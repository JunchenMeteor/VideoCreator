import assert from 'node:assert/strict';
import { test } from 'node:test';
import { randomBytes } from 'node:crypto';
import path from 'node:path';
import { launchEngine } from '../../tools/build/EngineProcess.mjs';
import { directory, metadata, python, repo, safeEnvironment, writeReceipt } from './t7_node_helpers.mjs';

test('CIM lookup failure must never verify an uncaptured tree or classify actual close0 as normal', { timeout: 30000 }, async () => {
  const folder = await directory('CimLookupUnavailable');
  const realRoot = process.env.SystemRoot;
  const token = randomBytes(32).toString('hex');
  const env = { ...safeEnvironment(), VIDEO_CREATOR_API_TOKEN: token };
  const fakeRoot = path.join(folder, 'AbsentLookupRoot');
  let host;
  let stdout = '';
  let stderr = '';
  try {
    // Only this owned Node process lookup changes. Python receives the real OS environment.
    process.env.SystemRoot = fakeRoot;
    host = launchEngine({ repo, executable: python, dataDir: path.join(folder, 'Instance'), env });
    host.child.stdout.on('data', (bytes) => { stdout += bytes.toString('utf8'); });
    host.child.stderr.on('data', (bytes) => { stderr += bytes.toString('utf8'); });
    const ready = await host.ready;
    const health = await fetch(ready.base_url + '/api/v1/health', { headers: { Authorization: 'Bearer ' + token }, signal: AbortSignal.timeout(5000) });
    assert.equal(health.status, 200);
    process.env.SystemRoot = realRoot;
    const independentlyLive = await metadata([host.child.pid]);
    assert.equal(independentlyLive.length, 1);
    process.env.SystemRoot = fakeRoot;
    const result = await host.shutdown();
    process.env.SystemRoot = realRoot;
    const independentlyAbsent = await metadata([host.child.pid]);
    await writeReceipt('CimLookupUnavailable', { mode: 'Node-only absent process-inspector lookup',
      fake_lookup_root: fakeRoot, ready, api_health_status: health.status,
      independently_live_root: independentlyLive, independently_absent_root: independentlyAbsent,
      actual_result: result, stdout: stdout.replaceAll(token, '[test-session-redacted]'),
      stderr: stderr.replaceAll(token, '[test-session-redacted]'),
      session_token_present_in_output: stdout.includes(token) || stderr.includes(token),
      provider_calls: 0, real_key_reads: 0,
      scope: 'Actual Node launch/HTTP/Python normal cleanup; controlled CIM executable lookup failure. No JobObject or worker claim.' });
    assert.equal(independentlyAbsent.length, 0);
    assert.deepEqual(result.exit, { code: 0, signal: null });
    assert.equal(result.marker_count, 1);
    assert.equal(result.port_closed, true);
    assert.equal(result.ownership.inspection_error, 'owned_inspection_failed');
    assert.equal(result.ownership.captured.length, 0);
    assert.equal(result.classification, 'error', 'Failed ownership inspection is not a normal cleanup proof');
    assert.equal(result.ownership.verified, false);
  } finally {
    if (realRoot === undefined) delete process.env.SystemRoot;
    else process.env.SystemRoot = realRoot;
    if (host) await host.shutdown();
  }
});
