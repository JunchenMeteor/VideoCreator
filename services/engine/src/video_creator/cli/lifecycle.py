"""Opt-in launcher-owned byte pipe control; never a production/task command."""

import asyncio
import os
import select
import stat
import sys
import threading
import time
from dataclasses import dataclass

import uvicorn

from video_creator.domain.errors import EngineError

MAX_FRAME_BYTES = 64
SHUTDOWN_FRAME = b"shutdown\n"
SHUTDOWN_TIMEOUT_SECONDS = 10.0


def diagnostic(code: str) -> None:
    # Codes are implementation constants. No channel input is ever reflected.
    data = ('{"event":"api_control","code":"' + code + '"}\n').encode("ascii")
    sys.stderr.buffer.write(data)
    sys.stderr.buffer.flush()


class ControlFrames:
    """At most 63 payload bytes; a rejected long frame is discarded through LF."""

    def __init__(self, on_diagnostic=diagnostic):
        self.pending = bytearray()
        self.discarding = False
        self.diagnostic = on_diagnostic

    def feed(self, block: bytes) -> bool:
        for byte in block:
            if self.discarding:
                if byte == 10:
                    self.discarding = False
                continue
            if byte != 10 and len(self.pending) >= MAX_FRAME_BYTES - 1:
                self.pending.clear()
                self.discarding = True
                self.diagnostic("frame_too_large")
                continue
            self.pending.append(byte)
            if byte == 10:
                accepted = self.pending == SHUTDOWN_FRAME
                self.pending.clear()
                if accepted:
                    return True
                self.diagnostic("frame_rejected")
        return False

    def eof(self) -> None:
        if self.pending:
            self.diagnostic("incomplete_frame")
        self.pending.clear()
        self.discarding = False


class ControlPipe:
    """Owned duplicate fd; readiness polling avoids any blocking reader thread."""

    def __init__(self, source_fd: int):
        self.fd = os.dup(source_fd)
        try:
            if os.name == "nt":
                import ctypes
                import msvcrt
                from ctypes import wintypes

                self.handle = wintypes.HANDLE(msvcrt.get_osfhandle(self.fd))
                self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
                self.kernel.GetFileType.argtypes = [wintypes.HANDLE]
                self.kernel.GetFileType.restype = wintypes.DWORD
                self.kernel.PeekNamedPipe.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD,
                                                      wintypes.LPVOID, ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID]
                self.kernel.PeekNamedPipe.restype = wintypes.BOOL
                if self.kernel.GetFileType(self.handle) != 3:  # FILE_TYPE_PIPE
                    raise EngineError("control_pipe_required", "Private control requires a launcher stdin pipe", 400)
                # CRT text mode must not silently turn rejected CRLF into accepted LF.
                msvcrt.setmode(self.fd, os.O_BINARY)
            elif not stat.S_ISFIFO(os.fstat(self.fd).st_mode):
                raise EngineError("control_pipe_required", "Private control requires a launcher stdin pipe", 400)
        except BaseException:
            self.close()
            raise

    def read_available(self) -> bytes | None:
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes

            available = wintypes.DWORD()
            if not self.kernel.PeekNamedPipe(self.handle, None, 0, None, ctypes.byref(available), None):
                code = ctypes.get_last_error()
                if code in {109, 232, 233}:  # broken/empty/disconnected pipe: EOF
                    return b""
                raise OSError("Private control pipe is unavailable")
            if not available.value:
                return None
            return os.read(self.fd, min(available.value, 4096))
        readable, _, _ = select.select([self.fd], [], [], 0)
        return os.read(self.fd, 4096) if readable else None

    def close(self) -> None:
        if self.fd >= 0:
            os.close(self.fd)
            self.fd = -1


@dataclass
class ApiLifecycle:
    ready: bool = False
    lifespan_completed: bool = False
    stop_requested: bool = False
    stop_started: float | None = None
    reader_completed: bool = False
    serve_completed: bool = False


async def controlled_serve(server: uvicorn.Server, listener, state: ApiLifecycle,
                           source_fd: int, timeout: float = SHUTDOWN_TIMEOUT_SECONDS) -> None:
    pipe = ControlPipe(source_fd)
    stop_event = asyncio.Event()

    async def read_control():
        frames = ControlFrames()
        try:
            while True:
                block = pipe.read_available()
                if block == b"":
                    frames.eof()
                    diagnostic("channel_eof")
                    return
                if block is not None and frames.feed(block):
                    state.stop_requested = True
                    state.stop_started = time.monotonic()
                    server.should_exit = True
                    stop_event.set()
                    return
                await asyncio.sleep(0.05)
        except OSError:
            # Channel loss does not request API or task cancellation.
            diagnostic("channel_unavailable")
        finally:
            pipe.close()
            state.reader_completed = True

    # Uvicorn's own drain timeout cancels tasks without raising. The owner
    # instead bounds the whole private shutdown and reports its failure.
    server.config.timeout_graceful_shutdown = None
    serving = asyncio.create_task(server.serve(sockets=[listener]), name="api-server")
    reader = asyncio.create_task(read_control(), name="api-private-control")
    requested = asyncio.create_task(stop_event.wait(), name="api-stop-request")
    try:
        done, _ = await asyncio.wait({serving, requested}, return_when=asyncio.FIRST_COMPLETED)
        if serving not in done:
            remaining = max(0, timeout - (time.monotonic() - state.stop_started))
            try:
                await asyncio.wait_for(asyncio.shield(serving), remaining)
            except TimeoutError:
                diagnostic("shutdown_timeout")
                raise EngineError("shutdown_timeout", "API shutdown exceeded its bounded cleanup window", 503) from None
        else:
            await serving  # Preserve startup failures and signal exits.
        if state.stop_started is not None and time.monotonic() - state.stop_started > timeout:
            diagnostic("shutdown_timeout")
            raise EngineError("shutdown_timeout", "API shutdown exceeded its bounded cleanup window", 503)
        state.serve_completed = True
    finally:
        for task in (reader, requested, serving):
            if not task.done():
                task.cancel()
        # This awaits actual reader fd release; no daemon thread is left behind.
        await asyncio.gather(reader, requested, serving, return_exceptions=True)
        pipe.close()


def confirm_stopped(server: uvicorn.Server, listener, state: ApiLifecycle,
                    original_threads: set[threading.Thread]) -> None:
    """Called only after the loop and listener context have really returned."""
    deadline = (state.stop_started or time.monotonic()) + SHUTDOWN_TIMEOUT_SECONDS
    owned_threads = [thread for thread in threading.enumerate() if thread not in original_threads]
    for thread in owned_threads:
        thread.join(timeout=max(0, deadline - time.monotonic()))
    lifespan = server.lifespan
    complete = (state.stop_requested and state.ready and state.lifespan_completed
                and state.serve_completed and state.reader_completed and server.started
                and not server.force_exit and not lifespan.error_occurred
                and not lifespan.startup_failed and not lifespan.shutdown_failed
                and listener.fileno() == -1 and not server.server_state.connections
                and not any(not task.done() for task in server.server_state.tasks)
                and not any(thread.is_alive() for thread in owned_threads))
    if time.monotonic() > deadline:
        raise EngineError("shutdown_timeout", "API cleanup exceeded its bounded cleanup window", 503)
    if not complete:
        raise EngineError("api_cleanup_incomplete", "API cleanup did not satisfy the private stop contract", 503)
    sys.stderr.buffer.write(b'{"event":"api_stopped","scope":"api"}\n')
    sys.stderr.buffer.flush()
