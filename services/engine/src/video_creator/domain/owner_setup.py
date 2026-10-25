"""Exact setup intent and receipts. Serialized values never grant confirmation."""

import hashlib
import json
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from video_creator.domain import contracts as c
from video_creator.domain.daily_project_authorization import (
    DailyCreativeTemplate,
    DailyExecutionRef,
    DailyProjectAuthorizationRef,
    ProjectGoalInput,
)
from video_creator.domain.native_execution_registration import (
    InstalledNativeRecordRef,
    InstallNativeExecution,
    NativeInstallationInputs,
    local_absolute_path,
)

SETUP_FRAME_LIMIT = 32 * 1024 * 1024


def setup_bytes(model) -> bytes:
    return json.dumps(model.model_dump(mode='json'), ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def setup_sha256(model) -> str:
    return hashlib.sha256(setup_bytes(model)).hexdigest()


def step_proposal_sha256(step) -> str:
    raw = step.model_dump(mode='json', exclude={'proposal_sha256'})
    data = json.dumps(raw, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                      allow_nan=False).encode('utf-8')
    return hashlib.sha256(data).hexdigest()


class SetupDirectoryIdentity(c.Contract):
    path: str = Field(min_length=1, max_length=32768)
    os_subject: str = Field(min_length=1, max_length=200)
    administrator_id: c.Identifier
    device: int = Field(ge=0, strict=True)
    inode: int = Field(ge=0, strict=True)

    @field_validator('path')
    @classmethod
    def local_directory(cls, value):
        return local_absolute_path(value)


class ExpectedSetupOwner(c.Contract):
    generation: int = Field(ge=0, strict=True)
    action_id: c.Identifier | None
    binding_body_sha256: c.Sha256 | None

    @model_validator(mode='after')
    def complete_original_state(self):
        if (self.generation == 0) != (self.action_id is None and self.binding_body_sha256 is None):
            raise ValueError('Empty Owner state has no action/hash; existing state needs both')
        if self.generation and (self.action_id is None or self.binding_body_sha256 is None):
            raise ValueError('Existing Owner state requires its complete original identity')
        return self


class SetupDraftIdentity(c.Contract):
    project_id: c.Identifier
    revision: int = Field(gt=0, strict=True)
    saved_at_us: int = Field(gt=0, strict=True)
    body_sha256: c.Sha256
    draft: c.ProjectInput
    project_draft_sha256: c.Sha256
    create_command_key: c.Identifier
    create_request_sha256: c.Sha256
    create_receipt_sha256: c.Sha256

    @model_validator(mode='after')
    def complete_original_create(self):
        actual = c.ProjectDraft(**self.draft.model_dump(), project_id=self.project_id,
                                revision=self.revision, saved_at_us=self.saved_at_us)
        if (self.body_sha256 != setup_sha256(self.draft)
                or self.create_request_sha256 != self.body_sha256
                or self.project_draft_sha256 != setup_sha256(actual)
                or self.create_receipt_sha256 != self.project_draft_sha256):
            raise ValueError('Setup freezes the complete actual draft and original create receipt')
        return self


class SetupOwnerInitialize(c.Contract):
    type: Literal['owner_initialize'] = 'owner_initialize'
    step_id: c.Identifier
    idempotency_key: c.Identifier
    proposal_sha256: c.Sha256
    owner_subject: c.Identifier
    project_ids: tuple[c.Identifier, ...] = Field(min_length=1, max_length=256)
    expires_at_us: int = Field(gt=0, strict=True)


class SetupExecutionInstall(c.Contract):
    type: Literal['execution_install'] = 'execution_install'
    step_id: c.Identifier
    idempotency_key: c.Identifier
    proposal_sha256: c.Sha256
    proposal: InstallNativeExecution
    owner_from_step: c.Identifier | None


class SetupExecutionReceiptDependency(c.Contract):
    source: Literal['this_setup_execution_receipt'] = 'this_setup_execution_receipt'
    step_id: c.Identifier


class SetupExistingExecution(c.Contract):
    source: Literal['existing_current_execution'] = 'existing_current_execution'
    installed_record_ref: InstalledNativeRecordRef
    execution_refs: tuple[DailyExecutionRef, ...] = Field(min_length=3, max_length=3)

    @model_validator(mode='after')
    def complete_roles(self):
        if {item.role for item in self.execution_refs} != {'api', 'mcp', 'worker'}:
            raise ValueError('Existing source requires all three exact current roles')
        return self


SetupExecutionDependency = Annotated[
    SetupExecutionReceiptDependency | SetupExistingExecution, Field(discriminator='source')]


class SetupCreationInstall(c.Contract):
    type: Literal['creation_install'] = 'creation_install'
    step_id: c.Identifier
    idempotency_key: c.Identifier
    proposal_sha256: c.Sha256
    authorization_id: c.Identifier
    previous_ref: DailyProjectAuthorizationRef | None
    execution_source: SetupExecutionDependency
    allowed_entries: tuple[Literal['api', 'mcp', 'native'], ...] = Field(min_length=1, max_length=3)
    expires_at_us: int = Field(gt=0, strict=True)
    max_created_projects: int = Field(gt=0, le=1_000_000, strict=True)
    max_active_productions: int = Field(gt=0, le=100_000, strict=True)
    template: DailyCreativeTemplate

    @model_validator(mode='after')
    def bounded_scope(self):
        if len(set(self.allowed_entries)) != len(self.allowed_entries) or self.expires_at_us > self.template.expires_at_us:
            raise ValueError('Setup creation scope is finite and has an explicit template interval')
        return self


class SetupContinueGoal(c.Contract):
    type: Literal['continue_goal'] = 'continue_goal'
    step_id: c.Identifier
    idempotency_key: c.Identifier
    proposal_sha256: c.Sha256
    creation_from_step: c.Identifier
    goal_sha256: c.Sha256


OwnerSetupStep = Annotated[
    SetupOwnerInitialize | SetupExecutionInstall | SetupCreationInstall | SetupContinueGoal,
    Field(discriminator='type')]


class OwnerSetupIntent(c.Contract):
    format: Literal['owner-setup-intent-v1'] = 'owner-setup-intent-v1'
    setup_id: c.Identifier
    instance_id: c.Identifier
    owner_subject: c.Identifier
    directory: SetupDirectoryIdentity
    expected_owner: ExpectedSetupOwner
    goal: ProjectGoalInput
    goal_sha256: c.Sha256
    project_draft: SetupDraftIdentity
    installation: NativeInstallationInputs
    external_receipt_path: str = Field(min_length=1, max_length=32768)
    expected_host_image: str = Field(min_length=1, max_length=32768)
    expected_host_sha256: c.Sha256
    source_manifest_sha256: c.Sha256
    created_at_us: int = Field(gt=0, strict=True)
    expires_at_us: int = Field(gt=0, strict=True)
    steps: tuple[OwnerSetupStep, ...] = Field(min_length=2, max_length=4)

    @field_validator('external_receipt_path', 'expected_host_image')
    @classmethod
    def actual_local_file(cls, value):
        return local_absolute_path(value)

    @model_validator(mode='after')
    def exact_closed_plan(self):
        if (self.expires_at_us <= self.created_at_us or self.goal_sha256 != setup_sha256(self.goal)
                or self.project_draft.body_sha256 != setup_sha256(self.project_draft.draft)
                or self.project_draft.draft != c.ProjectInput(name=self.goal.name, goal=self.goal.goal,
                    source_text=self.goal.inputs.source_text)
                or (self.expected_host_image, self.expected_host_sha256) != (
                    self.installation.installed_native_image, self.installation.installed_native_image_sha256)):
            raise ValueError('Setup requires the actual whole Goal, draft and independent installed source')
        if (len({item.step_id for item in self.steps}) != len(self.steps)
                or len({item.idempotency_key for item in self.steps}) != len(self.steps)):
            raise ValueError('Setup has distinct exact original step/key identities')
        kinds = tuple(item.type for item in self.steps)
        expected = ('owner_initialize',) if self.expected_owner.generation == 0 else ()
        if 'execution_install' in kinds:
            expected += ('execution_install',)
        expected += ('creation_install', 'continue_goal')
        if kinds != expected:
            raise ValueError('Only the closed original setup action order is admitted')
        owner_step = self.steps[0] if self.expected_owner.generation == 0 else None
        previous = {}
        for step in self.steps:
            if step.proposal_sha256 != step_proposal_sha256(step):
                raise ValueError('Each displayed original complete step has its exact proposal hash')
            if isinstance(step, SetupOwnerInitialize):
                if (step.owner_subject != self.owner_subject or step.project_ids != (self.project_draft.project_id,)
                        or step.expires_at_us < self.expires_at_us):
                    raise ValueError('First Owner scope is exactly the real Goal draft')
            elif isinstance(step, SetupExecutionInstall):
                if (step.proposal.installation != self.installation
                        or step.owner_from_step != (owner_step.step_id if owner_step else None)
                        or {item.role for item in step.proposal.registrations} != {'api', 'mcp', 'worker'}
                        or any(item.project_ids != (self.project_draft.project_id,)
                               or item.expires_at_us < self.expires_at_us for item in step.proposal.registrations)):
                    raise ValueError('Installation binds the original full input and all real draft roles')
            elif isinstance(step, SetupCreationInstall):
                source = step.execution_source
                if (isinstance(source, SetupExecutionReceiptDependency)
                        and (source.step_id not in previous or previous[source.step_id].type != 'execution_install')):
                    raise ValueError('Execution references can only come from this prior original receipt')
                if ((step.template.registration_sha256, step.template.resource_manifest_sha256,
                        step.template.runtime_manifest_sha256) != (self.installation.registration_sha256,
                        self.installation.resource_manifest_sha256, self.installation.runtime_manifest_sha256)
                        or step.expires_at_us < self.expires_at_us):
                    raise ValueError('Creation scope preserves all original installed identities and expiry')
            elif isinstance(step, SetupContinueGoal) and (
                    step.creation_from_step not in previous or previous[step.creation_from_step].type != 'creation_install'
                    or step.goal_sha256 != self.goal_sha256):
                raise ValueError('Continue only this original Goal and creation receipt')
            previous[step.step_id] = step
        c.reject_secrets(self.model_dump(mode='json'))
        # Frame adds fixed authenticated envelope fields; never truncate intent.
        if len(setup_bytes(self)) > SETUP_FRAME_LIMIT - 16 * 1024:
            raise ValueError('Complete setup must fit its bounded frame including envelope')
        return self


class NativeSetupConfirmationOrigin(c.Contract):
    authentication_source: Literal['native_owner_session'] = 'native_owner_session'
    session_id: c.Identifier
    challenge_id: c.Identifier
    confirmation_id: c.Identifier
    os_subject: str = Field(min_length=1, max_length=200)
    gui_session_id: c.Identifier
    document_generation: int = Field(gt=0, strict=True)
    host_pid: int = Field(gt=0, le=0xFFFFFFFF, strict=True)
    host_creation_filetime: int = Field(gt=0, strict=True)
    child_pid: int = Field(gt=0, le=0xFFFFFFFF, strict=True)
    child_creation_filetime: int = Field(gt=0, strict=True)
    expected_host_sha256: c.Sha256


class AcceptedOwnerSetupIntent(c.Contract):
    format: Literal['accepted-owner-setup-intent-v1'] = 'accepted-owner-setup-intent-v1'
    intent: OwnerSetupIntent
    intent_sha256: c.Sha256
    source: NativeSetupConfirmationOrigin
    accepted_at_us: int = Field(gt=0, strict=True)

    @model_validator(mode='after')
    def exact_origin(self):
        if (self.intent_sha256 != setup_sha256(self.intent)
                or (self.source.os_subject, self.source.expected_host_sha256) != (
                    self.intent.directory.os_subject, self.intent.expected_host_sha256)
                or not self.intent.created_at_us <= self.accepted_at_us < self.intent.expires_at_us):
            raise ValueError('Accepted record binds this exact intended source; it is not a ticket')
        return self


class OwnerSetupDependencyReceipt(c.Contract):
    step_id: c.Identifier
    receipt_sha256: c.Sha256


class FinalizedOwnerSetupStep(c.Contract):
    step_id: c.Identifier
    original_proposal_sha256: c.Sha256
    final_command_sha256: c.Sha256
    dependency_receipts: tuple[OwnerSetupDependencyReceipt, ...] = ()
    original_receipt_sha256: c.Sha256


class OwnerSetupStatus(c.Contract):
    format: Literal['owner-setup-status-v1'] = 'owner-setup-status-v1'
    setup_id: c.Identifier
    intent_sha256: c.Sha256
    phase: Literal['prepared', 'pending_confirmation', 'accepted', 'running', 'blocked', 'completed', 'aborted']
    current_step_id: c.Identifier | None
    committed_step_ids: tuple[c.Identifier, ...]
    code: c.Identifier
    api_ready: Literal[False] = False

    @field_validator('api_ready', mode='before')
    @classmethod
    def never_api_ready(cls, value):
        if type(value) is not bool or value:
            raise ValueError('Preparation/setup status never grants API readiness')
        return value
