"""The `serve` ready descriptor contract: required fields exist, optional fields stay in domain.

The descriptor is additive. ADR0081 added `authorization_state` to the restricted
shape only; the old T6 helper compared the exact key set, which turned that product
addition into 27 unrelated failures. These two cases pin both real shapes so a
later additive field cannot break every T6 mechanism test:
restricted (has `authorization_state`) and authorized (the field is absent).
"""

import secrets
import sys

from t6_cli_helpers import (
    AUTHORIZATION_SECRET_ENV,
    READY_REQUIRED,
    SERVE_BASE,
    assert_ready_descriptor,
    authorize_instance,
    serve_environment,
    start_ready,
    stop_process,
)


def test_restricted_serve_ready_descriptor_has_pending_authorization(tmp_path):
    """No Owner binding: the descriptor names the consent state and claims no principal."""
    environment = serve_environment()
    environment[AUTHORIZATION_SECRET_ENV] = secrets.token_hex(16)
    argv = [sys.executable, *SERVE_BASE, "--data-dir", str(tmp_path / "Instance")]
    process, ready = start_ready(argv, environment, label="restricted-ready")
    try:
        assert_ready_descriptor(ready)
        assert all(name in ready for name in READY_REQUIRED), ready
        assert ready["authorization_state"] == "pending", ready
        assert "principal_id" not in ready, ready
    finally:
        stop_process(process)


def test_authorized_serve_ready_descriptor_omits_restricted_only_field(tmp_path):
    """After the product consent channel writes the Owner binding and restarts, the
    ready descriptor is the authorized shape: no restricted-only `authorization_state`."""
    instance = tmp_path / "Instance"
    outcome = authorize_instance(instance)
    assert outcome["approved"] is not None, outcome
    assert outcome["approved"]["restart_required"] is True, outcome

    argv = [sys.executable, *SERVE_BASE, "--data-dir", str(instance)]
    process, ready = start_ready(argv, serve_environment(), label="authorized-ready")
    try:
        assert_ready_descriptor(ready)
        assert all(name in ready for name in READY_REQUIRED), ready
        assert "authorization_state" not in ready, ready
        # An ordinary production serve assembles no native execution identity.
        assert "principal_id" not in ready, ready
    finally:
        stop_process(process)
