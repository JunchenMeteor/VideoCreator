"""The media derivative request has exactly one JSON shape.

`clips` is an ordered JSON list of `[shot_id, asset_id]` pairs. That same body is
hashed by `canonical_object` and handed to the fixed driver; tuples (the old form)
are not JSON and are rejected before any hash or dispatch. This is the fix the
media review asked to protect (bodies built with tuples failed
`production_json_invalid`).
"""

from __future__ import annotations

import json

import pytest
from video_creator.domain.contracts import ProductionRequest, RevisionRef
from video_creator.domain.errors import EngineError
from video_creator.domain.local_material_production import LocalTimelineV1
from video_creator.workflows.local_material_drivers import (
    derivative_body,
    derivative_driver_input,
)
from video_creator.workflows.local_material_production import derivative_input_sha
from video_creator.workflows.production_json import canonical_object

CLIPS = [['shot-1', 'asset-1'], ['shot-2', 'asset-2']]


def timeline() -> LocalTimelineV1:
    return LocalTimelineV1(width=720, height=1280, fps_num=30, fps_den=1, duration_us=4_000_000,
                           shots=(), audio_tracks=())


def test_clips_json_pairs_are_the_sole_body_shape() -> None:
    body = derivative_body({'clips': CLIPS})
    assert body['clips'] == CLIPS
    assert body['clips'] == [['shot-1', 'asset-1'], ['shot-2', 'asset-2']]
    canonical = canonical_object(body)
    assert canonical == canonical_object({'clips': CLIPS})
    assert json.loads(canonical)['clips'] == CLIPS

    with pytest.raises(EngineError) as tuple_error:
        derivative_body({'clips': (('shot-1', 'asset-1'),)})
    assert tuple_error.value.code == 'local_builder_input_invalid'
    assert tuple_error.value.status_code == 422

    with pytest.raises(EngineError) as raw_error:
        canonical_object({'clips': [('shot-1', 'asset-1')]})
    assert raw_error.value.code == 'production_json_invalid', (
        'the old tuple form is not JSON and must stay rejected')


def test_derivative_input_sha_is_stable_and_hashes_the_driver_body() -> None:
    request = ProductionRequest(goal='media derivative request fixture', outputs=('video',))
    plan_ref = RevisionRef(revision_id='rev-plan-fixture', kind='plan', content_sha256='b' * 64)
    raw_body = {'bindings': (), 'timeline': timeline(), 'clips': CLIPS, 'narration_audio': None}

    first_sha, first_projection = derivative_input_sha(
        request=request, plan_revision_ref=plan_ref, key='production-local-shot-1',
        body=raw_body, route_id='local.edit.ffmpeg-v1')
    second_sha, second_projection = derivative_input_sha(
        request=request, plan_revision_ref=plan_ref, key='production-local-shot-1',
        body=raw_body, route_id='local.edit.ffmpeg-v1')
    assert first_sha == second_sha
    assert first_projection == second_projection
    assert first_projection['clips'] == CLIPS, 'the hashed body keeps JSON pairs'
    assert first_projection['bindings'] == []

    reordered = {'bindings': (), 'timeline': timeline(), 'clips': list(reversed(CLIPS)),
                 'narration_audio': None}
    reordered_sha, _projection = derivative_input_sha(
        request=request, plan_revision_ref=plan_ref, key='production-local-shot-1',
        body=reordered, route_id='local.edit.ffmpeg-v1')
    assert reordered_sha != first_sha, 'clip order is part of the request identity'

    driver_input = derivative_driver_input(first_projection, 'edit')
    assert driver_input['clips'] == (('shot-1', 'asset-1'), ('shot-2', 'asset-2')), (
        'the single driver boundary converts the hashed JSON pairs back to tuples only here')
    assert driver_input['narration_audio'] is None
