// Internal engine candidate: all source bytes are read from one exact Git commit.
import { spawn, spawnSync } from 'node:child_process';
import { readFile, writeFile, mkdir, copyFile, readdir, stat } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const args = process.argv.slice(2);
const get = (name) => { const i = args.indexOf(name); return i < 0 ? undefined : args[i + 1]; };
const commit = get('--commit');
const output = get('--output-dir');
const resourceManifest = get('--resource-manifest');
if (!/^[a-f0-9]{40}$/.test(commit || '') || !output || !path.isAbsolute(output) || !resourceManifest || !path.isAbsolute(resourceManifest)) throw new Error('Exact --commit, absolute --output-dir and --resource-manifest are required');
const git = (parameters) => {
  const result = spawnSync('git', ['-c', 'safe.directory=' + repo.replaceAll('\\', '/'), '-C', repo, ...parameters], { encoding: null, maxBuffer: 16 * 1024 * 1024, windowsHide: true, shell: false });
  if (result.status !== 0) throw new Error('Fixed commit Git extraction failed');
  return result.stdout;
};
const hash = (bytes) => createHash('sha256').update(bytes).digest('hex');
const sourcePaths = git(['ls-tree', '-r', '--name-only', commit, '--', 'services/engine/src', 'services/engine/migrations', 'services/engine/pyproject.toml', 'pyproject.toml', 'uv.lock', 'packaging/engine']).toString('utf8').trim().split('\n');
const stage = path.join(output, 'SourceStage');
const identities = [];
await mkdir(output, { recursive: true });
for (const name of sourcePaths) {
  if (!name || name.includes('..')) throw new Error('Unsafe fixed source path');
  const bytes = git(['show', commit + ':' + name]);
  const target = path.join(stage, name);
  await mkdir(path.dirname(target), { recursive: true });
  await writeFile(target, bytes);
  identities.push({ path: name, bytes: bytes.length, sha256: hash(bytes) });
}
const media = JSON.parse(await readFile(resourceManifest, 'utf8'));
const portable = { release: media.release, version: media.version, distribution: media.distribution, font_source: media.font.source, files: [] };
const resources = path.join(stage, 'Resources');
const putResource = async (source, relative, expectedBytes, expectedHash) => {
  const bytes = await readFile(source);
  if (bytes.length !== expectedBytes || hash(bytes) !== expectedHash) throw new Error('Pinned media resource differs: ' + relative);
  const target = path.join(resources, relative);
  await mkdir(path.dirname(target), { recursive: true }); await writeFile(target, bytes);
  portable.files.push({ path: relative.replaceAll('\\', '/'), bytes: bytes.length, sha256: hash(bytes) });
};
for (const item of media.files) await putResource(path.join(media.runtime_root, item.relative_path), 'Media/' + item.relative_path, item.bytes, item.sha256);
await putResource(media.font.path, 'Fonts/NotoSansCJKsc-Regular.otf', media.font.bytes, media.font.sha256);
const fontLicense = await readFile(media.font.license_path);
await putResource(media.font.license_path, 'Licenses/Noto-OFL.txt', fontLicense.length, media.font.license_sha256);
const ffmpegLicensePath = path.join(media.runtime_root, 'LICENSE.txt');
const ffmpegLicense = await readFile(ffmpegLicensePath);
await putResource(ffmpegLicensePath, 'Licenses/FFmpeg-GPL.txt', ffmpegLicense.length, media.release.license_sha256);
await mkdir(path.join(resources, 'Media'), { recursive: true });
await writeFile(path.join(resources, 'Media/manifest.json'), JSON.stringify(portable, null, 2) + '\n');
await mkdir(path.join(resources, 'Migrations'), { recursive: true });
for (const name of sourcePaths.filter((x) => x.startsWith('services/engine/migrations/') && x.endsWith('.sql'))) await copyFile(path.join(stage, name), path.join(resources, 'Migrations', path.basename(name)));
const python = process.env.VIDEO_CREATOR_PYTHON || path.join(repo, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const command = ['-X', 'utf8', '-m', 'PyInstaller', '--noconfirm', '--distpath', path.join(output, 'Dist'), '--workpath', path.join(output, 'Work'), path.join(stage, 'packaging/engine/Engine.spec')];
const receipt = { started_at: new Date().toISOString(), commit, scope: 'Internal CLI/API/framework candidate, not complete desktop application or release', source_files: identities, portable_resources: portable, python, command, exit_code: null, excluded_capabilities: ['Bundled isolated ASR interpreter/model not provisioned', 'Tauri application shell and installers not included', 'macOS and Linux not built or tested'] };
await writeFile(path.join(output, 'BuildReceipt.json'), JSON.stringify(receipt, null, 2) + '\n');
const child = spawn(python, command, { cwd: stage, env: { ...process.env, VIDEO_CREATOR_BUILD_STAGE: stage, PYTHONPATH: path.join(stage, 'services/engine/src'), PYTHONUTF8: '1', PYTHONIOENCODING: 'utf-8', OTEL_SDK_DISABLED: 'true', CREWAI_DISABLE_TELEMETRY: 'true', CREWAI_DISABLE_TRACKING: 'true' }, windowsHide: true, shell: false, stdio: 'inherit' });
const exit = await new Promise((resolve, reject) => { child.on('error', reject); child.on('exit', (code) => resolve(code ?? 1)); });
receipt.finished_at = new Date().toISOString(); receipt.exit_code = exit;
if (exit === 0) {
  const files = [];
  const scan = async (directory) => { for (const entry of await readdir(directory, { withFileTypes: true })) { const name = path.join(directory, entry.name); if (entry.isDirectory()) await scan(name); else { const bytes = await readFile(name); files.push({ path: path.relative(path.join(output, 'Dist'), name).replaceAll('\\', '/'), bytes: bytes.length, sha256: hash(bytes) }); } } };
  await scan(path.join(output, 'Dist')); receipt.artifact_files = files; receipt.artifact_bytes = files.reduce((sum, x) => sum + x.bytes, 0);
}
await writeFile(path.join(output, 'BuildReceipt.json'), JSON.stringify(receipt, null, 2) + '\n');
console.log(JSON.stringify({ event: 'engine_build_finished', commit, exit_code: exit, artifact_bytes: receipt.artifact_bytes ?? null }));
process.exitCode = exit;
