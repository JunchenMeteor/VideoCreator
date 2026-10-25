"""Development installation host entry point for ADR0077; never a release path.

This is the sole constructor of the development installation authority. Three
conditions must hold at once: explicit registration arguments, an environment
value equal to this process' actual `engine.instance_id`, and a non-frozen
build. Every refusal happens before `listener.bind`, so a rejected development
start never exposes a port or an HTTP response.

The public commands are `serve-dev` and `worker-dev`. They rewrite argv into the
existing `serve` / `worker --workflow registered-media-bundle-v1` commands and
then call `video_creator.cli.main.main(installed_service_factory=...)`.
"""

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from video_creator.api.development_marker import mark_development_host
from video_creator.application.development_installation import (
    WORKFLOW_VERSION,
    DevelopmentInstallationAuthority,
    DevelopmentLaunchBuild,
    DevelopmentLaunchConnection,
    assert_distinct_identities,
    assert_engine_registration,
    engine_source_facts,
    indexed_resource_facts,
    launch_context,
)
from video_creator.application.development_owner_initialization import (
    DEVELOPMENT_AUTHENTICATION_SOURCE,
    assert_development_owner_audit,
    create_development_production_control,
    development_owner_initialization_source,
)
from video_creator.domain.errors import EngineError

PROFILE = 'registered-media-config-local-v1'
SHA256 = re.compile('[0-9a-f]{64}')
_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_MAX_IDENTITY_LIFETIME_US = 7 * 86400_000_000
_DEVELOPMENT_ARGUMENTS = ('--development-registration', '--development-registration-sha256',
                          '--development-expires-at')


@dataclass(frozen=True)
class DevelopmentStart:
    """Explicit development start arguments; no value is read from a payload."""
    registration: Path
    registration_sha256: str
    expires_at_us: int
    data_dir: Path
    auto_owner_init: bool = False
    raw_arguments: tuple[tuple[str, str], ...] = ()
    ffmpeg: Path | None = None
    ffprobe: Path | None = None


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog='video-creator-engine')
    commands = root.add_subparsers(dest='command', required=True)
    serve = commands.add_parser('serve-dev', help='Development API host; non-production')
    serve.add_argument('--development-registration', required=True, type=Path,
                       help='Absolute local registered-media-config-local-v1 JSON')
    serve.add_argument('--development-registration-sha256', required=True,
                       help='Pinned SHA256 of that exact registration file')
    serve.add_argument('--development-expires-at', required=True,
                       help='Timezone-aware ISO8601 end of this development identity')
    serve.add_argument('--development-auto-owner-init', action='store_true',
                       help='Initialize the first Owner binding automatically; development only')
    serve.add_argument('--data-dir', required=True, type=Path)
    serve.add_argument('--host', default='127.0.0.1')
    serve.add_argument('--port', default=0, type=int)
    serve.add_argument('--allowed-origin', action='append', default=[])
    serve.add_argument('--allowed-host', action='append', default=[])
    serve.add_argument('--native-origin')
    serve.add_argument('--ffmpeg', type=Path)
    serve.add_argument('--ffprobe', type=Path)
    serve.add_argument('--control-stdin', action='store_true')
    worker = commands.add_parser('worker-dev', help='Development registered worker; non-production')
    worker.add_argument('--development-registration', required=True, type=Path)
    worker.add_argument('--development-registration-sha256', required=True)
    worker.add_argument('--development-expires-at', required=True)
    worker.add_argument('--development-auto-owner-init', action='store_true',
                        help='Initialize the first Owner binding automatically; development only')
    worker.add_argument('--data-dir', required=True, type=Path)
    worker.add_argument('--max-seconds', default=300, type=int)
    worker.add_argument('--once', action='store_true')
    worker.add_argument('--control-stdin', action='store_true')
    return root


def _expiry_microseconds(text: str) -> int:
    try:
        value = datetime.fromisoformat(text)
    except ValueError as error:
        raise EngineError('development_expiry_invalid',
                          '--development-expires-at must be a timezone-aware ISO8601 instant', 422) from error
    if value.tzinfo is None or value.utcoffset() is None:
        raise EngineError('development_expiry_invalid',
                          '--development-expires-at must carry an explicit timezone', 422)
    delta = value.astimezone(UTC) - _EPOCH
    microseconds = (delta.days * 86400 + delta.seconds) * 1_000_000 + delta.microseconds
    if microseconds <= 0:
        raise EngineError('development_expiry_invalid',
                          '--development-expires-at must be a real positive microsecond instant', 422)
    return microseconds


def _raw_development_arguments(argv) -> tuple[tuple[str, str], ...]:
    """The three development arguments exactly as written before the argv rewrite.

    `DevelopmentStart` keeps their original text so the Owner factory can prove
    it was enabled by this exact command line; `--flag value` and `--flag=value`
    are both preserved verbatim.
    """
    values = {}
    index = 0
    while index < len(argv):
        item = argv[index]
        for name in _DEVELOPMENT_ARGUMENTS:
            if item == name:
                if index + 1 < len(argv):
                    values[name] = argv[index + 1]
                index += 2
                break
            if item.startswith(name + '='):
                values[name] = item[len(name) + 1:]
                index += 1
                break
        else:
            index += 1
    if not all(name in values for name in _DEVELOPMENT_ARGUMENTS):
        return ()
    return tuple((name, values[name]) for name in _DEVELOPMENT_ARGUMENTS)


def _start(args, raw_arguments) -> DevelopmentStart:
    sha256 = args.development_registration_sha256
    if type(sha256) is not str or not SHA256.fullmatch(sha256):
        raise EngineError('development_registration_invalid',
                          '--development-registration-sha256 must be 64 lowercase hex characters', 422)
    return DevelopmentStart(registration=args.development_registration, registration_sha256=sha256,
                            expires_at_us=_expiry_microseconds(args.development_expires_at),
                            data_dir=args.data_dir,
                            auto_owner_init=bool(getattr(args, 'development_auto_owner_init', False)),
                            raw_arguments=raw_arguments,
                            ffmpeg=getattr(args, 'ffmpeg', None), ffprobe=getattr(args, 'ffprobe', None))


def _serve_argv(args) -> list[str]:
    argv = ['video-creator-engine', 'serve', '--data-dir', str(args.data_dir),
            '--host', args.host, '--port', str(args.port)]
    for origin in args.allowed_origin:
        argv += ['--allowed-origin', origin]
    for host in args.allowed_host:
        argv += ['--allowed-host', host]
    if args.native_origin is not None:
        argv += ['--native-origin', args.native_origin]
    if args.ffmpeg is not None:
        argv += ['--ffmpeg', str(args.ffmpeg)]
    if args.ffprobe is not None:
        argv += ['--ffprobe', str(args.ffprobe)]
    if args.control_stdin:
        argv.append('--control-stdin')
    return argv


def _worker_argv(args) -> list[str]:
    argv = ['video-creator-engine', 'worker', '--workflow', WORKFLOW_VERSION,
            '--data-dir', str(args.data_dir),
            '--production-config', str(args.development_registration),
            '--production-config-sha256', args.development_registration_sha256,
            '--max-seconds', str(args.max_seconds)]
    if args.once:
        argv.append('--once')
    if args.control_stdin:
        argv.append('--control-stdin')
    return argv


def _require_environment(instance_id: str) -> None:
    """(b) The only enabling value; it authorizes, it never carries scope."""
    expected = os.environ.get('VIDEO_CREATOR_DEVELOPMENT_INSTALLATION')
    if expected is None or expected != instance_id:
        raise EngineError('development_installation_denied',
                          'VIDEO_CREATOR_DEVELOPMENT_INSTALLATION must equal this instance identity', 403)


def _existing_instance_id(data_dir: Path) -> str | None:
    """Read an existing data-dir instance identity without creating the data dir.

    `worker-dev` needs the environment condition before the registered worker
    branch builds its own `EngineService`; constructing one here would create
    `Metadata.sqlite` merely to reject an unset/mismatched environment. A
    missing or unreadable instance therefore cannot satisfy condition (b) and
    is refused by the caller instead of being created as a side effect.
    """
    path = Path(data_dir) / 'Metadata.sqlite'
    if not path.is_file():
        return None
    try:
        connection = sqlite3.connect(path.absolute().as_uri() + '?mode=ro', uri=True,
                                     timeout=5, isolation_level=None)
        try:
            row = connection.execute("SELECT value FROM metadata WHERE key='instance_id'").fetchone()
        finally:
            connection.close()
    except sqlite3.Error:
        return None
    return row[0] if row is not None and type(row[0]) is str else None


def require_interactive(mode: str) -> None:
    """ADR0077 section 7: this host never enters the unattended policy path."""
    if mode != 'interactive':
        raise EngineError('development_mode_unsupported',
                          'The development host supports only interactive automation', 422)


def _guard_acceptance(bundle) -> None:
    """Refuse unattended acceptance before `EngineService.accept_production`.

    The development host cannot supply the immutable Owner policy chain an
    unattended request needs, so the refusal happens on this exact
    dev-process `BundleService` before any policy branch. Production `serve`
    never receives this wrapper.
    """
    original = bundle.create_production

    def create_production(actor, key, request):
        require_interactive(request.automation.mode)
        return original(actor, key, request)

    bundle.create_production = create_production


def _guard_execution(runtime, engine) -> None:
    """Refuse to start an unattended Run on the development worker."""
    original = runtime.invoke

    def invoke(lease, *, cancel=None, deadline_monotonic=None):
        require_interactive(engine.get_request(lease).automation.mode)
        return original(lease, cancel=cancel, deadline_monotonic=deadline_monotonic)

    runtime.invoke = invoke


def _guard_goal_creation(bundle) -> None:
    """A Goal production is `unattended` by construction; this host has no policy.

    `DailyProjectService` builds `Automation(mode='unattended', ...)`
    (`application/daily_projects.py:625`) internally, so no caller-supplied
    `automation.mode` exists to check. The development host refuses the whole
    goal entry instead of allowing an unattended production it cannot honour.
    """
    def create_project_goal(actor, key, goal, *, entry):
        raise EngineError('development_mode_unsupported',
                          'A Goal production is unattended, which this development host does not support', 422)

    bundle.create_project_goal = create_project_goal


def _read_registration(start: DevelopmentStart):
    """(a) Explicit trusted local registration file, never a task payload."""
    path = Path(start.registration)
    if (not path.is_absolute() or str(path).startswith(('\\\\', '//')) or path.is_symlink()
            or path.is_junction() or not path.is_file() or path.stat().st_size > 1024 * 1024):
        raise EngineError('development_registration_missing',
                          'The development registration must be a fixed absolute local file', 503)
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != start.registration_sha256:
        raise EngineError('development_registration_changed',
                          'The development registration differs from the pinned SHA256', 503)
    from video_creator.application.bundles import strict_json
    from video_creator.domain.local_material_production import (
        parse_local_registration_config,
    )

    try:
        payload = strict_json(raw)
    except EngineError as error:
        raise EngineError('development_registration_invalid',
                          'The development registration is not strict UTF-8 JSON', 422) from error
    if type(payload) is not dict or payload.get('format') != PROFILE:
        raise EngineError('development_registration_profile_unsupported',
                          'Only the registered-media-config-local-v1 profile is supported', 400)
    try:
        config = parse_local_registration_config(raw)
    except EngineError as error:
        raise EngineError('development_registration_invalid',
                          'The development registration does not satisfy its exact schema', 422) from error
    return config, path.resolve(), start.registration_sha256, path.resolve().parent


def _runtime_registration(start: DevelopmentStart, engine, runtime):
    """Worker uses the runtime's already parsed file, never a second parse."""
    from video_creator.application.media_registration import RegisteredMediaRuntime
    from video_creator.domain.local_material_production import RegistrationConfigLocalV1

    if type(runtime) is not RegisteredMediaRuntime or runtime.engine is not engine:
        raise EngineError('development_installation_denied',
                          'The registered worker must retain its actual same-Engine runtime', 403)
    if type(runtime.config) is not RegistrationConfigLocalV1:
        raise EngineError('development_registration_profile_unsupported',
                          'Only the registered-media-config-local-v1 profile is supported', 400)
    if (runtime.path.resolve() != Path(start.registration).resolve()
            or runtime.sha256 != start.registration_sha256):
        raise EngineError('development_registration_changed',
                          'The registered worker configuration differs from the pinned development registration', 503)
    config = runtime.config
    if runtime.installation_resource_identity != (runtime.sha256, config.production_resource_manifest_sha256,
                                                  config.production_runtime_manifest_sha256):
        raise EngineError('development_registration_changed',
                          'The registered worker resource identity differs from its configuration', 503)
    return config, runtime.path, runtime.sha256, runtime.path.parent


def _assert_no_asr_capability(config) -> None:
    """ADR0077 section 7: the development profile never loads ASR resources.

    `RegistrationConfigLocalV1` permits the four ASR fields to be present, but
    the accepted local chain keeps them null: a non-null set would make the
    registered runtime load ASR resources, which the development host does not
    support. This is a document-level capability refusal (422), never a
    retryable resource wait, and the code is not added to RESOURCE_WAIT_CODES.
    """
    fields = (config.asr_resource_manifest, config.asr_resource_manifest_sha256,
              config.asr_runtime_manifest_sha256, config.asr_route_id)
    if any(value is not None for value in fields):
        raise EngineError('development_asr_unsupported',
                          'Development local-v1 registrations must keep all four ASR fields null', 422)


def _assert_media_tools(start: DevelopmentStart, config, root: Path) -> None:
    """Prevent a system ffmpeg from standing in for the registered resources."""
    if start.ffmpeg is None or start.ffprobe is None:
        raise EngineError('development_installation_denied',
                          'serve-dev requires the registered --ffmpeg and --ffprobe resources', 403)
    expected = (root.joinpath(*config.ffmpeg.split('/')).resolve(),
                root.joinpath(*config.ffprobe.split('/')).resolve())
    if (Path(start.ffmpeg).resolve(), Path(start.ffprobe).resolve()) != expected:
        raise EngineError('development_installation_denied',
                          'serve-dev media tools must be the exact resources this registration names', 403)


def _assert_owner_audit(engine, record) -> None:
    """ADR0079 section 5.3: a development-initialized binding always keeps its audit."""
    principal = record.principal
    if principal.authentication_source != DEVELOPMENT_AUTHENTICATION_SOURCE:
        return
    assert_development_owner_audit(
        engine, action_id=record.action_id, authentication_source=principal.authentication_source,
        instance_id=principal.instance_id, owner_subject=principal.owner_subject,
        project_ids=tuple(principal.project_ids), expires_at_us=principal.expires_at_us)


def _owner_binding(start: DevelopmentStart, *, engine, authority, config, bundle, role,
                   registration_path, registration_sha256):
    """Owner gate: an active binding is read once; only a true first start initializes.

    Any Owner state other than `owner_restore_refresh_required` (no `Control/`
    directory) propagates unchanged. A development-initialized binding is
    re-checked against its retained audit before it authorizes this process.
    """
    from video_creator.application.owner_bootstrap import OwnerBootstrapStore

    store = OwnerBootstrapStore(engine)
    try:
        with store.current(allow_inactive=False) as record:
            _assert_owner_audit(engine, record)
            principal = record.principal
            return (principal.owner_subject, tuple(principal.project_ids), principal.expires_at_us,
                    principal.authentication_source)
    except EngineError as error:
        if not start.auto_owner_init or error.code != 'owner_restore_refresh_required':
            raise
    source = development_owner_initialization_source(
        engine=engine, registration_path=registration_path, registration_sha256=registration_sha256,
        expires_at_us=start.expires_at_us, data_dir=start.data_dir, role=role, bundle=bundle,
        authority=authority, config=config, raw_arguments=start.raw_arguments)
    store.change(action='initialize', action_key=source.action_key,
                 owner_subject=source.owner_subject, project_ids=source.project_ids,
                 expires_at_us=source.expires_at_us, confirmation_source=source)
    with store.current(allow_inactive=False) as record:
        _assert_owner_audit(engine, record)
        principal = record.principal
        return (principal.owner_subject, tuple(principal.project_ids), principal.expires_at_us,
                principal.authentication_source)


def _expiry(start: DevelopmentStart, engine, owner_expires_at_us: int) -> int:
    now = engine.clock()
    limit = min(owner_expires_at_us, now + _MAX_IDENTITY_LIFETIME_US)
    if not now < start.expires_at_us <= limit:
        raise EngineError('development_expiry_invalid',
                          'The development identity must end inside the current Owner binding and the seven day cap', 422)
    return start.expires_at_us


def _factory(start: DevelopmentStart):
    def assemble(*, engine, bundle, role, registered_runtime, for_management):
        from video_creator.application.native_installation import NativeOwnerServices
        from video_creator.application.owner_services import assemble_owner_services

        authority = build = connection = None
        try:
            if getattr(sys, 'frozen', False):
                raise EngineError('development_installation_unavailable',
                                  'A frozen artifact cannot host a development installation', 503)
            _require_environment(engine.instance_id)
            if role not in {'api', 'worker'}:
                raise EngineError('development_role_denied',
                                  'The development host supports only the api and worker roles', 403)
            if for_management is not False:
                raise EngineError('development_installation_denied',
                                  'A development installation is execution-only', 403)
            if bundle.engine is not engine or bundle.principals.owner_subject is None:
                raise EngineError('development_installation_denied',
                                  'The development host requires the actual same-Engine Bundle', 403)
            if role == 'worker':
                config, registration_path, registration_sha256, root = _runtime_registration(start, engine, registered_runtime)
            elif registered_runtime is not None:
                raise EngineError('development_installation_denied',
                                  'The development API role never holds a registered worker runtime', 403)
            else:
                config, registration_path, registration_sha256, root = _read_registration(start)
            _assert_no_asr_capability(config)
            if role == 'api':
                _assert_media_tools(start, config, root)
            engine_facts = engine_source_facts()
            assert_engine_registration(config, engine_facts)
            resource_facts = indexed_resource_facts(root, config)
            assert_distinct_identities(engine_facts, resource_facts)
            context = launch_context(instance_id=engine.instance_id, role=role,
                                     registration_sha256=registration_sha256, config=config,
                                     engine_facts=engine_facts, resource_facts=resource_facts)
            connection = DevelopmentLaunchConnection(context)
            build = DevelopmentLaunchBuild()
            authority = DevelopmentInstallationAuthority(
                engine, config, registration_path=registration_path,
                registration_sha256=registration_sha256, root=root, connection=connection)
            owner, project_ids, owner_expires_at_us, owner_authentication_source = _owner_binding(
                start, engine=engine, authority=authority, config=config, bundle=bundle, role=role,
                registration_path=registration_path, registration_sha256=registration_sha256)
            if owner != bundle.principals.owner_subject:
                raise EngineError('development_installation_denied',
                                  'The active Owner binding differs from the registered Bundle Owner', 403)
            registration = {
                'owner_subject': owner, 'executing_principal_id': owner, 'project_ids': project_ids,
                'registration_sha256': registration_sha256,
                'resource_manifest_sha256': config.production_resource_manifest_sha256,
                'runtime_manifest_sha256': config.production_runtime_manifest_sha256,
                'allowed_source_namespaces': (),
                'expires_at_us': _expiry(start, engine, owner_expires_at_us),
            }
            if (start.auto_owner_init
                    and owner_authentication_source == DEVELOPMENT_AUTHENTICATION_SOURCE):
                # Development bootstrap gap: production installs the retained
                # production authorization floor inside an authenticated
                # management/execution-registration action, which a development
                # instance never runs. The dev host creates only the empty first
                # floor, only for a development-initialized binding, only with
                # the explicit development flag and only while the four
                # authorization tables are provably empty.
                create_development_production_control(engine)
            services = assemble_owner_services(
                engine, owner, bundle=bundle, for_management=False,
                installation_authority=authority, installation_session_guard=authority,
                execution_registration=registration, owner_setup_bootstrap=None)
            # The unattended/policy mode is outside this host's scope; every
            # request entry refuses it before any production policy branch.
            _guard_acceptance(bundle)
            _guard_goal_creation(bundle)
            if role == 'worker':
                _guard_execution(registered_runtime, engine)
            mark_development_host()
            return NativeOwnerServices(services, connection, authority, build)
        except BaseException as failure:
            for owned in (authority, build, connection):
                if owned is None or getattr(owned, '_closed', False):
                    continue
                try:
                    owned.close()
                except BaseException as cleanup:  # noqa: BLE001 -- both retained closes attempted; original failure re-raised
                    failure.add_note('Development host cleanup also failed: ' + type(cleanup).__name__)
            raise
    return assemble


def main(argv: list[str] | None = None) -> int:
    try:
        # ADR0077 section 2 fixes the order as frozen -> dev argv. A frozen
        # artifact is refused even when its development arguments are missing.
        if getattr(sys, 'frozen', False):
            raise EngineError('development_installation_unavailable',
                              'A frozen artifact cannot host a development installation', 503)
        raw_argv = list(sys.argv[1:] if argv is None else argv)
        args = parser().parse_args(raw_argv)
        start = _start(args, _raw_development_arguments(raw_argv))
        if args.command == 'worker-dev':
            # ADR0077 section 2 keeps the environment condition before the
            # registration file and before any Engine/assembly. The existing
            # registered worker branch parses its runtime before the factory, so
            # the wrapper checks the same actual instance identity here; it
            # opens no listener, creates no data dir and does no assembly.
            instance_id = _existing_instance_id(start.data_dir)
            if instance_id is None:
                raise EngineError('development_installation_denied',
                                  'worker-dev requires an existing data directory instance identity', 403)
            _require_environment(instance_id)
        forwarded = _serve_argv(args) if args.command == 'serve-dev' else _worker_argv(args)
        from video_creator.cli.main import main as engine_main

        original = sys.argv
        sys.argv = forwarded
        try:
            return engine_main(installed_service_factory=_factory(start))
        finally:
            sys.argv = original
    except EngineError as error:
        print(json.dumps({'code': error.code, 'message': error.message}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
