"""ADR0058 finite plan data. No serialized value is an execution permit."""

from dataclasses import dataclass
from typing import Literal

from pydantic import Field, model_validator

from video_creator.domain import contracts as c
from video_creator.domain.affected_repair import MediaRole, AffectedMasterObservation, ProductionDriverResourcesV2
from video_creator.domain.bundle import MaterialReceipt
from video_creator.domain.current_final_evidence import FinalModel, CurrentFinalEvidenceReadSet
from video_creator.domain.plan_repair_targets import PlanRepairRevisionRef
from video_creator.domain.registered_production import ProductionBinding, ProductionRightsProposal

RecipeId = Literal['ambient-remix-v1', 'visual-preserve-mix-v1',
                   'audio-remix-preserved-clips-v1', 'cover-from-preserved-video-v1']
ROLE_ORDER = ('video', 'narration_audio', 'mixed_audio', 'cover')


class RecipeSourceRef(FinalModel):
    resource_name: str = Field(min_length=1, max_length=500)
    sha256: c.Sha256

    @model_validator(mode='after')
    def indexed_name(self):
        from pathlib import PurePosixPath
        name = PurePosixPath(self.resource_name)
        if (name.is_absolute() or not name.parts or name.as_posix() != self.resource_name
                or any(value in {'.', '..'} or ':' in value or '\\' in value for value in name.parts)):
            raise ValueError('Original held index relative name required')
        return self


class RecipeRouteRef(FinalModel):
    route_id: c.Identifier
    route_sha256: c.Sha256
    cost_rule_version: str = Field(min_length=1, max_length=300)


class PlanRepairComponentTargetV1(FinalModel):
    target_id: c.Identifier
    kind: Literal['narration', 'shot_clip', 'edit']
    shot_ids: tuple[c.Identifier, ...]
    timeline_range: c.MediaRange
    route_id: c.Identifier
    route_sha256: c.Sha256
    resource_section: Literal['narration', 'picture', 'edit']
    resource_section_sha256: c.Sha256
    input_revision_refs: tuple[PlanRepairRevisionRef, ...] = Field(min_length=1)
    input_payload_template_sha256: c.Sha256
    prerequisite_target_ids: tuple[c.Identifier, ...]
    output_roles: tuple[Literal['narration_audio', 'shot_clip', 'video', 'mixed_audio', 'cover'], ...] = Field(min_length=1)
    component_output_key: str = Field(min_length=1, max_length=300)
    recipe_id: RecipeId | None

    @model_validator(mode='after')
    def finite_component(self):
        for values in (self.shot_ids, self.prerequisite_target_ids, self.output_roles):
            if len(values) != len(set(values)):
                raise ValueError('Distinct finite component members required')
        if self.target_id in self.prerequisite_target_ids:
            raise ValueError('Self prerequisite forbidden')
        if len({ref.revision_id for ref in self.input_revision_refs}) != len(self.input_revision_refs):
            raise ValueError('Distinct immutable input revision references required')
        if self.kind == 'narration':
            valid = (self.target_id == 'production-narration' and self.recipe_id is None
                     and self.resource_section == 'narration' and self.output_roles == ('narration_audio',)
                     and self.component_output_key == 'narration_audio' and not self.prerequisite_target_ids)
        elif self.kind == 'shot_clip':
            valid = (len(self.shot_ids) == 1 and self.target_id == 'production-' + self.shot_ids[0]
                     and self.recipe_id is None and self.resource_section == 'picture'
                     and self.output_roles == ('shot_clip',) and self.component_output_key == self.shot_ids[0]
                     and not self.prerequisite_target_ids)
        else:
            expected = {'ambient-remix-v1': ('video', 'mixed_audio', 'cover'),
                        'visual-preserve-mix-v1': ('video', 'cover'),
                        'audio-remix-preserved-clips-v1': ('video', 'mixed_audio'),
                        'cover-from-preserved-video-v1': ('cover',)}.get(self.recipe_id)
            valid = (self.recipe_id is not None and self.target_id == 'production-edit.' + self.recipe_id
                     and self.resource_section == 'edit' and self.output_roles == expected
                     and self.component_output_key == ','.join(expected or ()))
        if not valid:
            raise ValueError('Explicit finite original component shape required')
        return self


class PlanRepairRecipeV1(FinalModel):
    format: Literal['current-plan-repair-recipe-v1']
    recipe_id: RecipeId
    implementation_version: str = Field(min_length=1, max_length=300)
    producer_source_refs: tuple[RecipeSourceRef, ...] = Field(min_length=1)
    component_target_ids: tuple[c.Identifier, ...] = Field(min_length=1)
    routes: tuple[RecipeRouteRef, ...] = Field(min_length=1)
    frame_source: Literal['first_frame_of_new_video', 'first_frame_of_preserved_video']
    clip_audio_mode: Literal['ambient_consumed', 'ambient_ignored']
    narration_mode: Literal['optional_registered_narration', 'preserved_narration_only']
    mixed_audio_mode: Literal['remix_actual_inputs', 'preserve_parent_bytes']
    allowed_output_variants: tuple[tuple[MediaRole, ...], ...] = Field(min_length=1)

    @model_validator(mode='after')
    def fixed_profile(self):
        rules = {
            'ambient-remix-v1': ('first_frame_of_new_video', 'ambient_consumed', 'optional_registered_narration', 'remix_actual_inputs',
                (('video', 'mixed_audio'), ('video', 'mixed_audio', 'cover'), ('video', 'narration_audio', 'mixed_audio'), ('video', 'narration_audio', 'mixed_audio', 'cover'))),
            'visual-preserve-mix-v1': ('first_frame_of_new_video', 'ambient_ignored', 'preserved_narration_only', 'preserve_parent_bytes',
                (('video',), ('video', 'cover'))),
            'audio-remix-preserved-clips-v1': ('first_frame_of_preserved_video', 'ambient_consumed', 'optional_registered_narration', 'remix_actual_inputs',
                (('video', 'mixed_audio'), ('video', 'narration_audio', 'mixed_audio'))),
            'cover-from-preserved-video-v1': ('first_frame_of_preserved_video', 'ambient_ignored', 'preserved_narration_only', 'preserve_parent_bytes', (('cover',),)),
        }
        actual = (self.frame_source, self.clip_audio_mode, self.narration_mode, self.mixed_audio_mode, self.allowed_output_variants)
        if actual != rules[self.recipe_id]:
            raise ValueError('Fixed profile and exact ordered output variants required')
        for values in (self.component_target_ids, tuple(ref.resource_name for ref in self.producer_source_refs),
                       tuple(ref.route_id for ref in self.routes)):
            if len(set(values)) != len(values):
                raise ValueError('Distinct original targets, source names and routes required')
        if self.component_target_ids[-1] != 'production-edit.' + self.recipe_id:
            raise ValueError('Recipe retains its sole original edit target last')
        return self


class PlanRepairTargetsV2(FinalModel):
    format: Literal['current-plan-repair-targets-v2']
    binding: ProductionBinding
    resource_manifest_sha256: c.Sha256
    runtime_manifest_sha256: c.Sha256
    script_ref: PlanRepairRevisionRef
    storyboard_ref: PlanRepairRevisionRef
    rights_declaration_sha256: c.Sha256
    allowed_action: Literal['regenerate_affected_media']
    max_revision_cycles: int = Field(ge=0, strict=True)
    component_targets: tuple[PlanRepairComponentTargetV1, ...] = Field(min_length=1)
    recipes: tuple[PlanRepairRecipeV1, ...] = Field(min_length=1, max_length=4)

    @model_validator(mode='after')
    def finite_graph(self):
        ids = tuple(value.target_id for value in self.component_targets)
        recipes = tuple(value.recipe_id for value in self.recipes)
        if len(set(ids)) != len(ids) or len(set(recipes)) != len(recipes) or self.script_ref.revision_id == self.storyboard_ref.revision_id:
            raise ValueError('Distinct finite targets, recipes and two source revisions required')
        if (self.component_targets[0].kind != 'narration'
                or sum(target.kind == 'narration' for target in self.component_targets) != 1):
            raise ValueError('The finite original component catalog starts with its sole narration')
        edit_seen = False
        refs = {self.script_ref.revision_id: self.script_ref.content_sha256,
                self.storyboard_ref.revision_id: self.storyboard_ref.content_sha256}
        seen = set()
        indexed = {target.target_id: target for target in self.component_targets}
        for target in self.component_targets:
            if target.kind == 'edit':
                edit_seen = True
            elif edit_seen:
                raise ValueError('Original narration and storyboard clips precede all recipe edits')
            if any(ref not in seen for ref in target.prerequisite_target_ids):
                raise ValueError('Only preceding original dependencies are valid')
            if any(refs.get(ref.revision_id) != ref.content_sha256 for ref in target.input_revision_refs):
                raise ValueError('Exact original source revisions required')
            seen.add(target.target_id)
        for recipe in self.recipes:
            selected = recipe.component_target_ids
            if recipe.recipe_id == 'ambient-remix-v1' and selected != tuple(
                    target.target_id for target in self.component_targets if target.kind != 'edit') + ('production-edit.ambient-remix-v1',):
                raise ValueError('Initial ambient catalog requires original narration and every ordered clip before its sole edit')
            if (any(value not in indexed for value in selected)
                    or selected != tuple(value for value in ids if value in selected)):
                raise ValueError('Recipe uses finite original ordered components')
            route_refs = {value.route_id: value.route_sha256 for value in recipe.routes}
            for identifier in selected:
                target = indexed[identifier]
                if route_refs.get(target.route_id) != target.route_sha256:
                    raise ValueError('Every component binds an actual recipe route')
                if target.kind == 'edit' and target.recipe_id != recipe.recipe_id:
                    raise ValueError('Exactly one matching edit component required')
                if (recipe.recipe_id in {'audio-remix-preserved-clips-v1', 'cover-from-preserved-video-v1'} and target.kind == 'shot_clip'
                        or recipe.narration_mode == 'preserved_narration_only' and target.kind == 'narration'):
                    raise ValueError('Preserved inputs cannot become generation components')
        if set(target.recipe_id for target in self.component_targets if target.kind == 'edit') != set(recipes):
            raise ValueError('Catalog and edit graph agree exactly')
        if len(self.component_targets) - sum(target.kind != 'edit' for target in self.component_targets) != len(recipes):
            raise ValueError('One and only one original edit target per recipe required')
        return self


class ProductionDriverResourcesV3(ProductionDriverResourcesV2):
    format: Literal['registered-production-driver-resources-v3']
    recipes: tuple[PlanRepairRecipeV1, ...] = Field(min_length=1, max_length=4)

    @model_validator(mode='after')
    def distinct_catalog(self):
        ids = tuple(value.recipe_id for value in self.recipes)
        if len(set(ids)) != len(ids):
            raise ValueError('Distinct finite installed recipe catalog required')
        return self


class RegisteredProductionPlanV3(FinalModel):
    format: Literal['registered-production-plan-v3']
    proposal: c.CreativeProposal
    rights_proposal: ProductionRightsProposal
    rights: tuple[c.RightsSnapshot, ...]
    timeline_duration_us: int = Field(gt=0, strict=True)
    workflow_candidate: Literal['crewai-flow-production-v1']
    initial_recipe_id: Literal['ambient-remix-v1']
    repair_targets: PlanRepairTargetsV2

    @model_validator(mode='after')
    def original_rights(self):
        if (self.rights != self.rights_proposal.rights
                or self.rights_proposal.declaration_sha256 != self.repair_targets.rights_declaration_sha256
                or self.rights_proposal.run_id != self.repair_targets.binding.run_id
                or self.rights_proposal.request_sha256 != self.repair_targets.binding.request_sha256
                or self.rights_proposal.registration_sha256 != self.repair_targets.binding.registration_sha256
                or self.initial_recipe_id not in {value.recipe_id for value in self.repair_targets.recipes}):
            raise ValueError('Initial recipe and exact original request rights declaration required')
        clips = tuple(target for target in self.repair_targets.component_targets if target.kind == 'shot_clip')
        if (tuple(target.shot_ids[0] for target in clips) != tuple(shot.shot_id for shot in self.proposal.shots)
                or self.timeline_duration_us != sum(shot.duration_us for shot in self.proposal.shots)):
            raise ValueError('Whole plan keeps the exact original ordered shots and duration')
        start = 0
        for target, shot in zip(clips, self.proposal.shots, strict=True):
            if (target.timeline_range.start_us, target.timeline_range.end_us) != (start, start + shot.duration_us):
                raise ValueError('Original half-open storyboard clock required')
            start += shot.duration_us
        c.reject_secrets(self.model_dump(mode='json'))
        return self


class AffectedRepairProposalV2(FinalModel):
    format: Literal['current-affected-repair-proposal-v2']
    parent_preparation_id: c.Identifier
    affected_artifact_ids: tuple[c.Identifier, ...] = Field(min_length=1)
    failed_unit_ids: tuple[c.Identifier, ...]
    requested_action: Literal['regenerate_affected_media']
    changed_media_roles: tuple[MediaRole, ...] = Field(min_length=1)
    impacted_shot_ids: tuple[c.Identifier, ...]
    regenerated_shot_ids: tuple[c.Identifier, ...]
    recipe_id: RecipeId
    projection_sha256: c.Sha256
    recipe_binding_sha256: c.Sha256
    component_target_ids: tuple[c.Identifier, ...] = Field(min_length=1)

    @model_validator(mode='after')
    def distinct_data(self):
        for values in (self.affected_artifact_ids, self.failed_unit_ids, self.changed_media_roles,
                       self.impacted_shot_ids, self.regenerated_shot_ids, self.component_target_ids):
            if len(set(values)) != len(values):
                raise ValueError('Distinct finite proposal members required')
        if (tuple(role for role in ROLE_ORDER if role in self.changed_media_roles) != self.changed_media_roles
                or not set(self.regenerated_shot_ids) <= set(self.impacted_shot_ids)):
            raise ValueError('Ordered exact roles and authentic impacted shot subset required')
        return self


@dataclass(frozen=True, eq=False)
class AffectedRepairExecutionV2:
    binding: ProductionBinding
    execution_fence: int
    parent_preparation_id: str
    parent_intent_sha256: str
    repair_command_sha256: str
    source_report_ref: MaterialReceipt
    affected_artifact_ids: tuple[str, ...]
    failed_unit_ids: tuple[str, ...]
    requested_action: Literal['regenerate_affected_media']
    changed_media_roles: tuple[MediaRole, ...]
    impacted_shot_ids: tuple[str, ...]
    regenerated_shot_ids: tuple[str, ...]
    recipe_id: RecipeId
    projection_sha256: str
    recipe_binding_sha256: str
    component_target_ids: tuple[str, ...]


@dataclass(frozen=True, eq=False)
class AffectedRepairReadSetV2:
    execution: AffectedRepairExecutionV2
    parent: CurrentFinalEvidenceReadSet
    child: CurrentFinalEvidenceReadSet | None
    masters: AffectedMasterObservation | None


def parse_registered_recipe_plan(value):
    """One explicit plan version dispatcher, never an approval parser."""
    from video_creator.domain.errors import EngineError
    from video_creator.domain.plan_repair_targets import RegisteredProductionPlanV2
    from pydantic import ValidationError
    if not isinstance(value, dict):
        raise EngineError('plan_repair_body_invalid', 'Typed finite registered plan object required', 422)
    version = value.get('format')
    if type(version) is not str:
        raise EngineError('plan_repair_body_invalid', 'Registered plan format must be an exact string', 422)
    model = {'registered-production-plan-v2': RegisteredProductionPlanV2,
             'registered-production-plan-v3': RegisteredProductionPlanV3}.get(version)
    if model is None:
        raise EngineError('plan_repair_body_invalid', 'Unknown registered plan version', 422)
    try:
        return model.model_validate(value)
    except (ValidationError, ValueError, TypeError):
        raise EngineError('plan_repair_body_invalid', 'Strict exact registered plan body required', 422) from None


def parse_production_recipe_resources(value):
    """Sole strict resource grammar. Declared data does not qualify installation."""
    from video_creator.domain.errors import EngineError
    from pydantic import ValidationError
    from video_creator.domain.component_diagnosis import ProductionDriverResourcesDiagnosticV1
    if not isinstance(value, dict):
        raise EngineError('production_resource_invalid', 'Finite original resource object required', 503)
    version = value.get('format')
    if type(version) is not str:
        raise EngineError('production_resource_invalid', 'Production resource format must be an exact string', 503)
    model = {'registered-production-driver-resources-v3-diagnostic-v1': ProductionDriverResourcesDiagnosticV1,
             'registered-production-driver-resources-v2': ProductionDriverResourcesV2,
             'registered-production-driver-resources-v3': ProductionDriverResourcesV3}.get(version)
    if model is None:
        raise EngineError('production_resource_invalid', 'Unknown production resource version', 503)
    try:
        if model is ProductionDriverResourcesDiagnosticV1:
            from video_creator.domain.plan_repair_targets import plan_payload_bytes
            return model.model_validate_json(plan_payload_bytes(value))
        return model.model_validate(value)
    except (ValidationError, ValueError, TypeError):
        raise EngineError('production_resource_invalid', 'Strict complete production resource body required', 503) from None
