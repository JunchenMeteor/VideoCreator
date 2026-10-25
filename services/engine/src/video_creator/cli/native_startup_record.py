"""Unique private native carrier; resource identities are not execution rights."""

import json
from dataclasses import dataclass
from pathlib import Path

from video_creator.domain.errors import EngineError
from video_creator.infrastructure.held_authority import (
    FRAME_LIMIT,
    HeldFileFact,
    NativeLaunchContext,
    _fields,
    _json,
    _text,
)
from video_creator.infrastructure.windows_authority_pipe import _local_image_path

FORMAT = 'native-startup-binding-v1'
FIELDS = ('format', 'instance_id', 'role', 'installed_native_image',
          'installed_native_image_sha256', 'registration_sha256',
          'resource_manifest_sha256', 'runtime_manifest_sha256',
          'expected_files', 'engine_file_names')


@dataclass(frozen=True, repr=False)
class NativeStartupRecord:
    context: NativeLaunchContext
    installed_native_image: Path
    installed_native_image_sha256: str

    @classmethod
    def parse(cls, data: bytes):
        try:
            body = _fields(_json(data), FIELDS)
            if body['format'] != FORMAT:
                raise ValueError('Unsupported private record version')
            canonical = json.dumps(body, ensure_ascii=False, sort_keys=True,
                                   separators=(',', ':'), allow_nan=False).encode('utf-8')
            if data != canonical or len(canonical) > FRAME_LIMIT:
                raise ValueError('Noncanonical private record')
            if type(body['expected_files']) is not list or type(body['engine_file_names']) is not list:
                raise ValueError('Private full maps must be arrays')
            files = tuple(HeldFileFact(**_fields(item, ('relative_path', 'bytes', 'sha256')))
                          for item in body['expected_files'])
            names = tuple(body['engine_file_names'])
            if (tuple(item.relative_path for item in files) != tuple(sorted(item.relative_path for item in files))
                    or any(type(name) is not str for name in names) or names != tuple(sorted(names))):
                raise ValueError('Private full map ordering differs')
            context = NativeLaunchContext(body['instance_id'], body['role'], body['registration_sha256'],
                body['resource_manifest_sha256'], body['runtime_manifest_sha256'], files, names)
            image = _local_image_path(_text(body['installed_native_image'], limit=32768))
            from video_creator.infrastructure.held_authority import _sha

            image_sha = _sha(body['installed_native_image_sha256'])
            return cls(context, image, image_sha)
        except (EngineError, ValueError, TypeError, UnicodeError, RecursionError) as error:
            raise EngineError('native_startup_record_invalid', 'Private native startup record is invalid', 422) from error
