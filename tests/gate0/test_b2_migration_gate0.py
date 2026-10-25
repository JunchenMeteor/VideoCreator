"""Real two-process migration and kill recovery. No upstream calls or credentials."""

import json
import os
import queue
import sqlite3
import subprocess
import sys
import threading
from pathlib import Path

import pytest
from schema_contract import CURRENT_SCHEMA_VERSION, assert_migration_catalog_matches_engine
from video_creator.application.engine import EngineService, digest
from video_creator.domain.contracts import (
    CapabilityRoute,
    ExecutionPolicy,
    Money,
    OperationIntent,
    OperationObservation,
    ProductionRequest,
)
from video_creator.infrastructure.database import Database

ROOT = Path(__file__).resolve().parents[2]


def spawn(data_dir, mode, release):
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith("VIDEO_CREATOR_SECRET_") and key != "VIDEO_CREATOR_API_TOKEN"}
    environment["PYTHONPATH"] = str(ROOT / "services/engine/src")
    environment["PYTHONUTF8"] = "1"
    environment["VIDEO_CREATOR_MIGRATIONS_DIR"] = str(ROOT / "services/engine/migrations")
    return subprocess.Popen([sys.executable, str(ROOT / "tools/testing/migration_child.py"),
        str(data_dir), mode, str(release)], env=environment, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, encoding="utf-8")


def next_event(process):
    lines = queue.Queue()
    threading.Thread(target=lambda: lines.put(process.stdout.readline()), daemon=True).start()
    line = lines.get(timeout=20)
    assert line, "Migration child exited before the requested boundary"
    return json.loads(line)


def save(tmp_path, name, body):
    (tmp_path / name).write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8", newline="\n")


def snapshot(data_dir):
    with sqlite3.connect(data_dir / "Metadata.sqlite") as connection:
        tables = [row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        return {table: {"columns": [row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')],
            "rows": connection.execute(f'SELECT * FROM "{table}" ORDER BY rowid').fetchall()} for table in tables}


def assert_preserved(original, after):
    """Every original row survives with identical values and order.

    Later migrations legitimately append rows (for example new metadata keys),
    so the projection of an original table must contain its original rows as an
    ordered subsequence: a changed, removed, reordered or duplicated row fails.
    """
    for table, record in original.items():
        indexes = [after[table]["columns"].index(column) for column in record["columns"]]
        projected = [tuple(row[index] for index in indexes) for row in after[table]["rows"]]
        position = 0
        for row in record["rows"]:
            while position < len(projected) and projected[position] != row:
                position += 1
            assert position < len(projected), f"Persistent rows changed during migration: {table}: {row!r}"
            position += 1


def seed_v1(data_dir):
    data_dir.mkdir()
    with sqlite3.connect(data_dir / "Metadata.sqlite") as connection:
        connection.executescript((ROOT / "services/engine/migrations/0001_ledger.sql").read_text(encoding="utf-8"))
        connection.execute("INSERT INTO metadata VALUES('instance_id','test-preserved-v1')")
        connection.execute("INSERT INTO projects(id,owner) VALUES('project','local-user')")
        connection.execute("INSERT INTO budget_groups VALUES('shared','local-user','CNY',20000000,77518,200000)")
        connection.execute("INSERT INTO productions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            "production", "project", "local-user", "one", digest("public"), "revision", "{}",
            "needs_reconciliation", "shared", 20000000, 77518, 200000, 0, 1))
        connection.execute("INSERT INTO runs(id,production_id,status,lease_until_us,fencing_token,attempt) VALUES('run','production','needs_reconciliation',1000000,1,1)")
        connection.execute("INSERT INTO steps VALUES('run','creative',?,'running',1,NULL)", (digest("public input"),))
        connection.execute("INSERT INTO operations VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            "unknown-operation", "production", "run", "creative", "one", digest("public prompt"),
            "{}", "unknown", 200000, 0, None, "unknown", "synthetic-upstream", None, 1, 1))
    return snapshot(data_dir)


def test_first_two_process_initialization_never_downgrades_schema(tmp_path):
    data_dir = tmp_path / "ConcurrentInstance"
    release = tmp_path / "ReleaseFirst.json"
    first = spawn(data_dir, "paused-first", release)
    contender = None
    receipt = {}
    try:
        boundary = next_event(first)
        assert boundary["phase"] == "initial_schema_before_write", boundary
        contender = spawn(data_dir, "contender", release)
        receipt["first_boundary"] = boundary
        if boundary["in_transaction"]:
            attempt = next_event(contender)
            assert attempt["phase"] == "writer_attempt"
            assert contender.poll() is None
            receipt["contender_attempt"] = attempt
            release.write_text("{}\n", encoding="utf-8", newline="\n")
            contender_stdout, contender_stderr = contender.communicate(timeout=20)
        else:
            contender_stdout, contender_stderr = contender.communicate(timeout=20)
            release.write_text("{}\n", encoding="utf-8", newline="\n")
        first_stdout, first_stderr = first.communicate(timeout=20)
        with sqlite3.connect(data_dir / "Metadata.sqlite") as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            column_count = sum(row[1] == "cancellation_requested" for row in connection.execute("PRAGMA table_info(runs)"))
        receipt.update(first_exit=first.returncode, contender_exit=contender.returncode,
            first_stdout=first_stdout, first_stderr=first_stderr,
            contender_stdout=contender_stdout, contender_stderr=contender_stderr,
            final_version=version, cancellation_columns=column_count, provider_calls=0)
        save(tmp_path, "TwoProcessReceipt.json", receipt)
        assert first.returncode == contender.returncode == 0, receipt
        assert_migration_catalog_matches_engine()
        assert version == CURRENT_SCHEMA_VERSION and column_count == 1
    finally:
        for process in [first, contender]:
            if process is not None and process.poll() is None:
                process.kill()
                process.communicate(timeout=10)


@pytest.mark.parametrize("version,phase", [(0, "kill-create"), (0, "kill-alter"), (1, "kill-alter")])
def test_actual_kill_rolls_back_whole_migration_and_preserves_rows(tmp_path, version, phase):
    data_dir = tmp_path / "KilledMigrationInstance"
    original = seed_v1(data_dir) if version == 1 else {}
    process = spawn(data_dir, phase, tmp_path / "NeverRelease.json")
    try:
        boundary = next_event(process)
        assert boundary["in_transaction"] is True
        process.kill()
        _stdout, stderr = process.communicate(timeout=10)
        assert process.returncode != 0
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=10)
    before_restart = snapshot(data_dir)
    with sqlite3.connect(data_dir / "Metadata.sqlite") as connection:
        rolled_back_version = connection.execute("PRAGMA user_version").fetchone()[0]
    assert rolled_back_version == version
    assert before_restart == original
    restarted = Database(data_dir)
    with restarted.connect() as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == CURRENT_SCHEMA_VERSION
    assert_preserved(original, snapshot(data_dir))
    save(tmp_path, "MigrationKillReceipt.json", {"version_before": version, "boundary": boundary,
        "actual_child_killed": True, "child_exit": process.returncode, "stderr": stderr,
        "rolled_back_version": rolled_back_version, "original_rows_preserved": True,
        "restart_version": CURRENT_SCHEMA_VERSION, "provider_calls": 0})


def test_v1_unknown_operation_and_reservations_survive_upgrade(tmp_path):
    data_dir = tmp_path / "V1UnknownInstance"
    original = seed_v1(data_dir)
    database = Database(data_dir)
    assert_preserved(original, snapshot(data_dir))
    with database.connect() as connection:
        operation = connection.execute("SELECT * FROM operations WHERE id='unknown-operation'").fetchone()
        assert operation["actual_units"] is None and operation["reserved_units"] == 200000
        assert operation["cost_evidence"] == "unknown" and operation["settled"] == 0
    # A second initialization must preserve every current-schema row exactly,
    # including the unknown operation.
    upgraded = snapshot(data_dir)
    Database(data_dir)
    assert snapshot(data_dir) == upgraded


def test_v2_unknown_operation_cancel_and_reconcile_after_restart(tmp_path):
    data_dir = tmp_path / "V2UnknownInstance"
    engine = EngineService(data_dir, clock=lambda: 1_000_000)
    engine.authorize_budget_group("shared", Money(amount="20"))
    engine.register_route(CapabilityRoute(route_id="synthetic", capability="text", source="owned_local",
        destination="local:synthetic", verified=True, max_operation_cost=Money(amount="0.2"), cost_rule_version="synthetic-v1"))
    accepted = engine.accept_production("local-user", "one", ProductionRequest(goal="public test", policy=ExecutionPolicy(
        allowed_provider_routes=("synthetic",), budget_group_id="shared", max_cost=Money(amount="20"))))
    lease = engine.acquire_run("first", run_id=accepted.run_id, lease_seconds=1)
    engine.begin_step(lease, "creative", digest("public input"))
    intent = OperationIntent(step_key="creative", dedupe_key="one", route_id="synthetic", input_sha256=digest("public prompt"), reserved_cost=Money(amount="0.2"))
    operation = engine.prepare_operation(lease, intent)
    engine.claim_operation(lease, operation["id"])
    engine.observe_operation(lease, operation["id"], OperationObservation(status="succeeded", external_id="synthetic",
        result_json={"content": "synthetic already accepted"}))
    engine.cancel_production("local-user", accepted.production_id)
    before = snapshot(data_dir)
    restarted = EngineService(data_dir, clock=lambda: 4_000_000)
    assert snapshot(data_dir) == before
    reconciliation = restarted.acquire_run("reconciler", run_id=accepted.run_id, reconciliation=True)
    assert reconciliation is not None
    assert restarted.get_production("local-user", accepted.production_id).cost.reserved.amount == Money(amount="0.2").amount
    restarted.observe_operation(reconciliation, operation["id"], OperationObservation(status="succeeded", external_id="synthetic",
        actual_cost=Money(amount="0.05"), cost_evidence="provider_receipt", result_json={"content": "synthetic already accepted"}), reconciliation=True)
    detail = restarted.get_production("local-user", accepted.production_id)
    assert detail.cost.spent.amount == Money(amount="0.05").amount and detail.cost.reserved.amount == 0
    with restarted.db.connect() as connection:
        assert connection.execute("SELECT status FROM runs WHERE id=?", (accepted.run_id,)).fetchone()[0] == "cancelled"
