import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { assertFailedCleanup, assertNormal, caseRoot, cleanup, directory, identity, jsonResponse,
  metadata, pinFiles, repo, sleep, start, waveSignal, writeReceipt } from './t7_node_helpers.mjs';

const manifestFile = path.resolve(repo, '../../Codex/VideoCreatorImplementation/Integration/Evidence/MediaRuntimeManifest.json');
const manifest = JSON.parse(await readFile(manifestFile, 'utf8'));
const mediaArgs = ['--ffmpeg', manifest.ffmpeg_path, '--ffprobe', manifest.ffprobe_path];
const runtimeFiles = [process.execPath, manifestFile, ...manifest.files.map((row) => path.join(manifest.runtime_root, row.relative_path))];
let resourceBefore;
let protectedBefore;

before(async () => {
  resourceBefore = await pinFiles(runtimeFiles);
  for (const row of manifest.files) assert.equal(resourceBefore[path.join(manifest.runtime_root, row.relative_path)], row.sha256);
  protectedBefore = await metadata([22508]);
  await writeReceipt('InputsBefore', { case_root: caseRoot, runtime_sha256_before: resourceBefore,
    legacy22508_before: protectedBefore, provider_calls: 0, real_key_reads: 0 });
});

after(async () => {
  const resourceAfter = await pinFiles(runtimeFiles);
  const protectedAfter = await metadata([22508]);
  await writeReceipt('InputsAfter', { runtime_sha256_before: resourceBefore, runtime_sha256_after: resourceAfter,
    legacy22508_before: protectedBefore, legacy22508_after: protectedAfter,
    legacy_protection_status: protectedBefore.length ? 'actual_creation_identity_compared' : 'not_present_before_not_claimed',
    scope: 'No legacy host restart or signal, exact runtime bytes; no JobObject/parent-crash claim' });
  assert.deepEqual(resourceAfter, resourceBefore);
  assert.deepEqual(protectedAfter, protectedBefore);
});

test('actual Node host normal stop and same-instance UTF8/decoded-audio restart', { timeout: 90000 }, async () => {
  const dataDir = path.join(await directory('NormalRestartData'), 'Instance Chinese 空格');
  const first = await start('NormalFirst', { dataDir, mediaArgs });
  const wave = waveSignal();
  let firstReady;
  let project;
  let asset;
  try {
    firstReady = await first.host.ready;
    const health = await jsonResponse(await first.request('/api/v1/health'), 200);
    assert.equal(health.worker_connected, false);
    project = await jsonResponse(await first.request('/api/v1/projects', { method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Idempotency-Key': 'T7-real-owned' },
      body: JSON.stringify({ name: 'T7 本地中文项目与空格', goal: '真实持久，不是模型作品' }) }), 201);
    const staged = await jsonResponse(await first.request('/api/v1/assets/staging', { method: 'POST',
      headers: { 'Content-Type': 'audio/wav' }, body: wave }), 201);
    asset = await jsonResponse(await first.request('/api/v1/assets/import', { method: 'POST',
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...staged,
        source: 'self-created-T7-audio-signal', rights: 'owned' }) }), 201);
    assert.equal(asset.probe.decoded, true);
    const result = await first.host.shutdown();
    await first.save({ ready: firstReady, project, asset, result, actual_media_signal: true });
    await assertNormal(first, result);
  } finally { await cleanup(first); }
  const second = await start('NormalSecond', { dataDir, mediaArgs });
  try {
    const ready = await second.host.ready;
    assert.equal(ready.instance_id, firstReady.instance_id);
    const persisted = await jsonResponse(await second.request('/api/v1/projects/' + project.project_id), 200);
    assert.deepEqual(persisted, project);
    const response = await second.request('/api/v1/assets/' + asset.asset_id + '/content');
    assert.equal(response.status, 200);
    assert.deepEqual(Buffer.from(await response.arrayBuffer()), wave);
    const result = await second.host.shutdown();
    await second.save({ ready, persisted_project: persisted, persisted_audio_exact: true, result });
    await assertNormal(second, result);
  } finally { await cleanup(second); }
});

for (const mode of ['eof', 'pipe-loss', 'default']) {
  test('actual Node host ' + mode + ' stays API-live then explicitly forced, never normal', { timeout: 60000 }, async () => {
    const run = await start({ eof: 'EofNegative', 'pipe-loss': 'PipeLossNegative', default: 'DefaultNegative' }[mode], { controlled: mode !== 'default' });
    try {
      const ready = await run.host.ready;
      if (mode === 'eof') run.host.disconnectControl();
      if (mode === 'pipe-loss') run.host.child.stdin.destroy();
      if (mode === 'default') await new Promise((resolve, reject) => run.host.child.stdin.write(Buffer.from('shutdown\n', 'ascii'), (error) => error ? reject(error) : resolve()));
      await sleep(150);
      const health = await jsonResponse(await run.request('/api/v1/health'), 200);
      const liveBefore = await metadata([run.host.child.pid]);
      assert.equal(liveBefore.length, 1);
      const began = performance.now();
      const result = await run.host.shutdown();
      const elapsedMs = performance.now() - began;
      await run.save({ ready, mode, health_before_shutdown: health, actual_root_before: liveBefore,
        shutdown_elapsed_ms: elapsedMs, result });
      await assertFailedCleanup(run, result, 'forced');
      assert.equal(result.exit.code, 1);
      assert.equal(result.exit.signal, null);
      assert.equal(result.marker_count, 0);
      assert.equal(result.port_closed, true);
      if (mode === 'default') { assert(result.frame_sent); assert(elapsedMs >= 15000); }
      else assert.equal(result.frame_sent, false);
      assert(result.fallback.actions.some((action) => action.tool_exit_code === 0));
    } finally { await cleanup(run); }
  });
}

test('actual Node host missing session fails before ready and preserves nonzero close', { timeout: 30000 }, async () => {
  const run = await start('MissingTokenNegative', { tokenPresent: false });
  try {
    await assert.rejects(run.host.ready, /engine_exited_before_ready/);
    const result = await run.host.shutdown();
    await run.save({ result, startup_failed: true, stdout_empty: run.output.stdout.length === 0 });
    await assertFailedCleanup(run, result, 'error');
    assert.equal(result.exit.code, 1);
    assert.equal(result.marker_count, 0);
    assert.equal(run.output.stdout, '');
    assert.equal(result.port_closed, null);
    assert.equal(result.fallback.actions.length, 0);
  } finally { await cleanup(run); }
});

test('actual Node spawn failure preserves failed close and has no invented PID/ready', { timeout: 30000 }, async () => {
  const run = await start('MissingExecutableNegative', { executable: path.join(await directory('AbsentBinary'), 'T7DoesNotExist.exe') });
  try {
    await assert.rejects(run.host.ready, /engine_spawn_failed|engine_exited_before_ready/);
    const result = await run.host.shutdown();
    await run.save({ result, startup_failed: true, spawned_pid: run.host.child.pid ?? null });
    await assertFailedCleanup(run, result, 'error');
    assert.notEqual(result.exit.code, 0);
    assert.equal(result.marker_count, 0);
    assert.equal(result.ownership.captured.length, 0);
    assert.equal(result.fallback.actions.length, 0);
    assert.equal(run.output.stdout, '');
  } finally { await cleanup(run); }
});

test('force targets captured creation identities and protects a real sibling API', { timeout: 60000 }, async () => {
  const victim = await start('ForceOwnTree');
  const sibling = await start('SiblingProtected');
  try {
    const victimReady = await victim.host.ready;
    const siblingReady = await sibling.host.ready;
    const siblingBefore = await metadata([sibling.host.child.pid]);
    const victimBefore = await metadata([victim.host.child.pid]);
    assert.equal(siblingBefore.length, 1);
    assert.equal(victimBefore.length, 1);
    victim.host.disconnectControl();
    await sleep(150);
    assert.equal((await victim.request('/api/v1/health')).status, 200);
    const result = await victim.host.shutdown();
    const siblingAfter = await metadata([sibling.host.child.pid]);
    assert.deepEqual(siblingAfter, siblingBefore);
    assert.equal((await sibling.request('/api/v1/health')).status, 200);
    const captured = new Set(result.ownership.captured.map(identity));
    assert(captured.has(identity(victimBefore[0])));
    assert(!captured.has(identity(siblingBefore[0])));
    assert(result.ownership.captured.some((row) => row.parent_pid === victim.host.child.pid), 'Measure the real .venv Python descendant');
    const capturedPids = new Set(result.ownership.captured.map((row) => row.pid));
    for (const action of result.fallback.actions) assert(capturedPids.has(action.pid));
    await victim.save({ ready: victimReady, victim_before: victimBefore, result, sibling_before: siblingBefore, sibling_after: siblingAfter });
    await assertFailedCleanup(victim, result, 'forced');
    const siblingResult = await sibling.host.shutdown();
    await sibling.save({ ready: siblingReady, sibling_before: siblingBefore, sibling_after: siblingAfter, result: siblingResult });
    await assertNormal(sibling, siblingResult);
  } finally { await cleanup(victim); await cleanup(sibling); }
});

for (const mode of ['crlf', 'spaced', 'extra', 'duplicate', 'partial', 'long-suffix', 'prefixed']) {
  test('controlled marker bytes ' + mode + ' cannot turn real close0 into host normal', { timeout: 30000 }, async () => {
    const names = { crlf: 'MarkerCrlf', spaced: 'MarkerSpaced', extra: 'MarkerExtra', duplicate: 'MarkerDuplicate',
      partial: 'MarkerPartial', 'long-suffix': 'MarkerLongSuffix', prefixed: 'MarkerPrefixed' };
    const run = await start(names[mode], { markerMode: mode });
    try {
      const ready = await run.host.ready;
      assert.equal((await run.request('/api/v1/health')).status, 200);
      const result = await run.host.shutdown();
      await run.save({ ready, mode, result, injected_marker_transport_only: true,
        scope_override: 'Actual Python/API cleanup with test-only stderr byte alteration; not natural backend failure' });
      await assertFailedCleanup(run, result, 'error');
      assert.deepEqual(result.exit, { code: 0, signal: null });
      assert.equal(result.port_closed, true);
      assert.equal(result.marker_count, mode === 'duplicate' ? 2 : 0);
      assert.equal(result.fallback.actions.length, 0);
    } finally { await cleanup(run); }
  });
}

test('controlled exact LF marker split across pipe writes remains one real normal stop', { timeout: 30000 }, async () => {
  const run = await start('MarkerSplit', { markerMode: 'split' });
  try {
    const ready = await run.host.ready;
    const result = await run.host.shutdown();
    await run.save({ ready, result, injected_marker_transport_only: true,
      scope_override: 'Exact production marker bytes preserved; two writes not guaranteed two OS data events' });
    await assertNormal(run, result);
  } finally { await cleanup(run); }
});
