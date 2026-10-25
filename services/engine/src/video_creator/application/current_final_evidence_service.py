"""Final evidence implementation on the original BundleService, not a validator fork."""

import hashlib
import threading
import time

from video_creator.application.engine import canonical, digest, identity
from video_creator.application.current_production_blockers import bound_context
from video_creator.application.current_final_evidence_recovery import CurrentFinalEvidenceRecovery
from video_creator.application.affected_repair_service import canonical_body
from video_creator.domain import contracts as c
from video_creator.domain.bundle import BundlePreparationIntent
from video_creator.domain.current_final_evidence import (
    CurrentFinalEvidenceAssessment, CurrentFinalEvidenceInputs, CurrentFinalEvidenceSnapshot,
    FinalEvidenceDependency, FinalEvidenceRepair,
)
from video_creator.domain.errors import EngineError
from video_creator.domain.diagnostic_recovery import CurrentQualityFailure


class _FinalEvidenceProblem(Exception):
    def __init__(self, reason, *, kind=None, report=None, actual=None, manifest=None):
        self.reason, self.kind = reason, kind
        self.report, self.actual, self.manifest = report, actual, manifest


class CurrentFinalEvidenceService(CurrentFinalEvidenceRecovery):
    """Mixin for the one actual service and its existing complete verifier."""

    def current_final_evidence_ports(self, ordinary_lease, binding):
        from video_creator.application.current_final_evidence import CurrentFinalEvidencePorts
        with self.engine.db.connect_readonly() as connection:
            self.engine._lease(connection, ordinary_lease)
            _run, _production, _request, actual = bound_context(self.engine, connection,
                ordinary_lease.run_id, binding.registration_sha256)
        if actual != binding:
            raise EngineError('final_evidence_binding_invalid', 'Original execution binding required', 409)
        port = CurrentFinalEvidencePorts(self, ordinary_lease, actual)
        with self._lock:
            self._final_evidence_ports[id(port)] = port
        return port

    def _final_binding(self, lease, connection):
        with self._lock:
            ports = [p for p in self._final_evidence_ports.values()
                     if p._lease == lease and p._thread == threading.get_ident()]
        if len(ports) != 1:
            raise EngineError('final_evidence_port_denied', 'One original service-held current port required', 403)
        _run, _production, _request, actual = bound_context(self.engine, connection,
            lease.run_id, ports[0]._binding.registration_sha256)
        if actual != ports[0]._binding:
            raise EngineError('final_evidence_binding_invalid', 'Original execution binding changed', 409)
        return actual

    def _in_current_final_evidence(self):
        with self._lock:
            return threading.get_ident() in self._final_evidence_scopes

    def _current_precision_problem(self, reason, **details):
        if self._in_current_final_evidence():
            raise _FinalEvidenceProblem(reason, **details)

    def _current_precision_authority_result(self, actual_result):
        # Keep the original actual authority invocation and exact True gate.
        # A current rejection is a denial, never a missing-resource wait.
        if self._in_current_final_evidence() and actual_result is not True:
            raise EngineError('precision_authority_denied', 'Actual authority rejected this report', 403)
        return actual_result

    def _current_repair_scope(self, lease, *, manifest=None):
        """Existing finite execute-plan/validation scope, never a new grant."""
        if manifest is not None and getattr(self, '_production_services_held', None):
            held = self._affected_services(lease)
            runtime = self._production_services_runtime
            original_plan_ref = next((ref for ref in manifest.creative_revision_refs if ref.kind == 'plan'), None)
            if original_plan_ref is None:
                return 'guidance_required'
            with self.engine.db.connect_readonly() as connection:
                run = self.engine._lease(connection, lease)
                production = self.engine._production(connection, run['production_id'])
                request = c.parse_production_request(production['request_json'])
                row = connection.execute('SELECT * FROM creative_revisions WHERE id=? AND run_id=? AND production_id=?',
                    (original_plan_ref.revision_id, lease.run_id, production['id'])).fetchone()
                if row is None or row['content_sha256'] != original_plan_ref.content_sha256 or digest(row['body']) != original_plan_ref.content_sha256:
                    raise EngineError('affected_source_invalid', 'Exact failed candidate plan changed', 422)
                plan = c.CreativeRevision.model_validate_json(row['body'])
                if production['revision_cycles'] >= request.automation.max_revision_cycles:
                    return 'guidance_required'
            admission_method = held[1].production_admission if held[5] else held[1].current_production_admission
            actual = admission_method(lease, plan.revision_id, phase='plan', action='execute_plan')
            if actual.state != 'allowed' or actual.target_sha256 != original_plan_ref.content_sha256:
                return 'guidance_required'
            quality = admission_method(lease, manifest.quality_ref.revision_id, phase='quality', action='continue_bundle_validation')
            if quality.state != 'allowed' or quality.target_sha256 != manifest.quality_ref.content_sha256:
                return 'guidance_required'
            validated = self.validate_registered_plan(lease, plan)
            if getattr(runtime.config, 'alignment_registration', None) is not None:
                return 'realignment'
            if validated is not None and production['revision_cycles'] < validated.repair_targets.max_revision_cycles:
                # Availability data only. authorize still independently checks
                # actual report/subset/roles and exact whole-plan current scope.
                return 'regenerate_affected_media'
            return 'realignment' if held[5] else 'guidance_required'
        registered = self._production_authorization.registered(lease)
        issuer = self._production_authorization.issuer()
        with issuer.current_guard(registered) as guard:
            with self.engine.db.connect_readonly() as connection:
                run = self.engine._lease(connection, lease)
                production = self.engine._production(connection, run['production_id'])
                request = c.parse_production_request(production['request_json'])
                issuer._guard(connection, guard)
                issuer._request(connection, production, run, registered)
                if request.automation.mode != 'unattended':
                    return 'guidance_required'
                issuer._bound(connection, guard, production, run, action='execute_plan')
                issuer._bound(connection, guard, production, run, action='continue_bundle_validation')
                plan = connection.execute('SELECT id FROM creative_revisions WHERE production_id=? AND run_id=? AND kind=? ORDER BY rowid DESC LIMIT 1',
                    (production['id'], run['id'], 'plan')).fetchone()
                if plan is None:
                    return 'guidance_required'
                issuer._creative(connection, production, run, plan[0], 'plan')
                issuer._guard(connection, guard)
        # Only deterministic realignment within the existing approved work.
        # Generated media regeneration needs its separate actual plan scope.
        return 'realignment'

    def _final_prepared(self, lease, preparation_id):
        with self.engine.db.connect_readonly() as connection:
            row, run, production, request = self._preparation(connection, lease, preparation_id)
            binding = self._final_binding(lease, connection)
            self._all_operations(connection, run)
            prepared = self._snapshot(connection, row)
            intent = BundlePreparationIntent.model_validate_json(row['intent_json'])
            items = connection.execute('SELECT * FROM bundle_items WHERE preparation_id=? AND material_id IS NOT NULL ORDER BY rowid',
                (preparation_id,)).fetchall()
        self.resolve_preparation_masters(lease, preparation_id)
        # Material receipt identity is never sufficient without original bytes.
        for receipt in prepared.materials:
            self.read_material(lease, preparation_id, receipt.material_id)
        for asset_id in intent.media_asset_ids:
            asset = self.asset(lease, asset_id)
            path = self.content_path(lease, asset_id)
            if self.assets._hash(path) != asset.sha256 or path.stat().st_size != asset.size:
                raise EngineError('bundle_integrity_failed', 'Original media asset changed', 422)
            if self.validators.media_validator is None:
                raise EngineError('media_decoder_unavailable', 'Real decoder required for final inputs', 503)
            self.validators.media_validator(path, asset.media_type)
        return row, production, request, binding, prepared, intent, items

    def _retain_final_assessment(self, lease, binding, snapshot=None, verified=None):
        assessment = CurrentFinalEvidenceAssessment(identity('final-assessment'), binding, snapshot, verified)
        with self._lock:
            self._final_evidence_assessments[id(assessment)] = (
                assessment, lease, threading.get_ident(), time.monotonic() + 30)
        return assessment

    def assert_current_final_assessment(self, connection, lease, assessment):
        with self._lock:
            saved = self._final_evidence_assessments.get(id(assessment))
        if (saved is None or saved[0] is not assessment or saved[1] != lease
                or saved[2] != threading.get_ident() or time.monotonic() >= saved[3]):
            raise EngineError('final_evidence_assessment_denied', 'Actual current service assessment required', 403)
        actual = self._final_binding(lease, connection)
        if actual != assessment.binding:
            raise EngineError('final_evidence_binding_invalid', 'Assessment changed original binding', 409)
        snapshot = assessment.snapshot
        if snapshot is None:
            raise EngineError('final_evidence_wait_required', 'Only a real wait/repair assessment can stop', 409)
        row, _run, _production, _request = self._preparation(connection, lease, snapshot.preparation_id)
        if digest(row['intent_json']) != snapshot.preparation_intent_sha256:
            raise EngineError('final_evidence_preparation_changed', 'Original preparation intent changed', 409)
        if self._snapshot(connection, row).materials != snapshot.ready_material_refs:
            raise EngineError('final_evidence_material_changed', 'Original READY receipt set changed', 409)
        from video_creator.domain.component_diagnosis import CurrentFinalDiagnosticSnapshotV1
        if type(snapshot) is CurrentFinalDiagnosticSnapshotV1:
            self.assert_diagnostic_assessment_writer(connection,lease,snapshot)
        return snapshot

    def _final_snapshot(self, lease, preparation_id, reason, *, dependencies=(), repair=None, manifest=None):
        row, _production, _request, binding, prepared, _intent, _items = self._final_prepared(lease, preparation_id)
        sha = None
        if manifest is not None:
            raw = (canonical(manifest) + '\n').encode('utf-8')
            sha = hashlib.sha256(raw).hexdigest()
            if row['manifest_sha256'] and row['manifest_sha256'] != sha:
                raise EngineError('bundle_manifest_conflict', 'Original manifest bytes cannot be overwritten', 409)
            self._write('CurrentFinalCandidates', 'candidate-' + sha, raw)
        snapshot = CurrentFinalEvidenceSnapshot(preparation_id=preparation_id,
            preparation_intent_sha256=digest(row['intent_json']), candidate_manifest_file_sha256=sha,
            ready_material_refs=prepared.materials, state='repair_required' if repair else 'waiting_evidence',
            reason_code=reason, dependencies=tuple(dependencies), repair=repair)
        return self._retain_final_assessment(lease, binding, snapshot)

    def _resolve_current_final_inputs(self, lease, preparation_id, binding):
        row, production, request, actual, prepared, intent, items = self._final_prepared(lease, preparation_id)
        if actual != binding:
            raise EngineError('final_evidence_binding_invalid', 'Ports changed original binding', 409)
        if len(intent.media_asset_ids) != 4:
            raise EngineError('production_media_capability_missing', 'All four original masters required', 503)
        self.resolve_preparation_masters(lease, preparation_id)
        evidence_kinds = {'precision_report', 'precision_report_v03', 'precision_reference_v03',
            'method_benchmark', 'method_benchmark_reference', 'method_qualification', 'evidence_policy',
            'work_alignment_validation'}
        ordinary = [item for item in items if item['schema_kind'] not in evidence_kinds]
        # Quality is a final report, but source text and actual ASR must exist first.
        for item in ordinary:
            late = item['schema_kind'] == 'quality' or item['relative_path'] == 'Checks/assembly-audit.json'
            if not late and item['status'] != 'ready':
                raise EngineError('bundle_output_missing', 'Ordinary transcript/text/material is unfinished', 422)
        paths = {item['relative_path'] for item in ordinary if item['status'] == 'ready'}
        if not {'Text/approved-script.json', 'Text/actual-transcript.json'} <= paths:
            raise EngineError('bundle_output_missing', 'Original actual transcript and approved script required', 422)
        # A new pre-candidate wait must retain genuine original assembly/context.
        assembly = self._read_final_assembly(row, actual)
        if assembly is None:
            raise EngineError('final_assembly_unavailable', 'Registered producer must commit original assembly before waiting', 503)
        self._validate_final_assembly_facts(lease, row, intent, actual, assembly, author=False)
        resolved = None
        if isinstance(request, c.ProductionRequestV03):
            try:
                with self.engine.db.connect_readonly() as connection:
                    registry = self.engine.evidence_registry
                    registry._revision(connection)
                    ref = request.delivery_requirements.evidence_policy_revision_ref
                    existing = connection.execute('SELECT 1 FROM alignment_admissions WHERE kind=? AND admission_id=? AND revision=?',
                        ('policy', ref.policy_id, ref.revision)).fetchone()
                    if existing is None:
                        dep = FinalEvidenceDependency(kind='method_qualification', completion_kind='consume_ready_evidence',
                            target_artifact_id=None, expected_schema_kind='method_qualification', source_ref=ref,
                            reason_code='evidence_policy_not_ready')
                        return self._final_snapshot(lease, preparation_id, 'evidence_policy_not_ready', dependencies=(dep,))
                    resolved = registry.resolve(production['owner'], production['project_id'], ref, connection=connection)
            except EngineError as error:
                if error.code != 'evidence_authority_unconfigured':
                    raise
                dep = FinalEvidenceDependency(kind='method_qualification', completion_kind='consume_ready_evidence',
                    target_artifact_id=None, expected_schema_kind='method_qualification',
                    source_ref=request.delivery_requirements.evidence_policy_revision_ref, reason_code=error.code)
                return self._final_snapshot(lease, preparation_id, error.code, dependencies=(dep,))
        return CurrentFinalEvidenceInputs(actual, preparation_id, digest(row['intent_json']), prepared.materials, resolved)

    def verify_current_final_evidence(self, ordinary_lease, preparation_id, manifest):
        lease = ordinary_lease
        with self.engine.db.connect_readonly() as connection:
            binding = self._final_binding(lease, connection)
        if manifest is None:
            inputs = self._resolve_current_final_inputs(lease, preparation_id, binding)
            if isinstance(inputs, CurrentFinalEvidenceAssessment):
                return inputs
            with self.engine.db.connect_readonly() as connection:
                items = connection.execute('SELECT * FROM bundle_items WHERE preparation_id=? AND material_id IS NOT NULL AND status!=?',
                    (preparation_id, 'ready')).fetchall()
            dependencies = []
            kinds = {'work_alignment_validation': ('work_validation', 'generate_runtime_report'),
                'precision_report': ('precision_measurement', 'consume_ready_evidence'),
                'precision_report_v03': ('precision_measurement', 'generate_runtime_report'),
                'precision_reference_v03': ('independent_reference', 'consume_ready_evidence'),
                'method_qualification': ('method_qualification', 'consume_ready_evidence')}
            for item in items:
                if item['schema_kind'] in kinds:
                    kind, completion = kinds[item['schema_kind']]
                    dependencies.append(FinalEvidenceDependency(kind=kind, completion_kind=completion,
                        target_artifact_id=item['artifact_id'], expected_schema_kind=item['schema_kind'],
                        source_ref=inputs.resolved.policy_ref if inputs.resolved else None, reason_code='final_report_not_ready'))
            if not dependencies:
                raise EngineError('final_candidate_required', 'All final materials are READY; complete real manifest required', 409)
            return self._final_snapshot(lease, preparation_id, 'final_report_not_ready', dependencies=dependencies)
        thread = threading.get_ident()
        with self._lock:
            if thread in self._final_evidence_scopes:
                raise EngineError('final_evidence_scope_conflict', 'Nested final verification denied', 409)
            self._final_evidence_scopes[thread] = (lease, preparation_id)
        try:
            try:
                verified = self.verify(lease, preparation_id, manifest)
            except _FinalEvidenceProblem as problem:
                if problem.report is not None:
                    _row, _production, _request, _binding, prepared, _intent, _items = self._final_prepared(lease, preparation_id)
                    precision = problem.actual.alignment.precision
                    material_id = (precision.measurement_report_locator.material_id
                        if isinstance(precision, c.PrecisionAssessmentV03) and precision.measurement_report_locator
                        else precision.evaluation_material_id)
                    item = next((a for a in manifest.artifacts if a.material_id == material_id), None)
                    receipt = next((r for r in prepared.materials if item and r.material_id == item.material_id), None)
                    if receipt is None:
                        raise EngineError('precision_evidence_conflict', 'Failure must retain actual full report bytes', 422)
                    failed = tuple(v.transcript_unit_id for v in problem.report.boundaries
                        if max(abs(v.predicted_range.start_us - v.reference_range.start_us),
                               abs(v.predicted_range.end_us - v.reference_range.end_us)) > 200_000)
                    affected = {item.artifact_id}
                    for artifact in manifest.artifacts:
                        if artifact.relative_path == 'Text/actual-transcript.json':
                            affected.add(artifact.artifact_id)
                    while True:
                        expanded = affected | {a.artifact_id for a in manifest.artifacts
                            if affected.intersection(a.dependency_artifact_ids)}
                        if expanded == affected:
                            break
                        affected = expanded
                    repair = FinalEvidenceRepair(failed_check_code=problem.reason, source_report_ref=receipt,
                        affected_artifact_ids=tuple(a.artifact_id for a in manifest.artifacts if a.artifact_id in affected),
                        failed_unit_ids=failed, allowed_action=self._current_repair_scope(lease, manifest=manifest))
                    original=self._final_snapshot(lease, preparation_id, problem.reason, repair=repair, manifest=manifest)
                    outcome=self._register_diagnostic_outcome(lease,'precision_failure',assessment=original)
                    return self.join_current_final_diagnosis(lease,preparation_id,manifest,outcome=outcome,
                        diagnostic=self._current_diagnostic_record_for_join(lease,preparation_id))
                dep = FinalEvidenceDependency(kind=problem.kind, completion_kind='consume_ready_evidence',
                    target_artifact_id=None, expected_schema_kind=None, source_ref=None, reason_code=problem.reason)
                original=self._final_snapshot(lease, preparation_id, problem.reason, dependencies=(dep,), manifest=manifest)
                outcome=self._register_diagnostic_outcome(lease,'evidence_wait',assessment=original)
                return self.join_current_final_diagnosis(lease,preparation_id,manifest,outcome=outcome,
                    diagnostic=self._current_diagnostic_record_for_join(lease,preparation_id))
            except CurrentQualityFailure as failure:
                diagnostic=self._current_diagnostic_record_for_join(lease,preparation_id)
                if diagnostic is None:raise failure.original_error
                return self.join_current_final_diagnosis(lease,preparation_id,manifest,outcome=failure.outcome,
                    diagnostic=diagnostic)
            original=self._retain_final_assessment(lease,binding,verified=verified)
            outcome=self._register_diagnostic_outcome(lease,'verified_then_diagnostic_block',assessment=original,verified=verified)
            return self.join_current_final_diagnosis(lease,preparation_id,manifest,outcome=outcome,
                diagnostic=self._current_diagnostic_record_for_join(lease,preparation_id))
        finally:
            with self._lock:
                self._final_evidence_scopes.pop(thread, None)

    def revise_current_final_preparation(self, lease, preparation_id, intent, *, affected_artifact_ids):
        """Immutable child intent, preserved READY parent and actual affected subset."""
        with self.engine.db.connect_readonly() as connection:
            parent, _run, production, request = self._preparation(connection, lease, preparation_id)
            original = BundlePreparationIntent.model_validate_json(parent['intent_json'])
            binding=self._final_binding(lease, connection)
        affected = tuple(affected_artifact_ids)
        allowed_artifacts={s.artifact_id for s in original.material_slots}
        from video_creator.domain.component_diagnosis import AffectedRepairExecutionDiagnosedV1
        with self._lock:
            actual_executions=[value[0] for value in self._affected_execution_held.values()
                if value[1]==lease and value[2]==threading.get_ident() and type(value[0]) is AffectedRepairExecutionDiagnosedV1
                and value[0].parent_preparation_id==preparation_id and value[0].affected_artifact_ids==affected]
        if actual_executions:
            if len({value.repair_command_sha256 for value in actual_executions})!=1:
                raise EngineError('affected_command_conflict','One actual admitted diagnosed child source required',409)
            assembly=self._read_final_assembly(parent,binding)
            if assembly is None:
                raise EngineError('source_material_missing','Actual immutable original media scope required',503)
            allowed_artifacts.update(a.artifact_id for a in assembly.media_artifacts)
        if (not affected or len(set(affected)) != len(affected)
                or not set(affected) <= allowed_artifacts
                or intent.bundle_revision_id == original.bundle_revision_id
                or (intent.bundle_id, intent.request_revision_id) != (original.bundle_id, original.request_revision_id)):
            raise EngineError('final_evidence_lineage_invalid', 'Distinct same-Run child with actual affected subset required', 422)
        execution = self._live_affected_for_parent(lease, preparation_id, affected)
        from video_creator.application.affected_repair_service import COMMAND_PREFIX, MASTERS_PREFIX
        from video_creator.application.affected_repair_service import same_audio_identity, assert_audio_records_current
        parent_assets = self.resolve_preparation_masters(lease, preparation_id)
        parent_masters = {role: asset.asset_id for role, asset in parent_assets.items()}
        master_observation = None
        alignment_result = None
        if execution.requested_action == 'realignment':
            alignment_result = self.read_registered_alignment_result(lease, execution)
        if execution.requested_action == 'regenerate_affected_media':
            from video_creator.domain.component_diagnosis import AffectedRepairExecutionDiagnosedV1
            from video_creator.domain.affected_repair_steps import affected_recipe_step
            master_step=(affected_recipe_step(execution,'master',component_target_id='production-master')[0]
                if type(execution) is AffectedRepairExecutionDiagnosedV1 else 'repair-master-' + execution.repair_command_sha256[:32])
            master_observation = self.observe_current_affected_masters(lease, execution,
                step_key=master_step)
        effective = dict(master_observation.effective_media_roles) if master_observation else parent_masters
        child_audio = self.asset(lease, effective['mixed_audio'])
        changed_audio = not same_audio_identity(parent_assets['mixed_audio'], child_audio)
        if set(intent.media_asset_ids) != set(effective.values()):
            raise EngineError('final_evidence_lineage_invalid', 'Child must retain exact authenticated effective master IDs', 422)
        from video_creator.application.current_final_evidence_journal import PREFIX, parse_journal
        self._validate_preparation_intent(lease, intent)
        registered = self._production_authorization.registered(lease)
        issuer = self._production_authorization.issuer()
        with issuer.current_guard(registered) as guard:
            with self.engine.db.transaction() as connection:
                current, run, prod, req = self._preparation(connection, lease, preparation_id)
                binding = self._final_binding(lease, connection)
                if current['intent_json'] != parent['intent_json']:
                    raise EngineError('final_evidence_lineage_changed', 'Original parent intent changed', 409)
                saved = connection.execute('SELECT value FROM metadata WHERE key=?', (PREFIX + run['id'],)).fetchone()
                if saved is None:
                    raise EngineError('final_evidence_claim_required', 'Real failed repair checkpoint required', 409)
                journal = parse_journal(saved[0], now=self.engine.clock())
                repair = journal.snapshot.repair
                if (journal.binding != binding or journal.snapshot.preparation_id != preparation_id
                        or journal.control.phase != 'executing' or journal.control.execution_fence != lease.fencing_token
                        or journal.control.resume_mode != 'repair' or repair is None
                        or tuple(affected) != repair.affected_artifact_ids):
                    raise EngineError('final_evidence_claim_required', 'Original failed source and current repair fence required', 409)
                actual_command, command_raw, _raw, _journal, _parent, _run, _prod, _req = self._affected_execution(connection, lease, execution)
                if alignment_result is not None:
                    self.assert_alignment_writer(connection, lease, execution.repair_command_sha256,
                        initial=False, guard=guard, execution=execution)
                    from video_creator.application.bundles import strict_json
                    companion, _payload, _request_bytes = self._load_alignment(connection, lease,
                        execution.repair_command_sha256, initial=False)
                    completed = connection.execute('SELECT result_json,status FROM steps WHERE run_id=? AND step_key=?',
                        (lease.run_id, companion['descriptor']['step_key'])).fetchone()
                    if completed is None or completed['status'] != 'succeeded' or strict_json(completed['result_json'].encode())['result']['alignment_content_sha256'] != alignment_result[0].content_sha256:
                        raise EngineError('alignment_result_changed', 'Child requires original successful settled alignment document', 409)
                self.assert_command_targets_writer(connection, lease, actual_command, guard=guard)
                assert_audio_records_current(connection, parent_assets['mixed_audio'], child_audio, prod['owner'])
                if actual_command['child_preparation_id'] is not None:
                    if actual_command['child_intent_sha256'] != digest(canonical(intent)):
                        raise EngineError('final_evidence_lineage_conflict', 'Original command already selected a different immutable child', 409)
                    child_row = self._selected_affected_child(connection, lease.run_id, journal, current, actual_command['child_preparation_id'])
                    issuer._guard(connection, guard)
                    return self._snapshot(connection, child_row)
                diagnosed=actual_command.get('format')=='current-final-affected-execution-v2-diagnostic-v1'
                report=repair.precision_report_ref if diagnosed else repair.source_report_ref
                repair_identity=({'diagnostic_ref':actual_command['diagnostic_ref'],
                    'input_key_sha256':actual_command['input_key_sha256']} if diagnosed else {})
                command = canonical_body({'parent_preparation_id': preparation_id,
                    'parent_intent_sha256': digest(parent['intent_json']),
                    'report_sha256': report.sha256 if report else None,
                    'report_material_id': report.material_id if report else None,
                    'affected_artifact_ids': list(affected),**repair_identity})
                command_key = 'current_final_repair_command:' + digest(command)
                old_command = connection.execute('SELECT value FROM metadata WHERE key=?', (command_key,)).fetchone()
                if old_command:
                    from video_creator.application.bundles import strict_json
                    previous = strict_json(old_command[0].encode())
                    if previous.get('child_intent_sha256') != digest(canonical(intent)):
                        raise EngineError('final_evidence_lineage_conflict', 'Repair source already has a different child intent', 409)
                    child_row = connection.execute('SELECT * FROM bundle_revisions WHERE id=? AND run_id=?',
                        (previous['child_preparation_id'], run['id'])).fetchone()
                    if child_row is None or child_row['intent_json'] != canonical(intent):
                        raise EngineError('final_evidence_lineage_invalid', 'Original atomic child missing or changed', 422)
                    issuer._guard(connection, guard)
                    return self._snapshot(connection, child_row)
                issuer.assert_final_evidence_resume_current(connection, guard, run_id=run['id'], binding=binding,
                    journal_sha256=digest(saved[0]), resume_mode='repair', affected_artifact_ids=affected)
                if prod['revision_cycles'] >= req.automation.max_revision_cycles:
                    raise EngineError('revision_limit', 'Original production revision allowance exhausted', 409)
                # Child/allocation, lineage, command and one shared counter commit atomically.
                # An existing preparation cannot be adopted from an unrelated command.
                if connection.execute('SELECT 1 FROM bundle_revisions WHERE revision_id=?', (intent.bundle_revision_id,)).fetchone():
                    raise EngineError('final_evidence_lineage_conflict', 'Child revision already exists outside this repair command', 409)
                child = self._prepare_bundle_writer(connection, lease, intent)
                observation_ref = None
                if master_observation is not None:
                    observed = connection.execute('SELECT value FROM metadata WHERE key=?',
                        (MASTERS_PREFIX + execution.repair_command_sha256,)).fetchone()
                    if observed is None:
                        raise EngineError('affected_master_source_unavailable', 'Original committed master observation required', 503)
                    observation_ref = {'repair_command_sha256': execution.repair_command_sha256,
                                       'content_sha256': digest(observed[0])}
                body = canonical_body({'format': 'current-final-evidence-lineage-v3' if diagnosed else 'current-final-evidence-lineage-v2', 'parent_preparation_id': preparation_id,
                    'parent_revision_id': original.bundle_revision_id, 'parent_intent_sha256': digest(parent['intent_json']),
                    'child_preparation_id': child.preparation_id, 'child_revision_id': intent.bundle_revision_id,
                    'child_intent_sha256': digest(canonical(intent)), 'affected_artifact_ids': list(affected),
                    'repair_source_report_sha256': report.sha256 if report else None,
                    'repair_source_material_id': report.material_id if report else None,
                    'repair_command_sha256': execution.repair_command_sha256, 'master_observation_ref': observation_ref,
                    **({'diagnostic_ref':actual_command['diagnostic_ref'],'input_key_sha256':actual_command['input_key_sha256'],
                        'failure_source':actual_command['failure_source'],'projection_sha256':execution.projection_sha256,
                        'recipe_binding_sha256':execution.recipe_binding_sha256} if diagnosed else {})})
                connection.execute('INSERT INTO metadata(key,value) VALUES(?,?)',
                    ('current_final_evidence_lineage:' + child.preparation_id, body))
                connection.execute('INSERT INTO metadata(key,value) VALUES(?,?)', (command_key, body))
                updated_command = {**actual_command, 'child_preparation_id': child.preparation_id,
                                   'child_intent_sha256': digest(canonical(intent))}
                if changed_audio:
                    import json
                    audio = connection.execute('SELECT sha256 FROM assets WHERE id=? AND owner=?',
                        (effective['mixed_audio'], prod['owner'])).fetchone()
                    if audio is None:
                        raise EngineError('affected_master_source_invalid', 'Actual child mixed audio asset missing', 422)
                    runtime = self._production_services_runtime
                    asr_key = 'repair-asr-' + execution.repair_command_sha256[:32]
                    updated_command['child_asr'] = {'step_key': asr_key, 'dedupe_key': asr_key,
                        'input_sha256': digest(json.dumps({'audio_sha256': audio[0],
                            'resource_manifest_sha256': runtime.config.asr_resource_manifest_sha256}, sort_keys=True)),
                        'route_id': runtime.config.asr_route_id, 'audio_asset_id': effective['mixed_audio'],
                        'audio_sha256': audio[0], 'child_preparation_id': child.preparation_id,
                        'child_intent_sha256': digest(canonical(intent)),
                        'repair_command_sha256': execution.repair_command_sha256}
                result = connection.execute('UPDATE metadata SET value=? WHERE key=? AND value=?',
                    (canonical_body(updated_command), COMMAND_PREFIX + execution.repair_command_sha256, command_raw))
                if result.rowcount != 1:
                    raise EngineError('affected_command_conflict', 'Original command changed during atomic child commit', 409)
                connection.execute('UPDATE productions SET revision_cycles=revision_cycles+1 WHERE id=?', (prod['id'],))
                self.engine._event(connection, run, 'production.final_evidence_revised', digest(body))
                self._final_binding(lease, connection)
                self.assert_command_targets_writer(connection, lease, updated_command, guard=guard)
                if alignment_result is not None:
                    self.assert_alignment_writer(connection, lease, execution.repair_command_sha256,
                        initial=False, guard=guard, execution=execution)
                assert_audio_records_current(connection, parent_assets['mixed_audio'], child_audio, prod['owner'])
                issuer._guard(connection, guard)
                return child
