"""Private diagnostic provenance. Neither data nor a content hash is authority."""

from dataclasses import dataclass
from typing import Literal

from pydantic import Field, model_validator

from video_creator.domain import contracts as c
from video_creator.domain.affected_recipe import AffectedRepairExecutionV2, AffectedRepairProposalV2, PlanRepairTargetsV2, RecipeSourceRef, ProductionDriverResourcesV3
from video_creator.domain.bundle import MaterialReceipt
from video_creator.domain.current_final_evidence import FinalModel, CurrentFinalEvidenceReadSet, FinalEvidenceControl
from video_creator.domain.registered_production import ProductionBinding

InformationCode = Literal['source_material_missing', 'source_mapping_incomplete', 'diagnostic_method_not_ready',
                          'analysis_operation_unsettled', 'analysis_inconclusive', 'competing_causes', 'finite_recipe_missing']
Component = Literal['cover', 'narration', 'mix', 'visual', 'ambient']
CheckKind = Literal['precision_boundary', 'cover_frame', 'narration_source', 'mix_source', 'visual_source', 'ambient_source']


class DiagnosticSourceMediaRefV1(FinalModel):
    artifact_id: c.Identifier
    asset_id: c.Identifier
    role: Literal['video', 'narration_audio', 'mixed_audio', 'cover', 'shot_clip']
    sha256: c.Sha256
    size: int = Field(gt=0, strict=True)
    media_type: str = Field(min_length=1, max_length=200)
    probe: c.MediaProbe | None
    source_operation_ids: tuple[c.Identifier, ...] = Field(min_length=1)
    intrinsic_range: c.MediaRange | None
    timeline_range: c.MediaRange | None
    mapping_refs: tuple[c.AudioMappingEvidenceRef, ...]
    shot_ids: tuple[c.Identifier, ...]

    @model_validator(mode='after')
    def actual_distinct(self):
        if len(set(self.source_operation_ids)) != len(self.source_operation_ids) or len(set(self.shot_ids)) != len(self.shot_ids):
            raise ValueError('Distinct actual source Operations and original shots required')
        return self


class DiagnosticOperationOutputRefV1(FinalModel):
    format: Literal['component-diagnostic-operation-output-v1']
    operation_id: c.Identifier
    input_sha256: c.Sha256
    observation_sha256: c.Sha256
    output_sha256: c.Sha256


class DiagnosticSampleRefV1(FinalModel):
    format: Literal['component-diagnostic-decoded-sample-v1']
    asset_id: c.Identifier
    source_sha256: c.Sha256
    source_range: c.MediaRange
    sample_sha256: c.Sha256
    sample_size: int = Field(gt=0, strict=True)
    decoder_ref: RecipeSourceRef


class DiagnosticMetadataRef(FinalModel):
    record_id: str = Field(min_length=1, max_length=512)
    content_sha256: c.Sha256
    size: int = Field(gt=0, le=2 * 1024 * 1024, strict=True)


DiagnosticEvidenceRef = c.RevisionRef | MaterialReceipt | DiagnosticSourceMediaRefV1 | DiagnosticOperationOutputRefV1 | DiagnosticSampleRefV1 | DiagnosticMetadataRef


class ComponentDiagnosticMethodRegistrationV1(FinalModel):
    method_id: c.Identifier
    version: c.Identifier
    implementation_source_refs: tuple[RecipeSourceRef, ...] = Field(min_length=1)
    rule_template_sha256: c.Sha256
    route: c.CapabilityRoute
    model_binding: c.Identifier | None
    check_kinds: tuple[CheckKind, ...] = Field(min_length=1)

    @model_validator(mode='after')
    def bounded_method(self):
        if (len(set(self.check_kinds)) != len(self.check_kinds)
                or len({ref.resource_name for ref in self.implementation_source_refs}) != len(self.implementation_source_refs)):
            raise ValueError('Distinct actual method checks and indexed sources required')
        route = self.route
        if route.capability == 'media_diagnosis':
            if route.source != 'owned_local' or route.credential_ref is not None or route.max_operation_cost.units() != 0 or self.model_binding is not None:
                raise ValueError('Bounded local diagnosis is credential-free and actually zero-cost')
        elif route.capability != 'text' or self.model_binding is None:
            raise ValueError('Only the original text model or bounded local diagnosis capability is valid')
        return self


class ComponentDiagnosticMethodRefV1(ComponentDiagnosticMethodRegistrationV1):
    resource_manifest_sha256: c.Sha256
    runtime_manifest_sha256: c.Sha256


class DiagnosticMethodsV1(FinalModel):
    format: Literal['registered-component-diagnostic-methods-v1']
    methods: tuple[ComponentDiagnosticMethodRegistrationV1, ...] = Field(min_length=1, max_length=16)

    @model_validator(mode='after')
    def unique_methods(self):
        if len({method.method_id for method in self.methods}) != len(self.methods):
            raise ValueError('Distinct original installed method IDs required')
        return self


class ProductionDriverResourcesDiagnosticV1(ProductionDriverResourcesV3):
    format: Literal['registered-production-driver-resources-v3-diagnostic-v1']
    diagnosis: DiagnosticMethodsV1


class ComponentDiagnosticCheckV1(FinalModel):
    check_id: c.Identifier
    check_kind: CheckKind
    component: Component | None
    source_refs: tuple[DiagnosticEvidenceRef, ...] = Field(min_length=1)
    shot_ids: tuple[c.Identifier, ...]
    intrinsic_range: c.MediaRange | None
    timeline_range: c.MediaRange | None
    expected_ref: DiagnosticEvidenceRef
    observed_ref: DiagnosticEvidenceRef
    observed_result: Literal['matches', 'differs', 'unavailable']
    assertion_status: Literal['supported', 'not_supported', 'undetermined']
    evidence_strength: Literal['deterministic_observation', 'attributed_model_assessment']
    limitations: tuple[str, ...]
    uncertainty_codes: tuple[InformationCode, ...]

    @model_validator(mode='after')
    def fixed_component(self):
        expected = {'precision_boundary': None, 'cover_frame': 'cover', 'narration_source': 'narration',
                    'mix_source': 'mix', 'visual_source': 'visual', 'ambient_source': 'ambient'}[self.check_kind]
        if expected != self.component or len(set(self.shot_ids)) != len(self.shot_ids):
            raise ValueError('Exact original check kind/component and distinct shots required')
        if self.observed_result == 'unavailable' and self.assertion_status == 'supported':
            raise ValueError('An unobserved source cannot support a component conclusion')
        return self


class ComponentDiagnosticObservationV1(FinalModel):
    format: Literal['current-component-diagnostic-observation-v1']
    input_key_sha256: c.Sha256
    method_ref: ComponentDiagnosticMethodRefV1
    analysis_operation_ids: tuple[c.Identifier, ...] = Field(min_length=1)
    checks: tuple[ComponentDiagnosticCheckV1, ...] = Field(min_length=1)
    limitations: tuple[str, ...]

    @model_validator(mode='after')
    def finite_observations(self):
        if (len(set(self.analysis_operation_ids)) != len(self.analysis_operation_ids)
                or len({check.check_id for check in self.checks}) != len(self.checks)
                or any(check.check_kind not in self.method_ref.check_kinds for check in self.checks)):
            raise ValueError('Actual distinct Operations and checks from the original method required')
        c.reject_secrets(self.model_dump(mode='json'))
        return self


class ComponentDiagnosisRefV1(FinalModel):
    format: Literal['current-component-diagnosis-ref-v1']
    record_id: c.Identifier
    content_sha256: c.Sha256
    size: int = Field(gt=0, le=2 * 1024 * 1024, strict=True)
    input_key_sha256: c.Sha256


class DiagnosticAnalysisOperationRefV1(FinalModel):
    operation_id: c.Identifier
    input_sha256: c.Sha256
    route_sha256: c.Sha256
    observation_sha256: c.Sha256
    output_sha256: c.Sha256


class ComponentDiagnosticFactV1(FinalModel):
    format: Literal['current-component-diagnostic-fact-v1']
    input_key_sha256: c.Sha256
    binding: ProductionBinding
    parent_preparation_id: c.Identifier
    parent_intent_sha256: c.Sha256
    authored_fence: int = Field(gt=0, strict=True)
    candidate_manifest_file_sha256: c.Sha256 | None
    creative_revision_refs: tuple[c.RevisionRef, ...] = Field(min_length=1)
    quality_ref: c.RevisionRef
    request_sha256: c.Sha256
    registration_sha256: c.Sha256
    resource_manifest_sha256: c.Sha256
    runtime_manifest_sha256: c.Sha256
    precision_report_ref: MaterialReceipt | None
    failure_event_kind: Literal['precision_timing', 'component_observation']
    source_media_refs: tuple[DiagnosticSourceMediaRefV1, ...] = Field(min_length=1)
    method_ref: ComponentDiagnosticMethodRefV1
    analysis_operation_refs: tuple[DiagnosticAnalysisOperationRefV1, ...] = Field(min_length=1)
    checks: tuple[ComponentDiagnosticCheckV1, ...] = Field(min_length=1)
    analysis_limitations: tuple[str, ...]
    result: Literal['timing_only', 'component_repair', 'information_required', 'no_component_failure']
    failure_component: Component | None
    source_shot_ids: tuple[c.Identifier, ...]
    speech_change: Literal['required', 'not_required', 'undetermined']
    ambient_change: Literal['required', 'not_required', 'undetermined']
    affected_artifact_ids: tuple[c.Identifier, ...]
    failed_unit_ids: tuple[c.Identifier, ...]
    intrinsic_ranges: tuple[c.MediaRange, ...]
    timeline_ranges: tuple[c.MediaRange, ...]
    uncertainty_codes: tuple[InformationCode, ...]
    information_requests: tuple[InformationCode, ...]

    @model_validator(mode='after')
    def exact_failure(self):
        if ((self.result == 'component_repair') != (self.failure_component is not None)
                or self.result == 'component_repair' and not self.affected_artifact_ids
                or self.failure_event_kind == 'precision_timing' and self.precision_report_ref is None
                or self.precision_report_ref is None and self.failed_unit_ids):
            raise ValueError('Actual independent precision and finite component diagnosis are distinct')
        for values in (self.source_shot_ids, self.affected_artifact_ids, self.failed_unit_ids):
            if len(set(values)) != len(values):
                raise ValueError('Distinct actual finite failed sources required')
        return self


@dataclass(frozen=True, eq=False)
class RegisteredComponentDiagnosisInputsV1:
    input_key_sha256: str
    binding: ProductionBinding
    parent_preparation_id: str
    parent_intent_sha256: str
    parent: CurrentFinalEvidenceReadSet
    precision_report_ref: MaterialReceipt | None
    precision_report_bytes: bytes | None
    failed_unit_ids: tuple[str, ...]
    source_media_refs: tuple[DiagnosticSourceMediaRefV1, ...]
    diagnostic_method_refs: tuple[ComponentDiagnosticMethodRefV1, ...]
    analysis_intents: tuple[c.OperationIntent, ...]


@dataclass(frozen=True, eq=False)
class RegisteredComponentDiagnosisV1:
    ref: ComponentDiagnosisRefV1
    fact: ComponentDiagnosticFactV1


class DiagnosticRepairSourceV1(FinalModel):
    diagnostic_ref: ComponentDiagnosisRefV1
    precision_report_ref: MaterialReceipt | None
    affected_artifact_ids: tuple[c.Identifier, ...] = Field(min_length=1)
    failed_unit_ids: tuple[c.Identifier, ...]
    allowed_action: Literal['regenerate_affected_media']


class CurrentFinalDiagnosticSnapshotV1(FinalModel):
    preparation_id: c.Identifier
    preparation_intent_sha256: c.Sha256
    candidate_manifest_file_sha256: c.Sha256 | None
    ready_material_refs: tuple[MaterialReceipt, ...]
    diagnostic_ref: ComponentDiagnosisRefV1 | None
    state: Literal['waiting_diagnosis', 'repair_required']
    reason_code: c.Identifier
    information_requests: tuple[InformationCode, ...]
    repair: DiagnosticRepairSourceV1 | None

    @model_validator(mode='after')
    def supported_repair(self):
        if ((self.state == 'repair_required') != (self.repair is not None)
                or self.repair is not None and self.repair.diagnostic_ref != self.diagnostic_ref
                or any(ref.preparation_id != self.preparation_id for ref in self.ready_material_refs)):
            raise ValueError('Diagnostic repair requires exactly its real recorded source')
        return self


class CurrentFinalDiagnosticJournalV1(FinalModel):
    format: Literal['current-production-final-evidence-diagnostic-v1']
    binding: ProductionBinding
    snapshot: CurrentFinalDiagnosticSnapshotV1
    control: FinalEvidenceControl
    blocked_at_us: int = Field(gt=0, strict=True)
    last_transition_at_us: int = Field(gt=0, strict=True)

    @model_validator(mode='after')
    def monotonic(self):
        if self.last_transition_at_us < self.blocked_at_us:
            raise ValueError('Original blocked time cannot be reset')
        return self


@dataclass(frozen=True)
class CurrentFinalDiagnosticContinuationV1:
    binding: ProductionBinding
    snapshot: CurrentFinalDiagnosticSnapshotV1
    resume_mode: Literal['retry_final_validation', 'repair']
    execution_fence: int


@dataclass(frozen=True, eq=False)
class AffectedRepairExecutionDiagnosedV1(AffectedRepairExecutionV2):
    source_report_ref: MaterialReceipt | None
    diagnostic_ref: ComponentDiagnosisRefV1
    input_key_sha256: str

    @property
    def affected_shot_ids(self):
        return self.impacted_shot_ids


class ComponentOnlyFailureSourceV1(FinalModel):
    format: Literal['component_diagnosis']
    diagnostic_ref: ComponentDiagnosisRefV1
    precision_report_ref: None


class PrecisionComponentFailureSourceV1(FinalModel):
    format: Literal['precision_with_component_diagnosis']
    diagnostic_ref: ComponentDiagnosisRefV1
    precision_report_ref: MaterialReceipt


class AffectedDiagnosticSourceV1(FinalModel):
    format: Literal['current-final-affected-execution-v2-diagnostic-v1']
    binding: ProductionBinding
    parent_preparation_id: c.Identifier
    parent_intent_sha256: c.Sha256
    source_report_ref: MaterialReceipt | None
    diagnostic_ref: ComponentDiagnosisRefV1
    input_key_sha256: c.Sha256
    failure_source: ComponentOnlyFailureSourceV1 | PrecisionComponentFailureSourceV1 = Field(discriminator='format')
    affected_artifact_ids: tuple[c.Identifier, ...] = Field(min_length=1)
    failed_unit_ids: tuple[c.Identifier, ...]
    requested_action: Literal['regenerate_affected_media']
    changed_media_roles: tuple[Literal['video','narration_audio','mixed_audio','cover'], ...]
    affected_shot_ids: tuple[c.Identifier, ...]
    proposal: AffectedRepairProposalV2
    plan_ref: c.RevisionRef
    quality_ref: c.RevisionRef
    repair_targets: PlanRepairTargetsV2
    route_bindings: dict[c.Identifier, c.CapabilityRoute]
    resource_manifest_sha256: c.Sha256
    runtime_manifest_sha256: c.Sha256

    @model_validator(mode='after')
    def exact_source(self):
        p=self.proposal
        if (self.failure_source.diagnostic_ref!=self.diagnostic_ref
                or self.failure_source.precision_report_ref!=self.source_report_ref
                or self.input_key_sha256!=self.diagnostic_ref.input_key_sha256
                or (self.parent_preparation_id,self.affected_artifact_ids,self.failed_unit_ids,
                    self.changed_media_roles,self.affected_shot_ids)!=(p.parent_preparation_id,
                    p.affected_artifact_ids,p.failed_unit_ids,p.changed_media_roles,p.impacted_shot_ids)):
            raise ValueError('Exact sole diagnosis, tagged precision source and proposal binding required')
        return self
