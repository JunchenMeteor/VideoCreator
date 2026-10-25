"""Closed command Step lookup in original short writers; no callback authority."""

from video_creator.application.engine import digest
from video_creator.domain.errors import EngineError


def assert_affected_step(connection, engine, lease, step_key, input_sha256, *, intent=None, authorization_guard=None):
    if step_key.startswith('component-diagnosis-'):
        service=getattr(engine,'_registered_plan_source',None)
        if service is None:
            raise EngineError('diagnostic_source_denied','Original actual production source required for analysis',403)
        service.assert_diagnostic_analysis_writer(connection,lease,step_key,input_sha256,
            intent=intent,guard=authorization_guard)
        return
    if step_key.startswith(('repair-alignment-', 'bundle-alignment-')):
        from video_creator.application.registered_alignment import assert_registered_alignment_step
        assert_registered_alignment_step(connection, engine, lease, step_key, input_sha256,
            intent=intent, authorization_guard=authorization_guard)
        return
    # Reserved namespace is only a rejection boundary, never a prefix permit.
    if not step_key.startswith(('repair-narration-', 'repair-picture-', 'repair-edit-', 'repair-master-', 'repair-asr-',
                                'repair2-narration-', 'repair2-picture-', 'repair2-edit-', 'repair2-master-')):
        return
    from video_creator.application.bundles import strict_json
    from video_creator.application.affected_repair_service import canonical_body
    from video_creator.application.current_final_evidence_journal import PREFIX, parse_journal
    from video_creator.application.current_production_blockers import bound_context
    from video_creator.application.affected_asr_binding import registered_child_asr
    from video_creator.domain.affected_repair_steps import affected_step_recipe
    run = engine._lease(connection, lease)
    matches = []
    for saved in connection.execute('SELECT value FROM metadata WHERE key LIKE ?', ('current_final_affected_execution:%',)):
        command = strict_json(saved[0].encode())
        if command.get('binding', {}).get('run_id') != lease.run_id:
            continue
        spec = command.get('steps', {}).get(step_key)
        child_asr = command.get('child_asr')
        if spec is None and isinstance(child_asr, dict) and child_asr.get('step_key') == step_key:
            spec = child_asr
        if spec is not None:
            matches.append((command, spec))
    if len(matches) != 1:
        raise EngineError('affected_step_denied', 'One actual registered full command Step required', 403)
    command, spec = matches[0]
    source_service = getattr(engine, '_registered_plan_source', None)
    if source_service is None:
        raise EngineError('affected_step_denied', 'Actual held registered production source required', 403)
    source_service.assert_command_targets_writer(connection, lease, command, guard=authorization_guard)
    source = {key: value for key, value in command.items() if key not in {
        'repair_command_sha256', 'source_sha256', 'steps', 'child_preparation_id', 'child_intent_sha256', 'child_asr'}}
    sha = command.get('repair_command_sha256')
    if digest(canonical_body(source)) != sha or spec['input_sha256'] != input_sha256:
        raise EngineError('affected_step_denied', 'Actual registered full command/input identity required', 403)
    if isinstance(command.get('child_asr'), dict) and command['child_asr']['step_key'] == step_key:
        if registered_child_asr(connection, engine, run, step_key) != spec:
            raise EngineError('affected_step_denied', 'Exact registered child ASR source required', 403)
    elif command.get('format') == 'current-final-affected-execution-v2-diagnostic-v1':
        from video_creator.domain.affected_repair_steps import affected_recipe_step_identity
        if (set(spec)!={'stage','component_target_id','input_sha256','dedupe_key','route_id'}
                or spec['stage'] not in {'narration','picture','edit','master'}
                or spec['component_target_id'] not in (*command['proposal']['component_target_ids'],'production-master')
                or command['requested_action']!='regenerate_affected_media'):
            raise EngineError('affected_step_denied','Exact registered diagnosed component Step required',403)
        expected=affected_recipe_step_identity(command['binding'],sha,spec['stage'],component_target_id=spec['component_target_id'])
        if (step_key,input_sha256,spec['dedupe_key'])!=expected:
            raise EngineError('affected_step_denied','Original diagnosed component recipe changed',403)
    else:
        if (set(spec) != {'stage', 'shot_id', 'input_sha256', 'dedupe_key', 'route_id'}
                or spec['stage'] not in {'narration', 'picture', 'edit', 'master'}
                or command['requested_action'] != 'regenerate_affected_media'
                or (spec['stage'] == 'picture') != (spec['shot_id'] is not None)
                or spec['shot_id'] is not None and spec['shot_id'] not in command['affected_shot_ids']):
            raise EngineError('affected_step_denied', 'Actual bounded registered generation target required', 403)
        expected_key, expected_input, expected_dedupe = affected_step_recipe(command['binding'], sha, spec['stage'], shot_id=spec['shot_id'])
        if (step_key, input_sha256, spec['dedupe_key']) != (expected_key, expected_input, expected_dedupe):
            raise EngineError('affected_step_denied', 'Original deterministic command recipe changed', 403)
    _run, _production, _request, binding = bound_context(engine, connection, lease.run_id, command['binding']['registration_sha256'])
    if command['binding'] != binding.model_dump(mode='json'):
        raise EngineError('affected_step_denied', 'Original actual command request binding changed', 403)
    checkpoint = connection.execute('SELECT value FROM metadata WHERE key=?', (PREFIX + run['id'],)).fetchone()
    if checkpoint is None:
        raise EngineError('final_evidence_claim_required', 'Actual current repair checkpoint required', 409)
    journal = parse_journal(checkpoint[0], now=engine.clock())
    if (journal.binding != binding or journal.control.phase != 'executing'
            or journal.control.execution_fence != lease.fencing_token
            or journal.snapshot.preparation_id not in {command['parent_preparation_id'], command.get('child_preparation_id')}):
        raise EngineError('final_evidence_claim_required', 'Current actual parent/selected child repair claim required', 409)
    if intent is not None and (intent.dedupe_key != spec['dedupe_key'] or intent.route_id != spec['route_id']):
        raise EngineError('affected_step_denied', 'Exact original registered route/dedupe required', 403)
