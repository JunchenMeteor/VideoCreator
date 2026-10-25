"""Finite local experiment template; never model-authored filters or commands."""

from __future__ import annotations

import shutil
import tempfile
import threading
import time
from decimal import Decimal
from pathlib import Path

from video_creator.domain.errors import EngineError
from video_creator.media.ffmpeg import FFmpegRuntime


class LocalTemplateRenderer:
    """Render three actual template shots from one already-authorized audio asset."""

    def __init__(
        self,
        runtime: FFmpegRuntime,
        font: Path,
        cancel: threading.Event,
        deadline: float,
    ):
        self.runtime, self.font = runtime, font
        self.cancel, self.deadline = cancel, deadline

    def check(self):
        if self.cancel.is_set() or time.monotonic() >= self.deadline:
            raise EngineError(
                "worker_attempt_interrupted", "Local rendering attempt must stop.", 409
            )

    def _run(self, args, *, cwd=None):
        self.check()
        self.runtime._run(
            self.runtime.ffmpeg,
            args,
            cancel=self.cancel,
            timeout=min(90, max(0.01, self.deadline - time.monotonic())),
            cwd=cwd,
        )
        self.check()

    def render_shot(
        self,
        narration: Path,
        output: Path,
        *,
        index: int,
        revised: bool,
        width: int,
        height: int,
    ):
        if index not in (1, 2, 3) or (width, height) not in {(720, 1280), (1280, 720)}:
            raise EngineError(
                "local_template_denied", "Unsupported local template.", 422
            )
        self.check()
        output = self.runtime._path(output, exists=False)
        duration, start = ((4, 0), (3, 4), (3, 7))[index - 1]
        color = ("0x264653", "0x2a9d8f", "0xe9c46a")[index - 1]
        title = ("第一镜头：明确目标", "第二镜头：提供依据", "第三镜头：总结与行动")[
            index - 1
        ]
        if revised:
            if index != 3:
                raise EngineError(
                    "local_template_denied", "Only shot three may change.", 422
                )
            color, title = "0xff6b6b", "第三镜头：一起试试看！"
        with tempfile.TemporaryDirectory(
            prefix="LocalShot-", dir=self.runtime.staging_root
        ) as temp:
            root = Path(temp)
            audio, font, text = (
                root / "Narration.wav",
                root / "Font.otf",
                root / "Title.txt",
            )
            shutil.copyfile(narration, audio)
            shutil.copyfile(self.font, font)
            text.write_text("本地实验模板\n" + title, encoding="utf-8", newline="\n")
            self._run(
                [
                    "-nostdin",
                    "-v",
                    "error",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    f"color=c={color}:s={width}x{height}:r=25:d={duration}",
                    *self.runtime._input_args(self.runtime._input_format(audio)),
                    "-ss",
                    str(start),
                    "-i",
                    str(audio),
                    "-vf",
                    "drawtext=fontfile=Font.otf:textfile=Title.txt:fontcolor=white:fontsize=36:x=(w-text_w)/2:y=(h-text_h)/2",
                    "-af",
                    "apad",
                    "-map",
                    "0:v:0",
                    "-map",
                    "1:a:0",
                    "-t",
                    str(duration),
                    "-c:v",
                    "libx264",
                    "-preset",
                    "fast",
                    "-crf",
                    "22",
                    "-pix_fmt",
                    "yuv420p",
                    "-ar",
                    "48000",
                    "-ac",
                    "2",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "160k",
                    "-movflags",
                    "+faststart",
                    "-f",
                    "mp4",
                    str(output),
                ],
                cwd=root,
            )

    def compose(self, shots: tuple[Path, Path, Path], video: Path, mixed: Path):
        self.check()
        video, mixed = (
            self.runtime._path(video, exists=False),
            self.runtime._path(mixed, exists=False),
        )
        with tempfile.TemporaryDirectory(
            prefix="LocalCompose-", dir=self.runtime.staging_root
        ) as temp:
            root = Path(temp)
            args = ["-nostdin", "-v", "error", "-y"]
            for index, source in enumerate(shots, 1):
                local = root / f"Shot{index}.mp4"
                shutil.copyfile(source, local)
                args.extend(
                    [
                        *self.runtime._input_args(self.runtime._input_format(local)),
                        "-i",
                        str(local),
                    ]
                )
            args.extend(
                [
                    "-filter_complex",
                    "[0:v:0][0:a:0][1:v:0][1:a:0][2:v:0][2:a:0]concat=n=3:v=1:a=1[v][a]",
                    "-map",
                    "[v]",
                    "-map",
                    "[a]",
                    "-t",
                    "10",
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
                    "-f",
                    "mp4",
                    str(video),
                ]
            )
            self._run(args)
        self._run(
            [
                "-nostdin",
                "-v",
                "error",
                "-y",
                *self.runtime._input_args(self.runtime._input_format(video)),
                "-i",
                str(video),
                "-vn",
                "-map",
                "0:a:0",
                "-t",
                str(Decimal(10)),
                "-ar",
                "48000",
                "-ac",
                "2",
                "-c:a",
                "pcm_s16le",
                "-f",
                "wav",
                str(mixed),
            ]
        )
