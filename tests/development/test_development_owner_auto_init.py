"""Development Owner auto-initialization (ADR0079) on real instance copies.

Every case is a real `serve-dev` child process against a throwaway copy of the
clean instance; the fixture registration is regenerated from the current checkout
by `tools/testing/local_chain_fixture.py`. The integration instance and the
integration registration slice are never written.

Covered:

* first start without `--development-auto-owner-init` keeps the old refusal;
* first start with the flag writes the binding, the audit and the retained
  production-authorization floor;
* a later start over a removed `Control/` refuses an existing binding;
* a non-empty authorization registry refuses the control bootstrap;
* a deleted audit file refuses the next start.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import local_chain_support as support
from conftest import require_current_registration

DEV_SOURCE = 'development_owner_initialization'


def instance_id(instance: Path) -> str:
    value = support.metadata_value(instance, 'instance_id')
    assert value, f'instance has no instance_id metadata: {instance}'
    return value


def run_dev(evidence: Path, name: str, instance: Path, *, auto_owner_init: bool) -> support.ProbeResult:
    argv = support.dev_host_arguments('serve-dev', port=0, auto_owner_init=auto_owner_init,
                                      data_dir=instance)
    return support.run_probe(name, argv, evidence,
                             env=support.dev_environment(instance_id(instance)), timeout=300)


def start_dev(evidence: Path, name: str, instance: Path, *, auto_owner_init: bool = True,
              token: str | None = None):
    token = token or support.new_token()
    argv = support.dev_host_arguments('serve-dev', port=0, auto_owner_init=auto_owner_init,
                                      data_dir=instance)
    environment = support.dev_environment(instance_id(instance))
    environment['VIDEO_CREATOR_API_TOKEN'] = token
    server = support.launch(name, argv, evidence, env=environment)
    ready = server.wait_for_event('ready', timeout=300)
    return server, ready, token


def test_first_start_without_auto_flag_requires_restore_refresh(evidence, installation, source_status,
                                                                instance_factory) -> None:
    require_current_registration(source_status)
    instance = instance_factory('auto-init-no-flag')
    result = run_dev(evidence, 'auto-init-no-flag', instance, auto_owner_init=False)
    assert result.exit_code == 1, (
        f'a fresh instance without the flag must be refused, got exit {result.exit_code}\n'
        f'stdout={result.stdout_text()}\nstderr={result.stderr_text()}')
    assert result.error_code() == 'owner_restore_refresh_required', (
        f'actual code={result.error_code()!r}\nstderr={result.stderr_text()}')
    state = support.instance_state(evidence, instance, name='auto-init-no-flag-state')
    assert state['owner']['initialized'] is False
    assert state['control_dir_exists'] is False, 'a refused start must not create Control/'
    assert not any(key.startswith('owner_') for key in state['metadata_keys'])
    assert not any(key.startswith('development_owner') for key in state['metadata_keys'])


def test_auto_flag_writes_binding_audit_and_production_control(evidence, installation, source_status,
                                                              instance_factory) -> None:
    require_current_registration(source_status)
    instance = instance_factory('auto-init-flag')
    server, ready, token = start_dev(evidence, 'auto-init-flag', instance)
    try:
        assert ready.get('principal_id') == 'local-user', json.dumps(ready, ensure_ascii=False)
        status, headers, health, raw = support.http_json(ready['base_url'], '/api/v1/health', token=token)
        assert status == 200, f'health returned {status}: {raw[:300]!r}'
        assert headers.get('x-videocreator-installation') == 'local-development'
        assert health['instance_id'] == instance_id(instance)
    finally:
        server.stop()

    state = support.instance_state(evidence, instance, name='auto-init-flag-state')
    owner = state['owner']
    assert owner['initialized'] is True and owner['active'] is True, json.dumps(owner, ensure_ascii=False)
    assert owner['owner_subject'] == 'local-user'
    assert owner['project_ids'] == [installation['project_id']]
    assert owner['principal']['authentication_source'] == DEV_SOURCE, owner['principal']
    assert owner['principal']['administrator_id']
    assert owner['principal']['expires_at_us'] > 0
    assert owner['revoked'] is False
    assert 'owner_management_binding' in state['metadata_keys']
    assert 'development_owner_initialization_audit' in state['metadata_keys']
    assert 'owner.bootstrap.initialize' in state['command_scopes']

    assert state['control_dir_exists'] is True
    for name in ('DevelopmentOwnerInitialization.json', 'OwnerManagementControl.json',
                 'ProductionAuthorizationControl.json'):
        assert name in state['control_files'], (
            f'{name} missing from Control/: {state["control_files"]}')
    assert state['audit_digest_matches'] is True, (
        'the audit file must hash to its committed metadata digest: '
        + json.dumps({key: state[key] for key in ('audit_sha256', 'audit_metadata_digest')}))
    audit = state['audit']
    assert audit['format'] == 'development-owner-initialization-audit-v1'
    assert audit['action'] == 'initialize'
    assert audit['owner_subject'] == 'local-user'
    assert audit['project_ids'] == [installation['project_id']]
    assert audit['instance_id'] == instance_id(instance)
    assert audit['registration']['path'] == str(installation['registration'])
    assert audit['registration']['sha256'] == installation['registration_sha256']
    assert audit['environment'] == {'VIDEO_CREATOR_DEVELOPMENT_INSTALLATION': instance_id(instance)}
    assert audit['process']['role'] == 'api'
    assert audit['process']['frozen'] is False
    assert audit['owner_binding']['generation'] == owner['generation']
    assert audit['owner_binding']['action_id'] == owner['action_id']
    control_record = audit['production_control_created']
    assert control_record['floor'] == 0
    assert control_record['path'] == 'Control/ProductionAuthorizationControl.json'
    assert set(control_record['counts']) == {'production_authorization_policies', 'production_admissions',
                                             'daily_project_authorizations', 'execution_registrations'}
    assert all(value == 0 for value in control_record['counts'].values())
    floor = state['production_control']
    assert floor['format'] == 'production-authorization-control-v1'
    assert floor['instance_id'] == instance_id(instance)
    assert floor['minimum_revision'] == 0
    assert floor['pending_request_sha256'] is None


def test_existing_binding_without_control_is_denied(evidence, installation, source_status,
                                                   instance_factory) -> None:
    require_current_registration(source_status)
    instance = instance_factory('auto-init-existing')
    server, _ready, _token = start_dev(evidence, 'auto-init-existing-first', instance)
    server.stop()
    before = support.instance_state(evidence, instance, name='auto-init-existing-before')
    assert before['owner']['initialized'] is True
    binding_before = support.metadata_value(instance, 'owner_management_binding')
    assert binding_before

    shutil.rmtree(instance / 'Control')
    result = run_dev(evidence, 'auto-init-existing-second', instance, auto_owner_init=True)
    assert result.exit_code == 1, (
        f'an existing binding must never be replaced, got exit {result.exit_code}\n'
        f'stdout={result.stdout_text()}\nstderr={result.stderr_text()}')
    assert result.error_code() == 'development_owner_existing_denied', (
        f'actual code={result.error_code()!r}\nstderr={result.stderr_text()}')
    after = support.instance_state(evidence, instance, name='auto-init-existing-after')
    assert support.metadata_value(instance, 'owner_management_binding') == binding_before, (
        'a denied start must not replace the existing Owner binding row')
    assert after['owner']['initialized'] is False, (
        'the Owner binding is unreadable until its original Control directory is restored')
    # `change()` locks the (recreated) Control directory before it can see the
    # existing binding row, so only the lock file may exist afterwards. No binding,
    # audit, OwnerManagementControl or production floor may be written.
    assert set(after['control_files']) <= {'OwnerManagementControl.lock'}, (
        'a denied start wrote Control state: ' + json.dumps(after['control_files']))
    assert after['audit_file_exists'] is False
    assert after['production_control_exists'] is False


def test_nonempty_authorization_registry_denies_control_bootstrap(evidence, installation, source_status,
                                                                 instance_factory) -> None:
    require_current_registration(source_status)
    instance = instance_factory('auto-init-nonempty')
    support.insert_daily_authorization(instance, instance_id=instance_id(instance))
    result = run_dev(evidence, 'auto-init-nonempty', instance, auto_owner_init=True)
    assert result.exit_code == 1, (
        f'a non-empty authorization registry must refuse the floor, got exit {result.exit_code}\n'
        f'stdout={result.stdout_text()}\nstderr={result.stderr_text()}')
    assert result.error_code() == 'development_control_state_denied', (
        f'actual code={result.error_code()!r}\nstderr={result.stderr_text()}')
    assert 'daily_project_authorizations' in result.stderr_text(), (
        'the refusal message must name the four authorization counts: ' + result.stderr_text())
    state = support.instance_state(evidence, instance, name='auto-init-nonempty-state')
    assert state['owner']['initialized'] is True, 'the Owner binding is written before the floor attempt'
    assert state['production_control_exists'] is False, (
        'the retained production floor must not be created over a non-empty registry')
    assert state['authorization_counts']['daily_project_authorizations'] == 1


def test_deleted_audit_file_refuses_the_next_start(evidence, installation, source_status,
                                                  instance_factory) -> None:
    require_current_registration(source_status)
    instance = instance_factory('auto-init-audit')
    server, _ready, _token = start_dev(evidence, 'auto-init-audit-first', instance)
    server.stop()
    before = support.instance_state(evidence, instance, name='auto-init-audit-before')
    assert before['audit_file_exists'] is True
    assert before['audit_digest_matches'] is True
    digest = before['audit_metadata_digest']

    (instance / 'Control' / 'DevelopmentOwnerInitialization.json').unlink()
    result = run_dev(evidence, 'auto-init-audit-missing', instance, auto_owner_init=False)
    assert result.exit_code == 1, (
        f'a missing audit file must refuse the start, got exit {result.exit_code}\n'
        f'stdout={result.stdout_text()}\nstderr={result.stderr_text()}')
    assert result.error_code() == 'development_owner_audit_missing', (
        f'actual code={result.error_code()!r}\nstderr={result.stderr_text()}')
    assert support.metadata_value(instance, 'development_owner_initialization_audit') == digest, (
        'the committed digest must survive the deleted file (the failure is the missing file)')
    state = support.instance_state(evidence, instance, name='auto-init-audit-after')
    assert state['audit_file_exists'] is False
    assert state['owner']['initialized'] is True
    assert state['production_control_exists'] is True
