"""Controlled child-only observation/fault injection; delegates the real production CLI."""

import errno
import json
import os
import sys
import threading
import time
from dataclasses import asdict
from pathlib import Path

from video_creator.application.engine import EngineService
from video_creator.cli import lifecycle
from video_creator.cli import main as cli


def run():
    mode, receipt_path, *args = sys.argv[1:]
    destination = Path(receipt_path)
    evidence = {"mode": mode, "injected": mode != "observe", "pipe_closures": [], "decoder_calls": []}
    original_close = lifecycle.ControlPipe.close

    def observed_close(pipe):
        fd = pipe.fd
        original_close(pipe)
        if fd >= 0:
            try:
                os.fstat(fd)
            except OSError as error:
                evidence["pipe_closures"].append({"fd": fd, "closed": error.errno == errno.EBADF})

    lifecycle.ControlPipe.close = observed_close
    original_confirm = cli.confirm_stopped

    def observed_confirm(server, listener, state, original_threads):
        original_confirm(server, listener, state, original_threads)
        evidence["actual_state"] = asdict(state)
        evidence["listener_fd"] = listener.fileno()
        evidence["owned_live_threads"] = [t.name for t in threading.enumerate() if t not in original_threads and t.is_alive()]

    cli.confirm_stopped = observed_confirm
    if mode in {"slow-http", "timeout-http"}:
        original_list = EngineService.list_projects

        def slow_list(engine, subject):
            sys.stderr.buffer.write(b'{"event":"t6_request_started"}\n')
            sys.stderr.buffer.flush()
            time.sleep(0.8)
            return original_list(engine, subject)

        EngineService.list_projects = slow_list
    if mode == "timeout-http":
        original_serve = cli.controlled_serve

        async def bounded_serve(server, listener, state, source_fd):
            return await original_serve(server, listener, state, source_fd, timeout=0.35)

        cli.controlled_serve = bounded_serve
    if mode == "cleanup-failure":
        original_app = cli.create_app

        def failed_app(*positional, **keywords):
            def failed_shutdown():
                raise RuntimeError("Synthetic T6 cleanup failure; no secret")
            keywords["on_shutdown"] = failed_shutdown
            return original_app(*positional, **keywords)

        cli.create_app = failed_app
    if mode == "media-observe":
        from video_creator.media import ffmpeg
        original_popen = ffmpeg.subprocess.Popen

        def counted_popen(command, *positional, **keywords):
            evidence["decoder_calls"].append([str(item) for item in command])
            return original_popen(command, *positional, **keywords)

        ffmpeg.subprocess.Popen = counted_popen
    try:
        sys.argv = [sys.argv[0], *args]
        code = cli.main()
        evidence["cli_return"] = code
        return code
    finally:
        # No modeled success: state is recorded only after production confirmation succeeds.
        evidence["pending_loop"] = False
        destination.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    raise SystemExit(run())
