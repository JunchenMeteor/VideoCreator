"""R2 first slice: honest budget and unavailable publishing."""

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


def test_budget_without_group_is_not_zero(tmp_path):
    _, client = _client(tmp_path)
    headers = {'Authorization': 'Bearer ' + 't' * 64}
    response = client.get('/api/v1/budget', headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['present'] is False
    assert body['authorization'] == 'none'
    assert body['cap'] == {'kind': 'not_configured', 'amount': None, 'currency': None}
    assert body['spent']['kind'] == 'not_configured'


def test_publish_is_503_unavailable_with_reason(tmp_path):
    _, client = _client(tmp_path)
    headers = {'Authorization': 'Bearer ' + 't' * 64}
    response = client.post('/api/v1/productions/production-a/publish', headers=headers)
    assert response.status_code == 503
    body = response.json()
    assert body['status'] == 'unavailable'
    assert body['code'] == 'publish_unavailable'
    assert body['reason']


def test_preview_local_zero_cost_is_confirmed(tmp_path):
    engine, client = _client(tmp_path)
    from video_creator.domain import contracts as c
    engine.register_route(c.CapabilityRoute(route_id='local.route', capability='render', source='owned_local',
                                            destination='local:render', max_operation_cost=c.Money(amount='0'),
                                            cost_rule_version='local-zero-v1', verified=True))
    headers = {'Authorization': 'Bearer ' + 't' * 64}
    body = {'goal': 'silent local video', 'policy': {'allowed_provider_routes': ['local.route']}}
    response = client.post('/api/v1/productions/preview', json=body, headers=headers)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['cost_basis'] == 'confirmed_no_charge'
    assert result['max_cost'] == {'kind': 'confirmed', 'amount': '0', 'currency': 'CNY'}
    assert result['excluded_reasons'] == []
