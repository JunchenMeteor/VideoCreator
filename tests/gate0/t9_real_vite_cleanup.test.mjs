import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import path from 'node:path';
import net from 'node:net';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';
import { cleanupRuntimeChildren, watchOwnedChild } from '../../tools/build/EngineProcess.mjs';
import { cleanup, metadata, pinFiles, repo, safeEnvironment, sleep, start } from './t7_node_helpers.mjs';

const caseRoot = process.env.VIDEO_CREATOR_T9_CASES;
assert(caseRoot && path.isAbsolute(caseRoot));
const hash = (value) => createHash('sha256').update(value).digest('hex');
const input = JSON.parse(await readFile(process.env.VIDEO_CREATOR_T9_RUNTIME_INPUTS, 'utf8'));
const require = createRequire(path.join(repo, 'apps/workbench/package.json'));
const viteCli = path.join(path.dirname(require.resolve('vite/package.json')), 'bin/vite.js');
const sourcePath = path.join(repo, 'tools/build/DevRuntime.mjs');
const sourceBytes = await readFile(sourcePath);
assert.equal(hash(sourceBytes), 'c0683c9a523398c0c866d5b711b605ea87f1e8864946e53fd0056d8acf820af8');
const source = sourceBytes.toString('utf8');
const begin = source.indexOf('const stop = (cause, abnormal = false) => {');
const end = source.indexOf("\nprocess.once('SIGINT'", begin);
assert(begin >= 0 && end > begin);
const callback = source.slice(begin, end);
let inputBefore;
let legacyBefore;
before(async () => {
  inputBefore = await pinFiles(input.paths);
  legacyBefore = await metadata([22508]);
  await writeFile(path.join(caseRoot, 'RuntimeInputsBefore.json'), JSON.stringify({ hashes: inputBefore, legacy_before: legacyBefore }, null, 2) + '\n');
});
after(async () => {
  const inputAfter = await pinFiles(input.paths);
  const legacyAfter = await metadata([22508]);
  await writeFile(path.join(caseRoot, 'RuntimeInputsAfter.json'), JSON.stringify({ before: inputBefore, after: inputAfter, legacy_before: legacyBefore, legacy_after: legacyAfter }, null, 2) + '\n');
  assert.deepEqual(inputAfter, inputBefore);
  assert.deepEqual(legacyAfter, legacyBefore);
});

async function freePort() {
  const server = net.createServer();
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve); });
  const port = server.address().port;
  await new Promise((resolve) => server.close(resolve));
  return port;
}
async function portClosed(port) {
  return new Promise((resolve) => {
    const socket = net.createConnection({ host: '127.0.0.1', port });
    const done = (value) => { socket.destroy(); resolve(value); };
    socket.once('connect', () => done(false));
    socket.once('error', (error) => done(error.code === 'ECONNREFUSED'));
    socket.setTimeout(1500, () => done(false));
  });
}
for (const failure of ['SyncThrow', 'AsyncReject']) {
  test('source-bound API ' + failure + ' still clears real owned Vite and protects sibling API', { timeout: 45000 }, async () => {
    const directory = path.join(caseRoot, failure);
    await mkdir(directory, { recursive: true });
    const root = path.join(directory, 'ViteRoot');
    await mkdir(root, { recursive: true });
    await writeFile(path.join(root, 'index.html'), '<!doctype html><html><body><h1>T9 self-owned Vite resource</h1></body></html>\n');
    const main = await start('P02' + failure + 'Main');
    const sibling = await start('P02' + failure + 'Sibling');
    let child;
    let owned;
    let rawOut = '';
    let rawErr = '';
    let forceResult;
    const port = await freePort();
    const baseUrl = 'http://127.0.0.1:' + port;
    const calls = [];
    const logs = [];
    const argv = [viteCli, root, '--config', path.join(repo, 'tests/gate0/T9Fixture/ViteConfig.mjs'), '--host', '127.0.0.1', '--port', String(port), '--strictPort'];
    try {
      const mainReady = await main.host.ready;
      const siblingReady = await sibling.host.ready;
      const siblingIdentityBefore = await metadata([sibling.host.child.pid]);
      assert.equal(siblingIdentityBefore.length, 1);
      child = spawn(process.execPath, argv, { cwd: directory, env: { ...safeEnvironment(), VIDEO_CREATOR_T9_VITE_CACHE: path.join(directory, 'ViteCache') }, windowsHide: true, shell: false, stdio: ['ignore', 'pipe', 'pipe'] });
      owned = watchOwnedChild(child);
      child.stdout.on('data', (bytes) => { rawOut += bytes.toString('utf8'); });
      child.stderr.on('data', (bytes) => { rawErr += bytes.toString('utf8'); });
      let html;
      const deadline = Date.now() + 15000;
      while (Date.now() < deadline && child.exitCode === null) {
        try { const response = await fetch(baseUrl, { signal: AbortSignal.timeout(1000) }); if (response.status === 200) { html = await response.text(); break; } } catch {}
        await sleep(100);
      }
      assert(html?.includes('T9 self-owned Vite resource'), 'Real Vite must return owned HTML before cleanup');
      await owned.capture();
      const viteBefore = await owned.inspect();
      assert.equal(viteBefore.verified, true);
      assert(viteBefore.captured.some((row) => row.pid === child.pid));
      const stopContext = {
        stopping: undefined,
        cleanupRuntimeChildren,
        engine: { child: main.host.child, shutdown: failure === 'SyncThrow' ? () => { calls.push('engine_shutdown'); throw new Error('T9 synthetic synchronous API cleanup failure'); } : async () => { calls.push('engine_shutdown'); throw new Error('T9 synthetic asynchronous API cleanup failure'); } },
        viteOwned: { force: async () => { calls.push('real_vite_force'); forceResult = await owned.force(); return forceResult; } },
        process: { exitCode: 0 },
        console: { log: (value) => logs.push(value), error: (value) => logs.push(value) },
      };
      const stop = new vm.Script("'use strict';\n" + callback + '\nstop;', { filename: sourcePath + ':T9ActualStopCallback' }).runInNewContext(stopContext);
      await stop('T9-injected-' + failure, true);
      const remaining = await metadata(viteBefore.captured.map((row) => row.pid));
      const siblingIdentityAfter = await metadata([sibling.host.child.pid]);
      const mainStatus = (await main.request('/api/v1/health')).status;
      const siblingStatus = (await sibling.request('/api/v1/health')).status;
      const closedPort = await portClosed(port);
      await writeFile(path.join(directory, 'Receipt.json'), JSON.stringify({
        source_path: sourcePath, source_sha256: hash(sourceBytes), callback_sha256: hash(callback), callback_character_start: begin, callback_character_end: end,
        actual_callback_source: callback, injected_api_failure: failure, calls, logs, isolated_exit_code: stopContext.process.exitCode,
        actual_vite: { executable: process.execPath, args: argv, pid: child.pid, base_url: baseUrl, initial_html_status: 200, html_sha256: hash(html), ownership_before: viteBefore, result: forceResult, independent_remaining: remaining, port_closed: closedPort },
        main_api: { ready: mainReady, health_after: mainStatus }, sibling_api: { ready: siblingReady, before: siblingIdentityBefore, after: siblingIdentityAfter, health_after: siblingStatus },
        provider_calls: 0, real_key_reads: 0,
        scope: 'Fixed production stop callback and cleanupRuntimeChildren; injected API rejection/throw; real Vite on self-owned HTML and real API siblings. Not full DevRuntime launcher/UI/signal end-to-end.',
      }, null, 2) + '\n');
      assert.equal(stopContext.process.exitCode, 1);
      assert.equal(calls.filter((value) => value === 'engine_shutdown').length, 1);
      assert.equal(calls.filter((value) => value === 'real_vite_force').length, 1, 'Owned workbench cleanup must still be attempted after API failure');
      assert(forceResult.exit && forceResult.ownership.verified);
      assert.equal(remaining.length, 0);
      assert.equal(closedPort, true);
      assert.deepEqual(siblingIdentityAfter, siblingIdentityBefore);
      assert.equal(mainStatus, 200);
      assert.equal(siblingStatus, 200);
      const stopped = JSON.parse(logs.find((value) => value.includes('dev_runtime_stopped')));
      assert.equal(stopped.api_cleanup_error, 'api_cleanup_failed');
      assert.equal(stopped.owned_cleanup_complete, false);
      assert.equal(stopped.classification, 'error');
      assert(!logs.join('\n').includes('T9 synthetic'), 'Arbitrary injected error text must not enter public log');
    } finally {
      if (owned && child.exitCode === null && child.signalCode === null) await owned.force();
      await cleanup(main);
      await cleanup(sibling);
      if (child) {
        await writeFile(path.join(directory, 'ViteStdout.txt'), rawOut);
        await writeFile(path.join(directory, 'ViteStderr.txt'), rawErr);
      }
      await main.save({ final_result: await main.host.shutdown() });
      await sibling.save({ final_result: await sibling.host.shutdown() });
    }
  });
}
