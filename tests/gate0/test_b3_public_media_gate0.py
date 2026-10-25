"""B3 actual HTTP/CLI/FFmpeg boundaries. Test signals are not generated creative media."""

import hashlib
import io
import json
import math
import os
import queue
import subprocess
import sys
import threading
import wave
from array import array
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from video_creator.api.app import create_app
from video_creator.application.assets import AssetService
from video_creator.application.engine import EngineService
from video_creator.cli.main import configured_media_validator
from video_creator.domain.contracts import AssetCandidate, ErrorEnvelope
from video_creator.domain.errors import EngineError

ROOT = Path(__file__).resolve().parents[2]
TOKEN = "synthetic-local-session-" + "x" * 40
MANIFEST = Path("G:/开发测试/Codex/VideoCreatorImplementation/Integration/Evidence/MediaRuntimeManifest.json")


def wav_bytes():
    pcm = array("h", [int(5000 * math.sin(2 * math.pi * 440 * i / 48000)) for i in range(48000)])
    stream = io.BytesIO()
    with wave.open(stream, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(48000)
        output.writeframes(pcm.tobytes())
    return stream.getvalue()


@pytest.fixture
def engine(tmp_path):
    return EngineService(tmp_path / "中文 空格 独立实例")


@pytest.fixture(scope="session")
def tools():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for item in data["files"]:
        path = Path(data["runtime_root"]) / item["relative_path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
    yield Path(data["ffmpeg_path"]), Path(data["ffprobe_path"])
    for item in data["files"]:
        path = Path(data["runtime_root"]) / item["relative_path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]


def client(engine, validator=None):
    return TestClient(create_app(engine, TOKEN, media_validator=validator), base_url="http://127.0.0.1",
                      headers={"Authorization": "Bearer " + TOKEN})


def candidate(staged):
    return {**staged, "source": "self-created-test-signal", "rights": "owned"}


def envelope(response, status, code):
    assert response.status_code == status and response.headers["content-type"].startswith("application/json")
    body = ErrorEnvelope.model_validate(response.json())
    assert body.code == code and body.request_id
    assert set(response.json()) == {"code", "message", "retryability", "request_id"}
    return body


def test_openapi_uses_unique_error_model_for_domain_and_input_failures(engine):
    schema = create_app(engine, TOKEN).openapi()
    components = schema["components"]["schemas"]
    assert components["ErrorEnvelope"]["properties"] == ErrorEnvelope.model_json_schema()["properties"]
    assert "HTTPValidationError" not in components
    for methods in schema["paths"].values():
        for operation in methods.values():
            for status in ["400", "401", "403", "404", "409", "413", "422", "503"]:
                assert operation["responses"][status]["content"]["application/json"]["schema"] == {"$ref": "#/components/schemas/ErrorEnvelope"}
    assert "text/plain" in schema["paths"]["/api/v1/health"]["get"]["responses"]["400"]["content"]
    assert "text/plain" in schema["paths"]["/api/v1/assets/{asset_id}/content"]["get"]["responses"]["416"]["content"]


def test_domain_errors_status_retryability_and_private_input_redaction(engine):
    private = "synthetic-private-source-do-not-echo"
    with client(engine) as api:
        envelope(api.get("/api/v1/health", headers={"Authorization": "invalid"}), 401, "unauthorized")
        envelope(api.get("/api/v1/health", headers={"Origin": "https://untrusted.invalid"}), 403, "origin_denied")
        envelope(api.get("/api/v1/assets/not-owned"), 404, "not_found")
        rejected = api.post("/api/v1/projects", json={"name": "public", "api_key": private})
        assert envelope(rejected, 422, "invalid_request").retryability == "never"
        assert private not in rejected.text and "api_key" not in rejected.text and "input" not in rejected.text
        original = api.post("/api/v1/projects", json={"name": "public"}, headers={"Idempotency-Key": "same"})
        assert original.status_code == 201
        envelope(api.post("/api/v1/projects", json={"name": "different"}, headers={"Idempotency-Key": "same"}), 409, "idempotency_conflict")


def test_framework_transport_errors_are_not_mislabeled_domain_json(engine):
    with client(engine) as api:
        host = api.get("/api/v1/health", headers={"Host": "untrusted.invalid"})
        assert host.status_code == 400 and host.headers["content-type"].startswith("text/plain")
        unknown = api.get("/unknown-path")
        method = api.delete("/api/v1/health")
        assert unknown.status_code == 404 and unknown.json() == {"detail": "Not Found"}
        assert method.status_code == 405 and method.json() == {"detail": "Method Not Allowed"}


@pytest.mark.parametrize("paths,code", [
    ((Path("G:/missing-ffmpeg.exe"), None), "media_runtime_incomplete"),
    ((None, Path("G:/missing-ffprobe.exe")), "media_runtime_incomplete"),
    ((Path("ffmpeg.exe"), Path("ffprobe.exe")), "media_runtime_path_denied"),
    ((Path("//untrusted.invalid/bin/ffmpeg.exe"), Path("//untrusted.invalid/bin/ffprobe.exe")), "media_runtime_path_denied"),
])
def test_launcher_resource_configuration_is_paired_absolute_and_local(engine, paths, code):
    with pytest.raises(EngineError) as error:
        configured_media_validator(engine, *paths)
    assert error.value.code == code


def test_missing_decoder_returns_503_and_preserves_same_ready_staging(engine):
    missing = engine.db.data_dir / "MissingTool.exe"
    assert configured_media_validator(engine, missing, missing) is None
    with client(engine) as api:
        staged = api.post("/api/v1/assets/staging", content=wav_bytes(), headers={"Content-Type": "audio/wav"})
        assert staged.status_code == 201
        for _ in range(2):
            envelope(api.post("/api/v1/assets/import", json=candidate(staged.json())), 503, "media_validator_missing")
    with engine.db.connect() as connection:
        row = connection.execute("SELECT status,asset_id FROM staging WHERE id=?", (staged.json()["staging_id"],)).fetchone()
        assert row["status"] == "ready" and row["asset_id"] is None


@pytest.mark.parametrize("media_type", ["audio/wav", "video/mp4"])
def test_real_decoder_imports_protected_content_and_ranges(engine, tools, tmp_path, media_type):
    validator = configured_media_validator(engine, *tools)
    assert validator is not None
    data = wav_bytes()
    if media_type == "video/mp4":
        signal = engine.db.data_dir / "TestSignal.mp4"
        result = subprocess.run([str(tools[0]), "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-i",
            "testsrc2=size=320x240:rate=10:duration=1", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(signal)], capture_output=True, check=False)
        assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
        data = signal.read_bytes()
    with client(engine, validator) as api:
        staged = api.post("/api/v1/assets/staging", content=data, headers={"Content-Type": media_type}).json()
        imported = api.post("/api/v1/assets/import", json=candidate(staged))
        assert imported.status_code == 201, imported.text
        record = imported.json()
        assert record["probe"]["decoded"] and record["probe"]["duration_us"] == 1_000_000
        assert record["probe"]["has_video"] == (media_type == "video/mp4")
        assert "ffmpeg version" in record["probe"]["tool_version"]
        route = "/api/v1/assets/" + record["asset_id"] + "/content"
        assert api.get(route, headers={"Authorization": "invalid"}).status_code == 401
        whole = api.get(route)
        assert whole.content == data and whole.headers["etag"] == '"' + hashlib.sha256(data).hexdigest() + '"'
        partial = api.get(route, headers={"Range": "bytes=1-10"})
        assert partial.status_code == 206 and partial.content == data[1:11]
        assert partial.headers["content-range"] == f"bytes 1-10/{len(data)}"
        malformed = api.get(route, headers={"Range": "bytes=bad"})
        assert malformed.status_code == 400 and malformed.headers["content-type"].startswith("text/plain")
        excessive = api.get(route, headers={"Range": f"bytes={len(data)+10}-"})
        assert excessive.status_code == 416 and excessive.headers["content-type"].startswith("text/plain")
    (tmp_path / "RealMediaImportReceipt.json").write_text(json.dumps({"media_type": media_type,
        "input_sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "record": record,
        "scope": "real test signal creation/decoder/import/content; not AI-generated shots or AV acceptance"},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def test_invalid_media_never_registers_asset_and_keeps_staging_ready(engine, tools):
    validator = configured_media_validator(engine, *tools)
    with client(engine, validator) as api:
        staged = api.post("/api/v1/assets/staging", content=b"not a valid WAV or MP4", headers={"Content-Type": "video/mp4"}).json()
        envelope(api.post("/api/v1/assets/import", json=candidate(staged)), 422, "media_process_failed")
    with engine.db.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM assets").fetchone()[0] == 0
        assert connection.execute("SELECT status FROM staging WHERE id=?", (staged["staging_id"],)).fetchone()[0] == "ready"


def test_real_import_detects_equal_size_content_tampering(engine, tools):
    validator = configured_media_validator(engine, *tools)
    assets = AssetService(engine)
    staged = assets.stage_bytes("local-user", wav_bytes(), "audio/wav")
    record = assets.import_asset("local-user", AssetCandidate(**candidate(staged)), validator)
    path = assets.content_path("local-user", record.asset_id)
    data = bytearray(path.read_bytes())
    data[-1] ^= 1
    path.write_bytes(data)
    with client(engine, validator) as api:
        envelope(api.get("/api/v1/assets/" + record.asset_id + "/content"), 422, "object_integrity_failed")


def test_cli_real_subprocess_lifecycle_and_media_import(tmp_path, tools):
    import httpx
    from t6_cli_helpers import authorize_instance

    data_dir = tmp_path / "CLI 中文 空格 实例"
    # ADR0081: a `serve` without an Owner binding only answers /health and
    # /api/v1/authorization/*; this case used to import media into that still
    # restricted process and now gets 403 owner_authorization_required. Authorize
    # the instance first through the product's own consent channel (restricted ->
    # pending -> approve -> restart), not the dev/native path, because the case is
    # about a production-shaped CLI serve and its real media import.
    authorize_instance(data_dir)
    environment = {k: v for k, v in os.environ.items() if not k.startswith("VIDEO_CREATOR_SECRET_")}
    environment.update(VIDEO_CREATOR_API_TOKEN=TOKEN, PYTHONPATH=str(ROOT / "services/engine/src"), PYTHONUTF8="1")
    process = subprocess.Popen([sys.executable, "-m", "video_creator.cli.main", "serve", "--data-dir", str(data_dir),
        "--port", "0", "--ffmpeg", str(tools[0]), "--ffprobe", str(tools[1])], cwd=ROOT, env=environment,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
    lines = queue.Queue()
    threading.Thread(target=lambda: lines.put(process.stdout.readline()), daemon=True).start()
    try:
        ready = json.loads(lines.get(timeout=20))
        assert ready["event"] == "ready"
        with httpx.Client(base_url=ready["base_url"], headers={"Authorization": "Bearer " + TOKEN}, trust_env=False) as api:
            assert api.get("/api/v1/health").status_code == 200
            staged = api.post("/api/v1/assets/staging", content=wav_bytes(), headers={"Content-Type": "audio/wav"}).json()
            imported = api.post("/api/v1/assets/import", json=candidate(staged))
            assert imported.status_code == 201, imported.text
            asset_id = imported.json()["asset_id"]
            assert api.get("/api/v1/assets/" + asset_id + "/content").content == wav_bytes()
    finally:
        process.terminate()
        stdout, stderr = process.communicate(timeout=10)
    assert process.returncode is not None and TOKEN not in stdout + stderr
    (tmp_path / "CliLifecycleReceipt.json").write_text(json.dumps({"ready": ready, "child_exit": process.returncode,
        "terminated": True, "imported_real_audio": True, "data_dir": str(data_dir),
        "provider_calls": 0}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
