import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';

test('isolated actual DevRuntime stop callback must attempt owned workbench cleanup after engine rejection', async () => {
  const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
  const sourcePath = path.join(repo, 'tools/build/DevRuntime.mjs');
  const bytes = await readFile(sourcePath);
  const sha256 = (data) => createHash('sha256').update(data).digest('hex');
  assert.equal(sha256(bytes), 'd900d689d960ade8f3c13bc9f495922f3890436bd58a03752f8a5dd44a4898c5');
  const source = bytes.toString('utf8');
  const begin = source.indexOf('const stop = (cause, abnormal = false) => {');
  const end = source.indexOf("\nprocess.once('SIGINT'", begin);
  assert(begin >= 0 && end > begin, 'Exact current callback boundaries must exist');
  const actualCallbackSource = source.slice(begin, end);
  const calls = [];
  const logs = [];
  const context = {
    stopping: undefined,
    engine: { shutdown: async () => {
      calls.push('engine_shutdown');
      throw new Error('Synthetic isolated CIM-recheck rejection; no OS request or secret');
    } },
    viteOwned: { force: async () => { calls.push('simulated_vite_force'); return {}; } },
    process: { exitCode: 0 },
    console: { log: (value) => logs.push(value), error: (value) => logs.push(value) },
  };
  // Execute the fixed production callback only. No launcher imports, real Vite, ports or processes.
  const stop = new vm.Script("'use strict';\n" + actualCallbackSource + '\nstop;', {
    filename: sourcePath + ':T7IsolatedStopCallback',
  }).runInNewContext(context);
  await stop('T7-isolated-engine-rejection', true);
  const directory = path.join(process.env.VIDEO_CREATOR_T7_CASES, 'RejectedEngineBranch');
  await mkdir(directory, { recursive: true });
  await writeFile(path.join(directory, 'T7Receipt.json'), JSON.stringify({
    source_path: sourcePath, source_sha256: sha256(bytes),
    callback_character_start: begin, callback_character_end: end,
    exact_callback_sha256: sha256(actualCallbackSource), actual_callback_source: actualCallbackSource,
    injected_engine_rejection: true, calls, logs, isolated_exit_code: context.process.exitCode,
    expected_simulated_owned_cleanup_calls: 1,
    actual_simulated_owned_cleanup_calls: calls.filter((value) => value === 'simulated_vite_force').length,
    actual_vite_started: false, actual_os_cleanup_or_residue_claim: false,
    provider_calls: 0, real_key_reads: 0,
    scope: 'Source-bound isolated DevRuntime callback execution with injected engine rejection and simulated cleanup counter only',
  }, null, 2) + '\n', 'utf8');
  assert.equal(context.process.exitCode, 1);
  assert(calls.includes('engine_shutdown'));
  assert.equal(calls.filter((value) => value === 'simulated_vite_force').length, 1,
    'Owned workbench cleanup must be attempted even when engine cleanup rejects');
});
