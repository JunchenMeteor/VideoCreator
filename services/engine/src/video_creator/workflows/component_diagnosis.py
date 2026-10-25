"""Original diagnostic inputs, paid/local Operations and immutable source facts."""
from __future__ import annotations

from video_creator.domain.component_diagnosis import (
    ComponentDiagnosticObservationV1,
    DiagnosticOperationOutputRefV1,
    RegisteredComponentDiagnosisInputsV1,
    RegisteredComponentDiagnosisV1,
)
from video_creator.domain.diagnostic_recovery import CurrentDiagnosticSourceRead
from video_creator.domain.errors import EngineError
from video_creator.domain.plan_repair_targets import plan_payload_sha256
from video_creator.workflows.attempt_control import current_attempt


def _completions(port, inputs):
    """Read every actual completion body; a locator alone is not information."""
    from video_creator.domain.diagnostic_recovery import (
        RegisteredComponentDiagnosisInputsV2,
    )

    if type(inputs) is RegisteredComponentDiagnosisInputsV1:
        return ()
    if type(inputs) is not RegisteredComponentDiagnosisInputsV2:
        raise EngineError("diagnostic_input_invalid", "Only the original registered diagnostic input versions may be consumed.", 403)
    result = []
    for completion in inputs.completion_source_refs:
        current_attempt().check()
        raw = port.read_diagnostic_completion(inputs, completion)
        if type(raw) is not bytes or not raw or len(raw) > 2 * 1024 * 1024:
            raise EngineError("diagnostic_completion_invalid", "Actual complete bounded source bytes are required.", 422)
        result.append((completion, raw))
    return tuple(result)


def analyse(port, lease, inputs, services):
    """Execute only the installed method covering the finite original checks."""
    from video_creator.application.engine import canonical, digest
    from video_creator.providers.component_diagnosis import ComponentDiagnosticPorts

    methods = services.component_diagnostic_ports
    if type(methods) is not ComponentDiagnosticPorts or methods.services is not services:
        raise EngineError("diagnostic_method_not_ready", "The actual same-runtime diagnostic implementation is not installed.", 503)
    completions = _completions(port, inputs)
    method, intent = methods.select_method(inputs)
    services.engine.begin_step(lease, intent.step_key, intent.input_sha256)
    original = services.engine.prepare_operation(lease, intent)
    driver, payload = methods.driver(lease, inputs, method, intent, completions)
    observation = services.executor.execute(lease, intent, driver, request_payload=payload)
    if observation.status != "succeeded" or type(observation.result_json) is not dict:
        raise EngineError("analysis_operation_unsettled", "Retain the original analysis outcome; unknown acceptance cannot submit another Operation.", 409,
                          "reconcile" if observation.status in {"unknown", "pending"} else "never")
    output_ref = DiagnosticOperationOutputRefV1(format="component-diagnostic-operation-output-v1",
        operation_id=original["id"], input_sha256=intent.input_sha256,
        observation_sha256=digest(canonical(observation)), output_sha256=plan_payload_sha256(observation.result_json))
    checks = methods.observation_checks(inputs, method, observation.result_json, output_ref, completions)
    actual = ComponentDiagnosticObservationV1(format="current-component-diagnostic-observation-v1",
        input_key_sha256=inputs.input_key_sha256, method_ref=method,
        analysis_operation_ids=(original["id"],), checks=checks,
        limitations=tuple(observation.result_json["limitations"]))
    services.engine.complete_step(lease, intent.step_key,
        result_json={"observation_sha256": output_ref.observation_sha256, "output_sha256": output_ref.output_sha256})
    current_attempt().check()
    return actual


def prepare_initial(port, lease, preparation_id, services):
    """Initial current producer selects its actual immutable diagnostic record."""
    if services.component_diagnostic_ports is None:
        return None  # Original v1/v2 installation, never a fabricated diagnosis.
    inputs = port.prepare_component_diagnosis(preparation_id)
    recorded = port.read_recorded_component_diagnosis(inputs)
    if recorded is None:
        recorded = port.record_component_diagnosis(inputs, analyse(port, lease, inputs, services))
    if type(recorded) is not RegisteredComponentDiagnosisV1 or recorded.ref.input_key_sha256 != inputs.input_key_sha256:
        raise EngineError("diagnostic_record_invalid", "Only the actual indexed fact for these original inputs may be used.", 409)
    return recorded


def resume_diagnosis(port, lease, continuation, diagnostic_source, services):
    """Analysis-only precedes ASR, repair, masters and the final whole verifier."""
    if type(diagnostic_source) is not CurrentDiagnosticSourceRead:
        raise EngineError("diagnostic_source_invalid", "An actual held diagnostic source is required.", 403)
    if diagnostic_source.execution_fence != lease.fencing_token or diagnostic_source.source.binding != continuation.binding:
        raise EngineError("diagnostic_source_conflict", "The original source retains this same Run binding and current fence.", 409)
    context = diagnostic_source.source.resume_context
    if context is None:
        return None
    if context.work_kind == "final_validation_after_analysis":
        return None  # Original new-continuation final verifier, exactly once.
    if context.work_kind not in {"reuse_record", "analyse_changed_input"}:
        raise EngineError("diagnostic_resume_invalid", "Unknown work kinds cannot cause media effects.", 409)
    inputs = port.prepare_component_diagnosis(continuation.snapshot.preparation_id,
        continuation=continuation, resume_probe=diagnostic_source)
    recorded = port.read_recorded_component_diagnosis(inputs)
    if recorded is None:
        if context.work_kind == "reuse_record":
            raise EngineError("diagnostic_record_unavailable", "The exact expected immutable record is missing; reuse cannot execute an analysis.", 409)
        recorded = port.append_component_diagnosis(inputs, analyse(port, lease, inputs, services))
    if type(recorded) is not RegisteredComponentDiagnosisV1 or recorded.ref.input_key_sha256 != inputs.input_key_sha256:
        raise EngineError("diagnostic_record_invalid", "Analysis recovery must use the actual same-input indexed record.", 409)
    current_attempt().check()
    return port.assess_resumed_component_diagnosis(continuation, recorded)
