"""Test-only marker transport perturbation; keeps the actual API implementation and cleanup."""

import os
import sys

MODE = os.environ.get("VIDEO_CREATOR_T7_MARKER")
MARKER = b'{"event":"api_stopped","scope":"api"}\n'

if MODE:
    original = sys.stderr

    class BytesOutput:
        def write(self, data):
            if data != MARKER:
                return original.buffer.write(data)
            alternatives = {
                "crlf": MARKER[:-1] + b"\r\n",
                "spaced": b'{"event": "api_stopped", "scope": "api"}\n',
                "extra": b'{"event":"api_stopped","scope":"api","extra":true}\n',
                "duplicate": MARKER + MARKER,
                "partial": MARKER[:-1],
                "long-suffix": b"x" * 513 + MARKER,
                "prefixed": b"unknown:" + MARKER,
            }
            if MODE == "split":
                original.buffer.write(MARKER[:8])
                original.buffer.flush()
                original.buffer.write(MARKER[8:])
                return len(data)
            altered = alternatives[MODE]
            original.buffer.write(altered)
            return len(data)

        def flush(self):
            return original.buffer.flush()

    class TextOutput:
        buffer = BytesOutput()

        def __getattr__(self, name):
            return getattr(original, name)

    sys.stderr = TextOutput()
