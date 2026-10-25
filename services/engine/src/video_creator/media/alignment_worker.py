"""Offline CPU CTC worker. No ASR, reference boundaries, downloads or authority.

The installed engine/helper/model/runtime closure is supplied by the trusted
parent. One original request yields one complete JSON Alignment, never an Asset.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import os
import platform
import sys
from pathlib import Path

PROTOCOL = "registered-ctc-worker-v1"
CONFIG = {"format": "whisperx-3.8.6-ctc-zh-cpu-v1", "device": "cpu", "compute_type": "float32",
          "sample_rate": 16000, "maximum_duration_us": 600_000_000, "window_us": 30_000_000,
          "context_us": 500_000, "normalization": "nfc-lower-cluster-original-scalar-span-v1",
          "time_quantization": "actual-convolution-stride-samples-half-up-us-v1",
          "torch_threads": 4, "minimum_character_probability": 0.01,
          "algorithm_sha256": "cc3607dcc25e592ae218f74a6ca644d6ce1c77d9cee4672f01c751da8feb9aa7"}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("alignment_duplicate_json_key")
        result[key] = value
    return result


def read_json(raw):
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("alignment_nonfinite_json")))


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def exact_file(root, name, expected):
    from pathlib import PurePosixPath

    relative = PurePosixPath(name)
    if (relative.is_absolute() or relative.as_posix() != name or not relative.parts
            or any(part in {".", ".."} or ":" in part or "\\" in part for part in relative.parts)):
        raise ValueError("alignment_resource_path_invalid")
    path = root.joinpath(*relative.parts)
    if (not path.is_file() or not path.resolve(strict=True).is_relative_to(root)
            or any(p.is_symlink() or p.is_junction() for p in (path, *path.parents) if p.is_relative_to(root))
            or sha(path) != expected):
        raise ValueError("alignment_resource_changed")
    return path


def half_up(numerator, denominator):
    return (2 * numerator + denominator) // (2 * denominator)


def decode_audio(path, track):
    import av
    import numpy as np

    arrays, native_samples, origin = [], 0, None
    clock = track["clock"]
    resampler = av.AudioResampler(format="fltp", layout="mono", rate=16000)
    with av.open(str(path), mode="r", options={"protocol_whitelist": "file"}) as container:
        streams = [s for s in container.streams.audio if s.index == track["stream_index"]]
        if len(streams) != 1:
            raise ValueError("alignment_original_audio_stream_missing")
        stream = streams[0]
        if (stream.codec_context.sample_rate != clock["sample_rate"]
                or stream.time_base is None or clock["timebase_num"] != stream.time_base.numerator
                or clock["timebase_den"] != stream.time_base.denominator):
            raise ValueError("alignment_original_audio_clock_changed")
        for frame in container.decode(stream):
            if origin is None:
                origin = frame.pts
            if frame.sample_rate != clock["sample_rate"]:
                raise ValueError("alignment_audio_rate_changed")
            native_samples += frame.samples
            if native_samples > clock["sample_rate"] * 600:
                raise ValueError("alignment_audio_duration_exceeded")
            arrays.extend(x.to_ndarray().reshape(-1) for x in resampler.resample(frame))
        arrays.extend(x.to_ndarray().reshape(-1) for x in resampler.resample(None))
    if native_samples != clock["decoded_sample_count"] or origin != clock["origin_pts"] or not arrays:
        raise ValueError("alignment_original_decoded_audio_changed")
    waveform = np.concatenate(arrays).astype(np.float32, copy=False)
    duration = half_up(native_samples * 1_000_000, clock["sample_rate"])
    if (not np.isfinite(waveform).all() or not 0 < duration <= 600_000_000
            or abs(len(waveform) - half_up(native_samples * 16000, clock["sample_rate"])) > 1):
        raise ValueError("alignment_resampling_invalid")
    return waveform, duration


def align_window(waveform, start_us, end_us, text, model, vocabulary, blank, configuration):
    import torch

    from video_creator.media.alignment_text import character_map
    from video_creator.media.ctc_alignment import backtrack, get_trellis, merge_repeats

    mapped = character_map(text, vocabulary)
    first = max(0, (start_us - CONFIG["context_us"]) * 16000 // 1_000_000)
    last = min(len(waveform), (end_us + CONFIG["context_us"]) * 16000 // 1_000_000)
    if not 0 < last - first <= CONFIG["window_us"] * 16000 // 1_000_000:
        raise ValueError("alignment_window_exceeds_bounded_anchor")
    signal = torch.from_numpy(waveform[first:last].copy()).unsqueeze(0)
    if configuration.get("do_normalize") is True:
        signal = (signal - signal.mean()) / torch.sqrt(signal.var(unbiased=False) + 1e-7)
    with torch.inference_mode():
        emission = torch.log_softmax(model(signal).logits[0].float(), dim=-1)
    if not torch.isfinite(emission).all() or emission.shape[0] <= len(mapped["characters"]):
        raise ValueError("alignment_emission_invalid")
    tokens = [value["token"] for value in mapped["characters"]]
    path = backtrack(get_trellis(emission, tokens, blank_id=blank), emission, tokens, blank_id=blank)
    if path is None:
        raise ValueError("alignment_ctc_backtrack_failed")
    segments = merge_repeats(path, [value["character"] for value in mapped["characters"]])
    if len(segments) != len(tokens):
        raise ValueError("alignment_ctc_character_coverage_incomplete")
    stride = math.prod(model.config.conv_stride)
    observed = []
    for character, segment in zip(mapped["characters"], segments, strict=True):
        if (segment.label != character["character"] or not math.isfinite(segment.score)
                or segment.score < CONFIG["minimum_character_probability"]):
            raise ValueError("alignment_ctc_character_confidence_insufficient")
        a, b = first + segment.start * stride, min(last, first + segment.end * stride)
        if a >= b:
            raise ValueError("alignment_ctc_frame_range_invalid")
        observed.append({"character": character["character"], "start_us": half_up(a * 1_000_000, 16000),
                         "end_us": half_up(b * 1_000_000, 16000)})
    return observed


def execute(protocol):
    # Only installed closure names enter sys.path; caller text cannot choose a module.
    root = Path(protocol["resource_root"]).resolve(strict=True)
    for name, expected in protocol["engine_files"].items():
        exact_file(root, name, expected)
    engine_root = exact_file(root, protocol["engine_marker"], protocol["engine_files"][protocol["engine_marker"]]).parent
    if engine_root.name != "video_creator":
        raise ValueError("alignment_installed_engine_layout_invalid")
    sys.path.insert(0, str(engine_root.parent))
    import torch
    from transformers import Wav2Vec2Config, Wav2Vec2ForCTC

    from video_creator.domain import contracts as c
    from video_creator.domain.registered_alignment import (
        AffectedAlignmentRequest,
        InitialAlignmentRequest,
        alignment_request_bytes,
    )
    from video_creator.media.alignment_text import (
        aggregate_units,
        character_map,
        map_units,
    )

    raw = canonical(protocol["request"])
    kind = InitialAlignmentRequest if protocol["request"]["format"] == "registered-initial-alignment-request-v1" else AffectedAlignmentRequest
    request = kind.model_validate_json(raw)
    if alignment_request_bytes(request) != raw or hashlib.sha256(raw).hexdigest() != protocol["request_sha256"]:
        raise ValueError("alignment_original_request_changed")
    resource = request.alignment_registration
    if sha(Path(__file__)) != resource.worker_sha256 or sha(Path(sys.executable)) != resource.runtime_sha256:
        raise ValueError("alignment_worker_changed")
    original_model_files = {name: exact_file(root, name, expected) for name, expected in resource.resources.model_files.items()}
    model_files = {Path(name).name: path for name, path in original_model_files.items()}
    if len(model_files) != len(resource.resources.model_files) or not {"config.json", "vocab.json", "preprocessor_config.json", "pytorch_model.bin"} <= set(model_files):
        raise ValueError("alignment_complete_model_files_required")
    model_config = read_json(model_files["config.json"].read_bytes())
    preprocessing = read_json(model_files["preprocessor_config.json"].read_bytes())
    vocabulary = read_json(model_files["vocab.json"].read_bytes())
    if (model_config.get("auto_map") or model_config.get("model_type") != "wav2vec2"
            or preprocessing.get("sampling_rate") != 16000
            or type(preprocessing.get("do_normalize")) is not bool
            or importlib.metadata.version("torch").split("+")[0] != "2.8.0"
            or importlib.metadata.version("whisperx") != "3.8.6"):
        raise ValueError("alignment_runtime_configuration_not_supported")
    config_sha = hashlib.sha256(canonical(CONFIG)).hexdigest()
    identity = c.AlignmentExecutionIdentity(method_id=CONFIG["format"], tool="WhisperX", tool_version="3.8.6",
        model_id="wav2vec2-large-xlsr-53-chinese", model_file_sha256={name: sha(path) for name, path in original_model_files.items()},
        resource_manifest_sha256=resource.resource_manifest_sha256, configuration_sha256=config_sha,
        compute_type="float32", device="cpu", operating_system=platform.system(), architecture=platform.machine())
    if identity != resource.registration.method_qualification_ref.execution_identity or config_sha != resource.resources.configuration_sha256:
        raise ValueError("alignment_actual_runtime_not_qualified")
    torch.set_num_threads(CONFIG["torch_threads"])
    model = Wav2Vec2ForCTC(Wav2Vec2Config.from_dict(model_config))
    weights = torch.load(model_files["pytorch_model.bin"], map_location="cpu", weights_only=True)
    if type(weights) is not dict or not weights or any(not isinstance(value, torch.Tensor) for value in weights.values()):
        raise ValueError("alignment_safe_state_dictionary_required")
    model.load_state_dict(weights, strict=True)
    model = model.to(device="cpu", dtype=torch.float32).eval()
    if any(parameter.device.type != "cpu" or parameter.dtype != torch.float32 for parameter in model.parameters()):
        raise ValueError("alignment_actual_compute_changed")
    blank = model.config.pad_token_id
    if type(blank) is not int or blank not in vocabulary.values():
        raise ValueError("alignment_blank_token_invalid")
    audio = Path(protocol["audio_path"])
    if audio.is_symlink() or audio.is_junction() or (audio.stat().st_size, sha(audio)) != (request.audio.size, request.audio.sha256):
        raise ValueError("alignment_audio_changed")
    waveform, duration = decode_audio(audio, request.audio.input_track.model_dump(mode="json"))
    if duration != request.transcript.transcript.duration_us:
        raise ValueError("alignment_original_duration_changed")
    utterances = {value.utterance_id: value for value in request.transcript.transcript.utterances}
    observations = {}
    for unit in request.unit_sources:
        if unit.transcript_unit_id not in request.allowed_unit_ids:
            continue
        ranges = [(unit.text, unit.predicted_range.start_us, unit.predicted_range.end_us)]
        if unit.predicted_range.end_us - unit.predicted_range.start_us + 2 * CONFIG["context_us"] > CONFIG["window_us"]:
            utterance = utterances[unit.utterance_id]
            if unit.word_id is not None or not utterance.words:
                raise ValueError("alignment_long_utterance_requires_actual_word_anchors")
            ranges = [(value.text, value.intrinsic_range.start_us, value.intrinsic_range.end_us) for value in utterance.words]
            map_units(unit.text, [{"unit_id": value.word_id, "text": value.text} for value in utterance.words], vocabulary)
        characters = []
        for text, start, end in ranges:
            characters.extend(align_window(waveform, start, end, text, model, vocabulary, blank, preprocessing))
        mapped = character_map(unit.text, vocabulary)
        mapped["units"] = [{"unit_id": unit.transcript_unit_id, "text": unit.text, "character_start": 0,
                            "character_end": len(mapped["characters"])}]
        observations[unit.transcript_unit_id] = aggregate_units(mapped, characters, duration)[0]
    boundaries = []
    previous = 0
    for unit in request.unit_sources:
        observed = observations.get(unit.transcript_unit_id)
        value = unit.predicted_range if observed is None else c.MediaRange(start_us=observed["start_us"], end_us=observed["end_us"])
        if value.start_us < previous or value.end_us > duration:
            raise ValueError("alignment_original_order_not_preserved")
        previous = value.end_us
        boundaries.append(c.AlignmentUnit(unit_id=unit.alignment_unit_id, transcript_unit_id=unit.transcript_unit_id, intrinsic_range=value))
    result = c.AlignmentRevisionV03(alignment_revision_id=request.output_alignment_revision_id,
        actual_transcript_revision_id=request.transcript.transcript.transcript_revision_id,
        transcript_content_sha256=request.transcript.transcript.content_sha256,
        input_audio_asset_id=request.audio.asset_id, input_audio_sha256=request.audio.sha256,
        units="word" if all(value.word_id is not None for value in request.unit_sources) else "utterance",
        boundaries=tuple(boundaries), timestamp_method="forced_ctc_actual_convolution_frames",
        method_ref=identity.method_id, precision=c.PrecisionAssessmentV03(status="not_measured",
            units="word" if all(value.word_id is not None for value in request.unit_sources) else "utterance",
            limitations=("Independent per-work boundaries were not supplied to inference.",)),
        confidence_unavailable_reason="Character admission thresholds are not a calibrated transcript confidence.", content_sha256="0" * 64)
    body = result.model_dump(mode="json")
    body.pop("content_sha256")
    result = result.model_copy(update={"content_sha256": hashlib.sha256(canonical(body)).hexdigest()})
    output = Path(protocol["partial_output"])
    output_root = Path(protocol["storage_root"]).resolve(strict=True)
    if (not output.resolve().is_relative_to(output_root) or output.exists()
            or any(p.is_symlink() or p.is_junction() for p in (output, *output.parents) if p.is_relative_to(output_root))):
        raise ValueError("alignment_output_denied")
    content = canonical(result.model_dump(mode="json")) + b"\n"
    if len(content) > 8 * 1024 * 1024:
        raise ValueError("alignment_output_exceeded")
    with output.open("xb") as target:
        target.write(content)
        target.flush()
        os.fsync(target.fileno())
    return {"protocol": PROTOCOL, "status": "succeeded", "request_sha256": protocol["request_sha256"],
            "output_sha256": hashlib.sha256(content).hexdigest(), "output_bytes": len(content),
            "execution_identity": identity.model_dump(mode="json"),
            "audio_observation": {"duration_us": duration, "resampled_samples": len(waveform), "sample_rate": 16000}}


def main():
    raw = sys.stdin.buffer.read(16 * 1024 * 1024 + 1)
    try:
        if len(raw) > 16 * 1024 * 1024:
            raise ValueError("alignment_input_exceeded")
        protocol = read_json(raw)
        if protocol["protocol"] != PROTOCOL:
            raise ValueError("alignment_protocol_invalid")
        result = execute(protocol)
    except Exception:  # noqa: BLE001 - no private paths, tensor values or raw exception in child output.
        sys.stdout.buffer.write(canonical({"protocol": PROTOCOL, "status": "failed", "error": "alignment_worker_failed"}))
        return 1
    sys.stdout.buffer.write(canonical(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
