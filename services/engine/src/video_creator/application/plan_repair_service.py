"""Request-scoped finite plan projection from the original held production source."""

import hashlib
import json
from contextlib import contextmanager

from pydantic import ValidationError

from video_creator.application.engine import digest
from video_creator.application.current_production_blockers import bound_context
from video_creator.application.affected_recipe_plan import AffectedRecipePlanService
from video_creator.domain import contracts as c
from video_creator.domain.errors import EngineError
from video_creator.domain.plan_repair_targets import (
    PlanRepairRevisionRef, PlanRepairTarget, PlanRepairTargetsV1,
    RegisteredProductionPlanV2, plan_payload_sha256,
)


class PlanRepairService(AffectedRecipePlanService):
    def prepare_plan_repair_targets(self, lease, *, proposal, script_revision_id, storyboard_revision_id):
        """Data preparation before plan approval; it never begins an Operation."""
        if type(proposal) is not c.CreativeProposal:
            raise EngineError('plan_repair_inputs_invalid', 'Original typed creative proposal required', 422)
        held = self._affected_services(lease)
        runtime = self._production_services_runtime
        rights = held[1].rights_proposal(lease)
        issuer = self._production_authorization.issuer()
        with issuer.current_guard(self._production_authorization.registered(lease)) as guard:
            with self.engine.db.connect_readonly() as connection:
                run, production, request, binding = bound_context(self.engine, connection, lease.run_id, runtime.sha256)
                self.engine._lease(connection, lease)
                issuer._guard(connection, guard)
                cap = request.automation.max_revision_cycles
                if held[5]:
                    _request, record = issuer._bound(connection, guard, production, run, action='begin_execution')
                    cap = min(cap, record.policy.max_revision_cycles)
                revisions = []
                for identifier, kind in ((script_revision_id, 'script'), (storyboard_revision_id, 'storyboard')):
                    row = connection.execute('SELECT * FROM creative_revisions WHERE id=? AND run_id=? AND production_id=?',
                        (identifier, lease.run_id, production['id'])).fetchone()
                    if row is None or row['kind'] != kind or digest(row['body']) != row['content_sha256']:
                        raise EngineError('plan_repair_source_invalid', 'Exact committed source revision required', 422)
                    revisions.append((c.CreativeRevision.model_validate_json(row['body']), row['content_sha256']))
                issuer._guard(connection, guard)
            script, storyboard = (value[0] for value in revisions)
            script_ref, storyboard_ref = (PlanRepairRevisionRef(revision_id=value.revision_id, content_sha256=sha)
                                         for value, sha in revisions)
            candidate = next(value for value in proposal.candidates if value.candidate_id == proposal.selected_candidate_id)
            expected_script = {'text': '\n'.join(shot.narration for shot in proposal.shots),
                               'candidate': candidate.model_dump(mode='json'), 'source_role': '声音导演'}
            start, expected_shots = 0, []
            for shot in proposal.shots:
                end = start + shot.duration_us
                expected_shots.append({**shot.model_dump(mode='json'),
                    'shot_revision_id': 'autonomous.shot.' + lease.run_id + '.' + shot.shot_id,
                    'timeline_range': {'start_us': start, 'end_us': end}})
                start = end
            if (script.body != expected_script or storyboard.body != {'shots': expected_shots, 'timeline_duration_us': start}
                    or script.revision_id not in storyboard.input_revision_refs):
                raise EngineError('plan_repair_source_invalid', 'Proposal must exactly match committed original script and storyboard', 422)
            from video_creator.application.bundles import strict_json
            if runtime.production_manifest.stat().st_size > 2 * 1024 * 1024:
                raise EngineError('production_resource_invalid', 'Original manifest exceeds its registered bound', 503)
            raw = runtime.production_manifest.read_bytes()
            if hashlib.sha256(raw).hexdigest() != held[6]:
                raise EngineError('production_resource_changed', 'Original resource manifest changed', 503)
            manifest = strict_json(raw)
            resources = manifest.get('production_drivers') if isinstance(manifest, dict) else None
            if not isinstance(resources, dict) or any(name not in resources for name in ('narration', 'picture', 'edit')):
                raise EngineError('plan_repair_recipe_not_ready', 'Original indexed narration/picture/edit recipe required', 503)
            # The installed fixed FFmpeg recipe consumes speech and each clip's
            # soundtrack. Its cover is the first decoded video frame, not audio.
            if resources['edit'].get('kind') != 'ffmpeg':
                raise EngineError('plan_repair_recipe_not_ready', 'No dependency recipe for this edit driver', 503)
            routes = {section: self.engine.configured_route(getattr(runtime.config.autonomous_registration, section + '_route_id'))
                      for section in ('narration', 'picture', 'edit')}
            whole_range = c.MediaRange(start_us=0, end_us=start)
            targets = [PlanRepairTarget(target_id='production-narration', kind='narration',
                shot_ids=tuple(shot.shot_id for shot in proposal.shots), timeline_range=whole_range,
                route_id=routes['narration'].route_id, route_sha256=plan_payload_sha256(routes['narration']),
                resource_section='narration', resource_section_sha256=plan_payload_sha256(resources['narration']),
                input_revision_refs=(script_ref,), input_payload_sha256=plan_payload_sha256(script.body),
                prerequisite_target_ids=(), output_roles=('narration_audio',),
                dependent_media_roles=('video', 'narration_audio', 'mixed_audio'))]
            for index, (shot, saved) in enumerate(zip(proposal.shots, expected_shots, strict=True)):
                targets.append(PlanRepairTarget(target_id='production-' + shot.shot_id, kind='shot_clip',
                    shot_ids=(shot.shot_id,), timeline_range=c.MediaRange.model_validate(saved['timeline_range']),
                    route_id=routes['picture'].route_id, route_sha256=plan_payload_sha256(routes['picture']),
                    resource_section='picture', resource_section_sha256=plan_payload_sha256(resources['picture']),
                    input_revision_refs=(storyboard_ref,), input_payload_sha256=plan_payload_sha256(shot),
                    prerequisite_target_ids=(), output_roles=('shot_clip',),
                    dependent_media_roles=('video', 'mixed_audio', 'cover') if index == 0 else ('video', 'mixed_audio')))
            prerequisites = tuple(target.target_id for target in targets)
            template = {'storyboard': storyboard.body, 'clip_target_ids': list(prerequisites[1:]),
                        'narration_target_id': prerequisites[0], 'output_roles': ['video', 'mixed_audio', 'cover']}
            targets.append(PlanRepairTarget(target_id='production-edit', kind='edit',
                shot_ids=tuple(shot.shot_id for shot in proposal.shots), timeline_range=whole_range,
                route_id=routes['edit'].route_id, route_sha256=plan_payload_sha256(routes['edit']),
                resource_section='edit', resource_section_sha256=plan_payload_sha256(resources['edit']),
                input_revision_refs=(script_ref, storyboard_ref), input_payload_sha256=plan_payload_sha256(template),
                prerequisite_target_ids=prerequisites, output_roles=('video', 'mixed_audio', 'cover'),
                dependent_media_roles=('video', 'mixed_audio', 'cover')))
            result = PlanRepairTargetsV1(format='current-plan-repair-targets-v1', binding=binding,
                resource_manifest_sha256=held[6], runtime_manifest_sha256=held[7], script_ref=script_ref,
                storyboard_ref=storyboard_ref, rights_declaration_sha256=rights.declaration_sha256,
                allowed_action='regenerate_affected_media', max_revision_cycles=cap, targets=tuple(targets))
            self.assert_current_production_services(lease, held[0], held[1])
            with self.engine.db.connect_readonly() as connection:
                self.engine._lease(connection, lease)
                issuer._guard(connection, guard)
                for value, sha in revisions:
                    row = connection.execute('SELECT body,content_sha256 FROM creative_revisions WHERE id=? AND run_id=?',
                        (value.revision_id, lease.run_id)).fetchone()
                    if row is None or row['content_sha256'] != sha or digest(row['body']) != sha:
                        raise EngineError('plan_repair_source_changed', 'Source changed during original projection', 409)
            return result

    def validate_registered_plan(self, lease, revision):
        """Strict v2 dispatcher; legacy original bodies are not rewritten."""
        if isinstance(revision.body, dict) and revision.body.get('format') == 'registered-production-plan-v3':
            return self.validate_registered_plan_v3(lease, revision)
        if (isinstance(revision.body, dict) and isinstance(revision.body.get('format'), str)
                and revision.body['format'].startswith('registered-production-plan-')
                and revision.body['format'] != 'registered-production-plan-v2'):
            raise EngineError('plan_repair_body_invalid', 'Unknown registered plan version cannot use legacy fallback', 422)
        if not isinstance(revision.body, dict) or revision.body.get('format') != 'registered-production-plan-v2':
            return None
        if revision.kind != 'plan':
            raise EngineError('plan_repair_source_invalid', 'Only a plan can carry registered plan v2', 422)
        try:
            plan = RegisteredProductionPlanV2.model_validate_json(json.dumps(revision.body, allow_nan=False))
        except (ValidationError, ValueError, TypeError):
            raise EngineError('plan_repair_body_invalid', 'Strict finite registered plan required', 422) from None
        targets = self.prepare_plan_repair_targets(lease, proposal=plan.proposal,
            script_revision_id=plan.repair_targets.script_ref.revision_id,
            storyboard_revision_id=plan.repair_targets.storyboard_ref.revision_id)
        if (targets != plan.repair_targets or plan.timeline_duration_us != targets.targets[-1].timeline_range.end_us
                or any(ref not in revision.input_revision_refs for ref in (targets.script_ref.revision_id, targets.storyboard_ref.revision_id))):
            raise EngineError('plan_repair_source_invalid', 'Plan projection differs from the actual held source', 422)
        return plan

    @contextmanager
    def plan_commit_guard(self, lease):
        held = self._affected_services(lease)
        issuer = self._production_authorization.issuer()
        with issuer.current_guard(self._production_authorization.registered(lease)) as guard:
            yield guard
        self.assert_current_production_services(lease, held[0], held[1])

    def assert_plan_sources_writer(self, connection, lease, plan, guard):
        """Only local SQL/current-source checks inside the original short writer."""
        runtime = self._production_services_runtime
        self.engine._lease(connection, lease)
        _run, _production, _request, binding = bound_context(self.engine, connection, lease.run_id, runtime.sha256)
        issuer = self._production_authorization.issuer()
        issuer._guard(connection, guard)
        issuer._request(connection, _production, _run, guard.identity)
        held = self._affected_services_writer(lease)
        if held[5]:
            issuer._bound(connection, guard, _production, _run, action='begin_execution')
        if binding != plan.repair_targets.binding:
            raise EngineError('plan_repair_source_changed', 'Current original request binding changed', 409)
        for ref in (plan.repair_targets.script_ref, plan.repair_targets.storyboard_ref):
            row = connection.execute('SELECT body,content_sha256 FROM creative_revisions WHERE id=? AND run_id=?',
                (ref.revision_id, lease.run_id)).fetchone()
            if row is None or row['content_sha256'] != ref.content_sha256 or digest(row['body']) != ref.content_sha256:
                raise EngineError('plan_repair_source_changed', 'Original plan source changed before commit', 409)
        issuer._guard(connection, guard)

    def _affected_services_writer(self, lease):
        """Only retained identity checks; no nested connection or file I/O."""
        import threading
        with self._lock:
            values = [value for value in self._production_services_held.values()
                      if value[2] == lease and value[3] == threading.get_ident()]
        if len(values) != 1:
            raise EngineError('production_services_source_invalid', 'Original same-fence factory source required', 403)
        return values[0]

    def assert_command_targets_writer(self, connection, lease, command, *, guard=None):
        """Same exact immutable target resolver at every repair writer/read boundary."""
        if command.get('format') == 'current-final-affected-execution-v2-diagnostic-v1':
            return self.assert_diagnostic_command_targets_writer(connection,lease,command,guard=guard)
        from video_creator.application.bundles import strict_json
        if command.get('requested_action') != 'regenerate_affected_media':
            return
        ref = command.get('plan_ref')
        if not isinstance(ref, dict):
            raise EngineError('guidance_required', 'Original finite approved plan required', 403)
        row = connection.execute('SELECT * FROM creative_revisions WHERE id=? AND run_id=?',
            (ref['revision_id'], lease.run_id)).fetchone()
        if row is None or row['content_sha256'] != ref['content_sha256'] or digest(row['body']) != ref['content_sha256']:
            raise EngineError('plan_repair_source_changed', 'Exact repair plan changed', 409)
        revision = c.CreativeRevision.model_validate_json(row['body'])
        if not isinstance(revision.body, dict) or revision.body.get('format') != 'registered-production-plan-v2':
            raise EngineError('guidance_required', 'Legacy plan has no generation targets', 403)
        try:
            plan = RegisteredProductionPlanV2.model_validate_json(json.dumps(revision.body, allow_nan=False))
        except (ValidationError, ValueError, TypeError):
            raise EngineError('plan_repair_body_invalid', 'Original finite plan is damaged', 422) from None
        projection = plan.repair_targets
        held = self._affected_services_writer(lease)
        runtime = self._production_services_runtime
        _run, production, request, binding = bound_context(self.engine, connection, lease.run_id, runtime.sha256)
        self.engine._lease(connection, lease)
        target_binding = command.get('repair_targets')
        if (projection.binding != binding or command.get('binding') != binding.model_dump(mode='json')
                or projection.resource_manifest_sha256 != held[6] or projection.runtime_manifest_sha256 != held[7]
                or not isinstance(target_binding, dict) or set(target_binding) != {'format', 'body_sha256', 'target_ids', 'input_payload_sha256'}
                or target_binding['format'] != projection.format
                or target_binding['body_sha256'] != plan_payload_sha256(projection)):
            raise EngineError('plan_repair_source_changed', 'Original complete finite target/source binding changed', 409)
        indexed = {value.target_id: value for value in projection.targets}
        ids = target_binding['target_ids']
        if (type(ids) is not list or not ids or len(set(ids)) != len(ids)
                or any(identifier not in indexed for identifier in ids)
                or ids != [value.target_id for value in projection.targets if value.target_id in ids]
                or target_binding['input_payload_sha256'] != {identifier: indexed[identifier].input_payload_sha256 for identifier in ids}):
            raise EngineError('affected_target_denied', 'Exact finite original target templates required', 403)
        selected = [value for value in projection.targets if value.kind == 'edit'
            or value.kind == 'narration' and 'narration_audio' in command['changed_media_roles']
            or value.kind == 'shot_clip' and 'video' in command['changed_media_roles'] and value.shot_ids[0] in command['affected_shot_ids']]
        dependencies = {role for value in selected if value.kind != 'edit' for role in value.dependent_media_roles}
        if not dependencies:
            dependencies = set(command['changed_media_roles']) & set(projection.targets[-1].dependent_media_roles)
        if ids != [value.target_id for value in selected] or dependencies != set(command['changed_media_roles']):
            raise EngineError('affected_target_denied', 'Original command differs from the finite recipe selection', 403)
        for source in (projection.script_ref, projection.storyboard_ref):
            original = connection.execute('SELECT body,content_sha256 FROM creative_revisions WHERE id=? AND run_id=?',
                (source.revision_id, lease.run_id)).fetchone()
            if original is None or original['content_sha256'] != source.content_sha256 or digest(original['body']) != source.content_sha256:
                raise EngineError('plan_repair_source_changed', 'Original repair input changed', 409)
        for identifier in ids:
            target = indexed[identifier]
            route_row = connection.execute('SELECT body FROM routes WHERE id=?', (target.route_id,)).fetchone()
            if route_row is None or plan_payload_sha256(c.CapabilityRoute.model_validate_json(route_row[0])) != target.route_sha256:
                raise EngineError('affected_route_denied', 'Original target route changed', 403)
        if production['revision_cycles'] > min(request.automation.max_revision_cycles, projection.max_revision_cycles):
            raise EngineError('revision_limit', 'Original finite total revision allowance exceeded', 409)
        issuer = self._production_authorization.issuer()
        if guard is not None:
            issuer._guard(connection, guard)
            issuer._request(connection, production, _run, guard.identity)
        if held[5]:
            if guard is None:
                # Caller still checks the current installed guard outside this
                # pure reader; exact persisted current policy is read locally.
                record = issuer._record(connection, issuer._current_binding(connection, production, _run).policy_ref,
                    self.engine._authorization_identity(production['owner']), request, production, action='execute_plan')
            else:
                _request, record = issuer._bound(connection, guard, production, _run, action='execute_plan')
            fact = issuer._earlier_action(connection, production, _run, record, lease, 'execute_plan')
            if (fact.target_id, fact.target_sha256) != (ref['revision_id'], ref['content_sha256']):
                raise EngineError('affected_target_denied', 'Actual execute_plan admission must bind this whole plan', 403)
            if projection.rights_declaration_sha256 != issuer._rights_sha(record.policy):
                raise EngineError('production_rights_conflict', 'Current policy rights changed', 409)
        else:
            declaration = held[1].declaration
            now = self.engine.clock()
            if (declaration.declaring_subject != production['owner'] or production['project_id'] not in declaration.project_ids
                    or declaration.expires_at_us is not None and declaration.expires_at_us <= now
                    or plan_payload_sha256(declaration) != projection.rights_declaration_sha256
                    or any(right.valid_from_us is not None and right.valid_from_us > now
                           or right.expires_at_us is not None and right.expires_at_us <= now for right in declaration.rights)):
                raise EngineError('production_rights_expired', 'Original human declaration is no longer current', 403)
            approvals = []
            for decision_row in connection.execute('SELECT * FROM decisions WHERE run_id=? ORDER BY rowid', (lease.run_id,)):
                decision = c.ReviewDecision.model_validate(strict_json(decision_row['body'].encode()))
                if decision.target_revision_id != ref['revision_id']:
                    continue
                if (digest(decision_row['body']) != decision_row['request_sha256']
                        or decision_row['result_json'] != decision_row['body']):
                    raise EngineError('production_review_invalid', 'Actual original approval bytes changed', 422)
                approvals.append(decision)
            if len(approvals) != 1 or approvals[0].action != 'approve':
                raise EngineError('affected_target_denied', 'Actual whole-plan human approve required', 403)
        return plan
