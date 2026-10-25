import { createHash } from 'node:crypto';
import { existsSync, lstatSync, mkdirSync, readFileSync, realpathSync, writeFileSync } from 'node:fs';
import { dirname, isAbsolute, join, relative, resolve } from 'node:path';

const PATCH_ID = 'KimiBuiltinIsolationV1';
const CLI_COMMIT = '92ce7ca53fb6edce2eb295304e7a5ce207f7062c';
const marker = '# Modified by VideoCreator on 2026-10-10: KimiBuiltinIsolationV1 (ADR0035).\n';
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
const gitBlob = bytes => createHash('sha1').update(`blob ${bytes.length}\0`).update(bytes).digest('hex');
const patches = [
  {
    path: 'src/kimi_cli/config.py',
    before_sha256: '77802fce6b65addf061e1607e04de0646ffa06d1d4c38d807a4cff6635a791c9',
    before_blob: '451f4681000aaeede5d80c88d12c95042138bc43',
    edits: [[
      '    extra_skill_dirs: list[str] = Field(\n',
      '    include_builtin_skills: bool = Field(\n' +
      '        default=True,\n' +
      '        strict=True,\n' +
      '        description="Include built-in skills in discovery (VideoCreator isolation control)",\n' +
      '    )\n' +
      '    extra_skill_dirs: list[str] = Field(\n',
    ]],
  },
  {
    path: 'src/kimi_cli/skill/__init__.py',
    before_sha256: '887dfc32fd076ef1a6b0d1beeadc26f6c8db2ca7b253227bd6881afdbcbb36f8',
    before_blob: '67e35052263dd5bdf0650594692e6c56066b7257',
    edits: [
      ['    extra_skill_dirs: Sequence[str] | None = None,\n) -> list[ScopedSkillsRoot]:\n',
       '    extra_skill_dirs: Sequence[str] | None = None,\n    include_builtin_skills: bool = True,\n) -> list[ScopedSkillsRoot]:\n'],
      ['    from kimi_cli.plugin.manager import get_plugins_dir\n    from kimi_cli.utils.path import find_project_root\n',
       '    if type(include_builtin_skills) is not bool:\n' +
       '        raise TypeError("include_builtin_skills must be a bool")\n\n' +
       '    from kimi_cli.plugin.manager import get_plugins_dir\n    from kimi_cli.utils.path import find_project_root\n'],
      ['    if _supports_builtin_skills():\n',
       '    if include_builtin_skills and _supports_builtin_skills():\n'],
    ],
  },
  {
    path: 'src/kimi_cli/soul/agent.py',
    before_sha256: '47d4d2cada5bc00e3330c46f03cf4f91d020316323395ff2251d0176ac33500a',
    before_blob: 'a208e08796a5dd2f516f1ffff6d0b046b20cdd13',
    edits: [[
      '            extra_skill_dirs=config.extra_skill_dirs or None,\n',
      '            extra_skill_dirs=config.extra_skill_dirs or None,\n' +
      '            include_builtin_skills=config.include_builtin_skills,\n',
    ]],
  },
];
const licences = [
  ['LICENSE', '58d1e17ffe5109a7ae296caafcadfdbe6a7d176f0bc4ab01e12a689b0499d8bd'],
  ['NOTICE', '6bdd9ca6fd120dcd6ba5e16bf2bacc01f42781fd2d9754ec934c5db05fcdc395'],
];

function checkedSource(root, name) {
  const path = join(root, name);
  for (let current = path; current !== root; current = dirname(current)) {
    if (lstatSync(current).isSymbolicLink()) throw new Error('source_symlink_rejected');
  }
  if (relative(root, realpathSync(path)).startsWith('..')) throw new Error('source_outside_root');
  return readFileSync(path);
}

function oneEdit(text, before, after) {
  const first = text.indexOf(before);
  if (first < 0 || text.indexOf(before, first + before.length) >= 0) throw new Error('patch_anchor_not_unique');
  return text.slice(0, first) + after + text.slice(first + before.length);
}

function diff(name, before, after) {
  const oldLines = before.split('\n');
  const newLines = after.split('\n');
  let prefix = 0;
  while (prefix < oldLines.length && prefix < newLines.length && oldLines[prefix] === newLines[prefix]) prefix++;
  let suffix = 0;
  while (suffix < oldLines.length - prefix && suffix < newLines.length - prefix &&
         oldLines[oldLines.length - 1 - suffix] === newLines[newLines.length - 1 - suffix]) suffix++;
  const removed = oldLines.slice(prefix, oldLines.length - suffix);
  const added = newLines.slice(prefix, newLines.length - suffix);
  return `--- a/${name}\n+++ b/${name}\n@@ -${prefix + 1},${removed.length} +${prefix + 1},${added.length} @@\n` +
    removed.map(line => `-${line}\n`).join('') + added.map(line => `+${line}\n`).join('');
}

export function patchBuiltinIsolation(sourceRoot, outputRoot) {
  if (!isAbsolute(sourceRoot) || !isAbsolute(outputRoot)) throw new Error('absolute_paths_required');
  const source = realpathSync(sourceRoot);
  const output = resolve(outputRoot);
  if (existsSync(output)) throw new Error('fresh_output_required');
  if (lstatSync(dirname(output)).isSymbolicLink()) throw new Error('output_parent_symlink_rejected');
  const decoded = new TextDecoder('utf-8', { fatal: true });
  const files = patches.map(patch => {
    const original = checkedSource(source, patch.path);
    if (sha256(original) !== patch.before_sha256 || gitBlob(original) !== patch.before_blob) throw new Error('upstream_source_identity_mismatch');
    const before = decoded.decode(original);
    if (before.includes('\r')) throw new Error('unexpected_source_line_endings');
    let after = before;
    for (const [oldText, newText] of patch.edits) after = oneEdit(after, oldText, newText);
    after = marker + after;
    return { patch, original, before, after, bytes: Buffer.from(after, 'utf8') };
  });
  const licenceBodies = licences.map(([name, expected]) => {
    const bytes = checkedSource(source, name);
    if (sha256(bytes) !== expected) throw new Error('upstream_license_identity_mismatch');
    return { name, bytes, sha256: expected };
  });
  mkdirSync(output);
  for (const file of files) {
    mkdirSync(dirname(join(output, file.patch.path)), { recursive: true });
    writeFileSync(join(output, file.patch.path), file.bytes, { flag: 'wx' });
  }
  for (const file of licenceBodies) writeFileSync(join(output, file.name), file.bytes, { flag: 'wx' });
  const patchText = files.map(file => diff(file.patch.path, file.before, file.after)).join('');
  writeFileSync(join(output, `${PATCH_ID}.patch`), patchText, { encoding: 'utf8', flag: 'wx' });
  const record = {
    patch_id: PATCH_ID, upstream_cli_commit: CLI_COMMIT, upstream_cli_version: '1.45.0',
    proposed_distribution_version: '1.45.0+videocreator.1', distribution_metadata_modified: false,
    sdk_version: '0.0.6', kosong_version: '0.53.0', source_slice_only: true,
    full_cli_source_tree_verified: false, production_dependency_lock_complete: false,
    runtime_executed: false, artifact_built: false,
    files: files.map(file => ({ path: file.patch.path, before_sha256: file.patch.before_sha256,
      before_git_blob: file.patch.before_blob, before_bytes: file.original.length,
      after_sha256: sha256(file.bytes), after_bytes: file.bytes.length })),
    licences: licenceBodies.map(file => ({ path: file.name, sha256: file.sha256, bytes: file.bytes.length })),
    diff_sha256: sha256(Buffer.from(patchText)),
  };
  writeFileSync(join(output, 'PatchManifest.json'), JSON.stringify(record, null, 2) + '\n', { flag: 'wx' });
  return record;
}

if (process.argv[1] && realpathSync(process.argv[1]) === realpathSync(new URL(import.meta.url))) {
  try {
    if (process.argv.length !== 4) throw new Error('usage_source_root_output_root');
    console.log(JSON.stringify(patchBuiltinIsolation(process.argv[2], process.argv[3])));
  } catch (error) {
    console.error(error instanceof Error ? error.message : 'patch_failed');
    process.exitCode = 1;
  }
}
