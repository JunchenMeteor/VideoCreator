"""Finite Test-only guard/sentinel checks; never executes product loader."""
import argparse
import ast
import contextlib
import hashlib
import io
import json
import os
import sys
import time
import unittest
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    own = Path("G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment").resolve()
    output = args.output_dir.resolve()
    assert output.is_relative_to(own) and not output.exists()
    output.mkdir(parents=True)
    fixture = Path(__file__).resolve().parents[2] / "tests/bundle"
    paths = sorted(fixture.glob("t16_*.py")) + sorted(fixture.glob("t17_*.py")) + [
        fixture / "t15_evidence.py", Path(__file__).resolve(), Path(sys.executable).resolve()]
    before = {str(path): sha(path) for path in paths}
    for path in paths:
        if path.suffix == ".py":
            raw = path.read_bytes()
            assert b"\r\n" not in raw and not raw.startswith(b"\xef\xbb\xbf")
            ast.parse(raw.decode("utf-8"), str(path))
    sys.path.insert(0, str(fixture))
    os.environ["T17_SANITY_DIR"] = str(output)
    import t16_preparation_sanity
    import t17_preparation_sanity
    suite = unittest.TestSuite((
        unittest.defaultTestLoader.loadTestsFromModule(t16_preparation_sanity),
        unittest.defaultTestLoader.loadTestsFromModule(t17_preparation_sanity)))
    stdout, stderr = io.StringIO(), io.StringIO()
    start = time.monotonic()
    with contextlib.redirect_stderr(stderr):
        result = unittest.TextTestRunner(stream=stdout, verbosity=2).run(suite)
    elapsed = time.monotonic() - start
    (output / "Stdout.txt").write_text(stdout.getvalue(), encoding="utf-8", newline="\n")
    (output / "Stderr.txt").write_text(stderr.getvalue(), encoding="utf-8", newline="\n")
    after = {path: sha(Path(path)) for path in before}
    assert before == after
    assert not any(name == "video_creator" or name.startswith("video_creator.") for name in sys.modules)
    receipt = {"phase": "T17_PLAIN_GUARD_SENTINEL_FIRST_REMEDIATION",
               "actual_argv": sys.argv, "python": sys.executable, "version": sys.version,
               "tests": result.testsRun, "failures": len(result.failures),
               "errors": len(result.errors), "skipped": len(result.skipped),
               "seconds": elapsed, "exit_code": 0 if result.wasSuccessful() else 1,
               "before": before, "after": after, "source_changes": [],
               "product_imports": 0, "product_launches": 0, "production_read_freeze": False,
               "actual_service_constructed": 0, "actual_producer_loader_calls": 0,
               "external_network_install_fee_key": 0,
               "synthetic_authority_installed": False,
               "classification": "own preflight order/sentinel plus hash grammar, not real bootstrap/authority/service",
               "whole_V03_closure": "not_ready_for_execution"}
    (output / "Receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
                                        encoding="utf-8", newline="\n")
    print(json.dumps({key: value for key, value in receipt.items()
                      if key not in {"before", "after"}}, ensure_ascii=False))
    return receipt["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
