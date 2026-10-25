"""Actual local creative/Step/media inputs for the sole Bundle composer.

This internal composition is not a Manifest, legal grant or schema substitute.
The local Bundle/applicable-output contract remains the Backend/Architecture
dependency; no insight/brief/storyboard placeholder documents are returned.
"""
from __future__ import annotations

from video_creator.application.engine import canonical, digest
from video_creator.domain.errors import EngineError
from video_creator.domain.local_bundle import LocalMasterSelectionV1
from video_creator.workflows.local_material_plan import (
    restore_local_plan,
    revision_ref,
    source_timeline_records,
)
from video_creator.workflows.local_material_production import (
    LocalMaterialPolicyServices,
    LocalMaterialServices,
    _completed,
)
from video_creator.workflows.local_material_rights import require_local_plan_rights
from video_creator.workflows.production_json import canonical_object


def read_local_composition(services, ordinary_lease, *, media_roles, plan_admission, production_rights_fact):
    """Read original scoped objects; never choose latest revisions or inputs."""
    if type(services) not in {LocalMaterialServices, LocalMaterialPolicyServices}:
        raise EngineError('local_composer_services_invalid', 'Use the original installed local services object.', 503)
    engine, bundle = services.engine, services.bundle
    request = engine.get_request(ordinary_lease)
    ports = services.production_ports if type(services) is LocalMaterialServices else services.policy_execution_ports
    revisions = {r.revision_id: r for r in bundle.creative_revisions(ordinary_lease)}
    plan_revision = revisions.get('autonomous.plan.' + ordinary_lease.run_id)
    quality_revision = revisions.get('autonomous.quality.' + ordinary_lease.run_id)
    if plan_revision is None or quality_revision is None or plan_revision.kind != 'plan' or quality_revision.kind != 'quality':
        raise EngineError('local_composition_revisions_missing', 'Local composition retains actual script, plan and quality, without fabricated extra versions.', 409)
    from video_creator.domain.local_material_production import parse_local_material_plan

    body = parse_local_material_plan(canonical_object(plan_revision.body).encode('utf-8'))
    sources = ports.local_material_plan_sources(ordinary_lease,
        script_revision_id=body.source_script_revision_ref.revision_id,
        source_script_origin=body.source_script_origin,
        selected_route_ids=tuple(r.route_id for r in body.selected_capabilities))
    plan = restore_local_plan(plan_revision, **vars(sources))
    rights = require_local_plan_rights(production_rights_fact, plan_admission, plan_revision, plan,
        services=services, ports=ports, lease=ordinary_lease, request=request)
    selection = ports.local_master_selection(ordinary_lease, plan_revision_id=plan_revision.revision_id)
    if (type(selection) is not LocalMasterSelectionV1 or selection.plan_revision_ref != revision_ref(plan_revision)
            or selection.request_ref != plan.request_ref or selection.outputs != request.outputs):
        raise EngineError('local_composition_selection_invalid', 'Use the actual current same-plan applicable selection.', 409)
    master = _completed(engine.read_step(ordinary_lease, 'media-master'))
    if (master is None or master['result'].get('media_roles') != media_roles
            or tuple(media_roles) != selection.master_roles
            or len(set(media_roles.values())) != len(media_roles) or set(master.get('asset_ids', ())) != set(media_roles.values())):
        raise EngineError('local_composition_masters_missing', 'Caller IDs alone cannot replace the successful applicable master Step.', 409)
    narration_steps = [('production-narration', ('narration_audio',))] if 'narration_audio' in selection.master_roles else []
    visual_steps = [('production-' + s.shot_id, (s.shot_id,)) for s in plan.timeline.shots] if selection.content_kind == 'video' else []
    edit_roles = tuple(role for role in selection.master_roles if role != 'narration_audio')
    expected = [*narration_steps, *visual_steps, ('production-edit', edit_roles)]
    expected_steps = [key for key, _roles in expected]
    if master['result'].get('source_steps') != expected_steps or master['result'].get('local_plan_revision_ref') != revision_ref(plan_revision).model_dump(mode='json'):
        raise EngineError('local_composition_lineage_invalid', 'Master lineage belongs to this exact immutable local plan.', 409)
    by_step = {}
    clips = []
    for key, roles in expected:
        step = _completed(engine.read_step(ordinary_lease, key))
        if (step is None or step['result'].get('roles') != list(roles)
                or step['result'].get('local_plan_revision_ref') != revision_ref(plan_revision).model_dump(mode='json')
                or type(step['result'].get('provider_observation_sha256')) is not str
                or len(step['result']['provider_observation_sha256']) != 64
                or len(step.get('asset_ids', ())) != len(roles)):
            raise EngineError('local_composition_lineage_invalid', 'Each derivative has its original completed Step and settled-observation commitment.', 409)
        actual_roles = dict(zip(roles, step['asset_ids'], strict=True))
        if any(actual_roles[role] != media_roles[role] for role in roles if role in media_roles):
            raise EngineError('local_composition_lineage_conflict', 'Every master comes from the exact successful registered derivative Step.', 409)
        by_step[key] = step
        if key not in {'production-narration', 'production-edit'}:
            clips.append((roles[0], bundle.asset(ordinary_lease, actual_roles[roles[0]])))
    script = sources.original_script[1]
    script_ref = sources.original_script[0]
    refs = (script_ref, revision_ref(plan_revision), revision_ref(quality_revision))
    if quality_revision.body.get('local_plan_revision_ref') != refs[1].model_dump(mode='json'):
        raise EngineError('local_composition_quality_conflict', 'Actual quality revision retains this original local plan.', 409)
    if quality_revision.body.get('observed_masters') is None:
        raise EngineError('local_composition_quality_missing', 'Actual master observations remain independent of final evidence qualification.', 409)
    return {'services': services, 'selection': selection, 'plan': plan, 'script_revision': script, 'plan_revision': plan_revision,
        'quality_revision': quality_revision, 'creative_revision_refs': refs,
        'media_assets': {role: bundle.asset(ordinary_lease, identifier) for role, identifier in media_roles.items()},
        'derivative_clips': tuple(clips), 'source_steps': by_step,
        'source_records': source_timeline_records(plan), 'request': request,
        'request_sha256': digest(canonical(request)), 'rights_fact': rights,
        'approval_refs': bundle.approval_refs(ordinary_lease), 'feedback_refs': bundle.feedback_refs(ordinary_lease)}


def observe_local_audio_coordinates(composition, bundle, ordinary_lease, media):
    """Actual measured clocks are separate from planned source/display ranges."""
    from video_creator.domain import contracts as c

    result = {}
    for role in ('video', 'narration_audio', 'mixed_audio'):
        asset = composition['media_assets'].get(role)
        if asset is None or not asset.probe.has_audio:
            continue
        path = bundle.content_path(ordinary_lease, asset.asset_id)
        clock, duration = media.clock(asset, path)
        track = c.AudioTrackRef(asset_id=asset.asset_id, sha256=asset.sha256, stream_index=clock.stream_index,
            kind={'video': 'video_encoded', 'narration_audio': 'narration', 'mixed_audio': 'mix_master'}[role],
            intrinsic_duration_us=duration, clock=clock, method_ref='actual-decoder')
        if not media.audio_clock_authority(track, path):
            raise EngineError('local_audio_clock_invalid', 'The actual registered clock must independently re-decode.', 422)
        if role in {'narration_audio', 'mixed_audio'} and duration != composition['plan'].timeline.duration_us:
            raise EngineError('local_audio_duration_invalid', 'Whole final audio duration differs from the actual approved timeline.', 422)
        result[role] = track
    return result


def bind_local_actual_transcript(composition, *, actual, original_observation, original_context_bytes,
        expected_audio_asset, media_track):
    """Exact complete validation; source script is never used as recognition."""
    from video_creator.providers.local_asr import validate_original_asr_result

    if (original_observation.status != 'succeeded' or original_observation.result_json != actual
            or expected_audio_asset.asset_id != composition['media_assets']['mixed_audio'].asset_id
            or media_track.asset_id != expected_audio_asset.asset_id or media_track.sha256 != expected_audio_asset.sha256):
        raise EngineError('local_transcript_source_conflict', 'Consume the original controlled successful final-mix ASR and actual track.', 409)
    validate_original_asr_result(actual, original_context_bytes)
    if (actual['input_audio_sha256'] != expected_audio_asset.sha256
            or actual['duration_us'] != media_track.intrinsic_duration_us):
        raise EngineError('local_transcript_audio_conflict', 'Final ASR binds the actual mix bytes and sample timeline.', 422)
    # Actual text/segments/words remain unchanged. Their original controlled
    # journal/settled Operation and strict context are still caller prerequisites.
    return actual


def retrieval_source_windows(composition, *, document, alignment, mapping):
    """Join real recognized units to actual plan source windows, without a P95.

    This returns private composer inputs, not Ready RAG documents. Publication
    still requires the sole local artifact/output mapping, complete Alignment
    gates, final authority and immutable actual Bundle verification.
    """
    from video_creator.workflows.registered_alignment import aligned_document

    if (alignment.input_audio_sha256 != composition['media_assets']['mixed_audio'].sha256
            or document.transcript.input_audio_sha256 != alignment.input_audio_sha256
            or alignment.actual_transcript_revision_id != document.transcript.transcript_revision_id
            or alignment.transcript_content_sha256 != document.transcript.content_sha256):
        raise EngineError('local_retrieval_alignment_conflict', 'Use actual final-mix alignment, never source-script proportional times.', 422)
    if (not mapping.pieces or any(p.source_track.sha256 != alignment.input_audio_sha256 for p in mapping.pieces)
            or mapping.target_video_asset_id != composition['media_assets']['video'].asset_id):
        raise EngineError('local_retrieval_mapping_conflict', 'Use the actual measured sample-to-work mapping.', 422)
    updated, _srt, _vtt, ranges = aligned_document(document, alignment, mapping)
    result = []
    for utterance in updated.transcript.utterances:
        span = ranges[utterance.utterance_id]
        shots = tuple(s for s in composition['plan'].timeline.shots
            if s.timeline_range.start_us < span.end_us and s.timeline_range.end_us > span.start_us)
        if not shots:
            raise EngineError('local_retrieval_source_missing', 'Actual recognized speech must overlap an explicit actual planned visual source.', 422)
        result.append({'text': utterance.text, 'text_origin': 'actual_final_mix_asr',
            'audio_intrinsic_range': utterance.intrinsic_range.model_dump(mode='json'),
            'work_range': span.model_dump(mode='json'), 'alignment_revision_id': alignment.alignment_revision_id,
            'source_script_revision_ref': composition['plan'].source_script_revision_ref.model_dump(mode='json'),
            'request_ref': composition['plan'].request_ref.model_dump(mode='json'),
            'source_windows': tuple({'shot_id': shot.shot_id, 'input_binding_id': shot.input_binding_id,
                'source_media_range': None if next(b for b in composition['plan'].input_bindings
                    if b.binding_id == shot.input_binding_id).media_type.startswith('image/') else shot.source_range.model_dump(mode='json'),
                'timeline_range': shot.timeline_range.model_dump(mode='json')} for shot in shots)})
    return tuple(result)
