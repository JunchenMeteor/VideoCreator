"""Local planning from original objects; no second binding parser or authority.

The sole plan/Ref/source validator names follow stopped ADR0074. Backend must
provide the actual controlled source objects before this candidate can run.
"""
from __future__ import annotations

from fractions import Fraction

from video_creator.application.engine import canonical, digest
from video_creator.domain import contracts as c
from video_creator.domain.errors import EngineError
from video_creator.domain.local_material_production import (
    LocalInputBindingV1,
    LocalMaterialPlanV1,
    LocalTimelineAudioTrackV1,
    LocalTimelineShotV1,
    LocalTimelineV1,
    local_binding_id,
    parse_local_material_plan,
    validate_local_material_plan_sources,
)
from video_creator.media.local_material_edit import validate_timeline
from video_creator.workflows.production_json import canonical_object, json_body


def revision_ref(revision):
    if type(revision) is not c.CreativeRevision:
        raise EngineError('local_revision_invalid', 'Use the original saved whole creative revision.', 409)
    return c.RevisionRef(revision_id=revision.revision_id, kind=revision.kind,
                         content_sha256=digest(canonical(revision)))


def binding_for(asset, usage):
    if type(asset) is not c.AssetRecord or not asset.probe.decoded or asset.probe.media_type != asset.media_type:
        raise EngineError('local_material_invalid', 'Original registered inputs need their actual complete decode evidence.', 422)
    return LocalInputBindingV1(binding_id=local_binding_id(asset.asset_id, usage),
        asset_id=asset.asset_id, sha256=asset.sha256, size=asset.size,
        media_type=asset.media_type, probe=asset.probe, source_ref=asset.source, usage=usage)


def propose_video_timeline(request, original_assets, *, narration_asset_id=None, max_duration_us):
    """Reviewable cuts/ADR0075 image holds; original input order is retained."""
    if type(original_assets) is not tuple or tuple(a.asset_id for a in original_assets) != request.inputs.asset_ids:
        raise EngineError('local_inputs_conflict', 'Read the complete ordered original request Asset set.', 409)
    by_id = {a.asset_id: a for a in original_assets}
    audio = by_id.get(narration_asset_id)
    if narration_asset_id is not None and (audio is None or not audio.probe.has_audio or audio.probe.duration_us is None):
        raise EngineError('local_narration_source_missing', 'Select an actual admitted source audio track for this voiced-video proposal.', 422)
    visuals = tuple(a for a in original_assets if a.media_type == 'video/mp4' and a.probe.has_video
        or a.media_type in {'image/jpeg', 'image/png'} and not a.probe.has_video
        and not a.probe.has_audio and a.probe.duration_us is None and a.probe.width and a.probe.height)
    if not visuals:
        raise EngineError('local_visual_source_missing', 'Use a real decoded video or PNG/JPEG static image.', 422)
    requested_duration = request.brief.target_duration_us if request.brief is not None else None
    available = max_duration_us if any(a.media_type.startswith('image/') for a in visuals) else sum(a.probe.duration_us or 0 for a in visuals)
    target = min(requested_duration or 10_000_000, audio.probe.duration_us if audio is not None else max_duration_us,
        max_duration_us, available)
    duration = target // 40_000 * 40_000
    if duration <= 0:
        raise EngineError('local_duration_invalid', 'The actual source material does not cover one 25fps frame.', 422)
    usage = 'narration' if 'narration_audio' in request.outputs else 'background_audio'
    bindings = [binding_for(audio, usage)] if audio is not None else []
    shots, cursor = [], 0
    for number, asset in enumerate(visuals):
        if cursor == duration:
            break
        binding = binding_for(asset, 'visual')
        if asset.media_type.startswith('image/'):
            # Reviewable equal shares of the remaining work; this is display
            # time selected BEFORE plan approval, not a source-image duration.
            remaining_frames = (duration - cursor) // 40_000
            length = max(1, remaining_frames // (len(visuals) - number)) * 40_000
        else:
            length = min(duration - cursor, (asset.probe.duration_us or 0) // 40_000 * 40_000)
        if length <= 0:
            continue
        bindings.append(binding)
        shots.append(LocalTimelineShotV1(shot_id=f'local-shot-{len(shots) + 1}',
            input_binding_id=binding.binding_id, source_range=c.MediaRange(start_us=0, end_us=length),
            timeline_range=c.MediaRange(start_us=cursor, end_us=cursor + length), fit='contain'))
        cursor += length
    if cursor != duration:
        raise EngineError('local_duration_invalid', 'Whole source frames do not cover the proposed work.', 422)
    width, height = (1920, 1080) if request.brief is not None and request.brief.aspect_ratio == '16:9' else (1080, 1920)
    timeline = LocalTimelineV1(width=width, height=height, fps_num=25, fps_den=1,
        duration_us=duration, shots=tuple(shots), audio_tracks=(LocalTimelineAudioTrackV1(
            track_id='local-audio-1', input_binding_id=bindings[0].binding_id,
            source_range=c.MediaRange(start_us=0, end_us=duration),
            timeline_range=c.MediaRange(start_us=0, end_us=duration), gain=1.0),) if audio is not None else ())
    # Preserve every accepted material in the plan. Unused inputs still need a
    # binding and their original evidence, without implicit audio selection.
    used_assets = {b.asset_id for b in bindings}
    for asset in original_assets:
        if asset.asset_id not in used_assets:
            if asset.media_type in {'image/jpeg', 'image/png', 'video/mp4'}:
                bindings.append(binding_for(asset, 'visual'))
            elif asset.media_type == 'audio/wav' and asset.probe.has_audio:
                bindings.append(binding_for(asset, 'background_audio'))
            else:
                raise EngineError('local_material_selection_required', 'The explicit plan must retain every original input with a supported usage.', 409)
    return tuple(bindings), timeline


def propose_audio_timeline(request, original_assets, *, max_duration_us):
    """An actual audio work has no black video, cover, shots or frame grid."""
    if type(original_assets) is not tuple or tuple(a.asset_id for a in original_assets) != request.inputs.asset_ids:
        raise EngineError('local_inputs_conflict', 'Use all original ordered input Asset records.', 409)
    if 'video' in request.outputs:
        raise EngineError('local_timeline_kind_conflict', 'A requested video cannot use the audio-only planner.', 422)
    candidates = tuple(a for a in original_assets if a.probe.has_audio and a.probe.duration_us is not None)
    if not candidates:
        raise EngineError('local_media_input_required', 'Audio-only works need an actual admitted audio stream.', 422)
    audio = candidates[0]
    requested = request.brief.target_duration_us if request.brief is not None else None
    # Choose an actual 48kHz sample-compatible boundary BEFORE plan approval.
    # No source intrinsic duration/probe or saved plan is modified.
    duration = min(requested or audio.probe.duration_us, audio.probe.duration_us, max_duration_us) // 125 * 125
    if duration <= 0:
        raise EngineError('local_duration_invalid', 'Actual audio does not cover one admitted sample interval.', 422)
    usage = 'narration' if 'narration_audio' in request.outputs else 'background_audio'
    binding = binding_for(audio, usage)
    bindings = [binding]
    for asset in original_assets:
        if asset.asset_id != audio.asset_id:
            kind = 'visual' if asset.media_type in {'image/jpeg', 'image/png', 'video/mp4'} else 'background_audio'
            bindings.append(binding_for(asset, kind))
    timeline = LocalTimelineV1(width=1080, height=1920, fps_num=25, fps_den=1,
        duration_us=duration, shots=(), audio_tracks=(LocalTimelineAudioTrackV1(track_id='local-audio-1',
            input_binding_id=binding.binding_id, source_range=c.MediaRange(start_us=0, end_us=duration),
            timeline_range=c.MediaRange(start_us=0, end_us=duration), gain=1.0),))
    return tuple(bindings), timeline


def build_local_plan(*, request, request_ref, accepted_goal, original_assets,
        original_script, original_routes, goal_ref, source_script_origin,
        rights_proposal, input_bindings, timeline, max_duration_us):
    """Consume sole controlled facts, retaining historical proposal timestamps.

    accepted_goal=None is accepted only when the Backend controlled reader has
    established actual absence. A caller/model cannot invoke this as a grant.
    """
    ref, script = original_script
    if revision_ref(script) != ref or ref.kind != 'script':
        raise EngineError('local_script_source_conflict', 'The script Ref binds the original entire saved revision.', 409)
    if type(script.body) is not dict or type(script.body.get('text')) is not str:
        raise EngineError('local_script_source_missing', 'Use the actual saved script text, never a surrogate transcript.', 409)
    validate_timeline(input_bindings, timeline, max_duration_us,
        content_kind='video' if 'video' in request.outputs else 'audio')
    plan = LocalMaterialPlanV1(format='registered-local-material-plan-v1',
        request_ref=request_ref, goal_ref=goal_ref, material_refs=original_assets,
        input_bindings=input_bindings, timeline=timeline, source_script_revision_ref=ref,
        source_script_origin=source_script_origin, rights_proposal=rights_proposal,
        selected_capabilities=original_routes, outputs=request.outputs)
    validate_local_material_plan_sources(plan, request=request, request_ref=request_ref,
        accepted_goal=accepted_goal, original_assets=original_assets,
        original_script=original_script, original_routes=original_routes)
    return plan


def restore_local_plan(revision, *, request, request_ref, accepted_goal,
                       original_assets, original_script, original_routes):
    if type(revision) is not c.CreativeRevision or revision.kind != 'plan':
        raise EngineError('local_plan_invalid', 'Restore only the actual immutable plan revision.', 409)
    # Parse original body, not a reconstruction with new rights/fence/Goal refs.
    plan = parse_local_material_plan(canonical_object(json_body(revision.body, path='plan.body')).encode('utf-8'))
    validate_local_material_plan_sources(plan, request=request, request_ref=request_ref,
        accepted_goal=accepted_goal, original_assets=original_assets,
        original_script=original_script, original_routes=original_routes)
    return plan


def selected_output_variant(plan):
    """No speech is fabricated to satisfy a legacy four-master result shape."""
    requested = set(plan.outputs)
    narration = any(b.usage == 'narration' and any(t.input_binding_id == b.binding_id
        for t in plan.timeline.audio_tracks) for b in plan.input_bindings)
    if 'video' not in requested:
        return 'audio_only'
    return 'voiced_video' if narration else 'unvoiced_video'


def source_timeline_records(plan):
    """Original source and display coordinates remain separately attributable.

    Returns the sole JSON body form, so a provenance record can enter a
    CreativeRevision body or a canonical hash without a second projection.
    """
    by_id = {b.binding_id: b for b in plan.input_bindings}
    visuals = [{'shot_id': shot.shot_id, 'input_binding': by_id[shot.input_binding_id].model_dump(mode='json'),
        'source_media_range': None if by_id[shot.input_binding_id].media_type.startswith('image/') else shot.source_range.model_dump(mode='json'),
        'planned_source_range': shot.source_range.model_dump(mode='json'),
        'display_range': shot.timeline_range.model_dump(mode='json'), 'fit': shot.fit,
        'model_generated': False} for shot in plan.timeline.shots]
    tracks = [{'track_id': track.track_id, 'input_binding': by_id[track.input_binding_id].model_dump(mode='json'),
        'source_media_range': track.source_range.model_dump(mode='json'),
        'timeline_range': track.timeline_range.model_dump(mode='json'), 'gain': track.gain,
        'playback_rate': str(Fraction(track.source_range.end_us - track.source_range.start_us,
            track.timeline_range.end_us - track.timeline_range.start_us))} for track in plan.timeline.audio_tracks]
    return json_body({'format': 'local-material-provenance-v1', 'request_ref': plan.request_ref.model_dump(mode='json'),
        'goal_ref': None if plan.goal_ref is None else plan.goal_ref.model_dump(mode='json'),
        'script_ref': plan.source_script_revision_ref.model_dump(mode='json'),
        'script_origin': plan.source_script_origin, 'visual_sources': visuals, 'audio_sources': tracks})
