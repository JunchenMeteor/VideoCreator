"""Explicit local Owner binding, retained revocation floor and current registry."""

import json
import os
import sys
import threading
from contextlib import contextmanager
from typing import Literal

from pydantic import Field

from video_creator.application.bundles import strict_json
from video_creator.application.engine import canonical, digest, identity
from video_creator.application.production_management import (
    ManagementPrincipal,
    ProductionAuthorizationControl,
    ProductionManagementRegistry,
    TrustedManagementBinding,
)
from video_creator.domain import contracts as c
from video_creator.domain.errors import EngineError
from video_creator.infrastructure.owner_identity import inspect_owner_directory
from video_creator.infrastructure.owner_secret import OwnerSecretStore

KEY = 'owner_management_binding'


class OwnerBindingRecord(c.Contract):
    format: Literal['local-owner-binding-v1'] = 'local-owner-binding-v1'
    principal: ManagementPrincipal
    os_subject: str = Field(min_length=1, max_length=200)
    directory_device: int = Field(ge=0, strict=True)
    directory_inode: int = Field(ge=0, strict=True)
    generation: int = Field(gt=0, strict=True)
    action_id: c.Identifier
    authorized_at_us: int = Field(gt=0, strict=True)
    revoked: bool


class _OwnerControlDocument(c.Contract):
    format: Literal['owner-management-control-v1'] = 'owner-management-control-v1'
    instance_id: c.Identifier
    minimum_revision: int = Field(ge=0, le=9_223_372_036_854_775_807, strict=True)
    pending_request_sha256: c.Sha256 | None = None


class OwnerManagementControl(ProductionAuthorizationControl):
    _filename = 'OwnerManagementControl.json'
    _document_type = _OwnerControlDocument


class OwnerBootstrapStore:
    def __init__(self, engine):
        self.engine = engine
        self.directory = engine.db.data_dir
        self.os_identity = inspect_owner_directory(self.directory)
        self.control = OwnerManagementControl(self.directory / 'Control' / 'OwnerManagementControl.json', engine.instance_id)
        self.secrets = OwnerSecretStore(self.directory, engine.instance_id)
        self._control_identity = inspect_owner_directory(self.control.path.parent) if self.control.path.parent.exists() else None
        self._fact_epoch, self._fact_sources = object(), set()

    def local_fact_source(self, *, native_connection=None):
        from video_creator.application.owner_fact_sources import local_owner_fact_source

        return local_owner_fact_source(self, native_connection=native_connection)

    def assert_current_directory(self, *, require_control=True):
        actual = inspect_owner_directory(self.directory)
        if actual != self.os_identity:
            raise EngineError('owner_directory_changed', 'Actual OS Owner or installation directory identity changed', 409)
        if require_control:
            if self._control_identity is None:
                raise EngineError('owner_restore_refresh_required', 'The original protected Owner Control directory is required', 503)
            if inspect_owner_directory(self.control.path.parent) != self._control_identity:
                raise EngineError('owner_directory_changed', 'Actual Owner Control directory identity changed', 409)
        return actual

    def _decode(self, body: str):
        try:
            if type(body) is not str:
                raise TypeError('Owner binding requires canonical persisted TEXT')
            record = OwnerBindingRecord.model_validate(strict_json(body.encode('utf-8')))
            if canonical(record) != body:
                raise ValueError('Noncanonical binding')
        except (ValueError, TypeError):
            raise EngineError('owner_binding_invalid', 'Stored local Owner action is damaged', 422) from None
        principal = record.principal
        actual = self.assert_current_directory()
        if (principal.instance_id != self.engine.instance_id or not principal.project_ids
                or len(set(principal.project_ids)) != len(principal.project_ids)
                or principal.administrator_id != actual.administrator_id
                or (record.os_subject, record.directory_device, record.directory_inode) != (
                    actual.os_subject, actual.directory_device, actual.directory_inode)):
            raise EngineError('owner_binding_denied', 'Owner action differs from this actual OS principal and directory', 403)
        return record

    def _read(self, connection):
        row = connection.execute('SELECT value FROM metadata WHERE key=?', (KEY,)).fetchone()
        return self._decode(row[0]) if row else None

    @staticmethod
    def _pending(path):
        if path.is_symlink() or path.is_junction() or not path.is_file() or path.stat().st_size > 65536:
            raise EngineError('owner_pending_invalid', 'Pending Owner action is damaged', 422)
        try:
            pending = strict_json(path.read_bytes())
            if not isinstance(pending, dict) or set(pending) != {'request_sha256', 'record'} or not isinstance(pending['record'], str):
                raise ValueError('Invalid pending fields')
            return pending
        except (ValueError, TypeError):
            raise EngineError('owner_pending_invalid', 'Pending Owner action is malformed', 422) from None

    def project_scope(self, owner_subject, projects):
        c.SourceBinding(system=owner_subject, namespace='local-owner')
        if not projects or len(set(projects)) != len(projects):
            raise EngineError('owner_project_scope_invalid', 'Distinct explicit owned project identities are required', 422)
        with self.engine.db.connect() as connection:
            for project in projects:
                c.SourceBinding(system=project, namespace='owner-project')
                if not connection.execute('SELECT id FROM projects WHERE id=? AND owner=?', (project, owner_subject)).fetchone():
                    raise EngineError('production_management_project_denied', 'Owner scope requires actual owned projects', 403)

    @contextmanager
    def current(self, *, allow_inactive=False):
        self.assert_current_directory()
        with self.control.locked(), self.engine.db.connect() as connection:
            record = self._read(connection)
            if record is None:
                raise EngineError('owner_not_initialized', 'Actual local Owner initialization is required', 503)
            self.control.assert_revision(record.generation)
            if not allow_inactive and (record.revoked or record.principal.expires_at_us <= self.engine.clock()):
                raise EngineError('production_management_denied', 'Local Owner management was revoked or expired', 403)
            yield record
            self.assert_current_directory()

    def revocation_target(self) -> OwnerBindingRecord:
        """Read scope for explicit local confirmation, never issue a capability.

        An original revoke may have committed its row before completing the
        retained floor. Only change() can reconcile that exact command; current()
        must continue rejecting the incomplete floor for management use.
        """
        self.assert_current_directory()
        with self.control.locked(), self.engine.db.connect() as connection:
            self.control.read()
            record = self._read(connection)
            if record is None:
                raise EngineError('owner_not_initialized', 'Actual local Owner initialization is required', 503)
            return record

    def change(self, *, action, action_key, owner_subject, project_ids, expires_at_us,
               confirmation_source=None):
        """Concrete local TTY confirmation; no caller-provided True confirmer."""
        self.assert_current_directory(require_control=self._control_identity is not None)
        if action not in {'initialize', 'renew', 'revoke'}:
            raise EngineError('owner_action_invalid', 'Unsupported local Owner action', 422)
        c.SourceBinding(system=action_key, namespace='owner-bootstrap-command')
        projects = tuple(project_ids)
        self.project_scope(owner_subject, projects)
        if type(expires_at_us) is not int or expires_at_us <= 0:
            raise EngineError('production_management_denied', 'An explicit future management expiry is required', 403)
        proposal = {'action': action, 'action_key': action_key, 'instance_id': self.engine.instance_id,
            'owner_subject': owner_subject, 'project_ids': projects, 'expires_at_us': expires_at_us,
            'scope': 'production.authorization.manage', 'os_subject': self.os_identity.os_subject,
            'directory_device': self.os_identity.directory_device, 'directory_inode': self.os_identity.directory_inode}
        body = json.dumps(proposal, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
        request_sha = digest(body)
        development = None
        product = None
        if confirmation_source is not None:
            from video_creator.application import (
                development_owner_initialization as development,
            )
            from video_creator.application import product_authorization as product
        if confirmation_source is None:
            confirm_local_action(self.engine.instance_id, action, proposal)
            authentication_source = 'headless_administrator'
        elif type(confirmation_source) is development.DevelopmentOwnerInitializationSource:
            # ADR0079: the only automatic Owner write; the exact retained
            # development source is re-bound to this Engine, proposal and OS
            # directory before the Control lock is taken.
            development.assert_development_owner_source(confirmation_source, engine=self.engine,
                                                        proposal=proposal, os_identity=self.os_identity)
            authentication_source = development.DEVELOPMENT_AUTHENTICATION_SOURCE
        elif type(confirmation_source) is product.ProductOwnerAuthorizationSource:
            # ADR0081: the only in-product consent write. The issued source is
            # bound to this Engine, proposal and OS directory, accepts first
            # initialization only, and is consumed by exactly one Owner action.
            product.assert_product_authorization_source(confirmation_source, engine=self.engine,
                                                        proposal=proposal, os_identity=self.os_identity)
            authentication_source = product.AUTHENTICATION_SOURCE
        else:
            from video_creator.application.owner_setup_service import OwnerSetupService
            from video_creator.application.owner_setup_sources import (
                OwnerActionConfirmationSource,
            )

            if (type(confirmation_source) is not OwnerActionConfirmationSource
                    or type(confirmation_source._service) is not OwnerSetupService
                    or confirmation_source._service.bootstrap is not self):
                raise EngineError('owner_setup_confirmation_denied', 'Only the original typed setup action source is admitted', 403)
            confirmation_source._service.assert_bootstrap_action(confirmation_source, self, proposal)
            authentication_source = 'native_owner_session'
        self.assert_current_directory(require_control=self._control_identity is not None)
        if self._control_identity is None and action != 'initialize':
            raise EngineError('owner_restore_refresh_required', 'An existing Owner action requires its original Control directory', 503)
        if (development is not None and authentication_source == development.DEVELOPMENT_AUTHENTICATION_SOURCE
                and (self._control_identity is not None or self.control.path.parent.exists())):
            raise EngineError('development_owner_state_denied',
                              'Development Owner initialization requires an instance with no Control state', 503)
        folder = self.control.path.parent
        folder.mkdir(mode=0o700, exist_ok=True)
        inspect_owner_directory(folder)
        pending_path = folder / 'OwnerManagementPending.json'
        scope = 'owner.bootstrap.' + action
        audit_sha256 = None
        product_audit_sha256 = None
        with self.control.locked():
            if development is not None and authentication_source == development.DEVELOPMENT_AUTHENTICATION_SOURCE:
                with self.engine.db.connect() as connection:
                    binding_row = connection.execute('SELECT 1 FROM metadata WHERE key=?', (KEY,)).fetchone()
                    if binding_row is not None:
                        replay = connection.execute(
                            'SELECT request_sha256 FROM commands WHERE owner=? AND scope=? AND idempotency_key=?',
                            (owner_subject, scope, action_key)).fetchone()
                        if replay is None or replay['request_sha256'] != request_sha:
                            raise EngineError('development_owner_existing_denied',
                                              'A development Owner initialization never replaces an existing binding', 409)
            if self._control_identity is None:
                # Only explicit first initialization may establish the first
                # Control identity; never refresh a replaced existing baseline.
                with self.engine.db.connect() as connection:
                    if connection.execute('SELECT 1 FROM metadata WHERE key=?', (KEY,)).fetchone():
                        raise EngineError('owner_restore_refresh_required', 'Existing Owner binding requires its original Control identity', 503)
                self._control_identity = inspect_owner_directory(folder)
            self.assert_current_directory()
            with self.engine.db.connect() as connection:
                old = self._read(connection)
                revision = old.generation if old else 0
                existing = connection.execute('SELECT request_sha256,result_json FROM commands WHERE owner=? AND scope=? AND idempotency_key=?',
                    (owner_subject, scope, action_key)).fetchone()
                if existing:
                    if existing['request_sha256'] != request_sha:
                        raise EngineError('idempotency_conflict', 'Owner action key was used for another confirmed proposal', 409)
                    original = self._decode(existing['result_json'])
                    floor = self.control.read()
                    if (floor.minimum_revision, floor.pending_request_sha256) == (original.generation, request_sha):
                        self.control.complete(original.generation, request_sha)
                    self.control.assert_revision(revision)
                    if pending_path.exists():
                        pending = self._pending(pending_path)
                        if pending == {'request_sha256': request_sha, 'record': canonical(original)}:
                            pending_path.unlink()
                    if development is not None and authentication_source == development.DEVELOPMENT_AUTHENTICATION_SOURCE:
                        development.assert_development_owner_audit(
                            self.engine, action_id=original.action_id,
                            authentication_source=authentication_source,
                            instance_id=original.principal.instance_id,
                            owner_subject=original.principal.owner_subject,
                            project_ids=tuple(original.principal.project_ids),
                            expires_at_us=original.principal.expires_at_us)
                    if product is not None and authentication_source == product.AUTHENTICATION_SOURCE:
                        product.assert_product_authorization_audit(
                            confirmation_source, engine=self.engine, action_id=original.action_id,
                            binding_generation=original.generation,
                            instance_id=original.principal.instance_id,
                            owner_subject=original.principal.owner_subject,
                            project_ids=tuple(original.principal.project_ids),
                            owner_expires_at_us=original.principal.expires_at_us)
                    return original
                if old and old.principal.owner_subject != owner_subject:
                    raise EngineError('owner_binding_denied', 'This installation already belongs to a different domain Owner', 403)
                if action == 'initialize' and old or action != 'initialize' and old is None:
                    raise EngineError('owner_binding_conflict', 'Initialize, renewal and revocation require their explicit existing state', 409)
                if action == 'revoke' and (projects, expires_at_us) != (old.principal.project_ids, old.principal.expires_at_us):
                    raise EngineError('owner_binding_conflict', 'Revocation must confirm the exact current Owner scope', 409)
                if not self.control.path.exists():
                    if old:
                        raise EngineError('owner_restore_refresh_required', 'Existing Owner binding requires its retained floor', 503)
                    self.control.initialize_new()
                if pending_path.exists():
                    pending = self._pending(pending_path)
                    if pending['request_sha256'] != request_sha:
                        raise EngineError('owner_pending_conflict', 'An earlier exact Owner action requires explicit recovery', 409)
                    record = self._decode(pending['record'])
                    if record.generation != revision + 1 or record.revoked != (action == 'revoke'):
                        raise EngineError('owner_pending_invalid', 'Pending Owner action differs from the current generation', 422)
                    if (record.revoked and record.principal != old.principal
                            or not record.revoked and (record.principal.owner_subject, record.principal.project_ids,
                                record.principal.expires_at_us, record.principal.authentication_source, record.principal.scope) != (
                                owner_subject, projects, expires_at_us, authentication_source, 'production.authorization.manage')):
                        raise EngineError('owner_pending_invalid', 'Pending binding differs from the complete confirmed Owner scope', 422)
                    if not record.revoked:
                        self.secrets.resolve(record.principal.authentication_binding_id)
                    if development is not None and authentication_source == development.DEVELOPMENT_AUTHENTICATION_SOURCE:
                        audit_sha256 = development.write_development_owner_audit(
                            confirmation_source, action_id=record.action_id, generation=record.generation,
                            authorized_at_us=record.authorized_at_us, request_sha256=request_sha, engine=self.engine)
                    if product is not None and authentication_source == product.AUTHENTICATION_SOURCE:
                        product_audit_sha256 = product.write_product_authorization_audit(
                            confirmation_source, action_id=record.action_id, generation=record.generation,
                            authorized_at_us=record.authorized_at_us, request_sha256=request_sha,
                            engine=self.engine,
                            result_ref={'command_scope': scope, 'action_key': action_key,
                                        'action_id': record.action_id, 'generation': record.generation})
                else:
                    if action != 'revoke' and expires_at_us <= self.engine.clock():
                        raise EngineError('production_management_denied', 'New management scope requires an explicit future expiry', 403)
                    if action == 'revoke':
                        principal = old.principal
                    else:
                        principal = ManagementPrincipal(instance_id=self.engine.instance_id,
                            administrator_id=self.os_identity.administrator_id, owner_subject=owner_subject,
                            project_ids=projects, authentication_binding_id=identity('owner-binding'),
                            authentication_source=authentication_source, scope='production.authorization.manage',
                            expires_at_us=expires_at_us)
                        # ADR0081/0082: the in-product consent writes the scoped
                        # Owner binding only. It must not mint the OS-vault
                        # management credential, so this source can never obtain
                        # a management capability (the registry refuses it).
                        if not (product is not None and authentication_source == product.AUTHENTICATION_SOURCE):
                            self.secrets.create(principal.authentication_binding_id)
                    record = OwnerBindingRecord(principal=principal, os_subject=self.os_identity.os_subject,
                        directory_device=self.os_identity.directory_device, directory_inode=self.os_identity.directory_inode,
                        generation=revision + 1, action_id=identity('owner-action'), authorized_at_us=self.engine.clock(),
                        revoked=action == 'revoke')
                    if development is not None and authentication_source == development.DEVELOPMENT_AUTHENTICATION_SOURCE:
                        audit_sha256 = development.write_development_owner_audit(
                            confirmation_source, action_id=record.action_id, generation=record.generation,
                            authorized_at_us=record.authorized_at_us, request_sha256=request_sha, engine=self.engine)
                    if product is not None and authentication_source == product.AUTHENTICATION_SOURCE:
                        product_audit_sha256 = product.write_product_authorization_audit(
                            confirmation_source, action_id=record.action_id, generation=record.generation,
                            authorized_at_us=record.authorized_at_us, request_sha256=request_sha,
                            engine=self.engine,
                            result_ref={'command_scope': scope, 'action_key': action_key,
                                        'action_id': record.action_id, 'generation': record.generation})
                    data = json.dumps({'request_sha256': request_sha, 'record': canonical(record)},
                        ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8') + b'\n'
                    with pending_path.open('xb') as stream:
                        stream.write(data)
                        stream.flush()
                        os.fsync(stream.fileno())
            generation = self.control.reserve(revision, request_sha)
            if generation != record.generation:
                raise EngineError('owner_binding_conflict', 'Owner floor and confirmed generation disagree', 409)
            with self.engine.db.transaction() as connection:
                if (confirmation_source is not None
                        and type(confirmation_source) not in (
                            development.DevelopmentOwnerInitializationSource,
                            product.ProductOwnerAuthorizationSource)):
                    confirmation_source._service.assert_bootstrap_action_local(confirmation_source, self, proposal, connection)
                self.assert_current_directory()
                current = self._read(connection)
                current_body = canonical(current) if current is not None else None
                old_body = canonical(old) if old is not None else None
                if current_body != old_body:
                    raise EngineError('owner_binding_conflict', 'Owner binding changed before its confirmed action', 409)
                for project in projects:
                    if not connection.execute('SELECT id FROM projects WHERE id=? AND owner=?', (project, owner_subject)).fetchone():
                        raise EngineError('production_management_project_denied', 'Confirmed project ownership changed', 403)
                if audit_sha256 is not None:
                    connection.execute('INSERT INTO metadata VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                                       (development.AUDIT_METADATA_KEY, audit_sha256))
                if product_audit_sha256 is not None:
                    connection.execute('INSERT INTO metadata VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                                       (product.AUDIT_METADATA_KEY, product_audit_sha256))
                connection.execute('INSERT INTO metadata VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (KEY, canonical(record)))
                connection.execute('INSERT INTO commands VALUES(?,?,?,?,?)', (owner_subject, scope, action_key, request_sha, canonical(record)))
                self.assert_current_directory()
                if (confirmation_source is not None
                        and type(confirmation_source) not in (
                            development.DevelopmentOwnerInitializationSource,
                            product.ProductOwnerAuthorizationSource)):
                    confirmation_source._service.assert_bootstrap_action_local(confirmation_source, self, proposal, connection)
            self.control.complete(generation, request_sha)
            pending_path.unlink()
            return record


class PersistentOwnerManagementRegistry(ProductionManagementRegistry):
    def __init__(self, store):
        self.store = store
        self._action_state = threading.local()
        with store.current() as record:
            if record.principal.authentication_source == 'product_authorization':
                # ADR0081/0082: in-product Owner consent deliberately mints no
                # management credential, so no registry capability may exist for
                # this source. A TTY/native renewal writes a new principal.
                raise EngineError('production_management_denied',
                                  'In-product Owner initialization grants no production management capability', 403)
            binding = TrustedManagementBinding(record.principal, store.secrets.resolve(record.principal.authentication_binding_id))
            self._generation = record.generation
        super().__init__(store.engine.instance_id, binding.principal.owner_subject, (binding,))

    def _current_record(self):
        held = getattr(self._action_state, 'record', None)
        if held is not None:
            self.store.assert_current_directory()
            return held
        with self.store.current() as record:
            if record.generation != self._generation or record.principal.authentication_binding_id not in self._bindings:
                raise EngineError('production_management_denied', 'Installed Owner management binding changed or was revoked', 403)
            return record

    def authenticate(self, credential, now_us):
        with self._lock:
            self._current_record()
            capability = super().authenticate(credential, now_us)
            try:
                self._current_record()
            except BaseException:
                self._issued.discard(capability)
                raise
            return capability

    def assert_current(self, capability, now_us, *, project_ids, owner_subject):
        principal = super().assert_current(capability, now_us, project_ids=project_ids, owner_subject=owner_subject)
        record = self._current_record()
        if principal != record.principal:
            raise EngineError('production_management_denied', 'Capability differs from the current durable Owner binding', 403)
        return principal

    @contextmanager
    def action_guard(self, capability, project_ids, owner_subject):
        with self._lock, self.store.current() as record:
            if record.generation != self._generation:
                raise EngineError('production_management_denied', 'Owner binding changed before this action', 403)
            super().assert_current(capability, self.store.engine.clock(), project_ids=project_ids, owner_subject=owner_subject)
            self._action_state.record = record
            try:
                yield
                self.store.assert_current_directory()
            finally:
                del self._action_state.record


def confirm_local_action(instance_id, action, proposal):
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise EngineError('owner_interactive_confirmation_required', 'Use an authenticated local Owner terminal with explicit confirmation', 403)
    print(json.dumps({'instance_id': instance_id, 'action': action, 'proposal': proposal}, ensure_ascii=False, indent=2))
    challenge = 'AUTHORIZE ' + instance_id + ' ' + action
    try:
        response = input('Type exactly "' + challenge + '" to confirm: ')
    except EOFError:
        raise EngineError('owner_confirmation_declined', 'Owner confirmation input ended', 403) from None
    if response != challenge:
        raise EngineError('owner_confirmation_declined', 'Owner action was not confirmed', 403)
