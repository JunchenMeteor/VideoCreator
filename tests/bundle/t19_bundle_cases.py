"""Real producer/publication/consumption assertions. Missing real fixtures fail ready.

No Fake service, DTO copies, SQL published rows, or precision/rights True callbacks.
"""
import hashlib
import json
import time
from pathlib import Path

from t16_guard import NotReadyForExecution


def _artifact_bytes(ctx, manifest, role):
    selected = [item for item in manifest.artifacts if role in item.roles]
    if len(selected) != 1:
        raise AssertionError("exactly one actual artifact required for " + role)
    item = selected[0]
    handle = ctx.bundle.content(ctx.bundle.principals.owner(), manifest.bundle_revision_id, item.artifact_id, "derivative")
    raw = handle.path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == item.sha256 and len(raw) == item.size
    return item, raw


def audit_v03_published(ctx, manifest):
    c = ctx.contracts
    assert type(manifest) is c.BundleManifestV03
    assert set(manifest.requested_outputs) == {"video", "narration_audio", "mixed_audio", "approved_script", "actual_transcript", "subtitles", "semantic_manifest", "rag_chunks"}
    _, raw = _artifact_bytes(ctx, manifest, "actual_transcript")
    document = c.ActualTranscriptDocumentV03.model_validate_json(raw)
    precision = document.alignment.precision
    if precision.status == "not_measured":
        assert precision.reference_ref is None and precision.sample_count is None and precision.p95_error_us is None
        assert precision.measurement_report_locator is None
        assert precision.criterion_version_ref is None
        assert not any("precision_reference" in a.roles or "precision_evaluation" in a.roles for a in manifest.artifacts)
    work_artifact = next(a for a in manifest.artifacts if a.artifact_id == manifest.work_validation_document_artifact_id)
    work_raw = ctx.bundle.content(ctx.bundle.principals.owner(), manifest.bundle_revision_id, work_artifact.artifact_id, "derivative").path.read_bytes()
    work = c.WorkAlignmentValidationReport.model_validate_json(work_raw)
    # RV20-P01: ordinary unmeasured per-work precision is not a runtime gap.
    assert work.evaluation_scope == "work_runtime_validation" and not work.source_gaps
    quality_item, quality_raw = _artifact_bytes(ctx, manifest, "quality")
    quality = c.BundleQualityEvidenceV03.model_validate_json(quality_raw)
    checks = {check.check_id: check for check in quality.checks}
    assert len(checks) == len(quality.checks)
    # RV20-P02: this is the actual immutable report after real final verify;
    # never rewrite it to verified to satisfy this assertion.
    assert checks["rights"].status == "verified" and checks["alignment"].status == "verified"
    assert manifest.approval_refs and manifest.rights
    rights = {r.rights_id: r for r in manifest.rights}
    _, rag_raw = _artifact_bytes(ctx, manifest, "rag_chunks")
    chunks = [c.RagChunk.model_validate_json(line) for line in rag_raw.splitlines()]
    assert chunks
    for chunk in chunks:
        parent = rights[chunk.rights_ref]
        if parent.expires_at_us is not None:
            # RV20-P04: no child null/extension beyond an actual finite right.
            assert chunk.valid_until_us is not None and chunk.valid_until_us <= parent.expires_at_us
        if chunk.valid_until_us is not None:
            assert chunk.valid_until_us > ctx.engine.clock()
    return {"bundle_revision_id": manifest.bundle_revision_id, "artifact_count": len(manifest.artifacts), "quality_artifact": quality_item.artifact_id, "chunk_count": len(chunks)}


def assert_correction_mapping(actual_links, oracle):
    """Pure graph oracle; expected IDs/edges come from independently bound data."""
    assert type(oracle) is dict
    expected_links = oracle["corrections"]
    ancestors = oracle["ancestors"]
    assert type(expected_links) is list and expected_links and type(ancestors) is list and ancestors
    expected = {}
    for row in expected_links:
        assert type(row) is dict and all(type(row.get(k)) is str and row[k] for k in ("artifact_id", "parent_artifact_id", "evaluation_id"))
        assert row["artifact_id"] not in expected
        expected[row["artifact_id"]] = row
    original_map = {}
    for row in ancestors:
        assert type(row) is dict and type(row.get("artifact_id")) is str and row["artifact_id"]
        assert row["artifact_id"] not in original_map
        original_map[row["artifact_id"]] = row
    actual = {}
    for row in actual_links:
        assert row["artifact_id"] not in actual
        actual[row["artifact_id"]] = row
    assert set(actual) == set(expected), "every independently expected corrected report must be present, with no extra report"
    assert set(original_map) == {row["parent_artifact_id"] for row in expected_links}
    for artifact_id, row in expected.items():
        assert actual[artifact_id] == row, "independent corrected report ID/ancestor edge/evaluation ID differs"
        seen = set()
        cursor = artifact_id
        while cursor in expected:
            assert cursor not in seen, "correction ancestry cycle"
            seen.add(cursor)
            cursor = expected[cursor]["parent_artifact_id"]
    return original_map


def audit_actual_correction(ctx, manifest, oracle):
    c = ctx.contracts
    indexed = {item.artifact_id: item for item in manifest.artifacts}
    assert len(indexed) == len(manifest.artifacts)
    reports = {}
    actual_links = []
    for item in manifest.artifacts:
        if item.roles != ("precision_evaluation",):
            continue
        raw = ctx.bundle.content(ctx.bundle.principals.owner(), manifest.bundle_revision_id, item.artifact_id, "derivative").path.read_bytes()
        body = json.loads(raw)
        if body.get("schema_version") == "0.3.0-candidate" and body.get("corrected_from"):
            assert hashlib.sha256(raw).hexdigest() == item.sha256 and len(raw) == item.size
            report = c.PrecisionEvaluationReportV03.model_validate(body)
            reports[item.artifact_id] = (item, report)
            actual_links.append({"artifact_id": item.artifact_id, "parent_artifact_id": report.corrected_from.artifact_id,
                                 "evaluation_id": report.evaluation_id})
    original_map = assert_correction_mapping(actual_links, oracle)
    measurements = []
    for artifact_id, (item, report) in reports.items():
        ref = report.corrected_from
        expected = original_map[ref.artifact_id]
        originals = Path(expected["file_path"]).read_bytes()
        expected_file_sha = hashlib.sha256(originals).hexdigest()
        assert expected_file_sha == expected["file_sha256"]
        origin = indexed[ref.artifact_id]
        assert origin.roles == ("precision_evaluation",) and origin.sha256 == expected_file_sha == ref.sha256
        assert origin.size == len(originals) and ref.artifact_id in item.dependency_artifact_ids
        copied = ctx.bundle.content(ctx.bundle.principals.owner(), manifest.bundle_revision_id, origin.artifact_id, "derivative").path.read_bytes()
        assert copied == originals  # Exact bytes of EACH independently pinned ancestor.
        for key in ("schema_version", "report_id", "content_sha256", "alignment_revision_id", "alignment_content_sha256"):
            assert getattr(ref, key) == expected[key]
        original_model = c.PrecisionEvaluationReport if expected["schema_version"] == c.SCHEMA_VERSION else c.PrecisionEvaluationReportV03
        original = original_model.model_validate_json(copied)
        assert original.evaluation_id == expected["report_id"] and original.content_sha256 == expected["content_sha256"]
        assert original.alignment_revision_id == expected["alignment_revision_id"]
        assert original.alignment_content_sha256 == expected["alignment_content_sha256"]
        measurements.append({"corrected_artifact_id": artifact_id, "ancestor_artifact_id": ref.artifact_id,
                             "ancestor_file_sha256": expected_file_sha, "ancestor_size": len(originals)})
    return {"oracle_executed": "per-ancestor-independent-mapping", "corrected_report_ids": [r.evaluation_id for _, r in reports.values()],
            "originals": measurements}


def consume_actual_correction(ctx, fixture):
    if not fixture or not fixture.get("bundle_revision_id") or not fixture.get("correction_oracle_document"):
        raise NotReadyForExecution("actual qualified corrected bundle and independently bound ancestor oracle are absent")
    manifest = ctx.bundle.get_manifest(ctx.bundle.principals.owner(), fixture["bundle_revision_id"], "derivative")
    published = audit_v03_published(ctx, manifest)
    correction = audit_actual_correction(ctx, manifest, fixture["correction_oracle_document"])
    return {"published": published, "correction": correction}


def produce_from_actual_fixture(ctx, fixture):
    required = ("instance_id", "production_id", "run_id", "video_asset_id", "narration_asset_id", "mixed_asset_id", "cover_asset_id", "asr_route_id")
    if type(fixture) is not dict or any(not fixture.get(key) for key in required):
        raise NotReadyForExecution("actual independently admitted own production fixture is missing")
    if fixture["instance_id"] != ctx.engine.instance_id:
        raise NotReadyForExecution("fixture belongs to another installation")
    detail = ctx.engine.get_production("local-user", fixture["production_id"])
    if detail.run_id != fixture["run_id"] or detail.bundle_ref is not None:
        raise NotReadyForExecution("requires original own uncompleted production run")
    lease = ctx.engine.acquire_run("t19-real-producer", run_id=detail.run_id)
    if lease is None:
        raise NotReadyForExecution("actual policy/ordinary lease is not ready")
    # The actual registry checks qualification; a fixture's approved flag cannot.
    ctx.bundle.evidence_policy(lease)
    for key in ("video_asset_id", "narration_asset_id", "mixed_asset_id", "cover_asset_id"):
        asset = ctx.bundle.asset(lease, fixture[key])
        path = ctx.bundle.content_path(lease, asset.asset_id)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == asset.sha256
    reference = None
    if fixture.get("per_work_reference_requested"):
        raise NotReadyForExecution("actual listener/arbitration issuer materials bootstrap not yet bound; no prediction-derived reference substitute")
    producer = ctx.bundle._t18_runtime_handles["producer"]
    result = producer(lease, **{key: fixture[key] for key in ("video_asset_id", "narration_asset_id", "mixed_asset_id", "cover_asset_id", "asr_route_id")}, reference_evidence=reference)
    assert result.state == "published" and result.bundle_ref is not None
    # Inspect actual service-visible bytes, not a media result JSON assertion.
    manifest = ctx.bundle.get_manifest(ctx.bundle.principals.owner(), result.bundle_ref.bundle_revision_id, "derivative")
    return audit_v03_published(ctx, manifest)


def consume_actual_bundle(ctx, fixture):
    if not fixture or not fixture.get("bundle_revision_id"):
        raise NotReadyForExecution("actual published qualified full bundle is absent")
    owner, c = ctx.bundle.principals.owner(), ctx.contracts
    revision = fixture["bundle_revision_id"]
    manifest = ctx.bundle.get_manifest(owner, revision, "export")
    audit_v03_published(ctx, manifest)
    job = ctx.bundle.request_export(owner, revision, "T19-full-export", c.BundleExportRequest())
    assert ctx.bundle.request_export(owner, revision, "T19-full-export", c.BundleExportRequest()).export_id == job.export_id
    deadline = time.monotonic() + 30
    ctx.bundle.start_exports()
    try:
        while time.monotonic() < deadline:
            current = ctx.bundle.export_status(owner, job.export_id)
            if current.status in {"ready", "failed"}:
                break
            time.sleep(0.05)
        assert current.status == "ready", current.error_code
        archive = ctx.bundle.export_content(owner, job.export_id)
        raw = archive.path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == current.archive_sha256
        project = ctx.engine.create_project("local-user", c.ProjectInput(name="T19-imported"))
        staged = ctx.bundle.assets.stage_bytes("local-user", raw, "application/zip")
        request = c.BundleImportRequest(staging_id=staged["staging_id"], archive_sha256=staged["sha256"], expected_origin_ref=job.bundle_ref, project_id=project.project_id)
        receipt = ctx.bundle.import_bundle(owner, "T19-original-import", request)
        assert ctx.bundle.import_status(owner, receipt.import_id) == receipt
        assert receipt.origin_bundle_ref == job.bundle_ref
        assert receipt.evidence_trust_status == "origin_snapshot_only" and receipt.execution_qualification_inherited is False
        return {"export_id": job.export_id, "archive_sha256": current.archive_sha256, "import_id": receipt.import_id}
    finally:
        ctx.bundle.stop_exports()


def reject_actual_runtime_gap(ctx, fixture):
    required = ("run_id", "preparation_id", "work_validation_material_id", "actual_transcript_artifact_id", "work_validation_artifact_id", "audio_mappings")
    if not fixture or any(not fixture.get(key) for key in required):
        raise NotReadyForExecution("actual staged runtime-gap fixture not bound; no manufactured passed validator")
    lease = ctx.engine.acquire_run("t19-real-runtime-gap", run_id=fixture["run_id"])
    if lease is None:
        raise NotReadyForExecution("actual original ordinary lease is not available")
    raw = ctx.bundle.read_material(lease, fixture["preparation_id"], fixture["work_validation_material_id"])
    actual = ctx.contracts.WorkAlignmentValidationReport.model_validate_json(raw)
    assert actual.source_gaps and actual.evaluation_scope == "work_runtime_validation"
    mappings = tuple(ctx.contracts.AudioTimelineMapping.model_validate(value) for value in fixture["audio_mappings"])
    try:
        ctx.bundle.verify_alignment_evidence(lease, fixture["preparation_id"],
            actual_transcript_artifact_id=fixture["actual_transcript_artifact_id"],
            work_validation_artifact_id=fixture["work_validation_artifact_id"], audio_mappings=mappings)
    except ctx.EngineError as error:
        assert error.code == "work_validation_incomplete"
    else:
        raise AssertionError("genuine actual runtime gap was accepted")
    detail = ctx.bundle.context(lease)
    assert detail.bundle_ref is None
    ctx.engine.release_run(lease)
    return {"preparation_id": fixture["preparation_id"], "runtime_gaps_preserved": list(actual.source_gaps)}
