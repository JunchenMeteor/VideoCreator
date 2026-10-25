"""Private finite repair data and service-held objects; none is a JSON permit."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Literal

from pydantic import Field, model_validator

from video_creator.domain import contracts as c
from video_creator.domain.bundle import MaterialReceipt
from video_creator.domain.current_final_evidence import CurrentFinalEvidenceReadSet, FinalModel
from video_creator.domain.registered_production import ProductionBinding

MediaRole = Literal['video', 'narration_audio', 'mixed_audio', 'cover']


class AffectedRepairProposal(FinalModel):
    format: Literal['current-affected-repair-proposal-v1']
    parent_preparation_id: c.Identifier
    affected_artifact_ids: tuple[c.Identifier, ...]
    failed_unit_ids: tuple[c.Identifier, ...]
    requested_action: Literal['realignment', 'regenerate_affected_media']
    changed_media_roles: tuple[MediaRole, ...]
    affected_shot_ids: tuple[c.Identifier, ...]

    @model_validator(mode='after')
    def actual_distinct_subset(self):
        for values in (self.affected_artifact_ids, self.failed_unit_ids, self.changed_media_roles, self.affected_shot_ids):
            if len(set(values)) != len(values):
                raise ValueError('Actual repair subsets are distinct')
        if not self.affected_artifact_ids or (self.requested_action == 'realignment' and self.changed_media_roles):
            raise ValueError('Realignment cannot regenerate media')
        if self.requested_action == 'regenerate_affected_media' and not self.changed_media_roles:
            raise ValueError('Actual changed media roles required')
        return self


@dataclass(frozen=True, eq=False)
class AffectedRepairExecution:
    binding: ProductionBinding
    execution_fence: int
    parent_preparation_id: str
    parent_intent_sha256: str
    repair_command_sha256: str
    source_report_ref: MaterialReceipt
    affected_artifact_ids: tuple[str, ...]
    failed_unit_ids: tuple[str, ...]
    requested_action: Literal['realignment', 'regenerate_affected_media']
    changed_media_roles: tuple[MediaRole, ...]
    affected_shot_ids: tuple[str, ...]


@dataclass(frozen=True, eq=False)
class AffectedMasterObservation:
    binding: ProductionBinding
    parent_preparation_id: str
    repair_command_sha256: str
    step_key: str
    step_input_sha256: str
    operation_ids: tuple[str, ...]
    changed_media_roles: tuple[MediaRole, ...]
    effective_media_roles: Mapping[str, str]


@dataclass(frozen=True, eq=False)
class AffectedRepairReadSet:
    execution: AffectedRepairExecution
    parent: CurrentFinalEvidenceReadSet
    child: CurrentFinalEvidenceReadSet | None
    masters: AffectedMasterObservation | None


class ForcedAlignmentRegistration(FinalModel):
    format: Literal['registered-forced-alignment-v1']
    route_id: c.Identifier
    driver_profile: Literal['qualified-local-forced-alignment-v1']
    resource_section: Literal['alignment']
    method_qualification_ref: c.MethodQualificationRef


class NarrationResourceSection(FinalModel):
    kind: Literal['piper']
    python: str
    worker: str
    model: str
    model_configuration: str = Field(alias='model_config')
    license_document: str
    version: str


class PictureResourceSection(FinalModel):
    kind: Literal['wan2.7']
    workspace_id: str = Field(pattern=r'^[a-zA-Z0-9-]{2,63}$')
    region: Literal['cn-beijing', 'ap-southeast-1']
    model: Literal['wan2.7-t2v-2026-06-12']
    resolution: Literal['720P', '1080P']
    download_hosts: tuple[str, ...] = Field(min_length=1, max_length=16)


class EditResourceSection(FinalModel):
    kind: Literal['ffmpeg']
    ffmpeg: str
    ffprobe: str


class AlignmentResourceSection(FinalModel):
    kind: Literal['qualified_local_forced_alignment']
    model_revision: str = Field(min_length=1, max_length=300)
    model_files: dict[str, c.Sha256]
    configuration_sha256: c.Sha256
    worker_resource: str
    runtime_resource: str
    license_artifact_ids: tuple[c.Identifier, ...] = Field(min_length=1)


class ProductionDriverResourcesV2(FinalModel):
    format: Literal['registered-production-driver-resources-v2']
    narration: NarrationResourceSection
    picture: PictureResourceSection
    edit: EditResourceSection
    alignment: AlignmentResourceSection | None

    @model_validator(mode='after')
    def owned_relative_resources(self):
        names = [self.narration.python, self.narration.worker, self.narration.model,
                 self.narration.model_configuration, self.narration.license_document,
                 self.edit.ffmpeg, self.edit.ffprobe]
        if self.alignment:
            if not self.alignment.model_files or len(set(self.alignment.license_artifact_ids)) != len(self.alignment.license_artifact_ids):
                raise ValueError('Complete distinct alignment resources/licenses required')
            names += [*self.alignment.model_files, self.alignment.worker_resource, self.alignment.runtime_resource]
        for name in names:
            relative = PurePosixPath(name)
            if (relative.is_absolute() or not relative.parts or relative.as_posix() != name
                    or any(p in {'.', '..'} or ':' in p or '\\' in p for p in relative.parts)):
                raise ValueError('Resource stays in original held installation index')
        if any(not host.endswith('.aliyuncs.com') or '..' in host or host.startswith('.') for host in self.picture.download_hosts):
            raise ValueError('Original provider output host scope required')
        return self
