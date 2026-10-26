"""BYOK credentials never leave the OS vault or enter instance metadata."""

import json
from pathlib import Path

from fastapi.testclient import TestClient
from video_creator.api.app import create_app
from video_creator.application import credentials as credential_store
from video_creator.application.engine import EngineService
from video_creator.domain.errors import EngineError


class FakeVault:
    def __init__(self):
        self.values = {}

    def store_secret(self, identifier, secret):
        self.values[identifier] = secret

    def remove_secret(self, identifier):
        self.values.pop(identifier, None)


def _client(tmp_path, monkeypatch):
    vault = FakeVault()
    monkeypatch.setattr(credential_store, "_vault", lambda: vault)
    engine = EngineService(Path(tmp_path))
    app = create_app(engine, 't' * 64, allowed_origins=('http://127.0.0.1:1420',),
                     allowed_hosts=('127.0.0.1',))
    return engine, vault, TestClient(app, base_url='http://127.0.0.1')


def test_create_list_and_no_secret_in_sqlite_or_registry(tmp_path, monkeypatch):
    _engine, vault, client = _client(tmp_path, monkeypatch)
    headers = {'Authorization': 'Bearer ' + 't' * 64}
    secret = 'sk-real-secret-value-1234567890'
    response = client.post('/api/v1/credentials', json={'provider': 'openai', 'label': 'primary',
                                                         'secret': secret}, headers=headers)
    assert response.status_code == 201, response.text
    item = response.json()
    assert secret not in response.text
    assert set(item) == {'credential_ref', 'fingerprint', 'provider', 'label', 'created_at_us'}
    listed = client.get('/api/v1/credentials', headers=headers).json()
    assert len(listed) == 1 and secret not in json.dumps(listed)
    assert secret not in (Path(tmp_path) / 'Control' / 'Credentials.json').read_text()
    assert secret not in (Path(tmp_path) / 'Control' / 'CredentialAudit.jsonl').read_text()
    for path in Path(tmp_path).rglob('*'):
        if path.is_file():
            assert secret.encode() not in path.read_bytes()
    assert vault.values
    ref = item['credential_ref']
    deleted = client.delete('/api/v1/credentials/' + ref, headers=headers)
    assert deleted.status_code == 204
    assert ref not in vault.values


def test_delete_in_use_returns_references(tmp_path, monkeypatch):
    engine, _vault, client = _client(tmp_path, monkeypatch)
    headers = {'Authorization': 'Bearer ' + 't' * 64}
    item = client.post('/api/v1/credentials', json={'provider': 'openai', 'label': 'p',
                                                     'secret': 'sk-in-use-1234567890'}, headers=headers).json()
    ref = item['credential_ref']
    with engine.db.transaction() as connection:
        connection.execute("INSERT INTO routes(id,body) VALUES(?,?)",
                           ('route-a', json.dumps({'route_id': 'route-a', 'credential_ref': ref})))
    response = client.delete('/api/v1/credentials/' + ref, headers=headers)
    assert response.status_code == 409
    assert response.json()['code'] == 'credential_in_use'
    assert 'route:route-a' in response.json()['references']


def test_external_reference_and_weak_vault(tmp_path, monkeypatch):
    _, _, client = _client(tmp_path, monkeypatch)
    headers = {'Authorization': 'Bearer ' + 't' * 64}
    bad = client.post('/api/v1/credentials', json={'provider': 'openai', 'label': 'p',
                                                    'secret': 'env:OPENAI_KEY'}, headers=headers)
    assert bad.status_code == 422
    assert bad.json()['code'] == 'credential_external_reference_denied'

    def weak():
        class Weak:
            def store_secret(self, identifier, secret):
                raise EngineError('secure_vault_unavailable', 'weak backend', 503)
        return Weak()
    monkeypatch.setattr(credential_store, '_vault', weak)
    response = client.post('/api/v1/credentials', json={'provider': 'openai', 'label': 'p',
                                                         'secret': 'sk-weak-1234567890'}, headers=headers)
    assert response.status_code == 503
    assert response.json()['code'] == 'vault_unavailable'
