"""Acceptance dispatch: local instance subset stays queued, non-local gates stay intact.

Real HTTP against two real processes:

* `serve-dev --development-auto-owner-init` on a copy of the clean instance for the
  local cases (`outputs=["video"]` in v0.2 and v0.3 must be accepted and `queued`);
* production `serve` on another instance whose Owner was authorized through the
  product's own consent channel (ADR0081), for the non-local cases, which must keep
  the old blockers (`output_profile_unavailable` for the v0.2 subset,
  `alignment_required` for v0.3 without a resolved evidence policy).

ADR0081: a `serve` without an Owner binding only answers `/health` and
`/api/v1/authorization/*`; every other route is `403 owner_authorization_required`.
That is why the non-local instance is authorized first. The product channel is
used instead of `--development-auto-owner-init` on purpose: the auto-init flag
turns the host into a development host (`x-videocreator-installation`), and these
cases must run against a production-shaped host. The channel itself is covered
independently by `test_product_authorization.py`.

The requests use the registered project and the four registered local routes; no
review decision and no worker are created.
"""

from __future__ import annotations

import hashlib
import json
import secrets
from pathlib import Path

import local_chain_support as support
import pytest
from conftest import require_current_registration


def generate_png(path: Path) -> tuple[Path, bytes]:
    from PIL import Image

    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new('RGB', (720, 1280), (32, 96, 160)).save(path, format='PNG')
    return path, path.read_bytes()


def upload_png(base_url: str, token: str, evidence: Path, name: str) -> dict:
    path, payload = generate_png(Path(evidence) / f'{name}-still-720x1280.png')
    digest = hashlib.sha256(payload).hexdigest()
    status, _headers, staged = support.http_bytes(
        base_url, '/api/v1/assets/staging', token=token, method='POST',
        body=payload, content_type='image/png')
    assert status == 201, f'asset staging returned {status}: {staged[:300]!r}'
    staging = json.loads(staged)
    candidate = {'staging_id': staging['staging_id'], 'sha256': digest, 'size': len(payload),
                 'media_type': 'image/png', 'source': 'tests/development/acceptance-dispatch',
                 'rights': 'user_asserted_owned_local_material'}
    status, _headers, imported, raw = support.http_json(
        base_url, '/api/v1/assets/import', token=token, method='POST', body=candidate)
    assert status == 201, f'asset import returned {status}: {raw[:600]!r}'
    return {'asset_id': imported['asset_id'], 'sha256': imported['sha256'], 'png': str(path)}


def production_body(*, project_id: str, asset_id: str, outputs: list[str],
                    routes: list[str], version: str | None) -> dict:
    body = {
        'goal': 'Acceptance dispatch probe: one owned still image, outputs ' + ','.join(outputs),
        'project_id': project_id,
        'inputs': {'asset_ids': [asset_id]},
        'automation': {'mode': 'interactive', 'max_revision_cycles': 2},
        'policy': {'version': 'local-default-v1', 'allowed_provider_routes': routes,
                   'external_transfer_allowed': False,
                   'max_cost': {'currency': 'CNY', 'amount': '0'}},
        'outputs': outputs,
    }
    if version is not None:
        body['request_format_version'] = version
    return body


def accept(base_url: str, token: str, body: dict, name: str) -> dict:
    status, _headers, accepted, raw = support.http_json(
        base_url, '/api/v1/productions', token=token, method='POST', body=body,
        idempotency_key=f'acceptance-{name}-{secrets.token_hex(8)}')
    assert status == 202, f'{name}: production accept returned {status}: {raw[:1200]!r}'
    return accepted


def detail_and_events(base_url: str, token: str, accepted: dict) -> tuple[dict, list[str]]:
    status, _headers, detail, raw = support.http_json(
        base_url, f'/api/v1/productions/{accepted["production_id"]}', token=token)
    assert status == 200, f'production read returned {status}: {raw[:400]!r}'
    status, _headers, events, raw = support.http_json(
        base_url, f'/api/v1/runs/{accepted["run_id"]}/events', token=token)
    assert status == 200, f'event read returned {status}: {raw[:400]!r}'
    return detail, [event['event_type'] for event in events]


@pytest.fixture(scope='session')
def local_dispatch(evidence, installation, source_status, instance_factory) -> dict:
    require_current_registration(source_status)
    instance = instance_factory('acceptance-local')
    token = support.new_token()
    instance_id = support.metadata_value(instance, 'instance_id')
    argv = support.dev_host_arguments('serve-dev', port=0, auto_owner_init=True, data_dir=instance)
    environment = support.dev_environment(instance_id)
    environment['VIDEO_CREATOR_API_TOKEN'] = token
    server = support.launch('acceptance-local-serve-dev', argv, evidence, env=environment)
    try:
        ready = server.wait_for_event('ready', timeout=300)
        assert ready.get('principal_id') == 'local-user'
        status, headers, health, raw = support.http_json(ready['base_url'], '/api/v1/health', token=token)
        assert status == 200, f'health returned {status}: {raw[:300]!r}'
        assert headers.get('x-videocreator-installation') == 'local-development'
        asset = upload_png(ready['base_url'], token, evidence, 'local')
        yield {'server': server, 'base_url': ready['base_url'], 'token': token,
               'instance': instance, 'asset': asset, 'health': health}
    finally:
        server.stop()


AUTHORIZATION_SECRET_ENV = 'VIDEO_CREATOR_AUTHORIZATION_SESSION_SECRET'


def production_arguments(instance: Path, installation: dict) -> list[str]:
    return [str(support.PYTHON), '-m', 'video_creator.cli.main', 'serve',
            '--data-dir', str(instance), '--host', '127.0.0.1', '--port', '0',
            '--ffmpeg', str(installation['ffmpeg']), '--ffprobe', str(installation['ffprobe'])]


@pytest.fixture(scope='session')
def nonlocal_dispatch(evidence, installation, instance_factory) -> dict:
    instance = instance_factory('acceptance-nonlocal')
    token = support.new_token()
    session_secret = secrets.token_hex(16)
    argv = production_arguments(instance, installation)
    # ADR0081 §2: without an Owner binding `serve` starts restricted. The launcher
    # (this fixture) injects the 128-bit authorization session secret, reads the
    # pending request with it, approves it, and only then restarts the same
    # instance into the ready host that the non-local cases need.
    restricted_environment = support.base_environment({
        'VIDEO_CREATOR_API_TOKEN': token,
        AUTHORIZATION_SECRET_ENV: session_secret,
    })
    restricted = support.launch('acceptance-nonlocal-restricted', argv, evidence,
                                env=restricted_environment)
    try:
        pending_ready = restricted.wait_for_event('ready', timeout=120)
        assert pending_ready.get('authorization_state') == 'pending', pending_ready
        status, headers, health, raw = support.http_json(
            pending_ready['base_url'], '/api/v1/health', token=token)
        assert status == 200, f'restricted health returned {status}: {raw[:300]!r}'
        assert headers.get('x-videocreator-authorization') == 'pending', headers
        status, _headers, refused, raw = support.http_json(
            pending_ready['base_url'], '/api/v1/projects', token=token)
        assert status == 403, f'restricted projects returned {status}: {raw[:300]!r}'
        assert refused.get('code') == 'owner_authorization_required', refused
        status, _headers, pending, raw = support.http_json(
            pending_ready['base_url'], '/api/v1/authorization/pending', token=token,
            exact_headers={'X-VideoCreator-Authorization': session_secret})
        assert status == 200, f'authorization pending returned {status}: {raw[:300]!r}'
        assert pending.get('nonce') and pending.get('state') == 'pending', pending
        status, _headers, approved, raw = support.http_json(
            pending_ready['base_url'], f"/api/v1/authorization/{pending['authorization_id']}/approve",
            token=token, method='POST',
            body={'scope_sha256': pending['scope_sha256'], 'nonce': pending['nonce']},
            exact_headers={'X-VideoCreator-Authorization': session_secret})
        assert status == 200, f'authorization approve returned {status}: {raw[:600]!r}'
        assert approved.get('state') == 'complete', approved
        assert approved.get('restart_required') is True, approved
        support.write_json(Path(evidence) / 'acceptance-nonlocal-authorization.json',
                           {'pending': {**pending, 'nonce': '<consumed; not persisted>'},
                            'approved': approved})
    finally:
        restricted.stop()

    environment = support.base_environment({'VIDEO_CREATOR_API_TOKEN': token})
    server = support.launch('acceptance-nonlocal-serve', argv, evidence, env=environment)
    try:
        ready = server.wait_for_event('ready', timeout=120)
        assert 'authorization_state' not in ready, (
            'a production serve with an Owner binding must not run the restricted channel')
        assert 'principal_id' not in ready
        status, headers, health, raw = support.http_json(ready['base_url'], '/api/v1/health', token=token)
        assert status == 200, f'health returned {status}: {raw[:300]!r}'
        assert 'x-videocreator-installation' not in headers, (
            'a production serve must not mark itself as a development host')
        asset = upload_png(ready['base_url'], token, evidence, 'nonlocal')
        yield {'server': server, 'base_url': ready['base_url'], 'token': token,
               'instance': instance, 'asset': asset, 'health': health}
    finally:
        server.stop()


def test_local_v02_video_subset_is_queued(evidence, installation, local_dispatch) -> None:
    body = production_body(project_id=installation['project_id'],
                           asset_id=local_dispatch['asset']['asset_id'], outputs=['video'],
                           routes=installation['route_ids'], version=None)
    accepted = accept(local_dispatch['base_url'], local_dispatch['token'], body, 'local-v02')
    detail, events = detail_and_events(local_dispatch['base_url'], local_dispatch['token'], accepted)
    support.write_json(Path(evidence) / 'acceptance-local-v02.json',
                       {'request': body, 'accepted': accepted, 'detail': detail, 'events': events})
    assert detail['status'] == 'queued', (
        'a local v0.2 video-only request must reach queued: '
        + json.dumps({'status': detail['status'], 'events': events}, ensure_ascii=False))
    assert events == ['production.accepted'], events
    for blocker in ('output_profile_unavailable', 'alignment_required'):
        assert blocker not in events


def test_local_v03_video_subset_is_queued(evidence, installation, local_dispatch) -> None:
    body = production_body(project_id=installation['project_id'],
                           asset_id=local_dispatch['asset']['asset_id'], outputs=['video'],
                           routes=installation['route_ids'], version='0.3.0-candidate')
    accepted = accept(local_dispatch['base_url'], local_dispatch['token'], body, 'local-v03')
    detail, events = detail_and_events(local_dispatch['base_url'], local_dispatch['token'], accepted)
    support.write_json(Path(evidence) / 'acceptance-local-v03.json',
                       {'request': body, 'accepted': accepted, 'detail': detail, 'events': events})
    assert accepted['schema_version'] == '0.3.0-candidate'
    assert detail['status'] == 'queued', (
        'a local v0.3 video-only request must reach queued: '
        + json.dumps({'status': detail['status'], 'events': events}, ensure_ascii=False))
    assert events == ['production.accepted'], events
    for blocker in ('output_profile_unavailable', 'alignment_required'):
        assert blocker not in events


def test_nonlocal_v02_video_subset_keeps_output_profile_blocker(evidence, installation,
                                                               nonlocal_dispatch) -> None:
    body = production_body(project_id=installation['project_id'],
                           asset_id=nonlocal_dispatch['asset']['asset_id'], outputs=['video'],
                           routes=installation['route_ids'], version=None)
    accepted = accept(nonlocal_dispatch['base_url'], nonlocal_dispatch['token'], body, 'nonlocal-v02')
    detail, events = detail_and_events(nonlocal_dispatch['base_url'], nonlocal_dispatch['token'], accepted)
    support.write_json(Path(evidence) / 'acceptance-nonlocal-v02.json',
                       {'request': body, 'accepted': accepted, 'detail': detail, 'events': events})
    assert detail['status'] == 'waiting_user', (
        'a non-local subset must stay behind the old output-profile gate: '
        + json.dumps({'status': detail['status'], 'events': events}, ensure_ascii=False))
    assert 'output_profile_unavailable' in events, events
    assert 'alignment_required' not in events
    assert detail['status'] != 'queued'


def test_nonlocal_v03_video_subset_keeps_alignment_blocker(evidence, installation,
                                                          nonlocal_dispatch) -> None:
    body = production_body(project_id=installation['project_id'],
                           asset_id=nonlocal_dispatch['asset']['asset_id'], outputs=['video'],
                           routes=installation['route_ids'], version='0.3.0-candidate')
    accepted = accept(nonlocal_dispatch['base_url'], nonlocal_dispatch['token'], body, 'nonlocal-v03')
    detail, events = detail_and_events(nonlocal_dispatch['base_url'], nonlocal_dispatch['token'], accepted)
    support.write_json(Path(evidence) / 'acceptance-nonlocal-v03.json',
                       {'request': body, 'accepted': accepted, 'detail': detail, 'events': events})
    assert detail['status'] == 'waiting_user', (
        'a non-local v0.3 subset must stay behind the evidence-policy gate: '
        + json.dumps({'status': detail['status'], 'events': events}, ensure_ascii=False))
    assert 'alignment_required' in events, events
    assert detail['status'] != 'queued'
