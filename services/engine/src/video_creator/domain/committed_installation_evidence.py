"""ADR0046 exact immutable committed facts; never a source capability."""

from typing import Literal
from pydantic import model_validator
from video_creator.domain import contracts as c
from video_creator.domain.installation_qualification import (
    I64, PositiveI64, QualificationRef, TrustAdmission, InstallationRecordAdmission,
    body_sha,
)


class InstallationActionRequest(c.Contract):
    action_id: c.Identifier
    kind: Literal['trust_admit', 'record_admit', 'replace']
    trust_admission_ref: QualificationRef
    record_ref: QualificationRef | None
    expected_registry_revision: I64


class PersistedRecordReceipt(InstallationRecordAdmission):
    kind: Literal['record_admit', 'replace']


class TrustCommit(c.Contract):
    admission_ref: QualificationRef
    action_ref: QualificationRef
    request: InstallationActionRequest
    request_sha256: c.Sha256
    registry_revision: PositiveI64
    source_receipt: TrustAdmission

    @model_validator(mode='after')
    def exact_event(self):
        receipt=self.source_receipt
        digest=body_sha(receipt)
        if (self.admission_ref!=QualificationRef(document_id='trust.'+digest,revision=1,sha256=digest)
                or self.action_ref!=QualificationRef(document_id=receipt.action_id,revision=self.registry_revision,sha256=digest)
                or self.request.action_id!=receipt.action_id or self.request.kind!='trust_admit'
                or self.request.trust_admission_ref!=self.admission_ref or self.request.record_ref is not None
                or self.request.expected_registry_revision!=0 or self.registry_revision!=1
                or self.request_sha256!=body_sha(self.request)):
            raise ValueError('Original trust commit/ref/request differ')
        return self


class RecordCommit(c.Contract):
    record_ref: QualificationRef
    action_ref: QualificationRef
    request: InstallationActionRequest
    request_sha256: c.Sha256
    registry_revision: PositiveI64
    source_receipt: PersistedRecordReceipt

    @model_validator(mode='after')
    def exact_event(self):
        receipt=self.source_receipt
        if (self.record_ref!=receipt.record.ref() or self.request.record_ref!=self.record_ref
                or self.request.action_id!=receipt.action_id or self.request.kind!=receipt.kind
                or self.request.trust_admission_ref!=receipt.trust_admission_ref
                or self.request.expected_registry_revision!=receipt.expected_registry_revision
                or self.registry_revision!=receipt.expected_registry_revision+1
                or self.request_sha256!=body_sha(self.request)
                or self.action_ref!=QualificationRef(document_id=receipt.action_id,revision=self.registry_revision,sha256=body_sha(receipt))):
            raise ValueError('Original record commit/ref/request differ')
        return self


class CommittedInstallationEvidence(c.Contract):
    format: Literal['installation-committed-evidence-v1']
    instance_id: c.Identifier
    registry_revision: PositiveI64
    trust_commit: TrustCommit
    record_commit: RecordCommit | None

    @model_validator(mode='after')
    def exact_current(self):
        record=self.record_commit
        if self.registry_revision!=(record.registry_revision if record is not None else self.trust_commit.registry_revision):
            raise ValueError('Committed header differs from its actual last admission')
        if record is not None and record.source_receipt.trust_admission_ref!=self.trust_commit.admission_ref:
            raise ValueError('Record commit belongs to another original trust admission')
        return self
