"""Exact historical setup facts for Goal cleanup; no strong source issuance."""

import json

from video_creator.application.bundles import strict_json
from video_creator.application.engine import canonical, digest
from video_creator.application.owner_bootstrap import OwnerBindingRecord
from video_creator.domain import contracts as c
from video_creator.domain.daily_project_authorization import (
    DailyProjectActionReceipt,
    InstallDailyProjectAuthorization,
)
from video_creator.domain.errors import EngineError
from video_creator.domain.native_execution_registration import (
    ExecutionRegistrationActionReceipt,
    InstallNativeExecution,
)
from video_creator.domain.owner_setup_journal import AcceptedSetupJournal

DENIAL_PREFIX = 'owner_setup_goal_denial:'


def _invalid():
    return EngineError('owner_setup_history_invalid', 'Exact original accepted setup facts are incomplete or changed', 422)


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _model(authorization, model, body):
    result = authorization._model(model, body)
    if canonical(result) != body:
        raise _invalid()
    return result


def _stored_json(body):
    if type(body) is not str:
        raise _invalid()
    try:
        return strict_json(body.encode('utf-8'))
    except (ValueError, UnicodeError):
        raise _invalid() from None


def validate_setup_goal_history(engine, authorization, reader, intent, *, committed_result, committed_denial=None,
                                check_recovery_file=True):
    """All hashing/file reads occur before the denial writer.

    The reader records the exact original rows for subsequent same-connection
    equality checks. This never calls OwnerSetupService.recover/_issue/current.
    """
    ref, origin = intent.accepted_setup_ref, intent.draft_origin
    row = reader.execute('SELECT * FROM owner_setup_journals WHERE setup_id=? AND instance_id=? AND owner=?',
        (ref.setup_id, engine.instance_id, intent.owner_subject)).fetchone()
    if (row is None or type(row['accepted_json']) is not str or row['accepted_sha256'] != ref.content_sha256
            or digest(row['accepted_json']) != ref.content_sha256):
        raise _invalid()
    journal = _model(authorization, AcceptedSetupJournal, row['accepted_json'])
    prepared = journal.prepared
    if (prepared.origin != origin or prepared.intent.goal != intent.goal
            or canonical(prepared) != row['preparation_json']
            or digest(row['preparation_json']) != row['preparation_sha256']
            or (row['request_sha256'], row['preparation_key'], row['project_id'], row['project_create_key']) != (
                digest(canonical(prepared.request)), origin.preparation_key, intent.project_id,
                origin.project_draft.create_command_key)
            or row['phase'] not in ('accepted', 'running', 'blocked', 'completed')):
        raise _invalid()
    path = engine.db.data_dir / 'Control' / ('AcceptedOwnerSetup-' + ref.content_sha256 + '.json')
    expected = canonical(journal).encode('utf-8')
    if len(expected) > 32 * 1024 * 1024:
        raise _invalid()
    if not check_recovery_file and committed_result is None and committed_denial is None:
        raise _invalid()
    if check_recovery_file:
        if (path.is_symlink() or path.is_junction() or not path.is_file() or path.stat().st_size != len(expected)):
            raise _invalid()
        with path.open('rb') as stream:
            if stream.read(len(expected) + 1) != expected:
                raise _invalid()
    draft = origin.project_draft
    actual_draft = c.ProjectDraft(**draft.draft.model_dump(), project_id=draft.project_id,
        revision=draft.revision, saved_at_us=draft.saved_at_us)
    create = reader.execute("SELECT request_sha256,result_json FROM commands WHERE owner=? AND scope='project.create' AND idempotency_key=?",
        (intent.owner_subject, draft.create_command_key)).fetchone()
    if (create is None or tuple(create) != (draft.create_request_sha256, canonical(actual_draft))
            or digest(create['result_json']) != draft.create_receipt_sha256):
        raise _invalid()
    # Either complete original resolution can survive later legitimate draft
    # edits; its actual command and independent denied progress must still match.
    if committed_result is None and committed_denial is None:
        actual = reader.execute('SELECT owner,body,revision,saved_at_us FROM projects WHERE id=?', (draft.project_id,)).fetchone()
        if actual is None or tuple(actual) != (intent.owner_subject, canonical(draft.draft), draft.revision, draft.saved_at_us):
            raise _invalid()
    else:
        actual = reader.execute('SELECT owner FROM projects WHERE id=?', (draft.project_id,)).fetchone()
        if actual is None or actual[0] != intent.owner_subject:
            raise _invalid()
    steps = prepared.intent.steps[:-1]
    rows = reader.execute('SELECT * FROM owner_setup_steps WHERE setup_id=? ORDER BY step_id', (ref.setup_id,)).fetchall()
    if {item['step_id'] for item in rows} != {step.step_id for step in steps} or len(rows) != len(steps):
        raise _invalid()
    indexed, receipts = {item['step_id']: item for item in rows}, {}
    scopes = {'owner_initialize': 'owner.bootstrap.initialize', 'execution_install': 'owner.execution.install',
        'creation_install': 'daily.project.install'}
    for step in steps:
        original = indexed[step.step_id]
        raw, sha = original['command_json'], original['command_sha256']
        if (original['original_proposal_sha256'] != step.proposal_sha256 or type(raw) is not str
                or digest(raw) != sha or type(original['receipt_json']) is not str
                or digest(original['receipt_json']) != original['receipt_sha256']):
            raise _invalid()
        command = reader.execute('SELECT request_sha256,result_json FROM commands WHERE owner=? AND scope=? AND idempotency_key=?',
            (intent.owner_subject, scopes[step.type], step.idempotency_key)).fetchone()
        if command is None or tuple(command) != (original['original_request_sha256'], original['receipt_json']):
            raise _invalid()
        if step.type == 'owner_initialize':
            expected_command = {'action': 'initialize', 'action_key': step.idempotency_key, 'instance_id': engine.instance_id,
                'owner_subject': intent.owner_subject, 'project_ids': step.project_ids, 'expires_at_us': step.expires_at_us,
                'scope': 'production.authorization.manage', 'os_subject': prepared.intent.directory.os_subject,
                'directory_device': prepared.intent.directory.device, 'directory_inode': prepared.intent.directory.inode}
            receipt = _model(authorization, OwnerBindingRecord, original['receipt_json'])
            if (raw != _json(expected_command) or original['original_request_sha256'] != sha
                    or digest(canonical(receipt)) != intent.owner_body_sha256
                    or receipt.principal.authentication_source != 'native_owner_session'):
                raise _invalid()
            dependencies = []
        elif step.type == 'execution_install':
            actual_command = _model(authorization, InstallNativeExecution, raw)
            receipt = _model(authorization, ExecutionRegistrationActionReceipt, original['receipt_json'])
            if actual_command != step.proposal or receipt.action != 'install':
                raise _invalid()
            expected_command = {'owner_subject': intent.owner_subject, 'scope': scopes[step.type],
                'idempotency_key': step.idempotency_key, 'action': 'install', 'command': actual_command.model_dump(mode='json')}
            if digest(_json(expected_command)) != original['original_request_sha256']:
                raise _invalid()
            dependencies = []
        else:
            actual_command = _model(authorization, InstallDailyProjectAuthorization, raw)
            receipt = _model(authorization, DailyProjectActionReceipt, original['receipt_json'])
            dependency = receipts.get(step.execution_source.step_id)
            if dependency is None:
                raise _invalid()
            prior, prior_sha = dependency
            roles = {item.role: item.registration_ref for item in actual_command.execution_refs}
            if (set(roles) != {'api', 'mcp', 'worker'}
                    or sorted(canonical(item) for item in roles.values()) != sorted(canonical(item) for item in prior.execution_refs)
                    or actual_command.installed_record_ref != prior.installed_record_ref
                    or receipt.authorization_ref != intent.authorization_ref or receipt.action != 'install'):
                raise _invalid()
            expected_fields = step.model_dump(exclude={'type', 'step_id', 'idempotency_key', 'proposal_sha256', 'execution_source'})
            if actual_command.model_dump(exclude={'installed_record_ref', 'execution_refs'}) != expected_fields:
                raise _invalid()
            expected_command = {'owner_subject': intent.owner_subject, 'scope': scopes[step.type],
                'idempotency_key': step.idempotency_key, 'action': 'install', 'command': actual_command.model_dump(mode='json')}
            if digest(_json(expected_command)) != original['original_request_sha256']:
                raise _invalid()
            dependencies = [{'step_id': step.execution_source.step_id, 'receipt_sha256': prior_sha}]
        if original['dependency_json'] != _json(dependencies):
            raise _invalid()
        receipts[step.step_id] = receipt, original['receipt_sha256']
    planned = reader.execute('SELECT value FROM metadata WHERE key=?', ('owner_setup_goal_ids:' + ref.setup_id,)).fetchone()
    if (planned is None or _stored_json(planned[0]) != [intent.production_id, intent.run_id,
            intent.request_revision_id, intent.derivation_id, intent.receipt_id]
            or prepared.intent.steps[-1].idempotency_key != intent.idempotency_key):
        raise _invalid()
    # Closed matrix: contradictory completed/null history is corruption, not a
    # known expiry condition that may be rewritten into a fresh denied result.
    denial = read_setup_denial(authorization, reader, ref.setup_id)
    if committed_result is not None:
        if (committed_denial is not None or denial is not None
                or (row['goal_result_json'], row['goal_result_sha256'], row['phase']) != (
                    canonical(committed_result), digest(canonical(committed_result)), 'completed')):
            raise _invalid()
    elif committed_denial is not None:
        if ((row['goal_result_json'], row['goal_result_sha256'], row['phase']) != (None, None, 'blocked')
                or denial != committed_denial):
            raise _invalid()
    elif (row['phase'] not in ('accepted', 'running', 'blocked') or denial is not None
            or row['goal_result_json'] is not None or row['goal_result_sha256'] is not None):
        raise _invalid()
    return journal


def denial_progress(intent, denied):
    return _json({'format': 'owner-setup-goal-denial-v1', 'setup_id': intent.accepted_setup_ref.setup_id,
        'accepted_setup_ref': intent.accepted_setup_ref.model_dump(mode='json'), 'goal_idempotency_key': intent.idempotency_key,
        'goal_sha256': intent.goal_sha256, 'intent_sha256': denied.intent_sha256,
        'denied_body': canonical(denied), 'denied_sha256': digest(canonical(denied))})


def read_setup_denial(authorization, connection, setup_id):
    row = connection.execute('SELECT value FROM metadata WHERE key=?', (DENIAL_PREFIX + setup_id,)).fetchone()
    if row is None:
        return None
    from video_creator.application.daily_projects import GOAL_DENIED_SCOPE, _DeniedGoal

    raw = _stored_json(row[0])
    if (type(raw) is not dict or set(raw) != {'format', 'setup_id', 'accepted_setup_ref', 'goal_idempotency_key',
            'goal_sha256', 'intent_sha256', 'denied_body', 'denied_sha256'}
            or _json(raw) != row[0] or raw['format'] != 'owner-setup-goal-denial-v1' or raw['setup_id'] != setup_id):
        raise _invalid()
    denied = _model(authorization, _DeniedGoal, raw['denied_body'])
    original = connection.execute('SELECT request_sha256,result_json FROM commands WHERE owner=? AND scope=? AND idempotency_key=?',
        (denied.owner_subject, GOAL_DENIED_SCOPE, raw['goal_idempotency_key'])).fetchone()
    journal = connection.execute('SELECT accepted_sha256,goal_result_json,phase FROM owner_setup_journals WHERE setup_id=? AND owner=? AND instance_id=?',
        (setup_id, denied.owner_subject, denied.instance_id)).fetchone()
    if (digest(raw['denied_body']) != raw['denied_sha256'] or denied.goal_sha256 != raw['goal_sha256']
            or denied.intent_sha256 != raw['intent_sha256'] or original is None
            or tuple(original) != (raw['goal_sha256'], raw['denied_body']) or journal is None
            or raw['accepted_setup_ref'] != {'setup_id': setup_id, 'content_sha256': journal['accepted_sha256']}
            or journal['goal_result_json'] is not None or journal['phase'] != 'blocked'):
        raise _invalid()
    return denied
