"""Fixed B24 ports only; implementing a Protocol or submitting a fact grants nothing."""

from dataclasses import dataclass
from typing import Protocol

from video_creator.application.production_management import AdministrationCapability
from video_creator.domain import contracts as c
from video_creator.domain.bundle import BundleContentHandle, MaterialReceipt
from video_creator.domain.local_copy_input_scope import (
    BindLocalCopyInputScope,
    InstallLocalCopyInputScope,
    LocalCopyInputActionReceipt,
    LocalCopyInputActionRef,
    LocalCopyInputBinding,
    LocalCopyInputScope,
    LocalCopyInputScopeRecord,
    LocalCopyInputScopeRef,
    LocalCopySourceItem,
    LocalCopySourceSet,
    PreviewLocalCopyInputScope,
    RevokeLocalCopyInputScope,
    SelectLocalCopyInputScope,
)
from video_creator.domain.production_authorization import ProductionPolicyRef


@dataclass(frozen=True)
class LocalCopySourceObservation:
    """Actual resolver-owned bytes/Ready facts, not an accepted caller assertion."""
    item: LocalCopySourceItem
    manifest: c.BundleManifest
    content: BundleContentHandle
    material_receipt: MaterialReceipt | None
    asset: c.AssetRecord | None


@dataclass(frozen=True)
class ResolvedLocalCopySources:
    """Private full preview/use closure; implementation must authenticate its origin."""
    source_set: LocalCopySourceSet
    observations: tuple[LocalCopySourceObservation, ...]
    checked_at_us: int
    valid_until_us: int


@dataclass(frozen=True)
class CopyInputAdmission:
    """Service-issued current-fence fact, never a request DTO or foreign ticket."""
    binding_id: str
    instance_id: str
    owner_subject: str
    destination_project_id: str
    production_id: str
    run_id: str
    request_revision_id: str
    request_sha256: str
    executing_principal_id: str
    registration_sha256: str
    policy_ref: ProductionPolicyRef
    scope_ref: LocalCopyInputScopeRef
    selection_action_ref: LocalCopyInputActionRef
    source_set: LocalCopySourceSet
    source_set_sha256: str
    registry_revision: int
    fencing_token: int
    checked_at_us: int
    valid_until_us: int


class LocalCopySourceResolver(Protocol):
    """Trusted Bundle source reader; actual files outside writer, identity inside writer."""

    def resolve_for_management(self, capability: AdministrationCapability,
            proposal: PreviewLocalCopyInputScope | LocalCopyInputScope) -> ResolvedLocalCopySources: ...

    def assert_sources_current(self, connection, resolved: ResolvedLocalCopySources,
            *, owner_subject: str, project_id: str, checked_at_us: int) -> None: ...


class LocalCopyInputServicePort(Protocol):
    """Implementation pending in Slice B; none of these ports is installed by Slice A."""

    def preview(self, capability: AdministrationCapability,
            proposal: PreviewLocalCopyInputScope) -> LocalCopyInputScope: ...

    def install_scope(self, capability: AdministrationCapability, idempotency_key: str,
            command: InstallLocalCopyInputScope) -> LocalCopyInputActionReceipt: ...

    def select_scope(self, capability: AdministrationCapability, idempotency_key: str,
            command: SelectLocalCopyInputScope) -> LocalCopyInputActionReceipt: ...

    def revoke_scope(self, capability: AdministrationCapability, idempotency_key: str,
            command: RevokeLocalCopyInputScope) -> LocalCopyInputActionReceipt: ...

    def get_scope(self, capability: AdministrationCapability,
            ref: LocalCopyInputScopeRef) -> LocalCopyInputScopeRecord: ...

    def bind_existing(self, capability: AdministrationCapability, idempotency_key: str,
            command: BindLocalCopyInputScope) -> LocalCopyInputActionReceipt: ...

    def bind_default_request(self, connection, *, production, run, registered,
            policy_ref: ProductionPolicyRef) -> LocalCopyInputBinding | None: ...

    def assert_current_copy_scope(self, connection, authorization_guard,
            lease: c.LeaseGrant, production, requested: ResolvedLocalCopySources) -> CopyInputAdmission: ...
