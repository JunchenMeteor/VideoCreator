"""Ordinary fenced input and current human-review facts for registered production."""
from video_creator.application.bundles import strict_json
from video_creator.application.delivery_metadata import DeliveryResolver
from video_creator.application.engine import canonical, digest
from video_creator.domain import contracts as c
from video_creator.domain.errors import EngineError
from video_creator.domain.local_material_production import plan_rights_body
from video_creator.domain.production_authorization import CurrentProductionAdmission, ProductionRightsFact
from video_creator.domain.registered_production import (
    ProductionAdmission,
    ProductionBinding,
    ProductionRightsDeclaration,
    ProductionRightsProposal,
)


class ProductionPorts:
    def __init__(self, engine, worker, declaration: ProductionRightsDeclaration, registration_sha256: str):
        self.engine, self.worker = engine, worker
        self.declaration, self.registration_sha256 = declaration, registration_sha256

    def local_material_plan_sources(self, lease, *, script_revision_id,
                                    source_script_origin, selected_route_ids):
        self.binding(lease)
        from video_creator.application.local_material_sources import LocalMaterialSourceService
        source = getattr(self.engine, '_local_material_plan_source', None)
        if type(source) is not LocalMaterialSourceService or source.engine is not self.engine or source.runtime.sha256 != self.registration_sha256:
            raise EngineError('local_material_source_unconfigured', 'Actual same Engine local source service required.', 503)
        return source.read(lease, script_revision_id=script_revision_id,
            source_script_origin=source_script_origin, selected_route_ids=selected_route_ids)[0]

    def local_material_final_context(self, lease):
        self.binding(lease)
        from video_creator.application.local_material_sources import LocalMaterialSourceService
        source = getattr(self.engine, '_local_material_plan_source', None)
        if type(source) is not LocalMaterialSourceService or source.runtime.sha256 != self.registration_sha256:
            raise EngineError('local_material_source_unconfigured', 'Actual original local source service required.', 503)
        return source.final_context(lease, self, policy=False)

    def local_master_selection(self, lease, *, plan_revision_id):
        self.binding(lease)
        from video_creator.application.local_material_sources import LocalMaterialSourceService
        source = getattr(self.engine, '_local_material_plan_source', None)
        if type(source) is not LocalMaterialSourceService or source.engine is not self.engine or source.runtime.sha256 != self.registration_sha256:
            raise EngineError('local_material_source_unconfigured', 'Actual same Engine local source is required.', 503)
        return source.master_selection(lease, self, policy=False, plan_revision_id=plan_revision_id)

    def binding(self, lease):
        with self.engine.db.connect() as connection:
            run = self.engine._lease(connection, lease)
            production = self.engine._production(connection, run['production_id'])
            row = connection.execute('SELECT * FROM execution_bindings WHERE run_id=?', (lease.run_id,)).fetchone()
        if not row or digest(row['body']) != row['content_sha256']:
            raise EngineError('execution_binding_missing', 'Registered input requires its intact original execution binding', 409)
        binding = ProductionBinding.model_validate(DeliveryResolver._json(row['body']))
        if (binding.instance_id, binding.production_id, binding.run_id, binding.request_revision_id,
                binding.request_sha256, binding.registration_sha256) != (
                self.engine.instance_id, production['id'], run['id'], production['request_revision_id'],
                digest(production['request_json']), self.registration_sha256):
            raise EngineError('execution_binding_conflict', 'Original registered execution identity changed', 409)
        return binding, production

    def production_rights(self, lease, plan_revision_id):
        c.CreativeRevision(revision_id=plan_revision_id, kind='plan', body={})
        if plan_revision_id != 'autonomous.plan.' + lease.run_id:
            raise EngineError('production_rights_scope_denied', 'Current declaration only targets this exact registered plan', 403)
        _binding, production = self.binding(lease)
        declaration = self.declaration
        now = self.engine.clock()
        if (declaration.declaring_subject != production['owner'] or production['project_id'] not in declaration.project_ids
                or declaration.expires_at_us is not None and declaration.expires_at_us <= now):
            raise EngineError('production_rights_policy_missing', 'Current Owner declaration is outside this production scope or lifetime', 503)
        for right in declaration.rights:
            if ((right.valid_from_us is not None and right.valid_from_us > now)
                    or (right.expires_at_us is not None and right.expires_at_us <= now)):
                raise EngineError('production_rights_expired', 'Current explicit rights declaration is not active', 403)
        # This is an Owner assertion for the exact plan to review, not a legal
        # authority or automatic approval. Final Bundle rights clearance stays.
        return declaration.rights

    def rights_proposal(self, lease):
        binding, _production = self.binding(lease)
        with self.engine.db.connect() as connection:
            run = self.engine._lease(connection, lease)
            production = self.engine._production(connection, run['production_id'])
            now = self.engine.clock()
            declaration = self.declaration
            if (production['owner'] != declaration.declaring_subject
                    or production['project_id'] not in declaration.project_ids
                    or (binding.production_id, binding.request_revision_id, binding.request_sha256) != (
                        production['id'], production['request_revision_id'], production['request_sha256'])):
                raise EngineError('production_rights_scope_denied', 'Proposal requires the original current owned request binding', 403)
            ends = [run['lease_until_us']]
            if declaration.expires_at_us is not None:
                ends.append(declaration.expires_at_us)
            for right in declaration.rights:
                if right.valid_from_us is not None and right.valid_from_us > now:
                    raise EngineError('production_rights_expired', 'Installed Owner declaration is not active', 403)
                if right.expires_at_us is not None:
                    ends.append(right.expires_at_us)
            if min(ends) <= now:
                raise EngineError('production_rights_expired', 'Installed Owner declaration or ordinary lease expired', 403)
            return ProductionRightsProposal(format='production-rights-proposal-v1',
                instance_id=self.engine.instance_id, production_id=production['id'], run_id=run['id'],
                request_revision_id=production['request_revision_id'], project_id=production['project_id'],
                request_sha256=production['request_sha256'], registration_sha256=binding.registration_sha256,
                declaring_subject=declaration.declaring_subject, declaration_id=declaration.declaration_id,
                declaration_sha256=digest(canonical(declaration)), rights=declaration.rights, source='owner_declaration',
                fencing_token=lease.fencing_token, checked_at_us=now, valid_until_us=min(ends))

    def current_production_admission(self, lease, revision_id, *, phase, action):
        if (phase, action) not in {('plan', 'execute_plan'), ('quality', 'continue_bundle_validation')}:
            raise EngineError('production_admission_action_invalid', 'Human bridge requires the exact original plan or quality action', 400)
        proposal = self.rights_proposal(lease)
        original = self.production_admission(lease, revision_id, phase=phase)
        with self.engine.db.connect() as connection:
            run = self.engine._lease(connection, lease)
            row = connection.execute('SELECT * FROM creative_revisions WHERE id=? AND production_id=? AND run_id=?',
                (revision_id, proposal.production_id, lease.run_id)).fetchone()
            if (not row or row['kind'] != phase or digest(row['body']) != original.revision_sha256
                    or row['content_sha256'] != original.revision_sha256):
                raise EngineError('production_review_conflict', 'Actual immutable target changed during admission', 409)
            if original.state == 'allowed':
                approval = original.approval_ref
                decision_row = connection.execute('SELECT * FROM decisions WHERE run_id=? AND idempotency_key=?',
                    (lease.run_id, approval.idempotency_key)).fetchone() if approval is not None else None
                if (decision_row is None or digest(decision_row['body']) != approval.decision_sha256
                        or decision_row['request_sha256'] != approval.decision_sha256
                        or decision_row['result_json'] != decision_row['body']):
                    raise EngineError('production_review_invalid', 'Human bridge requires the exact original stored approval', 422)
                decision = c.ReviewDecision.model_validate(strict_json(decision_row['body'].encode('utf-8')))
                if decision.action != 'approve' or decision.target_revision_id != revision_id:
                    raise EngineError('production_review_denied', 'Actual decision does not approve this exact target', 403)
            now = self.engine.clock()
            end = min(proposal.valid_until_us, run['lease_until_us'])
            if end <= now:
                raise EngineError('production_admission_expired', 'Human bridge requires a current ordinary lease and declaration', 403)
            state = {'allowed': 'allowed', 'waiting_user': 'waiting_user', 'denied': 'denied',
                     'authority_not_ready': 'waiting_authorization'}[original.state]
            return CurrentProductionAdmission(state=state, phase=phase, action=action,
                instance_id=proposal.instance_id, production_id=proposal.production_id, run_id=lease.run_id,
                request_revision_id=proposal.request_revision_id, request_sha256=proposal.request_sha256,
                registration_sha256=proposal.registration_sha256, target_id=revision_id,
                target_sha256=original.revision_sha256, fencing_token=lease.fencing_token,
                checked_at_us=now, valid_until_us=end if state == 'allowed' else None,
                source='human_review' if state == 'allowed' else None,
                human_approval_ref=original.approval_ref if state == 'allowed' else None,
                blocker_code=original.blocker_code)

    def current_production_rights(self, lease, plan_id):
        admission = self.current_production_admission(lease, plan_id, phase='plan', action='execute_plan')
        if admission.state != 'allowed':
            raise EngineError(admission.blocker_code or 'production_review_required', 'Actual approved plan is required for a rights fact', 403)
        proposal = self.rights_proposal(lease)
        if (proposal.instance_id, proposal.production_id, proposal.run_id, proposal.request_revision_id,
                proposal.request_sha256, proposal.registration_sha256, proposal.fencing_token) != (
                admission.instance_id, admission.production_id, admission.run_id, admission.request_revision_id,
                admission.request_sha256, admission.registration_sha256, admission.fencing_token):
            raise EngineError('production_rights_conflict', 'Current plan approval and declaration no longer share one request', 409)
        return ProductionRightsFact(instance_id=proposal.instance_id, production_id=proposal.production_id,
            run_id=proposal.run_id, request_revision_id=proposal.request_revision_id,
            request_sha256=proposal.request_sha256, plan_revision_id=plan_id,
            declaring_subject=proposal.declaring_subject, declaration_id=proposal.declaration_id,
            declaration_sha256=proposal.declaration_sha256, rights=proposal.rights, source='human_review',
            human_approval_ref=admission.human_approval_ref, fencing_token=lease.fencing_token,
            checked_at_us=proposal.checked_at_us, valid_until_us=min(proposal.valid_until_us, admission.valid_until_us))

    def production_admission(self, lease, revision_id, *, phase):
        if phase not in {'plan', 'quality'}:
            raise EngineError('production_admission_phase_invalid', 'Only the actual plan or quality version can be admitted', 400)
        _binding, production = self.binding(lease)
        with self.engine.db.connect() as connection:
            self.engine._lease(connection, lease)
            row = connection.execute('SELECT * FROM creative_revisions WHERE id=? AND production_id=? AND run_id=?',
                (revision_id, production['id'], lease.run_id)).fetchone()
            decisions = connection.execute('SELECT * FROM decisions WHERE run_id=? ORDER BY rowid', (lease.run_id,)).fetchall()
        if not row or row['kind'] != phase or digest(row['body']) != row['content_sha256']:
            raise EngineError('revision_not_found', 'Admission requires this exact current immutable Run version', 404)
        revision = c.CreativeRevision.model_validate(strict_json(row['body'].encode()))
        if phase == 'plan' and isinstance(revision.body, dict) and revision.body.get('format') == 'registered-local-material-plan-v1':
            source = getattr(self.engine, '_local_material_plan_source', None)
            if source is None:
                raise EngineError('local_material_source_unconfigured', 'Actual local source service required.', 503)
            source.validate(lease, revision)
        if phase == 'plan' and isinstance(revision.body, dict) and revision.body.get('format') == 'registered-production-plan-v2':
            source = getattr(self.engine, '_registered_plan_source', None)
            if source is None:
                raise EngineError('plan_repair_source_not_ready', 'Original registered plan source required', 503)
            source.validate_registered_plan(lease, revision)
        if phase == 'plan' and plan_rights_body(revision.body) != [right.model_dump(mode='json')
                for right in self.production_rights(lease, revision_id)]:
            raise EngineError('production_rights_conflict', 'The current plan changed the installed Owner declaration', 409)
        for value in decisions:
            decision = c.ReviewDecision.model_validate(strict_json(value['body'].encode()))
            if decision.target_revision_id != revision_id:
                continue
            if digest(value['body']) != value['request_sha256']:
                raise EngineError('production_review_invalid', 'Current persisted approval identity is damaged', 422)
            approval = c.ApprovalRef(run_id=lease.run_id, idempotency_key=value['idempotency_key'],
                decision_sha256=value['request_sha256'], target_revision_id=revision_id)
            return ProductionAdmission('allowed' if decision.action == 'approve' else 'denied', revision_id,
                row['content_sha256'], phase, approval_ref=approval,
                blocker_code=None if decision.action == 'approve' else 'production_review_denied')
        request = self.engine.get_request(lease)
        return ProductionAdmission('waiting_user' if request.automation.mode == 'interactive' else 'authority_not_ready',
            revision_id, row['content_sha256'], phase,
            blocker_code=None if request.automation.mode == 'interactive' else 'production_preapproval_missing')

    def admit_revision(self, lease, revision):
        fact = self.production_admission(lease, revision.revision_id, phase=revision.kind)
        if fact.revision_sha256 != digest(canonical(revision)):
            raise EngineError('production_review_conflict', 'Caller revision differs from the actual immutable admission target', 409)
        if fact.state in {'denied', 'authority_not_ready'}:
            raise EngineError(fact.blocker_code, 'Actual current approval or admitted unattended policy is required',
                              409 if fact.state == 'denied' else 503)
        return fact
