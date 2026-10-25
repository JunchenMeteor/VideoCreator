"""ADR0042 private canonical identity handshake; identity is never authority."""

from dataclasses import dataclass

from video_creator.cli.native_owner_startup import (
    NativeOwnerStartupRecord,
    _installation_fields,
)
from video_creator.domain.errors import EngineError
from video_creator.domain.native_execution_registration import NativeInstallationInputs
from video_creator.domain.owner_setup import SETUP_FRAME_LIMIT
from video_creator.infrastructure.held_authority import _fields, _json, _sha, _text, _uint
from video_creator.infrastructure.native_installation_observer import parse_installation_locator
from video_creator.infrastructure.native_owner_confirmation import (
    canonical_wire,
    parse_confirmation_locator,
)

WIRE = 'native-owner-instance-handshake-v1'
PEER_WIRE = 'native-owner-instance-peer-v1'
IDENTITY_LIMIT = 16 * 1024
FAILURES = {
    'owner_instance_handshake_invalid': 422,
    'owner_instance_handshake_limit': 413,
    'owner_instance_source_denied': 403,
    'owner_instance_binding_changed': 409,
    'owner_instance_source_unavailable': 503,
    'owner_instance_handshake_timeout': 503,
}


def invalid(message):
    return EngineError('owner_instance_handshake_invalid', message, 422)


def _canonical_object(data, names):
    try:
        raw = _fields(_json(data), names)
        if canonical_wire(raw) != data:
            raise invalid('Instance handshake requires exact canonical UTF8')
        return raw
    except EngineError as error:
        if error.code in FAILURES:
            raise
        raise invalid('Instance handshake fields or canonical bytes are invalid') from error


def parse_bootstrap_locator(value):
    try:
        raw = _fields(value, ('pipe', 'session', 'role', 'server'))
        pipe = _text(raw['pipe'], limit=512)
        prefix = '\\\\.\\pipe\\VideoCreator-OwnerSetupInit-'
        if (not pipe.startswith(prefix) or not pipe[len(prefix):]
                or any(char in pipe[len(prefix):] for char in ('\\', '/', ':'))):
            raise invalid('Initialization requires its closed local pipe family')
        _text(raw['session'], limit=128)
        if raw['role'] != 'owner-setup-initialize':
            raise invalid('Initialization locator has a different role')
        server = _fields(raw['server'], ('pid', 'creation_filetime', 'sid', 'image', 'image_sha256'))
        if _uint(server['pid'], positive=True) > 0xFFFFFFFF:
            raise invalid('Initialization peer PID is invalid')
        _uint(server['creation_filetime'], positive=True)
        _text(server['sid'], limit=200)
        _text(server['image'], limit=32768)
        _sha(server['image_sha256'])
        return raw
    except EngineError as error:
        if error.code in FAILURES:
            raise
        raise invalid('Initialization locator is invalid') from error


@dataclass(frozen=True)
class NativeInstanceInitializationRecord:
    installation: NativeInstallationInputs
    external_receipt_path: str
    expected_host_image: str
    expected_host_sha256: str
    bootstrap_locator_bytes: bytes

    @classmethod
    def parse(cls, data: bytes):
        raw = _canonical_object(data, ('format', 'installation_inputs',
            'external_receipt_path', 'expected_host_image', 'expected_host_sha256', 'bootstrap_locator'))
        if raw['format'] != 'native-owner-instance-initialization-v1':
            raise invalid('Initialization record version is not admitted')
        try:
            installation, receipt, host, sha = _installation_fields(raw)
        except EngineError as error:
            if error.status_code == 403:
                raise EngineError('owner_instance_source_denied', 'Independent initialization host differs', 403) from error
            raise invalid('Complete original installation fields are required') from error
        locator = parse_bootstrap_locator(raw['bootstrap_locator'])
        return cls(installation, receipt, host, sha, canonical_wire(locator))

    def assert_startup(self, record):
        if (record.installation, record.external_receipt_path, record.expected_host_image,
                record.expected_host_sha256) != (self.installation, self.external_receipt_path,
                self.expected_host_image, self.expected_host_sha256):
            raise EngineError('owner_instance_binding_changed', 'Original initialization resources changed', 409)


@dataclass(frozen=True)
class NativeInstanceSetupBinding:
    startup: NativeOwnerStartupRecord
    startup_record_bytes: bytes
    installation_locator_bytes: bytes
    confirmation_locator_bytes: bytes

    @classmethod
    def parse(cls, data: bytes, *, initialization, instance_id):
        raw = _canonical_object(data, ('wire', 'event', 'seq', 'startup_record',
            'installation_locator', 'confirmation_locator'))
        if (raw['wire'], raw['event'], type(raw['seq']), raw['seq']) != (WIRE, 'bind_setup', int, 2):
            raise invalid('Only the original sequence-two setup binding is admitted')
        for name in ('startup_record', 'installation_locator', 'confirmation_locator'):
            if type(raw[name]) is not dict:
                raise invalid('Setup binding contains canonical objects, never encoded carriers')
        startup_bytes = canonical_wire(raw['startup_record'])
        installation_bytes = canonical_wire(raw['installation_locator'])
        confirmation_bytes = canonical_wire(raw['confirmation_locator'])
        try:
            record = NativeOwnerStartupRecord.parse(startup_bytes)
            installation = parse_installation_locator(installation_bytes, instance_id)
            confirmation = parse_confirmation_locator(confirmation_bytes, instance_id)
        except EngineError as error:
            if error.status_code == 403:
                raise EngineError('owner_instance_binding_changed', 'Original instance binding differs', 409) from error
            raise invalid('Original complete setup carriers are invalid') from error
        if record.instance_id != instance_id:
            raise EngineError('owner_instance_binding_changed', 'Actual initialized instance changed', 409)
        initialization.assert_startup(record)
        original_server = parse_bootstrap_locator(_json(initialization.bootstrap_locator_bytes))['server']
        if installation['server'] != original_server or confirmation['server'] != original_server:
            raise EngineError('owner_instance_binding_changed', 'Original launch peer changed between phases', 409)
        return cls(record, startup_bytes, installation_bytes, confirmation_bytes)


def parse_peer_reply(data, session):
    raw = _canonical_object(data, ('wire', 'session', 'seq', 'status', 'code'))
    if (raw['wire'], raw['session'], type(raw['seq']), raw['seq']) != (PEER_WIRE, session, int, 1):
        raise invalid('Initialization peer reply differs from the original connection')
    if type(raw['status']) is not int or type(raw['code']) is not str:
        raise invalid('Initialization peer status must be strict')
    if (raw['status'], raw['code']) == (200, 'bound'):
        return
    if FAILURES.get(raw['code']) != raw['status']:
        raise invalid('Initialization peer failure is outside its closed grammar')
    raise EngineError(raw['code'], 'Original initialization peer refused the binding', raw['status'])


def frame_size(length):
    if not 0 < length <= SETUP_FRAME_LIMIT:
        raise EngineError('owner_instance_handshake_limit', 'Instance handshake exceeds its bounded frame', 413)
