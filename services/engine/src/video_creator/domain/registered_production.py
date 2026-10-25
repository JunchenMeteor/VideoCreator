"""Private registered production ports; never HTTP or model-owned permissions."""
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from video_creator.domain import contracts as c
from video_creator.domain.production_authorization import AuthorizationActionRef, ProductionPolicyRef

PROFILE = 'registered-media-bundle-v1'


class PrivateModel(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)


class ProductionBinding(PrivateModel):
    # The existing serialized B12 binding fields/defaults are unchanged.
    workflow_version: Literal['registered-media-bundle-v1'] = PROFILE
    instance_id: c.Identifier
    production_id: c.Identifier
    run_id: c.Identifier
    request_revision_id: c.Identifier
    request_sha256: c.Sha256
    registration_sha256: c.Sha256
    input_assets: tuple[tuple[c.Identifier, c.Sha256], ...]


class ProductionRightsDeclaration(PrivateModel):
    format: Literal['owner-production-rights-v1']
    declaration_id: c.Identifier
    declaring_subject: c.Identifier
    project_ids: tuple[c.Identifier, ...]
    expires_at_us: int | None = Field(gt=0, strict=True)
    rights: tuple[c.RightsSnapshot, ...]

    @model_validator(mode='after')
    def scope(self):
        if (not self.project_ids or len(set(self.project_ids)) != len(self.project_ids)
                or not self.rights or len({right.rights_id for right in self.rights}) != len(self.rights)):
            raise ValueError('Current declaration requires distinct explicit project and rights scope')
        # A trusted launcher can carry an Owner assertion; it cannot install a
        # legal owned/licensed authority by writing this JSON configuration.
        if any(right.basis != 'user_asserted' for right in self.rights):
            raise ValueError('Owned/licensed authority is not admitted by an Owner declaration')
        c.reject_secrets(self.model_dump(mode='json'))
        return self


class AutonomousRegistration(PrivateModel):
    format: Literal['registered-autonomous-production-v1']
    text_route_id: c.Identifier
    narration_route_id: c.Identifier
    picture_route_id: c.Identifier
    edit_route_id: c.Identifier
    master_index_route_id: c.Identifier
    driver_profile: Literal['registered-production-drivers-v1']
    rights_declaration: ProductionRightsDeclaration
    max_duration_us: int = Field(default=60_000_000, gt=0, le=600_000_000, strict=True)


class ProductionRightsProposal(PrivateModel):
    """Request-bound declaration only; never plan admission or execution power."""
    model_config = ConfigDict(extra='forbid', frozen=True, strict=True)
    format: Literal['production-rights-proposal-v1']
    instance_id: c.Identifier
    production_id: c.Identifier
    run_id: c.Identifier
    request_revision_id: c.Identifier
    project_id: c.Identifier
    request_sha256: c.Sha256
    registration_sha256: c.Sha256
    declaring_subject: c.Identifier
    declaration_id: c.Identifier
    declaration_sha256: c.Sha256
    rights: tuple[c.RightsSnapshot, ...]
    source: Literal['owner_declaration', 'owner_policy', 'delegated_project']
    policy_ref: ProductionPolicyRef | None = None
    owner_action_ref: AuthorizationActionRef | None = None
    fencing_token: int = Field(gt=0, strict=True)
    checked_at_us: int = Field(gt=0, strict=True)
    valid_until_us: int = Field(gt=0, strict=True)

    @model_validator(mode='after')
    def declaration_only(self):
        if (not self.rights or len({right.rights_id for right in self.rights}) != len(self.rights)
                or any(right.basis != 'user_asserted' for right in self.rights)
                or self.valid_until_us <= self.checked_at_us):
            raise ValueError('Proposal needs unique current Owner assertions, not independent legal authority')
        if self.source == 'owner_declaration':
            if self.policy_ref is not None or self.owner_action_ref is not None:
                raise ValueError('An installed Owner declaration does not grant a policy action')
        elif self.policy_ref is None or self.owner_action_ref is None:
            raise ValueError('Policy proposal must retain its real installed policy and Owner action')
        c.reject_secrets(self.model_dump(mode='json'))
        return self


class CurrentProductionUpstreamResult(PrivateModel):
    """Trusted same-Run result, never a provider-owned success declaration."""
    model_config = ConfigDict(extra='forbid', frozen=True, strict=True)
    run_id: c.Identifier
    fencing_token: int = Field(gt=0, strict=True)
    state: Literal['masters_ready', 'waiting_user', 'waiting_authorization', 'resource_not_ready',
                   'denied', 'needs_reconciliation']
    media_roles: dict[str, c.Identifier]
    blocker_code: c.Identifier | None = None

    @model_validator(mode='after')
    def actual_masters_only(self):
        if self.state == 'masters_ready':
            if (set(self.media_roles) != {'video', 'narration_audio', 'mixed_audio', 'cover'}
                    or len(set(self.media_roles.values())) != 4 or self.blocker_code is not None):
                raise ValueError('Only four distinct original masters without a blocker can be ready')
        elif self.media_roles:
            raise ValueError('A blocked upstream cannot claim master assets')
        c.reject_secrets(self.model_dump(mode='json'))
        return self


class CurrentProductionBlockerJournal(PrivateModel):
    """Private progress record; never a permission or executable receipt."""
    model_config = ConfigDict(extra='forbid', frozen=True, strict=True)
    format: Literal['current-production-blocker-v1']
    binding: ProductionBinding
    result: CurrentProductionUpstreamResult
    blocked_at_us: int = Field(gt=0, strict=True)

    @model_validator(mode='after')
    def real_wait(self):
        if (self.result.state not in {'waiting_authorization', 'resource_not_ready'}
                or self.result.media_roles or not self.result.blocker_code
                or self.result.run_id != self.binding.run_id):
            raise ValueError('Only an exact same-Run actual resource/authorization wait can be journalled')
        return self


@dataclass(frozen=True)
class ProductionDriverBuilders:
    narration: Callable
    picture: Callable
    edit: Callable


@dataclass(frozen=True)
class ProductionAdmission:
    state: Literal['allowed', 'waiting_user', 'denied', 'authority_not_ready']
    revision_id: str
    revision_sha256: str
    phase: Literal['plan', 'quality']
    approval_ref: c.ApprovalRef | None = None
    blocker_code: str | None = None


class AsrResultAllocation(PrivateModel):
    format: Literal['registered-asr-result-allocation-v1'] = 'registered-asr-result-allocation-v1'
    operation_id: c.Identifier
    run_id: c.Identifier
    step_key: c.Identifier
    input_sha256: c.Sha256
    dedupe_key: c.Identifier
    route_sha256: c.Sha256
    attempt_id: c.Identifier
    staging_id: c.Identifier
    binding_sha256: c.Sha256
    resource_manifest_sha256: c.Sha256
    runtime_manifest_sha256: c.Sha256


@dataclass(frozen=True)
class AsrResultHandle:
    allocation: AsrResultAllocation
    completed_path: Path


class StoredAsrObservation(PrivateModel):
    format: Literal['registered-asr-observation-v1'] = 'registered-asr-observation-v1'
    allocation: AsrResultAllocation
    observation: c.OperationObservation


class RegisteredReconciliation(PrivateModel):
    format: Literal['registered-asr-reconciliation-v1'] = 'registered-asr-reconciliation-v1'
    lease: c.LeaseGrant
    binding: ProductionBinding
    operation_ids: tuple[c.Identifier, ...]
