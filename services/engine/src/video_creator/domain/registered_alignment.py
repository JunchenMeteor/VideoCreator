"""ADR0056 private canonical input data; parsing never supplies a permit."""

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from video_creator.domain import contracts as c
from video_creator.domain.affected_repair import AlignmentResourceSection, ForcedAlignmentRegistration
from video_creator.domain.bundle import MaterialReceipt
from video_creator.domain.current_final_evidence import AsrValidationContextRef, FinalModel
from video_creator.domain.registered_production import ProductionBinding


class AlignmentAudioSource(FinalModel):
    asset_id: c.Identifier
    sha256: c.Sha256
    size: int = Field(gt=0, strict=True)
    media_type: str = Field(min_length=1, max_length=200)
    input_track: c.AudioTrackRef
    mapping: c.AudioTimelineMapping
    mapping_content_sha256: c.Sha256

    @model_validator(mode='after')
    def original_clock(self):
        if (self.asset_id, self.sha256) != (self.input_track.asset_id, self.input_track.sha256):
            raise ValueError('Actual input track and complete audio identity differ')
        if self.mapping_content_sha256 != self.mapping.content_sha256:
            raise ValueError('Original complete mapping content identity required')
        return self


class AlignmentAsrSource(FinalModel):
    operation_id: c.Identifier
    input_sha256: c.Sha256
    route_sha256: c.Sha256
    staging_id: c.Identifier
    result_file_sha256: c.Sha256
    context_ref: AsrValidationContextRef
    context_file_sha256: c.Sha256


class AlignmentTranscriptSource(FinalModel):
    transcript: c.ActualTranscriptRevision
    approved_script_revision_ref: c.RevisionRef
    asr_source: AlignmentAsrSource


class ReadyAlignmentTranscriptSource(AlignmentTranscriptSource):
    ready_receipt: MaterialReceipt
    ready_file_sha256: c.Sha256


class AlignmentUnitSource(FinalModel):
    alignment_unit_id: c.Identifier
    transcript_unit_id: c.Identifier
    utterance_id: c.Identifier
    word_id: c.Identifier | None
    text: str = Field(min_length=1, max_length=50_000)
    scalar_start: int = Field(ge=0, strict=True)
    scalar_end: int = Field(gt=0, strict=True)
    predicted_range: c.MediaRange

    @model_validator(mode='after')
    def exact_scalar_span(self):
        if self.scalar_end <= self.scalar_start or self.scalar_end - self.scalar_start != len(self.text):
            raise ValueError('Unicode scalar half-open text span required')
        if any(0xD800 <= ord(character) <= 0xDFFF for character in self.text):
            raise ValueError('Unpaired surrogate is not a Unicode scalar')
        return self


class AlignmentRegistrationSource(FinalModel):
    registration: ForcedAlignmentRegistration
    route_sha256: c.Sha256
    resource_manifest_sha256: c.Sha256
    runtime_manifest_sha256: c.Sha256
    resources: AlignmentResourceSection
    worker_sha256: c.Sha256
    runtime_sha256: c.Sha256


class InitialAlignmentRequest(FinalModel):
    format: Literal['registered-initial-alignment-request-v1']
    binding: ProductionBinding
    preparation_id: c.Identifier
    preparation_intent_sha256: c.Sha256
    assembly_context_sha256: c.Sha256
    asr_source: AlignmentAsrSource
    audio: AlignmentAudioSource
    transcript: AlignmentTranscriptSource
    unit_sources: tuple[AlignmentUnitSource, ...] = Field(min_length=1)
    allowed_unit_ids: tuple[c.Identifier, ...] = Field(min_length=1)
    source_alignment_revision_id: c.Identifier
    source_alignment_content_sha256: c.Sha256
    alignment_registration: AlignmentRegistrationSource
    output_alignment_revision_id: c.Identifier

    @model_validator(mode='after')
    def full_initial_units(self):
        ids = tuple(unit.transcript_unit_id for unit in self.unit_sources)
        if len(set(ids)) != len(ids) or self.allowed_unit_ids != ids or self.transcript.asr_source != self.asr_source:
            raise ValueError('Exactly original complete ordered initial units and ASR source required')
        c.reject_secrets(self.model_dump(mode='json'))
        return self


class AffectedAlignmentRequest(FinalModel):
    format: Literal['registered-affected-alignment-request-v1']
    binding: ProductionBinding
    repair_command_sha256: c.Sha256
    parent_preparation_id: c.Identifier
    parent_intent_sha256: c.Sha256
    source_report_ref: MaterialReceipt
    audio: AlignmentAudioSource
    transcript: ReadyAlignmentTranscriptSource
    unit_sources: tuple[AlignmentUnitSource, ...] = Field(min_length=1)
    failed_unit_ids: tuple[c.Identifier, ...] = Field(min_length=1)
    allowed_unit_ids: tuple[c.Identifier, ...] = Field(min_length=1)
    source_alignment_revision_id: c.Identifier
    source_alignment_content_sha256: c.Sha256
    alignment_registration: AlignmentRegistrationSource
    output_alignment_revision_id: c.Identifier

    @model_validator(mode='after')
    def bounded_actual_units(self):
        ids = tuple(unit.transcript_unit_id for unit in self.unit_sources)
        if (len(set(ids)) != len(ids) or len(set(self.allowed_unit_ids)) != len(self.allowed_unit_ids)
                or tuple(identity for identity in ids if identity in self.allowed_unit_ids) != self.allowed_unit_ids
                or tuple(identity for identity in ids if identity in self.failed_unit_ids) != self.failed_unit_ids
                or not set(self.failed_unit_ids) <= set(self.allowed_unit_ids)):
            raise ValueError('Original ordered failed subset and necessary closed unit set required')
        c.reject_secrets(self.model_dump(mode='json'))
        return self


def alignment_request_bytes(request: InitialAlignmentRequest | AffectedAlignmentRequest) -> bytes:
    if type(request) not in {InitialAlignmentRequest, AffectedAlignmentRequest}:
        raise TypeError('Sole strict registered alignment request required')
    return json.dumps(request.model_dump(mode='json'), ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode('utf-8')


def alignment_request_sha256(request: InitialAlignmentRequest | AffectedAlignmentRequest) -> str:
    return hashlib.sha256(alignment_request_bytes(request)).hexdigest()
