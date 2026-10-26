"""BYOK credential registry: OS vault only; instance files hold metadata only."""

from __future__ import annotations

import hashlib
import json
import secrets
from pathlib import Path

from video_creator.infrastructure.credentials import CredentialVault

SERVICE = CredentialVault
VAULT_WEAK_CODE = "vault_unavailable"


def _folder(data_dir: Path) -> Path:
    root = Path(data_dir) / "Control"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _registry_path(data_dir: Path) -> Path:
    return _folder(data_dir) / "Credentials.json"


def _audit_path(data_dir: Path) -> Path:
    return _folder(data_dir) / "CredentialAudit.jsonl"


def _read(data_dir: Path) -> dict:
    path = _registry_path(data_dir)
    if not path.is_file() or path.is_symlink():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    return value if isinstance(value, dict) else {}


def _write(data_dir: Path, value: dict) -> None:
    path = _registry_path(data_dir)
    pending = path.with_suffix(".json.pending")
    pending.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                  separators=(",", ":")) + "\n", encoding="utf-8")
    import os
    os.replace(pending, path)


def _audit(data_dir: Path, actor: str, action: str, ref: str, fingerprint: str, at_us: int) -> None:
    row = {"action": action, "ref": ref, "fingerprint": fingerprint,
           "actor": actor, "at_us": at_us}
    with _audit_path(data_dir).open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True,
                                separators=(",", ":")) + "\n")
        stream.flush()
        import os
        os.fsync(stream.fileno())


def _vault() -> CredentialVault:
    return CredentialVault()


def _refs_in(value) -> list[str]:
    found = []
    if isinstance(value, str) and value.startswith("vault:"):
        found.append(value)
    elif isinstance(value, dict):
        for child in value.values():
            found.extend(_refs_in(child))
    elif isinstance(value, (list, tuple)):
        for child in value:
            found.extend(_refs_in(child))
    return found


def list_credentials(data_dir: Path) -> list[dict]:
    return sorted(_read(data_dir).values(), key=lambda item: item["created_at_us"])


def references_for(engine, ref: str) -> list[str]:
    found = []
    with engine.db.connect_readonly() as connection:
        for row in connection.execute("SELECT id,body FROM routes ORDER BY id"):
            if ref in _refs_in(json.loads(row["body"])):
                found.append("route:" + row["id"])
        for row in connection.execute("SELECT id,request_json FROM productions ORDER BY rowid"):
            try:
                body = json.loads(row["request_json"])
            except ValueError:
                body = row["request_json"]
            if ref in _refs_in(body):
                found.append("production:" + row["id"])
    return found


def create_credential(data_dir: Path, actor: str, provider: str, label: str, secret: str,
                      now_us: int) -> dict:
    if "env:" in secret:
        from video_creator.domain.errors import EngineError
        raise EngineError("credential_external_reference_denied",
                          "Credential values cannot reference an external environment", 422)
    identifier = secrets.token_hex(16)
    ref = "vault:" + identifier
    fingerprint = hashlib.sha256(secret.encode("utf-8")).hexdigest()[:16]
    vault = _vault()
    try:
        vault.store_secret(identifier, secret)
    except Exception as error:  # noqa: BLE001 - sanitize vault failures, never include the secret
        from video_creator.domain.errors import EngineError
        if getattr(error, "code", None) == "secure_vault_unavailable":
            raise EngineError(VAULT_WEAK_CODE, "The OS credential vault is unavailable", 503) from None
        raise EngineError("credential_store_failed",
                          "OS credential vault could not save the credential", 503) from None
    item = {"credential_ref": ref, "fingerprint": fingerprint, "provider": provider,
            "label": label, "created_at_us": now_us}
    registry = _read(data_dir)
    registry[ref] = item
    _write(data_dir, registry)
    _audit(data_dir, actor, "credential.created", ref, fingerprint, now_us)
    return item


def delete_credential(data_dir: Path, actor: str, ref: str, now_us: int,
                      references: list[str]) -> dict:
    if references:
        from video_creator.domain.errors import EngineError
        error = EngineError("credential_in_use", "Credential is still referenced", 409)
        error.references = references
        raise error
    registry = _read(data_dir)
    item = registry.pop(ref, None)
    if item is None:
        from video_creator.domain.errors import EngineError
        raise EngineError("credential_not_found", "Credential is not registered", 404)
    identifier = ref.removeprefix("vault:")
    _vault().remove_secret(identifier)
    _write(data_dir, registry)
    _audit(data_dir, actor, "credential.deleted", ref, item["fingerprint"], now_us)
    return item
