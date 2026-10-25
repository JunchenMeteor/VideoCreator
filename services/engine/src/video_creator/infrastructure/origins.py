"""Trusted startup configuration only; renderer/model payload cannot register origins."""

import os
from urllib.parse import urlsplit

from video_creator.domain.errors import EngineError

WINDOWS_NATIVE_ORIGIN = "http://tauri.localhost"


def startup_origins(values: tuple[str, ...]) -> tuple[str, ...]:
    for value in values:
        try:
            parsed = urlsplit(value)
            port = parsed.port
        except ValueError:
            raise EngineError("startup_origin_invalid", "Trusted startup origin is not a supported exact origin", 400) from None
        if (not value or value == "null" or any(char in value for char in ("*", "\\", "%"))
                or parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username is not None
                or parsed.password is not None or parsed.path or parsed.query or parsed.fragment
                or (port is not None and not 1 <= port <= 65535)):
            raise EngineError("startup_origin_invalid", "Trusted startup origin must have exact scheme/host/port and no path or wildcard", 400)
        host = "[" + parsed.hostname + "]" if ":" in parsed.hostname else parsed.hostname
        expected = parsed.scheme + "://" + host + (":" + str(port) if port is not None else "")
        if value != expected:
            raise EngineError("startup_origin_invalid", "Trusted startup origin must use its exact canonical form", 400)
    if len(set(values)) != len(values):
        raise EngineError("startup_origin_invalid", "Trusted startup origins must be distinct", 400)
    return values


def native_startup_origins(native_origin: str, dev_origins: tuple[str, ...] = ()) -> tuple[str, ...]:
    if os.name != "nt" or native_origin != WINDOWS_NATIVE_ORIGIN:
        raise EngineError("native_origin_unsupported", "This installation has no verified native origin for the requested platform", 400)
    origins = startup_origins(dev_origins)
    for value in origins:
        parsed = urlsplit(value)
        if parsed.hostname not in {"127.0.0.1", "localhost"} or parsed.port is None:
            raise EngineError("native_dev_origin_denied", "Native development requires an exact configured loopback origin and port", 400)
    return (*origins, native_origin)
