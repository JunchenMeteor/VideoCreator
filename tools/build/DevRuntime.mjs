// Development host: tokens exist only in child process environment and memory.
import { spawn } from 'node:child_process';
import { fstatSync } from 'node:fs';
import { Socket } from 'node:net';
import { launchEngine, watchOwnedChild, cleanupRuntimeChildren } from './EngineProcess.mjs';
import { randomBytes, createHash } from 'node:crypto';
import { mkdir, readFile, realpath } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { createRequire } from 'node:module';

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const options = process.argv.slice(2);
const get = (name) => { const i = options.indexOf(name); return i < 0 ? undefined : options[i + 1]; };
const dataDir = get('--data-dir');
if (!dataDir || !path.isAbsolute(dataDir)) throw new Error('--data-dir must be an absolute isolated local instance directory');
const controlEnabled = options.includes('--control-stdin');
if (controlEnabled) {
  if (options.indexOf('--control-stdin') !== options.lastIndexOf('--control-stdin')) throw new Error('host_control_flag_invalid');
  try {
    const input = fstatSync(0);
    if (!(process.stdin instanceof Socket) || !process.stdin.readable || process.stdin.isTTY === true || input.isFile() || input.isCharacterDevice()) throw new Error();
  } catch { throw new Error('host_control_pipe_required'); }
}
const python = process.env.VIDEO_CREATOR_PYTHON || path.join(repo, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const token = randomBytes(32).toString('hex');
const portIndex = options.indexOf('--workbench-port');
const portText = portIndex < 0 ? '1420' : options[portIndex + 1];
if ((portIndex >= 0 && options.lastIndexOf('--workbench-port') !== portIndex) || typeof portText !== 'string' || !/^[1-9][0-9]{0,4}$/.test(portText) || String(Number(portText)) !== portText || Number(portText) < 1024 || Number(portText) > 65535) throw new Error('workbench_port_invalid');
const workbenchPort = Number(portText);
const origin = 'http://127.0.0.1:' + workbenchPort;
const env = { ...process.env, PYTHONPATH: path.join(repo, 'services/engine/src'), VIDEO_CREATOR_API_TOKEN: token, PYTHONUTF8: '1', PYTHONIOENCODING: 'utf-8' };
const mediaArgs = [];
let engine;
let pendingStopCause;
let trustedStopRequested = false;
let vite;
let viteOwned;
let stopping;
let lifecycleFailed = false;
let hostReady = false;
let earlyStopRequested = false;
let closeControlReader = () => {};
let rejectWorkbenchReady;
const stop = (cause, abnormal = false) => {
  lifecycleFailed ||= abnormal || cause !== 'host_control';
  if (lifecycleFailed) process.exitCode = 1;
  if (cause === 'host_control') trustedStopRequested = true;
  if (cause === 'host_control' && !hostReady) earlyStopRequested = true;
  if (stopping) return stopping;
  if (!engine) { pendingStopCause ||= cause; return Promise.resolve(); }
  closeControlReader();
  rejectWorkbenchReady?.(new Error('workbench_stopping'));
  stopping = (async () => {
    const results = await cleanupRuntimeChildren(engine, viteOwned);
    const api = results.api.status === 'fulfilled' ? results.api.value : null;
    const workbench = results.workbench.status === 'fulfilled' ? results.workbench.value : null;
    const workbenchCleared = results.workbench.status === 'fulfilled' && (!workbench || (workbench.exit && workbench.ownership?.verified && !workbench.ownership.alive.length && !workbench.ownership.unproven_children.length));
    const workbenchForced = workbench?.actions.some((action) => action.tool_exit_code === 0) ?? false;
    if (workbench && !workbenchForced) lifecycleFailed = true;
    const apiCleared = api?.classification === 'normal';
    const controlled = trustedStopRequested && apiCleared && workbenchCleared && !lifecycleFailed && !earlyStopRequested && hostReady;
    console.log(JSON.stringify({ event: 'dev_runtime_stopped', scope: 'host', api_scope: 'api', cause, classification: controlled ? 'controlled' : 'error', startup_status: hostReady ? 'ready' : earlyStopRequested ? 'stopped_before_ready' : 'failed', api_classification: api?.classification ?? 'error', api_exit_code: api?.exit?.code ?? engine.child.exitCode ?? null, api_signal: api?.exit?.signal ?? engine.child.signalCode ?? null, api_cleanup_error: results.api.status === 'rejected' ? 'api_cleanup_failed' : null, workbench_state: viteOwned ? workbenchCleared ? 'stopped' : 'unconfirmed' : 'not_started', workbench_cleanup_method: viteOwned ? workbenchForced ? 'owned_force' : 'unconfirmed' : 'not_started', workbench_cleanup_error: results.workbench.status === 'rejected' ? 'workbench_cleanup_failed' : null, workbench_exit_code: workbench?.exit?.code ?? null, workbench_signal: workbench?.exit?.signal ?? null, workbench_force_actions: workbench?.actions ?? [], api_marker_count: api?.marker_count ?? 0, api_port_closed: api?.port_closed ?? null, api_ownership: api?.ownership ?? null, workbench_ownership: workbench?.ownership ?? null, owned_cleanup_complete: apiCleared && workbenchCleared }));
    if (!controlled) process.exitCode = 1;
  })().catch(() => { console.error(JSON.stringify({ event: 'failed', code: 'owned_cleanup_failed' })); process.exitCode = 1; });
  return stopping;
};
process.once('SIGINT', () => void stop('host_sigint'));
process.once('SIGTERM', () => void stop('host_sigterm'));

if (controlEnabled) {
  let frame = [];
  let discarding = false;
  const diagnostic = (code) => console.error(JSON.stringify({ event: 'dev_host_control', code }));
  const onData = (block) => {
    for (const byte of block) {
      if (discarding) { if (byte === 10) discarding = false; continue; }
      if (byte !== 10 && frame.length >= 63) { frame = []; discarding = true; diagnostic('frame_too_large'); continue; }
      frame.push(byte);
      if (byte === 10) {
        const accepted = Buffer.from(frame).equals(Buffer.from('shutdown\n', 'ascii'));
        frame = [];
        if (accepted) void stop('host_control'); else diagnostic('frame_rejected');
      }
    }
  };
  const onEnd = () => { if (frame.length) diagnostic('incomplete_frame'); frame = []; discarding = false; process.stdin.removeListener('data', onData); diagnostic('channel_eof'); };
  const onError = () => { frame = []; discarding = false; process.stdin.removeListener('data', onData); diagnostic('channel_unavailable'); };
  closeControlReader = () => { process.stdin.removeListener('data', onData); process.stdin.removeListener('end', onEnd); process.stdin.removeListener('error', onError); process.stdin.pause(); process.stdin.destroy(); };
  process.stdin.on('data', onData);
  process.stdin.once('end', onEnd);
  process.stdin.once('error', onError);
}

// Reader is already installed. Yield once so pre-buffered pipe data can latch.
async function prepareEngine() {
  await new Promise((resolve) => setImmediate(resolve));
  if (pendingStopCause) return null;
// This launcher never authorizes budget, registers routes, imports model keys, or starts a worker.
const resourceManifest = process.env.VIDEO_CREATOR_RESOURCE_MANIFEST;
if (resourceManifest) {
  const manifest = JSON.parse(await readFile(resourceManifest, 'utf8'));
  const resourceRoot = await realpath(manifest.runtime_root);
  for (const file of manifest.files) {
    if (pendingStopCause) return null;
    const target = await realpath(path.resolve(resourceRoot, file.relative_path));
    const relative = path.relative(resourceRoot, target);
    if (relative.startsWith('..') || path.isAbsolute(relative)) throw new Error('Resource manifest escapes its installation root');
    const bytes = await readFile(target);
    if (bytes.length !== file.bytes || createHash('sha256').update(bytes).digest('hex') !== file.sha256.toLowerCase()) throw new Error('Resource bytes differ from pinned manifest');
  }
  for (const [flag, key, relative] of [['--ffmpeg', 'ffmpeg_path', 'bin/ffmpeg.exe'], ['--ffprobe', 'ffprobe_path', 'bin/ffprobe.exe']]) {
    if (!manifest.files.some((file) => file.relative_path === relative)) throw new Error('Required media resource is absent');
    const binary = await realpath(manifest[key]);
    if (binary !== await realpath(path.join(resourceRoot, relative))) throw new Error('Media resource entry differs from its verified manifest');
    mediaArgs.push(flag, binary);
  }
}
if (pendingStopCause) return null;
await mkdir(dataDir, { recursive: true });
if (pendingStopCause) return null;
  return launchEngine({ repo, executable: python, dataDir, env, origin, mediaArgs });
}
try { engine = await prepareEngine(); }
catch { lifecycleFailed = true; console.error(JSON.stringify({ event: 'failed', code: 'engine_start_failed' })); }
if (!engine) {
  closeControlReader();
  process.exitCode = 1;
  console.log(JSON.stringify({ event: 'dev_runtime_stopped', scope: 'host', api_scope: 'api', cause: pendingStopCause ?? 'engine_start_failed', classification: 'error', startup_status: earlyStopRequested ? 'stopped_before_ready' : 'failed', api_classification: 'not_started', api_exit_code: null, api_signal: null, api_marker_count: 0, api_port_closed: null, api_ownership: null, workbench_state: 'not_started', workbench_cleanup_method: 'not_started', workbench_exit_code: null, workbench_signal: null, workbench_force_actions: [], workbench_ownership: null, owned_cleanup_complete: false }));
}
if (engine) {
engine.closed.then((exit) => { if (!stopping) { console.error(JSON.stringify({ event: 'failed', code: 'engine_exited' })); void stop('engine_exited', true); } else if (exit.code !== 0 || exit.signal !== null) lifecycleFailed = true; });
if (pendingStopCause) void stop(pendingStopCause);
// Hard parent loss cannot run this asynchronous cleanup; native supervision is separate.
let ready;
try { ready = await engine.ready; }
catch { console.error(JSON.stringify({ event: 'failed', code: 'engine_start_failed' })); await stop('engine_start_failed', true); }
if (ready && !stopping) {
  try {
    const require = createRequire(path.join(repo, 'apps/workbench/package.json'));
    const viteCli = path.join(path.dirname(require.resolve('vite/package.json')), 'bin/vite.js');
    // Non-secret bootstrap is issued only after this owned API's validated ready.
    // Vite still holds the bearer privately; frontend receives only this origin.
    vite = spawn(process.execPath, [viteCli, '--host', '127.0.0.1'], { cwd: path.join(repo, 'apps/workbench'), env: {
      ...env,
      VIDEO_CREATOR_ENGINE_URL: ready.base_url,
      VIDEO_CREATOR_WORKBENCH_PORT: String(workbenchPort),
      VIDEO_CREATOR_TRUSTED_WORKBENCH_ORIGIN: origin,
      VIDEO_CREATOR_WORKBENCH_BOOTSTRAP_MODE: 'managed-proxy',
      VIDEO_CREATOR_WORKBENCH_BOOTSTRAP_SOURCE: 'dev-runtime-api-ready',
      VIDEO_CREATOR_WORKBENCH_INSTANCE_ID: ready.instance_id,
    }, stdio: ['ignore', 'pipe', 'pipe'], shell: false, windowsHide: true });
    viteOwned = watchOwnedChild(vite);
    vite.stderr.resume();
    vite.once('error', () => { console.error(JSON.stringify({ event: 'failed', code: 'workbench_spawn_failed' })); void stop('workbench_spawn_failed', true); });
    viteOwned.closed.then(() => { if (!stopping) void stop('workbench_exited', true); });
    await new Promise((resolve, reject) => {
      let buffer = '';
      let settled = false;
      const finish = (error) => { if (settled) return; settled = true; clearTimeout(timer); rejectWorkbenchReady = undefined; if (error) reject(error); else resolve(); };
      const timer = setTimeout(() => finish(new Error('workbench_ready_timeout')), 15000);
      rejectWorkbenchReady = (error) => finish(error);
      viteOwned.closed.then(() => finish(new Error('workbench_exited_before_ready')));
      vite.stdout.on('data', (bytes) => {
        if (settled) return;
        buffer += bytes.toString('utf8');
        if (buffer.length > 16384) { finish(new Error('workbench_ready_invalid')); return; }
        const plain = buffer.replace(/\x1b\[[0-9;]*m/g, '');
        if (plain.includes('Local:') && plain.includes(origin + '/')) finish();
      });
    });
    if (!stopping) {
      hostReady = true;
      console.log(JSON.stringify({ event: 'dev_runtime_ready', workbench_url: origin, instance_id: ready.instance_id, authentication: 'private_same_origin_proxy', paid_worker: false, media_resources_verified: mediaArgs.length === 4 }));
    }
  } catch { console.error(JSON.stringify({ event: 'failed', code: 'workbench_start_failed' })); await stop('workbench_start_failed', true); }
}
}
