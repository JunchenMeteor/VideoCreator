"""Independent real CLI lifecycle. Injected faults are explicitly nonbillable mechanism tests."""

import json
import queue
import threading
import time

import httpx
import pytest
import test_backend_gate0 as backend
from t6_cli_helpers import MARKER, Child, port_closed, write_receipt
from video_creator.application.engine import EngineService
from video_creator.application.executor import OperationExecutor
from video_creator.domain.contracts import ProductionRequest


@pytest.mark.parametrize("frame,diagnostic", [
    (b"unknown-synthetic-control\n", "frame_rejected"),
    (b"\xff\xfe\n", "frame_rejected"),
    (b"shutdown\r\n", "frame_rejected"),
    (b"a" * 64 + b"shutdown\n", "frame_too_large"),
])
def test_invalid_bytes_do_not_stop_and_oversize_suffix_cannot_escape(tmp_path, frame, diagnostic):
    child = Child(tmp_path / "Child")
    try:
        child.await_ready()
        child.send(frame)
        time.sleep(0.15)
        with child.api() as api:
            assert api.get("/api/v1/health").status_code == 200
        assert child.process.poll() is None and MARKER not in child.stderr
        child.send(b"shutdown\n")
        child.stopped()
        assert diagnostic.encode() in child.stderr
        assert b"unknown-synthetic-control" not in child.stderr
    finally:
        child.close()


@pytest.mark.parametrize("case", ["plain", "partial", "repeated", "early"])
def test_exact_lf_frame_and_partial_completion_really_stop(tmp_path, case):
    child = Child(tmp_path / "Child", early=b"shutdown\n" if case == "early" else None)
    try:
        child.await_ready()
        if case == "partial":
            child.send(b"shutdown")
            time.sleep(0.15)
            with child.api() as api:
                assert api.get("/api/v1/health").status_code == 200
            assert child.process.poll() is None and MARKER not in child.stderr
            child.send(b"\n")
        elif case != "early":
            child.send(b"shutdown\n" * (2 if case == "repeated" else 1))
        child.stopped()
    finally:
        child.close()


@pytest.mark.parametrize("controlled,partial", [(False, False), (True, False), (True, True)])
def test_default_and_eof_do_not_cancel_or_claim_a_clean_stop(tmp_path, controlled, partial):
    child = Child(tmp_path / "Child", controlled=controlled)
    try:
        child.await_ready()
        if not controlled:
            child.send(b"shutdown\n")
        elif partial:
            child.send(b"shutdown")
        child.process.stdin.close()
        time.sleep(0.2)
        with child.api() as api:
            health = api.get("/api/v1/health")
            assert health.status_code == 200 and not health.json()["worker_connected"]
        assert child.process.poll() is None and MARKER not in child.stderr
    finally:
        child.close()
    assert child.forced and child.process.returncode != 0 and MARKER not in child.stderr
    if controlled:
        assert b"channel_eof" in child.stderr
    if partial:
        assert b"incomplete_frame" in child.stderr


def test_real_startup_without_token_does_not_emit_ready_or_stop_success(tmp_path):
    child = Child(tmp_path / "Child", token=False)
    try:
        assert child.process.wait(timeout=10) == 1
        child.finish_readers()
        assert not child.stdout and MARKER not in child.stderr
        assert b"session_token_missing" in child.stderr
    finally:
        child.close()


def test_observed_reader_fd_and_real_cleanup_complete_before_marker(tmp_path):
    child = Child(tmp_path / "Child", mode="observe")
    try:
        child.await_ready()
        child.send(b"shutdown\n")
        child.stopped()
        evidence = json.loads((child.directory / "HostReceipt.json").read_text(encoding="utf-8"))
        assert evidence["pipe_closures"] and all(x["closed"] for x in evidence["pipe_closures"])
        assert evidence["actual_state"]["reader_completed"] and evidence["actual_state"]["serve_completed"]
        assert evidence["actual_state"]["lifespan_completed"] and evidence["listener_fd"] == -1
        assert not evidence["owned_live_threads"]
    finally:
        child.close()


def test_real_unknown_operation_and_shared_reserve_survive_stop_and_restart(tmp_path):
    directory = tmp_path / "Child"
    engine = EngineService(directory / "Instance")
    backend.configure(engine)
    accepted, lease = backend.lease_and_step(engine)
    calls = []

    def timeout_after_synthetic_accept(permit, _secret):
        calls.append(permit.operation_id)
        raise TimeoutError("Synthetic response loss: no paid/provider request")

    OperationExecutor(engine).execute(lease, backend.intent(), timeout_after_synthetic_accept)

    def persisted():
        fresh = EngineService(engine.db.data_dir)
        with fresh.db.connect() as db:
            operations = [dict(row) for row in db.execute("SELECT * FROM operations ORDER BY id")]
            production = dict(db.execute("SELECT status FROM productions WHERE id=?", (accepted.production_id,)).fetchone())
            cancellation = db.execute("SELECT cancellation_requested FROM runs WHERE id=?", (accepted.run_id,)).fetchone()[0]
        return {"instance_id": fresh.instance_id, "budget": fresh.budget_status("test-shared"),
                "operations": operations, "production": production, "run_cancellation_requested": cancellation}

    before = persisted()
    assert before["budget"]["reserved"]["amount"] == "0.2"
    assert before["operations"][0]["status"] == "unknown"
    stops = []
    for index in range(2):
        child = Child(directory)
        try:
            child.await_ready()
            assert child.ready["instance_id"] == before["instance_id"]
            with child.api() as api:
                assert api.get("/api/v1/health").status_code == 200
            child.send(b"shutdown\n")
            child.stopped()
            after = persisted()
            stops.append({"cycle": index, "after": after, "exit_code": child.process.returncode})
            assert after == before
        finally:
            child.close()
    assert len(calls) == 1
    write_receipt(tmp_path / "UnknownReserveReceipt.json", {"before": before, "stops": stops,
                  "synthetic_driver_calls": len(calls), "paid_provider_calls": 0})


def test_real_sse_observes_event_then_natural_eof_before_success(tmp_path):
    child = Child(tmp_path / "Child", authorize=True)
    received, errors = [], []
    started, finished = threading.Event(), threading.Event()
    try:
        child.await_ready()
        with child.api() as api:
            accepted = api.post("/api/v1/productions", json=ProductionRequest(goal="T6 public local SSE test").model_dump(mode="json"), headers={"Idempotency-Key": "t6-sse"})
            assert accepted.status_code == 202, accepted.text
            run_id = accepted.json()["run_id"]

        def consume():
            try:
                with child.api() as api, api.stream("GET", f"/api/v1/runs/{run_id}/events", headers={"Accept": "text/event-stream"}) as stream:
                    assert stream.status_code == 200
                    for line in stream.iter_lines():
                        received.append(line)
                        if line.startswith("data:"):
                            started.set()
            except (httpx.HTTPError, AssertionError) as error:
                errors.append(type(error).__name__)
            finally:
                finished.set()

        reader = threading.Thread(target=consume)
        reader.start()
        assert started.wait(timeout=8), errors
        child.send(b"shutdown\n")
        child.stopped()
        reader.join(timeout=3)
        assert finished.is_set() and not reader.is_alive() and not errors
        assert any(line.startswith("data:") for line in received)
        engine = EngineService(child.data_dir)
        detail = engine.get_production("local-user", accepted.json()["production_id"])
        assert detail.status != "cancelled"
        write_receipt(tmp_path / "SseDrainReceipt.json", {"event_lines": received, "errors": errors,
                       "natural_eof": finished.is_set(), "production_status": detail.status, "exit_code": 0})
    finally:
        child.close()


@pytest.mark.parametrize("mode", ["slow-http", "timeout-http"])
def test_real_inflight_http_drains_or_reports_actual_timeout(tmp_path, mode):
    child = Child(tmp_path / "Child", mode=mode, authorize=True)
    responses, errors = [], []
    try:
        child.await_ready()

        def request():
            try:
                with child.api() as api:
                    responses.append(api.get("/api/v1/projects").status_code)
            except httpx.HTTPError as error:
                errors.append(type(error).__name__)

        worker = threading.Thread(target=request)
        worker.start()
        deadline = time.monotonic() + 5
        observed = False
        while time.monotonic() < deadline:
            try:
                name, line = child.lines.get(timeout=0.2)
            except queue.Empty:
                continue
            if name == "stderr" and b"t6_request_started" in line:
                observed = True
                break
        assert observed, "Must stop while actual HTTP handler is still in flight"
        child.send(b"shutdown\n")
        if mode == "slow-http":
            child.stopped()
            worker.join(timeout=3)
            assert responses == [200] and not errors
        else:
            assert child.process.wait(timeout=15) == 1
            child.finish_readers()
            worker.join(timeout=3)
            assert MARKER not in child.stderr and b"shutdown_timeout" in child.stderr
            assert port_closed(child.ready["base_url"])
        assert not worker.is_alive()
        write_receipt(tmp_path / "HttpDrainReceipt.json", {"mode": mode, "real_request_started": observed,
                      "responses": responses, "errors": errors, "exit_code": child.process.returncode,
                      "synthetic_handler_delay_seconds": 0.8,
                      "synthetic_stop_timeout_seconds": 0.35 if mode == "timeout-http" else None})
    finally:
        child.close()


def test_actual_lifespan_cleanup_exception_is_nonzero_and_never_success(tmp_path):
    child = Child(tmp_path / "Child", mode="cleanup-failure")
    try:
        child.await_ready()
        child.send(b"shutdown\n")
        assert child.process.wait(timeout=15) == 1
        child.finish_readers()
        assert MARKER not in child.stderr and b"api_cleanup_incomplete" in child.stderr
        assert port_closed(child.ready["base_url"])
        evidence = json.loads((child.directory / "HostReceipt.json").read_text(encoding="utf-8"))
        assert evidence["pipe_closures"] and all(x["closed"] for x in evidence["pipe_closures"])
    finally:
        child.close()
