"""Development checkout facts source for ADR0077; never production evidence.

The bytes of this checkout and of the local resource files named by the
development registration are the whole fact source. That proves only "these
bytes are consistent on this checkout". It is not a held pipe observation, not
an Owner-protected build, not an independent installation record and not a
qualification, so it must never stand in for installation, release, Gate0 or
acceptance evidence.

Only `video_creator.cli.development_host` may import this module. It is not a
third production installation source and implements no qualification.
"""

import threading
from pathlib import Path

from video_creator.application.media_registration import (
    PACKAGE_ROOT,
    _hash,
    _local_file,
    _package_sources,
)
from video_creator.application.production_admissions import InstalledProductionEvidence
from video_creator.domain.errors import EngineError
from video_creator.domain.local_material_production import (
    RegistrationConfigLocalV1,
    parse_local_material_resources,
)
from video_creator.infrastructure.held_authority import (
    HeldFileFact,
    NativeLaunchContext,
)

WORKFLOW_VERSION = 'registered-media-bundle-v1'
DRIVER_PROFILE = 'registered-production-drivers-v1'


def _denied(code: str, message: str, status_code: int) -> EngineError:
    return EngineError(code, message, status_code)


def engine_source_facts() -> tuple[tuple[str, str, int], ...]:
    """Actual (name, sha256, size) of every current engine package source.

    Delegates to the installer's own `_package_sources`/`_local_file` so the
    development host cannot drift from the registered installation map.
    """
    try:
        names = sorted(_package_sources(PACKAGE_ROOT))
    except EngineError as error:
        raise _denied('development_engine_incomplete',
                      'The engine package source map cannot be read as fixed local files', 503) from error
    facts = []
    for name in names:
        try:
            target = _local_file(PACKAGE_ROOT, name)
            facts.append((name, _hash(target), target.stat().st_size))
        except (EngineError, OSError) as error:
            raise _denied('development_engine_incomplete',
                          'The registered engine package sources changed or became unavailable', 503) from error
    return tuple(facts)


def _resource_target(root: Path, relative: str, *, name: str) -> Path:
    try:
        return _local_file(root, relative)
    except (EngineError, OSError) as error:
        raise _denied('development_resource_missing',
                      f'Indexed local resource {name} is unavailable as a fixed local file', 503) from error


def indexed_resource_facts(root: Path, config) -> tuple[tuple[str, str, int], ...]:
    """Actual (relative name, sha256, size) of the indexed non-engine resources.

    Names stay relative to the registration directory, matching the engine
    partition's fixed relative identities. Every configured hash is enforced
    here, so a changed resource is `development_resource_changed`, not a
    silently accepted config value.
    """
    manifest_path = _resource_target(root, config.production_resource_manifest,
                                     name=config.production_resource_manifest)
    try:
        index = parse_local_material_resources(manifest_path.read_bytes())
    except (EngineError, OSError) as error:
        raise _denied('development_resource_changed',
                      'The pinned local resource manifest is not its registered document', 503) from error
    runtime_path = _resource_target(manifest_path.parent, index.runtime_manifest,
                                    name=index.runtime_manifest)
    try:
        runtime_name = runtime_path.relative_to(root).as_posix()
    except ValueError as error:
        raise _denied('development_resource_missing',
                      'The indexed runtime manifest must stay inside the registration directory', 503) from error
    targets = [
        (config.production_resource_manifest, manifest_path, config.production_resource_manifest_sha256),
        (runtime_name, runtime_path, config.production_runtime_manifest_sha256),
        (config.ffmpeg, _resource_target(root, config.ffmpeg, name=config.ffmpeg), config.ffmpeg_sha256),
        (config.ffprobe, _resource_target(root, config.ffprobe, name=config.ffprobe), config.ffprobe_sha256),
    ]
    if config.asr_resource_manifest is not None:
        targets.append((config.asr_resource_manifest,
                        _resource_target(root, config.asr_resource_manifest, name=config.asr_resource_manifest),
                        config.asr_resource_manifest_sha256))
    names = [name for name, _path, _sha in targets]
    if len(set(names)) != len(names):
        raise _denied('development_identity_collision',
                      'Indexed resource identities must be distinct', 422)
    facts = []
    for name, path, expected in targets:
        actual = _hash(path)
        if actual != expected:
            raise _denied('development_resource_changed',
                          f'Indexed local resource {name} differs from the registered hash', 503)
        facts.append((name, actual, path.stat().st_size))
    return tuple(sorted(facts))


def assert_engine_registration(config, facts) -> None:
    """The registration must cover exactly the current package and match it."""
    declared = config.engine_source_sha256
    actual = {name: sha for name, sha, _size in facts}
    if set(declared) != set(actual):
        raise _denied('development_engine_incomplete',
                      'The development registration must cover the complete current engine package', 503)
    for name in sorted(declared):
        if declared[name] != actual[name]:
            raise _denied('development_code_changed',
                          'Engine code differs from the development registration; regenerate it after every edit', 503)


def assert_distinct_identities(engine_facts, resource_facts) -> None:
    engine_names = {name for name, _sha, _size in engine_facts}
    resource_names = {name for name, _sha, _size in resource_facts}
    if engine_names & resource_names:
        raise _denied('development_identity_collision',
                      'Engine and resource relative identities must not collide', 422)


def launch_context(*, instance_id: str, role: str, registration_sha256: str, config,
                   engine_facts, resource_facts) -> NativeLaunchContext:
    """Real complete file map from the same hashed facts, never a stub."""
    expected = tuple(HeldFileFact(name, size, sha)
                     for name, sha, size in tuple(engine_facts) + tuple(resource_facts))
    return NativeLaunchContext(
        instance_id, role, registration_sha256,
        config.production_resource_manifest_sha256, config.production_runtime_manifest_sha256,
        expected, tuple(name for name, _sha, _size in engine_facts))


class DevelopmentLaunchConnection:
    """In-process launch identity holder; it owns no OS handle or pipe."""

    __slots__ = ('_closed', 'context')

    def __init__(self, context: NativeLaunchContext):
        if type(context) is not NativeLaunchContext:
            raise _denied('development_installation_denied',
                          'A real complete development launch context is required', 403)
        self.context = context
        self._closed = False

    def close(self) -> None:
        self._closed = True


class DevelopmentLaunchBuild:
    """Placeholder for the native Owner-protected build; it touches no file."""

    __slots__ = ('_closed',)

    def __init__(self):
        self._closed = False

    def close(self) -> None:
        self._closed = True


class DevelopmentInstallationAuthority:
    """Development-only evidence adapter: real disk hashes, no qualification.

    `observe` and `assert_current` re-read and re-hash the whole engine and
    resource partitions outside any writer. `assert_local_current` is the short
    writer hook: object/epoch/thread/closed only, no I/O, hash, DB or blocking
    lock. This type is deliberately not `NativeInstallationAuthority`, so
    production admissions never take the qualification branch for it.
    """

    def __init__(self, engine, config, *, registration_path: Path, registration_sha256: str,
                 root: Path, connection: DevelopmentLaunchConnection):
        self._engine = engine
        self._config = config
        self._registration_path = Path(registration_path)
        self._registration_sha256 = registration_sha256
        self._root = Path(root)
        self._connection = connection
        self._lock = threading.RLock()
        self._epoch = object()
        self._originals = {}
        self._retired = False
        self._closed = False
        if type(config) is RegistrationConfigLocalV1:
            # ADR0077 section 8.5: the API role deliberately owns no second
            # `RegisteredMediaRuntime`, so it has no `_local_material_plan_source`.
            # This parsed, real local-v1 registration is the equivalent in-process
            # signal that the instance is configured for local production. Only
            # this development authority sets it; production never constructs it.
            engine._development_local_registration = config

    @property
    def connection(self) -> DevelopmentLaunchConnection:
        return self._connection

    def _alive(self) -> None:
        if self._retired or self._closed:
            raise _denied('development_installation_retired',
                          'The development installation authority is closed', 503)

    def _registration_sha(self) -> str:
        path = self._registration_path
        try:
            if path.is_symlink() or path.is_junction() or not path.is_file() or path.stat().st_size > 1024 * 1024:
                raise _denied('development_registration_missing',
                              'The development registration file is unavailable', 503)
            return _hash(path)
        except OSError as error:
            raise _denied('development_registration_missing',
                          'The development registration file is unavailable', 503) from error

    def _current_facts(self):
        if self._registration_sha() != self._registration_sha256:
            raise _denied('development_registration_changed',
                          'The development registration changed after startup; regenerate it', 503)
        engine_facts = engine_source_facts()
        assert_engine_registration(self._config, engine_facts)
        resource_facts = indexed_resource_facts(self._root, self._config)
        assert_distinct_identities(engine_facts, resource_facts)
        return engine_facts, resource_facts

    def observe(self) -> InstalledProductionEvidence:
        with self._lock:
            self._alive()
            engine_facts, resource_facts = self._current_facts()
            evidence = InstalledProductionEvidence(
                self._engine.instance_id, self._registration_sha256,
                self._config.production_resource_manifest_sha256,
                self._config.production_runtime_manifest_sha256,
                WORKFLOW_VERSION, DRIVER_PROFILE, self._engine.clock(),
                tuple((name, sha) for name, sha, _size in engine_facts),
                tuple((name, sha) for name, sha, _size in resource_facts))
            self._originals[id(evidence)] = (evidence, self._epoch, threading.get_ident())
            return evidence

    def _original(self, observation) -> InstalledProductionEvidence:
        self._alive()
        original = self._originals.get(id(observation))
        if (type(observation) is not InstalledProductionEvidence or original is None
                or original[0] is not observation or original[1] is not self._epoch
                or original[2] != threading.get_ident()):
            raise _denied('development_evidence_foreign',
                          'Exact current-thread development evidence from this authority is required', 409)
        return original[0]

    def assert_current(self, observation) -> None:
        with self._lock:
            original = self._original(observation)
            engine_facts, resource_facts = self._current_facts()
            if tuple((name, sha) for name, sha, _size in engine_facts) != original.engine_source_sha256:
                raise _denied('development_code_changed',
                              'Engine source bytes changed since this observation', 503)
            if tuple((name, sha) for name, sha, _size in resource_facts) != original.indexed_resource_sha256:
                raise _denied('development_resource_changed',
                              'Indexed resource bytes changed since this observation', 503)

    def assert_local_current(self, observation) -> None:
        # Short writer hook: no hashing, DB read, file open or blocking lock.
        if not self._lock.acquire(blocking=False):
            raise _denied('installation_session_busy',
                          'The development authority is in external observation', 503)
        try:
            self._original(observation)
        finally:
            self._lock.release()

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._retired = True
            self._originals.clear()
            self._connection.close()
            self._closed = True
