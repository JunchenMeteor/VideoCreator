"""Owner management actions and immutable policy registry, separate from execution."""

import json
from contextlib import contextmanager

from video_creator.application.delivery_metadata import DeliveryResolver
from video_creator.application.engine import canonical, digest, identity
from video_creator.application.production_management import (
    ProductionAuthorizationControl,
    ProductionManagementRegistry,
)
from video_creator.domain import contracts as c
from video_creator.domain.errors import EngineError
from video_creator.domain.production_authorization import (
    AuthorizationActionReceipt,
    InstallProductionPolicy,
    ProductionAuthorizationPolicy,
    ProductionPolicyRecord,
    ProductionPolicyRef,
    RevokeProductionPolicy,
    SelectProductionPolicy,
)


class ProductionAuthorizationService:
    def __init__(self, engine, management: ProductionManagementRegistry | None = None,
                 control: ProductionAuthorizationControl | None = None):
        if management is not None and management.instance_id != engine.instance_id:
            raise EngineError('production_authorization_configuration_conflict', 'Management registry belongs to another instance', 503)
        if control is not None and control.instance_id != engine.instance_id:
            raise EngineError('production_authorization_configuration_conflict', 'Control floor belongs to another instance', 503)
        expected_control = engine.db.data_dir / 'Control' / 'ProductionAuthorizationControl.json'
        if control is not None and control.path.resolve() != expected_control:
            raise EngineError('production_authorization_configuration_conflict', 'Retained control must remain at its fixed installation Control identity', 503)
        self.engine, self.management, self.control = engine, management, control

    def _principal(self, capability, project_ids):
        if self.management is None or self.control is None:
            raise EngineError('production_management_unconfigured', 'Actual separate Owner management and retained control are required', 503)
        return self.management.assert_current(capability, self.engine.clock(), project_ids=project_ids,
                                              owner_subject=self.management.owner_subject)

    @contextmanager
    def _management_transaction(self, capability, projects):
        """Original writer; an installed Owner service adds current identity checks."""
        with self.engine.db.transaction() as connection:
            yield connection

    @staticmethod
    def _revision(connection):
        row = connection.execute("SELECT value FROM metadata WHERE key='production_authorization_registry_revision'").fetchone()
        if (not row or not isinstance(row[0], str) or not 1 <= len(row[0]) <= 19
                or not row[0].isascii() or not row[0].isdecimal()
                or str(int(row[0])) != row[0] or int(row[0]) > 9_223_372_036_854_775_806):
            raise EngineError('production_registry_unavailable', 'Current production authorization registry revision is missing or damaged', 503)
        return int(row[0])

    @staticmethod
    def _model(model, body):
        try:
            return model.model_validate(DeliveryResolver._json(body))
        except (ValueError, TypeError):
            raise EngineError('production_authorization_invalid', 'Persisted production authorization fact is damaged', 422) from None

    def _record(self, connection, ref, owner_subject):
        row = connection.execute('SELECT * FROM production_authorization_policies WHERE policy_id=? AND revision=? AND owner=?',
            (ref.policy_id, ref.revision, owner_subject)).fetchone()
        if not row:
            raise EngineError('production_policy_not_found', 'Production policy is not available to this Owner', 404)
        if (type(row['current']) is not int or row['current'] not in (0, 1)
                or type(row['revoked']) is not int or row['revoked'] not in (0, 1)):
            raise EngineError('production_policy_changed', 'Persisted policy status is not a valid registry fact', 422)
        policy = self._model(ProductionAuthorizationPolicy, row['body'])
        if digest(row['body']) != row['content_sha256'] or row['content_sha256'] != ref.content_sha256:
            raise EngineError('production_policy_changed', 'Immutable production policy identity changed', 422)
        action = self._model(AuthorizationActionReceipt, row['installation_action_json'])
        revoked = self._model(AuthorizationActionReceipt, row['revocation_action_json']) if row['revocation_action_json'] else None
        if (digest(row['installation_action_json']) != row['installation_action_sha256']
                or bool(row['revocation_action_json']) != bool(row['revocation_action_sha256'])
                or row['revocation_action_json'] and digest(row['revocation_action_json']) != row['revocation_action_sha256']):
            raise EngineError('production_action_changed', 'Immutable Owner action bytes differ from their original receipt hash', 422)
        if (policy.instance_id != self.engine.instance_id or policy.owner_subject != owner_subject
                or action.policy_ref != ref or action.instance_id != self.engine.instance_id
                or action.owner_subject != owner_subject or action.action not in {'create', 'replace'}
                or action.registry_revision != row['registry_revision'] or bool(row['revoked']) != (revoked is not None)
                or revoked is not None and (revoked.action != 'revoke' or revoked.policy_ref != ref)):
            raise EngineError('production_policy_changed', 'Policy status and actual original action identities do not agree', 422)
        return ProductionPolicyRecord(policy_ref=ref, policy=policy, installation_action=action,
            current=bool(row['current']), revoked=bool(row['revoked']), revocation_action=revoked)

    @staticmethod
    def _project_scope(connection, owner_subject, projects):
        for project_id in projects:
            if not connection.execute('SELECT id FROM projects WHERE id=? AND owner=?', (project_id, owner_subject)).fetchone():
                raise EngineError('production_management_project_denied', 'Management scope requires actual owned project identities', 403)

    def _policy_resources(self, connection, policy):
        self._project_scope(connection, policy.owner_subject, policy.project_ids)
        for expected in policy.routes:
            row = connection.execute('SELECT body FROM routes WHERE id=?', (expected.route_id,)).fetchone()
            if not row:
                raise EngineError('production_policy_route_unconfigured', 'Exact policy route is not installed', 503)
            route = self._model(c.CapabilityRoute, row['body'])
            if (digest(row['body']) != expected.route_sha256 or route.cost_rule_version != expected.cost_rule_version
                    or route.source != expected.source or not route.verified
                    or route.max_operation_cost != expected.max_operation_cost):
                raise EngineError('production_policy_route_conflict', 'Policy must bind the actual current route and cost rule', 409)
            if route.source == 'official':
                raise EngineError('official_unavailable', 'Policy cannot admit an unimplemented commercial gateway', 503)
        for expected in policy.input_assets:
            row = connection.execute('SELECT sha256 FROM assets WHERE id=? AND owner=?', (expected.asset_id, policy.owner_subject)).fetchone()
            if not row or row['sha256'] != expected.sha256:
                raise EngineError('production_policy_input_denied', 'Policy requires actual sameOwner Asset identities and hashes', 403)
        if policy.budget_group_id:
            row = connection.execute('SELECT id,owner,currency,cap_units FROM budget_groups WHERE id=? AND owner=?',
                (policy.budget_group_id, policy.owner_subject)).fetchone()
            if not row:
                raise EngineError('budget_unauthorized', 'Production policy cannot create a budget authorization', 403)
            body = json.dumps(dict(row), sort_keys=True, separators=(',', ':'))
            if digest(body) != policy.budget_group_identity_sha256 or policy.max_production_cost.units() > row['cap_units']:
                raise EngineError('production_policy_budget_conflict', 'Policy differs from the immutable existing group identity or cap', 409)

    def _action(self, capability, key, action, command, projects, prepare, *, target_request=None):
        # Only the fixed private sameRun reauthorization service supplies this
        # exact target. An ordinary task or selection action cannot acquire it.
        if (action == 'reauthorize') != (target_request is not None):
            raise EngineError('production_management_action_invalid', 'Reauthorization requires its explicit original request target', 403)
        c.SourceBinding(system=key, namespace='production-authorization-command')
        principal = self._principal(capability, projects)
        scope = 'production.authorization.' + action
        proposal = {'owner_subject': principal.owner_subject, 'scope': scope, 'idempotency_key': key,
                    'action': action, 'command': command.model_dump(mode='json')}
        c.reject_secrets(proposal)
        body = json.dumps(proposal,
                          ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
        request_sha = digest(body)
        with self.control.locked():
            with self.engine.db.connect() as connection:
                self._project_scope(connection, principal.owner_subject, projects)
                existing = connection.execute('SELECT * FROM commands WHERE owner=? AND scope=? AND idempotency_key=?',
                    (principal.owner_subject, scope, key)).fetchone()
                revision = self._revision(connection)
                if existing:
                    if existing['request_sha256'] != request_sha:
                        raise EngineError('idempotency_conflict', 'Management key was used for a different actual action', 409)
                    receipt = self._model(AuthorizationActionReceipt, existing['result_json'])
                    if (receipt.action, receipt.request_sha256, receipt.owner_subject, receipt.instance_id) != (
                            action, request_sha, principal.owner_subject, self.engine.instance_id):
                        raise EngineError('production_action_changed', 'Original management command receipt is damaged', 422)
                    current = self.control.read()
                    if (current.minimum_revision, current.pending_request_sha256) == (receipt.registry_revision, request_sha):
                        self.control.complete(receipt.registry_revision, request_sha)
                    self.control.assert_revision(revision)
                    return receipt
                if not self.control.path.exists():
                    if revision or connection.execute('SELECT 1 FROM production_authorization_policies LIMIT 1').fetchone():
                        raise EngineError('production_restore_refresh_required', 'Existing policies require their original retained control state', 503)
                    self.control.initialize_new()
                ref, mutation = prepare(connection)
            next_revision = self.control.reserve(revision, request_sha)
            receipt = AuthorizationActionReceipt(action_id=identity('authorization-action'), instance_id=self.engine.instance_id,
                administrator_id=principal.administrator_id, authentication_binding_id=principal.authentication_binding_id,
                authentication_source=principal.authentication_source, owner_subject=principal.owner_subject,
                project_ids=tuple(projects), action=action, policy_ref=ref, idempotency_key=key,
                request_sha256=request_sha, authorized_at_us=self.engine.clock(), registry_revision=next_revision,
                reason=command.reason if isinstance(command, RevokeProductionPolicy) else None,
                target_production_id=target_request[0] if target_request else None,
                target_request_revision_id=target_request[1] if target_request else None,
                target_request_sha256=target_request[2] if target_request else None)
            # External floor was durably raised before writer. Crash/failure is
            # fail-closed, never an invisible revocation rollback.
            with self._management_transaction(capability, projects) as connection:
                self._principal(capability, projects)
                if self._revision(connection) != revision:
                    raise EngineError('production_registry_conflict', 'Registry changed before this exact management commit', 409)
                self._project_scope(connection, principal.owner_subject, projects)
                mutation(connection, receipt)
                connection.execute("UPDATE metadata SET value=? WHERE key='production_authorization_registry_revision'", (str(next_revision),))
                connection.execute('INSERT INTO commands VALUES(?,?,?,?,?)',
                    (principal.owner_subject, scope, key, request_sha, canonical(receipt)))
            self.control.complete(next_revision, request_sha)
            return receipt

    def install_policy(self, capability, idempotency_key, command: InstallProductionPolicy):
        policy = command.policy
        principal = self._principal(capability, policy.project_ids)
        if policy.instance_id != self.engine.instance_id or policy.owner_subject != principal.owner_subject:
            raise EngineError('production_policy_owner_conflict', 'Actual authenticated Owner must endorse this exact instance policy', 403)
        action = 'replace' if command.previous_ref else 'create'
        def prepare(connection):
            self._policy_resources(connection, policy)
            if policy.expires_at_us <= self.engine.clock():
                raise EngineError('production_policy_expired', 'An expired proposal cannot be installed', 403)
            current = connection.execute('SELECT revision FROM production_authorization_policies WHERE policy_id=? ORDER BY revision DESC LIMIT 1',
                (command.policy_id,)).fetchone()
            if action == 'create' and current:
                raise EngineError('production_policy_conflict', 'Existing policy requires explicit exact-version replacement', 409)
            if command.previous_ref:
                old = self._record(connection, command.previous_ref, principal.owner_subject)
                if command.previous_ref.policy_id != command.policy_id or not old.current:
                    raise EngineError('production_policy_conflict', 'Replacement targets a different or stale current policy', 409)
            ref = ProductionPolicyRef(policy_id=command.policy_id, revision=current[0] + 1 if current else 1,
                                       content_sha256=digest(canonical(policy)))
            def mutate(writer, receipt):
                self._policy_resources(writer, policy)
                if policy.expires_at_us <= self.engine.clock():
                    raise EngineError('production_policy_expired', 'Policy expired before its actual management commit', 403)
                writer.execute('UPDATE production_authorization_policies SET current=0 WHERE policy_id=?', (command.policy_id,))
                writer.execute('INSERT INTO production_authorization_policies '
                    '(policy_id,revision,owner,body,content_sha256,installation_action_json,installation_action_sha256,current,installed_at_us,registry_revision) '
                    'VALUES(?,?,?,?,?,?,?,1,?,?)', (ref.policy_id, ref.revision, principal.owner_subject, canonical(policy),
                     ref.content_sha256, canonical(receipt), digest(canonical(receipt)), receipt.authorized_at_us, receipt.registry_revision))
            return ref, mutate
        return self._action(capability, idempotency_key, action, command, policy.project_ids, prepare)

    def select_policy(self, capability, idempotency_key, command: SelectProductionPolicy):
        principal = self._principal(capability, (command.project_id,))
        def prepare(connection):
            record = self._record(connection, command.policy_ref, principal.owner_subject)
            policy = record.policy
            if (not record.current or record.revoked or not policy.valid_from_us <= self.engine.clock() < policy.expires_at_us
                    or command.project_id not in policy.project_ids or command.executing_principal_id not in policy.executing_principal_ids
                    or command.registration_sha256 != policy.registration_sha256):
                raise EngineError('production_policy_inactive', 'Selection requires an actual active policy and exact caller/project/registration scope', 403)
            self._policy_resources(connection, policy)
            selector = json.dumps({'owner': principal.owner_subject, 'project_id': command.project_id,
                'principal': command.executing_principal_id, 'registration_sha256': command.registration_sha256}, sort_keys=True, separators=(',', ':'))
            key = 'production_authorization_default:' + digest(selector)
            def mutate(writer, receipt):
                current = self._record(writer, command.policy_ref, principal.owner_subject)
                if not current.current or current.revoked or current.policy.expires_at_us <= self.engine.clock():
                    raise EngineError('production_policy_inactive', 'Selected policy changed before the actual management action', 403)
                value = json.dumps({'selection': command.model_dump(mode='json'), 'action': receipt.model_dump(mode='json')},
                    ensure_ascii=False, sort_keys=True, separators=(',', ':'))
                writer.execute('INSERT INTO metadata VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key, value))
            return command.policy_ref, mutate
        return self._action(capability, idempotency_key, 'select', command, (command.project_id,), prepare)

    def revoke_policy(self, capability, idempotency_key, command: RevokeProductionPolicy):
        principal = self._principal(capability, ())
        with self.engine.db.connect() as connection:
            initial = self._record(connection, command.policy_ref, principal.owner_subject)
        def prepare(connection):
            record = self._record(connection, command.policy_ref, principal.owner_subject)
            if record.revoked:
                raise EngineError('production_policy_already_revoked', 'A different revocation action cannot overwrite the original', 409)
            def mutate(writer, receipt):
                current = self._record(writer, command.policy_ref, principal.owner_subject)
                if current.revoked:
                    raise EngineError('production_policy_already_revoked', 'Original revocation became current', 409)
                writer.execute('UPDATE production_authorization_policies SET revoked=1,revocation_action_json=?,revocation_action_sha256=? '
                    'WHERE policy_id=? AND revision=?', (canonical(receipt), digest(canonical(receipt)),
                                                       command.policy_ref.policy_id, command.policy_ref.revision))
            return command.policy_ref, mutate
        return self._action(capability, idempotency_key, 'revoke', command, initial.policy.project_ids, prepare)

    def get_policy(self, capability, ref: ProductionPolicyRef):
        principal = self._principal(capability, ())
        with self.control.locked(), self.engine.db.connect() as connection:
            self.control.assert_revision(self._revision(connection))
            record = self._record(connection, ref, principal.owner_subject)
            self._principal(capability, record.policy.project_ids)
            return record
