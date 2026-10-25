"""Fixed installed diagnostic producer and its actual source/output verifier."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from video_creator.domain import contracts as c
from video_creator.domain.bundle import MaterialReceipt
from video_creator.domain.component_diagnosis import ComponentDiagnosticCheckV1
from video_creator.domain.diagnostic_recovery import (
    DiagnosticFeedbackCompletion,
    DiagnosticMaterialCompletion,
    DiagnosticResourceCompletion,
)
from video_creator.domain.errors import EngineError
from video_creator.domain.plan_repair_targets import plan_payload_sha256
from video_creator.media.diagnostic_samples import decode_sources, frame_distance
from video_creator.providers.production_resources import (
    ProductionResources,
    file_sha256,
)
from video_creator.workflows.attempt_control import current_attempt

RULE = {"format": "component-decoder-review-v1", "frame_size": [64, 64], "cover_mean_rgb_error_limit": 12,
        "audio_sample_us": 2_000_000, "semantic_claims_from_metadata": False,
        "speech_text_difference_implies_tts_failure": False, "timing_difference_implies_tts_failure": False}
LOCAL_DESTINATION = "local:component-decoder-review-v1"


def _completion_text_body(completion, raw):
    """Represent actual authenticated bytes without inventing metadata MIME."""
    if type(completion) is DiagnosticFeedbackCompletion and completion.kind == "feedback":
        textual = True
    elif type(completion) is DiagnosticResourceCompletion and completion.kind == "qualified_resource":
        # This original metadata ref has no media_type. Its complete approved
        # content is supplied by the authenticated resource observer, not inferred.
        textual = True
    elif type(completion) is DiagnosticMaterialCompletion and completion.kind == "ready_material":
        if type(completion.ref) is not MaterialReceipt:
            raise EngineError("diagnostic_completion_invalid", "Ready material requires its original actual MaterialReceipt.", 422)
        media_type = completion.ref.media_type
        textual = media_type.startswith("text/") or media_type == "application/json"
    else:
        raise EngineError("diagnostic_completion_invalid", "Only the original three typed authenticated completion kinds are supported.", 422)
    if not textual:
        # Retain the original text-route binary boundary. The full bytes remain
        # in the actual local observation/check source; do not upload them here.
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        raise EngineError("diagnostic_completion_encoding_invalid", "The full authenticated text or metadata body must be valid UTF-8; never truncate or substitute a digest.", 422) from None


class ComponentDiagnosticPorts:
    """Created only by the fixed Engine factory, bound once to its real services."""
    def __init__(self, resources, storage_root):
        self.resources, self.storage_root = resources, Path(storage_root)
        self.services = None
        actual = resources.recipe_resources
        self.method_registrations = () if actual is None or actual.format != "registered-production-driver-resources-v3-diagnostic-v1" else actual.diagnosis.methods
        self._contexts = {}

    def bind_services(self, services):
        if self.services is not None:
            raise EngineError("diagnostic_service_binding_invalid", "The actual installed services may be bound only once.", 403)
        self.services = services

    def select_method(self, inputs):
        needed = {"cover_frame", "narration_source", "mix_source", "visual_source", "ambient_source"}
        if inputs.precision_report_ref is not None:
            needed.add("precision_boundary")
        candidates = [method for method in inputs.diagnostic_method_refs if needed <= set(method.check_kinds)
                      and method.rule_template_sha256 == plan_payload_sha256(RULE)]
        if len(candidates) != 1:
            raise EngineError("diagnostic_method_not_ready", "One actually registered complete method is required; distinct method Operations cannot be silently combined.", 503)
        method = candidates[0]
        if method.route.capability == "media_diagnosis" and method.route.destination != LOCAL_DESTINATION:
            raise EngineError("diagnostic_destination_denied", "Only the installed fixed local decoder-review route is implemented.", 403)
        expected = plan_payload_sha256({"input_key_sha256": inputs.input_key_sha256, "method_ref": method.model_dump(mode="json")})
        intents = [intent for intent in inputs.analysis_intents if intent.route_id == method.route.route_id and intent.input_sha256 == expected]
        if len(intents) != 1:
            raise EngineError("diagnostic_intent_invalid", "Use exactly the original backend-registered analysis intent.", 403)
        return method, intents[0]

    def _decoder(self, method):
        own = {file_sha256(Path(__file__)), file_sha256(Path(__file__).parents[1] / "media" / "diagnostic_samples.py")}
        if not own <= {ref.sha256 for ref in method.implementation_source_refs}:
            raise EngineError("diagnostic_method_not_ready", "The installed registration must cover the actual producer and decoder source bytes.", 503)
        ffmpeg_name = self.resources.section("edit", "ffmpeg")["ffmpeg"]
        return next((ref for ref in method.implementation_source_refs if ref.resource_name == ffmpeg_name
                     and ref.sha256 == file_sha256(self.resources.resource(ffmpeg_name))), None)

    def _local(self, lease, inputs, method, completions):
        decoder = self._decoder(method)
        if decoder is None:
            raise EngineError("diagnostic_method_not_ready", "The actual indexed decoder binary must be part of the registered method.", 503)
        decoded = decode_sources(self.services, lease, inputs, self.resources, self.storage_root, decoder)
        by_role = {source.role: (source, probe, samples) for source, probe, samples in decoded if source.role != "shot_clip"}
        if not {"video", "narration_audio", "mixed_audio", "cover"} <= set(by_role):
            raise EngineError("source_material_missing", "All four actual master sources are required.", 503)
        script = next((ref for ref in inputs.parent.assembly.creative_revision_refs if ref.kind == "script"), None)
        if script is None:
            raise EngineError("source_material_missing", "Original script provenance is required for speech diagnosis.", 503)
        completion_refs = tuple(completion.ref for completion, _ in completions)
        data, measurements = [], []
        kinds = {"cover_frame": ("cover", "cover"), "narration_source": ("narration_audio", "narration"),
                 "mix_source": ("mixed_audio", "mix"), "visual_source": ("video", "visual"),
                 "ambient_source": ("mixed_audio", "ambient")}
        for kind, (role, component) in kinds.items():
            source, _probe, samples = by_role[role]
            refs = (source,) + tuple(ref for _, ref, _ in samples if ref is not None) + completion_refs
            expected = script if kind == "narration_source" else source
            if kind == "narration_source":
                refs += (script,)
            observed, status = "matches", "not_supported"
            limitations = ("Actual complete decoding and bounded samples do not establish narrative or aesthetic correctness.",)
            uncertainty = ()
            if kind == "cover_frame":
                video = by_role["video"]
                cover_rgb = next(raw for channel, _, raw in samples if channel == "frame")
                video_ref, video_rgb = next((ref, raw) for channel, ref, raw in video[2] if channel == "frame")
                refs += (video[0], video_ref)
                expected = video_ref
                error = frame_distance(cover_rgb, video_rgb)
                measurements.append({"check_id": "component.cover_frame", "mean_rgb_error": error,
                    "cover_rgb_sha256": hashlib.sha256(cover_rgb).hexdigest(), "video_frame_ref": video_ref.model_dump(mode="json")})
                observed, status = ("matches" if error <= RULE["cover_mean_rgb_error_limit"] else "differs"), "supported"
                limitations = ("Decoded first-frame RGB comparison uses the registered compression tolerance; no visual meaning is inferred.",)
            if completions and kind != "cover_frame":
                # Feedback has been read in full. A local decoder cannot certify
                # a semantic complaint merely because source containers decode.
                observed, status, uncertainty = "unavailable", "undetermined", ("analysis_inconclusive",)
            if kind == "ambient_source":
                clips = [item for item in decoded if item[0].role == "shot_clip"]
                refs += tuple(item[0] for item in clips) + tuple(ref for item in clips for channel, ref, _ in item[2] if channel == "audio" and ref is not None)
                if not clips:
                    observed, status, uncertainty = "unavailable", "undetermined", ("source_material_missing",)
                    limitations += ("The controlled parent source does not expose its original clip soundtracks; mixed output cannot substitute for source ambient audio.",)
            data.append(ComponentDiagnosticCheckV1(check_id="component." + kind, check_kind=kind, component=component,
                source_refs=refs, shot_ids=source.shot_ids, intrinsic_range=source.intrinsic_range,
                timeline_range=source.timeline_range, expected_ref=expected, observed_ref=samples[0][1] if samples and samples[0][1] is not None else source,
                observed_result=observed, assertion_status=status, evidence_strength="deterministic_observation",
                limitations=limitations, uncertainty_codes=uncertainty).model_dump(mode="json"))
        if inputs.precision_report_ref is not None:
            report = inputs.precision_report_ref
            if inputs.precision_report_bytes is None or (len(inputs.precision_report_bytes), hashlib.sha256(inputs.precision_report_bytes).hexdigest()) != (report.size, report.sha256):
                raise EngineError("diagnostic_precision_source_invalid", "Timing analysis retains its complete actual independent READY report.", 422)
            data.append(ComponentDiagnosticCheckV1(check_id="component.precision_boundary", check_kind="precision_boundary", component=None,
                source_refs=(report,) + completion_refs, shot_ids=(), intrinsic_range=None, timeline_range=None,
                expected_ref=report, observed_ref=report, observed_result="differs" if inputs.failed_unit_ids else "matches",
                assertion_status="supported", evidence_strength="deterministic_observation",
                limitations=("Report-derived timing failure does not identify a narration or animation cause.",), uncertainty_codes=()).model_dump(mode="json"))
        return {"checks": data, "measurements": measurements, "input_key_sha256": inputs.input_key_sha256,
                "completion_sources": [{"ref": completion.ref.model_dump(mode="json"), "kind": completion.kind,
                    "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "body_hex": raw.hex()} for completion, raw in completions],
                "limitations": ["Actual sampled data and approved text only; no metadata substitutes for listening or scene interpretation."]}

    def driver(self, lease, inputs, method, intent, completions):
        if self.services is None or inputs.binding.run_id != lease.run_id or self.services.engine.configured_route(intent.route_id) != method.route:
            raise EngineError("diagnostic_service_binding_invalid", "Real same-Run services and the exact configured route are required.", 403)
        self._contexts[inputs.input_key_sha256] = (inputs, lease, completions)
        if len(self._contexts) > 32:
            del self._contexts[next(iter(self._contexts))]
        if method.route.capability == "text":
            # Text-only observations need decoded information, never a claim
            # that this endpoint directly watched or listened to source media.
            from video_creator.providers.deepseek import MODEL, DeepSeekTextDriver
            if method.model_binding != MODEL:
                raise EngineError("diagnostic_model_not_ready", "This fixed text adapter cannot impersonate another model or multimodal endpoint.", 503)
            text_sources = {"sources": [source.model_dump(mode="json") for source in inputs.source_media_refs],
                "approved_supplements": [{"ref": completion.ref.model_dump(mode="json"),
                    "body": _completion_text_body(completion, raw),
                    "binary_sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)} for completion, raw in completions]}
            messages = [{"role": "system", "content": "Return JSON with roles: director, editor, sound. Each contains assessment and limitations. Discuss only supplied source metadata and approved text. You did not watch or hear media; metadata cannot establish a scene or sound failure. Do not grant permissions or claim component failure from timing alone."},
                        {"role": "user", "content": json.dumps(text_sources, ensure_ascii=False, allow_nan=False)}]
            text = DeepSeekTextDriver(messages, max_tokens=2048, json_mode=True)
            payload = text.payload

            def invoke(permit, secret):
                self._permit(lease, method, permit)
                local = self._local(lease, inputs, method, completions)
                response = text(permit, secret)
                if response.status != "succeeded":
                    return response
                content = response.result_json.get("content") if type(response.result_json) is dict else None
                try:
                    opinions = json.loads(content)
                    if type(opinions) is not dict or set(opinions) != {"roles"} or set(opinions["roles"]) != {"director", "editor", "sound"}:
                        raise ValueError("actual roles missing")
                    for role in opinions["roles"].values():
                        if type(role) is not dict or set(role) != {"assessment", "limitations"} or any(type(value) is not str or not value or len(value) > 4000 for value in role.values()):
                            raise ValueError("actual attributed role output missing")
                except (ValueError, TypeError):
                    raise EngineError("diagnostic_model_output_invalid", "The actual response must contain every bounded attributed role and its limitations.", 422) from None
                return response.model_copy(update={"result_json": {**local, "model_response": response.result_json, "role_opinions": opinions,
                    "limitations": local["limitations"] + ["One original text completion with three attributed role perspectives; this is not independently executed multi-agent delegation."]}})
            return invoke, payload

        def invoke(permit, secret):
            self._permit(lease, method, permit)
            if secret is not None:
                raise EngineError("diagnostic_local_credentials_denied", "Local decoding cannot consume model credentials.", 403)
            return c.OperationObservation(status="succeeded", actual_cost=c.Money(amount="0"), cost_evidence="confirmed_no_charge",
                result_json=self._local(lease, inputs, method, completions))
        return invoke, None

    def _permit(self, lease, method, permit):
        current_attempt().check()
        if (permit.run_id, permit.fencing_token, permit.route) != (lease.run_id, lease.fencing_token, method.route):
            raise EngineError("diagnostic_permit_invalid", "Only the original registered route, Run and fenced permit may execute this method.", 403)

    def observation_checks(self, inputs, method, result, output_ref, completions):
        if result.get("input_key_sha256") != inputs.input_key_sha256:
            raise EngineError("diagnostic_output_invalid", "The actual response retains the original diagnostic input.", 422)
        checks = tuple(ComponentDiagnosticCheckV1.model_validate_json(json.dumps(value, allow_nan=False)) for value in result["checks"])
        if method.route.capability == "media_diagnosis":
            return tuple(check.model_copy(update={"source_refs": check.source_refs + (output_ref,)}) for check in checks)
        if method.route.capability == "text":
            checks = tuple(check.model_copy(update={"source_refs": check.source_refs + (output_ref,), "observed_ref": output_ref,
                "evidence_strength": "attributed_model_assessment", "assertion_status": "undetermined",
                "observed_result": "unavailable", "uncertainty_codes": ("analysis_inconclusive",),
                "limitations": check.limitations + ("Actual text-role opinions are attributed; semantic cause needs a qualified media observation method.",)}) for check in checks)
        return checks

    def verify_component_observation(self, inputs, observation, *, operation_observations):
        from video_creator.domain.component_diagnosis import (
            DiagnosticOperationOutputRefV1,
        )
        context = self._contexts.get(inputs.input_key_sha256)
        if context is None or context[0] != inputs or len(operation_observations) != 1:
            raise EngineError("diagnostic_verification_context_missing", "Recheck the actual original method inputs and its settled Operation.", 409)
        _, lease, completions = context
        reference, result = operation_observations[0]
        expected = self._local(lease, inputs, observation.method_ref, completions)
        raw = result.result_json
        for field in ("checks", "measurements", "input_key_sha256", "completion_sources"):
            if raw.get(field) != expected[field]:
                raise EngineError("diagnostic_recheck_failed", "Actual decoded sources and complete supplements differ from the original successful output.", 422)
        output = DiagnosticOperationOutputRefV1(format="component-diagnostic-operation-output-v1",
            operation_id=reference.operation_id, input_sha256=reference.input_sha256,
            observation_sha256=reference.observation_sha256, output_sha256=reference.output_sha256)
        checks = self.observation_checks(inputs, observation.method_ref, raw, output, completions)
        if checks != observation.checks or tuple(raw["limitations"]) != observation.limitations:
            raise EngineError("diagnostic_recheck_failed", "Actual attributed output and original checks must remain complete and identical.", 422)
        return observation


def create_component_diagnostic_ports(*, resource_manifest_path, resource_manifest_sha256, runtime_manifest_sha256, storage_root):
    resources = ProductionResources(resource_manifest_path, resource_manifest_sha256, runtime_manifest_sha256)
    if resources.recipe_resources is None or resources.recipe_resources.format != "registered-production-driver-resources-v3-diagnostic-v1":
        return None
    return ComponentDiagnosticPorts(resources, storage_root)
