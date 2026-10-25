"""Private offline ASR v2 worker; actual text and observed source coordinates."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import os
import platform
import socket
import sys
import time
from dataclasses import asdict, is_dataclass
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction
from pathlib import Path

MODEL_FILES = ("config.json", "model.bin", "tokenizer.json", "vocabulary.txt")
METHOD_ID = "faster-whisper-small-word-estimate-v1"


class WorkerError(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def microseconds(seconds: float) -> int:
    value = Decimal(str(seconds))
    if not value.is_finite() or value < 0:
        raise WorkerError("asr_worker_failed")
    return int((value * 1_000_000).to_integral_value(rounding=ROUND_HALF_UP))


def rational_microseconds(seconds: Fraction) -> int:
    value = seconds * 1_000_000
    sign = -1 if value < 0 else 1
    return sign * ((2 * abs(value.numerator) + value.denominator) // (2 * value.denominator))


def _canonical_sha(value) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _configuration_value(value):
    # Record a library's actual unbounded option without emitting invalid JSON
    # or changing the option used for inference. Transcript numbers remain finite.
    if isinstance(value, float) and not math.isfinite(value):
        return {"type": "nonfinite_float", "encoding": "ieee754-special-v1",
                "value": "nan" if math.isnan(value) else "+infinity" if value > 0 else "-infinity"}
    if isinstance(value, dict):
        return {key: _configuration_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_configuration_value(item) for item in value]
    return value


def _resource_identity(request: dict, hashes: dict) -> str | None:
    if request.get("require_execution_identity") is not True:
        return None
    manifest_path = Path(request["resource_manifest_path"])
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise WorkerError("asr_model_changed")
    observed_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    if observed_sha != request["resource_manifest_sha256"]:
        raise WorkerError("asr_model_changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    root = manifest_path.resolve().parent
    relative = manifest["model_dir"]
    if (type(relative) is not str or Path(relative).is_absolute() or ".." in Path(relative).parts
        or not (root / relative).resolve().is_relative_to(root)
        or (root / relative).resolve() != Path(request["model_dir"]).resolve()
        or manifest["model_revision"] != request["model_revision"]
        or manifest["model_file_sha256"] != hashes):
        raise WorkerError("asr_model_changed")
    return observed_sha


def _input(request: dict):
    if (type(request) is not dict or type(request.get("max_audio_duration_us")) is not int
        or not 0 < request["max_audio_duration_us"] <= 600_000_000
        or type(request.get("model_revision")) is not str or not request["model_revision"]
        or type(request.get("audio_sha256")) is not str or len(request["audio_sha256"]) != 64
        or type(request.get("model_file_sha256")) is not dict or set(request["model_file_sha256"]) != set(MODEL_FILES)):
        raise WorkerError("asr_input_invalid")
    try:
        audio, root, model, runtime = (Path(request[name]) for name in ("audio_path", "storage_root", "model_dir", "runtime_root"))
    except (KeyError, TypeError):
        raise WorkerError("asr_input_invalid") from None
    if (audio.is_symlink() or not audio.is_file() or not audio.resolve().is_relative_to(root.resolve())
        or model.is_symlink() or not model.is_dir() or runtime.is_symlink() or not runtime.is_dir()):
        raise WorkerError("asr_input_invalid")
    if hashlib.sha256(audio.read_bytes()).hexdigest() != request["audio_sha256"]:
        raise WorkerError("asr_audio_changed")
    hashes = {}
    for name in MODEL_FILES:
        path = model / name
        if path.is_symlink() or not path.is_file():
            raise WorkerError("asr_model_changed")
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    if hashes != request["model_file_sha256"]:
        raise WorkerError("asr_model_changed")
    return audio, model, runtime, hashes


def transcribe(request: dict) -> dict:
    audio, model_dir, runtime_root, hashes = _input(request)
    resource_sha = _resource_identity(request, hashes)
    os.environ.update(HF_HOME=str(runtime_root / "HuggingFace"), HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_IMPLICIT_TOKEN="1")
    for name in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "HUGGINGFACE_HUB_TOKEN"):
        os.environ.pop(name, None)

    def deny_network(_socket, _address):
        raise WorkerError("asr_worker_failed")

    def progress(stage):
        with (runtime_root / "Progress.jsonl").open("a", encoding="utf-8", newline="\n") as output:
            output.write(json.dumps({"stage": stage, "monotonic_seconds": time.monotonic()}) + "\n")

    socket.socket.connect = deny_network
    socket.socket.connect_ex = deny_network
    import av
    import numpy as np
    from faster_whisper import WhisperModel

    progress("decode_entered")
    with audio.open("rb") as source:
        header = source.read(16)
    if header[:4] == b"RIFF" and header[8:12] == b"WAVE":
        demuxer = "wav"
    elif header[4:8] == b"ftyp":
        demuxer = "mov"
    else:
        raise WorkerError("asr_decode_failed")
    # Actual bytes choose a fixed parser; MOV data references stay disabled.
    options = {"protocol_whitelist": "file", "enable_drefs": "0", "use_absolute_path": "0"}
    decoded_samples, rate, samples, frames = 0, None, [], 0
    first_pts, first_base, last_pts, first_time = None, None, None, None
    resampler = av.AudioResampler(format="fltp", layout="mono", rate=16_000)
    try:
        with av.open(str(audio), format=demuxer, options=options) as container:
            streams = container.streams.audio
            if len(streams) != 1 or len(container.streams.video) > 1:
                raise WorkerError("asr_unsupported_streams")
            stream = streams[0]
            container_format, stream_index, codec = container.format.name, stream.index, stream.codec_context.name
            has_video = len(container.streams.video) == 1
            for frame in container.decode(stream):
                if rate is None:
                    rate = frame.sample_rate
                if not rate or rate != frame.sample_rate or frame.pts is None or frame.time_base is None:
                    raise WorkerError("asr_discontinuous_pts")
                at = Fraction(frame.pts) * Fraction(frame.time_base)
                if first_time is None:
                    first_time, first_pts, first_base = at, frame.pts, Fraction(frame.time_base)
                if at != first_time + Fraction(decoded_samples, rate):
                    raise WorkerError("asr_discontinuous_pts")
                frames += 1
                last_pts = frame.pts
                decoded_samples += frame.samples
                if Fraction(decoded_samples * 1_000_000, rate) > request["max_audio_duration_us"]:
                    raise WorkerError("asr_audio_too_long")
                for resampled in resampler.resample(frame):
                    samples.append(resampled.to_ndarray().reshape(-1))
            for resampled in resampler.resample(None):
                samples.append(resampled.to_ndarray().reshape(-1))
        if not decoded_samples or not rate:
            raise WorkerError("asr_decode_failed")
        video_pts, video_base, video_start, offset = None, None, None, 0
        if has_video:
            with av.open(str(audio), format=demuxer, options=options) as container:
                first_video = next(container.decode(container.streams.video[0]), None)
                if first_video is None or first_video.pts is None or first_video.time_base is None:
                    raise WorkerError("asr_discontinuous_pts")
                video_pts, video_base = first_video.pts, Fraction(first_video.time_base)
                video_start = Fraction(video_pts) * video_base
                offset = rational_microseconds(first_time - video_start)
    except WorkerError:
        raise
    except Exception as error:
        raise WorkerError("asr_decode_failed") from error
    duration_us = rational_microseconds(Fraction(decoded_samples, rate))
    waveform = np.concatenate(samples)
    if not np.isfinite(waveform).all():
        raise WorkerError("asr_decode_failed")
    progress("model_loading")
    constructor = {"device": "cpu", "compute_type": "int8", "cpu_threads": 4, "local_files_only": True}
    model = WhisperModel(str(model_dir), **constructor)
    progress("model_loaded")
    progress("transcribe_entered")
    generator, info = model.transcribe(waveform, language="zh", word_timestamps=True, vad_filter=True, condition_on_previous_text=False, beam_size=5)
    segments, previous_end = [], 0
    for segment in generator:
        start, end = microseconds(segment.start), microseconds(segment.end)
        if start < previous_end or end <= start or end > duration_us:
            raise WorkerError("asr_worker_failed")
        previous_end = end
        words, word_end = [], start
        for word in segment.words or []:
            wstart, wend = microseconds(word.start), microseconds(word.end)
            if wend <= wstart:
                continue
            if wstart < word_end or wend > end:
                raise WorkerError("asr_worker_failed")
            word_end = wend
            words.append({"text": word.word, "start_us": wstart, "end_us": wend})
        segments.append({"text": segment.text, "start_us": start, "end_us": end, "words": words})
    text = "".join(segment["text"] for segment in segments)
    if not text.strip():
        raise WorkerError("asr_no_speech")
    if hashlib.sha256(audio.read_bytes()).hexdigest() != request["audio_sha256"]:
        raise WorkerError("asr_audio_changed")
    progress("worker_completed")
    versions = {"python": platform.python_version(), **{name: importlib.metadata.version(name)
                for name in ("faster-whisper", "ctranslate2", "av", "numpy", "onnxruntime", "tokenizers")}}
    runtime = {"device": model.model.device, "requested_compute_type": constructor["compute_type"],
               "actual_compute_type": model.model.compute_type, "model_file_sha256": hashes,
               "versions": versions, "av_library_versions": {key: list(value) for key, value in av.library_versions.items()},
               "network_guard": "Python socket.connect/connect_ex denied; native egress not audited"}
    if resource_sha is not None:
        if not is_dataclass(info.transcription_options) or not is_dataclass(info.vad_options):
            raise WorkerError("asr_worker_failed")
        configuration = {"encoding_version": "asr-configuration-json-v1", "method_id": METHOD_ID,
                         "implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                         "python_sha256": hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
                         "versions": versions, "av_library_versions": runtime["av_library_versions"],
                         "model_constructor_arguments": constructor,
                         "actual_transcription_options": asdict(info.transcription_options),
                         "actual_vad_options": asdict(info.vad_options),
                         "audio_decode": {"format": demuxer, "options": options, "resampled_rate": resampler.rate,
                                          "resampled_format": resampler.format.name, "resampled_layout": resampler.layout.name},
                         "actual_device": model.model.device, "actual_compute_type": model.model.compute_type}
        configuration = _configuration_value(configuration)
        runtime["execution_configuration"] = configuration
        runtime["execution_identity"] = {"method_id": METHOD_ID, "tool": "faster-whisper", "tool_version": versions["faster-whisper"],
                "model_id": "faster-whisper-small", "model_file_sha256": hashes, "resource_manifest_sha256": resource_sha,
                "configuration_sha256": _canonical_sha(configuration), "compute_type": model.model.compute_type,
                "device": model.model.device, "operating_system": platform.system(), "architecture": platform.machine()}
    return {
        "protocol_version": "local-asr-v2", "kind": "actual_transcript", "text": text,
        "segments": segments, "coordinate_system": "audio_intrinsic", "video_audio_offset_us": offset,
        "duration_us": duration_us, "language": info.language,
        "timestamp_method": "whisper_word_estimate_not_forced_alignment",
        "model_revision": request["model_revision"], "input_audio_sha256": request["audio_sha256"],
        "decoded_samples": decoded_samples, "sample_rate": rate,
        "runtime": runtime,
        "audio_provenance": {
            "container_format": container_format, "audio_stream_index": stream_index, "audio_codec": codec,
            "decoded_frame_count": frames, "first_frame_pts": first_pts,
            "first_frame_time_base": {"numerator": first_base.numerator, "denominator": first_base.denominator},
            "last_frame_pts": last_pts, "pts_continuity": "verified_exact",
            "source_sample_rate": rate, "source_decoded_samples": decoded_samples,
            "intrinsic_duration_us": duration_us, "duration_rounding": "round_half_up_exact_samples_over_rate",
            "container_audio_start_us": rational_microseconds(first_time),
            "resampled_sample_rate": 16_000, "resampled_samples": int(waveform.size),
            "first_video_frame_pts": video_pts,
            "first_video_frame_time_base": None if video_base is None else {"numerator": video_base.numerator, "denominator": video_base.denominator},
            "container_video_start_us": None if video_start is None else rational_microseconds(video_start),
            "observed_audio_video_offset_us": offset,
            "offset_basis": "first_decoded_audio_minus_first_decoded_video_pts" if has_video else "not_applicable_audio_only",
            "request_offset_used": False,
            "timeline_mapping": "source_container_observed; final_edit_mapping_not_validated",
            "alignment": "whisper_word_estimate; independent_precision_not_measured",
        },
    }


if __name__ == "__main__":
    try:
        payload = sys.stdin.buffer.read(16_385)
        if len(payload) > 16_384:
            raise WorkerError("asr_input_invalid")
        result = transcribe(json.loads(payload))
        sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False, allow_nan=False).encode("utf-8"))
    except Exception as error:
        code = error.code if isinstance(error, WorkerError) else "asr_worker_failed"
        sys.stdout.buffer.write(json.dumps({"protocol_version": "local-asr-v2", "kind": "asr_error", "error_code": code, "exception_type": type(error).__name__}).encode("utf-8"))
        raise SystemExit(1) from None
