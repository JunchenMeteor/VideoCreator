"""ADR0074 same Engine original readers. Projections never grant admission."""
import json
from dataclasses import dataclass
from weakref import WeakKeyDictionary, WeakValueDictionary

from pydantic import ValidationError

from video_creator.application.bundles import strict_json
from video_creator.application.daily_projects import (
    GOAL_ACCEPT_SCOPE,
    GOAL_INTENT_SCOPE,
    _parse_goal_intent,
)
from video_creator.application.engine import canonical, digest
from video_creator.application.production_authorization import (
    ProductionAuthorizationService,
)
from video_creator.domain import contracts as c
from video_creator.domain.daily_project_authorization import (
    ProjectGoalAccepted,
    ProjectGoalReceiptAcceptedV1,
    ProjectGoalReceiptQueryV1,
)
from video_creator.domain.errors import EngineError
from video_creator.domain.local_material_production import (
    LocalMaterialPlanV1,
    LocalProductionRequestRef,
    parse_local_material_plan,
    validate_local_material_plan_sources,
)
from video_creator.domain.production_authorization import (
    CurrentProductionAdmission,
    ProductionRightsFact,
)


@dataclass(frozen=True)
class LocalMaterialPlanSources:
    request: c.ProductionRequestAny
    request_ref: LocalProductionRequestRef
    accepted_goal: ProjectGoalAccepted | None
    original_assets: tuple[c.AssetRecord, ...]
    original_script: tuple[c.RevisionRef, c.CreativeRevision]
    original_routes: tuple[c.CapabilityRoute, ...]


@dataclass(frozen=True, eq=False)
class LocalMaterialFinalContext:
    sources: LocalMaterialPlanSources
    plan: LocalMaterialPlanV1
    plan_revision: tuple[c.RevisionRef, c.CreativeRevision]
    quality_revision: tuple[c.RevisionRef, c.CreativeRevision]
    plan_admission: CurrentProductionAdmission
    quality_admission: CurrentProductionAdmission
    production_rights_fact: ProductionRightsFact

    @property
    def selection(self):
        from video_creator.domain.local_bundle import select_local_masters
        return select_local_masters(self.sources.request, self.plan, self.plan_revision[0])


@dataclass(frozen=True, eq=False)
class _PlanSnapshot:
    source: object
    lease: c.LeaseGrant
    queries: tuple
    plan_sha256: str


class _Reader:
    def __init__(self, connection):
        self.connection, self.queries = connection, []

    def all(self, sql, arguments=()):
        rows = self.connection.execute(sql, arguments).fetchall()
        self.queries.append((sql, tuple(arguments), tuple(tuple(row) for row in rows)))
        return rows


class LocalMaterialSourceService:
    def __init__(self, runtime):
        self.runtime, self.engine, self.bundle = runtime, runtime.engine, runtime.bundle
        self._snapshots = WeakValueDictionary()
        self._contexts = WeakKeyDictionary()

    def _goal(self, reader, production, lease):
        intents = reader.all('SELECT idempotency_key,result_json FROM commands WHERE owner=? AND scope=? ORDER BY idempotency_key',
            (production['owner'], GOAL_INTENT_SCOPE))
        matches = []
        for row in intents:
            if type(row['result_json']) is not str or len(row['result_json'].encode('utf-8')) > 32 * 1024 * 1024:
                raise EngineError('local_goal_source_invalid', 'Original Goal intent must be bounded TEXT.', 422)
            intent = _parse_goal_intent(ProductionAuthorizationService, row['result_json'])
            if intent.production_id == production['id'] or intent.run_id == lease.run_id:
                if (intent.production_id, intent.run_id, intent.request_revision_id, canonical(intent.request)) != (
                        production['id'], lease.run_id, production['request_revision_id'], production['request_json']):
                    raise EngineError('local_goal_source_conflict', 'Goal intent differs from the actual request.', 409)
                matches.append((row['idempotency_key'], intent))
        children = reader.all('SELECT derivation_id,content_sha256 FROM project_scope_derivations WHERE production_id=? OR run_id=?',
            (production['id'], lease.run_id))
        accepted = reader.all('SELECT result_json FROM commands WHERE owner=? AND scope=? ORDER BY idempotency_key',
            (production['owner'], GOAL_ACCEPT_SCOPE))
        try:
            receipts = [ProjectGoalAccepted.model_validate_json(row[0], strict=True) for row in accepted]
        except (ValidationError, ValueError, UnicodeError) as error:
            raise EngineError('local_goal_source_invalid', 'Original acceptance records are damaged, not direct absence.', 422) from error
        receipts = [value for value in receipts if value.production_id == production['id'] or value.run_id == lease.run_id]
        if not matches:
            if children or receipts:
                raise EngineError('local_goal_source_invalid', 'Dangling accepted Goal is not direct absence.', 422)
            return None
        if len(matches) != 1 or len(children) != 1 or len(receipts) != 1:
            raise EngineError('local_goal_source_invalid', 'One complete original accepted Goal is required.', 422)
        key, intent = matches[0]
        query = ProjectGoalReceiptQueryV1(format='project-goal-receipt-query-v1',
            expected_instance_id=self.engine.instance_id, idempotency_key=key, goal=intent.goal)
        result = self.bundle.lookup_project_goal_receipt(self.bundle.principals.owner(), query)
        if type(result) is not ProjectGoalReceiptAcceptedV1 or result.receipt != receipts[0]:
            raise EngineError('local_goal_source_invalid', 'Original accepted Goal association is incomplete.', 422)
        return result.receipt

    def _origin(self, lease, request, script, origin, reader):
        text = script.body.get('text') if isinstance(script.body, dict) else None
        if type(text) is not str:
            raise EngineError('local_script_source_invalid', 'Original script has no exact text.', 422)
        if origin == 'user_provided':
            if text not in (request.inputs.source_text, request.goal) or not text:
                raise EngineError('local_script_source_conflict', 'User script differs from the actual request input.', 409)
            return
        operations = reader.all('SELECT * FROM operations WHERE run_id=? ORDER BY id', (lease.run_id,))
        matched = []
        for row in operations:
            if row['production_id'] != self.bundle.context(lease).production_id:
                raise EngineError('local_script_operation_conflict', 'Source Operation belongs to another actual production.', 409)
            route = c.CapabilityRoute.model_validate_json(row['route_json'])
            if origin == 'input_audio_transcript' and route.capability != 'transcription':
                continue
            if origin == 'model_inference' and route.capability != 'text':
                continue
            if row['status'] != 'succeeded' or not row['settled']:
                continue
            observation = c.OperationObservation.model_validate_json(row['observation_json'])
            value = observation.result_json
            if not isinstance(value, dict) or value.get('text') != text:
                continue
            steps = reader.all('SELECT input_sha256,status FROM steps WHERE run_id=? AND step_key=?',
                (lease.run_id, row['step_key']))
            if len(steps) != 1 or tuple(steps[0]) != (row['input_sha256'], 'succeeded'):
                raise EngineError('local_script_step_conflict', 'Original script source Step is not committed succeeded.', 409)
            if route.route_id not in request.policy.allowed_provider_routes:
                raise EngineError('local_script_route_denied', 'Original source route is outside this request.', 403)
            if origin == 'input_audio_transcript':
                original = self.runtime.journal.read_settled_original_asr(lease, row['id'])
                if original is None or original.observation != observation:
                    raise EngineError('local_script_asr_context_missing', 'Actual settled original ASR context is required.', 503)
                context = strict_json(original.original_context_bytes)['request']
                assets = [self.bundle.asset(lease, identifier) for identifier in request.inputs.asset_ids]
                audio = [asset for asset in assets if asset.sha256 == context['audio_sha256']
                    and str(self.bundle.content_path(lease, asset.asset_id).resolve()) == context['audio_path']]
                if len(audio) != 1 or not audio[0].probe.has_audio:
                    raise EngineError('local_script_asr_source_conflict', 'Input transcript cannot name generated mix or foreign audio.', 409)
            matched.append(row['id'])
        if len(matched) != 1:
            raise EngineError('local_script_source_invalid', 'Script requires one actual succeeded settled source Operation.', 422)

    def read(self, lease, *, script_revision_id, source_script_origin, selected_route_ids):
        if source_script_origin not in {'user_provided', 'model_inference', 'input_audio_transcript'}:
            raise EngineError('local_script_origin_invalid', 'Exact local script origin is required.', 422)
        registration = self.runtime.config.local_registration
        required = {registration.input_audio_route_id, registration.input_visual_route_id,
                    registration.edit_route_id, registration.master_index_route_id}
        if not required <= set(selected_route_ids) or len(set(selected_route_ids)) != len(selected_route_ids):
            raise EngineError('local_route_source_conflict', 'Actual local production must retain its four original route selections.', 409)
        with self.engine.db.connect_readonly() as connection:
            run = self.engine._lease(connection, lease)
            owner = self.engine._production(connection, run['production_id'])['owner']
        registered = self.engine._authorization_identity(owner)
        issuer = self.engine.production_admissions
        with issuer.current_guard(registered) as guard, self.engine.db.connect_readonly() as connection:
            run = self.engine._lease(connection, lease)
            production = self.engine._production(connection, run['production_id'])
            issuer._guard(connection, guard)
            issuer._request(connection, production, run, registered)
            reader = _Reader(connection)
            rows = reader.all('SELECT request_json,request_sha256,request_revision_id,project_id,owner FROM productions WHERE id=?', (production['id'],))
            if len(rows) != 1 or digest(production['request_json']) != production['request_sha256']:
                raise EngineError('local_request_source_invalid', 'Original immutable request is damaged.', 422)
            request = c.parse_production_request(production['request_json'])
            ref = LocalProductionRequestRef(instance_id=self.engine.instance_id, production_id=production['id'],
                run_id=lease.run_id, request_revision_id=production['request_revision_id'], request_sha256=production['request_sha256'])
            rows = reader.all('SELECT * FROM creative_revisions WHERE id=? AND production_id=? AND run_id=?',
                (script_revision_id, production['id'], lease.run_id))
            if len(rows) != 1 or rows[0]['kind'] != 'script' or digest(rows[0]['body']) != rows[0]['content_sha256']:
                raise EngineError('local_script_source_invalid', 'Actual same Run immutable script is required.', 422)
            script = c.CreativeRevision.model_validate_json(rows[0]['body'])
            if script.revision_id != script_revision_id or script.kind != 'script':
                raise EngineError('local_script_source_invalid', 'Original script row and body identity differ.', 422)
            script_ref = c.RevisionRef(revision_id=script_revision_id, kind='script', content_sha256=rows[0]['content_sha256'])
            assets = tuple(self.bundle.asset(lease, identifier) for identifier in request.inputs.asset_ids)
            for asset in assets:
                reader.all('SELECT * FROM assets WHERE id=? AND owner=?', (asset.asset_id, production['owner']))
                self.bundle.content_path(lease, asset.asset_id)
            routes = []
            for identifier in selected_route_ids:
                rows = reader.all('SELECT body FROM routes WHERE id=?', (identifier,))
                if len(rows) != 1:
                    raise EngineError('local_route_source_missing',
                        'Original selected route ' + identifier + ' is absent; selected='
                        + ','.join(selected_route_ids) + '; required=' + ','.join(sorted(required)), 503)
                route = c.CapabilityRoute.model_validate_json(rows[0][0])
                outside = identifier not in request.policy.allowed_provider_routes
                scope_bad = identifier in required and (
                    route.source != 'owned_local' or route.credential_ref is not None
                    or route.max_operation_cost.units() or not route.destination.startswith('local:'))
                if outside or scope_bad:
                    reasons = []
                    if outside:
                        reasons.append('not_in_request_policy')
                    if scope_bad:
                        if route.source != 'owned_local':
                            reasons.append('source=' + str(route.source))
                        if route.credential_ref is not None:
                            reasons.append('credential_ref_set')
                        if route.max_operation_cost.units():
                            reasons.append('cost=' + str(route.max_operation_cost.units()))
                        if not route.destination.startswith('local:'):
                            reasons.append('destination=' + str(route.destination))
                    raise EngineError('local_route_scope_denied',
                        'Selected route ' + identifier + ' failed ' + ','.join(reasons or ['unknown'])
                        + '; selected=' + ','.join(selected_route_ids)
                        + '; required=' + ','.join(sorted(required))
                        + '; run_id=' + lease.run_id + '; production_id=' + production['id'], 403)
                routes.append(route)
            goal = self._goal(reader, production, lease)
            issuer._guard(connection, guard)
            issuer._request(connection, production, run, registered)
            result = LocalMaterialPlanSources(request, ref, goal, assets, (script_ref, script), tuple(routes))
            queries = tuple(reader.queries)
        # Original ASR pure verifier owns its own actual current guard. Do not
        # nest a second qualification lease under the earlier read guard.
        with self.engine.db.connect_readonly() as connection:
            self.engine._lease(connection, lease)
            reader = _Reader(connection)
            self._origin(lease, request, script, source_script_origin, reader)
            queries += tuple(reader.queries)
            self.engine._lease(connection, lease)
        return result, queries

    def validate(self, lease, revision):
        plan = parse_local_material_plan(json.dumps(revision.body, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
        sources, queries = self.read(lease, script_revision_id=plan.source_script_revision_ref.revision_id,
            source_script_origin=plan.source_script_origin, selected_route_ids=tuple(route.route_id for route in plan.selected_capabilities))
        validate_local_material_plan_sources(plan, **vars(sources))
        if revision.kind != 'plan' or revision.revision_id != 'autonomous.plan.' + lease.run_id:
            raise EngineError('local_plan_scope_denied', 'Original registered same Run plan ID is required.', 403)
        proposal = plan.rights_proposal
        declaration = self.runtime.config.local_registration.rights_declaration
        if sources.request.automation.mode == 'unattended':
            with self.engine.db.connect_readonly() as connection:
                run = self.engine._lease(connection, lease)
                owner = self.engine._production(connection, run['production_id'])['owner']
            current = self.engine.production_admissions.rights_proposal(self.engine._authorization_identity(owner), lease)
        else:
            from video_creator.application.production_ports import ProductionPorts
            current = ProductionPorts(self.engine, self.runtime.worker, declaration, self.runtime.sha256).rights_proposal(lease)
        ignored = {'fencing_token', 'checked_at_us', 'valid_until_us'}
        if proposal.model_dump(exclude=ignored) != current.model_dump(exclude=ignored):
            raise EngineError('local_plan_rights_conflict', 'Historical plan declaration differs from actual installed scope.', 409)
        snapshot = _PlanSnapshot(self, lease, queries, digest(canonical(revision)))
        self._snapshots[id(snapshot)] = snapshot
        return snapshot

    def assert_writer(self, connection, lease, snapshot, guard):
        if self._snapshots.get(id(snapshot)) is not snapshot or snapshot.source is not self or snapshot.lease != lease:
            raise EngineError('local_plan_source_denied', 'Original held same lease source snapshot required.', 403)
        self.engine._lease(connection, lease)
        self.engine.production_admissions._guard(connection, guard)
        for sql, arguments, expected in snapshot.queries:
            if tuple(tuple(row) for row in connection.execute(sql, arguments).fetchall()) != expected:
                raise EngineError('local_plan_source_changed', 'Original source changed before plan writer commit.', 409)

    def master_selection(self, lease, execution_ports, *, policy, plan_revision_id):
        from video_creator.domain.local_bundle import select_local_masters
        self.runtime._remember_current_services_check(lease, execution_ports, policy)
        admission = execution_ports.production_admission if policy else execution_ports.current_production_admission
        fact = admission(lease, plan_revision_id, phase='plan', action='execute_plan')
        if (fact.state != 'allowed' or fact.run_id != lease.run_id
                or fact.fencing_token != lease.fencing_token or fact.registration_sha256 != self.runtime.sha256):
            raise EngineError('production_current_admission_required', 'Actual current approved local plan is required.', 403)
        with self.engine.db.connect_readonly() as connection:
            run = self.engine._lease(connection, lease)
            row = connection.execute('SELECT * FROM creative_revisions WHERE id=? AND production_id=? AND run_id=?',
                (plan_revision_id, run['production_id'], lease.run_id)).fetchone()
            if row is None or row['kind'] != 'plan' or row['content_sha256'] != fact.target_sha256 or digest(row['body']) != fact.target_sha256:
                raise EngineError('local_selection_plan_conflict', 'Current plan approval and immutable row differ.', 409)
            revision = c.CreativeRevision.model_validate_json(row['body'])
            if revision.revision_id != plan_revision_id or revision.kind != 'plan':
                raise EngineError('local_selection_plan_conflict', 'Original plan row and body differ.', 409)
        snapshot = self.validate(lease, revision)
        plan = parse_local_material_plan(json.dumps(revision.body, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
        with self.engine.db.connect_readonly() as connection:
            # The read projection must not silently retain a changed source after approval.
            self.engine._lease(connection, lease)
            for sql, arguments, expected in snapshot.queries:
                if tuple(tuple(value) for value in connection.execute(sql, arguments).fetchall()) != expected:
                    raise EngineError('local_plan_source_changed', 'Original source changed before master selection.', 409)
            production = self.engine._production(connection, run['production_id'])
            request = c.parse_production_request(production['request_json'])
        selection = select_local_masters(request, plan, c.RevisionRef(revision_id=plan_revision_id,
            kind='plan', content_sha256=fact.target_sha256))
        current = admission(lease, plan_revision_id, phase='plan', action='execute_plan')
        if (current.state != 'allowed' or current.target_sha256 != fact.target_sha256
                or current.fencing_token != lease.fencing_token or current.registration_sha256 != self.runtime.sha256):
            raise EngineError('production_current_admission_required', 'Original approval changed during selection.', 403)
        return selection

    def final_context(self, lease, execution_ports, *, policy):
        # These are the original bound live execution ports and original
        # admission/current methods, not fields embedded into the plan body.
        self.runtime._remember_current_services_check(lease, execution_ports, policy)
        plan_fact, quality_fact, rights = self.runtime._current_final_execution_facts(lease, execution_ports, policy)
        with self.engine.db.connect_readonly() as connection:
            run = self.engine._lease(connection, lease)
            rows = []
            for identifier, kind, expected_sha in ((plan_fact.target_id, 'plan', plan_fact.target_sha256),
                    (quality_fact.target_id, 'quality', quality_fact.target_sha256)):
                row = connection.execute('SELECT * FROM creative_revisions WHERE id=? AND production_id=? AND run_id=?',
                    (identifier, run['production_id'], lease.run_id)).fetchone()
                if row is None or row['kind'] != kind or row['content_sha256'] != expected_sha or digest(row['body']) != expected_sha:
                    raise EngineError('local_final_context_conflict', 'Final context requires actual currently approved immutable revisions.', 409)
                value = c.CreativeRevision.model_validate_json(row['body'])
                if value.revision_id != identifier or value.kind != kind:
                    raise EngineError('local_final_context_invalid', 'Original final revision row/body differs.', 422)
                rows.append((c.RevisionRef(revision_id=identifier, kind=kind, content_sha256=expected_sha), value))
        plan = parse_local_material_plan(json.dumps(rows[0][1].body, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
        self.validate(lease, rows[0][1])
        sources, _queries = self.read(lease, script_revision_id=plan.source_script_revision_ref.revision_id,
            source_script_origin=plan.source_script_origin, selected_route_ids=tuple(route.route_id for route in plan.selected_capabilities))
        validate_local_material_plan_sources(plan, **vars(sources))
        with self.engine.db.connect_readonly() as connection:
            self.engine._lease(connection, lease)
        context = LocalMaterialFinalContext(sources, plan, rows[0], rows[1], plan_fact, quality_fact, rights)
        self._contexts[context] = (lease, execution_ports, policy)
        return context

    def context_snapshot(self, lease, context):
        original = self._contexts.get(context)
        if original is None or original[0] != lease:
            raise EngineError('local_final_context_denied', 'Original service-created same lease context is required.', 403)
        fresh = self.final_context(lease, original[1], policy=original[2])
        if (fresh.sources, fresh.plan, fresh.plan_revision, fresh.quality_revision) != (
                context.sources, context.plan, context.plan_revision, context.quality_revision):
            raise EngineError('local_final_context_conflict', 'Original final source changed.', 409)
        prior = self.validate(lease, context.plan_revision[1])
        with self.engine.db.connect_readonly() as connection:
            reader = _Reader(connection)
            self.engine._lease(connection, lease)
            reader.all('SELECT * FROM creative_revisions WHERE id=?', (context.quality_revision[0].revision_id,))
            reader.all('SELECT * FROM decisions WHERE run_id=? ORDER BY rowid', (lease.run_id,))
            reader.all('SELECT * FROM execution_bindings WHERE run_id=?', (lease.run_id,))
        snapshot = _PlanSnapshot(self, lease, prior.queries + tuple(reader.queries), prior.plan_sha256)
        self._snapshots[id(snapshot)] = snapshot
        return snapshot

    def assert_selection_current(self, lease, selection):
        from video_creator.domain.local_bundle import LocalMasterSelectionV1
        if type(selection) is not LocalMasterSelectionV1:
            raise EngineError('local_master_selection_invalid', 'Only the sole actual local selection is allowed.', 422)
        matches = [context for context, held in tuple(self._contexts.items())
                   if held[0] == lease and context.selection == selection]
        if not matches:
            raise EngineError('local_master_selection_invalid', 'Selection lacks its original held current local context.', 409)
        self.context_snapshot(lease, matches[-1])

    def assert_context_writer(self, connection, lease, snapshot):
        if self._snapshots.get(id(snapshot)) is not snapshot or snapshot.source is not self or snapshot.lease != lease:
            raise EngineError('local_final_context_denied', 'Original held source snapshot is required.', 403)
        self.engine._lease(connection, lease)
        for sql, arguments, expected in snapshot.queries:
            if tuple(tuple(row) for row in connection.execute(sql, arguments).fetchall()) != expected:
                raise EngineError('local_plan_source_changed', 'Original context changed before writer commit.', 409)
