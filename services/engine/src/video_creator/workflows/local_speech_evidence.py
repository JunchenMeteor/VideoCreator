"""Real local speech materials: admitted ASR Operation -> transcript/alignment/subtitles.

Media side of ADR0080/ADR0082: one real settled ASR Operation on the final mix,
`AlignmentRevisionV03` with `units='utterance'` and `precision='not_measured'`,
and subtitles serialized by the sole Bundle serializer (no second formatter).
No CTC lineage, no self-issued benchmark or policy is invented here.
"""
from __future__ import annotations

import json
from decimal import Decimal
from fractions import Fraction

from video_creator.application.engine import digest
from video_creator.domain import contracts as c
from video_creator.domain.errors import EngineError
from video_creator.domain.local_bundle import (
    LocalActualTranscriptDocumentV1,
    LocalSpeechEvidenceV1,
)
from video_creator.workflows.attempt_control import current_attempt

SPEECH_LIMITATIONS = ('whisper_word_estimate_not_forced_alignment',
                      'precision_not_measured', 'local_self_issued_evidence')
ASR_STEP_KEY = 'local-final-asr'


def _record(model):
    from video_creator.application.bundles import record_sha
    return model.model_copy(update={'content_sha256': record_sha(model)})


def require_settled(operation):
    """Only an actually settled successful ASR Operation may yield materials."""
    if type(operation) is not dict or operation.get('settled') is not True:
        raise EngineError('local_asr_unsettled',
                          'Only a settled successful ASR Operation may enter the speech materials.', 409, 'reconcile')
    if operation.get('status') != 'succeeded':
        raise EngineError('local_asr_unavailable',
                          'Keep the original controlled ASR outcome; reconcile before resubmitting.', 409, 'reconcile')
    if type(operation.get('id')) is not str or not operation['id']:
        raise EngineError('local_asr_unsettled', 'The settled ASR Operation needs its actual identity.', 409, 'reconcile')
    return operation


def run_local_asr(engine, executor, media, lease, *, mixed_asset, mixed_path, asr_route_id,
                  asr_resources, runtime_root, timeout_seconds=600):
    """Registered, journalled ASR on the final mix; returns (actual, operation, input, resources)."""
    control = current_attempt()
    if type(asr_route_id) is not str or not asr_route_id:
        raise EngineError('local_asr_route_missing',
                          'A registered zero-cost local transcription route is required for speech works.', 503)
    route = engine.configured_route(asr_route_id)
    if (route.source != 'owned_local' or route.capability != 'transcription'
            or route.credential_ref is not None or route.max_operation_cost.units()
            or not route.destination.startswith('local:')):
        raise EngineError('local_asr_route_denied',
                          'Only the original credential-free zero-cost local ASR route is admitted.', 403)
    resources = asr_resources() if callable(asr_resources) else asr_resources
    if resources is None:
        raise EngineError('production_asr_resource_required',
                          'Actual final transcript/subtitle/RAG requires installed ASR resources.', 503)
    # The worker accepts exactly its own MODEL_FILES set; a documentation file in
    # the installed manifest is not a model file and must not be claimed as one.
    from video_creator.providers.local_asr import MODEL_FILES

    model_files = {name: resources.model_file_sha256.get(name) for name in MODEL_FILES}
    if any(type(value) is not str for value in model_files.values()):
        raise EngineError('local_asr_model_missing',
                          'The installed ASR model must provide every admitted model file.', 503)
    driver = resources.driver(mixed_path, storage_root=media.root, runtime_root=runtime_root,
        expected_audio_sha256=mixed_asset.sha256, expected_model_files=model_files,
        timeout_seconds=control.remaining(timeout_seconds),
        cancel=control.cancel_requested, deadline_monotonic=control.deadline_monotonic)
    operation_input = digest(json.dumps({'audio_sha256': mixed_asset.sha256,
        'resource_manifest_sha256': resources.manifest_sha256}, sort_keys=True))
    engine.begin_step(lease, ASR_STEP_KEY, operation_input)
    intent = c.OperationIntent(step_key=ASR_STEP_KEY, dedupe_key='local-final-asr-' + lease.run_id,
        input_sha256=operation_input, route_id=asr_route_id, reserved_cost=c.Money(amount='0'))
    control.check()
    observation = executor.execute(lease, intent, driver)
    if observation.status != 'succeeded' or type(observation.result_json) is not dict:
        raise EngineError('local_asr_unavailable',
                          'Keep the original unknown/pending ASR outcome; do not create another attempt.', 409,
                          'reconcile' if observation.status in {'unknown', 'pending'} else 'never')
    operation = require_settled(engine.prepare_operation(lease, intent))
    actual = observation.result_json
    from video_creator.providers.local_asr import validate_original_asr_result

    validate_original_asr_result(actual, driver.validation_context_bytes())
    if (actual.get('input_audio_sha256') != mixed_asset.sha256
            or actual.get('duration_us') != mixed_asset.probe.duration_us
            or not isinstance(actual.get('runtime', {}).get('execution_identity'), dict)):
        raise EngineError('local_asr_binding_invalid',
                          'Actual ASR must bind this final mix and observe its execution identity.', 422)
    if type(actual.get('text')) is not str or not actual['text'].strip() or not actual.get('segments'):
        raise EngineError('local_transcript_incomplete',
                          'A speech work needs actual recognized segments, not an empty transcript.', 422)
    engine.complete_step(lease, ASR_STEP_KEY, result_json=actual)
    return actual, operation, operation_input, resources


def build_local_speech_materials(*, composition, assets, tracks, actual, operation, operation_input,
                                 resources, artifact_ids, ids, video_track=None):
    """Typed speech documents from the settled observation; no invented facts.

    `ids` carries transcript/alignment/subtitle/mapping revision ids; artifact
    ids come from the producer's sole allocation table.
    """
    from video_creator.application.bundles import serialize_subtitles
    from video_creator.workflows.bundle_v03 import runtime_source_gaps

    control = current_attempt()
    control.check()
    if (type(actual.get('text')) is not str or not actual['text'].strip()
            or not isinstance(actual.get('segments'), list) or not actual['segments']):
        raise EngineError('local_transcript_incomplete',
                          'A speech work needs actual recognized segments, not an empty transcript.', 422)
    mixed = assets['mixed']
    track = tracks['mixed']
    identity = c.AlignmentExecutionIdentity.model_validate(actual['runtime']['execution_identity'])
    script_ref = composition['creative_revision_refs'][0]
    utterances = tuple(c.TranscriptUtterance(utterance_id=f'utterance-{index}', text=segment['text'],
        intrinsic_range=c.MediaRange(start_us=segment['start_us'], end_us=segment['end_us']),
        words=tuple(c.TranscriptWord(word_id=f'word-{index}-{number}', text=word['text'],
            intrinsic_range=c.MediaRange(start_us=word['start_us'], end_us=word['end_us']),
            timestamp_method=actual['timestamp_method'])
            for number, word in enumerate(segment['words'])))
        for index, segment in enumerate(actual['segments']))
    transcript = _record(c.ActualTranscriptRevision(transcript_revision_id=ids['transcript'],
        input_audio_asset_id=mixed.asset_id, input_audio_sha256=mixed.sha256, input_track=track,
        duration_us=actual['duration_us'], language=actual['language'], text=actual['text'],
        utterances=utterances, method_ref=identity.method_id,
        approved_script_revision_ref=script_ref,
        confidence_unavailable_reason='The admitted ASR does not provide a calibrated transcript confidence.',
        source_gaps=runtime_source_gaps(actual), content_sha256='0' * 64))
    alignment = _record(c.AlignmentRevisionV03(alignment_revision_id=ids['alignment'],
        actual_transcript_revision_id=transcript.transcript_revision_id,
        transcript_content_sha256=transcript.content_sha256,
        input_audio_asset_id=mixed.asset_id, input_audio_sha256=mixed.sha256, units='utterance',
        boundaries=tuple(c.AlignmentUnit(unit_id=f'alignment-{index}',
            transcript_unit_id=value.utterance_id, intrinsic_range=value.intrinsic_range)
            for index, value in enumerate(utterances)),
        timestamp_method=actual['timestamp_method'], method_ref=identity.method_id,
        precision=c.PrecisionAssessmentV03(status='not_measured', units='utterance',
            limitations=SPEECH_LIMITATIONS),
        confidence_unavailable_reason='Independent timing confidence has not been measured.',
        content_sha256='0' * 64))
    if video_track is None:
        raise EngineError('local_audio_work_mapping_required',
                          'Audio-only work requires the approved real work-target mapping contract.', 503)
    timeline = composition['plan'].timeline.duration_us
    raw_end = Fraction(track.clock.decoded_sample_count * 1_000_000, track.clock.sample_rate)
    end_error = Decimal(timeline) - Decimal(raw_end.numerator) / Decimal(raw_end.denominator)
    piece = c.AudioMappingPiece(piece_id='local-mix-placement', source_track=track,
        source_range=c.MediaRange(start_us=0, end_us=timeline),
        timeline_range=c.MediaRange(start_us=0, end_us=timeline),
        source_sample_start=0, source_sample_end=track.clock.decoded_sample_count,
        transformation='encode', end_rounding_error_us=end_error, method_ref='actual-decoder')
    if Fraction(video_track.clock.origin_pts or 0) * Fraction(
            video_track.clock.timebase_num or 1, video_track.clock.timebase_den or 1) != 0:
        raise EngineError('local_audio_mapping_required',
                          'A nonzero encoded audio origin needs its separately verified mapping.', 409)
    mapping = _record(c.AudioTimelineMapping(mapping_revision_id=ids['mapping'],
        target_video_asset_id=assets['video'].asset_id, target_track=video_track,
        timeline_duration_us=timeline, pieces=(piece,), encoding_origin_offset_us=0,
        method_ref='actual-decoder', content_sha256='0' * 64))
    cues = tuple(c.SubtitleCue(cue_id=f'cue-{index}', text=value.text,
        timeline_range=value.intrinsic_range, transcript_unit_refs=(value.utterance_id,))
        for index, value in enumerate(utterances))
    subtitles = c.SubtitleTrack(subtitle_revision_id=ids['subtitle'],
        actual_transcript_revision_id=transcript.transcript_revision_id,
        alignment_revision_id=alignment.alignment_revision_id,
        mapping_revision_id=mapping.mapping_revision_id, timeline_duration_us=timeline, cues=cues,
        srt_artifact_id=artifact_ids['Text/subtitles.srt'],
        vtt_artifact_id=artifact_ids['Text/subtitles.vtt'],
        quantization_errors=tuple(c.SubtitleQuantization(cue_id=value.cue_id, start_error_us=0, end_error_us=0)
            for value in cues), content_sha256='0' * 64)
    srt, vtt, quantization = serialize_subtitles(subtitles)
    subtitles = _record(subtitles.model_copy(update={'quantization_errors': tuple(quantization)}))
    if serialize_subtitles(subtitles)[:2] != (srt, vtt):
        raise EngineError('local_subtitle_serialization_invalid',
                          'Subtitle bytes must be the sole serializer output for this transcript.', 422)
    for cue, utterance in zip(subtitles.cues, transcript.utterances, strict=True):
        if cue.text != utterance.text or cue.transcript_unit_refs != (utterance.utterance_id,):
            raise EngineError('local_subtitle_transcript_conflict',
                              'Each cue must retain its exact transcript unit text and identity.', 422)
    document = _record(LocalActualTranscriptDocumentV1(
        speech_evidence_artifact_id=artifact_ids['Checks/local-speech-evidence.json'],
        transcript=transcript, alignment=alignment, subtitles=subtitles))
    speech = LocalSpeechEvidenceV1(state='speech_observed', input_audio_asset_id=mixed.asset_id,
        input_audio_sha256=mixed.sha256,
        transcript_artifact_id=artifact_ids['Text/actual-transcript.json'],
        alignment_artifact_id=artifact_ids['Text/actual-transcript.json'],
        subtitle_artifact_ids=(artifact_ids['Text/subtitles.srt'],
                               artifact_ids['Text/subtitles.vtt']),
        method_refs=(identity.method_id,),
        proof_artifact_ids=(artifact_ids['Media/mixed-audio.wav'],
                            artifact_ids['Text/actual-transcript.json']))
    method = c.MethodEvidence(method_id=identity.method_id, kind='observed',
        tool_name='faster-whisper', tool_version=identity.tool_version,
        model_repository=identity.model_id, model_revision=identity.model_id,
        resource_manifest_sha256=identity.resource_manifest_sha256,
        operation_ids=(operation['id'],),
        input_artifact_ids=(artifact_ids['Media/mixed-audio.wav'],),
        config_sha256=operation_input,
        limitations=('whisper_word_estimate_not_forced_alignment',
                     'No independent precision measurement; local self-issued evidence.',))
    return {'document': document, 'transcript': transcript, 'alignment': alignment,
            'subtitles': subtitles, 'srt': srt, 'vtt': vtt, 'mapping': mapping, 'speech': speech,
            'method': method, 'asr_operation_id': operation['id'], 'identity': identity}
