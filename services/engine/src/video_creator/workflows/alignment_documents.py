"""First-Ready and child derived speech bytes from real ASR/CTC/media facts."""
from __future__ import annotations

from video_creator.domain import contracts as c
from video_creator.domain.errors import EngineError


def original_draft(assembly, actual, *, existing_request=None):
    """Stable authored IDs, actual ASR ranges, no invented or copied source text."""
    from video_creator.application.engine import digest
    from video_creator.workflows.bundle_producer import _record
    from video_creator.workflows.bundle_v03 import runtime_source_gaps

    ids = assembly.document_artifact_ids
    mapping = assembly.audio_mappings[0]
    track = mapping.pieces[0].source_track
    script = next(ref for ref in assembly.creative_revision_refs if ref.kind == "script")
    utterances = tuple(c.TranscriptUtterance(utterance_id=f"utterance-{i}", text=segment["text"],
        intrinsic_range=c.MediaRange(start_us=segment["start_us"], end_us=segment["end_us"]),
        words=tuple(c.TranscriptWord(word_id=f"word-{i}-{j}", text=word["text"],
            intrinsic_range=c.MediaRange(start_us=word["start_us"], end_us=word["end_us"]),
            timestamp_method=actual["timestamp_method"]) for j, word in enumerate(segment["words"])))
        for i, segment in enumerate(actual["segments"]))
    transcript = _record(c.ActualTranscriptRevision(transcript_revision_id="transcript-" + digest(ids["transcript"])[:40],
        input_audio_asset_id=track.asset_id, input_audio_sha256=track.sha256, input_track=track,
        duration_us=assembly.timeline_duration_us, language=actual["language"], text=actual["text"], utterances=utterances,
        method_ref=actual["runtime"]["execution_identity"]["method_id"], approved_script_revision_ref=script,
        confidence_unavailable_reason="The admitted ASR does not provide a calibrated transcript confidence.",
        source_gaps=runtime_source_gaps(actual), content_sha256="0" * 64))
    prediction = _record(c.AlignmentRevisionV03(alignment_revision_id="alignment-" + digest(ids["transcript"] + ":prediction")[:40],
        actual_transcript_revision_id=transcript.transcript_revision_id, transcript_content_sha256=transcript.content_sha256,
        input_audio_asset_id=track.asset_id, input_audio_sha256=track.sha256, units="utterance",
        boundaries=tuple(c.AlignmentUnit(unit_id=f"alignment-{i}", transcript_unit_id=value.utterance_id,
                                        intrinsic_range=value.intrinsic_range) for i, value in enumerate(utterances)),
        timestamp_method=actual["timestamp_method"], method_ref=transcript.method_ref,
        precision=c.PrecisionAssessmentV03(status="not_measured", units="utterance",
            limitations=("Actual inference is not independent boundary evaluation.",)),
        confidence_unavailable_reason="Independent timing confidence has not been measured.", content_sha256="0" * 64))
    if existing_request is not None and (existing_request.transcript.transcript != transcript
            or existing_request.source_alignment_content_sha256 != prediction.content_sha256
            or existing_request.source_alignment_revision_id != prediction.alignment_revision_id):
        raise EngineError("alignment_original_draft_conflict", "Recovery cannot replace the original authored transcript/prediction addresses or actual ASR facts.", 409)
    subtitles = c.SubtitleTrack(subtitle_revision_id="subtitle-" + digest(ids["srt"] + ":" + ids["vtt"])[:40],
        actual_transcript_revision_id=transcript.transcript_revision_id, alignment_revision_id=prediction.alignment_revision_id,
        mapping_revision_id=mapping.mapping_revision_id, timeline_duration_us=assembly.timeline_duration_us,
        cues=tuple(c.SubtitleCue(cue_id=f"cue-{i}", text=value.text, timeline_range=value.intrinsic_range,
                               transcript_unit_refs=(value.utterance_id,)) for i, value in enumerate(utterances)),
        srt_artifact_id=ids["srt"], vtt_artifact_id=ids["vtt"], content_sha256="0" * 64)
    return c.ActualTranscriptDocumentV03(schema_version=c.V03_SCHEMA_VERSION, transcript=transcript,
                                       alignment=prediction, subtitles=subtitles)


def speech_documents(documents, document, alignment, mapping, *, assembly, media, video, video_path,
                     bundle_revision_id, project_id):
    """Rebuild acoustic ranges and real frames; original transcript stays exact."""
    from video_creator.application.bundles import validate_text
    from video_creator.workflows.bundle_producer import _json, _jsonl, _record
    from video_creator.workflows.registered_alignment import aligned_document

    updated, srt, vtt, ranges = aligned_document(document, alignment, mapping)
    shots = validate_text(documents["shots"][2], "shots", "application/x-ndjson")
    summary = validate_text(documents["summary"][2], "work_summary", "application/json")
    brief = validate_text(documents["brief"][2], "creative_revision", "application/json")
    insight = validate_text(documents["insight"][2], "creative_revision", "application/json")
    right = assembly.rights[0]
    source_refs = assembly.source_refs
    semantic = []
    for i, utterance in enumerate(document.transcript.utterances):
        span = ranges[utterance.utterance_id]
        matching = tuple(shot for shot in shots if shot.timeline_range.start_us < span.end_us
                         and shot.timeline_range.end_us > span.start_us)
        if not matching:
            raise EngineError("semantic_shot_missing", "Actual aligned speech must overlap real original shot evidence.", 422)
        frame = media.frame(video, video_path, span.start_us, "actual-decoder")
        if not media.frame_validator(frame, video_path):
            raise EngineError("semantic_frame_invalid", "Actual aligned frame must be independently decoded at its recorded PTS.", 422)
        audio = c.SemanticAudioSpan(track=document.transcript.input_track, intrinsic_range=span,
            timeline_range=span, mapping_piece_ids=tuple(value.piece_id for value in mapping.pieces))
        semantic.append(_record(c.SemanticSegmentV1(segment_id=f"segment-{i}", bundle_revision_id=bundle_revision_id,
            video_asset_id=video.asset_id, video_range=span, audio_spans=(audio,),
            shot_revision_ids=tuple(shot.shot_revision_id for shot in matching), transcript_unit_refs=(utterance.utterance_id,),
            speech_text=utterance.text, visual_description=f"Observed final frame {frame.width}x{frame.height} rgb24; no scene interpretation asserted.",
            summary=utterance.text, topic=summary.topic, main_thesis=summary.main_thesis, source_refs=source_refs,
            alignment_revision_id=alignment.alignment_revision_id,
            field_provenance={"speech_text": "observed", "summary": "derived",
                "topic": "derived" if "topic" in brief.body else "user_provided",
                "main_thesis": "derived" if "main_thesis" in insight.body else "user_provided", "visual_description": "observed"},
            frame_evidence_refs=(frame,), rights_ref=right.rights_id,
            retrieval_text=summary.topic + "\n" + summary.main_thesis + "\n" + utterance.text, content_sha256="0" * 64)))
    chunks = tuple(_record(c.RagChunk(chunk_id=f"chunk-{i}", chunk_type="speech_segment", bundle_revision_id=bundle_revision_id,
        segment_ids=(value.segment_id,), text=value.speech_text, source_refs=source_refs, video_ranges=(value.video_range,),
        audio_spans=value.audio_spans, language=document.transcript.language, rights_ref=right.rights_id,
        access_scope_ref=project_id,
        valid_until_us=right.expires_at_us, field_provenance={"text": "observed"},
        method_refs=(document.transcript.method_ref, alignment.method_ref, "actual-decoder"), content_sha256="0" * 64))
        for i, value in enumerate(semantic))
    # The actual project is a required trusted caller fact, not a fallback.
    documents["transcript"] = (*documents["transcript"][:2], _json(updated))
    documents["srt"] = (*documents["srt"][:2], srt)
    documents["vtt"] = (*documents["vtt"][:2], vtt)
    documents["segments"] = (*documents["segments"][:2], _jsonl(semantic))
    documents["rag"] = (*documents["rag"][:2], _jsonl(chunks))
    return updated
