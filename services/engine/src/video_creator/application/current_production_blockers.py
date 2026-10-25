"""Fixed same-connection progress checks; no policy, provider or permission minting."""
from pydantic import ValidationError

from video_creator.application.engine import canonical, digest
from video_creator.domain import contracts as c
from video_creator.domain.errors import EngineError
from video_creator.domain.registered_production import CurrentProductionBlockerJournal, ProductionBinding

PREFIX = 'current_production_blocker:'
LIMIT = 1024 * 1024


def parse_journal(raw, *, now):
    if type(raw) is not str or len(raw.encode('utf-8')) > LIMIT:
        raise EngineError('production_blocker_invalid', 'Original blocker must be bounded canonical TEXT', 422)
    try:
        from video_creator.domain.local_bundle import CurrentProductionBlockerJournalV2
        import json
        value = json.loads(raw)
        model = CurrentProductionBlockerJournalV2 if isinstance(value, dict) and value.get('format') == 'current-production-blocker-v2' else CurrentProductionBlockerJournal
        journal = model.model_validate(value)
    except (ValidationError, ValueError):
        raise EngineError('production_blocker_invalid', 'Original blocker grammar is damaged', 422) from None
    if canonical(journal) != raw or journal.blocked_at_us > now:
        raise EngineError('production_blocker_invalid', 'Original blocker bytes or service time are damaged', 422)
    return journal


def bound_context(engine, connection, run_id, registration_sha256):
    instance = connection.execute("SELECT value FROM metadata WHERE key='instance_id'").fetchone()
    if instance is None or instance[0] != engine.instance_id:
        raise EngineError('production_blocker_instance_changed', 'Original same-connection instance identity changed', 409)
    run = engine._run(connection, run_id)
    production = engine._production(connection, run['production_id'])
    latest = connection.execute('SELECT id FROM runs WHERE production_id=? ORDER BY rowid DESC LIMIT 1',
        (production['id'],)).fetchone()
    if latest is None or latest[0] != run_id:
        raise EngineError('production_blocker_superseded', 'Only the original latest Production Run can change progress', 409)
    if type(production['request_json']) is not str:
        raise EngineError('production_request_changed', 'Original request body must be TEXT', 422)
    request = c.parse_production_request(production['request_json'])
    if digest(production['request_json']) != production['request_sha256'] or canonical(request) != production['request_json']:
        raise EngineError('production_request_changed', 'Original immutable request body or hash is damaged', 422)
    row = connection.execute('SELECT * FROM execution_bindings WHERE run_id=?', (run_id,)).fetchone()
    if (row is None or type(row['body']) is not str or len(row['body'].encode('utf-8')) > LIMIT
            or digest(row['body']) != row['content_sha256']):
        raise EngineError('production_blocker_binding_invalid', 'Original complete execution binding is missing or damaged', 422)
    try:
        binding = ProductionBinding.model_validate_json(row['body'])
    except ValidationError:
        raise EngineError('production_blocker_binding_invalid', 'Original execution binding grammar is damaged', 422) from None
    if canonical(binding) != row['body']:
        raise EngineError('production_blocker_binding_invalid', 'Original binding bytes are not canonical', 422)
    if (binding.instance_id, binding.production_id, binding.run_id, binding.request_revision_id,
            binding.request_sha256, binding.registration_sha256) != (
            engine.instance_id, production['id'], run_id, production['request_revision_id'],
            production['request_sha256'], registration_sha256):
        raise EngineError('production_blocker_binding_conflict', 'Original request/Run/instance/registration differs', 409)
    assets = []
    for asset_id in request.inputs.asset_ids:
        asset = connection.execute('SELECT sha256 FROM assets WHERE id=? AND owner=?',
            (asset_id, production['owner'])).fetchone()
        if asset is None:
            raise EngineError('production_blocker_input_invalid', 'Original owned input Asset is unavailable', 422)
        assets.append((asset_id, asset[0]))
    if binding.input_assets != tuple(assets):
        raise EngineError('production_blocker_binding_invalid', 'Original ordered input Asset identities changed', 422)
    return run, production, request, binding


def unsettled(connection, run_id):
    return connection.execute("SELECT 1 FROM operations WHERE run_id=? AND (settled=0 OR status IN ('submitting','pending','unknown')) LIMIT 1",
        (run_id,)).fetchone() is not None


def require_settled(connection, run_id):
    if unsettled(connection, run_id):
        raise EngineError('production_blocker_reconciliation_required', 'Original unsettled effects require ledger reconciliation', 409, 'reconcile')


def require_wait(run, journal):
    if (run['status'] != 'waiting_user' or run['waiting_revision_id'] is not None
            or run['worker_id'] is not None or run['lease_until_us'] != 0
            or run['fencing_token'] != journal.result.fencing_token
            or run['paused'] or run['cancellation_requested']):
        raise EngineError('production_blocker_state_conflict', 'Original unowned non-review wait changed, paused or cancelled', 409)
