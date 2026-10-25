"""Same-current, finite diagnosed recipe admission; data never grants dispatch."""

import threading

from pydantic import ValidationError

from video_creator.application.engine import digest
from video_creator.application.affected_repair_service import canonical_body, COMMAND_PREFIX
from video_creator.application.current_production_blockers import bound_context, require_settled
from video_creator.domain import contracts as c
from video_creator.domain.affected_recipe import RegisteredProductionPlanV3, AffectedRepairProposalV2
from video_creator.domain.component_diagnosis import (
    AffectedDiagnosticSourceV1, AffectedRepairExecutionDiagnosedV1,
    ComponentDiagnosticFactV1, CurrentFinalDiagnosticContinuationV1,
)
from video_creator.domain.plan_repair_targets import plan_payload_sha256, plan_payload_bytes
from video_creator.domain.errors import EngineError


FORMAT='current-final-affected-execution-v2-diagnostic-v1'
DERIVED=frozenset({'repair_command_sha256','source_sha256','steps','child_preparation_id','child_intent_sha256','child_asr'})


def diagnosed_source(command):
    try:
        return AffectedDiagnosticSourceV1.model_validate_json(canonical_body(
            {key:value for key,value in command.items() if key not in DERIVED}))
    except (ValidationError,TypeError,ValueError):
        raise EngineError('affected_command_invalid','Strict complete diagnosed command source required',422) from None


class DiagnosedAffectedService:
    def read_diagnosed_affected_execution_inputs(self, lease, continuation):
        from video_creator.application.bundles import strict_json
        from video_creator.domain.affected_recipe import AffectedRepairReadSetV2
        from video_creator.domain.affected_repair_steps import affected_recipe_step
        from video_creator.application.affected_repair_service import MASTERS_PREFIX
        record=self.read_component_diagnosis(lease,continuation)
        if record is None:
            raise EngineError('diagnostic_record_unavailable','Explicit current source record required for command recovery',503)
        with self.engine.db.connect_readonly() as connection:
            _raw,journal,parent,*_=self._affected_claim(connection,lease,continuation)
            matches=[]
            for stored in connection.execute('SELECT value FROM metadata WHERE key LIKE ?',(COMMAND_PREFIX+'%',)):
                body=strict_json(stored[0].encode('utf-8'))
                if (body.get('format')==FORMAT and body.get('binding')==journal.binding.model_dump(mode='json')
                        and body.get('parent_preparation_id')==parent['id'] and body.get('diagnostic_ref')==record.ref.model_dump(mode='json')):
                    matches.append(body)
        if len(matches)!=1:
            raise EngineError('affected_execution_unavailable' if not matches else 'affected_command_conflict',
                'One immutable registered diagnosed command required',503 if not matches else 409)
        command=matches[0];source=diagnosed_source(command);p=source.proposal
        execution=AffectedRepairExecutionDiagnosedV1(source.binding,lease.fencing_token,source.parent_preparation_id,
            source.parent_intent_sha256,command['repair_command_sha256'],source.source_report_ref,p.affected_artifact_ids,
            p.failed_unit_ids,p.requested_action,p.changed_media_roles,p.impacted_shot_ids,p.regenerated_shot_ids,
            p.recipe_id,p.projection_sha256,p.recipe_binding_sha256,p.component_target_ids,source.diagnostic_ref,source.input_key_sha256)
        held=self._affected_services(lease)
        self._production_services_runtime._current_final_execution_facts(lease,held[1],held[5])
        with self._lock:self._affected_execution_held[id(execution)]=(execution,lease,threading.get_ident(),continuation)
        with self.engine.db.connect_readonly() as connection:
            self._affected_execution(connection,lease,execution)
            saved=connection.execute('SELECT value FROM metadata WHERE key=?',(MASTERS_PREFIX+execution.repair_command_sha256,)).fetchone()
        masters=self.observe_current_affected_masters(lease,execution,
            step_key=affected_recipe_step(execution,'master',component_target_id='production-master')[0]) if saved else None
        issuer=self._production_authorization.issuer()
        with issuer.current_guard(self._production_authorization.registered(lease)) as guard:
            parent_read=self._read_current_final_continuation_inputs(lease,continuation,guard)
            child_read=self._read_current_final_continuation_inputs(lease,continuation,guard,
                selected_preparation_id=command['child_preparation_id']) if command['child_preparation_id'] else None
        return AffectedRepairReadSetV2(execution,parent_read,child_read,masters)

    def assert_diagnostic_command_targets_writer(self, connection, lease, command, *, guard=None):
        from video_creator.application.bundles import strict_json
        source=diagnosed_source(command)
        held=self._affected_services_writer(lease)
        runtime=self._production_services_runtime
        run,production,request,binding=bound_context(self.engine,connection,lease.run_id,runtime.sha256)
        self.engine._lease(connection,lease)
        projection=source.repair_targets
        if (source.binding!=binding or projection.binding!=binding
                or (source.resource_manifest_sha256,source.runtime_manifest_sha256)!=held[6:8]
                or (projection.resource_manifest_sha256,projection.runtime_manifest_sha256)!=held[6:8]
                or source.proposal.projection_sha256!=plan_payload_sha256(projection)):
            raise EngineError('plan_repair_source_changed','Exact diagnosed request, held resources and projection required',409)
        plan_row=connection.execute('SELECT * FROM creative_revisions WHERE id=? AND run_id=?',
            (source.plan_ref.revision_id,lease.run_id)).fetchone()
        if plan_row is None or plan_row['content_sha256']!=source.plan_ref.content_sha256 or digest(plan_row['body'])!=source.plan_ref.content_sha256:
            raise EngineError('plan_repair_source_changed','Actual whole-plan immutable bytes changed',409)
        revision=c.CreativeRevision.model_validate_json(plan_row['body'])
        try:plan=RegisteredProductionPlanV3.model_validate_json(canonical_body(revision.body))
        except ValidationError:raise EngineError('plan_repair_body_invalid','Actual strict finite whole plan required',422) from None
        if plan.repair_targets!=projection:
            raise EngineError('plan_repair_source_changed','Command cannot substitute the approved whole-plan targets',409)
        for ref in (projection.script_ref,projection.storyboard_ref,source.quality_ref):
            row=connection.execute('SELECT * FROM creative_revisions WHERE id=? AND run_id=?',(ref.revision_id,lease.run_id)).fetchone()
            if row is None or row['content_sha256']!=ref.content_sha256 or digest(row['body'])!=ref.content_sha256:
                raise EngineError('plan_repair_source_changed','Original input/quality revision changed',409)
        ref=source.diagnostic_ref
        row=connection.execute('SELECT value FROM metadata WHERE key=?',(ref.record_id,)).fetchone()
        if row is None or (len(row[0].encode('utf-8')),digest(row[0]))!=(ref.size,ref.content_sha256):
            raise EngineError('diagnostic_source_changed','Actual immutable diagnosis reference changed',409)
        fact=ComponentDiagnosticFactV1.model_validate_json(row[0])
        if (plan_payload_bytes(fact)!=row[0].encode('utf-8') or fact.input_key_sha256!=source.input_key_sha256
                or fact.binding!=binding or fact.parent_preparation_id!=source.parent_preparation_id
                or fact.parent_intent_sha256!=source.parent_intent_sha256 or fact.result!='component_repair'
                or fact.precision_report_ref!=source.source_report_ref
                or fact.affected_artifact_ids!=source.affected_artifact_ids or fact.failed_unit_ids!=source.failed_unit_ids):
            raise EngineError('diagnostic_source_changed','Command requires the exact real component failure source',409)
        with self._lock:
            readers=[value for value in getattr(self,'_diagnostic_records_held',{}).values()
                if value[1]==lease and value[2]==threading.get_ident() and value[0].ref==ref and len(value)>=5]
        if not readers:
            raise EngineError('diagnostic_source_denied','Actual same-current verified diagnostic reader must be held',403)
        for reader in readers:self.assert_registered_ctc_work_writer(connection,reader[3])
        parent=connection.execute('SELECT * FROM bundle_revisions WHERE id=? AND run_id=?',
            (source.parent_preparation_id,lease.run_id)).fetchone()
        if parent is None or digest(parent['intent_json'])!=source.parent_intent_sha256:
            raise EngineError('diagnostic_source_changed','Original immutable parent intent changed',409)
        recipe=next((r for r in projection.recipes if r.recipe_id==source.proposal.recipe_id),None)
        if recipe is None or plan_payload_sha256(recipe)!=source.proposal.recipe_binding_sha256:
            raise EngineError('affected_target_denied','Exact approved finite recipe required',403)
        storyboard_row=connection.execute('SELECT body FROM creative_revisions WHERE id=? AND run_id=?',
            (projection.storyboard_ref.revision_id,lease.run_id)).fetchone()
        storyboard=c.CreativeRevision.model_validate_json(storyboard_row[0])
        from video_creator.domain.affected_recipe_mapping import map_affected_recipe
        parent_inputs=readers[0][4]
        roles=tuple(role for artifact in parent_inputs.parent.assembly.media_artifacts
            if artifact.artifact_id in fact.affected_artifact_ids for role in artifact.roles)
        expected=map_affected_recipe(projection,parent_preparation_id=fact.parent_preparation_id,
            affected_artifact_ids=fact.affected_artifact_ids,failed_unit_ids=fact.failed_unit_ids,
            failed_ranges=fact.timeline_ranges,storyboard_shots=storyboard.body['shots'],actual_failed_roles=roles,
            source_shot_ids=fact.source_shot_ids,failure_component=fact.failure_component,
            regenerate_narration=fact.speech_change=='required',ambient_required=fact.ambient_change=='required')
        if source.proposal!=expected:
            raise EngineError('affected_target_denied','Command differs from the single actual finite diagnosis mapper',403)
        indexed={target.target_id:target for target in projection.component_targets}
        selected=tuple(target for target in projection.component_targets if target.target_id in source.proposal.component_target_ids)
        if tuple(target.target_id for target in selected)!=source.proposal.component_target_ids or not set(source.proposal.component_target_ids)<=set(recipe.component_target_ids):
            raise EngineError('affected_target_denied','Distinct ordered original recipe components required',403)
        if set(source.route_bindings)!=set(source.proposal.component_target_ids)|{'production-master'}:
            raise EngineError('affected_route_denied','Complete exact selected component and master routes required',403)
        for identifier,route in source.route_bindings.items():
            current=connection.execute('SELECT body FROM routes WHERE id=?',(route.route_id,)).fetchone()
            if current is None or c.CapabilityRoute.model_validate_json(current[0])!=route or not route.verified:
                raise EngineError('affected_route_denied','Actual configured registered route changed',403)
            if identifier=='production-master':
                if route.route_id!=held[0].master_index_route_id or route.source!='owned_local' or route.credential_ref or route.max_operation_cost.units():
                    raise EngineError('affected_route_denied','Original actual free master-index route required',403)
            elif plan_payload_sha256(route)!=indexed[identifier].route_sha256:
                raise EngineError('affected_route_denied','Target route SHA differs from the approved whole plan',403)
        if 'steps' in command:
            from video_creator.domain.affected_repair_steps import affected_recipe_step_identity
            expected_steps={}
            sha=plan_payload_sha256(source)
            for identifier in (*source.proposal.component_target_ids,'production-master'):
                stage='master' if identifier=='production-master' else {'shot_clip':'picture','narration':'narration','edit':'edit'}[indexed[identifier].kind]
                key,input_sha,dedupe=affected_recipe_step_identity(binding.model_dump(mode='json'),sha,stage,component_target_id=identifier)
                expected_steps[key]={'stage':stage,'component_target_id':identifier,'input_sha256':input_sha,
                    'dedupe_key':dedupe,'route_id':source.route_bindings[identifier].route_id}
            if command['steps']!=expected_steps:
                raise EngineError('affected_step_denied','Command must retain its exact registered component Step descriptors',403)
        if production['revision_cycles']>min(request.automation.max_revision_cycles,projection.max_revision_cycles):
            raise EngineError('revision_limit','Original finite production revision allowance exceeded',409)
        issuer=self._production_authorization.issuer()
        if guard is not None:
            issuer._guard(connection,guard);issuer._request(connection,production,run,guard.identity)
        if held[5]:
            if guard is None:
                record=issuer._record(connection,issuer._current_binding(connection,production,run).policy_ref,
                    self.engine._authorization_identity(production['owner']),request,production,action='execute_plan')
            else:_request,record=issuer._bound(connection,guard,production,run,action='execute_plan')
            approval=issuer._earlier_action(connection,production,run,record,lease,'execute_plan')
            if (approval.target_id,approval.target_sha256)!=(source.plan_ref.revision_id,source.plan_ref.content_sha256):
                raise EngineError('affected_target_denied','Actual execute_plan admission must cover this whole plan',403)
            if projection.rights_declaration_sha256!=issuer._rights_sha(record.policy):
                raise EngineError('production_rights_conflict','Actual current policy rights changed',409)
        else:
            declaration=held[1].declaration;now=self.engine.clock()
            if (declaration.declaring_subject!=production['owner'] or production['project_id'] not in declaration.project_ids
                    or declaration.expires_at_us is not None and declaration.expires_at_us<=now
                    or plan_payload_sha256(declaration)!=projection.rights_declaration_sha256
                    or any(r.valid_from_us is not None and r.valid_from_us>now or r.expires_at_us is not None and r.expires_at_us<=now for r in declaration.rights)):
                raise EngineError('production_rights_expired','Actual human declaration is no longer current',403)
            approvals=[]
            for row in connection.execute('SELECT * FROM decisions WHERE run_id=? ORDER BY rowid',(lease.run_id,)):
                decision=c.ReviewDecision.model_validate(strict_json(row['body'].encode('utf-8')))
                if decision.target_revision_id==source.plan_ref.revision_id:
                    if digest(row['body'])!=row['request_sha256'] or row['result_json']!=row['body']:
                        raise EngineError('production_review_invalid','Actual whole-plan review bytes changed',422)
                    approvals.append(decision)
            if len(approvals)!=1 or approvals[0].action!='approve':
                raise EngineError('affected_target_denied','Actual whole-plan human approval required',403)
        return source

    def authorize_diagnosed_affected_execution(self, lease, continuation, proposal):
        from video_creator.application.bundles import strict_json
        from video_creator.domain.affected_repair_steps import affected_recipe_step
        if type(continuation) is not CurrentFinalDiagnosticContinuationV1 or type(proposal) is not AffectedRepairProposalV2:
            raise EngineError('affected_proposal_invalid','Exact sole diagnosed continuation and proposal required',422)
        expected=self.prepare_affected_recipe_proposal(lease,continuation)
        if proposal!=expected:
            raise EngineError('affected_proposal_invalid','Proposal differs from the original registered diagnosis mapper',422)
        registered=self.read_component_diagnosis(lease,continuation)
        held=self._affected_services(lease)
        with self._lock:record_hold=self._diagnostic_records_held[id(registered)]
        inputs=record_hold[4];fact=registered.fact
        plan_ref=next(ref for ref in inputs.parent.assembly.creative_revision_refs if ref.kind=='plan')
        revision=next(r for r in self.creative_revisions(lease) if r.revision_id==plan_ref.revision_id)
        plan=self.validate_registered_plan_v3(lease,revision)
        targets={t.target_id:t for t in plan.repair_targets.component_targets}
        routes={identifier:self.engine.configured_route(targets[identifier].route_id) for identifier in proposal.component_target_ids}
        routes['production-master']=self.engine.configured_route(held[0].master_index_route_id)
        admissions=self._production_services_runtime._current_final_execution_facts(lease,held[1],held[5])
        source=AffectedDiagnosticSourceV1(format=FORMAT,binding=fact.binding,parent_preparation_id=fact.parent_preparation_id,
            parent_intent_sha256=fact.parent_intent_sha256,source_report_ref=fact.precision_report_ref,
            diagnostic_ref=registered.ref,input_key_sha256=fact.input_key_sha256,
            failure_source={'format':'precision_with_component_diagnosis' if fact.precision_report_ref else 'component_diagnosis',
                'diagnostic_ref':registered.ref,'precision_report_ref':fact.precision_report_ref},
            affected_artifact_ids=proposal.affected_artifact_ids,failed_unit_ids=proposal.failed_unit_ids,
            requested_action=proposal.requested_action,changed_media_roles=proposal.changed_media_roles,
            affected_shot_ids=proposal.impacted_shot_ids,proposal=proposal,plan_ref=plan_ref,
            quality_ref=inputs.parent.assembly.quality_ref,repair_targets=plan.repair_targets,
            route_bindings=routes,resource_manifest_sha256=held[6],runtime_manifest_sha256=held[7])
        sha=plan_payload_sha256(source)
        execution=AffectedRepairExecutionDiagnosedV1(source.binding,lease.fencing_token,source.parent_preparation_id,
            source.parent_intent_sha256,sha,source.source_report_ref,proposal.affected_artifact_ids,proposal.failed_unit_ids,
            proposal.requested_action,proposal.changed_media_roles,proposal.impacted_shot_ids,proposal.regenerated_shot_ids,
            proposal.recipe_id,proposal.projection_sha256,proposal.recipe_binding_sha256,proposal.component_target_ids,
            registered.ref,registered.ref.input_key_sha256)
        steps={}
        for identifier in (*proposal.component_target_ids,'production-master'):
            stage='master' if identifier=='production-master' else {'shot_clip':'picture','narration':'narration','edit':'edit'}[targets[identifier].kind]
            key,input_sha,dedupe=affected_recipe_step(execution,stage,component_target_id=identifier)
            steps[key]={'stage':stage,'component_target_id':identifier,'input_sha256':input_sha,
                'dedupe_key':dedupe,'route_id':routes[identifier].route_id}
        body=canonical_body({**source.model_dump(mode='json'),'repair_command_sha256':sha,'source_sha256':sha,
            'steps':steps,'child_preparation_id':None,'child_intent_sha256':None})
        issuer=self._production_authorization.issuer()
        with issuer.current_guard(self._production_authorization.registered(lease)) as guard:
            with self.engine.db.transaction() as connection:
                checkpoint,journal,parent,run,production,request=self._affected_claim(connection,lease,continuation)
                require_settled(connection,lease.run_id)
                self.assert_registered_ctc_work_writer(connection,record_hold[3])
                issuer.assert_final_evidence_resume_current(connection,guard,run_id=run['id'],binding=source.binding,
                    journal_sha256=digest(checkpoint),resume_mode='repair',affected_artifact_ids=proposal.affected_artifact_ids)
                if held[5]:
                    _request,policy=issuer._bound(connection,guard,production,run,action='execute_plan')
                    issuer._bound(connection,guard,production,run,action='continue_bundle_validation')
                    permitted={r.route_id:r for r in policy.policy.routes}
                    for route in routes.values():
                        approved=permitted.get(route.route_id)
                        if approved is None or approved.route_sha256!=digest(canonical_body(route.model_dump(mode='json'))):
                            raise EngineError('affected_route_denied','Exact current Owner-covered route required',403)
                    for admission,action in zip(admissions[:2],('execute_plan','continue_bundle_validation'),strict=True):
                        issuer.assert_production_admission_current(connection,guard,lease,admission.admission_ref,stage=action)
                command=strict_json(body.encode('utf-8'))
                self.assert_diagnostic_command_targets_writer(connection,lease,command,guard=guard)
                saved=connection.execute('SELECT value FROM metadata WHERE key=?',(COMMAND_PREFIX+sha,)).fetchone()
                if saved is None:
                    if production['revision_cycles']>=min(request.automation.max_revision_cycles,plan.repair_targets.max_revision_cycles):
                        raise EngineError('revision_limit','Actual shared revision allowance exhausted',409)
                    for prior in connection.execute('SELECT value FROM metadata WHERE key LIKE ?',(COMMAND_PREFIX+'%',)):
                        candidate=strict_json(prior[0].encode('utf-8'))
                        if candidate.get('diagnostic_ref')==registered.ref.model_dump(mode='json') and candidate.get('parent_preparation_id')==source.parent_preparation_id:
                            raise EngineError('affected_command_conflict','Original diagnosis already binds a different immutable command',409)
                    connection.execute('INSERT INTO metadata(key,value) VALUES(?,?)',(COMMAND_PREFIX+sha,body))
                    self.engine._event(connection,run,'production.diagnosed_execution_registered',sha)
                else:
                    actual=strict_json(saved[0].encode('utf-8'))
                    if diagnosed_source(actual)!=source or actual.get('steps')!=steps:
                        raise EngineError('affected_command_conflict','Original diagnosed command source or deterministic Steps changed',409)
                self.assert_registered_ctc_work_writer(connection,record_hold[3])
                self._affected_claim(connection,lease,continuation)
                self.assert_diagnostic_command_targets_writer(connection,lease,command,guard=guard)
                issuer._guard(connection,guard)
        with self._lock:self._affected_execution_held[id(execution)]=(execution,lease,threading.get_ident(),continuation)
        return execution
