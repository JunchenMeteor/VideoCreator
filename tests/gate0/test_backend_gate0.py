"""Real SQLite/API implementation tests. All upstream responses are nonbillable injection."""

from __future__ import annotations

import hashlib
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import httpx
import pytest
from pydantic import ValidationError
from video_creator.api.app import create_app
from video_creator.application.assets import AssetService
from video_creator.application.engine import EngineService, digest
from video_creator.application.executor import OperationExecutor
from video_creator.application.pricing import DEEPSEEK_FLASH_RULE, calculate_usage_cost
from video_creator.domain.contracts import (
    AssetCandidate,
    CapabilityRoute,
    CreativeRevision,
    ExecutionPolicy,
    Money,
    OperationIntent,
    OperationObservation,
    ProductionRequest,
    ProjectInput,
    ReviewDecision,
)
from video_creator.domain.errors import EngineError
from video_creator.infrastructure.credentials import CredentialVault, SecretHandle


class Clock:
    def __init__(self):
        self.value = 10_000_000

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds * 1_000_000


@pytest.fixture
def setup_engine(tmp_path):
    clock = Clock()
    return EngineService(tmp_path / "Instance", clock=clock), clock


def request(*, budget="20", group="test-shared", routes=("text-test",), external=True):
    return ProductionRequest(goal="仅目标和公开测试资料", policy=ExecutionPolicy(
        max_cost=Money(amount=budget), budget_group_id=group,
        allowed_provider_routes=routes, external_transfer_allowed=external))


def configure(engine, *, bound="0.2", rule="synthetic-cost-v1", group_cap="20"):
    engine.authorize_budget_group("test-shared", Money(amount=group_cap))
    engine.register_route(CapabilityRoute(route_id="text-test", capability="text", source="owned_remote",
                          destination="https://nonbillable.invalid/text", verified=True,
                          max_operation_cost=Money(amount=bound), cost_rule_version=rule))


def lease_and_step(engine, req=None, key="one", step="creative"):
    accepted = engine.accept_production("local-user", key, req or request())
    lease = engine.acquire_run("test-worker", lease_seconds=1, run_id=accepted.run_id)
    assert lease is not None
    engine.begin_step(lease, step, digest("public input"))
    return accepted, lease


def intent(key="operation-one", cost="0.2", step="creative", sha=None):
    return OperationIntent(step_key=step, dedupe_key=key, input_sha256=sha or digest("public prompt"),
                           route_id="text-test", reserved_cost=Money(amount=cost))


def settled_observation(amount="0.05"):
    return OperationObservation(status="succeeded", external_id="synthetic-upstream-one",
                                actual_cost=Money(amount=amount), cost_evidence="provider_receipt",
                                result_json={"content": "synthetic response, not actual model creation"})


def assert_engine_error(code, callable_):
    with pytest.raises(EngineError) as captured:
        callable_()
    assert captured.value.code == code


def test_same_key_different_input_conflicts(setup_engine):
    engine, _ = setup_engine
    configure(engine)
    first = engine.accept_production("local-user", "same", request())
    repeat = engine.accept_production("local-user", "same", request())
    assert first == repeat
    assert_engine_error("idempotency_conflict", lambda: engine.accept_production("local-user", "same", ProductionRequest(goal="changed")))


def test_concurrent_accept_creates_one_production_and_run(setup_engine):
    engine, _ = setup_engine
    configure(engine)
    with ThreadPoolExecutor(max_workers=8) as workers:
        records = list(workers.map(lambda _: engine.accept_production("local-user", "parallel", request()), range(16)))
    assert len({(item.production_id, item.run_id) for item in records}) == 1
    with engine.db.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM productions").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 1


def test_subject_cannot_read_or_attach_another_project(setup_engine):
    engine, _ = setup_engine
    project = engine.create_project("alice", ProjectInput(name="private"))
    assert_engine_error("not_found", lambda: engine.get_project("bob", project.project_id))
    assert_engine_error("not_found", lambda: engine.accept_production("bob", "attach", ProductionRequest(goal="x", project_id=project.project_id)))


def test_project_versions_are_not_overwritten(setup_engine):
    engine, _ = setup_engine
    project = engine.create_project("local-user", ProjectInput(name="initial"))
    changed = engine.update_project("local-user", project.project_id, 1, ProjectInput(name="new"))
    assert changed.revision == 2
    assert_engine_error("revision_conflict", lambda: engine.update_project("local-user", project.project_id, 1, ProjectInput(name="stale")))
    assert engine.get_project("local-user", project.project_id).name == "new"


def test_concurrent_lease_only_one_worker_acquires(setup_engine):
    engine, _ = setup_engine
    accepted = engine.accept_production("local-user", "lease", ProductionRequest(goal="x"))
    with ThreadPoolExecutor(max_workers=8) as workers:
        leases = list(workers.map(lambda i: engine.acquire_run(f"worker-{i}", run_id=accepted.run_id), range(16)))
    assert sum(item is not None for item in leases) == 1


def test_expired_fence_rejects_old_worker_but_preserves_completed_step(setup_engine):
    engine, clock = setup_engine
    configure(engine)
    accepted, old = lease_and_step(engine)
    engine.complete_step(old, "creative", result_json={"approved": "persisted"})
    clock.advance(2)
    replacement = engine.acquire_run("replacement", run_id=accepted.run_id)
    assert replacement.fencing_token > old.fencing_token
    assert_engine_error("stale_lease", lambda: engine.complete_step(old, "creative", result_json={"approved": "persisted"}))
    assert engine.read_step(replacement, "creative")["status"] == "succeeded"


def test_persistent_intent_precedes_driver_and_network_is_outside_transaction(setup_engine):
    engine, _ = setup_engine
    configure(engine)
    accepted, lease = lease_and_step(engine)
    calls = []

    def injected_driver(permit, secret):
        with engine.db.transaction() as connection:
            operation = connection.execute("SELECT status FROM operations WHERE id=?", (permit.operation_id,)).fetchone()
            assert operation["status"] == "submitting"
            assert connection.execute("SELECT COUNT(*) FROM events WHERE event_type='operation.dispatch_intent'").fetchone()[0] == 1
        calls.append(permit.operation_id)
        return settled_observation()

    executor = OperationExecutor(engine)
    first = executor.execute(lease, intent(), injected_driver)
    second = executor.execute(lease, intent(), injected_driver)
    assert first == second
    assert len(calls) == 1
    assert engine.get_production("local-user", accepted.production_id).cost.spent.amount == Decimal("0.05")


def test_accepted_then_timeout_retains_reserve_and_never_replays(setup_engine):
    engine, clock = setup_engine
    configure(engine)
    accepted, lease = lease_and_step(engine)
    calls = []

    def accepted_then_timeout(permit, secret):
        calls.append(permit.operation_id)
        raise TimeoutError("synthetic upstream accepted then timed out")

    executor = OperationExecutor(engine)
    observation = executor.execute(lease, intent(), accepted_then_timeout)
    assert observation.status == "unknown"
    assert observation.actual_cost is None
    assert engine.get_production("local-user", accepted.production_id).status == "needs_reconciliation"
    assert engine.budget_status("test-shared")["reserved"]["amount"] == "0.2"
    clock.advance(301)
    resumed = engine.acquire_run("reconciler", run_id=accepted.run_id, reconciliation=True)
    with pytest.raises(EngineError):
        executor.execute(resumed, intent(), accepted_then_timeout)
    assert len(calls) == 1
    assert engine.budget_status("test-shared")["spent"]["amount"] == "0"


def test_crash_after_dispatch_before_observation_becomes_unknown(setup_engine):
    engine, clock = setup_engine
    configure(engine)
    accepted, lease = lease_and_step(engine)
    operation = engine.prepare_operation(lease, intent())
    engine.claim_operation(lease, operation["id"])
    clock.advance(2)
    restarted = EngineService(engine.db.data_dir, clock=clock)
    assert restarted.recover()["needs_reconciliation"] == 1
    assert restarted.get_production("local-user", accepted.production_id).operations[0].status == "unknown"
    assert restarted.budget_status("test-shared")["reserved"]["amount"] == "0.2"


def test_settlement_is_idempotent_and_conflicting_observation_rejected(setup_engine):
    engine, _ = setup_engine
    configure(engine)
    _, lease = lease_and_step(engine)
    operation = engine.prepare_operation(lease, intent())
    engine.claim_operation(lease, operation["id"])
    observed = settled_observation()
    engine.observe_operation(lease, operation["id"], observed)
    engine.observe_operation(lease, operation["id"], observed)
    assert engine.budget_status("test-shared")["spent"]["amount"] == "0.05"
    assert engine.budget_status("test-shared")["reserved"]["amount"] == "0"
    assert_engine_error("observation_conflict", lambda: engine.observe_operation(lease, operation["id"], settled_observation("0.06")))


def test_cancel_unsubmitted_reservation_releases_only_once(setup_engine):
    engine, _ = setup_engine
    configure(engine)
    accepted, lease = lease_and_step(engine)
    engine.prepare_operation(lease, intent())
    engine.cancel_production("local-user", accepted.production_id)
    engine.cancel_production("local-user", accepted.production_id)
    assert engine.budget_status("test-shared")["reserved"]["amount"] == "0"
    assert engine.budget_status("test-shared")["spent"]["amount"] == "0"


def test_shared_cap_survives_second_key_and_cannot_be_reset(setup_engine):
    engine, _ = setup_engine
    configure(engine, group_cap="0.3")
    _, first = lease_and_step(engine, key="first")
    engine.prepare_operation(first, intent())
    _, second = lease_and_step(engine, key="second")
    assert_engine_error("shared_budget_exceeded", lambda: engine.prepare_operation(second, intent("second-operation")))
    assert_engine_error("budget_authorization_conflict", lambda: engine.authorize_budget_group("test-shared", Money(amount="20")))
    engine.authorize_budget_group("test-shared", Money(amount="0.3"))
    assert engine.budget_status("test-shared")["reserved"]["amount"] == "0.2"


@pytest.mark.parametrize("case,code", [("zero", "budget_exceeded"), ("route", "route_denied"), ("external", "transfer_denied")])
def test_policy_boundary_refuses_driver_before_dispatch(setup_engine, case, code):
    engine, _ = setup_engine
    configure(engine)
    req = request(budget="0" if case == "zero" else "20", routes=() if case == "route" else ("text-test",), external=case != "external")
    _, lease = lease_and_step(engine, req)
    calls = []
    assert_engine_error(code, lambda: OperationExecutor(engine).execute(lease, intent(), lambda p, s: calls.append(p)))
    assert not calls
    assert engine.budget_status("test-shared")["reserved"]["amount"] == "0"


def test_observed_unknown_cost_cannot_complete_step(setup_engine):
    engine, _ = setup_engine
    configure(engine)
    accepted, lease = lease_and_step(engine)
    observed = OperationExecutor(engine).execute(lease, intent(), lambda p, s: OperationObservation(status="succeeded", result_json={"content": "synthetic accepted"}))
    assert observed.actual_cost is None
    assert engine.get_production("local-user", accepted.production_id).status == "needs_reconciliation"
    with pytest.raises(EngineError):
        engine.complete_step(lease, "creative")
    assert engine.budget_status("test-shared")["reserved"]["amount"] == "0.2"


def test_cancel_after_success_with_unknown_cost_keeps_reconciliation_access(setup_engine):
    engine, clock = setup_engine
    configure(engine)
    accepted, lease = lease_and_step(engine)
    OperationExecutor(engine).execute(lease, intent(), lambda p, s: OperationObservation(status="succeeded", result_json={"content": "synthetic accepted"}))
    clock.advance(301)
    engine.cancel_production("local-user", accepted.production_id)
    resumed = engine.acquire_run("reconciler", run_id=accepted.run_id, reconciliation=True)
    assert resumed is not None, "Cancel must not orphan a received operation whose cost remains unknown"


def test_feedback_reuses_shared_budget_and_limit_is_not_reset(setup_engine):
    engine, _ = setup_engine
    configure(engine)
    accepted, lease = lease_and_step(engine)
    OperationExecutor(engine).execute(lease, intent(), lambda p, s: settled_observation("0.1"))
    for cycle in range(3):
        revision = CreativeRevision(revision_id=f"plan-{cycle}", kind="plan", body={"facts": ["public original fact"]})
        engine.commit_creative_revision(lease, revision)
        engine.wait_for_review(lease, revision.revision_id)
        decision = ReviewDecision(target_revision_id=revision.revision_id, action="revise", instruction_text="只修改第三镜头，保留事实")
        if cycle == 2:
            with pytest.raises(EngineError) as error:
                engine.submit_decision("local-user", lease.run_id, f"decision-{cycle}", decision)
            assert error.value.code == "revision_limit"
            break
        revised = engine.submit_decision("local-user", lease.run_id, f"decision-{cycle}", decision)
        duplicate = engine.submit_decision("local-user", lease.run_id, f"decision-{cycle}", decision)
        assert revised == duplicate
        lease = engine.acquire_run("revision-worker", run_id=revised["new_run_id"])
    detail = engine.get_production("local-user", accepted.production_id)
    assert detail.revision_cycles == 2
    assert detail.cost.spent.amount == Decimal("0.1")
    assert engine.budget_status("test-shared")["spent"]["amount"] == "0.1"


def test_immutable_creative_revision_and_cross_production_refs(setup_engine):
    engine, _ = setup_engine
    configure(engine)
    _, first = lease_and_step(engine, key="first")
    engine.commit_creative_revision(first, CreativeRevision(revision_id="fixed", kind="plan", body={"a": 1}))
    assert_engine_error("revision_conflict", lambda: engine.commit_creative_revision(first, CreativeRevision(revision_id="fixed", kind="plan", body={"a": 2})))
    _, second = lease_and_step(engine, key="second")
    assert_engine_error("revision_ref_denied", lambda: engine.commit_creative_revision(second, CreativeRevision(revision_id="foreign", kind="script", input_revision_refs=("fixed",), body={})))


def test_asset_hash_owner_size_and_media_decoder_guard(setup_engine):
    engine, _ = setup_engine
    service = AssetService(engine)
    data = b'{"public":true}'
    staged = service.stage_bytes("alice", data, "application/json")
    candidate = AssetCandidate(**staged, source="test", rights="self-created")
    assert_engine_error("not_found", lambda: service.import_asset("bob", candidate))
    wrong = candidate.model_copy(update={"sha256": "0" * 64})
    assert_engine_error("asset_integrity_failed", lambda: service.import_asset("alice", wrong))
    asset = service.import_asset("alice", candidate)
    assert service.import_asset("alice", candidate) == asset
    assert_engine_error("asset_import_conflict", lambda: service.import_asset("alice", candidate.model_copy(update={"rights": "changed"})))
    staged_video = service.stage_bytes("alice", b"not real video", "video/mp4")
    assert_engine_error("media_validator_missing", lambda: service.import_asset("alice", AssetCandidate(**staged_video, source="test", rights="self-created")))


def test_content_read_detects_same_size_tampering(setup_engine):
    engine, _ = setup_engine
    service = AssetService(engine)
    staged = service.stage_bytes("local-user", b'{"public":1}', "application/json")
    asset = service.import_asset("local-user", AssetCandidate(**staged, source="test", rights="self-created"))
    path = service.content_path("local-user", asset.asset_id)
    path.write_bytes(b'{"public":2}')
    with pytest.raises(EngineError):
        service.content_path("local-user", asset.asset_id)


@pytest.mark.parametrize("name", ["../escape", "C:/Windows/file", "folder\\file", "..", "a:b", "/absolute"])
def test_asset_storage_denies_path_escape(setup_engine, name):
    engine, _ = setup_engine
    assert_engine_error("path_denied", lambda: AssetService(engine)._path("Staging", name))


def test_fake_secret_driver_exception_is_not_persisted(setup_engine):
    engine, _ = setup_engine
    configure(engine)
    accepted, lease = lease_and_step(engine)
    fake = "sk-" + "T1FakeSecretOnly" * 4

    def driver(p, s):
        raise RuntimeError(fake)

    observed = OperationExecutor(engine).execute(lease, intent(), driver)
    assert fake not in observed.model_dump_json()
    assert fake not in engine.get_production("local-user", accepted.production_id).model_dump_json()
    with engine.db.connect() as connection:
        assert fake not in "\n".join(connection.iterdump())
    handle = SecretHandle(fake)
    assert fake not in str(handle) and fake not in repr(handle)
    assert handle.reveal() == fake


def test_credentials_only_authorized_environment_namespace(monkeypatch):
    monkeypatch.setenv("VIDEO_CREATOR_SECRET_T1_FAKE", "fake-credential-never-transmitted")
    vault = CredentialVault()
    assert vault.resolve("env:VIDEO_CREATOR_SECRET_T1_FAKE").reveal() == "fake-credential-never-transmitted"
    assert_engine_error("credential_ref_denied", lambda: vault.resolve("env:PATH"))
    assert_engine_error("credential_ref_denied", lambda: vault.resolve("file:C:/secret"))


def test_money_and_usage_are_fixed_point_and_invalid_usage_stays_unknown():
    with pytest.raises(ValidationError):
        Money(amount=0.2)
    assert calculate_usage_cost({"prompt_tokens": 100, "completion_tokens": 10}, DEEPSEEK_FLASH_RULE).amount == Decimal("0.00028")
    assert_engine_error("usage_incomplete", lambda: calculate_usage_cost({"prompt_tokens": 100}))
    assert_engine_error("usage_invalid", lambda: calculate_usage_cost({"prompt_tokens": 100, "completion_tokens": True}))


@pytest.mark.asyncio
async def test_api_permissions_revision_error_redaction_and_range(setup_engine):
    engine, _ = setup_engine
    token = "T1-session-fake-only-" + "x" * 40
    app = create_app(engine, token, allowed_origins=("http://127.0.0.1:1420",))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1", headers={"Authorization": "Bearer " + token}) as client:
        assert (await client.get("/api/v1/health")).status_code == 200
        assert (await client.get("/api/v1/health", headers={"Origin": "https://evil.invalid"})).status_code == 403
        assert (await client.get("/api/v1/health", headers={"Host": "evil.invalid"})).status_code == 400
        fake = "sk-" + "T1FakeSecretOnly" * 4
        invalid = await client.post("/api/v1/productions", json={"goal": fake}, headers={"Idempotency-Key": "secret"})
        assert invalid.status_code == 422 and fake not in invalid.text
        project = (await client.post("/api/v1/projects", json={"name": "public"})).json()
        project_id = project["project_id"]
        assert (await client.put(f"/api/v1/projects/{project_id}", json={"name": "changed"}, headers={"If-Match": '"1"'})).status_code == 200
        assert (await client.put(f"/api/v1/projects/{project_id}", json={"name": "stale"}, headers={"If-Match": '"1"'})).status_code == 409
        staged = (await client.post("/api/v1/assets/staging", content=b"abcdef", headers={"Content-Type": "text/plain"})).json()
        asset = (await client.post("/api/v1/assets/import", json={**staged, "source": "test", "rights": "self-created"})).json()
        download = await client.get(f"/api/v1/assets/{asset['asset_id']}/content", headers={"Range": "bytes=1-3"})
        assert download.status_code == 206 and download.content == b"bcd"
        assert download.headers["etag"] == '"' + hashlib.sha256(b"abcdef").hexdigest() + '"'
    async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1") as client:
        assert (await client.get("/api/v1/health")).status_code == 401
