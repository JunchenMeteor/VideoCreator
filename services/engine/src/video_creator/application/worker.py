"""Gate0 local worker authority, durable bindings and fenced generated commits."""

import hashlib
import json
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from video_creator import __version__
from video_creator.application.assets import AssetService
from video_creator.application.engine import EngineService, canonical, digest, identity
from video_creator.domain.contracts import (
    AssetCandidate,
    CapabilityRoute,
    LeaseGrant,
    MediaProbe,
    Money,
    OperationObservation,
    ProductionRequestAny,
    parse_production_request,
    reject_secrets,
)
from video_creator.domain.errors import EngineError
from video_creator.domain.worker import (
    WORKFLOW_VERSION,
    BoundAsset,
    ExecutionBinding,
    GeneratedFileManifest,
    OutputReservation,
    ReconciliationAllocation,
    ReconciliationEvidence,
    ReconciliationFileHandle,
    ReconciliationInvocation,
    ReconciliationOutcome,
    ReconciliationTarget,
    WorkerInvocation,
    WorkerOutcome,
)

WORKER_SLOT = WORKFLOW_VERSION
HEARTBEAT_SECONDS = 5
PRESENCE_TTL_SECONDS = 15
RUN_LEASE_SECONDS = 30
REGISTERED_MEDIA_WORKFLOW = "registered-media-bundle-v1"


class WorkerService:
    def __init__(self, engine: EngineService, *, workflow_version: str = WORKFLOW_VERSION):
        if workflow_version not in {WORKFLOW_VERSION, REGISTERED_MEDIA_WORKFLOW}:
            raise EngineError("worker_workflow_denied", "Only fixed installed workflow profiles may hold the execution slot", 400)
        self.engine = engine
        self.workflow_version = workflow_version
        self.assets = AssetService(engine)

    def register_presence(self, manifest_sha256: str) -> str:
        # Validate this internal identity without storing launcher paths.
        BoundAsset(asset_id="resources", sha256=manifest_sha256)
        worker_id = identity("worker")
        with self.engine.db.transaction() as connection:
            old = connection.execute("SELECT * FROM worker_presence WHERE slot=?", (WORKER_SLOT,)).fetchone()
            if old and old["state"] in {"idle", "executing"} and old["expires_us"] > self.engine.clock():
                raise EngineError("worker_slot_busy", "The local execution slot is already held")
            now = self.engine.clock()
            connection.execute("INSERT INTO worker_presence VALUES(?,?,?,?,?,?,?,?,?,NULL) ON CONFLICT(slot) DO UPDATE SET worker_id=excluded.worker_id,pid=excluded.pid,workflow_version=excluded.workflow_version,resource_sha256=excluded.resource_sha256,engine_version=excluded.engine_version,heartbeat_us=excluded.heartbeat_us,expires_us=excluded.expires_us,state=excluded.state,active_run_id=NULL",
                               (WORKER_SLOT, worker_id, os.getpid(), self.workflow_version, manifest_sha256, __version__, now, now + PRESENCE_TTL_SECONDS * 1_000_000, "idle"))
        return worker_id

    def _presence(self, connection, worker_id: str):
        row = connection.execute("SELECT * FROM worker_presence WHERE slot=? AND worker_id=?", (WORKER_SLOT, worker_id)).fetchone()
        if not row or row["pid"] != os.getpid() or row["workflow_version"] != self.workflow_version or row["expires_us"] <= self.engine.clock() or row["state"] not in {"idle", "executing"}:
            raise EngineError("worker_presence_lost", "Worker presence expired or was superseded")
        return row

    def heartbeat_presence(self, worker_id: str) -> None:
        with self.engine.db.transaction() as connection:
            self._presence(connection, worker_id)
            now = self.engine.clock()
            connection.execute("UPDATE worker_presence SET heartbeat_us=?,expires_us=? WHERE slot=? AND worker_id=?",
                               (now, now + PRESENCE_TTL_SECONDS * 1_000_000, WORKER_SLOT, worker_id))

    def close_presence(self, worker_id: str, *, failed: bool = False) -> None:
        with self.engine.db.transaction() as connection:
            connection.execute("UPDATE worker_presence SET state=?,expires_us=0,active_run_id=NULL WHERE slot=? AND worker_id=?",
                               ("failed" if failed else "stopped", WORKER_SLOT, worker_id))

    def connected(self) -> bool:
        with self.engine.db.connect() as connection:
            row = connection.execute("SELECT * FROM worker_presence WHERE slot=?", (WORKER_SLOT,)).fetchone()
        return bool(row and row["state"] in {"idle", "executing"} and row["expires_us"] > self.engine.clock()
                    and row["engine_version"] == __version__ and row["workflow_version"] in {WORKFLOW_VERSION, REGISTERED_MEDIA_WORKFLOW})

    def bind_execution(self, lease: LeaseGrant, manifest_sha256: str) -> ExecutionBinding:
        request = self.engine.get_request(lease)
        if request.policy.external_transfer_allowed or request.policy.max_cost.units() or request.policy.budget_group_id:
            raise EngineError("local_experiment_policy_denied", "This experiment only permits zero-cost local execution", 403)
        for route_id in request.policy.allowed_provider_routes:
            route = self.engine.configured_route(route_id)
            if route.source != "owned_local" or route.credential_ref or route.max_operation_cost.units():
                raise EngineError("local_experiment_route_denied", "Experiment routes must be credential-free and local at zero cost", 403)
        with self.engine.db.connect() as connection:
            run = self.engine._lease(connection, lease)
            production = self.engine._production(connection, run["production_id"])
            owner, production_id, request_revision = production["owner"], production["id"], production["request_revision_id"]
        references = []
        for asset_id in request.inputs.asset_ids:
            record = self.assets.get(owner, asset_id)
            self.assets.content_path(owner, asset_id)  # Actual bytes checked outside the transaction.
            references.append(BoundAsset(asset_id=asset_id, sha256=record.sha256))
        binding = ExecutionBinding(run_id=lease.run_id, production_id=production_id, request_revision_id=request_revision,
                                   input_assets=tuple(references), resource_manifest_sha256=manifest_sha256)
        body = canonical(binding)
        with self.engine.db.transaction() as connection:
            self.engine._lease(connection, lease)
            existing = connection.execute("SELECT * FROM execution_bindings WHERE run_id=?", (lease.run_id,)).fetchone()
            if existing and existing["body"] != body:
                raise EngineError("execution_binding_conflict", "This run has a different fixed execution binding")
            connection.execute("INSERT OR IGNORE INTO execution_bindings VALUES(?,?,?)", (lease.run_id, body, digest(body)))
        return binding

    def read_binding(self, lease: LeaseGrant) -> ExecutionBinding:
        with self.engine.db.connect() as connection:
            self.engine._lease(connection, lease, allow_cancel=True)
            row = connection.execute("SELECT body FROM execution_bindings WHERE run_id=?", (lease.run_id,)).fetchone()
            if not row:
                raise EngineError("execution_binding_missing", "Bind fixed execution inputs first", 409)
            return ExecutionBinding.model_validate_json(row[0])

    def read_registered_binding(self, lease: LeaseGrant):
        from video_creator.application.delivery_metadata import DeliveryResolver
        from video_creator.domain.registered_production import ProductionBinding

        if self.workflow_version != REGISTERED_MEDIA_WORKFLOW:
            raise EngineError("worker_workflow_denied", "Registered input ports require the fixed registered worker profile", 403)
        with self.engine.db.connect() as connection:
            # A restricted reconciliation lease does not gain normal input,
            # previous-Step or generated-result access through this new port.
            run = self.engine._lease(connection, lease)
            production = self.engine._production(connection, run["production_id"])
            row = connection.execute("SELECT * FROM execution_bindings WHERE run_id=?", (lease.run_id,)).fetchone()
        if not row or digest(row["body"]) != row["content_sha256"]:
            raise EngineError("execution_binding_missing", "Registered input requires its intact original binding", 409)
        binding = ProductionBinding.model_validate(DeliveryResolver._json(row["body"]))
        request = parse_production_request(production["request_json"])
        if ((binding.instance_id, binding.production_id, binding.run_id, binding.request_revision_id,
                binding.request_sha256) != (self.engine.instance_id, production["id"], lease.run_id,
                production["request_revision_id"], digest(production["request_json"]))
                or tuple(item[0] for item in binding.input_assets) != request.inputs.asset_ids):
            raise EngineError("execution_binding_conflict", "Registered inputs differ from this original production request", 409)
        return binding

    def input_asset(self, lease: LeaseGrant, asset_id: str):
        if self.workflow_version == REGISTERED_MEDIA_WORKFLOW:
            binding = self.read_registered_binding(lease)
            inputs = tuple(BoundAsset(asset_id=identifier, sha256=sha) for identifier, sha in binding.input_assets)
        else:
            inputs = self.read_binding(lease).input_assets
        expected = next((item for item in inputs if item.asset_id == asset_id), None)
        if expected is None:
            raise EngineError("input_asset_denied", "Asset is outside this fixed execution binding", 403)
        with self.engine.db.connect() as connection:
            run = self.engine._lease(connection, lease, allow_cancel=True)
            owner = self.engine._production(connection, run["production_id"])["owner"]
        record = self.assets.get(owner, asset_id)
        if record.sha256 != expected.sha256:
            raise EngineError("asset_integrity_failed", "Bound input asset identity changed", 422)
        self.assets.content_path(owner, asset_id)
        return record

    def input_content_path(self, lease: LeaseGrant, asset_id: str) -> Path:
        self.input_asset(lease, asset_id)
        with self.engine.db.connect() as connection:
            run = self.engine._lease(connection, lease, allow_cancel=True)
            owner = self.engine._production(connection, run["production_id"])["owner"]
        return self.assets.content_path(owner, asset_id)

    def production_result_asset(self, lease: LeaseGrant, asset_id: str):
        if self.workflow_version == REGISTERED_MEDIA_WORKFLOW:
            self.read_registered_binding(lease)
        with self.engine.db.connect() as connection:
            run = self.engine._lease(connection, lease, allow_cancel=True)
            owner = self.engine._production(connection, run["production_id"])["owner"]
            rows = connection.execute("SELECT s.result_json FROM steps s JOIN runs r ON r.id=s.run_id WHERE r.production_id=? AND s.status='succeeded'", (run["production_id"],)).fetchall()
            if not any(asset_id in json.loads(row[0]).get("asset_ids", []) for row in rows):
                raise EngineError("result_asset_denied", "Asset is outside this production's committed steps", 403)
        return self.assets.get(owner, asset_id)

    def production_result_content_path(self, lease: LeaseGrant, asset_id: str) -> Path:
        self.production_result_asset(lease, asset_id)
        with self.engine.db.connect() as connection:
            run = self.engine._lease(connection, lease, allow_cancel=True)
            owner = self.engine._production(connection, run["production_id"])["owner"]
        return self.assets.content_path(owner, asset_id)

    def read_previous_step(self, lease: LeaseGrant, step_key: str) -> dict | None:
        if self.workflow_version == REGISTERED_MEDIA_WORKFLOW:
            self.read_registered_binding(lease)
        feedback = self.engine.feedback_for_run(lease)
        if feedback is None:
            return None
        with self.engine.db.connect() as connection:
            run = self.engine._lease(connection, lease, allow_cancel=True)
            previous = self.engine._run(connection, feedback.previous_run_id)
            if previous["production_id"] != run["production_id"]:
                raise EngineError("feedback_scope_denied", "Previous step is outside this production", 403)
            row = connection.execute("SELECT * FROM steps WHERE run_id=? AND step_key=? AND status='succeeded'", (previous["id"], step_key)).fetchone()
            return dict(row) if row else None

    def invocation(self, worker_id: str, manifest_sha256: str, max_seconds: int,
                   run_id: str | None = None) -> WorkerInvocation | None:
        with self.engine.db.transaction() as connection:
            presence = self._presence(connection, worker_id)
            if presence["resource_sha256"] != manifest_sha256:
                raise EngineError("worker_resource_conflict", "Worker resources differ from its verified registration")
            if presence["active_run_id"]:
                raise EngineError("worker_slot_busy", "Worker already holds an execution slot")
        self.engine.recover()
        with self.engine.db.connect() as connection:
            # This experiment has no Bundle terminal. A durable approved-review
            # Step parks local dispatch without inventing Production success.
            query = "SELECT r.id FROM runs r WHERE r.status='queued' AND r.paused=0 AND r.cancellation_requested=0 AND NOT EXISTS (SELECT 1 FROM steps s WHERE s.run_id=r.id AND s.step_key='local-review-approved' AND s.status='succeeded')"
            selected = connection.execute(query + (" AND r.id=?" if run_id else "") + " ORDER BY r.rowid LIMIT 1", (run_id,) if run_id else ()).fetchone()
        if selected is None:
            return None
        lease = self.engine.acquire_run(worker_id, lease_seconds=RUN_LEASE_SECONDS, run_id=selected[0])
        if not lease:
            return None
        try:
            binding = self.bind_execution(lease, manifest_sha256)
            with self.engine.db.transaction() as connection:
                self._presence(connection, worker_id)
                self.engine._lease(connection, lease)
                connection.execute("UPDATE worker_presence SET state='executing',active_run_id=? WHERE slot=? AND worker_id=?", (lease.run_id, WORKER_SLOT, worker_id))
            return WorkerInvocation(worker_id=worker_id, lease=lease, binding=binding, max_attempt_seconds=max_seconds)
        except BaseException:
            self.engine.release_run(lease)
            raise

    def heartbeat_invocation(self, invocation: WorkerInvocation) -> None:
        self.heartbeat_presence(invocation.worker_id)
        with self.engine.db.connect() as connection:
            run = self.engine._run(connection, invocation.lease.run_id)
            if run["status"] == "waiting_user" and run["worker_id"] is None:
                return  # Human review holds no execution lease.
            if run["cancellation_requested"]:
                raise EngineError("run_cancelled", "This local attempt must stop after explicit cancellation")
        self.engine.heartbeat(invocation.lease, lease_seconds=RUN_LEASE_SECONDS)

    def finish_invocation(self, invocation: WorkerInvocation, outcome: WorkerOutcome) -> None:
        with self.engine.db.connect() as connection:
            run = self.engine._run(connection, invocation.lease.run_id)
        if outcome.state == "waiting_user":
            if run["status"] != "waiting_user" or run["worker_id"] or run["lease_until_us"]:
                raise EngineError("worker_outcome_conflict", "Workflow did not persist and release its review wait")
        else:
            if run["worker_id"] == invocation.worker_id:
                self.engine.release_run(invocation.lease)
            if outcome.state == "needs_reconciliation" and run["status"] != "needs_reconciliation":
                raise EngineError("worker_outcome_conflict", "Reconciliation outcome lacks durable uncertainty")
        with self.engine.db.transaction() as connection:
            self._presence(connection, invocation.worker_id)
            connection.execute("UPDATE worker_presence SET state='idle',active_run_id=NULL WHERE slot=? AND worker_id=?", (WORKER_SLOT, invocation.worker_id))

    def _reconciliation_binding(self, connection, run, manifest_sha256: str) -> tuple[ExecutionBinding, ProductionRequestAny]:
        production = self.engine._production(connection, run["production_id"])
        row = connection.execute("SELECT * FROM execution_bindings WHERE run_id=?", (run["id"],)).fetchone()
        if not row or digest(row["body"]) != row["content_sha256"]:
            raise EngineError("execution_binding_missing", "Reconciliation requires the original intact binding", 409)
        binding = ExecutionBinding.model_validate_json(row["body"])
        if (binding.run_id, binding.production_id, binding.request_revision_id, binding.resource_manifest_sha256) != (run["id"], production["id"], production["request_revision_id"], manifest_sha256):
            raise EngineError("execution_binding_conflict", "Original reconciliation binding or resources differ", 409)
        request = parse_production_request(production["request_json"])
        if request.policy.external_transfer_allowed or request.policy.max_cost.units() or request.policy.budget_group_id:
            raise EngineError("reconciliation_policy_denied", "Only the original zero-cost local policy can be reconciled here", 403)
        if tuple(item.asset_id for item in binding.input_assets) != request.inputs.asset_ids:
            raise EngineError("execution_binding_conflict", "Original bound inputs differ from the immutable request", 409)
        for item in binding.input_assets:
            asset = connection.execute("SELECT sha256 FROM assets WHERE id=? AND owner=?", (item.asset_id, production["owner"])).fetchone()
            if not asset or asset[0] != item.sha256:
                raise EngineError("input_asset_denied", "Original bound input is unavailable or changed", 403)
        return binding, request

    def _reconciliation_target(self, connection, run, operation) -> ReconciliationTarget:
        if operation["run_id"] != run["id"] or operation["production_id"] != run["production_id"]:
            raise EngineError("operation_run_conflict", "Only this original run's operations can be reconciled", 409)
        production = self.engine._production(connection, run["production_id"])
        request = parse_production_request(production["request_json"])
        route = CapabilityRoute.model_validate_json(operation["route_json"])
        current = connection.execute("SELECT body FROM routes WHERE id=?", (route.route_id,)).fetchone()
        if (route.route_id != WORKFLOW_VERSION or route.destination != "local:" + WORKFLOW_VERSION
                or route.source != "owned_local" or route.capability != "render" or route.credential_ref
                or route.max_operation_cost.units() or not route.verified or operation["reserved_units"]
                or route.route_id not in request.policy.allowed_provider_routes or not current or current[0] != operation["route_json"]):
            raise EngineError("reconciliation_route_denied", "Original operation is outside the fixed verified free local render route", 403)
        step = connection.execute("SELECT * FROM steps WHERE run_id=? AND step_key=?", (run["id"], operation["step_key"])).fetchone()
        if not step or step["input_sha256"] != operation["input_sha256"]:
            raise EngineError("reconciliation_input_conflict", "Original operation and fixed step input disagree", 409)
        rows = connection.execute("SELECT a.*,s.owner,s.media_type,s.sha256,s.size,s.status FROM generated_attempts a JOIN staging s ON s.id=a.staging_id WHERE a.run_id=? AND a.step_key=? ORDER BY a.rowid", (run["id"], operation["step_key"])).fetchall()
        if not rows or any(row["input_sha256"] != step["input_sha256"] or row["owner"] != production["owner"] for row in rows):
            raise EngineError("reconciliation_allocations_missing", "Original operation lacks its exact owned output allocations", 409)
        expected_outputs = (("video", "video/mp4"), ("mixed", "audio/wav")) if step["step_key"] == "local-compose" else (("video", "video/mp4"),) if step["step_key"] in {"local-shot-1", "local-shot-2", "local-shot-3"} else ()
        if not expected_outputs or tuple((row["output_key"], row["media_type"]) for row in rows) != expected_outputs:
            raise EngineError("reconciliation_output_set_conflict", "Original allocations do not match this fixed render step's complete ordered profile", 409)
        allocations = tuple(ReconciliationAllocation(attempt_id=row["id"], staging_id=row["staging_id"], allocation_fence=row["allocation_fence"],
                                output_key=row["output_key"], media_type=row["media_type"], source=row["source"], rights=row["rights"],
                                staging_status=row["status"], sha256=row["sha256"] or None, size=row["size"]) for row in rows)
        return ReconciliationTarget(operation_id=operation["id"], step_key=operation["step_key"], input_sha256=operation["input_sha256"],
                                    step_input_sha256=step["input_sha256"], dedupe_key=operation["dedupe_key"], route=route,
                                    external_id=operation["external_id"], status=operation["status"], settled=bool(operation["settled"]),
                                    observation=OperationObservation.model_validate_json(operation["observation_json"]) if operation["observation_json"] else None,
                                    allocations=allocations)

    def reconciliation_invocation(self, worker_id: str, manifest_sha256: str, max_seconds: int,
                                  run_id: str | None = None, excluded_runs: set[str] | None = None) -> ReconciliationInvocation | None:
        self.engine.recover()
        excluded_runs = excluded_runs or set()
        with self.engine.db.transaction() as connection:
            presence = self._presence(connection, worker_id)
            if presence["active_run_id"] or presence["resource_sha256"] != manifest_sha256:
                raise EngineError("worker_slot_busy", "Reconciliation requires the current verified empty worker slot", 409)
            query = "SELECT r.* FROM runs r JOIN execution_bindings b ON b.run_id=r.id WHERE r.status='needs_reconciliation' AND r.lease_until_us<=?"
            rows = connection.execute(query + (" AND r.id=?" if run_id else "") + " ORDER BY r.rowid", (self.engine.clock(), run_id) if run_id else (self.engine.clock(),)).fetchall()
            run = next((row for row in rows if row["id"] not in excluded_runs), None)
            if run is None:
                return None
            binding, request = self._reconciliation_binding(connection, run, manifest_sha256)
            operations = connection.execute("SELECT * FROM operations WHERE run_id=? AND (status='unknown' OR (settled=0 AND status IN ('succeeded','failed'))) ORDER BY rowid", (run["id"],)).fetchall()
            if not operations:
                raise EngineError("reconciliation_targets_missing", "Run has no original unresolved operations", 409)
            targets = tuple(self._reconciliation_target(connection, run, operation) for operation in operations)
            fence, expiry = run["fencing_token"] + 1, self.engine.clock() + RUN_LEASE_SECONDS * 1_000_000
            connection.execute("UPDATE runs SET worker_id=?,lease_until_us=?,fencing_token=?,attempt=attempt+1 WHERE id=?", (worker_id, expiry, fence, run["id"]))
            connection.execute("UPDATE worker_presence SET state='executing',active_run_id=? WHERE slot=? AND worker_id=?", (run["id"], WORKER_SLOT, worker_id))
            self.engine._event(connection, self.engine._run(connection, run["id"]), "reconciliation.leased")
            lease = LeaseGrant(run_id=run["id"], worker_id=worker_id, fencing_token=fence, expires_at_us=expiry)
            return ReconciliationInvocation(worker_id=worker_id, lease=lease, binding=binding, request=request, targets=targets, max_attempt_seconds=max_seconds)

    def _reconciliation_scope(self, connection, invocation: ReconciliationInvocation):
        presence = self._presence(connection, invocation.worker_id)
        run = self.engine._run(connection, invocation.lease.run_id)
        if (invocation.worker_id != invocation.lease.worker_id or presence["active_run_id"] != run["id"]
                or run["worker_id"] != invocation.worker_id or run["fencing_token"] != invocation.lease.fencing_token
                or run["lease_until_us"] <= self.engine.clock()
                or run["status"] not in {"needs_reconciliation", "cancel_requested", "cancelled", "failed"}):
            raise EngineError("stale_lease", "Reconciliation lease expired, changed or left its private phase", 409)
        binding, request = self._reconciliation_binding(connection, run, presence["resource_sha256"])
        if binding != invocation.binding or request != invocation.request:
            raise EngineError("execution_binding_conflict", "Reconciliation must keep its exact original request and binding", 409)
        return run

    def read_reconciliation_target(self, invocation: ReconciliationInvocation, operation_id: str) -> ReconciliationTarget:
        expected = next((item for item in invocation.targets if item.operation_id == operation_id), None)
        if expected is None:
            raise EngineError("reconciliation_target_denied", "Operation is outside this fixed reconciliation invocation", 403)
        with self.engine.db.connect() as connection:
            run = self._reconciliation_scope(connection, invocation)
            operation = self.engine._operation(connection, run, operation_id)
            actual = self._reconciliation_target(connection, run, operation)
        def fixed(value):
            body = value.model_dump(mode="json")
            for key in ("status", "settled", "observation"):
                body.pop(key)
            for allocation in body["allocations"]:
                for key in ("staging_status", "sha256", "size"):
                    allocation.pop(key)
            return body
        if fixed(actual) != fixed(expected):
            raise EngineError("reconciliation_target_conflict", "Original operation or exact allocations changed", 409)
        return actual

    def reconciliation_files(self, invocation: ReconciliationInvocation, operation_id: str) -> tuple[ReconciliationFileHandle, ...]:
        target = self.read_reconciliation_target(invocation, operation_id)
        return tuple(ReconciliationFileHandle(allocation=item, completed_path=self.assets._path("Staging", item.staging_id)) for item in target.allocations)

    def reconciliation_input_asset(self, invocation: ReconciliationInvocation, asset_id: str):
        with self.engine.db.connect() as connection:
            run = self._reconciliation_scope(connection, invocation)
            owner = self.engine._production(connection, run["production_id"])["owner"]
            expected = next((item for item in invocation.binding.input_assets if item.asset_id == asset_id), None)
            if expected is None:
                raise EngineError("input_asset_denied", "Input is outside the original reconciliation binding", 403)
        record = self.assets.get(owner, asset_id)
        if record.sha256 != expected.sha256:
            raise EngineError("asset_integrity_failed", "Original bound input changed", 422)
        self.assets.content_path(owner, asset_id)
        return record

    def reconciliation_input_content_path(self, invocation: ReconciliationInvocation, asset_id: str) -> Path:
        self.reconciliation_input_asset(invocation, asset_id)
        with self.engine.db.connect() as connection:
            run = self._reconciliation_scope(connection, invocation)
            owner = self.engine._production(connection, run["production_id"])["owner"]
        return self.assets.content_path(owner, asset_id)

    def reconciliation_result_asset(self, invocation: ReconciliationInvocation, asset_id: str):
        with self.engine.db.connect() as connection:
            run = self._reconciliation_scope(connection, invocation)
            owner = self.engine._production(connection, run["production_id"])["owner"]
            rows = connection.execute("SELECT result_json FROM steps WHERE run_id=? AND status='succeeded'", (run["id"],)).fetchall()
            if not any(asset_id in json.loads(row[0]).get("asset_ids", []) for row in rows):
                raise EngineError("result_asset_denied", "Reconciliation input is outside this original run's committed steps", 403)
        self.assets.content_path(owner, asset_id)
        return self.assets.get(owner, asset_id)

    def reconciliation_result_content_path(self, invocation: ReconciliationInvocation, asset_id: str) -> Path:
        self.reconciliation_result_asset(invocation, asset_id)
        with self.engine.db.connect() as connection:
            run = self._reconciliation_scope(connection, invocation)
            owner = self.engine._production(connection, run["production_id"])["owner"]
        return self.assets.content_path(owner, asset_id)

    def read_reconciliation_step(self, invocation: ReconciliationInvocation, step_key: str) -> dict | None:
        with self.engine.db.connect() as connection:
            run = self._reconciliation_scope(connection, invocation)
            row = connection.execute("SELECT * FROM steps WHERE run_id=? AND step_key=?", (run["id"], step_key)).fetchone()
            return dict(row) if row else None

    def heartbeat_reconciliation(self, invocation: ReconciliationInvocation) -> None:
        with self.engine.db.transaction() as connection:
            run = self._reconciliation_scope(connection, invocation)
            now = self.engine.clock()
            connection.execute("UPDATE runs SET lease_until_us=? WHERE id=?", (now + RUN_LEASE_SECONDS * 1_000_000, run["id"]))
            connection.execute("UPDATE worker_presence SET heartbeat_us=?,expires_us=? WHERE slot=? AND worker_id=?", (now, now + PRESENCE_TTL_SECONDS * 1_000_000, WORKER_SLOT, invocation.worker_id))

    def observe_reconciled_operation(self, invocation: ReconciliationInvocation, evidence: ReconciliationEvidence,
                                     validator: Callable[[Path, str], MediaProbe]) -> dict:
        target = self.read_reconciliation_target(invocation, evidence.operation_id)
        if tuple(item.attempt_id for item in evidence.files) != tuple(item.attempt_id for item in target.allocations):
            raise EngineError("reconciliation_output_set_conflict", "Evidence must contain the exact ordered full original output set", 409)
        signatures = []
        for allocation, item in zip(target.allocations, evidence.files, strict=True):
            candidate = item.candidate
            if (candidate.staging_id, candidate.media_type, candidate.source, candidate.rights) != (allocation.staging_id, allocation.media_type, allocation.source, allocation.rights):
                raise EngineError("reconciliation_manifest_conflict", "Evidence differs from its original output allocation", 409)
            path = self.assets._path("Staging", allocation.staging_id)
            if not path.is_file() or path.stat().st_size != candidate.size or self.assets._hash(path) != candidate.sha256:
                raise EngineError("reconciliation_file_invalid", "Complete original output is missing or has different bytes", 409, "reconcile")
            if allocation.staging_status in {"ready", "imported"} and (candidate.sha256, candidate.size) != (allocation.sha256, allocation.size):
                raise EngineError("asset_integrity_failed", "Original ready output hash and size are immutable", 422)
            probe = validator(path, candidate.media_type)
            if (not probe.decoded or probe.media_type != candidate.media_type
                    or candidate.media_type.startswith("video/") and (not probe.has_video or not probe.duration_us)
                    or candidate.media_type.startswith("audio/") and (not probe.has_audio or not probe.duration_us)):
                raise EngineError("reconciliation_media_invalid", "Original output does not decode to its fixed media type", 422)
            if path.stat().st_size != candidate.size or self.assets._hash(path) != candidate.sha256:
                raise EngineError("reconciliation_file_changed", "Original output changed during evidence verification", 409)
            details = path.stat()
            signatures.append((path, details.st_size, details.st_mtime_ns, details.st_ctime_ns))
        observation = OperationObservation(status="succeeded", external_id=target.external_id, actual_cost=Money(amount="0"),
                                           cost_evidence="confirmed_no_charge", result_json={"generated_files": [item.model_dump(mode="json") for item in evidence.files]})
        with self.engine.db.transaction() as connection:
            run = self._reconciliation_scope(connection, invocation)
            operation = self.engine._operation(connection, run, evidence.operation_id)
            if operation["status"] == "failed":
                raise EngineError("reconciliation_failed_operation", "A known failed operation cannot be converted to success", 409)
            current = self._reconciliation_target(connection, run, operation)
            if current != target:
                raise EngineError("reconciliation_target_conflict", "Original operation changed before evidence commit", 409)
            for path, size, mtime, ctime in signatures:
                details = path.stat()
                if (details.st_size, details.st_mtime_ns, details.st_ctime_ns) != (size, mtime, ctime):
                    raise EngineError("reconciliation_file_changed", "Original output changed before evidence commit", 409)
            for item in evidence.files:
                connection.execute("UPDATE staging SET sha256=?,size=?,status='ready' WHERE id=? AND status='allocated'", (item.candidate.sha256, item.candidate.size, item.candidate.staging_id))
            result = self.engine._observe_operation(connection, run, invocation.lease, evidence.operation_id, observation, True,
                                                    hold_reconciliation=True)
            return result

    def finish_reconciliation(self, invocation: ReconciliationInvocation) -> ReconciliationOutcome:
        with self.engine.db.transaction() as connection:
            run = self._reconciliation_scope(connection, invocation)
            operations = connection.execute("SELECT status,settled FROM operations WHERE run_id=?", (run["id"],)).fetchall()
            unresolved = any(row["status"] not in {"succeeded", "failed"} or not row["settled"] for row in operations)
            failed = any(row["status"] == "failed" for row in operations)
            if run["status"] in {"failed", "cancelled"}:
                status = run["status"]
            elif unresolved:
                status = "needs_reconciliation"
            elif run["cancellation_requested"] or run["status"] in {"cancelled", "cancel_requested"}:
                status = "cancelled"
            elif failed or run["status"] == "failed":
                status = "failed"
            else:
                status = "queued"
            connection.execute("UPDATE runs SET status=?,worker_id=NULL,lease_until_us=0 WHERE id=?", (status, run["id"]))
            connection.execute("UPDATE productions SET status=? WHERE id=?", (status, run["production_id"]))
            connection.execute("UPDATE worker_presence SET state='idle',active_run_id=NULL WHERE slot=? AND worker_id=?", (WORKER_SLOT, invocation.worker_id))
            self.engine._event(connection, self.engine._run(connection, run["id"]), "reconciliation.finished")
            return ReconciliationOutcome(state=status)

    def allocate_output(self, lease: LeaseGrant, step_key: str, input_sha256: str, output_key: str,
                        media_type: str, source: str, rights: str) -> OutputReservation:
        alignment = step_key.startswith(('repair-alignment-', 'bundle-alignment-'))
        if alignment:
            if (output_key, media_type) != ('alignment-result', 'application/json'):
                raise EngineError('alignment_output_denied', 'Exactly the original single allocated JSON output required', 403)
            original = getattr(self.engine, '_registered_plan_source', None)
            if original is None:
                raise EngineError('alignment_step_denied', 'Actual original alignment source required', 403)
            original.preflight_registered_alignment_step(lease, step_key)
        # Reuse the public candidate string bounds; no filename comes from the caller.
        AssetCandidate(staging_id="validate", sha256=input_sha256, size=1, media_type=media_type, source=source, rights=rights)
        reject_secrets({"source": source, "rights": rights})
        (self.engine.db.data_dir / "Staging").mkdir(exist_ok=True)
        with self.engine.db.transaction() as connection:
            run = self.engine._lease(connection, lease)
            if alignment:
                from video_creator.application.registered_alignment import assert_registered_alignment_step
                assert_registered_alignment_step(connection, self.engine, lease, step_key, input_sha256)
            if not connection.execute("SELECT run_id FROM execution_bindings WHERE run_id=?", (lease.run_id,)).fetchone():
                raise EngineError("execution_binding_missing", "Bind fixed execution inputs before output allocation")
            step = connection.execute("SELECT * FROM steps WHERE run_id=? AND step_key=?", (lease.run_id, step_key)).fetchone()
            if not step or step["input_sha256"] != input_sha256 or step["fencing_token"] != lease.fencing_token:
                raise EngineError("generated_step_conflict", "Generated output requires the current fixed-input step")
            row = connection.execute("SELECT * FROM generated_attempts WHERE run_id=? AND step_key=? AND output_key=?", (lease.run_id, step_key, output_key)).fetchone()
            if row:
                staged = connection.execute("SELECT media_type FROM staging WHERE id=?", (row["staging_id"],)).fetchone()
                if (row["input_sha256"], row["source"], row["rights"], staged[0]) != (input_sha256, source, rights, media_type):
                    raise EngineError("generated_output_conflict", "Output identity already has different fixed inputs")
            else:
                staging_id, attempt_id = identity("staging"), identity("attempt")
                owner = self.engine._production(connection, run["production_id"])["owner"]
                connection.execute("INSERT INTO staging(id,owner,media_type,sha256,size,status) VALUES(?,?,?,'',0,'allocated')", (staging_id, owner, media_type))
                connection.execute("INSERT INTO generated_attempts VALUES(?,?,?,?,?,?,?,?,?)", (attempt_id, lease.run_id, step_key, input_sha256, output_key, staging_id, lease.fencing_token, source, rights))
                row = connection.execute("SELECT * FROM generated_attempts WHERE id=?", (attempt_id,)).fetchone()
            if alignment:
                assert_registered_alignment_step(connection, self.engine, lease, step_key, input_sha256)
        return OutputReservation(attempt_id=row["id"], staging_id=row["staging_id"], run_id=lease.run_id,
                                 step_key=step_key, input_sha256=input_sha256,
                                 partial_path=self.assets._path("Staging", row["staging_id"] + ".partial"),
                                 completed_path=self.assets._path("Staging", row["staging_id"]))

    def _generated(self, connection, lease: LeaseGrant, attempt_id: str):
        run = self.engine._lease(connection, lease)
        row = connection.execute("SELECT a.*,s.owner,s.media_type,s.sha256,s.size,s.status FROM generated_attempts a JOIN staging s ON s.id=a.staging_id WHERE a.id=? AND a.run_id=?", (attempt_id, lease.run_id)).fetchone()
        if not row or row["owner"] != self.engine._production(connection, run["production_id"])["owner"]:
            raise EngineError("generated_output_denied", "Generated output is outside this leased production", 403)
        return row

    def finish_output(self, lease: LeaseGrant, reservation: OutputReservation) -> GeneratedFileManifest:
        with self.engine.db.connect() as connection:
            row = self._generated(connection, lease, reservation.attempt_id)
        alignment = row['step_key'].startswith(('repair-alignment-', 'bundle-alignment-'))
        if alignment:
            original = getattr(self.engine, '_registered_plan_source', None)
            if original is None:
                raise EngineError('alignment_step_denied', 'Actual original alignment source required', 403)
            original.preflight_registered_alignment_step(lease, row['step_key'])
        path = self.assets._path("Staging", row["staging_id"])
        # No caller-supplied path is used. A complete file from a killed attempt
        # is reclaimable only through this exact durable allocation.
        if not path.is_file():
            raise EngineError("generated_file_missing", "Driver must fsync and atomically commit its allocated output first", 409, "reconcile")
        size, sha = path.stat().st_size, self.assets._hash(path)
        candidate = AssetCandidate(staging_id=row["staging_id"], sha256=sha, size=size, media_type=row["media_type"], source=row["source"], rights=row["rights"])
        with self.engine.db.transaction() as connection:
            row = self._generated(connection, lease, reservation.attempt_id)
            if alignment:
                from video_creator.application.registered_alignment import assert_registered_alignment_step
                assert_registered_alignment_step(connection, self.engine, lease, row['step_key'], row['input_sha256'])
            step = connection.execute("SELECT * FROM steps WHERE run_id=? AND step_key=?", (lease.run_id, row["step_key"])).fetchone()
            if not step or step["input_sha256"] != row["input_sha256"] or step["fencing_token"] != lease.fencing_token:
                raise EngineError("generated_step_conflict", "Output no longer belongs to the current step attempt")
            if row["status"] in {"ready", "imported"} and (row["sha256"], row["size"]) != (sha, size):
                raise EngineError("asset_integrity_failed", "Completed output changed after its fixed manifest", 422)
            if row["status"] == "allocated":
                connection.execute("UPDATE staging SET sha256=?,size=?,status='ready' WHERE id=?", (sha, size, row["staging_id"]))
            if alignment:
                assert_registered_alignment_step(connection, self.engine, lease, row['step_key'], row['input_sha256'])
        return GeneratedFileManifest(attempt_id=reservation.attempt_id, candidate=candidate)

    def commit_generated_step(self, lease: LeaseGrant, step_key: str, input_sha256: str,
                              files: tuple[GeneratedFileManifest, ...], result_json: object,
                              validator: Callable[[Path, str], MediaProbe]) -> dict:
        return self._commit_generated_step(lease, step_key, input_sha256, files, result_json, validator)

    def commit_generated_media_step(self, lease: LeaseGrant, step_key: str, input_sha256: str,
                                    files: tuple[GeneratedFileManifest, ...], role_attempt_ids: dict[str, str],
                                    result_json: dict, validator: Callable[[Path, str], MediaProbe]) -> dict:
        self.read_registered_binding(lease)
        allowed = {"video", "narration_audio", "mixed_audio", "cover"}
        if (not isinstance(role_attempt_ids, dict) or not role_attempt_ids or not set(role_attempt_ids) <= allowed
                or any(not isinstance(value, str) for value in role_attempt_ids.values())
                or len(set(role_attempt_ids.values())) != len(role_attempt_ids)
                or set(role_attempt_ids.values()) != {item.attempt_id for item in files}
                or not isinstance(result_json, dict) or "media_roles" in result_json):
            raise EngineError("production_media_roles_invalid", "Roles must select exact original file attempts; caller cannot supply Asset IDs", 422)
        mime_by_role = {"video": "video/mp4", "narration_audio": "audio/wav", "mixed_audio": "audio/wav", "cover": "image/jpeg"}
        indexed = {item.attempt_id: item for item in files}
        if any(indexed[attempt].candidate.media_type != mime_by_role[role] for role, attempt in role_attempt_ids.items()):
            raise EngineError("production_media_roles_invalid", "Each actual output attempt must retain its fixed media role MIME", 422)
        return self._commit_generated_step(lease, step_key, input_sha256, files, result_json, validator, role_attempt_ids)

    def _commit_generated_step(self, lease, step_key, input_sha256, files, result_json, validator, role_attempt_ids=None):
        if step_key.startswith(('repair-alignment-', 'bundle-alignment-')):
            raise EngineError('alignment_output_denied', 'Alignment JSON cannot be imported or decoded as a media Asset', 403)
        if not files or len({item.attempt_id for item in files}) != len(files):
            raise EngineError("generated_files_invalid", "Generated step requires distinct allocated files", 400)
        reject_secrets(result_json)
        with self.engine.db.connect() as connection:
            run = self.engine._lease(connection, lease)
            owner = self.engine._production(connection, run["production_id"])["owner"]
        # Hash, actual decoder and immutable file fsync/rename occur outside DB.
        probes = [self.assets.prepare_candidate(owner, item.candidate, validator) for item in files]
        with self.engine.db.transaction() as connection:
            self.engine._lease(connection, lease)
            step = connection.execute("SELECT * FROM steps WHERE run_id=? AND step_key=?", (lease.run_id, step_key)).fetchone()
            if not step or step["input_sha256"] != input_sha256:
                raise EngineError("step_input_conflict", "Generated step input does not match its fixed input")
            if step["status"] != "succeeded" and step["fencing_token"] != lease.fencing_token:
                raise EngineError("stale_lease", "Generated step belongs to a previous execution attempt")
            operations = connection.execute("SELECT * FROM operations WHERE run_id=? AND step_key=?", (lease.run_id, step_key)).fetchall()
            if not operations or any(row["status"] != "succeeded" or not row["settled"] for row in operations):
                raise EngineError("operation_incomplete", "Generated step requires successful settled operations", retryability="reconcile")
            manifested = []
            for row in operations:
                observation = OperationObservation.model_validate_json(row["observation_json"])
                if isinstance(observation.result_json, dict):
                    manifested.extend(observation.result_json.get("generated_files", []))
            asset_ids = []
            for item, probe in zip(files, probes, strict=True):
                row = self._generated(connection, lease, item.attempt_id)
                if (row["step_key"], row["input_sha256"], row["staging_id"], row["source"], row["rights"]) != (step_key, input_sha256, item.candidate.staging_id, item.candidate.source, item.candidate.rights):
                    raise EngineError("generated_output_conflict", "Generated manifest differs from the durable allocation")
                if item.model_dump(mode="json") not in manifested:
                    raise EngineError("generated_manifest_missing", "Settled operation must persist this exact file manifest first")
                asset_ids.append(self.assets.register_candidate(connection, owner, item.candidate, probe))
            if role_attempt_ids is not None:
                registered = {item.attempt_id: identifier for item, identifier in zip(files, asset_ids, strict=True)}
                result_json = {**result_json, "media_roles": {role: registered[attempt] for role, attempt in role_attempt_ids.items()}}
            return self.engine._complete_step(connection, lease, step_key, tuple(asset_ids), result_json)


@dataclass
class WorkerRuntimeServices:
    engine: EngineService
    worker: WorkerService
    assets: AssetService
    media_validator: Callable[[Path, str], MediaProbe]
    resource_manifest_path: Path
    cancel: threading.Event
    deadline_monotonic: float

    def load_resources(self, invocation: WorkerInvocation | ReconciliationInvocation) -> dict:
        raw = self.resource_manifest_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != invocation.binding.resource_manifest_sha256:
            raise EngineError("worker_resource_conflict", "Trusted resource manifest changed after binding", 409)
        return json.loads(raw)


def run_local_worker(engine: EngineService, resource_manifest_path: Path, manifest_sha256: str,
                     validator: Callable[[Path, str], MediaProbe], driver: Callable,
                     *, reconciliation_driver: Callable | None = None,
                     run_id: str | None = None, max_seconds: int = 300, once: bool = False,
                     control=None, on_ready: Callable[[str], None] | None = None) -> None:
    worker = WorkerService(engine)
    worker_id = worker.register_presence(manifest_sha256)
    deadline = time.monotonic() + max_seconds
    failed = False
    reconciled_runs: set[str] = set()
    try:
        worker.heartbeat_presence(worker_id)
        if on_ready:
            on_ready(worker_id)
        while time.monotonic() < deadline and not (control and control.stop_requested):
            worker.heartbeat_presence(worker_id)
            invocation = worker.reconciliation_invocation(worker_id, manifest_sha256, max(1, int(deadline - time.monotonic())), run_id, reconciled_runs)
            if invocation is not None:
                reconciled_runs.add(invocation.lease.run_id)
            else:
                invocation = worker.invocation(worker_id, manifest_sha256, max(1, int(deadline - time.monotonic())), run_id)
            if invocation is None:
                if once:
                    break
                time.sleep(0.25)
                continue
            cancel, finished = threading.Event(), threading.Event()
            errors = []
            def renew(finished=finished, cancel=cancel, invocation=invocation, errors=errors):
                while not finished.wait(HEARTBEAT_SECONDS):
                    try:
                        if time.monotonic() >= deadline:
                            cancel.set()
                        if isinstance(invocation, ReconciliationInvocation):
                            worker.heartbeat_reconciliation(invocation)
                        else:
                            worker.heartbeat_invocation(invocation)
                    except EngineError as error:
                        errors.append(error.code)
                        cancel.set()
                        return
            heartbeat = threading.Thread(target=renew, name="local-worker-heartbeat")
            heartbeat.start()
            try:
                services = WorkerRuntimeServices(engine, worker, worker.assets, validator, resource_manifest_path, cancel, deadline)
                reconciling = isinstance(invocation, ReconciliationInvocation)
                if reconciling:
                    if reconciliation_driver is None:
                        raise EngineError("reconciliation_driver_missing", "Fixed local evidence driver is not installed", 503)
                    outcome = reconciliation_driver(invocation, services)
                else:
                    outcome = driver(invocation, services)
                if not isinstance(outcome, ReconciliationOutcome if reconciling else WorkerOutcome):
                    raise EngineError("worker_outcome_invalid", "Fixed driver must return its matching internal phase outcome", 503)
                if errors or cancel.is_set() or time.monotonic() >= deadline:
                    raise EngineError("worker_attempt_interrupted", "Attempt lost ownership or exceeded its bounded window", 409)
                if reconciling:
                    actual = worker.finish_reconciliation(invocation)
                    print(json.dumps({"event": "worker.reconciliation_finished", "run_id": invocation.lease.run_id, "status": actual.state}), flush=True)
                else:
                    worker.finish_invocation(invocation, outcome)
            except BaseException:
                cancel.set()
                try:
                    if isinstance(invocation, ReconciliationInvocation):
                        worker.finish_reconciliation(invocation)
                    else:
                        engine.release_run(invocation.lease)
                except EngineError as error:
                    if error.code != "stale_lease":
                        raise
                raise
            finally:
                finished.set()
                heartbeat.join()
            if once:
                break
        if control:
            control.assert_drain_completed()
    except BaseException:
        failed = True
        raise
    finally:
        worker.close_presence(worker_id, failed=failed)
