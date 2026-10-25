"""ADR0075 sole local 0.4 contracts. Data and selections grant no authority."""
from typing import Literal

from pydantic import Field, model_validator

from video_creator.domain import contracts as c
from video_creator.domain.errors import EngineError
from video_creator.domain.local_material_production import (
    LocalMaterialPlanV1, LocalProductionRequestRef, _parse, local_material_sha256,
)
from video_creator.domain.registered_production import PrivateModel, ProductionBinding
from video_creator.domain.current_final_evidence import CurrentFinalAssemblyContextV2

LOCAL_SCHEMA_VERSION = '0.4.0-candidate'
LOCAL_PROFILE = 'local-material-bundle-v1'
MASTER_ORDER = ('video', 'narration_audio', 'mixed_audio', 'cover')
LOCAL_REQUIRED_FILES = frozenset({
    'Creative/production-plan.json', 'Text/approved-script.json', 'Checks/quality-report.json',
    'Checks/local-master-selection.json', 'Checks/local-speech-evidence.json',
    'Semantics/work-summary.json', 'Semantics/source-bindings.json',
    'Semantics/semantic-segments.jsonl', 'Semantics/rag-chunks.jsonl',
})


class LocalMasterSelectionV1(PrivateModel):
    format: Literal['local-master-selection-v1'] = 'local-master-selection-v1'
    request_ref: LocalProductionRequestRef
    plan_revision_ref: c.RevisionRef
    content_kind: Literal['video', 'audio']
    master_roles: tuple[Literal['video', 'narration_audio', 'mixed_audio', 'cover'], ...]
    outputs: tuple[c.OutputRole, ...]
    narration_binding_ids: tuple[c.Identifier, ...]
    script_purpose: Literal['spoken_script', 'production_script']

    @model_validator(mode='after')
    def exact_roles(self):
        if self.plan_revision_ref.kind != 'plan' or not self.master_roles:
            raise ValueError('Selection requires its actual approved plan and applicable masters')
        if self.master_roles != tuple(role for role in MASTER_ORDER if role in self.master_roles):
            raise ValueError('Master roles are unique and in the fixed order')
        video = self.content_kind == 'video'
        if video != ('video' in self.master_roles) or video != ('cover' in self.master_roles):
            raise ValueError('Only video selections contain video and cover')
        if not video and 'mixed_audio' not in self.master_roles:
            raise ValueError('Audio selections require real mixed audio')
        narration = bool(self.narration_binding_ids)
        if narration != ('narration_audio' in self.master_roles) or narration != (self.script_purpose == 'spoken_script'):
            raise ValueError('Narration and script purpose retain actual narration bindings')
        if len(set(self.outputs)) != len(self.outputs) or len(set(self.narration_binding_ids)) != len(self.narration_binding_ids):
            raise ValueError('Output and narration identities are unique')
        return self


def select_local_masters(request: c.ProductionRequestAny, plan: LocalMaterialPlanV1,
                         plan_revision_ref: c.RevisionRef) -> LocalMasterSelectionV1:
    """Pure deterministic projection; caller must separately prove current plan approval."""
    if plan.outputs != request.outputs or plan_revision_ref.kind != 'plan':
        raise EngineError('local_selection_request_conflict', 'Original request and plan outputs differ.', 409)
    video = 'video' in request.outputs
    audio = bool(plan.timeline.audio_tracks)
    if (video and not plan.timeline.shots) or (not video and not audio):
        raise EngineError('local_media_input_required', 'Actual applicable visual or audio inputs are required.', 422)
    bindings = {value.binding_id: value for value in plan.input_bindings}
    narration = tuple(dict.fromkeys(track.input_binding_id for track in plan.timeline.audio_tracks
                                   if bindings[track.input_binding_id].usage == 'narration'))
    roles = tuple(role for role in MASTER_ORDER if
                  (role in {'video', 'cover'} and video) or
                  (role == 'mixed_audio' and audio) or
                  (role == 'narration_audio' and bool(narration)))
    for role in request.outputs:
        applicable = (role not in {'video', 'narration_audio', 'mixed_audio', 'actual_transcript', 'subtitles'}
                      or (role == 'video' and video)
                      or (role == 'narration_audio' and bool(narration))
                      or (role in {'mixed_audio', 'actual_transcript', 'subtitles'} and audio))
        if not applicable:
            raise EngineError('local_output_not_applicable', f'Requested output {role} has no actual applicable input.', 422)
    return LocalMasterSelectionV1(request_ref=plan.request_ref, plan_revision_ref=plan_revision_ref,
        content_kind='video' if video else 'audio', master_roles=roles, outputs=request.outputs,
        narration_binding_ids=narration, script_purpose='spoken_script' if narration else 'production_script')


class CurrentProductionUpstreamResultV2(PrivateModel):
    format: Literal['current-production-upstream-v2'] = 'current-production-upstream-v2'
    profile: Literal['local-material-bundle-v1'] = LOCAL_PROFILE
    run_id: c.Identifier
    fencing_token: int = Field(gt=0, strict=True)
    state: Literal['masters_ready', 'waiting_user', 'waiting_authorization', 'resource_not_ready',
                   'denied', 'needs_reconciliation']
    selection: LocalMasterSelectionV1 | None
    media_roles: dict[Literal['video', 'narration_audio', 'mixed_audio', 'cover'], c.Identifier]
    blocker_code: c.Identifier | None = None

    @model_validator(mode='after')
    def actual_masters_only(self):
        if self.selection is not None and self.selection.request_ref.run_id != self.run_id:
            raise ValueError('Selection must belong to the same Run')
        if self.state == 'masters_ready':
            if (self.selection is None or tuple(self.media_roles) != self.selection.master_roles
                    or len(set(self.media_roles.values())) != len(self.media_roles)
                    or self.blocker_code is not None):
                raise ValueError('Ready mapping is the exact ordered distinct applicable master set')
        elif self.media_roles:
            raise ValueError('A blocked result cannot claim masters')
        c.reject_secrets(self.model_dump(mode='json'))
        return self


class CurrentProductionBlockerJournalV2(PrivateModel):
    format: Literal['current-production-blocker-v2'] = 'current-production-blocker-v2'
    binding: ProductionBinding
    result: CurrentProductionUpstreamResultV2
    blocked_at_us: int = Field(gt=0, strict=True)

    @model_validator(mode='after')
    def real_wait(self):
        if (self.result.state not in {'waiting_authorization', 'resource_not_ready'}
                or self.result.media_roles or not self.result.blocker_code
                or self.result.run_id != self.binding.run_id):
            raise ValueError('Only original same-Run resource or authorization waits are journalled')
        if self.result.selection is not None:
            ref = self.result.selection.request_ref
            if (ref.instance_id, ref.production_id, ref.request_revision_id, ref.request_sha256) != (
                    self.binding.instance_id, self.binding.production_id,
                    self.binding.request_revision_id, self.binding.request_sha256):
                raise ValueError('Selection must keep the original binding request')
        return self


class LocalSpeechEvidenceV1(c.Contract):
    format: Literal['local-speech-evidence-v1'] = 'local-speech-evidence-v1'
    state: Literal['speech_observed', 'no_speech_observed', 'no_audio_observed']
    input_audio_asset_id: c.Identifier | None
    input_audio_sha256: c.Sha256 | None
    transcript_artifact_id: c.Identifier | None
    alignment_artifact_id: c.Identifier | None
    subtitle_artifact_ids: tuple[c.Identifier, ...]
    method_refs: tuple[c.Identifier, ...]
    proof_artifact_ids: tuple[c.Identifier, ...]

    @model_validator(mode='after')
    def evidence_shape(self):
        if not self.method_refs or not self.proof_artifact_ids:
            raise ValueError('Absence and presence both require actual indexed method/proof sources')
        for values in (self.method_refs, self.proof_artifact_ids, self.subtitle_artifact_ids):
            if len(set(values)) != len(values):
                raise ValueError('Evidence identities are distinct')
        if self.state == 'no_audio_observed':
            if any(value is not None for value in (self.input_audio_asset_id, self.input_audio_sha256,
                    self.transcript_artifact_id, self.alignment_artifact_id)) or self.subtitle_artifact_ids:
                raise ValueError('No-audio evidence cannot contain fake audio or speech materials')
        elif self.input_audio_asset_id is None or self.input_audio_sha256 is None or self.transcript_artifact_id is None:
            raise ValueError('Actual audio states require original audio and transcript')
        elif self.state == 'speech_observed' and (self.alignment_artifact_id is None or len(self.subtitle_artifact_ids) != 2):
            raise ValueError('Observed speech requires complete alignment and both actual subtitle materials')
        elif self.state == 'no_speech_observed' and self.alignment_artifact_id is not None:
            raise ValueError('No-speech evidence cannot fabricate alignment units')
        return self


class LocalActualTranscriptDocumentV1(c.Contract):
    format: Literal['local-actual-transcript-v1'] = 'local-actual-transcript-v1'
    schema_version: Literal['0.4.0-candidate'] = LOCAL_SCHEMA_VERSION
    transcript: c.ActualTranscriptRevision
    alignment: c.AlignmentRevision | c.AlignmentRevisionV03 | None
    subtitles: c.SubtitleTrack | None
    speech_evidence_artifact_id: c.Identifier


class LocalCheckApplicabilityV1(c.Contract):
    check_id: c.Identifier
    status: Literal['applicable', 'not_applicable']
    reason_code: c.Identifier
    proof_artifact_ids: tuple[c.Identifier, ...] = Field(min_length=1)


class LocalBundleQualityEvidenceV1(c.BundleQualityEvidence):
    schema_version: Literal['0.4.0-candidate'] = LOCAL_SCHEMA_VERSION
    speech_evidence_artifact_id: c.Identifier
    alignment_report_artifact_ids: tuple[c.Identifier, ...]
    applicability: tuple[LocalCheckApplicabilityV1, ...]

    @model_validator(mode='after')
    def unique_checks(self):
        if (len({value.check_id for value in self.applicability}) != len(self.applicability)
                or len(set(self.alignment_report_artifact_ids)) != len(self.alignment_report_artifact_ids)):
            raise ValueError('Applicability and report identities are distinct')
        return self


class SemanticSegmentLocalV2(c.SemanticSegmentV1):
    record_format_version: Literal[2] = 2
    timeline_range: c.MediaRange
    video_asset_id: c.Identifier | None
    video_range: c.MediaRange | None
    alignment_revision_id: c.Identifier | None

    @model_validator(mode='after')
    def applicable_media(self):
        if (self.video_asset_id is None) != (self.video_range is None):
            raise ValueError('Actual video identity and range are paired')
        if self.video_asset_id is None and (self.frame_evidence_refs or self.shot_revision_ids):
            raise ValueError('Audio-only semantics cannot fabricate frames or shots')
        if not self.speech_text and (self.transcript_unit_refs or self.alignment_revision_id is not None):
            raise ValueError('No-speech semantics cannot fabricate transcript or alignment identities')
        return self


class RagChunkLocalV2(c.RagChunk):
    record_format_version: Literal[2] = 2
    chunk_type: Literal['work_summary', 'speech_segment', 'visual_segment', 'audio_segment']

    @model_validator(mode='after')
    def applicable_media(self):
        if self.chunk_type == 'audio_segment' and (self.video_ranges or not self.audio_spans):
            raise ValueError('Audio segment requires actual audio spans and no fake video ranges')
        if self.chunk_type == 'visual_segment' and not self.video_ranges:
            raise ValueError('Visual segment requires actual video ranges')
        return self


class ShotEvidenceLocalV1(c.ShotEvidence):
    pass


def local_shot_revision_id(plan_content_sha256: str, shot_id: str) -> str:
    return 'shot-' + local_material_sha256({'plan_content_sha256': plan_content_sha256, 'shot_id': shot_id})


def local_frame_time_us(frame: int, fps_num: int, fps_den: int) -> int:
    if type(frame) is not int or frame < 0 or type(fps_num) is not int or fps_num <= 0 or type(fps_den) is not int or fps_den <= 0:
        raise EngineError('local_frame_grid_invalid', 'Original positive integer frame grid is required.', 422)
    return (2 * frame * 1_000_000 * fps_den + fps_num) // (2 * fps_num)


class LocalVisualMappingRowV1(c.Contract):
    shot_id: c.Identifier
    input_binding_id: c.Identifier
    source_asset_id: c.Identifier
    source_sha256: c.Sha256
    source_media_range: c.MediaRange | None
    display_hold_us: c.PositiveInt | None
    timeline_range: c.MediaRange
    frame_start: c.NonnegativeInt
    frame_end: c.PositiveInt

    @model_validator(mode='after')
    def source_kind(self):
        if self.frame_end <= self.frame_start or (self.source_media_range is None) != (self.display_hold_us is not None):
            raise ValueError('Video source range and static display hold are exclusive')
        if self.display_hold_us is not None and self.display_hold_us != self.timeline_range.end_us - self.timeline_range.start_us:
            raise ValueError('Static display hold is the actual timeline duration')
        return self


class LocalVisualMappingDocumentV1(c.Contract):
    format: Literal['local-visual-mapping-v1'] = 'local-visual-mapping-v1'
    fps_num: c.PositiveInt
    fps_den: c.PositiveInt
    timeline_duration_us: c.PositiveInt
    rows: tuple[LocalVisualMappingRowV1, ...] = Field(min_length=1)

    @model_validator(mode='after')
    def frame_grid(self):
        if len({row.shot_id for row in self.rows}) != len(self.rows):
            raise ValueError('Visual mapping shot identities are unique')
        for row in self.rows:
            if (row.timeline_range.start_us, row.timeline_range.end_us) != (
                    local_frame_time_us(row.frame_start, self.fps_num, self.fps_den),
                    local_frame_time_us(row.frame_end, self.fps_num, self.fps_den)):
                raise ValueError('Approved timeline must retain exact integer frame boundaries')
            if row.timeline_range.end_us > self.timeline_duration_us:
                raise ValueError('Mapping exceeds the actual work duration')
        return self


class BundleManifestLocalV1(c.BundleManifest):
    schema_version: Literal['0.4.0-candidate'] = LOCAL_SCHEMA_VERSION
    bundle_format_version: Literal[2] = 2
    content_profile: Literal['local-material-bundle-v1'] = LOCAL_PROFILE
    request_format_version: Literal['0.2.0-candidate', '0.3.0-candidate'] | None
    selection_artifact_id: c.Identifier
    speech_evidence_artifact_id: c.Identifier
    visual_mapping_artifact_id: c.Identifier | None

    @model_validator(mode='after')
    def local_index(self):
        required = (self.selection_artifact_id, self.speech_evidence_artifact_id)
        if self.visual_mapping_artifact_id is not None:
            required += (self.visual_mapping_artifact_id,)
        if len(set(required)) != len(required) or not set(required) <= {item.artifact_id for item in self.artifacts}:
            raise ValueError('Local evidence refers to distinct actual indexed artifacts')
        kinds = [ref.kind for ref in self.creative_revision_refs]
        if not {'plan', 'script', 'quality'} <= set(kinds) or len(kinds) != len(set(kinds)):
            raise ValueError('Local bundle requires actual unique plan/script/quality Creative versions')
        return self


class DeliveryProjectionManifestLocalV1(c.DeliveryProjectionManifest):
    schema_version: Literal['0.4.0-candidate'] = LOCAL_SCHEMA_VERSION


class LocalFinalAssemblyContextV1(CurrentFinalAssemblyContextV2):
    """Private immutable assembly; original context fields and correction pair retained."""
    format: Literal['local-final-assembly-context-v1'] = 'local-final-assembly-context-v1'
    selection: LocalMasterSelectionV1
    asr_operation_id: c.Identifier | None

    @model_validator(mode='after')
    def distinct_original_ids(self):
        if (len(set(self.document_artifact_ids.values())) != len(self.document_artifact_ids)
                or len({value.artifact_id for value in self.media_artifacts}) != len(self.media_artifacts)
                or tuple(value.roles for value in self.media_artifacts) != tuple((role,) for role in self.selection.master_roles)
                or any(value.asset_id is None for value in self.media_artifacts)):
            raise ValueError('Local assembly must contain exactly actual selected masters and distinct documents')
        ref = self.selection.request_ref
        if (ref.instance_id, ref.production_id, ref.run_id, ref.request_revision_id, ref.request_sha256) != (
                self.binding.instance_id, self.binding.production_id, self.binding.run_id,
                self.binding.request_revision_id, self.binding.request_sha256):
            raise ValueError('Local assembly selection must retain the actual complete request binding')
        if ('mixed_audio' in self.selection.master_roles) != (self.asr_operation_id is not None):
            raise ValueError('Actual audio needs its real ASR source; silent work cannot fabricate one')
        c.reject_secrets(self.model_dump(mode='json'))
        return self


def parse_local_bundle_manifest(data: bytes) -> BundleManifestLocalV1:
    return _parse(data, BundleManifestLocalV1, 'local_bundle_manifest_invalid')
