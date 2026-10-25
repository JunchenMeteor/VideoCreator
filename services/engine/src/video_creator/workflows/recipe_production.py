"""Finite recipe consumers. Targets and current permission stay in Backend."""
from __future__ import annotations

from video_creator.domain.affected_recipe import (
    AffectedRepairExecutionV2,
    AffectedRepairProposalV2,
    parse_registered_recipe_plan,
)
from video_creator.domain.affected_repair_steps import affected_recipe_step
from video_creator.domain.component_diagnosis import AffectedRepairExecutionDiagnosedV1
from video_creator.domain.errors import EngineError

RECIPE_EXECUTIONS = {AffectedRepairExecutionV2, AffectedRepairExecutionDiagnosedV1}


def recipe_step(execution, stage, *, shot_id=None):
    component = {"master": "production-master", "narration": "production-narration",
                 "picture": "production-" + (shot_id or ""), "edit": "production-edit." + execution.recipe_id}[stage]
    return affected_recipe_step(execution, stage, component_target_id=component)


def require_recipe_execution(value, continuation, proposal):
    repair = continuation.snapshot.repair
    if type(value) not in RECIPE_EXECUTIONS or type(proposal) is not AffectedRepairProposalV2 or repair is None:
        raise EngineError("affected_recipe_execution_invalid", "Actual held recipe execution and its sole finite proposal are required.", 403)
    fields = ("parent_preparation_id", "affected_artifact_ids", "failed_unit_ids", "requested_action",
              "changed_media_roles", "impacted_shot_ids", "regenerated_shot_ids", "recipe_id",
              "projection_sha256", "recipe_binding_sha256", "component_target_ids")
    if any(getattr(value, field) != getattr(proposal, field) for field in fields):
        raise EngineError("affected_recipe_execution_invalid", "Every actual command field must retain the exact admitted finite proposal.", 403)
    if type(value) is AffectedRepairExecutionDiagnosedV1:
        if (value.diagnostic_ref != repair.diagnostic_ref or value.source_report_ref != repair.precision_report_ref
                or value.input_key_sha256 != value.diagnostic_ref.input_key_sha256):
            raise EngineError("affected_recipe_source_invalid", "A component command cannot replace its original diagnostic or independent precision source.", 403)
    elif value.source_report_ref != repair.source_report_ref:
        raise EngineError("affected_recipe_source_invalid", "Actual original independent report required.", 403)
    return value


def command_facts(value):
    fields = ("binding", "execution_fence", "parent_preparation_id", "parent_intent_sha256",
              "repair_command_sha256", "source_report_ref", "affected_artifact_ids", "failed_unit_ids",
              "requested_action", "changed_media_roles", "impacted_shot_ids", "regenerated_shot_ids",
              "recipe_id", "projection_sha256", "recipe_binding_sha256", "component_target_ids")
    facts = (type(value),) + tuple(getattr(value, field) for field in fields)
    if type(value) is AffectedRepairExecutionDiagnosedV1:
        facts += (value.diagnostic_ref, value.input_key_sha256)
    return facts


def recipe_for_command(execution, body):
    plan = parse_registered_recipe_plan(body)
    if plan.format != "registered-production-plan-v3":
        raise EngineError("affected_recipe_plan_missing", "Old approved plans cannot be retrofitted with a recipe catalog.", 403)
    recipe = next((value for value in plan.repair_targets.recipes if value.recipe_id == execution.recipe_id), None)
    if (recipe is None or execution.changed_media_roles not in recipe.allowed_output_variants
            or not set(execution.component_target_ids) <= set(recipe.component_target_ids)
            or set(execution.regenerated_shot_ids) - {shot.shot_id for shot in plan.proposal.shots}
            or execution.recipe_id in {"audio-remix-preserved-clips-v1", "cover-from-preserved-video-v1"} and execution.regenerated_shot_ids):
        raise EngineError("affected_recipe_scope_invalid", "Exactly the original registered recipe, changed output variant and finite generation targets are required.", 403)
    return recipe


def preserved_clips(port, lease, continuation, execution, services, shots):
    """Read current original clip provenance, never choose a latest/initial Step."""
    from video_creator.workflows.attempt_control import current_attempt
    current_attempt().check()
    recorded = port.read_component_diagnosis(continuation)
    sources = () if recorded is None else recorded.fact.source_media_refs
    result = {}
    for shot in shots:
        candidates = [source for source in sources if source.role == "shot_clip" and source.shot_ids == (shot.shot_id,)]
        if len(candidates) != 1:
            raise EngineError("affected_current_clip_provenance_unavailable", "Current parent clip sources require the controlled original edit Operation lineage; initial source Steps cannot substitute after a repair.", 503)
        source = candidates[0]
        asset = services.bundle.asset(lease, source.asset_id)
        path = services.bundle.content_path(lease, source.asset_id)
        probe = services.media_validator(path, "video/mp4")
        if (asset.sha256, asset.size, asset.probe, asset.media_type) != (source.sha256, source.size, source.probe, "video/mp4") or probe != source.probe or not probe.decoded:
            raise EngineError("affected_clip_source_changed", "Preserved actual clip bytes and complete decoder evidence must remain identical.", 409)
        result[shot.shot_id] = source.asset_id
    return result
