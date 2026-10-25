"""Sole local 0.4 final Bundle producer: real masters, no ASR resources.

This consumer is the Media side of ADR0075 steps 2/6: it consumes the held
Backend context (`LocalMaterialFinalContext`), the caller's applicable
`LocalMasterSelectionV1` and the already registered real masters, then builds
the typed local documents, stages them into the original preparation, verifies
and publishes the sole `BundleManifestLocalV1`. It never loads ASR resources,
never creates a second encoder and never invents a transcript.

The only real speech-free branch implemented here is `no_audio_observed`: the
approved plan has no audio tracks, no narration/mix master exists and the
actual final video decodes without an audio stream. There is deliberately no
zero-cue branch (统筹裁定 2026-10-25): `subtitles`/`actual_transcript` are
refused by name (`local_output_not_applicable`/422 for a silent work,
`local_speech_observation_required` for a speech-bearing work) instead of
writing empty documents or fabricating speech evidence.
"""
from __future__ import annotations

import hashlib

from pydantic import ValidationError

from video_creator.application.engine import canonical, digest
from video_creator.domain import contracts as c
from video_creator.domain.bundle import BundlePreparationIntent, MaterialSlot
from video_creator.domain.current_final_evidence import AssemblyContextRef
from video_creator.domain.errors import EngineError
from video_creator.domain.local_bundle import (
    LOCAL_REQUIRED_FILES,
    BundleManifestLocalV1,
    LocalBundleQualityEvidenceV1,
    LocalCheckApplicabilityV1,
    LocalFinalAssemblyContextV1,
    LocalMasterSelectionV1,
    LocalSpeechEvidenceV1,
)
from video_creator.domain.registered_production import PROFILE
from video_creator.workflows.attempt_control import attempt_control, current_attempt
from video_creator.workflows.local_bundle_inputs import (
    observe_local_frames,
    read_local_final_inputs,
    require_held_final_facts,
    visual_mapping_inputs,
)
from video_creator.workflows.local_material_composition import (
    observe_local_audio_coordinates,
)
from video_creator.workflows.local_semantics import build_local_semantics

EDIT_METHOD = 'local-owned-assets-v1'
DECODER_METHOD = 'actual-decoder'
PLAN_METHOD = 'local-approved-plan-v1'
ROLE_PATHS = {'video': 'Media/video.mp4', 'narration_audio': 'Media/narration.wav',
              'mixed_audio': 'Media/mixed-audio.wav', 'cover': 'Media/cover.jpg'}
AUDIO_ROLES = ('narration_audio', 'mixed_audio')
OUTPUT_PATHS = {'video': ('Media/video.mp4',), 'narration_audio': ('Media/narration.wav',),
                'mixed_audio': ('Media/mixed-audio.wav',),
                'approved_script': ('Text/approved-script.json',),
                'actual_transcript': ('Text/actual-transcript.json',),
                'subtitles': ('Text/subtitles.srt', 'Text/subtitles.vtt'),
                'semantic_manifest': ('Semantics/semantic-segments.jsonl',),
                'rag_chunks': ('Semantics/rag-chunks.jsonl',)}
SPEECH_CHECKS = frozenset({'audio_timeline', 'actual_transcript', 'alignment', 'subtitles'})
DOCUMENT_KINDS = {
    'Checks/local-master-selection.json': ('local_master_selection', 'application/json'),
    'Checks/local-speech-evidence.json': ('local_speech_evidence', 'application/json'),
    'Checks/quality-report.json': ('quality_local', 'application/json'),
    'Creative/production-plan.json': ('creative_revision', 'application/json'),
    'Semantics/rag-chunks.jsonl': ('rag_chunks_local', 'application/x-ndjson'),
    'Semantics/semantic-segments.jsonl': ('semantic_segments_local', 'application/x-ndjson'),
    'Semantics/source-bindings.json': ('source_bindings', 'application/json'),
    'Semantics/work-summary.json': ('work_summary', 'application/json'),
    'Text/approved-script.json': ('approved_script', 'application/json'),
}
VISUAL_KINDS = {'Semantics/shots.jsonl': ('shots_local', 'application/x-ndjson'),
                'Semantics/visual-mapping.json': ('visual_mapping_local', 'application/json')}
DOCUMENT_PATHS = frozenset(DOCUMENT_KINDS) | frozenset(VISUAL_KINDS)
SPOKEN_OUTPUTS = frozenset({'actual_transcript', 'subtitles'})
# The committed local final-assembly context indexes these same Ready documents
# by the role names its Backend validator admits. A path outside this table is
# never claimed as an assembly document.
ASSEMBLY_DOCUMENT_ROLES = {
    'Creative/production-plan.json': 'plan',
    'Text/approved-script.json': 'script',
    'Checks/quality-report.json': 'quality',
    'Checks/local-master-selection.json': 'selection',
    'Checks/local-speech-evidence.json': 'speech',
    'Semantics/work-summary.json': 'summary',
    'Semantics/source-bindings.json': 'sources',
    'Semantics/semantic-segments.jsonl': 'segments',
    'Semantics/rag-chunks.jsonl': 'rag',
    'Semantics/shots.jsonl': 'shots',
    'Semantics/visual-mapping.json': 'visual',
}


def _json(model):
    return (canonical(model) + '\n').encode('utf-8')


def _jsonl(models):
    return b''.join(_json(model) for model in models)


def _record(model):
    from video_creator.application.bundles import record_sha
    return model.model_copy(update={'content_sha256': record_sha(model)})


def _identity(prefix, *parts):
    return prefix + '-' + digest(canonical(list(parts)))[:40]


def _speech_error(request):
    if 'actual_transcript' in request.outputs or 'subtitles' in request.outputs:
        return EngineError('local_speech_observation_required',
            'Requested transcript/subtitles need an admitted final-mix speech observation; this consumer does not load ASR resources.', 503)
    return EngineError('local_speech_evidence_unavailable',
        'Speech-bearing local work needs the original settled final-mix ASR and governed alignment; this consumer does not produce them.', 503)


def _absence_evidence(composition, *, artifact_ids):
    """Actual no-audio proof from the registered final master and the plan."""
    plan, assets = composition['plan'], composition['media_assets']
    video = assets.get('video')
    if (video is None or plan.timeline.audio_tracks or any(role in assets for role in AUDIO_ROLES)):
        raise EngineError('local_audio_absence_invalid',
                          'No-audio evidence requires an actual silent visual work without audio masters.', 409)
    if (not video.probe.has_video or video.probe.has_audio
            or video.probe.duration_us != plan.timeline.duration_us):
        raise EngineError('local_master_timeline_invalid',
                          'The actual final video must decode as a silent master of the approved duration.', 422)
    return LocalSpeechEvidenceV1(state='no_audio_observed', input_audio_asset_id=None,
        input_audio_sha256=None, transcript_artifact_id=None, alignment_artifact_id=None,
        subtitle_artifact_ids=(), method_refs=(DECODER_METHOD, EDIT_METHOD),
        proof_artifact_ids=(artifact_ids[ROLE_PATHS['video']],))


def _lineage(artifact_ids, path):
    """Named error instead of a bare KeyError when a produced document's real source is absent."""
    try:
        return artifact_ids[path]
    except KeyError:
        raise EngineError('local_document_lineage_missing',
                          f'Produced document lineage needs the actual {path} artifact.', 409) from None


def _quality(composition, *, speech, artifact_ids, audio):
    absent = speech.state != 'speech_observed'
    evidence = {
        'media_integrity': (_lineage(artifact_ids, ROLE_PATHS['video']),),
        'audio_timeline': (_lineage(artifact_ids, ROLE_PATHS['video']),),
        'actual_transcript': (_lineage(artifact_ids, 'Checks/local-speech-evidence.json'),),
        'alignment': (_lineage(artifact_ids, 'Checks/local-speech-evidence.json'),),
        'subtitles': (_lineage(artifact_ids, 'Checks/local-speech-evidence.json'),),
        'semantic_sources': (_lineage(artifact_ids, 'Semantics/source-bindings.json'),
                             _lineage(artifact_ids, 'Semantics/work-summary.json')),
        'rights': (_lineage(artifact_ids, 'Creative/production-plan.json'),),
    }
    methods = {'media_integrity': DECODER_METHOD, 'audio_timeline': DECODER_METHOD,
               'actual_transcript': DECODER_METHOD, 'alignment': DECODER_METHOD,
               'subtitles': DECODER_METHOD, 'semantic_sources': PLAN_METHOD,
               'rights': PLAN_METHOD}
    skipped = SPEECH_CHECKS if absent else frozenset()
    if not audio:
        skipped = frozenset(set(skipped) | {'audio_timeline'})
    checks = tuple(c.QualityCheck(check_id=name,
        status='not_measured' if name in skipped else 'verified',
        method_ref=methods[name], evidence_artifact_ids=evidence[name],
        findings=('Actual decode and plan/source identity only; not perceptual quality or user acceptance.',))
        for name in evidence)
    applicability = tuple(LocalCheckApplicabilityV1(check_id=name,
        status='not_applicable' if name in skipped else 'applicable',
        reason_code='no_audio_observed' if name in SPEECH_CHECKS and not audio
        else 'no_observed_speech' if name == 'subtitles' else
        'actual_material_and_decoder_verified',
        proof_artifact_ids=evidence[name]) for name in evidence)
    quality = LocalBundleQualityEvidenceV1(quality_revision_ref=composition['creative_revision_refs'][2],
        checks=checks, speech_evidence_artifact_id=artifact_ids['Checks/local-speech-evidence.json'],
        alignment_report_artifact_ids=(), applicability=applicability, content_sha256='0' * 64)
    return _record(quality)


def _tool_identities(composition, media):
    """Actual measured tool identities; no profile constant stands in for them.

    The edit version is the identity the real registered master probes measured
    with the installed ffmpeg/ffprobe. The decoder version is what the actual
    isolated observer process reported about itself. Neither is invented here.
    """
    versions = {asset.probe.tool_version for asset in composition['media_assets'].values()}
    if len(versions) != 1:
        raise EngineError('local_method_identity_unavailable',
                          'Actual registered masters must report one measured media-tool version.', 503)
    edit_version = versions.pop()
    if type(edit_version) is not str or not edit_version.strip():
        raise EngineError('local_method_identity_unavailable',
                          'The actual master probe reported no measured media-tool version.', 503)
    decoder_version = media.observed_tool_version
    if type(decoder_version) is not str or not decoder_version:
        raise EngineError('local_method_identity_unavailable',
                          'The actual isolated decoder observation must report its measured version before methods are built.', 503)
    return edit_version, decoder_version


def _methods(composition, artifact_ids, *, video, media, registration_sha256):
    edit_version, decoder_version = _tool_identities(composition, media)
    plan_ref = composition['creative_revision_refs'][1]
    evidence = tuple(_lineage(artifact_ids, path) for path in VISUAL_KINDS if path in artifact_ids) if video else ()
    return (c.MethodEvidence(method_id=EDIT_METHOD, kind='observed', tool_name='FFmpeg',
                tool_version=edit_version[:200], config_sha256=registration_sha256,
                limitations=('Actual variable owned-material edit consumed from the upstream registered master Steps; tool_version is the identity the actual master probes measured.',
                             'config_sha256 is the installed registration bytes sha that pins the ffmpeg/ffprobe resource hashes; this consumer does not re-hash the binaries itself.')),
            c.MethodEvidence(method_id=DECODER_METHOD, kind='observed', tool_name='PyAV+FFmpeg',
                tool_version=decoder_version[:200], config_sha256=media.observer_sha256,
                evidence_artifact_ids=evidence,
                limitations=('tool_version is the measured library identity the actual isolated observer process reported.',
                             'config_sha256 is the sha256 of the actual fixed observer source, not a user configuration.',
                             'The observer interpreter is the host Engine interpreter validated by the factory; a registered interpreter hash remains a Backend installation item.')),
            c.MethodEvidence(method_id=PLAN_METHOD, kind='user_provided', tool_name='LocalMaterialProducer',
                tool_version=PROFILE, config_sha256=plan_ref.content_sha256,
                limitations=('Original approved plan/script and source bindings; not recognized speech.',
                             'tool_version is the registered local workflow profile, not a measured tool binary.')))


def _documents(composition, bundle, lease, *, selection, speech, shots, visuals, right, artifact_ids):
    script_ref, _plan_ref, _quality_ref = composition['creative_revision_refs']
    script = composition['script_revision']
    text = script.body.get('text') if isinstance(script.body, dict) else None
    if type(text) is not str or not text:
        raise EngineError('local_script_material_missing', 'The original script revision has no actual text.', 422)
    approved = _record(c.ApprovedScriptDocument(script_revision_ref=script_ref, text=text, content_sha256='0' * 64))
    audio = bool(composition['plan'].timeline.audio_tracks)
    quality = _quality(composition, speech=speech, artifact_ids=artifact_ids, audio=audio)
    semantics = build_local_semantics(composition,
        bundle_revision_id=_bundle_revision_id(composition, selection),
        access_scope_ref=bundle.context(lease).project_id, right=right, speech=speech, shots=shots)
    documents = {
        'Checks/local-master-selection.json': ('local_master_selection', 'application/json', _json(selection)),
        'Checks/local-speech-evidence.json': ('local_speech_evidence', 'application/json', _json(speech)),
        'Checks/quality-report.json': ('quality_local', 'application/json', _json(quality)),
        'Creative/production-plan.json': ('creative_revision', 'application/json', _json(composition['plan_revision'])),
        'Semantics/rag-chunks.jsonl': ('rag_chunks_local', 'application/x-ndjson', _jsonl(semantics['rag'])),
        'Semantics/semantic-segments.jsonl': ('semantic_segments_local', 'application/x-ndjson', _jsonl(semantics['segments'])),
        'Semantics/source-bindings.json': ('source_bindings', 'application/json', _json(semantics['sources'])),
        'Semantics/work-summary.json': ('work_summary', 'application/json', _json(semantics['summary'])),
        'Text/approved-script.json': ('approved_script', 'application/json', _json(approved)),
    }
    if visuals is not None:
        documents['Semantics/visual-mapping.json'] = ('visual_mapping_local', 'application/json', _json(visuals))
    if selection.content_kind == 'video':
        documents['Semantics/shots.jsonl'] = ('shots_local', 'application/x-ndjson', _jsonl(shots))
    return documents


def _bundle_revision_id(composition, selection):
    return _identity('local-bundle-revision', composition['request_sha256'],
                     selection.model_dump(mode='json'))


def _validate_outputs(documents, outputs, *, masters, assets):
    """Require an actual produced artifact for every requested output role.

    Media roles count only through the actual registered master assets, and
    documents count only through the fixed local document tables. A path merely
    inserted into the documents mapping therefore cannot impersonate the
    subtitle/transcript documents this profile never produces.
    """
    produced = {path for path in documents if path in DOCUMENT_PATHS}
    produced |= {ROLE_PATHS[role] for role in masters if role in assets and role in ROLE_PATHS}
    for role in outputs:
        paths = OUTPUT_PATHS.get(role)
        if paths is None:
            raise EngineError('local_output_not_applicable',
                              f'Requested output {role} has no local bundle attachment.', 422)
        if set(paths) <= produced:
            continue
        if role in SPOKEN_OUTPUTS:
            # Local 0.4 has no zero-cue branch (统筹裁定 2026-10-25): the two
            # spoken documents exist only after a real speech observation, so a
            # silent work is refused with the adjudicated 422 and a message that
            # names the missing zero-cue branch instead of implying that some
            # other input could still supply it.
            raise EngineError('local_output_not_applicable',
                              f'Local 0.4 does not produce {role}: this silent work has no speech to transcribe and '
                              'the zero-cue subtitle/transcript branch is not implemented. Request the work without '
                              f'{role}.', 422)
        raise EngineError('local_output_not_applicable',
                          f'Requested output {role} has no actual applicable local material.', 422)


def _slots(documents, *, video):
    required = LOCAL_REQUIRED_FILES | ({'Semantics/shots.jsonl', 'Semantics/visual-mapping.json'} if video else set())
    if not required <= set(documents):
        raise EngineError('local_bundle_material_missing', 'Every required local provenance slot must be produced.', 422)
    return tuple((path, kind, media_type) for path, (kind, media_type, _data) in documents.items())


def _media_artifacts(composition, *, selection, tracks, right):
    artifacts = []
    for role in selection.master_roles:
        try:
            asset = composition['media_assets'][role]
        except KeyError:
            raise EngineError('local_composition_masters_missing',
                              'Every selected master role needs its actual registered asset.', 409) from None
        probe = asset.probe
        artifacts.append(c.BundleArtifact(
            artifact_id=_identity('local-media', role, asset.asset_id), asset_id=asset.asset_id,
            sha256=asset.sha256, size=asset.size, media_type=asset.media_type,
            relative_path=ROLE_PATHS[role], roles=(role,), method_ref=EDIT_METHOD,
            rights_ref=right.rights_id,
            spec=c.ArtifactSpec(duration_us=probe.duration_us, width=probe.width, height=probe.height,
                                audio_clock=tracks[role].clock if role in tracks else None)))
    return tuple(artifacts)


def _document_artifacts(*, documents, receipts, artifact_ids, media_artifacts, right):
    dependencies = {
        'Creative/production-plan.json': (_lineage(artifact_ids, 'Text/approved-script.json'),),
        'Checks/local-master-selection.json': (_lineage(artifact_ids, 'Creative/production-plan.json'),),
        'Checks/local-speech-evidence.json': (_lineage(artifact_ids, ROLE_PATHS['video']),),
        'Checks/quality-report.json': (_lineage(artifact_ids, 'Semantics/semantic-segments.jsonl'),
                                       _lineage(artifact_ids, 'Checks/local-speech-evidence.json')),
        'Semantics/work-summary.json': (_lineage(artifact_ids, 'Creative/production-plan.json'),),
        'Semantics/source-bindings.json': (_lineage(artifact_ids, 'Creative/production-plan.json'),),
        # Video segments come from the actual shot frames; an audio/speech work
        # has no shot document at all and derives its segments from the actual
        # speech evidence, never from a missing key.
        'Semantics/semantic-segments.jsonl': (
            _lineage(artifact_ids, 'Semantics/shots.jsonl') if 'Semantics/shots.jsonl' in artifact_ids
            else _lineage(artifact_ids, 'Checks/local-speech-evidence.json'),),
        'Semantics/rag-chunks.jsonl': (_lineage(artifact_ids, 'Semantics/semantic-segments.jsonl'),),
        'Semantics/shots.jsonl': (_lineage(artifact_ids, ROLE_PATHS['video']),),
        'Semantics/visual-mapping.json': (_lineage(artifact_ids, ROLE_PATHS['video']),),
    }
    methods = {'Semantics/shots.jsonl': DECODER_METHOD,
               'Semantics/visual-mapping.json': DECODER_METHOD,
               'Checks/local-speech-evidence.json': DECODER_METHOD}
    artifacts = list(media_artifacts)
    for path in documents:
        receipt = receipts[path]
        artifacts.append(c.BundleArtifact(artifact_id=artifact_ids[path], material_id=receipt.material_id,
            sha256=receipt.sha256, size=receipt.size, media_type=receipt.media_type, relative_path=path,
            roles=(receipt.schema_kind,), dependency_artifact_ids=dependencies.get(path, ()),
            method_ref=methods.get(path, PLAN_METHOD), rights_ref=right.rights_id))
    return tuple(artifacts)


def _request_version(request):
    if request.request_format_version in {'0.2.0-candidate', '0.3.0-candidate'}:
        return request.request_format_version
    return None


def _assembly_context(*, engine, lease, preparation, intent, manifest, selection,
                      media_artifacts, registration_sha256):
    """Committed local assembly for the Manifest this preparation will verify.

    Every value is copied from the already built actual Manifest, the held
    manifest Clock, the caller's applicable selection and the original
    execution binding. Nothing is invented for a missing master, subtitle,
    transcript, ASR Operation or audio mapping: the sole reachable branch is a
    silent visual work, so the mappings stay empty and there is no ASR source.
    """
    from video_creator.application.current_production_blockers import bound_context

    if 'mixed_audio' in selection.master_roles or manifest.audio_mappings:
        raise EngineError('local_assembly_audio_mapping_unexpected',
                          'This silent local consumer cannot commit an assembly with audio mappings.', 409)
    documents = {ASSEMBLY_DOCUMENT_ROLES[artifact.relative_path]: artifact.artifact_id
                 for artifact in manifest.artifacts
                 if artifact.relative_path in ASSEMBLY_DOCUMENT_ROLES}
    with engine.db.connect_readonly() as connection:
        _run, _production, _request, binding = bound_context(
            engine, connection, lease.run_id, registration_sha256)
    try:
        return LocalFinalAssemblyContextV1(
            corrected_from=None, correction_reason=None,
            binding=binding, preparation_id=preparation.preparation_id,
            preparation_intent_sha256=digest(canonical(intent)),
            authored_fence=lease.fencing_token,
            manifest_created_at_us=manifest.created_at_us,
            timeline_duration_us=manifest.timeline_duration_us,
            creative_revision_refs=manifest.creative_revision_refs,
            approval_refs=manifest.approval_refs,
            feedback_revision_refs=manifest.feedback_revision_refs,
            source_refs=manifest.source_refs, outputs=manifest.outputs,
            media_artifacts=media_artifacts, audio_mappings=(),
            methods=manifest.methods, rights=manifest.rights, quality_ref=manifest.quality_ref,
            document_artifact_ids=documents, asr_operation_id=None, selection=selection)
    except ValidationError as error:
        # A shape/identity disagreement is a named terminal refusal, never an
        # uncaught Pydantic error escaping the worker as a 500.
        raise EngineError('local_assembly_context_invalid',
                          'The actual local assembly values do not satisfy the committed local contract.', 422) from error


def _produce_local(engine, bundle, executor, media, lease, *, production_services,
        local_material_context, selection, media_roles, asr_route_id,
        plan_admission, production_rights_fact, final_evidence_ports=None):
    from video_creator.application.local_material_sources import (
        LocalMaterialFinalContext,
    )
    from video_creator.workflows.current_final_evidence import require_final_port
    from video_creator.workflows.local_material_production import (
        LocalMaterialPolicyServices,
        LocalMaterialServices,
    )

    control = current_attempt()
    control.check()
    if type(production_services) not in {LocalMaterialServices, LocalMaterialPolicyServices}:
        raise EngineError('local_final_services_invalid', 'Use the original fixed local services object.', 503)
    if type(local_material_context) is not LocalMaterialFinalContext:
        raise EngineError('local_final_context_denied', 'The sole held local final context is required.', 403)
    if type(selection) is not LocalMasterSelectionV1:
        raise EngineError('local_master_selection_invalid', 'Only the sole actual local selection is allowed.', 422)
    if final_evidence_ports is not None:
        require_final_port(final_evidence_ports)
    # Held decisions only: the caller's live facts differ from the context's in
    # their observation clock, never in identity.
    require_held_final_facts(local_material_context,
        plan_admission=plan_admission, production_rights_fact=production_rights_fact)
    if type(media_roles) is not dict or tuple(media_roles) != selection.master_roles:
        raise EngineError('local_master_roles_invalid',
                          'Caller masters must equal the ordered applicable selection.', 409)
    composition = read_local_final_inputs(production_services, lease,
        local_material_context=local_material_context, media_roles=media_roles)
    control.check()
    request, plan = composition['request'], composition['plan']
    if composition['selection'] != selection or plan.request_ref.run_id != lease.run_id:
        raise EngineError('local_master_selection_conflict',
                          'Selection must be the actual held same-Run applicable set.', 409)
    if selection.outputs != request.outputs:
        raise EngineError('local_output_conflict',
                          'Selection outputs must retain the original request order.', 409)
    rights = composition['rights_fact'].rights
    if len(rights) != 1:
        raise EngineError('local_rights_declaration_ambiguous',
                          'This local profile consumes exactly one actual declaration per work.', 409)
    right = rights[0]
    assets = composition['media_assets']
    tracks = observe_local_audio_coordinates(composition, bundle, lease, media)
    if 'video' in assets:
        video = assets['video']
        if (video.probe.duration_us != plan.timeline.duration_us
                or (video.probe.width, video.probe.height) != (plan.timeline.width, plan.timeline.height)):
            raise EngineError('local_master_timeline_invalid',
                              'Actual video must match the approved frame timeline.', 422)
    audio = bool(plan.timeline.audio_tracks)
    if audio != ('mixed_audio' in assets):
        raise EngineError('local_master_audio_conflict',
                          'Actual mix/audio timeline presence differs from the approved plan.', 409)
    artifact_ids = {ROLE_PATHS[role]: _identity('local-media', role, assets[role].asset_id)
                    for role in selection.master_roles}
    documents_paths = [path for path in DOCUMENT_KINDS]
    if selection.content_kind == 'video':
        documents_paths += [path for path in VISUAL_KINDS]
    artifact_ids.update({path: _identity('local-material', path) for path in documents_paths})
    if audio:
        raise _speech_error(request)
    shots, visuals = (), None
    if selection.content_kind == 'video':
        visuals = visual_mapping_inputs(plan)
        shots = observe_local_frames(composition, bundle, lease, media)
    control.check()
    speech = _absence_evidence(composition, artifact_ids=artifact_ids)
    documents = _documents(composition, bundle, lease, selection=selection, speech=speech,
                           shots=shots, visuals=visuals, right=right, artifact_ids=artifact_ids)
    _validate_outputs(documents, request.outputs, masters=selection.master_roles, assets=assets)
    slots = _slots(documents, video=selection.content_kind == 'video')
    context = bundle.context(lease)
    bundle_id = _identity('local-bundle', composition['request_sha256'],
                          selection.model_dump(mode='json'))
    revision_id = _bundle_revision_id(composition, selection)
    intent = BundlePreparationIntent(bundle_id=bundle_id, bundle_revision_id=revision_id,
        request_revision_id=context.request_revision_id,
        input_sha256=digest(canonical(request)),
        material_slots=tuple(MaterialSlot(artifact_id=artifact_ids[path], relative_path=path,
            schema_kind=kind, media_type=media_type) for path, kind, media_type in slots),
        media_asset_ids=tuple(assets[role].asset_id for role in selection.master_roles))
    preparation = bundle.prepare_local(lease, intent, context=local_material_context)
    receipts = {}
    for path, (_kind, _media_type, data) in documents.items():
        control.check()
        receipts[path] = bundle.stage_material(lease, preparation.preparation_id,
                                               artifact_ids[path], data)
    media_artifacts = _media_artifacts(composition, selection=selection, tracks=tracks, right=right)
    artifacts = _document_artifacts(documents=documents, receipts=receipts,
        artifact_ids=artifact_ids, media_artifacts=media_artifacts, right=right)
    outputs = tuple(c.BundleOutput(role=role, artifact_ids=tuple(
        artifact_ids[path] for path in OUTPUT_PATHS[role])) for role in request.outputs)
    manifest = BundleManifestLocalV1(
        request_format_version=_request_version(request),
        instance_id=engine.instance_id, bundle_id=bundle_id, bundle_revision_id=revision_id,
        project_id=context.project_id, production_id=context.production_id, run_id=lease.run_id,
        request_revision_id=context.request_revision_id,
        request_sha256=composition['request_sha256'], workflow_version=PROFILE,
        created_at_us=engine.clock(), timeline_duration_us=plan.timeline.duration_us,
        creative_revision_refs=composition['creative_revision_refs'],
        approval_refs=composition['approval_refs'], feedback_revision_refs=composition['feedback_refs'],
        source_refs=_source_refs(composition), requested_outputs=request.outputs, outputs=outputs,
        artifacts=artifacts, audio_mappings=(), rights=(right,),
        quality_ref=composition['creative_revision_refs'][2],
        methods=_methods(composition, artifact_ids, video=selection.content_kind == 'video',
                         media=media, registration_sha256=production_services.registration_sha256),
        selection_artifact_id=artifact_ids['Checks/local-master-selection.json'],
        speech_evidence_artifact_id=artifact_ids['Checks/local-speech-evidence.json'],
        visual_mapping_artifact_id=(artifact_ids['Semantics/visual-mapping.json']
                                    if selection.content_kind == 'video' else None))
    control.check()
    assembly = _assembly_context(engine=engine, lease=lease, preparation=preparation,
        intent=intent, manifest=manifest, selection=selection,
        media_artifacts=media_artifacts,
        registration_sha256=production_services.registration_sha256)
    commit = require_final_port(final_evidence_ports).persist_assembly_context(
        lease, preparation.preparation_id, assembly)
    raw = (canonical(assembly) + '\n').encode('utf-8')
    if (type(commit) is not AssemblyContextRef
            or commit.preparation_id != preparation.preparation_id
            or commit.preparation_intent_sha256 != assembly.preparation_intent_sha256
            or (commit.content_sha256, commit.size) != (hashlib.sha256(raw).hexdigest(), len(raw))):
        raise EngineError('local_assembly_commit_invalid',
                          'Only the actual committed local assembly reference can precede Bundle verification.', 409)
    control.check()
    verified = bundle.verify_local(lease, preparation.preparation_id, manifest)
    control.check()
    reference = bundle.publish(lease, verified)
    from video_creator.workflows.bundle_producer import BundleProductionResult
    return BundleProductionResult('published', preparation.preparation_id, manifest,
        tuple(receipts.values()), bundle_ref=reference)


def _source_refs(composition):
    from video_creator.workflows.local_semantics import local_source_refs
    return local_source_refs(composition)


def produce_local_bundle(engine, bundle, executor, media, lease, *,
        production_services, local_material_context, selection, media_roles, asr_route_id,
        plan_admission, production_rights_fact, final_evidence_ports=None,
        cancel=None, deadline_monotonic=None):
    """Sole local produce entry; returns the ordinary Bundle publication result.

    `selection`/`media_roles` are the caller's actual applicable masters and
    `plan_admission`/`production_rights_fact` must be the same held facts. No
    ASR resource is loaded and no v2/v3 argument is accepted.
    """
    with attempt_control(cancel, deadline_monotonic).activate():
        return _produce_local(engine, bundle, executor, media, lease,
            production_services=production_services,
            local_material_context=local_material_context, selection=selection,
            media_roles=media_roles, asr_route_id=asr_route_id,
            plan_admission=plan_admission, production_rights_fact=production_rights_fact,
            final_evidence_ports=final_evidence_ports)
