"""Fixtures for the real local installation chain tests.

One pytest run writes one evidence directory; raw child bytes, argv and exit codes
live there and are never rewritten. Tests are written to run individually
(`pytest tests/development/test_development_host_negatives.py -k env`) without any
other fixture or plugin.

The session builds its own registration slice from the **current checkout** with the
official builder (`tools/testing/local_chain_fixture.py`) instead of trusting the
integration hand-off file, whose engine hashes legitimately move with every product
commit. Instance state is always a **copy**; the integration instance is never
written.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import local_chain_support as support
import pytest

sys.path.insert(0, str(support.REPO_ROOT / 'tools' / 'testing'))
import local_chain_fixture as fixture_tool


def pytest_report_header(config) -> str:
    return '\n'.join([f'local chain fixture: {support.DEFAULT_FIXTURE}',
                      f'local chain evidence root: {support.DEFAULT_EVIDENCE}'])


@pytest.fixture(scope='session')
def evidence() -> Path:
    stamp = datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')
    folder = support.DEFAULT_EVIDENCE / f'{stamp}-pytest-{os.getpid()}'
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'session.txt').write_text(
        f'created={support.utc_now()}\npid={os.getpid()}\nrepo={support.REPO_ROOT}\n',
        encoding='utf-8', newline='\n')
    return folder


@pytest.fixture(scope='session')
def fixture_slice(evidence) -> dict:
    """Rebuild (only when stale) the current-checkout registration fixture."""
    facts = fixture_tool.ensure()
    support.configure(installation=Path(facts['fixture_root']))
    support.write_json(Path(evidence) / 'fixture.json', facts)
    return facts


@pytest.fixture(scope='session')
def primary_instance(evidence, fixture_slice) -> dict:
    """A clean first-start instance copy shared by the refusal cases."""
    path = fixture_tool.new_instance(evidence, 'primary', base=Path(fixture_slice['base_instance']))
    support.configure(instance=path)
    return {'instance': path, 'instance_id': fixture_tool.instance_id(path)}


@pytest.fixture(scope='session')
def instance_factory(evidence, fixture_slice):
    """Create an isolated clean instance copy for one test."""
    def make(name: str) -> Path:
        return fixture_tool.new_instance(evidence, name, base=Path(fixture_slice['base_instance']))
    return make


@pytest.fixture(scope='session')
def installation(fixture_slice, primary_instance) -> dict:
    missing = [str(path) for path in (support.registration(), support.ffmpeg_binary(), support.ffprobe_binary(),
                                      support.package(), primary_instance['instance'])
               if not Path(path).exists()]
    if missing:
        pytest.fail('the local chain fixture is incomplete; missing: ' + ', '.join(missing))
    return {
        'installation': support.installation(),
        'registration': support.registration(),
        'registration_sha256': support.registration_sha256(),
        'instance': primary_instance['instance'],
        'package': support.package(),
        'ffmpeg': support.ffmpeg_binary(),
        'ffprobe': support.ffprobe_binary(),
        'project_id': support.project_id(),
        'route_ids': support.route_ids(),
        'fixture': fixture_slice,
    }


@pytest.fixture(scope='session')
def session_facts(evidence, installation) -> dict:
    facts = {
        'started_at': support.utc_now(),
        'git_head': support.git_head(),
        'git_status': support.git_status(evidence),
        'fixture': installation['fixture'],
        'registration': str(support.registration()),
        'registration_sha256': support.registration_sha256(),
        'registration_bytes': support.registration().stat().st_size,
        'instance': str(support.instance()),
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
            'The fixture registration is stale against the current checkout '
            f'(declared={source.get("declared_count")} current={source.get("current_count")}, '
            f'changed={source.get("changed_files")}). Rebuild it first:\n\n{support.build_command()}')


def require_human_review_approval() -> None:
    if os.environ.get('VIDEO_CREATOR_HUMAN_APPROVAL') != '1':
        pytest.skip(
            'The end-to-end chain needs two real human review decisions (plan and quality). '
            'This suite never approves on a human behalf; set VIDEO_CREATOR_HUMAN_APPROVAL=1 only '
            'when a person is at the API to submit them (see Handoff.md section 4).')
