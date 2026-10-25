"""Local eleven-field plan rights consumer; legacy helper stays unchanged."""
from video_creator.application.engine import canonical, digest
from video_creator.domain.errors import EngineError
from video_creator.domain.production_authorization import ProductionRightsFact
from video_creator.workflows.current_policy_evidence import require_proposal


def require_local_plan_rights(fact, admission, revision, plan, *, services, ports, lease, request):
    if type(fact) is not ProductionRightsFact:
        raise EngineError('local_rights_fact_missing', 'Use the actual full post-admission rights fact, never a tuple.', 503)
    checked = ProductionRightsFact.model_validate_json(canonical(fact))
    context = services.bundle.context(lease)
    expected = (services.engine.instance_id, context.production_id, lease.run_id,
                context.request_revision_id, digest(canonical(request)), lease.fencing_token)
    actual = (checked.instance_id, checked.production_id, checked.run_id,
              checked.request_revision_id, checked.request_sha256, checked.fencing_token)
    now = services.engine.clock()
    if (actual != expected or admission.state != 'allowed' or (admission.phase, admission.action) != ('plan', 'execute_plan')
            or admission.target_id != revision.revision_id or admission.target_sha256 != digest(canonical(revision))
            or checked.plan_revision_id != revision.revision_id or checked.source != admission.source
            or (checked.human_approval_ref, checked.policy_ref, checked.owner_action_ref)
               != (admission.human_approval_ref, admission.policy_ref, admission.owner_action_ref)
            or checked.rights != plan.rights_proposal.rights
            or not checked.checked_at_us <= now < min(checked.valid_until_us, admission.valid_until_us)):
        raise EngineError('local_rights_fact_conflict', 'Original full local plan admission/current rights identity and lifetime are required.', 403)
    current = require_proposal(ports.rights_proposal(lease), engine=services.engine, context=context,
        request=request, lease=lease, registration_sha256=services.registration_sha256)
    original = plan.rights_proposal
    historic_fields = {'fencing_token', 'checked_at_us', 'valid_until_us'}
    expected_source = 'human_review' if original.source == 'owner_declaration' else original.source
    if (original.model_dump(exclude=historic_fields) != current.model_dump(exclude=historic_fields)
            or (original.declaring_subject, original.declaration_id, original.declaration_sha256,
                original.policy_ref, original.owner_action_ref, expected_source)
               != (checked.declaring_subject, checked.declaration_id, checked.declaration_sha256,
                   checked.policy_ref, checked.owner_action_ref, checked.source)):
        raise EngineError('local_rights_proposal_conflict', 'Preserve immutable proposal provenance; a renewed fence never rewrites the plan.', 403)
    return checked
