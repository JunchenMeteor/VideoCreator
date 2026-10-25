"""Private immutable installation facts; never a portable execution ticket."""

import hashlib
import json
from pathlib import PurePosixPath, PureWindowsPath
from typing import Literal

from pydantic import Field, field_validator, model_validator

from video_creator.domain import contracts as c
from video_creator.infrastructure.held_authority import (
    HeldFileFact,
    NativeLaunchContext,
    _fields,
    _uint,
)

NativeRole = Literal['api', 'mcp', 'worker']


def private_body_sha256(model):
    data = json.dumps(model.model_dump(mode='json'), ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')
    return hashlib.sha256(data).hexdigest()


def local_absolute_path(value):
    if (type(value) is not str or not value or len(value) > 32768
            or any(ord(char) < 32 or 0xD800 <= ord(char) <= 0xDFFF for char in value)
            or value.startswith(('\\\\', '//'))):
        raise ValueError('A finite absolute local installation path is required')
    if '\\' in value or ':' in value:
        path = PureWindowsPath(value)
        if (not path.is_absolute() or len(path.drive) != 2 or path.drive[1] != ':'
                or any(':' in part or part.endswith((' ', '.')) for part in path.parts[1:])):
            raise ValueError('UNC/device/ADS installation paths are not admitted')
    else:
        path = PurePosixPath(value)
        if not path.is_absolute():
            raise ValueError('Absolute installation path required')
    # PurePath normalizes dot segments; inspect the original spelling as well.
    if any(part in ('.', '..') for part in value.replace('\\', '/').split('/')):
        raise ValueError('Installation path cannot contain dot segments')
    return str(path)


class NativeBuildEvidenceRef(c.Contract):
    kind: Literal['host_source', 'lockfile', 'tool', 'producer_input', 'license', 'qualification']
    reference_id: c.Identifier
    content_sha256: c.Sha256


class NativeBuildReceipt(c.Contract):
    """External final-host build facts, no self-installed signer or qualification."""
    format: Literal['native-build-receipt-v1'] = 'native-build-receipt-v1'
    build_id: c.Identifier
    target: c.Identifier
    host_image_bytes: int = Field(gt=0, le=9_223_372_036_854_775_807, strict=True)
    host_image_sha256: c.Sha256
    payload_manifest_sha256: c.Sha256
    registration_sha256: c.Sha256
    resource_manifest_sha256: c.Sha256
    runtime_manifest_sha256: c.Sha256
    evidence_refs: tuple[NativeBuildEvidenceRef, ...] = Field(min_length=4, max_length=256)

    @model_validator(mode='after')
    def original_build_inputs(self):
        identities = {(item.kind, item.reference_id) for item in self.evidence_refs}
        if (len(identities) != len(self.evidence_refs)
                or not {'host_source', 'lockfile', 'tool', 'producer_input'} <= {item.kind for item in self.evidence_refs}):
            raise ValueError('External build receipt requires its actual distinct source/lock/tool/producer inputs')
        c.reject_secrets(self.model_dump(mode='json'))
        return self


class NativeInstallationInputs(c.Contract):
    """Proposal identities; trusted installation observation must open all inputs."""
    composition_root: str
    installed_native_image: str
    installed_native_image_bytes: int = Field(gt=0, le=9_223_372_036_854_775_807, strict=True)
    installed_native_image_sha256: c.Sha256
    payload_root: str
    payload_manifest_sha256: c.Sha256
    registration_sha256: c.Sha256
    resource_manifest_sha256: c.Sha256
    runtime_manifest_sha256: c.Sha256
    expected_files: tuple[HeldFileFact, ...]
    engine_file_names: tuple[str, ...]
    build_receipt: NativeBuildReceipt
    build_receipt_sha256: c.Sha256

    @field_validator('composition_root', 'installed_native_image', 'payload_root')
    @classmethod
    def absolute_paths(cls, value):
        return local_absolute_path(value)

    @field_validator('expected_files', mode='before')
    @classmethod
    def exact_file_integers(cls, value):
        if type(value) not in (list, tuple):
            raise ValueError('Full installation map must be a finite array')
        for item in value:
            if type(item) is HeldFileFact:
                _uint(item.bytes)
            else:
                _uint(_fields(item, ('relative_path', 'bytes', 'sha256'))['bytes'])
        return value

    @model_validator(mode='after')
    def actual_full_graph_identity(self):
        NativeLaunchContext('installed-body', 'api', self.registration_sha256,
            self.resource_manifest_sha256, self.runtime_manifest_sha256, self.expected_files, self.engine_file_names)
        names = tuple(item.relative_path for item in self.expected_files)
        if names != tuple(sorted(names)) or self.engine_file_names != tuple(sorted(self.engine_file_names)):
            raise ValueError('Complete installation partitions must have the fixed original ordering')
        receipt = self.build_receipt
        if (self.build_receipt_sha256 != private_body_sha256(receipt)
                or (receipt.host_image_bytes, receipt.host_image_sha256, receipt.payload_manifest_sha256,
                    receipt.registration_sha256, receipt.resource_manifest_sha256, receipt.runtime_manifest_sha256) != (
                    self.installed_native_image_bytes, self.installed_native_image_sha256, self.payload_manifest_sha256,
                    self.registration_sha256, self.resource_manifest_sha256, self.runtime_manifest_sha256)):
            raise ValueError('Independent build receipt and complete actual installation inputs must agree')
        c.reject_secrets(self.model_dump(mode='json'))
        return self


class InstalledNativeRecordRef(c.Contract):
    record_id: c.Identifier
    revision: int = Field(gt=0, le=9_223_372_036_854_775_807, strict=True)
    content_sha256: c.Sha256


class ExecutionRegistrationRef(c.Contract):
    registration_id: c.Identifier
    revision: int = Field(gt=0, le=9_223_372_036_854_775_807, strict=True)
    content_sha256: c.Sha256


class InstalledNativeRecordBody(NativeInstallationInputs):
    format: Literal['installed-native-record-v1'] = 'installed-native-record-v1'
    record_id: c.Identifier
    revision: int = Field(gt=0, le=9_223_372_036_854_775_807, strict=True)
    instance_id: c.Identifier
    owner_subject: c.Identifier
    os_subject: str = Field(min_length=1, max_length=200)
    directory_device: int = Field(ge=0, strict=True)
    directory_inode: int = Field(ge=0, strict=True)
    owner_binding_generation: int = Field(gt=0, strict=True)
    owner_binding_action_id: c.Identifier
    authentication_binding_id: c.Identifier


class InstalledExecutionRegistrationBody(c.Contract):
    format: Literal['installed-execution-registration-v1'] = 'installed-execution-registration-v1'
    registration_id: c.Identifier
    revision: int = Field(gt=0, le=9_223_372_036_854_775_807, strict=True)
    instance_id: c.Identifier
    owner_subject: c.Identifier
    executing_principal_id: c.Identifier
    role: NativeRole
    project_ids: tuple[c.Identifier, ...] = Field(min_length=1, max_length=256)
    registration_sha256: c.Sha256
    resource_manifest_sha256: c.Sha256
    runtime_manifest_sha256: c.Sha256
    allowed_source_namespaces: tuple[tuple[c.Identifier, c.Identifier], ...] = Field(min_length=1, max_length=256)
    installed_record_ref: InstalledNativeRecordRef
    installation_inputs_sha256: c.Sha256
    expires_at_us: int = Field(gt=0, le=9_223_372_036_854_775_807, strict=True)
    owner_binding_generation: int = Field(gt=0, strict=True)
    owner_binding_action_id: c.Identifier
    authentication_binding_id: c.Identifier

    @model_validator(mode='after')
    def finite_real_owner_scope(self):
        if (self.executing_principal_id != self.owner_subject
                or len(set(self.project_ids)) != len(self.project_ids)
                or len(set(self.allowed_source_namespaces)) != len(self.allowed_source_namespaces)):
            raise ValueError('V1 execution is one actual domain Owner with distinct explicit finite scopes')
        for system, namespace in self.allowed_source_namespaces:
            c.SourceBinding(system=system, namespace=namespace)
        c.reject_secrets(self.model_dump(mode='json'))
        return self


class ExecutionRegistrationActionReceipt(c.Contract):
    """Independent Owner action; it is not a PolicyRef or production permit."""
    format: Literal['execution-registration-action-v1'] = 'execution-registration-action-v1'
    action_id: c.Identifier
    instance_id: c.Identifier
    administrator_id: c.Identifier
    owner_subject: c.Identifier
    authentication_binding_id: c.Identifier
    authentication_source: Literal['native_owner_session', 'headless_administrator']
    owner_binding_generation: int = Field(gt=0, strict=True)
    owner_binding_action_id: c.Identifier
    project_ids: tuple[c.Identifier, ...] = Field(min_length=1, max_length=256)
    action: Literal['install', 'replace', 'select', 'revoke']
    installed_record_ref: InstalledNativeRecordRef
    execution_refs: tuple[ExecutionRegistrationRef, ...] = Field(min_length=1, max_length=3)
    idempotency_key: c.Identifier
    request_sha256: c.Sha256
    authorized_at_us: int = Field(gt=0, strict=True)
    registry_revision: int = Field(gt=0, le=9_223_372_036_854_775_806, strict=True)
    reason: str | None = Field(default=None, min_length=1, max_length=2000)

    @model_validator(mode='after')
    def exact_original_action(self):
        if (len(set(self.project_ids)) != len(self.project_ids)
                or len({ref.registration_id for ref in self.execution_refs}) != len(self.execution_refs)
                or (self.action == 'revoke') != (self.reason is not None)):
            raise ValueError('Action requires distinct exact original targets and explicit revocation reason only')
        c.reject_secrets(self.model_dump(mode='json'))
        return self


class InstallExecutionRegistration(c.Contract):
    registration_id: c.Identifier
    role: NativeRole
    project_ids: tuple[c.Identifier, ...] = Field(min_length=1, max_length=256)
    allowed_source_namespaces: tuple[tuple[c.Identifier, c.Identifier], ...] = Field(min_length=1, max_length=256)
    expires_at_us: int = Field(gt=0, le=9_223_372_036_854_775_807, strict=True)
    previous_ref: ExecutionRegistrationRef | None = None


class InstallNativeExecution(c.Contract):
    record_id: c.Identifier
    installation: NativeInstallationInputs
    registrations: tuple[InstallExecutionRegistration, ...] = Field(min_length=1, max_length=3)
    previous_installed_ref: InstalledNativeRecordRef | None = None

    @model_validator(mode='after')
    def exact_roles(self):
        if (len({item.role for item in self.registrations}) != len(self.registrations)
                or len({item.registration_id for item in self.registrations}) != len(self.registrations)):
            raise ValueError('One explicit action has at most one exact registration per role')
        for item in self.registrations:
            if (len(set(item.project_ids)) != len(item.project_ids)
                    or len(set(item.allowed_source_namespaces)) != len(item.allowed_source_namespaces)):
                raise ValueError('Role scope cannot repeat project or source identities')
        return self


class SelectNativeExecution(c.Contract):
    registration_ref: ExecutionRegistrationRef


class RevokeNativeExecution(c.Contract):
    registration_ref: ExecutionRegistrationRef
    reason: str = Field(min_length=1, max_length=2000)
