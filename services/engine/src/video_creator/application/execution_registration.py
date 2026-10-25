"""Original-store native registration reads and current guards; no grant creation."""

import json
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field, replace

from video_creator.application.engine import canonical, digest, identity
from video_creator.application.native_execution_installation import (
    RetainedNativeInstallation,
)
from video_creator.application.owner_bootstrap import KEY as OWNER_KEY
from video_creator.application.production_authorization import (
    ProductionAuthorizationService,
)
from video_creator.domain.errors import EngineError
from video_creator.domain.native_execution_registration import (
    ExecutionRegistrationActionReceipt,
    ExecutionRegistrationRef,
    InstalledExecutionRegistrationBody,
    InstalledNativeRecordBody,
    InstalledNativeRecordRef,
    NativeInstallationInputs,
    private_body_sha256,
)
from video_creator.infrastructure.held_authority import FRAME_LIMIT, NativeLaunchContext


@dataclass(frozen=True, repr=False)
class PersistedExecutionRegistration:
    registration_ref: ExecutionRegistrationRef
    registration: InstalledExecutionRegistrationBody
    installed_record_ref: InstalledNativeRecordRef
    installed_record: InstalledNativeRecordBody
    installation_action: ExecutionRegistrationActionReceipt
    selection_action: ExecutionRegistrationActionReceipt | None
    revocation_action: ExecutionRegistrationActionReceipt | None
    current: bool
    revoked: bool


@dataclass(frozen=True, eq=False, repr=False)
class CurrentExecutionRegistration:
    """One original store's strong object and immutable facts; not a ticket."""
    record: PersistedExecutionRegistration
    owner_body: str = field(repr=False)
    registration_row: tuple = field(repr=False)
    installed_row: tuple = field(repr=False)
    command_rows: tuple = field(repr=False)
    minimum_registry_revision: int
    _store: object = field(repr=False)


@dataclass(frozen=True, eq=False, repr=False)
class ExecutionRegistrationGuard:
    current: CurrentExecutionRegistration
    minimum_registry_revision: int
    thread_id: int
    _store: object = field(repr=False)


class ExecutionRegistrationStore:
    """Read original canonical facts, never install from startup JSON or SHA.

    Owner actions will use the same authorization service/Control, not another
    registry floor. Installation observations are separate from resource
    qualification and are supplied only by trusted installation assembly.
    """
    def __init__(self, engine, *, bootstrap, authorization):
        if (bootstrap.engine is not engine or authorization.engine is not engine
                or authorization.control is None
                or authorization.control.instance_id != engine.instance_id):
            raise EngineError('execution_registration_configuration_conflict',
                              'Native registration requires the original same-instance Owner and authorization store', 503)
        self.engine, self.bootstrap, self.authorization = engine, bootstrap, authorization
        self.control = authorization.control
        self._lock = threading.RLock()
        self._currents, self._guards = set(), set()
        self._fact_epoch, self._goal_facts, self._fact_daily = object(), {}, None

    def accepted_goal_facts(self, root):
        from video_creator.application.accepted_goal_facts import accepted_goal_facts

        return accepted_goal_facts(self, root)

    def assert_goal_fact_writer(self, connection, context):
        from video_creator.application.accepted_goal_facts import (
            assert_goal_fact_writer,
        )

        return assert_goal_fact_writer(self, connection, context)

    @staticmethod
    def _projects(command):
        projects = tuple(dict.fromkeys(project for item in command.registrations for project in item.project_ids))
        if not 1 <= len(projects) <= 256:
            raise EngineError('execution_registration_scope_invalid', 'An installation action has one finite explicit Owner project scope', 422)
        return projects

    def _observed(self, observer, observation, installation, owner_binding):
        if observer is None:
            raise EngineError('native_installation_observer_unconfigured', 'Actual retained independent host and complete payload observer is required', 503)
        if (not isinstance(observation, RetainedNativeInstallation) or observation._issuer is not observer
                or observation._held_owner is None or observation.installation != installation
                or type(observation.observed_at_us) is not int or not 0 < observation.observed_at_us <= self.engine.clock()
                or (observation.instance_id, observation.owner_subject, observation.owner_binding_generation,
                    observation.owner_binding_action_id, observation.authentication_binding_id, observation.os_subject,
                    observation.directory_device, observation.directory_inode) != (
                    self.engine.instance_id, owner_binding.principal.owner_subject, owner_binding.generation,
                    owner_binding.action_id, owner_binding.principal.authentication_binding_id, owner_binding.os_subject,
                    owner_binding.directory_device, owner_binding.directory_inode)):
            raise EngineError('native_installation_observation_invalid', 'Actual original retained installation observation differs from this confirmed Owner action', 403)

    def _action(self, capability, key, action, command, projects, prepare, *, observer=None, observation=None):
        from video_creator.domain import contracts as c

        c.SourceBinding(system=key, namespace='owner-execution-command')
        principal = self.authorization._principal(capability, projects)
        scope = 'owner.execution.' + action
        proposal = {'owner_subject': principal.owner_subject, 'scope': scope, 'idempotency_key': key,
                    'action': action, 'command': command.model_dump(mode='json')}
        c.reject_secrets(proposal)
        request_sha = digest(json.dumps(proposal, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False))
        # Installation hash/RPC has already completed before either Control
        # lock. The writer below only checks that same original local epoch.
        with self.authorization.management.action_guard(capability, projects, principal.owner_subject), self.control.locked():
            with self.engine.db.connect() as connection:
                self.authorization._project_scope(connection, principal.owner_subject, projects)
                owner_binding = self.bootstrap._read(connection)
                if owner_binding is None or owner_binding.principal != principal:
                    raise EngineError('execution_registration_owner_denied', 'This action requires the actual current installed Owner binding', 403)
                revision = self.authorization._revision(connection)
                existing = connection.execute('SELECT request_sha256,result_json FROM commands WHERE owner=? AND scope=? AND idempotency_key=?',
                    (principal.owner_subject, scope, key)).fetchone()
                if existing:
                    if existing['request_sha256'] != request_sha:
                        raise EngineError('idempotency_conflict', 'Native Owner action key was used for another exact proposal', 409)
                    original = self._model(ExecutionRegistrationActionReceipt, existing['result_json'])
                    if (original.action, original.owner_subject, original.instance_id, original.idempotency_key, original.request_sha256) != (
                            action, principal.owner_subject, self.engine.instance_id, key, request_sha):
                        raise EngineError('execution_registration_action_invalid', 'Original action command result changed', 422)
                    for ref in original.execution_refs:
                        self._record(connection, ref, principal.owner_subject, revision, [])
                    floor = self.control.read()
                    if (floor.minimum_revision, floor.pending_request_sha256) == (original.registry_revision, request_sha):
                        self.control.complete(original.registry_revision, request_sha)
                    self.control.assert_revision(revision)
                    return original
                if not self.control.path.exists():
                    populated = any(connection.execute('SELECT 1 FROM ' + table + ' LIMIT 1').fetchone()
                                    for table in ('production_authorization_policies', 'installed_native_records', 'execution_registrations'))
                    if revision or populated:
                        raise EngineError('production_restore_refresh_required', 'Existing installation facts require their original retained authorization floor', 503)
                    self.control.initialize_new()
                if observation is not None:
                    self._observed(observer, observation, observation.installation, owner_binding)
                installed_ref, execution_refs, mutation = prepare(connection, owner_binding)
                # Validate all receipt fields before reserving the external floor.
                receipt = ExecutionRegistrationActionReceipt(action_id=identity('execution-action'), instance_id=self.engine.instance_id,
                    administrator_id=principal.administrator_id, owner_subject=principal.owner_subject,
                    authentication_binding_id=principal.authentication_binding_id, authentication_source=principal.authentication_source,
                    owner_binding_generation=owner_binding.generation, owner_binding_action_id=owner_binding.action_id,
                    project_ids=projects, action=action, installed_record_ref=installed_ref, execution_refs=execution_refs,
                    idempotency_key=key, request_sha256=request_sha, authorized_at_us=self.engine.clock(),
                    registry_revision=revision + 1, reason=command.reason if action == 'revoke' else None)
            if self.control.reserve(revision, request_sha) != receipt.registry_revision:
                raise EngineError('production_control_conflict', 'Native action reservation differs from its original registry revision', 409)
            owner_body = canonical(owner_binding)
            receipt_body = canonical(receipt)
            receipt_sha = digest(receipt_body)
            with self.authorization._management_transaction(capability, projects) as connection:
                self.authorization._principal(capability, projects)
                if self.authorization._revision(connection) != revision:
                    raise EngineError('production_registry_conflict', 'Native registration registry changed before commit', 409)
                # Original Owner service checks current OS/directory before and
                # before commit. Exact bound DB body is additionally unchanged.
                row = connection.execute('SELECT value FROM metadata WHERE key=?', (OWNER_KEY,)).fetchone()
                if row is None or row[0] != owner_body:
                    raise EngineError('execution_registration_owner_denied', 'Actual Owner binding changed before its exact action commit', 403)
                self.authorization._project_scope(connection, principal.owner_subject, projects)
                if observation is not None:
                    observer.assert_local_current(observation)
                mutation(connection, receipt, receipt_body, receipt_sha)
                connection.execute("UPDATE metadata SET value=? WHERE key='production_authorization_registry_revision'", (str(receipt.registry_revision),))
                connection.execute('INSERT INTO commands VALUES(?,?,?,?,?)', (principal.owner_subject, scope, key, request_sha, receipt_body))
                self.authorization._principal(capability, projects)
                if observation is not None:
                    observer.assert_local_current(observation)
            self.control.complete(receipt.registry_revision, request_sha)
            return receipt

    def install(self, capability, key, command, *, observer, observation):
        projects = self._projects(command)
        principal = self.authorization._principal(capability, projects)
        with self.bootstrap.current() as owner_binding:
            self._observed(observer, observation, command.installation, owner_binding)
        observer.assert_current(observation)
        action = 'replace' if command.previous_installed_ref or any(item.previous_ref for item in command.registrations) else 'install'

        def prepare(connection, owner):
            revision = self.authorization._revision(connection)
            latest = connection.execute('SELECT owner,MAX(revision) AS revision FROM installed_native_records WHERE record_id=? GROUP BY owner',
                (command.record_id,)).fetchall()
            if latest and (len(latest) != 1 or latest[0]['owner'] != principal.owner_subject):
                raise EngineError('installed_native_record_owner_denied', 'Installed identity belongs to a different original Owner', 403)
            old_revision = latest[0]['revision'] if latest else 0
            previous_installed_row = None
            if latest and command.previous_installed_ref is None:
                raise EngineError('installed_native_record_conflict', 'Existing installed identity requires explicit current-ref replacement', 409)
            if command.previous_installed_ref:
                old, old_row = self._installed(connection, command.previous_installed_ref, principal.owner_subject, revision, [])
                if (old.record_id != command.record_id or old.revision != old_revision or not old_row['current'] or old_row['revoked']):
                    raise EngineError('installed_native_record_conflict', 'Replacement must name the exact latest current installation', 409)
                previous_installed_row = tuple(dict(old_row).items())
            same_root = connection.execute('SELECT record_id,revision FROM installed_native_records WHERE instance_id=? AND owner=? AND composition_root=? AND current=1',
                (self.engine.instance_id, principal.owner_subject, command.installation.composition_root)).fetchone()
            if same_root and (not command.previous_installed_ref or tuple(same_root) != (
                    command.previous_installed_ref.record_id, command.previous_installed_ref.revision)):
                raise EngineError('installed_native_record_conflict', 'Composition root already has a different explicitly current installation', 409)
            installed = InstalledNativeRecordBody(**command.installation.model_dump(), record_id=command.record_id,
                revision=old_revision + 1, instance_id=self.engine.instance_id, owner_subject=principal.owner_subject,
                os_subject=owner.os_subject, directory_device=owner.directory_device, directory_inode=owner.directory_inode,
                owner_binding_generation=owner.generation, owner_binding_action_id=owner.action_id,
                authentication_binding_id=principal.authentication_binding_id)
            installed_body = canonical(installed)
            installed_ref = InstalledNativeRecordRef(record_id=installed.record_id, revision=installed.revision,
                                                     content_sha256=digest(installed_body))
            entries = []
            for item in command.registrations:
                previous_registration_row = None
                if not self.engine.clock() < item.expires_at_us <= principal.expires_at_us:
                    raise EngineError('execution_registration_expired', 'Role expiry must be explicitly future and within the actual management binding', 403)
                self.authorization._project_scope(connection, principal.owner_subject, item.project_ids)
                current = connection.execute('SELECT registration_id,revision,content_sha256 FROM execution_registrations WHERE instance_id=? AND owner=? AND role=? AND current=1',
                    (self.engine.instance_id, principal.owner_subject, item.role)).fetchone()
                latest_registration = connection.execute('SELECT owner,MAX(revision) AS revision FROM execution_registrations WHERE registration_id=? GROUP BY owner',
                    (item.registration_id,)).fetchall()
                if latest_registration and (len(latest_registration) != 1 or latest_registration[0]['owner'] != principal.owner_subject):
                    raise EngineError('execution_registration_owner_denied', 'Registration identity belongs to another actual Owner', 403)
                if current and (not item.previous_ref or tuple(current) != (item.previous_ref.registration_id,
                        item.previous_ref.revision, item.previous_ref.content_sha256)):
                    raise EngineError('execution_registration_current_conflict', 'Role replacement requires its exact current original registration', 409)
                if item.previous_ref:
                    previous, previous_row, _i = self._record(connection, item.previous_ref, principal.owner_subject, revision, [])
                    if not previous.current or previous.registration.role != item.role:
                        raise EngineError('execution_registration_current_conflict', 'Replacement names a stale or different current role', 409)
                    previous_registration_row = tuple(dict(previous_row).items())
                elif latest_registration:
                    raise EngineError('execution_registration_current_conflict', 'Existing registration identity requires its original current reference', 409)
                body = InstalledExecutionRegistrationBody(registration_id=item.registration_id,
                    revision=(latest_registration[0]['revision'] if latest_registration else 0) + 1,
                    instance_id=self.engine.instance_id, owner_subject=principal.owner_subject, executing_principal_id=principal.owner_subject,
                    role=item.role, project_ids=item.project_ids, allowed_source_namespaces=item.allowed_source_namespaces,
                    registration_sha256=installed.registration_sha256, resource_manifest_sha256=installed.resource_manifest_sha256,
                    runtime_manifest_sha256=installed.runtime_manifest_sha256, installed_record_ref=installed_ref,
                    installation_inputs_sha256=private_body_sha256(command.installation), expires_at_us=item.expires_at_us,
                    owner_binding_generation=owner.generation, owner_binding_action_id=owner.action_id,
                    authentication_binding_id=principal.authentication_binding_id)
                body_text = canonical(body)
                ref = ExecutionRegistrationRef(registration_id=body.registration_id, revision=body.revision, content_sha256=digest(body_text))
                entries.append((body, ref, tuple(current) if current else None, body_text, previous_registration_row))

            def mutate(writer, receipt, action_json, action_sha):
                if command.previous_installed_ref:
                    old_row = writer.execute('SELECT * FROM installed_native_records WHERE record_id=? AND revision=?',
                        (command.previous_installed_ref.record_id, command.previous_installed_ref.revision)).fetchone()
                    if old_row is None or tuple(dict(old_row).items()) != previous_installed_row:
                        raise EngineError('installed_native_record_conflict', 'Original installation changed before its replacement', 409)
                    writer.execute('UPDATE installed_native_records SET current=0 WHERE record_id=? AND current=1', (command.record_id,))
                writer.execute('INSERT INTO installed_native_records(record_id,revision,instance_id,owner,composition_root,body,content_sha256,'
                    'installation_action_json,installation_action_sha256,current,registry_revision) VALUES(?,?,?,?,?,?,?,?,?,1,?)',
                    (installed.record_id, installed.revision, installed.instance_id, installed.owner_subject, installed.composition_root,
                     installed_body, installed_ref.content_sha256, action_json, action_sha, receipt.registry_revision))
                for body, ref, previous, body_text, previous_row in entries:
                    now_current = writer.execute('SELECT registration_id,revision,content_sha256 FROM execution_registrations WHERE instance_id=? AND owner=? AND role=? AND current=1',
                        (self.engine.instance_id, principal.owner_subject, body.role)).fetchone()
                    if (tuple(now_current) if now_current else None) != previous or body.expires_at_us <= self.engine.clock():
                        raise EngineError('execution_registration_current_conflict', 'Original current role or expiry changed before commit', 409)
                    if previous is not None:
                        actual_previous = writer.execute('SELECT * FROM execution_registrations WHERE registration_id=? AND revision=?', previous[:2]).fetchone()
                        if actual_previous is None or tuple(dict(actual_previous).items()) != previous_row:
                            raise EngineError('execution_registration_current_conflict', 'Original registration bytes changed before replacement', 409)
                    writer.execute('UPDATE execution_registrations SET current=0 WHERE instance_id=? AND owner=? AND role=? AND current=1',
                        (self.engine.instance_id, principal.owner_subject, body.role))
                    writer.execute('INSERT INTO execution_registrations(registration_id,revision,instance_id,owner,role,installed_record_id,installed_record_revision,'
                        'body,content_sha256,installation_action_json,installation_action_sha256,current,registry_revision) VALUES(?,?,?,?,?,?,?,?,?,?,?,1,?)',
                        (body.registration_id, body.revision, body.instance_id, body.owner_subject, body.role,
                         installed_ref.record_id, installed_ref.revision, body_text, ref.content_sha256,
                         action_json, action_sha, receipt.registry_revision))
            return installed_ref, tuple(item[1] for item in entries), mutate
        return self._action(capability, key, action, command, projects, prepare, observer=observer, observation=observation)

    def select(self, capability, key, command, *, observer, observation):
        principal = self.authorization._principal(capability, ())
        with self.engine.db.connect() as connection:
            initial, _r, _i = self._record(connection, command.registration_ref, principal.owner_subject, self.authorization._revision(connection), [])
        inputs = NativeInstallationInputs.model_validate({name: getattr(initial.installed_record, name) for name in NativeInstallationInputs.model_fields})
        with self.bootstrap.current() as owner:
            self._observed(observer, observation, inputs, owner)
        observer.assert_current(observation)

        def prepare(connection, owner):
            record, target_row, installed_row = self._record(connection, command.registration_ref, principal.owner_subject, self.authorization._revision(connection), [])
            self._active(connection, replace(record, current=True), installed_row, owner)
            previous = connection.execute('SELECT registration_id,revision,content_sha256 FROM execution_registrations WHERE instance_id=? AND owner=? AND role=? AND current=1',
                (self.engine.instance_id, principal.owner_subject, record.registration.role)).fetchone()

            expected_target, expected_installed = tuple(dict(target_row).items()), tuple(dict(installed_row).items())
            def mutate(writer, receipt, body, body_sha):
                target = writer.execute('SELECT * FROM execution_registrations WHERE registration_id=? AND revision=?',
                    (command.registration_ref.registration_id, command.registration_ref.revision)).fetchone()
                actual = writer.execute('SELECT registration_id,revision,content_sha256 FROM execution_registrations WHERE instance_id=? AND owner=? AND role=? AND current=1',
                    (self.engine.instance_id, principal.owner_subject, record.registration.role)).fetchone()
                installed = writer.execute('SELECT * FROM installed_native_records WHERE record_id=? AND revision=?',
                    (record.installed_record_ref.record_id, record.installed_record_ref.revision)).fetchone()
                if (target is None or tuple(dict(target).items()) != expected_target
                        or tuple(actual or ()) != tuple(previous or ()) or installed is None
                        or tuple(dict(installed).items()) != expected_installed
                        or record.registration.expires_at_us <= self.engine.clock()):
                    raise EngineError('execution_registration_current_conflict', 'Explicit selection changed before actual commit', 409)
                writer.execute('UPDATE execution_registrations SET current=0 WHERE instance_id=? AND owner=? AND role=? AND current=1',
                    (self.engine.instance_id, principal.owner_subject, record.registration.role))
                writer.execute('UPDATE execution_registrations SET current=1,selection_action_json=?,selection_action_sha256=? WHERE registration_id=? AND revision=?',
                    (body, body_sha, command.registration_ref.registration_id, command.registration_ref.revision))
            return record.installed_record_ref, (record.registration_ref,), mutate
        return self._action(capability, key, 'select', command, initial.registration.project_ids, prepare,
                            observer=observer, observation=observation)

    def revoke(self, capability, key, command):
        principal = self.authorization._principal(capability, ())
        with self.engine.db.connect() as connection:
            initial, _r, _i = self._record(connection, command.registration_ref, principal.owner_subject, self.authorization._revision(connection), [])

        def prepare(connection, _owner):
            record, target_row, _i = self._record(connection, command.registration_ref, principal.owner_subject, self.authorization._revision(connection), [])
            if record.revoked:
                raise EngineError('execution_registration_already_revoked', 'Another action cannot overwrite original revocation', 409)
            expected_target = tuple(dict(target_row).items())
            def mutate(writer, receipt, body, body_sha):
                current = writer.execute('SELECT * FROM execution_registrations WHERE registration_id=? AND revision=?',
                    (command.registration_ref.registration_id, command.registration_ref.revision)).fetchone()
                if current is None or tuple(dict(current).items()) != expected_target:
                    raise EngineError('execution_registration_current_conflict', 'Original revocation target changed before commit', 409)
                writer.execute('UPDATE execution_registrations SET revoked=1,revocation_action_json=?,revocation_action_sha256=? WHERE registration_id=? AND revision=?',
                    (body, body_sha, command.registration_ref.registration_id, command.registration_ref.revision))
            return record.installed_record_ref, (record.registration_ref,), mutate
        return self._action(capability, key, 'revoke', command, initial.registration.project_ids, prepare)

    @staticmethod
    def _model(model, body):
        try:
            if type(body) is not str or not 1 <= len(body.encode('utf-8')) <= FRAME_LIMIT:
                raise ValueError('Canonical finite TEXT required')
            value = ProductionAuthorizationService._model(model, body)
            if canonical(value) != body:
                raise ValueError('Stored native registration is not canonical')
            return value
        except (EngineError, ValueError, TypeError, UnicodeError):
            raise EngineError('execution_registration_invalid', 'Persisted native registration fact is damaged', 422) from None

    @staticmethod
    def _status(row):
        if any(type(row[key]) is not int or row[key] not in (0, 1) for key in ('current', 'revoked')):
            raise EngineError('execution_registration_invalid', 'Persisted registration status is damaged', 422)
        if (bool(row['revoked']) != bool(row['revocation_action_json'])
                or bool(row['revocation_action_json']) != bool(row['revocation_action_sha256'])):
            raise EngineError('execution_registration_invalid', 'Original revocation row and receipt disagree', 422)

    def _read_action(self, connection, row, key, owner, registry_revision, commands):
        body = row[key + '_json']
        sha = row[key + '_sha256']
        if body is None and sha is None:
            return None
        action = self._model(ExecutionRegistrationActionReceipt, body)
        if (digest(body) != sha or action.owner_subject != owner or action.instance_id != self.engine.instance_id
                or action.registry_revision > registry_revision or action.authorized_at_us > self.engine.clock()):
            raise EngineError('execution_registration_action_invalid', 'Original native Owner action identity changed', 422)
        scope = 'owner.execution.' + action.action
        original = connection.execute('SELECT request_sha256,result_json FROM commands WHERE owner=? AND scope=? AND idempotency_key=?',
            (owner, scope, action.idempotency_key)).fetchone()
        if not original or (original['request_sha256'], original['result_json']) != (action.request_sha256, body):
            raise EngineError('execution_registration_action_invalid', 'Native record requires its actual original Owner command', 422)
        commands.append((owner, scope, action.idempotency_key, action.request_sha256, body))
        return action

    def _installed(self, connection, ref, owner, registry_revision, commands):
        row = connection.execute('SELECT * FROM installed_native_records WHERE record_id=? AND revision=? AND owner=? AND instance_id=?',
            (ref.record_id, ref.revision, owner, self.engine.instance_id)).fetchone()
        if row is None:
            raise EngineError('installed_native_record_not_found', 'Original local installed record is unavailable', 404)
        self._status(row)
        record = self._model(InstalledNativeRecordBody, row['body'])
        if (digest(row['body']) != ref.content_sha256 or row['content_sha256'] != ref.content_sha256
                or (record.record_id, record.revision, record.owner_subject, record.instance_id, record.composition_root) != (
                    ref.record_id, ref.revision, owner, self.engine.instance_id, row['composition_root'])):
            raise EngineError('installed_native_record_invalid', 'Immutable original installed record changed', 422)
        action = self._read_action(connection, row, 'installation_action', owner, registry_revision, commands)
        revoked = self._read_action(connection, row, 'revocation_action', owner, registry_revision, commands)
        if (action is None or action.action not in ('install', 'replace') or action.installed_record_ref != ref
                or action.registry_revision != row['registry_revision']
                or (action.owner_binding_generation, action.owner_binding_action_id, action.authentication_binding_id) != (
                    record.owner_binding_generation, record.owner_binding_action_id, record.authentication_binding_id)
                or revoked is not None and (revoked.action != 'revoke' or revoked.installed_record_ref != ref)):
            raise EngineError('installed_native_record_invalid', 'Actual installed record and Owner actions disagree', 422)
        return record, row

    def _record(self, connection, ref, owner, registry_revision, commands):
        row = connection.execute('SELECT * FROM execution_registrations WHERE registration_id=? AND revision=? AND owner=? AND instance_id=?',
            (ref.registration_id, ref.revision, owner, self.engine.instance_id)).fetchone()
        if row is None:
            raise EngineError('execution_registration_not_found', 'Original execution registration is unavailable', 404)
        self._status(row)
        body = self._model(InstalledExecutionRegistrationBody, row['body'])
        if (digest(row['body']) != ref.content_sha256 or row['content_sha256'] != ref.content_sha256
                or (body.registration_id, body.revision, body.instance_id, body.owner_subject, body.role,
                    body.installed_record_ref.record_id, body.installed_record_ref.revision) != (
                    ref.registration_id, ref.revision, self.engine.instance_id, owner, row['role'],
                    row['installed_record_id'], row['installed_record_revision'])):
            raise EngineError('execution_registration_invalid', 'Immutable execution body/row/ref differ', 422)
        installed, installed_row = self._installed(connection, body.installed_record_ref, owner, registry_revision, commands)
        action = self._read_action(connection, row, 'installation_action', owner, registry_revision, commands)
        selection = self._read_action(connection, row, 'selection_action', owner, registry_revision, commands)
        revoked = self._read_action(connection, row, 'revocation_action', owner, registry_revision, commands)
        if (action is None or action.action not in ('install', 'replace') or ref not in action.execution_refs
                or action.installed_record_ref != body.installed_record_ref or action.registry_revision != row['registry_revision']
                or not set(body.project_ids) <= set(action.project_ids)
                or (action.owner_binding_generation, action.owner_binding_action_id, action.authentication_binding_id) != (
                    body.owner_binding_generation, body.owner_binding_action_id, body.authentication_binding_id)
                or selection is not None and (selection.action != 'select' or ref not in selection.execution_refs
                    or selection.installed_record_ref != body.installed_record_ref)
                or revoked is not None and (revoked.action != 'revoke' or ref not in revoked.execution_refs
                    or revoked.installed_record_ref != body.installed_record_ref)):
            raise EngineError('execution_registration_invalid', 'Original Owner actions and registration scope differ', 422)
        inputs = NativeInstallationInputs.model_validate({key: getattr(installed, key) for key in NativeInstallationInputs.model_fields})
        if (body.installation_inputs_sha256 != private_body_sha256(inputs)
                or (body.registration_sha256, body.resource_manifest_sha256, body.runtime_manifest_sha256,
                    body.owner_binding_generation, body.owner_binding_action_id, body.authentication_binding_id) != (
                    installed.registration_sha256, installed.resource_manifest_sha256, installed.runtime_manifest_sha256,
                    installed.owner_binding_generation, installed.owner_binding_action_id, installed.authentication_binding_id)):
            raise EngineError('execution_registration_invalid', 'Full registration installation binding changed', 422)
        return PersistedExecutionRegistration(ref, body, body.installed_record_ref, installed, action, selection, revoked,
                                             bool(row['current']), bool(row['revoked'])), row, installed_row

    def _active(self, connection, record, installed_row, owner_binding):
        body, installed, now = record.registration, record.installed_record, self.engine.clock()
        principal = owner_binding.principal
        if (not record.current or record.revoked or not installed_row['current'] or installed_row['revoked']
                or body.expires_at_us <= now or body.expires_at_us > principal.expires_at_us
                or owner_binding.revoked or principal.expires_at_us <= now
                or body.owner_subject != principal.owner_subject or body.executing_principal_id != principal.owner_subject
                or not set(body.project_ids) <= set(principal.project_ids)
                or (body.owner_binding_generation, body.owner_binding_action_id, body.authentication_binding_id) != (
                    owner_binding.generation, owner_binding.action_id, principal.authentication_binding_id)
                or (installed.os_subject, installed.directory_device, installed.directory_inode) != (
                    owner_binding.os_subject, owner_binding.directory_device, owner_binding.directory_inode)
                or (record.installation_action.administrator_id, record.installation_action.authentication_source) != (
                    principal.administrator_id, principal.authentication_source)):
            raise EngineError('execution_registration_inactive', 'Execution registration expired, was revoked or has a different current Owner scope', 403)
        self.authorization._project_scope(connection, body.owner_subject, body.project_ids)

    @staticmethod
    def _startup(record, startup_record):
        context = startup_record.context
        installed = record.installed_record
        if (type(context) is not NativeLaunchContext
                or (context.instance_id, context.role, context.registration_sha256, context.resource_manifest_sha256,
                    context.runtime_manifest_sha256, context.expected_files, context.engine_file_names,
                    str(startup_record.installed_native_image), startup_record.installed_native_image_sha256) != (
                    record.registration.instance_id, record.registration.role, installed.registration_sha256,
                    installed.resource_manifest_sha256, installed.runtime_manifest_sha256, installed.expected_files,
                    installed.engine_file_names, installed.installed_native_image, installed.installed_native_image_sha256)):
            raise EngineError('execution_registration_startup_conflict', 'Carrier differs from the complete original installed record', 409)

    def get(self, capability, registration_ref):
        """Real authenticated historical read, never register or activate it."""
        principal = self.authorization._principal(capability, ())
        with (self.authorization.management.action_guard(capability, (), principal.owner_subject),
              self.control.locked(), self.engine.db.connect() as connection):
            revision = self.authorization._revision(connection)
            self.control.assert_revision(revision)
            commands = []
            record, _row, _installed = self._record(connection, registration_ref, principal.owner_subject, revision, commands)
            self.authorization._principal(capability, record.registration.project_ids)
            return record

    def current(self, owner_subject, role, startup_record) -> CurrentExecutionRegistration:
        """OwnerControl then ProductionControl; no secret resolution or permission inference."""
        if role not in ('api', 'mcp', 'worker'):
            raise EngineError('execution_registration_role_invalid', 'Original registered role is required', 422)
        with self._lock, self.bootstrap.current() as owner_binding, self.control.locked():
            if owner_binding.principal.owner_subject != owner_subject:
                raise EngineError('execution_registration_owner_denied', 'Actual Bundle Owner differs from the installed OS Owner action', 403)
            with self.engine.db.connect() as connection:
                revision = self.authorization._revision(connection)
                document = self.control.read()
                proof = None
                if document.pending_request_sha256:
                    from video_creator.application.daily_projects import (
                        read_pending_goal_intent,
                    )

                    proof = read_pending_goal_intent(self.engine, self.bootstrap, self.authorization, self.control, owner_binding)
                    if proof is None:
                        self.control.assert_revision(revision)
                    floor = revision
                else:
                    floor = self.control.assert_revision(revision)
                rows = connection.execute('SELECT registration_id,revision,content_sha256 FROM execution_registrations '
                    'WHERE instance_id=? AND owner=? AND role=? AND current=1', (self.engine.instance_id, owner_subject, role)).fetchall()
                if not rows:
                    raise EngineError('execution_registration_not_found', 'No current execution registration was installed for this actual Owner/role', 404)
                if len(rows) != 1:
                    raise EngineError('execution_registration_current_conflict', 'Current native role has conflicting original registrations', 409)
                row = rows[0]
                try:
                    ref = ExecutionRegistrationRef(registration_id=row['registration_id'], revision=row['revision'], content_sha256=row['content_sha256'])
                except (ValueError, TypeError):
                    raise EngineError('execution_registration_invalid', 'Current original registration reference is damaged', 422) from None
                commands = []
                record, registration_row, installed_row = self._record(connection, ref, owner_subject, revision, commands)
                self._active(connection, record, installed_row, owner_binding)
                self._startup(record, startup_record)
                if proof is not None:
                    self._goal_role(record, proof)
                current = CurrentExecutionRegistration(record, canonical(owner_binding), tuple(dict(registration_row).items()),
                    tuple(dict(installed_row).items()), tuple(commands), floor, self)
                self._currents.add(current)
                return current

    def release(self, current):
        """Original strong-object invalidation only; no DB/floor/budget change."""
        with self._lock:
            self._currents.discard(current)

    @staticmethod
    def _goal_role(record, proof):
        expected = {item.role: item.registration_ref for item in proof.parent.execution_refs}
        if (expected.get(record.registration.role) != record.registration_ref
                or proof.parent.installed_record_ref != record.installed_record_ref
                or proof.intent.owner_subject != record.registration.owner_subject):
            raise EngineError('daily_project_intent_invalid', 'Accepted Goal recovery differs from this original current installed role', 422)

    @contextmanager
    def _accepted_goal_guard(self, current):
        """Private startup/recovery binding only, never normal execution.

        A known accepted Goal can retain its original current object while the
        floor is exactly pending. Normal current_guard still rejects every
        pending floor. Only DailyProjectService resolves the original planned
        no-side-effect writer before the issuer yields its execution guard.
        """
        if (type(current) is not CurrentExecutionRegistration or current._store is not self
                or current not in self._currents):
            raise EngineError('execution_registration_current_required', 'Original same-store current source is required', 403)
        with self._lock, self.bootstrap.current() as owner_binding, self.control.locked():
            if canonical(owner_binding) != current.owner_body:
                raise EngineError('execution_registration_inactive', 'Original actual Owner changed before Goal recovery binding', 403)
            from video_creator.application.daily_projects import (
                read_pending_goal_intent,
            )

            proof = read_pending_goal_intent(self.engine, self.bootstrap, self.authorization, self.control, owner_binding)
            with self.engine.db.connect() as connection:
                revision = self.authorization._revision(connection)
                if proof is None:
                    floor = self.control.assert_revision(revision)
                else:
                    self._goal_role(current.record, proof)
                    floor = proof.database_revision
            guard = ExecutionRegistrationGuard(current, max(floor, current.minimum_registry_revision), threading.get_ident(), self)
            self._guards.add(guard)
            try:
                with self.engine.db.connect() as connection:
                    self.assert_writer_current(connection, guard)
                yield guard, proof
            finally:
                self._guards.remove(guard)

    @contextmanager
    def current_guard(self, current):
        if (not isinstance(current, CurrentExecutionRegistration) or current._store is not self
                or current not in self._currents):
            raise EngineError('execution_registration_current_required', 'Actual original store snapshot is required', 403)
        with self._lock, self.bootstrap.current() as owner_binding, self.control.locked():
            if canonical(owner_binding) != current.owner_body:
                raise EngineError('execution_registration_inactive', 'Original Owner binding changed after current lookup', 403)
            with self.engine.db.connect() as connection:
                floor = self.control.assert_revision(self.authorization._revision(connection))
            guard = ExecutionRegistrationGuard(current, max(floor, current.minimum_registry_revision), threading.get_ident(), self)
            self._guards.add(guard)
            try:
                # This read has no resource RPC or new execution authorization.
                with self.engine.db.connect() as connection:
                    self.assert_writer_current(connection, guard)
                yield guard
            finally:
                self._guards.remove(guard)

    def assert_writer_current(self, connection, guard):
        """Same original connection: DB identity/status/time only, no hash/OS/RPC."""
        if (not isinstance(guard, ExecutionRegistrationGuard) or guard._store is not self
                or guard not in self._guards or guard.thread_id != threading.get_ident()
                or guard.current not in self._currents):
            raise EngineError('execution_registration_guard_required', 'Original store/thread current guard is required', 403)
        current, record = guard.current, guard.current.record
        if self.authorization._revision(connection) < guard.minimum_registry_revision:
            raise EngineError('production_restore_refresh_required', 'Registration database was restored behind its original floor', 503)
        owner_row = connection.execute('SELECT value FROM metadata WHERE key=?', (OWNER_KEY,)).fetchone()
        registration_row = connection.execute('SELECT * FROM execution_registrations WHERE registration_id=? AND revision=? AND owner=? AND instance_id=?',
            (record.registration_ref.registration_id, record.registration_ref.revision, record.registration.owner_subject, self.engine.instance_id)).fetchone()
        installed_row = connection.execute('SELECT * FROM installed_native_records WHERE record_id=? AND revision=? AND owner=? AND instance_id=?',
            (record.installed_record_ref.record_id, record.installed_record_ref.revision, record.registration.owner_subject, self.engine.instance_id)).fetchone()
        if (owner_row is None or owner_row[0] != current.owner_body or registration_row is None or installed_row is None
                or tuple(dict(registration_row).items()) != current.registration_row
                or tuple(dict(installed_row).items()) != current.installed_row
                or registration_row['current'] != 1 or registration_row['revoked'] != 0
                or installed_row['current'] != 1 or installed_row['revoked'] != 0
                or record.registration.expires_at_us <= self.engine.clock()):
            raise EngineError('execution_registration_changed', 'Current original installation/registration/Owner identity changed before commit', 409)
        self.authorization._project_scope(connection, record.registration.owner_subject, record.registration.project_ids)
        for owner, scope, key, request_sha, body in current.command_rows:
            command = connection.execute('SELECT request_sha256,result_json FROM commands WHERE owner=? AND scope=? AND idempotency_key=?',
                (owner, scope, key)).fetchone()
            if command is None or tuple(command) != (request_sha, body):
                raise EngineError('execution_registration_action_invalid', 'Original installed command changed before commit', 422)

    @contextmanager
    def management_writer_guard(self, current, management_service, minimum_revision):
        """Fixed reauthorization writer only, inside its actual Owner action.

        OwnerControl and ProductionControl are already held by that service.
        Reopening them here would reverse the order and do I/O in the writer.
        This guard checks the original thread-local authenticated action, not a
        caller supplied Owner record or a reconstructed capability.
        """
        from video_creator.application.owner_bootstrap import (
            PersistentOwnerManagementRegistry,
        )

        registry = management_service.management
        if (not isinstance(registry, PersistentOwnerManagementRegistry)
                or registry.store.engine is not self.engine or management_service.engine is not self.engine
                or management_service.control is None or management_service.control.path != self.control.path
                or not isinstance(current, CurrentExecutionRegistration)
                or current._store is not self or current not in self._currents
                or type(minimum_revision) is not int or minimum_revision < current.minimum_registry_revision):
            raise EngineError('execution_registration_guard_required', 'Original same-instance authenticated management writer is required', 403)
        held = getattr(registry._action_state, 'record', None)
        if held is None or canonical(held) != current.owner_body:
            raise EngineError('execution_registration_inactive', 'Actual held Owner action differs from the original registration', 403)
        if not self._lock.acquire(blocking=False):
            raise EngineError('execution_registration_busy', 'Original registration is being checked outside this writer', 503)
        try:
            guard = ExecutionRegistrationGuard(current, minimum_revision, threading.get_ident(), self)
            self._guards.add(guard)
            try:
                yield guard
            finally:
                self._guards.remove(guard)
        finally:
            self._lock.release()

    def original_projection(self, current):
        """Only future same-issuer assembly consumes this alongside its strong binding."""
        if (not isinstance(current, CurrentExecutionRegistration) or current._store is not self
                or current not in self._currents):
            raise EngineError('execution_registration_current_required', 'Original same-store current facts are required', 403)
        body = current.record.registration
        return {key: getattr(body, key) for key in ('owner_subject', 'executing_principal_id', 'project_ids',
            'registration_sha256', 'resource_manifest_sha256', 'runtime_manifest_sha256',
            'allowed_source_namespaces', 'expires_at_us')}
