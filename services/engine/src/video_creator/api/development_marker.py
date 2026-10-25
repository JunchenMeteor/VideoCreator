"""In-process development host marker for ADR0077; never request or env input.

Only `video_creator.cli.development_host` marks a process, and only after the
development installation assembly succeeded. The value is a process-internal
fact used to describe `/api/v1/health`; it is not a qualification, a release
signal or a worker liveness proof.
"""

DEVELOPMENT_INSTALLATION_HEADER = 'X-VideoCreator-Installation'
DEVELOPMENT_INSTALLATION_VALUE = 'local-development'
_development = []


def mark_development_host() -> None:
    """Idempotent in-process mark; there is no way to set it from a payload."""
    if not _development:
        _development.append(True)


def is_development_host() -> bool:
    return bool(_development)
