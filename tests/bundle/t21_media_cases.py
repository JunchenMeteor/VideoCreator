"""Real media/typed-document drivers. Independent fixtures never come from ASR."""
from __future__ import annotations

import copy
import hashlib
import json
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

from t21_runtime import CaseBlocked

DEFAULT8 = {"video", "narration_audio", "mixed_audio", "approved_script", "actual_transcript", "subtitles", "semantic_manifest", "rag_chunks"}


def default_outputs(ctx):
    fixture = ctx.fixture("T15-01")
    body = copy.deepcopy(fixture["request"])
    body.pop("outputs", None)
    accepted = ctx.engine.accept_production("local-user", "T21-default8", ctx.c.parse_production_request(body))
    detail = ctx.engine.get_production("local-user", accepted.production_id)
    assert len(detail.request.outputs) == 8 and set(detail.request.outputs) == DEFAULT8
    subset = ctx.c.parse_production_request(dict(body, outputs=["video"]))
    small = ctx.engine.accept_production("local-user", "T21-subset", subset)
    observed = ctx.engine.get_production("local-user", small.production_id)
    assert observed.bundle_ref is None and not observed.operations
    assert observed.status == "waiting_user"
    return {"production_id": accepted.production_id, "subset_production_id": small.production_id}


def full_media_decode(ctx):
    fixture, manifest, _ = ctx.publication("T15-02")
    media = ctx.bundle._t18_runtime_handles["media"]
    observations = []
    for role in ("video", "narration_audio", "mixed_audio"):
        item, path, _ = ctx.artifact(manifest, role)
        asset = ctx.bundle.assets.get("local-user", item.asset_id)
        probe = ctx.bundle.validators.media_validator(path, item.media_type)
        assert probe.decoded and probe.has_audio
        if role == "video":
            assert probe.has_video and probe.width > 0 and probe.height > 0
        clock, duration = media.clock(asset, path)
        assert clock.decoded_sample_count > 0 and duration > 0
        observations.append({"role": role, "sha256": item.sha256, "duration_us": duration, "clock": clock.model_dump(mode="json")})
    # Mandatory independently supplied AV receipt; a decoder is not a listener.
    if not fixture.get("independent_av_receipt"):
        raise CaseBlocked("independent_actual_AV_review", "actual video/audio review receipt absent")
    av = ctx.bound_json(fixture["independent_av_receipt"])
    assert av["bundle_revision_id"] == manifest.bundle_revision_id
    assert av["reviewed_media_sha256"] == {row["role"]: row["sha256"] for row in observations}
    assert av["verdict"] == "accepted" and av["reviewer_ids"]
    return {"media": observations, "review_receipt_sha256": fixture["independent_av_receipt"]["sha256"]}


def manifest_bytes(ctx):
    _, manifest, raw = ctx.publication("T15-03")
    assert raw.decode("utf-8").endswith("\n") and b"\r\n" not in raw
    assert len({a.artifact_id for a in manifest.artifacts}) == len(manifest.artifacts)
    assert len({a.relative_path.casefold() for a in manifest.artifacts}) == len(manifest.artifacts)
    for artifact in manifest.artifacts:
        handle = ctx.bundle.content(ctx.bundle.principals.owner(), manifest.bundle_revision_id, artifact.artifact_id, "derivative")
        data = handle.path.read_bytes()
        assert hashlib.sha256(data).hexdigest() == artifact.sha256 and len(data) == artifact.size
        assert bool(artifact.asset_id) != bool(artifact.material_id)
    return {"manifest_file_sha256": hashlib.sha256(raw).hexdigest(), "artifact_count": len(manifest.artifacts)}


def strict_materials(ctx):
    fixture = ctx.fixture("T15-04")
    from video_creator.application.bundles import validate_text
    rejected = []
    for sample in fixture["invalid_documents"]:
        raw = ctx.bound_bytes(sample["bytes"])
        try:
            validate_text(raw, sample["schema_kind"], sample["media_type"])
        except (ValueError, ctx.EngineError) as error:
            rejected.append(type(error).__name__)
        else:
            raise AssertionError("real parser accepted duplicate/nonfinite malformed JSON")
    assert len(rejected) >= 5
    _, manifest, _ = ctx.publication("T15-04")
    from t15_oracles import record_hash
    for model in (ctx.transcript(manifest).transcript, ctx.transcript(manifest).alignment):
        record_hash(model.model_dump(mode="json"))
    return {"rejected_actual_parser_inputs": len(rejected)}


def transcript_input(ctx):
    fixture, manifest, _ = ctx.publication("T15-05")
    document = ctx.transcript(manifest)
    item = next(a for a in manifest.artifacts if a.artifact_id == fixture["actual_asr_input_artifact_id"])
    assert item.asset_id == document.transcript.input_audio_asset_id and item.sha256 == document.transcript.input_audio_sha256
    assert "mixed_audio" in item.roles or "video" in item.roles
    media = ctx.bundle._t18_runtime_handles["media"]
    handle = ctx.bundle.content(ctx.bundle.principals.owner(), manifest.bundle_revision_id, item.artifact_id, "derivative")
    asset = ctx.bundle.assets.get("local-user", item.asset_id)
    clock, duration = media.clock(asset, handle.path)
    assert clock == document.transcript.input_track.clock and duration == document.transcript.duration_us
    assert document.transcript.text == "".join(u.text for u in document.transcript.utterances)
    return {"actual_asr_input_sha256": item.sha256, "decoded_duration_us": duration}


def actual_asr(ctx, case_id="T15-07"):
    fixture = ctx.fixture(case_id)
    profile = ctx.fixture("ASR-runtime")
    from video_creator.providers.local_asr import run_local_asr
    request = ctx.bound_json(fixture["request_document"])
    result = run_local_asr(request, python_executable=Path(profile["python_executable"]),
                           runtime_root=Path(profile["runtime_root"]), timeout_seconds=profile["timeout_seconds"])
    assert result["execution"]["child_terminal"] and result["execution"]["tree_empty"]
    assert result["execution"]["return_code"] == 0
    ctx.journal.record("actual_asr_returned", {"input_audio_sha256": result["input_audio_sha256"], "pid": result["execution"]["pid"]})
    return request, result


def audio_corpus(ctx):
    fixture = ctx.fixture("T15-06")
    from video_creator.providers.local_asr import AsrProcessError, run_local_asr
    profile = ctx.fixture("ASR-runtime")
    kinds = set()
    results = []
    for sample in fixture["independent_corpus"]:
        oracle = ctx.bound_json(sample["human_annotation"])
        request = ctx.bound_json(sample["request_document"])
        assert oracle["input_audio_sha256"] == request["audio_sha256"]
        kinds.add(oracle["audio_kind"])
        try:
            actual = run_local_asr(request, python_executable=Path(profile["python_executable"]), runtime_root=Path(profile["runtime_root"]))
        except AsrProcessError as error:
            assert error.code == oracle["expected_error_code"]
            assert error.evidence["child_terminal"] and error.evidence["tree_empty"]
            results.append({"kind": oracle["audio_kind"], "code": error.code})
        else:
            assert actual["text"] == oracle["expected_transcript_text"]
            assert actual["input_audio_sha256"] == oracle["input_audio_sha256"]
            results.append({"kind": oracle["audio_kind"], "actual_text_sha256": hashlib.sha256(actual["text"].encode()).hexdigest()})
    assert {"chinese_speech", "music", "silence", "unintelligible"} <= kinds
    return {"real_corpus_observations": results}


def decoded_provenance(ctx):
    request, actual = actual_asr(ctx)
    fixture = ctx.fixture("T15-07")
    asset = ctx.bundle.assets.get("local-user", fixture["audio_asset_id"])
    path = ctx.bundle.assets.content_path("local-user", asset.asset_id)
    assert asset.sha256 == request["audio_sha256"] == actual["input_audio_sha256"]
    clock, duration = ctx.bundle._t18_runtime_handles["media"].clock(asset, path)
    assert clock.decoded_sample_count == actual["decoded_samples"] and clock.sample_rate == actual["sample_rate"]
    assert duration == actual["duration_us"]
    runtime = actual["runtime"]
    assert runtime["model_file_sha256"] == request["model_file_sha256"]
    profile = ctx.fixture("ASR-runtime")
    assert runtime["versions"] == ctx.bound_json(profile["independent_runtime_versions"])
    return {"actual_pid": actual["execution"]["pid"], "sample_count": actual["decoded_samples"], "duration_us": duration}


def corrupt_asr_adapter(ctx):
    # Fault injection at the validator boundary AFTER real worker output,
    # not a synthetic ASR positive or fake published bundle.
    fixture, lease = ctx.ordinary_lease("T15-08")
    import video_creator.providers.local_asr as provider
    profile = ctx.fixture("ASR-runtime")
    executor = ctx.bundle._t18_runtime_handles["executor"]
    real_validate = provider.validate_asr_result
    mutations = {
        "bool_pts": lambda r: r["audio_provenance"].__setitem__("first_frame_pts", True),
        "paired_sample_duration": lambda r: (r.__setitem__("decoded_samples", r["decoded_samples"] + 100), r.__setitem__("duration_us", r["duration_us"] + 1000)),
        "paired_offset": lambda r: (r.__setitem__("video_audio_offset_us", r["video_audio_offset_us"] + 1000), r["audio_provenance"].__setitem__("observed_audio_video_offset_us", r["video_audio_offset_us"])),
        "language_type": lambda r: r.__setitem__("language", ["zh"]),
        "invented_compute": lambda r: r["runtime"].__setitem__("actual_compute_type", "unapproved_compute"),
    }
    observations = []
    try:
        for name, mutate in mutations.items():
            seen = []
            def inject(result, request):
                real_validate(result, request)
                seen.append({"original_audio_sha256": result["input_audio_sha256"], "original_text_sha256": hashlib.sha256(result["text"].encode()).hexdigest()})
                bad = copy.deepcopy(result)
                mutate(bad)
                real_validate(bad, request)  # accepted corruption MUST fail the outer assertion.
            asset = ctx.bundle.assets.get("local-user", fixture["audio_asset_id"])
            path = ctx.bundle.assets.content_path("local-user", asset.asset_id)
            driver = provider.LocalAsrDriver(path, storage_root=ctx.engine.db.data_dir,
                model_dir=Path(profile["model_dir"]), python_executable=Path(profile["python_executable"]),
                model_revision=profile["model_revision"], expected_audio_sha256=asset.sha256,
                expected_model_files=profile["model_file_sha256"], runtime_root=Path(profile["runtime_root"]),
                resource_manifest_path=Path(profile["manifest_path"]), resource_manifest_sha256=profile["manifest_sha256"])
            intent_body = copy.deepcopy(fixture["operation_intent"])
            intent_body["dedupe_key"] += ":" + name
            intent = ctx.c.OperationIntent.model_validate(intent_body)
            with patch.object(provider, "validate_asr_result", inject):
                observation = executor.execute(lease, intent, driver)
            assert len(seen) == 1 and observation.status == "failed"
            assert observation.result_json["error_code"] == "asr_result_invalid"
            assert observation.actual_cost.units() == 0
            observations.append({"fault": name, "status": observation.status, "real_worker_input": seen[0]})
    finally:
        ctx.engine.release_run(lease)
    return {"fault_injection": True, "actual_adapter_observations": observations}


def missing_alignment_policy(ctx):
    fixture = ctx.fixture("T15-09")
    accepted = ctx.engine.accept_production("local-user", "T21-strict-default", ctx.c.parse_production_request(fixture["request"]))
    detail = ctx.engine.get_production("local-user", accepted.production_id)
    assert detail.request.delivery_requirements.alignment_requirement == "utterance_verified"
    assert detail.request.delivery_requirements.allowed_degradations == ()
    assert detail.status == "waiting_user" and detail.bundle_ref is None and not detail.operations
    return {"production_id": accepted.production_id, "status": detail.status}


def actual_metric(ctx, fixture, document, report):
    """Independent full-population calculation; this does not grant authority."""
    reference = ctx.bound_json(fixture["independent_reference"])
    expected = reference["ranges_by_unit"]
    predicted = document.alignment.boundaries
    assert len(predicted) == len(expected) and len({p.transcript_unit_id for p in predicted}) == len(predicted)
    assert {p.transcript_unit_id for p in predicted} == set(expected)
    pairs = report.boundaries
    assert len(pairs) == len(predicted) and {p.transcript_unit_id for p in pairs} == set(expected)
    from t16_assertions import assert_metric
    result = assert_metric([(p.transcript_unit_id, p.intrinsic_range.start_us, p.intrinsic_range.end_us) for p in predicted],
        [(key, span["start_us"], span["end_us"]) for key, span in expected.items()], document.transcript.duration_us,
        document.alignment.precision.sample_count, document.alignment.precision.p95_error_us)
    assert report.alignment_content_sha256 == document.alignment.content_sha256
    assert reference["input_audio_sha256"] == report.input_audio_sha256 == document.transcript.input_audio_sha256
    assert report.sample_count == result["N"] and report.p95_error_us == result["p95_error_us"]
    return result


def independent_precision(ctx, case_id="T15-10"):
    # Verification consumes a real unfinished preparation under its current
    # ordinary lease. A published/succeeded Run cannot be reacquired as work.
    fixture, lease, preparation = ctx.preparation(case_id)
    try:
        manifest = ctx.c.parse_bundle_manifest(ctx.bound_json(fixture["prepared_manifest"]))
        assert manifest.run_id == lease.run_id and manifest.bundle_revision_id == preparation.bundle_revision_id
        modern = manifest.schema_version == "0.3.0-candidate"
        documents = {}
        for role, model_name in (
            ("actual_transcript", "ActualTranscriptDocumentV03" if modern else "ActualTranscriptDocument"),
            ("precision_evaluation", "PrecisionEvaluationReportV03" if modern else "PrecisionEvaluationReport"),
        ):
            entries = [item for item in manifest.artifacts if role in item.roles]
            assert len(entries) == 1 and entries[0].material_id
            item = entries[0]
            raw = ctx.bundle.read_material(lease, preparation.preparation_id, item.material_id)
            assert hashlib.sha256(raw).hexdigest() == item.sha256 and len(raw) == item.size
            documents[role] = getattr(ctx.c, model_name).model_validate_json(raw)
        result = actual_metric(ctx, fixture, documents["actual_transcript"], documents["precision_evaluation"])
        # A numerical oracle is insufficient. Actual service verification must
        # also check the currently configured independent issuer and registry.
        if modern:
            policy = ctx.bundle.evidence_policy(lease)
            reference = ctx.bound_json(fixture["independent_reference"])
            assert policy.qualification.authority_ref == reference["authority_ref"]
            mappings = tuple(ctx.c.AudioTimelineMapping.model_validate(row) for row in fixture["audio_mappings"])
            token = ctx.bundle.verify_alignment_evidence(lease, preparation.preparation_id,
                actual_transcript_artifact_id=fixture["actual_transcript_artifact_id"],
                work_validation_artifact_id=fixture["work_validation_artifact_id"], audio_mappings=mappings)
            assert token.fencing_token == lease.fencing_token
        else:
            ctx.bundle.verify(lease, preparation.preparation_id, manifest)
        if case_id == "T15-11":
            counterexamples = ctx.host().run_fault_role("actual_precision_full_population_refusal", fixture)
            assert counterexamples["max_endpoint_N_refused"] and counterexamples["full_unique_population_refused"]
            assert counterexamples["new_published_revision_count"] == 0
            result = {"actual_metric": result, "actual_service_refusals": counterexamples}
        return result
    finally:
        ctx.engine.release_run(lease)


def real_word_degradation_guard(ctx):
    fixture, manifest, _ = ctx.publication("T15-12")
    detail = ctx.engine.get_production("local-user", fixture["production_id"])
    requirements = detail.request.delivery_requirements
    assert requirements.alignment_requirement == "word_verified"
    assert "word_estimate_with_declared_gap" in requirements.allowed_degradations
    assert ctx.bundle.validators.word_degradation_allowed is True  # Read real trusted configuration; never set it.
    quality_model = "BundleQualityEvidenceV03" if manifest.schema_version == "0.3.0-candidate" else "BundleQualityEvidence"
    quality = ctx.document(manifest, "quality", quality_model)[1]
    assert quality.allowed_degradation_approval_ref and quality.allowed_degradation_approval_ref in manifest.approval_refs
    actual = ctx.transcript(manifest)
    assert actual.alignment.units == "utterance", "utterance report cannot imply measured word precision"
    assert any(word.timestamp_method == "whisper_word_estimate_not_forced_alignment" for unit in actual.transcript.utterances for word in unit.words)
    report = ctx.document(manifest, "precision_evaluation", "PrecisionEvaluationReport")[1]
    metric = actual_metric(ctx, fixture, actual, report)
    rejected = ctx.host().run_fault_role("word_degradation_without_each_admission", fixture)
    assert rejected["missing_request_permission_rejected"] and rejected["missing_trusted_service_permission_rejected"]
    assert rejected["missing_real_approval_rejected"] and rejected["new_bundle_count"] == 0
    return {"actual_utterance_metric": metric, "actual_three_guard_refusals": rejected}


def subtitle_mapping(ctx, case_id="T15-13"):
    fixture, manifest, _ = ctx.publication(case_id)
    document = ctx.transcript(manifest)
    mappings = [ctx.c.AudioTimelineMapping.model_validate(row) for row in ctx.bound_json(fixture["independent_mapping_oracle"])]
    assert mappings and {p.transformation for m in mappings for p in m.pieces} >= {"crop", "place", "encode"}
    from t15_oracles import interval
    for mapping in mappings:
        for piece in mapping.pieces:
            source = interval(piece.source_range.model_dump(), piece.source_track.intrinsic_duration_us)
            target = interval(piece.timeline_range.model_dump(), mapping.timeline_duration_us)
            assert Fraction(target[1] - target[0]) == Fraction(source[1] - source[0]) * piece.playback_rate_den / piece.playback_rate_num
            assert piece.source_sample_start is not None or piece.source_pts_start is not None
    assert document.subtitles.mapping_revision_id in {m.mapping_revision_id for m in mappings}
    if case_id == "T15-14":
        for unit in (*document.transcript.utterances, *document.transcript.gaps):
            interval(unit.intrinsic_range.model_dump(), document.transcript.duration_us)
    if case_id == "T15-15":
        from video_creator.application.bundles import serialize_subtitles
        srt, vtt, quantization = serialize_subtitles(document.subtitles)
        assert srt == ctx.artifact(manifest, "srt")[2] and vtt == ctx.artifact(manifest, "vtt")[2]
        assert tuple(quantization) == document.subtitles.quantization_errors
        assert all(abs(q.start_error_us) < 1000 and abs(q.end_error_us) < 1000 for q in quantization)
    return {"mapping_ids": [m.mapping_revision_id for m in mappings], "actual_cues": len(document.subtitles.cues)}


def semantic_sources(ctx, case_id="T15-16"):
    fixture, manifest, _ = ctx.publication(case_id)
    segments = ctx.rows(manifest, "semantic_segments", "SemanticSegmentV1")
    chunks = ctx.rows(manifest, "rag_chunks", "RagChunk")
    source_oracle = ctx.bound_json(fixture["independent_source_oracle"])
    expected = source_oracle["source_refs"]
    assert segments and chunks
    for segment in segments:
        assert [r.model_dump(mode="json") for r in segment.source_refs] == expected
        assert segment.bundle_revision_id == manifest.bundle_revision_id
    index = {segment.segment_id: segment for segment in segments}
    for chunk in chunks:
        assert [r.model_dump(mode="json") for r in chunk.source_refs] == expected
        assert set(chunk.segment_ids) <= set(index)
        assert chunk.video_ranges == tuple(index[key].video_range for key in chunk.segment_ids)
        assert chunk.audio_spans == tuple(span for key in chunk.segment_ids for span in index[key].audio_spans)
    if case_id == "T15-18":
        media = ctx.bundle._t18_runtime_handles["media"]
        for segment in segments:
            assert segment.frame_evidence_refs and segment.field_provenance["visual_description"] in {"observed", "model_inference"}
            for frame in segment.frame_evidence_refs:
                asset = ctx.bundle.assets.get("local-user", frame.video_asset_id)
                path = ctx.bundle.assets.content_path("local-user", asset.asset_id)
                actual = media.frame(asset, path, frame.at_us, frame.decoder_method_ref)
                assert actual == frame
    return {"segments": len(segments), "chunks": len(chunks)}


def independent_retrieval(ctx, case_id="T15-19"):
    fixture = ctx.fixture(case_id)
    labels = ctx.bound_json(fixture["independent_MM05_labels"])
    if not fixture.get("retrieval_endpoint"):
        raise CaseBlocked("actual_semantic_retrieval_endpoint", "ranked retrieval API ABI not yet published")
    responses = {}
    client = ctx.http()
    for topic in labels["topics"]:
        response = client.request("POST", fixture["retrieval_endpoint"], json={"topic": topic})
        assert response.status == 200
        responses[topic] = response.json()["bundle_revision_ids"]
    from t15_oracles import retrieval
    metric = retrieval(labels, responses)
    return {key: str(value) for key, value in metric.items()}
