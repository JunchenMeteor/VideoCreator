"""No-lease current-source probe; original Runtime owns queue/claim effects."""
import hashlib
import threading
import time

from pydantic import ValidationError

from video_creator.application.engine import canonical, digest
from video_creator.application.affected_repair_service import canonical_body
from video_creator.application.current_final_evidence_journal import PREFIX, prepared_current, require_waiting
from video_creator.application.diagnostic_selection import source_key, parse_source, SELECT_PREFIX, INPUT_PREFIX, RESULT_PREFIX
from video_creator.domain import contracts as c
from video_creator.domain.bundle import MaterialReceipt
from video_creator.domain.component_diagnosis import ComponentDiagnosisRefV1, ComponentDiagnosticFactV1
from video_creator.domain.diagnostic_recovery import (
    DiagnosticMaterialCompletion, DiagnosticFeedbackCompletion, DiagnosticStableInputV2,
    RegisteredDiagnosticEnvelopeV2, RegisteredDiagnosticInputRef, DiagnosticMetadataRef,
    DiagnosticResumeContext, DiagnosticResumeProbe, CurrentDiagnosticSourceRead,
    CurrentFinalDiagnosticSourceV1,
)
from video_creator.domain.errors import EngineError
from video_creator.domain.plan_repair_targets import plan_payload_bytes, plan_payload_sha256

_probe_context=threading.local()

class DiagnosticResumeRuntime:
    @property
    def _pending_diagnostic_probe(self):
        return getattr(_probe_context,'pending',{}).get(id(self))

    @_pending_diagnostic_probe.setter
    def _pending_diagnostic_probe(self,value):
        if not hasattr(_probe_context,'pending'):_probe_context.pending={}
        if value is None:_probe_context.pending.pop(id(self),None)
        else:_probe_context.pending[id(self)]=value

    def probe_current_diagnostic_resume(self, journal, exact_raw, source):
        """Observe actual allowed changes without a synthetic lease or dispatch."""
        with self.engine.db.connect_readonly() as connection:
            prepared,run,production,request=prepared_current(self.engine,connection,journal)
            require_waiting(run,journal)
            _run,_production,_request,binding=self._diagnostic_bound_context(connection,run['id'])
            if binding!=journal.binding:raise EngineError('diagnostic_source_changed','Original current registration changed',409)
            registered=self.engine._authorization_identity(production['owner'])
            if (registered.registration_sha256,registered.resource_manifest_sha256,registered.runtime_manifest_sha256)!=self.installation_resource_identity:
                raise EngineError('production_installation_binding_invalid','Original qualified source differs from waiting binding',403)
            selected=connection.execute('SELECT * FROM metadata WHERE key=?',(SELECT_PREFIX+prepared['id'],)).fetchone()
            if selected is None:raise EngineError('diagnostic_source_changed','Committed waiting diagnostic selection missing',409)
            ref=ComponentDiagnosisRefV1.model_validate_json(selected['value'])
            if ref!=journal.snapshot.diagnostic_ref:raise EngineError('diagnostic_source_changed','Original journal/selected reference disagree',409)
            fact_row=connection.execute('SELECT * FROM metadata WHERE key=?',(ref.record_id,)).fetchone()
            if fact_row is None or (len(fact_row['value'].encode('utf-8')),digest(fact_row['value']))!=(ref.size,ref.content_sha256):
                raise EngineError('diagnostic_source_invalid','Immutable waiting diagnostic fact damaged',422)
            fact=ComponentDiagnosticFactV1.model_validate_json(fact_row['value'])
            if fact.binding!=binding or fact.parent_preparation_id!=prepared['id'] or fact.parent_intent_sha256!=digest(prepared['intent_json']):
                raise EngineError('diagnostic_source_changed','Original diagnostic source scope changed',409)
            if source is not None and source.diagnostic_ref!=ref:raise EngineError('diagnostic_source_changed','Source and selected fact disagree',409)
            input_row=connection.execute('SELECT * FROM metadata WHERE key=?',(INPUT_PREFIX+ref.input_key_sha256,)).fetchone()
            if input_row is None:raise EngineError('diagnostic_source_changed','Original registered input missing',409)
            from video_creator.application.bundles import strict_json
            original=strict_json(input_row['value'].encode('utf-8'))
            if not isinstance(original,dict) or set(original)!={'format','stable','analysis_intents'}:
                raise EngineError('diagnostic_source_invalid','Original strict registered input required',422)
            if original['format'] not in {'registered-component-diagnostic-input-v1','registered-component-diagnostic-input-v2'}:
                raise EngineError('diagnostic_source_invalid','Unknown registered input version',422)
            if digest(canonical_body(original['stable']))!=ref.input_key_sha256:
                raise EngineError('diagnostic_source_changed','Original complete stable input hash changed',409)
            checkpoint=connection.execute('SELECT * FROM metadata WHERE key=?',(PREFIX+run['id'],)).fetchone()
            if checkpoint is None or checkpoint['value']!=exact_raw:raise EngineError('final_evidence_checkpoint_changed','Original waiting journal changed',409)
            source_row=connection.execute('SELECT * FROM metadata WHERE key=?',(source_key(run['id'],exact_raw),)).fetchone()
            captures=[('metadata','key',checkpoint['key'],dict(checkpoint)),('metadata','key',selected['key'],dict(selected)),
                ('metadata','key',fact_row['key'],dict(fact_row)),('metadata','key',input_row['key'],dict(input_row)),
                ('bundle_revisions','id',prepared['id'],{key:prepared[key] for key in ('id','run_id','revision_id','intent_json')})]
            if source_row is not None:captures.append(('metadata','key',source_row['key'],dict(source_row)))
            items=connection.execute('SELECT * FROM bundle_items WHERE preparation_id=? AND status=? ORDER BY artifact_id',(prepared['id'],'ready')).fetchall()
            feedback=connection.execute('SELECT * FROM feedback_revisions WHERE production_id=? AND new_run_id=? ORDER BY id',(production['id'],run['id'])).fetchall()
        issuer=self.engine.production_admissions
        with issuer.current_guard(registered) as guard:
            with self.engine.db.connect_readonly() as connection:
                issuer._guard(connection,guard)
                issuer._request(connection,production,run,registered)
                self.bundle.assert_registered_ctc_work_writer(connection,tuple(captures))
                context=source.resume_context if source is not None else None
                if context is not None and context.work_kind=='final_validation_after_analysis':
                    from video_creator.application.current_production_blockers import unsettled
                    if unsettled(connection,run['id']):return 'needs_reconciliation','production_blocker_reconciliation_required',None
                    index=connection.execute('SELECT * FROM metadata WHERE key=?',(RESULT_PREFIX+ref.input_key_sha256,)).fetchone()
                    if (fact.result not in {'timing_only','no_component_failure'} or context.expected_diagnostic_ref!=ref
                            or index is None or ComponentDiagnosisRefV1.model_validate_json(index['value'])!=ref
                            or context.registered_input_ref.input_key_sha256!=ref.input_key_sha256):
                        raise EngineError('diagnostic_source_changed','Only actual committed cleared analysis may schedule full verification',409)
                    for operation in fact.analysis_operation_refs:
                        saved=connection.execute('SELECT * FROM operations WHERE id=? AND run_id=?',(operation.operation_id,run['id'])).fetchone()
                        if (saved is None or saved['status']!='succeeded' or not saved['settled']
                                or saved['input_sha256']!=operation.input_sha256 or digest(saved['route_json'])!=operation.route_sha256
                                or digest(saved['observation_json'])!=operation.observation_sha256):
                            raise EngineError('diagnostic_source_changed','Actual cleared analysis still requires its original succeeded settled Operations',409)
                        captures.append(('operations','id',saved['id'],dict(saved)))
                    captures.append(('metadata','key',index['key'],dict(index)))
                    if source_row is None or source_row['value']!=plan_payload_bytes(source).decode('utf-8'):
                        raise EngineError('diagnostic_source_changed','Original cleared analysis source body changed',409)
                    input_ref=RegisteredDiagnosticInputRef(record_id=input_row['key'],content_sha256=digest(input_row['value']),
                        size=len(input_row['value'].encode('utf-8')),input_key_sha256=ref.input_key_sha256)
                    if input_ref!=context.registered_input_ref:
                        raise EngineError('diagnostic_source_changed','Original cleared analysis input receipt changed',409)
                    source_ref=DiagnosticMetadataRef(record_id=source_row['key'],content_sha256=digest(source_row['value']),size=len(source_row['value'].encode('utf-8')))
                    probe=DiagnosticResumeProbe(binding,prepared['id'],exact_raw,CurrentDiagnosticSourceRead(source,source_ref,0),
                        context.completion_source_refs,input_ref,'final_validation_after_analysis',ref)
                    if not hasattr(self,'_diagnostic_resume_probes'):self._diagnostic_resume_probes={}
                    self._diagnostic_resume_probes[id(probe)]=(probe,threading.get_ident(),time.monotonic()+30,tuple(captures),
                        input_row['value'],source_row['value'],tuple((value,self._diagnostic_completion_bytes_no_lease(value,prepared,production)) for value in context.completion_source_refs))
                    issuer._guard(connection,guard)
                    return 'retry_final_validation',None,probe
            assembly=self.bundle._read_final_assembly(prepared,binding)
            if assembly is None:return 'still_blocked','original_assembly_context_missing',None
            if self.journal._probe_waiting_original_asr(binding.run_id,assembly.asr_operation_id) is None:
                return 'still_blocked','original_asr_validation_context_missing',None
            completions=[]
            used={plan_payload_sha256(value) for value in original['stable'].get('completion_source_refs',())}
            existing={receipt.material_id for receipt in journal.snapshot.ready_material_refs}
            requested=set(fact.information_requests)
            # Only a genuinely requested supplemental READY item can change input.
            for item in items:
                if item['material_id'] in existing or not requested.intersection({'source_material_missing','source_mapping_incomplete','analysis_inconclusive'}):continue
                receipt=MaterialReceipt(artifact_id=item['artifact_id'],preparation_id=prepared['id'],material_id=item['material_id'],
                    schema_kind=item['schema_kind'],media_type=item['media_type'],sha256=item['sha256'],size=item['size'])
                path=self.bundle._file('BundleMaterials',receipt.material_id);raw=path.read_bytes()
                if (len(raw),hashlib.sha256(raw).hexdigest())!=(receipt.size,receipt.sha256):raise EngineError('bundle_integrity_failed','New READY completion bytes changed',422)
                from video_creator.application.bundles import validate_text
                validate_text(raw,receipt.schema_kind,receipt.media_type)
                value=DiagnosticMaterialCompletion(kind='ready_material',ref=receipt)
                if plan_payload_sha256(value) not in used:completions.append(value)
            original_feedback={value.revision_id for value in assembly.feedback_revision_refs}
            for item in feedback:
                value=c.FeedbackRevision.model_validate_json(item['body'])
                if (value.feedback_id in original_feedback or not value.instruction_text.strip()
                        or value.target_revision_id not in {r.revision_id for r in assembly.creative_revision_refs}
                        or not requested.intersection({'source_mapping_incomplete','analysis_inconclusive','competing_causes'})):continue
                ref_value=c.RevisionRef(revision_id=value.feedback_id,kind='feedback',content_sha256=digest(item['body']))
                completion=DiagnosticFeedbackCompletion(kind='feedback',ref=ref_value)
                if plan_payload_sha256(completion) not in used:completions.append(completion)
            if not completions:
                # Resource completion cannot be inferred from file presence or a Bool.
                if 'diagnostic_method_not_ready' in requested:
                    return 'still_blocked','diagnostic_resource_observer_not_ready',None
                return 'still_blocked',next(iter(fact.information_requests),'analysis_inconclusive'),None
            stable=dict(original['stable']);stable['format']='current-component-diagnostic-input-v2'
            old_completions=stable.get('completion_source_refs',[])
            all_values=old_completions+[value.model_dump(mode='json') for value in completions]
            unique={plan_payload_sha256(value):value for value in all_values}
            stable['completion_source_refs']=[unique[key] for key in sorted(unique)]
            stable_value=DiagnosticStableInputV2.model_validate_json(canonical_body(stable))
            key=plan_payload_sha256(stable_value)
            intents=tuple(c.OperationIntent(step_key='component-diagnosis-'+key[:32]+'-'+plan_payload_sha256(method)[:16],
                dedupe_key='component-diagnosis-'+key[:32]+'-'+plan_payload_sha256(method)[:16],
                input_sha256=plan_payload_sha256({'input_key_sha256':key,'method_ref':method.model_dump(mode='json')}),
                route_id=method.route.route_id,reserved_cost=method.route.max_operation_cost) for method in stable_value.diagnostic_method_refs)
            envelope=RegisteredDiagnosticEnvelopeV2(format='registered-component-diagnostic-input-v2',stable=stable_value,analysis_intents=intents)
            input_body=plan_payload_bytes(envelope).decode('utf-8')
            with self.engine.db.connect_readonly() as connection:
                result=connection.execute('SELECT value FROM metadata WHERE key=?',(RESULT_PREFIX+key,)).fetchone()
                expected=ComponentDiagnosisRefV1.model_validate_json(result[0]) if result else None
                from video_creator.application.current_production_blockers import unsettled
                if unsettled(connection,run['id']):return 'needs_reconciliation','production_blocker_reconciliation_required',None
                issuer._guard(connection,guard);self.bundle.assert_registered_ctc_work_writer(connection,tuple(captures))
            if source is None:
                source=CurrentFinalDiagnosticSourceV1(format='current-final-diagnostic-source-v1',binding=binding,
                    journal_sha256=digest(exact_raw),snapshot_sha256=digest(canonical(journal.snapshot)),
                    preparation_id=prepared['id'],preparation_intent_sha256=digest(prepared['intent_json']),
                    candidate_manifest_file_sha256=journal.snapshot.candidate_manifest_file_sha256,
                    ready_material_refs=journal.snapshot.ready_material_refs,origin_kind='legacy_diagnostic_block',
                    original_snapshot=None,quality_failure=None,diagnostic_ref=ref,diagnostic_input_key_sha256=ref.input_key_sha256,
                    previous_source_ref=None,resume_context=None,authored_fence=fact.authored_fence)
            source_body=plan_payload_bytes(source).decode('utf-8')
            source_ref=DiagnosticMetadataRef(record_id=source_key(run['id'],exact_raw),content_sha256=digest(source_body),size=len(source_body.encode('utf-8')))
            read=CurrentDiagnosticSourceRead(source,source_ref,0)
            input_ref=RegisteredDiagnosticInputRef(record_id=INPUT_PREFIX+key,content_sha256=digest(input_body),size=len(input_body.encode('utf-8')),input_key_sha256=key)
            probe=DiagnosticResumeProbe(binding,prepared['id'],exact_raw,read,stable_value.completion_source_refs,input_ref,
                'reuse_record' if expected else 'analyse_changed_input',expected)
            if not hasattr(self,'_diagnostic_resume_probes'):self._diagnostic_resume_probes={}
            self._diagnostic_resume_probes[id(probe)]=(probe,threading.get_ident(),time.monotonic()+30,tuple(captures),input_body,source_body,
                tuple((value, self._diagnostic_completion_bytes_no_lease(value,prepared,production)) for value in stable_value.completion_source_refs))
            return 'retry_final_validation',None,probe

    def _diagnostic_bound_context(self, connection, run_id):
        from video_creator.application.current_production_blockers import bound_context
        return bound_context(self.engine,connection,run_id,self.sha256)

    def _diagnostic_completion_bytes_no_lease(self, completion, prepared, production):
        if completion.kind=='ready_material':
            if completion.ref.preparation_id!=prepared['id']:raise EngineError('diagnostic_source_changed','Completion must belong to original prepared scope',409)
            raw=self.bundle._file('BundleMaterials',completion.ref.material_id).read_bytes()
            if (len(raw),hashlib.sha256(raw).hexdigest())!=(completion.ref.size,completion.ref.sha256):raise EngineError('bundle_integrity_failed','Completion READY bytes changed',422)
            return raw
        if completion.kind=='feedback':
            with self.engine.db.connect_readonly() as connection:
                row=connection.execute('SELECT body FROM feedback_revisions WHERE id=? AND production_id=? AND new_run_id=?',
                    (completion.ref.revision_id,production['id'],prepared['run_id'])).fetchone()
            if row is None or digest(row[0])!=completion.ref.content_sha256:raise EngineError('diagnostic_source_changed','Original authenticated feedback changed',409)
            return row[0].encode('utf-8')
        raise EngineError('diagnostic_resource_observer_not_ready','Actual qualified resource completion observer required',503)

    def commit_diagnostic_probe_writer(self, connection, probe):
        hold=getattr(self,'_diagnostic_resume_probes',{}).get(id(probe))
        if hold is None or hold[0] is not probe or hold[1]!=threading.get_ident() or time.monotonic()>=hold[2]:
            raise EngineError('diagnostic_probe_denied','Actual current no-lease probe required',403)
        self.bundle.assert_registered_ctc_work_writer(connection,hold[3])
        for completion,raw in hold[6]:
            if completion.kind=='ready_material':
                row=connection.execute('SELECT * FROM bundle_items WHERE preparation_id=? AND material_id=? AND status=?',
                    (probe.preparation_id,completion.ref.material_id,'ready')).fetchone()
                if row is None or (row['sha256'],row['size'],row['artifact_id'])!=(completion.ref.sha256,completion.ref.size,completion.ref.artifact_id):
                    raise EngineError('diagnostic_source_changed','Actual completion receipt changed before queue',409)
            elif completion.kind=='feedback':
                row=connection.execute('SELECT body FROM feedback_revisions WHERE id=?',(completion.ref.revision_id,)).fetchone()
                if row is None or row[0].encode('utf-8')!=raw:raise EngineError('diagnostic_source_changed','Authenticated feedback body changed before queue',409)
        for key,body in ((probe.registered_input_ref.record_id,hold[4]),(probe.source.source_ref.record_id,hold[5])):
            saved=connection.execute('SELECT value FROM metadata WHERE key=?',(key,)).fetchone()
            if saved is not None and saved[0]!=body:raise EngineError('diagnostic_source_conflict','Original probe input/source body conflict',409)
            if saved is None:connection.execute('INSERT INTO metadata(key,value) VALUES(?,?)',(key,body))
        self.bundle.assert_registered_ctc_work_writer(connection,hold[3])
        return DiagnosticResumeContext(work_kind=probe.work_kind,previous_waiting_journal_sha256=digest(probe.journal_body),
            previous_diagnostic_ref=probe.source.source.diagnostic_ref,registered_input_ref=probe.registered_input_ref,
            completion_source_refs=probe.completion_source_refs,expected_diagnostic_ref=probe.expected_diagnostic_ref)
