"""Trusted startup: ordinary held production facts and explicit qualification."""

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from video_creator.application.owner_services import (
    OwnerServices,
    assemble_owner_services,
)
from video_creator.application.production_admissions import InstalledProductionEvidence
from video_creator.application.local_installation_authority import LocalInstallationAuthority
from video_creator.domain.errors import EngineError
from video_creator.infrastructure.held_authority import (
    HeldFactsObservation,
    NativeLaunchContext,
    OwnedAuthorityConnection,
)
from video_creator.infrastructure.windows_authority_pipe import (
    OwnerProtectedNativeBuild,
    open_owner_protected_native_build,
)


class QualifiedInstallationIssuer(Protocol):
    """Future independently admitted qualification store, not a bool adapter.

    Required input is the exact authenticated original held observation plus
    full launch identity. It must resolve actual current qualification records
    (including allowed role, complete file/ABI/license/workflow/driver identities
    and revocation) and bind the resulting original evidence to that record.
    It is not registered by this protocol, Owner policy, or install hashes.
    Current I49 not_ready blocks this port; its report/ref wire is not yet admitted.
    """
    def issue(self, *, connection: OwnedAuthorityConnection,
              original_facts: HeldFactsObservation,
              context: NativeLaunchContext) -> InstalledProductionEvidence: ...

    def assert_current(self, *, evidence: InstalledProductionEvidence,
                       connection: OwnedAuthorityConnection,
                       original_facts: HeldFactsObservation,
                       context: NativeLaunchContext) -> None: ...


class NativeInstallationAuthority:
    def __init__(self, connection: OwnedAuthorityConnection, *, qualification_issuer: QualifiedInstallationIssuer | None = None):
        self.connection, self.qualification_issuer = connection, qualification_issuer
        self._lock, self._originals = threading.RLock(), {}

    def observe(self) -> InstalledProductionEvidence:
        with self._lock:
            facts = self.connection.observe_facts()
            if facts.qualification == 'not_ready' or self.qualification_issuer is None:
                raise EngineError('production_installation_not_ready', 'Authenticated held files have no admitted current production qualification', 503)
            # This branch requires a future independently admitted host
            # qualification protocol. Current I49 cannot reach it.
            evidence = self.qualification_issuer.issue(connection=self.connection, original_facts=facts, context=self.connection.context)
            self._validate(evidence, facts)
            self._originals[id(evidence)] = (evidence, facts)
            self.assert_current(evidence)
            return evidence

    def _validate(self, evidence, facts):
        context = self.connection.context
        if (type(evidence) is not InstalledProductionEvidence
                or (evidence.instance_id, evidence.registration_sha256, evidence.resource_manifest_sha256,
                    evidence.runtime_manifest_sha256, evidence.workflow_version, evidence.driver_profile) != (
                    context.instance_id, context.registration_sha256, context.resource_manifest_sha256,
                    context.runtime_manifest_sha256, 'registered-media-bundle-v1', 'registered-production-drivers-v1')
                or evidence.observed_at_us != facts.observed_at_us):
            raise EngineError('production_installation_binding_invalid', 'Qualified evidence differs from the authenticated original observation', 503)
        engine_names = set(context.engine_file_names)
        expected_engine = tuple(sorted((file.relative_path, file.sha256) for file in facts.files if file.relative_path in engine_names))
        expected_resources = tuple(sorted((file.relative_path, file.sha256) for file in facts.files if file.relative_path not in engine_names))
        if evidence.engine_source_sha256 != expected_engine or evidence.indexed_resource_sha256 != expected_resources:
            raise EngineError('production_installation_binding_invalid', 'Qualified evidence must cover both exact complete held partitions', 503)

    def _original(self, evidence):
        self.connection.assert_local_current()
        pair = self._originals.get(id(evidence))
        if pair is None or pair[0] is not evidence:
            raise EngineError('installation_observation_denied', 'Original evidence object from this live adapter is required', 409)
        self.connection.assert_local_observation(pair[1])
        return pair[1]

    def assert_current(self, evidence):
        with self._lock:
            facts = self._original(evidence)
            self.connection.assert_current_facts(facts)
            if facts.qualification == 'not_ready' or self.qualification_issuer is None:
                raise EngineError('production_installation_not_ready', 'Original installation has no admitted qualification', 503)
            self.qualification_issuer.assert_current(evidence=evidence, connection=self.connection,
                                                     original_facts=facts, context=self.connection.context)
            self.connection.assert_local_observation(facts)

    def assert_local_current(self, evidence):
        """Short writer hook: object/epoch and local OS handle state, no RPC."""
        if not self._lock.acquire(blocking=False):
            raise EngineError('installation_session_busy', 'Installation adapter is currently in external observation', 503)
        try:
            facts = self._original(evidence)
            from video_creator.application.native_qualified_issuer import NativeQualifiedInstallationIssuer

            if type(self.qualification_issuer) is NativeQualifiedInstallationIssuer:
                self.qualification_issuer.assert_local_current(evidence=evidence, connection=self.connection,
                    original_facts=facts, context=self.connection.context)
        finally:
            self._lock.release()

    def close(self):
        with self._lock:
            from video_creator.application.native_qualified_issuer import NativeQualifiedInstallationIssuer

            if type(self.qualification_issuer) is NativeQualifiedInstallationIssuer:
                self.qualification_issuer.close()
            self._originals.clear()
            self.connection.close()


@dataclass(eq=False, repr=False)
class NativeOwnerServices:
    services: OwnerServices
    connection: OwnedAuthorityConnection
    authority: NativeInstallationAuthority | LocalInstallationAuthority
    build: OwnerProtectedNativeBuild
    _closed: bool = False

    def close(self):
        if not self._closed:
            self.authority.close()
            self.build.close()
            if self.services.execution_identity is not None:
                self.services.admissions.unregister_execution_identity(self.services.execution_identity)
            self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, *_exception):
        self.close()


def connect_native_installation(*, locator_bytes: bytes, context: NativeLaunchContext,
                                installed_native_image: Path, installed_native_image_sha256: str,
                                qualification_issuer: QualifiedInstallationIssuer | None = None):
    """Fixed trusted entry only; never read environment or a public payload.

    Image path/SHA must originate from the Owner-protected installed build record,
    independently of the private child locator. Returning facts is not authority.
    Caller retains both returned objects and closes connection before build.
    """
    if qualification_issuer is not None:
        raise EngineError('installation_peer_denied', 'Qualified startup requires its explicit factory', 403)
    build = open_owner_protected_native_build(image_path=installed_native_image,
                                              expected_sha256=installed_native_image_sha256)
    connection = None
    try:
        connection = OwnedAuthorityConnection(locator_bytes=locator_bytes, context=context, trusted_build=build)
        from video_creator.application.local_installation_authority import local_authority_from_connection
        return local_authority_from_connection(connection=connection, build=build), build
    except BaseException:
        if connection is not None:
            connection.close()
        build.close()
        raise


def assemble_native_owner_services(engine, owner_subject, *, bundle, locator_bytes: bytes,
                                   context: NativeLaunchContext, installed_native_image: Path,
                                   installed_native_image_sha256: str, execution_registration=None,
                                   for_management=False, qualification_issuer=None,
                                   native_registration_store=None, native_current_registration=None) -> NativeOwnerServices:
    """Actual same-instance factory injected by trusted native API/MCP/Worker.

    No public module selector, Owner action or policy install. Worker explicitly
    refuses management wiring and does not load a management secret. Existing
    Owner binding, project/control and execution scope guards remain mandatory.
    """
    if (context.instance_id != engine.instance_id or context.role == 'worker' and for_management):
        raise EngineError('installation_peer_denied', 'Native role or instance cannot alter Owner management wiring', 403)
    if execution_registration is not None:
        expected = (context.registration_sha256, context.resource_manifest_sha256, context.runtime_manifest_sha256)
        if (type(execution_registration) is not dict
                or tuple(execution_registration.get(name) for name in ('registration_sha256', 'resource_manifest_sha256', 'runtime_manifest_sha256')) != expected):
            raise EngineError('installation_peer_denied', 'Execution registration must match this exact native installation context', 403)
    authority, build = connect_native_installation(locator_bytes=locator_bytes, context=context,
        installed_native_image=installed_native_image, installed_native_image_sha256=installed_native_image_sha256,
        qualification_issuer=qualification_issuer)
    try:
        services = assemble_owner_services(engine, owner_subject, bundle=bundle, for_management=for_management,
            installation_authority=authority, installation_session_guard=authority,
            execution_registration=execution_registration, native_registration_store=native_registration_store,
            native_current_registration=native_current_registration)
        return NativeOwnerServices(services, authority.connection, authority, build)
    except BaseException:
        try:
            authority.close()
        finally:
            build.close()
        raise


def connect_qualified_native_installation(*, engine, bundle, locator_bytes, context,
                                          installed_native_image, installed_native_image_sha256):
    """Closed same-Engine v2 assembly; no caller-supplied issuer or trust anchor."""
    from video_creator.application.native_qualified_issuer import NativeQualifiedInstallationIssuer
    from video_creator.infrastructure.native_qualification_trust import open_native_qualification_trust
    from video_creator.infrastructure.qualified_authority import OwnedQualifiedAuthorityConnection

    if bundle.engine is not engine or context.instance_id != engine.instance_id:
        raise EngineError('qualification_unavailable', 'Original same-Engine Bundle/context is required', 503)
    build = open_owner_protected_native_build(image_path=installed_native_image,
        expected_sha256=installed_native_image_sha256)
    connection, source = None, None
    try:
        connection = OwnedQualifiedAuthorityConnection(locator_bytes=locator_bytes, context=context, trusted_build=build)
        source = open_native_qualification_trust(engine=engine, bundle=bundle, connection=connection, build=build)
        issuer = NativeQualifiedInstallationIssuer(engine=engine, bundle=bundle, connection=connection, trust_source=source)
        return NativeInstallationAuthority(connection, qualification_issuer=issuer), build
    except BaseException as failure:
        for original in (source, connection, build):
            if original is not None:
                try:
                    original.close()
                except BaseException as cleanup:
                    failure.add_note('Original qualified startup cleanup also failed: ' + type(cleanup).__name__)
        raise
