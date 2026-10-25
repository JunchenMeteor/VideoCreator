"""Trace the one backend CLI exporter; never maintain a second contract model."""
from __future__ import annotations
import hashlib
import argparse
import importlib.machinery
import importlib.metadata
import importlib.util
import json
import runpy
import sys
from pathlib import Path

WRAPPER = Path(__file__).resolve()
REPO = WRAPPER.parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('output', type=Path)
parser.add_argument('--source-snapshot', type=Path)
parser.add_argument('--dependency-root', type=Path)
parser.add_argument('--skip-native-file-observation', action='store_true',
                    help='Record module files only; leave explicit Windows DLL observation unperformed')
args = parser.parse_args()
OUTPUT = args.output.resolve()
SOURCE = REPO / 'services/engine/src'
records, denied, audited_reads, native_loaded = {}, [], {}, {}
snapshot_identity, snapshot_sources, module_sources, namespaces = None, {}, {}, {}
if args.dependency_root:
    dependency_root = args.dependency_root.resolve()
    if dependency_root != (REPO / '.venv/Lib/site-packages').resolve():
        raise ValueError('Unrecognized exporter dependency root')
    sys.path.append(str(dependency_root))
sys.path.insert(0, str(SOURCE))

def identity(path):
    path = Path(path).resolve()
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'path': path.as_posix(), 'bytes': path.stat().st_size, 'sha256': digest}

if args.source_snapshot:
    if not sys.flags.isolated or not sys.flags.no_site:
        raise ValueError('Snapshot export requires isolated no-site Python')
    if not args.dependency_root:
        raise ValueError('Snapshot export requires an explicit dependency root')
    snapshot_path = args.source_snapshot.resolve()
    snapshot_identity = identity(snapshot_path)
    snapshot = json.loads(snapshot_path.read_text(encoding='utf-8'))
    SOURCE = snapshot_path.parent / 'FinalSourceCopies/services/engine/src'
    sys.path[0] = str(SOURCE)
    for relative, item in snapshot['source_map'].items():
        if not relative.startswith('services/engine/') or '..' in Path(relative).parts:
            raise ValueError('Invalid source identity')
        file = Path(item['ordinary_copy']).resolve()
        expected = (snapshot_path.parent / 'FinalSourceCopies' / relative).resolve()
        if file != expected:
            raise ValueError('Ordinary source location is not declared')
        current = file
        while current != snapshot_path.parent:
            if current.is_symlink() or current.is_junction():
                raise ValueError('Linked ordinary input')
            current = current.parent
        before = identity(file)
        if before['sha256'] != item['sha256'] or before['bytes'] != item['size']:
            raise ValueError('Ordinary source bytes differ: ' + relative)
        snapshot_sources[relative] = {'before_export': before}
        if relative.startswith('services/engine/src/') and relative.endswith('.py'):
            parts = Path(relative.removeprefix('services/engine/src/')).with_suffix('').parts
            package = parts[-1] == '__init__'
            fullname = '.'.join(parts[:-1] if package else parts)
            if fullname in module_sources:
                raise ValueError('Duplicate engine module')
            module_sources[fullname] = (file, package)
            for count in range(1, len(parts)):
                parent = '.'.join(parts[:count])
                namespaces[parent] = SOURCE.joinpath(*parts[:count])
    namespaces = {key: value for key, value in namespaces.items() if key not in module_sources}

    auditing = False
    read_roots = (SOURCE, SOURCE.parent / 'migrations', Path(sys.base_prefix).resolve(), dependency_root)

    def audit(event, values):
        # A tracing boundary for this pure exporter, not a native execution sandbox.
        global auditing
        if event in ('socket.connect', 'socket.bind', 'subprocess.Popen', 'os.system'):
            raise RuntimeError('Pure exporter attempted a runtime side effect: ' + event)
        if event != 'open' or auditing or not values or not isinstance(values[0], (str, bytes)):
            return
        file = Path(values[0].decode(sys.getfilesystemencoding()) if isinstance(values[0], bytes) else values[0]).resolve()
        mode, flags = values[1:3]
        writing = (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (isinstance(flags, int) and bool(flags & 3))
        if writing:
            if not file.is_relative_to(OUTPUT):
                raise RuntimeError('Exporter attempted writing outside its output')
            return
        allowed = file == WRAPPER or file == snapshot_path or file == Path(sys.executable).resolve() or file.is_relative_to(OUTPUT) or any(file.is_relative_to(root) for root in read_roots)
        if not allowed:
            raise RuntimeError('Exporter attempted an undeclared read: ' + file.as_posix())
        if file.is_file():
            auditing = True
            try:
                audited_reads[file.as_posix()] = identity(file)
            finally:
                auditing = False

    sys.addaudithook(audit)

class OrdinarySourceLoader(importlib.machinery.SourceFileLoader):
    def get_code(self, fullname):
        file, _ = module_sources[fullname]
        source = file.read_bytes()
        before = identity(file)
        expected = snapshot_sources['services/engine/src/' + file.relative_to(SOURCE).as_posix()]['before_export']
        if before != expected or hashlib.sha256(source).hexdigest() != before['sha256']:
            raise ImportError('Ordinary input changed before compile: ' + fullname)
        records[fullname] = {'before_source_read': before}
        return compile(source, str(file), 'exec', dont_inherit=True)

class ExportSourceGuard:
    def find_spec(self, fullname, path=None, target=None):
        if fullname != 'video_creator' and not fullname.startswith('video_creator.'):
            return None
        if any(fullname == f'video_creator.{name}' or fullname.startswith(f'video_creator.{name}.') for name in ('media', 'providers', 'workflows')):
            denied.append(fullname)
            raise ImportError('Pure contract export attempted unrelated runtime source: ' + fullname)
        if snapshot_identity:
            if fullname in module_sources:
                file, package = module_sources[fullname]
                return importlib.util.spec_from_file_location(fullname, file, loader=OrdinarySourceLoader(fullname, str(file)), submodule_search_locations=[str(file.parent)] if package else None)
            if fullname in namespaces:
                spec = importlib.machinery.ModuleSpec(fullname, None, is_package=True)
                spec.submodule_search_locations = [str(namespaces[fullname])]
                return spec
            denied.append(fullname)
            raise ImportError('Pure export requested an unlisted ordinary module: ' + fullname)
        spec = importlib.machinery.PathFinder.find_spec(fullname, path)
        if spec and spec.origin and spec.origin.endswith('.py'):
            file = Path(spec.origin).resolve()
            if not file.is_relative_to(SOURCE):
                raise ImportError('Engine export source resolved outside the repository')
            records[fullname] = {'before_source_read': identity(file)}
        return spec

def finish():
    for item in records.values():
        item['after_export'] = identity(item['before_source_read']['path'])
        item['changed'] = item['before_source_read'] != item['after_export']
    third_party = {}
    for module in tuple(sys.modules.values()):
        origin = getattr(module, '__file__', None)
        if origin and Path(origin).is_file() and (Path(origin).resolve().is_relative_to(Path(sys.base_prefix).resolve()) or (args.dependency_root and Path(origin).resolve().is_relative_to(dependency_root))):
            third_party[str(Path(origin).resolve())] = identity(origin)
    packages = sorted([{'name': item.metadata['Name'], 'version': item.version} for item in importlib.metadata.distributions()], key=lambda item: item['name'].casefold())
    for item in snapshot_sources.values():
        item['after_export'] = identity(item['before_export']['path'])
        item['changed'] = item['before_export'] != item['after_export']
    if snapshot_identity and identity(snapshot_identity['path']) != snapshot_identity:
        raise RuntimeError('Source snapshot changed')
    if sys.platform == 'win32' and not args.skip_native_file_observation:
        import ctypes
        from ctypes import wintypes
        # Observation only. This does not qualify loaded DLLs or future native requests.
        kernel = ctypes.WinDLL(str(Path('C:/Windows/System32/kernel32.dll')), use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        kernel.K32EnumProcessModules.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.HMODULE), wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
        kernel.K32GetModuleFileNameExW.argtypes = [wintypes.HANDLE, wintypes.HMODULE, wintypes.LPWSTR, wintypes.DWORD]
        process = kernel.GetCurrentProcess()
        modules = (wintypes.HMODULE * 2048)()
        needed = wintypes.DWORD()
        if not kernel.K32EnumProcessModules(process, modules, ctypes.sizeof(modules), ctypes.byref(needed)) or needed.value > ctypes.sizeof(modules):
            raise RuntimeError('Export DLL origin observation failed')
        for module in modules[:needed.value // ctypes.sizeof(wintypes.HMODULE)]:
            name = ctypes.create_unicode_buffer(32768)
            if not kernel.K32GetModuleFileNameExW(process, module, name, len(name)):
                raise RuntimeError('Export DLL origin unavailable')
            auditing_before = auditing if snapshot_identity else False
            if snapshot_identity:
                globals()['auditing'] = True
            try:
                native_loaded[name.value] = identity(name.value)
            finally:
                if snapshot_identity:
                    globals()['auditing'] = auditing_before
    for module in tuple(sys.modules.values()):
        origin = getattr(module, '__file__', None)
        if origin and Path(origin).is_file() and (Path(origin).resolve().is_relative_to(Path(sys.base_prefix).resolve()) or (args.dependency_root and Path(origin).resolve().is_relative_to(dependency_root))):
            third_party[str(Path(origin).resolve())] = identity(origin)
    report = {'entry': 'video_creator.cli.main export-contracts', 'engine_source_reads': records,
              'denied_runtime_imports': denied, 'source_changes': any(item['changed'] for item in records.values()),
              'python': identity(sys.executable), 'python_version': sys.version, 'prefix': sys.prefix, 'base_prefix': sys.base_prefix,
              'loaded_environment_file_identity': third_party, 'installed_distribution_versions': packages,
              'wrapper': identity(WRAPPER), 'source_mode': 'formal_ordinary_snapshot' if snapshot_identity else 'repository',
              'source_snapshot': snapshot_identity, 'snapshot_source_identity': snapshot_sources,
              'snapshot_source_changes': any(item['changed'] for item in snapshot_sources.values()),
              'audited_read_identity': audited_reads, 'loaded_native_file_identity': native_loaded,
              'native_file_observation_performed': sys.platform == 'win32' and not args.skip_native_file_observation,
              'native_file_observation_mode': 'not_observed' if args.skip_native_file_observation else 'default_platform_observation',
              'scope': 'Actual pure exporter source resolution, Python open observations and loaded environment file origins plus explicitly selected native observation; not full OS syscall audit, portable loading or native qualification'}
    (OUTPUT / 'export.sources.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')

sys.meta_path.insert(0, ExportSourceGuard())
sys.argv = ['video-creator-engine', 'export-contracts', '--output-dir', str(OUTPUT)]
try:
    runpy.run_module('video_creator.cli.main', run_name='__main__', alter_sys=True)
finally:
    # Trace failure is a real failure, never an ignored atexit diagnostic.
    finish()
