"""Real end-to-end local chain: still image -> plan -> ffmpeg master -> quality -> 0.4 bundle.

This is the one positive case the task card asks for. It runs only when a real
Owner binding exists, because `serve-dev`/`worker-dev` refuse to start without one
and this suite never fabricates that binding (ADR0077 sections 4 and 6). When the
binding is absent the test skips with the exact human TTY `owner-init` command and
the current observed refusal code.

Flow, all through product entry points only:

1. `serve-dev` with the frozen registration, the four local routes and the bundled
   ffmpeg/ffprobe; assert the development health header.
2. Upload one real PNG still through `/api/v1/assets/staging` + `/api/v1/assets/import`
   (the import runs the bundled decoder, no mock media).
3. `POST /api/v1/productions` (`interactive`, `outputs=["video"]`, the four local
   routes, `max_cost=0`, the registered project id).
4. `worker-dev`, then approve the `plan` and `quality` revisions of that Run.
5. Assert: succeeded, non-empty `bundle_ref`, manifest `schema_version=0.4.0-candidate`,
   the mp4 probed by the *bundled* ffprobe (codec / duration / frame count against the
   visual-mapping document), the event sequence, a ledger with no unknown operation,
   and `VerifyPersistedAssembly.py` reading the persisted assembly back.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

import local_chain_support as support
import pytest
from conftest import require_current_registration, require_owner_binding

TERMINAL_STATUSES = {'succeeded', 'failed', 'cancelled', 'cancel_requested', 'needs_reconciliation'}
APPROVAL_KINDS = ('plan', 'quality')
POLL_SECONDS = 3
EVENT_SEQUENCE = ['production.accepted', 'plan.ready', 'review.required', 'review.decided',
                  'quality.ready', 'bundle.prepared', 'bundle.ready', 'production.succeeded']


def generate_still(path: Path) -> Path:
    """A real 720x1280 PNG (a vertical test pattern, not a fabricated Asset record)."""
    from PIL import Image

    image = Image.new('RGB', (720, 1280))
    pixels = image.load()
    for y in range(1280):
        for x in range(0, 720, 8):
            value = (x * 255) // 720
            for offset in range(8):
                pixels[x + offset, y] = (value, 64 + (y * 120) // 1280, 255 - value)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format='PNG')
    return path


def require_chain_preconditions(owner: dict, source: dict, routes: dict) -> None:
    require_owner_binding(owner)
    require_current_registration(source)
    if support.project_id() not in owner.get('project_ids', []):
        pytest.skip('The Owner binding does not include the registered project {}; re-run the TTY '
                    'owner-init with --project-id {}.\n\n{}'.format(support.project_id(), support.project_id(),
                       support.owner_init_command(owner.get('instance_id', '<instance>'))))
    if not routes.get('ok'):
        pytest.skip(f'The four local routes are not all registered; run:\n\n{support.register_route_command()}')
    projects = {item['project_id']: item['owner'] for item in routes.get('projects', [])}
    if projects.get(support.project_id()) != 'local-user':
        pytest.skip(f'The registered project {support.project_id()} is not an existing local-user project; create it with:\n\n{support.ensure_project_command()}')


def upload_still(base_url: str, token: str, evidence: Path) -> dict:
    path = generate_still(Path(evidence) / 'still-frame-720x1280.png')
    payload = path.read_bytes()
    digest = support.sha256_bytes(payload)
    status, _headers, staged = support.http_bytes(
        base_url, '/api/v1/assets/staging', token=token, method='POST',
        body=payload, content_type='image/png')
    assert status == 201, f'asset staging returned {status}: {staged[:400]!r}'
    staging = json.loads(staged)
    assert staging['sha256'] == digest and staging['size'] == len(payload)
    candidate = {
        'staging_id': staging['staging_id'],
        'sha256': digest,
        'size': len(payload),
        'media_type': 'image/png',
        'source': 'tests/development/local-chain-e2e',
        'rights': 'user_asserted_owned_local_material',
    }
    status, _headers, imported, raw = support.http_json(
        base_url, '/api/v1/assets/import', token=token, method='POST', body=candidate)
    assert status == 201, f'asset import returned {status}: {raw[:800]!r}'
    support.write_json(Path(evidence) / 'asset-import.json', imported)
    return {'asset_id': imported['asset_id'], 'sha256': imported['sha256'],
            'size': imported['size'], 'probe': imported['probe'], 'png': str(path)}


def production_request(asset_id: str) -> dict:
    return {
        'goal': '用这张本地自有静图制作一条只有画面的短片，只输出 video。',
        'project_id': support.project_id(),
        'inputs': {'asset_ids': [asset_id]},
        'automation': {'mode': 'interactive', 'max_revision_cycles': 2},
        'policy': {
            'version': 'local-default-v1',
            'allowed_provider_routes': support.route_ids(),
            'external_transfer_allowed': False,
            'max_cost': {'currency': 'CNY', 'amount': '0'},
        },
        'outputs': ['video'],
    }


def approve_revision(base_url: str, token: str, run_id: str, revision: dict, evidence: Path) -> dict:
    decision = {'target_revision_id': revision['revision_id'], 'action': 'approve', 'instruction_text': ''}
    status, _headers, payload, raw = support.http_json(
        base_url, f'/api/v1/runs/{run_id}/decisions', token=token, method='POST', body=decision,
        idempotency_key='chain-approve-{}'.format(revision['revision_id']))
    assert 200 <= status < 300, (
        f'approving {revision["kind"]} returned {status}: {raw[:800]!r}')
    support.write_json(Path(evidence) / f'approval-{revision["kind"]}.json',
                       {'revision': revision, 'response': payload})
    return payload


def drive_reviews(base_url: str, worker, token: str, production_id: str, run_id: str,
                  evidence: Path, timeout: float) -> dict:
    approved: set[str] = set()
    history: list[dict] = []
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status, _headers, detail, raw = support.http_json(
            base_url, f'/api/v1/productions/{production_id}', token=token)
        assert status == 200, f'production read returned {status}: {raw[:400]!r}'
        if detail['status'] != (history[-1]['status'] if history else None):
            history.append({'status': detail['status'], 'at': support.utc_now()})
        if detail['status'] in TERMINAL_STATUSES:
            return detail
        status, _headers, revisions, raw = support.http_json(
            base_url, f'/api/v1/productions/{production_id}/revisions', token=token)
        assert status == 200, f'revision read returned {status}: {raw[:400]!r}'
        for revision in revisions:
            if revision['kind'] not in APPROVAL_KINDS or revision['revision_id'] in approved:
                continue
            approve_revision(base_url, token, run_id, revision, evidence)
            approved.add(revision['revision_id'])
        worker_state = worker.process.poll()
        assert worker_state is None, (
            f'worker-dev exited with {worker_state} while the chain was running\n'
            f'stderr={worker.stderr_text()[-4000:]}')
        time.sleep(POLL_SECONDS)
    raise AssertionError(f'the local chain did not reach a terminal production status within {timeout}s\n'
                         f'status history={json.dumps(history)}\nworker stderr={worker.stderr_text()[-4000:]}')


def fetch_manifest(base_url: str, token: str, revision_id: str, evidence: Path) -> dict:
    status, _headers, manifest, raw = support.http_json(
        base_url, f'/api/v1/bundles/{revision_id}/manifest', token=token)
    assert status == 200, f'manifest read returned {status}: {raw[:800]!r}'
    support.write_json(Path(evidence) / 'bundle-manifest.json', manifest)
    return manifest


def download_artifact(base_url: str, token: str, revision_id: str, artifact: dict,
                      evidence: Path) -> tuple[Path, bytes]:
    status, _headers, payload = support.http_bytes(
        base_url, f'/api/v1/bundles/{revision_id}/artifacts/{artifact["artifact_id"]}/content',
        token=token)
    assert status == 200, f'artifact content returned {status}'
    assert support.sha256_bytes(payload) == artifact['sha256'], (
        'downloaded artifact bytes differ from its manifest SHA256')
    assert len(payload) == artifact['size']
    suffix = Path(artifact['relative_path']).suffix
    path = Path(evidence) / 'bundle' / ('master' + suffix)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path, payload


def visual_mapping(base_url: str, token: str, revision_id: str, manifest: dict,
                   evidence: Path) -> dict | None:
    mapping_id = manifest.get('visual_mapping_artifact_id')
    if not mapping_id:
        return None
    status, _headers, payload = support.http_bytes(
        base_url, f'/api/v1/bundles/{revision_id}/artifacts/{mapping_id}/content', token=token)
    assert status == 200, f'visual mapping content returned {status}'
    document = json.loads(payload.decode('utf-8'))
    support.write_json(Path(evidence) / 'visual-mapping.json', document)
    return document


def assert_mp4(evidence: Path, master: Path, manifest: dict, mapping: dict | None, artifact: dict) -> dict:
    probed = support.ffprobe(master, evidence=evidence, name='ffprobe-master')
    payload = probed['payload']
    streams = payload.get('streams', [])
    videos = [stream for stream in streams if stream.get('codec_type') == 'video']
    assert videos, 'the produced bundle mp4 has no video stream: ' + json.dumps(payload)[:1500]
    video = videos[0]
    assert video.get('codec_name') == 'h264', (
        'the local master must be h264/libx264: ' + json.dumps(video, ensure_ascii=False)[:1200])
    assert video.get('pix_fmt') == 'yuv420p', 'the local master must be yuv420p: ' + json.dumps(video)[:600]
    frames = int(video.get('nb_read_frames') or 0)
    assert frames > 0, 'ffprobe reported no decoded frames'

    timeline_us = int(manifest['timeline_duration_us'])
    format_duration_us = round(float(payload['format']['duration']) * 1_000_000)
    tolerance_us = 100_000
    assert abs(format_duration_us - timeline_us) <= tolerance_us, (
        f'mp4 duration {format_duration_us}us differs from the manifest timeline {timeline_us}us '
        f'by more than {tolerance_us}us')
    if mapping is not None:
        assert int(mapping['timeline_duration_us']) == timeline_us, (
            'the visual mapping timeline differs from the approved manifest timeline')
        expected_frames = max(int(row['frame_end']) for row in mapping['rows'])
        fps_num, fps_den = int(mapping['fps_num']), int(mapping['fps_den'])
        assert abs(frames - expected_frames) == 0, (
            f'decoded frame count {frames} differs from the approved frame grid end {expected_frames} '
            f'(fps {fps_num}/{fps_den}); raw ffprobe: {json.dumps(video, ensure_ascii=False)[:1200]}')
    assert video.get('width') and video.get('height')
    return {
        'codec_name': video.get('codec_name'),
        'pix_fmt': video.get('pix_fmt'),
        'width': video.get('width'),
        'height': video.get('height'),
        'nb_read_frames': frames,
        'duration_us': format_duration_us,
        'avg_frame_rate': video.get('avg_frame_rate'),
        'r_frame_rate': video.get('r_frame_rate'),
        'artifact_relative_path': artifact['relative_path'],
        'artifact_sha256': artifact['sha256'],
        'evidence': probed['record'],
    }


def assert_event_sequence(base_url: str, token: str, run_id: str) -> list[str]:
    status, _headers, events, raw = support.http_json(
        base_url, f'/api/v1/runs/{run_id}/events?after_sequence=0', token=token)
    assert status == 200, f'event read returned {status}: {raw[:400]!r}'
    types = [event['event_type'] for event in events]
    cursor = 0
    for expected in EVENT_SEQUENCE:
        try:
            cursor = types.index(expected, cursor) + 1
        except ValueError:
            raise AssertionError(f'event {expected!r} missing or out of order in {types}') from None
    assert types.count('review.decided') >= 2, f'expected two review decisions, got {types}'
    assert types.count('review.required') >= 2, f'expected two review requests, got {types}'
    return types


def assert_ledger(detail: dict) -> dict:
    operations = detail['operations']
    for operation in operations:
        assert operation['status'] != 'unknown', f'ledger operation unknown: {operation}'
        assert operation['cost_status'] == 'known', f'unknown cost in the ledger: {operation}'
        assert operation['actual_cost'] is not None, f'known cost without a value: {operation}'
        assert operation['actual_cost']['currency'] == 'CNY'
        assert str(operation['actual_cost']['amount']) == '0', (
            f'the local chain must be zero cost: {operation}')
    assert str(detail['cost']['spent']['amount']) == '0'
    assert str(detail['cost']['reserved']['amount']) == '0'
    return {'operations': len(operations), 'unknown': 0,
            'spent': detail['cost']['spent'], 'reserved': detail['cost']['reserved']}


def assert_database_ledger(instance: Path) -> dict:
    """Independent read: no unknown or unsettled operation may remain."""
    database = instance / 'Metadata.sqlite'
    connection = sqlite3.connect(database.absolute().as_uri() + '?mode=ro', uri=True, timeout=10)
    try:
        connection.row_factory = sqlite3.Row
        unknown = connection.execute(
            "SELECT id, status, settled FROM operations WHERE status='unknown' "
            "OR (settled=0 AND status IN ('succeeded','failed'))").fetchall()
        total = connection.execute('SELECT COUNT(*) AS count FROM operations').fetchone()['count']
        rows = [dict(row) for row in unknown]
    finally:
        connection.close()
    assert not rows, 'the operation ledger still has unknown/unsettled rows: ' + json.dumps(rows)
    return {'operations': total, 'unknown_or_unsettled': rows}


def run_assembly_readback(evidence: Path, registration_sha256: str) -> dict:
    assert support.VERIFY_ASSEMBLY.is_file(), (
        'VerifyPersistedAssembly.py is required to read the persisted local assembly back; '
        f'not found at {support.VERIFY_ASSEMBLY}')
    result = support.run_probe(
        'verify-persisted-assembly',
        [str(support.PYTHON), str(support.VERIFY_ASSEMBLY), '--data-dir', str(support.INSTANCE),
         '--registration-sha256', registration_sha256,
         '--out', str(Path(evidence) / 'assembly-readback.json')],
        evidence, env=support.base_environment(), timeout=300)
    assert result.exit_code == 0, (
        f'assembly read-back failed with {result.exit_code}\nstdout={result.stdout_text()}\n'
        f'stderr={result.stderr_text()}')
    payload = result.json_payloads()[-1]
    assert payload.get('ok') is True, f'read-back did not report ok: {payload}'
    assert payload.get('context_class') == 'LocalFinalAssemblyContextV1', (
        'the persisted context is not the local 0.4 assembly: ' + json.dumps(payload)[:800])
    assert payload.get('assembly_bytes', {}).get('sha256')
    return payload


def test_local_chain_produces_a_verifiable_0_4_bundle(evidence, installation, owner, source_status,
                                                     session_facts) -> None:
    routes = session_facts['routes_state']
    require_chain_preconditions(owner, source_status, routes)
    registration_sha = installation['registration_sha256']
    token = support.new_token()
    timeout = 900
    run_folder = Path(evidence) / 'chain'
    run_folder.mkdir(parents=True, exist_ok=True)

    serve_argv = support.dev_host_arguments('serve-dev', port=0)
    serve_environment = support.dev_environment(owner['instance_id'])
    serve_environment['VIDEO_CREATOR_API_TOKEN'] = token
    worker_argv = support.dev_host_arguments('worker-dev', max_seconds=timeout)
    worker_environment = support.dev_environment(owner['instance_id'])
    worker_environment['VIDEO_CREATOR_API_TOKEN'] = token

    with support.launch('serve-dev-chain', serve_argv, evidence, env=serve_environment) as server:
        ready = server.wait_for_event('ready', timeout=300)
        base_url = ready['base_url']
        assert ready.get('principal_id'), (
            'a real installed development start must report its principal: ' + json.dumps(ready))
        status, headers, health, raw = support.http_json(base_url, '/api/v1/health', token=token)
        assert status == 200
        assert headers.get('x-videocreator-installation') == 'local-development', (
            'serve-dev must mark its health response: ' + json.dumps(headers))
        support.write_json(run_folder / 'health.json', health)

        asset = upload_still(base_url, token, run_folder)
        request_body = production_request(asset['asset_id'])
        support.write_json(run_folder / 'production-request.json', request_body)
        idempotency = 'local-chain-e2e-{}'.format(support.sha256_bytes(
            json.dumps(request_body, ensure_ascii=False, sort_keys=True).encode('utf-8'))[:24])
        status, headers, accepted, raw = support.http_json(
            base_url, '/api/v1/productions', token=token, method='POST',
            body=request_body, idempotency_key=idempotency)
        assert status == 202, f'production accept returned {status}: {raw[:1200]!r}'
        support.write_json(run_folder / 'production-accepted.json', accepted)
        production_id, run_id = accepted['production_id'], accepted['run_id']

        with support.launch('worker-dev-chain', worker_argv, evidence, env=worker_environment) as worker:
            try:
                worker.wait_for_event('worker_ready', timeout=300)
                detail = drive_reviews(base_url, worker, token, production_id, run_id,
                                       run_folder, timeout)
            finally:
                worker.stop()
        support.write_json(run_folder / 'production-detail-final.json', detail)

        assert detail['status'] == 'succeeded', (
            'the local chain did not succeed: ' + json.dumps(detail, ensure_ascii=False)[:2000])
        bundle_ref = detail.get('bundle_ref')
        assert bundle_ref, 'a succeeded local production must expose its bundle_ref'
        support.write_json(run_folder / 'bundle-ref.json', bundle_ref)
        revision_id = bundle_ref['bundle_revision_id']

        manifest = fetch_manifest(base_url, token, revision_id, run_folder)
        assert manifest['schema_version'] == '0.4.0-candidate', (
            'the local bundle manifest version must be 0.4.0-candidate, got '
            + repr(manifest['schema_version']))
        assert manifest['content_profile'] == 'local-material-bundle-v1'
        assert list(manifest['requested_outputs']) == ['video']
        assert manifest['instance_id'] == owner['instance_id']
        assert manifest['project_id'] == support.project_id()
        assert manifest['quality_ref']['kind'] == 'quality'
        assert {ref['kind'] for ref in manifest['creative_revision_refs']} >= {'plan', 'script', 'quality'}

        videos = [artifact for artifact in manifest['artifacts']
                  if 'video' in artifact['roles'] or artifact['media_type'].startswith('video/')]
        assert len(videos) == 1, (
            'exactly one mp4 master artifact is expected: '
            + json.dumps([item['relative_path'] for item in manifest['artifacts']], ensure_ascii=False))
        master_artifact = videos[0]
        assert master_artifact['media_type'] == 'video/mp4'
        master_path, master_bytes = download_artifact(
            base_url, token, revision_id, master_artifact, run_folder)
        mapping = visual_mapping(base_url, token, revision_id, manifest, run_folder)
        probed = assert_mp4(run_folder, master_path, manifest, mapping, master_artifact)

        events = assert_event_sequence(base_url, token, run_id)
        ledger = assert_ledger(detail)
        support.write_json(run_folder / 'events.json', {'event_types': events})
        support.write_json(run_folder / 'ffprobe.json', probed)

        manifest_sha = support.sha256_file(run_folder / 'bundle-manifest.json')
        master_sha = support.sha256_bytes(master_bytes)
        assert master_sha == master_artifact['sha256']

    database_ledger = assert_database_ledger(support.INSTANCE)
    readback = run_assembly_readback(run_folder, registration_sha)
    summary = {
        'ok': True,
        'instance_id': owner['instance_id'],
        'project_id': support.project_id(),
        'production_id': production_id,
        'run_id': run_id,
        'bundle_ref': bundle_ref,
        'manifest_schema_version': manifest['schema_version'],
        'manifest_saved_sha256': manifest_sha,
        'master_path': str(master_path),
        'master_sha256': master_sha,
        'master_ffprobe': probed,
        'asset': {key: asset[key] for key in ('asset_id', 'sha256', 'size')},
        'events': events,
        'ledger': ledger,
        'database_ledger': database_ledger,
        'assembly_readback': {key: readback.get(key) for key in
                              ('ok', 'preparation_id', 'context_class', 'format', 'assembly_bytes')},
        'registration_sha256': registration_sha,
        'python': session_facts['versions']['python'],
        'ffmpeg': session_facts['versions']['ffmpeg'],
    }
    support.write_json(Path(evidence) / 'chain-summary.json', summary)
