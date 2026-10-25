"""Pinned data-only production resources for the existing indexed builder.

No Engine/provider import, resolver, download, executable or authority issuance.
This builds integrity inputs; runtime/ABI/licence qualification remains separate.
"""
from __future__ import annotations

import argparse
import email.parser
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat

MANIFEST_LIMIT = 2 * 1024 * 1024
INDEX_LIMIT = 16 * 1024 * 1024
FILE_LIMIT = 100000
SOURCE_LIMIT = 16 * 1024 * 1024
SHA = re.compile(r"[0-9a-f]{64}\Z")
IDENTIFIER = re.compile(r"[A-Za-z0-9_.:-]{1,128}\Z")


def relative(value):
    if (type(value) is not str or not value or PurePosixPath(value).as_posix() != value
            or PurePosixPath(value).is_absolute() or any(
                part in {".", ".."} or ":" in part or "\\" in part
                or part.rstrip(". ") != part
                or any(ord(char) < 32 or 0xD800 <= ord(char) <= 0xDFFF for char in part)
                for part in value.split("/"))):
        raise ValueError("Invalid installation-relative path: " + repr(value))
    return value


def physical(value):
    path = Path(value)
    if not path.is_absolute() or str(path).startswith(("\\\\", "//")):
        raise ValueError("An absolute local physical input is required")
    for member in (path, *path.parents):
        info = member.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 1024:
            raise ValueError("Linked input/ancestor: " + str(member))
    return path.resolve(strict=True)


def identity(path, limit=None):
    path = physical(path)
    digest = hashlib.sha256()
    body = bytearray() if limit is not None else None
    path_before = path.stat()
    with path.open("rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or (limit is not None and before.st_size > limit):
            raise ValueError("Non-file or oversized bounded input: " + str(path))
        count = 0
        while block := stream.read(1024 * 1024):
            count += len(block)
            if count > before.st_size or (limit is not None and count > limit):
                raise ValueError("Input grew while reading")
            digest.update(block)
            if body is not None:
                body.extend(block)
        after = os.fstat(stream.fileno())
    current = path.stat()
    fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
    # On this actual Windows interpreter fstat.ctim is last-change whereas
    # path.stat.ctim is birth time. Preserve both independent stable checks;
    # cross-API identity uses dev/ino/size/mtime and, where present, birthtime.
    cross_fields = fields[:-1] if os.name == "nt" else fields
    if (count != before.st_size
            or any(getattr(before, field) != getattr(after, field) for field in fields)
            or any(getattr(path_before, field) != getattr(current, field) for field in fields)
            or any(getattr(before, field) != getattr(current, field) for field in cross_fields)
            or getattr(before, "st_birthtime_ns", None) != getattr(current, "st_birthtime_ns", None)):
        raise ValueError("Input changed while reading: " + str(path))
    return {"path": str(path), "bytes": count, "sha256": digest.hexdigest()}, body


def unique_object(pairs):
    value = {}
    for key, child in pairs:
        if key in value:
            raise ValueError("Duplicate JSON key")
        value[key] = child
    return value


def checked(ref, limit=None):
    if (type(ref) is not dict or not {"path", "bytes", "sha256"} <= set(ref)
            or type(ref["bytes"]) is not int or ref["bytes"] < 0
            or type(ref["sha256"]) is not str or not SHA.fullmatch(ref["sha256"])):
        raise ValueError("A complete immutable file reference is required")
    actual, body = identity(ref["path"], limit)
    if any(actual[field] != ref[field] for field in ("bytes", "sha256")):
        raise ValueError("Pinned input changed: " + str(ref["path"]))
    return actual, body


def document(ref, limit):
    actual, body = checked(ref, limit)
    value = json.loads(bytes(body).decode("utf-8"), object_pairs_hook=unique_object,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))
    if type(value) is not dict:
        raise ValueError("JSON object required")
    return actual, value


def members(root):
    root = physical(root)
    pending, files, folded = [root], {}, set()
    while pending:
        directory = pending.pop()
        for child in sorted(directory.iterdir()):
            info = child.lstat()
            name = relative(child.relative_to(root).as_posix())
            if name.casefold() in folded:
                raise ValueError("Casefold directory/file collision: " + name)
            folded.add(name.casefold())
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 1024:
                raise ValueError("Linked resource member: " + name)
            if stat.S_ISDIR(info.st_mode):
                pending.append(child)
            elif stat.S_ISREG(info.st_mode):
                files[name] = child
                if len(files) > FILE_LIMIT:
                    raise ValueError("Resource file count exceeds 100000")
            else:
                raise ValueError("Nonregular resource member: " + name)
    return files


def source_selection(indices):
    """Merge explicitly frozen maps; different bytes need explicit supersedes."""
    selected, provenance, pins = {}, [], []
    for descriptor in indices:
        ref, value = document(descriptor, SOURCE_LIMIT)
        pins.append(ref)
        kind = descriptor["kind"]
        if kind not in {"backend", "media", "engine"}:
            raise ValueError("Unsupported immutable source index kind")
        mapping = value["sources"] if kind == "media" else value["source_map"]
        if not mapping:
            raise ValueError("Unsupported or empty immutable source index")
        source_root = physical(descriptor["ordinary_root"])
        for name, item in mapping.items():
            name = relative(name)
            if kind == "media":
                target = "Code/video_creator/" + name
            elif name.startswith("services/engine/src/"):
                target = "Code/" + name.removeprefix("services/engine/src/")
            elif name.startswith("services/engine/migrations/"):
                target = "Migrations/" + name.removeprefix("services/engine/migrations/")
            else:
                raise ValueError("Unexpected Engine source index member: " + name)
            source = physical(item["ordinary_copy"])
            if source != physical(source_root / name):
                raise ValueError("Ordinary copy is outside its exact index layout")
            file_ref = {"path": str(source), "bytes": item.get("bytes", item.get("size")),
                        "sha256": item["sha256"]}
            fact, _ = checked(file_ref)
            pins.append(fact)
            previous = selected.get(target)
            if previous and previous["sha256"] != fact["sha256"]:
                if descriptor.get("supersedes", {}).get(target) != previous["sha256"]:
                    raise ValueError("Source override lacks exact superseded identity: " + target)
            selected[target] = {**fact, "relative_path": relative(target)}
            provenance.append({"relative_path": target, "index_sha256": ref["sha256"],
                               "index_member": name, "source": fact})
    folded = [name.casefold() for name in selected]
    if len(set(folded)) != len(folded):
        raise ValueError("Casefold source collision")
    if "Code/video_creator/workflows/current_policy_evidence.py" not in selected:
        raise ValueError("Complete current policy Media source is required")
    return selected, provenance, pins


def diagnostic_decoder():
    # Fixed sibling build tool, never a path/plugin supplied by the input plan.
    import importlib.util
    path = Path(__file__).with_name("ValidateDiagnosticCatalog.py")
    physical(path)
    spec = importlib.util.spec_from_file_location("_fixed_diagnostic_catalog", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def driver_config(value, selected=None):
    if type(value) is dict and value.get("format") == "registered-production-driver-resources-v3-diagnostic-v1":
        if selected is None:
            raise ValueError("Diagnostic catalog requires the complete immutable Backend source selection")
        decoded = diagnostic_decoder().normalize_drivers(value, selected, checked)
        # Retain the original stricter physical-path/provider host checks, while
        # the sole Backend model owns alignment/recipes/diagnosis semantics.
        driver_config({"format": "registered-production-driver-resources-v1",
                       **{key: decoded[key] for key in ("narration", "picture", "edit")}})
        return decoded
    if type(value) is not dict or set(value) != {"format", "narration", "picture", "edit"}:
        raise ValueError("Exact production driver sections are required")
    if value["format"] != "registered-production-driver-resources-v1":
        raise ValueError("Unsupported production driver format")
    narration, picture, edit = (value[name] for name in ("narration", "picture", "edit"))
    if (type(narration) is not dict or set(narration) != {
            "kind", "python", "worker", "model", "model_config", "license_document", "version"}
            or narration["kind"] != "piper" or type(narration["version"]) is not str
            or not IDENTIFIER.fullmatch(narration["version"])):
        raise ValueError("Complete pinned Piper resources/version are required")
    for key in ("python", "worker", "model", "model_config", "license_document"):
        relative(narration[key])
    if narration["model_config"] != narration["model"] + ".json":
        raise ValueError("Piper model/config pair differs from the original worker")
    if (type(picture) is not dict or set(picture) != {
            "kind", "workspace_id", "region", "model", "resolution", "download_hosts"}
            or picture["kind"] != "wan2.7" or type(picture["workspace_id"]) is not str
            or not re.fullmatch(r"[a-zA-Z0-9-]{2,63}", picture["workspace_id"])
            or picture["region"] not in {"cn-beijing", "ap-southeast-1"}
            or picture["model"] != "wan2.7-t2v-2026-06-12"
            or picture["resolution"] not in {"720P", "1080P"}
            or type(picture["download_hosts"]) is not list
            or not 0 < len(picture["download_hosts"]) <= 16):
        raise ValueError("An actual selected Wan adapter configuration is required")
    hosts = picture["download_hosts"]
    if len(set(hosts)) != len(hosts) or any(type(host) is not str
            or not re.fullmatch(r"[a-z0-9.-]{1,253}", host)
            or not host.endswith(".aliyuncs.com") or ".." in host or host.startswith(".") for host in hosts):
        raise ValueError("Exact bounded Wan storage hosts required")
    if type(edit) is not dict or set(edit) != {"kind", "ffmpeg", "ffprobe"} or edit["kind"] != "ffmpeg":
        raise ValueError("Exact FFmpeg/ffprobe resources required")
    relative(edit["ffmpeg"])
    relative(edit["ffprobe"])
    return value


def prepare(plan_path, expected_sha256, backend_index_sha256):
    """Validate all supplied local inputs before the indexed builder writes."""
    plan_fact, _ = identity(plan_path, SOURCE_LIMIT)
    if plan_fact["sha256"] != expected_sha256:
        raise ValueError("Production input plan changed")
    _, plan = document(plan_fact, SOURCE_LIMIT)
    required = {"format", "source_indices", "resource_groups", "production_drivers",
                "registration_template", "asr_manifest", "outputs", "target"}
    diagnostic = plan.get("format") == "current-production-resource-build-v2-diagnostic-v1"
    if diagnostic:
        required.add("catalog_bindings")
    if set(plan) != required or plan["format"] not in {
            "current-production-resource-build-v1", "current-production-resource-build-v2-diagnostic-v1"}:
        raise ValueError("Exact production resource build plan required")
    if plan["target"] != {"platform": "windows-amd64", "python_abi": "cp313"}:
        raise ValueError("This indexed producer requires the actual Windows CPython 3.13 target; POSIX is separate")
    if not any(item.get("kind") == "backend" and item["sha256"] == backend_index_sha256
               for item in plan["source_indices"]):
        raise ValueError("Production plan differs from the selected Backend source stage")
    selected, provenance, pins = source_selection(plan["source_indices"])
    if diagnostic != (type(plan["production_drivers"]) is dict and plan["production_drivers"].get("format")
                      == "registered-production-driver-resources-v3-diagnostic-v1"):
        raise ValueError("Diagnostic build plan/catalog formats must agree; v1 stays independent")
    drivers = driver_config(plan["production_drivers"], selected)
    outputs = plan["outputs"]
    if outputs != {"manifest": "ProductionResources.json", "runtime_index": "ProductionRuntimeFileManifest.json",
                   "registration": "RegisteredMediaConfig.json", "provenance": "ProductionBuildProvenance.json"}:
        raise ValueError("Exact production output names required")
    for name in outputs.values():
        relative(name)
        if "/" in name:
            raise ValueError("Production manifest/config must share the installation root")
    if len({name.casefold() for name in outputs.values()}) != 4:
        raise ValueError("Generated output names collide")
    registration_fact, registration = document(plan["registration_template"], 1024 * 1024)
    pins.extend((plan_fact, registration_fact))
    expected = {"format", "engine_source_sha256", "asr_resource_manifest", "asr_resource_manifest_sha256",
                "asr_runtime_manifest_sha256", "ffmpeg", "ffmpeg_sha256", "ffprobe", "ffprobe_sha256",
                "asr_route_id", "autonomous_registration", "production_resource_manifest",
                "production_resource_manifest_sha256", "production_runtime_manifest_sha256", "upstream_profile"}
    if diagnostic:
        expected.add("alignment_registration")
    registration_format = "registered-media-config-v3" if diagnostic else "registered-media-config-v2"
    if set(registration) != expected or registration["format"] != registration_format:
        raise ValueError("Original complete registration template required: " + registration_format)
    if registration["upstream_profile"] != "current-registered-autonomous-upstream-v1":
        raise ValueError("Only the original current autonomous factory is accepted")
    autonomous = registration["autonomous_registration"]
    if (type(autonomous) is not dict or autonomous.get("format") != "registered-autonomous-production-v1"
            or autonomous.get("driver_profile") != "registered-production-drivers-v1"
            or set(autonomous) - {"format", "text_route_id", "narration_route_id", "picture_route_id",
                "edit_route_id", "master_index_route_id", "driver_profile", "rights_declaration", "max_duration_us"}):
        raise ValueError("Original AutonomousRegistration required; no route/rights synthesis")
    for key in ("text_route_id", "narration_route_id", "picture_route_id", "edit_route_id", "master_index_route_id"):
        if type(autonomous.get(key)) is not str or not IDENTIFIER.fullmatch(autonomous[key]):
            raise ValueError("Actual explicit registered route IDs required")
    duration = autonomous.get("max_duration_us", 60000000)
    if type(duration) is not int or not 0 < duration <= 600000000:
        raise ValueError("Original maximum duration bound required")
    declaration = autonomous.get("rights_declaration")
    if (type(declaration) is not dict or declaration.get("format") != "owner-production-rights-v1"
            or set(declaration) != {"format", "declaration_id", "declaring_subject", "project_ids", "expires_at_us", "rights"}):
        raise ValueError("Original finite Owner declaration required; no permission synthesis")
    for key in ("declaration_id", "declaring_subject"):
        if type(declaration[key]) is not str or not IDENTIFIER.fullmatch(declaration[key]):
            raise ValueError("Original declaration identity required")
    projects, rights = declaration["project_ids"], declaration["rights"]
    expiry = declaration["expires_at_us"]
    if (type(projects) is not list or not projects or any(type(name) is not str or not IDENTIFIER.fullmatch(name) for name in projects)
            or len(set(projects)) != len(projects) or type(rights) is not list or not rights
            or (expiry is not None and (type(expiry) is not int or expiry <= 0))):
        raise ValueError("Original distinct finite project/rights scope and expiry required")
    rights_ids = set()
    for right in rights:
        if (type(right) is not dict or right.get("basis") != "user_asserted"
                or type(right.get("rights_id")) is not str or not IDENTIFIER.fullmatch(right["rights_id"])
                or right["rights_id"] in rights_ids):
            raise ValueError("Configuration may preserve assertions, never mint owned/licensed authority")
        rights_ids.add(right["rights_id"])
    if type(registration["asr_route_id"]) is not str or not IDENTIFIER.fullmatch(registration["asr_route_id"]):
        raise ValueError("Actual ASR route ID required")
    resources, groups, roles, resource_names = {}, [], set(), set()
    for group in plan["resource_groups"]:
        role = group["role"]
        if role not in {"piper", "ffmpeg", "engine_runtime", "asr", "support"}:
            raise ValueError("Unknown resource group role")
        roles.add(role)
        root, prefix = physical(group["root"]), relative(group["prefix"])
        index_fact, index = document(group["index"], INDEX_LIMIT)
        pins.append(index_fact)
        rows = index.get("files")
        if type(rows) is not list or not 0 < len(rows) <= FILE_LIMIT:
            raise ValueError("Nonempty whole resource membership required")
        source_members, names = members(root), set()
        licenses = group["license_files"]
        if type(licenses) is not list or not licenses:
            raise ValueError("Original resource licence documents must be retained")
        for row in rows:
            name = relative(row["relative_path"])
            if name in names or name not in source_members:
                raise ValueError("Duplicate/missing resource index member: " + name)
            names.add(name)
            fact, _ = checked({"path": str(source_members[name]), "bytes": row["bytes"], "sha256": row["sha256"]})
            pins.append(fact)
            destination = relative(prefix + "/" + name)
            if destination.casefold() in resource_names or destination.casefold() in {key.casefold() for key in selected}:
                raise ValueError("Duplicate resource destination: " + destination)
            resource_names.add(destination.casefold())
            resources[destination] = {**fact, "relative_path": destination}
        # Index may be physically inside the root: retain and index its bytes too.
        if Path(index_fact["path"]).is_relative_to(root):
            name = relative(Path(index_fact["path"]).relative_to(root).as_posix())
            names.add(name)
            destination = relative(prefix + "/" + name)
            if destination.casefold() in resource_names:
                raise ValueError("Resource index cannot index its own digest")
            resource_names.add(destination.casefold())
            resources[destination] = {**index_fact, "relative_path": destination}
        if names != set(source_members):
            raise ValueError("Resource index does not cover whole physical group: " + role)
        for name in licenses:
            if relative(name) not in names or resources[prefix + "/" + name]["bytes"] == 0:
                raise ValueError("Missing or empty original licence document")
        metadata_files = group["metadata_files"]
        if type(metadata_files) is not list or (role in {"piper", "engine_runtime", "asr"} and not metadata_files):
            raise ValueError("Actual Python distribution metadata closure is required")
        distributions = []
        for name in metadata_files:
            name = relative(name)
            if name not in names or not name.endswith(".dist-info/METADATA"):
                raise ValueError("Missing exact installed METADATA member")
            _, body = checked(resources[prefix + "/" + name], MANIFEST_LIMIT)
            metadata = email.parser.BytesParser().parsebytes(bytes(body))
            if not metadata["Name"] or not metadata["Version"]:
                raise ValueError("Distribution metadata lacks exact name/version")
            distributions.append({"name": metadata["Name"], "version": metadata["Version"],
                                  "requires_dist": metadata.get_all("Requires-Dist", []),
                                  "metadata": prefix + "/" + name})
        actual_metadata = {name for name in names if name.endswith(".dist-info/METADATA")}
        if set(metadata_files) != actual_metadata:
            raise ValueError("Distribution metadata inventory is incomplete")
        if role == "piper":
            piper = [item for item in distributions if item["name"].lower().replace("_", "-") == "piper-tts"]
            if len(piper) != 1 or piper[0]["version"] != drivers["narration"]["version"]:
                raise ValueError("Actual Piper METADATA version differs from driver configuration")
            python_prefix = relative(group["python_prefix"])
            if drivers["narration"]["python"] != prefix + "/" + python_prefix + "/python.exe":
                raise ValueError("Piper interpreter must be inside its own complete runtime group")
        else:
            python_prefix = None
        groups.append({"role": role, "root": str(root), "prefix": prefix, "index": index_fact,
                       "files": sorted(names), "license_files": licenses,
                       "distributions": distributions, "python_prefix": python_prefix})
    if not {"piper", "ffmpeg", "engine_runtime", "asr"} <= roles:
        raise ValueError("Whole Piper/FFmpeg/Engine/ASR runtime groups are required")
    piper_groups = [group for group in groups if group["role"] == "piper"]
    if len(piper_groups) != 1 or drivers["narration"]["license_document"] not in {
            piper_groups[0]["prefix"] + "/" + name for name in piper_groups[0]["license_files"]}:
        raise ValueError("Piper model licence must be an original indexed group licence document")
    if len(resources) + len(selected) > FILE_LIMIT:
        raise ValueError("Total production resource count exceeds 100000")
    prepared = {"plan": plan, "plan_fact": plan_fact, "sources": selected, "source_provenance": provenance,
                "resources": resources, "groups": groups, "pins": pins, "drivers": drivers,
                "registration": registration, "target": plan["target"]}
    if diagnostic:
        prepared["catalog_provenance"] = diagnostic_decoder().validate_bindings(
            drivers, plan["catalog_bindings"], registration, selected, resources, groups,
            checked, document, relative)
    return prepared


def recheck(prepared):
    for ref in prepared["pins"]:
        checked(ref)
    for group in prepared["groups"]:
        if set(members(group["root"])) != set(group["files"]):
            raise ValueError("Resource membership changed after preflight")
    for item in prepared.get("catalog_provenance", {}).get("members", ()):
        checked(item)


def overlay(root, prepared):
    for item in (*prepared["sources"].values(), *prepared["resources"].values()):
        destination = root / item["relative_path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and item["relative_path"] in prepared["resources"]:
            actual, _ = identity(destination)
            if any(actual[key] != item[key] for key in ("bytes", "sha256")):
                raise ValueError("Resource overlay would change an existing payload member")
        shutil.copyfile(item["path"], destination)
        actual, _ = identity(destination)
        if any(actual[key] != item[key] for key in ("bytes", "sha256")):
            raise ValueError("Copied resource/source identity differs")
    recheck(prepared)


def build(root, prepared):
    """Generate metadata in the sole new indexed stage, before LoadPolicy seals."""
    root = physical(root)
    outputs = prepared["plan"]["outputs"]
    for name in outputs.values():
        if (root / name).exists():
            raise ValueError("Fresh generated production outputs required")
    files = members(root)
    engine = {name: path for name, path in files.items()
              if name.startswith("Code/video_creator/") and name.endswith(".py")}
    selected = {name: item for name, item in prepared["sources"].items()
                if name.startswith("Code/video_creator/") and name.endswith(".py")}
    if not engine or set(engine) != set(selected):
        raise ValueError("Complete immutable Engine/Media code map required; base or twelve-copy subset is insufficient")
    for name, item in selected.items():
        actual, _ = identity(engine[name])
        if any(actual[key] != item[key] for key in ("bytes", "sha256")):
            raise ValueError("Selected source differs from installed code: " + name)
    for item in prepared.get("catalog_provenance", {}).get("members", ()):
        name = item["relative_path"]
        if name not in files:
            raise ValueError("Catalog member missing from physical stage: " + name)
        actual, _ = identity(files[name])
        if any(actual[key] != item[key] for key in ("bytes", "sha256")):
            raise ValueError("Catalog member differs in physical stage: " + name)
    drivers = prepared["drivers"]
    for name in [drivers["narration"][key] for key in ("python", "worker", "model", "model_config", "license_document")] + [drivers["edit"][key] for key in ("ffmpeg", "ffprobe")]:
        if name not in files:
            raise ValueError("Required production driver resource missing: " + name)
    worker, _ = identity(files[drivers["narration"]["worker"]])
    current = selected["Code/video_creator/media/piper_worker.py"]
    if any(worker[key] != current[key] for key in ("bytes", "sha256")):
        raise ValueError("Piper worker is not the current selected implementation")
    asr_name = relative(prepared["plan"]["asr_manifest"])
    if asr_name not in files:
        raise ValueError("Original ASR manifest unavailable")
    asr_fact, _ = identity(files[asr_name], MANIFEST_LIMIT)
    _, asr = document(asr_fact, MANIFEST_LIMIT)
    asr_index = relative((PurePosixPath(asr_name).parent / relative(asr["runtime_manifest"])).as_posix())
    if asr_index not in files:
        raise ValueError("Original ASR runtime index unavailable")
    asr_index_fact, _ = identity(files[asr_index], INDEX_LIMIT)
    rows = []
    for name, path in sorted(files.items()):
        fact, _ = identity(path)
        rows.append({"relative_path": name, "bytes": fact["bytes"], "sha256": fact["sha256"]})
    if not 0 < len(rows) <= FILE_LIMIT:
        raise ValueError("Invalid complete production index count")
    generated = {}

    def put(key, body, limit):
        encoded = (json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
        if len(encoded) > limit:
            raise ValueError("Generated production metadata exceeds exact bound: " + key)
        path = root / outputs[key]
        with path.open("xb") as stream:
            stream.write(encoded)
        generated[key] = {"relative_path": outputs[key], "bytes": len(encoded), "sha256": hashlib.sha256(encoded).hexdigest()}

    put("runtime_index", {"format": "current-production-runtime-index-v1", "files": rows}, INDEX_LIMIT)
    put("manifest", {"runtime_manifest": outputs["runtime_index"], "production_drivers": drivers}, MANIFEST_LIMIT)
    registration = dict(prepared["registration"])
    registration.update(engine_source_sha256={name.removeprefix("Code/video_creator/"): item["sha256"] for name, item in sorted(selected.items())},
                        asr_resource_manifest=asr_name, asr_resource_manifest_sha256=asr_fact["sha256"],
                        asr_runtime_manifest_sha256=asr_index_fact["sha256"],
                        production_resource_manifest=outputs["manifest"],
                        production_resource_manifest_sha256=generated["manifest"]["sha256"],
                        production_runtime_manifest_sha256=generated["runtime_index"]["sha256"])
    for key in ("ffmpeg", "ffprobe"):
        registration[key] = drivers["edit"][key]
        fact, _ = identity(files[registration[key]])
        registration[key + "_sha256"] = fact["sha256"]
    put("registration", registration, 1024 * 1024)
    provenance = {"format": "current-production-build-provenance-v1", "input_plan": prepared["plan_fact"],
                  "source_selection": prepared["source_provenance"], "resource_groups": prepared["groups"],
                  "outputs": generated.copy(), "target": prepared["target"],
                  "execution_qualification": "not_admitted", "distribution_clearance": "not_admitted",
                  "backend_source_state": "explicit immutable input; current blocker source must be selected before release",
                  "route_rights": "Backend current admission; config is not entitlement"}
    if "catalog_provenance" in prepared:
        provenance["catalog"] = prepared["catalog_provenance"]
    put("provenance", provenance, INDEX_LIMIT)
    recheck(prepared)
    return generated


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-plan", type=Path, required=True)
    parser.add_argument("--input-plan-sha256", required=True)
    parser.add_argument("--backend-index-sha256", required=True)
    args = parser.parse_args()
    prepared = prepare(args.input_plan, args.input_plan_sha256, args.backend_index_sha256)
    recheck(prepared)
    print(json.dumps({"status": "DATA_INPUTS_VALIDATED_NOT_QUALIFIED", "sources": len(prepared["sources"]),
                      "resources": len(prepared["resources"]), "input_pins": len(prepared["pins"])}))


if __name__ == "__main__":
    main()
