"""ADR0044 actual-peer v2 connection and session-owned native writer lease."""

import struct
import threading
import time
from dataclasses import dataclass

from video_creator.domain.errors import EngineError
from video_creator.domain.installation_qualification import (
    I64_MAX, LeaseBinding, QualificationBinding, canonical_bytes, parse_exact,
)
from video_creator.infrastructure.held_authority import (
    FRAME_LIMIT, HeldFileFact, OwnedAuthorityConnection, _fields, _invalid,
    _json, _sha, _text, _uint,
)

WIRE = 'held-resource-authority-v2-candidate'
REPLY_FIELDS = ('wire', 'session', 'seq', 'status', 'code', 'observation_id',
                'observed_at_us', 'files', 'qualification', 'registration_sha256',
                'resource_manifest_sha256', 'runtime_manifest_sha256',
                'qualification_binding', 'lease_binding')


@dataclass(frozen=True, eq=False, repr=False)
class QualifiedHeldFactsObservation:
    observation_id: str
    observed_at_us: int
    files: tuple[HeldFileFact, ...]
    qualification: str
    binding: QualificationBinding | None
    _epoch: object


@dataclass(frozen=True, eq=False, repr=False)
class NativeWriterLease:
    binding: LeaseBinding
    observation: QualifiedHeldFactsObservation
    thread_id: int
    _owner: object
    _epoch: object


class OwnedQualifiedAuthorityConnection(OwnedAuthorityConnection):
    def __init__(self, **kwargs):
        self._active_lease = None
        self._lease_unknown = False
        self._bound_qualification = None
        super().__init__(**kwargs)

    def _invalidate(self):
        # Never claim the native RW guard released merely because our cache died.
        super()._invalidate()
        self._epoch = object()

    def assert_local_current(self):
        """Pure cache/member state; external RPC paths separately check peer."""
        if not self._lock.acquire(blocking=False):
            raise EngineError('installation_session_busy', 'Qualified session is in external observation', 503)
        try:
            if not self._valid:
                raise EngineError('installation_connection_invalid', 'Original qualified session is invalid', 503)
        finally:
            self._lock.release()

    def _reply(self, data, method):
        raw = _fields(_json(data), REPLY_FIELDS)
        if canonical_bytes(raw) != data:
            raise _invalid('Qualified response is not canonical')
        _uint(raw['seq'])
        _uint(raw['status'])
        _text(raw['code'])
        if (raw['wire'], raw['session'], raw['seq']) != (WIRE, self._session, self._seq):
            raise _invalid('Qualified response session/sequence differs')
        if tuple(_sha(raw[key]) for key in ('registration_sha256', 'resource_manifest_sha256', 'runtime_manifest_sha256')) != (
                self.context.registration_sha256, self.context.resource_manifest_sha256, self.context.runtime_manifest_sha256):
            raise EngineError('installation_peer_denied', 'Qualified reply launch maps differ', 403)
        if type(raw['files']) is not list:
            raise _invalid('Qualified reply files must be an array')
        files = tuple(HeldFileFact(**_fields(item, ('relative_path','bytes','sha256'))) for item in raw['files'])
        if any(file.bytes > I64_MAX for file in files) or tuple(file.relative_path for file in files) != tuple(sorted({file.relative_path for file in files})):
            raise _invalid('Qualified held file map exceeds I64 or is not sorted/distinct')
        binding = None
        if raw['qualification'] == 'qualified':
            binding = parse_exact(QualificationBinding, canonical_bytes(raw['qualification_binding']), limit=FRAME_LIMIT)
        elif raw['qualification'] != 'not_ready' or raw['qualification_binding'] is not None:
            raise _invalid('Facts-only qualified-wire reply must have null binding')
        lease = None
        if raw['lease_binding'] is not None:
            lease = parse_exact(LeaseBinding, canonical_bytes(raw['lease_binding']))
            if binding is None or lease.record_ref != binding.record.ref() or (
                    lease.registry_revision,lease.revocation_floor) != (binding.registry_revision,binding.revocation_floor):
                raise _invalid('Native lease differs from its full original record')
        if raw['status'] != 200:
            if files or raw['observation_id'] is not None or raw['observed_at_us'] is not None or lease is not None:
                raise _invalid('Qualified rejection contains observation/lease facts')
            status,code=raw['status'],raw['code']
            allowed={409:('qualification_changed','qualification_revoked','qualification_expired','lease_conflict','observation_unknown_or_foreign'),
                     503:('qualification_unavailable','qualification_unknown'),422:('invalid_frame',),403:('peer_denied',)}
            if code not in allowed.get(status,()):
                raise _invalid('Qualified authority error is outside the closed protocol')
            raise EngineError('installation_observation_denied' if code=='observation_unknown_or_foreign' else code,
                              'Original qualified authority rejected this exact operation',status)
        expected={'bind':('bound_qualified','bound_facts_only'),'observe':('observed_qualified','observed_facts_only'),
                  'assert_current':('current_qualified','current_facts_only'),
                  'begin_writer_lease':('writer_lease_acquired',),'end_writer_lease':('writer_lease_released',)}
        if raw['code'] not in expected[method] or method in ('bind','observe','assert_current') and raw['code'].endswith('_qualified') != (binding is not None):
            raise _invalid('Qualified method success code differs from its state')
        if method=='observe':
            _text(raw['observation_id'],limit=128)
            if not 0 < _uint(raw['observed_at_us'],positive=True) <= I64_MAX or files != tuple(sorted(self.context.expected_files,key=lambda file:file.relative_path)):
                raise _invalid('Qualified observed full map/time differs')
        elif files or raw['observation_id'] is not None or raw['observed_at_us'] is not None:
            raise _invalid('Qualified non-observe reply carries unexpected files/time/id')
        if (method in ('begin_writer_lease','end_writer_lease')) != (lease is not None):
            raise _invalid('Qualified reply has an invalid lease shape')
        if method=='bind':
            self._bound_qualification=binding
        return (raw,binding,lease),files

    def _exchange(self, method, *, deadline=None, **arguments):
        self.assert_local_current()
        deadline=time.monotonic()+10 if deadline is None else deadline
        try:
            self._transport.assert_peer()
            data=canonical_bytes(dict(method=method,wire=WIRE,session=self._session,seq=self._seq,**arguments))
            if not 1 <= len(data) <= FRAME_LIMIT:
                raise _invalid('Qualified request frame size differs')
            self._transport.write_all(struct.pack('<I',len(data))+data,deadline=deadline)
            size=struct.unpack('<I',self._transport.read_exact(4,deadline=deadline))[0]
            if not 1 <= size <= FRAME_LIMIT:
                raise _invalid('Qualified response frame size differs')
            reply,files=self._reply(self._transport.read_exact(size,deadline=deadline),method)
            self._transport.assert_peer()
            if time.monotonic()>=deadline:
                raise EngineError('installation_channel_timeout','Qualified exchange deadline elapsed',503)
            if self._seq==0xFFFFFFFFFFFFFFFF:
                raise _invalid('Qualified sequence exhausted')
            self._seq+=1
            return reply,files
        except BaseException:
            self._invalidate()
            raise

    def _original(self, observation):
        self.assert_local_current()
        if (type(observation) is not QualifiedHeldFactsObservation or observation._epoch is not self._epoch
                or self._observations.get(observation.observation_id) is not observation):
            raise EngineError('installation_observation_denied','Original qualified session observation is required',409)

    def observe_facts(self):
        with self._lock:
            if self._active_lease is not None:
                raise EngineError('lease_conflict','Cannot observe during original writer lease',409)
            (raw,binding,_),files=self._exchange('observe')
            key=raw['observation_id']
            if key in self._observations:
                self._invalidate()
                raise _invalid('Qualified observation ID was reused')
            observation=QualifiedHeldFactsObservation(key,raw['observed_at_us'],files,raw['qualification'],binding,self._epoch)
            self._observations[key]=observation
            return observation

    def assert_current_facts(self, observation):
        with self._lock:
            self._original(observation)
            (_,binding,_),_=self._exchange('assert_current',observation_id=observation.observation_id)
            if binding is None or observation.binding is None or (
                    binding.record,binding.registry_revision,binding.revocation_floor) != (
                    observation.binding.record,observation.binding.registry_revision,observation.binding.revocation_floor):
                self._invalidate()
                raise EngineError('qualification_changed','Original qualified record/current floor changed',409)

    def begin_writer_lease(self, observation):
        with self._lock:
            self._original(observation)
            if self._active_lease is not None:
                raise EngineError('lease_conflict','One outer native writer lease is permitted',409)
            # A failed read can follow native acquisition. Retain uncertainty
            # before sending; only an exact validated reply settles it.
            self._lease_unknown=True
            (_,binding,lease),_=self._exchange('begin_writer_lease',observation_id=observation.observation_id)
            if binding is None or observation.binding is None or lease.observation_id!=observation.observation_id or (
                    binding.record,binding.registry_revision,binding.revocation_floor) != (
                    observation.binding.record,observation.binding.registry_revision,observation.binding.revocation_floor):
                self._invalidate()
                raise EngineError('qualification_changed','Native lease belongs to another original record',409)
            original=NativeWriterLease(lease,observation,threading.get_ident(),self,self._epoch)
            self._active_lease=original
            self._lease_unknown=False
            return original

    def assert_local_lease(self, lease):
        self.assert_local_current()
        if (type(lease) is not NativeWriterLease or lease is not self._active_lease or lease._owner is not self
                or lease._epoch is not self._epoch or lease.thread_id!=threading.get_ident()):
            raise EngineError('lease_conflict','Original same-thread native writer lease is required',409)
        self._original(lease.observation)

    def end_writer_lease(self, lease):
        with self._lock:
            self.assert_local_lease(lease)
            self._lease_unknown=True
            (_,_,released),_=self._exchange('end_writer_lease',lease_id=lease.binding.lease_id)
            if released!=lease.binding:
                self._invalidate()
                raise _invalid('Native lease release receipt differs')
            self._active_lease=None
            self._lease_unknown=False

    def close(self):
        with self._lock:
            if self._active_lease is not None or self._lease_unknown:
                # Unknown begin/end preserves original transport and guard until
                # the actual owning child terminates; close is not a release ACK.
                self._invalidate()
                raise EngineError('qualification_unknown','Original native writer lease has not acknowledged release',503)
            super().close()
