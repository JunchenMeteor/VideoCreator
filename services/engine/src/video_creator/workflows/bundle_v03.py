"""Forward-only 0.3 evidence assembly through the unique controlled bundle port."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from video_creator.domain import contracts as c
from video_creator.domain.bundle import BundlePreparationIntent, MaterialSlot
from video_creator.domain.errors import EngineError


@dataclass(frozen=True)
class IndependentReferenceMaterials:
    """Untrusted input holder; only the registry/real source facts admit it."""
    reference: c.PerWorkReferenceDocument
    reference_bytes: bytes
    source_documents: tuple[tuple[MaterialSlot, bytes], ...]
    corrected_from: c.CorrectionOriginRef | None = None
    correction_reason: str | None = None


@dataclass
class PreparedV03Evidence:
    preparation: object
    resolved: object
    alignment: c.AlignmentRevisionV03
    documents: dict
    benchmark_binding: str
    reference: c.PerWorkReferenceDocument | None = None
    reference_ref: c.EvidenceReportRef | None = None
    measurement_locator: c.PerWorkReportLocator | None = None
    correction_origin: c.CorrectionOriginRef | None = None
    correction_reason: str | None = None
    receipts: dict = field(default_factory=dict)
    dependencies: dict = field(default_factory=dict)
    correction_copies: object | None = None
    intent: BundlePreparationIntent | None = None


def _record(value):
    from video_creator.application.bundles import record_sha
    return value.model_copy(update={"content_sha256": record_sha(value)})


def _json(value):
    from video_creator.application.engine import canonical
    return (canonical(value) + "\n").encode("utf-8")


def runtime_source_gaps(actual):
    """Keep actual execution gaps separate from per-work precision limits."""
    gaps = actual.get("runtime_source_gaps", ())
    if not isinstance(gaps, (list, tuple)) or any(not isinstance(value, str) or not value.strip() for value in gaps):
        raise EngineError("work_validation_incomplete", "Runtime gaps require their actual explicit facts.", 409)
    return tuple(gaps)


def _work_runtime_gaps(actual, document, original_checks, required):
    reported = runtime_source_gaps(actual)
    gaps = tuple(document.transcript.source_gaps)
    if reported != gaps:
        gaps += reported
    for check in original_checks:
        if check.check_id == "rights" and check.check_id not in required:
            continue
        if check.status == "failed" or check.status == "not_measured" and check.check_id != "alignment":
            gaps += (f"{check.check_id}: {check.status}; " + "; ".join(check.findings),)
    return gaps


def _resolved_documents(bundle, lease, resolved, request, actual, reference_available):
    """Only actual registry/child facts can populate qualification documents."""
    if resolved is None or request.delivery_requirements is None:
        raise EngineError("alignment_required", "A real preauthorized evidence policy is required.", 409)
    identity_observed = c.AlignmentExecutionIdentity.model_validate(actual["runtime"].get("execution_identity"))
    if identity_observed != resolved.qualification.execution_identity:
        raise EngineError("alignment_required", "Actual child execution differs from its admitted qualification.", 409)
    requirement = request.delivery_requirements
    if (resolved.policy_ref != requirement.evidence_policy_revision_ref
        or resolved.policy.alignment_evidence_policy != requirement.alignment_evidence_policy
        or resolved.policy.alignment_requirement != requirement.alignment_requirement
        or requirement.alignment_requirement != "utterance_verified"):
        raise EngineError("alignment_required", "This producer has no independent word-level admission.", 409)
    strict = requirement.alignment_evidence_policy == "strict_reference_v1"
    if strict and not reference_available:
        raise EngineError("alignment_required", "Strict work measurement requires real independent source materials.", 409)
    # A restricted full benchmark cannot be converted into invented disclosure.
    benchmark = bundle.benchmark_reference(lease)
    if not isinstance(benchmark, c.MethodBenchmarkReference):
        raise EngineError("benchmark_disclosure_required", "A real licensed benchmark reference is required.", 409)
    if benchmark.origin_report_ref != resolved.qualification.benchmark_report_ref:
        raise EngineError("benchmark_binding_invalid", "Disclosure must retain the original admitted report.", 409)
    return {
        "policy": ("Checks/evidence-policy.json", "evidence_policy", _json(resolved.policy)),
        "qualification": ("Checks/method-qualification.json", "method_qualification", _json(resolved.qualification)),
        "benchmark": ("Checks/method-benchmark-reference.json", "method_benchmark_reference", _json(benchmark)),
        "work_validation": ("Checks/work-alignment-validation.json", "work_alignment_validation", None),
    }


def bind_v03_evidence(state, bundle, lease, resolved, request, actual):
    """Fill original allocated addresses using a real resolved registry."""
    documents = _resolved_documents(bundle, lease, resolved, request, actual, state.reference is not None)
    if set(documents) - set(state.documents):
        raise EngineError("final_evidence_allocation_conflict", "Registry evidence must use the original allocated addresses.", 409)
    state.documents.update(documents)
    state.resolved = resolved


def prepare_v03_evidence(bundle, lease, resolved, context, request, bundle_id, revision_id, slots,
                         artifact_ids, media_asset_ids, actual, transcript, alignment,
                         *, instance_id: str, reference_evidence: IndependentReferenceMaterials | None = None,
                         selected_child=None, defer_measurement=False):
    """Allocate first when unresolved; allocation is never a qualification.

    Current v2 resolves its real registry through the held evidence port after
    ordinary inputs become Ready. Original v1 passes its registry here and
    retains its original checks and staging order.
    """
    from video_creator.application.engine import canonical, digest, identity
    from video_creator.workflows.bundle_correction import (
        correction_copy_plan,
        stage_correction_sources,
    )

    if resolved is not None:
        documents = _resolved_documents(bundle, lease, resolved, request, actual, reference_evidence is not None)
    else:
        if request.delivery_requirements is None:
            raise EngineError("evidence_policy_unavailable", "Explicit versioned requirements must retain their original evidence kinds.", 409)
        documents = {
            "policy": ("Checks/evidence-policy.json", "evidence_policy", None),
            "qualification": ("Checks/method-qualification.json", "method_qualification", None),
            "benchmark": ("Checks/method-benchmark-reference.json", "method_benchmark_reference", None),
            "work_validation": ("Checks/work-alignment-validation.json", "work_alignment_validation", None),
        }
        if request.delivery_requirements.alignment_evidence_policy == "strict_reference_v1" and reference_evidence is None:
            documents["reference"] = ("Checks/precision-reference.json", "precision_reference_v03", None)
            documents["measurement"] = ("Checks/precision-evaluation.json", "precision_report_v03", None)
    sources = {}
    correction_copies = None
    if reference_evidence is not None:
        reference = reference_evidence.reference
        if reference.input_audio_sha256 != transcript.input_audio_sha256:
            raise EngineError("reference_binding_invalid", "Independent reference belongs to another actual audio.", 409)
        unit_ids = tuple(value.utterance_id for value in transcript.utterances)
        if reference.units != unit_ids or set(unit_ids) != {value.transcript_unit_id for value in reference.boundaries}:
            raise EngineError("reference_binding_invalid", "Independent reference must cover every original actual unit.", 409)
        if any(value.reference_range.end_us > transcript.duration_us for value in reference.boundaries):
            raise EngineError("reference_binding_invalid", "Original independent boundaries exceed the actual audio.", 409)
        if bool(reference_evidence.corrected_from) != bool(reference_evidence.correction_reason):
            raise EngineError("correction_origin_missing", "An immutable correction retains its real origin and reason.", 409)
        if reference_evidence.corrected_from is not None:
            # The raw-reader alone cannot authorize portable ancestor copies.
            origin_fact = bundle.correction_origin_evidence(lease, reference_evidence.corrected_from,
                                                           purpose="derivative")
            correction_copies = correction_copy_plan(origin_fact, reference_evidence.corrected_from,
                    artifact_ids, instance_id=instance_id, context=context, lease=lease,
                    request_sha256=digest(canonical(request)))
            documents.update(correction_copies.documents)
        expected_sources = {ref.artifact_id: ref for ref in (*reference.independent_listener_refs, reference.arbitration_ref)}
        for number, (slot, data) in enumerate(reference_evidence.source_documents):
            if slot.artifact_id not in expected_sources or slot.schema_kind != "audit_summary":
                raise EngineError("reference_source_invalid", "Only the original listener/arbitration source files are allowed.", 409)
            name = "reference-source-" + str(number)
            if slot.artifact_id in {item.artifact_id for item in sources.values()}:
                raise EngineError("reference_source_invalid", "Original source artifacts are distinct.", 409)
            sources[name] = slot
            artifact_ids[name] = slot.artifact_id
            documents[name] = (slot.relative_path, slot.schema_kind, data)
        if {item.artifact_id for item in sources.values()} != set(expected_sources):
            raise EngineError("reference_source_invalid", "Independent source materials must be available in full.", 409)
        documents["reference"] = ("Checks/precision-reference.json", "precision_reference_v03", reference_evidence.reference_bytes)
        documents["measurement"] = ("Checks/precision-evaluation.json", "precision_report_v03", None)
    actual_slots = tuple(slot.model_copy(update={"schema_kind": "actual_transcript_v03"})
                         if slot.artifact_id == artifact_ids["transcript"] else slot for slot in slots)
    extra_slots = tuple(correction_copies.slots[name] if correction_copies is not None and name in correction_copies.slots
                        else MaterialSlot(artifact_id=artifact_ids[name], relative_path=value[0], schema_kind=value[1],
                          media_type="application/json") if name not in sources else sources[name]
                        for name, value in documents.items())
    intent = BundlePreparationIntent(bundle_id=bundle_id, bundle_revision_id=revision_id,
                    request_revision_id=context.request_revision_id, input_sha256=digest(canonical(request)),
                    material_slots=actual_slots + extra_slots, media_asset_ids=media_asset_ids)
    if selected_child is None:
        preparation = bundle.prepare(lease, intent)
    else:
        from video_creator.domain.current_final_evidence import (
            CurrentFinalEvidenceReadSet,
        )

        if type(selected_child) is not CurrentFinalEvidenceReadSet:
            raise EngineError("affected_child_source_invalid", "Only the original held selected child read set can supply preparation.", 403)
        actual_intent = selected_child.intent
        slots_by_id = {slot.artifact_id: slot for slot in actual_intent.material_slots}
        if (len(slots_by_id) != len(actual_intent.material_slots)
                or (intent.bundle_id, intent.bundle_revision_id, intent.request_revision_id, intent.input_sha256, intent.media_asset_ids)
                    != (actual_intent.bundle_id, actual_intent.bundle_revision_id, actual_intent.request_revision_id,
                        actual_intent.input_sha256, actual_intent.media_asset_ids)
                or any(slots_by_id.get(slot.artifact_id) != slot for slot in intent.material_slots)):
            raise EngineError("affected_child_allocation_invalid", "Every constructed source uses its actual atomic child allocation; no second prepare or renamed slot.", 422)
        intent = actual_intent
        preparation = bundle.recover_preparation(lease, selected_child.preparation.preparation_id)
        if (preparation.bundle_id, preparation.bundle_revision_id) != (intent.bundle_id, intent.bundle_revision_id):
            raise EngineError("affected_child_allocation_invalid", "Actual child preparation must retain its committed intent.", 409)
    state = PreparedV03Evidence(preparation, resolved, alignment, documents, "provenance_reference")
    state.intent = intent
    state.correction_copies = correction_copies
    state.dependencies.update({name: (artifact_ids["mixed"],) for name in ("transcript", "srt", "vtt", "segments", "rag")})
    state.dependencies.update(policy=(artifact_ids["qualification"],), qualification=(artifact_ids["benchmark"],),
                              work_validation=(artifact_ids["policy"], artifact_ids["transcript"]),
                              quality=(artifact_ids["work_validation"],))
    if reference_evidence is not None:
        if reference_evidence.corrected_from is not None:
            state.receipts.update(stage_correction_sources(bundle, lease, preparation, correction_copies))
            state.dependencies.update(correction_copies.dependencies)
        for name in (*sources, "reference"):
            receipt = bundle.stage_material(lease, preparation.preparation_id, artifact_ids[name], documents[name][2])
            state.receipts[name] = receipt
            if name in sources and receipt.sha256 != expected_sources[receipt.artifact_id].sha256:
                raise EngineError("reference_source_invalid", "Original independent source file bytes changed.", 409)
        reference_receipt = state.receipts.get("reference")
        reference_raw = (reference_evidence.reference_bytes if reference_receipt is None else
                         bundle.read_material(lease, preparation.preparation_id, reference_receipt.material_id))
        reference = c.PerWorkReferenceDocument.model_validate_json(reference_raw)
        if reference != reference_evidence.reference:
            raise EngineError("reference_binding_invalid", "Typed reference and actual ready reference bytes differ.", 409)
        state.reference = reference
        state.correction_origin = reference_evidence.corrected_from
        state.correction_reason = reference_evidence.correction_reason
        state.reference_ref = c.EvidenceReportRef(report_id=reference.report_id, schema_version=c.V03_SCHEMA_VERSION,
                    evaluation_scope="per_work_reference_measurement", content_sha256=hashlib.sha256(reference_raw).hexdigest())
        allocation = bundle.material_allocation(lease, preparation.preparation_id, artifact_ids["measurement"])
        if allocation.schema_kind != "precision_report_v03" or allocation.artifact_id != artifact_ids["measurement"]:
            raise EngineError("material_allocation_invalid", "Measurement must use the original allocated report slot.", 409)
        state.measurement_locator = c.PerWorkReportLocator(report_id=identity("precision-report") if selected_child is None and not defer_measurement else allocation.material_id,
                    artifact_id=allocation.artifact_id, material_id=allocation.material_id)
        if not defer_measurement:
            references = {item.transcript_unit_id: item.reference_range for item in reference.boundaries}
            errors = [max(abs(item.intrinsic_range.start_us - references[item.transcript_unit_id].start_us),
                          abs(item.intrinsic_range.end_us - references[item.transcript_unit_id].end_us)) for item in alignment.boundaries]
            p95 = sorted(errors)[(95 * len(errors) + 99) // 100 - 1]
            precision = c.PrecisionAssessmentV03(status="measured", units="utterance", sample_count=len(errors), p95_error_us=p95,
                        reference_ref=state.reference_ref, measurement_report_locator=state.measurement_locator,
                        criterion_version_ref="alignment-unit-max-p95-200ms-v1")
            state.alignment = _record(alignment.model_copy(update={"precision": precision}))
        state.dependencies.update(reference=tuple(slot.artifact_id for slot in sources.values()) + (artifact_ids["mixed"],),
                    measurement=(artifact_ids["reference"], artifact_ids["transcript"]),
                    transcript=(artifact_ids["mixed"], artifact_ids["reference"]),
                    work_validation=(artifact_ids["policy"], artifact_ids["transcript"], artifact_ids["measurement"]))
        if state.correction_origin is not None:
            state.dependencies["measurement"] += (state.correction_origin.artifact_id,)
    return state


def measure_alignment(state, alignment):
    """Independent evidence applies after CTC; it is never sent to the worker."""
    if state.reference is None:
        state.alignment = alignment
        return alignment
    references = {value.transcript_unit_id: value.reference_range for value in state.reference.boundaries}
    if alignment.units != "utterance" or tuple(references) != tuple(value.transcript_unit_id for value in alignment.boundaries):
        raise EngineError("reference_binding_invalid", "Actual acoustic units and independent reference must match exactly.", 409)
    errors = [max(abs(value.intrinsic_range.start_us - references[value.transcript_unit_id].start_us),
                  abs(value.intrinsic_range.end_us - references[value.transcript_unit_id].end_us)) for value in alignment.boundaries]
    precision = c.PrecisionAssessmentV03(status="measured", units=alignment.units, sample_count=len(errors),
        p95_error_us=sorted(errors)[(95 * len(errors) + 99) // 100 - 1], reference_ref=state.reference_ref,
        measurement_report_locator=state.measurement_locator, criterion_version_ref="alignment-unit-max-p95-200ms-v1")
    state.alignment = _record(alignment.model_copy(update={"precision": precision}))
    return state.alignment


def finish_v03_evidence(state, context, request, document, mapping, actual, operation_id, lease,
                        quality_revision_ref, artifact_ids, assembly_checks, *, work_report_id=None,
                        source_operation_ids=()):
    """Runtime observations are separate from independent per-work precision."""
    from video_creator.application.engine import canonical, digest, identity

    if state.resolved is None:
        raise EngineError("final_evidence_resolution_required", "Allocation cannot generate an admitted WorkValidation report.", 409)
    documents = dict(state.documents)
    execution = c.AlignmentExecutionIdentity.model_validate(actual["runtime"]["execution_identity"])
    if execution != state.resolved.qualification.execution_identity:
        raise EngineError("alignment_required", "Execution qualification changed while producing this work.", 409)
    quality_checks = tuple(check.model_copy(update={"status": "verified", "findings": (
                    "Actual audio/units/mapping/schema assembly observed; no per-work precision claim.",)})
                    if check.check_id == "alignment" else check for check in assembly_checks)
    required = set(state.resolved.policy.required_checks)
    if not required <= {check.check_id for check in quality_checks}:
        raise EngineError("alignment_required", "This producer has not observed every additional policy check.", 409)
    checks = tuple(check for check in quality_checks if check.check_id != "rights" or check.check_id in required)
    gaps = _work_runtime_gaps(actual, document, assembly_checks, required)
    complete = not gaps and all(check.status == "verified" for check in checks)
    report = _record(c.WorkAlignmentValidationReport(schema_version=c.V03_SCHEMA_VERSION,
                    evaluation_scope="work_runtime_validation", report_id=work_report_id if work_report_id is not None else identity("work-validation"),
                    production_id=context.production_id, run_id=lease.run_id,
                    request_revision_id=context.request_revision_id, request_sha256=digest(canonical(request)),
                    input_audio_asset_id=document.transcript.input_audio_asset_id,
                    input_audio_sha256=document.transcript.input_audio_sha256,
                    transcript_revision_id=document.transcript.transcript_revision_id,
                    transcript_content_sha256=document.transcript.content_sha256,
                    alignment_revision_id=document.alignment.alignment_revision_id,
                    alignment_content_sha256=document.alignment.content_sha256,
                    mapping_refs=(c.AudioMappingEvidenceRef(mapping_revision_id=mapping.mapping_revision_id,
                                  content_sha256=mapping.content_sha256),),
                    subtitle_revision_id=document.subtitles.subtitle_revision_id,
                    subtitle_content_sha256=document.subtitles.content_sha256,
                    operation_ids=tuple(dict.fromkeys((*source_operation_ids, operation_id))),
                    execution_identity=execution, transformations=("encode",),
                    evidence_policy_revision_ref=state.resolved.policy_ref, qualification_ref=state.resolved.qualification,
                    checks=checks, result="verified" if complete else "incomplete",
                    source_gaps=gaps,
                    reasons=() if complete else ("One or more checks, including independent rights clearance, remain unverified.",),
                    content_sha256="0" * 64))
    documents["work_validation"] = (*documents["work_validation"][:2], _json(report))
    measurement_ref = None
    if state.reference is not None:
        # Construct the immutable measurement after the final Alignment hash.
        references = {value.transcript_unit_id: value.reference_range for value in state.reference.boundaries}
        boundaries = tuple(c.PrecisionBoundaryPair(transcript_unit_id=value.transcript_unit_id,
                    predicted_range=value.intrinsic_range, reference_range=references[value.transcript_unit_id])
                    for value in document.alignment.boundaries)
        precision = document.alignment.precision
        measurement = _record(c.PrecisionEvaluationReportV03(schema_version=c.V03_SCHEMA_VERSION,
                    evaluation_scope="per_work_reference_measurement", evaluation_id=state.measurement_locator.report_id,
                    input_audio_sha256=document.transcript.input_audio_sha256,
                    alignment_revision_id=document.alignment.alignment_revision_id,
                    alignment_content_sha256=document.alignment.content_sha256, units="utterance",
                    boundaries=boundaries, sample_count=precision.sample_count, p95_error_us=precision.p95_error_us,
                    criterion_version_ref="alignment-unit-max-p95-200ms-v1", reference_ref=state.reference_ref,
                    authority_ref=state.reference.authority_ref.authority_id,
                    reference_material_id=state.receipts["reference"].material_id, method_ref=document.alignment.method_ref,
                    corrected_from=state.correction_origin,
                    correction_reason=state.correction_reason,
                    content_sha256="0" * 64))
        documents["measurement"] = (*documents["measurement"][:2], _json(measurement))
        measurement_ref = c.EvidenceReportRef(report_id=measurement.evaluation_id, schema_version=c.V03_SCHEMA_VERSION,
                    evaluation_scope="per_work_reference_measurement", content_sha256=measurement.content_sha256)
    quality = _record(c.BundleQualityEvidenceV03(schema_version=c.V03_SCHEMA_VERSION,
                    quality_revision_ref=quality_revision_ref, checks=quality_checks,
                    evidence_policy_revision_ref=state.resolved.policy_ref, qualification_ref=state.resolved.qualification,
                    work_validation_report_ref=c.EvidenceReportRef(report_id=report.report_id, schema_version=c.V03_SCHEMA_VERSION,
                        evaluation_scope="work_runtime_validation", content_sha256=report.content_sha256),
                    per_work_measurement_report_ref=measurement_ref, content_sha256="0" * 64))
    return documents, quality
