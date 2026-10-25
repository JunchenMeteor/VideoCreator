"""Original prepared ASR context, committed before dispatch and read without effects."""

import hashlib
import json
import os
from contextlib import contextmanager
from pathlib import Path

from pydantic import ValidationError

from video_creator.application.engine import canonical, digest
from video_creator.application.affected_repair_service import canonical_body
from video_creator.domain import contracts as c
from video_creator.domain.current_final_evidence import AsrValidationContextRef, CurrentFinalAsrRead
from video_creator.domain.errors import EngineError
from video_creator.domain.registered_production import StoredAsrObservation

CONTEXT_PREFIX = 'asr_validation_context:'
CONTEXT_LIMIT = 2 * 1024 * 1024


class OriginalAsrValidationContext:
    @contextmanager
    def _original_context_guard(self, run_id):
        with self.engine.db.connect_readonly() as connection:
            run = self.engine._run(connection, run_id)
            owner = self.engine._production(connection, run['production_id'])['owner']
        issuer = self.engine.production_admissions
        if issuer is None:
            raise EngineError('asr_recovery_validation_unavailable', 'Actual installation issuer is not configured', 503)
        registered = self.engine._authorization_identity(owner)
        if registered.registration_sha256 != self.registration_sha256:
            raise EngineError('asr_original_context_source_changed', 'Original installed registration changed', 503)
        with issuer.current_guard(registered) as guard:
            state = self._original_context_guard_state
            previous = getattr(state, 'guard', None)
            state.guard = guard
            try:
                yield
            finally:
                state.guard = previous

    def _context_source(self):
        """Original registered package coverage plus current installation, not caller hashes."""
        from video_creator.providers import local_asr
        package = Path(local_asr.__file__).parents[1]
        expected = self.original_source_sha256
        for leaf in ('providers/local_asr.py', 'media/asr_worker.py'):
            path = package / leaf
            if (not expected or leaf not in expected or path.is_symlink() or not path.is_file()
                    or hashlib.sha256(path.read_bytes()).hexdigest() != expected[leaf]):
                raise EngineError('asr_recovery_validation_unavailable', 'Original installed validator source unavailable', 503)
        return local_asr, expected['providers/local_asr.py'], expected['media/asr_worker.py']

    def _context_current(self, connection, run):
        binding, binding_sha = self._binding(connection, run)
        production = self.engine._production(connection, run['production_id'])
        request = c.parse_production_request(production['request_json'])
        guard = getattr(self._original_context_guard_state, 'guard', None)
        if guard is None:
            raise EngineError('asr_recovery_validation_unavailable', 'Actual held installation guard required', 503)
        issuer = self.engine.production_admissions
        registered, _revision = issuer._guard(connection, guard)
        if registered.registration_sha256 != self.registration_sha256:
            raise EngineError('asr_original_context_source_changed', 'Actual current registration changed', 503)
        issuer._request(connection, production, run, registered)
        self.engine._evidence_execution_guard(connection, production, request)
        return binding, binding_sha

    def _parse_original_context(self, raw):
        from video_creator.application.bundles import strict_json
        if type(raw) is not bytes or not 0 < len(raw) <= CONTEXT_LIMIT:
            raise EngineError('asr_original_context_invalid', 'Bounded original request bytes required', 422)
        body = strict_json(raw)
        required = {'audio_path', 'storage_root', 'model_dir', 'model_revision', 'audio_sha256',
                    'video_audio_offset_us', 'max_audio_duration_us', 'model_file_sha256'}
        resource = {'require_execution_identity', 'resource_manifest_path', 'resource_manifest_sha256'}
        if (type(body) is not dict or set(body) != {'format', 'provider_sha256', 'worker_sha256', 'request'}
                or body['format'] != 'local-asr-original-validation-context-v1'
                or type(body['request']) is not dict or set(body['request']) != required | resource
                or type(body['request']['model_file_sha256']) is not dict
                or body['request']['require_execution_identity'] is not True
                or canonical_body(body).encode('utf-8') != raw):
            raise EngineError('asr_original_context_invalid', 'Exact original canonical registered request required', 422)
        _module, provider, worker = self._context_source()
        if (body['provider_sha256'], body['worker_sha256'], body['request']['resource_manifest_sha256']) != (
                provider, worker, self.resource_manifest_sha256):
            raise EngineError('asr_original_context_source_changed', 'Original qualified request implementation changed', 503)
        return body

    def _context_path(self, context_sha256):
        return self.assets._path('AsrValidationContexts', 'context-' + context_sha256)

    def commit_original_validation_context(self, ordinary_lease, original_handle, original_driver):
        with self._original_context_guard(ordinary_lease.run_id):
            return self._commit_original_validation_context(ordinary_lease, original_handle, original_driver)

    def _commit_original_validation_context(self, ordinary_lease, original_handle, original_driver):
        module, _provider, _worker = self._context_source()
        if type(original_driver) is not module.LocalAsrDriver:
            raise EngineError('asr_original_driver_denied', 'Only the original registered concrete driver may save context', 403)
        raw = original_driver.validation_context_bytes()
        context = self._parse_original_context(raw)
        request = context['request']
        with self.engine.db.connect_readonly() as connection:
            run = self.engine._lease(connection, ordinary_lease)
            _binding, binding_sha = self._context_current(connection, run)
            operation = self._operation(connection, run, original_handle.allocation.operation_id)
            handle, _row = self._handle(connection, run, operation)
            production = self.engine._production(connection, run['production_id'])
            inputs = c.parse_production_request(production['request_json']).inputs.asset_ids
            allowed = set(inputs)
            for row in connection.execute("SELECT result_json FROM steps WHERE run_id=? AND status='succeeded'", (run['id'],)):
                allowed.update(json.loads(row[0]).get('asset_ids', []))
            assets = [self.assets.get(production['owner'], asset_id) for asset_id in allowed]
        if (handle != original_handle or operation['run_id'] != ordinary_lease.run_id
                or operation['production_id'] != production['id'] or operation['status'] != 'prepared' or operation['settled']
                or digest(json.dumps({'audio_sha256': request['audio_sha256'],
                    'resource_manifest_sha256': self.resource_manifest_sha256}, sort_keys=True)) != operation['input_sha256']):
            raise EngineError('asr_original_context_binding_invalid', 'Original undispatched Operation/handle/input required', 409)
        matches = [a for a in assets if a.sha256 == request['audio_sha256']
                   and str(self.assets.content_path(production['owner'], a.asset_id).resolve()) == request['audio_path']]
        if len(matches) != 1 or request['storage_root'] != str(self.engine.db.data_dir.resolve()):
            raise EngineError('asr_original_audio_denied', 'Original request must identify one scoped actual audio asset', 403)
        audio = matches[0]
        audio_path = self.assets.content_path(production['owner'], audio.asset_id)
        if (not audio.media_type.startswith('audio/') or audio_path.stat().st_size != audio.size
                or self.assets._hash(audio_path) != audio.sha256):
            raise EngineError('asr_original_audio_changed', 'Actual original audio bytes changed before context commit', 422)
        ref = AsrValidationContextRef(operation_id=operation['id'], run_id=run['id'],
            input_sha256=operation['input_sha256'], route_sha256=digest(operation['route_json']),
            binding_sha256=binding_sha, resource_manifest_sha256=self.resource_manifest_sha256,
            runtime_manifest_sha256=self.runtime_manifest_sha256, context_sha256=hashlib.sha256(raw).hexdigest(),
            size=len(raw), provider_sha256=context['provider_sha256'], worker_sha256=context['worker_sha256'])
        path = self._context_path(ref.context_sha256)
        path.parent.mkdir(exist_ok=True)
        if path.exists():
            if path.read_bytes() != raw:
                raise EngineError('asr_original_context_conflict', 'Original context bytes immutable', 409)
        else:
            partial = self.assets._path('AsrValidationContexts', 'context-' + ref.context_sha256 + '.partial')
            if partial.exists():
                if partial.read_bytes() != raw:
                    raise EngineError('asr_original_context_conflict', 'Interrupted context differs', 409)
            else:
                with partial.open('xb') as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
            os.link(partial, path)
            partial.unlink()
        key = CONTEXT_PREFIX + ref.operation_id
        with self.engine.db.transaction() as connection:
            current = self.engine._lease(connection, ordinary_lease)
            _binding, current_sha = self._context_current(connection, current)
            actual = self._operation(connection, current, ref.operation_id)
            current_handle, _row = self._handle(connection, current, actual)
            if (actual['status'] != 'prepared' or actual['settled'] or current_handle != original_handle
                    or current_sha != ref.binding_sha256 or actual['input_sha256'] != ref.input_sha256
                    or digest(actual['route_json']) != ref.route_sha256):
                raise EngineError('asr_original_context_binding_invalid', 'Original prepared writer binding changed', 409)
            old = connection.execute('SELECT value FROM metadata WHERE key=?', (key,)).fetchone()
            body = canonical_body({'format': 'asr-validation-context-binding-v1', 'ref': ref,
                              'authored_fence': ordinary_lease.fencing_token})
            if old:
                from video_creator.application.bundles import strict_json
                saved = strict_json(old[0].encode('utf-8'))
                if set(saved) != {'format', 'ref', 'authored_fence'} or saved['format'] != 'asr-validation-context-binding-v1' or saved['ref'] != ref.model_dump(mode='json'):
                    raise EngineError('asr_original_context_conflict', 'Operation already has a different original context', 409)
            else:
                connection.execute('INSERT INTO metadata(key,value) VALUES(?,?)', (key, body))
                self.engine._event(connection, current, 'asr.original_context_committed', ref.context_sha256)
            self._context_current(connection, current)
        return ref

    def _read_original_context(self, connection, run, operation):
        from video_creator.application.bundles import strict_json
        _binding, binding_sha = self._context_current(connection, run)
        row = connection.execute('SELECT value FROM metadata WHERE key=?', (CONTEXT_PREFIX + operation['id'],)).fetchone()
        if row is None:
            return None
        try:
            value = strict_json(row[0].encode('utf-8'))
            if set(value) != {'format', 'ref', 'authored_fence'} or value['format'] != 'asr-validation-context-binding-v1' or type(value['authored_fence']) is not int or value['authored_fence'] <= 0:
                raise ValueError('shape')
            ref = AsrValidationContextRef.model_validate(value['ref'])
        except (ValueError, TypeError, ValidationError):
            raise EngineError('asr_original_context_invalid', 'Original committed context grammar damaged', 422) from None
        if (ref.operation_id, ref.run_id, ref.input_sha256, ref.route_sha256, ref.binding_sha256,
                ref.resource_manifest_sha256, ref.runtime_manifest_sha256) != (operation['id'], run['id'],
                operation['input_sha256'], digest(operation['route_json']), binding_sha,
                self.resource_manifest_sha256, self.runtime_manifest_sha256):
            raise EngineError('asr_original_context_binding_invalid', 'Original committed context changed Operation', 422)
        path = self._context_path(ref.context_sha256)
        if not path.is_file():
            raise EngineError('asr_recovery_validation_unavailable', 'Committed original context file missing', 503)
        if path.stat().st_size != ref.size:
            raise EngineError('asr_original_context_invalid', 'Committed original context size changed', 422)
        raw = path.read_bytes()
        if len(raw) != ref.size or hashlib.sha256(raw).hexdigest() != ref.context_sha256:
            raise EngineError('asr_original_context_invalid', 'Committed original context bytes changed', 422)
        context = self._parse_original_context(raw)
        if (context['provider_sha256'], context['worker_sha256']) != (ref.provider_sha256, ref.worker_sha256):
            raise EngineError('asr_original_context_invalid', 'Original implementation commitments differ', 422)
        return ref, raw

    def read_settled_original_asr(self, ordinary_lease, operation_id):
        with self._original_context_guard(ordinary_lease.run_id):
            return self._read_settled_original_asr(ordinary_lease, operation_id)

    def _read_settled_original_asr(self, ordinary_lease, operation_id):
        with self.engine.db.connect_readonly() as connection:
            run = self.engine._lease(connection, ordinary_lease)
            operation = self._operation(connection, run, operation_id)
            if operation['run_id'] != run['id'] or operation['production_id'] != run['production_id']:
                raise EngineError('asr_result_scope_denied', 'Original ASR belongs to another Run', 403)
            if operation['status'] != 'succeeded' or not operation['settled']:
                raise EngineError('reconciliation_required', 'Original ASR is not succeeded and settled', 409, 'reconcile')
            saved = self._read_original_context(connection, run, operation)
            if saved is None:
                return None
            handle, row = self._handle(connection, run, operation)
            observation = c.OperationObservation.model_validate_json(operation['observation_json'])
        return self._settled_asr_facts(run, operation, handle, row, saved, observation)

    def _probe_waiting_original_asr(self, run_id, operation_id):
        """Private original unowned checkpoint preflight, not an operation API."""
        with self._original_context_guard(run_id):
            return self._probe_waiting_asr_facts(run_id, operation_id)

    def _probe_waiting_asr_facts(self, run_id, operation_id):
        with self.engine.db.connect_readonly() as connection:
            run = self.engine._run(connection, run_id)
            if (run['status'] != 'waiting_user' or run['waiting_revision_id'] is not None
                    or run['worker_id'] is not None or run['lease_until_us'] or run['paused'] or run['cancellation_requested']):
                raise EngineError('final_evidence_state_conflict', 'Original unowned final wait required', 409)
            operation = self._operation(connection, run, operation_id)
            if operation['run_id'] != run['id'] or operation['production_id'] != run['production_id']:
                raise EngineError('asr_result_scope_denied', 'Original ASR belongs to another Run', 403)
            if operation['status'] != 'succeeded' or not operation['settled']:
                raise EngineError('reconciliation_required', 'Original ASR is not settled', 409, 'reconcile')
            saved = self._read_original_context(connection, run, operation)
            if saved is None:
                return None
            handle, row = self._handle(connection, run, operation)
            observation = c.OperationObservation.model_validate_json(operation['observation_json'])
        return self._settled_asr_facts(run, operation, handle, row, saved, observation)

    def _settled_asr_facts(self, run, operation, handle, row, saved, observation):
        path = handle.completed_path
        if not path.is_file():
            raise EngineError('asr_result_unavailable', 'Original settled result file missing', 503)
        data = path.read_bytes()
        from video_creator.application.bundles import strict_json
        stored = StoredAsrObservation.model_validate(strict_json(data))
        if (stored.allocation != handle.allocation or stored.observation != observation
                or row['status'] not in {'ready', 'imported'}
                or (len(data), hashlib.sha256(data).hexdigest()) != (row['size'], row['sha256'])):
            raise EngineError('asr_result_invalid', 'Original settled observation and READY result differ', 422)
        self._valid_observation(stored.allocation, observation)
        ref, raw = saved
        module, _provider, _worker = self._context_source()
        try:
            module.validate_original_asr_result(observation.result_json, raw)
        except (ValueError, TypeError, KeyError):
            raise EngineError('asr_original_result_invalid', 'Original full request validator rejected settled result', 422) from None
        return CurrentFinalAsrRead(operation['id'], run['id'], run['production_id'], operation['input_sha256'],
            digest(operation['route_json']), 'succeeded', True, observation, handle.allocation, raw, ref)
