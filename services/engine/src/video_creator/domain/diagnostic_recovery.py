"""Private diagnostic history and held selection; none confers execution scope."""
from dataclasses import dataclass
from typing import Literal

from pydantic import Field, model_validator

from video_creator.domain import contracts as c
from video_creator.domain.bundle import MaterialReceipt
from video_creator.domain.component_diagnosis import (
    DiagnosticMetadataRef, ComponentDiagnosisRefV1, RegisteredComponentDiagnosisInputsV1,
    DiagnosticSourceMediaRefV1, ComponentDiagnosticMethodRefV1,
)
from video_creator.domain.current_final_evidence import FinalModel, CurrentFinalEvidenceSnapshot
from video_creator.domain.registered_production import ProductionBinding


class RegisteredDiagnosticInputRef(DiagnosticMetadataRef):
    input_key_sha256: c.Sha256


class DiagnosticFeedbackCompletion(FinalModel):
    kind: Literal['feedback']
    ref: c.RevisionRef


class DiagnosticMaterialCompletion(FinalModel):
    kind: Literal['ready_material']
    ref: MaterialReceipt


class DiagnosticResourceCompletion(FinalModel):
    kind: Literal['qualified_resource']
    ref: DiagnosticMetadataRef


CompletionRef = DiagnosticFeedbackCompletion | DiagnosticMaterialCompletion | DiagnosticResourceCompletion


class DiagnosticStableInputV2(FinalModel):
    format: Literal['current-component-diagnostic-input-v2']
    binding: ProductionBinding
    parent_preparation_id: c.Identifier
    parent_intent_sha256: c.Sha256
    candidate_manifest_file_sha256: c.Sha256 | None
    creative_revision_refs: tuple[c.RevisionRef, ...]
    quality_ref: c.RevisionRef
    source_media_refs: tuple[DiagnosticSourceMediaRefV1, ...]
    audio_mappings: tuple[c.AudioTimelineMapping, ...]
    precision_report_ref: MaterialReceipt | None
    diagnostic_method_refs: tuple[ComponentDiagnosticMethodRefV1, ...]
    completion_source_refs: tuple[CompletionRef, ...] = Field(min_length=1)

    @model_validator(mode='after')
    def distinct_completion_sources(self):
        from video_creator.domain.plan_repair_targets import plan_payload_sha256
        values=tuple(plan_payload_sha256(value) for value in self.completion_source_refs)
        if len(values)!=len(set(values)):
            raise ValueError('Actual completion refs cannot duplicate or salt the input')
        return self


class RegisteredDiagnosticEnvelopeV2(FinalModel):
    format: Literal['registered-component-diagnostic-input-v2']
    stable: DiagnosticStableInputV2
    analysis_intents: tuple[c.OperationIntent, ...]


class QualityFailureFacts(FinalModel):
    quality_material_ref: MaterialReceipt
    quality_body_sha256: c.Sha256
    quality_ref: c.RevisionRef
    required_check_ids: tuple[str, ...]
    incomplete_check_ids: tuple[str, ...]


class DiagnosticResumeContext(FinalModel):
    work_kind: Literal['reuse_record', 'analyse_changed_input', 'final_validation_after_analysis']
    previous_waiting_journal_sha256: c.Sha256
    previous_diagnostic_ref: ComponentDiagnosisRefV1 | None
    registered_input_ref: RegisteredDiagnosticInputRef
    completion_source_refs: tuple[CompletionRef, ...]
    expected_diagnostic_ref: ComponentDiagnosisRefV1 | None


class DiagnosticSelectionEvidence(FinalModel):
    selection_kind: Literal['first_select', 'retain', 'successor']
    old_selected_body: str | None
    old_selected_ref: ComponentDiagnosisRefV1 | None
    new_selected_body: str
    new_selected_ref: ComponentDiagnosisRefV1
    new_registered_input_ref: RegisteredDiagnosticInputRef
    old_journal_sha256: c.Sha256 | None
    previous_committed_source_ref: DiagnosticMetadataRef | None

    @model_validator(mode='after')
    def exact_bodies(self):
        if (self.old_selected_body is None) != (self.old_selected_ref is None):
            raise ValueError('Original selected absence and body are one observation')
        if self.old_selected_body is not None and ComponentDiagnosisRefV1.model_validate_json(self.old_selected_body) != self.old_selected_ref:
            raise ValueError('Exact original selected body required')
        if ComponentDiagnosisRefV1.model_validate_json(self.new_selected_body) != self.new_selected_ref:
            raise ValueError('Exact new selected body required')
        if self.new_registered_input_ref.input_key_sha256 != self.new_selected_ref.input_key_sha256:
            raise ValueError('New fact must retain its registered input')
        return self


class CurrentFinalDiagnosticSourceV1(FinalModel):
    format: Literal['current-final-diagnostic-source-v1']
    binding: ProductionBinding
    journal_sha256: c.Sha256
    snapshot_sha256: c.Sha256
    preparation_id: c.Identifier
    preparation_intent_sha256: c.Sha256
    candidate_manifest_file_sha256: c.Sha256 | None
    ready_material_refs: tuple[MaterialReceipt, ...]
    origin_kind: Literal['precision_failure', 'evidence_wait', 'quality_incomplete',
        'verified_then_diagnostic_block', 'legacy_diagnostic_block']
    original_snapshot: CurrentFinalEvidenceSnapshot | None
    quality_failure: QualityFailureFacts | None
    diagnostic_ref: ComponentDiagnosisRefV1 | None
    diagnostic_input_key_sha256: c.Sha256 | None
    previous_source_ref: DiagnosticMetadataRef | None
    resume_context: DiagnosticResumeContext | None
    authored_fence: int = Field(gt=0, strict=True)

    @model_validator(mode='after')
    def actual_origin(self):
        if self.origin_kind in {'precision_failure', 'evidence_wait'} and self.original_snapshot is None:
            raise ValueError('Original complete failure snapshot required')
        if (self.origin_kind == 'quality_incomplete') != (self.quality_failure is not None):
            raise ValueError('QC origin requires its accurate throw-site facts')
        if self.origin_kind in {'quality_incomplete', 'verified_then_diagnostic_block'} and self.original_snapshot is not None:
            raise ValueError('Success/QC marker is not an original precision snapshot')
        if (self.diagnostic_ref is None) != (self.diagnostic_input_key_sha256 is None):
            raise ValueError('Diagnostic input and explicit reference must agree')
        if self.diagnostic_ref and self.diagnostic_ref.input_key_sha256 != self.diagnostic_input_key_sha256:
            raise ValueError('Original diagnosis input changed')
        return self


class CurrentFinalDiagnosticSourceV2(CurrentFinalDiagnosticSourceV1):
    format: Literal['current-final-diagnostic-source-v2']
    selection_evidence: DiagnosticSelectionEvidence

    @model_validator(mode='after')
    def selected_source(self):
        if self.selection_evidence.new_selected_ref != self.diagnostic_ref:
            raise ValueError('Source must carry exactly its committed selection')
        return self


class SelectedChildDiagnosticTransitionEvidence(FinalModel):
    parent_preparation_id: c.Identifier
    parent_intent_sha256: c.Sha256
    child_preparation_id: c.Identifier
    child_intent_sha256: c.Sha256
    parent_journal_body: str = Field(min_length=1, max_length=1024 * 1024)
    parent_journal_sha256: c.Sha256
    parent_source_ref: DiagnosticMetadataRef | None
    parent_selected_body: str | None
    parent_selected_ref: ComponentDiagnosisRefV1 | None
    affected_command_ref: DiagnosticMetadataRef
    child_lineage_ref: DiagnosticMetadataRef
    parent_failure_snapshot_sha256: c.Sha256
    authored_fence: int = Field(gt=0, strict=True)

    @model_validator(mode='after')
    def exact_parent_body(self):
        import hashlib
        if hashlib.sha256(self.parent_journal_body.encode('utf-8')).hexdigest() != self.parent_journal_sha256:
            raise ValueError('Exact historical parent journal bytes required')
        if (self.parent_selected_body is None) != (self.parent_selected_ref is None):
            raise ValueError('Parent selected absence and body are one observation')
        if self.parent_selected_body is not None and ComponentDiagnosisRefV1.model_validate_json(self.parent_selected_body) != self.parent_selected_ref:
            raise ValueError('Exact historical parent selection required')
        if self.parent_source_ref is None and self.parent_selected_ref is not None:
            raise ValueError('Diagnosed parent requires its original source')
        if self.parent_preparation_id == self.child_preparation_id:
            raise ValueError('A transition must name the actual distinct child')
        return self


class FiniteDiagnosticTerminalEvidence(FinalModel):
    reason: Literal['revision_limit_exhausted']
    revision_cycles: int = Field(ge=0, strict=True)
    request_revision_limit: int = Field(ge=0, strict=True)
    approved_plan_ref: c.RevisionRef | None
    approved_plan_revision_limit: int | None = Field(ge=0, strict=True)
    effective_revision_limit: int = Field(ge=0, strict=True)
    requested_action: Literal['realignment', 'regenerate_affected_media']
    request_sha256: c.Sha256
    authored_fence: int = Field(gt=0, strict=True)
    committed_at_us: int = Field(gt=0, strict=True)

    @model_validator(mode='after')
    def actual_cap(self):
        if (self.approved_plan_ref is None) != (self.approved_plan_revision_limit is None):
            raise ValueError('The narrower approved plan cap needs its original reference')
        limit = self.request_revision_limit
        if self.approved_plan_revision_limit is not None:
            limit = min(limit, self.approved_plan_revision_limit)
        if self.effective_revision_limit != limit or self.revision_cycles < limit:
            raise ValueError('Only an actually exhausted minimum cap is terminal')
        return self


class CurrentFinalDiagnosticSourceV3(CurrentFinalDiagnosticSourceV2):
    format: Literal['current-final-diagnostic-source-v3']
    selected_child_transition: SelectedChildDiagnosticTransitionEvidence | None
    terminal_failure: FiniteDiagnosticTerminalEvidence | None

    @model_validator(mode='after')
    def actual_transition_or_terminal(self):
        child = self.selected_child_transition
        if child is None and self.terminal_failure is None:
            raise ValueError('V3 must record an actual child transition or finite terminal')
        if child is not None and (self.preparation_id != child.child_preparation_id
                or self.preparation_intent_sha256 != child.child_intent_sha256
                or self.selection_evidence.old_journal_sha256 != child.parent_journal_sha256
                or self.selection_evidence.previous_committed_source_ref != child.parent_source_ref
                or self.selection_evidence.old_selected_ref not in (None, self.diagnostic_ref)):
            raise ValueError('Child current selection cannot borrow the parent selection')
        return self


@dataclass(frozen=True, eq=False)
class PreparedSelectedChildDiagnosticTransition:
    evidence: SelectedChildDiagnosticTransitionEvidence
    command_body: str
    child_preparation_id: str


@dataclass(frozen=True, eq=False)
class RegisteredComponentDiagnosisInputsV2(RegisteredComponentDiagnosisInputsV1):
    completion_source_refs: tuple[CompletionRef, ...]
    registered_input_ref: RegisteredDiagnosticInputRef


@dataclass(frozen=True, eq=False)
class PreparedDiagnosticSelection:
    binding: ProductionBinding
    preparation_id: str
    recorded: object
    registered_input_ref: RegisteredDiagnosticInputRef
    selection_kind: str
    old_selected_body: str | None
    old_journal_body: str | None
    old_source_body: str | None
    source_ref: DiagnosticMetadataRef | None
    child_transition: PreparedSelectedChildDiagnosticTransition | None = None


@dataclass(frozen=True, eq=False)
class HeldDiagnosticOutcome:
    kind: str
    assessment: object | None
    verified: object | None
    quality_failure: QualityFailureFacts | None


@dataclass(frozen=True, eq=False)
class CurrentDiagnosticSourceRead:
    source: CurrentFinalDiagnosticSourceV1 | CurrentFinalDiagnosticSourceV2 | CurrentFinalDiagnosticSourceV3
    source_ref: DiagnosticMetadataRef
    execution_fence: int


@dataclass(frozen=True, eq=False)
class DiagnosticResumeProbe:
    binding: ProductionBinding
    preparation_id: str
    journal_body: str
    source: CurrentDiagnosticSourceRead
    completion_source_refs: tuple[CompletionRef, ...]
    registered_input_ref: RegisteredDiagnosticInputRef
    work_kind: str
    expected_diagnostic_ref: ComponentDiagnosisRefV1 | None


class CurrentQualityFailure(Exception):
    """Only the original exact QC throw site can produce this held marker."""
    def __init__(self, original_error, outcome):
        self.original_error = original_error
        self.outcome = outcome
