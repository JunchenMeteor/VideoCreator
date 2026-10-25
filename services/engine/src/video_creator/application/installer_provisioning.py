"""ADR0083 installer provisioning: configuration facts only, never authorization."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

from video_creator.application.engine import EngineService, canonical
from video_creator.application.media_registration import (
    PACKAGE_ROOT,
    _hash,
    _local_file,
    _package_sources,
)
from video_creator.application.production_management import (
    ProductionAuthorizationControl,
)
from video_creator.domain import contracts as c
from video_creator.domain.errors import EngineError
from video_creator.domain.local_material_production import (
    parse_local_registration_config,
)

FORMAT = 'installation-provisioning-v1'
RECORD_NAME = 'InstallationProvisioning.json'
OWNER = 'local-user'
PROJECT_NAME = 'Local Project'
EMPTY_TABLES = ('production_authorization_policies', 'production_admissions',
                'daily_project_authorizations', 'execution_registrations')


def _fail(code: str, message: str, status: int = 409) -> None:
    raise EngineError(code, message, status)


def _absolute_local(path: Path, label: str) -> Path:
    candidate = Path(path)
    if (not candidate.is_absolute() or str(candidate).startswith(('\\\\', '//'))
            or candidate.is_symlink() or candidate.is_junction()):
        _fail('installation_provisioning_denied',
              f'{label} must be one absolute non-link local directory', 403)
    return candidate


def _apply_acl(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    if os.name != 'nt':
        directory.chmod(0o700)
        return
    user = os.environ.get('USERNAME')
    if not user:
        _fail('installation_provisioning_unavailable', 'Current Windows user is unavailable', 503)
    try:
        subprocess.run(['icacls', str(directory), '/inheritance:r'], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(['icacls', str(directory), '/grant:r', f'{user}:(OI)(CI)F',
                        'SYSTEM:(OI)(CI)F'], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (OSError, subprocess.CalledProcessError):
        _fail('installation_provisioning_unavailable',
              'The instance ACL could not be restricted to the current user and SYSTEM', 503)


def _registration(path: Path) -> tuple[dict, str, Path]:
    raw = path.read_bytes()
    if not raw or len(raw) > 1024 * 1024:
        _fail('installation_provisioning_unavailable', 'Registration file is missing or outside its bound', 503)
    sha = hashlib.sha256(raw).hexdigest()
    try:
        config = parse_local_registration_config(raw)
    except (ValueError, TypeError):
        _fail('installation_provisioning_denied', 'Registration is not the trusted local-v1 grammar', 403)
    actual = {name: _hash(_local_file(PACKAGE_ROOT, name)) for name in _package_sources(PACKAGE_ROOT)}
    if set(config.engine_source_sha256) != set(actual) or any(
            config.engine_source_sha256[name] != actual[name] for name in actual):
        _fail('installation_registration_stale',
              'Registration engine hashes differ from the actual installed engine bytes', 503)
    root = path.resolve().parent
    resources = ((config.ffmpeg, config.ffmpeg_sha256), (config.ffprobe, config.ffprobe_sha256),
                 (config.production_resource_manifest, config.production_resource_manifest_sha256))
    if config.asr_resource_manifest is not None:
        resources += ((config.asr_resource_manifest, config.asr_resource_manifest_sha256),)
    for relative, expected in resources:
        installed = _local_file(root, relative)
        if _hash(installed) != expected:
            _fail('installation_registration_stale', f'Installed registration resource {relative} changed', 503)
    resources_doc = json.loads(_local_file(root, config.production_resource_manifest).read_text(encoding='utf-8'))
    runtime_index = _local_file(_local_file(root, config.production_resource_manifest).parent,
                                resources_doc['runtime_manifest'])
    if _hash(runtime_index) != config.production_runtime_manifest_sha256:
        _fail('installation_registration_stale', 'Installed local runtime index changed', 503)
    return config, sha, root


def _route_files(root: Path, config) -> dict[str, c.CapabilityRoute]:
    folder = root / 'Routes'
    if folder.is_symlink() or not folder.is_dir():
        _fail('installation_provisioning_incomplete', 'Registration root has no Routes directory', 503)
    expected = {config.local_registration.input_audio_route_id,
                config.local_registration.input_visual_route_id,
                config.local_registration.edit_route_id,
                config.local_registration.master_index_route_id}
    if config.asr_route_id is not None:
        expected.add(config.asr_route_id)
    routes = {}
    for path in sorted(folder.glob('*.json')):
        try:
            route = c.CapabilityRoute.model_validate_json(path.read_bytes())
        except (ValueError, TypeError):
            _fail('installation_provisioning_denied', f'Route file {path.name} is not a CapabilityRoute', 403)
        if route.route_id in routes:
            _fail('installation_provisioning_denied', f'Duplicate route id {route.route_id}', 403)
        if (route.source != 'owned_local' or route.credential_ref is not None
                or route.max_operation_cost.units() or not route.destination.startswith('local:')
                or route.verified is not True):
            _fail('installation_provisioning_denied',
                  f'Route {route.route_id} is not a verified zero-cost local route', 403)
        routes[route.route_id] = route
    if set(routes) != expected:
        _fail('installation_provisioning_incomplete',
              'Route files do not exactly match the registration route ids', 503)
    return routes


def _empty_tables(connection) -> bool:
    return all(connection.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] == 0
               for table in EMPTY_TABLES)


def _project(connection, project_id: str, now_us: int) -> dict:
    row = connection.execute('SELECT id,owner,body FROM projects WHERE id=?', (project_id,)).fetchone()
    if row is not None:
        if row['owner'] != OWNER:
            _fail('installation_provisioning_conflict', 'Registration project belongs to another owner', 409)
        return {'project_id': row['id'], 'created': False}
    body = canonical(c.ProjectInput(name=PROJECT_NAME))
    connection.execute('INSERT INTO projects(id,owner,body,saved_at_us) VALUES(?,?,?,?)',
                       (project_id, OWNER, body, now_us))
    # EngineService.clock() is monotonic microseconds; saved_at only needs a real
    # positive integer, and the writer uses the same clock source.
    return {'project_id': project_id, 'created': True}


def _record_path(control: Path) -> Path:
    return control / RECORD_NAME


def _write_record(control: Path, body: dict) -> None:
    data = (json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode('utf-8')
    pending = _record_path(control).with_suffix('.pending')
    if pending.is_symlink() or _record_path(control).is_symlink():
        _fail('installation_provisioning_denied', 'Provisioning record cannot cross links', 403)
    with pending.open('wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(pending, _record_path(control))


def provision(*, install_dir: Path, data_dir: Path, registration: Path) -> dict:
    install = _absolute_local(install_dir, 'Install directory')
    data = _absolute_local(data_dir, 'Instance data directory')
    if not install.is_dir():
        _fail('installation_provisioning_unavailable', 'Install directory does not exist', 503)
    registration = Path(registration)
    if not registration.is_absolute() or registration.is_symlink() or not registration.is_file():
        _fail('installation_provisioning_unavailable', 'Registration must be one absolute existing file', 503)
    config, registration_sha256, registration_root = _registration(registration)
    required_project = config.local_registration.rights_declaration.project_ids
    if len(required_project) != 1 or config.local_registration.rights_declaration.declaring_subject != OWNER:
        _fail('installation_provisioning_denied',
              'Registration must declare exactly one local-user project', 403)
    project_id = required_project[0]
    existing_record = data / 'Control' / RECORD_NAME
    if existing_record.is_file():
        try:
            existing = json.loads(existing_record.read_text(encoding='utf-8'))
        except (ValueError, TypeError):
            _fail('installation_provisioning_conflict', 'Existing provisioning record is damaged', 409)
        if (existing.get('format') != FORMAT
                or existing.get('registration_sha256') != registration_sha256
                or existing.get('project_id') != project_id):
            _fail('installation_provisioning_conflict',
                  'Existing provisioning record binds different install bytes or project', 409)
    routes = _route_files(registration_root, config)

    _apply_acl(data)
    control = data / 'Control'
    _apply_acl(control)
    engine = EngineService(data)
    record = _record_path(control)
    if record.is_file():
        try:
            existing = json.loads(record.read_text(encoding='utf-8'))
        except (ValueError, TypeError):
            _fail('installation_provisioning_conflict', 'Existing provisioning record is damaged', 409)
        if (existing.get('format') != FORMAT or existing.get('instance_id') != engine.instance_id
                or existing.get('registration_sha256') != registration_sha256
                or existing.get('project_id') != project_id
                or sorted(existing.get('route_ids', [])) != sorted(routes)):
            _fail('installation_provisioning_conflict',
                  'Existing provisioning record binds different install bytes or instance', 409)
        return {'status': 'already_provisioned', 'record': existing, 'registration_sha256': registration_sha256}

    with engine.db.transaction() as connection:
        if not _empty_tables(connection):
            _fail('installation_provisioning_denied',
                  'Provisioning requires the four authorization tables to be empty', 403)
        binding = connection.execute("SELECT 1 FROM metadata WHERE key='owner_management_binding'").fetchone()
        if binding is not None:
            _fail('installation_provisioning_denied', 'An Owner binding already exists; use repair, not provision', 403)
        project = _project(connection, project_id, engine.clock())
        for route in routes.values():
            connection.execute('INSERT INTO routes(id,body) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body',
                               (route.route_id, canonical(route)))
    floor = ProductionAuthorizationControl(control / 'ProductionAuthorizationControl.json', engine.instance_id)
    if floor.path.exists():
        existing_floor = floor.read()
        if existing_floor.minimum_revision != 0 or existing_floor.pending_request_sha256 is not None:
            _fail('installation_provisioning_denied',
                  'Existing production floor is not the zero-authority empty floor', 403)
        floor_state = 'adopted'
    else:
        floor.initialize_new()
        floor_state = 'created'
    with engine.db.connect() as connection:
        if not _empty_tables(connection):
            _fail('installation_provisioning_conflict',
                  'Authorization rows appeared during provisioning; refuse to claim completion', 409)
    body = {
        'format': FORMAT,
        'complete': True,
        'installer_version': c.CONTRACT_SET_VERSION,
        'provisioned_at_us': engine.clock(),
        'instance_id': engine.instance_id,
        'project_id': project_id,
        'registration_sha256': registration_sha256,
        'route_ids': sorted(routes),
        'items': [
            {'id': 'registration', 'sha256': registration_sha256},
            {'id': 'project', 'project_id': project_id, 'created': project['created']},
            {'id': 'production_floor', 'minimum_revision': 0, 'state': floor_state,
             'sha256': _hash(floor.path)},
            *[{'id': 'route:' + route_id, 'route_id': route_id}
              for route_id in sorted(routes)],
        ],
        'counts': {'routes': len(routes), 'projects': 1, 'authorization_rows': 0},
        'revision': 1,
    }
    _write_record(control, body)
    checks = verify_provisioning(data_dir=data, registration=registration, record=body)
    return {'status': 'provisioned', 'record': body, 'registration_sha256': registration_sha256,
            'checks': checks}


def verify_provisioning(*, data_dir: Path, registration: Path, record: dict) -> dict:
    """V1–V4: record self-consistency, real registration/runtime, routes, empty floor."""
    from video_creator.application.media_registration import RegisteredMediaRuntime

    engine = EngineService(data_dir)
    if (record.get('format') != FORMAT or record.get('complete') is not True
            or record.get('instance_id') != engine.instance_id
            or record.get('registration_sha256') != hashlib.sha256(Path(registration).read_bytes()).hexdigest()):
        _fail('installation_provisioning_incomplete', 'V1 provisioning record is not self-consistent', 503)
    config = parse_local_registration_config(Path(registration).read_bytes())
    # V2: real local runtime construction against the same installed bytes.
    RegisteredMediaRuntime(engine, Path(registration), record['registration_sha256'],
                           resource_manifest_hashes=frozenset())
    expected = {config.local_registration.input_audio_route_id, config.local_registration.input_visual_route_id,
                config.local_registration.edit_route_id, config.local_registration.master_index_route_id}
    if config.asr_route_id is not None:
        expected.add(config.asr_route_id)
    with engine.db.connect_readonly() as connection:
        rows = connection.execute('SELECT id FROM routes ORDER BY id').fetchall()
        route_ids = {row[0] for row in rows}
        if route_ids != expected:
            _fail('installation_provisioning_incomplete', 'V3 route rows differ from the registration', 503)
        if not _empty_tables(connection):
            _fail('installation_provisioning_incomplete', 'V4 authorization tables are not empty', 503)
        project = connection.execute('SELECT owner FROM projects WHERE id=?', (record['project_id'],)).fetchone()
        if project is None or project['owner'] != OWNER:
            _fail('installation_provisioning_incomplete', 'V4 project row is missing or foreign', 503)
    floor = ProductionAuthorizationControl(data_dir / 'Control' / 'ProductionAuthorizationControl.json',
                                          engine.instance_id).read()
    if floor.minimum_revision != 0 or floor.pending_request_sha256 is not None:
        _fail('installation_provisioning_incomplete', 'V4 production floor is not the empty floor', 503)
    return {'V1_record': 'ok', 'V2_registration_runtime': 'ok', 'V3_routes': sorted(route_ids),
            'V4_empty_floor': 'ok'}
