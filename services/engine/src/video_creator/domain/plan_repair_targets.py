"""Finite original plan data; serializing it never grants execution authority."""

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from video_creator.domain import contracts as c
from video_creator.domain.current_final_evidence import FinalModel
from video_creator.domain.registered_production import ProductionBinding, ProductionRightsProposal


def plan_payload_bytes(value):
    """New recursive JSON identities, independent of the original Goal encoder."""
    if hasattr(value, 'model_dump'):
        value = value.model_dump(mode='json')
    c.reject_secrets(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def plan_payload_sha256(value):
    return hashlib.sha256(plan_payload_bytes(value)).hexdigest()


class PlanRepairRevisionRef(FinalModel):
    revision_id: c.Identifier
    content_sha256: c.Sha256


class PlanRepairTarget(FinalModel):
    target_id: c.Identifier
    kind: Literal['narration', 'shot_clip', 'edit']
    shot_ids: tuple[c.Identifier, ...]
    timeline_range: c.MediaRange
    route_id: c.Identifier
    route_sha256: c.Sha256
    resource_section: Literal['narration', 'picture', 'edit']
    resource_section_sha256: c.Sha256
    input_revision_refs: tuple[PlanRepairRevisionRef, ...] = Field(min_length=1)
    input_payload_sha256: c.Sha256
    prerequisite_target_ids: tuple[c.Identifier, ...]
    output_roles: tuple[Literal['narration_audio', 'shot_clip', 'video', 'mixed_audio', 'cover'], ...] = Field(min_length=1)
    dependent_media_roles: tuple[Literal['video', 'narration_audio', 'mixed_audio', 'cover'], ...] = Field(min_length=1)

    @model_validator(mode='after')
    def original_component_shape(self):
        for values in (self.shot_ids, self.prerequisite_target_ids, self.output_roles, self.dependent_media_roles):
            if len(set(values)) != len(values):
                raise ValueError('Finite target arrays contain distinct original members')
        refs = tuple(ref.revision_id for ref in self.input_revision_refs)
        if len(set(refs)) != len(refs) or self.target_id in self.prerequisite_target_ids:
            raise ValueError('Distinct source revisions and nonrecursive prerequisites required')
        if self.kind == 'narration':
            if (self.target_id != 'production-narration' or self.resource_section != 'narration'
                    or self.output_roles != ('narration_audio',) or self.prerequisite_target_ids):
                raise ValueError('Original narration component required')
        elif self.kind == 'shot_clip':
            if (len(self.shot_ids) != 1 or self.target_id != 'production-' + self.shot_ids[0]
                    or self.resource_section != 'picture' or self.output_roles != ('shot_clip',)
                    or self.prerequisite_target_ids):
                raise ValueError('Original shot component required')
        elif (self.target_id != 'production-edit' or self.resource_section != 'edit'
                or any(role not in ('video', 'mixed_audio', 'cover') for role in self.output_roles)
                or not self.prerequisite_target_ids):
            raise ValueError('Original edit component required')
        return self


class PlanRepairTargetsV1(FinalModel):
    format: Literal['current-plan-repair-targets-v1']
    binding: ProductionBinding
    resource_manifest_sha256: c.Sha256
    runtime_manifest_sha256: c.Sha256
    script_ref: PlanRepairRevisionRef
    storyboard_ref: PlanRepairRevisionRef
    rights_declaration_sha256: c.Sha256
    allowed_action: Literal['regenerate_affected_media']
    max_revision_cycles: int = Field(ge=0, strict=True)
    targets: tuple[PlanRepairTarget, ...] = Field(min_length=1)

    @model_validator(mode='after')
    def finite_original_graph(self):
        ids = tuple(target.target_id for target in self.targets)
        if len(set(ids)) != len(ids):
            raise ValueError('A finite plan has distinct original targets')
        if (self.targets[0].kind != 'narration' or self.targets[-1].kind != 'edit'
                or any(target.kind != 'shot_clip' for target in self.targets[1:-1])):
            raise ValueError('Original narration, ordered shots, edit graph required')
        seen = set()
        expected_refs = {self.script_ref.revision_id: self.script_ref.content_sha256,
                         self.storyboard_ref.revision_id: self.storyboard_ref.content_sha256}
        if len(expected_refs) != 2:
            raise ValueError('Script and storyboard are distinct immutable revisions')
        for target in self.targets:
            if any(ref not in seen for ref in target.prerequisite_target_ids):
                raise ValueError('Only preceding original dependencies are valid')
            if any(expected_refs.get(ref.revision_id) != ref.content_sha256 for ref in target.input_revision_refs):
                raise ValueError('Target source references must match the exact original revisions')
            seen.add(target.target_id)
        if self.targets[-1].prerequisite_target_ids != ids[:-1]:
            raise ValueError('Edit depends on the original narration and ordered clips')
        c.reject_secrets(self.model_dump(mode='json'))
        return self


class RegisteredProductionPlanV2(FinalModel):
    format: Literal['registered-production-plan-v2']
    proposal: c.CreativeProposal
    rights_proposal: ProductionRightsProposal
    rights: tuple[c.RightsSnapshot, ...]
    timeline_duration_us: int = Field(gt=0, strict=True)
    workflow_candidate: Literal['crewai-flow-production-v1']
    repair_targets: PlanRepairTargetsV1

    @model_validator(mode='after')
    def same_declared_plan(self):
        if (self.rights != self.rights_proposal.rights
                or self.rights_proposal.declaration_sha256 != self.repair_targets.rights_declaration_sha256
                or self.rights_proposal.run_id != self.repair_targets.binding.run_id
                or self.rights_proposal.request_sha256 != self.repair_targets.binding.request_sha256
                or self.rights_proposal.registration_sha256 != self.repair_targets.binding.registration_sha256):
            raise ValueError('Plan data retains the same real request-bound rights declaration')
        c.reject_secrets(self.model_dump(mode='json'))
        return self
