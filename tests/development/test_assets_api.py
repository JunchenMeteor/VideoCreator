"""Asset listing and revision review fields exposed to the workbench."""
import json
import os
from pathlib import Path

from fastapi.testclient import TestClient

from video_creator.api.app import create_app
from video_creator.application.engine import EngineService


def _client(tmp_path):
    os.environ['VIDEO_CREATOR_MIGRATIONS_DIR'] = str(Path(__file__).resolve().parents[2] / 'services/engine/migrations')
    engine = EngineService(Path(tmp_path))
    app = create_app(engine, 't' * 64, allowed_origins=('http://127.0.0.1:1420',),
                     allowed_hosts=('127.0.0.1',))
    return engine, TestClient(app, base_url='http://127.0.0.1')


def test_assets_page_is_metadata_only_and_owner_scoped(tmp_path):
    engine, client = _client(tmp_path)
    with engine.db.transaction() as connection:
        connection.execute("INSERT INTO assets VALUES(?,?,?,?,?,?,?,?,?)",
                           ('asset-a', 'local-user', 'a' * 64, 12, 'audio/wav', 'upload', 'user_asserted', '{}', 100))
        connection.execute("INSERT INTO assets VALUES(?,?,?,?,?,?,?,?,?)",
                           ('asset-b', 'local-user', 'b' * 64, 34, 'video/mp4', 'upload', 'user_asserted', '{}', 200))
        connection.execute("INSERT INTO assets VALUES(?,?,?,?,?,?,?,?,?)",
                           ('asset-other', 'another-user', 'c' * 64, 56, 'audio/wav', 'upload', 'user_asserted', '{}', 300))
    headers = {'Authorization': 'Bearer ' + 't' * 64}
    response = client.get('/api/v1/assets?limit=1', headers=headers)
    assert response.status_code == 200, response.text
    page = response.json()
    assert len(page['assets']) == 1 and page['assets'][0]['asset_id'] == 'asset-a'
    assert page['assets'][0]['sha256_prefix'] == 'a' * 12
    assert page['assets'][0]['bytes'] == 12 and page['assets'][0]['created_at_us'] == 100
    assert 'probe' not in page['assets'][0] and 'path' not in page['assets'][0]
    assert page['next_cursor'] is not None
    next_page = client.get('/api/v1/assets?limit=1&cursor=' + page['next_cursor'], headers=headers).json()
    assert [item['asset_id'] for item in next_page['assets']] == ['asset-b']
    audio = client.get('/api/v1/assets?media_type=audio%2Fwav', headers=headers).json()
    assert [item['asset_id'] for item in audio['assets']] == ['asset-a']
    unknown = client.get('/api/v1/assets?media_type=video%2Fmp4&cursor=bad', headers=headers)
    assert unknown.status_code == 400


def test_production_revisions_exposes_expiry_and_failure(tmp_path):
    engine, client = _client(tmp_path)
    with engine.db.transaction() as connection:
        connection.execute("INSERT INTO projects(id,owner,body,revision,saved_at_us) VALUES(?,?,?,?,?)",
                           ('project-a', 'local-user', json.dumps({'name': 'P', 'source_text': ''}), 1, 1))
        connection.execute("INSERT INTO productions(id,project_id,owner,idempotency_key,request_sha256,request_revision_id,request_json,status,cap_units,created_at_us) VALUES(?,?,?,?,?,?,?,?,0,1)",
                           ('production-a', 'project-a', 'local-user', 'key', 'a' * 64, 'request-a', '{}', 'waiting_user'))
        connection.execute("INSERT INTO runs VALUES(?,?,'waiting_user',NULL,0,1,1,0,NULL,0)",
                           ('run-a', 'production-a'))
        body = json.dumps({'revision_id': 'quality-a', 'kind': 'quality', 'parent_revision_id': None, 'body': {'code': 'quality_failed', 'expires_at_us': 123456789}})
        connection.execute("INSERT INTO creative_revisions VALUES(?,?,?,?,?,?)",
                           ('quality-a', 'production-a', 'run-a', 'quality', body,
                            __import__('hashlib').sha256(body.encode()).hexdigest()))
    headers = {'Authorization': 'Bearer ' + 't' * 64}
    response = client.get('/api/v1/productions/production-a/revisions', headers=headers)
    assert response.status_code == 200, response.text
    item = response.json()[0]
    assert item['revision_id'] == 'quality-a' and item['kind'] == 'quality'
    assert item['expires_at_us'] == 123456789 and item['failure_code'] == 'quality_failed'


def test_openapi_contains_asset_and_revision_fields(tmp_path):
    _, client = _client(tmp_path)
    schema = client.get('/openapi.json').json()
    assets = schema['paths']['/api/v1/assets']['get']
    assert '200' in assets['responses']
    assert 'AssetPageV1' in schema['components']['schemas']
    revision = schema['components']['schemas']['ProductionRevisionSummary']
    assert {'expires_at_us', 'failure_code'} <= set(revision['properties'])
