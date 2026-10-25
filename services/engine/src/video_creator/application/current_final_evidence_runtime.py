"""Original registered Runtime's final-evidence writers and real continuation."""

import hashlib

from video_creator.application.engine import canonical, digest
from video_creator.application.current_final_evidence_journal import (
    PREFIX, parse_journal, prepared_current, reject_conflicting_wait, require_waiting,
)
from video_creator.application.current_production_blockers import bound_context, require_settled, unsettled
from video_creator.domain import contracts as c
from video_creator.domain.bundle import BundlePreparationIntent
from video_creator.domain.current_final_evidence import (
    CurrentFinalEvidenceContinuation, CurrentFinalEvidenceJournal, FinalEvidenceControl,
)
from video_creator.domain.errors import EngineError
from video_creator.domain.component_diagnosis import (
    CurrentFinalDiagnosticSnapshotV1,CurrentFinalDiagnosticJournalV1,CurrentFinalDiagnosticContinuationV1,
)
from video_creator.application.diagnostic_resume import DiagnosticResumeRuntime


def final_journal_model(snapshot):
    return (CurrentFinalDiagnosticJournalV1,'current-production-final-evidence-diagnostic-v1') if type(snapshot) is CurrentFinalDiagnosticSnapshotV1 else (CurrentFinalEvidenceJournal,'current-production-final-evidence-v1')


class CurrentFinalEvidenceRuntime(DiagnosticResumeRuntime):
    def _current_final_execution_facts(self, lease, ports, policy):
        checkpoint = self._final_checkpoint(lease.run_id)
        original_refs = None
        if checkpoint is not None:
            with self.engine.db.connect_readonly() as connection:
                prepared, _run, _production, _request = prepared_current(self.engine, connection, checkpoint)
            assembly = self.bundle._read_final_assembly(prepared, checkpoint.binding)
            if assembly is None:
                candidate = self.bundle._original_final_candidate(prepared, checkpoint, checkpoint.binding)
                if candidate is None:
                    raise EngineError('final_assembly_unavailable', 'Actual original continuation revisions unavailable', 503)
                original = candidate[0]
            else:
                original = assembly
            original_refs = {r.kind: r for r in (*original.creative_revision_refs, original.quality_ref)}
        with self.engine.db.connect_readonly() as connection:
            run = self.engine._lease(connection, lease)
            rows = connection.execute('SELECT * FROM creative_revisions WHERE production_id=? AND run_id=? AND kind IN (?,?) ORDER BY rowid',
                (run['production_id'], lease.run_id, 'plan', 'quality')).fetchall()
        revisions = {}
        for row in rows:
            if digest(row['body']) != row['content_sha256']:
                raise EngineError('production_creative_evidence_invalid', 'Original approved creative bytes changed', 422)
            value = c.CreativeRevision.model_validate_json(row['body'])
            if (value.revision_id, value.kind) != (row['id'], row['kind']):
                raise EngineError('production_creative_evidence_invalid', 'Actual creative identity changed', 422)
            if original_refs is None or (value.kind in original_refs and value.revision_id == original_refs[value.kind].revision_id
                    and row['content_sha256'] == original_refs[value.kind].content_sha256):
                revisions[value.kind] = value
        if set(revisions) != {'plan', 'quality'}:
            raise EngineError('production_creative_capability_missing', 'Actual original plan/quality required', 503)
        admission = ports.production_admission if policy else ports.current_production_admission
        facts = [admission(lease, revisions[phase].revision_id, phase=phase, action=action)
            for phase, action in (('plan', 'execute_plan'), ('quality', 'continue_bundle_validation'))]
        if any(f.state != 'allowed' or f.run_id != lease.run_id or f.fencing_token != lease.fencing_token
               or f.registration_sha256 != self.sha256 for f in facts):
            raise EngineError('production_current_admission_required', 'Original current plan and quality admission required', 403)
        rights = ports.production_rights(lease, revisions['plan'].revision_id) if policy else ports.current_production_rights(lease, revisions['plan'].revision_id)
        return facts[0], facts[1], rights

    def _final_checkpoint(self, run_id):
        with self.engine.db.connect_readonly() as connection:
            row = connection.execute('SELECT value FROM metadata WHERE key=?', (PREFIX + run_id,)).fetchone()
        return None if row is None else parse_journal(row[0], now=self.engine.clock())

    def _final_producer(self, lease, *, production_services, execution_ports, local_material_context=None):
        import inspect
        from video_creator.workflows.bundle_producer import create_registered_media_producer
        if 'final_evidence_ports' not in inspect.signature(create_registered_media_producer).parameters:
            raise EngineError('final_evidence_consumer_missing', 'Original factory has no current held-port interface', 503)
        extra = {}
        if local_material_context is not None:
            from video_creator.application.local_material_sources import LocalMaterialFinalContext
            if type(local_material_context) is not LocalMaterialFinalContext:
                raise EngineError('local_final_context_denied', 'Original local final source projection required.', 403)
            if 'local_material_context' not in inspect.signature(create_registered_media_producer).parameters:
                raise EngineError('production_local_final_consumer_missing', 'Actual local context Media composer is not installed.', 503)
            extra['local_material_context'] = local_material_context
        with self.engine.db.connect_readonly() as connection:
            self.engine._lease(connection, lease)
            _run, _production, _request, binding = bound_context(self.engine, connection, lease.run_id, self.sha256)
        ports = self.bundle.current_final_evidence_ports(lease, binding)
        try:
            ports.assert_production_services(lease, production_services, execution_ports)
            produce = create_registered_media_producer(engine=self.engine, bundle=self.bundle, executor=self.executor,
                resource_manifest_path=self.path.parent / self.config.asr_resource_manifest if self.config.asr_resource_manifest is not None else None,
                resource_manifest_sha256=self.config.asr_resource_manifest_sha256,
                runtime_manifest_sha256=self.config.asr_runtime_manifest_sha256,
                storage_root=self.engine.db.data_dir, runtime_root=self.runtime_root, final_evidence_ports=ports,
                production_services=production_services, **extra)
        except BaseException:
            ports.close()
            raise
        return produce, ports

    def park_current_final_evidence(self, ordinary_lease, assessment):
        lease = ordinary_lease
        now = self.engine.clock()
        issuer = self.bundle._production_authorization.issuer()
        from video_creator.application.diagnostic_terminal import prepare_failure, finite_failure
        with issuer.current_guard(self.bundle._production_authorization.registered(lease)) as preparation_guard, self.engine.db.connect_readonly() as reader:
            self.bundle.assert_current_final_assessment(reader,lease,assessment)
            prepare_failure(self.bundle,reader,lease,assessment,guard=preparation_guard)
        with issuer.current_guard(self.bundle._production_authorization.registered(lease)) as guard, self.engine.db.transaction() as connection:
            issuer._guard(connection, guard)
            old = connection.execute('SELECT value FROM metadata WHERE key=?', (PREFIX + lease.run_id,)).fetchone()
            if old is not None:
                previous = parse_journal(old[0], now=now)
                _row, run, _production, _request = prepared_current(self.engine, connection, previous)
                with self.bundle._lock:
                    saved = self.bundle._final_evidence_assessments.get(id(assessment))
                if saved is None or saved[0] is not assessment or saved[1] != lease:
                    raise EngineError('final_evidence_assessment_denied', 'Actual original assessment required', 403)
                if previous.control.phase == 'waiting' and previous.binding == assessment.binding and previous.snapshot == assessment.snapshot:
                    require_waiting(run, previous)
                    require_settled(connection, lease.run_id)
                    return
                if previous.control.phase != 'executing' or previous.control.execution_fence != lease.fencing_token:
                    raise EngineError('final_evidence_checkpoint_changed', 'Only current executing checkpoint can return to waiting', 409)
            else:
                previous = None
            run = self.engine._lease(connection, lease)
            if run['paused'] or run['cancellation_requested'] or run['waiting_revision_id'] is not None:
                raise EngineError('final_evidence_state_conflict', 'Actual cancellation/pause/human review wins', 409)
            reject_conflicting_wait(connection, lease.run_id)
            require_settled(connection, lease.run_id)
            snapshot = self.bundle.assert_current_final_assessment(connection, lease, assessment)
            with self.bundle._lock:
                diagnostic_association=getattr(self.bundle,'_diagnostic_assessment_sources',{}).get(id(assessment))
            terminal=finite_failure(self.bundle,connection,lease,assessment,guard=guard)
            selection_evidence=None
            if diagnostic_association is not None:
                selection_evidence=self.bundle.commit_current_diagnostic_selection_writer(connection,lease,
                    diagnostic_association[1],transition='park',guard=guard)
            if previous and previous.snapshot.preparation_id != snapshot.preparation_id:
                self.bundle._selected_affected_child(connection, lease.run_id, previous, _row, snapshot.preparation_id)
            journal_type,journal_format=final_journal_model(snapshot)
            journal = journal_type(format=journal_format,
                binding=assessment.binding, snapshot=snapshot,
                control=FinalEvidenceControl(phase='executing',resume_mode='repair',execution_fence=lease.fencing_token) if terminal is not None else FinalEvidenceControl(phase='waiting', resume_mode=None, execution_fence=None),
                blocked_at_us=previous.blocked_at_us if previous else now, last_transition_at_us=now)
            body = canonical(journal)
            if old is None:
                connection.execute('INSERT INTO metadata(key,value) VALUES(?,?)', (PREFIX + lease.run_id, body))
            elif connection.execute('UPDATE metadata SET value=? WHERE key=? AND value=?',
                    (body, PREFIX + lease.run_id, old[0])).rowcount != 1:
                raise EngineError('final_evidence_checkpoint_changed', 'Original checkpoint CAS lost', 409)
            if diagnostic_association is not None:
                self.bundle.write_diagnostic_source_for_assessment(connection,lease,assessment,journal,body,selection_evidence,terminal_failure=terminal)
                with self.bundle._lock:
                    selection=diagnostic_association[1]
                    captured=self.bundle.diagnostic_selection_final_writer(connection,lease,selection,journal_body=body)
                    held=self.bundle._diagnostic_records_held[id(selection.recorded)]
                    self.bundle._diagnostic_records_held[id(selection.recorded)]=(*held[:3],captured,held[4])
            elif previous is not None:
                self.bundle.copy_current_diagnostic_source_writer(connection,old[0],previous,body,journal)
            # All source/action/assessment checks requiring this live lease
            # precede the one original release, in this same transaction.
            if type(snapshot) is CurrentFinalDiagnosticSnapshotV1:
                self.bundle.assert_diagnostic_assessment_writer(connection,lease,snapshot,checkpoint_body=body)
            if diagnostic_association is not None:
                selection=diagnostic_association[1]
                self.bundle.diagnostic_selection_final_writer(connection,lease,selection,journal_body=body)
                if selection.child_transition is not None:
                    self.bundle.assert_selected_affected_child_writer(connection,lease,selection.child_transition,
                        guard=guard,journal_body=body)
            if terminal is not None:
                current_terminal=finite_failure(self.bundle,connection,lease,assessment,guard=guard)
                if current_terminal is None or current_terminal.model_dump(exclude={'committed_at_us'})!=terminal.model_dump(exclude={'committed_at_us'}):
                    raise EngineError('final_evidence_limit_changed','Exact own finite terminal sources changed',409)
            self.bundle.assert_current_final_assessment(connection,lease,assessment)
            self.engine._lease(connection,lease)
            require_settled(connection,lease.run_id)
            issuer._guard(connection,guard)
            status='failed' if terminal is not None else 'waiting_user'
            connection.execute('UPDATE runs SET status=?,waiting_revision_id=NULL,worker_id=NULL,lease_until_us=0 WHERE id=?',(status,lease.run_id))
            connection.execute('UPDATE productions SET status=? WHERE id=?',(status,run['production_id']))
            self.engine._event(connection,self.engine._run(connection,lease.run_id),
                'production.final_evidence_failed' if terminal is not None else 'production.final_evidence_blocked',digest(body))
            # Persistent checks only after release; never revive a lease.
            actual=connection.execute('SELECT value FROM metadata WHERE key=?',(PREFIX+lease.run_id,)).fetchone()
            stopped=self.engine._run(connection,lease.run_id)
            production=self.engine._production(connection,run['production_id'])
            if (actual is None or actual[0]!=body or stopped['status']!=status or production['status']!=status
                    or stopped['worker_id'] is not None or stopped['lease_until_us']!=0):
                raise EngineError('final_evidence_checkpoint_changed','Exact atomic stopped state required',409)
            if diagnostic_association is not None:
                source,_source_row=self.bundle._read_source_writer(connection,body,journal)
                selected=connection.execute('SELECT value FROM metadata WHERE key=?',
                    ('component-diagnostic-selected.'+snapshot.preparation_id,)).fetchone()
                if (source is None or source.diagnostic_ref!=diagnostic_association[1].recorded.ref or selected is None
                        or selected[0]!=selection_evidence.new_selected_body):
                    raise EngineError('diagnostic_source_changed','Stopped journal/source/selected must commit together',409)
                if terminal is not None and source.terminal_failure!=terminal:
                    raise EngineError('diagnostic_source_changed','Exact actual terminal companion required',409)
            issuer._guard(connection,guard)

    def _probe_final_inputs(self, journal, *, exact_raw=None):
        """Immutable original receipts and registry input checks, no provider effects."""
        with self.engine.db.connect_readonly() as connection:
            prepared, _run, production, request = prepared_current(self.engine, connection, journal)
            intent = BundlePreparationIntent.model_validate_json(prepared['intent_json'])
            ready = connection.execute('SELECT * FROM bundle_items WHERE preparation_id=? AND status=?',
                (prepared['id'], 'ready')).fetchall()
            resolved = None
            if isinstance(request, c.ProductionRequestV03):
                resolved = self.engine.evidence_registry.resolve(production['owner'], production['project_id'],
                    request.delivery_requirements.evidence_policy_revision_ref, connection=connection)
        for receipt in journal.snapshot.ready_material_refs:
            path = self.bundle._file('BundleMaterials', receipt.material_id)
            if not path.is_file() or path.stat().st_size != receipt.size or hashlib.sha256(path.read_bytes()).hexdigest() != receipt.sha256:
                raise EngineError('bundle_integrity_failed', 'Original READY bytes changed while waiting', 422)
        sha = journal.snapshot.candidate_manifest_file_sha256
        if sha:
            candidate = self.bundle._file('CurrentFinalCandidates', 'candidate-' + sha)
            if not candidate.is_file() or hashlib.sha256(candidate.read_bytes()).hexdigest() != sha:
                raise EngineError('bundle_integrity_failed', 'Original candidate bytes changed while waiting', 422)
        diagnostic=type(journal) is CurrentFinalDiagnosticJournalV1
        if diagnostic and journal.snapshot.state=='waiting_diagnosis':
            if exact_raw is None:raise EngineError('final_evidence_checkpoint_missing','Exact no-lease waiting body required',409)
            with self.engine.db.connect_readonly() as connection:
                source,_source_row=self.bundle._read_source_writer(connection,exact_raw,journal)
            mode,reason,probe=self.probe_current_diagnostic_resume(journal,exact_raw,source)
            self._pending_diagnostic_probe=probe
            return mode,reason
        if journal.snapshot.repair:
            if journal.snapshot.repair.allowed_action == 'guidance_required':
                return 'guidance_required', journal.snapshot.reason_code
            mode = 'repair'
        else:
            mode = 'retry_final_validation'
        for dep in (() if diagnostic else journal.snapshot.dependencies):
            if dep.completion_kind == 'consume_ready_evidence':
                if dep.kind == 'verifier_resource':
                    if not self.bundle.validators.precision_authorities:
                        return 'still_blocked', dep.reason_code
                elif dep.kind == 'method_qualification':
                    if resolved is None:
                        return 'still_blocked', dep.reason_code
                elif not dep.target_artifact_id or not any(row['artifact_id'] == dep.target_artifact_id for row in ready):
                    return 'still_blocked', dep.reason_code
            else:
                if resolved is None:
                    return 'still_blocked', 'evidence_authority_unconfigured'
                if dep.kind == 'precision_measurement' and not any(row['schema_kind'] == 'precision_reference_v03' for row in ready):
                    return 'still_blocked', 'independent_reference_missing'
                # Consumer must actually be installed, not a label/config flag.
                from video_creator.workflows.bundle_producer import create_registered_media_producer
                if (not callable(create_registered_media_producer)
                        or not callable(getattr(self.produce, 'continue_current_final_evidence', None))):
                    return 'still_blocked', 'final_evidence_consumer_missing'
        if len(intent.media_asset_ids) != 4:
            raise EngineError('bundle_output_missing', 'All original masters required', 422)
        assembly = self.bundle._read_final_assembly(prepared, journal.binding)
        if assembly is None:
            candidate = self.bundle._original_final_candidate(prepared, journal, journal.binding)
            if candidate is None:
                return 'still_blocked', 'original_assembly_context_missing'
            methods = [m for m in candidate[0].methods if m.tool_name == 'faster-whisper']
            if len(methods) != 1 or len(methods[0].operation_ids) != 1:
                raise EngineError('asr_result_scope_denied', 'Original candidate must name its ASR Operation', 422)
            operation_id = methods[0].operation_ids[0]
        else:
            operation_id = assembly.asr_operation_id
        if self.journal._probe_waiting_original_asr(journal.binding.run_id, operation_id) is None:
            return 'still_blocked', 'original_asr_validation_context_missing'
        if not callable(getattr(self.produce, 'continue_current_final_evidence', None)):
            return 'still_blocked', 'final_evidence_consumer_missing'
        return mode, None

    def resume_current_final_evidence(self, run_id):
        with self.engine.db.connect_readonly() as connection:
            row = connection.execute('SELECT value FROM metadata WHERE key=?', (PREFIX + run_id,)).fetchone()
            if row is None:
                return 'not_blocked', None
            raw = row[0]
            journal = parse_journal(raw, now=self.engine.clock())
            _prepared, run, production, request = prepared_current(self.engine, connection, journal)
            if run['status'] == 'succeeded':
                return self._observe_crashed_final_publication(journal, raw)
            if run['status']=='failed':
                from video_creator.application.diagnostic_terminal import observe_terminal
                return observe_terminal(self,journal,raw)
            require_waiting(run, journal)
        registered = self.engine._authorization_identity(production['owner'])
        issuer = self.engine.production_admissions
        try:
            with issuer.current_guard(registered) as guard:
                self._pending_diagnostic_probe=None
                mode, reason = self._probe_final_inputs(journal,exact_raw=raw)
                if mode=='needs_reconciliation':
                    # No queued mode, new lease, intent or dispatch is produced.
                    with self.engine.db.transaction() as connection:
                        saved=connection.execute('SELECT value FROM metadata WHERE key=?',(PREFIX+run_id,)).fetchone()
                        if saved is None or saved[0]!=raw:
                            raise EngineError('final_evidence_checkpoint_changed','Original reconciliation source changed',409)
                        _prepared,current,prod,_request=prepared_current(self.engine,connection,journal)
                        require_waiting(current,journal)
                        if current['paused'] or current['cancellation_requested'] or current['waiting_revision_id'] is not None:
                            raise EngineError('final_evidence_state_conflict','Actual pause/cancellation/human review wins',409)
                        reject_conflicting_wait(connection,run_id)
                        issuer._guard(connection,guard);issuer._request(connection,prod,current,registered)
                        if not unsettled(connection,run_id):
                            raise EngineError('production_blocker_reconciliation_changed','Original unknown source changed during probe',409)
                        connection.execute("UPDATE runs SET status='needs_reconciliation' WHERE id=?",(run_id,))
                        connection.execute("UPDATE productions SET status='needs_reconciliation' WHERE id=?",(prod['id'],))
                        self.engine._event(connection,self.engine._run(connection,run_id),'production.final_evidence_reconciliation',digest(raw))
                        issuer._guard(connection,guard)
                    return 'needs_reconciliation',reason
                if mode in {'still_blocked', 'guidance_required'}:
                    return mode, reason
                self._declaration_resume_current(production, request)
                from video_creator.workflows.attempt_control import current_attempt
                current_attempt().check()
                with self.engine.db.transaction() as connection:
                    saved = connection.execute('SELECT value FROM metadata WHERE key=?', (PREFIX + run_id,)).fetchone()
                    if saved is None or saved[0] != raw:
                        raise EngineError('final_evidence_checkpoint_changed', 'Original checkpoint CAS changed', 409)
                    _prepared, current, prod, _request = prepared_current(self.engine, connection, journal)
                    require_waiting(current, journal)
                    reject_conflicting_wait(connection, run_id)
                    issuer.assert_final_evidence_resume_current(connection, guard, run_id=run_id,
                        binding=journal.binding, journal_sha256=digest(raw), resume_mode=mode,
                        affected_artifact_ids=journal.snapshot.repair.affected_artifact_ids if mode == 'repair' else ())
                    if unsettled(connection, run_id):
                        connection.execute("UPDATE runs SET status='needs_reconciliation' WHERE id=?", (run_id,))
                        connection.execute("UPDATE productions SET status='needs_reconciliation' WHERE id=?", (prod['id'],))
                        self.engine._event(connection, self.engine._run(connection, run_id), 'production.final_evidence_reconciliation', digest(raw))
                        issuer._guard(connection, guard)
                        return 'needs_reconciliation', 'production_blocker_reconciliation_required'
                    queued = journal.model_copy(update={'control': FinalEvidenceControl(phase='queued', resume_mode=mode, execution_fence=None),
                        'last_transition_at_us': self.engine.clock()})
                    context=self.commit_diagnostic_probe_writer(connection,self._pending_diagnostic_probe) if self._pending_diagnostic_probe is not None else None
                    queued_body=canonical(queued)
                    if connection.execute('UPDATE metadata SET value=? WHERE key=? AND value=?', (queued_body, PREFIX + run_id, raw)).rowcount!=1:
                        raise EngineError('final_evidence_checkpoint_changed','Original exact queue CAS lost',409)
                    self.bundle.copy_current_diagnostic_source_writer(connection,raw,journal,queued_body,queued,resume_context=context)
                    connection.execute("UPDATE runs SET status='queued' WHERE id=?", (run_id,))
                    connection.execute("UPDATE productions SET status='queued' WHERE id=?", (prod['id'],))
                    self.engine._event(connection, self.engine._run(connection, run_id), 'production.final_evidence_resumed', digest(raw))
                    issuer._guard(connection, guard)
                return 'queued', None
        except EngineError as error:
            if error.status_code in {403, 503}:
                return 'still_blocked', error.code
            raise

    def _observe_crashed_final_publication(self, journal, raw):
        """Publisher committed before worker checkpoint cleanup; observe only."""
        run_id = journal.binding.run_id
        with self.engine.db.connect_readonly() as connection:
            published = connection.execute('SELECT * FROM bundle_revisions WHERE run_id=? AND production_id=? AND status=? ORDER BY rowid DESC LIMIT 1',
                (run_id, journal.binding.production_id, 'published')).fetchone()
        if published is None or not published['manifest_file_key'] or not published['manifest_json']:
            raise EngineError('final_evidence_publication_unobserved', 'Actual immutable publisher receipt required', 409)
        path = self.bundle._file('BundleManifests', published['manifest_file_key'])
        data = path.read_bytes()
        if data != published['manifest_json'].encode('utf-8') or hashlib.sha256(data).hexdigest() != published['manifest_sha256']:
            raise EngineError('bundle_integrity_failed', 'Actual published manifest bytes changed', 422)
        with self.engine.db.transaction() as connection:
            saved = connection.execute('SELECT value FROM metadata WHERE key=?', (PREFIX + run_id,)).fetchone()
            if saved is None:
                return 'not_blocked', None
            if saved[0] != raw:
                raise EngineError('final_evidence_checkpoint_changed', 'Original checkpoint CAS changed', 409)
            _prepared, run, _production, _request = prepared_current(self.engine, connection, journal)
            actual = connection.execute('SELECT * FROM bundle_revisions WHERE id=? AND run_id=? AND status=?',
                (published['id'], run_id, 'published')).fetchone()
            if run['status'] != 'succeeded' or actual is None or actual['manifest_sha256'] != published['manifest_sha256']:
                raise EngineError('final_evidence_publication_unobserved', 'Original actual committed publisher result required', 409)
            if actual['id'] != _prepared['id']:
                self.bundle._selected_affected_child(connection, run_id, journal, _prepared, actual['id'])
            connection.execute('DELETE FROM metadata WHERE key=? AND value=?', (PREFIX + run_id, raw))
            self.engine._event(connection, run, 'production.final_evidence_published', digest(raw))
        return 'not_blocked', None

    def claim_current_final_evidence(self, ordinary_lease):
        lease = ordinary_lease
        with self.engine.db.connect_readonly() as connection:
            run = self.engine._lease(connection, lease)
            owner = self.engine._production(connection, run['production_id'])['owner']
        issuer = self.engine.production_admissions
        with issuer.current_guard(self.engine._authorization_identity(owner)) as guard:
            with self.engine.db.transaction() as connection:
                saved = connection.execute('SELECT value FROM metadata WHERE key=?', (PREFIX + lease.run_id,)).fetchone()
                if saved is None:
                    raise EngineError('final_evidence_checkpoint_missing', 'Actual queued checkpoint required', 409)
                journal = parse_journal(saved[0], now=self.engine.clock())
                _prepared, run, _production, _request = prepared_current(self.engine, connection, journal)
                self.engine._lease(connection, lease)
                require_settled(connection, lease.run_id)
                if (journal.control.phase not in {'queued', 'executing'} or run['paused'] or run['cancellation_requested']
                        or run['waiting_revision_id'] is not None
                        or (journal.control.phase == 'executing' and journal.control.execution_fence > lease.fencing_token)):
                    raise EngineError('final_evidence_state_conflict', 'Original queue/new lease recovery required', 409)
                mode = journal.control.resume_mode
                issuer.assert_final_evidence_resume_current(connection, guard, run_id=lease.run_id,
                    binding=journal.binding, journal_sha256=digest(saved[0]), resume_mode=mode,
                    affected_artifact_ids=journal.snapshot.repair.affected_artifact_ids if mode == 'repair' else ())
                claimed = journal.model_copy(update={'control': FinalEvidenceControl(phase='executing', resume_mode=mode,
                    execution_fence=lease.fencing_token), 'last_transition_at_us': self.engine.clock()})
                claimed_body=canonical(claimed)
                if connection.execute('UPDATE metadata SET value=? WHERE key=? AND value=?',
                    (claimed_body, PREFIX + lease.run_id, saved[0])).rowcount!=1:
                    raise EngineError('final_evidence_checkpoint_changed','Original exact claim CAS lost',409)
                self.bundle.copy_current_diagnostic_source_writer(connection,saved[0],journal,claimed_body,claimed)
                self.engine._event(connection, run, 'production.final_evidence_claimed', digest(saved[0]))
                issuer._guard(connection, guard)
        continuation_type=CurrentFinalDiagnosticContinuationV1 if type(journal) is CurrentFinalDiagnosticJournalV1 else CurrentFinalEvidenceContinuation
        return continuation_type(journal.binding, journal.snapshot, mode, lease.fencing_token)

    def finish_current_final_evidence_failed(self, ordinary_lease, assessment):
        lease = ordinary_lease
        issuer=self.bundle._production_authorization.issuer()
        from video_creator.application.diagnostic_terminal import prepare_failure,finite_failure
        with issuer.current_guard(self.bundle._production_authorization.registered(lease)) as preparation_guard, self.engine.db.connect_readonly() as reader:
            self.bundle.assert_current_final_assessment(reader,lease,assessment)
            with self.bundle._lock:original_association=getattr(self.bundle,'_diagnostic_assessment_sources',{}).get(id(assessment))
            if original_association is not None and original_association[1].selection_kind!='retain':
                raise EngineError('diagnostic_selection_commit_required','Pending diagnosis must use the original atomic park',409)
            prepare_failure(self.bundle,reader,lease,assessment,guard=preparation_guard)
        with issuer.current_guard(self.bundle._production_authorization.registered(lease)) as guard, self.engine.db.transaction() as connection:
            snapshot = self.bundle.assert_current_final_assessment(connection, lease, assessment)
            run, production, request, _binding = bound_context(self.engine, connection, lease.run_id, self.sha256)
            self.engine._lease(connection, lease)
            require_settled(connection, lease.run_id)
            if snapshot.repair is None or snapshot.repair.allowed_action == 'guidance_required':
                raise EngineError('final_evidence_guidance_required', 'Guidance is not a finite ledger failure', 409)
            if run['paused'] or run['cancellation_requested'] or run['waiting_revision_id'] is not None:
                raise EngineError('final_evidence_state_conflict','Actual pause/cancellation/human review wins',409)
            terminal=finite_failure(self.bundle,connection,lease,assessment,guard=guard)
            if terminal is None:
                raise EngineError('final_evidence_limit_not_reached','Actual finite failure and minimum approved cap required',409)
            reject_conflicting_wait(connection, lease.run_id)
            saved = connection.execute('SELECT value FROM metadata WHERE key=?', (PREFIX + lease.run_id,)).fetchone()
            with self.bundle._lock:association=getattr(self.bundle,'_diagnostic_assessment_sources',{}).get(id(assessment))
            evidence=self.bundle.retain_failed_diagnostic_selection_writer(connection,lease,association[1]) if association is not None else None
            previous=None
            if saved is None:
                now = self.engine.clock()
                journal_type,journal_format=final_journal_model(snapshot)
                journal = journal_type(format=journal_format,
                    binding=assessment.binding, snapshot=snapshot,
                    control=FinalEvidenceControl(phase='executing', resume_mode='repair', execution_fence=lease.fencing_token),
                    blocked_at_us=now, last_transition_at_us=now)
                body=canonical(journal)
                connection.execute('INSERT INTO metadata(key,value) VALUES(?,?)', (PREFIX + lease.run_id, body))
            else:
                journal = parse_journal(saved[0], now=self.engine.clock())
                if journal.control.phase != 'executing' or journal.control.execution_fence != lease.fencing_token:
                    raise EngineError('final_evidence_checkpoint_changed', 'Only original current executing failure can finish', 409)
                previous=journal
                if journal.snapshot.preparation_id!=snapshot.preparation_id:
                    raise EngineError('diagnostic_source_changed','Failure finalization must retain the actual current selected preparation',409)
                journal_type,journal_format=final_journal_model(snapshot)
                journal=journal_type(format=journal_format,binding=assessment.binding,snapshot=snapshot,
                    control=journal.control,blocked_at_us=journal.blocked_at_us,last_transition_at_us=self.engine.clock())
                body=canonical(journal)
                if connection.execute('UPDATE metadata SET value=? WHERE key=? AND value=?',(body,PREFIX+lease.run_id,saved[0])).rowcount!=1:
                    raise EngineError('final_evidence_checkpoint_changed','Original exact failed finalization CAS lost',409)
            if association is not None:
                self.bundle.write_diagnostic_source_for_assessment(connection,lease,assessment,journal,body,evidence,terminal_failure=terminal)
                captures=self.bundle.diagnostic_selection_final_writer(connection,lease,association[1],journal_body=body)
                with self.bundle._lock:
                    held=self.bundle._diagnostic_records_held[id(association[1].recorded)]
                    self.bundle._diagnostic_records_held[id(association[1].recorded)]=(*held[:3],captures,held[4])
            elif previous is not None:
                self.bundle.copy_current_diagnostic_source_writer(connection,saved[0],previous,body,journal)
            if type(snapshot) is CurrentFinalDiagnosticSnapshotV1:
                self.bundle.assert_diagnostic_assessment_writer(connection,lease,snapshot,checkpoint_body=body)
            # Retain-only finish never calls the selection commit writer.
            if association is not None:
                self.bundle.diagnostic_selection_final_writer(connection,lease,association[1],journal_body=body)
            current_terminal=finite_failure(self.bundle,connection,lease,assessment,guard=guard)
            if current_terminal is None or current_terminal.model_dump(exclude={'committed_at_us'})!=terminal.model_dump(exclude={'committed_at_us'}):
                raise EngineError('final_evidence_limit_changed','Original retained finite source changed',409)
            self.bundle.assert_current_final_assessment(connection,lease,assessment)
            self.engine._lease(connection,lease)
            require_settled(connection,lease.run_id)
            issuer._guard(connection,guard)
            connection.execute("UPDATE runs SET status='failed',worker_id=NULL,lease_until_us=0 WHERE id=?", (lease.run_id,))
            connection.execute("UPDATE productions SET status='failed' WHERE id=?", (production['id'],))
            self.engine._event(connection, self.engine._run(connection, lease.run_id), 'production.final_evidence_failed',
                snapshot.repair.diagnostic_ref.content_sha256 if type(snapshot) is CurrentFinalDiagnosticSnapshotV1 else snapshot.repair.source_report_ref.sha256)
            stopped=self.engine._run(connection,lease.run_id)
            actual=connection.execute('SELECT value FROM metadata WHERE key=?',(PREFIX+lease.run_id,)).fetchone()
            if (stopped['status']!='failed' or stopped['worker_id'] is not None or stopped['lease_until_us']!=0
                    or self.engine._production(connection,production['id'])['status']!='failed' or actual is None or actual[0]!=body):
                raise EngineError('final_evidence_checkpoint_changed','Exact retained stopped failure required',409)
            if association is not None:
                source,_saved_source=self.bundle._read_source_writer(connection,body,journal)
                if source is None or source.terminal_failure!=terminal:
                    raise EngineError('diagnostic_source_changed','Exact retained terminal companion required',409)
            issuer._guard(connection,guard)

    def observe_current_final_publication(self, result):
        if result.state != 'published' or result.bundle_ref is None:
            return
        with self.engine.db.transaction() as connection:
            saved = connection.execute('SELECT value FROM metadata WHERE key=?', (PREFIX + result.manifest.run_id,)).fetchone()
            if saved is None:
                return
            journal = parse_journal(saved[0], now=self.engine.clock())
            row, run, _production, _request = prepared_current(self.engine, connection, journal)
            published = connection.execute('SELECT * FROM bundle_revisions WHERE id=? AND run_id=? AND status=?',
                (result.preparation_id, run['id'], 'published')).fetchone()
            if published is None or published['manifest_sha256'] != result.bundle_ref.manifest_sha256:
                raise EngineError('final_evidence_publication_unobserved', 'Only original actual publication clears checkpoint', 409)
            if published['id'] != row['id']:
                self.bundle._selected_affected_child(connection, run['id'], journal, row, published['id'])
            connection.execute('DELETE FROM metadata WHERE key=? AND value=?', (PREFIX + run['id'], saved[0]))
            self.engine._event(connection, run, 'production.final_evidence_published', digest(saved[0]))
