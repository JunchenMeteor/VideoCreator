"""Real independent Owner input-scope registry; binding never grants execution by itself."""

import json
import re
import threading
from contextlib import contextmanager
from dataclasses import dataclass

from video_creator.application.delivery_metadata import DeliveryResolver
from video_creator.application.engine import canonical, digest, identity
from video_creator.application.local_copy_input_control import LocalCopyInputControl
from video_creator.application.local_copy_input_ports import CopyInputAdmission
from video_creator.application.local_copy_source_resolver import (
    LocalCopyBundleSourceResolver,
)
from video_creator.domain.errors import EngineError
from video_creator.domain.local_copy_input_scope import (
    BindLocalCopyInputScope,
    LocalCopyInputActionReceipt,
    LocalCopyInputActionRef,
    LocalCopyInputBinding,
    LocalCopyInputScope,
    LocalCopyInputScopeRecord,
    LocalCopyInputScopeRef,
    canonical_sha256,
    member_key,
)

REGISTRY_KEY = 'local_copy_input_registry_revision'
DEFAULT_PREFIX = 'local_copy_input_default:'
COMMAND_PREFIX = 'local.copy.input.'


@dataclass(frozen=True, eq=False, repr=False)
class _CopyGuard:
    minimum_revision: int
    thread_id: int
    issuer: object


class LocalCopyInputService:
    def __init__(self, engine, management_service, bundle_service, *, control=None):
        if management_service.engine is not engine or bundle_service.engine is not engine:
            raise EngineError('local_copy_configuration_conflict', 'Management, source reader and Engine must be the same actual instance', 503)
        expected = engine.db.data_dir / 'Control' / 'LocalCopyInputControl.json'
        if control is not None and (type(control) is not LocalCopyInputControl
                or control.instance_id != engine.instance_id or control.path.resolve() != expected):
            raise EngineError('local_copy_configuration_conflict', 'Copy control requires its distinct fixed retained local identity', 503)
        self.engine, self.management, self.bundle = engine, management_service, bundle_service
        self.control = control or LocalCopyInputControl(expected, engine.instance_id)
        self.resolver = LocalCopyBundleSourceResolver(bundle_service, management_service)
        self._guards = set()

    def authenticate_management(self, credential):
        if self.management.management is None:
            raise EngineError('production_management_unconfigured', 'Separate actual Owner management is not installed', 503)
        return self.management.management.authenticate(credential, self.engine.clock())

    @staticmethod
    def _revision(connection):
        row = connection.execute('SELECT value FROM metadata WHERE key=?', (REGISTRY_KEY,)).fetchone()
        if (not row or not isinstance(row[0], str) or not row[0].isascii() or not row[0].isdecimal()
                or str(int(row[0])) != row[0] or not 0 <= int(row[0]) < 9_223_372_036_854_775_807):
            raise EngineError('local_copy_registry_invalid', 'Copy registry revision is missing or damaged', 422)
        return int(row[0])

    @staticmethod
    def _model(model, body):
        try:
            value = model.model_validate(DeliveryResolver._json(body))
            if canonical(value) != body:
                raise ValueError('Noncanonical stored scope fact')
            return value
        except (ValueError, TypeError):
            raise EngineError('local_copy_scope_invalid', 'Persisted copy scope/action/binding is damaged', 422) from None

    def _action_fact(self, connection, receipt, owner):
        row = connection.execute('SELECT request_sha256,result_json FROM commands WHERE owner=? AND scope=? AND idempotency_key=?',
            (owner, COMMAND_PREFIX + receipt.action, receipt.idempotency_key)).fetchone()
        if (not row or row['request_sha256'] != receipt.request_sha256 or row['result_json'] != canonical(receipt)
                or receipt.instance_id != self.engine.instance_id or receipt.owner_subject != owner
                or receipt.registry_revision > self._revision(connection)):
            raise EngineError('local_copy_action_invalid', 'Copy fact has no exact actual original Owner command/action', 422)

    def _record(self, connection, ref, owner):
        row = connection.execute('SELECT * FROM local_copy_input_scopes WHERE scope_id=? AND revision=? AND owner=?',
            (ref.scope_id, ref.revision, owner)).fetchone()
        if not row:
            raise EngineError('local_copy_scope_not_found', 'Copy scope is not available to this Owner', 404)
        if any(type(row[key]) is not int or row[key] not in (0, 1) for key in ('current', 'revoked')):
            raise EngineError('local_copy_scope_invalid', 'Persisted copy scope status is damaged', 422)
        scope = self._model(LocalCopyInputScope, row['body'])
        action = self._model(LocalCopyInputActionReceipt, row['installation_action_json'])
        revoked = self._model(LocalCopyInputActionReceipt, row['revocation_action_json']) if row['revocation_action_json'] else None
        if (digest(row['body']) != row['content_sha256'] or row['content_sha256'] != ref.content_sha256
                or digest(row['installation_action_json']) != row['installation_action_sha256']
                or bool(row['revocation_action_json']) != bool(row['revocation_action_sha256'])
                or revoked is not None and digest(row['revocation_action_json']) != row['revocation_action_sha256']
                or (row['scope_id'], row['revision'], row['owner'], row['project_id'], row['policy_id'], row['policy_revision'],
                    row['registry_revision'], row['installed_at_us']) != (scope.scope_id, scope.revision, scope.owner_subject,
                    scope.destination_project_id, scope.policy_ref.policy_id, scope.policy_ref.revision,
                    action.registry_revision, action.authorized_at_us)):
            raise EngineError('local_copy_scope_invalid', 'Copy row/body/action full identities disagree', 422)
        self._action_fact(connection, action, owner)
        if revoked is not None:
            self._action_fact(connection, revoked, owner)
        try:
            return LocalCopyInputScopeRecord(scope_ref=ref, scope=scope, installation_action=action,
                current=bool(row['current']), revoked=bool(row['revoked']), revocation_action=revoked)
        except ValueError:
            raise EngineError('local_copy_scope_invalid', 'Scope and actual Owner receipts contradict each other', 422) from None

    def _policy(self, connection, scope, *, require_scope_active=False):
        record = self.management._record(connection, scope.policy_ref, scope.owner_subject)
        policy = record.policy
        action = record.installation_action
        command = connection.execute('SELECT request_sha256,result_json FROM commands WHERE owner=? AND scope=? AND idempotency_key=?',
            (scope.owner_subject, 'production.authorization.' + action.action, action.idempotency_key)).fetchone()
        if (not record.current or record.revoked or not command or command['request_sha256'] != action.request_sha256
                or command['result_json'] != canonical(action) or policy.instance_id != self.engine.instance_id
                or scope.destination_project_id not in policy.project_ids
                or not set(scope.executing_principal_ids) <= set(policy.executing_principal_ids)
                or scope.registration_sha256 != policy.registration_sha256
                or not policy.valid_from_us <= scope.valid_from_us < scope.expires_at_us <= policy.expires_at_us):
            raise EngineError('local_copy_policy_conflict', 'Scope must bind the exact current policy/Owner/project/registration/time scope', 409)
        if require_scope_active and not scope.valid_from_us <= self.engine.clock() < scope.expires_at_us:
            raise EngineError('local_copy_scope_inactive', 'Copy scope is not active at the actual current time', 403)
        self.management._policy_resources(connection, policy)
        return record

    def _current(self, connection, ref, owner):
        record = self._record(connection, ref, owner)
        if not record.current or record.revoked:
            raise EngineError('local_copy_scope_inactive', 'Exact selected scope was replaced or revoked', 403)
        self._policy(connection, record.scope, require_scope_active=True)
        return record

    @contextmanager
    def current_guard(self):
        active = [guard for guard in self._guards if guard.thread_id == threading.get_ident()]
        if active:
            yield active[-1]  # Same retained lock is already held by this exact thread.
            return
        with self.control.locked():
            if self.control.path.exists():
                document = self.control.read()
                if document.pending_request_sha256:
                    raise EngineError('local_copy_restore_refresh_required', 'Actual copy management reservation is not completed', 503)
                minimum = document.minimum_revision
            else:
                with self.engine.db.connect() as connection:
                    if self._revision(connection) or connection.execute('SELECT 1 FROM local_copy_input_scopes LIMIT 1').fetchone():
                        raise EngineError('local_copy_restore_refresh_required', 'Existing copy registry needs its original retained floor', 503)
                minimum = 0  # No scope permission exists; never initializes control here.
            guard = _CopyGuard(minimum, threading.get_ident(), self)
            self._guards.add(guard)
            try:
                yield guard
            finally:
                self._guards.remove(guard)

    def _guard(self, connection):
        active = [guard for guard in self._guards if guard.issuer is self and guard.thread_id == threading.get_ident()]
        if not active:
            raise EngineError('local_copy_guard_required', 'Current same-thread retained copy control guard is required', 403)
        revision = self._revision(connection)
        if revision < max(guard.minimum_revision for guard in active):
            raise EngineError('local_copy_restore_refresh_required', 'Copy registry was restored behind its retained floor', 503)
        return revision

    def preview(self, capability, proposal):
        principal = self.management._principal(capability, (proposal.destination_project_id,))
        resolved = self.resolver.resolve_for_management(capability, proposal)
        result = LocalCopyInputScope(scope_id=proposal.scope_id, revision=proposal.revision,
            instance_id=self.engine.instance_id, owner_subject=principal.owner_subject,
            destination_project_id=proposal.destination_project_id, executing_principal_ids=proposal.executing_principal_ids,
            registration_sha256=proposal.registration_sha256, policy_ref=proposal.policy_ref,
            valid_from_us=proposal.valid_from_us, expires_at_us=proposal.expires_at_us,
            source_set=resolved.source_set, source_set_sha256=canonical_sha256(resolved.source_set))
        with self.management.control.locked(), self.engine.db.connect() as connection:
            self.management.control.assert_revision(self.management._revision(connection))
            self.management._principal(capability, (result.destination_project_id,))
            self._policy(connection, result)
        return result

    def _action(self, capability, key, action, command, project_id, prepare):
        if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}', key):
            raise EngineError('local_copy_command_invalid', 'Management requires a bounded explicit idempotency identity', 422)
        principal = self.management._principal(capability, (project_id,))
        body = json.dumps({'owner_subject': principal.owner_subject, 'scope': COMMAND_PREFIX + action,
            'idempotency_key': key, 'command': command.model_dump(mode='json')}, ensure_ascii=False,
            sort_keys=True, separators=(',', ':'), allow_nan=False)
        request_sha = digest(body)
        # Keep the established production-then-copy lock order. All file reads
        # and durable floor reserve/complete happen outside the short writer.
        with self.management.control.locked(), self.control.locked():
            with self.engine.db.connect() as connection:
                self.management.control.assert_revision(self.management._revision(connection))
                existing = connection.execute('SELECT * FROM commands WHERE owner=? AND scope=? AND idempotency_key=?',
                    (principal.owner_subject, COMMAND_PREFIX + action, key)).fetchone()
                revision = self._revision(connection)
                if existing:
                    if existing['request_sha256'] != request_sha:
                        raise EngineError('idempotency_conflict', 'Copy management key was used for another command', 409)
                    receipt = self._model(LocalCopyInputActionReceipt, existing['result_json'])
                    self._action_fact(connection, receipt, principal.owner_subject)
                    document = self.control.read()
                    if (document.minimum_revision, document.pending_request_sha256) == (receipt.registry_revision, request_sha):
                        self.control.complete(receipt.registry_revision, request_sha)
                    self.control.assert_revision(revision)
                    return receipt
                if not self.control.path.exists():
                    if revision or connection.execute('SELECT 1 FROM local_copy_input_scopes LIMIT 1').fetchone():
                        raise EngineError('local_copy_restore_refresh_required', 'Existing scopes require their original retained control', 503)
                    self.control.initialize_new()
                ref, mutation = prepare(connection)
                production_floor = self.management._revision(connection)
            next_revision = self.control.reserve(revision, request_sha)
            receipt = LocalCopyInputActionReceipt(action_id=identity('local-copy-action'), instance_id=self.engine.instance_id,
                administrator_id=principal.administrator_id, authentication_binding_id=principal.authentication_binding_id,
                authentication_source=principal.authentication_source, owner_subject=principal.owner_subject,
                destination_project_id=project_id, action=action, scope_ref=ref, idempotency_key=key,
                request_sha256=request_sha, authorized_at_us=self.engine.clock(), registry_revision=next_revision,
                reason=command.reason if action == 'revoke' else None, target=command if action == 'bind_request' else None)
            with self.engine.db.transaction() as connection:
                self.management._principal(capability, (project_id,))
                self.management._project_scope(connection, principal.owner_subject, (project_id,))
                if self._revision(connection) != revision or self.management._revision(connection) != production_floor:
                    raise EngineError('local_copy_registry_conflict', 'Copy or production registry changed before the exact Owner commit', 409)
                mutation(connection, receipt)
                connection.execute('UPDATE metadata SET value=? WHERE key=?', (str(next_revision), REGISTRY_KEY))
                connection.execute('INSERT INTO commands VALUES(?,?,?,?,?)',
                    (principal.owner_subject, COMMAND_PREFIX + action, key, request_sha, canonical(receipt)))
            self.control.complete(next_revision, request_sha)
            return receipt

    def install_scope(self, capability, idempotency_key, command):
        scope = command.scope
        principal = self.management._principal(capability, (scope.destination_project_id,))
        if scope.owner_subject != principal.owner_subject or scope.instance_id != self.engine.instance_id:
            raise EngineError('local_copy_scope_denied', 'Authenticated actual Owner must endorse this local scope', 403)
        action = 'replace' if command.previous_ref else 'create'

        def prepare(connection):
            self._policy(connection, scope)
            if scope.expires_at_us <= self.engine.clock():
                raise EngineError('local_copy_scope_inactive', 'Expired scope cannot be installed', 403)
            latest = connection.execute('SELECT revision FROM local_copy_input_scopes WHERE scope_id=? ORDER BY revision DESC LIMIT 1', (scope.scope_id,)).fetchone()
            if scope.revision != (latest[0] + 1 if latest else 1) or (action == 'create') != (latest is None):
                raise EngineError('local_copy_scope_conflict', 'Scope requires its exact next explicit revision', 409)
            if command.previous_ref is not None and not self._record(connection, command.previous_ref, principal.owner_subject).current:
                raise EngineError('local_copy_scope_conflict', 'Replacement requires the exact current scope', 409)
            resolved = self.resolver.resolve_for_management(capability, scope)
            if resolved.source_set != scope.source_set:
                raise EngineError('local_copy_source_conflict', 'Confirmed full source/handling/edge set differs from actual preview', 409)
            self.resolver.recheck_files(resolved)
            ref = LocalCopyInputScopeRef(scope_id=scope.scope_id, revision=scope.revision, content_sha256=canonical_sha256(scope))

            def mutate(writer, receipt):
                self._policy(writer, scope)
                if scope.expires_at_us <= self.engine.clock():
                    raise EngineError('local_copy_scope_inactive', 'Scope expired before the actual Owner commit', 403)
                current = writer.execute('SELECT revision FROM local_copy_input_scopes WHERE scope_id=? ORDER BY revision DESC LIMIT 1', (scope.scope_id,)).fetchone()
                if scope.revision != (current[0] + 1 if current else 1):
                    raise EngineError('local_copy_scope_conflict', 'Scope version changed before Owner commit', 409)
                self.resolver.assert_sources_current(writer, resolved, owner_subject=scope.owner_subject,
                    project_id=scope.destination_project_id, checked_at_us=self.engine.clock())
                writer.execute('UPDATE local_copy_input_scopes SET current=0 WHERE scope_id=?', (scope.scope_id,))
                writer.execute('INSERT INTO local_copy_input_scopes (scope_id,revision,owner,project_id,policy_id,policy_revision,body,content_sha256,installation_action_json,installation_action_sha256,current,registry_revision,installed_at_us) VALUES(?,?,?,?,?,?,?,?,?,?,1,?,?)',
                    (scope.scope_id, scope.revision, scope.owner_subject, scope.destination_project_id, scope.policy_ref.policy_id,
                    scope.policy_ref.revision, canonical(scope), ref.content_sha256, canonical(receipt), digest(canonical(receipt)),
                    receipt.registry_revision, receipt.authorized_at_us))
            return ref, mutate
        return self._action(capability, idempotency_key, action, command, scope.destination_project_id, prepare)

    @staticmethod
    def _default_key(owner, project_id, principal, registration_sha, policy_ref):
        return DEFAULT_PREFIX + digest(json.dumps({'owner': owner, 'project_id': project_id, 'principal': principal,
            'registration_sha256': registration_sha, 'policy_ref': policy_ref.model_dump(mode='json')}, sort_keys=True, separators=(',', ':')))

    def select_scope(self, capability, idempotency_key, command):
        principal = self.management._principal(capability, (command.destination_project_id,))

        def prepare(connection):
            def check(current):
                scope = self._current(current, command.scope_ref, principal.owner_subject).scope
                if ((scope.destination_project_id, scope.registration_sha256, scope.policy_ref) != (
                        command.destination_project_id, command.registration_sha256, command.policy_ref)
                        or command.executing_principal_id not in scope.executing_principal_ids):
                    raise EngineError('local_copy_scope_denied', 'Selection differs from exact project/principal/registration/policy scope', 403)
            check(connection)

            def mutate(writer, receipt):
                check(writer)
                key = self._default_key(principal.owner_subject, command.destination_project_id,
                    command.executing_principal_id, command.registration_sha256, command.policy_ref)
                value = json.dumps({'selection': command.model_dump(mode='json'), 'action': receipt.model_dump(mode='json')},
                    ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
                writer.execute('INSERT INTO metadata VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key, value))
            return command.scope_ref, mutate
        return self._action(capability, idempotency_key, 'select', command, command.destination_project_id, prepare)

    def revoke_scope(self, capability, idempotency_key, command):
        principal = self.management._principal(capability, ())
        with self.engine.db.connect() as connection:
            initial = self._record(connection, command.scope_ref, principal.owner_subject)

        def prepare(connection):
            if self._record(connection, command.scope_ref, principal.owner_subject).revoked:
                raise EngineError('local_copy_scope_conflict', 'Original scope revocation cannot be overwritten', 409)

            def mutate(writer, receipt):
                if self._record(writer, command.scope_ref, principal.owner_subject).revoked:
                    raise EngineError('local_copy_scope_conflict', 'Scope was already revoked by another action', 409)
                writer.execute('UPDATE local_copy_input_scopes SET revoked=1,revocation_action_json=?,revocation_action_sha256=? WHERE scope_id=? AND revision=?',
                    (canonical(receipt), digest(canonical(receipt)), command.scope_ref.scope_id, command.scope_ref.revision))
            return command.scope_ref, mutate
        return self._action(capability, idempotency_key, 'revoke', command, initial.scope.destination_project_id, prepare)

    def get_scope(self, capability, ref):
        principal = self.management._principal(capability, ())
        with self.current_guard(), self.engine.db.connect() as connection:
            self._guard(connection)
            record = self._record(connection, ref, principal.owner_subject)
            self.management._principal(capability, (record.scope.destination_project_id,))
            return record

    def _binding(self, connection, row):
        value = self._model(LocalCopyInputBinding, row['body'])
        action = self._model(LocalCopyInputActionReceipt, row['selection_action_json'])
        if (type(row['current']) is not int or row['current'] not in (0, 1)
                or digest(row['body']) != row['content_sha256'] or digest(row['selection_action_json']) != row['selection_action_sha256']
                or value.selection_action_ref != LocalCopyInputActionRef(action_id=action.action_id, content_sha256=digest(canonical(action)))
                or (action.instance_id, action.owner_subject, action.destination_project_id) != (
                    value.instance_id, value.owner_subject, value.destination_project_id)
                or action.scope_ref != value.scope_ref or action.action not in {'select', 'bind_request'}
                or (row['id'], row['production_id'], row['run_id'], row['request_revision_id'], row['request_sha256'], row['owner'],
                    row['project_id'], row['executing_principal_id'], row['registration_sha256'], row['scope_id'], row['scope_revision'],
                    row['policy_id'], row['policy_revision'], row['source_set_sha256'], row['bound_at_us'], row['registry_revision']) != (
                    value.binding_id, value.production_id, value.run_id, value.request_revision_id, value.request_sha256, value.owner_subject,
                    value.destination_project_id, value.executing_principal_id, value.registration_sha256, value.scope_ref.scope_id,
                    value.scope_ref.revision, value.policy_ref.policy_id, value.policy_ref.revision, value.source_set_sha256,
                    value.bound_at_us, value.registry_revision)):
            raise EngineError('local_copy_binding_invalid', 'Original copy binding columns and exact action/body disagree', 422)
        self._action_fact(connection, action, value.owner_subject)
        if action.target is not None and (action.target.production_id, action.target.run_id, action.target.request_revision_id,
                action.target.request_sha256) != (value.production_id, value.run_id, value.request_revision_id, value.request_sha256):
            raise EngineError('local_copy_binding_invalid', 'Actual supplemental Owner action targets a different request', 422)
        return value

    def _persist_binding(self, connection, production, run, registered, record, action, revision):
        scope = record.scope
        value = LocalCopyInputBinding(binding_id=identity('local-copy-binding'), instance_id=self.engine.instance_id,
            owner_subject=production['owner'], destination_project_id=production['project_id'], production_id=production['id'],
            run_id=run['id'], request_revision_id=production['request_revision_id'], request_sha256=production['request_sha256'],
            executing_principal_id=registered.executing_principal_id, registration_sha256=registered.registration_sha256,
            policy_ref=scope.policy_ref, scope_ref=record.scope_ref,
            selection_action_ref=LocalCopyInputActionRef(action_id=action.action_id, content_sha256=digest(canonical(action))),
            source_set_sha256=scope.source_set_sha256, bound_at_us=self.engine.clock(), registry_revision=revision)
        connection.execute('UPDATE local_copy_input_bindings SET current=0 WHERE production_id=? AND run_id=? AND executing_principal_id=? AND registration_sha256=?',
            (production['id'], run['id'], registered.executing_principal_id, registered.registration_sha256))
        connection.execute('INSERT INTO local_copy_input_bindings (id,production_id,run_id,request_revision_id,request_sha256,owner,project_id,executing_principal_id,registration_sha256,scope_id,scope_revision,policy_id,policy_revision,source_set_sha256,selection_action_json,selection_action_sha256,body,content_sha256,current,bound_at_us,registry_revision) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?,?)',
            (value.binding_id, value.production_id, value.run_id, value.request_revision_id, value.request_sha256, value.owner_subject,
            value.destination_project_id, value.executing_principal_id, value.registration_sha256, value.scope_ref.scope_id,
            value.scope_ref.revision, value.policy_ref.policy_id, value.policy_ref.revision, value.source_set_sha256,
            canonical(action), digest(canonical(action)), canonical(value), digest(canonical(value)), value.bound_at_us, revision))
        return value

    def bind_default_request(self, connection, *, production, run, registered, policy_ref):
        from video_creator.domain.local_copy_input_scope import (
            SelectLocalCopyInputScope,
        )
        revision = self._guard(connection)
        existing = connection.execute('SELECT * FROM local_copy_input_bindings WHERE production_id=? AND run_id=? AND current=1',
            (production['id'], run['id'])).fetchall()
        if existing:
            if len(existing) != 1:
                raise EngineError('local_copy_binding_invalid', 'Original request has conflicting current input bindings', 422)
            return self._binding(connection, existing[0])  # Never silently upgrade an original binding.
        row = connection.execute('SELECT value FROM metadata WHERE key=?', (self._default_key(production['owner'],
            production['project_id'], registered.executing_principal_id, registered.registration_sha256, policy_ref),)).fetchone()
        if not row:
            return None
        raw = DeliveryResolver._json(row[0])
        if not isinstance(raw, dict) or set(raw) != {'selection', 'action'}:
            raise EngineError('local_copy_selection_invalid', 'Actual default selection is damaged', 422)
        try:
            selection = SelectLocalCopyInputScope.model_validate(raw['selection'])
            action = LocalCopyInputActionReceipt.model_validate(raw['action'])
        except (ValueError, TypeError):
            raise EngineError('local_copy_selection_invalid', 'Stored selection/action grammar is damaged', 422) from None
        self._action_fact(connection, action, production['owner'])
        record = self._current(connection, selection.scope_ref, production['owner'])
        if (action.action != 'select' or action.scope_ref != selection.scope_ref
                or (action.instance_id, action.owner_subject, action.destination_project_id) != (
                    self.engine.instance_id, production['owner'], production['project_id'])
                or (selection.destination_project_id, selection.executing_principal_id, selection.registration_sha256, selection.policy_ref) != (
                    production['project_id'], registered.executing_principal_id, registered.registration_sha256, policy_ref)
                or record.scope.policy_ref != policy_ref or registered.executing_principal_id not in record.scope.executing_principal_ids):
            raise EngineError('local_copy_selection_invalid', 'Default differs from actual original request/policy/registration selection', 422)
        return self._persist_binding(connection, production, run, registered, record, action, revision)

    def bind_existing(self, capability, idempotency_key, command: BindLocalCopyInputScope):
        principal = self.management._principal(capability, ())
        with self.engine.db.connect() as connection:
            original = self.engine._production(connection, command.production_id, principal.owner_subject)
        project_id = original['project_id']

        def target(connection):
            from video_creator.application.production_reauthorization import read_wait
            production = self.engine._production(connection, command.production_id, principal.owner_subject)
            run = self.engine._run(connection, command.run_id)
            latest = connection.execute('SELECT id FROM runs WHERE production_id=? ORDER BY rowid DESC LIMIT 1', (production['id'],)).fetchone()
            if (not latest or latest[0] != command.run_id or run['production_id'] != production['id']
                    or (production['request_revision_id'], production['request_sha256']) != (command.request_revision_id, command.request_sha256)
                    or digest(production['request_json']) != command.request_sha256):
                raise EngineError('local_copy_binding_conflict', 'Supplemental action must target the exact original request/latest same Run', 409)
            if run['status'] not in {'queued', 'waiting_authorization', 'needs_reconciliation'} or run['cancellation_requested']:
                raise EngineError('local_copy_binding_conflict', 'Only the original nonterminal unowned queued/authorization-wait Run can be bound', 409)
            if run['worker_id'] is not None or run['lease_until_us'] > self.engine.clock():
                raise EngineError('local_copy_binding_active_lease', 'Release ordinary/reconciliation ownership before Owner binding', 409)
            registered = self.engine._authorization_identity(production['owner'])
            issuer = self.engine.production_admissions
            issuer._identity(registered)
            policy_fact = issuer._current_binding(connection, production, run)
            record = self._current(connection, command.scope_ref, principal.owner_subject)
            scope = record.scope
            if ((scope.policy_ref, scope.destination_project_id, scope.registration_sha256) != (
                    policy_fact.policy_ref, production['project_id'], registered.registration_sha256)
                    or registered.executing_principal_id not in scope.executing_principal_ids
                    or (policy_fact.request_revision_id, policy_fact.request_sha256) != (command.request_revision_id, command.request_sha256)):
                raise EngineError('local_copy_scope_denied', 'Supplemental scope differs from current original local policy/request/principal', 403)
            return production, run, registered, record, read_wait(self.engine, connection, production, run)

        def prepare(connection):
            target(connection)

            def mutate(writer, receipt):
                from video_creator.application.production_reauthorization import (
                    WAIT_PREFIX,
                    unresolved_operations,
                )
                production, run, registered, record, wait = target(writer)
                self._persist_binding(writer, production, run, registered, record, receipt, receipt.registry_revision)
                if wait is not None and wait.blocker_code in {'production_copy_source_scope_missing', 'local_copy_scope_inactive',
                        'local_copy_policy_conflict', 'local_copy_source_scope_denied'}:
                    writer.execute('DELETE FROM metadata WHERE key=?', (WAIT_PREFIX + run['id'],))
                    status = 'needs_reconciliation' if unresolved_operations(writer, run['id']) else 'queued'
                    writer.execute('UPDATE runs SET status=? WHERE id=?', (status, run['id']))
                    writer.execute('UPDATE productions SET status=? WHERE id=?', (status, production['id']))
                    self.engine._event(writer, self.engine._run(writer, run['id']), 'production.copy_input_authorized', production['request_revision_id'])
            return command.scope_ref, mutate
        return self._action(capability, idempotency_key, 'bind_request', command, project_id, prepare)

    def resolve_requested(self, lease, roots):
        return self.resolver.resolve_for_execution(lease, roots)

    def assert_current_copy_scope(self, connection, authorization_guard, lease, production, requested):
        revision = self._guard(connection)
        run = self.engine._lease(connection, lease)
        issuer = self.engine.production_admissions
        _request, policy_record = issuer._bound(connection, authorization_guard, production, run, action='execute_plan')
        registered, _production_revision = issuer._guard(connection, authorization_guard)
        rows = connection.execute('SELECT * FROM local_copy_input_bindings WHERE production_id=? AND run_id=? AND current=1',
            (production['id'], run['id'])).fetchall()
        if len(rows) != 1:
            raise EngineError('production_copy_source_scope_missing', 'Original request needs an actual Owner selected input scope binding', 403)
        binding = self._binding(connection, rows[0])
        record = self._current(connection, binding.scope_ref, production['owner'])
        scope = record.scope
        if ((binding.instance_id, binding.owner_subject, binding.destination_project_id, binding.production_id, binding.run_id,
                binding.request_revision_id, binding.request_sha256, binding.executing_principal_id, binding.registration_sha256,
                binding.policy_ref, binding.source_set_sha256) != (self.engine.instance_id, production['owner'], production['project_id'],
                production['id'], run['id'], production['request_revision_id'], production['request_sha256'], registered.executing_principal_id,
                registered.registration_sha256, policy_record.policy_ref, scope.source_set_sha256)
                or scope.policy_ref != policy_record.policy_ref or registered.executing_principal_id not in scope.executing_principal_ids):
            raise EngineError('local_copy_binding_conflict', 'Selected input binding differs from the actual current policy/request/principal', 409)
        self.resolver.assert_sources_current(connection, requested, owner_subject=production['owner'],
            project_id=production['project_id'], checked_at_us=self.engine.clock())
        allowed = {member_key(item): item for item in scope.source_set.items}
        for item in requested.source_set.items:
            original = allowed.get(member_key(item))
            if original is None:
                raise EngineError('local_copy_source_scope_denied', 'Confirmed input scope omits an actual required ancestor/license/proof', 403)
            before, actual = original.model_dump(mode='json'), item.model_dump(mode='json')
            for key in ('handling', 'required_uses'):
                before.pop(key)
                actual.pop(key)
            if (before != actual or item.handling == 'copy_into_delivery' and original.handling != 'copy_into_delivery'
                    or not set(item.required_uses) <= set(original.required_uses)):
                raise EngineError('local_copy_source_scope_denied', 'Scope does not cover exact source full identity/handling/all requested uses', 403)
        edge_keys = {(member_key(edge.source), member_key(edge.target), edge.kind) for edge in scope.source_set.edges}
        if any((member_key(edge.source), member_key(edge.target), edge.kind) not in edge_keys for edge in requested.source_set.edges):
            raise EngineError('local_copy_source_scope_denied', 'Scope omits a complete actual requested dependency edge', 403)
        now = self.engine.clock()
        expiry = min(scope.expires_at_us, policy_record.policy.expires_at_us, registered.expires_at_us,
                     lease.expires_at_us, requested.valid_until_us)
        if expiry <= now:
            raise EngineError('local_copy_scope_inactive', 'Actual scope/source/policy/lease is no longer current', 403)
        return CopyInputAdmission(binding.binding_id, self.engine.instance_id, production['owner'], production['project_id'],
            production['id'], run['id'], production['request_revision_id'], production['request_sha256'],
            registered.executing_principal_id, registered.registration_sha256, policy_record.policy_ref, binding.scope_ref,
            binding.selection_action_ref, requested.source_set, canonical_sha256(requested.source_set), revision,
            lease.fencing_token, now, expiry)
