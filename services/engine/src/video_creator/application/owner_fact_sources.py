"""Original OS-authenticated local facts root; never an execution/admin grant."""

import os
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass

from video_creator.application.engine import canonical
from video_creator.domain.errors import EngineError
from video_creator.infrastructure.held_authority import OwnedAuthorityConnection


@dataclass(frozen=True, eq=False, repr=False)
class LocalOwnerFactSource:
    owner_binding: object
    owner_body: str
    owner_generation: int
    database_identity: tuple[int, int]
    process_id: int
    thread_id: int
    expires_monotonic: float
    native_connection: object | None
    native_observation: object | None
    _store: object
    _engine: object
    _epoch: object


def _database_identity(store):
    path = store.engine.db.path
    if path.is_symlink() or path.is_junction() or not path.is_file():
        raise EngineError('owner_fact_source_invalid', 'Original instance metadata file is unavailable', 422)
    stat = path.stat()
    return stat.st_dev, stat.st_ino


@contextmanager
def local_owner_fact_source(store, *, native_connection=None):
    """Fixed bootstrap/installed startup only, before execution current checks.

    Actual OS ownership and original Control are necessary; no secret is read.
    The native variant additionally holds the original authenticated peer/facts.
    The OwnerControl lock outlives every subordinate ProductionControl context.
    """
    from video_creator.application.owner_bootstrap import OwnerBootstrapStore

    if type(store) is not OwnerBootstrapStore:
        raise EngineError('owner_fact_source_denied', 'Original same-instance bootstrap factory is required', 403)
    store.assert_current_directory()
    if native_connection is not None and (type(native_connection) is not OwnedAuthorityConnection
            or native_connection.context.instance_id != store.engine.instance_id):
        raise EngineError('owner_fact_source_denied', 'Native facts require the original same-instance authenticated connection', 403)
    observation = native_connection.observe_facts() if native_connection is not None else None
    if native_connection is not None:
        native_connection.assert_current_facts(observation)
    with store.control.locked(), store.engine.db.connect() as connection:
        record = store._read(connection)
        if record is None:
            raise EngineError('owner_not_initialized', 'Original local Owner facts are required', 503)
        generation = store.control.assert_revision(record.generation)
        if generation != record.generation:
            raise EngineError('owner_fact_source_invalid', 'Original Owner DB/floor generations differ', 422)
        actual_instance = connection.execute("SELECT value FROM metadata WHERE key='instance_id'").fetchone()
        if actual_instance is None or actual_instance[0] != store.engine.instance_id:
            raise EngineError('owner_fact_source_denied', 'Actual metadata instance differs from the original Engine', 403)
        source = LocalOwnerFactSource(record, canonical(record), generation, _database_identity(store),
            os.getpid(), threading.get_ident(), time.monotonic() + 30, native_connection, observation,
            store, store.engine, store._fact_epoch)
        store._fact_sources.add(source)
        try:
            assert_local_owner_fact_source(store, source)
            yield source
            assert_local_owner_fact_source(store, source)
        finally:
            store._fact_sources.discard(source)


def assert_local_owner_fact_source(store, source, *, connection=None):
    """With a writer connection: membership/epoch/cached exact rows only."""
    if (type(source) is not LocalOwnerFactSource or source._store is not store
            or source._engine is not store.engine or source._epoch is not store._fact_epoch
            or source not in store._fact_sources or source.process_id != os.getpid()
            or source.thread_id != threading.get_ident() or time.monotonic() >= source.expires_monotonic):
        raise EngineError('owner_fact_source_denied', 'Original live local Owner facts source/thread is required', 403)
    if source.native_connection is not None:
        source.native_connection.assert_local_observation(source.native_observation)
    if connection is not None:
        owner = connection.execute("SELECT value FROM metadata WHERE key='owner_management_binding'").fetchone()
        instance = connection.execute("SELECT value FROM metadata WHERE key='instance_id'").fetchone()
        if owner is None or owner[0] != source.owner_body or instance is None or instance[0] != store.engine.instance_id:
            raise EngineError('owner_fact_source_changed', 'Original local Owner/instance facts changed before completion', 409)
        return
    store.assert_current_directory()
    if _database_identity(store) != source.database_identity:
        raise EngineError('owner_fact_source_changed', 'Original metadata file identity changed', 409)
    if store.control.read().minimum_revision != source.owner_generation:
        raise EngineError('owner_fact_source_changed', 'Original Owner floor changed', 409)
    if source.native_connection is not None:
        source.native_connection.assert_current_facts(source.native_observation)
    with store.engine.db.connect() as reader:
        assert_local_owner_fact_source(store, source, connection=reader)
