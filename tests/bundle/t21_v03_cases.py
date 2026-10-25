"""Versioned registry/material/strict bundle consumers using unique Backend DTOs."""
from __future__ import annotations

import copy
import sqlite3
import time

from t21_runtime import CaseBlocked


def fixed_request_versions(ctx):
    fixture = ctx.fixture("V03-01")
    legacy = ctx.c.parse_production_request(fixture["legacy_request"])
    modern = ctx.c.parse_production_request(fixture["v03_request"])
    assert legacy.request_format_version in {None, "0.2.0-candidate"} and modern.request_format_version == "0.3.0-candidate"
    first = ctx.engine.accept_production("local-user", "T21-version-bound", legacy)
    assert ctx.engine.accept_production("local-user", "T21-version-bound", legacy) == first
    rejected = ctx.error("idempotency_conflict", ctx.engine.accept_production, "local-user", "T21-version-bound", modern)
    detail = ctx.engine.get_production("local-user", first.production_id)
    assert detail.request.request_format_version == legacy.request_format_version
    return {"production_id": first.production_id, "actual_version_conflict": rejected}


def three_scopes_null(ctx, case_id="V03-02"):
    _, manifest, _ = ctx.publication(case_id)
    actual = ctx.transcript(manifest)
    precision = actual.alignment.precision
    assert precision.evaluation_scope == "per_work_reference_measurement" and precision.status == "not_measured"
    assert all(getattr(precision, name) is None for name in ("sample_count", "p95_error_us", "reference_ref", "measurement_report_locator", "criterion_version_ref"))
    assert not any(set(a.roles) & {"precision_reference", "precision_evaluation"} for a in manifest.artifacts)
    work = ctx.document(manifest, "work_alignment_validation", "WorkAlignmentValidationReport")[1]
    assert work.evaluation_scope == "work_runtime_validation" and not work.source_gaps
    benchmark_role = "method_benchmark_reference" if any("method_benchmark_reference" in a.roles for a in manifest.artifacts) else "method_benchmark"
    model = "MethodBenchmarkReference" if benchmark_role.endswith("reference") else "MethodBenchmarkReport"
    benchmark = ctx.document(manifest, benchmark_role, model)[1]
    scope = benchmark.origin_report_ref.evaluation_scope if benchmark_role.endswith("reference") else benchmark.evaluation_scope
    assert scope == "capability_benchmark"
    return {"precision": "null_not_measured", "work_scope": work.evaluation_scope, "benchmark_scope": scope}


def actual_qualification_scope(ctx):
    fixture, lease = ctx.ordinary_lease("V03-03")
    try:
        registry = ctx.engine.evidence_registry
        ref = ctx.c.EvidencePolicyRevisionRef.model_validate(fixture["policy_ref"])
        execution = ctx.c.AlignmentExecutionIdentity.model_validate(ctx.bound_json(fixture["actual_execution_identity"]))
        values = fixture["actual_work_scope"]
        actual = registry.verify("local-user", fixture["project_id"], ref, execution, values["language"], values["media_type"], values["duration_us"], tuple(values["transformations"]))
        assert actual.qualification.execution_identity == execution
        rejected = []
        for field, value in fixture["out_of_scope_identity_values"].items():
            changed = execution.model_copy(update={field: value})
            rejected.append(ctx.error("evidence_execution_out_of_scope", registry.verify, "local-user", fixture["project_id"], ref, changed,
                values["language"], values["media_type"], values["duration_us"], tuple(values["transformations"])))
        assert {"compute_type", "device", "operating_system", "architecture", "resource_manifest_sha256"} <= set(fixture["out_of_scope_identity_values"])
        return {"actual_qualification": actual.qualification.qualification_id, "identity_refusals": rejected}
    finally:
        ctx.engine.release_run(lease)


def real_untrusted_install_refusal(ctx):
    fixture = ctx.fixture("V03-04")
    from video_creator.domain.evidence import EvidenceApproval
    document = ctx.c.MethodQualificationRef.model_validate(ctx.bound_json(fixture["qualification_document"]))
    benchmark = ctx.c.MethodBenchmarkReport.model_validate(ctx.bound_json(fixture["benchmark_document"]))
    approval = EvidenceApproval.model_validate(ctx.bound_json(fixture["approval_document"]))
    # No Test-issued capability/signature, even if payload says approved.
    rejected = ctx.error("evidence_administration_denied", ctx.engine.evidence_registry.install, None, document, benchmark, approval)
    return {"actual_registry_refusal": rejected}


def signed_revoke_during_publish(ctx):
    fixture = ctx.fixture("V03-05")
    host = ctx.host()
    # Role runs real signed revocation and real publisher against one SQLite
    # writer. It cannot replace the transaction with a fake snapshot.
    result = host.run_fault_role("signed_revoke_publish_order", fixture)
    assert result["revocation_first"]["published_count"] == 0
    assert result["publication_first"]["published_count"] == 1
    assert result["publication_first"]["original_manifest_sha256"] == result["publication_first"]["after_manifest_sha256"]
    assert result["old_verification_token_accepted"] is False
    return result


def registry_restart_backup(ctx):
    fixture = ctx.fixture("V03-06")
    result = ctx.host().run_fault_role("actual_registry_restart_backup", fixture)
    assert result["first_process_identity"] != result["restored_process_identity"]
    assert result["same_installation_id"] and result["registry_revision_after"] >= result["known_revocation_revision"]
    assert not result["replayed_revocation_revived"] and not result["different_body_same_identity_accepted"]
    assert result["budget_before"] == result["budget_after"] and result["operation_ids_before"] == result["operation_ids_after"]
    return result


def actual_max_N(ctx, case_id="V03-07"):
    fixture = ctx.fixture(case_id)
    from video_creator.application.evidence import validate_benchmark
    positive = ctx.c.MethodBenchmarkReport.model_validate(ctx.bound_json(fixture["independent_actual_benchmark"]))
    validate_benchmark(positive)
    # Different corpus files can reuse local IDs; qualification population is
    # independently indexed per audio in the public report, never deduplicated.
    from video_creator.application.alignment_math import unit_errors
    errors = [error for audio in positive.audios for error in unit_errors(audio.predicted_units, audio.reference_units, audio.boundaries, audio.duration_us)]
    rank = (95 * len(errors) + 99) // 100
    assert positive.sample_count == len(errors) and positive.p95_error_us == sorted(errors)[rank - 1] <= 200_000
    rejected = []
    for record in fixture["invalid_full_population_reports"]:
        body = ctx.bound_json(record)
        try:
            bad = ctx.c.MethodBenchmarkReport.model_validate(body)
            validate_benchmark(bad)
        except (ValueError, ctx.EngineError) as error:
            rejected.append(type(error).__name__)
        else:
            raise AssertionError("actual Backend accepted 2N/duplicate/missing population evidence")
    assert rejected
    return {"actual_N": len(errors), "actual_p95_us": positive.p95_error_us, "rejected": len(rejected)}


def real_allocation_persistence(ctx):
    fixture, lease, preparation = ctx.preparation("V03-09")
    try:
        first = ctx.bundle.material_allocation(lease, preparation.preparation_id, fixture["artifact_id"])
        assert ctx.bundle.material_allocation(lease, preparation.preparation_id, fixture["artifact_id"]) == first
        fields = first.__dict__
        assert not {"sha256", "size", "decoded", "validated"}.intersection(fields)
        result = ctx.host().run_fault_role("allocation_restart_read", {"fixture": fixture, "expected_material_id": first.material_id})
        assert result["material_id"] == first.material_id and result["allocation_ready_claim"] is False
        return {"original_allocation_id": first.material_id, "restart": result}
    finally:
        ctx.engine.release_run(lease)


def allocation_old_fence(ctx):
    fixture, old, preparation = ctx.preparation("V03-10")
    target = ctx.bundle.material_allocation(old, preparation.preparation_id, fixture["artifact_id"])
    before = ctx.bundle.read_material(old, preparation.preparation_id, target.material_id)
    # Real wall-clock lease expiry, never SQL/fake clock mutation.
    ctx.wait(lambda: ctx.engine.clock() >= old.expires_at_us, seconds=65)
    new = ctx.engine.acquire_run("t21-new-fence", run_id=old.run_id)
    assert new is not None and new.fencing_token > old.fencing_token
    try:
        rejection = ctx.error("stale_lease", ctx.bundle.stage_material, old, preparation.preparation_id, fixture["artifact_id"], before)
        assert ctx.bundle.read_material(new, preparation.preparation_id, target.material_id) == before
        return {"old_fence": old.fencing_token, "new_fence": new.fencing_token, "actual_rejection": rejection}
    finally:
        ctx.engine.release_run(new)


def actual_material_dag(ctx):
    fixture, manifest, _ = ctx.publication("V03-11")
    from t16_assertions import assert_acyclic_edges
    assert_acyclic_edges([(a.artifact_id, a.dependency_artifact_ids) for a in manifest.artifacts])
    doc = ctx.transcript(manifest)
    report = ctx.document(manifest, "precision_evaluation", "PrecisionEvaluationReportV03")[1]
    assert report.alignment_content_sha256 == doc.alignment.content_sha256
    assert report.input_audio_sha256 == doc.transcript.input_audio_sha256
    for item in manifest.artifacts:
        handle = ctx.bundle.content(ctx.bundle.principals.owner(), manifest.bundle_revision_id, item.artifact_id, "derivative")
        assert handle.sha256 == item.sha256 and handle.size == item.size
    expected = ctx.bound_json(fixture["independent_stage_order"])
    assert expected["actual_creation_order"] == ["allocation", "reference_ready", "alignment_ready", "measurement_ready", "work_validation_ready", "quality_ready", "manifest_ready"]
    return {"real_manifest_dag": len(manifest.artifacts)}


def real_qualified_unmeasured(ctx):
    from t19_bundle_cases import audit_v03_published
    fixture, manifest, _ = ctx.publication("V03-12")
    result = audit_v03_published(ctx, manifest)
    assert ctx.transcript(manifest).alignment.precision.status == "not_measured"
    if not fixture.get("independent_actual_orchestration_trace"):
        raise CaseBlocked("actual_W14_autonomous_upstream", "registered four-master packaging is insufficient for autonomous production")
    trace = ctx.bound_json(fixture["independent_actual_orchestration_trace"])
    assert trace["production_id"] == manifest.production_id and trace["run_id"] == manifest.run_id
    assert trace["manually_supplied_master_asset_ids"] == []
    assert trace["actual_model_operation_ids"] and trace["actual_role_delegations"]
    assert [phase["kind"] for phase in trace["completed_creative_revisions"]] == ["insight", "script", "storyboard"]
    assert len(trace["actual_generated_master_asset_ids"]) == 4
    assert set(trace["actual_generated_master_asset_ids"]) <= {item.asset_id for item in manifest.artifacts if item.asset_id}
    assert {operation.operation_id for operation in ctx.engine.get_production("local-user", manifest.production_id).operations} >= set(trace["actual_model_operation_ids"])
    return result


def actual_correction(ctx):
    from t19_bundle_cases import audit_v03_published, audit_actual_correction
    fixture, manifest, _ = ctx.publication("V03-13")
    oracle = ctx.bound_json(fixture["independent_correction_oracle"])
    for record in oracle["ancestors"]:
        ctx.bound_bytes({"path": record["file_path"], "sha256": record["file_sha256"]})
    result = audit_actual_correction(ctx, manifest, oracle)
    audit_v03_published(ctx, manifest)
    invalid = ctx.host().run_fault_role("old_2N_release_denied", fixture)
    assert invalid["new_release_count"] == 0 and invalid["old_bytes_sha256_before"] == invalid["old_bytes_sha256_after"]
    return {"actual_ancestor_audit": result, "old_invalid_release": invalid}


def benchmark_license_export(ctx):
    fixture, manifest, _ = ctx.publication("V03-14")
    from t21_bundle_cases import actual_export
    exported = actual_export(ctx, "V03-14")
    import io, zipfile
    with zipfile.ZipFile(io.BytesIO(exported["raw"])) as archive:
        reference_items = [a for a in manifest.artifacts if "method_benchmark_reference" in a.roles]
        if fixture["benchmark_license_mode"] == "provenance_reference":
            assert len(reference_items) == 1
            item = reference_items[0]
            reference = ctx.c.MethodBenchmarkReference.model_validate_json(archive.read(item.relative_path))
            assert reference.evidence_trust_status == "reference_only"
            assert not any("method_benchmark" in a.roles for a in manifest.artifacts)
            assert not set(fixture["restricted_corpus_paths"]).intersection(archive.namelist())
        else:
            assert fixture["benchmark_license_mode"] == "embedded_full_report"
            assert any("method_benchmark" in a.roles for a in manifest.artifacts)
    return {"actual_export_id": exported["job"].export_id}


def full_projection_closure(ctx):
    from t21_bundle_cases import actual_export
    from t16_assertions import assert_acyclic_edges
    full = actual_export(ctx, "V03-15")
    projected = actual_export(ctx, "V03-15-projection", projection=True)
    manifest = full["manifest"]
    assert_acyclic_edges([(a.artifact_id, a.dependency_artifact_ids) for a in manifest.artifacts])
    expected = {"evidence_policy", "method_qualification", "work_alignment_validation", "quality"}
    assert expected <= {role for a in manifest.artifacts for role in a.roles}
    return {"full_export": full["job"].export_id, "projection_export": projected["job"].export_id}


def imported_trust_no_inheritance(ctx):
    from t21_bundle_cases import second_instance_import
    result = second_instance_import(ctx, "V03-16")
    second = ctx.second()
    fixture = second.fixture("V03-16-local-recognition")
    unconfigured = ctx.error("evidence_authority_unconfigured", second.engine.evidence_registry.administration_capability)
    # Recognition is a separate real local authority action, never an import.
    if not fixture.get("real_signed_local_recognition"):
        raise CaseBlocked("actual_local_recognition", "signed local recognition record/administrator bootstrap absent")
    observed = second.host().run_fault_role("signed_local_recognition", fixture)
    assert observed["import_id"] == result["import_id"] and observed["evidence_trust_status"] == "recognized_locally"
    assert observed["execution_qualification_inherited"] is False
    return {"import": result, "initial_unconfigured": unconfigured, "recognition": observed}


def real_schema_migration(ctx):
    fixture = ctx.fixture("V03-17")
    result = ctx.host().run_fault_role("schema4_to5_migration_rollback", fixture)
    assert result["old_schema"] == 4 and result["new_schema"] == 5
    assert result["failed_attempt_version"] == 4 and result["failed_attempt_new_tables_absent"]
    assert result["old_public_rows_before"] == result["old_public_rows_after"]
    assert result["old_engine_rejects_new_schema"] and result["WAL_included_in_backup"]
    return result


def real_transports_detached(ctx):
    from t21_bundle_cases import autonomous_once
    from t21_process_cases import actual_mcp_host, same_worker_second_run, actual_worker_control_boundaries, actual_worker_stop_new_claims
    return {"actual_HTTP_goal": autonomous_once(ctx), "actual_MCP_stdio": actual_mcp_host(ctx),
            "actual_persistent_worker": same_worker_second_run(ctx),
            "actual_private_pipe": actual_worker_control_boundaries(ctx), "actual_stop_new_claims": actual_worker_stop_new_claims(ctx)}


def actual_all_runtime_materials(ctx):
    from t21_media_cases import transcript_input, full_media_decode, subtitle_mapping, semantic_sources
    from t19_bundle_cases import audit_v03_published
    _, manifest, _ = ctx.publication("V03-19")
    expected = audit_v03_published(ctx, manifest)
    # The public actual work report itself, not a media.passed JSON field.
    work = ctx.document(manifest, "work_alignment_validation", "WorkAlignmentValidationReport")[1]
    actual = ctx.transcript(manifest)
    assert not work.source_gaps and work.result == "verified"
    assert (work.transcript_revision_id, work.transcript_content_sha256) == (actual.transcript.transcript_revision_id, actual.transcript.content_sha256)
    assert (work.alignment_revision_id, work.alignment_content_sha256) == (actual.alignment.alignment_revision_id, actual.alignment.content_sha256)
    assert (work.subtitle_revision_id, work.subtitle_content_sha256) == (actual.subtitles.subtitle_revision_id, actual.subtitles.content_sha256)
    assert work.mapping_refs
    return {"full_report": expected, "actual_input": transcript_input(ctx), "media": full_media_decode(ctx),
            "mapping": subtitle_mapping(ctx), "semantic_and_frames": semantic_sources(ctx, "T15-18")}


def independent_method_and_MM05(ctx):
    from t21_media_cases import independent_retrieval
    from t21_bundle_cases import real_three_os
    return {"real_method_population": actual_max_N(ctx, "V03-20"),
            "independent_MM05": independent_retrieval(ctx, "V03-20"), "three_OS": real_three_os(ctx)}
