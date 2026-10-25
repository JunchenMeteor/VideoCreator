"""Private retained same-Engine/Bundle setup continuation and record frames."""

import json
import struct
import sys
import threading
import time
from video_creator.domain.errors import EngineError
from video_creator.domain.installation_qualification import canonical_bytes
from video_creator.infrastructure.held_authority import FRAME_LIMIT,_fields,_json,_uint

WIRE='native-owner-instance-record-handshake-v1'
_TOKEN=object()
_states={}
PRODUCTION_WIRE='native-owner-setup-production-carry-v1'
_production_members={}


class TrustCommittedSetupState:
    def __init__(self,token,engine,bundle,source,binding,stream,recovery,trust_consumer,trust_connection,trust_source):
        from video_creator.infrastructure.native_instance_source import _NativeInstanceSource
        from video_creator.application.installation_trust_consumer import NativeInstallationTrustConsumer
        from video_creator.infrastructure.native_installation_trust import OwnedInstallationTrustConnection
        from video_creator.cli.native_instance_protocol import NativeInstanceSetupBinding

        if (token is not _TOKEN or bundle.engine is not engine or type(source) is not _NativeInstanceSource
                or type(binding) is not NativeInstanceSetupBinding or type(trust_consumer) is not NativeInstallationTrustConsumer
                or type(trust_connection) is not OwnedInstallationTrustConnection or trust_connection.source is not source
                or trust_connection.engine is not engine or trust_source._connection is not trust_connection):
            raise EngineError('owner_instance_source_denied','Only original same-Engine setup may retain this state',403)
        trust_consumer.assert_current(trust_source)
        source.assert_setup_engine_current(engine)
        self.engine,self.bundle,self.source,self.binding,self.stream=engine,bundle,source,binding,stream
        self.recovery,self.trust_consumer,self.trust_connection,self.trust_source=recovery,trust_consumer,trust_connection,trust_source
        self._thread,self._closed=threading.get_ident(),False
        self._close_complete,self._close_failure=False,None
        self.record_consumer=self.record_connection=self.record_receipt=None
        self.qualified_authority=None
        self.qualified_build=None
        self._record_ready=False
        _states[id(self)]=self

    def assert_current(self):
        if self._closed or _states.get(id(self)) is not self or self._thread!=threading.get_ident() or self.bundle.engine is not self.engine:
            raise EngineError('installation_record_source_denied','Original same-thread retained setup state is required',403)
        self.source.assert_setup_engine_current(self.engine)
        self.trust_consumer.assert_current(self.trust_source)

    def close(self):
        if self._close_complete:
            return
        if self._close_failure is not None:
            # Do not retry an unknown end exchange or release dependencies.
            # The original strong module members survive until process terminal;
            # only the owning Native process/Job can observe that actual terminal.
            raise self._close_failure
        if self._thread!=threading.get_ident() or _states.get(id(self)) is not self:
            raise EngineError('installation_record_source_denied','Original owning setup thread must close this state',403)
        self._closed=True
        try:
            # A failed authority/issuer close must retain its build, original
            # source and transport. First failure stops this dependency chain.
            for original in (self.qualified_authority,self.qualified_build,self.record_consumer,self.record_connection,self.trust_consumer,self.trust_connection):
                if original is not None:
                    original.close()
            self.source.disable()
            self.stream.close()
        except BaseException as error:
            self._close_failure=error
            # _states and _production_members intentionally remain strong. Closed
            # State cannot create new writers, and this is not a release receipt.
            raise
        self._close_complete=True
        _states.pop(id(self),None)
        _production_members.pop(id(self),None)


def record_frame(state,seq,event,fields):
    state.assert_current()
    stream=state.stream
    stream.deadline=time.monotonic()+10
    if stream.pending:
        raise EngineError('installation_record_frame_invalid','Original installation stage cannot be pipelined',422)
    header=stream.read(4)
    if len(header)!=4:
        raise EngineError('installation_record_unknown','Original installation stage ended without a complete frame',503)
    size=struct.unpack('<I',header)[0]
    if not 1<=size<=FRAME_LIMIT:
        raise EngineError('installation_record_frame_limit','Original installation stage frame exceeds its bound',413)
    data=stream.read(size)
    if len(data)!=size:
        raise EngineError('installation_record_unknown','Original installation stage ended with an unknown outcome',503)
    raw=_fields(_json(data),('wire','event','seq','instance_id',*fields))
    _uint(raw['seq'])
    if canonical_bytes(raw)!=data or (raw['wire'],raw['event'],raw['seq'],raw['instance_id'])!=(WIRE,event,seq,state.engine.instance_id):
        raise EngineError('installation_record_frame_invalid','Original installation stage identity/sequence differs',422)
    if stream.pending:
        raise EngineError('installation_record_frame_invalid','Following input cannot precede original stage ACK',422)
    return raw


def record_response(event,seq,**fields):
    data=canonical_bytes(dict(wire=WIRE,event=event,seq=seq,**fields))
    sys.stdout.buffer.write(struct.pack('<I',len(data))+data)
    sys.stdout.buffer.flush()


def record_error(error):
    allowed={'installation_record_frame_invalid':422,'installation_record_frame_limit':413,'installation_record_source_denied':403,
        'installation_record_binding_changed':409,'installation_record_admission_conflict':409,'installation_record_unavailable':503,
        'installation_record_unknown':503,'installation_record_timeout':503}
    if allowed.get(error.code)==error.status_code:return error.code,error.status_code
    if error.code in ('installation_channel_timeout','owner_instance_handshake_timeout'):
        return 'installation_record_timeout',503
    return {422:('installation_record_frame_invalid',422),413:('installation_record_frame_limit',413),403:('installation_record_source_denied',403),
        409:('installation_record_binding_changed',409)}.get(error.status_code,('installation_record_unavailable',503))


def continue_setup(state,request):
    """Original Owner steps retained, using this one actual Engine and Bundle."""
    from video_creator.cli.native_owner_setup import _response
    from video_creator.application.owner_setup_confirmation import NativeOwnerConfirmationConsumer
    from video_creator.application.native_execution_observer import NativeExecutionObserverFactory
    from video_creator.application.owner_setup_service import OwnerSetupService

    state.assert_current()
    if state._record_ready:
        assert_production_bound(state)
    engine,bundle,record=state.engine,state.bundle,state.binding.startup
    service,consumer,failure,result=None,None,None,1
    try:
        consumer=NativeOwnerConfirmationConsumer(engine=engine,bundle=bundle,startup_record=record,
            locator_bytes=state.binding.confirmation_locator_bytes,initialization_source=state.source)
        preparation=consumer.preparation_source()
        observer=NativeExecutionObserverFactory(installation=record.installation,instance_id=record.instance_id,
            locator_bytes=state.binding.installation_locator_bytes,external_receipt_path=record.external_receipt_path,
            expected_host_image=record.expected_host_image,expected_host_sha256=record.expected_host_sha256)
        service=OwnerSetupService(engine=engine,bundle=bundle,confirmation=consumer,options=request.options,
            installation_observer_factory=observer,installation_authority=state.qualified_authority,
            installation_session_guard=state.qualified_authority)
        if state.recovery:
            accepted=service.recover(state.recovery,preparation=preparation)
            if accepted.journal.prepared.request!=request:
                raise EngineError('owner_setup_recovery_changed','Recovery requires the original complete request',409)
        else:
            intent=service.prepare_first_goal(request.idempotency_key,request.goal,preparation=preparation)
            _response('prepared',intent)
            confirmed=consumer.accept_setup(intent)
            accepted=service.accept(confirmed,preparation=preparation)
        _response('accepted',service.status(accepted.journal.prepared.intent.setup_id))
        original=service.execute(accepted)
        _response('goal_accepted',original)
        result=0
    except EngineError as error:
        failure=error
    finally:
        try:
            if service is not None:service.close()
            elif consumer is not None:consumer.close(None)
        except EngineError as error:
            failure=failure or error
            result=1
        if failure is not None:print(json.dumps({'code':failure.code,'message':failure.message}),file=sys.stderr)
    return result


def production_response(event,**fields):
    data=canonical_bytes(dict(wire=PRODUCTION_WIRE,event=event,seq=6,**fields))
    sys.stdout.buffer.write(struct.pack('<I',len(data))+data)
    sys.stdout.buffer.flush()


def production_error(error):
    allowed={'setup_production_frame_invalid':422,'setup_production_frame_limit':413,
        'setup_production_source_denied':403,'setup_production_binding_changed':409,
        'setup_production_unavailable':503,'setup_production_unknown':503,'setup_production_timeout':503}
    if allowed.get(error.code)==error.status_code:return error.code,error.status_code
    if 'timeout' in error.code:return 'setup_production_timeout',503
    if 'unknown' in error.code:return 'setup_production_unknown',503
    return {422:('setup_production_frame_invalid',422),413:('setup_production_frame_limit',413),
        403:('setup_production_source_denied',403),409:('setup_production_binding_changed',409)}.get(
            error.status_code,('setup_production_unavailable',503))


def production_frame(state):
    state.assert_current()
    stream=state.stream
    stream.deadline=time.monotonic()+10
    if stream.pending:
        raise EngineError('setup_production_frame_invalid','Production carry cannot precede record ready',422)
    header=stream.read(4)
    if len(header)!=4:
        raise EngineError('setup_production_unknown','Production carry ended without a complete header',503)
    size=struct.unpack('<I',header)[0]
    if not 1<=size<=FRAME_LIMIT:
        raise EngineError('setup_production_frame_limit','Production carry exceeds its bound',413)
    data=stream.read(size)
    if len(data)!=size:
        raise EngineError('setup_production_unknown','Production carry ended with an unknown outcome',503)
    if stream.pending:
        raise EngineError('setup_production_frame_invalid','Goal cannot precede production bound',422)
    return data


def assert_production_bound(state):
    state.assert_current()
    member=_production_members.get(id(state))
    if (member is None or member[0] is not state or member[1] is not state.qualified_authority
            or member[2] is not state.qualified_build or member[4]!=threading.get_ident()):
        raise EngineError('setup_production_source_denied','Original same-state production binding is required',403)
    state.record_consumer.assert_current(state.record_receipt)
    state.qualified_authority.assert_current(member[3])


def bind_production_authority(state:TrustCommittedSetupState,*,carrier_bytes:bytes)->None:
    """ADR0047 private original-child ingress; never assembles another Engine."""
    from pathlib import Path
    from video_creator.cli.native_startup_record import NativeStartupRecord
    from video_creator.application.native_installation import connect_qualified_native_installation

    if type(state) is not TrustCommittedSetupState:
        raise EngineError('setup_production_source_denied','Original retained setup state is required',403)
    state.assert_current()
    if (not state._record_ready or state.record_receipt is None or id(state) in _production_members
            or state.qualified_authority is not None or state.qualified_build is not None):
        raise EngineError('setup_production_source_denied','Only original post-sequence-five state may bind once',403)
    state.record_consumer.assert_current(state.record_receipt)
    raw=_fields(_json(carrier_bytes),('wire','event','seq','instance_id','startup_record','production_locator'))
    _uint(raw['seq'])
    if (canonical_bytes(raw)!=carrier_bytes or
            (raw['wire'],raw['event'],raw['seq'],raw['instance_id'])!=(PRODUCTION_WIRE,'bind_production',6,state.engine.instance_id)
            or type(raw['startup_record']) is not dict or type(raw['production_locator']) is not dict):
        raise EngineError('setup_production_frame_invalid','Production carry differs from the fixed canonical stage',422)
    startup=NativeStartupRecord.parse(canonical_bytes(raw['startup_record']))
    context=startup.context
    original=state.binding.startup.installation
    initial=state.source.record
    if ((context.instance_id,context.role)!=(state.engine.instance_id,'api') or
            (context.registration_sha256,context.resource_manifest_sha256,context.runtime_manifest_sha256,
             context.expected_files,context.engine_file_names)!=(original.registration_sha256,
                original.resource_manifest_sha256,original.runtime_manifest_sha256,original.expected_files,original.engine_file_names)
            or startup.installed_native_image!=Path(initial.expected_host_image)
            or startup.installed_native_image!=Path(original.installed_native_image)
            or startup.installed_native_image_sha256!=initial.expected_host_sha256
            or startup.installed_native_image_sha256!=original.installed_native_image_sha256):
        raise EngineError('setup_production_binding_changed','Production context differs from original installed maps or host',409)
    locator=_fields(raw['production_locator'],('pipe','session','instance_id','role','server'))
    if ((locator['instance_id'],locator['role'])!=(state.engine.instance_id,'api')
            or locator['server']!=state.source.locator['server']):
        raise EngineError('setup_production_source_denied','Production locator differs from original bootstrap peer',403)
    authority,build=connect_qualified_native_installation(engine=state.engine,bundle=state.bundle,
        locator_bytes=canonical_bytes(locator),context=context,installed_native_image=startup.installed_native_image,
        installed_native_image_sha256=startup.installed_native_image_sha256)
    # Retain immediately so unknown observation/cleanup keeps original ownership.
    state.qualified_authority,state.qualified_build=authority,build
    evidence=authority.observe()
    authority.assert_current(evidence)
    facts=authority._original(evidence)
    receipt=state.record_receipt
    if (facts.binding is None or facts.binding.record.ref()!=receipt.record_ref
            or facts.binding.registry_revision!=receipt.registry_revision
            or facts.binding.revocation_floor!=receipt.registry_revision):
        raise EngineError('setup_production_binding_changed','Live production qualification differs from committed original record',409)
    state.record_consumer.assert_current(receipt)
    _production_members[id(state)]=(state,authority,build,evidence,threading.get_ident())
    assert_production_bound(state)
