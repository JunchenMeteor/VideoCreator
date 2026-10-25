"""Real decoder probes use only self-created markers and a loopback listener."""

import hashlib
import json
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import test_b3_public_media_gate0 as media_tests
from video_creator.application.assets import AssetService
from video_creator.application.engine import EngineService
from video_creator.cli.main import configured_media_validator
from video_creator.domain.contracts import AssetCandidate
from video_creator.domain.errors import EngineError

tools = media_tests.tools
wav_bytes = media_tests.wav_bytes


@pytest.fixture
def marker_media(tmp_path, tools):
    ffmpeg, _ = tools
    outside = tmp_path / "OwnedOutside"
    outside.mkdir()
    segment = outside / "PublicMarker.ts"
    subprocess.run([str(ffmpeg), "-nostdin", "-v", "error", "-f", "lavfi", "-i",
        "sine=frequency=733:sample_rate=48000:duration=1", "-c:a", "aac", "-f", "mpegts", str(segment)],
        check=True, capture_output=True, timeout=15)
    return segment


def record(tmp_path, kind, staged_path, content, calls, requests, error, asset, segment=None):
    receipt = {"scope": "Own test sandbox and 127.0.0.1 only; no credentials, external DNS or paid services",
        "kind": kind, "staged_path": str(staged_path), "input_sha256": hashlib.sha256(content).hexdigest(),
        "input_bytes": content.decode("utf-8") if kind != "self-contained-wav" else "self-created PCM WAV",
        "decoder_processes": calls, "loopback_requests": requests,
        "error_code": error.code if error is not None else None,
        "imported": asset.model_dump(mode="json") if asset is not None else None,
        "external_marker": {"path": str(segment), "sha256": hashlib.sha256(segment.read_bytes()).hexdigest()} if segment else None,
        "real_creative_media": False}
    (tmp_path / "MediaReferenceReceipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n")


def track_decoder(monkeypatch):
    calls = []
    original = subprocess.Popen

    def counted(args, *positional, **keywords):
        calls.append([str(value) for value in args])
        return original(args, *positional, **keywords)

    monkeypatch.setattr("video_creator.media.ffmpeg.subprocess.Popen", counted)
    return calls


def test_self_contained_wav_still_uses_real_probe_and_full_decode(tmp_path, monkeypatch, tools):
    engine = EngineService(tmp_path / "MediaInstance")
    validator = configured_media_validator(engine, *tools)
    assert validator is not None
    service = AssetService(engine)
    content = wav_bytes()
    staged = service.stage_bytes("local-test", content, "audio/wav")
    calls = track_decoder(monkeypatch)
    asset = service.import_asset("local-test", AssetCandidate(**staged, source="self-created", rights="owned"), validator)
    record(tmp_path, "self-contained-wav", service.staging_path("local-test", staged["staging_id"]), content, calls, [], None, asset)
    assert asset.probe.decoded and asset.probe.has_audio and asset.probe.duration_us == 1_000_000
    assert len(calls) == 2 and service.content_path("local-test", asset.asset_id).read_bytes() == content


@pytest.mark.parametrize("kind", ["hls-network", "hls-local-outside", "concat-local-outside"])
def test_external_references_are_rejected_before_any_decoder_parse(tmp_path, monkeypatch, tools, marker_media, kind):
    marker = marker_media.read_bytes()
    requests = []

    class MarkerHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != "/PublicMarker.ts":
                self.send_error(404)
                return
            requests.append({"path": self.path, "bytes_served": len(marker), "sha256": hashlib.sha256(marker).hexdigest()})
            self.send_response(200)
            self.send_header("Content-Type", "video/mp2t")
            self.send_header("Content-Length", str(len(marker)))
            self.end_headers()
            self.wfile.write(marker)

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), MarkerHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        reference = f"http://127.0.0.1:{server.server_port}/PublicMarker.ts" if kind == "hls-network" else "../../OwnedOutside/PublicMarker.ts"
        playlist = ("ffconcat version 1.0\nfile '" + reference + "'\n") if kind == "concat-local-outside" else (
            "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:1\n#EXT-X-MEDIA-SEQUENCE:0\n#EXTINF:1.0,\n" + reference + "\n#EXT-X-ENDLIST\n")
        content = playlist.encode("utf-8")
        engine = EngineService(tmp_path / "MediaInstance")
        service = AssetService(engine)
        validator = configured_media_validator(engine, *tools)
        assert validator is not None
        staged = service.stage_bytes("local-test", content, "audio/wav")
        staged_path = service.staging_path("local-test", staged["staging_id"])
        calls = track_decoder(monkeypatch)
        error, asset = None, None
        try:
            asset = service.import_asset("local-test", AssetCandidate(**staged, source="self-created-boundary-fixture", rights="owned"), validator)
        except EngineError as caught:
            error = caught
        record(tmp_path, kind, staged_path, content, calls, requests, error, asset, marker_media)
        assert error is not None and asset is None, "An external-reference document cannot become a self-contained media asset"
        assert not requests, "No request may fetch even the controlled loopback marker"
        assert not calls, "Reject external-reference content before passing it to a media parser"
        with engine.db.connect() as connection:
            row = connection.execute("SELECT status,asset_id FROM staging WHERE id=?", (staged["staging_id"],)).fetchone()
        assert row["status"] == "ready" and row["asset_id"] is None
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
