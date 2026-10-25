"""Strict portable provenance and actual local publication-only capability."""

import hashlib
import json
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass

from video_creator.application.bundle_facts import (
    ProductionAuthorizationMaterialRef,
    SourcePolicyAuthorization,
)
from video_creator.application.engine import canonical, digest
from video_creator.domain import contracts as c
from video_creator.domain.bundle import MaterialReceipt
from video_creator.domain.daily_project_authorization import (
    ProductionAuthorizationDocumentV02,
)
from video_creator.domain.errors import EngineError
from video_creator.domain.local_material_production import plan_rights_body
from video_creator.domain.production_authorization import (
    ProductionAdmissionRef,
    ProductionAuthorizationDocument,
)

AUTHORIZATION_PATH = 'Checks/production-authorization.json'


def authorization_refs_body(refs):
    return [{'artifact': ref.artifact.model_dump(mode='json'), 'receipt': ref.receipt.model_dump(mode='json'),
             'document_sha256': digest(canonical(ref.document))} for ref in refs]


def source_policy_body(source):
    return {'format': 'local-source-policy-v1-adr0026',
            'bundle_ref': source.source_bundle_ref.model_dump(mode='json'),
            'authorization': authorization_refs_body((source.authorization,))[0],
            'plan_artifact': source.plan_artifact.model_dump(mode='json'),
            'plan_receipt': source.plan_receipt.model_dump(mode='json'),
            'observed_at_us': source.observed_at_us,
            'policy_current_at_read': source.policy_current_at_read,
            'policy_revoked_at_read': source.policy_revoked_at_read}


def validate_portable_authorization(manifest, documents):
    """Pure origin audit validation. Does not consult/install a local registry."""
    slots = [item for item in manifest.artifacts if 'production_authorization' in item.roles]
    if not slots:
        return ()
    if len(slots) != 1:
        raise EngineError('production_authorization_set_invalid', 'A complete origin has one exact indexed production authorization document', 422)
    item = slots[0]
    document = documents.get(item.relative_path)
    if (item.roles != ('production_authorization',) or item.relative_path != AUTHORIZATION_PATH
            or item.media_type != 'application/json' or not item.material_id
            or not isinstance(document, (ProductionAuthorizationDocument, ProductionAuthorizationDocumentV02))):
        raise EngineError('production_authorization_kind_invalid', 'Production authorization has its own exact role/path/MIME/schema', 422)
    fact, policy = document.plan_admission, document.policy
    if (fact.instance_id, fact.production_id, fact.run_id, fact.request_revision_id, fact.request_sha256) != (
            manifest.instance_id, manifest.production_id, manifest.run_id, manifest.request_revision_id, manifest.request_sha256):
        raise EngineError('production_authorization_origin_conflict', 'Portable authorization names a different original work/request', 422)
    plan_refs = [ref for ref in manifest.creative_revision_refs if ref.kind == 'plan'
                 and (ref.revision_id, ref.content_sha256) == (fact.target_id, fact.target_sha256)]
    plan = next((artifact for artifact in manifest.artifacts if artifact.relative_path == 'Creative/production-plan.json'), None)
    parsed_plan = documents.get('Creative/production-plan.json')
    if (len(plan_refs) != 1 or plan is None or plan.artifact_id not in item.dependency_artifact_ids
            or not isinstance(parsed_plan, c.CreativeRevision) or parsed_plan.kind != 'plan'
            or parsed_plan.revision_id != fact.target_id or digest(canonical(parsed_plan)) != fact.target_sha256
            or not isinstance(parsed_plan.body, dict) or plan_rights_body(parsed_plan.body) != [right.model_dump(mode='json') for right in policy.rights]):
        raise EngineError('production_authorization_plan_conflict', 'Portable authorization binds the actual indexed immutable plan and exact declaration', 422)
    rights_body = {'declaration_id': policy.rights_declaration_id, 'rights': [right.model_dump(mode='json') for right in policy.rights]}
    rights_sha = digest(json.dumps(rights_body, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False))
    action_scope = (document.owner_action.instance_id, document.owner_action.owner_subject) == (
        policy.instance_id, policy.owner_subject)
    if isinstance(document, ProductionAuthorizationDocumentV02):
        action_scope = action_scope and (document.source.child.project_id == manifest.project_id
            and document.source.receipt.production_id == manifest.production_id
            and document.source.receipt.request_revision_id == manifest.request_revision_id
            and document.source.receipt.request_sha256 == manifest.request_sha256
            and document.source.parent.authorization.instance_id == manifest.instance_id)
    else:
        action_scope = action_scope and document.owner_action.project_ids == policy.project_ids
    if (not action_scope
            or fact.rights_declaration_sha256 != rights_sha or manifest.project_id not in policy.project_ids
            or manifest.workflow_version != policy.workflow_version or manifest.timeline_duration_us > policy.max_duration_us
            or fact.executing_principal_id not in policy.executing_principal_ids
            or not policy.valid_from_us <= fact.checked_at_us < fact.valid_until_us <= policy.expires_at_us
            or not fact.checked_at_us <= manifest.created_at_us < policy.expires_at_us
            or 'execute_plan' not in policy.allowed_actions):
        raise EngineError('production_authorization_scope_conflict', 'Original plan/source scope and finite validity do not agree', 422)
    assertions = [right for right in manifest.rights if right.basis == 'user_asserted'
                  and right.approval_ref == policy.rights_declaration_id]
    if not assertions or any(right not in policy.rights for right in assertions):
        raise EngineError('production_authorization_rights_conflict', 'Portable provenance is only the exact original Owner assertion', 422)
    return (document,)


@dataclass(frozen=True, eq=False, repr=False)
class BundlePublicationScope:
    service: object
    lease: c.LeaseGrant
    verified: object
    manifest: c.BundleManifest
    final_context: object
    thread_id: int


class BundleProductionAuthorization:
    def __init__(self, bundle):
        self.bundle, self.engine = bundle, bundle.engine
        self._scopes = set()

    def issuer(self):
        issuer = getattr(self.engine, 'production_admissions', None)
        if issuer is None:
            raise EngineError('production_authorization_unconfigured', 'Actual local Owner policy execution is not installed', 403)
        return issuer

    def registered(self, lease):
        with self.engine.db.connect() as connection:
            run = self.engine._lease(connection, lease)
            production = self.engine._production(connection, run['production_id'])
        return self.engine._authorization_identity(production['owner'])

    def current_guard(self, lease):
        return self.issuer().current_guard(self.registered(lease))

    @contextmanager
    def guard_for(self, lease):
        with self.engine.db.connect() as connection:
            run = self.engine._lease(connection, lease)
            production = self.engine._production(connection, run['production_id'])
            unattended = c.parse_production_request(production['request_json']).automation.mode == 'unattended'
        if unattended:
            try:
                with self.current_guard(lease) as guard:
                    copy_service = getattr(self.engine, 'local_copy_inputs', None)
                    if copy_service is not None:
                        with copy_service.current_guard():
                            yield guard
                    else:
                        yield guard
            except EngineError as error:
                if error.code in {'production_copy_source_scope_missing', 'local_copy_scope_inactive',
                        'local_copy_policy_conflict', 'local_copy_source_scope_denied', 'local_copy_restore_refresh_required'}:
                    self.engine._suspend_operation_authorization(lease, error)
                raise
        else:
            yield None

    def refs_for_manifest(self, lease, manifest):
        with self.engine.db.connect() as connection:
            run = self.engine._lease(connection, lease)
            row = connection.execute('SELECT id FROM bundle_revisions WHERE revision_id=? AND run_id=? AND production_id=?',
                (manifest.bundle_revision_id, run['id'], run['production_id'])).fetchone()
        if not row:
            raise EngineError('production_authorization_preparation_missing', 'The actual local Manifest needs its sameRun preparation', 404)
        actual = self.bundle._ready_rights_artifacts(lease, row[0], manifest.artifacts)
        return self.refs_from_ready(lease, actual)

    def _historical_row(self, connection, lease, manifest):
        run = self.engine._lease(connection, lease)
        current = self.engine._production(connection, run['production_id'])
        return self._historical_source_row(connection, current['owner'], current['project_id'], manifest), current

    def _historical_source_row(self, connection, owner, project_id, manifest):
        if not connection.execute('SELECT id FROM projects WHERE id=? AND owner=?', (project_id, owner)).fetchone():
            raise EngineError('correction_origin_unavailable', 'Source context requires its actual local owned project', 403)
        row = connection.execute('SELECT * FROM bundle_revisions WHERE revision_id=? AND bundle_id=? AND owner=? AND project_id=?',
            (manifest.bundle_revision_id, manifest.bundle_id, owner, project_id)).fetchone()
        if (not row or not row['manifest_json'] or not row['manifest_sha256']
                or (manifest.instance_id, manifest.production_id, manifest.run_id, manifest.project_id, manifest.request_revision_id) != (
                    self.engine.instance_id, row['production_id'], row['run_id'], project_id, row['request_revision_id'])):
            raise EngineError('correction_origin_unavailable', 'Historical policy source must be the actual sameOwner/project local Bundle', 409)
        return row

    @staticmethod
    def _ready_receipt(connection, preparation_id, artifact, kind):
        item = connection.execute("SELECT * FROM bundle_items WHERE preparation_id=? AND artifact_id=? AND status='ready'", (preparation_id, artifact.artifact_id)).fetchone()
        if (not artifact.material_id or not item or (item['material_id'], item['relative_path'], item['media_type'], item['sha256'], item['size'], item['schema_kind']) != (
                artifact.material_id, artifact.relative_path, artifact.media_type, artifact.sha256, artifact.size, kind)):
            raise EngineError('correction_origin_integrity_failed', 'Historical policy proof differs from its original ready material journal', 422)
        return MaterialReceipt(preparation_id=preparation_id, artifact_id=artifact.artifact_id, material_id=artifact.material_id,
            sha256=artifact.sha256, size=artifact.size, media_type=artifact.media_type, schema_kind=kind)

    def read_historical_source(self, lease, manifest):
        """Controlled source read only; its old generation policy is not executed."""
        with self.engine.db.connect() as connection:
            _row, current = self._historical_row(connection, lease, manifest)
        return self._read_historical_source_for_owner(current['owner'], current['project_id'], manifest)

    def _read_historical_source_for_owner(self, owner, project_id, manifest):
        """Internal authenticated management resolver; never constructs an ordinary lease."""
        from video_creator.application.bundles import validate_text
        indexed = [item for item in manifest.artifacts if 'production_authorization' in item.roles]
        if not indexed:
            return None
        if len(indexed) != 1:
            raise EngineError('production_authorization_set_invalid', 'Historical source has one exact original authorization source', 422)
        authorization = indexed[0]
        plan = next((item for item in manifest.artifacts if item.relative_path == 'Creative/production-plan.json'), None)
        if plan is None:
            raise EngineError('production_authorization_plan_conflict', 'Historical source has no original indexed plan', 422)
        with self.engine.db.connect() as connection:
            row = self._historical_source_row(connection, owner, project_id, manifest)
            auth_receipt = self._ready_receipt(connection, row['id'], authorization, 'production_authorization')
            plan_receipt = self._ready_receipt(connection, row['id'], plan, 'creative_revision')
        documents = {}
        for artifact, receipt in ((authorization, auth_receipt), (plan, plan_receipt)):
            path = self.bundle._file('BundleMaterials', receipt.material_id)
            if artifact.size > 16 * 1024 * 1024 or artifact.size > self.bundle.assets.max_bytes:
                raise EngineError('source_closure_limit', 'Historical proof text exceeds the existing material/instance limit', 413)
            with path.open('rb') as handle:
                raw = handle.read(16 * 1024 * 1024 + 1)
            if len(raw) != receipt.size or hashlib.sha256(raw).hexdigest() != receipt.sha256:
                raise EngineError('correction_origin_integrity_failed', 'Historical proof file bytes changed', 422)
            documents[artifact.relative_path] = validate_text(raw, receipt.schema_kind, receipt.media_type)
        validate_portable_authorization(manifest, documents)
        source = SourcePolicyAuthorization(self.bundle._ref(row), ProductionAuthorizationMaterialRef(authorization, auth_receipt,
            documents[authorization.relative_path]), plan, plan_receipt, self.engine.clock())
        with self.engine.db.connect() as connection:
            record = self._assert_historical_source_for_owner(connection, owner, project_id, manifest, source)
        return SourcePolicyAuthorization(source.source_bundle_ref, source.authorization, source.plan_artifact, source.plan_receipt,
            source.observed_at_us, record.current, record.revoked)

    def assert_historical_source(self, connection, lease, manifest, source, *, right=None):
        _row, current = self._historical_row(connection, lease, manifest)
        return self._assert_historical_source_for_owner(connection, current['owner'], current['project_id'],
                                                       manifest, source, right=right)

    def _assert_historical_source_for_owner(self, connection, owner, project_id, manifest, source, *, right=None):
        """Immutable local history only. Never uses current _record/_bound.

        A replaced/revoked/expired creation policy remains historical provenance.
        Actual current RightsSnapshot/permission is checked separately by Bundle.
        """
        row = self._historical_source_row(connection, owner, project_id, manifest)
        if source.source_bundle_ref != self.bundle._ref(row):
            raise EngineError('correction_origin_integrity_failed', 'Historical proof belongs to a different original Bundle index', 422)
        document, fact = source.authorization.document, source.authorization.document.plan_admission
        original = self.engine._production(connection, manifest.production_id, owner)
        source_run = self.engine._run(connection, manifest.run_id)
        if (source_run['production_id'] != original['id'] or original['project_id'] != project_id
                or (fact.instance_id, fact.production_id, fact.run_id, fact.request_revision_id, fact.request_sha256) != (
                    self.engine.instance_id, original['id'], source_run['id'], original['request_revision_id'], original['request_sha256'])
                or (manifest.request_revision_id, manifest.request_sha256) != (fact.request_revision_id, fact.request_sha256)
                or digest(original['request_json']) != original['request_sha256']):
            raise EngineError('production_authorization_origin_conflict', 'Historical proof differs from actual original Production/Run/request', 422)
        issuer = self.issuer()
        admission = connection.execute('SELECT * FROM production_admissions WHERE id=? AND production_id=? AND run_id=?',
            (fact.admission_id, original['id'], source_run['id'])).fetchone()
        if not admission or issuer._fact(admission) != fact:
            raise EngineError('production_authorization_ledger_conflict', 'Historical source has no matching actual immutable local admission', 422)
        if isinstance(document, ProductionAuthorizationDocumentV02):
            daily = self.engine.daily_projects
            if daily is None:
                raise EngineError('daily_project_origin_unconfigured', 'Actual local delegated history reader is not installed', 503)
            record = daily.historical_record(connection, original, document)
        else:
            record = issuer.management_service._record(connection, document.policy_ref, original['owner'])
            action = record.installation_action
            command = connection.execute('SELECT request_sha256,result_json FROM commands WHERE owner=? AND scope=? AND idempotency_key=?',
                (original['owner'], 'production.authorization.' + action.action, action.idempotency_key)).fetchone()
            if ((record.policy_ref, record.policy, action) != (document.policy_ref, document.policy, document.owner_action)
                    or not command or command['request_sha256'] != action.request_sha256 or command['result_json'] != canonical(action)
                    or action.registry_revision > issuer.management_service._revision(connection)):
                raise EngineError('production_owner_action_unavailable', 'Historical statement is not its actual original local policy/Owner command', 422)
        plan, plan_sha = issuer._creative(connection, original, source_run, fact.target_id, 'plan')
        if (plan_sha != fact.target_sha256 or not isinstance(plan.body, dict)
                or plan_rights_body(plan.body) != [value.model_dump(mode='json') for value in record.policy.rights]
                or fact.rights_declaration_sha256 != issuer._rights_sha(record.policy)
                or not any(ref.kind == 'plan' and (ref.revision_id, ref.content_sha256) == (fact.target_id, fact.target_sha256)
                           for ref in manifest.creative_revision_refs)):
            raise EngineError('production_authorization_plan_conflict', 'Historical source plan/declaration differs from its actual immutable row', 422)
        for artifact, receipt, kind in ((source.authorization.artifact, source.authorization.receipt, 'production_authorization'),
                (source.plan_artifact, source.plan_receipt, 'creative_revision')):
            if artifact not in manifest.artifacts or self._ready_receipt(connection, row['id'], artifact, kind) != receipt:
                raise EngineError('correction_origin_integrity_failed', 'Historical proof ready identity changed before use', 422)
        if right is not None and (right.basis != 'user_asserted' or right.approval_ref != record.policy.rights_declaration_id
                or right not in record.policy.rights):
            raise EngineError('production_authorization_rights_conflict', 'Historical policy proves only its exact original Owner assertion', 403)
        return record

    def assert_current_copy_scope(self, connection, guard, lease, production, original, *, requested=None):
        """Use actual current request input scope, not a general policy Bool."""
        run = self.engine._lease(connection, lease)
        request, _record = self.issuer()._bound(connection, guard, production, run, action='execute_plan')
        if original.production_id == production['id'] and (original.request_revision_id, original.request_sha256) == (
                production['request_revision_id'], production['request_sha256']):
            return
        fields = ('system', 'namespace', 'article_id', 'article_revision', 'topic_id', 'topic_revision')
        covered = bool(original.source_refs)
        for ref in original.source_refs:
            matches = [binding for binding in request.source_bindings if all(getattr(binding, field) == getattr(ref, field) for field in fields)]
            if (len(matches) != 1 or not set(ref.input_asset_ids) <= set(request.inputs.asset_ids)
                    or matches[0].paragraph_ids and not set(ref.paragraph_ids) <= set(matches[0].paragraph_ids)):
                covered = False
        if covered:
            return  # _bound authenticated the exact namespace/principal/version and actual input Asset hashes.
        service = getattr(self.engine, 'local_copy_inputs', None)
        if service is not None and requested is not None:
            return service.assert_current_copy_scope(connection, guard, lease, production, requested)
        raise EngineError('production_copy_source_scope_missing', 'Current policy/request must explicitly cover this historical source input', 403)

    def refs_from_ready(self, lease, actual):
        from video_creator.application.bundles import validate_text
        refs = []
        for source in actual:
            artifact, receipt = source.artifact, source.receipt
            if receipt is None or receipt.schema_kind != 'production_authorization':
                if 'production_authorization' in artifact.roles:
                    raise EngineError('production_authorization_kind_invalid', 'Authorization role needs its actual controlled typed receipt', 422)
                continue
            if (artifact.roles != ('production_authorization',) or artifact.relative_path != AUTHORIZATION_PATH
                    or artifact.media_type != 'application/json' or receipt.media_type != artifact.media_type
                    or (receipt.sha256, receipt.size, receipt.material_id) != (artifact.sha256, artifact.size, artifact.material_id)):
                raise EngineError('production_authorization_kind_invalid', 'Actual authorization receipt and exact artifact role/path differ', 422)
            raw = source.content.path.read_bytes()
            if len(raw) != receipt.size or hashlib.sha256(raw).hexdigest() != receipt.sha256:
                raise EngineError('production_authorization_changed', 'Actual ready authorization bytes changed', 422)
            document = validate_text(raw, 'production_authorization', 'application/json')
            refs.append(ProductionAuthorizationMaterialRef(artifact, receipt, document))
        if len(refs) > 1:
            raise EngineError('production_authorization_set_invalid', 'Current local work has one exact authorization source', 422)
        return tuple(refs)

    def assert_local_current(self, connection, guard, lease, production, refs, *, right=None):
        if len(refs) != 1:
            raise EngineError('production_authorization_material_missing', 'Actual sameRun policy source material is required', 403)
        ref, issuer = refs[0], self.issuer()
        document, fact = ref.document, ref.document.plan_admission
        if (fact.instance_id, fact.production_id, fact.run_id, fact.request_revision_id, fact.request_sha256) != (
                self.engine.instance_id, production['id'], lease.run_id, production['request_revision_id'], production['request_sha256']):
            raise EngineError('production_authorization_local_conflict', 'Foreign or different work provenance cannot authorize this instance', 403)
        row = connection.execute('SELECT * FROM production_admissions WHERE id=? AND production_id=? AND run_id=?',
                                 (fact.admission_id, production['id'], lease.run_id)).fetchone()
        if not row or issuer._fact(row) != fact:
            raise EngineError('production_authorization_ledger_conflict', 'Local source is not its actual original immutable admission', 422)
        run = self.engine._lease(connection, lease)
        _request, record = issuer._bound(connection, guard, production, run, action='execute_plan')
        if (record.policy_ref, record.policy, record.installation_action) != (document.policy_ref, document.policy, document.owner_action):
            raise EngineError('production_authorization_policy_conflict', 'Actual current local policy/action differs from portable source', 403)
        if isinstance(document, ProductionAuthorizationDocumentV02) and record.derived_source != document.source:
            raise EngineError('production_authorization_policy_conflict', 'Actual complete current delegated source differs from its portable provenance', 403)
        current = issuer._earlier_action(connection, production, run, record, lease, 'execute_plan')
        if current.target_id != fact.target_id or current.target_sha256 != fact.target_sha256:
            raise EngineError('production_authorization_plan_conflict', 'Current fence requires the actual same immutable plan', 403)
        issuer.assert_production_admission_current(connection, guard, lease,
            ProductionAdmissionRef(admission_id=current.admission_id, content_sha256=digest(canonical(current))), stage='execute_plan')
        ready = connection.execute("SELECT * FROM bundle_items WHERE preparation_id=? AND artifact_id=? AND status='ready'",
                                   (ref.receipt.preparation_id, ref.artifact.artifact_id)).fetchone()
        if not ready or (ready['material_id'], ready['schema_kind'], ready['sha256'], ready['size']) != (
                ref.receipt.material_id, 'production_authorization', ref.receipt.sha256, ref.receipt.size):
            raise EngineError('production_authorization_material_changed', 'Current controlled ready receipt differs from the verified source', 422)
        if right is not None and (right.basis != 'user_asserted' or right.approval_ref != record.policy.rights_declaration_id or right not in record.policy.rights):
            raise EngineError('production_authorization_rights_conflict', 'A policy is neither owned/licensed authority nor a different declaration', 403)
        return current

    @contextmanager
    def publication_scope(self, lease, verified, manifest, final_context):
        scope = BundlePublicationScope(self, lease, verified, manifest, final_context, threading.get_ident())
        self.assert_verified_source(scope, hash_manifest=True)
        self._scopes.add(scope)
        try:
            yield scope
        finally:
            self._scopes.remove(scope)

    @contextmanager
    def publication_guard(self, lease, verified, manifest, final_context):
        with self.guard_for(lease) as guard:
            if guard is None:
                yield None, None
            else:
                with self.publication_scope(lease, verified, manifest, final_context) as scope:
                    yield guard, scope

    def assert_verified_source(self, scope, *, hash_manifest=False):
        with self.bundle._lock:
            observation = self.bundle._verified.get(scope.verified.verification_id)
        if (not observation or observation[0] != scope.lease or observation[1] != scope.manifest
                or observation[7] is not scope.final_context or observation[4] <= time.monotonic()
                or scope.final_context.final_manifest_sha256 != scope.verified.manifest_sha256):
            raise EngineError('production_publication_scope_invalid', 'Only actual service verification of this exact final Manifest can publish', 403)
        if hash_manifest and scope.verified.manifest_sha256 != hashlib.sha256((canonical(scope.manifest) + '\n').encode()).hexdigest():
            raise EngineError('production_publication_scope_invalid', 'Actual verified final Manifest identity differs', 403)

    def assert_publication_scope(self, scope, lease):
        if (not isinstance(scope, BundlePublicationScope) or scope.service is not self or scope not in self._scopes
                or scope.lease != lease or scope.thread_id != threading.get_ident()):
            raise EngineError('production_publication_scope_invalid', 'Final authorization is restricted to this actual publisher context', 403)
        self.assert_verified_source(scope)
        return scope.manifest, scope.final_context
