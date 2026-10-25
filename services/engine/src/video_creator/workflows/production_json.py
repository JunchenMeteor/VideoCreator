"""Exact JSON for media-owned plain objects; BaseModel canonical stays separate."""
from __future__ import annotations

import json
import math
from decimal import Decimal
from enum import Enum
from pathlib import PurePath

from pydantic import BaseModel, ValidationError

from video_creator.domain.errors import EngineError

MAX_DEPTH = 32


def json_body(value, *, path='body'):
    """Sole normalization for every media-owned body entering JSON.

    Converts only explicit, lossless forms: pydantic -> `model_dump(mode='json')`,
    `Enum` -> its value, `Decimal` -> finite plain string, `Path` -> string,
    `tuple` -> list. Bytes, sets and unknown types are rejected with a named
    error that carries the exact path; nothing is silently dropped.
    """
    return _normalize(value, path, 0)


def require_body(model, value, *, path='body'):
    """Normalize, then validate against the target model before any commit.

    The check round-trips through canonical JSON, mirroring how a committed
    revision is later read from the database; a failure names the first path.
    """
    normalized = json_body(value, path=path)
    raw = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    try:
        model.model_validate_json(raw)
    except (ValidationError, ValueError) as error:
        raise EngineError('media_body_invalid',
            f'Body does not validate as {model.__name__} at {_first_path(error)}.', 422) from None
    return normalized


def _first_path(error):
    if isinstance(error, ValidationError) and error.errors():
        first = error.errors()[0]
        # Pydantic union tags (`dict`, `list`, `str`, ...) are not field names.
        parts = [str(part) for part in first.get('loc', ())
                 if str(part) not in {'dict', 'list', 'tuple', 'str', 'int', 'float', 'bool', 'none'}]
        return '.'.join(parts) or '<root>'
    return '<root>'


def _deny(item, path, code='media_body_type_denied'):
    raise EngineError(code, f'{type(item).__name__} cannot enter a media body at {path}.', 422)


def _normalize(item, path, depth):
    if depth > MAX_DEPTH:
        raise EngineError('media_body_invalid', f'Body nesting exceeds {MAX_DEPTH} at {path}.', 422)
    if item is None or type(item) in {str, bool, int}:
        return item
    if type(item) is float:
        if not math.isfinite(item):
            raise EngineError('media_body_invalid', f'Non-finite number at {path}.', 422)
        return item
    if isinstance(item, BaseModel):
        return _normalize(item.model_dump(mode='json'), path, depth + 1)
    if isinstance(item, Enum):
        return _normalize(item.value, path, depth + 1)
    if isinstance(item, Decimal):
        if not item.is_finite():
            raise EngineError('media_body_invalid', f'Non-finite decimal at {path}.', 422)
        return format(item, 'f')
    if isinstance(item, PurePath):
        return str(item)
    if isinstance(item, dict):
        result = {}
        for key, child in item.items():
            if type(key) is not str:
                raise EngineError('media_body_key_denied', f'Body keys must be strings at {path}.', 422)
            result[key] = _normalize(child, path + '.' + key, depth + 1)
        return result
    if type(item) in {list, tuple}:
        return [_normalize(child, f'{path}[{index}]', depth + 1) for index, child in enumerate(item)]
    if isinstance(item, (bytes, bytearray, memoryview)):
        raise EngineError('media_body_bytes_denied', f'Raw bytes cannot enter a media body at {path}.', 422)
    _deny(item, path)


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
