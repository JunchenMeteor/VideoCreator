"""Real B9 signed-port adapters, lazy product import only after future admission.

V03 models/registry/allocation overloads and actual MCP hosting remain unbound.
This module does not define or instantiate a public DTO or mutate business SQL.
"""
from __future__ import annotations

import asyncio
import hashlib
import importlib
import importlib.machinery
import json
import sys
import types
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from t16_guard import NotReadyForExecution, admit_runtime


class ServiceAdapter:
    def __init__(self, admission_path, admission_sha256, binding_path, binding_sha256,
                 service_bootstrap, journal):
        self.admission, binding = admit_runtime(
            admission_path, admission_sha256, binding_path, binding_sha256)
        if type(service_bootstrap) is not types.FunctionType:
            raise NotReadyForExecution("requires approved post-preflight bootstrap function")
        factory_source = str(Path(service_bootstrap.__code__.co_filename).resolve())
        if (factory_source != binding["service_bootstrap_source"]
                or service_bootstrap.__qualname__ != binding["service_bootstrap_qualname"]
                or factory_source not in binding["required_sources"]):
            raise NotReadyForExecution("bootstrap outside frozen source/body closure")
        if any(name == "video_creator" or name.startswith("video_creator.") for name in sys.modules):
            raise NotReadyForExecution("producer already imported before first bootstrap")
        search = [binding["source_root"]]
        for item in binding["module_chain"]:
            spec = importlib.machinery.PathFinder.find_spec(item["module"], search)
            if (spec is None or type(spec.loader) is not importlib.machinery.SourceFileLoader
                    or spec.origin is None or str(Path(spec.origin).resolve()) != item["path"]):
                raise NotReadyForExecution("loader would resolve an unpinned target/package")
            search = list(spec.submodule_search_locations or [])
        sys.path.insert(0, binding["source_root"])
        # Required source/resource/body/target checks all precede first import.
        module = importlib.import_module("video_creator.application.bundles")
        service = service_bootstrap(module, self.admission)
        if type(service) is not module.BundleService:
            raise NotReadyForExecution("requires actual handed-off BundleService")
        self.service = service
        self.journal = journal

    def _call(self, method, *args, **kwargs):
        # Arguments may contain confidential actor/credentials; record no bodies.
        call = self.journal.record("service_call_enter", {"method": method})
        try:
            result = getattr(self.service, method)(*args, **kwargs)
        except BaseException as error:
            self.journal.record("service_call_raised",
                                {"method": method, "exception_type": type(error).__name__,
                                 "enter_event": call.name})
            raise
        self.journal.record("service_call_returned",
                            {"method": method, "return_type": type(result).__name__,
                             "enter_event": call.name})
        return result

    def context(self, lease):
        return self._call("context", lease)

    def prepare(self, lease, intent):
        return self._call("prepare", lease, intent)

    def stage_material(self, lease, preparation_id, artifact_id, data):
        return self._call("stage_material", lease, preparation_id, artifact_id, data)

    def read_material(self, lease, preparation_id, material_id):
        return self._call("read_material", lease, preparation_id, material_id)

    def verify(self, lease, preparation_id, manifest):
        return self._call("verify", lease, preparation_id, manifest)

    def publish(self, lease, verified):
        return self._call("publish", lease, verified)

    def recover_preparation(self, lease, preparation_id):
        return self._call("recover_preparation", lease, preparation_id)

    def request_export(self, actor, revision_id, key, request):
        return self._call("request_export", actor, revision_id, key, request)

    def export_status(self, actor, export_id):
        return self._call("export_status", actor, export_id)

    def import_bundle(self, actor, key, request):
        return self._call("import_bundle", actor, key, request)

    def import_status(self, actor, import_id):
        return self._call("import_status", actor, import_id)

    def content(self, actor, revision_id, artifact_id, purpose="playback"):
        return self._call("content", actor, revision_id, artifact_id, purpose)

    def semantic_page(self, actor, revision_id, cursor=None, limit=50):
        return self._call("semantic_page", actor, revision_id, cursor, limit)

    def pending_v03(self):
        raise NotReadyForExecution(
            "V03 DTO/registry/material_allocation/verify_alignment_evidence final ABI not published")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise NotReadyForExecution("redirect outside declared local transport is refused")


class HttpAdapter:
    def __init__(self, admission_path, admission_sha256, binding_path, binding_sha256, token, journal):
        self.admission, _ = admit_runtime(
            admission_path, admission_sha256, binding_path, binding_sha256)
        self.origin = self.admission["own_http_origin"]
        parsed = urllib.parse.urlsplit(self.origin)
        if (parsed.scheme != "http" or parsed.hostname != "127.0.0.1"
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or parsed.path not in ("", "/") or not parsed.port):
            raise NotReadyForExecution("only separately admitted own loopback origin")
        self.token = token  # Actual credential minted in own registered test instance.
        self.journal = journal
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), _NoRedirect())

    def request(self, method, relative_path, *, body=None, headers=None, max_bytes=4_194_304):
        if (not relative_path.startswith("/api/v1/") or relative_path.startswith("//")
                or "\\" in relative_path or "#" in relative_path):
            raise NotReadyForExecution("path not declared API relative path")
        extra = dict(headers or {})
        if any(key.lower() in {"authorization", "host", "proxy-authorization"} for key in extra):
            raise NotReadyForExecution("cannot replace trusted credential or destination")
        payload = None if body is None else json.dumps(
            body, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
        request = urllib.request.Request(self.origin.rstrip("/") + relative_path,
            data=payload, method=method, headers=extra | {
                "Authorization": f"Bearer {self.token}", "Content-Type": "application/json"})
        self.journal.record("http_request_enter",
                            {"method": method, "path": relative_path,
                             "body_sha256": None if payload is None else hashlib.sha256(payload).hexdigest()})
        try:
            response = self.opener.open(request, timeout=10)
        except urllib.error.HTTPError as error:
            response = error  # Preserve actual domain/framework HTTP result, no fake JSON envelope.
        with response:
            raw = response.read(max_bytes + 1)
            if len(raw) > max_bytes:
                raise NotReadyForExecution("bounded response exceeded test capture limit")
            captured = {"status": response.status, "content_type": response.headers.get("Content-Type"),
                        "etag": response.headers.get("ETag"), "bytes": raw}
        self.journal.record("http_request_returned",
                            {"method": method, "path": relative_path,
                             "status": captured["status"], "size": len(raw),
                             "response_sha256": hashlib.sha256(raw).hexdigest()})
        return captured


async def real_mcp_session(admission_path, admission_sha256, binding_path, binding_sha256,
                           tool_name, arguments):
    """Candidate real SDK client IPC; no server host argv exists in current B9."""
    admission, _ = admit_runtime(
        admission_path, admission_sha256, binding_path, binding_sha256)
    binding = admission.get("actual_mcp_stdio_host")
    if not binding or binding["final_host_published"] is not True:
        raise NotReadyForExecution("SDK handler factory is not a live MCP host")
    # Host binary/argv must be explicitly supplied by the future stable handoff.
    executable = Path(binding["executable"]).resolve(strict=True)
    if str(executable) not in admission["runtime_resources"]:
        raise NotReadyForExecution("MCP executable outside declared actual runtime")
    for source in binding["host_source_paths"]:
        if source not in admission["production_and_test_sources"]:
            raise NotReadyForExecution("MCP host source not pinned/archived")
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    parameters = StdioServerParameters(command=str(executable),
                                      args=binding["argv"], env=binding["own_safe_environment"])
    async with asyncio.timeout(30):
        async with stdio_client(parameters) as (reader, writer):
            async with ClientSession(reader, writer) as client:
                await client.initialize()
                tools = await client.list_tools()
                if tool_name not in {item.name for item in tools.tools}:
                    raise NotReadyForExecution("actual server did not register requested tool")
                return await client.call_tool(tool_name, arguments)
