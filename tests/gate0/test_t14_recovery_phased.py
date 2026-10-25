"""Proposed real K/R/N case; fixed RV13 approval and final inputs required."""
import hashlib
import json
import os
import socket
import sqlite3
import time
import urllib.request
from pathlib import Path

import pytest

from t14_evidence import Journal
from t14_process_helpers import force_owned, launch, metadata, ready, read_rows, safe_env, save_process, tree, wait_for
from t14_phased_assertions import assert_K, assert_R, assert_N

REPO = Path(__file__).resolve().parents[2]

# Real K/R/N evidence needs approved freezes, real media and fresh output dirs.
REQUIRED_ENVIRONMENT = ("VIDEO_CREATOR_T14_SOURCE_FREEZE", "VIDEO_CREATOR_T14_CASES",
                        "VIDEO_CREATOR_T14_MANIFEST", "VIDEO_CREATOR_T14_AUDIO",
                        "VIDEO_CREATOR_T14_RUNTIME")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(data):
    return {name: read_rows(data, name) for name in [
        "runs", "steps", "operations", "worker_presence", "generated_attempts",
        "staging", "assets", "productions", "execution_bindings", "creative_revisions"]}


def events(folder):
    return [json.loads(path.read_text("utf8")) for path in sorted((folder / "Events").glob("Event*.json"))]


def file_fact(path):
    return {"path": str(path), "sha256": sha(path), "size": path.stat().st_size,
            "mtime_ns": path.stat().st_mtime_ns}


def flow_rows(data):
    with sqlite3.connect((data / "WorkflowState/LocalRender.sqlite").as_uri() + "?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute(
            "SELECT flow_uuid,method_name,state_json FROM flow_states ORDER BY rowid")]


def test_real_kill_original_effect_reconciliation_and_normal_quality_phased_v1():
    missing = [name for name in REQUIRED_ENVIRONMENT if not os.environ.get(name)]
    if missing:
        pytest.skip("T14 real K/R/N evidence is not configured; missing: " + ", ".join(missing)
                    + ". Set the variables and rerun (see docs/acceptance/criteria/COMMANDS.md, section "
                      "\"Gate0 drift repair\"); an approved source freeze and fresh output dirs are required.")
    freeze_path = Path(os.environ["VIDEO_CREATOR_T14_SOURCE_FREEZE"])
    freeze = json.loads(freeze_path.read_text("utf8"))
    assert freeze["root_launch_authorized"] and freeze["independent_criteria_approved"]
    assert freeze["criteria_revision"] == 2 and freeze["criteria_review_id"] == "RV14"
    assert freeze["criteria_version"] == "gate0-local-recovery-phased-evidence-v1"
    for name, expected in freeze["production_sources"].items():
        assert sha(REPO / name) == expected
    criterion = REPO / "docs/acceptance/criteria/gate0-local-recovery-phased-evidence-v1.json"
    assert sha(criterion) == freeze["approved_criteria_sha256"]
    for name, expected in freeze["approved_fixture_versions"].items():
        assert sha(REPO / name) == expected
    # Lazy product imports follow actual final-source and standard admission.
    from video_creator.application.assets import AssetService
    from video_creator.application.engine import EngineService
    from video_creator.cli.main import configured_media_validator
    from video_creator.domain.contracts import (
        AssetCandidate, Automation, CapabilityRoute, CreativeBriefInput,
        ExecutionPolicy, Money, ProductionInputs, ProductionRequest, SourceBinding)
    from video_creator.media.ffmpeg import FFmpegRuntime

    root = Path(os.environ["VIDEO_CREATOR_T14_CASES"])
    root.mkdir(parents=True, exist_ok=False)
    journal = Journal(root / "Observations", "actual_os_observation")
    manifest = Path(os.environ["VIDEO_CREATOR_T14_MANIFEST"])
    audio = Path(os.environ["VIDEO_CREATOR_T14_AUDIO"])
    runtime = json.loads(Path(os.environ["VIDEO_CREATOR_T14_RUNTIME"]).read_text("utf8"))
    before = {path: sha(Path(path)) for path in runtime["paths"]}
    journal.record("admitted_inputs", {"criteria_sha256": sha(criterion),
                   "production_sources": freeze["production_sources"], "runtime_before": before})
    resources = json.loads(manifest.read_text("utf8"))
    data = root / "Instance"
    engine = EngineService(data)
    validator = configured_media_validator(engine, Path(resources["ffmpeg_path"]), Path(resources["ffprobe_path"]))
    assets = AssetService(engine)
    staged = assets.stage_bytes("local-user", audio.read_bytes(), "audio/wav")
    asset = assets.import_asset("local-user", AssetCandidate(
        **staged, source="T14 authorized public self-created local stimulus",
        rights="authorized finite local experiment"), validator)
    engine.register_route(CapabilityRoute(
        route_id="gate0-local-render-v1", capability="render", source="owned_local",
        destination="local:gate0-local-render-v1", max_operation_cost=Money(amount="0"),
        cost_rule_version="local-free-v1", verified=True))
    request = ProductionRequest(
        goal="T14 independent original-effect phased recovery",
        inputs=ProductionInputs(asset_ids=(asset.asset_id,), source_text="Deterministic experimental local template only"),
        source_bindings=(SourceBinding(system="local", namespace="T14-public-experiment",
                                      confirmed_facts=("Free local experiment",)),),
        brief=CreativeBriefInput(target_duration_us=10_000_000, aspect_ratio="9:16"),
        automation=Automation(mode="interactive", max_revision_cycles=2),
        policy=ExecutionPolicy(allowed_provider_routes=("gate0-local-render-v1",)),
        outputs=("video", "mixed_audio"))
    accepted = engine.accept_production("local-user", "t14-first", request)
    journal.record("accepted", accepted.model_dump(mode="json"))
    python = REPO / ".venv/Scripts/python.exe"
    worker_script = REPO / "tests/gate0/T14Fixture/PhasedWorker.py"
    sibling = launch(REPO, [str(python), "-B", "-X", "utf8",
                     str(REPO / "tests/gate0/T13Fixture/OwnedSibling.py")],
                     safe_env(REPO), root / "Sibling")
    sibling_ready = ready(sibling, "sibling_ready")
    sibling_tree = tree(sibling["process"].pid)
    sibling_pids = [row["pid"] for row in sibling_tree]
    sibling_identity = metadata(sibling_pids)
    journal.record("real_sibling_created", {"ready": sibling_ready, "identity": sibling_identity,
                   "captured_tree": sibling_tree})
    assert sibling_identity
    assert any(row["pid"] == sibling_ready["actual_pid"] for row in sibling_tree)

    def start_worker(stage):
        folder = root / ("KilledWorker" if stage == "K" else "RecoveryWorker")
        latch, trace = folder / "Latch", folder / "Trace"
        child = launch(REPO, [
            str(python), "-B", "-X", "utf8", str(worker_script), "--data-dir", str(data),
            "--resource-manifest", str(manifest), "--target-run", accepted.run_id,
            "--trace-dir", str(trace), "--stage", stage, "--latch-dir", str(latch),
            "--approved-source-freeze", str(freeze_path)], safe_env(REPO), folder)
        captured = tree(child["process"].pid)
        journal.record(stage + "_worker_created", {"captured_tree": captured, "argv": child["argv"]})
        assert captured
        return child, latch, trace, captured

    old, latch, ktrace, old_tree = start_worker("K")
    new, new_tree, cleanup = None, [], {}
    try:
        wait_for(lambda: (latch / "LatchReady.json").is_file(), old, 45)
        returned_K = json.loads((latch / "LatchReady.json").read_text("utf8"))
        K = snapshot(data)
        old_tree = tree(old["process"].pid)
        target_identity = metadata([returned_K["pid"]])
        journal.record("K_before_kill", {"latch": returned_K, "snapshot": K,
                       "captured_tree": old_tree, "target_identity": target_identity})
        assert target_identity and any(row["pid"] == returned_K["pid"] and
            row["created_utc"] == target_identity[0]["created_utc"] for row in old_tree)
        output = data / "Staging" / K["generated_attempts"][0]["staging_id"]
        Kfile, Kflows = file_fact(output), flow_rows(data)
        journal.record("K_complete_file_and_flow", {"file": Kfile, "flow_rows": Kflows})
        assert not output.with_name(output.name + ".partial").exists()
        assert_K(K, Kfile, events(ktrace))
        kill = force_owned(old, old_tree)
        gone = metadata([row["pid"] for row in old_tree])
        journal.record("K_actual_kill_terminal", {"actual": kill, "captured_tree_after": gone})
        assert kill["tool_exit"] == 0 and not gone
        sibling_after_kill = metadata(sibling_pids)
        journal.record("K_live_sibling_after_kill", {"identity": sibling_after_kill})
        assert sibling_after_kill == sibling_identity
        expiry = K["runs"][0]["lease_until_us"]
        started, wall_start = time.monotonic(), time.time_ns() // 1000
        journal.record("K_wall_wait_start", {"lease_until_us": expiry, "wall_us": wall_start})
        while time.time_ns() // 1000 <= expiry + 150000:
            assert time.monotonic() - started < 40
            time.sleep(.1)
        wall_end = time.time_ns() // 1000
        journal.record("K_real_lease_expired", {"lease_until_us": expiry,
                       "wall_before_us": wall_start, "wall_after_us": wall_end,
                       "actual_wait_seconds": time.monotonic() - started})
        assert wall_end > expiry
        new, rlatch, ntrace, new_tree = start_worker("RN")
        wait_for(lambda: (rlatch / "LatchReady.json").is_file(), new, 30)
        returned_R = json.loads((rlatch / "LatchReady.json").read_text("utf8"))
        R, Rfile, Rflows = snapshot(data), file_fact(output), flow_rows(data)
        Ridentity = metadata([returned_R["pid"]])
        new_tree = tree(new["process"].pid)
        journal.record("R_original_finish_returned", {"return": returned_R,
                       "snapshot": R, "file": Rfile, "flow_rows": Rflows,
                       "identity": Ridentity, "captured_tree": new_tree})
        assert Ridentity and any(row["pid"] == returned_R["pid"] for row in new_tree)
        assert Rflows == Kflows
        assert_R(K, R, Kfile, Rfile, events(ntrace), returned_R)
        (rlatch / "ReleaseLatch").write_bytes(b"bounded-read-only-observer-release")
        journal.record("R_latch_released_for_real_normal_dispatch", {})
        normal_fence = None

        def quality_wait():
            nonlocal normal_fence
            value = snapshot(data)
            run = value["runs"][0]
            if run["fencing_token"] > R["runs"][0]["fencing_token"] and normal_fence is None:
                normal_fence = run["fencing_token"]
                journal.record("N_first_fresh_normal_fence_observed",
                               {"snapshot": value, "identity": metadata([returned_R["pid"]])})
            return value if run["status"] == "waiting_user" and run["worker_id"] is None and run["lease_until_us"] == 0 else None

        N = wait_for(quality_wait, new, 55)
        Nfile, Nflows = file_fact(output), flow_rows(data)
        journal.record("N_quality_wait_durable", {"snapshot": N, "file": Nfile,
                       "flow_rows": Nflows, "normal_fence": normal_fence,
                       "identity": metadata([returned_R["pid"]]), "worker_poll": new["process"].poll()})
        assert_N(K, R, N, Kfile, Nfile, events(ntrace), normal_fence, Kflows, Nflows)
        assert new["process"].poll() is None and metadata([returned_R["pid"]]) == Ridentity
        assert len(Nflows) >= 6 and {row["flow_uuid"] for row in Nflows} == {row["flow_uuid"] for row in Kflows}
        staging = root / "DecodeObservationStaging"
        staging.mkdir()
        decoder = FFmpegRuntime(Path(resources["ffmpeg_path"]), Path(resources["ffprobe_path"]), staging)
        decoded = []
        probes = {}
        for row in N["assets"]:
            original, copy = assets.content_path("local-user", row["id"]), staging / row["id"]
            copy.write_bytes(original.read_bytes())
            assert sha(copy) == row["sha256"] and copy.stat().st_size == row["size"]
            probe = decoder.probe(copy, decode=True)
            assert probe.decoded and probe.media_type == row["media_type"]
            assert sha(copy) == row["sha256"] and copy.stat().st_size == row["size"]
            probes[row["id"]] = probe
            decoded.append({"asset_id": row["id"], "sha256": row["sha256"], "probe": probe.model_dump(mode="json")})
        journal.record("N_real_independent_decoder", {"decoded_assets": decoded})
        expected_duration = {"local-shot-1": 4_000_000, "local-shot-2": 3_000_000,
                             "local-shot-3": 3_000_000, "local-compose": 10_000_000}
        for step in N["steps"]:
            if step["step_key"] == "local-plan":
                continue
            asset_ids = json.loads(step["result_json"])["asset_ids"]
            for index, asset_id in enumerate(asset_ids):
                probe = probes[asset_id]
                assert probe.duration_us == expected_duration[step["step_key"]]
                assert probe.has_audio
                if index == 0:
                    assert probe.has_video and probe.width == 720 and probe.height == 1280
                else:
                    assert not probe.has_video and probe.media_type == "audio/wav"
        with urllib.request.urlopen("http://127.0.0.1:" + str(sibling_ready["port"]), timeout=4) as response:
            assert response.status == 200
        assert metadata(sibling_pids) == sibling_identity
        journal.record("N_live_sibling_protected", {"identity_before": sibling_identity,
                       "identity_after": metadata(sibling_pids), "actual_http": 200})
        exit_code = new["process"].wait(timeout=85)
        new_gone = metadata([row["pid"] for row in new_tree])
        journal.record("N_worker_natural_terminal", {"actual_exit": exit_code,
                       "captured_tree_after": new_gone, "presence": read_rows(data, "worker_presence")})
        assert exit_code == 0 and not new_gone
        after = {path: sha(Path(path)) for path in runtime["paths"]}
        journal.record("runtime_after", {"runtime_after": after})
        assert before == after
    finally:
        if old["process"].poll() is None:
            cleanup["old"] = force_owned(old, old_tree)
        if new and new["process"].poll() is None:
            try:
                cleanup["new"] = new["process"].wait(timeout=85)
            except Exception:
                cleanup["new"] = force_owned(new, new_tree)
        sibling["process"].stdin.write(b"shutdown\n")
        sibling["process"].stdin.flush()
        cleanup["sibling_exit"] = sibling["process"].wait(timeout=8)
        cleanup["sibling_remaining"] = metadata(sibling_pids)
        with socket.socket() as connection:
            connection.settimeout(2)
            cleanup["sibling_port_closed"] = connection.connect_ex(
                ("127.0.0.1", sibling_ready["port"])) != 0
        journal.record("final_cleanup", cleanup)
        for child in [old, new, sibling]:
            if child:
                save_process(child)
        assert not cleanup["sibling_remaining"] and cleanup["sibling_port_closed"]
