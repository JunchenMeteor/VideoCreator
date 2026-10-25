"""Actual 68-case runner, callable only after separate trusted admission.

No CLI bootstrap is guessed while Backend/Integration ports are unpublished.
Running this file directly reports not_ready/78 with zero actual cases. It is
not a product test, authority grant or replacement for the pre-Python starter.
"""
from __future__ import annotations

import json
import sys
import time
import traceback


def run_actual_suite(ctx, case_ids, journal):
    from t21_cases import CASE_ROWS, dispatch
    from t21_runtime import ActualRuntime, CaseBlocked
    assert type(ctx) is ActualRuntime, "only actual unique Backend consumer context"
    known = [row[0] for row in CASE_ROWS]
    assert case_ids and len(set(case_ids)) == len(case_ids)
    assert all(case_id in known for case_id in case_ids)
    results = []
    for case_id in case_ids:
        started = time.time_ns()
        journal.record("case_started", {"case_id": case_id, "wallclock_ns": started})
        try:
            observation = dispatch(ctx, case_id)
        except CaseBlocked as error:
            row = {"case_id": case_id, "status": "blocked", "requirement": error.requirement,
                   "detail": str(error), "actual_completed_cases": 0}
        except Exception as error:
            # Assertion/provider/implementation errors remain real failures;
            # RuntimeError is never generally translated to not_ready or skip.
            row = {"case_id": case_id, "status": "failed", "exception_type": type(error).__name__,
                   "frames": [{"file": frame.filename, "line": frame.lineno, "function": frame.name}
                              for frame in traceback.extract_tb(error.__traceback__)]}
        else:
            row = {"case_id": case_id, "status": "passed", "actual_completed_cases": 1, "observation": observation}
        row["ended_wallclock_ns"] = time.time_ns()
        results.append(row)
        journal.record("case_terminal", row)
    failed = sum(row["status"] == "failed" for row in results)
    blocked = sum(row["status"] == "blocked" for row in results)
    return {"cases": results, "pass": sum(row["status"] == "passed" for row in results),
            "fail": failed, "blocked": blocked, "skip": 0,
            "exit": 1 if failed else 78 if blocked else 0}


def main():
    print(json.dumps({"status": "not_ready_for_execution", "phase": "pre_python_admission",
        "actual_cases": 0, "skip": 0, "exit": 78,
        "missing": ["independent Review/Root immutable complete pins", "trusted NativeSupervisor bridge",
                    "final Backend factory/session bootstrap", "independent per-case resources"]}))
    return 78


if __name__ == "__main__":
    sys.exit(main())
