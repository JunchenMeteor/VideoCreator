"""V03 independent plain-data assertions; not producer DTOs or qualifications."""
from __future__ import annotations

from fractions import Fraction


def _units(entries, duration_us):
    assert type(duration_us) is int and duration_us > 0
    ids = set()
    validated = []
    for key, start, end in entries:
        assert type(key) is str and key and key not in ids
        assert type(start) is type(end) is int and 0 <= start < end <= duration_us
        ids.add(key)
        validated.append((key, start, end))
    assert validated
    return validated


def assert_metric(predicted_entries, reference_entries, duration_us, reported_n, reported_p95):
    # Adapter extraction must use final unique Backend objects, never a fake DTO.
    predicted = _units(predicted_entries, duration_us)
    references = _units(reference_entries, duration_us)
    assert len(predicted) == len(references)
    assert {entry[0] for entry in predicted} == {entry[0] for entry in references}
    reference_map = {key: (start, end) for key, start, end in references}
    errors = [max(abs(start - reference_map[key][0]), abs(end - reference_map[key][1]))
              for key, start, end in predicted]
    count = len(errors)
    rank = (95 * count + 99) // 100
    p95 = sorted(errors)[rank - 1]
    assert type(reported_n) is int and reported_n == count
    assert type(reported_p95) is int and reported_p95 == p95 <= 200_000
    return {"N": count, "p95_error_us": p95, "errors": errors}


def assert_unmeasured(assessment, actual_measurement_artifacts):
    assert assessment["evaluation_scope"] == "per_work_reference_measurement"
    assert assessment["status"] == "not_measured"
    for key in ("sample_count", "p95_error_us", "reference_ref", "measurement_report_locator"):
        assert assessment[key] is None
    assert actual_measurement_artifacts == [], "no empty/fake measurement attachment"


def assert_scope(scope, expected):
    scopes = {"capability_benchmark", "work_runtime_validation", "per_work_reference_measurement"}
    assert scope in scopes and expected in scopes and scope == expected


def assert_allocation_only(allocation):
    forbidden = {"sha256", "content_sha256", "size", "decoded", "validated"}
    assert not forbidden.intersection(allocation), "allocation is not ready Receipt"
    for key in ("preparation_id", "artifact_id", "material_id"):
        assert type(allocation[key]) is str and allocation[key]


def assert_acyclic_edges(edges):
    ids = {key for key, _ in edges}
    assert len(ids) == len(edges)
    for key, dependencies in edges:
        assert set(dependencies) <= ids
        assert len(dependencies) == len(set(dependencies))
    pending = {key: set(dependencies) for key, dependencies in edges}
    done = set()
    while pending:
        ready = {key for key, dependencies in pending.items() if dependencies <= done}
        assert ready, "report/material future-hash cycle"
        done.update(ready)
        pending = {key: dependencies for key, dependencies in pending.items() if key not in ready}
    return done
