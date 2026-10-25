"""One-use actual native installation trust action, after same-child bind."""

import struct
import time
from dataclasses import dataclass

from video_creator.domain.errors import EngineError
from video_creator.domain.installation_qualification import TrustAdmission, canonical_bytes, parse_exact
from video_creator.infrastructure.held_authority import FRAME_LIMIT, _fields, _invalid, _json, _sha, _text, _uint
from video_creator.infrastructure.native_instance_source import _NativeInstanceSource
from video_creator.infrastructure.windows_authority_pipe import WindowsAuthorityPipe

WIRE = 'held-installation-trust-v1-candidate'
PURPOSE = 'installation-trust-admission'
_retained_trust_connections = {}


def parse_trust_locator(data, instance_id):
    locator = _fields(_json(data), ('pipe','session','role','server','purpose','instance_id'))
    if canonical_bytes(locator) != data:
        raise _invalid('Trust-purpose locator must be canonical')
    pipe = _text(locator['pipe'],limit=512)
    prefix='\\\\.\\pipe\\VideoCreator-InstallationTrust-'
    if not pipe.startswith(prefix) or not pipe[len(prefix):] or any(char in pipe[len(prefix):] for char in ('\\','/',':')):
        raise _invalid('Trust purpose requires one exact local named pipe')
    _text(locator['session'],limit=128)
    if (locator['instance_id'],locator['role'],locator['purpose']) != (instance_id,PURPOSE,PURPOSE):
        raise EngineError('installation_peer_denied','Trust purpose/instance differs from the bound original child',403)
    server=_fields(locator['server'],('pid','creation_filetime','sid','image','image_sha256'))
    if _uint(server['pid'],positive=True)>0xFFFFFFFF:
        raise _invalid('Trust server PID exceeds its actual native representation')
    _uint(server['creation_filetime'],positive=True)
    _text(server['sid'])
    _text(server['image'],limit=32768)
    _sha(server['image_sha256'])
    return locator


@dataclass(frozen=True,eq=False,repr=False)
class AuthenticatedTrustAction:
    admission: TrustAdmission
    _connection: object
    _epoch: object


class OwnedInstallationTrustConnection:
    def __init__(self, *, engine, initialization_source, locator_bytes):
        if type(initialization_source) is not _NativeInstanceSource:
            raise EngineError('installation_peer_denied','Original initialized same-child source is required',403)
        initialization_source.assert_setup_engine_current(engine)
        self.engine,self.source=engine,initialization_source
        self.locator=parse_trust_locator(locator_bytes,engine.instance_id)
        if self.locator['server']!=initialization_source.locator['server']:
            raise EngineError('installation_peer_denied','Trust source is not the original initialized native parent',403)
        self._epoch,self._action,self._used,self._closed=object(),None,False,False
        self._transport=None
        _retained_trust_connections[id(self)]=self
        deadline=time.monotonic()+10
        try:
            self._transport=WindowsAuthorityPipe(pipe_name=self.locator['pipe'],server=self.locator['server'],
                trusted_build=initialization_source.host,startup_deadline=deadline)
            self.assert_current()
        except BaseException:
            self._closed=True
            if self._transport is not None:
                self._transport.close()
            raise

    def assert_current(self):
        if self._closed or _retained_trust_connections.get(id(self)) is not self:
            raise EngineError('qualification_unavailable','Original trust admission connection is unavailable',503)
        self.source.assert_setup_engine_current(self.engine)
        self._transport.assert_peer()

    def consume(self):
        self.assert_current()
        if self._used:
            raise EngineError('qualification_unknown','Original trust action already consumed or outcome unknown',503)
        self._used=True
        deadline=time.monotonic()+10
        data=canonical_bytes(dict(wire=WIRE,session=self.locator['session'],seq=1,method='admit',instance_id=self.engine.instance_id))
        self._transport.write_all(struct.pack('<I',len(data))+data,deadline=deadline)
        size=struct.unpack('<I',self._transport.read_exact(4,deadline=deadline))[0]
        if not 1 <= size <= FRAME_LIMIT:
            raise _invalid('Trust admission reply size differs')
        data=self._transport.read_exact(size,deadline=deadline)
        raw=_fields(_json(data),('wire','session','seq','status','code','instance_id','trust_admission'))
        if canonical_bytes(raw)!=data or (raw['wire'],raw['session'],raw['seq'],raw['instance_id'])!=(WIRE,self.locator['session'],1,self.engine.instance_id):
            raise _invalid('Trust action reply differs from its original purpose/sequence')
        _uint(raw['seq'])
        _uint(raw['status'])
        if raw['status']!=200:
            if raw['trust_admission'] is not None or raw['status'] not in (422,403,409,503):
                raise _invalid('Trust action rejection shape differs')
            raise EngineError('qualification_unavailable','Actual installation trust action was not admitted',raw['status'])
        if raw['code']!='trust_source_admitted':
            raise _invalid('Trust action success code differs')
        admission=parse_exact(TrustAdmission,canonical_bytes(raw['trust_admission']))
        if admission.host_build_receipt_sha256!=self.source.record.installation.build_receipt_sha256:
            raise EngineError('qualification_changed','Admitted trust action belongs to another held build receipt',409)
        self.assert_current()
        if time.monotonic()>=deadline:
            raise EngineError('installation_channel_timeout','Original trust action exchange exceeded its deadline',503)
        self._action=AuthenticatedTrustAction(admission,self,self._epoch)
        return self._action

    def assert_action(self, action, sql_connection=None):
        if (type(action) is not AuthenticatedTrustAction or self._action is not action
                or action._connection is not self or action._epoch is not self._epoch or self._closed):
            raise EngineError('qualification_unknown','Original authenticated trust action member is required',503)
        if sql_connection is None:
            self.assert_current()
        else:
            # Original parent/build handles and DataDir installation lock are
            # retained outside the writer. Only cache/member + SQL here.
            if (self.source._disabled or not self.source._setup_bound
                    or self.source._engine is not self.engine or self.source._database is not self.engine.db
                    or self.source._instance_id!=self.engine.instance_id
                    or self.source.host._closed or self.source.receipt._closed):
                raise EngineError('qualification_changed','Original bound trust source cache changed',409)
            row=sql_connection.execute("SELECT value FROM metadata WHERE key='instance_id'").fetchone()
            if row is None or row[0]!=self.engine.instance_id:
                raise EngineError('owner_instance_binding_changed','Original trust writer instance identity changed',409)

    def close(self):
        if not self._closed:
            self._epoch=object()
            self._closed=True
            self._transport.close()
            _retained_trust_connections.pop(id(self),None)
