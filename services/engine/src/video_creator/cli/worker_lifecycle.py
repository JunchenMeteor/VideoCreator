"""Opt-in worker quiesce pipe; EOF never cancels a production."""

import json
import os
import sys
import threading
import time

from video_creator.cli.lifecycle import ControlFrames, ControlPipe
from video_creator.domain.errors import EngineError

DRAIN_SECONDS = 10.0


def process_creation_identity():
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        kernel.GetProcessTimes.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.FILETIME), ctypes.POINTER(wintypes.FILETIME),
            ctypes.POINTER(wintypes.FILETIME), ctypes.POINTER(wintypes.FILETIME)]
        kernel.GetProcessTimes.restype = wintypes.BOOL
        values = [wintypes.FILETIME() for _ in range(4)]
        if not kernel.GetProcessTimes(kernel.GetCurrentProcess(), *(ctypes.byref(value) for value in values)):
            raise EngineError("process_identity_unavailable", "Actual Windows process creation identity is unavailable", 503)
        ticks = (values[0].dwHighDateTime << 32) | values[0].dwLowDateTime
        return {"kind": "windows-filetime-100ns", "value": str(ticks)}
    # Precise OS creation identity for other platforms requires their actual
    # integration adapter. Do not replace it with this function's wall clock.
    raise EngineError("process_identity_unavailable", "Actual process creation identity needs a platform-specific installed adapter", 503)


class WorkerControl:
    def __init__(self, enabled=False, source_fd=None):
        self.enabled, self.requested, self.finished = enabled, threading.Event(), threading.Event()
        self.stop_started = None
        self.error = None
        self.reader = self.pipe = None
        if enabled:
            self.pipe = ControlPipe(sys.stdin.fileno() if source_fd is None else source_fd)

    @property
    def stop_requested(self):
        return self.requested.is_set()

    def wait(self, seconds):
        return self.requested.wait(seconds)

    @staticmethod
    def diagnostic(code):
        print(json.dumps({"event": "worker_control", "scope": "worker", "code": code}), file=sys.stderr, flush=True)

    def __enter__(self):
        if self.pipe is not None:
            def read():
                frames = ControlFrames(self.diagnostic)
                try:
                    while not self.finished.wait(0.05):
                        block = self.pipe.read_available()
                        if block == b"":
                            frames.eof()
                            self.diagnostic("channel_eof")
                            return
                        if block is not None and frames.feed(block):
                            self.stop_started = time.monotonic()
                            self.requested.set()
                            return
                except OSError:
                    self.diagnostic("channel_unavailable")
                finally:
                    self.pipe.close()
            self.reader = threading.Thread(target=read, name="worker-private-control")
            self.reader.start()
        return self

    def assert_drain_completed(self):
        if self.stop_started is not None and time.monotonic() - self.stop_started > DRAIN_SECONDS:
            raise EngineError("worker_shutdown_timeout", "Current attempt did not really drain in the private shutdown window", 503)

    def __exit__(self, *exc):
        self.finished.set()
        if self.reader:
            self.reader.join(timeout=1)
            if self.reader.is_alive():
                raise EngineError("worker_cleanup_incomplete", "Private worker pipe reader has not actually ended", 503)
        if self.pipe:
            self.pipe.close()


def worker_ready(engine, worker_id, resource_sha256, workflow_version):
    from video_creator.application.worker import WorkerService
    with engine.db.connect() as connection:
        row = WorkerService(engine, workflow_version=workflow_version)._presence(connection, worker_id)
        if row["resource_sha256"] != resource_sha256:
            raise EngineError("worker_resource_conflict", "Ready resource identity differs from the held actual presence", 409)
    print(json.dumps({"event": "worker_ready", "scope": "worker", "instance_id": engine.instance_id,
        "worker_id": worker_id, "pid": os.getpid(), "process_creation": process_creation_identity(),
        "resource_sha256": resource_sha256, "workflow_version": workflow_version,
        "heartbeat_us": row["heartbeat_us"], "presence_expires_us": row["expires_us"],
        "autonomous_creation_ready": False}), file=sys.stderr, flush=True)


def confirm_worker_stopped(control, original_threads):
    if any(thread.is_alive() for thread in threading.enumerate() if thread not in original_threads):
        raise EngineError("worker_cleanup_incomplete", "Owned worker resources have not really ended", 503)
    control.assert_drain_completed()
    print(json.dumps({"event": "worker_stopped", "scope": "worker", "pid": os.getpid(),
        "process_creation": process_creation_identity(), "cleanup_completed": True,
        "process_exit_pending": True}), file=sys.stderr, flush=True)
