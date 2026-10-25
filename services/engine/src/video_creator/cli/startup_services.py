"""Trusted in-process assembly; incomplete shutdown retains original services."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Literal, Protocol

from video_creator.domain.errors import EngineError

if TYPE_CHECKING:
    from video_creator.application.bundles import BundleService
    from video_creator.application.engine import EngineService
    from video_creator.application.media_registration import RegisteredMediaRuntime
    from video_creator.application.native_installation import NativeOwnerServices

StartupRole = Literal['api', 'mcp', 'worker']


class InstalledServiceFactory(Protocol):
    """Fixed launch adapter closes its own partial construction on failure.

    There is no task/public/environment factory registration. All entry roles
    are execution-only; authenticated management uses its separate Owner path.
    """

    def __call__(self, *, engine: EngineService, bundle: BundleService,
                 role: StartupRole, registered_runtime: RegisteredMediaRuntime | None,
                 for_management: Literal[False]) -> NativeOwnerServices: ...


# A failed service call can unwind main while its resources remain alive. Keep
# original objects reachable until confirmed cleanup or actual process terminal.
# No reattachment, retry, automatic close, or atexit success claim is provided.
_retained: dict[int, StartupInstallation] = {}


class StartupInstallation:
    def __init__(self, native: NativeOwnerServices):
        self.native = native
        self.closed = False
        _retained[id(self)] = self

    def finish_shutdown(self, original_threads: set[threading.Thread]) -> None:
        if self.closed:
            return
        if any(thread.is_alive() for thread in threading.enumerate()
               if thread not in original_threads):
            raise EngineError('installed_services_cleanup_pending',
                              'Original service resources have not actually ended', 503)
        # If close raises, retain the original objects and primary failure.
        self.native.close()
        self.closed = True
        del _retained[id(self)]


def install_startup_services(factory: InstalledServiceFactory | None, *,
                             engine: EngineService, bundle: BundleService,
                             role: StartupRole,
                             registered_runtime: RegisteredMediaRuntime | None = None
                             ) -> StartupInstallation | None:
    if factory is None:
        return None
    from video_creator.application.native_installation import NativeOwnerServices

    if (role not in {'api', 'mcp', 'worker'} or bundle.engine is not engine
            or role == 'worker' and (registered_runtime is None
                or registered_runtime.engine is not engine
                or registered_runtime.bundle is not bundle)
            or role != 'worker' and registered_runtime is not None):
        raise EngineError('installed_services_binding_invalid',
                          'Startup requires the same actual Engine, Bundle and registered runtime', 503)
    native = factory(engine=engine, bundle=bundle, role=role,
                     registered_runtime=registered_runtime, for_management=False)
    if type(native) is not NativeOwnerServices:
        raise EngineError('installed_services_binding_invalid',
                          'Startup factory must return original native Owner services', 503)
    held = StartupInstallation(native)
    services = native.services
    context = native.connection.context
    if (native._closed or context.instance_id != engine.instance_id or context.role != role
            or native.authority.connection is not native.connection
            or services.bootstrap.engine is not engine
            or services.authorization.engine is not engine
            or services.admissions.engine is not engine
            or services.admissions.installation_authority is not native.authority
            or services.admissions.installation_session_guard is not native.authority
            or services.copy_inputs.engine is not engine or services.copy_inputs.bundle is not bundle
            or services.registry is not None or services.authorization.management is not None):
        raise EngineError('installed_services_binding_invalid',
                          'Returned services differ from the fixed execution-only instance or role', 503)
    return held


def confirm_api_cleanup(server, listener, state) -> None:
    """After the original server loop and listener have returned, not a stop request."""
    lifespan = server.lifespan
    if (not state.ready or not state.lifespan_completed or not state.serve_completed
            or not server.started or server.force_exit or lifespan.error_occurred
            or lifespan.startup_failed or lifespan.shutdown_failed
            or listener.fileno() != -1 or server.server_state.connections
            or any(not task.done() for task in server.server_state.tasks)):
        raise EngineError('api_cleanup_incomplete',
                          'Native installation remains held until actual API cleanup', 503)


def installed_principal_id(held: StartupInstallation, *, engine: EngineService,
                           bundle: BundleService, role: StartupRole) -> str:
    """Nonsecret identity from the same actual, currently qualified services.

    This is a private ready descriptor value, never an execution capability.
    No renderer/record may choose it and no ordinary serve gets this identity.
    """
    if (type(held) is not StartupInstallation or held.closed or _retained.get(id(held)) is not held
            or bundle.engine is not engine or bundle.principals.instance_id != engine.instance_id
            or held.native.connection.context.role != role
            or held.native.connection.context.instance_id != engine.instance_id):
        raise EngineError('installed_services_binding_invalid', 'Ready requires the original installed Engine/Bundle/role', 503)
    services, actor = held.native.services, bundle.principals.owner()
    registered = services.execution_identity
    if (registered is None or engine.production_admissions is not services.admissions
            or engine.daily_projects is not services.daily_projects or services.daily_projects is None
            or engine._authorization_identity(actor.subject_id) is not registered
            or registered.owner_subject != actor.subject_id or registered.executing_principal_id != actor.subject_id
            or not actor.owned_projects):
        raise EngineError('installed_services_binding_invalid', 'Ready needs the actual mapped installed Owner and Daily service', 503)
    # Qualification/current Owner/registration/held resources remain mandatory.
    # Returning subject text does not install, renew or authenticate anything.
    with services.admissions.current_guard(registered):
        return actor.subject_id
