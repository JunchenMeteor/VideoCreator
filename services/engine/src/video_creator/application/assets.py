"""Controlled staging IDs and immutable content-addressed files."""

import hashlib
import json
import os
from collections.abc import Callable
from pathlib import Path

from video_creator.application.engine import EngineService, canonical, identity
from video_creator.domain.contracts import (
    AssetCandidate,
    AssetRecord,
    MediaProbe,
    reject_secrets,
)
from video_creator.domain.errors import EngineError


class AssetService:
    def __init__(self, engine: EngineService, max_bytes: int = 512 * 1024 * 1024):
        self.engine, self.max_bytes = engine, max_bytes
        self.root = engine.db.data_dir

    def _path(self, folder: str, filename: str) -> Path:
        if not filename or filename in {".", ".."} or filename != Path(filename).name or ":" in filename or "\\" in filename or "/" in filename:
            raise EngineError("path_denied", "Only controlled file identities are accepted", 403)
        path = self.root / folder / filename
        if path.is_symlink() or (self.root / folder).is_symlink() or not path.resolve().is_relative_to(self.root):
            raise EngineError("path_denied", "Storage path escaped the installation", 403)
        return path

    def stage_bytes(self, subject: str, data: bytes, media_type: str) -> dict:
        if not data or len(data) > self.max_bytes:
            raise EngineError("asset_size_denied", "Asset is empty or exceeds the upload limit", 413)
        staging_id, sha = identity("staging"), hashlib.sha256(data).hexdigest()
        (self.root / "Staging").mkdir(exist_ok=True)
        with self.engine.db.transaction() as connection:
            connection.execute("INSERT INTO staging(id,owner,media_type,sha256,size,status) VALUES(?,?,?,?,?,'allocated')", (staging_id, subject, media_type, sha, len(data)))
        destination = self._path("Staging", staging_id)
        temporary = self._path("Staging", staging_id + ".partial")
        with temporary.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
        with self.engine.db.transaction() as connection:
            connection.execute("UPDATE staging SET status='ready' WHERE id=?", (staging_id,))
        return {"staging_id": staging_id, "sha256": sha, "size": len(data), "media_type": media_type}

    def staging_path(self, subject: str, staging_id: str) -> Path:
        """Trusted media driver only; HTTP never returns this absolute path."""
        with self.engine.db.connect() as connection:
            row = connection.execute("SELECT * FROM staging WHERE id=? AND owner=?", (staging_id, subject)).fetchone()
        if row is None:
            raise EngineError("not_found", "Staged asset not found", 404)
        path = self._path("Staging", staging_id)
        if not path.is_file():
            raise EngineError("staging_incomplete", "Staged file has not been committed", 409)
        return path

    def import_asset(self, subject: str, candidate: AssetCandidate,
                     validator: Callable[[Path, str], MediaProbe] | None = None) -> AssetRecord:
        with self.engine.db.connect() as connection:
            staged = connection.execute("SELECT * FROM staging WHERE id=? AND owner=?", (candidate.staging_id, subject)).fetchone()
            if staged and staged["asset_id"]:
                asset = self.get(subject, staged["asset_id"])
                if (asset.sha256, asset.size, asset.media_type, asset.source, asset.rights) != (candidate.sha256, candidate.size, candidate.media_type, candidate.source, candidate.rights):
                    raise EngineError("asset_import_conflict", "Staging identity already has a different immutable import")
                return asset
        if staged is None:
            raise EngineError("not_found", "Staged asset not found", 404)
        path = self.staging_path(subject, candidate.staging_id)
        size = path.stat().st_size
        sha = self._hash(path)
        if (size != candidate.size or sha != candidate.sha256 or size != staged["size"]
                or sha != staged["sha256"] or candidate.media_type != staged["media_type"]):
            raise EngineError("asset_integrity_failed", "Asset size, type or hash does not match", 422)
        if candidate.media_type in {"application/json", "text/plain", "application/x-ndjson"}:
            try:
                text = path.read_text(encoding="utf-8")
                if candidate.media_type == "application/json":
                    reject_secrets(json.loads(text))
                elif candidate.media_type == "application/x-ndjson":
                    for line in text.splitlines():
                        reject_secrets(json.loads(line))
                else:
                    reject_secrets(text)
            except (ValueError, UnicodeError):
                raise EngineError("text_asset_invalid", "Text asset is invalid or contains prohibited secret content", 422) from None
            probe = MediaProbe(media_type=candidate.media_type, tool_version="utf8-json-v1", decoded=True)
        else:
            if validator is None:
                raise EngineError("media_validator_missing", "A real media decoder is required", 503)
            probe = validator(path, candidate.media_type)
            if not probe.decoded or probe.media_type != candidate.media_type:
                raise EngineError("media_invalid", "Actual media decoding failed", 422)
            if candidate.media_type.startswith("video/") and (not probe.has_video or not probe.duration_us):
                raise EngineError("video_stream_missing", "Video has no valid video stream or duration", 422)
            if candidate.media_type.startswith("audio/") and (not probe.has_audio or not probe.duration_us):
                raise EngineError("audio_stream_missing", "Audio has no valid audio stream or duration", 422)
        object_path = self._path("Objects", sha)
        (self.root / "Objects").mkdir(exist_ok=True)
        if object_path.exists():
            if object_path.stat().st_size != size or self._hash(object_path) != sha:
                raise EngineError("object_integrity_failed", "Existing content object is corrupted", 422)
        else:
            # File commit precedes DB; a crash leaves a recoverable content object and staging record.
            temporary = self._path("Objects", identity("object") + ".partial")
            with path.open("rb") as source, temporary.open("xb") as output:
                while block := source.read(1024 * 1024):
                    output.write(block)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, object_path)
        with self.engine.db.transaction() as connection:
            current = connection.execute("SELECT asset_id FROM staging WHERE id=? AND owner=?", (candidate.staging_id, subject)).fetchone()
            if current["asset_id"]:
                asset_id = current["asset_id"]
            else:
                asset_id = identity("asset")
                connection.execute("INSERT INTO assets VALUES(?,?,?,?,?,?,?,?)", (asset_id, subject, sha, size, candidate.media_type, candidate.source, candidate.rights, canonical(probe)))
                connection.execute("UPDATE staging SET status='imported',asset_id=? WHERE id=?", (asset_id, candidate.staging_id))
        return self.get(subject, asset_id)

    def _hash(self, path: Path) -> str:
        value = hashlib.sha256()
        with path.open("rb") as stream:
            while block := stream.read(1024 * 1024):
                value.update(block)
        return value.hexdigest()

    def get(self, subject: str, asset_id: str) -> AssetRecord:
        with self.engine.db.connect() as connection:
            row = connection.execute("SELECT * FROM assets WHERE id=? AND owner=?", (asset_id, subject)).fetchone()
        if row is None:
            raise EngineError("not_found", "Asset not found", 404)
        return AssetRecord(asset_id=row["id"], sha256=row["sha256"], size=row["size"], media_type=row["media_type"], source=row["source"], rights=row["rights"], probe=MediaProbe.model_validate_json(row["probe_json"]))

    def content_path(self, subject: str, asset_id: str) -> Path:
        record = self.get(subject, asset_id)
        path = self._path("Objects", record.sha256)
        if not path.is_file() or path.stat().st_size != record.size:
            raise EngineError("object_unavailable", "Content object is unavailable", 503)
        if self._hash(path) != record.sha256:
            raise EngineError("object_integrity_failed", "Content object no longer matches its registered hash", 422)
        return path
