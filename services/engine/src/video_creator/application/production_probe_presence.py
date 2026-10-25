"""Original Worker presence held across the bounded local probe only."""

import threading
import time
from contextlib import contextmanager

from video_creator.application.worker import HEARTBEAT_SECONDS
from video_creator.domain.errors import EngineError


@contextmanager
def hold_probe_presence(worker, worker_id, control, deadline_monotonic):
    stop, errors = threading.Event(), []
    # This refuses expired/replaced identity; never register or revive it.
    worker.heartbeat_presence(worker_id)

    def cancelled():
        return control.stop_requested or bool(errors) or time.monotonic() >= deadline_monotonic

    def renew():
        while not stop.wait(HEARTBEAT_SECONDS):
            if control.stop_requested:
                return
            if time.monotonic() >= deadline_monotonic:
                errors.append(EngineError('worker_attempt_deadline', 'Original bounded probe deadline reached', 503))
                return
            try:
                worker.heartbeat_presence(worker_id)
            except BaseException as error:
                errors.append(error)
                return

    thread = threading.Thread(target=renew, name='production-probe-presence')
    thread.start()
    try:
        yield cancelled
    finally:
        stop.set()
        thread.join()
        if errors:
            raise errors[0]
    if not control.stop_requested:
        if time.monotonic() >= deadline_monotonic:
            raise EngineError('worker_attempt_deadline', 'Original bounded probe deadline reached', 503)
        worker.heartbeat_presence(worker_id)
