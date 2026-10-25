"""Private installation capabilities. No installer or trust root is a public DTO."""

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict

from video_creator.domain.contracts import (
    EvidenceAuthorityRevisionRef,
    EvidencePolicyRevision,
    EvidencePolicyRevisionRef,
    Identifier,
    MethodBenchmarkReport,
    MethodQualificationRef,
    Sha256,
)


class EvidenceApproval(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    issuer: Identifier
    approval_id: Identifier
    document_sha256: Sha256
    benchmark_content_sha256: Sha256
    signature: Sha256


class ReferenceIssuerApproval(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    issuer: Identifier
    approval_id: Identifier
    scope_content_sha256: Sha256
    signature: Sha256


class EvidenceRevocation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    issuer: Identifier
    target_kind: Literal["policy", "qualification", "reference_issuer"]
    target_id: Identifier
    target_revision: int
    effective_at_us: int
    reason: str
    dedupe_key: Identifier
    signature: Sha256


@dataclass(frozen=True)
class EvidenceAdminCapability:
    capability_id: str


class ReferenceIssuerAdmission(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    authority_id: Identifier
    revision: int
    issuer: Identifier
    reference_issuer: Identifier
    key_id: Identifier
    owner_subject: Identifier
    project_id: Identifier
    audio_sha256: tuple[Sha256, ...]
    listener_material_sha256: tuple[Sha256, ...]
    arbitration_material_sha256: tuple[Sha256, ...]
    independent_approval_refs: tuple[Sha256, ...]
    criterion_version_ref: Literal["alignment-unit-max-p95-200ms-v1"]
    evaluation_scope: Literal["per_work_reference_measurement"]
    valid_from_us: int
    expires_at_us: int
    content_sha256: Sha256

    @property
    def authority_ref(self) -> EvidenceAuthorityRevisionRef:
        return EvidenceAuthorityRevisionRef(authority_id=self.authority_id, revision=self.revision, content_sha256=self.content_sha256)


@dataclass(frozen=True)
class ResolvedEvidencePolicy:
    policy: EvidencePolicyRevision
    qualification: MethodQualificationRef
    benchmark: MethodBenchmarkReport
    registry_revision: int

    @property
    def policy_ref(self) -> EvidencePolicyRevisionRef:
        return EvidencePolicyRevisionRef(policy_id=self.policy.policy_id, revision=self.policy.revision,
                                       content_sha256=self.policy.content_sha256)
