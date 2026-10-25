"""Closed pre-instance Windows peer binding, without installation authority."""

import ctypes
import os
import struct
import time
from pathlib import Path

from video_creator.cli.native_instance_protocol import (
    PEER_WIRE,
    parse_bootstrap_locator,
    parse_peer_reply,
)
from video_creator.domain.errors import EngineError
from video_creator.infrastructure.held_authority import _json
from video_creator.infrastructure.native_owner_confirmation import canonical_wire
from video_creator.infrastructure.owner_identity import inspect_owner_directory
from video_creator.infrastructure.windows_authority_pipe import (
    WindowsAuthorityPipe,
    open_owner_protected_native_build,
)

# Hold the actual connection and original files to this indexed child's exit.
# Completing identity/bind does not close resources still held by Native/Job.
_retained_sources = {}


def assert_deadline(deadline):
    if time.monotonic() >= deadline:
        raise EngineError('owner_instance_handshake_timeout', 'Original initialization deadline elapsed', 503)


def _source_error(error):
    if error.code.startswith('owner_instance_'):
        return error
    code, status = {
        403: ('owner_instance_source_denied', 403),
        409: ('owner_instance_binding_changed', 409),
    }.get(error.status_code, ('owner_instance_source_unavailable', 503))
    if error.code == 'installation_channel_timeout':
        code, status = 'owner_instance_handshake_timeout', 503
    return EngineError(code, 'Original held initialization source is unavailable or changed', status)


class _NativeInstanceSource:
    """Only this closed factory's actual OS contact may bind one Engine."""

    def __init__(self, record, data_dir, deadline):
        self.record, self.data_dir, self.deadline = record, Path(data_dir), deadline
        self.locator = parse_bootstrap_locator(_json(record.bootstrap_locator_bytes))
        self.directory = self.host = self.receipt = self.transport = None
        self.child_identity = self.gui_session_id = None
        self._bound = self._disabled = False
        self._setup_bound = False
        self._engine = self._database = self._instance_id = self._database_identity = None
        _retained_sources[id(self)] = self

    def _open(self):
        if os.name != 'nt':
            raise EngineError('owner_instance_source_unavailable', 'Actual platform peer producer is not implemented', 503)
        try:
            assert_deadline(self.deadline)
            # Root already exists and is protected by the original Guardian.
            # No Engine/Database construction can precede this actual check.
            self.directory = inspect_owner_directory(self.data_dir)
            self.host = open_owner_protected_native_build(
                image_path=Path(self.record.expected_host_image), expected_sha256=self.record.expected_host_sha256)
            self.receipt = open_owner_protected_native_build(image_path=Path(self.record.external_receipt_path),
                expected_sha256=self.record.installation.build_receipt_sha256)
            receipt_bytes = canonical_wire(self.record.installation.build_receipt.model_dump(mode='json'))
            if (self.host.owner.os_subject != self.directory.os_subject
                    or self.receipt.owner.os_subject != self.directory.os_subject
                    or self.host.file_identity[2] != self.record.installation.installed_native_image_bytes
                    or self.receipt.file_identity[2] != len(receipt_bytes)):
                raise EngineError('owner_instance_source_denied', 'Actual original Owner or held files differ', 403)
            assert_deadline(self.deadline)
            self.transport = WindowsAuthorityPipe(pipe_name=self.locator['pipe'], server=self.locator['server'],
                trusted_build=self.host, startup_deadline=self.deadline)
            api = self.transport.api
            creation, sid, image = api.process_identity(api.kernel.GetCurrentProcess())
            self.child_identity = (os.getpid(), creation, sid, image)
            session, peer_session = ctypes.c_ulong(), ctypes.c_ulong()
            native = api.kernel.ProcessIdToSessionId
            native.argtypes, native.restype = [ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong)], ctypes.c_int
            if (not native(os.getpid(), ctypes.byref(session)) or session.value == 0
                    or not native(self.locator['server']['pid'], ctypes.byref(peer_session))
                    or session.value != peer_session.value or sid != self.directory.os_subject):
                raise EngineError('owner_instance_source_denied', 'Original peer requires the same actual GUI Owner session', 403)
            self.gui_session_id = session.value
            self._assert_os_current()
            exchange_deadline = min(self.deadline, time.monotonic() + 10)
            request = canonical_wire({'wire': PEER_WIRE, 'session': self.locator['session'], 'seq': 1, 'method': 'bind'})
            self.transport.write_all(struct.pack('<I', len(request)) + request, deadline=exchange_deadline)
            size = struct.unpack('<I', self.transport.read_exact(4, deadline=exchange_deadline))[0]
            if not 0 < size <= 16 * 1024:
                raise EngineError('owner_instance_handshake_limit', 'Initialization peer reply exceeds its frame', 413)
            parse_peer_reply(self.transport.read_exact(size, deadline=exchange_deadline), self.locator['session'])
            self._assert_os_current()
            assert_deadline(self.deadline)
            self._bound = True
            return self
        except EngineError as error:
            self._disabled = True
            mapped = _source_error(error)
            if mapped is error:
                raise
            raise mapped from error
        except BaseException:
            self._disabled = True
            raise

    def _assert_os_current(self):
        if (self._disabled or _retained_sources.get(id(self)) is not self
                or self.transport is None or self.host is None or self.receipt is None):
            raise EngineError('owner_instance_source_unavailable', 'Original initialization source is unavailable', 503)
        if inspect_owner_directory(self.data_dir) != self.directory:
            raise EngineError('owner_instance_binding_changed', 'Original Owner directory changed', 409)
        self.host.assert_current()
        self.receipt.assert_current()
        self.transport.assert_peer()
        api = self.transport.api
        creation, sid, image = api.process_identity(api.kernel.GetCurrentProcess())
        if (os.getpid(), creation, sid, image) != self.child_identity:
            raise EngineError('owner_instance_binding_changed', 'Original indexed child identity changed', 409)
        session, peer = ctypes.c_ulong(), ctypes.c_ulong()
        if (not api.kernel.ProcessIdToSessionId(os.getpid(), ctypes.byref(session))
                or not api.kernel.ProcessIdToSessionId(self.locator['server']['pid'], ctypes.byref(peer))
                or session.value != self.gui_session_id or peer.value != self.gui_session_id):
            raise EngineError('owner_instance_binding_changed', 'Original GUI Owner session changed', 409)

    def assert_current(self):
        if not self._bound:
            raise EngineError('owner_instance_source_unavailable', 'Original peer binding has not completed', 503)
        try:
            self._assert_os_current()
        except EngineError as error:
            self._disabled = True
            mapped = _source_error(error)
            if mapped is error:
                raise
            raise mapped from error

    def retain_engine(self, engine):
        # A concrete same Engine object, never a caller-supplied identity/DB map.
        from video_creator.application.engine import EngineService

        self.assert_current()
        assert_deadline(self.deadline)
        if (type(engine) is not EngineService or self._engine is not None
                or engine.db.data_dir != self.data_dir):
            raise EngineError('owner_instance_binding_changed', 'Original Engine/root association differs', 409)
        self._engine, self._database, self._instance_id = engine, engine.db, engine.instance_id
        self._database_identity = self._database_stat(engine.db.path)
        self.assert_engine_current(engine)

    @staticmethod
    def _database_stat(path):
        if path.is_symlink() or path.is_junction() or not path.is_file():
            raise EngineError('owner_instance_binding_changed', 'Original database file changed', 409)
        info = path.stat()
        return info.st_dev, info.st_ino

    def assert_engine_current(self, engine):
        self.assert_current()
        if not self._setup_bound:
            assert_deadline(self.deadline)
        if (engine is not self._engine or engine.db is not self._database or engine.instance_id != self._instance_id
                or engine.db.data_dir != self.data_dir
                or self._database_stat(engine.db.path) != self._database_identity):
            raise EngineError('owner_instance_binding_changed', 'Original Engine/database/root changed', 409)
        # Short original connection; never INSERT/recreate a missing identity.
        with engine.db.connect() as connection:
            row = connection.execute("SELECT value FROM metadata WHERE key='instance_id'").fetchone()
        if row is None or row[0] != self._instance_id:
            raise EngineError('owner_instance_binding_changed', 'Original persisted instance identity changed', 409)
        self.assert_current()
        if self._database_stat(engine.db.path) != self._database_identity:
            raise EngineError('owner_instance_binding_changed', 'Original database changed during its identity read', 409)
        if not self._setup_bound:
            assert_deadline(self.deadline)

    def complete_setup_binding(self, engine):
        if self._setup_bound:
            raise EngineError('owner_instance_binding_changed', 'Original setup binding cannot complete twice', 409)
        self.assert_engine_current(engine)
        self._setup_bound = True

    def assert_setup_engine_current(self, engine):
        if not self._setup_bound:
            raise EngineError('owner_instance_source_unavailable', 'Original setup binding has not completed', 503)
        self.assert_engine_current(engine)

    def assert_setup_engine_local_current(self, engine, connection=None):
        """Original short writer: local handles/file and same-connection row."""
        if (not self._setup_bound or self._disabled or not self._bound
                or _retained_sources.get(id(self)) is not self
                or engine is not self._engine or engine.db is not self._database
                or engine.instance_id != self._instance_id or engine.db.data_dir != self.data_dir
                or self._database_stat(engine.db.path) != self._database_identity):
            raise EngineError('owner_instance_binding_changed', 'Original setup Engine/database binding changed', 409)
        self.transport.assert_local_current()
        if connection is not None:
            row = connection.execute("SELECT value FROM metadata WHERE key='instance_id'").fetchone()
            if row is None or row[0] != self._instance_id:
                raise EngineError('owner_instance_binding_changed', 'Original writer instance identity changed', 409)
            if self._database_stat(engine.db.path) != self._database_identity:
                raise EngineError('owner_instance_binding_changed', 'Original database changed during writer validation', 409)

    def disable(self):
        # Retain originals until actual process exit. No reconnect/early close.
        self._disabled = True


def open_instance_source(record, data_dir, *, deadline):
    from video_creator.cli.native_instance_protocol import NativeInstanceInitializationRecord

    if type(record) is not NativeInstanceInitializationRecord:
        raise EngineError('owner_instance_source_denied', 'Original typed initialization is required', 403)
    return _NativeInstanceSource(record, data_dir, deadline)._open()
