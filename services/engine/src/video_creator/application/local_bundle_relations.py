"""Local 0.4 actual material relations. Uses the original service and authorities."""
from video_creator.domain import contracts as c
from video_creator.domain import local_bundle as local
from video_creator.domain.errors import EngineError


def _require(condition, code, message):
    if not condition:
        raise EngineError(code, message, 422)


def validate_local_relations(service, lease, preparation_id, manifest, documents, request, context):
    from video_creator.application.bundles import (
        check_record,
        local_fact_id,
        matches_actual_asr,
        serialize_subtitles,
    )
    indexed = {value.artifact_id: value for value in manifest.artifacts}
    paths = {value.relative_path: value for value in manifest.artifacts}
    fixed_paths = set(local.LOCAL_REQUIRED_FILES) | {'Semantics/shots.jsonl', 'Semantics/visual-mapping.json',
        'Media/video.mp4', 'Media/narration.wav', 'Media/mixed-audio.wav', 'Media/cover.jpg',
        'Text/actual-transcript.json', 'Text/subtitles.srt', 'Text/subtitles.vtt',
        'Creative/insight.json', 'Creative/brief.json', 'Creative/storyboard.json'}
    allowed_extra = {'license', 'precision_evaluation', 'precision_reference', 'frame_evidence', 'asr_input',
        'audit_summary', 'method_benchmark', 'method_benchmark_reference', 'method_qualification',
        'evidence_policy', 'work_alignment_validation', 'production_authorization'}
    _require(all(value.relative_path in fixed_paths or set(value.roles) <= allowed_extra for value in manifest.artifacts),
             'bundle_attachment_denied', 'Local package cannot add unapproved private attachments.')
    selection = documents.get('Checks/local-master-selection.json')
    speech = documents.get('Checks/local-speech-evidence.json')
    quality = documents.get('Checks/quality-report.json')
    _require(type(selection) is local.LocalMasterSelectionV1 and selection == context.selection,
             'local_selection_conflict', 'Selection differs from actual original approved sources.')
    _require(type(speech) is local.LocalSpeechEvidenceV1 and type(quality) is local.LocalBundleQualityEvidenceV1,
             'local_bundle_document_missing', 'Actual speech and quality materials are required.')
    _require(paths['Checks/local-master-selection.json'].artifact_id == manifest.selection_artifact_id
             and paths['Checks/local-speech-evidence.json'].artifact_id == manifest.speech_evidence_artifact_id
             and quality.speech_evidence_artifact_id == manifest.speech_evidence_artifact_id,
             'local_bundle_document_conflict', 'Indexed document identities differ.')
    _require(manifest.requested_outputs == selection.outputs == request.outputs
             and tuple(value.role for value in manifest.outputs) == request.outputs,
             'bundle_output_binding_invalid', 'Original requested outputs and order must be retained.')
    _require(manifest.timeline_duration_us == context.plan.timeline.duration_us,
             'local_timeline_conflict', 'Actual approved timeline duration differs.')
    _require(documents.get('Creative/production-plan.json') == context.plan_revision[1],
             'creative_material_conflict', 'Actual plan attachment differs from the immutable revision.')
    script = documents.get('Text/approved-script.json')
    _require(type(script) is c.ApprovedScriptDocument and script.script_revision_ref == context.sources.original_script[0]
             and script.text == context.sources.original_script[1].body.get('text'),
             'script_material_conflict', 'Actual script attachment differs from original saved text.')
    _require(quality.quality_revision_ref == context.quality_revision[0] == manifest.quality_ref,
             'bundle_quality_conflict', 'Quality binds the exact approved same-Run version.')
    for path, kind in (('Creative/insight.json', 'insight'), ('Creative/brief.json', 'brief'),
                       ('Creative/storyboard.json', 'storyboard')):
        value = documents.get(path)
        if value is not None:
            from video_creator.application.engine import canonical, digest
            _require(type(value) is c.CreativeRevision and value.kind == kind
                     and any(ref.revision_id == value.revision_id and ref.kind == kind
                             and ref.content_sha256 == digest(canonical(value)) for ref in manifest.creative_revision_refs),
                     'creative_material_conflict', 'Optional creative attachments require their actual immutable revision.')
    role_paths = {'video':'Media/video.mp4', 'narration_audio':'Media/narration.wav',
                  'mixed_audio':'Media/mixed-audio.wav', 'cover':'Media/cover.jpg'}
    master_ids = {}
    for role, path in role_paths.items():
        artifact = paths.get(path)
        if role in selection.master_roles:
            _require(artifact is not None and artifact.asset_id is not None and artifact.roles == (role,),
                     'local_master_missing', 'Each selected master is an actual role-bound Asset.')
            master_ids[role] = artifact.asset_id
            if role != 'cover':
                _require(artifact.spec.duration_us == manifest.timeline_duration_us,
                         'local_timeline_conflict', 'Decoded selected master duration must match the work.')
        else:
            _require(artifact is None, 'local_master_not_applicable', 'Absent roles cannot be filled with fake masters.')
    actual_roles = service._local_source().runtime.master_assets(lease, selection=selection)
    _require(master_ids == actual_roles, 'local_master_source_conflict', 'Masters differ from actual committed successful Step outputs.')
    output_paths = {'video':('Media/video.mp4',), 'narration_audio':('Media/narration.wav',),
        'mixed_audio':('Media/mixed-audio.wav',), 'approved_script':('Text/approved-script.json',),
        'actual_transcript':('Text/actual-transcript.json',), 'subtitles':('Text/subtitles.srt','Text/subtitles.vtt'),
        'semantic_manifest':('Semantics/semantic-segments.jsonl',), 'rag_chunks':('Semantics/rag-chunks.jsonl',)}
    for output in manifest.outputs:
        _require(tuple(indexed[ref].relative_path for ref in output.artifact_ids) == output_paths[output.role],
                 'bundle_output_binding_invalid', 'Outputs bind the actual applicable indexed paths.')
    methods = {method.method_id:method for method in manifest.methods}
    _require(set(speech.method_refs) <= set(methods) and set(speech.proof_artifact_ids) <= set(indexed),
             'local_speech_source_missing', 'Presence and absence proofs need actual indexed methods and artifacts.')
    actual = documents.get('Text/actual-transcript.json')
    if speech.state == 'no_audio_observed':
        _require('mixed_audio' not in master_ids and 'narration_audio' not in master_ids
                 and not context.plan.timeline.audio_tracks and actual is None
                 and selection.content_kind == 'video', 'local_audio_absence_invalid', 'No-audio requires an actual silent visual work.')
        video = paths['Media/video.mp4']
        with service.engine.db.connect_readonly() as connection:
            run=service.engine._lease(connection,lease)
            owner=service.engine._production(connection,run['production_id'])['owner']
        probe = service._media_probe(owner, video)
        _require(not probe.has_audio and video.artifact_id in speech.proof_artifact_ids,
                 'local_audio_absence_invalid', 'Actual final video decode must prove the absence of audio.')
        units, alignment_id = {}, None
    else:
        _require(type(actual) is local.LocalActualTranscriptDocumentV1 and
                 actual.speech_evidence_artifact_id == manifest.speech_evidence_artifact_id,
                 'actual_transcript_missing', 'Audio states require actual local transcript material.')
        transcript = actual.transcript
        _require((speech.input_audio_asset_id, speech.input_audio_sha256, speech.transcript_artifact_id) == (
            transcript.input_audio_asset_id, transcript.input_audio_sha256, paths['Text/actual-transcript.json'].artifact_id),
            'transcript_audio_binding_invalid', 'Speech evidence and transcript must retain original audio identity.')
        mixed = paths['Media/mixed-audio.wav']
        _require(transcript.input_audio_asset_id == mixed.asset_id and transcript.input_audio_sha256 == mixed.sha256
                 and transcript.approved_script_revision_ref == script.script_revision_ref,
                 'transcript_audio_binding_invalid', 'Actual final mixed audio and original script comparison are required.')
        method = methods.get(transcript.method_ref)
        _require(method is not None and method.kind == 'observed' and method.operation_ids
                 and method.resource_manifest_sha256 in service.validators.resource_manifest_hashes,
                 'actual_asr_evidence_missing', 'Actual admitted ASR method and resource are required.')
        observations=[]
        with service.engine.db.connect_readonly() as connection:
            service.engine._lease(connection, lease)
            for op in method.operation_ids:
                row=connection.execute("SELECT observation_json FROM operations WHERE id=? AND run_id=? AND status='succeeded' AND settled=1", (op,lease.run_id)).fetchone()
                _require(row is not None, 'actual_asr_evidence_missing', 'ASR must be actually successful and settled on this Run.')
                observations.append(c.OperationObservation.model_validate_json(row[0]).result_json)
        matching=[value for value in observations if matches_actual_asr(value,transcript)]
        _require(bool(matching), 'actual_asr_evidence_missing', 'Transcript must match original actual ASR observation.')
        if speech.state == 'no_speech_observed':
            _require(not transcript.text and not transcript.utterances and actual.alignment is None and actual.subtitles is None
                     and not transcript.source_gaps, 'local_speech_absence_invalid', 'Empty text alone is not observed no-speech.')
            gaps=sorted(transcript.gaps,key=lambda value:value.intrinsic_range.start_us)
            end=0
            for gap in gaps:
                _require(gap.classification in {'no_speech','music'} and gap.intrinsic_range.start_us == end,
                         'local_speech_absence_invalid', 'Observed absence must cover all actual audio without unknown gaps.')
                end=gap.intrinsic_range.end_us
            _require(end == transcript.duration_us and any(value.get('gaps') == [gap.model_dump(mode='json') for gap in transcript.gaps] for value in matching),
                     'local_speech_absence_invalid', 'Actual settled observation must retain complete original observed gaps.')
            if 'subtitles' in request.outputs:
                _require(tuple(speech.subtitle_artifact_ids) == tuple(paths[path].artifact_id for path in output_paths['subtitles'])
                         and documents.get('Text/subtitles.srt') == '\n'
                         and documents.get('Text/subtitles.vtt') == 'WEBVTT\n\n',
                         'local_empty_subtitles_invalid', 'Both actual MIME/hash-bound zero-cue SRT/VTT documents are required.')
            units,alignment_id={},None
        else:
            _require(transcript.utterances and transcript.text and actual.alignment is not None and actual.subtitles is not None,
                     'actual_speech_unrecognized', 'Observed speech requires full actual alignment and subtitle evidence.')
            alignment=actual.alignment
            _require((alignment.actual_transcript_revision_id,alignment.transcript_content_sha256,alignment.input_audio_asset_id,alignment.input_audio_sha256)==(
                transcript.transcript_revision_id,transcript.content_sha256,transcript.input_audio_asset_id,transcript.input_audio_sha256),
                'alignment_binding_invalid','Alignment must bind original complete ASR/audio.')
            units={value.utterance_id:value for value in transcript.utterances}
            words={word.word_id:word for value in transcript.utterances for word in value.words}
            expected=units if alignment.units=='utterance' else words
            _require(len({value.transcript_unit_id for value in alignment.boundaries})==len(alignment.boundaries)
                     and {value.transcript_unit_id for value in alignment.boundaries}==set(expected),
                     'alignment_unit_invalid','All original actual units must be aligned exactly once.')
            for value in alignment.boundaries:
                _require(value.intrinsic_range.end_us<=transcript.duration_us,'alignment_unit_invalid','Alignment exceeds actual audio.')
            if isinstance(alignment,c.AlignmentRevisionV03):
                service._verify_local_v03_reports(lease, preparation_id, manifest, documents, request, actual, quality)
            else:
                service._verify_strict_precision(lease, manifest, documents, actual, quality, request.delivery_requirements or c.DeliveryRequirements())
            srt,vtt,quantization=serialize_subtitles(actual.subtitles)
            _require(documents.get('Text/subtitles.srt')==srt.decode() and documents.get('Text/subtitles.vtt')==vtt.decode()
                     and actual.subtitles.quantization_errors==tuple(quantization),'subtitle_quantization_invalid','Actual subtitle bytes and quantization differ.')
            _require(actual.subtitles.actual_transcript_revision_id==transcript.transcript_revision_id
                     and actual.subtitles.alignment_revision_id==alignment.alignment_revision_id
                     and actual.subtitles.timeline_duration_us==manifest.timeline_duration_us,
                     'subtitle_binding_invalid','Actual subtitles bind this transcript/alignment/timeline.')
            units={**units,**words}
            alignment_id=alignment.alignment_revision_id
    pieces={}
    video=paths.get('Media/video.mp4')
    for mapping in manifest.audio_mappings:
        check_record(mapping)
        if video is None:
            raise EngineError('local_audio_work_mapping_required','Audio-only requires the approved actual work-target mapping contract.',503)
        _require(mapping.target_video_asset_id==video.asset_id and mapping.timeline_duration_us==manifest.timeline_duration_us,
                 'audio_mapping_invalid','Original mapping must target the actual final work.')
        for piece in mapping.pieces:
            record=service.asset(lease,piece.source_track.asset_id)
            _require(record.sha256==piece.source_track.sha256,'audio_mapping_invalid','Original audio mapping source bytes differ.')
            if service.audio_clock_authority is None:
                raise EngineError('audio_clock_unconfigured','Actual sample/PTS verifier is required.',503)
            _require(service.audio_clock_authority(piece.source_track,service.content_path(lease,record.asset_id)) is True,
                     'audio_clock_invalid','Actual original audio clock was rejected.')
            service._check_mapping_piece(piece)
            _require(piece.piece_id not in pieces,'audio_mapping_invalid','Mapping piece IDs must be globally unique.')
            pieces[piece.piece_id]=piece
    if speech.state != 'no_audio_observed':
        _require(bool(pieces),'audio_mapping_invalid','Actual sound requires complete sample/clock mappings.')
    sources = documents.get('Semantics/source-bindings.json')
    summary = documents.get('Semantics/work-summary.json')
    _require(type(sources) is c.SourceBindingsDocument and sources.bundle_revision_id == manifest.bundle_revision_id
             and sources.source_refs == manifest.source_refs and type(summary) is c.WorkSummary
             and summary.bundle_revision_id == manifest.bundle_revision_id
             and all(ref in manifest.source_refs for ref in summary.source_refs),
             'semantic_binding_invalid', 'Actual summary and source documents must retain the original bundle.')
    for binding in request.source_bindings:
        matches = [ref for ref in manifest.source_refs if
            (ref.system, ref.namespace, ref.article_id, ref.article_revision, ref.topic_id, ref.topic_revision) ==
            (binding.system, binding.namespace, binding.article_id, binding.article_revision, binding.topic_id, binding.topic_revision)]
        _require(len(matches) == 1 and set(binding.paragraph_ids) <= set(matches[0].paragraph_ids)
                 and set(binding.confirmed_facts) <= {fact.text for fact in matches[0].fact_refs},
                 'source_binding_lost', 'Original supplied document identities and facts must remain exact.')
        for fact in matches[0].fact_refs:
            if fact.text in binding.confirmed_facts:
                _require(fact.foreign_fact_id is None and fact.local_fact_id == local_fact_id(binding, fact.text)
                         and fact.confirmation_kind == 'caller_asserted', 'source_fact_identity_invalid',
                         'Caller text cannot invent a foreign fact authority.')
    _require(all(set(ref.input_asset_ids) <= set(request.inputs.asset_ids) for ref in manifest.source_refs),
             'source_asset_denied', 'Source references must keep the original fixed input assets.')
    shot_ids = set()
    if selection.content_kind == 'video':
        visual = documents.get('Semantics/visual-mapping.json')
        shots = documents.get('Semantics/shots.jsonl')
        _require(type(visual) is local.LocalVisualMappingDocumentV1 and isinstance(shots, list)
                 and all(type(value) is local.ShotEvidenceLocalV1 for value in shots)
                 and paths['Semantics/visual-mapping.json'].artifact_id == manifest.visual_mapping_artifact_id,
                 'local_visual_mapping_invalid', 'Video requires actual typed visual mapping and shot records.')
        _require((visual.fps_num, visual.fps_den, visual.timeline_duration_us) ==
                 (context.plan.timeline.fps_num, context.plan.timeline.fps_den, context.plan.timeline.duration_us)
                 and len(visual.rows) == len(context.plan.timeline.shots) == len(shots),
                 'local_visual_mapping_invalid', 'Actual approved frame grid and shot collection must remain exact.')
        bindings = {value.binding_id: value for value in context.plan.input_bindings}
        for row, planned, shot in zip(visual.rows, context.plan.timeline.shots, shots, strict=True):
            binding = bindings[planned.input_binding_id]
            still = binding.media_type in {'image/png', 'image/jpeg'}
            _require((row.shot_id, row.input_binding_id, row.source_asset_id, row.source_sha256, row.timeline_range) ==
                     (planned.shot_id, planned.input_binding_id, binding.asset_id, binding.sha256, planned.timeline_range)
                     and row.source_media_range == (None if still else planned.source_range)
                     and row.display_hold_us == (planned.timeline_range.end_us - planned.timeline_range.start_us if still else None),
                     'local_visual_mapping_invalid', 'Mapping must retain actual input bytes and approved display or source range.')
            if still:
                _require(binding.probe.decoded and binding.probe.duration_us is None
                         and binding.probe.width is not None and binding.probe.height is not None
                         and planned.source_range.start_us == 0
                         and planned.source_range.end_us == row.display_hold_us,
                         'local_still_source_invalid', 'Static images have an actual display hold, not a fabricated intrinsic duration.')
            _require(shot.shot_revision_id == local.local_shot_revision_id(context.plan_revision[0].content_sha256, planned.shot_id)
                     and shot.video_asset_id == video.asset_id and shot.timeline_range == planned.timeline_range
                     and all(ref in manifest.source_refs for ref in shot.source_refs),
                     'local_shot_source_invalid', 'Shot identity and ranges must come from the actual immutable plan.')
            shot_ids.add(shot.shot_revision_id)
            for frame in shot.frame_evidence_refs:
                if service.validators.frame_validator is None:
                    raise EngineError('frame_evidence_unconfigured', 'Actual final-frame verification is required.', 503)
                _require(frame.video_asset_id == video.asset_id and frame.video_sha256 == video.sha256
                         and planned.timeline_range.start_us <= frame.at_us < planned.timeline_range.end_us
                         and service.validators.frame_validator(frame, service.content_path(lease, video.asset_id)),
                         'frame_evidence_invalid', 'Shot frames must come from the actual final video interval.')
    else:
        _require(manifest.visual_mapping_artifact_id is None and 'Semantics/visual-mapping.json' not in paths
                 and 'Semantics/shots.jsonl' not in paths, 'local_visual_not_applicable', 'Audio-only cannot fabricate visual records.')
    segments=documents.get('Semantics/semantic-segments.jsonl')
    chunks=documents.get('Semantics/rag-chunks.jsonl')
    _require(isinstance(segments,list) and all(type(value) is local.SemanticSegmentLocalV2 for value in segments)
             and isinstance(chunks,list) and all(type(value) is local.RagChunkLocalV2 for value in chunks),
             'local_semantics_missing','Actual versioned local semantics and RAG records are required.')
    known={value.segment_id:value for value in segments}
    _require(len(known)==len(segments),'semantic_binding_invalid','Segment IDs must be unique.')
    rights={right.rights_id:right for right in manifest.rights}
    for segment in segments:
        _require(segment.bundle_revision_id==manifest.bundle_revision_id and segment.timeline_range.end_us<=manifest.timeline_duration_us
                 and segment.alignment_revision_id==alignment_id and segment.rights_ref in rights and set(segment.shot_revision_ids)<=shot_ids,
                 'semantic_binding_invalid','Semantic identity/range/alignment/rights differ from actual work.')
        _require(segment.speech_text==''.join(units[key].text for key in segment.transcript_unit_refs if key in units)
                 and set(segment.transcript_unit_refs)<=set(units) and all(ref in manifest.source_refs for ref in segment.source_refs),
                 'semantic_speech_invalid','Speech and source references must retain actual evidence.')
        _require((video is None and segment.video_asset_id is None) or (video is not None and segment.video_asset_id==video.asset_id
                 and segment.video_range==segment.timeline_range),'semantic_binding_invalid','No fake video identity/range is permitted.')
        for span in segment.audio_spans:
            service._check_span(span,pieces)
        for frame in segment.frame_evidence_refs:
            if service.validators.frame_validator is None:
                raise EngineError('frame_evidence_unconfigured','Actual final frame validation is required.',503)
            _require(video is not None and frame.video_asset_id==video.asset_id and frame.video_sha256==video.sha256
                     and frame.at_us<manifest.timeline_duration_us and service.validators.frame_validator(frame,service.content_path(lease,video.asset_id)),
                     'frame_evidence_invalid','Visual evidence must retain actual final decoded frames.')
        _require(not segment.visual_description or bool(segment.frame_evidence_refs),
                 'frame_evidence_invalid','Visual descriptions require actual observed frame evidence.')
    _require(len({chunk.chunk_id for chunk in chunks})==len(chunks),'rag_binding_invalid','RAG chunk IDs must be unique.')
    for chunk in chunks:
        _require(chunk.bundle_revision_id==manifest.bundle_revision_id and set(chunk.segment_ids)<=set(known)
                 and chunk.access_scope_ref==manifest.project_id and chunk.rights_ref in rights
                 and set(chunk.method_refs)<=set(methods) and all(ref in manifest.source_refs for ref in chunk.source_refs),
                 'rag_scope_invalid','RAG scope/version/source/methods must retain this actual bundle.')
        linked=[known[key] for key in chunk.segment_ids]
        if chunk.chunk_type!='work_summary':
            _require(linked and chunk.video_ranges==tuple(value.video_range for value in linked if value.video_range is not None)
                     and chunk.audio_spans==tuple(span for value in linked for span in value.audio_spans),
                     'rag_binding_invalid','RAG media spans differ from actual semantic records.')
        if chunk.chunk_type=='speech_segment':
            _require(speech.state=='speech_observed' and chunk.text==''.join(value.speech_text for value in linked),
                     'rag_speech_invalid','Only actual observed speech may enter speech chunks.')
        right=rights[chunk.rights_ref]
        _require(right.expires_at_us is None or chunk.valid_until_us is not None and chunk.valid_until_us<=right.expires_at_us,
                 'rag_rights_invalid','RAG validity cannot exceed original rights.')
    applicability={value.check_id:value for value in quality.applicability}
    required={'media_integrity','audio_timeline','actual_transcript','alignment','subtitles','semantic_sources','rights'}
    verified={value.check_id for value in quality.checks if value.status=='verified'}
    _require(len({value.check_id for value in quality.checks}) == len(quality.checks)
             and all(value.method_ref in methods and set(value.evidence_artifact_ids) <= set(indexed) for value in quality.checks),
             'bundle_quality_incomplete', 'Each actual QC check needs distinct identity and indexed method/evidence closure.')
    _require(required<=set(applicability),'bundle_quality_incomplete','Every original required check has explicit actual applicability.')
    for key in required:
        value=applicability[key]
        _require(set(value.proof_artifact_ids)<=set(indexed),'bundle_quality_incomplete','Applicability proof must be an actual indexed artifact.')
        should_apply=(key not in {'actual_transcript','alignment','subtitles','audio_timeline'}
                      or key == 'audio_timeline' and speech.state != 'no_audio_observed'
                      or key == 'actual_transcript' and actual is not None
                      or key == 'alignment' and speech.state == 'speech_observed'
                      or key == 'subtitles' and ('subtitles' in request.outputs or speech.state == 'speech_observed'))
        if should_apply:
            _require(value.status=='applicable' and key in verified,'bundle_quality_incomplete','All applicable original checks require actual verified evidence.')
        else:
            _require(value.status=='not_applicable','bundle_quality_incomplete','Only actually observed speech absence can mark speech checks inapplicable.')
    _require(all(check.status=='verified' for check in quality.checks if applicability.get(check.check_id) is None
                 or applicability[check.check_id].status=='applicable'),
             'bundle_quality_incomplete','Failed or missing applicable QC cannot be published.')
    return service._validate_shared_rights_methods(lease,manifest,documents)
