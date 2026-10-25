"""Only AST and own plain-data expectation sanity; never import any product."""
from __future__ import annotations

import argparse
import ast
import contextlib
import hashlib
import io
import json
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
    repo = Path(__file__).resolve().parents[2]
    fixture = repo / "tests/bundle"
    paths = sorted(fixture.glob("t16_*.py")) + [
        fixture / "t15_evidence.py", Path(__file__).resolve(), Path(sys.executable).resolve()]
    before = {str(path): sha(path) for path in paths}
    for path in paths:
        if path.suffix != ".py":
            continue
        data = path.read_bytes()
        assert b"\r\n" not in data and not data.startswith(b"\xef\xbb\xbf")
        ast.parse(data.decode("utf-8"), str(path))
    sys.path.insert(0, str(fixture))
    import t16_preparation_sanity
    suite = unittest.defaultTestLoader.loadTestsFromModule(t16_preparation_sanity)
    log, errors = io.StringIO(), io.StringIO()
    start = time.monotonic()
    with contextlib.redirect_stderr(errors):
        result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    elapsed = time.monotonic() - start
    (output / "Stdout.txt").write_text(log.getvalue(), encoding="utf-8", newline="\n")
    (output / "Stderr.txt").write_text(errors.getvalue(), encoding="utf-8", newline="\n")
    after = {path: sha(Path(path)) for path in before}
    assert before == after
    receipt = {"phase": "T16_PREPARATION_SANITY_ONLY", "actual_argv": sys.argv,
               "python": sys.executable, "python_version": sys.version,
               "tests": result.testsRun, "failures": len(result.failures),
               "errors": len(result.errors), "skipped": len(result.skipped),
               "seconds": elapsed, "exit_code": 0 if result.wasSuccessful() else 1,
               "before": before, "after": after, "source_changes": [],
               "product_imports": 0, "product_launches": 0, "production_read_freeze": False,
               "service_adapter_instantiated": False, "HTTP_requests": 0, "MCP_host_calls": 0,
               "ASR_decoder_DB_calls": 0, "key_reads": 0, "fees_cny": 0,
               "classification": "synthetic expected predicates only; no qualifications or product pass"}
    (output / "Receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
                                        encoding="utf-8", newline="\n")
    print(json.dumps({key: value for key, value in receipt.items()
                      if key not in {"before", "after"}}, ensure_ascii=False))
    return receipt["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
