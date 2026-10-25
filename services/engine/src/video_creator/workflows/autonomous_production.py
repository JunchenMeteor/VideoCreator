"""One Crew Flow candidate upstream on the existing Run/Step/Operation ledger.

Installed services are trusted constructors, not public/model configuration.
No fallback makes a colour template, approval, four Asset IDs or authority.
"""
from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from crewai.flow import Flow, listen, start
from crewai.flow.persistence import SQLiteFlowPersistence
from pydantic import PrivateAttr

from video_creator.application.engine import canonical, digest
from video_creator.domain import contracts as c
from video_creator.domain.errors import EngineError
from video_creator.domain.plan_repair_targets import (
    PlanRepairTargetsV1,
    RegisteredProductionPlanV2,
    plan_payload_bytes,
)
from video_creator.domain.registered_production import CurrentProductionUpstreamResult
from video_creator.domain.worker import GeneratedFileManifest
from video_creator.workflows.attempt_control import attempt_control, current_attempt
from video_creator.workflows.creative import CreativeCrew
from video_creator.workflows.current_policy_evidence import (
    require_admission,
    require_plan_rights,
    require_proposal,
    stored_proposal,
)
from video_creator.workflows.production_json import canonical_object, json_body

MASTER_INDEX_DESTINATION = "local:registered-master-index-v1"


@dataclass(frozen=True)
class BoundProductionDriver:
    """Private in-process adapter result; not a second public/role schema."""
    invoke: Callable
    request_payload: Mapping[str, object] | None = None


@dataclass(frozen=True)
class AutonomousServices:
    engine: object
    bundle: object
    worker: object
    executor: object
    media_validator: Callable
    subject: str
    text_route_id: str
    narration_route_id: str
    picture_route_id: str
    edit_route_id: str
    master_index_route_id: str
    # These must be installed fixed code: no module/URL/path from a model.
    narration_driver: Callable
    picture_driver: Callable
    edit_driver: Callable
    declare_rights: Callable  # Backend-owned current declaration, never model rights.
    admit_revision: Callable  # Backend-owned actual decision/preauthorized policy.
    max_duration_us: int = 60_000_000
    rights_proposal: Callable | None = None
    current_admission: Callable | None = None
    current_rights: Callable | None = None
    registration_sha256: str | None = None
    execution_ports: object | None = None
    alignment_registration: object | None = None
    alignment_driver: Callable | None = None
    prepare_plan_repair_targets: Callable | None = None
    component_diagnostic_ports: object | None = None


@dataclass(frozen=True)
class CurrentPolicyServices:
    """Separate installed policy consumer; no legacy human-decision callbacks."""
    engine: object
    bundle: object
    worker: object
    executor: object
    media_validator: Callable
    subject: str
    text_route_id: str
    narration_route_id: str
    picture_route_id: str
    edit_route_id: str
    master_index_route_id: str
    narration_driver: Callable
    picture_driver: Callable
    edit_driver: Callable
    policy_execution_ports: object
    registration_sha256: str
    max_duration_us: int = 60_000_000
    alignment_registration: object | None = None
    alignment_driver: Callable | None = None
    prepare_plan_repair_targets: Callable | None = None
    component_diagnostic_ports: object | None = None


@dataclass(frozen=True)
class AutonomousUpstreamResult:
    state: str  # masters_ready / waiting_user / needs_reconciliation only.
    media_roles: dict | None = None
    blocker_code: str | None = None


def _step_result(step):
    if step is None or step["status"] != "succeeded":
        return None
    envelope = json.loads(step["result_json"])
    if not isinstance(envelope, dict) or not isinstance(envelope.get("result"), dict):
        raise EngineError("production_step_invalid", "Original completed Step has no valid result envelope.", 409)
    return envelope


class AutonomousProductionFlow(Flow[dict]):
    _services: AutonomousServices = PrivateAttr()
    _lease: c.LeaseGrant = PrivateAttr()
    _request: object = PrivateAttr()
    _proposal: c.CreativeProposal = PrivateAttr(default=None)
    _revisions: dict = PrivateAttr(default_factory=dict)
    _rendered: dict = PrivateAttr(default_factory=dict)
    _plan_admission: object = PrivateAttr(default=None)
    _rights_fact: object = PrivateAttr(default=None)

    def __init__(self, services, lease, persistence):
        super().__init__(persistence=persistence, tracing=False, max_method_calls=10)
        self._services, self._lease = services, lease
        self._request = services.engine.get_request(lease)

    def _check(self):
        current_attempt().check()
        if self._services.engine.get_request(self._lease) != self._request:
            raise EngineError("production_input_changed", "Original request and ordinary fence must remain fixed.", 409)

    def _checkpoint(self, stage):
        # Only business IDs/status enter Flow persistence. It never authorizes a
        # fee, approval, filesystem path or Run resurrection after a crash.
        self.persistence.save_state(self.state["id"], stage, self.state)

    def _revision(self, kind, body, inputs=()):
        revision = c.CreativeRevision(revision_id="autonomous." + kind + "." + self._lease.run_id,
                    kind=kind, input_revision_refs=inputs, body=json_body(body, path="revision.body"))
        saved = self._services.engine.commit_creative_revision(self._lease, revision)
        self._revisions[kind] = saved
        return saved

    def _prepare_creative(self):
        # Interactive requests keep their original ordinary lease/Owner guard.
        self._check()

    def _rights_proposal(self):
        if not callable(self._services.rights_proposal):
            raise EngineError("production_rights_proposal_missing", "Install the current Backend rights-proposal port; a raw rights tuple is not its substitute.", 503)
        return require_proposal(self._services.rights_proposal(self._lease),
                    engine=self._services.engine, context=self._services.bundle.context(self._lease),
                    request=self._request, lease=self._lease,
                    registration_sha256=self._services.registration_sha256)

    def _restore_plan(self, proposal):
        expected = {kind: "autonomous." + kind + "." + self._lease.run_id
                    for kind in ("insight", "brief", "script", "storyboard", "plan")}
        revisions = {value.revision_id: value for value in self._services.bundle.creative_revisions(self._lease)}
        plan = revisions.get(expected["plan"])
        if plan is None:
            return None
        if "format" in plan.body:
            # Parse only the already committed whole body. A legacy plan has
            # no finite targets; recovery must never add or re-approve them.
            if plan.body["format"] == "registered-production-plan-v3":
                from video_creator.domain.affected_recipe import (
                    RegisteredProductionPlanV3,
                )

                RegisteredProductionPlanV3.model_validate_json(plan_payload_bytes(plan.body))
            else:
                RegisteredProductionPlanV2.model_validate_json(plan_payload_bytes(plan.body))
        stored_proposal(plan, proposal)
        if any(revision_id not in revisions or revisions[revision_id].kind != kind
               for kind, revision_id in expected.items()):
            raise EngineError("production_plan_versions_missing", "Original committed plan requires all original same-Run creative versions; do not generate replacements.", 409)
        self._revisions = {kind: revisions[revision_id] for kind, revision_id in expected.items()}
        if plan.input_revision_refs != tuple(self._revisions[kind].revision_id
                for kind in ("insight", "brief", "script", "storyboard")):
            raise EngineError("production_plan_versions_conflict", "Immutable plan no longer binds its exact original four versions.", 409)
        self._proposal = c.CreativeProposal.model_validate(plan.body["proposal"])
        self.state["plan_revision_id"] = plan.revision_id
        return plan

    def _stage_admission(self, revision):
        # Preserve the original human _admit verbatim; only then read the real
        # typed bridge. No request-phase human admission is manufactured.
        if not self._admit(revision):
            return False
        if not callable(self._services.current_admission) or not callable(self._services.current_rights):
            raise EngineError("production_current_admission_missing", "Current human evidence bridges must be installed by Backend.", 503)
        action = "execute_plan" if revision.kind == "plan" else "continue_bundle_validation"
        fact = require_admission(self._services.current_admission(self._lease, revision.revision_id,
                    phase=revision.kind, action=action), engine=self._services.engine,
                    context=self._services.bundle.context(self._lease), request=self._request,
                    lease=self._lease, registration_sha256=self._services.registration_sha256,
                    phase=revision.kind, action=action, target_id=revision.revision_id,
                    target_sha256=digest(canonical(revision)), sources={"human_review"})
        if fact.state != "allowed":
            raise EngineError(fact.blocker_code or "production_review_required", "Original human approval is no longer current.", 403)
        if revision.kind == "plan":
            self._plan_admission = fact
            self._rights_fact = require_plan_rights(self._services.current_rights(self._lease, revision.revision_id),
                    fact, revision, engine=self._services.engine, context=self._services.bundle.context(self._lease),
                    request=self._request, lease=self._lease)
        return True

    def _recheck_plan(self):
        self._check()
        plan = self._revisions["plan"]
        admission = require_admission(self._services.current_admission(self._lease, plan.revision_id,
                    phase="plan", action="execute_plan"), engine=self._services.engine,
                    context=self._services.bundle.context(self._lease), request=self._request,
                    lease=self._lease, registration_sha256=self._services.registration_sha256,
                    phase="plan", action="execute_plan", target_id=plan.revision_id,
                    target_sha256=digest(canonical(plan)), sources={"human_review"})
        self._rights_fact = require_plan_rights(self._services.current_rights(self._lease, plan.revision_id),
                    admission, plan, engine=self._services.engine, context=self._services.bundle.context(self._lease),
                    request=self._request, lease=self._lease)
        self._plan_admission = admission

    def _admit(self, revision):
        self._check()
        actual = self._services.engine.read_review_decision(self._lease, revision.revision_id)
        if actual is None:
            # This fixed backend callback may persist an already admitted policy
            # decision; it must retain this lease. Only wait_for_review below
            # parks an interactive Run. No bool becomes a media-side grant.
            self._services.admit_revision(self._lease, revision)
            actual = self._services.engine.read_review_decision(self._lease, revision.revision_id)
        if actual is None:
            if self._request.automation.mode == "interactive":
                self._services.engine.wait_for_review(self._lease, revision.revision_id)
                self.state["outcome"] = "waiting_user"
                return False
            raise EngineError("production_preapproval_missing", "Unattended production needs an actual preauthorized backend decision/policy admission.", 503)
        if actual.action != "approve" or actual.target_revision_id != revision.revision_id:
            raise EngineError("production_review_denied", "Actual decision did not approve this exact production revision.", 409)
        return True

    @start()
    def creative(self):
        self._check()
        self._prepare_creative()
        feedback = self._services.engine.feedback_for_run(self._lease)
        if feedback is not None:
            raise EngineError("production_feedback_binding_required", "Feedback must bind original unchanged assets and target revisions through the registered backend port.", 503)
        rights_proposal = self._rights_proposal()
        original_plan = self._restore_plan(rights_proposal)
        if original_plan is not None:
            return self._stage_admission(original_plan)
        crew = CreativeCrew(self._services.engine, self._services.bundle.context(self._lease).production_id,
                    self._lease, subject=self._services.subject, route_id=self._services.text_route_id, production_roles=True)
        source = crew.proposal()
        self._proposal = c.CreativeProposal.model_validate(source.body["proposal"])
        if (isinstance(self._services.max_duration_us, bool) or not 0 < self._services.max_duration_us <= 600_000_000
                or sum(shot.duration_us for shot in self._proposal.shots) > self._services.max_duration_us):
            raise EngineError("production_duration_denied", "Planned production exceeds its installed bounded duration.", 422)
        candidate = next(value for value in self._proposal.candidates if value.candidate_id == self._proposal.selected_candidate_id)
        insight = self._revision("insight", self._proposal.insight.model_dump(mode="json"), (source.revision_id,))
        brief = self._revision("brief", {"topic": candidate.title, "audience": self._proposal.insight.audience,
                    "main_thesis": self._proposal.insight.main_thesis, "angle": self._proposal.insight.angle}, (insight.revision_id,))
        # Final approved speech is the sound-role text, not the earlier candidate
        # silently substituted for it. Candidate provenance stays explicit.
        script = self._revision("script", {"text": "\n".join(shot.narration for shot in self._proposal.shots),
                    "candidate": candidate.model_dump(mode="json"), "source_role": "声音导演"}, (source.revision_id, brief.revision_id))
        start_us, shots = 0, []
        for shot in self._proposal.shots:
            end_us = start_us + shot.duration_us
            shots.append({**shot.model_dump(mode="json"), "shot_revision_id": "autonomous.shot." + self._lease.run_id + "." + shot.shot_id,
                          "timeline_range": {"start_us": start_us, "end_us": end_us}})
            start_us = end_us
        storyboard = self._revision("storyboard", {"shots": shots, "timeline_duration_us": start_us}, (script.revision_id,))
        if not callable(self._services.prepare_plan_repair_targets):
            raise EngineError("production_plan_targets_port_missing", "The original registered BundleService plan-target preparation port is required before a new plan.", 503)
        targets = self._services.prepare_plan_repair_targets(self._lease, proposal=self._proposal,
                    script_revision_id=script.revision_id, storyboard_revision_id=storyboard.revision_id)
        from video_creator.domain.affected_recipe import (
            PlanRepairTargetsV2,
            RegisteredProductionPlanV3,
        )

        if type(targets) not in {PlanRepairTargetsV1, PlanRepairTargetsV2}:
            raise EngineError("production_plan_targets_invalid", "The original bound service must return the sole finite original target model.", 503)
        model, version, recipe = ((RegisteredProductionPlanV3, "registered-production-plan-v3", {"initial_recipe_id": "ambient-remix-v1"})
                                 if type(targets) is PlanRepairTargetsV2 else
                                 (RegisteredProductionPlanV2, "registered-production-plan-v2", {}))
        plan_body = model(format=version,
                    proposal=self._proposal, rights_proposal=rights_proposal,
                    rights=rights_proposal.rights, timeline_duration_us=start_us,
                    workflow_candidate="crewai-flow-production-v1", repair_targets=targets, **recipe)
        plan = self._revision("plan", plan_body.model_dump(mode="json"),
                    (insight.revision_id, brief.revision_id, script.revision_id, storyboard.revision_id))
        self.state.update(proposal_revision_id=source.revision_id, plan_revision_id=plan.revision_id)
        self._checkpoint("creative_versions_committed")
        ready = self._stage_admission(plan)
        if ready:
            self._checkpoint("creative_admission_observed")
        return ready

    def _registered_outputs(self, saved, roles, *, master_roles):
        ids = saved.get("asset_ids")
        if (not isinstance(ids, list) or len(ids) != len(roles)
                or any(type(value) is not str for value in ids) or len(set(ids)) != len(ids)):
            raise EngineError("production_step_invalid", "Completed output must retain its exact distinct registered asset set.", 409)
        ordered_roles = [role for role, _ in roles]
        if saved["result"].get("roles") != ordered_roles:
            raise EngineError("production_step_invalid", "Completed output must retain its original ordered media roles.", 409)
        registered = dict(zip(ordered_roles, ids, strict=True))
        if master_roles:
            # This mapping is emitted by the current backend's fenced file
            # registration. It is not a set of caller-supplied Asset IDs.
            actual = saved["result"].get("media_roles")
            if not isinstance(actual, dict) or actual != registered:
                raise EngineError("production_media_roles_missing", "Original masters require the backend's exact registered role-to-asset mapping.", 409, "reconcile")
            registered = dict(actual)
        for asset_id, (_, media_type) in zip(ids, roles, strict=True):
            current = self._services.bundle.asset(self._lease, asset_id)
            if current.media_type != media_type:
                raise EngineError("production_step_invalid", "Original registered output no longer has the expected media type.", 409)
        return registered

    def _generated(self, key, roles, request_data, route_id, builder, *, master_roles=False):
        self._recheck_plan()
        input_sha = digest(canonical_object({"request": self._request.model_dump(mode="json"), "stage": key,
                                            "body": request_data, "route_id": route_id}))
        step = self._services.engine.begin_step(self._lease, key, input_sha)
        saved = _step_result(step)
        if saved is not None:
            return self._registered_outputs(saved, roles, master_roles=master_roles)
        route = self._services.engine.configured_route(route_id)
        outputs = tuple(self._services.worker.allocate_output(self._lease, key, input_sha, role, media_type,
                    "autonomous-production-v1:" + key, "Rights require the actual approved current plan and final bundle clearance")
                    for role, media_type in roles)
        spec = builder(request_data, outputs, ordinary_lease=self._lease, cancel=current_attempt().cancel_requested,
                       deadline_monotonic=current_attempt().deadline_monotonic)
        if not isinstance(spec, BoundProductionDriver) or not callable(spec.invoke):
            raise EngineError("production_provider_missing", "Installed provider must return the exact controlled driver boundary.", 503)
        intent = c.OperationIntent(step_key=key, dedupe_key="autonomous." + key + "." + input_sha[:40],
                    input_sha256=input_sha, route_id=route_id, reserved_cost=route.max_operation_cost)
        self._recheck_plan()
        observation = self._services.executor.execute(self._lease, intent, spec.invoke, request_payload=spec.request_payload)
        if observation.status != "succeeded" or not isinstance(observation.result_json, dict):
            raise EngineError("production_provider_unavailable", "Original provider outcome must be reconciled rather than re-submitted.", 409,
                              "reconcile" if observation.status in {"unknown", "pending"} else "never")
        files = tuple(GeneratedFileManifest.model_validate(value) for value in observation.result_json.get("generated_files", ()))
        if tuple(value.attempt_id for value in files) != tuple(value.attempt_id for value in outputs):
            raise EngineError("production_output_manifest_invalid", "Successful operation must persist all original ordered allocations.", 409, "reconcile")
        result = {"roles": [role for role, _ in roles], "provider_observation_sha256": digest(canonical(observation))}
        if master_roles:
            role_attempt_ids = {role: output.attempt_id for (role, _), output in zip(roles, outputs, strict=True)}
            committed = self._services.worker.commit_generated_media_step(
                self._lease, key, input_sha, files, role_attempt_ids, result, self._services.media_validator)
        else:
            committed = self._services.worker.commit_generated_step(
                self._lease, key, input_sha, files, result, self._services.media_validator)
        saved = _step_result(committed)
        if saved is None:
            raise EngineError("production_output_manifest_invalid", "Actual commit did not complete its original registered output Step.", 409, "reconcile")
        return self._registered_outputs(saved, roles, master_roles=master_roles)

    @listen(creative)
    def production(self, ready):
        if not ready:
            return False
        self._check()
        narration = self._generated("production-narration", (("narration_audio", "audio/wav"),),
                    self._revisions["script"].body, self._services.narration_route_id, self._services.narration_driver,
                    master_roles=True)
        clips = []
        for shot in self._proposal.shots:
            self._check()
            clip = self._generated("production-" + shot.shot_id, ((shot.shot_id, "video/mp4"),),
                    shot.model_dump(mode="json"), self._services.picture_route_id, self._services.picture_driver)
            clips.append(clip[shot.shot_id])
        edit_data = {"clips": clips, "narration_audio": narration["narration_audio"], "storyboard": self._revisions["storyboard"].body}
        if self._revisions["plan"].body.get("format") == "registered-production-plan-v3":
            edit_data["recipe_id"] = "ambient-remix-v1"
        self._rendered = self._generated("production-edit", (("video", "video/mp4"), ("mixed_audio", "audio/wav"), ("cover", "image/jpeg")),
                    edit_data,
                    self._services.edit_route_id, self._services.edit_driver, master_roles=True)
        self._rendered.update(narration)
        self.state["completed_output_steps"] = ["production-narration", *["production-" + shot.shot_id for shot in self._proposal.shots], "production-edit"]
        self._checkpoint("actual_generated_assets_committed")
        return True

    @listen(production)
    def masters(self, ready):
        if not ready:
            return None
        self._recheck_plan()
        if len(set(self._rendered.values())) != 4:
            raise EngineError("production_media_roles_invalid", "Four distinct independently registered masters are required.", 422)
        input_sha = digest(canonical_object({"media_roles": self._rendered, "plan_revision_id": self._revisions["plan"].revision_id}))
        self._services.engine.begin_step(self._lease, "media-master", input_sha)
        route = self._services.engine.configured_route(self._services.master_index_route_id)
        if (route.destination != MASTER_INDEX_DESTINATION or route.source != "owned_local"
                or route.capability != "video" or route.credential_ref or route.max_operation_cost.units()):
            raise EngineError("production_master_index_denied", "Master indexing is a fixed credential-free local validation operation.", 403)
        def validate_masters(permit, secret):
            if secret is not None or permit.route.destination != MASTER_INDEX_DESTINATION:
                raise EngineError("production_master_index_denied", "Master validation cannot make a provider request.", 403)
            observed = {}
            for role, asset_id in self._rendered.items():
                self._check()
                asset = self._services.bundle.asset(self._lease, asset_id)
                path = self._services.bundle.content_path(self._lease, asset_id)
                probe = self._services.media_validator(path, asset.media_type)
                if not probe.decoded or probe != asset.probe:
                    raise EngineError("production_master_evidence_invalid", "Actual master decoding changed after the original committed output.", 422)
                observed[role] = {"asset_id": asset.asset_id, "sha256": asset.sha256, "probe": probe.model_dump(mode="json")}
            if observed["video"]["probe"]["duration_us"] != observed["mixed_audio"]["probe"]["duration_us"]:
                raise EngineError("production_media_roles_invalid", "Actual final video and mix duration differ.", 422)
            return c.OperationObservation(status="succeeded", actual_cost=c.Money(amount="0"), cost_evidence="confirmed_no_charge",
                        result_json={"observed_masters": observed, "scope": "actual already-generated master indexing; no new generation"})
        intent = c.OperationIntent(step_key="media-master", dedupe_key="autonomous.master-index." + input_sha[:40],
                    input_sha256=input_sha, route_id=self._services.master_index_route_id, reserved_cost=c.Money(amount="0"))
        observation = self._services.executor.execute(self._lease, intent, validate_masters)
        if observation.status != "succeeded":
            raise EngineError("production_master_evidence_pending", "Original master indexing outcome must remain unresolved.", 409, "reconcile")
        self._services.engine.complete_step(self._lease, "media-master", asset_ids=tuple(self._rendered.values()),
                    result_json={"media_roles": self._rendered, "source_steps": self.state["completed_output_steps"]})
        quality = self._revision("quality", {"observed_masters": observation.result_json["observed_masters"],
                    "precision": "not_measured", "rights": "not_measured", "release_evidence": "sole bundle factory still required"},
                    tuple(value.revision_id for value in self._revisions.values()))
        self.state["quality_revision_id"] = quality.revision_id
        self._checkpoint("masters_and_quality_committed")
        if not self._stage_admission(quality):
            return None
        self.state["outcome"] = "masters_ready"
        self._checkpoint("masters_ready_not_bundle_success")
        return dict(self._rendered)


class CurrentPolicyProductionFlow(AutonomousProductionFlow):
    """Same candidate Flow/production steps, directly consumes real policy facts."""
    _services: CurrentPolicyServices = PrivateAttr()
    _request_admission: object = PrivateAttr(default=None)

    def _observe_admission(self, fact, *, phase, action, target_id, target_sha256):
        checked = require_admission(fact, engine=self._services.engine,
                    context=self._services.bundle.context(self._lease), request=self._request,
                    lease=self._lease, registration_sha256=self._services.registration_sha256,
                    phase=phase, action=action, target_id=target_id, target_sha256=target_sha256,
                    sources={"owner_policy", "delegated_project"})
        if checked.state != "allowed":
            self.state["outcome"] = checked.state
            self.state["blocker_code"] = checked.blocker_code
        return checked

    def _prepare_creative(self):
        self._check()
        context = self._services.bundle.context(self._lease)
        self._request_admission = self._observe_admission(
                    self._services.policy_execution_ports.begin_execution(self._lease),
                    phase="request", action="begin_execution", target_id=context.request_revision_id,
                    target_sha256=digest(canonical(self._request)))
        if self._request_admission.state != "allowed":
            # Original runner returns the actual typed state without starting
            # the Crew, writing creative versions, parking or clearing a lease.
            raise _PolicyBlocked(self._request_admission.state, self._request_admission.blocker_code)

    def _rights_proposal(self):
        proposal = require_proposal(self._services.policy_execution_ports.rights_proposal(self._lease),
                    engine=self._services.engine, context=self._services.bundle.context(self._lease),
                    request=self._request, lease=self._lease, registration_sha256=self._services.registration_sha256)
        request_fact = self._request_admission
        if (proposal.source != request_fact.source or proposal.policy_ref != request_fact.policy_ref
                or proposal.owner_action_ref != request_fact.owner_action_ref):
            raise EngineError("production_rights_proposal_conflict", "Current proposal must retain the actual begin-execution source.", 403)
        return proposal

    def _stage_admission(self, revision):
        self._check()
        action = "execute_plan" if revision.kind == "plan" else "continue_bundle_validation"
        fact = self._observe_admission(self._services.policy_execution_ports.production_admission(
                    self._lease, revision.revision_id, phase=revision.kind, action=action),
                    phase=revision.kind, action=action, target_id=revision.revision_id,
                    target_sha256=digest(canonical(revision)))
        if fact.state != "allowed":
            return False
        if revision.kind == "plan":
            self._plan_admission = fact
            self._rights_fact = require_plan_rights(self._services.policy_execution_ports.production_rights(
                    self._lease, revision.revision_id), fact, revision, engine=self._services.engine,
                    context=self._services.bundle.context(self._lease), request=self._request, lease=self._lease)
        return True

    def _recheck_plan(self):
        if not self._stage_admission(self._revisions["plan"]):
            raise _PolicyBlocked(self.state["outcome"], self.state.get("blocker_code"))


class _PolicyBlocked(Exception):
    def __init__(self, state, blocker_code):
        self.state, self.blocker_code = state, blocker_code


def run_current_policy_upstream(services: CurrentPolicyServices, lease: c.LeaseGrant, *, checkpoint_path: Path,
                               cancel=None, deadline_monotonic=None) -> CurrentProductionUpstreamResult:
    """Same owned Run/queue; typed state never creates approval or publication."""
    if type(services) is not CurrentPolicyServices:
        raise EngineError("production_policy_services_missing", "Use the hardcoded current policy factory.", 503)
    path = Path(checkpoint_path)
    root = services.engine.db.data_dir.resolve()
    if not path.resolve().is_relative_to(root) or any(parent.is_symlink() or parent.is_junction()
            for parent in (path, *path.parents) if parent.is_relative_to(root)):
        raise EngineError("production_checkpoint_denied", "Candidate checkpoint must remain in this owned installation.", 403)
    with attempt_control(cancel, deadline_monotonic).activate():
        persistence = SQLiteFlowPersistence(db_path=str(path))
        flow = CurrentPolicyProductionFlow(services, lease, persistence)
        flow.state["id"] = str(uuid5(NAMESPACE_URL, "autonomous-production-v1:" + lease.run_id))
        try:
            result = flow.kickoff()
        except _PolicyBlocked as blocked:
            return CurrentProductionUpstreamResult(run_id=lease.run_id, fencing_token=lease.fencing_token,
                    state=blocked.state, media_roles={}, blocker_code=blocked.blocker_code)
        except EngineError as error:
            if error.retryability != "reconcile":
                raise
            return CurrentProductionUpstreamResult(run_id=lease.run_id, fencing_token=lease.fencing_token,
                    state="needs_reconciliation", media_roles={}, blocker_code=error.code)
        if result is None:
            return CurrentProductionUpstreamResult(run_id=lease.run_id, fencing_token=lease.fencing_token,
                    state=flow.state["outcome"], media_roles={}, blocker_code=flow.state.get("blocker_code"))
        return CurrentProductionUpstreamResult(run_id=lease.run_id, fencing_token=lease.fencing_token,
                    state="masters_ready", media_roles=result)


def run_autonomous_upstream(services: AutonomousServices, lease: c.LeaseGrant, *, checkpoint_path: Path,
                            cancel=None, deadline_monotonic=None) -> AutonomousUpstreamResult:
    """Called by the same trusted registered Worker, never a second dispatcher."""
    path = Path(checkpoint_path)
    root = services.engine.db.data_dir.resolve()
    if not path.resolve().is_relative_to(root) or any(parent.is_symlink() or parent.is_junction()
            for parent in (path, *path.parents) if parent.is_relative_to(root)):
        raise EngineError("production_checkpoint_denied", "Candidate checkpoint must remain in this owned installation.", 403)
    with attempt_control(cancel, deadline_monotonic).activate():
        persistence = SQLiteFlowPersistence(db_path=str(path))
        flow = AutonomousProductionFlow(services, lease, persistence)
        flow.state["id"] = str(uuid5(NAMESPACE_URL, "autonomous-production-v1:" + lease.run_id))
        try:
            result = flow.kickoff()
        except EngineError as error:
            if error.retryability == "reconcile":
                return AutonomousUpstreamResult("needs_reconciliation", blocker_code=error.code)
            raise
        return AutonomousUpstreamResult("masters_ready", result) if result is not None else AutonomousUpstreamResult("waiting_user")
