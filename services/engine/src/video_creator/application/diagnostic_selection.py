"""Original outcome join and same-connection diagnostic selection/history."""
import hashlib
import threading
import time

from pydantic import ValidationError

from video_creator.application.engine import canonical, digest
from video_creator.application.affected_repair_service import canonical_body
from video_creator.application.current_final_evidence_journal import PREFIX, parse_journal
from video_creator.domain import contracts as c
from video_creator.domain.component_diagnosis import (
    ComponentDiagnosisRefV1, CurrentFinalDiagnosticSnapshotV1, DiagnosticRepairSourceV1,
)
from video_creator.domain.diagnostic_recovery import (
    DiagnosticMetadataRef, RegisteredDiagnosticInputRef, PreparedDiagnosticSelection,
    HeldDiagnosticOutcome, CurrentDiagnosticSourceRead, DiagnosticSelectionEvidence,
    CurrentFinalDiagnosticSourceV1, CurrentFinalDiagnosticSourceV2, QualityFailureFacts,
    CurrentQualityFailure, CurrentFinalDiagnosticSourceV3, DiagnosticResumeContext,
)
from video_creator.domain.errors import EngineError
from video_creator.domain.plan_repair_targets import plan_payload_bytes

SOURCE_PREFIX='current_final_diagnostic_source:'
SELECT_PREFIX='component-diagnostic-selected.'
INPUT_PREFIX='component-diagnostic-input.'
RESULT_PREFIX='component-diagnostic-result.'


def source_key(run_id, raw):
    return SOURCE_PREFIX+run_id+':'+digest(raw)


def parse_source(raw):
    from video_creator.application.bundles import strict_json
    try:
        value=strict_json(raw.encode('utf-8'))
        if not isinstance(value,dict):raise ValueError('Source object required')
        model={'current-final-diagnostic-source-v1':CurrentFinalDiagnosticSourceV1,
            'current-final-diagnostic-source-v2':CurrentFinalDiagnosticSourceV2,
            'current-final-diagnostic-source-v3':CurrentFinalDiagnosticSourceV3}.get(value.get('format'))
        if model is None:raise ValueError('Unknown diagnostic source grammar')
        return model.model_validate_json(raw)
    except (ValidationError,ValueError,TypeError):
        raise EngineError('diagnostic_source_invalid','Strict complete diagnostic source required',422) from None


class DiagnosticSelectionService:
    def prepare_selected_affected_child_transition(self, connection, lease, *, current_parent_journal, child_preparation_id, recorded):
        from video_creator.application.diagnostic_terminal import prepare_child
        return prepare_child(self, connection, lease, current_parent_journal=current_parent_journal,
            child_preparation_id=child_preparation_id, recorded=recorded)

    def assert_selected_affected_child_writer(self, connection, lease, transition, *, guard, journal_body=None):
        from video_creator.application.diagnostic_terminal import assert_child_writer
        return assert_child_writer(self, connection, lease, transition, guard=guard, journal_body=journal_body)

    def _diagnostic_v2_inputs(self, lease, row, inputs, stable, raw):
        """Read original committed completion facts; never dispatch or settle."""
        from video_creator.domain.diagnostic_recovery import (
            RegisteredDiagnosticEnvelopeV2, RegisteredComponentDiagnosisInputsV2,
        )
        if not isinstance(raw,str) or len(raw.encode('utf-8'))>2*1024*1024:
            raise EngineError('diagnostic_source_invalid','Finite original registered completion input required',422)
        try:envelope=RegisteredDiagnosticEnvelopeV2.model_validate_json(raw)
        except ValidationError:
            raise EngineError('diagnostic_source_invalid','Strict original registered completion input required',422) from None
        value=envelope.stable.model_dump(mode='json')
        original=dict(value)
        original.pop('completion_source_refs')
        original['format']='current-component-diagnostic-input-v1'
        if plan_payload_bytes(original)!=plan_payload_bytes(stable):
            raise EngineError('diagnostic_source_changed','Completion input must retain all original source facts',409)
        key=digest(plan_payload_bytes(envelope.stable))
        intents=tuple(c.OperationIntent(step_key='component-diagnosis-'+key[:32]+'-'+digest(plan_payload_bytes(method))[:16],
            dedupe_key='component-diagnosis-'+key[:32]+'-'+digest(plan_payload_bytes(method))[:16],
            input_sha256=digest(plan_payload_bytes({'input_key_sha256':key,'method_ref':method.model_dump(mode='json')})),
            route_id=method.route.route_id,reserved_cost=method.route.max_operation_cost) for method in inputs.diagnostic_method_refs)
        if envelope.analysis_intents!=intents or raw!=plan_payload_bytes(envelope).decode('utf-8'):
            raise EngineError('diagnostic_source_changed','Original completion input bytes and registered intents changed',409)
        captures=[]
        from video_creator.application.bundles import validate_text
        with self.engine.db.connect_readonly() as connection:
            self.engine._lease(connection,lease)
            _prepared,_run,production,_request=self._preparation(connection,lease,row['id'])
            for completion in envelope.stable.completion_source_refs:
                if completion.kind=='ready_material':
                    ref=completion.ref
                    receipt=next((receipt for receipt,_body in inputs.parent.materials if receipt==ref),None)
                    if receipt is None or ref.preparation_id!=row['id']:
                        raise EngineError('diagnostic_source_changed','Original completion must be an actual current READY receipt',409)
                    body=self.read_material(lease,row['id'],ref.material_id)
                    if (len(body),hashlib.sha256(body).hexdigest())!=(ref.size,ref.sha256):
                        raise EngineError('bundle_integrity_failed','Completion material bytes changed',422)
                    validate_text(body,ref.schema_kind,ref.media_type)
                elif completion.kind=='feedback':
                    ref=completion.ref
                    saved=connection.execute('SELECT * FROM feedback_revisions WHERE id=? AND production_id=? AND new_run_id=?',
                        (ref.revision_id,production['id'],lease.run_id)).fetchone()
                    if saved is None or digest(saved['body'])!=ref.content_sha256:
                        raise EngineError('diagnostic_source_changed','Original accepted feedback source changed',409)
                    feedback=c.FeedbackRevision.model_validate_json(saved['body'])
                    if feedback.new_run_id!=lease.run_id or not feedback.instruction_text.strip() or feedback.target_revision_id not in {value.revision_id for value in inputs.parent.assembly.creative_revision_refs}:
                        raise EngineError('diagnostic_source_denied','Feedback must bind this actual original author source',403)
                    captures.append(('feedback_revisions','id',ref.revision_id,dict(saved)))
                else:
                    raise EngineError('diagnostic_resource_observer_not_ready','Actual qualified installation completion observer required',503)
            self.assert_registered_ctc_work_writer(connection,tuple(captures))
        ref=RegisteredDiagnosticInputRef(record_id=INPUT_PREFIX+key,content_sha256=digest(raw),
            size=len(raw.encode('utf-8')),input_key_sha256=key)
        result=RegisteredComponentDiagnosisInputsV2(key,inputs.binding,inputs.parent_preparation_id,inputs.parent_intent_sha256,
            inputs.parent,inputs.precision_report_ref,inputs.precision_report_bytes,inputs.failed_unit_ids,
            inputs.source_media_refs,inputs.diagnostic_method_refs,intents,envelope.stable.completion_source_refs,ref)
        return result,value,tuple(captures)

    def _prepare_diagnostic_resumed_input(self, lease, preparation_id, continuation, source_read, row, inputs, methods):
        with self._lock:held=getattr(self,'_diagnostic_source_reads',{}).get(id(source_read))
        if held is None or held[0] is not source_read or held[1]!=lease or held[2]!=threading.get_ident() or source_read.execution_fence!=lease.fencing_token:
            raise EngineError('diagnostic_source_denied','Original claimed same-fence source reader required',403)
        source=source_read.source;context=source.resume_context
        if context is None or context.work_kind not in {'reuse_record','analyse_changed_input'} or source.preparation_id!=preparation_id:
            raise EngineError('diagnostic_source_denied','Actual committed analysis continuation required',403)
        with self.engine.db.connect_readonly() as connection:
            self.engine._lease(connection,lease)
            saved=connection.execute('SELECT * FROM metadata WHERE key=?',(context.registered_input_ref.record_id,)).fetchone()
            companion=connection.execute('SELECT * FROM metadata WHERE key=?',(source_read.source_ref.record_id,)).fetchone()
            if saved is None or companion is None or (digest(saved['value']),len(saved['value'].encode('utf-8')))!=(context.registered_input_ref.content_sha256,context.registered_input_ref.size):
                raise EngineError('diagnostic_source_changed','Exact committed registered input missing or changed',409)
            if (digest(companion['value']),len(companion['value'].encode('utf-8')))!=(source_read.source_ref.content_sha256,source_read.source_ref.size):
                raise EngineError('diagnostic_source_changed','Original claimed source companion changed',409)
        from video_creator.domain.diagnostic_recovery import RegisteredDiagnosticEnvelopeV2
        try:envelope=RegisteredDiagnosticEnvelopeV2.model_validate_json(saved['value'])
        except ValidationError:
            raise EngineError('diagnostic_source_invalid','Strict committed completion envelope required',422) from None
        row,inputs,stable=self._diagnostic_input_value(lease,preparation_id,methods,continuation=continuation,
            original_candidate_sha=envelope.stable.candidate_manifest_file_sha256)
        result,value,captures=self._diagnostic_v2_inputs(lease,row,inputs,stable,saved['value'])
        if result.registered_input_ref!=context.registered_input_ref or result.completion_source_refs!=context.completion_source_refs:
            raise EngineError('diagnostic_source_changed','Original resume context and registered completion input disagree',409)
        captures+=(('metadata','key',saved['key'],dict(saved)),('metadata','key',companion['key'],dict(companion)))
        with self._lock:
            if not hasattr(self,'_diagnostic_resumed_captures'):self._diagnostic_resumed_captures={}
            self._diagnostic_resumed_captures[id(result)]=(result,lease,threading.get_ident(),captures)
        return result,value

    def read_diagnostic_completion(self, lease, inputs, completion):
        """Bound producer reads exactly one already registered completion."""
        self._diagnostic_inputs_current(lease,inputs)
        if completion not in getattr(inputs,'completion_source_refs',()):
            raise EngineError('diagnostic_source_denied','Completion outside actual held registered input',403)
        if completion.kind=='ready_material':
            raw=self.read_material(lease,inputs.parent_preparation_id,completion.ref.material_id)
            if (len(raw),hashlib.sha256(raw).hexdigest())!=(completion.ref.size,completion.ref.sha256):
                raise EngineError('bundle_integrity_failed','Original completion bytes changed',422)
        elif completion.kind=='feedback':
            with self.engine.db.connect_readonly() as connection:
                self.engine._lease(connection,lease)
                row=connection.execute('SELECT body FROM feedback_revisions WHERE id=? AND new_run_id=?',
                    (completion.ref.revision_id,lease.run_id)).fetchone()
            if row is None or digest(row[0])!=completion.ref.content_sha256:
                raise EngineError('diagnostic_source_changed','Original completion feedback bytes changed',409)
            raw=row[0].encode('utf-8')
        else:
            raise EngineError('diagnostic_resource_observer_not_ready','Actual installation completion observer required',503)
        self._diagnostic_inputs_current(lease,inputs)
        return raw

    def _register_diagnostic_outcome(self, lease, kind, *, assessment=None, verified=None, quality_failure=None):
        result=HeldDiagnosticOutcome(kind,assessment,verified,quality_failure)
        with self._lock:
            if not hasattr(self,'_diagnostic_outcomes'):self._diagnostic_outcomes={}
            self._diagnostic_outcomes[id(result)]=(result,lease,threading.get_ident(),time.monotonic()+30)
        return result

    def assess_resumed_component_diagnosis(self, lease, continuation, recorded):
        """Rebuild a wait from actual settled analysis, never a Verified token.

        Cleared analysis parks an explicit next-verification context; it never
        creates a Verified token or bypasses the original whole verifier.
        """
        read=self.read_current_final_diagnostic_source(lease,continuation)
        if read is None or read.source.resume_context is None:
            raise EngineError('diagnostic_source_denied','Actual claimed analysis source required',403)
        context=read.source.resume_context
        if context.work_kind not in {'reuse_record','analyse_changed_input'} or recorded.ref.input_key_sha256!=context.registered_input_ref.input_key_sha256:
            raise EngineError('diagnostic_source_changed','Settled analysis must match the committed continuation input',409)
        with self._lock:held=getattr(self,'_diagnostic_records_held',{}).get(id(recorded))
        if held is None or held[0] is not recorded or held[1]!=lease or held[2]!=threading.get_ident():
            raise EngineError('diagnostic_source_denied','Actual current service-verified settled diagnosis required',403)
        source=read.source;fact=recorded.fact
        selection=self.prepare_current_diagnostic_selection(lease,source.preparation_id,recorded,continuation=continuation)
        row,_production,_request,binding,prepared,_intent,_items=self._final_prepared(lease,source.preparation_id)
        if fact.result in {'timing_only','no_component_failure'}:
            if source.original_snapshot is None:
                snapshot=CurrentFinalDiagnosticSnapshotV1(preparation_id=source.preparation_id,
                    preparation_intent_sha256=digest(row['intent_json']),candidate_manifest_file_sha256=source.candidate_manifest_file_sha256,
                    ready_material_refs=prepared.materials,diagnostic_ref=recorded.ref,state='waiting_diagnosis',
                    reason_code='final_validation_required',information_requests=(),repair=None)
            else:
                from video_creator.domain.current_final_evidence import CurrentFinalEvidenceSnapshot
                values=source.original_snapshot.model_dump(mode='json')
                values['ready_material_refs']=[value.model_dump(mode='json') for value in prepared.materials]
                snapshot=CurrentFinalEvidenceSnapshot.model_validate(values)
        else:
            original=source.original_snapshot
            snapshot=CurrentFinalDiagnosticSnapshotV1(preparation_id=source.preparation_id,
                preparation_intent_sha256=digest(row['intent_json']),candidate_manifest_file_sha256=source.candidate_manifest_file_sha256,
                ready_material_refs=prepared.materials,diagnostic_ref=recorded.ref,
                state='repair_required' if fact.result=='component_repair' else 'waiting_diagnosis',
                reason_code=original.reason_code if original else 'bundle_quality_incomplete' if source.origin_kind=='quality_incomplete' else 'analysis_inconclusive',
                information_requests=fact.information_requests,
                repair=DiagnosticRepairSourceV1(diagnostic_ref=recorded.ref,precision_report_ref=fact.precision_report_ref,
                    affected_artifact_ids=fact.affected_artifact_ids,failed_unit_ids=fact.failed_unit_ids,
                    allowed_action='regenerate_affected_media') if fact.result=='component_repair' else None)
        assessment=self._retain_final_assessment(lease,binding,snapshot)
        original_assessment=self._retain_final_assessment(lease,binding,source.original_snapshot) if source.original_snapshot is not None else None
        outcome=self._register_diagnostic_outcome(lease,source.origin_kind,assessment=original_assessment,quality_failure=source.quality_failure)
        with self._lock:
            if not hasattr(self,'_diagnostic_assessment_sources'):self._diagnostic_assessment_sources={}
            self._diagnostic_assessment_sources[id(assessment)]=(assessment,selection,outcome)
            if fact.result in {'timing_only','no_component_failure'} and source.original_snapshot is None:
                from video_creator.domain.diagnostic_recovery import DiagnosticResumeContext
                if not hasattr(self,'_diagnostic_assessment_resume_contexts'):self._diagnostic_assessment_resume_contexts={}
                self._diagnostic_assessment_resume_contexts[id(assessment)]=DiagnosticResumeContext(
                    work_kind='final_validation_after_analysis',previous_waiting_journal_sha256=context.previous_waiting_journal_sha256,
                    previous_diagnostic_ref=source.diagnostic_ref,registered_input_ref=context.registered_input_ref,
                    completion_source_refs=context.completion_source_refs,expected_diagnostic_ref=recorded.ref)
        return assessment

    def _current_diagnostic_record_for_join(self, lease, preparation_id):
        with self._lock:
            key=(lease.run_id,preparation_id,threading.get_ident(),lease.fencing_token)
            cache=getattr(self,'_diagnostic_inputs_active',{})
            entry=cache.get(key)
            active=None
            if entry is not None:
                inputs,owner_lease,owner_thread,owner_port=entry
                held=getattr(self,'_diagnostic_inputs_held',{}).get(id(inputs))
                if (owner_lease==lease and owner_thread==threading.get_ident()
                        and self._final_evidence_ports.get(id(owner_port)) is owner_port
                        and owner_port._service is self and owner_port._lease==lease and owner_port._thread==owner_thread
                        and held is not None and held[0] is inputs and held[1]==lease and held[2]==owner_thread
                        and len(held)>6 and held[6] is owner_port and inputs.parent.execution_fence==lease.fencing_token):
                    active=inputs
                elif cache.get(key) is entry:
                    # Reject stale cache ownership before choosing the original
                    # selected reader; do not swallow its source/current errors.
                    cache.pop(key)
        if active is not None:
            return self.read_recorded_component_diagnosis(lease,active)
        with self.engine.db.connect_readonly() as connection:
            self.engine._lease(connection,lease)
            selected=connection.execute('SELECT value FROM metadata WHERE key=?',(SELECT_PREFIX+preparation_id,)).fetchone()
        if selected is None:return None
        ref=ComponentDiagnosisRefV1.model_validate_json(selected[0])
        return self._read_explicit_diagnostic_record(lease,ref,preparation_id)

    def _current_quality_failure(self, lease, manifest, quality, required_checks):
        """Only called at the exact original bundle_quality_incomplete throw."""
        if not self._in_current_final_evidence():return
        with self._lock:scope=self._final_evidence_scopes.get(threading.get_ident())
        if scope is None or scope[0]!=lease:return
        preparation_id=scope[1]
        record=self._current_diagnostic_record_for_join(lease,preparation_id)
        if record is None or record.fact.result not in {'component_repair','information_required'}:return
        row,_production,_request,_binding,prepared,_intent,_items=self._final_prepared(lease,preparation_id)
        from video_creator.application.bundles import validate_text
        matches=[receipt for receipt in prepared.materials if receipt.schema_kind=='quality']
        if len(matches)!=1:return
        receipt=matches[0];raw=self.read_material(lease,preparation_id,receipt.material_id)
        document=validate_text(raw,receipt.schema_kind,receipt.media_type)
        if document!=quality or document.quality_revision_ref!=manifest.quality_ref:return
        facts=QualityFailureFacts(quality_material_ref=receipt,quality_body_sha256=hashlib.sha256(raw).hexdigest(),
            quality_ref=manifest.quality_ref,required_check_ids=tuple(sorted(required_checks)),
            incomplete_check_ids=tuple(sorted(required_checks-{check.check_id for check in quality.checks if check.status=='verified'})))
        outcome=self._register_diagnostic_outcome(lease,'quality_incomplete',quality_failure=facts)
        raise CurrentQualityFailure(EngineError('bundle_quality_incomplete','All server-required checks need actual evidence',422),outcome)

    def join_current_final_diagnosis(self, lease, preparation_id, manifest, *, outcome, diagnostic):
        with self._lock:held=getattr(self,'_diagnostic_outcomes',{}).get(id(outcome))
        if held is None or held[0] is not outcome or held[1]!=lease or held[2]!=threading.get_ident() or time.monotonic()>=held[3]:
            raise EngineError('diagnostic_outcome_denied','Only the real original once-verifier outcome is usable',403)
        if diagnostic is None:
            if outcome.kind=='quality_incomplete':raise EngineError('bundle_quality_incomplete','Actual original QC failure remains',422)
            return outcome.assessment
        selection=self.prepare_current_diagnostic_selection(lease,preparation_id,diagnostic)
        fact=diagnostic.fact
        original=outcome.assessment.snapshot if outcome.assessment is not None else None
        if original and original.repair and (fact.precision_report_ref!=original.repair.source_report_ref or fact.failed_unit_ids!=original.repair.failed_unit_ids):
            raise EngineError('diagnostic_source_changed','Original diagnosis must retain the actual failed precision source',409)
        if fact.result in {'timing_only','no_component_failure'}:
            if outcome.kind=='quality_incomplete':raise EngineError('bundle_quality_incomplete','Original QC is still incomplete',422)
            assessment=outcome.assessment
            if selection.child_transition is not None and outcome.verified is not None:
                row,_production,_request,binding,prepared,_intent,_items=self._final_prepared(lease,preparation_id)
                raw=(canonical(manifest)+'\n').encode('utf-8');candidate_sha=hashlib.sha256(raw).hexdigest()
                self._write('CurrentFinalCandidates','candidate-'+candidate_sha,raw)
                snapshot=CurrentFinalDiagnosticSnapshotV1(preparation_id=preparation_id,
                    preparation_intent_sha256=digest(row['intent_json']),candidate_manifest_file_sha256=candidate_sha,
                    ready_material_refs=prepared.materials,diagnostic_ref=diagnostic.ref,state='waiting_diagnosis',
                    reason_code='final_validation_required',information_requests=(),repair=None)
                assessment=self._retain_final_assessment(lease,binding,snapshot)
                context=DiagnosticResumeContext(work_kind='final_validation_after_analysis',
                    previous_waiting_journal_sha256=digest(selection.old_journal_body),previous_diagnostic_ref=None,
                    registered_input_ref=selection.registered_input_ref,completion_source_refs=(),expected_diagnostic_ref=diagnostic.ref)
                with self._lock:
                    if not hasattr(self,'_diagnostic_assessment_resume_contexts'):self._diagnostic_assessment_resume_contexts={}
                    self._diagnostic_assessment_resume_contexts[id(assessment)]=context
        else:
            row,_production,_request,binding,prepared,_intent,_items=self._final_prepared(lease,preparation_id)
            raw=(canonical(manifest)+'\n').encode('utf-8');candidate_sha=hashlib.sha256(raw).hexdigest()
            self._write('CurrentFinalCandidates','candidate-'+candidate_sha,raw)
            snapshot=CurrentFinalDiagnosticSnapshotV1(preparation_id=preparation_id,
                preparation_intent_sha256=digest(row['intent_json']),candidate_manifest_file_sha256=candidate_sha,
                ready_material_refs=prepared.materials,diagnostic_ref=diagnostic.ref,
                state='repair_required' if fact.result=='component_repair' else 'waiting_diagnosis',
                reason_code=original.reason_code if original else 'bundle_quality_incomplete' if outcome.kind=='quality_incomplete' else 'analysis_inconclusive',
                information_requests=fact.information_requests,
                repair=DiagnosticRepairSourceV1(diagnostic_ref=diagnostic.ref,precision_report_ref=fact.precision_report_ref,
                    affected_artifact_ids=fact.affected_artifact_ids,failed_unit_ids=fact.failed_unit_ids,
                    allowed_action='regenerate_affected_media') if fact.result=='component_repair' else None)
            assessment=self._retain_final_assessment(lease,binding,snapshot)
        with self._lock:
            if not hasattr(self,'_diagnostic_assessment_sources'):self._diagnostic_assessment_sources={}
            self._diagnostic_assessment_sources[id(assessment)]=(assessment,selection,outcome)
            if assessment.verified_material is not None:
                if not hasattr(self,'_diagnostic_verified_selections'):self._diagnostic_verified_selections={}
                self._diagnostic_verified_selections[assessment.verified_material.verification_id]=selection
        return assessment

    def _read_source_writer(self, connection, journal_raw, journal):
        key=source_key(journal.binding.run_id,journal_raw)
        saved=connection.execute('SELECT * FROM metadata WHERE key=?',(key,)).fetchone()
        if saved is None:return None,None
        source=parse_source(saved['value'])
        snapshot=journal.snapshot
        if (source.binding!=journal.binding or source.journal_sha256!=digest(journal_raw)
                or source.snapshot_sha256!=digest(canonical(snapshot)) or source.preparation_id!=snapshot.preparation_id
                or source.preparation_intent_sha256!=snapshot.preparation_intent_sha256
                or source.candidate_manifest_file_sha256!=snapshot.candidate_manifest_file_sha256
                or source.ready_material_refs!=snapshot.ready_material_refs):
            raise EngineError('diagnostic_source_changed','Exact journal/source/snapshot association changed',409)
        if type(source) is CurrentFinalDiagnosticSourceV3:
            from video_creator.application.diagnostic_terminal import read_child_history, read_source_chain
            read_child_history(self, connection, source)
            read_source_chain(self, connection, source)
        return source,saved

    def prepare_current_diagnostic_selection(self, lease, preparation_id, recorded, *, continuation=None):
        with self._lock:held=getattr(self,'_diagnostic_records_held',{}).get(id(recorded))
        if held is None or held[0] is not recorded or held[1]!=lease or held[2]!=threading.get_ident():
            raise EngineError('diagnostic_selection_denied','Actual service-held verified record required',403)
        if recorded.fact.parent_preparation_id!=preparation_id:raise EngineError('diagnostic_source_changed','Different preparation cannot select a fact',409)
        with self.engine.db.connect_readonly() as connection:
            self.engine._lease(connection,lease)
            self.assert_registered_ctc_work_writer(connection,held[3])
            old=connection.execute('SELECT * FROM metadata WHERE key=?',(SELECT_PREFIX+preparation_id,)).fetchone()
            waiting=connection.execute('SELECT * FROM metadata WHERE key=?',(PREFIX+lease.run_id,)).fetchone()
            previous=None;source_row=None;child_transition=None
            if waiting is not None:
                journal=parse_journal(waiting['value'],now=self.engine.clock())
                previous,source_row=self._read_source_writer(connection,waiting['value'],journal)
                if journal.control.phase!='executing' or journal.control.execution_fence!=lease.fencing_token:
                    raise EngineError('final_evidence_claim_required','Actual executing current selection required',409)
                if journal.snapshot.preparation_id!=preparation_id:
                    child_transition=self.prepare_selected_affected_child_transition(connection,lease,
                        current_parent_journal=journal,child_preparation_id=preparation_id,recorded=recorded)
            old_ref=ComponentDiagnosisRefV1.model_validate_json(old['value']) if old is not None else None
            if old_ref is not None:
                self._read_diagnosis_ref_writer(connection,lease,old_ref,held[4]) if old_ref==recorded.ref else self._strict_historical_selected_writer(connection,old_ref,recorded.fact.binding,preparation_id)
            if previous and child_transition is None and previous.diagnostic_ref!=old_ref:
                raise EngineError('diagnostic_source_changed','Original source and whole selected body disagree',409)
            kind='first_select' if old_ref is None else 'retain' if old_ref==recorded.ref else 'successor'
            if child_transition is not None and kind=='successor':
                raise EngineError('diagnostic_selection_denied','Parent repair cannot grant a child successor',409)
            if kind=='successor':
                context=previous.resume_context if previous else None
                if (context is None or context.previous_diagnostic_ref!=old_ref
                        or context.registered_input_ref.input_key_sha256!=recorded.ref.input_key_sha256
                        or not context.completion_source_refs or old_ref.input_key_sha256==recorded.ref.input_key_sha256):
                    raise EngineError('diagnostic_selection_denied','Only the actual changed-input continuation may select a successor',409)
            input_key=INPUT_PREFIX+recorded.ref.input_key_sha256
            input_row=connection.execute('SELECT * FROM metadata WHERE key=?',(input_key,)).fetchone()
            index=connection.execute('SELECT * FROM metadata WHERE key=?',(RESULT_PREFIX+recorded.ref.input_key_sha256,)).fetchone()
            if input_row is None or index is None or ComponentDiagnosisRefV1.model_validate_json(index['value'])!=recorded.ref:
                raise EngineError('diagnostic_source_changed','Original input and its unique result index required',409)
            captured=held[3]+tuple(('metadata','key',key,dict(value) if value is not None else None) for key,value in (
                (SELECT_PREFIX+preparation_id,old),(PREFIX+lease.run_id,waiting),(input_key,input_row),(RESULT_PREFIX+recorded.ref.input_key_sha256,index)))
            if child_transition is not None:
                with self._lock:captured+=self._diagnostic_child_transitions[id(child_transition)][4]
            if source_row is not None:captured+=(('metadata','key',source_row['key'],dict(source_row)),)
        registered=RegisteredDiagnosticInputRef(record_id=input_key,content_sha256=digest(input_row['value']),
            size=len(input_row['value'].encode('utf-8')),input_key_sha256=recorded.ref.input_key_sha256)
        source_ref=DiagnosticMetadataRef(record_id=source_row['key'],content_sha256=digest(source_row['value']),size=len(source_row['value'].encode('utf-8'))) if source_row else None
        selection=PreparedDiagnosticSelection(recorded.fact.binding,preparation_id,recorded,registered,kind,
            old['value'] if old else None,waiting['value'] if waiting else None,source_row['value'] if source_row else None,source_ref,child_transition)
        with self._lock:
            if not hasattr(self,'_diagnostic_selections'):self._diagnostic_selections={}
            self._diagnostic_selections[id(selection)]=(selection,lease,threading.get_ident(),time.monotonic()+30,captured)
        return selection

    def _strict_historical_selected_writer(self, connection, ref, binding, preparation_id):
        from video_creator.domain.component_diagnosis import ComponentDiagnosticFactV1
        row=connection.execute('SELECT value FROM metadata WHERE key=?',(ref.record_id,)).fetchone()
        if row is None or (len(row[0].encode('utf-8')),digest(row[0]))!=(ref.size,ref.content_sha256):
            raise EngineError('diagnostic_source_invalid','Original immutable selected fact damaged',422)
        fact=ComponentDiagnosticFactV1.model_validate_json(row[0])
        if fact.binding!=binding or fact.parent_preparation_id!=preparation_id or fact.input_key_sha256!=ref.input_key_sha256:
            raise EngineError('diagnostic_source_changed','Original selected identity is not this preparation',409)
        return fact

    def commit_current_diagnostic_selection_writer(self, connection, lease, selection, *, transition, guard=None):
        with self._lock:held=getattr(self,'_diagnostic_selections',{}).get(id(selection))
        if held is None or held[0] is not selection or held[1]!=lease or held[2]!=threading.get_ident() or time.monotonic()>=held[3]:
            raise EngineError('diagnostic_selection_denied','Current held selection is required at original writer',403)
        self.engine._lease(connection,lease)
        if self._final_binding(lease,connection)!=selection.binding:
            raise EngineError('diagnostic_source_changed','Original selection binding changed',409)
        self.assert_registered_ctc_work_writer(connection,held[4])
        if selection.child_transition is not None:
            if transition != 'park':
                raise EngineError('diagnostic_selection_denied','Child selection commits only at the original park',409)
            issuer=self._production_authorization.issuer()
            issuer._guard(connection,guard)
            self.assert_selected_affected_child_writer(connection,lease,selection.child_transition,guard=guard)
        if transition=='first_publish' and (selection.selection_kind!='first_select' or selection.old_journal_body is not None
                or selection.old_selected_body is not None or selection.recorded.fact.result in {'component_repair','information_required'}):
            raise EngineError('diagnostic_selection_denied','Publication only commits a first successful absent selection',409)
        if transition not in {'park','first_publish'}:raise EngineError('diagnostic_selection_denied','Original writer transition required',403)
        body=plan_payload_bytes(selection.recorded.ref).decode('utf-8');key=SELECT_PREFIX+selection.preparation_id
        if selection.selection_kind=='first_select':
            if connection.execute('SELECT 1 FROM metadata WHERE key=?',(key,)).fetchone() is not None:
                raise EngineError('diagnostic_selection_conflict','Original selected absence CAS lost',409)
            connection.execute('INSERT INTO metadata(key,value) VALUES(?,?)',(key,body))
        elif selection.selection_kind=='successor':
            if connection.execute('UPDATE metadata SET value=? WHERE key=? AND value=?',(body,key,selection.old_selected_body)).rowcount!=1:
                raise EngineError('diagnostic_selection_conflict','Original complete selected body CAS lost',409)
        else:
            current=connection.execute('SELECT value FROM metadata WHERE key=?',(key,)).fetchone()
            if current is None or current[0]!=body:raise EngineError('diagnostic_selection_conflict','Retained selection changed',409)
        return DiagnosticSelectionEvidence(selection_kind=selection.selection_kind,
            old_selected_body=selection.old_selected_body,old_selected_ref=ComponentDiagnosisRefV1.model_validate_json(selection.old_selected_body) if selection.old_selected_body else None,
            new_selected_body=body,new_selected_ref=selection.recorded.ref,new_registered_input_ref=selection.registered_input_ref,
            old_journal_sha256=digest(selection.old_journal_body) if selection.old_journal_body else None,
            previous_committed_source_ref=selection.source_ref)

    def diagnostic_selection_final_writer(self, connection, lease, selection, *, journal_body=None, source_body=None):
        with self._lock:held=self._diagnostic_selections.get(id(selection))
        if held is None or held[0] is not selection or held[1]!=lease or held[2]!=threading.get_ident():
            raise EngineError('diagnostic_selection_denied','Actual writer hold required',403)
        replacements={SELECT_PREFIX+selection.preparation_id:plan_payload_bytes(selection.recorded.ref).decode('utf-8')}
        if journal_body is not None:replacements[PREFIX+lease.run_id]=journal_body
        captured=[]
        for table,column,key,expected in held[4]:
            if table=='metadata' and key in replacements:
                current=connection.execute('SELECT * FROM metadata WHERE key=?',(key,)).fetchone()
                if current is None or current['value']!=replacements[key]:
                    raise EngineError('diagnostic_selection_conflict','Exact own committed selected/journal body required',409)
                captured.append((table,column,key,dict(current)))
            else:captured.append((table,column,key,expected))
        self.assert_registered_ctc_work_writer(connection,tuple(captured))
        if source_body is not None:
            saved=connection.execute('SELECT value FROM metadata WHERE key=?',(source_key(lease.run_id,journal_body),)).fetchone()
            if saved is None or saved[0]!=source_body:raise EngineError('diagnostic_source_changed','Exact own companion must commit with journal',409)
        return tuple(captured)

    def retain_failed_diagnostic_selection_writer(self, connection, lease, selection):
        """Failed finalization preserves an already committed selection only."""
        if selection.selection_kind!='retain':
            raise EngineError('diagnostic_selection_commit_required','Pending diagnosis must use its original park before failure finalization',409)
        self.engine._lease(connection,lease)
        self.diagnostic_selection_final_writer(connection,lease,selection)
        return DiagnosticSelectionEvidence(selection_kind='retain',old_selected_body=selection.old_selected_body,
            old_selected_ref=selection.recorded.ref,new_selected_body=selection.old_selected_body,
            new_selected_ref=selection.recorded.ref,new_registered_input_ref=selection.registered_input_ref,
            old_journal_sha256=digest(selection.old_journal_body) if selection.old_journal_body else None,
            previous_committed_source_ref=selection.source_ref)

    def write_diagnostic_source_for_assessment(self, connection, lease, assessment, journal, body, selection_evidence, *, terminal_failure=None):
        with self._lock:association=getattr(self,'_diagnostic_assessment_sources',{}).get(id(assessment))
        if association is None:return None
        _assessment,selection,outcome=association
        snapshot=journal.snapshot
        source_type=CurrentFinalDiagnosticSourceV3 if selection.child_transition is not None or terminal_failure is not None else CurrentFinalDiagnosticSourceV2
        extra={'selected_child_transition':selection.child_transition.evidence if selection.child_transition else None,
            'terminal_failure':terminal_failure} if source_type is CurrentFinalDiagnosticSourceV3 else {}
        source=source_type(format='current-final-diagnostic-source-v3' if extra else 'current-final-diagnostic-source-v2',binding=journal.binding,
            journal_sha256=digest(body),snapshot_sha256=digest(canonical(snapshot)),preparation_id=snapshot.preparation_id,
            preparation_intent_sha256=snapshot.preparation_intent_sha256,candidate_manifest_file_sha256=snapshot.candidate_manifest_file_sha256,
            ready_material_refs=snapshot.ready_material_refs,origin_kind=outcome.kind,
            original_snapshot=outcome.assessment.snapshot if outcome.assessment and outcome.kind in {'precision_failure','evidence_wait','legacy_diagnostic_block'} else None,quality_failure=outcome.quality_failure,
            diagnostic_ref=selection.recorded.ref,diagnostic_input_key_sha256=selection.recorded.ref.input_key_sha256,
            previous_source_ref=selection.source_ref,resume_context=getattr(self,'_diagnostic_assessment_resume_contexts',{}).get(id(assessment)),
            authored_fence=lease.fencing_token,selection_evidence=selection_evidence,**extra)
        raw=plan_payload_bytes(source).decode('utf-8');key=source_key(lease.run_id,body)
        saved=connection.execute('SELECT value FROM metadata WHERE key=?',(key,)).fetchone()
        if saved is not None and saved[0]!=raw:raise EngineError('diagnostic_source_conflict','Immutable exact journal source conflict',409)
        if saved is None:connection.execute('INSERT INTO metadata(key,value) VALUES(?,?)',(key,raw))
        self.diagnostic_selection_final_writer(connection,lease,selection,journal_body=body,source_body=raw)
        return source

    def copy_current_diagnostic_source_writer(self, connection, previous_raw, previous, new_raw, new_journal, *, resume_context=None):
        source,old=self._read_source_writer(connection,previous_raw,previous)
        if source is None:
            if type(previous.snapshot) is CurrentFinalDiagnosticSnapshotV1:
                raise EngineError('diagnostic_source_unavailable','Legacy diagnostic checkpoint needs current source reconstruction',503)
            return None
        selected=connection.execute('SELECT value FROM metadata WHERE key=?',(SELECT_PREFIX+source.preparation_id,)).fetchone()
        if selected is None or ComponentDiagnosisRefV1.model_validate_json(selected[0])!=source.diagnostic_ref:
            raise EngineError('diagnostic_source_changed','Queue/claim cannot change or lose the committed selection',409)
        reference=DiagnosticMetadataRef(record_id=old['key'],content_sha256=digest(old['value']),size=len(old['value'].encode('utf-8')))
        values={'journal_sha256':digest(new_raw),'snapshot_sha256':digest(canonical(new_journal.snapshot)),
            'preparation_id':new_journal.snapshot.preparation_id,
            'preparation_intent_sha256':new_journal.snapshot.preparation_intent_sha256,
            'candidate_manifest_file_sha256':new_journal.snapshot.candidate_manifest_file_sha256,
            'ready_material_refs':new_journal.snapshot.ready_material_refs,
            'previous_source_ref':reference,'resume_context':resume_context if resume_context is not None else source.resume_context}
        if new_journal.snapshot.preparation_id!=source.preparation_id:
            raise EngineError('diagnostic_source_changed','Different child requires its own original verified source association',409)
        copied=source.model_copy(update=values)
        # Reparse after update: model_copy is not a validation bypass.
        raw=plan_payload_bytes(copied).decode('utf-8');copied=parse_source(raw)
        key=source_key(new_journal.binding.run_id,new_raw)
        existing=connection.execute('SELECT value FROM metadata WHERE key=?',(key,)).fetchone()
        if existing is not None and existing[0]!=raw:raise EngineError('diagnostic_source_conflict','Immutable source copy conflict',409)
        if existing is None:connection.execute('INSERT INTO metadata(key,value) VALUES(?,?)',(key,raw))
        # Exact original body, selected body and own new journal all remain checked.
        current=connection.execute('SELECT value FROM metadata WHERE key=?',(old['key'],)).fetchone()
        journal_row=connection.execute('SELECT value FROM metadata WHERE key=?',(PREFIX+new_journal.binding.run_id,)).fetchone()
        if current is None or current[0]!=old['value'] or journal_row is None or journal_row[0]!=new_raw:
            raise EngineError('diagnostic_source_changed','Source and journal must commit together',409)
        return copied

    def read_current_final_diagnostic_source(self, lease, continuation):
        with self.engine.db.connect_readonly() as connection:
            self.engine._lease(connection,lease)
            saved=connection.execute('SELECT value FROM metadata WHERE key=?',(PREFIX+lease.run_id,)).fetchone()
            if saved is None:raise EngineError('final_evidence_checkpoint_missing','Exact current journal required',409)
            journal=parse_journal(saved[0],now=self.engine.clock())
            if (journal.control.phase!='executing' or journal.control.execution_fence!=lease.fencing_token
                    or continuation.binding!=journal.binding or continuation.snapshot!=journal.snapshot
                    or continuation.execution_fence!=lease.fencing_token):
                raise EngineError('final_evidence_claim_required','Actual current continuation required',409)
            source,row=self._read_source_writer(connection,saved[0],journal)
            if source is None:return None
            selected=connection.execute('SELECT value FROM metadata WHERE key=?',(SELECT_PREFIX+source.preparation_id,)).fetchone()
            if selected is None or ComponentDiagnosisRefV1.model_validate_json(selected[0])!=source.diagnostic_ref:
                raise EngineError('diagnostic_source_changed','Current journal/source/selected must agree',409)
            ref=DiagnosticMetadataRef(record_id=row['key'],content_sha256=digest(row['value']),size=len(row['value'].encode('utf-8')))
        result=CurrentDiagnosticSourceRead(source,ref,lease.fencing_token)
        with self._lock:
            if not hasattr(self,'_diagnostic_source_reads'):self._diagnostic_source_reads={}
            self._diagnostic_source_reads[id(result)]=(result,lease,threading.get_ident())
        return result

    def commit_first_publication_diagnosis(self, connection, lease, verified):
        with self._lock:selection=getattr(self,'_diagnostic_verified_selections',{}).get(verified.verification_id)
        if selection is None:return
        if selection.selection_kind=='retain':
            self.diagnostic_selection_final_writer(connection,lease,selection)
            return
        evidence=self.commit_current_diagnostic_selection_writer(connection,lease,selection,transition='first_publish')
        value={'format':'current-component-diagnostic-publication-source-v1','binding':selection.binding,
            'preparation_id':selection.preparation_id,'preparation_intent_sha256':selection.recorded.fact.parent_intent_sha256,
            'manifest_file_sha256':verified.manifest_sha256,'authored_fence':lease.fencing_token,
            'selected_ref':selection.recorded.ref,'selected_body':evidence.new_selected_body,
            'registered_input_ref':selection.registered_input_ref,'old_selected_body':None,'old_journal_sha256':None,
            'previous_source_ref':selection.source_ref}
        raw=canonical_body(value);key='component-diagnostic-publication-source.'+selection.preparation_id+'.'+verified.manifest_sha256
        old=connection.execute('SELECT value FROM metadata WHERE key=?',(key,)).fetchone()
        if old is not None and old[0]!=raw:raise EngineError('diagnostic_source_conflict','Original publication selection source conflict',409)
        if old is None:connection.execute('INSERT INTO metadata(key,value) VALUES(?,?)',(key,raw))
        captured=self.diagnostic_selection_final_writer(connection,lease,selection)
        with self._lock:
            held=self._diagnostic_records_held[id(selection.recorded)]
            self._diagnostic_records_held[id(selection.recorded)]=(*held[:3],captured,held[4])
