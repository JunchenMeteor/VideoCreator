"""Original native confirmation objects, separate from persisted provenance."""

import threading
from dataclasses import dataclass, field

from video_creator.domain.errors import EngineError
from video_creator.domain.owner_setup import OwnerSetupIntent, setup_sha256
from video_creator.infrastructure.native_owner_confirmation import (
    NativeOwnerConfirmationConnection,
)

_retained_consumers = {}


@dataclass(frozen=True, eq=False, repr=False)
class ConfirmedOwnerSetup:
    intent: OwnerSetupIntent
    intent_sha256: str
    _issuer: object = field(repr=False)
    _engine: object = field(repr=False)
    _epoch: object = field(repr=False)
    _thread_id: int = field(repr=False)
    _original: object = field(repr=False)


@dataclass(frozen=True, eq=False, repr=False)
class OwnerSetupPreparationSource:
    """Actual pre-API OS source, restricted to one honest draft preparation."""
    _issuer: object
    _engine: object
    _epoch: object
    _thread_id: int
    directory: object


class NativeOwnerConfirmationConsumer:
    """Only the fixed indexed Owner setup entry may assemble this consumer.

    Constructing a serialized source, a same-value object, a public API token or
    a caller-provided bool never enters this original issuer's member map.
    """

    def __init__(self, *, engine, bundle, startup_record, locator_bytes, initialization_source=None):
        if bundle.engine is not engine or startup_record.instance_id != engine.instance_id:
            raise EngineError('owner_setup_instance_denied', 'Confirmation requires original same Engine/Bundle', 403)
        self.engine, self.bundle, self.startup = engine, bundle, startup_record
        if initialization_source is not None:
            from video_creator.infrastructure.native_instance_source import _NativeInstanceSource

            if type(initialization_source) is not _NativeInstanceSource:
                raise EngineError('owner_instance_source_denied', 'Original concrete initialization source is required', 403)
            initialization_source.assert_setup_engine_current(engine)
        self._initialization_source = initialization_source
        self._epoch, self._lock = object(), threading.RLock()
        self._members, self._preparations, self._closed, self._started = {}, {}, False, False
        self._connection = NativeOwnerConfirmationConnection(instance_id=engine.instance_id,
            locator_bytes=locator_bytes, installation=startup_record.installation,
            external_receipt_path=startup_record.external_receipt_path,
            expected_host_image=startup_record.expected_host_image,
            expected_host_sha256=startup_record.expected_host_sha256)
        _retained_consumers[id(self)] = self

    def preparation_source(self) -> OwnerSetupPreparationSource:
        with self._lock:
            if self._closed or self._started or self._preparations:
                raise EngineError('owner_setup_preparation_denied', 'Original preparation is single-use', 403)
            if self._initialization_source is not None:
                self._initialization_source.assert_setup_engine_current(self.engine)
            self._connection.open_preparation(self.engine.db.data_dir)
            source = OwnerSetupPreparationSource(self, self.engine, self._epoch,
                threading.get_ident(), self._connection._directory)
            self._preparations[id(source)] = source
            return source

    def assert_preparation(self, source, *, local=False, connection=None):
        if (self._closed or type(source) is not OwnerSetupPreparationSource or source._issuer is not self
                or source._engine is not self.engine or source._epoch is not self._epoch
                or source._thread_id != threading.get_ident() or self._preparations.get(id(source)) is not source):
            raise EngineError('owner_setup_preparation_denied', 'Preparation requires the original OS source/thread', 403)
        if local:
            self._connection.assert_preparation_local_current()
            if self._initialization_source is not None:
                self._initialization_source.assert_setup_engine_local_current(self.engine, connection)
        else:
            self._connection.assert_preparation_current()
            if self._initialization_source is not None:
                self._initialization_source.assert_setup_engine_current(self.engine)

    def accept_setup(self, expected_intent: OwnerSetupIntent) -> ConfirmedOwnerSetup:
        with self._lock:
            if (self._started or self._closed or type(expected_intent) is not OwnerSetupIntent
                    or expected_intent.instance_id != self.engine.instance_id
                    or expected_intent.owner_subject != self.bundle.principals.owner_subject
                    or expected_intent.directory.path != str(self.engine.db.data_dir)
                    or not expected_intent.created_at_us <= self.engine.clock() < expected_intent.expires_at_us):
                raise EngineError('owner_setup_confirmation_denied', 'Only this original current prepared intent may be shown', 403)
            self._started = True
            original = self._connection.accept_setup(expected_intent)
            if self.engine.clock() >= expected_intent.expires_at_us:
                raise EngineError('owner_setup_expired', 'Intended setup interval expired during native confirmation', 403)
            confirmation = ConfirmedOwnerSetup(expected_intent, setup_sha256(expected_intent), self,
                self.engine, self._epoch, threading.get_ident(), original)
            self._members[id(confirmation)] = confirmation
            return confirmation

    def create_prepared_project(self, preparation, project, key):
        self.assert_preparation(preparation)
        owner = self.bundle.principals.owner_subject
        if self._initialization_source is None:
            return self.engine.create_project(owner, project, idempotency_key=key)
        return self.engine._create_project_for_setup(owner, project, key,
            initialization_source=self._initialization_source)

    def assert_initialization_local_current(self, connection):
        if self._initialization_source is not None:
            self._initialization_source.assert_setup_engine_local_current(self.engine, connection)

    def _original(self, confirmation):
        if (self._closed or type(confirmation) is not ConfirmedOwnerSetup or confirmation._issuer is not self
                or confirmation._engine is not self.engine or confirmation._epoch is not self._epoch
                or confirmation._thread_id != threading.get_ident()
                or self._members.get(id(confirmation)) is not confirmation
                or confirmation.intent is not confirmation._original.intent
                or self.engine.clock() >= confirmation.intent.expires_at_us):
            raise EngineError('owner_setup_confirmation_denied', 'Foreign/expired/closed/thread-changed confirmation is denied', 403)
        return confirmation._original

    def assert_current(self, confirmed: ConfirmedOwnerSetup) -> None:
        with self._lock:
            original = self._original(confirmed)
            if confirmed.intent_sha256 != setup_sha256(confirmed.intent):
                raise EngineError('owner_setup_confirmation_changed', 'Complete original intent changed', 409)
            self._connection.assert_current(original)
            if self._initialization_source is not None:
                self._initialization_source.assert_setup_engine_current(self.engine)

    def assert_local_current(self, confirmed: ConfirmedOwnerSetup, *, connection=None) -> None:
        if not self._lock.acquire(blocking=False):
            raise EngineError('owner_setup_source_busy', 'Original confirmation is in external validation', 503)
        try:
            self._connection.assert_local_current(self._original(confirmed))
            if self._initialization_source is not None:
                self._initialization_source.assert_setup_engine_local_current(self.engine, connection)
        finally:
            self._lock.release()

    def close(self, confirmed: ConfirmedOwnerSetup | None) -> None:
        with self._lock:
            if self._closed:
                return
            if confirmed is not None and (type(confirmed) is not ConfirmedOwnerSetup
                    or confirmed._issuer is not self or self._members.get(id(confirmed)) is not confirmed):
                raise EngineError('owner_setup_confirmation_denied', 'Cannot close a foreign setup source', 403)
            self._connection.close()
            self._members.clear()
            self._preparations.clear()
            self._closed = True
            del _retained_consumers[id(self)]
