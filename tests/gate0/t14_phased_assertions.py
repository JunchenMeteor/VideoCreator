"""Phased invariants; inputs must be independently persisted actual observations."""
import collections
import hashlib
import json
import os
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

OP_IDENTITY = ("id", "production_id", "run_id", "step_key", "dedupe_key", "input_sha256", "route_json", "created_at_us")
ALLOCATION_IDENTITY = ("id", "run_id", "step_key", "input_sha256", "output_key", "staging_id", "allocation_fence", "source", "rights")


def same_fields(before, after, names):
    for name in names:
        assert after[name] == before[name], name + " original identity changed"


def renders(events):
    return [event["facts"] for event in events if event["event"] == "render_begin"]


def normalized_path(path):
    return os.path.normcase(str(Path(path).resolve(strict=False)))


def assert_original_probe(events, original_file, target_run_id, expected_pid):
    """A real returned call must have decoded this exact original complete file."""
    begins = {}
    returned = {}
    for event in events:
        if event["event"] not in {"decode_begin", "decode_returned", "decode_raised"}:
            continue
        fact = event["facts"]
        call_id = fact["call_id"]
        if event["event"] == "decode_begin":
            assert call_id not in begins
            begins[call_id] = fact
        else:
            assert call_id not in returned and call_id in begins
            returned[call_id] = (event["event"], fact)
    exact_successes = []
    for call_id, (kind, fact) in returned.items():
        initial = begins[call_id]
        before, after = fact["input_before"], fact["input_after"]
        assert before == initial["input_before"] and fact["pid"] == initial["pid"]
        assert fact["target_run_id"] == initial["target_run_id"]
        if before.get("path") != normalized_path(original_file["path"]):
            continue
        assert fact["target_run_id"] == target_run_id
        assert fact["pid"] == expected_pid
        assert before.get("inside_staging") is True and after.get("inside_staging") is True
        assert "observation_error" not in before and "observation_error" not in after
        assert before == after and fact["changed_during_call"] is False
        assert before["sha256"] == original_file["sha256"] and before["size"] == original_file["size"]
        assert before["mtime_ns"] == original_file["mtime_ns"]
        assert kind == "decode_returned" and fact["decode_requested"] is True
        probe = fact["actual_public_probe"]
        assert probe["decoded"] is True and probe["media_type"] == "video/mp4"
        assert probe["duration_us"] == 4_000_000 and probe["width"] == 720 and probe["height"] == 1280
        assert probe["has_video"] is True and probe["has_audio"] is True
        exact_successes.append(call_id)
    assert exact_successes, "No genuine decode call is bound to K's original complete file"
    return exact_successes


def assert_K(snapshot, file, events):
    assert len(snapshot["operations"]) == len(snapshot["generated_attempts"]) == 1
    operation, allocation = snapshot["operations"][0], snapshot["generated_attempts"][0]
    assert operation["status"] == "submitting" and operation["settled"] == 0 and operation["observation_json"] is None
    stage = next(item for item in snapshot["staging"] if item["id"] == allocation["staging_id"])
    assert stage["status"] == "ready" and stage["sha256"] == file["sha256"] and stage["size"] == file["size"]
    assert len(snapshot["assets"]) == 1
    assert collections.Counter(event["step_key"] for event in renders(events)) == {"local-shot-1": 1}
    assert any(event["event"] == "render_returned" for event in events)


def assert_R(K, R, Kfile, Rfile, events, returned):
    assert returned["original_method_succeeded"]
    assert len(R["operations"]) == len(R["generated_attempts"]) == 1
    same_fields(K["operations"][0], R["operations"][0], OP_IDENTITY)
    same_fields(K["generated_attempts"][0], R["generated_attempts"][0], ALLOCATION_IDENTITY)
    assert Rfile == Kfile and R["steps"] == K["steps"] and R["assets"] == K["assets"]
    operation = R["operations"][0]
    assert operation["status"] == "succeeded" and operation["settled"] == 1
    assert operation["actual_units"] == operation["reserved_units"] == 0 and operation["cost_evidence"] == "confirmed_no_charge"
    manifest = json.loads(operation["observation_json"])["result_json"]["generated_files"]
    assert len(manifest) == 1 and manifest[0]["attempt_id"] == K["generated_attempts"][0]["id"]
    assert manifest[0]["candidate"]["sha256"] == Kfile["sha256"] and manifest[0]["candidate"]["size"] == Kfile["size"]
    original_allocation = K["generated_attempts"][0]
    original_stage = next(stage for stage in K["staging"] if stage["id"] == original_allocation["staging_id"])
    candidate = manifest[0]["candidate"]
    assert candidate["staging_id"] == original_allocation["staging_id"]
    assert Path(Kfile["path"]).name == candidate["staging_id"]
    assert candidate["media_type"] == original_stage["media_type"] == "video/mp4"
    assert candidate["source"] == original_allocation["source"] and candidate["rights"] == original_allocation["rights"]
    run = R["runs"][0]
    assert run["status"] == "queued" and run["worker_id"] is None and run["lease_until_us"] == 0
    assert run["fencing_token"] == returned["lease"]["fencing_token"]
    presence = R["worker_presence"][0]
    assert presence["state"] == "idle" and presence["active_run_id"] is None
    assert R["execution_bindings"] == K["execution_bindings"]
    assert not renders(events)
    assert not any(event["event"] in {"allocate_call_begin", "step_commit_call_begin", "asset_commit_call_begin", "plain_step_commit_call_begin"} for event in events)
    assert_original_probe(events, Kfile, K["runs"][0]["id"], returned["pid"])


def assert_N(K, R, N, Kfile, Nfile, events, normal_fence, Kflows, Nflows):
    assert Nfile == Kfile
    assert len(N["steps"]) == 5 and all(step["status"] == "succeeded" for step in N["steps"])
    assert {step["step_key"] for step in N["steps"]} == {"local-plan", "local-shot-1", "local-shot-2", "local-shot-3", "local-compose"}
    assert len(N["operations"]) == 4 and all(op["status"] == "succeeded" and op["settled"] == 1 and op["actual_units"] == op["reserved_units"] == 0 for op in N["operations"])
    assert collections.Counter(op["step_key"] for op in N["operations"]) == {"local-shot-1": 1, "local-shot-2": 1, "local-shot-3": 1, "local-compose": 1}
    assert len(N["generated_attempts"]) == 5
    outputs = collections.defaultdict(list)
    for allocation in N["generated_attempts"]:
        outputs[allocation["step_key"]].append(allocation["output_key"])
    assert dict(outputs) == {"local-shot-1": ["video"], "local-shot-2": ["video"], "local-shot-3": ["video"], "local-compose": ["video", "mixed"]}
    original = next(op for op in N["operations"] if op["id"] == K["operations"][0]["id"])
    same_fields(K["operations"][0], original, OP_IDENTITY)
    assert original["observation_json"] == R["operations"][0]["observation_json"]
    allocation = next(item for item in N["generated_attempts"] if item["id"] == K["generated_attempts"][0]["id"])
    same_fields(K["generated_attempts"][0], allocation, ALLOCATION_IDENTITY)
    assert len([op for op in N["operations"] if op["dedupe_key"] == original["dedupe_key"]]) == 1
    assert collections.Counter(event["step_key"] for event in renders(events)) == {"local-shot-2": 1, "local-shot-3": 1, "local-compose": 1}
    run = N["runs"][0]
    assert run["status"] == "waiting_user" and run["worker_id"] is None and run["lease_until_us"] == 0
    assert normal_fence > R["runs"][0]["fencing_token"] and run["fencing_token"] == normal_fence
    assert N["execution_bindings"] == K["execution_bindings"] and len(N["assets"]) == 6
    assert_media_lineage(N, Kflows, Nflows)


def assert_media_lineage(N, Kflows, Nflows):
    """Exact ordered Operation -> allocation -> staging -> Asset -> Step -> Flow."""
    run = N["runs"][0]
    run_id, production_id = run["id"], run["production_id"]
    owner = next(row["owner"] for row in N["productions"] if row["id"] == production_id)
    steps = {step["step_key"]: step for step in N["steps"]}
    assets = {asset["id"]: asset for asset in N["assets"]}
    staging = {stage["id"]: stage for stage in N["staging"]}
    expected_outputs = {
        "local-shot-1": [("video", "video/mp4")],
        "local-shot-2": [("video", "video/mp4")],
        "local-shot-3": [("video", "video/mp4")],
        "local-compose": [("video", "video/mp4"), ("mixed", "audio/wav")],
    }
    ordered_results = {}
    all_output_ids = []
    for key, expected in expected_outputs.items():
        operations = [op for op in N["operations"] if op["step_key"] == key]
        allocations = [item for item in N["generated_attempts"] if item["step_key"] == key]
        assert len(operations) == 1 and len(allocations) == len(expected)
        op = operations[0]
        step = steps[key]
        assert op["run_id"] == step["run_id"] == run_id and op["production_id"] == production_id
        assert op["input_sha256"] == step["input_sha256"]
        observation = json.loads(op["observation_json"])
        manifest = observation["result_json"]["generated_files"]
        assert len(manifest) == len(allocations)
        refs = []
        for index, (item, allocation, specification) in enumerate(zip(manifest, allocations, expected, strict=True)):
            output_key, media_type = specification
            assert allocation["run_id"] == run_id and allocation["input_sha256"] == op["input_sha256"]
            assert allocation["output_key"] == output_key
            assert item["attempt_id"] == allocation["id"]
            candidate = item["candidate"]
            assert candidate["staging_id"] == allocation["staging_id"]
            stage = staging[allocation["staging_id"]]
            assert stage["status"] == "imported" and stage["owner"] == owner
            assert candidate["media_type"] == stage["media_type"] == media_type
            assert candidate["source"] == allocation["source"] and candidate["rights"] == allocation["rights"]
            assert candidate["sha256"] == stage["sha256"] and candidate["size"] == stage["size"]
            asset_id = stage["asset_id"]
            asset = assets[asset_id]
            assert asset["owner"] == owner
            for field in ("sha256", "size", "media_type", "source", "rights"):
                assert asset[field] == candidate[field], key + " output " + str(index) + " Asset mismatch: " + field
            stored_probe = json.loads(asset["probe_json"])
            assert stored_probe["decoded"] is True and stored_probe["media_type"] == media_type
            refs.append(asset_id)
        step_value = json.loads(step["result_json"])
        assert step_value["asset_ids"] == refs, key + " Step references wrong ordered Assets"
        assert step_value["result"]["generated_files"] == manifest, key + " Step manifest differs from original Operation"
        ordered_results[key] = refs
        all_output_ids.extend(refs)
    assert len(all_output_ids) == len(set(all_output_ids)) == 5, "An Asset is shared or used to pad unrelated output counts"
    plan_result = json.loads(steps["local-plan"]["result_json"])
    assert plan_result["asset_ids"] == []
    plan_revision_id = plan_result["result"]["revision_id"]
    revisions = {row["id"]: row for row in N["creative_revisions"]}
    plan_revision = revisions[plan_revision_id]
    assert plan_revision["run_id"] == run_id and plan_revision["production_id"] == production_id and plan_revision["kind"] == "plan"
    plan_body = json.loads(plan_revision["body"])
    assert plan_body["revision_id"] == plan_revision_id and plan_body["body"] == plan_result["result"]["plan"]
    binding_row = next(row for row in N["execution_bindings"] if row["run_id"] == run_id)
    binding = json.loads(binding_row["body"])
    assert binding["run_id"] == run_id and binding["production_id"] == production_id
    canonical_binding = json.dumps(binding, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    binding_hash = hashlib.sha256(canonical_binding.encode("utf8")).hexdigest()
    flow_uuid = str(uuid5(NAMESPACE_URL, "video-creator:" + canonical_binding))
    shot_refs = [ordered_results["local-shot-" + str(index)][0] for index in (1, 2, 3)]
    output_refs = ordered_results["local-compose"]
    assert Kflows and len(Nflows) >= 6
    assert {row["flow_uuid"] for row in Kflows} == {flow_uuid}
    assert {row["flow_uuid"] for row in Nflows} == {flow_uuid}
    observed_methods = set()
    for row in [*Kflows, *Nflows]:
        state = json.loads(row["state_json"])
        assert state["id"] == flow_uuid and state["run_id"] == run_id
        assert state["binding_sha256"] == binding_hash and state["plan_revision_id"] == plan_revision_id
        method = row["method_name"]
        if row in Nflows:
            observed_methods.add(method)
        if "shot_asset_ids" in state:
            refs = state["shot_asset_ids"]
            assert refs == shot_refs[:len(refs)]
            assert 0 < len(refs) <= 3
        if method in {"local-shot-1", "local-shot-2", "local-shot-3"}:
            assert state["shot_asset_ids"] == shot_refs[:int(method.rsplit("-", 1)[1])]
        if method in {"compose", "review_pending"}:
            assert state["shot_asset_ids"] == shot_refs and state["output_asset_ids"] == output_refs
        if "output_asset_ids" in state:
            assert state["output_asset_ids"] == output_refs
        if method == "review_pending":
            assert state["outcome"] == "waiting_user" and state["quality_revision_id"] == run["waiting_revision_id"]
    assert {"prepare", "local-shot-1", "local-shot-2", "local-shot-3", "compose", "review_pending"} <= observed_methods
    quality_revision = revisions[run["waiting_revision_id"]]
    assert quality_revision["run_id"] == run_id and quality_revision["kind"] == "quality"
    quality_body = json.loads(quality_revision["body"])["body"]
    assert quality_body["plan_revision_id"] == plan_revision_id and quality_body["asset_ids"] == shot_refs + output_refs
    return ordered_results
