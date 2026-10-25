"""CLI diagnostics report identities and status, never credentials."""

import argparse
import asyncio
import hashlib
import importlib
import json
import os
import socket
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path

import uvicorn
from pydantic import TypeAdapter, ValidationError

from video_creator.api.app import create_app
from video_creator.application.bundles import BundleService
from video_creator.application.engine import EngineService
from video_creator.application.local_evidence import (
    evidence_admin_install,
    install_local_evidence_trust,
    local_evidence_resource_manifest_hashes,
)
from video_creator.application.product_authorization import (
    ProductAuthorizationChannel,
    authorization_session_secret_from_environment,
    owner_binding_absent,
)
from video_creator.application.worker import run_local_worker
from video_creator.cli.lifecycle import ApiLifecycle, confirm_stopped, controlled_serve
from video_creator.cli.startup_services import (
    InstalledServiceFactory,
    confirm_api_cleanup,
    install_startup_services,
    installed_principal_id,
)
from video_creator.domain import (
    contracts,
    daily_project_authorization,
    local_copy_input_scope,
)
from video_creator.domain.bundle import TrustedBundleValidators
from video_creator.domain.contracts import CapabilityRoute, MediaProbe, Money
from video_creator.domain.errors import EngineError
from video_creator.infrastructure.credentials import CredentialVault
from video_creator.infrastructure.origins import native_startup_origins, startup_origins


def configured_media_validator(engine: EngineService, ffmpeg: Path | None,
                               ffprobe: Path | None) -> Callable[[Path, str], MediaProbe] | None:
    """Wire only the fixed media implementation to trusted launcher resources.

    HTTP/model input cannot choose binaries or staging roots. An unavailable
    resource leaves uploads staged and imports explicitly blocked with 503.
    """
    if ffmpeg is None and ffprobe is None:
        return None
    if ffmpeg is None or ffprobe is None:
        raise EngineError("media_runtime_incomplete", "FFmpeg and ffprobe must be configured together", 400)
    if any(not binary.is_absolute() or str(binary).startswith(("\\\\", "//")) for binary in (ffmpeg, ffprobe)):
        raise EngineError("media_runtime_path_denied", "Media tools require absolute local launcher paths", 400)
    try:
        # Lazy fixed import keeps schema export and tool-less local startup usable.
        from video_creator.media.ffmpeg import FFmpegRuntime

        staging = engine.db.data_dir / "Staging"
        staging.mkdir(exist_ok=True)
        if staging.is_symlink() or not staging.resolve().is_relative_to(engine.db.data_dir):
            raise EngineError("path_denied", "Media staging escaped the installation", 403)
        runtime = FFmpegRuntime(ffmpeg, ffprobe, staging)
    except (OSError, EngineError) as error:
        if isinstance(error, EngineError) and error.code == "path_denied":
            raise
        print(json.dumps({"event": "media_unavailable", "code": "media_validator_missing",
                          "message": "Configured media tools are unavailable; media import remains blocked"}), file=sys.stderr)
        return None

    def validate(path: Path, media_type: str) -> MediaProbe:
        try:
            # AssetService checks the actual probe MIME against the staged MIME.
            return runtime.probe(path, decode=True)
        except OSError:
            raise EngineError("media_validator_missing", "Configured media decoder is unavailable", 503) from None

    return validate


def export_contracts(output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    # OpenAPI export must not create a runtime database or install user credentials.
    class ExportEngine:
        instance_id = "schema-export"
        class ExportDatabase:
            data_dir = output_dir
        db = ExportDatabase()
    app = create_app(ExportEngine(), "schema-export-token-" + "x" * 32)
    (output_dir / "openapi.json").write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    schemas = {}
    for name in dir(contracts):
        value = getattr(contracts, name)
        if isinstance(value, type) and issubclass(value, contracts.Contract) and value is not contracts.Contract:
            schemas[name] = value.model_json_schema()
    for name in dir(local_copy_input_scope):
        value = getattr(local_copy_input_scope, name)
        if (isinstance(value, type) and issubclass(value, contracts.Contract)
                and value.__module__ == local_copy_input_scope.__name__):
            schema = value.model_json_schema()
            if name in schemas and schemas[name] != schema:
                raise EngineError('contract_name_conflict', 'Independent copy contract collides with an existing unique schema', 503)
            schemas[name] = schema
    for name in dir(daily_project_authorization):
        value = getattr(daily_project_authorization, name)
        if (isinstance(value, type) and issubclass(value, contracts.Contract)
                and value.__module__ == daily_project_authorization.__name__ and not name.startswith('_')):
            schema = value.model_json_schema()
            if name in schemas and schemas[name] != schema:
                raise EngineError('contract_name_conflict', 'Daily creation contract collides with an existing unique schema', 503)
            schemas[name] = schema
    schemas['ProjectGoalReceiptAssociationV1'] = TypeAdapter(daily_project_authorization.ProjectGoalReceiptAssociationV1).json_schema()
    (output_dir / "schemas.json").write_text(json.dumps({"schema_version": contracts.CONTRACT_SET_VERSION, "supported_request_versions": [contracts.SCHEMA_VERSION, contracts.V03_SCHEMA_VERSION], "local_copy_input_scope_version": local_copy_input_scope.LOCAL_COPY_SCOPE_VERSION, "schemas": schemas}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"schema_version": contracts.CONTRACT_SET_VERSION, "schema_count": len(schemas)}))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="video-creator-engine")
    commands = root.add_subparsers(dest="command", required=True)
    from video_creator.cli.owner import add_owner_parsers
    add_owner_parsers(commands)
    serve = commands.add_parser("serve")
    serve.add_argument("--data-dir", required=True, type=Path)
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", default=0, type=int)
    serve.add_argument("--allowed-origin", action="append", default=[])
    serve.add_argument("--native-origin", help="Trusted native host exact origin; Windows http://tauri.localhost only")
    serve.add_argument("--allowed-host", action="append", default=[])
    serve.add_argument("--ffmpeg", type=Path, help="Trusted launcher absolute FFmpeg resource path")
    serve.add_argument("--ffprobe", type=Path, help="Trusted launcher absolute ffprobe resource path")
    serve.add_argument("--control-stdin", action="store_true", help="Accept fixed private stop frames from a trusted launcher pipe")
    export = commands.add_parser("export-contracts")
    export.add_argument("--output-dir", required=True, type=Path)
    secret = commands.add_parser("credential-import")
    secret.add_argument("--source", required=True, type=Path)
    secret.add_argument("--credential-id", required=True)
    budget = commands.add_parser("authorize-validation")
    budget.add_argument("--data-dir", required=True, type=Path)
    budget.add_argument("--amount", default="20.00")
    budget.add_argument("--subject", default="local-user")
    route = commands.add_parser("register-route")
    route.add_argument("--data-dir", required=True, type=Path)
    route.add_argument("--route-file", required=True, type=Path)
    recover = commands.add_parser("recover")
    recover.add_argument("--data-dir", required=True, type=Path)
    worker = commands.add_parser("worker")
    worker.add_argument("--data-dir", required=True, type=Path)
    worker.add_argument("--workflow", choices=["gate0-local-render-v1", "registered-media-bundle-v1"])
    worker.add_argument("--driver", help="Legacy explicit trusted workflow probe entry")
    worker.add_argument("--resource-manifest", type=Path)
    worker.add_argument("--run-id")
    worker.add_argument("--max-seconds", type=int, default=300)
    worker.add_argument("--once", action="store_true")
    worker.add_argument("--production-config", type=Path, help="Trusted installed complete engine/media registration")
    worker.add_argument("--production-config-sha256", help="Installer-pinned production configuration SHA256")
    worker.add_argument("--control-stdin", action="store_true", help="Opt-in private bounded quiesce pipe; EOF does not cancel tasks")
    evidence = commands.add_parser("evidence-admin",
                                   help="One-shot local self-issued evidence install; never starts a listener")
    evidence_commands = evidence.add_subparsers(dest="evidence_command", required=True)
    evidence_install = evidence_commands.add_parser("install")
    evidence_install.add_argument("--data-dir", required=True, type=Path)
    evidence_install.add_argument("--receipt", required=True, type=Path,
                                  help="The one-shot receipt issued by the approved product authorization")
    mcp = commands.add_parser("mcp-stdio")
    mcp.add_argument("--data-dir", required=True, type=Path)
    mcp.add_argument("--ffmpeg", type=Path)
    mcp.add_argument("--ffprobe", type=Path)
    return root


def main(*, installed_service_factory: InstalledServiceFactory | None = None,
         owner_installation_observer_factory=None) -> int:
    args = parser().parse_args()
    try:
        if installed_service_factory is not None and not (
                args.command in {"serve", "mcp-stdio"}
                or args.command == "worker" and args.workflow == "registered-media-bundle-v1"):
            raise EngineError("installed_services_command_denied", "Private installation assembly is limited to the actual API, MCP and registered Worker", 503)
        if owner_installation_observer_factory is not None and args.command != 'owner-execution':
            raise EngineError('owner_installation_command_denied', 'Private installation observer is limited to actual Owner execution registration actions', 403)
        if args.command in {"owner-init", "owner-policy", "owner-execution", "owner-project-creation"}:
            from video_creator.cli.owner import run_owner_command
            run_owner_command(args, installation_observer_factory=owner_installation_observer_factory)
        elif args.command == "export-contracts":
            export_contracts(args.output_dir)
        elif args.command == "credential-import":
            reference = CredentialVault().import_file(args.source, args.credential_id)
            print(json.dumps({"credential_ref": reference, "stored_in": "os_vault"}))
        elif args.command == "authorize-validation":
            cap = Money(amount=args.amount)
            if cap.units() > 20_000_000:
                raise EngineError("validation_budget_exceeded", "This validation authorization is capped at CNY 20.00", 400)
            engine = EngineService(args.data_dir)
            engine.authorize_budget_group("validation-cny20", cap, args.subject)
            print(json.dumps(engine.budget_status("validation-cny20")))
        elif args.command == "register-route":
            engine = EngineService(args.data_dir)
            route = CapabilityRoute.model_validate_json(args.route_file.read_text(encoding="utf-8"))
            engine.register_route(route)
            print(json.dumps({"registered_route_id": route.route_id}))
        elif args.command == "recover":
            print(json.dumps(EngineService(args.data_dir).recover()))
        elif args.command == "worker":
            from video_creator.cli.worker_lifecycle import (
                WorkerControl,
                confirm_worker_stopped,
                worker_ready,
            )
            original_threads = set(threading.enumerate())
            if args.workflow == "registered-media-bundle-v1":
                if args.driver or args.resource_manifest or not args.production_config or not args.production_config_sha256 or not 1 <= args.max_seconds <= 900:
                    raise EngineError("production_configuration_missing", "Registered producer requires a fixed complete installer configuration and bounded attempt window", 503)
                from video_creator.application.media_registration import (
                    RegisteredMediaRuntime,
                    run_registered_worker,
                )
                engine = EngineService(args.data_dir)
                install_local_evidence_trust(engine)
                # The same signed-qualification helper as `serve`/`mcp`: the
                # registered worker's own BundleService must trust the exact ASR
                # resource manifest of an admitted local self-issued policy, or
                # its speech preparation still refuses the real runtime identity.
                worker_evidence_manifests = local_evidence_resource_manifest_hashes(engine)
                runtime = RegisteredMediaRuntime(engine, args.production_config, args.production_config_sha256,
                                                 resource_manifest_hashes=worker_evidence_manifests)
                if worker_evidence_manifests:
                    # Nonsecret diagnostic: the worker process proves which
                    # admitted ASR resource manifest its BundleService trusts.
                    print(json.dumps({"event": "worker_local_evidence",
                                      "resource_manifest_hashes": sorted(worker_evidence_manifests)}), flush=True)
                installed = install_startup_services(installed_service_factory,
                    engine=engine, bundle=runtime.bundle, role="worker", registered_runtime=runtime)
                with WorkerControl(args.control_stdin) as control:
                    run_registered_worker(runtime, control=control,
                        on_ready=lambda identifier: worker_ready(engine, identifier, runtime.sha256, args.workflow),
                        run_id=args.run_id, once=args.once, max_seconds=args.max_seconds)
                if args.control_stdin:
                    confirm_worker_stopped(control, original_threads)
                if installed is not None:
                    installed.finish_shutdown(original_threads)
            elif args.workflow:
                if args.production_config or args.production_config_sha256:
                    raise EngineError("worker_configuration_invalid", "Production installer configuration cannot alter the legacy fixed experiment", 400)
                if args.driver or not args.resource_manifest or not 1 <= args.max_seconds <= 900:
                    raise EngineError("worker_configuration_invalid", "Fixed local workflow requires a resource manifest and a 1 to 900 second window", 400)
                manifest_path = args.resource_manifest
                if not manifest_path.is_absolute() or str(manifest_path).startswith(("\\\\", "//")):
                    raise EngineError("worker_resource_denied", "Worker resources require a trusted absolute local manifest", 400)
                raw = manifest_path.read_bytes()
                manifest = json.loads(raw)
                runtime_root = Path(manifest["runtime_root"]).resolve(strict=True)
                for entry in manifest["files"]:
                    resource = (runtime_root / entry["relative_path"]).resolve(strict=True)
                    if not resource.is_relative_to(runtime_root) or not resource.is_file():
                        raise EngineError("worker_resource_denied", "Manifest resource escaped its fixed local root", 403)
                    if resource.stat().st_size != entry["bytes"] or hashlib.sha256(resource.read_bytes()).hexdigest() != entry["sha256"]:
                        raise EngineError("worker_resource_integrity_failed", "Manifest resource failed its fixed hash", 503)
                for name in ("ffmpeg_path", "ffprobe_path"):
                    # The named launcher resources must be covered by the verified list.
                    configured = Path(manifest[name]).resolve(strict=True)
                    if not any((runtime_root / entry["relative_path"]).resolve() == configured for entry in manifest["files"]):
                        raise EngineError("worker_resource_integrity_failed", "Media tool is not covered by the verified manifest", 503)
                font = manifest["font"]
                font_path = Path(font["path"])
                if not font_path.is_absolute() or str(font_path).startswith(("\\\\", "//")):
                    raise EngineError("worker_resource_denied", "Font requires a fixed absolute local resource path", 403)
                if font_path.stat().st_size != font["bytes"] or hashlib.sha256(font_path.read_bytes()).hexdigest() != font["sha256"]:
                    raise EngineError("worker_resource_integrity_failed", "Font failed its fixed manifest hash", 503)
                def driver(invocation, services):
                    try:
                        workflow = importlib.import_module("video_creator.workflows.local_render")
                        callback = workflow.run_invocation
                    except (ImportError, AttributeError):
                        raise EngineError("worker_driver_missing", "Fixed local workflow implementation is not installed", 503) from None
                    return callback(invocation, services)

                def reconciliation_driver(invocation, services):
                    try:
                        workflow = importlib.import_module("video_creator.workflows.local_reconciliation")
                        callback = workflow.run_reconciliation
                    except (ImportError, AttributeError):
                        raise EngineError("reconciliation_driver_missing", "Fixed local evidence driver is not installed", 503) from None
                    return callback(invocation, services)
                engine = EngineService(args.data_dir)
                validator = configured_media_validator(engine, Path(manifest["ffmpeg_path"]), Path(manifest["ffprobe_path"]))
                if validator is None:
                    raise EngineError("media_validator_missing", "Worker requires the actual configured decoder", 503)
                resource_sha = hashlib.sha256(raw).hexdigest()
                with WorkerControl(args.control_stdin) as control:
                    run_local_worker(engine, manifest_path, resource_sha, validator, driver,
                                     reconciliation_driver=reconciliation_driver,
                                     run_id=args.run_id, max_seconds=args.max_seconds, once=args.once,
                                     control=control,
                                     on_ready=(lambda identifier: worker_ready(engine, identifier, resource_sha, args.workflow)) if args.control_stdin else None)
                if args.control_stdin:
                    confirm_worker_stopped(control, original_threads)
            else:
                if args.control_stdin or args.production_config or args.production_config_sha256:
                    raise EngineError("worker_configuration_invalid", "Legacy explicit probes do not implement the registered worker lifecycle", 400)
                if not args.driver:
                    raise EngineError("worker_configuration_invalid", "Select the fixed workflow or an explicit legacy probe", 400)
                module_name, _, function_name = args.driver.partition(":")
                if not module_name.startswith("video_creator.workflows.") or not function_name.isidentifier():
                    raise EngineError("worker_driver_denied", "Worker driver must be a configured workflow entry", 400)
                driver = getattr(importlib.import_module(module_name), function_name)
                engine = EngineService(args.data_dir)
                while True:
                    driver(engine)
                    if args.once:
                        break
                    time.sleep(0.25)
        elif args.command == "evidence-admin":
            if args.evidence_command != "install":
                raise EngineError("evidence_admin_command_invalid",
                                  "Only the one-shot evidence-admin install is supported", 400)
            print(json.dumps(evidence_admin_install(data_dir=args.data_dir, receipt=args.receipt),
                             ensure_ascii=False))
        elif args.command == "mcp-stdio":
            from video_creator.integrations.mcp_stdio import run_mcp_stdio
            token = os.environ.get("VIDEO_CREATOR_MCP_TOKEN", "")
            if len(token) < 32:
                raise EngineError("mcp_session_token_missing", "MCP requires a trusted per-session child environment token", 503)
            engine = EngineService(args.data_dir)
            install_local_evidence_trust(engine)
            media = configured_media_validator(engine, args.ffmpeg, args.ffprobe)
            bundle = BundleService(engine, TrustedBundleValidators(
                media_validator=media,
                resource_manifest_hashes=local_evidence_resource_manifest_hashes(engine)))
            original_threads = set(threading.enumerate())
            installed = install_startup_services(installed_service_factory,
                engine=engine, bundle=bundle, role="mcp")
            asyncio.run(run_mcp_stdio(bundle, token))
            if installed is not None:
                installed.finish_shutdown(original_threads)
        elif args.command == "serve":
            origins = (native_startup_origins(args.native_origin, tuple(args.allowed_origin))
                       if args.native_origin else startup_origins(tuple(args.allowed_origin)))
            if args.native_origin and (args.host != "127.0.0.1" or any(host not in {"127.0.0.1", "localhost"} for host in args.allowed_host)):
                raise EngineError("native_host_denied", "Native API binds only the fixed loopback listener and hosts", 400)
            token = os.environ.get("VIDEO_CREATOR_API_TOKEN", "")
            engine = EngineService(args.data_dir)
            install_local_evidence_trust(engine)
            session_secret = authorization_session_secret_from_environment()
            media_validator = None
            bundle = None
            installed = None
            # ADR0081 section 2: without an Owner binding the engine may listen,
            # but only `/health` and `/api/v1/authorization/*` are addressable.
            # The restricted branch below does not assemble Owner services, does
            # not register an execution identity and does not read admissions.
            restricted = (installed_service_factory is None and owner_binding_absent(engine))
            if not restricted:
                media_validator = configured_media_validator(engine, args.ffmpeg, args.ffprobe)
                # The admitted local self-issued qualification binds one exact
                # child-observed ASR resource manifest; publish-time validators
                # must trust that sha or the runtime identity check fails. The
                # helper reads only signed qualification rows, never config.
                bundle = BundleService(engine, TrustedBundleValidators(
                    media_validator=media_validator,
                    resource_manifest_hashes=local_evidence_resource_manifest_hashes(engine)))
                try:
                    installed = install_startup_services(installed_service_factory,
                        engine=engine, bundle=bundle, role="api")
                except EngineError as error:
                    # The development factory proves its own conditions (frozen,
                    # environment, registration, resource identity) before its
                    # Owner gate. Only the exact Owner refusal may fall back to
                    # the consent surface, and only when a launcher injected the
                    # authorization session secret: without that injection the
                    # development host keeps ADR0077/ADR0079's fail-before-bind.
                    if (installed_service_factory is not None
                            and error.code in {'owner_restore_refresh_required', 'owner_not_initialized'}
                            and session_secret is not None):
                        restricted = True
                        media_validator = None
                        bundle = None
                        installed = None
                    else:
                        raise
            channel = None
            if restricted:
                channel = ProductAuthorizationChannel(
                    engine, session_secret=session_secret, owner_subject="local-user",
                    caller_module="video_creator.cli.main", origins=origins,
                    allowed_hosts=tuple(args.allowed_host or ["127.0.0.1", "localhost"]),
                    launcher_origin="serve-dev" if installed_service_factory is not None else "serve",
                    allowed_kinds=('owner_initialize',))
            else:
                # A normally assembled instance offers only the local
                # self-issued evidence range (ADR0082); it never reopens the
                # Owner-initialization surface and never touches evidence rows
                # itself (the one-shot evidence-admin child does that).
                channel = ProductAuthorizationChannel(
                    engine, session_secret=session_secret, owner_subject="local-user",
                    caller_module="video_creator.cli.main", origins=origins,
                    allowed_hosts=tuple(args.allowed_host or ["127.0.0.1", "localhost"]),
                    launcher_origin="serve-dev" if installed_service_factory is not None else "serve",
                    allowed_kinds=('local_evidence_policy',))
            state = ApiLifecycle()
            original_threads = set(threading.enumerate())
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                listener.bind((args.host, args.port))
                listener.listen(128)
                actual_port = listener.getsockname()[1]

                def ready():
                    descriptor = {"event": "ready", "base_url": f"http://{args.host}:{actual_port}", "instance_id": engine.instance_id}
                    if restricted:
                        # No execution principal is claimed while restricted.
                        descriptor["authorization_state"] = channel.authorization_state
                    if installed is not None:
                        descriptor['principal_id'] = installed_principal_id(installed,
                            engine=engine, bundle=bundle, role='api')
                    state.ready = True
                    print(json.dumps(descriptor), flush=True)

                def shutdown_completed():
                    state.lifespan_completed = True

                server = None
                app = create_app(engine, token, allowed_origins=origins,
                                 allowed_hosts=tuple(args.allowed_host or ["127.0.0.1", "localhost"]),
                                 media_validator=media_validator, on_ready=ready,
                                 is_stopping=(lambda: server.should_exit) if args.control_stdin else None,
                                 on_shutdown=shutdown_completed if args.control_stdin or installed is not None else None,
                                 bundle_service=bundle,
                                 copy_input_service=installed.native.services.copy_inputs if installed is not None else None,
                                 authorization_channel=channel,
                                 authorization_state='none',
                                 restricted=restricted)
                server = uvicorn.Server(uvicorn.Config(app, log_level="warning", access_log=False,
                                                     lifespan="on" if args.control_stdin else "auto"))
                if args.control_stdin:
                    asyncio.run(controlled_serve(server, listener, state, sys.stdin.fileno()),
                                loop_factory=server.config.get_loop_factory())
                else:
                    server.run(sockets=[listener])
                    state.serve_completed = True
            if args.control_stdin:
                confirm_stopped(server, listener, state, original_threads)
            if installed is not None:
                confirm_api_cleanup(server, listener, state)
                installed.finish_shutdown(original_threads)
        return 0
    except (EngineError, ValidationError, OSError, ValueError, KeyError, TypeError) as error:
        code = error.code if isinstance(error, EngineError) else "configuration_failed"
        message = error.message if isinstance(error, EngineError) else "Configuration or local operation failed"
        print(json.dumps({"code": code, "message": message}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
