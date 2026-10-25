"""Durable installation trust; ordinary requests cannot install qualifications.

Trust roots are supplied by the trusted launcher/OS configuration. Empty roots
are the normal unconfigured state, never a permissive validator callback.
"""

import hashlib
import hmac
import json
import secrets
from collections.abc import Mapping

from pydantic import ValidationError

from video_creator.application.alignment_math import LIMIT_US, nearest_rank, unit_errors
from video_creator.application.engine import canonical, digest
from video_creator.domain import contracts as c
from video_creator.domain.errors import EngineError
from video_creator.domain.evidence import (
    EvidenceAdminCapability,
    EvidenceApproval,
    EvidenceRevocation,
    ReferenceIssuerAdmission,
    ReferenceIssuerApproval,
    ResolvedEvidencePolicy,
)


def evidence_sha(model) -> str:
    body = model.model_dump(mode="json")
    body.pop("content_sha256", None)
    return digest(json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def check_evidence_record(model):
    if evidence_sha(model) != model.content_sha256:
        raise EngineError("evidence_hash_invalid", "Evidence differs from its immutable complete record", 422)


def validate_benchmark(report: c.MethodBenchmarkReport):
    check_evidence_record(report)
    errors = []
    for audio in report.audios:
        if audio.language not in report.applicability.languages or audio.duration_us > report.applicability.maximum_duration_us:
            raise EngineError("benchmark_scope_invalid", "Corpus audio is outside its declared actual scope", 422)
        errors.extend(unit_errors(audio.predicted_units, audio.reference_units, audio.boundaries, audio.duration_us))
    count, p95 = nearest_rank(errors)
    if (report.sample_count, report.p95_error_us) != (count, p95):
        raise EngineError("criterion_mismatch", "Evidence uses a different statistic from complete unit max/N nearest rank", 422)
    if p95 > LIMIT_US or report.source_gaps:
        raise EngineError("benchmark_not_qualified", "Whole benchmark exceeds the criterion or has unresolved gaps", 409)


def validate_self_issued_benchmark(report: c.LocalSelfIssuedBenchmarkV1):
    """ADR0082 section 3.4: self-consistency, identity equality and literals only.

    It never calls `validate_benchmark`: there is no corpus, sample count, P95,
    listener or arbitration fact to validate, and inventing one is forbidden.
    """
    check_evidence_record(report)
    if (report.evaluation_scope != "capability_benchmark_not_performed"
            or report.precision_claim != "not_measured"
            or report.independent_reference != "none"
            or not report.authority_ref.startswith("local-selfissued-authority-")
            or not set(c.LOCAL_SELF_ISSUED_BENCHMARK_LIMITATIONS) <= set(report.limitations)
            or not report.limitations):
        raise EngineError("local_evidence_benchmark_invalid",
                          "A not-performed benchmark must retain its fixed local-self-issued literals", 422)


def _validated_benchmark(raw) -> c.MethodBenchmarkReport | c.LocalSelfIssuedBenchmarkV1:
    body = json.loads(raw) if isinstance(raw, (str, bytes)) else raw
    if not isinstance(body, dict):
        raise EngineError("evidence_benchmark_invalid", "Benchmark bytes are not a single document", 422)
    if body.get("evaluation_scope") == "capability_benchmark_not_performed":
        benchmark = c.LocalSelfIssuedBenchmarkV1.model_validate(body)
        validate_self_issued_benchmark(benchmark)
        return benchmark
    benchmark = c.MethodBenchmarkReport.model_validate(body)
    validate_benchmark(benchmark)
    return benchmark


class PersistentEvidenceRegistry:
    def __init__(self, engine, *, trust_roots: Mapping[str, bytes] | None = None,
                 trusted_configuration_sha256: str | None = None,
                 minimum_registry_revision: int | None = None,
                 reference_keys: Mapping[tuple[str, str], bytes] | None = None):
        self.engine = engine
        self._roots = dict(trust_roots or {})
        self._reference_keys = dict(reference_keys or {})
        if self._roots and (not trusted_configuration_sha256 or minimum_registry_revision is None
                            or any(len(value) < 32 for value in self._roots.values())):
            raise EngineError("evidence_configuration_invalid", "Trusted roots need a configuration identity and current external revocation floor", 503)
        self.configuration_sha256 = trusted_configuration_sha256
        self.minimum_registry_revision = minimum_registry_revision
        self._admin = EvidenceAdminCapability(secrets.token_hex(32))
        if any(len(value) < 32 for value in self._reference_keys.values()):
            raise EngineError("evidence_configuration_invalid", "Reference keys require a complete strong trusted configuration", 503)

    def administration_capability(self) -> EvidenceAdminCapability:
        # This object is only obtained through trusted in-process construction;
        # neither this method nor admission/revocation is registered in API/MCP.
        if not self._roots:
            raise EngineError("evidence_authority_unconfigured", "No trusted evidence issuer is installed", 503)
        return self._admin

    def _administration(self, capability):
        if capability is not self._admin or not self._roots:
            raise EngineError("evidence_administration_denied", "A current trusted installation capability is required", 403)

    def _signature(self, issuer, body, signature):
        key = self._roots.get(issuer)
        if key is None:
            raise EngineError("evidence_issuer_untrusted", "Evidence issuer is not trusted by this installation", 403)
        raw = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        if not hmac.compare_digest(hmac.new(key, raw, hashlib.sha256).hexdigest(), signature):
            raise EngineError("evidence_signature_invalid", "Evidence approval signature is not valid", 403)

    def _revision(self, connection):
        value = int(connection.execute("SELECT value FROM metadata WHERE key='evidence_registry_revision'").fetchone()[0])
        if not self._roots or self.minimum_registry_revision is None:
            raise EngineError("evidence_authority_unconfigured", "Current external trust and revocation state are required", 503)
        if value < self.minimum_registry_revision:
            raise EngineError("evidence_restore_refresh_required", "Restored registry predates known revocation facts", 503)
        return value

    def _next_revision(self, connection):
        value = self._revision(connection) + 1
        connection.execute("UPDATE metadata SET value=? WHERE key='evidence_registry_revision'", (str(value),))
        return value

    def install(self, capability: EvidenceAdminCapability, document: c.EvidencePolicyRevision | c.MethodQualificationRef,
                benchmark: c.MethodBenchmarkReport | c.LocalSelfIssuedBenchmarkV1, approval: EvidenceApproval):
        self._administration(capability)
        if isinstance(benchmark, c.LocalSelfIssuedBenchmarkV1):
            validate_self_issued_benchmark(benchmark)
        else:
            validate_benchmark(benchmark)
        check_evidence_record(document)
        if document.issuer != approval.issuer or approval.document_sha256 != document.content_sha256 or approval.benchmark_content_sha256 != benchmark.content_sha256:
            raise EngineError("evidence_approval_conflict", "Approval must bind the complete actual document and benchmark", 403)
        approval_identity = digest(approval.issuer + ":" + approval.approval_id)
        if approval_identity not in document.approval_refs:
            raise EngineError("evidence_approval_conflict", "Document does not retain this trusted approval identity", 403)
        body = approval.model_dump(mode="json")
        body.pop("signature")
        self._signature(approval.issuer, body, approval.signature)
        qualification = document.qualification_ref if isinstance(document, c.EvidencePolicyRevision) else document
        if (qualification.benchmark_report_ref.report_id, qualification.benchmark_report_ref.content_sha256,
            qualification.execution_identity, qualification.applicability, qualification.authority_ref) != (
                benchmark.report_id, benchmark.content_sha256, benchmark.execution_identity, benchmark.applicability, benchmark.authority_ref):
            raise EngineError("evidence_qualification_conflict", "Qualification must bind the exact complete benchmark execution and scope", 422)
        kind = "policy" if isinstance(document, c.EvidencePolicyRevision) else "qualification"
        identifier = document.policy_id if kind == "policy" else document.qualification_id
        with self.engine.db.transaction() as connection:
            self._revision(connection)
            previous = connection.execute("SELECT * FROM alignment_admissions WHERE kind=? AND admission_id=? AND revision=?", (kind, identifier, document.revision)).fetchone()
            if previous:
                if previous["body"] != canonical(document) or previous["approval_json"] != canonical(approval) or previous["benchmark_json"] != canonical(benchmark):
                    raise EngineError("evidence_admission_conflict", "An installed admission revision is immutable", 409)
                return previous["installation_sequence"]
            if kind == "policy":
                self._load(connection, "qualification", qualification.qualification_id, qualification.revision, qualification.content_sha256)
            sequence = self._next_revision(connection)
            connection.execute("INSERT INTO alignment_admissions VALUES(?,?,?,?,?,?,?,?,?,?,?)", (
                kind, identifier, document.revision, canonical(document), document.content_sha256, document.issuer,
                canonical(approval), canonical(benchmark), benchmark.content_sha256, sequence, self.engine.clock()))
            connection.execute("INSERT INTO metadata(key,value) VALUES('evidence_configuration_sha256',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (self.configuration_sha256,))
            return sequence

    def revoke(self, capability: EvidenceAdminCapability, revocation: EvidenceRevocation) -> int:
        self._administration(capability)
        if revocation.target_revision <= 0 or revocation.effective_at_us < 0 or not revocation.reason.strip():
            raise EngineError("evidence_revocation_invalid", "Revocation needs an exact target, effective time and reason", 422)
        body = revocation.model_dump(mode="json")
        body.pop("signature")
        self._signature(revocation.issuer, body, revocation.signature)
        with self.engine.db.transaction() as connection:
            self._revision(connection)
            old = connection.execute("SELECT * FROM alignment_revocations WHERE issuer=? AND dedupe_key=?", (revocation.issuer, revocation.dedupe_key)).fetchone()
            if old:
                if old["body"] != canonical(revocation):
                    raise EngineError("evidence_revocation_conflict", "Revocation identity already has a different immutable body", 409)
                return old["registry_revision"]
            target = connection.execute("SELECT issuer FROM alignment_admissions WHERE kind=? AND admission_id=? AND revision=?", (revocation.target_kind, revocation.target_id, revocation.target_revision)).fetchone()
            if not target or target[0] != revocation.issuer:
                raise EngineError("evidence_revocation_denied", "Only the original trusted issuer may revoke this admission", 403)
            sequence = self._next_revision(connection)
            connection.execute("INSERT INTO alignment_revocations VALUES(?,?,?,?,?,?,?,?,?)", (
                revocation.issuer, revocation.dedupe_key, revocation.target_kind, revocation.target_id,
                revocation.target_revision, revocation.effective_at_us, revocation.reason, canonical(revocation), sequence))
            return sequence

    def install_reference_issuer(self, capability: EvidenceAdminCapability, admission: ReferenceIssuerAdmission,
                                 approval: ReferenceIssuerApproval) -> int:
        self._administration(capability)
        check_evidence_record(admission)
        if (admission.revision <= 0 or admission.valid_from_us < 0 or admission.expires_at_us <= admission.valid_from_us
                or not admission.audio_sha256 or not admission.listener_material_sha256 or not admission.arbitration_material_sha256
                or not admission.independent_approval_refs):
            raise EngineError("reference_scope_invalid", "Actual reference issuer needs approved audio/listener/arbitration scope", 422)
        if approval.issuer != admission.issuer or approval.scope_content_sha256 != admission.content_sha256:
            raise EngineError("reference_approval_invalid", "Trusted issuer approval must bind this exact reference scope", 403)
        body = approval.model_dump(mode="json")
        body.pop("signature")
        self._signature(approval.issuer, body, approval.signature)
        with self.engine.db.transaction() as connection:
            old = connection.execute("SELECT * FROM alignment_admissions WHERE kind='reference_issuer' AND admission_id=? AND revision=?", (admission.authority_id, admission.revision)).fetchone()
            if old:
                if old["body"] != canonical(admission) or old["approval_json"] != canonical(approval):
                    raise EngineError("evidence_admission_conflict", "Reference issuer revision is immutable", 409)
                return old["installation_sequence"]
            sequence = self._next_revision(connection)
            connection.execute("INSERT INTO alignment_admissions VALUES('reference_issuer',?,?,?,?,?,?,?,?,?,?)", (
                admission.authority_id, admission.revision, canonical(admission), admission.content_sha256,
                admission.issuer, canonical(approval), "{}", admission.content_sha256, sequence, self.engine.clock()))
            return sequence

    def verify_work_reference(self, reference: c.PerWorkReferenceDocument, *, lease: c.LeaseGrant,
                              preparation_id: str, actual: c.ActualTranscriptDocumentV03,
                              source_documents: Mapping[str, tuple[c.EvidenceMaterialRef, bytes]], connection=None):
        if connection is None:
            with self.engine.db.connect() as current:
                return self.verify_work_reference(reference, lease=lease, preparation_id=preparation_id,
                    actual=actual, source_documents=source_documents, connection=current)
        self._revision(connection)
        run = self.engine._lease(connection, lease)
        production = self.engine._production(connection, run["production_id"])
        prepared = connection.execute("SELECT id FROM bundle_revisions WHERE id=? AND run_id=? AND request_revision_id=?", (preparation_id, run["id"], production["request_revision_id"])).fetchone()
        if not prepared or run["paused"]:
            raise EngineError("reference_scope_denied", "Reference is outside this ordinary fixed preparation", 403)
        row = connection.execute("SELECT * FROM alignment_admissions WHERE kind='reference_issuer' AND admission_id=? AND revision=?", (reference.authority_ref.authority_id, reference.authority_ref.revision)).fetchone()
        if not row or row["content_sha256"] != reference.authority_ref.content_sha256:
            raise EngineError("alignment_required", "No current approved independent reference issuer exists", 409)
        scope = ReferenceIssuerAdmission.model_validate_json(row["body"])
        check_evidence_record(scope)
        approval = ReferenceIssuerApproval.model_validate_json(row["approval_json"])
        unsigned = approval.model_dump(mode="json")
        unsigned.pop("signature")
        self._signature(approval.issuer, unsigned, approval.signature)
        if (approval.issuer, approval.scope_content_sha256) != (scope.issuer, scope.content_sha256):
            raise EngineError("reference_approval_invalid", "Actual separate issuer approval does not bind this scope", 403)
        now = self.engine.clock()
        revoked = connection.execute("SELECT 1 FROM alignment_revocations WHERE target_kind='reference_issuer' AND target_id=? AND target_revision=? AND effective_at_us<=?", (scope.authority_id, scope.revision, now)).fetchone()
        if (revoked or scope.valid_from_us > now or scope.expires_at_us <= now or scope.reference_issuer != reference.issuer
                or scope.key_id != reference.signature.key_id or (scope.owner_subject, scope.project_id) != (production["owner"], production["project_id"])
                or reference.input_audio_sha256 not in scope.audio_sha256 or reference.input_audio_sha256 != actual.transcript.input_audio_sha256):
            raise EngineError("reference_scope_denied", "Reference issuer is inactive or outside this exact work/audio scope", 403)
        key = self._reference_keys.get((reference.issuer, reference.signature.key_id))
        if key is None:
            raise EngineError("reference_issuer_unconfigured", "Reference scope key is unavailable; it confers no administrative privilege", 503)
        check_evidence_record(reference)
        body = reference.model_dump(mode="json")
        body.pop("signature")
        body.pop("content_sha256")
        expected = hmac.new(key, json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, reference.signature.digest):
            raise EngineError("reference_signature_invalid", "Reference declaration signature is invalid", 403)
        units = tuple(item.utterance_id for item in actual.transcript.utterances) if actual.alignment.units == "utterance" else tuple(word.word_id for utterance in actual.transcript.utterances for word in utterance.words)
        if reference.units != units or len(units) != len(set(units)):
            raise EngineError("reference_units_invalid", "Reference units must preserve the complete ordered actual transcript population", 422)
        if any(item.reference_range.end_us > actual.transcript.duration_us for item in reference.boundaries):
            raise EngineError("reference_range_invalid", "Reference boundary exceeds actual intrinsic audio duration", 422)
        all_refs = (*reference.independent_listener_refs, reference.arbitration_ref)
        if set(source_documents) != {item.artifact_id for item in all_refs}:
            raise EngineError("reference_source_missing", "All actual listener and arbitration bodies are required", 422)
        listener_ids = set()
        # Strict text parsing is imported lazily to keep schema/module imports
        # free of filesystem/provider work and avoid a module dependency cycle.
        from video_creator.application.bundles import strict_json
        for ref in all_refs:
            supplied, raw = source_documents[ref.artifact_id]
            item = connection.execute("SELECT * FROM bundle_items WHERE preparation_id=? AND artifact_id=? AND schema_kind='audit_summary' AND status='ready'", (preparation_id, ref.artifact_id)).fetchone()
            if supplied != ref or not item or (item["sha256"], item["size"]) != (ref.sha256, len(raw)) or hashlib.sha256(raw).hexdigest() != ref.sha256:
                raise EngineError("reference_source_invalid", "Reference source differs from its actual immutable ready material", 422)
            doc = strict_json(raw)
            facts = doc.get("findings") if isinstance(doc, dict) else None
            if not isinstance(facts, dict) or (facts.get("document_id"), facts.get("revision"), facts.get("input_audio_sha256"), facts.get("units")) != (ref.document_id, ref.revision, reference.input_audio_sha256, list(reference.units)):
                raise EngineError("reference_source_invalid", "Actual source identity/audio/complete units differ from reference declaration", 422)
            if facts.get("independent_approval_ref") not in scope.independent_approval_refs:
                raise EngineError("reference_independence_unapproved", "Source independence needs its actual separate trusted approval", 403)
            if ref == reference.arbitration_ref:
                if (ref.sha256 not in scope.arbitration_material_sha256 or facts.get("decision") not in {"no_dispute", "adjudicated"}
                        or not facts.get("reviewer_id") or facts.get("listener_artifact_ids") != [item.artifact_id for item in reference.independent_listener_refs]
                        or facts.get("reference_boundaries") != [item.model_dump(mode="json") for item in reference.boundaries]):
                    raise EngineError("reference_arbitration_invalid", "Actual arbitration must finalize the complete independent boundary set", 422)
            elif (ref.sha256 not in scope.listener_material_sha256 or not facts.get("listener_id") or not facts.get("annotation_tool")
                    or facts.get("independent_of_method_id") != actual.alignment.method_ref or facts["listener_id"] in listener_ids):
                raise EngineError("reference_listener_invalid", "Actual independent listener/tool/source scope is unavailable", 422)
            else:
                listener_ids.add(facts["listener_id"])
        return scope

    def reference_is_current(self, lease, preparation_id, reference, *, connection):
        self._revision(connection)
        run = self.engine._lease(connection, lease)
        production = self.engine._production(connection, run["production_id"])
        prepared = connection.execute("SELECT id FROM bundle_revisions WHERE id=? AND run_id=?", (preparation_id, run["id"])).fetchone()
        row = connection.execute("SELECT * FROM alignment_admissions WHERE kind='reference_issuer' AND admission_id=? AND revision=?", (reference.authority_ref.authority_id, reference.authority_ref.revision)).fetchone()
        if not prepared or not row or row["content_sha256"] != reference.authority_ref.content_sha256:
            raise EngineError("reference_scope_denied", "Reference approval is outside this publication preparation", 403)
        scope = ReferenceIssuerAdmission.model_validate_json(row["body"])
        check_evidence_record(scope)
        approval = ReferenceIssuerApproval.model_validate_json(row["approval_json"])
        unsigned = approval.model_dump(mode="json")
        unsigned.pop("signature")
        self._signature(approval.issuer, unsigned, approval.signature)
        if (approval.issuer, approval.scope_content_sha256) != (scope.issuer, scope.content_sha256):
            raise EngineError("reference_approval_invalid", "Publication needs this exact immutable reference issuer approval", 403)
        now = self.engine.clock()
        revoked = connection.execute("SELECT 1 FROM alignment_revocations WHERE target_kind='reference_issuer' AND target_id=? AND target_revision=? AND effective_at_us<=?", (scope.authority_id, scope.revision, now)).fetchone()
        if (revoked or scope.expires_at_us <= now or scope.valid_from_us > now
                or (scope.owner_subject, scope.project_id, scope.reference_issuer, scope.key_id) != (
                    production["owner"], production["project_id"], reference.issuer, reference.signature.key_id)
                or reference.input_audio_sha256 not in scope.audio_sha256
                or (reference.issuer, reference.signature.key_id) not in self._reference_keys):
            raise EngineError("reference_scope_denied", "Reference scope is currently revoked, expired or unauthorized", 403)
        body = reference.model_dump(mode="json")
        body.pop("signature")
        body.pop("content_sha256")
        expected = hmac.new(self._reference_keys[(reference.issuer, reference.signature.key_id)],
            json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, reference.signature.digest):
            raise EngineError("reference_signature_invalid", "Publication no longer has the actual current reference signature", 403)

    def _load(self, connection, kind, identifier, revision, content_sha256):
        self._revision(connection)
        row = connection.execute("SELECT * FROM alignment_admissions WHERE kind=? AND admission_id=? AND revision=?", (kind, identifier, revision)).fetchone()
        if not row or row["content_sha256"] != content_sha256:
            raise EngineError("alignment_required", "Exact trusted evidence admission is unavailable", 409)
        model = c.EvidencePolicyRevision if kind == "policy" else c.MethodQualificationRef
        try:
            document = model.model_validate_json(row["body"])
            benchmark = _validated_benchmark(row["benchmark_json"])
            approval = EvidenceApproval.model_validate_json(row["approval_json"])
        except (ValidationError, TypeError, ValueError):
            raise EngineError("evidence_admission_invalid",
                              "Stored evidence admission is not its canonical complete document", 422) from None
        body = approval.model_dump(mode="json")
        body.pop("signature")
        self._signature(approval.issuer, body, approval.signature)
        check_evidence_record(document)
        if (approval.document_sha256, approval.benchmark_content_sha256) != (document.content_sha256, benchmark.content_sha256):
            raise EngineError("evidence_approval_conflict", "Stored approval binding is inconsistent", 403)
        # ADR0082 review P2-3: the document and benchmark must mutually agree on
        # report identity, content hash, execution identity, applicability and
        # authority. A policy embeds the qualification; a qualification names the
        # benchmark. Any mismatch is a conflict, never a silent replacement.
        if kind == "policy":
            embedded = document.qualification_ref
        else:
            embedded = document
        if (embedded.benchmark_report_ref.report_id, embedded.benchmark_report_ref.content_sha256,
                embedded.execution_identity, embedded.applicability, embedded.authority_ref) != (
                benchmark.report_id, benchmark.content_sha256, benchmark.execution_identity,
                benchmark.applicability, benchmark.authority_ref):
            raise EngineError("evidence_qualification_conflict",
                              "Document, qualification and benchmark do not share one exact method identity", 409)
        now = self.engine.clock()
        revoked = connection.execute("SELECT 1 FROM alignment_revocations WHERE target_kind=? AND target_id=? AND target_revision=? AND effective_at_us<=?", (kind, identifier, revision, now)).fetchone()
        if revoked or document.valid_from_us > now or document.expires_at_us <= now:
            raise EngineError("evidence_admission_inactive", "Evidence is expired, not yet valid or currently revoked", 409)
        return document, benchmark

    def admitted(self, kind, identifier, revision, content_sha256):
        """Trusted-startup read of one already admitted row with full verification.

        Used by the local evidence administrator/validators: it re-checks the HMAC
        approval, the document/benchmark cross-binding, expiry/revocation and the
        registry floor instead of trusting a metadata or qualification row shape.
        """
        with self.engine.db.connect_readonly() as connection:
            return self._load(connection, kind, identifier, revision, content_sha256)

    def preauthorize(self, capability: EvidenceAdminCapability, subject: str, project_id: str | None,
                     policy_ref: c.EvidencePolicyRevisionRef):
        self._administration(capability)
        with self.engine.db.transaction() as connection:
            resolved = self.resolve(subject, project_id, policy_ref, connection=connection)
            scope = subject + ":" + (project_id or "instance")
            # Durable local selection of an already admitted policy, not authority approval.
            connection.execute("INSERT INTO metadata(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", ("evidence_default:" + scope, canonical(resolved.policy_ref)))

    def register_benchmark_reference(self, capability: EvidenceAdminCapability, reference: c.MethodBenchmarkReference,
                                     approval: EvidenceApproval):
        self._administration(capability)
        check_evidence_record(reference)
        if (approval.document_sha256, approval.benchmark_content_sha256) != (reference.content_sha256, reference.origin_report_ref.content_sha256):
            raise EngineError("benchmark_disclosure_approval_invalid", "Trusted disclosure approval must bind its actual document and original benchmark", 403)
        unsigned = approval.model_dump(mode="json")
        unsigned.pop("signature")
        self._signature(approval.issuer, unsigned, approval.signature)
        key = "evidence_benchmark_reference:" + reference.origin_report_ref.content_sha256
        body = json.dumps({"reference": reference.model_dump(mode="json"), "approval": approval.model_dump(mode="json")}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        with self.engine.db.transaction() as connection:
            self._revision(connection)
            old = connection.execute("SELECT value FROM metadata WHERE key=?", (key,)).fetchone()
            if old and old[0] != body:
                raise EngineError("benchmark_disclosure_conflict", "Trusted benchmark disclosure document is immutable", 409)
            if not old:
                self._next_revision(connection)
                connection.execute("INSERT INTO metadata(key,value) VALUES(?,?)", (key, body))

    def benchmark_reference(self, report_ref: c.EvidenceReportRef) -> c.MethodBenchmarkReference:
        with self.engine.db.connect() as connection:
            self._revision(connection)
            row = connection.execute("SELECT value FROM metadata WHERE key=?", ("evidence_benchmark_reference:" + report_ref.content_sha256,)).fetchone()
        if not row:
            raise EngineError("benchmark_reference_unconfigured", "No actual trusted licensed provenance disclosure is registered", 503)
        body = json.loads(row[0])
        reference = c.MethodBenchmarkReference.model_validate(body["reference"])
        approval = EvidenceApproval.model_validate(body["approval"])
        check_evidence_record(reference)
        unsigned = approval.model_dump(mode="json")
        unsigned.pop("signature")
        self._signature(approval.issuer, unsigned, approval.signature)
        if reference.origin_report_ref != report_ref or (approval.document_sha256, approval.benchmark_content_sha256) != (reference.content_sha256, report_ref.content_sha256):
            raise EngineError("benchmark_disclosure_approval_invalid", "Actual provenance disclosure changed its original report or approved bytes", 403)
        return reference

    def resolve(self, subject: str, project_id: str | None, policy_ref: c.EvidencePolicyRevisionRef | None = None,
                *, connection=None) -> ResolvedEvidencePolicy:
        if connection is None:
            with self.engine.db.connect() as current:
                return self.resolve(subject, project_id, policy_ref, connection=current)
        self._revision(connection)
        if policy_ref is None:
            for scope in (subject + ":" + (project_id or "instance"), subject + ":instance"):
                value = connection.execute("SELECT value FROM metadata WHERE key=?", ("evidence_default:" + scope,)).fetchone()
                if value:
                    policy_ref = c.EvidencePolicyRevisionRef.model_validate_json(value[0])
                    break
        if policy_ref is None:
            raise EngineError("alignment_required", "No trusted project or installation policy is preauthorized", 409)
        policy, benchmark = self._load(connection, "policy", policy_ref.policy_id, policy_ref.revision, policy_ref.content_sha256)
        if policy.owner_subject != subject or policy.project_id not in (None, project_id):
            raise EngineError("evidence_policy_scope_denied", "Policy does not preauthorize this subject/project", 403)
        qref = policy.qualification_ref
        qualification, actual_benchmark = self._load(connection, "qualification", qref.qualification_id, qref.revision, qref.content_sha256)
        if qualification != qref or actual_benchmark != benchmark:
            raise EngineError("evidence_qualification_conflict", "Policy and qualification refer to different complete evidence", 409)
        return ResolvedEvidencePolicy(policy, qualification, benchmark, self._revision(connection))

    def verify(self, subject: str, project_id: str, ref: c.EvidencePolicyRevisionRef,
               execution: c.AlignmentExecutionIdentity, language: str, media_type: str,
               duration_us: int, transformations: tuple[str, ...], *, connection=None) -> ResolvedEvidencePolicy:
        resolved = self.resolve(subject, project_id, ref, connection=connection)
        scope = resolved.qualification.applicability
        if (execution != resolved.qualification.execution_identity or language not in scope.languages
                or media_type not in scope.input_media_types or duration_us > scope.maximum_duration_us
                or not transformations or not set(transformations) <= set(scope.transformations)):
            raise EngineError("evidence_execution_out_of_scope", "Actual work execution is outside the exact qualified method scope", 409)
        return resolved
