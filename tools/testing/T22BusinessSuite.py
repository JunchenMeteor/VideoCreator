"""Scoped new runner uses T22 dispatch; it does not launch or grant runtime."""
from __future__ import annotations

import json
import sys
import time
import traceback


def run_actual_suite(ctx, case_ids, journal):
    from t22_cases import INHERITED_ROWS, dispatch
    from t21_runtime import ActualRuntime, CaseBlocked
    assert type(ctx) is ActualRuntime
    known = [row[0] for row in INHERITED_ROWS]
    assert case_ids and len(set(case_ids)) == len(case_ids) and all(case_id in known for case_id in case_ids)
    rows = []
    for case_id in case_ids:
        journal.record("case_started", {"case_id": case_id, "wallclock_ns": time.time_ns()})
        try:
            observation = dispatch(ctx, case_id)
        except CaseBlocked as error:
            row = {"case_id": case_id, "status": "blocked", "requirement": error.requirement, "detail": str(error)}
        except Exception as error:
            row = {"case_id": case_id, "status": "failed", "exception_type": type(error).__name__,
                "frames": [{"file": f.filename, "line": f.lineno, "function": f.name} for f in traceback.extract_tb(error.__traceback__)]}
        else:
            row = {"case_id": case_id, "status": "passed", "observation": observation}
        rows.append(row)
        journal.record("case_terminal", row)
    failed = sum(row["status"] == "failed" for row in rows)
    blocked = sum(row["status"] == "blocked" for row in rows)
    return {"cases": rows, "skip": 0, "pass": sum(row["status"] == "passed" for row in rows), "fail": failed,
            "blocked": blocked, "exit": 1 if failed else 78 if blocked else 0}


if __name__ == "__main__":
    print(json.dumps({"status": "not_ready_for_execution", "actual_product_cases": 0, "exit": 78,
        "missing": ["approved full runtime binding", "trusted session handle/process bridge", "actual independent fixtures"]}))
    sys.exit(78)
