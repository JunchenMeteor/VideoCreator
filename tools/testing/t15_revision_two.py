"""T15 revision2 pure fixture runner with separate immutable before/after runs."""
from __future__ import annotations

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
    fixture_dir = Path(__file__).resolve().parents[2] / "tests/bundle"
    sources = sorted(fixture_dir.glob("t15_*.py")) + [Path(__file__).resolve()]
    before = {str(path): sha(path) for path in sources}
    before[str(Path(sys.executable).resolve())] = sha(Path(sys.executable).resolve())
    for path in sources:
        raw = path.read_bytes()
        assert b"\r\n" not in raw and not raw.startswith(b"\xef\xbb\xbf")
        for node in ast.walk(ast.parse(raw.decode("utf-8"), str(path))):
            if isinstance(node, ast.Import):
                assert not any(a.name.startswith("video_creator") for a in node.names)
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith("video_creator")
    sys.path.insert(0, str(fixture_dir))
    os.environ["T15_SANITY_DIR"] = str(output)
    import t15_fixture_sanity
    import t15_revision_two_sanity
    suite = unittest.TestSuite((
        unittest.defaultTestLoader.loadTestsFromModule(t15_fixture_sanity),
        unittest.defaultTestLoader.loadTestsFromModule(t15_revision_two_sanity)))
    log = io.StringIO()
    stderr = io.StringIO()
    start = time.monotonic()
    with contextlib.redirect_stderr(stderr):
        result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    elapsed = time.monotonic() - start
    (output / "Stdout.txt").write_text(log.getvalue(), encoding="utf-8", newline="\n")
    (output / "Stderr.txt").write_text(stderr.getvalue(), encoding="utf-8", newline="\n")
    after = {path: sha(Path(path)) for path in before}
    assert before == after, "fixture/tool drift"
    receipt = {"phase": "T15_REVISION2_PURE_FIXTURE", "actual_argv": sys.argv,
               "python": sys.executable, "python_version": sys.version,
               "tests": result.testsRun, "failures": len(result.failures),
               "errors": len(result.errors), "skipped": len(result.skipped),
               "elapsed_seconds": elapsed, "exit_code": 0 if result.wasSuccessful() else 1,
               "before": before, "after": after, "source_changes": [],
               "product_imports": 0, "product_launches": 0, "production_read_freeze": False,
               "asr_decoder_database_calls": 0, "keys_read": 0, "fees_cny": 0,
               "classification": "synthetic plain-data fixture assertions only, not real precision"}
    (output / "Receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
                                        encoding="utf-8", newline="\n")
    print(json.dumps({key: value for key, value in receipt.items()
                      if key not in {"before", "after"}}, ensure_ascii=False))
    return receipt["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
