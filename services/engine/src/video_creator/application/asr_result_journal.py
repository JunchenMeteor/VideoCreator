"""Original local ASR result journal and separate restricted reconciliation phase."""
import hashlib
import json
import os
import threading

from video_creator.application.bundles import strict_json
from video_creator.application.delivery_metadata import DeliveryResolver
from video_creator.application.engine import canonical, digest
from video_creator.application.executor import OperationExecutor
from video_creator.application.asr_validation_context import OriginalAsrValidationContext
from video_creator.application.affected_asr_binding import registered_child_asr
from video_creator.application.worker import (
    PRESENCE_TTL_SECONDS,
    RUN_LEASE_SECONDS,
    WORKER_SLOT,
)
from video_creator.domain import contracts as c
from video_creator.domain.errors import EngineError
from video_creator.domain.registered_production import (
    PROFILE,
    AsrResultAllocation,
    AsrResultHandle,
    ProductionBinding,
    RegisteredReconciliation,
    StoredAsrObservation,
)
from video_creator.domain.worker import OutputReservation

STEP = 'bundle-actual-asr'
SOURCE = 'registered-asr-result-v1:'
RIGHTS = 'Internal actual ASR observation; no output or redistribution permission'


class AsrResultJournal(OriginalAsrValidationContext):
    def __init__(self, engine, worker, *, registration_sha256, resource_manifest_sha256,
                 runtime_manifest_sha256, asr_route_id, original_source_sha256=None):
        self.engine, self.worker, self.assets = engine, worker, worker.assets
        self.registration_sha256 = registration_sha256
        self.resource_manifest_sha256, self.runtime_manifest_sha256 = resource_manifest_sha256, runtime_manifest_sha256
        self.asr_route_id = asr_route_id
        self.original_source_sha256 = dict(original_source_sha256 or {})
        self._original_context_guard_state = threading.local()

    def _binding(self, connection, run):
        production = self.engine._production(connection, run['production_id'])
        row = connection.execute('SELECT * FROM execution_bindings WHERE run_id=?', (run['id'],)).fetchone()
        if not row or digest(row['body']) != row['content_sha256']:
            raise EngineError('execution_binding_missing', 'ASR result requires its original intact registered binding', 409)
        binding = ProductionBinding.model_validate(DeliveryResolver._json(row['body']))
        if (binding.workflow_version, binding.instance_id, binding.production_id, binding.run_id,
                binding.request_revision_id, binding.request_sha256, binding.registration_sha256) != (
                PROFILE, self.engine.instance_id, production['id'], run['id'], production['request_revision_id'],
                digest(production['request_json']), self.registration_sha256):
            raise EngineError('execution_binding_conflict', 'Original ASR request or installed registration changed', 409)
        return binding, row['content_sha256']

    def _operation(self, connection, run, operation_id):
        operation = self.engine._operation(connection, run, operation_id)
        route = c.CapabilityRoute.model_validate(DeliveryResolver._json(operation['route_json']))
        configured = connection.execute('SELECT body FROM routes WHERE id=?', (route.route_id,)).fetchone()
        child = registered_child_asr(connection, self.engine, run, operation['step_key']) if operation['step_key'] != STEP else None
        actual_step = operation['step_key'] if child else STEP
        actual_dedupe = child['dedupe_key'] if child else 'bundle-asr-' + run['id']
        step = connection.execute('SELECT * FROM steps WHERE run_id=? AND step_key=?', (run['id'], actual_step)).fetchone()
        if (operation['step_key'] != actual_step or operation['dedupe_key'] != actual_dedupe
                or child is not None and (operation['input_sha256'] != child['input_sha256'] or route.route_id != child['route_id'])
                or not step or step['input_sha256'] != operation['input_sha256']
                or route.route_id != self.asr_route_id or route.source != 'owned_local'
                or route.destination != 'local:faster-whisper-small-cpu-int8'
                or route.capability != 'transcription' or not route.verified or route.credential_ref
                or route.max_operation_cost.units() or operation['reserved_units']
                or not configured or configured[0] != operation['route_json']):
            raise EngineError('asr_result_scope_denied', 'Only the exact original verified free local ASR operation has a result handle', 403)
        request = c.parse_production_request(self.engine._production(connection, run['production_id'])['request_json'])
        if route.route_id not in request.policy.allowed_provider_routes:
            raise EngineError('asr_result_scope_denied', 'Original ASR route is outside the unchanged request policy', 403)
        return operation

    def _commitment(self, operation, binding_sha256):
        return digest(json.dumps({'operation_id': operation['id'], 'run_id': operation['run_id'],
            'input_sha256': operation['input_sha256'], 'dedupe_key': operation['dedupe_key'],
            'route_sha256': digest(operation['route_json']), 'binding_sha256': binding_sha256,
            'resource_manifest_sha256': self.resource_manifest_sha256,
            'runtime_manifest_sha256': self.runtime_manifest_sha256}, sort_keys=True, separators=(',', ':')))

    def _handle(self, connection, run, operation):
        _binding, binding_sha = self._binding(connection, run)
        row = connection.execute('SELECT a.*,s.media_type,s.status,s.sha256,s.size,s.owner FROM generated_attempts a '
            'JOIN staging s ON s.id=a.staging_id WHERE a.run_id=? AND a.step_key=? AND a.output_key=?',
            (run['id'], operation['step_key'], 'asr-result.' + operation['id'])).fetchone()
        owner = self.engine._production(connection, run['production_id'])['owner']
        if (not row or row['input_sha256'] != operation['input_sha256'] or row['owner'] != owner
                or row['media_type'] != 'application/json' or row['source'] != SOURCE + self._commitment(operation, binding_sha)
                or row['rights'] != RIGHTS):
            raise EngineError('asr_result_handle_missing', 'Only the originally allocated ASR result handle may be read', 503)
        allocation = AsrResultAllocation(operation_id=operation['id'], run_id=run['id'], step_key=operation['step_key'],
            input_sha256=operation['input_sha256'], dedupe_key=operation['dedupe_key'], route_sha256=digest(operation['route_json']),
            attempt_id=row['id'], staging_id=row['staging_id'], binding_sha256=binding_sha,
            resource_manifest_sha256=self.resource_manifest_sha256, runtime_manifest_sha256=self.runtime_manifest_sha256)
        return AsrResultHandle(allocation, self.assets._path('Staging', row['staging_id'])), dict(row)

    def allocate_asr_result(self, lease, intent):
        # Prepare is the same durable Operation and budget, never another queue.
        operation = self.engine.prepare_operation(lease, intent)
        if operation['status'] != 'prepared' or operation['settled']:
            raise EngineError('reconciliation_required', 'An original dispatched ASR cannot allocate or execute again', 409, 'reconcile')
        with self.engine.db.connect() as connection:
            run = self.engine._lease(connection, lease)
            operation = self._operation(connection, run, operation['id'])
            _binding, binding_sha = self._binding(connection, run)
        self.worker.allocate_output(lease, operation['step_key'], intent.input_sha256, 'asr-result.' + operation['id'],
            'application/json', SOURCE + self._commitment(operation, binding_sha), RIGHTS)
        with self.engine.db.connect() as connection:
            run = self.engine._lease(connection, lease)
            return self._handle(connection, run, self._operation(connection, run, operation['id']))[0]

    def _valid_observation(self, allocation, observation):
        actual = observation.result_json
        if (observation.status != 'succeeded' or observation.actual_cost is None or observation.actual_cost.units()
                or observation.cost_evidence != 'confirmed_no_charge' or not isinstance(actual, dict)
                or actual.get('protocol_version') != 'local-asr-v2' or actual.get('kind') != 'actual_transcript'
                or actual.get('coordinate_system') != 'audio_intrinsic' or not isinstance(actual.get('text'), str)
                or not isinstance(actual.get('segments'), list) or not actual['segments']):
            raise EngineError('asr_result_invalid', 'Only the original complete actual local ASR observation can be journaled', 422)
        execution = actual.get('execution')
        if (not isinstance(execution, dict) or execution.get('child_terminal') is not True
                or execution.get('tree_empty') is not True or type(execution.get('return_code')) is not int
                or execution['return_code'] != 0):
            raise EngineError('asr_result_cleanup_unknown', 'Actual child and its owned tree must be terminal before result persistence', 409, 'reconcile')
        expected = digest(json.dumps({'audio_sha256': actual.get('input_audio_sha256'),
            'resource_manifest_sha256': allocation.resource_manifest_sha256}, sort_keys=True))
        if expected != allocation.input_sha256:
            raise EngineError('asr_result_input_conflict', 'Actual transcription does not match its original audio/resource Operation input', 422)
        runtime = actual.get('runtime')
        identity = runtime.get('execution_identity') if isinstance(runtime, dict) else None
        if not isinstance(runtime, dict) or (identity is not None and (not isinstance(identity, dict)
                or identity.get('resource_manifest_sha256') != allocation.resource_manifest_sha256)):
            raise EngineError('asr_result_resource_conflict', 'Actual ASR runtime differs from the original installed resource', 422)

    def persist_asr_result(self, lease, handle, observation):
        with self.engine.db.connect() as connection:
            run = self.engine._lease(connection, lease)
            operation = self._operation(connection, run, handle.allocation.operation_id)
            actual, _row = self._handle(connection, run, operation)
        if actual != handle:
            raise EngineError('asr_result_handle_conflict', 'Caller cannot replace its original controlled ASR result handle', 409)
        self._valid_observation(handle.allocation, observation)
        data = (canonical(StoredAsrObservation(allocation=handle.allocation, observation=observation)) + '\n').encode()
        if len(data) > self.assets.max_bytes:
            raise EngineError('asr_result_too_large', 'Actual result exceeds the existing instance allocation limit', 413)
        path = actual.completed_path
        partial = self.assets._path('Staging', actual.allocation.staging_id + '.partial')
        if path.exists():
            if path.read_bytes() != data:
                raise EngineError('asr_result_conflict', 'Original completed ASR result bytes are immutable', 409)
        else:
            with partial.open('xb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            # Exclusive final installation cannot overwrite an earlier result.
            os.link(partial, path)
            partial.unlink()
        reservation = OutputReservation(attempt_id=handle.allocation.attempt_id, staging_id=handle.allocation.staging_id,
            run_id=lease.run_id, step_key=handle.allocation.step_key, input_sha256=handle.allocation.input_sha256,
            partial_path=partial, completed_path=path)
        receipt = self.worker.finish_output(lease, reservation)
        from video_creator.application.asr_observation_signature import sign_observation
        sign_observation(self.engine, allocation=handle.allocation,
                         staging_sha256=hashlib.sha256(data).hexdigest(), staging_size=len(data),
                         observation=observation)
        return receipt

    def _scope(self, connection, invocation):
        presence = self.worker._presence(connection, invocation.lease.worker_id)
        run = self.engine._run(connection, invocation.lease.run_id)
        if (presence['workflow_version'] != PROFILE or presence['resource_sha256'] != self.registration_sha256
                or presence['active_run_id'] != run['id'] or run['worker_id'] != invocation.lease.worker_id
                or run['fencing_token'] != invocation.lease.fencing_token or run['lease_until_us'] <= self.engine.clock()
                or run['status'] not in {'needs_reconciliation', 'cancel_requested', 'cancelled', 'failed'}):
            raise EngineError('stale_lease', 'Restricted ASR reconciliation lease expired or left its exact phase', 409)
        binding, _sha = self._binding(connection, run)
        if binding != invocation.binding:
            raise EngineError('execution_binding_conflict', 'Restricted phase cannot replace the original binding', 409)
        return run

    def reconciliation_invocation(self, worker_id, *, run_id=None, excluded_runs=()):
        self.engine.recover()
        with self.engine.db.transaction() as connection:
            presence = self.worker._presence(connection, worker_id)
            if presence['active_run_id'] or presence['resource_sha256'] != self.registration_sha256 or presence['workflow_version'] != PROFILE:
                raise EngineError('worker_slot_busy', 'Restricted ASR requires the exact installed empty worker slot', 409)
            rows = connection.execute("SELECT r.* FROM runs r JOIN execution_bindings b ON b.run_id=r.id "
                "WHERE r.status IN ('needs_reconciliation','cancel_requested','failed','cancelled') AND r.lease_until_us<=? "
                + (' AND r.id=?' if run_id else '') + ' ORDER BY r.rowid',
                (self.engine.clock(), run_id) if run_id else (self.engine.clock(),)).fetchall()
            for run in rows:
                if run['id'] in excluded_runs:
                    continue
                raw = connection.execute('SELECT body FROM execution_bindings WHERE run_id=?', (run['id'],)).fetchone()
                original = DeliveryResolver._json(raw[0])
                if not isinstance(original, dict):
                    raise EngineError('execution_binding_conflict', 'Original workflow binding must be a complete object', 422)
                if original.get('workflow_version') != PROFILE:
                    continue
                ids = []
                for operation in connection.execute("SELECT id,step_key FROM operations WHERE run_id=? "
                        "AND settled=0 AND status IN ('submitting','unknown','pending','succeeded') ORDER BY rowid", (run['id'],)):
                    if operation['step_key'] == STEP or registered_child_asr(connection, self.engine, run, operation['step_key']) is not None:
                        self._operation(connection, run, operation['id'])
                        ids.append(operation['id'])
                ids = tuple(ids)
                if not ids:
                    continue
                binding, _sha = self._binding(connection, run)
                fence, expiry = run['fencing_token'] + 1, self.engine.clock() + RUN_LEASE_SECONDS * 1_000_000
                connection.execute('UPDATE runs SET worker_id=?,fencing_token=?,lease_until_us=?,attempt=attempt+1 WHERE id=?',
                    (worker_id, fence, expiry, run['id']))
                connection.execute("UPDATE worker_presence SET state='executing',active_run_id=? WHERE slot=? AND worker_id=?",
                    (run['id'], WORKER_SLOT, worker_id))
                self.engine._event(connection, self.engine._run(connection, run['id']), 'reconciliation.leased')
                return RegisteredReconciliation(lease=c.LeaseGrant(run_id=run['id'], worker_id=worker_id,
                    fencing_token=fence, expires_at_us=expiry), binding=binding, operation_ids=ids)
        return None

    def read_asr_result(self, invocation, operation_id):
        if operation_id not in invocation.operation_ids:
            raise EngineError('asr_result_scope_denied', 'Restricted phase can only read its original named Operation', 403)
        with self.engine.db.connect() as connection:
            run = self._scope(connection, invocation)
            operation = self._operation(connection, run, operation_id)
            handle, row = self._handle(connection, run, operation)
        path = handle.completed_path
        if not path.is_file() or path.stat().st_size > self.assets.max_bytes:
            raise EngineError('asr_result_unavailable', 'No complete original ASR result exists; do not execute ASR again', 409, 'reconcile')
        before = path.stat()
        data = path.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        after = path.stat()
        if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise EngineError('asr_result_changed', 'Original ASR result changed while being read', 409, 'reconcile')
        if row['status'] in {'ready', 'imported'} and (sha, len(data)) != (row['sha256'], row['size']):
            raise EngineError('asr_result_invalid', 'Original ready result bytes differ from their immutable receipt', 422)
        try:
            stored = StoredAsrObservation.model_validate(strict_json(data))
        except (ValueError, TypeError):
            raise EngineError('asr_result_invalid', 'Original complete result does not match its fixed journal grammar', 422) from None
        if stored.allocation != handle.allocation:
            raise EngineError('asr_result_input_conflict', 'Original result belongs to another Operation or resource allocation', 422)
        self._valid_observation(stored.allocation, stored.observation)
        # Repeat the complete original validator against its pre-dispatch commit.
        # Missing historical context remains missing; no driver is constructed.
        with self._original_context_guard(invocation.lease.run_id):
            with self.engine.db.connect_readonly() as connection:
                run = self._scope(connection, invocation)
                operation = self._operation(connection, run, operation_id)
                if operation['run_id'] != run['id'] or operation['production_id'] != run['production_id']:
                    raise EngineError('asr_result_scope_denied', 'Original result must retain its actual Run', 403)
                original = self._read_original_context(connection, run, operation)
            if original is None:
                raise EngineError('asr_recovery_validation_unavailable',
                                  'Original pre-dispatch validation request was not committed', 503, 'reconcile')
            module, _provider, _worker = self._context_source()
            try:
                module.validate_original_asr_result(stored.observation.result_json, original[1])
            except (ValueError, TypeError, KeyError):
                raise EngineError('asr_original_result_invalid', 'Original complete request validator rejected result', 422) from None
            with self.engine.db.connect_readonly() as connection:
                self._context_current(connection, self._scope(connection, invocation))
        return handle, stored.observation, sha, len(data), (after.st_mtime_ns, after.st_ctime_ns)

    def observe_asr_result(self, invocation, operation_id):
        handle, observation, sha, size, signature = self.read_asr_result(invocation, operation_id)
        with self.engine.db.transaction() as connection:
            run = self._scope(connection, invocation)
            operation = self._operation(connection, run, operation_id)
            if operation['status'] == 'failed' or operation['settled']:
                raise EngineError('asr_result_operation_terminal', 'A settled or known failed original Operation cannot be rewritten', 409)
            current, _row = self._handle(connection, run, operation)
            stat = current.completed_path.stat()
            if current != handle or (stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns) != (size, *signature):
                raise EngineError('asr_result_changed', 'Original result changed before its restricted commit', 409)
            connection.execute("UPDATE staging SET sha256=?,size=?,status='ready' WHERE id=? AND status='allocated'",
                (sha, size, handle.allocation.staging_id))
            return self.engine._observe_operation(connection, run, invocation.lease, operation_id, observation,
                                                   True, hold_reconciliation=True)

    def heartbeat_reconciliation(self, invocation):
        with self.engine.db.transaction() as connection:
            self._scope(connection, invocation)
            now = self.engine.clock()
            connection.execute('UPDATE runs SET lease_until_us=? WHERE id=?',
                (now + RUN_LEASE_SECONDS * 1_000_000, invocation.lease.run_id))
            connection.execute('UPDATE worker_presence SET heartbeat_us=?,expires_us=? WHERE slot=? AND worker_id=?',
                (now, now + PRESENCE_TTL_SECONDS * 1_000_000, WORKER_SLOT, invocation.lease.worker_id))

    def finish_reconciliation(self, invocation):
        with self.engine.db.transaction() as connection:
            run = self._scope(connection, invocation)
            remaining = connection.execute("SELECT id FROM operations WHERE run_id=? AND (settled=0 OR status IN ('submitting','unknown','pending')) LIMIT 1", (run['id'],)).fetchone()
            status = run['status'] if run['status'] in {'failed', 'cancelled'} else (
                'needs_reconciliation' if remaining else 'cancelled' if run['cancellation_requested'] else 'queued')
            connection.execute('UPDATE runs SET status=?,worker_id=NULL,lease_until_us=0 WHERE id=?', (status, run['id']))
            connection.execute('UPDATE productions SET status=? WHERE id=?', (status, run['production_id']))
            connection.execute("UPDATE worker_presence SET state='idle',active_run_id=NULL WHERE slot=? AND worker_id=?",
                (WORKER_SLOT, invocation.lease.worker_id))
            self.engine._event(connection, self.engine._run(connection, run['id']), 'reconciliation.finished')
            return status


class RegisteredOperationExecutor(OperationExecutor):
    def __init__(self, engine, journal, vault=None):
        super().__init__(engine, vault)
        self.journal = journal

    def execute(self, lease, intent, driver, *, request_payload=None):
        if intent.step_key.startswith(('repair-alignment-', 'bundle-alignment-')):
            from video_creator.application.registered_alignment import registered_alignment_locator
            from video_creator.application.affected_repair_service import canonical_body
            source = getattr(self.engine, '_registered_plan_source', None)
            if source is None:
                raise EngineError('alignment_step_denied', 'Actual original alignment source required', 403)
            with self.engine.db.connect_readonly() as connection:
                self.engine._lease(connection, lease)
                locator, initial = registered_alignment_locator(connection, lease, intent.step_key)
            body, _request, raw = source._alignment_preflight(lease, locator, initial=initial)
            if intent != source._alignment_intent(body) or request_payload is None or canonical_body(request_payload).encode('utf-8') != raw:
                raise EngineError('alignment_step_denied', 'Exact original registered alignment request payload required', 403)
            return super().execute(lease, intent, driver, request_payload=request_payload)
        if intent.step_key != STEP:
            with self.engine.db.connect_readonly() as connection:
                run = self.engine._lease(connection, lease)
                child = registered_child_asr(connection, self.engine, run, intent.step_key)
            if child is None:
                if intent.step_key.startswith('repair-asr-'):
                    raise EngineError('asr_result_scope_denied', 'Unregistered child ASR Step cannot dispatch', 403)
                return super().execute(lease, intent, driver, request_payload=request_payload)
            if (intent.input_sha256, intent.dedupe_key, intent.route_id) != (child['input_sha256'], child['dedupe_key'], child['route_id']):
                raise EngineError('asr_result_scope_denied', 'Exact registered child ASR intent required', 403)
        operation = self.engine.prepare_operation(lease, intent)
        if operation['status'] != 'prepared' or operation['settled']:
            # Original executor refuses unknown and returns settled without dispatch.
            return super().execute(lease, intent, driver, request_payload=request_payload)
        handle = self.journal.allocate_asr_result(lease, intent)
        self.journal.commit_original_validation_context(lease, handle, driver)

        def journaled_driver(permit, secret):
            if permit.operation_id != handle.allocation.operation_id or secret is not None:
                raise EngineError('asr_result_scope_denied', 'ASR callback must retain the original free credentialless permit', 403)
            observation = driver(permit, secret)
            if isinstance(observation, c.OperationObservation) and observation.status == 'succeeded':
                self.journal.persist_asr_result(lease, handle, observation)
            return observation
        return super().execute(lease, intent, journaled_driver, request_payload=request_payload)
