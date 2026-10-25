"""Small deterministic FFmpeg boundary for independently decoded media.

The application supplies paths already resolved from staged assets. This layer
also limits every input/output to one staging directory and builds all command
arguments itself. A model never supplies filters, command strings, or switches.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from decimal import Decimal
from pathlib import Path

from video_creator.domain.contracts import MediaProbe
from video_creator.domain.errors import EngineError
from video_creator.providers.local_asr import AsrProcessError, _ProcessTree
from video_creator.workflows.attempt_control import current_attempt


class FFmpegRuntime:
    MAX_INPUT_BYTES = 256 * 1024 * 1024
    MAX_PIXELS = 16 * 1024 * 1024
    MAX_SIDE = 8192
    MAX_STREAMS = 8
    MAX_DURATION_US = 7_200_000_000
    MP4_BRANDS = frozenset(
        {
            b"isom",
            b"iso2",
            b"iso6",
            b"mp41",
            b"mp42",
            b"avc1",
            b"M4A ",
            b"dash",
        }
    )

    def __init__(self, ffmpeg: Path, ffprobe: Path, staging_root: Path):
        self.ffmpeg = Path(ffmpeg).resolve(strict=True)
        self.ffprobe = Path(ffprobe).resolve(strict=True)
        self.staging_root = Path(staging_root).resolve(strict=True)
        self.version = self._run(self.ffmpeg, ["-version"]).splitlines()[0]

    def _path(self, path: Path, *, exists: bool = True) -> Path:
        candidate = Path(path).resolve(strict=exists)
        if str(candidate).startswith(("\\\\", "//")) or not candidate.is_relative_to(
            self.staging_root
        ):
            raise EngineError(
                "media_path_denied", "Media path is outside controlled staging.", 403
            )
        return candidate

    @classmethod
    def _dimensions(cls, width, height):
        if (
            not isinstance(width, int)
            or not isinstance(height, int)
            or min(width, height) <= 0
        ):
            raise EngineError("invalid_media", "Media dimensions are unavailable.", 422)
        if max(width, height) > cls.MAX_SIDE or width * height > cls.MAX_PIXELS:
            raise EngineError(
                "media_resource_limit",
                "Media dimensions exceed the supported limit.",
                422,
            )

    @classmethod
    def _png_boundary(cls, path: Path, header: bytes):
        if header[8:16] != b"\x00\x00\x00\x0dIHDR" or len(header) < 24:
            raise EngineError("invalid_media", "PNG header is invalid.", 422)
        cls._dimensions(
            int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big")
        )
        # Walk framing only, never decompress here. Disallow animation and
        # concatenated documents before the external parser sees the input.
        size, position, chunks = path.stat().st_size, 8, 0
        with path.open("rb") as source:
            while position < size and chunks < 4096:
                source.seek(position)
                box = source.read(8)
                if len(box) != 8:
                    break
                length, kind = int.from_bytes(box[:4], "big"), box[4:]
                position += length + 12
                chunks += 1
                if position > size:
                    break
                if kind == b"acTL":
                    raise EngineError(
                        "media_format_denied", "Animated PNG is not supported.", 415
                    )
                if kind == b"IEND" and length == 0 and position == size:
                    return
        raise EngineError(
            "invalid_media", "PNG framing is invalid or exceeds limits.", 422
        )

    @classmethod
    def _mp4_boundary(cls, path: Path):
        # ISO BMFF track references are a separate boundary from the file-only
        # protocol. Admit only self-contained url entries in dref tables.
        containers = {b"moov", b"trak", b"mdia", b"minf", b"dinf"}
        count, references = 0, 0
        with path.open("rb") as source:

            def walk(start, end, depth):
                nonlocal count, references
                if depth > 8:
                    raise ValueError("box nesting")
                position = start
                while position < end:
                    source.seek(position)
                    header = source.read(8)
                    if len(header) != 8:
                        raise ValueError("box header")
                    length, kind = int.from_bytes(header[:4], "big"), header[4:]
                    header_size = 8
                    if length == 1:
                        extended = source.read(8)
                        if len(extended) != 8:
                            raise ValueError("extended box")
                        length, header_size = int.from_bytes(extended, "big"), 16
                    elif length == 0:
                        length = end - position
                    count += 1
                    if length < header_size or position + length > end or count > 65536:
                        raise ValueError("box size")
                    payload, box_end = position + header_size, position + length
                    if kind in containers:
                        walk(payload, box_end, depth + 1)
                    elif kind == b"dref":
                        source.seek(payload)
                        full = source.read(8)
                        if len(full) != 8 or full[:4] != b"\x00" * 4:
                            raise ValueError("reference table")
                        entries = int.from_bytes(full[4:], "big")
                        if not 1 <= entries <= cls.MAX_STREAMS:
                            raise ValueError("reference count")
                        cursor = payload + 8
                        for _ in range(entries):
                            source.seek(cursor)
                            entry = source.read(12)
                            if entry != b"\x00\x00\x00\x0curl \x00\x00\x00\x01":
                                raise EngineError(
                                    "media_reference_denied",
                                    "External or unsupported media references are denied.",
                                    415,
                                )
                            cursor += 12
                            references += 1
                        if cursor != box_end:
                            raise ValueError("reference table size")
                    position = box_end

            try:
                walk(0, path.stat().st_size, 0)
                if references == 0:
                    raise ValueError("self-contained track references missing")
            except ValueError:
                raise EngineError(
                    "invalid_media", "MP4 framing is invalid or unsupported.", 422
                ) from None

    @classmethod
    def _input_format(cls, path: Path) -> str:
        size = path.stat().st_size
        if not path.is_file() or size <= 0:
            raise EngineError(
                "invalid_media", "Media file is empty or unavailable.", 422
            )
        if size > cls.MAX_INPUT_BYTES:
            raise EngineError(
                "media_resource_limit", "Media input exceeds the supported size.", 422
            )
        with path.open("rb") as source:
            header = source.read(32)
            if header.startswith(b"\x89PNG\r\n\x1a\n"):
                cls._png_boundary(path, header)
                return "png_pipe"
            if header.startswith(b"\xff\xd8\xff"):
                source.seek(-2, 2)
                if source.read(2) != b"\xff\xd9":
                    raise EngineError("invalid_media", "JPEG framing is invalid.", 422)
                return "jpeg_pipe"
            if header[:4] == b"RIFF" and header[8:12] == b"WAVE":
                return "wav"
            if header[4:8] == b"ftyp" and header[8:12] in cls.MP4_BRANDS:
                cls._mp4_boundary(path)
                return "mov"
        # This rejects HLS/concat/XML and unsupported containers before Popen.
        # File extensions and requested Content-Type never select the parser.
        raise EngineError(
            "media_process_failed",
            "Media content is invalid, unsupported, or not self-contained.",
            422,
        )

    @classmethod
    def _input_args(cls, input_format: str) -> list[str]:
        args = [
            "-max_alloc",
            "67108864",
            "-protocol_whitelist",
            "file",
            "-format_whitelist",
            input_format,
            "-max_streams",
            str(cls.MAX_STREAMS),
            "-max_pixels",
            str(cls.MAX_PIXELS),
            "-threads",
            "1",
            "-f",
            input_format,
        ]
        if input_format == "mov":
            args.extend(
                [
                    "-enable_drefs",
                    "0",
                    "-use_absolute_path",
                    "0",
                    "-ignore_chapters",
                    "1",
                ]
            )
        return args

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

        control = current_attempt()
        control.check()
        with tempfile.TemporaryFile() as capture:
            process = subprocess.Popen(
                [str(binary), *args],
                stdin=subprocess.DEVNULL,
                stdout=capture,
                stderr=subprocess.STDOUT,
                shell=False,
                cwd=cwd,
                start_new_session=os.name != "nt",
            )
            tree, empty = None, False
            try:
                tree = _ProcessTree(process)
                deadline = time.monotonic() + control.remaining(timeout)
                while process.poll() is None:
                    control.check()
                    if cancel is not None and cancel.is_set():
                        raise EngineError("media_cancelled", "Controlled media process cancelled.", 409)
                    if time.monotonic() >= deadline:
                        raise EngineError("media_timeout", "Controlled media process timeout.", 409)
                    if capture.tell() > 128 * 1024:
                        raise EngineError("media_output_limit", "Controlled media output exceeds its bound.", 503)
                    time.sleep(0.02)
            except AsrProcessError:
                raise EngineError("media_cleanup_failed", "Controlled media process ownership is unavailable.", 503, "reconcile") from None
            finally:
                try:
                    empty = tree.close() if tree is not None else False
                except (OSError, AsrProcessError):
                    empty = False
                if process.poll() is None:
                    try:
                        process.kill()
                    except OSError:
                        pass
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    empty = False
                if not empty or process.poll() is None:
                    raise EngineError("media_cleanup_failed", "Controlled media descendants have not all terminated.", 503, "reconcile")
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

    def probe(
        self,
        path: Path,
        *,
        decode: bool = True,
        cancel: threading.Event | None = None,
        timeout: float | None = None,
    ) -> MediaProbe:
        # Explicit timeout bounds the WHOLE probe, including both processes.
        # Without it, preserve the previous 90-second bound per process.
        deadline = time.monotonic() + timeout if timeout is not None else None

        def remaining():
            if cancel is not None and cancel.is_set():
                raise EngineError(
                    "media_cancelled", "Controlled media probe cancelled.", 409
                )
            value = 90 if deadline is None else deadline - time.monotonic()
            if value <= 0:
                raise EngineError(
                    "media_timeout", "Controlled media probe timeout.", 409
                )
            return value

        remaining()
        path = self._path(path)
        input_format = self._input_format(path)
        image = input_format in {"png_pipe", "jpeg_pipe"}
        inputs = self._input_args(input_format)
        raw = self._run(
            self.ffprobe,
            [
                "-v",
                "error",
                *inputs,
                *(["-count_frames"] if image else []),
                "-show_format",
                "-show_streams",
                "-of",
                "json",
                str(path),
            ],
            cancel=cancel,
            timeout=remaining(),
        )
        try:
            info = json.loads(raw)
            streams = info["streams"]
            videos = [s for s in streams if s.get("codec_type") == "video"]
            audios = [s for s in streams if s.get("codec_type") == "audio"]
            formats = info["format"]["format_name"].split(",")
            if (
                input_format not in formats
                or not streams
                or len(streams) > self.MAX_STREAMS
            ):
                raise ValueError("invalid supported format or stream count")
            if any(s.get("codec_type") not in {"video", "audio"} for s in streams):
                raise ValueError("unsupported stream")
            for video in videos:
                self._dimensions(video.get("width"), video.get("height"))
            if image:
                if (
                    len(videos) != 1
                    or audios
                    or int(videos[0].get("nb_read_frames", 0)) != 1
                ):
                    raise ValueError("one static image required")
                codec = "png" if input_format == "png_pipe" else "mjpeg"
                if videos[0].get("codec_name") != codec:
                    raise ValueError("invalid image codec")
                media_type = "image/png" if input_format == "png_pipe" else "image/jpeg"
            elif input_format == "wav":
                pcm = {
                    "pcm_u8",
                    "pcm_s16le",
                    "pcm_s24le",
                    "pcm_s32le",
                    "pcm_f32le",
                    "pcm_f64le",
                }
                if (
                    videos
                    or not audios
                    or any(a.get("codec_name") not in pcm for a in audios)
                ):
                    raise ValueError("supported PCM WAVE required")
                media_type = "audio/wav"
            else:
                if any(
                    v.get("codec_name") not in {"h264", "hevc", "av1", "mpeg4"}
                    for v in videos
                ):
                    raise ValueError("unsupported MP4 video codec")
                if any(
                    a.get("codec_name") not in {"aac", "alac", "opus", "mp3"}
                    for a in audios
                ):
                    raise ValueError("unsupported MP4 audio codec")
                media_type = "video/mp4" if videos else "audio/mp4"
            duration = None if image else info.get("format", {}).get("duration")
            if duration is None:
                durations = [
                    Decimal(s["duration"])
                    for s in streams
                    if s.get("duration") is not None
                ]
                duration = max(durations) if durations and not image else None
            duration_us = (
                int(Decimal(str(duration)) * 1_000_000)
                if duration is not None
                else None
            )
            if not image and (
                duration_us is None
                or duration_us <= 0
                or duration_us > self.MAX_DURATION_US
                or not (videos or audios)
            ):
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
                    *inputs,
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
                cancel=cancel,
                timeout=remaining(),
            )
        remaining()
        return MediaProbe(
            media_type=media_type,
            duration_us=duration_us,
            has_video=bool(videos) and not image,
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
                *self._input_args(self._input_format(source)),
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
                *self._input_args(self._input_format(narration)),
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
                    *self._input_args(self._input_format(mixed)),
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
