"""Concrete Owner installation facts adapter, separate from execution issuer."""

import threading

from video_creator.application.native_execution_installation import (
    RetainedNativeInstallation,
)
from video_creator.application.owner_bootstrap import OwnerBindingRecord
from video_creator.domain.errors import EngineError
from video_creator.infrastructure.native_installation_observer import (
    NativeInstallationObserverConnection,
)

_retained_observers = {}


class NativeExecutionObserver:
    """Trusted same-instance factory result; construction performs no OS I/O."""

    def __init__(self, *, engine, bootstrap, authorization, installation, instance_id,
                 locator_bytes, external_receipt_path, expected_host_image, expected_host_sha256):
        if (engine.instance_id != instance_id or bootstrap.engine is not engine
                or authorization.engine is not engine):
            raise EngineError('native_startup_binding_denied', 'Installation factory differs from the original instance services', 403)
        self.engine, self.bootstrap, self.authorization = engine, bootstrap, authorization
        self.installation = installation
        self._connection = NativeInstallationObserverConnection(installation=installation, instance_id=instance_id,
            locator_bytes=locator_bytes, external_receipt_path=external_receipt_path,
            expected_host_image=expected_host_image, expected_host_sha256=expected_host_sha256)
        self._lock, self._originals, self._started, self._closed = threading.RLock(), {}, False, False
        _retained_observers[id(self)] = self

    def observe(self, installation, *, owner_binding: OwnerBindingRecord):
        with self._lock:
            if self._started or self._closed or installation != self.installation:
                raise EngineError('installation_observation_denied', 'The original one-shot installation input is required', 409)
            self._started = True
            # Release the actual Owner Control before full file/peer/RPC work.
            with self.bootstrap.current() as current:
                if current != owner_binding:
                    raise EngineError('production_management_denied', 'Actual Owner binding changed before installation observation', 403)
                binding = current
            self._connection.open()
            if (self._connection._host.owner.os_subject != binding.os_subject
                    or self._connection._receipt.owner.os_subject != binding.os_subject):
                raise EngineError('installation_peer_denied', 'Held installation files differ from the actual OS Owner', 403)
            facts = self._connection.observe()
            # A changed Owner cannot authorize an observation issued across its
            # confirmation window. No management credential reaches the pipe.
            with self.bootstrap.current() as current:
                if current != binding:
                    raise EngineError('production_management_denied', 'Actual Owner binding changed during installation observation', 403)
            principal = binding.principal
            observation = RetainedNativeInstallation(installation, self.engine.instance_id,
                principal.owner_subject, binding.generation, binding.action_id, principal.authentication_binding_id,
                binding.os_subject, binding.directory_device, binding.directory_inode, facts.observed_at_us,
                self, self._connection)
            self._originals[id(observation)] = (observation, facts)
            return observation

    def _original(self, observation):
        pair = self._originals.get(id(observation))
        if (self._closed or type(observation) is not RetainedNativeInstallation or observation._issuer is not self
                or observation._held_owner is not self._connection or pair is None or pair[0] is not observation):
            raise EngineError('installation_observation_denied', 'Exact original retained installation object is required', 409)
        self._connection.assert_local_current(pair[1])
        return pair[1]

    def assert_current(self, observation):
        with self._lock:
            facts = self._original(observation)
            self._connection.assert_current(facts)

    def production_authority(self, original_observation):
        """Original ordinary installation facts, never a qualification issuer."""
        from video_creator.application.local_installation_authority import local_authority_from_observer
        with self._lock:
            self._original(original_observation)
            return local_authority_from_observer(observer=self, observation=original_observation)

    def assert_local_current(self, observation):
        if not self._lock.acquire(blocking=False):
            raise EngineError('installation_session_busy', 'Installation adapter is in external observation', 503)
        try:
            self._original(observation)
        finally:
            self._lock.release()

    def close(self, observation):
        with self._lock:
            if self._closed:
                return
            if observation is not None:
                pair = self._originals.get(id(observation))
                if pair is None or pair[0] is not observation or observation._issuer is not self:
                    raise EngineError('installation_observation_denied', 'Cannot close a foreign installation view', 409)
            self._connection.close()
            self._closed = True
            self._originals.clear()
            del _retained_observers[id(self)]


class NativeExecutionObserverFactory:
    """Only the fixed indexed management startup constructs this callable."""

    def __init__(self, *, installation, instance_id, locator_bytes, external_receipt_path,
                 expected_host_image, expected_host_sha256):
        self._arguments = {'installation': installation, 'instance_id': instance_id, 'locator_bytes': locator_bytes,
            'external_receipt_path': external_receipt_path, 'expected_host_image': expected_host_image,
            'expected_host_sha256': expected_host_sha256}

    def __call__(self, *, engine, bootstrap, authorization):
        return NativeExecutionObserver(engine=engine, bootstrap=bootstrap, authorization=authorization, **self._arguments)
