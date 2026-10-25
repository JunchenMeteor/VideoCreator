"""CrewAI text bridge: every model request uses the same backend ledger."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from crewai.llms.base_llm import BaseLLM
from pydantic import BaseModel, PrivateAttr

from video_creator.application.engine import EngineService
from video_creator.application.executor import OperationExecutor
from video_creator.domain.contracts import LeaseGrant, OperationIntent
from video_creator.domain.errors import EngineError
from video_creator.providers.deepseek import (
    MODEL,
    DeepSeekTextDriver,
    validate_messages,
)
from video_creator.workflows.attempt_control import current_attempt
from video_creator.workflows.react_protocol import crewai_safe_turn, validate_react_turn


class ControlledTextLLM(BaseLLM):
    _engine: EngineService = PrivateAttr()
    _executor: OperationExecutor = PrivateAttr()
    _lease: LeaseGrant = PrivateAttr()
    _step_key: str = PrivateAttr()
    _route_id: str = PrivateAttr()
    _max_calls: int = PrivateAttr()
    _calls: int = PrivateAttr(default=0)
    _records: list[dict] = PrivateAttr(default_factory=list)
    _response_text: dict[str, str] = PrivateAttr(default_factory=dict)

    def __init__(
        self,
        engine: EngineService,
        executor: OperationExecutor,
        lease: LeaseGrant,
        step_key: str,
        route_id: str,
        *,
        max_calls: int = 16,
        max_tokens: int = 4096,
    ):
        super().__init__(
            model=MODEL, max_tokens=max_tokens, temperature=0.7, stop=["\nObservation:"]
        )
        self._engine, self._executor, self._lease = engine, executor, lease
        self._step_key, self._route_id = step_key, route_id
        self._max_calls = max_calls

    @property
    def call_records(self) -> tuple[dict, ...]:
        return tuple(self._records)

    def recorded_response(self, record: dict) -> str:
        """Resolve only a response captured by this controlled model adapter."""
        if not any(saved is record for saved in self._records):
            raise ValueError("model call record does not belong to this adapter")
        content = self._response_text.get(record.get("operation_dedupe_key"))
        if content is None or hashlib.sha256(
            content.encode("utf-8")
        ).hexdigest() != record.get("output_sha256"):
            raise ValueError("recorded model output is unavailable or inconsistent")
        return content

    def supports_function_calling(self) -> bool:
        # CrewAI executes its bounded delegation tools with its ReAct parser.
        return False

    def supports_stop_words(self) -> bool:
        return True

    def get_context_window_size(self) -> int:
        return 32768

    def call(
        self,
        messages,
        tools=None,
        callbacks=None,
        available_functions=None,
        from_task=None,
        from_agent=None,
        response_model: type[BaseModel] | None = None,
        **kwargs: Any,
    ):
        current_attempt().check()
        if self._calls >= self._max_calls:
            raise EngineError(
                "model_call_limit",
                "This creative step reached its bounded model call limit.",
            )
        normalized = validate_messages(
            [{"role": "user", "content": messages}]
            if isinstance(messages, str)
            else messages
        )
        driver = DeepSeekTextDriver(
            normalized,
            max_tokens=int(self.max_tokens),
            json_mode=response_model is not None,
            stop_sequences=tuple(
                dict.fromkeys(["\nObservation:", *self.stop_sequences])
            )
            if response_model is None
            else (),
        )
        payload = json.dumps(
            driver.payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        sha = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        self._lease = self._engine.heartbeat(self._lease, lease_seconds=600)
        route = self._engine.configured_route(self._route_id)
        intent = OperationIntent(
            step_key=self._step_key,
            dedupe_key=f"{self._step_key}.{sha[:48]}",
            input_sha256=sha,
            route_id=self._route_id,
            reserved_cost=route.max_operation_cost,
        )
        observation = self._executor.execute(self._lease, intent, driver)
        self._calls += 1
        self._records.append(
            {
                "input_sha256": sha,
                "operation_dedupe_key": intent.dedupe_key,
                "external_id": observation.external_id,
                "status": observation.status,
                "usage": observation.usage,
                "cost_evidence": observation.cost_evidence,
                "observed_cost": observation.actual_cost.model_dump(mode="json")
                if observation.actual_cost
                else None,
                "role": getattr(from_agent, "role", None),
                "delegation_tool_in_prompt": any(
                    "delegate_work_to_coworker" in m["content"].lower()
                    for m in normalized
                ),
                "response_model": response_model.__name__ if response_model else None,
            }
        )
        if (
            observation.status != "succeeded"
            or observation.cost_evidence == "unknown"
            or not isinstance(observation.result_json, dict)
        ):
            # No original HTTP status/body/cause escapes into CrewAI retry classification.
            raise EngineError(
                "model_operation_unavailable",
                "Model operation requires inspection before continuing.",
                retryability="reconcile"
                if observation.status == "unknown"
                or observation.cost_evidence == "unknown"
                else "never",
            )
        content = observation.result_json.get("content")
        if not isinstance(content, str) or not content.strip():
            raise EngineError(
                "model_output_invalid",
                "Model response did not contain usable text.",
                422,
            )
        self._track_token_usage_internal(observation.usage)
        self._records[-1]["output_sha256"] = hashlib.sha256(
            content.encode("utf-8")
        ).hexdigest()
        self._response_text[intent.dedupe_key] = content
        if response_model is None:
            try:
                validate_react_turn(content)
            except EngineError:
                self._records[-1]["protocol_accepted"] = False
                raise
        self._records[-1]["protocol_accepted"] = True
        current_attempt().check()
        return (
            response_model.model_validate_json(content)
            if response_model
            else crewai_safe_turn(content)
        )
