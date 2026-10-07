"""Admitted offline ASR in the installer-provisioned isolated interpreter."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

from video_creator.domain.contracts import ExecutionPermit, Money, OperationObservation
from video_creator.domain.errors import EngineError
from video_creator.infrastructure.credentials import SecretHandle

ASR_DESTINATION = "local:faster-whisper-small-cpu-int8"


class LocalAsrDriver:
    def __init__(
        self,
        audio_path: Path,
        *,
        storage_root: Path,
        model_dir: Path,
        python_executable: Path,
        model_revision: str,
        expected_audio_sha256: str,
        video_audio_offset_us: int = 0,
        max_audio_duration_us: int = 60_000_000,
    ):
        audio, root, model, python = map(
            Path, (audio_path, storage_root, model_dir, python_executable)
        )
        if (
            audio.is_symlink()
            or not audio.is_file()
            or not audio.resolve().is_relative_to(root.resolve())
            or model.is_symlink()
            or not model.is_dir()
            or python.is_symlink()
            or not python.is_file()
            or type(video_audio_offset_us) is not int
            or video_audio_offset_us < 0
            or type(max_audio_duration_us) is not int
            or not 0 < max_audio_duration_us <= 600_000_000
        ):
            raise EngineError(
                "asr_input_denied", "Offline ASR inputs are unavailable.", 403
            )
        self._python = python.resolve()
        self._audio, self._sha = audio, expected_audio_sha256
        self._request = {
            "audio_path": str(audio.resolve()),
            "storage_root": str(root.resolve()),
            "model_dir": str(model.resolve()),
            "model_revision": model_revision,
            "audio_sha256": expected_audio_sha256,
            "video_audio_offset_us": video_audio_offset_us,
            "max_audio_duration_us": max_audio_duration_us,
        }

    def __call__(
        self, permit: ExecutionPermit, secret: SecretHandle | None
    ) -> OperationObservation:
        if (
            permit.route.destination != ASR_DESTINATION
            or permit.route.capability != "transcription"
            or permit.route.source != "owned_local"
            or secret is not None
        ):
            raise EngineError(
                "asr_route_denied", "Only admitted offline ASR is supported.", 403
            )
        if hashlib.sha256(self._audio.read_bytes()).hexdigest() != self._sha:
            raise EngineError(
                "asr_audio_changed", "Audio changed before transcription.", 422
            )
        environment = {
            name: os.environ[name]
            for name in ("PATH", "SYSTEMROOT", "TEMP", "TMP")
            if name in os.environ
        }
        environment.update(
            {
                "PYTHONPATH": str(Path(__file__).parents[2]),
                "HF_HUB_OFFLINE": "1",
                "TRANSFORMERS_OFFLINE": "1",
            }
        )
        # Fixed module/interpreter; input fields cannot become shell or argv code.
        completed = subprocess.run(
            [str(self._python), "-X", "utf8", "-m", "video_creator.media.asr_worker"],
            input=json.dumps(self._request).encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=environment,
            shell=False,
            timeout=120,
            check=False,
        )
        if completed.returncode != 0 or len(completed.stdout) > 2 * 1024 * 1024:
            return OperationObservation(
                status="failed",
                actual_cost=Money(amount="0"),
                cost_evidence="confirmed_no_charge",
                result_json={"error_code": "offline_asr_worker_failed"},
            )
        result = json.loads(completed.stdout)
        if (
            not isinstance(result, dict)
            or result.get("kind") != "actual_transcript"
            or result.get("input_audio_sha256") != self._sha
        ):
            raise EngineError(
                "asr_result_invalid", "Offline ASR response is invalid.", 422
            )
        return OperationObservation(
            status="succeeded",
            actual_cost=Money(amount="0"),
            cost_evidence="confirmed_no_charge",
            result_json=result,
        )
