"""ADR0072/0073 local material data. Parsed data grants no execution authority."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import PurePosixPath
from typing import Annotated, Literal

from pydantic import Field, TypeAdapter, ValidationError, model_validator

from video_creator.domain import contracts as c
from video_creator.domain.affected_recipe import RecipeSourceRef
from video_creator.domain.affected_repair import ForcedAlignmentRegistration
from video_creator.domain.errors import EngineError
from video_creator.domain.registered_production import PrivateModel, ProductionRightsDeclaration, ProductionRightsProposal
from video_creator.domain.daily_project_authorization import ProjectScopeDerivationRef, ProjectGoalAccepted

Usage = Literal['narration', 'visual', 'background_audio']
Positive = Annotated[int, Field(strict=True, gt=0)]


def _relative(value: str) -> str:
    path = PurePosixPath(value)
    if (not value or path.is_absolute() or path.as_posix() != value
            or any(part in {'.', '..'} or ':' in part or '\\' in part for part in path.parts)):
        raise ValueError('Original indexed relative resource is required')
    return value


def local_material_canonical_bytes(value) -> bytes:
    """Private recursive JSON identity; never replaces original Goal canonical."""
    if isinstance(value, PrivateModel):
        value = value.model_dump(mode='json')
    c.reject_secrets(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def local_material_sha256(value) -> str:
    return hashlib.sha256(local_material_canonical_bytes(value)).hexdigest()


def local_binding_id(asset_id: str, usage: Usage) -> str:
    asset_id = TypeAdapter(c.Identifier).validate_python(asset_id, strict=True)
    usage = TypeAdapter(Usage).validate_python(usage, strict=True)
    return 'b-' + local_material_sha256({'asset_id': asset_id, 'usage': usage})


class LocalRegistrationV1(PrivateModel):
    profile: Literal['local-owned-assets-v1']
    rights_declaration: ProductionRightsDeclaration
    input_audio_route_id: c.Identifier
    input_visual_route_id: c.Identifier
    edit_route_id: c.Identifier
    master_index_route_id: c.Identifier
    max_duration_us: int = Field(strict=True, gt=0, le=600_000_000)


class RegistrationConfigLocalV1(PrivateModel):
    format: Literal['registered-media-config-local-v1']
    engine_source_sha256: dict[str, c.Sha256] = Field(min_length=1)
    ffmpeg: str = Field(min_length=1)
    ffmpeg_sha256: c.Sha256
    ffprobe: str = Field(min_length=1)
    ffprobe_sha256: c.Sha256
    asr_resource_manifest: str | None
    asr_resource_manifest_sha256: c.Sha256 | None
    asr_runtime_manifest_sha256: c.Sha256 | None
    asr_route_id: c.Identifier | None
    production_resource_manifest: str = Field(min_length=1)
    production_resource_manifest_sha256: c.Sha256
    production_runtime_manifest_sha256: c.Sha256
    local_registration: LocalRegistrationV1
    alignment_registration: ForcedAlignmentRegistration | None

    @model_validator(mode='after')
    def installed_inputs(self):
        optional = (self.asr_resource_manifest, self.asr_resource_manifest_sha256,
                    self.asr_runtime_manifest_sha256, self.asr_route_id)
        if any(value is None for value in optional) and not all(value is None for value in optional):
            raise ValueError('ASR fields must be all present or all null')
        for name in self.engine_source_sha256:
            _relative(name)
        for name in (self.ffmpeg, self.ffprobe, self.production_resource_manifest):
            _relative(name)
        if self.asr_resource_manifest is not None:
            _relative(self.asr_resource_manifest)
        return self


class _LocalSourceSection(PrivateModel):
    implementation_source_refs: tuple[RecipeSourceRef, ...] = Field(min_length=1)

    @model_validator(mode='after')
    def unique_sources(self):
        names = [ref.resource_name for ref in self.implementation_source_refs]
        if len(names) != len(set(names)):
            raise ValueError('Implementation source references must be distinct')
        return self


class LocalInputAudioResources(_LocalSourceSection):
    kind: Literal['uploaded-audio']


class LocalInputVisualResources(_LocalSourceSection):
    kind: Literal['owned-material']


class LocalEditResources(_LocalSourceSection):
    kind: Literal['ffmpeg']
    ffmpeg: str = Field(min_length=1)
    ffprobe: str = Field(min_length=1)

    @model_validator(mode='after')
    def tools(self):
        _relative(self.ffmpeg)
        _relative(self.ffprobe)
        return self


class LocalMaterialResourcesV1(PrivateModel):
    format: Literal['registered-local-material-resources-v1']
    runtime_manifest: str = Field(min_length=1)
    input_audio: LocalInputAudioResources
    input_visual: LocalInputVisualResources
    edit: LocalEditResources

    @model_validator(mode='after')
    def runtime(self):
        _relative(self.runtime_manifest)
        return self


class LocalInputBindingV1(PrivateModel):
    binding_id: c.Identifier
    asset_id: c.Identifier
    sha256: c.Sha256
    size: Positive
    media_type: str = Field(min_length=1, max_length=200)
    probe: c.MediaProbe
    source_ref: str = Field(min_length=1, max_length=256)
    usage: Usage

    @model_validator(mode='after')
    def connection_identity(self):
        if self.binding_id != local_binding_id(self.asset_id, self.usage):
            raise ValueError('Binding ID differs from original asset/usage canonical identity')
        if self.probe.media_type != self.media_type:
            raise ValueError('Binding media type differs from original probe')
        return self


class LocalTimelineShotV1(PrivateModel):
    shot_id: c.Identifier
    input_binding_id: c.Identifier
    source_range: c.MediaRange
    timeline_range: c.MediaRange
    fit: Literal['contain', 'cover']


class LocalTimelineAudioTrackV1(PrivateModel):
    track_id: c.Identifier
    input_binding_id: c.Identifier
    source_range: c.MediaRange
    timeline_range: c.MediaRange
    gain: float = Field(strict=True, ge=0, allow_inf_nan=False)


class LocalTimelineV1(PrivateModel):
    width: Positive
    height: Positive
    fps_num: Positive
    fps_den: Positive
    duration_us: Positive
    shots: tuple[LocalTimelineShotV1, ...]
    audio_tracks: tuple[LocalTimelineAudioTrackV1, ...]

    @model_validator(mode='after')
    def finite_ranges(self):
        for values, field in ((self.shots, 'shot_id'), (self.audio_tracks, 'track_id')):
            ids = [getattr(value, field) for value in values]
            if len(ids) != len(set(ids)):
                raise ValueError('Timeline item identities must be unique')
            if any(value.timeline_range.end_us > self.duration_us for value in values):
                raise ValueError('Timeline ranges exceed declared duration')
        return self


def validate_local_timeline_bindings(bindings: tuple[LocalInputBindingV1, ...],
                                     timeline: LocalTimelineV1) -> None:
    """Only the supplied current admitted plan collection is the join scope."""
    ids = [value.binding_id for value in bindings]
    pairs = [(value.asset_id, value.usage) for value in bindings]
    if len(ids) != len(set(ids)) or len(pairs) != len(set(pairs)):
        raise EngineError('local_plan_binding_duplicate', 'Plan input definitions must be unique.', 422)
    by_id = {value.binding_id: value for value in bindings}
    for values, usages in ((timeline.shots, {'visual'}),
                           (timeline.audio_tracks, {'narration', 'background_audio'})):
        for value in values:
            binding = by_id.get(value.input_binding_id)
            if binding is None:
                raise EngineError('local_plan_binding_missing', 'Timeline input is absent from this plan.', 422)
            if binding.usage not in usages:
                raise EngineError('local_plan_binding_usage_conflict', 'Timeline input usage conflicts.', 422)


def _parse(data: bytes, model, code: str):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Repeated JSON field')
            result[key] = value
        return result

    def finite(value):
        result = float(value)
        if not math.isfinite(result):
            raise ValueError('Nonfinite JSON number')
        return result

    def constant(value):
        raise ValueError('Nonfinite JSON constant')

    if type(data) is not bytes or not 1 <= len(data) <= 1_048_576 or data.startswith(b'\xef\xbb\xbf'):
        raise EngineError(code, 'Finite UTF-8 JSON bytes are required.', 422)
    try:
        value = json.loads(data.decode('utf-8'), object_pairs_hook=pairs,
                           parse_float=finite, parse_constant=constant)
        c.reject_secrets(value)
        return model.model_validate_json(data, strict=True)
    except (UnicodeError, ValueError, RecursionError, ValidationError) as error:
        raise EngineError(code, 'Local material data has an invalid exact schema.', 422) from error


def parse_local_registration_config(data: bytes) -> RegistrationConfigLocalV1:
    return _parse(data, RegistrationConfigLocalV1, 'local_registration_config_invalid')


def parse_local_material_resources(data: bytes) -> LocalMaterialResourcesV1:
    return _parse(data, LocalMaterialResourcesV1, 'local_material_resources_invalid')


class LocalProductionRequestRef(PrivateModel):
    instance_id: c.Identifier
    production_id: c.Identifier
    run_id: c.Identifier
    request_revision_id: c.Identifier
    request_sha256: c.Sha256


class LocalAcceptedGoalRef(PrivateModel):
    project_id: c.Identifier
    goal_sha256: c.Sha256
    derivation_ref: ProjectScopeDerivationRef


class LocalMaterialPlanV1(PrivateModel):
    format: Literal['registered-local-material-plan-v1']
    request_ref: LocalProductionRequestRef
    goal_ref: LocalAcceptedGoalRef | None
    material_refs: tuple[c.AssetRecord, ...]
    input_bindings: tuple[LocalInputBindingV1, ...]
    timeline: LocalTimelineV1
    source_script_revision_ref: c.RevisionRef
    source_script_origin: Literal['user_provided', 'model_inference', 'input_audio_transcript']
    rights_proposal: ProductionRightsProposal
    selected_capabilities: tuple[c.CapabilityRoute, ...]
    outputs: tuple[c.OutputRole, ...]

    @model_validator(mode='after')
    def collection_identity(self):
        validate_local_timeline_bindings(self.input_bindings, self.timeline)
        asset_ids = [value.asset_id for value in self.material_refs]
        routes = [value.route_id for value in self.selected_capabilities]
        if len(asset_ids) != len(set(asset_ids)) or len(routes) != len(set(routes)):
            raise ValueError('Material and capability identities must be unique')
        if set(asset_ids) != {value.asset_id for value in self.input_bindings}:
            raise ValueError('Material collection differs from plan input bindings')
        if self.source_script_revision_ref.kind != 'script':
            raise ValueError('Original script revision is required')
        return self


def parse_local_material_plan(data: bytes) -> LocalMaterialPlanV1:
    return _parse(data, LocalMaterialPlanV1, 'local_material_plan_invalid')


def plan_rights_body(body):
    """One strict local declaration projection; legacy representation unchanged."""
    if isinstance(body, dict) and body.get('format') == 'registered-local-material-plan-v1':
        plan = parse_local_material_plan(local_material_canonical_bytes(body))
        return [right.model_dump(mode='json') for right in plan.rights_proposal.rights]
    return body.get('rights') if isinstance(body, dict) else None


def validate_local_material_plan_sources(plan: LocalMaterialPlanV1, *,
        request: c.ProductionRequestAny, request_ref: LocalProductionRequestRef,
        accepted_goal: ProjectGoalAccepted | None, original_assets: tuple[c.AssetRecord, ...],
        original_script: tuple[c.RevisionRef, c.CreativeRevision],
        original_routes: tuple[c.CapabilityRoute, ...]) -> None:
    """Compare original data only; trusted absence/current remain caller duties."""
    def conflict(message):
        raise EngineError('local_material_source_conflict', message, 409)

    if plan.request_ref != request_ref or plan.outputs != request.outputs:
        conflict('Plan must retain original request identity and ordered outputs.')
    if accepted_goal is None:
        if plan.goal_ref is not None:
            conflict('Plan supplies a Goal absent from original controlled records.')
    else:
        expected_goal = LocalAcceptedGoalRef(project_id=accepted_goal.project_id,
            goal_sha256=accepted_goal.goal_sha256, derivation_ref=accepted_goal.derivation_ref)
        if ((accepted_goal.instance_id, accepted_goal.production_id, accepted_goal.run_id,
             accepted_goal.production.request_revision_id) != (request_ref.instance_id,
             request_ref.production_id, request_ref.run_id, request_ref.request_revision_id)
                or plan.goal_ref != expected_goal):
            conflict('Original accepted Goal and actual request are not the same production.')
    original = {asset.asset_id: asset for asset in original_assets}
    if len(original) != len(original_assets) or any(asset != original.get(asset.asset_id) for asset in plan.material_refs):
        conflict('Plan material record differs from actual original asset metadata.')
    if any(asset.asset_id not in request.inputs.asset_ids for asset in plan.material_refs):
        conflict('Plan material is outside the original request input scope.')
    for binding in plan.input_bindings:
        asset = original.get(binding.asset_id)
        if asset is None or (binding.sha256, binding.size, binding.media_type, binding.probe,
                binding.source_ref) != (asset.sha256, asset.size, asset.media_type, asset.probe, asset.source):
            conflict('Binding must retain the complete original asset identity.')
    ref, script = original_script
    if ref != plan.source_script_revision_ref or ref.kind != 'script' or script.kind != 'script' or ref.revision_id != script.revision_id:
        conflict('Plan script differs from original immutable script revision.')
    routes = {route.route_id: route for route in original_routes}
    if len(routes) != len(original_routes) or any(route != routes.get(route.route_id) for route in plan.selected_capabilities):
        conflict('Plan route differs from actual installed capability.')
    if any(route.route_id not in request.policy.allowed_provider_routes for route in plan.selected_capabilities):
        conflict('Selected capability is outside original request route scope.')
    proposal = plan.rights_proposal
    if (proposal.instance_id, proposal.production_id, proposal.run_id, proposal.request_revision_id,
            proposal.request_sha256) != (request_ref.instance_id, request_ref.production_id,
            request_ref.run_id, request_ref.request_revision_id, request_ref.request_sha256):
        conflict('Saved declaration belongs to another original request.')
