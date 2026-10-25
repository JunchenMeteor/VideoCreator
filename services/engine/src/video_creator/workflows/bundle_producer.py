"""Produce Bundle1 materials from actual registered media and controlled ASR."""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from video_creator.application.bundles import BundleService
    from video_creator.application.engine import EngineService
    from video_creator.application.executor import OperationExecutor
    from video_creator.domain.production_authorization import (
        CurrentProductionAdmission,
        ProductionRightsFact,
    )
from video_creator.domain import contracts as c
from video_creator.domain.bundle import (
    BundlePreparationIntent,
    MaterialReceipt,
    MaterialSlot,
)
from video_creator.domain.current_final_evidence import CurrentFinalEvidenceAssessment
from video_creator.domain.errors import EngineError
from video_creator.media.bundle_evidence import BundleMediaEvidence
from video_creator.providers.asr_resources import LocalAsrResources
from video_creator.workflows.attempt_control import attempt_control, current_attempt
from video_creator.workflows.current_policy_evidence import require_bundle_plan_facts


def _record(model):
    from video_creator.application.bundles import record_sha
    return model.model_copy(update={"content_sha256": record_sha(model)})


def _json(model):
    from video_creator.application.engine import canonical
    return (canonical(model) + "\n").encode("utf-8")


def _jsonl(models):
    return b"".join(_json(model) for model in models)


def _material_artifacts(receipts, documents, artifact_ids, evidence, asr_method, right, rights):
    """Describe actual Ready receipts, preserving every copied source fact."""
    result = []
    current_rights = {value.rights_id: value for value in rights}
    for name, receipt in receipts.items():
        copies = evidence.correction_copies if evidence is not None else None
        if copies is not None and name in copies.sources:
            source = copies.sources[name][0].artifact
            if source.rights_ref not in current_rights:
                raise EngineError("correction_rights_approval_required", "Current approved declarations must explicitly cover each original source right.", 409)
            roles, rights_ref, method_ref, spec = source.roles, source.rights_ref, "correction-copy-v1", source.spec
        else:
            roles = ({"audit": "audit_summary", "transcript": "actual_transcript", "reference": "precision_reference",
                      "measurement": "precision_evaluation"}.get(name, receipt.schema_kind),)
            rights_ref, spec = right.rights_id, c.ArtifactSpec()
            method_ref = ("current-production-authorization" if name == "authorization" else
                          asr_method if name in {"transcript", "srt", "vtt", "segments", "rag"} else "actual-decoder")
        dependencies = evidence.dependencies.get(name, ()) if evidence is not None else (
            (artifact_ids["mixed"],) if name in {"transcript", "srt", "vtt", "segments", "rag"} else ())
        if copies is not None and name in copies.sources:
            dependencies = tuple(dict.fromkeys((*dependencies, *current_rights[rights_ref].license_document_artifact_ids)))
            if artifact_ids[name] in dependencies:
                raise EngineError("correction_license_cycle", "A copied permission cannot use itself as its current license evidence.", 422)
        if name == "authorization":
            dependencies = tuple(dict.fromkeys((*dependencies, artifact_ids["plan"])))
        result.append(c.BundleArtifact(artifact_id=artifact_ids[name], material_id=receipt.material_id,
                    sha256=receipt.sha256, size=receipt.size, media_type=receipt.media_type,
                    relative_path=documents[name][0], roles=roles, dependency_artifact_ids=dependencies,
                    method_ref=method_ref, rights_ref=rights_ref, spec=spec))
    return tuple(result)


@dataclass(frozen=True)
class BundleProductionResult:
    state: str
    preparation_id: str
    manifest: c.BundleManifestAny | None
    materials: tuple[MaterialReceipt, ...]
    blocker_code: str | None = None
    bundle_ref: c.BundleRef | None = None
    final_evidence: CurrentFinalEvidenceAssessment | None = None

    def __post_init__(self):
        if self.state in {"waiting_evidence", "waiting_diagnosis", "repair_required"}:
            assessment = self.final_evidence
            if (type(assessment) is not CurrentFinalEvidenceAssessment or assessment.snapshot is None
                    or assessment.snapshot.state != self.state
                    or assessment.snapshot.preparation_id != self.preparation_id
                    or assessment.snapshot.ready_material_refs != self.materials
                    or assessment.snapshot.reason_code != self.blocker_code or self.bundle_ref is not None):
                raise EngineError("current_final_evidence_result_invalid", "Waiting results retain the actual service assessment and original Ready receipts.", 409)
        elif self.manifest is None or self.final_evidence is not None:
            raise EngineError("bundle_production_result_invalid", "Only an actual incomplete final-evidence wait may omit its Manifest.", 409)


def _final_wait(assessment, manifest=None):
    snapshot = assessment.snapshot
    return BundleProductionResult(snapshot.state, snapshot.preparation_id, manifest,
                    snapshot.ready_material_refs, snapshot.reason_code, final_evidence=assessment)


def produce_bundle(
    engine: EngineService, bundle: BundleService, executor: OperationExecutor,
    resources: LocalAsrResources, media: BundleMediaEvidence, lease: c.LeaseGrant,
    *, video_asset_id: str, narration_asset_id: str, mixed_asset_id: str,
    cover_asset_id: str, asr_route_id: str, runtime_root: Path,
    reference_evidence=None,
    plan_admission: CurrentProductionAdmission | None = None,
    production_rights_fact: ProductionRightsFact | None = None,
    final_evidence_ports=None,
    production_services=None,
    cancel=None, deadline_monotonic: float | None = None,
) -> BundleProductionResult:
    with attempt_control(cancel, deadline_monotonic).activate():
        return _produce_bundle(engine, bundle, executor, resources, media, lease,
                    video_asset_id=video_asset_id, narration_asset_id=narration_asset_id,
                    mixed_asset_id=mixed_asset_id, cover_asset_id=cover_asset_id,
                    asr_route_id=asr_route_id, runtime_root=runtime_root, reference_evidence=reference_evidence,
                    plan_admission=plan_admission, production_rights_fact=production_rights_fact,
                    final_evidence_ports=final_evidence_ports, production_services=production_services)


def _produce_bundle(
    engine, bundle, executor, resources, media, lease,
    *, video_asset_id, narration_asset_id, mixed_asset_id, cover_asset_id,
    asr_route_id, runtime_root, reference_evidence=None,
    plan_admission=None, production_rights_fact=None,
    final_evidence_ports=None,
    production_services=None,
    affected_state=None, repair_continuation=None, repair_proposal=None,
):
    """Ordinary lease only; no private SQL, arbitrary authority, or fake media IDs."""
    from video_creator.application.bundle_facts import FACT_FORMAT
    from video_creator.application.bundles import serialize_subtitles
    from video_creator.application.engine import canonical, digest
    from video_creator.application.engine import identity as fresh_identity
    from video_creator.workflows.bundle_correction import rights_check_from_fact
    from video_creator.workflows.bundle_v03 import (
        bind_v03_evidence,
        finish_v03_evidence,
        measure_alignment,
        prepare_v03_evidence,
        runtime_source_gaps,
    )
    from video_creator.workflows.current_final_evidence import (
        require_final_port,
        resolve_initial_evidence,
        verify_final_evidence,
    )

    control = current_attempt()
    control.check()
    context = bundle.context(lease)
    request = engine.get_request(lease)
    if affected_state is not None:
        from video_creator.domain.affected_recipe import AffectedRepairReadSetV2
        from video_creator.domain.affected_repair import AffectedRepairReadSet

        if (type(affected_state) not in {AffectedRepairReadSet, AffectedRepairReadSetV2} or affected_state.child is None
                or affected_state.execution.binding.run_id != lease.run_id or repair_continuation is None or repair_proposal is None):
            raise EngineError("affected_child_source_invalid", "Only actual selected child facts and the original held repair command may enter child assembly.", 403)

    def identity(prefix):
        if affected_state is None:
            return fresh_identity(prefix)
        # Stable authored document addresses survive a crash; they are neither
        # Asset IDs nor authority, and all bytes still use actual child slots.
        return prefix + "-" + digest(affected_state.execution.repair_command_sha256 + ":" + prefix)[:40]

    current_v2 = plan_admission is not None or production_rights_fact is not None
    if current_v2:
        require_final_port(final_evidence_ports)
        from video_creator.workflows.affected_production import require_services

        require_services(final_evidence_ports, lease, production_services)
    elif final_evidence_ports is not None:
        raise EngineError("current_final_evidence_scope_conflict", "A current held port cannot silently upgrade the original v1 producer.", 409)
    v03 = request.request_format_version == c.V03_SCHEMA_VERSION
    resolved = bundle.evidence_policy(lease) if v03 and not current_v2 else None
    if not v03 and reference_evidence is not None:
        raise EngineError("evidence_version_conflict", "New reference materials cannot alter a historical strict request.", 409)
    revisions = bundle.creative_revisions(lease)
    selected = {value.kind: value for value in revisions}
    required = {"insight", "brief", "plan", "script", "storyboard", "quality"}
    if plan_admission is not None or production_rights_fact is not None:
        same_run = {value.revision_id: value for value in revisions}
        selected = {kind: same_run[revision_id] for kind in required
                    if (revision_id := "autonomous." + kind + "." + lease.run_id) in same_run
                    and same_run[revision_id].kind == kind}
    if not required <= set(selected):
        raise EngineError("creative_versions_missing", "Actual creative versions are required before producing materials.", 409)
    script_revision = selected["script"]
    if not isinstance(script_revision.body, dict) or not isinstance(script_revision.body.get("text"), str):
        raise EngineError("script_material_missing", "The actual immutable script has no text.", 422)
    revision_refs = tuple(c.RevisionRef(revision_id=value.revision_id, kind=value.kind, content_sha256=digest(canonical(value))) for value in selected.values())
    refs = {value.kind: value for value in revision_refs}
    approval_refs, feedback_refs = bundle.approval_refs(lease), bundle.feedback_refs(lease)
    plan_admission, production_rights_fact = require_bundle_plan_facts(
                    plan_admission, production_rights_fact, selected["plan"], engine=engine,
                    context=context, request=request, lease=lease)
    if (plan_admission is not None and plan_admission.source == "human_review"
            and plan_admission.human_approval_ref not in approval_refs):
        raise EngineError("production_human_approval_missing", "The current human bridge must retain its actual stored ApprovalRef in Bundle provenance.", 403)
    policy_authorization = plan_admission is not None and plan_admission.source in {"owner_policy", "delegated_project"}
    rights_values = selected["plan"].body.get("rights", ()) if isinstance(selected["plan"].body, dict) else ()
    rights = tuple(c.RightsSnapshot.model_validate(value) for value in rights_values)
    if not rights or len({value.rights_id for value in rights}) != len(rights):
        raise EngineError("rights_evidence_missing", "The actual plan must retain explicit rights assertions.", 409)
    right = rights[0]
    assets = {"video": bundle.asset(lease, video_asset_id), "narration": bundle.asset(lease, narration_asset_id),
              "mixed": bundle.asset(lease, mixed_asset_id), "cover": bundle.asset(lease, cover_asset_id)}
    paths = {name: bundle.content_path(lease, value.asset_id) for name, value in assets.items()}
    if assets["narration"].asset_id == assets["mixed"].asset_id:
        raise EngineError("bundle_audio_roles_invalid", "Narration and final mix must be independently produced.", 422)
    timeline = assets["video"].probe.duration_us
    if not timeline or assets["mixed"].probe.duration_us != timeline:
        raise EngineError("bundle_audio_roles_invalid", "Actual video and final mix must have the same work duration.", 422)
    clocks = {name: media.clock(assets[name], paths[name]) for name in ("video", "narration", "mixed")}
    tracks = {name: c.AudioTrackRef(asset_id=assets[name].asset_id, sha256=assets[name].sha256,
                                   stream_index=clocks[name][0].stream_index,
                                   kind={"video": "video_encoded", "narration": "narration", "mixed": "mix_master"}[name],
                                   intrinsic_duration_us=clocks[name][1], clock=clocks[name][0], method_ref="actual-decoder")
              for name in clocks}
    if tracks["mixed"].intrinsic_duration_us != timeline:
        raise EngineError("audio_clock_invalid", "Actual mixed samples differ from the work duration.", 422)
    if not all(media.audio_clock_authority(track, paths[name]) for name, track in tracks.items()):
        raise EngineError("audio_clock_invalid", "An actual registered track could not be independently re-decoded.", 422)
    if affected_state is None:
        operation_input = digest(json.dumps({"audio_sha256": assets["mixed"].sha256, "resource_manifest_sha256": resources.manifest_sha256}, sort_keys=True))
        step_key = "bundle-actual-asr"
        engine.begin_step(lease, step_key, operation_input)
        intent = c.OperationIntent(step_key=step_key, dedupe_key="bundle-asr-" + lease.run_id,
                                   input_sha256=operation_input, route_id=asr_route_id, reserved_cost=c.Money(amount="0"))
        driver = resources.driver(paths["mixed"], storage_root=media.root, runtime_root=runtime_root,
                                  expected_audio_sha256=assets["mixed"].sha256, timeout_seconds=control.remaining(60),
                                  cancel=control.cancel_requested, deadline_monotonic=control.deadline_monotonic)
        control.check()
        observation = executor.execute(lease, intent, driver)
        if observation.status != "succeeded":
            raise EngineError("actual_asr_unavailable", "Keep the original controlled ASR outcome without ordinary-lease reads or resubmission.", 409, "reconcile")
        operation = engine.prepare_operation(lease, intent)
        if observation.status != "succeeded" or not operation["settled"] or not isinstance(observation.result_json, dict):
            raise EngineError("actual_asr_unavailable", "Actual controlled ASR did not succeed; keep its original operation outcome.", 409, "reconcile")
        actual = observation.result_json
    else:
        from video_creator.workflows.bundle_affected import child_asr

        actual, operation, operation_input = child_asr(final_evidence_ports, lease, repair_continuation,
                    repair_proposal, production_services, affected_state, resources=resources, media=media,
                    runtime_root=runtime_root, mixed=assets["mixed"], timeline=timeline)
    control.check()
    if v03 and not isinstance(actual.get("runtime", {}).get("execution_identity"), dict):
        raise EngineError("alignment_required", "The actual child did not observe an execution identity.", 409)
    asr_method = actual["runtime"]["execution_identity"]["method_id"] if v03 else "actual-asr"
    if affected_state is None:
        engine.complete_step(lease, step_key, result_json=actual)
    if actual["input_audio_sha256"] != assets["mixed"].sha256 or actual["duration_us"] != timeline:
        raise EngineError("actual_asr_binding_invalid", "Actual ASR differs from the independently decoded final mix.", 422)
    bundle_id, revision_id = identity("bundle"), identity("bundle-revision")
    transcript_id, alignment_id, mapping_id = identity("transcript"), identity("alignment"), identity("mapping")
    artifact_ids = {name: identity("artifact") for name in ("video", "narration", "mixed", "cover", "insight", "brief", "plan", "script", "transcript", "srt", "vtt", "summary", "sources", "shots", "segments", "rag", "quality", "audit", "policy", "qualification", "benchmark", "work_validation", "reference", "measurement")}
    if affected_state is not None:
        parent_assembly = affected_state.parent.assembly
        bundle_id, revision_id = affected_state.child.intent.bundle_id, affected_state.child.intent.bundle_revision_id
        artifact_ids.update(parent_assembly.document_artifact_ids)
        role_names = {"video": "video", "narration_audio": "narration", "mixed_audio": "mixed", "cover": "cover"}
        artifact_ids.update({role_names[value.roles[0]]: value.artifact_id for value in parent_assembly.media_artifacts})
    if current_v2 and v03:
        # Immutable authored addresses can be recovered from the saved complete
        # allocation set before the first final speech bytes become Ready.
        transcript_id = "transcript-" + digest(artifact_ids["transcript"])[:40]
        alignment_id = "alignment-" + digest(artifact_ids["transcript"] + ":prediction")[:40]
    if policy_authorization and affected_state is None:
        artifact_ids["authorization"] = identity("artifact")
    utterances = tuple(c.TranscriptUtterance(utterance_id=f"utterance-{index}", text=segment["text"],
                      intrinsic_range=c.MediaRange(start_us=segment["start_us"], end_us=segment["end_us"]),
                      words=tuple(c.TranscriptWord(word_id=f"word-{index}-{number}", text=word["text"],
                      intrinsic_range=c.MediaRange(start_us=word["start_us"], end_us=word["end_us"]), timestamp_method=actual["timestamp_method"])
                      for number, word in enumerate(segment["words"]))) for index, segment in enumerate(actual["segments"]))
    transcript = _record(c.ActualTranscriptRevision(transcript_revision_id=transcript_id, input_audio_asset_id=mixed_asset_id,
                      input_audio_sha256=assets["mixed"].sha256, input_track=tracks["mixed"], duration_us=timeline,
                      language=actual["language"], text=actual["text"], utterances=utterances, method_ref=asr_method,
                      approved_script_revision_ref=refs["script"], confidence_unavailable_reason="The admitted ASR does not provide a calibrated transcript confidence.",
                      source_gaps=runtime_source_gaps(actual) if v03 else ("Word boundaries are estimates; no independent precision report is installed.",), content_sha256="0" * 64))
    alignment_type = c.AlignmentRevisionV03 if v03 else c.AlignmentRevision
    precision_type = c.PrecisionAssessmentV03 if v03 else c.PrecisionAssessment
    alignment = _record(alignment_type(alignment_revision_id=alignment_id, actual_transcript_revision_id=transcript_id,
                      transcript_content_sha256=transcript.content_sha256, input_audio_asset_id=mixed_asset_id,
                      input_audio_sha256=assets["mixed"].sha256, units="utterance",
                      boundaries=tuple(c.AlignmentUnit(unit_id=f"alignment-{index}", transcript_unit_id=value.utterance_id, intrinsic_range=value.intrinsic_range) for index, value in enumerate(utterances)),
                      timestamp_method=actual["timestamp_method"], method_ref=asr_method,
                      precision=precision_type(status="not_measured", units="utterance", limitations=("Actual inference is not independent boundary evaluation.",)),
                      confidence_unavailable_reason="Independent timing confidence has not been measured.", content_sha256="0" * 64))
    raw_end = Fraction(tracks["mixed"].clock.decoded_sample_count * 1_000_000, tracks["mixed"].clock.sample_rate)
    end_error = Decimal(timeline) - Decimal(raw_end.numerator) / Decimal(raw_end.denominator)
    piece = c.AudioMappingPiece(piece_id="actual-mix-placement", source_track=tracks["mixed"],
                      source_range=c.MediaRange(start_us=0, end_us=timeline), timeline_range=c.MediaRange(start_us=0, end_us=timeline),
                      source_sample_start=0, source_sample_end=tracks["mixed"].clock.decoded_sample_count,
                      transformation="encode", end_rounding_error_us=end_error, method_ref="actual-decoder")
    video_audio_start = Fraction(tracks["video"].clock.origin_pts or 0) * Fraction(tracks["video"].clock.timebase_num or 1, tracks["video"].clock.timebase_den or 1)
    if video_audio_start != 0:
        raise EngineError("audio_mapping_required", "This assembly path requires a separately verified nonzero encoding-origin mapping.", 409)
    mapping = _record(c.AudioTimelineMapping(mapping_revision_id=mapping_id, target_video_asset_id=video_asset_id,
                      target_track=tracks["video"], timeline_duration_us=timeline, pieces=(piece,), encoding_origin_offset_us=0,
                      method_ref="actual-decoder", content_sha256="0" * 64))
    cues = tuple(c.SubtitleCue(cue_id=f"cue-{index}", text=value.text, timeline_range=value.intrinsic_range,
                              transcript_unit_refs=(value.utterance_id,)) for index, value in enumerate(utterances))
    subtitle_id = ("subtitle-" + digest(artifact_ids["srt"] + ":" + artifact_ids["vtt"])[:40]
                   if current_v2 and v03 else identity("subtitle"))
    subtitles = c.SubtitleTrack(subtitle_revision_id=subtitle_id, actual_transcript_revision_id=transcript_id,
                      alignment_revision_id=alignment_id, mapping_revision_id=mapping_id, timeline_duration_us=timeline, cues=cues,
                      srt_artifact_id=artifact_ids["srt"], vtt_artifact_id=artifact_ids["vtt"],
                      quantization_errors=tuple(c.SubtitleQuantization(cue_id=value.cue_id, start_error_us=0, end_error_us=0) for value in cues), content_sha256="0" * 64)
    srt, vtt, quantization = serialize_subtitles(subtitles)
    subtitles = _record(subtitles.model_copy(update={"quantization_errors": tuple(quantization)}))
    source_refs = tuple(c.BundleSourceRef(**value.model_dump(exclude={"confirmed_facts"}), binding_kind="provided_input",
                         fact_refs=tuple(c.SourceFactRef(text=fact, source_revision=value.topic_revision or value.article_revision or "caller-input",
                                    confirmation_kind="caller_asserted", local_fact_id=_local_fact(value, fact)) for fact in value.confirmed_facts),
                         input_asset_ids=request.inputs.asset_ids) for value in request.source_bindings)
    storyboard = selected["storyboard"].body
    shots_data = storyboard.get("shots", ()) if isinstance(storyboard, dict) else ()
    if not shots_data:
        raise EngineError("shot_ranges_missing", "Actual storyboard ranges are required for semantic references.", 409)
    shots = []
    for item in shots_data:
        control.check()
        span = c.MediaRange.model_validate(item["timeline_range"])
        if span.end_us > timeline:
            raise EngineError("shot_range_invalid", "Actual shot range exceeds the work.", 422)
        frame = media.frame(assets["video"], paths["video"], span.start_us, "actual-decoder")
        if not media.frame_validator(frame, paths["video"]):
            raise EngineError("frame_evidence_invalid", "Actual final-frame byte evidence could not be rechecked.", 422)
        shots.append(_record(c.ShotEvidence(shot_revision_id=item["shot_revision_id"], video_asset_id=video_asset_id,
                    timeline_range=span, source_refs=source_refs, frame_evidence_refs=(frame,), content_sha256="0" * 64)))
    topic = str(selected["brief"].body.get("topic", request.goal))
    thesis = str(selected["insight"].body.get("main_thesis", request.goal))
    topic_origin = "derived" if "topic" in selected["brief"].body else "user_provided"
    thesis_origin = "derived" if "main_thesis" in selected["insight"].body else "user_provided"
    semantic = []
    for index, value in enumerate(utterances):
        control.check()
        matching = tuple(shot for shot in shots if shot.timeline_range.start_us < value.intrinsic_range.end_us and shot.timeline_range.end_us > value.intrinsic_range.start_us)
        if not matching:
            raise EngineError("semantic_shot_missing", "Recognized speech has no actual storyboard range.", 422)
        frame = media.frame(assets["video"], paths["video"], value.intrinsic_range.start_us, "actual-decoder")
        span = c.SemanticAudioSpan(track=tracks["mixed"], intrinsic_range=value.intrinsic_range, timeline_range=value.intrinsic_range, mapping_piece_ids=(piece.piece_id,))
        semantic.append(_record(c.SemanticSegmentV1(segment_id=f"segment-{index}", bundle_revision_id=revision_id,
                    video_asset_id=video_asset_id, video_range=value.intrinsic_range, audio_spans=(span,),
                    shot_revision_ids=tuple(shot.shot_revision_id for shot in matching), transcript_unit_refs=(value.utterance_id,),
                    speech_text=value.text, visual_description=f"Observed final frame {frame.width}x{frame.height} rgb24; no scene interpretation asserted.",
                    summary=value.text, topic=topic, main_thesis=thesis, source_refs=source_refs, alignment_revision_id=alignment_id,
                    field_provenance={"speech_text": "observed", "summary": "derived", "topic": topic_origin, "main_thesis": thesis_origin, "visual_description": "observed"},
                    frame_evidence_refs=(frame,), rights_ref=right.rights_id, retrieval_text=topic + "\n" + thesis + "\n" + value.text, content_sha256="0" * 64)))
    chunks = tuple(_record(c.RagChunk(chunk_id=f"chunk-{index}", chunk_type="speech_segment", bundle_revision_id=revision_id,
                    segment_ids=(value.segment_id,), text=value.speech_text, source_refs=source_refs, video_ranges=(value.video_range,),
                    audio_spans=value.audio_spans, language=actual["language"], rights_ref=right.rights_id, access_scope_ref=context.project_id,
                    valid_until_us=right.expires_at_us,
                    field_provenance={"text": "observed"}, method_refs=(asr_method, "actual-decoder"), content_sha256="0" * 64)) for index, value in enumerate(semantic))
    quality = _record(c.BundleQualityEvidence(quality_revision_ref=refs["quality"], checks=tuple(
                    c.QualityCheck(check_id=name, status="not_measured" if name in {"alignment", "rights"} else "verified",
                    method_ref=asr_method if name in {"actual_transcript", "alignment"} else "actual-decoder",
                    evidence_artifact_ids=(artifact_ids["transcript"],), findings=("Assembly evidence only; not independent user acceptance.",))
                    for name in ("media_integrity", "audio_timeline", "actual_transcript", "alignment", "subtitles", "semantic_sources", "rights")), content_sha256="0" * 64))
    documents = {
        "insight": ("Creative/insight.json", "creative_revision", _json(selected["insight"])),
        "brief": ("Creative/brief.json", "creative_revision", _json(selected["brief"])),
        "plan": ("Creative/production-plan.json", "creative_revision", _json(selected["plan"])),
        "script": ("Text/approved-script.json", "approved_script", _json(_record(c.ApprovedScriptDocument(script_revision_ref=refs["script"], text=script_revision.body["text"], content_sha256="0" * 64)))),
        "transcript": ("Text/actual-transcript.json", "actual_transcript_v03" if v03 else "actual_transcript",
                    _json(c.ActualTranscriptDocumentV03(schema_version=c.V03_SCHEMA_VERSION, transcript=transcript, alignment=alignment, subtitles=subtitles)
                    if v03 else c.ActualTranscriptDocument(transcript=transcript, alignment=alignment, subtitles=subtitles))),
        "srt": ("Text/subtitles.srt", "srt", srt), "vtt": ("Text/subtitles.vtt", "vtt", vtt),
        "summary": ("Semantics/work-summary.json", "work_summary", _json(_record(c.WorkSummary(bundle_revision_id=revision_id, summary=actual["text"], topic=topic, main_thesis=thesis, source_refs=source_refs, content_sha256="0" * 64)))),
        "sources": ("Semantics/source-bindings.json", "source_bindings", _json(_record(c.SourceBindingsDocument(bundle_revision_id=revision_id, source_refs=source_refs, content_sha256="0" * 64)))),
        "shots": ("Semantics/shots.jsonl", "shots", _jsonl(shots)),
        "segments": ("Semantics/semantic-segments.jsonl", "semantic_segments", _jsonl(semantic)),
        "rag": ("Semantics/rag-chunks.jsonl", "rag_chunks", _jsonl(chunks)),
        "quality": ("Checks/quality-report.json", "quality", _json(quality)),
        "audit": ("Checks/assembly-audit.json", "audit_summary", (json.dumps({"summary": "Actual registered-media assembly; precision/rights not measured by this producer.", "operation_ids": [operation["id"]], "cost_status": "confirmed_no_charge", "method_refs": [asr_method, "actual-decoder"], "source_gaps": ["No independent precision report; word estimates are not forced alignment."]}, ensure_ascii=False) + "\n").encode()),
    }
    if policy_authorization:
        # Original BundleService reads the actual issuer document, preserving
        # V01/V02 grammar. No future Manifest hash or fabricated approval.
        documents["authorization"] = ("Checks/production-authorization.json", "production_authorization", None)
    slots = tuple(MaterialSlot(artifact_id=artifact_ids[name], relative_path=path, schema_kind=kind,
                         media_type="application/x-ndjson" if kind in {"shots", "semantic_segments", "rag_chunks"} else {"srt": "text/srt", "vtt": "text/vtt"}.get(kind, "application/json")) for name, (path, kind, _) in documents.items())
    evidence = None
    if v03:
        evidence = prepare_v03_evidence(bundle, lease, resolved, context, request, bundle_id, revision_id, slots,
                    artifact_ids, tuple(value.asset_id for value in assets.values()), actual, transcript, alignment,
                    instance_id=engine.instance_id, reference_evidence=reference_evidence,
                    selected_child=None if affected_state is None else affected_state.child,
                    defer_measurement=current_v2)
        preparation, alignment = evidence.preparation, evidence.alignment
        document = c.ActualTranscriptDocumentV03(schema_version=c.V03_SCHEMA_VERSION, transcript=transcript,
                    alignment=alignment, subtitles=subtitles)
        documents["transcript"] = ("Text/actual-transcript.json", "actual_transcript_v03", _json(document))
        documents.update(evidence.documents)
    else:
        preparation_intent = BundlePreparationIntent(bundle_id=bundle_id, bundle_revision_id=revision_id,
                    request_revision_id=context.request_revision_id, input_sha256=digest(canonical(request)), material_slots=slots,
                    media_asset_ids=tuple(value.asset_id for value in assets.values()))
        if affected_state is None:
            preparation = bundle.prepare(lease, preparation_intent)
        else:
            target = affected_state.child.intent
            if (target.bundle_id, target.bundle_revision_id, target.request_revision_id, target.input_sha256,
                    target.media_asset_ids, target.material_slots) != (
                    preparation_intent.bundle_id, preparation_intent.bundle_revision_id,
                    preparation_intent.request_revision_id, preparation_intent.input_sha256,
                    preparation_intent.media_asset_ids, preparation_intent.material_slots):
                raise EngineError("affected_child_allocation_invalid", "The real atomic child remains the only preparation for actual regenerated assembly.", 422)
            preparation, preparation_intent = affected_state.child.preparation, target
    if evidence is not None:
        preparation_intent = evidence.intent
    receipts = {} if evidence is None else dict(evidence.receipts)
    if affected_state is not None:
        from video_creator.workflows.bundle_affected import (
            preserve_documents,
            ready_child_sources,
        )

        preserve_documents(affected_state, documents, artifact_ids)
        receipts.update(ready_child_sources(bundle, lease, affected_state, documents, artifact_ids))
        original_pair = affected_state.parent.assembly
        if evidence is not None and original_pair.format == "current-final-assembly-context-v2":
            if evidence.correction_origin is not None and (evidence.correction_origin, evidence.correction_reason) != (
                    original_pair.corrected_from, original_pair.correction_reason):
                raise EngineError("correction_recovery_binding_invalid", "Actual child preserves the exact original author's correction source/reason pair.", 422)
            evidence.correction_origin, evidence.correction_reason = original_pair.corrected_from, original_pair.correction_reason
    if policy_authorization:
        control.check()
        receipts["authorization"] = bundle.stage_production_authorization(
                    lease, preparation.preparation_id, artifact_ids["authorization"],
                    plan_admission_ref=plan_admission.admission_ref)
    # Late WorkValidation/measurement/Quality cannot approve future files. First
    # stage immutable inputs and copied sources, then ask for actual Ready facts.
    alignment_first = current_v2 and v03
    late_alignment_documents = {"transcript", "srt", "vtt", "segments", "rag", "measurement"} if alignment_first else set()
    for name, (_, _, data) in documents.items():
        control.check()
        if name not in receipts and name not in {"quality", "audit"} | late_alignment_documents and data is not None:
            receipts[name] = bundle.stage_material(lease, preparation.preparation_id, artifact_ids[name], data)
    artifacts = []
    media_paths = {"video": "Media/video.mp4", "narration": "Media/narration.wav", "mixed": "Media/mixed-audio.wav", "cover": "Media/cover.jpg"}
    for name, value in assets.items():
        spec = c.ArtifactSpec(duration_us=value.probe.duration_us, width=value.probe.width, height=value.probe.height,
                              audio_clock=clocks[name][0] if name in clocks else None)
        artifacts.append(c.BundleArtifact(artifact_id=artifact_ids[name], asset_id=value.asset_id, sha256=value.sha256, size=value.size,
                         media_type=value.media_type, relative_path=media_paths[name], roles=({"video": "video", "narration": "narration_audio", "mixed": "mixed_audio", "cover": "cover"}[name],), method_ref="actual-decoder", rights_ref=right.rights_id, spec=spec))
    media_artifacts = tuple(artifacts)
    ready_artifacts = media_artifacts + _material_artifacts(receipts, documents, artifact_ids, evidence, asr_method, right, rights)
    required_uses = ("derivative", "export", "standalone_audio", "rag_index")
    if evidence is not None and evidence.correction_copies is not None:
        required_uses += ("redistribution",)
    rights_fact = bundle.verify_rights_evidence(lease, preparation.preparation_id,
                    rights=rights, approval_refs=approval_refs, creative_revision_refs=revision_refs,
                    artifacts=ready_artifacts, required_uses=required_uses)
    rights_check = rights_check_from_fact(rights_fact, instance_id=engine.instance_id, context=context,
                    lease=lease, request_sha256=digest(canonical(request)), preparation_id=preparation.preparation_id,
                    rights=rights, approval_refs=approval_refs, revision_refs=revision_refs,
                    artifacts=ready_artifacts, required_uses=required_uses)
    assembly_checks = tuple(rights_check if check.check_id == "rights" else check for check in quality.checks)
    validation_actual, validation_operation_id, alignment_method = actual, operation["id"], None
    if current_v2:
        from video_creator.workflows.bundle_recovery import persist_initial_assembly

        assembly = persist_initial_assembly(final_evidence_ports, engine=engine, bundle=bundle,
                    context=context, request=request, lease=lease, preparation=preparation,
                    intent=preparation_intent, plan_admission=plan_admission,
                    artifact_ids=artifact_ids, documents=documents, media_artifacts=media_artifacts,
                    mapping=mapping, actual=actual, operation=operation,
                    operation_input=operation_input, resources=resources, evidence=evidence,
                    right_fact=rights_fact, rights=rights, revision_refs=revision_refs,
                    approval_refs=approval_refs, feedback_refs=feedback_refs,
                    source_refs=source_refs, quality_ref=refs["quality"], timeline=timeline,
                    policy_authorization=policy_authorization)
        if alignment_first:
            from video_creator.workflows.alignment_documents import speech_documents
            from video_creator.workflows.registered_alignment import (
                run_alignment,
                runtime_actual,
            )

            # Pre-CTC assembly is now immutable. Independent evaluation sources
            # remain on the producer side and never enter the inference request.
            aligned, _file, ctc_observation, validation_operation_id = run_alignment(
                final_evidence_ports, production_services, lease,
                preparation_id=preparation.preparation_id, transcript=transcript,
                prediction=alignment, mapping=mapping)
            alignment = measure_alignment(evidence, aligned)
            document = speech_documents(documents, document, alignment, mapping,
                assembly=assembly, media=media, video=assets["video"], video_path=paths["video"],
                bundle_revision_id=revision_id, project_id=context.project_id)
            subtitles = document.subtitles
            validation_actual = runtime_actual(actual, ctc_observation)
            alignment_method = require_final_port(final_evidence_ports).registered_initial_alignment_method(
                lease, preparation.preparation_id)
            if alignment_method.method_id != aligned.method_ref:
                raise EngineError("alignment_method_conflict", "Only the original settled CTC ledger-derived method may enter the final Manifest.", 422)
            for name in ("transcript", "srt", "vtt", "segments", "rag"):
                if name not in receipts:
                    receipts[name] = bundle.stage_material(lease, preparation.preparation_id,
                        artifact_ids[name], documents[name][2])
            for name in ("reference",):
                if name in documents and name not in receipts and documents[name][2] is not None:
                    receipts[name] = bundle.stage_material(lease, preparation.preparation_id,
                        artifact_ids[name], documents[name][2])
                    evidence.receipts[name] = receipts[name]
        resolution = resolve_initial_evidence(final_evidence_ports, engine=engine, bundle=bundle,
                    context=context, request=request, lease=lease, preparation=preparation,
                    intent_sha256=digest(canonical(preparation_intent)),
                    registration_sha256=plan_admission.registration_sha256)
        if type(resolution) is CurrentFinalEvidenceAssessment:
            # No legacy _block/verify has run, and no quality/report placeholder
            # is staged as Ready. Backend alone persists this real checkpoint.
            return _final_wait(resolution)
        resolved = resolution.resolved
        if evidence is not None:
            bind_v03_evidence(evidence, bundle, lease, resolved, request, validation_actual)
            documents.update(evidence.documents)
            # Actual registry documents are inputs to WorkValidation; allocation
            # addresses alone never substitute for their real licensed bytes.
            for name, (_, _, data) in documents.items():
                control.check()
                if name not in receipts and name not in {"quality", "audit"} and data is not None:
                    receipts[name] = bundle.stage_material(lease, preparation.preparation_id, artifact_ids[name], data)
    if evidence is not None:
        report_id = None
        if current_v2:
            report_id = bundle.material_allocation(lease, preparation.preparation_id,
                                                  artifact_ids["work_validation"]).material_id
        extra_documents, quality = finish_v03_evidence(evidence, context, request, document, mapping, validation_actual,
                    validation_operation_id, lease, refs["quality"], artifact_ids, assembly_checks,
                    work_report_id=report_id, source_operation_ids=(operation["id"],))
        documents.update(extra_documents)
    else:
        quality = _record(quality.model_copy(update={"checks": assembly_checks}))
    documents["quality"] = ("Checks/quality-report.json", "quality", _json(quality))
    documents["audit"] = ("Checks/assembly-audit.json", "audit_summary", (json.dumps({
                    "summary": "Actual registered-media assembly and scoped pre-quality rights observation; final rights revalidation is still required.",
                    "operation_ids": [operation["id"]], "cost_status": "confirmed_no_charge",
                    "method_refs": [asr_method, "actual-decoder", "bundle-rights-v1"],
                    "findings": list(rights_fact.limitations), "source_gaps": list(rights_check.findings)
                    if rights_check.status != "verified" else []}, ensure_ascii=False) + "\n").encode())
    if affected_state is not None:
        preserve_documents(affected_state, documents, artifact_ids)
    stage_order = sorted(documents, key=lambda name: name in {"quality", "audit"}) if current_v2 else tuple(documents)
    for name in stage_order:
        _, _, data = documents[name]
        control.check()
        if name not in receipts:
            receipts[name] = bundle.stage_material(lease, preparation.preparation_id, artifact_ids[name], data)
    artifacts = media_artifacts + _material_artifacts(receipts, documents, artifact_ids, evidence, asr_method, right, rights)
    copied_methods = () if evidence is None or evidence.correction_copies is None else (
                    c.MethodEvidence(method_id="correction-copy-v1", kind="observed", tool_name="BundleService",
                         tool_version=FACT_FORMAT, config_sha256=evidence.correction_copies.fact.source_set_sha256,
                         evidence_artifact_ids=tuple(evidence.correction_copies.slots[name].artifact_id
                             for name in evidence.correction_copies.ordered_names),
                         limitations=evidence.correction_copies.fact.limitations),)
    authorization_methods = () if not policy_authorization else (
                    c.MethodEvidence(method_id="current-production-authorization", kind="observed",
                         tool_name="BundleService", tool_version="production-authorization-material-v1",
                         config_sha256=plan_admission.admission_ref.content_sha256,
                         evidence_artifact_ids=(artifact_ids["authorization"],),
                         limitations=("Original Backend admission document; execution permission does not verify media quality or legal rights.",)),)
    roles = {"video": ("video",), "narration_audio": ("narration",), "mixed_audio": ("mixed",), "approved_script": ("script",), "actual_transcript": ("transcript",), "subtitles": ("srt", "vtt"), "semantic_manifest": ("segments",), "rag_chunks": ("rag",)}
    version_fields = {} if evidence is None else {"schema_version": c.V03_SCHEMA_VERSION,
                    "evidence_policy_revision_ref": resolved.policy_ref, "qualification_ref": resolved.qualification,
                    "benchmark_binding": evidence.benchmark_binding,
                    "benchmark_document_artifact_id": artifact_ids["benchmark"], "policy_document_artifact_id": artifact_ids["policy"],
                    "qualification_document_artifact_id": artifact_ids["qualification"], "work_validation_document_artifact_id": artifact_ids["work_validation"]}
    manifest_type = c.BundleManifestV03 if v03 else c.BundleManifest
    manifest = manifest_type(**version_fields, instance_id=engine.instance_id, bundle_id=bundle_id, bundle_revision_id=revision_id,
                     project_id=context.project_id, production_id=context.production_id, run_id=lease.run_id,
                     request_revision_id=context.request_revision_id, request_sha256=digest(canonical(request)), workflow_version="registered-media-bundle-v1",
                     created_at_us=assembly.manifest_created_at_us if current_v2 else engine.clock(), timeline_duration_us=timeline, creative_revision_refs=revision_refs,
                     approval_refs=approval_refs, feedback_revision_refs=feedback_refs, source_refs=source_refs, requested_outputs=request.outputs,
                     outputs=tuple(c.BundleOutput(role=role, artifact_ids=tuple(artifact_ids[name] for name in names)) for role, names in roles.items()),
                     artifacts=artifacts, audio_mappings=(mapping,), rights=rights, quality_ref=refs["quality"],
                     methods=(c.MethodEvidence(method_id=asr_method, kind="observed", tool_name="faster-whisper", tool_version=actual["runtime"]["versions"]["faster-whisper"],
                         model_repository="Systran/faster-whisper-small", model_revision=resources.model_revision, resource_manifest_sha256=resources.manifest_sha256,
                         operation_ids=(operation["id"],), input_artifact_ids=(artifact_ids["mixed"],), config_sha256=operation_input,
                         limitations=("Word estimates; per-work precision is recorded separately in Alignment.",) if v03 else ("Word estimates; precision not independently measured.",)),
                     c.MethodEvidence(method_id="actual-decoder", kind="observed", tool_name="PyAV+FFmpeg", tool_version=actual["runtime"]["versions"]["av"],
                         resource_manifest_sha256=resources.manifest_sha256, config_sha256=digest("bundle-source-clock-and-frame-v1"),
                         limitations=("Observed media/schema consistency; not perceptual quality or rights verification.",)),
                     c.MethodEvidence(method_id="bundle-rights-v1", kind="observed", tool_name="BundleService",
                         tool_version=FACT_FORMAT, config_sha256=rights_fact.context.context_sha256,
                         evidence_artifact_ids=rights_fact.evidence_artifact_ids,
                         limitations=rights_fact.limitations)) + copied_methods + authorization_methods)
    if current_v2:
        manifest = manifest.model_copy(update={"methods": assembly.methods + (() if alignment_method is None else (alignment_method,))})
    if current_v2:
        from video_creator.workflows.component_diagnosis import prepare_initial

        prepare_initial(final_evidence_ports, lease, preparation.preparation_id, production_services)
        assessment = verify_final_evidence(final_evidence_ports, manifest, engine=engine, bundle=bundle,
                    context=context, request=request, lease=lease, preparation=preparation,
                    intent_sha256=digest(canonical(preparation_intent)),
                    registration_sha256=plan_admission.registration_sha256)
        if assessment.snapshot is not None:
            return _final_wait(assessment, manifest)
        control.check()
        reference = bundle.publish(lease, assessment.verified_material)
        return BundleProductionResult("published", preparation.preparation_id, manifest,
                    tuple(receipts.values()), bundle_ref=reference)
    try:
        control.check()
        if evidence is not None:
            bundle.verify_alignment_evidence(lease, preparation.preparation_id,
                    actual_transcript_artifact_id=artifact_ids["transcript"],
                    work_validation_artifact_id=artifact_ids["work_validation"], audio_mappings=(mapping,))
        verified = bundle.verify(lease, preparation.preparation_id, manifest)
    except EngineError as error:
        if error.code != "alignment_required":
            raise
        return BundleProductionResult("waiting_user", preparation.preparation_id, manifest, tuple(receipts.values()), error.code)
    control.check()
    reference = bundle.publish(lease, verified)
    return BundleProductionResult("published", preparation.preparation_id, manifest, tuple(receipts.values()), bundle_ref=reference)


def _local_fact(binding, fact):
    # Use the backend's unique source identity algorithm, not a second interpretation.
    from video_creator.application.bundles import local_fact_id
    return local_fact_id(binding, fact)


_REQUIRED = object()


def _require_v2v3_arguments(values):
    """Keep the original v0.2/v0.3 call-site TypeError for an omitted master.

    The sole `produce` entry serves both dispatches, so the v2/v3 arguments
    cannot stay positional-without-default. A private sentinel keeps them
    semantically required: an omitted argument fails here with the same
    TypeError class and the exact argument name instead of silently reaching
    `produce_bundle` as `None`.
    """
    missing = [name for name, value in values if value is _REQUIRED]
    if missing:
        raise TypeError('produce() missing required keyword argument(s) for the v0.2/v0.3 '
                        'consumer: ' + ', '.join(missing))


def create_registered_media_producer(*, engine, bundle, executor, resource_manifest_path: Path | None,
                                     resource_manifest_sha256: str | None, runtime_manifest_sha256: str | None,
                                     storage_root: Path, runtime_root: Path, final_evidence_ports=None,
                                     production_services=None, local_material_context=None):
    """Trusted backend factory: fixed code/resources, no caller-selected module."""
    if local_material_context is None:
        # The original v0.2/v0.3 source path keeps loading its exact ASR
        # resources and behaviour unchanged.
        from video_creator.providers.asr_resources import load_asr_resources

        resources = load_asr_resources(resource_manifest_path, resource_manifest_sha256, runtime_manifest_sha256)
        media = BundleMediaEvidence(resources.python, storage_root)
    else:
        # A silent local 0.4 work never loads ASR resources; its zero-null ASR
        # registration is a real absence. Speech works call the lazy loader
        # below inside their own branch, after the real route/registration check.
        resources = None

        def local_asr_resources():
            if (resource_manifest_path is None or resource_manifest_sha256 is None
                    or runtime_manifest_sha256 is None):
                return None
            from video_creator.providers.asr_resources import load_asr_resources

            return load_asr_resources(resource_manifest_path, resource_manifest_sha256,
                                      runtime_manifest_sha256)
        # The observer launches this interpreter with `-I -B -X utf8` and imports
        # PyAV, so it must be the actual protected CPython of this Engine, not a
        # frozen sidecar or an unrelated executable. Full interpreter hash
        # registration stays a Backend installation item (Handoff A-7); the
        # measured library version comes from the real worker observation.
        interpreter = Path(sys.executable)
        if (not interpreter.is_absolute() or not interpreter.is_file()
                or sys.implementation.name != 'cpython'):
            raise EngineError("local_media_interpreter_unavailable",
                "Local media evidence needs the actual protected CPython interpreter.", 503)
        media = BundleMediaEvidence(interpreter, storage_root)

    def produce(lease, *, video_asset_id=_REQUIRED, narration_asset_id=_REQUIRED, mixed_asset_id=_REQUIRED,
                cover_asset_id=_REQUIRED, asr_route_id=_REQUIRED, reference_evidence=None, plan_admission=None,
                production_rights_fact=None, cancel=None, deadline_monotonic=None,
                selection=_REQUIRED, media_roles=_REQUIRED):
        if local_material_context is not None:
            if (any(value is not _REQUIRED for value in (video_asset_id, narration_asset_id,
                    mixed_asset_id, cover_asset_id))
                    or reference_evidence is not None
                    or selection is _REQUIRED or media_roles is _REQUIRED
                    or selection is None or media_roles is None):
                raise EngineError("local_final_producer_arguments_invalid",
                    "The local producer consumes its selection and applicable masters only.", 422)
            from video_creator.workflows.local_bundle_producer import (
                produce_local_bundle,
            )

            return produce_local_bundle(engine, bundle, executor, media, lease,
                        production_services=production_services,
                        local_material_context=local_material_context, selection=selection,
                        media_roles=media_roles, asr_route_id=asr_route_id,
                        plan_admission=plan_admission, production_rights_fact=production_rights_fact,
                        final_evidence_ports=final_evidence_ports,
                        asr_resources=local_asr_resources, runtime_root=runtime_root,
                        cancel=cancel, deadline_monotonic=deadline_monotonic)
        if selection is not _REQUIRED or media_roles is not _REQUIRED:
            raise EngineError("local_material_context_required",
                "Applicable local masters need the original held local context at this factory.", 403)
        _require_v2v3_arguments((('video_asset_id', video_asset_id),
                    ('narration_asset_id', narration_asset_id), ('mixed_asset_id', mixed_asset_id),
                    ('cover_asset_id', cover_asset_id), ('asr_route_id', asr_route_id)))
        return produce_bundle(engine, bundle, executor, resources, media, lease,
                    video_asset_id=video_asset_id, narration_asset_id=narration_asset_id,
                    mixed_asset_id=mixed_asset_id, cover_asset_id=cover_asset_id,
                    asr_route_id=asr_route_id, runtime_root=runtime_root, reference_evidence=reference_evidence,
                    plan_admission=plan_admission, production_rights_fact=production_rights_fact,
                    final_evidence_ports=final_evidence_ports,
                    production_services=production_services,
                    cancel=cancel, deadline_monotonic=deadline_monotonic)

    def continue_current_final_evidence(*, ordinary_lease, continuation, policy_execution_ports, control,
                                       diagnostic_source=None):
        from video_creator.workflows.bundle_recovery import continue_bundle

        return continue_bundle(engine=engine, bundle=bundle, executor=executor, media=media,
                    final_evidence_ports=final_evidence_ports, ordinary_lease=ordinary_lease,
                    continuation=continuation, policy_execution_ports=policy_execution_ports, control=control,
                    production_services=production_services, resources=resources, runtime_root=runtime_root,
                    diagnostic_source=diagnostic_source)

    produce.continue_current_final_evidence = continue_current_final_evidence

    return produce
