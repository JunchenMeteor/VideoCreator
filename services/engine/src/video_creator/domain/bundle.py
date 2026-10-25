"""Private Bundle1 receipts/authority, never exported as HTTP schemas."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from video_creator.domain.contracts import (
    ActualTranscriptDocument,
    AssetRecord,
    AudioTimelineMapping,
    BundleManifest,
    BundleRef,
    FrameEvidenceRef,
    Identifier,
    LeaseGrant,
    MediaProbe,
    PrecisionEvaluationReport,
    Sha256,
    UsePurpose,
)
from video_creator.domain.production_authorization import ProductionAdmissionRef


class InternalBundleModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class MaterialSlot(InternalBundleModel):
    artifact_id: Identifier
    relative_path: str
    media_type: Literal["application/json", "application/x-ndjson", "text/plain", "text/srt", "text/vtt"]
    schema_kind: Literal["creative_revision", "approved_script", "actual_transcript", "work_summary", "source_bindings", "shots", "semantic_segments", "rag_chunks", "quality", "precision_report", "srt", "vtt", "license", "audit_summary", "actual_transcript_v03", "precision_report_v03", "precision_reference_v03", "method_benchmark", "method_benchmark_reference", "method_qualification", "evidence_policy", "work_alignment_validation", "production_authorization", "local_master_selection", "local_speech_evidence", "actual_transcript_local", "quality_local", "visual_mapping_local", "shots_local", "semantic_segments_local", "rag_chunks_local", "srt_local", "vtt_local"]


class BundlePreparationIntent(InternalBundleModel):
    bundle_id: Identifier
    bundle_revision_id: Identifier
    request_revision_id: Identifier
    input_sha256: Sha256
    material_slots: tuple[MaterialSlot, ...]
    media_asset_ids: tuple[Identifier, ...]


class MaterialReceipt(InternalBundleModel):
    preparation_id: Identifier
    artifact_id: Identifier
    material_id: Identifier
    sha256: Sha256
    size: int = Field(gt=0, strict=True)
    media_type: str
    schema_kind: str
    validation_method: Literal["bundle-strict-text-v1"] = "bundle-strict-text-v1"


class MaterialAllocation(InternalBundleModel):
    preparation_id: Identifier
    artifact_id: Identifier
    material_id: Identifier
    relative_path: str
    media_type: str
    schema_kind: str


@dataclass(frozen=True)
class VerifiedAlignmentEvidence:
    verification_id: str
    preparation_id: str
    run_id: str
    fencing_token: int
    work_report_sha256: str


class BundlePreparation(InternalBundleModel):
    preparation_id: Identifier
    bundle_id: Identifier
    bundle_revision_id: Identifier
    input_sha256: Sha256
    state: Literal["prepared", "published"]
    materials: tuple[MaterialReceipt, ...]
    manifest_sha256: Sha256 | None = None


@dataclass(frozen=True)
class AccessContext:
    subject_id: str
    installation_id: str
    project_ids: frozenset[str]
    operations: frozenset[str]
    purposes: frozenset[str]
    expires_at_us: int | None = None
    owned_projects: bool = False
    registration_id: str | None = None


@dataclass(frozen=True)
class PrincipalRegistration:
    principal_id: str
    project_ids: frozenset[str]
    operations: frozenset[str]
    purposes: frozenset[str]
    expires_at_us: int | None = None
    owned_projects: bool = False


@dataclass(frozen=True)
class VerifiedBundleMaterial:
    # Only the service that actually performed verification can resolve this token.
    verification_id: str
    preparation_id: str
    manifest_sha256: str


@dataclass(frozen=True)
class BundleContentHandle:
    path: Path
    sha256: str
    size: int
    media_type: str
    purpose: UsePurpose


@dataclass(frozen=True)
class ExportLease:
    export_id: str
    worker_id: str
    fencing_token: int
    expires_at_us: int


@dataclass(frozen=True)
class TrustedBundleValidators:
    media_validator: Callable[[Path, str], MediaProbe] | None = None
    precision_authorities: Mapping[str, Callable[[PrecisionEvaluationReport, ActualTranscriptDocument], bool]] | None = None
    frame_validator: Callable[[FrameEvidenceRef, Path], bool] | None = None
    resource_manifest_hashes: frozenset[str] = frozenset()
    word_degradation_allowed: bool = False


class BundleProducerPort(Protocol):
    def prepare(self, lease: LeaseGrant, intent: BundlePreparationIntent) -> BundlePreparation: ...
    def stage_production_authorization(self, lease: LeaseGrant, preparation_id: str, artifact_id: str,
        *, plan_admission_ref: ProductionAdmissionRef) -> MaterialReceipt: ...
    def stage_material(self, lease: LeaseGrant, preparation_id: str, artifact_id: str, data: bytes) -> MaterialReceipt: ...
    def read_material(self, lease: LeaseGrant, preparation_id: str, material_id: str) -> bytes: ...
    def asset(self, lease: LeaseGrant, asset_id: str) -> AssetRecord: ...
    def content_path(self, lease: LeaseGrant, asset_id: str) -> Path: ...
    def verify(self, lease: LeaseGrant, preparation_id: str, manifest: BundleManifest) -> VerifiedBundleMaterial: ...
    def publish(self, lease: LeaseGrant, verified: VerifiedBundleMaterial) -> BundleRef: ...
    def recover_preparation(self, lease: LeaseGrant, preparation_id: str) -> BundlePreparation: ...
    def material_allocation(self, lease: LeaseGrant, preparation_id: str, artifact_id: str) -> MaterialAllocation: ...
    def verify_alignment_evidence(self, lease: LeaseGrant, preparation_id: str, *, actual_transcript_artifact_id: str,
        work_validation_artifact_id: str, audio_mappings: tuple[AudioTimelineMapping, ...]) -> VerifiedAlignmentEvidence: ...
