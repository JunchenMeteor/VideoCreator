import assert from 'node:assert/strict';
import { test } from 'node:test';
import cp from 'node:child_process';
import { syncBuiltinESMExports } from 'node:module';
import { promisify } from 'node:util';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
import net from 'node:net';
import { fileURLToPath } from 'node:url';

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const caseRoot = process.env.VIDEO_CREATOR_T9_CASES;
assert(caseRoot && path.isAbsolute(caseRoot));
const originalExecFile = cp.execFile;
const realExecute = promisify(originalExecFile);
let armed = false;
let queried = 0;
let attemptedForce = 0;
const observations = [];
function controlledExecFile(executable, argv, options, callback) {
  if (armed && executable.toLowerCase().endsWith('taskkill.exe')) attemptedForce++;
  if (armed && executable.toLowerCase().endsWith('powershell.exe') && argv.at(-1).includes('ParentProcessId=')) {
    queried++;
    const script = argv.at(-1);
    observations.push({ ordinal: queried, injected: queried === 3, query_sha256: createHash('sha256').update(script).digest('hex'), target_pids: [...script.matchAll(/ProcessId=(\d+)/g)].map((match) => Number(match[1])) });
    if (queried === 3) {
      const error = new Error('T9 controlled target identity metadata unavailable');
      error.code = 'E_T9_IDENTITY_UNAVAILABLE';
      queueMicrotask(() => callback(error, '', ''));
      return undefined;
    }
  }
  return originalExecFile(executable, argv, options, callback);
}
controlledExecFile[promisify.custom] = (...args) => new Promise((resolve, reject) => controlledExecFile(...args, (error, stdout, stderr) => error ? reject(error) : resolve({ stdout, stderr })));
cp.execFile = controlledExecFile;
syncBuiltinESMExports();
const { watchOwnedChild } = await import('../../tools/build/EngineProcess.mjs');
const hash = (value) => createHash('sha256').update(value).digest('hex');
async function exactMetadata(pids) {
  assert(pids.every((pid) => Number.isSafeInteger(pid) && pid > 0));
  const filter = [...new Set(pids)].map((pid) => 'ProcessId=' + pid).join(' OR ');
  const script = '$ErrorActionPreference="Stop"; $rows=@(Get-CimInstance Win32_Process -Filter "' + filter + '" -Property ProcessId,ParentProcessId,CreationDate | ForEach-Object { [pscustomobject]@{pid=[int]$_.ProcessId;parent_pid=[int]$_.ParentProcessId;created_utc=$_.CreationDate.ToUniversalTime().ToString("o")} }); ConvertTo-Json -InputObject $rows -Compress';
  const { stdout } = await realExecute(path.join(process.env.SystemRoot, 'System32/WindowsPowerShell/v1.0/powershell.exe'), ['-NoProfile', '-NonInteractive', '-Command', script], { encoding: 'utf8', windowsHide: true, timeout: 10000 });
  const result = JSON.parse(stdout.replace(/^\uFEFF/, '').trim() || '[]');
  return Array.isArray(result) ? result : [result];
}
function startOwnedLeaf() {
  const fixture = path.join(repo, 'tests/gate0/T9Fixture/OwnedLoopbackChild.mjs');
  const child = cp.spawn(process.execPath, [fixture], { windowsHide: true, shell: false, env: { SystemRoot: process.env.SystemRoot }, stdio: ['ignore', 'pipe', 'pipe', 'ipc'] });
  let stdout = '';
  let stderr = '';
  child.stdout.on('data', (value) => { stdout += value.toString('utf8'); });
  child.stderr.on('data', (value) => { stderr += value.toString('utf8'); });
  const closed = new Promise((resolve) => child.once('close', (code, signal) => resolve({ code, signal })));
  const ready = new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('Owned leaf startup timeout')), 5000);
    child.once('message', (value) => { clearTimeout(timer); assert(value.event === 'ready' && Number.isInteger(value.port)); resolve(value); });
    child.once('error', (error) => { clearTimeout(timer); reject(error); });
  });
  return { child, closed, ready, output: () => ({ stdout, stderr }) };
}
async function closeKnownChild(run) {
  if (run.child.connected) run.child.send('close');
  const timeout = new Promise((resolve) => { const timer = setTimeout(() => resolve(null), 5000); timer.unref(); });
  const exit = await Promise.race([run.closed, timeout]);
  assert(exit, 'Self-owned fixture must close naturally through its private IPC');
  return exit;
}
async function isPortClosed(port) {
  return new Promise((resolve) => { const socket = net.createConnection({ host: '127.0.0.1', port }); const done = (value) => { socket.destroy(); resolve(value); }; socket.once('connect', () => done(false)); socket.once('error', (error) => done(error.code === 'ECONNREFUSED')); socket.setTimeout(1000, () => done(false)); });
}

test('immediate target metadata lookup failure skips force and preserves actual owned target and sibling', { timeout: 30000 }, async () => {
  const directory = path.join(caseRoot, 'ImmediateTargetLookup');
  await mkdir(directory, { recursive: true });
  const sourcePath = path.join(repo, 'tools/build/EngineProcess.mjs');
  assert.equal(hash(await readFile(sourcePath)), '874d0adc2205cc55dca0138963aa349c0389cab42bf6073d401ba6082ad95a28');
  const toolPaths = [process.execPath, path.join(process.env.SystemRoot, 'System32/WindowsPowerShell/v1.0/powershell.exe'), path.join(process.env.SystemRoot, 'System32/taskkill.exe')];
  const toolBefore = {};
  for (const target of toolPaths) toolBefore[target] = hash(await readFile(target));
  const legacyBefore = await exactMetadata([22508]);
  const target = startOwnedLeaf();
  const sibling = startOwnedLeaf();
  const owned = watchOwnedChild(target.child);
  let targetReady;
  let siblingReady;
  let result;
  let targetExit;
  let siblingExit;
  let failure;
  const facts = {};
  try {
    targetReady = await target.ready;
    siblingReady = await sibling.ready;
    const stateBefore = await owned.inspect();
    assert.equal(stateBefore.verified, true);
    assert.equal(stateBefore.captured.length, 1, 'Fixture must be a leaf for deterministic third-query injection');
    assert.equal(stateBefore.captured[0].pid, target.child.pid);
    const targetIdentityBefore = await exactMetadata([target.child.pid]);
    const siblingIdentityBefore = await exactMetadata([sibling.child.pid]);
    armed = true;
    result = await owned.force();
    armed = false;
    const targetIdentityAfter = await exactMetadata([target.child.pid]);
    const siblingIdentityAfter = await exactMetadata([sibling.child.pid]);
    const targetStatus = (await fetch('http://127.0.0.1:' + targetReady.port, { signal: AbortSignal.timeout(2000) })).status;
    const siblingStatus = (await fetch('http://127.0.0.1:' + siblingReady.port, { signal: AbortSignal.timeout(2000) })).status;
    Object.assign(facts, { ownership_before: stateBefore, injected_query_sequence: observations, production_force_result: result, attempted_taskkill_invocations: attemptedForce, target: { ready: targetReady, before: targetIdentityBefore, after: targetIdentityAfter, health_after: targetStatus }, sibling: { ready: siblingReady, before: siblingIdentityBefore, after: siblingIdentityAfter, health_after: siblingStatus } });
    assert(observations[2]?.injected && observations[2].target_pids.includes(target.child.pid));
    assert.equal(attemptedForce, 0, 'Unknown immediate identity must never reach taskkill');
    assert.equal(result.actions.length, 1);
    assert.equal(result.actions[0].pid, target.child.pid);
    assert.equal(result.actions[0].skipped, 'identity_unverified');
    assert.equal(result.actions[0].error_code, 'owned_identity_unverified');
    assert.equal(result.ownership.verified, false);
    assert.equal(result.ownership.inspection_error, 'owned_inspection_failed');
    assert.equal(result.exit, null);
    assert.deepEqual(targetIdentityAfter, targetIdentityBefore);
    assert.deepEqual(siblingIdentityAfter, siblingIdentityBefore);
    assert.equal(targetStatus, 200);
    assert.equal(siblingStatus, 200);
  } catch (error) { failure = error; }
  finally {
    armed = false;
    targetExit = await closeKnownChild(target);
    siblingExit = await closeKnownChild(sibling);
    cp.execFile = originalExecFile;
    syncBuiltinESMExports();
    const remaining = await exactMetadata([target.child.pid, sibling.child.pid]);
    const legacyAfter = await exactMetadata([22508]);
    const toolAfter = {};
    for (const filename of toolPaths) toolAfter[filename] = hash(await readFile(filename));
    Object.assign(facts, { provider_calls: 0, real_key_reads: 0, executable: process.execPath, fixture: path.join(repo, 'tests/gate0/T9Fixture/OwnedLoopbackChild.mjs'), source_sha256: hash(await readFile(sourcePath)), target_actual_exit: targetExit, sibling_actual_exit: siblingExit, independent_remaining: remaining, target_port_closed: await isPortClosed(targetReady.port), sibling_port_closed: await isPortClosed(siblingReady.port), tools_before: toolBefore, tools_after: toolAfter, legacy_before: legacyBefore, legacy_after: legacyAfter, scope: 'Controlled execFile failure on exactly immediate target CIM query, real preceding/following CIM, actual owned Node loopback leaves and natural IPC cleanup. No arbitrary PID force, no full DevRuntime/UI/JobObject claim.' });
    await writeFile(path.join(directory, 'Receipt.json'), JSON.stringify(facts, null, 2) + '\n');
    await writeFile(path.join(directory, 'TargetStdout.txt'), target.output().stdout);
    await writeFile(path.join(directory, 'TargetStderr.txt'), target.output().stderr);
    await writeFile(path.join(directory, 'SiblingStdout.txt'), sibling.output().stdout);
    await writeFile(path.join(directory, 'SiblingStderr.txt'), sibling.output().stderr);
    assert.deepEqual(toolAfter, toolBefore);
    assert.deepEqual(legacyAfter, legacyBefore);
    assert.equal(remaining.length, 0);
  }
  if (failure) throw failure;
  assert.deepEqual(targetExit, { code: 0, signal: null });
  assert.deepEqual(siblingExit, { code: 0, signal: null });
});
