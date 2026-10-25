"""ADR0048 pure historical association. No acceptance or current writer source."""

import sqlite3

from video_creator.application.daily_projects import (
    DailyProjectService, GOAL_ACCEPT_SCOPE, GOAL_DENIED_SCOPE, GOAL_INTENT_SCOPE,
    GOAL_INTENT_LIMIT, _AcceptedGoalIntentV2, _DeniedGoal, _parse_goal_intent,
)
from video_creator.application.engine import canonical, digest
from video_creator.application.owner_setup_history import validate_setup_goal_history
from video_creator.application.production_authorization import ProductionAuthorizationService
from video_creator.domain.daily_project_authorization import (
    ProjectGoalAccepted, ProjectGoalReceiptQueryV1, ProjectGoalReceiptAcceptedV1,
    ProjectGoalReceiptPendingV1, ProjectGoalReceiptDeniedV1, ProjectGoalReceiptAbsentV1,
)
from video_creator.domain.errors import EngineError


def _invalid():
    return EngineError('daily_project_result_invalid', 'Original Goal association facts are incomplete or changed', 422)


class _History:
    """Reuse only existing pure parsers/receipt validators; no Daily issuer init."""
    authorization = ProductionAuthorizationService
    _model = DailyProjectService._model
    _action_receipt = DailyProjectService._action_receipt
    _child = DailyProjectService._child
    _original_result = DailyProjectService._original_result

    def __init__(self, engine):
        self.engine = engine

    def _rows(self, reader, subject, key):
        return tuple(tuple(row) for row in reader.execute(
            'SELECT scope,request_sha256,result_json FROM commands WHERE owner=? AND idempotency_key=? AND scope IN (?,?,?) ORDER BY scope',
            (subject, key, GOAL_INTENT_SCOPE, GOAL_ACCEPT_SCOPE, GOAL_DENIED_SCOPE)))

    def _visible(self, actor, project_id):
        if not actor.owned_projects and project_id not in actor.project_ids:
            raise EngineError('not_found', 'Configured owned Goal project not found', 404)

    def _pending_file(self, intent):
        return self._protected_file('AcceptedGoal-' + digest(canonical(intent)) + '.json',
            canonical(intent).encode('utf-8'))

    def _protected_file(self, filename, expected):
        from video_creator.infrastructure.owner_identity import inspect_owner_directory

        root = self.engine.db.data_dir / 'Control'
        directory = inspect_owner_directory(root)
        path = root / filename
        if (len(expected) > GOAL_INTENT_LIMIT or path.is_symlink() or path.is_junction()
                or not path.is_file() or path.stat().st_size != len(expected)):
            raise EngineError('daily_project_intent_invalid', 'Original protected pending Goal bytes are unavailable', 422)
        before = path.stat()
        with path.open('rb') as stream:
            if stream.read(GOAL_INTENT_LIMIT + 1) != expected:
                raise EngineError('daily_project_intent_invalid', 'Original protected pending Goal bytes differ', 422)
        return root, directory, path, (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)

    @staticmethod
    def _pending_current(original):
        from video_creator.infrastructure.owner_identity import inspect_owner_directory

        root, directory, path, identity = original
        after = path.stat()
        if (inspect_owner_directory(root) != directory or path.is_symlink() or path.is_junction()
                or (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) != identity):
            raise EngineError('goal_receipt_unavailable', 'Protected pending facts changed during lookup', 503)

    def resolve(self, actor, query):
        subject, key = actor.subject_id, query.idempotency_key
        goal_sha = digest(canonical(query.goal))
        common = dict(format='project-goal-receipt-association-v1', instance_id=self.engine.instance_id,
            principal_id=subject, original_scope=GOAL_ACCEPT_SCOPE, idempotency_key=key,
            goal_sha256=goal_sha, canonicalization_id='project-goal-pydantic-json-v1')
        pending_file, setup_file, setup_identity, setup_id = None, None, None, None
        path = self.engine.db.path
        if path.is_symlink() or path.is_junction():
            raise EngineError('goal_receipt_unavailable', 'Original metadata path is unavailable', 503)
        original_db = path.stat()
        with self.engine.db.connect_readonly() as reader:
            reader.execute('BEGIN')
            instance = reader.execute("SELECT value FROM metadata WHERE key='instance_id'").fetchone()
            if instance is None or instance[0] != self.engine.instance_id:
                raise _invalid()
            rows = self._rows(reader, subject, key)
            indexed = {row[0]: row for row in rows}
            if len(indexed) != len(rows):
                raise _invalid()
            intent_row, accepted_row, denied_row = (indexed.get(scope) for scope in
                (GOAL_INTENT_SCOPE, GOAL_ACCEPT_SCOPE, GOAL_DENIED_SCOPE))
            intent, receipt = None, None
            if intent_row is not None:
                if (type(intent_row[2]) is not str or len(intent_row[2]) > GOAL_INTENT_LIMIT
                        or len(intent_row[2].encode('utf-8')) > GOAL_INTENT_LIMIT):
                    raise EngineError('daily_project_intent_invalid', 'Original persisted Goal intent is not bounded TEXT', 422)
                intent = _parse_goal_intent(self.authorization, intent_row[2])
                if canonical(intent) != intent_row[2]:
                    raise _invalid()
                self._visible(actor, intent.project_id)
            if accepted_row is not None:
                receipt = self._model(ProjectGoalAccepted, accepted_row[2])
                self._visible(actor, receipt.project_id)
            if any(row[1] != goal_sha for row in rows):
                raise EngineError('idempotency_conflict', 'Goal key belongs to a different original canonical input', 409)
            if accepted_row is not None and denied_row is not None:
                raise _invalid()
            if intent is not None and (intent.instance_id, intent.owner_subject, intent.idempotency_key,
                    intent.goal, intent.goal_sha256) != (self.engine.instance_id, subject, key, query.goal, goal_sha):
                raise _invalid()
            denied = None
            if accepted_row is not None:
                receipt = self._original_result(reader, subject, key, query.goal)
                (child, derivation), _ = self._child(reader, receipt.derivation_ref, subject)
                production = self.engine._production(reader, receipt.production_id, subject)
                if ((derivation.idempotency_key, derivation.goal_sha256, derivation.production_id,
                        derivation.run_id, derivation.request_revision_id, derivation.request_sha256) != (
                        key, goal_sha, receipt.production_id, receipt.run_id, receipt.production.request_revision_id,
                        production['request_sha256']) or digest(production['request_json']) != production['request_sha256']
                        or child.goal_sha256 != goal_sha):
                    raise _invalid()
                if intent is not None and (intent.project_id, intent.production_id, intent.run_id,
                        intent.request_revision_id, canonical(intent.request)) != (receipt.project_id,
                        receipt.production_id, receipt.run_id, receipt.production.request_revision_id, production['request_json']):
                    raise _invalid()
                result = ProjectGoalReceiptAcceptedV1(**common, state='accepted', receipt=receipt)
            elif denied_row is not None:
                if intent is None:
                    raise _invalid()
                denied = self._model(_DeniedGoal, denied_row[2])
                if ((denied.intent_sha256, denied.goal_sha256, denied.owner_subject, denied.instance_id,
                        denied.authorization_ref) != (digest(canonical(intent)), goal_sha, subject,
                        self.engine.instance_id, intent.authorization_ref)
                        or denied.registry_revision > self.authorization._revision(reader)):
                    raise _invalid()
                result = ProjectGoalReceiptDeniedV1(**common, state='denied', reason_code=denied.reason_code,
                    resolved_at_us=denied.resolved_at_us)
            elif intent is not None:
                pending_file = self._pending_file(intent)
                result = ProjectGoalReceiptPendingV1(**common, state='pending')
            else:
                result = ProjectGoalReceiptAbsentV1(**common, state='absent')
            if type(intent) is _AcceptedGoalIntentV2:
                setup_id = intent.accepted_setup_ref.setup_id
                journal = validate_setup_goal_history(self.engine, self.authorization, reader, intent,
                    committed_result=receipt, committed_denial=denied, check_recovery_file=result.state == 'pending')
                if result.state == 'pending':
                    setup_file = self._protected_file('AcceptedOwnerSetup-' + intent.accepted_setup_ref.content_sha256 + '.json',
                        canonical(journal).encode('utf-8'))
                setup_identity = tuple(reader.execute('SELECT * FROM owner_setup_journals WHERE setup_id=?',
                    (setup_id,)).fetchone())
            if pending_file is not None:
                self._pending_current(pending_file)
            if setup_file is not None:
                self._pending_current(setup_file)
        # A fresh coherent read detects commit/terminal changes during file validation.
        with self.engine.db.connect_readonly() as reader:
            reader.execute('BEGIN')
            if self._rows(reader, subject, key) != rows:
                raise EngineError('goal_receipt_unavailable', 'Original Goal facts changed during lookup', 503)
            if setup_id is not None:
                actual = reader.execute('SELECT * FROM owner_setup_journals WHERE setup_id=?', (setup_id,)).fetchone()
                if actual is None or tuple(actual) != setup_identity:
                    raise EngineError('goal_receipt_unavailable', 'Original setup facts changed during lookup', 503)
            instance = reader.execute("SELECT value FROM metadata WHERE key='instance_id'").fetchone()
            if instance is None or instance[0] != self.engine.instance_id:
                raise _invalid()
        after = path.stat()
        if (path.is_symlink() or path.is_junction()
                or (original_db.st_dev, original_db.st_ino) != (after.st_dev, after.st_ino)):
            raise EngineError('goal_receipt_unavailable', 'Original metadata identity changed during lookup', 503)
        if pending_file is not None:
            self._pending_current(pending_file)
        if setup_file is not None:
            self._pending_current(setup_file)
        return result


def lookup_project_goal_receipt(engine, actor, query):
    if type(query) is not ProjectGoalReceiptQueryV1:
        raise EngineError('invalid_request', 'Lookup requires its unique typed query', 422)
    if query.expected_instance_id != engine.instance_id:
        raise EngineError('goal_receipt_instance_conflict', 'Expected instance differs from the actual installation', 409)
    try:
        return _History(engine).resolve(actor, query)
    except EngineError as error:
        if error.status_code == 503:
            raise EngineError('goal_receipt_unavailable', 'Original Goal read facts are unavailable', 503) from None
        raise
    except (OSError, sqlite3.Error):
        raise EngineError('goal_receipt_unavailable', 'Original Goal storage is unavailable', 503) from None
    except (ValueError, TypeError, UnicodeError):
        raise _invalid() from None
