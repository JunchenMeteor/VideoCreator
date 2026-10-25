"""Consume service-issued source facts, never grant source-copy permissions."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from video_creator.application.bundle_facts import (
    MAX_CORRECTION_ARTIFACTS,
    MAX_CORRECTION_REPORTS,
    CorrectionOriginEvidence,
    CorrectionSourceArtifact,
    VerifiedRightsEvidence,
)
from video_creator.domain import contracts as c
from video_creator.domain.bundle import MaterialSlot
from video_creator.domain.errors import EngineError
from video_creator.workflows.attempt_control import current_attempt


@dataclass(frozen=True)
class CorrectionCopyPlan:
    fact: CorrectionOriginEvidence
    documents: dict
    slots: dict
    sources: dict[str, tuple[CorrectionSourceArtifact, ...]]
    dependencies: dict
    ordered_names: tuple[str, ...]


def _scope(fact, instance_id, context, lease, request_sha256):
    if (fact.instance_id, fact.production_id, fact.run_id, fact.request_revision_id,
            fact.request_sha256, fact.fencing_token) != (
            instance_id, context.production_id, lease.run_id, context.request_revision_id,
            request_sha256, lease.fencing_token):
        raise EngineError("correction_evidence_required", "Source facts must belong to this exact request and ordinary fence.", 409)
    if not 0 <= fact.checked_at_us < lease.expires_at_us:
        raise EngineError("correction_evidence_required", "Source observation must precede this ordinary lease expiry.", 409)


def _source_bytes(source):
    handle, artifact = source.content, source.artifact
    if (handle.sha256, handle.size, handle.media_type) != (artifact.sha256, artifact.size, artifact.media_type):
        raise EngineError("correction_origin_integrity_failed", "The controlled source handle differs from its indexed bytes.", 422)
    # The service already bounded the complete logical source set against the
    # actual AssetService.max_bytes; the handle never grants a larger read.
    with handle.path.open("rb") as stream:
        chunks, size = [], 0
        while size <= handle.size:
            current_attempt().check()
            chunk = stream.read(min(1024 * 1024, handle.size + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
        raw = b"".join(chunks)
    if len(raw) != handle.size or hashlib.sha256(raw).hexdigest() != handle.sha256:
        raise EngineError("correction_origin_integrity_failed", "Controlled source bytes changed after the actual rights observation.", 422)
    return raw


def correction_copy_plan(fact, origin, artifact_ids, *, instance_id, context, lease, request_sha256):
    """Preserve all source snapshots while allocating one exact artifact copy."""
    from video_creator.application.bundles import record_sha, validate_text

    if not isinstance(fact, CorrectionOriginEvidence):
        raise EngineError("correction_evidence_required", "Only the fixed source-fact port supplies a correction closure.", 409)
    _scope(fact, instance_id, context, lease, request_sha256)
    if (not fact.reports or fact.reports[0].reference != origin
            or not {"derivative", "export", "redistribution"} <= set(fact.required_uses)):
        raise EngineError("correction_evidence_required", "The full source chain and actual portable-copy purposes are required.", 409)
    if len(fact.reports) > MAX_CORRECTION_REPORTS:
        raise EngineError("source_closure_limit", "Source report depth exceeds the fixed limit.", 413)

    candidates, raw_by_id, report_refs, report_ids = {}, {}, {}, set()
    parsed_reports = {}
    all_sources = [*(item.source for item in fact.reports), *fact.license_documents,
                   *(edge.indexed_child for edge in fact.dependency_edges)]
    unique_sources = []
    for source in all_sources:
        current_attempt().check()
        if not isinstance(source, CorrectionSourceArtifact):
            raise EngineError("correction_evidence_required", "Every original source retains its unique typed service fact.", 409)
        if source.source_bundle_ref.instance_id != instance_id or source.artifact.rights_ref != source.rights.rights_id:
            raise EngineError("correction_evidence_required", "Source indexes retain their actual local instance and exact right identity.", 409)
        if source not in unique_sources:
            unique_sources.append(source)
        if len(unique_sources) > MAX_CORRECTION_ARTIFACTS:
            raise EngineError("source_closure_limit", "The full distinct source set exceeds the fixed limit.", 413)
        identifier = source.artifact.artifact_id
        if identifier in artifact_ids.values():
            raise EngineError("correction_origin_conflict", "Source identities cannot collide with new work identities.", 409)
        if not source.artifact.material_id:
            raise EngineError("correction_source_kind_unavailable", "This material producer cannot copy an original media dependency.", 503)
        raw = _source_bytes(source)
        previous = candidates.setdefault(identifier, [])
        signature = (source.artifact.sha256, source.artifact.size, source.artifact.media_type,
                     source.schema_kind, source.record_content_sha256, source.artifact.roles, source.artifact.spec)
        if previous and signature != (previous[0].artifact.sha256, previous[0].artifact.size,
                previous[0].artifact.media_type, previous[0].schema_kind, previous[0].record_content_sha256,
                previous[0].artifact.roles, previous[0].artifact.spec):
            raise EngineError("correction_artifact_conflict", "Shared source identities retain identical bytes, grammar and record.", 422)
        if identifier in raw_by_id and raw_by_id[identifier] != raw:
            raise EngineError("correction_origin_integrity_failed", "Shared source copies have different actual bytes.", 422)
        raw_by_id[identifier] = raw
        if source not in previous:
            previous.append(source)

    for item in fact.reports:
        current_attempt().check()
        reference, source = item.reference, item.source
        identifier = source.artifact.artifact_id
        expected_kind = "precision_report" if reference.schema_version == c.SCHEMA_VERSION else "precision_report_v03"
        if (reference.report_id in report_ids or identifier in report_refs
                or source.schema_kind != expected_kind or source.artifact.roles != ("precision_evaluation",)
                or source.record_content_sha256 != reference.content_sha256
                or source.artifact.material_id != reference.material_id
                or identifier != reference.artifact_id or item.raw_bytes != raw_by_id[identifier]
                or hashlib.sha256(item.raw_bytes).hexdigest() != reference.sha256):
            raise EngineError("correction_lineage_invalid", "Each immutable original report retains its exact typed locator.", 422)
        parsed = validate_text(item.raw_bytes, expected_kind, source.artifact.media_type)
        if (parsed.evaluation_id, parsed.content_sha256, parsed.alignment_revision_id,
                parsed.alignment_content_sha256, record_sha(parsed)) != (
                reference.report_id, reference.content_sha256, reference.alignment_revision_id,
                reference.alignment_content_sha256, reference.content_sha256):
            raise EngineError("correction_origin_integrity_failed", "Original report bytes and internal audit identity disagree.", 422)
        report_ids.add(reference.report_id)
        report_refs[identifier] = reference
        parsed_reports[identifier] = parsed

    graph = {identifier: set() for identifier in candidates}
    for identifier, sources in candidates.items():
        for source in sources:
            graph[identifier].update(source.rights.license_document_artifact_ids)
            if identifier not in parsed_reports:
                graph[identifier].update(source.artifact.dependency_artifact_ids)
    edge_keys = set()
    for edge in fact.dependency_edges:
        parent_id, child_id = edge.parent.artifact.artifact_id, edge.child_reference.artifact_id
        if (parent_id not in parsed_reports or child_id not in report_refs
                or (parent_id, child_id) in edge_keys
                or edge.parent not in candidates[parent_id]
                or edge.indexed_child not in candidates[child_id]
                or edge.child_source not in candidates[child_id]
                or edge.child_reference != report_refs[child_id]
                or edge.indexed_child.artifact.artifact_id != child_id
                or child_id not in edge.parent.artifact.dependency_artifact_ids):
            raise EngineError("correction_lineage_invalid", "Every original parent edge must retain both actual indexed and source identities.", 422)
        parsed = parsed_reports[parent_id]
        if not isinstance(parsed, c.PrecisionEvaluationReportV03) or parsed.corrected_from != edge.child_reference:
            raise EngineError("correction_lineage_invalid", "Original report bytes determine the ancestor edge.", 422)
        edge_keys.add((parent_id, child_id))
        graph[parent_id].add(child_id)
    for identifier, parsed in parsed_reports.items():
        reference = parsed.corrected_from if isinstance(parsed, c.PrecisionEvaluationReportV03) else None
        if reference is not None and (identifier, reference.artifact_id) not in edge_keys:
            raise EngineError("correction_origin_unavailable", "A corrected source cannot omit its actual ancestor edge.", 409)
    if any(not dependencies <= set(graph) for dependencies in graph.values()):
        raise EngineError("correction_origin_unavailable", "Source permissions and necessary dependencies must be complete.", 409)
    pending, ordered = dict(graph), []
    while pending:
        current_attempt().check()
        ready = sorted(identifier for identifier, dependencies in pending.items() if dependencies <= set(ordered))
        if not ready:
            raise EngineError("correction_lineage_invalid", "Source reports and permission dependencies contain a cycle.", 422)
        ordered.extend(ready)
        for identifier in ready:
            del pending[identifier]

    names = {identifier: "correction-copy-" + str(number) for number, identifier in enumerate(ordered)}
    documents, slots, sources, dependencies = {}, {}, {}, {}
    for identifier in ordered:
        name, source = names[identifier], candidates[identifier][0]
        path = ("Checks" if identifier in parsed_reports else "License") + "/source-" + hashlib.sha256(identifier.encode()).hexdigest() + "." + ("txt" if source.artifact.media_type == "text/plain" else "json")
        slot = MaterialSlot(artifact_id=identifier, relative_path=path, schema_kind=source.schema_kind,
                            media_type=source.artifact.media_type)
        artifact_ids[name] = identifier
        documents[name] = (path, source.schema_kind, raw_by_id[identifier])
        slots[name], sources[name] = slot, tuple(candidates[identifier])
        dependencies[name] = tuple(sorted(graph[identifier]))
    return CorrectionCopyPlan(fact, documents, slots, sources, dependencies, tuple(names[identifier] for identifier in ordered))


def stage_correction_sources(bundle, lease, preparation, plan):
    receipts = {}
    for name in plan.ordered_names:
        current_attempt().check()
        slot, sources = plan.slots[name], plan.sources[name]
        allocated = bundle.material_allocation(lease, preparation.preparation_id, slot.artifact_id)
        if (allocated.artifact_id, allocated.relative_path, allocated.schema_kind, allocated.media_type) != (
                slot.artifact_id, slot.relative_path, slot.schema_kind, slot.media_type) or any(
                allocated.material_id == source.artifact.material_id for source in sources):
            raise EngineError("correction_origin_conflict", "Original bytes require a fresh current allocation and exact grammar.", 409)
        receipt = bundle.stage_material(lease, preparation.preparation_id, slot.artifact_id, plan.documents[name][2])
        source = sources[0].artifact
        if (receipt.preparation_id, receipt.artifact_id, receipt.material_id, receipt.sha256,
                receipt.size, receipt.media_type, receipt.schema_kind) != (
                preparation.preparation_id, slot.artifact_id, allocated.material_id, source.sha256,
                source.size, source.media_type, slot.schema_kind):
            raise EngineError("correction_origin_integrity_failed", "The new Ready receipt must preserve the complete original bytes.", 422)
        receipts[name] = receipt
    return receipts


def rights_check_from_fact(fact, *, instance_id, context, lease, request_sha256, preparation_id,
                           rights, approval_refs, revision_refs, artifacts, required_uses):
    """Use the actual service check, preserving not_measured/failed outcomes."""
    if not isinstance(fact, VerifiedRightsEvidence):
        raise EngineError("rights_facts_invalid", "Only the controlled rights service returns preparation facts.", 409)
    observed = fact.context
    if (observed.instance_id, observed.project_id, observed.production_id, observed.run_id,
            observed.request_revision_id, observed.request_sha256, observed.fencing_token,
            observed.preparation_id, observed.stage, observed.final_manifest_sha256) != (
            instance_id, context.project_id, context.production_id, lease.run_id, context.request_revision_id,
            request_sha256, lease.fencing_token, preparation_id, "pre_quality", None):
        raise EngineError("rights_facts_invalid", "Rights observations must cover the current ordinary fence and ready scope.", 409)
    if (observed.rights != rights or observed.approval_refs != approval_refs
            or observed.creative_revision_refs != revision_refs or observed.required_uses != required_uses
            or tuple(value.artifact for value in observed.artifacts) != artifacts
            or fact.quality_check.check_id != "rights"
            or set(fact.evidence_artifact_ids) != {value.artifact_id for value in artifacts}
            or fact.quality_check.evidence_artifact_ids != fact.evidence_artifact_ids
            or any(value not in approval_refs for value in fact.approval_refs)):
        raise EngineError("rights_facts_invalid", "The real returned check cannot be reused for other declarations, approvals or files.", 409)
    return fact.quality_check
