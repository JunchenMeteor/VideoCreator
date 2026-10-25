"""Synthetic unit cases for evidence record validation; no product acceptance."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROCESS_ROOT = ROOT.parents[1] / "Codex" / "VideoCreatorImplementation" / "TestDevelopment"
MODULE_PATH = ROOT / "tools" / "testing" / "validate_evidence.py"
spec = importlib.util.spec_from_file_location("evidence_validator", MODULE_PATH)
validator = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(validator)


class EvidenceRecordTests(unittest.TestCase):
    def setUp(self):
        PROCESS_ROOT.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="EvidenceFixture-", dir=PROCESS_ROOT)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.stdout = self.root / "SyntheticStdout.txt"
        self.stdout.write_text("synthetic tool fixture only\n", encoding="utf-8", newline="\n")
        self.artifact = self.root / "SyntheticArtifact.txt"
        self.artifact.write_text("synthetic record only; no media\n", encoding="utf-8", newline="\n")
        self.commit = "1" * 40
        self.build = "2" * 64
        self.baseline = {"criteria_version": "test-only", "freeze_status": "frozen",
                         "source_sha256": {"spec": "3" * 64}, "gate0_criteria": ["G0-ENV"],
                         "requirements": [{"id": "FR01", "required_phases": ["R1", "R2"]},
                                          {"id": "CM01", "required_phases": ["R2"]}]}
        self.report = {
            "phase": "GATE0", "criteria_version": "test-only", "commit": self.commit,
            "build_sha256": self.build, "source_sha256": self.baseline["source_sha256"],
            "environment": {"os": "synthetic", "architecture": "synthetic", "machine": "unit-fixture"},
            "test_run": {"command": "python -m unittest", "cwd": str(ROOT), "exit_code": 0,
                         "passed": 1, "failed": 0, "skipped": 0, "stdout_path": self.stdout.name,
                         "stdout_sha256": hashlib.sha256(self.stdout.read_bytes()).hexdigest()},
            "items": [self.item("G0-ENV")],
        }

    def item(self, criterion):
        return {"criterion_id": criterion, "status": "passed", "evidence_kind": "real",
                "commit": self.commit, "build_sha256": self.build,
                "artifacts": [{"path": self.artifact.name,
                               "sha256": hashlib.sha256(self.artifact.read_bytes()).hexdigest()}]}

    def check(self, report=None):
        return validator.validate(self.report if report is None else report, self.baseline, self.root)

    def test_consistent_synthetic_record_has_no_structural_errors(self):
        self.assertEqual(self.check(), [])

    def test_mock_cannot_establish_completion(self):
        self.report["items"][0]["evidence_kind"] = "simulated"
        self.assertTrue(any("cannot establish completion" in e for e in self.check()))

    def test_skips_and_exit_failure_are_rejected(self):
        for value in (1, None, True):
            with self.subTest(value=value):
                report = copy.deepcopy(self.report)
                report["test_run"]["skipped"] = value
                report["test_run"]["exit_code"] = 1
                self.assertIn("nonzero or unknown skipped", self.check(report))
                self.assertIn("test command did not exit 0", self.check(report))

    def test_criterion_and_source_versions_are_checked(self):
        self.report["criteria_version"] = "old"
        self.report["source_sha256"] = {}
        self.assertIn("criteria version mismatch", self.check())
        self.assertIn("source specification hash mismatch", self.check())

    def test_unreviewed_standards_cannot_pass(self):
        self.baseline["freeze_status"] = "pending_independent_review"
        self.assertIn("criteria not independently frozen", self.check())

    def test_missing_and_duplicate_items_are_rejected(self):
        self.report["items"] = []
        self.assertIn("missing required criterion G0-ENV", self.check())
        self.report["items"] = [self.item("G0-ENV"), self.item("G0-ENV")]
        self.assertIn("duplicate criterion G0-ENV", self.check())

    def test_unexecuted_and_blocked_items_are_rejected(self):
        for state in ("blocked", "not_run", "failed", "skipped"):
            with self.subTest(state=state):
                self.report["items"][0]["status"] = state
                self.assertIn("G0-ENV: required item not passed", self.check())

    def test_file_mutation_and_missing_file_are_rejected(self):
        self.artifact.write_text("changed\n", encoding="utf-8", newline="\n")
        self.assertIn("G0-ENV: evidence hash mismatch", self.check())
        self.artifact.unlink()
        self.assertIn("G0-ENV: missing or empty evidence file", self.check())

    def test_path_escape_is_rejected_without_reading_outside_root(self):
        self.report["items"][0]["artifacts"][0]["path"] = "../Secret.txt"
        self.assertIn("G0-ENV: evidence outside declared root", self.check())

    def test_cross_commit_build_are_rejected(self):
        self.report["items"][0]["commit"] = "a" * 40
        self.report["items"][0]["build_sha256"] = "b" * 64
        self.assertIn("G0-ENV: commit/build differs", self.check())

    def test_r2_must_include_r1_regression_and_commercial_checks(self):
        self.report["phase"] = "R2"
        self.report["items"] = [self.item("CM01")]
        self.assertIn("missing required criterion FR01", self.check())
        self.report["items"].append(self.item("FR01"))
        self.assertEqual(self.check(), [])

    def test_echo_and_empty_output_are_not_actual_check_commands(self):
        self.report["test_run"]["command"] = "echo ok"
        self.stdout.write_text("", encoding="utf-8")
        self.assertIn("missing actual check command", self.check())
        self.assertIn("test output: missing or empty evidence file", self.check())

    def test_cli_red_then_green_structural_check(self):
        baseline_path = self.root / "Baseline.json"
        report_path = self.root / "Report.json"
        baseline_path.write_text(json.dumps(self.baseline), encoding="utf-8", newline="\n")
        self.report["items"][0]["evidence_kind"] = "simulated"
        report_path.write_text(json.dumps(self.report), encoding="utf-8", newline="\n")
        command = [sys.executable, str(MODULE_PATH), "--baseline", str(baseline_path),
                   "--report", str(report_path), "--evidence-root", str(self.root)]
        red = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(red.returncode, 1)
        self.assertFalse(json.loads(red.stdout)["external_behavior_verified"])
        self.report["items"][0]["evidence_kind"] = "real"
        report_path.write_text(json.dumps(self.report), encoding="utf-8", newline="\n")
        green = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(green.returncode, 0)
        self.assertEqual(json.loads(green.stdout)["independent_acceptance"], "still_required")
        (PROCESS_ROOT / "EvidenceToolRedGreen.json").write_text(
            json.dumps({"scope": "synthetic evidence validator only; no product acceptance",
                        "command": command,
                        "red": {"exit_code": red.returncode, "stdout": red.stdout, "stderr": red.stderr},
                        "green": {"exit_code": green.returncode, "stdout": green.stdout, "stderr": green.stderr}},
                       ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    unittest.main()
