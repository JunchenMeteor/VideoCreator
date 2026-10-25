"""Private management credential and externally retained authorization floor.

No production/MCP payload can install these objects. A trusted host must bind a
separate actual Owner/admin session. Merely constructing a service grants none.
"""

import hmac
import os
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import Field

from video_creator.application.bundles import strict_json
from video_creator.application.engine import canonical
from video_creator.domain import contracts as c
from video_creator.domain.errors import EngineError


class ManagementPrincipal(c.Contract):
    instance_id: c.Identifier
    administrator_id: c.Identifier
    owner_subject: c.Identifier
    project_ids: tuple[c.Identifier, ...]
    authentication_binding_id: c.Identifier
    authentication_source: Literal['native_owner_session', 'headless_administrator',
                                   'development_owner_initialization', 'product_authorization']
    scope: Literal['production.authorization.manage']
    expires_at_us: int = Field(gt=0, strict=True)


@dataclass(frozen=True, repr=False)
class TrustedManagementBinding:
    principal: ManagementPrincipal
    credential: bytes = field(repr=False)


@dataclass(frozen=True, eq=False, repr=False)
class AdministrationCapability:
    """Opaque in-process issued capability, never a request/portable DTO."""
    principal: ManagementPrincipal
    _issuer: object = field(repr=False)


class ProductionManagementRegistry:
    def __init__(self, instance_id, owner_subject, bindings=()):
        self.instance_id, self.owner_subject = instance_id, owner_subject
        self._lock = threading.RLock()
        self._bindings, self._issued = {}, set()
        for binding in bindings:
            if (not isinstance(binding, TrustedManagementBinding) or not isinstance(binding.credential, bytes)
                    or not 32 <= len(binding.credential) <= 8192
                    or binding.principal.instance_id != instance_id
                    or binding.principal.owner_subject != owner_subject
                    or not binding.principal.project_ids
                    or len(set(binding.principal.project_ids)) != len(binding.principal.project_ids)
                    or binding.principal.authentication_binding_id in self._bindings):
                raise EngineError('production_management_configuration_invalid', 'Trusted management bindings are not exact distinct Owner scopes', 503)
            if any(hmac.compare_digest(existing.credential, binding.credential) for existing in self._bindings.values()):
                raise EngineError('production_management_configuration_invalid', 'Management credentials must bind one exact installed identity', 503)
            self._bindings[binding.principal.authentication_binding_id] = binding

    def authenticate(self, credential: bytes, now_us: int) -> AdministrationCapability:
        if not isinstance(credential, bytes) or not 32 <= len(credential) <= 8192:
            raise EngineError('production_management_denied', 'Separate authenticated production management is required', 403)
        with self._lock:
            self._issued = {capability for capability in self._issued if capability.principal.expires_at_us > now_us
                and capability.principal.authentication_binding_id in self._bindings}
            for binding in self._bindings.values():
                if binding.principal.expires_at_us > now_us and hmac.compare_digest(binding.credential, credential):
                    capability = AdministrationCapability(binding.principal, self)
                    self._issued.add(capability)
                    return capability
        raise EngineError('production_management_denied', 'Separate authenticated production management is required', 403)

    def assert_current(self, capability, now_us, *, project_ids, owner_subject):
        with self._lock:
            if (not isinstance(capability, AdministrationCapability) or capability._issuer is not self
                    or capability not in self._issued):
                raise EngineError('production_management_denied', 'Management capability was not issued by this installed registry', 403)
            principal = capability.principal
            binding = self._bindings.get(principal.authentication_binding_id)
            if (not binding or binding.principal != principal or principal.expires_at_us <= now_us
                    or principal.instance_id != self.instance_id or principal.owner_subject != owner_subject
                    or not set(project_ids) <= set(principal.project_ids)):
                raise EngineError('production_management_denied', 'Management identity expired, was revoked or is outside the exact Owner scope', 403)
            return principal

    def revoke_binding(self, authentication_binding_id):
        """Trusted host session closure only; never a model management tool."""
        with self._lock:
            self._bindings.pop(authentication_binding_id, None)
            self._issued = {capability for capability in self._issued
                if capability.principal.authentication_binding_id != authentication_binding_id}


class _ControlDocument(c.Contract):
    format: Literal['production-authorization-control-v1'] = 'production-authorization-control-v1'
    instance_id: c.Identifier
    minimum_revision: int = Field(ge=0, le=9_223_372_036_854_775_807, strict=True)
    pending_request_sha256: c.Sha256 | None = None


class ProductionAuthorizationControl:
    """A separately retained high-water mark, excluded from SQLite snapshots.

    The floor is reserved before a management commit, outside its DB writer.
    A crash before commit fails closed. Only an exact authorized retry may
    complete that same reservation; no automatic floor rollback is allowed.
    """
    _filename = 'ProductionAuthorizationControl.json'
    _document_type = _ControlDocument

    def __init__(self, path: Path, instance_id: str):
        path = Path(path)
        if (not path.is_absolute() or str(path).startswith(('\\\\', '//'))
                or path.name != self._filename):
            raise EngineError('production_control_path_denied', 'Trusted control requires its fixed absolute local filename', 503)
        for parent in (path, *path.parents):
            if parent.is_symlink() or parent.is_junction():
                raise EngineError('production_control_path_denied', 'Authorization control cannot cross links', 503)
        self.path, self.instance_id = path, instance_id
        self._lock = threading.RLock()

    @contextmanager
    def locked(self):
        if not self.path.parent.is_dir():
            raise EngineError('production_control_unconfigured', 'Externally retained authorization control is not installed', 503)
        lock_path = self.path.with_suffix('.lock')
        if lock_path.is_symlink() or lock_path.is_junction():
            raise EngineError('production_control_path_denied', 'Authorization control lock cannot cross links', 503)
        with self._lock, lock_path.open('a+b') as stream:
            stream.seek(0)
            if stream.read(1) == b'':
                stream.write(b'\0')
                stream.flush()
            stream.seek(0)
            try:
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                raise EngineError('production_control_busy', 'Retained authorization control is unavailable or owned by another action', 503) from None
            try:
                yield
            finally:
                stream.seek(0)
                if os.name == 'nt':
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)

    def read(self):
        if self.path.is_symlink() or not self.path.is_file() or self.path.stat().st_size > 64 * 1024:
            raise EngineError('production_control_unconfigured', 'Current external authorization floor is unavailable', 503)
        try:
            document = self._document_type.model_validate(strict_json(self.path.read_bytes()))
        except (ValueError, TypeError):
            raise EngineError('production_control_invalid', 'Current external authorization floor is damaged', 422) from None
        if document.instance_id != self.instance_id:
            raise EngineError('production_control_instance_conflict', 'Control belongs to another installation', 409)
        return document

    def _install(self, document):
        if self.path.is_symlink() or self.path.is_junction():
            raise EngineError('production_control_path_denied', 'Authorization control changed into a link', 503)
        temporary = self.path.with_suffix('.pending')
        data = (canonical(document) + '\n').encode('utf-8')
        if temporary.exists():
            if (temporary.is_symlink() or temporary.is_junction()
                    or temporary.stat().st_size != len(data) or temporary.read_bytes() != data):
                raise EngineError('production_control_update_incomplete', 'Earlier incomplete control bytes require explicit Owner recovery', 503)
        else:
            with temporary.open('xb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        os.replace(temporary, self.path)
        if os.name != 'nt':
            descriptor = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)

    def initialize_new(self):
        """Service calls only after an actual authorized action on an empty registry."""
        if self.path.exists():
            return self.read()
        self._install(self._document_type(instance_id=self.instance_id, minimum_revision=0))
        return self.read()

    def reserve(self, database_revision, request_sha256):
        current = self.read()
        next_revision = database_revision + 1
        if current.minimum_revision > database_revision:
            if (current.minimum_revision, current.pending_request_sha256) != (next_revision, request_sha256):
                raise EngineError('production_restore_refresh_required', 'Authorization database is behind its retained floor', 503)
            return next_revision
        if current.pending_request_sha256 is not None:
            raise EngineError('production_control_pending', 'An earlier management reservation must be completed first', 409)
        self._install(self._document_type(instance_id=self.instance_id, minimum_revision=next_revision,
                                       pending_request_sha256=request_sha256))
        return next_revision

    def complete(self, revision, request_sha256):
        current = self.read()
        if (current.minimum_revision, current.pending_request_sha256) != (revision, request_sha256):
            raise EngineError('production_control_conflict', 'Original management reservation changed', 409)
        self._install(self._document_type(instance_id=self.instance_id, minimum_revision=revision))

    def assert_revision(self, database_revision):
        current = self.read()
        if current.pending_request_sha256 or database_revision < current.minimum_revision:
            raise EngineError('production_restore_refresh_required', 'Production policy requires current external authorization state', 503)
        return current.minimum_revision
