"""Internal Gate0 worker v1 candidates; not additional public HTTP schemas."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from video_creator.domain.contracts import (
    AssetCandidate,
    CapabilityRoute,
    Identifier,
    LeaseGrant,
    OperationObservation,
    ProductionRequestAny,
    Sha256,
)

WORKFLOW_VERSION = "gate0-local-render-v1"


class InternalModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class BoundAsset(InternalModel):
    asset_id: Identifier
    sha256: Sha256


class ExecutionBinding(InternalModel):
    run_id: Identifier
    production_id: Identifier
    request_revision_id: Identifier
    workflow_version: Literal["gate0-local-render-v1"] = WORKFLOW_VERSION
    input_assets: tuple[BoundAsset, ...]
    resource_manifest_sha256: Sha256


class WorkerInvocation(InternalModel):
    worker_id: Identifier
    lease: LeaseGrant
    binding: ExecutionBinding
    max_attempt_seconds: int = Field(gt=0, le=900)


class OutputReservation(InternalModel):
    attempt_id: Identifier
    staging_id: Identifier
    run_id: Identifier
    step_key: Identifier
    input_sha256: Sha256
    # Trusted in-process handles only; never persisted/exported/returned over HTTP.
    partial_path: Path
    completed_path: Path


class GeneratedFileManifest(InternalModel):
    attempt_id: Identifier
    candidate: AssetCandidate


class WorkerOutcome(InternalModel):
    state: Literal["waiting_user", "released", "needs_reconciliation"]
    # There is intentionally no production/Bundle succeeded result.


class ReconciliationAllocation(InternalModel):
    attempt_id: Identifier
    staging_id: Identifier
    allocation_fence: int = Field(gt=0)
    output_key: Identifier
    media_type: str
    source: str
    rights: str
    staging_status: Literal["allocated", "ready", "imported"]
    sha256: Sha256 | None
    size: int = Field(ge=0)


class ReconciliationTarget(InternalModel):
    operation_id: Identifier
    step_key: Identifier
    input_sha256: Sha256
    step_input_sha256: Sha256
    dedupe_key: Identifier
    route: CapabilityRoute
    external_id: str | None
    status: Literal["prepared", "submitting", "pending", "succeeded", "failed", "unknown"]
    settled: bool
    observation: OperationObservation | None
    allocations: tuple[ReconciliationAllocation, ...]


class ReconciliationInvocation(InternalModel):
    reconciliation_version: Literal["gate0-local-reconciliation-v1"] = "gate0-local-reconciliation-v1"
    worker_id: Identifier
    lease: LeaseGrant
    binding: ExecutionBinding
    request: ProductionRequestAny
    targets: tuple[ReconciliationTarget, ...]
    max_attempt_seconds: int = Field(gt=0, le=900)


class ReconciliationFileHandle(InternalModel):
    allocation: ReconciliationAllocation
    completed_path: Path  # Trusted in-process only; no directory scanning.


class ReconciliationEvidence(InternalModel):
    operation_id: Identifier
    files: tuple[GeneratedFileManifest, ...]


class ReconciliationOutcome(InternalModel):
    state: Literal["queued", "needs_reconciliation", "cancel_requested", "cancelled", "failed"]
