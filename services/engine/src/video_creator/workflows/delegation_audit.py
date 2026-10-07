"""Successful specialist output and exact final reuse, independent of attempts."""

from __future__ import annotations

import contextvars
import hashlib
import json

from crewai import Agent, Task
from crewai.tools.agent_tools.agent_tools import AgentTools
from crewai.tools.agent_tools.delegate_work_tool import DelegateWorkTool

from video_creator.domain.contracts import InsightBrief, ScriptCandidate, StoryboardShot
from video_creator.domain.errors import EngineError
from video_creator.workflows.react_protocol import final_response_content

ACTIVE_AUDIT: contextvars.ContextVar[list[dict] | None] = contextvars.ContextVar(
    "delegation_audit", default=None
)


def canonical_body(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def parse_specialist(role, raw):
    value = json.loads(raw)
    if role == "洞察师":
        return InsightBrief.model_validate(value).model_dump(mode="json")
    if role == "编剧":
        if not isinstance(value, list) or len(value) != 3:
            raise ValueError("three candidates required")
        parsed = [
            ScriptCandidate.model_validate(item).model_dump(mode="json")
            for item in value
        ]
        if len({item["candidate_id"] for item in parsed}) != 3:
            raise ValueError("distinct candidates required")
        return parsed
    if role == "导演":
        if not isinstance(value, list) or len(value) != 3:
            raise ValueError("three shots required")
        return [
            StoryboardShot.model_validate(item).model_dump(mode="json")
            for item in value
        ]
    raise ValueError("role unavailable")


def successful_reuse(proposal, audit):
    body = proposal.model_dump(mode="json")
    required = {"洞察师": body["insight"], "编剧": body["candidates"]}
    refs = []
    for role, value in required.items():
        sha = hashlib.sha256(canonical_body(value).encode("utf-8")).hexdigest()
        record = next(
            (
                r
                for r in audit
                if r.get("kind") == "delegate"
                and r.get("status") == "completed"
                and r.get("role") == role
                and r.get("output_sha256") == sha
                and r.get("model_calls")
                and all(
                    c.get("status") == "succeeded"
                    and c.get("protocol_accepted")
                    and c.get("cost_evidence") != "unknown"
                    for c in r["model_calls"]
                )
            ),
            None,
        )
        if record is None:
            return False, []
        refs.append(
            {"role": role, "task_sha256": record["task_sha256"], "output_sha256": sha}
        )
    return True, refs


class AuditedDelegateTool(DelegateWorkTool):
    def _execute(self, agent_name, task, context=None):
        audit = ACTIVE_AUDIT.get()
        if audit is None:
            raise EngineError(
                "delegation_audit_missing", "Delegation audit is unavailable.", 409
            )
        selected = next(
            (
                a
                for a in self.agents
                if self.sanitize_agent_name(a.role)
                == self.sanitize_agent_name(agent_name or "")
            ),
            None,
        )
        record = {
            "kind": "delegate",
            "role": agent_name,
            "status": "attempted",
            "task_sha256": hashlib.sha256(
                canonical_body({"task": task, "context": context}).encode("utf-8")
            ).hexdigest(),
        }
        audit.append(record)
        if selected is None:
            record["status"] = "failed"
            return "Delegation failed: role unavailable."
        llm = selected.llm
        before = len(llm.call_records)
        try:
            # This executes only in response to a model-selected actual tool invocation.
            schema_hint = (
                "InsightBrief JSON object"
                if selected.role == "洞察师"
                else "JSON array of exactly three ScriptCandidate objects"
                if selected.role == "编剧"
                else "JSON array of exactly three StoryboardShot objects"
            )
            child = Task(
                description=task
                + "\nReturn only "
                + schema_hint
                + ".\nSingle object JSON Schema:\n"
                + json.dumps(
                    {
                        "洞察师": InsightBrief,
                        "编剧": ScriptCandidate,
                        "导演": StoryboardShot,
                    }[selected.role].model_json_schema(),
                    ensure_ascii=False,
                ),
                agent=selected,
                expected_output=schema_hint,
            )
            raw = selected.execute_task(child, context)
            result = parse_specialist(selected.role, raw)
            calls = [
                c for c in llm.call_records[before:] if c.get("role") == selected.role
            ]
            if not calls or any(
                c.get("status") != "succeeded"
                or not c.get("protocol_accepted")
                or c.get("cost_evidence") == "unknown"
                for c in calls
            ):
                raise ValueError("no successful model output")
            encoded = canonical_body(result)
            # Parsing/formatting cannot substitute a different Schema-valid
            # task result for the actual successful final model output.
            actual_content = llm.recorded_response(calls[-1])
            actual_result = parse_specialist(
                selected.role, final_response_content(actual_content)
            )
            if canonical_body(actual_result) != encoded:
                raise ValueError("task result differs from actual model output")
            record.update(
                {
                    "role": selected.role,
                    "status": "completed",
                    "model_calls": calls,
                    "output_sha256": hashlib.sha256(
                        encoded.encode("utf-8")
                    ).hexdigest(),
                    "source_model_output_sha256": calls[-1]["output_sha256"],
                    "source_operation_dedupe_key": calls[-1]["operation_dedupe_key"],
                }
            )
            return encoded
        except (EngineError, ValueError, TypeError):
            record["status"] = "failed"
            return "Delegation failed: specialist output unavailable or invalid."


class AuditedManager(Agent):
    def get_delegation_tools(self, agents):
        defaults = AgentTools(agents=agents).tools()
        return [
            AuditedDelegateTool(
                agents=list(agents), description=defaults[0].description
            ),
            defaults[1],
        ]
