"""Consume the original nine held alignment ports and one original JSON Step."""
from __future__ import annotations

import hashlib

from video_creator.domain import contracts as c
from video_creator.domain.errors import EngineError
from video_creator.domain.worker import GeneratedFileManifest
from video_creator.workflows.attempt_control import current_attempt
from video_creator.workflows.autonomous_production import BoundProductionDriver
from video_creator.workflows.current_final_evidence import require_final_port


def run_alignment(port, services, lease, *, preparation_id=None, execution=None, transcript=None,
                  prediction=None, mapping=None):
    """Read settled/committed first. Unknown never receives another inference."""
    held = require_final_port(port)
    initial = execution is None
    if initial:
        if preparation_id is None:
            raise EngineError("alignment_preparation_missing", "Original initial preparation identity is required.", 409)
        intent = held.register_initial_alignment(lease, preparation_id, transcript=transcript,
                                                 prediction=prediction, mapping=mapping)
        raw = held.registered_initial_alignment_request(lease, preparation_id)
        read = lambda: held.read_registered_initial_alignment_result(lease, preparation_id)
        commit = lambda files: held.commit_registered_initial_alignment_result(lease, preparation_id, files=files)
    else:
        intent = held.registered_alignment_intent(lease, execution)
        raw = held.registered_alignment_request(lease, execution)
        read = lambda: held.read_registered_alignment_result(lease, execution)
        commit = lambda files: held.commit_registered_alignment_result(lease, execution, files=files)
    if (type(intent) is not c.OperationIntent or type(raw) is not bytes or intent.reserved_cost.units()
            or intent.input_sha256 != hashlib.sha256(raw).hexdigest()):
        raise EngineError("alignment_original_input_invalid", "Use the sole original zero-cost intent and complete canonical request bytes.", 403)
    from video_creator.application.bundles import strict_json
    from video_creator.domain.registered_alignment import alignment_request_bytes
    from video_creator.providers.local_alignment import parse_request

    payload = strict_json(raw)
    request = parse_request(payload)
    if alignment_request_bytes(request) != raw or request.binding.run_id != lease.run_id:
        raise EngineError("alignment_original_input_invalid", "Original binding and canonical input cannot be reconstructed or changed.", 422)
    services.engine.begin_step(lease, intent.step_key, intent.input_sha256)
    original = services.engine.prepare_operation(lease, intent)
    if original["status"] == "succeeded" and original["settled"]:
        try:
            return (*read(), original["id"])
        except EngineError as error:
            if error.code != "alignment_step_commit_required":
                raise
            # This exact held error denotes observation-before-Step-commit.
            # The original persisted observation supplies its original file.
            observation = original.get("observation_json")
            if type(observation) is str:
                observation = strict_json(observation.encode())
            if type(observation) is c.OperationObservation:
                observation = observation.model_dump(mode="json")
            if type(observation) is not dict:
                raise EngineError("alignment_original_observation_missing", "Original settled evidence is unavailable; no new model call is permitted.", 409, "reconcile")
            files = tuple(GeneratedFileManifest.model_validate(value) for value in observation.get("result_json", {}).get("generated_files", ()))
            if len(files) != 1:
                raise EngineError("alignment_original_observation_missing", "Exactly one original complete JSON manifest is required.", 409, "reconcile")
            commit(files)
            return (*read(), original["id"])
    if original["status"] != "prepared":
        raise EngineError("alignment_original_unresolved", "Original pending/unknown/terminal result retains its own reconciliation boundary.", 409,
                          "reconcile" if original["status"] in {"pending", "submitting", "unknown"} else "never")
    if services.alignment_driver is None or services.alignment_registration != request.alignment_registration.registration:
        raise EngineError("alignment_resource_not_ready", "The original installed hardcoded CTC builder and exact registration are required.", 503)
    control = current_attempt()
    control.check()
    output = services.worker.allocate_output(lease, intent.step_key, intent.input_sha256,
                "alignment-result", "application/json", "registered offline CTC alignment", "Original admitted audio and registered method rights; no new grant.")
    bound = services.alignment_driver(payload, (output,), ordinary_lease=lease,
                cancel=control.cancel_requested, deadline_monotonic=control.deadline_monotonic)
    if type(bound) is not BoundProductionDriver or bound.request_payload != payload:
        raise EngineError("alignment_driver_binding_invalid", "Actual builder must retain the full exact original request payload.", 403)
    observation = services.executor.execute(lease, intent, bound.invoke, request_payload=bound.request_payload)
    if observation.status != "succeeded":
        raise EngineError("alignment_original_unresolved", "An uncertain original CTC operation is never resubmitted.", 409,
                          "reconcile" if observation.status in {"pending", "unknown"} else "never")
    files = tuple(GeneratedFileManifest.model_validate(value) for value in observation.result_json.get("generated_files", ()))
    if len(files) != 1:
        raise EngineError("alignment_original_output_invalid", "A successful Step requires one actual JSON output manifest.", 422)
    commit(files)  # Backend verifies actual bytes, original context and settled Operation before completing Step.
    return (*read(), original["id"])


def aligned_document(document, alignment, mapping):
    """Keep actual ASR text/ranges intact; regenerate cues from acoustic units."""
    from video_creator.application.bundles import serialize_subtitles
    from video_creator.workflows.bundle_producer import _record

    transcript = document.transcript
    boundaries = {value.transcript_unit_id: value.intrinsic_range for value in alignment.boundaries}
    ranges = {}
    for utterance in transcript.utterances:
        if alignment.units == "utterance":
            span = boundaries.get(utterance.utterance_id)
        else:
            words = [boundaries[value.word_id] for value in utterance.words if value.word_id in boundaries]
            if len(words) != len(utterance.words) or not words:
                raise EngineError("alignment_unit_coverage_missing", "Every original spoken word requires its actual acoustic boundary.", 422)
            span = c.MediaRange(start_us=words[0].start_us, end_us=words[-1].end_us)
        if span is None or span.end_us > transcript.duration_us:
            raise EngineError("alignment_unit_coverage_missing", "Every original utterance requires complete actual alignment.", 422)
        ranges[utterance.utterance_id] = span
    # The installed initial recipe has one actual full mixed-audio placement.
    if (len(mapping.pieces) != 1 or mapping.pieces[0].source_range != mapping.pieces[0].timeline_range
            or mapping.pieces[0].source_range.start_us != 0):
        raise EngineError("alignment_mapping_recipe_unsupported", "This recipe requires the original independently verified full placement.", 409)
    cues = tuple(value.model_copy(update={"timeline_range": ranges[value.transcript_unit_refs[0]]})
                 for value in document.subtitles.cues)
    subtitles = document.subtitles.model_copy(update={"alignment_revision_id": alignment.alignment_revision_id,
                                                     "cues": cues, "content_sha256": "0" * 64})
    srt, vtt, quantization = serialize_subtitles(subtitles)
    subtitles = _record(subtitles.model_copy(update={"quantization_errors": tuple(quantization)}))
    value = type(document)(**document.model_dump(exclude={"alignment", "subtitles"}), alignment=alignment, subtitles=subtitles)
    return value, srt, vtt, ranges


def runtime_actual(actual, observation):
    """Separate the CTC execution identity from unchanged original ASR output."""
    if (type(observation) is not c.OperationObservation or observation.status != "succeeded"
            or not isinstance(observation.result_json, dict)):
        raise EngineError("alignment_actual_evidence_missing", "Only the actual held committed CTC observation supplies its runtime identity.", 422)
    execution = c.AlignmentExecutionIdentity.model_validate(observation.result_json["execution_identity"])
    return {**actual, "runtime": {**actual["runtime"], "execution_identity": execution.model_dump(mode="json")}}
