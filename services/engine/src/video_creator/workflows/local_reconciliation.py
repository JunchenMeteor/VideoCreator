"""Read and decode original local outputs; never execute the normal Flow."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import TYPE_CHECKING

from video_creator.domain.contracts import AssetCandidate
from video_creator.domain.errors import EngineError
from video_creator.domain.worker import (
    GeneratedFileManifest,
    ReconciliationEvidence,
    ReconciliationInvocation,
    ReconciliationOutcome,
)
from video_creator.media.ffmpeg import FFmpegRuntime

if TYPE_CHECKING:
    from video_creator.application.worker import WorkerRuntimeServices

SOURCE = "gate0-local-render-v1: deterministic experiment template, not model creation"
RIGHTS = "Local experimental derivative of this production's authorized input; no distribution grant added"


def _input_digest(value):
    body = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _step_result(step):
    if not step or step["status"] != "succeeded":
        raise EngineError(
            "reconciliation_evidence_incomplete",
            "Original successful step evidence is missing.",
            409,
            "reconcile",
        )
    result = json.loads(step["result_json"])
    if not isinstance(result, dict) or not isinstance(result.get("result"), dict):
        raise EngineError(
            "reconciliation_evidence_incomplete",
            "Original step evidence is invalid.",
            409,
            "reconcile",
        )
    return result


def _target_identity(target):
    return (
        target.operation_id,
        target.step_key,
        target.input_sha256,
        target.step_input_sha256,
        target.dedupe_key,
        target.route,
        target.external_id,
        tuple(
            (
                item.attempt_id,
                item.staging_id,
                item.allocation_fence,
                item.output_key,
                item.media_type,
                item.source,
                item.rights,
            )
            for item in target.allocations
        ),
    )


def _original_plan(invocation, services):
    step = services.worker.read_reconciliation_step(invocation, "local-plan")
    result = _step_result(step)
    plan = result["result"].get("plan")
    if not isinstance(plan, dict):
        raise EngineError(
            "reconciliation_evidence_incomplete",
            "Original template plan is unavailable.",
            409,
            "reconcile",
        )
    request = invocation.request
    dimensions = (
        (1280, 720)
        if request.brief and request.brief.aspect_ratio == "16:9"
        else (720, 1280)
    )
    facts = [
        fact for source in request.source_bindings for fact in source.confirmed_facts
    ]
    shots = plan.get("shots")
    if (
        plan.get("experiment") is not True
        or plan.get("template") != "gate0-local-render-v1"
        or plan.get("goal") != request.goal
        or plan.get("confirmed_facts") != facts
        or (plan.get("width"), plan.get("height")) != dimensions
        or plan.get("duration_us") != 10_000_000
        or not isinstance(shots, list)
        or len(shots) != 3
        or any(
            not isinstance(shot, dict)
            or shot.get("shot_id") != f"shot-{index}"
            or type(shot.get("duration_us")) is not int
            or shot["duration_us"] != duration
            or type(shot.get("revised")) is not bool
            or (index < 3 and shot["revised"])
            for index, (shot, duration) in enumerate(
                zip(shots or (), (4_000_000, 3_000_000, 3_000_000), strict=False), 1
            )
        )
    ):
        raise EngineError(
            "reconciliation_evidence_incomplete",
            "Original plan differs from the fixed local profile.",
            409,
            "reconcile",
        )
    audio = services.worker.reconciliation_input_asset(
        invocation, plan["audio_asset_id"]
    )
    services.worker.reconciliation_input_content_path(invocation, audio.asset_id)
    if (
        audio.sha256 != plan.get("audio_sha256")
        or audio.media_type != "audio/wav"
        or not audio.probe.decoded
        or (audio.probe.duration_us or 0) < 10_000_000
    ):
        raise EngineError(
            "reconciliation_evidence_incomplete",
            "Original input audio evidence does not match.",
            409,
            "reconcile",
        )
    binding_hash = _input_digest(invocation.binding.model_dump(mode="json"))
    if step["input_sha256"] != _input_digest({"binding": binding_hash, "plan": plan}):
        raise EngineError(
            "reconciliation_evidence_incomplete",
            "Original plan input hash does not match.",
            409,
            "reconcile",
        )
    return plan


def _expected(invocation, services, plan, target):
    resources = invocation.binding.resource_manifest_sha256
    if target.step_key in {"local-shot-1", "local-shot-2", "local-shot-3"}:
        index = int(target.step_key[-1])
        shot = plan["shots"][index - 1]
        input_hash = _input_digest(
            {
                "shot": shot,
                "audio": plan["audio_sha256"],
                "width": plan["width"],
                "height": plan["height"],
                "resources": resources,
            }
        )
        outputs, duration = (("video", "video/mp4"),), shot["duration_us"]
    elif target.step_key == "local-compose":
        hashes = []
        for index in (1, 2, 3):
            step = services.worker.read_reconciliation_step(
                invocation, "local-shot-" + str(index)
            )
            result = _step_result(step)
            if len(result.get("asset_ids", [])) != 1:
                raise EngineError(
                    "reconciliation_evidence_incomplete",
                    "Original shot asset collection is invalid.",
                    409,
                    "reconcile",
                )
            asset = services.worker.reconciliation_result_asset(
                invocation, result["asset_ids"][0]
            )
            services.worker.reconciliation_result_content_path(
                invocation, asset.asset_id
            )
            hashes.append(asset.sha256)
        input_hash = _input_digest({"shots": hashes, "resources": resources})
        outputs, duration = (("video", "video/mp4"), ("mixed", "audio/wav")), 10_000_000
    else:
        raise EngineError(
            "reconciliation_profile_denied",
            "Operation is outside the fixed local profile.",
            403,
        )
    if target.input_sha256 != input_hash or target.step_input_sha256 != input_hash:
        raise EngineError(
            "reconciliation_evidence_incomplete",
            "Original operation input hash does not match.",
            409,
            "reconcile",
        )
    if (
        tuple((item.output_key, item.media_type) for item in target.allocations)
        != outputs
    ):
        raise EngineError(
            "reconciliation_evidence_incomplete",
            "Original complete output collection does not match.",
            409,
            "reconcile",
        )
    if target.dedupe_key != "local." + invocation.lease.run_id + "." + target.step_key:
        raise EngineError(
            "reconciliation_profile_denied",
            "Original operation identity does not match.",
            403,
        )
    route = target.route
    if (
        route.route_id != "gate0-local-render-v1"
        or route.capability != "render"
        or route.source != "owned_local"
        or route.destination != "local:gate0-local-render-v1"
        or route.credential_ref
        or route.max_operation_cost.units()
        or not route.verified
    ):
        raise EngineError(
            "reconciliation_profile_denied",
            "Only the original verified free local route may be reconciled.",
            403,
        )
    return duration


def run_reconciliation(
    invocation: ReconciliationInvocation, services: WorkerRuntimeServices
) -> ReconciliationOutcome:
    deadline = min(
        services.deadline_monotonic, time.monotonic() + invocation.max_attempt_seconds
    )

    def check():
        if services.cancel.is_set() or time.monotonic() >= deadline:
            raise EngineError(
                "worker_attempt_interrupted",
                "Local reconciliation attempt must stop.",
                409,
                "reconcile",
            )

    def file_hash(path):
        checksum = hashlib.sha256()
        with path.open("rb") as source:
            while chunk := source.read(1024 * 1024):
                check()
                checksum.update(chunk)
        return checksum.hexdigest()

    try:
        check()
        resources = services.load_resources(invocation)
        # No mkdir, temp file, normal Flow, allocation or render occurs here.
        staging = services.assets.root / "Staging"
        if staging.is_symlink() or not staging.resolve(strict=True).is_relative_to(
            services.assets.root.resolve()
        ):
            raise EngineError(
                "media_path_denied", "Original staging escaped the installation.", 403
            )
        runtime = FFmpegRuntime(
            Path(resources["ffmpeg_path"]), Path(resources["ffprobe_path"]), staging
        )

        def validator(path, _media_type):
            check()
            probe = runtime.probe(
                path,
                decode=True,
                cancel=services.cancel,
                timeout=min(90, max(0.01, deadline - time.monotonic())),
            )
            check()
            return probe

        plan = _original_plan(invocation, services)
        for original in invocation.targets:
            check()
            target = services.worker.read_reconciliation_target(
                invocation, original.operation_id
            )
            if _target_identity(target) != _target_identity(original):
                raise EngineError(
                    "reconciliation_target_conflict",
                    "Original reconciliation target changed.",
                    409,
                )
            if target.status == "failed":
                return ReconciliationOutcome(state="failed")
            if target.status == "prepared":
                return ReconciliationOutcome(state="needs_reconciliation")
            duration = _expected(invocation, services, plan, target)
            handles = services.worker.reconciliation_files(
                invocation, target.operation_id
            )
            if tuple(handle.allocation for handle in handles) != target.allocations:
                raise EngineError(
                    "reconciliation_target_conflict",
                    "Original file collection changed.",
                    409,
                )
            manifests = []
            for handle in handles:
                check()
                allocation, path = handle.allocation, handle.completed_path
                if (
                    allocation.source != SOURCE
                    or allocation.rights != RIGHTS
                    or path.name != allocation.staging_id
                    or path.is_symlink()
                    or not path.resolve(strict=True).is_relative_to(staging.resolve())
                ):
                    raise EngineError(
                        "media_path_denied",
                        "File is outside its original local allocation.",
                        403,
                    )
                if (
                    not path.is_file()
                    or not 0 < path.stat().st_size <= runtime.MAX_INPUT_BYTES
                ):
                    return ReconciliationOutcome(state="needs_reconciliation")
                size, before_hash = path.stat().st_size, file_hash(path)
                if allocation.staging_status in {"ready", "imported"} and (
                    size != allocation.size or before_hash != allocation.sha256
                ):
                    return ReconciliationOutcome(state="needs_reconciliation")
                if allocation.staging_status == "allocated" and (
                    allocation.size != 0 or allocation.sha256 is not None
                ):
                    return ReconciliationOutcome(state="needs_reconciliation")
                probe = validator(path, allocation.media_type)
                video = allocation.output_key == "video"
                if (
                    not probe.decoded
                    or probe.media_type != allocation.media_type
                    or probe.duration_us != duration
                    or probe.has_video != video
                    or not probe.has_audio
                    or (
                        video
                        and (probe.width, probe.height)
                        != (plan["width"], plan["height"])
                    )
                    or (
                        not video
                        and (probe.width is not None or probe.height is not None)
                    )
                ):
                    return ReconciliationOutcome(state="needs_reconciliation")
                if path.stat().st_size != size or file_hash(path) != before_hash:
                    return ReconciliationOutcome(state="needs_reconciliation")
                manifests.append(
                    GeneratedFileManifest(
                        attempt_id=allocation.attempt_id,
                        candidate=AssetCandidate(
                            staging_id=allocation.staging_id,
                            sha256=before_hash,
                            size=size,
                            media_type=allocation.media_type,
                            source=allocation.source,
                            rights=allocation.rights,
                        ),
                    )
                )
            check()
            services.worker.observe_reconciled_operation(
                invocation,
                ReconciliationEvidence(
                    operation_id=target.operation_id, files=tuple(manifests)
                ),
                validator,
            )
        # Only a suggestion. The runner rechecks all original operations and
        # cancellation, revokes this lease, then may queue a NEW normal attempt.
        return ReconciliationOutcome(state="queued")
    except EngineError as error:
        if error.code in {
            "reconciliation_evidence_incomplete",
            "invalid_media",
            "media_process_failed",
            "media_format_denied",
            "media_reference_denied",
            "media_resource_limit",
            "media_timeout",
            "media_cancelled",
            "worker_attempt_interrupted",
        }:
            return ReconciliationOutcome(state="needs_reconciliation")
        raise
    except (OSError, KeyError, ValueError, TypeError):
        # Missing/bad evidence is not evidence of failed generation. Ownership
        # EngineErrors above remain distinct and are cleaned up by the runner.
        return ReconciliationOutcome(state="needs_reconciliation")
