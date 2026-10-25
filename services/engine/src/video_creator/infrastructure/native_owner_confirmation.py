"""One authenticated native Owner dialog channel, never a public approval API."""

import ctypes
import json
import os
import struct
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from video_creator.domain.errors import EngineError
from video_creator.domain.owner_setup import (
    SETUP_FRAME_LIMIT,
    NativeSetupConfirmationOrigin,
    OwnerSetupIntent,
    setup_sha256,
)
from video_creator.infrastructure.held_authority import (
    _fields,
    _json,
    _sha,
    _text,
    _uint,
)
from video_creator.infrastructure.native_installation_observer import _HeldClose
from video_creator.infrastructure.owner_identity import inspect_owner_directory
from video_creator.infrastructure.windows_authority_pipe import (
    WindowsAuthorityPipe,
    open_owner_protected_native_build,
)

WIRE = 'native-owner-setup-confirmation-v1'
_retained_connections = {}


def invalid(message):
    return EngineError('owner_setup_wire_invalid', message, 422)


def canonical_wire(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                      allow_nan=False).encode('utf-8')


def parse_confirmation_locator(data: bytes, instance_id: str):
    raw = _fields(_json(data), ('pipe', 'session', 'instance_id', 'role', 'server'))
    if canonical_wire(raw) != data:
        raise invalid('Owner setup locator requires exact canonical UTF8')
    prefix = '\\\\.\\pipe\\VideoCreator-OwnerSetup-'
    pipe = _text(raw['pipe'], limit=512)
    if (not pipe.startswith(prefix) or not pipe[len(prefix):]
            or any(value in pipe[len(prefix):] for value in ('\\', '/', ':'))):
        raise invalid('Owner setup requires its independent local pipe family')
    _text(raw['session'], limit=128)
    if (raw['instance_id'], raw['role']) != (instance_id, 'owner-setup'):
        raise EngineError('owner_setup_source_denied', 'Owner setup instance or role differs', 403)
    server = _fields(raw['server'], ('pid', 'creation_filetime', 'sid', 'image', 'image_sha256'))
    if _uint(server['pid'], positive=True) > 0xFFFFFFFF:
        raise invalid('Actual Owner setup peer PID is invalid')
    _uint(server['creation_filetime'], positive=True)
    _text(server['sid'], limit=200)
    _text(server['image'], limit=32768)
    _sha(server['image_sha256'])
    return raw


@dataclass(frozen=True, eq=False, repr=False)
class RetainedSetupConfirmation:
    intent: OwnerSetupIntent
    intent_sha256: str
    source: NativeSetupConfirmationOrigin
    deadline_monotonic: float
    _epoch: object


class NativeOwnerConfirmationConnection:
    """Strong original ownership precedes OS contact and any ambiguous take."""

    def __init__(self, *, instance_id, locator_bytes, expected_host_image, expected_host_sha256,
                 external_receipt_path, installation):
        self.instance_id = instance_id
        self.locator = parse_confirmation_locator(locator_bytes, instance_id)
        self.host_path, self.receipt_path = Path(expected_host_image), Path(external_receipt_path)
        self.host_sha = _sha(expected_host_sha256)
        self.installation = installation
        if (str(self.host_path), self.host_sha) != (
                installation.installed_native_image, installation.installed_native_image_sha256):
            raise EngineError('owner_setup_source_denied', 'Independent host differs from original installation', 403)
        self._host = self._receipt = self._transport = None
        self._host_close = self._receipt_close = None
        self._lock, self._epoch = threading.RLock(), object()
        self._valid = self._opened = self._closed = self._taken = False
        self._close_contacted, self._close_error = False, None
        self._seq, self._intent, self._original, self._challenge = 0, None, None, None
        self._directory = self._directory_path = self._child_identity = None
        self._gui_session_id = None
        _retained_connections[id(self)] = self

    @staticmethod
    def _deadline(deadline):
        if time.monotonic() >= deadline:
            raise EngineError('owner_setup_timeout', 'Original setup exchange or confirmation expired', 403)

    def open_preparation(self, data_dir):
        """Authenticate the original OS source, without presenting/confirming.

        This phase can save one honest draft. It sends no approval RPC and
        provides neither a management capability nor a production identity.
        """
        with self._lock:
            if self._transport is not None or self._opened or self._closed:
                raise EngineError('owner_setup_replay', 'Original preparation cannot reopen', 409)
            self._directory_path = Path(data_dir)
            deadline = time.monotonic() + 20
            try:
                self._directory = inspect_owner_directory(self._directory_path)
                self._host = open_owner_protected_native_build(image_path=self.host_path, expected_sha256=self.host_sha)
                self._host_close = _HeldClose(self._host)
                self._receipt = open_owner_protected_native_build(image_path=self.receipt_path,
                    expected_sha256=self.installation.build_receipt_sha256)
                self._receipt_close = _HeldClose(self._receipt)
                expected_receipt = canonical_wire(self.installation.build_receipt.model_dump(mode='json'))
                if (self._host.owner.os_subject != self._directory.os_subject
                        or self._receipt.owner.os_subject != self._directory.os_subject
                        or self._host.file_identity[2] != self.installation.installed_native_image_bytes
                        or self._receipt.file_identity[2] != len(expected_receipt)):
                    raise EngineError('owner_setup_source_denied', 'Original held files differ from actual OS Owner/full size', 403)
                self._deadline(deadline)
                self._transport = WindowsAuthorityPipe(pipe_name=self.locator['pipe'], server=self.locator['server'],
                    trusted_build=self._host, startup_deadline=deadline)
                creation, sid, _image = self._transport.api.process_identity(self._transport.api.kernel.GetCurrentProcess())
                self._child_identity = (os.getpid(), creation, sid)
                session = ctypes.c_ulong()
                native = self._transport.api.kernel.ProcessIdToSessionId
                native.argtypes, native.restype = [ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong)], ctypes.c_int
                if not native(os.getpid(), ctypes.byref(session)) or session.value == 0:
                    raise EngineError('owner_setup_source_denied', 'Native setup requires the actual interactive OS session', 403)
                peer_session = ctypes.c_ulong()
                if (not native(self.locator['server']['pid'], ctypes.byref(peer_session))
                        or peer_session.value != session.value or sid != self._directory.os_subject):
                    raise EngineError('owner_setup_source_denied', 'Original host and child require the same actual OS GUI Owner session', 403)
                self._gui_session_id = 'windows-session-' + str(session.value)
                self._valid = True
                self.assert_preparation_current()
                self._deadline(deadline)
            except BaseException:
                self._valid = False
                raise

    def assert_preparation_current(self):
        with self._lock:
            self._local()
            if inspect_owner_directory(self._directory_path) != self._directory:
                raise EngineError('owner_setup_source_denied', 'Original preparation directory changed', 403)
            self._host.assert_current()
            self._receipt.assert_current()
            self._transport.assert_peer()

    def assert_preparation_local_current(self):
        self._local()

    def open(self, intent):
        with self._lock:
            if self._opened or self._closed or type(intent) is not OwnerSetupIntent:
                raise EngineError('owner_setup_replay', 'Original setup connection cannot reopen', 409)
            if self._transport is None:
                self.open_preparation(Path(intent.directory.path))
            self._opened, self._intent = True, intent
            if ((intent.instance_id, intent.installation, intent.expected_host_image,
                    intent.expected_host_sha256, intent.external_receipt_path) != (self.instance_id,
                    self.installation, str(self.host_path), self.host_sha, str(self.receipt_path))):
                raise EngineError('owner_setup_source_denied', 'Complete intent differs from original protected startup', 403)
            deadline = time.monotonic() + 20
            try:
                if self._directory_path != Path(intent.directory.path):
                    raise EngineError('owner_setup_source_denied', 'Intent differs from the original prepared directory', 403)
                self._assert_directory()
                self.assert_preparation_current()
                self._exchange('bind', deadline=min(deadline, time.monotonic() + 10))
            except BaseException:
                self._valid = False
                raise

    def _assert_directory(self):
        actual = inspect_owner_directory(Path(self._intent.directory.path))
        expected = self._intent.directory
        if (actual != self._directory or (actual.os_subject, actual.administrator_id,
                actual.directory_device, actual.directory_inode) != (expected.os_subject,
                expected.administrator_id, expected.device, expected.inode)):
            raise EngineError('owner_setup_source_denied', 'Actual Owner/data directory changed', 403)

    def _local(self):
        if (not self._valid or self._closed or self._transport is None or self._transport.invalid
                or self._host is None or self._receipt is None or self._host._closed or self._receipt._closed):
            raise EngineError('owner_setup_source_closed', 'Original setup source is irreversibly unavailable', 403)

    def _reply(self, data, method):
        reply = _fields(_json(data), ('wire', 'session', 'seq', 'status', 'code', 'setup_id',
            'intent_sha256', 'challenge_id', 'remaining_us', 'intent', 'confirmation_source'))
        if canonical_wire(reply) != data:
            raise invalid('Native confirmation reply is not exact canonical UTF8')
        _uint(reply['seq'])
        status = _uint(reply['status'])
        code = _text(reply['code'], limit=128)
        remaining = _uint(reply['remaining_us'])
        if ((reply['wire'], reply['session'], reply['seq'], reply['setup_id'],
                _sha(reply['intent_sha256'])) != (WIRE, self.locator['session'], self._seq,
                self._intent.setup_id, setup_sha256(self._intent))):
            raise invalid('Reply differs from the original full setup/session/sequence')
        if status in (403, 409, 503):
            allowed = {403: {'declined', 'expired', 'source_closed', 'owner_changed'},
                409: {'intent_changed', 'already_taken', 'generation_changed'},
                503: {'native_session_unavailable'}}
            if code not in allowed[status] or reply['intent'] is not None or reply['confirmation_source'] is not None:
                raise invalid('Native setup returned an unsupported failure shape')
            raise EngineError('owner_setup_' + code, 'Native Owner setup was not accepted/current', status)
        expected = {'bind': (200, 'bound'), 'present': (202, 'pending'),
            'assert_current': (200, 'current'), 'close': (200, 'view_closed_native_ownership_retained')}
        if method != 'take' and (status, code) != expected[method]:
            raise invalid('Native setup returned a different method state')
        if method == 'take' and (status, code) not in ((202, 'pending'), (200, 'confirmed')):
            raise invalid('Take must report definite pending or one original confirmed object')
        if method == 'bind' or method == 'close':
            if (reply['challenge_id'] is not None or remaining or reply['intent'] is not None
                    or reply['confirmation_source'] is not None):
                raise invalid('Bind/close do not carry approval or dialog facts')
            return reply, None
        challenge = _text(reply['challenge_id'], limit=128)
        if self._challenge is not None and challenge != self._challenge:
            raise invalid('Original dialog challenge changed')
        if method == 'present':
            if not 0 < remaining <= 600_000_000 or reply['intent'] is not None or reply['confirmation_source'] is not None:
                raise invalid('Present is pending; it cannot grant confirmation')
            self._challenge = challenge
            return reply, None
        if method == 'take' and status == 202:
            if not 0 < remaining <= 600_000_000 or reply['intent'] is not None or reply['confirmation_source'] is not None:
                raise invalid('Pending take cannot carry an approval')
            return reply, None
        if not 0 < remaining <= 120_000_000:
            raise invalid('Confirmed consumption interval is finite and cannot be extended')
        if reply['intent'] != self._intent.model_dump(mode='json'):
            raise invalid('Confirmed/current reply must bind the complete displayed original intent')
        try:
            source = NativeSetupConfirmationOrigin.model_validate(reply['confirmation_source'])
        except (ValueError, TypeError) as error:
            raise invalid('Original confirmation provenance is incomplete') from error
        if source.model_dump(mode='json') != reply['confirmation_source']:
            raise invalid('Native confirmation provenance must be complete and strict')
        server = self.locator['server']
        if ((source.session_id, source.challenge_id, source.os_subject, source.expected_host_sha256,
                source.host_pid, source.host_creation_filetime, source.child_pid, source.child_creation_filetime)
                != (self.locator['session'], self._challenge, self._directory.os_subject, self.host_sha,
                    server['pid'], server['creation_filetime'], self._child_identity[0], self._child_identity[1])
                or self._child_identity[2] != source.os_subject or source.gui_session_id != self._gui_session_id):
            raise EngineError('owner_setup_source_denied', 'Original actual OS peer/child/Owner differs', 403)
        return reply, source

    def _exchange(self, method, *, deadline=None, **arguments):
        self._local()
        deadline = time.monotonic() + 10 if deadline is None else deadline
        try:
            self._deadline(deadline)
            self._assert_directory()
            self._host.assert_current()
            self._receipt.assert_current()
            self._transport.assert_peer()
            self._deadline(deadline)
            request = {'method': method, 'wire': WIRE, 'session': self.locator['session'],
                'seq': self._seq, 'setup_id': self._intent.setup_id,
                'intent_sha256': setup_sha256(self._intent), **arguments}
            data = canonical_wire(request)
            if not 0 < len(data) <= SETUP_FRAME_LIMIT:
                raise invalid('Whole native setup request exceeds the frame bound')
            self._transport.write_all(struct.pack('<I', len(data)) + data, deadline=deadline)
            size = struct.unpack('<I', self._transport.read_exact(4, deadline=deadline))[0]
            if not 0 < size <= SETUP_FRAME_LIMIT:
                raise invalid('Whole native setup reply exceeds the frame bound')
            reply, source = self._reply(self._transport.read_exact(size, deadline=deadline), method)
            self._transport.assert_peer()
            self._assert_directory()
            self._deadline(deadline)
            if self._seq == 0xFFFFFFFFFFFFFFFF:
                raise invalid('Setup sequence is exhausted')
            self._seq += 1
            return reply, source
        except BaseException:
            # Includes ambiguous accepted take. Never reconnect/reissue it.
            self._valid = False
            raise

    def accept_setup(self, intent):
        with self._lock:
            if self._taken:
                raise EngineError('owner_setup_replay', 'One original confirmation may be consumed once', 409)
            self.open(intent)
            presentation_started = time.monotonic()
            reply, _source = self._exchange('present', intent=intent.model_dump(mode='json'))
            challenge_deadline = presentation_started + reply['remaining_us'] / 1_000_000
            while True:
                self._deadline(challenge_deadline)
                take_started = time.monotonic()
                reply, source = self._exchange('take', challenge_id=self._challenge,
                    deadline=min(challenge_deadline, time.monotonic() + 10))
                if source is not None:
                    self._taken = True
                    original = RetainedSetupConfirmation(intent, setup_sha256(intent), source,
                        take_started + reply['remaining_us'] / 1_000_000, self._epoch)
                    self._original = original
                    return original
                # Only a definite202 pending permits another polling take. An
                # exception after contact invalidates and never returns here.
                time.sleep(min(0.1, max(0.0, challenge_deadline - time.monotonic())))

    def assert_local_current(self, confirmation):
        if not self._lock.acquire(blocking=False):
            raise EngineError('owner_setup_source_busy', 'Owner setup is in an external exchange', 503)
        try:
            self._local()
            if (type(confirmation) is not RetainedSetupConfirmation or confirmation is not self._original
                    or confirmation._epoch is not self._epoch or confirmation.intent is not self._intent):
                raise EngineError('owner_setup_confirmation_denied', 'Only the original retained confirmation is valid', 403)
            self._deadline(confirmation.deadline_monotonic)
        finally:
            self._lock.release()

    def assert_current(self, confirmation):
        with self._lock:
            self.assert_local_current(confirmation)
            _reply, source = self._exchange('assert_current', challenge_id=self._challenge,
                confirmation_id=confirmation.source.confirmation_id,
                deadline=min(confirmation.deadline_monotonic, time.monotonic() + 10))
            if source != confirmation.source:
                self._valid = False
                raise EngineError('owner_setup_confirmation_changed', 'Original confirmation identity/expiry changed', 409)

    def close(self):
        with self._lock:
            if self._closed:
                return
            primary = self._close_error
            try:
                if primary is not None:
                    raise primary
                if self._valid and not self._close_contacted:
                    self._close_contacted = True
                    self._exchange('close', confirmation_id=(
                        self._original.source.confirmation_id if self._original else None))
            except BaseException as error:
                primary, self._close_error = error, error
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
            self._original = None
            del _retained_connections[id(self)]
