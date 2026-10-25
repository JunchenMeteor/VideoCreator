#!/usr/bin/env python
"""Deterministic development-registration fixture for the local chain tests.

The integration hand-off slice (`Integration/LocalInstallationRegistrationBuild`)
binds the engine-source hashes of the commit it was built from. Once product
source moves on, every `serve-dev`/`worker-dev` start is refused with
`development_code_changed`/`production_code_changed`, so the negative and
positive cases can no longer reach the behaviour they assert.

This module rebuilds that slice **in the test role's own process directory** with
the official builder (`build_local_registration.py` + `check_local_registration.py`,
byte-copied from the hand-off and re-copied when they change), against the current
checkout and a copy of a clean instance. It never writes to the integration
directory and never edits product source.

Freshness is decided by re-implementing the installer's own rule: the set and
byte hashes of `_package_sources(PACKAGE_ROOT)`. If they equal the fixture
registration the build is reused; otherwise the fixture is regenerated and its
stdout/stderr/exit are preserved under `<fixture>/logs/`.

CLI (also used by `RunLocalChainE2E.ps1`):

    python tools/testing/local_chain_fixture.py ensure --json
    python tools/testing/local_chain_fixture.py status --json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINE_SRC = REPO_ROOT / 'services' / 'engine' / 'src'
DEFAULT_PYTHON = REPO_ROOT / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
PYTHON = Path(os.environ.get('VIDEO_CREATOR_PYTHON') or DEFAULT_PYTHON)

DEFAULT_INTEGRATION = Path(os.environ.get('VIDEO_CREATOR_LOCAL_INTEGRATION')
                           or r'G:/开发测试/Codex/VideoCreatorImplementation/Integration/LocalInstallationRegistrationBuild')
DEFAULT_FIXTURE = Path(os.environ.get('VIDEO_CREATOR_LOCAL_FIXTURE')
                       or r'G:/开发测试/Codex/VideoCreatorImplementation/Test/LocalChainEndToEnd/Fixture')
DEFAULT_TEMPLATE = Path(os.environ.get('VIDEO_CREATOR_LOCAL_TEMPLATE')
                        or r'G:/开发测试/Codex/VideoCreatorImplementation/Backend/DevelopmentOwnerAutoInit/Instance/Template')

BUILDER = 'build_local_registration.py'
CHECKER = 'check_local_registration.py'
BASE_INSTANCE = 'BaseInstance'


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with open(path, 'rb') as stream:
        while block := stream.read(1024 * 1024):
            hasher.update(block)
    return hasher.hexdigest()


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec='seconds')


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + '\n',
                    encoding='utf-8', newline='\n')


def read_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def _with_engine():
    source = str(ENGINE_SRC)
    if source not in sys.path:
        sys.path.insert(0, source)
    from video_creator.application.media_registration import (
        PACKAGE_ROOT,
        _hash,
        _local_file,
        _package_sources,
    )

    return PACKAGE_ROOT, _hash, _local_file, _package_sources


def current_engine_map() -> dict[str, str]:
    """(relative path, sha256) of every engine package source, the installer's way."""
    package_root, _hash, _local_file, _package_sources = _with_engine()
    return {name: _hash(_local_file(package_root, name))
            for name in sorted(_package_sources(package_root))}


def registration_engine_map(registration: Path) -> dict[str, str]:
    return dict(read_json(registration)['engine_source_sha256'])


def is_fresh(fixture_root: Path) -> tuple[bool, str]:
    registration = Path(fixture_root) / 'Registration.json'
    if not registration.is_file():
        return False, 'fixture registration missing'
    payload = read_json(registration)
    declared = dict(payload['engine_source_sha256'])
    current = current_engine_map()
    if set(declared) != set(current):
        return False, (f'engine source set differs (declared={len(declared)} current={len(current)}, '
                       f'missing={sorted(set(declared) - set(current))[:5]}, '
                       f'extra={sorted(set(current) - set(declared))[:5]})')
    changed = sorted(name for name in current if declared[name] != current[name])
    if changed:
        return False, f'{len(changed)} engine source file(s) changed: {changed[:8]}'
    root = registration.parent
    for name, expected in ((payload['production_resource_manifest'], payload['production_resource_manifest_sha256']),
                           (payload['ffmpeg'], payload['ffmpeg_sha256']),
                           (payload['ffprobe'], payload['ffprobe_sha256'])):
        candidate = root.joinpath(*name.split('/'))
        if not candidate.is_file():
            return False, f'fixture resource missing: {name}'
        if sha256_file(candidate) != expected:
            return False, f'fixture resource changed: {name}'
    runtime = root / 'Package' / 'RuntimeFileManifest.json'
    if not runtime.is_file() or sha256_file(runtime) != payload['production_runtime_manifest_sha256']:
        return False, 'fixture runtime manifest missing or changed'
    return True, 'fixture registration matches the current checkout'


def _sid() -> str:
    completed = subprocess.run(['whoami', '/user'], capture_output=True, text=True, timeout=60, check=False)
    parts = completed.stdout.split()
    for part in parts:
        if part.startswith('S-1-') and part.count('-') >= 5:
            return part
    raise RuntimeError('could not determine the current Windows SID: ' + completed.stdout)


def apply_acl(path: Path) -> None:
    """Owner-only directory, matching `inspect_owner_directory` on Windows."""
    sid = _sid()
    subprocess.run(['icacls', str(path), '/inheritance:r'], capture_output=True, check=True, timeout=120)
    subprocess.run(['icacls', str(path), '/grant:r', f'*{sid}:(OI)(CI)F', '*S-1-5-18:(OI)(CI)F'],
                   capture_output=True, check=True, timeout=120)


def instance_id(path: Path) -> str:
    connection = sqlite3.connect(Path(path) / 'Metadata.sqlite', timeout=30)
    try:
        row = connection.execute("SELECT value FROM metadata WHERE key='instance_id'").fetchone()
    finally:
        connection.close()
    if row is None or type(row[0]) is not str:
        raise RuntimeError(f'instance has no instance_id metadata: {path}')
    return row[0]


def instance_project_id(path: Path, owner: str = 'local-user') -> str:
    connection = sqlite3.connect(Path(path) / 'Metadata.sqlite', timeout=30)
    try:
        row = connection.execute('SELECT id FROM projects WHERE owner=? ORDER BY rowid LIMIT 1',
                                 (owner,)).fetchone()
    finally:
        connection.close()
    if row is None:
        raise RuntimeError(f'instance has no {owner} project: {path}')
    return row[0]


def strip_owner_state(path: Path) -> None:
    """Turn an initialized instance copy into a first-start instance.

    Only removes Owner artefacts (Control directory, the binding/audit metadata
    rows and the owner command receipts); projects, routes and assets stay.
    """
    control = Path(path) / 'Control'
    if control.exists():
        shutil.rmtree(control)
    connection = sqlite3.connect(Path(path) / 'Metadata.sqlite', timeout=30)
    try:
        connection.execute("DELETE FROM metadata WHERE key IN "
                           "('owner_management_binding','development_owner_initialization_audit')")
        connection.execute("DELETE FROM commands WHERE scope LIKE 'owner.%'")
        connection.commit()
    finally:
        connection.close()


def _copy_script(source: Path, destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file() and destination.read_bytes() == source.read_bytes():
        return sha256_file(destination)
    shutil.copy2(source, destination)
    return sha256_file(destination)


def _copy_tree(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)


def ensure_base_instance(fixture_root: Path, integration: Path, template: Path) -> tuple[Path, str]:
    base = Path(fixture_root) / BASE_INSTANCE
    if base.is_dir() and (base / 'Metadata.sqlite').is_file():
        apply_acl(base)
        return base, 'existing'
    if template.is_dir() and (template / 'Metadata.sqlite').is_file():
        _copy_tree(template, base)
        provenance = f'copied from clean template {template}'
    else:
        source = integration / 'Instance' / 'ChainInstance'
        if not (source / 'Metadata.sqlite').is_file():
            raise RuntimeError(f'no clean template and no integration instance available: {source}')
        _copy_tree(source, base)
        strip_owner_state(base)
        provenance = f'copied from integration instance and stripped of Owner state: {source}'
    apply_acl(base)
    return base, provenance


def _json_object(text: str):
    """The builder prints one (possibly pretty-printed) JSON object; decode it."""
    start = text.find('{')
    if start < 0:
        return None
    try:
        value, _end = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _build(fixture_root: Path, integration: Path, base: Path, project_id: str) -> dict:
    logs = Path(fixture_root) / 'logs'
    logs.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')
    stdout_path = logs / f'build-{stamp}.stdout.bin'
    stderr_path = logs / f'build-{stamp}.stderr.bin'
    command = [str(PYTHON), str(Path(fixture_root) / BUILDER),
               '--repo', str(REPO_ROOT),
               '--instance-dir', str(base),
               '--project-id', project_id,
               '--skip-runtime-check']
    environment = dict(os.environ)
    for key in ('VIDEO_CREATOR_DEVELOPMENT_INSTALLATION', 'VIDEO_CREATOR_API_TOKEN'):
        environment.pop(key, None)
    environment.update({'PYTHONPATH': str(ENGINE_SRC), 'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8'})
    started = _now()
    with open(stdout_path, 'wb') as stdout, open(stderr_path, 'wb') as stderr:
        completed = subprocess.run(command, cwd=str(fixture_root), env=environment,
                                   stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                   timeout=1800, check=False)
    finished = _now()
    payload = _json_object(stdout_path.read_text(encoding='utf-8', errors='replace'))
    record = {
        'command': command,
        'cwd': str(fixture_root),
        'exit': completed.returncode,
        'started_at': started,
        'finished_at': finished,
        'stdout': str(stdout_path),
        'stderr': str(stderr_path),
        'result': payload,
    }
    _write_json(logs / f'build-{stamp}.json', record)
    if completed.returncode != 0 or not payload or payload.get('ok') is not True:
        stderr_text = stderr_path.read_text(encoding='utf-8', errors='replace')[-2000:]
        raise RuntimeError(
            f'fixture registration build failed with exit {completed.returncode}; '
            f'raw output: {stdout_path} / {stderr_path}\nstderr: {stderr_text}')
    return record


def ensure(*, fixture_root: Path = DEFAULT_FIXTURE, integration: Path = DEFAULT_INTEGRATION,
           template: Path = DEFAULT_TEMPLATE, force: bool = False) -> dict:
    """Make the fixture registration current for this checkout and return its facts."""
    fixture_root = Path(fixture_root)
    fixture_root.mkdir(parents=True, exist_ok=True)
    builder_sha = _copy_script(Path(integration) / BUILDER, fixture_root / BUILDER)
    checker_sha = _copy_script(Path(integration) / CHECKER, fixture_root / CHECKER)
    base, instance_provenance = ensure_base_instance(fixture_root, integration, template)
    project_id = instance_project_id(base)

    fresh, reason = is_fresh(fixture_root)
    build = None
    if force or not fresh:
        prev = fixture_root / 'Registration.json'
        if prev.is_file():
            try:
                project_id = read_json(prev)['local_registration']['rights_declaration']['project_ids'][0]
            except (ValueError, KeyError, IndexError):
                pass
        build = _build(fixture_root, integration, base, project_id)
        fresh, reason = is_fresh(fixture_root)
        if not fresh:
            # The product can move while the builder copies it; one retry is enough
            # to distinguish a concurrent edit from a genuinely broken fixture.
            build = _build(fixture_root, integration, base, project_id)
            fresh, reason = is_fresh(fixture_root)
        if not fresh:
            raise RuntimeError('fixture registration is still stale after two rebuilds: ' + reason)

    registration = fixture_root / 'Registration.json'
    payload = read_json(registration)
    return {
        'ok': True,
        'fixture_root': str(fixture_root),
        'registration': str(registration),
        'registration_sha256': sha256_file(registration),
        'registration_bytes': registration.stat().st_size,
        'engine_source_count': len(payload['engine_source_sha256']),
        'project_id': project_id,
        'base_instance': str(base),
        'base_instance_id': instance_id(base),
        'instance_provenance': instance_provenance,
        'template': str(template),
        'integration': str(integration),
        'builder': str(fixture_root / BUILDER),
        'builder_sha256': builder_sha,
        'checker_sha256': checker_sha,
        'fresh': fresh,
        'freshness': reason,
        'rebuilt': build is not None,
        'build_exit': None if build is None else build['exit'],
        'build_log': None if build is None else build['stdout'].replace('.stdout.bin', '.json'),
        'package_bytes': sum(path.stat().st_size for path in (fixture_root / 'Package').rglob('*')
                             if path.is_file()),
        'checked_at': _now(),
    }


def new_instance(evidence: Path, name: str, *, source: Path | None = None,
                 base: Path | None = None, clean: bool = True) -> Path:
    """Copy a base instance into the evidence folder and restrict its ACL."""
    destination = Path(evidence) / 'instances' / name
    if destination.exists():
        shutil.rmtree(destination)
    origin = Path(source) if source is not None else Path(base if base is not None
                                                          else DEFAULT_FIXTURE / BASE_INSTANCE)
    _copy_tree(origin, destination)
    if clean and source is None:
        strip_owner_state(destination)
    apply_acl(destination)
    return destination


def status(*, fixture_root: Path = DEFAULT_FIXTURE) -> dict:
    fixture_root = Path(fixture_root)
    fresh, reason = is_fresh(fixture_root)
    registration = fixture_root / 'Registration.json'
    return {
        'ok': registration.is_file(),
        'fixture_root': str(fixture_root),
        'registration': str(registration),
        'registration_sha256': sha256_file(registration) if registration.is_file() else None,
        'fresh': fresh,
        'freshness': reason,
    }


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture-root', default=str(DEFAULT_FIXTURE))
    parser.add_argument('--integration', default=str(DEFAULT_INTEGRATION))
    parser.add_argument('--template', default=str(DEFAULT_TEMPLATE))
    commands = parser.add_subparsers(dest='command', required=True)
    ensure_command = commands.add_parser('ensure')
    ensure_command.add_argument('--force', action='store_true')
    commands.add_parser('status')
    arguments = parser.parse_args(argv)
    if arguments.command == 'status':
        print(json.dumps(status(fixture_root=Path(arguments.fixture_root)), ensure_ascii=False,
                         sort_keys=True))
        return 0
    try:
        facts = ensure(fixture_root=Path(arguments.fixture_root),
                       integration=Path(arguments.integration),
                       template=Path(arguments.template),
                       force=arguments.force)
    except Exception as error:  # noqa: BLE001 -- the CLI reports the exact failure
        print(json.dumps({'ok': False, 'error': f'{error}'}, ensure_ascii=False, sort_keys=True),
              file=sys.stderr)
        return 1
    print(json.dumps(facts, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
