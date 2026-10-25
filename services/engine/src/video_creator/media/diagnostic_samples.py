"""Bounded real decoder samples; source identity is not a semantic review."""
from __future__ import annotations

import hashlib
import tempfile
from decimal import Decimal
from pathlib import Path

from video_creator.domain import contracts as c
from video_creator.domain.component_diagnosis import DiagnosticSampleRefV1
from video_creator.domain.errors import EngineError
from video_creator.media.ffmpeg import FFmpegRuntime
from video_creator.providers.production_resources import file_sha256
from video_creator.workflows.attempt_control import current_attempt

FRAME_BYTES = 64 * 64 * 3
MAX_AUDIO_US = 2_000_000


def decode_sources(services, lease, inputs, resources, storage_root, decoder_ref):
    """Read registered bytes and independently decode every finite input source."""
    config = resources.section("edit", "ffmpeg")
    runtime = FFmpegRuntime(resources.resource(config["ffmpeg"]), resources.resource(config["ffprobe"]), storage_root)
    result = []
    with tempfile.TemporaryDirectory(prefix="ComponentSamples-", dir=storage_root) as temporary:
        root = Path(temporary)
        for index, source in enumerate(inputs.source_media_refs):
            current_attempt().check()
            asset = services.bundle.asset(lease, source.asset_id)
            path = services.bundle.content_path(lease, source.asset_id)
            if ((asset.sha256, asset.size, asset.media_type) != (source.sha256, source.size, source.media_type)
                    or path.stat().st_size != source.size or file_sha256(path) != source.sha256):
                raise EngineError("diagnostic_source_changed", "Actual registered source bytes must match the held original source.", 409)
            probe = runtime.probe(path, decode=True, timeout=current_attempt().remaining(30))
            if not probe.decoded or probe != source.probe or probe.media_type != source.media_type:
                raise EngineError("diagnostic_decode_invalid", "Source must retain its original complete decoder evidence.", 422)
            samples = []
            still = source.media_type.startswith("image/")
            channels = (("frame", probe.has_video or still), ("audio", probe.has_audio))
            for channel, available in channels:
                if not available:
                    continue
                duration = min(probe.duration_us or 40_000, MAX_AUDIO_US if channel == "audio" else 40_000)
                span = c.MediaRange(start_us=0, end_us=duration)
                output = root / (str(index) + "-" + channel + ".bin")
                argv = ["-nostdin", "-v", "error", "-y", *runtime._input_args(runtime._input_format(path)), "-i", str(path)]
                if channel == "frame":
                    argv += ["-map", "0:v:0", "-frames:v", "1", "-vf", "scale=64:64", "-pix_fmt", "rgb24", "-f", "rawvideo", str(output)]
                    limit = FRAME_BYTES
                else:
                    argv += ["-map", "0:a:0", "-t", format(Decimal(duration) / 1_000_000, "f"),
                             "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", "-f", "s16le", str(output)]
                    limit = 64_000
                runtime._run(runtime.ffmpeg, argv, timeout=current_attempt().remaining(30))
                if not output.is_file() or not 0 < output.stat().st_size <= limit:
                    raise EngineError("diagnostic_sample_invalid", "Actual decoder sample exceeds its fixed byte or time bound.", 422)
                raw = output.read_bytes()
                if channel == "frame" and len(raw) != FRAME_BYTES or channel == "audio" and len(raw) % 2:
                    raise EngineError("diagnostic_sample_invalid", "Actual RGB/PCM sample framing is incomplete.", 422)
                # Static images have no temporal range. Their actual decoded
                # RGB is bound by the source and Operation measurement, never a
                # fabricated 40ms image duration/sample interval.
                ref = None if still else DiagnosticSampleRefV1(format="component-diagnostic-decoded-sample-v1", asset_id=source.asset_id,
                    source_sha256=source.sha256, source_range=span, sample_sha256=hashlib.sha256(raw).hexdigest(),
                    sample_size=len(raw), decoder_ref=decoder_ref)
                samples.append((channel, ref, raw))
            if file_sha256(path) != source.sha256:
                raise EngineError("diagnostic_source_changed", "A source changed while its samples were decoded.", 409)
            result.append((source, probe, tuple(samples)))
    return tuple(result)


def frame_distance(left, right):
    """Explicit decoded RGB measurement, not an aesthetic/subject judgement."""
    if len(left) != FRAME_BYTES or len(right) != FRAME_BYTES:
        raise EngineError("diagnostic_sample_invalid", "Fixed complete RGB samples are required.", 422)
    return sum(abs(a - b) for a, b in zip(left, right, strict=True)) / FRAME_BYTES
