"""T22 real stdio/control consumers. No product import or spawn on import.

Private authorization is only held in memory, delivered by the admitted host.
No bridge may silently supply it to the explicit missing/wrong-auth probes.
"""
from __future__ import annotations

import copy
import sqlite3

from t21_process_cases import StdioMcpClient, _check_protected, _presence, _protected
from t21_runtime import CaseBlocked


def authorized_params(name, arguments, bearer_header):
    if type(bearer_header) is not str or not bearer_header.startswith("Bearer ") or len(bearer_header) < 39:
        raise CaseBlocked("private_MCP_session_handle", "trusted per-session Bearer handle unavailable")
    # This object is transient request memory. Never persist, hash or log it.
    return {"name": name, "arguments": copy.deepcopy(arguments), "_meta": {"authorization": bearer_header}}


class AuthorizedStdioMcpClient(StdioMcpClient):
    def call_authorized(self, name, arguments, private_handle):
        def send(header):
            params = authorized_params(name, arguments, header)
            try:
                return self.request("tools/call", params)
            finally:
                params.pop("_meta", None)
        # The actual host owns the real per-child token. Test does not read
        # source files, env secrets or turn a fixture string into admission.
        return private_handle.with_authorization(send)

    def call_exact_params(self, params):
        # Deliberately no auth injection/normalization; negative bytes preserve
        # missing or known wrong public sentinel metadata exactly.
        return self.request("tools/call", copy.deepcopy(params))


def actual_mcp_host(ctx):
    fixture = ctx.fixture("MCP-session")
    host = ctx.host()
    if not hasattr(host, "mcp_session_token_handle"):
        raise CaseBlocked("trusted_MCP_private_handle_bridge", "per-child memory token-handle ABI has not been bound")
    protected = _protected(host)
    process = host.launch_role("mcp", ctx.engine.instance_id)
    private_handle = host.mcp_session_token_handle(process)
    client = AuthorizedStdioMcpClient(process, protocol_version=fixture["protocol_version"], journal=ctx.journal, maximum_bytes=4_194_304)
    try:
        initialized = client.initialize()
        names = [tool["name"] for tool in client.tools()]
        expected = {"production_create", "production_get", "production_decide", "bundle_get", "bundle_semantic_list",
                    "bundle_export", "bundle_export_get", "bundle_reference_grant", "bundle_reference_revoke",
                    "bundle_import", "bundle_import_get", "bundle_import_export"}
        assert len(names) == len(expected) and set(names) == expected
        result = client.call_authorized("bundle_get", {"revision_id": "T22-absent"}, private_handle)
        assert result["isError"] is True
        envelope = ctx.c.ErrorEnvelope.model_validate(result["structuredContent"])
        assert envelope.code == "not_found"
        rejected = client.call_authorized("bundle_get", {"revision_id": "T22-absent", "owner": "local-user"}, private_handle)
        assert rejected["isError"] is True
        assert ctx.c.ErrorEnvelope.model_validate(rejected["structuredContent"]).code == "invalid_request"
        auth_refusals = []
        for params in (
            {"name": "bundle_get", "arguments": {"revision_id": "T22-absent"}},
            {"name": "bundle_get", "arguments": {"revision_id": "T22-absent"},
             "_meta": {"authorization": "Bearer T22_PUBLIC_DELIBERATELY_INVALID"}},
        ):
            result = client.call_exact_params(params)
            assert result["isError"] is True
            actual = ctx.c.ErrorEnvelope.model_validate(result["structuredContent"])
            assert actual.code == "mcp_session_invalid"
            auth_refusals.append(actual.code)
        ctx.journal.record("mcp_auth_boundary", {"authorized_business_code": envelope.code,
            "unauthorized_codes": auth_refusals, "token_bytes_logged_or_hashed": False})
        return {"protocol_version": initialized["protocolVersion"], "actual_tools": names,
                "authorized_missing_bundle": envelope.code, "actual_auth_refusals": auth_refusals}
    finally:
        # MCP lifecycle closes its actual owned stdin to produce EOF; sending
        # the Worker shutdown line into JSON-RPC would be an invalid RPC frame.
        observation = host.close_owned(process, mode="stdio_eof")
        assert observation.actual_exit == 0 and observation.forced is False and observation.job_active_processes == 0
        assert observation.stderr_role_marker_seen
        client.close_reader()
        _check_protected(host, protected)


def control_specs():
    # Literal original bytes, with distinct incomplete-EOF and oversized-EOF.
    # These are expectations, not a reimplementation of ControlFrames.
    return (
        {"name": "invalid_LF", "bytes": b"invalid\n", "eof": False, "diagnostics": ("frame_rejected",), "continues": True},
        {"name": "non_ASCII_LF", "bytes": b"\xff\n", "eof": False, "diagnostics": ("frame_rejected",), "continues": True},
        {"name": "too_long_LF", "bytes": b"x" * 65 + b"\n", "eof": False, "diagnostics": ("frame_too_large",), "continues": True},
        {"name": "original_too_long_EOF", "bytes": b"x" * 65, "eof": True, "diagnostics": ("frame_too_large", "channel_eof"), "continues": True},
        {"name": "incomplete_EOF", "bytes": b"shut", "eof": True, "diagnostics": ("incomplete_frame", "channel_eof"), "continues": True},
        {"name": "empty_EOF", "bytes": b"", "eof": True, "diagnostics": ("channel_eof",), "continues": True},
    )


def actual_missing_mcp_token_startup(ctx):
    host = ctx.host()
    protected = _protected(host)
    process = host.launch_role("mcp-without-session-token", ctx.engine.instance_id)
    identity = process.actual_identity()
    try:
        terminal = process.wait_actual_exit(timeout=10)
        assert terminal.actual_exit != 0 and terminal.forced is False and terminal.job_active_processes == 0
        assert process.wait_stderr_error_code("mcp_session_token_missing", timeout=1)
        assert not process.observed_ready_marker() and not terminal.stderr_role_marker_seen
        return {"actual_missing_token_code": "mcp_session_token_missing", "actual_exit": terminal.actual_exit}
    finally:
        if host.identity_is_live(identity):
            assert host.kill_owned_job(process, identity).job_active_processes == 0
        _check_protected(host, protected)


def run_cancellation_snapshot(ctx):
    with sqlite3.connect(ctx.engine.db.path.as_uri() + "?mode=ro", uri=True) as connection:
        return connection.execute("SELECT id,cancellation_requested,status,worker_id,lease_until_us FROM runs ORDER BY id").fetchall()


def actual_worker_control_boundaries(ctx):
    fixture = ctx.fixture("OS-worker-control")
    if not fixture.get("final_backend_control_descriptor"):
        raise CaseBlocked("final_Worker_control_instance_binding", "actual worker launch/diagnostic/finite EOF cleanup profile remains unbound")
    descriptor = ctx.bound_json(fixture["final_backend_control_descriptor"])
    assert descriptor["frame_hex"] == b"shutdown\n".hex() and descriptor["maximum_frame_bytes"] == 64
    host = ctx.host()
    protected = _protected(host)
    observed = []
    for spec in control_specs():
        process = host.launch_role("worker-private-control", ctx.engine.instance_id)
        identity = process.actual_identity()
        try:
            process.wait_ready(timeout=10)
            before_presence = _presence(ctx)
            before_runs = run_cancellation_snapshot(ctx)
            assert before_presence and before_presence["pid"] == identity.pid
            assert before_presence["active_run_id"] is None
            if any(row[2] in {"queued", "running"} or row[3] is not None or row[4] != 0 for row in before_runs):
                raise CaseBlocked("idle_waiting_only_control_instance", "control probe requires no eligible claim or active ordinary lease")
            process.write_owned_stdin(spec["bytes"])
            if spec["eof"]:
                process.close_owned_stdin()
            # One trusted stderr consumer preserves events without reflecting
            # input. Its bridge must supply exact structured role diagnostics.
            diagnostics = process.wait_stderr_diagnostics("worker_control", "worker", spec["diagnostics"], timeout=5)
            assert tuple(item["code"] for item in diagnostics) == spec["diagnostics"]
            assert all(set(item) == {"event", "scope", "code"} for item in diagnostics)
            ctx.wait(lambda: (_presence(ctx) or {}).get("heartbeat_us", 0) > before_presence["heartbeat_us"], seconds=5)
            after_presence = _presence(ctx)
            assert host.identity_is_live(identity) and process.actual_identity() == identity
            assert after_presence["pid"] == identity.pid and after_presence["worker_id"] == before_presence["worker_id"]
            assert after_presence["active_run_id"] is None
            assert run_cancellation_snapshot(ctx) == before_runs, "invalid frame or EOF changed a run/cancel/lease"
            if spec["eof"]:
                # Once the sole stdin writer is dropped, another legal frame
                # cannot be sent. An explicit owned Job cleanup is forced and
                # separately classified; it never proves a normal stop.
                close = host.kill_owned_job(process, identity)
                assert close.forced and close.job_active_processes == 0
                cleanup_mode = "forced_after_proven_EOF_survival"
            else:
                process.write_owned_stdin(b"shutdown\n")
                close = process.wait_actual_exit(timeout=15)
                assert close.actual_exit == 0 and not close.forced and close.job_active_processes == 0
                assert close.stderr_role_marker_seen
                cleanup_mode = "later_legal_shutdown_natural"
            observed.append({"case": spec["name"], "diagnostics": spec["diagnostics"],
                "identity": identity.to_evidence(), "heartbeat_before": before_presence["heartbeat_us"],
                "heartbeat_after": after_presence["heartbeat_us"], "cleanup_mode": cleanup_mode, "forced": close.forced})
        finally:
            if host.identity_is_live(identity):
                cleanup = host.kill_owned_job(process, identity)
                assert cleanup.job_active_processes == 0
            _check_protected(host, protected)
    # Default-off is its own actual branch: no private diagnostic reader.
    process = host.launch_role("worker-control-default-off", ctx.engine.instance_id)
    identity = process.actual_identity()
    try:
        process.wait_ready(timeout=10)
        before = _presence(ctx)
        rows = run_cancellation_snapshot(ctx)
        process.write_owned_stdin(b"shutdown\n")
        ctx.wait(lambda: (_presence(ctx) or {}).get("heartbeat_us", 0) > before["heartbeat_us"], seconds=5)
        assert host.identity_is_live(identity) and run_cancellation_snapshot(ctx) == rows
        assert process.observed_worker_control_diagnostics() == []
        cleanup = host.kill_owned_job(process, identity)
        assert cleanup.forced and cleanup.job_active_processes == 0
        observed.append({"case": "default_off", "cleanup_mode": "forced_after_proven_default_off_survival", "forced": True})
    finally:
        if host.identity_is_live(identity):
            assert host.kill_owned_job(process, identity).job_active_processes == 0
        _check_protected(host, protected)
    return {"actual_control_boundaries": observed}
