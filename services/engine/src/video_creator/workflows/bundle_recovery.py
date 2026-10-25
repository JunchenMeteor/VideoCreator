"""Same-Run recovery from original held facts; never reruns missing inference."""
from __future__ import annotations

import hashlib

from video_creator.domain import contracts as c
from video_creator.domain.current_final_evidence import (
    AssemblyContextRef,
    CurrentFinalAssemblyContextV2,
    CurrentFinalEvidenceAssessment,
    CurrentFinalEvidenceReadSet,
)
from video_creator.domain.errors import EngineError
from video_creator.domain.registered_production import ProductionBinding
from video_creator.workflows.current_final_evidence import (
    reauthorize_continuation,
    require_final_port,
    require_final_value,
    verify_final_evidence,
)

BASE_DOCUMENTS = {"insight", "brief", "plan", "script", "transcript", "srt", "vtt", "summary", "sources",
                  "shots", "segments", "rag", "quality", "audit", "authorization"}
OUTPUTS = {"video": ("video",), "narration_audio": ("narration",), "mixed_audio": ("mixed",),
           "approved_script": ("script",), "actual_transcript": ("transcript",),
           "subtitles": ("srt", "vtt"), "semantic_manifest": ("segments",), "rag_chunks": ("rag",)}


def persist_initial_assembly(port, *, engine, bundle, context, request, lease, preparation, intent,
                             plan_admission, artifact_ids, documents, media_artifacts, mapping,
                             actual, operation, operation_input, resources, evidence, right_fact, rights,
                             revision_refs, approval_refs, feedback_refs, source_refs, quality_ref,
                             timeline, policy_authorization):
    """Save actual first author facts before a no-candidate wait can be returned."""
    from video_creator.application.bundle_facts import FACT_FORMAT
    from video_creator.application.engine import canonical, digest
    from video_creator.workflows.attempt_control import current_attempt

    current_attempt().check()
    binding = ProductionBinding(instance_id=engine.instance_id, production_id=context.production_id,
                run_id=lease.run_id, request_revision_id=context.request_revision_id,
                request_sha256=digest(canonical(request)), registration_sha256=plan_admission.registration_sha256,
                input_assets=tuple((identity, bundle.asset(lease, identity).sha256) for identity in request.inputs.asset_ids))
    asr_method = actual["runtime"]["execution_identity"]["method_id"] if evidence is not None else "actual-asr"
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
    methods = (
        c.MethodEvidence(method_id=asr_method, kind="observed", tool_name="faster-whisper",
            tool_version=actual["runtime"]["versions"]["faster-whisper"], model_repository="Systran/faster-whisper-small",
            model_revision=resources.model_revision, resource_manifest_sha256=resources.manifest_sha256,
            operation_ids=(operation["id"],), input_artifact_ids=(artifact_ids["mixed"],), config_sha256=operation_input,
            limitations=("Word estimates; per-work precision is recorded separately in Alignment.",) if evidence is not None
                         else ("Word estimates; precision not independently measured.",)),
        c.MethodEvidence(method_id="actual-decoder", kind="observed", tool_name="PyAV+FFmpeg",
            tool_version=actual["runtime"]["versions"]["av"], resource_manifest_sha256=resources.manifest_sha256,
            config_sha256=digest("bundle-source-clock-and-frame-v1"),
            limitations=("Observed media/schema consistency; not perceptual quality or rights verification.",)),
        c.MethodEvidence(method_id="bundle-rights-v1", kind="observed", tool_name="BundleService",
            tool_version=FACT_FORMAT, config_sha256=right_fact.context.context_sha256,
            evidence_artifact_ids=right_fact.evidence_artifact_ids, limitations=right_fact.limitations),
    ) + copied_methods + authorization_methods
    original_pair = {"corrected_from": None, "correction_reason": None} if evidence is None else {
                    "corrected_from": evidence.correction_origin, "correction_reason": evidence.correction_reason}
    value = CurrentFinalAssemblyContextV2(format="current-final-assembly-context-v2", **original_pair,
                binding=binding,
                preparation_id=preparation.preparation_id, preparation_intent_sha256=digest(canonical(intent)),
                authored_fence=lease.fencing_token, manifest_created_at_us=engine.clock(), timeline_duration_us=timeline,
                creative_revision_refs=revision_refs, approval_refs=approval_refs, feedback_revision_refs=feedback_refs,
                source_refs=source_refs, outputs=tuple(c.BundleOutput(role=role,
                    artifact_ids=tuple(artifact_ids[name] for name in names)) for role, names in OUTPUTS.items()),
                media_artifacts=media_artifacts, audio_mappings=(mapping,), methods=methods, rights=rights,
                quality_ref=quality_ref, document_artifact_ids={name: artifact_ids[name] for name in documents},
                asr_operation_id=operation["id"])
    ref = require_final_port(port).persist_assembly_context(lease, preparation.preparation_id, value)
    raw = (canonical(value) + "\n").encode("utf-8")
    if (type(ref) is not AssemblyContextRef or ref.preparation_id != preparation.preparation_id
            or ref.preparation_intent_sha256 != value.preparation_intent_sha256
            or (ref.content_sha256, ref.size) != (hashlib.sha256(raw).hexdigest(), len(raw))):
        raise EngineError("final_assembly_commit_invalid", "Only the actual committed original assembly reference can precede waiting.", 409)
    current_attempt().check()
    return value


def _read_original(port, lease, continuation):
    value = require_final_port(port).read_continuation_inputs(lease, continuation)
    return _validate_readset(value, lease, continuation.binding, continuation.snapshot.preparation_id,
                    continuation.snapshot.preparation_intent_sha256)


def _validate_readset(value, lease, binding, preparation_id, intent_sha256):
    from video_creator.application.engine import canonical, digest

    if (type(value) is not CurrentFinalEvidenceReadSet or value.binding != binding
            or type(value.execution_fence) is not int or value.execution_fence != lease.fencing_token
            or value.preparation.preparation_id != preparation_id
            or digest(canonical(value.intent)) != intent_sha256):
        raise EngineError("final_evidence_readset_invalid", "Original held read set must retain the same claim, intent and new fence.", 409)
    if len(value.allocations) != len(value.intent.material_slots):
        raise EngineError("final_evidence_readset_invalid", "The complete original ordered allocations are required.", 422)
    for slot, allocation in zip(value.intent.material_slots, value.allocations, strict=True):
        if ((allocation.preparation_id, allocation.artifact_id, allocation.relative_path, allocation.media_type, allocation.schema_kind)
                != (value.preparation.preparation_id, slot.artifact_id, slot.relative_path, slot.media_type, slot.schema_kind)):
            raise EngineError("final_evidence_readset_invalid", "Allocation identity/order cannot be reconstructed from the current request.", 422)
    by_id = {}
    for receipt, raw in value.materials:
        allocation = next((item for item in value.allocations if item.artifact_id == receipt.artifact_id), None)
        if (allocation is None or allocation.material_id != receipt.material_id or type(raw) is not bytes
                or receipt.preparation_id != value.preparation.preparation_id
                or (len(raw), hashlib.sha256(raw).hexdigest()) != (receipt.size, receipt.sha256)
                or receipt.artifact_id in by_id):
            raise EngineError("final_evidence_readset_invalid", "Original Ready receipt and complete bytes must agree.", 422)
        by_id[receipt.artifact_id] = (receipt, raw)
    if {item.artifact_id: item for item in value.preparation.materials} != {key: item[0] for key, item in by_id.items()}:
        raise EngineError("final_evidence_readset_invalid", "No original Ready material may be dropped.", 422)
    if any(by_id.get(receipt.artifact_id) != (receipt, raw) for receipt, raw in value.strict_materials):
        raise EngineError("final_evidence_readset_invalid", "Strict evidence is only the original complete-byte projection.", 422)
    if value.candidate is not None:
        raw, expected = value.candidate
        if type(raw) is not bytes or hashlib.sha256(raw).hexdigest() != expected:
            raise EngineError("final_candidate_invalid", "Full candidate file SHA must remain distinct from record hashes.", 422)
    return value


def _candidate(readset):
    from video_creator.application.bundles import strict_json

    if readset.candidate is None:
        return None
    return c.parse_bundle_manifest(strict_json(readset.candidate[0]))


def _actual(readset):
    from video_creator.providers.local_asr import validate_original_asr_result

    source = readset.asr
    if source is None:
        raise EngineError("asr_recovery_validation_unavailable", "An actual pre-dispatch original validation context is required; missing inference is not rerun.", 503)
    ref = source.context_ref
    if (source.status != "succeeded" or source.settled is not True
            or source.observation.status != "succeeded" or source.run_id != readset.binding.run_id
            or source.production_id != readset.binding.production_id
            or (ref.operation_id, ref.run_id, ref.input_sha256, ref.route_sha256)
                != (source.operation_id, source.run_id, source.input_sha256, source.route_sha256)
            or (len(source.original_context_bytes), hashlib.sha256(source.original_context_bytes).hexdigest())
                != (ref.size, ref.context_sha256)):
        raise EngineError("asr_recovery_binding_invalid", "Only the same settled original Operation and authored validation bytes can generate a report.", 422)
    validate_original_asr_result(source.observation.result_json, source.original_context_bytes)
    return source.observation.result_json


def _reference(readset, allocations, document_ids):
    from video_creator.application.bundles import strict_json
    from video_creator.domain.bundle import MaterialSlot
    from video_creator.workflows.bundle_v03 import IndependentReferenceMaterials

    original = {receipt.artifact_id: (receipt, raw) for receipt, raw in readset.strict_materials}
    value = original.get(document_ids.get("reference"))
    if value is None:
        return None
    receipt, raw = value
    if receipt.schema_kind != "precision_reference_v03":
        raise EngineError("precision_reference_source_invalid", "Original reference grammar must remain exact.", 422)
    reference = c.PerWorkReferenceDocument.model_validate(strict_json(raw))
    sources = []
    expected = {ref.artifact_id: ref for ref in (*reference.independent_listener_refs, reference.arbitration_ref)}
    for allocation in readset.allocations:
        ref = expected.get(allocation.artifact_id)
        if ref is None:
            continue
        value = original.get(ref.artifact_id)
        if value is None or allocation is None or value[0].sha256 != ref.sha256:
            raise EngineError("precision_reference_source_missing", "Complete independent listener and arbitration sources are required.", 409)
        slot = MaterialSlot(artifact_id=allocation.artifact_id, relative_path=allocation.relative_path,
                            media_type=allocation.media_type, schema_kind=allocation.schema_kind)
        sources.append((slot, value[1]))
    if {slot.artifact_id for slot, _ in sources} != set(expected):
        raise EngineError("precision_reference_source_missing", "Every original independent source must retain its allocation order.", 409)
    assembly = readset.assembly
    origin, reason = (assembly.corrected_from, assembly.correction_reason) if type(assembly) is CurrentFinalAssemblyContextV2 else (None, None)
    if any(name.startswith("correction-copy-") for name in document_ids):
        measurement = original.get(document_ids.get("measurement"))
        if measurement is None and origin is None:
            raise EngineError("correction_recovery_context_required", "Pre-candidate correction origin/reason is not recorded until the actual measurement exists; copied ancestors cannot supply the missing author intent.", 503)
        if measurement is not None:
            report = c.PrecisionEvaluationReportV03.model_validate(strict_json(measurement[1]))
            if origin is not None and (origin, reason) != (report.corrected_from, report.correction_reason):
                raise EngineError("correction_recovery_context_conflict", "Recorded author intent and original Ready current measurement cannot disagree.", 422)
            origin, reason = report.corrected_from, report.correction_reason
        if origin is None or not reason:
            raise EngineError("correction_recovery_context_required", "Only the original current measurement records its authored correction locator and reason.", 503)
    elif origin is not None:
        raise EngineError("correction_recovery_context_conflict", "Authored correction cannot omit its complete original copied closure.", 422)
    return IndependentReferenceMaterials(reference, raw, tuple(sources), origin, reason)


def _documents(readset, *, final_speech_required=True):
    from video_creator.application.bundles import validate_text

    assembly = readset.assembly
    allocated = {value.artifact_id: value for value in readset.allocations}
    ready = {receipt.artifact_id: (receipt, raw) for receipt, raw in readset.materials}
    if set(assembly.document_artifact_ids.values()) != set(allocated):
        raise EngineError("final_assembly_allocation_missing", "Every original allocated document and copied dependency must be retained.", 422)
    documents, receipts, parsed = {}, {}, {}
    for name, artifact_id in assembly.document_artifact_ids.items():
        allocation = allocated.get(artifact_id)
        if allocation is None:
            raise EngineError("final_assembly_allocation_missing", "Original assembly document IDs must use the full original allocation set.", 422)
        item = ready.get(artifact_id)
        documents[name] = (allocation.relative_path, allocation.schema_kind, None if item is None else item[1])
        if item is not None:
            receipt, raw = item
            if (receipt.schema_kind, receipt.media_type) != (allocation.schema_kind, allocation.media_type):
                raise EngineError("final_ready_material_invalid", "Original Ready grammar/path must retain its allocation.", 422)
            parsed[name] = validate_text(raw, receipt.schema_kind, receipt.media_type)
            receipts[name] = receipt
    required = BASE_DOCUMENTS - {"quality", "audit", "authorization"}
    if not final_speech_required:
        required -= {"transcript", "srt", "vtt", "segments", "rag"}
    if not required <= set(receipts):
        raise EngineError("final_assembly_inputs_missing", "All original creative, actual transcript, subtitle and semantic inputs must be Ready.", 409)
    if "authorization" in documents and "authorization" not in receipts:
        raise EngineError("final_assembly_inputs_missing", "Original actual authorization bytes must precede assembly recovery.", 409)
    return allocated, documents, receipts, parsed


def _observed_checks(readset, *, bundle, media, lease, parsed, document, actual, artifact_ids):
    """Observe the original audio/frame facts; permission does not prove quality."""
    from video_creator.application.bundles import serialize_subtitles

    mapping = readset.assembly.audio_mappings[0]
    roles = {value.roles[0]: value for value in readset.assembly.media_artifacts}
    video = roles["video"]
    for artifact in readset.assembly.media_artifacts:
        asset = bundle.asset(lease, artifact.asset_id)
        if (asset.sha256, asset.size, asset.media_type) != (artifact.sha256, artifact.size, artifact.media_type):
            raise EngineError("final_media_changed", "Original masters are immutable and remain independently controlled.", 422)
        if artifact.spec.audio_clock is not None:
            clock, duration = media.clock(asset, bundle.content_path(lease, artifact.asset_id))
            if clock != artifact.spec.audio_clock or duration != artifact.spec.duration_us:
                raise EngineError("audio_clock_invalid", "Each original master clock must retain its actual decoded samples and duration.", 422)
    tracks = [document.transcript.input_track, mapping.target_track]
    tracks.extend(piece.source_track for piece in mapping.pieces)
    for track in tracks:
        if not media.audio_clock_authority(track, bundle.content_path(lease, track.asset_id)):
            raise EngineError("audio_clock_invalid", "The original mapping clock must still decode to its exact samples.", 422)
    if (actual["input_audio_sha256"], actual["duration_us"], actual["text"], actual["language"]) != (
            document.transcript.input_audio_sha256, document.transcript.duration_us,
            document.transcript.text, document.transcript.language):
        raise EngineError("actual_transcript_binding_invalid", "Original validated inference must retain the actual transcript text and clock.", 422)
    expected = tuple((segment["text"], segment["start_us"], segment["end_us"],
                      tuple((word["text"], word["start_us"], word["end_us"]) for word in segment["words"]))
                     for segment in actual["segments"])
    observed = tuple((value.text, value.intrinsic_range.start_us, value.intrinsic_range.end_us,
                      tuple((word.text, word.intrinsic_range.start_us, word.intrinsic_range.end_us) for word in value.words))
                     for value in document.transcript.utterances)
    if observed != expected:
        raise EngineError("actual_transcript_binding_invalid", "No authored text or estimated ranges may replace original validated ASR units.", 422)
    srt, vtt, quantization = serialize_subtitles(document.subtitles)
    if (parsed["srt"], parsed["vtt"]) != (srt.decode("utf-8"), vtt.decode("utf-8")):
        raise EngineError("subtitle_binding_invalid", "Ready subtitle bytes must retain the actual original cue timeline.", 422)
    if quantization != document.subtitles.quantization_errors:
        raise EngineError("subtitle_binding_invalid", "Original subtitle rounding must remain the actual declared transformation.", 422)
    units = {value.utterance_id: value for value in document.transcript.utterances}
    for segment in parsed["segments"]:
        text = "".join(units[identity].text for identity in segment.transcript_unit_refs)
        if (segment.speech_text != text or segment.video_asset_id != video.asset_id
                or segment.alignment_revision_id != document.alignment.alignment_revision_id):
            raise EngineError("semantic_binding_invalid", "Original retrieval speech must retain its actual unit and media bindings.", 422)
        for frame in segment.frame_evidence_refs:
            if not media.frame_validator(frame, bundle.content_path(lease, video.asset_id)):
                raise EngineError("semantic_frame_invalid", "Original observed frame hashes must decode at the same exact PTS.", 422)
    method = document.transcript.method_ref
    return tuple(c.QualityCheck(check_id=name, status="not_measured" if name in {"alignment", "rights"} else "verified",
                method_ref=method if name in {"actual_transcript", "alignment"} else "actual-decoder",
                evidence_artifact_ids=(artifact_ids["transcript"],),
                findings=("Assembly evidence only; not independent user acceptance.",))
                for name in ("media_integrity", "audio_timeline", "actual_transcript", "alignment", "subtitles", "semantic_sources", "rights"))


def _restore_evidence(readset, resolution, *, bundle, lease, request, actual, document, artifact_ids, documents, receipts):
    from video_creator.workflows.bundle_v03 import (
        PreparedV03Evidence,
        bind_v03_evidence,
    )

    allocations = {value.artifact_id: value for value in readset.allocations}
    reference_input = _reference(readset, allocations, artifact_ids)
    names = set(documents) - BASE_DOCUMENTS
    extras = {name: documents[name] for name in documents if name in names}
    state = PreparedV03Evidence(readset.preparation, None, document.alignment, extras, "provenance_reference")
    state.intent = readset.intent
    state.receipts.update({name: receipt for name, receipt in receipts.items() if name in names})
    state.dependencies.update({name: (artifact_ids["mixed"],) for name in ("transcript", "srt", "vtt", "segments", "rag")})
    state.dependencies.update(policy=(artifact_ids["qualification"],), qualification=(artifact_ids["benchmark"],),
                work_validation=(artifact_ids["policy"], artifact_ids["transcript"]), quality=(artifact_ids["work_validation"],))
    if reference_input is not None:
        state.reference = reference_input.reference
        state.reference_ref = c.EvidenceReportRef(report_id=state.reference.report_id, schema_version=c.V03_SCHEMA_VERSION,
                    evaluation_scope="per_work_reference_measurement", content_sha256=receipts["reference"].sha256)
        precision = document.alignment.precision
        state.measurement_locator = precision.measurement_report_locator
        allocation = allocations.get(artifact_ids["measurement"])
        if (precision.status != "measured" or precision.reference_ref != state.reference_ref
                or state.measurement_locator is None or allocation is None
                or (state.measurement_locator.artifact_id, state.measurement_locator.material_id) != (allocation.artifact_id, allocation.material_id)):
            raise EngineError("precision_recovery_binding_invalid", "Original measured Alignment must retain its original actual source and report allocation.", 422)
        state.correction_origin, state.correction_reason = reference_input.corrected_from, reference_input.correction_reason
        source_ids = tuple(slot.artifact_id for slot, _ in reference_input.source_documents)
        state.dependencies.update(reference=source_ids + (artifact_ids["mixed"],), measurement=(artifact_ids["reference"], artifact_ids["transcript"]),
                    transcript=(artifact_ids["mixed"], artifact_ids["reference"]),
                    work_validation=(artifact_ids["policy"], artifact_ids["transcript"], artifact_ids["measurement"]))
        if state.correction_origin is not None:
            # Restore the exact original source closure through its genuine fact
            # port, without allocating, renaming, or restaging any Ready copy.
            from video_creator.application.engine import canonical, digest
            from video_creator.workflows.bundle_correction import correction_copy_plan

            fact = bundle.correction_origin_evidence(lease, state.correction_origin, purpose="derivative")
            unchanged = {name: value for name, value in artifact_ids.items() if not name.startswith("correction-copy-")}
            copied = correction_copy_plan(fact, state.correction_origin, unchanged, instance_id=readset.binding.instance_id,
                        context=bundle.context(lease), lease=lease, request_sha256=digest(canonical(request)))
            for name in copied.ordered_names:
                if (unchanged[name] != artifact_ids.get(name) or copied.documents[name] != documents.get(name)
                        or name not in receipts):
                    raise EngineError("correction_recovery_binding_invalid", "Every original copied ancestor/license/edge byte must match the original Ready set.", 422)
            state.correction_copies = copied
            state.dependencies.update(copied.dependencies)
            state.dependencies["measurement"] += (state.correction_origin.artifact_id,)
    bind_v03_evidence(state, bundle, lease, resolution.resolved, request, actual)
    return state


def _generate_candidate(readset, resolution, *, engine, bundle, media, context, request, lease, admission, rights, control,
                        final_evidence_ports=None, alignment_execution=None, continuation=None):
    from video_creator.application.engine import canonical, digest
    from video_creator.workflows.bundle_correction import rights_check_from_fact
    from video_creator.workflows.bundle_producer import (
        _json,
        _material_artifacts,
        _record,
    )
    from video_creator.workflows.bundle_v03 import finish_v03_evidence

    assembly = readset.assembly
    allocations, documents, receipts, parsed = _documents(readset)
    if rights.rights != assembly.rights:
        raise EngineError("final_assembly_rights_conflict", "Fresh plan declarations cannot replace the original authored rights snapshots.", 403)
    artifact_ids = dict(assembly.document_artifact_ids)
    role_names = {"video": "video", "narration_audio": "narration", "mixed_audio": "mixed", "cover": "cover"}
    for value in assembly.media_artifacts:
        artifact_ids[role_names[value.roles[0]]] = value.artifact_id
    document, actual = parsed["transcript"], _actual(readset)
    validation_actual, validation_operation_id, methods = actual, readset.asr.operation_id, assembly.methods
    if alignment_execution is not None:
        from video_creator.workflows.registered_alignment import runtime_actual

        observation, validation_operation_id = alignment_execution
        validation_actual = runtime_actual(actual, observation)
    elif request.request_format_version == c.V03_SCHEMA_VERSION:
        from video_creator.workflows.alignment_recovery import (
            initial_runtime,
            selected_runtime,
        )

        if continuation is not None:
            validation_actual, validation_operation_id, methods = selected_runtime(
                final_evidence_ports, lease, continuation, readset, actual, document)
        else:
            # The synchronous authorized repair branch retains its own original
            # execution/initial-child source; the retry-only getter cannot dispatch it.
            validation_actual, validation_operation_id, methods = initial_runtime(final_evidence_ports, lease, readset, actual)
    if document.transcript.approved_script_revision_ref not in assembly.creative_revision_refs:
        raise EngineError("creative_recovery_binding_invalid", "The actual transcript keeps its original approved creative source.", 422)
    state = None
    if request.request_format_version == c.V03_SCHEMA_VERSION:
        state = _restore_evidence(readset, resolution, bundle=bundle, lease=lease, request=request,
                    actual=validation_actual, document=document, artifact_ids=artifact_ids, documents=documents, receipts=receipts)
        documents.update(state.documents)
    asr_method, right = document.transcript.method_ref, assembly.rights[0]
    ready_artifacts = assembly.media_artifacts + _material_artifacts(receipts, documents, artifact_ids, state, asr_method, right, assembly.rights)
    uses = ("derivative", "export", "standalone_audio", "rag_index")
    if state is not None and state.correction_copies is not None:
        uses += ("redistribution",)
    fact = bundle.verify_rights_evidence(lease, readset.preparation.preparation_id, rights=assembly.rights,
                approval_refs=assembly.approval_refs, creative_revision_refs=assembly.creative_revision_refs,
                artifacts=ready_artifacts, required_uses=uses)
    rights_check = rights_check_from_fact(fact, instance_id=engine.instance_id, context=context, lease=lease,
                request_sha256=digest(canonical(request)), preparation_id=readset.preparation.preparation_id,
                rights=assembly.rights, approval_refs=assembly.approval_refs, revision_refs=assembly.creative_revision_refs,
                artifacts=ready_artifacts, required_uses=uses)
    checks = _observed_checks(readset, bundle=bundle, media=media, lease=lease, parsed=parsed,
                             document=document, actual=actual, artifact_ids=artifact_ids)
    checks = tuple(rights_check if value.check_id == "rights" else value for value in checks)
    if state is not None:
        report_id = (parsed["work_validation"].report_id if "work_validation" in parsed else
                     parsed["quality"].work_validation_report_ref.report_id if "quality" in parsed else
                     allocations[artifact_ids["work_validation"]].material_id)
        additional, quality = finish_v03_evidence(state, context, request, document, assembly.audio_mappings[0], validation_actual,
                    validation_operation_id, lease, assembly.quality_ref, artifact_ids, checks, work_report_id=report_id,
                    source_operation_ids=(readset.asr.operation_id,))
        documents.update(additional)
    else:
        quality = _record(c.BundleQualityEvidence(quality_revision_ref=assembly.quality_ref, checks=checks, content_sha256="0" * 64))
    documents["quality"] = (*documents["quality"][:2], _json(quality))
    import json

    audit = (json.dumps({
                "summary": "Actual registered-media assembly and scoped pre-quality rights observation; final rights revalidation is still required.",
                "operation_ids": [readset.asr.operation_id], "cost_status": "confirmed_no_charge",
                "method_refs": [asr_method, "actual-decoder", "bundle-rights-v1"],
                "findings": list(fact.limitations), "source_gaps": list(rights_check.findings) if rights_check.status != "verified" else []}, ensure_ascii=False) + "\n").encode("utf-8")
    documents["audit"] = (*documents["audit"][:2], documents["audit"][2] if "audit" in receipts else audit)
    ordered = sorted(documents, key=lambda name: name in {"quality", "audit"})
    for name in ordered:
        raw = documents[name][2]
        control.check()
        if raw is None:
            raise EngineError("final_evidence_material_missing", "An allocated slot is never Ready evidence.", 409)
        if name in receipts:
            original = next(data for receipt, data in readset.materials if receipt.artifact_id == artifact_ids[name])
            if raw != original:
                raise EngineError("final_ready_material_conflict", "Ready report or source bytes cannot be rewritten under the original material ID; actual affected child lineage is required.", 409)
        else:
            receipts[name] = bundle.stage_material(lease, readset.preparation.preparation_id, artifact_ids[name], raw)
            allocated = allocations[artifact_ids[name]]
            if (receipts[name].material_id, receipts[name].sha256, receipts[name].size) != (
                    allocated.material_id, hashlib.sha256(raw).hexdigest(), len(raw)):
                raise EngineError("final_evidence_stage_invalid", "A new report must use the original allocation and actual staged bytes.", 422)
    versions = {} if state is None else {"schema_version": c.V03_SCHEMA_VERSION,
                "evidence_policy_revision_ref": state.resolved.policy_ref, "qualification_ref": state.resolved.qualification,
                "benchmark_binding": state.benchmark_binding, "benchmark_document_artifact_id": artifact_ids["benchmark"],
                "policy_document_artifact_id": artifact_ids["policy"], "qualification_document_artifact_id": artifact_ids["qualification"],
                "work_validation_document_artifact_id": artifact_ids["work_validation"]}
    manifest_type = c.BundleManifest if state is None else c.BundleManifestV03
    return manifest_type(**versions, instance_id=assembly.binding.instance_id,
                bundle_id=readset.intent.bundle_id, bundle_revision_id=readset.intent.bundle_revision_id,
                project_id=context.project_id, production_id=assembly.binding.production_id, run_id=assembly.binding.run_id,
                request_revision_id=assembly.binding.request_revision_id, request_sha256=assembly.binding.request_sha256,
                workflow_version="registered-media-bundle-v1", created_at_us=assembly.manifest_created_at_us,
                timeline_duration_us=assembly.timeline_duration_us, creative_revision_refs=assembly.creative_revision_refs,
                approval_refs=assembly.approval_refs, feedback_revision_refs=assembly.feedback_revision_refs,
                source_refs=assembly.source_refs, requested_outputs=request.outputs, outputs=assembly.outputs,
                artifacts=assembly.media_artifacts + _material_artifacts(receipts, documents, artifact_ids, state, asr_method, right, assembly.rights),
                audio_mappings=assembly.audio_mappings, methods=methods, rights=assembly.rights, quality_ref=assembly.quality_ref)


def continue_bundle(*, engine, bundle, executor, media, final_evidence_ports, ordinary_lease,
                    continuation, policy_execution_ports, control, production_services=None,
                    resources=None, runtime_root=None, diagnostic_source=None):
    """Read the same claim, re-admit its targets and finish only actual evidence."""
    from video_creator.workflows.bundle_producer import (
        BundleProductionResult,
        _final_wait,
    )

    with control.activate():
        control.check()
        from video_creator.workflows.affected_production import require_services

        require_services(final_evidence_ports, ordinary_lease, production_services, policy_execution_ports)
        if diagnostic_source is not None:
            from video_creator.workflows.component_diagnosis import resume_diagnosis

            assessment = resume_diagnosis(final_evidence_ports, ordinary_lease, continuation,
                        diagnostic_source, production_services)
            if assessment is not None:
                return _final_wait(assessment)
        readset = _read_original(final_evidence_ports, ordinary_lease, continuation)
        candidate = _candidate(readset)
        origin = candidate if candidate is not None else readset.assembly
        if origin is None:
            raise EngineError("final_assembly_unavailable", "Original committed assembly is missing; no IDs or mapping are rebuilt from current host.", 503)
        context, request, admission, rights = reauthorize_continuation(engine=engine, bundle=bundle,
                    lease=ordinary_lease, continuation=continuation, policy_execution_ports=policy_execution_ports,
                    control=control, revision_refs=origin.creative_revision_refs)
        _actual(readset)
        if continuation.resume_mode == "repair":
            return _repair(readset, continuation, control, engine=engine, bundle=bundle, executor=executor,
                    media=media, port=final_evidence_ports, lease=ordinary_lease, services=production_services,
                    resources=resources, runtime_root=runtime_root, context=context, request=request,
                    admission=admission, rights=rights)
        if (candidate is None and request.request_format_version == c.V03_SCHEMA_VERSION
                and not {readset.assembly.document_artifact_ids[name] for name in ("transcript", "srt", "vtt", "segments", "rag")}
                        <= {r.artifact_id for r, _ in readset.materials}):
            from video_creator.workflows.alignment_recovery import restore_initial

            restore_initial(final_evidence_ports, production_services, ordinary_lease, readset,
                bundle=bundle, media=media, context=context)
            readset = _read_original(final_evidence_ports, ordinary_lease, continuation)
        resolution = require_final_port(final_evidence_ports).resolve_inputs(ordinary_lease, readset.preparation.preparation_id)
        resolution = require_final_value(resolution, engine=engine, bundle=bundle, context=context, request=request,
                    lease=ordinary_lease, preparation=readset.preparation,
                    intent_sha256=continuation.snapshot.preparation_intent_sha256,
                    registration_sha256=admission.registration_sha256)
        if type(resolution) is CurrentFinalEvidenceAssessment:
            if resolution.snapshot is None:
                raise EngineError("final_evidence_result_invalid", "Input resolution does not publish an unfinished candidate.", 409)
            return _final_wait(resolution, candidate)
        if candidate is None:
            if (request.request_format_version == c.V03_SCHEMA_VERSION
                    and request.delivery_requirements.alignment_evidence_policy == "strict_reference_v1"
                    and readset.assembly.document_artifact_ids.get("reference") not in
                        {receipt.artifact_id for receipt, _ in readset.strict_materials}):
                waiting = require_final_port(final_evidence_ports).verify_current_final_evidence(
                    ordinary_lease, readset.preparation.preparation_id, None)
                waiting = require_final_value(waiting, engine=engine, bundle=bundle, context=context,
                    request=request, lease=ordinary_lease, preparation=readset.preparation,
                    intent_sha256=continuation.snapshot.preparation_intent_sha256,
                    registration_sha256=admission.registration_sha256)
                if type(waiting) is not CurrentFinalEvidenceAssessment or waiting.snapshot is None:
                    raise EngineError("final_evidence_result_invalid", "Missing independent sources require the real service's original wait assessment.", 409)
                return _final_wait(waiting)
            candidate = _generate_candidate(readset, resolution, engine=engine, bundle=bundle,
                        media=media, context=context, request=request, lease=ordinary_lease,
                        admission=admission, rights=rights, control=control, final_evidence_ports=final_evidence_ports,
                        continuation=continuation)
        assessment = verify_final_evidence(final_evidence_ports, candidate, engine=engine, bundle=bundle,
                    context=context, request=request, lease=ordinary_lease, preparation=readset.preparation,
                    intent_sha256=continuation.snapshot.preparation_intent_sha256,
                    registration_sha256=admission.registration_sha256)
        if assessment.snapshot is not None:
            return _final_wait(assessment, candidate)
        control.check()
        reference = bundle.publish(ordinary_lease, assessment.verified_material)
        prepared = bundle.recover_preparation(ordinary_lease, readset.preparation.preparation_id)
        return BundleProductionResult("published", prepared.preparation_id, candidate, prepared.materials, bundle_ref=reference)


def _repair(readset, continuation, control, *, engine, bundle, executor, media, port, lease, services,
            resources, runtime_root, context, request, admission, rights):
    """Actual held command, source outputs, selected child, report and publisher."""
    from video_creator.application.engine import canonical, digest
    from video_creator.workflows.affected_production import (
        authorize,
        proposal_for_failure,
        regenerate_masters,
    )
    from video_creator.workflows.bundle_affected import select_child
    from video_creator.workflows.bundle_producer import (
        BundleProductionResult,
        _final_wait,
        _produce_bundle,
    )

    control.check()
    proposal = proposal_for_failure(readset, continuation, bundle=bundle, lease=lease, port=port)
    alignment_execution = None
    if proposal.requested_action == "realignment":
        from video_creator.workflows.alignment_recovery import produce_realignment_child
        from video_creator.workflows.registered_alignment import run_alignment

        execution = authorize(port, lease, continuation, proposal, services)
        aligned, _file, observation, operation_id = run_alignment(port, services, lease, execution=execution)
        state = select_child(port, lease, continuation, proposal, services, execution, None)
        state = produce_realignment_child(port, services, lease, continuation, proposal, state,
            aligned, observation, operation_id, bundle=bundle, media=media, context=context)
        alignment_execution = (observation, operation_id)
        masters = None
    else:
        execution, masters = regenerate_masters(port, lease, continuation, proposal, services, readset)
        state = select_child(port, lease, continuation, proposal, services, execution, masters)
    child = _validate_readset(state.child, lease, continuation.binding,
                    state.child.preparation.preparation_id, digest(canonical(state.child.intent)))
    candidate = _candidate(child)
    if candidate is None and child.assembly is None:
        if resources is None or runtime_root is None:
            raise EngineError("affected_child_resources_missing", "The original registered producer must retain its own actual ASR resources and runtime; no manifest guessing.", 503)
        original_docs = state.parent.assembly.document_artifact_ids
        allocations = {item.artifact_id: item for item in state.parent.allocations}
        mixed = bundle.asset(lease, masters.effective_media_roles["mixed_audio"])
        reference = (_reference(state.parent, allocations, original_docs)
                     if state.parent.asr is not None and mixed.sha256 == _actual(state.parent)["input_audio_sha256"] else None)
        return _produce_bundle(engine, bundle, executor, resources, media, lease,
                    video_asset_id=masters.effective_media_roles["video"],
                    narration_asset_id=masters.effective_media_roles["narration_audio"],
                    mixed_asset_id=masters.effective_media_roles["mixed_audio"], cover_asset_id=masters.effective_media_roles["cover"],
                    asr_route_id=None, runtime_root=runtime_root, reference_evidence=reference,
                    plan_admission=admission, production_rights_fact=rights,
                    final_evidence_ports=port, production_services=services, affected_state=state,
                    repair_continuation=continuation, repair_proposal=proposal)
    if child.assembly is None and candidate is None:
        raise EngineError("final_assembly_unavailable", "Only the actual selected child author's context may finish its report.", 503)
    resolution = require_final_port(port).resolve_inputs(lease, child.preparation.preparation_id)
    resolution = require_final_value(resolution, engine=engine, bundle=bundle, context=context, request=request,
                    lease=lease, preparation=child.preparation, intent_sha256=digest(canonical(child.intent)),
                    registration_sha256=admission.registration_sha256)
    if type(resolution) is CurrentFinalEvidenceAssessment:
        return _final_wait(resolution, candidate)
    if candidate is None:
        if (request.request_format_version == c.V03_SCHEMA_VERSION
                and request.delivery_requirements.alignment_evidence_policy == "strict_reference_v1"
                and child.assembly.document_artifact_ids.get("reference") not in {receipt.artifact_id for receipt, _ in child.strict_materials}):
            waiting = require_final_port(port).verify_current_final_evidence(lease, child.preparation.preparation_id, None)
            waiting = require_final_value(waiting, engine=engine, bundle=bundle, context=context, request=request, lease=lease,
                        preparation=child.preparation, intent_sha256=digest(canonical(child.intent)), registration_sha256=admission.registration_sha256)
            if type(waiting) is not CurrentFinalEvidenceAssessment or waiting.snapshot is None:
                raise EngineError("final_evidence_result_invalid", "Missing child reference must be the actual held service wait.", 409)
            return _final_wait(waiting)
        candidate = _generate_candidate(child, resolution, engine=engine, bundle=bundle, media=media, context=context,
                    request=request, lease=lease, admission=admission, rights=rights, control=control,
                    final_evidence_ports=port, alignment_execution=alignment_execution)
    assessment = verify_final_evidence(port, candidate, engine=engine, bundle=bundle, context=context, request=request,
                    lease=lease, preparation=child.preparation, intent_sha256=digest(canonical(child.intent)),
                    registration_sha256=admission.registration_sha256)
    if assessment.snapshot is not None:
        return _final_wait(assessment, candidate)
    control.check()
    reference = bundle.publish(lease, assessment.verified_material)
    prepared = bundle.recover_preparation(lease, child.preparation.preparation_id)
    return BundleProductionResult("published", prepared.preparation_id, candidate, prepared.materials, bundle_ref=reference)
