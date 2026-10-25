#!/usr/bin/env python
"""Read-mostly probes for the local installation chain tests (development only).

Every subcommand prints exactly one JSON object on stdout and never writes product
state. The tests under `tests/development/` call these instead of re-implementing
product checks, so the same facts can be reproduced by hand from the evidence log.

Exit codes: 0 for a completed observation (even when it reports a refusal), 2 when
the probe itself could not run. No subcommand confirms an Owner action, patches a
hash or imports a model.

This module is part of `tools/testing/`; it is test tooling, not product code.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def _emit(payload) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with open(path, 'rb') as stream:
        while block := stream.read(1024 * 1024):
            hasher.update(block)
    return hasher.hexdigest()


def _repo_src(repo_root: str | None) -> Path:
    repo = Path(repo_root).resolve() if repo_root else Path(__file__).resolve().parents[2]
    source = repo / 'services' / 'engine' / 'src'
    if str(source) not in sys.path:
        sys.path.insert(0, str(source))
    return repo


def _principal_fields(principal) -> dict:
    """Owner/management principal fields, whatever the current exact schema name is."""
    fields = {}
    for name in ('instance_id', 'owner_subject', 'administrator_id', 'project_ids',
                 'authentication_binding_id', 'authentication_source', 'scope',
                 'expires_at_us'):
        fields[name] = getattr(principal, name, None)
    if type(fields['project_ids']) is tuple:
        fields['project_ids'] = list(fields['project_ids'])
    return fields


def owner_state(arguments) -> int:
    """Report the real Owner binding without ever creating or confirming one."""
    _repo_src(arguments.repo)
    from video_creator.application.engine import EngineService
    from video_creator.application.owner_bootstrap import OwnerBootstrapStore
    from video_creator.domain.errors import EngineError

    engine = EngineService(Path(arguments.data_dir).resolve())
    store = OwnerBootstrapStore(engine)
    result = {
        'ok': True,
        'instance_id': engine.instance_id,
        'data_dir': str(engine.db.data_dir),
        'owner_initialized': False,
        'owner_active': False,
    }
    try:
        with store.current(allow_inactive=True) as record:
            principal = record.principal
            result.update({
                'owner_initialized': True,
                'principal': _principal_fields(principal),
                'owner_subject': principal.owner_subject,
                'project_ids': list(principal.project_ids),
                'expires_at_us': principal.expires_at_us,
                'revoked': record.revoked,
                'generation': record.generation,
                'action_id': record.action_id,
            })
            if arguments.project_id:
                result['project_in_binding'] = arguments.project_id in principal.project_ids
    except EngineError as error:
        result.update({'error_code': error.code, 'message': error.message})
    try:
        with store.current(allow_inactive=False):
            result['owner_active'] = True
    except EngineError as error:
        result.setdefault('active_error_code', error.code)
        result.setdefault('active_error_message', error.message)
    _emit(result)
    return 0


def source_status(arguments) -> int:
    """Compare the registration's engine map with the actual current checkout bytes."""
    _repo_src(arguments.repo)
    from video_creator.application.media_registration import (
        PACKAGE_ROOT,
        _hash,
        _local_file,
        _package_sources,
    )

    registration = Path(arguments.registration).resolve()
    payload = json.loads(registration.read_text(encoding='utf-8'))
    declared = dict(payload['engine_source_sha256'])
    actual = sorted(_package_sources(PACKAGE_ROOT))
    current = {name: _hash(_local_file(PACKAGE_ROOT, name)) for name in actual}
    changed = sorted(name for name in set(declared) & set(current) if declared[name] != current[name])
    result = {
        'ok': not changed and set(declared) == set(current),
        'package_root': str(PACKAGE_ROOT),
        'registration': str(registration),
        'registration_sha256': _sha256(registration),
        'declared_count': len(declared),
        'current_count': len(current),
        'changed_files': changed,
        'missing_files': sorted(set(declared) - set(current)),
        'extra_files': sorted(set(current) - set(declared)),
    }
    _emit(result)
    return 0


def routes_state(arguments) -> int:
    """List registered routes and whether the four local route ids are present."""
    _repo_src(arguments.repo)
    from video_creator.application.engine import EngineService

    engine = EngineService(Path(arguments.data_dir).resolve())
    with engine.db.connect_readonly() as connection:
        ids = sorted(row['id'] for row in connection.execute('SELECT id FROM routes'))
        projects = sorted((row['id'], row['owner']) for row in connection.execute('SELECT id, owner FROM projects'))
    payload = json.loads(Path(arguments.registration).read_text(encoding='utf-8'))
    registration = payload['local_registration']
    expected = [registration['input_audio_route_id'], registration['input_visual_route_id'],
                registration['edit_route_id'], registration['master_index_route_id']]
    _emit({
        'ok': all(route_id in ids for route_id in expected),
        'registered_routes': ids,
        'expected_local_routes': expected,
        'missing_local_routes': [route_id for route_id in expected if route_id not in ids],
        'projects': [{'project_id': item[0], 'owner': item[1]} for item in projects],
        'instance_id': engine.instance_id,
    })
    return 0


def _control_state(engine) -> dict:
    """Control directory inventory, production floor record and audit digest match."""
    from video_creator.application import (
        development_owner_initialization as development,
    )
    from video_creator.domain.errors import EngineError

    root = Path(engine.db.data_dir) / 'Control'
    files = sorted(path.name for path in root.iterdir() if path.is_file()) if root.is_dir() else []
    state = {
        'control_dir': str(root),
        'control_dir_exists': root.is_dir(),
        'control_files': files,
        'audit_file': str(root / development.AUDIT_FILENAME),
        'audit_file_exists': (root / development.AUDIT_FILENAME).is_file(),
        'production_control_file': str(root / development._PRODUCTION_CONTROL_FILENAME),
        'production_control_exists': (root / development._PRODUCTION_CONTROL_FILENAME).is_file(),
        'authorization_counts': None,
        'production_control': None,
        'audit_sha256': None,
        'audit_metadata_digest': None,
        'audit_digest_matches': None,
        'audit': None,
        'audit_error': None,
    }
    try:
        state['authorization_counts'] = development._authorization_counts(engine)
    except EngineError as error:
        state['authorization_error'] = {'code': error.code, 'message': error.message}
    control_file = root / development._PRODUCTION_CONTROL_FILENAME
    if control_file.is_file():
        try:
            state['production_control'] = json.loads(control_file.read_text(encoding='utf-8'))
        except ValueError:
            state['production_control'] = '<invalid json>'
    audit_file = root / development.AUDIT_FILENAME
    if audit_file.is_file():
        state['audit_sha256'] = _sha256(audit_file)
    with engine.db.connect() as connection:
        row = connection.execute('SELECT value FROM metadata WHERE key=?',
                                 (development.AUDIT_METADATA_KEY,)).fetchone()
    state['audit_metadata_digest'] = row[0] if row is not None else None
    state['audit_digest_matches'] = (state['audit_sha256'] is not None
                                     and state['audit_sha256'] == state['audit_metadata_digest'])
    try:
        state['audit'] = development._parse_audit(engine)
    except EngineError as error:
        state['audit_error'] = {'code': error.code, 'message': error.message}
    return state


def _owner_snapshot(engine) -> dict:
    from video_creator.application.owner_bootstrap import OwnerBootstrapStore
    from video_creator.domain.errors import EngineError

    store = OwnerBootstrapStore(engine)
    snapshot = {'initialized': False, 'active': False}
    try:
        with store.current(allow_inactive=True) as record:
            snapshot.update({
                'initialized': True,
                'principal': _principal_fields(record.principal),
                'owner_subject': record.principal.owner_subject,
                'project_ids': list(record.principal.project_ids),
                'expires_at_us': record.principal.expires_at_us,
                'revoked': record.revoked,
                'generation': record.generation,
                'action_id': record.action_id,
            })
    except EngineError as error:
        snapshot.update({'error_code': error.code, 'message': error.message})
    try:
        with store.current(allow_inactive=False):
            snapshot['active'] = True
    except EngineError as error:
        snapshot.setdefault('active_error_code', error.code)
    return snapshot


def instance_state(arguments) -> int:
    """Everything a test needs to assert about one instance's Owner/control state."""
    _repo_src(arguments.repo)
    from video_creator.application.engine import EngineService

    engine = EngineService(Path(arguments.data_dir).resolve())
    with engine.db.connect_readonly() as connection:
        metadata_keys = sorted(row['key'] for row in connection.execute('SELECT key FROM metadata'))
        command_scopes = sorted(row['scope'] for row in connection.execute('SELECT DISTINCT scope FROM commands'))
        projects = [{'project_id': row['id'], 'owner': row['owner']}
                    for row in connection.execute('SELECT id, owner FROM projects ORDER BY rowid')]
    payload = {
        'ok': True,
        'instance_id': engine.instance_id,
        'data_dir': str(engine.db.data_dir),
        'metadata_keys': metadata_keys,
        'command_scopes': command_scopes,
        'projects': projects,
        'owner': _owner_snapshot(engine),
    }
    for key, value in _control_state(engine).items():
        payload[key] = value
    _emit(payload)
    return 0


def marker_health(arguments) -> int:
    """Exercise the in-process /health development marker on a throwaway instance.

    This is the same `create_app` production path; it is NOT a `serve-dev` process.
    It proves the header is process-internal and cannot be set by a request header.
    """
    _repo_src(arguments.repo)
    from fastapi.testclient import TestClient
    from video_creator.api.app import create_app
    from video_creator.api.development_marker import (
        DEVELOPMENT_INSTALLATION_HEADER,
        mark_development_host,
    )
    from video_creator.application.engine import EngineService

    scratch = Path(arguments.scratch_dir).resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    token = 'p' * 64
    application = create_app(EngineService(scratch), token)
    authorization = {'Authorization': 'Bearer ' + token}
    result = {'ok': True, 'data_dir': str(scratch)}
    with TestClient(application, base_url='http://127.0.0.1') as client:
        before = client.get('/api/v1/health', headers=authorization)
        result['unmarked'] = {'status': before.status_code,
                              'development_header': before.headers.get(DEVELOPMENT_INSTALLATION_HEADER)}
        mark_development_host()
        forged = dict(authorization)
        forged[DEVELOPMENT_INSTALLATION_HEADER] = 'forged-by-caller'
        after = client.get('/api/v1/health', headers=forged)
        result['marked'] = {
            'status': after.status_code,
            'development_header': after.headers.get(DEVELOPMENT_INSTALLATION_HEADER),
            'body': after.json(),
        }
        responses = application.openapi()['paths']['/api/v1/health']['get'].get('responses', {})
        declared = {header for response in responses.values()
                    for header in response.get('headers', {})}
        result['openapi_declares_development_header'] = DEVELOPMENT_INSTALLATION_HEADER in declared
    _emit(result)
    return 0


def unattended_guards(arguments) -> int:
    """Run the development host's own unattended refusals on inert stubs.

    Process-internal seam: proof that the dev host refuses unattended before the
    policy branch, not an HTTP end-to-end observation.
    """
    _repo_src(arguments.repo)
    from video_creator.cli import development_host as dev
    from video_creator.domain.errors import EngineError

    def outcome(callback):
        try:
            value = callback()
        except EngineError as error:
            return {'outcome': 'error', 'code': error.code, 'status_code': error.status_code,
                    'message': error.message}
        return {'outcome': 'accepted', 'value': repr(value)}

    class AcceptanceBundle:
        def __init__(self):
            self.calls = 0

        def create_production(self, actor, key, request):
            self.calls += 1
            return 'accepted'

    class ExecutionRuntime:
        def __init__(self):
            self.calls = 0

        def invoke(self, lease, *, cancel=None, deadline_monotonic=None):
            self.calls += 1
            return 'invoked'

    class Mode:
        def __init__(self, mode):
            self.mode = mode

    class Request:
        def __init__(self, mode):
            self.automation = Mode(mode)

    acceptance = AcceptanceBundle()
    dev._guard_acceptance(acceptance)
    unattended_accept = outcome(lambda: acceptance.create_production('actor', 'key', Request('unattended')))
    acceptance_calls_after_unattended = acceptance.calls
    interactive_accept = outcome(lambda: acceptance.create_production('actor', 'key', Request('interactive')))

    execution = ExecutionRuntime()
    engine_stub = type('Engine', (), {'get_request': staticmethod(lambda lease: Request('unattended'))})()
    dev._guard_execution(execution, engine_stub)
    unattended_execution = outcome(lambda: execution.invoke('lease'))

    goal_bundle = AcceptanceBundle()
    dev._guard_goal_creation(goal_bundle)
    goal = outcome(lambda: goal_bundle.create_project_goal('actor', 'key', 'goal', entry='api'))

    _emit({
        'ok': True,
        'require_interactive_unattended': outcome(lambda: dev.require_interactive('unattended')),
        'require_interactive_interactive': outcome(lambda: dev.require_interactive('interactive')),
        'acceptance_unattended': unattended_accept,
        'acceptance_original_calls_after_unattended': acceptance_calls_after_unattended,
        'acceptance_interactive': interactive_accept,
        'execution_unattended': unattended_execution,
        'execution_original_calls_after_unattended': execution.calls,
        'goal_creation': goal,
    })
    return 0


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', default=None, help='repository root (default: inferred)')
    commands = parser.add_subparsers(dest='command', required=True)

    owner = commands.add_parser('owner-state')
    owner.add_argument('--data-dir', required=True)
    owner.add_argument('--project-id')
    owner.set_defaults(handler=owner_state)

    source = commands.add_parser('source-status')
    source.add_argument('--registration', required=True)
    source.set_defaults(handler=source_status)

    routes = commands.add_parser('routes-state')
    routes.add_argument('--data-dir', required=True)
    routes.add_argument('--registration', required=True)
    routes.set_defaults(handler=routes_state)

    instance = commands.add_parser('instance-state')
    instance.add_argument('--data-dir', required=True)
    instance.set_defaults(handler=instance_state)

    marker = commands.add_parser('marker-health')
    marker.add_argument('--scratch-dir', required=True)
    marker.set_defaults(handler=marker_health)

    guards = commands.add_parser('unattended-guards')
    guards.set_defaults(handler=unattended_guards)

    arguments = parser.parse_args(argv)
    return arguments.handler(arguments)


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
