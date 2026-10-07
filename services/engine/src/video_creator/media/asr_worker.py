"""Private offline worker for an isolated ASR interpreter; JSON over stdin/stdout."""

from __future__ import annotations

import hashlib
import json
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path


def microseconds(seconds: float) -> int:
    value = Decimal(str(seconds))
    if not value.is_finite() or value < 0:
        raise ValueError("invalid timestamp")
    return int((value * 1_000_000).to_integral_value(rounding=ROUND_HALF_UP))


def transcribe(request: dict) -> dict:
    import av
    import numpy as np
    from faster_whisper import WhisperModel

    audio = Path(request["audio_path"])
    root = Path(request["storage_root"])
    if audio.is_symlink() or not audio.resolve().is_relative_to(root.resolve()):
        raise ValueError("audio path denied")
    if hashlib.sha256(audio.read_bytes()).hexdigest() != request["audio_sha256"]:
        raise ValueError("audio changed")
    decoded_samples, rate, samples = 0, None, []
    resampler = av.AudioResampler(format="fltp", layout="mono", rate=16_000)
    with av.open(str(audio)) as container:
        streams = container.streams.audio
        if len(streams) != 1:
            raise ValueError("one audio stream required")
        for frame in container.decode(streams[0]):
            if rate is None:
                rate = frame.sample_rate
            if not rate or rate != frame.sample_rate:
                raise ValueError("inconsistent audio sample rate")
            decoded_samples += frame.samples
            if decoded_samples * 1_000_000 // rate > request["max_audio_duration_us"]:
                raise ValueError("audio too long")
            for resampled in resampler.resample(frame):
                samples.append(resampled.to_ndarray().reshape(-1))
        for resampled in resampler.resample(None):
            samples.append(resampled.to_ndarray().reshape(-1))
    if not decoded_samples or not rate:
        raise ValueError("no decoded audio")
    duration_us = decoded_samples * 1_000_000 // rate
    model = WhisperModel(
        request["model_dir"],
        device="cpu",
        compute_type="int8",
        cpu_threads=4,
        local_files_only=True,
    )
    generator, info = model.transcribe(
        np.concatenate(samples),
        language="zh",
        word_timestamps=True,
        vad_filter=True,
        condition_on_previous_text=False,
        beam_size=5,
    )
    segments, last_start = [], -1
    for segment in generator:
        start, end = microseconds(segment.start), microseconds(segment.end)
        if start < last_start or end <= start or end > duration_us:
            raise ValueError("invalid segment range")
        last_start = start
        words = []
        for word in segment.words or []:
            wstart, wend = microseconds(word.start), microseconds(word.end)
            if wend <= wstart:
                continue  # punctuation remains in segment text
            if wstart < start or wend > end:
                raise ValueError("invalid word range")
            words.append({"text": word.word, "start_us": wstart, "end_us": wend})
        segments.append(
            {"text": segment.text, "start_us": start, "end_us": end, "words": words}
        )
    return {
        "kind": "actual_transcript",
        "text": "".join(s["text"] for s in segments),
        "segments": segments,
        "coordinate_system": "audio_intrinsic",
        "video_audio_offset_us": request["video_audio_offset_us"],
        "duration_us": duration_us,
        "language": info.language,
        "timestamp_method": "whisper_word_estimate_not_forced_alignment",
        "model_revision": request["model_revision"],
        "input_audio_sha256": request["audio_sha256"],
        "decoded_samples": decoded_samples,
        "sample_rate": rate,
    }


if __name__ == "__main__":
    try:
        result = transcribe(json.loads(sys.stdin.buffer.read(16_384)))
        sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
    except Exception:  # noqa: BLE001 - fixed failure at isolated process boundary; no raw diagnostics.
        sys.stdout.buffer.write(b'{"error_code":"offline_asr_worker_failed"}')
        raise SystemExit(1) from None
