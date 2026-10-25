"""Resolve an installer-pinned ASR directory; provenance paths never drive I/O."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from video_creator.domain.errors import EngineError
from video_creator.providers.local_asr import LocalAsrDriver


def _relative(root: Path, name: str) -> Path:
    relative = PurePosixPath(name)
    if (not isinstance(name, str) or relative.is_absolute() or not relative.parts
        or any(part in {"", ".", ".."} or ":" in part or "\\" in part for part in relative.parts)):
        raise EngineError("asr_resource_denied", "Resource paths must stay inside the installation.", 403)
    path = root.joinpath(*relative.parts)
    if path.is_symlink() or not path.resolve().is_relative_to(root):
        raise EngineError("asr_resource_denied", "Resource paths must stay inside the installation.", 403)
    return path


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


@dataclass(frozen=True)
class LocalAsrResources:
    python: Path
    model_dir: Path
    model_revision: str
    model_file_sha256: dict[str, str]
    manifest_sha256: str
    runtime_manifest_sha256: str
    manifest_path: Path | None = None

    def driver(self, audio: Path, *, storage_root: Path, runtime_root: Path,
               expected_audio_sha256: str, **controls) -> LocalAsrDriver:
        return LocalAsrDriver(audio, storage_root=storage_root, runtime_root=runtime_root,
                              python_executable=self.python, model_dir=self.model_dir,
                              model_revision=self.model_revision, expected_model_files=self.model_file_sha256,
                              expected_audio_sha256=expected_audio_sha256,
                              resource_manifest_path=self.manifest_path,
                              resource_manifest_sha256=self.manifest_sha256 if self.manifest_path is not None else None, **controls)


def load_asr_resources(manifest_path: Path, expected_manifest_sha256: str,
                       expected_runtime_manifest_sha256: str) -> LocalAsrResources:
    path = Path(manifest_path)
    if path.is_symlink() or not path.is_file() or _hash(path) != expected_manifest_sha256:
        raise EngineError("asr_resource_changed", "Trusted ASR configuration changed.", 503)
    root = path.resolve().parent
    manifest = json.loads(path.read_text(encoding="utf-8"))
    index = _relative(root, manifest["runtime_manifest"])
    if _hash(index) != expected_runtime_manifest_sha256:
        raise EngineError("asr_resource_changed", "Trusted ASR resource index changed.", 503)
    files = json.loads(index.read_text(encoding="utf-8"))["files"]
    seen = set()
    for item in files:
        resource = _relative(root, item["relative_path"])
        if str(resource).casefold() in seen or not resource.is_file() or resource.stat().st_size != item["bytes"] or _hash(resource) != item["sha256"]:
            raise EngineError("asr_resource_changed", "Installed ASR resources differ from their trusted index.", 503)
        seen.add(str(resource).casefold())
    for key in ("provider", "worker"):
        installed = _relative(root, manifest[key])
        current = Path(__file__).with_name("local_asr.py") if key == "provider" else Path(__file__).parents[1] / "media/asr_worker.py"
        if _hash(installed) != manifest[key + "_sha256"] or _hash(current) != manifest[key + "_sha256"]:
            raise EngineError("asr_code_changed", "ASR protocol code differs from its admitted version.", 503)
    model = _relative(root, manifest["model_dir"])
    for name, digest in manifest["model_file_sha256"].items():
        if _hash(_relative(model.resolve(), name)) != digest:
            raise EngineError("asr_model_changed", "ASR model differs from trusted installation bytes.", 503)
    return LocalAsrResources(_relative(root, manifest["python"]), model,
                             manifest["model_revision"], dict(manifest["model_file_sha256"]),
                             expected_manifest_sha256, expected_runtime_manifest_sha256, path.resolve())
