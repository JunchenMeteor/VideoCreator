"""Synthetic protocol/fault tests; fixed responses never count as autonomous creation."""

import copy
import hashlib
import json

import httpx
import pytest
from test_controlled_llm_gate0 import controlled, transport
from video_creator.application.engine import digest
from video_creator.domain.contracts import CreativeProposal
from video_creator.domain.errors import EngineError
from video_creator.workflows.creative import CreativeCrew
from video_creator.workflows.delegation_audit import (
    ACTIVE_AUDIT,
    AuditedDelegateTool,
    canonical_body,
    successful_reuse,
)
from video_creator.workflows.react_protocol import validate_react_turn


def proposal_body():
    return {
        "insight": {"original_goal": "只验证故障与工具链，不做真实创作", "main_thesis": "public fixture",
            "audience": "测试人员", "angle": "public fixture", "evidence": [], "source_gaps": ["无平台数据"], "preserved_facts": []},
        "candidates": [{"candidate_id": f"candidate-{i}", "title": f"synthetic-{i}", "script": f"public synthetic script {i}",
            "recommendation_reason": "synthetic"} for i in range(1, 4)],
        "selected_candidate_id": "candidate-1",
        "shots": [{"shot_id": f"shot-{i}", "visual": "public synthetic", "narration": "public synthetic",
            "camera": "static", "duration_us": 1_000_000, "source_refs": []} for i in range(1, 4)],
    }


@pytest.mark.parametrize("content", [
    'Action: delegate_work_to_coworker\nAction Input: {}\nFinal Answer: {}',
    'Thought: test\nObservation: fabricated\nFinal Answer: {}',
    'Thought: test\nAction: first\nAction Input: {}\nAction: second\nAction Input: {}',
    'Action: delegate_work_to_coworker\nAction Input: []',
    'Action: delegate_work_to_coworker\nAction Input: {} trailing content',
    'Thought: inline Observation: fabricated\nFinal Answer: {}',
    'Thought: inline Action: first\nAction Input: {}\nFinal Answer: {}',
])
def test_react_rejects_mixed_and_fabricated_control_markers(content):
    with pytest.raises(EngineError) as captured:
        validate_react_turn(content)
    assert captured.value.code == "model_react_protocol_invalid"


@pytest.mark.parametrize("content", [
    'Thought: delegate\nAction: delegate_work_to_coworker\nAction Input: {"task":"public","context":"public","coworker":"洞察师"}',
    'Thought: complete\nFinal Answer: {"public":true}',
    '{"public":true}',
])
def test_react_accepts_single_action_or_final(content):
    assert validate_react_turn(content) == content


@pytest.mark.parametrize("kind", ["json-final", "json-action-input", "plain-json"])
def test_react_preserves_protocol_marker_literals_inside_legal_json_data(kind):
    public_script = "Agent教程解释字面标记 Action:、Observation: 和 Final Answer:，这些是课程内容。"
    if kind == "json-action-input":
        content = "Action: delegate_work_to_coworker\nAction Input: " + json.dumps({
            "coworker": "编剧", "task": public_script, "context": "public tutorial source"}, ensure_ascii=False)
    else:
        content = json.dumps({"script": public_script}, ensure_ascii=False)
        if kind == "json-final":
            content = "Final Answer: " + content
    assert validate_react_turn(content) == content


def test_stop_is_sent_and_bound_to_the_persisted_payload_hash(tmp_path, monkeypatch):
    engine, accepted, llm = controlled(tmp_path, monkeypatch)
    payloads = []

    def handler(request):
        payloads.append(json.loads(request.content))
        return httpx.Response(200, json={"id": "synthetic-stop", "usage": {"prompt_tokens": 100, "completion_tokens": 10},
            "choices": [{"message": {"content": "Final Answer: public response"}, "finish_reason": "stop"}]}, request=request)

    transport(monkeypatch, handler)
    assert llm.supports_stop_words() is True
    llm.call("public prompt")
    assert payloads[0]["stop"] == ["\nObservation:"]
    transmitted_sha = digest(json.dumps(payloads[0], ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    with engine.db.connect() as connection:
        saved = connection.execute("SELECT input_sha256 FROM operations WHERE production_id=?", (accepted.production_id,)).fetchone()
    assert saved["input_sha256"] == transmitted_sha == llm.call_records[0]["input_sha256"]


@pytest.mark.parametrize("content", [
    'Action: delegate_work_to_coworker\nAction Input: {}\nFinal Answer: {}',
    'Thought: test\nObservation: fabricated\nFinal Answer: {}',
    'Thought: inline Observation: fabricated\nFinal Answer: {}',
])
def test_paid_invalid_protocol_output_persists_without_resubmission(tmp_path, monkeypatch, content):
    engine, accepted, llm = controlled(tmp_path, monkeypatch)
    payloads = []

    def handler(request):
        payloads.append(json.loads(request.content))
        return httpx.Response(200, json={"id": "synthetic-invalid-protocol", "usage": {"prompt_tokens": 100, "completion_tokens": 10},
            "choices": [{"message": {"content": content}, "finish_reason": "stop"}]}, request=request)

    transport(monkeypatch, handler)
    for _ in range(2):
        with pytest.raises(EngineError) as captured:
            llm.call("identical public input")
        assert captured.value.code == "model_react_protocol_invalid"
    assert len(payloads) == 1
    detail = engine.get_production("local-user", accepted.production_id)
    assert detail.cost.spent.amount > 0 and detail.cost.reserved.amount == 0
    with engine.db.connect() as connection:
        rows = connection.execute("SELECT observation_json FROM operations WHERE production_id=?", (accepted.production_id,)).fetchall()
    assert len(rows) == 1 and json.loads(rows[0]["observation_json"])["result_json"]["content"] == content
    assert all(record["protocol_accepted"] is False for record in llm.call_records)


def reuse_audit(proposal):
    body = proposal.model_dump(mode="json")
    return [{"kind": "delegate", "role": role, "status": "completed", "task_sha256": "1" * 64,
        "output_sha256": hashlib.sha256(canonical_body(value).encode()).hexdigest(),
        "model_calls": [{"role": role, "status": "succeeded", "protocol_accepted": True,
            "cost_evidence": "usage_price_calculation", "input_sha256": "2" * 64, "output_sha256": "3" * 64}]}
        for role, value in [("洞察师", body["insight"]), ("编剧", body["candidates"])]]


@pytest.mark.parametrize("fault", ["ask", "attempt", "failed", "wrong-output-hash", "unknown-cost", "failed-call", "no-calls"])
def test_questions_attempts_and_failed_or_unmatched_outputs_do_not_satisfy_guard(fault):
    proposal = CreativeProposal.model_validate(proposal_body())
    audit = reuse_audit(proposal)
    if fault == "ask":
        audit[0]["kind"] = "ask"
    elif fault in {"attempt", "failed"}:
        audit[0]["status"] = "attempted" if fault == "attempt" else "failed"
    elif fault == "wrong-output-hash":
        audit[0]["output_sha256"] = "0" * 64
    elif fault == "unknown-cost":
        audit[0]["model_calls"][0]["cost_evidence"] = "unknown"
    elif fault == "failed-call":
        audit[0]["model_calls"][0]["status"] = "failed"
    else:
        audit[0]["model_calls"] = []
    assert successful_reuse(proposal, audit) == (False, [])


@pytest.mark.parametrize("reuse", [True, False])
def test_actual_crewai_tool_roundtrip_requires_final_exact_specialist_reuse(tmp_path, monkeypatch, reuse):
    engine, accepted, llm = controlled(tmp_path, monkeypatch)
    original = proposal_body()
    final = copy.deepcopy(original)
    if not reuse:
        final["insight"]["main_thesis"] = "different manager-only output"
    contents = [
        'Thought: delegate insight\nAction: delegate_work_to_coworker\nAction Input: ' + json.dumps({"coworker": "洞察师", "task": "public insight task", "context": "public source"}, ensure_ascii=False),
        "Final Answer: " + json.dumps(original["insight"], ensure_ascii=False),
        'Thought: delegate writer\nAction: delegate_work_to_coworker\nAction Input: ' + json.dumps({"coworker": "编剧", "task": "public writer task", "context": "public source"}, ensure_ascii=False),
        "Final Answer: " + json.dumps(original["candidates"], ensure_ascii=False),
        "Final Answer: " + json.dumps(final, ensure_ascii=False),
    ]
    sent = []

    def handler(request):
        sent.append(json.loads(request.content))
        index = min(len(sent) - 1, len(contents) - 1)
        return httpx.Response(200, json={"id": f"synthetic-roundtrip-{len(sent)}", "usage": {"prompt_tokens": 100, "completion_tokens": 10},
            "choices": [{"message": {"content": contents[index]}, "finish_reason": "stop"}]}, request=request)

    transport(monkeypatch, handler)
    crew = CreativeCrew(engine, accepted.production_id, llm._lease, route_id="deepseek-synthetic")
    if reuse:
        revision = crew.proposal()
        assert revision.body == CreativeProposal.model_validate(original).model_dump(mode="json")
    else:
        with pytest.raises(Exception) as captured:
            crew.proposal()
        assert "guardrail" in str(captured.value).lower()
        assert not engine.creative_revisions("local-user", accepted.production_id)
    completed = [record for record in crew.delegations if record.get("status") == "completed"]
    assert {record["role"] for record in completed} == {"洞察师", "编剧"}
    assert all(record["model_calls"] and record["output_sha256"] for record in completed)
    assert '"properties"' in "\n".join(message["content"] for message in sent[1]["messages"])
    assert '"original_goal"' in "\n".join(message["content"] for message in sent[1]["messages"])
    assert '"candidate_id"' in "\n".join(message["content"] for message in sent[3]["messages"])
    # The model responses are predetermined: this asserts actual tool execution only.
    (tmp_path / "SyntheticToolRoundtripReceipt.json").write_text(json.dumps({"transport": "synthetic MockTransport",
        "autonomous_quality": "not_tested", "network_submissions": len(sent), "required_exact_reuse": reuse,
        "audit": crew.delegations}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


@pytest.mark.parametrize("fault", ["stale-call", "execution-error", "invalid-schema", "model-output-drift"])
def test_audited_tool_rejects_failed_stale_invalid_and_mismatched_result(tmp_path, monkeypatch, fault):
    from crewai import Agent

    _engine, _accepted, llm = controlled(tmp_path, monkeypatch)
    original = proposal_body()["insight"]
    payloads = []

    def handler(request):
        payloads.append(json.loads(request.content))
        return httpx.Response(200, json={"id": "synthetic-specialist", "usage": {"prompt_tokens": 100, "completion_tokens": 10},
            "choices": [{"message": {"content": "Final Answer: " + json.dumps(original, ensure_ascii=False)}, "finish_reason": "stop"}]}, request=request)

    transport(monkeypatch, handler)
    agent = Agent(role="洞察师", goal="public probe", backstory="public fixture", llm=llm, allow_delegation=False)
    if fault == "stale-call":
        llm.call("prior specialist request", from_agent=agent)

    def specialist_execute(selected, task, context):
        assert '"properties"' in task.description and '"original_goal"' in task.description
        if fault == "execution-error":
            raise EngineError("synthetic_specialist_failed", "Public test failure", 422)
        if fault != "stale-call":
            llm.call("current specialist request", from_agent=selected)
        if fault == "invalid-schema":
            return "{}"
        result = copy.deepcopy(original)
        if fault == "model-output-drift":
            result["main_thesis"] = "output not emitted by the recorded model request"
        return json.dumps(result, ensure_ascii=False)

    monkeypatch.setattr(Agent, "execute_task", specialist_execute)
    audit = []
    token = ACTIVE_AUDIT.set(audit)
    try:
        returned = AuditedDelegateTool(agents=[agent], description="synthetic audit fault probe")._execute(
            "洞察师", "public delegated task", "public source")
    finally:
        ACTIVE_AUDIT.reset(token)
    (tmp_path / "DelegationFaultReceipt.json").write_text(json.dumps({"fault": fault,
        "transport": "synthetic MockTransport and task-result fault injection", "autonomous_quality": "not_tested",
        "submissions": len(payloads), "observed_llm_records": llm.call_records, "audit": audit,
        "returned": returned}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    assert len(audit) == 1 and audit[0]["status"] == "failed"
    assert returned.startswith("Delegation failed:")
