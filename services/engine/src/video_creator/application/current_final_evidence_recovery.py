"""Controlled original assembly persistence and same-claim pure recovery reads."""

import hashlib
import json
import sys

from pydantic import ValidationError

from video_creator.application.affected_repair_service import (
    AffectedRepairService,
    canonical_body,
)
from video_creator.application.component_diagnosis_service import (
    ComponentDiagnosisService,
)
from video_creator.application.current_final_evidence_journal import (
    PREFIX,
    parse_journal,
    prepared_current,
)
from video_creator.application.diagnosed_affected_service import (
    DiagnosedAffectedService,
)
from video_creator.application.diagnostic_selection import DiagnosticSelectionService
from video_creator.application.engine import canonical, digest
from video_creator.application.plan_repair_service import PlanRepairService
from video_creator.application.registered_alignment import RegisteredAlignmentService
from video_creator.domain import contracts as c
from video_creator.domain import local_bundle as local
from video_creator.domain.bundle import BundlePreparationIntent
from video_creator.domain.current_final_evidence import (
    AssemblyContextRef,
    CurrentFinalAssemblyContext,
    CurrentFinalAssemblyContextV2,
    CurrentFinalEvidenceReadSet,
)
from video_creator.domain.errors import EngineError

ASSEMBLY_PREFIX = 'current_final_assembly:'
_NO_NEW_ASSEMBLY = object()
DOCUMENT_PATHS = {
    'insight': 'Creative/insight.json', 'brief': 'Creative/brief.json', 'plan': 'Creative/production-plan.json',
    'script': 'Text/approved-script.json', 'transcript': 'Text/actual-transcript.json',
    'srt': 'Text/subtitles.srt', 'vtt': 'Text/subtitles.vtt', 'summary': 'Semantics/work-summary.json',
    'sources': 'Semantics/source-bindings.json', 'shots': 'Semantics/shots.jsonl',
    'segments': 'Semantics/semantic-segments.jsonl', 'rag': 'Semantics/rag-chunks.jsonl',
    'quality': 'Checks/quality-report.json', 'audit': 'Checks/assembly-audit.json',
    'authorization': 'Checks/production-authorization.json', 'policy': 'Checks/evidence-policy.json',
    'qualification': 'Checks/method-qualification.json', 'benchmark': 'Checks/method-benchmark-reference.json',
    'work_validation': 'Checks/work-alignment-validation.json', 'reference': 'Checks/precision-reference.json',
    'measurement': 'Checks/precision-evaluation.json',
}


def has_original_masters(intent, assembly) -> bool:
    """Version dispatch for the original master set behind one committed assembly.

    ADR0075 local works select only their applicable subset of the fixed master
    roles (a silent visual work has `video` + `cover`), so a local assembly is
    compared with its exact selection and the preparation intent that was
    authored from it. Every legacy v0.2/v0.3 assembly keeps the original
    four-master rule unchanged.
    """
    if type(assembly) is local.LocalFinalAssemblyContextV1:
        roles = tuple(assembly.selection.master_roles)
        artifacts = tuple(assembly.media_artifacts)
        assets = tuple(intent.media_asset_ids)
        return (bool(roles)
                and tuple(artifact.roles for artifact in artifacts) == tuple((role,) for role in roles)
                and tuple(artifact.asset_id for artifact in artifacts) == assets
                and len(set(roles)) == len(roles)
                and len(set(assets)) == len(assets))
    return len(intent.media_asset_ids) == 4


def final_read_set_asr(assembly, validated):
    """The only value the read-set's `asr` slot may hold for this assembly.

    `CurrentFinalEvidenceReadSet.asr` is declared `CurrentFinalAsrRead | None`.
    A local assembly's committed speech document (`LocalSpeechEvidenceV1`) is a
    different type; storing it in `asr` violates that declaration and readers
    reach it as an uncaught `AttributeError`. Local validation has already
    re-proved the speech facts, so the slot stays empty for local works and the
    declared contract (typed read or None) is preserved.
    """
    if type(assembly) is local.LocalFinalAssemblyContextV1:
        return None
    return validated


class CurrentFinalEvidenceRecovery(DiagnosticSelectionService, ComponentDiagnosisService, DiagnosedAffectedService, PlanRepairService, AffectedRepairService, RegisteredAlignmentService):
    def _original_final_candidate(self, row, journal, binding):
        from video_creator.application.bundles import strict_json
        expected = (row['manifest_sha256'] if row['manifest_file_key'] else
                    journal.snapshot.candidate_manifest_file_sha256 if row['id'] == journal.snapshot.preparation_id else None)
        if expected is None:
            return None
        path = (self._file('BundleManifests', row['manifest_file_key']) if row['manifest_file_key']
                else self._file('CurrentFinalCandidates', 'candidate-' + expected))
        if not path.is_file():
            raise EngineError('final_candidate_unavailable', 'Original committed candidate file missing', 503)
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise EngineError('final_candidate_invalid', 'Original candidate file SHA changed', 422)
        manifest = c.parse_bundle_manifest(strict_json(raw))
        if (manifest.instance_id, manifest.production_id, manifest.run_id, manifest.bundle_id,
                manifest.bundle_revision_id, manifest.request_revision_id, manifest.request_sha256) != (
                binding.instance_id, binding.production_id, binding.run_id, row['bundle_id'], row['revision_id'],
                binding.request_revision_id, binding.request_sha256):
            raise EngineError('final_candidate_invalid', 'Original candidate complete identity changed', 422)
        return manifest, raw, expected

    def _original_asr(self):
        journal = getattr(self, '_original_asr_journal', None)
        if journal is None or journal.engine is not self.engine:
            raise EngineError('asr_recovery_validation_unavailable', 'Original registered ASR journal required', 503)
        return journal

    def _read_final_assembly(self, row, binding):
        from video_creator.application.bundles import strict_json
        with self.engine.db.connect_readonly() as connection:
            stored = connection.execute('SELECT value FROM metadata WHERE key=?', (ASSEMBLY_PREFIX + row['id'],)).fetchone()
        if stored is None:
            return None
        try:
            body = strict_json(stored[0].encode('utf-8'))
            if set(body) != {'format', 'binding', 'ref'} or body['format'] != 'current-final-assembly-binding-v1':
                raise ValueError('shape')
            ref = AssemblyContextRef.model_validate(body['ref'])
            if body['binding'] != binding.model_dump(mode='json'):
                raise ValueError('binding')
        except (ValueError, TypeError, ValidationError):
            raise EngineError('final_assembly_invalid', 'Original committed assembly binding damaged', 422) from None
        if (ref.preparation_id, ref.preparation_intent_sha256) != (row['id'], digest(row['intent_json'])):
            raise EngineError('final_assembly_invalid', 'Assembly changed original preparation', 422)
        path = self._file('CurrentFinalAssemblies', 'assembly-' + ref.content_sha256)
        if not path.is_file():
            raise EngineError('final_assembly_unavailable', 'Committed assembly file missing', 503)
        raw = path.read_bytes()
        if (len(raw), hashlib.sha256(raw).hexdigest()) != (ref.size, ref.content_sha256):
            raise EngineError('final_assembly_invalid', 'Original assembly complete file changed', 422)
        try:
            data = strict_json(raw)
            model = (local.LocalFinalAssemblyContextV1 if data.get('format') == 'local-final-assembly-context-v1'
                     else CurrentFinalAssemblyContextV2 if data.get('format') == 'current-final-assembly-context-v2'
                     else CurrentFinalAssemblyContext)
            # Committed bytes are JSON; a strict dict parse would reject their
            # arrays for every tuple field. Read through the JSON entry point.
            context = model.model_validate_json(raw)
        except (ValidationError, EngineError, TypeError, ValueError):
            raise EngineError('final_assembly_invalid', 'Original assembly schema damaged', 422) from None
        if raw != (canonical(context) + '\n').encode() or context.binding != binding or context.preparation_id != row['id'] or context.preparation_intent_sha256 != ref.preparation_intent_sha256:
            raise EngineError('final_assembly_invalid', 'Original assembly bytes and scope differ', 422)
        return context

    def _validate_final_assembly_facts(self, lease, row, intent, binding, context, *, author, allow_missing_asr=False):
        if type(context) is local.LocalFinalAssemblyContextV1:
            from video_creator.application.local_bundle_assembly import (
                validate_local_assembly,
            )
            return validate_local_assembly(self, lease, row, intent, binding, context, author=author)
        from video_creator.application.bundles import validate_text
        # A genuine initial preparation has no final transcript receipt yet.
        # Its ASR and source assembly are validated by the dedicated held path.
        with self.engine.db.connect_readonly() as connection:
            speech = connection.execute('SELECT status FROM bundle_items WHERE preparation_id=? AND relative_path IN (?,?,?,?,?)',
                (row['id'], 'Text/actual-transcript.json', 'Text/subtitles.srt', 'Text/subtitles.vtt',
                 'Semantics/semantic-segments.jsonl', 'Semantics/rag-chunks.jsonl')).fetchall()
            registered = connection.execute('SELECT 1 FROM metadata WHERE key=?', ('current_initial_alignment:' + row['id'],)).fetchone()
        # Source authoring precedes CTC for an admitted initial or selected
        # changed-audio child. Partial recovery is only for its already
        # registered actual CTC; it does not certify missing final documents.
        ready = sum(item['status'] == 'ready' for item in speech)
        if (len(speech) == 5 and ready < 5 and (ready == 0 or (not author and registered is not None))
                and getattr(self, '_production_services_runtime', None) is not None):
            return self._initial_assembly_facts(lease, row, intent, binding, context, author=author)
        if (context.binding != binding or context.preparation_id != row['id']
                or context.preparation_intent_sha256 != digest(row['intent_json'])
                or (author and context.authored_fence != lease.fencing_token)):
            raise EngineError('final_assembly_binding_invalid', 'Original author/preparation/binding required', 409)
        slots = {slot.artifact_id: slot for slot in intent.material_slots}
        documents = context.document_artifact_ids
        if not {'insight', 'brief', 'plan', 'script', 'transcript', 'srt', 'vtt', 'summary', 'sources', 'shots', 'segments', 'rag', 'quality', 'audit'} <= set(documents) or not set(documents.values()) <= set(slots):
            raise EngineError('final_assembly_document_invalid', 'Complete original full-eight document allocation required', 422)
        # Extra evidence role names must describe an actual admitted evidence slot.
        parsed = {}
        prepared = self.recover_preparation(lease, row['id'])
        receipts = {r.artifact_id: r for r in prepared.materials}
        for role, artifact_id in documents.items():
            slot = slots[artifact_id]
            if role in DOCUMENT_PATHS:
                if slot.relative_path != DOCUMENT_PATHS[role]:
                    raise EngineError('final_assembly_document_invalid', 'Original document role/path changed', 422)
            elif not ((role.startswith('reference-source-') and role.removeprefix('reference-source-').isdigit()
                       and slot.schema_kind == 'audit_summary') or
                      (role.startswith('correction-copy-') and role.removeprefix('correction-copy-').isdigit()
                       and slot.schema_kind in {'precision_report', 'precision_report_v03', 'audit_summary', 'license'}
                       and slot.relative_path.startswith(('Checks/source-', 'License/source-')))):
                raise EngineError('final_assembly_document_invalid', 'Unknown document role', 422)
            if artifact_id in receipts:
                receipt = receipts[artifact_id]
                raw = self.read_material(lease, row['id'], receipt.material_id)
                parsed[role] = validate_text(raw, slot.schema_kind, slot.media_type)
            elif role not in {'quality', 'audit', 'policy', 'qualification', 'benchmark', 'work_validation', 'reference', 'measurement'}:
                raise EngineError('final_assembly_material_missing', 'Original ordinary documents must be READY before assembly commit', 409)
        transcript = parsed.get('transcript')
        if not isinstance(transcript, (c.ActualTranscriptDocument, c.ActualTranscriptDocumentV03)):
            raise EngineError('final_assembly_document_invalid', 'Actual original transcript required', 422)
        if (transcript.subtitles.timeline_duration_us != context.timeline_duration_us
                or transcript.subtitles.srt_artifact_id != documents['srt']
                or transcript.subtitles.vtt_artifact_id != documents['vtt']
                or len(context.audio_mappings) != 1
                or context.audio_mappings[0].mapping_revision_id != transcript.subtitles.mapping_revision_id):
            raise EngineError('final_assembly_mapping_invalid', 'Original subtitle/mapping identities differ', 422)
        if (context.manifest_created_at_us < row['created_at_us'] or context.manifest_created_at_us > self.engine.clock()
                or parsed['sources'].source_refs != context.source_refs
                or parsed['summary'].source_refs != context.source_refs
                or parsed['script'].script_revision_ref not in context.creative_revision_refs):
            raise EngineError('final_assembly_source_invalid', 'Original clock/source/script facts differ', 422)
        if {a.asset_id for a in context.media_artifacts} != set(intent.media_asset_ids) or {tuple(a.roles) for a in context.media_artifacts} != {('video',), ('narration_audio',), ('mixed_audio',), ('cover',)}:
            raise EngineError('final_assembly_media_invalid', 'Exactly original four master roles required', 422)
        masters = self.resolve_preparation_masters(lease, row['id'])
        if any(masters[a.roles[0]].asset_id != a.asset_id for a in context.media_artifacts):
            raise EngineError('final_assembly_media_invalid', 'Assembly changed authenticated preparation masters', 422)
        for artifact in context.media_artifacts:
            asset = self.asset(lease, artifact.asset_id)
            path = self.content_path(lease, artifact.asset_id)
            if (artifact.sha256, artifact.size, artifact.media_type) != (asset.sha256, asset.size, asset.media_type) or self.assets._hash(path) != asset.sha256:
                raise EngineError('final_assembly_media_invalid', 'Original full media identity differs', 422)
            actual = self.validators.media_validator(path, asset.media_type) if self.validators.media_validator else None
            if actual is None or artifact.spec is None or (artifact.spec.duration_us, artifact.spec.width, artifact.spec.height) != (actual.duration_us, actual.width, actual.height):
                raise EngineError('final_assembly_media_invalid', 'Original real decoded media specs required', 422)
        creative = {r.revision_id: r for r in self.creative_revisions(lease)}
        for ref in (*context.creative_revision_refs, context.quality_ref):
            revision = creative.get(ref.revision_id)
            if revision is None or (revision.kind, digest(canonical(revision))) != (ref.kind, ref.content_sha256):
                raise EngineError('final_assembly_revision_invalid', 'Actual original creative revision required', 422)
        if any(ref not in self.approval_refs(lease) for ref in context.approval_refs) or any(ref not in self.feedback_refs(lease) for ref in context.feedback_revision_refs):
            raise EngineError('final_assembly_revision_invalid', 'Actual original approval/feedback source required', 422)
        asr = self._original_asr().read_settled_original_asr(lease, context.asr_operation_id)
        if asr is None:
            if allow_missing_asr:
                return None
            raise EngineError('asr_recovery_validation_unavailable', 'Original committed ASR context required before assembly', 503)
        if (asr.observation.result_json['input_audio_sha256'] != transcript.transcript.input_audio_sha256
                or asr.observation.result_json['text'] != transcript.transcript.text):
            raise EngineError('final_assembly_asr_invalid', 'Original transcript does not retain original settled ASR', 422)
        methods = [m for m in context.methods if context.asr_operation_id in m.operation_ids]
        runtime = asr.observation.result_json['runtime']
        if (len(methods) != 1 or methods[0].method_id != transcript.transcript.method_ref
                or methods[0].config_sha256 != asr.input_sha256
                or methods[0].tool_version != runtime['versions']['faster-whisper']
                or methods[0].resource_manifest_sha256 != asr.context_ref.resource_manifest_sha256):
            raise EngineError('final_assembly_asr_invalid', 'Original ASR method versions/config/Operation differ', 422)
        if self.audio_clock_authority is None:
            raise EngineError('audio_clock_unavailable', 'Original real audio-clock verifier required', 503)
        for mapping in context.audio_mappings:
            target = self.content_path(lease, mapping.target_video_asset_id)
            if not self.audio_clock_authority(mapping.target_track, target):
                raise EngineError('final_assembly_mapping_invalid', 'Original target sample-clock facts differ', 422)
            for piece in mapping.pieces:
                source = self.content_path(lease, piece.source_track.asset_id)
                if not self.audio_clock_authority(piece.source_track, source):
                    raise EngineError('final_assembly_mapping_invalid', 'Original source sample-clock facts differ', 422)
        self.assert_current_correction_pair(lease, row['id'], context=context)
        return asr

    @staticmethod
    def _same_assembly_newer_fence(actual, context, lease) -> bool:
        """The same immutable authoring context re-entered under a later lease.

        Only `authored_fence` may differ; the persisted fence must belong to an
        earlier attempt of this exact run (`<=` current fence), and every other
        field is compared exactly. This is attempt re-entry evidence, never a
        new authored context.
        """
        return (type(actual) is type(context)
                and actual.binding == context.binding
                and actual.binding.run_id == lease.run_id
                and actual.authored_fence <= lease.fencing_token
                and actual.model_copy(update={'authored_fence': context.authored_fence}) == context)

    @staticmethod
    def _context_field_diff(actual, context):
        """Field-level, bounded diagnostic; it never widens the refusal."""
        def bounded(value):
            text = repr(value)
            return text if len(text) <= 120 else text[:117] + '...'

        names = sorted(set(actual.model_fields) | set(context.model_fields))
        differences = {}
        for name in names:
            left = getattr(actual, name, None)
            right = getattr(context, name, None)
            if left != right or type(left) is not type(right):
                differences[name] = {
                    'actual_type': type(left).__name__, 'expected_type': type(right).__name__,
                    'actual': bounded(left), 'expected': bounded(right),
                }
        return differences

    def assert_current_correction_pair(self, lease, preparation_id, *, context=None):
        """One current immutable v2 author/READY measurement rule, including publish."""
        from video_creator.application.bundles import validate_text
        with self.engine.db.connect_readonly() as connection:
            row, _run, _production, _request = self._preparation(connection, lease, preparation_id)
            saved = connection.execute('SELECT value FROM metadata WHERE key=?', (ASSEMBLY_PREFIX + preparation_id,)).fetchone()
            reports = connection.execute('SELECT * FROM bundle_items WHERE preparation_id=? AND relative_path=? AND status=?',
                (preparation_id, 'Checks/precision-evaluation.json', 'ready')).fetchall()
            binding = self._final_binding(lease, connection) if saved is not None else None
        actual = self._read_final_assembly(row, binding) if saved is not None else None
        if (actual is not None and context is not None and actual != context
                and not self._same_assembly_newer_fence(actual, context, lease)):
            differences = self._context_field_diff(actual, context)
            names = list(differences)[:5]
            print(json.dumps({
                'event': 'correction_context_diff',
                'preparation_id': preparation_id, 'run_id': lease.run_id,
                'actual_fence': actual.authored_fence,
                'expected_fence': context.authored_fence,
                'fields': dict(list(differences.items())[:20]),
            }, ensure_ascii=False, sort_keys=True), file=sys.stderr, flush=True)
            raise EngineError('correction_context_conflict',
                              'Original immutable author context differs; differs=' + ','.join(names), 422)
        authored = actual if actual is not None else context
        if len(reports) > 1:
            raise EngineError('correction_context_conflict', 'One original current measurement required', 422)
        source_rows = []
        for report in reports:
            raw = self.read_material(lease, preparation_id, report['material_id'])
            measurement = validate_text(raw, report['schema_kind'], report['media_type'])
            if isinstance(authored, CurrentFinalAssemblyContextV2) and (not isinstance(measurement, c.PrecisionEvaluationReportV03)
                    or (measurement.corrected_from, measurement.correction_reason) != (authored.corrected_from, authored.correction_reason)):
                raise EngineError('correction_context_conflict', 'Current READY measurement differs from original authored correction pair', 422)
            source_rows.append((report['material_id'], report['sha256'], report['size']))
        return (saved[0] if saved is not None else None, tuple(source_rows))

    @staticmethod
    def assert_correction_pair_writer(connection, preparation_id, observed, *, allow_new_assembly=_NO_NEW_ASSEMBLY):
        saved = connection.execute('SELECT value FROM metadata WHERE key=?', (ASSEMBLY_PREFIX + preparation_id,)).fetchone()
        actual = saved[0] if saved is not None else None
        allowed_first_binding = (observed[0] is None and type(allow_new_assembly) is str
                                 and actual == allow_new_assembly)
        if actual != observed[0] and not allowed_first_binding:
            raise EngineError('correction_context_conflict', 'Original author context changed at writer boundary', 409)
        rows = tuple((row['material_id'], row['sha256'], row['size']) for row in connection.execute(
            'SELECT material_id,sha256,size FROM bundle_items WHERE preparation_id=? AND relative_path=? AND status=?',
            (preparation_id, 'Checks/precision-evaluation.json', 'ready')))
        if rows != observed[1]:
            raise EngineError('correction_context_conflict', 'Original READY measurement changed at writer boundary', 409)

    def _assembly_correction_context(self, lease, preparation_id, context):
        """Reacquire the actual selected original and every licensed immutable copy."""
        if not isinstance(context, CurrentFinalAssemblyContextV2) or context.corrected_from is None:
            return None
        fact = self.correction_origin_evidence(lease, context.corrected_from)
        prepared = self.recover_preparation(lease, preparation_id)
        copies = {receipt.artifact_id: receipt for receipt in prepared.materials}
        sources = {}
        for source in (*(item.source for item in fact.reports), *fact.license_documents,
                       *(edge.indexed_child for edge in fact.dependency_edges)):
            artifact = source.artifact
            receipt = copies.get(artifact.artifact_id)
            if (receipt is None or (receipt.sha256, receipt.size, receipt.media_type, receipt.schema_kind) !=
                    (artifact.sha256, artifact.size, artifact.media_type, source.schema_kind)
                    or self.read_material(lease, preparation_id, receipt.material_id) != source.content.path.read_bytes()):
                raise EngineError('correction_origin_integrity_failed', 'Assembly requires each exact original READY correction copy', 422)
            sources[artifact.artifact_id] = artifact
        declared = {identity for role, identity in context.document_artifact_ids.items() if role.startswith('correction-copy-')}
        if declared != set(sources):
            raise EngineError('correction_origin_integrity_failed', 'Saved correction copy plan differs from complete original closure', 422)
        rights = self.verify_rights_evidence(lease, preparation_id, rights=context.rights,
            approval_refs=context.approval_refs, creative_revision_refs=context.creative_revision_refs,
            artifacts=(*context.media_artifacts, *sources.values()), required_uses=fact.required_uses)
        self._origin_files_current(lease, rights.context)
        return rights.context

    def persist_current_final_assembly_context(self, lease, preparation_id, context):
        local_snapshot = None
        if type(context) is local.LocalFinalAssemblyContextV1:
            with self._lock:
                held_context = getattr(self, '_local_preparation_contexts', {}).get(preparation_id)
            if held_context is None:
                raise EngineError('local_preparation_context_missing', 'Original controlled local preparation is required.', 409)
            local_snapshot = self._local_source().context_snapshot(lease, held_context)
        row, _production, _request, binding, _prepared, intent, _items = self._final_prepared(lease, preparation_id)
        # The author check is about this attempt's current writer lease; a
        # re-entry deliberately keeps the committed earlier fence for byte
        # identity, while every other context field is still current.
        author_context = context.model_copy(update={'authored_fence': lease.fencing_token})
        self._validate_final_assembly_facts(lease, row, intent, binding, author_context, author=True)
        correction_context = self._assembly_correction_context(lease, preparation_id, context)
        correction_pair = self.assert_current_correction_pair(lease, preparation_id, context=context)
        saved_context = self._read_final_assembly(row, binding)
        if saved_context is not None and self._same_assembly_newer_fence(saved_context, context, lease):
            # The same immutable assembly was committed by an earlier attempt
            # of this run before its journal; a later lease re-enters it. Keep
            # the committed bytes untouched and return their original Ref.
            saved_raw = (canonical(saved_context) + '\n').encode('utf-8')
            ref = AssemblyContextRef(preparation_id=preparation_id,
                preparation_intent_sha256=digest(row['intent_json']),
                content_sha256=hashlib.sha256(saved_raw).hexdigest(), size=len(saved_raw))
            with self.engine.db.transaction() as connection:
                self.engine._lease(connection, lease)
                if self._final_binding(lease, connection) != binding:
                    raise EngineError('final_assembly_binding_invalid',
                                      'Original assembly author binding changed during re-entry', 409)
                run = self.engine._run(connection, lease.run_id)
                self.engine._event(connection, run, 'production.final_assembly_reentry',
                                   ref.content_sha256)
            return ref
        raw = (canonical(context) + '\n').encode('utf-8')
        ref = AssemblyContextRef(preparation_id=preparation_id, preparation_intent_sha256=digest(row['intent_json']),
            content_sha256=hashlib.sha256(raw).hexdigest(), size=len(raw))
        self._write('CurrentFinalAssemblies', 'assembly-' + ref.content_sha256, raw)
        body = canonical_body({'format': 'current-final-assembly-binding-v1', 'binding': binding, 'ref': ref})
        key = ASSEMBLY_PREFIX + preparation_id
        issuer = self._production_authorization.issuer()
        with issuer.current_guard(self._production_authorization.registered(lease)) as guard, self.engine.db.transaction() as connection:
            current, run, production, _request = self._preparation(connection, lease, preparation_id)
            if local_snapshot is not None:
                self._local_source().assert_context_writer(connection, lease, local_snapshot)
            self.assert_correction_pair_writer(connection, preparation_id, correction_pair)
            issuer._guard(connection, guard)
            if correction_context is not None:
                self._origin_bindings_current(connection, lease, production, correction_context, guard=guard)
            if self._final_binding(lease, connection) != binding or current['intent_json'] != row['intent_json']:
                raise EngineError('final_assembly_binding_invalid', 'Original author writer changed preparation', 409)
            old = connection.execute('SELECT value FROM metadata WHERE key=?', (key,)).fetchone()
            if old and old[0] != body:
                raise EngineError('final_assembly_conflict', 'Original assembly bytes immutable', 409)
            if old is None:
                connection.execute('INSERT INTO metadata(key,value) VALUES(?,?)', (key, body))
                self.engine._event(connection, run, 'production.final_assembly_committed', ref.content_sha256)
            self._final_binding(lease, connection)
            self.assert_correction_pair_writer(connection, preparation_id, correction_pair, allow_new_assembly=body)
            if local_snapshot is not None:
                self._local_source().assert_context_writer(connection, lease, local_snapshot)
            if correction_context is not None:
                self._origin_bindings_current(connection, lease, production, correction_context, guard=guard)
            issuer._guard(connection, guard)
        return ref

    def read_current_final_continuation_inputs(self, lease, continuation):
        issuer = self._production_authorization.issuer()
        with issuer.current_guard(self._production_authorization.registered(lease)) as guard:
            return self._read_current_final_continuation_inputs(lease, continuation, guard)

    def _read_current_final_continuation_inputs(self, lease, continuation, guard, *, selected_preparation_id=None):
        with self.engine.db.connect_readonly() as connection:
            self.engine._lease(connection, lease)
            binding = self._final_binding(lease, connection)
            self._production_authorization.issuer()._guard(connection, guard)
            stored = connection.execute('SELECT value FROM metadata WHERE key=?', (PREFIX + lease.run_id,)).fetchone()
            if stored is None:
                raise EngineError('final_evidence_claim_required', 'Original executing checkpoint required', 409)
            journal = parse_journal(stored[0], now=self.engine.clock())
            row, _run, _production, _request = prepared_current(self.engine, connection, journal)
            if (binding != continuation.binding or journal.binding != binding or journal.snapshot != continuation.snapshot
                    or journal.control.phase != 'executing' or journal.control.execution_fence != lease.fencing_token
                    or continuation.execution_fence != lease.fencing_token or journal.control.resume_mode != continuation.resume_mode):
                raise EngineError('final_evidence_claim_required', 'Exact original current new-fence continuation required', 409)
            if selected_preparation_id is not None and selected_preparation_id != row['id']:
                row = self._selected_affected_child(connection, lease.run_id, journal, row, selected_preparation_id)
            intent = BundlePreparationIntent.model_validate_json(row['intent_json'])
        self.resolve_preparation_masters(lease, row['id'])
        preparation = self.recover_preparation(lease, row['id'])
        allocations = tuple(self.material_allocation(lease, row['id'], s.artifact_id) for s in intent.material_slots)
        materials = tuple((r, self.read_material(lease, row['id'], r.material_id)) for r in preparation.materials)
        saved_candidate = self._original_final_candidate(row, journal, binding)
        candidate = None if saved_candidate is None else saved_candidate[1:]
        manifest = None if saved_candidate is None else saved_candidate[0]
        assembly = self._read_final_assembly(row, binding)
        missing = []
        asr = None
        local_assembly = type(assembly) is local.LocalFinalAssemblyContextV1
        if assembly is None:
            if manifest is None:
                missing.append('original_assembly_context_missing')
        else:
            asr = final_read_set_asr(assembly, self._validate_final_assembly_facts(
                lease, row, intent, binding, assembly, author=False, allow_missing_asr=True))
            self._assembly_correction_context(lease, row['id'], assembly)
            if manifest is not None:
                fields = ('creative_revision_refs', 'approval_refs', 'feedback_revision_refs', 'source_refs',
                          'outputs', 'audio_mappings', 'rights', 'quality_ref', 'timeline_duration_us')
                if any(getattr(manifest, f) != getattr(assembly, f) for f in fields) or manifest.created_at_us != assembly.manifest_created_at_us or tuple(a for a in manifest.artifacts if a.asset_id) != assembly.media_artifacts:
                    raise EngineError('final_assembly_candidate_conflict', 'Candidate and original assembly disagree', 422)
                if manifest.methods != self.expected_initial_alignment_methods(lease, row['id'], assembly):
                    raise EngineError('final_assembly_candidate_conflict', 'Candidate methods differ from original source plus actual committed initial CTC', 422)
        if assembly is None and manifest is not None:
            from video_creator.application.bundles import validate_text
            actual_receipt = next((r for r, _raw in materials if r.schema_kind in {'actual_transcript', 'actual_transcript_v03'}), None)
            actual_bytes = next((raw for r, raw in materials if r == actual_receipt), None)
            if actual_receipt is None:
                raise EngineError('bundle_output_missing', 'Original candidate has no READY actual transcript', 422)
            actual = validate_text(actual_bytes, actual_receipt.schema_kind, actual_receipt.media_type)
            methods = [m for m in manifest.methods if m.method_id == actual.transcript.method_ref]
            if len(methods) != 1 or len(methods[0].operation_ids) != 1:
                raise EngineError('asr_result_scope_denied', 'Original candidate must name its single original ASR Operation', 422)
            asr = self._original_asr().read_settled_original_asr(lease, methods[0].operation_ids[0])
        if asr is None and not local_assembly:
            # A local work's speech facts are the committed local document, not
            # a non-local ASR read; only a legacy assembly can miss that context.
            missing.append('original_asr_validation_context_missing')
        strict_kinds = {'precision_reference_v03', 'precision_report_v03', 'precision_report',
                        'method_benchmark_reference', 'method_benchmark', 'method_qualification',
                        'evidence_policy', 'work_alignment_validation', 'license'}
        strict_ids = {r.artifact_id for r, _raw in materials if r.schema_kind in strict_kinds}
        from video_creator.application.bundles import check_record, validate_text
        by_artifact = {r.artifact_id: (r, raw) for r, raw in materials}
        paths = {a.artifact_id: a.relative_path for a in allocations}
        documents = {paths[r.artifact_id]: validate_text(raw, r.schema_kind, r.media_type) for r, raw in materials}
        actual = documents.get('Text/actual-transcript.json')
        for receipt, raw in materials:
            if receipt.schema_kind != 'precision_reference_v03':
                continue
            reference = validate_text(raw, receipt.schema_kind, receipt.media_type)
            check_record(reference)
            if not isinstance(actual, c.ActualTranscriptDocumentV03):
                raise EngineError('precision_reference_source_missing', 'Original actual transcript required for source closure', 422)
            sources = {}
            for ref in (*reference.independent_listener_refs, reference.arbitration_ref):
                value = by_artifact.get(ref.artifact_id)
                if value is None:
                    missing.append('independent_reference_source_missing')
                    continue
                source, source_bytes = value
                if source.sha256 != ref.sha256 or source.schema_kind != 'audit_summary':
                    raise EngineError('precision_reference_source_invalid', 'Original full source receipt/grammar differs', 422)
                sources[ref.artifact_id] = (ref, source_bytes)
                strict_ids.add(ref.artifact_id)
            if len(sources) == len(reference.independent_listener_refs) + 1:
                self.engine.evidence_registry.verify_work_reference(reference, lease=lease, preparation_id=row['id'],
                    actual=actual, source_documents=sources)
        measurement = documents.get('Checks/precision-evaluation.json')
        if isinstance(measurement, c.PrecisionEvaluationReportV03):
            if isinstance(assembly, CurrentFinalAssemblyContextV2) and (
                    measurement.corrected_from != assembly.corrected_from or measurement.correction_reason != assembly.correction_reason):
                raise EngineError('correction_context_conflict', 'Immutable current report differs from original authored correction pair', 422)
            if measurement.corrected_from is not None:
                self.correction_origin_evidence(lease, measurement.corrected_from)
        elif (assembly is not None and not isinstance(assembly, CurrentFinalAssemblyContextV2)
              and manifest is None and any(role.startswith('correction-copy-') for role in assembly.document_artifact_ids)):
            missing.append('correction_recovery_context_required')
        if manifest is not None:
            artifacts = {a.artifact_id: a for a in manifest.artifacts}
            while True:
                expanded = strict_ids | {dependency for identity in strict_ids if identity in artifacts
                                         for dependency in artifacts[identity].dependency_artifact_ids}
                if expanded == strict_ids:
                    break
                strict_ids = expanded
            self._correction_closure(manifest, documents, lease=lease)
        strict_materials = tuple(value for value in materials if value[0].artifact_id in strict_ids)
        with self.engine.db.connect_readonly() as connection:
            self.engine._lease(connection, lease)
            saved = connection.execute('SELECT value FROM metadata WHERE key=?', (PREFIX + lease.run_id,)).fetchone()
            if self._final_binding(lease, connection) != binding or saved is None or saved[0] != stored[0]:
                raise EngineError('final_evidence_checkpoint_changed', 'Original read claim changed', 409)
            self._production_authorization.issuer()._guard(connection, guard)
        return CurrentFinalEvidenceReadSet(binding, lease.fencing_token, preparation, intent, allocations,
            materials, candidate, assembly, asr, strict_materials, tuple(dict.fromkeys(missing)))
