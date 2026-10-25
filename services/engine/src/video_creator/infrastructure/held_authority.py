"""Strict private I49 facts wire; no public DTO or resource qualification."""

import json
import math
import struct
import threading
import time
from dataclasses import dataclass
from typing import Literal

from video_creator.domain.errors import EngineError
from video_creator.infrastructure.windows_authority_pipe import WindowsAuthorityPipe

WIRE = 'held-resource-authority-v1-candidate'
FRAME_LIMIT = 32 * 1024 * 1024


def _invalid(message):
    return EngineError('installation_frame_invalid', message, 422)


def _fields(value, names):
    if type(value) is not dict or set(value) != set(names):
        raise _invalid('Private authority fields do not match the fixed protocol')
    return value


def _text(value, *, limit=1024):
    if (type(value) is not str or not value or len(value) > limit
            or any(ord(char) < 32 or 0xD800 <= ord(char) <= 0xDFFF for char in value)):
        raise _invalid('Private authority text is invalid')
    return value


def _uint(value, *, positive=False):
    if type(value) is not int or not (1 if positive else 0) <= value <= 0xFFFFFFFFFFFFFFFF:
        raise _invalid('Private authority integer is invalid')
    return value


def _sha(value):
    if type(value) is not str or len(value) != 64 or any(char not in '0123456789abcdef' for char in value):
        raise _invalid('Private authority SHA256 is invalid')
    return value


def _relative(value):
    value = _text(value, limit=32768)
    if value.startswith('/') or '\\' in value or ':' in value or any(part in ('', '.', '..') for part in value.split('/')):
        raise _invalid('Held resource identity must be a complete fixed relative file')
    return value


def _json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise _invalid('Private authority JSON repeats a field')
            result[key] = value
        return result

    def number(value):
        parsed = float(value)
        if not math.isfinite(parsed):
            raise _invalid('Private authority JSON has a nonfinite number')
        return parsed

    def constant(_value):
        raise _invalid('Private authority JSON has a nonfinite number')

    if type(data) is not bytes or not 1 <= len(data) <= FRAME_LIMIT:
        raise _invalid('Private authority JSON has an invalid finite size')
    try:
        return json.loads(data.decode('utf-8'), object_pairs_hook=pairs, parse_float=number, parse_constant=constant)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise _invalid('Private authority JSON is damaged') from error


@dataclass(frozen=True)
class HeldFileFact:
    relative_path: str
    bytes: int
    sha256: str

    def __post_init__(self):
        _relative(self.relative_path)
        _uint(self.bytes)
        _sha(self.sha256)


@dataclass(frozen=True)
class NativeLaunchContext:
    """Fixed installation launch input, not accepted by a route/CLI parser.

    Complete expected map and engine/indexed partition originate from the same
    trusted installation preparation. Hashes are context identities only.
    """
    instance_id: str
    role: Literal['api', 'worker', 'mcp']
    registration_sha256: str
    resource_manifest_sha256: str
    runtime_manifest_sha256: str
    expected_files: tuple[HeldFileFact, ...]
    engine_file_names: tuple[str, ...]

    def __post_init__(self):
        _text(self.instance_id)
        if self.role not in ('api', 'worker', 'mcp'):
            raise _invalid('Native installation role is not an admitted production entry')
        for sha in (self.registration_sha256, self.resource_manifest_sha256, self.runtime_manifest_sha256):
            _sha(sha)
        if type(self.expected_files) is not tuple or not self.expected_files or any(type(item) is not HeldFileFact for item in self.expected_files):
            raise _invalid('Native installation requires its complete finite file map')
        names = {item.relative_path for item in self.expected_files}
        if len(names) != len(self.expected_files):
            raise _invalid('Native installation repeats a file identity')
        if (type(self.engine_file_names) is not tuple or not self.engine_file_names
                or len(set(self.engine_file_names)) != len(self.engine_file_names)
                or not set(self.engine_file_names) < names):
            raise _invalid('Native installation requires complete nonempty engine and indexed partitions')
        # Refuse oversized launch context before connecting; never truncate it.
        representation = json.dumps([item.__dict__ for item in self.expected_files], ensure_ascii=False).encode('utf-8')
        if len(representation) > FRAME_LIMIT - 16384:
            raise _invalid('Full native installation map exceeds the admitted wire')


@dataclass(frozen=True, eq=False, repr=False)
class HeldFactsObservation:
    observation_id: str
    observed_at_us: int
    files: tuple[HeldFileFact, ...]
    qualification: Literal['not_ready']
    _epoch: object


class OwnedAuthorityConnection:
    """One exact child-opened session; identity map is private and strong."""
    def __init__(self, *, locator_bytes: bytes, context: NativeLaunchContext, trusted_build):
        self.context, self._epoch = context, object()
        self._lock = threading.RLock()
        self._observations, self._seq, self._valid = {}, 0, False
        self._transport = None
        locator = _fields(_json(locator_bytes), ('pipe', 'session', 'instance_id', 'role', 'server'))
        pipe = _text(locator['pipe'], limit=512)
        if not pipe.startswith('\\\\.\\pipe\\') or not pipe[9:] or any(char in pipe[9:] for char in ('\\', '/', ':')):
            raise _invalid('Authority locator must be one local named pipe')
        self._session = _text(locator['session'], limit=128)
        if (locator['instance_id'], locator['role']) != (context.instance_id, context.role):
            raise EngineError('installation_peer_denied', 'Private launch instance or role differs from the trusted startup', 403)
        server = _fields(locator['server'], ('pid', 'creation_filetime', 'sid', 'image', 'image_sha256'))
        if not 0 < _uint(server['pid'], positive=True) <= 0xFFFFFFFF:
            raise _invalid('Authority PID is invalid')
        _uint(server['creation_filetime'], positive=True)
        _text(server['sid'])
        _text(server['image'], limit=32768)
        _sha(server['image_sha256'])
        deadline = time.monotonic() + 20
        try:
            self._transport = WindowsAuthorityPipe(pipe_name=pipe, server=server,
                trusted_build=trusted_build, startup_deadline=deadline)
            self._valid = True
            self._exchange('bind', deadline=min(deadline, time.monotonic() + 10),
                           instance_id=context.instance_id, role=context.role)
        except BaseException:
            self.close()
            raise

    def _invalidate(self):
        self._valid = False
        self._observations.clear()

    def assert_local_current(self):
        # A short writer must never wait behind another thread's pipe RPC.
        if not self._lock.acquire(blocking=False):
            raise EngineError('installation_session_busy', 'Original authority session is currently in external observation', 503)
        try:
            if not self._valid:
                raise EngineError('installation_connection_invalid', 'Original held authority session is invalid', 503)
            try:
                self._transport.assert_local_current()
            except BaseException:
                self._invalidate()
                raise
        finally:
            self._lock.release()

    def _reply(self, data, method):
        reply = _fields(_json(data), ('wire', 'session', 'seq', 'status', 'code', 'observation_id',
            'observed_at_us', 'files', 'qualification', 'registration_sha256', 'resource_manifest_sha256', 'runtime_manifest_sha256'))
        _uint(reply['seq'])
        _uint(reply['status'])
        _text(reply['code'])
        if (reply['wire'], reply['session'], reply['seq']) != (WIRE, self._session, self._seq):
            raise _invalid('Authority reply does not match the original session and sequence')
        expected = (self.context.registration_sha256, self.context.resource_manifest_sha256, self.context.runtime_manifest_sha256)
        if tuple(_sha(reply[name]) for name in ('registration_sha256', 'resource_manifest_sha256', 'runtime_manifest_sha256')) != expected:
            raise EngineError('installation_peer_denied', 'Authority reply differs from the fixed installation launch', 403)
        if reply['qualification'] != 'not_ready':
            # I49 currently has no qualified report/reference grammar. It must
            # be independently revised/admitted before issuing production facts.
            raise _invalid('Current wire does not admit a qualified installation claim')
        if type(reply['files']) is not list:
            raise _invalid('Authority complete file map is invalid')
        files = []
        for raw in reply['files']:
            raw = _fields(raw, ('relative_path', 'bytes', 'sha256'))
            files.append(HeldFileFact(raw['relative_path'], raw['bytes'], raw['sha256']))
        if len({item.relative_path for item in files}) != len(files):
            raise _invalid('Authority repeats a held file')
        if reply['status'] == 409 and reply['code'] == 'observation_unknown_or_foreign':
            if files or reply['observed_at_us'] is not None or reply['observation_id'] is not None:
                raise _invalid('Authority rejection contains unexpected observation facts')
            raise EngineError('installation_observation_denied', 'Original observation is unknown or foreign', 409)
        if reply['status'] == 422 and reply['code'] == 'invalid_frame':
            raise _invalid('Authority rejected this private frame')
        expected_code = {'bind': 'bound_facts_only', 'observe': 'observed_facts_only', 'assert_current': 'current_facts_only'}[method]
        if reply['status'] != 200 or reply['code'] != expected_code:
            raise _invalid('Authority reply has an unsupported status or method result')
        if method == 'observe':
            _text(reply['observation_id'], limit=128)
            _uint(reply['observed_at_us'], positive=True)
            if tuple(sorted(files, key=lambda item: item.relative_path)) != tuple(sorted(self.context.expected_files, key=lambda item: item.relative_path)):
                raise _invalid('Actual held map differs from the complete trusted launch map')
        elif files or reply['observed_at_us'] is not None or reply['observation_id'] is not None:
            raise _invalid('Authority method returned an unsupported observation shape')
        return reply, tuple(files)

    def _exchange(self, method, *, deadline=None, **arguments):
        self.assert_local_current()
        deadline = time.monotonic() + 10 if deadline is None else deadline
        try:
            self._transport.assert_peer()
            request = dict(method=method, wire=WIRE, session=self._session, seq=self._seq, **arguments)
            data = json.dumps(request, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
            if not 1 <= len(data) <= FRAME_LIMIT:
                raise _invalid('Private request exceeds its finite frame bound')
            self._transport.write_all(struct.pack('<I', len(data)) + data, deadline=deadline)
            size = struct.unpack('<I', self._transport.read_exact(4, deadline=deadline))[0]
            if not 1 <= size <= FRAME_LIMIT:
                raise _invalid('Authority frame size is invalid')
            reply, files = self._reply(self._transport.read_exact(size, deadline=deadline), method)
            self._transport.assert_peer()
            if time.monotonic() >= deadline:
                raise EngineError('installation_channel_timeout', 'Authority verification exceeded the whole exchange deadline', 503)
            if self._seq == 0xFFFFFFFFFFFFFFFF:
                raise _invalid('Original authority sequence is exhausted')
            self._seq += 1
            return reply, files
        except BaseException:
            self._invalidate()
            raise

    def observe_facts(self):
        with self._lock:
            reply, files = self._exchange('observe')
            key = reply['observation_id']
            if key in self._observations:
                self._invalidate()
                raise _invalid('Authority attempted to revive an observation ID')
            observation = HeldFactsObservation(key, reply['observed_at_us'], files, 'not_ready', self._epoch)
            self._observations[key] = observation
            return observation

    def _original(self, observation):
        self.assert_local_current()
        if (type(observation) is not HeldFactsObservation or observation._epoch is not self._epoch
                or self._observations.get(observation.observation_id) is not observation):
            raise EngineError('installation_observation_denied', 'Exact original observation object from this live session is required', 409)

    def assert_current_facts(self, observation):
        with self._lock:
            self._original(observation)
            self._exchange('assert_current', observation_id=observation.observation_id)

    def assert_local_observation(self, observation):
        if not self._lock.acquire(blocking=False):
            raise EngineError('installation_session_busy', 'Original authority session is currently in external observation', 503)
        try:
            self._original(observation)
        finally:
            self._lock.release()

    def close(self):
        with self._lock:
            self._invalidate()
            if self._transport is not None:
                self._transport.close()
