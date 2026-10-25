"""Exact same-connection final-evidence checkpoint checks; no writer authority."""

from pydantic import ValidationError

from video_creator.application.engine import canonical, digest
from video_creator.application.current_production_blockers import bound_context
from video_creator.domain.bundle import BundlePreparationIntent, MaterialReceipt
from video_creator.domain.current_final_evidence import CurrentFinalEvidenceJournal
from video_creator.domain.errors import EngineError

PREFIX = 'current_production_final_evidence:'
LIMIT = 1024 * 1024


def parse_journal(raw, *, now):
    if type(raw) is not str or len(raw.encode('utf-8')) > LIMIT:
        raise EngineError('final_evidence_journal_invalid', 'Original checkpoint must be bounded TEXT', 422)
    try:
        from video_creator.application.bundles import strict_json
        from video_creator.domain.component_diagnosis import CurrentFinalDiagnosticJournalV1
        data = strict_json(raw.encode('utf-8'))
        if not isinstance(data, dict):
            raise ValueError('checkpoint object')
        model = (CurrentFinalDiagnosticJournalV1 if data.get('format') == 'current-production-final-evidence-diagnostic-v1'
                 else CurrentFinalEvidenceJournal)
        journal = model.model_validate_json(raw)
    except (ValidationError, ValueError, TypeError):
        raise EngineError('final_evidence_journal_invalid', 'Original checkpoint grammar is damaged', 422) from None
    if canonical(journal) != raw or journal.last_transition_at_us > now:
        raise EngineError('final_evidence_journal_invalid', 'Original checkpoint canonical bytes/time changed', 422)
    return journal


def prepared_current(engine, connection, journal):
    run, production, request, binding = bound_context(engine, connection, journal.binding.run_id,
        journal.binding.registration_sha256)
    if binding != journal.binding:
        raise EngineError('final_evidence_binding_invalid', 'Checkpoint changed original complete binding', 409)
    snapshot = journal.snapshot
    row = connection.execute('SELECT * FROM bundle_revisions WHERE id=? AND run_id=? AND production_id=? AND request_revision_id=?',
        (snapshot.preparation_id, run['id'], production['id'], production['request_revision_id'])).fetchone()
    if row is None or digest(row['intent_json']) != snapshot.preparation_intent_sha256:
        raise EngineError('final_evidence_preparation_changed', 'Checkpoint original intent is unavailable or changed', 409)
    BundlePreparationIntent.model_validate_json(row['intent_json'])
    for receipt in snapshot.ready_material_refs:
        item = connection.execute('SELECT * FROM bundle_items WHERE preparation_id=? AND artifact_id=? AND status=?',
            (snapshot.preparation_id, receipt.artifact_id, 'ready')).fetchone()
        if item is None or MaterialReceipt(preparation_id=row['id'], artifact_id=item['artifact_id'],
                material_id=item['material_id'], sha256=item['sha256'], size=item['size'],
                media_type=item['media_type'], schema_kind=item['schema_kind']) != receipt:
            raise EngineError('final_evidence_material_changed', 'Original READY material cannot be replaced', 422)
    return row, run, production, request


def require_waiting(run, journal):
    if (journal.control.phase != 'waiting' or run['status'] != 'waiting_user'
            or run['waiting_revision_id'] is not None or run['worker_id'] is not None
            or run['lease_until_us'] != 0 or run['paused'] or run['cancellation_requested']):
        raise EngineError('final_evidence_state_conflict', 'Original unowned non-review wait changed', 409)


def reject_conflicting_wait(connection, run_id):
    for prefix in ('current_production_blocker:', 'production_authorization_wait:'):
        if connection.execute('SELECT 1 FROM metadata WHERE key=?', (prefix + run_id,)).fetchone():
            raise EngineError('final_evidence_wait_conflict', 'Original resource or explicit authorization wait remains', 409)
