"""Frozen Test bootstrap preflight; product imports occur only after this."""
from __future__ import annotations

import hashlib
from pathlib import Path

from t15_evidence import strict_json

OWN = Path("G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment").resolve()
REPO = Path("G:/开发测试/Projects/VideoCreator").resolve()
TARGET_MODULE = "video_creator.application.bundles"
TARGET_PATH = REPO / "services/engine/src/video_creator/application/bundles.py"


class NotReadyForExecution(RuntimeError):
    pass


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _existing_file(path, label):
    try:
        result = Path(path).resolve(strict=True)
        if not result.is_file():
            raise NotReadyForExecution(f"{label} must be a file")
        return result
    except OSError as error:
        raise NotReadyForExecution(f"{label} missing before loader") from error


def _canonical(path):
    value = Path(path)
    if not value.is_absolute():
        raise NotReadyForExecution("absolute binding path required")
    return str(value.resolve())


def _map(mapping, label):
    if type(mapping) is not dict or not mapping:
        raise NotReadyForExecution(f"nonempty independently frozen {label} required")
    result = {}
    for path, identity in mapping.items():
        key = _canonical(path)
        if key in result or type(identity) is not str or len(identity) != 64:
            raise NotReadyForExecution(f"invalid {label} identity")
        try:
            int(identity, 16)
        except ValueError as error:
            raise NotReadyForExecution(f"invalid {label} SHA") from error
        result[key] = identity
    return result


def identity_preflight(binding, admission, body_records):
    """Frozen binding is independently hash-pinned; synthetic tests grant nothing."""
    required_sources = _map(binding["required_sources"], "source closure")
    required_resources = _map(binding["required_resources"], "resource closure")
    actual_sources = _map(admission["production_and_test_sources"], "declared sources")
    actual_resources = _map(admission["runtime_resources"], "declared resources")
    if actual_sources != required_sources or actual_resources != required_resources:
        raise NotReadyForExecution("admission cannot change independently frozen closure")
    target = _canonical(binding["target_path"])
    if target not in required_sources:
        raise NotReadyForExecution("target missing before loader")
    root = Path(binding["source_root"]).resolve()
    names = binding["target_module"].split(".")
    expected_chain = []
    for index in range(1, len(names) + 1):
        prefix = ".".join(names[:index])
        path = root.joinpath(*names[:index])
        path = path / "__init__.py" if index < len(names) else path.with_suffix(".py")
        expected_chain.append({"module": prefix, "path": _canonical(path)})
    if binding["module_chain"] != expected_chain or expected_chain[-1]["path"] != target:
        raise NotReadyForExecution("target/package canonical path mismatch")
    if any(item["path"] not in required_sources for item in expected_chain):
        raise NotReadyForExecution("package initializer closure missing")
    if type(body_records) is not list or len(body_records) != len(required_sources):
        raise NotReadyForExecution("complete original source body list required")
    archived = {}
    for item in body_records:
        source = _canonical(item["source_path"])
        if source in archived:
            raise NotReadyForExecution("duplicate source body entry")
        body = _existing_file(item["body_copy"], "source body")
        if not body.is_relative_to(OWN):
            raise NotReadyForExecution("body copy not Test owned")
        archived[source] = body
    if set(archived) != set(required_sources):
        raise NotReadyForExecution("body list missing or extra")
    for source, expected in required_sources.items():
        original = _existing_file(source, "source")
        if not (original.is_relative_to(REPO) or original.is_relative_to(OWN)):
            raise NotReadyForExecution("source not repository/Test owned")
        if file_hash(original) != expected or file_hash(archived[source]) != expected:
            raise NotReadyForExecution("source/body hash mismatch before loader")
    for source, expected in required_resources.items():
        if file_hash(_existing_file(source, "resource")) != expected:
            raise NotReadyForExecution("resource missing/drift before loader")
    return binding


def identity_then_loader(binding, admission, body_records, loader):
    """Order-test seam only: sentinel is neither service nor product bootstrap."""
    checked = identity_preflight(binding, admission, body_records)
    return loader(checked)


def admit_runtime(admission_path, expected_admission_sha256, binding_path, expected_binding_sha256):
    path, frozen = Path(admission_path).resolve(strict=True), Path(binding_path).resolve(strict=True)
    if (not path.is_relative_to(OWN) or not frozen.is_relative_to(OWN)
            or file_hash(path) != expected_admission_sha256
            or file_hash(frozen) != expected_binding_sha256):
        raise NotReadyForExecution("untrusted out-of-band admission/bootstrap binding")
    value = strict_json(path.read_bytes())
    binding = strict_json(frozen.read_bytes())
    if not (value["root_runtime_authorized"] is True
            and value["independent_runtime_adapter_approved"] is True):
        raise NotReadyForExecution("preparation approval is not runtime approval")
    if binding["target_module"] != TARGET_MODULE or _canonical(binding["target_path"]) != str(TARGET_PATH):
        raise NotReadyForExecution("not frozen real BundleService target")
    if _canonical(binding["source_root"]) != str(REPO / "services/engine/src"):
        raise NotReadyForExecution("not producer source root")
    if binding["criterion_version"] != "gate0-v03-alignment-bundle-evidence-v1":
        raise NotReadyForExecution("different criterion")
    criterion = Path(binding["criterion_path"]).resolve(strict=True)
    if (not criterion.is_relative_to(REPO / "docs/acceptance/criteria")
            or file_hash(criterion) != binding["criterion_sha256"]
            or value["criterion_sha256"] != binding["criterion_sha256"]):
        raise NotReadyForExecution("criterion drift")
    instance = Path(value["own_data_dir"]).resolve()
    if not instance.is_relative_to(OWN):
        raise NotReadyForExecution("not own isolated DataDir")
    if value["paid_provider_calls_allowed"] is not False:
        raise NotReadyForExecution("this test stage has zero-fee boundary")
    body_manifest = Path(value["prelaunch_source_body_manifest"]).resolve(strict=True)
    if not body_manifest.is_relative_to(OWN) or file_hash(body_manifest) != value["prelaunch_source_body_manifest_sha256"]:
        raise NotReadyForExecution("producer body archive missing")
    records = strict_json(body_manifest.read_bytes())["files"]
    identity_preflight(binding, value, records)
    if value["source_archives_completed_before_product_import"] is not True:
        raise NotReadyForExecution("post-run archive cannot authorize first import")
    return value, binding
