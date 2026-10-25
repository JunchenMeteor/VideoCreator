"""Transparent real publisher barriers for a separately supervised child.

These hooks neither create content nor settle operations. Parent-owned Job
termination at the durable barrier is what creates the actual fault window.
No hook is installed on import; no product object is constructed here.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch


def durable_phase(path, record):
    # Caller must bind this exact own path before child launch. Do not mkdir,
    # follow a link or overwrite a receipt from a previous experiment.
    target = Path(path)
    assert target.is_absolute() and target.parent.is_dir() and not target.exists()
    assert not any(parent.is_symlink() for parent in (target.parent, *target.parent.parents))
    raw = (json.dumps(record, ensure_ascii=False, allow_nan=False, sort_keys=True) + "\n").encode("utf-8")
    with target.open("xb") as sink:
        sink.write(raw)
        sink.flush()
        os.fsync(sink.fileno())


@contextmanager
def real_publisher_barrier(bundle, lease, preparation_id, phase, phase_path, *, window_seconds):
    assert phase in {"manifest_file_before_commit", "published_return_before_flow"}
    assert 0 < window_seconds <= 30
    preparation = bundle.recover_preparation(lease, preparation_id)
    original_write, original_publish = bundle._write, bundle.publish
    hit = []

    def observe_and_hold():
        assert not hit, "publisher barrier hit more than once"
        path = bundle._file("BundleManifests", preparation.bundle_revision_id)
        raw = path.read_bytes()
        row = {
            "phase": phase, "pid": os.getpid(), "run_id": lease.run_id,
            "fencing_token": lease.fencing_token, "preparation_id": preparation_id,
            "bundle_revision_id": preparation.bundle_revision_id,
            "file_path": str(path), "file_sha256": hashlib.sha256(raw).hexdigest(), "file_size": len(raw),
            "observed_wallclock_ns": time.time_ns(), "observed_monotonic_ns": time.monotonic_ns(),
        }
        hit.append(row)
        durable_phase(phase_path, row)
        # Expected parent kill never returns. Timeout is a real fixture error;
        # it cannot be mistaken for a successful normal publisher continuation.
        threading.Event().wait(window_seconds)
        raise AssertionError("approved real kill window expired without parent Job termination")

    def write(folder, key, data):
        result = original_write(folder, key, data)
        if phase == "manifest_file_before_commit" and folder == "BundleManifests" and key == preparation.bundle_revision_id:
            observe_and_hold()
        return result

    def publish(current_lease, verified):
        result = original_publish(current_lease, verified)
        if phase == "published_return_before_flow":
            assert current_lease == lease and result.bundle_revision_id == preparation.bundle_revision_id
            observe_and_hold()
        return result

    with patch.object(bundle, "_write", write), patch.object(bundle, "publish", publish):
        yield hit
