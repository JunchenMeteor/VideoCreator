"""Fixed pre-API indexed Owner setup entry; no renderer approval endpoint."""

import argparse
import json
import struct
import sys
import time
from pathlib import Path

from video_creator.application.bundles import BundleService
from video_creator.application.engine import EngineService
from video_creator.application.native_execution_observer import (
    NativeExecutionObserverFactory,
)
from video_creator.application.owner_setup_confirmation import (
    NativeOwnerConfirmationConsumer,
)
from video_creator.application.owner_setup_service import OwnerSetupService
from video_creator.cli.native_owner_startup import NativeOwnerStartupRecord
from video_creator.domain.errors import EngineError
from video_creator.domain.owner_setup import SETUP_FRAME_LIMIT
from video_creator.domain.owner_setup_journal import SetupPreparationRequest
from video_creator.infrastructure.held_authority import _json
from video_creator.infrastructure.native_installation_observer import (
    parse_installation_locator,
)
from video_creator.infrastructure.native_owner_confirmation import (
    parse_confirmation_locator,
)


def _request(stream):
    header = stream.read(4)
    if len(header) != 4:
        raise EngineError('owner_setup_request_invalid', 'Original setup request frame is incomplete', 422)
    length = struct.unpack('<I', header)[0]
    if not 0 < length <= SETUP_FRAME_LIMIT - 16 * 1024:
        raise EngineError('owner_setup_request_limit', 'Complete setup request exceeds its bounded frame', 413)
    data = stream.read(length)
    if len(data) != length:
        raise EngineError('owner_setup_request_invalid', 'Original setup request bytes are incomplete', 422)
    raw = _json(data)
    try:
        request = SetupPreparationRequest.model_validate(raw)
    except (ValueError, TypeError) as error:
        raise EngineError('owner_setup_request_invalid', 'Complete original Goal/options are required', 422) from error
    canonical = json.dumps(request.model_dump(mode='json'), ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode('utf-8')
    if data != canonical:
        raise EngineError('owner_setup_request_invalid', 'Request must contain exact full canonical typed fields', 422)
    return request


def _response(event, document):
    # Status/proposal/receipt only. No strong sources or management secrets.
    data = json.dumps({'wire': 'native-owner-setup-result-v1', 'event': event,
        'document': document.model_dump(mode='json')}, ensure_ascii=False,
        sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    if len(data) > SETUP_FRAME_LIMIT:
        raise EngineError('owner_setup_response_limit', 'Complete original setup result exceeds its frame', 413)
    sys.stdout.buffer.write(struct.pack('<I', len(data)) + data)
    sys.stdout.buffer.flush()


def _arguments():
    parser = argparse.ArgumentParser(prog='video-creator-owner-setup')
    parser.add_argument('--data-dir', required=True, type=Path)
    parser.add_argument('--recover-setup-id')
    return parser.parse_args()


def _continue_setup(*, engine, record, installation_locator_bytes,
                    confirmation_locator_bytes, request, recover_setup_id, initialization_source=None):
    """One existing setup implementation, operating on the retained Engine."""
    service, consumer, failure, result = None, None, None, 1
    try:
        if engine.instance_id != record.instance_id:
            raise EngineError('owner_setup_instance_denied', 'Original startup differs from this actual DataDir instance', 403)
        bundle = BundleService(engine)
        consumer = NativeOwnerConfirmationConsumer(engine=engine, bundle=bundle,
            startup_record=record, locator_bytes=confirmation_locator_bytes,
            initialization_source=initialization_source)
        preparation = consumer.preparation_source()
        observer = NativeExecutionObserverFactory(installation=record.installation, instance_id=record.instance_id,
            locator_bytes=installation_locator_bytes, external_receipt_path=record.external_receipt_path,
            expected_host_image=record.expected_host_image, expected_host_sha256=record.expected_host_sha256)
        service = OwnerSetupService(engine=engine, bundle=bundle, confirmation=consumer,
            options=request.options, installation_observer_factory=observer)
        if recover_setup_id:
            accepted = service.recover(recover_setup_id, preparation=preparation)
            if accepted.journal.prepared.request != request:
                raise EngineError('owner_setup_recovery_changed', 'Recovery request must equal its original complete Goal/options/key', 409)
        else:
            intent = service.prepare_first_goal(request.idempotency_key, request.goal, preparation=preparation)
            _response('prepared', intent)
            confirmed = consumer.accept_setup(intent)
            accepted = service.accept(confirmed, preparation=preparation)
        _response('accepted', service.status(accepted.journal.prepared.intent.setup_id))
        original = service.execute(accepted)
        _response('goal_accepted', original)
        result = 0
    except EngineError as error:
        failure = error
    finally:
        try:
            if service is not None:
                service.close()
            elif consumer is not None:
                consumer.close(None)
        except EngineError as error:
            failure = failure or error
            result = 1
    if failure is not None:
        print(json.dumps({'code': failure.code, 'message': failure.message}), file=sys.stderr)
    return result


def main(*, startup_record: bytes, installation_locator_bytes: bytes,
         confirmation_locator_bytes: bytes) -> int:
    """Original six-field/three-byte-argument indexed entry remains compatible."""
    try:
        record = NativeOwnerStartupRecord.parse(startup_record)
        parse_installation_locator(installation_locator_bytes, record.instance_id)
        parse_confirmation_locator(confirmation_locator_bytes, record.instance_id)
        args = _arguments()
        request = _request(sys.stdin.buffer)
        engine = EngineService(args.data_dir)
        return _continue_setup(engine=engine, record=record,
            installation_locator_bytes=installation_locator_bytes,
            confirmation_locator_bytes=confirmation_locator_bytes,
            request=request, recover_setup_id=args.recover_setup_id)
    except EngineError as error:
        print(json.dumps({'code': error.code, 'message': error.message}), file=sys.stderr)
        return 1


class _InitializationInput:
    """Original stdin duplicate, polling finite bytes without a reader thread."""

    def __init__(self, deadline):
        from video_creator.cli.lifecycle import ControlPipe

        try:
            self.pipe = ControlPipe(sys.stdin.fileno())
        except EngineError as error:
            if error.code != 'control_pipe_required':
                raise
            raise EngineError('owner_instance_handshake_invalid', 'Original initialization requires a stdin pipe', 422) from error
        self.pending, self.deadline = bytearray(), deadline
        self.eof = False

    def read(self, count):
        from video_creator.infrastructure.native_instance_source import assert_deadline

        while len(self.pending) < count and not self.eof:
            if self.deadline is not None:
                assert_deadline(self.deadline)
            block = self.pipe.read_available()
            if block is None:
                time.sleep(0.01)
            elif not block:
                self.eof = True
            else:
                self.pending.extend(block)
        data = bytes(self.pending[:count])
        del self.pending[:count]
        return data

    def close(self):
        self.pipe.close()


def _instance_response(event, seq, **fields):
    from video_creator.cli.native_instance_protocol import IDENTITY_LIMIT, WIRE
    from video_creator.infrastructure.native_owner_confirmation import canonical_wire

    data = canonical_wire({'wire': WIRE, 'event': event, 'seq': seq, **fields})
    if len(data) > IDENTITY_LIMIT:
        raise EngineError('owner_instance_handshake_limit', 'Instance identity result exceeds its frame', 413)
    sys.stdout.buffer.write(struct.pack('<I', len(data)) + data)
    sys.stdout.buffer.flush()


def initialize_and_bind(*, initialization_record: bytes) -> int:
    """Fixed ADR0042 entry: actual source first, exactly one original Engine."""
    from video_creator.cli.native_instance_protocol import (
        NativeInstanceInitializationRecord,
        NativeInstanceSetupBinding,
        frame_size,
        invalid,
    )
    from video_creator.infrastructure.held_authority import _text
    from video_creator.infrastructure.native_instance_source import (
        assert_deadline,
        open_instance_source,
    )

    source, stream, seq, setup_bound = None, None, 1, False
    deadline = time.monotonic() + 20
    try:
        record = NativeInstanceInitializationRecord.parse(initialization_record)
        args = _arguments()
        source = open_instance_source(record, args.data_dir, deadline=deadline)
        source.assert_current()
        stream = _InitializationInput(deadline)
        initial = stream.pipe.read_available()
        if initial is not None:
            raise invalid('Original setup input ended or sent bytes before instance_ready')
        database_path = args.data_dir / 'Metadata.sqlite'
        if database_path.is_symlink() or database_path.is_junction():
            raise EngineError('owner_instance_binding_changed', 'Original database target is a filesystem link', 409)
        assert_deadline(deadline)
        engine = EngineService(args.data_dir)
        try:
            _text(engine.instance_id)  # Same original Backend instance grammar.
        except EngineError as error:
            raise EngineError('owner_instance_binding_changed', 'Actual persisted instance identity is invalid', 409) from error
        source.retain_engine(engine)
        source.assert_engine_current(engine)
        _instance_response('instance_ready', 1, instance_id=engine.instance_id)
        assert_deadline(deadline)
        seq = 2
        header = stream.read(4)
        if len(header) != 4:
            raise invalid('Original setup binding header is incomplete')
        length = struct.unpack('<I', header)[0]
        frame_size(length)
        data = stream.read(length)
        if len(data) != length:
            raise invalid('Original setup binding is incomplete')
        binding = NativeInstanceSetupBinding.parse(data, initialization=record, instance_id=engine.instance_id)
        if stream.pending:
            raise invalid('Setup cannot pipeline a Goal before original setup_bound')
        source.assert_engine_current(engine)
        _instance_response('setup_bound', 2, instance_id=engine.instance_id)
        assert_deadline(deadline)
        source.complete_setup_binding(engine)
        setup_bound = True
        # Later genuine Owner review has its original service deadlines.
        stream.deadline = None
        request = _request(stream)
        source.assert_setup_engine_current(engine)
        return _continue_setup(engine=engine, record=binding.startup,
            installation_locator_bytes=binding.installation_locator_bytes,
            confirmation_locator_bytes=binding.confirmation_locator_bytes,
            request=request, recover_setup_id=args.recover_setup_id, initialization_source=source)
    except EngineError as error:
        if not setup_bound:
            _instance_response('error', seq, code=error.code, status=error.status_code)
        print(json.dumps({'code': error.code, 'message': error.message}), file=sys.stderr)
        return 1
    finally:
        if source is not None:
            source.disable()
        if stream is not None:
            stream.close()


TRUST_HANDSHAKE_WIRE = 'native-owner-instance-trust-handshake-v1'
from video_creator.cli.native_qualified_setup import TrustCommittedSetupState,_TOKEN as _SETUP_STATE_TOKEN


def _trust_error(error):
    if error.code in ('owner_instance_handshake_invalid', 'owner_instance_handshake_limit',
                      'owner_instance_source_denied', 'owner_instance_binding_changed',
                      'owner_instance_handshake_timeout', 'owner_instance_source_unavailable'):
        return error.code, error.status_code
    if error.code == 'installation_channel_timeout':
        return 'owner_instance_handshake_timeout', 503
    return {422: ('owner_instance_handshake_invalid', 422),
            413: ('owner_instance_handshake_limit', 413),
            403: ('owner_instance_source_denied', 403),
            409: ('owner_instance_binding_changed', 409)}.get(
                error.status_code, ('owner_instance_source_unavailable', 503))


def _trust_response(event, **fields):
    from video_creator.domain.installation_qualification import canonical_bytes

    data = canonical_bytes({'wire': TRUST_HANDSHAKE_WIRE, 'event': event, 'seq': 3, **fields})
    sys.stdout.buffer.write(struct.pack('<I', len(data)) + data)
    sys.stdout.buffer.flush()


def _admit_bound_trust(*, engine, source, stream, bundle):
    from video_creator.application.installation_trust_consumer import NativeInstallationTrustConsumer
    from video_creator.domain.installation_qualification import canonical_bytes
    from video_creator.infrastructure.held_authority import FRAME_LIMIT, _fields, _uint
    from video_creator.infrastructure.native_installation_trust import OwnedInstallationTrustConnection

    stream.deadline = time.monotonic() + 10
    if stream.pending:
        raise EngineError('owner_instance_handshake_invalid', 'Trust cannot precede original setup_bound', 422)
    header = stream.read(4)
    if len(header) != 4:
        raise EngineError('owner_instance_handshake_invalid', 'Original trust stage header is incomplete', 422)
    size = struct.unpack('<I', header)[0]
    if not 1 <= size <= FRAME_LIMIT:
        raise EngineError('owner_instance_handshake_limit', 'Original trust stage frame exceeds its bound', 413)
    data = stream.read(size)
    if len(data) != size:
        raise EngineError('owner_instance_handshake_invalid', 'Original trust stage bytes are incomplete', 422)
    raw = _fields(_json(data), ('wire', 'event', 'seq', 'instance_id', 'locator'))
    _uint(raw['seq'])
    if canonical_bytes(raw) != data or (raw['wire'], raw['event'], raw['seq'], raw['instance_id']) != (
            TRUST_HANDSHAKE_WIRE, 'admit_installation_trust', 3, engine.instance_id):
        raise EngineError('owner_instance_handshake_invalid', 'Trust stage differs from original same-child identity', 422)
    if stream.pending:
        raise EngineError('owner_instance_handshake_invalid', 'Goal cannot precede original trust commit', 422)
    source.assert_setup_engine_current(engine)
    connection = OwnedInstallationTrustConnection(engine=engine, initialization_source=source,
        locator_bytes=canonical_bytes(raw['locator']))
    consumer = NativeInstallationTrustConsumer()
    try:
        original = consumer.admit_source(engine=engine, bundle=bundle, bound_connection=connection)
        consumer.assert_current(original)
        _trust_response('installation_trust_committed', instance_id=engine.instance_id)
        return consumer,connection,original
    except BaseException:
        consumer.close()
        connection.close()
        raise


def _initialize_bind_and_admit_trust_state(*, initialization_record: bytes) -> 'TrustCommittedSetupState':
    """Fixed ADR0042 entry: actual source first, exactly one original Engine."""
    from video_creator.cli.native_instance_protocol import (
        NativeInstanceInitializationRecord,
        NativeInstanceSetupBinding,
        frame_size,
        invalid,
    )
    from video_creator.infrastructure.held_authority import _text
    from video_creator.infrastructure.native_instance_source import (
        assert_deadline,
        open_instance_source,
    )

    source, stream, seq, setup_bound = None, None, 1, False
    trust_committed = False
    state,trust_consumer,trust_connection=None,None,None
    deadline = time.monotonic() + 20
    try:
        record = NativeInstanceInitializationRecord.parse(initialization_record)
        args = _arguments()
        source = open_instance_source(record, args.data_dir, deadline=deadline)
        source.assert_current()
        stream = _InitializationInput(deadline)
        initial = stream.pipe.read_available()
        if initial is not None:
            raise invalid('Original setup input ended or sent bytes before instance_ready')
        database_path = args.data_dir / 'Metadata.sqlite'
        if database_path.is_symlink() or database_path.is_junction():
            raise EngineError('owner_instance_binding_changed', 'Original database target is a filesystem link', 409)
        assert_deadline(deadline)
        engine = EngineService(args.data_dir)
        try:
            _text(engine.instance_id)  # Same original Backend instance grammar.
        except EngineError as error:
            raise EngineError('owner_instance_binding_changed', 'Actual persisted instance identity is invalid', 409) from error
        source.retain_engine(engine)
        source.assert_engine_current(engine)
        _instance_response('instance_ready', 1, instance_id=engine.instance_id)
        assert_deadline(deadline)
        seq = 2
        header = stream.read(4)
        if len(header) != 4:
            raise invalid('Original setup binding header is incomplete')
        length = struct.unpack('<I', header)[0]
        frame_size(length)
        data = stream.read(length)
        if len(data) != length:
            raise invalid('Original setup binding is incomplete')
        binding = NativeInstanceSetupBinding.parse(data, initialization=record, instance_id=engine.instance_id)
        if stream.pending:
            raise invalid('Setup cannot pipeline a Goal before original setup_bound')
        source.assert_engine_current(engine)
        _instance_response('setup_bound', 2, instance_id=engine.instance_id)
        assert_deadline(deadline)
        source.complete_setup_binding(engine)
        setup_bound = True
        # Later genuine Owner review has its original service deadlines.
        seq = 3
        bundle=BundleService(engine)
        trust_consumer,trust_connection,trust_source=_admit_bound_trust(engine=engine, source=source, stream=stream,bundle=bundle)
        trust_committed = True
        state=TrustCommittedSetupState(_SETUP_STATE_TOKEN,engine,bundle,source,binding,stream,args.recover_setup_id,
            trust_consumer,trust_connection,trust_source)
        return state
    except EngineError as error:
        if setup_bound and not trust_committed:
            code, status = _trust_error(error)
            _trust_response("error", code=code, status=status)
        elif not setup_bound:
            _instance_response('error', seq, code=error.code, status=error.status_code)
        print(json.dumps({'code': error.code, 'message': error.message}), file=sys.stderr)
        raise
    finally:
        if state is None:
            if trust_consumer is not None:trust_consumer.close()
            if trust_connection is not None:trust_connection.close()
            if source is not None:source.disable()
            if stream is not None:stream.close()


def initialize_bind_and_admit_trust(*, initialization_record: bytes) -> int:
    """Compatible trust-only plan: seq3 followed by the original Goal."""
    from video_creator.cli.native_qualified_setup import continue_setup
    state=None
    result=1
    try:
        state=_initialize_bind_and_admit_trust_state(initialization_record=initialization_record)
        state.stream.deadline=None
        request=_request(state.stream)
        result=continue_setup(state,request)
    except EngineError as error:
        print(json.dumps({'code':error.code,'message':error.message}),file=sys.stderr)
    finally:
        if state is not None:
            try:state.close()
            except EngineError as error:
                print(json.dumps({'code':error.code,'message':error.message}),file=sys.stderr)
                result=1
    return result


def initialize_bind_admit_trust_and_record(*, initialization_record: bytes) -> int:
    """ADR0045 first-install plan, same Engine and retained original source."""
    from video_creator.cli.native_qualified_setup import continue_setup,record_frame,record_response,record_error
    from video_creator.domain.installation_qualification import canonical_bytes,QualificationRef,parse_exact
    from video_creator.infrastructure.native_installation_record import OwnedInstallationRecordConnection
    from video_creator.application.installation_record_consumer import NativeInstallationRecordConsumer
    from video_creator.cli.native_qualified_setup import (
        bind_production_authority,production_frame,production_response,production_error,
    )
    state=None
    seq,result,record_ready,production_bound=4,1,False,False
    try:
        state=_initialize_bind_and_admit_trust_state(initialization_record=initialization_record)
        raw=record_frame(state,4,'admit_installation_record',('locator',))
        state.record_connection=OwnedInstallationRecordConnection(engine=state.engine,initialization_source=state.source,locator_bytes=canonical_bytes(raw['locator']))
        state.record_consumer=NativeInstallationRecordConsumer()
        receipt=state.record_consumer.admit_record(engine=state.engine,bundle=state.bundle,bound_connection=state.record_connection)
        state.record_receipt=receipt
        record_response('installation_record_committed',4,instance_id=state.engine.instance_id,
            action_id=receipt.action_id,record_ref=receipt.record_ref.model_dump(mode='json'),registry_revision=receipt.registry_revision)
        seq=5
        raw=record_frame(state,5,'installation_record_current',('action_id','record_ref','registry_revision'))
        from video_creator.infrastructure.held_authority import _uint
        _uint(raw['registry_revision'],positive=True)
        ref=parse_exact(QualificationRef,canonical_bytes(raw['record_ref']))
        if (raw['action_id'],ref,raw['registry_revision'])!=(receipt.action_id,receipt.record_ref,receipt.registry_revision):
            raise EngineError('installation_record_binding_changed','Native current differs from original committed action/ref',409)
        state.record_consumer.assert_current(receipt)
        record_response('installation_record_ready',5,instance_id=state.engine.instance_id)
        record_ready=True
        state._record_ready=True
        seq=6
        bind_production_authority(state,carrier_bytes=production_frame(state))
        production_response('production_bound',instance_id=state.engine.instance_id)
        production_bound=True
        state.stream.deadline=None
        request=_request(state.stream)
        result=continue_setup(state,request)
    except EngineError as error:
        if state is not None and not record_ready:
            code,status=record_error(error)
            record_response('error',seq,code=code,status=status)
        elif state is not None and not production_bound:
            code,status=production_error(error)
            production_response('error',code=code,status=status)
        print(json.dumps({'code':error.code,'message':error.message}),file=sys.stderr)
    finally:
        if state is not None:
            try:state.close()
            except EngineError as error:
                print(json.dumps({'code':error.code,'message':error.message}),file=sys.stderr)
                result=1
    return result
