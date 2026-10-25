"""Same-Engine real trust admission persistence, before OwnerSetup/production."""

import os
import threading
from dataclasses import dataclass
from pathlib import Path

from video_creator.application.installation_qualification_control import InstallationQualificationControl
from video_creator.application.production_management import ProductionAuthorizationControl
from video_creator.domain.errors import EngineError
from video_creator.domain.installation_qualification import (
    I64_MAX, QualificationRef, TrustAdmission, TrustSnapshot, body_sha, canonical_bytes, parse_exact,
)
from video_creator.infrastructure.native_installation_trust import OwnedInstallationTrustConnection
from video_creator.infrastructure.owner_identity import inspect_owner_directory

SCOPE='installation-qualification'


class _InstallationLock(ProductionAuthorizationControl):
    _filename='InstallationTrustInstallLock.json'


def qualification_control(engine):
    return InstallationQualificationControl(engine.db.data_dir/'Control'/'InstallationQualificationControl.json',engine.instance_id)


def registry_revision(connection):
    row=connection.execute('SELECT registry_revision FROM installation_qualification_current WHERE singleton=1').fetchone()
    return row[0] if row is not None else 0


def next_revision(revision):
    if type(revision) is not int or not 0<=revision<I64_MAX:
        raise EngineError('qualification_changed','Qualification registry revision is exhausted or invalid',409)
    return revision+1


def snapshot_path(engine):
    return engine.db.data_dir/'Control'/'QualificationTrustSnapshot.json'


def install_snapshot(engine,snapshot):
    path=snapshot_path(engine)
    inspect_owner_directory(path.parent)
    if path.is_symlink() or path.is_junction():
        raise EngineError('qualification_unavailable','Protected qualification snapshot became a link',503)
    data=canonical_bytes(snapshot)
    temporary=path.with_suffix('.pending')
    if temporary.exists():
        if temporary.is_symlink() or temporary.is_junction() or temporary.read_bytes()!=data:
            raise EngineError('qualification_unknown','Earlier snapshot write requires its exact original receipt',503)
    else:
        with temporary.open('xb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    os.replace(temporary,path)
    if os.name!='nt':
        descriptor=os.open(path.parent,os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def read_snapshot(engine):
    path=snapshot_path(engine)
    inspect_owner_directory(path.parent)
    if path.is_symlink() or path.is_junction() or not path.is_file() or path.stat().st_size>1024*1024:
        raise EngineError('qualification_unavailable','Original protected trust snapshot is unavailable',503)
    snapshot=parse_exact(TrustSnapshot,path.read_bytes())
    if snapshot.instance_id!=engine.instance_id:
        raise EngineError('qualification_changed','Qualification snapshot belongs to another instance',409)
    return snapshot


def trust_row_admission(row):
    if row is None:
        raise EngineError('qualification_unavailable','Committed trust admission is unavailable',503)
    admission=parse_exact(TrustAdmission,row['source_receipt_json'].encode('utf-8'))
    if (row['action_id'],row['issuer_id'],row['trust_mode'],row['public_key_hex'],row['materials_json'],
            row['host_build_receipt_sha256'],row['intent_sha256'],row['accepted_at_us'])!=(
            admission.action_id,admission.issuer_id,admission.trust_mode,admission.public_key_hex,
            canonical_bytes([ref.model_dump(mode='json') for ref in admission.material_refs]).decode('utf-8'),
            admission.host_build_receipt_sha256,admission.intent_sha256,admission.accepted_at_us):
        raise EngineError('qualification_unknown','Trust admission fields differ from its canonical original receipt',503)
    return admission


def trust_ref(row):
    admission=trust_row_admission(row)
    return QualificationRef(document_id=row['admission_id'],revision=row['revision'],sha256=body_sha(admission))


@dataclass(frozen=True,eq=False,repr=False)
class InstallationTrustAdmissionSource:
    admission_ref: QualificationRef
    admission: TrustAdmission
    _consumer: object
    _connection: object
    _action: object
    _epoch: object
    _thread: int


class NativeInstallationTrustConsumer:
    def __init__(self):
        self._epoch,self._sources=object(),{}

    def admit_source(self, *, engine,bundle,bound_connection):
        from video_creator.application.committed_installation_evidence import install_committed_evidence

        if (type(bound_connection) is not OwnedInstallationTrustConnection or bound_connection.engine is not engine
                or bundle.engine is not engine):
            raise EngineError('qualification_unavailable','Original same-Engine native trust source is required',503)
        action=bound_connection.consume()
        bound_connection.assert_action(action)
        owner=bundle.principals.owner_subject
        control=qualification_control(engine)
        # Engine/host supplied protected Control root; never create an alternate
        # unprotected directory or establish a source by file self-signature.
        inspect_owner_directory(control.path.parent)
        lock=_InstallationLock(control.path.parent/'InstallationTrustInstallLock.json',engine.instance_id)
        with lock.locked(),control.locked():
            bound_connection.assert_action(action)
            with engine.db.connect() as reader:
                row=reader.execute('SELECT * FROM installation_qualification_trust WHERE action_id=?',(action.admission.action_id,)).fetchone()
                revision=registry_revision(reader)
                if row is None and (revision or reader.execute('SELECT 1 FROM installation_qualification_trust LIMIT 1').fetchone() is not None):
                    raise EngineError('qualification_changed','Initial installation route cannot replace admitted trust',409)
                if row is not None and trust_row_admission(row)!=action.admission:
                    raise EngineError('qualification_changed','Original installation action receipt changed',409)
                admission_id='trust.'+body_sha(action.admission)
                ref=QualificationRef(document_id=admission_id,revision=1,sha256=body_sha(action.admission))
                request=dict(action_id=action.admission.action_id,kind='trust_admit',trust_admission_ref=ref.model_dump(mode='json'),
                             record_ref=None,expected_registry_revision=0)
                request_sha=body_sha(request)
                existing=reader.execute('SELECT request_sha256,result_json FROM commands WHERE owner=? AND scope=? AND idempotency_key=?',
                    (owner,SCOPE,action.admission.action_id)).fetchone()
            if existing is not None:
                if existing['request_sha256']!=request_sha or row is None or revision<1 or trust_ref(row)!=ref:
                    raise EngineError('qualification_changed','Trust action retry differs from its original accepted request',409)
                snapshot=parse_exact(TrustSnapshot,existing['result_json'].encode('utf-8'))
                retained=control.read()
                if revision>1 or (retained.minimum_revision==revision+1 and retained.pending_request_sha256 is not None):
                    # The same genuine installer is resuming its later record
                    # action. Trust is already immutable; never overwrite its
                    # higher pending floor/snapshot with the old trust result.
                    # Record consumer must authenticate that original action
                    # and reconcile its own commit before any production use.
                    current=engine.db.connect()
                    try:
                        actual=current.execute('SELECT * FROM installation_qualification_current WHERE singleton=1').fetchone()
                        if (actual is None or actual['trust_admission_id']!=ref.document_id
                                or actual['state']!=('qualified' if revision>1 else 'not_ready')
                                or retained.minimum_revision not in (revision,revision+1)):
                            raise EngineError('qualification_changed','Later original installation state cannot replay this trust action',409)
                    finally:current.close()
                    source=InstallationTrustAdmissionSource(ref,action.admission,self,bound_connection,action,self._epoch,threading.get_ident())
                    self._sources[id(source)]=source
                    return source
                retained=control.read()
                if retained.minimum_revision!=revision or retained.pending_request_sha256 not in (None,request_sha):
                    raise EngineError('qualification_unknown','Original trust action floor cannot be recovered from this receipt',503)
                install_committed_evidence(engine=engine,owner=owner,snapshot=snapshot)
                install_snapshot(engine,snapshot)
                if retained.pending_request_sha256 is not None:
                    control.complete(revision,request_sha)
            else:
                if row is not None:
                    raise EngineError('qualification_unknown','Trust admission lacks its original command receipt',503)
                if revision!=0:
                    raise EngineError('qualification_changed','Only an empty original registry accepts first trust',409)
                next_revision(revision)
                control.initialize_new()  # Only after the authenticated action + empty registry.
                reserved=control.reserve(revision,request_sha)
                snapshot=TrustSnapshot(format='installation-qualification-trust-snapshot-v1',instance_id=engine.instance_id,
                    registry_revision=reserved,trust_admission_ref=ref,current_record_ref=None,state='not_ready')
                bound_connection.assert_action(action)
                with engine.db.transaction() as writer:
                    bound_connection.assert_action(action,writer)
                    if registry_revision(writer)!=0 or writer.execute('SELECT 1 FROM installation_qualification_trust LIMIT 1').fetchone() is not None:
                        raise EngineError('qualification_changed','Original empty installation registry changed',409)
                    a=action.admission
                    writer.execute('INSERT INTO installation_qualification_trust VALUES(?,?,?,?,?,?,?,?,?,?,?)',(
                        admission_id,1,a.action_id,a.issuer_id,a.trust_mode,a.public_key_hex,
                        canonical_bytes([ref.model_dump(mode='json') for ref in a.material_refs]).decode('utf-8'),
                        a.host_build_receipt_sha256,a.intent_sha256,a.accepted_at_us,canonical_bytes(a).decode('utf-8')))
                    writer.execute('INSERT INTO installation_qualification_events VALUES(?,?,?,?,?,?,?,?,?)',(
                        reserved,'trust_admit',a.action_id,request_sha,admission_id,None,None,canonical_bytes(a).decode('utf-8'),a.accepted_at_us))
                    writer.execute('INSERT INTO installation_qualification_current VALUES(?,?,?,?,?,?)',(1,reserved,admission_id,None,None,'not_ready'))
                    writer.execute('INSERT INTO commands VALUES(?,?,?,?,?)',(owner,SCOPE,a.action_id,request_sha,canonical_bytes(snapshot).decode('utf-8')))
                    bound_connection.assert_action(action,writer)
                install_committed_evidence(engine=engine,owner=owner,snapshot=snapshot)
                install_snapshot(engine,snapshot)
                control.complete(reserved,request_sha)
            source=InstallationTrustAdmissionSource(ref,action.admission,self,bound_connection,action,self._epoch,threading.get_ident())
            self._sources[id(source)]=source
            return source

    def assert_current(self,source):
        if (type(source) is not InstallationTrustAdmissionSource or self._sources.get(id(source)) is not source
                or source._consumer is not self or source._epoch is not self._epoch or source._thread!=threading.get_ident()):
            raise EngineError('qualification_unavailable','Original live trust admission source is required',503)
        source._connection.assert_action(source._action)

    def close(self):
        self._epoch=object()
        self._sources.clear()
