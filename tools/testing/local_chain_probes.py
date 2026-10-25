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
                'owner_subject': principal.owner_subject,
                'executing_principal_id': principal.executing_principal_id,
                'project_ids': list(principal.project_ids),
                'expires_at_us': principal.expires_at_us,
                'revoked': record.revoked,
                'generation': record.generation,
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
    policy branch, not an HTTP end-to-end observation (that needs a real Owner).
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

    marker = commands.add_parser('marker-health')
    marker.add_argument('--scratch-dir', required=True)
    marker.set_defaults(handler=marker_health)

    guards = commands.add_parser('unattended-guards')
    guards.set_defaults(handler=unattended_guards)

    arguments = parser.parse_args(argv)
    return arguments.handler(arguments)


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
