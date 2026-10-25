"""Original pre-Ready recovery and actual realignment child material production."""
from __future__ import annotations

import hashlib

from video_creator.domain import contracts as c
from video_creator.domain.errors import EngineError
from video_creator.workflows.current_final_evidence import require_final_port


def _slot_stage(bundle, lease, readset, documents, receipts, name):
    identity = readset.assembly.document_artifact_ids[name]
    raw = documents[name][2]
    if name in receipts:
        if bundle.read_material(lease, readset.preparation.preparation_id, receipts[name].material_id) != raw:
            raise EngineError("alignment_ready_material_conflict", "Original Ready bytes cannot be rewritten after a crash.", 409)
        return receipts[name]
    receipt = bundle.stage_material(lease, readset.preparation.preparation_id, identity, raw)
    allocation = next(value for value in readset.allocations if value.artifact_id == identity)
    if (receipt.material_id, receipt.sha256, receipt.size) != (allocation.material_id, hashlib.sha256(raw).hexdigest(), len(raw)):
        raise EngineError("alignment_ready_material_invalid", "Only the original allocated material and complete bytes may become Ready.", 422)
    return receipt


def restore_initial(port, services, lease, readset, *, bundle, media, context):
    """Original assembly/draft/Operation; never new ASR/preparation/UUIDs."""
    from video_creator.workflows.alignment_documents import (
        original_draft,
        speech_documents,
    )
    from video_creator.workflows.bundle_recovery import (
        _actual,
        _documents,
        _reference,
        _validate_readset,
    )
    from video_creator.workflows.bundle_v03 import (
        PreparedV03Evidence,
        measure_alignment,
    )
    from video_creator.workflows.registered_alignment import run_alignment

    assembly = readset.assembly
    allocations, documents, receipts, _parsed = _documents(readset, final_speech_required=False)
    if {"transcript", "srt", "vtt", "segments", "rag"} <= set(receipts):
        return readset
    actual = _actual(readset)
    document = original_draft(assembly, actual)
    alignment, _manifest, _observation, _operation_id = run_alignment(port, services, lease,
        preparation_id=readset.preparation.preparation_id, transcript=document.transcript,
        prediction=document.alignment, mapping=assembly.audio_mappings[0])
    # Recover the original independent source bytes separately, after reading
    # the original settled CTC result. They never become an inference input.
    reference_input = _reference(readset, allocations, assembly.document_artifact_ids)
    if reference_input is not None:
        reference = reference_input.reference
        state = PreparedV03Evidence(readset.preparation, None, alignment, {}, "provenance_reference")
        state.reference = reference
        state.reference_ref = c.EvidenceReportRef(report_id=reference.report_id, schema_version=c.V03_SCHEMA_VERSION,
            evaluation_scope="per_work_reference_measurement", content_sha256=receipts["reference"].sha256)
        allocation = allocations[assembly.document_artifact_ids["measurement"]]
        state.measurement_locator = c.PerWorkReportLocator(report_id=allocation.material_id,
            artifact_id=allocation.artifact_id, material_id=allocation.material_id)
        alignment = measure_alignment(state, alignment)
    elif "reference" in assembly.document_artifact_ids:
        raise EngineError("precision_reference_source_missing", "The original independent reference bytes must be Ready before derived speech; recovery cannot invent or replace them.", 409)
    video = next(value for value in assembly.media_artifacts if value.roles == ("video",))
    asset = bundle.asset(lease, video.asset_id)
    if (asset.sha256, asset.size) != (video.sha256, video.size):
        raise EngineError("alignment_original_media_changed", "Original complete master is required for aligned retrieval frames.", 422)
    speech_documents(documents, document, alignment, assembly.audio_mappings[0], assembly=assembly,
        media=media, video=asset, video_path=bundle.content_path(lease, asset.asset_id),
        bundle_revision_id=readset.intent.bundle_revision_id, project_id=context.project_id)
    for name in ("transcript", "srt", "vtt", "segments", "rag"):
        receipts[name] = _slot_stage(bundle, lease, readset, documents, receipts, name)
    # Reading current facts requires the held continuation claim supplied by the
    # caller, not a constructed claim. The caller reloads it after this writer.
    _validate_readset(readset, lease, readset.binding, readset.preparation.preparation_id,
                     assembly.preparation_intent_sha256)
    return readset


def initial_runtime(port, lease, readset, actual):
    """Legacy unchanged methods or the actual settled initial CTC ninth getter."""
    from video_creator.domain.registered_alignment import InitialAlignmentRequest
    from video_creator.workflows.registered_alignment import runtime_actual

    held = require_final_port(port)
    try:
        raw = held.registered_initial_alignment_request(lease, readset.preparation.preparation_id)
    except EngineError as error:
        if error.code != "alignment_registration_missing":
            raise
        return actual, readset.asr.operation_id, readset.assembly.methods
    original = InitialAlignmentRequest.model_validate_json(raw)
    alignment, _manifest, observation = held.read_registered_initial_alignment_result(lease, readset.preparation.preparation_id)
    method = held.registered_initial_alignment_method(lease, readset.preparation.preparation_id)
    if (len(method.operation_ids) != 1 or method.method_id != alignment.method_ref
            or original.transcript.transcript.input_audio_sha256 != actual["input_audio_sha256"]
            or any(value.method_id == method.method_id for value in readset.assembly.methods)):
        raise EngineError("alignment_original_method_conflict", "Only the actual original CTC method can extend immutable pre-CTC source methods.", 422)
    return runtime_actual(actual, observation), method.operation_ids[0], (*readset.assembly.methods, method)


def selected_runtime(port, lease, continuation, readset, actual, document):
    """Consume the current held five-fact read; it supplies no execution right."""
    from video_creator.application.bundles import strict_json
    from video_creator.domain.registered_alignment import (
        AffectedAlignmentRequest,
        InitialAlignmentRequest,
        alignment_request_bytes,
    )
    from video_creator.domain.worker import GeneratedFileManifest
    from video_creator.providers.local_alignment import parse_request
    from video_creator.workflows.registered_alignment import runtime_actual

    result = require_final_port(port).read_selected_alignment_result(lease, continuation)
    if result is None:
        # Only the held service can return this authenticated legacy result.
        # A missing/unknown/conflicting CTC source raises instead of falling back.
        asr_method = actual["runtime"]["execution_identity"]["method_id"]
        matches = [value for value in readset.assembly.methods if value.method_id == asr_method]
        if (document.transcript.method_ref != asr_method or document.alignment.method_ref != asr_method
                or len(matches) != 1 or matches[0].operation_ids != (readset.asr.operation_id,)):
            raise EngineError("alignment_legacy_source_conflict", "Authenticated legacy facts cannot omit or replace an authored CTC method.", 422)
        return actual, readset.asr.operation_id, readset.assembly.methods
    if type(result) is not tuple or len(result) != 5:
        raise EngineError("alignment_selected_source_invalid", "The original held result must contain exactly five source facts.", 422)
    raw, alignment, manifest, observation, method = result
    if (type(raw) is not bytes or type(alignment) not in (c.AlignmentRevision, c.AlignmentRevisionV03)
            or type(manifest) is not GeneratedFileManifest or type(observation) is not c.OperationObservation
            or type(method) is not c.MethodEvidence or observation.status != "succeeded"
            or len(method.operation_ids) != 1 or type(observation.result_json) is not dict):
        raise EngineError("alignment_selected_source_invalid", "Canonical input, committed file, actual observation and original method are required.", 422)
    request = parse_request(strict_json(raw))
    original = observation.result_json
    files = tuple(GeneratedFileManifest.model_validate(value) for value in original.get("generated_files", ()))
    source = request.transcript.asr_source
    if (alignment_request_bytes(request) != raw or request.binding != readset.binding
            or original.get("request_sha256") != hashlib.sha256(raw).hexdigest()
            or files != (manifest,) or manifest.candidate.media_type != "application/json"
            or source.operation_id != readset.asr.operation_id or source.context_ref != readset.asr.context_ref
            or source.input_sha256 != readset.asr.input_sha256 or source.route_sha256 != readset.asr.route_sha256
            or source.staging_id != readset.asr.allocation.staging_id
            or source.context_file_sha256 != hashlib.sha256(readset.asr.original_context_bytes).hexdigest()
            or document.transcript != request.transcript.transcript
            or type(document.alignment) is not type(alignment)
            or document.alignment.model_dump(mode="json", exclude={"precision", "content_sha256"})
                != alignment.model_dump(mode="json", exclude={"precision", "content_sha256"})):
        raise EngineError("alignment_selected_source_conflict", "The selected actual ASR, canonical request and immutable CTC must remain one source.", 422)
    locator = ("preparation_id", request.preparation_id) if type(request) is InitialAlignmentRequest else (
        "repair_command_sha256", request.repair_command_sha256)
    execution = c.AlignmentExecutionIdentity.model_validate(original["execution_identity"])
    if (original.get(locator[0]) != locator[1] or method.method_id != alignment.method_ref
            or method.method_id != execution.method_id or method.kind != "model_inference"
            or (method.tool_name, method.tool_version, method.model_repository, method.model_revision,
                method.config_sha256, method.resource_manifest_sha256) != (
                    execution.tool, execution.tool_version, execution.model_id,
                    request.alignment_registration.resources.model_revision,
                    execution.configuration_sha256, execution.resource_manifest_sha256)):
        raise EngineError("alignment_selected_method_conflict", "Method evidence must retain the actual returned execution and original model/config source.", 422)
    methods = readset.assembly.methods
    matches = [value for value in methods if value.method_id == method.method_id]
    if matches:
        if len(matches) != 1 or matches[0] != method:
            raise EngineError("alignment_selected_method_conflict", "An authored method cannot be overwritten or duplicated while retrying.", 422)
    elif type(request) is AffectedAlignmentRequest:
        raise EngineError("alignment_selected_method_missing", "An affected child must already retain its actual authored CTC method.", 422)
    else:
        methods = (*methods, method)  # Sole actual initial method; original order is retained.
    return runtime_actual(actual, observation), method.operation_ids[0], methods


def produce_realignment_child(port, services, lease, continuation, proposal, state, aligned, observation, operation_id,
                             *, bundle, media, context):
    """Actual child allocations, complete immutable copies and scoped new bytes."""
    from video_creator.application.engine import canonical, digest
    from video_creator.workflows.affected_production import authorize, read_affected
    from video_creator.workflows.alignment_documents import speech_documents
    from video_creator.workflows.bundle_producer import _json
    from video_creator.workflows.bundle_recovery import _documents, _reference
    from video_creator.workflows.bundle_v03 import (
        PreparedV03Evidence,
        measure_alignment,
    )

    child, parent = state.child, state.parent
    if child is None:
        raise EngineError("alignment_child_missing", "The actual atomic selected child is required.", 409)
    allocations, documents, parent_receipts, parsed = _documents(parent)
    draft = parsed["transcript"]
    ids = parent.assembly.document_artifact_ids
    child_allocations = {value.artifact_id: value for value in child.allocations}
    if set(child_allocations) != set(allocations):
        raise EngineError("alignment_child_source_missing", "Complete parent source/license allocation closure must survive child selection.", 422)
    reference_input = _reference(parent, allocations, ids)
    evidence = PreparedV03Evidence(child.preparation, None, aligned, {}, "provenance_reference")
    if reference_input is not None:
        reference = reference_input.reference
        evidence.reference = reference
        original = parent_receipts["reference"]
        evidence.reference_ref = c.EvidenceReportRef(report_id=reference.report_id, schema_version=c.V03_SCHEMA_VERSION,
            evaluation_scope="per_work_reference_measurement", content_sha256=original.sha256)
        allocation = child_allocations[ids["measurement"]]
        evidence.measurement_locator = c.PerWorkReportLocator(report_id=allocation.material_id,
            artifact_id=allocation.artifact_id, material_id=allocation.material_id)
        evidence.correction_origin, evidence.correction_reason = reference_input.corrected_from, reference_input.correction_reason
    alignment = measure_alignment(evidence, aligned)
    video = next(value for value in parent.assembly.media_artifacts if value.roles == ("video",))
    asset = bundle.asset(lease, video.asset_id)
    document = speech_documents(documents, draft, alignment, parent.assembly.audio_mappings[0],
        assembly=parent.assembly, media=media, video=asset, video_path=bundle.content_path(lease, asset.asset_id),
        bundle_revision_id=child.intent.bundle_revision_id, project_id=context.project_id)
    documents["transcript"] = (*documents["transcript"][:2], _json(document))
    # Reports are generated from the actual new alignment only after current
    # registry resolution. Their old Ready bytes are never copied as new facts.
    for name in ("quality", "audit", "work_validation", "measurement"):
        if name in documents:
            documents[name] = (*documents[name][:2], None)
    existing = {receipt.artifact_id: (receipt, raw) for receipt, raw in child.materials}
    affected = set(state.execution.affected_artifact_ids)
    for name, (_, _, raw) in documents.items():
        if raw is None:
            continue
        identity = ids[name]
        prior = next((data for receipt, data in parent.materials if receipt.artifact_id == identity), None)
        if identity not in affected and raw != prior:
            raise EngineError("alignment_dependency_scope_incomplete", "Changed derived bytes require the actual authorized affected closure; no broad retry.", 403)
        authorize(port, lease, continuation, proposal, services, original=state.execution)
        if identity in existing:
            if existing[identity][1] != raw:
                raise EngineError("alignment_child_ready_conflict", "Existing actual child Ready bytes cannot be replaced.", 409)
        else:
            receipt = bundle.stage_material(lease, child.preparation.preparation_id, identity, raw)
            allocation = child_allocations[identity]
            if (receipt.material_id, receipt.sha256, receipt.size) != (allocation.material_id, hashlib.sha256(raw).hexdigest(), len(raw)):
                raise EngineError("alignment_child_allocation_invalid", "Actual child uses its own new allocation and complete original bytes.", 422)
    identity = c.AlignmentExecutionIdentity.model_validate(observation.result_json["execution_identity"])
    from video_creator.domain.registered_alignment import AffectedAlignmentRequest

    original_request = AffectedAlignmentRequest.model_validate_json(
        require_final_port(port).registered_alignment_request(lease, state.execution))
    method = c.MethodEvidence(method_id=identity.method_id, kind="model_inference", tool_name=identity.tool,
        tool_version=identity.tool_version, model_repository=identity.model_id,
        model_revision=original_request.alignment_registration.resources.model_revision,
        resource_manifest_sha256=identity.resource_manifest_sha256, operation_ids=(operation_id,),
        input_artifact_ids=tuple(value.artifact_id for value in parent.assembly.media_artifacts if value.roles == ("mixed_audio",)),
        config_sha256=identity.configuration_sha256,
        limitations=("Actual forced alignment is not independent work-boundary measurement.",))
    methods = tuple(value for value in parent.assembly.methods if value.method_id != identity.method_id) + (method,)
    assembly = parent.assembly.model_copy(update={"preparation_id": child.preparation.preparation_id,
        "preparation_intent_sha256": digest(canonical(child.intent)), "authored_fence": lease.fencing_token,
        "manifest_created_at_us": services.engine.clock(), "methods": methods})
    if child.assembly is not None:
        assembly = child.assembly
    else:
        require_final_port(port).persist_assembly_context(lease, child.preparation.preparation_id, assembly)
    return read_affected(port, lease, continuation, state.execution)
