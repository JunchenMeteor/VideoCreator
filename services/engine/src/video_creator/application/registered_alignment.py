"""Original held sources, immutable alignment registration and JSON Step commit."""

import hashlib

from pydantic import ValidationError

from video_creator.application.affected_repair_service import canonical_body
from video_creator.application.committed_alignment_read import (
    CommittedAlignmentReadService,
)
from video_creator.application.engine import canonical, digest, identity
from video_creator.domain import contracts as c
from video_creator.domain import local_bundle as local
from video_creator.domain.affected_repair import AlignmentResourceSection
from video_creator.domain.errors import EngineError
from video_creator.domain.registered_alignment import (
    AffectedAlignmentRequest,
    AlignmentAsrSource,
    AlignmentAudioSource,
    AlignmentRegistrationSource,
    AlignmentTranscriptSource,
    AlignmentUnitSource,
    InitialAlignmentRequest,
    ReadyAlignmentTranscriptSource,
    alignment_request_bytes,
)
from video_creator.domain.worker import GeneratedFileManifest

INITIAL_PREFIX = 'current_initial_alignment:'
AFFECTED_PREFIX = 'current_affected_alignment:'
MAX_JSON_BYTES = 8 * 1024 * 1024


def registered_alignment_locator(connection, lease, step_key):
    from video_creator.application.bundles import strict_json
    initial = step_key.startswith('bundle-alignment-')
    prefix = INITIAL_PREFIX if initial else AFFECTED_PREFIX
    matches = []
    for row in connection.execute('SELECT key,value FROM metadata WHERE key LIKE ?', (prefix + '%',)):
        body = strict_json(row['value'].encode('utf-8'))
        if body.get('descriptor', {}).get('step_key') == step_key:
            request = _parse_request(body['canonical_request_utf8'].encode('utf-8'), initial)
            if request.binding.run_id == lease.run_id:
                matches.append(row['key'][len(prefix):])
    if len(matches) != 1:
        raise EngineError('alignment_step_denied', 'One actual original registered full alignment Step required', 403)
    return matches[0], initial


def assert_registered_alignment_step(connection, engine, lease, step_key, input_sha256, *, intent=None, authorization_guard=None):
    source = getattr(engine, '_registered_plan_source', None)
    if source is None:
        raise EngineError('alignment_step_denied', 'Actual installed same-Engine source required', 403)
    locator, initial = registered_alignment_locator(connection, lease, step_key)
    body, _payload = source.assert_alignment_writer(connection, lease, locator, initial=initial, guard=authorization_guard)
    if body['request_sha256'] != input_sha256:
        raise EngineError('alignment_step_denied', 'Original full canonical request SHA required', 403)
    if intent is not None and intent != source._alignment_intent(body):
        raise EngineError('alignment_step_denied', 'Original exact route/input/dedupe/free cost required', 403)


def _semantic_sha(model):
    return digest(canonical_body({key: value for key, value in model.model_dump(mode='json').items()
                                 if key != 'content_sha256'}))


def _check_semantic(model):
    if model.content_sha256 != _semantic_sha(model):
        raise EngineError('alignment_source_invalid', 'Original complete semantic content SHA changed', 422)


def _parse_request(raw, initial):
    from video_creator.application.bundles import strict_json
    try:
        strict_json(raw)
        request = (InitialAlignmentRequest if initial else AffectedAlignmentRequest).model_validate_json(raw)
    except (ValidationError, ValueError, TypeError):
        raise EngineError('alignment_binding_invalid', 'Strict original alignment request damaged', 422) from None
    if alignment_request_bytes(request) != raw:
        raise EngineError('alignment_binding_invalid', 'Original canonical request bytes required', 422)
    return request


class RegisteredAlignmentService(CommittedAlignmentReadService):
    def preflight_registered_alignment_step(self, lease, step_key):
        with self.engine.db.connect_readonly() as connection:
            self.engine._lease(connection, lease)
            locator, initial = registered_alignment_locator(connection, lease, step_key)
        self._alignment_preflight(lease, locator, initial=initial)

    def _initial_assembly_facts(self, lease, row, intent, binding, context, *, author):
        """Only real pre-READY initial assembly; no fake transcript receipt."""
        from video_creator.application.bundles import validate_text
        held = self._affected_services(lease)
        runtime = self._production_services_runtime
        if getattr(runtime.config, 'alignment_registration', None) is None:
            raise EngineError('alignment_resource_not_ready', 'Actual initial alignment source required', 503)
        if (context.binding != binding or context.preparation_id != row['id']
                or context.preparation_intent_sha256 != digest(row['intent_json'])
                or author and context.authored_fence != lease.fencing_token):
            raise EngineError('final_assembly_binding_invalid', 'Actual same-preparation initial author required', 409)
        prepared = self.recover_preparation(lease, row['id'])
        receipts = {receipt.artifact_id: receipt for receipt in prepared.materials}
        slots = {slot.artifact_id: slot for slot in intent.material_slots}
        if not set(context.document_artifact_ids.values()) <= set(slots):
            raise EngineError('final_assembly_document_invalid', 'Original actual allocated initial documents required', 422)
        late = {'transcript', 'srt', 'vtt', 'segments', 'rag', 'quality', 'audit',
                'work_validation', 'measurement', 'reference', 'policy', 'qualification', 'benchmark'}
        for role, artifact_id in context.document_artifact_ids.items():
            from video_creator.application.current_final_evidence_recovery import (
                DOCUMENT_PATHS,
            )
            slot = slots[artifact_id]
            if role in DOCUMENT_PATHS and slot.relative_path != DOCUMENT_PATHS[role]:
                raise EngineError('final_assembly_document_invalid', 'Original initial document path changed', 422)
            receipt = receipts.get(artifact_id)
            if receipt is not None:
                validate_text(self.read_material(lease, row['id'], receipt.material_id), slot.schema_kind, slot.media_type)
            elif role not in late:
                raise EngineError('final_assembly_material_missing', 'Original source materials must be READY before initial context', 409)
        speech_ready = any(context.document_artifact_ids.get(role) in receipts for role in ('transcript', 'srt', 'vtt', 'segments', 'rag'))
        if speech_ready and author:
            raise EngineError('initial_alignment_source_denied', 'Initial context cannot overwrite READY final speech materials', 403)
        if speech_ready:
            committed, _file, _observation = self._read_alignment(lease, row['id'], initial=True)
            receipt = receipts.get(context.document_artifact_ids.get('transcript'))
            if receipt is not None:
                document = validate_text(self.read_material(lease, row['id'], receipt.material_id), receipt.schema_kind, receipt.media_type)
                with self.engine.db.connect_readonly() as connection:
                    _body, request, _raw = self._load_alignment(connection, lease, row['id'], initial=True)
                if (not isinstance(document, (c.ActualTranscriptDocument, c.ActualTranscriptDocumentV03))
                        or document.transcript != request.transcript.transcript or type(document.alignment) is not type(committed)
                        or document.alignment.model_dump(mode='json', exclude={'precision', 'content_sha256'})
                        != committed.model_dump(mode='json', exclude={'precision', 'content_sha256'})):
                    raise EngineError('initial_alignment_source_denied', 'Partial READY transcript must retain actual committed CTC', 422)
                _check_semantic(document.alignment)
        masters = self.resolve_preparation_masters(lease, row['id'])
        if {a.asset_id for a in context.media_artifacts} != set(intent.media_asset_ids):
            raise EngineError('final_assembly_media_invalid', 'Exactly original four masters required', 422)
        for artifact in context.media_artifacts:
            if len(artifact.roles) != 1 or artifact.roles[0] not in masters:
                raise EngineError('final_assembly_media_invalid', 'Original exact master roles required', 422)
            asset = masters[artifact.roles[0]]
            if (artifact.asset_id, artifact.sha256, artifact.size, artifact.media_type) != (
                    asset.asset_id, asset.sha256, asset.size, asset.media_type):
                raise EngineError('final_assembly_media_invalid', 'Actual full master bytes differ', 422)
        creative = {revision.revision_id: revision for revision in self.creative_revisions(lease)}
        for ref in (*context.creative_revision_refs, context.quality_ref):
            value = creative.get(ref.revision_id)
            if value is None or value.kind != ref.kind or digest(canonical(value)) != ref.content_sha256:
                raise EngineError('final_assembly_revision_invalid', 'Original full committed revision required', 422)
        if any(ref not in self.approval_refs(lease) for ref in context.approval_refs) or any(
                ref not in self.feedback_refs(lease) for ref in context.feedback_revision_refs):
            raise EngineError('final_assembly_revision_invalid', 'Original approvals/feedback required', 422)
        self._production_services_runtime._current_final_execution_facts(lease, held[1], held[5])
        asr = self._original_asr().read_settled_original_asr(lease, context.asr_operation_id)
        if asr is None or asr.observation.result_json.get('input_audio_sha256') != masters['mixed_audio'].sha256:
            raise EngineError('asr_recovery_validation_unavailable', 'Original full successful ASR/context required', 503)
        methods = [method for method in context.methods if context.asr_operation_id in method.operation_ids]
        if len(methods) != 1 or methods[0].config_sha256 != asr.input_sha256 or methods[0].resource_manifest_sha256 != asr.context_ref.resource_manifest_sha256:
            raise EngineError('final_assembly_asr_invalid', 'Actual original ASR method/context identity required', 422)
        self._assembly_correction_context(lease, row['id'], context)
        self.assert_current_correction_pair(lease, row['id'], context=context)
        return asr
    def _alignment_registration(self, lease, transcript, prediction):
        from video_creator.application.bundles import strict_json
        held = self._affected_services(lease)
        runtime = self._production_services_runtime
        registration = getattr(runtime.config, 'alignment_registration', None)
        if registration is None or runtime.production_manifest is None:
            raise EngineError('alignment_resource_not_ready', 'Actual installed alignment registration required', 503)
        path = runtime.production_manifest
        if not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
            raise EngineError('alignment_resource_not_ready', 'Complete bounded installed resource index required', 503)
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != held[6]:
            raise EngineError('alignment_resource_changed', 'Original held resource manifest changed', 409)
        try:
            section = AlignmentResourceSection.model_validate_json(canonical_body(strict_json(raw)['production_drivers']['alignment']))
        except (KeyError, ValidationError, TypeError, ValueError):
            raise EngineError('alignment_resource_not_ready', 'Strict actual alignment resource section required', 503) from None
        route = self.engine.configured_route(registration.route_id)
        if (not route.verified or route.source != 'owned_local' or route.capability != 'alignment'
                or route.credential_ref or route.max_operation_cost.units()):
            raise EngineError('alignment_resource_not_ready', 'Verified free local alignment route required', 503)
        with self.engine.db.connect_readonly() as connection:
            run = self.engine._lease(connection, lease)
            production = self.engine._production(connection, run['production_id'])
            request = c.parse_production_request(production['request_json'])
            if not isinstance(request, c.ProductionRequestV03) or request.delivery_requirements is None:
                raise EngineError('alignment_resource_not_ready', 'Actual admitted method policy reference required', 503)
            resolved = self.engine.evidence_registry.resolve(production['owner'], production['project_id'],
                request.delivery_requirements.evidence_policy_revision_ref, connection=connection)
        qualification = registration.method_qualification_ref
        execution = qualification.execution_identity
        applicability = qualification.applicability
        if (qualification != resolved.qualification or execution.resource_manifest_sha256 != held[6]
                or execution.configuration_sha256 != section.configuration_sha256
                or execution.model_file_sha256 != section.model_files
                or applicability.units != prediction.units or transcript.language not in applicability.languages
                or transcript.duration_us > applicability.maximum_duration_us):
            raise EngineError('alignment_resource_not_ready', 'Actual method/model/configuration/applicability qualification required', 503)
        # These files remain in the original protected installed index; hashing
        # them is evidence of identity, never an issuer or a substitute license.
        hashes = {}
        for name in (*section.model_files, section.worker_resource, section.runtime_resource):
            resource = runtime.runtime_root / name
            if not resource.is_file():
                raise EngineError('alignment_resource_not_ready', 'Original installed alignment file missing', 503)
            hashes[name] = self.assets._hash(resource)
        if any(hashes[name] != expected for name, expected in section.model_files.items()):
            raise EngineError('alignment_resource_changed', 'Actual installed model files differ from qualified input', 409)
        self.assert_current_production_services(lease, held[0], held[1])
        return AlignmentRegistrationSource(registration=registration, route_sha256=digest(canonical(route)),
            resource_manifest_sha256=held[6], runtime_manifest_sha256=held[7], resources=section,
            worker_sha256=hashes[section.worker_resource], runtime_sha256=hashes[section.runtime_resource])

    def _alignment_sources(self, lease, preparation_id, context, transcript, prediction, mapping, *, initial):
        if (type(transcript) is not c.ActualTranscriptRevision or type(prediction) not in {c.AlignmentRevision, c.AlignmentRevisionV03}
                or type(mapping) is not c.AudioTimelineMapping):
            raise EngineError('alignment_source_invalid', 'Original strict transcript/alignment/mapping models required', 422)
        _check_semantic(transcript)
        _check_semantic(prediction)
        _check_semantic(mapping)
        if (transcript.transcript_revision_id, transcript.content_sha256, transcript.input_audio_asset_id,
                transcript.input_audio_sha256) != (prediction.actual_transcript_revision_id,
                prediction.transcript_content_sha256, prediction.input_audio_asset_id, prediction.input_audio_sha256):
            raise EngineError('alignment_source_invalid', 'Original actual transcript and predicted units differ', 422)
        if context.audio_mappings != (mapping,) or transcript.approved_script_revision_ref not in context.creative_revision_refs:
            raise EngineError('alignment_source_invalid', 'Original saved mapping and approved script required', 422)
        asr = self._original_asr().read_settled_original_asr(lease, context.asr_operation_id)
        if asr is None:
            raise EngineError('asr_recovery_validation_unavailable', 'Original committed complete ASR context required', 503)
        actual = asr.observation.result_json
        segments = actual.get('segments')
        if (actual.get('input_audio_sha256'), actual.get('language'), actual.get('text')) != (
                transcript.input_audio_sha256, transcript.language, transcript.text) or not isinstance(segments, list):
            raise EngineError('alignment_source_invalid', 'Original successful settled ASR text/language/audio required', 422)
        if len(segments) != len(transcript.utterances):
            raise EngineError('alignment_source_invalid', 'Original ASR segment sequence changed', 422)
        for utterance, segment in zip(transcript.utterances, segments, strict=True):
            if (utterance.text, utterance.intrinsic_range.start_us, utterance.intrinsic_range.end_us) != (
                    segment.get('text'), segment.get('start_us'), segment.get('end_us')):
                raise EngineError('alignment_source_invalid', 'Original ASR segment boundaries and text required', 422)
            words = segment.get('words', [])
            if len(utterance.words) != len(words) or any((word.text, word.intrinsic_range.start_us, word.intrinsic_range.end_us)
                    != (original.get('text'), original.get('start_us'), original.get('end_us'))
                    for word, original in zip(utterance.words, words, strict=True)):
                raise EngineError('alignment_source_invalid', 'Original ASR word sequence required', 422)
        asr_methods = [method for method in context.methods if context.asr_operation_id in method.operation_ids]
        if len(asr_methods) != 1 or transcript.method_ref != asr_methods[0].method_id:
            raise EngineError('alignment_source_invalid', 'Original transcript ASR method identity required', 422)
        if initial and prediction.method_ref != transcript.method_ref:
            raise EngineError('alignment_source_invalid', 'Initial prediction requires original ASR method identity', 422)
        masters = self.resolve_preparation_masters(lease, preparation_id)
        audio = masters['mixed_audio']
        if (audio.asset_id, audio.sha256) != (transcript.input_audio_asset_id, transcript.input_audio_sha256):
            raise EngineError('alignment_source_invalid', 'Original effective mixed master required', 422)
        if self.audio_clock_authority is None or not self.audio_clock_authority(transcript.input_track, self.content_path(lease, audio.asset_id)):
            raise EngineError('alignment_source_invalid', 'Actual decoded original audio sample clock required', 422)
        if not self.audio_clock_authority(mapping.target_track, self.content_path(lease, mapping.target_video_asset_id)):
            raise EngineError('alignment_source_invalid', 'Original video encoded sample clock required', 422)
        for piece in mapping.pieces:
            if not self.audio_clock_authority(piece.source_track, self.content_path(lease, piece.source_track.asset_id)):
                raise EngineError('alignment_source_invalid', 'Original mapped source sample clock required', 422)
        self._assembly_correction_context(lease, preparation_id, context)
        self.assert_current_correction_pair(lease, preparation_id, context=context)
        with self.engine.db.connect_readonly() as connection:
            self.engine._lease(connection, lease)
            staged = connection.execute('SELECT sha256,size,status FROM staging WHERE id=?', (asr.allocation.staging_id,)).fetchone()
        if staged is None or staged['status'] not in {'ready', 'imported'}:
            raise EngineError('alignment_source_invalid', 'Actual original ASR READY allocation required', 422)
        asr_source = AlignmentAsrSource(operation_id=asr.operation_id, input_sha256=asr.input_sha256,
            route_sha256=asr.route_sha256, staging_id=asr.allocation.staging_id, result_file_sha256=staged['sha256'],
            context_ref=asr.context_ref, context_file_sha256=hashlib.sha256(asr.original_context_bytes).hexdigest())
        audio_source = AlignmentAudioSource(asset_id=audio.asset_id, sha256=audio.sha256, size=audio.size,
            media_type=audio.media_type, input_track=transcript.input_track, mapping=mapping, mapping_content_sha256=mapping.content_sha256)
        utterances = {item.utterance_id: item for item in transcript.utterances}
        words = {word.word_id: (utterance, word) for utterance in transcript.utterances for word in utterance.words}
        units = []
        for unit in prediction.boundaries:
            word_id = None
            if prediction.units == 'utterance':
                utterance = utterances.get(unit.transcript_unit_id)
                if utterance is None:
                    raise EngineError('alignment_source_invalid', 'Original predicted utterance ID missing', 422)
                text, start, end = utterance.text, 0, len(utterance.text)
                original_range = utterance.intrinsic_range
            else:
                pair = words.get(unit.transcript_unit_id)
                if pair is None:
                    raise EngineError('alignment_source_invalid', 'Original predicted word ID missing', 422)
                utterance, word = pair
                original_range = word.intrinsic_range
                start = sum(len(value.text) for value in utterance.words[:utterance.words.index(word)])
                end, text, word_id = start + len(word.text), word.text, word.word_id
                if utterance.text[start:end] != text:
                    raise EngineError('alignment_source_unalignable', 'ASR word-to-scalar mapping is not uniquely recoverable', 422)
            if initial and unit.intrinsic_range != original_range:
                raise EngineError('alignment_source_invalid', 'Initial prediction requires original ASR boundaries', 422)
            units.append(AlignmentUnitSource(alignment_unit_id=unit.unit_id, transcript_unit_id=unit.transcript_unit_id,
                utterance_id=utterance.utterance_id, word_id=word_id, text=text, scalar_start=start, scalar_end=end,
                predicted_range=unit.intrinsic_range))
        if not units or len({unit.transcript_unit_id for unit in units}) != len(units):
            raise EngineError('alignment_source_unalignable', 'Complete original distinct alignment units required', 422)
        complete_ids = (tuple(item.utterance_id for item in transcript.utterances) if prediction.units == 'utterance'
                        else tuple(word.word_id for utterance in transcript.utterances for word in utterance.words))
        if tuple(unit.transcript_unit_id for unit in units) != complete_ids:
            raise EngineError('alignment_source_unalignable', 'Original complete ordered actual speech units required', 422)
        return audio_source, asr_source, tuple(units)

    def _alignment_companion(self, request, prediction, context_sha):
        raw = alignment_request_bytes(request)
        sha = hashlib.sha256(raw).hexdigest()
        initial = type(request) is InitialAlignmentRequest
        key = ('bundle-alignment-' + sha[:32]) if initial else ('repair-alignment-' + request.repair_command_sha256[:32])
        return {'format': 'current-initial-alignment-binding-v1' if initial else 'current-affected-alignment-binding-v1',
            'canonical_request_utf8': raw.decode('utf-8'), 'request_sha256': sha,
            'source_prediction': prediction.model_dump(mode='json'), 'assembly_context_sha256': context_sha,
            'output_alignment_revision_id': request.output_alignment_revision_id,
            'descriptor': {'step_key': key, 'stage': 'alignment', 'shot_id': None, 'input_sha256': sha,
                'dedupe_key': key, 'route_id': request.alignment_registration.registration.route_id}}

    def _load_alignment(self, connection, lease, locator, *, initial):
        from video_creator.application.bundles import strict_json
        prefix = INITIAL_PREFIX if initial else AFFECTED_PREFIX
        saved = connection.execute('SELECT value FROM metadata WHERE key=?', (prefix + locator,)).fetchone()
        if saved is None:
            raise EngineError('alignment_registration_missing', 'Original immutable alignment registration missing', 503)
        body = strict_json(saved[0].encode('utf-8'))
        if (not isinstance(body, dict) or set(body) != {'format', 'canonical_request_utf8', 'request_sha256',
                'source_prediction', 'assembly_context_sha256', 'output_alignment_revision_id', 'descriptor'}
                or body['format'] != ('current-initial-alignment-binding-v1' if initial else 'current-affected-alignment-binding-v1')):
            raise EngineError('alignment_binding_invalid', 'Closed original alignment binding required', 422)
        if type(body['canonical_request_utf8']) is not str:
            raise EngineError('alignment_binding_invalid', 'Original request must be canonical UTF8 text', 422)
        raw = body['canonical_request_utf8'].encode('utf-8')
        if len(raw) > MAX_JSON_BYTES or hashlib.sha256(raw).hexdigest() != body['request_sha256']:
            raise EngineError('alignment_binding_invalid', 'Original full canonical alignment SHA required', 422)
        request = _parse_request(raw, initial)
        if (request.binding.run_id != lease.run_id or request.output_alignment_revision_id != body['output_alignment_revision_id']
                or (request.preparation_id if initial else request.repair_command_sha256) != locator):
            raise EngineError('alignment_binding_invalid', 'Original Run/request locator differs', 422)
        key = 'bundle-alignment-' + body['request_sha256'][:32] if initial else 'repair-alignment-' + locator[:32]
        expected = {'step_key': key, 'stage': 'alignment', 'shot_id': None, 'input_sha256': body['request_sha256'],
            'dedupe_key': key, 'route_id': request.alignment_registration.registration.route_id}
        if body['descriptor'] != expected:
            raise EngineError('alignment_binding_invalid', 'Original exact registered alignment descriptor changed', 422)
        return body, request, raw

    def _alignment_intent(self, body):
        descriptor = body['descriptor']
        return c.OperationIntent(step_key=descriptor['step_key'], input_sha256=descriptor['input_sha256'],
            route_id=descriptor['route_id'], dedupe_key=descriptor['dedupe_key'], reserved_cost=c.Money(amount='0'))

    def _alignment_preflight(self, lease, locator, *, initial, execution=None):
        self._affected_services(lease)
        issuer = self._production_authorization.issuer()
        with issuer.current_guard(self._production_authorization.registered(lease)) as guard:
            with self.engine.db.connect_readonly() as connection:
                body, request, raw = self._load_alignment(connection, lease, locator, initial=initial)
                self.assert_alignment_writer(connection, lease, locator, initial=initial, guard=guard, execution=execution)
                preparation_id = request.preparation_id if initial else request.parent_preparation_id
                row, _run, _production, _request = self._preparation(connection, lease, preparation_id)
            context = self._read_final_assembly(row, request.binding)
            if context is None or digest(canonical(context) + '\n') != body['assembly_context_sha256']:
                raise EngineError('alignment_source_changed', 'Original saved assembly changed', 409)
            prediction = self._alignment_prediction(body)
            audio, asr, units = self._alignment_sources(lease, preparation_id, context,
                request.transcript.transcript, prediction, request.audio.mapping, initial=initial)
            registration = self._alignment_registration(lease, request.transcript.transcript, prediction)
            if (audio, asr, units, registration) != (request.audio, request.transcript.asr_source,
                    request.unit_sources, request.alignment_registration):
                raise EngineError('alignment_source_changed', 'Original complete request/source/resource facts changed', 409)
            with self.engine.db.connect_readonly() as connection:
                self.assert_alignment_writer(connection, lease, locator, initial=initial, guard=guard, execution=execution)
                current, _request, _raw = self._load_alignment(connection, lease, locator, initial=initial)
                if current != body:
                    raise EngineError('alignment_binding_invalid', 'Original immutable companion changed', 422)
        return body, request, raw

    @staticmethod
    def _alignment_prediction(body):
        data = body['source_prediction']
        family = c.AlignmentRevisionV03 if 'evaluation_scope' in data.get('precision', {}) else c.AlignmentRevision
        try:
            result = family.model_validate(data)
        except ValidationError:
            raise EngineError('alignment_binding_invalid', 'Original prediction schema changed', 422) from None
        _check_semantic(result)
        return result

    def registered_alignment_intent(self, lease, execution):
        body, _request, _raw = self._alignment_preflight(lease, execution.repair_command_sha256, initial=False, execution=execution)
        return self._alignment_intent(body)

    def registered_alignment_request(self, lease, execution):
        _body, _request, raw = self._alignment_preflight(lease, execution.repair_command_sha256, initial=False, execution=execution)
        return raw

    def registered_initial_alignment_request(self, lease, preparation_id):
        _body, _request, raw = self._alignment_preflight(lease, preparation_id, initial=True)
        return raw

    def commit_registered_alignment_result(self, lease, execution, *, files):
        return self._commit_alignment(lease, execution.repair_command_sha256, files=files, initial=False, execution=execution)

    def read_registered_alignment_result(self, lease, execution):
        return self._read_alignment(lease, execution.repair_command_sha256, initial=False, execution=execution)

    def commit_registered_initial_alignment_result(self, lease, preparation_id, *, files):
        return self._commit_alignment(lease, preparation_id, files=files, initial=True)

    def read_registered_initial_alignment_result(self, lease, preparation_id):
        return self._read_alignment(lease, preparation_id, initial=True)

    def registered_initial_alignment_method(self, lease, preparation_id):
        """Original ledger-derived MethodEvidence, never caller manifest data."""
        self._read_alignment(lease, preparation_id, initial=True)
        body, request, _raw = self._alignment_preflight(lease, preparation_id, initial=True)
        with self.engine.db.connect_readonly() as connection:
            self.engine._lease(connection, lease)
            operations = connection.execute('SELECT * FROM operations WHERE run_id=? AND step_key=?',
                (lease.run_id, body['descriptor']['step_key'])).fetchall()
            if len(operations) != 1 or operations[0]['status'] != 'succeeded' or not operations[0]['settled']:
                raise EngineError('alignment_result_missing', 'One original succeeded settled initial operation required', 409, 'reconcile')
            operation_id = operations[0]['id']
            row, _run, _production, _request = self._preparation(connection, lease, preparation_id)
        assembly = self._read_final_assembly(row, request.binding)
        if assembly is None:
            raise EngineError('final_assembly_unavailable', 'Original immutable initial assembly missing', 503)
        audio_artifacts = tuple(artifact.artifact_id for artifact in assembly.media_artifacts
                                if artifact.asset_id == request.audio.asset_id and artifact.roles == ('mixed_audio',))
        if len(audio_artifacts) != 1:
            raise EngineError('alignment_source_invalid', 'Original actual mixed audio artifact required', 422)
        execution = request.alignment_registration.registration.method_qualification_ref.execution_identity
        return c.MethodEvidence(method_id=execution.method_id, kind='model_inference', tool_name=execution.tool,
            tool_version=execution.tool_version, model_repository=execution.model_id,
            model_revision=request.alignment_registration.resources.model_revision,
            resource_manifest_sha256=request.alignment_registration.resource_manifest_sha256,
            operation_ids=(operation_id,), input_artifact_ids=audio_artifacts,
            config_sha256=execution.configuration_sha256,
            limitations=('Actual forced alignment is not independent work-boundary measurement.',))

    def registered_ctc_work_source(self, lease, preparation_id, actual, report):
        """Use the same selected committed read composition as the held getter."""
        local_v03 = isinstance(actual, local.LocalActualTranscriptDocumentV1) and isinstance(actual.alignment, c.AlignmentRevisionV03)
        if not (isinstance(actual, c.ActualTranscriptDocumentV03) or local_v03) or not isinstance(report, c.WorkAlignmentValidationReport):
            return None
        with self.engine.db.connect_readonly() as connection:
            self.engine._lease(connection, lease)
            initial = connection.execute('SELECT 1 FROM metadata WHERE key=?', (INITIAL_PREFIX + preparation_id,)).fetchone()
            lineage = connection.execute('SELECT 1 FROM metadata WHERE key=?', ('current_final_evidence_lineage:' + preparation_id,)).fetchone()
        if initial is None and lineage is None:
            # Existing normal unregistered ASR-only work remains the original
            # runtime validator branch. This is not the new held getter.
            return None
        return self._validate_composed_ctc_work_source(lease, preparation_id, actual, report)

    def _registered_initial_alignment(self, lease, preparation_id):
        """True only when a real registered initial CTC source exists for this preparation."""
        with self.engine.db.connect_readonly() as connection:
            self.engine._lease(connection, lease)
            return bool(
                connection.execute('SELECT 1 FROM metadata WHERE key=?',
                                   (INITIAL_PREFIX + preparation_id,)).fetchone()
                or connection.execute('SELECT 1 FROM metadata WHERE key=?',
                                      ('current_final_evidence_lineage:' + preparation_id,)).fetchone())

    @staticmethod
    def assert_registered_ctc_work_writer(connection, expected):
        if expected is None:
            return
        queries = {'metadata': 'SELECT * FROM metadata WHERE key=?',
                   'operations': 'SELECT * FROM operations WHERE id=?', 'steps': 'SELECT * FROM steps WHERE run_id=? AND step_key=?',
                   'generated_attempts': 'SELECT * FROM generated_attempts WHERE id=?',
                   'staging': 'SELECT * FROM staging WHERE id=?', 'assets': 'SELECT * FROM assets WHERE id=?',
                   'bundle_revisions': 'SELECT * FROM bundle_revisions WHERE id=?', 'routes': 'SELECT * FROM routes WHERE id=?',
                   'creative_revisions': 'SELECT * FROM creative_revisions WHERE id=?',
                   'feedback_revisions': 'SELECT * FROM feedback_revisions WHERE id=?',
                   'decisions': 'SELECT * FROM decisions WHERE run_id=? AND idempotency_key=?'}
        for table, _column, key, original in expected:
            if table == 'text_materials':
                observed = tuple(dict(row) for row in connection.execute(
                    'SELECT * FROM bundle_items WHERE preparation_id=? AND asset_id IS NULL ORDER BY artifact_id', (key,)))
                if observed != original:
                    raise EngineError('work_ctc_source_changed', 'Original selected material allocation set changed', 409)
                continue
            row = connection.execute(queries[table], key if table in {'steps', 'decisions'} else (key,)).fetchone()
            observed = ({field: row[field] for field in original} if row is not None and table == 'bundle_revisions'
                        else dict(row) if row is not None else None)
            if observed != original:
                raise EngineError('work_ctc_source_changed', 'Original CTC/ASR/child source changed at writer boundary', 409)

    def registered_ctc_work_manifest_source(self, lease, preparation_id, manifest):
        if not isinstance(manifest, (c.BundleManifestV03, local.BundleManifestLocalV1)):
            return None
        prepared = self.recover_preparation(lease, preparation_id)
        documents, _snapshot = self._initial_precision_materials(lease, preparation_id, manifest, prepared)
        actual = documents.get('Text/actual-transcript.json')
        report = documents.get('Checks/work-alignment-validation.json')
        if isinstance(manifest, local.BundleManifestLocalV1):
            if actual is None or isinstance(actual, local.LocalActualTranscriptDocumentV1) and actual.alignment is None:
                return None
            quality = documents.get('Checks/quality-report.json')
            if not isinstance(quality, local.LocalBundleQualityEvidenceV1):
                raise EngineError('local_quality_missing', 'Local CTC requires original typed quality reports.', 422)
            indexed = {item.artifact_id: item for item in manifest.artifacts}
            reports = [documents.get(indexed[identifier].relative_path) for identifier in quality.alignment_report_artifact_ids if identifier in indexed]
            matched = [item for item in reports if isinstance(item, c.WorkAlignmentValidationReport)]
            if isinstance(actual, local.LocalActualTranscriptDocumentV1) and isinstance(actual.alignment, c.AlignmentRevisionV03):
                if not self._registered_initial_alignment(lease, preparation_id):
                    # ADR0082: the local whisper estimate method has no CTC
                    # lineage and must not be required to fabricate a CTC work
                    # report. Its own evidence is validated by the local V03
                    # branch (policy/qualification/benchmark evidence +
                    # not_measured AlignmentRevisionV03).
                    return None
                if len(matched) != 1:
                    raise EngineError('work_evidence_material_missing', 'Local verified CTC requires exactly one actual work report.', 422)
                report = matched[0]
            else:
                return None
        if not isinstance(actual, (c.ActualTranscriptDocumentV03, local.LocalActualTranscriptDocumentV1)) or not isinstance(report, c.WorkAlignmentValidationReport):
            return None
        source = self.registered_ctc_work_source(lease, preparation_id, actual, report)
        if source is not None:
            self._validate_work_runtime(lease, preparation_id, actual, report, manifest.audio_mappings)
        return source

    def expected_initial_alignment_methods(self, lease, preparation_id, assembly):
        """Exactly original methods plus one authenticated actual initial CTC."""
        with self.engine.db.connect_readonly() as connection:
            self.engine._lease(connection, lease)
            saved = connection.execute('SELECT value FROM metadata WHERE key=?', (INITIAL_PREFIX + preparation_id,)).fetchone()
        if saved is None:
            return assembly.methods
        method = self.registered_initial_alignment_method(lease, preparation_id)
        if any(value.method_id == method.method_id for value in assembly.methods):
            raise EngineError('alignment_method_conflict', 'Pre-CTC source cannot already claim the later operation', 422)
        return (*assembly.methods, method)

    def assert_initial_alignment_manifest(self, lease, preparation_id, manifest):
        """Shared final-reader/verifier gate tied to exact original JSON output."""
        from video_creator.application.bundles import validate_text
        with self.engine.db.connect_readonly() as connection:
            row, _run, _production, _request = self._preparation(connection, lease, preparation_id)
            saved = connection.execute('SELECT value FROM metadata WHERE key=?', (INITIAL_PREFIX + preparation_id,)).fetchone()
            if saved is None:
                return None
            body, request, _raw = self._load_alignment(connection, lease, preparation_id, initial=True)
            operation = connection.execute('SELECT * FROM operations WHERE run_id=? AND step_key=?',
                (lease.run_id, body['descriptor']['step_key'])).fetchall()
            step = connection.execute('SELECT * FROM steps WHERE run_id=? AND step_key=?',
                (lease.run_id, body['descriptor']['step_key'])).fetchone()
            source = (saved[0], tuple((value['id'], value['observation_json'], value['status'], value['settled']) for value in operation),
                      dict(step) if step is not None else None)
        alignment, _file, _observation = self._read_alignment(lease, preparation_id, initial=True)
        context = self._read_final_assembly(row, request.binding)
        if context is None:
            raise EngineError('final_assembly_unavailable', 'Original immutable initial source assembly missing', 503)
        if manifest.methods != self.expected_initial_alignment_methods(lease, preparation_id, context):
            raise EngineError('alignment_method_conflict', 'Final methods must be original source plus exactly actual committed initial CTC', 422)
        prepared = self.recover_preparation(lease, preparation_id)
        artifact_id = context.document_artifact_ids['transcript']
        receipt = next((item for item in prepared.materials if item.artifact_id == artifact_id), None)
        if receipt is None:
            raise EngineError('alignment_result_missing', 'Actual first READY transcript must consume committed CTC', 409)
        document = validate_text(self.read_material(lease, preparation_id, receipt.material_id), receipt.schema_kind, receipt.media_type)
        if (not isinstance(document, (c.ActualTranscriptDocument, c.ActualTranscriptDocumentV03, local.LocalActualTranscriptDocumentV1))
                or document.transcript != request.transcript.transcript):
            raise EngineError('alignment_result_invalid', 'Final READY transcript/alignment differs from original successful CTC output', 422)
        _check_semantic(document.alignment)
        material_source = ()
        if document.alignment != alignment:
            # Only independent precision and its derived complete-record SHA
            # may differ. Every inference identity, boundary and method stays
            # equal to the authenticated original settled JSON output.
            if (type(document.alignment) is not type(alignment)
                    or not isinstance(document, (c.ActualTranscriptDocumentV03, local.LocalActualTranscriptDocumentV1))
                    or not isinstance(manifest, (c.BundleManifestV03, local.BundleManifestLocalV1))
                    or document.alignment.precision.status != 'measured'
                    or document.alignment.model_dump(mode='json', exclude={'precision', 'content_sha256'})
                    != alignment.model_dump(mode='json', exclude={'precision', 'content_sha256'})):
                raise EngineError('alignment_result_invalid', 'Only independently verified precision may derive from original CTC', 422)
            documents, material_source = self._initial_precision_materials(lease, preparation_id, manifest, prepared)
            if documents.get('Text/actual-transcript.json') != document:
                raise EngineError('alignment_result_invalid', 'Measured alignment requires the same actual indexed READY transcript', 422)
            with self.engine.db.connect_readonly() as connection:
                _row, _run, _production, production_request = self._preparation(connection, lease, preparation_id)
            # Use the existing complete local qualification, independent
            # reference/report mathematics and source-authority gates intact.
            if isinstance(manifest, local.BundleManifestLocalV1):
                quality = documents.get('Checks/quality-report.json')
                if not isinstance(quality, local.LocalBundleQualityEvidenceV1):
                    raise EngineError('local_quality_missing', 'Derived local precision requires actual typed QC.', 422)
                self._verify_local_v03_reports(lease, preparation_id, manifest, documents, production_request, document, quality)
            else:
                self._verify_v03_documents(lease, manifest, documents, production_request)
        return (*source, material_source)

    def _initial_precision_materials(self, lease, preparation_id, manifest, prepared):
        from video_creator.application.bundles import validate_text
        receipts = {item.material_id: item for item in prepared.materials}
        documents = {}
        with self.engine.db.connect_readonly() as connection:
            self.engine._lease(connection, lease)
            rows = connection.execute('SELECT material_id,artifact_id,relative_path,sha256,size,media_type,schema_kind,status FROM bundle_items WHERE preparation_id=? AND material_id IS NOT NULL ORDER BY material_id',
                (preparation_id,)).fetchall()
        snapshot = tuple(tuple(row) for row in rows)
        actual_rows = {row['material_id']: row for row in rows}
        for artifact in manifest.artifacts:
            if artifact.material_id is None:
                continue
            receipt = receipts.get(artifact.material_id)
            current = actual_rows.get(artifact.material_id)
            if (receipt is None or current is None or current['status'] != 'ready'
                    or (current['artifact_id'], current['relative_path'], current['sha256'], current['size'], current['media_type'])
                    != (artifact.artifact_id, artifact.relative_path, artifact.sha256, artifact.size, artifact.media_type)
                    or (receipt.artifact_id, receipt.sha256, receipt.size, receipt.media_type, receipt.schema_kind)
                    != (current['artifact_id'], current['sha256'], current['size'], current['media_type'], current['schema_kind'])):
                raise EngineError('alignment_result_invalid', 'Independent precision requires exact original READY material identities', 422)
            raw = self.read_material(lease, preparation_id, receipt.material_id)
            if len(raw) != artifact.size or hashlib.sha256(raw).hexdigest() != artifact.sha256:
                raise EngineError('alignment_result_invalid', 'Independent precision original READY bytes changed', 422)
            documents[artifact.relative_path] = validate_text(raw, receipt.schema_kind, receipt.media_type)
        return documents, snapshot

    @staticmethod
    def assert_initial_alignment_manifest_writer(connection, lease, preparation_id, expected):
        saved = connection.execute('SELECT value FROM metadata WHERE key=?', (INITIAL_PREFIX + preparation_id,)).fetchone()
        if expected is None:
            if saved is not None:
                raise EngineError('alignment_source_changed', 'Original initial source appeared after verification', 409)
            return
        from video_creator.application.bundles import strict_json
        if saved is None or saved[0] != expected[0]:
            raise EngineError('alignment_source_changed', 'Original initial registration changed before publication', 409)
        body = strict_json(saved[0].encode('utf-8'))
        operations = tuple((value['id'], value['observation_json'], value['status'], value['settled'])
            for value in connection.execute('SELECT * FROM operations WHERE run_id=? AND step_key=?',
                (lease.run_id, body['descriptor']['step_key'])))
        step = connection.execute('SELECT * FROM steps WHERE run_id=? AND step_key=?',
            (lease.run_id, body['descriptor']['step_key'])).fetchone()
        if operations != expected[1] or (dict(step) if step is not None else None) != expected[2]:
            raise EngineError('alignment_source_changed', 'Original settled operation/committed Step changed before publication', 409)
        if expected[3]:
            materials = tuple(tuple(row) for row in connection.execute(
                'SELECT material_id,artifact_id,relative_path,sha256,size,media_type,schema_kind,status FROM bundle_items WHERE preparation_id=? AND material_id IS NOT NULL ORDER BY material_id',
                (preparation_id,)))
            if materials != expected[3]:
                raise EngineError('alignment_source_changed', 'Original independently verified precision materials changed at writer boundary', 409)

    def assert_alignment_writer(self, connection, lease, locator, *, initial, guard=None, execution=None):
        """Pure retained identity and same-connection source checks at each writer."""
        from video_creator.application.bundles import strict_json
        from video_creator.application.current_production_blockers import bound_context
        self.engine._lease(connection, lease)
        held = self._affected_services_writer(lease)
        runtime = self._production_services_runtime
        run, production, request, binding = bound_context(self.engine, connection, lease.run_id, runtime.sha256)
        body, payload, _raw = self._load_alignment(connection, lease, locator, initial=initial)
        preparation_id = payload.preparation_id if initial else payload.parent_preparation_id
        row, _run, _production, _request = self._preparation(connection, lease, preparation_id)
        if payload.binding != binding or (payload.preparation_intent_sha256 if initial else payload.parent_intent_sha256) != digest(row['intent_json']):
            raise EngineError('alignment_source_changed', 'Original preparation/request identity changed', 409)
        if (payload.alignment_registration.resource_manifest_sha256, payload.alignment_registration.runtime_manifest_sha256) != held[6:8]:
            raise EngineError('alignment_source_changed', 'Actual retained installed resource identity changed', 409)
        registration = getattr(runtime.config, 'alignment_registration', None)
        if registration != payload.alignment_registration.registration:
            raise EngineError('alignment_resource_changed', 'Actual registered algorithm changed', 409)
        route = connection.execute('SELECT body FROM routes WHERE id=?', (body['descriptor']['route_id'],)).fetchone()
        if route is None or digest(route['body']) != payload.alignment_registration.route_sha256:
            raise EngineError('alignment_resource_changed', 'Actual registered alignment route changed', 409)
        ref = request.delivery_requirements.evidence_policy_revision_ref if isinstance(request, c.ProductionRequestV03) and request.delivery_requirements else None
        if ref is None:
            raise EngineError('alignment_resource_not_ready', 'Original concrete evidence policy required', 503)
        resolved = self.engine.evidence_registry.resolve(production['owner'], production['project_id'], ref, connection=connection)
        if resolved.qualification != registration.method_qualification_ref:
            raise EngineError('alignment_resource_changed', 'Actual current method qualification changed', 409)
        assembly = connection.execute('SELECT value FROM metadata WHERE key=?', ('current_final_assembly:' + preparation_id,)).fetchone()
        if assembly is None:
            raise EngineError('final_assembly_unavailable', 'Original saved preparation assembly required', 503)
        assembly_binding = strict_json(assembly[0].encode('utf-8'))
        if (assembly_binding.get('binding') != binding.model_dump(mode='json')
                or assembly_binding.get('ref', {}).get('content_sha256') != body['assembly_context_sha256']):
            raise EngineError('alignment_source_changed', 'Original immutable assembly association changed', 409)
        original_asr = self.engine._operation(connection, run, payload.transcript.asr_source.operation_id)
        if (original_asr['status'] != 'succeeded' or not original_asr['settled']
                or original_asr['input_sha256'] != payload.transcript.asr_source.input_sha256
                or digest(original_asr['route_json']) != payload.transcript.asr_source.route_sha256):
            raise EngineError('reconciliation_required', 'Original successful settled ASR source required', 409, 'reconcile')
        from video_creator.application.asr_validation_context import CONTEXT_PREFIX
        context_row = connection.execute('SELECT value FROM metadata WHERE key=?',
            (CONTEXT_PREFIX + original_asr['id'],)).fetchone()
        if context_row is None:
            raise EngineError('asr_recovery_validation_unavailable', 'Original ASR context association missing', 503)
        context_body = strict_json(context_row[0].encode('utf-8'))
        if context_body.get('ref') != payload.transcript.asr_source.context_ref.model_dump(mode='json'):
            raise EngineError('alignment_source_changed', 'Original complete ASR context binding changed', 409)
        staged_asr = connection.execute('SELECT sha256,status FROM staging WHERE id=?',
            (payload.transcript.asr_source.staging_id,)).fetchone()
        if staged_asr is None or staged_asr['status'] not in {'ready', 'imported'} or staged_asr['sha256'] != payload.transcript.asr_source.result_file_sha256:
            raise EngineError('alignment_source_changed', 'Original settled ASR result allocation changed', 409)
        audio = connection.execute('SELECT sha256,size,media_type FROM assets WHERE id=? AND owner=?',
            (payload.audio.asset_id, production['owner'])).fetchone()
        if audio is None or tuple(audio) != (payload.audio.sha256, payload.audio.size, payload.audio.media_type):
            raise EngineError('alignment_source_changed', 'Original mixed audio record changed', 409)
        if not initial:
            from video_creator.application.affected_repair_service import COMMAND_PREFIX
            saved = connection.execute('SELECT value FROM metadata WHERE key=?', (COMMAND_PREFIX + locator,)).fetchone()
            if saved is None:
                raise EngineError('alignment_binding_invalid', 'Original main command missing', 422)
            command = strict_json(saved[0].encode('utf-8'))
            expected = {key: value for key, value in body['descriptor'].items() if key != 'step_key'}
            if (command.get('requested_action') != 'realignment' or command.get('changed_media_roles')
                    or command.get('steps') != {body['descriptor']['step_key']: expected}
                    or command.get('source_report_ref') != payload.source_report_ref.model_dump(mode='json')
                    or tuple(command.get('failed_unit_ids', ())) != payload.failed_unit_ids):
                raise EngineError('alignment_binding_invalid', 'Original exact one-Step realignment command required', 422)
            source = {key: value for key, value in command.items() if key not in {
                'repair_command_sha256', 'source_sha256', 'steps', 'child_preparation_id', 'child_intent_sha256', 'child_asr'}}
            if digest(canonical_body(source)) != locator:
                raise EngineError('alignment_binding_invalid', 'Original main command SHA changed', 422)
            if execution is not None:
                self._affected_execution(connection, lease, execution)
            from video_creator.application.current_final_evidence_journal import (
                PREFIX,
                parse_journal,
            )
            stored = connection.execute('SELECT value FROM metadata WHERE key=?', (PREFIX + lease.run_id,)).fetchone()
            journal = parse_journal(stored[0], now=self.engine.clock()) if stored else None
            if (journal is None or journal.binding != binding or journal.control.phase != 'executing'
                    or journal.control.resume_mode != 'repair' or journal.control.execution_fence != lease.fencing_token
                    or journal.snapshot.preparation_id not in {preparation_id, command.get('child_preparation_id')}):
                raise EngineError('final_evidence_claim_required', 'Actual same-fence realignment continuation required', 409)
            creative_refs = (command['plan_ref'], command['quality_ref'])
        else:
            creative_refs = self._initial_alignment_refs(connection, lease, preparation_id)
        issuer = self._production_authorization.issuer()
        if guard is not None:
            issuer._guard(connection, guard)
            issuer._request(connection, production, run, guard.identity)
        for ref, action in zip(creative_refs, ('execute_plan', 'continue_bundle_validation'), strict=True):
            revision = connection.execute('SELECT body,content_sha256 FROM creative_revisions WHERE id=? AND run_id=?',
                (ref['revision_id'], lease.run_id)).fetchone()
            if revision is None or revision['content_sha256'] != ref['content_sha256'] or digest(revision['body']) != ref['content_sha256']:
                raise EngineError('alignment_source_changed', 'Original plan/quality source changed', 409)
            if held[5]:
                if guard is None:
                    record = issuer._record(connection, issuer._current_binding(connection, production, run).policy_ref,
                        self.engine._authorization_identity(production['owner']), request, production, action=action)
                else:
                    _request, record = issuer._bound(connection, guard, production, run, action=action)
                fact = issuer._earlier_action(connection, production, run, record, lease, action)
                if (fact.target_id, fact.target_sha256) != (ref['revision_id'], ref['content_sha256']):
                    raise EngineError('alignment_execution_denied', 'Actual whole source production admission required', 403)
                admitted_route = next((value for value in record.policy.routes if value.route_id == body['descriptor']['route_id']), None)
                if admitted_route is None or admitted_route.route_sha256 != payload.alignment_registration.route_sha256:
                    raise EngineError('alignment_execution_denied', 'Actual policy alignment route scope required', 403)
            else:
                approvals = []
                for decision_row in connection.execute('SELECT * FROM decisions WHERE run_id=?', (lease.run_id,)):
                    decision = c.ReviewDecision.model_validate(strict_json(decision_row['body'].encode('utf-8')))
                    if decision.target_revision_id == ref['revision_id']:
                        if digest(decision_row['body']) != decision_row['request_sha256'] or decision_row['result_json'] != decision_row['body']:
                            raise EngineError('production_review_invalid', 'Actual original approval changed', 422)
                        approvals.append(decision)
                if len(approvals) != 1 or approvals[0].action != 'approve':
                    raise EngineError('alignment_execution_denied', 'Actual original whole plan/quality human approval required', 403)
        if not held[5]:
            declaration = held[1].declaration
            now = self.engine.clock()
            if (declaration.declaring_subject != production['owner'] or production['project_id'] not in declaration.project_ids
                    or declaration.expires_at_us is not None and declaration.expires_at_us <= now
                    or any(right.valid_from_us is not None and right.valid_from_us > now
                        or right.expires_at_us is not None and right.expires_at_us <= now for right in declaration.rights)):
                raise EngineError('production_rights_expired', 'Original human production rights expired', 403)
        if guard is not None:
            issuer._guard(connection, guard)
        return body, payload

    def _initial_alignment_refs(self, connection, lease, preparation_id):
        from video_creator.application.bundles import strict_json
        saved = connection.execute('SELECT value FROM metadata WHERE key=?', ('current_initial_alignment_sources:' + preparation_id,)).fetchone()
        if saved is None:
            raise EngineError('alignment_source_unavailable', 'Original immutable initial plan/source association required', 503)
        body = strict_json(saved[0].encode('utf-8'))
        if set(body) != {'plan_ref', 'quality_ref'}:
            raise EngineError('alignment_binding_invalid', 'Closed original initial creative source binding required', 422)
        return body['plan_ref'], body['quality_ref']

    def register_initial_alignment(self, lease, preparation_id, *, transcript, prediction, mapping):
        self._affected_services(lease)
        row, _production, _request, binding, _prepared, _intent, items = self._final_prepared(lease, preparation_id)
        if any(item['status'] == 'ready' and item['relative_path'] in {
                'Text/actual-transcript.json', 'Text/subtitles.srt', 'Text/subtitles.vtt',
                'Semantics/semantic-segments.jsonl', 'Semantics/rag-chunks.jsonl'} for item in items):
            with self.engine.db.connect_readonly() as connection:
                saved = connection.execute('SELECT value FROM metadata WHERE key=?', (INITIAL_PREFIX + preparation_id,)).fetchone()
            if saved is None:
                raise EngineError('initial_alignment_source_denied', 'Old READY estimated documents cannot be replaced or relabelled CTC', 403)
            body, payload, _raw = self._alignment_preflight(lease, preparation_id, initial=True)
            if (payload.transcript.transcript, payload.audio.mapping, body['source_prediction']) != (
                    transcript, mapping, prediction.model_dump(mode='json')):
                raise EngineError('initial_alignment_conflict', 'Replay cannot replace original initial source', 409)
            return self._alignment_intent(body)
        context = self._read_final_assembly(row, binding)
        if context is None:
            raise EngineError('final_assembly_unavailable', 'Persist original same-preparation assembly before initial registration', 503)
        audio, asr, units = self._alignment_sources(lease, preparation_id, context, transcript, prediction, mapping, initial=True)
        registration = self._alignment_registration(lease, transcript, prediction)
        held = self._affected_services(lease)
        self._production_services_runtime._current_final_execution_facts(lease, held[1], held[5])
        with self.engine.db.connect_readonly() as connection:
            prior = connection.execute('SELECT value FROM metadata WHERE key=?', (INITIAL_PREFIX + preparation_id,)).fetchone()
            existing = self._load_alignment(connection, lease, preparation_id, initial=True)[1] if prior else None
        output_id = existing.output_alignment_revision_id if existing else identity('alignment')
        payload = InitialAlignmentRequest(format='registered-initial-alignment-request-v1', binding=binding,
            preparation_id=preparation_id, preparation_intent_sha256=digest(row['intent_json']),
            assembly_context_sha256=digest(canonical(context) + '\n'), asr_source=asr, audio=audio,
            transcript=AlignmentTranscriptSource(transcript=transcript,
                approved_script_revision_ref=transcript.approved_script_revision_ref, asr_source=asr),
            unit_sources=units, allowed_unit_ids=tuple(unit.transcript_unit_id for unit in units),
            source_alignment_revision_id=prediction.alignment_revision_id, source_alignment_content_sha256=prediction.content_sha256,
            alignment_registration=registration, output_alignment_revision_id=output_id)
        body = self._alignment_companion(payload, prediction, payload.assembly_context_sha256)
        refs = {ref.kind: ref for ref in (*context.creative_revision_refs, context.quality_ref)}
        if not {'plan', 'quality'} <= set(refs):
            raise EngineError('alignment_source_invalid', 'Original saved plan and quality source required', 422)
        creative = canonical_body({'plan_ref': refs['plan'], 'quality_ref': refs['quality']})
        issuer = self._production_authorization.issuer()
        with issuer.current_guard(self._production_authorization.registered(lease)) as guard, self.engine.db.transaction() as connection:
            current, run, _production, _request = self._preparation(connection, lease, preparation_id)
            issuer._guard(connection, guard)
            if current['intent_json'] != row['intent_json'] or self._final_binding(lease, connection) != binding:
                raise EngineError('initial_alignment_conflict', 'Original same preparation/source changed', 409)
            exists = connection.execute('SELECT value FROM metadata WHERE key=?', (INITIAL_PREFIX + preparation_id,)).fetchone()
            if exists is None:
                final_ready = connection.execute("SELECT 1 FROM bundle_items WHERE preparation_id=? AND status='ready' AND relative_path IN (?,?,?,?,?)",
                    (preparation_id, 'Text/actual-transcript.json', 'Text/subtitles.srt', 'Text/subtitles.vtt',
                     'Semantics/semantic-segments.jsonl', 'Semantics/rag-chunks.jsonl')).fetchone()
                if final_ready is not None:
                    raise EngineError('initial_alignment_source_denied', 'First CTC registration cannot follow final speech READY', 403)
            for key, text in ((INITIAL_PREFIX + preparation_id, canonical_body(body)),
                    ('current_initial_alignment_sources:' + preparation_id, creative)):
                old = connection.execute('SELECT value FROM metadata WHERE key=?', (key,)).fetchone()
                if old is not None and old[0] != text:
                    raise EngineError('initial_alignment_conflict', 'Original initial input and IDs are immutable', 409)
                if old is None:
                    connection.execute('INSERT INTO metadata(key,value) VALUES(?,?)', (key, text))
            self.assert_alignment_writer(connection, lease, preparation_id, initial=True, guard=guard)
            self.engine._event(connection, run, 'production.initial_alignment_registered', body['request_sha256'])
            self.assert_alignment_writer(connection, lease, preparation_id, initial=True, guard=guard)
        return self._alignment_intent(body)

    def prepare_affected_alignment(self, lease, parent, source, command_sha):
        from video_creator.application.bundles import validate_text
        if parent.assembly is None or parent.asr is None:
            raise EngineError('alignment_source_unavailable', 'Original parent assembly and actual ASR context required', 503)
        role = parent.assembly.document_artifact_ids['transcript']
        original = next(((receipt, raw) for receipt, raw in parent.materials if receipt.artifact_id == role), None)
        if original is None:
            raise EngineError('alignment_source_unavailable', 'Original complete READY transcript required', 503)
        receipt, raw = original
        document = validate_text(raw, receipt.schema_kind, receipt.media_type)
        if not isinstance(document, (c.ActualTranscriptDocument, c.ActualTranscriptDocumentV03)):
            raise EngineError('alignment_source_invalid', 'Original actual transcript schema required', 422)
        prediction, transcript = document.alignment, document.transcript
        audio, asr, units = self._alignment_sources(lease, parent.preparation.preparation_id, parent.assembly,
            transcript, prediction, parent.assembly.audio_mappings[0], initial=False)
        registration = self._alignment_registration(lease, transcript, prediction)
        with self.engine.db.connect_readonly() as connection:
            saved = connection.execute('SELECT value FROM metadata WHERE key=?', (AFFECTED_PREFIX + command_sha,)).fetchone()
            existing = self._load_alignment(connection, lease, command_sha, initial=False)[1] if saved else None
        output_id = existing.output_alignment_revision_id if existing else identity('alignment')
        failed = tuple(source['failed_unit_ids'])
        # Exact failed units are the minimal boundary consistency closure. No
        # reference/gold ranges or report body are delivered to inference.
        allowed = tuple(unit.transcript_unit_id for unit in units if unit.transcript_unit_id in failed)
        payload = AffectedAlignmentRequest(format='registered-affected-alignment-request-v1', binding=parent.binding,
            repair_command_sha256=command_sha, parent_preparation_id=parent.preparation.preparation_id,
            parent_intent_sha256=digest(canonical(parent.intent)), source_report_ref=source['source_report_ref'],
            audio=audio, transcript=ReadyAlignmentTranscriptSource(transcript=transcript,
                approved_script_revision_ref=transcript.approved_script_revision_ref, asr_source=asr,
                ready_receipt=receipt, ready_file_sha256=hashlib.sha256(raw).hexdigest()),
            unit_sources=units, failed_unit_ids=failed, allowed_unit_ids=allowed,
            source_alignment_revision_id=prediction.alignment_revision_id, source_alignment_content_sha256=prediction.content_sha256,
            alignment_registration=registration, output_alignment_revision_id=output_id)
        body = self._alignment_companion(payload, prediction, digest(canonical(parent.assembly) + '\n'))
        descriptor = body['descriptor']
        return body, {descriptor['step_key']: {key: value for key, value in descriptor.items() if key != 'step_key'}}

    def persist_affected_alignment_writer(self, connection, lease, command_sha, companion):
        from video_creator.application.affected_repair_service import COMMAND_PREFIX
        from video_creator.application.bundles import strict_json
        key = AFFECTED_PREFIX + command_sha
        current = connection.execute('SELECT value FROM metadata WHERE key=?', (COMMAND_PREFIX + command_sha,)).fetchone()
        if current is None:
            raise EngineError('alignment_binding_invalid', 'Original main command must commit atomically', 422)
        command = strict_json(current[0].encode('utf-8'))
        old = connection.execute('SELECT value FROM metadata WHERE key=?', (key,)).fetchone()
        text = canonical_body(companion)
        if old is not None and old[0] != text:
            raise EngineError('alignment_registration_conflict', 'Original alignment companion is immutable', 409)
        if old is None:
            if command.get('child_preparation_id') is not None:
                raise EngineError('alignment_registration_conflict', 'Cannot attach new inference to an existing child', 409)
            descriptor = companion['descriptor']
            if (connection.execute('SELECT 1 FROM operations WHERE run_id=? AND step_key=?', (lease.run_id, descriptor['step_key'])).fetchone()
                    or connection.execute('SELECT 1 FROM generated_attempts WHERE run_id=? AND step_key=?', (lease.run_id, descriptor['step_key'])).fetchone()
                    or connection.execute('SELECT 1 FROM steps WHERE run_id=? AND step_key=?', (lease.run_id, descriptor['step_key'])).fetchone()):
                raise EngineError('alignment_registration_conflict', 'Legacy unregistered effects cannot be adopted', 409, 'reconcile')
            connection.execute('INSERT INTO metadata(key,value) VALUES(?,?)', (key, text))

    def _alignment_result_facts(self, lease, locator, *, initial, execution=None, files=None):
        body, request, _raw = self._alignment_preflight(lease, locator, initial=initial, execution=execution)
        return self._alignment_result_payload(lease, locator, body, request, initial=initial, files=files)

    def _alignment_result_payload(self, lease, locator, body, request, *, initial, files=None):
        """Exact result checks shared after distinct execution or committed-read guards."""
        from video_creator.application.bundles import strict_json
        descriptor = body['descriptor']
        with self.engine.db.connect_readonly() as connection:
            self.engine._lease(connection, lease)
            operations = connection.execute('SELECT * FROM operations WHERE run_id=? AND step_key=?', (lease.run_id, descriptor['step_key'])).fetchall()
            if len(operations) != 1:
                raise EngineError('alignment_result_missing', 'Exactly original alignment Operation required', 409, 'reconcile')
            operation = dict(operations[0])
            if operation['status'] != 'succeeded' or not operation['settled']:
                raise EngineError('reconciliation_required', 'Actual successful settled alignment Operation required', 409, 'reconcile')
            observation = c.OperationObservation.model_validate_json(operation['observation_json'])
            if (operation['input_sha256'], operation['dedupe_key'], digest(operation['route_json'])) != (
                    descriptor['input_sha256'], descriptor['dedupe_key'], request.alignment_registration.route_sha256):
                raise EngineError('alignment_result_invalid', 'Original settled operation input/route/dedupe differs', 422)
            manifests = observation.result_json.get('generated_files') if isinstance(observation.result_json, dict) else None
            if not isinstance(manifests, list) or len(manifests) != 1:
                raise EngineError('alignment_result_invalid', 'Exactly actual generated JSON manifest required', 422)
            manifest = GeneratedFileManifest.model_validate(manifests[0])
            if files is not None and (type(files) is not tuple or files != (manifest,)):
                raise EngineError('alignment_result_invalid', 'Caller manifest differs from original settled Operation', 422)
            allocated = self._production_services_runtime.worker._generated(connection, lease, manifest.attempt_id)
            if (allocated['step_key'], allocated['input_sha256'], allocated['output_key'], allocated['media_type'], allocated['status']) != (
                    descriptor['step_key'], descriptor['input_sha256'], 'alignment-result', 'application/json', 'ready'):
                raise EngineError('alignment_result_invalid', 'Original one JSON allocation required, never a media Asset', 422)
            candidate = manifest.candidate
            if (candidate.staging_id, candidate.sha256, candidate.size, candidate.media_type, candidate.source, candidate.rights) != (
                    allocated['staging_id'], allocated['sha256'], allocated['size'], allocated['media_type'], allocated['source'], allocated['rights']):
                raise EngineError('alignment_result_invalid', 'Original actual full-file receipt differs', 422)
            allocation = dict(allocated)
        path = self.assets._path('Staging', candidate.staging_id)
        if not path.is_file() or path.stat().st_size > MAX_JSON_BYTES:
            raise EngineError('alignment_result_missing', 'Bounded actual completed allocated JSON missing', 503)
        before = path.stat()
        raw = path.read_bytes()
        after = path.stat()
        signature = (after.st_size, after.st_mtime_ns, after.st_ctime_ns, after.st_ino)
        if signature != (before.st_size, before.st_mtime_ns, before.st_ctime_ns, before.st_ino):
            raise EngineError('alignment_result_changed', 'Original allocated JSON changed during controlled read', 409, 'reconcile')
        if (len(raw), hashlib.sha256(raw).hexdigest()) != (candidate.size, candidate.sha256):
            raise EngineError('alignment_result_invalid', 'Original completed alignment bytes changed', 422)
        prediction = self._alignment_prediction(body)
        try:
            alignment = type(prediction).model_validate(strict_json(raw))
        except (ValidationError, TypeError, ValueError):
            raise EngineError('alignment_result_invalid', 'Actual alignment document schema rejected', 422) from None
        _check_semantic(alignment)
        expected = request.transcript.transcript
        if (alignment.alignment_revision_id, alignment.actual_transcript_revision_id, alignment.transcript_content_sha256,
                alignment.input_audio_asset_id, alignment.input_audio_sha256, alignment.units, alignment.method_ref) != (
                request.output_alignment_revision_id, expected.transcript_revision_id, expected.content_sha256,
                expected.input_audio_asset_id, expected.input_audio_sha256, prediction.units,
                request.alignment_registration.registration.method_qualification_ref.execution_identity.method_id):
            raise EngineError('alignment_result_invalid', 'Original alignment identity/transcript/audio/method changed', 422)
        if alignment.precision.status != 'not_measured' or alignment.precision.p95_error_us is not None:
            raise EngineError('alignment_result_invalid', 'Inference cannot claim independent measured precision', 422)
        if len(alignment.boundaries) != len(prediction.boundaries):
            raise EngineError('alignment_result_invalid', 'Original complete unit sequence required', 422)
        allowed = set(request.allowed_unit_ids)
        for unit, original in zip(alignment.boundaries, prediction.boundaries, strict=True):
            if (unit.unit_id, unit.transcript_unit_id) != (original.unit_id, original.transcript_unit_id):
                raise EngineError('alignment_result_invalid', 'Original unit IDs/order changed', 422)
            if unit.intrinsic_range.end_us > expected.duration_us or (unit.transcript_unit_id not in allowed and unit != original):
                raise EngineError('alignment_result_invalid', 'Unit outside permitted audio/subset changed', 422)
        result = observation.result_json
        if (result.get('request_sha256') != body['request_sha256']
                or result.get('execution_identity') != request.alignment_registration.registration.method_qualification_ref.execution_identity.model_dump(mode='json')
                or (result.get('preparation_id') != locator if initial else result.get('repair_command_sha256') != locator)):
            raise EngineError('alignment_result_invalid', 'Original request and actual runtime method execution facts required', 422)
        return body, request, alignment, manifest, observation, operation, allocation, signature

    def _commit_alignment(self, lease, locator, *, files, initial, execution=None):
        facts = self._alignment_result_facts(lease, locator, initial=initial, execution=execution, files=files)
        body, _request, alignment, manifest, _observation, operation, allocation, signature = facts
        result = {'request_sha256': body['request_sha256'], 'generated_files': [manifest.model_dump(mode='json')],
            'alignment_content_sha256': alignment.content_sha256, 'operation_id': operation['id']}
        issuer = self._production_authorization.issuer()
        with issuer.current_guard(self._production_authorization.registered(lease)) as guard, self.engine.db.transaction() as connection:
            self.assert_alignment_writer(connection, lease, locator, initial=initial, guard=guard, execution=execution)
            run = self.engine._lease(connection, lease)
            current = dict(self.engine._operation(connection, run, operation['id']))
            actual = dict(self._production_services_runtime.worker._generated(connection, lease, manifest.attempt_id))
            if current != operation or actual != allocation:
                raise EngineError('alignment_result_changed', 'Actual settled operation/allocation changed before commit', 409)
            stat = self.assets._path('Staging', manifest.candidate.staging_id).stat()
            if (stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns, stat.st_ino) != signature:
                raise EngineError('alignment_result_changed', 'Original allocated JSON changed before Step commit', 409, 'reconcile')
            self.engine._complete_step(connection, lease, body['descriptor']['step_key'], (), result)
            self.assert_alignment_writer(connection, lease, locator, initial=initial, guard=guard, execution=execution)
        return alignment

    def _read_alignment(self, lease, locator, *, initial, execution=None):
        facts = self._alignment_result_facts(lease, locator, initial=initial, execution=execution)
        return self._read_committed_alignment_facts(lease, facts)

    def _read_committed_alignment_facts(self, lease, facts):
        body, _request, alignment, manifest, observation, operation, _allocation, signature = facts
        with self.engine.db.connect_readonly() as connection:
            self.engine._lease(connection, lease)
            step = connection.execute('SELECT * FROM steps WHERE run_id=? AND step_key=?', (lease.run_id, body['descriptor']['step_key'])).fetchone()
            if step is None or step['status'] != 'succeeded':
                raise EngineError('alignment_step_commit_required', 'Settled alignment must commit original Step without repeating inference', 409)
            from video_creator.application.bundles import strict_json
            saved = strict_json(step['result_json'].encode('utf-8'))
            expected = {'request_sha256': body['request_sha256'], 'generated_files': [manifest.model_dump(mode='json')],
                'alignment_content_sha256': alignment.content_sha256, 'operation_id': operation['id']}
            if saved != {'asset_ids': [], 'result': expected} or step['input_sha256'] != body['request_sha256']:
                raise EngineError('alignment_result_invalid', 'Original successful Step differs from actual settled JSON result', 422)
        stat = self.assets._path('Staging', manifest.candidate.staging_id).stat()
        if (stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns, stat.st_ino) != signature:
            raise EngineError('alignment_result_changed', 'Original allocated JSON changed during successful Step read', 409, 'reconcile')
        return alignment, manifest, observation
