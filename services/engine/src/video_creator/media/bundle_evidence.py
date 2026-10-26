"""Real installed clock/frame authorities for registered immutable bundle media."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from video_creator.domain import contracts as c
from video_creator.domain.errors import EngineError
from video_creator.providers.local_asr import AsrProcessError, _ProcessTree, _Stream
from video_creator.workflows.attempt_control import current_attempt


class BundleMediaEvidence:
    def __init__(self, python: Path, storage_root: Path):
        self.python, self.root = Path(python).resolve(strict=True), Path(storage_root).resolve(strict=True)
        self.worker = Path(__file__).with_name("bundle_probe_worker.py")
        # A frozen executable is not a Python interpreter. Launch its private
        # media-probe command so the observer uses the bundled av/_internal libs
        # in the same product process image; source/dev keeps the isolated
        # interpreter + script form.
        self.argv = ([str(self.python), "media-probe"] if getattr(sys, "frozen", False)
                     else [str(self.python), "-I", "-B", "-X", "utf8", str(self.worker)])
        self.execution_records = []
        # Measured identities of the actual observer process, never constants.
        self.tool_versions = []

    @property
    def observed_tool_version(self) -> str | None:
        """The single version the actual isolated observer reported, or None.

        None means no real observation has completed yet; callers must not
        substitute a profile constant for the measured library identity.
        """
        versions = set(self.tool_versions)
        return versions.pop() if len(versions) == 1 else None

    @property
    def observer_sha256(self) -> str:
        """sha256 of the actual fixed observer source this instance launches."""
        return hashlib.sha256(self.worker.read_bytes()).hexdigest()

    def _observe(self, path: Path, sha: str, mode: str, at_us: int = 0, exact_frame: dict | None = None):
        path = Path(path)
        if path.is_symlink() or not path.resolve().is_relative_to(self.root):
            raise EngineError("media_path_denied", "Media evidence requires controlled immutable bytes.", 403)
        environment = {name: os.environ[name] for name in ("SYSTEMROOT", "TEMP", "TMP") if name in os.environ}
        request = {"path": str(path), "storage_root": str(self.root), "sha256": sha, "mode": mode, "at_us": at_us}
        if exact_frame is not None:
            request["exact_frame"] = exact_frame
        argv = list(self.argv)
        control = current_attempt()
        deadline = time.monotonic() + control.remaining(30)
        started = time.monotonic()
        print(json.dumps({'event': 'observe_started', 'mode': mode, 'sha256': sha[:12],
                          'path': str(path), 'argv': argv, 'deadline_in': round(deadline - started, 3)},
                         ensure_ascii=False), file=sys.stderr, flush=True)
        process, tree, writer, streams = None, None, None, None
        failure = None
        failed_write = threading.Event()
        execution = {"child_terminal": False, "tree_empty": False, "stream_threads_terminal": False, "input_writer_terminal": False}
        try:
            process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment, shell=False, start_new_session=os.name != "nt")
            execution["child_pid"] = process.pid
            tree = _ProcessTree(process)
            stdout, stderr = _Stream(process.stdout, 16384), _Stream(process.stderr, 65536)
            streams = (stdout, stderr)
            def send_input():
                try:
                    process.stdin.write(json.dumps(request).encode())
                    process.stdin.close()
                except (OSError, ValueError):
                    failed_write.set()
            writer = threading.Thread(target=send_input, daemon=True)
            writer.start()
            while process.poll() is None:
                control.check()
                if time.monotonic() >= deadline:
                    print(json.dumps({'event': 'observe_timeout', 'mode': mode, 'sha256': sha[:12],
                                      'elapsed_seconds': round(time.monotonic() - started, 3),
                                      'bound_seconds': 30}, ensure_ascii=False),
                          file=sys.stderr, flush=True)
                    raise EngineError("media_evidence_timeout", "Actual media observation exceeded its bound.", 503)
                if stdout.exceeded.is_set() or stderr.exceeded.is_set() or failed_write.is_set() or stdout.failed.is_set() or stderr.failed.is_set():
                    raise EngineError("media_evidence_failed", "Actual media observation output is unavailable.", 503)
                time.sleep(0.02)
        except EngineError as error:
            failure = error
        except (OSError, ValueError, AsrProcessError):
            failure = EngineError("media_evidence_failed", "Actual media observation did not finish.", 503)
        finally:
            try:
                execution["tree_empty"] = tree.close() if tree is not None else False
            except (OSError, AsrProcessError):
                execution["tree_empty"] = False
            if process is not None:
                if process.poll() is None:
                    try:
                        process.kill()
                    except OSError:
                        pass
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    execution["tree_empty"] = False
                if writer is not None:
                    writer.join(timeout=5)
                execution.update(child_terminal=process.poll() is not None, return_code=process.returncode,
                                 input_writer_terminal=writer is None or not writer.is_alive())
            if streams is not None:
                for stream in streams:
                    stream.thread.join(timeout=5)
                execution.update(stream_threads_terminal=all(not stream.thread.is_alive() for stream in streams),
                    stdout_bytes=stdout.total, stderr_bytes=stderr.total, stdout_sha256=stdout.digest.hexdigest(), stderr_sha256=stderr.digest.hexdigest())
            self.execution_records.append(execution)
        if not all(execution[key] for key in ("tree_empty", "child_terminal", "stream_threads_terminal", "input_writer_terminal")):
            raise EngineError("media_evidence_cleanup_failed", "Actual observation resources have not all terminated.", 503, "reconcile")
        if failure is not None:
            raise failure
        print(json.dumps({'event': 'observe_finished', 'mode': mode, 'sha256': sha[:12],
                          'elapsed_seconds': round(time.monotonic() - started, 3),
                          'return_code': process.returncode}, ensure_ascii=False),
              file=sys.stderr, flush=True)
        if process.returncode != 0 or stdout.exceeded.is_set() or stderr.exceeded.is_set():
            raise EngineError("media_evidence_failed", "Actual media observation is unavailable.", 503)
        try:
            result = json.loads(stdout.content)
            if type(result) is not dict or result.get("input_sha256") != sha:
                raise ValueError("invalid observation")
        except (ValueError, TypeError):
            raise EngineError("media_evidence_invalid", "Actual media evidence is invalid.", 422) from None
        reported = result.get("tool_version")
        if type(reported) is str and reported:
            self.tool_versions.append(reported)
        return result

    def clock(self, asset: c.AssetRecord, path: Path):
        observed = self._observe(path, asset.sha256, "clock")
        return c.AudioClock.model_validate(observed["clock"]), observed["duration_us"]

    def frame(self, asset: c.AssetRecord, path: Path, at_us: int, method_ref: str):
        observed = self._observe(path, asset.sha256, "frame", at_us)
        fields = {key: value for key, value in observed.items() if key not in {"input_sha256", "tool_version"}}
        return c.FrameEvidenceRef(video_asset_id=asset.asset_id, video_sha256=asset.sha256,
                                  decoder_method_ref=method_ref, **fields)

    def audio_clock_authority(self, track: c.AudioTrackRef, path: Path) -> bool:
        try:
            observed = self._observe(path, track.sha256, "clock")
            return c.AudioClock.model_validate(observed["clock"]) == track.clock and observed["duration_us"] == track.intrinsic_duration_us
        except EngineError as error:
            if error.code.startswith("production_attempt_") or error.code == "media_evidence_cleanup_failed":
                raise
            return False
        except (ValueError, TypeError, KeyError):
            return False

    def frame_validator(self, frame: c.FrameEvidenceRef, path: Path) -> bool:
        try:
            if frame.actual_pts is None or frame.timebase_num is None or frame.timebase_den is None:
                return False
            observed = self._observe(path, frame.video_sha256, "frame", frame.at_us,
                                     {"pts": frame.actual_pts, "num": frame.timebase_num, "den": frame.timebase_den})
            return all(observed.get(name) == getattr(frame, name) for name in (
                "at_us", "actual_pts", "timebase_num", "timebase_den", "decoded_frame_sha256", "pixel_format", "width", "height"))
        except EngineError as error:
            if error.code.startswith("production_attempt_") or error.code == "media_evidence_cleanup_failed":
                raise
            return False
        except (ValueError, TypeError, KeyError):
            return False
