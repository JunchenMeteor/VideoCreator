"""One deterministic private Step recipe; deriving a key grants no permission."""

import hashlib
import json

from video_creator.domain.affected_repair import AffectedRepairExecution
from video_creator.domain.errors import EngineError


def affected_master_step(execution: AffectedRepairExecution, stage: str, *, shot_id: str | None = None):
    """Return exact (step_key, input_sha256, dedupe_key) for an admitted target."""
    if stage not in {'narration', 'picture', 'edit', 'master'}:
        raise EngineError('affected_step_invalid', 'Fixed original production stage required', 422)
    if (stage == 'picture') != (shot_id is not None) or shot_id is not None and shot_id not in execution.affected_shot_ids:
        raise EngineError('affected_step_invalid', 'Exactly one original admitted picture shot required', 422)
    if execution.requested_action != 'regenerate_affected_media':
        raise EngineError('affected_step_denied', 'Realignment cannot dispatch generated media', 403)
    if stage == 'narration' and 'narration_audio' not in execution.changed_media_roles:
        raise EngineError('affected_step_denied', 'Original narration is preserved', 403)
    if stage == 'picture' and 'video' not in execution.changed_media_roles:
        raise EngineError('affected_step_denied', 'Original picture track is preserved', 403)
    return affected_step_recipe(execution.binding.model_dump(mode='json'), execution.repair_command_sha256, stage, shot_id=shot_id)


def affected_step_recipe(binding, repair_command_sha256, stage, *, shot_id=None):
    """Pure canonical algorithm also used to verify stored descriptors, never a permit."""
    body = {'format': 'current-affected-step-input-v1', 'binding': binding,
            'repair_command_sha256': repair_command_sha256, 'stage': stage, 'shot_id': shot_id}
    raw = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    sha = hashlib.sha256(raw).hexdigest()
    suffix = repair_command_sha256[:32]
    key = 'repair-' + stage + '-' + suffix + (('-' + hashlib.sha256(shot_id.encode()).hexdigest()[:16]) if shot_id else '')
    return key, sha, key


def affected_recipe_step(execution, stage, *, component_target_id):
    """ADR0058 pure v2 identity; actual service registration is checked separately."""
    from video_creator.domain.affected_recipe import AffectedRepairExecutionV2
    from video_creator.domain.component_diagnosis import AffectedRepairExecutionDiagnosedV1
    if type(execution) not in {AffectedRepairExecutionV2,AffectedRepairExecutionDiagnosedV1} or stage not in {'narration', 'picture', 'edit', 'master'}:
        raise EngineError('affected_step_invalid', 'Sole finite v2 execution data and fixed stage required', 422)
    expected = {'master': ('production-master',), 'narration': ('production-narration',),
                'picture': tuple('production-' + shot for shot in execution.regenerated_shot_ids),
                'edit': ('production-edit.' + execution.recipe_id,)}[stage]
    if (component_target_id not in expected
            or stage != 'master' and component_target_id not in execution.component_target_ids
            or stage == 'narration' and 'narration_audio' not in execution.changed_media_roles):
        raise EngineError('affected_step_denied', 'Exact selected component identity required', 403)
    return affected_recipe_step_identity(execution.binding.model_dump(mode='json'),
        execution.repair_command_sha256, stage, component_target_id=component_target_id)


def affected_recipe_step_identity(binding, repair_command_sha256, stage, *, component_target_id):
    """The same deterministic algorithm verifies a stored v2 descriptor."""
    if stage not in {'narration', 'picture', 'edit', 'master'} or not isinstance(component_target_id, str):
        raise EngineError('affected_step_invalid', 'Fixed v2 stage and original target name required', 422)
    body = {'format': 'current-affected-step-input-v2', 'binding': binding,
            'repair_command_sha256': repair_command_sha256, 'stage': stage,
            'component_target_id': component_target_id}
    raw = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    sha = hashlib.sha256(raw).hexdigest()
    key = ('repair2-' + stage + '-' + repair_command_sha256[:32] + '-'
           + hashlib.sha256(component_target_id.encode('utf-8')).hexdigest()[:16])
    return key, sha, key
