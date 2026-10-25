"""Same-instance trusted Owner wiring, never a task-controlled registration."""

from contextlib import contextmanager, nullcontext
from dataclasses import dataclass

from video_creator.application.local_copy_input_service import LocalCopyInputService
from video_creator.application.owner_bootstrap import (
    OwnerBootstrapStore,
    PersistentOwnerManagementRegistry,
)
from video_creator.application.production_admissions import ProductionAdmissions
from video_creator.application.production_authorization import (
    ProductionAuthorizationService,
)
from video_creator.application.production_management import (
    ProductionAuthorizationControl,
)
from video_creator.application.production_reauthorization import (
    ProductionReauthorization,
)
from video_creator.domain.errors import EngineError


class OwnerAuthorizationService(ProductionAuthorizationService):
    @contextmanager
    def confirmed_setup_action(self, source):
        from video_creator.application.owner_setup_service import OwnerSetupService
        from video_creator.application.owner_setup_sources import (
            OwnerActionConfirmationSource,
        )

        if (type(source) is not OwnerActionConfirmationSource or type(source._service) is not OwnerSetupService
                or source._service._services.authorization is not self or getattr(self, '_setup_action', None) is not None):
            raise EngineError('owner_setup_action_denied', 'Original same-instance setup management action is required', 403)
        source._service.assert_action_current(source)
        self._setup_action = source
        try:
            yield
        finally:
            self._setup_action = None

    def _setup_local(self, connection):
        source = getattr(self, '_setup_action', None)
        if source is not None:
            source._service.assert_action_local(source, connection)

    @contextmanager
    def _management_transaction(self, capability, projects):
        from video_creator.application.native_installation import NativeInstallationAuthority
        from video_creator.application.native_qualified_issuer import NativeQualifiedInstallationIssuer

        authority=getattr(self,'_qualified_authority',None)
        qualified=authority.qualification_issuer if type(authority) is NativeInstallationAuthority else None
        if type(qualified) is NativeQualifiedInstallationIssuer:
            import threading
            preflight=getattr(self,'_qualified_preflight',None)
            if preflight is not None:
                if preflight[0]!=threading.get_ident() or preflight[1] is not authority:
                    raise EngineError('qualification_unavailable','Original management source scope is foreign',503)
                evidence=preflight[2]
                authority._original(evidence)
            else:
                evidence=authority.observe()
            scope=qualified.current_writer_lease(evidence=evidence)
        else:
            scope=nullcontext(None)
        # OwnerControl and ProductionControl were acquired by the original
        # action path before this fixed hook; native lease is acquired now,
        # before the original SQLite transaction. No public callback.
        with scope as lease,super()._management_transaction(capability,projects) as connection:
            self._principal(capability, projects)
            self._setup_local(connection)
            if lease is not None:qualified.assert_writer_current(sql_connection=connection,lease=lease)
            yield connection
            self._principal(capability, projects)
            self._setup_local(connection)
            if lease is not None:qualified.assert_writer_current(sql_connection=connection,lease=lease)

    def _action(self, capability, key, action, command, projects, prepare, *, target_request=None):
        # Lock the durable Owner generation for the whole actual policy action,
        # including original short-writer current checks. Revocation serializes.
        with self.management.action_guard(capability, projects, self.management.owner_subject):
            return super()._action(capability, key, action, command, projects, prepare,
                                   target_request=target_request)


@dataclass(repr=False)
class OwnerServices:
    bootstrap: OwnerBootstrapStore
    registry: PersistentOwnerManagementRegistry | None
    authorization: ProductionAuthorizationService
    admissions: ProductionAdmissions
    reauthorization: ProductionReauthorization
    copy_inputs: LocalCopyInputService
    execution_identity: object | None = None
    native_registration_store: object | None = None
    native_current_registration: object | None = None
    daily_projects: object | None = None


def assemble_owner_services(engine, owner_subject, *, bundle, for_management=False,
                            installation_authority=None, execution_registration=None,
                            installation_session_guard=None, native_registration_store=None,
                            native_current_registration=None, owner_setup_bootstrap=None) -> OwnerServices:
    """Trusted host/CLI startup only; no Owner action or resource qualification.

    Integration supplies the concrete authority and exact authenticated register
    arguments. Configuration hashes alone are neither observations nor permission.
    Worker uses for_management=False and never loads management authentication.
    """
    if bundle.engine is not engine or bundle.principals.owner_subject != owner_subject:
        raise EngineError('owner_configuration_conflict', 'Owner wiring must use the actual same Engine, Bundle and domain Owner', 503)
    if owner_setup_bootstrap is not None and (type(owner_setup_bootstrap) is not OwnerBootstrapStore
            or owner_setup_bootstrap.engine is not engine):
        raise EngineError('owner_setup_instance_denied', 'Setup must retain the original same-instance Owner store', 403)
    bootstrap = owner_setup_bootstrap or OwnerBootstrapStore(engine)
    with bootstrap.current(allow_inactive=not for_management) as binding:
        if binding.principal.owner_subject != owner_subject:
            raise EngineError('owner_binding_denied', 'Configured domain Owner differs from the explicit OS Owner binding', 403)
    registry = PersistentOwnerManagementRegistry(bootstrap) if for_management else None
    control = ProductionAuthorizationControl(engine.db.data_dir / 'Control' / 'ProductionAuthorizationControl.json', engine.instance_id)
    service = (OwnerAuthorizationService if for_management else ProductionAuthorizationService)(engine, registry, control)
    issuer = ProductionAdmissions(service, installation_authority=installation_authority,
                                  installation_session_guard=installation_session_guard)
    # Private assembly uses the very same actual authority object as the
    # admission issuer. This reference grants no Owner or policy capability.
    if type(service) is OwnerAuthorizationService:
        service._qualified_authority=installation_authority
    copy_inputs = LocalCopyInputService(engine, service, bundle)
    engine.configure_local_copy_inputs(copy_inputs)
    if (native_registration_store is None) != (native_current_registration is None):
        raise EngineError('execution_registration_binding_denied', 'Durable native startup requires both original store and current source', 403)
    if native_registration_store is not None and (
            execution_registration is None or native_registration_store.engine is not engine
            or native_registration_store.original_projection(native_current_registration) != execution_registration):
        raise EngineError('execution_registration_binding_denied', 'Native execution projection lost its original same-instance current reference', 403)
    registered = None
    if execution_registration is not None:
        required = {'owner_subject', 'executing_principal_id', 'project_ids', 'registration_sha256',
            'resource_manifest_sha256', 'runtime_manifest_sha256', 'allowed_source_namespaces', 'expires_at_us'}
        if (type(execution_registration) is not dict or set(execution_registration) != required
                or execution_registration['owner_subject'] != owner_subject
                or execution_registration['executing_principal_id'] != owner_subject):
            raise EngineError('owner_execution_registration_denied', 'First installation wiring supports one exact authenticated local Owner only', 403)
        if installation_authority is None:
            raise EngineError('production_installation_authority_unconfigured', 'Actual held installation authority is required before execution registration', 503)
        registered = issuer.register_execution_identity(**execution_registration)
        if native_registration_store is not None:
            try:
                issuer.bind_native_registration(registered, store=native_registration_store, current=native_current_registration)
            except BaseException:
                issuer.unregister_execution_identity(registered)
                raise
        engine.configure_production_authorization(issuer, subject_identities={owner_subject: registered})
    from video_creator.application.daily_projects import DailyProjectService
    from video_creator.application.execution_registration import (
        ExecutionRegistrationStore,
    )

    registrations = native_registration_store or ExecutionRegistrationStore(engine, bootstrap=bootstrap, authorization=service)
    # Native store can be the original startup reader whose authorization
    # object predates this issuer; retain its actual same Control/bootstrap.
    daily = DailyProjectService(engine, bootstrap=registrations.bootstrap,
        authorization=service, registrations=registrations, issuer=issuer)
    if registered is not None:
        engine.configure_daily_projects(daily)
        # Before API/MCP/Worker ready, resolve only an exact already accepted
        # Goal floor. No pending means no forced qualification for draft use.
        with daily.control.locked():
            pending = daily.control.read().pending_request_sha256
        if pending is not None:
            with issuer.current_guard(registered):
                pass
    return OwnerServices(bootstrap, registry, service, issuer, ProductionReauthorization(issuer), copy_inputs,
                         registered, native_registration_store, native_current_registration, daily)
