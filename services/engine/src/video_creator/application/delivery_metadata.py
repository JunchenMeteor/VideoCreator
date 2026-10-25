"""One current content/metadata resolver; internal evidence is never disclosed."""

import hashlib
import json
from dataclasses import dataclass

from video_creator.application.engine import canonical, digest
from video_creator.domain import contracts as c
from video_creator.domain.bundle import AccessContext, BundleContentHandle
from video_creator.domain.errors import EngineError


@dataclass(frozen=True)
class GrantPath:
    grant_id: str
    preparation_id: str
    recipient_id: str
    body_sha256: str
    expires_at_us: int


@dataclass(frozen=True)
class VerifiedContentFile:
    artifact_id: str
    handle: BundleContentHandle
    binding: tuple
    signature: tuple


@dataclass(frozen=True)
class ContentScope:
    actor: AccessContext
    row: dict
    manifest: c.BundleManifestAny
    local_import: bool
    targets: tuple[str, ...]
    internal: tuple[str, ...]
    edges: tuple[tuple[str, str, str], ...]
    license_ids: frozenset[str]
    locator: object
    purpose_binding: object
    identity: tuple
    grant: GrantPath | None
    boundary_evidence: tuple[tuple[str, int | None], ...]
    checked_at_us: int


@dataclass(frozen=True)
class ResolvedContent:
    scope: ContentScope
    handle: BundleContentHandle
    verified_files: tuple[VerifiedContentFile, ...]

    def metadata(self, instance_id):
        deadlines = [value for _, value in self.scope.boundary_evidence if value is not None]
        return c.DeliveryContentMetadata(local_instance_id=instance_id, locator=self.scope.locator,
            sha256=self.handle.sha256, size=self.handle.size, media_type=self.handle.media_type,
            purpose_binding=self.scope.purpose_binding, checked_at_us=self.scope.checked_at_us,
            authorization_expires_at_us=min(deadlines) if deadlines else None)


class DeliveryResolver:
    def __init__(self, service):
        self.service, self.engine, self.assets = service, service.engine, service.assets

    @staticmethod
    def _json(value):
        from video_creator.application.bundles import strict_json
        if not isinstance(value, str):
            raise EngineError('bundle_text_invalid', 'Stored bundle JSON must be actual UTF-8 text', 422)
        try:
            encoded = value.encode('utf-8', errors='strict')
        except UnicodeError:
            raise EngineError('bundle_text_invalid', 'Stored bundle JSON must be actual UTF-8 text', 422) from None
        return strict_json(encoded)

    @staticmethod
    def _signature(path):
        stat = path.stat()
        return stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns, stat.st_ino

    def _manifest(self, row, imported):
        try:
            original = self._json(row['manifest_json'])
            if not isinstance(original, dict):
                raise TypeError('original index requires an object')
            manifest = c.parse_bundle_manifest(original)
            reference = (c.BundleRef.model_validate(self._json(row['origin_ref_json'])) if imported else self.service._ref(row))
        except (EngineError, ValueError, TypeError, KeyError):
            raise EngineError('bundle_integrity_failed', 'Original content index or reference is invalid', 422) from None
        expected = (reference.instance_id, reference.bundle_id, reference.bundle_revision_id, reference.schema_version)
        if (manifest.instance_id, manifest.bundle_id, manifest.bundle_revision_id, manifest.schema_version) != expected:
            raise EngineError('bundle_integrity_failed', 'Original index differs from its immutable reference', 422)
        if hashlib.sha256(row['manifest_json'].encode()).hexdigest() != reference.manifest_sha256:
            raise EngineError('bundle_integrity_failed', 'Original index bytes differ from the original reference SHA', 422)
        if imported:
            if row['origin_key'] != digest(canonical(reference)):
                raise EngineError('import_binding_invalid', 'Local import is bound to a different original reference', 422)
        elif (manifest.project_id, manifest.production_id, manifest.run_id, manifest.request_revision_id) != (
                row['project_id'], row['production_id'], row['run_id'], row['request_revision_id']):
            raise EngineError('bundle_integrity_failed', 'Published source identity differs from its original index', 422)
        return manifest, reference

    def _document(self, actor, identifier, imported, operation, purpose):
        current = self.service._actor(actor, operation, purpose)
        with self.engine.db.connect() as connection:
            if imported:
                row = connection.execute('SELECT * FROM bundle_imports WHERE id=? AND owner=?', (identifier, actor.subject_id)).fetchone()
            else:
                row = connection.execute("SELECT * FROM bundle_revisions WHERE revision_id=? AND status='published'", (identifier,)).fetchone()
        if row is None:
            raise EngineError('not_found', 'Local bundle import not found' if imported else 'Bundle revision not found', 404)
        row = dict(row)
        owner = current.subject_id == row['owner'] and current.owned_projects
        if not owner and row['project_id'] not in current.project_ids:
            raise EngineError('not_found', 'Local bundle import not found' if imported else 'Bundle revision not found', 404)
        manifest, reference = self._manifest(row, imported)
        return current, row, owner, manifest, reference

    def _grant(self, actor, row, reference, targets, purpose, semantic, now):
        with self.engine.db.connect() as connection:
            rows = connection.execute('SELECT * FROM bundle_grants WHERE preparation_id=? AND recipient_id=? AND revoked_at_us IS NULL AND expires_at_us>?',
                (row['id'], actor.subject_id, now)).fetchall()
        candidates, damaged = [], False
        for candidate in rows:
            try:
                grant = c.BundleReferenceGrant.model_validate(self._json(candidate['body']))
                if ((grant.grant_id, grant.recipient_id, grant.project_id, grant.bundle_ref, grant.expires_at_us) != (
                        candidate['id'], candidate['recipient_id'], row['project_id'], reference, candidate['expires_at_us'])
                        or candidate['owner'] != row['owner'] or grant.revoked_at_us is not None
                        or not grant.created_at_us <= now < grant.expires_at_us
                        or grant.created_at_us >= grant.expires_at_us
                        or len(set(grant.artifact_ids)) != len(grant.artifact_ids)
                        or len(set(grant.purposes)) != len(grant.purposes)):
                    raise ValueError('inconsistent original grant evidence')
            except (EngineError, ValueError, TypeError, KeyError):
                damaged = True
                continue
            if purpose in grant.purposes and set(targets) <= set(grant.artifact_ids) and (not semantic or grant.allow_semantic_text):
                candidates.append(GrantPath(grant.grant_id, row['id'], actor.subject_id,
                    hashlib.sha256(candidate['body'].encode()).hexdigest(), grant.expires_at_us))
        if not candidates:
            if damaged:
                raise EngineError('bundle_grant_invalid', 'No consistent active grant evidence confirms this exact content use', 422)
            raise EngineError('bundle_scope_denied', 'No active reference grant permits this exact bundle use', 403)
        return min(candidates, key=lambda value: (-value.expires_at_us, value.grant_id))

    @staticmethod
    def _closure(manifest, targets):
        indexed, rights = {}, {}
        for right in manifest.rights:
            if right.rights_id in rights:
                raise EngineError('bundle_index_invalid', 'Original rights identities are not unique', 422)
            for values in (right.license_document_artifact_ids, right.permitted_uses, right.platforms, right.territories, right.limitations):
                if len(set(values)) != len(values):
                    raise EngineError('bundle_index_invalid', 'Original rights lists must be distinct before closure traversal', 422)
            rights[right.rights_id] = right
        for artifact in manifest.artifacts:
            if (artifact.artifact_id in indexed or artifact.rights_ref not in rights
                    or len(set(artifact.dependency_artifact_ids)) != len(artifact.dependency_artifact_ids)
                    or len(set(artifact.roles)) != len(artifact.roles)):
                raise EngineError('bundle_index_invalid', 'Original artifact/right identities or dependency lists conflict', 422)
            indexed[artifact.artifact_id] = artifact
        if not targets or not set(targets) <= set(indexed):
            raise EngineError('not_found', 'Bundle artifact not found', 404)
        visiting, visited, edges, licenses = set(), set(), [], set()
        stack = [(identifier, False) for identifier in reversed(targets)]
        while stack:
            identifier, leaving = stack.pop()
            if leaving:
                visiting.remove(identifier)
                visited.add(identifier)
                continue
            if identifier in visiting:
                raise EngineError('bundle_dependency_cycle', 'Original artifact and license references contain a cycle', 422)
            if identifier in visited:
                continue
            artifact = indexed.get(identifier)
            if artifact is None:
                raise EngineError('bundle_license_missing', 'Necessary original dependency or license is absent from the index', 422)
            visiting.add(identifier)
            stack.append((identifier, True))
            successors = [(value, 'artifact_dependency') for value in artifact.dependency_artifact_ids]
            successors += [(value, 'license_document') for value in rights[artifact.rights_ref].license_document_artifact_ids]
            for child, relation in successors:
                if child not in indexed:
                    raise EngineError('bundle_license_missing', 'Necessary original dependency or license is absent from the index', 422)
                edges.append((identifier, child, relation))
                if relation == 'license_document':
                    licenses.add(child)
            stack.extend((child, False) for child, _ in reversed(successors))
        ordered = tuple(item.artifact_id for item in manifest.artifacts if item.artifact_id in visited)
        return ordered, tuple(edges), frozenset(licenses)

    def _scope(self, kind, actor, identifier, artifact_id, purpose):
        imported = kind.startswith('import_')
        journal = None
        request = None
        if kind == 'export_archive':
            with self.engine.db.connect() as connection:
                journal = connection.execute('SELECT * FROM bundle_exports WHERE id=?', (identifier,)).fetchone()
            if journal is None or (journal['owner'], journal['registration_id']) != (actor.subject_id, actor.registration_id):
                raise EngineError('not_found', 'Export job not found', 404)
            journal = dict(journal)
            try:
                request = c.BundleExportRequest.model_validate(self._json(journal['request_json']))
            except (EngineError, ValueError, TypeError):
                raise EngineError('export_integrity_failed', 'Original export request is invalid', 422) from None
            purpose = request.purpose
            imported = journal['import_id'] is not None
            if imported:
                source_id = journal['import_id']
            else:
                with self.engine.db.connect() as connection:
                    source = connection.execute('SELECT revision_id FROM bundle_revisions WHERE id=?', (journal['preparation_id'],)).fetchone()
                if source is None:
                    raise EngineError('not_found', 'Bundle revision not found', 404)
                source_id = source[0]
            operation = 'bundle.export'
        else:
            source_id = identifier
            operation = 'bundle.read' if kind.endswith('manifest') else 'bundle.content'
        current, row, owner, manifest, reference = self._document(actor, source_id, imported, operation, purpose)
        if request:
            targets = tuple(item.artifact_id for item in self.service._selection(manifest, request))
            semantic = request.delivery_profile == 'full' or any(item.artifact_id in targets and item.media_type.startswith(('text/', 'application/')) for item in manifest.artifacts)
            source = (c.LocalImportExportSource(import_id=row['id'], origin_bundle_ref=reference) if imported else c.LocalBundleExportSource(bundle_ref=reference))
            locator = c.ExportArchiveContentLocator(export_id=journal['id'], source=source, input_sha256=journal['input_sha256'],
                delivery_profile=request.delivery_profile, artifact_ids=request.artifact_ids)
            expected = digest(json.dumps({'bundle_ref':reference.model_dump(mode='json'),'request':request.model_dump(mode='json')},
                ensure_ascii=False,sort_keys=True,separators=(',', ':')))
            if expected != journal['input_sha256']:
                raise EngineError('export_integrity_failed', 'Original export input identity is inconsistent', 422)
            binding = c.ExportJournalPurpose(purpose=purpose)
        elif kind.endswith('manifest'):
            targets = tuple(item.artifact_id for item in manifest.artifacts)
            semantic = True
            locator = (c.ImportManifestContentLocator(import_id=row['id'], origin_bundle_ref=reference) if imported else c.BundleManifestContentLocator(bundle_ref=reference))
            binding = c.ContentRequestPurpose(purpose=purpose)
        else:
            targets, semantic = (artifact_id,), False
            locator = (c.ImportArtifactContentLocator(import_id=row['id'], origin_bundle_ref=reference, artifact_id=artifact_id) if imported else
                c.BundleArtifactContentLocator(bundle_ref=reference, artifact_id=artifact_id))
            binding = c.ContentRequestPurpose(purpose=purpose)
        internal, edges, licenses = self._closure(manifest, targets)
        now = self.engine.clock()
        # Registry facts are reread after index parsing; a changed registration
        # cannot silently widen the original actor of this request.
        current = self.service._actor(actor, operation, purpose)
        grant = None if imported or owner else self._grant(current, row, reference, targets, purpose, semantic, now)
        boundaries = [('registration', current.expires_at_us)]
        if current.expires_at_us is not None and (type(current.expires_at_us) is not int or current.expires_at_us <= now):
            raise EngineError('authorization_boundary_invalid', 'Current registration has no consistent unexpired deadline fact', 422)
        if grant:
            boundaries.append(('grant:' + grant.grant_id, grant.expires_at_us))
        rights = {value.rights_id:value for value in manifest.rights}
        for artifact in manifest.artifacts:
            if artifact.artifact_id in internal:
                right = rights[artifact.rights_ref]
                if ((right.valid_from_us is not None and right.valid_from_us > now)
                        or (right.expires_at_us is not None and right.expires_at_us <= now)
                        or artifact.artifact_id in targets and purpose not in right.permitted_uses):
                    raise EngineError('bundle_rights_denied', 'Necessary content rights do not permit this current use or time', 403)
                boundaries.append(('right:' + right.rights_id, right.expires_at_us))
        if request and journal['status'] != 'ready':
            raise EngineError('export_not_ready', 'Exact archive is not ready', 409)
        if request and (not journal['archive_sha256'] or journal['size'] is None or not journal['archive_file_key']):
            raise EngineError('export_integrity_failed', 'Ready original archive facts are incomplete', 422)
        identity = (kind, row['id'], row['owner'], row['project_id'], row['manifest_json'], row['manifest_file_key'],
            row['mapping_json'] if imported else (row['status'], row['manifest_sha256'], row['request_revision_id']))
        if journal:
            identity += (journal['id'], journal['owner'], journal['registration_id'], journal['preparation_id'],journal['import_id'],
                journal['input_sha256'],journal['request_json'],journal['status'],journal['archive_file_key'],journal['archive_sha256'],journal['size'])
        return ContentScope(current, row, manifest, imported, targets, internal, edges, licenses, locator, binding,
            identity, grant, tuple(boundaries), now)

    def _node(self, scope, artifact):
        if scope.local_import:
            try:
                mapping = self._json(scope.row['mapping_json'])
                binding = mapping.get(artifact.artifact_id) if isinstance(mapping, dict) else None
            except EngineError:
                raise EngineError('import_binding_invalid', 'Local import mapping is invalid', 422) from None
            if not binding:
                raise EngineError('import_binding_missing', 'Necessary local import locator is unavailable', 503)
            expected_keys = {'asset_id'} if artifact.asset_id else {'material_id','schema_kind'}
            if not isinstance(binding, dict) or set(binding) != expected_keys:
                raise EngineError('import_binding_invalid', 'Necessary local import locator conflicts with the original indexed type', 422)
            material = binding.get('material_id')
            source_asset = binding.get('asset_id')
            kind = binding.get('schema_kind')
            proof_binding = tuple(sorted(binding.items()))
        else:
            with self.engine.db.connect() as connection:
                ready = connection.execute("SELECT * FROM bundle_items WHERE preparation_id=? AND artifact_id=?", (scope.row['id'], artifact.artifact_id)).fetchone()
            if not ready or ready['status'] != 'ready':
                raise EngineError('bundle_mapping_unavailable', 'Necessary original artifact has no ready local receipt', 503)
            expected = (artifact.asset_id, artifact.material_id, artifact.sha256, artifact.size, artifact.media_type, artifact.relative_path)
            actual = (ready['asset_id'],ready['material_id'],ready['sha256'],ready['size'],ready['media_type'],ready['relative_path'])
            if actual != expected:
                raise EngineError('bundle_integrity_failed', 'Necessary original artifact differs from its actual ready receipt', 422)
            material, source_asset, kind = ready['material_id'], ready['asset_id'], ready['schema_kind']
            proof_binding = (*actual, kind, ready['status'])
        if source_asset:
            if not isinstance(source_asset, str):
                raise EngineError('import_binding_invalid', 'Necessary local Asset identity is invalid', 422)
            try:
                record = self.assets.get(scope.row['owner'], source_asset)
            except EngineError as error:
                if error.code != 'not_found':
                    raise
                raise EngineError('import_binding_missing' if scope.local_import else 'bundle_integrity_failed',
                    'Necessary original Asset record is unavailable', 503 if scope.local_import else 422) from None
            if (record.sha256, record.size, record.media_type) != (artifact.sha256, artifact.size, artifact.media_type):
                raise EngineError('import_binding_invalid' if scope.local_import else 'bundle_integrity_failed', 'Necessary Asset differs from the original index', 422)
            # Scope and exact record were checked above. Full hash runs once in
            # phase2; the fresh final authorization phase does no large IO.
            path = self.assets._path('Objects', record.sha256)
        else:
            if not isinstance(material, str) or not material:
                raise EngineError('import_binding_missing', 'Necessary local material locator is unavailable', 503)
            path = self.service._file('BundleMaterials', material)
        if ((artifact.artifact_id in scope.license_ids or 'license' in artifact.roles)
                and (artifact.roles != ('license',) or not material or kind != 'license' or artifact.media_type != 'text/plain')):
            raise EngineError('bundle_license_invalid', 'Necessary license must be the original controlled license/plain-text material', 422)
        return path, proof_binding

    def _check_file(self, path, sha, size):
        try:
            before = self._signature(path)
            if before[0] != size or self.assets._hash(path) != sha or before != self._signature(path):
                raise EngineError('bundle_integrity_failed', 'Necessary original content bytes changed or differ from the index', 422)
            return before
        except OSError:
            raise EngineError('bundle_integrity_failed', 'Necessary original content file is unavailable', 422) from None

    def resolve(self, kind, actor, identifier, artifact_id=None, purpose='playback'):
        try:
            return self._resolve(kind, actor, identifier, artifact_id, purpose)
        except (ValueError, TypeError, KeyError, OSError):
            raise EngineError('bundle_integrity_failed', 'Original local content facts or bytes are invalid', 422) from None

    def _resolve(self, kind, actor, identifier, artifact_id, purpose):
        initial = self._scope(kind, actor, identifier, artifact_id, purpose)
        reference = self.service._origin_ref(initial.row) if initial.local_import else self.service._ref(initial.row)
        manifest_path = self.service._file('BundleManifests', initial.row['manifest_file_key'])
        manifest_size = len(initial.row['manifest_json'].encode())
        manifest_signature = self._check_file(manifest_path, reference.manifest_sha256, manifest_size)
        files = []
        internal = set(initial.internal)
        for artifact in initial.manifest.artifacts:
            if artifact.artifact_id not in internal:
                continue
            path, binding = self._node(initial, artifact)
            signature = self._check_file(path, artifact.sha256, artifact.size)
            if artifact.artifact_id in initial.license_ids or 'license' in artifact.roles:
                from video_creator.application.bundles import validate_text
                validate_text(path.read_bytes(), 'license', artifact.media_type)
            files.append(VerifiedContentFile(artifact.artifact_id,
                BundleContentHandle(path, artifact.sha256, artifact.size, artifact.media_type, initial.purpose_binding.purpose), binding, signature))
        if kind == 'export_archive':
            with self.engine.db.connect() as connection:
                journal = connection.execute('SELECT * FROM bundle_exports WHERE id=?', (identifier,)).fetchone()
            if journal is None:
                raise EngineError('not_found', 'Export job not found', 404)
            path = self.service._file('BundleExports', journal['archive_file_key'])
            handle = BundleContentHandle(path, journal['archive_sha256'], journal['size'], 'application/zip', initial.purpose_binding.purpose)
            content_signature = self._check_file(path, handle.sha256, handle.size)
        elif kind.endswith('manifest'):
            handle = BundleContentHandle(manifest_path, reference.manifest_sha256, manifest_size, 'application/json', purpose)
            content_signature = manifest_signature
        else:
            handle = next(value.handle for value in files if value.artifact_id == artifact_id)
            content_signature = next(value.signature for value in files if value.artifact_id == artifact_id)
        # A fresh actual time/registry/row/grant/rights observation after hashing.
        final = self._scope(kind, actor, identifier, artifact_id, purpose)
        if (final.identity, final.targets, final.internal, final.edges, final.license_ids) != (
                initial.identity, initial.targets, initial.internal, initial.edges, initial.license_ids):
            raise EngineError('bundle_integrity_failed', 'Original content identity changed during verification', 422)
        indexed = {value.artifact_id:value for value in final.manifest.artifacts}
        for fact in files:
            artifact = indexed[fact.artifact_id]
            path, binding = self._node(final, artifact)
            if path != fact.handle.path or binding != fact.binding or self._signature(path) != fact.signature:
                raise EngineError('bundle_integrity_failed', 'Necessary ready locator or file changed during authorization', 422)
        if self._signature(manifest_path) != manifest_signature or self._signature(handle.path) != content_signature:
            raise EngineError('bundle_integrity_failed', 'Original manifest/content changed during authorization', 422)
        return ResolvedContent(final, handle, tuple(files))
