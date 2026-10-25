// Independent test observations of real owned processes and loopback HTTP.
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { createHash, randomBytes } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';
import { launchEngine } from '../../tools/build/EngineProcess.mjs';

const execute = promisify(execFile);
export const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
export const caseRoot = process.env.VIDEO_CREATOR_T7_CASES;
assert(caseRoot && path.isAbsolute(caseRoot), 'A dedicated absolute T7 case directory is required');
export const python = path.join(repo, '.venv/Scripts/python.exe');
export const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
export const sha256 = (data) => createHash('sha256').update(data).digest('hex');

export function safeEnvironment() {
  const output = {};
  for (const name of ['SystemRoot', 'WINDIR', 'ComSpec', 'PATH', 'PATHEXT', 'TEMP', 'TMP', 'PSModulePath']) {
    if (process.env[name]) output[name] = process.env[name];
  }
  return { ...output, PYTHONPATH: path.join(repo, 'services/engine/src'), PYTHONUTF8: '1',
    PYTHONIOENCODING: 'utf-8', OTEL_SDK_DISABLED: 'true', CREWAI_TRACING_ENABLED: 'false' };
}

export async function directory(name) {
  assert(/^[A-Z][a-zA-Z0-9]*$/.test(name));
  const value = path.join(caseRoot, name);
  await mkdir(value, { recursive: true });
  return value;
}

export async function writeReceipt(name, value) {
  const folder = await directory(name);
  await writeFile(path.join(folder, 'T7Receipt.json'), JSON.stringify(value, null, 2) + '\n', 'utf8');
}

export async function metadata(pids) {
  // Independent explicit PID observations: no tree traversal, names, commands or broad inventory.
  assert.equal(process.platform, 'win32', 'Other operating systems are not implemented/measured by this observer');
  const ids = [...new Set(pids)];
  assert(ids.every((id) => Number.isSafeInteger(id) && id > 0));
  if (!ids.length) return [];
  const filter = ids.map((id) => 'ProcessId=' + id).join(' OR ');
  const script = '$ErrorActionPreference="Stop"; $rows=@(Get-CimInstance Win32_Process -Filter "' + filter + '" -Property ProcessId,ParentProcessId,CreationDate | ForEach-Object { [pscustomobject]@{pid=[int]$_.ProcessId;parent_pid=[int]$_.ParentProcessId;created_utc=$_.CreationDate.ToUniversalTime().ToString("o")} }); ConvertTo-Json -InputObject $rows -Compress';
  const result = await execute(path.join(process.env.SystemRoot || 'C:/Windows', 'System32/WindowsPowerShell/v1.0/powershell.exe'),
    ['-NoProfile', '-NonInteractive', '-Command', script], { env: safeEnvironment(), windowsHide: true, timeout: 10000, encoding: 'utf8' });
  const parsed = JSON.parse(result.stdout.replace(/^\uFEFF/, '').trim() || '[]');
  return Array.isArray(parsed) ? parsed : [parsed];
}

export function identity(row) { return row.pid + ':' + row.created_utc; }

export async function start(name, { dataDir, controlled = true, tokenPresent = true, executable = python, mediaArgs = [], markerMode } = {}) {
  const folder = await directory(name);
  const token = randomBytes(32).toString('hex');
  const env = safeEnvironment();
  if (tokenPresent) env.VIDEO_CREATOR_API_TOKEN = token;
  if (markerMode) {
    env.PYTHONPATH = path.join(repo, 'tests/gate0/T7Fixture') + path.delimiter + env.PYTHONPATH;
    env.VIDEO_CREATOR_T7_MARKER = markerMode;
  }
  const host = launchEngine({ repo, executable, dataDir: dataDir || path.join(folder, 'Instance Chinese 空格'),
    env, mediaArgs, controlStdin: controlled });
  const output = { stdout: '', stderr: '' };
  host.child.stdout.on('data', (bytes) => { output.stdout += bytes.toString('utf8'); });
  host.child.stderr.on('data', (bytes) => { output.stderr += bytes.toString('utf8'); });
  const redact = (text) => text.replaceAll(token, '[test-session-redacted]');
  const request = async (route, options = {}) => {
    const ready = await host.ready;
    return fetch(ready.base_url + route, { ...options,
      headers: { Authorization: 'Bearer ' + token, ...options.headers }, signal: AbortSignal.timeout(8000) });
  };
  return { name, folder, host, output, request, token, redact,
    save: async (facts) => writeReceipt(name, { ...facts, actual_args: host.args,
      raw_stdout: redact(output.stdout), raw_stderr: redact(output.stderr),
      session_token_present_in_raw_output: output.stdout.includes(token) || output.stderr.includes(token),
      provider_calls: 0, real_key_reads: 0, scope: 'Owned Windows Node helper to actual local Python API; not native or worker lifecycle' }) };
}

export async function assertNormal(run, result) {
  assert.equal(result.classification, 'normal');
  assert.deepEqual(result.exit, { code: 0, signal: null });
  assert.equal(result.frame_sent, true);
  assert.equal(result.frame_bytes, 9);
  assert.equal(result.marker_count, 1);
  assert.equal(result.port_closed, true);
  assert.equal(result.ownership.verified, true);
  assert.equal(result.ownership.alive.length, 0);
  assert.equal(result.ownership.unproven_children.length, 0);
  assert(result.ownership.captured.some((row) => row.pid === run.host.child.pid));
  assert(result.ownership.captured.every((row) => Number.isFinite(Date.parse(row.created_utc))));
  assert.equal((await metadata(result.ownership.captured.map((row) => row.pid))).length, 0);
  assert(!run.output.stdout.includes(run.token) && !run.output.stderr.includes(run.token), 'Session token must not appear in child output');
}

export async function assertFailedCleanup(run, result, expected) {
  assert.equal(result.classification, expected);
  assert.notEqual(result.classification, 'normal');
  assert.equal(result.scope, 'api');
  assert.equal(result.ownership.verified, true);
  assert.equal(result.ownership.alive.length, 0);
  assert.equal(result.ownership.unproven_children.length, 0);
  assert.equal(result.cleanup_complete, true);
  assert.equal((await metadata(result.ownership.captured.map((row) => row.pid))).length, 0);
  assert(!run.output.stdout.includes(run.token) && !run.output.stderr.includes(run.token));
}

export async function cleanup(run) {
  const result = await run.host.shutdown();
  assert.equal(result.ownership.alive.length, 0, 'Do not leave an owned process behind after the test');
}

export function waveSignal() {
  const samples = 48000;
  const output = Buffer.alloc(44 + samples * 2);
  output.write('RIFF', 0); output.writeUInt32LE(output.length - 8, 4); output.write('WAVEfmt ', 8);
  output.writeUInt32LE(16, 16); output.writeUInt16LE(1, 20); output.writeUInt16LE(1, 22);
  output.writeUInt32LE(48000, 24); output.writeUInt32LE(96000, 28);
  output.writeUInt16LE(2, 32); output.writeUInt16LE(16, 34); output.write('data', 36);
  output.writeUInt32LE(samples * 2, 40);
  for (let index = 0; index < samples; index++) output.writeInt16LE(Math.round(5000 * Math.sin(2 * Math.PI * 440 * index / 48000)), 44 + index * 2);
  return output;
}

export async function jsonResponse(response, status) {
  assert.equal(response.status, status);
  return response.json();
}

export async function pinFiles(paths) {
  const output = {};
  for (const filename of paths) output[filename] = sha256(await readFile(filename));
  return output;
}
