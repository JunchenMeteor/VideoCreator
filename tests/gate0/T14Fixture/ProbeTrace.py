"""Passive exact-input observations around one genuine probe invocation."""
import functools
import hashlib
import os
from pathlib import Path
from uuid import uuid4


def fingerprint(path, staging_root):
    """Do not read an input outside the original decoder's controlled root."""
    fact = {}
    try:
        candidate = Path(path).resolve(strict=False)
        controlled = Path(staging_root).resolve(strict=False)
        fact["path"] = os.path.normcase(str(candidate))
        fact["inside_staging"] = candidate.is_relative_to(controlled)
        if not fact["inside_staging"]:
            fact["observation_error"] = "OutsideControlledStaging"
            return fact
        stat = candidate.stat()
        fact.update(size=stat.st_size, mtime_ns=stat.st_mtime_ns)
        if not candidate.is_file() or stat.st_size > 256 * 1024 * 1024:
            fact["observation_error"] = "NotFiniteMediaFile"
            return fact
        fact["sha256"] = hashlib.sha256(candidate.read_bytes()).hexdigest()
    except (OSError, ValueError, TypeError) as error:
        fact["observation_error"] = type(error).__name__
    return fact


def wrap_probe(original, journal, target_run_id):
    @functools.wraps(original)
    def observed(self, *args, **kwargs):
        actual_input = args[0] if args else kwargs["path"]
        before = fingerprint(actual_input, self.staging_root)
        fact = {"pid": os.getpid(), "target_run_id": target_run_id, "method": "probe",
                "kind": "decode", "call_id": uuid4().hex,
                "decode_requested": kwargs.get("decode", True), "input_before": before}
        journal.record("decode_begin", fact)
        try:
            result = original(self, *args, **kwargs)
        except BaseException as error:
            after = fingerprint(actual_input, self.staging_root)
            try:
                journal.record("decode_raised", {
                    **fact, "input_after": after, "changed_during_call": before != after,
                    "exception_type": type(error).__name__,
                    "original_error_code": getattr(error, "code", None)})
            except BaseException as observation_error:
                error.add_note("Test probe exception recorder failed: " + type(observation_error).__name__)
            raise
        after = fingerprint(actual_input, self.staging_root)
        journal.record("decode_returned", {
            **fact, "input_after": after, "changed_during_call": before != after,
            "actual_public_probe": result.model_dump(mode="json")})
        return result
    return observed
