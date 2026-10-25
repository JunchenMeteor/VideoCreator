"""Synthetic fixture association checks only, no product/FFmpeg/SQLite execution."""
import copy
import hashlib
import json
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from uuid import NAMESPACE_URL, uuid5

REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(REPO / "tests/gate0"), str(REPO / "tests/gate0/T14Fixture")]
from t14_evidence import Journal
from ProbeTrace import wrap_probe
from t14_phased_assertions import assert_original_probe, assert_media_lineage

ROOT = Path(os.environ["VIDEO_CREATOR_T14_ASSOCIATION_SANITY"])
ROOT.mkdir(parents=True, exist_ok=False)


def synthetic_lineage():
    run_id, production_id, owner = "synthetic-run", "synthetic-production", "fixture-owner"
    plan_id, quality_id = "synthetic-plan", "synthetic-quality"
    binding = {"run_id": run_id, "production_id": production_id, "request_revision_id": "fixture-request",
               "workflow_version": "gate0-local-render-v1", "input_assets": [],
               "resource_manifest_sha256": "f" * 64}
    canonical = json.dumps(binding, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    flow_id = str(uuid5(NAMESPACE_URL, "video-creator:" + canonical))
    N = {"runs": [{"id": run_id, "production_id": production_id, "waiting_revision_id": quality_id}],
         "productions": [{"id": production_id, "owner": owner}], "steps": [], "assets": [],
         "staging": [], "generated_attempts": [], "operations": [],
         "execution_bindings": [{"run_id": run_id, "body": canonical}], "creative_revisions": []}
    plan = {"experiment": True, "synthetic_fixture_not_actual_media": True}
    N["steps"].append({"run_id": run_id, "step_key": "local-plan",
        "result_json": json.dumps({"asset_ids": [], "result": {"revision_id": plan_id, "plan": plan}})})
    N["creative_revisions"].append({"id": plan_id, "run_id": run_id, "production_id": production_id,
        "kind": "plan", "body": json.dumps({"revision_id": plan_id, "body": plan})})
    results = {}
    for key, outputs in [
        ("local-shot-1", [("video", "video/mp4")]), ("local-shot-2", [("video", "video/mp4")]),
        ("local-shot-3", [("video", "video/mp4")]), ("local-compose", [("video", "video/mp4"), ("mixed", "audio/wav")])]:
        manifest, refs = [], []
        input_hash = hashlib.sha256(key.encode()).hexdigest()
        for output_key, media_type in outputs:
            suffix = key + "-" + output_key
            attempt, stage, asset = "attempt-" + suffix, "stage-" + suffix, "asset-" + suffix
            candidate = {"staging_id": stage, "sha256": hashlib.sha256(suffix.encode()).hexdigest(),
                         "size": 123, "media_type": media_type, "source": "synthetic-fixture",
                         "rights": "fixture-association-only"}
            manifest.append({"attempt_id": attempt, "candidate": candidate})
            N["generated_attempts"].append({"id": attempt, "run_id": run_id, "step_key": key,
                "input_sha256": input_hash, "staging_id": stage, "output_key": output_key})
            N["generated_attempts"][-1].update(source=candidate["source"], rights=candidate["rights"])
            N["staging"].append({"id": stage, "owner": owner, "status": "imported", "asset_id": asset,
                "sha256": candidate["sha256"], "size": candidate["size"], "media_type": media_type})
            N["assets"].append({"id": asset, "owner": owner, **{field: candidate[field]
                for field in ("sha256", "size", "media_type", "source", "rights")},
                "probe_json": json.dumps({"decoded": True, "media_type": media_type})})
            refs.append(asset)
        N["operations"].append({"run_id": run_id, "production_id": production_id, "step_key": key,
            "input_sha256": input_hash, "observation_json": json.dumps({"result_json": {"generated_files": manifest}})})
        N["steps"].append({"run_id": run_id, "step_key": key, "input_sha256": input_hash,
            "result_json": json.dumps({"asset_ids": refs, "result": {"generated_files": manifest}})})
        results[key] = refs
    shots = [results["local-shot-" + str(index)][0] for index in (1, 2, 3)]
    final = results["local-compose"]
    N["creative_revisions"].append({"id": quality_id, "run_id": run_id, "kind": "quality",
        "body": json.dumps({"body": {"plan_revision_id": plan_id, "asset_ids": shots + final}})})
    rows = []
    base = {"id": flow_id, "run_id": run_id, "binding_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
            "plan_revision_id": plan_id}
    for method in ["prepare", "local-shot-1", "local-shot-2", "local-shot-3", "compose", "review_pending"]:
        state = dict(base)
        if method.startswith("local-shot-"):
            state["shot_asset_ids"] = shots[:int(method[-1])]
        if method in {"compose", "review_pending"}:
            state.update(shot_asset_ids=shots, output_asset_ids=final)
        if method == "review_pending":
            state.update(outcome="waiting_user", quality_revision_id=quality_id)
        rows.append({"flow_uuid": flow_id, "method_name": method, "state_json": json.dumps(state)})
    return N, [copy.deepcopy(rows[0])], rows


class ProbeFixture:
    def model_dump(self, mode):
        return {"decoded": True, "media_type": "video/mp4", "duration_us": 4_000_000,
                "width": 720, "height": 1280, "has_audio": True, "has_video": True}


class AssociationSanity(unittest.TestCase):
    def probe_events(self, label, actual_path, mutate=False, raise_error=None):
        folder = ROOT / label
        journal = Journal(folder, "fixture_sanity")
        calls = []
        sentinel = ProbeFixture()

        def original(self, path, decode=True):
            calls.append(path)
            if mutate:
                path.write_bytes(b"changed plain fixture bytes")
            if raise_error is not None:
                raise raise_error
            return sentinel

        wrapped = wrap_probe(original, journal, "synthetic-run")
        decoder = SimpleNamespace(staging_root=ROOT)
        if raise_error is not None:
            with self.assertRaises(type(raise_error)) as caught:
                wrapped(decoder, actual_path, decode=True)
            self.assertIs(caught.exception, raise_error)
        else:
            self.assertIs(wrapped(decoder, actual_path, decode=True), sentinel)
        self.assertEqual(calls, [actual_path])  # one original fake callable, zero decoder executions
        return [json.loads(path.read_text("utf8")) for path in sorted(folder.glob("Event*.json"))]

    def test_original_fixture_input_bound_and_wrong_same_bytes_path_rejected(self):
        original, wrong = ROOT / "OriginalPlainFixture.bin", ROOT / "OtherPlainFixture.bin"
        original.write_bytes(b"plain fixture data, not a video")
        wrong.write_bytes(original.read_bytes())
        file = {"path": str(original), "sha256": hashlib.sha256(original.read_bytes()).hexdigest(),
                "size": original.stat().st_size, "mtime_ns": original.stat().st_mtime_ns}
        correct = self.probe_events("CorrectProbe", original)
        assert_original_probe(correct, file, "synthetic-run", os.getpid())
        unrelated = self.probe_events("WrongPathProbe", wrong)
        with self.assertRaises(AssertionError):
            assert_original_probe(unrelated, file, "synthetic-run", os.getpid())

    def test_probe_changed_bytes_rejected_and_original_exception_preserved(self):
        path = ROOT / "ChangedPlainFixture.bin"
        path.write_bytes(b"original plain fixture")
        file = {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "size": path.stat().st_size, "mtime_ns": path.stat().st_mtime_ns}
        changed = self.probe_events("ChangedProbe", path, mutate=True)
        with self.assertRaises(AssertionError):
            assert_original_probe(changed, file, "synthetic-run", os.getpid())
        sentinel = RuntimeError("own fake callable exception, not a product error")
        raised = self.probe_events("ExceptionProbe", path, raise_error=sentinel)
        self.assertEqual(raised[-1]["event"], "decode_raised")

    def test_valid_synthetic_lineage_and_same_spec_swapped_or_shared_steps_rejected(self):
        N, Kflows, Nflows = synthetic_lineage()
        assert_media_lineage(N, Kflows, Nflows)
        for shared in (False, True):
            bad = copy.deepcopy(N)
            two, three = [step for step in bad["steps"] if step["step_key"] in {"local-shot-2", "local-shot-3"}]
            second, third = json.loads(two["result_json"]), json.loads(three["result_json"])
            second["asset_ids"] = third["asset_ids"]
            if not shared:
                third["asset_ids"] = json.loads(two["result_json"])["asset_ids"]
                three["result_json"] = json.dumps(third)
            two["result_json"] = json.dumps(second)
            with self.assertRaises(AssertionError):
                assert_media_lineage(bad, Kflows, Nflows)

    def test_wrong_flow_run_binding_and_ordered_refs_rejected(self):
        N, Kflows, Nflows = synthetic_lineage()
        for field, value in [
            ("run_id", "foreign-run"), ("binding_sha256", "0" * 64),
            ("shot_asset_ids", ["asset-local-shot-1-video", "asset-local-shot-3-video", "asset-local-shot-2-video"]),
            ("output_asset_ids", ["asset-local-compose-mixed", "asset-local-compose-video"])]:
            bad = copy.deepcopy(Nflows)
            state = json.loads(bad[-1]["state_json"])
            state[field] = value
            bad[-1]["state_json"] = json.dumps(state)
            with self.assertRaises(AssertionError):
                assert_media_lineage(N, Kflows, bad)


if __name__ == "__main__":
    assert not any(name.startswith("video_creator") for name in sys.modules)
    unittest.main()
