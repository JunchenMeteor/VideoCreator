"""Production resources pinned by the same trusted installer manifest/index."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath

from video_creator.domain.errors import EngineError
from video_creator.workflows.attempt_control import current_attempt


def file_sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            current_attempt().check()
            digest.update(block)
    return digest.hexdigest()


def contained_file(root: Path, name: str):
    if not isinstance(name, str):
        raise EngineError("production_resource_denied", "Resource requires an installation-relative path.", 403)
    relative = PurePosixPath(name)
    if (relative.is_absolute() or not relative.parts or relative.as_posix() != name
            or any(part in {".", ".."} or ":" in part or "\\" in part for part in relative.parts)):
        raise EngineError("production_resource_denied", "Resource path must remain inside its installation.", 403)
    root = root.resolve(strict=True)
    path = root.joinpath(*relative.parts)
    for candidate in (path, *path.parents):
        if candidate.is_relative_to(root) and (candidate.is_symlink() or candidate.is_junction()):
            raise EngineError("production_resource_denied", "Resource links are not admitted.", 403)
    if not path.is_file() or not path.resolve(strict=True).is_relative_to(root):
        raise EngineError("production_resource_missing",
                          f"Exact installed resource is unavailable: root={root}; name={name}", 503)
    return path


def _object(path, limit):
    if path.stat().st_size > limit:
        raise EngineError("production_resource_invalid", "Installed resource metadata exceeds its bound.", 503)
    try:
        def unique(pairs):
            value = {}
            for key, child in pairs:
                if key in value:
                    raise ValueError("duplicate metadata key")
                value[key] = child
            return value
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)
        if not isinstance(value, dict):
            raise TypeError("object required")
        return value
    except (TypeError, ValueError, UnicodeError):
        raise EngineError("production_resource_invalid", "Installed production metadata is invalid.", 503) from None


class ProductionResources:
    def __init__(self, manifest_path, manifest_sha256, runtime_manifest_sha256):
        path = Path(manifest_path)
        if path.is_symlink() or path.is_junction() or file_sha256(path) != manifest_sha256:
            raise EngineError("production_resource_changed", "Exact installer manifest changed.", 503)
        self.root = path.resolve(strict=True).parent
        manifest = _object(path, 2 * 1024 * 1024)
        index = contained_file(self.root, manifest["runtime_manifest"])
        if file_sha256(index) != runtime_manifest_sha256:
            raise EngineError("production_resource_changed", "Exact installed resource index changed.", 503)
        records = _object(index, 16 * 1024 * 1024).get("files")
        if not isinstance(records, list) or not 0 < len(records) <= 100000:
            raise EngineError("production_resource_invalid", "Installed resource index has no bounded file list.", 503)
        self.records = {}
        for record in records:
            if (type(record) is not dict or not {"relative_path", "bytes", "sha256"} <= set(record)
                    or type(record["relative_path"]) is not str or type(record["sha256"]) is not str):
                raise EngineError("production_resource_invalid", "Resource index fields are not exact file identities.", 503)
            name = record["relative_path"]
            if (name.casefold() in self.records or type(record["bytes"]) is not int or record["bytes"] < 0
                    or not re.fullmatch("[0-9a-f]{64}", record["sha256"])):
                raise EngineError("production_resource_invalid", "Resource identities are not exact and distinct.", 503)
            self.records[name.casefold()] = record
        for record in self.records.values():
            self.resource(record["relative_path"])
        self.config = manifest.get("production_drivers")
        if not isinstance(self.config, dict):
            raise EngineError("production_driver_resources_missing", "Production TTS/video/edit resources have not been installed in this manifest.", 503)
        version = self.config.get("format")
        self.recipe_resources = None
        if version in {"registered-production-driver-resources-v3", "registered-production-driver-resources-v3-diagnostic-v1"}:
            from video_creator.domain.affected_recipe import (
                parse_production_recipe_resources,
            )

            self.recipe_resources = parse_production_recipe_resources(self.config)
            actual = self.recipe_resources
            self.config = actual.model_dump(mode="json", by_alias=True)
            for recipe in actual.recipes:
                for reference in recipe.producer_source_refs:
                    if file_sha256(self.resource(reference.resource_name)) != reference.sha256:
                        raise EngineError("production_recipe_source_changed", "Recipe producers differ from their indexed installation.", 503)
            if version == "registered-production-driver-resources-v3-diagnostic-v1":
                for method in actual.diagnosis.methods:
                    for reference in method.implementation_source_refs:
                        if file_sha256(self.resource(reference.resource_name)) != reference.sha256:
                            raise EngineError("diagnostic_source_changed", "Diagnostic implementation differs from its indexed installation.", 503)
            if actual.alignment is not None:
                for name, expected in actual.alignment.model_files.items():
                    if file_sha256(self.resource(name)) != expected:
                        raise EngineError("alignment_resource_changed", "Declared model bytes differ from their actual indexed identities.", 503)
                self.resource(actual.alignment.worker_resource)
                self.resource(actual.alignment.runtime_resource)
        elif version == "registered-production-driver-resources-v2":
            from pydantic import ValidationError

            from video_creator.domain.affected_repair import ProductionDriverResourcesV2

            try:
                actual = ProductionDriverResourcesV2.model_validate_json(json.dumps(self.config, ensure_ascii=False, allow_nan=False))
            except ValidationError:
                raise EngineError("production_driver_resources_invalid", "Actual v2 resources must satisfy the sole installed grammar.", 503) from None
            self.config = actual.model_dump(mode="json", by_alias=True)
            if actual.alignment is not None:
                for name, expected in actual.alignment.model_files.items():
                    if file_sha256(self.resource(name)) != expected:
                        raise EngineError("alignment_resource_changed", "Declared model bytes differ from their actual indexed identities.", 503)
                self.resource(actual.alignment.worker_resource)
                self.resource(actual.alignment.runtime_resource)
        elif version != "registered-production-driver-resources-v1":
            raise EngineError("production_driver_resources_missing", "Installed resources require an explicit original or registered recipe grammar.", 503)
        self.manifest_sha256 = manifest_sha256
        self.runtime_manifest_sha256 = runtime_manifest_sha256

    def resource(self, name):
        path = contained_file(self.root, name)
        record = self.records.get(name.casefold())
        if record is None or path.stat().st_size != record["bytes"] or file_sha256(path) != record["sha256"]:
            raise EngineError("production_resource_changed", "Production resource differs from its trusted index.", 503)
        return path

    def section(self, name, kind):
        value = self.config.get(name)
        if not isinstance(value, dict) or value.get("kind") != kind:
            raise EngineError("production_" + name + "_not_configured", "Required actual production adapter is not configured.", 503)
        return dict(value)
