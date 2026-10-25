"""Development-only first Owner initialization source for ADR0079; never a release path.

The type defined here is the third, explicitly restricted `confirmation_source`
of `OwnerBootstrapStore.change()`. It is constructed only by
`video_creator.cli.development_host`, only in a development process whose three
development conditions already hold, and only for a true first start (no
`Control/` directory, no Owner binding). It carries no callable confirmer and
cannot be expressed as a bool, dict, string, JSON document or argv value.

Everything this module proves is "this checkout, this registration file, this
registered project scope and this OS identity agree right now". It is not a
native Owner session, not an installation qualification and never acceptable
release, Gate0 or acceptance evidence.
"""

import hashlib
import json
import os
import sys
import threading
from datetime import UTC, datetime
from pathlib import Path

from video_creator.application.bundles import BundleService, strict_json
from video_creator.application.engine import EngineService, digest
from video_creator.application.production_management import (
    ProductionAuthorizationControl,
)
from video_creator.domain import contracts as c
from video_creator.domain.errors import EngineError
from video_creator.domain.local_material_production import RegistrationConfigLocalV1
from video_creator.infrastructure.owner_identity import inspect_owner_directory

_FACTORY = object()
_EPOCH = object()
_retained_sources = {}

DEVELOPMENT_OWNER_SUBJECT = 'local-user'
DEVELOPMENT_AUTHENTICATION_SOURCE = 'development_owner_initialization'
AUDIT_METADATA_KEY = 'development_owner_initialization_audit'
AUDIT_FILENAME = 'DevelopmentOwnerInitialization.json'
AUDIT_FORMAT = 'development-owner-initialization-audit-v1'
_MAX_OWNER_LIFETIME_US = 7 * 86400_000_000
_MAX_AUDIT_BYTES = 64 * 1024

_DEVELOPMENT_ARGUMENTS = ('--development-registration', '--development-registration-sha256',
                          '--development-expires-at')
_AUDIT_KEYS = {'format', 'action', 'action_key', 'instance_id', 'owner_subject', 'project_ids',
               'expires_at_us', 'owner_binding', 'request_sha256', 'registration',
               'development_arguments', 'environment', 'process', 'os_identity', 'created_at_us'}
_OPTIONAL_AUDIT_KEYS = {'production_control_created'}
_PRODUCTION_CONTROL_FILENAME = 'ProductionAuthorizationControl.json'
_PRODUCTION_CONTROL_RECORD = 'production_control_created'
_PRODUCTION_CONTROL_RELATIVE = 'Control/' + _PRODUCTION_CONTROL_FILENAME
_AUTHORIZATION_TABLES = ('production_authorization_policies', 'production_admissions',
                         'daily_project_authorizations', 'execution_registrations')
_CALLER_MODULE = 'video_creator.cli.development_host'
_EPOCH_DATETIME = datetime(1970, 1, 1, tzinfo=UTC)


def _denied(code: str, message: str, status_code: int) -> EngineError:
    return EngineError(code, message, status_code)


def _source_denied(message: str) -> EngineError:
    return _denied('development_owner_source_denied', message, 403)


def _audit_missing(message: str) -> EngineError:
    return _denied('development_owner_audit_missing', message, 503)


def _audit_changed(message: str) -> EngineError:
    return _denied('development_owner_audit_changed', message, 409)


def _registration_missing(message: str) -> EngineError:
    return _denied('development_registration_missing', message, 503)


def _registration_changed(message: str) -> EngineError:
    return _denied('development_registration_changed', message, 503)


def _subject_denied(message: str) -> EngineError:
    return _denied('development_owner_subject_denied', message, 403)


def _project_required(message: str) -> EngineError:
    return _denied('development_owner_project_required', message, 503)


def _registration_conflict(message: str) -> EngineError:
    return _denied('development_owner_registration_conflict', message, 409)


def _caller_module() -> str | None:
    """The caller's canonical module name, also when the host runs via `python -m`.

    A `-m` entry executes the host file as `__main__`; its import spec still
    carries the canonical name, so the recorded provenance stays exact.
    """
    caller_globals = sys._getframe(2).f_globals
    specification = caller_globals.get('__spec__')
    return getattr(specification, 'name', None) or caller_globals.get('__name__')


def _read_registration_file(path_text, registration_sha256) -> Path:
    """Step 4: the exact absolute local registration file, read and re-hashed."""
    try:
        path = Path(path_text)
    except (TypeError, ValueError):
        raise _registration_missing('The development registration must be a fixed absolute local file') from None
    try:
        if (not path.is_absolute() or str(path).startswith(('\\\\', '//'))
                or path.is_symlink() or path.is_junction() or not path.is_file()
                or path.stat().st_size > 1024 * 1024):
            raise _registration_missing('The development registration must be a fixed absolute local file')
        raw = path.read_bytes()
    except OSError:
        raise _registration_missing('The development registration file is unavailable') from None
    if type(registration_sha256) is not str or len(registration_sha256) != 64 or any(
            character not in '0123456789abcdef' for character in registration_sha256):
        raise _registration_changed('The pinned development registration SHA256 must be 64 lowercase hex characters')
    if hashlib.sha256(raw).hexdigest() != registration_sha256:
        raise _registration_changed('The development registration differs from the pinned SHA256')
    return path.resolve()


def _parse_expiry(text: str) -> int:
    """Step 10: the original text must parse to the same microsecond instant."""
    if type(text) is not str:
        raise _source_denied('The development expiry argument must be its original text')
    try:
        value = datetime.fromisoformat(text)
    except ValueError:
        raise _source_denied('The development expiry argument is not an ISO8601 instant') from None
    if value.tzinfo is None or value.utcoffset() is None:
        raise _source_denied('The development expiry argument must carry an explicit timezone')
    delta = value.astimezone(UTC) - _EPOCH_DATETIME
    microseconds = (delta.days * 86400 + delta.seconds) * 1_000_000 + delta.microseconds
    if microseconds <= 0:
        raise _source_denied('The development expiry argument must be a positive microsecond instant')
    return microseconds


def _checked_data_dir(engine, data_dir) -> Path:
    try:
        candidate = Path(data_dir)
    except (TypeError, ValueError):
        raise _source_denied('The development data directory must be an absolute local directory') from None
    if not candidate.is_absolute() or str(candidate).startswith(('\\\\', '//')):
        raise _source_denied('The development data directory must be an absolute local directory')
    try:
        if candidate.is_symlink() or candidate.is_junction() or not candidate.is_dir():
            raise _source_denied('The development data directory cannot cross filesystem links')
        if candidate.resolve() != Path(engine.db.data_dir).resolve():
            raise _source_denied('The development data directory must be this exact Engine instance')
    except OSError:
        raise _source_denied('The development data directory is unavailable') from None
    return Path(engine.db.data_dir)


def _raw_arguments(raw_arguments) -> tuple[tuple[str, str], ...]:
    """Step 10: exactly the three development arguments, verbatim and in order."""
    if type(raw_arguments) is not tuple or len(raw_arguments) != len(_DEVELOPMENT_ARGUMENTS):
        raise _source_denied('The original development arguments are required')
    for expected, pair in zip(_DEVELOPMENT_ARGUMENTS, raw_arguments, strict=True):
        if type(pair) is not tuple or len(pair) != 2 or pair[0] != expected or type(pair[1]) is not str:
            raise _source_denied('The original development arguments must be exactly the three values')
    return raw_arguments


def _validate_project_scope(engine, declaration) -> tuple[str, ...]:
    """Step 8: only the registration's declared projects, each actually owned."""
    projects = tuple(declaration.project_ids)
    if not projects or len(set(projects)) != len(projects):
        raise _project_required('The development registration must declare distinct owned projects')
    try:
        for project in projects:
            c.SourceBinding(system=project, namespace='owner-project')
    except (ValueError, TypeError):
        raise _source_denied('Every declared project identity must be a real source binding') from None
    with engine.db.connect_readonly() as connection:
        for project in projects:
            row = connection.execute('SELECT 1 FROM projects WHERE id=? AND owner=?',
                                     (project, DEVELOPMENT_OWNER_SUBJECT)).fetchone()
            if row is None:
                raise _project_required(
                    "The development registration declares a project this Owner does not own; prepare it first: "
                    "PrepareLocalChain.py ensure-project --data-dir " + str(engine.db.data_dir)
                    + " --project-id " + project)
    return projects


def _assert_authority(engine, authority, role, registration_path: Path, registration_sha256: str) -> None:
    """Step 7: the live development authority this process actually built."""
    from video_creator.application.development_installation import (
        DevelopmentInstallationAuthority,
    )

    connection = getattr(authority, 'connection', None)
    context = getattr(connection, 'context', None)
    if (type(authority) is not DevelopmentInstallationAuthority
            or getattr(authority, '_engine', None) is not engine
            or getattr(authority, '_registration_sha256', None) != registration_sha256
            or Path(getattr(authority, '_registration_path', Path('/'))).resolve() != registration_path
            or Path(getattr(authority, '_root', Path('/'))).resolve() != registration_path.parent
            or getattr(authority, '_closed', None) is not False
            or getattr(authority, '_retired', None) is not False
            or getattr(context, 'instance_id', None) != engine.instance_id
            or getattr(context, 'role', None) != role
            or getattr(context, 'registration_sha256', None) != registration_sha256):
        raise _registration_conflict('The development Owner source does not belong to this live development authority')


class DevelopmentOwnerInitializationSource:
    """Opaque in-process development Owner source; never serializable or forgeable."""

    __slots__ = (
        '_action_key',
        '_authority',
        '_caller_module',
        '_config',
        '_created_at_us',
        '_engine',
        '_environment_value',
        '_epoch',
        '_executable',
        '_expires_at_us',
        '_os_identity',
        '_owner_subject',
        '_pid',
        '_project_ids',
        '_raw_arguments',
        '_registration_path',
        '_registration_sha256',
        '_resource_manifest_sha256',
        '_role',
        '_runtime_manifest_sha256',
        '_thread_id',
    )

    def __init__(self, token, *, engine, authority, config, role, registration_path, registration_sha256,
                 resource_manifest_sha256, runtime_manifest_sha256, raw_arguments, environment_value,
                 os_identity, owner_subject, project_ids, action_key, expires_at_us, caller_module,
                 pid, executable, created_at_us):
        if token is not _FACTORY:
            raise _source_denied('The original development Owner factory is required')
        for name, value in (
                ('_engine', engine), ('_authority', authority), ('_config', config), ('_role', role),
                ('_registration_path', registration_path), ('_registration_sha256', registration_sha256),
                ('_resource_manifest_sha256', resource_manifest_sha256),
                ('_runtime_manifest_sha256', runtime_manifest_sha256),
                ('_raw_arguments', raw_arguments), ('_environment_value', environment_value),
                ('_os_identity', os_identity), ('_owner_subject', owner_subject),
                ('_project_ids', project_ids), ('_action_key', action_key),
                ('_expires_at_us', expires_at_us), ('_caller_module', caller_module),
                ('_pid', pid), ('_executable', executable), ('_created_at_us', created_at_us),
                ('_epoch', _EPOCH), ('_thread_id', threading.get_ident())):
            object.__setattr__(self, name, value)
        _retained_sources[id(self)] = self

    def __setattr__(self, name, value):
        raise _source_denied('The development Owner source is immutable after construction')

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

    def __repr__(self) -> str:
        return '<DevelopmentOwnerInitializationSource>'


def development_owner_initialization_source(*, engine, registration_path, registration_sha256,
                                            expires_at_us, data_dir, role, bundle, authority, config,
                                            raw_arguments) -> DevelopmentOwnerInitializationSource:
    """The sole factory; every invocation re-verifies its own preconditions."""
    caller_module = _caller_module()
    if type(engine) is not EngineService:
        raise _source_denied('An actual EngineService is required')
    if type(role) is not str or role not in {'api', 'worker'}:
        raise _source_denied('The development Owner source supports only the api and worker roles')
    directory = _checked_data_dir(engine, data_dir)
    if getattr(sys, 'frozen', False):
        raise _denied('development_installation_unavailable',
                      'A frozen artifact cannot host a development installation', 503)
    if os.environ.get('VIDEO_CREATOR_DEVELOPMENT_INSTALLATION') != engine.instance_id:
        raise _denied('development_installation_denied',
                      'VIDEO_CREATOR_DEVELOPMENT_INSTALLATION must equal this instance identity', 403)
    registration_file = _read_registration_file(registration_path, registration_sha256)
    if type(config) is not RegistrationConfigLocalV1:
        raise _subject_denied('The development Owner source requires the parsed local-v1 registration')
    declaration = config.local_registration.rights_declaration
    if declaration.declaring_subject != DEVELOPMENT_OWNER_SUBJECT:
        raise _subject_denied('The development registration must declare the local-user subject')
    if (type(bundle) is not BundleService or bundle.engine is not engine
            or getattr(bundle.principals, 'owner_subject', None) != DEVELOPMENT_OWNER_SUBJECT):
        raise _subject_denied('The development Bundle principal must be the declared local-user subject')
    _assert_authority(engine, authority, role, registration_file, registration_sha256)
    projects = _validate_project_scope(engine, declaration)
    now = engine.clock()
    if type(expires_at_us) is not int or not now < expires_at_us <= now + _MAX_OWNER_LIFETIME_US:
        raise _denied('development_owner_expiry_invalid',
                      'The development Owner expiry must end inside the seven day cap', 422)
    raw = _raw_arguments(raw_arguments)
    if Path(raw[0][1]).resolve() != registration_file:
        raise _source_denied('The original registration argument is not this registration file')
    if raw[1][1] != registration_sha256:
        raise _source_denied('The original registration SHA256 argument is not this registration SHA256')
    if _parse_expiry(raw[2][1]) != expires_at_us:
        raise _source_denied('The original expiry argument is not this Owner expiry')
    if caller_module != _CALLER_MODULE:
        raise _source_denied('Only the development host may construct the development Owner source')
    os_identity = inspect_owner_directory(directory)
    action_key = 'development-owner-initialize.' + digest(engine.instance_id)
    return DevelopmentOwnerInitializationSource(
        _FACTORY, engine=engine, authority=authority, config=config, role=role,
        registration_path=registration_file, registration_sha256=registration_sha256,
        resource_manifest_sha256=config.production_resource_manifest_sha256,
        runtime_manifest_sha256=config.production_runtime_manifest_sha256,
        raw_arguments=raw, environment_value=os.environ['VIDEO_CREATOR_DEVELOPMENT_INSTALLATION'],
        os_identity=os_identity, owner_subject=DEVELOPMENT_OWNER_SUBJECT, project_ids=projects,
        action_key=action_key, expires_at_us=expires_at_us, caller_module=caller_module,
        pid=os.getpid(), executable=sys.executable, created_at_us=engine.clock())


def _assert_retained(source) -> None:
    if (type(source) is not DevelopmentOwnerInitializationSource
            or _retained_sources.get(id(source)) is not source
            or source._epoch is not _EPOCH
            or source._thread_id != threading.get_ident()):
        raise _source_denied('Only the original retained development Owner source is admitted')


def assert_development_owner_source(source, *, engine, proposal, os_identity) -> None:
    """Bind this in-process source to the exact proposal, directory and authority."""
    _assert_retained(source)
    if type(engine) is not EngineService or source._engine is not engine:
        raise _source_denied('The development Owner source belongs to another Engine instance')
    if type(proposal) is not dict:
        raise _source_denied('The development Owner source requires the exact canonical proposal')
    if (proposal.get('action'), proposal.get('action_key'), proposal.get('instance_id'),
            proposal.get('owner_subject'), proposal.get('project_ids'),
            proposal.get('expires_at_us')) != (
            'initialize', source.action_key, engine.instance_id, source.owner_subject,
            source.project_ids, source.expires_at_us):
        raise _source_denied('The confirmed Owner proposal differs from the development source scope')
    if (proposal.get('os_subject'), proposal.get('directory_device'), proposal.get('directory_inode')) != (
            os_identity.os_subject, os_identity.directory_device, os_identity.directory_inode):
        raise _source_denied('The development Owner source was not observed on this OS directory identity')
    if type(source._config) is not RegistrationConfigLocalV1:
        raise _subject_denied('The development Owner source no longer holds the parsed local-v1 registration')
    declaration = source._config.local_registration.rights_declaration
    if (declaration.declaring_subject != DEVELOPMENT_OWNER_SUBJECT
            or declaration.project_ids != source.project_ids):
        raise _subject_denied('The development registration no longer declares this Owner scope')
    _assert_authority(engine, source._authority, source._role, source._registration_path,
                      source._registration_sha256)
    try:
        if (source._registration_path.is_symlink() or source._registration_path.is_junction()
                or not source._registration_path.is_file()
                or source._registration_path.stat().st_size > 1024 * 1024):
            raise _registration_missing('The development registration file is unavailable')
        if hashlib.sha256(source._registration_path.read_bytes()).hexdigest() != source._registration_sha256:
            raise _registration_changed('The development registration changed after it authorized this action')
    except OSError:
        raise _registration_missing('The development registration file is unavailable') from None


def _audit_document(source, *, action_id, generation, authorized_at_us, request_sha256, engine) -> bytes:
    if (type(action_id) is not str or not action_id or type(generation) is not int or generation <= 0
            or type(authorized_at_us) is not int or authorized_at_us <= 0
            or type(request_sha256) is not str
            or len(request_sha256) != 64
            or any(character not in '0123456789abcdef' for character in request_sha256)):
        raise _source_denied('The development Owner audit requires the exact written binding identity')
    identity = source._os_identity
    document = {
        'format': AUDIT_FORMAT,
        'action': 'initialize',
        'action_key': source.action_key,
        'instance_id': engine.instance_id,
        'owner_subject': source.owner_subject,
        'project_ids': list(source.project_ids),
        'expires_at_us': source.expires_at_us,
        'owner_binding': {'action_id': action_id, 'generation': generation,
                          'authorized_at_us': authorized_at_us},
        'request_sha256': request_sha256,
        'registration': {'path': str(source._registration_path),
                         'sha256': source._registration_sha256,
                         'resource_manifest_sha256': source._resource_manifest_sha256,
                         'runtime_manifest_sha256': source._runtime_manifest_sha256},
        'development_arguments': [[name, value] for name, value in source._raw_arguments],
        'environment': {'VIDEO_CREATOR_DEVELOPMENT_INSTALLATION': source._environment_value},
        'process': {'role': source._role, 'frozen': False, 'pid': source._pid,
                    'executable': source._executable, 'caller_module': source._caller_module,
                    'thread_id': source._thread_id},
        'os_identity': {'os_subject': identity.os_subject,
                        'administrator_id': identity.administrator_id,
                        'directory_device': identity.directory_device,
                        'directory_inode': identity.directory_inode},
        'created_at_us': engine.clock(),
    }
    if set(document) != _AUDIT_KEYS:
        raise _source_denied('The development Owner audit document is incomplete')
    body = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                      allow_nan=False).encode('utf-8') + b'\n'
    if len(body) > _MAX_AUDIT_BYTES:
        raise _denied('development_owner_audit_unwritten',
                      'The development Owner audit exceeds its fixed sixty-four kilobyte document bound', 503)
    return body


def write_development_owner_audit(source, *, action_id, generation, authorized_at_us,
                                  request_sha256, engine) -> str:
    """Create or reuse the one Control audit file; never silently overwrite one."""
    _assert_retained(source)
    if type(engine) is not EngineService or source._engine is not engine:
        raise _source_denied('The development Owner audit belongs to another Engine instance')
    folder = Path(engine.db.data_dir) / 'Control'
    path = folder / AUDIT_FILENAME
    body = _audit_document(source, action_id=action_id, generation=generation,
                           authorized_at_us=authorized_at_us, request_sha256=request_sha256, engine=engine)
    digest_hex = hashlib.sha256(body).hexdigest()
    try:
        if path.is_symlink() or path.is_junction():
            raise OSError('The audit path cannot cross filesystem links')
        if path.exists():
            existing = path.read_bytes()
            if existing == body:
                return digest_hex
            if len(existing) > _MAX_AUDIT_BYTES:
                raise OSError('The previous audit document exceeds its fixed bound')
            aborted = folder / ('DevelopmentOwnerInitialization.aborted-'
                                + hashlib.sha256(existing).hexdigest() + '.json')
            if aborted.exists():
                raise OSError('The retained aborted audit name already exists')
            path.rename(aborted)
        with path.open('xb') as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as error:
        raise _denied('development_owner_audit_unwritten',
                      'The development Owner audit could not be written; no Owner binding was written',
                      503) from error
    return digest_hex


def _canonical_audit_bytes(document: dict) -> bytes:
    body = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                      allow_nan=False).encode('utf-8') + b'\n'
    if len(body) > _MAX_AUDIT_BYTES:
        raise _denied('development_owner_audit_unwritten',
                      'The development Owner audit exceeds its fixed sixty-four kilobyte document bound', 503)
    return body


def _authorization_counts(engine) -> dict[str, int]:
    """Read-only proof that the authorization registry has no rows yet."""
    counts = {}
    try:
        with engine.db.connect_readonly() as connection:
            for table in _AUTHORIZATION_TABLES:
                counts[table] = int(connection.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0])
    except Exception as error:  # an unreadable registry is not provably empty
        raise _denied('development_control_state_denied',
                      'The authorization registry cannot be proven empty', 503) from error
    return counts


def _validate_production_control_record(record) -> None:
    if (type(record) is not dict
            or set(record) != {'created_at_us', 'recorded_at_us', 'floor', 'path', 'counts'}
            or type(record.get('created_at_us')) is not int or record.get('created_at_us') <= 0
            or type(record.get('recorded_at_us')) is not int or record.get('recorded_at_us') <= 0
            or type(record.get('floor')) is not int or record.get('floor') != 0
            or record.get('path') != _PRODUCTION_CONTROL_RELATIVE
            or type(record.get('counts')) is not dict
            or set(record.get('counts')) != set(_AUTHORIZATION_TABLES)
            or any(type(value) is not int or value != 0 for value in record['counts'].values())):
        raise _audit_changed('The development Owner audit production-control record is malformed')


def _append_audit_record(engine, name: str, record: dict) -> str:
    """Append one dev-only audit fact and commit its new digest to metadata."""
    document = _parse_audit(engine)
    existing = document.get(name)
    if existing is not None:
        if existing != record:
            raise _audit_changed('The development Owner audit already records a different ' + name)
        return hashlib.sha256(_canonical_audit_bytes(document)).hexdigest()
    document[name] = record
    body = _canonical_audit_bytes(document)
    digest_hex = hashlib.sha256(body).hexdigest()
    target = Path(engine.db.data_dir) / 'Control' / AUDIT_FILENAME
    temporary = target.with_name(AUDIT_FILENAME + '.pending')
    try:
        if target.is_symlink() or target.is_junction():
            raise OSError('The audit path cannot cross filesystem links')
        if temporary.exists():
            raise OSError('An earlier incomplete audit update must be resolved first')
        with temporary.open('xb') as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    except OSError as error:
        raise _denied('development_owner_audit_unwritten',
                      'The development Owner audit could not record the production control',
                      503) from error
    with engine.db.transaction() as connection:
        connection.execute('INSERT INTO metadata VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                           (AUDIT_METADATA_KEY, digest_hex))
    return digest_hex


def create_development_production_control(engine) -> dict | None:
    """Install the retained production authorization floor for a dev instance once.

    `assemble_owner_services` reads `Control/ProductionAuthorizationControl.json`
    on every start, but production installs that floor only inside an
    authenticated management/execution-registration action, which a development
    instance never performs. The development host therefore creates the empty
    first floor itself, and only when all of the following hold: this is the
    dev-only assembly path, the caller passed `--development-auto-owner-init`,
    the floor file does not exist, and the four authorization tables are
    provably empty. An existing floor is never overwritten or rebuilt.
    """
    if type(engine) is not EngineService:
        raise _source_denied('An actual EngineService is required')
    path = Path(engine.db.data_dir) / 'Control' / _PRODUCTION_CONTROL_FILENAME
    if path.is_symlink() or path.is_junction():
        raise _denied('development_control_state_denied',
                      'The retained production authorization floor cannot cross links', 503)
    if path.exists():
        return None
    counts = _authorization_counts(engine)
    if any(counts.values()):
        raise _denied('development_control_state_denied',
                      'The authorization registry is not empty; the retained production floor is never rebuilt: '
                      + json.dumps(counts, sort_keys=True), 503)
    control = ProductionAuthorizationControl(path, engine.instance_id)
    created_at_us = engine.clock()
    control.initialize_new()
    floor = control.read()
    if (floor.instance_id != engine.instance_id or floor.minimum_revision != 0
            or floor.pending_request_sha256 is not None):
        raise _denied('development_control_state_denied',
                      'The newly installed production floor is not the empty first floor', 503)
    record = {
        'created_at_us': created_at_us,
        'recorded_at_us': engine.clock(),
        'floor': 0,
        'path': _PRODUCTION_CONTROL_RELATIVE,
        'counts': counts,
    }
    _append_audit_record(engine, _PRODUCTION_CONTROL_RECORD, record)
    return record


def _parse_audit(engine) -> dict:
    try:
        with engine.db.connect() as connection:
            row = connection.execute('SELECT value FROM metadata WHERE key=?',
                                     (AUDIT_METADATA_KEY,)).fetchone()
    except Exception:  # noqa: BLE001 -- a database error is the same missing audit evidence
        raise _audit_missing('The development Owner audit digest is unavailable') from None
    if row is None or type(row[0]) is not str:
        raise _audit_missing('The development Owner initialization audit is required')
    path = Path(engine.db.data_dir) / 'Control' / AUDIT_FILENAME
    try:
        if path.is_symlink() or path.is_junction() or not path.is_file() or path.stat().st_size > _MAX_AUDIT_BYTES:
            raise _audit_missing('The development Owner initialization audit file is required')
        raw = path.read_bytes()
    except OSError:
        raise _audit_missing('The development Owner initialization audit file is required') from None
    if hashlib.sha256(raw).hexdigest() != row[0]:
        raise _audit_changed('The development Owner audit differs from its committed metadata digest')
    try:
        document = strict_json(raw)
    except (EngineError, TypeError):
        raise _audit_changed('The development Owner audit is not its canonical document') from None
    if type(document) is not dict or not _AUDIT_KEYS <= set(document):
        raise _audit_changed('The development Owner audit document is incomplete')
    if set(document) - (_AUDIT_KEYS | _OPTIONAL_AUDIT_KEYS):
        raise _audit_changed('The development Owner audit document has unknown fields')
    record = document.get(_PRODUCTION_CONTROL_RECORD)
    if record is not None:
        _validate_production_control_record(record)
    return document


def assert_development_owner_audit(engine, *, action_id, authentication_source, instance_id,
                                   owner_subject, project_ids, expires_at_us) -> None:
    """Every development start re-reads the audit file against its SQLite digest."""
    if authentication_source != DEVELOPMENT_AUTHENTICATION_SOURCE:
        return
    if type(engine) is not EngineService:
        raise _source_denied('An actual EngineService is required')
    document = _parse_audit(engine)
    projects = list(project_ids)
    binding = document.get('owner_binding')
    if (document.get('format') != AUDIT_FORMAT or document.get('action') != 'initialize'
            or document.get('action_key') != 'development-owner-initialize.' + digest(instance_id)
            or document.get('instance_id') != instance_id
            or document.get('owner_subject') != owner_subject
            or document.get('project_ids') != projects
            or document.get('expires_at_us') != expires_at_us
            or type(binding) is not dict
            or set(binding) != {'action_id', 'generation', 'authorized_at_us'}
            or binding.get('action_id') != action_id
            or type(binding.get('generation')) is not int or binding.get('generation') <= 0
            or type(binding.get('authorized_at_us')) is not int or binding.get('authorized_at_us') <= 0):
        raise _audit_changed('The development Owner audit does not describe the current binding')
    registration = document.get('registration')
    environment = document.get('environment')
    process = document.get('process')
    identity = document.get('os_identity')
    arguments = document.get('development_arguments')
    if (type(registration) is not dict
            or set(registration) != {'path', 'sha256', 'resource_manifest_sha256', 'runtime_manifest_sha256'}
            or type(environment) is not dict
            or environment != {'VIDEO_CREATOR_DEVELOPMENT_INSTALLATION': instance_id}
            or type(process) is not dict
            or set(process) != {'role', 'frozen', 'pid', 'executable', 'caller_module', 'thread_id'}
            or process.get('frozen') is not False
            or process.get('role') not in {'api', 'worker'}
            or process.get('caller_module') != _CALLER_MODULE
            or type(process.get('pid')) is not int or process.get('pid') <= 0
            or type(process.get('thread_id')) is not int or process.get('thread_id') <= 0
            or type(identity) is not dict
            or set(identity) != {'os_subject', 'administrator_id', 'directory_device', 'directory_inode'}
            or type(arguments) is not list or len(arguments) != len(_DEVELOPMENT_ARGUMENTS)
            or [pair[0] if type(pair) is list and len(pair) == 2 else None for pair in arguments]
            != list(_DEVELOPMENT_ARGUMENTS)
            or type(document.get('request_sha256')) is not str
            or type(document.get('created_at_us')) is not int or document.get('created_at_us') <= 0):
        raise _audit_changed('The development Owner audit does not describe this development process')
