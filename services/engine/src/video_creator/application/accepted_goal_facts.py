"""Exact accepted Goal denial/finish facts, independent of execution current."""

import json
import threading
from contextlib import contextmanager
from dataclasses import dataclass

from video_creator.application.bundles import strict_json
from video_creator.application.engine import canonical, digest
from video_creator.application.owner_fact_sources import assert_local_owner_fact_source
from video_creator.application.owner_setup_history import (
    DENIAL_PREFIX,
    denial_progress,
    validate_setup_goal_history,
)
from video_creator.domain.daily_project_authorization import (
    DailyProjectAuthorizationRef,
)
from video_creator.domain.errors import EngineError
from video_creator.domain.native_execution_registration import (
    ExecutionRegistrationRef,
    InstalledNativeRecordRef,
)


def _invalid(message):
    return EngineError('daily_project_fact_invalid', message, 422)


class _Rows:
    def __init__(self, rows):
        self.rows, self.index = rows, 0

    def fetchone(self):
        if self.index == len(self.rows):
            return None
        row = self.rows[self.index]
        self.index += 1
        return row

    def fetchall(self):
        rows = self.rows[self.index:]
        self.index = len(self.rows)
        return rows

    def __iter__(self):
        return iter(self.fetchall())


class _FactReader:
    """Reads the real connection, retaining exact queried rows, never fixtures."""
    def __init__(self, connection):
        self.connection, self.queries = connection, {}

    def execute(self, statement, parameters=()):
        if not statement.lstrip().upper().startswith('SELECT '):
            raise _invalid('Historical facts reader cannot mutate any ledger')
        parameters = tuple(parameters)
        rows = self.connection.execute(statement, parameters).fetchall()
        # Revision and resolution are checked separately before/after the sole
        # permitted denial write; immutable source rows never get exemptions.
        if statement != "SELECT value FROM metadata WHERE key='production_authorization_registry_revision'":
            key = statement, parameters
            expected = tuple(tuple(row) for row in rows)
            if key in self.queries and self.queries[key] != expected:
                raise _invalid('Historical source changed during its complete read')
            self.queries[key] = expected
        return _Rows(rows)


@dataclass(frozen=True, eq=False, repr=False)
class AcceptedGoalFactContext:
    intent: object
    purpose: str
    reason_code: str | None
    pending_sha256: str
    database_revision: int
    reserved_revision: int
    root: object
    thread_id: int
    _store: object
    _daily: object
    _epoch: object


def _owner_command(reader, bootstrap, owner_subject, expected_sha256):
    rows = reader.execute("SELECT * FROM commands WHERE owner=? AND scope IN ('owner.bootstrap.initialize','owner.bootstrap.renew','owner.bootstrap.revoke')",
        (owner_subject,)).fetchall()
    matched = []
    for row in rows:
        if type(row['result_json']) is not str or digest(row['result_json']) != expected_sha256:
            continue
        owner = bootstrap._decode(row['result_json'])
        action = row['scope'].rsplit('.', 1)[-1]
        proposal = {'action': action, 'action_key': row['idempotency_key'], 'instance_id': bootstrap.engine.instance_id,
            'owner_subject': owner_subject, 'project_ids': owner.principal.project_ids,
            'expires_at_us': owner.principal.expires_at_us, 'scope': 'production.authorization.manage',
            'os_subject': owner.os_subject, 'directory_device': owner.directory_device, 'directory_inode': owner.directory_inode}
        body = json.dumps(proposal, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
        if (row['request_sha256'] != digest(body) or owner.principal.owner_subject != owner_subject
                or owner.revoked != (action == 'revoke') or owner.authorized_at_us > bootstrap.engine.clock()):
            raise _invalid('Historical Owner has no complete original authentic action')
        matched.append(owner)
    if len(matched) != 1:
        raise _invalid('Historical Owner must have one exact original command')
    return matched[0]


def _intent(reader, store, root, document):
    from video_creator.application.daily_projects import (
        GOAL_INTENT_LIMIT,
        GOAL_INTENT_SCOPE,
        INTENT_LOCATOR_PREFIX,
        _parse_goal_intent,
    )

    pending = document.pending_request_sha256
    row = reader.execute('SELECT value FROM metadata WHERE key=?', (INTENT_LOCATOR_PREFIX + pending,)).fetchone()
    if row is None:
        raise EngineError('production_restore_refresh_required', 'Pending floor is not an admitted original Goal namespace', 503)
    if type(row[0]) is not str:
        raise _invalid('Original pending Goal locator is not canonical SQL TEXT')
    try:
        raw = strict_json(row[0].encode('utf-8'))
    except (ValueError, UnicodeError):
        raise _invalid('Original pending Goal locator JSON is damaged') from None
    if (type(raw) is not dict or set(raw) != {'owner_subject', 'idempotency_key', 'goal_sha256', 'intent_sha256'}
            or json.dumps(raw, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) != row[0]
            or raw['intent_sha256'] != pending or raw['owner_subject'] != root.owner_binding.principal.owner_subject):
        raise _invalid('Original pending Goal locator differs from this actual Owner')
    command = reader.execute('SELECT request_sha256,result_json FROM commands WHERE owner=? AND scope=? AND idempotency_key=?',
        (raw['owner_subject'], GOAL_INTENT_SCOPE, raw['idempotency_key'])).fetchone()
    if (command is None or command['request_sha256'] != raw['goal_sha256'] or type(command['result_json']) is not str
            or len(command['result_json'].encode('utf-8')) > GOAL_INTENT_LIMIT or digest(command['result_json']) != pending):
        raise _invalid('Original pending command/body/hash is unavailable')
    intent = _parse_goal_intent(store.authorization, command['result_json'])
    if (canonical(intent) != command['result_json'] or (intent.instance_id, intent.owner_subject,
            intent.idempotency_key, intent.goal_sha256) != (store.engine.instance_id,
            raw['owner_subject'], raw['idempotency_key'], raw['goal_sha256'])):
        raise _invalid('Original accepted Goal identities changed')
    path = store.control.path.parent / ('AcceptedGoal-' + pending + '.json')
    expected = command['result_json'].encode('utf-8')
    if path.is_symlink() or path.is_junction() or not path.is_file() or path.stat().st_size != len(expected):
        raise _invalid('Original protected accepted Goal file is unavailable')
    with path.open('rb') as stream:
        if stream.read(GOAL_INTENT_LIMIT + 1) != expected:
            raise _invalid('Original protected accepted Goal file changed')
    return intent


def _historical_sources(store, daily, reader, root, intent):
    old_owner = _owner_command(reader, store.bootstrap, intent.owner_subject, intent.owner_body_sha256)
    current_owner = _owner_command(reader, store.bootstrap, intent.owner_subject, digest(root.owner_body))
    if current_owner != root.owner_binding or current_owner.generation < old_owner.generation:
        raise _invalid('Original Owner history is not the actual current OS Owner chain')
    parent, _row = daily._record(reader, intent.authorization_ref, intent.owner_subject)
    original = parent.authorization
    if (original.owner_binding_generation, original.owner_binding_action_id, original.authentication_binding_id) != (
            old_owner.generation, old_owner.action_id, old_owner.principal.authentication_binding_id):
        raise _invalid('Original parent differs from its actual historical Owner action')
    from video_creator.domain.production_authorization import AuthorizationActionRef

    if intent.creation_action_ref != AuthorizationActionRef(action_id=parent.creation_action.action_id,
            content_sha256=digest(canonical(parent.creation_action))):
        raise _invalid('Original accepted creation action differs')
    # Check every immutable request field against the original finite template;
    # do not resolve today's embedding/reference defaults for historical facts.
    request, template = intent.request, original.template
    expected_policy = request.policy.model_copy(update={'allowed_provider_routes': tuple(item.route_id for item in template.routes),
        'external_transfer_allowed': template.external_transfer_allowed, 'max_cost': template.max_production_cost,
        'budget_group_id': template.budget_group_id})
    from video_creator.domain import contracts as c

    mode = request.delivery_requirements.alignment_evidence_policy if isinstance(request, c.ProductionRequestV03) else 'strict_reference_v1'
    if (request.policy != expected_policy or request.automation.max_revision_cycles != template.max_revision_cycles
            or mode not in template.alignment_modes):
        raise _invalid('Original normalized request differs from its finite template')
    reason = None
    now = store.engine.clock()
    if (current_owner.generation != old_owner.generation or current_owner.revoked
            or current_owner.principal.expires_at_us <= now):
        reason = 'production_management_denied'
    if parent.revoked or original.expires_at_us <= now:
        reason = reason or 'daily_project_authorization_inactive'
    if not parent.current:
        replacements = reader.execute('SELECT authorization_id,revision,content_sha256 FROM daily_project_authorizations '
            'WHERE authorization_id=? AND owner=? AND instance_id=? AND current=1',
            (original.authorization_id, intent.owner_subject, store.engine.instance_id)).fetchall()
        if len(replacements) != 1:
            raise _invalid('Noncurrent parent has no exact authentic replacement')
        replacement, _row = daily._record(reader, DailyProjectAuthorizationRef(authorization_id=replacements[0][0],
            revision=replacements[0][1], content_sha256=replacements[0][2]), intent.owner_subject)
        if replacement.authorization.revision <= original.revision or replacement.creation_action.action != 'replace':
            raise _invalid('Parent replacement has no actual original replacement action')
        reason = reason or 'daily_project_authorization_inactive'
    revision = store.authorization._revision(reader)
    for role in original.execution_refs:
        record, _registration, installed = store._record(reader, role.registration_ref, intent.owner_subject, revision, [])
        body = record.registration
        if (record.installed_record_ref != original.installed_record_ref or body.role != role.role
                or (body.owner_binding_generation, body.owner_binding_action_id, body.authentication_binding_id) != (
                    old_owner.generation, old_owner.action_id, old_owner.principal.authentication_binding_id)
                or (record.installed_record.os_subject, record.installed_record.directory_device, record.installed_record.directory_inode) != (
                    old_owner.os_subject, old_owner.directory_device, old_owner.directory_inode)):
            raise _invalid('Original complete installed role differs from its authenticated historical Owner')
        if record.revoked or installed['revoked'] or body.expires_at_us <= now:
            reason = reason or 'execution_registration_inactive'
        if not record.current:
            candidates = reader.execute('SELECT registration_id,revision,content_sha256 FROM execution_registrations '
                'WHERE instance_id=? AND owner=? AND role=? AND current=1',
                (store.engine.instance_id, intent.owner_subject, role.role)).fetchall()
            if len(candidates) != 1:
                raise _invalid('Noncurrent role lacks an authentic current replacement')
            successor, _r, _i = store._record(reader, ExecutionRegistrationRef(registration_id=candidates[0][0],
                revision=candidates[0][1], content_sha256=candidates[0][2]), intent.owner_subject, revision, [])
            action = successor.selection_action or successor.installation_action
            if action.action not in ('replace', 'select') or action.registry_revision <= record.installation_action.registry_revision:
                raise _invalid('Noncurrent role has no actual replacement/selection action')
            reason = reason or 'execution_registration_inactive'
        if not installed['current']:
            candidates = reader.execute('SELECT record_id,revision,content_sha256 FROM installed_native_records '
                'WHERE record_id=? AND instance_id=? AND owner=? AND current=1',
                (record.installed_record_ref.record_id, store.engine.instance_id, intent.owner_subject)).fetchall()
            if len(candidates) != 1:
                raise _invalid('Noncurrent installed record lacks an authentic replacement')
            successor, successor_row = store._installed(reader, InstalledNativeRecordRef(record_id=candidates[0][0],
                revision=candidates[0][1], content_sha256=candidates[0][2]), intent.owner_subject, revision, [])
            replacement = store._read_action(reader, successor_row, 'installation_action', intent.owner_subject, revision, [])
            if successor.revision <= record.installed_record_ref.revision or replacement.action != 'replace':
                raise _invalid('Installed replacement has no actual original action')
            reason = reason or 'execution_registration_inactive'
    return reason


def _committed_acceptance_facts(store, daily, reader, intent, result, reserved_revision):
    """Bind real committed leaf data to the independent protected intent.

    Reconstructing the expected immutable child policy is an equality check,
    not an execution identity, current scope or authorization issuance.
    """
    from video_creator.domain.production_authorization import (
        ProductionAuthorizationPolicy,
    )

    (child, receipt), _row = daily._child(reader, result.derivation_ref, intent.owner_subject,
        parent_ref=intent.authorization_ref)
    parent, _parent_row = daily._record(reader, intent.authorization_ref, intent.owner_subject)
    production = store.engine._production(reader, intent.production_id, intent.owner_subject)
    run = store.engine._acceptance_run(reader, production)
    original_body, original_sha = canonical(intent.request), digest(canonical(intent.request))
    if ((result.project_id, result.production_id, result.run_id, result.production.request_revision_id,
            result.derivation_ref.derivation_id, receipt.receipt_id) != (
            intent.project_id, intent.production_id, intent.run_id, intent.request_revision_id,
            intent.derivation_id, intent.receipt_id)
            or (production['project_id'], production['id'], production['owner'], production['idempotency_key'],
                production['request_revision_id'], production['request_json'], production['request_sha256'], run['id'], run['production_id']) != (
                intent.project_id, intent.production_id, intent.owner_subject, intent.idempotency_key,
                intent.request_revision_id, original_body, original_sha, intent.run_id, intent.production_id)):
        raise _invalid('Committed original Goal differs from its complete protected planned identities/request')
    if ((receipt.instance_id, receipt.owner_subject, receipt.authorization_ref, receipt.creation_action_ref,
            receipt.derivation_ref, receipt.goal_sha256, receipt.request_sha256, receipt.production_id,
            receipt.run_id, receipt.request_revision_id, receipt.idempotency_key, receipt.accepted_at_us,
            receipt.registry_revision) != (intent.instance_id, intent.owner_subject, intent.authorization_ref,
            intent.creation_action_ref, result.derivation_ref, intent.goal_sha256, original_sha, intent.production_id,
            intent.run_id, intent.request_revision_id, intent.idempotency_key, intent.accepted_at_us, reserved_revision)):
        raise _invalid('Committed derived receipt differs from its original protected acceptance/parent references')
    expected_policy = ProductionAuthorizationPolicy(**parent.authorization.template.model_dump(exclude={'expires_at_us'}),
        instance_id=intent.instance_id, owner_subject=intent.owner_subject, executing_principal_ids=(intent.owner_subject,),
        project_ids=(intent.project_id,), expires_at_us=parent.authorization.expires_at_us)
    if ((child.derivation_id, child.instance_id, child.owner_subject, child.executing_principal_id,
            child.project_id, child.goal_sha256, child.entry, child.authorization_ref, child.creation_action_ref,
            child.installed_record_ref, child.execution_refs, child.expires_at_us, child.derived_policy) != (
            intent.derivation_id, intent.instance_id, intent.owner_subject, intent.owner_subject,
            intent.project_id, intent.goal_sha256, intent.entry, intent.authorization_ref, intent.creation_action_ref,
            parent.authorization.installed_record_ref, parent.authorization.execution_refs,
            parent.authorization.expires_at_us, expected_policy)):
        raise _invalid('Committed child differs from its actual original accepted parent/Goal')


@contextmanager
def accepted_goal_facts(store, root):
    assert_local_owner_fact_source(store.bootstrap, root)
    daily = store._fact_daily
    if daily is None or daily.registrations is not store or daily.engine is not store.engine:
        raise EngineError('daily_project_fact_unconfigured', 'Original facts-only Daily assembly is required', 503)
    if not store._lock.acquire(blocking=False):
        raise EngineError('execution_registration_busy', 'Original registration is being checked by another context', 503)
    context = None
    try:
        with store.control.locked():
            document = store.control.read()
            if document.pending_request_sha256 is None:
                yield None
                return
            with store.engine.db.connect() as connection:
                reader = _FactReader(connection)
                revision = store.authorization._revision(reader)
                if revision not in (document.minimum_revision, document.minimum_revision - 1):
                    raise _invalid('Pending original Goal floor/DB revisions disagree')
                intent = _intent(reader, store, root, document)
                reason = _historical_sources(store, daily, reader, root, intent)
                from video_creator.application.daily_projects import (
                    GOAL_ACCEPT_SCOPE,
                    GOAL_DENIED_SCOPE,
                    _AcceptedGoalIntentV2,
                    _DeniedGoal,
                )

                results = connection.execute('SELECT scope,request_sha256,result_json FROM commands WHERE owner=? AND scope IN (?,?) AND idempotency_key=?',
                    (intent.owner_subject, GOAL_ACCEPT_SCOPE, GOAL_DENIED_SCOPE, intent.idempotency_key)).fetchall()
                if len(results) > 1 or results and results[0]['request_sha256'] != intent.goal_sha256:
                    raise _invalid('Original Goal has conflicting resolution commands')
                result = None
                if results:
                    if revision != document.minimum_revision:
                        raise _invalid('Committed original Goal revision differs from its exact floor')
                    if results[0]['scope'] == GOAL_ACCEPT_SCOPE:
                        result = daily._original_result(reader, intent.owner_subject, intent.idempotency_key, intent.goal)
                        _committed_acceptance_facts(store, daily, reader, intent, result, document.minimum_revision)
                    else:
                        result = daily._model(_DeniedGoal, results[0]['result_json'])
                        if (result.intent_sha256, result.registry_revision, result.authorization_ref, result.goal_sha256,
                                result.owner_subject, result.instance_id) != (document.pending_request_sha256, revision,
                                intent.authorization_ref, intent.goal_sha256, intent.owner_subject, store.engine.instance_id):
                            raise _invalid('Committed original denied receipt differs from its exact reservation')
                    purpose = 'finish_committed'
                else:
                    if document.minimum_revision != revision + 1:
                        raise _invalid('Uncommitted original Goal does not own its exact next floor')
                    for sql, parameters in (
                        ('SELECT id FROM productions WHERE id=? OR project_id=?', (intent.production_id, intent.project_id)),
                        ('SELECT id FROM runs WHERE id=? OR production_id=?', (intent.run_id, intent.production_id)),
                        ('SELECT derivation_id FROM project_scope_derivations WHERE derivation_id=? OR project_id=?', (intent.derivation_id, intent.project_id)),
                    ):
                        if reader.execute(sql, parameters).fetchall():
                            raise _invalid('Uncommitted Goal has partial original creation side effects')
                    purpose = 'deny_uncommitted' if reason is not None else None
                if type(intent) is _AcceptedGoalIntentV2:
                    committed = result if results and results[0]['scope'] == GOAL_ACCEPT_SCOPE else None
                    committed_denial = result if results and results[0]['scope'] == GOAL_DENIED_SCOPE else None
                    validate_setup_goal_history(store.engine, store.authorization, reader, intent,
                        committed_result=committed, committed_denial=committed_denial)
                    if not results and reader.execute('SELECT value FROM metadata WHERE key=?',
                            (DENIAL_PREFIX + intent.accepted_setup_ref.setup_id,)).fetchone() is not None:
                        raise _invalid('Uncommitted setup already has another denial association')
                if purpose is None:
                    yield None
                    return
                denied = _DeniedGoal(intent_sha256=document.pending_request_sha256, goal_sha256=intent.goal_sha256,
                    authorization_ref=intent.authorization_ref, owner_subject=intent.owner_subject, instance_id=store.engine.instance_id,
                    reason_code=reason, resolved_at_us=store.engine.clock(), registry_revision=document.minimum_revision) if purpose == 'deny_uncommitted' else None
                context = AcceptedGoalFactContext(intent, purpose, reason, document.pending_request_sha256,
                    revision, document.minimum_revision, root, threading.get_ident(), store, daily, store._fact_epoch)
                state = {'queries': reader.queries, 'result_rows': tuple(tuple(row) for row in results), 'resolved': False,
                    'denied': denied, 'denied_body': canonical(denied) if denied is not None else None,
                    'progress': denial_progress(intent, denied) if denied is not None and type(intent) is _AcceptedGoalIntentV2 else None}
                store._goal_facts[context] = state
            assert_local_owner_fact_source(store.bootstrap, root)
            yield context
            assert_local_owner_fact_source(store.bootstrap, root)
    finally:
        if context is not None:
            store._goal_facts.pop(context, None)
        store._lock.release()


def assert_goal_fact_writer(store, connection, context):
    if (type(context) is not AcceptedGoalFactContext or context._store is not store or context._epoch is not store._fact_epoch
            or context not in store._goal_facts or context.thread_id != threading.get_ident()
            or context._daily is not store._fact_daily):
        raise EngineError('daily_project_fact_source_denied', 'Original live Store/thread facts context is required', 403)
    assert_local_owner_fact_source(store.bootstrap, context.root, connection=connection)
    state = store._goal_facts[context]
    if context.root.native_connection is not None:
        from video_creator.application.native_goal_facts_startup import (
            assert_native_startup_fact_writer,
        )

        assert_native_startup_fact_writer(store, connection, context)
    expected_revision = context.reserved_revision if state['resolved'] else context.database_revision
    if store.authorization._revision(connection) != expected_revision:
        raise _invalid('Original Goal registry revision changed before completion')
    for (statement, parameters), expected in state['queries'].items():
        actual = tuple(tuple(row) for row in connection.execute(statement, parameters).fetchall())
        if state['resolved'] and state['progress'] is not None and statement.startswith('SELECT * FROM owner_setup_journals '):
            columns = [item[0] for item in connection.execute(statement, parameters).description]
            phase_index = columns.index('phase')
            expected = tuple(tuple('blocked' if i == phase_index else value for i, value in enumerate(row)) for row in expected)
        if actual != expected:
            if (state['resolved'] and state['progress'] is not None and statement == 'SELECT value FROM metadata WHERE key=?'
                    and parameters == (DENIAL_PREFIX + context.intent.accepted_setup_ref.setup_id,)
                    and actual == ((state['progress'],),) and expected == ()):
                continue
            raise _invalid('Original accepted Goal source rows/commands changed before completion')
    from video_creator.application.daily_projects import (
        GOAL_ACCEPT_SCOPE,
        GOAL_DENIED_SCOPE,
    )

    rows = tuple(tuple(row) for row in connection.execute('SELECT scope,request_sha256,result_json FROM commands WHERE owner=? AND scope IN (?,?) AND idempotency_key=?',
        (context.intent.owner_subject, GOAL_ACCEPT_SCOPE, GOAL_DENIED_SCOPE, context.intent.idempotency_key)).fetchall())
    expected = ((GOAL_DENIED_SCOPE, context.intent.goal_sha256, state['denied_body']),) if state['resolved'] else state['result_rows']
    if rows != expected:
        raise _invalid('Original Goal resolution changed before exact completion')


def resolve_accepted_goal_fact(daily, context):
    store = daily.registrations
    if type(context) is not AcceptedGoalFactContext or context._daily is not daily:
        raise EngineError('daily_project_fact_source_denied', 'Original same-Daily facts context is required', 403)
    from video_creator.application.daily_projects import GOAL_DENIED_SCOPE

    state = store._goal_facts.get(context)
    if state is None:
        raise EngineError('daily_project_fact_source_denied', 'Closed facts contexts cannot be revived', 403)
    if context.purpose == 'deny_uncommitted':
        with daily.engine.db.transaction() as writer:
            assert_goal_fact_writer(store, writer, context)
            writer.execute('INSERT INTO commands VALUES(?,?,?,?,?)', (context.intent.owner_subject,
                GOAL_DENIED_SCOPE, context.intent.idempotency_key, context.intent.goal_sha256, state['denied_body']))
            writer.execute("UPDATE metadata SET value=? WHERE key='production_authorization_registry_revision'", (str(context.reserved_revision),))
            if state['progress'] is not None:
                setup_id = context.intent.accepted_setup_ref.setup_id
                writer.execute("UPDATE owner_setup_journals SET phase='blocked' WHERE setup_id=? AND goal_result_json IS NULL", (setup_id,))
                for key, value in ((DENIAL_PREFIX + setup_id, state['progress']), ('owner_setup_block:' + setup_id, context.reason_code)):
                    writer.execute('INSERT INTO metadata VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key, value))
            state['resolved'] = True
            assert_goal_fact_writer(store, writer, context)
    elif context.purpose == 'finish_committed':
        with daily.engine.db.connect() as reader:
            assert_goal_fact_writer(store, reader, context)
    else:
        raise EngineError('daily_project_fact_source_denied', 'Facts context has no admitted cleanup purpose', 403)
    # The original held floor is checked again, outside every DB writer. No
    # reserve/new action is issued and a competing/unknown floor cannot clear.
    assert_local_owner_fact_source(store.bootstrap, context.root)
    if context.root.native_connection is not None:
        # Same original source and complete cached rows immediately before
        # completing the floor; this is a read, with no OS/hash/RPC in it.
        with daily.engine.db.connect() as reader:
            assert_goal_fact_writer(store, reader, context)
    document = store.control.read()
    if (document.minimum_revision, document.pending_request_sha256) != (context.reserved_revision, context.pending_sha256):
        raise _invalid('Original floor changed before exact complete')
    store.control.complete(context.reserved_revision, context.pending_sha256)
