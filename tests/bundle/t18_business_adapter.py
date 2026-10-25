"""B11 ABI candidate; T16 history is retained and not retroactively proven."""
from t16_business_adapter import ServiceAdapter
from t18_bootstrap import create_bundle_service


class B11ServiceAdapter(ServiceAdapter):
    def __init__(self, admission_path, admission_sha256, binding_path, binding_sha256, journal):
        super().__init__(admission_path, admission_sha256, binding_path, binding_sha256,
                         create_bundle_service, journal)

    def material_allocation(self, lease, preparation_id, artifact_id):
        return self._call("material_allocation", lease, preparation_id, artifact_id)

    def evidence_policy(self, lease):
        return self._call("evidence_policy", lease)

    def benchmark_reference(self, lease):
        return self._call("benchmark_reference", lease)

    def correction_origin(self, lease, reference):
        return self._call("correction_origin", lease, reference)

    def verify_alignment_evidence(self, lease, preparation_id, *,
                                  actual_transcript_artifact_id,
                                  work_validation_artifact_id, audio_mappings):
        return self._call("verify_alignment_evidence", lease, preparation_id,
                          actual_transcript_artifact_id=actual_transcript_artifact_id,
                          work_validation_artifact_id=work_validation_artifact_id,
                          audio_mappings=audio_mappings)
