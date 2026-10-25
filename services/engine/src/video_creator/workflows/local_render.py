"""Gate0 free local template Flow: business facts precede Flow checkpoints.

This finite experiment is not autonomous model creation or a finished Bundle.
Only backend ports grant lease, operation, file-allocation and asset authority.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from crewai.flow import Flow, listen, start
from crewai.flow.persistence import SQLiteFlowPersistence
from pydantic import PrivateAttr

from video_creator.application.engine import canonical, digest
from video_creator.application.worker import WorkerRuntimeServices
from video_creator.domain.contracts import (
    CreativeRevision,
    Money,
    OperationIntent,
    OperationObservation,
)
from video_creator.domain.errors import EngineError
from video_creator.domain.worker import (
    GeneratedFileManifest,
    WorkerInvocation,
    WorkerOutcome,
)
from video_creator.media.ffmpeg import FFmpegRuntime
from video_creator.media.local_render import LocalTemplateRenderer
from video_creator.workflows.production_json import json_body

SOURCE = "gate0-local-render-v1: deterministic experiment template, not model creation"
RIGHTS = "Local experimental derivative of this production's authorized input; no distribution grant added"
INSTRUCTION = "表达更年轻，只修改第三镜头"


def _value_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _result(step):
    if not step or step["status"] != "succeeded":
        return None
    value = json.loads(step["result_json"])
    if not isinstance(value, dict) or not isinstance(value.get("result"), dict):
        raise EngineError(
            "local_step_invalid", "Persisted local step result is invalid.", 409
        )
    return value


class LocalRenderFlow(Flow[dict]):
    _invocation: WorkerInvocation = PrivateAttr()
    _services: WorkerRuntimeServices = PrivateAttr()
    _renderer: LocalTemplateRenderer = PrivateAttr()
    _request: object = PrivateAttr()
    _plan: dict = PrivateAttr(default_factory=dict)
    _audio_path: Path = PrivateAttr()
    _feedback: object = PrivateAttr(default=None)

    def __init__(self, invocation, services, renderer, persistence):
        super().__init__(persistence=persistence, tracing=False, max_method_calls=8)
        self._invocation, self._services, self._renderer = (
            invocation,
            services,
            renderer,
        )
        self._request = services.engine.get_request(invocation.lease)
        self._feedback = services.engine.feedback_for_run(invocation.lease)

    def _check(self):
        self._renderer.check()
        # Re-read ownership before any subsequent work. The backend checks the
        # current fence; Flow state itself never grants authority.
        if (
            self._services.worker.read_binding(self._invocation.lease)
            != self._invocation.binding
        ):
            raise EngineError(
                "execution_binding_conflict", "Fixed execution binding changed.", 409
            )

    def _checkpoint(self, name):
        self.persistence.save_state(self.state["id"], name, self.state)

    def _read(self, key):
        return self._services.engine.read_step(self._invocation.lease, key)

    def _finish_plain(self, key, input_hash, result):
        engine, lease = self._services.engine, self._invocation.lease
        step = engine.begin_step(lease, key, input_hash)
        if step["status"] != "succeeded":
            step = engine.complete_step(lease, key, result_json=result)
        return _result(step)

    @start()
    def prepare(self):
        self._check()
        binding_hash = digest(canonical(self._invocation.binding))
        if self.state.get("binding_sha256") not in (None, binding_hash):
            raise EngineError(
                "flow_binding_conflict",
                "Checkpoint belongs to different fixed inputs.",
                409,
            )
        self.state["binding_sha256"] = binding_hash
        self.state["run_id"] = self._invocation.lease.run_id
        if self._request.brief and self._request.brief.target_duration_us not in (
            None,
            10_000_000,
        ):
            raise EngineError(
                "local_template_denied", "Local experiment is exactly ten seconds.", 422
            )
        audio = None
        for bound in self._invocation.binding.input_assets:
            asset = self._services.worker.input_asset(
                self._invocation.lease, bound.asset_id
            )
            if (
                asset.media_type == "audio/wav"
                and asset.probe.decoded
                and (asset.probe.duration_us or 0) >= 10_000_000
            ):
                audio = asset
                break
        if audio is None:
            raise EngineError(
                "local_audio_required",
                "Provide an authorized decoded PCM WAV of at least ten seconds.",
                422,
            )
        self._audio_path = self._services.worker.input_content_path(
            self._invocation.lease, audio.asset_id
        )
        width, height = (
            (1280, 720)
            if self._request.brief and self._request.brief.aspect_ratio == "16:9"
            else (720, 1280)
        )
        plan = {
            "experiment": True,
            "template": "gate0-local-render-v1",
            "goal": self._request.goal,
            "confirmed_facts": [
                fact
                for source in self._request.source_bindings
                for fact in source.confirmed_facts
            ],
            "audio_asset_id": audio.asset_id,
            "audio_sha256": audio.sha256,
            "width": width,
            "height": height,
            "duration_us": 10_000_000,
            "shots": [
                {"shot_id": f"shot-{index}", "duration_us": duration, "revised": False}
                for index, duration in ((1, 4_000_000), (2, 3_000_000), (3, 3_000_000))
            ],
            "instruction_text": "",
            "preserved_constraints": [],
        }
        parent = None
        if self._feedback:
            if self._feedback.instruction_text != INSTRUCTION:
                raise EngineError(
                    "local_revision_unsupported",
                    "This finite template supports only its documented shot-three instruction.",
                    422,
                )
            previous = _result(
                self._services.worker.read_previous_step(
                    self._invocation.lease, "local-plan"
                )
            )
            if previous is None:
                raise EngineError(
                    "local_previous_plan_missing",
                    "Feedback requires its persisted prior template plan.",
                    409,
                )
            old = previous["result"]["plan"]
            if any(
                old[field] != plan[field]
                for field in (
                    "goal",
                    "confirmed_facts",
                    "audio_asset_id",
                    "audio_sha256",
                    "width",
                    "height",
                    "duration_us",
                )
            ):
                raise EngineError(
                    "local_constraint_failed",
                    "Feedback changed fixed facts or media inputs.",
                    409,
                )
            plan["shots"] = [dict(item) for item in old["shots"]]
            plan["shots"][2]["revised"] = True
            plan["instruction_text"] = self._feedback.instruction_text
            plan["preserved_constraints"] = list(self._feedback.preserved_constraints)
            parent = self._feedback.target_revision_id
        revision_id = "local-plan." + self._invocation.lease.run_id
        revision = CreativeRevision(
            revision_id=revision_id, kind="plan", parent_revision_id=parent,
            body=json_body(plan, path="revision.body"),
        )
        self._services.engine.commit_creative_revision(self._invocation.lease, revision)
        saved = self._finish_plain(
            "local-plan",
            digest(_value_json({"binding": binding_hash, "plan": plan})),
            {"revision_id": revision_id, "plan": plan},
        )
        self._plan = saved["result"]["plan"]
        self.state["plan_revision_id"] = revision_id
        self._checkpoint("prepare")
        return revision_id

    def _generated(self, key, input_hash, output_types, render):
        self._check()
        engine, worker, lease = (
            self._services.engine,
            self._services.worker,
            self._invocation.lease,
        )
        step = engine.begin_step(lease, key, input_hash)
        existing = _result(step)
        if existing is not None:
            for asset_id in existing["asset_ids"]:
                worker.production_result_content_path(lease, asset_id)
            return existing
        route_id = "gate0-local-render-v1"
        route = engine.configured_route(route_id)
        if (
            route.capability != "render"
            or route.source != "owned_local"
            or route.credential_ref
            or route.max_operation_cost.units()
            or route.destination != "local:gate0-local-render-v1"
        ):
            raise EngineError(
                "local_route_denied",
                "Only the fixed free local render route is allowed.",
                403,
            )
        intent = OperationIntent(
            step_key=key,
            dedupe_key="local." + lease.run_id + "." + key,
            input_sha256=input_hash,
            route_id=route_id,
            reserved_cost=Money(amount="0"),
        )
        operation = engine.prepare_operation(lease, intent)
        reservations = tuple(
            worker.allocate_output(
                lease, key, input_hash, output_key, media_type, SOURCE, RIGHTS
            )
            for output_key, media_type in output_types
        )
        files = ()
        if operation["status"] == "succeeded" and operation["settled"]:
            observation = OperationObservation.model_validate_json(
                operation["observation_json"]
            )
            if not isinstance(observation.result_json, dict):
                raise EngineError(
                    "generated_manifest_missing",
                    "Successful local operation lacks its file evidence.",
                    409,
                )
            files = tuple(
                GeneratedFileManifest.model_validate(item)
                for item in observation.result_json.get("generated_files", [])
            )
            actual = tuple(
                worker.finish_output(lease, reservation) for reservation in reservations
            )
            if files != actual:
                raise EngineError(
                    "generated_manifest_conflict",
                    "Completed files differ from the settled operation.",
                    409,
                )
        else:
            complete = all(
                reservation.completed_path.is_file() for reservation in reservations
            )
            if operation["status"] == "prepared":
                engine.claim_operation(lease, operation["id"])
                if not complete:
                    # Never overwrite a complete sibling after a partial crash.
                    if any(
                        reservation.completed_path.exists()
                        or reservation.partial_path.exists()
                        for reservation in reservations
                    ):
                        engine.observe_operation(
                            lease,
                            operation["id"],
                            OperationObservation(status="unknown"),
                        )
                        return None
                    render(tuple(item.partial_path for item in reservations))
                    self._check()
                    for reservation in reservations:
                        with reservation.partial_path.open("r+b") as output:
                            os.fsync(output.fileno())
                        os.replace(reservation.partial_path, reservation.completed_path)
            elif not complete:
                if operation["status"] != "unknown":
                    engine.observe_operation(
                        lease, operation["id"], OperationObservation(status="unknown")
                    )
                return None
            self._check()
            files = tuple(
                worker.finish_output(lease, reservation) for reservation in reservations
            )
            for reservation, item in zip(reservations, files, strict=True):
                probe = self._services.media_validator(
                    reservation.completed_path, item.candidate.media_type
                )
                if not probe.decoded or probe.media_type != item.candidate.media_type:
                    raise EngineError(
                        "local_decode_failed",
                        "Completed local output failed real decoding.",
                        422,
                    )
            engine.observe_operation(
                lease,
                operation["id"],
                OperationObservation(
                    status="succeeded",
                    external_id=reservations[0].attempt_id,
                    actual_cost=Money(amount="0"),
                    cost_evidence="confirmed_no_charge",
                    result_json={
                        "generated_files": [
                            item.model_dump(mode="json") for item in files
                        ]
                    },
                ),
                reconciliation=operation["status"] == "unknown",
            )
        self._check()
        step = worker.commit_generated_step(
            lease,
            key,
            input_hash,
            files,
            {
                "generated_files": [item.model_dump(mode="json") for item in files],
                "experiment": True,
            },
            self._services.media_validator,
        )
        return _result(step)

    @listen(prepare)
    def render_shots(self, _):
        shots = []
        for index, shot in enumerate(self._plan["shots"], 1):
            self._check()
            key = "local-shot-" + str(index)
            input_hash = digest(
                _value_json(
                    {
                        "shot": shot,
                        "audio": self._plan["audio_sha256"],
                        "width": self._plan["width"],
                        "height": self._plan["height"],
                        "resources": self._invocation.binding.resource_manifest_sha256,
                    }
                )
            )
            current = self._read(key)
            previous = (
                self._services.worker.read_previous_step(self._invocation.lease, key)
                if self._feedback and index < 3
                else None
            )
            if (
                (current is None or current["status"] != "succeeded")
                and previous
                and previous["status"] == "succeeded"
                and previous["input_sha256"] == input_hash
            ):
                old = _result(previous)
                for asset_id in old["asset_ids"]:
                    self._services.worker.production_result_content_path(
                        self._invocation.lease, asset_id
                    )
                self._services.engine.begin_step(
                    self._invocation.lease, key, input_hash
                )
                current = self._services.engine.complete_step(
                    self._invocation.lease, key, tuple(old["asset_ids"]), old["result"]
                )
            if current and current["status"] == "succeeded":
                result = _result(current)
            else:
                result = self._generated(
                    key,
                    input_hash,
                    (("video", "video/mp4"),),
                    lambda paths, index=index, shot=shot: self._renderer.render_shot(
                        self._audio_path,
                        paths[0],
                        index=index,
                        revised=shot["revised"],
                        width=self._plan["width"],
                        height=self._plan["height"],
                    ),
                )
            if result is None:
                self.state["outcome"] = "needs_reconciliation"
                self._checkpoint("render_shots_uncertain")
                return False
            shots.append(result["asset_ids"][0])
            self.state["shot_asset_ids"] = list(shots)
            self._checkpoint(key)
        return True

    @listen(render_shots)
    def compose(self, ready):
        if not ready:
            return False
        self._check()
        assets = tuple(
            self._services.worker.production_result_asset(
                self._invocation.lease, asset_id
            )
            for asset_id in self.state["shot_asset_ids"]
        )
        paths = tuple(
            self._services.worker.production_result_content_path(
                self._invocation.lease, asset.asset_id
            )
            for asset in assets
        )
        input_hash = digest(
            _value_json(
                {
                    "shots": [asset.sha256 for asset in assets],
                    "resources": self._invocation.binding.resource_manifest_sha256,
                }
            )
        )
        result = self._generated(
            "local-compose",
            input_hash,
            (("video", "video/mp4"), ("mixed", "audio/wav")),
            lambda outputs: self._renderer.compose(paths, outputs[0], outputs[1]),
        )
        if result is None:
            self.state["outcome"] = "needs_reconciliation"
            self._checkpoint("compose_uncertain")
            return False
        self.state["output_asset_ids"] = list(result["asset_ids"])
        self._checkpoint("compose")
        return True

    @listen(compose)
    def review(self, ready):
        if not ready:
            return WorkerOutcome(state="needs_reconciliation")
        self._check()
        engine, lease = self._services.engine, self._invocation.lease
        revision_id = "local-quality." + lease.run_id
        body = {
            "experiment": True,
            "asset_ids": self.state["shot_asset_ids"] + self.state["output_asset_ids"],
            "passed": False,
            "method": "actual_ffmpeg_decode; human audiovisual review pending",
            "plan_revision_id": self.state["plan_revision_id"],
            "instruction_text": self._plan["instruction_text"],
            "preserved_constraints": self._plan["preserved_constraints"],
        }
        engine.commit_creative_revision(
            lease,
            CreativeRevision(
                revision_id=revision_id,
                kind="quality",
                input_revision_refs=(self.state["plan_revision_id"],),
                body=json_body(body, path="revision.body"),
            ),
        )
        decision = engine.read_review_decision(lease, revision_id)
        self.state["quality_revision_id"] = revision_id
        if self._request.automation.mode == "interactive" and decision is None:
            # Persist only IDs before releasing ownership; no console/thread wait.
            self.state["outcome"] = "waiting_user"
            self._checkpoint("review_pending")
            engine.wait_for_review(lease, revision_id)
            return WorkerOutcome(state="waiting_user")
        if decision is not None and decision.action != "approve":
            raise EngineError(
                "local_review_conflict", "This run lacks its fixed approval.", 409
            )
        result = {
            "quality_revision_id": revision_id,
            "approval": decision.model_dump(mode="json") if decision else None,
            "unattended_policy_only": decision is None,
            "bundle_pending": True,
        }
        self._finish_plain("local-review-approved", digest(_value_json(result)), result)
        self.state["outcome"] = "released"
        self._checkpoint("review_accepted_bundle_pending")
        return WorkerOutcome(state="released")


def run_invocation(
    invocation: WorkerInvocation, services: WorkerRuntimeServices
) -> WorkerOutcome:
    resources = services.load_resources(invocation)
    staging = services.assets.root / "Staging"
    staging.mkdir(exist_ok=True)
    if staging.is_symlink() or not staging.resolve().is_relative_to(
        services.assets.root.resolve()
    ):
        raise EngineError(
            "media_path_denied", "Controlled staging escaped the instance.", 403
        )
    state_root = services.assets.root / "WorkflowState"
    state_root.mkdir(exist_ok=True)
    if state_root.is_symlink() or not state_root.resolve().is_relative_to(
        services.assets.root.resolve()
    ):
        raise EngineError(
            "flow_path_denied", "Flow checkpoint escaped the instance.", 403
        )
    state_path = state_root / "LocalRender.sqlite"
    if state_path.is_symlink():
        raise EngineError(
            "flow_path_denied", "Flow checkpoint path is not controlled.", 403
        )
    runtime = FFmpegRuntime(
        Path(resources["ffmpeg_path"]), Path(resources["ffprobe_path"]), staging
    )
    renderer = LocalTemplateRenderer(
        runtime,
        Path(resources["font"]["path"]),
        services.cancel,
        min(
            services.deadline_monotonic,
            time.monotonic() + invocation.max_attempt_seconds,
        ),
    )
    persistence = SQLiteFlowPersistence(str(state_path))
    flow = LocalRenderFlow(invocation, services, renderer, persistence)
    flow_id = str(
        uuid5(NAMESPACE_URL, "video-creator:" + canonical(invocation.binding))
    )
    outcome = flow.kickoff(inputs={"id": flow_id})
    if not isinstance(outcome, WorkerOutcome):
        raise EngineError(
            "worker_outcome_invalid",
            "Local Flow did not return its controlled outcome.",
            503,
        )
    return outcome
