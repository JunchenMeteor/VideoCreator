"""Private final-evidence progress; serialized values never confer authority."""

from dataclasses import dataclass
from typing import Literal

from pydantic import ConfigDict, Field, model_validator

from video_creator.domain import contracts as c
from video_creator.domain.bundle import (
    BundlePreparation,
    BundlePreparationIntent,
    MaterialAllocation,
    MaterialReceipt,
    VerifiedBundleMaterial,
)
from video_creator.domain.evidence import ResolvedEvidencePolicy
from video_creator.domain.registered_production import (
    AsrResultAllocation,
    PrivateModel,
    ProductionBinding,
)

# This is the original allocation grammar, not a parallel public SchemaKind.
SchemaKind = Literal['creative_revision', 'approved_script', 'actual_transcript', 'work_summary',
    'source_bindings', 'shots', 'semantic_segments', 'rag_chunks', 'quality', 'precision_report',
    'srt', 'vtt', 'license', 'audit_summary', 'actual_transcript_v03', 'precision_report_v03',
    'precision_reference_v03', 'method_benchmark', 'method_benchmark_reference', 'method_benchmark_self_issued',
    'method_qualification', 'evidence_policy', 'work_alignment_validation', 'production_authorization']
SourceRef = c.EvidencePolicyRevisionRef | c.EvidenceReportRef | c.EvidenceAuthorityRevisionRef | c.MethodQualificationRef | c.EvidenceMaterialRef


class FinalModel(PrivateModel):
    model_config = ConfigDict(extra='forbid', frozen=True, strict=True)


class FinalEvidenceDependency(FinalModel):
    kind: Literal['work_validation', 'method_qualification', 'independent_reference',
                  'precision_measurement', 'verifier_resource']
    completion_kind: Literal['consume_ready_evidence', 'generate_runtime_report']
    target_artifact_id: c.Identifier | None
    expected_schema_kind: SchemaKind | None
    source_ref: SourceRef | None
    reason_code: c.Identifier

    @model_validator(mode='after')
    def runtime_only(self):
        if self.completion_kind == 'generate_runtime_report' and self.kind not in {'work_validation', 'precision_measurement'}:
            raise ValueError('Independent references and qualifications are never runtime generated')
        return self


class FinalEvidenceRepair(FinalModel):
    failed_check_code: c.Identifier
    source_report_ref: MaterialReceipt
    affected_artifact_ids: tuple[c.Identifier, ...]
    failed_unit_ids: tuple[c.Identifier, ...]
    allowed_action: Literal['realignment', 'regenerate_affected_media', 'guidance_required']

    @model_validator(mode='after')
    def distinct_actual_subset(self):
        if (not self.affected_artifact_ids or len(set(self.affected_artifact_ids)) != len(self.affected_artifact_ids)
                or len(set(self.failed_unit_ids)) != len(self.failed_unit_ids)):
            raise ValueError('Repair retains the actual distinct failed subset')
        return self


class CurrentFinalEvidenceSnapshot(FinalModel):
    preparation_id: c.Identifier
    preparation_intent_sha256: c.Sha256
    candidate_manifest_file_sha256: c.Sha256 | None
    ready_material_refs: tuple[MaterialReceipt, ...]
    state: Literal['waiting_evidence', 'repair_required']
    reason_code: c.Identifier
    dependencies: tuple[FinalEvidenceDependency, ...]
    repair: FinalEvidenceRepair | None

    @model_validator(mode='after')
    def exact_preparation(self):
        if (len({r.artifact_id for r in self.ready_material_refs}) != len(self.ready_material_refs)
                or any(r.preparation_id != self.preparation_id for r in self.ready_material_refs)
                or (self.state == 'repair_required') != (self.repair is not None)
                or (self.state == 'waiting_evidence' and not self.dependencies)):
            raise ValueError('Snapshot preserves one real preparation and a concrete reason')
        return self


class FinalEvidenceControl(FinalModel):
    phase: Literal['waiting', 'queued', 'executing']
    resume_mode: Literal['retry_final_validation', 'repair'] | None
    execution_fence: int | None = Field(gt=0, strict=True)

    @model_validator(mode='after')
    def phase_shape(self):
        if ((self.phase == 'waiting' and (self.resume_mode is not None or self.execution_fence is not None))
                or (self.phase == 'queued' and (self.resume_mode is None or self.execution_fence is not None))
                or (self.phase == 'executing' and (self.resume_mode is None or self.execution_fence is None))):
            raise ValueError('Control must keep its original three-phase shape')
        return self


class CurrentFinalEvidenceJournal(FinalModel):
    format: Literal['current-production-final-evidence-v1']
    binding: ProductionBinding
    snapshot: CurrentFinalEvidenceSnapshot
    control: FinalEvidenceControl
    blocked_at_us: int = Field(gt=0, strict=True)
    last_transition_at_us: int = Field(gt=0, strict=True)

    @model_validator(mode='after')
    def monotonic_transition(self):
        if self.last_transition_at_us < self.blocked_at_us:
            raise ValueError('Original blocked time cannot be reset by continuation')
        return self


@dataclass(frozen=True, eq=False)
class CurrentFinalEvidenceAssessment:
    assessment_id: str
    binding: ProductionBinding
    snapshot: CurrentFinalEvidenceSnapshot | None
    verified_material: VerifiedBundleMaterial | None

    def __post_init__(self):
        if (self.snapshot is None) == (self.verified_material is None):
            raise ValueError('A service assessment is either a wait or actual verified material')


@dataclass(frozen=True, eq=False)
class CurrentFinalEvidenceInputs:
    binding: ProductionBinding
    preparation_id: str
    preparation_intent_sha256: str
    ready_material_refs: tuple[MaterialReceipt, ...]
    resolved: ResolvedEvidencePolicy | None


@dataclass(frozen=True)
class CurrentFinalEvidenceContinuation:
    binding: ProductionBinding
    snapshot: CurrentFinalEvidenceSnapshot
    resume_mode: Literal['retry_final_validation', 'repair']
    execution_fence: int


class AssemblyContextRef(FinalModel):
    preparation_id: c.Identifier
    preparation_intent_sha256: c.Sha256
    content_sha256: c.Sha256
    size: int = Field(gt=0, strict=True)


class AsrValidationContextRef(FinalModel):
    operation_id: c.Identifier
    run_id: c.Identifier
    input_sha256: c.Sha256
    route_sha256: c.Sha256
    binding_sha256: c.Sha256
    resource_manifest_sha256: c.Sha256
    runtime_manifest_sha256: c.Sha256
    context_sha256: c.Sha256
    size: int = Field(gt=0, le=2 * 1024 * 1024, strict=True)
    provider_sha256: c.Sha256
    worker_sha256: c.Sha256


class CurrentFinalAssemblyContext(FinalModel):
    format: Literal['current-final-assembly-context-v1']
    binding: ProductionBinding
    preparation_id: c.Identifier
    preparation_intent_sha256: c.Sha256
    authored_fence: int = Field(gt=0, strict=True)
    manifest_created_at_us: c.NonnegativeInt
    timeline_duration_us: c.PositiveInt
    creative_revision_refs: tuple[c.RevisionRef, ...]
    approval_refs: tuple[c.ApprovalRef, ...]
    feedback_revision_refs: tuple[c.RevisionRef, ...]
    source_refs: tuple[c.BundleSourceRef, ...]
    outputs: tuple[c.BundleOutput, ...]
    media_artifacts: tuple[c.BundleArtifact, ...]
    audio_mappings: tuple[c.AudioTimelineMapping, ...]
    methods: tuple[c.MethodEvidence, ...]
    rights: tuple[c.RightsSnapshot, ...]
    quality_ref: c.RevisionRef
    document_artifact_ids: dict[str, c.Identifier]
    asr_operation_id: c.Identifier

    @model_validator(mode='after')
    def distinct_original_ids(self):
        if (len(set(self.document_artifact_ids.values())) != len(self.document_artifact_ids)
                or len({a.artifact_id for a in self.media_artifacts}) != 4
                or len(self.media_artifacts) != 4):
            raise ValueError('Original distinct documents and four masters required')
        c.reject_secrets(self.model_dump(mode='json'))
        return self


class CurrentFinalAssemblyContextV2(CurrentFinalAssemblyContext):
    format: Literal['current-final-assembly-context-v2']
    corrected_from: c.CorrectionOriginRef | None
    correction_reason: str | None = Field(min_length=1, max_length=1000)

    @model_validator(mode='after')
    def original_correction_pair(self):
        if (self.corrected_from is None) != (self.correction_reason is None):
            raise ValueError('Original correction locator and author reason are one pair')
        return self


@dataclass(frozen=True, eq=False)
class CurrentFinalAsrRead:
    """Original settled facts; a projection confers no execution permission."""
    operation_id: str
    run_id: str
    production_id: str
    input_sha256: str
    route_sha256: str
    status: Literal['succeeded']
    settled: bool
    observation: c.OperationObservation
    allocation: AsrResultAllocation
    original_context_bytes: bytes
    context_ref: AsrValidationContextRef


@dataclass(frozen=True, eq=False)
class CurrentFinalEvidenceReadSet:
    """Sole nonserializable original service read-set, never an authority."""
    binding: ProductionBinding
    execution_fence: int
    preparation: BundlePreparation
    intent: BundlePreparationIntent
    allocations: tuple[MaterialAllocation, ...]
    materials: tuple[tuple[MaterialReceipt, bytes], ...]
    candidate: tuple[bytes, str] | None
    assembly: CurrentFinalAssemblyContext | CurrentFinalAssemblyContextV2 | None
    asr: CurrentFinalAsrRead | None
    strict_materials: tuple[tuple[MaterialReceipt, bytes], ...]
    missing_facts: tuple[str, ...]
