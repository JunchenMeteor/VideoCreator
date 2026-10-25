"""Real reference/registry/material/export consumers; never sign a reference."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from t21_runtime import CaseBlocked


def _reference_prepared(ctx, case_id):
    fixture, lease, preparation = ctx.preparation(case_id)
    try:
        actual_bytes = ctx.bundle.read_material(lease, preparation.preparation_id, fixture["actual_transcript_material_id"])
        actual = ctx.c.ActualTranscriptDocumentV03.model_validate_json(actual_bytes)
        reference_bytes = ctx.bundle.read_material(lease, preparation.preparation_id, fixture["reference_material_id"])
        reference = ctx.c.PerWorkReferenceDocument.model_validate_json(reference_bytes)
        sources = {}
        for ref in (*reference.independent_listener_refs, reference.arbitration_ref):
            allocated = ctx.bundle.material_allocation(lease, preparation.preparation_id, ref.artifact_id)
            raw = ctx.bundle.read_material(lease, preparation.preparation_id, allocated.material_id)
            assert hashlib.sha256(raw).hexdigest() == ref.sha256
            sources[ref.artifact_id] = (ref, raw)
        return fixture, lease, preparation, actual, reference, reference_bytes, sources
    except Exception:
        ctx.engine.release_run(lease)
        raise


def _verify(ctx, values):
    _, lease, preparation, actual, reference, _, sources = values
    return ctx.engine.evidence_registry.verify_work_reference(reference, lease=lease,
        preparation_id=preparation.preparation_id, actual=actual, source_documents=sources)


def reference_unique_dispatch(ctx):
    values = _reference_prepared(ctx, "REF-01")
    _, lease, _, _, reference, raw, _ = values
    try:
        from video_creator.application.bundles import validate_text
        parsed = validate_text(raw, "precision_reference_v03", "application/json")
        assert type(parsed) is ctx.c.PerWorkReferenceDocument
        try:
            validate_text(raw, "precision_report_v03", "application/json")
        except (ValueError, ctx.EngineError):
            pass
        else:
            raise AssertionError("work reference was parsed as measurement union")
        _verify(ctx, values)
        return {"actual_model": type(parsed).__name__, "reference_file_sha256": hashlib.sha256(raw).hexdigest()}
    finally:
        ctx.engine.release_run(lease)


def reference_original_audio_units(ctx):
    values = _reference_prepared(ctx, "REF-02")
    fixture, lease, _, actual, reference, _, _ = values
    try:
        asset = ctx.bundle.asset(lease, actual.transcript.input_audio_asset_id)
        path = ctx.bundle.content_path(lease, asset.asset_id)
        assert asset.sha256 == reference.input_audio_sha256 == actual.transcript.input_audio_sha256
        assert hashlib.sha256(path.read_bytes()).hexdigest() == asset.sha256
        clock, duration = ctx.bundle._t18_runtime_handles["media"].clock(asset, path)
        assert clock == actual.transcript.input_track.clock and duration == actual.transcript.duration_us
        from t17_reference_assertions import reference_units
        ordered = [u.utterance_id for u in actual.transcript.utterances]
        reference_units(list(reference.units), [(u.transcript_unit_id, u.reference_range.start_us, u.reference_range.end_us) for u in reference.boundaries], ordered, duration)
        oracle = ctx.bound_json(fixture["independent_original_units"])
        assert oracle["input_audio_sha256"] == asset.sha256 and oracle["ordered_unit_ids"] == ordered
        _verify(ctx, values)
        return {"actual_audio_sha256": asset.sha256, "full_N": len(ordered), "decoded_samples": clock.decoded_sample_count}
    finally:
        ctx.engine.release_run(lease)


def actual_listener_arbitration(ctx):
    values = _reference_prepared(ctx, "REF-03")
    fixture, lease, _, actual, reference, _, sources = values
    try:
        scope = _verify(ctx, values)
        corpus = ctx.bound_json(fixture["independent_listening_review_receipt"])
        assert corpus["audio_sha256"] == reference.input_audio_sha256
        assert corpus["listener_material_sha256"] == [ref.sha256 for ref in reference.independent_listener_refs]
        assert corpus["arbitration_material_sha256"] == reference.arbitration_ref.sha256
        facts = [json.loads(raw)["findings"] for _, raw in sources.values()]
        assert len({row["listener_id"] for row in facts if "listener_id" in row}) == len(reference.independent_listener_refs)
        assert scope.independent_approval_refs
        assert corpus["actual_human_reviewers"] and corpus["annotation_session_ids"]
        return {"actual_listeners": len(reference.independent_listener_refs), "arbitration_sha256": reference.arbitration_ref.sha256}
    finally:
        ctx.engine.release_run(lease)


def issuer_scope_current(ctx):
    values = _reference_prepared(ctx, "REF-04")
    fixture, lease, preparation, actual, reference, _, sources = values
    try:
        scope = _verify(ctx, values)
        assert scope.evaluation_scope == "per_work_reference_measurement"
        assert scope.valid_from_us <= ctx.engine.clock() < scope.expires_at_us
        wrong = reference.model_copy(update={"issuer": fixture["untrusted_issuer"]})
        # Hash recomputation is NOT a signature; the real registry must reject.
        from video_creator.application.evidence import evidence_sha
        wrong = wrong.model_copy(update={"content_sha256": evidence_sha(wrong)})
        rejected = ctx.error("reference_scope_denied", ctx.engine.evidence_registry.verify_work_reference, wrong,
            lease=lease, preparation_id=preparation.preparation_id, actual=actual, source_documents=sources)
        return {"actual_authority_id": scope.authority_id, "issuer_refusal": rejected}
    finally:
        ctx.engine.release_run(lease)


def actual_three_hash_layers(ctx):
    values = _reference_prepared(ctx, "REF-05")
    _, lease, _, _, reference, raw, _ = values
    try:
        from t17_reference_assertions import reference_hash_layers
        result = reference_hash_layers(reference.model_dump(mode="json"), raw, hashlib.sha256(raw).hexdigest())
        scope = _verify(ctx, values)  # Real private registry verifies HMAC with installed key; Test never reads it.
        return {"internal_content_sha256": result["internal_content_sha256"], "complete_file_sha256": result["complete_file_sha256"],
                "actual_registry_issuer": scope.reference_issuer, "signature_input_sha256": hashlib.sha256(result["signature_input_bytes"]).hexdigest()}
    finally:
        ctx.engine.release_run(lease)


def signed_prediction_copy_refused(ctx):
    values = _reference_prepared(ctx, "REF-06")
    fixture, lease, preparation, actual, _, _, sources = values
    try:
        # External adversarial fixture must carry an actual valid issuer HMAC;
        # Test cannot create/sign it or change issuer roots to make it valid.
        if not fixture.get("externally_signed_prediction_copy"):
            raise CaseBlocked("valid_HMAC_prediction_copy_fixture", "approved issuer adversarial reference and actual source bodies absent")
        copied = ctx.c.PerWorkReferenceDocument.model_validate_json(ctx.bound_bytes(fixture["externally_signed_prediction_copy"]))
        predictions = [(b.transcript_unit_id, b.intrinsic_range.start_us, b.intrinsic_range.end_us) for b in actual.alignment.boundaries]
        assert [(b.transcript_unit_id, b.reference_range.start_us, b.reference_range.end_us) for b in copied.boundaries] == predictions
        try:
            ctx.engine.evidence_registry.verify_work_reference(copied, lease=lease, preparation_id=preparation.preparation_id,
                actual=actual, source_documents=sources)
        except ctx.EngineError as error:
            assert error.code in {"reference_source_missing", "reference_source_invalid", "reference_independence_unapproved", "reference_listener_invalid", "reference_arbitration_invalid"}
            assert error.code != "reference_signature_invalid", "fixture did not exercise a valid HMAC claim"
            return {"actual_independence_refusal": error.code}
        raise AssertionError("signed ASR-prediction copy was accepted as independent ground truth")
    finally:
        ctx.engine.release_run(lease)


def actual_reference_dag(ctx):
    fixture, manifest, _ = ctx.publication("REF-07")
    from t16_assertions import assert_acyclic_edges
    ids = assert_acyclic_edges([(a.artifact_id, a.dependency_artifact_ids) for a in manifest.artifacts])
    reference = ctx.document(manifest, "precision_reference", "PerWorkReferenceDocument")[1]
    report = ctx.document(manifest, "precision_evaluation", "PrecisionEvaluationReportV03")[1]
    document = ctx.transcript(manifest)
    assert {r.artifact_id for r in (*reference.independent_listener_refs, reference.arbitration_ref)} <= ids
    assert document.alignment.precision.reference_ref.sha256 == ctx.artifact(manifest, "precision_reference")[0].sha256
    assert report.alignment_content_sha256 == document.alignment.content_sha256
    locator = document.alignment.precision.measurement_report_locator.model_dump(mode="json")
    assert not {"sha256", "size", "decoded", "validated"}.intersection(locator)
    order = ctx.bound_json(fixture["actual_stage_sequence"])
    positions = {entry["phase"]: entry["sequence"] for entry in order}
    required = ["listener_complete", "reference_ready", "alignment_ready", "measurement_ready", "work_validation_ready", "quality_ready", "manifest_ready"]
    assert all(a < b for a, b in zip([positions[p] for p in required], [positions[p] for p in required][1:]))
    return {"actual_reference_dag_nodes": len(ids)}


def actual_reference_export(ctx):
    from t21_bundle_cases import actual_export
    exported = actual_export(ctx, "REF-08")
    manifest = exported["manifest"]
    reference = ctx.document(manifest, "precision_reference", "PerWorkReferenceDocument")[1]
    included = {a.artifact_id for a in manifest.artifacts}
    assert {r.artifact_id for r in (*reference.independent_listener_refs, reference.arbitration_ref)} <= included
    assert any("precision_evaluation" in a.roles for a in manifest.artifacts)
    restricted = ctx.fixture("REF-08-restricted")
    try:
        ctx.bundle.request_export(ctx.bundle.principals.owner(), restricted["bundle_revision_id"], "T21-ref-restricted-full", ctx.c.BundleExportRequest())
    except ctx.EngineError as error:
        assert error.code == "bundle_rights_denied"
    else:
        raise AssertionError("full export silently omitted restricted reference evidence")
    return {"actual_reference_full_export_id": exported["job"].export_id}


def actual_reference_origin_import(ctx):
    from t21_bundle_cases import second_instance_import
    result = second_instance_import(ctx, "REF-09")
    second = ctx.second()
    receipt = second.bundle.import_status(second.bundle.principals.owner(), result["import_id"])
    assert receipt.evidence_trust_status == "origin_snapshot_only" and receipt.execution_qualification_inherited is False
    manifest = second.bundle.import_manifest(second.bundle.principals.owner(), receipt.import_id)
    actual_refs = [a for a in manifest.artifacts if "precision_reference" in a.roles]
    assert len(actual_refs) == 1
    raw = second.bundle.import_content(second.bundle.principals.owner(), receipt.import_id, actual_refs[0].artifact_id).path.read_bytes()
    reference = second.c.PerWorkReferenceDocument.model_validate_json(raw)
    assert hashlib.sha256(raw).hexdigest() == actual_refs[0].sha256
    assert reference.units
    return {"origin": result, "actual_reference_file_sha256": actual_refs[0].sha256}


def actual_null_or_strict_wait(ctx):
    from t21_v03_cases import three_scopes_null
    observed = three_scopes_null(ctx, "REF-10")
    fixture = ctx.fixture("REF-10-strict")
    accepted = ctx.engine.accept_production("local-user", "T21-ref-missing-strict", ctx.c.parse_production_request(fixture["request"]))
    detail = ctx.engine.get_production("local-user", accepted.production_id)
    assert detail.status == "waiting_user" and detail.bundle_ref is None and not detail.operations
    assert detail.request.delivery_requirements.alignment_evidence_policy == "strict_reference_v1"
    return {"qualified_real_null": observed, "strict_real_waiting_production": accepted.production_id}
