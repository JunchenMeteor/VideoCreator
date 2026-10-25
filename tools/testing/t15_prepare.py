"""Executable preparation only: AST + own plain-data unit tests, no product."""
from __future__ import annotations

import argparse
import ast
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
    own_root = Path("G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment").resolve()
    output = args.output_dir.resolve()
    assert output.is_relative_to(own_root) and not output.exists()
    output.mkdir(parents=True)
    repo = Path(__file__).resolve().parents[2]
    fixture_dir = repo / "tests/bundle"
    paths = sorted(fixture_dir.glob("t15_*.py")) + [Path(__file__).resolve()]
    before = {str(path): sha(path) for path in paths}
    before[str(Path(sys.executable).resolve())] = sha(Path(sys.executable).resolve())
    for path in paths:
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf") and b"\r\n" not in raw
        tree = ast.parse(raw.decode("utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert not any(alias.name.startswith("video_creator") for alias in node.names)
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith("video_creator")
    sys.path.insert(0, str(fixture_dir))
    os.environ["T15_SANITY_DIR"] = str(output)
    import t15_fixture_sanity
    stream = io.StringIO()
    start = time.monotonic()
    suite = unittest.defaultTestLoader.loadTestsFromModule(t15_fixture_sanity)
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    elapsed = time.monotonic() - start
    raw = stream.getvalue()
    (output / "Stdout.txt").write_text(raw, encoding="utf-8", newline="\n")
    after = {path: sha(Path(path)) for path in before}
    assert before == after, "own fixture/tool changed"
    receipt = {"classification": "pure_fixture_sanity_not_product",
               "argv": sys.argv, "python": sys.executable,
               "python_version": sys.version, "tests_run": result.testsRun,
               "failures": len(result.failures), "errors": len(result.errors),
               "skipped": len(result.skipped), "elapsed_seconds": elapsed,
               "exit_code": 0 if result.wasSuccessful() else 1,
               "before": before, "after": after, "source_changes": [],
               "production_imports": 0, "product_launches": 0,
               "decoder_calls": 0, "asr_calls": 0, "database_business_writes": 0,
               "credentials_read": 0, "paid_api_calls": 0}
    (output / "Receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n")
    print(json.dumps({key: value for key, value in receipt.items()
                      if key not in {"before", "after"}}, ensure_ascii=False))
    return receipt["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
