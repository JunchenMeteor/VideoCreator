"""Actual Owner creation actions and exact local derived source facts."""

import json
import os
import threading
import weakref
from dataclasses import dataclass
from typing import Literal

from pydantic import Field, model_validator

from video_creator.application.engine import canonical, digest, identity
from video_creator.domain import contracts as c
from video_creator.domain.daily_project_authorization import (
    DailyProjectActionReceipt,
    DailyProjectAuthorization,
    DailyProjectAuthorizationRecord,
    DailyProjectAuthorizationRef,
    DerivedProjectAuthorization,
    InstallDailyProjectAuthorization,
    ProjectDerivationReceipt,
    ProjectGoalAccepted,
    ProjectGoalInput,
    ProjectScopeDerivation,
    ProjectScopeDerivationRef,
    RevokeDailyProjectAuthorization,
)
from video_creator.domain.errors import EngineError
from video_creator.domain.owner_setup_journal import AcceptedSetupRef, DraftOrigin
from video_creator.domain.production_authorization import (
    AuthorizationActionRef,
    ProductionAuthorizationPolicy,
    ProductionPolicyRef,
)

GOAL_INTENT_SCOPE = 'project.goal.intent'
GOAL_ACCEPT_SCOPE = 'project.goal.accept'
GOAL_DENIED_SCOPE = 'project.goal.denied'
INTENT_LOCATOR_PREFIX = 'daily_project_accepted_intent:'
GOAL_INTENT_LIMIT = 32 * 1024 * 1024


def _json_body(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


class _AcceptedGoalIntent(c.Contract):
    format: Literal['accepted-daily-project-goal-v1'] = 'accepted-daily-project-goal-v1'
    instance_id: c.Identifier
    owner_subject: c.Identifier
    entry: Literal['api', 'mcp', 'native']
    idempotency_key: c.Identifier
    goal: ProjectGoalInput
    goal_sha256: c.Sha256
    request: c.ProductionRequestAny
    authorization_ref: DailyProjectAuthorizationRef
    creation_action_ref: AuthorizationActionRef
    project_id: c.Identifier
    production_id: c.Identifier
    run_id: c.Identifier
    request_revision_id: c.Identifier
    derivation_id: c.Identifier
    receipt_id: c.Identifier
    owner_body_sha256: c.Sha256
    accepted_at_us: int = Field(gt=0, strict=True)

    @model_validator(mode='after')
    def exact_original_goal_request(self):
        if (digest(canonical(self.goal)) != self.goal_sha256
                or (self.request.goal, self.request.project_id, self.request.inputs, self.request.source_bindings,
                    self.request.brief, self.request.delivery, self.request.automation.mode) != (
                    self.goal.goal, self.project_id, self.goal.inputs, self.goal.source_bindings,
                    self.goal.brief, self.goal.delivery, 'unattended')):
            raise ValueError('Accepted Goal freezes its distinct actual normalized Production request')
        return self


class _AcceptedGoalIntentV2(_AcceptedGoalIntent):
    format: Literal['accepted-daily-project-goal-v2'] = 'accepted-daily-project-goal-v2'
    project_origin: Literal['owner_setup_draft']
    draft_origin: DraftOrigin
    accepted_setup_ref: AcceptedSetupRef

    @model_validator(mode='after')
    def original_setup_draft(self):
        if ((self.project_id, self.owner_subject, self.instance_id, self.goal, self.goal_sha256) != (
                self.draft_origin.project_draft.project_id, self.draft_origin.owner_subject,
                self.draft_origin.instance_id, self.draft_origin.goal, self.draft_origin.goal_sha256)
                or self.accepted_setup_ref.setup_id != self.draft_origin.setup_id or self.entry != 'native'):
            raise ValueError('V2 reuses only its exact accepted first Goal draft')
        return self


def _parse_goal_intent(authorization, body):
    from video_creator.application.bundles import strict_json

    raw = strict_json(body.encode('utf-8'))
    if type(raw) is not dict:
        raise EngineError('daily_project_intent_invalid', 'Accepted Goal is not a strict object', 422)
    models = {'accepted-daily-project-goal-v1': _AcceptedGoalIntent,
              'accepted-daily-project-goal-v2': _AcceptedGoalIntentV2}
    model = models.get(raw.get('format'))
    if model is None:
        raise EngineError('daily_project_intent_invalid', 'Accepted Goal version is not admitted', 422)
    return authorization._model(model, body)


class _DeniedGoal(c.Contract):
    format: Literal['denied-daily-project-goal-v1'] = 'denied-daily-project-goal-v1'
    intent_sha256: c.Sha256
    goal_sha256: c.Sha256
    authorization_ref: DailyProjectAuthorizationRef
    owner_subject: c.Identifier
    instance_id: c.Identifier
    reason_code: c.Identifier
    resolved_at_us: int = Field(gt=0, strict=True)
    registry_revision: int = Field(gt=0, strict=True)


@dataclass(frozen=True, eq=False, repr=False)
class _GoalRecoveryProof:
    intent: _AcceptedGoalIntent
    parent: DailyProjectAuthorization
    pending_sha256: str
    database_revision: int


def read_pending_goal_intent(engine, bootstrap, authorization, control, owner_binding):
    """Original protected accepted-intent proof, outside every short writer.

    Unknown namespaces/floors remain the original fail-closed control path.
    This read creates neither an execution identity nor a management capability.
    Owner/current installed role and full qualification are checked separately.
    """
    document = control.read()
    if document.pending_request_sha256 is None:
        return None
    bootstrap.assert_current_directory()
    with engine.db.connect() as connection:
        revision = authorization._revision(connection)
        row = connection.execute('SELECT value FROM metadata WHERE key=?',
            (INTENT_LOCATOR_PREFIX + document.pending_request_sha256,)).fetchone()
        if row is None:
            return None
        # Use the original strict parser without accepting a caller-made locator.
        from video_creator.application.bundles import strict_json

        locator = strict_json(row[0].encode('utf-8')) if type(row[0]) is str else None
        if (type(locator) is not dict or set(locator) != {'owner_subject', 'idempotency_key', 'goal_sha256', 'intent_sha256'}
                or _json_body(locator) != row[0] or locator['intent_sha256'] != document.pending_request_sha256
                or locator['owner_subject'] != owner_binding.principal.owner_subject):
            raise EngineError('daily_project_intent_invalid', 'Actual pending Goal locator or Owner changed', 422)
        command = connection.execute('SELECT request_sha256,result_json FROM commands WHERE owner=? AND scope=? AND idempotency_key=?',
            (locator['owner_subject'], GOAL_INTENT_SCOPE, locator['idempotency_key'])).fetchone()
        if (command is None or command['request_sha256'] != locator['goal_sha256']
                or type(command['result_json']) is not str or digest(command['result_json']) != locator['intent_sha256']
                or len(command['result_json'].encode('utf-8')) > GOAL_INTENT_LIMIT):
            raise EngineError('daily_project_intent_invalid', 'Pending Goal is not the original exact authenticated accepted command', 422)
        intent = _parse_goal_intent(authorization, command['result_json'])
        if (canonical(intent) != command['result_json'] or digest(canonical(intent.goal)) != intent.goal_sha256
                or (intent.instance_id, intent.owner_subject, intent.idempotency_key, intent.goal_sha256) != (
                    engine.instance_id, locator['owner_subject'], locator['idempotency_key'], locator['goal_sha256'])
                or intent.owner_body_sha256 != digest(canonical(owner_binding))
                or revision not in (document.minimum_revision, document.minimum_revision - 1)):
            raise EngineError('daily_project_intent_invalid', 'Pending Goal canonical identity, actual Owner or reserved floor differs', 422)
        source = connection.execute('SELECT body,creation_action_json,creation_action_sha256 FROM daily_project_authorizations '
            'WHERE authorization_id=? AND revision=? AND owner=? AND instance_id=?',
            (intent.authorization_ref.authorization_id, intent.authorization_ref.revision, intent.owner_subject, engine.instance_id)).fetchone()
        if (source is None or digest(source['body']) != intent.authorization_ref.content_sha256
                or digest(source['creation_action_json']) != source['creation_action_sha256']):
            raise EngineError('daily_project_intent_invalid', 'Pending Goal original delegation bytes are unavailable', 422)
        parent = authorization._model(DailyProjectAuthorization, source['body'])
        action = authorization._model(DailyProjectActionReceipt, source['creation_action_json'])
        original = connection.execute('SELECT request_sha256,result_json FROM commands WHERE owner=? AND scope=? AND idempotency_key=?',
            (intent.owner_subject, 'daily.project.' + action.action, action.idempotency_key)).fetchone()
        if (canonical(parent) != source['body'] or canonical(action) != source['creation_action_json']
                or action.authorization_ref != intent.authorization_ref or action.action not in ('install', 'replace')
                or intent.creation_action_ref != AuthorizationActionRef(action_id=action.action_id, content_sha256=source['creation_action_sha256'])
                or original is None or tuple(original) != (action.request_sha256, source['creation_action_json'])):
            raise EngineError('daily_project_intent_invalid', 'Pending Goal requires its actual independent original Owner creation action', 422)
    path = control.path.parent / ('AcceptedGoal-' + document.pending_request_sha256 + '.json')
    data = canonical(intent).encode('utf-8')
    if (path.is_symlink() or path.is_junction() or not path.is_file() or path.stat().st_size != len(data)):
        raise EngineError('daily_project_intent_invalid', 'Exact original protected Goal recovery copy is unavailable', 422)
    with path.open('rb') as stream:
        actual = stream.read(GOAL_INTENT_LIMIT + 1)
    if actual != data:
        raise EngineError('daily_project_intent_invalid', 'Protected accepted Goal recovery bytes changed', 422)
    bootstrap.assert_current_directory()
    return _GoalRecoveryProof(intent, parent, document.pending_request_sha256, revision)


@dataclass(frozen=True, eq=False, repr=False)
class _GoalWriterContext:
    intent: _AcceptedGoalIntent
    parent: DailyProjectAuthorizationRecord
    request: object
    guard: object
    next_revision: int
    thread_id: int
    _service: object
    setup_source: object | None = None


@dataclass(frozen=True, eq=False, repr=False)
class DerivedProjectScope:
    """Original same-issuer local source; serialized provenance is not this."""
    source: DerivedProjectAuthorization
    registered: object
    _service: object


@dataclass(frozen=True)
class _DerivedPolicyRecord:
    policy_ref: ProductionPolicyRef
    policy: object
    installation_action: DailyProjectActionReceipt
    derived_source: DerivedProjectAuthorization
    current: bool = True
    revoked: bool = False
    derived_scope: DerivedProjectScope | None = None


class DailyProjectService:
    def __init__(self, engine, *, bootstrap, authorization, registrations, issuer):
        if (bootstrap.engine is not engine or authorization.engine is not engine
                or registrations.engine is not engine or issuer.engine is not engine
                or issuer.management_service is not authorization or registrations.bootstrap is not bootstrap
                or registrations.authorization.control.path != authorization.control.path):
            raise EngineError('daily_project_configuration_conflict', 'Creation service requires original same-instance Owner, control and issuer', 503)
        self.engine, self.bootstrap, self.authorization = engine, bootstrap, authorization
        self.registrations, self.issuer, self.control = registrations, issuer, authorization.control
        self._scopes = weakref.WeakSet()
        self._writers = set()
        self._owner_setup = None

    def configure_owner_setup(self, service):
        from video_creator.application.owner_setup_service import OwnerSetupService

        if (type(service) is not OwnerSetupService or service.engine is not self.engine
                or service._services.daily_projects is not self or self._owner_setup not in (None, service)):
            raise EngineError('owner_setup_instance_denied', 'Only the original same-instance setup service may recover V2', 403)
        self._owner_setup = service

    def resolve_accepted_goal_fact(self, context):
        from video_creator.application.accepted_goal_facts import (
            resolve_accepted_goal_fact,
        )

        return resolve_accepted_goal_fact(self, context)

    def resolve_before_current(self, *, native_connection=None):
        """Fixed same-instance startup/in-memory route; never mint execution."""
        with self.registrations.control.locked():
            pending = self.registrations.control.read().pending_request_sha256
        if pending is None:
            return
        # The original Owner lock is acquired first by the true OS fact root.
        self.registrations._fact_daily = self
        with (self.bootstrap.local_fact_source(native_connection=native_connection) as root,
                self.registrations.accepted_goal_facts(root) as context):
            if context is not None:
                self.resolve_accepted_goal_fact(context)

    def _model(self, model, body):
        value = self.authorization._model(model, body)
        if canonical(value) != body:
            raise EngineError('daily_project_record_invalid', 'Daily project record is not exact original canonical bytes', 422)
        return value

    def _action_receipt(self, connection, raw, sha, owner):
        action = self._model(DailyProjectActionReceipt, raw)
        command = connection.execute('SELECT request_sha256,result_json FROM commands WHERE owner=? AND scope=? AND idempotency_key=?',
            (owner, 'daily.project.' + action.action, action.idempotency_key)).fetchone()
        if (digest(raw) != sha or action.owner_subject != owner or action.instance_id != self.engine.instance_id
                or command is None or tuple(command) != (action.request_sha256, raw)
                or action.registry_revision > self.authorization._revision(connection)):
            raise EngineError('daily_project_action_invalid', 'Creation authority has no matching original actual Owner command', 422)
        return action

    def _record(self, connection, ref, owner):
        row = connection.execute('SELECT * FROM daily_project_authorizations WHERE authorization_id=? AND revision=? AND owner=? AND instance_id=?',
            (ref.authorization_id, ref.revision, owner, self.engine.instance_id)).fetchone()
        if row is None:
            raise EngineError('daily_project_authorization_not_found', 'Creation delegation is unavailable to this actual Owner', 404)
        if any(type(row[key]) is not int or row[key] not in (0, 1) for key in ('current', 'revoked')):
            raise EngineError('daily_project_record_invalid', 'Creation delegation status is damaged', 422)
        body = self._model(DailyProjectAuthorization, row['body'])
        action = self._action_receipt(connection, row['creation_action_json'], row['creation_action_sha256'], owner)
        revoked = self._action_receipt(connection, row['revocation_action_json'], row['revocation_action_sha256'], owner) if row['revoked'] else None
        if (digest(row['body']) != ref.content_sha256 or row['content_sha256'] != ref.content_sha256
                or (body.authorization_id, body.revision, body.instance_id, body.owner_subject) != (
                    ref.authorization_id, ref.revision, self.engine.instance_id, owner)
                or action.registry_revision != row['registry_revision']
                or bool(row['revocation_action_json']) != bool(row['revoked'])
                or bool(row['revocation_action_sha256']) != bool(row['revoked'])):
            raise EngineError('daily_project_record_invalid', 'Creation delegation row/body/action identities differ', 422)
        return DailyProjectAuthorizationRecord(authorization_ref=ref, authorization=body, creation_action=action,
            current=bool(row['current']), revoked=bool(row['revoked']), revocation_action=revoked), row

    def _resources(self, connection, owner, template):
        # Identical old route/input/shared-budget checks, without using any
        # pretend project ID to gain the old finite project scope.
        for expected in template.routes:
            row = connection.execute('SELECT body FROM routes WHERE id=?', (expected.route_id,)).fetchone()
            if row is None:
                raise EngineError('production_policy_route_unconfigured', 'Creation template route is not installed', 503)
            route = self.authorization._model(c.CapabilityRoute, row['body'])
            if (digest(row['body']) != expected.route_sha256 or route.cost_rule_version != expected.cost_rule_version
                    or route.source != expected.source or not route.verified or route.max_operation_cost != expected.max_operation_cost):
                raise EngineError('production_policy_route_conflict', 'Creation template differs from current actual route/cost facts', 409)
            if route.source == 'official':
                raise EngineError('official_unavailable', 'Creation template cannot install a commercial gateway', 503)
        for expected in template.input_assets:
            row = connection.execute('SELECT sha256 FROM assets WHERE id=? AND owner=?', (expected.asset_id, owner)).fetchone()
            if row is None or row[0] != expected.sha256:
                raise EngineError('production_policy_input_denied', 'Creation template requires sameOwner actual full Asset identities', 403)
        if template.budget_group_id:
            row = connection.execute('SELECT id,owner,currency,cap_units FROM budget_groups WHERE id=? AND owner=?',
                (template.budget_group_id, owner)).fetchone()
            if (row is None or digest(json.dumps(dict(row), sort_keys=True, separators=(',', ':'))) != template.budget_group_identity_sha256
                    or template.max_production_cost.units() > row['cap_units']):
                raise EngineError('production_policy_budget_conflict', 'Creation shares the actual original immutable budget group', 409)

    def _current(self, connection, record, owner_binding):
        body, owner, now = record.authorization, owner_binding.principal, self.engine.clock()
        if (not record.current or record.revoked or not body.template.valid_from_us <= now < body.expires_at_us
                or body.expires_at_us > owner.expires_at_us
                or (body.owner_subject, body.owner_binding_generation, body.owner_binding_action_id, body.authentication_binding_id) != (
                    owner.owner_subject, owner_binding.generation, owner_binding.action_id, owner.authentication_binding_id)):
            raise EngineError('daily_project_authorization_inactive', 'Creation delegation or original Owner action is no longer current', 403)
        revision = self.authorization._revision(connection)
        namespaces = {(item.system, item.namespace) for item in body.template.allowed_sources}
        for expected in body.execution_refs:
            execution, _row, installed = self.registrations._record(connection, expected.registration_ref, body.owner_subject, revision, [])
            self.registrations._active(connection, execution, installed, owner_binding)
            actual = execution.registration
            if (actual.role != expected.role or execution.installed_record_ref != body.installed_record_ref
                    or body.expires_at_us > actual.expires_at_us or not namespaces <= set(actual.allowed_source_namespaces)
                    or (actual.registration_sha256, actual.resource_manifest_sha256, actual.runtime_manifest_sha256) != (
                        body.template.registration_sha256, body.template.resource_manifest_sha256, body.template.runtime_manifest_sha256)):
                raise EngineError('daily_project_execution_changed', 'Creation delegation differs from original current installed role/source identities', 403)
        self._resources(connection, body.owner_subject, body.template)

    def _owner_action(self, capability, key, action, proposal, prepare):
        c.SourceBinding(system=key, namespace='daily-project-owner-action')
        principal = self.authorization._principal(capability, ())
        scope = 'daily.project.' + action
        request_sha = digest(_json_body({'owner_subject': principal.owner_subject, 'scope': scope,
            'idempotency_key': key, 'action': action, 'command': proposal.model_dump(mode='json')}))
        # The independent actual creation action uses the real Owner capability;
        # it never broadens ManagementPrincipal.project_ids or invents a policy.
        with self.authorization.management.action_guard(capability, (), principal.owner_subject), self.control.locked():
            with self.engine.db.connect() as connection:
                owner = self.bootstrap._read(connection)
                if owner is None or owner.principal != principal:
                    raise EngineError('production_management_denied', 'Original actual Owner binding is required', 403)
                revision = self.authorization._revision(connection)
                old = connection.execute('SELECT request_sha256,result_json FROM commands WHERE owner=? AND scope=? AND idempotency_key=?',
                    (principal.owner_subject, scope, key)).fetchone()
                if old:
                    if old['request_sha256'] != request_sha:
                        raise EngineError('idempotency_conflict', 'Creation management key names another exact proposal', 409)
                    receipt = self._model(DailyProjectActionReceipt, old['result_json'])
                    if (receipt.action, receipt.instance_id, receipt.owner_subject, receipt.request_sha256,
                            receipt.idempotency_key) != (action, self.engine.instance_id, principal.owner_subject, request_sha, key):
                        raise EngineError('daily_project_action_invalid', 'Original creation action receipt is damaged', 422)
                    floor = self.control.read()
                    if (floor.minimum_revision, floor.pending_request_sha256) == (receipt.registry_revision, request_sha):
                        self.control.complete(receipt.registry_revision, request_sha)
                    self.control.assert_revision(revision)
                    return receipt
                self.control.assert_revision(revision)
                ref, mutate = prepare(connection, owner)
                receipt = DailyProjectActionReceipt(action_id=identity('daily-project-action'), instance_id=self.engine.instance_id,
                    owner_subject=principal.owner_subject, administrator_id=principal.administrator_id,
                    authentication_binding_id=principal.authentication_binding_id, authentication_source=principal.authentication_source,
                    owner_binding_generation=owner.generation, owner_binding_action_id=owner.action_id,
                    action=action, authorization_ref=ref, derivation_ref=getattr(proposal, 'derivation_ref', None),
                    idempotency_key=key, request_sha256=request_sha, authorized_at_us=self.engine.clock(),
                    registry_revision=revision + 1, reason=proposal.reason if action.startswith('revoke') else None)
            if self.control.reserve(revision, request_sha) != receipt.registry_revision:
                raise EngineError('production_control_conflict', 'Creation reservation has a different actual revision', 409)
            with self.authorization._management_transaction(capability, ()) as writer:
                self.authorization._principal(capability, ())
                if self.authorization._revision(writer) != revision or canonical(self.bootstrap._read(writer)) != canonical(owner):
                    raise EngineError('production_management_denied', 'Original Owner/registry changed before exact creation action', 403)
                mutate(writer, owner, receipt)
                writer.execute("UPDATE metadata SET value=? WHERE key='production_authorization_registry_revision'", (str(receipt.registry_revision),))
                writer.execute('INSERT INTO commands VALUES(?,?,?,?,?)', (principal.owner_subject, scope, key, request_sha, canonical(receipt)))
                self.authorization._principal(capability, ())
            self.control.complete(receipt.registry_revision, request_sha)
            return receipt

    def install(self, capability, key, proposal: InstallDailyProjectAuthorization):
        principal = self.authorization._principal(capability, ())
        action = 'replace' if proposal.previous_ref else 'install'

        def prepare(connection, owner):
            latest = connection.execute('SELECT revision,owner FROM daily_project_authorizations WHERE authorization_id=? ORDER BY revision DESC LIMIT 1',
                (proposal.authorization_id,)).fetchone()
            if latest and (latest['owner'] != principal.owner_subject or proposal.previous_ref is None):
                raise EngineError('daily_project_authorization_conflict', 'Existing creation delegation requires its sameOwner exact replacement', 409)
            count = 0
            if proposal.previous_ref:
                old, row = self._record(connection, proposal.previous_ref, principal.owner_subject)
                if not old.current or proposal.previous_ref.authorization_id != proposal.authorization_id or latest is None or latest['revision'] != proposal.previous_ref.revision:
                    raise EngineError('daily_project_authorization_conflict', 'Replacement must name the current exact parent', 409)
                count = row['created_projects']
            if (proposal.expires_at_us <= self.engine.clock() or proposal.expires_at_us > principal.expires_at_us
                    or proposal.max_created_projects < count):
                raise EngineError('daily_project_authorization_inactive', 'Creation expiry/count cannot bypass actual Owner or prior lifetime consumption', 403)
            body = DailyProjectAuthorization(**proposal.model_dump(exclude={'previous_ref'}),
                revision=latest['revision'] + 1 if latest else 1, instance_id=self.engine.instance_id,
                owner_subject=principal.owner_subject, executing_principal_ids=(principal.owner_subject,),
                owner_binding_generation=owner.generation, owner_binding_action_id=owner.action_id,
                authentication_binding_id=principal.authentication_binding_id)
            # Resource/role/current checks are deterministic registry facts;
            # production qualification remains the original later issuer guard.
            ref = DailyProjectAuthorizationRef(authorization_id=body.authorization_id, revision=body.revision,
                content_sha256=digest(canonical(body)))
            def mutate(writer, binding, receipt):
                record = DailyProjectAuthorizationRecord(authorization_ref=ref, authorization=body,
                    creation_action=receipt, current=True, revoked=False)
                self._current(writer, record, binding)
                if proposal.previous_ref:
                    old, old_row = self._record(writer, proposal.previous_ref, principal.owner_subject)
                    if not old.current or old_row['created_projects'] != count:
                        raise EngineError('daily_project_authorization_conflict', 'Parent changed before exact replacement', 409)
                writer.execute('UPDATE daily_project_authorizations SET current=0 WHERE authorization_id=?', (body.authorization_id,))
                writer.execute('INSERT INTO daily_project_authorizations '
                    '(authorization_id,revision,instance_id,owner,body,content_sha256,creation_action_json,creation_action_sha256,current,created_projects,registry_revision) '
                    'VALUES(?,?,?,?,?,?,?,?,1,?,?)', (body.authorization_id, body.revision, self.engine.instance_id,
                    principal.owner_subject, canonical(body), ref.content_sha256, canonical(receipt), digest(canonical(receipt)), count, receipt.registry_revision))
            return ref, mutate
        return self._owner_action(capability, key, action, proposal, prepare)

    def revoke(self, capability, key, proposal: RevokeDailyProjectAuthorization):
        principal = self.authorization._principal(capability, ())
        action = 'revoke_child' if proposal.derivation_ref else 'revoke'
        def prepare(connection, _owner):
            record, _row = self._record(connection, proposal.authorization_ref, principal.owner_subject)
            if record.revoked:
                raise EngineError('daily_project_authorization_conflict', 'Original parent revocation cannot be replaced', 409)
            if proposal.derivation_ref:
                self._child(connection, proposal.derivation_ref, principal.owner_subject, proposal.authorization_ref)
            def mutate(writer, _binding, receipt):
                current, _row = self._record(writer, proposal.authorization_ref, principal.owner_subject)
                if current.revoked:
                    raise EngineError('daily_project_authorization_conflict', 'Parent was already revoked', 409)
                raw, sha = canonical(receipt), digest(canonical(receipt))
                if proposal.derivation_ref:
                    _child, row = self._child(writer, proposal.derivation_ref, principal.owner_subject, proposal.authorization_ref)
                    if row['revoked']:
                        raise EngineError('daily_project_scope_revoked', 'Original child revocation cannot be overwritten', 409)
                    writer.execute('UPDATE project_scope_derivations SET revoked=1,revocation_action_json=?,revocation_action_sha256=? WHERE derivation_id=?',
                        (raw, sha, proposal.derivation_ref.derivation_id))
                else:
                    writer.execute('UPDATE daily_project_authorizations SET revoked=1,revocation_action_json=?,revocation_action_sha256=? WHERE authorization_id=? AND revision=?',
                        (raw, sha, proposal.authorization_ref.authorization_id, proposal.authorization_ref.revision))
            return proposal.authorization_ref, mutate
        return self._owner_action(capability, key, action, proposal, prepare)

    def get(self, capability, ref):
        principal = self.authorization._principal(capability, ())
        with self.authorization.management.action_guard(capability, (), principal.owner_subject), self.control.locked(), self.engine.db.connect() as connection:
            self.control.assert_revision(self.authorization._revision(connection))
            return self._record(connection, ref, principal.owner_subject)[0]

    def _child(self, connection, ref, owner, parent_ref=None):
        row = connection.execute('SELECT * FROM project_scope_derivations WHERE derivation_id=? AND owner=? AND instance_id=?',
            (ref.derivation_id, owner, self.engine.instance_id)).fetchone()
        if row is None:
            raise EngineError('daily_project_scope_not_found', 'Exact derived local project scope is unavailable', 404)
        child = self._model(ProjectScopeDerivation, row['body'])
        receipt = self._model(ProjectDerivationReceipt, row['receipt_json'])
        command = connection.execute("SELECT request_sha256,result_json FROM commands WHERE owner=? AND scope='project.goal.accept' AND idempotency_key=?",
            (owner, receipt.idempotency_key)).fetchone()
        if (digest(row['body']) != ref.content_sha256 or row['content_sha256'] != ref.content_sha256
                or digest(row['receipt_json']) != row['receipt_sha256'] or receipt.derivation_ref != ref
                or (row['project_id'], row['production_id'], row['run_id'], row['authorization_id'], row['authorization_revision']) != (
                    child.project_id, receipt.production_id, receipt.run_id, child.authorization_ref.authorization_id, child.authorization_ref.revision)
                or parent_ref is not None and child.authorization_ref != parent_ref
                or command is None or command['request_sha256'] != receipt.goal_sha256
                or receipt.registry_revision != row['registry_revision'] or receipt.registry_revision > self.authorization._revision(connection)
                or type(row['revoked']) is not int or row['revoked'] not in (0, 1)):
            raise EngineError('daily_project_scope_invalid', 'Derived child original request/receipt/row identities differ', 422)
        accepted = self._model(ProjectGoalAccepted, command['result_json'])
        if (accepted.derivation_ref != ref or accepted.goal_sha256 != receipt.goal_sha256
                or (accepted.instance_id, accepted.project_id, accepted.production_id, accepted.run_id) != (
                    child.instance_id, child.project_id, receipt.production_id, receipt.run_id)):
            raise EngineError('daily_project_scope_invalid', 'Child original Goal acceptance and derivation receipt differ', 422)
        if row['revoked']:
            revoked = self._action_receipt(connection, row['revocation_action_json'], row['revocation_action_sha256'], owner)
            if revoked.action != 'revoke_child' or revoked.derivation_ref != ref:
                raise EngineError('daily_project_scope_invalid', 'Child revocation is not its actual exact Owner action', 422)
        elif row['revocation_action_json'] is not None or row['revocation_action_sha256'] is not None:
            raise EngineError('daily_project_scope_invalid', 'Child status has hidden revocation bytes', 422)
        return (child, receipt), row

    def derived_record(self, connection, production, registered, *, action=None):
        row = connection.execute('SELECT derivation_id,content_sha256 FROM project_scope_derivations WHERE project_id=? AND owner=?',
            (production['project_id'], registered.owner_subject)).fetchone()
        if row is None:
            return None
        registered = self.issuer._identity(registered)
        (child, receipt), status = self._child(connection, ProjectScopeDerivationRef(derivation_id=row[0], content_sha256=row[1]), registered.owner_subject)
        parent, _row = self._record(connection, child.authorization_ref, registered.owner_subject)
        # Owner/file I/O was performed by the original current guard outside
        # this writer; validate exact canonical bound DB identity here only.
        from video_creator.application.owner_bootstrap import KEY, OwnerBindingRecord

        owner_row = connection.execute('SELECT value FROM metadata WHERE key=?', (KEY,)).fetchone()
        if owner_row is None:
            raise EngineError('production_management_denied', 'Actual original Owner binding is unavailable', 403)
        owner = self._model(OwnerBindingRecord, owner_row[0])
        self._current(connection, parent, owner)
        native = self.issuer._native_bindings.get(registered)
        if native is None:
            raise EngineError('daily_project_execution_changed', 'Derived project requires the actual original durable execution source', 403)
        store, current = native
        expected_refs = {item.role: item.registration_ref for item in child.execution_refs}
        if (store.engine is not self.engine or expected_refs.get(current.record.registration.role) != current.record.registration_ref
                or current.record.installed_record_ref != child.installed_record_ref or status['revoked']
                or child.expires_at_us <= self.engine.clock() or child.executing_principal_id != registered.executing_principal_id
                or (receipt.production_id, receipt.request_revision_id, receipt.request_sha256) != (
                    production['id'], production['request_revision_id'], production['request_sha256'])
                or action is not None and action not in child.derived_policy.allowed_actions):
            raise EngineError('daily_project_scope_inactive', 'Derived scope differs from actual current caller/role/Run/request/action', 403)
        source = DerivedProjectAuthorization(parent=parent, child=child, receipt=receipt)
        scope = DerivedProjectScope(source, registered, self)
        self._scopes.add(scope)
        return _DerivedPolicyRecord(ProductionPolicyRef(policy_id=child.derivation_id, revision=1,
            content_sha256=digest(canonical(child.derived_policy))), child.derived_policy, parent.creation_action, source,
            derived_scope=scope)

    def historical_record(self, connection, production, document):
        """Exact local immutable provenance, never a current execution guard.

        A later parent/child revocation is reported without resurrecting the
        old lease or treating portable bytes as an installed Owner command.
        Bundle separately retains every current source-right/permission check.
        """
        from video_creator.domain.daily_project_authorization import (
            ProductionAuthorizationDocumentV02,
        )

        if not isinstance(document, ProductionAuthorizationDocumentV02):
            raise EngineError('daily_project_origin_invalid', 'Exact delegated provenance is required', 422)
        source = document.source
        (child, receipt), status = self._child(connection, source.receipt.derivation_ref, production['owner'])
        parent, _row = self._record(connection, child.authorization_ref, production['owner'])
        if (child != source.child or receipt != source.receipt
                or (parent.authorization_ref, parent.authorization, parent.creation_action) != (
                    source.parent.authorization_ref, source.parent.authorization, source.parent.creation_action)
                or (child.instance_id, child.owner_subject, child.project_id,
                    receipt.production_id, receipt.request_revision_id, receipt.request_sha256) != (
                    self.engine.instance_id, production['owner'], production['project_id'],
                    production['id'], production['request_revision_id'], production['request_sha256'])):
            raise EngineError('daily_project_origin_invalid', 'Portable derived source differs from its full actual local original facts', 422)
        return _DerivedPolicyRecord(document.policy_ref, child.derived_policy, parent.creation_action,
            source, current=parent.current and not bool(status['revoked']),
            revoked=parent.revoked or bool(status['revoked']))

    def assert_scope(self, scope, registered):
        if (type(scope) is not DerivedProjectScope or scope._service is not self
                or scope not in self._scopes or scope.registered is not registered):
            raise EngineError('daily_project_scope_required', 'Actual same-service and same-issuer derived source is required', 403)

    def _parent_for_goal(self, connection, owner, goal):
        ref = goal.creation_authorization_ref
        if ref is None:
            rows = connection.execute('SELECT authorization_id,revision,content_sha256 FROM daily_project_authorizations '
                'WHERE instance_id=? AND owner=? AND current=1 AND revoked=0', (self.engine.instance_id, owner)).fetchall()
            if len(rows) != 1:
                raise EngineError('daily_project_selection_required', 'One exact current creation delegation must be selected', 403)
            ref = DailyProjectAuthorizationRef(authorization_id=rows[0][0], revision=rows[0][1], content_sha256=rows[0][2])
        return self._record(connection, ref, owner)

    def _goal_scope(self, connection, registered, parent, owner_binding, goal, entry, *, recovery=None):
        self._current(connection, parent, owner_binding)
        body, template = parent.authorization, parent.authorization.template
        if (registered.owner_subject != body.owner_subject or registered.executing_principal_id != body.owner_subject
                or entry not in body.allowed_entries):
            raise EngineError('daily_project_execution_denied', 'Only the actual mapped Owner may invoke an allowed creation entry', 403)
        native = self.issuer._native_bindings.get(registered)
        roles = {item.role: item.registration_ref for item in body.execution_refs}
        if recovery is not None and (type(recovery) is not _GoalRecoveryProof
                or (recovery.intent.goal, recovery.intent.entry, recovery.intent.authorization_ref,
                    recovery.intent.owner_subject) != (goal, entry, parent.authorization_ref, registered.owner_subject)):
            raise EngineError('daily_project_intent_invalid', 'Only the actual original protected intent can retain its accepted entry', 422)
        if (native is None or roles.get(native[1].record.registration.role) != native[1].record.registration_ref
                or recovery is None and native[1].record.registration.role != ('api' if entry == 'native' else entry)
                or native[1].record.installed_record_ref != body.installed_record_ref):
            raise EngineError('daily_project_execution_denied', 'Creation uses the original installed role source and current strong identity', 403)
        if (goal.brief.language not in template.languages or goal.brief.aspect_ratio not in template.aspect_ratios
                or goal.brief.target_duration_us is not None and goal.brief.target_duration_us > template.max_duration_us
                or goal.delivery not in template.delivery_modes
                or goal.inputs.source_text and not template.caller_supplied_text_allowed):
            raise EngineError('daily_project_template_denied', 'Goal text/creative/delivery options exceed the actual creation template', 403)
        allowed_assets = {item.asset_id for item in template.input_assets}
        scopes = {(item.system, item.namespace): item for item in template.allowed_sources}
        if not set(goal.inputs.asset_ids) <= allowed_assets:
            raise EngineError('daily_project_input_denied', 'Goal cannot expand actual template Asset scope', 403)
        for source in goal.source_bindings:
            permitted = scopes.get((source.system, source.namespace))
            if (permitted is None or source.article_id and permitted.require_article_revision and not source.article_revision
                    or source.topic_id and permitted.require_topic_revision and not source.topic_revision):
                raise EngineError('daily_project_source_denied', 'Goal source must match the exact allowed system/namespace/revisions', 403)

    def _quota(self, connection, parent, row):
        if (type(row['created_projects']) is not int or row['created_projects'] < 0
                or row['created_projects'] >= parent.authorization.max_created_projects):
            raise EngineError('daily_project_creation_quota', 'The actual lifetime creation count is exhausted or damaged', 403)
        active = connection.execute('SELECT COUNT(*) FROM project_scope_derivations d JOIN productions p ON p.id=d.production_id '
            "WHERE d.authorization_id=? AND d.owner=? AND p.status NOT IN ('succeeded','failed','cancelled')",
            (parent.authorization_ref.authorization_id, parent.authorization.owner_subject)).fetchone()[0]
        if active >= parent.authorization.max_active_productions:
            raise EngineError('daily_project_active_quota', 'Creation delegation has its actual maximum active productions', 403)

    def _request_for_goal(self, goal, parent, project_id, *, pinned=None):
        template = parent.authorization.template
        fields = {'goal': goal.goal, 'project_id': project_id, 'inputs': goal.inputs,
            'source_bindings': goal.source_bindings, 'brief': goal.brief, 'delivery': goal.delivery,
            'automation': c.Automation(mode='unattended', max_revision_cycles=template.max_revision_cycles),
            'policy': c.ExecutionPolicy(allowed_provider_routes=tuple(item.route_id for item in template.routes),
                external_transfer_allowed=template.external_transfer_allowed, max_cost=template.max_production_cost,
                budget_group_id=template.budget_group_id)}
        if isinstance(pinned, c.ProductionRequestV03):
            request = c.ProductionRequestV03(**fields, delivery_requirements=pinned.delivery_requirements)
            with self.engine.db.connect() as connection:
                normalized = self.engine._resolve_v03_request(connection, parent.authorization.owner_subject, request)
        elif pinned is not None:
            normalized = self.engine._resolve_request(c.ProductionRequest(**fields))
        elif 'qualified_method_runtime_v1' in template.alignment_modes:
            # A real installation-wide evidence default can cover the actual
            # new project. It is independent of the creation delegation and
            # never becomes a made-up per-work reference or qualification.
            try:
                with self.engine.db.connect() as connection:
                    normalized = self.engine._resolve_v03_request(connection, parent.authorization.owner_subject,
                        c.ProductionRequestV03(**fields))
            except EngineError as error:
                if error.code != 'alignment_required' or 'strict_reference_v1' not in template.alignment_modes:
                    raise
                normalized = self.engine._resolve_request(c.ProductionRequest(**fields))
        else:
            normalized = self.engine._resolve_request(c.ProductionRequest(**fields))
        requirements = normalized.delivery_requirements
        mode = requirements.alignment_evidence_policy if isinstance(normalized, c.ProductionRequestV03) else 'strict_reference_v1'
        if mode not in template.alignment_modes or pinned is not None and normalized != pinned:
            raise EngineError('daily_project_evidence_changed', 'Original accepted request/evidence differs from the finite template or original pinned policy', 403)
        return normalized

    def _intent_path(self, intent):
        # Fixed original protected Control directory, never a caller path.
        return self.control.path.parent / ('AcceptedGoal-' + digest(canonical(intent)) + '.json')

    def _retain_intent_file(self, intent):
        self.bootstrap.assert_current_directory()
        path, data = self._intent_path(intent), canonical(intent).encode('utf-8')
        if len(data) > GOAL_INTENT_LIMIT:
            raise EngineError('daily_project_intent_limit', 'Complete accepted Goal intent exceeds the finite journal limit', 413)
        if path.exists():
            if path.is_symlink() or path.is_junction() or not path.is_file() or path.stat().st_size != len(data):
                raise EngineError('daily_project_intent_invalid', 'Original protected accepted Goal bytes changed', 422)
            with path.open('rb') as stream:
                actual = stream.read(GOAL_INTENT_LIMIT + 1)
            if actual != data:
                raise EngineError('daily_project_intent_invalid', 'Original protected accepted Goal bytes changed', 422)
            return
        with path.open('xb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if os.name != 'nt':
            descriptor = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        self.bootstrap.assert_current_directory()

    def _intent(self, connection, subject, key, goal, *, check_file=True):
        row = connection.execute('SELECT request_sha256,result_json FROM commands WHERE owner=? AND scope=? AND idempotency_key=?',
            (subject, GOAL_INTENT_SCOPE, key)).fetchone()
        if row is None:
            return None
        if row['request_sha256'] != digest(canonical(goal)):
            raise EngineError('idempotency_conflict', 'Goal key belongs to different original canonical input', 409)
        intent = _parse_goal_intent(self.authorization, row['result_json'])
        if (intent.instance_id, intent.owner_subject, intent.idempotency_key, intent.goal, intent.goal_sha256) != (
                self.engine.instance_id, subject, key, goal, row['request_sha256']):
            raise EngineError('daily_project_intent_invalid', 'Original authenticated accepted Goal identities differ', 422)
        path, data = self._intent_path(intent), canonical(intent).encode('utf-8')
        if check_file:
            if (path.is_symlink() or path.is_junction() or not path.is_file()
                    or path.stat().st_size != len(data) or len(data) > GOAL_INTENT_LIMIT):
                raise EngineError('daily_project_intent_invalid', 'Exact protected Goal recovery bytes are unavailable', 422)
            with path.open('rb') as stream:
                actual = stream.read(GOAL_INTENT_LIMIT + 1)
            if actual != data:
                raise EngineError('daily_project_intent_invalid', 'Exact protected Goal recovery bytes changed', 422)
        return intent

    def _original_result(self, connection, subject, key, goal):
        denied = connection.execute('SELECT request_sha256,result_json FROM commands WHERE owner=? AND scope=? AND idempotency_key=?',
            (subject, GOAL_DENIED_SCOPE, key)).fetchone()
        if denied:
            if denied['request_sha256'] != digest(canonical(goal)):
                raise EngineError('idempotency_conflict', 'Goal key belongs to different original canonical input', 409)
            result = self._model(_DeniedGoal, denied['result_json'])
            intent = self._intent(connection, subject, key, goal, check_file=False)
            if (intent is None or digest(canonical(intent)) != result.intent_sha256
                    or (result.instance_id, result.owner_subject, result.goal_sha256, result.authorization_ref) != (
                        self.engine.instance_id, subject, intent.goal_sha256, intent.authorization_ref)
                    or result.registry_revision > self.authorization._revision(connection)):
                raise EngineError('daily_project_intent_invalid', 'Original denied Goal resolution is damaged', 422)
            raise EngineError(result.reason_code, 'Original accepted Goal was resolved without authorization; no project or production was dispatched', 403)
        row = connection.execute('SELECT request_sha256,result_json FROM commands WHERE owner=? AND scope=? AND idempotency_key=?',
            (subject, GOAL_ACCEPT_SCOPE, key)).fetchone()
        if row is None:
            return None
        if row['request_sha256'] != digest(canonical(goal)):
            raise EngineError('idempotency_conflict', 'Goal key belongs to different original canonical input', 409)
        result = self._model(ProjectGoalAccepted, row['result_json'])
        production = self.engine._production(connection, result.production_id, subject)
        accepted = self.engine._acceptance_receipt(connection, production, canonical(result.production))
        if ((result.instance_id, result.project_id, result.production_id, result.run_id, result.goal_sha256) != (
                self.engine.instance_id, accepted.project_id, accepted.production_id, accepted.run_id, row['request_sha256'])):
            raise EngineError('daily_project_result_invalid', 'Original Goal response identities differ from actual original Production acceptance', 422)
        self._child(connection, result.derivation_ref, subject)
        return result

    def accept(self, subject, key, goal: ProjectGoalInput, *, entry):
        c.SourceBinding(system=key, namespace='project-goal-command')
        if entry not in ('api', 'mcp', 'native'):
            raise EngineError('daily_project_execution_denied', 'Creation entry is not admitted', 403)
        # A historical exact receipt grants no new execution permission.
        with self.engine.db.connect() as connection:
            connection.execute('BEGIN')
            original = self._original_result(connection, subject, key, goal)
            if original is not None:
                return original
        registered = self.engine._authorization_identity(subject)
        with self.issuer.current_guard(registered) as guard:
            with self.engine.db.connect() as connection:
                registered, _revision = self.issuer._guard(connection, guard)
                owner = self.bootstrap._read(connection)
                parent, row = self._parent_for_goal(connection, subject, goal)
                self._goal_scope(connection, registered, parent, owner, goal, entry)
                self._quota(connection, parent, row)
                intent = self._intent(connection, subject, key, goal)
                if type(intent) is _AcceptedGoalIntentV2:
                    raise EngineError('owner_setup_goal_source_required', 'Pending first Goal requires its original private accepted setup source', 403)
                if intent is None:
                    project_id = identity('project')
                    request = self._request_for_goal(goal, parent, project_id)
                    intent = _AcceptedGoalIntent(instance_id=self.engine.instance_id, owner_subject=subject,
                        entry=entry, idempotency_key=key, goal=goal, goal_sha256=digest(canonical(goal)),
                        request=request,
                        authorization_ref=parent.authorization_ref, creation_action_ref=AuthorizationActionRef(
                            action_id=parent.creation_action.action_id, content_sha256=digest(canonical(parent.creation_action))),
                        project_id=project_id, production_id=identity('production'), run_id=identity('run'),
                        request_revision_id=identity('request'), derivation_id=identity('project-scope'), receipt_id=identity('project-derivation'),
                        owner_body_sha256=digest(canonical(owner)), accepted_at_us=self.engine.clock())
                elif (intent.entry, intent.authorization_ref, intent.owner_body_sha256) != (entry, parent.authorization_ref, digest(canonical(owner))):
                    raise EngineError('daily_project_intent_inactive', 'Original accepted Goal cannot silently select a changed authority/entry/Owner', 403)
            self._retain_intent_file(intent)
            with self.engine.db.transaction() as connection:
                self.issuer._guard(connection, guard)
                # The exact protected file was read/retained before the writer;
                # this same-connection check revalidates the journal only.
                previous = self._intent(connection, subject, key, goal, check_file=False)
                if previous is None:
                    connection.execute('INSERT INTO commands VALUES(?,?,?,?,?)',
                        (subject, GOAL_INTENT_SCOPE, key, intent.goal_sha256, canonical(intent)))
                elif previous != intent:
                    raise EngineError('daily_project_intent_invalid', 'Original accepted Goal intent changed', 422)
                locator = _json_body({'owner_subject': subject, 'idempotency_key': key,
                    'goal_sha256': intent.goal_sha256, 'intent_sha256': digest(canonical(intent))})
                metadata_key = INTENT_LOCATOR_PREFIX + digest(canonical(intent))
                original_locator = connection.execute('SELECT value FROM metadata WHERE key=?', (metadata_key,)).fetchone()
                if original_locator and original_locator[0] != locator:
                    raise EngineError('daily_project_intent_invalid', 'Original pending Goal locator changed', 422)
                if not original_locator:
                    connection.execute('INSERT INTO metadata VALUES(?,?)', (metadata_key, locator))
            return self._commit_intent(registered, guard, intent)

    def accept_owner_setup_goal(self, source):
        from video_creator.application.owner_setup_sources import OwnerSetupGoalSource

        if (type(source) is not OwnerSetupGoalSource or self._owner_setup is None
                or source._service is not self._owner_setup or source._daily is not self):
            raise EngineError('owner_setup_goal_source_denied', 'Private first Goal needs its original strong setup source', 403)
        service = self._owner_setup
        service.assert_goal_current(source)
        subject, key, goal = source.draft_origin.owner_subject, source.idempotency_key, source.goal
        with self.engine.db.connect() as connection:
            original = self._original_result(connection, subject, key, goal)
            if original is not None:
                row = service._row(connection, source.accepted_setup_ref.setup_id)
                if row['goal_result_json'] != canonical(original):
                    raise EngineError('owner_setup_goal_already_consumed', 'Original first draft belongs to another acceptance', 409)
                return original
        registered = source.registered
        with self.issuer.current_guard(registered) as guard:
            with self.engine.db.connect() as connection:
                service.assert_goal_local_current(source, connection)
                self.issuer._guard(connection, guard)
                owner = self.bootstrap._read(connection)
                ref = service.goal_authorization_ref(source)
                parent, row = self._record(connection, ref, subject)
                self._goal_scope(connection, registered, parent, owner, goal, 'native')
                self._quota(connection, parent, row)
                intent = self._intent(connection, subject, key, goal)
                if intent is None:
                    production, run, request_revision, derivation, receipt = source.planned_ids
                    project_id = source.draft_origin.project_draft.project_id
                    intent = _AcceptedGoalIntentV2(instance_id=self.engine.instance_id, owner_subject=subject,
                        entry='native', idempotency_key=key, goal=goal, goal_sha256=digest(canonical(goal)),
                        request=self._request_for_goal(goal, parent, project_id), authorization_ref=parent.authorization_ref,
                        creation_action_ref=AuthorizationActionRef(action_id=parent.creation_action.action_id,
                            content_sha256=digest(canonical(parent.creation_action))), project_id=project_id,
                        production_id=production, run_id=run, request_revision_id=request_revision,
                        derivation_id=derivation, receipt_id=receipt, owner_body_sha256=digest(canonical(owner)),
                        accepted_at_us=self.engine.clock(), project_origin='owner_setup_draft',
                        draft_origin=source.draft_origin, accepted_setup_ref=source.accepted_setup_ref)
                elif (type(intent) is not _AcceptedGoalIntentV2 or intent.draft_origin != source.draft_origin
                        or intent.accepted_setup_ref != source.accepted_setup_ref or intent.authorization_ref != ref):
                    raise EngineError('idempotency_conflict', 'Goal key belongs to another setup/origin/draft/current parent', 409)
            self._retain_intent_file(intent)
            with self.engine.db.transaction() as connection:
                service.assert_goal_local_current(source, connection)
                self.issuer._guard(connection, guard)
                previous = self._intent(connection, subject, key, goal, check_file=False)
                if previous is None:
                    connection.execute('INSERT INTO commands VALUES(?,?,?,?,?)',
                        (subject, GOAL_INTENT_SCOPE, key, intent.goal_sha256, canonical(intent)))
                elif previous != intent:
                    raise EngineError('owner_setup_goal_changed', 'Original private V2 intent changed', 409)
                locator = _json_body({'owner_subject': subject, 'idempotency_key': key,
                    'goal_sha256': intent.goal_sha256, 'intent_sha256': digest(canonical(intent))})
                metadata_key = INTENT_LOCATOR_PREFIX + digest(canonical(intent))
                existing = connection.execute('SELECT value FROM metadata WHERE key=?', (metadata_key,)).fetchone()
                if existing is not None and existing[0] != locator:
                    raise EngineError('daily_project_intent_invalid', 'Original V2 pending locator changed', 422)
                if existing is None:
                    connection.execute('INSERT INTO metadata VALUES(?,?)', (metadata_key, locator))
                service.assert_goal_local_current(source, connection)
            return self._commit_intent(registered, guard, intent, setup_source=source)

    def recover_pending(self, registered, installation):
        """Resolve only the original Goal reservation, before normal dispatch.

        Full installed observation was obtained outside locks by the issuer.
        This exact store guard performs Owner -> Production locking and verifies
        original current rows. No provider, Owner action, new ID or lease occurs.
        """
        binding = self.issuer._native_bindings.get(registered)
        if binding is None:
            return
        store, current = binding
        with store._accepted_goal_guard(current) as pair:
            native_guard, proof = pair
            if proof is None:
                return
            intent = proof.intent
            with self.issuer._issued_guard(registered, installation, proof.database_revision, native_guard=native_guard) as guard:
                with self.engine.db.connect() as connection:
                    self.issuer._guard(connection, guard)
                    result_row = connection.execute('SELECT request_sha256 FROM commands WHERE owner=? AND scope IN (?,?) AND idempotency_key=?',
                        (intent.owner_subject, GOAL_ACCEPT_SCOPE, GOAL_DENIED_SCOPE, intent.idempotency_key)).fetchall()
                    if result_row:
                        if len(result_row) != 1 or result_row[0][0] != intent.goal_sha256:
                            raise EngineError('daily_project_intent_invalid', 'Original Goal has conflicting resolution commands', 422)
                        try:
                            self._original_result(connection, intent.owner_subject, intent.idempotency_key, intent.goal)
                        except EngineError as error:
                            if error.status_code != 403:
                                raise
                            denied = self._model(_DeniedGoal, connection.execute('SELECT result_json FROM commands WHERE owner=? AND scope=? AND idempotency_key=?',
                                (intent.owner_subject, GOAL_DENIED_SCOPE, intent.idempotency_key)).fetchone()[0])
                            if denied.registry_revision != proof.database_revision:
                                raise EngineError('daily_project_intent_invalid', 'Original denied revision differs from reserved floor', 422) from None
                        if self.control.read().minimum_revision != proof.database_revision:
                            raise EngineError('daily_project_intent_invalid', 'Committed Goal is behind its original reserved revision', 422)
                        self.control.complete(proof.database_revision, proof.pending_sha256)
                        return
                    if self.control.read().minimum_revision != proof.database_revision + 1:
                        raise EngineError('daily_project_intent_invalid', 'Uncommitted Goal must own exactly its original next revision', 422)
                    parent, row = self._record(connection, intent.authorization_ref, intent.owner_subject)
                    try:
                        self._goal_scope(connection, registered, parent, self.bootstrap._read(connection), intent.goal, intent.entry, recovery=proof)
                        self._quota(connection, parent, row)
                        self._request_for_goal(intent.goal, parent, intent.project_id, pinned=intent.request)
                    except EngineError as error:
                        # Corrupt/missing facts and unknown namespaces are not
                        # permissions denial and remain explicit repair paths.
                        if error.status_code != 403:
                            raise
                        denial = error.code
                    else:
                        denial = None
                if denial is None:
                    if type(intent) is _AcceptedGoalIntentV2:
                        if self._owner_setup is None:
                            raise EngineError('owner_setup_recovery_source_required', 'Exact accepted setup recovery must be assembled before Ready', 503)
                        with self._owner_setup.recovery_goal_source(intent) as source:
                            self._commit_intent(registered, guard, intent, recovery=proof, setup_source=source)
                    else:
                        self._commit_intent(registered, guard, intent, recovery=proof)
                else:
                    self._deny_intent(guard, proof, denial)

    def _deny_intent(self, guard, proof, reason):
        intent, revision = proof.intent, proof.database_revision + 1
        result = _DeniedGoal(intent_sha256=proof.pending_sha256, goal_sha256=intent.goal_sha256,
            authorization_ref=intent.authorization_ref, owner_subject=intent.owner_subject,
            instance_id=self.engine.instance_id, reason_code=reason, resolved_at_us=self.engine.clock(), registry_revision=revision)
        with self.engine.db.transaction() as connection:
            self.issuer._guard(connection, guard)
            if (self.authorization._revision(connection) != proof.database_revision
                    or self._intent(connection, intent.owner_subject, intent.idempotency_key, intent.goal, check_file=False) != intent):
                raise EngineError('daily_project_intent_invalid', 'Original denied Goal changed before exact resolution', 422)
            connection.execute('INSERT INTO commands VALUES(?,?,?,?,?)',
                (intent.owner_subject, GOAL_DENIED_SCOPE, intent.idempotency_key, intent.goal_sha256, canonical(result)))
            connection.execute("UPDATE metadata SET value=? WHERE key='production_authorization_registry_revision'", (str(revision),))
            self.issuer._guard(connection, guard)
        self.control.complete(revision, proof.pending_sha256)

    def _commit_intent(self, registered, guard, intent, *, recovery=None, setup_source=None):
        if type(intent) is _AcceptedGoalIntentV2:
            if self._owner_setup is None or setup_source is None:
                raise EngineError('owner_setup_goal_source_required', 'V2 cannot execute through the public V1 path', 403)
            self._owner_setup.assert_goal_current(setup_source)
        with self.engine.db.connect() as connection:
            revision = self.authorization._revision(connection)
            parent, row = self._record(connection, intent.authorization_ref, intent.owner_subject)
            owner = self.bootstrap._read(connection)
            self._goal_scope(connection, registered, parent, owner, intent.goal, intent.entry, recovery=recovery)
            self._quota(connection, parent, row)
            if (digest(canonical(owner)) != intent.owner_body_sha256 or intent.creation_action_ref != AuthorizationActionRef(
                    action_id=parent.creation_action.action_id, content_sha256=digest(canonical(parent.creation_action)))):
                raise EngineError('daily_project_intent_inactive', 'Accepted intent differs from the original actual creation action/Owner', 403)
        request = self._request_for_goal(intent.goal, parent, intent.project_id, pinned=intent.request)
        next_revision = self.control.reserve(revision, digest(canonical(intent)))
        context = _GoalWriterContext(intent, parent, request, guard, next_revision, threading.get_ident(), self, setup_source)
        self._writers.add(context)
        try:
            with self.engine.db.transaction() as connection:
                self.issuer._guard(connection, guard)
                if self.authorization._revision(connection) != revision:
                    raise EngineError('production_registry_conflict', 'Registry changed before exact Goal derivation', 409)
                parent, row = self._record(connection, intent.authorization_ref, intent.owner_subject)
                self._goal_scope(connection, registered, parent, self.bootstrap._read(connection), intent.goal, intent.entry, recovery=recovery)
                self._quota(connection, parent, row)
                if type(intent) is _AcceptedGoalIntentV2:
                    self._owner_setup.assert_goal_local_current(setup_source, connection)
                    if (setup_source.draft_origin != intent.draft_origin
                            or setup_source.accepted_setup_ref != intent.accepted_setup_ref
                            or connection.execute('SELECT 1 FROM productions WHERE project_id=?', (intent.project_id,)).fetchone()
                            or connection.execute('SELECT 1 FROM project_scope_derivations WHERE project_id=?', (intent.project_id,)).fetchone()):
                        raise EngineError('owner_setup_goal_already_consumed', 'Only the exact unconsumed first Goal draft may be reused', 409)
                else:
                    project = c.ProjectInput(name=intent.goal.name, goal=intent.goal.goal, source_text=intent.goal.inputs.source_text)
                    connection.execute('INSERT INTO projects(id,owner,body,saved_at_us) VALUES(?,?,?,?)',
                        (intent.project_id, intent.owner_subject, canonical(project), intent.accepted_at_us))
                connection.execute("UPDATE metadata SET value=? WHERE key='production_authorization_registry_revision'", (str(next_revision),))
                accepted = self.engine._accept_production_connection(connection, intent.owner_subject,
                    'daily-production.' + digest(canonical(intent)), request,
                    authorization_guard=guard, authorization_error=None,
                    planned_ids=(intent.production_id, intent.run_id, intent.request_revision_id), daily_context=context)
                child_row = connection.execute('SELECT content_sha256 FROM project_scope_derivations WHERE derivation_id=?', (intent.derivation_id,)).fetchone()
                result = ProjectGoalAccepted(instance_id=self.engine.instance_id, project_id=intent.project_id,
                    production_id=accepted.production_id, run_id=accepted.run_id, goal_sha256=intent.goal_sha256,
                    derivation_ref=ProjectScopeDerivationRef(derivation_id=intent.derivation_id, content_sha256=child_row[0]), production=accepted)
                connection.execute('UPDATE commands SET result_json=? WHERE owner=? AND scope=? AND idempotency_key=?',
                    (canonical(result), intent.owner_subject, GOAL_ACCEPT_SCOPE, intent.idempotency_key))
                connection.execute("UPDATE metadata SET value=? WHERE key='production_authorization_registry_revision'", (str(next_revision),))
                if type(intent) is _AcceptedGoalIntentV2:
                    self._owner_setup.commit_goal(connection, setup_source, result)
                    self._owner_setup.assert_goal_local_current(setup_source, connection)
                self.issuer._guard(connection, guard)
            self.control.complete(next_revision, digest(canonical(intent)))
            return result
        finally:
            self._writers.remove(context)

    def commit_child(self, connection, context, production, run):
        if (type(context) is not _GoalWriterContext or context._service is not self or context not in self._writers
                or context.thread_id != threading.get_ident()):
            raise EngineError('daily_project_writer_required', 'Original actual Goal writer/thread is required', 403)
        registered, _revision = self.issuer._guard(connection, context.guard)
        intent, parent = context.intent, context.parent
        if (production['id'], production['project_id'], production['owner'], run['id'], production['request_revision_id']) != (
                intent.production_id, intent.project_id, intent.owner_subject, intent.run_id, intent.request_revision_id):
            raise EngineError('daily_project_writer_required', 'Original planned actual Project/Production/Run identities differ', 403)
        policy = ProductionAuthorizationPolicy(**parent.authorization.template.model_dump(exclude={'expires_at_us'}),
            instance_id=self.engine.instance_id, owner_subject=intent.owner_subject, executing_principal_ids=(registered.executing_principal_id,),
            project_ids=(intent.project_id,), expires_at_us=parent.authorization.expires_at_us)
        child = ProjectScopeDerivation(derivation_id=intent.derivation_id, authorization_ref=parent.authorization_ref,
            creation_action_ref=intent.creation_action_ref, instance_id=self.engine.instance_id, owner_subject=intent.owner_subject,
            executing_principal_id=registered.executing_principal_id, entry=intent.entry, project_id=intent.project_id,
            goal_sha256=intent.goal_sha256, installed_record_ref=parent.authorization.installed_record_ref,
            execution_refs=parent.authorization.execution_refs, expires_at_us=parent.authorization.expires_at_us, derived_policy=policy)
        ref = ProjectScopeDerivationRef(derivation_id=child.derivation_id, content_sha256=digest(canonical(child)))
        receipt = ProjectDerivationReceipt(receipt_id=intent.receipt_id, instance_id=self.engine.instance_id,
            owner_subject=intent.owner_subject, authorization_ref=parent.authorization_ref,
            creation_action_ref=intent.creation_action_ref, derivation_ref=ref, goal_sha256=intent.goal_sha256,
            request_sha256=production['request_sha256'], production_id=production['id'], run_id=run['id'],
            request_revision_id=production['request_revision_id'], idempotency_key=intent.idempotency_key,
            accepted_at_us=intent.accepted_at_us, registry_revision=context.next_revision)
        connection.execute('INSERT INTO project_scope_derivations '
            '(derivation_id,project_id,instance_id,owner,authorization_id,authorization_revision,production_id,run_id,body,content_sha256,receipt_json,receipt_sha256,registry_revision) '
            'VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)', (child.derivation_id, child.project_id, self.engine.instance_id,
            intent.owner_subject, parent.authorization_ref.authorization_id, parent.authorization_ref.revision,
            production['id'], run['id'], canonical(child), ref.content_sha256, canonical(receipt), digest(canonical(receipt)), context.next_revision))
        # The receipt and actual child become visible atomically with the same
        # original acceptance; the initial response is finalized before commit.
        accepted = self.engine._accepted(connection, production)
        result = ProjectGoalAccepted(instance_id=self.engine.instance_id, project_id=child.project_id,
            production_id=production['id'], run_id=run['id'], derivation_ref=ref, goal_sha256=intent.goal_sha256, production=accepted)
        connection.execute('INSERT INTO commands VALUES(?,?,?,?,?)',
            (intent.owner_subject, GOAL_ACCEPT_SCOPE, intent.idempotency_key, intent.goal_sha256, canonical(result)))
        updated = connection.execute('UPDATE daily_project_authorizations SET created_projects=created_projects+1 '
            'WHERE authorization_id=? AND revision=? AND created_projects<?',
            (parent.authorization_ref.authorization_id, parent.authorization_ref.revision, parent.authorization.max_created_projects))
        if updated.rowcount != 1:
            raise EngineError('daily_project_creation_quota', 'Actual lifetime creation counter changed before commit', 403)
