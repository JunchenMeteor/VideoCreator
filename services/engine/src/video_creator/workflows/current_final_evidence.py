"""Consume the actual held final-evidence port, never manufacture its facts."""
from __future__ import annotations

from video_creator.domain.component_diagnosis import (
    CurrentFinalDiagnosticContinuationV1,
    CurrentFinalDiagnosticSnapshotV1,
)
from video_creator.domain.current_final_evidence import (
    CurrentFinalEvidenceAssessment,
    CurrentFinalEvidenceContinuation,
    CurrentFinalEvidenceInputs,
    CurrentFinalEvidenceSnapshot,
)
from video_creator.domain.errors import EngineError
from video_creator.workflows.attempt_control import AttemptControl, current_attempt
from video_creator.workflows.current_policy_evidence import (
    require_admission,
    require_plan_rights,
)


def require_final_port(port):
    from video_creator.application.current_final_evidence import (
        CurrentFinalEvidencePorts,
    )

    if type(port) is not CurrentFinalEvidencePorts:
        raise EngineError("current_final_evidence_port_required", "Current production needs its actual registered held final-evidence port.", 503)
    # Type does not grant trust. Each subsequent port call verifies its service
    # registry identity, thread, original binding and actual ordinary lease.
    return port


def _binding(binding, *, engine, context, request, lease, registration_sha256):
    from video_creator.application.engine import canonical, digest

    if ((binding.instance_id, binding.production_id, binding.run_id, binding.request_revision_id,
         binding.request_sha256, binding.registration_sha256)
            != (engine.instance_id, context.production_id, lease.run_id, context.request_revision_id,
                digest(canonical(request)), registration_sha256)):
        raise EngineError("current_final_evidence_binding_conflict", "Evidence must retain the original registered Run and request.", 409)


def require_final_value(value, *, engine, bundle, context, request, lease, preparation,
                        intent_sha256, registration_sha256):
    """Check a result returned by the held port without recreating its authority."""
    from video_creator.application.engine import canonical

    if type(value) not in {CurrentFinalEvidenceInputs, CurrentFinalEvidenceAssessment}:
        raise EngineError("current_final_evidence_result_invalid", "Only the actual sole Backend result type is accepted.", 503)
    _binding(value.binding, engine=engine, context=context, request=request, lease=lease,
             registration_sha256=registration_sha256)
    if type(value) is CurrentFinalEvidenceAssessment:
        if value.snapshot is None:
            if value.verified_material is None or value.verified_material.preparation_id != preparation.preparation_id:
                raise EngineError("current_final_evidence_result_invalid", "Ready assessment must name the same actual preparation.", 409)
            return value
        model = CurrentFinalDiagnosticSnapshotV1 if type(value.snapshot) is CurrentFinalDiagnosticSnapshotV1 else CurrentFinalEvidenceSnapshot
        snapshot = model.model_validate_json(canonical(value.snapshot))
        preparation_id, intent_sha, ready = (snapshot.preparation_id, snapshot.preparation_intent_sha256,
                                             snapshot.ready_material_refs)
    else:
        preparation_id, intent_sha, ready = (value.preparation_id, value.preparation_intent_sha256,
                                             value.ready_material_refs)
    original = bundle.recover_preparation(lease, preparation.preparation_id)
    if ((preparation_id, intent_sha) != (preparation.preparation_id, intent_sha256)
            or original.bundle_id != preparation.bundle_id
            or original.bundle_revision_id != preparation.bundle_revision_id
            or {item.artifact_id: item for item in ready} != {item.artifact_id: item for item in original.materials}
            or len({item.artifact_id for item in ready}) != len(ready)):
        raise EngineError("current_final_evidence_snapshot_conflict", "Checkpoint must retain the exact original intent and actual Ready receipts.", 409)
    return value


def resolve_initial_evidence(port, *, engine, bundle, context, request, lease, preparation,
                             intent_sha256, registration_sha256):
    current_attempt().check()
    value = require_final_port(port).resolve_inputs(lease, preparation.preparation_id)
    checked = require_final_value(value, engine=engine, bundle=bundle, context=context, request=request,
                    lease=lease, preparation=preparation, intent_sha256=intent_sha256,
                    registration_sha256=registration_sha256)
    if type(checked) is CurrentFinalEvidenceAssessment and checked.snapshot is None:
        raise EngineError("current_final_evidence_result_invalid", "Input resolution cannot publish an unfinished candidate.", 409)
    return checked


def verify_final_evidence(port, manifest, *, engine, bundle, context, request, lease, preparation,
                          intent_sha256, registration_sha256):
    current_attempt().check()
    value = require_final_port(port).verify_current_final_evidence(lease, preparation.preparation_id, manifest)
    if type(value) is not CurrentFinalEvidenceAssessment:
        raise EngineError("current_final_evidence_result_invalid", "Only the held service's full verification assessment can finish this candidate.", 503)
    return require_final_value(value, engine=engine, bundle=bundle, context=context, request=request,
                    lease=lease, preparation=preparation, intent_sha256=intent_sha256,
                    registration_sha256=registration_sha256)


def reauthorize_continuation(*, engine, bundle, lease, continuation, policy_execution_ports, control, revision_refs):
    """The checkpoint is not permission; recheck actual request/plan/quality."""
    from video_creator.application.engine import canonical, digest
    from video_creator.application.production_admissions import PolicyExecutionPorts
    from video_creator.application.production_ports import ProductionPorts

    if type(control) is not AttemptControl or type(continuation) not in {CurrentFinalEvidenceContinuation, CurrentFinalDiagnosticContinuationV1}:
        raise EngineError("current_final_evidence_continuation_invalid", "Use the fixed continuation and trusted in-process control.", 403)
    if (type(continuation.execution_fence) is not int or continuation.execution_fence != lease.fencing_token
            or continuation.resume_mode not in {"retry_final_validation", "repair"}):
        raise EngineError("current_final_evidence_continuation_conflict", "Only the new original Run's current execution fence may continue.", 409)
    model = CurrentFinalDiagnosticSnapshotV1 if type(continuation) is CurrentFinalDiagnosticContinuationV1 else CurrentFinalEvidenceSnapshot
    model.model_validate_json(canonical(continuation.snapshot))
    control.check()
    context, request = bundle.context(lease), engine.get_request(lease)
    policy = request.automation.mode == "unattended"
    expected_port = PolicyExecutionPorts if policy else ProductionPorts
    if type(policy_execution_ports) is not expected_port:
        raise EngineError("production_current_admission_port_required", "Continuation requires its actual Runtime-selected human or policy ports.", 503)
    registration_sha = continuation.binding.registration_sha256
    _binding(continuation.binding, engine=engine, context=context, request=request,
             lease=lease, registration_sha256=registration_sha)
    if policy:
        fact = require_admission(policy_execution_ports.begin_execution(lease), engine=engine, context=context,
                    request=request, lease=lease, registration_sha256=registration_sha, phase="request",
                    action="begin_execution", target_id=context.request_revision_id,
                    target_sha256=digest(canonical(request)), sources={"owner_policy", "delegated_project"})
        if fact.state != "allowed":
            raise EngineError(fact.blocker_code or "production_current_admission_required", "Actual current request permission is required before continuation.", 403)
    revisions = {value.revision_id: value for value in bundle.creative_revisions(lease)}
    required = {"insight", "brief", "plan", "script", "storyboard", "quality"}
    original = {value.kind: value for value in revision_refs}
    selected = {kind: revisions[ref.revision_id] for kind, ref in original.items()
                if ref.revision_id in revisions and revisions[ref.revision_id].kind == kind
                and digest(canonical(revisions[ref.revision_id])) == ref.content_sha256}
    if set(selected) != required or len(original) != len(revision_refs):
        raise EngineError("creative_versions_missing", "Continuation cannot create replacement creative versions or masters.", 409)
    plan_fact = None
    for phase, action in (("plan", "execute_plan"), ("quality", "continue_bundle_validation")):
        control.check()
        target = selected[phase]
        actual = (policy_execution_ports.production_admission(lease, target.revision_id, phase=phase, action=action)
                  if policy else policy_execution_ports.current_production_admission(
                      lease, target.revision_id, phase=phase, action=action))
        admitted = require_admission(actual, engine=engine, context=context,
                    request=request, lease=lease, registration_sha256=registration_sha, phase=phase, action=action,
                    target_id=target.revision_id, target_sha256=digest(canonical(target)),
                    sources={"owner_policy", "delegated_project"} if policy else {"human_review"})
        if admitted.state != "allowed":
            raise EngineError(admitted.blocker_code or "production_current_admission_required", "Original plan and quality targets require fresh current permission.", 403)
        if phase == "plan":
            plan_fact = admitted
    actual_rights = (policy_execution_ports.production_rights(lease, selected["plan"].revision_id) if policy
                    else policy_execution_ports.current_production_rights(lease, selected["plan"].revision_id))
    rights = require_plan_rights(actual_rights,
                    plan_fact, selected["plan"], engine=engine, context=context, request=request, lease=lease)
    control.check()
    return context, request, plan_fact, rights
