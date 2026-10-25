"""One fixed indexed Owner entry; carrier JSON is identity, not authority."""

import json
import sys
from dataclasses import dataclass

from video_creator.application.native_execution_observer import (
    NativeExecutionObserverFactory,
)
from video_creator.domain.errors import EngineError
from video_creator.domain.native_execution_registration import (
    NativeInstallationInputs,
    local_absolute_path,
)
from video_creator.infrastructure.held_authority import (
    _fields,
    _invalid,
    _json,
    _sha,
    _text,
)
from video_creator.infrastructure.native_installation_observer import (
    parse_installation_locator,
)


def _installation_fields(raw):
    """Shared complete installation identity; never constructs an authority."""
    try:
        installation = NativeInstallationInputs.model_validate(raw['installation_inputs'])
        receipt = local_absolute_path(raw['external_receipt_path'])
        host = local_absolute_path(raw['expected_host_image'])
    except (TypeError, ValueError) as error:
        raise _invalid('Indexed installation proposal or independent file path is invalid') from error
    if raw['installation_inputs'] != installation.model_dump(mode='json'):
        raise _invalid('Indexed installation input requires its complete original typed canonical fields')
    sha = _sha(raw['expected_host_sha256'])
    if (host, sha) != (installation.installed_native_image, installation.installed_native_image_sha256):
        raise EngineError('installation_peer_denied', 'Independent expected host differs from the full installation input', 403)
    return installation, receipt, host, sha


@dataclass(frozen=True)
class NativeOwnerStartupRecord:
    instance_id: str
    installation: NativeInstallationInputs
    external_receipt_path: str
    expected_host_image: str
    expected_host_sha256: str

    @classmethod
    def parse(cls, data: bytes):
        raw = _fields(_json(data), ('format', 'instance_id', 'installation_inputs',
            'external_receipt_path', 'expected_host_image', 'expected_host_sha256'))
        if raw['format'] != 'native-owner-installation-startup-v1':
            raise _invalid('Indexed Owner startup record version is not admitted')
        canonical = json.dumps(raw, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
        if canonical != data:
            raise _invalid('Indexed Owner startup requires exact canonical UTF8 bytes without a trailing newline')
        installation, receipt, host, sha = _installation_fields(raw)
        return cls(_text(raw['instance_id']), installation, receipt, host, sha)


def main(*, startup_record: bytes, locator_bytes: bytes) -> int:
    """Guardian invokes this exact indexed symbol with protected input bytes.

    No public module/env selector, initial execution registration, implicit
    Owner action or credential transfer. Original CLI authentication and TTY
    occur before observe opens the original OS guards/channel.
    """
    try:
        record = NativeOwnerStartupRecord.parse(startup_record)
        parse_installation_locator(locator_bytes, record.instance_id)
        factory = NativeExecutionObserverFactory(installation=record.installation, instance_id=record.instance_id,
            locator_bytes=locator_bytes, external_receipt_path=record.external_receipt_path,
            expected_host_image=record.expected_host_image, expected_host_sha256=record.expected_host_sha256)
        from video_creator.cli.main import main as engine_main

        return engine_main(owner_installation_observer_factory=factory)
    except EngineError as error:
        print(json.dumps({'code': error.code, 'message': error.message}), file=sys.stderr)
        return 1
