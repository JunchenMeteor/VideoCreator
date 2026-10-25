"""Actual bounded local Bundle source closure, issued only by this concrete resolver."""

import threading

from video_creator.application.delivery_metadata import DeliveryResolver
from video_creator.application.engine import canonical, digest
from video_creator.application.local_copy_input_ports import (
    LocalCopySourceObservation,
    ResolvedLocalCopySources,
)
from video_creator.domain import contracts as c
from video_creator.domain.bundle import BundleContentHandle, MaterialReceipt
from video_creator.domain.errors import EngineError
from video_creator.domain.local_copy_input_scope import (
    LocalCopyAssetLocator,
    LocalCopyDependencyEdge,
    LocalCopyMaterialLocator,
    LocalCopyMemberRef,
    LocalCopySourceItem,
    LocalCopySourceSet,
    member_key,
)


class LocalCopyBundleSourceResolver:
    def __init__(self, bundle, management_service):
        if bundle.engine is not management_service.engine:
            raise EngineError('local_copy_configuration_conflict', 'Source reader and real management must share this Engine', 503)
        self.bundle, self.engine, self.management = bundle, bundle.engine, management_service
        self._issued = {}
        self._cache_lock = threading.RLock()

    def resolve_for_management(self, capability, proposal):
        principal = self.management._principal(capability, (proposal.destination_project_id,))
        if proposal.instance_id != self.engine.instance_id or (hasattr(proposal, 'owner_subject')
                and proposal.owner_subject != principal.owner_subject):
            raise EngineError('local_copy_scope_denied', 'Management preview belongs to a different local Owner/instance', 403)
        roots = proposal.roots if hasattr(proposal, 'roots') else tuple(
            next(item for item in proposal.source_set.items if member_key(item) == member_key(root))
            for root in proposal.source_set.roots)
        return self._resolve(principal.owner_subject, proposal.destination_project_id, roots)

    def resolve_for_execution(self, lease, roots):
        with self.engine.db.connect() as connection:
            run = self.engine._lease(connection, lease)
            production = self.engine._production(connection, run['production_id'])
        return self._resolve(production['owner'], production['project_id'], roots)

    def _row(self, connection, owner, project_id, reference):
        row = connection.execute("SELECT * FROM bundle_revisions WHERE bundle_id=? AND revision_id=? AND owner=? AND project_id=? AND status='published'",
            (reference.bundle_id, reference.bundle_revision_id, owner, project_id)).fetchone()
        if (reference.instance_id != self.engine.instance_id or not row or not row['manifest_json']
                or not row['manifest_file_key'] or self.bundle._ref(row) != reference):
            raise EngineError('local_copy_source_unavailable', 'Source must be its exact actual published local sameOwner/project Bundle', 409)
        manifest = c.parse_bundle_manifest(row['manifest_json'])
        original = self.engine._production(connection, row['production_id'], owner)
        if ((manifest.instance_id, manifest.project_id, manifest.production_id, manifest.run_id,
                manifest.request_revision_id, manifest.request_sha256) != (self.engine.instance_id, project_id,
                row['production_id'], row['run_id'], row['request_revision_id'], original['request_sha256'])
                or digest(original['request_json']) != original['request_sha256']):
            raise EngineError('local_copy_source_invalid', 'Source index and original local request identities do not agree', 422)
        return row, manifest

    def _origin_reference(self, owner, project_id, reference):
        with self.engine.db.connect() as connection:
            rows = connection.execute("SELECT b.* FROM bundle_revisions b JOIN bundle_items i ON i.preparation_id=b.id WHERE i.material_id=? AND i.artifact_id=? AND i.status='ready' AND b.owner=? AND b.project_id=? AND b.status='published'",
                (reference.material_id, reference.artifact_id, owner, project_id)).fetchall()
        if len(rows) != 1:
            raise EngineError('local_copy_source_unavailable', 'Correction origin must resolve one exact original local Ready index', 409)
        return self.bundle._ref(rows[0])

    def _resolve(self, owner, project_id, roots):
        from video_creator.application.bundles import record_sha, validate_text
        nodes, manifests, histories, edges, walking = {}, {}, {}, {}, set()
        reports, report_graph, expected_origins = {}, {}, {}
        logical_bytes = 0

        def load(reference):
            key = canonical(reference)
            if key not in manifests:
                with self.engine.db.connect() as connection:
                    row, manifest = self._row(connection, owner, project_id, reference)
                path = self.bundle._file('BundleManifests', row['manifest_file_key'])
                if (not path.is_file() or path.stat().st_size > 16 * 1024 * 1024
                        or path.read_bytes() != row['manifest_json'].encode()
                        or self.bundle.assets._hash(path) != reference.manifest_sha256):
                    raise EngineError('local_copy_source_invalid', 'Source Manifest actual full bytes changed', 422)
                manifests[key] = (dict(row), manifest)
                histories[key] = self.bundle._production_authorization._read_historical_source_for_owner(owner, project_id, manifest)
            return manifests[key], histories[key]

        def edge(parent, child, kind):
            value = LocalCopyDependencyEdge(source=LocalCopyMemberRef(bundle_ref=parent.bundle_ref, artifact_id=parent.artifact_id),
                target=LocalCopyMemberRef(bundle_ref=child.bundle_ref, artifact_id=child.artifact_id), kind=kind)
            edges[(member_key(parent), member_key(child), kind)] = value

        def visit(reference, artifact_id, handling, uses):
            nonlocal logical_bytes
            ref = LocalCopyMemberRef(bundle_ref=reference, artifact_id=artifact_id)
            key = member_key(ref)
            if key in walking:
                raise EngineError('local_copy_source_invalid', 'Source/license/proof closure contains a cycle', 422)
            if key in nodes:
                old = nodes[key]
                merged = tuple(sorted(set(old.item.required_uses) | set(uses)))
                chosen = 'copy_into_delivery' if 'copy_into_delivery' in (handling, old.item.handling) else 'verify_only'
                if (merged, chosen) == (old.item.required_uses, old.item.handling):
                    return ref
                # Revisit stricter actual uses; never deduplicate away a constraint.
                nodes.pop(key)
                logical_bytes -= old.item.size
                uses, handling = merged, chosen
            (row, manifest), history = load(reference)
            artifact = next((item for item in manifest.artifacts if item.artifact_id == artifact_id), None)
            right = next((item for item in manifest.rights if artifact and item.rights_id == artifact.rights_ref), None)
            if not artifact or not right:
                raise EngineError('local_copy_source_unavailable', 'Selected source/rights is absent from its exact Bundle index', 409)
            actual_uses = tuple(sorted(set(uses)))
            self.bundle._rights_time(right, self.engine.clock(), actual_uses if handling == 'copy_into_delivery' else ())
            if right.basis != 'user_asserted':
                raise EngineError('rights_preflight_admission_required', 'Actual owned/licensed source authority is not yet admitted', 503)
            with self.engine.db.connect() as connection:
                self._row(connection, owner, project_id, reference)
                ready = connection.execute("SELECT * FROM bundle_items WHERE preparation_id=? AND artifact_id=? AND status='ready'", (row['id'], artifact_id)).fetchone()
                if (not ready or (ready['material_id'], ready['asset_id'], ready['sha256'], ready['size'], ready['media_type'], ready['relative_path']) != (
                        artifact.material_id, artifact.asset_id, artifact.sha256, artifact.size, artifact.media_type, artifact.relative_path)):
                    raise EngineError('local_copy_source_invalid', 'Actual source Ready receipt disagrees with its immutable index', 422)
                if history is not None:
                    self.bundle._production_authorization._assert_historical_source_for_owner(connection, owner, project_id, manifest, history, right=right)
                else:
                    self.bundle._assert_owner_right(connection, manifest.production_id, right, manifest.approval_refs, manifest.creative_revision_refs)
            if len(nodes) >= 256 or logical_bytes + artifact.size > self.bundle.assets.max_bytes:
                raise EngineError('source_closure_limit', 'Source artifacts and logical bytes exceed actual instance limits', 413)
            path = self.bundle._artifact_path(owner, artifact)
            if not path.is_file() or path.stat().st_size != artifact.size or self.bundle.assets._hash(path) != artifact.sha256:
                raise EngineError('local_copy_source_invalid', 'Source actual full file SHA/size differs from Ready identity', 422)
            receipt = asset = parsed = None
            if artifact.material_id:
                receipt = MaterialReceipt(preparation_id=row['id'], artifact_id=artifact_id, material_id=artifact.material_id,
                    sha256=artifact.sha256, size=artifact.size, media_type=artifact.media_type, schema_kind=ready['schema_kind'])
                parsed = validate_text(path.read_bytes(), receipt.schema_kind, artifact.media_type)
                locator = LocalCopyMaterialLocator(material_id=artifact.material_id)
            else:
                asset = self.bundle.assets.get(owner, artifact.asset_id)
                if (asset.sha256, asset.size, asset.media_type) != (artifact.sha256, artifact.size, artifact.media_type) or not asset.probe.decoded:
                    raise EngineError('local_copy_source_invalid', 'Media source requires its actual decoded registered Asset', 422)
                locator = LocalCopyAssetLocator(asset_id=artifact.asset_id)
            item = LocalCopySourceItem(bundle_ref=reference, artifact_id=artifact_id, source_instance_id=self.engine.instance_id,
                source_project_id=project_id, source_production_id=manifest.production_id, locator=locator, sha256=artifact.sha256,
                size=artifact.size, media_type=artifact.media_type, roles=artifact.roles, rights_id=right.rights_id,
                rights_sha256=digest(canonical(right)), handling=handling, required_uses=actual_uses)
            nodes[key] = LocalCopySourceObservation(item, manifest,
                BundleContentHandle(path, artifact.sha256, artifact.size, artifact.media_type, actual_uses[0]), receipt, asset)
            logical_bytes += artifact.size
            walking.add(key)
            if isinstance(parsed, (c.PrecisionEvaluationReport, c.PrecisionEvaluationReportV03)):
                if record_sha(parsed) != parsed.content_sha256:
                    raise EngineError('local_copy_source_invalid', 'Original report record SHA is not its actual strict full report', 422)
                report_identity = (receipt.schema_kind, parsed.content_sha256, artifact.sha256, artifact.size, artifact.media_type)
                previous_report = reports.get(parsed.evaluation_id)
                if previous_report is not None and previous_report != report_identity:
                    raise EngineError('local_copy_source_invalid', 'One historical report ID has conflicting strict grammar/record/full byte identities', 422)
                reports[parsed.evaluation_id] = report_identity
                report_graph.setdefault(parsed.evaluation_id, set())
                if len(reports) > 32:
                    raise EngineError('source_closure_limit', 'Actual historical report count exceeds the existing bound', 413)
            for identifier in artifact.dependency_artifact_ids:
                child = visit(reference, identifier, handling, actual_uses)
                edge(ref, child, 'artifact_dependency')
            for identifier in right.license_document_artifact_ids:
                child = visit(reference, identifier, handling, actual_uses)
                child_item = nodes[member_key(child)].item
                child_receipt = nodes[member_key(child)].material_receipt
                if child_item.roles != ('license',) or child_receipt is None or child_receipt.schema_kind != 'license' or child_item.media_type != 'text/plain':
                    raise EngineError('bundle_license_missing', 'Actual license must retain its own Ready grammar/role/full bytes', 422)
                edge(ref, child, 'license_dependency')
            if isinstance(parsed, (c.PrecisionEvaluationReport, c.PrecisionEvaluationReportV03)):
                origin = parsed.corrected_from if isinstance(parsed, c.PrecisionEvaluationReportV03) else None
                if origin is not None:
                    if origin.artifact_id not in artifact.dependency_artifact_ids:
                        raise EngineError('correction_origin_unavailable', 'Source parent must index the exact ancestor forward edge', 422)
                    indexed = nodes[member_key(LocalCopyMemberRef(bundle_ref=reference, artifact_id=origin.artifact_id))]
                    if indexed.item.sha256 != origin.sha256 or indexed.item.roles != ('precision_evaluation',):
                        raise EngineError('local_copy_source_invalid', 'Parent ancestor copy differs from its full original locator', 422)
                    original_ref = self._origin_reference(owner, project_id, origin)
                    origin_key = (canonical(original_ref), origin.artifact_id)
                    previous_origin = expected_origins.get(origin_key)
                    if previous_origin is not None and previous_origin != origin:
                        raise EngineError('local_copy_source_invalid', 'One original ancestor identity has conflicting full reference constraints', 422)
                    expected_origins[origin_key] = origin
                    child = visit(original_ref, origin.artifact_id, handling, actual_uses)
                    report_graph[parsed.evaluation_id].add(origin.report_id)
                    edge(ref, child, 'correction_origin')
            expected = expected_origins.get((canonical(reference), artifact_id))
            if expected is not None and (artifact.material_id != expected.material_id or artifact.sha256 != expected.sha256
                    or not isinstance(parsed, (c.PrecisionEvaluationReport, c.PrecisionEvaluationReportV03))
                    or (parsed.evaluation_id, parsed.content_sha256, parsed.alignment_revision_id, parsed.alignment_content_sha256) != (
                        expected.report_id, expected.content_sha256, expected.alignment_revision_id, expected.alignment_content_sha256)):
                raise EngineError('local_copy_source_invalid', 'Ancestor full locator/grammar/record/alignment identity changed', 422)
            walking.remove(key)
            return ref

        actual_roots = {member_key(ref): ref for ref in (
            visit(root.bundle_ref, root.artifact_id, root.handling, root.required_uses) for root in roots)}

        def reaches(start, target):
            queue, seen = [start], set()
            while queue:
                key = queue.pop()
                if key == target:
                    return True
                if key in seen:
                    continue
                seen.add(key)
                queue.extend(child for parent, child, _kind in edges if parent == key)
            return False

        proof_bundles = set()
        while set(manifests) - proof_bundles:
            bundle_key = min(set(manifests) - proof_bundles)
            proof_bundles.add(bundle_key)
            row, manifest = manifests[bundle_key]
            reference = self.bundle._ref(row)
            history = histories[bundle_key]
            anchors = [value.item for value in nodes.values() if canonical(value.item.bundle_ref) == bundle_key]
            proof_ids = set()
            if history is not None:
                proof_ids.update((history.authorization.artifact.artifact_id, history.plan_artifact.artifact_id))
            else:
                # Real human declaration also carries its indexed immutable
                # creative file, not merely a guessed approval ID in metadata.
                for anchor in anchors:
                    right = next(value for value in manifest.rights if value.rights_id == anchor.rights_id)
                    with self.engine.db.connect() as connection:
                        ready = connection.execute("SELECT artifact_id,material_id FROM bundle_items WHERE preparation_id=? AND status='ready' AND schema_kind='creative_revision'", (row['id'],)).fetchall()
                    matches = []
                    for item in ready:
                        path = self.bundle._file('BundleMaterials', item['material_id'])
                        if path.stat().st_size > 16 * 1024 * 1024:
                            raise EngineError('source_closure_limit', 'Source human proof exceeds bounded text size', 413)
                        parsed = validate_text(path.read_bytes(), 'creative_revision', 'application/json')
                        if parsed.revision_id == right.approval_ref:
                            matches.append(item['artifact_id'])
                    if len(matches) != 1:
                        raise EngineError('local_copy_source_invalid', 'Actual human declaration needs its unique indexed Ready creative proof', 422)
                    proof_ids.add(matches[0])
            for proof_id in sorted(proof_ids):
                proof = visit(reference, proof_id, 'verify_only', ('derivative',))
                related = [anchor for anchor in anchors if anchor.artifact_id not in proof_ids]
                linked = False
                for anchor in related:
                    parent = LocalCopyMemberRef(bundle_ref=anchor.bundle_ref, artifact_id=anchor.artifact_id)
                    if reaches(member_key(proof), member_key(parent)):
                        # A certificate can refer back to an earlier creative
                        # file without introducing a false file hash cycle.
                        actual_roots[member_key(proof)] = proof
                        edge(proof, parent, 'authorization_proof')
                    else:
                        edge(parent, proof, 'authorization_proof')
                    linked = True
                if not linked:
                    actual_roots[member_key(proof)] = proof
        for (bundle_key, artifact_id), expected in expected_origins.items():
            observation = next(value for value in nodes.values() if canonical(value.item.bundle_ref) == bundle_key and value.item.artifact_id == artifact_id)
            receipt = observation.material_receipt
            parsed = validate_text(observation.content.path.read_bytes(), receipt.schema_kind, receipt.media_type) if receipt else None
            if (receipt is None or receipt.schema_kind != ('precision_report' if expected.schema_version == c.SCHEMA_VERSION else 'precision_report_v03')
                    or observation.item.roles != ('precision_evaluation',) or observation.item.locator.kind != 'material'
                    or observation.item.locator.material_id != expected.material_id or observation.item.sha256 != expected.sha256
                    or not isinstance(parsed, (c.PrecisionEvaluationReport, c.PrecisionEvaluationReportV03))
                    or (parsed.evaluation_id, parsed.content_sha256, parsed.alignment_revision_id, parsed.alignment_content_sha256) != (
                        expected.report_id, expected.content_sha256, expected.alignment_revision_id, expected.alignment_content_sha256)):
                raise EngineError('local_copy_source_invalid', 'Complete original ancestor identity does not match its declared forward edge', 422)
        report_depths, report_visiting = {}, set()

        def ancestor_depth(report_id):
            if report_id in report_visiting:
                raise EngineError('local_copy_source_invalid', 'Actual corrected_from report graph contains a cycle', 422)
            if report_id in report_depths:
                return report_depths[report_id]
            if report_id not in reports:
                raise EngineError('local_copy_source_invalid', 'Actual corrected_from ancestor has no strictly verified original report', 422)
            report_visiting.add(report_id)
            depth = 1 + max((ancestor_depth(child) for child in report_graph[report_id]), default=0)
            report_visiting.remove(report_id)
            if depth > 32:
                raise EngineError('source_closure_limit', 'Actual corrected_from report ancestor chain exceeds the existing bound', 413)
            report_depths[report_id] = depth
            return depth

        for report_id in reports:
            ancestor_depth(report_id)
        # Resolver output ordering is deterministic; hashing never silently
        # sorts or folds a caller-provided tuple after Owner confirmation.
        nodes = dict(sorted(nodes.items()))
        source_set = LocalCopySourceSet(items=tuple(value.item for value in nodes.values()), roots=tuple(actual_roots.values()),
            edges=tuple(value for _key, value in sorted(edges.items())))
        now = self.engine.clock()
        expiry = min([now + 30_000_000, *[right.expires_at_us for observation in nodes.values()
            for right in observation.manifest.rights if right.rights_id == observation.item.rights_id and right.expires_at_us is not None]])
        resolved = ResolvedLocalCopySources(source_set, tuple(nodes.values()), now, expiry)
        with self._cache_lock:
            self._issued = {key: value for key, value in self._issued.items() if value[0].valid_until_us > now}
            if len(self._issued) >= 256:
                raise EngineError('local_copy_observation_limit', 'Current bounded source observations are full; retry after expiry', 503)
            self._issued[id(resolved)] = (resolved, owner, project_id, histories)
        with self.engine.db.connect() as connection:
            self.assert_sources_current(connection, resolved, owner_subject=owner, project_id=project_id, checked_at_us=self.engine.clock())
        return resolved

    def assert_sources_current(self, connection, resolved, *, owner_subject, project_id, checked_at_us):
        with self._cache_lock:
            issued = self._issued.get(id(resolved))
        if (not issued or issued[0] is not resolved or issued[1:3] != (owner_subject, project_id)
                or not resolved.checked_at_us <= checked_at_us < resolved.valid_until_us):
            raise EngineError('local_copy_observation_stale', 'Only this resolver actual complete current observation can be consumed', 409)
        for observation in resolved.observations:
            item = observation.item
            row, manifest = self._row(connection, owner_subject, project_id, item.bundle_ref)
            artifact = next((value for value in manifest.artifacts if value.artifact_id == item.artifact_id), None)
            right = next((value for value in manifest.rights if value.rights_id == item.rights_id), None)
            expected_id = item.locator.material_id if item.locator.kind == 'material' else item.locator.asset_id
            if (manifest != observation.manifest or not artifact or not right
                    or (artifact.sha256, artifact.size, artifact.media_type, artifact.roles, artifact.rights_ref) != (
                        item.sha256, item.size, item.media_type, item.roles, item.rights_id)
                    or (artifact.material_id if item.locator.kind == 'material' else artifact.asset_id) != expected_id
                    or digest(canonical(right)) != item.rights_sha256):
                raise EngineError('local_copy_source_invalid', 'Actual source/member/rights identity changed before commit', 422)
            ready = connection.execute("SELECT * FROM bundle_items WHERE preparation_id=? AND artifact_id=? AND status='ready'", (row['id'], item.artifact_id)).fetchone()
            if (not ready or (ready['material_id'], ready['asset_id'], ready['sha256'], ready['size'], ready['media_type'], ready['relative_path']) != (
                    artifact.material_id, artifact.asset_id, artifact.sha256, artifact.size, artifact.media_type, artifact.relative_path)
                    or observation.material_receipt and ready['schema_kind'] != observation.material_receipt.schema_kind):
                raise EngineError('local_copy_source_invalid', 'Actual member Ready journal changed before commit', 422)
            if observation.asset is not None:
                asset = connection.execute('SELECT * FROM assets WHERE id=? AND owner=?', (observation.asset.asset_id, owner_subject)).fetchone()
                try:
                    probe = c.MediaProbe.model_validate(DeliveryResolver._json(asset['probe_json'])) if asset else None
                except (ValueError, TypeError):
                    raise EngineError('local_copy_source_invalid', 'Actual media Asset probe storage is damaged', 422) from None
                if (not asset or (asset['sha256'], asset['size'], asset['media_type'], asset['source'], asset['rights']) != (
                        observation.asset.sha256, observation.asset.size, observation.asset.media_type,
                        observation.asset.source, observation.asset.rights)
                        or probe != observation.asset.probe):
                    raise EngineError('local_copy_source_invalid', 'Actual media Asset identity/probe changed before commit', 422)
            self.bundle._rights_time(right, checked_at_us, item.required_uses if item.handling == 'copy_into_delivery' else ())
            if right.basis != 'user_asserted':
                raise EngineError('rights_preflight_admission_required', 'Current real source authority is not admitted', 503)
            history = issued[3][canonical(item.bundle_ref)]
            if history is None:
                self.bundle._assert_owner_right(connection, manifest.production_id, right, manifest.approval_refs, manifest.creative_revision_refs)
            else:
                self.bundle._production_authorization._assert_historical_source_for_owner(connection, owner_subject, project_id, manifest, history, right=right)

    def recheck_files(self, resolved):
        with self._cache_lock:
            issued = self._issued.get(id(resolved))
        if not issued or issued[0] is not resolved:
            raise EngineError('local_copy_observation_stale', 'Original source observation is unavailable', 409)
        manifests = {}
        with self.engine.db.connect() as connection:
            for value in resolved.observations:
                row, _manifest = self._row(connection, issued[1], issued[2], value.item.bundle_ref)
                manifests[row['id']] = dict(row)
        for row in manifests.values():
            path = self.bundle._file('BundleManifests', row['manifest_file_key'])
            if path.read_bytes() != row['manifest_json'].encode() or self.bundle.assets._hash(path) != row['manifest_sha256']:
                raise EngineError('local_copy_source_invalid', 'Source Manifest actual full file changed after preview', 422)
        for value in resolved.observations:
            path = value.content.path
            if not path.is_file() or path.stat().st_size != value.item.size or self.bundle.assets._hash(path) != value.item.sha256:
                raise EngineError('local_copy_source_invalid', 'Source/proof actual full file changed after preview', 422)
