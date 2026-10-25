"""Explicit local owned-material Flow on the original fenced Run.

This candidate never generates six placeholder Creative versions. Initial
source acquisition belongs to Backend; commit_plan_from_original_sources is
the bounded consumer of those real objects, not a source lookup/authority.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from crewai.flow import Flow, listen, start
from crewai.flow.persistence import SQLiteFlowPersistence
from pydantic import PrivateAttr

from video_creator.application.asr_result_journal import (
    AsrResultJournal,
    RegisteredOperationExecutor,
)
from video_creator.application.bundles import BundleService
from video_creator.application.engine import EngineService, canonical, digest
from video_creator.application.executor import OperationExecutor
from video_creator.application.production_admissions import PolicyExecutionPorts
from video_creator.application.production_ports import ProductionPorts
from video_creator.application.worker import WorkerService
from video_creator.domain import contracts as c
from video_creator.domain.errors import EngineError
from video_creator.domain.local_bundle import (
    CurrentProductionUpstreamResultV2,
    LocalMasterSelectionV1,
)
from video_creator.domain.local_material_production import (
    LocalAcceptedGoalRef,
    LocalMaterialPlanV1,
    LocalRegistrationV1,
    parse_local_material_plan,
)
from video_creator.domain.registered_production import (
    PROFILE,
)
from video_creator.domain.worker import GeneratedFileManifest
from video_creator.providers.production_common import permit_scope
from video_creator.providers.production_resources import file_sha256
from video_creator.workflows.attempt_control import attempt_control, current_attempt
from video_creator.workflows.autonomous_production import BoundProductionDriver
from video_creator.workflows.current_policy_evidence import (
    require_admission,
    require_proposal,
)
from video_creator.workflows.local_material_drivers import (
    create_local_material_production_drivers,
    derivative_body,
)
from video_creator.workflows.local_material_plan import (
    build_local_plan,
    propose_audio_timeline,
    propose_video_timeline,
    restore_local_plan,
    revision_ref,
    source_timeline_records,
)
from video_creator.workflows.local_material_rights import require_local_plan_rights
from video_creator.workflows.production_json import (
    canonical_object,
    json_body,
    require_body,
)

MASTER_INDEX_DESTINATION = 'local:registered-master-index-v1'


def checked_revision(revision_id, kind, input_revision_refs, body):
    """Build one CreativeRevision from the sole normalized, pre-checked body.

    `body: JsonValue` rejects tuples at construction (the third failure of this
    class); normalizing first and validating the whole revision before commit
    turns any remaining shape error into a named `media_body_invalid` with its
    first failing path.
    """
    payload = json_body({'revision_id': revision_id, 'kind': kind,
        'input_revision_refs': list(input_revision_refs), 'body': body}, path='revision')
    return c.CreativeRevision.model_validate(require_body(c.CreativeRevision, payload, path='revision'))


def publication_rights(plan, quality_revision_id):
    """Declared rights tied to this Run's quality revision.

    The installed Owner declaration has no work-scoped `approval_ref`; Bundle
    publication requires the approved revision whose body holds the exact
    declaration, so the quality body carries it bound to this Run's quality
    revision. Only that identifier is added; every declared field is kept.
    """
    if type(quality_revision_id) is not str or not quality_revision_id:
        raise EngineError('local_quality_revision_invalid',
                          'A publication rights assertion needs the actual quality revision identity.', 422)
    declared = plan.rights_proposal.rights
    if not declared:
        raise EngineError('local_rights_declaration_ambiguous',
                          'This local profile consumes exactly one actual declaration per work.', 409)
    return tuple(right.model_copy(update={'approval_ref': quality_revision_id}) for right in declared)


def derivative_input_sha(*, request, plan_revision_ref, key, body, route_id):
    """Sole hashed derivative Step input; returns its canonical JSON body too.

    The projection from `derivative_body` is both hashed here and handed to the
    fixed driver builder, so a Step's identity and its driver request cannot
    drift into different shapes.
    """
    if type(key) is not str or type(route_id) is not str:
        raise EngineError('local_builder_input_invalid',
            'A derivative Step and route identity are strings.', 422)
    projection = derivative_body(body)
    return digest(canonical_object(json_body({'profile': 'local-owned-assets-v1',
        'request': request.model_dump(mode='json'),
        'plan_revision_ref': plan_revision_ref.model_dump(mode='json'),
        'step': key, 'body': projection, 'route_id': route_id}))), projection


@dataclass(frozen=True)
class _LocalServices:
    engine: EngineService
    worker: WorkerService
    bundle: BundleService
    executor: OperationExecutor
    registration: LocalRegistrationV1
    subject: str
    media_validator: object
    drivers: object
    registration_sha256: str
    alignment_registration: object | None = None

    def commit_plan_from_original_sources(self, ordinary_lease, *, request_ref, accepted_goal,
            original_assets, original_script, original_routes, goal_ref, source_script_origin,
            input_bindings, timeline):
        """The host supplies original scoped facts, never public request extras."""
        request = self.engine.get_request(ordinary_lease)
        context = self.bundle.context(ordinary_lease)
        ports = self.production_ports if type(self) is LocalMaterialServices else self.policy_execution_ports
        proposal = require_proposal(ports.rights_proposal(ordinary_lease), engine=self.engine,
            context=context, request=request, lease=ordinary_lease, registration_sha256=self.registration_sha256)
        plan = build_local_plan(request=request, request_ref=request_ref, accepted_goal=accepted_goal,
            original_assets=original_assets, original_script=original_script, original_routes=original_routes,
            goal_ref=goal_ref, source_script_origin=source_script_origin, rights_proposal=proposal,
            input_bindings=input_bindings, timeline=timeline, max_duration_us=self.registration.max_duration_us)
        # Original declaration admission namespace; sole local format is explicit.
        # Backend must specialize the local plan source check, not add a twelfth
        # field or accept this method as a human/policy execution approval.
        body = require_body(LocalMaterialPlanV1, plan.model_dump(mode='json'))
        revision = checked_revision('autonomous.plan.' + ordinary_lease.run_id,
            'plan', (original_script[0].revision_id,), body)
        return self.engine.commit_creative_revision(ordinary_lease, revision)


@dataclass(frozen=True)
class LocalMaterialServices(_LocalServices):
    production_ports: ProductionPorts | None = None


@dataclass(frozen=True)
class LocalMaterialPolicyServices(_LocalServices):
    policy_execution_ports: PolicyExecutionPorts | None = None


def _services(*, engine, worker, bundle, executor, registration, subject, storage_root, runtime_root,
        decoder, resource_manifest_path, resource_manifest_sha256, runtime_manifest_sha256,
        ports, policy, alignment_registration):
    if (type(engine) is not EngineService or type(worker) is not WorkerService
            or type(bundle) is not BundleService or type(executor) not in (OperationExecutor, RegisteredOperationExecutor)
            or type(registration) is not LocalRegistrationV1 or worker.engine is not engine
            or worker.workflow_version != PROFILE or bundle.engine is not engine or executor.engine is not engine):
        raise EngineError('local_services_binding_conflict', 'Use the one original registered Engine/Worker/Bundle/executor.', 409)
    if type(executor) is RegisteredOperationExecutor and (
            type(executor.journal) is not AsrResultJournal or executor.journal.engine is not engine
            or executor.journal.worker is not worker):
        raise EngineError('local_executor_journal_conflict', 'Retain the original same Engine/Worker ASR journal.', 409)
    if policy:
        if type(ports) is not PolicyExecutionPorts or ports.issuer.engine is not engine:
            raise EngineError('local_policy_port_invalid', 'Retain the actual same Engine policy issuer ports.', 503)
        registration_sha = ports.registered.registration_sha256
    else:
        if (type(ports) is not ProductionPorts or ports.engine is not engine or ports.worker is not worker
                or ports.declaration != registration.rights_declaration):
            raise EngineError('local_human_port_invalid', 'Retain the actual same Engine human ports and installed declaration.', 503)
        registration_sha = ports.registration_sha256
    if type(subject) is not str or not subject or not callable(decoder):
        raise EngineError('local_services_invalid', 'The trusted host supplies its actual owner and complete decode validator.', 503)
    if subject != (ports.registered.owner_subject if policy else registration.rights_declaration.declaring_subject):
        raise EngineError('local_subject_conflict', 'Retain the actual installed Owner subject, not a caller identity.', 403)
    drivers = create_local_material_production_drivers(engine=engine, worker=worker, bundle=bundle,
        storage_root=storage_root, runtime_root=runtime_root, decoder=decoder,
        resource_manifest_path=resource_manifest_path, resource_manifest_sha256=resource_manifest_sha256,
        runtime_manifest_sha256=runtime_manifest_sha256, local_registration=registration)
    common = {'engine': engine, 'worker': worker, 'bundle': bundle, 'executor': executor, 'registration': registration,
        'subject': subject, 'media_validator': decoder, 'drivers': drivers, 'registration_sha256': registration_sha,
        'alignment_registration': alignment_registration}
    return LocalMaterialPolicyServices(**common, policy_execution_ports=ports) if policy else LocalMaterialServices(**common, production_ports=ports)


def create_local_engine_services(*, engine, worker, bundle, executor, production_ports, registration,
        subject, storage_root, runtime_root, decoder, resource_manifest_path, resource_manifest_sha256,
        runtime_manifest_sha256, alignment_registration=None):
    return _services(engine=engine, worker=worker, bundle=bundle, executor=executor, registration=registration,
        subject=subject, storage_root=storage_root, runtime_root=runtime_root, decoder=decoder,
        resource_manifest_path=resource_manifest_path, resource_manifest_sha256=resource_manifest_sha256,
        runtime_manifest_sha256=runtime_manifest_sha256, ports=production_ports, policy=False,
        alignment_registration=alignment_registration)


def create_local_policy_engine_services(*, engine, worker, bundle, executor, policy_execution_ports, registration,
        subject, storage_root, runtime_root, decoder, resource_manifest_path, resource_manifest_sha256,
        runtime_manifest_sha256, alignment_registration=None):
    return _services(engine=engine, worker=worker, bundle=bundle, executor=executor, registration=registration,
        subject=subject, storage_root=storage_root, runtime_root=runtime_root, decoder=decoder,
        resource_manifest_path=resource_manifest_path, resource_manifest_sha256=resource_manifest_sha256,
        runtime_manifest_sha256=runtime_manifest_sha256, ports=policy_execution_ports, policy=True,
        alignment_registration=alignment_registration)


def _completed(step):
    if step is None or step['status'] != 'succeeded':
        return None
    envelope = json.loads(step['result_json'])
    if type(envelope) is not dict or type(envelope.get('result')) is not dict:
        raise EngineError('local_step_invalid', 'Completed Step must retain its original result envelope.', 409)
    return envelope


class LocalMaterialFlow(Flow[dict]):
    _services: object = PrivateAttr()
    _lease: c.LeaseGrant = PrivateAttr()
    _request: object = PrivateAttr()
    _plan: object = PrivateAttr(default=None)
    _revision: object = PrivateAttr(default=None)
    _script: object = PrivateAttr(default=None)
    _roles: dict = PrivateAttr(default_factory=dict)
    _admission: object = PrivateAttr(default=None)
    _rights: object = PrivateAttr(default=None)
    _selection: object = PrivateAttr(default=None)

    def __init__(self, services, lease, persistence):
        super().__init__(persistence=persistence, tracing=False, max_method_calls=10)
        self._services, self._lease = services, lease
        self._request = services.engine.get_request(lease)

    def _check(self):
        current_attempt().check()
        if self._services.engine.get_request(self._lease) != self._request:
            raise EngineError('local_request_changed', 'The original request and actual ordinary fence remain fixed.', 409)

    def _save(self, stage):
        self.persistence.save_state(self.state['id'], stage, self.state)

    def _blocked(self, state, code):
        self.state.update(outcome=state, blocker_code=code)
        return False

    def _admit(self, revision):
        self._check()
        phase = revision.kind
        action = 'execute_plan' if phase == 'plan' else 'continue_bundle_validation'
        services = self._services
        if type(services) is LocalMaterialServices:
            # Backend parks/releases the real target exactly once. Media does
            # not fabricate a decision, lease or second quality waiting state.
            fact = services.production_ports.current_production_admission(self._lease,
                revision.revision_id, phase=phase, action=action)
            sources = {'human_review'}
        else:
            fact = services.policy_execution_ports.production_admission(self._lease,
                revision.revision_id, phase=phase, action=action)
            sources = {'owner_policy', 'delegated_project'}
        checked = require_admission(fact, engine=services.engine, context=services.bundle.context(self._lease),
            request=self._request, lease=self._lease, registration_sha256=services.registration_sha256,
            phase=phase, action=action, target_id=revision.revision_id,
            target_sha256=digest(canonical(revision)), sources=sources)
        from video_creator.application.media_registration import sys_event
        sys_event('flow_admission', run_id=self._lease.run_id, kind=revision.kind,
                  revision_id=revision.revision_id, state=checked.state, blocker=checked.blocker_code)
        if checked.state != 'allowed':
            if checked.state == 'waiting_user' and checked.blocker_code is None:
                with services.engine.db.connect_readonly() as connection:
                    prior = connection.execute("SELECT body FROM decisions WHERE run_id=?", (self._lease.run_id,)).fetchall()
                decided = any(__import__('json').loads(row[0]).get('target_revision_id') == revision.revision_id
                              for row in prior)
                if decided:
                    raise EngineError('production_review_state_inconsistent',
                                      'A stored approval exists but the current admission still waits for review', 409)
            self._blocked(checked.state, checked.blocker_code)
            if checked.state == 'waiting_user' and type(services) is LocalMaterialServices:
                self.state['waiting_revision_id'] = revision.revision_id
                self._save('local_actual_review_target_committed')
                services.engine.wait_for_review(self._lease, revision.revision_id)
            return False
        if phase == 'plan':
            rights = (services.production_ports.current_production_rights(self._lease, revision.revision_id)
                if type(services) is LocalMaterialServices else services.policy_execution_ports.production_rights(self._lease, revision.revision_id))
            self._admission = checked
            self._rights = require_local_plan_rights(rights, checked, revision, self._plan,
                services=services,
                ports=services.production_ports if type(services) is LocalMaterialServices else services.policy_execution_ports,
                request=self._request, lease=self._lease)
        return True

    def _recheck(self):
        if not self._admit(self._revision):
            raise EngineError(self.state.get('blocker_code') or 'local_plan_permission_changed', 'Original current plan permission is required for each Step.', 403)

    @start()
    def plan(self):
        self._check()
        services = self._services
        if type(services) is LocalMaterialPolicyServices:
            context = services.bundle.context(self._lease)
            fact = require_admission(services.policy_execution_ports.begin_execution(self._lease), engine=services.engine,
                context=context, request=self._request, lease=self._lease, registration_sha256=services.registration_sha256,
                phase='request', action='begin_execution', target_id=context.request_revision_id,
                target_sha256=digest(canonical(self._request)), sources={'owner_policy', 'delegated_project'})
            if fact.state != 'allowed':
                return self._blocked(fact.state, fact.blocker_code)
        revisions = {r.revision_id: r for r in services.bundle.creative_revisions(self._lease)}
        revision = revisions.get('autonomous.plan.' + self._lease.run_id)
        if revision is None:
            script_id = 'autonomous.script.' + self._lease.run_id
            script = revisions.get(script_id)
            if script is None:
                source_text = self._request.inputs.source_text or self._request.goal
                script = services.engine.commit_creative_revision(self._lease, checked_revision(script_id,
                    'script', (), {'text': source_text, 'source_origin': 'user_provided',
                    'source_kind': 'request_source_text' if self._request.inputs.source_text else 'request_goal',
                    'actual_transcript': False}))
            origin = script.body.get('source_origin') if type(script.body) is dict else None
            if origin not in {'user_provided', 'model_inference', 'input_audio_transcript'}:
                raise EngineError('local_script_origin_missing', 'Restore only explicit original script provenance.', 409)
            ports = services.production_ports if type(services) is LocalMaterialServices else services.policy_execution_ports
            selected_routes = (services.registration.input_audio_route_id, services.registration.input_visual_route_id,
                services.registration.edit_route_id, services.registration.master_index_route_id)
            sources = ports.local_material_plan_sources(self._lease, script_revision_id=script.revision_id,
                source_script_origin=origin, selected_route_ids=selected_routes)
            audios = [a for a in sources.original_assets if a.media_type == 'audio/wav' and a.probe.has_audio]
            if not audios:
                audios = [a for a in sources.original_assets if a.probe.has_audio]
            if 'video' in sources.request.outputs:
                if not audios and any(role in sources.request.outputs for role in (
                        'narration_audio', 'mixed_audio', 'actual_transcript', 'subtitles')):
                    raise EngineError('local_output_not_applicable', 'The original request asks for an audio output without a real audio input.', 422)
                selected_audio = audios[0].asset_id if audios and any(role in sources.request.outputs
                    for role in ('narration_audio', 'mixed_audio', 'actual_transcript', 'subtitles')) else None
                bindings, timeline = propose_video_timeline(sources.request, sources.original_assets,
                    narration_asset_id=selected_audio, max_duration_us=services.registration.max_duration_us)
            else:
                bindings, timeline = propose_audio_timeline(sources.request, sources.original_assets,
                    max_duration_us=services.registration.max_duration_us)
            goal = sources.accepted_goal
            goal_ref = None if goal is None else LocalAcceptedGoalRef(project_id=goal.project_id,
                goal_sha256=goal.goal_sha256, derivation_ref=goal.derivation_ref)
            revision = services.commit_plan_from_original_sources(self._lease,
                request_ref=sources.request_ref, accepted_goal=goal, original_assets=sources.original_assets,
                original_script=sources.original_script, original_routes=sources.original_routes,
                goal_ref=goal_ref, source_script_origin=origin, input_bindings=bindings, timeline=timeline)
            revisions[script.revision_id] = script
        if revision.kind != 'plan':
            raise EngineError('local_plan_invalid', 'Original target must be an actual saved plan.', 409)
        initial = parse_local_material_plan(canonical_object(json_body(revision.body, path='plan.body')).encode('utf-8'))
        ports = services.production_ports if type(services) is LocalMaterialServices else services.policy_execution_ports
        sources = ports.local_material_plan_sources(self._lease,
            script_revision_id=initial.source_script_revision_ref.revision_id,
            source_script_origin=initial.source_script_origin,
            selected_route_ids=tuple(r.route_id for r in initial.selected_capabilities))
        plan = restore_local_plan(revision, **vars(sources))
        context = services.bundle.context(self._lease)
        if (plan.request_ref.instance_id, plan.request_ref.production_id, plan.request_ref.run_id,
                plan.request_ref.request_revision_id, plan.request_ref.request_sha256) != (
                services.engine.instance_id, context.production_id, self._lease.run_id,
                context.request_revision_id, digest(canonical(self._request))):
            raise EngineError('local_plan_request_conflict', 'The immutable plan must bind this original complete request.', 409)
        if plan.outputs != self._request.outputs or tuple(a.asset_id for a in plan.material_refs) != self._request.inputs.asset_ids:
            raise EngineError('local_plan_inputs_conflict', 'Preserve original ordered outputs and all accepted input material facts.', 409)
        script = revisions.get(plan.source_script_revision_ref.revision_id)
        if script is None or revision_ref(script) != plan.source_script_revision_ref:
            raise EngineError('local_plan_script_conflict', 'Restore the exact whole original source script, never final ASR.', 409)
        for original in plan.material_refs:
            if services.bundle.asset(self._lease, original.asset_id) != original:
                raise EngineError('local_plan_asset_conflict', 'Original admitted material bytes and rights cannot drift.', 409)
        required_routes = {services.registration.input_audio_route_id, services.registration.input_visual_route_id,
            services.registration.edit_route_id, services.registration.master_index_route_id}
        if {r.route_id for r in plan.selected_capabilities} != required_routes:
            raise EngineError('local_plan_route_conflict', 'This local profile retains its exact four installed route identities.', 409)
        for original in plan.selected_capabilities:
            if services.engine.configured_route(original.route_id) != original:
                raise EngineError('local_plan_route_conflict', 'Original selected installed routes cannot drift.', 409)
        self._plan, self._revision, self._script = plan, revision, script
        self.state.update(plan_revision_id=revision.revision_id, source_script_revision_id=script.revision_id)
        self._save('local_plan_restored_without_rewriting')
        # Backend's specialized original local source validator must check Goal
        # and origin before this actual whole-plan admission can be allowed.
        if not self._admit(revision):
            return False
        self._selection = ports.local_master_selection(self._lease, plan_revision_id=revision.revision_id)
        if (type(self._selection) is not LocalMasterSelectionV1
                or self._selection.request_ref != plan.request_ref
                or self._selection.plan_revision_ref != revision_ref(revision)
                or self._selection.outputs != self._request.outputs):
            raise EngineError('local_master_selection_conflict', 'Only the actual held same-plan selection may choose applicable masters.', 409)
        return True

    def _outputs(self, saved, roles, masters):
        ids = saved.get('asset_ids')
        keys = [role for role, _ in roles]
        if (type(ids) is not list or len(ids) != len(roles) or len(set(ids)) != len(ids)
                or any(type(value) is not str for value in ids) or saved['result'].get('roles') != keys):
            raise EngineError('local_step_invalid', 'Restore the exact ordered distinct registered output set.', 409)
        actual = dict(zip(keys, ids, strict=True))
        if masters and saved['result'].get('media_roles') != actual:
            raise EngineError('local_master_mapping_invalid', 'Only Backend fenced registration supplies actual master roles.', 409, 'reconcile')
        for role, media_type in roles:
            if self._services.bundle.asset(self._lease, actual[role]).media_type != media_type:
                raise EngineError('local_step_invalid', 'Registered output MIME changed.', 409)
        return actual

    def _generated(self, key, roles, data, route_id, builder, *, masters=False):
        self._recheck()
        input_sha, body = derivative_input_sha(request=self._request,
            plan_revision_ref=revision_ref(self._revision), key=key, body=data, route_id=route_id)
        services, lease = self._services, self._lease
        saved = _completed(services.engine.begin_step(lease, key, input_sha))
        if saved is not None:
            return self._outputs(saved, roles, masters)
        route = services.engine.configured_route(route_id)
        outputs = tuple(services.worker.allocate_output(lease, key, input_sha, role, mime,
            'local-owned-assets-v1:' + key, 'Derivative of actual admitted inputs; current plan and final rights clearance remain required') for role, mime in roles)
        spec = builder(body, outputs, ordinary_lease=lease, cancel=current_attempt().cancel_requested,
            deadline_monotonic=current_attempt().deadline_monotonic)
        if type(spec) is not BoundProductionDriver or not callable(spec.invoke):
            raise EngineError('local_driver_invalid', 'The fixed builder returns the original controlled driver object.', 503)
        intent = c.OperationIntent(step_key=key, dedupe_key='local.' + key + '.' + input_sha[:40],
            input_sha256=input_sha, route_id=route_id, reserved_cost=route.max_operation_cost)
        self._recheck()
        observation = services.executor.execute(lease, intent, spec.invoke, request_payload=spec.request_payload)
        if observation.status != 'succeeded' or type(observation.result_json) is not dict:
            raise EngineError('local_output_unavailable', 'Keep original unknown/pending output; do not create another attempt.', 409,
                'reconcile' if observation.status in {'unknown', 'pending'} else 'never')
        files = tuple(GeneratedFileManifest.model_validate(v) for v in observation.result_json.get('generated_files', ()))
        if tuple(f.attempt_id for f in files) != tuple(o.attempt_id for o in outputs):
            raise EngineError('local_output_manifest_invalid', 'All original ordered allocation manifests must be complete before commit.', 409, 'reconcile')
        result = json_body({'roles': [r for r, _ in roles], 'provider_observation_sha256': digest(canonical(observation)),
            'local_plan_revision_ref': revision_ref(self._revision).model_dump(mode='json'),
            'source_bindings': [b.model_dump(mode='json') for b in self._plan.input_bindings],
            'source_provenance': source_timeline_records(self._plan)}, path='result')
        if masters:
            committed = services.worker.commit_generated_media_step(lease, key, input_sha, files,
                {r: o.attempt_id for (r, _), o in zip(roles, outputs, strict=True)}, result, services.media_validator)
        else:
            committed = services.worker.commit_generated_step(lease, key, input_sha, files, result, services.media_validator)
        saved = _completed(committed)
        if saved is None:
            raise EngineError('local_output_commit_pending', 'A settled provider result is not a committed output Step.', 409, 'reconcile')
        return self._outputs(saved, roles, masters)

    @listen(plan)
    def derivatives(self, ready):
        if not ready:
            return False
        services, registration = self._services, self._services.registration
        data = {'bindings': self._plan.input_bindings, 'timeline': self._plan.timeline}
        narration, source_steps = {}, []
        if 'narration_audio' in self._selection.master_roles:
            narration = self._generated('production-narration', (('narration_audio', 'audio/wav'),), data,
                registration.input_audio_route_id, services.drivers.narration, masters=True)
            source_steps.append('production-narration')
        clips = []
        for shot in self._plan.timeline.shots if self._selection.content_kind == 'video' else ():
            key = 'production-' + shot.shot_id
            output = self._generated(key, ((shot.shot_id, 'video/mp4'),), {**data, 'shot_id': shot.shot_id},
                registration.input_visual_route_id, services.drivers.picture)
            # Sole request form: JSON pairs, identical to the hashed body below.
            clips.append([shot.shot_id, output[shot.shot_id]])
            source_steps.append(key)
        kinds = {'video': 'video/mp4', 'mixed_audio': 'audio/wav', 'cover': 'image/jpeg'}
        edit_roles = tuple((role, kinds[role]) for role in self._selection.master_roles if role != 'narration_audio')
        result = self._generated('production-edit', edit_roles,
            {**data, 'clips': clips, 'narration_audio': narration.get('narration_audio')},
            registration.edit_route_id, services.drivers.edit, masters=True)
        combined = {**result, **narration}
        self._roles = {role: combined[role] for role in self._selection.master_roles}
        self.state['source_steps'] = [*source_steps, 'production-edit']
        self._save('local_actual_derivatives_registered')
        return True

    @listen(derivatives)
    def masters(self, ready):
        if not ready:
            return None
        self._recheck()
        services, lease, plan = self._services, self._lease, self._plan
        if (set(self._roles) != set(self._selection.master_roles)
                or len(set(self._roles.values())) != len(self._roles)):
            raise EngineError('local_master_roles_invalid', 'Only the actual ordered distinct applicable masters may be indexed.', 409)
        key = 'media-master'
        input_sha = digest(canonical_object(json_body({'profile': 'local-owned-assets-v1', 'roles': self._roles,
            'source_steps': self.state['source_steps'],
            'plan_revision_ref': revision_ref(self._revision).model_dump(mode='json')})))
        step = services.engine.begin_step(lease, key, input_sha)
        saved = _completed(step)
        route = services.engine.configured_route(services.registration.master_index_route_id)
        if route.destination != MASTER_INDEX_DESTINATION:
            raise EngineError('local_master_index_denied', 'Only the original credentialless local master validation route is allowed.', 403)

        def inspect(permit, secret):
            permit_scope(services.engine, permit, lease, services.registration.master_index_route_id,
                'video', MASTER_INDEX_DESTINATION, local=True, secret=secret)
            observed = {}
            for role, asset_id in self._roles.items():
                self._check()
                asset, path = services.bundle.asset(lease, asset_id), services.bundle.content_path(lease, asset_id)
                if path.stat().st_size != asset.size or file_sha256(path) != asset.sha256:
                    raise EngineError('local_master_changed', 'Registered master bytes changed before indexing.', 409)
                probe = services.media_validator(path, asset.media_type)
                if not probe.decoded or probe != asset.probe or file_sha256(path) != asset.sha256:
                    raise EngineError('local_master_decode_invalid', 'Full decode and byte identity must match the actual registered master.', 422)
                observed[role] = {'asset_id': asset_id, 'sha256': asset.sha256, 'probe': probe.model_dump(mode='json')}
            if any(value['probe']['duration_us'] != plan.timeline.duration_us
                    for role, value in observed.items() if role != 'cover'):
                raise EngineError('local_master_timeline_invalid', 'Actual final audio/video must match the approved timeline.', 422)
            if 'video' in observed and observed['video']['probe']['has_audio'] != bool(plan.timeline.audio_tracks):
                raise EngineError('local_master_audio_conflict', 'Final video has exactly the explicitly planned audio, never an implicit source stream.', 422)
            return c.OperationObservation(status='succeeded', actual_cost=c.Money(amount='0'), cost_evidence='confirmed_no_charge',
                result_json=json_body({'observed_masters': observed, 'scope': 'actual local derivative master indexing'}))

        intent = c.OperationIntent(step_key=key, dedupe_key='local.master-index.' + input_sha[:40], input_sha256=input_sha,
            route_id=services.registration.master_index_route_id, reserved_cost=c.Money(amount='0'))
        # Execute/restore the same original Operation. Completed Step never
        # allocates or renders media again; unknown stays reconciliation-only.
        observation = services.executor.execute(lease, intent, inspect)
        if observation.status != 'succeeded' or type(observation.result_json) is not dict:
            raise EngineError('local_master_index_pending', 'Original indexing must be reconciled without re-rendering.', 409, 'reconcile')
        if saved is None:
            services.engine.complete_step(lease, key, asset_ids=tuple(self._roles.values()),
                result_json=json_body({'media_roles': self._roles, 'source_steps': self.state['source_steps'],
                    'local_plan_revision_ref': revision_ref(self._revision).model_dump(mode='json')}, path='result'))
        elif saved['result'].get('media_roles') != self._roles or saved['result'].get('source_steps') != self.state['source_steps']:
            raise EngineError('local_master_step_conflict', 'Restore only the original indexed source lineage.', 409)
        quality_id = 'autonomous.quality.' + lease.run_id
        # The publication rights assertion is this Run's quality version: the
        # installed Owner declaration carries no work-scoped approval_ref, while
        # the Bundle publisher requires the approved revision whose body holds
        # the exact declaration. Only that identifier is added; every declared
        # field stays as installed, and the real decision is still required.
        publication = publication_rights(plan, quality_id)
        quality = services.engine.commit_creative_revision(lease, checked_revision(
            quality_id, 'quality',
            (self._script.revision_id, self._revision.revision_id),
            json_body({'format': 'local-material-quality-v1', 'observed_masters': observation.result_json['observed_masters'],
                'local_plan_revision_ref': revision_ref(self._revision).model_dump(mode='json'),
                'source_provenance': source_timeline_records(plan), 'precision': 'not_measured',
                'rights': [right.model_dump(mode='json') for right in publication],
                'asr_status': 'not_measured', 'release_evidence': 'Actual final Bundle validation remains required'})))
        self.state['quality_revision_id'] = quality.revision_id
        self._save('local_masters_and_actual_quality_committed')
        if not self._admit(quality):
            return None
        self.state['outcome'] = 'masters_ready'
        self._save('local_masters_ready_not_bundle_success')
        return dict(self._roles)


def _run(services, lease, *, checkpoint_path, cancel, deadline_monotonic, policy):
    expected = LocalMaterialPolicyServices if policy else LocalMaterialServices
    if type(services) is not expected:
        raise EngineError('local_services_invalid', 'Use the fixed actual human or policy services object.', 503)
    path = Path(checkpoint_path)
    root = services.engine.db.data_dir.resolve()
    if (not path.resolve().is_relative_to(root) or any(p.is_symlink() or p.is_junction()
            for p in (path, *path.parents) if p.is_relative_to(root))):
        raise EngineError('local_checkpoint_denied', 'The non-authorizing checkpoint stays in this owned instance.', 403)
    with attempt_control(cancel, deadline_monotonic).activate():
        # A review decision returns the same Run to queued. The previous attempt
        # persisted outcome=waiting_user; restoring that checkpoint makes the
        # Flow look complete and silently skips the post-review masters/final
        # path. A queued Run is a fresh attempt: discard only its flow progress;
        # settled Steps/Operations are re-read idempotently.
        if path.exists():
            with services.engine.db.connect_readonly() as connection:
                current = services.engine._run(connection, lease.run_id)
            if current['status'] == 'queued':
                for suffix in ('', '-wal', '-shm'):
                    candidate = Path(str(path) + suffix)
                    if candidate.exists() and candidate.is_file():
                        candidate.unlink()
        flow = LocalMaterialFlow(services, lease, SQLiteFlowPersistence(db_path=str(path)))
        flow.state['id'] = str(uuid5(NAMESPACE_URL, 'local-material-production-v1:' + lease.run_id))
        try:
            result = flow.kickoff()
        except EngineError as error:
            if error.retryability != 'reconcile':
                raise
            return CurrentProductionUpstreamResultV2(run_id=lease.run_id, fencing_token=lease.fencing_token,
                state='needs_reconciliation', selection=flow._selection, media_roles={}, blocker_code=error.code)
        return CurrentProductionUpstreamResultV2(run_id=lease.run_id, fencing_token=lease.fencing_token,
            state='masters_ready' if result is not None else flow.state['outcome'],
            selection=flow._selection,
            media_roles={} if result is None else result, blocker_code=None if result is not None else flow.state.get('blocker_code'))


def run_local_material_upstream(services, lease, *, checkpoint_path, cancel=None, deadline_monotonic=None):
    return _run(services, lease, checkpoint_path=checkpoint_path, cancel=cancel,
        deadline_monotonic=deadline_monotonic, policy=False)


def run_local_material_policy_upstream(services, lease, *, checkpoint_path, cancel=None, deadline_monotonic=None):
    return _run(services, lease, checkpoint_path=checkpoint_path, cancel=cancel,
        deadline_monotonic=deadline_monotonic, policy=True)
