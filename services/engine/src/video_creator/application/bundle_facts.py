"""Private preparation facts; no HTTP models or independently usable tickets."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Protocol

if TYPE_CHECKING:
    from video_creator.application.local_copy_input_ports import CopyInputAdmission

from video_creator.domain import contracts as c
from video_creator.domain.bundle import (
    BundleContentHandle,
    MaterialAllocation,
    MaterialReceipt,
)
from video_creator.domain.daily_project_authorization import (
    ProductionAuthorizationDocumentV02,
)
from video_creator.domain.production_authorization import (
    ProductionAuthorizationDocument,
)

FACT_FORMAT = "bundle-facts-v1-adr0020"
MAX_CORRECTION_REPORTS = 32
MAX_CORRECTION_ARTIFACTS = 256


@dataclass(frozen=True)
class ReadyRightsArtifact:
    artifact: c.BundleArtifact
    content: BundleContentHandle
    allocation: MaterialAllocation | None
    receipt: MaterialReceipt | None


@dataclass(frozen=True)
class CopiedRightsBinding:
    source_bundle_ref: c.BundleRef
    source_artifact: c.BundleArtifact
    source_rights: c.RightsSnapshot
    source_rights_sha256: str
    source_record_sha256: str | None
    current_artifact: c.BundleArtifact
    current_rights: c.RightsSnapshot
    license_id_mapping: tuple[tuple[str, str], ...]
    current_approval_refs: tuple[c.ApprovalRef, ...]
    required_uses: tuple[c.UsePurpose, ...]
    source_policy_authorization: 'SourcePolicyAuthorization | None' = None
    copy_input_admission: 'CopyInputAdmission | None' = None


@dataclass(frozen=True)
class ProductionAuthorizationMaterialRef:
    artifact: c.BundleArtifact
    receipt: MaterialReceipt
    document: ProductionAuthorizationDocument | ProductionAuthorizationDocumentV02


@dataclass(frozen=True)
class SourcePolicyAuthorization:
    """Source identity container, not an execution or redistribution permit.

    Registry status is an observation of the historical source, not a new
    permission. ADR0026 keeps current creation and rights checks separate.
    """
    source_bundle_ref: c.BundleRef
    authorization: ProductionAuthorizationMaterialRef
    plan_artifact: c.BundleArtifact
    plan_receipt: MaterialReceipt
    observed_at_us: int = 0
    policy_current_at_read: bool | None = None
    policy_revoked_at_read: bool | None = None


@dataclass(frozen=True)
class PreparedRightsContext:
    instance_id: str
    subject: str
    project_id: str
    production_id: str
    run_id: str
    request_revision_id: str
    request_sha256: str
    preparation_id: str
    fencing_token: int
    checked_at_us: int
    required_uses: tuple[c.UsePurpose, ...]
    rights: tuple[c.RightsSnapshot, ...]
    approval_refs: tuple[c.ApprovalRef, ...]
    creative_revision_refs: tuple[c.RevisionRef, ...]
    artifacts: tuple[ReadyRightsArtifact, ...]
    stage: Literal["pre_quality", "final_manifest"]
    final_manifest_sha256: str | None
    origin_bindings: tuple[CopiedRightsBinding, ...]
    context_sha256: str
    production_authorization_refs: tuple[ProductionAuthorizationMaterialRef, ...] = ()


@dataclass(frozen=True)
class GrantEvidenceRef:
    source_id: str
    source_revision: str
    content_sha256: str
    subject_id: str
    project_id: str
    rights_id: str
    permitted_uses: tuple[c.UsePurpose, ...]
    platforms: tuple[str, ...]
    territories: tuple[str, ...]
    valid_from_us: int | None
    expires_at_us: int | None


@dataclass(frozen=True)
class RightsAuthorityObservation:
    authority_id: str
    authority_revision: str
    configuration_sha256: str
    revocation_revision: str
    grant_evidence_refs: tuple[GrantEvidenceRef, ...]
    context_sha256: str
    rights_sha256: str
    observed_at_us: int
    valid_until_us: int
    check: c.QualityCheck
    evidence_artifact_ids: tuple[str, ...]


class PreparedRightsAuthority(Protocol):
    """Candidate for architecture admission, disabled in this implementation.

    Trusted startup only. verify may consult real sources outside a writer;
    assert_current must be deterministic local read-only validation, never
    network/file I/O. Neither bool nor caller-created fields are observations.
    """
    def verify(self, context: PreparedRightsContext) -> tuple[RightsAuthorityObservation, ...]: ...
    def assert_current(self, context: PreparedRightsContext, observations: tuple[RightsAuthorityObservation, ...],
                       *, now_us: int, connection) -> None: ...


@dataclass(frozen=True)
class VerifiedRightsEvidence:
    verification_id: str
    context: PreparedRightsContext
    quality_check: c.QualityCheck
    evidence_artifact_ids: tuple[str, ...]
    approval_refs: tuple[c.ApprovalRef, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class CorrectionSourceArtifact:
    source_bundle_ref: c.BundleRef
    artifact: c.BundleArtifact
    rights: c.RightsSnapshot
    content: BundleContentHandle
    approval_refs: tuple[c.ApprovalRef, ...]
    schema_kind: str
    record_content_sha256: str | None
    source_policy_authorization: SourcePolicyAuthorization | None = None


@dataclass(frozen=True)
class CorrectionDependencyEdge:
    parent: CorrectionSourceArtifact
    indexed_child: CorrectionSourceArtifact
    child_reference: c.CorrectionOriginRef
    child_source: CorrectionSourceArtifact


@dataclass(frozen=True)
class CorrectionReportSource:
    reference: c.CorrectionOriginRef
    source: CorrectionSourceArtifact
    raw_bytes: bytes


@dataclass(frozen=True)
class CorrectionOriginEvidence:
    instance_id: str
    production_id: str
    run_id: str
    request_revision_id: str
    request_sha256: str
    fencing_token: int
    checked_at_us: int
    required_uses: tuple[c.UsePurpose, ...]
    reports: tuple[CorrectionReportSource, ...]
    license_documents: tuple[CorrectionSourceArtifact, ...]
    dependency_edges: tuple[CorrectionDependencyEdge, ...]
    source_set_sha256: str
    limitations: tuple[str, ...]
    copy_input_admission: 'CopyInputAdmission | None' = None
