"""First original installer record commit/recovery, never a production lease."""

import threading
from dataclasses import dataclass
from video_creator.domain.errors import EngineError
from video_creator.domain.installation_qualification import TrustSnapshot, canonical_bytes, body_sha, parse_exact
from video_creator.domain.committed_installation_evidence import InstallationActionRequest
from video_creator.application.installation_trust_consumer import (
    _InstallationLock, qualification_control, registry_revision, next_revision, trust_ref,
    install_snapshot, trust_row_admission,
)
from video_creator.application.committed_installation_evidence import install_committed_evidence,read_committed_evidence,export_committed_evidence
from video_creator.infrastructure.native_installation_record import OwnedInstallationRecordConnection
from video_creator.infrastructure.native_qualification_trust import open_native_qualification_trust


@dataclass(frozen=True,eq=False,repr=False)
class InstallationRecordAdmissionReceipt:
    action_id: str
    record_ref: object
    registry_revision: int
    _consumer: object
    _connection: object
    _source: object
    _materials: object
    _bundle: object
    _epoch: object
    _thread: int


class NativeInstallationRecordConsumer:
    def __init__(self):
        self._epoch,self._receipts,self._materials=object(),{},[]

    def _member(self,receipt):
        if (type(receipt) is not InstallationRecordAdmissionReceipt or self._receipts.get(id(receipt)) is not receipt
                or receipt._consumer is not self or receipt._epoch is not self._epoch or receipt._thread!=threading.get_ident()):
            raise EngineError('installation_record_source_denied','Original committed installer receipt member is required',403)

    @staticmethod
    def _local(connection,source,materials):
        source._connection.assert_action(source,connection)
        materials.assert_member()
        now=materials.engine.clock()
        if not source.admission.record.valid_from_us<=now<source.admission.record.expires_at_us or source.admission.accepted_at_us>now:
            raise EngineError('installation_record_binding_changed','Original qualification/action expired or has not occurred before commit',409)
        if any(original._closed for original in [materials.build,materials._held_index,*materials._installation_holds,*(hold.build for hold in materials._holds)]):
            raise EngineError('installation_record_binding_changed','Original installation material guard was released',409)
        pinned=materials._rows
        trust=connection.execute('SELECT * FROM installation_qualification_trust WHERE admission_id=?',
            (materials.snapshot.trust_admission_ref.document_id,)).fetchone()
        event=connection.execute('SELECT * FROM installation_qualification_events WHERE registry_revision=?',
            (materials.snapshot.trust_admission_ref.revision,)).fetchone()
        if pinned is None or trust is None or event is None or tuple(trust)!=pinned[1]:
            raise EngineError('installation_record_binding_changed','Original same-connection admitted trust source changed',409)
        # Trust event is always its original revision, not the latest record event.
        if trust_row_admission(trust)!=materials.admission or trust_ref(trust)!=source.admission.trust_admission_ref:
            raise EngineError('installation_record_binding_changed','Original same-connection trust receipt/ref changed',409)
        if event['kind']!='trust_admit' or event['receipt_json']!=canonical_bytes(materials.admission).decode('utf-8'):
            raise EngineError('installation_record_binding_changed','Original immutable trust event changed',409)

    def admit_record(self,*,engine,bundle,bound_connection):
        if type(bound_connection) is not OwnedInstallationRecordConnection or bound_connection.engine is not engine or bundle.engine is not engine:
            raise EngineError('installation_record_source_denied','Original same-Engine installer connection is required',403)
        source=bound_connection.consume()
        action=source.admission
        control=qualification_control(engine)
        lock=_InstallationLock(control.path.parent/'InstallationTrustInstallLock.json',engine.instance_id)
        owner=bundle.principals.owner_subject
        with lock.locked(),control.locked():
            bound_connection.assert_action(source)
            materials=open_native_qualification_trust(engine=engine,bundle=bundle,connection=bound_connection,build=bound_connection.source.host)
            self._materials.append(materials)
            if (action.trust_admission_ref!=materials.snapshot.trust_admission_ref
                    or action.material_index_sha256!=materials._held_index.expected_sha256):
                raise EngineError('installation_record_binding_changed','Original installer trust/material index changed',409)
            materials.verify_record(action.record,bound_connection.context)
            request=InstallationActionRequest(action_id=action.action_id,kind='record_admit',trust_admission_ref=action.trust_admission_ref,
                record_ref=action.record.ref(),expected_registry_revision=action.expected_registry_revision)
            request_sha=body_sha(request)
            reserved=next_revision(action.expected_registry_revision)
            with engine.db.connect() as reader:
                current=reader.execute('SELECT * FROM installation_qualification_current WHERE singleton=1').fetchone()
                existing=reader.execute('SELECT request_sha256,result_json FROM commands WHERE owner=? AND scope=? AND idempotency_key=?',
                    (owner,'installation-qualification',action.action_id)).fetchone()
                if existing is not None:
                    if existing['request_sha256']!=request_sha:
                        raise EngineError('installation_record_admission_conflict','Original installer key belongs to another action',409)
                    snapshot=parse_exact(TrustSnapshot,existing['result_json'].encode('utf-8'))
                    event=reader.execute('SELECT * FROM installation_qualification_events WHERE action_id=?',(action.action_id,)).fetchone()
                    record=reader.execute('SELECT * FROM installation_qualification_records WHERE record_id=? AND revision=?',
                        (action.record.record_id,action.record.revision)).fetchone()
                    if (event is None or event['receipt_json']!=canonical_bytes(action).decode('utf-8')
                            or event['request_sha256']!=request_sha or event['registry_revision']!=reserved
                            or record is None or record['record_json']!=canonical_bytes(action.record).decode('utf-8')
                            or snapshot.current_record_ref!=action.record.ref() or snapshot.registry_revision!=reserved
                            or snapshot.trust_admission_ref!=action.trust_admission_ref or snapshot.state!='qualified'
                            or current is None or tuple(current)!=(1,reserved,action.trust_admission_ref.document_id,action.record.record_id,action.record.revision,'qualified')):
                        raise EngineError('installation_record_unknown','Original record action cannot be recovered from these committed facts',503)
                else:
                    if (current is None or tuple(current)!=(1,action.expected_registry_revision,action.trust_admission_ref.document_id,None,None,'not_ready')
                            or reader.execute("SELECT 1 FROM metadata WHERE key='owner_management_binding'").fetchone() is not None
                            or reader.execute('SELECT 1 FROM installation_qualification_records LIMIT 1').fetchone() is not None):
                        raise EngineError('installation_record_admission_conflict','Initial installer route requires original empty record/Owner state',409)
                    snapshot=TrustSnapshot(format='installation-qualification-trust-snapshot-v1',instance_id=engine.instance_id,
                        registry_revision=reserved,trust_admission_ref=action.trust_admission_ref,current_record_ref=action.record.ref(),state='qualified')
            retained=control.read()
            if existing is not None:
                if retained.minimum_revision!=reserved or retained.pending_request_sha256 not in (None,request_sha):
                    raise EngineError('installation_record_unknown','Original higher or foreign retained floor cannot be repaired',503)
            else:
                if control.reserve(action.expected_registry_revision,request_sha)!=reserved:
                    raise EngineError('installation_record_binding_changed','Original installation floor changed',409)
                bound_connection.assert_action(source)
                for original in [materials._held_index,*materials._installation_holds,*(hold.build for hold in materials._holds)]:original.assert_current()
                with engine.db.transaction() as writer:
                    self._local(writer,source,materials)
                    current=writer.execute('SELECT * FROM installation_qualification_current WHERE singleton=1').fetchone()
                    if (current is None or tuple(current)!=(1,action.expected_registry_revision,action.trust_admission_ref.document_id,None,None,'not_ready')
                            or writer.execute("SELECT 1 FROM metadata WHERE key='owner_management_binding'").fetchone() is not None
                            or writer.execute('SELECT 1 FROM installation_qualification_records LIMIT 1').fetchone() is not None):
                        raise EngineError('installation_record_admission_conflict','Original initial registry changed before installer commit',409)
                    writer.execute('INSERT INTO installation_qualification_records VALUES(?,?,?,?,?)',(
                        action.record.record_id,action.record.revision,action.record_sha256,canonical_bytes(action.record).decode('utf-8'),action.trust_admission_ref.document_id))
                    writer.execute('INSERT INTO installation_qualification_events VALUES(?,?,?,?,?,?,?,?,?)',(
                        reserved,'record_admit',action.action_id,request_sha,action.trust_admission_ref.document_id,action.record.record_id,action.record.revision,canonical_bytes(action).decode('utf-8'),action.accepted_at_us))
                    writer.execute("UPDATE installation_qualification_current SET registry_revision=?,record_id=?,record_revision=?,state='qualified' WHERE singleton=1",
                        (reserved,action.record.record_id,action.record.revision))
                    writer.execute('INSERT INTO commands VALUES(?,?,?,?,?)',(owner,'installation-qualification',action.action_id,request_sha,canonical_bytes(snapshot).decode('utf-8')))
                    self._local(writer,source,materials)
                    if tuple(writer.execute('SELECT * FROM installation_qualification_current WHERE singleton=1').fetchone())!=(1,reserved,action.trust_admission_ref.document_id,action.record.record_id,action.record.revision,'qualified'):
                        raise EngineError('installation_record_binding_changed','Original post-write current row changed',409)
            install_committed_evidence(engine=engine,owner=owner,snapshot=snapshot)
            install_snapshot(engine,snapshot)
            if control.read().pending_request_sha256 is not None:control.complete(reserved,request_sha)
            receipt=InstallationRecordAdmissionReceipt(action.action_id,action.record.ref(),reserved,self,bound_connection,source,materials,bundle,self._epoch,threading.get_ident())
            self._receipts[id(receipt)]=receipt
            return receipt

    def assert_current(self,receipt):
        self._member(receipt)
        receipt._connection.assert_action(receipt._source)
        from video_creator.application.installation_trust_consumer import read_snapshot
        engine=receipt._connection.engine
        snapshot=read_snapshot(engine)
        retained=qualification_control(engine).read()
        evidence=read_committed_evidence(engine)
        committed=export_committed_evidence(engine=engine,owner=receipt._bundle.principals.owner_subject,snapshot=snapshot)
        if (snapshot.state!='qualified' or snapshot.current_record_ref!=receipt.record_ref or snapshot.registry_revision!=receipt.registry_revision
                or retained.pending_request_sha256 is not None or retained.minimum_revision!=receipt.registry_revision
                or evidence.registry_revision!=receipt.registry_revision or evidence.record_commit is None
                or evidence.record_commit.source_receipt!=receipt._source.admission or evidence!=committed):
            raise EngineError('installation_record_binding_changed','Original committed current/source/floor changed before native confirmation',409)
        with engine.db.connect() as reader:
            self._local(reader,receipt._source,receipt._materials)
            if registry_revision(reader)!=receipt.registry_revision:
                raise EngineError('installation_record_binding_changed','Actual committed registry changed before native current',409)

    def close(self):
        failure=None
        self._epoch=object();self._receipts.clear()
        for source in self._materials:
            try:source.close()
            except BaseException as error:failure=failure or error
        if failure is not None:raise failure
        self._materials.clear()
