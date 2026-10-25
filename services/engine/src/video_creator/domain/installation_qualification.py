"""ADR0044 private strict qualification facts; parsing never grants authority."""

import hashlib
import json
from typing import Annotated, Literal

from pydantic import Field, model_validator

from video_creator.domain import contracts as c
from video_creator.domain.errors import EngineError
from video_creator.infrastructure.held_authority import _json, _relative

I64_MAX = 9_223_372_036_854_775_807
I64 = Annotated[int, Field(ge=0, le=I64_MAX, strict=True)]
PositiveI64 = Annotated[int, Field(gt=0, le=I64_MAX, strict=True)]
U32 = Annotated[int, Field(ge=0, le=0xFFFFFFFF, strict=True)]
CRT_NAMES = ('mfc140u.dll', 'msvcp140.dll', 'msvcp140_1.dll', 'msvcp140_2.dll',
             'msvcp140_atomic_wait.dll', 'msvcp140_codecvt_ids.dll',
             'vcruntime140.dll', 'vcruntime140_1.dll')
FEATURES = ('x86_sse2', 'x86_avx', 'x86_avx2', 'arm_neon')
PROFILES = ('api', 'worker', 'mcp', 'asr')


def canonical_bytes(value):
    if isinstance(value, c.Contract):
        value = value.model_dump(mode='json')
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def body_sha(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def parse_exact(model, data, *, limit=1024 * 1024):
    if type(data) is not bytes or not 1 <= len(data) <= limit:
        raise EngineError('installation_frame_invalid', 'Private qualification size is invalid', 422)
    try:
        raw = _json(data)
        value = model.model_validate(raw)
        if canonical_bytes(value) != data:
            raise ValueError('Private qualification fields or canonical bytes differ')
        return value
    except (ValueError, TypeError, UnicodeError, RecursionError) as error:
        raise EngineError('installation_frame_invalid', 'Private qualification document is invalid', 422) from error


class QualificationRef(c.Contract):
    document_id: c.Identifier
    revision: PositiveI64
    sha256: c.Sha256


def check_refs(refs):
    keys = tuple((ref.document_id, ref.revision, ref.sha256) for ref in refs)
    if not keys or len(keys) > 4096 or keys != tuple(sorted(set(keys))):
        raise ValueError('Complete distinct qualification refs must be sorted')


class OsFloor(c.Contract):
    kind: Literal['os_floor']
    product: Literal['windows_nt', 'linux_kernel', 'darwin']
    version: tuple[U32, U32, U32]
    report_ref: QualificationRef


class PythonAbi(c.Contract):
    kind: Literal['python_abi']
    implementation: Literal['cpython']
    version: tuple[Literal[3], Literal[13], Literal[16]]
    abi_tag: Literal['cp313']
    gil: Literal['standard']
    report_ref: QualificationRef

    @model_validator(mode='before')
    @classmethod
    def strict_version(cls, raw):
        if type(raw) is dict and (type(raw.get('version')) is not list
                or any(type(item) is not int for item in raw['version'])):
            raise ValueError('Python ABI version requires strict integers')
        return raw


class CpuFeatures(c.Contract):
    kind: Literal['cpu_features']
    features: tuple[Literal['x86_sse2', 'x86_avx', 'x86_avx2', 'arm_neon'], ...]
    report_ref: QualificationRef

    @model_validator(mode='after')
    def ordered(self):
        if tuple(feature for feature in FEATURES if feature in self.features) != self.features:
            raise ValueError('CPU features must be distinct and ordered')
        return self


class CrtComponent(c.Contract):
    name: Literal['mfc140u.dll', 'msvcp140.dll', 'msvcp140_1.dll', 'msvcp140_2.dll',
                  'msvcp140_atomic_wait.dll', 'msvcp140_codecvt_ids.dll',
                  'vcruntime140.dll', 'vcruntime140_1.dll']
    floor: tuple[U32, U32, U32, U32]


class WindowsCrt(c.Contract):
    kind: Literal['windows_crt']
    components: tuple[CrtComponent, ...]
    report_ref: QualificationRef

    @model_validator(mode='after')
    def complete(self):
        if tuple(item.name for item in self.components) != CRT_NAMES:
            raise ValueError('All eight actual CRT components are required')
        return self


class Libc(c.Contract):
    kind: Literal['libc']
    family: Literal['glibc']
    version: tuple[U32, U32, U32]
    report_ref: QualificationRef


TargetCondition = Annotated[OsFloor | PythonAbi | CpuFeatures | WindowsCrt | Libc, Field(discriminator='kind')]


class QualificationTarget(c.Contract):
    os: Literal['windows', 'linux', 'macos']
    arch: Literal['x86_64', 'aarch64']
    conditions: tuple[TargetCondition, ...]

    @model_validator(mode='after')
    def target(self):
        if self.arch == 'aarch64' and self.os != 'macos':
            raise ValueError('Unsupported qualification target pair')
        expected = ('os_floor', 'python_abi', 'cpu_features')
        expected += ('windows_crt',) if self.os == 'windows' else ('libc',) if self.os == 'linux' else ()
        if tuple(item.kind for item in self.conditions) != expected:
            raise ValueError('Complete target conditions must have fixed order')
        if self.conditions[0].product != {'windows': 'windows_nt', 'linux': 'linux_kernel', 'macos': 'darwin'}[self.os]:
            raise ValueError('Target floor product differs')
        features = self.conditions[2].features
        if self.arch == 'x86_64' and 'arm_neon' in features or self.arch == 'aarch64' and any(f.startswith('x86_') for f in features):
            raise ValueError('CPU features belong to another architecture')
        return self


class QualificationFile(c.Contract):
    relative_path: str = Field(strict=True, min_length=1, max_length=32768)
    bytes: I64
    sha256: c.Sha256

    @model_validator(mode='after')
    def relative(self):
        _relative(self.relative_path)
        return self


class QualificationProfile(c.Contract):
    name: Literal['api', 'worker', 'mcp', 'asr']
    artifact_version: c.Identifier
    executable: str = Field(strict=True)
    bootstrap: str = Field(strict=True)
    entry_module: Literal['video_creator.cli.main', 'video_creator.media.asr_worker']
    command: Literal['serve', 'worker', 'mcp-stdio'] | None
    adapter_module: Literal['video_creator.cli.native_startup'] | None
    adapter_callable: Literal['main_qualified'] | None
    load_policy_sha256: c.Sha256
    required_files: tuple[QualificationFile, ...]
    required_files_sha256: c.Sha256
    report_refs: tuple[QualificationRef, ...]

    @model_validator(mode='after')
    def profile(self):
        _relative(self.executable)
        _relative(self.bootstrap)
        expected = ('video_creator.media.asr_worker', None, None, None) if self.name == 'asr' else (
            'video_creator.cli.main', {'api': 'serve', 'worker': 'worker', 'mcp': 'mcp-stdio'}[self.name],
            'video_creator.cli.native_startup', 'main_qualified')
        if (self.entry_module, self.command, self.adapter_module, self.adapter_callable) != expected:
            raise ValueError('Profile entry differs from the fixed indexed plan')
        names = tuple(item.relative_path for item in self.required_files)
        if not names or len(names) > 65536 or names != tuple(sorted(set(names))):
            raise ValueError('Profile requires a complete sorted distinct file map')
        if body_sha([item.model_dump(mode='json') for item in self.required_files]) != self.required_files_sha256:
            raise ValueError('Profile required file map differs')
        check_refs(self.report_refs)
        return self


class InstallationQualificationRecord(c.Contract):
    format: Literal['installation-qualification-record-v1']
    record_id: c.Identifier
    revision: PositiveI64
    target: QualificationTarget
    registration_sha256: c.Sha256
    resource_manifest_sha256: c.Sha256
    runtime_manifest_sha256: c.Sha256
    host_build_receipt_sha256: c.Sha256
    full_file_map_sha256: c.Sha256
    engine_partition_sha256: c.Sha256
    workflow_version: Literal['registered-media-bundle-v1']
    driver_profile: Literal['registered-production-drivers-v1']
    roles: tuple[Literal['api', 'mcp', 'worker'], ...]
    profiles: tuple[QualificationProfile, ...]
    qualification_suite_ref: QualificationRef
    runtime_report_refs: tuple[QualificationRef, ...]
    license_evidence_refs: tuple[QualificationRef, ...]
    build_provenance_refs: tuple[QualificationRef, ...]
    independent_review_ref: QualificationRef
    independent_acceptance_ref: QualificationRef
    valid_from_us: PositiveI64
    expires_at_us: PositiveI64
    issuer_id: c.Identifier
    trust_mode: Literal['publisher', 'local_verifier']
    signature: str = Field(strict=True, pattern=r'^[a-f0-9]{128}$')

    @model_validator(mode='after')
    def coverage(self):
        if self.roles != ('api', 'mcp', 'worker') or tuple(profile.name for profile in self.profiles) != PROFILES:
            raise ValueError('All roles and all four original profiles are required')
        if self.valid_from_us >= self.expires_at_us:
            raise ValueError('Qualification validity must be finite and increasing')
        for refs in (self.runtime_report_refs, self.license_evidence_refs, self.build_provenance_refs):
            check_refs(refs)
        return self

    def ref(self):
        return QualificationRef(document_id=self.record_id, revision=self.revision, sha256=body_sha(self))

    def verify_signature(self, public_key):
        try:
            from cryptography.exceptions import InvalidSignature
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        except ImportError as error:
            raise EngineError('qualification_unavailable','Approved Ed25519 runtime dependency is unavailable',503) from error

        if type(public_key) is not bytes or len(public_key) != 32:
            raise EngineError('qualification_unavailable', 'Original admitted Ed25519 anchor is unavailable', 503)
        body = self.model_dump(mode='json')
        body.pop('signature')
        try:
            Ed25519PublicKey.from_public_bytes(public_key).verify(bytes.fromhex(self.signature), canonical_bytes(body))
        except (InvalidSignature, ValueError) as error:
            raise EngineError('qualification_unknown', 'Qualification signature does not match the admitted source', 503) from error


class TrustAdmission(c.Contract):
    action_id: c.Identifier
    accepted_at_us: PositiveI64
    issuer_id: c.Identifier
    trust_mode: Literal['publisher', 'local_verifier']
    public_key_hex: str = Field(strict=True, pattern=r'^[a-f0-9]{64}$')
    material_refs: tuple[QualificationRef, ...]
    host_build_receipt_sha256: c.Sha256
    intent_sha256: c.Sha256

    @model_validator(mode='after')
    def refs(self):
        check_refs(self.material_refs)
        return self


class TrustSnapshot(c.Contract):
    format: Literal['installation-qualification-trust-snapshot-v1']
    instance_id: c.Identifier
    registry_revision: PositiveI64
    trust_admission_ref: QualificationRef
    current_record_ref: QualificationRef | None
    state: Literal['not_ready', 'qualified', 'revoked']

    @model_validator(mode='after')
    def state_ref(self):
        if self.state == 'qualified' and self.current_record_ref is None:
            raise ValueError('Qualified snapshot requires the complete original record')
        return self


class QualificationBinding(c.Contract):
    record: InstallationQualificationRecord
    record_sha256: c.Sha256
    registry_revision: PositiveI64
    revocation_floor: I64
    checked_at_us: PositiveI64

    @model_validator(mode='after')
    def record_binding(self):
        if body_sha(self.record) != self.record_sha256 or len(canonical_bytes(self.record)) > 1024 * 1024:
            raise ValueError('Qualification record full hash/size differs')
        if self.revocation_floor > self.registry_revision:
            raise ValueError('Qualification registry is behind its floor')
        return self


class LeaseBinding(c.Contract):
    lease_id: c.Identifier
    observation_id: c.Identifier
    record_ref: QualificationRef
    registry_revision: PositiveI64
    revocation_floor: I64


class InstallationRecordAdmission(c.Contract):
    """Actual installer receipt; deserialization alone establishes no source."""
    action_id: c.Identifier
    accepted_at_us: PositiveI64
    kind: Literal['record_admit']
    trust_admission_ref: QualificationRef
    expected_registry_revision: PositiveI64
    record: InstallationQualificationRecord
    record_sha256: c.Sha256
    host_build_receipt_sha256: c.Sha256
    intent_sha256: c.Sha256
    material_index_sha256: c.Sha256

    @model_validator(mode='after')
    def original_record(self):
        if body_sha(self.record)!=self.record_sha256 or len(canonical_bytes(self.record))>1024*1024:
            raise ValueError('Original complete installation record hash/size differs')
        if self.record.host_build_receipt_sha256!=self.host_build_receipt_sha256:
            raise ValueError('Installer action and complete record belong to different builds')
        return self
