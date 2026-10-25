"""One-shot DeepSeek text driver behind an admitted Operation.

No SDK, automatic retry, redirects, token streaming or arbitrary destinations.
Fee interpretation is supplied by the backend-owned cost rule.
"""

from __future__ import annotations

import json

import httpx

from video_creator.application.pricing import MAX_REQUEST_BYTES
from video_creator.domain.contracts import ExecutionPermit, OperationObservation
from video_creator.domain.errors import EngineError
from video_creator.infrastructure.credentials import SecretHandle
from video_creator.workflows.attempt_control import current_attempt

ENDPOINT = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-flash"


def validate_messages(messages: list[dict]) -> list[dict[str, str]]:
    if not messages or len(messages) > 100:
        raise EngineError("text_input_denied", "Invalid text message count.", 422)
    result = []
    for item in messages:
        if item.get("role") not in {"system", "user", "assistant"} or not isinstance(
            item.get("content"), str
        ):
            raise EngineError(
                "text_input_denied", "Only text chat messages are admitted.", 422
            )
        result.append({"role": item["role"], "content": item["content"]})
    if (
        len(json.dumps(result, ensure_ascii=False).encode("utf-8"))
        > MAX_REQUEST_BYTES - 1024
    ):
        raise EngineError(
            "text_input_denied", "Text input exceeds the probe size limit.", 413
        )
    return result


class DeepSeekTextDriver:
    def __init__(
        self,
        messages: list[dict],
        *,
        max_tokens: int = 4096,
        json_mode: bool = False,
        stop_sequences: tuple[str, ...] = (),
    ):
        if not 1 <= max_tokens <= 4096:
            raise EngineError(
                "text_output_denied",
                "Output token limit must be between one and 4096.",
                422,
            )
        self.payload = {
            "model": MODEL,
            "messages": validate_messages(messages),
            "thinking": {"type": "disabled"},
            "stream": False,
            "max_tokens": max_tokens,
        }
        if len(stop_sequences) > 4 or any(
            not isinstance(s, str) or not 0 < len(s) <= 128 for s in stop_sequences
        ):
            raise EngineError(
                "text_stop_denied", "Stop sequences exceed the supported bound.", 422
            )
        if stop_sequences:
            self.payload["stop"] = list(stop_sequences)
        if json_mode:
            if not any(
                "json" in message["content"].lower()
                for message in self.payload["messages"]
            ):
                raise EngineError(
                    "json_instruction_missing",
                    "JSON mode requires an explicit JSON instruction.",
                    422,
                )
            self.payload["response_format"] = {"type": "json_object"}
        if (
            len(json.dumps(self.payload, ensure_ascii=False).encode("utf-8"))
            > MAX_REQUEST_BYTES
        ):
            raise EngineError(
                "text_input_denied",
                "Text request exceeds its admitted size bound.",
                413,
            )

    def __call__(
        self, permit: ExecutionPermit, secret: SecretHandle | None
    ) -> OperationObservation:
        control = current_attempt()
        control.check()
        if (
            permit.route.destination != ENDPOINT
            or permit.route.capability != "text"
            or secret is None
        ):
            raise EngineError(
                "provider_boundary_denied",
                "The admitted text route or credential is unavailable.",
                403,
            )
        # The Executor has already saved 'submitting'. Any ambiguous response
        # stays unknown, retaining the reservation; no provider exception leaks.
        try:
            transport = httpx.HTTPTransport(retries=0)
            with (
                httpx.Client(
                    transport=transport,
                    timeout=httpx.Timeout(control.remaining(120), connect=control.remaining(15)),
                    follow_redirects=False,
                    trust_env=False,
                ) as client,
                client.stream(
                    "POST",
                    ENDPOINT,
                    json=self.payload,
                    headers={
                        "Authorization": "Bearer " + secret.reveal(),
                        "Content-Type": "application/json",
                    },
                ) as response,
            ):
                if response.status_code != 200:
                    return OperationObservation(
                        status="unknown",
                        result_json={
                            "error_code": "upstream_http_status",
                            "http_status": response.status_code,
                        },
                    )
                chunks, size = [], 0
                for chunk in response.iter_bytes():
                    control.check()
                    size += len(chunk)
                    if size > 2 * 1024 * 1024:
                        return OperationObservation(
                            status="unknown",
                            result_json={"error_code": "upstream_response_too_large"},
                        )
                    chunks.append(chunk)
                body = json.loads(b"".join(chunks))
        except (httpx.HTTPError, OSError, ValueError, EngineError):
            return OperationObservation(
                status="unknown",
                result_json={"error_code": "upstream_transport_uncertain"},
            )
        usage = {}
        external_id = body.get("id") if isinstance(body, dict) else None
        try:
            raw_usage = body["usage"]
            for key in (
                "prompt_tokens",
                "completion_tokens",
                "total_tokens",
                "prompt_cache_hit_tokens",
                "prompt_cache_miss_tokens",
            ):
                if key in raw_usage:
                    value = raw_usage[key]
                    if (
                        isinstance(value, bool)
                        or not isinstance(value, int)
                        or value < 0
                    ):
                        raise ValueError("invalid usage")
                    usage[key] = value
            if not {"prompt_tokens", "completion_tokens"} <= usage.keys():
                raise ValueError("missing usage")
            content = body["choices"][0]["message"].get("content")
            finish_reason = body["choices"][0]["finish_reason"]
            if not isinstance(content, str):
                content = ""
        except (
            KeyError,
            IndexError,
            TypeError,
            ValueError,
            ArithmeticError,
            EngineError,
        ):
            return OperationObservation(
                status="unknown",
                external_id=external_id,
                usage=usage,
                result_json={"error_code": "upstream_observation_incomplete"},
            )
        # Length/empty/filtered output consumed a request. Its observed usage
        # settles before a separate explicit revision is considered.
        valid = finish_reason == "stop" and bool(content.strip())
        return OperationObservation(
            status="succeeded" if valid else "failed",
            external_id=external_id,
            usage=usage,
            actual_cost=None,
            cost_evidence="unknown",
            result_json={
                "content": content,
                "finish_reason": finish_reason,
                "model": body.get("model", MODEL),
            },
        )
