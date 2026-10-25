"""Actual OS/stdio consumers. Integration Job host ABI must be bound first.

The host is not a mock or Test authority: it must be loaded by approved runtime
bootstrap from frozen Integration sources. No subprocess is started on import.
"""
from __future__ import annotations

import json
import queue
import sqlite3
import threading
import time

from t21_runtime import CaseBlocked


def _presence(ctx):
    with sqlite3.connect(ctx.engine.db.path.as_uri() + "?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute("SELECT worker_id,pid,workflow_version,resource_sha256,engine_version,heartbeat_us,expires_us,state,active_run_id FROM worker_presence").fetchall()
        assert len(rows) <= 1
        return dict(rows[0]) if rows else None


def _protected(host):
    identities = host.protected_identities()
    if not identities:
        raise CaseBlocked("nonempty_live_owned_sibling", "a real live protected holder must be available")
    for identity in identities:
        assert host.identity_is_live(identity), "protected holder not actually live"
    return identities


def _check_protected(host, identities):
    for identity in identities:
        assert host.identity_is_live(identity), "protected sibling PID/creation changed or was killed"


def _normal_close(process, host):
    observation = host.close_owned(process)
    assert observation.actual_exit == 0 and observation.forced is False
    assert observation.job_active_processes == 0 and observation.owned_handles_closed
    return {"actual_exit": observation.actual_exit, "forced": observation.forced, "job_active_processes": observation.job_active_processes}


def same_worker_second_run(ctx):
    fixture = ctx.fixture("OS-worker-session")
    host = ctx.host()
    protected = _protected(host)
    worker = host.launch_role("worker", ctx.engine.instance_id)
    assert "--once" not in worker.argv and "--run-id" not in worker.argv
    identity = worker.actual_identity()
    assert identity.pid > 0 and identity.creation_time and worker.job_assigned_before_resume
    try:
        ready = worker.wait_ready(timeout=10)
        assert ready["instance_id"] == ctx.engine.instance_id
        before = ctx.wait(lambda: _presence(ctx))
        assert before["pid"] == identity.pid and before["worker_id"] == ready["worker_id"]
        first = ctx.engine.accept_production("local-user", "T21-first", ctx.c.parse_production_request(fixture["first_request"]))
        first_detail = ctx.wait(lambda: _waiting(ctx, first.production_id), seconds=fixture["wait_seconds"])
        released = _presence(ctx)
        assert released["worker_id"] == before["worker_id"] and released["active_run_id"] is None
        assert first_detail.run_id != released["active_run_id"] and host.identity_is_live(identity)
        heartbeat = released["heartbeat_us"]
        ctx.wait(lambda: (_presence(ctx) or {}).get("heartbeat_us", 0) > heartbeat)
        second = ctx.engine.accept_production("local-user", "T21-second", ctx.c.parse_production_request(fixture["second_request"]))
        assert second.run_id != first.run_id
        second_detail = ctx.wait(lambda: _waiting(ctx, second.production_id), seconds=fixture["wait_seconds"])
        after = _presence(ctx)
        assert host.identity_is_live(identity) and worker.actual_identity() == identity
        assert after["pid"] == identity.pid and after["worker_id"] == before["worker_id"]
        assert after["heartbeat_us"] > heartbeat and after["active_run_id"] is None
        return {"identity": identity.to_evidence(), "worker_id": before["worker_id"],
                "first_run_id": first.run_id, "second_run_id": second.run_id,
                "first_state": first_detail.status, "second_state": second_detail.status,
                "scope": "real worker lease/heartbeat mechanism; template inputs do not prove autonomous media creation"}
    finally:
        _normal_close(worker, host)
        _check_protected(host, protected)


def _waiting(ctx, production_id):
    detail = ctx.engine.get_production("local-user", production_id)
    if detail.status != "waiting_user":
        return None
    # Read actual lease columns instead of assuming waiting implies release.
    with sqlite3.connect(ctx.engine.db.path.as_uri() + "?mode=ro", uri=True) as connection:
        row = connection.execute("SELECT worker_id,lease_until_us FROM runs WHERE id=?", (detail.run_id,)).fetchone()
        bindings = connection.execute("SELECT count(*) FROM execution_bindings WHERE run_id=?", (detail.run_id,)).fetchone()[0]
        steps = connection.execute("SELECT count(*) FROM steps WHERE run_id=?", (detail.run_id,)).fetchone()[0]
    assert row is not None
    if row[0] is not None or row[1] != 0 or bindings != 1 or steps < 1:
        return None
    return detail


class StdioMcpClient:
    def __init__(self, process, *, protocol_version, journal, maximum_bytes=33_554_432):
        self.process, self.version, self.journal = process, protocol_version, journal
        self.maximum = maximum_bytes
        self.messages = queue.Queue(maxsize=32)
        self.sequence = 0
        self.closed = False
        self.reader = threading.Thread(target=self._read, daemon=True, name="T21-McpReader")
        self.reader.start()

    def _read(self):
        from t15_evidence import strict_json
        try:
            while True:
                raw = self.process.stdout.readline(self.maximum + 1)
                if not raw:
                    self.messages.put(EOFError("actual MCP stdout closed"), timeout=1)
                    return
                if len(raw) > self.maximum or not raw.endswith(b"\n"):
                    raise ValueError("MCP bounded JSON-line framing failed")
                message = strict_json(raw)
                if type(message) is not dict or message.get("jsonrpc") != "2.0":
                    raise ValueError("MCP JSON-RPC envelope invalid")
                self.messages.put(message, timeout=1)
        except Exception as error:
            try:
                self.messages.put(error, timeout=1)
            except queue.Full:
                pass

    def _send(self, message):
        raw = json.dumps(message, allow_nan=False, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
        assert len(raw) <= self.maximum
        self.process.stdin.write(raw)
        self.process.stdin.flush()

    def request(self, method, params, timeout=20):
        self.sequence += 1
        request_id = self.sequence
        self._send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            message = self.messages.get(timeout=max(0.01, deadline - time.monotonic()))
            if isinstance(message, Exception):
                raise message
            if "id" not in message:
                continue  # Actual notifications are retained as metadata, not responses.
            assert message["id"] == request_id, "cross-request/replayed MCP response"
            if "error" in message:
                raise AssertionError("actual MCP protocol error: " + str(message["error"].get("code")))
            assert "result" in message
            self.journal.record("mcp_rpc_returned", {"method": method, "request_id": request_id})
            return message["result"]
        raise TimeoutError("MCP request actual deadline elapsed")

    def initialize(self):
        result = self.request("initialize", {"protocolVersion": self.version, "capabilities": {},
                                             "clientInfo": {"name": "VideoCreatorIndependentTest", "version": "T21"}})
        assert result["protocolVersion"] == self.version and "tools" in result["capabilities"]
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return result

    def tools(self):
        return self.request("tools/list", {})["tools"]

    def call(self, name, arguments):
        return self.request("tools/call", {"name": name, "arguments": arguments})

    def close_reader(self):
        self.reader.join(timeout=3)
        assert not self.reader.is_alive(), "MCP reader remained live after owned process close"


def actual_mcp_host(ctx):
    fixture = ctx.fixture("MCP-session")
    host = ctx.host()
    protected = _protected(host)
    process = host.launch_role("mcp", ctx.engine.instance_id)
    client = StdioMcpClient(process, protocol_version=fixture["protocol_version"], journal=ctx.journal)
    try:
        initialized = client.initialize()
        names = [tool["name"] for tool in client.tools()]
        expected = {"production_create", "production_get", "production_decide", "bundle_get", "bundle_semantic_list",
                    "bundle_export", "bundle_export_get", "bundle_reference_grant", "bundle_reference_revoke",
                    "bundle_import", "bundle_import_get", "bundle_import_export"}
        assert len(names) == len(expected) and set(names) == expected
        result = client.call("bundle_get", {"revision_id": "T21-absent-revision"})
        assert result["isError"] is True
        envelope = ctx.c.ErrorEnvelope.model_validate(result["structuredContent"])
        assert envelope.code == "not_found", "configured authenticated MCP path required"
        # Actor injection must fail before any service read; no credential in args.
        rejected = client.call("bundle_get", {"revision_id": "T21-absent-revision", "owner": "local-user"})
        assert rejected["isError"] is True
        bad = ctx.c.ErrorEnvelope.model_validate(rejected["structuredContent"])
        assert bad.code == "invalid_request"
        return {"protocol_version": initialized["protocolVersion"], "actual_tools": names,
                "missing_bundle_code": envelope.code, "payload_actor_code": bad.code}
    finally:
        _normal_close(process, host)
        client.close_reader()
        _check_protected(host, protected)


def unconfigured_mcp_host(ctx):
    fixture = ctx.fixture("MCP-session")
    if fixture.get("unconfigured_service_handler_exposed_over_stdio") is not True:
        raise CaseBlocked("final_MCP_auth_failure_ABI", "old unconfigured handler 503 does not define the new host's missing-session startup/auth boundary")
    host = ctx.host()
    protected = _protected(host)
    process = host.launch_role("mcp_unconfigured", ctx.engine.instance_id)
    client = StdioMcpClient(process, protocol_version=fixture["protocol_version"], journal=ctx.journal)
    try:
        client.initialize()
        result = client.call("bundle_get", {"revision_id": "T21-absent"})
        assert result["isError"] is True
        envelope = ctx.c.ErrorEnvelope.model_validate(result["structuredContent"])
        assert envelope.code == "mcp_principal_unconfigured"
        return {"actual_auth_refusal": envelope.code}
    finally:
        _normal_close(process, host)
        client.close_reader()
        _check_protected(host, protected)


def actual_worker_control_boundaries(ctx):
    """Real private pipe/EOF/default-off semantics, never callback simulation.

    This consumer needs the final published Worker frame/argv description and
    an actual owned stdin writer/close endpoint. Neither ABI is guessed here.
    """
    fixture = ctx.fixture("OS-worker-control")
    if not fixture.get("final_backend_control_descriptor"):
        raise CaseBlocked("final_Worker_private_control_ABI", "default-off/EOF/framing metadata not yet fixed")
    descriptor = ctx.bound_json(fixture["final_backend_control_descriptor"])
    assert descriptor["frame_hex"] == b"shutdown\n".hex() and descriptor["maximum_frame_bytes"] == 64
    host = ctx.host()
    protected = _protected(host)
    observations = []
    for launch_profile, data, close_pipe, expected_early_exit in (
        ("worker-control-default-off", b"shutdown\n", False, False),
        ("worker-private-control", b"", True, False),
        ("worker-private-control", b"x" * 65, True, True),
        ("worker-private-control", b"invalid\n", False, True),
    ):
        process = host.launch_role(launch_profile, ctx.engine.instance_id)
        identity = process.actual_identity()
        try:
            process.wait_ready(timeout=10)
            before = _presence(ctx)
            assert before and before["pid"] == identity.pid
            process.write_owned_stdin(data)
            if close_pipe:
                process.close_owned_stdin()
            if expected_early_exit:
                terminal = process.wait_actual_exit(timeout=descriptor["invalid_frame_exit_seconds"])
                assert terminal.actual_exit != 0 and terminal.forced is False
                assert terminal.job_active_processes == 0
            else:
                ctx.wait(lambda: (_presence(ctx) or {}).get("heartbeat_us", 0) > before["heartbeat_us"])
                assert host.identity_is_live(identity), "default-off or EOF cancelled the persistent Worker"
                assert _presence(ctx)["worker_id"] == before["worker_id"]
                terminal = host.close_owned(process)
                assert terminal.actual_exit == 0 and not terminal.forced and terminal.job_active_processes == 0
            observations.append({"profile": launch_profile, "identity": identity.to_evidence(),
                                 "actual_exit": terminal.actual_exit, "forced": terminal.forced})
        finally:
            # Cleanup is tied to the captured Job, not a PID discovered later.
            if host.identity_is_live(identity):
                residual = host.kill_owned_job(process, identity)
                assert residual.job_active_processes == 0
            _check_protected(host, protected)
    return {"actual_control_boundaries": observations}


def actual_worker_stop_new_claims(ctx):
    fixture = ctx.fixture("OS-worker-stop-new-claims")
    if not fixture.get("final_backend_control_descriptor"):
        raise CaseBlocked("final_Worker_private_control_ABI", "real active-work/stop marker binding is unavailable")
    descriptor = ctx.bound_json(fixture["final_backend_control_descriptor"])
    assert descriptor["frame_hex"] == b"shutdown\n".hex()
    host = ctx.host()
    protected = _protected(host)
    worker = host.launch_role("worker", ctx.engine.instance_id)
    identity = worker.actual_identity()
    try:
        worker.wait_ready(timeout=10)
        first = ctx.engine.accept_production("local-user", "T21-stop-first", ctx.c.parse_production_request(fixture["first_request"]))
        active = worker.wait_actual_work_started(first.run_id, timeout=fixture["wait_seconds"])
        assert active["run_id"] == first.run_id and active["pid"] == identity.pid
        worker.write_owned_stdin(b"shutdown\n")
        second = ctx.engine.accept_production("local-user", "T21-stop-second", ctx.c.parse_production_request(fixture["second_request"]))
        closed = worker.wait_actual_exit(timeout=descriptor["active_work_grace_seconds"])
        assert closed.actual_exit == 0 and closed.forced is False and closed.job_active_processes == 0
        first_detail = ctx.engine.get_production("local-user", first.production_id)
        second_detail = ctx.engine.get_production("local-user", second.production_id)
        assert first_detail.status != "cancel_requested" and second_detail.run_id != first_detail.run_id
        with sqlite3.connect(ctx.engine.db.path.as_uri() + "?mode=ro", uri=True) as con:
            second_bindings = con.execute("SELECT count(*) FROM execution_bindings WHERE run_id=?", (second.run_id,)).fetchone()[0]
            first_cancel = con.execute("SELECT cancellation_requested FROM runs WHERE id=?", (first.run_id,)).fetchone()[0]
        assert second_bindings == 0 and not first_cancel, "private host stop must stop claims without cancelling production"
        return {"identity": identity.to_evidence(), "first_run_id": first.run_id,
                "second_unclaimed_run_id": second.run_id, "actual_exit": closed.actual_exit}
    finally:
        if host.identity_is_live(identity):
            cleanup = host.kill_owned_job(worker, identity)
            assert cleanup.job_active_processes == 0
        _check_protected(host, protected)
