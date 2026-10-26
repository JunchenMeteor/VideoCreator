"""The A' evidence-admin path requires explicit UI confirmation and a bound nonce."""

import hashlib
import json
from pathlib import Path

import pytest
from video_creator.application.local_evidence import evidence_admin_install_confirmed
from video_creator.domain.errors import EngineError


def _args(tmp_path: Path, **overrides):
    root = tmp_path / "install"
    root.mkdir(exist_ok=True)
    record = tmp_path / "record.json"
    record.write_text(json.dumps({"format": "installation-provisioning-v1", "complete": True,
                                  "install_root": str(root)}), encoding="utf-8")
    record_sha = hashlib.sha256(record.read_bytes()).hexdigest()
    nonce = "a" * 32
    policy = overrides.get("policy", "local_evidence_policy")
    confirmation = hashlib.sha256(json.dumps(
        {"nonce": nonce, "install_record_sha256": record_sha, "policy": policy},
        sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    values = {"data_dir": tmp_path / "data", "install_root": root, "installation_record": record,
              "installation_record_sha256": record_sha, "confirmed_by_ui": True,
              "confirmation_nonce": nonce, "confirmation_sha256": confirmation, "policy": policy}
    values.update(overrides)
    return values


def test_confirmed_by_ui_is_required(tmp_path):
    with pytest.raises(EngineError) as error:
        evidence_admin_install_confirmed(**_args(tmp_path, confirmed_by_ui=False))
    assert error.value.code == "local_evidence_ui_confirmation_required"


def test_confirmation_digest_is_bound(tmp_path):
    with pytest.raises(EngineError) as error:
        evidence_admin_install_confirmed(**_args(tmp_path, confirmation_sha256="0" * 64))
    assert error.value.code == "local_evidence_confirmation_invalid"


def test_replay_and_idempotent(tmp_path, monkeypatch):
    import video_creator.application.local_evidence as evidence
    import video_creator.application.owner_bootstrap as owner_module

    data = tmp_path / "data"
    (data / "Control").mkdir(parents=True)
    values = _args(tmp_path)

    class FakeOwner:
        principal = type("P", (), {"owner_subject": "owner", "project_ids": ("project",)})()

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    class FakeStore:
        def __init__(self, engine):
            pass

        def current(self, allow_inactive=False):
            return FakeOwner()

    monkeypatch.setattr(owner_module, "OwnerBootstrapStore", FakeStore)
    monkeypatch.setattr(evidence, "load_local_evidence_key", lambda instance_id, create=True: ("issuer", b"key"))
    monkeypatch.setattr(evidence, "evidence_admin_install",
                        lambda **kwargs: {"policy_ref": {"policy_id": "p", "revision": 1, "content_sha256": "a" * 64}})
    values["data_dir"] = data
    first = evidence.evidence_admin_install_confirmed(**values)
    assert first["status"] == "installed"
    second = evidence.evidence_admin_install_confirmed(**values)
    assert second["status"] == "already_installed"

    other = _args(tmp_path, policy="another-policy")
    other["data_dir"] = data
    with pytest.raises(EngineError) as error:
        evidence.evidence_admin_install_confirmed(**other)
    assert error.value.code == "local_evidence_nonce_replayed"
