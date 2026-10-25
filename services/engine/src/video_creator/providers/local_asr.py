"""Admitted offline ASR with an isolated, bounded process-tree protocol."""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import signal
import subprocess
import tempfile
import threading
import time
from collections.abc import Callable
from fractions import Fraction
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from video_creator.domain.contracts import ExecutionPermit, OperationObservation
    from video_creator.infrastructure.credentials import SecretHandle

ASR_DESTINATION = "local:faster-whisper-small-cpu-int8"
MODEL_FILES = ("config.json", "model.bin", "tokenizer.json", "vocabulary.txt")
MAX_OUTPUT_BYTES = 2 * 1024 * 1024
MAX_STDERR_BYTES = 64 * 1024


class AsrProcessError(RuntimeError):
    def __init__(self, code: str, evidence: dict | None = None, stderr: bytes = b""):
        super().__init__(code)
        self.code, self.evidence, self.stderr = code, evidence or {}, stderr


def model_file_hashes(model_dir: Path) -> dict[str, str]:
    root = Path(model_dir)
    if root.is_symlink() or not root.is_dir():
        raise AsrProcessError("asr_model_unavailable")
    result = {}
    for name in MODEL_FILES:
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise AsrProcessError("asr_model_unavailable")
        result[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


class _ProcessTree:
    def __init__(self, process: subprocess.Popen):
        self.process, self.job, self.kernel = process, None, None
        if os.name != "nt":
            return
        import ctypes
        from ctypes import wintypes

        class Basic(ctypes.Structure):
            _fields_ = [("ProcessTime", ctypes.c_int64), ("JobTime", ctypes.c_int64),
                        ("Flags", wintypes.DWORD), ("MinWorkingSet", ctypes.c_size_t),
                        ("MaxWorkingSet", ctypes.c_size_t), ("ActiveLimit", wintypes.DWORD),
                        ("Affinity", ctypes.c_size_t), ("Priority", wintypes.DWORD),
                        ("Scheduling", wintypes.DWORD)]

        class Io(ctypes.Structure):
            _fields_ = [(name, ctypes.c_uint64) for name in ("ReadOps", "WriteOps", "OtherOps", "ReadBytes", "WriteBytes", "OtherBytes")]

        class Extended(ctypes.Structure):
            _fields_ = [("Basic", Basic), ("Io", Io), ("ProcessMemory", ctypes.c_size_t),
                        ("JobMemory", ctypes.c_size_t), ("PeakProcess", ctypes.c_size_t),
                        ("PeakJob", ctypes.c_size_t)]

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        signatures = {
            "CreateJobObjectW": ([ctypes.c_void_p, wintypes.LPCWSTR], wintypes.HANDLE),
            "SetInformationJobObject": ([wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD], wintypes.BOOL),
            "AssignProcessToJobObject": ([wintypes.HANDLE, wintypes.HANDLE], wintypes.BOOL),
            "TerminateJobObject": ([wintypes.HANDLE, wintypes.UINT], wintypes.BOOL),
            "QueryInformationJobObject": ([wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p], wintypes.BOOL),
            "CloseHandle": ([wintypes.HANDLE], wintypes.BOOL),
        }
        for name, (arguments, result) in signatures.items():
            getattr(kernel, name).argtypes, getattr(kernel, name).restype = arguments, result
        job, limits = kernel.CreateJobObjectW(None, None), Extended()
        limits.Basic.Flags = 0x2000  # KILL_ON_JOB_CLOSE, no breakaway.
        if not job or not kernel.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            if job:
                kernel.CloseHandle(job)
            raise AsrProcessError("asr_process_containment_failed")
        if not kernel.AssignProcessToJobObject(job, wintypes.HANDLE(int(process._handle))):
            kernel.CloseHandle(job)
            raise AsrProcessError("asr_process_containment_failed")
        self.job, self.kernel = job, kernel

    def close(self) -> bool:
        expires = time.monotonic() + 5
        if self.job is not None:
            import ctypes
            import struct

            try:
                if not self.kernel.TerminateJobObject(self.job, 1):
                    return False
                while time.monotonic() < expires:
                    accounting = ctypes.create_string_buffer(48)
                    if not self.kernel.QueryInformationJobObject(self.job, 1, accounting, 48, None):
                        return False
                    if struct.unpack_from("I", accounting.raw, 40)[0] == 0:
                        return True
                    time.sleep(0.01)
                return False
            finally:
                self.kernel.CloseHandle(self.job)
                self.job = None
        try:
            os.killpg(self.process.pid, signal.SIGKILL)
            while time.monotonic() < expires:
                self.process.poll()
                try:
                    os.killpg(self.process.pid, 0)
                except ProcessLookupError:
                    return True
                time.sleep(0.01)
            return False
        except ProcessLookupError:
            return True


class _Stream:
    def __init__(self, stream, limit):
        self.stream, self.limit = stream, limit
        self.content, self.total, self.digest = bytearray(), 0, hashlib.sha256()
        self.exceeded = threading.Event()
        self.failed = threading.Event()
        self.thread = threading.Thread(target=self._read, daemon=True)
        self.thread.start()

    def _read(self):
        try:
            while chunk := self.stream.read(8192):
                self.total += len(chunk)
                self.digest.update(chunk)
                self.content.extend(chunk[:max(0, self.limit - len(self.content))])
                if self.total > self.limit:
                    self.exceeded.set()
        except (OSError, ValueError):
            self.failed.set()
        finally:
            self.stream.close()


def _unique_object(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError("duplicate JSON field")
        result[name] = value
    return result


def _nonfinite(_value):
    raise ValueError("nonfinite JSON")


def _rational_us(value: Fraction) -> int:
    value *= 1_000_000
    sign = -1 if value < 0 else 1
    return sign * ((2 * abs(value.numerator) + value.denominator) // (2 * value.denominator))


def _time_base(value: dict) -> Fraction:
    if (type(value) is not dict or set(value) != {"numerator", "denominator"}
        or type(value["numerator"]) is not int or type(value["denominator"]) is not int
        or value["numerator"] <= 0 or value["denominator"] <= 0):
        raise ValueError("invalid time base")
    return Fraction(value["numerator"], value["denominator"])


def validate_asr_result(result: dict, request: dict) -> None:
    if (type(result) is not dict or result.get("protocol_version") != "local-asr-v2"
        or result.get("kind") != "actual_transcript" or result.get("input_audio_sha256") != request["audio_sha256"]
        or result.get("model_revision") != request["model_revision"] or result.get("coordinate_system") != "audio_intrinsic"
        or result.get("timestamp_method") != "whisper_word_estimate_not_forced_alignment"
        or type(result.get("language")) is not str or not re.fullmatch(r"[a-z]{2,3}", result["language"])
        or type(result.get("text")) is not str or not result["text"].strip()
        or type(result.get("segments")) is not list or not 0 < len(result["segments"]) <= 10_000
        or type(result.get("duration_us")) is not int or not 0 < result["duration_us"] <= request["max_audio_duration_us"]):
        raise ValueError("invalid transcript envelope")
    previous_end, texts = 0, []
    for segment in result["segments"]:
        if (type(segment) is not dict or type(segment.get("text")) is not str or not segment["text"].strip()
            or type(segment.get("words")) is not list or type(segment.get("start_us")) is not int
            or type(segment.get("end_us")) is not int or not previous_end <= segment["start_us"] < segment["end_us"] <= result["duration_us"]):
            raise ValueError("invalid segment")
        previous_end, word_end = segment["end_us"], segment["start_us"]
        for word in segment["words"]:
            if (type(word) is not dict or type(word.get("text")) is not str or not word["text"].strip()
                or type(word.get("start_us")) is not int or type(word.get("end_us")) is not int
                or not word_end <= word["start_us"] < word["end_us"] <= segment["end_us"]):
                raise ValueError("invalid word")
            word_end = word["end_us"]
        texts.append(segment["text"])
    if result["text"] != "".join(texts):
        raise ValueError("text and segments differ")
    runtime, audio = result.get("runtime"), result.get("audio_provenance")
    if (type(runtime) is not dict or runtime.get("device") != "cpu" or runtime.get("requested_compute_type") != "int8"
        or runtime.get("actual_compute_type") not in {"int8", "int8_float32", "float32"}
        or runtime.get("model_file_sha256") != request["model_file_sha256"] or type(runtime.get("versions")) is not dict
        or any(type(runtime["versions"].get(name)) is not str or not runtime["versions"][name] for name in
               ("python", "faster-whisper", "ctranslate2", "av", "numpy", "onnxruntime", "tokenizers"))
        or type(audio) is not dict or audio.get("pts_continuity") != "verified_exact"
        or audio.get("duration_rounding") != "round_half_up_exact_samples_over_rate"
        or type(result.get("decoded_samples")) is not int or result["decoded_samples"] <= 0
        or type(result.get("sample_rate")) is not int or result["sample_rate"] <= 0
        or audio.get("source_decoded_samples") != result["decoded_samples"] or audio.get("source_sample_rate") != result["sample_rate"]
        or audio.get("intrinsic_duration_us") != result["duration_us"]
        or type(result.get("video_audio_offset_us")) is not int or result["video_audio_offset_us"] != audio.get("observed_audio_video_offset_us")):
        raise ValueError("invalid resource/time provenance")
    if any(not re.fullmatch(r"[0-9]+(?:\.[0-9]+){1,3}(?:[a-zA-Z0-9.+-]*)", version)
           for version in runtime["versions"].values()):
        raise ValueError("invalid runtime version")
    identity = runtime.get("execution_identity")
    if request.get("require_execution_identity") is True or identity is not None:
        configuration = runtime.get("execution_configuration")
        if (type(identity) is not dict or type(configuration) is not dict
            or identity.get("method_id") != "faster-whisper-small-word-estimate-v1"
            or identity.get("tool") != "faster-whisper" or identity.get("model_id") != "faster-whisper-small"
            or identity.get("tool_version") != runtime["versions"]["faster-whisper"]
            or identity.get("model_file_sha256") != runtime["model_file_sha256"]
            or identity.get("compute_type") != runtime["actual_compute_type"] or identity.get("device") != runtime["device"]
            or any(type(identity.get(name)) is not str or not identity[name] for name in ("operating_system", "architecture"))
            or identity.get("resource_manifest_sha256") != request.get("resource_manifest_sha256")
            or identity.get("configuration_sha256") != hashlib.sha256(json.dumps(configuration, ensure_ascii=False,
                    sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
            or configuration.get("actual_device") != runtime["device"]
            or configuration.get("actual_compute_type") != runtime["actual_compute_type"]
            or configuration.get("versions") != runtime["versions"]):
            raise ValueError("invalid actual execution identity")
    for name in ("audio_stream_index", "decoded_frame_count", "first_frame_pts", "last_frame_pts",
                 "container_audio_start_us", "resampled_sample_rate", "resampled_samples", "observed_audio_video_offset_us"):
        if type(audio.get(name)) is not int:
            raise ValueError("invalid audio provenance integer")
    if (audio["audio_stream_index"] < 0 or audio["decoded_frame_count"] <= 0
        or audio["resampled_sample_rate"] != 16_000 or audio["resampled_samples"] <= 0
        or type(audio.get("container_format")) is not str or not audio["container_format"]
        or type(audio.get("audio_codec")) is not str or not audio["audio_codec"]
        or audio.get("request_offset_used") is not False):
        raise ValueError("invalid decoded audio provenance")
    duration = Fraction(result["decoded_samples"], result["sample_rate"])
    if result["duration_us"] != _rational_us(duration):
        raise ValueError("sample duration does not match")
    base = _time_base(audio["first_frame_time_base"])
    first = audio["first_frame_pts"] * base
    if audio["container_audio_start_us"] != _rational_us(first):
        raise ValueError("audio origin does not match")
    if not first <= audio["last_frame_pts"] * base < first + duration:
        raise ValueError("last frame is outside the decoded interval")
    if audio.get("offset_basis") == "not_applicable_audio_only":
        if any(audio.get(name) is not None for name in ("first_video_frame_pts", "first_video_frame_time_base", "container_video_start_us")):
            raise ValueError("unexpected video origin")
        offset = 0
    elif audio.get("offset_basis") == "first_decoded_audio_minus_first_decoded_video_pts":
        if type(audio.get("first_video_frame_pts")) is not int or type(audio.get("container_video_start_us")) is not int:
            raise ValueError("invalid video origin")
        video = audio["first_video_frame_pts"] * _time_base(audio["first_video_frame_time_base"])
        if audio["container_video_start_us"] != _rational_us(video):
            raise ValueError("video origin does not match")
        offset = _rational_us(first - video)
    else:
        raise ValueError("unknown offset basis")
    if result["video_audio_offset_us"] != offset:
        raise ValueError("offset does not match actual origins")


def _cancel_requested(cancel: Callable[[], bool] | None) -> bool:
    if cancel is None:
        return False
    try:
        value = cancel()
        if type(value) is not bool:
            raise ValueError("invalid control")
        return value
    except Exception:  # noqa: BLE001 - original trusted-control fault is sanitized and still raises.
        raise AsrProcessError("asr_control_invalid") from None


def run_local_asr(request: dict, *, python_executable: Path, runtime_root: Path,
                  timeout_seconds: float = 120, deadline_monotonic: float | None = None,
                  cancel: Callable[[], bool] | None = None) -> dict:
    """Private protocol: fixed script, no backend/vault import or arbitrary argv."""
    if (type(timeout_seconds) not in (int, float) or not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= 600
        or deadline_monotonic is not None and (type(deadline_monotonic) not in (int, float) or not math.isfinite(deadline_monotonic))):
        raise AsrProcessError("asr_control_invalid")
    began = time.monotonic()
    deadline = min(began + timeout_seconds, deadline_monotonic if deadline_monotonic is not None else math.inf)
    if _cancel_requested(cancel):
        raise AsrProcessError("asr_cancelled", {"phase": "before_launch"})
    if deadline <= began:
        raise AsrProcessError("asr_deadline_exceeded", {"phase": "before_launch"})
    root, python = Path(runtime_root), Path(python_executable)
    if root.is_symlink() or not root.is_dir() or python.is_symlink() or not python.is_file():
        raise AsrProcessError("asr_runtime_unavailable")
    worker = Path(__file__).parents[1] / "media/asr_worker.py"
    evidence = {"worker_sha256": hashlib.sha256(worker.read_bytes()).hexdigest(), "python_sha256": hashlib.sha256(python.read_bytes()).hexdigest(), "deadline_monotonic": deadline, "timeout_seconds": timeout_seconds, "tree_containment": "windows_job_kill_on_close" if os.name == "nt" else "posix_process_group", "stdin_bytes": 0}
    with tempfile.TemporaryDirectory(prefix="Asr-", dir=root.resolve()) as temporary:
        runtime = Path(temporary)
        payload = dict(request, runtime_root=str(runtime))
        encoded = json.dumps(payload, allow_nan=False).encode("utf-8")
        if len(encoded) > 16_384:
            raise AsrProcessError("asr_input_too_large")
        environment = {name: os.environ[name] for name in ("SYSTEMROOT", "TEMP", "TMP") if name in os.environ}
        environment.update(PATH=str(python.resolve().parent), HF_HOME=str(runtime / "HuggingFace"), HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_IMPLICIT_TOKEN="1")
        argv = [str(python.resolve()), "-I", "-B", "-X", "utf8", str(worker.resolve())]
        evidence["argv"] = argv
        process, tree, streams, writer = None, None, None, None
        reason, write_failed = None, threading.Event()
        try:
            process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=runtime, env=environment, shell=False, start_new_session=os.name != "nt")
            evidence["pid"] = process.pid
            tree = _ProcessTree(process)  # Worker waits for stdin; containment precedes input.
            stdout, stderr = _Stream(process.stdout, MAX_OUTPUT_BYTES), _Stream(process.stderr, MAX_STDERR_BYTES)
            streams = stdout, stderr

            def send_input():
                try:
                    process.stdin.write(encoded)
                    process.stdin.close()
                    evidence["stdin_bytes"] = len(encoded)
                except OSError:
                    write_failed.set()

            writer = threading.Thread(target=send_input, daemon=True)
            writer.start()
            while process.poll() is None:
                if stdout.exceeded.is_set() or stderr.exceeded.is_set():
                    reason = "asr_output_too_large"
                elif write_failed.is_set() or stdout.failed.is_set() or stderr.failed.is_set():
                    reason = "asr_process_failed"
                elif _cancel_requested(cancel):
                    reason = "asr_cancelled"
                elif time.monotonic() >= deadline:
                    reason = "asr_deadline_exceeded"
                if reason is not None:
                    break
                time.sleep(min(0.02, max(0, deadline - time.monotonic())))
        except AsrProcessError as error:
            reason = error.code
        except (OSError, ValueError, TypeError):
            reason = "asr_process_failed"
        finally:
            if tree is not None:
                evidence["tree_empty"] = tree.close()
                if not evidence["tree_empty"]:
                    reason = "asr_cleanup_failed"
            if process is not None:
                if process.poll() is None:
                    process.kill()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    reason = "asr_cleanup_failed"
                if writer is not None:
                    writer.join(timeout=5)
                if writer is not None and writer.is_alive():
                    reason = "asr_cleanup_failed"
                if process.stdin is not None and not process.stdin.closed:
                    process.stdin.close()
                evidence.update(return_code=process.returncode, child_terminal=process.poll() is not None)
            if streams is not None:
                for stream in streams:
                    stream.thread.join(timeout=5)
                if any(stream.thread.is_alive() for stream in streams):
                    reason = "asr_cleanup_failed"
                evidence.update(stdout_bytes=stdout.total, stdout_sha256=stdout.digest.hexdigest(), stderr_bytes=stderr.total, stderr_sha256=stderr.digest.hexdigest(), stderr_truncated=stderr.total > MAX_STDERR_BYTES)
                if stderr.total:
                    diagnostics = root.resolve() / "Diagnostics"
                    if diagnostics.is_symlink():
                        reason = "asr_cleanup_failed"
                    else:
                        diagnostics.mkdir(exist_ok=True)
                        with tempfile.NamedTemporaryFile(prefix="Asr-", suffix=".stderr", dir=diagnostics, delete=False) as diagnostic:
                            diagnostic.write(stderr.content)
                            evidence["stderr_artifact"] = diagnostic.name
            progress = runtime / "Progress.jsonl"
            evidence["progress"] = []
            if progress.is_file() and progress.stat().st_size <= 8192:
                for line in progress.read_text(encoding="utf-8").splitlines():
                    try:
                        event = json.loads(line)
                        if type(event) is not dict or type(event.get("stage")) is not str:
                            raise ValueError("invalid progress")
                        evidence["progress"].append(event)
                    except (ValueError, TypeError):
                        evidence["progress_parse_error"] = True
            evidence["wall_seconds"] = time.monotonic() - began
        if reason is not None:
            raise AsrProcessError(reason, evidence, bytes(stderr.content) if streams else b"")
        if streams is None or process.returncode != 0:
            code = "offline_asr_worker_failed"
            if streams is not None:
                try:
                    error = json.loads(stdout.content)
                    allowed = {"asr_input_invalid", "asr_audio_changed", "asr_model_changed", "asr_decode_failed", "asr_unsupported_streams", "asr_discontinuous_pts", "asr_audio_too_long", "asr_no_speech", "asr_worker_failed"}
                    if error.get("protocol_version") == "local-asr-v2" and error.get("kind") == "asr_error" and error.get("error_code") in allowed:
                        code = error["error_code"]
                except (ValueError, TypeError, AttributeError):
                    pass
            raise AsrProcessError(code, evidence, bytes(stderr.content) if streams else b"")
        if stdout.exceeded.is_set() or stderr.exceeded.is_set():
            raise AsrProcessError("asr_output_too_large", evidence, bytes(stderr.content))
        try:
            result = json.loads(stdout.content, parse_constant=_nonfinite, object_pairs_hook=_unique_object)
            validate_asr_result(result, payload)
        except (ValueError, TypeError, KeyError, AttributeError):
            raise AsrProcessError("asr_result_invalid", evidence, bytes(stderr.content)) from None
        result["execution"] = evidence
        return result


def _original_context_bytes(request: dict) -> bytes:
    provider = Path(__file__)
    worker = provider.parents[1] / "media/asr_worker.py"
    context = {"format": "local-asr-original-validation-context-v1",
               "provider_sha256": hashlib.sha256(provider.read_bytes()).hexdigest(),
               "worker_sha256": hashlib.sha256(worker.read_bytes()).hexdigest(),
               "request": request}
    return json.dumps(context, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def validate_original_asr_result(result: dict, original_context_bytes: bytes) -> None:
    """Exact original context only; Backend must verify its journal commitment."""
    if type(original_context_bytes) is not bytes or not 0 < len(original_context_bytes) <= 2 * 1024 * 1024:
        raise ValueError("invalid original ASR context bytes")
    def unique(pairs):
        value = {}
        for key, child in pairs:
            if key in value:
                raise ValueError("duplicate original context key")
            value[key] = child
        return value
    def nonfinite(_value):
        raise ValueError("nonfinite original context")
    context = json.loads(original_context_bytes.decode("utf-8"), object_pairs_hook=unique,
                         parse_constant=nonfinite)
    if (type(context) is not dict or set(context) != {"format", "provider_sha256", "worker_sha256", "request"}
            or context["format"] != "local-asr-original-validation-context-v1"
            or any(type(context[key]) is not str or not re.fullmatch("[0-9a-f]{64}", context[key])
                   for key in ("provider_sha256", "worker_sha256"))
            or json.dumps(context, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                          allow_nan=False).encode("utf-8") != original_context_bytes):
        raise ValueError("invalid canonical original ASR context")
    request = context["request"]
    required = {"audio_path", "storage_root", "model_dir", "model_revision", "audio_sha256",
                "video_audio_offset_us", "max_audio_duration_us", "model_file_sha256"}
    resource = {"require_execution_identity", "resource_manifest_path", "resource_manifest_sha256"}
    if type(request) is not dict or set(request) not in (required, required | resource):
        raise ValueError("invalid original ASR request fields")
    # No source/expected value is inferred from result. This is the same full
    # text/timestamps/resources/actual-execution validator as normal execution.
    validate_asr_result(result, request)


class LocalAsrDriver:
    def __init__(self, audio_path: Path, *, storage_root: Path, model_dir: Path,
                 python_executable: Path, model_revision: str, expected_audio_sha256: str,
                 video_audio_offset_us: int = 0, max_audio_duration_us: int = 60_000_000,
                 runtime_root: Path | None = None, expected_model_files: dict[str, str] | None = None,
                 timeout_seconds: float = 120, deadline_monotonic: float | None = None,
                 cancel: Callable[[], bool] | None = None, resource_manifest_path: Path | None = None,
                 resource_manifest_sha256: str | None = None):
        from video_creator.domain.errors import EngineError

        audio, root, model, python = map(Path, (audio_path, storage_root, model_dir, python_executable))
        if (audio.is_symlink() or not audio.is_file() or not audio.resolve().is_relative_to(root.resolve())
            or model.is_symlink() or not model.is_dir() or python.is_symlink() or not python.is_file()
            or type(video_audio_offset_us) is not int or type(max_audio_duration_us) is not int
            or not 0 < max_audio_duration_us <= 600_000_000):
            raise EngineError("asr_input_denied", "Offline ASR inputs are unavailable.", 403)
        self._python, self._audio, self._sha = python.resolve(), audio, expected_audio_sha256
        self._runtime_root = Path(runtime_root) if runtime_root is not None else root / "AsrRuntime"
        if self._runtime_root.is_symlink():
            raise EngineError("asr_input_denied", "Offline ASR runtime is unavailable.", 403)
        self._runtime_root.mkdir(parents=True, exist_ok=True)
        self._timeout, self._deadline, self._cancel = timeout_seconds, deadline_monotonic, cancel
        self._request = {"audio_path": str(audio.resolve()), "storage_root": str(root.resolve()), "model_dir": str(model.resolve()), "model_revision": model_revision, "audio_sha256": expected_audio_sha256, "video_audio_offset_us": video_audio_offset_us, "max_audio_duration_us": max_audio_duration_us, "model_file_sha256": dict(expected_model_files) if expected_model_files is not None else model_file_hashes(model)}
        if resource_manifest_path is not None or resource_manifest_sha256 is not None:
            manifest = Path(resource_manifest_path) if resource_manifest_path is not None else None
            if (manifest is None or manifest.is_symlink() or not manifest.is_file()
                or not isinstance(resource_manifest_sha256, str) or not re.fullmatch("[0-9a-f]{64}", resource_manifest_sha256)
                or hashlib.sha256(manifest.read_bytes()).hexdigest() != resource_manifest_sha256):
                raise EngineError("asr_resource_changed", "Actual ASR resource identity is unavailable.", 503)
            self._request.update(require_execution_identity=True, resource_manifest_path=str(manifest.resolve()),
                                 resource_manifest_sha256=resource_manifest_sha256)
        self._original_validation_context = _original_context_bytes(self._request)

    def validation_context_bytes(self) -> bytes:
        """Secret-free immutable original request; internal local journal only."""
        if _original_context_bytes(self._request) != self._original_validation_context:
            from video_creator.domain.errors import EngineError
            raise EngineError("asr_original_context_changed", "Original ASR request or implementation changed before execution.", 409)
        return self._original_validation_context

    def __call__(self, permit: ExecutionPermit, secret: SecretHandle | None) -> OperationObservation:
        from video_creator.domain.contracts import Money, OperationObservation
        from video_creator.domain.errors import EngineError

        if (permit.route.destination != ASR_DESTINATION or permit.route.capability != "transcription"
            or permit.route.source != "owned_local" or secret is not None):
            raise EngineError("asr_route_denied", "Only admitted offline ASR is supported.", 403)
        if hashlib.sha256(self._audio.read_bytes()).hexdigest() != self._sha:
            raise EngineError("asr_audio_changed", "Audio changed before transcription.", 422)
        self.validation_context_bytes()
        try:
            result = run_local_asr(self._request, python_executable=self._python, runtime_root=self._runtime_root, timeout_seconds=self._timeout, deadline_monotonic=self._deadline, cancel=self._cancel)
        except AsrProcessError as error:
            # Unconfirmed tree cleanup cannot become a definite operation failure.
            status = "unknown" if error.code == "asr_cleanup_failed" else "failed"
            return OperationObservation(status=status, actual_cost=Money(amount="0"), cost_evidence="confirmed_no_charge", result_json={"error_code": error.code, "execution": error.evidence})
        return OperationObservation(status="succeeded", actual_cost=Money(amount="0"), cost_evidence="confirmed_no_charge", result_json=result)
