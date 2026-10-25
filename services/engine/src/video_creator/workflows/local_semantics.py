"""Serialize actual local media/source joins; this module grants no authority.

Ready materials, rights, absence observations and acoustic precision are checked
by the held Backend verifier. User goals are labelled as user inputs, never as
recognized speech or a model insight. Old Bundle formats are unchanged.
"""
from __future__ import annotations

from video_creator.domain import contracts as c
from video_creator.domain.errors import EngineError
from video_creator.domain.local_bundle import (
    LocalActualTranscriptDocumentV1,
    LocalSpeechEvidenceV1,
    RagChunkLocalV2,
    SemanticSegmentLocalV2,
    ShotEvidenceLocalV1,
)


def record(value):
    from video_creator.application.bundles import record_sha

    return value.model_copy(update={'content_sha256': record_sha(value)})


def local_source_refs(composition):
    """Original article/topic/facts and complete input IDs, with no new claims."""
    from video_creator.application.bundles import local_fact_id

    request = composition['request']
    return tuple(c.BundleSourceRef(**value.model_dump(exclude={'confirmed_facts'}),
        binding_kind='provided_input', input_asset_ids=request.inputs.asset_ids,
        fact_refs=tuple(c.SourceFactRef(text=fact,
            source_revision=value.topic_revision or value.article_revision or 'caller-input',
            confirmation_kind='caller_asserted', local_fact_id=local_fact_id(value, fact))
            for fact in value.confirmed_facts)) for value in request.source_bindings)


def _actual_right(composition, right, source_refs):
    # A declaration is not a licence attestation; final verify still checks
    # actual rights evidence. Expiry in retrieval records must never disappear.
    if type(right) is not c.RightsSnapshot or right not in composition['rights_fact'].rights:
        raise EngineError('local_semantic_rights_conflict', 'Use an original currently checked local declaration.', 403)
    expiries = [value.expires_at_us for value in composition['rights_fact'].rights
        if value.expires_at_us is not None]
    expiries += [value.valid_until_us for value in source_refs if value.valid_until_us is not None]
    return min(expiries) if expiries else None


def _actual_shots(composition, shots):
    from video_creator.domain.local_bundle import local_shot_revision_id

    plan = composition['plan']
    expected = tuple(local_shot_revision_id(composition['creative_revision_refs'][1].content_sha256,
        value.shot_id) for value in plan.timeline.shots)
    if (type(shots) is not tuple or tuple(value.shot_revision_id for value in shots) != expected
            or any(type(value) is not ShotEvidenceLocalV1 or not value.frame_evidence_refs for value in shots)):
        raise EngineError('local_semantic_frames_required', 'Every actual plan shot needs its complete observed frame document.', 409)
    video = composition['media_assets'].get('video')
    for shot, planned in zip(shots, plan.timeline.shots, strict=True):
        if (video is None or shot.video_asset_id != video.asset_id or shot.timeline_range != planned.timeline_range
                or any(frame.video_asset_id != video.asset_id or frame.video_sha256 != video.sha256
                    or not shot.timeline_range.start_us <= frame.at_us < shot.timeline_range.end_us
                    for frame in shot.frame_evidence_refs)):
            raise EngineError('local_semantic_frames_conflict', 'Frames refer to the actual immutable final master and exact plan window.', 409)


def _speech_ranges(composition, speech, document, mapping):
    from video_creator.workflows.local_bundle_inputs import validate_no_speech_coverage
    from video_creator.workflows.registered_alignment import aligned_document

    if type(document) is not LocalActualTranscriptDocumentV1:
        raise EngineError('local_semantic_transcript_required', 'Actual speech states need the original local transcript document.', 409)
    mixed = composition['media_assets'].get('mixed_audio')
    transcript = document.transcript
    if (mixed is None or transcript.input_audio_asset_id != mixed.asset_id or transcript.input_audio_sha256 != mixed.sha256
            or (speech.input_audio_asset_id, speech.input_audio_sha256) != (mixed.asset_id, mixed.sha256)
            or document.speech_evidence_artifact_id is None):
        raise EngineError('local_semantic_audio_conflict', 'Transcript and speech evidence retain the actual final mix bytes.', 409)
    video = composition['media_assets'].get('video')
    if video is None:
        # The old mapping has a mandatory real video target. Its public
        # audio-only replacement belongs to Backend/Architecture, not here.
        raise EngineError('local_audio_mapping_not_ready', 'Audio-only work requires the sole real work-target audio mapping.', 503)
    if (type(mapping) is not c.AudioTimelineMapping or mapping.target_video_asset_id != video.asset_id
            or len(mapping.pieces) != 1 or mapping.timeline_duration_us != composition['plan'].timeline.duration_us):
        raise EngineError('local_semantic_mapping_required', 'Use the actual measured complete final-mix-to-video mapping.', 409)
    piece = mapping.pieces[0]
    if (piece.source_track != transcript.input_track or piece.source_range != piece.timeline_range
            or piece.source_range.start_us != 0 or piece.source_range.end_us != transcript.duration_us
            or piece.source_sample_start != 0 or piece.source_sample_end != transcript.input_track.clock.decoded_sample_count
            or piece.playback_rate_num != 1 or piece.playback_rate_den != 1):
        raise EngineError('local_semantic_mapping_conflict', 'This installed recipe only supports actual full identity placement.', 409)
    if speech.state == 'no_speech_observed':
        validate_no_speech_coverage(transcript)
        if document.alignment is not None or document.subtitles is not None:
            raise EngineError('local_no_speech_alignment_conflict', 'No-speech data cannot fabricate alignment units or cue tracks.', 409)
        return (), piece
    alignment = document.alignment
    if (alignment is None or document.subtitles is None or not transcript.text or not transcript.utterances
            or alignment.actual_transcript_revision_id != transcript.transcript_revision_id
            or alignment.transcript_content_sha256 != transcript.content_sha256
            or alignment.input_audio_sha256 != mixed.sha256):
        raise EngineError('local_semantic_alignment_required', 'Recognized speech requires complete original acoustic alignment and subtitles.', 409)
    updated, _srt, _vtt, ranges = aligned_document(document, alignment, mapping)
    return tuple((value, ranges[value.utterance_id]) for value in updated.transcript.utterances), piece


def observe_local_speech_frames(composition, bundle, lease, media, *, speech, document, mapping):
    """Sample the actual acoustic unit starts, not a nearby planned shot start."""
    from video_creator.providers.production_resources import file_sha256

    video = composition['media_assets'].get('video')
    if video is None or speech.state != 'speech_observed':
        return {}
    ranges, _piece = _speech_ranges(composition, speech, document, mapping)
    path = bundle.content_path(lease, video.asset_id)
    frames = {}
    for value, span in ranges:
        if path.stat().st_size != video.size or file_sha256(path) != video.sha256:
            raise EngineError('local_semantic_video_changed', 'The actual final master must remain immutable while sampled.', 409)
        frame = media.frame(video, path, span.start_us, 'actual-decoder')
        if (not media.frame_validator(frame, path) or file_sha256(path) != video.sha256
                or not span.start_us <= frame.at_us < span.end_us):
            raise EngineError('local_semantic_frame_invalid', 'Each speech segment needs its own actual independently decoded frame.', 422)
        frames[value.utterance_id] = (frame,)
    return frames


def build_local_semantics(composition, *, bundle_revision_id, access_scope_ref, right,
        speech, shots, transcript_document=None, mapping=None, speech_frames=None):
    """Create sole typed documents from actually observed inputs, without staging.

    This function is a serializer, not proof that a caller's evidence is valid.
    Production must retain the settled observations and both registered media
    authorities; Backend rechecks all of them at final verification.
    """
    if type(speech) is not LocalSpeechEvidenceV1:
        raise EngineError('local_speech_evidence_required', 'Presence and absence retain the sole complete speech evidence.', 409)
    _actual_shots(composition, shots)
    plan, request = composition['plan'], composition['request']
    source_refs = local_source_refs(composition)
    expiry = _actual_right(composition, right, source_refs)
    goal = request.goal
    topic, thesis = goal[:1000], goal[:10_000]
    summary = record(c.WorkSummary(bundle_revision_id=bundle_revision_id, summary=goal,
        topic=topic, main_thesis=thesis, source_refs=source_refs, content_sha256='0' * 64))
    sources = record(c.SourceBindingsDocument(bundle_revision_id=bundle_revision_id,
        source_refs=source_refs, content_sha256='0' * 64))
    video = composition['media_assets'].get('video')
    if speech.state == 'no_audio_observed':
        if (video is None or video.probe.has_audio or plan.timeline.audio_tracks
                or any(role in composition['media_assets'] for role in ('mixed_audio', 'narration_audio'))
                or transcript_document is not None or mapping is not None):
            raise EngineError('local_no_audio_conflict', 'No-audio output has real decoded video and no invented sound evidence.', 409)
        speech_ranges, piece = (), None
    else:
        speech_ranges, piece = _speech_ranges(composition, speech, transcript_document, mapping)
    windows = [(value.text, span, (value.utterance_id,)) for value, span in speech_ranges]
    if not windows:
        windows = [('', shot.timeline_range, ()) for shot in shots]
    segments = []
    for number, (text, span, unit_ids) in enumerate(windows):
        matching = tuple(shot for shot in shots if shot.timeline_range.start_us < span.end_us
            and shot.timeline_range.end_us > span.start_us)
        if video is not None and not matching:
            raise EngineError('local_semantic_source_missing', 'Every segment needs its actual planned visual source.', 409)
        frames = tuple(frame for shot in matching for frame in shot.frame_evidence_refs)
        if text and video is not None:
            frames = speech_frames.get(unit_ids[0], ()) if type(speech_frames) is dict else ()
            if (not frames or any(type(frame) is not c.FrameEvidenceRef or frame.video_asset_id != video.asset_id
                    or frame.video_sha256 != video.sha256 or not span.start_us <= frame.at_us < span.end_us for frame in frames)):
                raise EngineError('local_semantic_speech_frame_required', 'Retain the actual decoded frame for this acoustic segment.', 409)
        visual = '; '.join(f'Decoded frame at {frame.at_us}us: {frame.width}x{frame.height} {frame.pixel_format}'
            for frame in frames)
        audio_spans = (c.SemanticAudioSpan(track=piece.source_track, intrinsic_range=span,
            timeline_range=span, mapping_piece_ids=(piece.piece_id,)),) if piece is not None else ()
        segment_summary = text or goal
        segments.append(record(SemanticSegmentLocalV2(segment_id=f'local-segment-{number}',
            bundle_revision_id=bundle_revision_id, timeline_range=span,
            video_asset_id=video.asset_id if video is not None else None, video_range=span if video is not None else None,
            audio_spans=audio_spans, shot_revision_ids=tuple(value.shot_revision_id for value in matching),
            transcript_unit_refs=unit_ids, speech_text=text, visual_description=visual,
            summary=segment_summary, topic=topic, main_thesis=thesis, source_refs=source_refs,
            alignment_revision_id=transcript_document.alignment.alignment_revision_id if text else None,
            field_provenance={'speech_text': 'observed' if text else 'derived', 'summary': 'derived' if text else 'user_provided',
                'visual_description': 'observed', 'topic': 'derived', 'main_thesis': 'derived'},
            frame_evidence_refs=frames, rights_ref=right.rights_id, valid_until_us=expiry,
            retrieval_text=f'{goal}\n{segment_summary}\n{visual}', content_sha256='0' * 64)))
    chunks = [record(RagChunkLocalV2(chunk_id='local-work-summary', chunk_type='work_summary',
        bundle_revision_id=bundle_revision_id, segment_ids=tuple(value.segment_id for value in segments),
        text=goal, source_refs=source_refs, video_ranges=tuple(value.video_range for value in segments if value.video_range is not None),
        audio_spans=tuple(span for value in segments for span in value.audio_spans), language=transcript_document.transcript.language
        if transcript_document is not None else 'und', rights_ref=right.rights_id, access_scope_ref=access_scope_ref,
        valid_until_us=expiry, field_provenance={'text': 'user_provided'},
        method_refs=('local-approved-plan-v1',), content_sha256='0' * 64))]
    for number, segment in enumerate(segments):
        chunk_type = 'speech_segment' if segment.speech_text else 'visual_segment' if video is not None else 'audio_segment'
        chunks.append(record(RagChunkLocalV2(chunk_id=f'local-chunk-{number}', chunk_type=chunk_type,
            bundle_revision_id=bundle_revision_id, segment_ids=(segment.segment_id,), text=segment.retrieval_text,
            source_refs=source_refs, video_ranges=(segment.video_range,) if segment.video_range is not None else (),
            audio_spans=segment.audio_spans, language=transcript_document.transcript.language
            if transcript_document is not None else 'und', rights_ref=right.rights_id, access_scope_ref=access_scope_ref,
            valid_until_us=expiry, field_provenance={'text': 'derived'},
            method_refs=tuple(dict.fromkeys((*speech.method_refs, 'actual-decoder'))), content_sha256='0' * 64)))
    return {'summary': summary, 'sources': sources, 'shots': shots, 'segments': tuple(segments), 'rag': tuple(chunks)}
