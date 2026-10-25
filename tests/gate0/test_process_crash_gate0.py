"""Real child-process termination; upstream responses/creative content are synthetic."""

import json
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path

import pytest
from video_creator.application.assets import AssetService
from video_creator.application.engine import EngineService, digest
from video_creator.domain.contracts import AssetCandidate

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("phase", ["dispatch", "step", "object"])
def test_actual_process_kill_at_persistence_boundary_is_recoverable(tmp_path, phase):
    data_dir = tmp_path / "KilledInstance"
    environment = {key: value for key, value in os.environ.items() if not key.startswith("VIDEO_CREATOR_SECRET_")}
    environment["PYTHONPATH"] = str(ROOT / "services" / "engine" / "src")
    environment["PYTHONUTF8"] = "1"
    process = subprocess.Popen([sys.executable, str(ROOT / "tools" / "testing" / "crash_child.py"), phase, str(data_dir)],
                               env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
    lines = queue.Queue()
    threading.Thread(target=lambda: lines.put(process.stdout.readline()), daemon=True).start()
    try:
        boundary = json.loads(lines.get(timeout=20))
        assert boundary["phase"] == phase
    finally:
        process.kill()
        _remaining_stdout, _stderr = process.communicate(timeout=10)
    assert process.returncode is not None
    (tmp_path / "CrashReceipt.json").write_text(json.dumps({"phase": phase, "actual_child_killed": True,
        "provider_calls": 0, "boundary": boundary, "child_exit_code": process.returncode,
        "creative_generation": "not_tested", "upstream_acceptance": "synthetic_only"}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    restarted = EngineService(data_dir, clock=lambda: 4_000_000)
    if phase == "object":
        asset = AssetService(restarted).import_asset("local-user", AssetCandidate.model_validate(boundary["candidate"]))
        assert AssetService(restarted).content_path("local-user", asset.asset_id).is_file()
        assert asset.sha256 == boundary["candidate"]["sha256"]
        return
    recovery = restarted.recover()
    assert recovery["recovered_runs"] == 1
    if phase == "dispatch":
        assert recovery["needs_reconciliation"] == 1
        detail = restarted.get_production("local-user", boundary["production_id"])
        assert detail.operations[0].status == "unknown" and detail.operations[0].actual_cost is None
        assert detail.cost.reserved.amount > 0
        return
    lease = restarted.acquire_run("new-worker", run_id=boundary["run_id"])
    assert lease is not None
    saved = restarted.begin_step(lease, "creative", digest("public input"))
    assert saved["status"] == "succeeded"
    assert json.loads(saved["result_json"])["result"]["revision_ref"] == "synthetic-not-generated"
