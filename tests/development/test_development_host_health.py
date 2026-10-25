"""Health visibility of the development host (ADR0077 section 5).

Observed on the real frozen slice:

* a real production `serve` process returns `/api/v1/health` **without**
  `X-VideoCreator-Installation`, and a caller-supplied value is never reflected;
* the header appears only when the process itself is marked, and the OpenAPI
  response declaration stays unchanged;
* `serve-dev` (the real development process, which also proves the header in a
  genuine dev start) needs a real Owner binding and is skipped with the exact
  `owner-init` command until one exists.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import local_chain_support as support
from conftest import require_current_registration, require_owner_binding

HEADER = 'X-VideoCreator-Installation'


def test_production_serve_health_has_no_development_header(evidence, installation, owner) -> None:
    """Real production process: unmarked, no dev header, caller header not reflected."""
    instance = support.copy_instance_for_serve(evidence)
    token = support.new_token()
    argv = [str(support.PYTHON), '-m', 'video_creator.cli.main', 'serve',
            '--data-dir', str(instance), '--host', '127.0.0.1', '--port', '0']
    environment = support.base_environment({'VIDEO_CREATOR_API_TOKEN': token})
    with support.launch('production-serve', argv, evidence, env=environment) as server:
        ready = server.wait_for_event('ready', timeout=90)
        assert 'principal_id' not in ready, (
            'an uninstalled production serve must not claim a development principal: '
            + json.dumps(ready, ensure_ascii=False))
        status, headers, payload, raw = support.http_json(
            ready['base_url'], '/api/v1/health', token=token,
            exact_headers={HEADER: 'forged-by-caller'})
        assert status == 200, f'health returned {status}: {raw[:400]!r}'
        assert HEADER.lower() not in headers, (
            'a production serve must not expose the development installation header: '
            + json.dumps(headers, ensure_ascii=False))
        assert payload['mode'] == 'local'
        assert payload['instance_id'] == owner['instance_id'], (
            'health must report the actual instance identity: ' + json.dumps(payload, ensure_ascii=False))
        assert 'local-development' not in json.dumps(payload), (
            'health must not describe a development binding in its body: '
            + json.dumps(payload, ensure_ascii=False))
        assert server.stdout_text().count('"event": "ready"') == 1


def test_development_header_is_process_internal_only(evidence, installation) -> None:
    """Same production app: the header exists only after the dev host marks the process."""
    scratch = Path(tempfile.mkdtemp(prefix='vc-marker-instance-'))
    try:
        result = support.run_probe_module('marker-health', ['marker-health', '--scratch-dir', str(scratch)],
                                          evidence, env=support.base_environment())
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    assert result.exit_code == 0, f'probe failed: {result.stderr_text()}'
    payload = result.json_payloads()[-1]
    support.write_json(Path(evidence) / 'marker-health.json', payload)
    assert payload['unmarked']['status'] == 200
    assert payload['unmarked']['development_header'] is None, (
        'an unmarked process must not send the development header')
    assert payload['marked']['status'] == 200
    assert payload['marked']['development_header'] == 'local-development', (
        'the marked development process must send its header, got '
        + repr(payload['marked']['development_header']))
    assert payload['marked']['body']['mode'] == 'local', (
        'the health body contract must stay unchanged: ' + json.dumps(payload['marked']['body']))
    assert payload['openapi_declares_development_header'] is False, (
        'the runtime development header must not enter the published OpenAPI contract')


def test_serve_dev_health_returns_development_header(evidence, installation, owner, source_status) -> None:
    """Real `serve-dev` process; skipped until the human TTY Owner binding exists."""
    require_owner_binding(owner)
    require_current_registration(source_status)
    assert support.project_id() in owner.get('project_ids', []), (
        'the Owner binding must name the registered project: ' + json.dumps(owner, ensure_ascii=False))
    token = support.new_token()
    argv = support.dev_host_arguments('serve-dev', port=0)
    environment = support.dev_environment(owner['instance_id'])
    environment['VIDEO_CREATOR_API_TOKEN'] = token
    with support.launch('serve-dev-health', argv, evidence, env=environment) as server:
        ready = server.wait_for_event('ready', timeout=300)
        assert ready.get('principal_id'), (
            'a real installed development start must report its principal: '
            + json.dumps(ready, ensure_ascii=False))
        status, headers, payload, raw = support.http_json(
            ready['base_url'], '/api/v1/health', token=token)
        assert status == 200, f'health returned {status}: {raw[:400]!r}'
        assert headers.get(HEADER.lower()) == 'local-development', (
            'the actual serve-dev process must expose its development header, got '
            + repr(headers.get(HEADER.lower())))
        assert payload['instance_id'] == owner['instance_id']
        assert payload['mode'] == 'local'
