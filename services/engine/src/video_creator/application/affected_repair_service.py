"""Original held production sources and authenticated preparation master reads."""

import threading
import hashlib
import json
from types import MappingProxyType
from pydantic import BaseModel

from video_creator.application.engine import canonical, digest
from video_creator.domain.bundle import BundlePreparationIntent
from video_creator.domain.errors import EngineError

ROLES = frozenset({'video', 'narration_audio', 'mixed_audio', 'cover'})
COMMAND_PREFIX = 'current_final_affected_execution:'
MASTERS_PREFIX = 'current_final_affected_masters:'
LINEAGE_PREFIX = 'current_final_evidence_lineage:'


def same_audio_identity(parent, child):
    """Actual WAV bytes and decoded clock identity, independent of Asset ID."""
    return (parent.sha256, parent.size, parent.media_type, parent.probe) == (
        child.sha256, child.size, child.media_type, child.probe)


def assert_audio_records_current(connection, parent, child, owner):
    from video_creator.domain import contracts as c
    for expected in (parent, child):
        row = connection.execute('SELECT * FROM assets WHERE id=? AND owner=?', (expected.asset_id, owner)).fetchone()
        if (row is None or (row['sha256'], row['size'], row['media_type'], c.MediaProbe.model_validate_json(row['probe_json']))
                != (expected.sha256, expected.size, expected.media_type, expected.probe)):
            raise EngineError('affected_master_source_changed', 'Actual parent/child audio byte/time record changed', 409)


def canonical_body(value):
    """Same compact sorted JSON bytes; only original typed models need conversion."""
    def typed(item):
        if isinstance(item, BaseModel):
            return item.model_dump(mode='json')
        raise TypeError('Only typed model leaves are valid in a private command body')
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), default=typed, allow_nan=False)


class AffectedRepairService:
    def _affected_step_row(self, connection, lease, key):
        self.engine._lease(connection, lease)
        row = connection.execute('SELECT * FROM steps WHERE run_id=? AND step_key=?', (lease.run_id, key)).fetchone()
        if row is None:
            raise EngineError('affected_master_source_unavailable', 'Original registered Step missing', 503)
        return row
    def _affected_claim(self, connection, lease, continuation):
        from video_creator.application.current_final_evidence_journal import PREFIX, parse_journal, prepared_current
        saved = connection.execute('SELECT value FROM metadata WHERE key=?', (PREFIX + lease.run_id,)).fetchone()
        if saved is None:
            raise EngineError('final_evidence_claim_required', 'Original executing repair checkpoint required', 409)
        journal = parse_journal(saved[0], now=self.engine.clock())
        row, run, production, request = prepared_current(self.engine, connection, journal)
        binding = self._final_binding(lease, connection)
        if (binding != continuation.binding or journal.binding != binding or journal.snapshot != continuation.snapshot
                or journal.control.phase != 'executing' or journal.control.resume_mode != 'repair'
                or continuation.resume_mode != 'repair' or journal.control.execution_fence != lease.fencing_token
                or continuation.execution_fence != lease.fencing_token or journal.snapshot.repair is None):
            raise EngineError('final_evidence_claim_required', 'Exact current original repair continuation required', 409)
        return saved[0], journal, row, run, production, request

    def _affected_services(self, lease):
        with self._lock:
            held = [value for value in getattr(self, '_production_services_held', {}).values()
                    if value[2] == lease and value[3] == threading.get_ident()]
        if len(held) != 1:
            raise EngineError('production_services_source_invalid', 'One actual current factory source required', 403)
        self.assert_current_production_services(lease, held[0][0], held[0][1])
        return held[0]

    def _affected_execution(self, connection, lease, execution):
        from video_creator.application.bundles import strict_json
        with self._lock:
            held = self._affected_execution_held.get(id(execution))
        if (held is None or held[0] is not execution or held[1] != lease
                or held[2] != threading.get_ident() or execution.execution_fence != lease.fencing_token):
            raise EngineError('affected_execution_denied', 'Actual current service-held execution required', 403)
        raw, journal, parent, run, production, request = self._affected_claim(connection, lease, held[3])
        saved = connection.execute('SELECT value FROM metadata WHERE key=?',
            (COMMAND_PREFIX + execution.repair_command_sha256,)).fetchone()
        if saved is None:
            raise EngineError('affected_command_unavailable', 'Original persistent command required', 503)
        command = strict_json(saved[0].encode())
        source = {key: value for key, value in command.items() if key not in {
            'repair_command_sha256', 'source_sha256', 'steps', 'child_preparation_id', 'child_intent_sha256', 'child_asr'}}
        if (digest(canonical_body(source)) != execution.repair_command_sha256
                or command.get('source_sha256') != execution.repair_command_sha256
                or command.get('binding') != execution.binding.model_dump(mode='json')
                or command.get('parent_preparation_id') != parent['id']
                or command.get('parent_intent_sha256') != digest(parent['intent_json'])
                or command.get('source_report_ref') != (execution.source_report_ref.model_dump(mode='json') if execution.source_report_ref is not None else None)):
            raise EngineError('affected_command_invalid', 'Original complete command identity changed', 422)
        if command.get('format') == 'current-final-affected-execution-v2-diagnostic-v1':
            from video_creator.domain.component_diagnosis import AffectedRepairExecutionDiagnosedV1
            from video_creator.application.diagnosed_affected_service import diagnosed_source
            source=diagnosed_source(command)
            if (type(execution) is not AffectedRepairExecutionDiagnosedV1
                    or source.diagnostic_ref!=execution.diagnostic_ref or source.input_key_sha256!=execution.input_key_sha256
                    or source.proposal.recipe_id!=execution.recipe_id or source.proposal.component_target_ids!=execution.component_target_ids):
                raise EngineError('affected_command_invalid','Exact current held diagnosed execution required',422)
        self.assert_command_targets_writer(connection, lease, command)
        return command, saved[0], raw, journal, parent, run, production, request

    def _live_affected_for_parent(self, lease, preparation_id, affected):
        with self._lock:
            values = [value[0] for value in self._affected_execution_held.values()
                      if value[1] == lease and value[2] == threading.get_ident()
                      and value[0].parent_preparation_id == preparation_id
                      and value[0].affected_artifact_ids == tuple(affected)]
        by_sha = {value.repair_command_sha256: value for value in values}
        if len(by_sha) != 1:
            raise EngineError('affected_execution_denied', 'One actual current registered finite repair required', 403)
        return next(iter(by_sha.values()))

    def read_registered_child_asr_intent(self, lease, execution):
        from video_creator.application.affected_asr_binding import registered_child_asr
        from video_creator.domain import contracts as c
        self._affected_services(lease)
        issuer = self._production_authorization.issuer()
        with issuer.current_guard(self._production_authorization.registered(lease)) as guard:
            with self.engine.db.connect_readonly() as connection:
                command, _raw, _journal_raw, journal, parent, run, _production, _request = self._affected_execution(connection, lease, execution)
                issuer._guard(connection, guard)
                child_id = command.get('child_preparation_id')
                if child_id is None:
                    raise EngineError('affected_child_required', 'Actual atomic child commit must precede child ASR', 409)
                child = self._selected_affected_child(connection, lease.run_id, journal, parent, child_id)
            parent_roles = self.resolve_preparation_masters(lease, parent['id'])
            child_roles = self.resolve_preparation_masters(lease, child['id'])
            with self.engine.db.connect_readonly() as connection:
                current_run = self.engine._lease(connection, lease)
                assert_audio_records_current(connection, parent_roles['mixed_audio'], child_roles['mixed_audio'],
                    self.engine._production(connection, current_run['production_id'])['owner'])
            if same_audio_identity(parent_roles['mixed_audio'], child_roles['mixed_audio']):
                if command.get('child_asr') is not None:
                    raise EngineError('asr_result_scope_denied', 'Unchanged original audio cannot carry a new ASR registration', 403)
                with self.engine.db.connect_readonly() as connection:
                    _command, _raw, _jraw, _journal, _parent, _run, _production, _request = self._affected_execution(connection, lease, execution)
                    assert_audio_records_current(connection, parent_roles['mixed_audio'], child_roles['mixed_audio'], _production['owner'])
                    issuer._guard(connection, guard)
                return None
            with self.engine.db.connect_readonly() as connection:
                current, _raw, _journal_raw, _journal, _parent, run, _production, _request = self._affected_execution(connection, lease, execution)
                if current != command:
                    raise EngineError('affected_command_conflict', 'Actual selected child command changed', 409)
                registered = registered_child_asr(connection, self.engine, run, 'repair-asr-' + execution.repair_command_sha256[:32])
                if registered is None:
                    raise EngineError('asr_result_scope_denied', 'Changed actual audio requires its committed child ASR registration', 403)
                route = self.engine.configured_route(registered['route_id'])
                runtime = self._production_services_runtime
                if (route.route_id != runtime.config.asr_route_id or route.source != 'owned_local'
                        or route.capability != 'transcription' or not route.verified or route.credential_ref
                        or route.max_operation_cost.units() or route.destination != 'local:faster-whisper-small-cpu-int8'):
                    raise EngineError('asr_result_scope_denied', 'Actual original free local ASR route required', 403)
                assert_audio_records_current(connection, parent_roles['mixed_audio'], child_roles['mixed_audio'], _production['owner'])
                issuer._guard(connection, guard)
                return c.OperationIntent(step_key=registered['step_key'], dedupe_key=registered['dedupe_key'],
                    input_sha256=registered['input_sha256'], route_id=registered['route_id'], reserved_cost=c.Money(amount='0'))

    def _selected_affected_child(self, connection, run_id, journal, parent, child_id):
        from video_creator.application.bundles import strict_json
        matches = []
        for stored in connection.execute('SELECT value FROM metadata WHERE key LIKE ?', (COMMAND_PREFIX + '%',)):
            command = strict_json(stored[0].encode())
            if (command.get('binding') == journal.binding.model_dump(mode='json')
                    and command.get('parent_preparation_id') == parent['id']
                    and command.get('child_preparation_id') == child_id):
                matches.append(command)
        if len(matches) != 1:
            raise EngineError('final_evidence_lineage_invalid', 'One actual current selected child command required', 422)
        command = matches[0]
        child = connection.execute('SELECT * FROM bundle_revisions WHERE id=? AND run_id=?', (child_id, run_id)).fetchone()
        lineage = connection.execute('SELECT value FROM metadata WHERE key=?', (LINEAGE_PREFIX + child_id,)).fetchone()
        if (child is None or lineage is None or command['child_intent_sha256'] != digest(child['intent_json'])
                or command['parent_intent_sha256'] != digest(parent['intent_json'])):
            raise EngineError('final_evidence_lineage_invalid', 'Actual immutable selected child association changed', 422)
        body = strict_json(lineage[0].encode())
        diagnosed=command.get('format')=='current-final-affected-execution-v2-diagnostic-v1'
        if diagnosed and (body.get('format')!='current-final-evidence-lineage-v3'
                or body.get('diagnostic_ref')!=command.get('diagnostic_ref')
                or body.get('input_key_sha256')!=command.get('input_key_sha256')
                or body.get('failure_source')!=command.get('failure_source')):
            raise EngineError('final_evidence_lineage_invalid','Actual selected child diagnostic source association changed',422)
        if (body.get('repair_command_sha256') != command['repair_command_sha256']
                or body.get('parent_preparation_id') != parent['id']
                or body.get('child_preparation_id') != child_id or body.get('child_intent_sha256') != digest(child['intent_json'])
                or body.get('affected_artifact_ids') != command['affected_artifact_ids']
                or body.get('repair_source_report_sha256') != (command['source_report_ref']['sha256'] if command['source_report_ref'] else None)):
            raise EngineError('final_evidence_lineage_invalid', 'Selected child differs from original command/report/subset', 422)
        return child

    def read_current_affected_execution_inputs(self, lease, continuation):
        from video_creator.domain.component_diagnosis import CurrentFinalDiagnosticContinuationV1
        if type(continuation) is CurrentFinalDiagnosticContinuationV1:
            return self.read_diagnosed_affected_execution_inputs(lease,continuation)
        from video_creator.application.bundles import strict_json
        from video_creator.domain.affected_repair import AffectedRepairExecution, AffectedRepairReadSet
        from video_creator.domain.bundle import MaterialReceipt
        held = self._affected_services(lease)
        self._production_services_runtime._current_final_execution_facts(lease, held[1], held[5])
        with self.engine.db.connect_readonly() as connection:
            _raw, journal, row, _run, _production, _request = self._affected_claim(connection, lease, continuation)
            matches = []
            for saved in connection.execute('SELECT value FROM metadata WHERE key LIKE ?', (COMMAND_PREFIX + '%',)):
                body = strict_json(saved[0].encode())
                if (body.get('binding') == journal.binding.model_dump(mode='json')
                        and body.get('parent_preparation_id') == row['id']
                        and body.get('source_report_ref') == journal.snapshot.repair.source_report_ref.model_dump(mode='json')
                        and body.get('affected_artifact_ids') == list(journal.snapshot.repair.affected_artifact_ids)):
                    matches.append(body)
        if len(matches) != 1:
            raise EngineError('affected_execution_unavailable' if not matches else 'affected_command_conflict',
                'One actual registered command for this original failed source required', 503 if not matches else 409)
        command = matches[0]
        execution = AffectedRepairExecution(journal.binding, lease.fencing_token, row['id'], command['parent_intent_sha256'],
            command['repair_command_sha256'], MaterialReceipt.model_validate(command['source_report_ref']),
            tuple(command['affected_artifact_ids']), tuple(command['failed_unit_ids']), command['requested_action'],
            tuple(command['changed_media_roles']), tuple(command['affected_shot_ids']))
        with self._lock:
            self._affected_execution_held[id(execution)] = (execution, lease, threading.get_ident(), continuation)
        with self.engine.db.connect_readonly() as connection:
            self._affected_execution(connection, lease, execution)
            observed = connection.execute('SELECT value FROM metadata WHERE key=?',
                (MASTERS_PREFIX + execution.repair_command_sha256,)).fetchone()
        masters = (self.observe_current_affected_masters(lease, execution,
                   step_key='repair-master-' + execution.repair_command_sha256[:32]) if observed else None)
        issuer = self._production_authorization.issuer()
        with issuer.current_guard(self._production_authorization.registered(lease)) as guard:
            parent_read = self._read_current_final_continuation_inputs(lease, continuation, guard)
            child_read = (self._read_current_final_continuation_inputs(lease, continuation, guard,
                          selected_preparation_id=command['child_preparation_id']) if command['child_preparation_id'] else None)
        return AffectedRepairReadSet(execution, parent_read, child_read, masters)

    def observe_current_affected_masters(self, lease, execution, *, step_key):
        from video_creator.application.bundles import strict_json
        from video_creator.domain import contracts as c
        from video_creator.domain.affected_repair import AffectedMasterObservation
        from video_creator.domain.worker import GeneratedFileManifest
        self._affected_services(lease)
        with self.engine.db.connect_readonly() as connection:
            command, command_raw, _journal_raw, _journal, parent, _run, _production, _request = self._affected_execution(connection, lease, execution)
        expected_master='repair-master-' + execution.repair_command_sha256[:32]
        if command.get('format') == 'current-final-affected-execution-v2-diagnostic-v1':
            from video_creator.domain.affected_repair_steps import affected_recipe_step
            expected_master=affected_recipe_step(execution,'master',component_target_id='production-master')[0]
        if execution.requested_action != 'regenerate_affected_media' or step_key != expected_master:
            raise EngineError('affected_master_source_invalid', 'Only this admitted command master-index Step may be observed', 422)
        target = command['steps'].get(step_key)
        changed, step, operations = self._master_roles_from_step(lease, step_key, execution.changed_media_roles)
        if target is None or step['input_sha256'] != target['input_sha256']:
            raise EngineError('affected_master_source_invalid', 'Actual master input differs from registered full command', 422)
        result = strict_json(step['result_json'].encode())['result']
        source_steps = result.get('source_steps')
        if (not isinstance(source_steps, list) or not source_steps or len(set(source_steps)) != len(source_steps)
                or not set(source_steps) <= set(command['steps']) - {step_key}):
            raise EngineError('affected_master_source_invalid', 'Master must retain the actual registered generated source Steps', 422)
        receipts = []
        contributed = set()
        source_snapshots = []
        indexed = []
        with self.engine.db.connect_readonly() as connection:
            for key in source_steps:
                source = self._affected_step_row(connection, lease, key)
                expected = command['steps'][key]
                if source['status'] != 'succeeded' or source['input_sha256'] != expected['input_sha256']:
                    raise EngineError('affected_master_source_invalid', 'Original successful source Step required', 422)
                saved = strict_json(source['result_json'].encode())
                contributed.update(saved['asset_ids'])
                source_operations = connection.execute('SELECT * FROM operations WHERE run_id=? AND step_key=?', (lease.run_id, key)).fetchall()
                if not source_operations or any(op['status'] != 'succeeded' or not op['settled'] for op in source_operations):
                    raise EngineError('affected_master_evidence_pending', 'Original generated source Operations require reconciliation', 409, 'reconcile')
                source_snapshots.append((key, dict(source), [dict(op) for op in source_operations]))
                for op in source_operations:
                    route = c.CapabilityRoute.model_validate_json(op['route_json'])
                    observation = c.OperationObservation.model_validate_json(op['observation_json'])
                    if (op['input_sha256'] != expected['input_sha256'] or op['dedupe_key'] != expected['dedupe_key']
                            or route.route_id != expected['route_id'] or observation.status != 'succeeded'
                            or not isinstance(observation.result_json, dict) or not observation.result_json.get('generated_files')):
                        raise EngineError('affected_master_source_invalid', 'Actual registered generated-file Observation required', 422)
                    receipts.extend(GeneratedFileManifest.model_validate(value) for value in observation.result_json['generated_files'])
            for op in operations:
                route = c.CapabilityRoute.model_validate_json(op['route_json'])
                observation = c.OperationObservation.model_validate_json(op['observation_json'])
                if (op['input_sha256'] != target['input_sha256'] or op['dedupe_key'] != target['dedupe_key']
                        or route.route_id != target['route_id'] or route.source != 'owned_local'
                        or route.credential_ref or route.max_operation_cost.units() or op['reserved_units']
                        or observation.status != 'succeeded' or not isinstance(observation.result_json, dict)
                        or set(observation.result_json.get('observed_masters', {})) != set(changed)):
                    raise EngineError('affected_master_source_invalid', 'Actual free original master-index observation required', 422)
                indexed.append(observation.result_json['observed_masters'])
        if not set(changed.values()) <= contributed:
            raise EngineError('affected_master_source_invalid', 'New Asset IDs must originate in registered actual generated Steps', 422)
        parent_roles = {role: asset.asset_id for role, asset in self.resolve_preparation_masters(lease, parent['id']).items()}
        effective = {**parent_roles, **changed}
        if len(set(effective.values())) != 4 or any(changed[role] == parent_roles[role] for role in changed):
            raise EngineError('affected_master_source_invalid', 'Changed roles require distinct actual new Assets', 422)
        for role, asset_id in changed.items():
            asset = self.asset(lease, asset_id)
            path = self.content_path(lease, asset_id)
            if path.stat().st_size != asset.size or self.assets._hash(path) != asset.sha256:
                raise EngineError('bundle_integrity_failed', 'Generated affected master bytes changed', 422)
            if asset.media_type != {'video': 'video/mp4', 'narration_audio': 'audio/wav', 'mixed_audio': 'audio/wav', 'cover': 'image/jpeg'}[role]:
                raise EngineError('affected_master_source_invalid', 'Actual new master MIME must match its registered role', 422)
            if not any(value.candidate.sha256 == asset.sha256 and value.candidate.size == asset.size for value in receipts):
                raise EngineError('affected_master_source_invalid', 'Registered new asset lacks its actual generated-file manifest', 422)
            if self.validators.media_validator is None:
                raise EngineError('media_decoder_unavailable', 'Actual registered decoder required', 503)
            self.validators.media_validator(path, asset.media_type)
            for actual_index in indexed:
                expected_index = {'asset_id': asset.asset_id, 'sha256': asset.sha256,
                                  'probe': asset.probe.model_dump(mode='json')}
                if actual_index[role] != expected_index:
                    raise EngineError('affected_master_source_invalid', 'Master-index observation differs from actual decoded asset', 422)
        observation = AffectedMasterObservation(execution.binding, parent['id'], execution.repair_command_sha256,
            step_key, step['input_sha256'], tuple(op['id'] for op in operations), execution.changed_media_roles,
            MappingProxyType(effective))
        body = canonical_body({'format': 'current-final-affected-masters-v1', 'binding': execution.binding,
            'parent_preparation_id': parent['id'], 'repair_command_sha256': execution.repair_command_sha256,
            'step_key': step_key, 'step_input_sha256': step['input_sha256'], 'operation_ids': observation.operation_ids,
            'changed_media_roles': execution.changed_media_roles, 'effective_media_roles': effective,
            'source_steps': source_steps})
        issuer = self._production_authorization.issuer()
        with issuer.current_guard(self._production_authorization.registered(lease)) as guard:
            with self.engine.db.connect_readonly() as connection:
                existing = connection.execute('SELECT value FROM metadata WHERE key=?',
                    (MASTERS_PREFIX + execution.repair_command_sha256,)).fetchone()
                if existing is not None:
                    if existing[0] != body:
                        raise EngineError('affected_master_conflict', 'Original committed master observation is immutable', 409)
                    current, current_raw, _jraw, _journal, _parent, _run, _production, _request = self._affected_execution(connection, lease, execution)
                    self.assert_command_targets_writer(connection, lease, current, guard=guard)
                    if current_raw != command_raw or dict(self._affected_step_row(connection, lease, step_key)) != dict(step):
                        raise EngineError('affected_master_source_changed', 'Original committed source changed during pure restore', 409)
                    current_operations = connection.execute('SELECT * FROM operations WHERE run_id=? AND step_key=?', (lease.run_id, step_key)).fetchall()
                    if [dict(op) for op in current_operations] != [dict(op) for op in operations]:
                        raise EngineError('affected_master_source_changed', 'Original settled index observations changed during pure restore', 409)
                    for key, source, source_ops in source_snapshots:
                        actual_source = self._affected_step_row(connection, lease, key)
                        actual_ops = connection.execute('SELECT * FROM operations WHERE run_id=? AND step_key=?', (lease.run_id, key)).fetchall()
                        if dict(actual_source) != source or [dict(op) for op in actual_ops] != source_ops:
                            raise EngineError('affected_master_source_changed', 'Original generation facts changed during pure restore', 409)
                    issuer._guard(connection, guard)
                    with self._lock:
                        self._affected_observation_held[id(observation)] = (observation, lease, threading.get_ident())
                    return observation
            with self.engine.db.transaction() as connection:
                current, current_raw, journal_raw, journal, _parent, run, production, request = self._affected_execution(connection, lease, execution)
                issuer.assert_final_evidence_resume_current(connection, guard, run_id=run['id'], binding=execution.binding,
                    journal_sha256=digest(journal_raw), resume_mode='repair', affected_artifact_ids=execution.affected_artifact_ids)
                if self._affected_services_writer(lease)[5]:
                    issuer.require_operation_current(connection, guard, lease)
                self.assert_command_targets_writer(connection, lease, command, guard=guard)
                if current_raw != command_raw or self._affected_step_row(connection, lease, step_key)['result_json'] != step['result_json']:
                    raise EngineError('affected_master_source_changed', 'Original command or master Step changed before observation commit', 409)
                actual_ops = connection.execute('SELECT * FROM operations WHERE run_id=? AND step_key=?', (lease.run_id, step_key)).fetchall()
                if [dict(op) for op in actual_ops] != [dict(op) for op in operations]:
                    raise EngineError('affected_master_source_changed', 'Original settled master Operations changed before commit', 409)
                for key, source, source_ops in source_snapshots:
                    actual_source = self._affected_step_row(connection, lease, key)
                    actual_source_ops = connection.execute('SELECT * FROM operations WHERE run_id=? AND step_key=?', (lease.run_id, key)).fetchall()
                    if dict(actual_source) != source or [dict(op) for op in actual_source_ops] != source_ops:
                        raise EngineError('affected_master_source_changed', 'Original generated source rows changed before commit', 409)
                for role, asset_id in changed.items():
                    current_asset = connection.execute('SELECT sha256 FROM assets WHERE id=? AND owner=?', (asset_id, production['owner'])).fetchone()
                    if current_asset is None or current_asset[0] != indexed[0][role]['sha256']:
                        raise EngineError('affected_master_source_changed', 'Actual registered new Asset changed before observation commit', 409)
                key = MASTERS_PREFIX + execution.repair_command_sha256
                previous = connection.execute('SELECT value FROM metadata WHERE key=?', (key,)).fetchone()
                if previous is not None and previous[0] != body:
                    raise EngineError('affected_master_conflict', 'Original master observation is immutable', 409)
                if previous is None:
                    connection.execute('INSERT INTO metadata(key,value) VALUES(?,?)', (key, body))
                    self.engine._event(connection, run, 'production.affected_masters_observed', digest(body))
                self._affected_execution(connection, lease, execution)
                if self._affected_services_writer(lease)[5]:
                    issuer.require_operation_current(connection, guard, lease)
                self.assert_command_targets_writer(connection, lease, command, guard=guard)
                issuer._guard(connection, guard)
        with self._lock:
            self._affected_observation_held[id(observation)] = (observation, lease, threading.get_ident())
        return observation

    def authorize_current_affected_execution(self, lease, continuation, proposal):
        from video_creator.domain.component_diagnosis import CurrentFinalDiagnosticContinuationV1
        if type(continuation) is CurrentFinalDiagnosticContinuationV1:
            return self.authorize_diagnosed_affected_execution(lease,continuation,proposal)
        from video_creator.application.bundles import strict_json, validate_text
        from video_creator.application.current_production_blockers import require_settled
        from video_creator.domain import contracts as c
        from video_creator.domain.affected_repair import AffectedRepairExecution, AffectedRepairProposal
        from video_creator.domain.affected_repair_steps import affected_master_step
        if type(proposal) is not AffectedRepairProposal:
            raise EngineError('affected_proposal_invalid', 'Sole typed finite proposal required', 422)
        held = self._affected_services(lease)
        parent = self.read_current_final_continuation_inputs(lease, continuation)
        repair = continuation.snapshot.repair
        if (repair is None or proposal.parent_preparation_id != parent.preparation.preparation_id
                or proposal.affected_artifact_ids != repair.affected_artifact_ids
                or proposal.failed_unit_ids != repair.failed_unit_ids):
            raise EngineError('affected_proposal_invalid', 'Actual original failed source and ordered subset required', 422)
        report_bytes = self.read_material(lease, proposal.parent_preparation_id, repair.source_report_ref.material_id)
        if hashlib.sha256(report_bytes).hexdigest() != repair.source_report_ref.sha256:
            raise EngineError('affected_report_changed', 'Original failed full report changed', 422)
        report = validate_text(report_bytes, repair.source_report_ref.schema_kind, repair.source_report_ref.media_type)
        failed = tuple(unit.transcript_unit_id for unit in report.boundaries if max(
            abs(unit.predicted_range.start_us - unit.reference_range.start_us),
            abs(unit.predicted_range.end_us - unit.reference_range.end_us)) > 200_000)
        if failed != proposal.failed_unit_ids:
            raise EngineError('affected_proposal_invalid', 'Proposed units differ from actual original failure', 422)
        if parent.assembly is None or parent.candidate is None:
            raise EngineError('affected_source_unavailable', 'Actual failed candidate and original assembly required', 503)
        manifest = c.parse_bundle_manifest(strict_json(parent.candidate[0]))
        revisions = {value.revision_id: value for value in self.creative_revisions(lease)}
        plan_ref = next((ref for ref in parent.assembly.creative_revision_refs if ref.kind == 'plan'), None)
        storyboard_ref = next((ref for ref in parent.assembly.creative_revision_refs if ref.kind == 'storyboard'), None)
        plan = revisions.get(plan_ref.revision_id) if plan_ref else None
        storyboard = revisions.get(storyboard_ref.revision_id) if storyboard_ref else None
        if (plan is None or storyboard is None or digest(canonical(plan)) != plan_ref.content_sha256
                or digest(canonical(storyboard)) != storyboard_ref.content_sha256 or not isinstance(plan.body, dict)
                or not isinstance(storyboard.body, dict)):
            raise EngineError('affected_source_invalid', 'Exact committed plan and storyboard required', 422)
        original_proposal = c.CreativeProposal.model_validate(plan.body.get('proposal'))
        plan_shots = {shot.shot_id: shot for shot in original_proposal.shots}
        failed_ranges = [unit.predicted_range for unit in report.boundaries if unit.transcript_unit_id in failed]
        shots = tuple(shot['shot_id'] for shot in storyboard.body.get('shots', ()) if any(
            shot['timeline_range']['start_us'] < value.end_us and value.start_us < shot['timeline_range']['end_us']
            for value in failed_ranges))
        if proposal.affected_shot_ids != shots or not set(shots) <= set(plan_shots):
            raise EngineError('affected_proposal_invalid', 'Actual failed-unit storyboard dependency closure required', 422)
        actual_roles = {role for artifact in manifest.artifacts if artifact.artifact_id in repair.affected_artifact_ids
                        for role in artifact.roles if role in ROLES}
        if not set(proposal.changed_media_roles) <= actual_roles:
            raise EngineError('affected_proposal_invalid', 'New media roles require actual failed artifact dependencies', 422)
        runtime = self._production_services_runtime
        admissions = runtime._current_final_execution_facts(lease, held[1], held[5])
        finite_targets = None
        if proposal.requested_action == 'regenerate_affected_media':
            from video_creator.domain.plan_repair_targets import plan_payload_sha256
            validated = self.validate_registered_plan(lease, plan)
            if validated is None:
                raise EngineError('guidance_required', 'Legacy plan has no approved finite generation targets', 403)
            indexed_targets = validated.repair_targets.targets
            selected = tuple(target for target in indexed_targets if target.kind == 'edit'
                or target.kind == 'narration' and 'narration_audio' in proposal.changed_media_roles
                or target.kind == 'shot_clip' and 'video' in proposal.changed_media_roles and target.shot_ids[0] in shots)
            dependencies = {role for target in selected if target.kind != 'edit' for role in target.dependent_media_roles}
            if not dependencies:
                dependencies = set(proposal.changed_media_roles) & set(indexed_targets[-1].dependent_media_roles)
            if dependencies != set(proposal.changed_media_roles) or not dependencies <= actual_roles:
                raise EngineError('guidance_required', 'Changed roles must match the actual finite recipe failure dependency intersection', 403)
            finite_targets = {'format': validated.repair_targets.format,
                'body_sha256': plan_payload_sha256(validated.repair_targets),
                'target_ids': [target.target_id for target in selected],
                'input_payload_sha256': {target.target_id: target.input_payload_sha256 for target in selected}}
        alignment = getattr(runtime.config, 'alignment_registration', None)
        if proposal.requested_action == 'realignment' and alignment is None:
            raise EngineError('alignment_resource_not_ready', 'Actual qualified alignment registration required', 503)
        route_ids = ({'alignment': alignment.route_id} if proposal.requested_action == 'realignment' else
            {stage: getattr(held[0], stage + '_route_id') for stage in ('narration', 'picture', 'edit', 'master_index')})
        routes = {stage: self.engine.configured_route(route_id) for stage, route_id in route_ids.items()}
        if proposal.requested_action == 'realignment':
            route = routes['alignment']
            if not route.verified or route.source != 'owned_local' or route.capability != 'alignment' or route.credential_ref or route.max_operation_cost.units():
                raise EngineError('alignment_resource_not_ready', 'Verified free local credential-free alignment route required', 503)
            if parent.asr is None:
                raise EngineError('asr_recovery_validation_unavailable', 'Actual source audio ASR context required', 503)
            # The actual registered method must be one of the resolved held qualifications.
            resolved = self._resolve_current_final_inputs(lease, proposal.parent_preparation_id, parent.binding)
            evidence = getattr(resolved, 'resolved', None)
            if evidence is None or alignment.method_qualification_ref != evidence.qualification:
                raise EngineError('alignment_resource_not_ready', 'Actual current algorithm qualification source required', 503)
        source = {'format': 'current-final-affected-execution-v1', 'binding': parent.binding,
            'parent_preparation_id': proposal.parent_preparation_id, 'parent_intent_sha256': digest(canonical(parent.intent)),
            'source_report_ref': repair.source_report_ref, 'affected_artifact_ids': proposal.affected_artifact_ids,
            'failed_unit_ids': failed, 'requested_action': proposal.requested_action,
            'changed_media_roles': proposal.changed_media_roles, 'affected_shot_ids': shots,
            'plan_ref': plan_ref, 'quality_ref': parent.assembly.quality_ref,
            'route_bindings': routes, 'resource_manifest_sha256': held[6], 'runtime_manifest_sha256': held[7]}
        if finite_targets is not None:
            source['repair_targets'] = finite_targets
        source_text = canonical_body(source)
        sha = digest(source_text)
        execution = AffectedRepairExecution(parent.binding, lease.fencing_token, proposal.parent_preparation_id,
            digest(canonical(parent.intent)), sha, repair.source_report_ref, proposal.affected_artifact_ids,
            failed, proposal.requested_action, proposal.changed_media_roles, shots)
        steps = {}
        alignment_companion = None
        if proposal.requested_action == 'realignment':
            alignment_companion, steps = self.prepare_affected_alignment(lease, parent, source, sha)
        if proposal.requested_action == 'regenerate_affected_media':
            targets = [('master', None), ('edit', None)]
            if 'narration_audio' in proposal.changed_media_roles:
                targets.append(('narration', None))
            if 'video' in proposal.changed_media_roles:
                targets.extend(('picture', shot) for shot in shots)
            for stage, shot in targets:
                key, input_sha, dedupe = affected_master_step(execution, stage, shot_id=shot)
                steps[key] = {'stage': stage, 'shot_id': shot, 'input_sha256': input_sha,
                    'dedupe_key': dedupe, 'route_id': route_ids['master_index' if stage == 'master' else stage]}
        body = canonical_body({**source, 'repair_command_sha256': sha, 'source_sha256': digest(source_text),
                          'steps': steps, 'child_preparation_id': None, 'child_intent_sha256': None})
        issuer = self._production_authorization.issuer()
        with issuer.current_guard(self._production_authorization.registered(lease)) as guard:
            with self.engine.db.transaction() as connection:
                original, journal, _row, run, production, request = self._affected_claim(connection, lease, continuation)
                require_settled(connection, lease.run_id)
                issuer.assert_final_evidence_resume_current(connection, guard, run_id=run['id'], binding=parent.binding,
                    journal_sha256=digest(original), resume_mode='repair', affected_artifact_ids=proposal.affected_artifact_ids)
                if held[5]:
                    _request, record = issuer._bound(connection, guard, production, run, action='execute_plan')
                    issuer._bound(connection, guard, production, run, action='continue_bundle_validation')
                    permitted = {route.route_id: route for route in record.policy.routes}
                    for route in routes.values():
                        approved = permitted.get(route.route_id)
                        if approved is None or approved.route_sha256 != digest(canonical(route)):
                            raise EngineError('affected_route_denied', 'Exact current original policy route required', 403)
                    for admission, stage in zip(admissions[:2], ('execute_plan', 'continue_bundle_validation'), strict=True):
                        issuer.assert_production_admission_current(connection, guard, lease, admission.admission_ref, stage=stage)
                self.assert_command_targets_writer(connection, lease, {**source, 'binding': parent.binding.model_dump(mode='json'),
                    'plan_ref': plan_ref.model_dump(mode='json')}, guard=guard)
                old = connection.execute('SELECT value FROM metadata WHERE key=?', (COMMAND_PREFIX + sha,)).fetchone()
                if old is None:
                    cap = min(request.automation.max_revision_cycles, validated.repair_targets.max_revision_cycles) if finite_targets is not None else request.automation.max_revision_cycles
                    if production['revision_cycles'] >= cap:
                        raise EngineError('revision_limit', 'Original shared production revision allowance exhausted', 409)
                    matches = connection.execute('SELECT value FROM metadata WHERE key LIKE ?', (COMMAND_PREFIX + '%',)).fetchall()
                    for value in matches:
                        previous = strict_json(value[0].encode())
                        if (previous.get('binding') == parent.binding.model_dump(mode='json')
                                and previous.get('parent_preparation_id') == proposal.parent_preparation_id
                                and previous.get('source_report_ref') == repair.source_report_ref.model_dump(mode='json')
                                and previous.get('affected_artifact_ids') == list(proposal.affected_artifact_ids)
                                and previous.get('requested_action') == proposal.requested_action):
                            raise EngineError('affected_command_conflict', 'Original failed source already has a different command payload', 409)
                    connection.execute('INSERT INTO metadata(key,value) VALUES(?,?)', (COMMAND_PREFIX + sha, body))
                    self.engine._event(connection, run, 'production.affected_execution_registered', sha)
                else:
                    previous = strict_json(old[0].encode())
                    if (alignment_companion is not None and previous.get('steps') == {}
                            and previous.get('child_preparation_id') is None
                            and previous.get('source_sha256') == digest(source_text)):
                        # Only this actual no-effect continuation may attach the
                        # companion; its original complete command SHA remains.
                        changed = connection.execute('UPDATE metadata SET value=? WHERE key=? AND value=?',
                            (body, COMMAND_PREFIX + sha, old[0]))
                        if changed.rowcount != 1:
                            raise EngineError('affected_command_conflict', 'Original no-effect command changed', 409)
                        previous = strict_json(body.encode('utf-8'))
                    if previous.get('source_sha256') != digest(source_text) or previous.get('steps') != steps:
                        raise EngineError('affected_command_conflict', 'Original command source or deterministic steps changed', 409)
                if alignment_companion is not None:
                    self.persist_affected_alignment_writer(connection, lease, sha, alignment_companion)
                    self.assert_alignment_writer(connection, lease, sha, initial=False, guard=guard)
                self._affected_claim(connection, lease, continuation)
                self.assert_command_targets_writer(connection, lease, strict_json(body.encode()), guard=guard)
                if alignment_companion is not None:
                    self.assert_alignment_writer(connection, lease, sha, initial=False, guard=guard)
                issuer._guard(connection, guard)
        with self._lock:
            self._affected_execution_held[id(execution)] = (execution, lease, threading.get_ident(), continuation)
        return execution

    def assert_current_production_services(self, lease, services, ports):
        """Object identity comes only from the original Runtime's fixed factory."""
        with self._lock:
            held = getattr(self, '_production_services_held', {}).get((lease.run_id, id(services)))
        runtime = getattr(self, '_production_services_runtime', None)
        if (held is None or held[0] is not services or held[1] is not ports
                or held[2] != lease or held[3] != threading.get_ident()
                or runtime is None or runtime.engine is not self.engine
                or runtime.bundle is not self or services.engine is not self.engine
                or services.worker is not runtime.worker or services.executor is not runtime.executor
                or services.bundle is not self):
            raise EngineError('production_services_source_invalid', 'Actual same Runtime factory source required', 403)
        registered = self._production_authorization.registered(lease)
        issuer = self._production_authorization.issuer()
        with issuer.current_guard(registered) as guard:
            with self.engine.db.connect_readonly() as connection:
                run = self.engine._lease(connection, lease)
                production = self.engine._production(connection, run['production_id'])
                from video_creator.application.current_production_blockers import bound_context
                _run, _production, _request, binding = bound_context(self.engine, connection, lease.run_id, runtime.sha256)
                issuer._guard(connection, guard)
                issuer._request(connection, production, run, registered)
                if binding != held[4] or (guard.installation.resource_manifest_sha256,
                        guard.installation.runtime_manifest_sha256) != held[6:8]:
                    raise EngineError('production_services_source_changed', 'Original installed source binding changed', 409)
                from video_creator.domain import contracts as c
                if (c.parse_production_request(production['request_json']).automation.mode == 'unattended') != held[5]:
                    raise EngineError('production_services_mode_invalid', 'Original human/policy source changed', 403)
                issuer._guard(connection, guard)

    def _master_roles_from_step(self, lease, step_key, expected_roles=ROLES):
        from video_creator.application.bundles import strict_json
        step = self.engine.read_step(lease, step_key)
        if step is None or step['status'] != 'succeeded' or type(step['result_json']) is not str:
            raise EngineError('production_media_capability_missing', 'Actual settled master Step required', 503)
        body = strict_json(step['result_json'].encode('utf-8'))
        result = body.get('result') if isinstance(body, dict) else None
        roles = result.get('media_roles') if isinstance(result, dict) else None
        if (not isinstance(roles, dict) or set(roles) != set(expected_roles)
                or any(type(value) is not str for value in roles.values())
                or len(set(roles.values())) != len(expected_roles) or set(body.get('asset_ids', ())) != set(roles.values())):
            raise EngineError('production_media_roles_invalid', 'Exact four registered output roles required', 422)
        with self.engine.db.connect_readonly() as connection:
            self.engine._lease(connection, lease)
            operations = connection.execute('SELECT * FROM operations WHERE run_id=? AND step_key=?',
                (lease.run_id, step_key)).fetchall()
        if not operations or any(op['status'] != 'succeeded' or not op['settled'] for op in operations):
            raise EngineError('media_master_evidence_pending', 'Actual successful settled master Operations required', 409, 'reconcile')
        return roles, step, operations

    def resolve_preparation_masters(self, lease, preparation_id):
        """One bounded same-Run lineage resolver for all four master identities."""
        from video_creator.domain import local_bundle as local
        with self._lock:
            context = getattr(self, '_local_preparation_contexts', {}).get(preparation_id)
        if context is not None:
            from video_creator.domain.bundle import BundlePreparationIntent
            self._local_source().context_snapshot(lease, context)
            with self.engine.db.connect_readonly() as connection:
                row, _run, _production, _request = self._preparation(connection, lease, preparation_id)
                intent = BundlePreparationIntent.model_validate_json(row['intent_json'])
                lineage = connection.execute('SELECT 1 FROM metadata WHERE key=?', (LINEAGE_PREFIX + preparation_id,)).fetchone()
            if lineage is not None:
                raise EngineError('local_lineage_source_required', 'Local selected child requires its actual versioned lineage resolver.', 409)
            roles = self._local_source().runtime.master_assets(lease, selection=context.selection)
            if set(intent.media_asset_ids) != set(roles.values()):
                raise EngineError('production_media_roles_invalid', 'Local preparation must retain the actual selected master Step assets.', 422)
            return {role: self.asset(lease, identifier) for role, identifier in roles.items()}
        from video_creator.application.bundles import strict_json
        rows, seen = [], set()
        current_id = preparation_id
        with self.engine.db.connect_readonly() as connection:
            _run = self.engine._lease(connection, lease)
            production = self.engine._production(connection, _run['production_id'])
            limit = production['revision_cycles'] + 1
            while True:
                if current_id in seen or len(seen) >= limit:
                    raise EngineError('final_evidence_lineage_invalid', 'Cyclic or excessive preparation ancestry', 422)
                seen.add(current_id)
                row = connection.execute('SELECT * FROM bundle_revisions WHERE id=? AND run_id=?',
                    (current_id, lease.run_id)).fetchone()
                if row is None:
                    raise EngineError('final_evidence_lineage_invalid', 'Actual same-Run preparation ancestor required', 422)
                saved = connection.execute('SELECT value FROM metadata WHERE key=?',
                    (LINEAGE_PREFIX + current_id,)).fetchone()
                lineage = None if saved is None else strict_json(saved[0].encode('utf-8'))
                rows.append((row, lineage))
                if lineage is None:
                    break
                if (not isinstance(lineage, dict) or lineage.get('format') not in {
                        'current-final-evidence-lineage-v1', 'current-final-evidence-lineage-v2', 'current-final-evidence-lineage-v3'}
                        or lineage.get('child_preparation_id') != current_id
                        or lineage.get('child_intent_sha256') != digest(row['intent_json'])
                        or lineage.get('child_revision_id') != row['revision_id']
                        or type(lineage.get('parent_preparation_id')) is not str):
                    raise EngineError('final_evidence_lineage_invalid', 'Committed child lineage identity changed', 422)
                current_id = lineage['parent_preparation_id']
        roles, _step, _operations = self._master_roles_from_step(lease, 'media-master')
        root_intent = BundlePreparationIntent.model_validate_json(rows[-1][0]['intent_json'])
        if set(root_intent.media_asset_ids) != set(roles.values()):
            raise EngineError('production_media_roles_invalid', 'Root intent must retain original master Step assets', 422)
        for index in range(len(rows) - 2, -1, -1):
            row, lineage = rows[index]
            parent = rows[index + 1][0]
            if (lineage['parent_intent_sha256'] != digest(parent['intent_json'])
                    or lineage['parent_revision_id'] != parent['revision_id']):
                raise EngineError('final_evidence_lineage_invalid', 'Original parent lineage identity changed', 422)
            if lineage['format']=='current-final-evidence-lineage-v3':
                self.prime_explicit_diagnostic_lineage(lease,row['id'],lineage)
            if lineage['format'] in {'current-final-evidence-lineage-v2','current-final-evidence-lineage-v3'}:
                roles = self._committed_affected_roles(lease, row, parent, lineage, roles)
            intent = BundlePreparationIntent.model_validate_json(row['intent_json'])
            if set(intent.media_asset_ids) != set(roles.values()):
                raise EngineError('production_media_roles_invalid', 'Child intent differs from authenticated effective masters', 422)
        assets = {}
        for role, asset_id in roles.items():
            asset = self.asset(lease, asset_id)
            path = self.content_path(lease, asset_id)
            expected_type = {'video': 'video/mp4', 'narration_audio': 'audio/wav',
                             'mixed_audio': 'audio/wav', 'cover': 'image/jpeg'}[role]
            if asset.media_type != expected_type or path.stat().st_size != asset.size or self.assets._hash(path) != asset.sha256:
                raise EngineError('bundle_integrity_failed', 'Actual master bytes or MIME changed', 422)
            if self.validators.media_validator is None:
                raise EngineError('media_decoder_unavailable', 'Actual registered decoder required', 503)
            self.validators.media_validator(path, asset.media_type)
            assets[role] = asset
        return MappingProxyType(assets)

    def _committed_affected_roles(self, lease, row, parent, lineage, parent_roles):
        from video_creator.application.bundles import strict_json
        sha = lineage.get('repair_command_sha256')
        with self.engine.db.connect_readonly() as connection:
            self.engine._lease(connection, lease)
            command_row = connection.execute('SELECT value FROM metadata WHERE key=?', (COMMAND_PREFIX + str(sha),)).fetchone()
            observation_row = connection.execute('SELECT value FROM metadata WHERE key=?', (MASTERS_PREFIX + str(sha),)).fetchone()
        if command_row is None:
            raise EngineError('affected_master_source_unavailable', 'Committed command and master observation required', 503)
        command = strict_json(command_row[0].encode())
        with self.engine.db.connect_readonly() as connection:
            self.assert_command_targets_writer(connection, lease, command)
        source = {key: value for key, value in command.items() if key not in {
            'repair_command_sha256', 'source_sha256', 'steps', 'child_preparation_id', 'child_intent_sha256', 'child_asr'}}
        if (digest(canonical_body(source)) != sha or command.get('source_sha256') != sha
                or command.get('binding', {}).get('run_id') != lease.run_id
                or command.get('binding', {}).get('instance_id') != self.engine.instance_id
                or lineage.get('affected_artifact_ids') != command.get('affected_artifact_ids')
                or lineage.get('repair_source_report_sha256') != (command.get('source_report_ref') or {}).get('sha256')
                or lineage.get('repair_source_material_id') != (command.get('source_report_ref') or {}).get('material_id')):
            raise EngineError('affected_master_source_invalid', 'Original full command/report/subset binding changed', 422)
        if command.get('requested_action') == 'realignment':
            if (lineage.get('master_observation_ref') is not None or command.get('child_preparation_id') != row['id']
                    or command.get('child_intent_sha256') != digest(row['intent_json'])
                    or command.get('parent_preparation_id') != parent['id']
                    or command.get('parent_intent_sha256') != digest(parent['intent_json'])
                    or command.get('changed_media_roles') != []):
                raise EngineError('affected_master_source_invalid', 'Realignment must preserve exact parent masters', 422)
            return parent_roles
        if observation_row is None:
            raise EngineError('affected_master_source_unavailable', 'Committed generated master observation required', 503)
        observation = strict_json(observation_row[0].encode())
        if (command.get('child_preparation_id') != row['id'] or command.get('child_intent_sha256') != digest(row['intent_json'])
                or command.get('parent_preparation_id') != parent['id']
                or command.get('parent_intent_sha256') != digest(parent['intent_json'])
                or lineage.get('master_observation_ref') != {'repair_command_sha256': sha,
                    'content_sha256': digest(observation_row[0])}
                or observation.get('repair_command_sha256') != sha
                or observation.get('parent_preparation_id') != parent['id']):
            raise EngineError('affected_master_source_invalid', 'Actual command/observation/child association changed', 422)
        master_step='repair-master-' + sha[:32]
        if command.get('format')=='current-final-affected-execution-v2-diagnostic-v1':
            from video_creator.domain.affected_repair_steps import affected_recipe_step_identity
            master_step=affected_recipe_step_identity(command['binding'],sha,'master',component_target_id='production-master')[0]
        changed, step, operations = self._master_roles_from_step(lease, master_step,
            command.get('changed_media_roles', ()))
        roles = {**parent_roles, **changed}
        if (step['input_sha256'] != observation.get('step_input_sha256')
                or sorted(op['id'] for op in operations) != sorted(observation.get('operation_ids', ()))
                or roles != observation.get('effective_media_roles')
                or any(roles[role] != parent_roles[role] for role in ROLES - set(command.get('changed_media_roles', ())))):
            raise EngineError('affected_master_source_invalid', 'Original settled outputs or preserved roles changed', 422)
        return roles
