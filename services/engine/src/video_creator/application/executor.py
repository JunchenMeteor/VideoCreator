"""Only this boundary invokes paid drivers; dispatch intent always precedes invocation."""

import json
from collections.abc import Callable, Mapping

from video_creator.application.engine import EngineService, digest
from video_creator.application.pricing import (
    KIMI_K26_RULE,
    normalize_observation,
    validate_kimi_request,
)
from video_creator.domain.contracts import (
    ExecutionPermit,
    LeaseGrant,
    OperationIntent,
    OperationObservation,
)
from video_creator.domain.errors import EngineError
from video_creator.infrastructure.credentials import CredentialVault, SecretHandle


class OperationExecutor:
    def __init__(self, engine: EngineService, vault: CredentialVault | None = None):
        self.engine = engine
        self.vault = vault or CredentialVault()

    def execute(self, lease: LeaseGrant, intent: OperationIntent,
                driver: Callable[[ExecutionPermit, SecretHandle | None], OperationObservation],
                *, request_payload: Mapping[str, object] | None = None) -> OperationObservation:
        configured = self.engine.configured_route(intent.route_id)
        if configured.cost_rule_version == KIMI_K26_RULE:
            if request_payload is None:
                raise EngineError("provider_request_missing", "Kimi dispatch requires the exact bounded request payload", 400)
            bounded_cost = validate_kimi_request(request_payload)
            if intent.reserved_cost.units() < bounded_cost.units():
                raise EngineError("reservation_too_small", "Reservation must cover the Kimi context-window cost bound", 400)
            payload_sha256 = digest(json.dumps(request_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            if intent.input_sha256 != payload_sha256:
                raise EngineError("provider_request_conflict", "Operation input hash differs from the bounded Kimi request", 409)
        operation = self.engine.prepare_operation(lease, intent)
        if operation["settled"]:
            return OperationObservation.model_validate_json(operation["observation_json"])
        if operation["status"] != "prepared":
            raise EngineError("reconciliation_required", "Existing operation cannot be re-submitted", retryability="reconcile")
        # Resolve configuration before the irreversible dispatch boundary.
        route = self.engine.configured_route(intent.route_id)
        secret = self.vault.resolve(route.credential_ref) if route.credential_ref else None
        self.engine.heartbeat(lease, lease_seconds=300)
        permit = self.engine.claim_operation(lease, operation["id"])
        try:
            observation = driver(permit, secret)
            if not isinstance(observation, OperationObservation):
                raise TypeError("Driver must return OperationObservation")
        except Exception:  # noqa: BLE001 - any driver failure after dispatch may represent an accepted charge.
            # A callback may have transmitted the request. No retry and no raw exception body.
            observation = OperationObservation(status="unknown")
        try:
            observation = normalize_observation(observation, permit.route.cost_rule_version)
        except EngineError:
            # Keep received usage/output, but do not invent a numeric charge or release reservation.
            observation = observation.model_copy(update={"actual_cost": None, "cost_evidence": "unknown"})
        self.engine.observe_operation(lease, operation["id"], observation)
        return observation
