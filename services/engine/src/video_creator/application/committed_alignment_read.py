"""Current held read-only composition of an already committed CTC result."""

from video_creator.application.engine import canonical, digest
from video_creator.application.affected_repair_service import canonical_body
from video_creator.domain import contracts as c
from video_creator.domain.errors import EngineError


class CommittedAlignmentReadService:
    def _committed_ctc_claim(self, connection, lease, preparation_id=None, continuation=None):
        from video_creator.application.current_final_evidence_journal import PREFIX, parse_journal, prepared_current
        self.engine._lease(connection, lease)
        saved = connection.execute('SELECT * FROM metadata WHERE key=?', (PREFIX + lease.run_id,)).fetchone()
        if saved is None:
            if continuation is None and preparation_id is not None:
                row, run, production, request = self._preparation(connection, lease, preparation_id)
                initial = connection.execute('SELECT 1 FROM metadata WHERE key=?', ('current_initial_alignment:' + preparation_id,)).fetchone()
                lineage = connection.execute('SELECT 1 FROM metadata WHERE key=?', ('current_final_evidence_lineage:' + preparation_id,)).fetchone()
                if initial is not None and lineage is None:
                    binding = self._final_binding(lease, connection)
                    return row, run, production, request, binding, ('metadata', 'key', PREFIX + lease.run_id, None)
            raise EngineError('final_evidence_claim_required', 'Original executing read claim required', 409)
        journal = parse_journal(saved['value'], now=self.engine.clock())
        row, run, production, request = prepared_current(self.engine, connection, journal)
        binding = self._final_binding(lease, connection)
        if (journal.binding != binding or journal.control.phase != 'executing'
                or journal.control.execution_fence != lease.fencing_token
                or journal.control.resume_mode not in {'repair', 'retry_final_validation'}):
            raise EngineError('final_evidence_claim_required', 'Current fenced read claim required', 409)
        if continuation is not None:
            if (continuation.binding != binding or continuation.snapshot != journal.snapshot
                    or continuation.execution_fence != lease.fencing_token
                    or continuation.resume_mode != 'retry_final_validation'
                    or journal.control.resume_mode != 'retry_final_validation'):
                raise EngineError('final_evidence_claim_required', 'Exact current retry continuation required', 409)
            preparation_id = row['id']
        elif preparation_id != row['id']:
            if journal.control.resume_mode != 'repair':
                raise EngineError('final_evidence_claim_required', 'Retry may read only its actual selected preparation', 409)
            row = self._selected_affected_child(connection, lease.run_id, journal, row, preparation_id)
        return row, run, production, request, binding, ('metadata', 'key', saved['key'], dict(saved))

    def _committed_ctc_select(self, connection, lease, selected, production):
        from video_creator.application.bundles import strict_json
        from video_creator.application.registered_alignment import INITIAL_PREFIX
        from video_creator.application.affected_repair_service import COMMAND_PREFIX, LINEAGE_PREFIX
        current, seen, snapshot = selected['id'], set(), []
        maximum = min(32, production['revision_cycles'] + 1)
        while current is not None:
            if current in seen or len(seen) >= maximum:
                raise EngineError('work_ctc_source_invalid', 'Committed ancestry exceeds original revision count or is cyclic', 422)
            seen.add(current)
            row, _run, _production, _request = self._preparation(connection, lease, current)
            snapshot.append(('bundle_revisions', 'id', current, {key: row[key] for key in ('id', 'run_id', 'revision_id', 'intent_json')}))
            initial_key, lineage_key = INITIAL_PREFIX + current, LINEAGE_PREFIX + current
            initial = connection.execute('SELECT * FROM metadata WHERE key=?', (initial_key,)).fetchone()
            edge = connection.execute('SELECT * FROM metadata WHERE key=?', (lineage_key,)).fetchone()
            for key, value in ((initial_key, initial), (lineage_key, edge)):
                snapshot.append(('metadata', 'key', key, dict(value) if value is not None else None))
            command = None
            lineage = None if edge is None else strict_json(edge['value'].encode('utf-8'))
            if lineage is not None:
                if (lineage.get('format') not in {'current-final-evidence-lineage-v1', 'current-final-evidence-lineage-v2','current-final-evidence-lineage-v3'}
                        or lineage.get('child_preparation_id') != current
                        or lineage.get('child_revision_id') != row['revision_id']
                        or lineage.get('child_intent_sha256') != digest(row['intent_json'])):
                    raise EngineError('work_ctc_source_invalid', 'Original child lineage changed', 422)
                parent, _run, _production, _request = self._preparation(connection, lease, lineage['parent_preparation_id'])
                snapshot.append(('bundle_revisions', 'id', parent['id'], {key: parent[key] for key in ('id', 'run_id', 'revision_id', 'intent_json')}))
                if (lineage.get('parent_revision_id') != parent['revision_id']
                        or lineage.get('parent_intent_sha256') != digest(parent['intent_json'])):
                    raise EngineError('work_ctc_source_invalid', 'Original parent intent changed', 422)
                if lineage['format'] in {'current-final-evidence-lineage-v2','current-final-evidence-lineage-v3'}:
                    key = COMMAND_PREFIX + str(lineage.get('repair_command_sha256'))
                    stored = connection.execute('SELECT * FROM metadata WHERE key=?', (key,)).fetchone()
                    if stored is None:
                        raise EngineError('affected_command_unavailable', 'Nearest committed child command missing', 503)
                    snapshot.append(('metadata', 'key', key, dict(stored)))
                    command = strict_json(stored['value'].encode('utf-8'))
                    source = {key: value for key, value in command.items() if key not in {
                        'repair_command_sha256', 'source_sha256', 'steps', 'child_preparation_id', 'child_intent_sha256', 'child_asr'}}
                    sha = lineage['repair_command_sha256']
                    if (digest(canonical_body(source)) != sha or command.get('source_sha256') != sha
                            or command.get('binding', {}).get('run_id') != lease.run_id
                            or command.get('binding', {}).get('instance_id') != self.engine.instance_id
                            or command.get('parent_preparation_id') != parent['id']
                            or command.get('parent_intent_sha256') != digest(parent['intent_json'])
                            or command.get('child_preparation_id') != current
                            or command.get('child_intent_sha256') != digest(row['intent_json'])
                            or command.get('affected_artifact_ids') != lineage.get('affected_artifact_ids')
                            or (command.get('source_report_ref') or {}).get('sha256') != lineage.get('repair_source_report_sha256')
                            or (command.get('source_report_ref') or {}).get('material_id') != lineage.get('repair_source_material_id')):
                        raise EngineError('work_ctc_source_invalid', 'Original command/child/source report association changed', 422)
                    if lineage['format']=='current-final-evidence-lineage-v3' and (
                            command.get('format')!='current-final-affected-execution-v2-diagnostic-v1'
                            or command.get('diagnostic_ref')!=lineage.get('diagnostic_ref')
                            or command.get('input_key_sha256')!=lineage.get('input_key_sha256')
                            or command.get('failure_source')!=lineage.get('failure_source')):
                        raise EngineError('work_ctc_source_invalid','Complete original diagnostic lineage source changed',422)
                    self.assert_command_targets_writer(connection, lease, command)
            if initial is not None and command is not None and command.get('requested_action') == 'realignment':
                raise EngineError('work_ctc_source_invalid', 'Conflicting nearest initial and realignment registrations', 422)
            if initial is not None:
                return (current, True), snapshot
            if command is not None and command.get('requested_action') == 'realignment':
                return (lineage['repair_command_sha256'], False), snapshot
            current = None if lineage is None else lineage['parent_preparation_id']
        return None, snapshot

    def _committed_ctc_guard(self, connection, lease, selection, selected_id, guard):
        """Separate read-source guard; never calls or expands the execution guard."""
        from video_creator.application.bundles import strict_json
        from video_creator.application.current_production_blockers import bound_context
        from video_creator.application.affected_repair_service import COMMAND_PREFIX
        locator, initial = selection
        held = self._affected_services_writer(lease)
        runtime = self._production_services_runtime
        run, production, request, binding = bound_context(self.engine, connection, lease.run_id, runtime.sha256)
        self.engine._lease(connection, lease)
        body, payload, raw = self._load_alignment(connection, lease, locator, initial=initial)
        source_id = payload.preparation_id if initial else payload.parent_preparation_id
        row, _run, _production, _request = self._preparation(connection, lease, source_id)
        if (payload.binding != binding
                or (payload.preparation_intent_sha256 if initial else payload.parent_intent_sha256) != digest(row['intent_json'])
                or (payload.alignment_registration.resource_manifest_sha256, payload.alignment_registration.runtime_manifest_sha256) != held[6:8]
                or payload.alignment_registration.registration != runtime.config.alignment_registration):
            raise EngineError('alignment_source_changed', 'Original committed source/current installation identity changed', 409)
        route = connection.execute('SELECT * FROM routes WHERE id=?', (body['descriptor']['route_id'],)).fetchone()
        if route is None or digest(route['body']) != payload.alignment_registration.route_sha256:
            raise EngineError('alignment_resource_changed', 'Original current route changed', 409)
        ref = request.delivery_requirements.evidence_policy_revision_ref
        resolved = self.engine.evidence_registry.resolve(production['owner'], production['project_id'], ref, connection=connection)
        if resolved.qualification != payload.alignment_registration.registration.method_qualification_ref:
            raise EngineError('alignment_resource_changed', 'Current exact qualification required', 409)
        keys = [('current_initial_alignment:' if initial else 'current_affected_alignment:') + locator,
                'current_final_assembly:' + source_id]
        rows = [('bundle_revisions', 'id', row['id'], {key: row[key] for key in ('id', 'run_id', 'revision_id', 'intent_json')}),
                ('routes', 'id', route['id'], dict(route))]
        for key in keys:
            saved = connection.execute('SELECT * FROM metadata WHERE key=?', (key,)).fetchone()
            if saved is None:
                raise EngineError('alignment_source_unavailable', 'Original request/assembly missing', 503)
            rows.append(('metadata', 'key', key, dict(saved)))
        assembly = strict_json(rows[-1][3]['value'].encode('utf-8'))
        if (assembly.get('binding') != binding.model_dump(mode='json')
                or assembly.get('ref', {}).get('content_sha256') != body['assembly_context_sha256']):
            raise EngineError('alignment_source_changed', 'Original immutable assembly association changed', 409)
        if initial:
            refs = self._initial_alignment_refs(connection, lease, source_id)
            key = 'current_initial_alignment_sources:' + source_id
        else:
            key = COMMAND_PREFIX + locator
            stored = connection.execute('SELECT * FROM metadata WHERE key=?', (key,)).fetchone()
            if stored is None:
                raise EngineError('alignment_source_unavailable', 'Original finite command missing', 503)
            command = strict_json(stored['value'].encode('utf-8'))
            expected = {key: value for key, value in body['descriptor'].items() if key != 'step_key'}
            if (command.get('requested_action') != 'realignment' or command.get('changed_media_roles')
                    or command.get('parent_preparation_id') != source_id
                    or command.get('steps') != {body['descriptor']['step_key']: expected}
                    or command.get('source_report_ref') != payload.source_report_ref.model_dump(mode='json')
                    or tuple(command.get('failed_unit_ids', ())) != payload.failed_unit_ids):
                raise EngineError('alignment_binding_invalid', 'Exact original realignment companion/command required', 422)
            refs = (command['plan_ref'], command['quality_ref'])
        saved = connection.execute('SELECT * FROM metadata WHERE key=?', (key,)).fetchone()
        if saved is None:
            raise EngineError('alignment_source_unavailable', 'Original creative source association missing', 503)
        rows.append(('metadata', 'key', key, dict(saved)))
        issuer = self._production_authorization.issuer()
        issuer._guard(connection, guard)
        issuer._request(connection, production, run, guard.identity)
        for ref, action in zip(refs, ('execute_plan', 'continue_bundle_validation'), strict=True):
            revision = connection.execute('SELECT * FROM creative_revisions WHERE id=? AND run_id=?', (ref['revision_id'], lease.run_id)).fetchone()
            if revision is None or revision['content_sha256'] != ref['content_sha256'] or digest(revision['body']) != ref['content_sha256']:
                raise EngineError('alignment_source_changed', 'Original approved plan/quality changed', 409)
            rows.append(('creative_revisions', 'id', revision['id'], dict(revision)))
            if held[5]:
                _request, record = issuer._bound(connection, guard, production, run, action=action)
                fact = issuer._earlier_action(connection, production, run, record, lease, action)
                route_scope = next((value for value in record.policy.routes if value.route_id == body['descriptor']['route_id']), None)
                if ((fact.target_id, fact.target_sha256) != (ref['revision_id'], ref['content_sha256'])
                        or route_scope is None or route_scope.route_sha256 != payload.alignment_registration.route_sha256):
                    raise EngineError('alignment_execution_denied', 'Original approved source/route scope required for read', 403)
            else:
                approvals = []
                for decision_row in connection.execute('SELECT * FROM decisions WHERE run_id=?', (lease.run_id,)):
                    decision = c.ReviewDecision.model_validate(strict_json(decision_row['body'].encode('utf-8')))
                    if decision.target_revision_id == ref['revision_id']:
                        if digest(decision_row['body']) != decision_row['request_sha256'] or decision_row['result_json'] != decision_row['body']:
                            raise EngineError('production_review_invalid', 'Original human source approval changed', 422)
                        approvals.append(decision)
                        rows.append(('decisions', 'run_id,idempotency_key', (lease.run_id, decision_row['idempotency_key']), dict(decision_row)))
                if len(approvals) != 1 or approvals[0].action != 'approve':
                    raise EngineError('alignment_execution_denied', 'Original human plan/quality approval required', 403)
        if not held[5]:
            declaration = held[1].declaration
            now = self.engine.clock()
            if (declaration.declaring_subject != production['owner'] or production['project_id'] not in declaration.project_ids
                    or declaration.expires_at_us is not None and declaration.expires_at_us <= now
                    or any(right.valid_from_us is not None and right.valid_from_us > now
                        or right.expires_at_us is not None and right.expires_at_us <= now for right in declaration.rights)):
                raise EngineError('production_rights_expired', 'Original production rights expired', 403)
        issuer._guard(connection, guard)
        return body, payload, raw, rows

    def _committed_ctc_composition(self, lease, *, preparation_id=None, continuation=None):
        from video_creator.application.bundles import validate_text
        self._affected_services(lease)
        issuer = self._production_authorization.issuer()
        with issuer.current_guard(self._production_authorization.registered(lease)) as guard:
            with self.engine.db.connect_readonly() as connection:
                selected, _run, production, _request, binding, claim = self._committed_ctc_claim(connection, lease, preparation_id, continuation)
            masters = self.resolve_preparation_masters(lease, selected['id'])
            with self.engine.db.connect_readonly() as connection:
                current,*_=self._committed_ctc_claim(connection,lease,preparation_id,continuation)
                if dict(current)!=dict(selected):
                    raise EngineError('work_ctc_source_changed','Actual selected intent changed before committed result selection',409)
                selection, snapshots = self._committed_ctc_select(connection, lease, selected, production)
                snapshots.append(claim)
                if selection is not None:
                    body, request, raw, source_rows = self._committed_ctc_guard(connection, lease, selection, selected['id'], guard)
                    snapshots.extend(source_rows)
                    source_id = request.preparation_id if selection[1] else request.parent_preparation_id
                    source_row, _run, _production, _request = self._preparation(connection, lease, source_id)
            selected_assembly = self._read_final_assembly(selected, binding)
            if selected_assembly is None:
                raise EngineError('final_assembly_unavailable', 'Selected original authored assembly required', 503)
            with self.engine.db.connect_readonly() as connection:
                assembly_key = 'current_final_assembly:' + selected['id']
                stored = connection.execute('SELECT * FROM metadata WHERE key=?', (assembly_key,)).fetchone()
                if stored is None:
                    raise EngineError('final_assembly_unavailable', 'Selected immutable assembly association missing', 503)
                snapshots.append(('metadata', 'key', assembly_key, dict(stored)))
                materials = tuple(dict(row) for row in connection.execute(
                    'SELECT * FROM bundle_items WHERE preparation_id=? AND asset_id IS NULL ORDER BY artifact_id', (selected['id'],)))
                snapshots.append(('text_materials', 'preparation_id', selected['id'], materials))
                for asset in masters.values():
                    row = connection.execute('SELECT * FROM assets WHERE id=?', (asset.asset_id,)).fetchone()
                    if row is None:
                        raise EngineError('work_ctc_source_changed', 'Original selected master disappeared', 409)
                    snapshots.append(('assets', 'id', asset.asset_id, dict(row)))
            if {value.asset_id for value in selected_assembly.media_artifacts} != {value.asset_id for value in masters.values()}:
                raise EngineError('work_ctc_source_invalid', 'Selected authored four masters differ from committed ancestry', 422)
            for artifact in selected_assembly.media_artifacts:
                if len(artifact.roles) != 1 or artifact.roles[0] not in masters:
                    raise EngineError('work_ctc_source_invalid', 'Selected original master roles required', 422)
                asset = masters[artifact.roles[0]]
                path = self.content_path(lease, asset.asset_id)
                if ((artifact.sha256, artifact.size, artifact.media_type) != (asset.sha256, asset.size, asset.media_type)
                        or path.stat().st_size != asset.size or self.assets._hash(path) != asset.sha256):
                    raise EngineError('work_ctc_source_invalid', 'Actual selected master bytes changed', 422)
                self._media_probe(production['owner'], artifact)
            if selection is None:
                # Legacy is explicit original ASR qualification, not a missing
                # nearest registered source or a not-ready CTC fallback.
                asr = self._original_asr().read_settled_original_asr(lease, selected_assembly.asr_operation_id)
                if asr is None:
                    raise EngineError('asr_recovery_validation_unavailable', 'Original legacy ASR context required', 503)
                with self.engine.db.connect_readonly() as connection:
                    _row, _run, prod, req = self._preparation(connection, lease, selected['id'])
                    resolved = self.engine.evidence_registry.resolve(prod['owner'], prod['project_id'], req.delivery_requirements.evidence_policy_revision_ref, connection=connection)
                method = [value for value in selected_assembly.methods if asr.operation_id in value.operation_ids]
                identity = resolved.qualification.execution_identity
                if (len(method) != 1 or method[0].kind != 'observed' or method[0].method_id != identity.method_id
                        or asr.observation.result_json.get('runtime', {}).get('execution_identity') != identity.model_dump(mode='json')
                        or asr.observation.result_json.get('input_audio_sha256') != masters['mixed_audio'].sha256):
                    raise EngineError('alignment_resource_not_ready', 'Current policy/source does not permit legacy ASR-only work', 503)
                from video_creator.application.asr_validation_context import CONTEXT_PREFIX
                with self.engine.db.connect_readonly() as connection:
                    for table, column, key in (('operations', 'id', asr.operation_id),
                                               ('staging', 'id', asr.allocation.staging_id),
                                               ('metadata', 'key', CONTEXT_PREFIX + asr.operation_id)):
                        row = connection.execute('SELECT * FROM ' + table + ' WHERE ' + column + '=?', (key,)).fetchone()
                        if row is None or (table == 'operations' and c.OperationObservation.model_validate_json(row['observation_json']) != asr.observation):
                            raise EngineError('asr_recovery_validation_unavailable', 'Original legacy ASR association changed', 409)
                        snapshots.append((table, column, key, dict(row)))
                prepared = self.recover_preparation(lease, selected['id'])
                for receipt in prepared.materials:
                    if receipt.schema_kind in {'actual_transcript', 'actual_transcript_v03'}:
                        document = validate_text(self.read_material(lease, selected['id'], receipt.material_id), receipt.schema_kind, receipt.media_type)
                        if document.transcript.method_ref != method[0].method_id or document.alignment.method_ref != method[0].method_id:
                            raise EngineError('alignment_resource_not_ready', 'Legacy source cannot hide a distinct CTC method', 503)
                self._committed_ctc_recheck(lease, snapshots, selection, selected['id'], guard, continuation)
                return None, tuple(snapshots)
            source_assembly = self._read_final_assembly(source_row, request.binding)
            if source_assembly is None or digest(canonical(source_assembly) + '\n') != body['assembly_context_sha256']:
                raise EngineError('alignment_source_changed', 'Original CTC source assembly changed', 409)
            prediction = self._alignment_prediction(body)
            audio, asr, units = self._alignment_sources(lease, source_id, source_assembly, request.transcript.transcript,
                prediction, request.audio.mapping, initial=selection[1])
            registration = self._alignment_registration(lease, request.transcript.transcript, prediction)
            if (audio, asr, units, registration) != (request.audio, request.transcript.asr_source, request.unit_sources, request.alignment_registration):
                raise EngineError('alignment_source_changed', 'Original full source/request/current resource changed', 409)
            if ((masters['mixed_audio'].asset_id, masters['mixed_audio'].sha256, masters['mixed_audio'].size, masters['mixed_audio'].media_type)
                    != (request.audio.asset_id, request.audio.sha256, request.audio.size, request.audio.media_type)
                    or selected_assembly.asr_operation_id != request.transcript.asr_source.operation_id
                    or selected_assembly.audio_mappings != (request.audio.mapping,)):
                raise EngineError('work_ctc_source_invalid', 'Selected audio/ASR/full mapping cannot inherit another CTC', 422)
            facts = self._alignment_result_payload(lease, selection[0], body, request, initial=selection[1])
            alignment, manifest, observation = self._read_committed_alignment_facts(lease, facts)
            operation = facts[5]
            identity = c.AlignmentExecutionIdentity.model_validate(observation.result_json['execution_identity'])
            if identity != registration.registration.method_qualification_ref.execution_identity:
                raise EngineError('work_ctc_source_invalid', 'Actual Observation identity differs from original registration', 422)
            mixed = [value.artifact_id for value in source_assembly.media_artifacts
                     if value.asset_id == request.audio.asset_id and value.roles == ('mixed_audio',)]
            if len(mixed) != 1:
                raise EngineError('work_ctc_source_invalid', 'Original source mixed audio artifact required', 422)
            method = c.MethodEvidence(method_id=identity.method_id, kind='model_inference', tool_name=identity.tool,
                tool_version=identity.tool_version, model_repository=identity.model_id, model_revision=registration.resources.model_revision,
                resource_manifest_sha256=registration.resource_manifest_sha256, operation_ids=(operation['id'],),
                input_artifact_ids=tuple(mixed), config_sha256=identity.configuration_sha256,
                limitations=('Actual forced alignment is not independent work-boundary measurement.',))
            matches = [value for value in selected_assembly.methods if value.method_id == method.method_id]
            if (len(matches) > 1 or matches and matches != [method] or not selection[1] and not matches):
                raise EngineError('alignment_method_conflict', 'Selected authored CTC method must exactly retain the actual operation', 422)
            prepared = self.recover_preparation(lease, selected['id'])
            for receipt in prepared.materials:
                if receipt.schema_kind not in {'actual_transcript', 'actual_transcript_v03'}:
                    continue
                document = validate_text(self.read_material(lease, selected['id'], receipt.material_id), receipt.schema_kind, receipt.media_type)
                if (document.transcript != request.transcript.transcript or type(document.alignment) is not type(alignment)
                        or document.alignment.model_dump(mode='json', exclude={'precision', 'content_sha256'})
                        != alignment.model_dump(mode='json', exclude={'precision', 'content_sha256'})):
                    raise EngineError('work_ctc_source_invalid', 'Selected READY transcript differs from actual original CTC', 422)
            snapshots.extend(self._committed_ctc_fact_rows(lease, body, request, facts))
            self._committed_ctc_recheck(lease, snapshots, selection, selected['id'], guard, continuation)
            stat = self.assets._path('Staging', manifest.candidate.staging_id).stat()
            if (stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns, stat.st_ino) != facts[-1]:
                raise EngineError('alignment_result_changed', 'Original CTC JSON changed before readonly delivery', 409, 'reconcile')
            if self._alignment_registration(lease, request.transcript.transcript, prediction) != registration:
                raise EngineError('alignment_resource_changed', 'Original current resources changed before readonly delivery', 409)
            with self.engine.db.connect_readonly() as connection:
                self.assert_registered_ctc_work_writer(connection, tuple(snapshots))
                issuer._guard(connection, guard)
            return (raw, alignment, manifest, observation, method), tuple(snapshots)

    def _committed_ctc_fact_rows(self, lease, body, request, facts):
        from video_creator.application.asr_validation_context import CONTEXT_PREFIX
        from video_creator.application.bundles import strict_json
        asr = self._original_asr().read_settled_original_asr(lease, request.transcript.asr_source.operation_id)
        if asr is None or asr.context_ref != request.transcript.asr_source.context_ref:
            raise EngineError('asr_recovery_validation_unavailable', 'Original settled ASR context changed', 409)
        rows = []
        keys = [('operations', facts[5]['id']), ('operations', request.transcript.asr_source.operation_id),
                ('generated_attempts', facts[3].attempt_id), ('staging', facts[3].candidate.staging_id),
                ('staging', request.transcript.asr_source.staging_id), ('assets', request.audio.asset_id),
                ('metadata', CONTEXT_PREFIX + request.transcript.asr_source.operation_id)]
        with self.engine.db.connect_readonly() as connection:
            self.engine._lease(connection, lease)
            for table, key in keys:
                column = 'key' if table == 'metadata' else 'id'
                row = connection.execute('SELECT * FROM ' + table + ' WHERE ' + column + '=?', (key,)).fetchone()
                if row is None or (table == 'operations' and key == facts[5]['id'] and dict(row) != facts[5]):
                    raise EngineError('work_ctc_source_changed', 'Actual committed result/source row changed', 409)
                if table == 'operations' and key == asr.operation_id and (
                        c.OperationObservation.model_validate_json(row['observation_json']) != asr.observation
                        or row['status'] != 'succeeded' or not row['settled']
                        or row['input_sha256'] != request.transcript.asr_source.input_sha256
                        or digest(row['route_json']) != request.transcript.asr_source.route_sha256):
                    raise EngineError('work_ctc_source_changed', 'Original ASR Op identity changed during read', 409)
                if table == 'generated_attempts' and any(row[column] != facts[6][column] for column in row.keys()):
                    raise EngineError('work_ctc_source_changed', 'Original generated allocation changed', 409)
                if table == 'staging' and key == facts[3].candidate.staging_id and (
                        (row['sha256'], row['size'], row['media_type'], row['status']) != (
                            facts[3].candidate.sha256, facts[3].candidate.size, facts[3].candidate.media_type, 'ready')):
                    raise EngineError('work_ctc_source_changed', 'Original completed staging receipt changed', 409)
                rows.append((table, column, key, dict(row)))
            step = connection.execute('SELECT * FROM steps WHERE run_id=? AND step_key=?', (lease.run_id, body['descriptor']['step_key'])).fetchone()
            expected = {'asset_ids': [], 'result': {'request_sha256': body['request_sha256'],
                'generated_files': [facts[3].model_dump(mode='json')], 'alignment_content_sha256': facts[2].content_sha256,
                'operation_id': facts[5]['id']}}
            if (step is None or step['status'] != 'succeeded' or step['input_sha256'] != body['request_sha256']
                    or strict_json(step['result_json'].encode('utf-8')) != expected):
                raise EngineError('alignment_step_commit_required', 'Original successful committed Step required', 409)
            rows.append(('steps', 'run_id,step_key', (lease.run_id, body['descriptor']['step_key']), dict(step)))
        return rows

    def _committed_ctc_recheck(self, lease, snapshots, selection, selected_id, guard, continuation):
        issuer = self._production_authorization.issuer()
        with self.engine.db.connect_readonly() as connection:
            selected, _run, prod, _req, _binding, _claim = self._committed_ctc_claim(connection, lease, selected_id, continuation)
            current, _rows = self._committed_ctc_select(connection, lease, selected, prod)
            if current != selection:
                raise EngineError('work_ctc_source_changed', 'Nearest committed source changed', 409)
            self.assert_registered_ctc_work_writer(connection, tuple(snapshots))
            if selection is not None:
                self._committed_ctc_guard(connection, lease, selection, selected_id, guard)
            issuer._guard(connection, guard)

    def read_selected_alignment_result(self, lease, continuation):
        result, _snapshot = self._committed_ctc_composition(lease, continuation=continuation)
        return result

    def _validate_composed_ctc_work_source(self, lease, preparation_id, actual, report):
        from video_creator.application.registered_alignment import _parse_request, _check_semantic
        result, snapshot = self._committed_ctc_composition(lease, preparation_id=preparation_id)
        if result is None:
            return None
        raw, alignment, _manifest, observation, method = result
        from video_creator.application.bundles import strict_json
        initial = strict_json(raw).get('format') == 'registered-initial-alignment-request-v1'
        request = _parse_request(raw, initial)
        if (actual.transcript != request.transcript.transcript or type(actual.alignment) is not type(alignment)
                or actual.alignment.model_dump(mode='json', exclude={'precision', 'content_sha256'})
                != alignment.model_dump(mode='json', exclude={'precision', 'content_sha256'})
                or report.execution_identity.model_dump(mode='json') != observation.result_json['execution_identity']
                or report.qualification_ref != request.alignment_registration.registration.method_qualification_ref
                or not {method.operation_ids[0], request.transcript.asr_source.operation_id} <= set(report.operation_ids)):
            raise EngineError('work_ctc_source_invalid', 'Report requires original selected CTC and independent ASR identities', 422)
        _check_semantic(actual.alignment)
        return snapshot
