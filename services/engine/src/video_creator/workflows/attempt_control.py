"""Trusted in-process attempt signals; never an approval or model argument."""
from __future__ import annotations

import contextvars
import math
import time
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass

from video_creator.domain.errors import EngineError

_ACTIVE: contextvars.ContextVar[AttemptControl | None] = contextvars.ContextVar("production_attempt_control", default=None)


@dataclass(frozen=True)
class AttemptControl:
    cancel: Callable[[], bool] | None = None
    deadline_monotonic: float | None = None

    def __post_init__(self):
        if self.cancel is not None and not callable(self.cancel):
            raise EngineError("production_attempt_control_invalid", "Attempt signals require a trusted in-process callback.", 403)
        if self.deadline_monotonic is not None and (isinstance(self.deadline_monotonic, bool)
                or not isinstance(self.deadline_monotonic, (int, float)) or not math.isfinite(self.deadline_monotonic)):
            raise EngineError("production_attempt_control_invalid", "Attempt deadline must be a finite monotonic time.", 403)

    def cancel_requested(self):
        if self.cancel is None:
            return False
        try:
            result = self.cancel()
            if type(result) is not bool:
                raise ValueError("invalid signal")
            return result
        except Exception:  # noqa: BLE001 - signal faults fail closed with a fixed, secret-free error.
            raise EngineError("production_attempt_control_failed", "Trusted attempt signal is unavailable.", 503) from None

    def check(self):
        if self.cancel_requested():
            # Only the backend decides business cancellation versus host-stop.
            raise EngineError("production_attempt_interrupted", "The trusted host stopped this attempt.", 409)
        if self.deadline_monotonic is not None and time.monotonic() >= self.deadline_monotonic:
            raise EngineError("production_attempt_deadline", "The trusted attempt deadline expired.", 409)

    def remaining(self, maximum):
        self.check()
        if isinstance(maximum, bool) or not isinstance(maximum, (int, float)) or not math.isfinite(maximum) or maximum <= 0:
            raise EngineError("production_attempt_control_invalid", "Child duration must have a finite positive bound.", 403)
        value = maximum if self.deadline_monotonic is None else min(maximum, self.deadline_monotonic - time.monotonic())
        if value <= 0:
            raise EngineError("production_attempt_deadline", "The trusted attempt deadline expired.", 409)
        return value

    @contextmanager
    def activate(self):
        self.check()
        token = _ACTIVE.set(self)
        try:
            yield self
        finally:
            _ACTIVE.reset(token)


def current_attempt():
    return _ACTIVE.get() or AttemptControl()


def attempt_control(cancel=None, deadline_monotonic=None):
    requested = AttemptControl(cancel, deadline_monotonic)
    parent = _ACTIVE.get()
    if parent is None:
        return requested
    deadlines = [value for value in (parent.deadline_monotonic, requested.deadline_monotonic) if value is not None]
    return AttemptControl(lambda: parent.cancel_requested() or requested.cancel_requested(), min(deadlines) if deadlines else None)
