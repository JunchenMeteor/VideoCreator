"""Candidate Gate0 contracts; generated clients must consume these definitions."""

import re
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    field_validator,
    model_validator,
)

SCHEMA_VERSION = "0.1.0-candidate"
Identifier = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")]
Sha256 = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


def reject_secrets(value: object) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower().replace("-", "_") in {"api_key", "access_token", "refresh_token", "password", "client_secret", "authorization"}:
                raise ValueError("Secret fields cannot enter persisted or exported content")
            reject_secrets(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            reject_secrets(child)
    elif isinstance(value, str) and re.search(r"\bsk-[A-Za-z0-9_-]{20,}\b", value):
        raise ValueError("API credentials cannot enter persisted or exported content")


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Money(Contract):
    currency: Literal["CNY"] = "CNY"
    amount: Decimal = Field(ge=0, max_digits=18, decimal_places=6)

    @field_validator("amount", mode="before")
    @classmethod
    def fixed_point_input(cls, value: object) -> object:
        if isinstance(value, (float, bool)):
            # Pydantic converts ValueError into a safe validation failure; TypeError would escape.
            raise ValueError("money requires a decimal string, Decimal, or integer")  # noqa: TRY004
        return value

    def units(self) -> int:
        return int(self.amount * 1_000_000)

    @classmethod
    def from_units(cls, units: int) -> "Money":
        return cls(amount=Decimal(units) / 1_000_000)


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_USER = "waiting_user"
    WAITING_PROVIDER = "waiting_provider"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCEL_REQUESTED = "cancel_requested"
    CANCELLED = "cancelled"
    NEEDS_RECONCILIATION = "needs_reconciliation"


class SourceBinding(Contract):
    system: Identifier
    namespace: Identifier
    article_id: Identifier | None = None
    article_revision: Identifier | None = None
    topic_id: Identifier | None = None
    topic_revision: Identifier | None = None
    paragraph_ids: tuple[Identifier, ...] = ()
    confirmed_facts: tuple[str, ...] = ()

    @model_validator(mode="after")
    def fixed_versions(self) -> "SourceBinding":
        for prefix in ("article", "topic"):
            if bool(getattr(self, f"{prefix}_id")) != bool(getattr(self, f"{prefix}_revision")):
                raise ValueError(f"{prefix} identity and revision must be supplied together")
        return self


class ProductionInputs(Contract):
    source_text: str = Field(default="", max_length=500_000)
    asset_ids: tuple[Identifier, ...] = ()


class Automation(Contract):
    mode: Literal["interactive", "unattended"] = "interactive"
    max_revision_cycles: int = Field(default=2, ge=0, le=2)


class ExecutionPolicy(Contract):
    version: Identifier = "local-default-v1"
    allowed_provider_routes: tuple[Identifier, ...] = ()
    external_transfer_allowed: bool = False
    max_cost: Money = Field(default_factory=lambda: Money(amount="0"))
    budget_group_id: Identifier | None = None


class CreativeBriefInput(Contract):
    language: str = "zh-CN"
    target_duration_us: int | None = Field(default=None, gt=0)
    aspect_ratio: Literal["9:16", "16:9"] = "9:16"
    guidance: str | None = Field(default=None, max_length=10_000)


class ProductionRequest(Contract):
    goal: str = Field(min_length=1, max_length=10_000)
    inputs: ProductionInputs = Field(default_factory=ProductionInputs)
    project_id: Identifier | None = None
    source_bindings: tuple[SourceBinding, ...] = ()
    brief: CreativeBriefInput | None = None
    automation: Automation = Field(default_factory=Automation)
    policy: ExecutionPolicy = Field(default_factory=ExecutionPolicy)
    outputs: tuple[Literal["video", "narration_audio", "mixed_audio", "approved_script", "actual_transcript", "subtitles", "semantic_manifest", "rag_chunks"], ...] = (
        "video", "narration_audio", "mixed_audio", "approved_script", "actual_transcript",
        "subtitles", "semantic_manifest", "rag_chunks",
    )
    delivery: Literal["reference", "export"] = "reference"

    @field_validator("goal")
    @classmethod
    def nonblank_goal(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("goal must not be blank")
        return value

    @field_validator("outputs")
    @classmethod
    def unique_outputs(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value or len(set(value)) != len(value):
            raise ValueError("outputs must be nonempty and unique")
        return value

    @model_validator(mode="after")
    def no_secrets(self) -> "ProductionRequest":
        reject_secrets(self.model_dump(mode="json"))
        return self


class ProductionAccepted(Contract):
    schema_version: str = SCHEMA_VERSION
    instance_id: Identifier
    production_id: Identifier
    run_id: Identifier
    project_id: Identifier
    request_revision_id: Identifier
    status: RunStatus
    status_path: str
    events_path: str


class ProjectInput(Contract):
    name: str = Field(default="未命名项目", min_length=1, max_length=200)
    goal: str = Field(default="", max_length=10_000)
    source_text: str = Field(default="", max_length=500_000)

    @model_validator(mode="after")
    def no_secrets(self) -> "ProjectInput":
        reject_secrets(self.model_dump(mode="json"))
        return self


class ProjectDraft(ProjectInput):
    project_id: Identifier
    revision: int = Field(gt=0)
    saved_at_us: int


class OperationSummary(Contract):
    operation_id: Identifier
    status: str
    cost_status: Literal["unknown", "known"]
    actual_cost: Money | None
    cost_evidence: str
    external_id: str | None


class ProductionCost(Contract):
    spent: Money
    reserved: Money


class ProductionDetail(ProductionAccepted):
    request: ProductionRequest
    cost: ProductionCost
    operations: tuple[OperationSummary, ...]
    revision_cycles: int


class StagedAsset(Contract):
    staging_id: Identifier
    sha256: Sha256
    size: int = Field(gt=0)
    media_type: str


class InstanceHealth(Contract):
    instance_id: Identifier
    schema_version: str = SCHEMA_VERSION
    engine_version: str
    mode: Literal["local"] = "local"
    worker_connected: bool


class LeaseGrant(Contract):
    run_id: Identifier
    worker_id: Identifier
    fencing_token: int = Field(gt=0)
    expires_at_us: int = Field(gt=0)


class TaskContext(Contract):
    production_id: Identifier
    run_id: Identifier
    step_key: Identifier
    request_revision_id: Identifier
    input_sha256: Sha256
    policy: ExecutionPolicy


class DelegatedTask(Contract):
    task_key: Identifier
    role: Literal["insight", "writer", "director", "producer", "picture", "sound", "editor", "reviewer"]
    dependencies: tuple[Identifier, ...] = ()
    route_id: Identifier | None = None
    input_refs: tuple[Identifier, ...] = ()
    output_schema: Identifier


class CreativePlan(Contract):
    revision_id: Identifier
    tasks: tuple[DelegatedTask, ...]

    @model_validator(mode="after")
    def acyclic(self) -> "CreativePlan":
        nodes = {task.task_key: set(task.dependencies) for task in self.tasks}
        if len(nodes) != len(self.tasks):
            raise ValueError("duplicate task key")
        completed: set[str] = set()
        while nodes:
            ready = {key for key, dependencies in nodes.items() if dependencies <= completed}
            if not ready:
                raise ValueError("cyclic or missing task dependency")
            completed.update(ready)
            nodes = {key: deps for key, deps in nodes.items() if key not in ready}
        return self


class ReviewDecision(Contract):
    target_revision_id: Identifier
    action: Literal["approve", "revise", "reject"]
    instruction_text: str = Field(default="", max_length=10_000)
    preserved_constraints: tuple[str, ...] = ()


class CapabilityRoute(Contract):
    route_id: Identifier
    capability: Literal["text", "image", "video", "speech", "transcription", "alignment", "render"]
    source: Literal["owned_remote", "owned_local", "official"]
    destination: str
    credential_ref: Identifier | None = None
    max_operation_cost: Money
    cost_rule_version: Identifier
    verified: bool = False

    @model_validator(mode="after")
    def destination_boundary(self) -> "CapabilityRoute":
        parsed = urlsplit(self.destination)
        if self.source == "owned_local" and self.destination.startswith("local:"):
            return self
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("Provider destination must not contain credentials or query parameters")
        if self.source == "owned_local":
            if parsed.scheme not in {"http", "https"} or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
                raise ValueError("Local endpoints must remain on loopback")
        elif parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("Remote destinations require HTTPS")
        return self


class OperationIntent(Contract):
    step_key: Identifier
    dedupe_key: Identifier
    input_sha256: Sha256
    route_id: Identifier
    reserved_cost: Money


class OperationObservation(Contract):
    status: Literal["pending", "succeeded", "failed", "unknown"]
    external_id: str | None = Field(default=None, max_length=256)
    result_asset_ids: tuple[Identifier, ...] = ()
    actual_cost: Money | None = None
    cost_evidence: Literal["provider_receipt", "usage_price_calculation", "confirmed_no_charge", "unknown"] = "unknown"
    usage: dict[str, int] = Field(default_factory=dict)
    result_json: JsonValue | None = None

    @model_validator(mode="after")
    def evidence_matches_cost(self) -> "OperationObservation":
        if (self.actual_cost is None) != (self.cost_evidence == "unknown"):
            raise ValueError("unknown cost must have no numeric actual cost")
        if any(value < 0 for value in self.usage.values()):
            raise ValueError("usage counts cannot be negative")
        reject_secrets(self.result_json)
        return self


class ExecutionPermit(Contract):
    operation_id: Identifier
    run_id: Identifier
    fencing_token: int
    route: CapabilityRoute


class MediaRange(Contract):
    start_us: int = Field(ge=0, strict=True)
    end_us: int = Field(gt=0, strict=True)

    @model_validator(mode="after")
    def half_open(self) -> "MediaRange":
        if self.end_us <= self.start_us:
            raise ValueError("end_us must exceed start_us")
        return self


class MediaProbe(Contract):
    media_type: str
    duration_us: int | None = Field(default=None, gt=0)
    has_video: bool = False
    has_audio: bool = False
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)
    tool_version: str
    decoded: bool


class AssetCandidate(Contract):
    staging_id: Identifier
    sha256: Sha256
    size: int = Field(gt=0)
    media_type: str
    source: str = Field(min_length=1, max_length=256)
    rights: str = Field(min_length=1, max_length=1000)


class AssetRecord(Contract):
    asset_id: Identifier
    sha256: Sha256
    size: int
    media_type: str
    source: str
    rights: str
    probe: MediaProbe


class TimelineClip(Contract):
    asset_id: Identifier
    source_range: MediaRange
    timeline_range: MediaRange
    kind: Literal["video", "audio", "subtitle"]


class Timeline(Contract):
    duration_us: int = Field(gt=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    clips: tuple[TimelineClip, ...]

    @model_validator(mode="after")
    def ranges(self) -> "Timeline":
        if any(clip.timeline_range.end_us > self.duration_us for clip in self.clips):
            raise ValueError("timeline clip exceeds duration")
        return self


class QualityReport(Contract):
    revision_id: Identifier
    asset_ids: tuple[Identifier, ...]
    passed: bool
    method: str
    findings: tuple[str, ...] = ()


class CreativeRevision(Contract):
    revision_id: Identifier
    kind: Literal["insight", "brief", "plan", "script", "storyboard", "quality"]
    parent_revision_id: Identifier | None = None
    input_revision_refs: tuple[Identifier, ...] = ()
    body: JsonValue

    @model_validator(mode="after")
    def no_secrets(self) -> "CreativeRevision":
        reject_secrets(self.body)
        return self


class FeedbackRevision(Contract):
    feedback_id: Identifier
    previous_run_id: Identifier
    new_run_id: Identifier
    target_revision_id: Identifier
    instruction_text: str
    preserved_constraints: tuple[str, ...]


class InsightEvidence(Contract):
    evidence_id: Identifier
    source_ref: str
    source_revision: str
    observation: str
    evidence_kind: Literal["provided_fact", "observed_sample", "inference", "creative_hypothesis"]


class InsightBrief(Contract):
    original_goal: str
    main_thesis: str
    audience: str
    angle: str
    evidence: tuple[InsightEvidence, ...]
    source_gaps: tuple[str, ...] = ()
    preserved_facts: tuple[str, ...] = ()


class ScriptCandidate(Contract):
    candidate_id: Identifier
    title: str
    script: str
    recommendation_reason: str


class StoryboardShot(Contract):
    shot_id: Identifier
    visual: str
    narration: str
    camera: str
    duration_us: int = Field(gt=0)
    source_refs: tuple[Identifier, ...] = ()


class CreativeProposal(Contract):
    insight: InsightBrief
    candidates: tuple[ScriptCandidate, ScriptCandidate, ScriptCandidate]
    selected_candidate_id: Identifier
    shots: tuple[StoryboardShot, StoryboardShot, StoryboardShot]

    @model_validator(mode="after")
    def unique_and_selected(self) -> "CreativeProposal":
        ids = {candidate.candidate_id for candidate in self.candidates}
        if len(ids) != 3 or self.selected_candidate_id not in ids:
            raise ValueError("Three unique candidates and an existing selected ID are required")
        if len({shot.shot_id for shot in self.shots}) != 3:
            raise ValueError("Three distinct shots are required")
        reject_secrets(self.model_dump(mode="json"))
        return self


class ShotRevisionProposal(Contract):
    target_shot_id: Identifier
    revised_shot: StoryboardShot
    preserved_facts: tuple[str, ...]
    unchanged_shot_ids: tuple[Identifier, ...]
    instruction_text: str

    @model_validator(mode="after")
    def targeted(self) -> "ShotRevisionProposal":
        if self.target_shot_id != self.revised_shot.shot_id or self.target_shot_id in self.unchanged_shot_ids:
            raise ValueError("Revision must change only its target shot")
        return self


class BundleRef(Contract):
    instance_id: Identifier
    bundle_id: Identifier
    bundle_revision_id: Identifier
    schema_version: str = SCHEMA_VERSION
    manifest_sha256: Sha256


class SemanticSegment(Contract):
    segment_id: Identifier
    bundle_revision_id: Identifier
    video_asset_id: Identifier
    video_range: MediaRange
    speech_text: str
    visual_description: str
    source_refs: tuple[SourceBinding, ...] = ()


class EventEnvelope(Contract):
    event_id: Identifier
    sequence: int = Field(gt=0)
    production_id: Identifier
    run_id: Identifier
    event_type: str
    occurred_at_us: int
    status: RunStatus
    entity_revision_id: Identifier | None = None


class ErrorEnvelope(Contract):
    code: str
    message: str
    retryability: Literal["never", "safe", "reconcile"]
    request_id: str
