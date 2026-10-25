"""Real, self-created formats and bounded media counterexamples; no generated artwork."""

import hashlib
import json
import struct
import subprocess
import threading
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import test_b3_public_media_gate0 as media_tests
from video_creator.application.assets import AssetService
from video_creator.application.engine import EngineService
from video_creator.cli.main import configured_media_validator
from video_creator.domain.contracts import AssetCandidate
from video_creator.domain.errors import EngineError
from video_creator.media.ffmpeg import FFmpegRuntime

tools = media_tests.tools


@pytest.fixture(scope="session")
def samples(tmp_path_factory, tools):
    directory = tmp_path_factory.mktemp("T5Samples")
    ffmpeg, _ = tools
    recipes = {
        "png": ["-f", "lavfi", "-i", "color=c=red:s=32x24:d=0.04", "-frames:v", "1", "-c:v", "png", "-f", "image2", "-update", "1"],
        "jpeg": ["-f", "lavfi", "-i", "color=c=blue:s=32x24:d=0.04", "-frames:v", "1", "-c:v", "mjpeg", "-f", "image2", "-update", "1"],
        "video": ["-f", "lavfi", "-i", "color=c=green:s=32x24:r=10:d=1", "-f", "lavfi", "-i", "sine=frequency=733:duration=1", "-t", "1", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-f", "mp4"],
        "audio": ["-f", "lavfi", "-i", "sine=frequency=733:duration=1", "-t", "1", "-c:a", "aac", "-f", "mp4"],
        "quicktime": ["-f", "lavfi", "-i", "color=c=green:s=32x24:r=10:d=1", "-t", "1", "-c:v", "libx264", "-f", "mov"],
        "mp3": ["-f", "lavfi", "-i", "sine=frequency=733:duration=1", "-c:a", "libmp3lame", "-f", "mp3"],
        "nine-streams": ["-f", "lavfi", "-i", "sine=frequency=733:duration=1", *[part for _ in range(9) for part in ("-map", "0:a:0")], "-t", "1", "-c:a", "aac", "-f", "mp4"],
    }
    results = {}
    for name, args in recipes.items():
        path = directory / (name + ".bin")
        command = [str(ffmpeg), "-nostdin", "-v", "error", *args, str(path)]
        result = subprocess.run(command, capture_output=True, check=False, timeout=30)
        assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
        results[name] = path
    wave = directory / "wave.bin"
    wave.write_bytes(media_tests.wav_bytes())
    results["wave"] = wave
    (directory / "FixtureGenerationReceipt.json").write_text(json.dumps({"self_created": True,
        "creative_media": False, "files": [{"kind": k, "path": str(p), "size": p.stat().st_size,
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for k, p in results.items()]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return results


def recorder(monkeypatch):
    calls = []
    original = subprocess.Popen

    def counted(args, *positional, **keywords):
        calls.append([str(value) for value in args])
        return original(args, *positional, **keywords)

    monkeypatch.setattr("video_creator.media.ffmpeg.subprocess.Popen", counted)
    return calls


def persist(tmp_path, kind, content, calls, *, asset=None, error=None, state=None, requests=None, size=None):
    (tmp_path / "RealFormatBoundaryReceipt.json").write_text(json.dumps({"kind": kind,
        "source_sha256": hashlib.sha256(content).hexdigest() if content is not None else None,
        "source_size": len(content) if content is not None else size, "decoder_processes": calls,
        "asset": asset.model_dump(mode="json") if asset else None,
        "error": {"code": error.code, "status": error.status_code} if error else None,
        "staging_state": state, "loopback_requests": requests or [],
        "scope": "Self-created test media, private test sandbox, no secrets or paid API; not artwork"},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def attempt(tmp_path, monkeypatch, tools, content, mime, kind, requests=None):
    engine = EngineService(tmp_path / "MediaInstance")
    service = AssetService(engine)
    validator = configured_media_validator(engine, *tools)
    assert validator is not None
    staged = service.stage_bytes("local-test", content, mime)
    calls = recorder(monkeypatch)
    asset, error = None, None
    try:
        asset = service.import_asset("local-test", AssetCandidate(**staged, source="self-created-test", rights="owned"), validator)
    except EngineError as caught:
        error = caught
    with engine.db.connect() as connection:
        state = dict(connection.execute("SELECT status,asset_id FROM staging WHERE id=?", (staged["staging_id"],)).fetchone())
    persist(tmp_path, kind, content, calls, asset=asset, error=error, state=state, requests=requests)
    return service, asset, error, calls, state


@pytest.mark.parametrize("kind,mime", [("png", "image/png"), ("jpeg", "image/jpeg"), ("wave", "audio/wav"), ("video", "video/mp4"), ("audio", "audio/mp4")])
def test_real_supported_formats_import_with_exact_mime_and_complete_decode(tmp_path, monkeypatch, tools, samples, kind, mime):
    content = samples[kind].read_bytes()
    service, asset, error, calls, state = attempt(tmp_path, monkeypatch, tools, content, mime, kind)
    assert error is None and asset is not None and state["status"] == "imported"
    assert asset.media_type == asset.probe.media_type == mime and asset.probe.decoded
    assert len(calls) == 2 and "-xerror" in calls[1] and calls[1][-3:] == ["-f", "null", "-"]
    assert service.content_path("local-test", asset.asset_id).read_bytes() == content
    if kind in {"png", "jpeg"}:
        assert (asset.probe.width, asset.probe.height) == (32, 24)
        assert asset.probe.duration_us is None and not asset.probe.has_video and not asset.probe.has_audio
    else:
        assert asset.probe.duration_us == 1_000_000 and asset.probe.has_audio
        assert asset.probe.has_video is (kind == "video")


@pytest.mark.parametrize("kind,mime", [("png", "image/jpeg"), ("jpeg", "image/png"), ("video", "audio/wav"), ("audio", "video/mp4")])
def test_claimed_mime_cannot_relabel_real_supported_content(tmp_path, monkeypatch, tools, samples, kind, mime):
    _, asset, error, calls, state = attempt(tmp_path, monkeypatch, tools, samples[kind].read_bytes(), mime, "wrong-mime-" + kind)
    assert asset is None and error.code == "media_invalid" and error.status_code == 422
    assert len(calls) == 2 and state == {"status": "ready", "asset_id": None}


@pytest.mark.parametrize("kind", ["quicktime", "mp3"])
def test_unsupported_real_container_cannot_be_relabelled_as_mp4(tmp_path, monkeypatch, tools, samples, kind):
    _, asset, error, calls, state = attempt(tmp_path, monkeypatch, tools, samples[kind].read_bytes(), "video/mp4", kind)
    assert asset is None and error.status_code == 422 and not calls
    assert state == {"status": "ready", "asset_id": None}


def png_chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


@pytest.mark.parametrize("kind", ["png-truncated", "png-concatenated", "png-animated", "jpeg-truncated", "jpeg-no-image", "mp4-truncated", "mp4-no-stream"])
def test_malformed_or_missing_stream_media_never_imports(tmp_path, monkeypatch, tools, samples, kind):
    png, jpeg, movie = (samples[name].read_bytes() for name in ("png", "jpeg", "video"))
    content = {"png-truncated": png[:-2], "png-concatenated": png + png,
        "png-animated": png[:33] + png_chunk(b"acTL", struct.pack(">II", 2, 0)) + png[33:],
        "jpeg-truncated": jpeg[:-2], "jpeg-no-image": b"\xff\xd8\xff\xe0\x00\x02\xff\xd9",
        "mp4-truncated": movie[:-1], "mp4-no-stream": movie[:int.from_bytes(movie[:4], "big")] + box(b"moov", box(b"trak", box(b"mdia", box(b"minf", box(b"dinf", box(b"dref", b"\x00" * 4 + struct.pack(">I", 1) + box(b"url ", b"\x00\x00\x00\x01"))))))) }[kind]
    mime = "image/png" if kind.startswith("png") else "image/jpeg" if kind.startswith("jpeg") else "video/mp4"
    _, asset, error, _calls, state = attempt(tmp_path, monkeypatch, tools, content, mime, kind)
    assert asset is None and error.status_code in {415, 422}
    assert state == {"status": "ready", "asset_id": None}


@pytest.mark.parametrize("width,height", [(8193, 1), (4100, 4100)])
def test_declared_image_dimensions_exceeding_real_limits_refuse_before_parser(tmp_path, monkeypatch, tools, samples, width, height):
    original = samples["png"].read_bytes()
    ihdr = struct.pack(">II", width, height) + original[24:29]
    content = original[:8] + png_chunk(b"IHDR", ihdr) + original[33:]
    _, asset, error, calls, state = attempt(tmp_path, monkeypatch, tools, content, "image/png", "oversized-png")
    assert asset is None and error.code == "media_resource_limit" and not calls
    assert state == {"status": "ready", "asset_id": None}


def test_actual_oversized_file_refuses_before_parser(tmp_path, monkeypatch, tools):
    staging = tmp_path / "Staging"
    staging.mkdir()
    path = staging / "OwnOversize.bin"
    with path.open("wb") as output:
        output.truncate(256 * 1024 * 1024 + 1)
    runtime = FFmpegRuntime(*tools, staging)
    calls = recorder(monkeypatch)
    with pytest.raises(EngineError) as captured:
        runtime.probe(path)
    persist(tmp_path, "actual-file-over-256MiB", None, calls, error=captured.value, size=path.stat().st_size)
    assert captured.value.code == "media_resource_limit" and not calls
    path.unlink()


def test_real_nine_stream_mp4_exceeds_declared_stream_limit(tmp_path, monkeypatch, tools, samples):
    _, asset, error, calls, state = attempt(tmp_path, monkeypatch, tools, samples["nine-streams"].read_bytes(), "audio/mp4", "nine-streams")
    assert asset is None and error.status_code == 422 and len(calls) == 1
    assert state == {"status": "ready", "asset_id": None}


def box(kind, payload):
    return struct.pack(">I", len(payload) + 8) + kind + payload


def replace_dref(data, entry):
    """Fixture mutation preserves every unrelated generated MP4 box byte."""
    pieces, position = [], 0
    while position < len(data):
        size = int.from_bytes(data[position:position + 4], "big")
        kind = data[position + 4:position + 8]
        assert 8 <= size <= len(data) - position
        payload = data[position + 8:position + size]
        if kind in {b"moov", b"trak", b"mdia", b"minf", b"dinf"}:
            payload = replace_dref(payload, entry)
        elif kind == b"dref":
            payload = b"\x00" * 4 + struct.pack(">I", 1) + entry
        pieces.append(box(kind, payload))
        position += size
    return b"".join(pieces)


@pytest.mark.parametrize("kind", ["network-url", "outside-url", "outside-urn"])
def test_real_mp4_external_dref_refuses_before_parser_or_reference_read(tmp_path, monkeypatch, tools, samples, kind):
    content = samples["video"].read_bytes()
    outside = tmp_path / "OutsideMarker.mp4"
    outside.write_bytes(content)
    requests = []

    class MarkerHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != "/marker.mp4":
                self.send_error(404)
                return
            requests.append(self.path)
            self.send_response(200)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), MarkerHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        location = f"http://127.0.0.1:{server.server_port}/marker.mp4" if kind == "network-url" else outside.as_uri()
        entry = box(b"urn ", b"\x00" * 4 + b"owned-marker\x00" + location.encode() + b"\x00") if kind == "outside-urn" else box(b"url ", b"\x00" * 4 + location.encode() + b"\x00")
        modified = replace_dref(content, entry)
        assert b"mdat" in modified and b"h264" not in entry and location.encode() in modified
        _, asset, error, calls, state = attempt(tmp_path, monkeypatch, tools, modified, "video/mp4", "dref-" + kind, requests)
        assert asset is None and error.code == "media_reference_denied" and not calls and not requests
        assert state == {"status": "ready", "asset_id": None}
        assert outside.read_bytes() == content
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
