// Trusted development host only. No renderer command surface or worker supervision.
import { spawn, execFile } from 'node:child_process';
import { promisify } from 'node:util';
import path from 'node:path';
import net from 'node:net';

const execute = promisify(execFile);
const FRAME = Buffer.from('shutdown\n', 'ascii');
const MARKER = Buffer.from('{"event":"api_stopped","scope":"api"}\n', 'ascii');
const NORMAL_WAIT_MS = 15000;
const settle = (promise, milliseconds) => new Promise((resolve) => {
  const timer = setTimeout(() => resolve(null), milliseconds);
  promise.then((value) => { clearTimeout(timer); resolve(value); }, () => { clearTimeout(timer); resolve(null); });
});
const key = (item) => item.pid + ':' + item.created_utc;
const localAbsolute = (value) => typeof value === 'string' && path.isAbsolute(value) && !value.startsWith('//') && !value.startsWith('\\\\');

async function processMetadata(pids) {
  if (process.platform !== 'win32') throw new Error('owned_process_inspection_requires_windows');
  const unique = [...new Set(pids)];
  if (!unique.length) return [];
  if (unique.length > 128 || unique.some((pid) => !Number.isSafeInteger(pid) || pid <= 0)) throw new Error('owned_pid_invalid');
  const filter = unique.map((pid) => 'ProcessId=' + pid + ' OR ParentProcessId=' + pid).join(' OR ');
  // Only host-generated numeric IDs enter this fixed, read-only metadata query.
  const script = '$ErrorActionPreference="Stop"; $rows=@(Get-CimInstance Win32_Process -Filter "' + filter + '" -Property ProcessId,ParentProcessId,CreationDate | ForEach-Object { [pscustomobject]@{pid=[int]$_.ProcessId;parent_pid=[int]$_.ParentProcessId;created_utc=$_.CreationDate.ToUniversalTime().ToString("o")} }); ConvertTo-Json -InputObject $rows -Compress';
  const { stdout } = await execute(path.join(process.env.SystemRoot || 'C:/Windows', 'System32/WindowsPowerShell/v1.0/powershell.exe'), ['-NoProfile', '-NonInteractive', '-Command', script], { encoding: 'utf8', windowsHide: true, timeout: 5000, maxBuffer: 262144 });
  const value = JSON.parse(stdout.replace(/^\uFEFF/, '').trim() || '[]');
  const rows = Array.isArray(value) ? value : [value];
  if (rows.some((row) => !Number.isSafeInteger(row.pid) || !Number.isSafeInteger(row.parent_pid) || !Number.isFinite(Date.parse(row.created_utc)))) throw new Error('owned_metadata_invalid');
  return rows;
}

export function watchOwnedChild(child) {
  const captured = new Map();
  let inspectionError = null;
  let rootIdentity = null;
  const closed = new Promise((resolve) => {
    child.once('close', (code, signal) => resolve({ code, signal }));
    // Spawn errors are recorded, while close remains the authoritative termination event.
    child.on('error', () => {});
  });
  let ended = null;
  closed.then((value) => { ended = value; });
  async function capture() {
    if (!child.pid) return;
    try {
      let seeds = [child.pid];
      for (let depth = 0; depth < 16; depth++) {
        const rows = await processMetadata(seeds);
        const root = rows.find((row) => row.pid === child.pid);
        if (!rootIdentity && root && !ended) { rootIdentity = root; captured.set(key(root), root); }
        const sameRoot = root && rootIdentity && key(root) === key(rootIdentity);
        const validParents = new Set(rows.filter((row) => captured.has(key(row))).map((row) => row.pid));
        if (sameRoot) validParents.add(root.pid);
        const added = [];
        for (const row of rows) {
          if (validParents.has(row.parent_pid) && !captured.has(key(row))) {
            captured.set(key(row), row); added.push(row.pid);
          }
        }
        if (captured.size > 128) throw new Error('owned_tree_limit');
        if (!added.length) break;
        seeds = [...new Set([...seeds, ...added])];
      }
    } catch { inspectionError = 'owned_inspection_failed'; }
  }
  const initialCapture = capture();
  async function inspect() {
    await initialCapture;
    // A completed process with a positive PID but no captured root is still unverified.
    // Only an actual failed spawn (no PID) can prove that no child was created.
    if (!captured.size) return { verified: !child.pid && !!ended && !inspectionError, captured: [], alive: [], unproven_children: [], inspection_error: inspectionError || (child.pid ? 'root_identity_missing' : null) };
    try {
      const rows = await processMetadata([...captured.values()].map((row) => row.pid));
      const alive = rows.filter((row) => captured.has(key(row)));
      const knownPids = new Set([...captured.values()].map((row) => row.pid));
      const unproven = rows.filter((row) => knownPids.has(row.parent_pid) && !captured.has(key(row)));
      return { verified: !!rootIdentity && !inspectionError, captured: [...captured.values()], alive, unproven_children: unproven, inspection_error: inspectionError };
    } catch { inspectionError = 'owned_inspection_failed'; return { verified: false, captured: [...captured.values()], alive: [], unproven_children: [], inspection_error: inspectionError }; }
  }
  async function force() {
    await initialCapture;
    await capture();
    const actions = [];
    const state = await inspect();
    // Recheck creation identity immediately before each fixed taskkill invocation.
    const targets = [...state.alive].sort((a, b) => a.pid === child.pid ? -1 : b.pid === child.pid ? 1 : 0);
    for (const target of targets) {
      let current;
      try { current = (await processMetadata([target.pid])).find((row) => row.pid === target.pid); }
      catch {
        inspectionError = 'owned_inspection_failed';
        actions.push({ pid: target.pid, skipped: 'identity_unverified', error_code: 'owned_identity_unverified' });
        continue;
      }
      if (!current || key(current) !== key(target)) { actions.push({ pid: target.pid, skipped: 'identity_changed_or_absent' }); continue; }
      try {
        await execute(path.join(process.env.SystemRoot || 'C:/Windows', 'System32/taskkill.exe'), ['/PID', String(target.pid), '/T', '/F'], { windowsHide: true, timeout: 5000, maxBuffer: 65536 });
        actions.push({ pid: target.pid, tool_exit_code: 0 });
      } catch (error) { actions.push({ pid: target.pid, tool_exit_code: Number.isInteger(error.code) ? error.code : null, error_code: 'owned_force_failed' }); }
    }
    const exit = ended || await settle(closed, 5000);
    return { exit, actions, ownership: await inspect() };
  }
  return { child, closed, capture, inspect, force };
}

async function portClosed(baseUrl) {
  if (!baseUrl) return null;
  const port = Number(new URL(baseUrl).port);
  return new Promise((resolve) => {
    const socket = net.createConnection({ host: '127.0.0.1', port });
    socket.setTimeout(1500);
    const finish = (value) => { socket.destroy(); resolve(value); };
    socket.once('connect', () => finish(false));
    socket.once('timeout', () => finish(null));
    socket.once('error', (error) => finish(error.code === 'ECONNREFUSED' ? true : null));
  });
}

export function launchEngine({ repo, executable, dataDir, env, origin, mediaArgs = [], controlStdin = true }) {
  if (!localAbsolute(repo) || !localAbsolute(executable) || !localAbsolute(dataDir)) throw new Error('engine_paths_must_be_absolute');
  const originPort = origin?.match(/^http:\/\/127\.0\.0\.1:([1-9][0-9]{0,4})$/);
  if (origin && (!originPort || originPort[0] !== origin || Number(originPort[1]) < 1024 || Number(originPort[1]) > 65535)) throw new Error('engine_origin_invalid');
  if (mediaArgs.length && (mediaArgs.length !== 4 || mediaArgs[0] !== '--ffmpeg' || mediaArgs[2] !== '--ffprobe' || !localAbsolute(mediaArgs[1]) || !localAbsolute(mediaArgs[3]))) throw new Error('engine_media_args_invalid');
  const args = ['-B', '-X', 'utf8', '-m', 'video_creator.cli.main', 'serve', '--data-dir', dataDir, '--host', '127.0.0.1', '--port', '0'];
  if (origin) args.push('--allowed-origin', origin);
  if (controlStdin) args.push('--control-stdin');
  args.push(...mediaArgs);
  const child = spawn(executable, args, { cwd: repo, env: { ...env, PYTHONDONTWRITEBYTECODE: '1' }, stdio: ['pipe', 'pipe', 'pipe'], shell: false, windowsHide: true });
  const owned = watchOwnedChild(child);
  let markerCount = 0;
  let pending = Buffer.alloc(0);
  let discarding = false;
  child.stderr.on('data', (chunk) => {
    // Bounded byte parser. Unknown diagnostics/application data are never forwarded.
    for (const byte of chunk) {
      if (discarding) { if (byte === 10) discarding = false; continue; }
      pending = Buffer.concat([pending, Buffer.from([byte])]);
      if (pending.length > 512) { pending = Buffer.alloc(0); discarding = byte !== 10; continue; }
      if (byte === 10) { if (pending.equals(MARKER)) markerCount++; pending = Buffer.alloc(0); }
    }
  });
  let pipeError = false;
  child.stdin.on('error', () => { pipeError = true; });
  let readyValue = null;
  const ready = new Promise((resolve, reject) => {
    let buffer = Buffer.alloc(0);
    let settled = false;
    const finish = (error, value) => { if (settled) return; settled = true; clearTimeout(timer); if (error) reject(new Error(error)); else resolve(value); };
    const timer = setTimeout(() => finish('engine_ready_timeout'), 30000);
    child.once('error', () => finish('engine_spawn_failed'));
    owned.closed.then(() => finish('engine_exited_before_ready'));
    child.stdout.on('data', (part) => {
      if (settled) return;
      buffer = Buffer.concat([buffer, part]);
      if (buffer.length > 16384) { finish('engine_ready_invalid'); return; }
      const newline = buffer.indexOf(10);
      if (newline < 0) return;
      try {
        const value = JSON.parse(buffer.subarray(0, newline).toString('utf8'));
        const u = new URL(value.base_url);
        const keys = Object.keys(value).sort().join(',');
        // ADR0081: a restricted process adds its authorization channel state.
        const restricted = keys === 'authorization_state,base_url,event,instance_id'
          && (value.authorization_state === 'pending' || value.authorization_state === 'complete');
        if ((keys !== 'base_url,event,instance_id' && !restricted) || value.event !== 'ready' || u.protocol !== 'http:' || u.hostname !== '127.0.0.1' || !u.port || u.username || u.password || u.pathname !== '/' || u.search || u.hash || typeof value.instance_id !== 'string' || !value.instance_id) throw new Error();
        readyValue = value;
        // Ready proves API availability only; capture failures stay latched for cleanup.
        owned.capture().then(() => finish(null, value), () => finish('engine_ownership_unavailable'));
      } catch { finish('engine_ready_invalid'); }
    });
  });
  let stopping;
  async function shutdown() {
    await owned.capture();
    const alreadyClosed = child.exitCode !== null || child.signalCode !== null;
    let reason = alreadyClosed ? 'engine_already_exited' : 'control_pipe_unavailable';
    let exit = null;
    let sent = false;
    if (!alreadyClosed && !pipeError && !child.stdin.destroyed && child.stdin.writable && !child.stdin.writableEnded) {
      try {
        sent = await new Promise((resolve) => child.stdin.write(FRAME, (error) => resolve(!error)));
      } catch { sent = false; }
      if (sent) { reason = 'normal_wait_timeout'; exit = await settle(owned.closed, NORMAL_WAIT_MS); }
    } else if (alreadyClosed) exit = await settle(owned.closed, 1000);
    let ownership = await owned.inspect();
    let closedPort = await portClosed(readyValue?.base_url);
    const complete = (state) => state.verified && state.alive.length === 0 && state.unproven_children.length === 0;
    if (sent && exit?.code === 0 && exit.signal === null && markerCount === 1 && closedPort === true && complete(ownership)) {
      return { classification: 'normal', scope: 'api', frame_sent: true, frame_bytes: FRAME.length, marker_count: markerCount, exit, port_closed: closedPort, ownership, fallback: null };
    }
    if (exit) reason = 'api_stop_unconfirmed';
    const fallback = await owned.force();
    ownership = fallback.ownership;
    closedPort = await portClosed(readyValue?.base_url);
    return { classification: fallback.actions.some((action) => Object.hasOwn(action, 'tool_exit_code')) ? 'forced' : 'error', scope: 'api', reason, frame_sent: sent, frame_bytes: sent ? FRAME.length : 0, marker_count: markerCount, exit: fallback.exit || exit, port_closed: closedPort, ownership, fallback: { actions: fallback.actions }, cleanup_complete: complete(ownership) && (readyValue ? closedPort === true : true) };
  }
  return { child, ready, closed: owned.closed, args, shutdown: () => stopping ||= shutdown(), disconnectControl: () => child.stdin.end() };
}

// Each invocation is isolated: even a synchronous API throw cannot skip Vite.
// This private pair owns no Worker and never changes a production or budget.
export async function cleanupRuntimeChildren(engine, viteOwned) {
  const [api, workbench] = await Promise.allSettled([
    Promise.resolve().then(() => engine.shutdown()),
    Promise.resolve().then(() => viteOwned ? viteOwned.force() : null),
  ]);
  return { api, workbench };
}
