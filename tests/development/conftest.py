"""Fixtures for the real local installation chain tests.

One pytest run writes one evidence directory; raw child bytes, argv and exit codes
live there and are never rewritten. Tests are written to run individually
(`pytest tests/development/test_development_host_negatives.py -k env`) without any
other fixture or plugin.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import local_chain_support as support
import pytest


def pytest_report_header(config) -> str:
    lines = [f'local chain installation: {support.INSTALLATION}',
             f'local chain evidence root: {support.EVIDENCE_ROOT}']
    return '\n'.join(lines)


@pytest.fixture(scope='session')
def evidence() -> Path:
    stamp = datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')
    folder = support.EVIDENCE_ROOT / f'{stamp}-pytest-{os.getpid()}'
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'session.txt').write_text(
        f'created={support.utc_now()}\npid={os.getpid()}\nrepo={support.REPO_ROOT}\n',
        encoding='utf-8', newline='\n')
    return folder


@pytest.fixture(scope='session')
def installation() -> dict:
    missing = [str(path) for path in (support.INSTALLATION, support.REGISTRATION,
                                      support.INSTANCE, support.PACKAGE, support.FFMPEG,
                                      support.FFPROBE) if not path.exists()]
    if missing:
        pytest.skip('The frozen local installation slice is unavailable; missing: '
                    + ', '.join(missing)
                    + '\nRegenerate it with the integration hand-off build before running these tests.')
    return {
        'installation': support.INSTALLATION,
        'registration': support.REGISTRATION,
        'registration_sha256': support.registration_sha256(),
        'instance': support.INSTANCE,
        'package': support.PACKAGE,
        'ffmpeg': support.FFMPEG,
        'ffprobe': support.FFPROBE,
        'project_id': support.project_id(),
        'route_ids': support.route_ids(),
    }


@pytest.fixture(scope='session')
def session_facts(evidence, installation) -> dict:
    facts = {
        'started_at': support.utc_now(),
        'git_head': support.git_head(),
        'git_status': support.git_status(evidence),
        'registration': str(support.REGISTRATION),
        'registration_sha256': support.registration_sha256(),
        'registration_bytes': support.REGISTRATION.stat().st_size,
        'instance': str(support.INSTANCE),
        'project_id': support.project_id(),
        'route_ids': support.route_ids(),
        'versions': support.tool_versions(evidence),
        'source_status': support.source_status(evidence),
        'owner_state': support.owner_state(evidence),
        'routes_state': support.routes_state(evidence),
    }
    support.write_json(Path(evidence) / 'session.json', facts)
    return facts


@pytest.fixture(scope='session')
def owner(session_facts) -> dict:
    return session_facts['owner_state']


@pytest.fixture(scope='session')
def source_status(session_facts) -> dict:
    return session_facts['source_status']


def require_owner_binding(owner_state: dict) -> None:
    if not owner_state.get('owner_active'):
        pytest.skip(support.owner_skip_reason(owner_state))


def require_absent_owner_binding(owner_state: dict) -> None:
    if owner_state.get('owner_initialized'):
        observed = json.dumps({key: owner_state.get(key) for key in
                               ('owner_subject', 'project_ids', 'revoked', 'expires_at_us')},
                              ensure_ascii=False)
        pytest.skip(
            f'An Owner binding already exists ({observed}), so the not-initialized refusal cannot '
            'be exercised without revoking it; this suite never revokes an Owner.')


def require_current_registration(source: dict) -> None:
    if not source.get('ok'):
        pytest.skip(
            'The registration was built from different engine bytes '
            f'(declared={source.get("declared_count")} current={source.get("current_count")}, '
            f'changed={source.get("changed_files")}, missing={source.get("missing_files")}, '
            f'extra={source.get("extra_files")}). Regenerate it first:\n\n{support.build_command()}')
