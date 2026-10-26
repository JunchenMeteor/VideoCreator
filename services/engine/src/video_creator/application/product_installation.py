"""ADR0084 product trusted-startup authority: installation facts only, no management."""

from __future__ import annotations

import json
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from video_creator.application.media_registration import (
    PACKAGE_ROOT,
    _hash,
    _local_file,
    _package_sources,
)
from video_creator.application.production_admissions import InstalledProductionEvidence
from video_creator.domain.errors import EngineError

WORKFLOW = 'registered-media-bundle-v1'
DRIVER = 'registered-production-drivers-v1'


@dataclass(eq=False, repr=False)
class ProductStartupContext:
    instance_id: str
    role: str


class ProductStartupConnection:
    def __init__(self, context):
        self.context = context
        self._closed = False

    def close(self):
        self._closed = True


class ProductStartupBuild:
    def __init__(self):
        self._closed = False

    def close(self):
        self._closed = True


class ProductInstallationAuthority:
    def __init__(self, engine, *, record_path: Path, record_sha256: str, registration: Path,
                 registration_sha256: str, role: str):
        self.engine = engine
        self.record_path = Path(record_path)
        self.record_sha256 = record_sha256
        self.registration = Path(registration)
        self.registration_sha256 = registration_sha256
        self.role = role
        self._lock = threading.RLock()
        self._observations = {}
        self._cached_observation = None
        self._closed = False
        self.connection = None

    def _record(self):
        raw = self.record_path.read_bytes()
        if hashlib_sha(raw) != self.record_sha256:
            raise EngineError('trusted_startup_record_changed', 'Installation record differs from its pinned bytes', 503)
        try:
            value = json.loads(raw)
        except (ValueError, TypeError):
            raise EngineError('trusted_startup_record_invalid', 'Installation record is not canonical JSON', 422) from None
        return value

    def _files(self, record):
        expected = []
        for fact in record.get('expected_files', []):
            path = Path(record['install_root']) / fact['relative_path']
            if (path.is_symlink() or not path.is_file() or path.stat().st_size != fact['bytes']
                    or _hash(path) != fact['sha256']):
                raise EngineError('trusted_startup_bytes_changed',
                                  'Installed file differs from the provisioning record', 503)
            expected.append((fact['relative_path'], fact['sha256']))
        for tree in record.get('expected_trees', []):
            base = Path(record['install_root']) / tree['relative_path']
            files = self._tree_files(base)
            body = [(name, size, sha) for name, size, sha in files]
            digest = hashlib_sha(json.dumps(body, ensure_ascii=False, sort_keys=True,
                                            separators=(',', ':')).encode('utf-8'))
            if (len(files), sum(size for _name, size, _sha in files), digest) != (
                    tree['file_count'], tree['bytes'], tree['sha256']):
                raise EngineError('trusted_startup_bytes_changed',
                                  'Installed tree differs from the provisioning record', 503)
            for name, _size, sha in files:
                expected.append((tree['relative_path'].rstrip('/') + '/' + name, sha))
        return tuple(sorted(set(expected)))

    @staticmethod
    def _tree_files(base: Path):
        if not base.is_dir():
            return []
        return [(path.relative_to(base).as_posix(), path.stat().st_size, _hash(path))
                for path in sorted(base.rglob('*')) if path.is_file()]

    def observe(self):
        with self._lock:
            started = time.monotonic()
            if self._closed:
                raise EngineError('trusted_startup_retired', 'Product installation authority was closed', 503)
            record = self._record()
            if (record.get('format') != 'installation-provisioning-v1' or record.get('complete') is not True
                    or record.get('instance_id') != self.engine.instance_id
                    or record.get('registration_sha256') != self.registration_sha256
                    or hashlib_sha(self.registration.read_bytes()) != self.registration_sha256):
                raise EngineError('trusted_startup_registration_conflict', 'Registration record or bytes changed', 409)
            cache_key = (self.record_sha256, record.get('install_root'), self.registration_sha256,
                         self.engine.instance_id)
            if self._cached_observation is not None and self._cached_observation[0] == cache_key:
                evidence = self._cached_observation[1]
                self._observations[id(evidence)] = (evidence, threading.get_ident())
                print(json.dumps({'event': 'installation_observe', 'cached': True,
                                  'elapsed_seconds': round(time.monotonic() - started, 4)},
                                 ensure_ascii=False), file=sys.stderr, flush=True)
                return evidence
            files = self._files(record)
            evidence = InstalledProductionEvidence(
                instance_id=self.engine.instance_id,
                registration_sha256=record['registration_sha256'],
                resource_manifest_sha256=record['resource_manifest_sha256'],
                runtime_manifest_sha256=record['runtime_manifest_sha256'],
                workflow_version=WORKFLOW, driver_profile=DRIVER,
                observed_at_us=self.engine.clock(),
                engine_source_sha256=tuple(sorted(
                    (name, _hash(_local_file(PACKAGE_ROOT, name))) for name in _package_sources(PACKAGE_ROOT))),
                indexed_resource_sha256=files)
            self._observations[id(evidence)] = (evidence, threading.get_ident())
            self._cached_observation = (cache_key, evidence)
            print(json.dumps({'event': 'installation_observe', 'cached': False,
                              'indexed_files': len(files),
                              'elapsed_seconds': round(time.monotonic() - started, 4)},
                             ensure_ascii=False), file=sys.stderr, flush=True)
            return evidence

    def assert_current(self, evidence):
        with self._lock:
            held = self._observations.get(id(evidence))
            if held is None or held[0] is not evidence:
                raise EngineError('trusted_startup_retired', 'Installation observation is not retained', 503)
            fresh = self.observe()
            if (fresh.engine_source_sha256, fresh.indexed_resource_sha256) != (
                    evidence.engine_source_sha256, evidence.indexed_resource_sha256):
                raise EngineError('trusted_startup_bytes_changed', 'Installed bytes changed during production', 503)

    def assert_local_current(self, evidence):
        held = self._observations.get(id(evidence))
        if held is None or held[0] is not evidence or held[1] != threading.get_ident():
            raise EngineError('trusted_startup_session_conflict', 'Installation observation is not current', 503)

    def close(self):
        with self._lock:
            self._closed = True
            self._observations.clear()


def hashlib_sha(data: bytes) -> str:
    import hashlib
    return hashlib.sha256(data).hexdigest()
