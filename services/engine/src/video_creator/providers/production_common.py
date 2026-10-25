"""Ordinary lease/permit and existing output-handle boundary for real drivers."""
from __future__ import annotations

import os
from pathlib import Path

from video_creator.domain import contracts as c
from video_creator.domain.errors import EngineError
from video_creator.domain.worker import OutputReservation
from video_creator.workflows.attempt_control import current_attempt


def output_scope(outputs, lease, storage_root):
    if (not isinstance(outputs, tuple) or not outputs or len(outputs) > 3
            or any(not isinstance(value, OutputReservation) for value in outputs)
            or len({value.attempt_id for value in outputs}) != len(outputs)):
        raise EngineError("production_output_denied", "Actual distinct ordered reservations are required.", 403)
    root = Path(storage_root).resolve(strict=True)
    if len({(value.step_key, value.input_sha256) for value in outputs}) != 1:
        raise EngineError("production_output_denied", "Outputs must bind one original step and input.", 403)
    for value in outputs:
        if value.run_id != lease.run_id:
            raise EngineError("production_output_denied", "Output is outside this ordinary Run.", 403)
        for path in (value.partial_path, value.completed_path):
            if not path.resolve().is_relative_to(root):
                raise EngineError("production_output_denied", "Output is outside controlled storage.", 403)
            if any(candidate.is_symlink() or candidate.is_junction()
                   for candidate in (path, *path.parents) if candidate.is_relative_to(root)):
                raise EngineError("production_output_denied", "Output links are not admitted.", 403)
            if path.exists():
                raise EngineError("production_original_output_unresolved", "An original output exists; reconcile it instead of overwriting or regenerating.", 409, "reconcile")
        if value.partial_path.parent != value.completed_path.parent:
            raise EngineError("production_output_denied", "Atomic completion requires the original staging directory.", 403)
    return outputs


def permit_scope(engine, permit, lease, route_id, capability, destination, *, local, secret):
    current_attempt().check()
    if ((permit.run_id, permit.fencing_token) != (lease.run_id, lease.fencing_token)
            or permit.route.route_id != route_id or permit.route.capability != capability
            or permit.route.destination != destination or not permit.route.verified):
        raise EngineError("production_permit_denied", "Original permit, route and ordinary fence must agree.", 403)
    if local and (permit.route.source != "owned_local" or permit.route.credential_ref is not None
                  or secret is not None or permit.route.max_operation_cost.units()):
        raise EngineError("production_permit_denied", "This local driver has no credential or charge authority.", 403)
    if not local and (permit.route.source != "owned_remote" or secret is None):
        raise EngineError("production_permit_denied", "Remote BYOK requires its actual admitted credential; official entitlement is separate.", 403)
    engine.get_request(lease)  # Existing backend validates expiry/current ordinary fence.


def install_output(engine, worker, lease, output, decoder, media_type):
    current_attempt().check()
    engine.get_request(lease)
    probe = decoder(output.partial_path, media_type)
    if not isinstance(probe, c.MediaProbe) or not probe.decoded or probe.media_type != media_type:
        raise EngineError("production_decode_invalid", "Actual complete output has no matching decoded media evidence.", 422)
    # Same-directory hard-link creation does not replace an existing completed
    # handle. The old partial is then unlinked. No bytes become a registered Asset
    # until the original backend finish/settled/fenced commit succeeds.
    try:
        os.link(output.partial_path, output.completed_path, follow_symlinks=False)
        output.partial_path.unlink()
    except OSError:
        raise EngineError("production_output_completion_uncertain", "Original completion must be reconciled from its handles.", 409, "reconcile") from None
    return worker.finish_output(lease, output), probe


def local_observation(files, result):
    return c.OperationObservation(status="succeeded", actual_cost=c.Money(amount="0"),
                cost_evidence="confirmed_no_charge",
                result_json={**result, "generated_files": [value.model_dump(mode="json") for value in files]})
