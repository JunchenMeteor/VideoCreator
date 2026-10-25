"""Bounded MCP JSON-RPC LF transport on trusted launcher-owned stdio pipes."""

import json
import logging
import secrets
import sys
import threading
from contextlib import asynccontextmanager

import anyio
from mcp import types
from mcp.shared.message import SessionMessage
from video_creator.application.bundles import BundleService
from video_creator.cli.lifecycle import ControlPipe
from video_creator.domain.errors import EngineError
from video_creator.integrations.mcp import create_mcp_server

MAX_RPC_LINE_BYTES = 4 * 1024 * 1024


def diagnostic(event, **values):
    print(json.dumps({"event": event, "scope": "mcp", **values}), file=sys.stderr, flush=True)


class SanitizedMcpLog(logging.Handler):
    def emit(self, record):
        # Never render SDK validation exception values or request metadata.
        diagnostic("mcp_diagnostic", code="protocol_diagnostic")


@asynccontextmanager
async def bounded_stdio():
    pipe = ControlPipe(sys.stdin.fileno())
    send_in, receive_in = anyio.create_memory_object_stream(0)
    send_out, receive_out = anyio.create_memory_object_stream(0)

    async def read():
        line, rejecting = bytearray(), False
        try:
            async with send_in:
                while True:
                    block = pipe.read_available()
                    if block == b"":
                        if line or rejecting:
                            diagnostic("mcp_frame_rejected", code="incomplete_rpc_frame")
                        return
                    if block is None:
                        await anyio.sleep(0.01)
                        continue
                    for value in block:
                        if rejecting:
                            if value == 10:
                                rejecting = False
                            continue
                        if len(line) >= MAX_RPC_LINE_BYTES:
                            line.clear()
                            rejecting = value != 10
                            diagnostic("mcp_frame_rejected", code="rpc_frame_too_large")
                            continue
                        if value != 10:
                            line.append(value)
                            continue
                        try:
                            message = types.JSONRPCMessage.model_validate_json(bytes(line))
                        except (ValueError, TypeError):
                            diagnostic("mcp_frame_rejected", code="invalid_rpc_frame")
                        else:
                            await send_in.send(SessionMessage(message))
                        finally:
                            line.clear()
        finally:
            pipe.close()

    async def write():
        async with receive_out:
            async for message in receive_out:
                payload = message.message.model_dump_json(by_alias=True, exclude_none=True).encode("utf-8") + b"\n"
                sys.stdout.buffer.write(payload)
                sys.stdout.buffer.flush()

    try:
        async with anyio.create_task_group() as tasks:
            tasks.start_soon(read)
            tasks.start_soon(write)
            try:
                yield receive_in, send_out
            finally:
                tasks.cancel_scope.cancel()
        await receive_in.aclose()
        await send_out.aclose()
    finally:
        pipe.close()


async def run_mcp_stdio(service: BundleService, token: str):
    if not isinstance(token, str) or len(token) < 32:
        raise EngineError("mcp_session_token_missing", "MCP requires a trusted per-session child environment token", 503)
    owner = service.principals.owner()
    original_threads = set(threading.enumerate())
    state = {"ready": False, "closed": False}
    logger = logging.getLogger("mcp")
    previous = logger.handlers[:], logger.propagate
    logger.handlers, logger.propagate = [SanitizedMcpLog()], False

    def actor():
        meta = server.request_context.meta
        fields = meta.model_dump() if meta is not None else {}
        authorization = fields.get("authorization")
        if not isinstance(authorization, str) or not secrets.compare_digest(authorization.encode("utf-8"), ("Bearer " + token).encode("utf-8")):
            raise EngineError("mcp_session_invalid", "Installation session is invalid", 401)
        current = service.principals.owner()
        if current != owner or current.installation_id != service.engine.instance_id:
            raise EngineError("principal_scope_changed", "MCP installation principal changed", 403)
        return current

    def ready():
        state["ready"] = True
        diagnostic("mcp_ready", instance_id=service.engine.instance_id, transport="stdio-jsonrpc-lf",
            authentication="per-call-meta-bearer", worker_started=False)

    def shutdown():
        state["closed"] = True

    server = create_mcp_server(service, actor, on_ready=ready, on_shutdown=shutdown)
    try:
        service.engine.recover()
        async with bounded_stdio() as (input_stream, output_stream):
            await server.run(input_stream, output_stream, server.create_initialization_options())
        if (not state["ready"] or not state["closed"]
                or any(thread.is_alive() for thread in threading.enumerate() if thread not in original_threads)):
            raise EngineError("mcp_cleanup_incomplete", "MCP transport/export resources have not actually stopped", 503)
        diagnostic("mcp_stopped", cleanup_completed=True, process_exit_pending=True, worker_cancelled=False)
    except EngineError:
        raise
    except Exception:  # noqa: BLE001 - never reflect SDK request metadata in a transport failure
        raise EngineError("mcp_transport_failed", "MCP transport or cleanup failed", 503) from None
    finally:
        logger.handlers, logger.propagate = previous
