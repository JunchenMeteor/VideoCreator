"""Real service/HTTP/export/import/fault drivers; no fixture database writes."""
from __future__ import annotations

import copy
import hashlib
import io
import json
import sqlite3
import time
import zipfile
from dataclasses import replace

from t21_runtime import CaseBlocked


def readonly_counts(ctx, run_id):
    with sqlite3.connect(ctx.engine.db.path.as_uri() + "?mode=ro", uri=True) as con:
        con.execute("BEGIN")
        row = con.execute("SELECT status,worker_id,lease_until_us,fencing_token FROM runs WHERE id=?", (run_id,)).fetchone()
        operations = con.execute("SELECT id,status,settled,actual_units FROM operations WHERE run_id=? ORDER BY id", (run_id,)).fetchall()
        steps = con.execute("SELECT step_key,status,result_json FROM steps WHERE run_id=? ORDER BY step_key", (run_id,)).fetchall()
        bundles = con.execute("SELECT revision_id,status,manifest_sha256 FROM bundle_revisions WHERE run_id=? ORDER BY revision_id", (run_id,)).fetchall()
    return {"run": row, "operations": operations, "steps": steps, "bundles": bundles}


def exact_error(ctx, codes, callback):
    try:
        callback()
    except ctx.EngineError as error:
        assert error.code in codes
        return {"code": error.code, "status": error.status_code}
    raise AssertionError("actual service accepted forbidden input")


def immutable_expiring_revision(ctx):
    fixture, manifest, original = ctx.publication("T15-20")
    handles = [ctx.bundle.content(ctx.bundle.principals.owner(), manifest.bundle_revision_id, a.artifact_id, "derivative") for a in manifest.artifacts]
    expected = [(h.path, h.sha256, h.path.read_bytes()) for h in handles]
    expires = fixture["rights_expires_at_us"]
    assert ctx.engine.clock() < expires <= ctx.engine.clock() + 30_000_000
    ctx.wait(lambda: ctx.engine.clock() >= expires)
    denied = exact_error(ctx, {"bundle_rights_denied"}, lambda: ctx.bundle.semantic_page(ctx.bundle.principals.owner(), manifest.bundle_revision_id))
    for path, sha, raw in expected:
        assert path.read_bytes() == raw and hashlib.sha256(raw).hexdigest() == sha
    # Actual revision source facts remain fixed even when indexing access expires.
    return {"immutable_manifest_sha256": hashlib.sha256(original).hexdigest(), "current_index_refusal": denied}


def principal_payload_boundary(ctx):
    fixture, manifest, _ = ctx.publication("T15-21")
    owner = ctx.bundle.principals.owner()
    spoofed = replace(owner, subject_id=fixture["foreign_subject"])
    rejected = exact_error(ctx, {"principal_scope_changed", "principal_unconfigured"}, lambda: ctx.bundle.get_manifest(spoofed, manifest.bundle_revision_id))
    response = ctx.http().request("POST", "/v1/productions", json=dict(fixture["request"], owner="local-user"), authenticated=False)
    assert response.status in {401, 403} and not response.json().get("production_id")
    return {"service_actor_refusal": rejected, "http_status": response.status}


def pre_content_authorization(ctx):
    fixture, manifest, _ = ctx.publication("T15-22")
    api = ctx.http()
    results = []
    for endpoint in fixture["protected_paths"]:
        for headers in ({"Range": "bytes=0-1"}, {"If-None-Match": fixture["manifest_etag"]}):
            result = api.request("GET", endpoint, headers=headers, authenticated=False)
            assert result.status in {401, 403, 404} and result.status not in {200, 206, 304}
            envelope = ctx.c.ErrorEnvelope.model_validate(result.json())
            results.append({"path": endpoint, "status": result.status, "code": envelope.code})
    assert len(results) >= 6
    return {"actual_authorization_before_read": results}


def real_grant_expiry_revoke(ctx):
    fixture, manifest, _ = ctx.publication("T15-23")
    owner = ctx.bundle.principals.owner()
    recipient = ctx.bundle.principals.principal(fixture["recipient_id"], ctx.engine.clock())
    request = ctx.c.BundleGrantRequest(recipient_id=fixture["recipient_id"], artifact_ids=(fixture["artifact_id"],),
        allow_semantic_text=False, purposes=("playback",), expires_at_us=ctx.engine.clock() + 500_000)
    grant = ctx.bundle.create_grant(owner, manifest.bundle_revision_id, "T21-short-grant", request)
    assert grant.artifact_ids == request.artifact_ids and grant.purposes == request.purposes
    ctx.bundle.content(recipient, manifest.bundle_revision_id, fixture["artifact_id"], "playback")
    ctx.wait(lambda: ctx.engine.clock() >= grant.expires_at_us)
    expired = exact_error(ctx, {"bundle_scope_denied", "principal_expired"}, lambda: ctx.bundle.content(recipient, manifest.bundle_revision_id, fixture["artifact_id"], "playback"))
    fresh = request.model_copy(update={"expires_at_us": ctx.engine.clock() + 1_000_000})
    active = ctx.bundle.create_grant(owner, manifest.bundle_revision_id, "T21-revoke-grant", fresh)
    revoked = ctx.bundle.revoke_grant(owner, active.grant_id)
    assert revoked.revoked_at_us is not None
    refused = exact_error(ctx, {"bundle_scope_denied"}, lambda: ctx.bundle.content(recipient, manifest.bundle_revision_id, fixture["artifact_id"], "playback"))
    return {"expiry": expired, "revocation": refused}


def real_rights_limit(ctx):
    fixture, manifest, _ = ctx.publication("T15-24")
    owner = ctx.bundle.principals.owner()
    expected = ctx.bound_json(fixture["independent_rights_oracle"])
    assert [r.model_dump(mode="json") for r in manifest.rights] == expected["rights_snapshots"]
    denied = exact_error(ctx, {"bundle_rights_denied"}, lambda: ctx.bundle.content(owner, manifest.bundle_revision_id, fixture["restricted_artifact_id"], "redistribution"))
    assert ctx.bundle.get_manifest(owner, manifest.bundle_revision_id, "playback").artifacts == manifest.artifacts
    return {"actual_rights_restriction": denied, "artifact_count_unchanged": len(manifest.artifacts)}


def unsettled_no_publish(ctx):
    fixture, lease, preparation = ctx.preparation("T15-25")
    try:
        before = readonly_counts(ctx, lease.run_id)
        assert any(row[1] in {"unknown", "failed"} or row[2] == 0 for row in before["operations"])
        manifest = ctx.c.parse_bundle_manifest(ctx.bound_json(fixture["manifest_document"]))
        denied = exact_error(ctx, {"operation_incomplete"},
            lambda: ctx.bundle.verify(lease, preparation.preparation_id, manifest))
        after = readonly_counts(ctx, lease.run_id)
        assert before["bundles"] == after["bundles"] and not any(row[1] == "published" for row in after["bundles"])
        return {"actual_rejection": denied}
    finally:
        ctx.engine.release_run(lease)


def actual_cancel_deadline(ctx):
    fixture = ctx.fixture("T15-26")
    profile = ctx.fixture("ASR-runtime")
    from pathlib import Path
    from video_creator.providers.local_asr import AsrProcessError, run_local_asr
    request = ctx.bound_json(fixture["request_document"])
    observations = []
    for mode in ("cancel", "deadline"):
        start = time.monotonic()
        try:
            run_local_asr(request, python_executable=Path(profile["python_executable"]), runtime_root=Path(profile["runtime_root"]),
                deadline_monotonic=start + fixture["deadline_seconds"] if mode == "deadline" else None,
                cancel=(lambda: time.monotonic() - start > fixture["cancel_after_seconds"]) if mode == "cancel" else None)
        except AsrProcessError as error:
            assert error.code == ("asr_cancelled" if mode == "cancel" else "asr_deadline_exceeded")
            assert error.evidence.get("pid") and error.evidence["child_terminal"] and error.evidence["tree_empty"]
            observations.append({"mode": mode, "pid": error.evidence["pid"], "code": error.code})
        else:
            raise AssertionError("actual cancellation/deadline did not terminate the worker")
    if not fixture.get("uncertain_cleanup_injection"):
        raise CaseBlocked("actual_cleanup_unknown_fault", "controlled actual cleanup-query failure fixture/hook remains required; certain cleanup alone is insufficient")
    result = ctx.host().run_fault_role("asr_cleanup_unknown", fixture["uncertain_cleanup_injection"])
    assert result["operation_status"] == "unknown" and result["settled"] is False
    return {"actual_controlled_terminations": observations, "unknown_cleanup": result}


def actual_publish_crash(ctx, case_id="T15-27"):
    fixture = ctx.fixture(case_id)
    host = ctx.host()
    phase = "manifest_file_before_commit" if case_id == "T15-27" else "published_return_before_flow"
    original = host.launch_fault_role("bundle_publisher", ctx.engine.instance_id, phase)
    identity = original.actual_identity()
    marker = original.wait_phase(phase, timeout=fixture["window_seconds"])
    assert marker["run_id"] == fixture["run_id"] and marker["file_sha256"]
    before = readonly_counts(ctx, fixture["run_id"])
    killed = host.kill_owned_job(original, identity)
    assert killed.forced and killed.job_active_processes == 0
    recovered = host.launch_role("worker", ctx.engine.instance_id)
    try:
        after = ctx.wait(lambda: _published_counts(ctx, fixture["run_id"]), seconds=fixture["recovery_seconds"])
        assert len([row for row in after["bundles"] if row[1] == "published"]) == 1
        assert after["operations"] == before["operations"], "crash recovery re-generated or charged an original operation"
        observed_file = ctx.bundle.manifest_content(ctx.bundle.principals.owner(), marker["bundle_revision_id"], "derivative")
        assert hashlib.sha256(observed_file.path.read_bytes()).hexdigest() == marker["file_sha256"]
        return {"phase": phase, "forced_original": killed.to_evidence(), "recovered_bundle_revision_id": marker["bundle_revision_id"]}
    finally:
        final = host.close_owned(recovered)
        assert final.actual_exit == 0 and not final.forced and final.job_active_processes == 0


def _published_counts(ctx, run_id):
    result = readonly_counts(ctx, run_id)
    return result if any(row[1] == "published" for row in result["bundles"]) else None


def concurrent_bundle_commands(ctx):
    fixture = ctx.fixture("T15-29")
    from concurrent.futures import ThreadPoolExecutor
    request = ctx.c.parse_production_request(fixture["request"])
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: ctx.engine.accept_production("local-user", "T21-concurrent-exact", request), range(2)))
    assert results[0] == results[1]
    changed = request.model_copy(update={"goal": request.goal + " changed"})
    rejected = exact_error(ctx, {"idempotency_conflict"}, lambda: ctx.engine.accept_production("local-user", "T21-concurrent-exact", changed))
    # Actual package duplicate publication still needs the real producer branch.
    result = ctx.host().run_fault_role("concurrent_bundle_publish", fixture)
    assert result["published_revision_count"] == 1 and result["bundle_success_event_count"] == 1
    return {"production_id": results[0].production_id, "conflict": rejected, "actual_publisher_counts": result}


def actual_export(ctx, case_id="T15-30", projection=False):
    fixture, manifest, _ = ctx.publication(case_id)
    owner = ctx.bundle.principals.owner()
    body = fixture.get("export_request", {}) if projection else {}
    request = ctx.c.BundleExportRequest.model_validate(body)
    job = ctx.bundle.request_export(owner, manifest.bundle_revision_id, "T21-export-" + case_id, request)
    assert ctx.bundle.export_status(owner, job.export_id).export_id == job.export_id
    ctx.bundle.start_exports()
    try:
        complete = ctx.wait(lambda: _ready_export(ctx, owner, job.export_id))
        handle = ctx.bundle.export_content(owner, job.export_id)
        raw = handle.path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == complete.archive_sha256
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            names = archive.namelist()
            assert len(names) == len(set(names))
            if not projection:
                assert archive.read("bundle.manifest.json") == ctx.bundle.manifest_content(owner, manifest.bundle_revision_id, "export").path.read_bytes()
                for artifact in manifest.artifacts:
                    assert hashlib.sha256(archive.read(artifact.relative_path)).hexdigest() == artifact.sha256
            else:
                delivery = json.loads(archive.read("delivery.manifest.json"))
                assert delivery["parent_bundle_ref"] == job.bundle_ref.model_dump(mode="json")
                for item in delivery["artifacts"]:
                    assert hashlib.sha256(archive.read(item["relative_path"])).hexdigest() == item["sha256"]
        return {"job": job, "manifest": manifest, "raw": raw, "archive_sha256": complete.archive_sha256}
    finally:
        ctx.bundle.stop_exports()


def _ready_export(ctx, actor, identifier):
    observed = ctx.bundle.export_status(actor, identifier)
    if observed.status == "failed":
        raise AssertionError("actual export failed: " + str(observed.error_code))
    return observed if observed.status == "ready" else None


def malicious_archives(ctx, case_id="T15-32"):
    fixture = ctx.fixture(case_id)
    expected_variants = {"traversal", "absolute", "backslash", "drive", "link", "duplicate_case", "duplicate", "missing", "extra"}
    if case_id == "T15-33":
        expected_variants = {"compressed_limit", "uncompressed_limit", "entry_count", "entry_size"}
    assert {item["kind"] for item in fixture["archives"]} == expected_variants
    results = []
    for item in fixture["archives"]:
        raw = ctx.bound_bytes(item["archive"])
        staged = ctx.bundle.assets.stage_bytes("local-user", raw, "application/zip")
        request = ctx.c.BundleImportRequest(staging_id=staged["staging_id"], archive_sha256=staged["sha256"],
            expected_origin_ref=ctx.c.BundleRef.model_validate(fixture["origin_ref"]), project_id=fixture["project_id"])
        results.append(exact_error(ctx, set(item["expected_codes"]), lambda: ctx.bundle.import_bundle(ctx.bundle.principals.owner(), "T21-bad-" + item["kind"], request)))
    return {"actual_import_rejections": results}


def second_instance_import(ctx, case_id="T15-34"):
    exported = actual_export(ctx, case_id)
    second = ctx.second()
    c, owner = second.c, second.bundle.principals.owner()
    project = second.engine.create_project("local-user", c.ProjectInput(name="T21-independent-import"))
    staged = second.bundle.assets.stage_bytes("local-user", exported["raw"], "application/zip")
    request = c.BundleImportRequest(staging_id=staged["staging_id"], archive_sha256=exported["archive_sha256"],
        expected_origin_ref=exported["job"].bundle_ref, project_id=project.project_id)
    receipt = second.bundle.import_bundle(owner, "T21-second-original", request)
    imported = second.bundle.import_manifest(owner, receipt.import_id, "derivative")
    assert imported == exported["manifest"] and receipt.origin_bundle_ref == exported["job"].bundle_ref
    assert second.bundle.import_manifest_content(owner, receipt.import_id).path.read_bytes() == ctx.bundle.manifest_content(ctx.bundle.principals.owner(), imported.bundle_revision_id).path.read_bytes()
    assert receipt.evidence_trust_status == "origin_snapshot_only" and receipt.execution_qualification_inherited is False
    for artifact in imported.artifacts:
        handle = second.bundle.import_content(owner, receipt.import_id, artifact.artifact_id, "derivative")
        assert hashlib.sha256(handle.path.read_bytes()).hexdigest() == artifact.sha256
    if case_id == "T15-35":
        job = second.bundle.request_import_export(owner, receipt.import_id, "T21-reexport-original", c.BundleExportRequest())
        second.bundle.start_exports()
        try:
            complete = ctx.wait(lambda: _ready_export(second, owner, job.export_id))
            raw = second.bundle.export_content(owner, job.export_id).path.read_bytes()
            assert hashlib.sha256(raw).hexdigest() == complete.archive_sha256
        finally:
            second.bundle.stop_exports()
    return {"second_instance_id": second.engine.instance_id, "import_id": receipt.import_id, "original_revision": imported.bundle_revision_id}


def actual_contract_transports(ctx):
    fixture = ctx.fixture("T15-36")
    http = ctx.http().request("GET", "/openapi.json")
    assert http.status == 200
    actual = http.json()
    assert actual == ctx.bound_json(fixture["generated_openapi"])
    assert "ErrorEnvelope" in actual["components"]["schemas"]
    from t21_process_cases import actual_mcp_host, unconfigured_mcp_host
    return {"openapi": "actual HTTP equal frozen generation", "configured_mcp": actual_mcp_host(ctx), "unconfigured_mcp": unconfigured_mcp_host(ctx)}


def autonomous_once(ctx):
    fixture = ctx.fixture("T15-37")
    if fixture.get("upstream_route") != "real_autonomous_goal_to_masters":
        raise CaseBlocked("W14_autonomous_upstream", "registered 4-master packager/gate0 render is not goal-to-video creation")
    request = fixture["request"]
    forbidden = {"video_asset_id", "narration_asset_id", "mixed_asset_id", "cover_asset_id", "prebuilt_masters"}
    assert not forbidden.intersection(request)
    api = ctx.http()
    first = api.request("POST", "/v1/productions", json=request, headers={"Idempotency-Key": "T21-autonomous-once"})
    assert first.status == 202
    accepted = ctx.c.ProductionAccepted.model_validate(first.json())
    api.disconnect_client()  # This must not stop the separate persistent worker.
    def finished():
        detail = ctx.engine.get_production("local-user", accepted.production_id)
        return detail if detail.bundle_ref else None
    detail = ctx.wait(finished, seconds=fixture["allowed_duration_seconds"])
    manifest = ctx.bundle.get_manifest(ctx.bundle.principals.owner(), detail.bundle_ref.bundle_revision_id, "derivative")
    assert len(manifest.requested_outputs) == 8
    trace = ctx.bound_json(fixture["independent_orchestration_audit"])
    assert trace["production_id"] == accepted.production_id and trace["goal_request_sha256"] == accepted.request_sha256
    assert trace["real_model_calls"] > 0 and trace["real_successful_delegations"] > 0
    assert trace["manually_supplied_master_assets"] == []
    return {"actual_autonomous_revision": manifest.bundle_revision_id, "orchestration_audit_sha256": fixture["independent_orchestration_audit"]["sha256"]}


def real_three_os(ctx):
    fixture = ctx.fixture("T15-38")
    reports = [ctx.bound_json(record) for record in fixture["independent_installed_OS_receipts"]]
    assert {report["os"] for report in reports} == {"windows", "macos", "linux"}
    for report in reports:
        assert report["clean_install_actual"] and report["offline_owned_resources_verified"]
        assert report["actual_local_accountless_use"] and report["horizontal_decode"] and report["vertical_decode"]
        assert report["backup_import_restored"] and report["license_inventory_sha256"]
        assert report["actual_signed_build_sha256"] == fixture["expected_builds"][report["os"]]
    return {"actual_OS_receipts": [record["sha256"] for record in fixture["independent_installed_OS_receipts"]]}
