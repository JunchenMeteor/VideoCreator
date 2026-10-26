"""Local-v1 final speech must not require the v2-only ASR cache initializer."""

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from video_creator.application.media_registration import RegisteredMediaRuntime


def test_local_v1_selected_asr_uses_or_creates_cache(tmp_path: Path):
    manifest = tmp_path / "Asr.json"
    manifest.write_text(json.dumps({"format": "local-asr-resource-v1"}), encoding="utf-8")
    manifest_sha = hashlib.sha256(manifest.read_bytes()).hexdigest()
    route = SimpleNamespace(source="owned_local", capability="transcription", credential_ref=None,
                            max_operation_cost=SimpleNamespace(units=lambda: 0))
    runtime = object.__new__(RegisteredMediaRuntime)
    runtime.path = tmp_path / "Registration.json"
    runtime.path.write_text("{}", encoding="utf-8")
    runtime.config = SimpleNamespace(
        asr_resource_manifest="Asr.json",
        asr_resource_manifest_sha256=manifest_sha,
        asr_runtime_manifest_sha256="runtime-sha",
        asr_route_id="local.asr.test",
    )
    runtime.engine = SimpleNamespace(configured_route=lambda route_id: route)
    sentinel = object()
    runtime._asr_resources_cache = {(manifest_sha, "runtime-sha"): sentinel}
    assert runtime._require_selected_asr() is sentinel
