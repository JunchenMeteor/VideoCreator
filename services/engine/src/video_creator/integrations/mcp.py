"""MCP1 transport adapter; authority and all business behavior stay in services.

The hosting process must provide a trusted per-session AccessContext resolver.
No tool accepts a credential, owner, filesystem path, or permission declaration.
"""

import json
from collections.abc import Callable
from contextlib import asynccontextmanager

from mcp import types
from mcp.server.lowlevel import Server
from pydantic import BaseModel, TypeAdapter, ValidationError
from video_creator.application.bundles import BundleService
from video_creator.application.engine import identity
from video_creator.domain import contracts as c
from video_creator.domain.bundle import AccessContext
from video_creator.domain.daily_project_authorization import (
    ProjectGoalAccepted,
    ProjectGoalReceiptQueryV1,
    ProjectGoalReceiptAssociationV1,
    ProjectGoalInput,
)
from video_creator.domain.errors import EngineError


def _schema(fields):
    properties, definitions, required = {}, {}, []
    for name, value in fields.items():
        if not isinstance(value, dict):
            schema = TypeAdapter(value).json_schema()
            definitions.update(schema.pop("$defs", {}))
            properties[name] = schema
        else:
            properties[name] = value
        required.append(name)
    result = {"type": "object", "properties": properties, "required": required, "additionalProperties": False}
    if definitions:
        result["$defs"] = definitions
    return result


def create_mcp_server(service: BundleService, context_provider: Callable[[], AccessContext] | None = None,
                      *, on_ready: Callable[[], None] | None = None,
                      on_shutdown: Callable[[], None] | None = None) -> Server:
    identifier = {"type": "string", "minLength": 1, "maxLength": 128}
    definitions = {
        "lookup_project_goal_receipt": ({"query": ProjectGoalReceiptQueryV1}, ProjectGoalReceiptAssociationV1),
        "create_project_goal": ({"idempotency_key": identifier, "goal": ProjectGoalInput}, ProjectGoalAccepted),
        "production_create": ({"idempotency_key": identifier, "request": c.ProductionRequestAny}, c.ProductionAccepted),
        "production_get": ({"production_id": identifier}, c.ProductionDetail),
        "production_decide": ({"run_id": identifier, "idempotency_key": identifier, "decision": c.ReviewDecision}, c.ReviewDecision | c.FeedbackRevision),
        "bundle_get": ({"revision_id": identifier}, c.BundleManifestAny),
        "bundle_semantic_list": ({"revision_id": identifier, "cursor": {"type": ["string", "null"]}, "limit": {"type": "integer", "minimum": 1, "maximum": 100}}, c.SemanticPage),
        "bundle_export": ({"revision_id": identifier, "idempotency_key": identifier, "request": c.BundleExportRequest}, c.BundleExportAccepted),
        "bundle_export_get": ({"export_id": identifier}, c.BundleExportAccepted),
        "bundle_reference_grant": ({"revision_id": identifier, "idempotency_key": identifier, "request": c.BundleGrantRequest}, c.BundleReferenceGrant),
        "bundle_reference_revoke": ({"grant_id": identifier}, c.BundleReferenceGrant),
        "bundle_import": ({"idempotency_key": identifier, "request": c.BundleImportRequest}, c.BundleImportReceiptAny),
        "bundle_import_get": ({"import_id": identifier}, c.BundleImportReceiptAny),
        "bundle_import_export": ({"import_id": identifier, "idempotency_key": identifier, "request": c.BundleExportRequest}, c.BundleExportAccepted),
    }

    @asynccontextmanager
    async def lifespan(server):
        service.start_exports()
        try:
            if on_ready:
                on_ready()
            yield {}
        finally:
            service.stop_exports()
            if on_shutdown:
                on_shutdown()

    server = Server("VideoCreator", version=c.CONTRACT_SET_VERSION, lifespan=lifespan)

    @server.list_tools()
    async def list_tools():
        return [types.Tool(name=name, description="Installation-authorized VideoCreator service operation; identifiers confer no access.",
                           inputSchema=_schema(fields), outputSchema={"type": "object", **TypeAdapter(result).json_schema()},
                           annotations=types.ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True)
                           if name == 'lookup_project_goal_receipt' else None) for name, (fields, result) in definitions.items()]

    # SDK input validation can echo raw values. Validate inside the sanitized
    # boundary instead, while publishing the same unique Pydantic schemas.
    @server.call_tool(validate_input=False)
    async def call_tool(name, arguments):
        try:
            if context_provider is None:
                raise EngineError("mcp_principal_unconfigured", "MCP session has no trusted installation principal", 503)
            actor = context_provider()
            if not isinstance(actor, AccessContext):
                raise EngineError("mcp_principal_unconfigured", "MCP session principal is not configured", 503)
            if name not in definitions or not isinstance(arguments, dict) or set(arguments) != set(definitions[name][0]):
                raise EngineError("invalid_request", "Tool arguments do not satisfy the published contract", 422)
            values = dict(arguments)
            for key, field in definitions[name][0].items():
                if not isinstance(field, dict):
                    values[key] = TypeAdapter(field).validate_python(values[key])
                elif field.get("type") == "string" and (not isinstance(values[key], str) or not 1 <= len(values[key]) <= 128):
                    raise EngineError("invalid_request", "Tool identity is outside its bounded contract", 422)
            if name == 'lookup_project_goal_receipt':
                result = service.lookup_project_goal_receipt(actor, values['query'])
            elif name == 'create_project_goal':
                result = service.create_project_goal(actor, values['idempotency_key'], values['goal'], entry='mcp')
            elif name == "production_create":
                result = service.create_production(actor, values["idempotency_key"], values["request"])
            elif name == "production_get":
                result = service.production(actor, values["production_id"])
            elif name == "production_decide":
                result = service.decision(actor, values["run_id"], values["idempotency_key"], values["decision"])
            elif name == "bundle_get":
                result = service.get_manifest(actor, values["revision_id"])
            elif name == "bundle_semantic_list":
                if type(values["limit"]) is not int or (values["cursor"] is not None and not isinstance(values["cursor"], str)):
                    raise EngineError("invalid_request", "Semantic cursor and limit do not satisfy the contract", 422)
                result = service.semantic_page(actor, values["revision_id"], values["cursor"], values["limit"])
            elif name == "bundle_export":
                result = service.request_export(actor, values["revision_id"], values["idempotency_key"], values["request"])
            elif name == "bundle_export_get":
                result = service.export_status(actor, values["export_id"])
            elif name == "bundle_reference_grant":
                result = service.create_grant(actor, values["revision_id"], values["idempotency_key"], values["request"])
            elif name == "bundle_reference_revoke":
                result = service.revoke_grant(actor, values["grant_id"])
            elif name == "bundle_import":
                result = service.import_bundle(actor, values["idempotency_key"], values["request"])
            elif name == "bundle_import_get":
                result = service.import_status(actor, values["import_id"])
            else:
                result = service.request_import_export(actor, values["import_id"], values["idempotency_key"], values["request"])
            body = result.model_dump(mode="json") if isinstance(result, BaseModel) else result
            return types.CallToolResult(content=[types.TextContent(type="text", text=json.dumps(body, ensure_ascii=False))], structuredContent=body, isError=False)
        except EngineError as error:
            envelope = c.ErrorEnvelope(code=error.code, message=error.message, retryability=error.retryability, request_id=identity("request"))
        except (ValueError, ValidationError):
            envelope = c.ErrorEnvelope(code="invalid_request", message="Tool arguments do not satisfy the published contract", retryability="never", request_id=identity("request"))
        except Exception:  # noqa: BLE001 - prevent the SDK from reflecting private exception text
            envelope = c.ErrorEnvelope(code="mcp_service_unavailable", message="Required installation operation is unavailable", retryability="reconcile", request_id=identity("request"))
        body = envelope.model_dump(mode="json")
        return types.CallToolResult(content=[types.TextContent(type="text", text=json.dumps(body, ensure_ascii=False))], structuredContent=body, isError=True)

    return server
