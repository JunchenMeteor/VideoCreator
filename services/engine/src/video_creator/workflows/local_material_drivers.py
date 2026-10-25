"""Hardcoded owned-material builders; no ASR, Piper, Wan or caller module dispatch."""
from __future__ import annotations

from pathlib import Path

from video_creator.domain.errors import EngineError
from video_creator.domain.local_material_production import (
    LocalInputBindingV1,
    LocalRegistrationV1,
    LocalTimelineV1,
)
from video_creator.domain.registered_production import ProductionDriverBuilders
from video_creator.media.ffmpeg import FFmpegRuntime
from video_creator.media.local_material_edit import (
    LocalAudioNormalizeDriver,
    LocalMaterialEditDriver,
    LocalVisualMaterialDriver,
)
from video_creator.providers.local_material_resources import LocalMaterialResources
from video_creator.providers.production_common import output_scope
from video_creator.workflows.attempt_control import attempt_control
from video_creator.workflows.autonomous_production import BoundProductionDriver

DERIVATIVE_FIELDS = frozenset({'bindings', 'timeline', 'shot_id', 'clips', 'narration_audio'})


def derivative_body(data):
    """Sole JSON request body for one derivative step.

    The same value is hashed by `canonical_object` and handed to the fixed
    builders, so exactly one request form exists: current-plan typed objects
    and clip pairs are projected here and never reinterpreted later.
    """
    if type(data) is not dict or not set(data) <= DERIVATIVE_FIELDS:
        raise EngineError('local_builder_input_invalid',
            'The fixed derivative request consumes only its current-plan body.', 422)
    body = {}
    for name, value in data.items():
        if name == 'bindings':
            if type(value) is not tuple or any(type(item) is not LocalInputBindingV1 for item in value):
                raise EngineError('local_builder_input_invalid',
                    'Only the actual current-plan binding tuple is accepted.', 422)
            body[name] = [item.model_dump(mode='json') for item in value]
        elif name == 'timeline':
            if type(value) is not LocalTimelineV1:
                raise EngineError('local_builder_input_invalid',
                    'Only the actual current-plan timeline is accepted.', 422)
            body[name] = value.model_dump(mode='json')
        elif name == 'clips':
            body[name] = _clip_list(value)
        elif name == 'shot_id':
            if type(value) is not str:
                raise EngineError('local_builder_input_invalid', 'A shot identity must be a string.', 422)
            body[name] = value
        else:
            if value is not None and type(value) is not str:
                raise EngineError('local_builder_input_invalid',
                    'A narration Asset identity must be a string or absent.', 422)
            body[name] = value
    return body


def _clip_list(clips):
    """Ordered `[shot_id, asset_id]` JSON pairs; one form only, no tuples."""
    if (type(clips) is not list or any(type(item) is not list or len(item) != 2
            or any(type(part) is not str for part in item) for item in clips)):
        raise EngineError('local_builder_input_invalid',
            'Clip pairs are an ordered JSON list of [shot_id, asset_id].', 422)
    return [[shot_id, asset_id] for shot_id, asset_id in clips]


def derivative_driver_input(request_data, kind):
    """Typed driver arguments re-parsed strictly from the sole JSON body.

    `LocalMaterialEditDriver` consumes `tuple[tuple[str, str], ...]`, while the
    hashed request keeps plain JSON pairs. The conversion happens only at this
    driver boundary and preserves the exact ordered pairs.
    """
    fields = {'bindings', 'timeline'}
    if kind == 'input_visual':
        fields.add('shot_id')
    elif kind == 'edit':
        fields |= {'clips', 'narration_audio'}
    if type(request_data) is not dict or set(request_data) != fields:
        raise EngineError('local_builder_input_invalid',
            'The fixed local builder consumes only its actual current-plan objects and registered derivatives.', 422)
    try:
        bindings = tuple(LocalInputBindingV1.model_validate(value) for value in request_data['bindings'])
        timeline = LocalTimelineV1.model_validate(request_data['timeline'])
    except (TypeError, ValueError):
        raise EngineError('local_builder_input_invalid',
            'Only the canonical current-plan body is accepted.', 422) from None
    result = {'bindings': bindings, 'timeline': timeline}
    if kind == 'input_visual':
        if type(request_data['shot_id']) is not str:
            raise EngineError('local_visual_output_invalid', 'One actual approved shot identity is required.', 422)
        result['shot_id'] = request_data['shot_id']
    elif kind == 'edit':
        result['clips'] = tuple((shot_id, asset_id) for shot_id, asset_id in _clip_list(request_data['clips']))
        narration = request_data['narration_audio']
        if narration is not None and type(narration) is not str:
            raise EngineError('local_builder_input_invalid', 'A narration Asset identity must be a string or absent.', 422)
        result['narration_audio'] = narration
    return result



def create_local_material_production_drivers(*, engine, worker, bundle, storage_root, runtime_root, decoder,
        resource_manifest_path, resource_manifest_sha256, runtime_manifest_sha256,
        local_registration: LocalRegistrationV1) -> ProductionDriverBuilders:
    if type(local_registration) is not LocalRegistrationV1 or not callable(decoder):
        raise EngineError('local_driver_context_invalid', 'Use the sole local registration and trusted full-decode MIME validator.', 503)
    resources = LocalMaterialResources(manifest_path=resource_manifest_path, manifest_sha256=resource_manifest_sha256,
        runtime_manifest_sha256=runtime_manifest_sha256)

    def build(request_data, ordered_output_reservations, *, ordinary_lease, cancel, deadline_monotonic, kind):
        control = attempt_control(cancel, deadline_monotonic)
        with control.activate():
            outputs = output_scope(ordered_output_reservations, ordinary_lease, storage_root)
            inputs = derivative_driver_input(request_data, kind)
            section = {'input_audio': resources.config.input_audio, 'input_visual': resources.config.input_visual,
                       'edit': resources.config.edit}[kind]
            source_root = Path(__file__).parents[1]
            resources.check_sources(section, (
                Path(__file__), source_root / 'media/local_material_edit.py', source_root / 'media/ffmpeg.py',
                source_root / 'media/local_frame_grid.py',
                source_root / 'providers/local_material_resources.py', source_root / 'providers/production_resources.py',
                source_root / 'providers/production_common.py', source_root / 'workflows/attempt_control.py',
            ))
            runtime = FFmpegRuntime(resources.resource(resources.config.edit.ffmpeg),
                resources.resource(resources.config.edit.ffprobe), storage_root)
            common = {'engine': engine, 'worker': worker, 'bundle': bundle, 'decoder': decoder, 'runtime': runtime,
                'lease': ordinary_lease, 'outputs': outputs, 'bindings': inputs['bindings'], 'timeline': inputs['timeline'],
                'max_duration_us': local_registration.max_duration_us, 'cancel': cancel, 'deadline_monotonic': deadline_monotonic}
            if kind == 'input_audio':
                if len(outputs) != 1:
                    raise EngineError('local_narration_output_invalid', 'Normalize actual narration into one independent output.', 422)
                driver = LocalAudioNormalizeDriver(route_id=local_registration.input_audio_route_id, **common)
            elif kind == 'input_visual':
                if len(outputs) != 1:
                    raise EngineError('local_visual_output_invalid', 'One actual approved shot uses one derivative output.', 422)
                driver = LocalVisualMaterialDriver(route_id=local_registration.input_visual_route_id,
                    shot_id=inputs['shot_id'], **common)
            else:
                request = engine.get_request(ordinary_lease)
                count = 2 + bool(inputs['timeline'].audio_tracks) if 'video' in request.outputs else 1
                if len(outputs) != count:
                    raise EngineError('local_edit_output_invalid', 'Reserve only applicable real video, mix and cover outputs.', 422)
                driver = LocalMaterialEditDriver(route_id=local_registration.edit_route_id,
                    clips=inputs['clips'], narration_audio=inputs['narration_audio'], **common)
            return BoundProductionDriver(driver)

    def narration(request_data, ordered_output_reservations, *, ordinary_lease, cancel, deadline_monotonic):
        return build(request_data, ordered_output_reservations, ordinary_lease=ordinary_lease,
            cancel=cancel, deadline_monotonic=deadline_monotonic, kind='input_audio')

    def picture(request_data, ordered_output_reservations, *, ordinary_lease, cancel, deadline_monotonic):
        return build(request_data, ordered_output_reservations, ordinary_lease=ordinary_lease,
            cancel=cancel, deadline_monotonic=deadline_monotonic, kind='input_visual')

    def edit(request_data, ordered_output_reservations, *, ordinary_lease, cancel, deadline_monotonic):
        return build(request_data, ordered_output_reservations, ordinary_lease=ordinary_lease,
            cancel=cancel, deadline_monotonic=deadline_monotonic, kind='edit')

    # Construction verifies only selected local bytes. Missing/unselected ASR
    # must not prevent ordinary editing. Full speech/RAG publication uses its
    # separate original ASR/evidence ports in the later fixed Flow/composer.
    return ProductionDriverBuilders(narration=narration, picture=picture, edit=edit)
