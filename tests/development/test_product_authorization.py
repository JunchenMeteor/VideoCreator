"""Directed product-authorization channel: restricted serve -> pending -> approve -> restart.

ADR0081: a `serve` process without an Owner binding may listen, but only
`/api/v1/health` and `/api/v1/authorization/*` are addressable; every other route
is `403 owner_authorization_required`. The consent surface must not unlock the
same process: approval writes the Owner binding and reports `restart_required`,
and only a restarted host is a ready host.

This case is deliberately independent from `test_acceptance_dispatch.py`: that
suite only needs an authorized non-local host, while this one asserts the channel
protocol itself (secret-gated nonce, `complete` + `restart_required`, the still
closed routes before the restart, and the open routes after it).
"""

from __future__ import annotations

import secrets
from pathlib import Path

import local_chain_support as support

AUTHORIZATION_SECRET_ENV = 'VIDEO_CREATOR_AUTHORIZATION_SESSION_SECRET'
SECRET_HEADER = 'X-VideoCreator-Authorization'
SECRET_HEADER_LOWER = SECRET_HEADER.lower()


def production_arguments(instance: Path, installation: dict) -> list[str]:
    return [str(support.PYTHON), '-m', 'video_creator.cli.main', 'serve',
            '--data-dir', str(instance), '--host', '127.0.0.1', '--port', '0',
            '--ffmpeg', str(installation['ffmpeg']), '--ffprobe', str(installation['ffprobe'])]


def test_product_authorization_channel_end_to_end(evidence, installation, instance_factory) -> None:
    instance = instance_factory('product-authorization')
    token = support.new_token()
    session_secret = secrets.token_hex(16)
    argv = production_arguments(instance, installation)
    observed: dict = {}

    restricted_environment = support.base_environment({
        'VIDEO_CREATOR_API_TOKEN': token,
        AUTHORIZATION_SECRET_ENV: session_secret,
    })
    restricted = support.launch('product-authorization-restricted', argv, evidence,
                                env=restricted_environment)
    try:
        ready = restricted.wait_for_event('ready', timeout=120)
        # 1. An uninitialized instance starts restricted instead of failing before bind.
        assert ready.get('authorization_state') == 'pending', ready
        assert 'principal_id' not in ready, ready
        base_url = ready['base_url']

        # 2. Every product route is closed, but health answers and names the state.
        status, headers, health, raw = support.http_json(base_url, '/api/v1/health', token=token)
        assert status == 200, f'health returned {status}: {raw[:300]!r}'
        assert headers.get(SECRET_HEADER_LOWER) == 'pending', headers
        status, _headers, refused, raw = support.http_json(base_url, '/api/v1/projects', token=token)
        assert status == 403, f'projects returned {status} before authorization: {raw[:300]!r}'
        assert refused.get('code') == 'owner_authorization_required', refused
        observed['restricted'] = {'ready': ready, 'health': health, 'projects': refused}

        # 3. The pending view is secret-gated: without the launcher secret it is
        #    refused, with it the single-use nonce is actually present.
        status, _headers, denied, raw = support.http_json(
            base_url, '/api/v1/authorization/pending', token=token)
        assert status == 403, f'pending without the secret returned {status}: {raw[:300]!r}'
        assert denied.get('code') == 'authorization_session_denied', denied
        status, _headers, pending, raw = support.http_json(
            base_url, '/api/v1/authorization/pending', token=token,
            exact_headers={SECRET_HEADER: session_secret})
        assert status == 200, f'pending returned {status}: {raw[:300]!r}'
        assert pending.get('state') == 'pending', pending
        assert pending.get('can_decide') is True, pending
        assert isinstance(pending.get('nonce'), str) and pending['nonce'], pending
        observed['pending'] = {**pending, 'nonce': '<consumed; not persisted>'}

        # 4. Approval completes the channel and demands a restart; it must not
        #    claim the instance is ready in this process.
        decision = {'scope_sha256': pending['scope_sha256'], 'nonce': pending['nonce']}
        status, _headers, approved, raw = support.http_json(
            base_url, f"/api/v1/authorization/{pending['authorization_id']}/approve",
            token=token, method='POST', body=decision,
            exact_headers={SECRET_HEADER: session_secret})
        assert status == 200, f'approve returned {status}: {raw[:600]!r}'
        assert approved.get('state') == 'complete', approved
        assert approved.get('restart_required') is True, approved
        assert approved.get('nonce') is None, 'a decided request must not expose its nonce'
        observed['approved'] = approved

        status, headers, _health, _raw = support.http_json(base_url, '/api/v1/health', token=token)
        assert status == 200
        assert headers.get(SECRET_HEADER_LOWER) == 'complete', headers

        # 5. Still the same restricted process: the product routes stay closed.
        status, _headers, still_refused, raw = support.http_json(base_url, '/api/v1/projects', token=token)
        assert status == 403, f'projects opened without a restart: {status} {raw[:300]!r}'
        assert still_refused.get('code') == 'owner_authorization_required', still_refused
        observed['before_restart'] = still_refused
    finally:
        restricted.stop()

    # 6. The restart is the only path to a ready host.
    environment = support.base_environment({'VIDEO_CREATOR_API_TOKEN': token})
    server = support.launch('product-authorization-serve', argv, evidence, env=environment)
    try:
        ready = server.wait_for_event('ready', timeout=120)
        assert 'authorization_state' not in ready, (
            'an authorized instance must not start the restricted channel again')
        status, headers, _health, raw = support.http_json(ready['base_url'], '/api/v1/health', token=token)
        assert status == 200, f'health returned {status}: {raw[:300]!r}'
        assert headers.get(SECRET_HEADER_LOWER) == 'none', headers
        status, _headers, projects, raw = support.http_json(ready['base_url'], '/api/v1/projects', token=token)
        assert status == 200, f'projects returned {status} after the restart: {raw[:600]!r}'
        assert isinstance(projects, list), projects
        observed['after_restart'] = {'project_count': len(projects)}
    finally:
        server.stop()

    support.write_json(Path(evidence) / 'product-authorization.json', observed)
