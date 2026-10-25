"""Distinct Owner production authorization; never an alignment qualification."""

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from video_creator.domain import contracts as c

AUTHORIZATION_VERSION = '0.1.0-candidate'


def _body_sha256(model):
    data = json.dumps(model.model_dump(mode='json'), ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')
    return hashlib.sha256(data).hexdigest()


class ProductionPolicyRef(c.Contract):
    policy_id: c.Identifier
    revision: int = Field(gt=0, strict=True)
    content_sha256: c.Sha256


class AuthorizationActionRef(c.Contract):
    action_id: c.Identifier
    content_sha256: c.Sha256


class ProductionAdmissionRef(c.Contract):
    admission_id: c.Identifier
    content_sha256: c.Sha256


class PolicyInputAsset(c.Contract):
    asset_id: c.Identifier
    sha256: c.Sha256


class PolicySourceScope(c.Contract):
    system: c.Identifier
    namespace: c.Identifier
    executing_principal_ids: tuple[c.Identifier, ...]
    require_article_revision: bool = True
    require_topic_revision: bool = True

    @model_validator(mode='after')
    def finite_principals(self):
        if not self.executing_principal_ids or len(set(self.executing_principal_ids)) != len(self.executing_principal_ids):
            raise ValueError('Source scope requires distinct explicit principals')
        return self


class PolicyRouteBinding(c.Contract):
    route_id: c.Identifier
    route_sha256: c.Sha256
    cost_rule_version: c.Identifier
    source: Literal['owned_local', 'owned_remote', 'official']
    max_operation_cost: c.Money


class ProductionAuthorizationPolicy(c.Contract):
    kind: Literal['production_authorization_policy'] = 'production_authorization_policy'
    version: Literal['0.1.0-candidate'] = AUTHORIZATION_VERSION
    instance_id: c.Identifier
    owner_subject: c.Identifier
    executing_principal_ids: tuple[c.Identifier, ...]
    project_ids: tuple[c.Identifier, ...]
    registration_sha256: c.Sha256
    resource_manifest_sha256: c.Sha256
    runtime_manifest_sha256: c.Sha256
    workflow_version: Literal['registered-media-bundle-v1']
    driver_profile: Literal['registered-production-drivers-v1']
    valid_from_us: int = Field(gt=0, le=9_223_372_036_854_775_807, strict=True)
    expires_at_us: int = Field(gt=0, le=9_223_372_036_854_775_807, strict=True)
    languages: tuple[str, ...]
    aspect_ratios: tuple[Literal['9:16', '16:9'], ...]
    max_duration_us: int = Field(gt=0, le=600_000_000, strict=True)
    output_profile: Literal['video-audio-text-rag-eight-v1']
    delivery_modes: tuple[Literal['export', 'reference'], ...]
    allowed_actions: tuple[Literal['begin_execution', 'execute_plan',
                                   'continue_bundle_validation', 'finalize_bundle'], ...]
    input_assets: tuple[PolicyInputAsset, ...] = ()
    allowed_sources: tuple[PolicySourceScope, ...] = ()
    caller_supplied_text_allowed: bool = False
    routes: tuple[PolicyRouteBinding, ...]
    external_transfer_allowed: bool = False
    max_production_cost: c.Money
    budget_group_id: c.Identifier | None = None
    budget_group_identity_sha256: c.Sha256 | None = None
    max_revision_cycles: int = Field(ge=0, le=2, strict=True)
    alignment_modes: tuple[Literal['strict_reference_v1', 'qualified_method_runtime_v1'], ...]
    rights_declaration_id: c.Identifier
    rights: tuple[c.RightsSnapshot, ...]
    required_quality_checks: tuple[Literal['media_integrity', 'audio_timeline', 'actual_transcript',
                                         'alignment', 'subtitles', 'semantic_sources', 'rights'], ...]

    @model_validator(mode='after')
    def finite_scope(self):
        for values in (self.executing_principal_ids, self.project_ids, self.languages,
                       self.aspect_ratios, self.delivery_modes, self.allowed_actions, self.alignment_modes,
                       self.required_quality_checks):
            if not values or len(set(values)) != len(values):
                raise ValueError('Policy scope requires distinct explicit finite values')
        if self.expires_at_us <= self.valid_from_us:
            raise ValueError('Policy validity must be a finite increasing interval')
        if any(not language or len(language) > 64 for language in self.languages):
            raise ValueError('Policy languages must be bounded explicit values')
        if not self.routes or len({route.route_id for route in self.routes}) != len(self.routes):
            raise ValueError('Policy routes must be distinct explicit registrations')
        if len({asset.asset_id for asset in self.input_assets}) != len(self.input_assets):
            raise ValueError('Policy input identities cannot repeat')
        if len({(source.system, source.namespace) for source in self.allowed_sources}) != len(self.allowed_sources):
            raise ValueError('Policy source scopes cannot overlap by identity')
        if bool(self.budget_group_id) != bool(self.budget_group_identity_sha256):
            raise ValueError('Existing budget group requires its exact immutable identity')
        if self.max_production_cost.units() and not self.budget_group_id:
            raise ValueError('Paid policy requires the already authorized shared budget group')
        if (not self.rights or len({right.rights_id for right in self.rights}) != len(self.rights)
                or any(right.basis != 'user_asserted' for right in self.rights)):
            raise ValueError('Owner policy only carries explicit user_asserted declarations')
        if any(right.approval_ref != self.rights_declaration_id for right in self.rights):
            raise ValueError('Policy assertion must name its exact Owner declaration identifier')
        if set(self.required_quality_checks) != {'media_integrity', 'audio_timeline', 'actual_transcript',
                                              'alignment', 'subtitles', 'semantic_sources', 'rights'}:
            raise ValueError('Policy cannot remove mandatory quality checks')
        c.reject_secrets(self.model_dump(mode='json'))
        return self


class InstallProductionPolicy(c.Contract):
    policy_id: c.Identifier
    policy: ProductionAuthorizationPolicy
    previous_ref: ProductionPolicyRef | None = None


class SelectProductionPolicy(c.Contract):
    policy_ref: ProductionPolicyRef
    project_id: c.Identifier
    executing_principal_id: c.Identifier
    registration_sha256: c.Sha256


class RevokeProductionPolicy(c.Contract):
    policy_ref: ProductionPolicyRef
    reason: str = Field(min_length=1, max_length=2000)


class AuthorizationActionReceipt(c.Contract):
    action_id: c.Identifier
    instance_id: c.Identifier
    administrator_id: c.Identifier
    authentication_binding_id: c.Identifier
    authentication_source: Literal['native_owner_session', 'headless_administrator']
    owner_subject: c.Identifier
    project_ids: tuple[c.Identifier, ...]
    action: Literal['create', 'replace', 'select', 'revoke', 'reauthorize']
    policy_ref: ProductionPolicyRef
    idempotency_key: c.Identifier
    request_sha256: c.Sha256
    authorized_at_us: int = Field(gt=0, strict=True)
    registry_revision: int = Field(gt=0, strict=True)
    reason: str | None = Field(default=None, min_length=1, max_length=2000)
    target_production_id: c.Identifier | None = None
    target_request_revision_id: c.Identifier | None = None
    target_request_sha256: c.Sha256 | None = None

    @model_validator(mode='after')
    def complete_target(self):
        if (self.action == 'revoke') != (self.reason is not None):
            raise ValueError('Only revocation carries its actual management reason')
        if self.action == 'reauthorize':
            if not all((self.target_production_id, self.target_request_revision_id, self.target_request_sha256)):
                raise ValueError('Reauthorization requires the exact existing request target')
        elif any((self.target_production_id, self.target_request_revision_id, self.target_request_sha256)):
            raise ValueError('Only reauthorization has a production target')
        c.reject_secrets(self.model_dump(mode='json'))
        return self


class ProductionPolicyRecord(c.Contract):
    policy_ref: ProductionPolicyRef
    policy: ProductionAuthorizationPolicy
    installation_action: AuthorizationActionReceipt
    current: bool
    revoked: bool
    revocation_action: AuthorizationActionReceipt | None = None

    @model_validator(mode='after')
    def original_action(self):
        action = self.installation_action
        if (self.policy_ref.content_sha256 != _body_sha256(self.policy)
                or action.policy_ref != self.policy_ref or action.action not in {'create', 'replace'}
                or (action.instance_id, action.owner_subject, action.project_ids) != (
                    self.policy.instance_id, self.policy.owner_subject, self.policy.project_ids)
                or self.revoked != (self.revocation_action is not None)):
            raise ValueError('Policy record requires its exact original Owner action and body identity')
        if self.revocation_action is not None and (self.revocation_action.action != 'revoke'
                or self.revocation_action.policy_ref != self.policy_ref
                or self.revocation_action.instance_id != self.policy.instance_id
                or self.revocation_action.owner_subject != self.policy.owner_subject):
            raise ValueError('Revocation must target the original exact instance policy')
        return self


class ProductionAdmissionFact(c.Contract):
    """Private current-fence fact; callers cannot submit this as permission."""
    admission_id: c.Identifier
    instance_id: c.Identifier
    production_id: c.Identifier
    run_id: c.Identifier
    request_revision_id: c.Identifier
    request_sha256: c.Sha256
    executing_principal_id: c.Identifier
    registration_sha256: c.Sha256
    resource_manifest_sha256: c.Sha256
    runtime_manifest_sha256: c.Sha256
    phase: Literal['request', 'plan', 'quality']
    action: Literal['bind_request', 'begin_execution', 'execute_plan',
                    'continue_bundle_validation', 'finalize_bundle']
    target_kind: Literal['request', 'creative_revision', 'final_manifest']
    target_id: c.Identifier
    target_sha256: c.Sha256
    policy_ref: ProductionPolicyRef
    owner_action_ref: AuthorizationActionRef
    rights_declaration_sha256: c.Sha256
    registry_revision: int = Field(gt=0, strict=True)
    checked_at_us: int = Field(gt=0, strict=True)
    valid_until_us: int = Field(gt=0, strict=True)
    fencing_token: int | None = Field(default=None, gt=0, strict=True)

    @model_validator(mode='after')
    def phase_target(self):
        phases = {'bind_request': ('request', 'request'), 'begin_execution': ('request', 'request'),
            'execute_plan': ('plan', 'creative_revision'),
            'continue_bundle_validation': ('quality', 'creative_revision'),
            'finalize_bundle': ('quality', 'final_manifest')}
        if phases[self.action] != (self.phase, self.target_kind):
            raise ValueError('Admission action must match its actual target phase')
        if (self.action == 'bind_request') != (self.fencing_token is None):
            raise ValueError('Only request binding has no execution fence')
        if self.valid_until_us <= self.checked_at_us:
            raise ValueError('Admission is not currently valid')
        if self.phase == 'request' and (self.target_id, self.target_sha256) != (
                self.request_revision_id, self.request_sha256):
            raise ValueError('Request fact cannot bind a different request target')
        c.reject_secrets(self.model_dump(mode='json'))
        return self


class CurrentProductionAdmission(c.Contract):
    """Typed human/policy branches; bind_request is never an execution permit."""
    state: Literal['allowed', 'waiting_user', 'waiting_authorization', 'denied', 'resource_not_ready']
    phase: Literal['request', 'plan', 'quality']
    action: Literal['begin_execution', 'execute_plan', 'continue_bundle_validation', 'finalize_bundle']
    instance_id: c.Identifier
    production_id: c.Identifier
    run_id: c.Identifier
    request_revision_id: c.Identifier
    request_sha256: c.Sha256
    registration_sha256: c.Sha256
    target_id: c.Identifier
    target_sha256: c.Sha256
    fencing_token: int = Field(gt=0, strict=True)
    checked_at_us: int = Field(gt=0, strict=True)
    valid_until_us: int | None = Field(default=None, gt=0, strict=True)
    source: Literal['human_review', 'owner_policy', 'delegated_project'] | None = None
    human_approval_ref: c.ApprovalRef | None = None
    policy_ref: ProductionPolicyRef | None = None
    owner_action_ref: AuthorizationActionRef | None = None
    admission_ref: ProductionAdmissionRef | None = None
    blocker_code: c.Identifier | None = None

    @model_validator(mode='after')
    def real_source_branch(self):
        expected_phase = {'begin_execution': 'request', 'execute_plan': 'plan',
                          'continue_bundle_validation': 'quality', 'finalize_bundle': 'quality'}
        if expected_phase[self.action] != self.phase:
            raise ValueError('Current action must match its actual production phase')
        if self.state != 'allowed':
            if any((self.source, self.human_approval_ref, self.policy_ref, self.owner_action_ref, self.admission_ref)):
                raise ValueError('An unavailable admission has no approval source')
            return self
        if self.valid_until_us is None or self.valid_until_us <= self.checked_at_us or self.blocker_code:
            raise ValueError('Allowed admission needs an actual current validity interval')
        if self.source == 'human_review':
            if (self.phase == 'request' or not self.human_approval_ref
                    or any((self.policy_ref, self.owner_action_ref, self.admission_ref))):
                raise ValueError('Human branch requires only the real version approval')
            if self.human_approval_ref.run_id != self.run_id or (self.action != 'finalize_bundle'
                    and self.human_approval_ref.target_revision_id != self.target_id):
                raise ValueError('Human approval must name the actual sameRun creative target')
        elif self.source in ('owner_policy', 'delegated_project'):
            if not all((self.policy_ref, self.owner_action_ref, self.admission_ref)) or self.human_approval_ref:
                raise ValueError('Policy branch needs actual policy/action/admission, not a fake human approval')
        else:
            raise ValueError('Allowed admission requires a known real source')
        return self


class ProductionRightsFact(c.Contract):
    instance_id: c.Identifier
    production_id: c.Identifier
    run_id: c.Identifier
    request_revision_id: c.Identifier
    request_sha256: c.Sha256
    plan_revision_id: c.Identifier
    declaring_subject: c.Identifier
    declaration_id: c.Identifier
    declaration_sha256: c.Sha256
    rights: tuple[c.RightsSnapshot, ...]
    source: Literal['human_review', 'owner_policy', 'delegated_project']
    human_approval_ref: c.ApprovalRef | None = None
    policy_ref: ProductionPolicyRef | None = None
    owner_action_ref: AuthorizationActionRef | None = None
    fencing_token: int = Field(gt=0, strict=True)
    checked_at_us: int = Field(gt=0, strict=True)
    valid_until_us: int = Field(gt=0, strict=True)

    @model_validator(mode='after')
    def assertion_origin(self):
        if not self.rights or any(right.basis != 'user_asserted' for right in self.rights):
            raise ValueError('Owner assertion is not independent owned/licensed authority')
        if self.source == 'human_review':
            if not self.human_approval_ref or self.policy_ref or self.owner_action_ref:
                raise ValueError('Human assertion requires the actual human approval')
            if (self.human_approval_ref.run_id, self.human_approval_ref.target_revision_id) != (
                    self.run_id, self.plan_revision_id):
                raise ValueError('Human declaration requires the sameRun actual plan approval')
        elif not self.policy_ref or not self.owner_action_ref or self.human_approval_ref:
            raise ValueError('Owner assertion requires its real installed action and policy')
        if self.valid_until_us <= self.checked_at_us:
            raise ValueError('Rights assertion must be current')
        return self


class ProductionAuthorizationDocument(c.Contract):
    """Portable provenance, never a foreign instance ticket or policy installer."""
    kind: Literal['production_authorization'] = 'production_authorization'
    version: Literal['0.1.0-candidate'] = AUTHORIZATION_VERSION
    document_id: c.Identifier
    policy_ref: ProductionPolicyRef
    policy: ProductionAuthorizationPolicy
    owner_action: AuthorizationActionReceipt
    plan_admission: ProductionAdmissionFact

    @model_validator(mode='after')
    def no_future_target(self):
        if (self.owner_action.policy_ref != self.policy_ref or self.plan_admission.policy_ref != self.policy_ref
                or self.plan_admission.action != 'execute_plan' or self.plan_admission.fencing_token is None
                or self.policy.instance_id != self.owner_action.instance_id
                or self.policy.instance_id != self.plan_admission.instance_id):
            raise ValueError('Authorization provenance must bind the actual earlier Owner action and plan')
        if (self.policy_ref.content_sha256 != _body_sha256(self.policy)
                or self.owner_action.owner_subject != self.policy.owner_subject
                or self.owner_action.project_ids != self.policy.project_ids
                or self.owner_action.action not in {'create', 'replace'}
                or self.plan_admission.owner_action_ref.action_id != self.owner_action.action_id
                or self.plan_admission.owner_action_ref.content_sha256 != _body_sha256(self.owner_action)
                or self.plan_admission.registration_sha256 != self.policy.registration_sha256
                or self.plan_admission.resource_manifest_sha256 != self.policy.resource_manifest_sha256
                or self.plan_admission.runtime_manifest_sha256 != self.policy.runtime_manifest_sha256
                or self.plan_admission.valid_until_us > self.policy.expires_at_us):
            raise ValueError('Authorization provenance requires actual complete policy/action/resource identities')
        c.reject_secrets(self.model_dump(mode='json'))
        return self
