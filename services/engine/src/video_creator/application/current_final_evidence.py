"""Service-held final evidence ports, shared by the original registered producer."""

import threading

from video_creator.domain import contracts as c
from video_creator.domain.current_final_evidence import (
    AssemblyContextRef, CurrentFinalAssemblyContext, CurrentFinalEvidenceAssessment,
    CurrentFinalAssemblyContextV2, CurrentFinalEvidenceContinuation, CurrentFinalEvidenceInputs, CurrentFinalEvidenceReadSet,
)
from video_creator.domain.affected_repair import (
    AffectedMasterObservation, AffectedRepairExecution, AffectedRepairProposal, AffectedRepairReadSet,
)
from video_creator.domain.errors import EngineError
from video_creator.domain.worker import GeneratedFileManifest
from video_creator.domain.component_diagnosis import (
    ComponentDiagnosticObservationV1, RegisteredComponentDiagnosisInputsV1,
    RegisteredComponentDiagnosisV1, CurrentFinalDiagnosticContinuationV1,
)
from video_creator.domain.affected_recipe import AffectedRepairProposalV2


class CurrentFinalEvidencePorts:
    """Only the original BundleService may register a usable instance.

    Constructing this class or copying its attributes does not register it.
    Every call rechecks actual object identity, thread and the current lease.
    """

    __slots__ = ('_service', '_lease', '_binding', '_thread')

    def __init__(self, service, lease, binding):
        self._service, self._lease, self._binding = service, lease, binding
        self._thread = threading.get_ident()

    def _current(self, ordinary_lease):
        service = self._service
        with service._lock:
            registered = service._final_evidence_ports.get(id(self))
        if (registered is not self or threading.get_ident() != self._thread
                or ordinary_lease != self._lease):
            raise EngineError('final_evidence_port_denied', 'Original service-held current ports required', 403)
        with service.engine.db.connect_readonly() as connection:
            service.engine._lease(connection, ordinary_lease)
        return service

    def resolve_inputs(self, ordinary_lease: c.LeaseGrant, preparation_id: str) -> CurrentFinalEvidenceInputs | CurrentFinalEvidenceAssessment:
        service = self._current(ordinary_lease)
        return service._resolve_current_final_inputs(ordinary_lease, preparation_id, self._binding)

    def verify_current_final_evidence(self, ordinary_lease: c.LeaseGrant, preparation_id: str,
                                      manifest: c.BundleManifestAny | None) -> CurrentFinalEvidenceAssessment:
        service = self._current(ordinary_lease)
        return service.verify_current_final_evidence(ordinary_lease, preparation_id, manifest)

    def revise_preparation(self, ordinary_lease, preparation_id, intent, *, affected_artifact_ids):
        service = self._current(ordinary_lease)
        return service.revise_current_final_preparation(ordinary_lease, preparation_id, intent,
            affected_artifact_ids=affected_artifact_ids)

    def read_continuation_inputs(self, ordinary_lease: c.LeaseGrant,
                                 continuation: CurrentFinalEvidenceContinuation) -> CurrentFinalEvidenceReadSet:
        service = self._current(ordinary_lease)
        return service.read_current_final_continuation_inputs(ordinary_lease, continuation)

    def persist_assembly_context(self, ordinary_lease: c.LeaseGrant, preparation_id: str,
                                 context: CurrentFinalAssemblyContext | CurrentFinalAssemblyContextV2) -> AssemblyContextRef:
        service = self._current(ordinary_lease)
        return service.persist_current_final_assembly_context(ordinary_lease, preparation_id, context)

    def assert_production_services(self, ordinary_lease, production_services, execution_ports) -> None:
        service = self._current(ordinary_lease)
        service.assert_current_production_services(ordinary_lease, production_services, execution_ports)

    def authorize_affected_execution(self, ordinary_lease, continuation,
                                     proposal: AffectedRepairProposal) -> AffectedRepairExecution:
        service = self._current(ordinary_lease)
        return service.authorize_current_affected_execution(ordinary_lease, continuation, proposal)

    def observe_affected_masters(self, ordinary_lease, execution: AffectedRepairExecution,
                                *, step_key: c.Identifier) -> AffectedMasterObservation:
        service = self._current(ordinary_lease)
        return service.observe_current_affected_masters(ordinary_lease, execution, step_key=step_key)

    def read_affected_execution_inputs(self, ordinary_lease, continuation) -> AffectedRepairReadSet:
        service = self._current(ordinary_lease)
        return service.read_current_affected_execution_inputs(ordinary_lease, continuation)

    def registered_child_asr_intent(self, ordinary_lease, execution: AffectedRepairExecution) -> c.OperationIntent | None:
        service = self._current(ordinary_lease)
        return service.read_registered_child_asr_intent(ordinary_lease, execution)

    def registered_alignment_intent(self, ordinary_lease, execution: AffectedRepairExecution) -> c.OperationIntent:
        return self._current(ordinary_lease).registered_alignment_intent(ordinary_lease, execution)

    def registered_alignment_request(self, ordinary_lease, execution: AffectedRepairExecution) -> bytes:
        return self._current(ordinary_lease).registered_alignment_request(ordinary_lease, execution)

    def commit_registered_alignment_result(self, ordinary_lease, execution: AffectedRepairExecution,
                                           *, files: tuple[GeneratedFileManifest, ...]) -> c.AlignmentRevision | c.AlignmentRevisionV03:
        return self._current(ordinary_lease).commit_registered_alignment_result(ordinary_lease, execution, files=files)

    def read_registered_alignment_result(self, ordinary_lease, execution: AffectedRepairExecution) -> tuple[c.AlignmentRevision | c.AlignmentRevisionV03, GeneratedFileManifest, c.OperationObservation]:
        return self._current(ordinary_lease).read_registered_alignment_result(ordinary_lease, execution)

    def register_initial_alignment(self, ordinary_lease, preparation_id: str, *, transcript: c.ActualTranscriptRevision,
                                   prediction: c.AlignmentRevision | c.AlignmentRevisionV03,
                                   mapping: c.AudioTimelineMapping) -> c.OperationIntent:
        return self._current(ordinary_lease).register_initial_alignment(ordinary_lease, preparation_id,
            transcript=transcript, prediction=prediction, mapping=mapping)

    def registered_initial_alignment_request(self, ordinary_lease, preparation_id: str) -> bytes:
        return self._current(ordinary_lease).registered_initial_alignment_request(ordinary_lease, preparation_id)

    def commit_registered_initial_alignment_result(self, ordinary_lease, preparation_id: str,
                                                   *, files: tuple[GeneratedFileManifest, ...]) -> c.AlignmentRevision | c.AlignmentRevisionV03:
        return self._current(ordinary_lease).commit_registered_initial_alignment_result(ordinary_lease, preparation_id, files=files)

    def read_registered_initial_alignment_result(self, ordinary_lease, preparation_id: str) -> tuple[c.AlignmentRevision | c.AlignmentRevisionV03, GeneratedFileManifest, c.OperationObservation]:
        return self._current(ordinary_lease).read_registered_initial_alignment_result(ordinary_lease, preparation_id)

    def registered_initial_alignment_method(self, ordinary_lease, preparation_id: str) -> c.MethodEvidence:
        return self._current(ordinary_lease).registered_initial_alignment_method(ordinary_lease, preparation_id)

    def read_selected_alignment_result(self, ordinary_lease: c.LeaseGrant,
                                       continuation: CurrentFinalEvidenceContinuation) -> tuple[
            bytes, c.AlignmentRevision | c.AlignmentRevisionV03, GeneratedFileManifest,
            c.OperationObservation, c.MethodEvidence] | None:
        return self._current(ordinary_lease).read_selected_alignment_result(ordinary_lease, continuation)

    def prepare_component_diagnosis(self, preparation_id: str, *, continuation=None, resume_probe=None) -> RegisteredComponentDiagnosisInputsV1:
        return self._current(self._lease).prepare_component_diagnosis(self._lease, preparation_id,
            continuation=continuation,resume_probe=resume_probe,owner_port=self)

    def read_current_final_diagnostic_source(self, continuation):
        return self._current(self._lease).read_current_final_diagnostic_source(self._lease,continuation)

    def assess_resumed_component_diagnosis(self, continuation, recorded):
        return self._current(self._lease).assess_resumed_component_diagnosis(self._lease,continuation,recorded)

    def read_diagnostic_completion(self, inputs, completion):
        return self._current(self._lease).read_diagnostic_completion(self._lease,inputs,completion)

    def record_component_diagnosis(self, inputs: RegisteredComponentDiagnosisInputsV1,
                                   observation: ComponentDiagnosticObservationV1) -> RegisteredComponentDiagnosisV1:
        return self._current(self._lease).record_component_diagnosis(self._lease, inputs, observation)

    def append_component_diagnosis(self, inputs: RegisteredComponentDiagnosisInputsV1,
                                   observation: ComponentDiagnosticObservationV1) -> RegisteredComponentDiagnosisV1:
        return self._current(self._lease).append_component_diagnosis(self._lease, inputs, observation)

    def read_recorded_component_diagnosis(self, inputs: RegisteredComponentDiagnosisInputsV1) -> RegisteredComponentDiagnosisV1 | None:
        return self._current(self._lease).read_recorded_component_diagnosis(self._lease, inputs)

    def read_component_diagnosis(self, continuation) -> RegisteredComponentDiagnosisV1 | None:
        return self._current(self._lease).read_component_diagnosis(self._lease, continuation)

    def prepare_affected_recipe_proposal(self, continuation: CurrentFinalDiagnosticContinuationV1) -> AffectedRepairProposalV2:
        return self._current(self._lease).prepare_affected_recipe_proposal(self._lease, continuation)

    def close(self):
        with self._service._lock:
            if self._service._final_evidence_ports.get(id(self)) is not self:
                return
            self._service._final_evidence_ports.pop(id(self))
            active=getattr(self._service,'_diagnostic_inputs_active',{})
            for key,value in tuple(active.items()):
                if value[3] is self:
                    active.pop(key)
            sources = getattr(self._service, '_production_services_held', {})
            for key, source in tuple(sources.items()):
                if source[2] == self._lease and source[3] == self._thread:
                    sources.pop(key)
            for name in ('_affected_execution_held', '_affected_observation_held', '_diagnostic_inputs_held', '_diagnostic_records_held',
                         '_diagnostic_source_reads','_diagnostic_selections','_diagnostic_outcomes','_diagnostic_resumed_captures',
                         '_diagnostic_child_transitions','_diagnostic_terminal_inputs'):
                held = getattr(self._service, name, {})
                for key, value in tuple(held.items()):
                    if value[1] == self._lease and value[2] == self._thread:
                        if name=='_diagnostic_inputs_held' and len(value)>6 and value[6] is not self:
                            continue
                        held.pop(key)
