"""Small deterministic FFmpeg boundary for independently decoded media.

The application supplies paths already resolved from staged assets. This layer
also limits every input/output to one staging directory and builds all command
arguments itself. A model never supplies filters, command strings, or switches.
"""

from __future__ import annotations

import json
import subprocess
import threading
import time
from decimal import Decimal
from pathlib import Path

from video_creator.domain.contracts import MediaProbe
from video_creator.domain.errors import EngineError


class FFmpegRuntime:
    def __init__(self, ffmpeg: Path, ffprobe: Path, staging_root: Path):
        self.ffmpeg = Path(ffmpeg).resolve(strict=True)
        self.ffprobe = Path(ffprobe).resolve(strict=True)
        self.staging_root = Path(staging_root).resolve(strict=True)
        self.version = self._run(self.ffmpeg, ["-version"]).splitlines()[0]

    def _path(self, path: Path, *, exists: bool = True) -> Path:
        candidate = Path(path).resolve(strict=exists)
        if not candidate.is_relative_to(self.staging_root):
            raise EngineError(
                "media_path_denied", "Media path is outside controlled staging.", 403
            )
        return candidate

    @staticmethod
    def _run(
        binary: Path,
        args: list[str],
        *,
        timeout: float = 90,
        cancel: threading.Event | None = None,
        cwd: Path | None = None,
    ) -> str:
        # Temporary capture files prevent pipes filling while cancellation polls.
        import tempfile

        with tempfile.TemporaryFile() as capture:
            process = subprocess.Popen(
                [str(binary), *args],
                stdin=subprocess.DEVNULL,
                stdout=capture,
                stderr=subprocess.STDOUT,
                shell=False,
                cwd=cwd,
            )
            deadline = time.monotonic() + timeout
            while process.poll() is None:
                if (
                    cancel is not None and cancel.is_set()
                ) or time.monotonic() > deadline:
                    process.terminate()
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                    reason = (
                        "cancelled"
                        if cancel is not None and cancel.is_set()
                        else "timeout"
                    )
                    raise EngineError(
                        "media_" + reason,
                        "Controlled media process " + reason + ".",
                        409,
                    )
                time.sleep(0.05)
            capture.seek(0)
            output = capture.read(128 * 1024).decode("utf-8", errors="replace")
        if process.returncode != 0:
            # No arbitrary user paths/command line are exposed in a public error.
            raise EngineError(
                "media_process_failed",
                "Media processing or independent decoding failed.",
                422,
            )
        return output

    def probe(self, path: Path, *, decode: bool = True) -> MediaProbe:
        path = self._path(path)
        if not path.is_file() or path.stat().st_size == 0:
            raise EngineError(
                "invalid_media", "Media file is empty or unavailable.", 422
            )
        raw = self._run(
            self.ffprobe,
            ["-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
        )
        try:
            info = json.loads(raw)
            streams = info["streams"]
            videos = [s for s in streams if s.get("codec_type") == "video"]
            audios = [s for s in streams if s.get("codec_type") == "audio"]
            duration = info.get("format", {}).get("duration")
            if duration is None:
                durations = [
                    Decimal(s["duration"])
                    for s in streams
                    if s.get("duration") is not None
                ]
                duration = max(durations) if durations else None
            duration_us = (
                int(Decimal(str(duration)) * 1_000_000)
                if duration is not None
                else None
            )
            if duration_us is None or duration_us <= 0 or not (videos or audios):
                raise ValueError("missing valid media duration/streams")
        except (KeyError, ValueError, TypeError, ArithmeticError):
            raise EngineError(
                "invalid_media", "Media has invalid duration or streams.", 422
            ) from None
        if decode:
            self._run(
                self.ffmpeg,
                [
                    "-nostdin",
                    "-v",
                    "error",
                    "-xerror",
                    "-i",
                    str(path),
                    "-map",
                    "0:v?",
                    "-map",
                    "0:a?",
                    "-f",
                    "null",
                    "-",
                ],
            )
        return MediaProbe(
            media_type="video/mp4" if videos else "audio/wav",
            duration_us=duration_us,
            has_video=bool(videos),
            has_audio=bool(audios),
            width=videos[0].get("width") if videos else None,
            height=videos[0].get("height") if videos else None,
            tool_version=self.version,
            decoded=decode,
        )

    def normalize_audio(
        self,
        source: Path,
        output: Path,
        *,
        duration_us: int,
        cancel: threading.Event | None = None,
    ) -> MediaProbe:
        source, output = self._path(source), self._path(output, exists=False)
        if duration_us <= 0 or duration_us > 60_000_000:
            raise EngineError(
                "duration_out_of_range",
                "Probe duration must be between zero and sixty seconds.",
                422,
            )
        self._run(
            self.ffmpeg,
            [
                "-nostdin",
                "-v",
                "error",
                "-y",
                "-i",
                str(source),
                "-vn",
                "-af",
                "apad",
                "-t",
                str(Decimal(duration_us) / 1_000_000),
                "-ar",
                "48000",
                "-ac",
                "1",
                "-c:a",
                "pcm_s16le",
                str(output),
            ],
            cancel=cancel,
        )
        return self.probe(output)

    def render_signal_probe(
        self,
        narration: Path,
        output: Path,
        mixed: Path,
        title_file: Path,
        font_file: Path,
        *,
        width: int,
        height: int,
        duration_us: int = 10_000_000,
        cancel: threading.Event | None = None,
    ) -> tuple[MediaProbe, MediaProbe]:
        if (width, height) not in {
            (720, 1280),
            (1280, 720),
            (1080, 1920),
            (1920, 1080),
        }:
            raise EngineError("canvas_denied", "Unsupported probe canvas.", 422)
        if duration_us != 10_000_000:
            raise EngineError(
                "duration_out_of_range",
                "Gate0 signal probe is exactly ten seconds.",
                422,
            )
        narration = self._path(narration)
        output, mixed = (
            self._path(output, exists=False),
            self._path(mixed, exists=False),
        )
        title_file = self._path(title_file)
        # Font is an installation resource, supplied by the integration role.
        font_file = Path(font_file).resolve(strict=True)
        duration = "10"
        self._run(
            self.ffmpeg,
            [
                "-nostdin",
                "-v",
                "error",
                "-y",
                "-i",
                str(narration),
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=220:sample_rate=48000:duration=10",
                "-filter_complex",
                "[1:a]volume=0.04[music];[0:a][music]amix=inputs=2:duration=longest:normalize=0[mix]",
                "-map",
                "[mix]",
                "-t",
                duration,
                "-ar",
                "48000",
                "-ac",
                "2",
                "-c:a",
                "pcm_s16le",
                str(mixed),
            ],
            cancel=cancel,
        )
        # Working directory removes drive-colon escaping for user-supplied text.
        # Only filenames generated by this layer are admitted into filter syntax.
        import shutil
        import tempfile

        with tempfile.TemporaryDirectory(
            prefix="VideoCreatorFont-", dir=self.staging_root
        ) as temp:
            font_local, title_local = Path(temp) / "Font.ttf", Path(temp) / "Title.txt"
            shutil.copyfile(font_file, font_local)
            shutil.copyfile(title_file, title_local)

            draw = (
                "drawtext=fontfile=Font.ttf:textfile=Title.txt:fontcolor=white:fontsize=40:"
                "x=(w-text_w)/2:y=(h-text_h)/2"
            )
            self._run(
                self.ffmpeg,
                [
                    "-nostdin",
                    "-v",
                    "error",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    f"testsrc2=size={width}x{height}:rate=25:duration=10",
                    "-i",
                    str(mixed),
                    "-vf",
                    draw,
                    "-map",
                    "0:v:0",
                    "-map",
                    "1:a:0",
                    "-t",
                    duration,
                    "-c:v",
                    "libx264",
                    "-preset",
                    "fast",
                    "-crf",
                    "22",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "160k",
                    "-movflags",
                    "+faststart",
                    str(output),
                ],
                cancel=cancel,
                cwd=Path(temp),
            )
        return self.probe(output), self.probe(mixed)
