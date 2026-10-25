"""Explicit sameRun Owner reauthorization and truthful suspension journal."""

from pydantic import Field

from video_creator.application.delivery_metadata import DeliveryResolver
from video_creator.application.engine import canonical, digest
from video_creator.domain import contracts as c
from video_creator.domain.errors import EngineError
from video_creator.domain.production_authorization import (
    AuthorizationActionRef,
    ProductionAdmissionRef,
    ProductionPolicyRef,
)

WAIT_PREFIX = 'production_authorization_wait:'
BINDING_PREFIX = 'production_authorization_binding:'
AUTHORIZATION_WAIT_CODES = frozenset({
    'production_authorization_unconfigured', 'production_management_unconfigured',
    'production_execution_identity_denied', 'production_policy_selection_missing',
    'production_request_binding_missing', 'production_policy_inactive',
    'production_restore_refresh_required', 'production_policy_action_denied',
    'production_admission_expired', 'production_admission_stale',
    'production_admission_sequence_required', 'production_admission_sequence_stale',
    'production_copy_source_scope_missing', 'local_copy_scope_inactive',
    'local_copy_policy_conflict', 'local_copy_source_scope_denied',
    'local_copy_restore_refresh_required',
    'execution_registration_inactive', 'execution_registration_changed',
    'production_management_denied',
    'daily_project_authorization_inactive', 'daily_project_execution_changed',
    'daily_project_scope_inactive', 'daily_project_execution_denied',
})


class ReauthorizeOriginalProduction(c.Contract):
    """Private management command; actual authenticated admin capability required."""
    production_id: c.Identifier
    run_id: c.Identifier
    request_revision_id: c.Identifier
    request_sha256: c.Sha256
    policy_ref: ProductionPolicyRef


class AuthorizationWait(c.Contract):
    format: str = Field(default='production-authorization-wait-v1', pattern='^production-authorization-wait-v1$')
    instance_id: c.Identifier
    production_id: c.Identifier
    run_id: c.Identifier
    request_revision_id: c.Identifier
    request_sha256: c.Sha256
    target_id: c.Identifier
    blocker_code: c.Identifier
    fencing_token: int | None = Field(default=None, gt=0, strict=True)
    suspended_at_us: int = Field(gt=0, strict=True)


class CurrentPolicyBinding(c.Contract):
    format: str = Field(default='production-current-policy-binding-v1', pattern='^production-current-policy-binding-v1$')
    instance_id: c.Identifier
    production_id: c.Identifier
    run_id: c.Identifier
    request_revision_id: c.Identifier
    request_sha256: c.Sha256
    admission_ref: ProductionAdmissionRef
    reauthorization_action_ref: AuthorizationActionRef
    reauthorization_idempotency_key: c.Identifier


def unresolved_operations(connection, run_id):
    return connection.execute("SELECT id FROM operations WHERE run_id=? AND (status IN ('submitting','pending','unknown') "
        "OR (settled=0 AND status IN ('succeeded','failed'))) LIMIT 1", (run_id,)).fetchone() is not None


def suspend_authorization(engine, connection, run, production, *, blocker_code, target_id, fence=None):
    """Caller has validated original request and optional ordinary lease.

    No Operation/budget row changes. Unknown remains reachable via the existing
    reconciliation path; the normal scheduler skips this journal until actual
    Owner reauthorization. This does not install a new reconciliation driver.
    """
    if run['status'] in {'succeeded', 'failed', 'cancelled', 'cancel_requested'} or run['cancellation_requested']:
        raise EngineError('production_reauthorization_terminal', 'Authorization cannot revive a terminal or cancelling Run', 409)
    wait = AuthorizationWait(instance_id=engine.instance_id, production_id=production['id'], run_id=run['id'],
        request_revision_id=production['request_revision_id'], request_sha256=production['request_sha256'],
        target_id=target_id, blocker_code=blocker_code, fencing_token=fence, suspended_at_us=engine.clock())
    status = 'needs_reconciliation' if unresolved_operations(connection, run['id']) else 'waiting_authorization'
    connection.execute('INSERT INTO metadata(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                       (WAIT_PREFIX + run['id'], canonical(wait)))
    connection.execute('UPDATE runs SET status=?,worker_id=NULL,lease_until_us=0 WHERE id=?', (status, run['id']))
    latest = connection.execute('SELECT id FROM runs WHERE production_id=? ORDER BY rowid DESC LIMIT 1', (production['id'],)).fetchone()
    if latest and latest[0] == run['id']:
        connection.execute('UPDATE productions SET status=? WHERE id=?', (status, production['id']))
    engine._event(connection, engine._run(connection, run['id']), 'production.authorization_required', target_id)
    return wait


def read_wait(engine, connection, production, run):
    row = connection.execute('SELECT value FROM metadata WHERE key=?', (WAIT_PREFIX + run['id'],)).fetchone()
    if not row:
        return None
    try:
        wait = AuthorizationWait.model_validate(DeliveryResolver._json(row[0]))
    except (ValueError, TypeError):
        raise EngineError('production_authorization_wait_invalid', 'Stored authorization wait facts are damaged', 422) from None
    if (wait.instance_id, wait.production_id, wait.run_id, wait.request_revision_id, wait.request_sha256) != (
            engine.instance_id, production['id'], run['id'], production['request_revision_id'], production['request_sha256']):
        raise EngineError('production_authorization_wait_invalid', 'Authorization wait belongs to a different original request', 422)
    return wait


class ProductionReauthorization:
    def __init__(self, issuer):
        self.issuer, self.management, self.engine = issuer, issuer.management_service, issuer.engine

    def _target(self, connection, principal, command):
        production = self.engine._production(connection, command.production_id, principal.owner_subject)
        run = self.engine._run(connection, command.run_id)
        latest = connection.execute('SELECT id FROM runs WHERE production_id=? ORDER BY rowid DESC LIMIT 1', (production['id'],)).fetchone()
        if (not latest or latest[0] != command.run_id or run['production_id'] != production['id']
                or (production['request_revision_id'], production['request_sha256']) != (
                    command.request_revision_id, command.request_sha256)):
            raise EngineError('production_reauthorization_target_conflict', 'Owner action requires the exact original request and latest Run', 409)
        if (production['status'] in {'succeeded', 'failed', 'cancelled', 'cancel_requested'}
                or run['status'] in {'succeeded', 'failed', 'cancelled', 'cancel_requested'} or run['cancellation_requested']):
            raise EngineError('production_reauthorization_terminal', 'Owner authorization cannot revive a terminal or cancelling production', 409)
        request = c.parse_production_request(production['request_json'])
        if request.automation.mode != 'unattended':
            raise EngineError('production_reauthorization_mode_conflict', 'Interactive review cannot be replaced by this policy management action', 409)
        wait = read_wait(self.engine, connection, production, run)
        if run['status'] not in {'queued', 'waiting_authorization', 'needs_reconciliation'} or run['status'] == 'needs_reconciliation' and wait is None:
            raise EngineError('production_reauthorization_state_conflict', 'Actual authorization wait or original unbound queued Run is required', 409)
        if run['worker_id'] is not None or run['lease_until_us'] > self.engine.clock():
            raise EngineError('production_reauthorization_active_lease', 'Actual ordinary ownership must be released before this explicit Owner action', 409)
        return production, run

    def reauthorize(self, capability, idempotency_key, command: ReauthorizeOriginalProduction):
        """No default-policy change can invoke this actual administrative action."""
        principal = self.management._principal(capability, ())
        with self.engine.db.connect() as connection:
            production = self.engine._production(connection, command.production_id, principal.owner_subject)
            projects = (production['project_id'],)
            self.management._principal(capability, projects)
            repeated = connection.execute("SELECT 1 FROM commands WHERE owner=? AND scope='production.authorization.reauthorize' AND idempotency_key=?",
                                          (principal.owner_subject, idempotency_key)).fetchone()
            if not repeated:
                self._target(connection, principal, command)
        if repeated:
            # A real prior action remains idempotent after execution advances;
            # it does not issue new permission or depend on current resources.
            def not_a_new_action(connection):
                raise EngineError('production_action_disappeared', 'Original immutable management command disappeared', 422)
            return self.management._action(capability, idempotency_key, 'reauthorize', command, projects, not_a_new_action,
                target_request=(command.production_id, command.request_revision_id, command.request_sha256))
        registered = self.engine._authorization_identity(production['owner'])
        # Long source/resource rehash outside both DB writer and management
        # mutation. No True callback or expected values from task/results.
        with self.issuer._lock:
            registered = self.issuer._identity(registered)
            observation = self.issuer._installation(registered)

            def prepare(connection):
                target, run = self._target(connection, principal, command)
                request = self.issuer._request(connection, target, run, registered)
                self.issuer._record(connection, command.policy_ref, registered, request, target, action='begin_execution')

                def mutate(writer, receipt):
                    current, current_run = self._target(writer, principal, command)
                    request = self.issuer._request(writer, current, current_run, registered)
                    record = self.issuer._record(writer, command.policy_ref, registered, request, current, action='begin_execution')
                    with self.issuer._management_writer_guard(registered, observation, self.management._revision(writer)) as guard:
                        fact = self.issuer._persist(writer, guard, current, current_run, request, record,
                            phase='request', action='bind_request', target_kind='request',
                            target_id=current['request_revision_id'], target_sha256=current['request_sha256'], fence=None)
                    pointer = CurrentPolicyBinding(instance_id=self.engine.instance_id, production_id=current['id'],
                        run_id=current_run['id'], request_revision_id=current['request_revision_id'], request_sha256=current['request_sha256'],
                        admission_ref=ProductionAdmissionRef(admission_id=fact.admission_id, content_sha256=digest(canonical(fact))),
                        reauthorization_action_ref=AuthorizationActionRef(action_id=receipt.action_id, content_sha256=digest(canonical(receipt))),
                        reauthorization_idempotency_key=receipt.idempotency_key)
                    writer.execute('INSERT INTO metadata VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                                   (BINDING_PREFIX + current_run['id'], canonical(pointer)))
                    writer.execute('DELETE FROM metadata WHERE key=?', (WAIT_PREFIX + current_run['id'],))
                    status = 'needs_reconciliation' if unresolved_operations(writer, current_run['id']) else 'queued'
                    writer.execute('UPDATE runs SET status=?,worker_id=NULL,lease_until_us=0 WHERE id=?', (status, current_run['id']))
                    writer.execute('UPDATE productions SET status=? WHERE id=?', (status, current['id']))
                    self.engine._event(writer, self.engine._run(writer, current_run['id']), 'production.reauthorized', current['request_revision_id'])
                return command.policy_ref, mutate

            with self.issuer._qualified_management_preflight(registered,observation):
                return self.management._action(capability, idempotency_key, 'reauthorize', command, projects, prepare,
                    target_request=(command.production_id, command.request_revision_id, command.request_sha256))
