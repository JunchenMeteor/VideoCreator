"""Actual local neural narration behind the original Operation and lease."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import threading
import time
from pathlib import Path

from video_creator.domain.errors import EngineError
from video_creator.providers.local_asr import AsrProcessError, _ProcessTree, _Stream
from video_creator.providers.production_common import (
    install_output,
    local_observation,
    permit_scope,
)
from video_creator.providers.production_resources import file_sha256
from video_creator.workflows.attempt_control import attempt_control

DESTINATION = "local:piper-tts-v1"


class PiperNarrationDriver:
    def __init__(self, *, engine, worker, decoder, resources, route_id, lease, output,
                 storage_root, text, cancel, deadline_monotonic):
        self.engine, self.worker, self.decoder = engine, worker, decoder
        self.resources, self.route_id, self.lease, self.output = resources, route_id, lease, output
        self.storage_root, self.text = Path(storage_root), text
        self.control = attempt_control(cancel, deadline_monotonic)

    def __call__(self, permit, secret):
        with self.control.activate():
            permit_scope(self.engine, permit, self.lease, self.route_id, "speech", DESTINATION, local=True, secret=secret)
            config = self.resources.section("narration", "piper")
            paths = {name: self.resources.resource(config[name]) for name in
                     ("python", "worker", "model", "model_config", "license_document")}
            current = Path(__file__).parents[1] / "media/piper_worker.py"
            if hashlib.sha256(current.read_bytes()).digest() != hashlib.sha256(paths["worker"].read_bytes()).digest():
                raise EngineError("production_tts_code_changed", "Installed TTS worker differs from the current registered implementation.", 503)
            request = {"protocol": "piper-production-worker-v1", "text": self.text,
                       "resource_root": str(self.resources.root), "storage_root": str(self.storage_root),
                       "partial_output": str(self.output.partial_path), "piper_version": config["version"]}
            for name in ("model", "model_config", "license_document"):
                request[name] = str(paths[name])
                request[name + "_sha256"] = self.resources.records[config[name].casefold()]["sha256"]
            result, execution = self._run([str(paths["python"]), "-I", "-B", "-X", "utf8", str(paths["worker"])], request)
            expected = hashlib.sha256(self.text.encode()).hexdigest()
            if (result.get("protocol") != "piper-production-worker-v1" or result.get("status") != "succeeded"
                    or result.get("source_text_sha256") != expected
                    or result.get("output_sha256") != file_sha256(self.output.partial_path)
                    or result.get("output_bytes") != self.output.partial_path.stat().st_size):
                raise EngineError("production_tts_observation_invalid", "Actual narration output did not match its original request/bytes.", 422)
            file, probe = install_output(self.engine, self.worker, self.lease, self.output, self.decoder, "audio/wav")
            return local_observation((file,), {"synthesis": result, "probe": probe.model_dump(mode="json"),
                                              "execution": execution, "scope": "actual neural narration; source text is not ASR"})

    def _run(self, argv, request):
        raw = json.dumps(request, ensure_ascii=False).encode()
        if len(raw) > 32768:
            raise EngineError("production_tts_input_denied", "Narration request exceeds its bounded protocol.", 413)
        deadline = time.monotonic() + self.control.remaining(120)
        process, tree, writer, streams = None, None, None, None
        write_failed = threading.Event()
        execution = {"child_terminal": False, "tree_empty": False, "threads_terminal": False}
        failure = None
        try:
            process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                env={name: os.environ[name] for name in ("SYSTEMROOT", "TEMP", "TMP") if name in os.environ},
                shell=False, start_new_session=os.name != "nt")
            execution["child_pid"] = process.pid
            tree = _ProcessTree(process)
            stdout, stderr = _Stream(process.stdout, 32768), _Stream(process.stderr, 65536)
            streams = (stdout, stderr)
            def send():
                try:
                    process.stdin.write(raw)
                    process.stdin.close()
                except (OSError, ValueError):
                    write_failed.set()
            writer = threading.Thread(target=send, daemon=True)
            writer.start()
            while process.poll() is None:
                self.control.check()
                if time.monotonic() >= deadline:
                    raise EngineError("production_tts_timeout", "Actual narration exceeded its time bound.", 409)
                if self.output.partial_path.exists() and self.output.partial_path.stat().st_size > 64 * 1024 * 1024:
                    raise EngineError("production_tts_output_invalid", "Narration PCM output exceeded its byte bound.", 413)
                if write_failed.is_set() or any(stream.exceeded.is_set() or stream.failed.is_set() for stream in streams):
                    raise EngineError("production_tts_output_invalid", "Narration child protocol exceeded its bound.", 503)
                time.sleep(0.02)
        except EngineError as error:
            failure = error
        except (OSError, ValueError, AsrProcessError):
            failure = EngineError("production_tts_failed", "Actual narration process was unavailable.", 503)
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
                execution.update(child_terminal=process.poll() is not None, return_code=process.returncode)
            if writer is not None:
                writer.join(timeout=5)
            if streams is not None:
                for stream in streams:
                    stream.thread.join(timeout=5)
                execution.update(stdout_bytes=stdout.total, stderr_bytes=stderr.total,
                                 stdout_sha256=stdout.digest.hexdigest(), stderr_sha256=stderr.digest.hexdigest())
                execution["threads_terminal"] = (not writer.is_alive()
                                                and all(not stream.thread.is_alive() for stream in streams))
        if not all(execution[key] for key in ("child_terminal", "tree_empty", "threads_terminal")):
            raise EngineError("production_tts_cleanup_uncertain", "Narration process resources remain unresolved.", 503, "reconcile")
        if failure is not None:
            raise failure
        if process.returncode or any(stream.exceeded.is_set() or stream.failed.is_set() for stream in streams):
            raise EngineError("production_tts_failed", "Actual narration process did not succeed.", 503)
        try:
            result = json.loads(stdout.content)
            if not isinstance(result, dict):
                raise TypeError("object required")
        except (ValueError, TypeError):
            raise EngineError("production_tts_output_invalid", "Actual narration child returned an invalid protocol.", 422) from None
        return result, execution
