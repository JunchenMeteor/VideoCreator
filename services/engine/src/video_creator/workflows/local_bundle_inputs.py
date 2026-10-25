"""Actual held local Bundle inputs, before the sole 0.4 material schema.

These private composer values do not grant rights, create Ready materials, or
replace Backend selection/prepare/verify. Original ASR bytes remain unchanged.
"""
from video_creator.application.asr_result_journal import AsrResultJournal
from video_creator.application.engine import canonical, digest
from video_creator.application.local_material_sources import LocalMaterialFinalContext
from video_creator.domain import contracts as c
from video_creator.domain.current_final_evidence import CurrentFinalAsrRead
from video_creator.domain.errors import EngineError
from video_creator.domain.local_bundle import (
    LocalVisualMappingDocumentV1,
    ShotEvidenceLocalV1,
    local_shot_revision_id,
)
from video_creator.domain.production_authorization import (
    CurrentProductionAdmission,
    ProductionRightsFact,
)
from video_creator.media.local_frame_grid import frame_index, frame_time_us
from video_creator.providers.production_resources import file_sha256
from video_creator.workflows.local_material_composition import (
    bind_local_actual_transcript,
    read_local_composition,
)
from video_creator.workflows.local_material_production import (
    LocalMaterialPolicyServices,
    LocalMaterialServices,
)


def admission_identity(admission):
    """Immutable identity of one admission decision, never its live clock.

    `CurrentProductionAdmission` carries the live observation interval
    (`checked_at_us`/`valid_until_us`) that the ports recompute on every real
    read. Those two fields are when the decision was observed, not what was
    decided: comparing them across a database round-trip or a later clock would
    reject the same stored decision. Everything else (instance/run/request
    binding, phase/action, target revision and fence, source branch and its
    committed refs) is the actual held decision identity.
    """
    if type(admission) is not CurrentProductionAdmission:
        raise EngineError('local_final_facts_invalid',
                          'Use the original typed production admission, not a projection.', 409)
    return (admission.state, admission.phase, admission.action,
            admission.instance_id, admission.production_id, admission.run_id,
            admission.request_revision_id, admission.request_sha256, admission.registration_sha256,
            admission.target_id, admission.target_sha256, admission.fencing_token, admission.source,
            _ref(admission.human_approval_ref), _ref(admission.policy_ref),
            _ref(admission.owner_action_ref), _ref(admission.admission_ref), admission.blocker_code)


def rights_identity(fact):
    """Immutable identity of the rights decision, never its live clock.

    Same rule as `admission_identity`: the declaration id/sha, policy/action
    refs, fencing token and the actual `RightsSnapshot` tuple are the decision;
    `checked_at_us`/`valid_until_us` are only when it was observed.
    """
    if type(fact) is not ProductionRightsFact:
        raise EngineError('local_final_facts_invalid',
                          'Use the original typed production rights fact, not a projection.', 409)
    return (fact.instance_id, fact.production_id, fact.run_id, fact.request_revision_id,
            fact.request_sha256, fact.plan_revision_id, fact.declaring_subject, fact.declaration_id,
            fact.declaration_sha256, tuple(canonical(right) for right in fact.rights),
            fact.source, _ref(fact.human_approval_ref), _ref(fact.policy_ref),
            _ref(fact.owner_action_ref), fact.fencing_token)


def _ref(value):
    return None if value is None else canonical(value)


def require_held_final_facts(context, *, plan_admission, production_rights_fact):
    """409 unless the caller facts are the same immutable held decisions.

    Callers build their plan/rights facts independently of the held context, so
    two real reads of the same stored decision differ only in the observed
    validity clock. Compare identities, never the live timestamped objects.
    """
    if (admission_identity(plan_admission) != admission_identity(context.plan_admission)
            or rights_identity(production_rights_fact) != rights_identity(context.production_rights_fact)):
        raise EngineError('local_final_facts_conflict',
                          'Caller plan/rights facts must be the actual held current decisions.', 409)


def read_local_final_inputs(services, ordinary_lease, *, local_material_context, media_roles):
    """Re-read the seven actual held facts on the original current lease."""
    if (type(services) not in {LocalMaterialServices, LocalMaterialPolicyServices}
            or type(local_material_context) is not LocalMaterialFinalContext):
        raise EngineError('local_final_context_denied', 'Use the actual registered local services and sole held final context.', 403)
    ports = services.production_ports if type(services) is LocalMaterialServices else services.policy_execution_ports
    current = ports.local_material_final_context(ordinary_lease)
    # Compare the actual re-read facts after a real current read: persisted
    # revisions and sources are immutable values, while the three live
    # admission/rights facts are compared by their held-decision identity only.
    # The held context is frozen and eq=False, so object equality would always
    # fail and timestamp equality would always fail for a second real read.
    if (type(current) is not LocalMaterialFinalContext
            or current.sources != local_material_context.sources
            or current.plan != local_material_context.plan
            or current.plan_revision != local_material_context.plan_revision
            or current.quality_revision != local_material_context.quality_revision
            or admission_identity(current.plan_admission) != admission_identity(local_material_context.plan_admission)
            or admission_identity(current.quality_admission) != admission_identity(local_material_context.quality_admission)
            or rights_identity(current.production_rights_fact) != rights_identity(local_material_context.production_rights_fact)):
        raise EngineError('local_final_context_changed', 'Original current source/admission facts changed before assembly.', 409)
    if (current.plan_revision[0].kind != 'plan'
            or current.plan_revision[0].revision_id != current.plan_revision[1].revision_id
            or current.plan_revision[0].content_sha256 != digest(canonical(current.plan_revision[1]))):
        raise EngineError('local_final_context_invalid', 'Retain the actual plan revision pair.', 409)
    composition = read_local_composition(services, ordinary_lease, media_roles=media_roles,
        plan_admission=current.plan_admission, production_rights_fact=current.production_rights_fact)
    if (composition['plan'] != current.plan or composition['plan_revision'] != current.plan_revision[1]
            or composition['quality_revision'] != current.quality_revision[1]
            or composition['script_revision'] != current.sources.original_script[1]):
        raise EngineError('local_final_sources_changed', 'The complete original plan/script/quality must match the held final context.', 409)
    return composition


def visual_mapping_inputs(plan):
    """Exact source/display coordinates for the sole LocalVisualMapping DTO."""
    bindings = {value.binding_id: value for value in plan.input_bindings}
    timeline, rows, cursor = plan.timeline, [], 0
    for shot in timeline.shots:
        binding = bindings[shot.input_binding_id]
        n0 = frame_index(shot.timeline_range.start_us, timeline.fps_num, timeline.fps_den)
        n1 = frame_index(shot.timeline_range.end_us, timeline.fps_num, timeline.fps_den)
        if n0 != cursor or n1 <= n0:
            raise EngineError('local_visual_mapping_invalid', 'Each actual approved shot covers its contiguous integer frame interval.', 422)
        still = binding.media_type in {'image/jpeg', 'image/png'}
        hold = shot.timeline_range.end_us - shot.timeline_range.start_us
        if still and (binding.probe.has_video or binding.probe.has_audio or binding.probe.duration_us is not None
                or not binding.probe.decoded or not binding.probe.width or not binding.probe.height
                or shot.source_range.start_us != 0 or shot.source_range.end_us != hold):
            raise EngineError('local_static_mapping_invalid', 'Image display hold must not be represented as measured source time.', 422)
        if not still and (binding.media_type != 'video/mp4' or not binding.probe.has_video
                or binding.probe.duration_us is None or shot.source_range.end_us > binding.probe.duration_us):
            raise EngineError('local_video_mapping_invalid', 'Original video ranges stay inside their actual decoded source.', 422)
        rows.append({'shot_id': shot.shot_id, 'input_binding_id': binding.binding_id,
            'source_asset_id': binding.asset_id, 'source_sha256': binding.sha256,
            'source_media_range': None if still else shot.source_range.model_dump(mode='json'),
            'display_hold_us': hold if still else None,
            'timeline_range': shot.timeline_range.model_dump(mode='json'), 'frame_start': n0, 'frame_end': n1})
        cursor = n1
    if rows and frame_time_us(cursor, timeline.fps_num, timeline.fps_den) != timeline.duration_us:
        raise EngineError('local_visual_mapping_invalid', 'Actual final frame boundary must equal the approved work duration.', 422)
    if not rows:
        raise EngineError('local_visual_mapping_not_applicable', 'Audio-only works have no visual mapping document.', 422)
    return LocalVisualMappingDocumentV1.model_validate({'format': 'local-visual-mapping-v1',
        'fps_num': timeline.fps_num, 'fps_den': timeline.fps_den,
        'timeline_duration_us': timeline.duration_us, 'rows': rows})


def observe_local_frames(composition, bundle, ordinary_lease, media):
    """Actual final-frame bytes; plan records never impersonate storyboard."""
    video = composition['media_assets'].get('video')
    if video is None:
        return ()
    path = bundle.content_path(ordinary_lease, video.asset_id)
    result = []
    for shot in composition['plan'].timeline.shots:
        if path.stat().st_size != video.size or file_sha256(path) != video.sha256:
            raise EngineError('local_final_video_changed', 'Frame sampling uses the actual immutable final master.', 409)
        frame = media.frame(video, path, shot.timeline_range.start_us, 'actual-decoder')
        if not media.frame_validator(frame, path) or file_sha256(path) != video.sha256:
            raise EngineError('local_frame_evidence_invalid', 'Each real sampled frame must pass the original frame authority.', 422)
        # ADR0075's deterministic shot record ID is not a Creative revision.
        shot_id = local_shot_revision_id(composition['creative_revision_refs'][1].content_sha256, shot.shot_id)
        from video_creator.workflows.local_semantics import local_source_refs, record

        result.append(record(ShotEvidenceLocalV1(shot_revision_id=shot_id, video_asset_id=video.asset_id,
            timeline_range=shot.timeline_range, source_refs=local_source_refs(composition),
            frame_evidence_refs=(frame,), content_sha256='0' * 64)))
    return tuple(result)


def actual_transcript_from_journal(composition, ordinary_lease, *, journal, operation_id,
        input_track, transcript_revision_id):
    """Original settled ASR/full context, with no new inference or expected data."""
    if (type(journal) is not AsrResultJournal or journal is not composition['services'].executor.journal
            or journal.engine is not composition['services'].engine or journal.worker is not composition['services'].worker):
        raise EngineError('local_original_asr_required', 'Use the original registered same-instance ASR journal.', 403)
    facts = journal.read_settled_original_asr(ordinary_lease, operation_id)
    request_ref = composition['plan'].request_ref
    if (type(facts) is not CurrentFinalAsrRead or facts.status != 'succeeded' or not facts.settled
            or (facts.operation_id, facts.run_id, facts.production_id) != (
                operation_id, ordinary_lease.run_id, request_ref.production_id)
            or facts.allocation.operation_id != operation_id or facts.allocation.run_id != ordinary_lease.run_id):
        raise EngineError('local_original_asr_required', 'Only the actual successful settled journal and its original committed context are consumable.', 409)
    actual = bind_local_actual_transcript(composition, actual=facts.observation.result_json,
        original_observation=facts.observation, original_context_bytes=facts.original_context_bytes,
        expected_audio_asset=composition['media_assets']['mixed_audio'], media_track=input_track)
    utterances = tuple(c.TranscriptUtterance(utterance_id=f'utterance-{number}', text=segment['text'],
        intrinsic_range=c.MediaRange(start_us=segment['start_us'], end_us=segment['end_us']),
        words=tuple(c.TranscriptWord(word_id=f'word-{number}-{index}', text=word['text'],
            intrinsic_range=c.MediaRange(start_us=word['start_us'], end_us=word['end_us']),
            timestamp_method=actual['timestamp_method']) for index, word in enumerate(segment['words'])))
        for number, segment in enumerate(actual['segments']))
    from video_creator.application.bundles import record_sha
    from video_creator.workflows.bundle_v03 import runtime_source_gaps

    method = actual['runtime']['execution_identity']['method_id']
    transcript = c.ActualTranscriptRevision(transcript_revision_id=transcript_revision_id,
        input_audio_asset_id=input_track.asset_id, input_audio_sha256=input_track.sha256, input_track=input_track,
        duration_us=actual['duration_us'], language=actual['language'], text=actual['text'], utterances=utterances,
        method_ref=method, approved_script_revision_ref=composition['plan'].source_script_revision_ref,
        confidence_unavailable_reason='Actual ASR has no calibrated transcript confidence.',
        source_gaps=runtime_source_gaps(actual), content_sha256='0' * 64)
    transcript = transcript.model_copy(update={'content_sha256': record_sha(transcript)})
    # A nonempty complete transcript is speech observed. Current frozen ASR
    # rejects empty inference; never convert its error into no_speech evidence.
    return transcript, facts


def validate_no_speech_coverage(transcript):
    """Coverage check only, AFTER a real admitted no-speech observer is verified.

    This check is not an observer, source attestation or authority. Current
    frozen ASR does not provide such an observation; that path remains NOT_READY.
    """
    if type(transcript) is not c.ActualTranscriptRevision or transcript.text or transcript.utterances:
        raise EngineError('local_no_speech_unconfirmed', 'A supplied string cannot replace the complete actual transcript document.', 409)
    cursor = 0
    for gap in transcript.gaps:
        if (gap.classification not in {'no_speech', 'music'} or gap.method_ref != transcript.method_ref
                or gap.intrinsic_range.start_us != cursor):
            raise EngineError('local_no_speech_unconfirmed', 'Observed no-speech/music gaps must cover the complete actual audio without gaps.', 409)
        cursor = gap.intrinsic_range.end_us
    if cursor != transcript.duration_us:
        raise EngineError('local_no_speech_unconfirmed', 'The complete real audio must have an explicit successful absence observation.', 409)


def zero_cue_subtitle_bytes(transcript):
    """Serialize the two actual zero-cue materials for one admitted absence.

    `transcript` is a required argument, not an option: the bytes exist only
    AFTER a complete real no-speech `ActualTranscriptRevision` covers the whole
    audio (`validate_no_speech_coverage`). Local 0.4 has no zero-cue branch
    (统筹裁定 2026-10-25) and no production caller of this serializer, so there
    is deliberately no way to obtain empty subtitle documents for an
    unobserved or unadmitted work.
    """
    from video_creator.application.bundles import validate_text

    validate_no_speech_coverage(transcript)
    # An SRT without cues has no header, so its complete document is one LF;
    # the VTT keeps its required header. Both parse under the sole grammar.
    srt, vtt = b'\n', b'WEBVTT\n\n'
    if (validate_text(srt, 'srt_local', 'text/srt') != '\n'
            or validate_text(vtt, 'vtt_local', 'text/vtt') != 'WEBVTT\n\n'):
        raise EngineError('local_empty_subtitles_invalid',
                          'Zero-cue subtitle materials must parse as the sole admitted local grammar.', 422)
    return srt, vtt
