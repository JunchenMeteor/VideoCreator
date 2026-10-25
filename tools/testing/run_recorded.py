"""Capture real command output and before/after source hashes; never infer gate completion."""

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


def snapshot(root):
    files = list((root / "services/engine/src/video_creator").rglob("*.py"))
    files += list((root / "services/engine/migrations").glob("*.sql"))
    files += list((root / "tests/gate0").glob("*.py"))
    files += list((root / "tools/testing").glob("*.py"))
    return {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(files)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--scope-file", type=Path, help="Optional explicit repository source dependency list; outside changes are still recorded")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        raise ValueError("Actual command required")
    root = Path(__file__).resolve().parents[2]
    args.output_dir.mkdir(parents=True, exist_ok=False)
    all_before, started = snapshot(root), datetime.now(UTC).isoformat()
    scope = None
    if args.scope_file:
        scope = json.loads(args.scope_file.read_text(encoding="utf-8"))
        if not isinstance(scope, list) or not scope or any(not isinstance(p, str) for p in scope):
            raise ValueError("Scope must be a nonempty list of repository source paths")
        for relative in scope:
            path = root / relative
            if Path(relative).is_absolute() or not path.resolve().is_relative_to(root) or not path.is_file():
                raise ValueError("Scope contains an unavailable or out-of-repository source")
        before = {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in sorted(set(scope))}
    else:
        before = all_before
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith("VIDEO_CREATOR_SECRET_") and key != "VIDEO_CREATOR_API_TOKEN"}
    environment.update(PYTHONPATH=str(root / "services/engine/src"), PYTHONUTF8="1", OTEL_SDK_DISABLED="true", CREWAI_TRACING_ENABLED="false")
    result = subprocess.run(command, cwd=root, env=environment, capture_output=True, text=True, encoding="utf-8", check=False)
    all_after = snapshot(root)
    after = {p: hashlib.sha256((root / p).read_bytes()).hexdigest() if (root / p).is_file() else None
             for p in before} if scope else all_after
    for name, value in (("Stdout.txt", result.stdout), ("Stderr.txt", result.stderr)):
        (args.output_dir / name).write_text(value, encoding="utf-8", newline="\n")
    record = {"command": command, "cwd": str(root), "started_at": started,
              "finished_at": datetime.now(UTC).isoformat(), "exit_code": result.returncode,
              "environment": {"os": platform.platform(), "architecture": platform.machine(), "python": sys.version.split()[0]},
              "schema_version": "0.1.0-candidate", "source_sha256_before": before, "source_sha256_after": after,
              "explicit_source_scope": scope,
              "source_changed_during_run": sorted(path for path in set(before) | set(after) if before.get(path) != after.get(path)),
              "outside_scope_changed_during_run": sorted(path for path in set(all_before) | set(all_after)
                  if scope is not None and path not in before and all_before.get(path) != all_after.get(path)),
              "all_source_sha256_before": all_before, "all_source_sha256_after": all_after,
              "stdout_sha256": hashlib.sha256(result.stdout.encode("utf-8")).hexdigest(),
              "stderr_sha256": hashlib.sha256(result.stderr.encode("utf-8")).hexdigest(),
              "provider_calls": "not_measured_by_wrapper", "evidence_scope": "declared nonbillable implementation tests; individual assertions establish call counts",
              "gate_completion": "not_assessed; independent review and acceptance required"}
    (args.output_dir / "CommandReceipt.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"exit_code": result.returncode, "source_changes": len(record["source_changed_during_run"]),
                      "outside_scope_changes": len(record["outside_scope_changed_during_run"]),
                      "provider_calls": "not_measured_by_wrapper", "actual_command_output": result.stdout, "stderr": result.stderr}, ensure_ascii=False))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
