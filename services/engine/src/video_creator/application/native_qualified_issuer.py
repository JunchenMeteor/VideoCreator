"""Concrete same-Engine qualified issuer and original native writer lease."""

import threading
from contextlib import contextmanager
from dataclasses import dataclass

from video_creator.application.production_admissions import InstalledProductionEvidence
from video_creator.domain.errors import EngineError
from video_creator.infrastructure.native_qualification_trust import NativeQualificationTrustSource
from video_creator.infrastructure.qualified_authority import OwnedQualifiedAuthorityConnection, QualifiedHeldFactsObservation


@dataclass(frozen=True,eq=False,repr=False)
class QualifiedWriterLease:
    evidence: InstalledProductionEvidence
    original_facts: QualifiedHeldFactsObservation
    native_lease: object
    minimum_revision: int
    source_epoch: object
    thread_id: int
    _issuer: object
    _epoch: object


class NativeQualifiedInstallationIssuer:
    def __init__(self, *, engine,bundle,connection,trust_source):
        if (type(connection) is not OwnedQualifiedAuthorityConnection or type(trust_source) is not NativeQualificationTrustSource
                or trust_source.engine is not engine or trust_source.bundle is not bundle
                or trust_source.connection is not connection or bundle.engine is not engine):
            raise EngineError('qualification_unavailable','Original installed same-Engine qualified sources are required',503)
        trust_source.assert_current()
        self.engine,self.bundle,self.connection,self.trust_source=engine,bundle,connection,trust_source
        self._epoch,self._closed=object(),False
        self._members,self._leases={},{}
        self._lock=threading.RLock()

    def _original(self, *, evidence,connection,original_facts,context):
        if (self._closed or connection is not self.connection or context is not self.connection.context
                or type(original_facts) is not QualifiedHeldFactsObservation
                or self._members.get(id(evidence), (None,None))[0] is not evidence
                or self._members[id(evidence)][1] is not original_facts):
            raise EngineError('qualification_unknown','Original issuer/evidence/held-facts membership is required',503)
        connection.assert_local_observation(original_facts)
        self.trust_source.assert_member()

    def issue(self, *, connection,original_facts,context):
        with self._lock:
            if (self._closed or connection is not self.connection or context is not self.connection.context
                    or type(original_facts) is not QualifiedHeldFactsObservation or original_facts.binding is None):
                raise EngineError('qualification_unavailable','Actual original qualified observation is unavailable',503)
            connection.assert_local_observation(original_facts)
            record=original_facts.binding.record
            source=self.trust_source
            source.verify_record(record,context)
            if (source.snapshot.state!='qualified' or source.snapshot.current_record_ref!=record.ref()
                    or source.snapshot.registry_revision!=original_facts.binding.registry_revision):
                raise EngineError('qualification_unavailable','Genuine qualification record has not been admitted by the installation source',503)
            names=set(context.engine_file_names)
            evidence=InstalledProductionEvidence(context.instance_id,context.registration_sha256,context.resource_manifest_sha256,
                context.runtime_manifest_sha256,record.workflow_version,record.driver_profile,original_facts.observed_at_us,
                tuple(sorted((f.relative_path,f.sha256) for f in original_facts.files if f.relative_path in names)),
                tuple(sorted((f.relative_path,f.sha256) for f in original_facts.files if f.relative_path not in names)))
            self._members[id(evidence)]=(evidence,original_facts)
            return evidence

    def assert_current(self, *, evidence,connection,original_facts,context):
        with self._lock:
            self._original(evidence=evidence,connection=connection,original_facts=original_facts,context=context)
            self.trust_source.verify_record(original_facts.binding.record,context)
            snapshot=self.trust_source.snapshot
            if snapshot.state!='qualified' or snapshot.current_record_ref!=original_facts.binding.record.ref() or snapshot.registry_revision!=original_facts.binding.registry_revision:
                raise EngineError('qualification_changed','Original qualified current/ref changed',409)

    def assert_local_current(self, *, evidence,connection,original_facts,context):
        """Original cache/member lease checks only, no I/O or SQL connection open."""
        if not self._lock.acquire(blocking=False):
            raise EngineError('qualification_unavailable','Qualified issuer is currently observing an external source',503)
        try:
            self._original(evidence=evidence,connection=connection,original_facts=original_facts,context=context)
            lease=self._leases.get(threading.get_ident())
            if lease is None or lease.evidence is not evidence:
                raise EngineError('lease_conflict','Qualified short writer requires its original outer lease',409)
            self._local_lease(lease)
        finally:
            self._lock.release()

    def _local_lease(self,lease):
        if (type(lease) is not QualifiedWriterLease or lease._issuer is not self or lease._epoch is not self._epoch
                or lease.source_epoch is not self.trust_source._epoch or self._closed
                or lease.thread_id!=threading.get_ident() or self._leases.get(lease.thread_id) is not lease):
            raise EngineError('lease_conflict','Original current same-thread issuer writer lease is required',409)
        self.connection.assert_local_lease(lease.native_lease)
        self.trust_source.assert_member()

    @contextmanager
    def current_writer_lease(self, *, evidence):
        thread=threading.get_ident()
        with self._lock:
            if thread in self._leases:
                raise EngineError('lease_conflict','Do not reacquire original QualificationControl or native lease',409)
            pair=self._members.get(id(evidence))
            if pair is None or pair[0] is not evidence:
                raise EngineError('qualification_unknown','Original issuer evidence is required',503)
            facts=pair[1]
            self.assert_current(evidence=evidence,connection=self.connection,original_facts=facts,context=self.connection.context)
        source=self.trust_source
        with source.control.locked():
            # All file/peer/cryptography work is outside SQLite writers and before
            # native begin. Original held resources remain separately retained.
            retained=source.assert_current()
            native=self.connection.begin_writer_lease(facts)
            lease=QualifiedWriterLease(evidence,facts,native,retained.minimum_revision,source._epoch,thread,self,self._epoch)
            self._leases[thread]=lease
            failure=None
            try:
                yield lease
            except BaseException as error:
                failure=error
                raise
            finally:
                self._leases.pop(thread,None)
                try:
                    self.connection.end_writer_lease(native)
                except BaseException as release:
                    self._epoch=object()
                    self._members.clear()
                    # Commit may already have succeeded; preserve unknown native
                    # guard state. Original exception wins when rollback failed.
                    if failure is not None:
                        failure.add_note('Native writer lease release also failed: '+type(release).__name__)
                    else:
                        raise

    def assert_writer_current(self, *, sql_connection,lease):
        self._local_lease(lease)
        self.trust_source.assert_local_rows(sql_connection)
        if lease.minimum_revision!=lease.original_facts.binding.registry_revision or (
                lease.native_lease.binding.revocation_floor!=lease.original_facts.binding.revocation_floor):
            raise EngineError('qualification_changed','Original writer qualification/floor cache differs',409)
        if not lease.original_facts.binding.record.valid_from_us<=self.engine.clock()<lease.original_facts.binding.record.expires_at_us:
            raise EngineError('qualification_expired','Qualification expired before the short writer commit',409)

    def close(self):
        if self._leases or self.connection._active_lease is not None or self.connection._lease_unknown:
            raise EngineError('qualification_unknown','Original entered qualified writer must finish before source close',503)
        self._closed=True
        self._epoch=object()
        self._members.clear()
        self.trust_source.close()
