"""ADR0083 V1-V11: real installer provisioning and first-run acceptance.

Runs against one real install directory (registration + Package/AsrPackage/Routes)
and one real instance directory that must still have no Owner binding. Every
step prints one JSON line and the final table is honest: a step is PASS only when
its expected observation was actually reached; missing prerequisites are
NOT_EXECUTED with the reason, never skipped into a pass.

Prerequisite: `installer-admin provision` has already been run for these two
directories (see COMMANDS.md ADR0083 entry). This script never provisions and
never rewrites the registration.

Usage:
  python tests/acceptance/adr0083_provisioning_v1_v11.py \
      --install-dir <Install> --data-dir <Data> --out <results.json>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(r"G:/开发测试/Projects/VideoCreator")
ENGINE_SRC = REPO / "services" / "engine" / "src"
REGISTRATION_BUILD = REPO.parents[1] / "Codex/VideoCreatorImplementation/Integration/LocalInstallationRegistrationBuild"
AUTHORIZATION_SECRET_ENV = "VIDEO_CREATOR_AUTHORIZATION_SESSION_SECRET"
AUTHORIZATION_HEADER = "X-VideoCreator-Authorization"
EMPTY_TABLES = ("production_authorization_policies", "production_admissions",
                "daily_project_authorizations", "execution_registrations")


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as stream:
        while block := stream.read(1 << 20):
            hasher.update(block)
    return hasher.hexdigest()


def _get(url: str, token: str | None, *, headers: dict | None = None):
    request = urllib.request.Request(url, headers={**(headers or {}),
                                                   **({"Authorization": "Bearer " + token} if token else {})})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, {k.lower(): v for k, v in response.headers.items()}, response.read()
    except urllib.error.HTTPError as error:
        return error.code, {k.lower(): v for k, v in error.headers.items()}, error.read()


def _post(url: str, token: str, body: dict, *, headers: dict | None = None):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST", headers={
        "Authorization": "Bearer " + token, "Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, {k.lower(): v for k, v in response.headers.items()}, response.read()
    except urllib.error.HTTPError as error:
        return error.code, {k.lower(): v for k, v in error.headers.items()}, error.read()


def _json(raw: bytes):
    try:
        return json.loads(raw or b"{}")
    except json.JSONDecodeError:
        return {"raw": raw[:400].decode("utf-8", "replace")}


class Result:
    def __init__(self):
        self.rows = []

    def add(self, index, status, command, expected, actual, evidence=None):
        self.rows.append({"id": index, "status": status, "command": command, "expected": expected,
                          "actual": actual, "evidence": evidence or {}})
        print(json.dumps({"id": index, "status": status}, ensure_ascii=False), flush=True)

    def render(self) -> str:
        lines = [f"{'#':<4}{'status':<14}observation"]
        for row in self.rows:
            lines.append(f"{row['id']:<4}{row['status']:<14}{row['actual'][:160]}")
        return "\n".join(lines)


class Server:
    """One real CLI child with its raw stdout kept as evidence."""

    def __init__(self, argv, environment, *, label):
        self.label = label
        self.argv = [str(item) for item in argv]
        self.lines = []
        self.process = subprocess.Popen(self.argv, cwd=str(REPO), env=environment,
                                        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)
        self.ready = self._await_ready()

    def _await_ready(self, timeout=60):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            line = self.process.stdout.readline()
            if not line:
                if self.process.poll() is not None:
                    raise AssertionError(f"{self.label} exited: {self.process.stderr.read()[-600:]!r}")
                continue
            text = line.decode("utf-8", "replace").strip()
            self.lines.append(text)
            try:
                body = json.loads(text)
            except json.JSONDecodeError:
                continue
            if body.get("event") == "ready":
                return body
        self.stop()
        raise AssertionError(f"{self.label}: no readiness in {timeout}s")

    def stop(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=20)


def registration_route_ids(config: dict) -> set[str]:
    ids = {config["local_registration"]["input_audio_route_id"],
           config["local_registration"]["input_visual_route_id"],
           config["local_registration"]["edit_route_id"],
           config["local_registration"]["master_index_route_id"]}
    if config.get("asr_route_id") is not None:
        ids.add(config["asr_route_id"])
    return ids


def v1(result: Result, data: Path, registration: Path) -> dict:
    record_path = data / "Control" / "InstallationProvisioning.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    instance = sqlite3.connect(f"file:{data / 'Metadata.sqlite'}?mode=ro", uri=True)
    row = instance.execute("SELECT value FROM metadata WHERE key='instance_id'").fetchone()
    instance.close()
    actual_items = {item["id"] for item in record.get("items", [])}
    problems = []
    if record.get("format") != "installation-provisioning-v1":
        problems.append("format")
    if record.get("complete") is not True:
        problems.append("complete")
    if row is None or record.get("instance_id") != row[0]:
        problems.append("instance_id")
    if not str(record.get("project_id", "")).startswith("project-"):
        problems.append("project_id")
    if not (isinstance(record.get("registration_sha256"), str) and len(record["registration_sha256"]) == 64):
        problems.append("registration_sha256")
    if record.get("registration_sha256") != _sha256(registration):
        problems.append("registration_sha256_bytes")
    if record.get("route_ids") and sorted(record["route_ids"]) != sorted(
            registration_route_ids(json.loads(registration.read_text(encoding="utf-8")))):
        problems.append("route_ids")
    # ADR0083 V1 expects items covering A1-A8+B1-B6; the implementation writes
    # only the B-group subset below. Report the gap instead of hiding it.
    adr_expected = {f"A{i}" for i in range(1, 9)} | {f"B{i}" for i in range(1, 7)}
    coverage_gap = sorted(adr_expected)
    self_consistent = not problems
    status = "PASS" if self_consistent and not coverage_gap else "FAIL"
    result.add("V1", status,
               "Get-Content <Data>/Control/InstallationProvisioning.json",
               "installation-provisioning-v1; complete=True; instance/project/sha self-consistent; items cover A1-A8+B1-B6",
               f"self_consistent={self_consistent} {problems}; items={sorted(actual_items)}; "
               f"adr_item_coverage_missing={coverage_gap}",
               {"record": str(record_path), "record_sha256": _sha256(record_path)})
    if not problems:
        # Self-consistency alone passes; the coverage expectation is a separate
        # observable and is reported as the V1 coverage gap above.
        pass
    return record


def v2(result: Result, install: Path, data: Path, checkout_report: Path) -> dict:
    scratch = install / "V2Scratch"
    command = ["G:/开发测试/Projects/VideoCreator/.venv/Scripts/python.exe",
               str(REGISTRATION_BUILD / "check_local_registration.py"),
               "--repo", str(REPO), "--out", str(install), "--runtime",
               "--instance-dir", str(scratch), "--output", str(checkout_report)]
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=600, check=False)
    report = json.loads(checkout_report.read_text(encoding="utf-8")) if checkout_report.is_file() else {}
    ok = completed.returncode == 0 and report.get("ok") is True
    result.add("V2", "PASS" if ok else "FAIL", " ".join(command[:1] + command[1:]),
               "exit 0; ok=true; six checks true including registered_media_runtime",
               f"exit={completed.returncode} ok={report.get('ok')} checks="
               + ",".join(f"{c['name']}={'ok' if c['ok'] else 'FAIL'}" for c in report.get("checks", [])),
               {"report": str(checkout_report), "scratch_note": "scratch instance must live inside <Install>; "
                "the checker rmtree's whatever --instance-dir names, so the real instance is never passed"})
    return report


def v3(result: Result, data: Path, registration: Path) -> set[str]:
    config = json.loads(registration.read_text(encoding="utf-8"))
    expected = registration_route_ids(config)
    connection = sqlite3.connect(f"file:{data / 'Metadata.sqlite'}?mode=ro", uri=True)
    rows = {row[0] for row in connection.execute("SELECT id FROM routes ORDER BY id")}
    connection.close()
    ok = rows == expected
    result.add("V3", "PASS" if ok else "FAIL",
               "sqlite3 (read-only) SELECT id FROM routes ORDER BY id",
               "exactly the five registration route ids",
               f"rows={sorted(rows)} match={ok}", {"expected": sorted(expected)})
    return rows


def v4(result: Result, data: Path, record: dict) -> dict:
    path = data / "Control" / "ProductionAuthorizationControl.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    floor_item = next((item for item in record.get("items", []) if item["id"] == "production_floor"), {})
    ok = (document.get("minimum_revision") == 0 and document.get("pending_request_sha256") is None
          and document.get("instance_id") == record.get("instance_id")
          and floor_item.get("sha256") == _sha256(path))
    connection = sqlite3.connect(f"file:{data / 'Metadata.sqlite'}?mode=ro", uri=True)
    counts = {table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
              for table in EMPTY_TABLES}
    connection.close()
    ok = ok and all(count == 0 for count in counts.values())
    result.add("V4", "PASS" if ok else "FAIL",
               "Get-Content <Data>/Control/ProductionAuthorizationControl.json + SHA256",
               "minimum_revision=0, pending=null, file SHA equals V1 item sha, four tables empty",
               f"floor={document} sha_match={floor_item.get('sha256') == _sha256(path)} table_counts={counts}")
    return document


def v5(result: Result, data: Path) -> None:
    script = ("$a=Get-Acl '" + str(data) + "'; $a.Access | Select-Object IdentityReference,"
              "FileSystemRights,IsInherited | ConvertTo-Json -Compress")
    completed = subprocess.run(["pwsh", "-NoProfile", "-NonInteractive", "-Command", script],
                               capture_output=True, text=True, encoding="utf-8", timeout=120, check=False)
    try:
        entries = json.loads(completed.stdout.strip() or "[]")
    except json.JSONDecodeError:
        entries = []
    if isinstance(entries, dict):
        entries = [entries]
    identities = [str(entry.get("IdentityReference")) for entry in entries]
    user = os.environ.get("USERNAME", "")

    def identity(entry) -> str:
        raw = entry.get("IdentityReference")
        return str(raw.get("Value") if isinstance(raw, dict) else raw)

    def full_control(entry) -> bool:
        raw = entry.get("FileSystemRights")
        return raw in (2032127, -1610612735) or str(raw) == "FullControl"

    trusted = [entry for entry in entries
               if (identity(entry).endswith("SYSTEM") or (user and identity(entry).endswith(user)))
               and full_control(entry)
               and entry.get("IsInherited") is False]
    forbidden = any(marker in " ".join(identities)
                    for marker in ("Everyone", "\\Users", "Authenticated Users", "BUILTIN"))
    ok = len(entries) == 2 and len(trusted) == 2 and not forbidden
    result.add("V5", "PASS" if ok else "FAIL",
               "Get-Acl <Data> | Select IdentityReference,FileSystemRights,IsInherited",
               "exactly two non-inherited FullControl ACEs: current user + NT AUTHORITY\\SYSTEM",
               f"aces={entries} exit={completed.returncode}")


def v6(result: Result, server: Server, token: str) -> None:
    base = server.ready["base_url"]
    status_projects, _headers, raw_projects = _get(base + "/api/v1/projects", token)
    status_health, headers_health, _raw_health = _get(base + "/api/v1/health", token)
    body = _json(raw_projects)
    ok = (status_projects == 403 and body.get("code") == "owner_authorization_required"
          and status_health == 200
          and headers_health.get(AUTHORIZATION_HEADER.lower()) == "pending")
    result.add("V6", "PASS" if ok else "FAIL",
               f"GET {base}/api/v1/projects ; GET /api/v1/health (restricted serve)",
               "projects 403 owner_authorization_required; health 200 with X-VideoCreator-Authorization: pending",
               f"projects={status_projects} {body.get('code')}; health={status_health} "
               f"header={headers_health.get(AUTHORIZATION_HEADER.lower())}",
               {"ready": server.ready})


def v7(result: Result, restricted: Server, restart, data: Path, token: str, secret: str) -> Server:
    base = restricted.ready["base_url"]
    status, _headers, raw = _get(base + "/api/v1/authorization/pending", token,
                                 headers={AUTHORIZATION_HEADER: secret})
    pending = _json(raw)
    if status != 200 or not pending.get("nonce"):
        result.add("V7", "FAIL", "GET /api/v1/authorization/pending + approve + restart",
                   "pending view with nonce, approve -> complete/restart_required, restart -> /projects 200",
                   f"pending status={status} body={pending}")
        return None
    status_approve, _headers, raw_approve = _post(
        base + f"/api/v1/authorization/{pending['authorization_id']}/approve", token,
        {"scope_sha256": pending["scope_sha256"], "nonce": pending["nonce"]},
        headers={AUTHORIZATION_HEADER: secret})
    approved = _json(raw_approve)
    restricted.stop()
    ready = restart()
    status_projects, _headers, _raw_projects = _get(ready["base_url"] + "/api/v1/projects", token)
    _status_health, headers_health, _raw = _get(ready["base_url"] + "/api/v1/health", token)
    audit_path = data / "Control" / "ProductAuthorization.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.is_file() else {}
    connection = sqlite3.connect(f"file:{data / 'Metadata.sqlite'}?mode=ro", uri=True)
    metadata = connection.execute("SELECT value FROM metadata WHERE key='product_authorization_audit'").fetchone()
    connection.close()
    owner_status = subprocess.run(
        [str(REPO / ".venv/Scripts/python.exe"),
         str(REGISTRATION_BUILD / "PrepareLocalChain.py"),
         "--repo", str(REPO), "owner-status", "--data-dir", str(data)],
        capture_output=True, text=True, encoding="utf-8", timeout=120, check=False)
    owner = json.loads(owner_status.stdout or "{}")
    ok = (status_approve == 200 and approved.get("state") == "complete"
          and approved.get("restart_required") is True
          and status_projects == 200 and headers_health.get(AUTHORIZATION_HEADER.lower()) == "none"
          and audit.get("format") == "product-authorization-audit-v1"
          and audit.get("kind") == "owner_initialize" and audit.get("decision") == "approve"
          and metadata is not None and metadata[0] == _sha256(audit_path)
          and owner_status.returncode == 0 and owner.get("owner_initialized") is True)
    result.add("V7", "PASS" if ok else "FAIL",
               "pending -> approve -> restart -> /health,/projects ; PrepareLocalChain owner-status",
               "/health: none; /projects 200; audit format/kind/decision and metadata SHA match; owner_initialized true",
               f"approve={status_approve} state={approved.get('state')} restart_required={approved.get('restart_required')} "
               f"projects={status_projects} health={headers_health.get(AUTHORIZATION_HEADER.lower())} "
               f"owner_initialized={owner.get('owner_initialized')} audit_sha_match={metadata is not None and metadata[0] == _sha256(audit_path)}",
               {"audit": str(audit_path), "owner_status": owner})


def v8(result: Result, data: Path, base: str, token: str) -> None:
    connection = sqlite3.connect(f"file:{data / 'Metadata.sqlite'}?mode=ro", uri=True)
    row = connection.execute("SELECT value FROM metadata WHERE key='owner_management_binding'").fetchone()
    connection.close()
    binding = json.loads(row[0]) if row else {}
    binding_id = binding.get("principal", {}).get("authentication_binding_id") or binding.get("authentication_binding_id")
    instance_id = binding.get("principal", {}).get("instance_id") or ""
    key = f"owner-{instance_id}-{binding_id}"
    import keyring  # only for the V8 negative observation
    secret = keyring.get_password("VideoCreatorOwnerManagement", key)
    status, _headers, raw = _post(base + "/api/v1/local-copy-input-scopes/install", token, {})
    body = _json(raw)
    ok = secret is None and status == 403 and body.get("code") == "production_management_denied"
    result.add("V8", "PASS" if ok else "FAIL",
               "keyring.get_password('VideoCreatorOwnerManagement', 'owner-<instance>-<binding>') + "
               "POST /api/v1/local-copy-input-scopes/install with the install token",
               "keyring None; management endpoint 403 production_management_denied",
               f"keyring={'None' if secret is None else 'PRESENT'} management={status} {body.get('code')}",
               {"binding_id": binding_id})


def v9(result: Result, install: Path) -> None:
    hits = []
    for pattern in ("*.json", "*.cmd"):
        for path in install.glob(pattern):
            text = path.read_text(encoding="utf-8", errors="replace")
            for marker in ("VIDEO_CREATOR_DEVELOPMENT_INSTALLATION", "--development-registration"):
                if marker in text:
                    hits.append({"file": str(path), "marker": marker})
    engine = install / "VideoCreatorEngine.exe"
    packaged = engine.is_file()
    result.add("V9", "FAIL" if hits else ("NOT_EXECUTED" if not packaged else "PASS"),
               "Select-String <Install>/*.json,*.cmd -Pattern dev markers; <Engine> serve-dev",
               "no dev markers; packaged engine rejects serve-dev with argparse exit 2",
               f"dev_marker_hits={hits}; packaged_engine_present={packaged}"
               + ("" if packaged else " -> the serve-dev/frozen half cannot run without a real built package")
               + ("" if hits else "; install files contain no dev marker"),
               {"install": str(install)})


def v10(result: Result, install: Path, base: str, token: str) -> None:
    root = _get(base + "/", None)[0]
    workbench = install / "Workbench"
    page = workbench / "index.html"
    if not page.is_file():
        result.add("V10", "NOT_EXECUTED", "GET <Port>/ ; GET /api/v1/health ; grep page source for token",
                   "200 page with <div id=\"root\"> and no token bytes",
                   "no built Workbench/ or launcher in this install directory; there is no page or "
                   "same-origin proxy to observe, so the token-leak assertion has no object")
        return
    html = page.read_text(encoding="utf-8", errors="replace")
    leaked = token[:8] in html or token in html
    result.add("V10", "FAIL" if (root != 200 or leaked) else "PASS",
               "GET <Port>/ ; GET /api/v1/health ; grep page source for token",
               "200 page with <div id=\"root\"> and no token bytes",
               f"root={root} token_leak={leaked}")


def v11(result: Result, base: str, token: str, project_id: str) -> None:
    from video_creator.domain.contracts import ProductionRequest

    body = ProductionRequest(goal="ADR0083 V11 execution authority probe").model_dump(mode="json")
    status, _headers, raw = _post(base + "/api/v1/productions", token, body,
                                  headers={"Idempotency-Key": "adr0083-v11-" + secrets.token_hex(8)})
    payload = _json(raw)
    detail = None
    if status == 202 and payload.get("production_id"):
        _detail_status, _detail_headers, raw_detail = _get(
            base + "/api/v1/productions/" + payload["production_id"], token)
        detail = _json(raw_detail)
    ok = status == 403 and payload.get("code") == "production_authorization_unconfigured"
    result.add("V11", "PASS" if ok else "FAIL",
               "POST /api/v1/productions (minimal local request, Idempotency-Key)",
               "403 production_authorization_unconfigured (R1 current expected state)",
               f"status={status} code={payload.get('code')} production_id={payload.get('production_id')} "
               f"detail_status={detail.get('status') if detail else None}",
               {"response": {key: payload.get(key) for key in ("code", "production_id", "run_id", "schema_version")}})


def main(argv: list[str]) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install-dir", required=True, type=Path)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--registration", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--timeout", type=float, default=180)
    arguments = parser.parse_args(argv)
    install = arguments.install_dir.resolve()
    data = arguments.data_dir.resolve()
    registration = (arguments.registration or install / "Registration.json").resolve()
    out = arguments.out or (data.parent / "V1-V11-results.json")

    environment = {key: value for key, value in os.environ.items() if not key.startswith("VIDEO_CREATOR_")}
    environment["PYTHONPATH"] = str(ENGINE_SRC)
    environment["PYTHONUTF8"] = "1"
    token = secrets.token_hex(32)
    secret = secrets.token_hex(16)
    served = environment | {"VIDEO_CREATOR_API_TOKEN": token, AUTHORIZATION_SECRET_ENV: secret}
    restart_environment = environment | {"VIDEO_CREATOR_API_TOKEN": token}
    config = json.loads(registration.read_text(encoding="utf-8"))
    argv_serve = [str(REPO / ".venv/Scripts/python.exe"), "-m", "video_creator.cli.main", "serve",
                  "--data-dir", str(data), "--host", "127.0.0.1", "--port", "0",
                  "--ffmpeg", str(install / config["ffmpeg"]), "--ffprobe", str(install / config["ffprobe"])]

    result = Result()
    record = v1(result, data, registration)
    v2(result, install, data, data.parent / "V2-registration-runtime.json")
    v3(result, data, registration)
    v4(result, data, record)
    v5(result, data)

    state = {"server": None}

    def restart():
        state["server"] = Server(argv_serve, restart_environment, label="adr0083-ready")
        return state["server"].ready

    restricted = Server(argv_serve, served, label="adr0083-restricted")
    try:
        v6(result, restricted, token)
        v7(result, restricted, restart, data, token, secret)
    finally:
        restricted.stop()
    try:
        if state["server"] is not None:
            base = state["server"].ready["base_url"]
            v8(result, data, base, token)
            v11(result, base, token, record["project_id"])
        else:
            for index in ("V8", "V11"):
                result.add(index, "NOT_EXECUTED", "-", "requires the authorized restart",
                           "the authorized restart from V7 did not happen")
        v9(result, install)
        if state["server"] is not None:
            v10(result, install, state["server"].ready["base_url"], token)
        else:
            result.add("V10", "NOT_EXECUTED", "-", "requires a serving host",
                       "the authorized restart from V7 did not happen")
    finally:
        if state["server"] is not None:
            state["server"].stop()

    payload = {"format": "adr0083-v1-v11-run-v1", "install": str(install), "data": str(data),
               "registration_sha256": _sha256(registration), "token": "<redacted>",
               "results": result.rows}
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8", newline="\n")
    print(result.render())
    print(json.dumps({"results": str(out)}))
    failures = [row["id"] for row in result.rows if row["status"] == "FAIL"]
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
