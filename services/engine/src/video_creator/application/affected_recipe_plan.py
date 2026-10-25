"""New finite plan source assembly, independently dispatched from legacy V2."""

import hashlib

from pydantic import ValidationError

from video_creator.domain.affected_recipe import (
    PlanRepairComponentTargetV1, PlanRepairTargetsV2, ProductionDriverResourcesV3,
    RegisteredProductionPlanV3, parse_production_recipe_resources,
)
from video_creator.domain.errors import EngineError
from video_creator.domain.plan_repair_targets import plan_payload_sha256


class AffectedRecipePlanService:
    def prepare_plan_repair_targets_v2(self, lease, *, proposal, script_revision_id, storyboard_revision_id):
        """Reuse authenticated source preparation, never its old dependency rules."""
        from video_creator.application.bundles import strict_json
        from video_creator.providers.production_resources import ProductionResources
        original = self.prepare_plan_repair_targets(lease, proposal=proposal,
            script_revision_id=script_revision_id, storyboard_revision_id=storyboard_revision_id)
        held = self._affected_services(lease)
        runtime = self._production_services_runtime
        raw = runtime.production_manifest.read_bytes()
        if hashlib.sha256(raw).hexdigest() != held[6] or len(raw) > 2 * 1024 * 1024:
            raise EngineError('production_resource_changed', 'Current complete resource manifest required', 503)
        document = strict_json(raw)
        try:
            resources = parse_production_recipe_resources(document.get('production_drivers'))
            if not isinstance(resources, ProductionDriverResourcesV3):
                raise ValueError('recipe catalog')
        except (ValidationError, ValueError, TypeError):
            raise EngineError('plan_repair_recipe_not_ready', 'Strict installed resource v3 recipe catalog required', 503) from None
        indexed = ProductionResources(runtime.production_manifest, held[6], held[7])
        components = []
        for target in original.targets[:-1]:
            components.append(PlanRepairComponentTargetV1(
                target_id=target.target_id, kind=target.kind, shot_ids=target.shot_ids,
                timeline_range=target.timeline_range, route_id=target.route_id, route_sha256=target.route_sha256,
                resource_section=target.resource_section, resource_section_sha256=target.resource_section_sha256,
                input_revision_refs=target.input_revision_refs, input_payload_template_sha256=target.input_payload_sha256,
                prerequisite_target_ids=target.prerequisite_target_ids, output_roles=target.output_roles,
                component_output_key='narration_audio' if target.kind == 'narration' else target.shot_ids[0], recipe_id=None))
        edit = original.targets[-1]
        output_roles = {'ambient-remix-v1': ('video', 'mixed_audio', 'cover'),
            'visual-preserve-mix-v1': ('video', 'cover'),
            'audio-remix-preserved-clips-v1': ('video', 'mixed_audio'),
            'cover-from-preserved-video-v1': ('cover',)}
        for recipe in resources.recipes:
            if (recipe.recipe_id == 'ambient-remix-v1' and recipe.component_target_ids
                    != tuple(target.target_id for target in original.targets[:-1]) + ('production-edit.ambient-remix-v1',)):
                raise EngineError('plan_repair_recipe_not_ready', 'Initial ambient catalog must retain original narration and all ordered clips', 503)
            for source in recipe.producer_source_refs:
                path = indexed.resource(source.resource_name)
                if hashlib.sha256(path.read_bytes()).hexdigest() != source.sha256:
                    raise EngineError('production_resource_changed', 'Original recipe producer index content changed', 503)
            route_refs = {ref.route_id: ref for ref in recipe.routes}
            for ref in recipe.routes:
                route = self.engine.configured_route(ref.route_id)
                if plan_payload_sha256(route) != ref.route_sha256 or route.cost_rule_version != ref.cost_rule_version:
                    raise EngineError('affected_route_denied', 'Actual recipe route and cost-rule version required', 403)
            edit_id = 'production-edit.' + recipe.recipe_id
            if edit.route_id not in route_refs:
                raise EngineError('plan_repair_recipe_not_ready', 'Recipe must bind the actual original edit route', 503)
            prerequisites = tuple(value for value in recipe.component_target_ids if value != edit_id)
            known = {value.target_id for value in components}
            if not set(prerequisites) <= known:
                raise EngineError('plan_repair_recipe_not_ready', 'Recipe references an unknown original component', 503)
            # Explicit fixed graph/template identity, not dependency intersection.
            template = {'format': 'current-plan-repair-edit-template-v1', 'recipe': recipe.model_dump(mode='json'),
                'storyboard_ref': original.storyboard_ref.model_dump(mode='json'),
                'script_ref': original.script_ref.model_dump(mode='json'),
                'timeline_duration_us': edit.timeline_range.end_us,
                'parent_role_inputs': ('video', 'narration_audio', 'mixed_audio', 'cover'),
                'component_target_ids': prerequisites, 'output_roles': output_roles[recipe.recipe_id]}
            components.append(PlanRepairComponentTargetV1(target_id=edit_id, kind='edit', shot_ids=edit.shot_ids,
                timeline_range=edit.timeline_range, route_id=edit.route_id, route_sha256=edit.route_sha256,
                resource_section='edit', resource_section_sha256=plan_payload_sha256(resources.edit),
                input_revision_refs=edit.input_revision_refs, input_payload_template_sha256=plan_payload_sha256(template),
                prerequisite_target_ids=prerequisites, output_roles=output_roles[recipe.recipe_id],
                component_output_key=','.join(output_roles[recipe.recipe_id]), recipe_id=recipe.recipe_id))
        result = PlanRepairTargetsV2(format='current-plan-repair-targets-v2', binding=original.binding,
            resource_manifest_sha256=original.resource_manifest_sha256, runtime_manifest_sha256=original.runtime_manifest_sha256,
            script_ref=original.script_ref, storyboard_ref=original.storyboard_ref,
            rights_declaration_sha256=original.rights_declaration_sha256, allowed_action=original.allowed_action,
            max_revision_cycles=original.max_revision_cycles, component_targets=tuple(components), recipes=resources.recipes)
        self.assert_current_production_services(lease, held[0], held[1])
        if runtime.production_manifest.read_bytes() != raw:
            raise EngineError('production_resource_changed', 'Original complete recipe source changed during preparation', 503)
        return result

    def validate_registered_plan_v3(self, lease, revision):
        try:
            from video_creator.domain.plan_repair_targets import plan_payload_bytes
            plan = RegisteredProductionPlanV3.model_validate_json(plan_payload_bytes(revision.body))
        except (ValidationError, ValueError, TypeError):
            raise EngineError('plan_repair_body_invalid', 'Strict original registered production plan v3 required', 422) from None
        if revision.kind != 'plan':
            raise EngineError('plan_repair_body_invalid', 'Only a plan may carry the finite recipe catalog', 422)
        targets = self.prepare_plan_repair_targets_v2(lease, proposal=plan.proposal,
            script_revision_id=plan.repair_targets.script_ref.revision_id,
            storyboard_revision_id=plan.repair_targets.storyboard_ref.revision_id)
        if (targets != plan.repair_targets or plan.timeline_duration_us != sum(shot.duration_us for shot in plan.proposal.shots)
                or any(ref not in revision.input_revision_refs for ref in (targets.script_ref.revision_id, targets.storyboard_ref.revision_id))):
            raise EngineError('plan_repair_source_invalid', 'Whole plan differs from actual held recipe projection', 422)
        return plan
