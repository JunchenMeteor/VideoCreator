"""Exact registered child ASR association, usable by original reconcile readers."""

import json

from video_creator.application.engine import digest
from video_creator.domain.errors import EngineError


def registered_child_asr(connection, engine, run, step_key):
    from video_creator.application.bundles import strict_json
    matches = []
    for saved in connection.execute('SELECT value FROM metadata WHERE key LIKE ?', ('current_final_affected_execution:%',)):
        command = strict_json(saved[0].encode('utf-8'))
        child_asr = command.get('child_asr')
        if isinstance(child_asr, dict) and child_asr.get('step_key') == step_key and command.get('binding', {}).get('run_id') == run['id']:
            matches.append((command, child_asr))
    if not matches:
        return None
    if len(matches) != 1:
        raise EngineError('asr_result_scope_denied', 'Exactly one original registered child ASR source required', 403)
    command, child = matches[0]
    required = {'step_key', 'dedupe_key', 'input_sha256', 'route_id', 'audio_asset_id', 'audio_sha256',
                'child_preparation_id', 'child_intent_sha256', 'repair_command_sha256'}
    sha = command.get('repair_command_sha256')
    source = {key: value for key, value in command.items() if key not in {
        'repair_command_sha256', 'source_sha256', 'steps', 'child_preparation_id', 'child_intent_sha256', 'child_asr'}}
    if (set(child) != required or digest(json.dumps(source, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)) != sha
            or child['repair_command_sha256'] != sha or step_key != 'repair-asr-' + sha[:32]
            or child['dedupe_key'] != step_key or child['child_preparation_id'] != command.get('child_preparation_id')
            or child['child_intent_sha256'] != command.get('child_intent_sha256')):
        raise EngineError('asr_result_scope_denied', 'Original complete command/child ASR association changed', 403)
    row = connection.execute('SELECT * FROM bundle_revisions WHERE id=? AND run_id=?', (child['child_preparation_id'], run['id'])).fetchone()
    asset = connection.execute('SELECT * FROM assets WHERE id=? AND owner=?',
        (child['audio_asset_id'], engine._production(connection, run['production_id'])['owner'])).fetchone()
    lineage = connection.execute('SELECT value FROM metadata WHERE key=?', ('current_final_evidence_lineage:' + child['child_preparation_id'],)).fetchone()
    if (row is None or digest(row['intent_json']) != child['child_intent_sha256'] or asset is None
            or asset['sha256'] != child['audio_sha256'] or asset['media_type'] != 'audio/wav' or lineage is None):
        raise EngineError('asr_result_scope_denied', 'Actual same-Run child/audio/lineage required', 403)
    body = strict_json(lineage[0].encode())
    if (body.get('repair_command_sha256') != sha or body.get('child_preparation_id') != row['id']
            or body.get('child_intent_sha256') != child['child_intent_sha256']):
        raise EngineError('asr_result_scope_denied', 'Selected child lineage differs from ASR registration', 403)
    from video_creator.domain.bundle import BundlePreparationIntent
    selected_intent = BundlePreparationIntent.model_validate_json(row['intent_json'])
    if child['audio_asset_id'] not in selected_intent.media_asset_ids:
        raise EngineError('asr_result_scope_denied', 'Original ASR audio is outside selected child masters', 403)
    observed = connection.execute('SELECT value FROM metadata WHERE key=?', ('current_final_affected_masters:' + sha,)).fetchone()
    if observed is None or strict_json(observed[0].encode()).get('effective_media_roles', {}).get('mixed_audio') != child['audio_asset_id']:
        raise EngineError('asr_result_scope_denied', 'Original ASR audio must be the authenticated child mix', 403)
    source_service = getattr(engine, '_registered_plan_source', None)
    runtime = getattr(source_service, '_production_services_runtime', None)
    if runtime is None or child['route_id'] != runtime.config.asr_route_id or child['input_sha256'] != digest(json.dumps({
            'audio_sha256': asset['sha256'], 'resource_manifest_sha256': runtime.config.asr_resource_manifest_sha256}, sort_keys=True)):
        raise EngineError('asr_result_scope_denied', 'Original registered child ASR route/input context changed', 403)
    return child
