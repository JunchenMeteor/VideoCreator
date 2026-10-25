"""Local setup journals. These exact facts are not transferable capabilities."""

from typing import Literal

from pydantic import Field, model_validator

from video_creator.domain import contracts as c
from video_creator.domain.daily_project_authorization import (
    DailyCreativeTemplate,
    ProjectGoalInput,
)
from video_creator.domain.owner_setup import (
    AcceptedOwnerSetupIntent,
    OwnerSetupIntent,
    SetupDraftIdentity,
    setup_sha256,
)


class SetupPreparationOptions(c.Contract):
    """Displayed finite proposal; actual service/current checks remain required."""
    format: Literal['owner-setup-preparation-options-v1'] = 'owner-setup-preparation-options-v1'
    management_expires_at_us: int = Field(gt=0, strict=True)
    setup_expires_at_us: int = Field(gt=0, strict=True)
    max_created_projects: int = Field(gt=0, le=1_000_000, strict=True)
    max_active_productions: int = Field(gt=0, le=100_000, strict=True)
    allowed_entries: tuple[Literal['api', 'mcp', 'native'], ...] = Field(min_length=1, max_length=3)
    template: DailyCreativeTemplate
    source_manifest_sha256: c.Sha256

    @model_validator(mode='after')
    def finite_original_scope(self):
        if ('native' not in self.allowed_entries or len(set(self.allowed_entries)) != len(self.allowed_entries)
                or not self.setup_expires_at_us <= self.template.expires_at_us <= self.management_expires_at_us):
            raise ValueError('Setup continuation and its finite creation expiry must be explicit')
        return self


class SetupPreparationRequest(c.Contract):
    format: Literal['owner-setup-preparation-request-v1'] = 'owner-setup-preparation-request-v1'
    idempotency_key: c.Identifier
    goal: ProjectGoalInput
    options: SetupPreparationOptions


class DraftOrigin(c.Contract):
    format: Literal['owner-setup-draft-origin-v1'] = 'owner-setup-draft-origin-v1'
    instance_id: c.Identifier
    owner_subject: c.Identifier
    project_draft: SetupDraftIdentity
    goal: ProjectGoalInput
    goal_sha256: c.Sha256
    preparation_key: c.Identifier
    setup_id: c.Identifier
    intent_revision: int = Field(gt=0, strict=True)
    intent_sha256: c.Sha256

    @model_validator(mode='after')
    def exact_full_goal(self):
        if (setup_sha256(self.goal) != self.goal_sha256
                or self.project_draft.draft != c.ProjectInput(name=self.goal.name,
                    goal=self.goal.goal, source_text=self.goal.inputs.source_text)):
            raise ValueError('Draft origin keeps the distinct complete Goal and actual ProjectInput')
        return self


class AcceptedSetupRef(c.Contract):
    setup_id: c.Identifier
    content_sha256: c.Sha256


class PreparedSetupJournal(c.Contract):
    format: Literal['prepared-owner-setup-v1'] = 'prepared-owner-setup-v1'
    request: SetupPreparationRequest
    intent: OwnerSetupIntent
    origin: DraftOrigin

    @model_validator(mode='after')
    def exact_prepared_identity(self):
        if (self.request.goal != self.intent.goal or self.origin.goal != self.intent.goal
                or self.origin.project_draft != self.intent.project_draft
                or self.origin.preparation_key != self.request.idempotency_key
                or (self.origin.setup_id, self.origin.intent_sha256, self.origin.instance_id, self.origin.owner_subject)
                    != (self.intent.setup_id, setup_sha256(self.intent), self.intent.instance_id, self.intent.owner_subject)):
            raise ValueError('Preparation must freeze the exact saved draft and full displayed intent')
        return self


class AcceptedSetupJournal(c.Contract):
    format: Literal['accepted-owner-setup-journal-v1'] = 'accepted-owner-setup-journal-v1'
    prepared: PreparedSetupJournal
    accepted: AcceptedOwnerSetupIntent

    @model_validator(mode='after')
    def unchanged_displayed_intent(self):
        if self.prepared.intent != self.accepted.intent:
            raise ValueError('Accepted setup cannot rewrite the displayed preparation')
        return self
