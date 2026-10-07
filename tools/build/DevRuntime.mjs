// Development host: tokens exist only in child process environment and memory.
import { spawn, spawnSync } from 'node:child_process';
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
const python = process.env.VIDEO_CREATOR_PYTHON || path.join(repo, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const token = randomBytes(32).toString('hex');
const origin = 'http://127.0.0.1:1420';
const env = { ...process.env, PYTHONPATH: path.join(repo, 'services/engine/src'), VIDEO_CREATOR_API_TOKEN: token, PYTHONUTF8: '1', PYTHONIOENCODING: 'utf-8' };
// This launcher never authorizes budget, registers routes, imports model keys, or starts a worker.
const mediaArgs = [];
const resourceManifest = process.env.VIDEO_CREATOR_RESOURCE_MANIFEST;
if (resourceManifest) {
  const manifest = JSON.parse(await readFile(resourceManifest, 'utf8'));
  const resourceRoot = await realpath(manifest.runtime_root);
  for (const file of manifest.files) {
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
await mkdir(dataDir, { recursive: true });
const engine = spawn(python, ['-m', 'video_creator.cli.main', 'serve', '--data-dir', dataDir, '--host', '127.0.0.1', '--port', '0', '--allowed-origin', origin, ...mediaArgs], { cwd: repo, env, stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true });
let vite;
let stopping = false;
const stopChild = (child) => {
  if (!child || child.exitCode !== null) return;
  if (process.platform === 'win32') {
    // Venv redirectors and Vite may own descendants; only this host's child trees.
    spawnSync(path.join(process.env.SystemRoot || 'C:/Windows', 'System32/taskkill.exe'), ['/PID', String(child.pid), '/T', '/F'], { stdio: 'ignore', shell: false, windowsHide: true });
  } else child.kill('SIGTERM');
};
const stop = () => { if (stopping) return; stopping = true; stopChild(vite); stopChild(engine); };
process.once('SIGINT', stop);
process.once('SIGTERM', stop);
process.once('exit', stop);
engine.on('error', () => { console.error(JSON.stringify({ event: 'failed', code: 'engine_spawn_failed' })); stop(); process.exitCode = 1; });
const ready = await new Promise((resolve, reject) => {
  let buffer = '';
  const timer = setTimeout(() => { stop(); reject(new Error('engine_ready_timeout')); }, 30000);
  engine.once('exit', () => { clearTimeout(timer); reject(new Error('engine_exited_before_ready')); });
  engine.stdout.on('data', (part) => {
    buffer += part.toString('utf8');
    if (buffer.length > 16384) { clearTimeout(timer); stop(); reject(new Error('engine_ready_invalid')); return; }
    const newline = buffer.indexOf('\n');
    if (newline < 0) return;
    try {
      const value = JSON.parse(buffer.slice(0, newline));
      const u = new URL(value.base_url);
      if (value.event !== 'ready' || u.protocol !== 'http:' || u.hostname !== '127.0.0.1' || !u.port || u.username || u.password || u.pathname !== '/' || u.search || u.hash || typeof value.instance_id !== 'string') throw new Error();
      clearTimeout(timer); resolve(value);
    } catch { clearTimeout(timer); stop(); reject(new Error('engine_ready_invalid')); }
  });
});
// Do not forward arbitrary engine stderr/stdout: diagnostics may contain application data.
engine.stderr.resume();
const require = createRequire(path.join(repo, 'apps/workbench/package.json'));
const viteCli = path.join(path.dirname(require.resolve('vite/package.json')), 'bin/vite.js');
vite = spawn(process.execPath, [viteCli, '--host', '127.0.0.1'], { cwd: path.join(repo, 'apps/workbench'), env: { ...env, VIDEO_CREATOR_ENGINE_URL: ready.base_url }, stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true });
vite.stdout.on('data', (data) => process.stdout.write(data));
vite.stderr.on('data', (data) => process.stderr.write(data));
vite.once('error', () => { console.error(JSON.stringify({ event: 'failed', code: 'workbench_spawn_failed' })); stop(); process.exitCode = 1; });
vite.once('exit', (code) => { stop(); process.exitCode = code ?? 1; });
engine.once('exit', (code) => { if (!stopping) { console.error(JSON.stringify({ event: 'failed', code: 'engine_exited' })); stop(); process.exitCode = code || 1; } });
console.log(JSON.stringify({ event: 'dev_runtime_ready', workbench_url: origin, instance_id: ready.instance_id, authentication: 'private_same_origin_proxy', paid_worker: false, media_resources_verified: mediaArgs.length === 4 }));
