"""One original installer record action; no production qualified lease."""

import struct
import threading
import time
from dataclasses import dataclass
from video_creator.domain.errors import EngineError
from video_creator.domain.installation_qualification import InstallationRecordAdmission, canonical_bytes, parse_exact
from video_creator.infrastructure.held_authority import FRAME_LIMIT, NativeLaunchContext, _fields, _json, _text, _uint, _sha, _invalid
from video_creator.infrastructure.native_instance_source import _NativeInstanceSource
from video_creator.infrastructure.windows_authority_pipe import WindowsAuthorityPipe

WIRE='held-installation-record-v1-candidate'
PURPOSE='installation-record-admission'
_connections={}


@dataclass(frozen=True,eq=False,repr=False)
class InstallationRecordAdmissionSource:
    admission: InstallationRecordAdmission
    _connection: object
    _epoch: object
    _thread: int


class OwnedInstallationRecordConnection:
    def __init__(self,*,engine,initialization_source,locator_bytes):
        if type(initialization_source) is not _NativeInstanceSource:
            raise EngineError('installation_record_source_denied','Original initialized child source is required',403)
        initialization_source.assert_setup_engine_current(engine)
        locator=_fields(_json(locator_bytes),('pipe','session','role','server','purpose','instance_id'))
        pipe=_text(locator['pipe'],limit=512)
        prefix='\\\\.\\pipe\\VideoCreator-InstallationRecord-'
        if canonical_bytes(locator)!=locator_bytes or not pipe.startswith(prefix) or not pipe[len(prefix):] or any(char in pipe[len(prefix):] for char in ('\\','/',':')):
            raise _invalid('Installation record locator requires exact original local purpose')
        _text(locator['session'],limit=128)
        server=_fields(locator['server'],('pid','creation_filetime','sid','image','image_sha256'))
        if _uint(server['pid'],positive=True)>0xFFFFFFFF:
            raise _invalid('Original installer PID exceeds native range')
        _uint(server['creation_filetime'],positive=True);_text(server['sid']);_text(server['image'],limit=32768);_sha(server['image_sha256'])
        if (locator['instance_id'],locator['role'],locator['purpose'])!=(engine.instance_id,PURPOSE,PURPOSE) or server!=initialization_source.locator['server']:
            raise EngineError('installation_record_source_denied','Original installer peer/purpose/instance differs',403)
        self.engine,self.source,self.locator=engine,initialization_source,locator
        self._epoch,self._closed,self._used,self._action,self._transport=object(),False,False,None,None
        self._thread=threading.get_ident()
        inputs=initialization_source.record.installation
        self.context=NativeLaunchContext(engine.instance_id,'api',inputs.registration_sha256,inputs.resource_manifest_sha256,
            inputs.runtime_manifest_sha256,inputs.expected_files,inputs.engine_file_names)
        _connections[id(self)]=self
        try:
            self._transport=WindowsAuthorityPipe(pipe_name=pipe,server=server,trusted_build=initialization_source.host,startup_deadline=time.monotonic()+10)
            self.assert_current()
        except BaseException:
            if self._transport is not None:self._transport.close()
            self._closed=True
            _connections.pop(id(self),None)
            raise

    def assert_local_current(self):
        if (self._closed or _connections.get(id(self)) is not self or self._thread!=threading.get_ident()
                or self.source._disabled or not self.source._setup_bound or self.source._engine is not self.engine
                or self.source._database is not self.engine.db or self.source._instance_id!=self.engine.instance_id
                or self.source.host._closed or self.source.receipt._closed):
            raise EngineError('installation_record_binding_changed','Original installer member/bound instance changed',409)

    def assert_current(self):
        self.assert_local_current()
        self.source.assert_setup_engine_current(self.engine)
        self._transport.assert_peer()

    def consume(self):
        self.assert_current()
        if self._used:
            raise EngineError('installation_record_unknown','Original installer action already used or unknown',503)
        self._used=True
        deadline=time.monotonic()+10
        data=canonical_bytes(dict(wire=WIRE,session=self.locator['session'],seq=1,method='admit_record',instance_id=self.engine.instance_id))
        self._transport.write_all(struct.pack('<I',len(data))+data,deadline=deadline)
        size=struct.unpack('<I',self._transport.read_exact(4,deadline=deadline))[0]
        if not 1<=size<=FRAME_LIMIT:raise _invalid('Installation record reply frame exceeds bound')
        data=self._transport.read_exact(size,deadline=deadline)
        raw=_fields(_json(data),('wire','session','seq','status','code','instance_id','record_admission'))
        _uint(raw['seq']);_uint(raw['status']);_text(raw['code'])
        if canonical_bytes(raw)!=data or (raw['wire'],raw['session'],raw['seq'],raw['instance_id'])!=(WIRE,self.locator['session'],1,self.engine.instance_id):
            raise _invalid('Installation record reply original sequence differs')
        if raw['status']!=200:
            if raw['record_admission'] is not None or raw['status'] not in (422,403,409,503):raise _invalid('Installation record rejection differs')
            code={422:'installation_record_frame_invalid',403:'installation_record_source_denied',409:'installation_record_admission_conflict',503:'installation_record_unavailable'}[raw['status']]
            raise EngineError(code,'Original installer rejected the record action',raw['status'])
        if raw['code']!='record_source_admitted':raise _invalid('Installation record success code differs')
        admission=parse_exact(InstallationRecordAdmission,canonical_bytes(raw['record_admission']),limit=FRAME_LIMIT)
        if admission.host_build_receipt_sha256!=self.source.record.installation.build_receipt_sha256:
            raise EngineError('installation_record_binding_changed','Record action belongs to another original build',409)
        self.assert_current()
        if time.monotonic()>=deadline:raise EngineError('installation_record_timeout','Original installer exchange exceeded deadline',503)
        self._action=InstallationRecordAdmissionSource(admission,self,self._epoch,threading.get_ident())
        return self._action

    def assert_action(self,action,sql_connection=None):
        self.assert_local_current()
        if (type(action) is not InstallationRecordAdmissionSource or action is not self._action
                or action._connection is not self or action._epoch is not self._epoch or action._thread!=threading.get_ident()):
            raise EngineError('installation_record_source_denied','Original installer action member is required',403)
        if sql_connection is None:self.assert_current()
        else:
            row=sql_connection.execute("SELECT value FROM metadata WHERE key='instance_id'").fetchone()
            if row is None or row[0]!=self.engine.instance_id:
                raise EngineError('installation_record_binding_changed','Actual original installer SQLite identity changed',409)

    def close(self):
        if not self._closed:
            self._transport.close()
            self._closed=True;self._epoch=object()
            _connections.pop(id(self),None)
