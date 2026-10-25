"""Export only real committed immutable rows before snapshot/control completion."""

import os
from video_creator.domain.errors import EngineError
from video_creator.domain.committed_installation_evidence import (
    CommittedInstallationEvidence, InstallationActionRequest, TrustCommit, RecordCommit,
    PersistedRecordReceipt,
)
from video_creator.domain.installation_qualification import QualificationRef, body_sha, canonical_bytes, parse_exact
from video_creator.infrastructure.owner_identity import inspect_owner_directory

LIMIT=4*1024*1024


def evidence_path(engine):
    return engine.db.data_dir/'Control'/'CommittedInstallationEvidence.json'


def read_committed_evidence(engine):
    path=evidence_path(engine)
    inspect_owner_directory(path.parent)
    if path.is_symlink() or path.is_junction() or not path.is_file() or path.stat().st_size>LIMIT:
        raise EngineError('qualification_unavailable','Original committed installation evidence is unavailable',503)
    value=parse_exact(CommittedInstallationEvidence,path.read_bytes(),limit=LIMIT)
    if value.instance_id!=engine.instance_id:
        raise EngineError('qualification_changed','Committed evidence belongs to another instance',409)
    return value


def _request(source,record_ref):
    return InstallationActionRequest(action_id=source.action_id,kind=source.kind if hasattr(source,'kind') else 'trust_admit',
        trust_admission_ref=source.trust_admission_ref if hasattr(source,'trust_admission_ref') else record_ref,
        record_ref=record_ref if hasattr(source,'kind') else None,
        expected_registry_revision=source.expected_registry_revision if hasattr(source,'kind') else 0)


def export_committed_evidence(*,engine,owner,snapshot):
    from video_creator.application.installation_trust_consumer import trust_row_admission,trust_ref

    with engine.db.connect() as reader:
        current=reader.execute('SELECT * FROM installation_qualification_current WHERE singleton=1').fetchone()
        if current is None or (current['registry_revision'],current['trust_admission_id'],current['state'])!=(snapshot.registry_revision,snapshot.trust_admission_ref.document_id,snapshot.state):
            raise EngineError('qualification_changed','Original committed current differs from snapshot',409)
        row=reader.execute('SELECT * FROM installation_qualification_trust WHERE admission_id=?',(current['trust_admission_id'],)).fetchone()
        receipt=trust_row_admission(row)
        ref=trust_ref(row)
        if ref!=snapshot.trust_admission_ref:
            raise EngineError('qualification_changed','Original committed trust ref changed',409)
        event=reader.execute('SELECT * FROM installation_qualification_events WHERE action_id=?',(receipt.action_id,)).fetchone()
        request=_request(receipt,ref)
        _check_event(reader,owner,event,receipt,request,ref,None)
        trust=TrustCommit(admission_ref=ref,action_ref=QualificationRef(document_id=receipt.action_id,revision=event['registry_revision'],sha256=body_sha(receipt)),
            request=request,request_sha256=event['request_sha256'],registry_revision=event['registry_revision'],source_receipt=receipt)
        record=None
        if snapshot.current_record_ref is not None:
            rref=snapshot.current_record_ref
            rrow=reader.execute('SELECT * FROM installation_qualification_records WHERE record_id=? AND revision=?',(rref.document_id,rref.revision)).fetchone()
            event=reader.execute('SELECT * FROM installation_qualification_events WHERE registry_revision=?',(snapshot.registry_revision,)).fetchone()
            if event is None or rrow is None:
                raise EngineError('qualification_unknown','Original record admission lacks committed rows',503)
            action=parse_exact(PersistedRecordReceipt,event['receipt_json'].encode('utf-8'),limit=LIMIT)
            if (rrow['record_json']!=canonical_bytes(action.record).decode('utf-8') or rrow['record_sha256']!=rref.sha256
                    or rrow['trust_admission_id']!=ref.document_id or action.record.ref()!=rref
                    or (current['record_id'],current['record_revision'])!=(rref.document_id,rref.revision)):
                raise EngineError('qualification_changed','Original immutable record bytes/ref differ',409)
            request=_request(action,rref)
            _check_event(reader,owner,event,action,request,ref,rref)
            record=RecordCommit(record_ref=rref,action_ref=QualificationRef(document_id=action.action_id,revision=event['registry_revision'],sha256=body_sha(action)),
                request=request,request_sha256=event['request_sha256'],registry_revision=event['registry_revision'],source_receipt=action)
        return CommittedInstallationEvidence(format='installation-committed-evidence-v1',instance_id=engine.instance_id,
            registry_revision=snapshot.registry_revision,trust_commit=trust,record_commit=record)


def _check_event(reader,owner,event,source,request,trust_ref,record_ref):
    digest=body_sha(request)
    command=reader.execute('SELECT request_sha256,result_json FROM commands WHERE owner=? AND scope=? AND idempotency_key=?',
        (owner,'installation-qualification',source.action_id)).fetchone()
    if (event is None or event['receipt_json']!=canonical_bytes(source).decode('utf-8')
            or event['kind']!=request.kind or event['action_id']!=source.action_id
            or event['occurred_at_us']!=source.accepted_at_us or event['request_sha256']!=digest
            or event['trust_admission_id']!=trust_ref.document_id
            or (event['record_id'],event['record_revision'])!=((record_ref.document_id,record_ref.revision) if record_ref is not None else (None,None))
            or command is None or command['request_sha256']!=digest):
        raise EngineError('qualification_unknown','Actual original immutable event/command receipt differs',503)
    from video_creator.domain.installation_qualification import TrustSnapshot
    accepted=parse_exact(TrustSnapshot,command['result_json'].encode('utf-8'))
    if (accepted.registry_revision!=event['registry_revision'] or accepted.instance_id!=trust_ref_instance(reader)
            or accepted.trust_admission_ref!=trust_ref or accepted.current_record_ref!=record_ref):
        raise EngineError('qualification_unknown','Actual original command snapshot differs',503)


def trust_ref_instance(reader):
    row=reader.execute("SELECT value FROM metadata WHERE key='instance_id'").fetchone()
    if row is None:
        raise EngineError('qualification_changed','Actual instance metadata is absent',409)
    return row[0]


def install_committed_evidence(*,engine,owner,snapshot):
    value=export_committed_evidence(engine=engine,owner=owner,snapshot=snapshot)
    data=canonical_bytes(value)
    if len(data)>LIMIT:
        raise EngineError('qualification_unavailable','Complete committed evidence exceeds its fixed bound',503)
    path=evidence_path(engine)
    inspect_owner_directory(path.parent)
    if path.is_symlink() or path.is_junction():
        raise EngineError('qualification_unavailable','Original committed evidence became a link',503)
    if path.exists():
        previous=read_committed_evidence(engine)
        if previous.registry_revision>value.registry_revision or previous.registry_revision==value.registry_revision and previous!=value:
            raise EngineError('qualification_changed','Original higher or conflicting committed evidence cannot be replaced',409)
        if previous==value:
            return value
    pending=path.with_suffix('.pending')
    if pending.exists():
        if pending.is_symlink() or pending.is_junction() or pending.stat().st_size!=len(data) or pending.read_bytes()!=data:
            raise EngineError('qualification_unknown','Original incomplete evidence needs exact recovery',503)
    else:
        with pending.open('xb') as stream:
            stream.write(data);stream.flush();os.fsync(stream.fileno())
    os.replace(pending,path)
    if os.name!='nt':
        descriptor=os.open(path.parent,os.O_RDONLY)
        try:os.fsync(descriptor)
        finally:os.close(descriptor)
    return value
