"""Actual held diagnostic source/record service; ledger effects stay in Worker."""

import hashlib
import threading

from pydantic import ValidationError

from video_creator.application.engine import canonical, digest
from video_creator.domain import contracts as c
from video_creator.domain.bundle import BundlePreparationIntent
from video_creator.domain.component_diagnosis import (
    ComponentDiagnosticFactV1, ComponentDiagnosisRefV1, ComponentDiagnosticObservationV1,
    DiagnosticAnalysisOperationRefV1, DiagnosticSourceMediaRefV1, DiagnosticSampleRefV1,
    DiagnosticOperationOutputRefV1, ProductionDriverResourcesDiagnosticV1,
    RegisteredComponentDiagnosisInputsV1, RegisteredComponentDiagnosisV1,
    ComponentDiagnosticMethodRefV1, DiagnosticMetadataRef,
)
from video_creator.domain.current_final_evidence import CurrentFinalEvidenceReadSet
from video_creator.domain.errors import EngineError
from video_creator.domain.plan_repair_targets import plan_payload_bytes, plan_payload_sha256

INPUT_PREFIX = 'component-diagnostic-input.'
SELECT_PREFIX = 'component-diagnostic-selected.'
RECORD_PREFIX = 'component-diagnosis.'
RESULT_PREFIX = 'component-diagnostic-result.'
LIMIT = 2 * 1024 * 1024


class ComponentDiagnosisService:
    def assert_diagnostic_publish_writer(self, connection, lease, preparation_id):
        """Additional denial only; the original publication guard remains required."""
        selected=connection.execute('SELECT value FROM metadata WHERE key=?',(SELECT_PREFIX+preparation_id,)).fetchone()
        with self._lock:
            factories=[value for value in getattr(self,'_production_services_held',{}).values()
                if value[2]==lease and value[3]==threading.get_ident()]
        required=any(getattr(value[0],'component_diagnostic_ports',None) is not None for value in factories)
        if selected is None:
            if required:
                raise EngineError('diagnostic_source_missing','Actual installed diagnostic production must retain its current source record',409)
            return
        try:ref=ComponentDiagnosisRefV1.model_validate_json(selected[0])
        except ValidationError:raise EngineError('diagnostic_source_invalid','Original selected diagnostic reference damaged',422) from None
        row=connection.execute('SELECT value FROM metadata WHERE key=?',(ref.record_id,)).fetchone()
        if row is None or (len(row[0].encode('utf-8')),digest(row[0]))!=(ref.size,ref.content_sha256):
            raise EngineError('diagnostic_source_changed','Actual immutable selected diagnostic record changed',409)
        fact=ComponentDiagnosticFactV1.model_validate_json(row[0])
        if fact.binding!=self._final_binding(lease,connection) or fact.parent_preparation_id!=preparation_id:
            raise EngineError('diagnostic_source_changed','Actual selected diagnosis must retain this complete publication binding',409)
        if fact.result in {'component_repair','information_required'}:
            raise EngineError('diagnostic_component_failed','Current original media still has a real component failure or unresolved diagnosis',422)
        with self._lock:
            readers=[value for value in getattr(self,'_diagnostic_records_held',{}).values()
                if value[1]==lease and value[2]==threading.get_ident() and value[0].ref==ref and len(value)>=5]
        if not readers:
            raise EngineError('diagnostic_source_denied','Actual current verified diagnostic reader required before publication',403)
        for reader in readers:self.assert_registered_ctc_work_writer(connection,reader[3])

    def assert_diagnostic_assessment_writer(self, connection, lease, snapshot, *, checkpoint_body=None):
        from video_creator.application.current_final_evidence_journal import PREFIX,parse_journal
        with self._lock:
            readers=[value for value in getattr(self,'_diagnostic_records_held',{}).values()
                if value[1]==lease and value[2]==threading.get_ident() and value[0].ref==snapshot.diagnostic_ref and len(value)>=5]
        if not readers:
            raise EngineError('diagnostic_source_denied','Actual original verified diagnostic record must be retained',403)
        ref=snapshot.diagnostic_ref
        stored=connection.execute('SELECT value FROM metadata WHERE key=?',(ref.record_id,)).fetchone()
        if stored is None or (len(stored[0].encode('utf-8')),digest(stored[0]))!=(ref.size,ref.content_sha256):
            raise EngineError('diagnostic_source_changed','Immutable diagnostic record changed at final writer',409)
        for reader in readers:
            captured=reader[3]
            if checkpoint_body is not None:
                checkpoint=connection.execute('SELECT value FROM metadata WHERE key=?',(PREFIX+lease.run_id,)).fetchone()
                if checkpoint is None or checkpoint[0]!=checkpoint_body:
                    raise EngineError('final_evidence_checkpoint_changed','Original own diagnostic checkpoint CAS lost',409)
                journal=parse_journal(checkpoint[0],now=self.engine.clock())
                if journal.snapshot!=snapshot or journal.binding!=reader[0].fact.binding:
                    raise EngineError('final_evidence_checkpoint_changed','Exact own diagnostic snapshot/binding required',409)
                captured=tuple(item for item in captured if not (item[0]=='metadata' and item[2]==PREFIX+lease.run_id))
            self.assert_registered_ctc_work_writer(connection,captured)
        return snapshot

    def assert_diagnostic_analysis_writer(self, connection, lease, step_key, input_sha256, *, intent=None, guard=None):
        """Original held registration and captured sources, with no nested I/O."""
        with self._lock:
            matches=[]
            for value in getattr(self,'_diagnostic_inputs_held',{}).values():
                if value[1]!=lease or value[2]!=threading.get_ident():continue
                for registered in value[0].analysis_intents:
                    if registered.step_key==step_key:matches.append((value,registered))
        if len(matches)!=1:
            raise EngineError('diagnostic_source_denied','Exactly one actual held registered analysis Step required',403)
        held,registered=matches[0]
        if registered.input_sha256!=input_sha256 or intent is not None and registered!=intent:
            raise EngineError('diagnostic_source_denied','Actual registered analysis input/route/dedupe required',403)
        self.engine._lease(connection,lease)
        self.assert_registered_ctc_work_writer(connection,held[3])
        factory=self._affected_services_writer(lease)
        if getattr(factory[0],'component_diagnostic_ports',None) is not held[5]:
            raise EngineError('diagnostic_source_denied','Original actual factory-bound verifier changed',403)
        issuer=self._production_authorization.issuer()
        if guard is not None:issuer._guard(connection,guard)
        return registered

    def _diagnostic_factory(self, lease):
        held = self._affected_services(lease)
        ports = getattr(held[0], 'component_diagnostic_ports', None)
        if (ports is None or getattr(ports, 'services', None) is not held[0]
                or not callable(getattr(ports, 'verify_component_observation', None))):
            raise EngineError('diagnostic_method_not_ready', 'Original factory-bound diagnostic producer/verifier required', 503)
        return held, ports

    def prime_explicit_diagnostic_lineage(self, lease, child_id, lineage):
        from video_creator.application.affected_repair_service import LINEAGE_PREFIX,COMMAND_PREFIX,canonical_body
        from video_creator.application.bundles import strict_json
        from video_creator.application.diagnosed_affected_service import diagnosed_source
        if lineage.get('format')!='current-final-evidence-lineage-v3':
            raise EngineError('final_evidence_lineage_invalid','Explicit diagnostic lineage v3 required',422)
        with self.engine.db.connect_readonly() as connection:
            self.engine._lease(connection,lease)
            saved=connection.execute('SELECT * FROM metadata WHERE key=?',(LINEAGE_PREFIX+child_id,)).fetchone()
            child,*_=self._preparation(connection,lease,child_id)
            parent,*_=self._preparation(connection,lease,lineage['parent_preparation_id'])
            command_row=connection.execute('SELECT * FROM metadata WHERE key=?',
                (COMMAND_PREFIX+lineage['repair_command_sha256'],)).fetchone()
            if (saved is None or strict_json(saved['value'].encode('utf-8'))!=lineage or command_row is None
                    or lineage.get('child_intent_sha256')!=digest(child['intent_json'])
                    or lineage.get('parent_intent_sha256')!=digest(parent['intent_json'])):
                raise EngineError('final_evidence_lineage_invalid','Actual committed parent/child/command source required',422)
            command=strict_json(command_row['value'].encode('utf-8'));source=diagnosed_source(command)
            if (plan_payload_sha256(source)!=lineage['repair_command_sha256']
                    or command.get('source_sha256')!=lineage['repair_command_sha256']
                    or command.get('child_preparation_id')!=child_id or command.get('child_intent_sha256')!=digest(child['intent_json'])
                    or source.parent_preparation_id!=parent['id'] or source.parent_intent_sha256!=digest(parent['intent_json'])
                    or lineage.get('diagnostic_ref')!=source.diagnostic_ref.model_dump(mode='json')
                    or lineage.get('failure_source')!=source.failure_source.model_dump(mode='json')
                    or lineage.get('projection_sha256')!=source.proposal.projection_sha256
                    or lineage.get('recipe_binding_sha256')!=source.proposal.recipe_binding_sha256):
                raise EngineError('final_evidence_lineage_invalid','Complete immutable diagnostic command and lineage changed',422)
            captured=(('metadata','key',saved['key'],dict(saved)),('metadata','key',command_row['key'],dict(command_row)),
                ('bundle_revisions','id',child['id'],{key:child[key] for key in ('id','run_id','revision_id','intent_json')}),
                ('bundle_revisions','id',parent['id'],{key:parent[key] for key in ('id','run_id','revision_id','intent_json')}))
        record=self._read_explicit_diagnostic_record(lease,source.diagnostic_ref,parent['id'])
        with self.engine.db.connect_readonly() as connection:
            self.assert_registered_ctc_work_writer(connection,captured)
            self.assert_diagnostic_command_targets_writer(connection,lease,command)
        with self._lock:
            current=self._diagnostic_records_held[id(record)]
            self._diagnostic_records_held[id(record)]=(*current[:3],current[3]+captured,current[4])
        return record

    def _diagnostic_methods(self, lease, held, ports):
        from video_creator.application.bundles import strict_json
        from video_creator.providers.production_resources import ProductionResources
        runtime = self._production_services_runtime
        raw = runtime.production_manifest.read_bytes()
        if len(raw) > LIMIT or hashlib.sha256(raw).hexdigest() != held[6]:
            raise EngineError('production_resource_changed', 'Actual diagnostic installation resource manifest changed', 503)
        try:
            resources = ProductionDriverResourcesDiagnosticV1.model_validate_json(plan_payload_bytes(strict_json(raw)['production_drivers']))
        except (ValidationError, ValueError, KeyError, TypeError):
            raise EngineError('diagnostic_method_not_ready', 'Strict current installed diagnostic resource catalog required', 503) from None
        registrations = resources.diagnosis.methods
        if tuple(getattr(ports, 'method_registrations', ())) != registrations:
            raise EngineError('diagnostic_method_not_ready', 'Actual factory methods differ from the installed source catalog', 503)
        methods = tuple(ComponentDiagnosticMethodRefV1(**method.model_dump(mode='python'),
            resource_manifest_sha256=held[6],runtime_manifest_sha256=held[7]) for method in registrations)
        files = ProductionResources(runtime.production_manifest, held[6], held[7])
        for method in methods:
            if (method.resource_manifest_sha256, method.runtime_manifest_sha256) != held[6:8]:
                raise EngineError('diagnostic_source_changed', 'Actual method installation binding changed', 403)
            route = self.engine.configured_route(method.route.route_id)
            if route != method.route or not route.verified:
                raise EngineError('diagnostic_source_changed', 'Current registered method route differs', 403)
            for ref in method.implementation_source_refs:
                if hashlib.sha256(files.resource(ref.resource_name).read_bytes()).hexdigest() != ref.sha256:
                    raise EngineError('diagnostic_source_changed', 'Actual indexed diagnostic producer changed', 403)
        return methods

    def _diagnostic_source_rows(self, connection, lease, row, parent, sources, methods, *, continuation=None):
        from video_creator.application.current_final_evidence_journal import PREFIX, parse_journal, prepared_current
        self.engine._lease(connection, lease)
        if self._final_binding(lease, connection) != parent.binding:
            raise EngineError('diagnostic_source_changed', 'Original diagnostic binding changed', 409)
        current, run, production, request = self._preparation(connection, lease, row['id'])
        if current['intent_json'] != row['intent_json']:
            raise EngineError('diagnostic_source_changed', 'Original parent intent changed', 409)
        snapshots = [('bundle_revisions', 'id', row['id'], {key: row[key] for key in ('id', 'run_id', 'revision_id', 'intent_json')})]
        for key in ('current_final_assembly:' + row['id'],):
            saved = connection.execute('SELECT * FROM metadata WHERE key=?', (key,)).fetchone()
            if saved is None:
                raise EngineError('source_material_missing', 'Actual immutable parent assembly required', 503)
            snapshots.append(('metadata', 'key', key, dict(saved)))
        checkpoint = connection.execute('SELECT * FROM metadata WHERE key=?', (PREFIX + lease.run_id,)).fetchone()
        if continuation is not None:
            if checkpoint is None:
                raise EngineError('final_evidence_claim_required', 'Original explicit diagnostic continuation required', 409)
            journal = parse_journal(checkpoint['value'], now=self.engine.clock())
            prepared_current(self.engine, connection, journal)
            if (journal.binding != continuation.binding or journal.snapshot != continuation.snapshot
                    or journal.control.phase != 'executing' or journal.control.execution_fence != lease.fencing_token
                    or continuation.execution_fence != lease.fencing_token or journal.snapshot.preparation_id != row['id']):
                raise EngineError('final_evidence_claim_required', 'Exact current parent/fence required for diagnosis', 409)
        snapshots.append(('metadata', 'key', PREFIX + lease.run_id, dict(checkpoint) if checkpoint is not None else None))
        for ref in (*parent.assembly.creative_revision_refs, parent.assembly.quality_ref):
            source = connection.execute('SELECT * FROM creative_revisions WHERE id=? AND run_id=?', (ref.revision_id, lease.run_id)).fetchone()
            if source is None or source['content_sha256'] != ref.content_sha256 or digest(source['body']) != ref.content_sha256:
                raise EngineError('diagnostic_source_changed', 'Original authored source revision changed', 409)
            snapshots.append(('creative_revisions', 'id', source['id'], dict(source)))
        for source in sources:
            asset = connection.execute('SELECT * FROM assets WHERE id=? AND owner=?', (source.asset_id, production['owner'])).fetchone()
            if asset is None or (asset['sha256'], asset['size'], asset['media_type']) != (source.sha256, source.size, source.media_type):
                raise EngineError('diagnostic_source_changed', 'Original actual source asset changed', 409)
            snapshots.append(('assets', 'id', asset['id'], dict(asset)))
            for identifier in source.source_operation_ids:
                op = connection.execute('SELECT * FROM operations WHERE id=? AND run_id=?', (identifier, lease.run_id)).fetchone()
                if op is None or op['status'] != 'succeeded' or not op['settled']:
                    raise EngineError('analysis_operation_unsettled', 'Original source Operation must be successful and settled', 409, 'reconcile')
                snapshots.append(('operations', 'id', identifier, dict(op)))
        for method in methods:
            route = connection.execute('SELECT * FROM routes WHERE id=?', (method.route.route_id,)).fetchone()
            if route is None or c.CapabilityRoute.model_validate_json(route['body']) != method.route:
                raise EngineError('diagnostic_source_changed', 'Actual registered analysis route changed', 403)
            snapshots.append(('routes', 'id', route['id'], dict(route)))
        snapshots.append(('text_materials', 'preparation_id', row['id'], tuple(dict(item) for item in connection.execute(
            'SELECT * FROM bundle_items WHERE preparation_id=? AND asset_id IS NULL ORDER BY artifact_id', (row['id'],)))))
        return tuple(snapshots), run, production, request

    def _diagnostic_parent(self, lease, preparation_id, *, continuation=None):
        with self.engine.db.connect_readonly() as connection:
            row, _run, _production, _request = self._preparation(connection, lease, preparation_id)
            binding = self._final_binding(lease, connection)
        intent = BundlePreparationIntent.model_validate_json(row['intent_json'])
        assembly = self._read_final_assembly(row, binding)
        if assembly is None:
            raise EngineError('source_material_missing', 'Actual source assembly must precede diagnostic analysis', 503)
        assets = self.resolve_preparation_masters(lease, preparation_id)
        asr = self._validate_final_assembly_facts(lease, row, intent, binding, assembly, author=False, allow_missing_asr=True)
        preparation = self.recover_preparation(lease, preparation_id)
        allocations = tuple(self.material_allocation(lease, preparation_id, slot.artifact_id) for slot in intent.material_slots)
        materials = tuple((ref, self.read_material(lease, preparation_id, ref.material_id)) for ref in preparation.materials)
        candidate = None
        if row['manifest_file_key']:
            _manifest, raw, file_sha = self._original_final_candidate(row, None, binding)
            candidate = (raw, file_sha)
        parent = CurrentFinalEvidenceReadSet(binding, lease.fencing_token, preparation, intent, allocations,
            materials, candidate, assembly, asr, tuple(value for value in materials if value[0].schema_kind in {
                'precision_report', 'precision_report_v03', 'work_alignment_validation', 'license'}), ())
        from video_creator.application.bundles import strict_json
        revisions = {value.revision_id: value for value in self.creative_revisions(lease)}
        storyboard = next((revisions.get(ref.revision_id) for ref in assembly.creative_revision_refs if ref.kind == 'storyboard'), None)
        if storyboard is None or not isinstance(storyboard.body, dict):
            raise EngineError('source_mapping_incomplete', 'Original immutable storyboard is required', 503)
        shots = tuple(storyboard.body.get('shots', ()))
        sources = []
        with self.engine.db.connect_readonly() as connection:
            self.engine._lease(connection, lease)
            for artifact in assembly.media_artifacts:
                asset = assets[artifact.roles[0]]
                operations = []
                for op in connection.execute('SELECT * FROM operations WHERE run_id=? AND status=? AND settled=1 ORDER BY id', (lease.run_id, 'succeeded')):
                    observation = c.OperationObservation.model_validate_json(op['observation_json'])
                    if asset.asset_id in observation.result_asset_ids:
                        operations.append(op['id'])
                if not operations:
                    raise EngineError('source_material_missing', 'Original master has no actual settled Operation provenance', 503)
                role = artifact.roles[0]
                duration = asset.probe.duration_us if asset.probe is not None else None
                sources.append(DiagnosticSourceMediaRefV1(artifact_id=artifact.artifact_id, asset_id=asset.asset_id,
                    role=role, sha256=asset.sha256, size=asset.size, media_type=asset.media_type, probe=asset.probe,
                    source_operation_ids=tuple(operations), intrinsic_range=c.MediaRange(start_us=0,end_us=duration) if duration else None,
                    timeline_range=c.MediaRange(start_us=0,end_us=assembly.timeline_duration_us),
                    mapping_refs=tuple(c.AudioMappingEvidenceRef(mapping_revision_id=m.mapping_revision_id,content_sha256=m.content_sha256) for m in assembly.audio_mappings),
                    shot_ids=tuple(shot['shot_id'] for shot in shots) if role == 'video' else (shots[0]['shot_id'],) if role == 'cover' and shots else ()))
        precision = tuple(value for value in materials if value[0].schema_kind in {'precision_report','precision_report_v03'})
        if len(precision)>1:
            raise EngineError('diagnostic_source_invalid', 'Ambiguous original precision report source', 422)
        receipt, report_bytes = precision[0] if precision else (None,None)
        failed = ()
        if receipt is not None:
            from video_creator.application.bundles import validate_text
            report=validate_text(report_bytes,receipt.schema_kind,receipt.media_type)
            failed=tuple(unit.transcript_unit_id for unit in report.boundaries if max(abs(unit.predicted_range.start_us-unit.reference_range.start_us),abs(unit.predicted_range.end_us-unit.reference_range.end_us))>200_000)
        return row,parent,tuple(sources),receipt,report_bytes,failed

    def _diagnostic_input_value(self, lease, preparation_id, methods, *, continuation=None, original_candidate_sha=False):
        row,parent,sources,precision,raw_report,failed = self._diagnostic_parent(lease,preparation_id,continuation=continuation)
        stable = {'format':'current-component-diagnostic-input-v1','binding':parent.binding,
            'parent_preparation_id':preparation_id,'parent_intent_sha256':digest(row['intent_json']),
            'candidate_manifest_file_sha256':parent.candidate[1] if parent.candidate else None,
            'creative_revision_refs':parent.assembly.creative_revision_refs,'quality_ref':parent.assembly.quality_ref,
            'source_media_refs':sources,'audio_mappings':parent.assembly.audio_mappings,
            'precision_report_ref':precision,'diagnostic_method_refs':methods}
        if original_candidate_sha is not False:
            if original_candidate_sha is not None and (parent.candidate is None or parent.candidate[1]!=original_candidate_sha):
                raise EngineError('diagnostic_source_changed','Original authenticated candidate source changed',409)
            # A candidate produced later by full verification is not a new
            # diagnostic input or a future identity in the original key.
            stable['candidate_manifest_file_sha256']=original_candidate_sha
        # Convert nested model leaves with the original recursive command encoder.
        from video_creator.application.affected_repair_service import canonical_body
        stable_raw=canonical_body(stable)
        key=digest(stable_raw)
        intents=tuple(c.OperationIntent(step_key='component-diagnosis-'+key[:32]+'-'+plan_payload_sha256(method)[:16],
            dedupe_key='component-diagnosis-'+key[:32]+'-'+plan_payload_sha256(method)[:16],
            input_sha256=plan_payload_sha256({'input_key_sha256':key,'method_ref':method.model_dump(mode='json')}),
            route_id=method.route.route_id,reserved_cost=method.route.max_operation_cost) for method in methods)
        inputs=RegisteredComponentDiagnosisInputsV1(key,parent.binding,preparation_id,digest(row['intent_json']),parent,
            precision,raw_report,failed,sources,methods,intents)
        return row,inputs,stable

    def prepare_component_diagnosis(self, lease, preparation_id, *, continuation=None, resume_probe=None, owner_port=None):
        with self._lock:
            if owner_port is None:
                owners=[port for port in self._final_evidence_ports.values()
                    if port._lease==lease and port._thread==threading.get_ident()]
                if len(owners)!=1:
                    raise EngineError('diagnostic_source_denied','One actual current owning final port required',403)
                owner_port=owners[0]
            if (self._final_evidence_ports.get(id(owner_port)) is not owner_port or owner_port._service is not self
                    or owner_port._lease!=lease or owner_port._thread!=threading.get_ident()):
                raise EngineError('diagnostic_source_denied','Actual same-service lease/thread owning final port required',403)
        held, ports = self._diagnostic_factory(lease)
        methods = self._diagnostic_methods(lease, held, ports)
        row,inputs,stable = self._diagnostic_input_value(lease,preparation_id,methods,continuation=continuation)
        if resume_probe is not None:
            inputs,stable=self._prepare_diagnostic_resumed_input(lease,preparation_id,continuation,resume_probe,row,inputs,methods)
        parent,sources=inputs.parent,inputs.source_media_refs
        key,intents=inputs.input_key_sha256,inputs.analysis_intents
        issuer=self._production_authorization.issuer()
        with issuer.current_guard(self._production_authorization.registered(lease)) as guard:
            with self.engine.db.transaction() as connection:
                snapshots,run,production,request=self._diagnostic_source_rows(connection,lease,row,parent,sources,methods,continuation=continuation)
                if resume_probe is not None:
                    with self._lock:resumed=self._diagnostic_resumed_captures.get(id(inputs))
                    if resumed is None or resumed[0] is not inputs or resumed[1]!=lease or resumed[2]!=threading.get_ident():
                        raise EngineError('diagnostic_source_denied','Actual held completion source captures required',403)
                    snapshots+=resumed[3]
                    self.assert_registered_ctc_work_writer(connection,snapshots)
                issuer._guard(connection,guard)
                issuer._request(connection,production,run,guard.identity)
                old=connection.execute('SELECT value FROM metadata WHERE key=?',(INPUT_PREFIX+key,)).fetchone()
                from video_creator.application.affected_repair_service import canonical_body
                from video_creator.domain.diagnostic_recovery import RegisteredComponentDiagnosisInputsV2
                body=canonical_body({'format':'registered-component-diagnostic-input-v2' if type(inputs) is RegisteredComponentDiagnosisInputsV2 else 'registered-component-diagnostic-input-v1','stable':stable,
                    'analysis_intents':intents})
                if old is not None and old[0]!=body:
                    raise EngineError('diagnostic_record_conflict','Stable diagnostic input already has different source or intents',409)
                if old is None:
                    connection.execute('INSERT INTO metadata(key,value) VALUES(?,?)',(INPUT_PREFIX+key,body))
                self.assert_registered_ctc_work_writer(connection,snapshots)
                issuer._guard(connection,guard)
            self.assert_current_production_services(lease,held[0],held[1])
        with self._lock:
            if self._final_evidence_ports.get(id(owner_port)) is not owner_port:
                raise EngineError('diagnostic_source_denied','Owning final port closed before input registration',403)
            if not hasattr(self,'_diagnostic_inputs_held'):
                self._diagnostic_inputs_held={}
            self._diagnostic_inputs_held[id(inputs)]=(inputs,lease,threading.get_ident(),snapshots,continuation,ports,owner_port)
            if not hasattr(self,'_diagnostic_inputs_active'):self._diagnostic_inputs_active={}
            self._diagnostic_inputs_active[(lease.run_id,preparation_id,threading.get_ident(),lease.fencing_token)]=(
                inputs,lease,threading.get_ident(),owner_port)
        return inputs

    def _diagnostic_inputs_current(self, lease, inputs):
        with self._lock:
            held=getattr(self,'_diagnostic_inputs_held',{}).get(id(inputs))
            owner=held[6] if held is not None and len(held)>6 else None
            owner_current=(owner is not None and self._final_evidence_ports.get(id(owner)) is owner
                and owner._service is self and owner._lease==lease and owner._thread==threading.get_ident())
        if (held is None or held[0] is not inputs or held[1]!=lease or held[2]!=threading.get_ident()
                or inputs.parent.execution_fence!=lease.fencing_token):
            raise EngineError('diagnostic_source_denied','Actual same-thread current held diagnostic inputs required',403)
        if not owner_current:
            raise EngineError('diagnostic_source_denied','Original owning final port must remain current',403)
        factory,ports=self._diagnostic_factory(lease)
        if ports is not held[5] or self._diagnostic_methods(lease,factory,ports)!=inputs.diagnostic_method_refs:
            raise EngineError('diagnostic_source_changed','Actual diagnostic method producer changed',403)
        row,parent,sources,precision,raw,failed=self._diagnostic_parent(lease,inputs.parent_preparation_id,continuation=held[4])
        if (parent!=inputs.parent or sources!=inputs.source_media_refs or precision!=inputs.precision_report_ref
                or raw!=inputs.precision_report_bytes or failed!=inputs.failed_unit_ids):
            # eq=False readsets deliberately require exact constituent facts.
            fields=('binding','execution_fence','preparation','intent','allocations','materials','candidate','assembly','asr','strict_materials','missing_facts')
            if (any(getattr(parent,name)!=getattr(inputs.parent,name) for name in fields
                    if name!='asr' and not (name=='candidate' and inputs.parent.candidate is None))
                    or (parent.asr is None)!=(inputs.parent.asr is None)
                    or parent.asr is not None and (parent.asr.context_ref,parent.asr.observation)!=(inputs.parent.asr.context_ref,inputs.parent.asr.observation)
                    or sources!=inputs.source_media_refs or precision!=inputs.precision_report_ref or raw!=inputs.precision_report_bytes or failed!=inputs.failed_unit_ids):
                raise EngineError('diagnostic_source_changed','Immutable actual diagnostic inputs changed',409)
        with self.engine.db.connect_readonly() as connection:
            self.assert_registered_ctc_work_writer(connection,held[3])
        return held,factory,ports,row

    def _diagnostic_operation_facts(self, connection, lease, inputs, observation):
        refs,observations,rows=[],[],[]
        self.engine._lease(connection,lease)
        intents={intent.dedupe_key:intent for intent in inputs.analysis_intents}
        for identifier in observation.analysis_operation_ids:
            row=connection.execute('SELECT * FROM operations WHERE id=? AND run_id=?',(identifier,lease.run_id)).fetchone()
            if row is None or row['status']!='succeeded' or not row['settled']:
                raise EngineError('analysis_operation_unsettled','Actual diagnostic Operation must be succeeded and settled',409,'reconcile')
            intent=intents.get(row['dedupe_key'])
            actual_route=c.CapabilityRoute.model_validate_json(row['route_json'])
            if (intent is None or row['step_key']!=intent.step_key or row['input_sha256']!=intent.input_sha256
                    or actual_route!=observation.method_ref.route or actual_route.route_id!=intent.route_id
                    or intent.input_sha256!=plan_payload_sha256({'input_key_sha256':inputs.input_key_sha256,
                        'method_ref':observation.method_ref.model_dump(mode='json')})):
                raise EngineError('diagnostic_source_invalid','Analysis Operation does not bind a registered input intent',422)
            actual=c.OperationObservation.model_validate_json(row['observation_json'])
            if actual.status!='succeeded' or actual.result_json is None or actual.actual_cost is None:
                raise EngineError('analysis_operation_unsettled','Actual diagnostic observation and settled cost required',409,'reconcile')
            output_sha=plan_payload_sha256(actual.result_json)
            ref=DiagnosticAnalysisOperationRefV1(operation_id=identifier,input_sha256=row['input_sha256'],
                route_sha256=digest(row['route_json']),observation_sha256=digest(row['observation_json']),output_sha256=output_sha)
            refs.append(ref);observations.append((ref,actual));rows.append(('operations','id',identifier,dict(row)))
        if not refs:
            raise EngineError('analysis_operation_unsettled','Actual ledger analysis is required before recording',409,'reconcile')
        return tuple(refs),tuple(observations),tuple(rows)

    def _diagnostic_check_refs(self, inputs, observation, operations):
        known=tuple(inputs.source_media_refs)+tuple(inputs.parent.assembly.creative_revision_refs)+(inputs.parent.assembly.quality_ref,)
        known+=tuple(receipt for receipt,_raw in inputs.parent.materials)
        completions=getattr(inputs,'completion_source_refs',())
        known+=tuple(value.ref for value in completions)
        observed_completion_refs=[]
        op_refs={ref.operation_id:ref for ref in operations}
        by_asset={ref.asset_id:ref for ref in inputs.source_media_refs}
        for check in observation.checks:
            source_assets=[]
            for ref in (*check.source_refs,check.expected_ref,check.observed_ref):
                if any(ref==value.ref for value in completions):observed_completion_refs.append(ref)
                if isinstance(ref,DiagnosticOperationOutputRefV1):
                    actual=op_refs.get(ref.operation_id)
                    if actual is None or (ref.input_sha256,ref.observation_sha256,ref.output_sha256)!=(actual.input_sha256,actual.observation_sha256,actual.output_sha256):
                        raise EngineError('diagnostic_source_invalid','Diagnostic evidence must reference the actual analysis output',422)
                elif isinstance(ref,DiagnosticSampleRefV1):
                    source=by_asset.get(ref.asset_id)
                    if (source is None or source.sha256!=ref.source_sha256
                            or ref.decoder_ref not in observation.method_ref.implementation_source_refs
                            or source.intrinsic_range is not None and ref.source_range.end_us>source.intrinsic_range.end_us):
                        raise EngineError('diagnostic_source_invalid','Decoded sample must bind the actual source and original registered decoder',422)
                    source_assets.append(source)
                elif isinstance(ref,DiagnosticMetadataRef):
                    if not any(value.kind=='qualified_resource' and value.ref==ref for value in completions):
                        raise EngineError('diagnostic_source_invalid','Resource evidence must bind an actual held qualified resource completion',422)
                elif ref not in known:
                    raise EngineError('diagnostic_source_invalid','Evidence outside the original finite input source closure',422)
                elif isinstance(ref,DiagnosticSourceMediaRefV1):
                    source_assets.append(ref)
            allowed_shots={shot for source in source_assets for shot in source.shot_ids}
            if check.shot_ids and not set(check.shot_ids)<=allowed_shots:
                raise EngineError('diagnostic_source_invalid','Check shots must come from the actual observed source',422)
            if check.check_kind!='precision_boundary' and not source_assets:
                raise EngineError('diagnostic_source_invalid','Component analysis must reference actual media, not just text',422)
            expected_role={'narration_source':'narration_audio','mix_source':'mixed_audio',
                'cover_frame':'cover','visual_source':'video','ambient_source':'mixed_audio'}.get(check.check_kind)
            if expected_role is not None and not any(source.role==expected_role for source in source_assets):
                raise EngineError('diagnostic_source_invalid','Component evidence requires its actual corresponding media source',422)
            for interval,name in ((check.intrinsic_range,'intrinsic_range'),(check.timeline_range,'timeline_range')):
                if interval is not None and not any(getattr(source,name) is not None
                        and getattr(source,name).start_us<=interval.start_us
                        and interval.end_us<=getattr(source,name).end_us for source in source_assets):
                    raise EngineError('diagnostic_source_invalid','Measured interval exceeds the real bounded source clock',422)
            if check.check_kind=='narration_source' and not any(isinstance(ref,c.RevisionRef)
                    and ref.kind=='script' for ref in (*check.source_refs,check.expected_ref)):
                raise EngineError('diagnostic_source_invalid','Narration failure must retain the actual authored script source',422)
            if check.evidence_strength=='attributed_model_assessment':
                if observation.method_ref.route.capability!='text' or not any(isinstance(ref,DiagnosticOperationOutputRefV1) for ref in (*check.source_refs,check.observed_ref)):
                    raise EngineError('diagnostic_source_invalid','Attributed model opinion retains its actual model response provenance',422)
            elif observation.method_ref.route.capability!='media_diagnosis':
                raise EngineError('diagnostic_source_invalid','Model output cannot become deterministic media measurement',422)
            if check.check_kind=='precision_boundary' and inputs.precision_report_ref is None:
                raise EngineError('diagnostic_source_invalid','Timing claims require the actual independent READY report',422)
        if any(value.ref not in observed_completion_refs for value in completions):
            raise EngineError('diagnostic_source_invalid','Every original completion must be consumed by actual attributed checks',422)

    def _diagnostic_project(self, inputs, observation):
        supported=tuple(check for check in observation.checks if check.assertion_status=='supported' and check.observed_result=='differs')
        components={check.component for check in supported if check.component is not None}
        uncertainty=tuple(dict.fromkeys(code for check in observation.checks for code in check.uncertainty_codes))
        incomplete=any(check.assertion_status=='undetermined' or check.observed_result=='unavailable' for check in observation.checks)
        if len(components)>1:
            result,component,requests='information_required',None,('competing_causes',)
        elif incomplete:
            result,component,requests='information_required',None,('analysis_inconclusive',)
        elif components:
            result,component,requests='component_repair',next(iter(components)),()
        elif inputs.failed_unit_ids or any(check.check_kind=='precision_boundary' for check in supported):
            result,component,requests='timing_only',None,()
        else:
            result,component,requests='no_component_failure',None,()
        source_ids={ref.artifact_id for check in supported if check.component==component and component is not None
                    for ref in check.source_refs if isinstance(ref,DiagnosticSourceMediaRefV1)}
        for check in supported:
            if component is not None and check.component==component:
                for ref in check.source_refs:
                    if isinstance(ref,DiagnosticSampleRefV1):
                        source_ids.update(source.artifact_id for source in inputs.source_media_refs if source.asset_id==ref.asset_id)
        artifacts=inputs.parent.assembly.media_artifacts
        while True:
            expanded=source_ids|{artifact.artifact_id for artifact in artifacts if source_ids.intersection(artifact.dependency_artifact_ids)}
            if expanded==source_ids:break
            source_ids=expanded
        affected=tuple(artifact.artifact_id for artifact in artifacts if artifact.artifact_id in source_ids)
        shots={shot for check in supported if check.component==component for shot in check.shot_ids}
        ordered=tuple(dict.fromkeys(shot for source in inputs.source_media_refs for shot in source.shot_ids if shot in shots))
        if result=='component_repair' and (not affected or component in {'visual','ambient'} and not ordered):
            result,component,requests='information_required',None,('source_mapping_incomplete',)
            affected=()
        return {'result':result,'failure_component':component,'source_shot_ids':ordered,
            'speech_change':'required' if component=='narration' else 'undetermined' if result=='information_required' else 'not_required',
            'ambient_change':'required' if component=='ambient' else 'undetermined' if result=='information_required' else 'not_required',
            'affected_artifact_ids':affected,'failed_unit_ids':inputs.failed_unit_ids,
            'intrinsic_ranges':tuple(check.intrinsic_range for check in supported if check.intrinsic_range is not None),
            'timeline_ranges':tuple(check.timeline_range for check in supported if check.timeline_range is not None),
            'uncertainty_codes':uncertainty,'information_requests':requests}

    def record_component_diagnosis(self, lease, inputs, observation):
        return self._record_component_diagnosis(lease, inputs, observation, select=True)

    def append_component_diagnosis(self, lease, inputs, observation):
        return self._record_component_diagnosis(lease, inputs, observation, select=False)

    def read_recorded_component_diagnosis(self, lease, inputs):
        self._diagnostic_inputs_current(lease, inputs)
        with self.engine.db.connect_readonly() as connection:
            self.engine._lease(connection, lease)
            indexed=connection.execute('SELECT value FROM metadata WHERE key=?',
                (RESULT_PREFIX+inputs.input_key_sha256,)).fetchone()
            if indexed is None:
                # The only legacy source is the exact validated old selection.
                indexed=connection.execute('SELECT value FROM metadata WHERE key=?',
                    (SELECT_PREFIX+inputs.parent_preparation_id,)).fetchone()
                if indexed is None:return None
                legacy=ComponentDiagnosisRefV1.model_validate_json(indexed[0])
                if legacy.input_key_sha256!=inputs.input_key_sha256:return None
            ref=ComponentDiagnosisRefV1.model_validate_json(indexed[0])
            if ref.input_key_sha256!=inputs.input_key_sha256:
                raise EngineError('diagnostic_source_changed','Unique input index belongs to another input',409)
        return self._read_explicit_diagnostic_record(lease,ref,inputs.parent_preparation_id)

    def _record_component_diagnosis(self, lease, inputs, observation, *, select):
        if type(observation) is not ComponentDiagnosticObservationV1 or observation.input_key_sha256!=inputs.input_key_sha256:
            raise EngineError('diagnostic_source_invalid','Sole typed observation must bind actual held input',422)
        held,factory,ports,row=self._diagnostic_inputs_current(lease,inputs)
        reused=self.read_recorded_component_diagnosis(lease,inputs)
        if reused is not None:
            if (reused.fact.method_ref!=observation.method_ref or reused.fact.checks!=observation.checks
                    or reused.fact.analysis_limitations!=observation.limitations
                    or tuple(ref.operation_id for ref in reused.fact.analysis_operation_refs)!=observation.analysis_operation_ids):
                raise EngineError('diagnostic_record_conflict','One input cannot acquire a different result at a new fence',409)
            self._reuse_recorded_diagnosis_writer(lease,inputs,reused,select=select)
            return reused
        if observation.method_ref not in inputs.diagnostic_method_refs:
            raise EngineError('diagnostic_source_invalid','Observation must bind an actual installed registered method',422)
        with self.engine.db.connect_readonly() as connection:
            refs,op_observations,op_rows=self._diagnostic_operation_facts(connection,lease,inputs,observation)
        self._diagnostic_check_refs(inputs,observation,refs)
        # This is the original actual factory-bound verifier, not a caller callback.
        verified=ports.verify_component_observation(inputs,observation,operation_observations=op_observations)
        if type(verified) is not ComponentDiagnosticObservationV1 or verified!=observation:
            raise EngineError('diagnostic_source_invalid','Deterministic recheck disagrees with the original attributed observation',422)
        projected=self._diagnostic_project(inputs,observation)
        fact=ComponentDiagnosticFactV1(format='current-component-diagnostic-fact-v1',input_key_sha256=inputs.input_key_sha256,
            binding=inputs.binding,parent_preparation_id=inputs.parent_preparation_id,parent_intent_sha256=inputs.parent_intent_sha256,
            authored_fence=lease.fencing_token,candidate_manifest_file_sha256=inputs.parent.candidate[1] if inputs.parent.candidate else None,
            creative_revision_refs=inputs.parent.assembly.creative_revision_refs,quality_ref=inputs.parent.assembly.quality_ref,
            request_sha256=inputs.binding.request_sha256,registration_sha256=inputs.binding.registration_sha256,
            resource_manifest_sha256=factory[6],runtime_manifest_sha256=factory[7],precision_report_ref=inputs.precision_report_ref,
            failure_event_kind='precision_timing' if inputs.precision_report_ref is not None else 'component_observation',
            source_media_refs=inputs.source_media_refs,method_ref=observation.method_ref,analysis_operation_refs=refs,
            checks=observation.checks,analysis_limitations=observation.limitations,**projected)
        raw=plan_payload_bytes(fact)
        if len(raw)>LIMIT:
            raise EngineError('diagnostic_source_invalid','Bounded complete diagnostic fact required',422)
        record_sha=hashlib.sha256(raw).hexdigest()
        record_id=RECORD_PREFIX+inputs.input_key_sha256+'.'+record_sha
        ref=ComponentDiagnosisRefV1(format='current-component-diagnosis-ref-v1',record_id=record_id,
            content_sha256=record_sha,size=len(raw),input_key_sha256=inputs.input_key_sha256)
        issuer=self._production_authorization.issuer()
        self._diagnostic_inputs_current(lease,inputs)
        with issuer.current_guard(self._production_authorization.registered(lease)) as guard:
            with self.engine.db.transaction() as connection:
                snapshots,run,production,request=self._diagnostic_source_rows(connection,lease,row,inputs.parent,
                    inputs.source_media_refs,inputs.diagnostic_method_refs,continuation=held[4])
                issuer._guard(connection,guard);issuer._request(connection,production,run,guard.identity)
                self.assert_registered_ctc_work_writer(connection,held[3]+op_rows)
                current_refs,_observations,_rows=self._diagnostic_operation_facts(connection,lease,inputs,observation)
                if current_refs!=refs:
                    raise EngineError('diagnostic_source_changed','Original settled analysis changed before record commit',409)
                pointer_key=SELECT_PREFIX+inputs.parent_preparation_id
                old=connection.execute('SELECT value FROM metadata WHERE key=?',(pointer_key,)).fetchone()
                if select and old is not None:
                    saved=ComponentDiagnosisRefV1.model_validate_json(old[0])
                    if saved.input_key_sha256==ref.input_key_sha256 and saved.content_sha256!=ref.content_sha256:
                        raise EngineError('diagnostic_record_conflict','One stable input cannot acquire conflicting immutable result bytes',409)
                    if saved!=ref:
                        raise EngineError('diagnostic_record_conflict','Original selected diagnosis cannot be overwritten',409)
                existing=connection.execute('SELECT value FROM metadata WHERE key=?',(record_id,)).fetchone()
                index_key=RESULT_PREFIX+inputs.input_key_sha256
                indexed=connection.execute('SELECT value FROM metadata WHERE key=?',(index_key,)).fetchone()
                ref_body=plan_payload_bytes(ref).decode('utf-8')
                if indexed is not None and indexed[0]!=ref_body:
                    raise EngineError('diagnostic_record_conflict','One exact input already has different immutable result',409)
                if existing is not None and existing[0].encode('utf-8')!=raw:
                    raise EngineError('diagnostic_record_conflict','Immutable diagnostic record bytes conflict',409)
                if existing is None:
                    connection.execute('INSERT INTO metadata(key,value) VALUES(?,?)',(record_id,raw.decode('utf-8')))
                    self.engine._event(connection,run,'production.component_diagnosis_recorded',record_sha)
                if indexed is None:
                    connection.execute('INSERT INTO metadata(key,value) VALUES(?,?)',(index_key,ref_body))
                if select and old is None:
                    connection.execute('INSERT INTO metadata(key,value) VALUES(?,?)',(pointer_key,ref_body))
                self.assert_registered_ctc_work_writer(connection,held[3]+op_rows+snapshots)
                issuer._guard(connection,guard)
            self.assert_current_production_services(lease,factory[0],factory[1])
        registered=RegisteredComponentDiagnosisV1(ref,fact)
        with self._lock:
            if not hasattr(self,'_diagnostic_records_held'):self._diagnostic_records_held={}
            self._diagnostic_records_held[id(registered)]=(registered,lease,threading.get_ident(),held[3]+op_rows+snapshots,inputs)
        return registered

    def _reuse_recorded_diagnosis_writer(self, lease, inputs, recorded, *, select):
        with self._lock:held=self._diagnostic_records_held[id(recorded)]
        issuer=self._production_authorization.issuer()
        with issuer.current_guard(self._production_authorization.registered(lease)) as guard, self.engine.db.transaction() as connection:
            run=self.engine._lease(connection,lease)
            production=self.engine._production(connection,run['production_id'])
            issuer._guard(connection,guard);issuer._request(connection,production,run,guard.identity)
            self.assert_registered_ctc_work_writer(connection,held[3])
            body=plan_payload_bytes(recorded.ref).decode('utf-8')
            index_key=RESULT_PREFIX+inputs.input_key_sha256
            indexed=connection.execute('SELECT value FROM metadata WHERE key=?',(index_key,)).fetchone()
            if indexed is not None and indexed[0]!=body:
                raise EngineError('diagnostic_record_conflict','Original unique result index changed',409)
            old=connection.execute('SELECT value FROM metadata WHERE key=?',(SELECT_PREFIX+inputs.parent_preparation_id,)).fetchone()
            if select and old is not None and old[0]!=body:
                raise EngineError('diagnostic_record_conflict','Original default record cannot replace a selection',409)
            if indexed is None:connection.execute('INSERT INTO metadata(key,value) VALUES(?,?)',(index_key,body))
            if select and old is None:connection.execute('INSERT INTO metadata(key,value) VALUES(?,?)',(SELECT_PREFIX+inputs.parent_preparation_id,body))
            self.assert_registered_ctc_work_writer(connection,held[3]);issuer._guard(connection,guard)

    def diagnostic_block_after_verified(self, lease, preparation_id, manifest, verified):
        """An extra denial after whole verify succeeded; never a publishing permit."""
        from video_creator.domain.component_diagnosis import CurrentFinalDiagnosticSnapshotV1,DiagnosticRepairSourceV1
        from video_creator.domain.bundle import VerifiedBundleMaterial
        if type(verified) is not VerifiedBundleMaterial:
            raise EngineError('diagnostic_source_denied','Original whole-verifier result required before an extra diagnostic block',403)
        with self._lock:
            values=[value for value in getattr(self,'_diagnostic_records_held',{}).values()
                if value[1]==lease and value[2]==threading.get_ident()
                and value[0].fact.parent_preparation_id==preparation_id and len(value)>=5]
        unique={value[0].ref.content_sha256:value for value in values}
        if not unique:return None
        if len(unique)!=1:
            raise EngineError('diagnostic_record_conflict','Exactly one original diagnosis for the verified preparation required',409)
        hold=next(iter(unique.values()));registered=hold[0];fact=registered.fact
        if fact.result not in {'component_repair','information_required'}:return None
        factory,_ports=self._diagnostic_factory(lease)
        with self.engine.db.connect_readonly() as connection:
            self.engine._lease(connection,lease)
            self.assert_registered_ctc_work_writer(connection,hold[3])
            row,_production,_request,binding,prepared,_intent,_items=self._final_prepared(lease,preparation_id)
        if binding!=fact.binding or digest(row['intent_json'])!=fact.parent_intent_sha256:
            raise EngineError('diagnostic_source_changed','Whole verified parent differs from original diagnosis',409)
        raw=(canonical(manifest)+'\n').encode('utf-8');file_sha=hashlib.sha256(raw).hexdigest()
        if fact.candidate_manifest_file_sha256 is not None and file_sha!=fact.candidate_manifest_file_sha256:
            raise EngineError('diagnostic_source_changed','Original authenticated candidate cannot be replaced',409)
        self._write('CurrentFinalCandidates','candidate-'+file_sha,raw)
        snapshot=CurrentFinalDiagnosticSnapshotV1(preparation_id=preparation_id,
            preparation_intent_sha256=fact.parent_intent_sha256,candidate_manifest_file_sha256=file_sha,
            ready_material_refs=prepared.materials,diagnostic_ref=registered.ref,
            state='repair_required' if fact.result=='component_repair' else 'waiting_diagnosis',
            reason_code='component_repair_required' if fact.result=='component_repair' else 'analysis_inconclusive',
            information_requests=fact.information_requests,
            repair=DiagnosticRepairSourceV1(diagnostic_ref=registered.ref,precision_report_ref=fact.precision_report_ref,
                affected_artifact_ids=fact.affected_artifact_ids,failed_unit_ids=fact.failed_unit_ids,
                allowed_action='regenerate_affected_media') if fact.result=='component_repair' else None)
        self.assert_current_production_services(lease,factory[0],factory[1])
        return self._retain_final_assessment(lease,binding,snapshot)

    def _read_diagnosis_ref_writer(self, connection, lease, ref, inputs):
        saved=connection.execute('SELECT value FROM metadata WHERE key=?',(ref.record_id,)).fetchone()
        if saved is None:
            raise EngineError('diagnostic_record_unavailable','Referenced immutable record is missing',503)
        raw=saved[0].encode('utf-8')
        if (len(raw),hashlib.sha256(raw).hexdigest())!=(ref.size,ref.content_sha256):
            raise EngineError('diagnostic_source_invalid','Referenced complete diagnostic bytes changed',422)
        try:fact=ComponentDiagnosticFactV1.model_validate_json(raw)
        except ValidationError:raise EngineError('diagnostic_source_invalid','Immutable diagnostic fact is damaged',422) from None
        if (fact.input_key_sha256!=inputs.input_key_sha256 or fact.binding!=inputs.binding
                or fact.parent_preparation_id!=inputs.parent_preparation_id or fact.parent_intent_sha256!=inputs.parent_intent_sha256
                or plan_payload_bytes(fact)!=raw):
            raise EngineError('diagnostic_source_changed','Original diagnostic source/binding changed',409)
        return RegisteredComponentDiagnosisV1(ref,fact)

    def read_component_diagnosis(self, lease, continuation):
        """Read only the exact ref in the current checkpoint; never select latest."""
        from video_creator.application.current_final_evidence_journal import PREFIX,parse_journal,prepared_current
        from video_creator.domain.component_diagnosis import CurrentFinalDiagnosticContinuationV1
        from video_creator.domain.current_final_evidence import CurrentFinalEvidenceContinuation
        if type(continuation) not in {CurrentFinalDiagnosticContinuationV1,CurrentFinalEvidenceContinuation}:
            raise EngineError('final_evidence_claim_required','Exact diagnostic continuation type required',409)
        issuer=self._production_authorization.issuer()
        with issuer.current_guard(self._production_authorization.registered(lease)) as guard:
            with self.engine.db.connect_readonly() as connection:
                self.engine._lease(connection,lease)
                saved=connection.execute('SELECT * FROM metadata WHERE key=?',(PREFIX+lease.run_id,)).fetchone()
                if saved is None:
                    raise EngineError('final_evidence_claim_required','Explicit diagnostic checkpoint missing',409)
                journal=parse_journal(saved['value'],now=self.engine.clock())
                prepared_current(self.engine,connection,journal)
                issuer._guard(connection,guard)
                if (journal.binding!=continuation.binding or journal.snapshot!=continuation.snapshot
                        or journal.control.phase!='executing' or journal.control.execution_fence!=lease.fencing_token
                        or continuation.execution_fence!=lease.fencing_token):
                    raise EngineError('final_evidence_claim_required','Current diagnostic claim/fence changed',409)
                source,source_row=self._read_source_writer(connection,saved['value'],journal)
                ref=source.diagnostic_ref if source is not None else getattr(continuation.snapshot,'diagnostic_ref',None)
                if ref is None:
                    return None
                selected=connection.execute('SELECT * FROM metadata WHERE key=?',(SELECT_PREFIX+journal.snapshot.preparation_id,)).fetchone()
                result=connection.execute('SELECT * FROM metadata WHERE key=?',(RESULT_PREFIX+ref.input_key_sha256,)).fetchone()
                if selected is None or ComponentDiagnosisRefV1.model_validate_json(selected['value'])!=ref:
                    raise EngineError('diagnostic_source_changed','Original current journal/source/selected must agree',409)
                if result is None:
                    # Legacy v1 predates this index; its exact selected input is
                    # still verified by the pure full immutable reader below.
                    if source is not None and source.format=='current-final-diagnostic-source-v2':
                        raise EngineError('diagnostic_source_changed','Committed v2 selection requires its unique result index',409)
                elif ComponentDiagnosisRefV1.model_validate_json(result['value'])!=ref:
                    raise EngineError('diagnostic_source_changed','Current selected diagnosis and unique input result disagree',409)
                current_rows=(('metadata','key',selected['key'],dict(selected)),
                    ('metadata','key',RESULT_PREFIX+ref.input_key_sha256,dict(result) if result is not None else None))
                if source_row is not None:current_rows+=(('metadata','key',source_row['key'],dict(source_row)),)
        registered=self._read_explicit_diagnostic_record(lease,ref,continuation.snapshot.preparation_id,continuation=continuation)
        with self.engine.db.connect_readonly() as connection:
            self.engine._lease(connection,lease)
            self.assert_registered_ctc_work_writer(connection,current_rows)
        with self._lock:
            held=self._diagnostic_records_held[id(registered)]
            self._diagnostic_records_held[id(registered)]=(*held[:3],held[3]+current_rows,held[4])
        return registered

    def _read_explicit_diagnostic_record(self, lease, ref, preparation_id, *, continuation=None):
        """Shared pure source reader; caller must establish journal or lineage ref."""
        factory,ports=self._diagnostic_factory(lease)
        methods=self._diagnostic_methods(lease,factory,ports)
        issuer=self._production_authorization.issuer()
        with issuer.current_guard(self._production_authorization.registered(lease)) as guard:
            from video_creator.application.bundles import strict_json
            with self.engine.db.connect_readonly() as connection:
                original=connection.execute('SELECT value FROM metadata WHERE key=?',(INPUT_PREFIX+ref.input_key_sha256,)).fetchone()
                if original is None:
                    raise EngineError('diagnostic_source_changed','Original explicit registered input missing',409)
                original_body=strict_json(original[0].encode('utf-8'))
                if not isinstance(original_body,dict) or set(original_body)!={'format','stable','analysis_intents'} or original_body['format'] not in {'registered-component-diagnostic-input-v1','registered-component-diagnostic-input-v2'} or not isinstance(original_body['stable'],dict):
                    raise EngineError('diagnostic_source_invalid','Strict original registered input body required',422)
                original_candidate=original_body['stable'].get('candidate_manifest_file_sha256')
            row,inputs,stable=self._diagnostic_input_value(lease,preparation_id,
                methods,continuation=continuation,original_candidate_sha=original_candidate)
            completion_captures=()
            if original_body['format']=='registered-component-diagnostic-input-v2':
                inputs,stable,completion_captures=self._diagnostic_v2_inputs(lease,row,inputs,stable,original[0])
            if ref.input_key_sha256!=inputs.input_key_sha256:
                raise EngineError('diagnostic_source_changed','Explicit diagnosis belongs to a different actual source input',409)
            from video_creator.application.affected_repair_service import canonical_body
            expected=canonical_body({'format':original_body['format'],
                'stable':stable,'analysis_intents':inputs.analysis_intents})
            with self.engine.db.connect_readonly() as connection:
                stored=connection.execute('SELECT * FROM metadata WHERE key=?',(INPUT_PREFIX+inputs.input_key_sha256,)).fetchone()
                if stored is None or stored['value']!=expected:
                    raise EngineError('diagnostic_source_changed','Original registered diagnostic input is absent or changed',409)
                registered=self._read_diagnosis_ref_writer(connection,lease,ref,inputs)
                fact=registered.fact
                if (fact.method_ref not in methods or fact.source_media_refs!=inputs.source_media_refs
                        or fact.precision_report_ref!=inputs.precision_report_ref
                        or fact.failed_unit_ids!=inputs.failed_unit_ids):
                    raise EngineError('diagnostic_source_changed','Immutable diagnostic source facts no longer match original input',409)
                observation=ComponentDiagnosticObservationV1(format='current-component-diagnostic-observation-v1',
                    input_key_sha256=inputs.input_key_sha256,method_ref=fact.method_ref,
                    analysis_operation_ids=tuple(value.operation_id for value in fact.analysis_operation_refs),
                    checks=fact.checks,limitations=fact.analysis_limitations)
                refs,observations,op_rows=self._diagnostic_operation_facts(connection,lease,inputs,observation)
                if refs!=fact.analysis_operation_refs:
                    raise EngineError('diagnostic_source_changed','Original settled analysis bytes changed',409)
                snapshots,*_=self._diagnostic_source_rows(connection,lease,row,inputs.parent,
                    inputs.source_media_refs,methods,continuation=continuation)
                snapshots+=op_rows+completion_captures+(('metadata','key',stored['key'],dict(stored)),)
                record_row=connection.execute('SELECT * FROM metadata WHERE key=?',(ref.record_id,)).fetchone()
                snapshots+=(('metadata','key',ref.record_id,dict(record_row)),)
                issuer._guard(connection,guard)
            self._diagnostic_check_refs(inputs,observation,refs)
            verified=ports.verify_component_observation(inputs,observation,operation_observations=observations)
            if type(verified) is not ComponentDiagnosticObservationV1 or verified!=observation:
                raise EngineError('diagnostic_source_invalid','Original attributed observation fails its registered verifier',422)
            if any(getattr(fact,name)!=value for name,value in self._diagnostic_project(inputs,observation).items()):
                raise EngineError('diagnostic_source_invalid','Immutable derived conclusion differs from the original verified checks',422)
            with self.engine.db.connect_readonly() as connection:
                self.engine._lease(connection,lease)
                self.assert_registered_ctc_work_writer(connection,snapshots)
                issuer._guard(connection,guard)
            self.assert_current_production_services(lease,factory[0],factory[1])
        with self._lock:
            if not hasattr(self,'_diagnostic_records_held'):self._diagnostic_records_held={}
            self._diagnostic_records_held[id(registered)]=(registered,lease,threading.get_ident(),snapshots,inputs)
        return registered

    def prepare_affected_recipe_proposal(self, lease, continuation):
        from video_creator.domain.affected_recipe_mapping import map_affected_recipe
        from video_creator.domain.affected_recipe import RegisteredProductionPlanV3
        registered=self.read_component_diagnosis(lease,continuation)
        if registered is None or registered.fact.result!='component_repair':
            raise EngineError('diagnostic_component_required','Actual explicit component repair diagnosis required',409)
        fact=registered.fact
        with self._lock:
            inputs=self._diagnostic_records_held[id(registered)][4]
        plan_ref=next((ref for ref in inputs.parent.assembly.creative_revision_refs if ref.kind=='plan'),None)
        storyboard_ref=next((ref for ref in inputs.parent.assembly.creative_revision_refs if ref.kind=='storyboard'),None)
        if plan_ref is None or storyboard_ref is None:
            raise EngineError('source_mapping_incomplete','Actual original plan and storyboard references required',503)
        revisions={value.revision_id:value for value in self.creative_revisions(lease)}
        plan_revision=revisions.get(plan_ref.revision_id)
        storyboard=revisions.get(storyboard_ref.revision_id)
        if plan_revision is None or storyboard is None:
            raise EngineError('source_material_missing','Original plan/storyboard revisions unavailable',503)
        plan=self.validate_registered_plan_v3(lease,plan_revision)
        if type(plan) is not RegisteredProductionPlanV3:
            raise EngineError('finite_recipe_missing','Actual whole-plan finite recipe catalog required',403)
        roles=tuple(role for artifact in inputs.parent.assembly.media_artifacts
            if artifact.artifact_id in fact.affected_artifact_ids for role in artifact.roles)
        proposal=map_affected_recipe(plan.repair_targets,parent_preparation_id=fact.parent_preparation_id,
            affected_artifact_ids=fact.affected_artifact_ids,failed_unit_ids=fact.failed_unit_ids,
            failed_ranges=fact.timeline_ranges,storyboard_shots=storyboard.body['shots'],actual_failed_roles=roles,
            source_shot_ids=fact.source_shot_ids,failure_component=fact.failure_component,
            regenerate_narration=fact.speech_change=='required',ambient_required=fact.ambient_change=='required')
        # Data preparation performs no admissions, quota reservation or provider dispatch.
        self.read_component_diagnosis(lease,continuation)
        return proposal
