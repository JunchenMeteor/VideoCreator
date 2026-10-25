"""Hardcoded owned-material builders; no ASR, Piper, Wan or caller module dispatch."""
from __future__ import annotations

from pathlib import Path

from video_creator.domain.errors import EngineError
from video_creator.domain.local_material_production import LocalRegistrationV1
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
            fields = {'bindings', 'timeline'}
            if kind == 'input_visual':
                fields.add('shot_id')
            elif kind == 'edit':
                fields |= {'clips', 'narration_audio'}
            if type(request_data) is not dict or set(request_data) != fields:
                raise EngineError('local_builder_input_invalid', 'The fixed local builder consumes only its actual current-plan objects and registered derivatives.', 422)
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
                'lease': ordinary_lease, 'outputs': outputs, 'bindings': request_data['bindings'], 'timeline': request_data['timeline'],
                'max_duration_us': local_registration.max_duration_us, 'cancel': cancel, 'deadline_monotonic': deadline_monotonic}
            if kind == 'input_audio':
                if len(outputs) != 1:
                    raise EngineError('local_narration_output_invalid', 'Normalize actual narration into one independent output.', 422)
                driver = LocalAudioNormalizeDriver(route_id=local_registration.input_audio_route_id, **common)
            elif kind == 'input_visual':
                if len(outputs) != 1 or type(request_data['shot_id']) is not str:
                    raise EngineError('local_visual_output_invalid', 'One actual approved shot uses one derivative output.', 422)
                driver = LocalVisualMaterialDriver(route_id=local_registration.input_visual_route_id,
                    shot_id=request_data['shot_id'], **common)
            else:
                request = engine.get_request(ordinary_lease)
                count = 2 + bool(request_data['timeline'].audio_tracks) if 'video' in request.outputs else 1
                if len(outputs) != count:
                    raise EngineError('local_edit_output_invalid', 'Reserve only applicable real video, mix and cover outputs.', 422)
                driver = LocalMaterialEditDriver(route_id=local_registration.edit_route_id,
                    clips=request_data['clips'], narration_audio=request_data['narration_audio'], **common)
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
