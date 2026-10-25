"""Independent local input selection; neither rights clearance nor execution permission."""

import hashlib
import json
from typing import Annotated, Literal

from pydantic import Field, model_validator

from video_creator.domain import contracts as c
from video_creator.domain.production_authorization import ProductionPolicyRef

LOCAL_COPY_SCOPE_VERSION = '0.1.0-candidate'
MAX_SOURCE_ARTIFACTS = 256
MAX_SOURCE_REPORTS = 32


def canonical_sha256(model):
    raw = json.dumps(model.model_dump(mode='json'), ensure_ascii=False, sort_keys=True,
                     separators=(',', ':'), allow_nan=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def member_key(reference):
    return (reference.bundle_ref.instance_id, reference.bundle_ref.bundle_id,
            reference.bundle_ref.bundle_revision_id, reference.bundle_ref.schema_version,
            reference.bundle_ref.manifest_sha256, reference.artifact_id)


class LocalCopyInputScopeRef(c.Contract):
    scope_id: c.Identifier
    revision: int = Field(gt=0, strict=True)
    content_sha256: c.Sha256


class LocalCopyInputActionRef(c.Contract):
    action_id: c.Identifier
    content_sha256: c.Sha256


class LocalCopyMemberRef(c.Contract):
    bundle_ref: c.BundleRef
    artifact_id: c.Identifier

    @model_validator(mode='after')
    def explicit_version(self):
        if self.bundle_ref.schema_version not in {'0.2.0-candidate', '0.3.0-candidate'}:
            raise ValueError('Local copy requires an explicit supported immutable Bundle version')
        return self


class LocalCopyMaterialLocator(c.Contract):
    kind: Literal['material'] = 'material'
    material_id: c.Identifier


class LocalCopyAssetLocator(c.Contract):
    kind: Literal['asset'] = 'asset'
    asset_id: c.Identifier


class LocalCopySourceItem(LocalCopyMemberRef):
    kind: Literal['local_bundle_artifact'] = 'local_bundle_artifact'
    source_instance_id: c.Identifier
    source_project_id: c.Identifier
    source_production_id: c.Identifier
    locator: Annotated[LocalCopyMaterialLocator | LocalCopyAssetLocator, Field(discriminator='kind')]
    sha256: c.Sha256
    size: int = Field(gt=0, le=9_223_372_036_854_775_807, strict=True)
    media_type: str = Field(min_length=1, max_length=100)
    roles: tuple[c.Identifier, ...]
    rights_id: c.Identifier
    rights_sha256: c.Sha256
    handling: Literal['verify_only', 'copy_into_delivery']
    required_uses: tuple[c.UsePurpose, ...]

    @model_validator(mode='after')
    def finite_item(self):
        if self.source_instance_id != self.bundle_ref.instance_id:
            raise ValueError('Source instance and immutable BundleRef must agree')
        if (not self.roles or len(set(self.roles)) != len(self.roles)
                or not self.required_uses or len(set(self.required_uses)) != len(self.required_uses)):
            raise ValueError('Source roles and uses must be explicit and distinct')
        if self.handling == 'copy_into_delivery' and not {'derivative', 'export', 'redistribution'} <= set(self.required_uses):
            raise ValueError('Delivery copy requires derivative, export and redistribution scope')
        text_types = {'application/json', 'application/x-ndjson', 'text/plain', 'text/srt', 'text/vtt'}
        if (self.media_type in text_types) != (self.locator.kind == 'material'):
            raise ValueError('Indexed text Material cannot be disguised as a media Asset')
        c.reject_secrets(self.model_dump(mode='json'))
        return self


class LocalCopyDependencyEdge(c.Contract):
    source: LocalCopyMemberRef
    target: LocalCopyMemberRef
    kind: Literal['artifact_dependency', 'license_dependency', 'authorization_proof', 'correction_origin']


class LocalCopyRequestedRoot(LocalCopyMemberRef):
    handling: Literal['verify_only', 'copy_into_delivery']
    required_uses: tuple[c.UsePurpose, ...]

    @model_validator(mode='after')
    def exact_handling(self):
        if not self.required_uses or len(set(self.required_uses)) != len(self.required_uses):
            raise ValueError('Root uses must be finite, explicit and distinct')
        if self.handling == 'copy_into_delivery' and not {'derivative', 'export', 'redistribution'} <= set(self.required_uses):
            raise ValueError('Delivery root requires derivative, export and redistribution')
        return self


class PreviewLocalCopyInputScope(c.Contract):
    """Owner chooses finite roots; trusted service resolves their complete proof closure."""
    scope_id: c.Identifier
    revision: int = Field(gt=0, strict=True)
    instance_id: c.Identifier
    destination_project_id: c.Identifier
    executing_principal_ids: tuple[c.Identifier, ...]
    registration_sha256: c.Sha256
    policy_ref: ProductionPolicyRef
    valid_from_us: int = Field(gt=0, le=9_223_372_036_854_775_807, strict=True)
    expires_at_us: int = Field(gt=0, le=9_223_372_036_854_775_807, strict=True)
    roots: tuple[LocalCopyRequestedRoot, ...] = Field(min_length=1, max_length=MAX_SOURCE_ARTIFACTS)

    @model_validator(mode='after')
    def finite_preview(self):
        if (not self.executing_principal_ids or len(set(self.executing_principal_ids)) != len(self.executing_principal_ids)
                or len({member_key(root) for root in self.roots}) != len(self.roots)
                or self.expires_at_us <= self.valid_from_us
                or any(root.bundle_ref.instance_id != self.instance_id for root in self.roots)):
            raise ValueError('Preview requires distinct local roots/principals and a finite time interval')
        c.reject_secrets(self.model_dump(mode='json'))
        return self


class LocalCopySourceSet(c.Contract):
    """Ordered full source identities; no include-future-dependencies permission."""
    items: tuple[LocalCopySourceItem, ...] = Field(min_length=1, max_length=MAX_SOURCE_ARTIFACTS)
    roots: tuple[LocalCopyMemberRef, ...] = Field(min_length=1, max_length=MAX_SOURCE_ARTIFACTS)
    edges: tuple[LocalCopyDependencyEdge, ...] = Field(max_length=MAX_SOURCE_ARTIFACTS * MAX_SOURCE_ARTIFACTS)

    @model_validator(mode='after')
    def complete_graph(self):
        keys = [member_key(value) for value in self.items]
        roots = [member_key(value) for value in self.roots]
        edge_keys = [(member_key(value.source), member_key(value.target), value.kind) for value in self.edges]
        if (len(set(keys)) != len(keys) or len(set(roots)) != len(roots)
                or len(set(edge_keys)) != len(edge_keys) or not set(roots) <= set(keys)):
            raise ValueError('Duplicate/conflicting sources, roots or edges are rejected before deduplication')
        graph = {key: [] for key in keys}
        for source, target, _kind in edge_keys:
            if source not in graph or target not in graph or source == target:
                raise ValueError('Every dependency must name two exact approved source members')
            graph[source].append(target)
        visited, visiting = set(), set()

        def walk(key):
            if key in visiting:
                raise ValueError('Local source dependencies must be acyclic')
            if key in visited:
                return
            visiting.add(key)
            for child in graph[key]:
                walk(child)
            visiting.remove(key)
            visited.add(key)

        for root in roots:
            walk(root)
        if visited != set(keys):
            raise ValueError('Source set cannot hide unrelated members outside its selected closure')
        return self


class LocalCopyInputScope(c.Contract):
    kind: Literal['local_copy_input_scope'] = 'local_copy_input_scope'
    version: Literal['0.1.0-candidate'] = LOCAL_COPY_SCOPE_VERSION
    scope_id: c.Identifier
    revision: int = Field(gt=0, strict=True)
    instance_id: c.Identifier
    owner_subject: c.Identifier
    destination_project_id: c.Identifier
    executing_principal_ids: tuple[c.Identifier, ...]
    registration_sha256: c.Sha256
    policy_ref: ProductionPolicyRef
    valid_from_us: int = Field(gt=0, le=9_223_372_036_854_775_807, strict=True)
    expires_at_us: int = Field(gt=0, le=9_223_372_036_854_775_807, strict=True)
    source_set: LocalCopySourceSet
    source_set_sha256: c.Sha256

    @model_validator(mode='after')
    def exact_local_scope(self):
        if (not self.executing_principal_ids or len(set(self.executing_principal_ids)) != len(self.executing_principal_ids)
                or self.expires_at_us <= self.valid_from_us):
            raise ValueError('Local input scope requires distinct principals and a finite validity interval')
        if self.source_set_sha256 != canonical_sha256(self.source_set):
            raise ValueError('Source set SHA must bind every ordered member, root and dependency')
        if any((item.source_instance_id, item.source_project_id) != (self.instance_id, self.destination_project_id)
               for item in self.source_set.items):
            raise ValueError('Local input scope only admits the exact same instance and project')
        c.reject_secrets(self.model_dump(mode='json'))
        return self


class InstallLocalCopyInputScope(c.Contract):
    scope: LocalCopyInputScope
    previous_ref: LocalCopyInputScopeRef | None = None

    @model_validator(mode='after')
    def explicit_replacement(self):
        if self.previous_ref is None:
            if self.scope.revision != 1:
                raise ValueError('A new scope starts at revision one')
        elif (self.previous_ref.scope_id != self.scope.scope_id
              or self.scope.revision != self.previous_ref.revision + 1):
            raise ValueError('Replacement must target the exact preceding immutable scope revision')
        return self


class SelectLocalCopyInputScope(c.Contract):
    scope_ref: LocalCopyInputScopeRef
    destination_project_id: c.Identifier
    executing_principal_id: c.Identifier
    registration_sha256: c.Sha256
    policy_ref: ProductionPolicyRef


class RevokeLocalCopyInputScope(c.Contract):
    scope_ref: LocalCopyInputScopeRef
    reason: str = Field(min_length=1, max_length=2000)


class BindLocalCopyInputScope(c.Contract):
    scope_ref: LocalCopyInputScopeRef
    production_id: c.Identifier
    run_id: c.Identifier
    request_revision_id: c.Identifier
    request_sha256: c.Sha256


class LocalCopyInputActionReceipt(c.Contract):
    kind: Literal['local_copy_input_action'] = 'local_copy_input_action'
    version: Literal['0.1.0-candidate'] = LOCAL_COPY_SCOPE_VERSION
    action_id: c.Identifier
    instance_id: c.Identifier
    administrator_id: c.Identifier
    authentication_binding_id: c.Identifier
    authentication_source: Literal['native_owner_session', 'headless_administrator']
    owner_subject: c.Identifier
    destination_project_id: c.Identifier
    action: Literal['create', 'replace', 'select', 'revoke', 'bind_request']
    scope_ref: LocalCopyInputScopeRef
    idempotency_key: c.Identifier
    request_sha256: c.Sha256
    authorized_at_us: int = Field(gt=0, strict=True)
    registry_revision: int = Field(gt=0, strict=True)
    reason: str | None = Field(default=None, min_length=1, max_length=2000)
    target: BindLocalCopyInputScope | None = None

    @model_validator(mode='after')
    def exact_action(self):
        if ((self.action == 'revoke') != (self.reason is not None)
                or (self.action == 'bind_request') != (self.target is not None)
                or self.target is not None and self.target.scope_ref != self.scope_ref):
            raise ValueError('Only revocation has a reason and only exact request binding has a target')
        c.reject_secrets(self.model_dump(mode='json'))
        return self


class LocalCopyInputScopeRecord(c.Contract):
    scope_ref: LocalCopyInputScopeRef
    scope: LocalCopyInputScope
    installation_action: LocalCopyInputActionReceipt
    current: bool = Field(strict=True)
    revoked: bool = Field(strict=True)
    revocation_action: LocalCopyInputActionReceipt | None = None

    @model_validator(mode='after')
    def original_action(self):
        scope, action = self.scope, self.installation_action
        if (self.scope_ref != LocalCopyInputScopeRef(scope_id=scope.scope_id, revision=scope.revision,
                content_sha256=canonical_sha256(scope)) or action.scope_ref != self.scope_ref
                or action.action not in {'create', 'replace'}
                or (action.instance_id, action.owner_subject, action.destination_project_id) != (
                    scope.instance_id, scope.owner_subject, scope.destination_project_id)
                or self.revoked != (self.revocation_action is not None)):
            raise ValueError('Scope record needs its exact immutable scope and actual installation action')
        if self.revocation_action is not None:
            revoked = self.revocation_action
            if (revoked.action != 'revoke' or revoked.scope_ref != self.scope_ref
                    or (revoked.instance_id, revoked.owner_subject, revoked.destination_project_id) != (
                        scope.instance_id, scope.owner_subject, scope.destination_project_id)):
                raise ValueError('Revocation must name the original exact local scope')
        return self


class LocalCopyInputBinding(c.Contract):
    """Persistent selected input set; deliberately no execution fence or permission flag."""
    binding_id: c.Identifier
    instance_id: c.Identifier
    owner_subject: c.Identifier
    destination_project_id: c.Identifier
    production_id: c.Identifier
    run_id: c.Identifier
    request_revision_id: c.Identifier
    request_sha256: c.Sha256
    executing_principal_id: c.Identifier
    registration_sha256: c.Sha256
    policy_ref: ProductionPolicyRef
    scope_ref: LocalCopyInputScopeRef
    selection_action_ref: LocalCopyInputActionRef
    source_set_sha256: c.Sha256
    bound_at_us: int = Field(gt=0, strict=True)
    registry_revision: int = Field(gt=0, strict=True)
