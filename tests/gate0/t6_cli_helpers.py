"""Owned loopback child observations; no real credentials, external calls or signals-as-success."""

import ctypes
import hashlib
import json
import os
import queue
import secrets
import socket
import subprocess
import sys
import threading
import time
from ctypes import wintypes
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
TOKEN = "synthetic-t6-local-session-" + "x" * 40
MARKER = b'{"event":"api_stopped","scope":"api"}'

# The `serve` ready descriptor is an additive contract: these fields must always
# exist, but a new documented field must not fail every T6 mechanism test. ADR0081
# added `authorization_state` to the restricted shape only, so the old exact-set
# equality turned a product addition into 27 unrelated failures.
READY_REQUIRED = ("event", "base_url", "instance_id")
READY_OPTIONAL_DOMAINS = {"authorization_state": {"pending", "complete", "none"}}


def assert_ready_descriptor(body):
    """Required fields present with their documented values; optional ones typed."""
    assert isinstance(body, dict), body
    missing = [name for name in READY_REQUIRED if name not in body]
    assert not missing, f"ready descriptor is missing {missing}: {body}"
    assert body["event"] == "ready", body
    assert isinstance(body["base_url"], str) and body["base_url"].startswith("http://127.0.0.1:"), body
    assert isinstance(body["instance_id"], str) and body["instance_id"], body
    for name, allowed in READY_OPTIONAL_DOMAINS.items():
        if name in body:
            assert body[name] in allowed, f"ready {name} left its domain {sorted(allowed)}: {body}"
    if "principal_id" in body:
        assert isinstance(body["principal_id"], str) and body["principal_id"], body


AUTHORIZATION_SECRET_ENV = "VIDEO_CREATOR_AUTHORIZATION_SESSION_SECRET"
AUTHORIZATION_HEADER = "X-VideoCreator-Authorization"
SERVE_BASE = ["-m", "video_creator.cli.main", "serve", "--host", "127.0.0.1", "--port", "0"]


def serve_environment(token=TOKEN):
    """The clean child environment; inherited secrets never leak into a T6 child."""
    environment = {k: v for k, v in os.environ.items()
                   if not k.startswith("VIDEO_CREATOR_SECRET_") and k != "VIDEO_CREATOR_API_TOKEN"}
    environment.update(PYTHONPATH=str(ROOT / "services/engine/src"), PYTHONUTF8="1",
                       OTEL_SDK_DISABLED="true", CREWAI_TRACING_ENABLED="false")
    if token is not None:
        environment["VIDEO_CREATOR_API_TOKEN"] = token
    return environment


def start_ready(argv, environment, *, label="t6-ready", timeout=25.0):
    """Start one CLI child and wait for its actual `ready` descriptor."""
    process = subprocess.Popen(argv, cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    lines = queue.Queue()

    def pump(stream, name):
        for line in iter(stream.readline, b""):
            lines.put((name, line))

    for stream, name in ((process.stdout, "stdout"), (process.stderr, "stderr")):
        threading.Thread(target=pump, args=(stream, name), daemon=True).start()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            name, line = lines.get(timeout=0.2)
        except queue.Empty:
            if process.poll() is not None:
                raise AssertionError(f"{label}: child exited before readiness")
            continue
        if name != "stdout":
            continue
        try:
            body = json.loads(line)
        except json.JSONDecodeError:
            continue
        if body.get("event") == "ready":
            return process, body
    process.kill()
    raise AssertionError(f"{label}: no real readiness within {timeout}s")


def stop_process(process, timeout=15.0):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=timeout)
    for stream in (process.stdout, process.stderr):
        if stream is not None and not stream.closed:
            stream.close()


def ensure_owned_project(data_dir):
    """The first Owner project must exist before the consent request (product rule)."""
    from video_creator.application.engine import EngineService
    from video_creator.domain.contracts import ProjectInput

    engine = EngineService(data_dir)
    with engine.db.connect_readonly() as connection:
        row = connection.execute("SELECT 1 FROM projects WHERE owner=?", ("local-user",)).fetchone()
    if row is None:
        engine.create_project("local-user", ProjectInput(name="T6 local instance"))


def authorize_instance(data_dir, *, timeout=25.0):
    """ADR0081: give this instance a real Owner through the product consent channel.

    A `serve` without an Owner binding only answers `/health` and
    `/api/v1/authorization/*`; every T6 case that uses a product route therefore
    needs an authorized instance before its measured child starts. The consent
    surface never unlocks its own process: approval writes the binding and reports
    `restart_required`, so this runs a short-lived restricted process and the
    caller then starts the measured child on the same directory.

    On an already authorized instance the restricted channel is absent and this
    is a no-op that only observes the ready descriptor.
    """
    environment = serve_environment()
    secret = secrets.token_hex(16)
    environment[AUTHORIZATION_SECRET_ENV] = secret
    ensure_owned_project(data_dir)
    argv = [sys.executable, *SERVE_BASE, "--data-dir", str(data_dir)]
    process, ready = start_ready(argv, environment, label="t6-authorize", timeout=timeout)
    try:
        if "authorization_state" not in ready:
            return {"restricted_ready": ready, "approved": None}
        assert ready["authorization_state"] == "pending", ready
        with httpx.Client(base_url=ready["base_url"],
                          headers={"Authorization": "Bearer " + TOKEN, AUTHORIZATION_HEADER: secret},
                          trust_env=False, timeout=10) as api:
            pending = api.get("/api/v1/authorization/pending")
            assert pending.status_code == 200, pending.text
            request = pending.json()
            assert request["nonce"] and request["state"] == "pending", request
            approved = api.post(f"/api/v1/authorization/{request['authorization_id']}/approve",
                                json={"scope_sha256": request["scope_sha256"], "nonce": request["nonce"]})
            assert approved.status_code == 200, approved.text
            body = approved.json()
            assert body["state"] == "complete" and body["restart_required"] is True, body
            return {"restricted_ready": ready, "approved": body}
    finally:
        stop_process(process)




def descendants(root_pid):
    """Observe PID ancestry on this measured Windows host; disclose only our descendants."""
    if os.name != "nt":
        raise RuntimeError("This process observer has not been implemented/measured on other OSes")

    class Entry(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("usage", wintypes.DWORD), ("pid", wintypes.DWORD),
                    ("heap", ctypes.c_size_t), ("module", wintypes.DWORD), ("threads", wintypes.DWORD),
                    ("parent", wintypes.DWORD), ("priority", wintypes.LONG), ("flags", wintypes.DWORD),
                    ("exe", wintypes.WCHAR * 260)]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(Entry)]
    kernel.Process32FirstW.restype = wintypes.BOOL
    kernel.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(Entry)]
    kernel.Process32NextW.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.CreateToolhelp32Snapshot(2, 0)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    parents, entry = {}, Entry()
    entry.size = ctypes.sizeof(entry)
    try:
        valid = kernel.Process32FirstW(handle, ctypes.byref(entry))
        while valid:
            parents[entry.pid] = entry.parent
            valid = kernel.Process32NextW(handle, ctypes.byref(entry))
    finally:
        kernel.CloseHandle(handle)
    found = {root_pid}
    while True:
        expanded = found | {pid for pid, parent in parents.items() if parent in found}
        if found == expanded:
            return sorted(found - {root_pid})
        found = expanded


def port_closed(url):
    address = httpx.URL(url)
    with socket.socket() as client:
        client.settimeout(0.3)
        return client.connect_ex((address.host, address.port)) != 0


class Child:
    def __init__(self, directory, *, controlled=True, mode=None, tools=None, token=True, early=None,
                 authorize=False):
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)
        self.data_dir = directory / "Instance"
        environment = serve_environment(TOKEN if token else None)
        # ADR0081: a production-ready instance needs a real Owner binding; the
        # consent channel is driven over HTTP before the measured child starts.
        self.authorization = authorize_instance(self.data_dir) if authorize else None
        args = [sys.executable]
        args += [str(ROOT / "tests/gate0/t6_fault_host.py"), mode, str(directory / "HostReceipt.json")] if mode else ["-m", "video_creator.cli.main"]
        args += ["serve", "--data-dir", str(self.data_dir), "--host", "127.0.0.1", "--port", "0"]
        if controlled:
            args.append("--control-stdin")
        if tools:
            args += ["--ffmpeg", str(tools[0]), "--ffprobe", str(tools[1])]
        self.command, self.lines = args, queue.Queue()
        self.stdout, self.stderr, self.forced = bytearray(), bytearray(), False
        self.process = subprocess.Popen(args, cwd=ROOT, env=environment, stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.observed_descendants = []
        self.threads = []
        for stream, target, label in [(self.process.stdout, self.stdout, "stdout"), (self.process.stderr, self.stderr, "stderr")]:
            def collect(source=stream, output=target, name=label):
                for line in iter(source.readline, b""):
                    output.extend(line)
                    self.lines.put((name, line))
            thread = threading.Thread(target=collect, name="t6-" + label)
            thread.start()
            self.threads.append(thread)
        self.ready = None
        if early is not None:
            self.send(early)

    def await_ready(self):
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            try:
                name, line = self.lines.get(timeout=0.2)
            except queue.Empty:
                if self.process.poll() is not None:
                    raise AssertionError("Child exited before readiness: " + self.stderr.decode(errors="replace"))
                continue
            if name == "stdout":
                body = json.loads(line)
                if body.get("event") == "ready":
                    assert_ready_descriptor(body)
                    self.ready = body
                    self.observed_descendants.extend(descendants(self.process.pid))
                    return body
        raise AssertionError("No real API readiness within deadline")

    def api(self):
        return httpx.Client(base_url=self.ready["base_url"], headers={"Authorization": "Bearer " + TOKEN},
                            trust_env=False, timeout=8)

    def send(self, data):
        self.process.stdin.write(data)
        self.process.stdin.flush()

    def stopped(self):
        self.observed_descendants.extend(descendants(self.process.pid))
        code = self.process.wait(timeout=15)
        self.finish_readers()
        assert code == 0, self.stderr.decode(errors="replace")
        assert self.stderr.splitlines().count(MARKER) == 1
        assert port_closed(self.ready["base_url"])
        self.await_no_descendants()
        assert TOKEN.encode() not in self.stdout + self.stderr
        return code

    def finish_readers(self):
        for thread in self.threads:
            thread.join(timeout=3)
            assert not thread.is_alive(), "Test collector must observe actual OS pipe EOF"

    def await_no_descendants(self):
        deadline = time.monotonic() + 3
        remaining = descendants(self.process.pid)
        while remaining and time.monotonic() < deadline:
            time.sleep(0.05)
            remaining = descendants(self.process.pid)
        assert not remaining, f"Owned child PIDs must really exit: {remaining}"

    def close(self):
        if self.process.poll() is None:
            self.forced = True
            self.process.terminate()
            self.process.wait(timeout=15)
        self.finish_readers()
        self.await_no_descendants()
        for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
            stream.close()
        receipt = {"command": self.command, "pid": self.process.pid, "ready": self.ready,
                   "exit_code": self.process.returncode, "forced_cleanup": self.forced,
                   "marker_count": self.stderr.splitlines().count(MARKER),
                   "port_closed": port_closed(self.ready["base_url"]) if self.ready else None,
                   "observed_descendants": sorted(set(self.observed_descendants)),
                   "remaining_descendants": descendants(self.process.pid),
                   "collector_threads_joined": all(not t.is_alive() for t in self.threads),
                   "provider_calls": 0, "real_key_reads": 0, "scope": "Actual owned Windows child and loopback HTTP; not worker lifecycle or production creation"}
        (self.directory / "ChildReceipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8", newline="\n")
        (self.directory / "ChildStdout.txt").write_bytes(self.stdout)
        (self.directory / "ChildStderr.txt").write_bytes(self.stderr)


def write_receipt(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def sha(data):
    return hashlib.sha256(data).hexdigest()
