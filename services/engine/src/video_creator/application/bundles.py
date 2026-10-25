"""Instance-owned Bundle1 material journal, publication and scoped delivery."""

import hashlib
import json
import math
import os
import re
import secrets
import threading
import time
import zipfile
from collections.abc import Callable
from dataclasses import replace
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction
from itertools import pairwise
from pathlib import Path

from pydantic import BaseModel, ValidationError

from video_creator.application.alignment_math import LIMIT_US, nearest_rank, unit_errors
from video_creator.application.assets import AssetService
from video_creator.application.bundle_authorization import (
    AUTHORIZATION_PATH,
    BundleProductionAuthorization,
    authorization_refs_body,
    source_policy_body,
    validate_portable_authorization,
)
from video_creator.application.bundle_facts import (
    MAX_CORRECTION_ARTIFACTS,
    MAX_CORRECTION_REPORTS,
    CopiedRightsBinding,
    CorrectionDependencyEdge,
    CorrectionOriginEvidence,
    CorrectionReportSource,
    CorrectionSourceArtifact,
    PreparedRightsAuthority,
    PreparedRightsContext,
    ReadyRightsArtifact,
    VerifiedRightsEvidence,
)
from video_creator.application.current_final_evidence_service import (
    CurrentFinalEvidenceService,
)
from video_creator.application.engine import EngineService, canonical, digest, identity
from video_creator.application.evidence import (
    validate_benchmark,
    validate_self_issued_benchmark,
)
from video_creator.domain import contracts as c
from video_creator.domain import local_bundle as local
from video_creator.domain.bundle import (
    AccessContext,
    BundleContentHandle,
    BundlePreparation,
    BundlePreparationIntent,
    ExportLease,
    MaterialAllocation,
    MaterialReceipt,
    PrincipalRegistration,
    TrustedBundleValidators,
    VerifiedAlignmentEvidence,
    VerifiedBundleMaterial,
)
from video_creator.domain.daily_project_authorization import (
    ProductionAuthorizationDocumentV02,
    ProjectGoalAccepted,
    ProjectGoalInput,
    ProjectGoalReceiptAssociationV1,
    ProjectGoalReceiptQueryV1,
)
from video_creator.domain.errors import EngineError
from video_creator.domain.local_material_production import plan_rights_body
from video_creator.domain.production_authorization import (
    ProductionAdmissionRef,
    ProductionAuthorizationDocument,
)

FULL_OUTPUTS = frozenset(("video", "narration_audio", "mixed_audio", "approved_script", "actual_transcript", "subtitles", "semantic_manifest", "rag_chunks"))
FIXED_FILES = frozenset(("Media/video.mp4", "Media/narration.wav", "Media/mixed-audio.wav", "Media/cover.jpg",
    "Creative/insight.json", "Creative/brief.json", "Creative/production-plan.json", "Text/approved-script.json",
    "Text/actual-transcript.json", "Text/subtitles.srt", "Text/subtitles.vtt", "Semantics/work-summary.json",
    "Semantics/source-bindings.json", "Semantics/shots.jsonl", "Semantics/semantic-segments.jsonl", "Semantics/rag-chunks.jsonl", "Checks/quality-report.json"))
OPERATIONS = frozenset(("bundle.read", "bundle.content", "bundle.export", "bundle.grant", "bundle.revoke", "bundle.import", "bundle.semantic", "production.create", "production.read", "production.review"))
PURPOSES = frozenset(("playback", "export", "rag_index", "derivative", "commercial_use", "standalone_audio", "redistribution"))
TEXT_MODELS = {"creative_revision": c.CreativeRevision, "approved_script": c.ApprovedScriptDocument,
    "actual_transcript": c.ActualTranscriptDocument, "work_summary": c.WorkSummary, "source_bindings": c.SourceBindingsDocument,
    "shots": c.ShotEvidence, "semantic_segments": c.SemanticSegmentV1, "rag_chunks": c.RagChunk,
    "quality": c.BundleQualityEvidence, "precision_report": c.PrecisionEvaluationReport,
    "actual_transcript_v03": c.ActualTranscriptDocumentV03,
    "precision_reference_v03": c.PerWorkReferenceDocument,
    "method_benchmark": c.MethodBenchmarkReport, "method_benchmark_reference": c.MethodBenchmarkReference,
    "method_benchmark_self_issued": c.LocalSelfIssuedBenchmarkV1,
    "method_qualification": c.MethodQualificationRef, "evidence_policy": c.EvidencePolicyRevision,
    "work_alignment_validation": c.WorkAlignmentValidationReport,
    "production_authorization": ProductionAuthorizationDocument}
TEXT_MODELS.update({"local_master_selection": local.LocalMasterSelectionV1,
    "local_speech_evidence": local.LocalSpeechEvidenceV1,
    "actual_transcript_local": local.LocalActualTranscriptDocumentV1,
    "quality_local": local.LocalBundleQualityEvidenceV1,
    "visual_mapping_local": local.LocalVisualMappingDocumentV1,
    "shots_local": local.ShotEvidenceLocalV1,
    "semantic_segments_local": local.SemanticSegmentLocalV2,
    "rag_chunks_local": local.RagChunkLocalV2})


def _text_model(kind, body):
    if not isinstance(body, dict):
        raise EngineError("bundle_text_invalid", "Material JSON root must be an object", 422)
    if kind == "precision_report_v03":
        model = c.PrecisionEvaluationReportV03
    elif kind == "quality" and body.get("schema_version") == c.V03_SCHEMA_VERSION:
        model = c.BundleQualityEvidenceV03
    elif kind == "production_authorization":
        # Version is explicit; old 0.1 canonical provenance stays unchanged.
        models = {'0.1.0-candidate': ProductionAuthorizationDocument,
                  '0.2.0-candidate': ProductionAuthorizationDocumentV02}
        model = models.get(body.get('version', '0.1.0-candidate'))
        if model is None:
            raise EngineError('production_authorization_version_invalid', 'Production authorization version is not admitted', 422)
    else:
        model = TEXT_MODELS.get(kind)
    return model.model_validate(body) if model else body


def strict_json(data: bytes):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result
    def invalid(value):
        raise ValueError("nonfinite JSON")
    def floating(value):
        result = float(value)
        if not math.isfinite(result):
            raise ValueError("nonfinite JSON exponent")
        return result
    try:
        result = json.loads(data.decode("utf-8"), object_pairs_hook=pairs, parse_constant=invalid, parse_float=floating)
        c.reject_secrets(result)
        return result
    except (ValueError, UnicodeError):
        raise EngineError("bundle_text_invalid", "Bundle text is not strict UTF-8 JSON", 422) from None


def record_sha(model: BaseModel) -> str:
    body = model.model_dump(mode="json")
    body.pop("content_sha256", None)
    return digest(json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def check_record(model: BaseModel):
    if hasattr(model, "content_sha256") and record_sha(model) != model.content_sha256:
        raise EngineError("record_hash_invalid", "Semantic or versioned record hash is invalid", 422)


def matches_actual_asr(result, transcript):
    """Bind unchanged ordered text and integer ranges to the settled ASR fact."""
    if (not isinstance(result, dict) or result.get("kind") != "actual_transcript"
            or result.get("input_audio_sha256") != transcript.input_audio_sha256 or result.get("text") != transcript.text):
        return False
    segments = result.get("segments")
    if not isinstance(segments, list) or len(segments) != len(transcript.utterances):
        return False
    def matches(raw, unit):
        return (isinstance(raw, dict) and raw.get("text") == unit.text
            and type(raw.get("start_us")) is int and type(raw.get("end_us")) is int
            and (raw["start_us"], raw["end_us"]) == (unit.intrinsic_range.start_us, unit.intrinsic_range.end_us))
    for raw, utterance in zip(segments, transcript.utterances, strict=True):
        if not matches(raw, utterance):
            return False
        words = raw.get("words", [])
        if (not isinstance(words, list) or len(words) != len(utterance.words)
                or not all(matches(item, word) for item, word in zip(words, utterance.words, strict=True))):
            return False
    return True


def validate_text(data: bytes, kind: str, media_type: str):
    if not data or len(data) > 16 * 1024 * 1024 or b"\r" in data:
        raise EngineError("bundle_text_invalid", "Material must be bounded UTF-8/LF actual text", 422)
    try:
        if kind in {'srt_local', 'vtt_local'}:
            expected_type = 'text/srt' if kind == 'srt_local' else 'text/vtt'
            if media_type != expected_type:
                raise ValueError('local subtitles retain their actual MIME')
            text = data.decode('utf-8')
            c.reject_secrets(text)
            # Parse the explicit zero-cue forms; no arbitrary empty JSON/string
            # is accepted as a missing subtitle document.
            if kind == 'srt_local' and text == '\n':
                return text
            if kind == 'vtt_local' and text == 'WEBVTT\n\n':
                return text
            return validate_text(data, 'srt' if kind == 'srt_local' else 'vtt', media_type)
        if kind == 'production_authorization' and media_type != 'application/json':
            raise ValueError('production authorization has one independent JSON schema')
        if kind in {"license", "srt", "vtt"}:
            text = data.decode("utf-8")
            c.reject_secrets(text)
            if not text.strip():
                raise ValueError("empty text")
            if kind == "vtt" and not text.startswith("WEBVTT\n"):
                raise ValueError("invalid VTT")
            if kind == "srt" and not re.search(r"\d{2}:\d{2}:\d{2},\d{3} -->", text):
                raise ValueError("invalid SRT")
            return text
        if media_type == "application/x-ndjson":
            if not data.endswith(b"\n"):
                raise ValueError("JSONL requires final LF")
            rows = [strict_json(line) for line in data.splitlines()]
            if not rows:
                raise ValueError("empty JSONL")
            values = [_text_model(kind, row) for row in rows]
        else:
            body = strict_json(data)
            values = [_text_model(kind, body)]
        if kind == "audit_summary":
            allowed = {"summary", "findings", "operation_ids", "cost_status", "method_refs", "source_gaps", "reference_boundaries"}
            if any(not isinstance(value, dict) or not set(value) <= allowed for value in values):
                raise ValueError("audit summary fields")
        for value in values:
            if isinstance(value, BaseModel):
                check_record(value)
            if isinstance(value, (c.ActualTranscriptDocument, c.ActualTranscriptDocumentV03)):
                for record in (value.transcript, value.alignment, value.subtitles):
                    check_record(record)
            if isinstance(value, local.LocalActualTranscriptDocumentV1):
                for record in (value.transcript, value.alignment, value.subtitles):
                    if record is not None:
                        check_record(record)
        return values if media_type == "application/x-ndjson" else values[0]
    except (UnicodeError, ValueError, ValidationError):
        raise EngineError("bundle_text_invalid", "Actual material does not satisfy its fixed text schema", 422) from None


class InstancePrincipalRegistry:
    """Only trusted launch configuration binds credentials to distinct principals."""
    def __init__(self, instance_id: str, owner_subject: str = "local-user"):
        self.instance_id, self.owner_subject = instance_id, owner_subject
        self._registrations: dict[str, PrincipalRegistration] = {}
        self._credentials: dict[str, str] = {}
        self._lock = threading.RLock()

    def owner(self) -> AccessContext:
        return AccessContext(self.owner_subject, self.instance_id, frozenset(), OPERATIONS, PURPOSES, owned_projects=True)

    def register(self, registration: PrincipalRegistration, credential: str):
        if registration.principal_id == self.owner_subject or len(credential) < 32:
            raise EngineError("principal_configuration_invalid", "Portal credentials and principal must be distinct from owner", 400)
        with self._lock:
            key = hashlib.sha256(credential.encode()).hexdigest()
            if key in self._credentials and self._credentials[key] != registration.principal_id:
                raise EngineError("principal_configuration_conflict", "Credential identity is already registered", 409)
            self._registrations[registration.principal_id] = registration
            self._credentials[key] = registration.principal_id

    def principal(self, principal_id: str, now_us: int) -> AccessContext:
        with self._lock:
            registration = self._registrations.get(principal_id)
        if not registration:
            raise EngineError("principal_unconfigured", "Recipient principal is not registered in this installation", 503)
        if registration.expires_at_us is not None and registration.expires_at_us <= now_us:
            raise EngineError("principal_expired", "Installation credential has expired", 401)
        return AccessContext(registration.principal_id, self.instance_id, registration.project_ids,
                             registration.operations, registration.purposes, registration.expires_at_us,
                             registration.owned_projects, registration.principal_id)

    def authenticate(self, credential: str, now_us: int) -> AccessContext:
        supplied = hashlib.sha256(credential.encode()).hexdigest()
        with self._lock:
            principal = next((value for key, value in self._credentials.items() if secrets.compare_digest(key, supplied)), None)
        if principal is None:
            raise EngineError("unauthorized", "A registered installation credential is required", 401)
        return self.principal(principal, now_us)


class BundleService(CurrentFinalEvidenceService):
    def __init__(self, engine: EngineService, validators: TrustedBundleValidators | None = None,
                 principals: InstancePrincipalRegistry | None = None,
                 rights_authority: Callable[[c.RightsSnapshot, c.BundleManifest], bool] | None = None,
                 audio_clock_authority: Callable[[c.AudioTrackRef, Path], bool] | None = None,
                 *, prepared_rights_authority: PreparedRightsAuthority | None = None):
        if prepared_rights_authority is not None:
            # ADR0020 admits the protocol, not any actual adapter/configuration.
            raise EngineError("rights_preflight_admission_required", "Prepared rights authority requires formal trusted configuration admission", 503)
        self.engine, self.assets = engine, AssetService(engine)
        self.validators = validators or TrustedBundleValidators()
        self.principals = principals or InstancePrincipalRegistry(engine.instance_id)
        self.rights_authority = rights_authority
        self._rights_facts = {}
        self._correction_facts = {}
        self._copy_source_observations = {}
        self.audio_clock_authority = audio_clock_authority
        self._verified = {}
        self._alignment_verified = {}
        self._final_evidence_ports = {}
        self._final_evidence_assessments = {}
        self._final_evidence_scopes = {}
        self._lock = threading.RLock()
        self._export_stop = threading.Event()
        self._export_thread = None
        self._export_users = 0
        self._production_authorization = BundleProductionAuthorization(self)

    @staticmethod
    def _rights_time(right, now_us, required_uses=()):
        if right.valid_from_us is not None and right.valid_from_us > now_us:
            raise EngineError("bundle_rights_not_started", "Artifact rights are not active yet", 403)
        if right.expires_at_us is not None and right.expires_at_us <= now_us:
            raise EngineError("bundle_rights_expired", "An artifact's rights have expired", 403)
        if not set(required_uses) <= set(right.permitted_uses):
            raise EngineError("bundle_rights_denied", "Actual rights do not permit all requested preparation/delivery uses", 403)

    @staticmethod
    def _assert_owner_right(connection, production_id, right, approval_refs, revision_refs, *,
                            expected_run_id=None):
        references = {ref.revision_id: ref for ref in revision_refs}
        if right.approval_ref not in references:
            raise EngineError("bundle_rights_unverified", "Owner assertion requires its exact indexed immutable creative revision", 403)
        ref = references[right.approval_ref]
        row = connection.execute("SELECT * FROM creative_revisions WHERE id=? AND production_id=?", (ref.revision_id, production_id)).fetchone()
        if not row or row["content_sha256"] != ref.content_sha256:
            raise EngineError("bundle_rights_unverified", "Owner assertion differs from its actual creative version", 403)
        revision = c.CreativeRevision.model_validate_json(row["body"])
        if revision.kind != ref.kind or digest(canonical(revision)) != ref.content_sha256:
            raise EngineError("bundle_rights_unverified", "Owner assertion content or kind changed", 403)
        accepted = []
        for approval in approval_refs:
            if approval.target_revision_id != right.approval_ref:
                continue
            # A rights approval is bound to the exact Run that authored the
            # current execution; another Run's approval cannot authorize it.
            if expected_run_id is not None and approval.run_id != expected_run_id:
                raise EngineError("bundle_approval_conflict",
                                  "Rights approval belongs to a different Run", 409)
            decision = connection.execute("SELECT d.body FROM decisions d JOIN runs r ON r.id=d.run_id WHERE d.run_id=? AND d.idempotency_key=? AND r.production_id=?", (
                approval.run_id, approval.idempotency_key, production_id)).fetchone()
            if not decision or digest(decision[0]) != approval.decision_sha256:
                raise EngineError("bundle_approval_conflict", "Rights approval is not the original persisted decision", 409)
            parsed = c.ReviewDecision.model_validate_json(decision[0])
            if parsed.action != "approve" or parsed.target_revision_id != right.approval_ref:
                raise EngineError("bundle_approval_conflict", "The actual decision did not approve the rights assertion revision", 409)
            accepted.append(approval)
        if not accepted:
            raise EngineError("bundle_rights_unverified", "Rights need an actual owner approval for this exact target revision", 403)
        candidates = plan_rights_body(revision.body)
        if not isinstance(candidates, list):
            raise EngineError("bundle_rights_unverified", "Approved body contains no complete rights declaration list", 403)
        try:
            declarations = tuple(c.RightsSnapshot.model_validate(value) for value in candidates)
        except ValidationError:
            raise EngineError("bundle_rights_unverified", "Approved rights declaration is invalid", 403) from None
        if len({value.rights_id for value in declarations}) != len(declarations) or right not in declarations:
            raise EngineError("bundle_rights_unverified", "Full immutable rights declaration must match exactly, without duplicate IDs", 403)
        return tuple(accepted)

    def _ready_rights_artifacts(self, lease, preparation_id, artifacts):
        if not artifacts or len({item.artifact_id for item in artifacts}) != len(artifacts):
            raise EngineError("rights_artifacts_invalid", "Rights facts require distinct actual ready artifacts", 422)
        with self.engine.db.connect() as connection:
            row, _, production, _ = self._preparation(connection, lease, preparation_id)
            intent = BundlePreparationIntent.model_validate_json(row["intent_json"])
        actual = []
        for artifact in artifacts:
            allocation = receipt = None
            if artifact.asset_id:
                if artifact.asset_id not in intent.media_asset_ids:
                    raise EngineError("bundle_asset_denied", "Rights fact media is outside the exact preparation", 404)
                asset = self.asset(lease, artifact.asset_id)
                if (asset.sha256, asset.size, asset.media_type) != (artifact.sha256, artifact.size, artifact.media_type) or not asset.probe.decoded:
                    raise EngineError("bundle_material_conflict", "Rights fact differs from the actual decoded Asset record", 422)
                path = self.assets.content_path(production["owner"], asset.asset_id)
            else:
                allocation = self.material_allocation(lease, preparation_id, artifact.artifact_id)
                if (allocation.material_id, allocation.relative_path, allocation.media_type) != (artifact.material_id, artifact.relative_path, artifact.media_type):
                    raise EngineError("bundle_material_conflict", "Rights fact differs from the controlled material allocation", 422)
                raw = self.read_material(lease, preparation_id, artifact.material_id)
                if len(raw) != artifact.size or hashlib.sha256(raw).hexdigest() != artifact.sha256:
                    raise EngineError("bundle_integrity_failed", "Rights fact material bytes differ from the actual ready receipt", 422)
                path = self._file("BundleMaterials", artifact.material_id)
                receipt = MaterialReceipt(preparation_id=preparation_id, artifact_id=artifact.artifact_id,
                    material_id=artifact.material_id, sha256=artifact.sha256, size=artifact.size,
                    media_type=allocation.media_type, schema_kind=allocation.schema_kind)
            actual.append(ReadyRightsArtifact(artifact, BundleContentHandle(path, artifact.sha256, artifact.size, artifact.media_type, "derivative"), allocation, receipt))
        return tuple(actual)

    @staticmethod
    def _fact_revisions(connection, production_id, approval_refs, revision_refs):
        if len({(ref.run_id, ref.idempotency_key) for ref in approval_refs}) != len(approval_refs):
            raise EngineError("bundle_approval_conflict", "A rights fact cannot collapse repeated approval identities", 409)
        revisions = {ref.revision_id: ref for ref in revision_refs}
        for ref in revision_refs:
            row = connection.execute("SELECT * FROM creative_revisions WHERE id=? AND production_id=?", (ref.revision_id, production_id)).fetchone()
            if (not row or row["content_sha256"] != ref.content_sha256 or digest(row["body"]) != ref.content_sha256
                    or c.CreativeRevision.model_validate_json(row["body"]).kind != ref.kind):
                raise EngineError("bundle_revision_conflict", "Every supplied rights fact revision must be an actual immutable version", 409)
        for ref in approval_refs:
            row = connection.execute("SELECT d.body FROM decisions d JOIN runs r ON r.id=d.run_id WHERE d.run_id=? AND d.idempotency_key=? AND r.production_id=?", (ref.run_id, ref.idempotency_key, production_id)).fetchone()
            if not row or digest(row[0]) != ref.decision_sha256 or ref.target_revision_id not in revisions:
                raise EngineError("bundle_approval_conflict", "Each supplied approval must match an indexed real decision and target", 409)
            parsed = c.ReviewDecision.model_validate_json(row[0])
            if parsed.action != "approve" or parsed.target_revision_id != ref.target_revision_id:
                raise EngineError("bundle_approval_conflict", "The actual persisted decision did not approve this exact version", 409)

    @staticmethod
    def _minimum_fact_uses(request, artifacts, *, copying=False):
        # These are uses of the actual ready scope, not permission for future files.
        uses = {"derivative", "export"}
        for item in artifacts:
            if set(item.roles) & {"narration_audio", "mixed_audio"}:
                uses.add("standalone_audio")
            if "rag_chunks" in item.roles:
                uses.add("rag_index")
        if copying:
            uses.add("redistribution")
        return uses

    def verify_rights_evidence(self, lease: c.LeaseGrant, preparation_id: str, *,
            rights: tuple[c.RightsSnapshot, ...], approval_refs: tuple[c.ApprovalRef, ...],
            creative_revision_refs: tuple[c.RevisionRef, ...], artifacts: tuple[c.BundleArtifact, ...],
            required_uses: tuple[c.UsePurpose, ...] = ("derivative", "export")) -> VerifiedRightsEvidence:
        if not rights or len({right.rights_id for right in rights}) != len(rights) or len({ref.revision_id for ref in creative_revision_refs}) != len(creative_revision_refs):
            raise EngineError("rights_facts_invalid", "Rights and creative version identities must be distinct and nonempty", 422)
        if not required_uses or len(set(required_uses)) != len(required_uses) or not set(required_uses) <= PURPOSES:
            raise EngineError("rights_use_invalid", "Rights verification uses are distinct existing purposes", 422)
        actual = self._ready_rights_artifacts(lease, preparation_id, artifacts)
        authorization_refs = self._production_authorization.refs_from_ready(lease, actual)
        indexed = {value.artifact.artifact_id: value for value in actual}
        if {item.artifact.rights_ref for item in actual} != {right.rights_id for right in rights}:
            raise EngineError("rights_facts_invalid", "Each provided right must cover actual indexed artifacts, with no unbound right", 422)
        now_us = self.engine.clock()
        accepted, pending = [], []
        with self._production_authorization.guard_for(lease) as guard, self.engine.db.connect() as connection:
            _, run, production, request = self._preparation(connection, lease, preparation_id)
            if not self._minimum_fact_uses(request, artifacts) <= set(required_uses):
                raise EngineError("rights_use_invalid", "Caller cannot reduce the required actual creation/delivery uses", 422)
            self._fact_revisions(connection, production["id"], approval_refs, creative_revision_refs)
            if guard is not None:
                self._production_authorization.assert_local_current(connection, guard, lease, production, authorization_refs)
            for right in rights:
                for values in (right.license_document_artifact_ids, right.platforms, right.territories, right.limitations):
                    if len(set(values)) != len(values):
                        raise EngineError("rights_facts_invalid", "Rights source constraints and license locators must be distinct", 422)
                self._rights_time(right, now_us, required_uses)
                for identifier in right.license_document_artifact_ids:
                    source = indexed.get(identifier)
                    if (not source or not source.receipt or source.receipt.schema_kind != "license"
                            or source.receipt.media_type != "text/plain" or source.artifact.roles != ("license",)):
                        raise EngineError("bundle_license_missing", "Every license source must be an actual ready typed license material", 422)
                if right.basis == "licensed" and not right.license_document_artifact_ids:
                    raise EngineError("bundle_license_missing", "Licensed rights require actual ready license documents", 422)
                if right.basis == "user_asserted":
                    if guard is not None:
                        self._production_authorization.assert_local_current(connection, guard, lease, production, authorization_refs, right=right)
                    else:
                        accepted.extend(self._assert_owner_right(connection, production["id"], right, approval_refs, creative_revision_refs, expected_run_id=lease.run_id))
                else:
                    pending.append("owned/licensed preflight authority is not admitted; legacy final Manifest callback cannot preverify")
        origin_bindings = self._copied_rights_bindings(lease, preparation_id, rights, artifacts, tuple(accepted), required_uses)
        identifiers = tuple(sorted(indexed))
        serialized = {"instance_id": self.engine.instance_id, "production_id": production["id"], "run_id": run["id"],
            "request_revision_id": production["request_revision_id"], "request_sha256": production["request_sha256"],
            "preparation_id": preparation_id, "fencing_token": lease.fencing_token, "checked_at_us": now_us,
            "required_uses": required_uses, "rights": [right.model_dump(mode="json") for right in rights],
            "approvals": [ref.model_dump(mode="json") for ref in approval_refs],
            "revisions": [ref.model_dump(mode="json") for ref in creative_revision_refs],
            "artifacts": [item.artifact.model_dump(mode="json") for item in actual],
            "receipts": [item.receipt.model_dump(mode="json") if item.receipt else None for item in actual],
            "allocations": [item.allocation.model_dump(mode="json") if item.allocation else None for item in actual],
            "subject": production["owner"], "project_id": production["project_id"], "stage": "pre_quality",
            "final_manifest_sha256": None, "origin_bindings": [self._binding_body(value) for value in origin_bindings],
            "production_authorization_refs": authorization_refs_body(authorization_refs)}
        context = PreparedRightsContext(self.engine.instance_id, production["owner"], production["project_id"], production["id"],
            run["id"], production["request_revision_id"], production["request_sha256"], preparation_id, lease.fencing_token,
            now_us, required_uses, rights, approval_refs, creative_revision_refs, actual, "pre_quality", None, origin_bindings,
            digest(json.dumps(serialized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))), authorization_refs)
        check = c.QualityCheck(check_id="rights", status="not_measured" if pending else "verified", method_ref="bundle-rights-v1",
            evidence_artifact_ids=identifiers, findings=tuple(dict.fromkeys(pending)))
        fact = VerifiedRightsEvidence(identity("rights-fact"), context, check, identifiers,
            tuple({(ref.run_id, ref.idempotency_key, ref.target_revision_id, ref.decision_sha256): ref for ref in accepted}.values()),
            ("user_asserted verifies an actual exact Owner declaration through a real human decision or current Owner policy; it is not independent ownership or license certification.", *tuple(dict.fromkeys(pending))))
        with self._lock:
            now = self.engine.clock()
            self._rights_facts = {key: value for key, value in self._rights_facts.items() if value[0] > now}
            self._rights_facts[fact.verification_id] = (lease.expires_at_us, lease, fact)
        return fact

    @staticmethod
    def _source_body(source):
        body = {"bundle_ref": source.source_bundle_ref.model_dump(mode="json"),
            "artifact": source.artifact.model_dump(mode="json"), "rights": source.rights.model_dump(mode="json"),
            "approvals": [ref.model_dump(mode="json") for ref in source.approval_refs],
            "schema_kind": source.schema_kind, "record_content_sha256": source.record_content_sha256}
        if source.source_policy_authorization is not None:
            body["source_policy_authorization"] = source_policy_body(source.source_policy_authorization)
        return body

    @classmethod
    def _binding_body(cls, value):
        body = {"source_bundle_ref": value.source_bundle_ref.model_dump(mode="json"),
            "source_artifact": value.source_artifact.model_dump(mode="json"),
            "source_rights": value.source_rights.model_dump(mode="json"), "source_rights_sha256": value.source_rights_sha256,
            "source_record_sha256": value.source_record_sha256,
            "current_artifact": value.current_artifact.model_dump(mode="json"),
            "current_rights": value.current_rights.model_dump(mode="json"), "license_id_mapping": value.license_id_mapping,
            "current_approval_refs": [ref.model_dump(mode="json") for ref in value.current_approval_refs],
            "required_uses": value.required_uses}
        if value.source_policy_authorization is not None:
            body["source_policy_authorization"] = source_policy_body(value.source_policy_authorization)
        if value.copy_input_admission is not None:
            body["copy_input_admission"] = cls._copy_input_body(value.copy_input_admission)
        return body

    @staticmethod
    def _copy_input_body(fact):
        return {"format": "local-copy-input-admission-v1-adr0028", "binding_id": fact.binding_id,
            "instance_id": fact.instance_id, "owner_subject": fact.owner_subject,
            "destination_project_id": fact.destination_project_id, "production_id": fact.production_id,
            "run_id": fact.run_id, "request_revision_id": fact.request_revision_id,
            "request_sha256": fact.request_sha256, "executing_principal_id": fact.executing_principal_id,
            "registration_sha256": fact.registration_sha256, "policy_ref": fact.policy_ref.model_dump(mode="json"),
            "scope_ref": fact.scope_ref.model_dump(mode="json"), "selection_action_ref": fact.selection_action_ref.model_dump(mode="json"),
            "source_set": fact.source_set.model_dump(mode="json"), "source_set_sha256": fact.source_set_sha256,
            "registry_revision": fact.registry_revision, "fencing_token": fact.fencing_token,
            "checked_at_us": fact.checked_at_us, "valid_until_us": fact.valid_until_us}

    @staticmethod
    def _copy_observation_key(lease, fact):
        return (lease.run_id, lease.worker_id, lease.fencing_token, fact.binding_id,
                canonical(fact.scope_ref), fact.source_set_sha256)

    def _copy_scope_for_sources(self, lease, sources, required_uses):
        """Actual full required closure outside writer; old legal branches keep their None hash."""
        from video_creator.domain.local_copy_input_scope import (
            LocalCopyRequestedRoot,
            member_key,
        )
        with self._production_authorization.guard_for(lease) as guard:
            if guard is None:
                return None
            roots = {}
            with self.engine.db.connect() as connection:
                _, production, _ = self._scope(connection, lease)
                for source in sources:
                    row = connection.execute('SELECT * FROM bundle_revisions WHERE revision_id=? AND manifest_sha256=? AND owner=? AND project_id=?',
                        (source.source_bundle_ref.bundle_revision_id, source.source_bundle_ref.manifest_sha256,
                         production['owner'], production['project_id'])).fetchone()
                    if not row or not row['manifest_json']:
                        raise EngineError('correction_origin_unavailable', 'Actual input source index is unavailable', 409)
                    try:
                        self._production_authorization.assert_current_copy_scope(connection, guard, lease, production,
                            c.parse_bundle_manifest(row['manifest_json']))
                    except EngineError as error:
                        if error.code != 'production_copy_source_scope_missing':
                            raise
                        root = LocalCopyRequestedRoot(bundle_ref=source.source_bundle_ref,
                            artifact_id=source.artifact.artifact_id, handling='copy_into_delivery', required_uses=required_uses)
                        roots[member_key(root)] = root
            if not roots:
                return None
            service = getattr(self.engine, 'local_copy_inputs', None)
            if service is None:
                raise EngineError('production_copy_source_scope_missing', 'Actual Owner input scope management is not configured', 403)
            requested = service.resolve_requested(lease, tuple(roots.values()))
            with self.engine.db.connect() as connection:
                _, production, _ = self._scope(connection, lease)
                fact = service.assert_current_copy_scope(connection, guard, lease, production, requested)
            with self._lock:
                now = self.engine.clock()
                self._copy_source_observations = {key: value for key, value in self._copy_source_observations.items()
                    if value.valid_until_us > now}
                self._copy_source_observations[self._copy_observation_key(lease, fact)] = requested
            return fact

    def _copy_fact_current(self, connection, guard, lease, production, fact):
        service = getattr(self.engine, 'local_copy_inputs', None)
        with self._lock:
            requested = self._copy_source_observations.get(self._copy_observation_key(lease, fact))
        if service is None or requested is None:
            raise EngineError('local_copy_observation_stale', 'Final copy requires its actual sameRun service-issued full source observation', 409)
        current = service.assert_current_copy_scope(connection, guard, lease, production, requested)
        fields = ('binding_id', 'instance_id', 'owner_subject', 'destination_project_id', 'production_id', 'run_id',
                  'request_revision_id', 'request_sha256', 'executing_principal_id', 'registration_sha256',
                  'policy_ref', 'scope_ref', 'selection_action_ref', 'source_set', 'source_set_sha256', 'fencing_token')
        if any(getattr(current, field) != getattr(fact, field) for field in fields):
            raise EngineError('local_copy_binding_conflict', 'Actual initial and final copy scope/binding/full source identity differ', 409)
        return requested

    @classmethod
    def _context_body(cls, context):
        return {"instance_id": context.instance_id, "subject": context.subject, "project_id": context.project_id,
            "production_id": context.production_id, "run_id": context.run_id, "request_revision_id": context.request_revision_id,
            "request_sha256": context.request_sha256, "preparation_id": context.preparation_id, "fencing_token": context.fencing_token,
            "checked_at_us": context.checked_at_us, "required_uses": context.required_uses,
            "rights": [value.model_dump(mode="json") for value in context.rights],
            "approvals": [value.model_dump(mode="json") for value in context.approval_refs],
            "revisions": [value.model_dump(mode="json") for value in context.creative_revision_refs],
            "artifacts": [value.artifact.model_dump(mode="json") for value in context.artifacts],
            "allocations": [value.allocation.model_dump(mode="json") if value.allocation else None for value in context.artifacts],
            "receipts": [value.receipt.model_dump(mode="json") if value.receipt else None for value in context.artifacts],
            "stage": context.stage, "final_manifest_sha256": context.final_manifest_sha256,
            "origin_bindings": [cls._binding_body(value) for value in context.origin_bindings],
            "production_authorization_refs": authorization_refs_body(context.production_authorization_refs)}

    def _final_rights_context(self, lease, preparation_id, manifest, sha, request):
        uses = self._minimum_fact_uses(request, manifest.artifacts)
        with self._lock:
            source_facts = self._correction_facts.get((lease.run_id, lease.worker_id, lease.fencing_token))
        if source_facts and source_facts[0] > self.engine.clock():
            uses.add("redistribution")
        fact = self.verify_rights_evidence(lease, preparation_id, rights=manifest.rights,
            approval_refs=manifest.approval_refs, creative_revision_refs=manifest.creative_revision_refs,
            artifacts=manifest.artifacts, required_uses=tuple(sorted(uses)))
        context = replace(fact.context, stage="final_manifest", final_manifest_sha256=sha, context_sha256="")
        return replace(context, context_sha256=digest(json.dumps(self._context_body(context), ensure_ascii=False, sort_keys=True, separators=(",", ":"))))

    def _origin_bindings_current(self, connection, lease, production, context, *, guard):
        for binding in context.origin_bindings:
            source = binding.source_bundle_ref
            row = connection.execute("SELECT * FROM bundle_revisions WHERE revision_id=? AND bundle_id=? AND manifest_sha256=? AND owner=? AND project_id=?", (
                source.bundle_revision_id, source.bundle_id, source.manifest_sha256, production["owner"], production["project_id"])).fetchone()
            if not row or not row["manifest_json"]:
                raise EngineError("correction_origin_unavailable", "Copied source index is no longer its actual owned immutable source", 409)
            original = c.parse_bundle_manifest(row["manifest_json"])
            if binding.source_artifact not in original.artifacts or binding.source_rights not in original.rights:
                raise EngineError("correction_origin_integrity_failed", "Copied source identity or original declaration changed", 422)
            item = connection.execute("SELECT * FROM bundle_items WHERE preparation_id=? AND artifact_id=? AND status='ready'", (row["id"], binding.source_artifact.artifact_id)).fetchone()
            if (not item or (item["material_id"], item["asset_id"], item["sha256"], item["size"], item["media_type"]) != (
                    binding.source_artifact.material_id, binding.source_artifact.asset_id, binding.source_artifact.sha256,
                    binding.source_artifact.size, binding.source_artifact.media_type)):
                raise EngineError("correction_origin_integrity_failed", "Copied source ready journal changed before publication", 422)
            self._rights_time(binding.source_rights, self.engine.clock(), binding.required_uses)
            self._narrower_copied_right(binding.source_rights, binding.current_rights, dict(binding.license_id_mapping))
            if binding.source_rights.basis != "user_asserted":
                raise EngineError("rights_preflight_admission_required", "Source authority local revocation/configuration store is not yet admitted", 503)
            if binding.source_policy_authorization is not None:
                self._production_authorization.assert_historical_source(connection, lease, original, binding.source_policy_authorization,
                    right=binding.source_rights)
            else:
                self._assert_owner_right(connection, original.production_id, binding.source_rights, original.approval_refs, original.creative_revision_refs, expected_run_id=lease.run_id)
            self._rights_time(binding.current_rights, self.engine.clock(), binding.required_uses)
            if guard is not None:
                self._production_authorization.assert_local_current(connection, guard, lease, production,
                    context.production_authorization_refs, right=binding.current_rights)
                if binding.copy_input_admission is not None:
                    self._copy_fact_current(connection, guard, lease, production, binding.copy_input_admission)
                else:
                    self._production_authorization.assert_current_copy_scope(connection, guard, lease, production, original)
            else:
                self._assert_owner_right(connection, production["id"], binding.current_rights, context.approval_refs, context.creative_revision_refs, expected_run_id=lease.run_id)

    def _origin_files_current(self, lease, context):
        """Fresh full source/proof reads outside the visibility writer."""
        rows, files = {}, {}
        with self.engine.db.connect() as connection:
            _, production, _ = self._scope(connection, lease)
            for binding in context.origin_bindings:
                ref = binding.source_bundle_ref
                key = (ref.bundle_id, ref.bundle_revision_id, ref.manifest_sha256)
                row = connection.execute("SELECT * FROM bundle_revisions WHERE bundle_id=? AND revision_id=? AND manifest_sha256=? AND owner=? AND project_id=?", (
                    *key, production["owner"], production["project_id"])).fetchone()
                if not row or not row["manifest_json"] or not row["manifest_file_key"]:
                    raise EngineError("correction_origin_unavailable", "Current source proof needs its actual owned immutable index", 409)
                rows[key] = dict(row)
                sources = [binding.source_artifact]
                if binding.source_policy_authorization is not None:
                    source = binding.source_policy_authorization
                    sources.extend((source.authorization.artifact, source.plan_artifact))
                for artifact in sources:
                    files[(key, artifact.artifact_id, artifact.material_id, artifact.asset_id)] = (row["owner"], artifact)
        for row in rows.values():
            path = self._file("BundleManifests", row["manifest_file_key"])
            if not path.is_file() or path.read_bytes() != row["manifest_json"].encode() or self.assets._hash(path) != row["manifest_sha256"]:
                raise EngineError("correction_origin_integrity_failed", "Source immutable Manifest bytes changed after preflight", 422)
        for owner, artifact in files.values():
            path = self._artifact_path(owner, artifact)
            if not path.is_file() or path.stat().st_size != artifact.size or self.assets._hash(path) != artifact.sha256:
                raise EngineError("correction_origin_integrity_failed", "Source/proof bytes changed after preflight", 422)
        observed = set()
        for binding in context.origin_bindings:
            fact = binding.copy_input_admission
            if fact is None:
                continue
            key = self._copy_observation_key(lease, fact)
            if key in observed:
                continue
            observed.add(key)
            with self._lock:
                requested = self._copy_source_observations.get(key)
            service = getattr(self.engine, 'local_copy_inputs', None)
            if service is None or requested is None:
                raise EngineError('local_copy_observation_stale', 'Current input proof closure must be reverified before publication', 409)
            service.resolver.recheck_files(requested)  # Full hashes outside visibility writer.

    @staticmethod
    def _narrower_copied_right(source, current, mapping):
        if (current.basis != source.basis or current.holder != source.holder
                or current.license_identifier != source.license_identifier or current.attribution != source.attribution
                or not set(current.permitted_uses) <= set(source.permitted_uses)
                or not set(source.limitations) <= set(current.limitations)
                or not set(mapping.values()) <= set(current.license_document_artifact_ids)):
            raise EngineError("correction_rights_widened", "Current copied declaration must preserve source identity, license mapping and constraints", 403)
        for old_values, new_values in ((source.platforms, current.platforms), (source.territories, current.territories)):
            if old_values and (not new_values or not set(new_values) <= set(old_values)):
                raise EngineError("correction_rights_widened", "Copied source platform/territory restrictions cannot be broadened", 403)
        if ((source.expires_at_us is not None and (current.expires_at_us is None or current.expires_at_us > source.expires_at_us))
                or (source.valid_from_us is not None and (current.valid_from_us is None or current.valid_from_us < source.valid_from_us))):
            raise EngineError("correction_rights_widened", "Copied rights validity cannot exceed the actual source permission", 403)

    def _historical_copy_requires_facts(self, historical, facts) -> bool:
        """Only correction/copy paths treat a historical identity match as a copy.

        Local artifact ids are deterministic (`_identity('local-media', role,
        asset_id)`), so an ordinary second run regenerates the same id/sha from
        the same input masters. A true copy is distinguished by being in the
        correction-facts path or the current-final-evidence/copy scope.
        """
        return bool(historical) and (bool(facts) or self._in_current_final_evidence())

    def _copied_rights_bindings(self, lease, preparation_id, rights, artifacts, approvals, required_uses):
        with self._lock:
            facts = self._correction_facts.get((lease.run_id, lease.worker_id, lease.fencing_token))
        sources = {}
        if facts and facts[0] > self.engine.clock():
            for value in facts[1]:
                for source in (*(item.source for item in value.reports), *value.license_documents,
                        *(edge.indexed_child for edge in value.dependency_edges)):
                    candidates = sources.setdefault(source.artifact.artifact_id, [])
                    if any((old.artifact.sha256, old.schema_kind, old.record_content_sha256) != (
                            source.artifact.sha256, source.schema_kind, source.record_content_sha256) for old in candidates):
                        raise EngineError("correction_artifact_conflict", "Source copies cannot collapse different bytes, grammar or record identity", 422)
                    if source not in candidates:
                        candidates.append(source)
        current_artifacts = {item.artifact_id: item for item in artifacts}
        current_rights = {right.rights_id: right for right in rights}
        selected_sources = tuple(source for identifier, values in sources.items() if identifier in current_artifacts for source in values)
        copy_fact = self._copy_scope_for_sources(lease, selected_sources, required_uses) if selected_sources else None
        bindings = []
        for item in artifacts:
            candidates = sources.get(item.artifact_id)
            with self.engine.db.connect() as connection:
                _, _, production, _ = self._preparation(connection, lease, preparation_id)
                historical = connection.execute("SELECT 1 FROM bundle_items i JOIN bundle_revisions b ON b.id=i.preparation_id WHERE i.artifact_id=? AND i.sha256=? AND i.status='ready' AND b.id!=? AND b.owner=? AND b.project_id=? AND b.manifest_json IS NOT NULL LIMIT 1", (
                    item.artifact_id, item.sha256, preparation_id, production["owner"], production["project_id"])).fetchone()
            if not candidates:
                if self._historical_copy_requires_facts(historical, facts):
                    raise EngineError("correction_evidence_required", "A historical copy needs current service-issued complete source facts", 409)
                continue
            for source in candidates:
                if (item.sha256, item.size, item.media_type) != (source.artifact.sha256, source.artifact.size, source.artifact.media_type):
                    raise EngineError("correction_origin_integrity_failed", "Copy must retain its source's exact immutable bytes", 422)
                mapping = {}
                for key in source.rights.license_document_artifact_ids:
                    originals = sources.get(key)
                    target = current_artifacts.get(key)
                    if (not originals or not target or target.roles != ("license",)
                            or any(target.sha256 != original.artifact.sha256 for original in originals)):
                        raise EngineError("bundle_license_missing", "Every copied source license needs its actual new ready indexed copy", 422)
                    mapping[key] = target.artifact_id
                current = current_rights[item.rights_ref]
                self._narrower_copied_right(source.rights, current, mapping)
                with self._production_authorization.guard_for(lease) as guard, self.engine.db.connect() as connection:
                    _, _, production, _ = self._preparation(connection, lease, preparation_id)
                    origin = connection.execute("SELECT * FROM bundle_revisions WHERE revision_id=? AND manifest_sha256=? AND owner=? AND project_id=?", (
                        source.source_bundle_ref.bundle_revision_id, source.source_bundle_ref.manifest_sha256, production["owner"], production["project_id"])).fetchone()
                    if not origin or not origin["manifest_json"]:
                        raise EngineError("correction_origin_unavailable", "Source input scope needs its actual local immutable index", 409)
                    if guard is not None:
                        if copy_fact is not None:
                            self._copy_fact_current(connection, guard, lease, production, copy_fact)
                        else:
                            self._production_authorization.assert_current_copy_scope(connection, guard, lease, production,
                                c.parse_bundle_manifest(origin["manifest_json"]))
                # Effective validity also includes each actual license source
                # and its own necessary permission/dependency closure.
                dependency_ids, checked = list(source.rights.license_document_artifact_ids), set()
                while dependency_ids:
                    key = dependency_ids.pop()
                    if key in checked:
                        continue
                    checked.add(key)
                    dependencies = sources.get(key)
                    if not dependencies:
                        raise EngineError("bundle_license_missing", "Copied permission dependency is missing from complete source facts", 422)
                    for dependency in dependencies:
                        boundary = dependency.rights
                        if ((boundary.expires_at_us is not None and (current.expires_at_us is None or current.expires_at_us > boundary.expires_at_us))
                                or (boundary.valid_from_us is not None and (current.valid_from_us is None or current.valid_from_us < boundary.valid_from_us))):
                            raise EngineError("correction_rights_widened", "Copied effective validity cannot exceed any required source permission", 403)
                        dependency_ids.extend((*boundary.license_document_artifact_ids, *dependency.artifact.dependency_artifact_ids))
                if "redistribution" not in required_uses:
                    raise EngineError("rights_use_invalid", "Portable original/permission copies require actual redistribution permission", 422)
                self._rights_time(source.rights, self.engine.clock(), required_uses)
                bindings.append(CopiedRightsBinding(source.source_bundle_ref, source.artifact, source.rights,
                    digest(canonical(source.rights)), source.record_content_sha256, item, current, tuple(mapping.items()),
                    tuple(ref for ref in approvals if ref.target_revision_id == current.approval_ref), required_uses,
                    source.source_policy_authorization, copy_fact))
        return tuple(bindings)

    def _file(self, folder: str, key: str) -> Path:
        return self.assets._path(folder, key)

    def _write(self, folder: str, key: str, data: bytes):
        root = self.engine.db.data_dir / folder
        root.mkdir(exist_ok=True)
        path = self._file(folder, key)
        expected = hashlib.sha256(data).hexdigest()
        if path.exists():
            if self.assets._hash(path) != expected or path.stat().st_size != len(data):
                raise EngineError("bundle_file_conflict", "Immutable bundle file already has different content", 409, "reconcile")
            return path
        partial = self._file(folder, key + ".partial")
        # An original interrupted write is never accepted as completed evidence.
        if partial.exists():
            if partial.stat().st_size != len(data) or self.assets._hash(partial) != expected:
                raise EngineError("bundle_partial_conflict", "Original partial file needs explicit reconciliation", 409, "reconcile")
        else:
            with partial.open("xb") as output:
                output.write(data)
                output.flush()
                os.fsync(output.fileno())
        os.replace(partial, path)
        if self.assets._hash(path) != expected:
            raise EngineError("bundle_file_invalid", "Committed file does not match its fixed bytes", 422)
        return path

    def _scope(self, connection, lease: c.LeaseGrant):
        run = self.engine._lease(connection, lease)
        production = self.engine._production(connection, run["production_id"])
        request = c.parse_production_request(production["request_json"])
        local_source = self._local_source(required=False)
        if run["paused"] or (local_source is None and (
                request.request_format_version not in {c.SCHEMA_VERSION, c.V03_SCHEMA_VERSION}
                or set(request.outputs) != FULL_OUTPUTS)):
            raise EngineError("bundle_profile_unavailable", "A fixed new full-eight-output request and unpaused ordinary lease are required", 409)
        self.engine._evidence_execution_guard(connection, production, request)
        return run, production, request

    def _local_source(self, *, required=True):
        from video_creator.application.local_material_sources import (
            LocalMaterialSourceService,
        )
        from video_creator.domain.local_material_production import (
            RegistrationConfigLocalV1,
        )
        source = getattr(self.engine, '_local_material_plan_source', None)
        if source is None and not required:
            return None
        if (type(source) is not LocalMaterialSourceService or source.engine is not self.engine
                or source.bundle is not self or source.runtime.bundle is not self
                or type(source.runtime.config) is not RegistrationConfigLocalV1):
            raise EngineError('local_bundle_source_denied', 'Original same Engine installed local source is required.', 403)
        return source

    def _preparation(self, connection, lease, preparation_id):
        run, production, request = self._scope(connection, lease)
        row = connection.execute("SELECT * FROM bundle_revisions WHERE id=? AND run_id=? AND owner=?", (preparation_id, run["id"], production["owner"])).fetchone()
        if not row or row["request_revision_id"] != production["request_revision_id"]:
            raise EngineError("bundle_preparation_denied", "Preparation is outside this fixed run", 404)
        return row, run, production, request

    def _snapshot(self, connection, row):
        items = connection.execute("SELECT * FROM bundle_items WHERE preparation_id=? AND material_id IS NOT NULL AND status='ready' ORDER BY rowid", (row["id"],)).fetchall()
        receipts = tuple(MaterialReceipt(preparation_id=row["id"], artifact_id=item["artifact_id"], material_id=item["material_id"],
                          sha256=item["sha256"], size=item["size"], media_type=item["media_type"], schema_kind=item["schema_kind"]) for item in items)
        return BundlePreparation(preparation_id=row["id"], bundle_id=row["bundle_id"], bundle_revision_id=row["revision_id"],
                    input_sha256=row["input_sha256"], state=row["status"], materials=receipts, manifest_sha256=row["manifest_sha256"])

    def asset(self, lease: c.LeaseGrant, asset_id: str) -> c.AssetRecord:
        with self.engine.db.connect() as connection:
            run = self.engine._lease(connection, lease, allow_cancel=True)
            production = self.engine._production(connection, run["production_id"])
            request = c.parse_production_request(production["request_json"])
            rows = connection.execute("SELECT result_json FROM steps s JOIN runs r ON r.id=s.run_id WHERE r.production_id=? AND s.status='succeeded'", (production["id"],)).fetchall()
            allowed = set(request.inputs.asset_ids)
            for row in rows:
                allowed.update(json.loads(row[0]).get("asset_ids", []))
            if asset_id not in allowed:
                raise EngineError("bundle_asset_denied", "Asset is outside this production's fixed input or committed results", 403)
        return self.assets.get(production["owner"], asset_id)

    def content_path(self, lease: c.LeaseGrant, asset_id: str) -> Path:
        self.asset(lease, asset_id)
        with self.engine.db.connect() as connection:
            run = self.engine._lease(connection, lease, allow_cancel=True)
            owner = self.engine._production(connection, run["production_id"])["owner"]
        return self.assets.content_path(owner, asset_id)

    def context(self, lease: c.LeaseGrant) -> c.ProductionDetail:
        with self.engine.db.connect() as connection:
            run, production, _ = self._scope(connection, lease)
            detail = self.engine.get_production(production["owner"], production["id"])
            return detail.model_copy(update={"run_id": run["id"], "status": run["status"]})

    def creative_revisions(self, lease: c.LeaseGrant) -> tuple[c.CreativeRevision, ...]:
        with self.engine.db.connect() as connection:
            _, production, _ = self._scope(connection, lease)
            rows = connection.execute("SELECT body FROM creative_revisions WHERE production_id=? ORDER BY rowid", (production["id"],)).fetchall()
            return tuple(c.CreativeRevision.model_validate_json(row[0]) for row in rows)

    def approval_refs(self, lease: c.LeaseGrant) -> tuple[c.ApprovalRef, ...]:
        with self.engine.db.connect() as connection:
            _, production, _ = self._scope(connection, lease)
            rows = connection.execute("SELECT d.* FROM decisions d JOIN runs r ON r.id=d.run_id WHERE r.production_id=? ORDER BY d.rowid", (production["id"],)).fetchall()
            result = []
            for row in rows:
                decision = c.ReviewDecision.model_validate_json(row["body"])
                if decision.action == "approve":
                    result.append(c.ApprovalRef(run_id=row["run_id"], idempotency_key=row["idempotency_key"],
                        target_revision_id=decision.target_revision_id, decision_sha256=digest(row["body"])))
            return tuple(result)

    def feedback_refs(self, lease: c.LeaseGrant) -> tuple[c.RevisionRef, ...]:
        with self.engine.db.connect() as connection:
            _, production, _ = self._scope(connection, lease)
            rows = connection.execute("SELECT id,body FROM feedback_revisions WHERE production_id=? ORDER BY rowid", (production["id"],)).fetchall()
            return tuple(c.RevisionRef(revision_id=row["id"], kind="feedback", content_sha256=digest(row["body"])) for row in rows)

    def _validate_preparation_intent(self, lease: c.LeaseGrant, intent: BundlePreparationIntent):
        if len({item.artifact_id for item in intent.material_slots}) != len(intent.material_slots) or len({item.relative_path.casefold() for item in intent.material_slots}) != len(intent.material_slots):
            raise EngineError("bundle_material_slots_invalid", "Material slots have unique identities and paths", 422)
        authorization_slots = [slot for slot in intent.material_slots if slot.schema_kind == "production_authorization" or slot.relative_path == AUTHORIZATION_PATH]
        if len(authorization_slots) > 1 or any(slot.schema_kind != "production_authorization" or slot.relative_path != AUTHORIZATION_PATH for slot in authorization_slots):
            raise EngineError("production_authorization_kind_invalid", "Authorization has one independent exact kind/path", 422)
        for slot in intent.material_slots:
            expected_type = "application/x-ndjson" if slot.schema_kind in {"shots", "semantic_segments", "rag_chunks", "shots_local", "semantic_segments_local", "rag_chunks_local"} else {"srt": "text/srt", "vtt": "text/vtt", "srt_local": "text/srt", "vtt_local": "text/vtt", "license": "text/plain"}.get(slot.schema_kind, "application/json")
            if slot.media_type != expected_type:
                raise EngineError("bundle_material_type_invalid", "Material MIME must match its unique admitted schema", 422)
            # This validates the public safe locator, without creating a media asset.
            c.BundleArtifact(artifact_id=slot.artifact_id, material_id="validation", sha256="0" * 64, size=1, media_type=slot.media_type,
                relative_path=slot.relative_path, roles=(slot.schema_kind,), method_ref="validation", rights_ref="validation")
        for asset_id in intent.media_asset_ids:
            self.asset(lease, asset_id)

    def prepare(self, lease: c.LeaseGrant, intent: BundlePreparationIntent) -> BundlePreparation:
        self._validate_preparation_intent(lease, intent)
        with self.engine.db.transaction() as connection:
            return self._prepare_bundle_writer(connection, lease, intent)

    def prepare_local(self, lease, intent: BundlePreparationIntent, *, context):
        source = self._local_source()
        snapshot = source.context_snapshot(lease, context)
        self._validate_preparation_intent(lease, intent)
        expected = local.LOCAL_REQUIRED_FILES | ({'Semantics/shots.jsonl', 'Semantics/visual-mapping.json'}
            if context.selection.content_kind == 'video' else set())
        if not expected <= {slot.relative_path for slot in intent.material_slots}:
            raise EngineError('local_bundle_material_missing', 'All actual local provenance and applicable visual slots are required.', 422)
        with self._production_authorization.guard_for(lease) as guard, self.engine.db.transaction() as connection:
            source.assert_context_writer(connection, lease, snapshot)
            if guard is not None:
                run = self.engine._lease(connection, lease)
                issuer = self._production_authorization.issuer()
                issuer._bound(connection, guard, self.engine._production(connection, run['production_id']),
                    run, action='execute_plan')
                ref = context.plan_admission.admission_ref
                admitted = connection.execute('SELECT * FROM production_admissions WHERE id=? AND run_id=?',
                    (ref.admission_id if ref is not None else None, lease.run_id)).fetchone()
                if ref is None or admitted is None or digest(canonical(issuer._fact(admitted))) != ref.content_sha256:
                    raise EngineError('local_bundle_admission_changed', 'Original actual plan admission changed before allocation.', 409)
            prepared = self._prepare_bundle_writer(connection, lease, intent, local_context=context)
            source.assert_context_writer(connection, lease, snapshot)
        with self._lock:
            if not hasattr(self, '_local_preparation_contexts'):
                self._local_preparation_contexts = {}
            old = self._local_preparation_contexts.get(prepared.preparation_id)
            if old is not None and (old.plan_revision, old.quality_revision, old.selection) != (
                    context.plan_revision, context.quality_revision, context.selection):
                raise EngineError('local_bundle_context_conflict', 'Original local preparation cannot replace its approved sources.', 409)
            self._local_preparation_contexts[prepared.preparation_id] = context
        return prepared

    def recover_local_preparation(self, lease, preparation_id, *, context):
        source = self._local_source()
        source.context_snapshot(lease, context)
        with self.engine.db.connect_readonly() as connection:
            row, _run, _production, _request = self._preparation(connection, lease, preparation_id)
            intent = BundlePreparationIntent.model_validate_json(row['intent_json'])
        restored = self.prepare_local(lease, intent, context=context)
        if restored.preparation_id != preparation_id:
            raise EngineError('local_bundle_context_conflict', 'Recovery cannot allocate a different preparation.', 409)
        return restored

    def verify_local(self, lease, preparation_id, manifest):
        if type(manifest) is not local.BundleManifestLocalV1:
            raise EngineError('local_bundle_version_invalid', 'Explicit sole local manifest is required.', 422)
        return self.verify(lease, preparation_id, manifest)

    def _prepare_bundle_writer(self, connection, lease, intent, *, local_context=None):
        """Original allocation writer, shared only by original prepare and atomic repair."""
        run, production, request = self._scope(connection, lease)
        if intent.request_revision_id != production["request_revision_id"]:
            raise EngineError("request_revision_conflict", "Bundle uses another fixed request", 409)
        has_local = any(slot.schema_kind.endswith('_local') or slot.schema_kind in {'local_master_selection', 'local_speech_evidence'}
                        for slot in intent.material_slots)
        if has_local and local_context is None:
            raise EngineError('local_bundle_context_required', 'Local material allocation requires original controlled context.', 403)
        new_kinds = {"actual_transcript_v03", "precision_report_v03", "precision_reference_v03", "method_benchmark",
            "method_benchmark_reference", "method_benchmark_self_issued", "method_qualification", "evidence_policy",
            "work_alignment_validation"}
        if local_context is None and request.request_format_version == c.SCHEMA_VERSION and any(slot.schema_kind in new_kinds for slot in intent.material_slots):
            raise EngineError("bundle_material_version_conflict", "Old strict preparation cannot accept versioned 0.3 material grammar", 422)
        if local_context is None and request.request_format_version == c.V03_SCHEMA_VERSION and any(slot.relative_path == "Text/actual-transcript.json" and slot.schema_kind != "actual_transcript_v03" for slot in intent.material_slots):
            raise EngineError("bundle_material_version_conflict", "Explicit 0.3 preparation requires its actual transcript grammar", 422)
        old = connection.execute("SELECT * FROM bundle_revisions WHERE revision_id=?", (intent.bundle_revision_id,)).fetchone()
        if old:
            if old["run_id"] != run["id"] or old["intent_json"] != canonical(intent):
                raise EngineError("bundle_preparation_conflict", "Bundle revision already has a different fixed preparation", 409)
            return self._snapshot(connection, old)
        preparation_id = identity("preparation")
        connection.execute("INSERT INTO bundle_revisions(id,bundle_id,revision_id,owner,project_id,production_id,run_id,request_revision_id,input_sha256,intent_json,status,prepared_fence,created_at_us) VALUES(?,?,?,?,?,?,?,?,?,?,'prepared',?,?)",
            (preparation_id, intent.bundle_id, intent.bundle_revision_id, production["owner"], production["project_id"], production["id"], run["id"], production["request_revision_id"], intent.input_sha256, canonical(intent), lease.fencing_token, self.engine.clock()))
        for slot in intent.material_slots:
            connection.execute("INSERT INTO bundle_items(preparation_id,artifact_id,material_id,relative_path,media_type,schema_kind,status,allocation_fence) VALUES(?,?,?,?,?,?,'allocated',?)",
                (preparation_id, slot.artifact_id, identity("material"), slot.relative_path, slot.media_type, slot.schema_kind, lease.fencing_token))
        self.engine._event(connection, run, "bundle.prepared", intent.bundle_revision_id)
        return self._snapshot(connection, connection.execute("SELECT * FROM bundle_revisions WHERE id=?", (preparation_id,)).fetchone())

    def stage_production_authorization(self, lease: c.LeaseGrant, preparation_id: str, artifact_id: str, *, plan_admission_ref: ProductionAdmissionRef) -> MaterialReceipt:
        with self.engine.db.connect() as connection:
            self._preparation(connection, lease, preparation_id)
            slot = connection.execute("SELECT * FROM bundle_items WHERE preparation_id=? AND artifact_id=?", (preparation_id, artifact_id)).fetchone()
        if (not slot or slot["schema_kind"] != "production_authorization" or slot["relative_path"] != AUTHORIZATION_PATH
                or slot["media_type"] != "application/json" or not slot["material_id"]):
            raise EngineError("production_authorization_slot_missing", "Actual authorization staging needs its original exact allocated material", 422)
        document = self._production_authorization.issuer().authorization_document(
            self._production_authorization.registered(lease), lease, plan_admission_ref)
        return self.stage_material(lease, preparation_id, artifact_id, (canonical(document) + "\n").encode("utf-8"))

    def stage_material(self, lease: c.LeaseGrant, preparation_id: str, artifact_id: str, data: bytes) -> MaterialReceipt:
        with self.engine.db.connect() as connection:
            self._preparation(connection, lease, preparation_id)
            item = connection.execute("SELECT * FROM bundle_items WHERE preparation_id=? AND artifact_id=? AND material_id IS NOT NULL", (preparation_id, artifact_id)).fetchone()
        if not item:
            raise EngineError("bundle_material_denied", "Material is outside the original exact preparation", 404)
        validate_text(data, item["schema_kind"], item["media_type"])
        sha, size = hashlib.sha256(data).hexdigest(), len(data)
        with self.engine.db.transaction() as connection:
            self._preparation(connection, lease, preparation_id)
            current = connection.execute("SELECT * FROM bundle_items WHERE preparation_id=? AND artifact_id=?", (preparation_id, artifact_id)).fetchone()
            if current["sha256"] and (current["sha256"], current["size"]) != (sha, size):
                raise EngineError("bundle_material_conflict", "Original material bytes are immutable", 409)
            connection.execute("UPDATE bundle_items SET sha256=?,size=?,status='writing' WHERE preparation_id=? AND artifact_id=? AND status!='ready'", (sha, size, preparation_id, artifact_id))
        self._write("BundleMaterials", item["material_id"], data)
        with self.engine.db.transaction() as connection:
            self._preparation(connection, lease, preparation_id)
            connection.execute("UPDATE bundle_items SET status='ready' WHERE preparation_id=? AND artifact_id=? AND sha256=? AND size=?", (preparation_id, artifact_id, sha, size))
        return MaterialReceipt(preparation_id=preparation_id, artifact_id=artifact_id, material_id=item["material_id"], sha256=sha, size=size,
                               media_type=item["media_type"], schema_kind=item["schema_kind"])

    def material_allocation(self, lease: c.LeaseGrant, preparation_id: str, artifact_id: str) -> MaterialAllocation:
        with self.engine.db.connect() as connection:
            self._preparation(connection, lease, preparation_id)
            item = connection.execute("SELECT * FROM bundle_items WHERE preparation_id=? AND artifact_id=? AND material_id IS NOT NULL", (preparation_id, artifact_id)).fetchone()
            if not item:
                raise EngineError("bundle_material_denied", "Material allocation is outside the exact persisted preparation", 404)
            return MaterialAllocation(preparation_id=preparation_id, artifact_id=item["artifact_id"], material_id=item["material_id"],
                relative_path=item["relative_path"], media_type=item["media_type"], schema_kind=item["schema_kind"])

    def evidence_policy(self, lease: c.LeaseGrant):
        with self.engine.db.connect() as connection:
            _, production, request = self._scope(connection, lease)
            if not isinstance(request, c.ProductionRequestV03) or not request.delivery_requirements:
                raise EngineError("evidence_policy_unavailable", "Only an explicit 0.3 fixed policy has an automatic evidence scope", 409)
            return self.engine.evidence_registry.resolve(production["owner"], production["project_id"], request.delivery_requirements.evidence_policy_revision_ref, connection=connection)

    def local_evidence_policy(self, lease: c.LeaseGrant):
        """ADR0082 product ruling: auto-resolve the installed local self-issued policy.

        Only for a local work whose request has no explicit 0.3 delivery
        requirements. It reads the durable `preauthorize` selection and re-verifies
        it through the registry; no config/request/environment value selects it.
        Returns None when no verified local self-issued policy is installed.
        """
        from video_creator.application.local_evidence import (
            local_evidence_selected_policy,
        )

        with self.engine.db.connect() as connection:
            _run, production, request = self._scope(connection, lease)
            if (request.request_format_version == c.V03_SCHEMA_VERSION
                    and request.delivery_requirements is not None):
                return None
            return local_evidence_selected_policy(self.engine, production["owner"],
                                                  production["project_id"], connection=connection)

    def benchmark_reference(self, lease: c.LeaseGrant) -> c.MethodBenchmarkReference:
        resolved = self.evidence_policy(lease)
        return self.engine.evidence_registry.benchmark_reference(resolved.qualification.benchmark_report_ref)

    def correction_origin(self, lease: c.LeaseGrant, reference: c.CorrectionOriginRef) -> bytes:
        with self.engine.db.connect() as connection:
            _, production, _ = self._scope(connection, lease)
            item = connection.execute("SELECT i.* FROM bundle_items i JOIN bundle_revisions b ON b.id=i.preparation_id WHERE i.material_id=? AND i.artifact_id=? AND i.status='ready' AND b.owner=? AND b.project_id=?", (
                reference.material_id, reference.artifact_id, production["owner"], production["project_id"])).fetchone()
        kind = "precision_report" if reference.schema_version == c.SCHEMA_VERSION else "precision_report_v03"
        if not item or item["schema_kind"] != kind or item["sha256"] != reference.sha256:
            raise EngineError("correction_origin_unavailable", "Original immutable report is not an owned ready material in this project", 409)
        path = self._file("BundleMaterials", item["material_id"])
        if not path.is_file():
            raise EngineError("correction_origin_unavailable", "Original report bytes are unavailable", 409)
        raw = path.read_bytes()
        if len(raw) != item["size"] or hashlib.sha256(raw).hexdigest() != reference.sha256:
            raise EngineError("correction_origin_integrity_failed", "Original report bytes differ from their immutable audit hash", 422)
        report = validate_text(raw, kind, item["media_type"])
        if (report.evaluation_id, report.content_sha256, report.alignment_revision_id, report.alignment_content_sha256) != (
                reference.report_id, reference.content_sha256, reference.alignment_revision_id, reference.alignment_content_sha256):
            raise EngineError("correction_origin_integrity_failed", "Correction audit locator changed an original report identity", 422)
        return raw

    def _correction_source_manifest(self, lease, reference):
        raw = self.correction_origin(lease, reference)
        with self.engine.db.connect() as connection:
            _, production, _ = self._scope(connection, lease)
            row = connection.execute("SELECT b.* FROM bundle_revisions b JOIN bundle_items i ON i.preparation_id=b.id WHERE i.material_id=? AND i.artifact_id=? AND i.status='ready' AND b.owner=? AND b.project_id=?", (
                reference.material_id, reference.artifact_id, production["owner"], production["project_id"])).fetchone()
        if not row or not row["manifest_json"] or not row["manifest_sha256"] or not row["manifest_file_key"]:
            raise EngineError("correction_license_index_unavailable", "Readable report has no original persisted rights and license index", 409)
        path = self._file("BundleManifests", row["manifest_file_key"])
        if not path.is_file() or path.read_bytes() != row["manifest_json"].encode() or self.assets._hash(path) != row["manifest_sha256"]:
            raise EngineError("correction_origin_integrity_failed", "Original rights index bytes or manifest hash changed", 422)
        manifest = c.parse_bundle_manifest(row["manifest_json"])
        if (manifest.instance_id, manifest.bundle_id, manifest.bundle_revision_id, manifest.production_id, manifest.project_id) != (
                self.engine.instance_id, row["bundle_id"], row["revision_id"], row["production_id"], production["project_id"]):
            raise EngineError("correction_origin_integrity_failed", "Original license index differs from the owned project/source revision", 422)
        return row, manifest, raw

    def _correction_source_artifact(self, row, manifest, artifact_id, required_uses, *, lease, authorization_cache):
        artifact = next((item for item in manifest.artifacts if item.artifact_id == artifact_id), None)
        right = next((item for item in manifest.rights if artifact and item.rights_id == artifact.rights_ref), None)
        if not artifact or not right:
            raise EngineError("correction_license_index_unavailable", "Original artifact or rights declaration is absent from the exact index", 409)
        for values in (right.license_document_artifact_ids, right.platforms, right.territories, right.limitations, artifact.dependency_artifact_ids):
            if len(set(values)) != len(values):
                raise EngineError("correction_source_invalid", "Original rights/index lists must be distinct before constructing a source map", 422)
        with self.engine.db.connect() as connection:
            ready = connection.execute("SELECT * FROM bundle_items WHERE preparation_id=? AND artifact_id=? AND status='ready'", (row["id"], artifact_id)).fetchone()
            if (not ready or (ready["asset_id"], ready["material_id"], ready["sha256"], ready["size"], ready["media_type"], ready["relative_path"]) != (
                    artifact.asset_id, artifact.material_id, artifact.sha256, artifact.size, artifact.media_type, artifact.relative_path)):
                raise EngineError("correction_origin_integrity_failed", "Original indexed source is not its actual immutable ready receipt", 422)
            self._rights_time(right, self.engine.clock(), required_uses)
            if right.basis != "user_asserted":
                raise EngineError("rights_preflight_admission_required", "Owned/licensed source delivery needs an admitted real scoped authority", 503)
        cache_key = (row["id"], row["manifest_sha256"])
        if cache_key not in authorization_cache:
            authorization_cache[cache_key] = self._production_authorization.read_historical_source(lease, manifest)
        source_policy = authorization_cache[cache_key]
        with self.engine.db.connect() as connection:
            if source_policy is not None:
                self._production_authorization.assert_historical_source(connection, lease, manifest, source_policy, right=right)
                approved = ()
            else:
                approved = self._assert_owner_right(connection, manifest.production_id, right, manifest.approval_refs, manifest.creative_revision_refs, expected_run_id=lease.run_id)
        path = self._artifact_path(row["owner"], artifact)
        if not path.is_file() or path.stat().st_size != artifact.size or self.assets._hash(path) != artifact.sha256:
            raise EngineError("correction_origin_integrity_failed", "Original license/source artifact bytes changed", 422)
        record_hash = None
        if artifact.material_id:
            parsed = validate_text(path.read_bytes(), ready["schema_kind"], artifact.media_type)
            if isinstance(parsed, (c.PrecisionEvaluationReport, c.PrecisionEvaluationReportV03)):
                if record_sha(parsed) != parsed.content_sha256:
                    raise EngineError("correction_origin_integrity_failed", "Original report internal record SHA changed", 422)
                record_hash = parsed.content_sha256
        return CorrectionSourceArtifact(self._ref(row), artifact, right,
            BundleContentHandle(path, artifact.sha256, artifact.size, artifact.media_type, required_uses[0]), approved,
            ready["schema_kind"], record_hash, source_policy)

    def correction_origin_evidence(self, lease: c.LeaseGrant, reference: c.CorrectionOriginRef, *,
            purpose: c.UsePurpose = "derivative") -> CorrectionOriginEvidence:
        if purpose not in PURPOSES:
            raise EngineError("rights_use_invalid", "Source delivery purpose is outside the existing protocol", 422)
        required_uses = tuple(dict.fromkeys((purpose, "derivative", "export", "redistribution")))
        with self.engine.db.connect() as connection:
            run, production, _ = self._scope(connection, lease)
        reports, licenses, references, source_artifacts, edges = [], {}, set(), {}, []
        authorization_cache, physical_files = {}, {}
        identifiers = {}
        logical_bytes = 0
        def register_file(reference, artifact):
            nonlocal logical_bytes
            key = (canonical(reference), artifact.artifact_id, artifact.material_id, artifact.asset_id)
            signature = (artifact.sha256, artifact.size, artifact.media_type)
            if key in physical_files and physical_files[key] != signature:
                raise EngineError("correction_artifact_conflict", "A source/proof identity has conflicting actual bytes", 422)
            if key not in physical_files:
                physical_files[key] = signature
                logical_bytes += artifact.size
            if len(physical_files) > MAX_CORRECTION_ARTIFACTS or logical_bytes > self.assets.max_bytes:
                raise EngineError("source_closure_limit", "Complete source evidence exceeds bounded artifact/byte limits", 413)
        def register(source):
            key = digest(json.dumps(self._source_body(source), ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            signature = (source.artifact.sha256, source.artifact.size, source.artifact.media_type,
                source.schema_kind, source.record_content_sha256)
            identifier = source.artifact.artifact_id
            if identifier in identifiers and identifiers[identifier] != signature:
                raise EngineError("correction_artifact_conflict", "An original artifact ID has conflicting full bytes, grammar or record identity", 422)
            identifiers[identifier] = signature
            existing = source_artifacts.get(key)
            if existing is not None:
                return False
            source_artifacts[key] = source
            register_file(source.source_bundle_ref, source.artifact)
            if source.source_policy_authorization is not None:
                proof = source.source_policy_authorization
                for artifact in (proof.authorization.artifact, proof.plan_artifact):
                    register_file(proof.source_bundle_ref, artifact)
            return True
        current = reference
        while current is not None:
            if current.report_id in references or len(reports) >= MAX_CORRECTION_REPORTS:
                raise EngineError("source_closure_limit" if len(reports) >= MAX_CORRECTION_REPORTS else "correction_lineage_invalid", "Correction ancestors are distinct and limited to 32 source reports/depth", 413 if len(reports) >= MAX_CORRECTION_REPORTS else 422)
            references.add(current.report_id)
            row, manifest, raw = self._correction_source_manifest(lease, current)
            source = self._correction_source_artifact(row, manifest, current.artifact_id, required_uses, lease=lease, authorization_cache=authorization_cache)
            if (source.artifact.material_id != current.material_id or source.artifact.sha256 != current.sha256
                    or source.artifact.roles != ("precision_evaluation",)):
                raise EngineError("correction_origin_integrity_failed", "Source locator differs from the exact indexed report", 422)
            register(source)
            reports.append(CorrectionReportSource(current, source, raw))
            parsed = validate_text(raw, "precision_report" if current.schema_version == c.SCHEMA_VERSION else "precision_report_v03", source.artifact.media_type)
            next_reference = parsed.corrected_from if isinstance(parsed, c.PrecisionEvaluationReportV03) else None
            index_sources = [source]
            if next_reference:
                if next_reference.artifact_id not in source.artifact.dependency_artifact_ids:
                    raise EngineError("correction_origin_unavailable", "Persisted parent report must index its exact ancestor forward edge", 422)
                indexed_child = self._correction_source_artifact(row, manifest, next_reference.artifact_id, required_uses, lease=lease, authorization_cache=authorization_cache)
                child_row, child_manifest, _ = self._correction_source_manifest(lease, next_reference)
                child_source = self._correction_source_artifact(child_row, child_manifest, next_reference.artifact_id, required_uses, lease=lease, authorization_cache=authorization_cache)
                expected_kind = "precision_report" if next_reference.schema_version == c.SCHEMA_VERSION else "precision_report_v03"
                if (indexed_child.artifact.roles != ("precision_evaluation",) or indexed_child.schema_kind != expected_kind
                        or child_source.schema_kind != expected_kind or indexed_child.artifact.sha256 != next_reference.sha256
                        or indexed_child.record_content_sha256 != next_reference.content_sha256):
                    raise EngineError("correction_origin_integrity_failed", "Parent ancestor copy differs from exact original file/grammar/record identity", 422)
                child_report = validate_text(indexed_child.content.path.read_bytes(), expected_kind, indexed_child.artifact.media_type)
                if (child_report.evaluation_id, child_report.alignment_revision_id, child_report.alignment_content_sha256) != (
                        next_reference.report_id, next_reference.alignment_revision_id, next_reference.alignment_content_sha256):
                    raise EngineError("correction_origin_integrity_failed", "Parent indexed ancestor changed its record or alignment locator", 422)
                register(indexed_child)
                index_sources.append(indexed_child)
                edges.append(CorrectionDependencyEdge(source, indexed_child, next_reference, child_source))
            # Both the parent's own right and its indexed ancestor copy's right
            # constrain disclosure. The original ancestor's index is checked
            # separately on the next report iteration, never substituted here.
            queue = [(identifier, (), True) for index_source in index_sources for identifier in index_source.rights.license_document_artifact_ids]
            visited = set()
            visited_sources = {}
            license_edges = {}
            while queue:
                identifier, ancestors, license_locator = queue.pop(0)
                if identifier in ancestors:
                    raise EngineError("correction_license_cycle", "Original rights/license dependency graph contains a cycle", 422)
                license_source = visited_sources.get(identifier) or self._correction_source_artifact(row, manifest, identifier, required_uses, lease=lease, authorization_cache=authorization_cache)
                # Rights license locators are actual controlled documents;
                # dependencies may also be audited source materials.
                if license_locator and (not license_source.artifact.material_id or license_source.artifact.roles != ("license",)):
                    raise EngineError("bundle_license_missing", "Original license reference is not an actual typed license document", 422)
                if license_source.artifact.roles == ("license",):
                    with self.engine.db.connect() as connection:
                        slot = connection.execute("SELECT schema_kind FROM bundle_items WHERE preparation_id=? AND artifact_id=?", (row["id"], identifier)).fetchone()
                    if not slot or slot[0] != "license" or license_source.artifact.media_type != "text/plain":
                        raise EngineError("bundle_license_missing", "Original license must have its real immutable license grammar and MIME", 422)
                    validate_text(license_source.content.path.read_bytes(), "license", "text/plain")
                if identifier in visited:
                    continue
                visited.add(identifier)
                visited_sources[identifier] = license_source
                register(license_source)
                licenses[digest(json.dumps(self._source_body(license_source), ensure_ascii=False, sort_keys=True, separators=(",", ":")))] = license_source
                children = (*license_source.rights.license_document_artifact_ids, *license_source.artifact.dependency_artifact_ids)
                license_edges[identifier] = set(children)
                queue.extend((child, (*ancestors, identifier), child in license_source.rights.license_document_artifact_ids) for child in children)
            completed = set()
            while license_edges:
                ready = {key for key, dependencies in license_edges.items() if dependencies <= completed}
                if not ready:
                    raise EngineError("correction_license_cycle", "Original license and rights dependencies must form a complete acyclic graph", 422)
                completed.update(ready)
                license_edges = {key: value for key, value in license_edges.items() if key not in ready}
            current = next_reference
        # Repeat ordinary fence/policy and current source rights after all reads.
        with self.engine.db.connect() as connection:
            self._scope(connection, lease)
            for source in source_artifacts.values():
                self._rights_time(source.rights, self.engine.clock(), required_uses)
        body = {"sources": [self._source_body(value) for value in source_artifacts.values()],
            "edges": [{"parent": self._source_body(edge.parent), "indexed_child": self._source_body(edge.indexed_child),
                "child_reference": edge.child_reference.model_dump(mode="json"), "child_source": self._source_body(edge.child_source)} for edge in edges],
            "required_uses": required_uses}
        copy_fact = self._copy_scope_for_sources(lease, tuple(source_artifacts.values()), required_uses)
        if copy_fact is not None:
            body['copy_input_admission'] = self._copy_input_body(copy_fact)
        fact = CorrectionOriginEvidence(self.engine.instance_id, production["id"], run["id"], production["request_revision_id"],
            production["request_sha256"], lease.fencing_token, self.engine.clock(), required_uses, tuple(reports), tuple(licenses.values()),
            tuple(edges), digest(json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))),
            ("Source approval is historical source evidence, not approval for a new Production or a local precision qualification.",), copy_fact)
        with self._lock:
            key = (lease.run_id, lease.worker_id, lease.fencing_token)
            previous = self._correction_facts.get(key)
            values = previous[1] if previous and previous[0] > self.engine.clock() else ()
            self._correction_facts[key] = (lease.expires_at_us, (*values, fact))
        return fact

    def read_material(self, lease: c.LeaseGrant, preparation_id: str, material_id: str) -> bytes:
        with self.engine.db.connect() as connection:
            self._preparation(connection, lease, preparation_id)
            item = connection.execute("SELECT * FROM bundle_items WHERE preparation_id=? AND material_id=? AND status='ready'", (preparation_id, material_id)).fetchone()
        if not item:
            raise EngineError("bundle_material_missing", "Original material is incomplete", 409, "reconcile")
        path = self._file("BundleMaterials", material_id)
        if not path.is_file():
            raise EngineError("bundle_material_unavailable", "Committed actual text material is unavailable", 503)
        data = path.read_bytes()
        if (hashlib.sha256(data).hexdigest(), len(data)) != (item["sha256"], item["size"]):
            raise EngineError("bundle_material_integrity_failed", "Original material no longer matches its fixed bytes", 422)
        validate_text(data, item["schema_kind"], item["media_type"])
        return data

    def recover_preparation(self, lease: c.LeaseGrant, preparation_id: str) -> BundlePreparation:
        with self.engine.db.connect() as connection:
            row, _, _, _ = self._preparation(connection, lease, preparation_id)
            return self._snapshot(connection, row)

    def _block(self, lease, code: str):
        revision = c.CreativeRevision(revision_id=identity("block"), kind="quality", body={"code": code, "block_code": code, "recoverable": True})
        # Missing capability is a persisted blocker even in unattended mode;
        # automated policy is not evidence that the capability exists.
        with self.engine.db.transaction() as connection:
            run = self.engine._lease(connection, lease)
            body = canonical(revision)
            connection.execute("INSERT INTO creative_revisions VALUES(?,?,?,?,?,?)", (revision.revision_id, run["production_id"], lease.run_id, "quality", body, digest(body)))
            connection.execute("UPDATE runs SET status='waiting_user',waiting_revision_id=?,worker_id=NULL,lease_until_us=0 WHERE id=?", (revision.revision_id, lease.run_id))
            connection.execute("UPDATE productions SET status='waiting_user' WHERE id=?", (run["production_id"],))
            self.engine._event(connection, self.engine._run(connection, lease.run_id), code, revision.revision_id)
        raise EngineError(code, "Required actual evidence is unavailable; inspect the persisted review blocker", 409, "safe")

    def _artifact_path(self, owner, item: c.BundleArtifact) -> Path:
        if item.asset_id:
            return self.assets.content_path(owner, item.asset_id)
        return self._file("BundleMaterials", item.material_id)

    def _media_probe(self, owner: str, artifact: c.BundleArtifact):
        if self.validators.media_validator is None:
            raise EngineError("media_validator_missing", "Bundle publication requires actual media decoding", 503)
        with self.engine.db.connect() as connection:
            staged = connection.execute("SELECT id FROM staging WHERE owner=? AND asset_id=? AND sha256=? AND size=? AND status='imported' ORDER BY rowid LIMIT 1", (owner, artifact.asset_id, artifact.sha256, artifact.size)).fetchone()
        if not staged:
            raise EngineError("bundle_media_staging_missing", "Actual media decoder needs the original controlled staging handle", 503)
        path = self.assets.staging_path(owner, staged[0])
        if path.stat().st_size != artifact.size or self.assets._hash(path) != artifact.sha256:
            raise EngineError("asset_integrity_failed", "Original media staging content changed", 422)
        probe = self.validators.media_validator(path, artifact.media_type)
        if not probe.decoded or probe.media_type != artifact.media_type:
            raise EngineError("bundle_media_invalid", "Bundle media does not decode to its declared type", 422)
        if artifact.spec.duration_us is not None and probe.duration_us != artifact.spec.duration_us:
            raise EngineError("bundle_media_spec_invalid", "Actual decoded media duration differs from its fixed spec", 422)
        if artifact.spec.width is not None and (probe.width, probe.height) != (artifact.spec.width, artifact.spec.height):
            raise EngineError("bundle_media_spec_invalid", "Actual decoded dimensions differ from their fixed spec", 422)
        return probe

    def _check_revisions(self, connection, production, manifest):
        required = ({"plan", "script", "quality"} if isinstance(manifest, local.BundleManifestLocalV1)
                    else {"insight", "brief", "plan", "script", "storyboard", "quality"})
        if isinstance(manifest, local.BundleManifestLocalV1):
            kinds = tuple(ref.kind for ref in manifest.creative_revision_refs)
            if len(set(kinds)) != len(kinds) or set(kinds) - {"insight", "brief", "plan", "script", "storyboard", "quality"}:
                raise EngineError('bundle_revision_conflict', 'Local creative attachments retain unique actual supported kinds.', 422)
        if not required <= {ref.kind for ref in manifest.creative_revision_refs}:
            raise EngineError("bundle_revision_missing", "Complete bundle requires all actual creative versions", 422)
        if manifest.quality_ref.kind != "quality" or manifest.quality_ref not in manifest.creative_revision_refs:
            raise EngineError("bundle_revision_conflict", "Quality reference must name the actual indexed quality revision", 409)
        for ref in (*manifest.creative_revision_refs, manifest.quality_ref):
            row = connection.execute("SELECT * FROM creative_revisions WHERE id=? AND production_id=?", (ref.revision_id, production["id"])).fetchone()
            if not row or row["content_sha256"] != ref.content_sha256 or c.CreativeRevision.model_validate_json(row["body"]).kind != ref.kind:
                raise EngineError("bundle_revision_conflict", "Creative revision belongs to different input or production", 409)
            if ref == manifest.quality_ref and row["run_id"] != manifest.run_id:
                raise EngineError("bundle_quality_run_conflict", "Quality must be produced by the exact publishing run", 409)
        for ref in manifest.feedback_revision_refs:
            row = connection.execute("SELECT body FROM feedback_revisions WHERE id=? AND production_id=?", (ref.revision_id, production["id"])).fetchone()
            if ref.kind != "feedback" or not row or digest(row[0]) != ref.content_sha256:
                raise EngineError("bundle_feedback_conflict", "Feedback lineage must retain its actual fixed original revision", 409)
        approved = set()
        for ref in manifest.approval_refs:
            row = connection.execute("SELECT d.body FROM decisions d JOIN runs r ON r.id=d.run_id WHERE d.run_id=? AND d.idempotency_key=? AND r.production_id=?", (ref.run_id, ref.idempotency_key, production["id"])).fetchone()
            if not row or digest(row[0]) != ref.decision_sha256:
                raise EngineError("bundle_approval_conflict", "Approval does not match a real fixed decision", 409)
            decision = c.ReviewDecision.model_validate_json(row[0])
            if decision.action != "approve" or decision.target_revision_id != ref.target_revision_id:
                raise EngineError("bundle_approval_conflict", "The referenced decision did not approve this revision", 409)
            approved.add(ref.target_revision_id)
        request = c.parse_production_request(production["request_json"])
        if request.automation.mode == "interactive":
            needed = {manifest.quality_ref.revision_id, next(ref.revision_id for ref in manifest.creative_revision_refs if ref.kind == "script")}
            # Approving an immutable plan approves its explicitly fixed input refs.
            for revision_id in tuple(approved):
                row = connection.execute("SELECT body FROM creative_revisions WHERE id=? AND production_id=?", (revision_id, production["id"])).fetchone()
                if row:
                    approved.update(c.CreativeRevision.model_validate_json(row[0]).input_revision_refs)
            if not needed <= approved:
                raise EngineError("bundle_approval_required", "The actual script and quality revisions need explicit approval", 409)

    def _all_operations(self, connection, run):
        rows = connection.execute("SELECT status,settled FROM operations WHERE run_id=?", (run["id"],)).fetchall()
        if not rows or any(row["status"] != "succeeded" or not row["settled"] for row in rows):
            raise EngineError("operation_incomplete", "Bundle publication requires all run operations successful and settled", 409, "reconcile")
        if connection.execute("SELECT 1 FROM operations WHERE production_id=? AND (settled=0 OR status IN ('submitting','unknown','pending')) LIMIT 1", (run["production_id"],)).fetchone():
            raise EngineError("operation_incomplete", "Historical operation uncertainty must be reconciled before publication", 409, "reconcile")

    def verify(self, lease: c.LeaseGrant, preparation_id: str, manifest: c.BundleManifest) -> VerifiedBundleMaterial:
        local_context = local_snapshot = None
        if isinstance(manifest, local.BundleManifestLocalV1):
            with self._lock:
                local_context = getattr(self, '_local_preparation_contexts', {}).get(preparation_id)
            if local_context is None:
                raise EngineError('local_preparation_context_missing', 'Recover the original controlled local preparation before verification.', 409)
            local_snapshot = self._local_source().context_snapshot(lease, local_context)
        with self.engine.db.connect() as connection:
            row, run, production, request = self._preparation(connection, lease, preparation_id)
            if (manifest.request_format_version if local_context is not None else manifest.schema_version) != request.request_format_version:
                raise EngineError("bundle_version_conflict", "Manifest belongs to a different fixed request version", 409)
            if (manifest.instance_id, manifest.bundle_id, manifest.bundle_revision_id, manifest.project_id, manifest.production_id, manifest.run_id,
                manifest.request_revision_id, manifest.request_sha256) != (self.engine.instance_id, row["bundle_id"], row["revision_id"], production["project_id"], production["id"], run["id"], production["request_revision_id"], production["request_sha256"]):
                raise EngineError("bundle_identity_conflict", "Manifest must keep all original fixed identities", 409)
            self._all_operations(connection, run)
            self._check_revisions(connection, production, manifest)
            intent = BundlePreparationIntent.model_validate_json(row["intent_json"])
            materials = connection.execute("SELECT * FROM bundle_items WHERE preparation_id=? AND material_id IS NOT NULL ORDER BY rowid", (preparation_id,)).fetchall()
        if local_context is None and (set(manifest.requested_outputs) != FULL_OUTPUTS or set(request.outputs) != FULL_OUTPUTS):
            raise EngineError("output_profile_unavailable", "This implementation publishes only the complete eight-output profile", 409)
        paths = {artifact.relative_path for artifact in manifest.artifacts}
        required_files = (local.LOCAL_REQUIRED_FILES | ({'Semantics/shots.jsonl', 'Semantics/visual-mapping.json'}
                          if local_context.selection.content_kind == 'video' else set())) if local_context is not None else FIXED_FILES
        if not required_files <= paths:
            raise EngineError("bundle_output_missing", "Required output or fixed provenance attachment is missing", 422)
        material_map = {item["artifact_id"]: item for item in materials}
        if {artifact.artifact_id for artifact in manifest.artifacts if artifact.material_id} != set(material_map):
            raise EngineError("bundle_material_set_conflict", "Manifest must contain the exact original material set", 409)
        if {artifact.asset_id for artifact in manifest.artifacts if artifact.asset_id} != set(intent.media_asset_ids):
            raise EngineError("bundle_asset_set_conflict", "Manifest media differs from its original prepared asset set", 409)
        if local_context is None and getattr(self, '_production_services_runtime', None) is not None and self._final_evidence_ports:
            masters = self.resolve_preparation_masters(lease, preparation_id)
            if any(tuple(artifact.roles) != (role,) for role, asset in masters.items()
                   for artifact in manifest.artifacts if artifact.asset_id == asset.asset_id):
                raise EngineError('bundle_asset_set_conflict', 'Manifest roles differ from authenticated preparation masters', 409)
        documents, file_records = {}, []
        for artifact in manifest.artifacts:
            if artifact.asset_id:
                record = self.asset(lease, artifact.asset_id)
                if (record.sha256, record.size, record.media_type) != (artifact.sha256, artifact.size, artifact.media_type):
                    raise EngineError("bundle_asset_conflict", "Manifest differs from its registered actual Asset", 422)
                path = self.content_path(lease, artifact.asset_id)
                self._media_probe(row["owner"], artifact)
            else:
                item = material_map[artifact.artifact_id]
                if item["status"] != "ready" or (item["material_id"], item["relative_path"], item["sha256"], item["size"], item["media_type"]) != (artifact.material_id, artifact.relative_path, artifact.sha256, artifact.size, artifact.media_type):
                    raise EngineError("bundle_material_conflict", "Manifest differs from its actual controlled material receipt", 422)
                data = self.read_material(lease, preparation_id, artifact.material_id)
                documents[artifact.relative_path] = validate_text(data, item["schema_kind"], artifact.media_type)
                path = self._file("BundleMaterials", artifact.material_id)
            if path.stat().st_size != artifact.size or self.assets._hash(path) != artifact.sha256:
                raise EngineError("bundle_integrity_failed", "Prepared actual bytes changed", 422)
            stat = path.stat()
            file_records.append((artifact, path, (stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns, stat.st_ino)))
        correction_pair = self.assert_current_correction_pair(lease, preparation_id)
        alignment_source = self.assert_initial_alignment_manifest(lease, preparation_id, manifest)
        ctc_work_source = self.registered_ctc_work_manifest_source(lease, preparation_id, manifest)
        if local_context is not None:
            from video_creator.application.local_bundle_relations import (
                validate_local_relations,
            )
            rights_observations = validate_local_relations(self, lease, preparation_id, manifest, documents, request, local_context)
        else:
            rights_observations = self._validate_relations(lease, manifest, documents, request)
        raw = (canonical(manifest) + "\n").encode("utf-8")
        sha, file_key = hashlib.sha256(raw).hexdigest(), "manifest-" + row["revision_id"]
        final_rights_context = self._final_rights_context(lease, preparation_id, manifest, sha, request)
        with self.engine.db.transaction() as connection:
            current, _, _, _ = self._preparation(connection, lease, preparation_id)
            if local_snapshot is not None:
                self._local_source().assert_context_writer(connection, lease, local_snapshot)
            self.assert_correction_pair_writer(connection, preparation_id, correction_pair)
            self.assert_initial_alignment_manifest_writer(connection, lease, preparation_id, alignment_source)
            self.assert_registered_ctc_work_writer(connection, ctc_work_source)
            if current["manifest_sha256"] and current["manifest_sha256"] != sha:
                raise EngineError("bundle_manifest_conflict", "Original revision already has a different manifest", 409)
            for artifact in manifest.artifacts:
                if artifact.asset_id:
                    connection.execute("INSERT OR IGNORE INTO bundle_items(preparation_id,artifact_id,asset_id,relative_path,media_type,sha256,size,status,allocation_fence) VALUES(?,?,?,?,?,?,?,'ready',?)",
                        (preparation_id, artifact.artifact_id, artifact.asset_id, artifact.relative_path, artifact.media_type, artifact.sha256, artifact.size, lease.fencing_token))
            connection.execute("UPDATE bundle_revisions SET manifest_json=?,manifest_sha256=?,manifest_file_key=? WHERE id=?", (raw.decode("utf-8"), sha, file_key, preparation_id))
            self.assert_correction_pair_writer(connection, preparation_id, correction_pair)
            self.assert_initial_alignment_manifest_writer(connection, lease, preparation_id, alignment_source)
            self.assert_registered_ctc_work_writer(connection, ctc_work_source)
            if local_snapshot is not None:
                self._local_source().assert_context_writer(connection, lease, local_snapshot)
        path = self._write("BundleManifests", file_key, raw)
        token = identity("verification")
        with self._lock:
            self._verified[token] = (lease, manifest, tuple(file_records), path, time.monotonic() + 30,
                tuple(value for value in documents.values() if isinstance(value, c.PerWorkReferenceDocument)), rights_observations, final_rights_context)
            if not hasattr(self, '_verified_correction_pairs'):
                self._verified_correction_pairs = {}
            self._verified_correction_pairs[token] = correction_pair
            if not hasattr(self, '_verified_alignment_sources'):
                self._verified_alignment_sources = {}
            self._verified_alignment_sources[token] = alignment_source
            if not hasattr(self, '_verified_ctc_work_sources'):
                self._verified_ctc_work_sources = {}
            self._verified_ctc_work_sources[token] = ctc_work_source
            if local_context is not None:
                if not hasattr(self, '_verified_local_contexts'):
                    self._verified_local_contexts = {}
                self._verified_local_contexts[token] = local_context
        return VerifiedBundleMaterial(token, preparation_id, sha)

    def _publish_rights_current(self, connection, production, manifest, observations, *, lease, guard, authorization_refs):
        if set(observations) != {right.rights_id for right in manifest.rights}:
            raise EngineError("bundle_rights_unverified", "Final rights facts differ from the exact verified Manifest", 409)
        indexed = {item.artifact_id: item for item in manifest.artifacts}
        for right in manifest.rights:
            self._rights_time(right, self.engine.clock())
            for identifier in right.license_document_artifact_ids:
                artifact = indexed.get(identifier)
                ready = connection.execute("SELECT * FROM bundle_items WHERE preparation_id=(SELECT id FROM bundle_revisions WHERE revision_id=?) AND artifact_id=? AND status='ready'", (
                    manifest.bundle_revision_id, identifier)).fetchone()
                if (not artifact or not artifact.material_id or artifact.roles != ("license",) or not ready
                        or ready["schema_kind"] != "license" or (ready["material_id"], ready["sha256"], ready["size"]) != (
                            artifact.material_id, artifact.sha256, artifact.size)):
                    raise EngineError("bundle_license_missing", "Current publication requires the real immutable ready license closure", 422)
            if not observations[right.rights_id]:
                if right.basis != "user_asserted":
                    raise EngineError("bundle_rights_unverified", "Owned/licensed rights require an actual trusted final verifier", 403)
                if guard is not None:
                    self._production_authorization.assert_local_current(connection, guard, lease, production, authorization_refs, right=right)
                else:
                    self._assert_owner_right(connection, production["id"], right, manifest.approval_refs, manifest.creative_revision_refs, expected_run_id=lease.run_id)

    def publish(self, lease: c.LeaseGrant, verified: VerifiedBundleMaterial) -> c.BundleRef:
        with self._lock:
            observation = self._verified.get(verified.verification_id)
        if not observation or observation[0] != lease or observation[4] <= time.monotonic():
            raise EngineError("bundle_verification_required", "Only actual current service verification can publish", 409, "reconcile")
        _, manifest, files, manifest_path, _, reference_documents, rights_observations, final_context = observation
        local_snapshot = None
        if isinstance(manifest, local.BundleManifestLocalV1):
            with self._lock:
                local_context = getattr(self, '_verified_local_contexts', {}).get(verified.verification_id)
            if local_context is None:
                raise EngineError('local_preparation_context_missing', 'Publication requires the originally verified controlled local context.', 409)
            local_snapshot = self._local_source().context_snapshot(lease, local_context)
        correction_pair = self.assert_current_correction_pair(lease, verified.preparation_id)
        with self._lock:
            original_pair = getattr(self, '_verified_correction_pairs', {}).get(verified.verification_id)
        if original_pair is None or correction_pair != original_pair:
            raise EngineError('correction_context_conflict', 'Publish must consume the originally verified author/measurement identity', 409)
        alignment_source = self.assert_initial_alignment_manifest(lease, verified.preparation_id, manifest)
        ctc_work_source = self.registered_ctc_work_manifest_source(lease, verified.preparation_id, manifest)
        with self._lock:
            alignment_observed = getattr(self, '_verified_alignment_sources', {})
            if verified.verification_id not in alignment_observed or alignment_observed[verified.verification_id] != alignment_source:
                raise EngineError('alignment_source_changed', 'Publish requires the originally verified initial CTC source', 409)
            ctc_observed = getattr(self, '_verified_ctc_work_sources', {})
            if verified.verification_id not in ctc_observed or ctc_observed[verified.verification_id] != ctc_work_source:
                raise EngineError('work_ctc_source_changed', 'Publish requires the originally verified CTC/ASR source', 409)
        if local_snapshot is None and getattr(self, '_production_services_runtime', None) is not None and self._final_evidence_ports:
            self.resolve_preparation_masters(lease, verified.preparation_id)
        # All large hash reads stay outside SQLite; immutable writer discipline
        # plus final file identity checks protect service races, not malicious OS peers.
        if self.assets._hash(manifest_path) != verified.manifest_sha256:
            raise EngineError("bundle_integrity_failed", "Actual manifest bytes changed", 422)
        for artifact, path, _ in files:
            if path.stat().st_size != artifact.size or self.assets._hash(path) != artifact.sha256:
                raise EngineError("bundle_integrity_failed", "Bundle bytes changed after verification", 422)
        # Legacy final-Manifest validation remains compatible, with a fresh
        # check outside the writer. It cannot be used as a fake preflight.
        for right in manifest.rights:
            if rights_observations.get(right.rights_id) and not (self.rights_authority and self.rights_authority(right, manifest) is True):
                raise EngineError("bundle_rights_unverified", "Trusted final rights verification is no longer current", 403)
        # An already published immutable result is an observation, not a new
        # execution grant. Its original request/policy is never installed again.
        with self.engine.db.connect() as connection:
            published = connection.execute("SELECT * FROM bundle_revisions WHERE id=?", (verified.preparation_id,)).fetchone()
            if published and published["status"] == "published" and published["manifest_sha256"] == verified.manifest_sha256 and published["run_id"] == lease.run_id:
                return self._ref(published)
        self._origin_files_current(lease, final_context)
        with self._production_authorization.publication_guard(lease, verified, manifest, final_context) as (guard, scope), self.engine.db.transaction() as connection:
            row = connection.execute("SELECT * FROM bundle_revisions WHERE id=?", (verified.preparation_id,)).fetchone()
            if row and row["status"] == "published" and row["manifest_sha256"] == verified.manifest_sha256 and row["run_id"] == lease.run_id:
                return self._ref(row)
            row, run, production, _ = self._preparation(connection, lease, verified.preparation_id)
            if local_snapshot is not None:
                self._local_source().assert_context_writer(connection, lease, local_snapshot)
            self.commit_first_publication_diagnosis(connection,lease,verified)
            self.assert_diagnostic_publish_writer(connection,lease,verified.preparation_id)
            self.assert_correction_pair_writer(connection, verified.preparation_id, correction_pair)
            self.assert_initial_alignment_manifest_writer(connection, lease, verified.preparation_id, alignment_source)
            self.assert_registered_ctc_work_writer(connection, ctc_work_source)
            self._all_operations(connection, run)
            self._check_revisions(connection, production, manifest)
            if (final_context.stage != "final_manifest" or final_context.final_manifest_sha256 != verified.manifest_sha256
                    or (final_context.instance_id, final_context.subject, final_context.project_id, final_context.production_id,
                        final_context.run_id, final_context.request_revision_id, final_context.request_sha256, final_context.preparation_id,
                        final_context.fencing_token) != (self.engine.instance_id, production["owner"], production["project_id"],
                        production["id"], run["id"], production["request_revision_id"], production["request_sha256"], row["id"], lease.fencing_token)
                    or final_context.rights != manifest.rights or tuple(value.artifact for value in final_context.artifacts) != manifest.artifacts):
                raise EngineError("bundle_rights_unverified", "Final private facts are not the exact current lease, Manifest and actual artifact scope", 409)
            self._publish_rights_current(connection, production, manifest, rights_observations, lease=lease,
                guard=guard, authorization_refs=final_context.production_authorization_refs)
            self._origin_bindings_current(connection, lease, production, final_context, guard=guard)
            if isinstance(manifest, c.BundleManifestV03) or isinstance(manifest, local.BundleManifestLocalV1) and reference_documents:
                # The same BEGIN IMMEDIATE order is shared with signed revocations.
                policy_ref = manifest.evidence_policy_revision_ref if isinstance(manifest, c.BundleManifestV03) else local_context.sources.request.delivery_requirements.evidence_policy_revision_ref
                self.engine.evidence_registry.resolve(production["owner"], production["project_id"], policy_ref, connection=connection)
                for reference in reference_documents:
                    self.engine.evidence_registry.reference_is_current(lease, verified.preparation_id, reference, connection=connection)
            if row["manifest_sha256"] != verified.manifest_sha256 or row["manifest_json"] != canonical(manifest) + "\n":
                raise EngineError("bundle_manifest_conflict", "Fixed preparation changed before publication", 409)
            for _, path, signature in files:
                stat = path.stat()
                if (stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns, stat.st_ino) != signature:
                    raise EngineError("bundle_file_changed", "Prepared file changed before the visibility transaction", 409, "reconcile")
            if scope is not None:
                self._production_authorization.issuer()._finalize_bundle_current(connection, guard, lease, scope)
            step_key = "deliver-bundle"
            old = connection.execute("SELECT * FROM steps WHERE run_id=? AND step_key=?", (run["id"], step_key)).fetchone()
            if old and old["input_sha256"] != row["input_sha256"]:
                raise EngineError("step_input_conflict", "Delivery step is fixed to a different original input", 409)
            if not old:
                connection.execute("INSERT INTO steps VALUES(?,?,?,'running',?,NULL)", (run["id"], step_key, row["input_sha256"], lease.fencing_token))
            elif old["status"] != "succeeded":
                connection.execute("UPDATE steps SET fencing_token=? WHERE run_id=? AND step_key=?", (lease.fencing_token, run["id"], step_key))
            ref = self._ref(row)
            self.assert_diagnostic_publish_writer(connection,lease,verified.preparation_id)
            if local_snapshot is not None:
                self._local_source().assert_context_writer(connection, lease, local_snapshot)
            self.engine._complete_step(connection, lease, step_key, (), {"bundle_ref": ref.model_dump(mode="json")})
            connection.execute("UPDATE bundle_revisions SET status='published',published_at_us=? WHERE id=?", (self.engine.clock(), row["id"]))
            connection.execute("UPDATE runs SET status='succeeded',worker_id=NULL,lease_until_us=0 WHERE id=?", (run["id"],))
            connection.execute("UPDATE productions SET status='succeeded' WHERE id=?", (production["id"],))
            finished = self.engine._run(connection, run["id"])
            self.engine._event(connection, finished, "bundle.ready", row["revision_id"])
            self.engine._event(connection, finished, "production.succeeded", row["revision_id"])
            self.assert_correction_pair_writer(connection, verified.preparation_id, correction_pair)
            self.assert_initial_alignment_manifest_writer(connection, lease, verified.preparation_id, alignment_source)
            self.assert_registered_ctc_work_writer(connection, ctc_work_source)
            return ref

    def _ref(self, row) -> c.BundleRef:
        version = c.parse_bundle_manifest(row["manifest_json"]).schema_version if row["manifest_json"] else c.SCHEMA_VERSION
        return c.BundleRef(schema_version=version, instance_id=self.engine.instance_id, bundle_id=row["bundle_id"], bundle_revision_id=row["revision_id"], manifest_sha256=row["manifest_sha256"])

    def _actor(self, actor: AccessContext, operation: str, purpose: str):
        current = self.principals.principal(actor.registration_id, self.engine.clock()) if actor.registration_id else self.principals.owner()
        if actor != current or actor.installation_id != self.engine.instance_id:
            raise EngineError("principal_scope_changed", "Trusted principal registration is no longer current", 403)
        if operation not in actor.operations or purpose not in actor.purposes:
            raise EngineError("bundle_scope_denied", "Principal operation or purpose is outside its configured scope", 403)
        return current

    def _rights(self, manifest, artifact_ids, purpose):
        rights = {item.rights_id: item for item in manifest.rights}
        selected = [item for item in manifest.artifacts if item.artifact_id in artifact_ids]
        now = self.engine.clock()
        for item in selected:
            right = rights[item.rights_ref]
            if purpose not in right.permitted_uses or (right.valid_from_us is not None and right.valid_from_us > now) or (right.expires_at_us is not None and right.expires_at_us <= now):
                raise EngineError("bundle_rights_denied", "Artifact rights do not permit this current use", 403)

    def _visible(self, actor, revision_id, operation, purpose, artifact_ids=(), semantic=False):
        self._actor(actor, operation, purpose)
        with self.engine.db.connect() as connection:
            row = connection.execute("SELECT * FROM bundle_revisions WHERE revision_id=? AND status='published'", (revision_id,)).fetchone()
            if not row:
                raise EngineError("not_found", "Bundle revision not found", 404)
            owner = actor.subject_id == row["owner"] and actor.owned_projects
            if not owner and row["project_id"] not in actor.project_ids:
                raise EngineError("not_found", "Bundle revision not found", 404)
            manifest = c.parse_bundle_manifest(row["manifest_json"])
            known = {item.artifact_id for item in manifest.artifacts}
            if not set(artifact_ids) <= known:
                raise EngineError("not_found", "Bundle artifact not found", 404)
            if not owner:
                grants = connection.execute("SELECT body FROM bundle_grants WHERE preparation_id=? AND recipient_id=? AND revoked_at_us IS NULL AND expires_at_us>?", (row["id"], actor.subject_id, self.engine.clock())).fetchall()
                allowed = [c.BundleReferenceGrant.model_validate_json(value[0]) for value in grants]
                if not any(purpose in grant.purposes and set(artifact_ids) <= set(grant.artifact_ids) and (not semantic or grant.allow_semantic_text) for grant in allowed):
                    raise EngineError("bundle_scope_denied", "No active reference grant permits this exact bundle use", 403)
            self._rights(manifest, artifact_ids or tuple(known), purpose)
        return row, manifest

    def get_manifest(self, actor: AccessContext, revision_id: str, purpose: str = "playback") -> c.BundleManifest:
        return self._manifest_content_facts(actor, revision_id, purpose).scope.manifest

    def _manifest_content_facts(self, actor, revision_id, purpose):
        # Whole Manifest still requires bundle.read, semantic permission and
        # one grant covering every disclosed artifact. This replaces the old
        # two-pass check with its stronger complete selector, not a leaf union.
        self._actor(actor, "bundle.read", purpose)
        from video_creator.application.delivery_metadata import DeliveryResolver
        return DeliveryResolver(self).resolve("bundle_manifest", actor, revision_id, purpose=purpose)

    def manifest_content(self, actor: AccessContext, revision_id: str, purpose: str = "playback") -> BundleContentHandle:
        return self._manifest_content_facts(actor, revision_id, purpose).handle

    def manifest_metadata(self, actor: AccessContext, revision_id: str, purpose: str = "playback") -> c.DeliveryContentMetadata:
        return self._manifest_content_facts(actor, revision_id, purpose).metadata(self.engine.instance_id)

    def create_production(self, actor: AccessContext, key: str, request: c.ProductionRequest) -> c.ProductionAccepted:
        self._actor(actor, "production.create", "derivative")
        # ADR0084 temporary gate: acceptance itself must prove an actual
        # execution authority exists. A production may not sit queued only to
        # fail later at execution. Dev supplies its own dev authority; a
        # product process without the card-B factory refuses here with the
        # same named code execution would use. Card B replaces this with
        # "authority exists and is currently valid".
        try:
            if getattr(self.engine, '_require_acceptance_authority', False):
                self.engine._authorization_identity(actor.subject_id)
        except EngineError as error:
            if error.code in {'production_authorization_unconfigured',
                              'production_execution_identity_denied'}:
                raise EngineError('production_authorization_unconfigured',
                                  'No trusted production execution authority is installed; production acceptance is refused',
                                  403) from error
            raise
        if request.project_id:
            with self.engine.db.connect() as connection:
                row = connection.execute("SELECT owner FROM projects WHERE id=?", (request.project_id,)).fetchone()
            if not row or row[0] != actor.subject_id or not (actor.owned_projects or request.project_id in actor.project_ids):
                raise EngineError("not_found", "Configured owned production project not found", 404)
        elif not actor.owned_projects:
            raise EngineError("project_scope_required", "Principal requires an explicitly configured owned project", 403)
        return self.engine.accept_production(actor.subject_id, key, request)

    def create_project_goal(self, actor: AccessContext, key: str, goal: ProjectGoalInput, *, entry: str) -> ProjectGoalAccepted:
        self._actor(actor, 'production.create', 'derivative')
        # The ordinary token does not manage a delegation. The original issuer
        # must map this actual principal to the installed Owner and current
        # bounded creation action; refs/body cannot supply that authority.
        if not actor.owned_projects or actor.subject_id != self.principals.owner_subject:
            raise EngineError('daily_project_execution_denied', 'This version creates Goal projects only for the actual installed local Owner', 403)
        return self.engine.create_project_goal(actor.subject_id, key, goal, entry=entry)

    def lookup_project_goal_receipt(self, actor: AccessContext, query: ProjectGoalReceiptQueryV1) -> ProjectGoalReceiptAssociationV1:
        from video_creator.application.goal_receipt_lookup import (
            lookup_project_goal_receipt,
        )
        self._actor(actor, 'production.read', 'playback')
        result = lookup_project_goal_receipt(self.engine, actor, query)
        self._actor(actor, 'production.read', 'playback')
        return result

    def production(self, actor: AccessContext, production_id: str) -> c.ProductionDetail:
        self._actor(actor, "production.read", "playback")
        detail = self.engine.get_production(actor.subject_id, production_id)
        if not actor.owned_projects and detail.project_id not in actor.project_ids:
            raise EngineError("not_found", "Configured production project not found", 404)
        return detail

    def decision(self, actor: AccessContext, run_id: str, key: str, decision: c.ReviewDecision):
        self._actor(actor, "production.review", "derivative")
        with self.engine.db.connect() as connection:
            run = self.engine._run(connection, run_id)
        self.production(actor, run["production_id"])
        return self.engine.submit_decision(actor.subject_id, run_id, key, decision)

    def production_revisions(self, actor: AccessContext, production_id: str) -> list[c.ProductionRevisionSummary]:
        """Readable pending/decided creative revisions for one authorized production."""
        self._actor(actor, "production.read", "playback")
        self.production(actor, production_id)
        result = []
        for revision in self.engine.creative_revisions(actor.subject_id, production_id):
            body = revision.body if isinstance(revision.body, dict) else {}
            expires = body.get("expires_at_us")
            failure = body.get("failure_code") or body.get("code")
            result.append(c.ProductionRevisionSummary(
                revision_id=revision.revision_id, kind=revision.kind,
                parent_revision_id=revision.parent_revision_id,
                expires_at_us=expires if isinstance(expires, int) and expires > 0 else None,
                failure_code=failure if isinstance(failure, str) and failure else None))
        return result

    def content(self, actor: AccessContext, revision_id: str, artifact_id: str, purpose: str = "playback") -> BundleContentHandle:
        return self._leaf_content_facts(actor, revision_id, artifact_id, purpose).handle

    def _leaf_content_facts(self, actor, revision_id, artifact_id, purpose):
        # This one leaf chain retains the existing current registry/instance
        # and exact bundle.content/purpose boundary. DeliveryResolver._document
        # retains published/owner/project hiding; its single-grant selector
        # covers only this leaf, never merges grants or reads whole-Manifest.
        self._actor(actor, "bundle.content", purpose)
        from video_creator.application.delivery_metadata import DeliveryResolver
        return DeliveryResolver(self).resolve("bundle_artifact", actor, revision_id, artifact_id, purpose)

    def content_metadata(self, actor: AccessContext, revision_id: str, artifact_id: str, purpose: str = "playback") -> c.DeliveryContentMetadata:
        return self._leaf_content_facts(actor, revision_id, artifact_id, purpose).metadata(self.engine.instance_id)

    def semantic_page(self, actor: AccessContext, revision_id: str, cursor: str | None = None, limit: int = 50) -> c.SemanticPage:
        if not 1 <= limit <= 100 or (cursor is not None and (not cursor.isdecimal() or len(cursor) > 10)):
            raise EngineError("invalid_cursor", "Semantic page has a bounded numeric cursor and limit", 400)
        _, manifest = self._visible(actor, revision_id, "bundle.semantic", "rag_index", semantic=True)
        artifact = next(item for item in manifest.artifacts if item.relative_path == "Semantics/semantic-segments.jsonl")
        self._visible(actor, revision_id, "bundle.semantic", "rag_index", (artifact.artifact_id,), semantic=True)
        # Content scope is independently enforced; semantic permission is not a byte-read ticket.
        handle = self.content(actor, revision_id, artifact.artifact_id, "rag_index")
        rows = validate_text(handle.path.read_bytes(), "semantic_segments", artifact.media_type)
        start = int(cursor or "0")
        if start > len(rows):
            raise EngineError("invalid_cursor", "Cursor is outside the fixed semantic revision", 400)
        return c.SemanticPage(bundle_ref=c.BundleRef(schema_version=manifest.schema_version, instance_id=manifest.instance_id, bundle_id=manifest.bundle_id,
                    bundle_revision_id=manifest.bundle_revision_id, manifest_sha256=hashlib.sha256((canonical(manifest) + "\n").encode()).hexdigest()),
                    segments=tuple(rows[start:start + limit]), next_cursor=str(start + limit) if start + limit < len(rows) else None)

    @staticmethod
    def _key(key):
        if not key or len(key) > 128:
            raise EngineError("invalid_idempotency_key", "A bounded nonempty idempotency key is required", 400)

    def _command(self, connection, actor, scope, key, sha):
        self._key(key)
        row = connection.execute("SELECT * FROM commands WHERE owner=? AND scope=? AND idempotency_key=?", (actor.subject_id, scope, key)).fetchone()
        if row and row["request_sha256"] != sha:
            raise EngineError("idempotency_conflict", "Command key already binds a different exact input", 409)
        return json.loads(row["result_json"]) if row else None

    def create_grant(self, actor: AccessContext, revision_id: str, key: str, request: c.BundleGrantRequest) -> c.BundleReferenceGrant:
        row, manifest = self._visible(actor, revision_id, "bundle.grant", "redistribution", request.artifact_ids, semantic=request.allow_semantic_text)
        if actor.subject_id != row["owner"] or not actor.owned_projects:
            raise EngineError("grant_owner_required", "Only the installation's owning principal may grant references", 403)
        recipient = self.principals.principal(request.recipient_id, self.engine.clock())
        if row["project_id"] not in recipient.project_ids or not set(request.purposes) <= recipient.purposes or "bundle.read" not in recipient.operations:
            raise EngineError("recipient_scope_denied", "Recipient registration does not permit this project and use", 403)
        if not request.artifact_ids or len(set(request.artifact_ids)) != len(request.artifact_ids) or not request.purposes or len(set(request.purposes)) != len(request.purposes):
            raise EngineError("grant_scope_invalid", "Grant explicitly selects distinct artifacts and purposes", 422)
        if request.expires_at_us <= self.engine.clock() or (recipient.expires_at_us is not None and request.expires_at_us > recipient.expires_at_us):
            raise EngineError("grant_expiry_denied", "Grant exceeds recipient lifetime", 403)
        for purpose in request.purposes:
            self._rights(manifest, request.artifact_ids, purpose)
        rights = {item.rights_id: item for item in manifest.rights}
        if any(rights[item.rights_ref].expires_at_us is not None and request.expires_at_us > rights[item.rights_ref].expires_at_us for item in manifest.artifacts if item.artifact_id in request.artifact_ids):
            raise EngineError("grant_expiry_denied", "Grant exceeds its actual artifact rights", 403)
        scope, sha = "bundle.grant:" + revision_id, digest(canonical(request))
        with self.engine.db.transaction() as connection:
            existing = self._command(connection, actor, scope, key, sha)
            if existing:
                return c.BundleReferenceGrant.model_validate(existing)
            result = c.BundleReferenceGrant(grant_id=identity("grant"), bundle_ref=self._ref(row), project_id=row["project_id"],
                recipient_id=request.recipient_id, artifact_ids=request.artifact_ids, allow_semantic_text=request.allow_semantic_text,
                purposes=request.purposes, created_at_us=self.engine.clock(), expires_at_us=request.expires_at_us)
            connection.execute("INSERT INTO bundle_grants VALUES(?,?,?,?,?,?,NULL)", (result.grant_id, row["id"], actor.subject_id, result.recipient_id, canonical(result), result.expires_at_us))
            connection.execute("INSERT INTO commands VALUES(?,?,?,?,?)", (actor.subject_id, scope, key, sha, canonical(result)))
            return result

    def revoke_grant(self, actor: AccessContext, grant_id: str) -> c.BundleReferenceGrant:
        self._actor(actor, "bundle.revoke", "redistribution")
        with self.engine.db.transaction() as connection:
            row = connection.execute("SELECT * FROM bundle_grants WHERE id=? AND owner=?", (grant_id, actor.subject_id)).fetchone()
            if not row or not actor.owned_projects:
                raise EngineError("not_found", "Reference grant not found", 404)
            revoked = row["revoked_at_us"] or self.engine.clock()
            connection.execute("UPDATE bundle_grants SET revoked_at_us=? WHERE id=?", (revoked, grant_id))
            return c.BundleReferenceGrant.model_validate_json(row["body"]).model_copy(update={"revoked_at_us": revoked})

    @staticmethod
    def _selection(manifest, request):
        indexed = {item.artifact_id: item for item in manifest.artifacts}
        selected = set(indexed) if request.delivery_profile == "full" else set(request.artifact_ids)
        if not selected <= set(indexed) or len(set(request.artifact_ids)) != len(request.artifact_ids):
            raise EngineError("export_selection_invalid", "Projection selects distinct indexed artifacts", 422)
        if isinstance(manifest, c.BundleManifestV03):
            selected.update((manifest.policy_document_artifact_id, manifest.qualification_document_artifact_id,
                             manifest.benchmark_document_artifact_id, manifest.work_validation_document_artifact_id))
            selected.update(item.artifact_id for item in manifest.artifacts if item.relative_path == "Checks/quality-report.json")
        # Portable production provenance follows projections too. It and its
        # dependencies remain in the ordinary authorized export selector; this
        # does not add a grant for either the source document or its plan.
        selected.update(item.artifact_id for item in manifest.artifacts if item.roles == ("production_authorization",))
        rights = {right.rights_id: right for right in manifest.rights}
        while True:
            expanded = selected | {ref for key in selected for ref in indexed[key].dependency_artifact_ids}
            expanded.update(ref for key in selected for ref in rights[indexed[key].rights_ref].license_document_artifact_ids)
            if not expanded <= set(indexed):
                raise EngineError("bundle_license_missing", "Selected evidence and output need the actual indexed license closure", 422)
            if expanded == selected:
                break
            selected = expanded
        return tuple(item for item in manifest.artifacts if item.artifact_id in selected)

    def request_export(self, actor: AccessContext, revision_id: str, key: str, request: c.BundleExportRequest) -> c.BundleExportAccepted:
        row, manifest = self._visible(actor, revision_id, "bundle.export", request.purpose, request.artifact_ids,
                                       semantic=request.delivery_profile == "full")
        selected = self._selection(manifest, request)
        self._visible(actor, revision_id, "bundle.export", request.purpose, tuple(item.artifact_id for item in selected),
                       semantic=any(item.media_type.startswith(("text/", "application/")) for item in selected))
        return self._journal_export(actor, row, None, manifest, key, request)

    def _journal_export(self, actor, row, imported, manifest, key, request):
        ref = self._origin_ref(imported) if imported else self._ref(row)
        scope = "bundle.export:" + (imported["id"] if imported else ref.bundle_revision_id)
        sha = digest(json.dumps({"bundle_ref": ref.model_dump(mode="json"), "request": request.model_dump(mode="json")}, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        with self.engine.db.transaction() as connection:
            existing = self._command(connection, actor, scope, key, sha)
            if existing:
                return self._export_result(connection.execute("SELECT * FROM bundle_exports WHERE id=?", (existing["export_id"],)).fetchone())
            export_id = identity("export")
            connection.execute("INSERT INTO bundle_exports(id,owner,registration_id,preparation_id,import_id,input_sha256,request_json,actor_json,status,created_at_us) VALUES(?,?,?,?,?,?,?,?,'queued',?)",
                (export_id, actor.subject_id, actor.registration_id, None if imported else row["id"], imported["id"] if imported else None,
                 sha, canonical(request), json.dumps({"subject_id": actor.subject_id, "registration_id": actor.registration_id}), self.engine.clock()))
            result = self._export_result(connection.execute("SELECT * FROM bundle_exports WHERE id=?", (export_id,)).fetchone())
            connection.execute("INSERT INTO commands VALUES(?,?,?,?,?)", (actor.subject_id, scope, key, sha, canonical(result)))
            return result

    def _export_result(self, row):
        if row is None:
            raise EngineError("not_found", "Export job not found", 404)
        with self.engine.db.connect() as connection:
            if row["import_id"]:
                imported = connection.execute("SELECT * FROM bundle_imports WHERE id=?", (row["import_id"],)).fetchone()
                ref = self._origin_ref(imported)
            else:
                revision = connection.execute("SELECT * FROM bundle_revisions WHERE id=?", (row["preparation_id"],)).fetchone()
                ref = self._ref(revision)
        return c.BundleExportAccepted(export_id=row["id"], bundle_ref=ref,
            delivery_profile=c.BundleExportRequest.model_validate_json(row["request_json"]).delivery_profile,
            status=row["status"], input_sha256=row["input_sha256"], status_path=f"/api/v1/bundle-exports/{row['id']}",
            archive_sha256=row["archive_sha256"], size=row["size"], error_code=row["error_code"],
            content_path=f"/api/v1/bundle-exports/{row['id']}/content" if row["status"] == "ready" else None)

    def _export_scope(self, actor, row):
        if row is None or (row["owner"], row["registration_id"]) != (actor.subject_id, actor.registration_id):
            raise EngineError("not_found", "Export job not found", 404)
        request = c.BundleExportRequest.model_validate_json(row["request_json"])
        if row["import_id"]:
            imported, manifest = self._import_visible(actor, row["import_id"], "bundle.export", request.purpose)
            self._rights(manifest, tuple(item.artifact_id for item in self._selection(manifest, request)), request.purpose)
            return None, imported, manifest, request
        with self.engine.db.connect() as connection:
            revision = connection.execute("SELECT revision_id FROM bundle_revisions WHERE id=?", (row["preparation_id"],)).fetchone()
        if not revision:
            raise EngineError("not_found", "Bundle revision not found", 404)
        original, manifest = self._visible(actor, revision[0], "bundle.export", request.purpose, request.artifact_ids, semantic=request.delivery_profile == "full")
        self._visible(actor, revision[0], "bundle.export", request.purpose, tuple(item.artifact_id for item in self._selection(manifest, request)),
                       semantic=any(item.media_type.startswith(("text/", "application/")) for item in self._selection(manifest, request)))
        return original, None, manifest, request

    def export_status(self, actor: AccessContext, export_id: str) -> c.BundleExportAccepted:
        with self.engine.db.connect() as connection:
            row = connection.execute("SELECT * FROM bundle_exports WHERE id=?", (export_id,)).fetchone()
        self._export_scope(actor, row)
        return self._export_result(row)

    def export_content(self, actor: AccessContext, export_id: str) -> BundleContentHandle:
        return self._export_content_facts(actor, export_id).handle

    def _export_content_facts(self, actor, export_id):
        # Only this original export journal chain changes: resolver preserves
        # exact owner/registration, original purpose/request/selection,
        # bundle.export, complete public closure/semantic scope, ready archive
        # and verified original bytes. A caller supplies no replacement purpose.
        from video_creator.application.delivery_metadata import DeliveryResolver
        return DeliveryResolver(self).resolve("export_archive", actor, export_id)

    def export_metadata(self, actor: AccessContext, export_id: str) -> c.DeliveryContentMetadata:
        return self._export_content_facts(actor, export_id).metadata(self.engine.instance_id)

    def acquire_export(self, worker_id: str, lease_seconds: int = 180) -> ExportLease | None:
        if not worker_id or not 1 <= lease_seconds <= 3600:
            raise EngineError("invalid_lease", "Export lease is bounded and has a worker identity", 400)
        with self.engine.db.transaction() as connection:
            row = connection.execute("SELECT * FROM bundle_exports WHERE status='queued' OR (status='building' AND lease_until_us<=?) ORDER BY rowid LIMIT 1", (self.engine.clock(),)).fetchone()
            if not row:
                return None
            fence, expiry = row["fencing_token"] + 1, self.engine.clock() + lease_seconds * 1_000_000
            connection.execute("UPDATE bundle_exports SET status='building',worker_id=?,fencing_token=?,lease_until_us=? WHERE id=?", (worker_id, fence, expiry, row["id"]))
            return ExportLease(row["id"], worker_id, fence, expiry)

    def _export_lease(self, connection, lease):
        row = connection.execute("SELECT * FROM bundle_exports WHERE id=?", (lease.export_id,)).fetchone()
        if not row or row["status"] != "building" or (row["worker_id"], row["fencing_token"]) != (lease.worker_id, lease.fencing_token) or row["lease_until_us"] <= self.engine.clock():
            raise EngineError("stale_export_lease", "Export worker lease expired or was superseded", 409, "reconcile")
        return row

    def heartbeat_export(self, lease: ExportLease, lease_seconds: int = 180) -> ExportLease:
        if not 1 <= lease_seconds <= 3600:
            raise EngineError("invalid_lease", "Export lease lifetime is bounded", 400)
        with self.engine.db.transaction() as connection:
            self._export_lease(connection, lease)
            expiry = self.engine.clock() + lease_seconds * 1_000_000
            connection.execute("UPDATE bundle_exports SET lease_until_us=? WHERE id=?", (expiry, lease.export_id))
        return ExportLease(lease.export_id, lease.worker_id, lease.fencing_token, expiry)

    def _archive_entries(self, actor, row):
        revision, imported, manifest, request = self._export_scope(actor, row)
        selected = self._selection(manifest, request)
        if request.delivery_profile == "full":
            raw = (imported or revision)["manifest_json"].encode()
            entries = [("bundle.manifest.json", raw, hashlib.sha256(raw).hexdigest(), len(raw))]
        else:
            projection_type = c.DeliveryProjectionManifestV03 if isinstance(manifest, c.BundleManifestV03) else c.DeliveryProjectionManifest
            projection = projection_type(schema_version=manifest.schema_version, parent_bundle_ref=self._origin_ref(imported) if imported else self._ref(revision),
                artifacts=selected, purpose=request.purpose, created_at_us=row["created_at_us"])
            raw = (canonical(projection) + "\n").encode()
            entries = [("delivery.manifest.json", raw, hashlib.sha256(raw).hexdigest(), len(raw))]
        for item in selected:
            handle = self.import_content(actor, imported["id"], item.artifact_id, request.purpose) if imported else self.content(actor, revision["revision_id"], item.artifact_id, request.purpose)
            entries.append((item.relative_path, handle.path, item.sha256, item.size))
        if sum(entry[3] for entry in entries) > self.assets.max_bytes:
            raise EngineError("export_size_denied", "Exact archive exceeds the installation limit", 413)
        return entries

    def _check_archive(self, path, entries):
        try:
            with zipfile.ZipFile(path) as archive:
                infos = archive.infolist()
                if [value.filename for value in infos] != [entry[0] for entry in entries]:
                    raise ValueError("archive entry set")
                for info, (_, source, sha, size) in zip(infos, entries, strict=True):
                    if info.file_size != size or info.flag_bits & 1 or info.is_dir():
                        raise ValueError("archive metadata")
                    hasher = hashlib.sha256()
                    count = 0
                    with archive.open(info) as stream:
                        while block := stream.read(1024 * 1024):
                            count += len(block)
                            if count > size:
                                raise ValueError("archive size")
                            hasher.update(block)
                    if count != size or hasher.hexdigest() != sha or (isinstance(source, bytes) and archive.read(info) != source):
                        raise ValueError("archive content")
        except (ValueError, OSError, zipfile.BadZipFile, RuntimeError):
            raise EngineError("export_integrity_failed", "Archive does not contain the exact journaled delivery", 422) from None

    def build_export(self, lease: ExportLease) -> c.BundleExportAccepted:
        with self.engine.db.connect() as connection:
            row = self._export_lease(connection, lease)
        actor = self.principals.principal(row["registration_id"], self.engine.clock()) if row["registration_id"] else self.principals.owner()
        if actor.subject_id != row["owner"]:
            raise EngineError("export_principal_changed", "Export owner registration changed", 403)
        entries = self._archive_entries(actor, row)
        deadline = time.monotonic() + 120
        def checkpoint():
            if self._export_stop.is_set() or time.monotonic() >= deadline:
                raise EngineError("export_interrupted", "Export executor stopped or reached its bounded deadline", 409, "reconcile")
            with self.engine.db.connect() as connection:
                self._export_lease(connection, lease)
            self._export_scope(actor, row)
        old_key = row["archive_file_key"]
        old_path = self._file("BundleExports", old_key) if old_key else None
        if old_path and old_path.is_file():
            self._check_archive(old_path, entries)
            path, key = old_path, old_key
        else:
            key = f"{row['id']}-f{lease.fencing_token}.zip"
            (self.engine.db.data_dir / "BundleExports").mkdir(exist_ok=True)
            path = self._file("BundleExports", key)
            partial = self._file("BundleExports", key + ".partial")
            with self.engine.db.transaction() as connection:
                self._export_lease(connection, lease)
                connection.execute("UPDATE bundle_exports SET archive_file_key=? WHERE id=?", (key, row["id"]))
            # A superseded fence writes to a different journaled file identity.
            with partial.open("xb") as output, zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
                for name, source, sha, size in entries:
                    checkpoint()
                    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                    info.external_attr = 0o100600 << 16
                    info.compress_type = zipfile.ZIP_STORED
                    hasher, count = hashlib.sha256(), 0
                    with archive.open(info, "w") as target:
                        if isinstance(source, bytes):
                            target.write(source)
                            hasher.update(source)
                            count = len(source)
                        else:
                            with source.open("rb") as original:
                                while block := original.read(1024 * 1024):
                                    checkpoint()
                                    count += len(block)
                                    if count > size:
                                        raise EngineError("bundle_integrity_failed", "Source changed while exporting", 422)
                                    hasher.update(block)
                                    target.write(block)
                    if count != size or hasher.hexdigest() != sha:
                        raise EngineError("bundle_integrity_failed", "Source changed while exporting", 422)
            with partial.open("r+b") as completed:
                os.fsync(completed.fileno())
            checkpoint()
            os.replace(partial, path)
            self._check_archive(path, entries)
        archive_sha, size = self.assets._hash(path), path.stat().st_size
        self._export_scope(actor, row)
        with self.engine.db.transaction() as connection:
            self._export_lease(connection, lease)
            connection.execute("UPDATE bundle_exports SET status='ready',worker_id=NULL,lease_until_us=0,archive_file_key=?,archive_sha256=?,size=?,error_code=NULL WHERE id=?", (key, archive_sha, size, row["id"]))
            return self._export_result(connection.execute("SELECT * FROM bundle_exports WHERE id=?", (row["id"],)).fetchone())

    def start_exports(self):
        with self._lock:
            self._export_users += 1
            if self._export_thread and self._export_thread.is_alive():
                return
            self._export_stop.clear()
            def run():
                worker_id = identity("export-worker")
                while not self._export_stop.is_set():
                    lease = self.acquire_export(worker_id)
                    if not lease:
                        self._export_stop.wait(0.25)
                        continue
                    try:
                        self.build_export(lease)
                    except (EngineError, OSError, zipfile.BadZipFile):
                        with self.engine.db.transaction() as connection:
                            try:
                                self._export_lease(connection, lease)
                            except EngineError:
                                continue
                            connection.execute("UPDATE bundle_exports SET status=?,worker_id=NULL,lease_until_us=0,error_code=? WHERE id=?", ("queued" if self._export_stop.is_set() else "failed", "export_interrupted" if self._export_stop.is_set() else "export_failed", lease.export_id))
            self._export_thread = threading.Thread(target=run, name="video-creator-export", daemon=True)
            self._export_thread.start()

    def stop_exports(self, timeout_seconds: float = 5):
        with self._lock:
            self._export_users = max(0, self._export_users - 1)
            if self._export_users:
                return
            self._export_stop.set()
        if self._export_thread:
            self._export_thread.join(timeout_seconds)
            if self._export_thread.is_alive():
                raise EngineError("export_cleanup_incomplete", "Export executor has not actually stopped", 503)

    @staticmethod
    def _origin_ref(row):
        return c.BundleRef.model_validate_json(row["origin_ref_json"])

    def _import_visible(self, actor, import_id, operation, purpose):
        self._actor(actor, operation, purpose)
        with self.engine.db.connect() as connection:
            row = connection.execute("SELECT * FROM bundle_imports WHERE id=? AND owner=?", (import_id, actor.subject_id)).fetchone()
        if not row or not (actor.owned_projects or row["project_id"] in actor.project_ids):
            raise EngineError("not_found", "Local bundle import not found", 404)
        manifest = c.parse_bundle_manifest(row["manifest_json"])
        return row, manifest

    def _import_receipt(self, row):
        model = c.BundleImportReceiptV03 if self._origin_ref(row).schema_version == c.V03_SCHEMA_VERSION else c.BundleImportReceipt
        return model(import_id=row["id"], local_instance_id=self.engine.instance_id, project_id=row["project_id"],
            origin_bundle_ref=self._origin_ref(row), status_path=f"/api/v1/bundle-imports/{row['id']}",
            manifest_path=f"/api/v1/bundle-imports/{row['id']}/manifest", index_state=row["index_state"])

    def import_status(self, actor: AccessContext, import_id: str) -> c.BundleImportReceipt:
        row, _ = self._import_visible(actor, import_id, "bundle.read", "playback")
        return self._import_receipt(row)

    def import_manifest(self, actor: AccessContext, import_id: str, purpose: str = "playback") -> c.BundleManifest:
        return self._import_manifest_content_facts(actor, import_id, purpose).scope.manifest

    def _import_manifest_content_facts(self, actor, import_id, purpose):
        # Original bundle.read/purpose and local import owner/project checks
        # remain. No playback-only import_get or foreign grant is substituted.
        self._actor(actor, "bundle.read", purpose)
        from video_creator.application.delivery_metadata import DeliveryResolver
        return DeliveryResolver(self).resolve("import_manifest", actor, import_id, purpose=purpose)

    def import_manifest_content(self, actor: AccessContext, import_id: str, purpose: str = "playback") -> BundleContentHandle:
        return self._import_manifest_content_facts(actor, import_id, purpose).handle

    def import_manifest_metadata(self, actor: AccessContext, import_id: str, purpose: str = "playback") -> c.DeliveryContentMetadata:
        return self._import_manifest_content_facts(actor, import_id, purpose).metadata(self.engine.instance_id)

    def import_content(self, actor: AccessContext, import_id: str, artifact_id: str, purpose: str = "playback") -> BundleContentHandle:
        return self._import_leaf_content_facts(actor, import_id, artifact_id, purpose).handle

    def _import_leaf_content_facts(self, actor, import_id, artifact_id, purpose):
        # Imported leaf retains exact local owner/project, bundle.content and
        # requested purpose; foreign origin refs never authorize local access.
        self._actor(actor, "bundle.content", purpose)
        from video_creator.application.delivery_metadata import DeliveryResolver
        return DeliveryResolver(self).resolve("import_artifact", actor, import_id, artifact_id, purpose)

    def import_content_metadata(self, actor: AccessContext, import_id: str, artifact_id: str, purpose: str = "playback") -> c.DeliveryContentMetadata:
        return self._import_leaf_content_facts(actor, import_id, artifact_id, purpose).metadata(self.engine.instance_id)

    def request_import_export(self, actor: AccessContext, import_id: str, key: str, request: c.BundleExportRequest) -> c.BundleExportAccepted:
        imported, manifest = self._import_visible(actor, import_id, "bundle.export", request.purpose)
        self._rights(manifest, tuple(value.artifact_id for value in self._selection(manifest, request)), request.purpose)
        return self._journal_export(actor, None, imported, manifest, key, request)

    @staticmethod
    def _material_kind(artifact, version=c.SCHEMA_VERSION, correction_origins=None):
        if "production_authorization" in artifact.roles or artifact.relative_path == AUTHORIZATION_PATH:
            if (artifact.roles != ("production_authorization",) or artifact.relative_path != AUTHORIZATION_PATH
                    or artifact.media_type != "application/json" or not artifact.material_id):
                raise EngineError("production_authorization_kind_invalid", "Authorization has its own exact role/path/MIME/schema", 415)
            return "production_authorization"
        fixed = {"Creative/insight.json": "creative_revision", "Creative/brief.json": "creative_revision",
            "Creative/production-plan.json": "creative_revision", "Text/approved-script.json": "approved_script",
            "Text/actual-transcript.json": "actual_transcript", "Text/subtitles.srt": "srt", "Text/subtitles.vtt": "vtt",
            "Semantics/work-summary.json": "work_summary", "Semantics/source-bindings.json": "source_bindings",
            "Semantics/shots.jsonl": "shots", "Semantics/semantic-segments.jsonl": "semantic_segments",
            "Semantics/rag-chunks.jsonl": "rag_chunks", "Checks/quality-report.json": "quality"}
        if version == local.LOCAL_SCHEMA_VERSION:
            local_fixed = {'Checks/local-master-selection.json': 'local_master_selection',
                'Checks/local-speech-evidence.json': 'local_speech_evidence',
                'Semantics/visual-mapping.json': 'visual_mapping_local',
                'Text/actual-transcript.json': 'actual_transcript_local',
                'Checks/quality-report.json': 'quality_local', 'Semantics/shots.jsonl': 'shots_local',
                'Semantics/semantic-segments.jsonl': 'semantic_segments_local',
                'Semantics/rag-chunks.jsonl': 'rag_chunks_local', 'Text/subtitles.srt': 'srt_local',
                'Text/subtitles.vtt': 'vtt_local'}
            if artifact.relative_path in local_fixed:
                return local_fixed[artifact.relative_path]
        if artifact.relative_path in fixed:
            kind = fixed[artifact.relative_path]
            return "actual_transcript_v03" if version == c.V03_SCHEMA_VERSION and kind == "actual_transcript" else kind
        if version in {c.V03_SCHEMA_VERSION, local.LOCAL_SCHEMA_VERSION}:
            for role in ("method_benchmark", "method_benchmark_reference", "method_benchmark_self_issued",
                         "method_qualification", "evidence_policy", "work_alignment_validation"):
                if role in artifact.roles:
                    if artifact.roles != (role,):
                        raise EngineError("import_evidence_kind_invalid", "Versioned evidence has one exact admitted kind/role", 415)
                    return role
            if "precision_evaluation" in artifact.roles:
                if artifact.roles != ("precision_evaluation",):
                    raise EngineError("import_evidence_kind_invalid", "Measurement has its own exact admitted role", 415)
                origin = (correction_origins or {}).get(artifact.artifact_id)
                if origin is not None:
                    if origin.sha256 != artifact.sha256:
                        raise EngineError("correction_origin_integrity_failed", "Indexed audit origin differs from its immutable file hash", 422)
                    if origin.schema_version == c.SCHEMA_VERSION:
                        return "precision_report"
                return "precision_report_v03"
            if "precision_reference" in artifact.roles:
                if artifact.roles != ("precision_reference",):
                    raise EngineError("import_evidence_kind_invalid", "Reference has its own exact admitted role", 415)
                return "precision_reference_v03"
        if "precision_evaluation" in artifact.roles:
            return "precision_report"
        if "license" in artifact.roles:
            return "license"
        if "precision_reference" in artifact.roles or "audit_summary" in artifact.roles:
            return "audit_summary"
        raise EngineError("import_material_unrecognized", "Additional text requires an admitted schema role", 415)

    @staticmethod
    def _correction_origins(documents):
        origins = {}
        for report in documents.values():
            if isinstance(report, c.PrecisionEvaluationReportV03) and report.corrected_from:
                ref = report.corrected_from
                if ref.artifact_id in origins and origins[ref.artifact_id] != ref:
                    raise EngineError("correction_lineage_invalid", "One original audit artifact cannot have conflicting identities", 422)
                origins[ref.artifact_id] = ref
        return origins

    def _import_documents(self, manifest, materials):
        # Only a fully parsed, explicitly versioned correction report can
        # select the old audit grammar. A payload cannot choose its own kind.
        documents, deferred = {}, []
        for artifact in manifest.artifacts:
            if not artifact.material_id:
                continue
            raw = materials[artifact.relative_path]
            if manifest.schema_version == c.V03_SCHEMA_VERSION and artifact.roles == ("precision_evaluation",):
                body = strict_json(raw)
                if not isinstance(body, dict) or body.get("schema_version") != c.V03_SCHEMA_VERSION:
                    deferred.append(artifact)
                    continue
            documents[artifact.relative_path] = validate_text(raw, self._material_kind(artifact, manifest.schema_version), artifact.media_type)
        origins = self._correction_origins(documents)
        for artifact in deferred:
            documents[artifact.relative_path] = validate_text(materials[artifact.relative_path],
                self._material_kind(artifact, manifest.schema_version, origins), artifact.media_type)
        self._correction_closure(manifest, documents)
        return documents

    def _correction_closure(self, manifest, documents, *, lease=None):
        indexed = {item.artifact_id: item for item in manifest.artifacts}
        for item in manifest.artifacts:
            report = documents.get(item.relative_path)
            if not isinstance(report, c.PrecisionEvaluationReportV03) or not report.corrected_from:
                continue
            ref = report.corrected_from
            origin = indexed.get(ref.artifact_id)
            original = documents.get(origin.relative_path) if origin else None
            expected_type = c.PrecisionEvaluationReport if ref.schema_version == c.SCHEMA_VERSION else c.PrecisionEvaluationReportV03
            if (not origin or not origin.material_id or origin.roles != ("precision_evaluation",)
                    or origin.sha256 != ref.sha256 or type(original) is not expected_type
                    or ref.artifact_id == item.artifact_id or ref.report_id == report.evaluation_id
                    or ref.artifact_id not in item.dependency_artifact_ids):
                raise EngineError("correction_origin_unavailable", "Complete correction delivery requires the exact indexed original audit bytes and forward dependency", 422)
            if (original.evaluation_id, original.content_sha256, original.alignment_revision_id, original.alignment_content_sha256) != (
                    ref.report_id, ref.content_sha256, ref.alignment_revision_id, ref.alignment_content_sha256):
                raise EngineError("correction_origin_integrity_failed", "Original audit report identities differ from the explicit correction locator", 422)
            if lease is not None:
                # The original material ID is a source locator. A new durable
                # delivery allocation may differ; full file SHA binds its copy.
                self.correction_origin(lease, ref)

    def _parse_import(self, archive_path, request):
        try:
            with zipfile.ZipFile(archive_path) as archive:
                infos = archive.infolist()
                if len(infos) > 512 or any(info.is_dir() or info.flag_bits & 1 or (info.external_attr >> 16) & 0o170000 not in {0, 0o100000} for info in infos):
                    raise ValueError("archive metadata")
                names = [info.filename for info in infos]
                if "delivery.manifest.json" in names:
                    raise EngineError("unsupported_delivery_profile", "A projection is not a complete original bundle", 415)
                if not names or names[0] != "bundle.manifest.json" or len({value.casefold() for value in names}) != len(names):
                    raise ValueError("archive index")
                total = sum(info.file_size for info in infos)
                if total > self.assets.max_bytes or any(info.file_size <= 0 or info.compress_size == 0 or info.file_size > max(info.compress_size * 100, 1024 * 1024) for info in infos):
                    raise EngineError("import_size_denied", "Bundle archive exceeds bounded extraction limits", 413)
                if infos[0].file_size > 16 * 1024 * 1024:
                    raise ValueError("manifest size")
                raw = archive.read(infos[0])
                manifest = c.parse_bundle_manifest(strict_json(raw))
                ref = c.BundleRef(schema_version=manifest.schema_version, instance_id=manifest.instance_id, bundle_id=manifest.bundle_id, bundle_revision_id=manifest.bundle_revision_id, manifest_sha256=hashlib.sha256(raw).hexdigest())
                if ref != request.expected_origin_ref:
                    raise EngineError("import_origin_conflict", "Exact original identity and manifest hash do not match", 409)
                if set(manifest.requested_outputs) != FULL_OUTPUTS or not FIXED_FILES <= {item.relative_path for item in manifest.artifacts}:
                    raise EngineError("import_incomplete", "Import requires the complete original eight-output profile", 422)
                if names != ["bundle.manifest.json", *(item.relative_path for item in manifest.artifacts)]:
                    raise ValueError("unregistered or reordered archive entries")
                materials = {}
                for info, artifact in zip(infos[1:], manifest.artifacts, strict=True):
                    if info.file_size != artifact.size:
                        raise ValueError("artifact size")
                    value = archive.read(info)
                    if hashlib.sha256(value).hexdigest() != artifact.sha256:
                        raise ValueError("artifact hash")
                    if artifact.material_id:
                        materials[artifact.relative_path] = value
                documents = self._import_documents(manifest, materials)
                self._validate_import_relations(manifest, documents)
                return raw, manifest
        except (ValueError, OSError, zipfile.BadZipFile, RuntimeError, ValidationError):
            raise EngineError("bundle_import_invalid", "Archive does not satisfy the unchanged original bundle contract", 422) from None

    def _validate_import_relations(self, manifest, documents):
        # Foreign provenance is validated against its original work only; this
        # pure branch cannot install or resolve a local execution authorization.
        validate_portable_authorization(manifest, documents)
        by_path = {item.relative_path: item for item in manifest.artifacts}
        actual = documents.get("Text/actual-transcript.json")
        segments = documents.get("Semantics/semantic-segments.jsonl")
        chunks = documents.get("Semantics/rag-chunks.jsonl")
        quality = documents.get("Checks/quality-report.json")
        if not isinstance(actual, (c.ActualTranscriptDocument, c.ActualTranscriptDocumentV03)) or not segments or not chunks or not isinstance(quality, c.BundleQualityEvidence):
            raise EngineError("import_incomplete", "Complete actual speech and semantic materials are required", 422)
        video, mixed = by_path["Media/video.mp4"], by_path["Media/mixed-audio.wav"]
        if video.spec.duration_us != manifest.timeline_duration_us or mixed.spec.duration_us != manifest.timeline_duration_us:
            raise EngineError("import_media_binding_invalid", "Original final video and mixed audio must bind the work duration", 422)
        if (actual.transcript.input_audio_asset_id, actual.transcript.input_audio_sha256) != (mixed.asset_id, mixed.sha256):
            admitted = [item for item in manifest.artifacts if "asr_input" in item.roles and video.artifact_id in item.dependency_artifact_ids]
            if not any((item.asset_id, item.sha256) == (actual.transcript.input_audio_asset_id, actual.transcript.input_audio_sha256) for item in admitted):
                raise EngineError("import_transcript_binding_invalid", "Actual transcript is not bound to registered final audio", 422)
        if (actual.alignment.actual_transcript_revision_id, actual.alignment.transcript_content_sha256, actual.alignment.input_audio_sha256) != (actual.transcript.transcript_revision_id, actual.transcript.content_sha256, actual.transcript.input_audio_sha256):
            raise EngineError("import_alignment_invalid", "Original alignment differs from the original actual transcript", 422)
        unit_ids = [value.utterance_id for value in actual.transcript.utterances] if actual.alignment.units == "utterance" else [word.word_id for value in actual.transcript.utterances for word in value.words]
        aligned_ids = [value.transcript_unit_id for value in actual.alignment.boundaries]
        if (not unit_ids or len(unit_ids) != len(set(unit_ids)) or len(aligned_ids) != len(set(aligned_ids))
                or set(unit_ids) != set(aligned_ids) or any(value.intrinsic_range.end_us > actual.transcript.duration_us for value in actual.alignment.boundaries)):
            raise EngineError("import_alignment_invalid", "Origin alignment units are complete, distinct and within actual audio", 422)
        srt, vtt, errors = serialize_subtitles(actual.subtitles)
        if errors != actual.subtitles.quantization_errors or documents.get("Text/subtitles.srt") != srt.decode() or documents.get("Text/subtitles.vtt") != vtt.decode():
            raise EngineError("import_subtitle_invalid", "Original subtitle bytes differ from their declared serializer", 422)
        if isinstance(manifest, c.BundleManifestV03):
            self._validate_import_v03_evidence(manifest, documents, actual, quality)
        else:
            precision = actual.alignment.precision
            if precision.status != "measured" or precision.p95_error_us > LIMIT_US:
                raise EngineError("import_precision_missing", "Complete origin must carry its actual measured precision evidence", 422)
            report = next((value for item in manifest.artifacts if item.material_id == precision.evaluation_material_id
                and isinstance(value := documents.get(item.relative_path), c.PrecisionEvaluationReport)), None)
            if not report or (report.alignment_content_sha256, report.input_audio_sha256, report.alignment_revision_id, report.units,
                              report.criterion_version_ref) != (actual.alignment.content_sha256, actual.transcript.input_audio_sha256,
                              actual.alignment.alignment_revision_id, precision.units, precision.criterion_version_ref):
                raise EngineError("import_precision_missing", "Exact original independent precision report is missing", 422)
            reference = next((documents.get(item.relative_path) for item in manifest.artifacts if item.material_id == report.reference_material_id), None)
            if not isinstance(reference, dict) or not isinstance(reference.get("reference_boundaries"), list):
                raise EngineError("precision_reference_invalid", "Complete original reference array is required", 422)
            references = tuple(c.PrecisionReferenceUnit.model_validate(value) for value in reference["reference_boundaries"])
            count, p95 = nearest_rank(unit_errors(actual.alignment.boundaries, references, report.boundaries, actual.transcript.duration_us))
            if (precision.sample_count, precision.p95_error_us) != (count, p95):
                raise EngineError("criterion_mismatch", "Original precision record differs from whole-unit max/N criterion", 422)
        known_segments = {item.segment_id: item for item in segments}
        if len(known_segments) != len(segments) or any(item.bundle_revision_id != manifest.bundle_revision_id or item.video_asset_id != video.asset_id or item.video_range.end_us > manifest.timeline_duration_us for item in segments):
            raise EngineError("import_semantic_invalid", "Original semantic locations do not bind this video revision", 422)
        if any(item.bundle_revision_id != manifest.bundle_revision_id or any(ref not in known_segments for ref in item.segment_ids) for item in chunks):
            raise EngineError("import_rag_invalid", "Original RAG records differ from their segment revision", 422)
        # Import validates original evidence and bytes; it does not mint a local ASR
        # operation, inherit origin grants, or certify a foreign precision authority.

    def _validate_import_v03_evidence(self, manifest, documents, actual, quality):
        indexed = {item.artifact_id: item for item in manifest.artifacts}
        def document(ref, model):
            item = indexed[ref]
            value = documents.get(item.relative_path)
            if not item.material_id or not isinstance(value, model):
                raise EngineError("import_evidence_missing", "Origin evidence must be a complete actual indexed document", 422)
            check_record(value)
            return value
        policy = document(manifest.policy_document_artifact_id, c.EvidencePolicyRevision)
        qualification = document(manifest.qualification_document_artifact_id, c.MethodQualificationRef)
        work = document(manifest.work_validation_document_artifact_id, c.WorkAlignmentValidationReport)
        policy_ref = c.EvidencePolicyRevisionRef(policy_id=policy.policy_id, revision=policy.revision, content_sha256=policy.content_sha256)
        if (manifest.evidence_policy_revision_ref, manifest.qualification_ref, policy.qualification_ref) != (policy_ref, qualification, qualification):
            raise EngineError("import_evidence_binding_invalid", "Origin policy/qualification references differ from complete material bytes", 422)
        if not isinstance(actual, c.ActualTranscriptDocumentV03) or not isinstance(quality, c.BundleQualityEvidenceV03):
            raise EngineError("import_evidence_version_conflict", "Explicit 0.3 requires its own actual transcript and quality schemas", 422)
        if (work.production_id, work.run_id, work.request_revision_id, work.request_sha256, work.input_audio_asset_id,
            work.input_audio_sha256, work.transcript_content_sha256, work.alignment_content_sha256, work.subtitle_content_sha256,
            work.execution_identity, work.evidence_policy_revision_ref, work.qualification_ref) != (
                manifest.production_id, manifest.run_id, manifest.request_revision_id, manifest.request_sha256, actual.transcript.input_audio_asset_id,
                actual.transcript.input_audio_sha256, actual.transcript.content_sha256, actual.alignment.content_sha256,
                actual.subtitles.content_sha256, qualification.execution_identity, policy_ref, qualification):
            raise EngineError("import_evidence_binding_invalid", "Origin runtime report differs from the immutable original work/revisions", 422)
        if work.result != "verified" or work.source_gaps or work.reasons or not set(policy.required_checks) <= {item.check_id for item in work.checks if item.status == "verified"}:
            raise EngineError("import_evidence_incomplete", "Origin runtime evidence is incomplete", 422)
        if (quality.evidence_policy_revision_ref, quality.qualification_ref, quality.work_validation_report_ref.report_id,
            quality.work_validation_report_ref.content_sha256) != (policy_ref, qualification, work.report_id, work.content_sha256):
            raise EngineError("import_evidence_binding_invalid", "Origin quality binds a different scoped runtime report", 422)
        benchmark_models = {'embedded_full_report': c.MethodBenchmarkReport,
                            'embedded_self_issued': c.LocalSelfIssuedBenchmarkV1,
                            'provenance_reference': c.MethodBenchmarkReference}
        benchmark_model = benchmark_models.get(manifest.benchmark_binding)
        if benchmark_model is None:
            raise EngineError('import_benchmark_binding_invalid', 'Origin benchmark binding is not admitted', 422)
        benchmark = document(manifest.benchmark_document_artifact_id, benchmark_model)
        if isinstance(benchmark, c.MethodBenchmarkReport):
            validate_benchmark(benchmark)
            if (qualification.benchmark_report_ref.report_id, qualification.benchmark_report_ref.content_sha256,
                qualification.execution_identity, qualification.applicability) != (benchmark.report_id, benchmark.content_sha256,
                benchmark.execution_identity, benchmark.applicability):
                raise EngineError("import_benchmark_binding_invalid", "Origin qualification differs from the actual embedded benchmark", 422)
        elif isinstance(benchmark, c.LocalSelfIssuedBenchmarkV1):
            validate_self_issued_benchmark(benchmark)
            if (qualification.benchmark_report_ref.report_id, qualification.benchmark_report_ref.content_sha256,
                qualification.execution_identity, qualification.applicability, qualification.authority_ref) != (benchmark.report_id,
                benchmark.content_sha256, benchmark.execution_identity, benchmark.applicability, benchmark.authority_ref):
                raise EngineError("import_benchmark_binding_invalid",
                                  "Origin qualification differs from the actual self-issued declaration", 422)
        elif (benchmark.origin_report_ref, benchmark.execution_identity, benchmark.applicability) != (
                qualification.benchmark_report_ref, qualification.execution_identity, qualification.applicability):
            raise EngineError("import_benchmark_binding_invalid", "Origin provenance reference cannot replace the original benchmark SHA", 422)
        elif benchmark.license_ref not in {right.rights_id for right in manifest.rights}:
            raise EngineError("import_benchmark_license_missing", "Reference disclosure has no original license scope", 403)
        precision = actual.alignment.precision
        reports = [value for value in documents.values() if isinstance(value, c.PrecisionEvaluationReportV03)]
        if precision.status != "measured":
            if reports or quality.per_work_measurement_report_ref or policy.alignment_evidence_policy == "strict_reference_v1":
                raise EngineError("import_precision_invalid", "Unmeasured qualified origin has no measurement report and strict origin needs a reference", 422)
        else:
            self._verify_per_work_precision(manifest, documents, actual)
        if actual.alignment.units != qualification.applicability.units or actual.alignment.units != ("word" if policy.alignment_requirement == "word_verified" else "utterance"):
            raise EngineError("import_alignment_scope_invalid", "Origin unit scope does not satisfy the actual qualified policy", 422)
        # Origin structure is not local issuer admission/current revocation or
        # new execution eligibility. Initial import status stays snapshot only.

    def import_bundle(self, actor: AccessContext, key: str, request: c.BundleImportRequest) -> c.BundleImportReceipt:
        self._actor(actor, "bundle.import", "export")
        with self.engine.db.connect() as connection:
            project = connection.execute("SELECT * FROM projects WHERE id=? AND owner=?", (request.project_id, actor.subject_id)).fetchone()
            staged = connection.execute("SELECT * FROM staging WHERE id=? AND owner=?", (request.staging_id, actor.subject_id)).fetchone()
        if not project or not (actor.owned_projects or request.project_id in actor.project_ids):
            raise EngineError("not_found", "Destination project not found", 404)
        if not staged or staged["status"] != "ready" or staged["media_type"] != "application/zip":
            raise EngineError("not_found", "Owned ready ZIP staging not found", 404)
        archive_path = self.assets.staging_path(actor.subject_id, request.staging_id)
        if self.assets._hash(archive_path) != request.archive_sha256 or staged["sha256"] != request.archive_sha256 or archive_path.stat().st_size != staged["size"]:
            raise EngineError("import_integrity_failed", "Original controlled archive bytes changed", 422)
        raw, manifest = self._parse_import(archive_path, request)
        origin_key = digest(canonical(request.expected_origin_ref))
        sha, scope = digest(canonical(request)), "bundle.import"
        self._key(key)
        worker, deadline = identity("import-worker"), time.monotonic() + 120
        with self.engine.db.transaction() as connection:
            previous = self._command(connection, actor, scope, key, sha)
            ready = connection.execute("SELECT * FROM bundle_imports WHERE owner=? AND project_id=? AND origin_key=?", (actor.subject_id, request.project_id, origin_key)).fetchone()
            if ready:
                result = self._import_receipt(ready)
                if not previous:
                    connection.execute("INSERT INTO commands VALUES(?,?,?,?,?)", (actor.subject_id, scope, key, sha, canonical(result)))
                return result
            if previous and previous.get("lease_until_us", 0) > self.engine.clock():
                raise EngineError("import_in_progress", "Original import already has a live bounded worker", 409, "safe")
            progress = {"import_id": previous["import_id"] if previous else identity("import"), "worker_id": worker,
                "fencing_token": previous.get("fencing_token", 0) + 1 if previous else 1, "lease_until_us": self.engine.clock() + 180_000_000,
                "bindings": previous.get("bindings", {}) if previous else {}}
            if previous:
                connection.execute("UPDATE commands SET result_json=? WHERE owner=? AND scope=? AND idempotency_key=?", (json.dumps(progress), actor.subject_id, scope, key))
            else:
                connection.execute("INSERT INTO commands VALUES(?,?,?,?,?)", (actor.subject_id, scope, key, sha, json.dumps(progress)))
        def checkpoint(connection=None):
            if time.monotonic() >= deadline:
                raise EngineError("import_deadline", "Import reached its bounded deadline", 409, "reconcile")
            self._actor(actor, "bundle.import", "export")
            if connection is None:
                with self.engine.db.connect() as current:
                    return checkpoint(current)
            saved = self._command(connection, actor, scope, key, sha)
            if not saved or (saved.get("worker_id"), saved.get("fencing_token")) != (worker, progress["fencing_token"]) or saved.get("lease_until_us", 0) <= self.engine.clock():
                raise EngineError("stale_import_lease", "Import worker lease expired or was superseded", 409, "reconcile")
        try:
            with zipfile.ZipFile(archive_path) as archive:
                origin_documents = self._import_documents(manifest, {
                    item.relative_path: archive.read(item.relative_path) for item in manifest.artifacts if item.material_id})
                correction_origins = self._correction_origins(origin_documents)
                for artifact in manifest.artifacts:
                    checkpoint()
                    value = archive.read(artifact.relative_path)
                    if len(value) != artifact.size or hashlib.sha256(value).hexdigest() != artifact.sha256:
                        raise EngineError("import_integrity_failed", "Archive changed during its controlled extraction", 422)
                    local_key = "imported-" + digest(progress["import_id"] + ":" + artifact.artifact_id)
                    if artifact.material_id:
                        self._write("BundleMaterials", local_key, value)
                        binding = {"material_id": local_key, "schema_kind": self._material_kind(artifact, manifest.schema_version, correction_origins)}
                    else:
                        if self.validators.media_validator is None:
                            raise EngineError("media_validator_missing", "Actual import media decoding is unavailable", 503)
                        with self.engine.db.transaction() as connection:
                            checkpoint(connection)
                            connection.execute("INSERT OR IGNORE INTO staging(id,owner,media_type,sha256,size,status) VALUES(?,?,?,?,?,'allocated')", (local_key, actor.subject_id, artifact.media_type, artifact.sha256, artifact.size))
                        self._write("Staging", local_key, value)
                        with self.engine.db.transaction() as connection:
                            checkpoint(connection)
                            connection.execute("UPDATE staging SET status='ready' WHERE id=? AND status='allocated'", (local_key,))
                        candidate = c.AssetCandidate(staging_id=local_key, sha256=artifact.sha256, size=artifact.size, media_type=artifact.media_type,
                                source="local", rights="original-bundle:" + origin_key)
                        asset = self.assets.import_asset(actor.subject_id, candidate, self.validators.media_validator)
                        if artifact.spec.duration_us is not None and asset.probe.duration_us != artifact.spec.duration_us:
                            raise EngineError("import_media_spec_invalid", "Actual decoded original duration differs from manifest", 422)
                        if artifact.spec.width is not None and (asset.probe.width, asset.probe.height) != (artifact.spec.width, artifact.spec.height):
                            raise EngineError("import_media_spec_invalid", "Actual decoded original dimensions differ from manifest", 422)
                        binding = {"asset_id": asset.asset_id}
                    progress["bindings"][artifact.artifact_id] = binding
                    with self.engine.db.transaction() as connection:
                        checkpoint(connection)
                        connection.execute("UPDATE commands SET result_json=? WHERE owner=? AND scope=? AND idempotency_key=?", (json.dumps(progress), actor.subject_id, scope, key))
            manifest_key = "import-manifest-" + progress["import_id"]
            self._write("BundleManifests", manifest_key, raw)
            if self.assets._hash(archive_path) != request.archive_sha256:
                raise EngineError("import_integrity_failed", "Original archive changed before local visibility", 422)
            with self.engine.db.transaction() as connection:
                checkpoint(connection)
                connection.execute("INSERT INTO bundle_imports(id,owner,project_id,origin_key,origin_ref_json,manifest_json,manifest_file_key,mapping_json,created_at_us) VALUES(?,?,?,?,?,?,?,?,?)",
                    (progress["import_id"], actor.subject_id, request.project_id, origin_key, canonical(request.expected_origin_ref), raw.decode(), manifest_key, json.dumps(progress["bindings"]), self.engine.clock()))
                result = self._import_receipt(connection.execute("SELECT * FROM bundle_imports WHERE id=?", (progress["import_id"],)).fetchone())
                connection.execute("UPDATE commands SET result_json=? WHERE owner=? AND scope=? AND idempotency_key=?", (canonical(result), actor.subject_id, scope, key))
                return result
        except BaseException:
            with self.engine.db.transaction() as connection:
                saved = self._command(connection, actor, scope, key, sha)
                if saved and (saved.get("worker_id"), saved.get("fencing_token")) == (worker, progress["fencing_token"]):
                    progress["lease_until_us"] = 0
                    connection.execute("UPDATE commands SET result_json=? WHERE owner=? AND scope=? AND idempotency_key=?", (json.dumps(progress), actor.subject_id, scope, key))
            raise

    def _verify_strict_precision(self, lease, manifest, documents, actual, quality, requirements):
        transcript, alignment = actual.transcript, actual.alignment
        precision = alignment.precision
        if precision.status != "measured" or precision.units != "utterance":
            self._current_precision_problem('precision_measurement_missing', kind='precision_measurement')
            self._block(lease, "alignment_required")

        reports = [value for value in documents.values() if isinstance(value, c.PrecisionEvaluationReport)]
        report = next((value for value in reports if any(item.material_id == precision.evaluation_material_id and documents.get(item.relative_path) is value for item in manifest.artifacts)), None)
        authority = (self.validators.precision_authorities or {}).get(precision.criterion_version_ref)
        if self._in_current_final_evidence():
            if report is None:
                self._current_precision_problem('precision_measurement_missing', kind='precision_measurement')
            if authority is None:
                self._current_precision_problem('precision_verifier_not_ready', kind='verifier_resource')
            if (report.alignment_revision_id != alignment.alignment_revision_id
                    or report.alignment_content_sha256 != alignment.content_sha256
                    or report.input_audio_sha256 != transcript.input_audio_sha256
                    or report.units != precision.units or report.criterion_version_ref != precision.criterion_version_ref):
                raise EngineError('precision_evidence_conflict', 'Actual report changed audio/alignment/criterion binding', 422)
            if authority(report, actual) is not True:
                raise EngineError('precision_authority_denied', 'Actual authority rejected this report', 403)
        if (not report or not authority or self._current_precision_authority_result(authority(report, actual)) is not True or report.alignment_revision_id != alignment.alignment_revision_id
                or report.alignment_content_sha256 != alignment.content_sha256 or report.input_audio_sha256 != transcript.input_audio_sha256
                or report.units != precision.units or report.criterion_version_ref != precision.criterion_version_ref):
            self._block(lease, "alignment_required")
        reference = next((documents.get(item.relative_path) for item in manifest.artifacts if item.material_id == report.reference_material_id), None)
        if not isinstance(reference, dict) or not isinstance(reference.get("reference_boundaries"), list):
            raise EngineError("precision_reference_invalid", "Complete actual independent reference units are required", 422)
        try:
            references = tuple(c.PrecisionReferenceUnit.model_validate(value) for value in reference["reference_boundaries"])
        except ValidationError:
            raise EngineError("precision_reference_invalid", "Original reference unit array is invalid", 422) from None
        count, p95 = nearest_rank(unit_errors(alignment.boundaries, references, report.boundaries, transcript.duration_us))
        if (precision.sample_count, precision.p95_error_us) != (count, p95):
            raise EngineError("criterion_mismatch", "Original report differs from complete unit max/N nearest rank", 422)
        if p95 > LIMIT_US:
            self._current_precision_problem('precision_limit_exceeded', report=report, actual=actual, manifest=manifest)
            self._block(lease, "alignment_required")
        # One utterance report can never certify word accuracy. This phase
        # supports only the explicitly admitted estimate degradation.
        if requirements.alignment_requirement == "word_verified" and (
                "word_estimate_with_declared_gap" not in requirements.allowed_degradations or not self.validators.word_degradation_allowed
                or not quality.allowed_degradation_approval_ref or quality.allowed_degradation_approval_ref not in manifest.approval_refs):
            if self._in_current_final_evidence():
                raise EngineError('alignment_scope_denied', 'Actual word requirement has no admitted degradation', 403)
            self._block(lease, "alignment_required")

    def verify_alignment_evidence(self, lease: c.LeaseGrant, preparation_id: str, *,
                                  actual_transcript_artifact_id: str, work_validation_artifact_id: str,
                                  audio_mappings: tuple[c.AudioTimelineMapping, ...]) -> VerifiedAlignmentEvidence:
        with self.engine.db.connect() as connection:
            self._preparation(connection, lease, preparation_id)
        actual_id = self.material_allocation(lease, preparation_id, actual_transcript_artifact_id).material_id
        report_id = self.material_allocation(lease, preparation_id, work_validation_artifact_id).material_id
        actual = c.ActualTranscriptDocumentV03.model_validate(strict_json(self.read_material(lease, preparation_id, actual_id)))
        report = c.WorkAlignmentValidationReport.model_validate(strict_json(self.read_material(lease, preparation_id, report_id)))
        self._validate_work_runtime(lease, preparation_id, actual, report, audio_mappings)
        token = VerifiedAlignmentEvidence(identity("alignment-verification"), preparation_id, lease.run_id, lease.fencing_token, report.content_sha256)
        with self._lock:
            self._alignment_verified[token.verification_id] = (token, lease, actual.alignment.content_sha256,
                tuple((mapping.mapping_revision_id, mapping.content_sha256) for mapping in audio_mappings), time.monotonic() + 30)
        return token

    def _validate_work_runtime(self, lease, preparation_id, actual, report, mappings):
        ctc_source = self.registered_ctc_work_source(lease, preparation_id, actual, report)
        with self.engine.db.connect() as connection:
            _, run, production, request = self._preparation(connection, lease, preparation_id)
            if (not isinstance(request, c.ProductionRequestV03)
                    or not (isinstance(actual, c.ActualTranscriptDocumentV03)
                            or isinstance(actual, local.LocalActualTranscriptDocumentV1) and isinstance(actual.alignment, c.AlignmentRevisionV03))):
                raise EngineError("evidence_version_conflict", "Automatic evidence belongs only to explicit 0.3", 409)
            self._all_operations(connection, run)
            transcript, alignment, subtitles = actual.transcript, actual.alignment, actual.subtitles
            for value in (transcript, alignment, subtitles, report):
                check_record(value)
            expected = (production["id"], run["id"], production["request_revision_id"], production["request_sha256"],
                transcript.input_audio_asset_id, transcript.input_audio_sha256, transcript.transcript_revision_id,
                transcript.content_sha256, alignment.alignment_revision_id, alignment.content_sha256,
                subtitles.subtitle_revision_id, subtitles.content_sha256)
            observed = (report.production_id, report.run_id, report.request_revision_id, report.request_sha256,
                report.input_audio_asset_id, report.input_audio_sha256, report.transcript_revision_id,
                report.transcript_content_sha256, report.alignment_revision_id, report.alignment_content_sha256,
                report.subtitle_revision_id, report.subtitle_content_sha256)
            if observed != expected:
                raise EngineError("work_evidence_binding_invalid", "Runtime report differs from this actual work/run/request/audio/revisions", 422)
            if len({item.mapping_revision_id for item in mappings}) != len(mappings) or len({item.mapping_revision_id for item in report.mapping_refs}) != len(report.mapping_refs):
                raise EngineError("work_evidence_binding_invalid", "Mapping references are distinct before indexing", 422)
            if {(item.mapping_revision_id, item.content_sha256) for item in mappings} != {(item.mapping_revision_id, item.content_sha256) for item in report.mapping_refs}:
                raise EngineError("work_evidence_binding_invalid", "Runtime report must retain all original actual mapping versions", 422)
            for mapping in mappings:
                check_record(mapping)
                for piece in mapping.pieces:
                    self._check_mapping_piece(piece)
            ref = request.delivery_requirements.evidence_policy_revision_ref
            if report.evidence_policy_revision_ref != ref:
                raise EngineError("work_evidence_binding_invalid", "Runtime report changed the preauthorized policy", 422)
            asset = self.assets.get(production["owner"], transcript.input_audio_asset_id)
            resolved = self.engine.evidence_registry.verify(production["owner"], production["project_id"], ref,
                report.execution_identity, transcript.language, asset.media_type, transcript.duration_us,
                report.transformations, connection=connection)
            if report.qualification_ref != resolved.qualification or alignment.units != resolved.qualification.applicability.units:
                raise EngineError("work_qualification_conflict", "Work uses a different exact qualification or unit scope", 409)
            needed_units = "word" if request.delivery_requirements.alignment_requirement == "word_verified" else "utterance"
            if alignment.units != needed_units:
                raise EngineError("alignment_required", "No unapproved word degradation may replace the requested verified units", 409)
            if report.result != "verified" or report.source_gaps or report.reasons:
                raise EngineError("work_validation_incomplete", "Work runtime validation has unresolved gaps or failed checks", 409)
            if not set(resolved.policy.required_checks) <= {check.check_id for check in report.checks if check.status == "verified"}:
                raise EngineError("work_validation_incomplete", "All preauthorized policy checks need actual complete evidence", 422)
            runtime_match = ctc_source is not None
            asr_match = False
            for operation_id in report.operation_ids:
                row = connection.execute("SELECT observation_json FROM operations WHERE id=? AND run_id=? AND status='succeeded' AND settled=1", (operation_id, run["id"])).fetchone()
                if not row:
                    raise EngineError("work_operation_invalid", "Work evidence requires actual successful settled observations of this exact run", 422)
                raw = c.OperationObservation.model_validate_json(row[0]).result_json
                if matches_actual_asr(raw, transcript):
                    asr_match = True
                    runtime = raw.get("runtime", {})
                    # Child-observed complete identity is mandatory. Current W9
                    # lacks OS/config identity; do not invent it from this host.
                    if (isinstance(runtime, dict) and runtime.get("execution_identity") == report.execution_identity.model_dump(mode="json")
                        and (runtime.get("device"), runtime.get("actual_compute_type"), runtime.get("model_file_sha256")) == (
                            report.execution_identity.device, report.execution_identity.compute_type, dict(report.execution_identity.model_file_sha256))):
                        runtime_match = True
            if not asr_match or not runtime_match or report.execution_identity.resource_manifest_sha256 not in self.validators.resource_manifest_hashes:
                self._current_precision_problem('work_execution_identity_missing', kind='work_validation')
                raise EngineError("work_execution_identity_missing", "Actual child-observed compute/OS/config/model/resource identity is unavailable", 409)
            self.assert_registered_ctc_work_writer(connection, ctc_source)
            return resolved

    def _verify_per_work_precision(self, manifest, documents, actual, *, lease=None, preparation_id=None):
        precision = actual.alignment.precision
        if precision.status != "measured" or precision.reference_ref is None or precision.measurement_report_locator is None:
            self._current_precision_problem('independent_reference_missing', kind='independent_reference')
            raise EngineError("alignment_required", "An actual strict measurement needs its complete independent reference", 409)
        indexed = {item.artifact_id: item for item in manifest.artifacts}
        locator = precision.measurement_report_locator
        item = indexed.get(locator.artifact_id)
        report = documents.get(item.relative_path) if item else None
        if (not item or item.material_id != locator.material_id or "precision_evaluation" not in item.roles
                or not isinstance(report, c.PrecisionEvaluationReportV03) or report.evaluation_id != locator.report_id):
            raise EngineError("work_measurement_binding_invalid", "Durable report locator must resolve its actual ready measurement artifact", 422)
        reference_item = next((value for value in manifest.artifacts if value.material_id == report.reference_material_id), None)
        reference = documents.get(reference_item.relative_path) if reference_item else None
        if not reference_item or "precision_reference" not in reference_item.roles or not isinstance(reference, c.PerWorkReferenceDocument):
            raise EngineError("precision_reference_invalid", "Reference must be its actual distinct versioned indexed material", 422)
        check_record(reference)
        check_record(report)
        expected_ref = c.EvidenceReportRef(report_id=reference.report_id, schema_version=c.V03_SCHEMA_VERSION,
            evaluation_scope="per_work_reference_measurement", content_sha256=reference_item.sha256)
        if report.reference_ref != expected_ref or precision.reference_ref != expected_ref:
            raise EngineError("precision_reference_hash_invalid", "Reference identity uses complete ready file SHA, not internal record or signature hash", 422)
        if (report.alignment_revision_id, report.alignment_content_sha256, report.input_audio_sha256, reference.input_audio_sha256,
            report.units, precision.units, report.criterion_version_ref, report.authority_ref, report.method_ref) != (
                actual.alignment.alignment_revision_id, actual.alignment.content_sha256, actual.transcript.input_audio_sha256,
                actual.transcript.input_audio_sha256, actual.alignment.units, actual.alignment.units, precision.criterion_version_ref,
                reference.authority_ref.authority_id, actual.alignment.method_ref):
            raise EngineError("precision_evidence_conflict", "Measurement changed actual alignment/audio/unit/criterion identity", 422)
        units = tuple(value.utterance_id for value in actual.transcript.utterances) if actual.alignment.units == "utterance" else tuple(word.word_id for value in actual.transcript.utterances for word in value.words)
        if len(units) != len(set(units)) or reference.units != units or set(units) != {value.transcript_unit_id for value in actual.alignment.boundaries}:
            raise EngineError("precision_evidence_conflict", "Full original transcript, alignment and reference populations must match", 422)
        count, p95 = nearest_rank(unit_errors(actual.alignment.boundaries, reference.boundaries, report.boundaries, actual.transcript.duration_us))
        if (count, p95) != (precision.sample_count, precision.p95_error_us) or (count, p95) != (report.sample_count, report.p95_error_us):
            raise EngineError("criterion_mismatch", "Actual measurement differs from complete unit max/N nearest rank", 422)
        if p95 > LIMIT_US and not self._in_current_final_evidence():
            raise EngineError("alignment_required", "Actual full-unit measurement exceeds the 200ms criterion", 409)
        if report.corrected_from and (report.corrected_from.report_id == report.evaluation_id or not report.correction_reason):
            raise EngineError("correction_lineage_invalid", "Correction requires a distinct original report and its actual reason", 422)
        self._correction_closure(manifest, documents, lease=lease)
        source_documents = {}
        for ref in (*reference.independent_listener_refs, reference.arbitration_ref):
            source = indexed.get(ref.artifact_id)
            body = documents.get(source.relative_path) if source else None
            if not source or not source.material_id or "audit_summary" not in source.roles or source.sha256 != ref.sha256 or not isinstance(body, dict):
                raise EngineError("precision_reference_source_missing", "Real listener/arbitration body and disclosure license closure are required", 422)
            if ref.artifact_id not in reference_item.dependency_artifact_ids:
                raise EngineError("evidence_dependency_missing", "Reference material must retain all original listener and arbitration dependencies", 422)
            if lease is not None:
                source_documents[ref.artifact_id] = (ref, self.read_material(lease, preparation_id, source.material_id))
            facts = body.get("findings")
            if not isinstance(facts, dict) or (facts.get("document_id"), facts.get("revision"), facts.get("input_audio_sha256"), facts.get("units")) != (ref.document_id, ref.revision, reference.input_audio_sha256, list(units)):
                raise EngineError("precision_reference_source_invalid", "Original source identity/audio/whole unit declarations conflict", 422)
        if reference_item.artifact_id not in item.dependency_artifact_ids:
            raise EngineError("evidence_dependency_missing", "Actual measurement retains its original reference dependency", 422)
        if lease is not None:
            self.engine.evidence_registry.verify_work_reference(reference, lease=lease, preparation_id=preparation_id,
                actual=actual, source_documents=source_documents)
        # Current classification may only retain a failure from an actually
        # authenticated original reference/source closure, never a forged one.
        if p95 > LIMIT_US:
            self._current_precision_problem('precision_limit_exceeded', report=report, actual=actual, manifest=manifest)
        # Origin import only checks original complete structure/bytes/math.
        # Local signature/source approval and execution remain separate.
        return report

    def _verify_v03_documents(self, lease, manifest, documents, request):
        indexed = {item.artifact_id: item for item in manifest.artifacts}
        def document(artifact_id, model, role):
            item = indexed[artifact_id]
            value = documents.get(item.relative_path)
            if not item.material_id or item.roles != (role,) or not isinstance(value, model):
                raise EngineError("work_evidence_material_missing", "Evidence must be an actual typed indexed material with its exact role", 422)
            check_record(value)
            return item, value
        _, policy = document(manifest.policy_document_artifact_id, c.EvidencePolicyRevision, "evidence_policy")
        _, qualification = document(manifest.qualification_document_artifact_id, c.MethodQualificationRef, "method_qualification")
        _, work = document(manifest.work_validation_document_artifact_id, c.WorkAlignmentValidationReport, "work_alignment_validation")
        actual, quality = documents["Text/actual-transcript.json"], documents["Checks/quality-report.json"]
        if not isinstance(quality, c.BundleQualityEvidenceV03):
            raise EngineError("evidence_version_conflict", "0.3 quality requires its own scoped evidence model", 422)
        with self.engine.db.connect() as connection:
            row = connection.execute("SELECT id FROM bundle_revisions WHERE revision_id=? AND run_id=?", (manifest.bundle_revision_id, lease.run_id)).fetchone()
        resolved = self._validate_work_runtime(lease, row[0], actual, work, manifest.audio_mappings)
        if (policy, qualification, manifest.qualification_ref, manifest.evidence_policy_revision_ref) != (resolved.policy, resolved.qualification, resolved.qualification, resolved.policy_ref):
            raise EngineError("work_qualification_conflict", "Manifest evidence differs from the current exact registry admission", 409)
        if (quality.evidence_policy_revision_ref, quality.qualification_ref, quality.work_validation_report_ref.report_id,
            quality.work_validation_report_ref.content_sha256) != (resolved.policy_ref, qualification, work.report_id, work.content_sha256):
            raise EngineError("work_evidence_binding_invalid", "Quality must bind this actual complete runtime report", 422)
        benchmark_types = {'embedded_full_report': (c.MethodBenchmarkReport, "method_benchmark"),
                           'embedded_self_issued': (c.LocalSelfIssuedBenchmarkV1, "method_benchmark_self_issued"),
                           'provenance_reference': (c.MethodBenchmarkReference, "method_benchmark_reference")}
        if manifest.benchmark_binding not in benchmark_types:
            raise EngineError('benchmark_binding_invalid', 'Manifest benchmark binding is not admitted', 422)
        benchmark_type, benchmark_role = benchmark_types[manifest.benchmark_binding]
        _, benchmark = document(manifest.benchmark_document_artifact_id, benchmark_type, benchmark_role)
        if isinstance(benchmark, c.MethodBenchmarkReport):
            validate_benchmark(benchmark)
            if benchmark != resolved.benchmark:
                raise EngineError("benchmark_binding_invalid", "Embedded benchmark differs from actual admitted complete evidence", 422)
        elif isinstance(benchmark, c.LocalSelfIssuedBenchmarkV1):
            validate_self_issued_benchmark(benchmark)
            if benchmark != resolved.benchmark:
                raise EngineError("benchmark_binding_invalid",
                                  "Embedded self-issued declaration differs from actual admitted evidence", 422)
            if request.delivery_requirements.alignment_evidence_policy == 'strict_reference_v1':
                raise EngineError('alignment_required',
                                  'Strict reference policy cannot use a not-performed local declaration.', 409)
        elif (benchmark.origin_report_ref, benchmark.execution_identity, benchmark.applicability, benchmark.corpus_id,
              benchmark.corpus_sha256, benchmark.authority_ref) != (qualification.benchmark_report_ref, resolved.benchmark.execution_identity,
              resolved.benchmark.applicability, resolved.benchmark.corpus_id, resolved.benchmark.corpus_sha256, resolved.benchmark.authority_ref):
            raise EngineError("benchmark_binding_invalid", "Provenance reference must retain the original report identity, not its own hash", 422)
        elif benchmark != self.engine.evidence_registry.benchmark_reference(qualification.benchmark_report_ref):
            raise EngineError("benchmark_disclosure_approval_invalid", "Producer cannot fabricate a licensed disclosure from the admitted benchmark", 403)
        elif benchmark.license_ref not in {right.rights_id for right in manifest.rights}:
            raise EngineError("benchmark_license_missing", "Actual provenance reference requires its disclosed license scope", 403)
        precision = actual.alignment.precision
        measurements = [value for value in documents.values() if isinstance(value, c.PrecisionEvaluationReportV03)]
        if precision.status != "measured":
            if measurements or quality.per_work_measurement_report_ref is not None or request.delivery_requirements.alignment_evidence_policy == "strict_reference_v1":
                if (measurements or quality.per_work_measurement_report_ref is not None) and self._in_current_final_evidence():
                    raise EngineError('precision_evidence_conflict', 'Unmeasured work cannot hide real measurements', 422)
                self._current_precision_problem('independent_reference_missing', kind='independent_reference')
                raise EngineError("alignment_required", "No reference means no measurement artifact or metric; strict policy still requires real reference", 409)
        else:
            report = self._verify_per_work_precision(manifest, documents, actual, lease=lease, preparation_id=row[0])
            if (quality.per_work_measurement_report_ref is None or quality.per_work_measurement_report_ref.report_id != report.evaluation_id
                    or quality.per_work_measurement_report_ref.content_sha256 != report.content_sha256):
                raise EngineError("work_measurement_binding_invalid", "Quality must retain this actual immutable work measurement", 422)
        # Forward dependencies form a DAG. Projections independently include
        # required release evidence; no reverse transcript->work-report cycle.
        required_edges = {
            manifest.policy_document_artifact_id: {manifest.qualification_document_artifact_id},
            manifest.qualification_document_artifact_id: {manifest.benchmark_document_artifact_id},
            manifest.work_validation_document_artifact_id: {manifest.policy_document_artifact_id,
                next(item.artifact_id for item in manifest.artifacts if item.relative_path == "Text/actual-transcript.json")},
            next(item.artifact_id for item in manifest.artifacts if item.relative_path == "Checks/quality-report.json"): {manifest.work_validation_document_artifact_id},
        }
        for artifact_id, needed in required_edges.items():
            if not needed <= set(indexed[artifact_id].dependency_artifact_ids):
                raise EngineError("evidence_dependency_missing", "Actual evidence index lacks its forward provenance closure", 422)
    def _validate_relations(self, lease, manifest, documents, request):
        by_path = {item.relative_path: item for item in manifest.artifacts}
        by_id = {item.artifact_id: item for item in manifest.artifacts}
        for path, kind in (("Creative/insight.json", "insight"), ("Creative/brief.json", "brief"), ("Creative/production-plan.json", "plan")):
            document = documents.get(path)
            if not isinstance(document, c.CreativeRevision) or document.kind != kind or not any(ref.revision_id == document.revision_id and ref.kind == kind and ref.content_sha256 == digest(canonical(document)) for ref in manifest.creative_revision_refs):
                raise EngineError("creative_material_conflict", "Creative attachment differs from its actual immutable revision", 422)
        expected = {"video": ("Media/video.mp4",), "narration_audio": ("Media/narration.wav",), "mixed_audio": ("Media/mixed-audio.wav",),
                    "approved_script": ("Text/approved-script.json",), "actual_transcript": ("Text/actual-transcript.json",),
                    "subtitles": ("Text/subtitles.srt", "Text/subtitles.vtt"), "semantic_manifest": ("Semantics/semantic-segments.jsonl",), "rag_chunks": ("Semantics/rag-chunks.jsonl",)}
        for output in manifest.outputs:
            if {by_id[ref].relative_path for ref in output.artifact_ids} != set(expected[output.role]):
                raise EngineError("bundle_output_binding_invalid", "Output roles must bind their actual fixed artifacts", 422)
        allowed_extra_roles = {"license", "precision_evaluation", "precision_reference", "frame_evidence", "asr_input", "audit_summary", "method_benchmark", "method_benchmark_reference", "method_benchmark_self_issued", "method_qualification", "evidence_policy", "work_alignment_validation"}
        for item in manifest.artifacts:
            if item.relative_path not in FIXED_FILES and not set(item.roles) <= allowed_extra_roles:
                raise EngineError("bundle_attachment_denied", "Extra private files cannot enter the fixed export index", 403)
        video, narration, mixed = (by_path[key] for key in ("Media/video.mp4", "Media/narration.wav", "Media/mixed-audio.wav"))
        if video.spec.duration_us != manifest.timeline_duration_us or mixed.spec.duration_us != manifest.timeline_duration_us or narration.asset_id == mixed.asset_id:
            raise EngineError("bundle_audio_roles_invalid", "Video/mix share the actual work duration and narration is independently produced", 422)
        actual = documents.get("Text/actual-transcript.json")
        script = documents.get("Text/approved-script.json")
        quality = documents.get("Checks/quality-report.json")
        if not isinstance(actual, (c.ActualTranscriptDocument, c.ActualTranscriptDocumentV03)) or not isinstance(script, c.ApprovedScriptDocument) or not isinstance(quality, c.BundleQualityEvidence):
            raise EngineError("bundle_document_missing", "Actual transcript, approved script and actual quality evidence are required", 422)
        transcript, alignment, subtitles = actual.transcript, actual.alignment, actual.subtitles
        if not transcript.utterances or not transcript.text.strip():
            raise EngineError("actual_speech_unrecognized", "Default narration requires actual recognized speech, not source-script substitution", 422)
        if transcript.input_audio_asset_id != mixed.asset_id and not any(item.asset_id == transcript.input_audio_asset_id and "asr_input" in item.roles and video.artifact_id in item.dependency_artifact_ids for item in manifest.artifacts):
            raise EngineError("transcript_audio_binding_invalid", "Main transcript must use final mixed PCM or registered encoded-audio decoding", 422)
        if (alignment.actual_transcript_revision_id, alignment.transcript_content_sha256, alignment.input_audio_asset_id, alignment.input_audio_sha256) != (transcript.transcript_revision_id, transcript.content_sha256, transcript.input_audio_asset_id, transcript.input_audio_sha256):
            raise EngineError("alignment_binding_invalid", "Alignment must bind the unchanged actual audio and transcript", 422)
        if transcript.approved_script_revision_ref != script.script_revision_ref or script.script_revision_ref not in manifest.creative_revision_refs:
            raise EngineError("script_revision_conflict", "Approved script comparison must keep its actual creative version", 409)
        with self.engine.db.connect() as connection:
            stored_script = connection.execute("SELECT body FROM creative_revisions WHERE id=?", (script.script_revision_ref.revision_id,)).fetchone()
            body = c.CreativeRevision.model_validate_json(stored_script[0]).body
            if not isinstance(body, dict) or body.get("text") != script.text:
                raise EngineError("script_material_conflict", "Script material differs from the approved script revision", 422)
            method = next((value for value in manifest.methods if value.method_id == transcript.method_ref), None)
            raw_results = []
            for operation_id in method.operation_ids if method else ():
                row = connection.execute("SELECT * FROM operations WHERE id=? AND run_id=? AND status='succeeded' AND settled=1", (operation_id, lease.run_id)).fetchone()
                if row:
                    observation = c.OperationObservation.model_validate_json(row["observation_json"])
                    if isinstance(observation.result_json, dict):
                        raw_results.append(observation.result_json)
            if not method or method.kind != "observed" or not any(matches_actual_asr(result, transcript) for result in raw_results):
                raise EngineError("actual_asr_evidence_missing", "Transcript must match the actual controlled ASR operation observation", 422)
        if method.resource_manifest_sha256 not in self.validators.resource_manifest_hashes:
            raise EngineError("asr_resource_unconfigured", "Actual ASR resource revision is not admitted by this installation", 503)
        units = {item.utterance_id: item for item in transcript.utterances}
        words = {word.word_id: word for item in transcript.utterances for word in item.words}
        word_count = sum(len(item.words) for item in transcript.utterances)
        alignment_ids = [item.transcript_unit_id for item in alignment.boundaries]
        expected = units if alignment.units == "utterance" else words
        if len(units) != len(transcript.utterances) or len(words) != word_count or set(units) & set(words) or len(set(alignment_ids)) != len(alignment_ids) or set(alignment_ids) != set(expected):
            raise EngineError("alignment_unit_invalid", "Actual units and aligned unit identities must be distinct and complete", 422)
        for unit in alignment.boundaries:
            source = (units if alignment.units == "utterance" else words).get(unit.transcript_unit_id)
            if not source or unit.intrinsic_range.end_us > transcript.duration_us:
                raise EngineError("alignment_unit_invalid", "Alignment unit is outside actual recognized speech", 422)
        requirements = request.delivery_requirements or c.DeliveryRequirements()
        if isinstance(manifest, c.BundleManifestV03):
            self._verify_v03_documents(lease, manifest, documents, request)
        else:
            self._verify_strict_precision(lease, manifest, documents, actual, quality, requirements)
        mappings = {item.mapping_revision_id: item for item in manifest.audio_mappings}
        if not mappings or any(item.target_video_asset_id != video.asset_id or item.timeline_duration_us != manifest.timeline_duration_us for item in mappings.values()):
            raise EngineError("audio_mapping_invalid", "Every mapping targets this exact final work", 422)
        pieces = {}
        for mapping in mappings.values():
            check_record(mapping)
            for piece in mapping.pieces:
                actual_track = self.asset(lease, piece.source_track.asset_id)
                if actual_track.sha256 != piece.source_track.sha256 or self.audio_clock_authority is None:
                    raise EngineError("audio_clock_unconfigured", "Actual audio samples/PTS require a trusted installed verification method", 503)
                if self.audio_clock_authority(piece.source_track, self.content_path(lease, actual_track.asset_id)) is not True:
                    raise EngineError("audio_clock_invalid", "Raw sample/PTS clock differs from the registered actual audio", 422)
                self._check_mapping_piece(piece)
                if piece.piece_id in pieces:
                    raise EngineError("audio_mapping_invalid", "Mapping piece IDs are globally distinct within the bundle", 422)
                pieces[piece.piece_id] = piece
        if (subtitles.actual_transcript_revision_id, subtitles.alignment_revision_id, subtitles.timeline_duration_us) != (transcript.transcript_revision_id, alignment.alignment_revision_id, manifest.timeline_duration_us) or subtitles.mapping_revision_id not in mappings:
            raise EngineError("subtitle_binding_invalid", "Subtitles must bind actual transcript/alignment and this final timeline", 422)
        for cue in subtitles.cues:
            text = "".join((units.get(ref) or words.get(ref)).text for ref in cue.transcript_unit_refs if units.get(ref) or words.get(ref))
            if not cue.transcript_unit_refs or text != cue.text:
                raise EngineError("subtitle_text_invalid", "Cue text must preserve its actual recognized units", 422)
        srt, vtt, quantization = serialize_subtitles(subtitles)
        if tuple(quantization) != subtitles.quantization_errors:
            raise EngineError("subtitle_quantization_invalid", "Recorded errors must match the exact approved serializer", 422)
        if documents.get("Text/subtitles.srt") != srt.decode() or documents.get("Text/subtitles.vtt") != vtt.decode():
            raise EngineError("subtitle_material_conflict", "Actual SRT/VTT differs from the verified microsecond cue table", 422)
        sources = documents.get("Semantics/source-bindings.json")
        summary = documents.get("Semantics/work-summary.json")
        segments = documents.get("Semantics/semantic-segments.jsonl")
        chunks = documents.get("Semantics/rag-chunks.jsonl")
        if (not isinstance(sources, c.SourceBindingsDocument) or sources.source_refs != manifest.source_refs or sources.bundle_revision_id != manifest.bundle_revision_id
                or not isinstance(summary, c.WorkSummary) or summary.bundle_revision_id != manifest.bundle_revision_id or not segments or not chunks):
            raise EngineError("semantic_binding_invalid", "Source/summary/semantic/RAG files bind the exact original bundle", 422)
        for binding in request.source_bindings:
            matches = [ref for ref in manifest.source_refs if (ref.system, ref.namespace, ref.article_id, ref.article_revision, ref.topic_id, ref.topic_revision) == (binding.system, binding.namespace, binding.article_id, binding.article_revision, binding.topic_id, binding.topic_revision)]
            if not matches or not set(binding.paragraph_ids) <= set(matches[0].paragraph_ids) or not set(binding.confirmed_facts) <= {fact.text for fact in matches[0].fact_refs}:
                raise EngineError("source_binding_lost", "Original source identities/versions/facts must be preserved exactly", 422)
            for fact in matches[0].fact_refs:
                if fact.text in binding.confirmed_facts and (fact.foreign_fact_id is not None or fact.local_fact_id != local_fact_id(binding, fact.text) or fact.confirmation_kind != "caller_asserted"):
                    raise EngineError("source_fact_identity_invalid", "A string-only caller fact keeps a derived local identity; it cannot invent a foreign fact ID", 422)
        if any(not set(ref.input_asset_ids) <= set(request.inputs.asset_ids) for ref in manifest.source_refs):
            raise EngineError("source_asset_denied", "Source bindings can only name actual fixed caller input assets", 403)
        known_segments = {segment.segment_id: segment for segment in segments}
        if len(known_segments) != len(segments):
            raise EngineError("semantic_binding_invalid", "Semantic segment IDs are unique", 422)
        for segment in segments:
            if segment.bundle_revision_id != manifest.bundle_revision_id or segment.video_asset_id != video.asset_id or segment.video_range.end_us > manifest.timeline_duration_us or segment.alignment_revision_id != alignment.alignment_revision_id:
                raise EngineError("semantic_binding_invalid", "Semantic media range/version does not match actual work", 422)
            actual_speech = "".join((units.get(ref) or words.get(ref)).text for ref in segment.transcript_unit_refs if units.get(ref) or words.get(ref))
            if actual_speech != segment.speech_text or any(ref not in manifest.source_refs for ref in segment.source_refs):
                raise EngineError("semantic_speech_invalid", "Semantic speech/source refs differ from actual fixed evidence", 422)
            for span in segment.audio_spans:
                self._check_span(span, pieces)
            if segment.visual_description and (not segment.frame_evidence_refs or self.validators.frame_validator is None):
                raise EngineError("frame_evidence_unconfigured", "Actual final-frame verification is required for visual descriptions", 503)
            for frame in segment.frame_evidence_refs:
                if frame.video_asset_id != video.asset_id or frame.video_sha256 != video.sha256 or frame.at_us >= manifest.timeline_duration_us or not self.validators.frame_validator(frame, self.content_path(lease, video.asset_id)):
                    raise EngineError("frame_evidence_invalid", "Visual evidence must come from the actual final video", 422)
        if len({chunk.chunk_id for chunk in chunks}) != len(chunks):
            raise EngineError("rag_binding_invalid", "RAG chunk IDs are unique", 422)
        for chunk in chunks:
            if chunk.bundle_revision_id != manifest.bundle_revision_id or any(ref not in known_segments for ref in chunk.segment_ids) or not chunk.video_ranges or any(value.end_us > manifest.timeline_duration_us for value in chunk.video_ranges):
                raise EngineError("rag_binding_invalid", "RAG chunks keep actual segment/version/media locations", 422)
            referenced = [known_segments[key] for key in chunk.segment_ids]
            if chunk.chunk_type != "work_summary" and (not referenced or chunk.video_ranges != tuple(item.video_range for item in referenced) or chunk.audio_spans != tuple(span for item in referenced for span in item.audio_spans)):
                raise EngineError("rag_binding_invalid", "Segment chunks preserve exact registered video/audio locations", 422)
            if chunk.chunk_type == "speech_segment" and chunk.text != "".join(item.speech_text for item in referenced):
                raise EngineError("rag_speech_invalid", "Speech chunks must preserve recognized speech rather than source-script text", 422)
            if chunk.access_scope_ref != manifest.project_id or chunk.rights_ref not in {right.rights_id for right in manifest.rights} or any(ref not in manifest.source_refs for ref in chunk.source_refs) or any(ref not in {method.method_id for method in manifest.methods} for ref in chunk.method_refs):
                raise EngineError("rag_scope_invalid", "RAG rights, project and provenance refer to this actual bundle", 422)
            right = next(item for item in manifest.rights if item.rights_id == chunk.rights_ref)
            if right.expires_at_us is not None and (chunk.valid_until_us is None or chunk.valid_until_us > right.expires_at_us):
                raise EngineError("rag_rights_invalid", "Semantic validity cannot outlast its actual parent rights", 422)
        required_checks = {"media_integrity", "audio_timeline", "actual_transcript", "alignment", "subtitles", "semantic_sources", "rights"}
        if quality.quality_revision_ref != manifest.quality_ref or not required_checks <= {check.check_id for check in quality.checks if check.status == "verified"}:
            self._current_quality_failure(lease,manifest,quality,required_checks)
            raise EngineError("bundle_quality_incomplete", "All server-required checks need actual evidence", 422)
        validate_portable_authorization(manifest, documents)
        authorization_refs = self._production_authorization.refs_for_manifest(lease, manifest)
        rights_observations = {}
        with self._production_authorization.guard_for(lease) as guard, self.engine.db.connect() as connection:
            run = self.engine._lease(connection, lease)
            production = self.engine._production(connection, run["production_id"])
            if guard is not None:
                self._production_authorization.assert_local_current(connection, guard, lease, production, authorization_refs)
            for right in manifest.rights:
                self._rights_time(right, self.engine.clock())
                if right.basis == "licensed" and (not right.license_document_artifact_ids or any(ref not in by_id for ref in right.license_document_artifact_ids)):
                    raise EngineError("bundle_license_missing", "Licensed output requires its actual license document references", 422)
                trusted = self.rights_authority and self.rights_authority(right, manifest) is True
                if not trusted:
                    if right.basis != "user_asserted":
                        raise EngineError("bundle_rights_unverified", "Model declarations cannot grant rights; an actual owner assertion or trusted authority is required", 403)
                    if guard is not None:
                        self._production_authorization.assert_local_current(connection, guard, lease, production, authorization_refs, right=right)
                    else:
                        self._assert_owner_right(connection, manifest.production_id, right, manifest.approval_refs, manifest.creative_revision_refs, expected_run_id=lease.run_id)
                rights_observations[right.rights_id] = bool(trusted)
        for method in manifest.methods:
            if any(ref not in by_id for ref in (*method.input_artifact_ids, *method.evidence_artifact_ids)):
                raise EngineError("bundle_method_invalid", "Method evidence must reference actual indexed inputs", 422)
            with self.engine.db.connect() as connection:
                for operation_id in method.operation_ids:
                    if not connection.execute("SELECT id FROM operations WHERE id=? AND production_id=? AND status='succeeded' AND settled=1", (operation_id, manifest.production_id)).fetchone():
                        raise EngineError("bundle_method_invalid", "Method operation must be an actual successful settled operation of this production", 422)
        return rights_observations

    def _validate_shared_rights_methods(self, lease, manifest, documents):
        """Local caller uses the same original rights and successful-operation gates."""
        by_id = {item.artifact_id: item for item in manifest.artifacts}
        validate_portable_authorization(manifest, documents)
        authorization_refs = self._production_authorization.refs_for_manifest(lease, manifest)
        rights_observations = {}
        with self._production_authorization.guard_for(lease) as guard, self.engine.db.connect() as connection:
            run = self.engine._lease(connection, lease)
            production = self.engine._production(connection, run['production_id'])
            if guard is not None:
                self._production_authorization.assert_local_current(connection, guard, lease, production, authorization_refs)
            for right in manifest.rights:
                self._rights_time(right, self.engine.clock())
                if right.basis == 'licensed' and (not right.license_document_artifact_ids
                        or any(ref not in by_id for ref in right.license_document_artifact_ids)):
                    raise EngineError('bundle_license_missing', 'Actual licensed source documents are required.', 422)
                trusted = self.rights_authority and self.rights_authority(right, manifest) is True
                if not trusted:
                    if right.basis != 'user_asserted':
                        raise EngineError('bundle_rights_unverified', 'Actual Owner assertion or independent authority is required.', 403)
                    if guard is not None:
                        self._production_authorization.assert_local_current(connection, guard, lease, production, authorization_refs, right=right)
                    else:
                        self._assert_owner_right(connection, manifest.production_id, right, manifest.approval_refs, manifest.creative_revision_refs, expected_run_id=lease.run_id)
                rights_observations[right.rights_id] = bool(trusted)
            for method in manifest.methods:
                if any(ref not in by_id for ref in (*method.input_artifact_ids, *method.evidence_artifact_ids)):
                    raise EngineError('bundle_method_invalid', 'Actual indexed method inputs and evidence are required.', 422)
                for operation_id in method.operation_ids:
                    if not connection.execute("SELECT id FROM operations WHERE id=? AND run_id=? AND production_id=? AND status='succeeded' AND settled=1",
                            (operation_id, lease.run_id, manifest.production_id)).fetchone():
                        raise EngineError('bundle_method_invalid', 'Actual same-Run successful settled method operation is required.', 422)
        return rights_observations

    def _verify_local_v03_reports(self, lease, preparation_id, manifest, documents, request, actual, quality):
        """Full real typed reports and original registry/current/reference validators."""
        indexed = {item.artifact_id: item for item in manifest.artifacts}
        reports = {}
        for artifact_id in quality.alignment_report_artifact_ids:
            item = indexed.get(artifact_id)
            if item is None or item.material_id is None or len(item.roles) != 1:
                raise EngineError('work_evidence_material_missing', 'Actual distinct report material is required.', 422)
            role = item.roles[0]
            model = TEXT_MODELS.get(role) or ({'precision_evaluation': c.PrecisionEvaluationReportV03,
                                              'precision_reference': c.PerWorkReferenceDocument}.get(role))
            value = documents.get(item.relative_path)
            if model is None or not isinstance(value, model) or role in reports:
                raise EngineError('work_evidence_material_missing', 'Exact typed unique report roles are required.', 422)
            check_record(value)
            reports[role] = value
        # ADR0082 method dispatch: only a real registered initial CTC needs a
        # work report. The local self-issued whisper estimate method has no CTC
        # lineage; it proves the installed policy plus its own actual settled
        # ASR/transcript/subtitle/not-measured alignment evidence instead.
        registered_ctc = self._registered_initial_alignment(lease, preparation_id)
        if not registered_ctc:
            from video_creator.application.local_evidence import (
                local_evidence_selected_policy,
            )

            with self.engine.db.connect_readonly() as connection:
                run = self.engine._lease(connection, lease)
                production = self.engine._production(connection, run['production_id'])
                resolved = local_evidence_selected_policy(
                    self.engine, production['owner'], production['project_id'], connection=connection)
            if resolved is None:
                raise EngineError('alignment_required',
                                  'Local whisper publication requires an installed and verified self-issued policy.', 409)
            if resolved.policy.alignment_evidence_policy != 'qualified_method_runtime_v1':
                raise EngineError('alignment_required',
                                  'Local whisper evidence requires the qualified method runtime policy.', 409)
            self._assert_whisper_not_measured(actual.alignment.precision)
            if (actual.transcript.method_ref != resolved.qualification.execution_identity.method_id
                    or actual.alignment.timestamp_method != 'whisper_word_estimate_not_forced_alignment'):
                raise EngineError('work_execution_identity_mismatch',
                                  'Alignment method differs from its admitted whisper estimate identity.', 409)
            # If a producer also staged its evidence documents, they must be the
            # exact admitted source; absence is fine because the registry row is
            # authoritative and already signature/expiry/scope verified.
            if 'evidence_policy' in reports and reports['evidence_policy'] != resolved.policy:
                raise EngineError('work_qualification_conflict', 'Staged policy differs from its admitted source.', 409)
            if 'method_qualification' in reports and reports['method_qualification'] != resolved.qualification:
                raise EngineError('work_qualification_conflict', 'Staged qualification differs from its admitted source.', 409)
            if 'method_benchmark_self_issued' in reports:
                validate_self_issued_benchmark(reports['method_benchmark_self_issued'])
                if reports['method_benchmark_self_issued'] != resolved.benchmark:
                    raise EngineError('benchmark_binding_invalid',
                                      'Staged self-issued declaration differs from its admitted source.', 422)
            return resolved
        if not {'evidence_policy', 'method_qualification', 'work_alignment_validation'} <= set(reports):
            raise EngineError('work_evidence_material_missing',
                              'Actual policy, qualification and runtime reports are required for registered CTC.', 422)
        resolved = self._validate_work_runtime(lease, preparation_id, actual,
            reports['work_alignment_validation'], manifest.audio_mappings)
        if reports['evidence_policy'] != resolved.policy or reports['method_qualification'] != resolved.qualification:
            raise EngineError('work_qualification_conflict', 'Reports differ from original real current registry admission.', 409)
        benchmark = reports.get('method_benchmark')
        reference = reports.get('method_benchmark_reference')
        self_issued = reports.get('method_benchmark_self_issued')
        if sum(value is not None for value in (benchmark, reference, self_issued)) != 1:
            raise EngineError('benchmark_binding_invalid',
                              'Exactly one actual benchmark, licensed reference or self-issued declaration is required.', 422)
        if benchmark is not None:
            validate_benchmark(benchmark)
            if benchmark != resolved.benchmark:
                raise EngineError('benchmark_binding_invalid', 'Actual benchmark differs from complete admitted source.', 422)
        elif self_issued is not None:
            validate_self_issued_benchmark(self_issued)
            if self_issued != resolved.benchmark:
                raise EngineError('benchmark_binding_invalid',
                                  'Self-issued not-performed declaration differs from its admitted source.', 422)
            if resolved.policy.alignment_evidence_policy == 'strict_reference_v1':
                raise EngineError('alignment_required',
                                  'Strict reference policy cannot use a not-performed local declaration.', 409)
        elif (reference != self.engine.evidence_registry.benchmark_reference(resolved.qualification.benchmark_report_ref)
                or reference.license_ref not in {right.rights_id for right in manifest.rights}):
            raise EngineError('benchmark_disclosure_approval_invalid', 'Original licensed benchmark disclosure is required.', 403)
        if actual.alignment.precision.status == 'measured':
            self._verify_per_work_precision(manifest, documents, actual, lease=lease, preparation_id=preparation_id)
        elif resolved.policy.alignment_evidence_policy == 'strict_reference_v1':
            raise EngineError('alignment_required', 'Strict reference policy requires original independent actual measurement.', 409)
        elif any(isinstance(value, c.PrecisionEvaluationReportV03) for value in documents.values()):
            raise EngineError('precision_evidence_conflict', 'Unmeasured work cannot hide actual measured evidence.', 422)
        return resolved

    @staticmethod
    def _local_v03_required_roles(registered_ctc: bool) -> set[str]:
        """Method dispatch: only registered CTC requires a work report."""
        if not registered_ctc:
            return set()
        return {'evidence_policy', 'method_qualification', 'work_alignment_validation'}

    @staticmethod
    def _assert_whisper_not_measured(precision):
        if (precision.status != 'not_measured' or precision.sample_count is not None
                or precision.p95_error_us is not None or precision.reference_ref is not None
                or precision.measurement_report_locator is not None):
            raise EngineError('work_precision_claim_invalid',
                              'Whisper word estimate cannot claim a measured precision.', 422)

    @staticmethod
    def _check_mapping_piece(piece):
        rate = Fraction(piece.playback_rate_num, piece.playback_rate_den)
        if piece.source_sample_start is not None:
            start = Fraction(piece.source_sample_start * 1_000_000, piece.source_track.clock.sample_rate)
            end = Fraction(piece.source_sample_end * 1_000_000, piece.source_track.clock.sample_rate)
        else:
            start = Fraction(piece.source_pts_start * piece.source_timebase_num * 1_000_000, piece.source_timebase_den)
            end = Fraction(piece.source_pts_end * piece.source_timebase_num * 1_000_000, piece.source_timebase_den)
        # Raw signed PTS may have an origin. Published ranges remain nonnegative.
        if start < 0:
            offset = Fraction(piece.source_track.clock.origin_pts or 0) * Fraction(piece.source_timebase_num * 1_000_000, piece.source_timebase_den)
            start, end = start - offset, end - offset
        for raw, observed, declared in ((start, piece.source_range.start_us, piece.start_rounding_error_us), (end, piece.source_range.end_us, piece.end_rounding_error_us)):
            error = Decimal(observed) - Decimal(raw.numerator) / Decimal(raw.denominator)
            if abs(error) >= 1 or error != declared:
                raise EngineError("audio_mapping_rounding_invalid", "Published audio boundary must keep its exact declared raw quantization error", 422)
        target_raw_duration = (end - start) / rate
        rounded = int((Decimal(target_raw_duration.numerator) / Decimal(target_raw_duration.denominator)).to_integral_value(rounding=ROUND_HALF_UP))
        if abs((piece.timeline_range.end_us - piece.timeline_range.start_us) - rounded) > 1:
            raise EngineError("audio_mapping_rate_invalid", "Actual rational time transform differs from its declared mapped range", 422)

    @staticmethod
    def _check_span(span, pieces):
        if not span.mapping_piece_ids or len(set(span.mapping_piece_ids)) != len(span.mapping_piece_ids) or any(key not in pieces for key in span.mapping_piece_ids):
            raise EngineError("semantic_audio_mapping_invalid", "Audio span must reference original mapping pieces", 422)
        candidates = [pieces[key] for key in span.mapping_piece_ids]
        if any(piece.source_track != span.track for piece in candidates):
            raise EngineError("semantic_audio_mapping_invalid", "Audio span uses another raw track", 422)
        for before, after in pairwise(candidates):
            if before.source_range.end_us != after.source_range.start_us or before.timeline_range.end_us != after.timeline_range.start_us:
                raise EngineError("semantic_audio_mapping_invalid", "A cross-piece span must preserve contiguous raw and final ranges", 422)
        first, last = candidates[0], candidates[-1]
        if not (first.source_range.start_us <= span.intrinsic_range.start_us < first.source_range.end_us and last.source_range.start_us < span.intrinsic_range.end_us <= last.source_range.end_us):
            raise EngineError("semantic_audio_mapping_invalid", "Audio span is outside its actual raw mapping", 422)
        for piece, source_boundary, target_boundary in ((first, span.intrinsic_range.start_us, span.timeline_range.start_us), (last, span.intrinsic_range.end_us, span.timeline_range.end_us)):
            transformed = Fraction(piece.timeline_range.start_us) + Fraction((source_boundary - piece.source_range.start_us) * piece.playback_rate_den, piece.playback_rate_num)
            error = abs(Fraction(target_boundary) - transformed)
            if error > 1:
                raise EngineError("semantic_audio_mapping_invalid", "Audio span does not follow the actual rational time transform", 422)


def local_fact_id(binding: c.SourceBinding, text: str) -> str:
    if text not in binding.confirmed_facts:
        raise EngineError("source_fact_denied", "Local identity requires an actual unchanged caller fact", 422)
    body = {"system": binding.system, "namespace": binding.namespace, "article_id": binding.article_id,
            "article_revision": binding.article_revision, "topic_id": binding.topic_id, "topic_revision": binding.topic_revision, "text": text}
    return "fact-" + digest(json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def serialize_subtitles(track: c.SubtitleTrack) -> tuple[bytes, bytes, tuple[c.SubtitleQuantization, ...]]:
    quantized = [[cue.timeline_range.start_us // 1000, min((cue.timeline_range.end_us + 999) // 1000, track.timeline_duration_us // 1000)] for cue in track.cues]
    for index in range(len(track.cues) - 1):
        before, after = track.cues[index], track.cues[index + 1]
        if before.timeline_range.end_us <= after.timeline_range.start_us:
            quantized[index][1] = min(quantized[index][1], quantized[index + 1][0])
        elif not after.overlap_declared:
            raise EngineError("subtitle_overlap_invalid", "Original overlapping cues need an explicit declaration", 422)
    errors, srt, vtt = [], [], ["WEBVTT\n"]
    def timestamp(value, separator):
        hours, remainder = divmod(value, 3_600_000)
        minutes, remainder = divmod(remainder, 60_000)
        seconds, milliseconds = divmod(remainder, 1000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}{separator}{milliseconds:03d}"
    for index, (cue, (start, end)) in enumerate(zip(track.cues, quantized, strict=True)):
        if end <= start:
            raise EngineError("subtitle_quantization_invalid", "A cue collapses under the declared millisecond serializer", 422)
        errors.append(c.SubtitleQuantization(cue_id=cue.cue_id, start_error_us=start * 1000 - cue.timeline_range.start_us, end_error_us=end * 1000 - cue.timeline_range.end_us))
        srt.append(f"{index + 1}\n{timestamp(start, ',')} --> {timestamp(end, ',')}\n{cue.text}\n")
        vtt.append(f"{timestamp(start, '.')} --> {timestamp(end, '.')}\n{cue.text}\n")
    return ("\n".join(srt) + "\n").encode(), ("\n".join(vtt) + "\n").encode(), tuple(errors)
