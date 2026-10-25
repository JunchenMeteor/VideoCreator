"""Closed original-source trust factory and retained protected material objects."""

import os
import threading
from dataclasses import dataclass
from typing import Literal

from pydantic import Field, model_validator

from video_creator.application.installation_trust_consumer import (
    qualification_control, read_snapshot, registry_revision, trust_ref, trust_row_admission,
)
from video_creator.domain import contracts as c
from video_creator.domain.errors import EngineError
from video_creator.domain.native_execution_registration import NativeBuildReceipt, NativeInstallationInputs
from video_creator.domain.installation_qualification import (
    I64, QualificationRef, canonical_bytes, parse_exact,
)
from video_creator.infrastructure.held_authority import _relative
from video_creator.infrastructure.owner_identity import inspect_owner_directory
from video_creator.infrastructure.qualified_authority import OwnedQualifiedAuthorityConnection
from video_creator.infrastructure.windows_authority_pipe import OwnerProtectedNativeBuild, open_owner_protected_native_build

PURPOSES=('trust_anchor','publisher_provenance','verifier_code_index','qualification_suite',
          'independent_review','independent_acceptance','anchor_generation',
          'qualification_report','license_evidence','build_provenance')
_TOKEN=object()
_sources={}


class QualificationMaterial(c.Contract):
    ref: QualificationRef
    relative_path: str = Field(strict=True)
    bytes: I64
    purpose: Literal['trust_anchor','publisher_provenance','verifier_code_index','qualification_suite',
                     'independent_review','independent_acceptance','anchor_generation',
                     'qualification_report','license_evidence','build_provenance']

    @model_validator(mode='after')
    def path(self):
        _relative(self.relative_path)
        if self.bytes > 32 * 1024 * 1024 or any(part.endswith((' ', '.')) for part in self.relative_path.split('/')):
            raise ValueError('Material requires finite protected native path and size')
        return self


class QualificationMaterialsIndex(c.Contract):
    format: Literal['installation-qualification-material-index-v1']
    issuer_id: c.Identifier
    trust_mode: Literal['publisher','local_verifier']
    public_key_hex: str=Field(strict=True,pattern=r'^[a-f0-9]{64}$')
    materials: tuple[QualificationMaterial,...]

    @model_validator(mode='after')
    def members(self):
        refs=tuple((m.ref.document_id,m.ref.revision,m.ref.sha256) for m in self.materials)
        paths=tuple(m.relative_path.casefold() for m in self.materials)
        if not refs or len(refs)>4096 or refs!=tuple(sorted(set(refs))) or len(set(paths))!=len(paths):
            raise ValueError('Material index requires finite distinct sorted refs/paths')
        purposes=tuple(m.purpose for m in self.materials)
        if purposes.count('trust_anchor')!=1:
            raise ValueError('Exactly one original admitted anchor is required')
        required=('trust_anchor','publisher_provenance') if self.trust_mode=='publisher' else (
            'trust_anchor','verifier_code_index','qualification_suite','independent_review','independent_acceptance','anchor_generation')
        if any(purpose not in purposes for purpose in required):
            raise ValueError('Complete independently admitted trust source materials are required')
        return self


@dataclass(frozen=True,eq=False,repr=False)
class _MaterialHold:
    material: QualificationMaterial
    build: OwnerProtectedNativeBuild


class NativeQualificationTrustSource:
    def __init__(self, *, token,engine,bundle,connection,build,snapshot,admission,index,held_index,holds,installation_holds,installation_action=None):
        if token is not _TOKEN:
            raise EngineError('qualification_unavailable','Only the closed native trust factory may establish this source',503)
        self.engine,self.bundle,self.connection,self.build=engine,bundle,connection,build
        self.snapshot,self.admission,self.index=snapshot,admission,index
        self._held_index,self._holds=held_index,tuple(holds)
        self._installation_holds=tuple(installation_holds)
        self._installation_action=installation_action
        self.control=qualification_control(engine)
        self._epoch,self._closed=object(),False
        self._thread=threading.get_ident()
        self._rows=None
        _sources[id(self)]=self

    def assert_current(self):
        self.assert_member()
        self.connection._transport.assert_peer()
        self.build.assert_current()
        self._held_index.assert_current()
        for original in self._installation_holds:
            original.assert_current()
        for hold in self._holds:
            hold.build.assert_current()
        current=read_snapshot(self.engine)
        document=self.control.read()
        if self._installation_action is None:
            from video_creator.application.committed_installation_evidence import read_committed_evidence,export_committed_evidence
            evidence=read_committed_evidence(self.engine)
            committed=export_committed_evidence(engine=self.engine,owner=self.bundle.principals.owner_subject,snapshot=current)
            if (evidence.registry_revision!=current.registry_revision or evidence.trust_commit.admission_ref!=current.trust_admission_ref
                    or evidence.trust_commit.source_receipt!=self.admission or evidence.record_commit is None
                    or evidence.record_commit.record_ref!=current.current_record_ref or current.state!='qualified' or evidence!=committed):
                raise EngineError('qualification_changed','Original committed evidence differs from current qualified source',409)
            if current!=self.snapshot:
                raise EngineError('qualification_changed','Original protected trust/current snapshot changed',409)
            if document.pending_request_sha256 or document.minimum_revision!=current.registry_revision:
                raise EngineError('qualification_unknown','Qualification retained floor is pending or differs from snapshot',503)
        else:
            self.connection.assert_action(self._installation_action)
            action=self._installation_action.admission
            from video_creator.domain.committed_installation_evidence import InstallationActionRequest
            from video_creator.domain.installation_qualification import body_sha
            request=InstallationActionRequest(action_id=action.action_id,kind=action.kind,trust_admission_ref=action.trust_admission_ref,
                record_ref=action.record.ref(),expected_registry_revision=action.expected_registry_revision)
            if (current.trust_admission_ref!=action.trust_admission_ref or current.state=='revoked'
                    or current.registry_revision not in (action.expected_registry_revision,action.expected_registry_revision+1)
                    or document.minimum_revision not in (action.expected_registry_revision,action.expected_registry_revision+1)
                    or document.pending_request_sha256 not in (None,body_sha(request))):
                raise EngineError('qualification_unknown','Original installer action cannot recover this protected floor/snapshot',503)
        with self.engine.db.connect() as reader:
            self._assert_snapshot_rows(reader)
        return document

    def assert_member(self):
        if (self._closed or _sources.get(id(self)) is not self or self._thread!=threading.get_ident()
                or self.bundle.engine is not self.engine or self.connection.context.instance_id!=self.engine.instance_id):
            raise EngineError('qualification_unavailable','Original same-instance trust source member is unavailable',503)
        self.connection.assert_local_current()

    def _assert_snapshot_rows(self,reader):
        current=reader.execute('SELECT * FROM installation_qualification_current WHERE singleton=1').fetchone()
        if current is None or (current['registry_revision'],current['trust_admission_id'],current['state'])!=(
                self.snapshot.registry_revision,self.snapshot.trust_admission_ref.document_id,self.snapshot.state):
            raise EngineError('qualification_changed','Actual qualification current row differs from protected snapshot',409)
        row=reader.execute('SELECT * FROM installation_qualification_trust WHERE admission_id=?',
            (self.snapshot.trust_admission_ref.document_id,)).fetchone()
        if trust_ref(row)!=self.snapshot.trust_admission_ref or trust_row_admission(row)!=self.admission:
            raise EngineError('qualification_changed','Actual original admitted trust row changed',409)
        event=reader.execute('SELECT * FROM installation_qualification_events WHERE registry_revision=?',
            (self.snapshot.registry_revision,)).fetchone()
        if event is None or event['trust_admission_id']!=row['admission_id']:
            raise EngineError('qualification_unknown','Snapshot lacks its exact original committed event',503)
        expected_record=self.snapshot.current_record_ref
        if expected_record is None:
            if current['record_id'] is not None or current['record_revision'] is not None:
                raise EngineError('qualification_changed','Facts-only current unexpectedly contains a record',409)
            record=None
        else:
            record=reader.execute('SELECT * FROM installation_qualification_records WHERE record_id=? AND revision=?',
                (expected_record.document_id,expected_record.revision)).fetchone()
            if (current['record_id'],current['record_revision'])!=(expected_record.document_id,expected_record.revision) or record is None or record['record_sha256']!=expected_record.sha256 or record['trust_admission_id']!=row['admission_id']:
                raise EngineError('qualification_changed','Original record row/ref differs from snapshot',409)
        self._rows=(tuple(current),tuple(row),tuple(event),tuple(record) if record is not None else None)

    def assert_local_rows(self,reader):
        self.assert_member()
        if self._rows is None:
            raise EngineError('qualification_unavailable','Original source rows were not pinned outside writer',503)
        expected=self._rows
        current=reader.execute('SELECT * FROM installation_qualification_current WHERE singleton=1').fetchone()
        row=reader.execute('SELECT * FROM installation_qualification_trust WHERE admission_id=?',
            (self.snapshot.trust_admission_ref.document_id,)).fetchone()
        event=reader.execute('SELECT * FROM installation_qualification_events WHERE registry_revision=?',
            (self.snapshot.registry_revision,)).fetchone()
        ref=self.snapshot.current_record_ref
        record=reader.execute('SELECT * FROM installation_qualification_records WHERE record_id=? AND revision=?',
            (ref.document_id,ref.revision)).fetchone() if ref is not None else None
        actual=tuple(tuple(item) if item is not None else None for item in (current,row,event,record))
        if actual!=expected:
            raise EngineError('qualification_changed','Actual same-connection qualification rows changed',409)
        identity=reader.execute("SELECT value FROM metadata WHERE key='instance_id'").fetchone()
        if identity is None or identity[0]!=self.engine.instance_id:
            raise EngineError('qualification_changed','Actual qualification writer instance identity changed',409)

    def require_material(self,ref,purpose):
        for hold in self._holds:
            if hold.material.ref==ref and hold.material.purpose==purpose:
                return hold
        raise EngineError('qualification_unavailable','Complete original qualification attachment is missing',503)

    def verify_record(self,record,context):
        self.assert_current()
        import platform
        import sys
        # This concrete transport is Windows. Other target factories require
        # their actual POSIX peer/FD implementation, never Windows aliases.
        if (os.name!='nt' or (record.target.os,record.target.arch)!=('windows','x86_64')
                or platform.machine().lower() not in ('amd64','x86_64')
                or sys.implementation.name!='cpython' or sys.version_info[:3]!=(3,13,16)):
            raise EngineError('qualification_unavailable','Original concrete runtime/target differs from the admitted Windows profile',503)
        if (record.issuer_id,record.trust_mode,record.host_build_receipt_sha256)!=(
                self.admission.issuer_id,self.admission.trust_mode,self.admission.host_build_receipt_sha256):
            raise EngineError('qualification_changed','Qualification differs from its independently admitted trust source',409)
        record.verify_signature(bytes.fromhex(self.admission.public_key_hex))
        self.require_material(record.qualification_suite_ref,'qualification_suite')
        self.require_material(record.independent_review_ref,'independent_review')
        self.require_material(record.independent_acceptance_ref,'independent_acceptance')
        for refs,purpose in ((record.runtime_report_refs,'qualification_report'),(record.license_evidence_refs,'license_evidence'),
                             (record.build_provenance_refs,'build_provenance')):
            for ref in refs:
                self.require_material(ref,purpose)
        for condition in record.target.conditions:
            self.require_material(condition.report_ref,'qualification_report')
        for profile in record.profiles:
            for ref in profile.report_refs:
                self.require_material(ref,'qualification_report')
        # Native registry also validates actual target receipt/LoadPolicy/ABI,
        # reports and distribution closure while holding original native guards.
        # Backend independently checks the original whole-map and active profile.
        from video_creator.domain.installation_qualification import body_sha
        files=[dict(relative_path=f.relative_path,bytes=f.bytes,sha256=f.sha256) for f in sorted(context.expected_files,key=lambda f:f.relative_path)]
        if record.full_file_map_sha256!=body_sha(files) or record.engine_partition_sha256!=body_sha(list(context.engine_file_names)):
            raise EngineError('qualification_changed','Qualification full file/engine partition map differs',409)
        if (record.registration_sha256,record.resource_manifest_sha256,record.runtime_manifest_sha256)!=(
                context.registration_sha256,context.resource_manifest_sha256,context.runtime_manifest_sha256):
            raise EngineError('qualification_changed','Qualification registration maps differ from original launch',409)
        profile=next(profile for profile in record.profiles if profile.name==context.role)
        actual={f['relative_path']:(f['bytes'],f['sha256']) for f in files}
        complete={}
        for candidate in record.profiles:
            for file in candidate.required_files:
                fact=(file.bytes,file.sha256)
                if file.relative_path in complete and complete[file.relative_path]!=fact:
                    raise EngineError('qualification_changed','Qualified profiles contain conflicting original files',409)
                complete[file.relative_path]=fact
        if complete!=actual or any(actual.get(f.relative_path)!=(f.bytes,f.sha256) for f in profile.required_files):
            raise EngineError('qualification_changed','Qualified active profile required map differs from held payload',409)
        now=self.engine.clock()
        if not record.valid_from_us<=now<record.expires_at_us:
            raise EngineError('qualification_expired','Original qualification has not started or has expired',409)

    def close(self):
        if not self._closed:
            self._closed=True
            self._epoch=object()
            # All retained original closes attempted once; preserve first error.
            failure=None
            for build in [*(hold.build for hold in self._holds),self._held_index,*self._installation_holds]:
                try:
                    build.close()
                except BaseException as error:
                    failure=failure or error
            if failure is not None:
                raise failure
            _sources.pop(id(self),None)


def open_native_qualification_trust(*,engine,bundle,connection,build):
    from video_creator.infrastructure.native_installation_record import OwnedInstallationRecordConnection

    if (type(connection) not in (OwnedQualifiedAuthorityConnection,OwnedInstallationRecordConnection) or type(build) is not OwnerProtectedNativeBuild
            or connection._transport.build is not build or bundle.engine is not engine
            or connection.context.instance_id!=engine.instance_id):
        raise EngineError('qualification_unavailable','Original installed same-Engine/Bundle/peer/build is required',503)
    connection._transport.assert_peer()
    build.assert_current()
    # Normal packaged-host relation is fixed by the original held image.
    # Instance Control only stores the committed floor/snapshot; it is never
    # the installation's qualification-material root.
    if build.path.parent.name != 'Host':
        raise EngineError('qualification_unavailable','Original normal packaged Host layout is required',503)
    composition=build.path.parent.parent
    root=composition/'Control'
    owner=inspect_owner_directory(root)
    if owner.os_subject!=build.owner.os_subject:
        raise EngineError('qualification_unavailable','Trust storage differs from the actual held installation Owner',503)
    snapshot=read_snapshot(engine)
    control=qualification_control(engine)
    document=control.read()
    installation_action=connection._action if type(connection) is OwnedInstallationRecordConnection else None
    if installation_action is None and (document.pending_request_sha256 or document.minimum_revision!=snapshot.registry_revision):
        raise EngineError('qualification_unknown','Original trust floor is pending or behind current',503)
    with engine.db.connect() as reader:
        row=reader.execute('SELECT * FROM installation_qualification_trust WHERE admission_id=?',
            (snapshot.trust_admission_ref.document_id,)).fetchone()
        admission=trust_row_admission(row)
        if trust_ref(row)!=snapshot.trust_admission_ref:
            raise EngineError('qualification_changed','Original admission/ref/current row differs from snapshot',409)
        if installation_action is None:
            if registry_revision(reader)!=snapshot.registry_revision:
                raise EngineError('qualification_changed','Original current row differs from protected snapshot',409)
        else:
            connection.assert_action(installation_action)
            action=installation_action.admission
            current=reader.execute('SELECT * FROM installation_qualification_current WHERE singleton=1').fetchone()
            if current is None or current['trust_admission_id']!=action.trust_admission_ref.document_id or current['registry_revision'] not in (action.expected_registry_revision,action.expected_registry_revision+1):
                raise EngineError('qualification_changed','Original installer action differs from committed current',409)
            ref=None
            if current['record_id'] is not None:
                record=reader.execute('SELECT * FROM installation_qualification_records WHERE record_id=? AND revision=?',(current['record_id'],current['record_revision'])).fetchone()
                if record is None:
                    raise EngineError('qualification_unknown','Original current record lacks immutable bytes',503)
                ref=QualificationRef(document_id=current['record_id'],revision=current['record_revision'],sha256=record['record_sha256'])
            from video_creator.domain.installation_qualification import TrustSnapshot
            snapshot=TrustSnapshot(format='installation-qualification-trust-snapshot-v1',instance_id=engine.instance_id,
                registry_revision=current['registry_revision'],trust_admission_ref=trust_ref(row),current_record_ref=ref,state=current['state'])
    path=root/'QualificationMaterialsIndex.json'
    if path.is_symlink() or path.is_junction() or not path.is_file() or path.stat().st_size>32*1024*1024:
        raise EngineError('qualification_unavailable','Protected qualification material index is unavailable',503)
    data=path.read_bytes()
    index=parse_exact(QualificationMaterialsIndex,data,limit=32*1024*1024)
    if len(data)+sum(material.bytes for material in index.materials)>128*1024*1024:
        raise EngineError('qualification_unavailable','Original qualification material aggregate exceeds its fixed bound',503)
    if (index.issuer_id,index.trust_mode,index.public_key_hex)!=(admission.issuer_id,admission.trust_mode,admission.public_key_hex):
        raise EngineError('qualification_changed','Index key is not the original independently admitted anchor',409)
    import hashlib
    held_index=open_owner_protected_native_build(image_path=path,expected_sha256=hashlib.sha256(data).hexdigest())
    holds=[]
    installation_holds=[]
    try:
        receipt_path=root/'NativeBuildReceipt.json'
        held_receipt=open_owner_protected_native_build(image_path=receipt_path,expected_sha256=admission.host_build_receipt_sha256)
        installation_holds.append(held_receipt)
        if held_receipt.file_identity[2]>1024*1024:
            raise EngineError('qualification_unavailable','Original build receipt exceeds its fixed bound',503)
        receipt=parse_exact(NativeBuildReceipt,receipt_path.read_bytes())
        input_path=root/'NativeInstallationInputs.json'
        if input_path.is_symlink() or input_path.is_junction() or not input_path.is_file() or input_path.stat().st_size>32*1024*1024:
            raise EngineError('qualification_unavailable','Original normal installation input is unavailable',503)
        input_data=input_path.read_bytes()
        held_input=open_owner_protected_native_build(image_path=input_path,expected_sha256=hashlib.sha256(input_data).hexdigest())
        installation_holds.append(held_input)
        inputs=parse_exact(NativeInstallationInputs,input_data,limit=32*1024*1024)
        if any(original.owner.os_subject!=owner.os_subject for original in installation_holds):
            raise EngineError('qualification_changed','Original installation input/receipt Owner differs',409)
        if (os.path.normcase(inputs.composition_root)!=os.path.normcase(str(composition))
                or os.path.normcase(inputs.installed_native_image)!=os.path.normcase(str(build.path))
                or inputs.installed_native_image_bytes!=build.file_identity[2]
                or inputs.installed_native_image_sha256!=build.expected_sha256
                or inputs.build_receipt!=receipt
                or inputs.build_receipt_sha256!=admission.host_build_receipt_sha256
                or (inputs.registration_sha256,inputs.resource_manifest_sha256,inputs.runtime_manifest_sha256,
                    inputs.expected_files,inputs.engine_file_names)!=(connection.context.registration_sha256,
                    connection.context.resource_manifest_sha256,connection.context.runtime_manifest_sha256,
                    connection.context.expected_files,connection.context.engine_file_names)):
            raise EngineError('qualification_changed','Original held Host/receipt/full installation graph differs',409)
        held_receipt.assert_current()
        held_input.assert_current()
        for material in index.materials:
            original=open_owner_protected_native_build(image_path=root/material.relative_path,expected_sha256=material.ref.sha256)
            holds.append(_MaterialHold(material,original))
            if original.owner.os_subject!=owner.os_subject or original.file_identity[2]!=material.bytes:
                raise EngineError('qualification_changed','Actual protected material Owner/size differs from its ref',409)
        indexed={hold.material.ref for hold in holds}
        if any(ref not in indexed for ref in admission.material_refs):
            raise EngineError('qualification_unavailable','An original trust action material is absent',503)
        anchor=next(hold for hold in holds if hold.material.purpose=='trust_anchor')
        if anchor.material.bytes!=32 or anchor.build.path.read_bytes()!=bytes.fromhex(admission.public_key_hex):
            raise EngineError('qualification_changed','Original held anchor bytes differ from admitted action',409)
        source=NativeQualificationTrustSource(token=_TOKEN,engine=engine,bundle=bundle,connection=connection,build=build,
            snapshot=snapshot,admission=admission,index=index,held_index=held_index,holds=holds,installation_holds=installation_holds,installation_action=installation_action)
        source.assert_current()
        return source
    except BaseException as failure:
        for original in [*(hold.build for hold in holds),held_index,*installation_holds]:
            try:
                original.close()
            except BaseException as cleanup:
                failure.add_note('Original qualification material cleanup also failed: '+type(cleanup).__name__)
        raise
