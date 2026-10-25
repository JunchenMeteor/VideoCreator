"""Separate authenticated installation facts channel; never qualification."""

import json
import struct
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from video_creator.domain.errors import EngineError
from video_creator.domain.native_execution_registration import private_body_sha256
from video_creator.infrastructure.held_authority import (
    FRAME_LIMIT,
    HeldFileFact,
    _fields,
    _invalid,
    _json,
    _sha,
    _text,
    _uint,
)
from video_creator.infrastructure.windows_authority_pipe import (
    WindowsAuthorityPipe,
    open_owner_protected_native_build,
)

WIRE = 'native-installation-observer-v1'
_retained_connections = {}


def parse_installation_locator(data, instance_id):
    locator = _fields(_json(data), ('pipe', 'session', 'instance_id', 'role', 'server'))
    pipe = _text(locator['pipe'], limit=512)
    prefix = '\\\\.\\pipe\\VideoCreator-Install-'
    if (not pipe.startswith(prefix) or not pipe[len(prefix):]
            or any(char in pipe[len(prefix):] for char in ('\\', '/', ':'))):
        raise _invalid('Installation observer requires its exact local pipe family')
    _text(locator['session'], limit=128)
    if (locator['instance_id'], locator['role']) != (instance_id, 'owner-installation'):
        raise EngineError('installation_peer_denied', 'Installation observer instance or role differs', 403)
    server = _fields(locator['server'], ('pid', 'creation_filetime', 'sid', 'image', 'image_sha256'))
    if _uint(server['pid'], positive=True) > 0xFFFFFFFF:
        raise _invalid('Installation observer PID is invalid')
    _uint(server['creation_filetime'], positive=True)
    _text(server['sid'])
    _text(server['image'], limit=32768)
    _sha(server['image_sha256'])
    return locator


@dataclass(frozen=True, eq=False, repr=False)
class NativeInstallationFacts:
    observation_id: str
    observed_at_us: int
    files: tuple[HeldFileFact, ...]
    _epoch: object


class _HeldClose:
    """Unknown close contact retains the original object, without retry."""

    def __init__(self, original):
        self.original, self.contacted, self.confirmed = original, False, False
        self.error = None

    def close(self):
        if not self.contacted:
            self.contacted = True
            try:
                self.original.close()
                self.confirmed = True
            except BaseException as error:
                self.error = error
                raise
        if not self.confirmed:
            if self.error is not None:
                raise self.error
            raise EngineError('installation_channel_close_unknown', 'Original held file close is not confirmed', 503)


class NativeInstallationObserverConnection:
    """One original management view, retained before any OS contact.

    The expected host is an independent protected installer input. Locator and
    proposal hashes only compare identities; they never issue execution scope.
    """

    def __init__(self, *, installation, instance_id, locator_bytes, external_receipt_path,
                 expected_host_image, expected_host_sha256):
        self.installation, self.instance_id = installation, instance_id
        self.locator = parse_installation_locator(locator_bytes, instance_id)
        self.receipt_path, self.host_path = Path(external_receipt_path), Path(expected_host_image)
        if (str(self.host_path) != str(Path(installation.installed_native_image))
                or expected_host_sha256 != installation.installed_native_image_sha256):
            raise EngineError('installation_peer_denied', 'Independent host differs from the complete installation proposal', 403)
        self.host_sha256 = _sha(expected_host_sha256)
        self._inputs_sha256 = private_body_sha256(installation)
        self._epoch, self._lock = object(), threading.RLock()
        self._transport = self._host = self._receipt = None
        self._host_close = self._receipt_close = None
        self._observations, self._seq = {}, 0
        self._valid, self._opened, self._closed, self._view_close_contacted = False, False, False, False
        self._view_close_error = None
        _retained_connections[id(self)] = self

    @staticmethod
    def _deadline(deadline):
        if time.monotonic() >= deadline:
            raise EngineError('installation_channel_timeout', 'Installation observation exceeded its absolute deadline', 503)

    def open(self):
        with self._lock:
            if self._opened or self._closed:
                raise EngineError('installation_connection_invalid', 'Original installation view cannot reconnect', 503)
            self._opened = True
            deadline = time.monotonic() + 20
            try:
                self._host = open_owner_protected_native_build(image_path=self.host_path, expected_sha256=self.host_sha256)
                self._host_close = _HeldClose(self._host)
                self._deadline(deadline)
                self._receipt = open_owner_protected_native_build(image_path=self.receipt_path,
                    expected_sha256=self.installation.build_receipt_sha256)
                self._receipt_close = _HeldClose(self._receipt)
                receipt_bytes = json.dumps(self.installation.build_receipt.model_dump(mode='json'),
                    ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
                if (self._host.file_identity[2] != self.installation.installed_native_image_bytes
                        or self._receipt.file_identity[2] != len(receipt_bytes) or len(receipt_bytes) > FRAME_LIMIT):
                    raise _invalid('Actual host or canonical external receipt has a different complete size')
                self._deadline(deadline)
                self._transport = WindowsAuthorityPipe(pipe_name=self.locator['pipe'], server=self.locator['server'],
                    trusted_build=self._host, startup_deadline=deadline)
                self._valid = True
                self._exchange('bind', deadline=min(deadline, time.monotonic() + 10),
                    installation_inputs_sha256=self._inputs_sha256)
            except BaseException:
                self._valid = False
                raise

    def _local(self):
        # No OS calls, hashes or RPC in the short writer hook.
        if (not self._valid or self._closed or self._transport is None or self._transport.invalid
                or self._host is None or self._receipt is None or self._host._closed or self._receipt._closed):
            raise EngineError('installation_connection_invalid', 'Original installation view is invalid', 503)

    def _reply(self, data, method):
        reply = _fields(_json(data), ('wire', 'session', 'seq', 'status', 'code',
            'installation_inputs_sha256', 'observation_id', 'observed_at_us', 'host_image',
            'build_receipt_file', 'payload_files', 'qualification'))
        _uint(reply['seq'])
        _uint(reply['status'])
        _text(reply['code'])
        if ((reply['wire'], reply['session'], reply['seq'], _sha(reply['installation_inputs_sha256'])) != (
                WIRE, self.locator['session'], self._seq, self._inputs_sha256)
                or reply['qualification'] != 'not_ready'):
            raise _invalid('Installation reply differs from the original identity or claims unadmitted qualification')
        code = {'bind': 'bound_facts_only', 'observe': 'observed_facts_only',
            'assert_current': 'current_facts_only', 'close': 'view_closed_native_ownership_retained'}[method]
        if reply['status'] != 200 or reply['code'] != code:
            raise _invalid('Installation observer returned an unsupported method result')
        if type(reply['payload_files']) is not list:
            raise _invalid('Installation payload must be its complete ordered array')
        files = tuple(HeldFileFact(**_fields(raw, ('relative_path', 'bytes', 'sha256')))
            for raw in reply['payload_files'])
        if method == 'observe':
            _text(reply['observation_id'], limit=128)
            _uint(reply['observed_at_us'], positive=True)
            for field, held, size, sha in (
                ('host_image', self._host, self.installation.installed_native_image_bytes, self.host_sha256),
                ('build_receipt_file', self._receipt, self._receipt.file_identity[2], self.installation.build_receipt_sha256)):
                fact = _fields(reply[field], ('path', 'bytes', 'sha256'))
                _text(fact['path'], limit=32768)
                # Rust canonical paths can carry the validated extended-drive
                # spelling. Match the actual independently held file identity,
                # without accepting arbitrary UNC/aliases or text-only trust.
                held.assert_image_path(fact['path'])
                if (_uint(fact['bytes']), _sha(fact['sha256'])) != (size, sha):
                    raise _invalid('Actual original host or external receipt identity differs')
            if files != self.installation.expected_files:
                raise _invalid('Actual installation payload differs from the whole original map')
        elif (files or any(reply[name] is not None for name in (
                'observation_id', 'observed_at_us', 'host_image', 'build_receipt_file'))):
            raise _invalid('Installation method contains unexpected observation facts')
        return reply, files

    def _exchange(self, method, *, deadline=None, **arguments):
        self._local()
        deadline = time.monotonic() + 10 if deadline is None else deadline
        try:
            self._deadline(deadline)
            self._host.assert_current()
            self._receipt.assert_current()
            self._transport.assert_peer()
            self._deadline(deadline)
            request = dict(method=method, wire=WIRE, session=self.locator['session'], seq=self._seq, **arguments)
            data = json.dumps(request, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
            if not 1 <= len(data) <= FRAME_LIMIT:
                raise _invalid('Private installation request exceeds its complete frame bound')
            self._transport.write_all(struct.pack('<I', len(data)) + data, deadline=deadline)
            size = struct.unpack('<I', self._transport.read_exact(4, deadline=deadline))[0]
            if not 1 <= size <= FRAME_LIMIT:
                raise _invalid('Private installation reply exceeds its complete frame bound')
            reply, files = self._reply(self._transport.read_exact(size, deadline=deadline), method)
            self._transport.assert_peer()
            self._receipt.assert_current()
            self._deadline(deadline)
            if self._seq == 0xFFFFFFFFFFFFFFFF:
                raise _invalid('Installation sequence is exhausted')
            self._seq += 1
            return reply, files
        except BaseException:
            self._valid = False
            raise

    def observe(self):
        with self._lock:
            reply, files = self._exchange('observe')
            key = reply['observation_id']
            if key in self._observations:
                self._valid = False
                raise _invalid('Installation observer revived an original observation ID')
            observation = NativeInstallationFacts(key, reply['observed_at_us'], files, self._epoch)
            self._observations[key] = observation
            return observation

    def assert_local_current(self, observation):
        if not self._lock.acquire(blocking=False):
            raise EngineError('installation_session_busy', 'Installation view is in external observation', 503)
        try:
            self._local()
            if (type(observation) is not NativeInstallationFacts or observation._epoch is not self._epoch
                    or self._observations.get(observation.observation_id) is not observation):
                raise EngineError('installation_observation_denied', 'Exact original installation observation is required', 409)
        finally:
            self._lock.release()

    def assert_current(self, observation):
        with self._lock:
            self.assert_local_current(observation)
            self._exchange('assert_current', observation_id=observation.observation_id)

    def close(self):
        with self._lock:
            if self._closed:
                return
            # Contacted-but-unconfirmed view close is never resubmitted. Physical
            # pipe close resumes only the transport's original retained I/O.
            primary = self._view_close_error
            try:
                if primary is not None:
                    raise primary
                if self._valid and not self._view_close_contacted:
                    self._view_close_contacted = True
                    key = next(iter(self._observations), None)
                    self._exchange('close', observation_id=key)
            except BaseException as error:
                primary = error
                self._view_close_error = error
                raise
            finally:
                self._valid = False
                try:
                    if self._transport is not None:
                        self._transport.close()
                    for retained in (self._receipt_close, self._host_close):
                        if retained is not None:
                            retained.close()
                except BaseException as error:
                    if primary is not None:
                        raise primary from error
                    raise
            self._closed = True
            self._observations.clear()
            del _retained_connections[id(self)]
