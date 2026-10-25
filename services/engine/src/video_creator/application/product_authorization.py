"""Product-in-installation Owner authorization channel (ADR0081).

The product replaces the terminal `AUTHORIZE <instance> <action>` challenge with a
bounded, in-product consent surface. This module owns that surface and is the only
constructor of `ProductOwnerAuthorizationSource`, the fourth exact
`confirmation_source` of `OwnerBootstrapStore.change()`.

Hard boundaries (all re-checked inside this module, never delegated to a caller):

* it only asks for **first Owner initialization**; `renew`/`revoke` stay on the
  existing TTY/native paths in this revision;
* an approval needs four independent facts: the installation session token (the
  API dependency), the launcher-injected 128-bit session secret (never echoed in
  any response, header, log or audit), a single-use 128-bit nonce, and the
  recomputed canonical scope hash;
* the audit file `Control/ProductAuthorization.json` is written and fsynced
  **before** the Owner binding transaction; if it cannot be written the whole
  approval fails with `authorization_audit_unwritten` and no binding exists;
* the pending request lives only in this process' memory (single slot, exactly
  like ADR0005's `_retained_*` registrations). No table, no migration, no
  recovery of an earlier unapproved request;
* it never unlocks the current process: a successful approval only records the
  Owner binding and reports `restart_required=true`; execution identity is still
  constructed by the trusted startup factory after a restart (ADR0081 section 2);
* it is never a second authorization path: `serve-dev --development-auto-owner-init`
  keeps its own source, and a process with either source disables the other.

The request/audit documents are private to this module and the API layer. They are
not part of `packages/contracts`, not exported into `schemas.json` and the
authorization routes are deliberately excluded from OpenAPI.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from video_creator.application.bundles import strict_json
from video_creator.application.engine import EngineService
from video_creator.application.local_evidence import (
    build_receipt,
    discard_pending_receipt,
    finalize_receipt,
    local_evidence_audit_filename,
    local_evidence_audit_metadata_key,
    local_evidence_scope,
    prepare_receipt,
)
from video_creator.domain.errors import EngineError
from video_creator.infrastructure.owner_identity import inspect_owner_directory

REQUEST_FORMAT = 'product-authorization-request-v1'
VIEW_VERSION = 'product-authorization-ui-v1'
AUDIT_FORMAT = 'product-authorization-audit-v1'
AUDIT_FILENAME = 'ProductAuthorization.json'
AUDIT_METADATA_KEY = 'product_authorization_audit'
AUTHENTICATION_SOURCE = 'product_authorization'
SESSION_SECRET_ENV = 'VIDEO_CREATOR_AUTHORIZATION_SESSION_SECRET'
AUTHORIZATION_HEADER = 'X-VideoCreator-Authorization'
HEALTH_HEADER = 'X-VideoCreator-Authorization'
DEFAULT_OWNER_SUBJECT = 'local-user'
OWNER_BINDING_KIND = 'owner_initialize'
LOCAL_EVIDENCE_KIND = 'local_evidence_policy'
_SUPPORTED_KINDS = (OWNER_BINDING_KIND, LOCAL_EVIDENCE_KIND)
_INSTALL_WINDOW_US = 10 * 60_000_000

_REQUEST_LIFETIME_US = 600_000_000
_MAX_OWNER_LIFETIME_US = 7 * 86400_000_000
_MAX_AUDIT_BYTES = 64 * 1024
_SESSION_SECRET_CHARS = frozenset('0123456789abcdef')
_PRODUCTION_CONTROL_FILENAME = 'ProductionAuthorizationControl.json'
_OWNER_BINDING_METADATA_KEY = 'owner_management_binding'
_AUTHORIZATION_TABLES = ('production_authorization_policies', 'production_admissions',
                         'daily_project_authorizations', 'execution_registrations')
_FACTORY = object()
_EPOCH = object()
_retained_sources: dict[int, ProductOwnerAuthorizationSource] = {}
_retained_channels: dict[int, ProductAuthorizationChannel] = {}


def _denied(code: str, message: str, status_code: int) -> EngineError:
    return EngineError(code, message, status_code)


def _source_denied(message: str) -> EngineError:
    return _denied('authorization_source_denied', message, 403)


def _not_found(message: str) -> EngineError:
    return _denied('authorization_not_found', message, 404)


def _not_available(message: str) -> EngineError:
    return _denied('authorization_session_unavailable', message, 503)


def _session_denied(message: str) -> EngineError:
    return _denied('authorization_session_denied', message, 403)


def _nonce_denied(message: str) -> EngineError:
    return _denied('authorization_nonce_denied', message, 403)


def _origin_denied(message: str) -> EngineError:
    return _denied('origin_denied', message, 403)


def _expired(message: str) -> EngineError:
    return _denied('authorization_expired', message, 409)


def _already_decided(message: str) -> EngineError:
    return _denied('authorization_already_decided', message, 409)


def _conflict(message: str) -> EngineError:
    return _denied('authorization_conflict', message, 409)


def _instance_conflict(message: str) -> EngineError:
    return _denied('authorization_instance_conflict', message, 409)


def _audit_unwritten(message: str) -> EngineError:
    return _denied('authorization_audit_unwritten', message, 503)


def _audit_changed(message: str) -> EngineError:
    return _denied('authorization_audit_changed', message, 409)


def _audit_missing(message: str) -> EngineError:
    return _denied('authorization_audit_missing', message, 503)


def _canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def _fingerprint(value: str) -> str:
    """Short, non-reversible audit fingerprint for a secret or nonce."""
    return _sha256_text(value)[:16]


def _clock(engine) -> int:
    return engine.clock()


def authorization_session_secret_from_environment() -> str | None:
    """Read the launcher-injected authorization session secret, or None.

    The value is 128-bit lowercase hex and is never written anywhere by the
    product. A present but malformed value is a launcher configuration failure
    (`authorization_session_secret_invalid`), not a silently disabled channel.
    """
    raw = os.environ.get(SESSION_SECRET_ENV)
    if raw is None or raw == '':
        return None
    if type(raw) is not str or len(raw) != 32 or any(character not in _SESSION_SECRET_CHARS for character in raw):
        raise _denied('authorization_session_secret_invalid',
                      'The launcher authorization session secret must be 128 bits of lowercase hex', 503)
    return raw


def owner_binding_absent(engine) -> bool:
    """True only when this instance has no persisted Owner binding at all.

    This is the durable-row question, not a directory-permission proof: whether
    the OS actually protects the installation directory is proven later by the
    Owner write itself (`change()`), never by this read-only check. A damaged or
    unreadable binding row is not "absent" and keeps its existing failure path,
    so a broken Owner state can never open a consent surface.
    """
    with engine.db.connect_readonly() as connection:
        row = connection.execute('SELECT 1 FROM metadata WHERE key=?',
                                 (_OWNER_BINDING_METADATA_KEY,)).fetchone()
    return row is None


def _owned_projects(engine, owner_subject: str) -> tuple[str, ...]:
    """The actual projects this installation already records for the Owner."""
    with engine.db.connect_readonly() as connection:
        rows = connection.execute('SELECT id FROM projects WHERE owner=? ORDER BY id',
                                  (owner_subject,)).fetchall()
    projects = tuple(row[0] for row in rows)
    if not projects:
        raise _denied('owner_project_required',
                      'No project this installation owns exists yet; create the first project before requesting Owner authorization',
                      503)
    return projects


@dataclass
class ProductAuthorizationRequest:
    """One in-memory pending consent request; never persisted while pending."""

    format: str
    authorization_id: str
    instance_id: str
    generation: int
    kind: str
    scope: dict
    scope_sha256: str
    requested_by: dict
    created_at_us: int
    expires_at_us: int
    nonce: str
    state: str = 'pending'
    result_ref: dict | None = field(default=None)


class AuthorizationDecision(BaseModel):
    """The exact decision body; an unapproved extra field is refused."""

    model_config = ConfigDict(extra='forbid')

    scope_sha256: str
    nonce: str
    instance_id: str | None = None
    generation: int | None = None


class LocalEvidencePolicyRequest(BaseModel):
    """The product-side request for one local self-issued evidence range."""

    model_config = ConfigDict(extra='forbid')

    project_id: str


class ProductOwnerAuthorizationSource:
    """Opaque in-process product consent source; never serializable or forgeable.

    Construction requires the module-private factory token, registration in the
    process-local retained table, this module's epoch and the issuing thread.
    The object exposes only the four values `change()` needs; there is no
    `model_dump`, no `__reduce__`, no setter and no way to rebuild one from a
    request body, environment value or stored document.
    """

    __slots__ = (
        '_action_key', '_authorization_id', '_caller_module', '_channel', '_claimed',
        '_created_at_us', '_engine', '_epoch', '_expires_at_us', '_generation',
        '_instance_id', '_nonce_fingerprint', '_origin', '_os_identity',
        '_owner_subject', '_project_ids', '_request_expires_at_us', '_requested_by',
        '_scope', '_scope_sha256', '_thread_id',
    )

    def __init__(self, token, *, channel, engine, authorization_id, scope, scope_sha256,
                 generation, request_expires_at_us, owner_expires_at_us, owner_subject,
                 project_ids, nonce_fingerprint, requested_by, origin, caller_module,
                 os_identity, created_at_us, action_key):
        if token is not _FACTORY:
            raise _source_denied('The module-private product authorization factory is required')
        for name, value in (
                ('_channel', channel), ('_engine', engine), ('_authorization_id', authorization_id),
                ('_scope', scope), ('_scope_sha256', scope_sha256), ('_generation', generation),
                ('_request_expires_at_us', request_expires_at_us),
                ('_expires_at_us', owner_expires_at_us), ('_owner_subject', owner_subject),
                ('_project_ids', project_ids), ('_nonce_fingerprint', nonce_fingerprint),
                ('_requested_by', requested_by), ('_origin', origin),
                ('_caller_module', caller_module), ('_os_identity', os_identity),
                ('_created_at_us', created_at_us), ('_action_key', action_key),
                ('_instance_id', engine.instance_id), ('_claimed', False),
                ('_epoch', _EPOCH), ('_thread_id', threading.get_ident())):
            object.__setattr__(self, name, value)
        _retained_sources[id(self)] = self

    def __setattr__(self, name, value):
        raise _source_denied('The product authorization source is immutable after construction')

    @property
    def action_key(self) -> str:
        return self._action_key

    @property
    def owner_subject(self) -> str:
        return self._owner_subject

    @property
    def project_ids(self) -> tuple[str, ...]:
        return self._project_ids

    @property
    def expires_at_us(self) -> int:
        return self._expires_at_us

    @property
    def authorization_id(self) -> str:
        return self._authorization_id

    @property
    def scope_sha256(self) -> str:
        return self._scope_sha256

    def __repr__(self) -> str:
        return '<ProductOwnerAuthorizationSource>'


def _assert_retained(source) -> None:
    if (type(source) is not ProductOwnerAuthorizationSource
            or _retained_sources.get(id(source)) is not source
            or source._epoch is not _EPOCH
            or source._thread_id != threading.get_ident()):
        raise _source_denied('Only the original retained product authorization source is admitted')


def _assert_channel_retained(channel) -> None:
    if type(channel) is not ProductAuthorizationChannel or _retained_channels.get(id(channel)) is not channel:
        raise _source_denied('Only the original retained product authorization channel is admitted')


def assert_product_authorization_source(source, *, engine, proposal, os_identity) -> None:
    """Bind this in-process consent source to the exact Owner proposal and directory.

    This is the fourth and last `change()` branch: it accepts only first Owner
    initialization, only for the instance, scope and directory that were actually
    displayed and approved, and only once.
    """
    _assert_retained(source)
    channel = source._channel
    _assert_channel_retained(channel)
    if type(engine) is not EngineService or source._engine is not engine or channel.engine is not engine:
        raise _source_denied('The product authorization source belongs to another Engine instance')
    if source._claimed:
        raise _source_denied('The product authorization source was already consumed by one Owner action')
    if type(proposal) is not dict:
        raise _source_denied('The product authorization source requires the exact canonical proposal')
    request = channel._request
    if (request is None or request.authorization_id != source.authorization_id
            or request.state != 'approved' or request.scope_sha256 != source.scope_sha256
            or _fingerprint(request.nonce) != source._nonce_fingerprint):
        raise _source_denied('The product authorization source no longer matches its issued request')
    if (proposal.get('action'), proposal.get('action_key'), proposal.get('instance_id'),
            proposal.get('owner_subject'), tuple(proposal.get('project_ids') or ()),
            proposal.get('expires_at_us')) != (
            'initialize', source.action_key, engine.instance_id, source.owner_subject,
            source.project_ids, source.expires_at_us):
        raise _source_denied('The confirmed Owner proposal differs from the product authorization scope')
    if (proposal.get('scope'), proposal.get('os_subject'), proposal.get('directory_device'),
            proposal.get('directory_inode')) != (
            'production.authorization.manage', os_identity.os_subject,
            os_identity.directory_device, os_identity.directory_inode):
        raise _source_denied('The product authorization was not approved for this OS directory identity')
    identity = source._os_identity
    if (identity.os_subject, identity.administrator_id, identity.directory_device,
            identity.directory_inode) != (
            os_identity.os_subject, os_identity.administrator_id, os_identity.directory_device,
            os_identity.directory_inode):
        raise _source_denied('The product authorization OS directory identity changed after approval')
    # The source stays retained so the audit writer can prove it is the original
    # issued object; `_claimed` makes a second Owner action impossible.
    object.__setattr__(source, '_claimed', True)


def _common_audit_document(channel, request, *, decision, result_ref, engine, identity,
                           origin, decided_at_us) -> bytes:
    """The §6 audit document shared by approval and denial decisions."""
    if channel._session_secret is None:
        raise _not_available('The product authorization session secret is not installed in this process')
    document = {
        'format': AUDIT_FORMAT,
        'authorization_id': request.authorization_id,
        'instance_id': engine.instance_id,
        'generation': request.generation,
        'kind': request.kind,
        'scope': request.scope,
        'scope_sha256': request.scope_sha256,
        'requested_by': request.requested_by,
        'created_at_us': request.created_at_us,
        'decided_at_us': decided_at_us,
        'expires_at_us': request.expires_at_us,
        'decision': decision,
        'session_secret_fingerprint': _fingerprint(channel._session_secret),
        'nonce_fingerprint': _fingerprint(request.nonce),
        'origin': origin,
        'caller_module': channel.caller_module,
        'os_identity': {'os_subject': identity.os_subject,
                        'administrator_id': identity.administrator_id,
                        'directory_device': identity.directory_device,
                        'directory_inode': identity.directory_inode},
        'result_ref': result_ref,
    }
    body = _canonical(document).encode('utf-8') + b'\n'
    if len(body) > _MAX_AUDIT_BYTES:
        raise _audit_unwritten(
            'The product authorization audit exceeds its fixed sixty-four kilobyte document bound')
    return body


def _audit_document(source, *, action_id, generation, authorized_at_us, request_sha256,
                    engine, result_ref) -> bytes:
    _assert_retained(source)
    channel = source._channel
    _assert_channel_retained(channel)
    if (type(engine) is not EngineService or source._engine is not engine
            or type(action_id) is not str or not action_id
            or type(generation) is not int or generation <= 0
            or type(authorized_at_us) is not int or authorized_at_us <= 0
            or type(request_sha256) is not str or len(request_sha256) != 64
            or any(character not in _SESSION_SECRET_CHARS for character in request_sha256)
            or type(result_ref) is not dict
            or set(result_ref) != {'command_scope', 'action_key', 'action_id', 'generation'}):
        raise _source_denied('The product authorization audit requires the exact written binding identity')
    request = channel._request
    if request is None or request.authorization_id != source.authorization_id:
        raise _source_denied('The product authorization audit has no matching issued request')
    return _common_audit_document(source._channel, request, decision='approve',
                                  result_ref=result_ref, engine=engine,
                                  identity=source._os_identity, origin=source._origin,
                                  decided_at_us=_clock(engine))


def _install_audit_file(engine, body: bytes, message: str, *, filename: str = AUDIT_FILENAME) -> str:
    """Create (or reuse byte-identical) the one audit file; never overwrite silently."""
    digest_hex = hashlib.sha256(body).hexdigest()
    folder = Path(engine.db.data_dir) / 'Control'
    path = folder / filename
    try:
        if path.is_symlink() or path.is_junction():
            raise OSError('The authorization audit path cannot cross filesystem links')
        if path.exists():
            existing = path.read_bytes()
            if existing == body:
                return digest_hex
            if len(existing) > _MAX_AUDIT_BYTES:
                raise OSError('The previous authorization audit document exceeds its fixed bound')
            aborted = folder / (Path(filename).stem + '.aborted-'
                                + hashlib.sha256(existing).hexdigest() + '.json')
            if aborted.exists():
                raise OSError('The retained aborted authorization audit name already exists')
            path.rename(aborted)
        with path.open('xb') as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as error:
        raise _audit_unwritten(message) from error
    return digest_hex


def write_product_authorization_audit(source, *, action_id, generation, authorized_at_us,
                                      request_sha256, engine, result_ref) -> str:
    """Create the approval audit before the binding; the digest commits with it.

    A stale, different audit file is retained as
    `ProductAuthorization.aborted-<sha256>.json` and never deleted: a failed or
    superseded decision is historical evidence, not something a retry may erase.
    """
    body = _audit_document(source, action_id=action_id, generation=generation,
                           authorized_at_us=authorized_at_us, request_sha256=request_sha256,
                           engine=engine, result_ref=result_ref)
    return _install_audit_file(
        engine, body,
        'The product authorization audit could not be written; no Owner binding was written')


def write_product_denial_audit(channel, request, *, engine, origin) -> str:
    """Create the denial audit before the decision is recorded.

    A denial is a real authorization decision: the same file and committed
    metadata digest record `decision='deny'`, the scope, the fingerprints and
    the caller. A failed write leaves the request pending and changes nothing.
    """
    _assert_channel_retained(channel)
    if (type(engine) is not EngineService or channel.engine is not engine
            or type(request) is not ProductAuthorizationRequest
            or channel._request is not request or request.state != 'pending'):
        raise _source_denied('The product denial audit requires the original pending request')
    folder = Path(engine.db.data_dir) / 'Control'
    try:
        folder.mkdir(mode=0o700, exist_ok=True)
    except OSError as error:
        raise _audit_unwritten('The product authorization audit could not be written; '
                               'the denial was not recorded') from error
    identity = inspect_owner_directory(Path(engine.db.data_dir))
    inspect_owner_directory(folder)
    body = _common_audit_document(channel, request, decision='deny',
                                  result_ref={'authorization_id': request.authorization_id,
                                              'decision': 'deny', 'binding_written': False},
                                  engine=engine, identity=identity, origin=origin or '',
                                  decided_at_us=_clock(engine))
    return _install_audit_file(
        engine, body,
        'The product authorization audit could not be written; the denial was not recorded')


def _commit_audit_digest(engine, digest_hex: str, *, key: str = AUDIT_METADATA_KEY) -> None:
    with engine.db.transaction() as connection:
        connection.execute('INSERT INTO metadata VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                           (key, digest_hex))


def _audit_baseline(engine, filename: str = AUDIT_FILENAME) -> bytes | None:
    path = Path(engine.db.data_dir) / 'Control' / filename
    try:
        if path.is_file() and not path.is_symlink() and not path.is_junction():
            return path.read_bytes()
    except OSError:
        return None
    return None


def _restore_audit(engine, baseline: bytes | None, *, filename: str = AUDIT_FILENAME) -> None:
    """A failed metadata commit may not leave an uncommitted decision audited."""
    path = Path(engine.db.data_dir) / 'Control' / filename
    try:
        if baseline is None:
            if path.is_file() and not path.is_symlink() and not path.is_junction():
                path.unlink()
            return
        temporary = path.with_name(filename + '.restore')
        with temporary.open('wb') as stream:
            stream.write(baseline)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except OSError as error:
        raise _audit_unwritten(
            'The product authorization audit could not be restored after a failed metadata commit'
        ) from error


def _read_audit(engine) -> tuple[dict, str]:
    try:
        with engine.db.connect_readonly() as connection:
            row = connection.execute('SELECT value FROM metadata WHERE key=?',
                                     (AUDIT_METADATA_KEY,)).fetchone()
    except Exception:  # noqa: BLE001 -- a database error is the same missing evidence
        raise _audit_missing('The product authorization audit digest is unavailable') from None
    if row is None or type(row[0]) is not str:
        raise _audit_missing('The product authorization audit is required')
    path = Path(engine.db.data_dir) / 'Control' / AUDIT_FILENAME
    try:
        if (path.is_symlink() or path.is_junction() or not path.is_file()
                or path.stat().st_size > _MAX_AUDIT_BYTES):
            raise _audit_missing('The product authorization audit file is required')
        raw = path.read_bytes()
    except OSError:
        raise _audit_missing('The product authorization audit file is required') from None
    if hashlib.sha256(raw).hexdigest() != row[0]:
        raise _audit_changed('The product authorization audit differs from its committed metadata digest')
    try:
        document = strict_json(raw)
    except (EngineError, TypeError):
        raise _audit_changed('The product authorization audit is not its canonical document') from None
    if type(document) is not dict:
        raise _audit_changed('The product authorization audit is not a single document')
    return document, row[0]


def assert_product_authorization_audit(source, *, engine, action_id, binding_generation,
                                       instance_id, owner_subject, project_ids,
                                       owner_expires_at_us) -> None:
    """The idempotent replay path may only succeed with its committed audit."""
    _assert_retained(source)
    document, _digest = _read_audit(engine)
    scope = document.get('scope')
    result = document.get('result_ref')
    expected_keys = {'format', 'authorization_id', 'instance_id', 'generation', 'kind',
                     'scope', 'scope_sha256', 'requested_by', 'created_at_us',
                     'decided_at_us', 'expires_at_us', 'decision',
                     'session_secret_fingerprint', 'nonce_fingerprint', 'origin',
                     'caller_module', 'os_identity', 'result_ref'}
    if (set(document) != expected_keys or document.get('format') != AUDIT_FORMAT
            or document.get('authorization_id') != source.authorization_id
            or document.get('kind') != OWNER_BINDING_KIND
            or document.get('scope_sha256') != source.scope_sha256
            or document.get('decision') != 'approve'
            or document.get('instance_id') != instance_id
            or type(scope) is not dict
            or scope.get('kind') != OWNER_BINDING_KIND
            or scope.get('owner_subject') != owner_subject
            or scope.get('project_ids') != list(project_ids)
            or scope.get('expires_at_us') != owner_expires_at_us
            or type(result) is not dict
            or result.get('action_id') != action_id
            or result.get('generation') != binding_generation):
        raise _audit_changed('The product authorization audit does not describe the current Owner binding')


def _authorization_counts(engine) -> dict[str, int]:
    counts = {}
    try:
        with engine.db.connect_readonly() as connection:
            for table in _AUTHORIZATION_TABLES:
                counts[table] = int(connection.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0])
    except Exception as error:  # an unreadable registry is not provably empty
        raise _denied('product_authorization_state_denied',
                      'The authorization registry cannot be proven empty', 503) from error
    return counts


def create_product_authorization_control(engine) -> dict | None:
    """Create only the empty first production floor for a product-authorized dev instance.

    `assemble_owner_services` always reads `Control/ProductionAuthorizationControl.json`
    before an execution registration is issued, but production installs that
    floor inside an authenticated management/execution-registration action. A
    development instance that was initialized through the in-product consent
    never runs such an action, so its first restart would dead-end at
    `production_control_unconfigured` (the same bootstrap gap ADR0079 section
    13.2 records for the development source).

    This function creates **only** the empty first floor, and only when all four
    authorization tables are provably empty. An existing floor is never
    overwritten: it is either accepted (empty first floor) or refused. It writes
    no execution identity, no policy and no admission.
    """
    if type(engine) is not EngineService:
        raise _denied('product_authorization_state_denied', 'An actual EngineService is required', 503)
    from video_creator.application.owner_bootstrap import OwnerBootstrapStore
    from video_creator.application.production_management import (
        ProductionAuthorizationControl,
    )

    with OwnerBootstrapStore(engine).current(allow_inactive=False) as record:
        if record.principal.authentication_source != AUTHENTICATION_SOURCE:
            raise _denied('product_authorization_state_denied',
                          'Only an in-product authorized Owner may bootstrap the empty production floor', 503)
    path = Path(engine.db.data_dir) / 'Control' / _PRODUCTION_CONTROL_FILENAME
    if path.is_symlink() or path.is_junction():
        raise _denied('product_authorization_state_denied',
                      'The retained production floor cannot cross filesystem links', 503)
    if path.exists():
        floor = ProductionAuthorizationControl(path, engine.instance_id).read()
        if (floor.instance_id != engine.instance_id or floor.minimum_revision != 0
                or floor.pending_request_sha256 is not None):
            raise _denied('product_authorization_state_denied',
                          'The existing production floor is not the empty first floor', 503)
        return None
    counts = _authorization_counts(engine)
    if any(counts.values()):
        raise _denied('product_authorization_state_denied',
                      'The authorization registry is not empty; the retained production floor is never rebuilt',
                      503)
    control = ProductionAuthorizationControl(path, engine.instance_id)
    control.initialize_new()
    after = control.read()
    if (after.instance_id != engine.instance_id or after.minimum_revision != 0
            or after.pending_request_sha256 is not None):
        raise _denied('product_authorization_state_denied',
                      'The newly installed production floor is not the empty first floor', 503)
    return {'floor': 0, 'path': 'Control/' + _PRODUCTION_CONTROL_FILENAME, 'counts': counts}


class ProductAuthorizationChannel:
    """One restricted or consuming process' in-memory authorization state machine.

    The channel is created by the trusted startup entry point only. It never
    registers an execution identity, never assembles Owner services and never
    grants a management capability: its whole effect is one `change('initialize')`
    call plus the audit that precedes it.
    """

    def __init__(self, engine, *, session_secret=None, owner_subject=DEFAULT_OWNER_SUBJECT,
                 caller_module='video_creator.cli.main', origins=(), allowed_hosts=(),
                 launcher_origin='serve', allowed_kinds=(OWNER_BINDING_KIND,)):
        if type(engine) is not EngineService:
            raise _denied('product_authorization_configuration_conflict',
                          'The product authorization channel requires an actual EngineService', 503)
        if session_secret is not None and (
                type(session_secret) is not str or len(session_secret) != 32
                or any(character not in _SESSION_SECRET_CHARS for character in session_secret)):
            raise _denied('authorization_session_secret_invalid',
                          'The launcher authorization session secret must be 128 bits of lowercase hex', 503)
        if type(owner_subject) is not str or not owner_subject:
            raise _denied('product_authorization_configuration_conflict',
                          'The product authorization channel requires its installation Owner subject', 503)
        if (type(allowed_kinds) is not tuple or not allowed_kinds
                or any(kind not in _SUPPORTED_KINDS for kind in allowed_kinds)
                or len(set(allowed_kinds)) != len(allowed_kinds)):
            raise _denied('product_authorization_configuration_conflict',
                          'The channel offers only distinct supported authorization kinds', 503)
        self.allowed_kinds = allowed_kinds
        self.engine = engine
        self.instance_id = engine.instance_id
        self.owner_subject = owner_subject
        self.caller_module = caller_module
        self.origins = tuple(origins)
        self.allowed_hosts = tuple(allowed_hosts)
        self.launcher_origin = launcher_origin
        self._session_secret = session_secret
        self._lock = threading.RLock()
        self._request: ProductAuthorizationRequest | None = None
        _retained_channels[id(self)] = self

    @property
    def has_session_secret(self) -> bool:
        return self._session_secret is not None

    @property
    def authorization_state(self) -> str:
        """`pending` before a decision, `complete` after one; never `none` here."""
        with self._lock:
            request = self._request
            if request is not None and request.state in {'approved', 'applied'}:
                return 'complete'
            return 'pending'

    def _generation(self) -> int:
        # A restricted process has no binding by construction; only a race with
        # another process can produce one, and then the real generation is read
        # through the same validating store that `change()` will use.
        if owner_binding_absent(self.engine):
            return 0
        from video_creator.application.owner_bootstrap import OwnerBootstrapStore

        with OwnerBootstrapStore(self.engine).current(allow_inactive=True) as record:
            return record.generation

    def _create_request(self, kind=OWNER_BINDING_KIND, *, generation=None, scope=None) -> ProductAuthorizationRequest:
        now = _clock(self.engine)
        if kind not in _SUPPORTED_KINDS:
            raise _denied('authorization_kind_denied', 'Unsupported product authorization kind', 403)
        if generation is None:
            generation = self._generation()
        if scope is None:
            if kind != OWNER_BINDING_KIND:
                raise _source_denied('A non-Owner authorization request requires its exact approved range')
            projects = _owned_projects(self.engine, self.owner_subject)
            owner_expires_at_us = now + _MAX_OWNER_LIFETIME_US
            scope = {
                'kind': OWNER_BINDING_KIND,
                'owner_subject': self.owner_subject,
                'project_ids': list(projects),
                'expires_at_us': owner_expires_at_us,
                'amount_cap': None,
                'target': {'kind': 'local-owner-binding-v1'},
            }
        scope_sha256 = _sha256_text(_canonical(scope))
        identity_material = {'instance_id': self.instance_id, 'generation': generation,
                             'kind': kind, 'scope_sha256': scope_sha256}
        authorization_id = 'authorization-' + _sha256_text(_canonical(identity_material))[:40]
        request = ProductAuthorizationRequest(
            format=REQUEST_FORMAT,
            authorization_id=authorization_id,
            instance_id=self.instance_id,
            generation=generation,
            kind=kind,
            scope=scope,
            scope_sha256=scope_sha256,
            requested_by={'role': 'api', 'pid': os.getpid(), 'executable': sys.executable,
                          'module': self.caller_module,
                          'launcher_origin': self.launcher_origin},
            created_at_us=now,
            expires_at_us=now + _REQUEST_LIFETIME_US,
            nonce=secrets.token_hex(16),
        )
        if self._request is not None and self._request.state == 'pending':
            self._request.state = 'superseded'
        self._request = request
        return request

    @staticmethod
    def _restart_required(request: ProductAuthorizationRequest) -> bool:
        return request.state in {'approved', 'applied'}

    def _view(self, request: ProductAuthorizationRequest) -> dict:
        state = 'complete' if self._restart_required(request) else request.state
        if request.kind == OWNER_BINDING_KIND:
            summary = (
                'Authorize this installation Owner ({owner}) for {count} project(s) until {expiry}'
            ).format(owner=request.scope['owner_subject'],
                     count=len(request.scope['project_ids']),
                     expiry=request.scope['expires_at_us'])
        else:
            summary = (
                'Authorize local self-issued evidence (not measured) for project {project} until {expiry}'
            ).format(project=request.scope['project_id'], expiry=request.scope['expires_at_us'])
        view = {
            'version': VIEW_VERSION,
            'authorization_id': request.authorization_id,
            'kind': request.kind,
            'scope': {**request.scope, 'summary': summary},
            'scope_sha256': request.scope_sha256,
            'created_at_us': request.created_at_us,
            'expires_at_us': request.expires_at_us,
            # The single-use nonce has to reach the page that is allowed to
            # decide. It is returned only while this request is pending and only
            # when a launcher-installed session secret exists (the two GET routes
            # then require that same secret header), and it is never written to
            # disk or to any log. After a decision it is always `null`.
            'nonce': (request.nonce if request.state == 'pending' and self._session_secret is not None
                      else None),
            'state': state,
            'restart_required': self._restart_required(request),
            'can_decide': request.state == 'pending' and _clock(self.engine) < request.expires_at_us,
        }
        if request.kind == LOCAL_EVIDENCE_KIND and request.result_ref:
            # The launcher runs the one-shot installer, then restarts the host so
            # the OS-vault key is picked up by normal startup.
            view['install'] = {
                'action': 'evidence-admin-install',
                'command': 'video_creator evidence-admin install',
                'receipt_id': request.result_ref.get('receipt_id'),
                'receipt_path': request.result_ref.get('receipt_path'),
                'receipt_sha256': request.result_ref.get('receipt_sha256'),
                'restart_required_after_install': True,
            }
        return view

    def pending(self, *, secret=None) -> dict:
        """The one current view.

        A restricted process re-issues its first-Owner request automatically. A
        normal process only shows an already requested evidence range: it never
        opens an Owner-initialization surface.
        """
        with self._lock:
            self._assert_read_secret(secret)
            request = self._request
            owner_available = OWNER_BINDING_KIND in self.allowed_kinds
            if request is None or request.state in {'expired', 'denied', 'superseded'}:
                if not owner_available:
                    if request is None:
                        raise _not_found('No product authorization request has been created in this process')
                    return self._view(request)
                request = self._create_request()
            elif request.state == 'pending' and _clock(self.engine) >= request.expires_at_us:
                request.state = 'expired'
                if not owner_available:
                    return self._view(request)
                request = self._create_request()
            return self._view(request)

    def request_local_evidence_policy(self, project_id, *, secret=None) -> dict:
        """Explicit product consent to issue one local self-issued evidence range."""
        with self._lock:
            self._assert_read_secret(secret)
            if LOCAL_EVIDENCE_KIND not in self.allowed_kinds:
                raise _denied('authorization_kind_denied',
                              'This process does not offer a local evidence policy range', 403)
            if type(project_id) is not str or not project_id:
                raise _denied('owner_project_scope_invalid', 'One explicit owned project is required', 422)
            from video_creator.application.owner_bootstrap import OwnerBootstrapStore

            with OwnerBootstrapStore(self.engine).current(allow_inactive=False) as record:
                principal = record.principal
                if principal.owner_subject != self.owner_subject:
                    raise _denied('evidence_policy_scope_denied',
                                  'The actual Owner binding differs from this installation subject', 403)
                if project_id not in principal.project_ids:
                    raise _denied('production_management_project_denied',
                                  'The requested project is outside the actual Owner scope', 403)
                generation = record.generation
                now = _clock(self.engine)
                expires_at_us = min(now + _MAX_OWNER_LIFETIME_US, principal.expires_at_us)
                if expires_at_us <= now:
                    raise _denied('production_management_denied',
                                  'The actual Owner management scope already expired', 403)
            scope = local_evidence_scope(instance_id=self.instance_id,
                                         owner_subject=self.owner_subject,
                                         project_id=project_id,
                                         expires_at_us=expires_at_us)
            request = self._create_request(LOCAL_EVIDENCE_KIND, generation=generation, scope=scope)
            return self._view(request)

    def get(self, authorization_id: str, *, secret=None) -> dict:
        with self._lock:
            self._assert_read_secret(secret)
            return self._view(self._require_request(authorization_id))

    def _assert_read_secret(self, secret) -> None:
        """A view carrying the nonce requires the launcher session secret.

        Without a configured secret the channel is read-only (approval is
        refused with `authorization_session_unavailable`), so the view stays
        readable but never contains the nonce.
        """
        if self._session_secret is None:
            return
        if type(secret) is not str or not secret or not hmac.compare_digest(
                secret.encode('utf-8'), self._session_secret.encode('utf-8')):
            raise _session_denied('The launcher authorization session secret is missing or wrong')

    def _require_request(self, authorization_id) -> ProductAuthorizationRequest:
        request = self._request
        if (type(authorization_id) is not str or request is None
                or request.state == 'superseded' or request.authorization_id != authorization_id):
            raise _not_found('No product authorization request has this identity in this process')
        return request

    def _assert_caller(self, *, secret, origin, fetch_site) -> None:
        if self._session_secret is None:
            raise _not_available(
                'This process was not started by a launcher that injected the authorization session secret; '
                'it can display the pending request but cannot approve it')
        if type(secret) is not str or not secret or not hmac.compare_digest(
                secret.encode('utf-8'), self._session_secret.encode('utf-8')):
            raise _session_denied('The launcher authorization session secret is missing or wrong')
        if origin is not None and origin not in self.origins:
            raise _origin_denied('Authorization requires an exact trusted startup origin')
        if fetch_site is not None and fetch_site != 'same-origin':
            raise _origin_denied('Authorization requires a same-origin browser request')

    @staticmethod
    def _assert_identity(decision: AuthorizationDecision, request: ProductAuthorizationRequest) -> None:
        if decision.instance_id is not None and decision.instance_id != request.instance_id:
            raise _instance_conflict('The decision names another installation instance')
        if decision.generation is not None and decision.generation != request.generation:
            raise _instance_conflict('The decision names another Owner control generation')

    @staticmethod
    def _assert_decision_credentials(decision: AuthorizationDecision,
                                     request: ProductAuthorizationRequest) -> None:
        if type(decision.nonce) is not str or not hmac.compare_digest(
                decision.nonce.encode('utf-8'), request.nonce.encode('utf-8')):
            raise _nonce_denied('The authorization nonce was already used or does not belong to this request')
        # Recompute the canonical scope hash instead of trusting the stored copy:
        # this is what proves the client approved exactly the displayed scope.
        recomputed = _sha256_text(_canonical(request.scope))
        if recomputed != request.scope_sha256:
            raise _conflict('The pending authorization scope no longer matches its recorded hash')
        if type(decision.scope_sha256) is not str or not hmac.compare_digest(
                decision.scope_sha256.encode('utf-8'), recomputed.encode('utf-8')):
            raise _conflict('The submitted scope hash differs from the approved authorization scope')

    def _expire_if_stale(self, request: ProductAuthorizationRequest) -> None:
        if request.state == 'pending' and _clock(self.engine) >= request.expires_at_us:
            request.state = 'expired'

    def approve(self, authorization_id: str, decision: AuthorizationDecision, *, secret,
                origin=None, fetch_site=None) -> dict:
        with self._lock:
            request = self._require_request(authorization_id)
            self._assert_caller(secret=secret, origin=origin, fetch_site=fetch_site)
            self._assert_identity(decision, request)
            if request.state in {'approved', 'applied'}:
                # Same request + same scope + same nonce + same decision is the
                # original decision replayed, never a second Owner write.
                self._assert_decision_credentials(decision, request)
                return self._view(request)
            if request.state == 'denied':
                if (decision.nonce == request.nonce
                        and decision.scope_sha256 == request.scope_sha256):
                    return self._view(request)
                raise _already_decided('This authorization request was already denied')
            self._expire_if_stale(request)
            if request.state == 'expired':
                raise _expired('This authorization request expired; a new request must be created')
            if request.state != 'pending':
                raise _not_found('No product authorization request has this identity in this process')
            self._assert_decision_credentials(decision, request)
            if request.kind == LOCAL_EVIDENCE_KIND:
                return self._approve_local_evidence(request, origin=origin)
            from video_creator.application.owner_bootstrap import OwnerBootstrapStore

            store = OwnerBootstrapStore(self.engine)
            source = self._issue_source(request, store=store, origin=origin)
            request.state = 'approved'
            try:
                record = store.change(action='initialize', action_key=source.action_key,
                                      owner_subject=source.owner_subject,
                                      project_ids=source.project_ids,
                                      expires_at_us=source.expires_at_us,
                                      confirmation_source=source)
            except BaseException:
                # Nothing was granted; the same still-pending request may be
                # submitted again (its nonce is bound to this single decision).
                if request.state == 'approved':
                    request.state = 'pending'
                raise
            request.state = 'applied'
            request.result_ref = {'action_id': record.action_id, 'generation': record.generation,
                                  'command_scope': 'owner.bootstrap.initialize',
                                  'command_key': source.action_key}
            return self._view(request)

    def _approve_local_evidence(self, request: ProductAuthorizationRequest, *, origin) -> dict:
        """Approve the range only: audit + receipt, no evidence row, no binding.

        The one-shot `evidence-admin` child performs the actual install with the
        real settled ASR observation and the OS-vault key. This process never
        holds that key and never opens the evidence registry.
        """
        from video_creator.application.owner_bootstrap import OwnerBootstrapStore

        now = _clock(self.engine)
        with OwnerBootstrapStore(self.engine).current(allow_inactive=False) as record:
            principal = record.principal
            if (principal.owner_subject != self.owner_subject
                    or principal.owner_subject != request.scope['owner_subject']
                    or request.scope['project_id'] not in principal.project_ids):
                raise _denied('evidence_policy_scope_denied',
                              'The approved local evidence range is outside the actual Owner binding', 403)
            if record.generation != request.generation:
                raise _instance_conflict('The Owner binding generation changed before this approval')
        identity = inspect_owner_directory(Path(self.engine.db.data_dir))
        receipt_id = 'local-evidence-receipt-' + secrets.token_hex(12)
        audit_body = _common_audit_document(
            self, request, decision='approve',
            result_ref={'receipt_id': receipt_id, 'receipt_filename': local_evidence_audit_filename()},
            engine=self.engine, identity=identity, origin=origin or '', decided_at_us=now)
        audit_sha256 = hashlib.sha256(audit_body).hexdigest()
        receipt = build_receipt(
            request_scope=request.scope, authorization_id=request.authorization_id,
            scope_sha256=request.scope_sha256, audit_sha256=audit_sha256, receipt_id=receipt_id,
            approved_at_us=now, install_by_us=now + _INSTALL_WINDOW_US,
            origin=origin or '', nonce_fingerprint=_fingerprint(request.nonce),
            session_secret_fingerprint=_fingerprint(self._session_secret))
        baseline = _audit_baseline(self.engine, local_evidence_audit_filename())
        target, _payload, receipt_sha256 = prepare_receipt(self.engine, receipt=receipt)
        try:
            _install_audit_file(
                self.engine, audit_body,
                'The local evidence approval audit could not be written; no receipt was issued',
                filename=local_evidence_audit_filename())
            _commit_audit_digest(self.engine, audit_sha256,
                                 key=local_evidence_audit_metadata_key())
            finalize_receipt(self.engine, target=target)
        except BaseException:
            discard_pending_receipt(self.engine)
            _restore_audit(self.engine, baseline, filename=local_evidence_audit_filename())
            raise
        request.state = 'applied'
        request.result_ref = {'receipt_id': receipt_id, 'receipt_path': str(target),
                              'receipt_sha256': receipt_sha256,
                              'policy_expires_at_us': request.scope['expires_at_us']}
        return self._view(request)

    def deny(self, authorization_id: str, decision: AuthorizationDecision, *, secret,
             origin=None, fetch_site=None) -> dict:
        with self._lock:
            request = self._require_request(authorization_id)
            self._assert_caller(secret=secret, origin=origin, fetch_site=fetch_site)
            self._assert_identity(decision, request)
            if request.state == 'denied':
                self._assert_decision_credentials(decision, request)
                return self._view(request)
            if request.state in {'approved', 'applied'}:
                raise _already_decided('This authorization request was already approved')
            self._expire_if_stale(request)
            if request.state == 'expired':
                raise _expired('This authorization request expired; a new request must be created')
            if request.state != 'pending':
                raise _not_found('No product authorization request has this identity in this process')
            self._assert_decision_credentials(decision, request)
            # A denial is a real authorization decision, so it is audited before
            # the in-memory state changes: the same `Control/ProductAuthorization.json`
            # (decision='deny') and its committed metadata digest. A failed audit
            # write leaves this request pending and changes nothing.
            baseline = _audit_baseline(self.engine)
            digest_hex = write_product_denial_audit(self, request, engine=self.engine, origin=origin)
            try:
                _commit_audit_digest(self.engine, digest_hex)
            except BaseException:
                _restore_audit(self.engine, baseline)
                raise
            request.state = 'denied'
            request.result_ref = {'decision': 'deny', 'binding_written': False}
            return self._view(request)

    def _issue_source(self, request: ProductAuthorizationRequest, *, store, origin) -> ProductOwnerAuthorizationSource:
        _assert_channel_retained(self)
        if self._session_secret is None:
            raise _not_available('The product authorization session secret is not installed in this process')
        action_key = 'product-owner-initialize.' + request.authorization_id
        return ProductOwnerAuthorizationSource(
            _FACTORY,
            channel=self,
            engine=self.engine,
            authorization_id=request.authorization_id,
            scope=request.scope,
            scope_sha256=request.scope_sha256,
            generation=request.generation,
            request_expires_at_us=request.expires_at_us,
            owner_expires_at_us=request.scope['expires_at_us'],
            owner_subject=request.scope['owner_subject'],
            project_ids=tuple(request.scope['project_ids']),
            nonce_fingerprint=_fingerprint(request.nonce),
            requested_by=dict(request.requested_by),
            origin=origin or '',
            caller_module=self.caller_module,
            os_identity=store.os_identity,
            created_at_us=request.created_at_us,
            action_key=action_key,
        )
