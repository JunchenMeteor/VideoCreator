"""Private parent-child proofs and terminal facts at the original writers."""
import threading
import time

from video_creator.application.engine import canonical, digest
from video_creator.application.current_final_evidence_journal import PREFIX, parse_journal, prepared_current
from video_creator.application.current_production_blockers import bound_context, require_settled
from video_creator.domain import contracts as c
from video_creator.domain.diagnostic_recovery import (
    DiagnosticMetadataRef, PreparedSelectedChildDiagnosticTransition,
    SelectedChildDiagnosticTransitionEvidence, FiniteDiagnosticTerminalEvidence,
)
from video_creator.domain.component_diagnosis import ComponentDiagnosisRefV1, CurrentFinalDiagnosticContinuationV1
from video_creator.domain.current_final_evidence import CurrentFinalEvidenceContinuation
from video_creator.domain.errors import EngineError


def metadata_ref(row):
    return DiagnosticMetadataRef(record_id=row['key'], content_sha256=digest(row['value']),
        size=len(row['value'].encode('utf-8')))


def _capture(table, key, row, *, column='id'):
    return (table, column, key, dict(row) if row is not None else None)


def _current_actions(service, connection, lease, factory, admissions, guard):
    """Use actual registered receipts, never an action Boolean from a command."""
    issuer = service._production_authorization.issuer()
    run, production, request, _binding = bound_context(service.engine, connection, lease.run_id,
        service._production_services_runtime.sha256)
    service.engine._lease(connection, lease)
    if run['paused'] or run['cancellation_requested'] or run['waiting_revision_id'] is not None:
        raise EngineError('final_evidence_state_conflict', 'Actual pause/cancellation/human review wins', 409)
    issuer._guard(connection, guard)
    issuer._request(connection, production, run, guard.identity)
    if len(admissions) != 2 or any(admission.state != 'allowed' or admission.run_id != lease.run_id
            or admission.fencing_token != lease.fencing_token
            or admission.registration_sha256 != service._production_services_runtime.sha256
            or admission.valid_until_us is None or admission.valid_until_us <= service.engine.clock()
            for admission in admissions):
        raise EngineError('production_current_admission_required', 'Actual unexpired same-fence plan and quality receipts required', 403)
    if factory[5]:
        for admission, action in zip(admissions, ('execute_plan', 'continue_bundle_validation'), strict=True):
            issuer._bound(connection, guard, production, run, action=action)
            issuer.assert_production_admission_current(connection, guard, lease, admission.admission_ref, stage=action)
    else:
        from video_creator.application.bundles import strict_json
        declaration = factory[1].declaration
        now = service.engine.clock()
        if (declaration.declaring_subject != production['owner'] or production['project_id'] not in declaration.project_ids
                or declaration.expires_at_us is not None and declaration.expires_at_us <= now
                or any(right.valid_from_us is not None and right.valid_from_us > now
                    or right.expires_at_us is not None and right.expires_at_us <= now for right in declaration.rights)):
            raise EngineError('production_rights_expired', 'Original actual human declaration is no longer current', 403)
        for admission in admissions:
            target = connection.execute('SELECT * FROM creative_revisions WHERE id=? AND run_id=?',
                (admission.target_id, lease.run_id)).fetchone()
            if target is None or target['content_sha256'] != admission.target_sha256 or digest(target['body']) != admission.target_sha256:
                raise EngineError('production_creative_evidence_invalid', 'Actual approved plan/quality changed', 409)
            approvals = []
            for row in connection.execute('SELECT * FROM decisions WHERE run_id=? ORDER BY rowid', (lease.run_id,)):
                decision = c.ReviewDecision.model_validate(strict_json(row['body'].encode('utf-8')))
                if decision.target_revision_id != target['id']:
                    continue
                if digest(row['body']) != row['request_sha256'] or row['result_json'] != row['body']:
                    raise EngineError('production_review_invalid', 'Actual immutable approval changed', 422)
                approvals.append(decision)
            if len(approvals) != 1 or approvals[0].action != 'approve':
                raise EngineError('production_review_required', 'Actual whole plan and quality approvals required', 403)
            ref = admission.human_approval_ref
            original = connection.execute('SELECT * FROM decisions WHERE run_id=? AND idempotency_key=?',
                (lease.run_id, ref.idempotency_key)).fetchone() if ref is not None else None
            if (ref is None or ref.run_id != lease.run_id or ref.target_revision_id != admission.target_id
                    or original is None or original['request_sha256'] != ref.decision_sha256
                    or digest(original['body']) != ref.decision_sha256 or original['result_json'] != original['body']
                    or c.ReviewDecision.model_validate(strict_json(original['body'].encode('utf-8'))) != approvals[0]):
                raise EngineError('production_review_invalid', 'Actual exact human admission approval receipt changed', 422)
    return run, production, request


def prepare_child(service, connection, lease, *, current_parent_journal, child_preparation_id, recorded):
    """Caller is the original selector; the exact connection establishes parent."""
    from video_creator.application.affected_repair_service import COMMAND_PREFIX, LINEAGE_PREFIX
    from video_creator.application.diagnostic_selection import SELECT_PREFIX
    from video_creator.application.bundles import strict_json
    saved = connection.execute('SELECT * FROM metadata WHERE key=?', (PREFIX + lease.run_id,)).fetchone()
    if saved is None or parse_journal(saved['value'], now=service.engine.clock()) != current_parent_journal:
        raise EngineError('final_evidence_checkpoint_changed', 'Exact actual current parent body required', 409)
    journal = current_parent_journal
    parent, _run, _production, _request = prepared_current(service.engine, connection, journal)
    service.engine._lease(connection, lease)
    if (journal.control.phase != 'executing' or journal.control.resume_mode != 'repair'
            or journal.control.execution_fence != lease.fencing_token or journal.snapshot.repair is None
            or journal.snapshot.repair.allowed_action == 'guidance_required'
            or recorded.fact.binding != journal.binding or recorded.fact.parent_preparation_id != child_preparation_id):
        raise EngineError('diagnostic_selection_denied', 'Actual parent repair and registered child fact required', 409)
    require_settled(connection, lease.run_id)
    child = service._selected_affected_child(connection, lease.run_id, journal, parent, child_preparation_id)
    commands = []
    for row in connection.execute('SELECT * FROM metadata WHERE key LIKE ?', (COMMAND_PREFIX + '%',)):
        command = strict_json(row['value'].encode('utf-8'))
        if (command.get('binding') == journal.binding.model_dump(mode='json')
                and command.get('parent_preparation_id') == parent['id']
                and command.get('child_preparation_id') == child['id']):
            commands.append((row, command))
    if len(commands) != 1:
        raise EngineError('diagnostic_selection_conflict', 'One exact committed parent-child command required', 409)
    command_row, command = commands[0]
    lineage = connection.execute('SELECT * FROM metadata WHERE key=?', (LINEAGE_PREFIX + child['id'],)).fetchone()
    if (lineage is None or command_row['key'] != COMMAND_PREFIX + command['repair_command_sha256']
            or command['child_intent_sha256'] != digest(child['intent_json'])
            or command['parent_intent_sha256'] != digest(parent['intent_json'])):
        raise EngineError('final_evidence_lineage_invalid', 'Exact committed command/intent/lineage required', 422)
    previous, source_row = service._read_source_writer(connection, saved['value'], journal)
    selected = connection.execute('SELECT * FROM metadata WHERE key=?', (SELECT_PREFIX + parent['id'],)).fetchone()
    parent_ref = ComponentDiagnosisRefV1.model_validate_json(selected['value']) if selected else None
    if previous is not None and previous.diagnostic_ref != parent_ref:
        raise EngineError('diagnostic_source_changed', 'Parent source and complete selection disagree', 409)
    if previous is None and (parent_ref is not None or hasattr(journal.snapshot, 'diagnostic_ref')):
        raise EngineError('diagnostic_source_changed', 'Diagnosed parent cannot lose its actual source', 409)
    factory = service._affected_services(lease)
    admissions = service._production_services_runtime._current_final_execution_facts(lease, factory[1], factory[5])[:2]
    continuation_type = CurrentFinalDiagnosticContinuationV1 if hasattr(journal.snapshot, 'diagnostic_ref') else CurrentFinalEvidenceContinuation
    continuation = continuation_type(journal.binding, journal.snapshot, 'repair', lease.fencing_token)
    issuer = service._production_authorization.issuer()
    with issuer.current_guard(service._production_authorization.registered(lease)) as guard:
        if parent_ref is not None:
            parent_record = service._read_explicit_diagnostic_record(lease, parent_ref, parent['id'], continuation=continuation)
            with service._lock:
                parent_captures = service._diagnostic_records_held[id(parent_record)][3]
        else:
            read = service._read_current_final_continuation_inputs(lease, continuation, guard)
            if read.missing_facts:
                raise EngineError('final_evidence_source_unavailable', 'Complete actual original parent validation sources required', 503)
            repair = journal.snapshot.repair
            original = next((receipt for receipt, _data in read.materials if receipt == repair.source_report_ref), None)
            if original is None:
                raise EngineError('diagnostic_source_changed', 'Actual complete original failed precision report required', 409)
            parent_captures = ()
        service.assert_command_targets_writer(connection, lease, command, guard=guard)
        _current_actions(service, connection, lease, factory, admissions, guard)
        # Both real parent/child masters, unchanged media and settled ASR/CTC
        # are resolved through the original lineage-aware reader, not IDs alone.
        service.resolve_preparation_masters(lease, parent['id'])
        service.resolve_preparation_masters(lease, child['id'])
        captures = list(parent_captures)
        captures.extend((_capture('metadata', saved['key'], saved, column='key'),
            _capture('metadata', SELECT_PREFIX + parent['id'], selected, column='key'),
            _capture('metadata', command_row['key'], command_row, column='key'),
            _capture('metadata', lineage['key'], lineage, column='key')))
        for admission in admissions:
            row = connection.execute('SELECT * FROM creative_revisions WHERE id=? AND run_id=?',
                (admission.target_id, lease.run_id)).fetchone()
            captures.append(_capture('creative_revisions', admission.target_id, row))
            if admission.human_approval_ref is not None:
                key = (lease.run_id, admission.human_approval_ref.idempotency_key)
                row = connection.execute('SELECT * FROM decisions WHERE run_id=? AND idempotency_key=?', key).fetchone()
                captures.append(_capture('decisions', key, row, column='idempotency_key'))
        if source_row is not None:
            captures.append(_capture('metadata', source_row['key'], source_row, column='key'))
        else:
            from video_creator.application.diagnostic_selection import source_key
            captures.append(_capture('metadata', source_key(lease.run_id, saved['value']), None, column='key'))
        for row in (parent, child):
            captures.append(('bundle_revisions', 'id', row['id'],
                {key: row[key] for key in ('id', 'run_id', 'production_id', 'request_revision_id', 'revision_id', 'intent_json')}))
            captures.append(('text_materials', 'preparation_id', row['id'], tuple(dict(item) for item in connection.execute(
                'SELECT * FROM bundle_items WHERE preparation_id=? AND asset_id IS NULL ORDER BY artifact_id', (row['id'],)))))
        for step_key, descriptor in command['steps'].items():
            step = connection.execute('SELECT * FROM steps WHERE run_id=? AND step_key=?', (lease.run_id, step_key)).fetchone()
            operations = connection.execute('SELECT * FROM operations WHERE run_id=? AND step_key=?', (lease.run_id, step_key)).fetchall()
            if (step is None or step['status'] != 'succeeded' or step['input_sha256'] != descriptor['input_sha256']
                    or not operations or any(op['status'] != 'succeeded' or not op['settled']
                        or op['input_sha256'] != descriptor['input_sha256'] for op in operations)):
                raise EngineError('diagnostic_selection_denied', 'Original command Steps and Operations must really succeed and settle', 409)
            captures.append(_capture('steps', (lease.run_id, step_key), step, column='step_key'))
            captures.extend(_capture('operations', op['id'], op) for op in operations)
        service.assert_registered_ctc_work_writer(connection, tuple(captures))
        require_settled(connection, lease.run_id)
        issuer._guard(connection, guard)
    evidence = SelectedChildDiagnosticTransitionEvidence(parent_preparation_id=parent['id'],
        parent_intent_sha256=digest(parent['intent_json']), child_preparation_id=child['id'],
        child_intent_sha256=digest(child['intent_json']), parent_journal_body=saved['value'],
        parent_journal_sha256=digest(saved['value']), parent_source_ref=metadata_ref(source_row) if source_row else None,
        parent_selected_body=selected['value'] if selected else None, parent_selected_ref=parent_ref,
        affected_command_ref=metadata_ref(command_row), child_lineage_ref=metadata_ref(lineage),
        parent_failure_snapshot_sha256=digest(canonical(journal.snapshot)), authored_fence=lease.fencing_token)
    result = PreparedSelectedChildDiagnosticTransition(evidence, command_row['value'], child['id'])
    with service._lock:
        if not hasattr(service, '_diagnostic_child_transitions'):
            service._diagnostic_child_transitions = {}
        service._diagnostic_child_transitions[id(result)] = (result, lease, threading.get_ident(),
            time.monotonic() + 30, tuple(captures), factory, admissions)
    return result


def assert_child_writer(service, connection, lease, transition, *, guard, journal_body=None):
    with service._lock:
        held = getattr(service, '_diagnostic_child_transitions', {}).get(id(transition))
    if held is None or held[0] is not transition or held[1] != lease or held[2] != threading.get_ident() or time.monotonic() >= held[3]:
        raise EngineError('diagnostic_selection_denied', 'Actual same-service/fence/thread child proof required', 403)
    captures = held[4]
    if journal_body is not None:
        replaced = []
        for table, column, key, expected in captures:
            if table == 'metadata' and key == PREFIX + lease.run_id:
                row = connection.execute('SELECT * FROM metadata WHERE key=?', (key,)).fetchone()
                if row is None or row['value'] != journal_body:
                    raise EngineError('final_evidence_checkpoint_changed', 'Exact own child journal CAS required', 409)
                expected = dict(row)
            replaced.append((table, column, key, expected))
        captures = tuple(replaced)
    service.assert_registered_ctc_work_writer(connection, captures)
    _current_actions(service, connection, lease, held[5], held[6], guard)
    from video_creator.application.bundles import strict_json
    service.assert_command_targets_writer(connection, lease, strict_json(transition.command_body.encode('utf-8')), guard=guard)
    require_settled(connection, lease.run_id)
    return transition.evidence


def read_child_history(service, connection, source):
    """History proves immutable association, never a live parent execution."""
    evidence = getattr(source, 'selected_child_transition', None)
    if evidence is None:
        return
    parent_journal = parse_journal(evidence.parent_journal_body, now=service.engine.clock())
    if (parent_journal.binding != source.binding or parent_journal.snapshot.preparation_id != evidence.parent_preparation_id
            or parent_journal.snapshot.preparation_intent_sha256 != evidence.parent_intent_sha256
            or digest(canonical(parent_journal.snapshot)) != evidence.parent_failure_snapshot_sha256
            or parent_journal.control.phase != 'executing' or parent_journal.control.resume_mode != 'repair'
            or parent_journal.control.execution_fence != evidence.authored_fence):
        raise EngineError('diagnostic_source_invalid', 'Exact historical parent repair facts required', 422)
    for ref in (evidence.affected_command_ref, evidence.child_lineage_ref, evidence.parent_source_ref):
        if ref is None:
            continue
        row = connection.execute('SELECT * FROM metadata WHERE key=?', (ref.record_id,)).fetchone()
        if row is None or metadata_ref(row) != ref:
            raise EngineError('diagnostic_source_invalid', 'Immutable historical command/lineage/source changed', 422)
    from video_creator.application.affected_repair_service import COMMAND_PREFIX, LINEAGE_PREFIX
    from video_creator.application.bundles import strict_json
    lineage_row=connection.execute('SELECT value FROM metadata WHERE key=?',(evidence.child_lineage_ref.record_id,)).fetchone()
    lineage=strict_json(lineage_row[0].encode('utf-8'))
    if (evidence.child_lineage_ref.record_id!=LINEAGE_PREFIX+evidence.child_preparation_id
            or evidence.affected_command_ref.record_id!=COMMAND_PREFIX+str(lineage.get('repair_command_sha256'))):
        raise EngineError('diagnostic_source_invalid','Historical refs must name the actual child command/lineage',422)
    command_row=connection.execute('SELECT value FROM metadata WHERE key=?',(evidence.affected_command_ref.record_id,)).fetchone()
    command=strict_json(command_row[0].encode('utf-8'))
    if (command.get('binding')!=source.binding.model_dump(mode='json')
            or command.get('parent_preparation_id')!=evidence.parent_preparation_id
            or command.get('parent_intent_sha256')!=evidence.parent_intent_sha256
            or command.get('child_preparation_id')!=evidence.child_preparation_id
            or command.get('child_intent_sha256')!=evidence.child_intent_sha256
            or evidence.parent_source_ref is None and hasattr(parent_journal.snapshot,'diagnostic_ref')):
        raise EngineError('diagnostic_source_invalid','Historical command must retain this exact parent-child source',422)
    parent = connection.execute('SELECT * FROM bundle_revisions WHERE id=? AND run_id=?',
        (evidence.parent_preparation_id, source.binding.run_id)).fetchone()
    if parent is None or digest(parent['intent_json']) != evidence.parent_intent_sha256:
        raise EngineError('diagnostic_source_invalid', 'Immutable historical parent intent changed', 422)
    child = service._selected_affected_child(connection, source.binding.run_id, parent_journal, parent, evidence.child_preparation_id)
    if digest(child['intent_json']) != evidence.child_intent_sha256:
        raise EngineError('diagnostic_source_invalid', 'Immutable child intent changed', 422)
    from video_creator.application.diagnostic_selection import SELECT_PREFIX
    selected = connection.execute('SELECT value FROM metadata WHERE key=?', (SELECT_PREFIX + parent['id'],)).fetchone()
    if (selected[0] if selected else None) != evidence.parent_selected_body:
        raise EngineError('diagnostic_source_changed', 'Historical parent selection was replaced', 409)
    if evidence.parent_source_ref is not None:
        from video_creator.application.diagnostic_selection import parse_source, source_key
        saved = connection.execute('SELECT value FROM metadata WHERE key=?', (evidence.parent_source_ref.record_id,)).fetchone()
        parent_source = parse_source(saved[0])
        if (evidence.parent_source_ref.record_id != source_key(source.binding.run_id, evidence.parent_journal_body)
                or parent_source.binding != source.binding or parent_source.journal_sha256 != evidence.parent_journal_sha256
                or parent_source.snapshot_sha256 != evidence.parent_failure_snapshot_sha256
                or parent_source.preparation_id != evidence.parent_preparation_id
                or parent_source.preparation_intent_sha256 != evidence.parent_intent_sha256
                or parent_source.diagnostic_ref != evidence.parent_selected_ref):
            raise EngineError('diagnostic_source_invalid', 'Historical parent source/body/selection closure changed', 422)


def read_source_chain(service, connection, source):
    """Bounded immutable chain read; it never grants an old execution fence."""
    from video_creator.application.diagnostic_selection import parse_source
    seen = set()
    ref = source.previous_source_ref
    for _depth in range(128):
        if ref is None:
            return
        if ref.record_id in seen:
            raise EngineError('diagnostic_source_invalid', 'Cyclic historical source references', 422)
        seen.add(ref.record_id)
        row = connection.execute('SELECT * FROM metadata WHERE key=?', (ref.record_id,)).fetchone()
        if row is None or metadata_ref(row) != ref:
            raise EngineError('diagnostic_source_invalid', 'Exact immutable source history changed', 422)
        parent = parse_source(row['value'])
        from video_creator.application.diagnostic_selection import SOURCE_PREFIX
        if ref.record_id!=SOURCE_PREFIX+source.binding.run_id+':'+parent.journal_sha256:
            raise EngineError('diagnostic_source_invalid','Historical source key must name its exact journal',422)
        if parent.binding != source.binding:
            raise EngineError('diagnostic_source_invalid', 'Historical source crossed original binding', 422)
        if getattr(parent, 'selected_child_transition', None) is not None:
            read_child_history(service, connection, parent)
        ref = parent.previous_source_ref
    raise EngineError('diagnostic_source_invalid', 'Historical source chain exceeds the bounded read limit', 422)


def prepare_failure(service, connection, lease, assessment, *, guard):
    """The actual same-transaction cap predicate; information is not failure."""
    snapshot = assessment.snapshot
    if snapshot.repair is None or snapshot.repair.allowed_action == 'guidance_required':
        return None
    run, production, request, _binding = bound_context(service.engine, connection, lease.run_id,
        service._production_services_runtime.sha256)
    service.engine._lease(connection, lease)
    require_settled(connection, lease.run_id)
    factory = service._affected_services_writer(lease)
    # Receipts were produced from the current original plan/quality before
    # this writer; do not acquire another authority or invent a target.
    with service._lock:
        association = getattr(service, '_diagnostic_assessment_sources', {}).get(id(assessment))
    if association is not None:
        outcome = association[2]
        if outcome.kind not in {'precision_failure', 'quality_incomplete', 'legacy_diagnostic_block'}:
            return None
        inputs = service._diagnostic_records_held[id(association[1].recorded)][4]
        refs = inputs.parent.assembly.creative_revision_refs
    else:
        # The original real failure preparation's immutable assembly provides
        # the approved plan; this is a local source read, not a new approval.
        row = connection.execute('SELECT * FROM bundle_revisions WHERE id=? AND run_id=?',
            (snapshot.preparation_id, lease.run_id)).fetchone()
        assembly = service._read_final_assembly(row, assessment.binding)
        if assembly is None:
            raise EngineError('final_assembly_unavailable', 'Original immutable failure assembly required for its finite cap', 503)
        refs = assembly.creative_revision_refs
    plans = tuple(ref for ref in refs if ref.kind == 'plan')
    if len(plans) != 1:
        raise EngineError('production_review_required', 'One actual whole-plan source required', 403)
    plan_ref = plans[0]
    row = connection.execute('SELECT * FROM creative_revisions WHERE id=? AND run_id=?', (plan_ref.revision_id, lease.run_id)).fetchone()
    if row is None or row['content_sha256'] != plan_ref.content_sha256 or digest(row['body']) != plan_ref.content_sha256:
        raise EngineError('plan_repair_source_changed', 'Actual immutable failure plan changed', 409)
    revision = c.CreativeRevision.model_validate_json(row['body'])
    cap = None
    projection = None
    if isinstance(revision.body, dict) and revision.body.get('format') in {'registered-production-plan-v2', 'registered-production-plan-v3'}:
        from video_creator.domain.plan_repair_targets import RegisteredProductionPlanV2
        from video_creator.domain.affected_recipe import RegisteredProductionPlanV3
        from video_creator.application.affected_repair_service import canonical_body
        model = RegisteredProductionPlanV3 if revision.body['format'] == 'registered-production-plan-v3' else RegisteredProductionPlanV2
        projection = model.model_validate_json(canonical_body(revision.body)).repair_targets
        cap = projection.max_revision_cycles
        if (projection.binding != assessment.binding or projection.resource_manifest_sha256 != factory[6]
                or projection.runtime_manifest_sha256 != factory[7]):
            raise EngineError('plan_repair_source_changed', 'Actual approved cap differs from its original binding/resources', 409)
    limit = min(request.automation.max_revision_cycles, cap) if cap is not None else request.automation.max_revision_cycles
    issuer = service._production_authorization.issuer()
    issuer._guard(connection, guard)
    issuer._request(connection, production, run, guard.identity)
    if factory[5]:
        for action in ('execute_plan', 'continue_bundle_validation'):
            _request, policy = issuer._bound(connection, guard, production, run, action=action)
            admission = issuer._earlier_action(connection, production, run, policy, lease, action)
            if action == 'execute_plan' and (admission.target_id, admission.target_sha256) != (plan_ref.revision_id, plan_ref.content_sha256):
                raise EngineError('affected_target_denied', 'Actual whole plan approval required for its finite cap', 403)
            if projection is not None and projection.rights_declaration_sha256 != issuer._rights_sha(policy.policy):
                raise EngineError('production_rights_conflict', 'Actual finite whole-plan policy rights changed', 409)
    else:
        # The original human receipt/declaration paths remain mandatory.
        runtime = service._production_services_runtime
        admissions = runtime._current_final_execution_facts(lease, factory[1], False)[:2]
        _current_actions(service, connection, lease, factory, admissions, guard)
        if (admissions[0].target_id, admissions[0].target_sha256) != (plan_ref.revision_id, plan_ref.content_sha256):
            raise EngineError('affected_target_denied', 'Actual whole plan approval required for its finite cap', 403)
        from video_creator.domain.plan_repair_targets import plan_payload_sha256
        if projection is not None and projection.rights_declaration_sha256 != plan_payload_sha256(factory[1].declaration):
            raise EngineError('production_rights_conflict', 'Actual finite whole-plan human rights changed', 409)
    # Keep original nonterminal counter too: no later writer may silently
    # turn this same held assessment into a different budget observation.
    if factory[5]:
        admissions = ()
    with service._lock:
        if not hasattr(service, '_diagnostic_terminal_inputs'):
            service._diagnostic_terminal_inputs = {}
        service._diagnostic_terminal_inputs[id(assessment)] = (assessment, lease, threading.get_ident(), time.monotonic() + 30,
            dict(row), plan_ref, cap, production['revision_cycles'], request.automation.max_revision_cycles,
            digest(production['request_json']), factory, admissions,
            projection.rights_declaration_sha256 if projection is not None else None)
    return limit


def finite_failure(service, connection, lease, assessment, *, guard):
    if assessment.snapshot.repair is None or assessment.snapshot.repair.allowed_action == 'guidance_required':
        return None
    with service._lock:
        held = getattr(service, '_diagnostic_terminal_inputs', {}).get(id(assessment))
    if held is None:
        # A verified success/information wait cannot be turned into terminal.
        with service._lock:
            association = getattr(service, '_diagnostic_assessment_sources', {}).get(id(assessment))
        if association is not None and association[2].kind not in {'precision_failure', 'quality_incomplete', 'legacy_diagnostic_block'}:
            return None
        raise EngineError('final_evidence_assessment_denied', 'Actual held original finite failure source required', 403)
    if held[0] is not assessment or held[1] != lease or held[2] != threading.get_ident() or time.monotonic() >= held[3]:
        raise EngineError('final_evidence_assessment_denied', 'Actual same-thread/fence finite source required', 403)
    service.assert_registered_ctc_work_writer(connection, (_capture('creative_revisions', held[4]['id'], held[4]),))
    issuer = service._production_authorization.issuer()
    run, production, request, _binding = bound_context(service.engine, connection, lease.run_id, service._production_services_runtime.sha256)
    service.engine._lease(connection, lease)
    require_settled(connection, lease.run_id)
    issuer._guard(connection, guard)
    issuer._request(connection, production, run, guard.identity)
    if (production['revision_cycles'], request.automation.max_revision_cycles, digest(production['request_json'])) != (held[7], held[8], held[9]):
        raise EngineError('final_evidence_limit_changed', 'Original exact counter/request/cap changed', 409)
    if service._affected_services_writer(lease) is not held[10]:
        raise EngineError('production_services_source_invalid', 'Original finite failure factory changed', 403)
    if held[10][5]:
        for action in ('execute_plan', 'continue_bundle_validation'):
            _request, policy = issuer._bound(connection, guard, production, run, action=action)
            admission = issuer._earlier_action(connection, production, run, policy, lease, action)
            if action == 'execute_plan' and (admission.target_id, admission.target_sha256) != (held[5].revision_id, held[5].content_sha256):
                raise EngineError('affected_target_denied', 'Actual complete plan approval required', 403)
            if held[12] is not None and issuer._rights_sha(policy.policy) != held[12]:
                raise EngineError('production_rights_conflict', 'Original approved finite policy rights changed', 409)
    else:
        _current_actions(service, connection, lease, held[10], held[11], guard)
        from video_creator.domain.plan_repair_targets import plan_payload_sha256
        if held[12] is not None and plan_payload_sha256(held[10][1].declaration) != held[12]:
            raise EngineError('production_rights_conflict', 'Original approved finite human rights changed', 409)
    limit = min(held[8], held[6]) if held[6] is not None else held[8]
    if held[7] < limit:
        return None
    return FiniteDiagnosticTerminalEvidence(reason='revision_limit_exhausted', revision_cycles=held[7],
        request_revision_limit=held[8], approved_plan_ref=held[5] if held[6] is not None else None,
        approved_plan_revision_limit=held[6], effective_revision_limit=limit,
        requested_action=assessment.snapshot.repair.allowed_action, request_sha256=held[9],
        authored_fence=lease.fencing_token, committed_at_us=service.engine.clock())


def observe_terminal(runtime, journal, raw):
    """Observe a committed failure after response loss, without claiming work."""
    service = runtime.bundle
    issuer = runtime.engine.production_admissions
    with runtime.engine.db.connect_readonly() as connection:
        _prepared, run, production, request = prepared_current(runtime.engine, connection, journal)
        owner = production['owner']
    registered = runtime.engine._authorization_identity(owner)
    with issuer.current_guard(registered) as guard, runtime.engine.db.connect_readonly() as connection:
        issuer._guard(connection, guard)
        saved = connection.execute('SELECT value FROM metadata WHERE key=?', (PREFIX + run['id'],)).fetchone()
        prepared, run, production, request = prepared_current(runtime.engine, connection, journal)
        if (saved is None or saved[0] != raw or run['status'] != 'failed' or production['status'] != 'failed'
                or run['worker_id'] is not None or run['lease_until_us'] != 0
                or journal.control.phase != 'executing' or journal.control.resume_mode != 'repair'
                or journal.snapshot.repair is None or journal.snapshot.repair.allowed_action == 'guidance_required'):
            raise EngineError('final_evidence_checkpoint_changed', 'Exact committed finite failure required', 409)
        event=connection.execute("SELECT * FROM events WHERE run_id=? AND event_type='production.final_evidence_failed' ORDER BY occurred_at_us DESC,id DESC LIMIT 1",(run['id'],)).fetchone()
        legacy_revision=(journal.snapshot.repair.diagnostic_ref.content_sha256 if hasattr(journal.snapshot.repair,'diagnostic_ref') else journal.snapshot.repair.source_report_ref.sha256)
        if event is None or event['status']!='failed' or event['entity_revision_id'] not in (digest(raw),legacy_revision):
            raise EngineError('final_evidence_terminal_unobserved','Actual same-source committed finite failure event required',409)
        issuer._request(connection, production, run, registered)
        runtime._declaration_resume_current(production, request)
        require_settled(connection, run['id'])
        source, _row = service._read_source_writer(connection, raw, journal)
        if source is not None:
            terminal = getattr(source, 'terminal_failure', None)
            if terminal is None:
                raise EngineError('final_evidence_terminal_unobserved', 'Original diagnostic failure lacks its exact terminal source', 409)
            if (terminal.revision_cycles != production['revision_cycles']
                    or terminal.request_revision_limit != request.automation.max_revision_cycles
                    or terminal.request_sha256 != digest(production['request_json'])
                    or terminal.authored_fence != journal.control.execution_fence
                    or terminal.requested_action != journal.snapshot.repair.allowed_action):
                raise EngineError('diagnostic_source_changed', 'Exact finite failure history changed', 409)
            from video_creator.application.diagnostic_selection import SELECT_PREFIX
            selected = connection.execute('SELECT value FROM metadata WHERE key=?', (SELECT_PREFIX + source.preparation_id,)).fetchone()
            if selected is None or ComponentDiagnosisRefV1.model_validate_json(selected[0]) != source.diagnostic_ref:
                raise EngineError('diagnostic_source_changed', 'Terminal journal/source/selection changed', 409)
            if terminal.approved_plan_ref is not None:
                plan = connection.execute('SELECT * FROM creative_revisions WHERE id=? AND run_id=?',
                    (terminal.approved_plan_ref.revision_id, run['id'])).fetchone()
                if (plan is None or plan['content_sha256'] != terminal.approved_plan_ref.content_sha256
                        or digest(plan['body']) != terminal.approved_plan_ref.content_sha256):
                    raise EngineError('diagnostic_source_invalid', 'Immutable terminal cap source changed', 422)
                revision = c.CreativeRevision.model_validate_json(plan['body'])
                from video_creator.domain.plan_repair_targets import RegisteredProductionPlanV2
                from video_creator.domain.affected_recipe import RegisteredProductionPlanV3
                from video_creator.application.affected_repair_service import canonical_body
                if not isinstance(revision.body, dict) or revision.body.get('format') not in {'registered-production-plan-v2', 'registered-production-plan-v3'}:
                    raise EngineError('diagnostic_source_invalid', 'Original registered finite cap grammar required', 422)
                model = RegisteredProductionPlanV3 if revision.body['format'] == 'registered-production-plan-v3' else RegisteredProductionPlanV2
                if model.model_validate_json(canonical_body(revision.body)).repair_targets.max_revision_cycles != terminal.approved_plan_revision_limit:
                    raise EngineError('diagnostic_source_invalid', 'Terminal cap differs from its immutable whole plan', 422)
        elif hasattr(journal.snapshot, 'diagnostic_ref'):
            raise EngineError('diagnostic_source_changed', 'Terminal diagnostic companion missing', 409)
        else:
            # Preserve ordinary failure/source-absence semantics. Observation
            # cannot queue anything and relies on the original failed report.
            assembly=service._read_final_assembly(prepared,journal.binding)
            candidate=service._original_final_candidate(prepared,journal,journal.binding) if assembly is None else None
            original=assembly if assembly is not None else candidate[0] if candidate is not None else None
            if original is None:
                raise EngineError('final_assembly_unavailable','Original ordinary failure cap source required',503)
            plans=tuple(ref for ref in original.creative_revision_refs if ref.kind=='plan')
            if len(plans)!=1:
                raise EngineError('production_review_required','One original ordinary failure plan required',403)
            plan=connection.execute('SELECT * FROM creative_revisions WHERE id=? AND run_id=?',(plans[0].revision_id,run['id'])).fetchone()
            if plan is None or plan['content_sha256']!=plans[0].content_sha256 or digest(plan['body'])!=plans[0].content_sha256:
                raise EngineError('plan_repair_source_changed','Original ordinary failure cap source changed',409)
            revision=c.CreativeRevision.model_validate_json(plan['body'])
            limit=request.automation.max_revision_cycles
            if isinstance(revision.body,dict) and revision.body.get('format') in {'registered-production-plan-v2','registered-production-plan-v3'}:
                from video_creator.domain.plan_repair_targets import RegisteredProductionPlanV2
                from video_creator.domain.affected_recipe import RegisteredProductionPlanV3
                from video_creator.application.affected_repair_service import canonical_body
                model=RegisteredProductionPlanV3 if revision.body['format']=='registered-production-plan-v3' else RegisteredProductionPlanV2
                limit=min(limit,model.model_validate_json(canonical_body(revision.body)).repair_targets.max_revision_cycles)
            if production['revision_cycles']<limit:
                raise EngineError('final_evidence_limit_not_reached','Actual original ordinary finite cap not exhausted',409)
            ref = journal.snapshot.repair.source_report_ref
            try:
                data = service._file('BundleMaterials', ref.material_id).read_bytes()
            except FileNotFoundError:
                raise EngineError('bundle_integrity_failed', 'Immutable ordinary failure report disappeared', 422) from None
            import hashlib
            if len(data) != ref.size or hashlib.sha256(data).hexdigest() != ref.sha256:
                raise EngineError('bundle_integrity_failed', 'Immutable ordinary failure report changed', 422)
        issuer._guard(connection, guard)
    return 'failed', 'revision_limit_exhausted'
