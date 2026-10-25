"""Local 0.4 final assembly validation on the original BundleService.

`LocalFinalAssemblyContextV1` is the local analogue of
`CurrentFinalAssemblyContextV2`: it is authored before a final-evidence
candidate exists, so it must already retain the same Run's approved plan and
quality versions, the actual applicable master selection, the committed
media-master Step outputs, the original Asset bytes and the committed local
speech evidence.

Nothing here fabricates a transcript, subtitles or silence: a missing material
is a named `EngineError`, never a pass. The returned object is the committed
`LocalSpeechEvidenceV1` (the local counterpart of the settled original ASR read
that the non-local branch returns), or None only when the caller explicitly
allows a missing standard evidence context.
"""

import json

from video_creator.application.engine import canonical, digest
from video_creator.domain import contracts as c
from video_creator.domain import local_bundle as local
from video_creator.domain.errors import EngineError
from video_creator.domain.local_material_production import parse_local_material_plan

SPEECH_PATH = 'Checks/local-speech-evidence.json'
TRANSCRIPT_PATH = 'Text/actual-transcript.json'
QUALITY_PATH = 'Checks/quality-report.json'
MASTER_PATHS = {'video': 'Media/video.mp4', 'narration_audio': 'Media/narration.wav',
                'mixed_audio': 'Media/mixed-audio.wav', 'cover': 'Media/cover.jpg'}
DOCUMENT_PATHS = {
    'plan': 'Creative/production-plan.json',
    'script': 'Text/approved-script.json',
    'quality': QUALITY_PATH,
    'selection': 'Checks/local-master-selection.json',
    'speech': SPEECH_PATH,
    'summary': 'Semantics/work-summary.json',
    'sources': 'Semantics/source-bindings.json',
    'segments': 'Semantics/semantic-segments.jsonl',
    'rag': 'Semantics/rag-chunks.jsonl',
    'shots': 'Semantics/shots.jsonl',
    'visual': 'Semantics/visual-mapping.json',
    'transcript': TRANSCRIPT_PATH,
    'srt': 'Text/subtitles.srt',
    'vtt': 'Text/subtitles.vtt',
}
VISUAL_PATHS = frozenset({'Semantics/shots.jsonl', 'Semantics/visual-mapping.json'})
FIXED_PATHS = frozenset(local.LOCAL_REQUIRED_FILES) | VISUAL_PATHS | {
    TRANSCRIPT_PATH, 'Text/subtitles.srt', 'Text/subtitles.vtt', 'Checks/assembly-audit.json'}
LATE_PATHS = frozenset({QUALITY_PATH, 'Checks/assembly-audit.json'})
EVIDENCE_KINDS = frozenset({
    'precision_report', 'precision_report_v03', 'precision_reference_v03', 'method_benchmark',
    'method_benchmark_reference', 'method_qualification', 'evidence_policy',
    'work_alignment_validation', 'license', 'audit_summary', 'production_authorization',
})


def _invalid(code: str, message: str, status_code: int = 422) -> EngineError:
    return EngineError(code, message, status_code)


class _LocalAssemblyCheck:
    """Ordered, fail-closed validation of one local final assembly context."""

    def __init__(self, service, lease, row, intent, binding, context, *, author, allow_missing_asr):
        self.service, self.lease, self.row = service, lease, row
        self.intent, self.binding, self.context = intent, binding, context
        self.author, self.allow_missing_asr = author, allow_missing_asr
        self.production = self.request = self.plan = self.plan_ref = None
        self.selection = self.committed = self.slots = self.documents = None

    def validate(self):
        self._scope()
        self._revisions()
        self._selection()
        self._masters()
        speech = self._speech()
        self._speech_relations(speech)
        self._documents()
        return speech

    # -- original same-Run scope -------------------------------------------------

    def _scope(self):
        from video_creator.application.current_production_blockers import bound_context

        context = self.context
        if type(context) is not local.LocalFinalAssemblyContextV1:
            raise _invalid('local_assembly_context_invalid',
                           'Only the sole local final assembly context is admitted')
        if (context.binding != self.binding or context.preparation_id != self.row['id']
                or context.preparation_intent_sha256 != digest(self.row['intent_json'])
                or canonical(self.intent) != self.row['intent_json']
                or context.timeline_duration_us <= 0):
            raise _invalid('local_assembly_binding_invalid',
                           'Assembly retains a different preparation, intent or binding', 409)
        if self.author and context.authored_fence != self.lease.fencing_token:
            raise _invalid('local_assembly_binding_invalid',
                           'Only the authoring fence may commit this assembly', 409)
        with self.service.engine.db.connect_readonly() as connection:
            run, production, request, actual = bound_context(
                self.service.engine, connection, self.lease.run_id,
                self.binding.registration_sha256)
        if actual != self.binding or run['id'] != self.lease.run_id:
            raise _invalid('local_assembly_binding_invalid',
                           'Assembly binding differs from the original committed execution binding', 409)
        if production['request_revision_id'] != self.intent.request_revision_id:
            raise _invalid('local_assembly_intent_conflict',
                           'Preparation intent belongs to another request revision', 409)
        if not self.row['created_at_us'] <= context.manifest_created_at_us <= self.service.engine.clock():
            raise _invalid('local_assembly_clock_invalid',
                           'Assembly authoring time must be inside this preparation and the current clock')
        self.production, self.request = production, request

    # -- committed creative versions --------------------------------------------

    def _creative(self, revision_ref, role):
        with self.service.engine.db.connect_readonly() as connection:
            row = connection.execute(
                'SELECT * FROM creative_revisions WHERE id=? AND production_id=? AND run_id=?',
                (revision_ref.revision_id, self.production['id'], self.lease.run_id)).fetchone()
        if (row is None or row['kind'] != revision_ref.kind
                or row['content_sha256'] != revision_ref.content_sha256
                or digest(row['body']) != revision_ref.content_sha256):
            raise _invalid('local_assembly_revision_invalid',
                           f'Assembly {role} version is not this Run\'s actual immutable revision', 422)
        revision = c.CreativeRevision.model_validate_json(row['body'])
        if (revision.revision_id, revision.kind) != (revision_ref.revision_id, revision_ref.kind):
            raise _invalid('local_assembly_revision_invalid',
                           f'Assembly {role} row and typed body differ', 422)
        return revision

    def _revisions(self):
        context = self.context
        if len({ref.revision_id for ref in context.creative_revision_refs}) != len(context.creative_revision_refs):
            raise _invalid('local_assembly_revision_invalid',
                           'Assembly creative versions must be distinct')
        for ref in context.creative_revision_refs:
            self._creative(ref, 'creative')
        plan_ref = context.selection.plan_revision_ref
        if plan_ref.kind != 'plan':
            raise _invalid('local_assembly_plan_invalid', 'Selection must retain the approved plan')
        plan_revision = self._creative(plan_ref, 'plan')
        self._creative(context.quality_ref, 'quality')
        try:
            plan = parse_local_material_plan(
                json.dumps(plan_revision.body, ensure_ascii=False,
                           separators=(',', ':')).encode('utf-8'))
        except (EngineError, TypeError) as error:
            raise _invalid('local_assembly_plan_invalid',
                           'The approved plan body is not the actual local plan document') from error
        if plan.request_ref != local.LocalProductionRequestRef(
                instance_id=self.binding.instance_id, production_id=self.binding.production_id,
                run_id=self.binding.run_id, request_revision_id=self.binding.request_revision_id,
                request_sha256=self.binding.request_sha256):
            raise _invalid('local_assembly_plan_invalid',
                           'Plan retains a different original request identity', 409)
        if plan.timeline.duration_us != context.timeline_duration_us:
            raise _invalid('local_assembly_timeline_conflict',
                           'Assembly timeline duration differs from the approved plan', 409)
        self.plan, self.plan_ref = plan, plan_ref

    def _selection(self):
        context = self.context
        if type(context.selection) is not local.LocalMasterSelectionV1:
            raise _invalid('local_assembly_selection_invalid',
                           'Only the sole actual local master selection is admitted')
        expected = local.select_local_masters(self.request, self.plan, self.plan_ref)
        if expected != context.selection:
            raise _invalid('local_assembly_selection_conflict',
                           'Selection differs from the actual approved plan and request', 409)
        self.selection = expected

    # -- actual committed masters ------------------------------------------------

    def _committed_masters(self, selection):
        """The already committed `media-master` Step, without any live held context.

        `RegisteredMediaRuntime.master_assets(selection=...)` first proves a held
        in-process `final_context`; a restarted process cannot have one, so the
        validator reads the committed Step (and its settled Operations) directly
        and compares it with `selection.master_roles`. Every Asset byte and its
        real decoded spec are still re-verified by `_master` below.
        """
        from video_creator.application.bundles import strict_json

        step = self.service.engine.read_step(self.lease, 'media-master')
        if step is None or step['status'] != 'succeeded' or type(step['result_json']) is not str:
            raise _invalid('production_media_capability_missing',
                           'Upstream media-master Step must commit before the final assembly', 503)
        body = strict_json(step['result_json'].encode('utf-8'))
        result = body.get('result') if isinstance(body, dict) else None
        roles = result.get('media_roles') if isinstance(result, dict) else None
        required = set(selection.master_roles)
        if (not isinstance(roles, dict) or set(roles) != required
                or any(type(value) is not str for value in roles.values())
                or len(set(roles.values())) != len(required)):
            raise _invalid('local_assembly_master_conflict',
                           'Committed media-master roles differ from the applicable selection', 409)
        # The committed Step body keeps `asset_ids` at the top level (the media
        # side's `_outputs()` reads `saved['asset_ids']` there); only the role
        # map lives under `result`. A Step row may also carry `asset_ids`.
        committed = body.get('asset_ids') if isinstance(body, dict) else None
        if committed is None:
            committed = step.get('asset_ids')
        if (not isinstance(committed, list) or len(set(committed)) != len(committed)
                or set(committed) != set(roles.values())):
            raise _invalid('local_assembly_master_conflict',
                           'Committed media-master assets must be its distinct role outputs', 409)
        with self.service.engine.db.connect_readonly() as connection:
            operations = connection.execute(
                "SELECT status,settled FROM operations WHERE run_id=? AND step_key='media-master'",
                (self.lease.run_id,)).fetchall()
        if any(not row['settled'] or row['status'] in {'submitting', 'pending', 'unknown'}
               for row in operations):
            raise _invalid('media_master_evidence_pending',
                           'Original media-master Operations require reconciliation', 409)
        if not operations or any(row['status'] != 'succeeded' for row in operations):
            raise _invalid('media_master_evidence_missing',
                           'Actual media-master requires its successful settled Operations', 409)
        for role, identifier in roles.items():
            record = self.service.asset(self.lease, identifier)
            if (not record.probe.decoded or role == 'video' and not record.probe.has_video
                    or role in {'narration_audio', 'mixed_audio'} and not record.probe.has_audio
                    or role == 'cover' and not record.media_type.startswith('image/')):
                raise _invalid('local_assembly_master_changed',
                               'Committed media does not satisfy its original output role')
        return {role: roles[role] for role in selection.master_roles}

    def _masters(self):
        selection = self.selection
        self.slots = {slot.artifact_id: slot for slot in self.intent.material_slots}
        committed = self._committed_masters(selection)
        if set(committed) != set(selection.master_roles):
            raise _invalid('local_assembly_master_conflict',
                           'Committed media-master roles differ from the applicable selection', 409)
        ordered = tuple(committed[role] for role in selection.master_roles)
        if tuple(artifact.asset_id for artifact in self.context.media_artifacts) != ordered:
            raise _invalid('local_assembly_master_conflict',
                           'Assembly masters differ from the actual committed media-master outputs', 409)
        if (len(set(self.intent.media_asset_ids)) != len(self.intent.media_asset_ids)
                or set(self.intent.media_asset_ids) != set(ordered)):
            raise _invalid('local_assembly_master_conflict',
                           'Preparation intent does not retain exactly the selected masters', 409)
        for artifact in self.context.media_artifacts:
            self._master(artifact)
        self.committed = committed

    def _master(self, artifact):
        role = artifact.roles[0]
        if artifact.relative_path != MASTER_PATHS[role]:
            raise _invalid('local_assembly_master_path_invalid',
                           'Each actual master keeps its fixed local relative path')
        asset = self.service.asset(self.lease, artifact.asset_id)
        path = self.service.content_path(self.lease, artifact.asset_id)
        if ((artifact.sha256, artifact.size, artifact.media_type)
                != (asset.sha256, asset.size, asset.media_type)
                or self.service.assets._hash(path) != asset.sha256):
            raise _invalid('local_assembly_master_changed',
                           'Assembly master differs from the original Asset bytes')
        if self.service.validators.media_validator is None:
            raise _invalid('local_assembly_decoder_missing',
                           'Assembly requires the actual configured media decoder', 503)
        actual = self.service.validators.media_validator(path, asset.media_type)
        spec = artifact.spec
        if (spec.duration_us, spec.width, spec.height) != (
                actual.duration_us, actual.width, actual.height):
            raise _invalid('local_assembly_master_changed',
                           'Assembly master spec differs from the actual decoded media')

    # -- committed local speech evidence -----------------------------------------

    def _speech_row(self):
        with self.service.engine.db.connect_readonly() as connection:
            item = connection.execute(
                'SELECT * FROM bundle_items WHERE preparation_id=? AND relative_path=?',
                (self.row['id'], SPEECH_PATH)).fetchone()
        if item is None or item['material_id'] is None or item['status'] != 'ready':
            return None
        if item['schema_kind'] != 'local_speech_evidence' or item['media_type'] != 'application/json':
            raise _invalid('local_assembly_speech_invalid',
                           'The committed speech slot is not the local speech evidence document')
        return item

    def _speech(self):
        item = self._speech_row()
        if item is None:
            if self.allow_missing_asr:
                return None
            raise _invalid('local_assembly_speech_missing',
                           'Committed local speech evidence is required before final assembly', 409)
        if item['artifact_id'] not in set(self.context.document_artifact_ids.values()):
            raise _invalid('local_assembly_document_invalid',
                           'Assembly must index the committed speech evidence artifact')
        raw = self.service.read_material(self.lease, self.row['id'], item['material_id'])
        from video_creator.application.bundles import validate_text

        speech = validate_text(raw, item['schema_kind'], item['media_type'])
        if type(speech) is not local.LocalSpeechEvidenceV1:
            raise _invalid('local_assembly_speech_invalid',
                           'The committed speech evidence is not its actual typed document')
        return speech

    def _speech_relations(self, speech):
        context, selection = self.context, self.selection
        if speech is None:
            return
        methods = {value.method_id for value in context.methods}
        indexed = set(context.document_artifact_ids.values()) | {
            artifact.artifact_id for artifact in context.media_artifacts}
        if (not methods or len(methods) != len(context.methods)
                or not set(speech.method_refs) <= methods
                or not set(speech.proof_artifact_ids) <= indexed
                or len(set(speech.proof_artifact_ids)) != len(speech.proof_artifact_ids)):
            raise _invalid('local_assembly_speech_invalid',
                           'Speech evidence methods and proofs must be this assembly\'s actual indexes')
        audio_roles = {'mixed_audio', 'narration_audio'} & set(selection.master_roles)
        if speech.state == 'no_audio_observed':
            if (audio_roles or self.plan.timeline.audio_tracks or context.audio_mappings
                    or context.asr_operation_id is not None
                    or self._has_path(TRANSCRIPT_PATH)):
                raise _invalid('local_assembly_audio_absence_invalid',
                               'No-audio evidence cannot keep audio masters, mappings, ASR or a transcript', 409)
            video = self.committed.get('video')
            if video is None:
                raise _invalid('local_assembly_audio_absence_invalid',
                               'No-audio evidence requires the actual silent visual master', 409)
            probe = self.service.asset(self.lease, video).probe
            if (not probe.decoded or not probe.has_video or probe.has_audio
                    or probe.duration_us != self.context.timeline_duration_us):
                raise _invalid('local_assembly_audio_absence_invalid',
                               'The actual final video must decode as a silent visual master of the approved duration')
        else:
            if not audio_roles or context.asr_operation_id is None or not context.audio_mappings:
                raise _invalid('local_assembly_mapping_invalid',
                               'Speech-bearing assembly requires the actual mixed audio, ASR operation and mappings', 409)
            if not self._has_path(TRANSCRIPT_PATH):
                raise _invalid('local_assembly_document_invalid',
                               'Speech-bearing assembly requires the actual transcript material')
            asr = self.service._original_asr().read_settled_original_asr(
                self.lease, context.asr_operation_id)
            if asr is None:
                raise _invalid('local_assembly_asr_missing',
                               'Assembly requires the original settled ASR operation', 503)
        self._mappings()

    def _has_path(self, relative_path: str) -> bool:
        for artifact_id in self.context.document_artifact_ids.values():
            slot = self.slots.get(artifact_id)
            if slot is not None and slot.relative_path == relative_path:
                return True
        return False

    def _mappings(self):
        from video_creator.application.bundles import check_record

        context, committed = self.context, self.committed
        video = committed.get('video')
        pieces = set()
        for mapping in context.audio_mappings:
            check_record(mapping)
            if (video is None or mapping.target_video_asset_id != video
                    or mapping.timeline_duration_us != context.timeline_duration_us):
                raise _invalid('local_assembly_mapping_invalid',
                               'Each mapping targets the actual final work and timeline')
            for piece in mapping.pieces:
                record = self.service.asset(self.lease, piece.source_track.asset_id)
                if record.sha256 != piece.source_track.sha256:
                    raise _invalid('local_assembly_mapping_invalid',
                                   'Mapped source bytes differ from the original Asset')
                if self.service.audio_clock_authority is None:
                    raise _invalid('local_assembly_audio_clock_missing',
                                   'Assembly requires the actual sample/clock verifier', 503)
                if self.service.audio_clock_authority(
                        piece.source_track, self.service.content_path(self.lease, record.asset_id)) is not True:
                    raise _invalid('local_assembly_mapping_invalid',
                                   'The original sample clock rejects this mapping source')
                self.service._check_mapping_piece(piece)
                if piece.piece_id in pieces:
                    raise _invalid('local_assembly_mapping_invalid',
                                   'Mapping piece identities must be globally unique')
                pieces.add(piece.piece_id)

    # -- allocated documents -----------------------------------------------------

    def _documents(self):
        context, slots = self.context, self.slots
        documents = context.document_artifact_ids
        if not set(documents.values()) <= set(slots) or len(set(documents.values())) != len(documents):
            raise _invalid('local_assembly_document_invalid',
                           'Every assembly document must be one distinct allocated slot')
        covered = {slots[artifact_id].relative_path for artifact_id in documents.values()}
        required = set(local.LOCAL_REQUIRED_FILES) | (
            VISUAL_PATHS if self.selection.content_kind == 'video' else set())
        if not required <= covered:
            raise _invalid('local_assembly_document_missing',
                           'Assembly must index every required local provenance material', 409)
        if self.selection.content_kind != 'video' and covered & VISUAL_PATHS:
            raise _invalid('local_assembly_document_invalid',
                           'Audio-only assembly cannot fabricate visual documents')
        prepared = self.service.recover_preparation(self.lease, self.row['id'])
        receipts = {receipt.artifact_id: receipt for receipt in prepared.materials}
        from video_creator.application.bundles import validate_text

        for role, artifact_id in documents.items():
            slot = slots[artifact_id]
            if role in DOCUMENT_PATHS and DOCUMENT_PATHS[role] != slot.relative_path:
                raise _invalid('local_assembly_document_invalid',
                               'A known document role keeps its fixed local relative path')
            if role not in DOCUMENT_PATHS and (slot.relative_path not in FIXED_PATHS
                                               and slot.schema_kind not in EVIDENCE_KINDS):
                raise _invalid('local_assembly_document_invalid',
                               'Unknown document role may only carry an admitted evidence kind')
            receipt = receipts.get(artifact_id)
            if receipt is None:
                if slot.relative_path in LATE_PATHS:
                    continue
                raise _invalid('local_assembly_document_missing',
                               'Every ordinary assembly document must be READY before commit', 409)
            validate_text(self.service.read_material(self.lease, self.row['id'], receipt.material_id),
                          slot.schema_kind, slot.media_type)


def validate_local_assembly(service, lease, row, intent, binding, context, *, author,
                            allow_missing_asr=False):
    """Validate this local assembly against the same Run's actual committed facts.

    Returns the committed `LocalSpeechEvidenceV1`, or None only when
    `allow_missing_asr` explicitly admits a not-yet-committed evidence context.
    """
    return _LocalAssemblyCheck(service, lease, row, intent, binding, context,
                               author=author, allow_missing_asr=allow_missing_asr).validate()
