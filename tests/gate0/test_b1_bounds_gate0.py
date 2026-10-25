"""Gate0 controlled Kimi mathematics, request admission and v1 persistence migration."""

import json
import sqlite3
from decimal import Decimal
from pathlib import Path

import pytest
from video_creator.application.engine import EngineService, digest
from video_creator.application.executor import OperationExecutor
from video_creator.application.pricing import (
    KIMI_K26_RULE,
    calculate_usage_cost,
    estimate_kimi_reserved,
)
from video_creator.domain.contracts import (
    CapabilityRoute,
    ExecutionPolicy,
    Money,
    OperationIntent,
    OperationObservation,
    ProductionRequest,
    ProjectInput,
)
from video_creator.domain.errors import EngineError


def kimi_payload():
    return {"model": "kimi-k2.6", "thinking": {"type": "disabled"}, "max_tokens": 512,
            "n": 1, "stream": False, "messages": [{"role": "user", "content": "public test"}]}


def setup_kimi(tmp_path):
    engine = EngineService(tmp_path / "KimiBoundInstance")
    engine.authorize_budget_group("shared-20", Money(amount="20"))
    engine.register_route(CapabilityRoute(route_id="kimi-synthetic", capability="text", source="owned_remote",
                          destination="https://nonbillable.invalid/kimi", verified=True,
                          max_operation_cost=Money(amount="1.72"), cost_rule_version=KIMI_K26_RULE))
    accepted = engine.accept_production("local-user", "one", ProductionRequest(goal="only admission math", policy=ExecutionPolicy(
        allowed_provider_routes=("kimi-synthetic",), budget_group_id="shared-20", external_transfer_allowed=True,
        max_cost=Money(amount="20"))))
    lease = engine.acquire_run("test-worker", run_id=accepted.run_id)
    engine.begin_step(lease, "creative", digest("public input"))
    return engine, accepted, lease


def make_intent(payload, *, sha=None, reserve="1.72"):
    return OperationIntent(step_key="creative", dedupe_key="one", route_id="kimi-synthetic",
        input_sha256=sha or digest(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))),
        reserved_cost=Money(amount=reserve))


def test_kimi_whole_context_reservation_exact_upper_bound():
    reserve = estimate_kimi_reserved(512)
    assert reserve.amount == Decimal("1.717760")
    maximum = calculate_usage_cost({"prompt_tokens": 262144, "completion_tokens": 512}, KIMI_K26_RULE)
    assert maximum == reserve
    cached = calculate_usage_cost({"prompt_tokens": 1000, "completion_tokens": 100, "cached_tokens": 500}, KIMI_K26_RULE)
    assert cached.amount == Decimal("0.0065")


@pytest.mark.parametrize("usage", [{"prompt_tokens": 262145, "completion_tokens": 1},
                                  {"prompt_tokens": 1, "completion_tokens": 513},
                                  {"prompt_tokens": 10, "completion_tokens": 1, "cached_tokens": 11},
                                  {"prompt_tokens": 1}])
def test_kimi_unknown_or_out_of_bound_usage_is_not_zero_cost(usage):
    with pytest.raises(EngineError):
        calculate_usage_cost(usage, KIMI_K26_RULE)


@pytest.mark.parametrize("field,value,code", [("model", "other", "model_denied"),
    ("thinking", {"type": "enabled"}, "thinking_mode_denied"),
    ("max_tokens", 513, "model_request_bound_exceeded"), ("max_tokens", True, "model_request_bound_exceeded"),
    ("n", 2, "generation_mode_denied"), ("stream", True, "generation_mode_denied"),
    ("tools", [{"type": "function"}], "tools_denied")])
def test_invalid_kimi_actual_payload_is_rejected_before_driver(tmp_path, field, value, code):
    engine, _, lease = setup_kimi(tmp_path)
    payload = kimi_payload()
    payload[field] = value
    calls = []
    with pytest.raises(EngineError) as error:
        OperationExecutor(engine).execute(lease, make_intent(payload), lambda p, s: calls.append(p), request_payload=payload)
    assert error.value.code == code
    assert calls == []
    assert engine.budget_status("shared-20")["reserved"]["amount"] == "0"


def test_kimi_payload_hash_and_sufficient_reservation_required(tmp_path):
    engine, _, lease = setup_kimi(tmp_path)
    payload = kimi_payload()
    calls = []
    for operation, keyword, code in [(make_intent(payload), {}, "provider_request_missing"),
        (make_intent(payload, sha="0" * 64), {"request_payload": payload}, "provider_request_conflict"),
        (make_intent(payload, reserve="1"), {"request_payload": payload}, "reservation_too_small")]:
        with pytest.raises(EngineError) as error:
            OperationExecutor(engine).execute(lease, operation, lambda p, s: calls.append(p), **keyword)
        assert error.value.code == code
    assert calls == []


def test_kimi_usage_settlement_and_repeat_do_not_double_spend(tmp_path):
    engine, accepted, lease = setup_kimi(tmp_path)
    payload = kimi_payload()
    calls = []

    def injected_driver(permit, secret):
        calls.append(permit.operation_id)
        return OperationObservation(status="succeeded", external_id="synthetic-kimi", usage={
            "prompt_tokens": 1000, "completion_tokens": 100, "cached_tokens": 500}, result_json={"text": "synthetic"})

    executor = OperationExecutor(engine)
    first = executor.execute(lease, make_intent(payload), injected_driver, request_payload=payload)
    repeat = executor.execute(lease, make_intent(payload), injected_driver, request_payload=payload)
    assert first == repeat and len(calls) == 1
    detail = engine.get_production("local-user", accepted.production_id)
    assert detail.cost.spent.amount == Decimal("0.0065")
    assert engine.budget_status("shared-20")["cap"]["amount"] == "20"
    assert engine.budget_status("shared-20")["spent"]["amount"] == "0.0065"
    assert engine.budget_status("shared-20")["reserved"]["amount"] == "0"


def test_schema_one_upgrade_preserves_instance_budget_and_rows(tmp_path):
    data_dir = tmp_path / "SchemaOneInstance"
    data_dir.mkdir()
    migration = Path(__file__).resolve().parents[2] / "services/engine/migrations/0001_ledger.sql"
    with sqlite3.connect(data_dir / "Metadata.sqlite") as connection:
        connection.executescript(migration.read_text(encoding="utf-8"))
        connection.execute("INSERT INTO metadata VALUES('instance_id','preserved-instance')")
        connection.execute("INSERT INTO budget_groups(id,owner,currency,cap_units,spent_units,reserved_units) VALUES('shared-20','local-user','CNY',20000000,100000,200000)")
    migrated = EngineService(data_dir)
    assert migrated.instance_id == "preserved-instance"
    assert migrated.budget_status("shared-20")["spent"]["amount"] == "0.1"
    assert migrated.budget_status("shared-20")["reserved"]["amount"] == "0.2"
    with migrated.db.connect() as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 2
        assert "cancellation_requested" in {row["name"] for row in connection.execute("PRAGMA table_info(runs)")}


def test_newer_schema_is_rejected_without_silent_reset(tmp_path):
    data_dir = tmp_path / "TooNewInstance"
    data_dir.mkdir()
    with sqlite3.connect(data_dir / "Metadata.sqlite") as connection:
        connection.execute("PRAGMA user_version=999")
    with pytest.raises(EngineError) as error:
        EngineService(data_dir)
    assert error.value.code == "schema_too_new"
    with sqlite3.connect(data_dir / "Metadata.sqlite") as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 999


def test_project_create_idempotency_same_and_conflicting_input(tmp_path):
    engine = EngineService(tmp_path / "ProjectCommands")
    original = engine.create_project("local-user", ProjectInput(name="public initial"), idempotency_key="same")
    repeat = engine.create_project("local-user", ProjectInput(name="public initial"), idempotency_key="same")
    assert original == repeat
    with pytest.raises(EngineError) as error:
        engine.create_project("local-user", ProjectInput(name="different"), idempotency_key="same")
    assert error.value.code == "idempotency_conflict"
