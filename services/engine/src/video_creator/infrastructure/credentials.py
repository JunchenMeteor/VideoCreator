"""OS-vault-only secrets. Project databases and flow snapshots contain references."""

import os
from pathlib import Path

import keyring

from video_creator.domain.errors import EngineError

SERVICE_NAME = "VideoCreator"


class SecretHandle:
    __slots__ = ("_value",)

    def __init__(self, value: str):
        self._value = value

    def reveal(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return "<SecretHandle redacted>"

    def __str__(self) -> str:
        return "<SecretHandle redacted>"


class CredentialVault:
    def _backend(self):
        backend = keyring.get_keyring()
        module = type(backend).__module__
        if not module.startswith(("keyring.backends.Windows", "keyring.backends.macOS", "keyring.backends.SecretService", "keyring.backends.kwallet")):
            raise EngineError("secure_vault_unavailable", "A supported OS credential vault is required", 503)
        return backend

    def import_file(self, source: str | Path, credential_id: str) -> str:
        if not credential_id or len(credential_id) > 100 or not all(c.isalnum() or c in "-_" for c in credential_id):
            raise EngineError("invalid_credential_ref", "Invalid credential identifier", 400)
        secret = Path(source).read_text(encoding="utf-8-sig").strip()
        if not 16 <= len(secret) <= 512 or any(c.isspace() for c in secret):
            raise EngineError("invalid_credential", "Credential file must contain one API key", 400)
        try:
            self._backend().set_password(SERVICE_NAME, credential_id, secret)
        except EngineError:
            raise
        except Exception:  # noqa: BLE001 - OS backends use platform exceptions; never expose secret-bearing bodies.
            raise EngineError("credential_import_failed", "OS credential vault could not save the credential", 503) from None
        return f"vault:{credential_id}"

    def resolve(self, reference: str) -> SecretHandle:
        kind, _, identifier = reference.partition(":")
        if kind == "vault":
            try:
                value = self._backend().get_password(SERVICE_NAME, identifier)
            except EngineError:
                raise
            except Exception:  # noqa: BLE001 - sanitize platform-specific vault exceptions at this boundary.
                raise EngineError("credential_unavailable", "OS credential vault is unavailable", 503) from None
        elif kind == "env" and identifier.startswith("VIDEO_CREATOR_SECRET_"):
            value = os.environ.get(identifier)
        else:
            raise EngineError("credential_ref_denied", "Unsupported credential reference", 403)
        if not value:
            raise EngineError("credential_missing", "Configured credential is unavailable", 503)
        return SecretHandle(value)

    @staticmethod
    def _vault_identifier(identifier: str) -> str:
        if (type(identifier) is not str or not identifier or len(identifier) > 200
                or not all(character.isalnum() or character in "-_.:" for character in identifier)):
            raise EngineError("invalid_credential_ref", "Invalid credential identifier", 400)
        return identifier

    def store_secret(self, identifier: str, secret: str) -> None:
        """Trusted startup only: write one opaque secret into the OS vault.

        No request, task, model output or configuration file reaches this path;
        the local evidence administrator is its only caller.
        """
        identifier = self._vault_identifier(identifier)
        if (type(secret) is not str or not 1 <= len(secret) <= 4096
                or any(character.isspace() for character in secret)):
            raise EngineError("invalid_credential", "Credential value is not one bounded secret", 400)
        try:
            self._backend().set_password(SERVICE_NAME, identifier, secret)
        except EngineError:
            raise
        except Exception:  # noqa: BLE001 - OS backends use platform exceptions; never expose secret-bearing bodies.
            raise EngineError("credential_store_failed", "OS credential vault could not save the secret", 503) from None

    def load_secret(self, identifier: str) -> str | None:
        identifier = self._vault_identifier(identifier)
        try:
            return self._backend().get_password(SERVICE_NAME, identifier)
        except EngineError:
            raise
        except Exception:  # noqa: BLE001 - sanitize platform-specific vault exceptions at this boundary.
            raise EngineError("credential_unavailable", "OS credential vault is unavailable", 503) from None

    def remove_secret(self, identifier: str) -> None:
        identifier = self._vault_identifier(identifier)
        try:
            self._backend().delete_password(SERVICE_NAME, identifier)
        except EngineError:
            raise
        except Exception as error:  # noqa: BLE001 - a missing entry is already removed.
            if type(error).__name__ != "PasswordDeleteError":
                raise EngineError("credential_store_failed", "OS credential vault could not remove the secret", 503) from None
