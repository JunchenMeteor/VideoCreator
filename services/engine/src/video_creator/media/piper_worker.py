"""Fixed isolated Piper CPU worker; actual synthesis, no ASR or downloads."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import sys
import wave
from pathlib import Path


def _hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def main():
    request = json.loads(sys.stdin.buffer.read(32769))
    if not isinstance(request, dict) or request.get("protocol") != "piper-production-worker-v1":
        raise ValueError("protocol")
    text = request["text"]
    if type(text) is not str or not 0 < len(text) <= 4000:
        raise ValueError("text")
    root = Path(request["resource_root"]).resolve(strict=True)
    paths = {}
    for name in ("model", "model_config", "license_document"):
        path = Path(request[name])
        if path.is_symlink() or path.is_junction() or not path.resolve(strict=True).is_relative_to(root):
            raise ValueError("resource path")
        if _hash(path) != request[name + "_sha256"]:
            raise ValueError("resource changed")
        paths[name] = path
    if paths["model_config"] != Path(str(paths["model"]) + ".json"):
        raise ValueError("model config")
    output = Path(request["partial_output"])
    storage = Path(request["storage_root"]).resolve(strict=True)
    if (not output.resolve().is_relative_to(storage) or output.exists()
            or any(path.is_symlink() or path.is_junction() for path in (output, *output.parents)
                   if path.is_relative_to(storage))):
        raise ValueError("output")
    version = importlib.metadata.version("piper-tts")
    if version != request["piper_version"]:
        raise ValueError("runtime version")
    from piper import PiperVoice
    voice = PiperVoice.load(str(paths["model"]), use_cuda=False)
    with output.open("xb") as target, wave.open(target, "wb") as audio:
        voice.synthesize_wav(text, audio)
    with wave.open(str(output), "rb") as audio:
        frames, rate = audio.getnframes(), audio.getframerate()
        channels, width = audio.getnchannels(), audio.getsampwidth()
    if not 0 < frames <= rate * 600 or channels != 1 or width != 2:
        raise ValueError("actual PCM output")
    return {"protocol": "piper-production-worker-v1", "status": "succeeded",
            "source_text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "output_sha256": _hash(output), "output_bytes": output.stat().st_size,
            "sample_rate": rate, "frames": frames, "channels": channels, "sample_width": width,
            "duration_us": (frames * 1_000_000 + rate - 1) // rate,
            "runtime": {"piper-tts": version, "python": platform.python_version(),
                        "os": platform.system(), "machine": platform.machine(), "device": "cpu"}}


if __name__ == "__main__":
    try:
        response = main()
    except Exception:  # noqa: BLE001 - child errors expose only a fixed code, never provider/config text.
        print(json.dumps({"status": "failed", "error_code": "piper_synthesis_failed"}))
        sys.exit(1)
    print(json.dumps(response, ensure_ascii=False, allow_nan=False))
