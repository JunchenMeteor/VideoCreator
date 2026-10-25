"""Bounded real-Owner creation delegation, distinct from old policy actions."""

from typing import Annotated, Literal

from pydantic import ConfigDict, Field, ValidationError, field_validator, model_validator

from video_creator.domain import contracts as c
from video_creator.domain.native_execution_registration import (
    ExecutionRegistrationRef,
    InstalledNativeRecordRef,
)
from video_creator.domain.production_authorization import (
    AuthorizationActionRef,
    PolicyInputAsset,
    PolicyRouteBinding,
    PolicySourceScope,
    ProductionAdmissionFact,
    ProductionAuthorizationPolicy,
    ProductionPolicyRef,
    _body_sha256,
)


class DailyProjectAuthorizationRef(c.Contract):
    authorization_id: c.Identifier
    revision: int = Field(gt=0, strict=True)
    content_sha256: c.Sha256


class ProjectScopeDerivationRef(c.Contract):
    derivation_id: c.Identifier
    content_sha256: c.Sha256


class DailyCreativeTemplate(c.Contract):
    """Complete finite creative scope without unknown future project IDs."""
    registration_sha256: c.Sha256
    resource_manifest_sha256: c.Sha256
    runtime_manifest_sha256: c.Sha256
    workflow_version: Literal['registered-media-bundle-v1']
    driver_profile: Literal['registered-production-drivers-v1']
    valid_from_us: int = Field(gt=0, strict=True)
    expires_at_us: int = Field(gt=0, strict=True)
    languages: tuple[str, ...]
    aspect_ratios: tuple[Literal['9:16', '16:9'], ...]
    max_duration_us: int = Field(gt=0, le=600_000_000, strict=True)
    output_profile: Literal['video-audio-text-rag-eight-v1']
    delivery_modes: tuple[Literal['export', 'reference'], ...]
    allowed_actions: tuple[Literal['begin_execution', 'execute_plan', 'continue_bundle_validation', 'finalize_bundle'], ...]
    input_assets: tuple[PolicyInputAsset, ...]
    allowed_sources: tuple[PolicySourceScope, ...]
    caller_supplied_text_allowed: bool
    routes: tuple[PolicyRouteBinding, ...]
    external_transfer_allowed: bool
    max_production_cost: c.Money
    budget_group_id: c.Identifier | None
    budget_group_identity_sha256: c.Sha256 | None
    max_revision_cycles: int = Field(ge=0, le=2, strict=True)
    alignment_modes: tuple[Literal['strict_reference_v1', 'qualified_method_runtime_v1'], ...]
    rights_declaration_id: c.Identifier
    rights: tuple[c.RightsSnapshot, ...]
    required_quality_checks: tuple[Literal['media_integrity', 'audio_timeline', 'actual_transcript',
        'alignment', 'subtitles', 'semantic_sources', 'rights'], ...]

    @model_validator(mode='after')
    def complete_finite_template(self):
        for values in (self.languages, self.aspect_ratios, self.delivery_modes, self.allowed_actions,
                       self.alignment_modes, self.required_quality_checks):
            if not values or len(set(values)) != len(values):
                raise ValueError('Delegation template requires explicit distinct finite choices')
        if self.expires_at_us <= self.valid_from_us or any(not item or len(item) > 64 for item in self.languages):
            raise ValueError('Delegation template validity/language is invalid')
        if not self.routes or len({item.route_id for item in self.routes}) != len(self.routes):
            raise ValueError('Delegation template requires complete distinct routes')
        if (len({item.asset_id for item in self.input_assets}) != len(self.input_assets)
                or len({(item.system, item.namespace) for item in self.allowed_sources}) != len(self.allowed_sources)):
            raise ValueError('Delegation input/source scope cannot repeat')
        if (bool(self.budget_group_id) != bool(self.budget_group_identity_sha256)
                or self.max_production_cost.units() and not self.budget_group_id):
            raise ValueError('Delegation shares one actual immutable budget group')
        if (not self.rights or len({item.rights_id for item in self.rights}) != len(self.rights)
                or any(item.basis != 'user_asserted' or item.approval_ref != self.rights_declaration_id for item in self.rights)):
            raise ValueError('Delegation assertion cannot replace independent owned/licensed evidence')
        if set(self.required_quality_checks) != {'media_integrity', 'audio_timeline', 'actual_transcript',
                'alignment', 'subtitles', 'semantic_sources', 'rights'}:
            raise ValueError('Delegation cannot remove mandatory quality checks')
        c.reject_secrets(self.model_dump(mode='json'))
        return self


class DailyExecutionRef(c.Contract):
    role: Literal['api', 'mcp', 'worker']
    registration_ref: ExecutionRegistrationRef


class InstallDailyProjectAuthorization(c.Contract):
    authorization_id: c.Identifier
    previous_ref: DailyProjectAuthorizationRef | None = None
    installed_record_ref: InstalledNativeRecordRef
    execution_refs: tuple[DailyExecutionRef, ...]
    allowed_entries: tuple[Literal['api', 'mcp', 'native'], ...]
    expires_at_us: int = Field(gt=0, strict=True)
    max_created_projects: int = Field(gt=0, le=1_000_000, strict=True)
    max_active_productions: int = Field(gt=0, le=100_000, strict=True)
    template: DailyCreativeTemplate

    @model_validator(mode='after')
    def complete_roles(self):
        if (len(self.execution_refs) != 3 or {item.role for item in self.execution_refs} != {'api', 'mcp', 'worker'}
                or not self.allowed_entries or len(set(self.allowed_entries)) != len(self.allowed_entries)
                or self.expires_at_us > self.template.expires_at_us):
            raise ValueError('Creation delegation binds all three actual execution roles and a finite interval')
        return self


class DailyProjectAuthorization(c.Contract):
    format: Literal['daily-project-authorization-v1'] = 'daily-project-authorization-v1'
    authorization_id: c.Identifier
    revision: int = Field(gt=0, strict=True)
    instance_id: c.Identifier
    owner_subject: c.Identifier
    executing_principal_ids: tuple[c.Identifier, ...]
    owner_binding_generation: int = Field(gt=0, strict=True)
    owner_binding_action_id: c.Identifier
    authentication_binding_id: c.Identifier
    installed_record_ref: InstalledNativeRecordRef
    execution_refs: tuple[DailyExecutionRef, ...]
    allowed_entries: tuple[Literal['api', 'mcp', 'native'], ...]
    expires_at_us: int = Field(gt=0, strict=True)
    max_created_projects: int = Field(gt=0, le=1_000_000, strict=True)
    max_active_productions: int = Field(gt=0, le=100_000, strict=True)
    template: DailyCreativeTemplate

    @model_validator(mode='after')
    def exact_owner_template(self):
        if self.executing_principal_ids != (self.owner_subject,):
            raise ValueError('This version delegates only the actual local Owner')
        InstallDailyProjectAuthorization(authorization_id=self.authorization_id,
            installed_record_ref=self.installed_record_ref, execution_refs=self.execution_refs,
            allowed_entries=self.allowed_entries, expires_at_us=self.expires_at_us,
            max_created_projects=self.max_created_projects, max_active_productions=self.max_active_productions,
            template=self.template)
        if any(set(item.executing_principal_ids) != {self.owner_subject} for item in self.template.allowed_sources):
            raise ValueError('Source scope cannot install another execution identity')
        return self


class DailyProjectActionReceipt(c.Contract):
    format: Literal['daily-project-owner-action-v1'] = 'daily-project-owner-action-v1'
    action_id: c.Identifier
    instance_id: c.Identifier
    owner_subject: c.Identifier
    administrator_id: c.Identifier
    authentication_binding_id: c.Identifier
    owner_binding_generation: int = Field(gt=0, strict=True)
    owner_binding_action_id: c.Identifier
    authentication_source: Literal['native_owner_session', 'headless_administrator']
    action: Literal['install', 'replace', 'revoke', 'revoke_child']
    authorization_ref: DailyProjectAuthorizationRef
    derivation_ref: ProjectScopeDerivationRef | None = None
    idempotency_key: c.Identifier
    request_sha256: c.Sha256
    authorized_at_us: int = Field(gt=0, strict=True)
    registry_revision: int = Field(gt=0, strict=True)
    reason: str | None = Field(default=None, min_length=1, max_length=2000)

    @model_validator(mode='after')
    def real_action_target(self):
        if (self.action == 'revoke_child') != (self.derivation_ref is not None):
            raise ValueError('Child revocation requires its exact real child ref')
        if self.action.startswith('revoke') != (self.reason is not None):
            raise ValueError('Revocation requires its actual explicit reason')
        c.reject_secrets(self.model_dump(mode='json'))
        return self


class RevokeDailyProjectAuthorization(c.Contract):
    authorization_ref: DailyProjectAuthorizationRef
    derivation_ref: ProjectScopeDerivationRef | None = None
    reason: str = Field(min_length=1, max_length=2000)

    @model_validator(mode='after')
    def no_secrets(self):
        c.reject_secrets(self.model_dump(mode='json'))
        return self


class DailyProjectAuthorizationRecord(c.Contract):
    authorization_ref: DailyProjectAuthorizationRef
    authorization: DailyProjectAuthorization
    creation_action: DailyProjectActionReceipt
    current: bool
    revoked: bool
    revocation_action: DailyProjectActionReceipt | None = None

    @model_validator(mode='after')
    def actual_creation_origin(self):
        if (self.authorization_ref.content_sha256 != _body_sha256(self.authorization)
                or self.creation_action.authorization_ref != self.authorization_ref
                or self.creation_action.action not in ('install', 'replace')
                or (self.creation_action.owner_subject, self.creation_action.instance_id,
                    self.creation_action.owner_binding_generation, self.creation_action.owner_binding_action_id) != (
                    self.authorization.owner_subject, self.authorization.instance_id,
                    self.authorization.owner_binding_generation, self.authorization.owner_binding_action_id)
                or self.revoked != (self.revocation_action is not None)):
            raise ValueError('Creation delegation requires its original independent Owner action')
        if self.revocation_action and (self.revocation_action.authorization_ref != self.authorization_ref
                or self.revocation_action.action != 'revoke'):
            raise ValueError('Revocation must name the exact parent delegation')
        return self


class ProjectGoalInput(c.Contract):
    format: Literal['project-goal-input-v1'] = 'project-goal-input-v1'
    name: str = Field(default='未命名项目', min_length=1, max_length=200)
    goal: str = Field(min_length=1, max_length=10_000)
    inputs: c.ProductionInputs = Field(default_factory=c.ProductionInputs)
    source_bindings: tuple[c.SourceBinding, ...] = ()
    brief: c.CreativeBriefInput = Field(default_factory=c.CreativeBriefInput)
    delivery: Literal['reference', 'export'] = 'reference'
    creation_authorization_ref: DailyProjectAuthorizationRef | None = None

    @model_validator(mode='after')
    def original_goal(self):
        if not self.goal.strip():
            raise ValueError('Goal must not be blank')
        c.reject_secrets(self.model_dump(mode='json'))
        import json

        if len(json.dumps(self.model_dump(mode='json'), ensure_ascii=False, sort_keys=True,
                separators=(',', ':'), allow_nan=False).encode('utf-8')) > 32 * 1024 * 1024 - 16 * 1024:
            raise ValueError('Canonical Goal must fit its complete bounded accepted-intent journal')
        return self


class ProjectScopeDerivation(c.Contract):
    format: Literal['project-scope-derivation-v1'] = 'project-scope-derivation-v1'
    derivation_id: c.Identifier
    authorization_ref: DailyProjectAuthorizationRef
    creation_action_ref: AuthorizationActionRef
    instance_id: c.Identifier
    owner_subject: c.Identifier
    executing_principal_id: c.Identifier
    entry: Literal['api', 'mcp', 'native']
    project_id: c.Identifier
    goal_sha256: c.Sha256
    installed_record_ref: InstalledNativeRecordRef
    execution_refs: tuple[DailyExecutionRef, ...]
    expires_at_us: int = Field(gt=0, strict=True)
    derived_policy: ProductionAuthorizationPolicy

    @model_validator(mode='after')
    def exact_real_child(self):
        if (self.executing_principal_id != self.owner_subject
                or self.derived_policy.project_ids != (self.project_id,)
                or (self.derived_policy.instance_id, self.derived_policy.owner_subject) != (self.instance_id, self.owner_subject)
                or self.derived_policy.executing_principal_ids != (self.owner_subject,)
                or self.derived_policy.expires_at_us > self.expires_at_us):
            raise ValueError('Derived policy is exactly the real child project and actual Owner')
        return self


class ProjectDerivationReceipt(c.Contract):
    issuer: Literal['trusted_project_derivation'] = 'trusted_project_derivation'
    receipt_id: c.Identifier
    instance_id: c.Identifier
    owner_subject: c.Identifier
    authorization_ref: DailyProjectAuthorizationRef
    creation_action_ref: AuthorizationActionRef
    derivation_ref: ProjectScopeDerivationRef
    goal_sha256: c.Sha256
    request_sha256: c.Sha256
    production_id: c.Identifier
    run_id: c.Identifier
    request_revision_id: c.Identifier
    idempotency_key: c.Identifier
    accepted_at_us: int = Field(gt=0, strict=True)
    registry_revision: int = Field(gt=0, strict=True)


class ProjectGoalAccepted(c.Contract):
    format: Literal['project-goal-accepted-v1'] = 'project-goal-accepted-v1'
    instance_id: c.Identifier
    project_id: c.Identifier
    production_id: c.Identifier
    run_id: c.Identifier
    derivation_ref: ProjectScopeDerivationRef
    goal_sha256: c.Sha256
    production: c.ProductionAccepted

    @model_validator(mode='after')
    def actual_original_acceptance(self):
        if (self.instance_id, self.project_id, self.production_id, self.run_id) != (
                self.production.instance_id, self.production.project_id,
                self.production.production_id, self.production.run_id):
            raise ValueError('Goal response must point to the actual original Production acceptance')
        return self


class ProjectGoalReceiptQueryV1(c.Contract):
    model_config = ConfigDict(extra='forbid', frozen=True, strict=True)
    format: Literal['project-goal-receipt-query-v1']
    expected_instance_id: c.Identifier
    idempotency_key: c.Identifier
    goal: ProjectGoalInput

    @field_validator('goal', mode='before')
    @classmethod
    def original_goal_parser(cls, value):
        from video_creator.domain.errors import EngineError

        try:
            return ProjectGoalInput.model_validate(value)
        except ValidationError as error:
            if any(item['msg'].endswith('Canonical Goal must fit its complete bounded accepted-intent journal')
                    for item in error.errors(include_input=False)):
                raise EngineError('goal_receipt_request_limit', 'Complete Goal exceeds its original limit', 413) from None
            raise

    @model_validator(mode='after')
    def bounded_query(self):
        import json
        from video_creator.domain.errors import EngineError

        if len(json.dumps(self.model_dump(mode='json'), ensure_ascii=False, sort_keys=True,
                separators=(',', ':'), allow_nan=False).encode('utf-8')) > 32 * 1024 * 1024:
            raise EngineError('goal_receipt_request_limit', 'Complete query exceeds its bounded frame', 413)
        return self


class _ProjectGoalReceiptAssociationBase(c.Contract):
    model_config = ConfigDict(extra='forbid', frozen=True, strict=True)
    format: Literal['project-goal-receipt-association-v1']
    instance_id: c.Identifier
    principal_id: c.Identifier
    original_scope: Literal['project.goal.accept']
    idempotency_key: c.Identifier
    goal_sha256: c.Sha256
    canonicalization_id: Literal['project-goal-pydantic-json-v1']


class ProjectGoalReceiptAcceptedV1(_ProjectGoalReceiptAssociationBase):
    state: Literal['accepted']
    receipt: ProjectGoalAccepted

    @model_validator(mode='after')
    def associated_original(self):
        if (self.receipt.instance_id, self.receipt.goal_sha256) != (self.instance_id, self.goal_sha256):
            raise ValueError('Associated receipt must retain its original instance and Goal')
        return self


class ProjectGoalReceiptPendingV1(_ProjectGoalReceiptAssociationBase):
    state: Literal['pending']


class ProjectGoalReceiptDeniedV1(_ProjectGoalReceiptAssociationBase):
    state: Literal['denied']
    reason_code: c.Identifier
    resolved_at_us: int = Field(gt=0, strict=True)


class ProjectGoalReceiptAbsentV1(_ProjectGoalReceiptAssociationBase):
    state: Literal['absent']


ProjectGoalReceiptAssociationV1 = Annotated[
    ProjectGoalReceiptAcceptedV1 | ProjectGoalReceiptPendingV1 |
    ProjectGoalReceiptDeniedV1 | ProjectGoalReceiptAbsentV1,
    Field(discriminator='state'),
]


class DerivedProjectAuthorization(c.Contract):
    format: Literal['derived-project-authorization-v1'] = 'derived-project-authorization-v1'
    parent: DailyProjectAuthorizationRecord
    child: ProjectScopeDerivation
    receipt: ProjectDerivationReceipt

    @model_validator(mode='after')
    def complete_real_sources(self):
        child, parent, receipt = self.child, self.parent, self.receipt
        if (child.authorization_ref != parent.authorization_ref or receipt.authorization_ref != parent.authorization_ref
                or receipt.derivation_ref != ProjectScopeDerivationRef(derivation_id=child.derivation_id, content_sha256=_body_sha256(child))
                or receipt.creation_action_ref != child.creation_action_ref
                or child.creation_action_ref != AuthorizationActionRef(action_id=parent.creation_action.action_id,
                    content_sha256=_body_sha256(parent.creation_action)) or receipt.goal_sha256 != child.goal_sha256
                or (receipt.instance_id, receipt.owner_subject) != (child.instance_id, child.owner_subject)
                or child.derived_policy.model_dump(exclude={'kind', 'version', 'instance_id', 'owner_subject',
                    'executing_principal_ids', 'project_ids', 'expires_at_us'}) != parent.authorization.template.model_dump(exclude={'expires_at_us'})
                or child.expires_at_us > parent.authorization.expires_at_us
                or child.derived_policy.expires_at_us != child.expires_at_us):
            raise ValueError('Derived source requires the full actual parent, child and independent receipts')
        return self


class ProductionAuthorizationDocumentV02(c.Contract):
    kind: Literal['production_authorization'] = 'production_authorization'
    version: Literal['0.2.0-candidate'] = '0.2.0-candidate'
    source_kind: Literal['delegated_project'] = 'delegated_project'
    document_id: c.Identifier
    source: DerivedProjectAuthorization
    policy_ref: ProductionPolicyRef
    plan_admission: ProductionAdmissionFact

    @property
    def policy(self):
        return self.source.child.derived_policy

    @property
    def owner_action(self):
        return self.source.parent.creation_action

    @model_validator(mode='after')
    def immutable_actual_plan(self):
        policy, receipt, fact = self.source.child.derived_policy, self.source.receipt, self.plan_admission
        if (self.policy_ref != ProductionPolicyRef(policy_id=self.source.child.derivation_id, revision=1,
                content_sha256=_body_sha256(policy)) or fact.policy_ref != self.policy_ref
                or fact.owner_action_ref != self.source.child.creation_action_ref or fact.action != 'execute_plan'
                or fact.fencing_token is None or (fact.production_id, fact.request_revision_id, fact.request_sha256) != (
                    receipt.production_id, receipt.request_revision_id, receipt.request_sha256)):
            raise ValueError('Delegated provenance binds the original actual plan and request, never foreign execution')
        return self
