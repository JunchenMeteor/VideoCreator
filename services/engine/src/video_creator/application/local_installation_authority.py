"""Ordinary production from original held objects; never independent qualification."""
import threading

from video_creator.application.production_admissions import InstalledProductionEvidence
from video_creator.domain.errors import EngineError
from video_creator.infrastructure.held_authority import NativeLaunchContext, OwnedAuthorityConnection
from video_creator.infrastructure.windows_authority_pipe import OwnerProtectedNativeBuild

_FACTORY = object()
_retained_authorities = {}


class LocalInstallationAuthority:
    def __init__(self, token, *, connection=None, build=None, observer=None, observation=None):
        if token is not _FACTORY:
            raise EngineError('installation_observation_denied', 'Original local factory is required.', 403)
        self._connection, self._build = connection, build
        self._observer, self._observation = observer, observation
        self._lock, self._epoch = threading.RLock(), object()
        self._originals, self._retired, self._closed = {}, False, False
        _retained_authorities[id(self)] = self

    def _context(self):
        if self._connection is not None:
            return self._connection.context
        installation = self._observation.installation
        return NativeLaunchContext(self._observation.instance_id, 'api',
            installation.registration_sha256, installation.resource_manifest_sha256,
            installation.runtime_manifest_sha256, installation.expected_files, installation.engine_file_names)

    def _local_source(self, facts):
        if self._retired or self._closed or _retained_authorities.get(id(self)) is not self:
            raise EngineError('installation_connection_invalid', 'Original local authority is retired.', 503)
        if self._connection is not None:
            if self._build._closed:
                raise EngineError('installation_connection_invalid', 'Original native build is closed.', 503)
            self._connection.assert_local_observation(facts)
        else:
            self._observer.assert_local_current(self._observation)
            if self._observer._original(self._observation) is not facts:
                raise EngineError('installation_observation_denied', 'Original retained facts changed.', 409)

    def _full_source(self, facts):
        self._local_source(facts)
        if self._connection is not None:
            self._build.assert_current()
            self._connection.assert_current_facts(facts)
        else:
            self._observer.assert_current(self._observation)
        self._local_source(facts)

    def observe(self):
        with self._lock:
            if self._retired or self._closed:
                raise EngineError('installation_connection_invalid', 'Original local authority is retired.', 503)
            facts = (self._connection.observe_facts() if self._connection is not None
                     else self._observer._original(self._observation))
            self._full_source(facts)
            context = self._context()
            actual = tuple(sorted(facts.files, key=lambda item: item.relative_path))
            expected = tuple(sorted(context.expected_files, key=lambda item: item.relative_path))
            if actual != expected:
                raise EngineError('installation_peer_denied', 'Complete held map differs.', 403)
            names = set(context.engine_file_names)
            evidence = InstalledProductionEvidence(context.instance_id, context.registration_sha256,
                context.resource_manifest_sha256, context.runtime_manifest_sha256,
                'registered-media-bundle-v1', 'registered-production-drivers-v1', facts.observed_at_us,
                tuple((item.relative_path, item.sha256) for item in actual if item.relative_path in names),
                tuple((item.relative_path, item.sha256) for item in actual if item.relative_path not in names))
            self._originals[id(evidence)] = (evidence, facts, self._epoch, threading.get_ident())
            return evidence

    def _original(self, evidence):
        original = self._originals.get(id(evidence))
        if (type(evidence) is not InstalledProductionEvidence or original is None
                or original[0] is not evidence or original[2] is not self._epoch
                or original[3] != threading.get_ident()):
            raise EngineError('installation_observation_denied', 'Exact current-thread local evidence is required.', 409)
        self._local_source(original[1])
        return original[1]

    def assert_current(self, evidence):
        with self._lock:
            self._full_source(self._original(evidence))

    def assert_local_current(self, evidence):
        # Writer: no hashing/RPC/new observation/file open/blocking lock.
        if not self._lock.acquire(blocking=False):
            raise EngineError('installation_session_busy', 'Local authority is in external observation.', 503)
        try:
            self._original(evidence)
        finally:
            self._lock.release()

    def close(self):
        with self._lock:
            if self._closed:
                return
            self._retired = True
            self._originals.clear()
            if self._connection is not None:
                self._connection.close()
            # Setup observer owns its own actual host/receipt/transport closure.
            _retained_authorities.pop(id(self), None)
            self._closed = True


def local_authority_from_connection(*, connection, build):
    if (type(connection) is not OwnedAuthorityConnection or type(build) is not OwnerProtectedNativeBuild
            or connection._transport is None or connection._transport.build is not build or build._closed):
        raise EngineError('installation_peer_denied', 'Exact held ordinary connection/build are required.', 403)
    connection.assert_local_current()
    build.assert_current()
    return LocalInstallationAuthority(_FACTORY, connection=connection, build=build)


def local_authority_from_observer(*, observer, observation):
    from video_creator.application.native_execution_observer import NativeExecutionObserver, _retained_observers
    from video_creator.application.native_execution_installation import RetainedNativeInstallation
    if (type(observer) is not NativeExecutionObserver or _retained_observers.get(id(observer)) is not observer
            or type(observation) is not RetainedNativeInstallation or observation._issuer is not observer
            or observation._held_owner is not observer._connection):
        raise EngineError('installation_observation_denied', 'Exact retained observer is required.', 403)
    observer.assert_current(observation)
    return LocalInstallationAuthority(_FACTORY, observer=observer, observation=observation)
