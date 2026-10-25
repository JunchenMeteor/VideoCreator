"""Test-only passive evidence, strict byte readers; no product imports."""
from __future__ import annotations

import hashlib
import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def strict_json(data: bytes):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def nonfinite(value):
        raise ValueError(f"nonfinite JSON number: {value}")

    def finite_float(value):
        parsed = float(value)
        if not math.isfinite(parsed):
            raise ValueError(f"JSON number overflows to nonfinite: {value}")
        return parsed

    return json.loads(data.decode("utf-8"), object_pairs_hook=pairs,
                      parse_constant=nonfinite, parse_float=finite_float)


def controlled_file(root: Path, relative: str) -> dict:
    """Read only an exact candidate package entry, never search arbitrary dirs."""
    assert isinstance(relative, str) and "\\" not in relative and ":" not in relative
    parts = relative.split("/")
    assert len(parts) >= 2 and all(p not in {"", ".", ".."} for p in parts)
    base = root.resolve(strict=True)
    current = base
    for part in parts:
        current = current / part
        assert not current.is_symlink(), "symlink package entry"
        assert not current.is_junction(), "junction package entry"
    resolved = current.resolve(strict=True)
    assert resolved.is_relative_to(base) and resolved.is_file()
    stat_before = resolved.stat()
    raw = resolved.read_bytes()
    stat_after = resolved.stat()
    assert (stat_before.st_size, stat_before.st_mtime_ns) == (
        stat_after.st_size, stat_after.st_mtime_ns), "bytes changed during read"
    return {"relative_path": relative, "sha256": digest(raw), "size": len(raw),
            "bytes": raw}


class Journal:
    """Own new directory only. Persist facts immediately, not inferred outcomes."""
    def __init__(self, directory: Path):
        directory.mkdir(parents=True, exist_ok=False)
        self.directory = directory
        self.sequence = 0
        self.previous_sha256 = None

    def record(self, kind: str, facts: dict) -> Path:
        self.sequence += 1
        entry = {"sequence": self.sequence, "kind": kind, "facts": facts,
                 "utc": datetime.now(timezone.utc).isoformat(),
                 "wall_ns": time.time_ns(), "monotonic_ns": time.monotonic_ns(),
                 "previous_sha256": self.previous_sha256}
        data = (json.dumps(entry, ensure_ascii=False, allow_nan=False,
                           sort_keys=True, indent=2) + "\n").encode("utf-8")
        final = self.directory / f"Event{self.sequence:04d}.json"
        temporary = self.directory / f"Pending{self.sequence:04d}.json"
        with temporary.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, final)
        self.previous_sha256 = digest(data)
        return final
