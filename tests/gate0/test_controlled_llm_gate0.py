"""Nonbillable HTTP transport injection against the real driver/ledger/LLM bridge."""

from __future__ import annotations

import json

import httpx
import pytest
from video_creator.application.engine import EngineService, digest
from video_creator.application.executor import OperationExecutor
from video_creator.application.pricing import DEEPSEEK_FLASH_RULE
from video_creator.domain.contracts import (
    CapabilityRoute,
    ExecutionPolicy,
    Money,
    ProductionRequest,
)
from video_creator.domain.errors import EngineError
from video_creator.providers.deepseek import ENDPOINT
from video_creator.workflows.controlled_llm import ControlledTextLLM


def controlled(tmp_path, monkeypatch):
    monkeypatch.setenv("VIDEO_CREATOR_SECRET_T1_FAKE", "fake-no-network-credential")
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
    monkeypatch.setenv("CREWAI_TRACING_ENABLED", "false")
    engine = EngineService(tmp_path / "SyntheticLlmInstance")
    engine.authorize_budget_group("test-shared", Money(amount="20"))
    engine.register_route(CapabilityRoute(route_id="deepseek-synthetic", capability="text", source="owned_remote",
                          destination=ENDPOINT, verified=True, credential_ref="env:VIDEO_CREATOR_SECRET_T1_FAKE",
                          max_operation_cost=Money(amount="0.2"), cost_rule_version=DEEPSEEK_FLASH_RULE))
    accepted = engine.accept_production("local-user", "controlled", ProductionRequest(
        goal="只验证故障与工具链，不做真实创作", policy=ExecutionPolicy(
            max_cost=Money(amount="20"), budget_group_id="test-shared",
            allowed_provider_routes=("deepseek-synthetic",), external_transfer_allowed=True)))
    lease = engine.acquire_run("synthetic-worker", run_id=accepted.run_id)
    engine.begin_step(lease, "creative", digest("public input"))
    return engine, accepted, ControlledTextLLM(engine, OperationExecutor(engine), lease, "creative", "deepseek-synthetic")


def transport(monkeypatch, handler):
    def create(*, retries):
        assert retries == 0
        return httpx.MockTransport(handler)

    monkeypatch.setattr("video_creator.providers.deepseek.httpx.HTTPTransport", create)


@pytest.mark.parametrize("fault", ["accepted-timeout", "429"])
def test_underlying_crewai_retry_wrapper_never_resubmits_unknown(tmp_path, monkeypatch, fault):
    engine, accepted, llm = controlled(tmp_path, monkeypatch)
    submissions = []

    def handler(request):
        submissions.append(request.url.path)
        assert request.headers["Authorization"] == "Bearer fake-no-network-credential"
        if fault == "accepted-timeout":
            raise httpx.ReadTimeout("rate limit synthetic upstream accepted", request=request)
        return httpx.Response(429, json={"error": "rate limit"}, request=request)

    transport(monkeypatch, handler)
    with pytest.raises(EngineError):
        llm.call("public test prompt")
    with pytest.raises(EngineError):
        llm.call("public test prompt")
    assert len(submissions) == 1
    detail = engine.get_production("local-user", accepted.production_id)
    assert detail.status == "needs_reconciliation"
    assert len(detail.operations) == 1
    assert detail.operations[0].actual_cost is None
    assert detail.cost.reserved.amount == Money(amount="0.2").amount
    assert detail.cost.spent.amount == 0


def test_same_prompt_replays_saved_response_without_second_network_submission(tmp_path, monkeypatch):
    engine, accepted, llm = controlled(tmp_path, monkeypatch)
    submissions = []

    def handler(request):
        submissions.append(json.loads(request.content))
        return httpx.Response(200, json={"id": "synthetic-one", "usage": {"prompt_tokens": 100, "completion_tokens": 10},
                                        "choices": [{"message": {"content": "synthetic answer"}, "finish_reason": "stop"}]}, request=request)

    transport(monkeypatch, handler)
    assert llm.call("same public prompt") == "synthetic answer"
    assert llm.call("same public prompt") == "synthetic answer"
    assert len(submissions) == 1
    assert len(engine.get_production("local-user", accepted.production_id).operations) == 1
    assert engine.get_production("local-user", accepted.production_id).cost.spent.amount == Money(amount="0.00028").amount


def test_native_tools_not_advertised_and_text_prompt_preserved(tmp_path, monkeypatch):
    _, _, llm = controlled(tmp_path, monkeypatch)
    submissions = []

    def handler(request):
        submissions.append(json.loads(request.content))
        return httpx.Response(200, json={"id": "synthetic-tool-inspection", "usage": {"prompt_tokens": 100, "completion_tokens": 10},
                                        "choices": [{"message": {"content": "synthetic answer"}, "finish_reason": "stop"}]}, request=request)

    transport(monkeypatch, handler)
    assert llm.supports_function_calling() is False
    public_prompt = "ReAct工具由上层prompt包含：Delegate work to coworker，coworker=洞察师，context=公开资料"
    llm.call(public_prompt, tools=[{"type": "function", "function": {"name": "synthetic_delegate"}}],
             available_functions={"synthetic_delegate": lambda: "never invoked"})
    assert submissions[0]["messages"][0]["content"] == public_prompt
    assert "tools" not in submissions[0]
    # This confirms the declared text/ReAct bridge, not autonomous delegation.


def test_creative_crew_actual_react_prompt_exposes_delegation_tool(tmp_path, monkeypatch):
    from crewai.tools.agent_tools.delegate_work_tool import DelegateWorkTool
    from crewai.utilities.string_utils import sanitize_tool_name
    from video_creator.workflows.creative import CreativeCrew

    engine, accepted, llm = controlled(tmp_path, monkeypatch)
    submissions = []
    proposal = {
        "insight": {"original_goal": "只验证故障与工具链，不做真实创作", "main_thesis": "测试",
                    "audience": "测试人员", "angle": "测试", "evidence": [], "source_gaps": ["无平台数据"], "preserved_facts": []},
        "candidates": [{"candidate_id": f"candidate-{i}", "title": "synthetic", "script": "synthetic",
                        "recommendation_reason": "synthetic"} for i in range(1, 4)],
        "selected_candidate_id": "candidate-1",
        "shots": [{"shot_id": f"shot-{i}", "visual": "synthetic", "narration": "synthetic",
                   "camera": "static", "duration_us": 1_000_000, "source_refs": []} for i in range(1, 4)],
    }

    def handler(request):
        submissions.append(json.loads(request.content))
        # No Action/Action Input injection: this explicitly does not perform delegation.
        content = "Thought: synthetic transport test\nFinal Answer: " + json.dumps(proposal, ensure_ascii=False)
        return httpx.Response(200, json={"id": f"synthetic-crew-{len(submissions)}", "usage": {"prompt_tokens": 100, "completion_tokens": 10},
                                        "choices": [{"message": {"content": content}, "finish_reason": "stop"}]}, request=request)

    transport(monkeypatch, handler)
    crew = CreativeCrew(engine, accepted.production_id, llm._lease, route_id="deepseek-synthetic")
    with pytest.raises(Exception) as captured:
        crew.proposal()
    assert submissions, "Crew must reach the real controlled driver for this transport probe"
    assert "guardrail" in str(captured.value).lower()
    first_prompt = "\n".join(message["content"] for message in submissions[0]["messages"])
    registered_name = sanitize_tool_name(DelegateWorkTool.model_fields["name"].default)
    (tmp_path / "ManagerPrompt.txt").write_text(first_prompt + "\n", encoding="utf-8", newline="\n")
    (tmp_path / "ToolExposureReceipt.json").write_text(json.dumps({"registered_name": registered_name,
        "registered_name_in_first_prompt": registered_name in first_prompt.lower(),
        "native_function_calling": False, "actual_delegations": crew.delegations,
        "network_submissions": len(submissions), "transport": "synthetic MockTransport; no actual model calls"},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    assert registered_name in first_prompt.lower(), "ReAct manager must see the actual sanitized registered delegation tool definition"
    assert "coworker" in first_prompt.lower() and "context" in first_prompt.lower()
    assert not engine.creative_revisions("local-user", accepted.production_id)
    assert all(record["count"] == 0 for record in crew.delegations)
