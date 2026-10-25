"""Exact JSON for media-owned plain objects; BaseModel canonical stays separate."""
from __future__ import annotations

import json
import math

from video_creator.domain.errors import EngineError


def canonical_object(value: dict) -> str:
    def validate(item, depth=0):
        if depth > 32:
            raise ValueError("JSON nesting limit")
        if item is None or type(item) in {str, bool, int}:
            return
        if type(item) is float and math.isfinite(item):
            return
        if type(item) is dict and all(type(key) is str for key in item):
            for child in item.values():
                validate(child, depth + 1)
            return
        if type(item) is list:
            for child in item:
                validate(child, depth + 1)
            return
        raise ValueError("non-JSON input")

    try:
        if type(value) is not dict:
            raise ValueError("plain JSON object required")
        validate(value)
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError):
        raise EngineError("production_json_invalid", "Media input is not a bounded canonical JSON object.", 422) from None
