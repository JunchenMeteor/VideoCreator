"""Independent real TCP upload/import/content and generated-contract checks; self-created signals."""

import json
import os
import struct
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import test_b3_public_media_gate0 as original_media
import test_t5_real_media_formats as formats
from t6_cli_helpers import ROOT, Child, sha, write_receipt
from video_creator.application.engine import EngineService

tools = original_media.tools
samples = formats.samples


@pytest.mark.parametrize("kind", ["apng", "network-url", "outside-url", "outside-urn"])
def test_real_tcp_unsupported_media_is_415_unique_envelope_before_decoder(tmp_path, tools, samples, kind):
    movie = samples["video"].read_bytes()
    outside = tmp_path / "OwnedOutsideMarker.mp4"
    outside.write_bytes(movie)
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append(self.path)
            self.send_response(200)
            self.send_header("Content-Length", str(len(movie)))
            self.end_headers()
            self.wfile.write(movie)

        def log_message(self, *_args):
            pass

    listener = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    listener_thread = threading.Thread(target=listener.serve_forever)
    listener_thread.start()
    child = Child(tmp_path / "Child", mode="media-observe", tools=tools)
    try:
        child.await_ready()
        if kind == "apng":
            png = samples["png"].read_bytes()
            content = png[:33] + formats.png_chunk(b"acTL", struct.pack(">II", 2, 0)) + png[33:]
            mime, expected = "image/png", "media_format_denied"
        else:
            location = f"http://127.0.0.1:{listener.server_port}/owned-marker.mp4" if kind == "network-url" else outside.as_uri()
            entry = formats.box(b"urn ", b"\x00" * 4 + b"owned-marker\x00" + location.encode() + b"\x00") if kind == "outside-urn" else formats.box(b"url ", b"\x00" * 4 + location.encode() + b"\x00")
            content = formats.replace_dref(movie, entry)
            mime, expected = "video/mp4", "media_reference_denied"
        with child.api() as api:
            staged = api.post("/api/v1/assets/staging", content=content, headers={"Content-Type": mime})
            assert staged.status_code == 201
            candidate = original_media.candidate(staged.json())
            responses = [api.post("/api/v1/assets/import", json=candidate) for _ in range(2)]
            envelopes = [original_media.envelope(response, 415, expected).model_dump(mode="json") for response in responses]
            assert all(body["retryability"] == "never" for body in envelopes)
            assert len({body["request_id"] for body in envelopes}) == 2
            assert api.get("/api/v1/health").status_code == 200
        child.send(b"shutdown\n")
        child.stopped()
        host = json.loads((child.directory / "HostReceipt.json").read_text(encoding="utf-8"))
        decoder = [command for command in host["decoder_calls"] if "-version" not in command]
        assert not decoder and not requests
        engine = EngineService(child.data_dir)
        with engine.db.connect() as database:
            state = dict(database.execute("SELECT status,asset_id FROM staging WHERE id=?", (candidate["staging_id"],)).fetchone())
            asset_count = database.execute("SELECT COUNT(*) FROM assets").fetchone()[0]
        assert state == {"status": "ready", "asset_id": None} and asset_count == 0
        assert engine.db.data_dir.joinpath("Staging", candidate["staging_id"]).read_bytes() == content
        assert outside.read_bytes() == movie
        write_receipt(tmp_path / "HttpMediaBoundaryReceipt.json", {"kind": kind, "source_sha256": sha(content),
            "statuses": [response.status_code for response in responses], "envelopes": envelopes,
            "actual_decoder_processes": decoder, "loopback_requests": requests, "staging": state,
            "asset_count": asset_count, "outside_marker_sha256": sha(outside.read_bytes()),
            "scope": "Actual TCP + actual guard + pass-through process observation; not general OS file-read auditing"})
    finally:
        child.close()
        listener.shutdown()
        listener.server_close()
        listener_thread.join(timeout=3)
        assert not listener_thread.is_alive()


@pytest.mark.parametrize("kind,mime", [("png", "image/png"), ("jpeg", "image/jpeg"), ("wave", "audio/wav"), ("video", "video/mp4"), ("audio", "audio/mp4")])
def test_real_tcp_legal_media_imports_decodes_and_protected_range_reads(tmp_path, tools, samples, kind, mime):
    content = samples[kind].read_bytes()
    child = Child(tmp_path / "Child", mode="media-observe", tools=tools)
    try:
        child.await_ready()
        with child.api() as api:
            staged = api.post("/api/v1/assets/staging", content=content, headers={"Content-Type": mime})
            assert staged.status_code == 201
            response = api.post("/api/v1/assets/import", json=original_media.candidate(staged.json()))
            assert response.status_code == 201, response.text
            asset = response.json()
            assert asset["probe"]["decoded"] and asset["media_type"] == mime
            route = "/api/v1/assets/" + asset["asset_id"] + "/content"
            assert api.get(route).content == content
            segment = api.get(route, headers={"Range": "bytes=1-7"})
            assert segment.status_code == 206 and segment.content == content[1:8]
            original_media.envelope(api.get(route, headers={"Authorization": "invalid"}), 401, "unauthorized")
            bad_range = api.get(route, headers={"Range": f"bytes={len(content)+1}-"})
            assert bad_range.status_code == 416 and bad_range.headers["content-type"].startswith("text/plain")
        child.send(b"shutdown\n")
        child.stopped()
        host = json.loads((child.directory / "HostReceipt.json").read_text(encoding="utf-8"))
        decoder = [command for command in host["decoder_calls"] if "-version" not in command]
        assert len(decoder) == 2 and "-xerror" in decoder[1]
        write_receipt(tmp_path / "HttpMediaSuccessReceipt.json", {"kind": kind, "source_sha256": sha(content),
            "actual_http_status": 201, "asset": asset, "actual_decoder_processes": decoder,
            "content_exact": True, "actual_range_status": segment.status_code, "unauthorized_status": 401,
            "invalid_range_status": bad_range.status_code, "provider_calls": 0})
    finally:
        child.close()


def test_real_tcp_original_garbage_is_422_and_original_errors_remain_distinct(tmp_path, tools):
    child = Child(tmp_path / "Child", tools=tools)
    try:
        child.await_ready()
        with child.api() as api:
            original_media.envelope(api.get("/api/v1/health", headers={"Authorization": "invalid"}), 401, "unauthorized")
            original_media.envelope(api.get("/api/v1/health", headers={"Origin": "https://untrusted.invalid"}), 403, "origin_denied")
            original_media.envelope(api.get("/api/v1/assets/not-owned"), 404, "not_found")
            invalid = api.post("/api/v1/projects", json={"name": "public", "api_key": "synthetic-T6-do-not-echo"})
            original_media.envelope(invalid, 422, "invalid_request")
            assert "synthetic-T6-do-not-echo" not in invalid.text and "api_key" not in invalid.text
            first = api.post("/api/v1/projects", json={"name": "public"}, headers={"Idempotency-Key": "same"})
            assert first.status_code == 201
            original_media.envelope(api.post("/api/v1/projects", json={"name": "different"}, headers={"Idempotency-Key": "same"}), 409, "idempotency_conflict")
            staged = api.post("/api/v1/assets/staging", content=b"not a valid WAV or MP4", headers={"Content-Type": "video/mp4"})
            assert staged.status_code == 201
            garbage = api.post("/api/v1/assets/import", json=original_media.candidate(staged.json()))
            body = original_media.envelope(garbage, 422, "media_process_failed")
            assert body.retryability == "never"
            assert api.get("/unknown-path").json() == {"detail": "Not Found"}
            assert api.delete("/api/v1/health").json() == {"detail": "Method Not Allowed"}
            bad_host = api.get("/api/v1/health", headers={"Host": "untrusted.invalid"})
            assert bad_host.status_code == 400 and bad_host.headers["content-type"].startswith("text/plain")
        child.send(b"shutdown\n")
        child.stopped()
        engine = EngineService(child.data_dir)
        with engine.db.connect() as database:
            state = dict(database.execute("SELECT status,asset_id FROM staging WHERE id=?", (staged.json()["staging_id"],)).fetchone())
            assert database.execute("SELECT COUNT(*) FROM assets").fetchone()[0] == 0
        assert state == {"status": "ready", "asset_id": None}
        write_receipt(tmp_path / "HttpOriginalErrorsReceipt.json", {"garbage_status": garbage.status_code,
            "garbage_envelope": garbage.json(), "garbage_staging": state,
            "observed_domain_statuses": [401, 403, 404, 409, 422], "observed_transport_statuses": [400, 404, 405]})
    finally:
        child.close()


def test_actual_cli_export_declares_415_without_public_schema_drift(tmp_path):
    output = tmp_path / "Export"
    env = {k: v for k, v in os.environ.items() if not k.startswith("VIDEO_CREATOR_SECRET_") and k != "VIDEO_CREATOR_API_TOKEN"}
    command = [sys.executable, "-m", "video_creator.cli.main", "export-contracts", "--output-dir", str(output)]
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, timeout=15, check=False)
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    openapi = json.loads((output / "openapi.json").read_text(encoding="utf-8"))
    for methods in openapi["paths"].values():
        for operation in methods.values():
            for status in ["400", "401", "403", "404", "409", "413", "415", "422", "503"]:
                assert operation["responses"][status]["content"]["application/json"]["schema"] == {"$ref": "#/components/schemas/ErrorEnvelope"}
    assert "HTTPValidationError" not in openapi["components"]["schemas"]
    schemas = json.loads((output / "schemas.json").read_text(encoding="utf-8"))
    assert len(schemas["schemas"]) == 43
    write_receipt(tmp_path / "ActualContractExportReceipt.json", {"command": command, "exit_code": result.returncode,
                  "openapi_sha256": sha((output / "openapi.json").read_bytes()),
                  "schemas_sha256": sha((output / "schemas.json").read_bytes()),
                  "public_schema_count": 43, "all_domain_415_reference": "#/components/schemas/ErrorEnvelope"})
