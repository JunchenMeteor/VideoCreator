"""Gate0 execution authority, separate from framework checkpoints."""

import hashlib
import json
import time
import uuid
from collections.abc import Callable
from contextlib import ExitStack, contextmanager
from pathlib import Path

from pydantic import BaseModel, ValidationError

from video_creator.application.pricing import normalize_observation
from video_creator.domain.contracts import (
    SCHEMA_VERSION,
    BundleRef,
    CapabilityRoute,
    CreativeRevision,
    DeliveryRequirements,
    DeliveryRequirementsV03,
    EventEnvelope,
    ExecutionPermit,
    FeedbackRevision,
    LeaseGrant,
    Money,
    OperationIntent,
    OperationObservation,
    ProductionAccepted,
    ProductionDetail,
    ProductionRequest,
    ProductionRequestAny,
    ProductionRequestV03,
    ProjectDraft,
    ProjectInput,
    ReviewDecision,
    parse_production_request,
    reject_secrets,
)
from video_creator.domain.errors import EngineError
from video_creator.infrastructure.database import Database

# The complete declared output role set, and the subset that needs real speech
# evidence (transcript/alignment/subtitles). Both are contract constants, never
# request-controlled.
_OUTPUT_ROLES = frozenset({"video", "narration_audio", "mixed_audio", "approved_script",
                           "actual_transcript", "subtitles", "semantic_manifest", "rag_chunks"})
_SPEECH_OUTPUT_ROLES = frozenset({"narration_audio", "mixed_audio", "actual_transcript", "subtitles"})


def identity(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


def canonical(model: BaseModel) -> str:
    return json.dumps(model.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class EngineService:
    def __init__(self, data_dir: str | Path, clock: Callable[[], int] | None = None):
        self.db = Database(Path(data_dir))
        self.clock = clock or (lambda: time.time_ns() // 1000)
        with self.db.transaction() as connection:
            connection.execute("INSERT OR IGNORE INTO metadata VALUES ('instance_id',?)", (identity("instance"),))
            self.instance_id = connection.execute("SELECT value FROM metadata WHERE key='instance_id'").fetchone()[0]
        from video_creator.application.evidence import PersistentEvidenceRegistry
        self.evidence_registry = PersistentEvidenceRegistry(self)
        self.production_admissions = None
        self._production_execution_identities = {}
        self.local_copy_inputs = None
        self.daily_projects = None

    def configure_daily_projects(self, service):
        from video_creator.application.daily_projects import DailyProjectService

        if (type(service) is not DailyProjectService or service.engine is not self
                or service.issuer is not self.production_admissions
                or self.daily_projects is not None and self.daily_projects is not service):
            raise EngineError('daily_project_configuration_conflict', 'Daily project service must be the original same Engine/issuer', 503)
        self.daily_projects = service

    def create_project_goal(self, subject, idempotency_key, goal, *, entry):
        if self.daily_projects is None:
            raise EngineError('daily_project_authorization_unconfigured', 'Actual installed creation delegation is required', 503)
        return self.daily_projects.accept(subject, idempotency_key, goal, entry=entry)

    def configure_local_copy_inputs(self, service):
        """Trusted host wiring only; installs neither a scope nor Owner authentication."""
        from video_creator.application.local_copy_input_service import (
            LocalCopyInputService,
        )
        if type(service) is not LocalCopyInputService or service.engine is not self:
            raise EngineError('local_copy_configuration_conflict', 'Copy service must be the exact local concrete Engine service', 503)
        if self.local_copy_inputs is not None and self.local_copy_inputs is not service:
            raise EngineError('local_copy_configuration_conflict', 'Live copy registry cannot be silently replaced', 503)
        self.local_copy_inputs = service

    def configure_evidence_registry(self, registry):
        """Trusted startup only: root the evidence registry with the OS-vault key.

        The registry still carries no execution or Owner capability. A request,
        task payload or model output never reaches this method; only the trusted
        host startup and the one-shot local evidence administrator call it.
        """
        from video_creator.application.evidence import PersistentEvidenceRegistry

        if type(registry) is not PersistentEvidenceRegistry or registry.engine is not self:
            raise EngineError('evidence_configuration_invalid',
                              'Evidence registry must be the exact same-instance implementation', 503)
        self.evidence_registry = registry

    def configure_production_authorization(self, issuer, *, subject_identities):
        """Trusted authenticated host startup, never a task or management action.

        Existing protected endpoints pass their real owner subject. This finite
        map binds that subject to one already registered identity; no payload
        may select a principal, policy or installation. It does not install a
        concrete resource authority or grant administration to ordinary callers.
        """
        from video_creator.application.production_admissions import ProductionAdmissions
        if not isinstance(issuer, ProductionAdmissions) or issuer.engine is not self:
            raise EngineError('production_authorization_configuration_conflict', 'Execution issuer must belong to this exact engine instance', 503)
        bindings = dict(subject_identities)
        if not bindings:
            raise EngineError('production_authorization_configuration_conflict', 'Actual authenticated execution subject bindings are required', 503)
        with issuer._lock:
            for subject, registered in bindings.items():
                issuer._identity(registered)
                if subject != registered.owner_subject:
                    raise EngineError('production_authorization_configuration_conflict', 'Existing protected subject must own its exact registered project scope', 503)
        if self.production_admissions is not None:
            if self.production_admissions is issuer and self._production_execution_identities == bindings:
                return
            raise EngineError('production_authorization_configuration_conflict', 'Live execution registration cannot be silently replaced', 503)
        self.production_admissions, self._production_execution_identities = issuer, bindings

    def _authorization_identity(self, subject):
        if self.production_admissions is None:
            raise EngineError('production_authorization_unconfigured', 'Actual Owner policy execution is not configured', 403)
        registered = self._production_execution_identities.get(subject)
        if registered is None:
            raise EngineError('production_execution_identity_denied', 'This actual authenticated subject has no registered execution scope', 403)
        return registered

    def _suspend_operation_authorization(self, lease, error):
        from video_creator.application.production_reauthorization import (
            suspend_authorization,
        )
        with self.db.transaction() as connection:
            try:
                run = self._lease(connection, lease)
            except EngineError as current_error:
                if current_error.code in {'stale_lease', 'run_cancelled'}:
                    return
                raise
            production = self._production(connection, run['production_id'])
            suspend_authorization(self, connection, run, production, blocker_code=error.code,
                                  target_id=production['request_revision_id'], fence=lease.fencing_token)

    @contextmanager
    def _operation_authorization_context(self, lease, *, affected_step_key=None):
        """Long current resource validation precedes an original short writer."""
        from video_creator.application.production_reauthorization import (
            AUTHORIZATION_WAIT_CODES,
        )
        if affected_step_key is not None and affected_step_key.startswith(('repair-alignment-', 'bundle-alignment-')):
            source = getattr(self, '_registered_plan_source', None)
            if source is None:
                raise EngineError('alignment_step_denied', 'Actual same-Engine installed alignment source required', 403)
            source.preflight_registered_alignment_step(lease, affected_step_key)
        with self.db.connect() as connection:
            run = self._lease(connection, lease)
            production = self._production(connection, run['production_id'])
            request = parse_production_request(production['request_json'])
        if request.automation.mode != 'unattended':
            if affected_step_key is not None and affected_step_key.startswith(('repair-narration-', 'repair-picture-', 'repair-edit-', 'repair-master-', 'repair-asr-', 'repair-alignment-', 'bundle-alignment-')):
                source = getattr(self, '_registered_plan_source', None)
                if source is None:
                    raise EngineError('affected_step_denied', 'Actual original installed repair source required', 403)
                with source.plan_commit_guard(lease) as guard:
                    yield guard
                return
            yield None
            return
        try:
            registered = self._authorization_identity(production['owner'])
            with self.production_admissions.current_guard(registered) as guard:
                yield guard
        except EngineError as error:
            if error.code in AUTHORIZATION_WAIT_CODES:
                # The original writer has rolled back before this context exit.
                # Preserve all provider/unknown evidence and original reserves.
                self._suspend_operation_authorization(lease, error)
            raise

    def _event(self, connection, run, event_type: str, revision: str | None = None):
        connection.execute(
            "INSERT INTO events(id,production_id,run_id,event_type,status,occurred_at_us,entity_revision_id) VALUES(?,?,?,?,?,?,?)",
            (identity("event"), run["production_id"], run["id"], event_type, run["status"], self.clock(), revision),
        )

    def _run(self, connection, run_id: str):
        run = connection.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        if run is None:
            raise EngineError("not_found", "Run not found", 404)
        return run

    def _production(self, connection, production_id: str, subject: str | None = None):
        production = connection.execute("SELECT * FROM productions WHERE id=?", (production_id,)).fetchone()
        if production is None or (subject is not None and production["owner"] != subject):
            raise EngineError("not_found", "Production not found", 404)
        return production

    def _lease(self, connection, lease: LeaseGrant, allow_cancel: bool = False):
        run = self._run(connection, lease.run_id)
        allowed = {"running", "waiting_provider"}
        if allow_cancel:
            allowed.update({"cancel_requested", "needs_reconciliation"})
        if (run["worker_id"] != lease.worker_id or run["fencing_token"] != lease.fencing_token
                or run["lease_until_us"] <= self.clock() or run["status"] not in allowed):
            raise EngineError("stale_lease", "Lease expired or was superseded")
        if run["cancellation_requested"] and not allow_cancel:
            raise EngineError("run_cancelled", "Production is cancelled; only reconciliation is allowed")
        return run

    def authorize_budget_group(self, group_id: str, cap: Money, subject: str = "local-user"):
        """Trusted instance configuration only. Existing authorization cannot silently reset."""
        with self.db.transaction() as connection:
            row = connection.execute("SELECT * FROM budget_groups WHERE id=?", (group_id,)).fetchone()
            if row is not None:
                if row["cap_units"] != cap.units() or row["currency"] != cap.currency or row["owner"] != subject:
                    raise EngineError("budget_authorization_conflict", "Existing shared authorization is immutable")
                return
            connection.execute("INSERT INTO budget_groups(id,owner,currency,cap_units) VALUES(?,?,?,?)", (group_id, subject, cap.currency, cap.units()))

    def register_route(self, route: CapabilityRoute):
        """Trusted configuration, never a model-generated permission grant."""
        if not route.verified:
            raise EngineError("capability_unverified", "Route must have an actual capability configuration", 400)
        if route.source == "official":
            raise EngineError("official_unavailable", "Official account service is not implemented in Gate0", 503)
        with self.db.transaction() as connection:
            connection.execute("INSERT INTO routes(id,body) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body", (route.route_id, canonical(route)))

    def configured_route(self, route_id: str) -> CapabilityRoute:
        with self.db.connect() as connection:
            row = connection.execute("SELECT body FROM routes WHERE id=?", (route_id,)).fetchone()
            if row is None:
                raise EngineError("route_unavailable", "Provider route is not configured", 503)
            return CapabilityRoute.model_validate_json(row[0])

    def create_project(self, subject: str, project: ProjectInput, idempotency_key: str | None = None) -> ProjectDraft:
        return self._create_project(subject, project, idempotency_key)

    def _create_project_for_setup(self, subject, project, idempotency_key, *, initialization_source):
        from video_creator.infrastructure.native_instance_source import (
            _NativeInstanceSource,
        )

        if type(initialization_source) is not _NativeInstanceSource:
            raise EngineError('owner_instance_source_denied', 'Original concrete setup source is required', 403)
        initialization_source.assert_setup_engine_current(self)
        return self._create_project(subject, project, idempotency_key, initialization_source=initialization_source)

    def _create_project(self, subject, project, idempotency_key, *, initialization_source=None):
        if initialization_source is not None:
            from video_creator.infrastructure.native_instance_source import (
                _NativeInstanceSource,
            )

            if type(initialization_source) is not _NativeInstanceSource:
                raise EngineError('owner_instance_source_denied', 'Original concrete setup source is required', 403)
        if idempotency_key is not None and (not idempotency_key or len(idempotency_key) > 128):
            raise EngineError("invalid_idempotency_key", "A bounded nonempty idempotency key is required", 400)
        body = canonical(project)
        project_id = identity("project")
        saved = self.clock()
        with self.db.transaction() as connection:
            if initialization_source is not None:
                initialization_source.assert_setup_engine_local_current(self, connection)
            if idempotency_key:
                existing = connection.execute("SELECT * FROM commands WHERE owner=? AND scope='project.create' AND idempotency_key=?", (subject, idempotency_key)).fetchone()
                if existing:
                    if existing["request_sha256"] != digest(body):
                        raise EngineError("idempotency_conflict", "Project key was used with different input")
                    if initialization_source is not None:
                        initialization_source.assert_setup_engine_local_current(self, connection)
                    return ProjectDraft.model_validate_json(existing["result_json"])
            connection.execute("INSERT INTO projects(id,owner,body,saved_at_us) VALUES(?,?,?,?)", (project_id, subject, body, saved))
            result = ProjectDraft(**project.model_dump(), project_id=project_id, revision=1, saved_at_us=saved)
            if idempotency_key:
                connection.execute("INSERT INTO commands VALUES(?,'project.create',?,?,?)", (subject, idempotency_key, digest(body), canonical(result)))
            if initialization_source is not None:
                initialization_source.assert_setup_engine_local_current(self, connection)
            return result

    def get_project(self, subject: str, project_id: str) -> ProjectDraft:
        with self.db.connect() as connection:
            row = connection.execute("SELECT * FROM projects WHERE id=? AND owner=?", (project_id, subject)).fetchone()
            if row is None:
                raise EngineError("not_found", "Project not found", 404)
            return ProjectDraft(**json.loads(row["body"]), project_id=row["id"], revision=row["revision"], saved_at_us=row["saved_at_us"])

    def list_projects(self, subject: str) -> list[ProjectDraft]:
        with self.db.connect() as connection:
            rows = connection.execute("SELECT * FROM projects WHERE owner=? ORDER BY saved_at_us DESC LIMIT 100", (subject,)).fetchall()
            return [ProjectDraft(**json.loads(row["body"]), project_id=row["id"], revision=row["revision"], saved_at_us=row["saved_at_us"]) for row in rows]

    def update_project(self, subject: str, project_id: str, expected_revision: int, project: ProjectInput) -> ProjectDraft:
        with self.db.transaction() as connection:
            row = connection.execute("SELECT * FROM projects WHERE id=? AND owner=?", (project_id, subject)).fetchone()
            if row is None:
                raise EngineError("not_found", "Project not found", 404)
            if row["revision"] != expected_revision:
                raise EngineError("revision_conflict", "Draft has a newer saved revision")
            saved, revision = self.clock(), expected_revision + 1
            connection.execute("UPDATE projects SET body=?,revision=?,saved_at_us=? WHERE id=?", (canonical(project), revision, saved, project_id))
            return ProjectDraft(**project.model_dump(), project_id=project_id, revision=revision, saved_at_us=saved)

    def accept_production(self, subject: str, idempotency_key: str, request: ProductionRequestAny) -> ProductionAccepted:
        if not subject or not idempotency_key or len(idempotency_key) > 128:
            raise EngineError("invalid_identity", "Subject and a bounded idempotency key are required", 400)
        # Observing a prior idempotent acceptance never acquires new execution
        # permission or resolves a later default policy/resource configuration.
        with self.db.connect() as connection:
            # Production, receipt and original event must share one read
            # snapshot when another first acceptance commits concurrently.
            connection.execute("BEGIN")
            repeated = self._original_acceptance(connection, subject, idempotency_key, request)
            if repeated is not None:
                return repeated
        from video_creator.application.production_reauthorization import (
            AUTHORIZATION_WAIT_CODES,
        )
        with ExitStack() as stack:
            guard, authorization_error = None, None
            if request.automation.mode == 'unattended':
                try:
                    registered = self._authorization_identity(subject)
                    guard = stack.enter_context(self.production_admissions.current_guard(registered))
                    if self.local_copy_inputs is not None:
                        stack.enter_context(self.local_copy_inputs.current_guard())
                except EngineError as error:
                    if error.code not in AUTHORIZATION_WAIT_CODES:
                        raise
                    authorization_error = error
            return self._accept_production_writer(subject, idempotency_key, request,
                                                  authorization_guard=guard, authorization_error=authorization_error)

    def _original_acceptance(self, connection, subject, idempotency_key, request):
        existing = connection.execute("SELECT * FROM productions WHERE owner=? AND idempotency_key=?", (subject, idempotency_key)).fetchone()
        journal = connection.execute("SELECT request_sha256,result_json FROM commands WHERE owner=? AND scope='production.accept' AND idempotency_key=?", (subject, idempotency_key)).fetchone()
        if existing is None:
            if journal is not None:
                raise EngineError("acceptance_record_invalid", "Original acceptance has no matching production", 422)
            return None
        if journal is not None:
            recorded_hash = journal["request_sha256"]
            if not isinstance(recorded_hash, str) or len(recorded_hash) != 64 or any(char not in "0123456789abcdef" for char in recorded_hash):
                raise EngineError("acceptance_record_invalid", "Original acceptance input identity is malformed", 422)
            if journal["request_sha256"] != digest(canonical(request)):
                raise EngineError("idempotency_conflict", "The same key was used with different original input")
            return self._acceptance_receipt(connection, existing, journal["result_json"])
        original = parse_production_request(existing["request_json"])
        if isinstance(original, ProductionRequestV03):
            if not isinstance(request, ProductionRequestV03):
                raise EngineError("idempotency_conflict", "Existing key belongs to a different original request version")
            candidate = request.model_copy(update={"delivery_requirements": request.delivery_requirements or original.delivery_requirements})
        else:
            if isinstance(request, ProductionRequestV03):
                raise EngineError("idempotency_conflict", "Existing key belongs to a different original request version")
            candidate = request if original.request_format_version is None else request.model_copy(update={
                "request_format_version": original.request_format_version,
                "delivery_requirements": request.delivery_requirements or original.delivery_requirements,
            })
        if existing["request_sha256"] != digest(canonical(candidate)):
            raise EngineError("idempotency_conflict", "The same key was used with different input")
        # Historical rows have no immutable returned-status snapshot. Anchor
        # their identity to the original event, never to a later feedback Run.
        return self._accepted(connection, existing, run=self._acceptance_run(connection, existing))

    def _acceptance_run(self, connection, production):
        events = connection.execute("SELECT run_id,entity_revision_id FROM events WHERE production_id=? AND event_type='production.accepted'", (production["id"],)).fetchall()
        if len(events) != 1 or events[0]["entity_revision_id"] != production["request_revision_id"]:
            raise EngineError("acceptance_record_invalid", "Original acceptance event is missing or inconsistent", 422)
        run = connection.execute("SELECT * FROM runs WHERE id=? AND production_id=?", (events[0]["run_id"], production["id"])).fetchone()
        if run is None:
            raise EngineError("acceptance_record_invalid", "Original acceptance Run is unavailable", 422)
        return run

    def _acceptance_receipt(self, connection, production, serialized):
        if not isinstance(serialized, str):
            raise EngineError("acceptance_record_invalid", "Original acceptance receipt is malformed", 422)
        try:
            receipt = ProductionAccepted.model_validate_json(serialized)
        except (ValueError, ValidationError):
            raise EngineError("acceptance_record_invalid", "Original acceptance receipt is malformed", 422) from None
        original = self._accepted(connection, production, run=self._acceptance_run(connection, production))
        expected = original.model_dump(mode="json")
        actual = receipt.model_dump(mode="json")
        # Status belongs to the immutable acceptance snapshot. Reading it does
        # not claim that the original Run is still queued or may run again.
        expected.pop("status")
        actual.pop("status")
        if actual != expected or canonical(receipt) != serialized:
            raise EngineError("acceptance_record_invalid", "Original acceptance receipt has inconsistent identity", 422)
        return receipt

    def _accept_production_writer(self, subject, idempotency_key, request, *, authorization_guard, authorization_error):
        with self.db.transaction() as connection:
            return self._accept_production_connection(connection, subject, idempotency_key, request,
                authorization_guard=authorization_guard, authorization_error=authorization_error)

    def _accept_production_connection(self, connection, subject, idempotency_key, request, *,
                                      authorization_guard, authorization_error, planned_ids=None, daily_context=None):
        """Original writer core; trusted Goal creation shares this exact transaction."""
        original_input_sha256 = digest(canonical(request))
        repeated = self._original_acceptance(connection, subject, idempotency_key, request)
        if repeated is not None:
            return repeated
        blocker_code = None
        if isinstance(request, ProductionRequestV03):
            if self._local_skips_evidence_policy(request) and request.delivery_requirements is None:
                # A local instance with no speech output has nothing to align;
                # the local producer still validates real applicable facts.
                pass
            else:
                try:
                    request = self._resolve_v03_request(connection, subject, request)
                except EngineError as error:
                    if error.code not in {"alignment_required", "evidence_authority_unconfigured", "evidence_admission_inactive", "evidence_restore_refresh_required"}:
                        raise
                    blocker_code = "alignment_required"
        else:
            request = self._resolve_request(request)
        body, request_hash = canonical(request), digest(canonical(request))
        project_id = request.project_id or identity("project")
        if request.project_id:
            project = connection.execute("SELECT * FROM projects WHERE id=? AND owner=?", (project_id, subject)).fetchone()
            if project is None:
                raise EngineError("not_found", "Project not found", 404)
        else:
            project = ProjectInput(goal=request.goal, source_text=request.inputs.source_text)
            connection.execute("INSERT INTO projects(id,owner,body,saved_at_us) VALUES(?,?,?,?)", (project_id, subject, canonical(project), self.clock()))
        for asset_id in request.inputs.asset_ids:
            if connection.execute("SELECT id FROM assets WHERE id=? AND owner=?", (asset_id, subject)).fetchone() is None:
                raise EngineError("input_asset_denied", "Input asset is unavailable to this subject", 403)
        group_id = request.policy.budget_group_id
        if group_id and connection.execute("SELECT id FROM budget_groups WHERE id=? AND owner=?", (group_id, subject)).fetchone() is None:
            raise EngineError("budget_unauthorized", "Shared budget authorization is not configured", 403)
        production_id, run_id, revision_id = planned_ids or (identity("production"), identity("run"), identity("request"))
        connection.execute(
            "INSERT INTO productions(id,project_id,owner,idempotency_key,request_sha256,request_revision_id,request_json,status,budget_group_id,cap_units,created_at_us) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (production_id, project_id, subject, idempotency_key, request_hash, revision_id, body, "queued", group_id, request.policy.max_cost.units(), self.clock()),
        )
        connection.execute("INSERT INTO runs(id,production_id,status) VALUES(?,?,'queued')", (run_id, production_id))
        self._event(connection, self._run(connection, run_id), "production.accepted", revision_id)
        if daily_context is not None:
            self.daily_projects.commit_child(connection, daily_context, self._production(connection, production_id), self._run(connection, run_id))
        if request.automation.mode == 'unattended' and authorization_guard is not None:
            from video_creator.application.production_reauthorization import (
                AUTHORIZATION_WAIT_CODES,
            )
            try:
                policy_binding = self.production_admissions.bind_request(connection, authorization_guard,
                    self._production(connection, production_id), self._run(connection, run_id))
                if self.local_copy_inputs is not None and policy_binding is not None:
                    registered, _registry_revision = self.production_admissions._guard(connection, authorization_guard)
                    self.local_copy_inputs.bind_default_request(connection,
                        production=self._production(connection, production_id), run=self._run(connection, run_id),
                        registered=registered, policy_ref=policy_binding.policy_ref)
            except EngineError as error:
                if error.code not in AUTHORIZATION_WAIT_CODES:
                    raise
                authorization_error = error
        if not self._full_output_profile(request) or blocker_code:
            blocker_code = blocker_code or "output_profile_unavailable"
            blocker = CreativeRevision(revision_id=identity("quality"), kind="quality", body={"code": blocker_code, "requested_outputs": list(request.outputs)})
            serialized = canonical(blocker)
            connection.execute("INSERT INTO creative_revisions VALUES(?,?,?,?,?,?)", (blocker.revision_id, production_id, run_id, "quality", serialized, digest(serialized)))
            connection.execute("UPDATE runs SET status='waiting_user',waiting_revision_id=? WHERE id=?", (blocker.revision_id, run_id))
            connection.execute("UPDATE productions SET status='waiting_user' WHERE id=?", (production_id,))
            self._event(connection, self._run(connection, run_id), blocker_code, blocker.revision_id)
        elif authorization_error is not None:
            from video_creator.application.production_reauthorization import (
                suspend_authorization,
            )
            suspend_authorization(self, connection, self._run(connection, run_id), self._production(connection, production_id),
                                  blocker_code=authorization_error.code, target_id=revision_id)
        accepted = self._accepted(connection, self._production(connection, production_id))
        connection.execute("INSERT INTO commands(owner,scope,idempotency_key,request_sha256,result_json) VALUES(?,'production.accept',?,?,?)",
                           (subject, idempotency_key, original_input_sha256, canonical(accepted)))
        return accepted

    @staticmethod
    def _resolve_request(request: ProductionRequest) -> ProductionRequest:
        # Only new identities resolve defaults. Persisted legacy bodies/hashes are immutable.
        return request.model_copy(update={"request_format_version": SCHEMA_VERSION,
                                          "delivery_requirements": request.delivery_requirements or DeliveryRequirements()})

    def _local_material_profile(self) -> bool:
        """Whether this instance is configured for local material production.

        The worker side is marked by the real installed local source service.
        The development API role deliberately never builds a second
        `RegisteredMediaRuntime` (ADR0077 section 8.5), so its development
        authority records the parsed real local-v1 registration instead.
        Production never sets either signal.
        """
        return (getattr(self, "_local_material_plan_source", None) is not None
                or getattr(self, "_development_local_registration", None) is not None
                or getattr(self, "_local_material_registration", None) is not None)

    def _local_skips_evidence_policy(self, request: ProductionRequest) -> bool:
        """Local requests without any speech output have no evidence to resolve."""
        return (self._local_material_profile()
                and not (set(request.outputs) & _SPEECH_OUTPUT_ROLES))

    def _full_output_profile(self, request: ProductionRequest) -> bool:
        if self._local_material_profile():
            # Local production consumes the actually applicable subset; empty,
            # duplicate or undeclared roles remain structurally impossible and
            # the local producer still refuses inapplicable outputs by name.
            outputs = tuple(request.outputs)
            return (bool(outputs) and len(set(outputs)) == len(outputs)
                    and set(outputs) <= _OUTPUT_ROLES)
        return set(request.outputs) == _OUTPUT_ROLES

    def _resolve_v03_request(self, connection, subject, request):
        ref = request.delivery_requirements.evidence_policy_revision_ref if request.delivery_requirements else None
        resolved = self.evidence_registry.resolve(subject, request.project_id, ref, connection=connection)
        requirements = DeliveryRequirementsV03(alignment_requirement=resolved.policy.alignment_requirement,
            alignment_evidence_policy=resolved.policy.alignment_evidence_policy, evidence_policy_revision_ref=resolved.policy_ref)
        if request.delivery_requirements is not None and request.delivery_requirements != requirements:
            raise EngineError("evidence_policy_conflict", "Request differs from its exact preauthorized policy", 409)
        return request.model_copy(update={"delivery_requirements": requirements})

    def _evidence_execution_guard(self, connection, production, request):
        if isinstance(request, ProductionRequestV03):
            if self._local_skips_evidence_policy(request) and request.delivery_requirements is None:
                return
            if not request.delivery_requirements:
                raise EngineError("alignment_required", "Request has no resolved trusted evidence policy", 409)
            self.evidence_registry.resolve(production["owner"], production["project_id"], request.delivery_requirements.evidence_policy_revision_ref, connection=connection)

    def _accepted(self, connection, production, *, run=None) -> ProductionAccepted:
        if run is None:
            run = connection.execute("SELECT * FROM runs WHERE production_id=? ORDER BY rowid DESC LIMIT 1", (production["id"],)).fetchone()
        version = parse_production_request(production["request_json"]).request_format_version or SCHEMA_VERSION
        return ProductionAccepted(schema_version=version, instance_id=self.instance_id, production_id=production["id"], run_id=run["id"], project_id=production["project_id"], request_revision_id=production["request_revision_id"], status=run["status"], status_path=f"/api/v1/productions/{production['id']}", events_path=f"/api/v1/runs/{run['id']}/events")

    def get_production(self, subject: str, production_id: str) -> ProductionDetail:
        with self.db.connect() as connection:
            production = self._production(connection, production_id, subject)
            accepted = self._accepted(connection, production)
            operations = connection.execute("SELECT id,status,actual_units,cost_evidence,external_id FROM operations WHERE production_id=? ORDER BY rowid", (production_id,)).fetchall()
            bundle = connection.execute("SELECT bundle_id,revision_id,manifest_sha256 FROM bundle_revisions WHERE production_id=? AND status='published' ORDER BY rowid DESC LIMIT 1", (production_id,)).fetchone()
            return ProductionDetail.model_validate({
                **accepted.model_dump(mode="json"),
                "request": json.loads(production["request_json"]),
                "cost": {"spent": Money.from_units(production["spent_units"]).model_dump(mode="json"), "reserved": Money.from_units(production["reserved_units"]).model_dump(mode="json")},
                "operations": [{"operation_id": op["id"], "status": op["status"], "cost_status": "unknown" if op["actual_units"] is None else "known", "actual_cost": None if op["actual_units"] is None else Money.from_units(op["actual_units"]).model_dump(mode="json"), "cost_evidence": op["cost_evidence"], "external_id": op["external_id"]} for op in operations],
                "revision_cycles": production["revision_cycles"],
                "bundle_ref": None if not bundle else BundleRef(schema_version=accepted.schema_version, instance_id=self.instance_id, bundle_id=bundle["bundle_id"], bundle_revision_id=bundle["revision_id"], manifest_sha256=bundle["manifest_sha256"]).model_dump(mode="json"),
            })

    def list_productions(self, subject: str, limit: int = 50) -> list[ProductionAccepted]:
        with self.db.connect() as connection:
            rows = connection.execute("SELECT * FROM productions WHERE owner=? ORDER BY created_at_us DESC LIMIT ?", (subject, min(max(limit, 1), 100))).fetchall()
            return [self._accepted(connection, row) for row in rows]

    def recover(self) -> dict[str, int]:
        """A dispatch uncertainty is preserved; recovery never re-submits it."""
        recovered = reconciliations = 0
        with self.db.transaction() as connection:
            runs = connection.execute("SELECT * FROM runs WHERE lease_until_us<=? AND status IN ('running','waiting_provider','cancel_requested')", (self.clock(),)).fetchall()
            for run in runs:
                connection.execute("UPDATE operations SET status='unknown' WHERE run_id=? AND status='submitting'", (run["id"],))
                unknown = connection.execute("SELECT id FROM operations WHERE run_id=? AND (status='unknown' OR (settled=0 AND status IN ('succeeded','failed'))) LIMIT 1", (run["id"],)).fetchone()
                pending = connection.execute("SELECT id FROM operations WHERE run_id=? AND status='pending' LIMIT 1", (run["id"],)).fetchone()
                status = "needs_reconciliation" if unknown else "cancel_requested" if pending and run["cancellation_requested"] else "waiting_provider" if pending else "cancelled" if run["cancellation_requested"] else "queued"
                connection.execute("UPDATE runs SET status=?,worker_id=NULL,lease_until_us=0 WHERE id=?", (status, run["id"]))
                connection.execute("UPDATE productions SET status=? WHERE id=?", (status, run["production_id"]))
                self._event(connection, self._run(connection, run["id"]), "run.recovered")
                recovered += 1
                reconciliations += bool(unknown)
        return {"recovered_runs": recovered, "needs_reconciliation": reconciliations}

    def acquire_run(self, worker_id: str, lease_seconds: int = 60, run_id: str | None = None, reconciliation: bool = False) -> LeaseGrant | None:
        if not worker_id or not 1 <= lease_seconds <= 3600:
            raise EngineError("invalid_lease", "Lease lifetime must be 1 to 3600 seconds", 400)
        self.recover()
        statuses = ("needs_reconciliation", "waiting_provider", "cancel_requested") if reconciliation else ("queued",)
        with self.db.transaction() as connection:
            placeholders = ",".join("?" for _ in statuses)
            query = f"SELECT * FROM runs WHERE status IN ({placeholders}) AND lease_until_us<=?"
            if not reconciliation:
                query += " AND paused=0 AND cancellation_requested=0"
                # A reconciliation may temporarily return the original Run to
                # queued. Its real authorization wait must still block normal
                # production until an explicit Owner action clears that journal.
                query += " AND NOT EXISTS (SELECT 1 FROM metadata WHERE key='production_authorization_wait:'||runs.id)"
                # Resource/authorization progress must pass its exact same-Run
                # current-source CAS resumer before normal production resumes.
                query += " AND NOT EXISTS (SELECT 1 FROM metadata WHERE key='current_production_blocker:'||runs.id)"
            parameters: list = [*statuses, self.clock()]
            if run_id:
                query += " AND id=?"
                parameters.append(run_id)
            run = connection.execute(query + " ORDER BY rowid LIMIT 1", parameters).fetchone()
            if run is None:
                return None
            if not reconciliation:
                checkpoint = connection.execute('SELECT value FROM metadata WHERE key=?',
                    ('current_production_final_evidence:' + run['id'],)).fetchone()
                if checkpoint is not None:
                    from video_creator.application.current_final_evidence_journal import (
                        parse_journal,
                        prepared_current,
                    )
                    final = parse_journal(checkpoint[0], now=self.clock())
                    prepared_current(self, connection, final)
                    if final.control.phase == 'waiting':
                        return None
            fence, expiry = run["fencing_token"] + 1, self.clock() + lease_seconds * 1_000_000
            status = run["status"] if reconciliation else "running"
            connection.execute("UPDATE runs SET worker_id=?,lease_until_us=?,fencing_token=?,attempt=attempt+1,status=? WHERE id=?", (worker_id, expiry, fence, status, run["id"]))
            connection.execute("UPDATE productions SET status=? WHERE id=?", (status, run["production_id"]))
            self._event(connection, self._run(connection, run["id"]), "run.leased")
            return LeaseGrant(run_id=run["id"], worker_id=worker_id, fencing_token=fence, expires_at_us=expiry)

    def heartbeat(self, lease: LeaseGrant, lease_seconds: int = 60) -> LeaseGrant:
        if not 1 <= lease_seconds <= 3600:
            raise EngineError("invalid_lease", "Lease lifetime must be 1 to 3600 seconds", 400)
        with self.db.transaction() as connection:
            self._lease(connection, lease, allow_cancel=True)
            expiry = self.clock() + lease_seconds * 1_000_000
            connection.execute("UPDATE runs SET lease_until_us=? WHERE id=?", (expiry, lease.run_id))
            return lease.model_copy(update={"expires_at_us": expiry})

    def get_request(self, lease: LeaseGrant) -> ProductionRequest:
        with self.db.connect() as connection:
            run = self._lease(connection, lease, allow_cancel=True)
            return parse_production_request(self._production(connection, run["production_id"])["request_json"])

    def begin_step(self, lease: LeaseGrant, step_key: str, input_sha256: str) -> dict:
        with self._initial_alignment_step_context(lease, step_key) as alignment_guard, self.db.transaction() as connection:
            run = self._lease(connection, lease)
            from video_creator.application.affected_step_guard import (
                assert_affected_step,
            )
            assert_affected_step(connection, self, lease, step_key, input_sha256, authorization_guard=alignment_guard)
            production = self._production(connection, run["production_id"])
            request = parse_production_request(production["request_json"])
            self._evidence_execution_guard(connection, production, request)
            if request.request_format_version is not None and not self._full_output_profile(request):
                raise EngineError("output_profile_unavailable", "This legal output subset has no installed execution profile", 409)
            if run["paused"]:
                raise EngineError("run_paused", "New steps are paused")
            step = connection.execute("SELECT * FROM steps WHERE run_id=? AND step_key=?", (lease.run_id, step_key)).fetchone()
            if step:
                if step["input_sha256"] != input_sha256:
                    raise EngineError("step_input_conflict", "Step input is fixed within this run")
                if step["status"] == "succeeded":
                    return dict(step)
                connection.execute("UPDATE steps SET fencing_token=? WHERE run_id=? AND step_key=?", (lease.fencing_token, lease.run_id, step_key))
            else:
                connection.execute("INSERT INTO steps VALUES(?,?,?,'running',?,NULL)", (lease.run_id, step_key, input_sha256, lease.fencing_token))
                self._event(connection, run, "step.started")
            assert_affected_step(connection, self, lease, step_key, input_sha256, authorization_guard=alignment_guard)
            return dict(connection.execute("SELECT * FROM steps WHERE run_id=? AND step_key=?", (lease.run_id, step_key)).fetchone())

    @contextmanager
    def _initial_alignment_step_context(self, lease, step_key):
        if step_key.startswith(('repair-alignment-', 'bundle-alignment-')):
            with self._operation_authorization_context(lease, affected_step_key=step_key) as guard:
                yield guard
        else:
            yield None

    def _route_guard(self, connection, production, intent: OperationIntent) -> CapabilityRoute:
        request = parse_production_request(production["request_json"])
        self._evidence_execution_guard(connection, production, request)
        if request.request_format_version is not None and not self._full_output_profile(request):
            raise EngineError("output_profile_unavailable", "This legal output subset has no installed execution profile", 409)
        row = connection.execute("SELECT body FROM routes WHERE id=?", (intent.route_id,)).fetchone()
        if intent.route_id not in request.policy.allowed_provider_routes or row is None:
            raise EngineError("route_denied", "Provider route is outside the authorized policy", 403)
        route = CapabilityRoute.model_validate_json(row[0])
        if not route.verified or route.source == "official":
            raise EngineError("capability_unavailable", "Provider capability is unavailable", 503)
        if route.source == "owned_remote" and not request.policy.external_transfer_allowed:
            raise EngineError("transfer_denied", "External transfer is not authorized", 403)
        if intent.reserved_cost.units() < route.max_operation_cost.units():
            raise EngineError("reservation_too_small", "Reservation must cover the configured operation bound", 400)
        return route

    def prepare_operation(self, lease: LeaseGrant, intent: OperationIntent) -> dict:
        # Returning an immutable original Operation is observation, never new
        # submission permission. Preserve dedupe/unknown semantics even after a
        # later policy change; claim has its own irreversible-boundary guard.
        with self.db.connect() as connection:
            run = self._lease(connection, lease)
            existing = connection.execute('SELECT id FROM operations WHERE production_id=? AND dedupe_key=?',
                                          (run['production_id'], intent.dedupe_key)).fetchone()
        if existing:
            return self._prepare_operation_writer(lease, intent, authorization_guard=None)
        with self._operation_authorization_context(lease, affected_step_key=intent.step_key) as guard:
            return self._prepare_operation_writer(lease, intent, authorization_guard=guard)

    def _prepare_operation_writer(self, lease, intent, *, authorization_guard):
        with self.db.transaction() as connection:
            run = self._lease(connection, lease)
            production = self._production(connection, run["production_id"])
            existing = connection.execute("SELECT * FROM operations WHERE production_id=? AND dedupe_key=?", (production["id"], intent.dedupe_key)).fetchone()
            if existing:
                saved_route = CapabilityRoute.model_validate_json(existing["route_json"])
                if (existing["input_sha256"] != intent.input_sha256 or existing["step_key"] != intent.step_key
                        or saved_route.route_id != intent.route_id or existing["reserved_units"] != intent.reserved_cost.units()):
                    raise EngineError("operation_input_conflict", "Operation identity has different input or route")
                return dict(existing)
            if run["paused"]:
                raise EngineError("run_paused", "New operations are paused")
            from video_creator.application.affected_step_guard import (
                assert_affected_step,
            )
            assert_affected_step(connection, self, lease, intent.step_key, intent.input_sha256, intent=intent, authorization_guard=authorization_guard)
            step = connection.execute("SELECT status FROM steps WHERE run_id=? AND step_key=?", (lease.run_id, intent.step_key)).fetchone()
            if not step or step["status"] != "running":
                raise EngineError("step_not_running", "Start the fixed-input step before preparing operations")
            if parse_production_request(production['request_json']).automation.mode == 'unattended':
                if authorization_guard is None or self.production_admissions is None:
                    raise EngineError('production_authorization_unconfigured', 'Current actual Owner execution guard is required', 403)
                self.production_admissions.require_operation_current(connection, authorization_guard, lease)
            route = self._route_guard(connection, production, intent)
            reserve = intent.reserved_cost.units()
            if reserve + production["spent_units"] + production["reserved_units"] > production["cap_units"]:
                raise EngineError("budget_exceeded", "Production budget would be exceeded", 402)
            group_id = production["budget_group_id"]
            if reserve and not group_id:
                raise EngineError("budget_unauthorized", "Paid execution requires an instance authorization group", 403)
            if group_id:
                group = connection.execute("SELECT * FROM budget_groups WHERE id=?", (group_id,)).fetchone()
                if reserve + group["spent_units"] + group["reserved_units"] > group["cap_units"]:
                    raise EngineError("shared_budget_exceeded", "Shared authorization would be exceeded", 402)
                connection.execute("UPDATE budget_groups SET reserved_units=reserved_units+? WHERE id=?", (reserve, group_id))
            connection.execute("UPDATE productions SET reserved_units=reserved_units+? WHERE id=?", (reserve, production["id"]))
            operation_id = identity("operation")
            connection.execute("INSERT INTO operations(id,production_id,run_id,step_key,dedupe_key,input_sha256,route_json,status,reserved_units,created_at_us) VALUES(?,?,?,?,?,?,?,'prepared',?,?)", (operation_id, production["id"], lease.run_id, intent.step_key, intent.dedupe_key, intent.input_sha256, canonical(route), reserve, self.clock()))
            self._event(connection, run, "operation.prepared")
            assert_affected_step(connection, self, lease, intent.step_key, intent.input_sha256, intent=intent, authorization_guard=authorization_guard)
            return dict(connection.execute("SELECT * FROM operations WHERE id=?", (operation_id,)).fetchone())

    def _operation(self, connection, run, operation_id: str):
        operation = connection.execute("SELECT * FROM operations WHERE id=? AND production_id=?", (operation_id, run["production_id"])).fetchone()
        if operation is None:
            raise EngineError("not_found", "Operation not found", 404)
        return operation

    def claim_operation(self, lease: LeaseGrant, operation_id: str) -> ExecutionPermit:
        with self.db.connect_readonly() as connection:
            run = self._lease(connection, lease)
            step_key = self._operation(connection, run, operation_id)['step_key']
        with self._operation_authorization_context(lease, affected_step_key=step_key) as guard:
            return self._claim_operation_writer(lease, operation_id, authorization_guard=guard)

    def _claim_operation_writer(self, lease, operation_id, *, authorization_guard):
        with self.db.transaction() as connection:
            run = self._lease(connection, lease)
            operation = self._operation(connection, run, operation_id)
            if operation["status"] != "prepared" or operation["run_id"] != lease.run_id:
                raise EngineError("operation_not_submittable", "Existing side effect must be read or reconciled", retryability="reconcile")
            if run["paused"]:
                raise EngineError("run_paused", "New operations are paused")
            production = self._production(connection, run['production_id'])
            if parse_production_request(production['request_json']).automation.mode == 'unattended':
                if authorization_guard is None or self.production_admissions is None:
                    raise EngineError('production_authorization_unconfigured', 'Current actual Owner execution guard is required', 403)
                self.production_admissions.require_operation_current(connection, authorization_guard, lease)
            # Revalidate current allowed configuration before the irreversible boundary.
            intent = OperationIntent(step_key=operation["step_key"], dedupe_key=operation["dedupe_key"], input_sha256=operation["input_sha256"], route_id=CapabilityRoute.model_validate_json(operation["route_json"]).route_id, reserved_cost=Money.from_units(operation["reserved_units"]))
            from video_creator.application.affected_step_guard import (
                assert_affected_step,
            )
            assert_affected_step(connection, self, lease, intent.step_key, intent.input_sha256, intent=intent, authorization_guard=authorization_guard)
            current_route = self._route_guard(connection, production, intent)
            if canonical(current_route) != operation["route_json"]:
                raise EngineError("route_configuration_changed", "Route changed after preparation")
            connection.execute("UPDATE operations SET status='submitting',claimed_fence=? WHERE id=?", (lease.fencing_token, operation_id))
            self._event(connection, run, "operation.dispatch_intent")
            assert_affected_step(connection, self, lease, intent.step_key, intent.input_sha256, intent=intent, authorization_guard=authorization_guard)
            return ExecutionPermit(operation_id=operation_id, run_id=lease.run_id, fencing_token=lease.fencing_token, route=current_route)

    def observe_operation(self, lease: LeaseGrant, operation_id: str, observation: OperationObservation, reconciliation: bool = False) -> dict:
        with self.db.transaction() as connection:
            run = self._lease(connection, lease, allow_cancel=True)
            if run["status"] == "needs_reconciliation" and connection.execute("SELECT slot FROM worker_presence WHERE worker_id=? AND active_run_id=?", (lease.worker_id, lease.run_id)).fetchone():
                raise EngineError("reconciliation_port_required", "A local worker must use its restricted original-operation evidence port", 409)
            return self._observe_operation(connection, run, lease, operation_id, observation, reconciliation)

    def _observe_operation(self, connection, run, lease: LeaseGrant, operation_id: str, observation: OperationObservation, reconciliation: bool,
                           hold_reconciliation: bool = False) -> dict:
        """Existing settlement logic; a caller must first prove its lease scope."""
        operation = self._operation(connection, run, operation_id)
        try:
            observation = normalize_observation(observation, CapabilityRoute.model_validate_json(operation["route_json"]).cost_rule_version)
        except EngineError:
            observation = observation.model_copy(update={"actual_cost": None, "cost_evidence": "unknown"})
        if operation["run_id"] != lease.run_id:
            raise EngineError("operation_run_conflict", "Reconciliation must use the original run")
        if operation["status"] == "prepared":
            raise EngineError("operation_not_dispatched", "Operation was not dispatched")
        if operation["status"] == "unknown" and not reconciliation:
            raise EngineError("reconciliation_required", "Unknown acceptance requires explicit reconciliation evidence", retryability="reconcile")
        body = canonical(observation)
        if operation["settled"]:
            if operation["observation_json"] != body:
                raise EngineError("observation_conflict", "Settled observation is immutable")
            return dict(operation)
        if operation["external_id"] and observation.external_id != operation["external_id"]:
            raise EngineError("external_id_conflict", "External request identity is fixed")
        for asset_id in observation.result_asset_ids:
            production = self._production(connection, run["production_id"])
            if not connection.execute("SELECT id FROM assets WHERE id=? AND owner=?", (asset_id, production["owner"])).fetchone():
                raise EngineError("result_asset_denied", "Result asset is unavailable", 403)
        settled = observation.actual_cost is not None and observation.status in {"succeeded", "failed"}
        actual_units = observation.actual_cost.units() if observation.actual_cost is not None else None
        if settled:
            reserve = operation["reserved_units"]
            production = self._production(connection, run["production_id"])
            connection.execute("UPDATE productions SET reserved_units=reserved_units-?,spent_units=spent_units+? WHERE id=?", (reserve, actual_units, production["id"]))
            if production["budget_group_id"]:
                connection.execute("UPDATE budget_groups SET reserved_units=reserved_units-?,spent_units=spent_units+? WHERE id=?", (reserve, actual_units, production["budget_group_id"]))
        connection.execute("UPDATE operations SET status=?,external_id=?,observation_json=?,actual_units=?,cost_evidence=?,settled=? WHERE id=?", (observation.status, observation.external_id, body, actual_units, observation.cost_evidence, int(settled), operation_id))
        if observation.status == "unknown" or (observation.status in {"succeeded", "failed"} and not settled):
            status = "needs_reconciliation"
        elif observation.status == "pending":
            status = "cancel_requested" if run["cancellation_requested"] else "waiting_provider"
        elif run["cancellation_requested"]:
            unknown = connection.execute("SELECT id FROM operations WHERE run_id=? AND (status='unknown' OR (settled=0 AND status IN ('succeeded','failed'))) LIMIT 1", (lease.run_id,)).fetchone()
            active = connection.execute("SELECT id FROM operations WHERE run_id=? AND status IN ('submitting','pending') LIMIT 1", (lease.run_id,)).fetchone()
            status = "needs_reconciliation" if unknown else "cancel_requested" if active else "cancelled"
        else:
            status = "running"
        # An actual charge over the bound is recorded honestly, then all new dispatch stops.
        if settled and actual_units > operation["reserved_units"]:
            status = "needs_reconciliation"
        if hold_reconciliation:
            status = run["status"] if run["status"] in {"failed", "cancelled", "cancel_requested"} else "needs_reconciliation"
        connection.execute("UPDATE runs SET status=? WHERE id=?", (status, lease.run_id))
        connection.execute("UPDATE productions SET status=? WHERE id=?", (status, run["production_id"]))
        self._event(connection, self._run(connection, lease.run_id), "operation.observed")
        return dict(connection.execute("SELECT * FROM operations WHERE id=?", (operation_id,)).fetchone())

    def complete_step(self, lease: LeaseGrant, step_key: str, asset_ids: tuple[str, ...] = (), result_json: object = None) -> dict:
        if step_key.startswith(('repair-alignment-', 'bundle-alignment-')):
            raise EngineError('alignment_commit_required', 'Only the original settled JSON result consumer may commit alignment', 403)
        reject_secrets(result_json)
        with self.db.transaction() as connection:
            return self._complete_step(connection, lease, step_key, asset_ids, result_json)

    def _complete_step(self, connection, lease: LeaseGrant, step_key: str, asset_ids: tuple[str, ...], result_json: object) -> dict:
        """Shared guard for ordinary and atomically registered generated results."""
        run = self._lease(connection, lease)
        production = self._production(connection, run["production_id"])
        step = connection.execute("SELECT * FROM steps WHERE run_id=? AND step_key=?", (lease.run_id, step_key)).fetchone()
        if not step:
            raise EngineError("step_not_found", "Step was not started", 404)
        for asset_id in asset_ids:
            if not connection.execute("SELECT id FROM assets WHERE id=? AND owner=?", (asset_id, production["owner"])).fetchone():
                raise EngineError("result_asset_denied", "Step result asset is unavailable", 403)
        result = json.dumps({"asset_ids": list(asset_ids), "result": result_json}, sort_keys=True, ensure_ascii=False)
        if step["status"] == "succeeded":
            if step["result_json"] != result:
                raise EngineError("step_result_conflict", "Completed step is immutable")
            return dict(step)
        pending = connection.execute("SELECT id FROM operations WHERE run_id=? AND step_key=? AND (status!='succeeded' OR settled=0) LIMIT 1", (lease.run_id, step_key)).fetchone()
        if pending:
            raise EngineError("operation_incomplete", "Step has incomplete or unreconciled operations", retryability="reconcile")
        connection.execute("UPDATE steps SET status='succeeded',result_json=?,fencing_token=? WHERE run_id=? AND step_key=?", (result, lease.fencing_token, lease.run_id, step_key))
        self._event(connection, run, "step.completed")
        return dict(connection.execute("SELECT * FROM steps WHERE run_id=? AND step_key=?", (lease.run_id, step_key)).fetchone())

    def read_review_decision(self, lease: LeaseGrant, revision_id: str) -> ReviewDecision | None:
        with self.db.connect() as connection:
            run = self._lease(connection, lease, allow_cancel=True)
            if not connection.execute("SELECT id FROM creative_revisions WHERE id=? AND production_id=?", (revision_id, run["production_id"])).fetchone():
                raise EngineError("revision_not_found", "Revision is outside the leased production", 404)
            rows = connection.execute("SELECT body FROM decisions WHERE run_id=? ORDER BY rowid", (lease.run_id,)).fetchall()
            matches = [ReviewDecision.model_validate_json(row[0]) for row in rows]
            return next((item for item in matches if item.target_revision_id == revision_id), None)

    def release_run(self, lease: LeaseGrant) -> None:
        """Stop holding this attempt, preserving uncertain dispatch for recovery."""
        with self.db.transaction() as connection:
            run = self._lease(connection, lease, allow_cancel=True)
            # needs_reconciliation is already a recovery state, so recover()
            # need not visit it. Release this exact validated owner's marker in
            # the same writer; uncertainty, current fence and budget remain.
            connection.execute("UPDATE runs SET worker_id=NULL,lease_until_us=0 WHERE id=?", (run["id"],))
        self.recover()

    def read_step(self, lease: LeaseGrant, step_key: str) -> dict | None:
        with self.db.connect() as connection:
            self._lease(connection, lease, allow_cancel=True)
            row = connection.execute("SELECT * FROM steps WHERE run_id=? AND step_key=?", (lease.run_id, step_key)).fetchone()
            return dict(row) if row else None

    def commit_creative_revision(self, lease: LeaseGrant, revision: CreativeRevision) -> CreativeRevision:
        registered_plan = None
        plan_source = None
        if isinstance(revision.body, dict) and revision.body.get('format') == 'registered-production-plan-v2':
            plan_source = getattr(self, '_registered_plan_source', None)
            if (plan_source is None or plan_source.engine is not self
                    or getattr(plan_source, '_production_services_runtime', None) is None
                    or plan_source._production_services_runtime.engine is not self
                    or plan_source._production_services_runtime.bundle is not plan_source):
                raise EngineError('plan_repair_source_not_ready', 'Original held registered plan source required', 503)
            registered_plan = plan_source.validate_registered_plan(lease, revision)
        body = canonical(revision)
        from contextlib import nullcontext
        with (plan_source.plan_commit_guard(lease) if registered_plan is not None else nullcontext()) as plan_guard, self.db.transaction() as connection:
            run = self._lease(connection, lease)
            if registered_plan is not None:
                plan_source.assert_plan_sources_writer(connection, lease, registered_plan, plan_guard)
            existing = connection.execute("SELECT * FROM creative_revisions WHERE id=?", (revision.revision_id,)).fetchone()
            if existing:
                if existing["production_id"] != run["production_id"] or existing["content_sha256"] != digest(body):
                    raise EngineError("revision_conflict", "Creative revision ID is immutable")
                if registered_plan is not None:
                    plan_source.assert_plan_sources_writer(connection, lease, registered_plan, plan_guard)
                return CreativeRevision.model_validate_json(existing["body"])
            for ref in (*revision.input_revision_refs, *((revision.parent_revision_id,) if revision.parent_revision_id else ())):
                if not connection.execute("SELECT id FROM creative_revisions WHERE id=? AND production_id=?", (ref, run["production_id"])).fetchone():
                    raise EngineError("revision_ref_denied", "Creative revision reference is unavailable", 403)
            connection.execute("INSERT INTO creative_revisions VALUES(?,?,?,?,?,?)", (revision.revision_id, run["production_id"], lease.run_id, revision.kind, body, digest(body)))
            self._event(connection, run, f"{revision.kind}.ready", revision.revision_id)
            if registered_plan is not None:
                plan_source.assert_plan_sources_writer(connection, lease, registered_plan, plan_guard)
        return revision

    def creative_revisions(self, subject: str, production_id: str) -> list[CreativeRevision]:
        with self.db.connect() as connection:
            self._production(connection, production_id, subject)
            rows = connection.execute("SELECT body FROM creative_revisions WHERE production_id=? ORDER BY rowid", (production_id,)).fetchall()
            return [CreativeRevision.model_validate_json(row[0]) for row in rows]

    def feedback_for_run(self, lease: LeaseGrant) -> FeedbackRevision | None:
        with self.db.connect() as connection:
            self._lease(connection, lease, allow_cancel=True)
            row = connection.execute("SELECT body FROM feedback_revisions WHERE new_run_id=?", (lease.run_id,)).fetchone()
            return FeedbackRevision.model_validate_json(row[0]) if row else None

    def wait_for_review(self, lease: LeaseGrant, revision_id: str):
        with self.db.transaction() as connection:
            run = self._lease(connection, lease)
            request = parse_production_request(self._production(connection, run["production_id"])["request_json"])
            if request.automation.mode != "interactive":
                raise EngineError("review_mode_conflict", "Unattended approval must use policy validation")
            if not connection.execute("SELECT id FROM creative_revisions WHERE id=? AND production_id=?", (revision_id, run["production_id"])).fetchone():
                raise EngineError("revision_not_found", "Only a persisted creative revision can be reviewed", 404)
            connection.execute("UPDATE runs SET status='waiting_user',waiting_revision_id=?,worker_id=NULL,lease_until_us=0 WHERE id=?", (revision_id, lease.run_id))
            connection.execute("UPDATE productions SET status='waiting_user' WHERE id=?", (run["production_id"],))
            self._event(connection, self._run(connection, lease.run_id), "review.required", revision_id)

    def submit_decision(self, subject: str, run_id: str, key: str, decision: ReviewDecision) -> dict:
        body, decision_hash = canonical(decision), digest(canonical(decision))
        with self.db.transaction() as connection:
            run = self._run(connection, run_id)
            production = self._production(connection, run["production_id"], subject)
            existing = connection.execute("SELECT * FROM decisions WHERE run_id=? AND idempotency_key=?", (run_id, key)).fetchone()
            if existing:
                if existing["request_sha256"] != decision_hash:
                    raise EngineError("idempotency_conflict", "Decision key has different input")
                return json.loads(existing["result_json"])
            if run["status"] != "waiting_user" or run["waiting_revision_id"] != decision.target_revision_id:
                raise EngineError("revision_conflict", "Decision targets an old or unavailable revision")
            target = connection.execute("SELECT body FROM creative_revisions WHERE id=?", (decision.target_revision_id,)).fetchone()
            target_body = CreativeRevision.model_validate_json(target[0]).body if target else None
            missing_capability = (target_body.get("code") or target_body.get("block_code")) if isinstance(target_body, dict) else None
            if decision.action == "approve" and missing_capability in {"output_profile_unavailable", "alignment_required"}:
                raise EngineError(missing_capability, "Approval cannot install a missing execution or evidence capability", 409)
            if decision.action == "revise":
                request = parse_production_request(production["request_json"])
                if production["revision_cycles"] >= request.automation.max_revision_cycles:
                    raise EngineError("revision_limit", "Production revision limit has been reached")
                new_run_id = identity("run")
                connection.execute("INSERT INTO runs(id,production_id,status) VALUES(?,?,'queued')", (new_run_id, production["id"]))
                feedback = FeedbackRevision(feedback_id=identity("feedback"), previous_run_id=run_id, new_run_id=new_run_id, target_revision_id=decision.target_revision_id, instruction_text=decision.instruction_text, preserved_constraints=decision.preserved_constraints)
                connection.execute("INSERT INTO feedback_revisions VALUES(?,?,?,?)", (feedback.feedback_id, production["id"], new_run_id, canonical(feedback)))
                result = feedback.model_dump(mode="json")
                connection.execute("INSERT INTO decisions VALUES(?,?,?,?,?)", (run_id, key, decision_hash, body, json.dumps(result)))
                connection.execute("UPDATE productions SET revision_cycles=revision_cycles+1,status='queued' WHERE id=?", (production["id"],))
                connection.execute("UPDATE runs SET status='cancelled',waiting_revision_id=NULL WHERE id=?", (run_id,))
                self._event(connection, self._run(connection, new_run_id), "feedback.accepted", feedback.feedback_id)
                return result
            connection.execute("INSERT INTO decisions VALUES(?,?,?,?,?)", (run_id, key, decision_hash, body, body))
            status = "queued" if decision.action == "approve" else "failed"
            connection.execute("UPDATE runs SET status=?,waiting_revision_id=NULL WHERE id=?", (status, run_id))
            connection.execute("UPDATE productions SET status=? WHERE id=?", (status, production["id"]))
            self._event(connection, self._run(connection, run_id), "review.decided", decision.target_revision_id)
            return decision.model_dump(mode="json")

    def cancel_production(self, subject: str, production_id: str):
        with self.db.transaction() as connection:
            self._production(connection, production_id, subject)
            runs = connection.execute("SELECT * FROM runs WHERE production_id=? AND status NOT IN ('succeeded','failed','cancelled')", (production_id,)).fetchall()
            for run in runs:
                prepared = connection.execute("SELECT * FROM operations WHERE run_id=? AND status='prepared' AND settled=0", (run["id"],)).fetchall()
                for operation in prepared:
                    production = self._production(connection, production_id)
                    reserve = operation["reserved_units"]
                    observation = OperationObservation(status="failed", actual_cost=Money(amount="0"), cost_evidence="confirmed_no_charge")
                    connection.execute("UPDATE operations SET status='failed',settled=1,actual_units=0,cost_evidence='confirmed_no_charge',observation_json=? WHERE id=?", (canonical(observation), operation["id"]))
                    connection.execute("UPDATE productions SET reserved_units=reserved_units-? WHERE id=?", (reserve, production_id))
                    if production["budget_group_id"]:
                        connection.execute("UPDATE budget_groups SET reserved_units=reserved_units-? WHERE id=?", (reserve, production["budget_group_id"]))
                unknown = connection.execute("SELECT id FROM operations WHERE run_id=? AND (status='unknown' OR (settled=0 AND status IN ('succeeded','failed'))) LIMIT 1", (run["id"],)).fetchone()
                active = connection.execute("SELECT id FROM operations WHERE run_id=? AND status IN ('submitting','pending') LIMIT 1", (run["id"],)).fetchone()
                status = "needs_reconciliation" if unknown else "cancel_requested" if active else "cancelled"
                connection.execute("UPDATE runs SET status=?,cancellation_requested=1 WHERE id=?", (status, run["id"]))
                connection.execute("UPDATE productions SET status=? WHERE id=?", (status, production_id))
                self._event(connection, self._run(connection, run["id"]), "production.cancel_requested")

    def set_paused(self, subject: str, run_id: str, paused: bool):
        with self.db.transaction() as connection:
            run = self._run(connection, run_id)
            self._production(connection, run["production_id"], subject)
            if run["status"] in {"succeeded", "failed", "cancelled", "cancel_requested"}:
                raise EngineError("run_terminal", "Run cannot change its scheduling state")
            connection.execute("UPDATE runs SET paused=? WHERE id=?", (int(paused), run_id))
            self._event(connection, run, "run.paused" if paused else "run.resumed")

    def events(self, subject: str, run_id: str, after_sequence: int = 0, limit: int = 100) -> list[EventEnvelope]:
        with self.db.connect() as connection:
            run = self._run(connection, run_id)
            self._production(connection, run["production_id"], subject)
            rows = connection.execute("SELECT * FROM events WHERE run_id=? AND sequence>? ORDER BY sequence LIMIT ?", (run_id, after_sequence, min(max(limit, 1), 500))).fetchall()
            return [EventEnvelope(event_id=row["id"], sequence=row["sequence"], production_id=row["production_id"], run_id=row["run_id"], event_type=row["event_type"], occurred_at_us=row["occurred_at_us"], status=row["status"], entity_revision_id=row["entity_revision_id"]) for row in rows]

    def budget_status(self, group_id: str) -> dict:
        with self.db.connect() as connection:
            row = connection.execute("SELECT * FROM budget_groups WHERE id=?", (group_id,)).fetchone()
            if row is None:
                raise EngineError("not_found", "Shared budget not configured", 404)
            return {"group_id": group_id, "cap": Money.from_units(row["cap_units"]).model_dump(mode="json"), "spent": Money.from_units(row["spent_units"]).model_dump(mode="json"), "reserved": Money.from_units(row["reserved_units"]).model_dump(mode="json")}
