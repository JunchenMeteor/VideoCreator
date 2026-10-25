"""Current Owner-policy facts on the original ledger; no Worker activation.

Only a trusted host registers execution identities. Resource verification is a
separate concrete installation adapter, not a model assertion or boolean check.
No method here dispatches a provider, installs a policy or invents a human review.
"""

import json
import threading
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass, field
from typing import Literal, Protocol

from video_creator.application.engine import canonical, digest, identity
from video_creator.application.production_authorization import (
    ProductionAuthorizationService,
)
from video_creator.domain import contracts as c
from video_creator.domain.errors import EngineError
from video_creator.domain.local_material_production import plan_rights_body
from video_creator.domain.registered_production import ProductionRightsProposal
from video_creator.domain.production_authorization import (
    AuthorizationActionReceipt,
    AuthorizationActionRef,
    CurrentProductionAdmission,
    ProductionAdmissionFact,
    ProductionAdmissionRef,
    ProductionAuthorizationDocument,
    ProductionRightsFact,
    SelectProductionPolicy,
)


@dataclass(frozen=True)
class InstalledProductionEvidence:
    """Actual adapter observation, never public caller-controlled metadata.

    The concrete fixed installation adapter must hash the complete engine and
    indexed resources outside the DB writer. Its absence fails closed. This
    protocol alone neither registers an adapter nor proves installed resources.
    """
    instance_id: str
    registration_sha256: str
    resource_manifest_sha256: str
    runtime_manifest_sha256: str
    workflow_version: Literal['registered-media-bundle-v1']
    driver_profile: Literal['registered-production-drivers-v1']
    observed_at_us: int
    # Finite relative file identities from the actual installation observation.
    engine_source_sha256: tuple[tuple[str, str], ...]
    indexed_resource_sha256: tuple[tuple[str, str], ...]


class ProductionInstallationAuthority(Protocol):
    def observe(self) -> InstalledProductionEvidence: ...
    def assert_current(self, observation: InstalledProductionEvidence) -> None:
        """Outside writer: rehash actual source/resources; never a bool callback."""
        ...


class InstallationSessionGuard(Protocol):
    def assert_local_current(self, observation: InstalledProductionEvidence) -> None:
        """Short writer: original object/session invalidation only; no RPC/hash."""
        ...


@dataclass(frozen=True, eq=False, repr=False)
class RegisteredExecutionIdentity:
    instance_id: str
    owner_subject: str
    executing_principal_id: str
    project_ids: tuple[str, ...]
    registration_sha256: str
    resource_manifest_sha256: str
    runtime_manifest_sha256: str
    allowed_source_namespaces: tuple[tuple[str, str], ...]
    expires_at_us: int


@dataclass(frozen=True, eq=False, repr=False)
class _AdmissionGuard:
    identity: RegisteredExecutionIdentity
    installation: InstalledProductionEvidence
    minimum_registry_revision: int
    thread_id: int
    issuer: object = field(repr=False)
    native_guard: object | None = field(default=None, repr=False)
    qualification_lease: object | None = field(default=None, repr=False)


class ProductionAdmissions:
    """Private issuer, enabled only by distinct trusted installation wiring.

    A host retains an identity object issued here after it has authenticated its
    real executing principal. An HTTP/model payload cannot reconstruct it. The
    empty default and a missing concrete installation authority cannot issue an
    execution fact. Management and its separately authenticated actions remain
    exclusively in ProductionAuthorizationService.
    """
    def __init__(self, management_service: ProductionAuthorizationService, *,
                 installation_authority: ProductionInstallationAuthority | None = None,
                 installation_session_guard: InstallationSessionGuard | None = None):
        self.management_service = management_service
        self.engine = management_service.engine
        self.installation_authority = installation_authority
        self.installation_session_guard = installation_session_guard
        self._lock = threading.RLock()
        self._identities, self._guards = set(), set()
        self._native_bindings = {}

    def register_execution_identity(self, *, owner_subject, executing_principal_id, project_ids,
                                    registration_sha256, resource_manifest_sha256,
                                    runtime_manifest_sha256, allowed_source_namespaces,
                                    expires_at_us):
        """Trusted authenticated startup adapter only; not a management/MCP tool.

        Registering this identity grants no policy permission. Every fact needs
        an actual prior Owner selection, its immutable action and current floor.
        The host must not derive owner/principal/projects from task JSON.
        """
        projects, sources = tuple(project_ids), tuple(allowed_source_namespaces)
        if (not projects or len(set(projects)) != len(projects)
                or len(set(sources)) != len(sources)
                or type(expires_at_us) is not int or expires_at_us <= self.engine.clock()):
            raise EngineError('production_execution_registration_invalid', 'Trusted execution scope must be finite and current', 503)
        c.SourceBinding(system=owner_subject, namespace=executing_principal_id)
        for project_id in projects:
            c.SourceBinding(system=project_id, namespace='production-project')
        for system, namespace in sources:
            c.SourceBinding(system=system, namespace=namespace)
        c.BundleRef(instance_id=self.engine.instance_id, bundle_id='registration',
            bundle_revision_id='registration', manifest_sha256=registration_sha256)
        for sha in (resource_manifest_sha256, runtime_manifest_sha256):
            c.AssetCandidate(staging_id='registration', sha256=sha, size=1, media_type='application/json',
                             source='installed', rights='local')
        with self.engine.db.connect() as connection:
            self.management_service._project_scope(connection, owner_subject, projects)
        registered = RegisteredExecutionIdentity(self.engine.instance_id, owner_subject, executing_principal_id,
            projects, registration_sha256, resource_manifest_sha256, runtime_manifest_sha256, sources, expires_at_us)
        with self._lock:
            self._identities.add(registered)
        return registered

    def unregister_execution_identity(self, registered):
        """Actual host execution-session closure; preserves original DB facts."""
        with self._lock:
            self._identities.discard(registered)
            binding = self._native_bindings.pop(registered, None)
            if binding is not None:
                binding[0].release(binding[1])

    def bind_native_registration(self, registered, *, store, current):
        """Trusted same-Engine assembly retains the original durable source.

        The eight-field projection alone never turns into a persistent ticket.
        Existing explicitly registered in-memory identities keep their original
        behavior; native startup must retain this independent current reference.
        """
        from video_creator.application.execution_registration import (
            ExecutionRegistrationStore,
        )

        with self._lock:
            self._identity(registered)
            if (type(store) is not ExecutionRegistrationStore or store.engine is not self.engine
                    or store.control.path != self.management_service.control.path
                    or registered in self._native_bindings
                    or any(getattr(registered, name) != value for name, value in store.original_projection(current).items())):
                raise EngineError('execution_registration_binding_denied', 'Original issuer and current registration do not match this actual instance', 403)
            # Binding is not execution admission. Only an exact already
            # accepted Goal reservation may retain the current source until
            # DailyProjectService finishes its original no-side-effect writer.
            with store._accepted_goal_guard(current):
                self._native_bindings[registered] = (store, current)

    def _identity(self, registered):
        if (not isinstance(registered, RegisteredExecutionIdentity) or registered not in self._identities
                or registered.instance_id != self.engine.instance_id or registered.expires_at_us <= self.engine.clock()):
            raise EngineError('production_execution_identity_denied', 'Current authenticated installed execution identity is required', 403)
        return registered

    def _installation(self, registered):
        if self.installation_authority is None:
            raise EngineError('production_installation_authority_unconfigured', 'Concrete fixed installation observation is not registered', 503)
        observation = self.installation_authority.observe()
        expected = (self.engine.instance_id, registered.registration_sha256, registered.resource_manifest_sha256,
                    registered.runtime_manifest_sha256, 'registered-media-bundle-v1', 'registered-production-drivers-v1')
        if (not isinstance(observation, InstalledProductionEvidence)
                or (observation.instance_id, observation.registration_sha256, observation.resource_manifest_sha256,
                    observation.runtime_manifest_sha256, observation.workflow_version, observation.driver_profile) != expected
                or type(observation.observed_at_us) is not int or not 0 < observation.observed_at_us <= self.engine.clock()
                or not observation.engine_source_sha256 or not observation.indexed_resource_sha256):
            raise EngineError('production_installation_binding_invalid', 'Actual complete installation observation differs from the trusted execution registration', 503)
        for files in (observation.engine_source_sha256, observation.indexed_resource_sha256):
            if len({name for name, _sha in files}) != len(files):
                raise EngineError('production_installation_binding_invalid', 'Installation observation repeats a file identity', 503)
            for name, sha in files:
                if not name or name.startswith(('/', '\\')) or '\\' in name or ':' in name or any(p in {'', '.', '..'} for p in name.split('/')):
                    raise EngineError('production_installation_binding_invalid', 'Actual installation identities must be fixed relative files', 503)
                c.AssetCandidate(staging_id='installation', sha256=sha, size=1, media_type='application/octet-stream',
                                 source='installed', rights='local')
        self.installation_authority.assert_current(observation)
        return observation

    @contextmanager
    def current_guard(self, registered):
        """Resource I/O and external floor read precede the short DB writer.

        The same retained control lock serializes management revocation with
        admission/dispatch commits. A guard is object- and thread-scoped, cannot
        be serialized, and must not be held across provider/network execution.
        """
        with self._lock:
            registered = self._identity(registered)
            installation = self._installation(registered)
            control = self.management_service.control
            if control is None:
                raise EngineError('production_management_unconfigured', 'Retained production authorization control is required', 503)
            binding = self._native_bindings.get(registered)
            if binding is not None:
                store, current = binding
                daily = self.engine.daily_projects
                if daily is not None:
                    daily.recover_pending(registered, installation)
                # Same original store holds OwnerControl before the shared
                # ProductionControl. Do not reacquire that file lock below.
                with (store.current_guard(current) as native_guard,
                      self._issued_guard(registered, installation, native_guard.minimum_registry_revision,
                                         native_guard=native_guard) as guard):
                    yield guard
                return
            with control.locked():
                document = control.read()
                if document.pending_request_sha256:
                    raise EngineError('production_restore_refresh_required', 'Current management reservation is not yet committed', 503)
                with self._issued_guard(registered, installation, document.minimum_revision) as guard:
                    yield guard

    @contextmanager
    def _issued_guard(self, registered, installation, minimum_revision, *, native_guard=None, inside_writer=False):
        from video_creator.application.native_installation import NativeInstallationAuthority
        from video_creator.application.native_qualified_issuer import NativeQualifiedInstallationIssuer

        authority=self.installation_authority
        qualified=(authority.qualification_issuer if type(authority) is NativeInstallationAuthority else None)
        if type(qualified) is NativeQualifiedInstallationIssuer:
            if inside_writer:
                # Management's outer source scope must have already acquired
                # the original lease. This path performs no RPC/file access.
                lease=qualified._leases.get(threading.get_ident())
                if lease is None or lease.evidence is not installation:
                    raise EngineError('qualification_unavailable','Original management outer qualification lease is required',503)
                qualified._local_lease(lease)
                lease_scope=nullcontext(lease)
            else:
                lease_scope=qualified.current_writer_lease(evidence=installation)
        else:
            lease_scope=nullcontext(None)
        with lease_scope as lease:
            guard = _AdmissionGuard(registered, installation, minimum_revision, threading.get_ident(), self, native_guard,lease)
            self._guards.add(guard)
            try:
                yield guard
            finally:
                self._guards.remove(guard)

    def _guard(self, connection, guard):
        if (not isinstance(guard, _AdmissionGuard) or guard.issuer is not self or guard not in self._guards
                or guard.thread_id != threading.get_ident()):
            raise EngineError('production_authorization_guard_required', 'Current issuer-scoped writer guard is required', 403)
        registered = self._identity(guard.identity)
        binding = self._native_bindings.get(registered)
        if binding is not None:
            store, current = binding
            if guard.native_guard is None or guard.native_guard.current is not current:
                raise EngineError('execution_registration_guard_required', 'Original durable current guard is required in this writer', 403)
            store.assert_writer_current(connection, guard.native_guard)
        elif guard.native_guard is not None:
            raise EngineError('execution_registration_guard_required', 'Foreign durable current guard is not accepted', 403)
        if self.installation_session_guard is not None:
            self.installation_session_guard.assert_local_current(guard.installation)
        if guard.qualification_lease is not None:
            guard.qualification_lease._issuer.assert_writer_current(sql_connection=connection,lease=guard.qualification_lease)
        revision = self.management_service._revision(connection)
        if revision < guard.minimum_registry_revision:
            raise EngineError('production_restore_refresh_required', 'Registry was restored behind the retained control floor', 503)
        return registered, revision

    @contextmanager
    def _qualified_management_preflight(self,registered,installation):
        from video_creator.application.native_installation import NativeInstallationAuthority
        from video_creator.application.native_qualified_issuer import NativeQualifiedInstallationIssuer
        from video_creator.application.owner_services import OwnerAuthorizationService

        self._identity(registered)
        authority=self.installation_authority
        service=self.management_service
        if (type(authority) is NativeInstallationAuthority and type(authority.qualification_issuer) is NativeQualifiedInstallationIssuer):
            if type(service) is not OwnerAuthorizationService or service._qualified_authority is not authority or getattr(service,'_qualified_preflight',None) is not None:
                raise EngineError('qualification_unavailable','Original qualified management assembly is required',503)
            authority._original(installation)
            original=(threading.get_ident(),authority,installation)
            service._qualified_preflight=original
            try:yield
            finally:
                if service._qualified_preflight is original:service._qualified_preflight=None
        else:
            yield

    @contextmanager
    def _management_writer_guard(self, registered, installation, minimum_revision):
        """Fixed reauthorization service only, under its real management lock.

        Installation was observed/rechecked before the writer. The management
        service already holds its control lock and reserved its next revision;
        reopening that file lock inside the writer would be both I/O and wrong.
        """
        self._identity(registered)
        if (installation.instance_id, installation.registration_sha256, installation.resource_manifest_sha256,
                installation.runtime_manifest_sha256) != (self.engine.instance_id, registered.registration_sha256,
                registered.resource_manifest_sha256, registered.runtime_manifest_sha256):
            raise EngineError('production_installation_binding_invalid', 'Actual management preflight differs from this execution identity', 503)
        binding = self._native_bindings.get(registered)
        if binding is not None:
            store, current = binding
            with (store.management_writer_guard(current, self.management_service, minimum_revision) as native_guard,
                  self._issued_guard(registered, installation, minimum_revision, native_guard=native_guard,inside_writer=True) as guard):
                yield guard
        else:
            with self._issued_guard(registered, installation, minimum_revision,inside_writer=True) as guard:
                yield guard

    def _request(self, connection, production, run, registered):
        if (production['owner'] != registered.owner_subject or run['production_id'] != production['id']):
            raise EngineError('production_execution_scope_denied', 'Actual principal scope does not include this original request and Run', 403)
        if production['project_id'] not in registered.project_ids:
            daily = self.engine.daily_projects
            if daily is None or daily.derived_record(connection, production, registered) is None:
                raise EngineError('production_execution_scope_denied', 'Project has no actual exact local derived creation scope', 403)
        request = c.parse_production_request(production['request_json'])
        if digest(production['request_json']) != production['request_sha256'] or canonical(request) != production['request_json']:
            raise EngineError('production_request_changed', 'Original immutable request body or hash is damaged', 422)
        return request

    def _record(self, connection, policy_ref, registered, request, production, *, action=None):
        daily = self.engine.daily_projects
        derived = daily.derived_record(connection, production, registered, action=action) if daily is not None else None
        record = derived or self.management_service._record(connection, policy_ref, registered.owner_subject)
        if derived is not None:
            daily.assert_scope(derived.derived_scope, registered)
        if record.policy_ref != policy_ref:
            raise EngineError('production_policy_scope_denied', 'Current exact derived policy differs from this immutable admission', 403)
        policy, now = record.policy, self.engine.clock()
        installed_action = record.installation_action
        if derived is None:
            command = connection.execute('SELECT request_sha256,result_json FROM commands WHERE owner=? AND scope=? AND idempotency_key=?',
                (registered.owner_subject, 'production.authorization.' + installed_action.action,
                 installed_action.idempotency_key)).fetchone()
            if (not command or command['request_sha256'] != installed_action.request_sha256
                    or command['result_json'] != canonical(installed_action)
                    or installed_action.registry_revision > self.management_service._revision(connection)):
                raise EngineError('production_owner_action_unavailable', 'Original policy requires its actual immutable installed management action', 422)
            if not record.current or record.revoked:
                raise EngineError('production_policy_inactive', 'Original installed policy was replaced or revoked', 403)
        if not policy.valid_from_us <= now < policy.expires_at_us:
            raise EngineError('production_policy_inactive', 'Exact original policy was replaced, revoked or is outside its validity', 403)
        if (registered.executing_principal_id not in policy.executing_principal_ids
                or production['project_id'] not in policy.project_ids
                or (registered.registration_sha256, registered.resource_manifest_sha256, registered.runtime_manifest_sha256) != (
                    policy.registration_sha256, policy.resource_manifest_sha256, policy.runtime_manifest_sha256)):
            raise EngineError('production_policy_scope_denied', 'Policy differs from the actual execution or installation identity', 403)
        if action is not None and action not in policy.allowed_actions:
            raise EngineError('production_policy_action_denied', 'This exact current policy does not authorize the requested stage action', 403)
        brief = request.brief or c.CreativeBriefInput()
        if (brief.language not in policy.languages or brief.aspect_ratio not in policy.aspect_ratios
                or brief.target_duration_us is not None and brief.target_duration_us > policy.max_duration_us
                or request.delivery not in policy.delivery_modes or not self.engine._full_output_profile(request)
                or request.automation.max_revision_cycles > policy.max_revision_cycles
                or production['revision_cycles'] > policy.max_revision_cycles):
            raise EngineError('production_policy_creative_scope_denied', 'Original creative/delivery scope or revision limits exceed this policy', 403)
        if request.inputs.source_text and not policy.caller_supplied_text_allowed:
            raise EngineError('production_policy_text_denied', 'Caller text is outside the explicit Owner policy scope', 403)
        known_assets = {asset.asset_id: asset.sha256 for asset in policy.input_assets}
        for asset_id in request.inputs.asset_ids:
            row = connection.execute('SELECT sha256 FROM assets WHERE id=? AND owner=?', (asset_id, production['owner'])).fetchone()
            if not row or asset_id not in known_assets or row['sha256'] != known_assets[asset_id]:
                raise EngineError('production_policy_input_denied', 'Original input Asset is outside the exact current Owner identity/hash scope', 403)
        scopes = {(scope.system, scope.namespace): scope for scope in policy.allowed_sources}
        for source in request.source_bindings:
            key = (source.system, source.namespace)
            scope = scopes.get(key)
            if (scope is None or key not in registered.allowed_source_namespaces
                    or registered.executing_principal_id not in scope.executing_principal_ids
                    or source.article_id and scope.require_article_revision and not source.article_revision
                    or source.topic_id and scope.require_topic_revision and not source.topic_revision):
                raise EngineError('production_policy_source_denied', 'Source binding is outside the actual authenticated namespace and fixed-version policy scope', 403)
        routes = {route.route_id for route in policy.routes}
        if (not set(request.policy.allowed_provider_routes) <= routes
                or request.policy.external_transfer_allowed and not policy.external_transfer_allowed
                or request.policy.max_cost.currency != policy.max_production_cost.currency
                or request.policy.max_cost.units() > policy.max_production_cost.units()
                or production['cap_units'] != request.policy.max_cost.units()
                or request.policy.budget_group_id != policy.budget_group_id
                or production['budget_group_id'] != policy.budget_group_id):
            raise EngineError('production_policy_execution_scope_denied', 'Original routes, transfer, cap or existing budget group differ from the exact Owner scope', 403)
        self.management_service._policy_resources(connection, policy)
        return record

    def _earlier_action(self, connection, production, run, record, lease, action):
        rows = connection.execute('SELECT * FROM production_admissions WHERE production_id=? AND run_id=? AND action=? '
            'AND policy_id=? AND policy_revision=? AND fencing_token=?', (production['id'], run['id'], action,
            record.policy_ref.policy_id, record.policy_ref.revision, lease.fencing_token)).fetchall()
        if len(rows) != 1:
            raise EngineError('production_admission_sequence_required', 'Current fence needs its actual earlier stage admission', 403)
        fact = self._fact(rows[0])
        if (fact.policy_ref != record.policy_ref or fact.request_revision_id != production['request_revision_id']
                or fact.request_sha256 != production['request_sha256'] or fact.valid_until_us <= self.engine.clock()):
            raise EngineError('production_admission_sequence_stale', 'Earlier stage admission differs from current immutable scope', 403)
        if fact.target_kind == 'creative_revision':
            _revision, sha = self._creative(connection, production, run, fact.target_id, fact.phase)
            if sha != fact.target_sha256:
                raise EngineError('production_admission_target_changed', 'Earlier admitted creative version changed', 422)
        return fact

    def _fact(self, row):
        fact = self.management_service._model(ProductionAdmissionFact, row['body'])
        if (digest(row['body']) != row['content_sha256'] or canonical(fact) != row['body']
                or (row['id'], row['production_id'], row['run_id'], row['phase'], row['action'], row['target_kind'],
                    row['target_id'], row['target_sha256'], row['policy_id'], row['policy_revision'], row['fencing_token'], row['issued_at_us']) != (
                    fact.admission_id, fact.production_id, fact.run_id, fact.phase, fact.action, fact.target_kind,
                    fact.target_id, fact.target_sha256, fact.policy_ref.policy_id, fact.policy_ref.revision, fact.fencing_token, fact.checked_at_us)):
            raise EngineError('production_admission_changed', 'Immutable admission row and full fact bytes do not agree', 422)
        return fact

    def _existing(self, connection, production, run, *, phase, action, target_kind, target_id, policy_ref, fence):
        row = connection.execute('SELECT * FROM production_admissions WHERE production_id=? AND run_id=? AND phase=? '
            'AND action=? AND target_kind=? AND target_id=? AND policy_id=? AND policy_revision=? AND COALESCE(fencing_token,0)=?',
            (production['id'], run['id'], phase, action, target_kind, target_id, policy_ref.policy_id, policy_ref.revision, fence or 0)).fetchone()
        return self._fact(row) if row else None

    @staticmethod
    def _rights_sha(policy):
        body = json.dumps({'declaration_id': policy.rights_declaration_id,
            'rights': [right.model_dump(mode='json') for right in policy.rights]},
            ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
        return digest(body)

    def _persist(self, connection, guard, production, run, request, record, *, phase, action,
                 target_kind, target_id, target_sha256, fence):
        registered, revision = self._guard(connection, guard)
        existing = self._existing(connection, production, run, phase=phase, action=action, target_kind=target_kind,
                                  target_id=target_id, policy_ref=record.policy_ref, fence=fence)
        owner_action = record.installation_action
        source = AuthorizationActionRef(action_id=owner_action.action_id, content_sha256=digest(canonical(owner_action)))
        rights_sha = self._rights_sha(record.policy)
        if existing:
            if (existing.target_sha256 != target_sha256 or existing.request_revision_id != production['request_revision_id']
                    or existing.request_sha256 != production['request_sha256'] or existing.owner_action_ref != source
                    or existing.registration_sha256 != registered.registration_sha256
                    or existing.resource_manifest_sha256 != registered.resource_manifest_sha256
                    or existing.runtime_manifest_sha256 != registered.runtime_manifest_sha256
                    or existing.executing_principal_id != registered.executing_principal_id
                    or existing.rights_declaration_sha256 != rights_sha):
                raise EngineError('production_admission_conflict', 'The same admission identity cannot acquire different immutable facts', 409)
            if action != 'bind_request' and existing.valid_until_us <= self.engine.clock():
                raise EngineError('production_admission_expired', 'This fence requires a fresh execution attempt after admission expiry', 403)
            return existing
        now = self.engine.clock()
        # Fence and live lease are independently checked in every writer. A
        # heartbeat does not change fence or rewrite an immutable fact's bytes.
        valid_until = min(record.policy.expires_at_us, registered.expires_at_us)
        if valid_until <= now:
            raise EngineError('production_admission_expired', 'Actual Owner policy, identity or ordinary lease is no longer current', 403)
        fact = ProductionAdmissionFact(admission_id=identity('production-admission'), instance_id=self.engine.instance_id,
            production_id=production['id'], run_id=run['id'], request_revision_id=production['request_revision_id'],
            request_sha256=production['request_sha256'], executing_principal_id=registered.executing_principal_id,
            registration_sha256=registered.registration_sha256, resource_manifest_sha256=registered.resource_manifest_sha256,
            runtime_manifest_sha256=registered.runtime_manifest_sha256, phase=phase, action=action, target_kind=target_kind,
            target_id=target_id, target_sha256=target_sha256, policy_ref=record.policy_ref, owner_action_ref=source,
            rights_declaration_sha256=rights_sha, registry_revision=revision, checked_at_us=now,
            valid_until_us=valid_until, fencing_token=fence)
        body = canonical(fact)
        connection.execute('INSERT INTO production_admissions '
            '(id,production_id,run_id,phase,action,target_kind,target_id,target_sha256,policy_id,policy_revision,fencing_token,body,content_sha256,issued_at_us) '
            'VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)', (fact.admission_id, fact.production_id, fact.run_id, fact.phase, fact.action,
            fact.target_kind, fact.target_id, fact.target_sha256, fact.policy_ref.policy_id, fact.policy_ref.revision,
            fact.fencing_token, body, digest(body), fact.checked_at_us))
        return fact

    def bind_request(self, connection, guard, production, run):
        """Accept-writer hook. Original normalized request and hash remain intact.

        Only a genuine stored selection action can create this non-executing
        fact. Existing original bindings never take a changed default selection.
        This hook is not yet attached to Engine.accept_production in this slice.
        """
        registered, _revision = self._guard(connection, guard)
        request = self._request(connection, production, run, registered)
        if request.automation.mode != 'unattended':
            return None
        previous = connection.execute("SELECT * FROM production_admissions WHERE production_id=? AND run_id=? AND action='bind_request'",
                                      (production['id'], run['id'])).fetchall()
        if len(previous) > 1:
            raise EngineError('production_request_binding_conflict', 'Original request has ambiguous policy bindings', 422)
        if previous:
            fact = self._fact(previous[0])
            if (fact.request_revision_id, fact.request_sha256, fact.executing_principal_id,
                    fact.registration_sha256, fact.resource_manifest_sha256, fact.runtime_manifest_sha256) != (
                    production['request_revision_id'], production['request_sha256'], registered.executing_principal_id,
                    registered.registration_sha256, registered.resource_manifest_sha256, registered.runtime_manifest_sha256):
                raise EngineError('production_request_binding_conflict', 'Original request was bound to a different actual caller or installation', 409)
            return fact
        daily = self.engine.daily_projects
        derived = daily.derived_record(connection, production, registered) if daily is not None else None
        if derived is not None:
            # This source was atomically derived by the original trusted Goal
            # writer. No fake human create/select policy receipt is fabricated.
            record = self._record(connection, derived.policy_ref, registered, request, production)
            return self._persist(connection, guard, production, run, request, record, phase='request', action='bind_request',
                target_kind='request', target_id=production['request_revision_id'],
                target_sha256=production['request_sha256'], fence=None)
        selector = json.dumps({'owner': production['owner'], 'project_id': production['project_id'],
            'principal': registered.executing_principal_id, 'registration_sha256': registered.registration_sha256}, sort_keys=True, separators=(',', ':'))
        row = connection.execute('SELECT value FROM metadata WHERE key=?', ('production_authorization_default:' + digest(selector),)).fetchone()
        if not row:
            raise EngineError('production_policy_selection_missing', 'Actual Owner must select a policy for this original caller/project/registration', 403)
        from video_creator.application.delivery_metadata import DeliveryResolver
        raw = DeliveryResolver._json(row['value'])
        if not isinstance(raw, dict) or set(raw) != {'selection', 'action'}:
            raise EngineError('production_policy_selection_changed', 'Stored selection structure is damaged', 422)
        selection = self.management_service._model(SelectProductionPolicy, canonical_dict(raw['selection']))
        action = self.management_service._model(AuthorizationActionReceipt, canonical_dict(raw['action']))
        command = connection.execute("SELECT result_json FROM commands WHERE owner=? AND scope='production.authorization.select' AND idempotency_key=?",
                                     (production['owner'], action.idempotency_key)).fetchone()
        if (not command or command[0] != canonical(action) or action.action != 'select'
                or action.instance_id != self.engine.instance_id or action.owner_subject != production['owner']
                or production['project_id'] not in action.project_ids or action.policy_ref != selection.policy_ref
                or selection.project_id != production['project_id'] or selection.executing_principal_id != registered.executing_principal_id
                or selection.registration_sha256 != registered.registration_sha256):
            raise EngineError('production_policy_selection_changed', 'Selection does not have its actual authenticated Owner management receipt', 422)
        record = self._record(connection, selection.policy_ref, registered, request, production)
        return self._persist(connection, guard, production, run, request, record, phase='request', action='bind_request',
                             target_kind='request', target_id=production['request_revision_id'],
                             target_sha256=production['request_sha256'], fence=None)

    def _bound(self, connection, guard, production, run, *, action):
        registered, _revision = self._guard(connection, guard)
        request = self._request(connection, production, run, registered)
        fact = self._current_binding(connection, production, run)
        if (fact.instance_id, fact.request_revision_id, fact.request_sha256, fact.executing_principal_id,
                fact.registration_sha256, fact.resource_manifest_sha256, fact.runtime_manifest_sha256) != (
                self.engine.instance_id, production['request_revision_id'], production['request_sha256'], registered.executing_principal_id,
                registered.registration_sha256, registered.resource_manifest_sha256, registered.runtime_manifest_sha256):
            raise EngineError('production_request_binding_conflict', 'Original policy binding differs from current actual request or installation', 409)
        record = self._record(connection, fact.policy_ref, registered, request, production, action=action)
        if fact.owner_action_ref != AuthorizationActionRef(action_id=record.installation_action.action_id,
                content_sha256=digest(canonical(record.installation_action))) or fact.rights_declaration_sha256 != self._rights_sha(record.policy):
            raise EngineError('production_request_binding_changed', 'Original Owner action or rights declaration binding changed', 422)
        return request, record

    def _current_binding(self, connection, production, run):
        from video_creator.application.production_reauthorization import (
            BINDING_PREFIX,
            CurrentPolicyBinding,
            ReauthorizeOriginalProduction,
        )
        pointer = connection.execute('SELECT value FROM metadata WHERE key=?', (BINDING_PREFIX + run['id'],)).fetchone()
        if pointer:
            binding = self.management_service._model(CurrentPolicyBinding, pointer[0])
            if (binding.instance_id, binding.production_id, binding.run_id, binding.request_revision_id, binding.request_sha256) != (
                    self.engine.instance_id, production['id'], run['id'], production['request_revision_id'], production['request_sha256']):
                raise EngineError('production_request_binding_changed', 'Current binding pointer differs from this original request/Run', 422)
            row = connection.execute("SELECT * FROM production_admissions WHERE id=? AND production_id=? AND run_id=? AND action='bind_request'",
                (binding.admission_ref.admission_id, production['id'], run['id'])).fetchone()
            if not row or row['content_sha256'] != binding.admission_ref.content_sha256:
                raise EngineError('production_request_binding_changed', 'Current binding pointer is missing its immutable fact', 422)
            fact = self._fact(row)
            command = connection.execute("SELECT * FROM commands WHERE owner=? AND scope='production.authorization.reauthorize' AND idempotency_key=?",
                                         (production['owner'], binding.reauthorization_idempotency_key)).fetchone()
            if not command:
                raise EngineError('production_request_binding_changed', 'Pointer is not an actual authenticated Owner reauthorization action', 422)
            receipt = self.management_service._model(AuthorizationActionReceipt, command['result_json'])
            proposal = ReauthorizeOriginalProduction(production_id=production['id'], run_id=run['id'],
                request_revision_id=production['request_revision_id'], request_sha256=production['request_sha256'], policy_ref=fact.policy_ref)
            request_body = canonical_dict({'owner_subject': production['owner'], 'scope': 'production.authorization.reauthorize',
                'idempotency_key': command['idempotency_key'], 'action': 'reauthorize', 'command': proposal.model_dump(mode='json')})
            if (digest(command['result_json']) != binding.reauthorization_action_ref.content_sha256
                    or receipt.action_id != binding.reauthorization_action_ref.action_id
                    or receipt.instance_id != self.engine.instance_id or receipt.owner_subject != production['owner']
                    or receipt.action != 'reauthorize' or receipt.policy_ref != fact.policy_ref
                    or receipt.idempotency_key != command['idempotency_key']
                    or receipt.request_sha256 != command['request_sha256'] or command['request_sha256'] != digest(request_body)
                    or receipt.registry_revision > self.management_service._revision(connection)
                    or (receipt.target_production_id, receipt.target_request_revision_id, receipt.target_request_sha256) != (
                        production['id'], production['request_revision_id'], production['request_sha256'])
                    or production['project_id'] not in receipt.project_ids):
                raise EngineError('production_request_binding_changed', 'Actual original Owner reauthorization receipt and pointer do not agree', 422)
            return fact
        rows = connection.execute("SELECT * FROM production_admissions WHERE production_id=? AND run_id=? AND action='bind_request'",
                                  (production['id'], run['id'])).fetchall()
        if len(rows) != 1:
            raise EngineError('production_request_binding_missing', 'Original unattended Run lacks one exact immutable Owner policy binding', 403)
        return self._fact(rows[0])

    def require_operation_current(self, connection, guard, lease):
        """Before an original prepare/claim boundary, not provider execution.

        An actual plan commits the stage boundary. Its current samefence fact
        must have been issued by production_admission, never task JSON. Reading
        an existing Operation or settling an original observation needs no new
        production permission and does not call this port.
        """
        run = self.engine._lease(connection, lease)
        production = self.engine._production(connection, run['production_id'])
        request, record = self._bound(connection, guard, production, run, action='begin_execution')
        fact = self._persist(connection, guard, production, run, request, record, phase='request', action='begin_execution',
            target_kind='request', target_id=production['request_revision_id'], target_sha256=production['request_sha256'], fence=lease.fencing_token)
        self.assert_production_admission_current(connection, guard, lease,
            ProductionAdmissionRef(admission_id=fact.admission_id, content_sha256=digest(canonical(fact))), stage='begin_execution')
        plan = connection.execute("SELECT id FROM creative_revisions WHERE production_id=? AND run_id=? AND kind='plan' ORDER BY rowid DESC LIMIT 1",
                                  (production['id'], run['id'])).fetchone()
        if plan:
            _request, record = self._bound(connection, guard, production, run, action='execute_plan')
            plan_fact = self._earlier_action(connection, production, run, record, lease, 'execute_plan')
            if plan_fact.target_id != plan[0]:
                raise EngineError('production_admission_stage_conflict', 'The current committed plan differs from the admitted stage', 403)
            self.assert_production_admission_current(connection, guard, lease,
                ProductionAdmissionRef(admission_id=plan_fact.admission_id, content_sha256=digest(canonical(plan_fact))), stage='execute_plan')
        return fact

    def begin_execution(self, registered, lease):
        with self.current_guard(registered) as guard, self.engine.db.transaction() as connection:
            run = self.engine._lease(connection, lease)
            production = self.engine._production(connection, run['production_id'])
            request, record = self._bound(connection, guard, production, run, action='begin_execution')
            fact = self._persist(connection, guard, production, run, request, record, phase='request', action='begin_execution',
                target_kind='request', target_id=production['request_revision_id'], target_sha256=production['request_sha256'], fence=lease.fencing_token)
            return self._current(fact, record)

    def _creative(self, connection, production, run, revision_id, phase):
        row = connection.execute('SELECT * FROM creative_revisions WHERE id=? AND production_id=? AND run_id=?',
                                  (revision_id, production['id'], run['id'])).fetchone()
        if not row or row['kind'] != phase:
            raise EngineError('production_admission_target_unavailable', 'Actual immutable sameRun creative target is required', 404)
        revision = self.management_service._model(c.CreativeRevision, row['body'])
        if canonical(revision) != row['body'] or digest(row['body']) != row['content_sha256']:
            raise EngineError('production_admission_target_changed', 'Immutable creative target bytes or SHA changed', 422)
        return revision, row['content_sha256']

    def production_admission(self, registered, lease, revision_id, *, phase, action):
        """Policy branch only. The legacy real human service remains separate.

        execute_plan binds the actual plan and assertion; continue validation
        allows factory checks, never grants verified QC or final publication.
        Final publication is intentionally not accepted by this creative hook.
        """
        if (phase, action) not in {('plan', 'execute_plan'), ('quality', 'continue_bundle_validation')}:
            raise EngineError('production_admission_action_invalid', 'Creative admission must match its exact plan or quality action', 400)
        validated_plan = None
        validated_local_plan = None
        local_plan_source = getattr(self.engine, '_local_material_plan_source', None)
        plan_source = getattr(self.engine, '_registered_plan_source', None)
        if phase == 'plan':
            with self.engine.db.connect_readonly() as connection:
                run = self.engine._lease(connection, lease)
                production = self.engine._production(connection, run['production_id'])
                original_revision, original_sha = self._creative(connection, production, run, revision_id, phase)
            if isinstance(original_revision.body, dict) and original_revision.body.get('format') == 'registered-production-plan-v2':
                if plan_source is None:
                    raise EngineError('plan_repair_source_not_ready', 'Original registered plan source required', 503)
                validated_plan = plan_source.validate_registered_plan(lease, original_revision)
            if isinstance(original_revision.body, dict) and original_revision.body.get('format') == 'registered-local-material-plan-v1':
                if local_plan_source is None:
                    raise EngineError('local_material_source_unconfigured', 'Original local plan source required.', 503)
                validated_local_plan = local_plan_source.validate(lease, original_revision)
        with self.current_guard(registered) as guard, self.engine.db.transaction() as connection:
            run = self.engine._lease(connection, lease)
            production = self.engine._production(connection, run['production_id'])
            request, record = self._bound(connection, guard, production, run, action=action)
            self._earlier_action(connection, production, run, record, lease, 'begin_execution')
            if phase == 'quality':
                self._earlier_action(connection, production, run, record, lease, 'execute_plan')
            revision, target_sha = self._creative(connection, production, run, revision_id, phase)
            if validated_plan is not None:
                if target_sha != original_sha:
                    raise EngineError('plan_repair_source_changed', 'Immutable plan changed before admission', 409)
                plan_source.assert_plan_sources_writer(connection, lease, validated_plan, guard)
            if validated_local_plan is not None:
                if target_sha != original_sha:
                    raise EngineError('local_plan_source_changed', 'Immutable local plan changed before admission.', 409)
                local_plan_source.assert_writer(connection, lease, validated_local_plan, guard)
            if phase == 'plan' and (not isinstance(revision.body, dict) or plan_rights_body(revision.body) != [
                    right.model_dump(mode='json') for right in record.policy.rights]):
                raise EngineError('production_rights_conflict', 'Actual plan must bind the exact actual Owner policy declaration', 409)
            if phase == 'plan':
                now = self.engine.clock()
                if any(right.valid_from_us is not None and right.valid_from_us > now
                       or right.expires_at_us is not None and right.expires_at_us <= now for right in record.policy.rights):
                    raise EngineError('production_rights_expired', 'Exact actual Owner plan declaration is no longer current', 403)
            fact = self._persist(connection, guard, production, run, request, record, phase=phase, action=action,
                target_kind='creative_revision', target_id=revision_id, target_sha256=target_sha, fence=lease.fencing_token)
            if validated_plan is not None:
                plan_source.assert_plan_sources_writer(connection, lease, validated_plan, guard)
            if validated_local_plan is not None:
                local_plan_source.assert_writer(connection, lease, validated_local_plan, guard)
            return self._current(fact, record)

    @staticmethod
    def _current(fact, record=None):
        return CurrentProductionAdmission(state='allowed', phase=fact.phase, action=fact.action,
            instance_id=fact.instance_id, production_id=fact.production_id, run_id=fact.run_id,
            request_revision_id=fact.request_revision_id, request_sha256=fact.request_sha256,
            registration_sha256=fact.registration_sha256, target_id=fact.target_id, target_sha256=fact.target_sha256,
            fencing_token=fact.fencing_token, checked_at_us=fact.checked_at_us, valid_until_us=fact.valid_until_us,
            source='delegated_project' if record is not None and hasattr(record, 'derived_source') else 'owner_policy',
            policy_ref=fact.policy_ref, owner_action_ref=fact.owner_action_ref,
            admission_ref=ProductionAdmissionRef(admission_id=fact.admission_id, content_sha256=digest(canonical(fact))))

    def assert_production_admission_current(self, connection, guard, lease, admission_ref, *, stage):
        """Local deterministic writer guard. No resource/file/network I/O here.

        The caller must obtain current_guard before entering its DB writer.
        Original provider reconciliation never calls this normal execution port.
        """
        run = self.engine._lease(connection, lease)
        production = self.engine._production(connection, run['production_id'])
        row = connection.execute('SELECT * FROM production_admissions WHERE id=? AND production_id=? AND run_id=?',
                                 (admission_ref.admission_id, production['id'], run['id'])).fetchone()
        if not row or row['content_sha256'] != admission_ref.content_sha256:
            raise EngineError('production_admission_unavailable', 'Current ordinary execution needs its exact stored fact', 403)
        fact = self._fact(row)
        if fact.action == 'bind_request' or fact.fencing_token != lease.fencing_token or fact.valid_until_us <= self.engine.clock():
            raise EngineError('production_admission_stale', 'Binding, old fence or expired fact is not an execution permit', 403)
        if stage not in {'begin_execution', 'execute_plan', 'continue_bundle_validation'} or stage != fact.action:
            raise EngineError('production_admission_stage_conflict', 'Writer must use the exact current stage action', 403)
        _request, record = self._bound(connection, guard, production, run, action=fact.action)
        if record.policy_ref != fact.policy_ref:
            raise EngineError('production_admission_policy_conflict', 'Writer fact differs from the exact original bound policy', 409)
        if fact.target_kind == 'request':
            current_sha = production['request_sha256']
        else:
            _creative, current_sha = self._creative(connection, production, run, fact.target_id, fact.phase)
        if current_sha != fact.target_sha256:
            raise EngineError('production_admission_target_conflict', 'Writer target differs from its actual immutable version', 409)
        return fact

    def rights_proposal(self, registered, lease):
        """Current request-bound declaration; creates no plan or permission."""
        with self.current_guard(registered) as guard, self.engine.db.connect() as connection:
            run = self.engine._lease(connection, lease)
            production = self.engine._production(connection, run['production_id'])
            _request, record = self._bound(connection, guard, production, run, action='begin_execution')
            earlier = self._earlier_action(connection, production, run, record, lease, 'begin_execution')
            now = self.engine.clock()
            ends = [record.policy.expires_at_us, registered.expires_at_us, run['lease_until_us'], earlier.valid_until_us]
            for right in record.policy.rights:
                if (right.basis != 'user_asserted' or right.valid_from_us is not None and right.valid_from_us > now
                        or right.expires_at_us is not None and right.expires_at_us <= now):
                    raise EngineError('production_rights_expired', 'Current request declaration is outside its actual scope or lifetime', 403)
                if right.expires_at_us is not None:
                    ends.append(right.expires_at_us)
            return ProductionRightsProposal(format='production-rights-proposal-v1',
                instance_id=self.engine.instance_id, production_id=production['id'], run_id=run['id'],
                request_revision_id=production['request_revision_id'], project_id=production['project_id'],
                request_sha256=production['request_sha256'], registration_sha256=registered.registration_sha256,
                declaring_subject=production['owner'], declaration_id=record.policy.rights_declaration_id,
                declaration_sha256=self._rights_sha(record.policy), rights=record.policy.rights,
                source='delegated_project' if hasattr(record, 'derived_source') else 'owner_policy',
                policy_ref=record.policy_ref, owner_action_ref=AuthorizationActionRef(
                    action_id=record.installation_action.action_id, content_sha256=digest(canonical(record.installation_action))),
                fencing_token=lease.fencing_token, checked_at_us=now, valid_until_us=min(ends))

    def production_rights(self, registered, lease, plan_revision_id):
        """Rights fact only after the exact committed plan has current admission."""
        with self.current_guard(registered) as guard, self.engine.db.connect() as connection:
            run = self.engine._lease(connection, lease)
            production = self.engine._production(connection, run['production_id'])
            _request, record = self._bound(connection, guard, production, run, action='execute_plan')
            c.CreativeRevision(revision_id=plan_revision_id, kind='plan', body={})
            if plan_revision_id != 'autonomous.plan.' + lease.run_id:
                raise EngineError('production_rights_scope_denied', 'Owner declaration targets this exact registered Run plan', 403)
            plan, plan_sha = self._creative(connection, production, run, plan_revision_id, 'plan')
            admitted = self._earlier_action(connection, production, run, record, lease, 'execute_plan')
            if (admitted.target_id != plan_revision_id or admitted.target_sha256 != plan_sha or not isinstance(plan.body, dict)
                    or plan_rights_body(plan.body) != [right.model_dump(mode='json') for right in record.policy.rights]):
                raise EngineError('production_rights_conflict', 'Rights fact requires the exact committed and admitted plan declaration', 409)
            self.assert_production_admission_current(connection, guard, lease,
                ProductionAdmissionRef(admission_id=admitted.admission_id, content_sha256=digest(canonical(admitted))),
                stage='execute_plan')
            now = self.engine.clock()
            rights = record.policy.rights
            ends = [record.policy.expires_at_us, registered.expires_at_us, run['lease_until_us'], admitted.valid_until_us]
            for right in rights:
                if right.valid_from_us is not None and right.valid_from_us > now or right.expires_at_us is not None and right.expires_at_us <= now:
                    raise EngineError('production_rights_expired', 'Actual Owner assertion has no current validity interval', 403)
                if right.expires_at_us is not None:
                    ends.append(right.expires_at_us)
            return ProductionRightsFact(instance_id=self.engine.instance_id, production_id=production['id'], run_id=run['id'],
                request_revision_id=production['request_revision_id'], request_sha256=production['request_sha256'],
                plan_revision_id=plan_revision_id, declaring_subject=production['owner'], declaration_id=record.policy.rights_declaration_id,
                declaration_sha256=self._rights_sha(record.policy), rights=rights,
                source='delegated_project' if hasattr(record, 'derived_source') else 'owner_policy',
                policy_ref=record.policy_ref, owner_action_ref=AuthorizationActionRef(action_id=record.installation_action.action_id,
                    content_sha256=digest(canonical(record.installation_action))), fencing_token=lease.fencing_token,
                checked_at_us=now, valid_until_us=min(ends))

    def authorization_document(self, registered, lease, plan_admission_ref):
        with self.current_guard(registered) as guard, self.engine.db.connect() as connection:
            fact = self.assert_production_admission_current(connection, guard, lease, plan_admission_ref, stage='execute_plan')
            production = self.engine._production(connection, fact.production_id)
            run = self.engine._run(connection, fact.run_id)
            _request, record = self._bound(connection, guard, production, run, action='execute_plan')
            if hasattr(record, 'derived_source'):
                from video_creator.domain.daily_project_authorization import (
                    ProductionAuthorizationDocumentV02,
                )

                return ProductionAuthorizationDocumentV02(document_id='production-authorization.' + fact.admission_id,
                    source=record.derived_source, policy_ref=record.policy_ref, plan_admission=fact)
            return ProductionAuthorizationDocument(document_id='production-authorization.' + fact.admission_id,
                policy_ref=record.policy_ref, policy=record.policy, owner_action=record.installation_action, plan_admission=fact)

    def _finalize_bundle_current(self, connection, guard, lease, publication_scope):
        """Only the real Bundle publisher's active verification scope may call.

        No creative/tool port returns this permission. The final fact and Bundle
        visibility commit share one existing writer; no future hash is inserted
        into portable provenance or the Manifest itself.
        """
        from video_creator.application.bundle_authorization import (
            BundlePublicationScope,
        )
        if (not isinstance(publication_scope, BundlePublicationScope)
                or publication_scope.service.engine is not self.engine):
            raise EngineError('production_publication_scope_invalid', 'This issuer requires its exact real Bundle publisher scope', 403)
        manifest, final_context = publication_scope.service.assert_publication_scope(publication_scope, lease)
        run = self.engine._lease(connection, lease)
        production = self.engine._production(connection, run['production_id'])
        latest = connection.execute('SELECT id FROM runs WHERE production_id=? ORDER BY rowid DESC LIMIT 1', (production['id'],)).fetchone()
        if not latest or latest[0] != run['id']:
            raise EngineError('production_publication_run_conflict', 'An old Run cannot publish over the actual current production', 409)
        request, record = self._bound(connection, guard, production, run, action='finalize_bundle')
        self._earlier_action(connection, production, run, record, lease, 'begin_execution')
        plan = self._earlier_action(connection, production, run, record, lease, 'execute_plan')
        quality = self._earlier_action(connection, production, run, record, lease, 'continue_bundle_validation')
        if ((manifest.instance_id, manifest.production_id, manifest.run_id, manifest.request_revision_id, manifest.request_sha256) != (
                self.engine.instance_id, production['id'], run['id'], production['request_revision_id'], production['request_sha256'])
                or (quality.target_id, quality.target_sha256) != (manifest.quality_ref.revision_id, manifest.quality_ref.content_sha256)
                or not any(ref.kind == 'plan' and (ref.revision_id, ref.content_sha256) == (plan.target_id, plan.target_sha256)
                           for ref in manifest.creative_revision_refs)
                or manifest.workflow_version != record.policy.workflow_version
                or manifest.timeline_duration_us > record.policy.max_duration_us
                or set(manifest.requested_outputs) != {'video', 'narration_audio', 'mixed_audio', 'approved_script',
                                                     'actual_transcript', 'subtitles', 'semantic_manifest', 'rag_chunks'}
                or final_context.stage != 'final_manifest' or final_context.fencing_token != lease.fencing_token):
            raise EngineError('production_publication_binding_invalid', 'Actual final work/quality/plan/output scope differs from current policy', 403)
        video = next((item for item in manifest.artifacts if item.relative_path == 'Media/video.mp4'), None)
        brief = request.brief or c.CreativeBriefInput()
        width, height = map(int, brief.aspect_ratio.split(':'))
        if (video is None or video.spec.width is None or video.spec.height is None
                or video.spec.width * height != video.spec.height * width):
            raise EngineError('production_publication_aspect_conflict', 'Actual verified final dimensions must preserve the original declared aspect', 422)
        if isinstance(request, c.ProductionRequestV03) and request.delivery_requirements.alignment_evidence_policy not in record.policy.alignment_modes:
            raise EngineError('production_publication_evidence_denied', 'Current policy does not authorize this exact original alignment mode', 403)
        if not isinstance(request, c.ProductionRequestV03) and 'strict_reference_v1' not in record.policy.alignment_modes:
            raise EngineError('production_publication_evidence_denied', 'Old strict evidence cannot silently acquire a qualified/degraded path', 403)
        publication_scope.service.assert_local_current(connection, guard, lease, production,
                                                       final_context.production_authorization_refs)
        # Existing quality/media/evidence validation produced this opaque token;
        # the service rechecks original all-success/settled operations and rights
        # in this same writer. A policy is never a replacement for those checks.
        return self._persist(connection, guard, production, run, request, record, phase='quality', action='finalize_bundle',
            target_kind='final_manifest', target_id=manifest.bundle_revision_id,
            target_sha256=publication_scope.verified.manifest_sha256, fence=lease.fencing_token)

    def assert_blocker_resume_current(self, connection, guard, *, run_id, binding, blocker_sha256):
        """No-lease queue qualification under the original live issuer guard."""
        from video_creator.application.current_production_blockers import PREFIX, bound_context, parse_journal
        from video_creator.application.production_reauthorization import WAIT_PREFIX

        registered, _revision = self._guard(connection, guard)
        run, production, request, actual = bound_context(self.engine, connection, run_id, registered.registration_sha256)
        row = connection.execute('SELECT value FROM metadata WHERE key=?', (PREFIX + run_id,)).fetchone()
        if row is None or type(row[0]) is not str or digest(row[0]) != blocker_sha256:
            raise EngineError('production_blocker_changed', 'Original blocker compare-and-swap identity changed', 409)
        journal = parse_journal(row[0], now=self.engine.clock())
        if actual != binding or journal.binding != actual:
            raise EngineError('production_blocker_binding_invalid', 'Original complete blocker and execution binding differ', 422)
        self._request(connection, production, run, registered)
        if connection.execute('SELECT 1 FROM metadata WHERE key=?', (WAIT_PREFIX + run_id,)).fetchone():
            raise EngineError('production_reauthorization_required', 'Original explicit Owner reauthorization wait remains', 403)
        if request.automation.mode == 'unattended':
            _request, record = self._bound(connection, guard, production, run, action='begin_execution')
            for phase, action in (('plan', 'execute_plan'), ('quality', 'continue_bundle_validation')):
                rows = connection.execute('SELECT * FROM creative_revisions WHERE production_id=? AND run_id=? AND kind=?',
                    (production['id'], run_id, phase)).fetchall()
                if rows:
                    self._bound(connection, guard, production, run, action=action)
                for row in rows:
                    revision, _sha = self._creative(connection, production, run, row['id'], phase)
                    if phase == 'plan' and (not isinstance(revision.body, dict)
                            or plan_rights_body(revision.body) != [right.model_dump(mode='json') for right in record.policy.rights]):
                        raise EngineError('production_rights_conflict', 'Historical committed plan differs from the actual original policy declaration', 403)
        else:
            if journal.result.state != 'resource_not_ready':
                raise EngineError('production_review_required', 'Interactive authorization wait needs original human review', 403)
            if any((source.system, source.namespace) not in registered.allowed_source_namespaces for source in request.source_bindings):
                raise EngineError('production_execution_scope_denied', 'Original interactive sources exceed actual namespace scope', 403)
            rows = connection.execute('SELECT * FROM decisions WHERE run_id=?', (run_id,)).fetchall()
            for row in rows:
                if digest(row['body']) != row['request_sha256'] or row['result_json'] != row['body']:
                    raise EngineError('production_review_invalid', 'Original immutable human decision is damaged', 422)
                decision = self.management_service._model(c.ReviewDecision, row['body'])
                target = connection.execute('SELECT * FROM creative_revisions WHERE id=? AND production_id=? AND run_id=?',
                    (decision.target_revision_id, production['id'], run_id)).fetchone()
                if target is None or digest(target['body']) != target['content_sha256']:
                    raise EngineError('production_review_invalid', 'Original decision target is unavailable or damaged', 422)
        # Same original scope, immediately before the caller's queue writer.
        self._guard(connection, guard)

    def assert_final_evidence_resume_current(self, connection, guard, *, run_id, binding,
            journal_sha256, resume_mode, affected_artifact_ids):
        """Current original issuer/scope; checkpoint is progress, never admission."""
        from video_creator.application.current_final_evidence_journal import PREFIX, parse_journal, prepared_current, reject_conflicting_wait

        registered, _revision = self._guard(connection, guard)
        saved = connection.execute('SELECT value FROM metadata WHERE key=?', (PREFIX + run_id,)).fetchone()
        if saved is None or type(saved[0]) is not str or digest(saved[0]) != journal_sha256:
            raise EngineError('final_evidence_checkpoint_changed', 'Original checkpoint CAS changed', 409)
        journal = parse_journal(saved[0], now=self.engine.clock())
        _prepared, run, production, request = prepared_current(self.engine, connection, journal)
        if binding != journal.binding or registered.registration_sha256 != binding.registration_sha256:
            raise EngineError('final_evidence_binding_invalid', 'Actual current registration/binding differs', 409)
        reject_conflicting_wait(connection, run_id)
        self._request(connection, production, run, registered)
        if resume_mode not in {'retry_final_validation', 'repair'}:
            raise EngineError('final_evidence_resume_invalid', 'Original finite resume mode required', 422)
        if resume_mode == 'repair':
            repair = journal.snapshot.repair
            if (repair is None or repair.allowed_action == 'guidance_required'
                    or tuple(affected_artifact_ids) != repair.affected_artifact_ids
                    or production['revision_cycles'] >= request.automation.max_revision_cycles):
                raise EngineError('final_evidence_guidance_required', 'Original limited repair scope unavailable', 403)
        elif affected_artifact_ids:
            raise EngineError('final_evidence_resume_invalid', 'Validation retry cannot add media repair scope', 422)
        if request.automation.mode == 'unattended':
            self._bound(connection, guard, production, run, action='begin_execution')
            self._bound(connection, guard, production, run, action='execute_plan')
            self._bound(connection, guard, production, run, action='continue_bundle_validation')
            self._bound(connection, guard, production, run, action='finalize_bundle')
        else:
            if any((s.system, s.namespace) not in registered.allowed_source_namespaces for s in request.source_bindings):
                raise EngineError('production_execution_scope_denied', 'Original source namespace scope required', 403)
            for phase in ('plan', 'quality'):
                target = connection.execute('SELECT id,body,content_sha256 FROM creative_revisions WHERE production_id=? AND run_id=? AND kind=? ORDER BY rowid DESC LIMIT 1',
                    (production['id'], run_id, phase)).fetchone()
                if target is None or digest(target['body']) != target['content_sha256']:
                    raise EngineError('production_review_required', 'Actual approved original plan/quality required', 403)
                approved = False
                for decision in connection.execute('SELECT * FROM decisions WHERE run_id=?', (run_id,)).fetchall():
                    if digest(decision['body']) != decision['request_sha256'] or decision['body'] != decision['result_json']:
                        raise EngineError('production_review_invalid', 'Original immutable approval is damaged', 422)
                    value = self.management_service._model(c.ReviewDecision, decision['body'])
                    approved |= value.target_revision_id == target['id'] and value.action == 'approve'
                if not approved:
                    raise EngineError('production_review_required', 'Original genuine human approval required', 403)
        self._guard(connection, guard)

    def execution_ports(self, registered):
        """Host binds the actual caller once; model/Media never supplies it."""
        with self._lock:
            self._identity(registered)
            return PolicyExecutionPorts(self, registered)


@dataclass(frozen=True, repr=False)
class PolicyExecutionPorts:
    issuer: ProductionAdmissions = field(repr=False)
    registered: RegisteredExecutionIdentity = field(repr=False)

    def begin_execution(self, ordinary_lease):
        return self.issuer.begin_execution(self.registered, ordinary_lease)

    def rights_proposal(self, ordinary_lease):
        return self.issuer.rights_proposal(self.registered, ordinary_lease)

    def local_material_plan_sources(self, ordinary_lease, *, script_revision_id,
                                    source_script_origin, selected_route_ids):
        self.issuer.rights_proposal(self.registered, ordinary_lease)
        from video_creator.application.local_material_sources import LocalMaterialSourceService
        source = getattr(self.issuer.engine, '_local_material_plan_source', None)
        if type(source) is not LocalMaterialSourceService or source.engine is not self.issuer.engine or source.runtime.sha256 != self.registered.registration_sha256:
            raise EngineError('local_material_source_unconfigured', 'Actual same Engine local source service required.', 503)
        return source.read(ordinary_lease, script_revision_id=script_revision_id,
            source_script_origin=source_script_origin, selected_route_ids=selected_route_ids)[0]

    def local_material_final_context(self, ordinary_lease):
        self.issuer.rights_proposal(self.registered, ordinary_lease)
        from video_creator.application.local_material_sources import LocalMaterialSourceService
        source = getattr(self.issuer.engine, '_local_material_plan_source', None)
        if type(source) is not LocalMaterialSourceService or source.runtime.sha256 != self.registered.registration_sha256:
            raise EngineError('local_material_source_unconfigured', 'Actual original local source service required.', 503)
        return source.final_context(ordinary_lease, self, policy=True)

    def local_master_selection(self, ordinary_lease, *, plan_revision_id):
        self.issuer.rights_proposal(self.registered, ordinary_lease)
        from video_creator.application.local_material_sources import LocalMaterialSourceService
        source = getattr(self.issuer.engine, '_local_material_plan_source', None)
        if (type(source) is not LocalMaterialSourceService or source.engine is not self.issuer.engine
                or source.runtime.sha256 != self.registered.registration_sha256):
            raise EngineError('local_material_source_unconfigured', 'Actual same Engine local source is required.', 503)
        return source.master_selection(ordinary_lease, self, policy=True, plan_revision_id=plan_revision_id)

    def production_admission(self, ordinary_lease, revision_id, *, phase, action):
        return self.issuer.production_admission(self.registered, ordinary_lease, revision_id, phase=phase, action=action)

    def production_rights(self, ordinary_lease, plan_revision_id):
        return self.issuer.production_rights(self.registered, ordinary_lease, plan_revision_id)

    def authorization_document(self, ordinary_lease, plan_admission_ref):
        return self.issuer.authorization_document(self.registered, ordinary_lease, plan_admission_ref)


def canonical_dict(value):
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    except (ValueError, TypeError):
        raise EngineError('production_authorization_invalid', 'Stored action payload is not strict canonical JSON', 422) from None
