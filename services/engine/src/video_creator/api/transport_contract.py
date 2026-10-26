"""Unique HTTP transport declarations derived from the actual API routes.

This describes the existing guards and byte protocol; it grants no access,
installs no authority and does not declare a native broker ready.
"""

from copy import deepcopy

from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.responses import FileResponse

from video_creator.domain.contracts import CONTRACT_SET_VERSION

TRANSPORT_FORMAT = "engine-http-transport-v1-candidate"
SECURITY_SCHEME = "InstallationBearer"
MANAGEMENT_SCHEME = "ProductionManagementBearer"
MANAGEMENT = frozenset(('local_copy_scope_preview', 'local_copy_scope_install', 'local_copy_scope_select',
                        'local_copy_scope_revoke', 'local_copy_scope_get', 'local_copy_scope_bind'))

# The keys are actual endpoint functions, never a second method/path registry.
# Permission strings are existing BundleService/AccessContext operations.
DELEGATED = {
    'lookup_project_goal_receipt': (("production.read",), "playback"),
    'create_project_goal': (("production.create",), "derivative"),
    "production_create": (("production.create",), "derivative"),
    "production_get": (("production.read",), "playback"),
    "decision_submit": (("production.review", "production.read"), "derivative_and_playback"),
    "bundle_get": (("bundle.read",), "purpose_query"),
    "bundle_content": (("bundle.content",), "purpose_query"),
    "bundle_semantic": (("bundle.semantic", "bundle.content"), "rag_index"),
    "bundle_export": (("bundle.export",), "request_purpose"),
    "bundle_export_status": (("bundle.export",), "original_export_purpose"),
    "bundle_export_content": (("bundle.export",), "original_export_purpose"),
    "bundle_grant": (("bundle.grant",), "redistribution"),
    "bundle_revoke": (("bundle.revoke",), "redistribution"),
    "bundle_import": (("bundle.import",), "export"),
    "bundle_import_get": (("bundle.read",), "playback"),
    "bundle_import_manifest": (("bundle.read",), "purpose_query"),
    "bundle_import_content": (("bundle.content",), "purpose_query"),
    "bundle_import_export": (("bundle.export",), "request_purpose"),
}
OWNER_ONLY = frozenset(("health", "projects", "project_create", "project_get", "project_update",
    "production_list", "production_cancel", "production_revisions", "run_pause", "run_resume",
    "run_events", "asset_list", "asset_stage", "asset_import", "asset_get", "asset_content",
    "budget_summary", "production_preview", "production_publish"))
FILE_ENDPOINTS = frozenset(("asset_content", "bundle_get", "bundle_content", "bundle_export_content",
    "bundle_import_manifest", "bundle_import_content"))
MANIFEST_ENDPOINTS = frozenset(("bundle_get", "bundle_import_manifest"))
STRING = {"type": "string"}
BINARY = {"type": "string", "format": "binary"}


def content_metadata_for(content_endpoint):
    """Bind an actual metadata endpoint to its actual content function."""
    def decorate(metadata_endpoint):
        metadata_endpoint.__delivery_content_endpoint__ = content_endpoint
        return metadata_endpoint
    return decorate


def _delivery_relations(app, schema):
    routes = {route.endpoint: route for route in app.routes if isinstance(route, APIRoute) and route.include_in_schema}
    relations = {}
    for endpoint, metadata_route in routes.items():
        content_endpoint = getattr(endpoint, "__delivery_content_endpoint__", None)
        if content_endpoint is None:
            continue
        content_route = routes.get(content_endpoint)
        if (content_route is None or content_endpoint.__name__ not in FILE_ENDPOINTS
                or metadata_route.methods != {"GET"} or content_route.methods != {"GET"}
                or content_endpoint in relations):
            raise ValueError("Metadata must bind exactly one real GET content endpoint")
        content = schema["paths"][content_route.path]["get"]
        metadata = schema["paths"][metadata_route.path]["get"]
        target = metadata["responses"]["200"]["content"]["application/json"]["schema"]
        if set(target) != {"$ref"} or target["$ref"].rsplit("/", 1)[-1] != "DeliveryContentMetadata":
            raise ValueError("Metadata requires its unique single published response schema")
        bindings = {}
        for kind in ("path", "query"):
            original = {value["name"]: value for value in content.get("parameters", []) if value.get("in") == kind}
            selected = {value["name"]: value for value in metadata.get("parameters", []) if value.get("in") == kind}
            if (set(original) != set(selected) or kind == "query" and set(original) - {"purpose"}
                    or any(original[key].get("schema") != selected[key].get("schema") for key in original)):
                raise ValueError("Metadata parameter bindings must be the exact closed same-name content parameters")
            bindings[kind] = {key: key for key in selected}
        rule = ("installation_owner" if content_endpoint.__name__ == "asset_content" else
                "original_export_journal" if content_endpoint.__name__ == "bundle_export_content" else "same_content_request")
        relations[content_endpoint] = (metadata_route, {
            "format": "authorized-content-relation-v1-candidate",
            "metadata_operation_id": metadata["operationId"], "metadata_schema_ref": target["$ref"],
            "path_bindings": bindings["path"], "query_bindings": bindings["query"], "purpose_rule": rule,
            "response_binding": {"kind": "single_delivery_content_metadata", "schema_kind": "delivery_content_metadata",
                "schema_version": "0.1.0-candidate"},
            "content_integrity": {"digest_header": "ETag", "digest_encoding": "quoted_sha256",
                "complete_size_header": "Content-Length", "complete_status": 200, "partial_status": 206,
                "partial_total_header": "Content-Range"}})
    if {endpoint.__name__ for endpoint in relations} != FILE_ENDPOINTS:
        raise ValueError("Every admitted content endpoint needs exactly one metadata relation")
    return relations


def _header(name, description, *, native_pattern=None):
    value = {"name": name, "in": "header", "required": False, "schema": dict(STRING), "description": description}
    if native_pattern:
        value["x-native-value-pattern"] = native_pattern
    return value


def _response_headers(*names):
    descriptions = {
        "Content-Type": "Actual response MIME, including charset/boundary when supplied.",
        "Content-Length": "Actual HTTP body byte length when present; a partial length is not the full artifact size.",
        "ETag": "Quoted SHA256 for content; quoted numeric revision for project drafts.",
        "Last-Modified": "FileResponse stat timestamp; not a creative revision or integrity proof.",
        "Cache-Control": "Actual route cache directive.",
        "Accept-Ranges": "bytes for FileResponse content.",
        "Content-Range": "Single206 bytes start-end/size;416 bytes */size. Multipart206 carries its ranges within the body.",
    }
    return {name: {"schema": dict(STRING), "description": descriptions[name]} for name in names}


def _file_contract(operation, name):
    conditional = name != "asset_content"
    parameters = operation.setdefault("parameters", [])
    parameters.extend((
        _header("Range", "Starlette byte ranges; malformed400, unsatisfiable416, a supported range206. Too many ranges fall back to200.",
            native_pattern=r"^bytes=(?:[0-9]+-[0-9]*|-[0-9]+)$"),
        _header("If-Range", "Range applies only when exactly equal to the current ETag or Last-Modified; otherwise full200."),
    ))
    if conditional:
        parameters.append(_header("If-None-Match", "Only exact equality to the current quoted SHA256 ETag returns304, after authorization and integrity checks."))
    media = "application/zip" if name == "bundle_export_content" else "application/json" if name in MANIFEST_ENDPOINTS else "*/*"
    responses = operation["responses"]
    common = _response_headers("Content-Type", "Content-Length", "ETag", "Last-Modified", "Cache-Control", "Accept-Ranges")
    current = responses.setdefault("200", {"description": "Authorized complete original bytes"})
    if name not in MANIFEST_ENDPOINTS:
        current["content"] = {media: {"schema": dict(BINARY)}}
    current["headers"] = deepcopy(common)
    responses["206"] = {"description": "Authorized actual partial bytes; never evidence of complete file integrity.",
        "headers": {**deepcopy(common), **_response_headers("Content-Range")},
        "content": {media: {"schema": dict(BINARY)}, "multipart/byteranges": {"schema": dict(BINARY)}}}
    responses["416"] = {"description": "Unsatisfiable byte range; Starlette empty plain-text transport response.",
        "headers": _response_headers("Content-Type", "Content-Length", "Content-Range"),
        "content": {"text/plain": {"schema": dict(STRING)}}}
    if conditional:
        responses["304"] = {"description": "Authorized exact ETag match; empty body, not a full-file verification.",
            "headers": _response_headers("ETag", "Cache-Control")}
    return {"kind": "original_file_bytes", "media_type_source": "actual_content_handle",
        "conditional_not_modified": conditional, "conditional_equality": "exact_quoted_sha256" if conditional else None,
        "range": {"unit": "bytes", "single": True, "suffix": True, "open_end": True,
            "multiple": "Starlette multipart/byteranges; native admission is single-range only",
            "maximum_ranges": FileResponse.max_ranges, "excess_ranges": "200_full_body", "if_range": "exact_etag_or_last_modified"},
        "status_body_kinds": {"200": "bytes", "206": "partial_bytes", "304": "none" if conditional else "not_implemented",
            "416": "empty_plain_text"},
        "head_supported": False, "head_rejection": "FastAPI route405; FileResponse internals do not register a HEAD operation",
        "authorization_before_conditional_range": True,
        "full_size_limit": None,
        "size_limit_semantics": "Existing asset/journal/service checks apply; this declaration adds no download cap"}


def install_transport_contract(app: FastAPI, *, allowed_hosts: tuple[str, ...], allowed_origins: tuple[str, ...], upload_max_bytes: int):
    """Attach declarations only. Existing Header/auth/stream handlers are unchanged."""
    original = app.openapi

    def openapi():
        baseline = original()
        if "x-engine-transport" in baseline:
            return baseline
        # A failed declaration must not leave a partially admitted cached schema.
        schema = deepcopy(baseline)
        schema.setdefault("components", {}).setdefault("securitySchemes", {})[SECURITY_SCHEME] = {
            "type": "http", "scheme": "bearer", "description": "Opaque installation session or configured principal credential, not OAuth/JWT. Runtime requires the exact Bearer prefix; secrets remain in the trusted caller."}
        schema["security"] = [{SECURITY_SCHEME: []}]
        schema['components']['securitySchemes'][MANAGEMENT_SCHEME] = {
            'type': 'http', 'scheme': 'bearer', 'description':
                'Distinct actual Owner management credential issued by the installed ProductionManagementRegistry; ordinary installation token is rejected. No OAuth or task JSON registration.'}
        schema["info"]["x-contract-set-version"] = CONTRACT_SET_VERSION
        schema["x-engine-transport"] = {
            "format": TRANSPORT_FORMAT, "contract_set_version": CONTRACT_SET_VERSION,
            "api_info_version": schema["info"]["version"], "native_ready": False,
            "service_client": {"origin_absent": "accepted_when_host_and_bearer_valid",
                "origin_present": "exact_trusted_startup_origin_required", "configured_hosts": list(allowed_hosts),
                "configured_origins": list(allowed_origins), "host_port": "TrustedHost validates hostname; trusted broker binds the verified ready port"},
            "native_constraints": {"target": "verified_instance_loopback", "arbitrary_url_method_path": False,
                "redirects": "reject", "environment_proxy": "disabled", "request_headers": "operation-declared non-secret headers only",
                "forbidden_renderer_headers": ["Authorization", "Host", "Origin", "Cookie", "Proxy-Authorization", "Sec-Fetch-Site"],
                "reject_header_control_characters": True, "path_parameters": "encode once as one logical segment; never a filesystem path",
                "response_bytes": "original uncompressed bytes; no transparent transformation", "native_ipc_format": "native-ipc-v1-candidate"},
        }
        relations = _delivery_relations(app, schema)
        declared = 0
        for route in app.routes:
            if not isinstance(route, APIRoute) or not route.include_in_schema:
                continue
            name = route.endpoint.__name__
            content_endpoint = getattr(route.endpoint, "__delivery_content_endpoint__", None)
            authorization_name = content_endpoint.__name__ if content_endpoint else name
            if authorization_name not in OWNER_ONLY and authorization_name not in DELEGATED and authorization_name not in MANAGEMENT:
                raise ValueError("HTTP operation is missing its unique transport authorization declaration")
            for method in route.methods:
                operation = schema["paths"][route.path][method.lower()]
                operation["security"] = [{MANAGEMENT_SCHEME if name in MANAGEMENT else SECURITY_SCHEME: []}]
                parameters = operation.setdefault("parameters", [])
                parameters[:] = [value for value in parameters if not (value.get("in") == "header" and value["name"].lower() == "authorization")]
                permission, purpose = DELEGATED.get(authorization_name, ((), None))
                if purpose == "derivative_and_playback":
                    purpose_scope = {"source": "fixed", "values": ["derivative", "playback"]}
                elif purpose in {"purpose_query", "request_purpose", "original_export_purpose"}:
                    purpose_scope = {"source": purpose, "values": None}
                else:
                    purpose_scope = {"source": "fixed", "values": [purpose] if purpose else []}
                metadata = {"format": TRANSPORT_FORMAT, "authorization": {
                    "mode": "installation_owner_only" if authorization_name in OWNER_ONLY else "current_principal_registration",
                    "domain_operations": list(permission), "purposes": purpose_scope,
                    "resource_scope": "actual subject/project ownership, current registration/grant/rights checks; IDs are not authorization tickets"},
                    "body": {"kind": "json_bytes" if "requestBody" in operation else "none", "maximum_bytes": None,
                        "limit_semantics": "Published field constraints; no separate JSON HTTP byte cap is implemented"},
                    "response": {"kind": "json", "head_supported": False},
                    "mutating": method not in {"GET", "HEAD"}, "automatic_http_retry": False}
                if name == 'lookup_project_goal_receipt':
                    metadata['mutating'] = False
                    metadata['body']['limit_semantics'] = 'Original parsed canonical Goal limit 32MiB-16KiB; typed query32MiB. No separate raw HTTP byte cap.'
                    operation['responses']['200']['headers'] = _response_headers('Cache-Control')
                if name in {"bundle_grant", "bundle_revoke"}:
                    metadata["authorization"]["owning_principal_required"] = True
                if name in MANAGEMENT:
                    metadata['authorization'] = {'mode': 'actual_owner_management',
                        'domain_operations': ['production.authorization.manage'],
                        'purposes': {'source': 'fixed', 'values': []},
                        'resource_scope': 'actual local Owner/admin capability, exact project/registry/current source and immutable command; ordinary installation/Portal/MCP execution credentials cannot manage',
                        'owning_principal_required': True, 'installation_session_accepted': False}
                    metadata['native_admission'] = 'requires a separate actual management credential transport; no renderer-supplied credential or generic installation token'
                if name in {"bundle_export", "bundle_import_export"}:
                    metadata["authorization"]["continuation_checks"] = {
                        "phase": "asynchronous_export_builder", "domain_operations": ["bundle.content"],
                        "purpose": "original_export_purpose", "scope": "each selected artifact and license dependency"}
                if name in {"project_get", "project_update"}:
                    operation["responses"]["200"]["headers"] = _response_headers("ETag")
                if name == "project_update":
                    next(value for value in parameters if value.get("name") == "If-Match")["description"] = "Draft numeric revision parsed as int after trimming quote characters; mismatch409."
                if name == "asset_stage":
                    parameters.append(_header("Content-Type", "Actual staging MIME before the first semicolon; defaults application/octet-stream. Staging is not decoder or rights approval."))
                    operation["requestBody"] = {"required": True, "content": {"*/*": {"schema": {**BINARY, "minLength": 1, "maxLength": upload_max_bytes}}}}
                    metadata["body"] = {"kind": "raw_bytes", "minimum_bytes": 1, "maximum_bytes": upload_max_bytes,
                        "limit_semantics": "Actual AssetService.max_bytes; empty or oversized413", "media_type": "request Content-Type; no multipart envelope",
                        "buffering": "Request.stream is consumed into a bounded bytearray; not a constant-memory disk upload"}
                if name == "run_events":
                    parameters.extend((_header("Accept", "Response is SSE when this value contains text/event-stream; otherwise a JSON event list."),
                        _header("Last-Event-ID", "Integer resume cursor; effective cursor=max(after_sequence,int(header)). Malformed400; a larger cursor yields no earlier events.", native_pattern=r"^[0-9]+$")))
                    operation["responses"]["200"]["content"]["text/event-stream"] = {"schema": dict(STRING)}
                    operation["responses"]["200"]["headers"] = _response_headers("Content-Type", "Cache-Control")
                    metadata["response"] = {"kind": "json_or_sse", "sse": {
                        "selection": "Accept contains text/event-stream", "frame": "id: sequence\\nevent: event_type\\ndata: EventEnvelope JSON\\n\\n",
                        "cursor": "persisted monotonically increasing sequence; not necessarily contiguous within a Run",
                        "effective_cursor": "max(after_sequence, int(Last-Event-ID))", "selection_after_cursor": "strictly_greater",
                        "batch_limit": 100, "heartbeat": ": heartbeat\\n\\n", "idle_heartbeat_seconds": 1,
                        "retention_gap_error": "not implemented; future cursor yields empty events", "end": "disconnect or actual API stop",
                        "connection_abort_cancels_production": False}}
                if name in FILE_ENDPOINTS:
                    metadata["response"] = _file_contract(operation, name)
                    metadata["delivery_metadata"] = deepcopy(relations[route.endpoint][1])
                elif content_endpoint:
                    metadata["response"] = {"kind": "json", "head_supported": False,
                        "schema_kind": "delivery_content_metadata", "schema_version": "0.1.0-candidate",
                        "authorization_snapshot_not_capability": True}
                    metadata["metadata_input"] = {"body": "none", "range_or_conditional": "rejected",
                        "query": "exact_operation_declared_parameters_only"}
                for response in operation["responses"].values():
                    response.setdefault("headers", {}).setdefault("Content-Type", _response_headers("Content-Type")["Content-Type"])
                # The broker derives method/path/params/body from this same
                # operation; this extension supplies only otherwise absent semantics.
                metadata["request_headers"] = [value["name"] for value in parameters if value.get("in") == "header"]
                if "requestBody" in operation and "Content-Type" not in metadata["request_headers"]:
                    metadata["request_headers"].append("Content-Type")
                metadata["response_headers"] = sorted({header for value in operation["responses"].values() for header in value.get("headers", {})})
                operation["x-engine-transport"] = metadata
                declared += 1
        schema["x-engine-transport"]["operation_count"] = declared
        app.openapi_schema = schema
        return schema

    app.openapi = openapi
