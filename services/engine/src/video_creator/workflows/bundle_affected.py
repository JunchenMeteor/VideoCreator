"""Actual selected child facts and original registered ASR; no new authority."""
from __future__ import annotations

import json

from video_creator.domain import contracts as c
from video_creator.domain.bundle import BundlePreparationIntent
from video_creator.domain.errors import EngineError
from video_creator.workflows.affected_production import (
    MEDIA_TYPES,
    authorize,
    read_affected,
)
from video_creator.workflows.attempt_control import current_attempt
from video_creator.workflows.current_final_evidence import require_final_port


def select_child(port, lease, continuation, proposal, services, execution, observation):
    """Atomic lineage/counter comes from the sole held revision writer."""
    from video_creator.application.engine import canonical, digest

    authorize(port, lease, continuation, proposal, services, original=execution)
    state = read_affected(port, lease, continuation, execution)
    if state.child is not None:
        return state
    parent = state.parent
    if (observation is not None and state.masters is not observation
            and (state.masters is None or dict(state.masters.effective_media_roles) != dict(observation.effective_media_roles))):
        raise EngineError("affected_master_observation_invalid", "Only the real committed original master observation can supply child media.", 409)
    roles = ({artifact.roles[0]: artifact.asset_id for artifact in parent.assembly.media_artifacts}
             if observation is None else dict(state.masters.effective_media_roles))
    if set(roles) != set(MEDIA_TYPES) or len(set(roles.values())) != 4:
        raise EngineError("affected_child_media_invalid", "The real effective four-role mapping is required before child creation.", 422)
    # This is a stable authored revision address, not an Asset or execution
    # identity. Original actual slot IDs/layout remain under NEW allocations.
    revision = "repair-bundle-revision-" + execution.repair_command_sha256[:40]
    intent = BundlePreparationIntent(bundle_id=parent.intent.bundle_id, bundle_revision_id=revision,
                request_revision_id=parent.intent.request_revision_id, input_sha256=parent.intent.input_sha256,
                material_slots=parent.intent.material_slots, media_asset_ids=tuple(roles[role] for role in MEDIA_TYPES))
    child = require_final_port(port).revise_preparation(lease, parent.preparation.preparation_id, intent,
                affected_artifact_ids=execution.affected_artifact_ids)
    state = read_affected(port, lease, continuation, execution)
    if (state.child is None or state.child.preparation.preparation_id != child.preparation_id
            or digest(canonical(state.child.intent)) != digest(canonical(intent))):
        raise EngineError("affected_child_commit_invalid", "Only the actual atomic selected child and complete committed intent may be consumed.", 409)
    if {allocation.material_id for allocation in state.child.allocations} & {allocation.material_id for allocation in parent.allocations}:
        raise EngineError("affected_child_allocation_invalid", "Actual child allocations cannot reuse any parent material ID.", 422)
    return state


def child_asr(port, lease, continuation, proposal, services, state, *, resources, media, runtime_root, mixed, timeline):
    """Use the registered exact intent; original context is journaled by executor."""
    from video_creator.application.engine import digest
    from video_creator.workflows.bundle_recovery import _actual

    execution = state.execution
    authorize(port, lease, continuation, proposal, services, original=execution)
    intent = require_final_port(port).registered_child_asr_intent(lease, execution)
    if intent is None:
        actual = _actual(state.parent)
        if (actual["input_audio_sha256"], actual["duration_us"]) != (mixed.sha256, timeline):
            raise EngineError("affected_asr_source_invalid", "Unchanged audio requires the actual original ASR hash and complete timeline.", 422)
        source = state.parent.asr
        return actual, {"id": source.operation_id, "settled": source.settled}, source.input_sha256
    if type(intent) is not c.OperationIntent or intent.reserved_cost.units():
        raise EngineError("affected_asr_intent_invalid", "Only the original registered credential-free local child intent is usable.", 403)
    expected = digest(json.dumps({"audio_sha256": mixed.sha256, "resource_manifest_sha256": resources.manifest_sha256}, sort_keys=True))
    if intent.input_sha256 != expected:
        raise EngineError("affected_asr_resource_conflict", "Actual original registered child audio and installed ASR resources must match.", 409)
    services.engine.begin_step(lease, intent.step_key, intent.input_sha256)
    original = services.engine.prepare_operation(lease, intent)
    # A terminal successful original is read through its persisted validation
    # context; unknown/failed originals are never sent to the model again.
    if original["status"] == "succeeded" and original["settled"]:
        restored = read_affected(port, lease, continuation, execution)
        actual = _actual(restored.child)
    else:
        if original["status"] != "prepared":
            raise EngineError("affected_asr_unresolved", "The original child ASR requires its existing reconciliation boundary.", 409,
                        "reconcile" if original["status"] in {"submitting", "unknown", "pending"} else "never")
        control = current_attempt()
        driver = resources.driver(services.bundle.content_path(lease, mixed.asset_id), storage_root=media.root,
                    runtime_root=runtime_root, expected_audio_sha256=mixed.sha256,
                    timeout_seconds=control.remaining(60), cancel=control.cancel_requested,
                    deadline_monotonic=control.deadline_monotonic)
        authorize(port, lease, continuation, proposal, services, original=execution)
        observation = services.executor.execute(lease, intent, driver)
        if observation.status != "succeeded":
            raise EngineError("affected_asr_unresolved", "Keep the original registered child outcome rather than resubmitting under another key.", 409,
                        "reconcile" if observation.status in {"unknown", "pending"} else "never")
        original = services.engine.prepare_operation(lease, intent)
        if not original["settled"] or original["status"] != "succeeded":
            raise EngineError("affected_asr_unresolved", "A result alone is not its actual settled original Operation.", 409, "reconcile")
        restored = read_affected(port, lease, continuation, execution)
        actual = _actual(restored.child)
    if (actual["input_audio_sha256"], actual["duration_us"]) != (mixed.sha256, timeline):
        raise EngineError("affected_asr_binding_invalid", "New audio requires its complete actually validated new inference and decoded timeline.", 422)
    authorize(port, lease, continuation, proposal, services, original=execution)
    services.engine.complete_step(lease, intent.step_key, result_json=actual)
    return actual, original, intent.input_sha256


def parent_documents(state):
    from video_creator.workflows.bundle_recovery import _documents

    return _documents(state.parent)


def preserve_documents(state, documents, artifact_ids):
    """Immutable parent copies under new child IDs; no broad changed fallback."""
    _, original, receipts, _ = parent_documents(state)
    affected = set(state.execution.affected_artifact_ids)
    for name, prior in original.items():
        identity = artifact_ids.get(name)
        if identity is None:
            raise EngineError("affected_child_source_missing", "The complete original document/license/source closure must be retained.", 422)
        if name not in documents:
            documents[name] = prior
        if identity not in affected and name in receipts:
            produced = documents[name][2]
            if produced is not None and produced != prior[2]:
                raise EngineError("affected_dependency_scope_incomplete", "Changed source bytes require their actual original affected dependency closure; no all-document fallback.", 403)
            documents[name] = prior
    allocations = {allocation.artifact_id: allocation for allocation in state.child.allocations}
    if {artifact_ids[name] for name in documents} != set(allocations):
        raise EngineError("affected_child_allocation_invalid", "Every child slot must retain its complete original author name and typed source.", 422)
    for name, (path, kind, _) in documents.items():
        allocation = allocations[artifact_ids[name]]
        if (path, kind) != (allocation.relative_path, allocation.schema_kind):
            raise EngineError("affected_child_allocation_invalid", "Actual child allocation grammar and path cannot be changed by assembly.", 422)
    return documents


def ready_child_sources(bundle, lease, state, documents, artifact_ids):
    """Read actual child Ready bytes, rejecting any computed-content conflict."""
    ready = {}
    for receipt, raw in state.child.materials:
        name = next((name for name, identity in artifact_ids.items() if identity == receipt.artifact_id and name in documents), None)
        if name is None or documents[name][2] != raw:
            raise EngineError("affected_child_ready_conflict", "Committed child sources are immutable and cannot be overwritten after a crash.", 409)
        if bundle.read_material(lease, state.child.preparation.preparation_id, receipt.material_id) != raw:
            raise EngineError("affected_child_ready_conflict", "The actual scoped child source must retain its complete original bytes.", 422)
        ready[name] = receipt
    return ready
