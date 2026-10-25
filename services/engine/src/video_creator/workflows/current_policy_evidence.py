"""Consume complete Backend facts; never creates an approval or authority."""
from video_creator.application.engine import canonical, digest
from video_creator.domain.errors import EngineError
from video_creator.domain.production_authorization import (
    CurrentProductionAdmission,
    ProductionRightsFact,
)
from video_creator.domain.registered_production import ProductionRightsProposal
from video_creator.workflows.production_json import canonical_object


def _identity(engine, context, request, lease):
    return (engine.instance_id, context.production_id, lease.run_id,
            context.request_revision_id, digest(canonical(request)), lease.fencing_token)


def _fact_identity(fact):
    return (fact.instance_id, fact.production_id, fact.run_id,
            fact.request_revision_id, fact.request_sha256, fact.fencing_token)


def require_proposal(proposal, *, engine, context, request, lease, registration_sha256):
    if type(proposal) is not ProductionRightsProposal:
        raise EngineError("production_rights_proposal_missing", "The actual Backend request-bound proposal is required.", 503)
    # Revalidation also rejects a modified model_copy; no truthy object grants rights.
    checked = ProductionRightsProposal.model_validate_json(canonical(proposal))
    now = engine.clock()
    if (_fact_identity(checked) != _identity(engine, context, request, lease)
            or checked.project_id != context.project_id
            or checked.registration_sha256 != registration_sha256
            or not checked.checked_at_us <= now < checked.valid_until_us):
        raise EngineError("production_rights_proposal_conflict", "Current proposal must match the original request, registration, project and ordinary fence.", 403)
    return checked


def stored_proposal(plan, current):
    body = plan.body
    snapshot = body.get("rights_proposal") if isinstance(body, dict) else None
    if not isinstance(snapshot, dict):
        raise EngineError("production_plan_proposal_missing", "Original immutable plan has no complete request-bound proposal; it cannot be silently rewritten.", 409)
    original = ProductionRightsProposal.model_validate_json(canonical_object(snapshot))
    # Old time/fence remain in original plan bytes. Execution uses current facts.
    time_fields = {"fencing_token", "checked_at_us", "valid_until_us"}
    if (original.model_dump(exclude=time_fields) != current.model_dump(exclude=time_fields)
            or body.get("rights") != [right.model_dump(mode="json") for right in original.rights]):
        raise EngineError("production_plan_proposal_conflict", "Original committed proposal and current declaration differ; no new model plan or wider right is substituted.", 403)
    return original


def require_admission(fact, *, engine, context, request, lease, registration_sha256,
                      phase, action, target_id, target_sha256, sources):
    if type(fact) is not CurrentProductionAdmission:
        raise EngineError("production_current_admission_missing", "The actual complete Backend admission is required.", 503)
    checked = CurrentProductionAdmission.model_validate_json(canonical(fact))
    if (_fact_identity(checked) != _identity(engine, context, request, lease)
            or checked.registration_sha256 != registration_sha256
            or (checked.phase, checked.action, checked.target_id, checked.target_sha256)
            != (phase, action, target_id, target_sha256)):
        raise EngineError("production_current_admission_conflict", "Admission must name the exact original phase, immutable target, request, registration and fence.", 403)
    now = engine.clock()
    if checked.checked_at_us > now or (checked.state == "allowed" and
            (checked.source not in sources or not checked.checked_at_us <= now < checked.valid_until_us)):
        raise EngineError("production_current_admission_expired", "Current admission source or lifetime is invalid.", 403)
    return checked


def require_plan_rights(fact, admission, plan, *, engine, context, request, lease):
    if type(fact) is not ProductionRightsFact:
        raise EngineError("production_current_rights_missing", "The original complete post-admission rights fact is required.", 503)
    checked = ProductionRightsFact.model_validate_json(canonical(fact))
    if (admission.state != "allowed" or admission.phase != "plan" or admission.action != "execute_plan"
            or admission.target_id != plan.revision_id or admission.target_sha256 != digest(canonical(plan))
            or _fact_identity(checked) != _identity(engine, context, request, lease)
            or checked.plan_revision_id != plan.revision_id
            or checked.source != admission.source
            or (checked.human_approval_ref, checked.policy_ref, checked.owner_action_ref)
            != (admission.human_approval_ref, admission.policy_ref, admission.owner_action_ref)
            or plan.body.get("rights") != [right.model_dump(mode="json") for right in checked.rights]
            or not checked.checked_at_us <= engine.clock() < min(checked.valid_until_us, admission.valid_until_us)):
        raise EngineError("production_current_rights_conflict", "The full current rights fact must retain this exact admitted plan and source; it is not a tuple or legal authority.", 403)
    snapshot = plan.body.get("rights_proposal")
    if not isinstance(snapshot, dict):
        raise EngineError("production_plan_proposal_missing", "A v2 rights fact must retain the original committed request proposal; no legacy plan is silently upgraded.", 409)
    original = ProductionRightsProposal.model_validate_json(canonical_object(snapshot))
    expected_source = "human_review" if original.source == "owner_declaration" else original.source
    if ((original.instance_id, original.production_id, original.run_id,
            original.request_revision_id, original.request_sha256, original.registration_sha256,
            original.project_id) != (admission.instance_id, admission.production_id, admission.run_id,
            admission.request_revision_id, admission.request_sha256, admission.registration_sha256,
            context.project_id)
            or (original.declaring_subject, original.declaration_id, original.declaration_sha256,
                original.policy_ref, original.owner_action_ref, expected_source)
            != (checked.declaring_subject, checked.declaration_id, checked.declaration_sha256,
                checked.policy_ref, checked.owner_action_ref, checked.source)):
        raise EngineError("production_current_rights_conflict", "The current fact changed the committed proposal provenance.", 403)
    return checked


def require_bundle_plan_facts(plan_admission, rights_fact, plan, *, engine, context, request, lease):
    if plan_admission is None and rights_fact is None:
        return None, None  # Original v1 caller; Backend final checks remain unchanged.
    if plan_admission is None or rights_fact is None:
        raise EngineError("production_current_evidence_incomplete", "Current v2 requires both original plan admission and full rights fact.", 409)
    if type(plan_admission) is not CurrentProductionAdmission:
        raise EngineError("production_current_admission_missing", "The actual typed admission is required.", 503)
    admission = require_admission(plan_admission, engine=engine, context=context, request=request,
                    lease=lease, registration_sha256=plan_admission.registration_sha256,
                    phase="plan", action="execute_plan", target_id=plan.revision_id,
                    target_sha256=digest(canonical(plan)), sources={"human_review", "owner_policy", "delegated_project"})
    rights = require_plan_rights(rights_fact, admission, plan,
                    engine=engine, context=context, request=request, lease=lease)
    if admission.state != "allowed":
        raise EngineError(admission.blocker_code or "production_current_admission_required", "Actual current plan permission is required before Bundle effects.", 403)
    return admission, rights
