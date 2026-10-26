"""Candidate Gate0 contracts; generated clients must consume these definitions."""

import re
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from math import gcd
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    field_validator,
    model_serializer,
    model_validator,
)

SCHEMA_VERSION = "0.2.0-candidate"
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
        if isinstance(value, str):
            try:
                parsed = Decimal(value)
            except InvalidOperation:
                raise ValueError("money requires an exact decimal string") from None
            if not parsed.is_finite():
                raise ValueError("money must be a finite decimal")
            return parsed
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
    WAITING_AUTHORIZATION = "waiting_authorization"
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


class DeliveryRequirements(Contract):
    alignment_requirement: Literal["utterance_verified", "word_verified"] = "utterance_verified"
    allowed_degradations: tuple[Literal["word_estimate_with_declared_gap"], ...] = ()

    @model_validator(mode="after")
    def permitted_degradation(self) -> "DeliveryRequirements":
        if len(set(self.allowed_degradations)) != len(self.allowed_degradations):
            raise ValueError("duplicate degradation")
        if self.allowed_degradations and self.alignment_requirement != "word_verified":
            raise ValueError("word degradation requires an explicit word requirement")
        return self


class ProductionRequest(Contract):
    # None is the actual legacy format, never a backfilled 0.2 policy.
    request_format_version: Literal["0.2.0-candidate"] | None = None
    delivery_requirements: DeliveryRequirements | None = None
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

    @model_serializer(mode="wrap")
    def preserve_legacy_body(self, handler):
        body = handler(self)
        for key in ("request_format_version", "delivery_requirements"):
            if body.get(key) is None:
                body.pop(key, None)
        return body

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
    request: "ProductionRequest | ProductionRequestV03"
    cost: ProductionCost
    operations: tuple[OperationSummary, ...]
    revision_cycles: int
    bundle_ref: "BundleRef | None" = None


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
    capability: Literal["text", "image", "video", "speech", "transcription", "alignment", "render", "media_diagnosis"]
    source: Literal["owned_remote", "owned_local", "official"]
    destination: str
    credential_ref: Identifier | None = None
    max_operation_cost: Money
    cost_rule_version: Identifier
    verified: bool = False

    @model_validator(mode="after")
    def destination_boundary(self) -> "CapabilityRoute":
        if self.capability == 'media_diagnosis' and (
                self.source != 'owned_local' or self.credential_ref is not None or self.max_operation_cost.units() != 0):
            raise ValueError('Media diagnosis is strictly local, credential-free and zero-cost')
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


class AssetSummaryV1(Contract):
    asset_id: Identifier
    media_type: str = Field(min_length=1, max_length=100)
    bytes: int = Field(gt=0, strict=True)
    sha256_prefix: str = Field(min_length=12, max_length=12, pattern=r"^[0-9a-f]{12}$")
    source: str = Field(min_length=1, max_length=256)
    created_at_us: int = Field(ge=0, strict=True)


# Collection response convention: collections that can grow (pagination) or
# whose future fields may be added return a named object envelope
# (`assets`, `credentials`); fixed bounded identity lists may return a bare
# array only when their contract model itself is the list. New collection
# endpoints default to an envelope.
class AssetPageV1(Contract):
    assets: tuple[AssetSummaryV1, ...]
    next_cursor: str | None = None


class ProductionRevisionSummary(Contract):
    revision_id: Identifier
    kind: Literal["insight", "brief", "plan", "script", "storyboard", "quality"]
    parent_revision_id: Identifier | None = None
    input_revision_refs: tuple[Identifier, ...] = ()
    body: JsonValue
    expires_at_us: int | None = Field(default=None, gt=0, strict=True)
    failure_code: str | None = Field(default=None, min_length=1, max_length=100)


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


class AssetContentLocator(Contract):
    kind: Literal["asset"] = "asset"
    asset_id: Identifier


class BundleManifestContentLocator(Contract):
    kind: Literal["bundle_manifest"] = "bundle_manifest"
    bundle_ref: BundleRef


class BundleArtifactContentLocator(Contract):
    kind: Literal["bundle_artifact"] = "bundle_artifact"
    bundle_ref: BundleRef
    artifact_id: Identifier


class LocalBundleExportSource(Contract):
    kind: Literal["local_bundle"] = "local_bundle"
    bundle_ref: BundleRef


class LocalImportExportSource(Contract):
    kind: Literal["local_import"] = "local_import"
    import_id: Identifier
    origin_bundle_ref: BundleRef


class ExportArchiveContentLocator(Contract):
    kind: Literal["export_archive"] = "export_archive"
    export_id: Identifier
    source: Annotated[LocalBundleExportSource | LocalImportExportSource, Field(discriminator="kind")]
    input_sha256: Sha256
    delivery_profile: Literal["full", "projection"]
    artifact_ids: tuple[Identifier, ...]

    @field_validator("artifact_ids")
    @classmethod
    def distinct_selection(cls, value):
        if len(set(value)) != len(value):
            raise ValueError("export selection identities must be distinct")
        return value


class ImportManifestContentLocator(Contract):
    kind: Literal["import_manifest"] = "import_manifest"
    import_id: Identifier
    origin_bundle_ref: BundleRef


class ImportArtifactContentLocator(Contract):
    kind: Literal["import_artifact"] = "import_artifact"
    import_id: Identifier
    origin_bundle_ref: BundleRef
    artifact_id: Identifier


class InstallationOwnerPurpose(Contract):
    kind: Literal["installation_owner"] = "installation_owner"


class ContentRequestPurpose(Contract):
    kind: Literal["content_request"] = "content_request"
    purpose: "UsePurpose"


class ExportJournalPurpose(Contract):
    kind: Literal["export_journal"] = "export_journal"
    purpose: "UsePurpose"


class DeliveryContentMetadata(Contract):
    """A current authorized fact snapshot, never a transferable access ticket."""
    schema_kind: Literal["delivery_content_metadata"] = "delivery_content_metadata"
    schema_version: Literal["0.1.0-candidate"] = "0.1.0-candidate"
    local_instance_id: Identifier
    locator: Annotated[AssetContentLocator | BundleManifestContentLocator | BundleArtifactContentLocator |
        ExportArchiveContentLocator | ImportManifestContentLocator | ImportArtifactContentLocator, Field(discriminator="kind")]
    state: Literal["ready"] = "ready"
    sha256: Sha256
    size: int = Field(ge=0, strict=True)
    media_type: str = Field(min_length=1, max_length=200)
    purpose_binding: Annotated[InstallationOwnerPurpose | ContentRequestPurpose | ExportJournalPurpose, Field(discriminator="kind")]
    checked_at_us: int = Field(ge=0, strict=True)
    authorization_expires_at_us: Annotated[int, Field(gt=0, strict=True)] | None

    @model_validator(mode="after")
    def bound_content_identity(self):
        expected = ("installation_owner" if self.locator.kind == "asset" else
                    "export_journal" if self.locator.kind == "export_archive" else "content_request")
        if self.purpose_binding.kind != expected:
            raise ValueError("locator and effective purpose binding must agree")
        reference = getattr(self.locator, "bundle_ref", None)
        if self.locator.kind == "export_archive" and self.locator.source.kind == "local_bundle":
            reference = self.locator.source.bundle_ref
        if reference and reference.instance_id != self.local_instance_id:
            raise ValueError("local bundle reference must belong to the current installation")
        if self.authorization_expires_at_us is not None and self.authorization_expires_at_us <= self.checked_at_us:
            raise ValueError("metadata must reflect a current unexpired authorization path")
        reject_secrets(self.model_dump(mode="json"))
        return self


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


# Bundle1 models below are the only new public source. Legacy SemanticSegment
# remains historical; it cannot be silently promoted to this complete profile.
OutputRole = Literal["video", "narration_audio", "mixed_audio", "approved_script", "actual_transcript", "subtitles", "semantic_manifest", "rag_chunks"]
UsePurpose = Literal["playback", "export", "rag_index", "derivative", "commercial_use", "standalone_audio", "redistribution"]
NonnegativeInt = Annotated[int, Field(ge=0, strict=True)]
PositiveInt = Annotated[int, Field(gt=0, strict=True)]
Confidence = Annotated[Decimal, Field(ge=0, le=1, allow_inf_nan=False)]


class RevisionRef(Contract):
    revision_id: Identifier
    kind: Literal["insight", "brief", "plan", "script", "storyboard", "quality", "feedback"]
    content_sha256: Sha256


class ApprovalRef(Contract):
    run_id: Identifier
    idempotency_key: Identifier
    target_revision_id: Identifier
    decision_sha256: Sha256


class MethodEvidence(Contract):
    method_id: Identifier
    kind: Literal["observed", "model_inference", "user_provided", "derived"]
    tool_name: str = Field(min_length=1, max_length=200)
    tool_version: str = Field(min_length=1, max_length=200)
    build_revision: str | None = Field(default=None, max_length=200)
    model_repository: str | None = Field(default=None, max_length=300)
    model_revision: str | None = Field(default=None, max_length=200)
    resource_manifest_sha256: Sha256 | None = None
    operation_ids: tuple[Identifier, ...] = ()
    input_artifact_ids: tuple[Identifier, ...] = ()
    config_sha256: Sha256
    evidence_artifact_ids: tuple[Identifier, ...] = ()
    limitations: tuple[str, ...] = ()


class RightsSnapshot(Contract):
    rights_id: Identifier
    basis: Literal["owned", "licensed", "user_asserted"]
    holder: str | None = Field(default=None, max_length=300)
    license_identifier: str | None = Field(default=None, max_length=200)
    license_document_artifact_ids: tuple[Identifier, ...] = ()
    permitted_uses: tuple[UsePurpose, ...]
    attribution: str = Field(default="", max_length=4000)
    valid_from_us: NonnegativeInt | None = None
    expires_at_us: PositiveInt | None = None
    platforms: tuple[str, ...] = ()
    territories: tuple[str, ...] = ()
    approval_ref: Identifier | None = None
    limitations: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validity(self) -> "RightsSnapshot":
        if not self.permitted_uses or len(set(self.permitted_uses)) != len(self.permitted_uses):
            raise ValueError("rights require distinct explicit uses")
        if self.expires_at_us is not None and self.valid_from_us is not None and self.expires_at_us <= self.valid_from_us:
            raise ValueError("rights expiry precedes its start")
        return self


class AudioClock(Contract):
    sample_rate: PositiveInt
    decoded_sample_count: PositiveInt
    stream_index: NonnegativeInt = 0
    timebase_num: PositiveInt | None = None
    timebase_den: PositiveInt | None = None
    origin_pts: int | None = Field(default=None, strict=True)

    @model_validator(mode="after")
    def paired_timebase(self) -> "AudioClock":
        if bool(self.timebase_num) != bool(self.timebase_den):
            raise ValueError("timebase numerator and denominator are paired")
        return self


class ArtifactSpec(Contract):
    duration_us: PositiveInt | None = None
    width: PositiveInt | None = None
    height: PositiveInt | None = None
    audio_clock: AudioClock | None = None


class BundleArtifact(Contract):
    artifact_id: Identifier
    asset_id: Identifier | None = None
    material_id: Identifier | None = None
    sha256: Sha256
    size: PositiveInt
    media_type: str = Field(min_length=1, max_length=100)
    relative_path: str = Field(min_length=1, max_length=200)
    roles: tuple[str, ...]
    dependency_artifact_ids: tuple[Identifier, ...] = ()
    method_ref: Identifier
    rights_ref: Identifier
    spec: ArtifactSpec = Field(default_factory=ArtifactSpec)

    @model_validator(mode="after")
    def locator(self) -> "BundleArtifact":
        if bool(self.asset_id) == bool(self.material_id):
            raise ValueError("artifact has exactly one media Asset or controlled text Material")
        text_types = {"application/json", "application/x-ndjson", "text/plain", "text/srt", "text/vtt"}
        if self.media_type in text_types and self.asset_id is not None:
            raise ValueError("bundle text uses controlled Material, not a fabricated media probe")
        if self.media_type not in text_types and self.asset_id is None:
            raise ValueError("media requires a registered Asset")
        parts = self.relative_path.split("/")
        if (len(parts) < 2 or parts[0] not in {"Media", "Creative", "Text", "Semantics", "Checks", "License"}
                or any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,100}", part) or part in {".", ".."} for part in parts)):
            raise ValueError("artifact path must be a bounded package-relative path")
        if not self.roles or len(set(self.roles)) != len(self.roles):
            raise ValueError("artifact roles are explicit and unique")
        return self


class BundleOutput(Contract):
    role: OutputRole
    artifact_ids: tuple[Identifier, ...]
    status: Literal["present"] = "present"
    provenance_revision_refs: tuple[RevisionRef, ...] = ()

    @model_validator(mode="after")
    def complete_references(self) -> "BundleOutput":
        if not self.artifact_ids or len(set(self.artifact_ids)) != len(self.artifact_ids):
            raise ValueError("output requires distinct actual artifacts")
        return self


class AudioTrackRef(Contract):
    asset_id: Identifier
    sha256: Sha256
    stream_index: NonnegativeInt
    kind: Literal["narration", "mix_master", "video_encoded", "dialogue", "music", "effects"]
    intrinsic_duration_us: PositiveInt
    clock: AudioClock
    method_ref: Identifier


class AudioMappingPiece(Contract):
    piece_id: Identifier
    source_track: AudioTrackRef
    source_range: MediaRange
    timeline_range: MediaRange
    playback_rate_num: PositiveInt = 1
    playback_rate_den: PositiveInt = 1
    source_sample_start: NonnegativeInt | None = None
    source_sample_end: PositiveInt | None = None
    source_pts_start: int | None = Field(default=None, strict=True)
    source_pts_end: int | None = Field(default=None, strict=True)
    source_timebase_num: PositiveInt | None = None
    source_timebase_den: PositiveInt | None = None
    transformation: Literal["crop", "place", "resample", "time_stretch", "encode"]
    rounding_policy: Literal["half_up_us"] = "half_up_us"
    start_rounding_error_us: Decimal = Field(default=Decimal(0), gt=-1, lt=1, allow_inf_nan=False)
    end_rounding_error_us: Decimal = Field(default=Decimal(0), gt=-1, lt=1, allow_inf_nan=False)
    method_ref: Identifier

    @model_validator(mode="after")
    def raw_coordinates(self) -> "AudioMappingPiece":
        if gcd(self.playback_rate_num, self.playback_rate_den) != 1:
            raise ValueError("rate must be a reduced positive rational")
        if self.source_range.end_us > self.source_track.intrinsic_duration_us:
            raise ValueError("source range exceeds decoded audio")
        if (self.source_sample_start is None) != (self.source_sample_end is None):
            raise ValueError("sample boundaries are paired")
        if self.source_sample_end is not None and (self.source_sample_end <= self.source_sample_start or self.source_sample_end > self.source_track.clock.decoded_sample_count):
            raise ValueError("sample range is invalid")
        raw = (self.source_pts_start, self.source_pts_end, self.source_timebase_num, self.source_timebase_den)
        if any(value is not None for value in raw) and (any(value is None for value in raw) or self.source_pts_end <= self.source_pts_start):
            raise ValueError("PTS evidence has complete valid rational boundaries")
        if self.source_sample_start is None and self.source_pts_start is None:
            raise ValueError("mapping needs actual sample or PTS evidence")
        return self


class AudioTimelineMapping(Contract):
    mapping_revision_id: Identifier
    target_video_asset_id: Identifier
    target_track: AudioTrackRef
    target_coordinate: Literal["work_timeline"] = "work_timeline"
    timeline_duration_us: PositiveInt
    pieces: tuple[AudioMappingPiece, ...]
    encoding_origin_offset_us: int | None = Field(default=None, strict=True)
    method_ref: Identifier
    content_sha256: Sha256

    @model_validator(mode="after")
    def timeline(self) -> "AudioTimelineMapping":
        if not self.pieces or len({piece.piece_id for piece in self.pieces}) != len(self.pieces):
            raise ValueError("mapping requires distinct pieces")
        if any(piece.timeline_range.end_us > self.timeline_duration_us for piece in self.pieces):
            raise ValueError("mapped audio exceeds work timeline")
        return self


class TranscriptWord(Contract):
    word_id: Identifier
    text: str = Field(min_length=1, max_length=1000)
    intrinsic_range: MediaRange
    timestamp_method: str = Field(min_length=1, max_length=200)
    confidence: Confidence | None = None


class TranscriptUtterance(Contract):
    utterance_id: Identifier
    text: str = Field(min_length=1, max_length=50_000)
    intrinsic_range: MediaRange
    words: tuple[TranscriptWord, ...] = ()

    @model_validator(mode="after")
    def word_bounds(self) -> "TranscriptUtterance":
        if any(word.intrinsic_range.start_us < self.intrinsic_range.start_us or word.intrinsic_range.end_us > self.intrinsic_range.end_us for word in self.words):
            raise ValueError("word range exceeds utterance")
        return self


class TranscriptGap(Contract):
    gap_id: Identifier
    intrinsic_range: MediaRange
    classification: Literal["unintelligible", "no_speech", "music", "not_observed"]
    method_ref: Identifier
    reason: str = Field(min_length=1, max_length=1000)


class PrecisionAssessment(Contract):
    status: Literal["measured", "not_measured", "unavailable"]
    units: Literal["utterance", "word"]
    sample_count: PositiveInt | None = None
    p95_error_us: NonnegativeInt | None = None
    evaluation_material_id: Identifier | None = None
    criterion_version_ref: Identifier | None = None
    limitations: tuple[str, ...] = ()

    @model_validator(mode="after")
    def measurements(self) -> "PrecisionAssessment":
        fields = (self.sample_count, self.p95_error_us, self.evaluation_material_id, self.criterion_version_ref)
        if self.status == "measured" and any(value is None for value in fields):
            raise ValueError("measured precision needs independent report and criterion")
        if self.status != "measured" and any(value is not None for value in fields):
            raise ValueError("unmeasured precision has no fabricated metric")
        return self


class PrecisionBoundaryPair(Contract):
    transcript_unit_id: Identifier
    predicted_range: MediaRange
    reference_range: MediaRange


class PrecisionEvaluationReport(Contract):
    evaluation_id: Identifier
    alignment_revision_id: Identifier
    alignment_content_sha256: Sha256
    input_audio_sha256: Sha256
    units: Literal["utterance", "word"]
    criterion_version_ref: Identifier
    authority_ref: Identifier
    reference_material_id: Identifier
    boundaries: tuple[PrecisionBoundaryPair, ...]
    method_ref: Identifier
    content_sha256: Sha256

    @model_validator(mode="after")
    def samples(self) -> "PrecisionEvaluationReport":
        if not self.boundaries or len({item.transcript_unit_id for item in self.boundaries}) != len(self.boundaries):
            raise ValueError("precision report requires actual distinct comparison samples")
        return self


class AlignmentUnit(Contract):
    unit_id: Identifier
    transcript_unit_id: Identifier
    intrinsic_range: MediaRange


class AlignmentRevision(Contract):
    alignment_revision_id: Identifier
    actual_transcript_revision_id: Identifier
    transcript_content_sha256: Sha256
    input_audio_asset_id: Identifier
    input_audio_sha256: Sha256
    units: Literal["utterance", "word"]
    boundaries: tuple[AlignmentUnit, ...]
    timestamp_method: str = Field(min_length=1, max_length=200)
    method_ref: Identifier
    precision: PrecisionAssessment
    confidence: Confidence | None = None
    confidence_unavailable_reason: str | None = None
    content_sha256: Sha256


class ActualTranscriptRevision(Contract):
    transcript_revision_id: Identifier
    input_audio_asset_id: Identifier
    input_audio_sha256: Sha256
    input_track: AudioTrackRef
    coordinate: Literal["audio_intrinsic"] = "audio_intrinsic"
    duration_us: PositiveInt
    language: str = Field(min_length=1, max_length=30)
    text: str = Field(max_length=500_000)
    utterances: tuple[TranscriptUtterance, ...]
    gaps: tuple[TranscriptGap, ...] = ()
    method_ref: Identifier
    approved_script_revision_ref: RevisionRef
    confidence: Confidence | None = None
    confidence_unavailable_reason: str | None = None
    source_gaps: tuple[str, ...] = ()
    content_sha256: Sha256

    @model_validator(mode="after")
    def actual_audio(self) -> "ActualTranscriptRevision":
        if self.input_track.asset_id != self.input_audio_asset_id or self.input_track.sha256 != self.input_audio_sha256:
            raise ValueError("actual transcript must bind its exact decoded audio")
        if self.duration_us != self.input_track.intrinsic_duration_us:
            raise ValueError("transcript duration differs from actual input")
        if self.text != "".join(utterance.text for utterance in self.utterances):
            raise ValueError("actual text is the complete unchanged utterance sequence")
        if not self.utterances and not self.gaps:
            raise ValueError("empty ASR requires explicit observed gaps, never assumed music")
        if any(unit.intrinsic_range.end_us > self.duration_us for unit in (*self.utterances, *self.gaps)):
            raise ValueError("transcript interval exceeds actual audio")
        if self.confidence is None and not self.confidence_unavailable_reason:
            raise ValueError("absent confidence has an explicit reason")
        return self


class SubtitleCue(Contract):
    cue_id: Identifier
    text: str = Field(min_length=1, max_length=10_000)
    timeline_range: MediaRange
    transcript_unit_refs: tuple[Identifier, ...]
    overlap_declared: bool = False


class SubtitleQuantization(Contract):
    cue_id: Identifier
    start_error_us: int = Field(gt=-1000, lt=1000, strict=True)
    end_error_us: int = Field(gt=-1000, lt=1000, strict=True)


class SubtitleTrack(Contract):
    subtitle_revision_id: Identifier
    actual_transcript_revision_id: Identifier
    alignment_revision_id: Identifier
    mapping_revision_id: Identifier
    coordinate: Literal["work_timeline"] = "work_timeline"
    timeline_duration_us: PositiveInt
    cues: tuple[SubtitleCue, ...]
    srt_artifact_id: Identifier
    vtt_artifact_id: Identifier
    quantization_policy: Literal["subtitle-ms-contain-capped-v1"] = "subtitle-ms-contain-capped-v1"
    quantization_errors: tuple[SubtitleQuantization, ...]
    content_sha256: Sha256

    @model_validator(mode="after")
    def cue_bounds(self) -> "SubtitleTrack":
        if not self.cues or len({cue.cue_id for cue in self.cues}) != len(self.cues):
            raise ValueError("subtitles require distinct actual cues")
        if any(cue.timeline_range.end_us > self.timeline_duration_us for cue in self.cues):
            raise ValueError("subtitle exceeds work timeline")
        if tuple(cue.cue_id for cue in self.cues) != tuple(error.cue_id for error in self.quantization_errors):
            raise ValueError("quantization is recorded for each exact cue")
        return self


class SourceFactRef(Contract):
    foreign_fact_id: Identifier | None = None
    local_fact_id: Identifier | None = None
    text: str = Field(min_length=1, max_length=10_000)
    source_revision: str = Field(min_length=1, max_length=200)
    confirmation_kind: Literal["caller_asserted", "approved", "researched_observation", "inference"]
    approval_ref: Identifier | None = None


class BundleSourceRef(Contract):
    system: Identifier
    namespace: Identifier
    article_id: Identifier | None = None
    article_revision: Identifier | None = None
    topic_id: Identifier | None = None
    topic_revision: Identifier | None = None
    paragraph_ids: tuple[Identifier, ...] = ()
    fact_refs: tuple[SourceFactRef, ...] = ()
    input_asset_ids: tuple[Identifier, ...] = ()
    binding_kind: Literal["provided_input", "researched_source"]
    evidence_refs: tuple[Identifier, ...] = ()
    retrieved_at_us: NonnegativeInt | None = None
    valid_until_us: PositiveInt | None = None

    @model_validator(mode="after")
    def versions(self) -> "BundleSourceRef":
        for key in ("article", "topic"):
            if bool(getattr(self, key + "_id")) != bool(getattr(self, key + "_revision")):
                raise ValueError("source identity and revision are paired")
        return self


class FrameEvidenceRef(Contract):
    video_asset_id: Identifier
    video_sha256: Sha256
    at_us: NonnegativeInt
    actual_pts: int | None = Field(default=None, strict=True)
    timebase_num: PositiveInt | None = None
    timebase_den: PositiveInt | None = None
    decoded_frame_sha256: Sha256
    pixel_format: str = Field(min_length=1, max_length=30)
    width: PositiveInt
    height: PositiveInt
    decoder_method_ref: Identifier
    frame_artifact_id: Identifier | None = None
    limitations: tuple[str, ...] = ()


class SemanticAudioSpan(Contract):
    track: AudioTrackRef
    intrinsic_range: MediaRange
    timeline_range: MediaRange
    mapping_piece_ids: tuple[Identifier, ...]


class SemanticSegmentV1(Contract):
    record_format_version: Literal[1] = 1
    segment_id: Identifier
    bundle_revision_id: Identifier
    video_asset_id: Identifier
    video_range: MediaRange
    audio_spans: tuple[SemanticAudioSpan, ...]
    shot_revision_ids: tuple[Identifier, ...]
    transcript_unit_refs: tuple[Identifier, ...]
    speech_text: str
    visual_description: str
    summary: str
    topic: str
    main_thesis: str
    keywords: tuple[str, ...] = ()
    entities: tuple[dict[str, str], ...] = ()
    source_refs: tuple[BundleSourceRef, ...] = ()
    alignment_revision_id: Identifier
    field_provenance: dict[str, Literal["observed", "model_inference", "user_provided", "derived"]]
    frame_evidence_refs: tuple[FrameEvidenceRef, ...]
    rights_ref: Identifier
    valid_until_us: PositiveInt | None = None
    retrieval_text: str
    content_sha256: Sha256


class RagChunk(Contract):
    record_format_version: Literal[1] = 1
    chunk_id: Identifier
    chunk_type: Literal["work_summary", "speech_segment", "visual_segment"]
    bundle_revision_id: Identifier
    segment_ids: tuple[Identifier, ...]
    text: str = Field(min_length=1, max_length=100_000)
    source_refs: tuple[BundleSourceRef, ...] = ()
    video_ranges: tuple[MediaRange, ...]
    audio_spans: tuple[SemanticAudioSpan, ...] = ()
    language: str
    rights_ref: Identifier
    access_scope_ref: Identifier
    valid_until_us: PositiveInt | None = None
    field_provenance: dict[str, Literal["observed", "model_inference", "user_provided", "derived"]]
    method_refs: tuple[Identifier, ...]
    content_sha256: Sha256


class QualityCheck(Contract):
    check_id: Identifier
    status: Literal["verified", "failed", "not_measured"]
    method_ref: Identifier
    evidence_artifact_ids: tuple[Identifier, ...]
    criterion_version_ref: Identifier | None = None
    findings: tuple[str, ...] = ()


class BundleQualityEvidence(Contract):
    quality_revision_ref: RevisionRef
    checks: tuple[QualityCheck, ...]
    allowed_degradation_approval_ref: ApprovalRef | None = None
    content_sha256: Sha256


class ApprovedScriptDocument(Contract):
    script_revision_ref: RevisionRef
    text: str = Field(min_length=1, max_length=500_000)
    content_sha256: Sha256


class WorkSummary(Contract):
    bundle_revision_id: Identifier
    summary: str = Field(min_length=1, max_length=50_000)
    topic: str = Field(min_length=1, max_length=1000)
    main_thesis: str = Field(min_length=1, max_length=10_000)
    source_refs: tuple[BundleSourceRef, ...]
    content_sha256: Sha256


class SourceBindingsDocument(Contract):
    bundle_revision_id: Identifier
    source_refs: tuple[BundleSourceRef, ...]
    content_sha256: Sha256


class ShotEvidence(Contract):
    shot_revision_id: Identifier
    video_asset_id: Identifier
    timeline_range: MediaRange
    source_refs: tuple[BundleSourceRef, ...]
    frame_evidence_refs: tuple[FrameEvidenceRef, ...]
    content_sha256: Sha256


class ActualTranscriptDocument(Contract):
    transcript: ActualTranscriptRevision
    alignment: AlignmentRevision
    subtitles: SubtitleTrack


class BundleManifest(Contract):
    schema_version: Literal["0.2.0-candidate"] = "0.2.0-candidate"
    bundle_format_version: Literal[1] = 1
    instance_id: Identifier
    bundle_id: Identifier
    bundle_revision_id: Identifier
    project_id: Identifier
    production_id: Identifier
    run_id: Identifier
    request_revision_id: Identifier
    request_sha256: Sha256
    workflow_version: Identifier
    created_at_us: NonnegativeInt
    timeline_duration_us: PositiveInt
    creative_revision_refs: tuple[RevisionRef, ...]
    approval_refs: tuple[ApprovalRef, ...]
    feedback_revision_refs: tuple[RevisionRef, ...] = ()
    source_refs: tuple[BundleSourceRef, ...]
    requested_outputs: tuple[OutputRole, ...]
    outputs: tuple[BundleOutput, ...]
    artifacts: tuple[BundleArtifact, ...]
    audio_mappings: tuple[AudioTimelineMapping, ...]
    methods: tuple[MethodEvidence, ...]
    rights: tuple[RightsSnapshot, ...]
    quality_ref: RevisionRef

    @model_validator(mode="after")
    def indexes(self) -> "BundleManifest":
        artifacts = {item.artifact_id: item for item in self.artifacts}
        if not artifacts or len(artifacts) != len(self.artifacts) or len({item.relative_path.casefold() for item in self.artifacts}) != len(self.artifacts):
            raise ValueError("artifact IDs and normalized paths are unique")
        if len(set(self.requested_outputs)) != len(self.requested_outputs) or {item.role for item in self.outputs} != set(self.requested_outputs) or len(self.outputs) != len(self.requested_outputs):
            raise ValueError("outputs exactly match the fixed requested profile")
        methods, rights = {item.method_id for item in self.methods}, {item.rights_id for item in self.rights}
        if len(methods) != len(self.methods) or len(rights) != len(self.rights):
            raise ValueError("method and rights identities are unique")
        for item in self.artifacts:
            if item.method_ref not in methods or item.rights_ref not in rights or any(ref not in artifacts for ref in item.dependency_artifact_ids):
                raise ValueError("artifact provenance or dependency is missing")
        for output in self.outputs:
            if any(ref not in artifacts for ref in output.artifact_ids):
                raise ValueError("output references an actual indexed artifact")
        pending = {key: set(value.dependency_artifact_ids) for key, value in artifacts.items()}
        done = set()
        while pending:
            ready = {key for key, dependencies in pending.items() if dependencies <= done}
            if not ready:
                raise ValueError("artifact dependencies contain a cycle")
            done.update(ready)
            pending = {key: value for key, value in pending.items() if key not in ready}
        reject_secrets(self.model_dump(mode="json"))
        return self


class BundleExportRequest(Contract):
    delivery_profile: Literal["full", "projection"] = "full"
    format: Literal["zip"] = "zip"
    artifact_ids: tuple[Identifier, ...] = ()
    purpose: UsePurpose = "export"

    @model_validator(mode="after")
    def projection(self) -> "BundleExportRequest":
        if self.delivery_profile == "full" and self.artifact_ids:
            raise ValueError("full export always contains the original complete manifest")
        if self.delivery_profile == "projection" and not self.artifact_ids:
            raise ValueError("projection explicitly selects artifacts")
        return self


class BundleExportAccepted(Contract):
    export_id: Identifier
    bundle_ref: BundleRef
    delivery_profile: Literal["full", "projection"]
    status: Literal["queued", "building", "ready", "failed"]
    input_sha256: Sha256
    status_path: str
    archive_sha256: Sha256 | None = None
    size: PositiveInt | None = None
    content_path: str | None = None
    error_code: str | None = None


class DeliveryProjectionManifest(Contract):
    schema_version: Literal["0.2.0-candidate"] = "0.2.0-candidate"
    delivery_profile: Literal["projection"] = "projection"
    parent_bundle_ref: BundleRef
    artifacts: tuple[BundleArtifact, ...]
    purpose: UsePurpose
    created_at_us: NonnegativeInt


class BundleGrantRequest(Contract):
    recipient_id: Identifier
    artifact_ids: tuple[Identifier, ...]
    allow_semantic_text: bool = False
    purposes: tuple[UsePurpose, ...]
    expires_at_us: PositiveInt


class BundleReferenceGrant(Contract):
    grant_id: Identifier
    bundle_ref: BundleRef
    project_id: Identifier
    recipient_id: Identifier
    artifact_ids: tuple[Identifier, ...]
    allow_semantic_text: bool
    purposes: tuple[UsePurpose, ...]
    created_at_us: NonnegativeInt
    expires_at_us: PositiveInt
    revoked_at_us: NonnegativeInt | None = None


class SemanticPage(Contract):
    bundle_ref: BundleRef
    segments: tuple[SemanticSegmentV1, ...]
    next_cursor: str | None = None


class BundleImportRequest(Contract):
    staging_id: Identifier
    archive_sha256: Sha256
    expected_origin_ref: BundleRef
    project_id: Identifier


class BundleImportReceipt(Contract):
    import_id: Identifier
    local_instance_id: Identifier
    project_id: Identifier
    origin_bundle_ref: BundleRef
    status: Literal["ready"] = "ready"
    status_path: str
    manifest_path: str
    index_state: Literal["not_built", "ready", "failed"] = "not_built"


V03_SCHEMA_VERSION = "0.3.0-candidate"
CONTRACT_SET_VERSION = V03_SCHEMA_VERSION


class EvidencePolicyRevisionRef(Contract):
    policy_id: Identifier
    revision: PositiveInt
    content_sha256: Sha256


class EvidenceReportRef(Contract):
    report_id: Identifier
    schema_version: Literal["0.3.0-candidate"]
    evaluation_scope: Literal["capability_benchmark", "work_runtime_validation", "per_work_reference_measurement",
                              "capability_benchmark_not_performed"]
    content_sha256: Sha256


class PerWorkReportLocator(Contract):
    # A durable address, deliberately not a receipt or a future content hash.
    report_id: Identifier
    artifact_id: Identifier
    material_id: Identifier
    schema_kind: Literal["precision_report_v03"] = "precision_report_v03"


class AlignmentExecutionIdentity(Contract):
    method_id: Identifier
    tool: str = Field(min_length=1, max_length=200)
    tool_version: str = Field(min_length=1, max_length=200)
    model_id: Identifier
    model_file_sha256: dict[Identifier, Sha256]
    resource_manifest_sha256: Sha256
    configuration_sha256: Sha256
    compute_type: str = Field(min_length=1, max_length=100)
    device: str = Field(min_length=1, max_length=100)
    operating_system: str = Field(min_length=1, max_length=100)
    architecture: str = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def actual_resources(self):
        if not self.model_file_sha256:
            raise ValueError("execution identity needs actual model resources")
        return self


class AlignmentApplicability(Contract):
    languages: tuple[str, ...] = Field(min_length=1)
    input_media_types: tuple[str, ...] = Field(min_length=1)
    transformations: tuple[Identifier, ...] = Field(min_length=1)
    maximum_duration_us: PositiveInt
    units: Literal["utterance", "word"]

    @model_validator(mode="after")
    def exact_scope(self):
        for values in (self.languages, self.input_media_types, self.transformations):
            if len(set(values)) != len(values) or any(not value or value == "*" for value in values):
                raise ValueError("applicability is explicit, distinct and bounded")
        return self


class MethodQualificationRef(Contract):
    qualification_id: Identifier
    revision: PositiveInt
    profile_id: Identifier
    profile_revision: PositiveInt
    profile_sha256: Sha256
    execution_identity: AlignmentExecutionIdentity
    applicability: AlignmentApplicability
    benchmark_report_ref: EvidenceReportRef
    criterion_version_ref: Literal["alignment-unit-max-p95-200ms-v1"]
    authority_ref: Identifier
    issuer: Identifier
    approval_refs: tuple[Sha256, ...] = Field(min_length=1)
    valid_from_us: NonnegativeInt
    expires_at_us: PositiveInt
    content_sha256: Sha256

    @model_validator(mode="after")
    def benchmark_scope(self):
        if self.expires_at_us <= self.valid_from_us:
            raise ValueError("qualification binds an actual validity interval")
        if self.benchmark_report_ref.evaluation_scope == "capability_benchmark_not_performed":
            # ADR0082 section 3.4: a "not performed" declaration is admitted only
            # for a local self-issued authority; every other issuer still needs a
            # real capability benchmark.
            if not self.authority_ref.startswith("local-selfissued-authority-"):
                raise ValueError("only a local self-issued authority may bind a not-performed declaration")
        elif self.benchmark_report_ref.evaluation_scope != "capability_benchmark":
            raise ValueError("qualification binds a capability benchmark")
        return self


class EvidencePolicyRevision(Contract):
    policy_id: Identifier
    revision: PositiveInt
    owner_subject: Identifier
    project_id: Identifier | None = None
    alignment_evidence_policy: Literal["strict_reference_v1", "qualified_method_runtime_v1"]
    alignment_requirement: Literal["utterance_verified", "word_verified"]
    qualification_ref: MethodQualificationRef
    required_checks: tuple[Identifier, ...] = Field(min_length=1)
    preauthorized: Literal[True]
    issuer: Identifier
    approval_refs: tuple[Sha256, ...] = Field(min_length=1)
    valid_from_us: NonnegativeInt
    expires_at_us: PositiveInt
    content_sha256: Sha256

    @model_validator(mode="after")
    def policy_scope(self):
        if self.expires_at_us <= self.valid_from_us or len(set(self.required_checks)) != len(self.required_checks):
            raise ValueError("policy interval and checks are explicit")
        return self


class DeliveryRequirementsV03(Contract):
    alignment_requirement: Literal["utterance_verified", "word_verified"]
    allowed_degradations: tuple[Literal["word_estimate_with_declared_gap"], ...] = ()
    alignment_evidence_policy: Literal["strict_reference_v1", "qualified_method_runtime_v1"]
    evidence_policy_revision_ref: EvidencePolicyRevisionRef

    @model_validator(mode="after")
    def no_unapproved_degradation(self):
        if self.allowed_degradations:
            raise ValueError("no word degradation has been admitted for 0.3")
        return self


class ProductionRequestV03(ProductionRequest):
    # Required: absent versions continue through the historical strict parser.
    request_format_version: Literal["0.3.0-candidate"]
    delivery_requirements: DeliveryRequirementsV03 | None = None


class PrecisionAssessmentV03(Contract):
    evaluation_scope: Literal["per_work_reference_measurement"] = "per_work_reference_measurement"
    status: Literal["measured", "not_measured", "unavailable"]
    units: Literal["utterance", "word"]
    sample_count: PositiveInt | None = None
    p95_error_us: NonnegativeInt | None = None
    reference_ref: EvidenceReportRef | None = None
    measurement_report_locator: PerWorkReportLocator | None = None
    criterion_version_ref: Literal["alignment-unit-max-p95-200ms-v1"] | None = None
    limitations: tuple[str, ...] = ()

    @model_validator(mode="after")
    def real_measurement_only(self):
        fields = (self.sample_count, self.p95_error_us, self.reference_ref, self.measurement_report_locator, self.criterion_version_ref)
        if (self.status == "measured") != all(value is not None for value in fields):
            raise ValueError("a measurement requires its independent work reference and durable report address")
        if self.status != "measured" and any(value is not None for value in fields):
            raise ValueError("unmeasured work has null N/P95/reference/report/criterion")
        if self.reference_ref and self.reference_ref.evaluation_scope != "per_work_reference_measurement":
            raise ValueError("a benchmark cannot be a work measurement")
        return self


class AlignmentRevisionV03(AlignmentRevision):
    precision: PrecisionAssessmentV03


class ActualTranscriptDocumentV03(Contract):
    schema_version: Literal["0.3.0-candidate"]
    transcript: ActualTranscriptRevision
    alignment: AlignmentRevisionV03
    subtitles: SubtitleTrack


class PrecisionReferenceUnit(Contract):
    transcript_unit_id: Identifier
    reference_range: MediaRange


class EvidenceAuthorityRevisionRef(Contract):
    authority_id: Identifier
    revision: PositiveInt
    content_sha256: Sha256


class EvidenceMaterialRef(Contract):
    document_id: Identifier
    revision: Identifier
    artifact_id: Identifier
    schema_kind: Literal["audit_summary"]
    sha256: Sha256


class ReferenceSignature(Contract):
    algorithm: Literal["HMAC-SHA256"]
    key_id: Identifier
    digest: Sha256


class PerWorkReferenceDocument(Contract):
    schema_version: Literal["0.3.0-candidate"]
    evaluation_scope: Literal["per_work_reference_measurement"]
    report_id: Identifier
    input_audio_sha256: Sha256
    units: tuple[Identifier, ...] = Field(min_length=1)
    boundaries: tuple[PrecisionReferenceUnit, ...] = Field(min_length=1)
    authority_ref: EvidenceAuthorityRevisionRef
    issuer: Identifier
    independent_listener_refs: tuple[EvidenceMaterialRef, ...] = Field(min_length=1)
    arbitration_ref: EvidenceMaterialRef
    signature: ReferenceSignature
    content_sha256: Sha256

    @model_validator(mode="after")
    def complete_reference(self):
        ids = tuple(item.transcript_unit_id for item in self.boundaries)
        if len(set(self.units)) != len(self.units) or len(set(ids)) != len(ids) or set(ids) != set(self.units):
            raise ValueError("reference declarations and original boundary array are distinct and complete")
        if len({item.artifact_id for item in self.independent_listener_refs}) != len(self.independent_listener_refs):
            raise ValueError("listener source material identities are distinct")
        if self.arbitration_ref.artifact_id in {item.artifact_id for item in self.independent_listener_refs}:
            raise ValueError("arbitration is its own actual immutable source material")
        return self


class CorrectionOriginRef(Contract):
    # Audit locator only; no current method/reference/runtime authorization.
    schema_version: Literal["0.2.0-candidate", "0.3.0-candidate"]
    evaluation_scope: Literal["per_work_reference_measurement"]
    report_id: Identifier
    artifact_id: Identifier
    material_id: Identifier
    sha256: Sha256
    content_sha256: Sha256
    alignment_revision_id: Identifier
    alignment_content_sha256: Sha256


class PrecisionEvaluationReportV03(PrecisionEvaluationReport):
    schema_version: Literal["0.3.0-candidate"]
    evaluation_scope: Literal["per_work_reference_measurement"]
    criterion_version_ref: Literal["alignment-unit-max-p95-200ms-v1"]
    reference_ref: EvidenceReportRef
    sample_count: PositiveInt
    p95_error_us: NonnegativeInt
    corrected_from: CorrectionOriginRef | None = None
    correction_reason: str | None = Field(default=None, min_length=1, max_length=1000)

    @model_validator(mode="after")
    def correction_lineage(self):
        if bool(self.corrected_from) != bool(self.correction_reason):
            raise ValueError("a corrected immutable report retains its origin and reason")
        if self.reference_ref.evaluation_scope != "per_work_reference_measurement":
            raise ValueError("only actual work references measure this work")
        return self


class BenchmarkAudio(Contract):
    audio_id: Identifier
    sha256: Sha256
    coordinate: Literal["audio_intrinsic"]
    duration_us: PositiveInt
    language: str = Field(min_length=1, max_length=30)
    license_ref: Sha256
    reference_ref: Sha256
    predicted_units: tuple[AlignmentUnit, ...] = Field(min_length=1)
    reference_units: tuple[PrecisionReferenceUnit, ...] = Field(min_length=1)
    boundaries: tuple[PrecisionBoundaryPair, ...] = Field(min_length=1)


class MethodBenchmarkReport(Contract):
    schema_version: Literal["0.3.0-candidate"]
    evaluation_scope: Literal["capability_benchmark"]
    report_id: Identifier
    execution_identity: AlignmentExecutionIdentity
    applicability: AlignmentApplicability
    corpus_id: Identifier
    corpus_sha256: Sha256
    audios: tuple[BenchmarkAudio, ...] = Field(min_length=1)
    independent_listener_refs: tuple[Sha256, ...] = Field(min_length=2)
    arbitration_ref: Sha256
    independence_evidence_ref: Sha256
    authority_ref: Identifier
    criterion_version_ref: Literal["alignment-unit-max-p95-200ms-v1"]
    sample_count: PositiveInt
    p95_error_us: NonnegativeInt
    source_gaps: tuple[str, ...] = ()
    content_sha256: Sha256

    @model_validator(mode="after")
    def whole_corpus(self):
        if len({item.audio_id for item in self.audios}) != len(self.audios) or len(set(self.independent_listener_refs)) != len(self.independent_listener_refs):
            raise ValueError("benchmark retains distinct complete corpus and independent listeners")
        return self


LOCAL_SELF_ISSUED_BENCHMARK_LIMITATIONS = (
    "whisper_word_estimate_not_forced_alignment",
    "no_independent_precision_benchmark",
    "self_issued_local_instance_only",
    "not_third_party_certification",
)


class LocalSelfIssuedBenchmarkV1(Contract):
    """ADR0082 section 3.4: a declaration that no benchmark was performed.

    It has no corpus, sample count, P95, listener or arbitration field at all, so
    it cannot be rendered as a measurement. It is admitted only for a local
    self-issued authority and always carries the fixed limitations.
    """

    schema_version: Literal["0.3.0-candidate"]
    evaluation_scope: Literal["capability_benchmark_not_performed"]
    report_id: Identifier
    execution_identity: AlignmentExecutionIdentity
    applicability: AlignmentApplicability
    authority_ref: Identifier
    precision_claim: Literal["not_measured"]
    independent_reference: Literal["none"]
    limitations: tuple[str, ...] = Field(min_length=4)
    disclosure_sha256: Sha256
    content_sha256: Sha256

    @model_validator(mode="after")
    def not_performed(self):
        if not self.authority_ref.startswith("local-selfissued-authority-"):
            raise ValueError("a not-performed declaration exists only for a local self-issued authority")
        if not set(LOCAL_SELF_ISSUED_BENCHMARK_LIMITATIONS) <= set(self.limitations):
            raise ValueError("the declaration retains every fixed limitation")
        return self


class MethodBenchmarkReference(Contract):
    schema_version: Literal["0.3.0-candidate"]
    evidence_trust_status: Literal["reference_only"]
    report_id: Identifier
    origin_report_ref: EvidenceReportRef
    corpus_id: Identifier
    corpus_sha256: Sha256
    execution_identity: AlignmentExecutionIdentity
    applicability: AlignmentApplicability
    criterion_version_ref: Literal["alignment-unit-max-p95-200ms-v1"]
    authority_ref: Identifier
    disclosable_summary: str = Field(min_length=1, max_length=10_000)
    license_ref: Identifier
    acquisition_status: Literal["not_included_license_restricted", "available_separately", "unavailable"]
    acquisition_reference: str | None = Field(default=None, max_length=2000)
    limitations: tuple[str, ...] = Field(min_length=1)
    content_sha256: Sha256

    @model_validator(mode="after")
    def referenced_scope(self):
        if self.origin_report_ref.evaluation_scope != "capability_benchmark":
            raise ValueError("reference document retains the actual benchmark identity")
        return self


class AudioMappingEvidenceRef(Contract):
    mapping_revision_id: Identifier
    content_sha256: Sha256


class WorkAlignmentValidationReport(Contract):
    schema_version: Literal["0.3.0-candidate"]
    evaluation_scope: Literal["work_runtime_validation"]
    report_id: Identifier
    production_id: Identifier
    run_id: Identifier
    request_revision_id: Identifier
    request_sha256: Sha256
    input_audio_asset_id: Identifier
    input_audio_sha256: Sha256
    transcript_revision_id: Identifier
    transcript_content_sha256: Sha256
    alignment_revision_id: Identifier
    alignment_content_sha256: Sha256
    mapping_refs: tuple[AudioMappingEvidenceRef, ...] = Field(min_length=1)
    subtitle_revision_id: Identifier
    subtitle_content_sha256: Sha256
    operation_ids: tuple[Identifier, ...] = Field(min_length=1)
    execution_identity: AlignmentExecutionIdentity
    transformations: tuple[Identifier, ...] = Field(min_length=1)
    evidence_policy_revision_ref: EvidencePolicyRevisionRef
    qualification_ref: MethodQualificationRef
    checks: tuple[QualityCheck, ...] = Field(min_length=1)
    result: Literal["verified", "failed", "incomplete"]
    source_gaps: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()
    content_sha256: Sha256

    @model_validator(mode="after")
    def distinct_observations(self):
        if len(set(self.operation_ids)) != len(self.operation_ids) or len({item.check_id for item in self.checks}) != len(self.checks):
            raise ValueError("work observations and check identities are distinct")
        return self


class BundleQualityEvidenceV03(BundleQualityEvidence):
    schema_version: Literal["0.3.0-candidate"]
    evidence_policy_revision_ref: EvidencePolicyRevisionRef
    qualification_ref: MethodQualificationRef
    work_validation_report_ref: EvidenceReportRef
    per_work_measurement_report_ref: EvidenceReportRef | None = None

    @model_validator(mode="after")
    def distinct_report_scopes(self):
        if self.work_validation_report_ref.evaluation_scope != "work_runtime_validation":
            raise ValueError("quality requires the actual work runtime report")
        if self.per_work_measurement_report_ref and self.per_work_measurement_report_ref.evaluation_scope != "per_work_reference_measurement":
            raise ValueError("a benchmark is not a work measurement")
        if self.allowed_degradation_approval_ref:
            raise ValueError("word degradation is not approved")
        return self


class BundleManifestV03(BundleManifest):
    schema_version: Literal["0.3.0-candidate"]
    evidence_policy_revision_ref: EvidencePolicyRevisionRef
    qualification_ref: MethodQualificationRef
    benchmark_binding: Literal["embedded_full_report", "provenance_reference", "embedded_self_issued"]
    benchmark_document_artifact_id: Identifier
    policy_document_artifact_id: Identifier
    qualification_document_artifact_id: Identifier
    work_validation_document_artifact_id: Identifier

    @model_validator(mode="after")
    def evidence_index(self):
        refs = (self.benchmark_document_artifact_id, self.policy_document_artifact_id, self.qualification_document_artifact_id, self.work_validation_document_artifact_id)
        if len(set(refs)) != len(refs) or not set(refs) <= {item.artifact_id for item in self.artifacts}:
            raise ValueError("all evidence documents have distinct actual indexed artifacts")
        return self


class DeliveryProjectionManifestV03(DeliveryProjectionManifest):
    schema_version: Literal["0.3.0-candidate"]


class BundleImportReceiptV03(BundleImportReceipt):
    evidence_trust_status: Literal["origin_snapshot_only", "locally_recognized_current"] = "origin_snapshot_only"
    execution_qualification_inherited: Literal[False] = False


class CostAmountV1(Contract):
    """A cost fact that cannot silently turn unknown into zero."""

    kind: Literal["confirmed", "unknown", "not_configured"]
    amount: str | None = None
    currency: str | None = None

    @model_validator(mode="after")
    def amount_matches_kind(self) -> "CostAmountV1":
        if self.kind == "confirmed":
            if self.amount is None or self.currency is None:
                raise ValueError("confirmed cost requires amount and currency")
            Decimal(self.amount)
        elif self.amount is not None or self.currency is not None:
            raise ValueError("unknown/not_configured cost has no amount")
        return self


class BudgetSummaryV1(Contract):
    present: bool
    group_id: Identifier | None = None
    authorization: Literal["none", "local_zero_cost", "authorized_cap"]
    cap: CostAmountV1
    spent: CostAmountV1
    reserved: CostAmountV1


class PublishUnavailableV1(Contract):
    status: Literal["unavailable"] = "unavailable"
    code: Literal["publish_unavailable"] = "publish_unavailable"
    reason: str


class CredentialSummaryV1(Contract):
    credential_ref: str
    fingerprint: str
    provider: str
    label: str
    created_at_us: int


class CredentialCreateV1(Contract):
    provider: Identifier
    label: str = Field(min_length=1, max_length=200)
    secret: str = Field(min_length=1, max_length=4096)


class CredentialListV1(Contract):
    """Wrapped collection; a future next_cursor can be added without a break."""

    credentials: tuple[CredentialSummaryV1, ...] = ()


class RouteDecisionV1(Contract):
    capability: str
    route_id: str | None = None
    source_kind: Literal["owned_local", "byok", "official", "unavailable"]
    reason: str


class CapabilitySourceV1(Contract):
    kind: Literal["owned_local", "byok", "official"]
    route_id: str | None = None
    credential_ref: str | None = None
    available: bool
    reason: str


class CapabilityListV1(Contract):
    capabilities: tuple[CapabilitySourceV1, ...] = ()


class ProductionPreviewV1(Contract):
    max_cost: CostAmountV1
    excluded_reasons: tuple[str, ...] = ()
    cost_basis: Literal["confirmed_no_charge", "usage_price_calculation", "unknown"]
    route_decision: tuple[RouteDecisionV1, ...] = ()


ProductionRequestAny = ProductionRequest | ProductionRequestV03
BundleManifestAny = BundleManifest | BundleManifestV03
BundleImportReceiptAny = BundleImportReceipt | BundleImportReceiptV03


def parse_production_request(body: str | dict) -> ProductionRequestAny:
    import json
    value = json.loads(body) if isinstance(body, str) else body
    model = ProductionRequestV03 if value.get("request_format_version") == V03_SCHEMA_VERSION else ProductionRequest
    return model.model_validate(value)


def parse_bundle_manifest(body: str | dict) -> BundleManifestAny:
    import json
    value = json.loads(body) if isinstance(body, str) else body
    if value.get("schema_version") == "0.4.0-candidate":
        from video_creator.domain.local_bundle import BundleManifestLocalV1
        return BundleManifestLocalV1.model_validate(value)
    model = BundleManifestV03 if value.get("schema_version") == V03_SCHEMA_VERSION else BundleManifest
    return model.model_validate(value)


ProductionDetail.model_rebuild()
DeliveryContentMetadata.model_rebuild()
