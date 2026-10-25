"""One finite data mapper; input/output objects never authorize side effects."""

from video_creator.domain import contracts as c
from video_creator.domain.affected_recipe import AffectedRepairProposalV2, ROLE_ORDER
from video_creator.domain.errors import EngineError
from video_creator.domain.plan_repair_targets import plan_payload_sha256


def _half_up(numerator, denominator):
    return (2 * numerator + denominator) // (2 * denominator)


def failed_timeline_ranges(boundaries, failed_unit_ids, *, coordinate, mapping, audio_sha256):
    """Map only original authenticated ranges; require complete source coverage."""
    selected = tuple(value for value in boundaries if value.transcript_unit_id in failed_unit_ids)
    if tuple(value.transcript_unit_id for value in selected) != tuple(failed_unit_ids):
        raise EngineError('affected_failure_source_invalid', 'Exact original ordered failure units required', 422)
    ranges = []
    for value in selected:
        predicted = value.predicted_range
        if coordinate == 'work_timeline':
            ranges.append(predicted)
            continue
        if coordinate != 'audio_intrinsic' or mapping is None:
            raise EngineError('guidance_required', 'Original explicit coordinate and complete mapping required', 403)
        pieces = sorted((piece for piece in mapping.pieces
                         if piece.source_track.sha256 == audio_sha256
                         and piece.source_range.start_us < predicted.end_us
                         and predicted.start_us < piece.source_range.end_us),
                        key=lambda piece: (piece.source_range.start_us, piece.timeline_range.start_us))
        covered = predicted.start_us
        for piece in pieces:
            start = max(predicted.start_us, piece.source_range.start_us)
            end = min(predicted.end_us, piece.source_range.end_us)
            if start != covered or end <= start:
                raise EngineError('guidance_required', 'Ambiguous, gapped or duplicated source mapping cannot select shots', 403)
            mapped_start = piece.timeline_range.start_us + _half_up(
                (start - piece.source_range.start_us) * piece.playback_rate_den, piece.playback_rate_num)
            mapped_end = piece.timeline_range.start_us + _half_up(
                (end - piece.source_range.start_us) * piece.playback_rate_den, piece.playback_rate_num)
            if mapped_end <= mapped_start or mapped_end > piece.timeline_range.end_us:
                raise EngineError('affected_failure_source_invalid', 'Mapped half-open boundary is outside actual timeline piece', 422)
            ranges.append(c.MediaRange(start_us=mapped_start, end_us=mapped_end))
            covered = end
        if covered != predicted.end_us:
            raise EngineError('guidance_required', 'No complete original audio coordinate mapping', 403)
    return tuple(ranges)


def map_affected_recipe(projection, *, parent_preparation_id, affected_artifact_ids,
                        failed_unit_ids, failed_ranges, storyboard_shots, actual_failed_roles,
                        source_shot_ids, failure_component, regenerate_narration=False,
                        ambient_required=False):
    """Exact selection from authenticated failure facts and finite approved data.

    failure_component is the caller's already authenticated original diagnostic
    fact, not model inference, role output, or a replacement for approval.
    The service must independently re-read it at the command writer boundary.
    """
    if failure_component not in {'cover', 'narration', 'mix', 'visual', 'ambient'}:
        raise EngineError('guidance_required', 'Original failure component cannot be diagnosed from output roles', 403)
    shots = tuple(storyboard_shots)
    shot_ids = tuple(shot['shot_id'] for shot in shots)
    if len(set(shot_ids)) != len(shot_ids):
        raise EngineError('affected_failure_source_invalid', 'Distinct original ordered storyboard required', 422)
    impacted = tuple(shot['shot_id'] for shot in shots if any(
        shot['timeline_range']['start_us'] < value.end_us
        and value.start_us < shot['timeline_range']['end_us'] for value in failed_ranges))
    if not failed_ranges:
        if not source_shot_ids or not set(source_shot_ids) <= set(shot_ids):
            raise EngineError('guidance_required', 'Non-timed failure needs original artifact/shot source closure', 403)
        impacted = tuple(identifier for identifier in shot_ids if identifier in source_shot_ids)
    if failure_component == 'cover':
        recipe_id = 'cover-from-preserved-video-v1'
    elif failure_component in {'narration', 'mix'}:
        recipe_id = 'audio-remix-preserved-clips-v1'
    elif failure_component == 'visual':
        recipe_id = 'visual-preserve-mix-v1'
    else:
        if not ambient_required:
            raise EngineError('guidance_required', 'Ambient regeneration needs actual original ambient-input requirement', 403)
        recipe_id = 'ambient-remix-v1'
    recipes = {value.recipe_id: value for value in projection.recipes}
    recipe = recipes.get(recipe_id)
    if recipe is None:
        raise EngineError('affected_target_denied', 'This whole plan did not register the required recipe', 403)
    regenerated = ()
    if recipe_id in {'ambient-remix-v1', 'visual-preserve-mix-v1'}:
        if not source_shot_ids or not set(source_shot_ids) <= set(impacted):
            raise EngineError('guidance_required', 'Regeneration needs authenticated finite impacted source shots', 403)
        regenerated = tuple(identifier for identifier in impacted if identifier in source_shot_ids)
        if not regenerated:
            raise EngineError('guidance_required', 'Clip recipe requires an actual affected source shot', 403)
    if regenerate_narration and recipe.narration_mode != 'optional_registered_narration':
        raise EngineError('affected_target_denied', 'Selected profile preserves original narration', 403)
    if failure_component == 'narration' and not regenerate_narration:
        raise EngineError('guidance_required', 'Actual narration failure cannot be hidden by remixing original speech', 403)
    components = tuple(target.target_id for target in projection.component_targets
                       if target.target_id in recipe.component_target_ids
                       and (target.kind == 'edit' or target.kind == 'narration' and regenerate_narration
                            or target.kind == 'shot_clip' and target.shot_ids[0] in regenerated))
    expected_clips = {'production-' + identifier for identifier in regenerated}
    selected_clips = {target.target_id for target in projection.component_targets
                      if target.target_id in components and target.kind == 'shot_clip'}
    if selected_clips != expected_clips or (regenerate_narration and 'production-narration' not in components):
        raise EngineError('affected_target_denied', 'Whole recipe lacks exact required generation components', 403)
    roles = {'cover'} if recipe_id == 'cover-from-preserved-video-v1' else {'video'}
    if recipe.mixed_audio_mode == 'remix_actual_inputs':
        roles.add('mixed_audio')
    if regenerate_narration:
        roles.add('narration_audio')
    if regenerated and shot_ids[0] in regenerated:
        roles.add('cover')
    ordered = tuple(role for role in ROLE_ORDER if role in roles)
    if ordered not in recipe.allowed_output_variants or not roles <= set(actual_failed_roles):
        raise EngineError('affected_target_denied', 'Exact recipe outputs exceed actual failed artifact roles', 403)
    return AffectedRepairProposalV2(format='current-affected-repair-proposal-v2',
        parent_preparation_id=parent_preparation_id, affected_artifact_ids=tuple(affected_artifact_ids),
        failed_unit_ids=tuple(failed_unit_ids), requested_action='regenerate_affected_media',
        changed_media_roles=ordered, impacted_shot_ids=impacted, regenerated_shot_ids=regenerated,
        recipe_id=recipe_id, projection_sha256=plan_payload_sha256(projection),
        recipe_binding_sha256=plan_payload_sha256(recipe), component_target_ids=components)
