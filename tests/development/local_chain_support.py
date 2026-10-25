"""Shared helpers for the real local installation chain tests (development only).

The tests never import product modules into the pytest process for the observed
behaviour: every refusal and every server is a real child process, and its raw
stdout/stderr bytes plus argv and exit code are written under the evidence
directory. Product imports happen only inside `tools/testing/local_chain_probes.py`
child processes.

Paths default to this suite's own current-checkout registration fixture and a
copy of a clean instance (`tools/testing/local_chain_fixture.py`); the integration
hand-off directory is read only to byte-copy its builder. Override with:

    VIDEO_CREATOR_LOCAL_FIXTURE        registration fixture root (Registration.json + Package)
    VIDEO_CREATOR_LOCAL_INSTALLATION   alternative registration slice root
    VIDEO_CREATOR_LOCAL_INSTANCE       chain instance data dir
    VIDEO_CREATOR_LOCAL_CHAIN_EVIDENCE evidence root (raw logs live here)
    VIDEO_CREATOR_PYTHON               interpreter used for product entry points
    VIDEO_CREATOR_VERIFY_ASSEMBLY      absolute path to VerifyPersistedAssembly.py
"""

from __future__ import annotations

import hashlib
import json
import os
import queue
import secrets
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINE_SRC = REPO_ROOT / 'services' / 'engine' / 'src'
PROBES = REPO_ROOT / 'tools' / 'testing' / 'local_chain_probes.py'
FIXTURE_TOOL = REPO_ROOT / 'tools' / 'testing' / 'local_chain_fixture.py'

DEFAULT_PYTHON = REPO_ROOT / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
PYTHON = Path(os.environ.get('VIDEO_CREATOR_PYTHON') or DEFAULT_PYTHON)

DEFAULT_FIXTURE = Path(os.environ.get('VIDEO_CREATOR_LOCAL_FIXTURE')
                       or r'G:/开发测试/Codex/VideoCreatorImplementation/Test/LocalChainEndToEnd/Fixture')
DEFAULT_EVIDENCE = Path(os.environ.get('VIDEO_CREATOR_LOCAL_CHAIN_EVIDENCE')
                        or r'G:/开发测试/Codex/VideoCreatorImplementation/Test/LocalChainEndToEnd/Evidence')

VERIFY_ASSEMBLY = Path(os.environ.get('VIDEO_CREATOR_VERIFY_ASSEMBLY')
                       or r'G:/开发测试/Codex/VideoCreatorImplementation/AgentMedia/LocalAssemblyClosure/VerifyPersistedAssembly.py')

DEV_ENVIRONMENT = 'VIDEO_CREATOR_DEVELOPMENT_INSTALLATION'
BASE_EXECUTION_SOURCE = 'tests/development'

_OVERRIDES: dict[str, Path] = {}


def configure(**values) -> None:
    """Point the helpers at this session's real registration slice and instance.

    The suite builds its own current registration fixture (see
    `tools/testing/local_chain_fixture.py`) and uses copies of a clean instance,
    so the integration hand-off directory and its instance are never written.
    """
    for name in ('installation', 'instance', 'evidence_root', 'fixture'):
        value = values.get(name)
        if value is not None:
            _OVERRIDES[name] = Path(value)


def installation() -> Path:
    if 'installation' in _OVERRIDES:
        return _OVERRIDES['installation']
    override = os.environ.get('VIDEO_CREATOR_LOCAL_INSTALLATION')
    return Path(override) if override else DEFAULT_FIXTURE


def instance() -> Path:
    if 'instance' in _OVERRIDES:
        return _OVERRIDES['instance']
    override = os.environ.get('VIDEO_CREATOR_LOCAL_INSTANCE')
    return Path(override) if override else installation() / 'Instances' / 'Primary'


def registration() -> Path:
    return installation() / 'Registration.json'


def package() -> Path:
    return installation() / 'Package'


def ffmpeg_binary() -> Path:
    return package() / 'Media' / 'FFmpeg' / 'bin' / 'ffmpeg.exe'


def ffprobe_binary() -> Path:
    return package() / 'Media' / 'FFmpeg' / 'bin' / 'ffprobe.exe'


def routes() -> Path:
    return installation() / 'Routes'


def evidence_root() -> Path:
    override = os.environ.get('VIDEO_CREATOR_LOCAL_CHAIN_EVIDENCE')
    return (_OVERRIDES.get('evidence_root') or (Path(override) if override else DEFAULT_EVIDENCE))


_DYNAMIC = {
    'INSTALLATION': installation,
    'INSTANCE': instance,
    'REGISTRATION': registration,
    'ROUTES': routes,
    'PACKAGE': package,
    'FFMPEG': ffmpeg_binary,
    'FFPROBE': ffprobe_binary,
    'EVIDENCE_ROOT': evidence_root,
}


def __getattr__(name):
    """Backwards-compatible module attributes resolved at access time."""
    resolver = _DYNAMIC.get(name)
    if resolver is None:
        raise AttributeError(name)
    return resolver()


# --------------------------------------------------------------------------- first principles

def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec='milliseconds')


def expires_at(days: int = 5, offset_minutes: int = 0) -> str:
    moment = datetime.now(UTC) + timedelta(days=days, minutes=offset_minutes)
    return moment.strftime('%Y-%m-%dT%H:%M:%SZ')


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with open(path, 'rb') as stream:
        while block := stream.read(1024 * 1024):
            hasher.update(block)
    return hasher.hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + '\n',
                    encoding='utf-8', newline='\n')


def registration_payload() -> dict:
    return read_json(registration())


def registration_sha256() -> str:
    return sha256_file(registration())


def route_ids() -> list[str]:
    payload = registration_payload()['local_registration']
    return [payload['input_audio_route_id'], payload['input_visual_route_id'],
            payload['edit_route_id'], payload['master_index_route_id']]


def project_id() -> str:
    declared = registration_payload()['local_registration']['rights_declaration']['project_ids']
    if not declared:
        raise AssertionError('registration names no project id in its rights declaration')
    return declared[0]


def new_token() -> str:
    return secrets.token_hex(32)


def base_environment(extra: dict[str, str] | None = None) -> dict[str, str]:
    """A clean child environment: inherited values never enable or mask dev mode."""
    environment = {key: value for key, value in os.environ.items()
                   if key not in {DEV_ENVIRONMENT, 'VIDEO_CREATOR_API_TOKEN', 'VIDEO_CREATOR_MCP_TOKEN'}}
    environment['PYTHONPATH'] = str(ENGINE_SRC)
    environment['PYTHONUTF8'] = '1'
    environment['PYTHONIOENCODING'] = 'utf-8'
    environment.pop('PYTHONHOME', None)
    if extra:
        environment.update({key: value for key, value in extra.items() if value is not None})
    return environment


def environment_record(environment: dict[str, str], secret_keys=()) -> dict[str, str]:
    interesting = {DEV_ENVIRONMENT, 'PYTHONPATH', 'PYTHONUTF8', 'VIDEO_CREATOR_API_TOKEN'}
    record = {}
    for key in sorted(interesting):
        if key not in environment:
            record[key] = '<unset>'
        elif any(secret in key for secret in secret_keys) or 'TOKEN' in key:
            record[key] = f'<redacted len={len(environment[key])}>'
        else:
            record[key] = environment[key]
    return record


# --------------------------------------------------------------------------- process evidence

@dataclass(frozen=True)
class ProbeResult:
    """One finished child process with its preserved raw bytes."""
    name: str
    argv: list[str]
    cwd: str
    exit_code: int
    stdout: bytes
    stderr: bytes
    started_at: str
    finished_at: str
    record_path: Path

    def stdout_text(self) -> str:
        return self.stdout.decode('utf-8', 'replace')

    def stderr_text(self) -> str:
        return self.stderr.decode('utf-8', 'replace')

    def combined(self) -> str:
        return self.stdout_text() + self.stderr_text()

    def json_payloads(self) -> list[dict]:
        payloads = []
        for line in self.combined().splitlines():
            stripped = line.strip()
            if not stripped.startswith('{'):
                continue
            try:
                value = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                payloads.append(value)
        return payloads

    def error_code(self) -> str | None:
        """The refusal code the engine printed, if it printed one."""
        for payload in reversed(self.json_payloads()):
            if 'code' in payload and 'message' in payload:
                return payload['code']
        return None

    def events(self) -> list[str]:
        return [payload['event'] for payload in self.json_payloads() if 'event' in payload]


def run_probe(name: str, argv: list[str], evidence: Path, *, cwd: Path | None = None,
              env: dict[str, str] | None = None, timeout: float = 180,
              stdin_bytes: bytes | None = None) -> ProbeResult:
    """Run one child and persist argv, raw stdout, raw stderr and the exit code."""
    folder = Path(evidence)
    folder.mkdir(parents=True, exist_ok=True)
    environment = base_environment() if env is None else env
    started = utc_now()
    completed = subprocess.run(
        [str(item) for item in argv], cwd=str(cwd or REPO_ROOT), env=environment,
        input=stdin_bytes, stdin=subprocess.DEVNULL if stdin_bytes is None else None,
        capture_output=True, timeout=timeout, check=False,
    )
    finished = utc_now()
    stdout_path = folder / f'{name}.stdout.bin'
    stderr_path = folder / f'{name}.stderr.bin'
    stdout_path.write_bytes(completed.stdout)
    stderr_path.write_bytes(completed.stderr)
    record_path = folder / f'{name}.result.json'
    write_json(record_path, {
        'name': name,
        'kind': 'completed-process',
        'argv': [str(item) for item in argv],
        'cwd': str(cwd or REPO_ROOT),
        'environment': environment_record(environment),
        'exit_code': completed.returncode,
        'started_at': started,
        'finished_at': finished,
        'stdout_bytes': len(completed.stdout),
        'stderr_bytes': len(completed.stderr),
        'stdout_file': str(stdout_path),
        'stderr_file': str(stderr_path),
    })
    return ProbeResult(name=name, argv=[str(item) for item in argv], cwd=str(cwd or REPO_ROOT),
                       exit_code=completed.returncode, stdout=completed.stdout,
                       stderr=completed.stderr, started_at=started, finished_at=finished,
                       record_path=record_path)


def run_probe_module(name: str, arguments: list[str], evidence: Path, *,
                     env: dict[str, str] | None = None, timeout: float = 180) -> ProbeResult:
    argv = [PYTHON, str(PROBES), '--repo', str(REPO_ROOT), *arguments]
    environment = base_environment() if env is None else env
    return run_probe(name, argv, evidence, cwd=REPO_ROOT, env=environment, timeout=timeout)


# --------------------------------------------------------------------------- product observations

def owner_state(evidence: Path, *, name: str = 'owner-state') -> dict:
    result = run_probe_module(name, ['owner-state', '--data-dir', str(instance()),
                                     '--project-id', project_id()], evidence)
    assert result.exit_code == 0, (
        f'{name} failed with exit {result.exit_code}\n'
        f'argv={result.argv}\nstdout={result.stdout_text()}\nstderr={result.stderr_text()}')
    payload = result.json_payloads()[-1]
    payload['_record'] = str(result.record_path)
    return payload


def source_status(evidence: Path, *, name: str = 'source-status') -> dict:
    result = run_probe_module(name, ['source-status', '--registration', str(registration())], evidence)
    assert result.exit_code == 0, (
        f'{name} failed with exit {result.exit_code}\nstdout={result.stdout_text()}\nstderr={result.stderr_text()}')
    payload = result.json_payloads()[-1]
    payload['_record'] = str(result.record_path)
    return payload


def routes_state(evidence: Path, *, name: str = 'routes-state') -> dict:
    result = run_probe_module(name, ['routes-state', '--data-dir', str(instance()),
                                     '--registration', str(registration())], evidence)
    assert result.exit_code == 0, (
        f'{name} failed with exit {result.exit_code}\nstdout={result.stdout_text()}\nstderr={result.stderr_text()}')
    payload = result.json_payloads()[-1]
    payload['_record'] = str(result.record_path)
    return payload


def instance_state(evidence: Path, data_dir: Path | None = None, *,
                   name: str = 'instance-state') -> dict:
    """Owner/control/audit facts of one instance copy, read through product code."""
    result = run_probe_module(name, ['instance-state', '--data-dir', str(data_dir or instance())], evidence)
    assert result.exit_code == 0, (
        f'{name} failed with exit {result.exit_code}\n'
        f'argv={result.argv}\nstdout={result.stdout_text()}\nstderr={result.stderr_text()}')
    payload = result.json_payloads()[-1]
    payload['_record'] = str(result.record_path)
    return payload


def metadata_value(data_dir: Path, key: str):
    import sqlite3

    connection = sqlite3.connect(Path(data_dir) / 'Metadata.sqlite', timeout=30)
    try:
        row = connection.execute('SELECT value FROM metadata WHERE key=?', (key,)).fetchone()
    finally:
        connection.close()
    return None if row is None else row[0]


def sqlite_rows(data_dir: Path, query: str, parameters: tuple = ()) -> list[dict]:
    import sqlite3

    connection = sqlite3.connect(Path(data_dir) / 'Metadata.sqlite', timeout=30)
    connection.row_factory = sqlite3.Row
    try:
        return [dict(row) for row in connection.execute(query, parameters)]
    finally:
        connection.close()


def sqlite_execute(data_dir: Path, statement: str, parameters: tuple = ()) -> None:
    import sqlite3

    connection = sqlite3.connect(Path(data_dir) / 'Metadata.sqlite', timeout=30)
    try:
        connection.execute(statement, parameters)
        connection.commit()
    finally:
        connection.close()


def insert_daily_authorization(data_dir: Path, *, instance_id: str, owner: str = 'local-user') -> None:
    """Fixture row making the authorization registry provably non-empty.

    It is inserted only into a throwaway instance copy, and only to prove the
    development control bootstrap refuses a non-empty registry.
    """
    digest = 'a' * 64
    sqlite_execute(
        data_dir,
        'INSERT INTO daily_project_authorizations '
        '(authorization_id, revision, instance_id, owner, body, content_sha256, '
        ' creation_action_json, creation_action_sha256, current, revoked, '
        ' created_projects, registry_revision) '
        'VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
        ('authorization-fixture-local-chain', 1, instance_id, owner, '{}', digest,
         '{}', digest, 1, 0, 0, 1),
    )


def owner_init_command(instance_id: str) -> str:
    """The one human TTY action this suite can never take."""
    return (
        f'$env:PYTHONPATH = \'{ENGINE_SRC}\'\n'
        f"& '{PYTHON}' -m video_creator.cli.main owner-init `\n"
        f"  --data-dir '{instance()}' `\n"
        "  --action initialize --action-key 'chain-owner-init-1' `\n"
        "  --owner-subject 'local-user' `\n"
        f"  --project-id '{project_id()}' `\n"
        f"  --expires-at '{expires_at(days=6)}'"
    )


def owner_skip_reason(state: dict) -> str:
    return (
        'The real Owner binding is absent (owner-init needs a real interactive TTY; '
        'this suite never confirms one). Observed state: {}. Run in a real terminal:\n\n{}'.format(json.dumps({key: state.get(key) for key in
                       ('owner_initialized', 'owner_active', 'error_code', 'active_error_code')},
                      ensure_ascii=False), owner_init_command(state.get('instance_id', '<instance>'))))


def build_command() -> str:
    """Rebuild this suite's current-checkout registration fixture."""
    return (f"& '{PYTHON}' '{FIXTURE_TOOL}' ensure --fixture-root '{installation()}'\n"
            '# the fixture rebuilds itself when the checkout bytes move; the integration '
            'hand-off slice is never written')


def register_route_command() -> str:
    return '\n'.join(
        f"& '{PYTHON}' -m video_creator.cli.main register-route --data-dir '{instance()}' --route-file '{path}'"
        for path in sorted(routes().glob('*.json')))


def ensure_project_command() -> str:
    helper = Path(r'G:/开发测试/Codex/VideoCreatorImplementation/Integration/LocalInstallationRegistrationBuild') / 'PrepareLocalChain.py'
    return (f"$env:PYTHONPATH = '{ENGINE_SRC}'\n"
            f"& '{PYTHON}' '{helper}' --repo '{REPO_ROOT}' ensure-project "
            f"--data-dir '{instance()}' --name 'VideoCreator Local Chain' --owner 'local-user'")


# --------------------------------------------------------------------------- dev host argv

def dev_host_arguments(command: str, *, registration: Path | None = None,
                       registration_sha256: str | None = None, expires: str | None = None,
                       data_dir: Path | None = None, host: str = '127.0.0.1', port: int = 0,
                       ffmpeg: Path | None = None, ffprobe: Path | None = None,
                       max_seconds: int = 300, omit: tuple[str, ...] = (),
                       auto_owner_init: bool = False,
                       extra: tuple[str, ...] = ()) -> list[str]:
    """Build the exact documented serve-dev / worker-dev command line."""
    registration = registration if registration is not None else globals()['registration']()
    data_dir = data_dir if data_dir is not None else instance()
    ffmpeg = ffmpeg if ffmpeg is not None else ffmpeg_binary()
    ffprobe = ffprobe if ffprobe is not None else ffprobe_binary()
    pinned = registration_sha256 if registration_sha256 is not None else sha256_file(registration)
    expiry = expires if expires is not None else expires_at()
    flags = {
        'registration': ['--development-registration', str(registration)],
        'registration-sha256': ['--development-registration-sha256', pinned],
        'expires': ['--development-expires-at', expiry],
    }
    argv = [str(PYTHON), '-m', 'video_creator.cli.development_host', command]
    for key in ('registration', 'registration-sha256', 'expires'):
        if key not in omit:
            argv += flags[key]
    if auto_owner_init:
        argv.append('--development-auto-owner-init')
    argv += ['--data-dir', str(data_dir)]
    if command == 'serve-dev':
        argv += ['--host', host, '--port', str(port)]
        if 'ffmpeg' not in omit and ffmpeg is not None:
            argv += ['--ffmpeg', str(ffmpeg)]
        if 'ffprobe' not in omit and ffprobe is not None:
            argv += ['--ffprobe', str(ffprobe)]
    else:
        argv += ['--max-seconds', str(max_seconds)]
    argv += list(extra)
    return argv


def dev_environment(instance_id: str | None, *, include_token: bool = True) -> dict[str, str]:
    extra: dict[str, str] = {}
    if instance_id is not None:
        extra[DEV_ENVIRONMENT] = instance_id
    if include_token:
        extra['VIDEO_CREATOR_API_TOKEN'] = new_token()
    return base_environment(extra)


# --------------------------------------------------------------------------- long-running children

@dataclass
class ServerProcess:
    """A long-running product child with raw byte logs and buffered lines."""
    name: str
    argv: list[str]
    evidence: Path
    stdout_path: Path
    stderr_path: Path
    record_path: Path
    process: subprocess.Popen
    lines: list[tuple[str, str]] = field(default_factory=list)
    _queue: queue.Queue = field(default_factory=queue.Queue)
    _threads: list[threading.Thread] = field(default_factory=list)
    _files: list = field(default_factory=list)
    _closed: bool = False

    def wait_for(self, predicate, *, timeout: float, label: str) -> dict:
        deadline = time.monotonic() + timeout
        while True:
            if self._queue.empty() and self.process.poll() is not None:
                self._drain()
                raise AssertionError(
                    f'{label} exited with {self.process.returncode} before the expected line.\n'
                    f'argv={self.argv}\nstderr={self.stderr_text()[-4000:]}\nstdout={self.stdout_text()[-2000:]}')
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                self._drain()
                raise AssertionError(
                    f'{label} did not reach the expected line within {timeout}s.\n'
                    f'argv={self.argv}\nstderr={self.stderr_text()[-4000:]}\nstdout={self.stdout_text()[-2000:]}')
            try:
                _stream, line = self._queue.get(timeout=min(0.5, remaining))
            except queue.Empty:
                continue
            payload = _json_line(line)
            if payload is not None and predicate(payload):
                return payload

    def wait_for_event(self, event: str, *, timeout: float = 120) -> dict:
        return self.wait_for(lambda payload: payload.get('event') == event,
                             timeout=timeout, label=f'{self.name} event {event!r}')

    def stop(self, *, grace: float = 20) -> int:
        if not self._closed:
            self._closed = True
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=grace)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=grace)
            for thread in self._threads:
                thread.join(timeout=5)
            for handle in self._files:
                handle.close()
            write_json(self.record_path, {
                'name': self.name,
                'kind': 'long-running-process',
                'argv': self.argv,
                'exit_code': self.process.returncode,
                'stdout_file': str(self.stdout_path),
                'stderr_file': str(self.stderr_path),
                'stopped_by_test': True,
            })
        return self.process.returncode

    def stdout_text(self) -> str:
        return self.stdout_path.read_bytes().decode('utf-8', 'replace') if self.stdout_path.exists() else ''

    def stderr_text(self) -> str:
        return self.stderr_path.read_bytes().decode('utf-8', 'replace') if self.stderr_path.exists() else ''

    def _drain(self) -> None:
        try:
            while True:
                self._queue.get_nowait()
        except queue.Empty:
            return

    def __enter__(self):
        return self

    def __exit__(self, *_error):
        self.stop()
        return False


def _json_line(line: str) -> dict | None:
    stripped = line.strip()
    if not stripped.startswith('{'):
        return None
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def launch(name: str, argv: list[str], evidence: Path, *, env: dict[str, str],
           cwd: Path | None = None) -> ServerProcess:
    folder = Path(evidence)
    folder.mkdir(parents=True, exist_ok=True)
    stdout_path = folder / f'{name}.stdout.bin'
    stderr_path = folder / f'{name}.stderr.bin'
    # Deliberate long-lived handles: the pump threads write the raw bytes until the
    # process is stopped; `stop()` closes them.
    stdout_handle = open(stdout_path, 'wb')  # noqa: SIM115
    stderr_handle = open(stderr_path, 'wb')  # noqa: SIM115
    process = subprocess.Popen([str(item) for item in argv], cwd=str(cwd or REPO_ROOT), env=env,
                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    server = ServerProcess(name=name, argv=[str(item) for item in argv], evidence=folder,
                           stdout_path=stdout_path, stderr_path=stderr_path,
                           record_path=folder / f'{name}.result.json', process=process,
                           _files=[stdout_handle, stderr_handle])

    def pump(stream, handle, tag) -> None:
        try:
            for raw in iter(stream.readline, b''):
                handle.write(raw)
                handle.flush()
                text = raw.decode('utf-8', 'replace').rstrip('\r\n')
                server.lines.append((tag, text))
                server._queue.put((tag, text))
        finally:
            stream.close()

    for stream, handle, tag in ((process.stdout, stdout_handle, 'stdout'),
                                (process.stderr, stderr_handle, 'stderr')):
        thread = threading.Thread(target=pump, args=(stream, handle, tag), daemon=True)
        thread.start()
        server._threads.append(thread)
    return server


# --------------------------------------------------------------------------- HTTP + ffprobe

def http_json(base_url: str, path: str, *, token: str, method: str = 'GET', body=None,
              idempotency_key: str | None = None, exact_headers: dict[str, str] | None = None,
              timeout: float = 60) -> tuple[int, dict, dict, bytes]:
    """One real HTTP call returning (status, headers, parsed-or-raw body, raw bytes)."""
    import urllib.error
    import urllib.request

    data = None if body is None else json.dumps(body, ensure_ascii=False).encode('utf-8')
    headers = {'Authorization': 'Bearer ' + token}
    if data is not None:
        headers['Content-Type'] = 'application/json'
    if idempotency_key:
        headers['Idempotency-Key'] = idempotency_key
    if exact_headers:
        headers.update(exact_headers)
    request = urllib.request.Request(base_url + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            status = response.status
            response_headers = {key.lower(): value for key, value in response.headers.items()}
    except urllib.error.HTTPError as error:
        raw = error.read()
        status = error.code
        response_headers = {key.lower(): value for key, value in error.headers.items()}
    payload: dict | bytes
    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        payload = raw
    return status, response_headers, payload, raw


def http_bytes(base_url: str, path: str, *, token: str, method: str = 'GET', body: bytes | None = None,
               content_type: str | None = None, timeout: float = 120) -> tuple[int, dict, bytes]:
    import urllib.request

    headers = {'Authorization': 'Bearer ' + token}
    if content_type:
        headers['Content-Type'] = content_type
    request = urllib.request.Request(base_url + path, data=body, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.status, {key.lower(): value for key, value in response.headers.items()}, response.read()


def ffprobe(path: Path, *, evidence: Path, name: str) -> dict:
    """Probe with the registration's bundled ffprobe, never a system binary."""
    result = run_probe(name, [str(ffprobe_binary()), '-v', 'error', '-print_format', 'json',
                              '-show_format', '-show_streams', '-count_frames', str(path)],
                       evidence, timeout=180)
    assert result.exit_code == 0, (
        f'bundled ffprobe failed with exit {result.exit_code}\nargv={result.argv}\n'
        f'stderr={result.stderr_text()}')
    return {'payload': json.loads(result.stdout_text()), 'record': str(result.record_path),
            'stdout': result.stdout_text(), 'stderr': result.stderr_text()}


def tool_versions(evidence: Path) -> dict:
    python = run_probe('version-python', [str(PYTHON), '-VV'], evidence, timeout=60)
    ffmpeg_run = run_probe('version-ffmpeg', [str(ffmpeg_binary()), '-version'], evidence, timeout=60)
    ffprobe_result = run_probe('version-ffprobe', [str(ffprobe_binary()), '-version'], evidence, timeout=60)
    return {
        'python': python.stdout_text().strip(),
        'python_exit': python.exit_code,
        'ffmpeg': ffmpeg_run.stdout_text().splitlines()[0] if ffmpeg_run.stdout_text() else '',
        'ffmpeg_exit': ffmpeg_run.exit_code,
        'ffprobe': ffprobe_result.stdout_text().splitlines()[0] if ffprobe_result.stdout_text() else '',
        'ffprobe_exit': ffprobe_result.exit_code,
    }


def git_head() -> str:
    try:
        completed = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=str(REPO_ROOT),
                                   capture_output=True, check=True, timeout=30)
        return completed.stdout.decode('utf-8').strip()
    except (OSError, subprocess.SubprocessError):
        return '<unavailable>'


def git_status(evidence: Path) -> str:
    result = run_probe('git-status', ['git', 'status', '--porcelain'], evidence, timeout=60)
    return result.stdout_text()


def copy_instance_for_serve(evidence: Path, name: str = 'isolated-instance') -> Path:
    """Copy only the SQLite instance files so a production `serve` cannot touch the chain."""
    destination = Path(evidence) / name
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    for path in sorted(instance().glob('Metadata.sqlite*')):
        shutil.copy2(path, destination / path.name)
    return destination
