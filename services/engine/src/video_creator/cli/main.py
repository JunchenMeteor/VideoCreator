"""CLI diagnostics report identities and status, never credentials."""

import argparse
import importlib
import json
import os
import socket
import sys
import time
from pathlib import Path

import uvicorn
from pydantic import ValidationError

from video_creator.api.app import create_app
from video_creator.application.engine import EngineService
from video_creator.domain import contracts
from video_creator.domain.contracts import CapabilityRoute, Money
from video_creator.domain.errors import EngineError
from video_creator.infrastructure.credentials import CredentialVault


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
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind((args.host, args.port))
            listener.listen(128)
            actual_port = listener.getsockname()[1]

            def ready():
                print(json.dumps({"event": "ready", "base_url": f"http://{args.host}:{actual_port}", "instance_id": engine.instance_id}), flush=True)

            app = create_app(engine, token, allowed_origins=tuple(args.allowed_origin),
                             allowed_hosts=tuple(args.allowed_host or ["127.0.0.1", "localhost"]), on_ready=ready)

            uvicorn.Server(uvicorn.Config(app, log_level="warning", access_log=False)).run(sockets=[listener])
        return 0
    except (EngineError, ValidationError, OSError, ValueError) as error:
        code = error.code if isinstance(error, EngineError) else "configuration_failed"
        message = error.message if isinstance(error, EngineError) else "Configuration or local operation failed"
        print(json.dumps({"code": code, "message": message}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
