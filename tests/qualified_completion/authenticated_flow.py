"""Executable downstream assertions requiring REAL existing factory-held inputs.

These functions are not collected as unit cases and are currently NOT_READY.
They never construct or register an Owner, issuer, factory, held source or grant.
"""

from video_creator.domain.component_diagnosis import ComponentDiagnosticObservationV1, RegisteredComponentDiagnosisV1
from video_creator.domain.diagnostic_recovery import RegisteredComponentDiagnosisInputsV2


def verify_normal_record_and_explicit_recovery(service, lease, inputs, observation):
    if type(inputs) is not RegisteredComponentDiagnosisInputsV2 or type(observation) is not ComponentDiagnosticObservationV1:
        raise TypeError("Original full registered inputs and actual observation required")
    # Real consumer performs all original current/rights/Operation/source checks.
    registered = service.record_component_diagnosis(lease, inputs, observation)
    if type(registered) is not RegisteredComponentDiagnosisV1:
        raise AssertionError("Original registered diagnostic record required")
    recovered = service._read_explicit_diagnostic_record(lease, registered.ref, inputs.parent_preparation_id)
    assert recovered.ref == registered.ref
    assert recovered.fact == registered.fact
    assert recovered.fact.checks == observation.checks
    # No patched verifier or forced qualified observer. A still-unimplemented
    # real observer remains an error, not a callback returning successful bytes.
    for completion in inputs.completion_source_refs:
        raw = service.read_diagnostic_completion(lease, inputs, completion)
        assert type(raw) is bytes
    return registered, recovered


def verify_real_refusal(expected_code, expected_status, action):
    """Called with a real resource/current/rights invalidation scenario, not True."""
    from video_creator.domain.errors import EngineError
    try:
        action()
    except EngineError as error:
        assert (error.code, error.status_code) == (expected_code, expected_status)
    else:
        raise AssertionError("Actual invalidated source/current/rights action succeeded")
