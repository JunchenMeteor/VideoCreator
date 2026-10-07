"""CLI diagnostics report identities and status, never credentials."""

import argparse
import importlib
import json
import os
import socket
import sys
import time
from collections.abc import Callable
from pathlib import Path

import uvicorn
from pydantic import ValidationError

from video_creator.api.app import create_app
from video_creator.application.engine import EngineService
from video_creator.domain import contracts
from video_creator.domain.contracts import CapabilityRoute, MediaProbe, Money
from video_creator.domain.errors import EngineError
from video_creator.infrastructure.credentials import CredentialVault


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
    (output_dir / "schemas.json").write_text(json.dumps({"schema_version": contracts.SCHEMA_VERSION, "schemas": schemas}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"schema_version": contracts.SCHEMA_VERSION, "schema_count": len(schemas)}))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="video-creator-engine")
    commands = root.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve")
    serve.add_argument("--data-dir", required=True, type=Path)
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", default=0, type=int)
    serve.add_argument("--allowed-origin", action="append", default=[])
    serve.add_argument("--allowed-host", action="append", default=[])
    serve.add_argument("--ffmpeg", type=Path, help="Trusted launcher absolute FFmpeg resource path")
    serve.add_argument("--ffprobe", type=Path, help="Trusted launcher absolute ffprobe resource path")
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
    worker.add_argument("--driver", required=True)
    worker.add_argument("--once", action="store_true")
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "export-contracts":
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
        elif args.command == "serve":
            token = os.environ.get("VIDEO_CREATOR_API_TOKEN", "")
            engine = EngineService(args.data_dir)
            media_validator = configured_media_validator(engine, args.ffmpeg, args.ffprobe)
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind((args.host, args.port))
            listener.listen(128)
            actual_port = listener.getsockname()[1]

            def ready():
                print(json.dumps({"event": "ready", "base_url": f"http://{args.host}:{actual_port}", "instance_id": engine.instance_id}), flush=True)

            app = create_app(engine, token, allowed_origins=tuple(args.allowed_origin),
                             allowed_hosts=tuple(args.allowed_host or ["127.0.0.1", "localhost"]),
                             media_validator=media_validator, on_ready=ready)

            uvicorn.Server(uvicorn.Config(app, log_level="warning", access_log=False)).run(sockets=[listener])
        return 0
    except (EngineError, ValidationError, OSError, ValueError) as error:
        code = error.code if isinstance(error, EngineError) else "configuration_failed"
        message = error.message if isinstance(error, EngineError) else "Configuration or local operation failed"
        print(json.dumps({"code": code, "message": message}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
