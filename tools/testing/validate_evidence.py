"""Validate evidence records, never certify external behavior or visual quality."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


def file_errors(record: dict, evidence_root: Path, label: str) -> list[str]:
    errors = []
    path_value = record.get("path")
    if not isinstance(path_value, str):
        return [f"{label}: missing evidence path"]
    root = evidence_root.resolve()
    path = (root / path_value).resolve()
    if not path.is_relative_to(root):
        return [f"{label}: evidence outside declared root"]
    if not path.is_file() or path.stat().st_size == 0:
        return [f"{label}: missing or empty evidence file"]
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if record.get("sha256") != digest:
        errors.append(f"{label}: evidence hash mismatch")
    return errors


def validate(report: dict, baseline: dict, evidence_root: Path) -> list[str]:
    errors = []
    phase = report.get("phase")
    if phase not in {"GATE0", "R1", "R2"}:
        errors.append("unknown phase")
    if report.get("criteria_version") != baseline.get("criteria_version"):
        errors.append("criteria version mismatch")
    if baseline.get("freeze_status") != "frozen":
        errors.append("criteria not independently frozen")
    if report.get("source_sha256") != baseline.get("source_sha256"):
        errors.append("source specification hash mismatch")
    if not re.fullmatch(r"[0-9a-f]{40}", str(report.get("commit", ""))):
        errors.append("missing exact commit")
    if not re.fullmatch(r"[0-9a-f]{64}", str(report.get("build_sha256", ""))):
        errors.append("missing build hash")
    environment = report.get("environment", {})
    if not isinstance(environment, dict) or not all(environment.get(key) for key in ("os", "architecture", "machine")):
        errors.append("missing actual environment")
    run = report.get("test_run", {})
    if not isinstance(run, dict):
        errors.append("invalid test run")
        run = {}
    command = run.get("command")
    if not isinstance(command, str) or not command.strip() or re.match(r"\s*(?:echo|Write-Output|printf)\b", command, re.IGNORECASE):
        errors.append("missing actual check command")
    if not run.get("cwd"):
        errors.append("missing command cwd")
    if type(run.get("exit_code")) is not int or run["exit_code"] != 0:
        errors.append("test command did not exit 0")
    for field in ("failed", "skipped"):
        if type(run.get(field)) is not int or run[field] != 0:
            errors.append(f"nonzero or unknown {field}")
    if type(run.get("passed")) is not int or run["passed"] < 1:
        errors.append("no passing tests recorded")
    errors += file_errors({"path": run.get("stdout_path"), "sha256": run.get("stdout_sha256")}, evidence_root, "test output")
    expected = set(baseline.get("gate0_criteria", [])) if phase == "GATE0" else {
        item["id"] for item in baseline.get("requirements", []) if phase in item["required_phases"]
    }
    items = report.get("items", [])
    if not isinstance(items, list):
        errors.append("invalid criterion records")
        items = []
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            errors.append("invalid criterion record")
            continue
        criterion = item.get("criterion_id")
        if criterion not in expected:
            errors.append(f"unexpected criterion {criterion}")
        if criterion in seen:
            errors.append(f"duplicate criterion {criterion}")
        seen.add(criterion)
        if item.get("status") != "passed":
            errors.append(f"{criterion}: required item not passed")
        if item.get("evidence_kind") != "real":
            errors.append(f"{criterion}: simulated/inspection evidence cannot establish completion")
        artifacts = item.get("artifacts", [])
        if not isinstance(artifacts, list) or not artifacts:
            errors.append(f"{criterion}: no actual artifact evidence")
        else:
            for artifact in artifacts:
                if not isinstance(artifact, dict):
                    errors.append(f"{criterion}: invalid artifact evidence")
                else:
                    errors += file_errors(artifact, evidence_root, str(criterion))
        if item.get("commit") != report.get("commit") or item.get("build_sha256") != report.get("build_sha256"):
            errors.append(f"{criterion}: commit/build differs")
    errors += [f"missing required criterion {criterion}" for criterion in sorted(expected - seen)]
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        errors = validate(json.loads(args.report.read_text(encoding="utf-8")), json.loads(args.baseline.read_text(encoding="utf-8")), args.evidence_root)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"record_validation": "failed", "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps({"record_validation": "failed" if errors else "consistent", "errors": errors,
                      "independent_acceptance": "still_required", "external_behavior_verified": False}, ensure_ascii=False))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
