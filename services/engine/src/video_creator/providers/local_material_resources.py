"""Sole local resource grammar plus the original installation file index."""
from __future__ import annotations

import re
from pathlib import Path

from video_creator.domain.errors import EngineError
from video_creator.domain.local_material_production import (
    parse_local_material_resources,
)
from video_creator.providers.production_resources import (
    _object,
    contained_file,
    file_sha256,
)


class LocalMaterialResources:
    def __init__(self, *, manifest_path, manifest_sha256, runtime_manifest_sha256):
        # Backend passes its original config/native-held installed manifest.
        # Factory runtime_root is instance child scratch, never this root.
        # These reads establish resource integrity, not source/Owner authority.
        path = Path(manifest_path)
        if (not path.is_absolute() or any(candidate.is_symlink() or candidate.is_junction()
                                         for candidate in (path, *path.parents)) or not path.is_file()
                or path.stat().st_size > 1_048_576 or file_sha256(path) != manifest_sha256):
            raise EngineError('local_resource_changed', 'The exact installed local resource manifest is unavailable.', 503)
        self.root = path.resolve(strict=True).parent
        if contained_file(self.root, path.name) != path.resolve(strict=True):
            raise EngineError('local_resource_denied', 'The original manifest must be within the indexed installation.', 403)
        # This file itself uses the sole exact grammar. There is no alternate
        # local parser, compatibility wrapper, TTS/video fallback or secret key.
        self.config = parse_local_material_resources(path.read_bytes())
        self.manifest_path = path.resolve(strict=True)
        self.manifest_sha256 = manifest_sha256
        self.runtime_manifest_sha256 = runtime_manifest_sha256
        index = contained_file(self.root, self.config.runtime_manifest)
        if file_sha256(index) != runtime_manifest_sha256:
            raise EngineError('local_resource_changed', 'The original local runtime index changed.', 503)
        records = _object(index, 16 * 1024 * 1024).get('files')
        if type(records) is not list or not 1 <= len(records) <= 100000:
            raise EngineError('local_resource_index_invalid', 'The installed local index requires a bounded exact file list.', 503)
        self.records = {}
        for record in records:
            if (type(record) is not dict or not {'relative_path', 'bytes', 'sha256'} <= set(record)
                    or type(record['relative_path']) is not str or type(record['bytes']) is not int
                    or record['bytes'] < 0 or type(record['sha256']) is not str
                    or not re.fullmatch('[0-9a-f]{64}', record['sha256'])
                    or record['relative_path'].casefold() in self.records):
                raise EngineError('local_resource_index_invalid', 'Each actual resource has one finite file identity.', 503)
            self.records[record['relative_path'].casefold()] = record
        for record in self.records.values():
            self.resource(record['relative_path'])
        for section in (self.config.input_audio, self.config.input_visual, self.config.edit):
            for reference in section.implementation_source_refs:
                if file_sha256(self.resource(reference.resource_name)) != reference.sha256:
                    raise EngineError('local_source_changed', 'The installed local implementation source changed.', 503)
        self.resource(self.config.edit.ffmpeg)
        self.resource(self.config.edit.ffprobe)

    def resource(self, name):
        path = contained_file(self.root, name)
        record = self.records.get(name.casefold())
        if record is None or path.stat().st_size != record['bytes'] or file_sha256(path) != record['sha256']:
            raise EngineError('local_resource_changed', 'An actual local resource differs from its original index.', 503)
        return path

    def check_sources(self, section, paths):
        # Equality here is SOURCE identity only. Owner/current, credentials,
        # admission and operation/output authority remain the original ports.
        if file_sha256(self.manifest_path) != self.manifest_sha256:
            raise EngineError('local_resource_changed', 'The exact installed manifest changed before this attempt.', 503)
        index = contained_file(self.root, self.config.runtime_manifest)
        if file_sha256(index) != self.runtime_manifest_sha256:
            raise EngineError('local_resource_changed', 'The exact installed index changed before this attempt.', 503)
        expected = set()
        for reference in section.implementation_source_refs:
            actual = file_sha256(self.resource(reference.resource_name))
            if actual != reference.sha256:
                raise EngineError('local_source_changed', 'The local adapter source changed before this attempt.', 503)
            expected.add(actual)
        if not {file_sha256(path) for path in paths} <= expected:
            raise EngineError('local_source_unregistered', 'All actual producer helpers must appear in the selected indexed source section.', 503)
