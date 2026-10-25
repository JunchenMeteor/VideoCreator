"""Generated management secrets stay in OS vault or Owner-only Linux files."""

import os
import secrets
import stat
import sys

from video_creator.domain.errors import EngineError
from video_creator.infrastructure.credentials import CredentialVault


class OwnerSecretStore:
    def __init__(self, data_dir, instance_id):
        self.data_dir, self.instance_id = data_dir, instance_id

    def _key(self, binding_id):
        if not binding_id or len(binding_id) > 100 or any(character not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for character in binding_id):
            raise EngineError('owner_secret_identity_invalid', 'Invalid internal Owner binding identity', 422)
        return 'owner-' + self.instance_id + '-' + binding_id

    def _directory(self):
        directory = self.data_dir / 'Control' / 'OwnerSecrets'
        directory.mkdir(mode=0o700, exist_ok=True)
        info = directory.lstat()
        if directory.is_symlink() or not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise EngineError('owner_secret_denied', 'Secret directory must be restricted to the actual UID', 403)
        return directory

    def create(self, binding_id):
        key = self._key(binding_id)
        value = secrets.token_urlsafe(48)
        if sys.platform.startswith('linux'):
            path = self._directory() / binding_id
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(descriptor, 'wb') as stream:
                stream.write(value.encode('ascii'))
                stream.flush()
                os.fsync(stream.fileno())
            directory_descriptor = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
        else:
            try:
                CredentialVault()._backend().set_password('VideoCreatorOwnerManagement', key, value)
            except EngineError:
                raise
            except Exception:  # noqa: BLE001 - vault exception bodies may contain secrets.
                raise EngineError('owner_secret_unavailable', 'OS vault could not store management authentication', 503) from None

    def resolve(self, binding_id) -> bytes:
        key = self._key(binding_id)
        if sys.platform.startswith('linux'):
            path = self._directory() / binding_id
            descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(descriptor, 'rb') as stream:
                info = os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077 or not 32 <= info.st_size <= 512:
                    raise EngineError('owner_secret_denied', 'Management authentication is not an Owner-only file', 403)
                value = stream.read(513).decode('ascii')
        else:
            try:
                value = CredentialVault()._backend().get_password('VideoCreatorOwnerManagement', key)
            except EngineError:
                raise
            except Exception:  # noqa: BLE001 - never expose vault exceptions or credential content.
                raise EngineError('owner_secret_unavailable', 'OS management authentication is unavailable', 503) from None
        if not isinstance(value, str) or not 32 <= len(value) <= 512 or any(character.isspace() for character in value):
            raise EngineError('owner_secret_unavailable', 'Management authentication is missing or damaged', 503)
        return value.encode('ascii')
