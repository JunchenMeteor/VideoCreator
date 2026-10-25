"""Actual B11 service calls after trusted launch. No product top-level imports.

These are executable cases, not AST arity checks. They have not been run yet.
Fixture creative text is explicitly state evidence, never autonomous creation.
"""
import hashlib
import secrets
import time


def _request(ctx, goal):
    return ctx.contracts.ProductionRequest(goal=goal)


def _lease(ctx, name):
    accepted = ctx.engine.accept_production("local-user", name, _request(ctx, name))
    lease = ctx.engine.acquire_run("t19-worker", run_id=accepted.run_id)
    assert lease is not None, "a fresh complete legacy request must be queued"
    return accepted, lease


def _error(ctx, code, callback, *args, **kwargs):
    try:
        callback(*args, **kwargs)
    except ctx.EngineError as error:
        assert error.code == code, (error.code, code)
        return {"code": error.code, "status": error.status_code}
    raise AssertionError("expected actual domain refusal: " + code)


def project_idempotency(ctx):
    value = ctx.contracts.ProjectInput(name="T19-owned", goal="state fixture")
    first = ctx.engine.create_project("local-user", value, "T19-project-idem")
    repeat = ctx.engine.create_project("local-user", value, "T19-project-idem")
    assert first == repeat
    return {"project_id": first.project_id, "revision": first.revision}


def project_input_conflict(ctx):
    c = ctx.contracts
    first = ctx.engine.create_project("local-user", c.ProjectInput(name="first"), "T19-project-conflict")
    _error(ctx, "idempotency_conflict", ctx.engine.create_project, "local-user", c.ProjectInput(name="different"), "T19-project-conflict")
    assert ctx.engine.get_project("local-user", first.project_id) == first


def project_owner_boundary(ctx):
    first = ctx.engine.create_project("local-user", ctx.contracts.ProjectInput(name="owner boundary"))
    _error(ctx, "not_found", ctx.engine.get_project, "another-subject", first.project_id)


def project_revision_conflict(ctx):
    c = ctx.contracts
    first = ctx.engine.create_project("local-user", c.ProjectInput(name="revision1"))
    latest = ctx.engine.update_project("local-user", first.project_id, first.revision, c.ProjectInput(name="revision2"))
    _error(ctx, "revision_conflict", ctx.engine.update_project, "local-user", first.project_id, first.revision, c.ProjectInput(name="stale"))
    assert ctx.engine.get_project("local-user", first.project_id) == latest


def request_idempotency(ctx):
    request = _request(ctx, "T19 original immutable request")
    first = ctx.engine.accept_production("local-user", "T19-request-idem", request)
    repeat = ctx.engine.accept_production("local-user", "T19-request-idem", request)
    assert first == repeat
    detail = ctx.engine.get_production("local-user", first.production_id)
    assert detail.request.request_format_version == "0.2.0-candidate"
    assert detail.request.delivery_requirements.alignment_requirement == "utterance_verified"
    assert not detail.operations and detail.bundle_ref is None


def request_input_conflict(ctx):
    first = ctx.engine.accept_production("local-user", "T19-request-conflict", _request(ctx, "original"))
    _error(ctx, "idempotency_conflict", ctx.engine.accept_production, "local-user", "T19-request-conflict", _request(ctx, "changed"))
    assert ctx.engine.get_production("local-user", first.production_id).request.goal == "original"


def request_cross_version(ctx):
    ctx.engine.accept_production("local-user", "T19-version", _request(ctx, "version"))
    new = ctx.contracts.ProductionRequestV03(request_format_version="0.3.0-candidate", goal="version")
    _error(ctx, "idempotency_conflict", ctx.engine.accept_production, "local-user", "T19-version", new)


def v03_unconfigured_waits(ctx):
    c = ctx.contracts
    request = c.ProductionRequestV03(request_format_version="0.3.0-candidate", goal="unconfigured policy")
    first = ctx.engine.accept_production("local-user", "T19-unconfigured", request)
    detail = ctx.engine.get_production("local-user", first.production_id)
    assert str(detail.status) == "waiting_user"
    assert detail.request.delivery_requirements is None and not detail.operations and detail.bundle_ref is None
    assert ctx.engine.acquire_run("t19-unconfigured-worker", run_id=first.run_id) is None
    events = ctx.engine.events("local-user", first.run_id)
    assert any(event.event_type == "alignment_required" for event in events)
    assert ctx.engine.accept_production("local-user", "T19-unconfigured", request) == first


def unconfigured_authority_rejected(ctx):
    _error(ctx, "evidence_authority_unconfigured", ctx.engine.evidence_registry.administration_capability)


def missing_six_consumers(ctx):
    c, bundle, owner = ctx.contracts, ctx.bundle, ctx.bundle.principals.owner()
    _error(ctx, "not_found", bundle.content, owner, "absent-revision", "absent-artifact")
    _error(ctx, "not_found", bundle.semantic_page, owner, "absent-revision", None, 50)
    _error(ctx, "not_found", bundle.request_export, owner, "absent-revision", "T19-export", c.BundleExportRequest())
    _error(ctx, "not_found", bundle.export_status, owner, "absent-export")
    _error(ctx, "not_found", bundle.import_status, owner, "absent-import")
    request = c.BundleImportRequest(staging_id="absent-staging", archive_sha256="0" * 64,
        expected_origin_ref=c.BundleRef(instance_id="absent-origin", bundle_id="absent-bundle", bundle_revision_id="absent-revision", manifest_sha256="0" * 64),
        project_id="absent-project")
    _error(ctx, "not_found", bundle.import_bundle, owner, "T19-import", request)


def altered_principal_rejected(ctx):
    owner = ctx.bundle.principals.owner()
    # Unique actual internal model; no Test DTO and no new registered authority.
    wrong = ctx.AccessContext(owner.subject_id, "different-installation", owner.project_ids,
        owner.operations, owner.purposes, owned_projects=owner.owned_projects)
    _error(ctx, "principal_scope_changed", ctx.bundle.content, wrong, "absent", "absent")


def expired_recipient_rejected(ctx):
    credential = secrets.token_urlsafe(32)
    registration = ctx.PrincipalRegistration("T19-expired-recipient", frozenset(), frozenset({"bundle.read"}),
        frozenset({"playback"}), expires_at_us=ctx.engine.clock() - 1)
    ctx.bundle.principals.register(registration, credential)
    _error(ctx, "principal_expired", ctx.bundle.principals.authenticate, credential, ctx.engine.clock())


def semantic_cursor_guard(ctx):
    owner = ctx.bundle.principals.owner()
    _error(ctx, "invalid_cursor", ctx.bundle.semantic_page, owner, "absent", "-1", 50)
    _error(ctx, "invalid_cursor", ctx.bundle.semantic_page, owner, "absent", None, 101)


def real_wall_lease_fencing(ctx):
    accepted = ctx.engine.accept_production("local-user", "T19-fence", _request(ctx, "real wall clock fencing"))
    old = ctx.engine.acquire_run("t19-old-worker", lease_seconds=1, run_id=accepted.run_id)
    assert old is not None
    while ctx.engine.clock() <= old.expires_at_us:
        time.sleep(0.02)
    new = ctx.engine.acquire_run("t19-new-worker", lease_seconds=10, run_id=accepted.run_id)
    assert new is not None and new.fencing_token > old.fencing_token
    _error(ctx, "stale_lease", ctx.engine.begin_step, old, "T19-expired-step", "1" * 64)
    ctx.engine.begin_step(new, "T19-current-step", "2" * 64)
    ctx.engine.complete_step(new, "T19-current-step", result_json={"test_evidence": "state only"})
    ctx.engine.release_run(new)
    return {"old_expiry_us": old.expires_at_us, "new_fence": new.fencing_token, "wall_observed_us": ctx.engine.clock()}


def pause_and_cancel_boundaries(ctx):
    accepted = ctx.engine.accept_production("local-user", "T19-pause", _request(ctx, "pause"))
    ctx.engine.set_paused("local-user", accepted.run_id, True)
    assert ctx.engine.acquire_run("t19-paused-worker", run_id=accepted.run_id) is None
    ctx.engine.set_paused("local-user", accepted.run_id, False)
    lease = ctx.engine.acquire_run("t19-resumed-worker", run_id=accepted.run_id)
    assert lease is not None
    ctx.engine.release_run(lease)
    ctx.engine.cancel_production("local-user", accepted.production_id)
    assert ctx.engine.acquire_run("t19-cancel-worker", run_id=accepted.run_id) is None
    assert not ctx.engine.get_production("local-user", accepted.production_id).operations


def review_cannot_install_capability(ctx):
    request = ctx.contracts.ProductionRequestV03(request_format_version="0.3.0-candidate", goal="review is not policy installation")
    accepted = ctx.engine.accept_production("local-user", "T19-blocker-review", request)
    revisions = ctx.engine.creative_revisions("local-user", accepted.production_id)
    blocker = next(r for r in revisions if r.kind == "quality" and r.body.get("code") == "alignment_required")
    decision = ctx.contracts.ReviewDecision(target_revision_id=blocker.revision_id, action="approve")
    _error(ctx, "alignment_required", ctx.engine.submit_decision, "local-user", accepted.run_id, "T19-approve-blocker", decision)
    assert str(ctx.engine.get_production("local-user", accepted.production_id).status) == "waiting_user"


def worker_presence_authority(ctx):
    worker = ctx.WorkerService(ctx.engine)
    resource = ctx.resource_manifest_sha256
    worker_id = worker.register_presence(resource)
    try:
        assert worker.connected()
        _error(ctx, "worker_slot_busy", worker.register_presence, resource)
        worker.heartbeat_presence(worker_id)
        assert worker.connected()
    finally:
        worker.close_presence(worker_id)
    assert not worker.connected()
    return {"worker_id": worker_id, "scope": "real same-process WorkerService presence; not independent OS Worker lifetime"}


def worker_binding_immutable(ctx):
    accepted, lease = _lease(ctx, "T19-worker-binding")
    worker = ctx.WorkerService(ctx.engine)
    first = worker.bind_execution(lease, ctx.resource_manifest_sha256)
    assert worker.read_binding(lease) == first
    assert worker.bind_execution(lease, ctx.resource_manifest_sha256) == first
    other_hash = hashlib.sha256(b"different test resource identity").hexdigest()
    _error(ctx, "execution_binding_conflict", worker.bind_execution, lease, other_hash)
    assert worker.read_binding(lease) == first
    ctx.engine.release_run(lease)


def actual_factory_missing_creative(ctx):
    _, lease = _lease(ctx, "T19-factory-missing-input")
    producer = ctx.bundle._t18_runtime_handles["producer"]
    _error(ctx, "creative_versions_missing", producer, lease, video_asset_id="absent-video",
        narration_asset_id="absent-narration", mixed_asset_id="absent-mix", cover_asset_id="absent-cover", asr_route_id="absent-route")
    detail = ctx.engine.get_production("local-user", ctx.bundle.context(lease).production_id)
    assert not detail.operations and detail.bundle_ref is None
    ctx.engine.release_run(lease)


SERVICE_CASES = [
    ("project-idempotency", project_idempotency), ("project-input-conflict", project_input_conflict),
    ("project-owner-boundary", project_owner_boundary), ("project-revision-conflict", project_revision_conflict),
    ("request-idempotency", request_idempotency), ("request-input-conflict", request_input_conflict),
    ("request-cross-version", request_cross_version), ("v03-unconfigured-waits", v03_unconfigured_waits),
    ("unconfigured-authority-rejected", unconfigured_authority_rejected), ("missing-six-consumers", missing_six_consumers),
    ("altered-principal-rejected", altered_principal_rejected), ("expired-recipient-rejected", expired_recipient_rejected),
    ("semantic-cursor-guard", semantic_cursor_guard), ("real-wall-lease-fencing", real_wall_lease_fencing),
    ("pause-and-cancel-boundaries", pause_and_cancel_boundaries), ("review-cannot-install-capability", review_cannot_install_capability),
    ("worker-presence-authority", worker_presence_authority), ("worker-binding-immutable", worker_binding_immutable),
    ("actual-factory-missing-creative", actual_factory_missing_creative),
]
