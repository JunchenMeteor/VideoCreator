"""Indexed source/metadata/data/native loading for a host-held candidate resource.

This is a loading policy, not a sandbox for arbitrary trusted native code. The
native host must authenticate and retain the complete installation before boot.
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import threading
import types


class LoadingError(ImportError):
    pass


def strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise LoadingError('load_policy_duplicate_key')
        result[key] = value
    return result


def load_document(raw):
    return json.loads(raw.decode('utf-8', errors='strict'), object_pairs_hook=strict_object,
                      parse_constant=lambda _: (_ for _ in ()).throw(LoadingError('load_policy_nonfinite')))


def digest(raw):
    # The exact CPython build must supply this builtin; never search a DLL path
    # for a crypto helper before the indexed finder/native guard exists.
    if importlib.machinery.BuiltinImporter.find_spec('_sha2') is None:
        raise LoadingError('bootstrap_hash_builtin_unavailable')
    primitive = importlib.machinery.BuiltinImporter
    if '_sha2' not in sys.modules:
        spec = primitive.find_spec('_sha2')
        module = importlib.util.module_from_spec(spec)
        primitive.exec_module(module)
        sys.modules['_sha2'] = module
    return sys.modules['_sha2'].sha256(raw).hexdigest()


def relative(value):
    if not isinstance(value, str) or not value or '\\' in value or ':' in value:
        raise LoadingError('indexed_path_invalid')
    path = Path(value)
    if path.is_absolute() or any(part in ('', '.', '..') for part in path.parts):
        raise LoadingError('indexed_path_invalid')
    return value


class FileStore:
    def __init__(self, root, entries):
        self.root = Path(root).resolve(strict=True)
        self.entries = {}
        folded = set()
        self._state = threading.local()
        for entry in entries:
            if set(entry) != {'relative_path', 'bytes', 'sha256'}:
                raise LoadingError('indexed_file_shape_invalid')
            name = relative(entry['relative_path'])
            if name.casefold() in folded or not isinstance(entry['bytes'], int) or entry['bytes'] < 0:
                raise LoadingError('indexed_file_collision')
            if len(entry['sha256']) != 64 or any(char not in '0123456789abcdef' for char in entry['sha256']):
                raise LoadingError('indexed_digest_invalid')
            folded.add(name.casefold())
            self.entries[name] = entry

    @property
    def checking(self):
        return getattr(self._state, 'checking', 0)

    def path(self, name):
        name = relative(name)
        if name not in self.entries:
            raise LoadingError('unlisted_resource')
        current = self.root
        for component in Path(name).parts:
            current = current / component
            stat = current.lstat()
            if current.is_symlink() or getattr(stat, 'st_file_attributes', 0) & 1024:
                raise LoadingError('indexed_resource_reparse')
        if not current.is_file() or current.resolve(strict=True) != self.root / name:
            raise LoadingError('indexed_resource_identity')
        return current

    def read(self, name):
        self._state.checking = self.checking + 1
        try:
            path = self.path(name)
            raw = path.read_bytes()
            entry = self.entries[name]
            if len(raw) != entry['bytes'] or digest(raw) != entry['sha256']:
                raise LoadingError('indexed_resource_integrity')
            return raw
        finally:
            self._state.checking = self.checking - 1


class IndexedResource:
    def __init__(self, store, prefix):
        self.store, self.prefix = store, prefix.rstrip('/')

    @property
    def name(self):
        return self.prefix.rsplit('/', 1)[-1]

    def is_file(self):
        return self.prefix in self.store.entries

    def is_dir(self):
        return any(name.startswith(self.prefix + '/') for name in self.store.entries)

    def iterdir(self):
        prefix = self.prefix + '/'
        names = sorted({name[len(prefix):].split('/', 1)[0] for name in self.store.entries if name.startswith(prefix)})
        return iter(IndexedResource(self.store, prefix + name) for name in names)

    def joinpath(self, *parts):
        name = self.prefix
        for item in parts:
            name += '/' + relative(str(item))
        return IndexedResource(self.store, name)

    __truediv__ = joinpath

    def open(self, mode='r', *args, **kwargs):
        if mode not in ('r', 'rb'):
            raise LoadingError('package_resource_read_only')
        raw = self.store.read(self.prefix)
        if mode == 'rb':
            if args or kwargs:
                raise TypeError('Binary resource open does not accept text options')
            return io.BytesIO(raw)
        return io.TextIOWrapper(io.BytesIO(raw), *args, **kwargs)

    def read_bytes(self):
        return self.store.read(self.prefix)

    def read_text(self, encoding='utf-8', errors='strict'):
        return self.read_bytes().decode(encoding, errors=errors)


class ResourceReader:
    def __init__(self, store, prefix):
        self.store, self.prefix = store, prefix

    def files(self):
        return IndexedResource(self.store, self.prefix)

    def open_resource(self, name):
        return self.files().joinpath(name).open('rb')

    def resource_path(self, name):
        relative_name = self.files().joinpath(name).prefix
        self.store.read(relative_name)
        return str(self.store.path(relative_name))

    def is_resource(self, name):
        return self.files().joinpath(name).is_file()

    def contents(self):
        return (item.name for item in self.files().iterdir())


class NamespaceResource:
    def __init__(self, resources):
        self.resources = resources

    @property
    def name(self):
        return self.resources[0].name

    def is_file(self):
        return any(item.is_file() for item in self.resources)

    def is_dir(self):
        return any(item.is_dir() for item in self.resources)

    def iterdir(self):
        names = sorted({child.name for item in self.resources for child in item.iterdir()})
        return iter(self.joinpath(name) for name in names)

    def joinpath(self, *parts):
        return NamespaceResource([item.joinpath(*parts) for item in self.resources])

    __truediv__ = joinpath

    def _file(self):
        found = [item for item in self.resources if item.is_file()]
        if len(found) != 1:
            raise LoadingError('namespace_resource_missing_or_ambiguous')
        return found[0]

    def open(self, *args, **kwargs):
        return self._file().open(*args, **kwargs)

    def read_bytes(self):
        return self._file().read_bytes()

    def read_text(self, *args, **kwargs):
        return self._file().read_text(*args, **kwargs)


class IndexedNamespaceLoader:
    def __init__(self, store, portions):
        self.store, self.portions = store, portions

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        pass

    def get_resource_reader(self, fullname):
        store, portions = self.store, self.portions
        class Reader:
            def files(self):
                return NamespaceResource([IndexedResource(store, part) for part in portions])
            def open_resource(self, name):
                return self.files().joinpath(name).open('rb')
            def resource_path(self, name):
                resource = self.files().joinpath(name)._file()
                store.read(resource.prefix)
                return str(store.path(resource.prefix))
            def is_resource(self, name):
                return self.files().joinpath(name).is_file()
            def contents(self):
                return (item.name for item in self.files().iterdir())
        return Reader()


class IndexedSourceLoader(importlib.machinery.SourceFileLoader):
    def __init__(self, finder, fullname, record):
        self.finder, self.record = finder, record
        super().__init__(fullname, str(finder.store.path(record['file'])))

    def get_code(self, fullname):
        code = compile(self.finder.store.read(self.record['file']), self.path, 'exec', dont_inherit=True)
        self.finder.native.register_source_code(code, fullname, self.record['file'])
        return code

    def get_data(self, path):
        try:
            name = Path(path).resolve(strict=True).relative_to(self.finder.store.root).as_posix()
        except (ValueError, OSError) as error:
            raise LoadingError('unlisted_package_data') from error
        return self.finder.store.read(name)

    def get_resource_reader(self, fullname):
        if self.record['kind'] == 'package':
            return ResourceReader(self.finder.store, self.record['directory'])
        return None


class NativeSourceContext:
    """Host-owned observations and launch binding; never a JSON authority ctor.

    Digest/shape checks provide transfer integrity. The pre-Python native owner
    must independently authenticate the carrier and retain its source handles.
    """
    def __init__(self, document, binding, expected_sha, profile, artifact, policy_sha):
        required = {'format', 'host_pid', 'host_creation_filetime', 'profile',
                    'artifact_version', 'policy_sha256', 'observations'}
        frame = {'host_pid', 'host_creation_filetime', 'child_pid', 'child_creation_filetime',
                 'profile', 'artifact_version', 'policy_sha256', 'context_sha256'}
        if set(document) != required or set(binding) != frame or document['format'] != 'native-system-source-context-v2-candidate':
            raise LoadingError('native_source_context_shape')
        for name in ('host_pid', 'host_creation_filetime', 'child_pid', 'child_creation_filetime'):
            if type(binding[name]) is not int or binding[name] <= 0:
                raise LoadingError('native_source_binding_integer_type')
        for name in ('profile', 'artifact_version', 'policy_sha256', 'context_sha256'):
            if not isinstance(binding[name], str) or not binding[name]:
                raise LoadingError('native_source_binding_string_type')
        for name, expected in (('profile', profile), ('artifact_version', artifact), ('policy_sha256', policy_sha)):
            if document[name] != expected or binding[name] != expected:
                raise LoadingError('native_source_context_binding')
        for name in ('host_pid', 'host_creation_filetime'):
            if type(document[name]) is not int or document[name] <= 0 or binding[name] != document[name]:
                raise LoadingError('native_source_context_binding')
        if binding['context_sha256'] != expected_sha or binding['child_pid'] != os.getpid() or binding['host_pid'] != os.getppid() or type(binding['child_creation_filetime']) is not int or binding['child_creation_filetime'] <= 0:
            raise LoadingError('native_source_child_binding')
        observation = document['observations']
        fields = {'format', 'windows_directory', 'system_directory', 'os_version', 'architecture', 'files', 'errors', 'api_set_mappings', 'supported_minimum_os_build', 'redistribution'}
        if set(observation) != fields or observation.get('format') != 'windows-native-source-observations-v1' or observation.get('architecture') != 'amd64':
            raise LoadingError('native_source_observation_version')
        self.observation, self.binding = observation, binding
        file_fields = {'path', 'bytes', 'sha256', 'machine', 'volume_serial', 'file_index', 'modified_filetime', 'file_version', 'static_imports', 'delay_imports', 'signature'}
        signature_fields = {'method', 'wintrust_status', 'publisher_organization', 'signer_certificate_sha256', 'catalog', 'catalog_sha256', 'catalog_bytes', 'online_revocation'}
        for record in observation['files'].values():
            if set(record) != file_fields or set(record['signature']) != signature_fields:
                raise LoadingError('native_source_file_shape')
            for field in ('bytes', 'machine', 'volume_serial', 'file_index', 'modified_filetime'):
                if type(record[field]) is not int or record[field] < 0:
                    raise LoadingError('native_source_file_integer_type')
        self.system_directory = self.physical(Path(observation['system_directory']))
        windows = self.physical(Path(observation['windows_directory']))
        if os.name != 'nt' or self.system_directory.name.casefold() != 'system32' or self.system_directory.parent != windows:
            raise LoadingError('native_source_actual_root_invalid')

    @staticmethod
    def physical(path):
        if not path.is_absolute():
            raise LoadingError('native_source_path_invalid')
        for parent in (path, *path.parents):
            stat = parent.lstat()
            if parent.is_symlink() or getattr(stat, 'st_file_attributes', 0) & 1024:
                raise LoadingError('native_source_path_reparse')
        return path.resolve(strict=True)

    def record(self, identifier):
        if identifier in self.observation['errors']:
            raise LoadingError('native_source_required_unverified:' + identifier)
        record = self.observation['files'].get(identifier)
        if record is None:
            raise LoadingError('native_source_required_missing:' + identifier)
        signature = record['signature']
        if signature['wintrust_status'] != 0 or signature['publisher_organization'] != 'Microsoft Corporation' or len(signature.get('signer_certificate_sha256') or '') != 64 or signature['method'] not in ('WinVerifyTrust:file', 'CryptCATAdmin+WinVerifyTrust:catalog'):
            raise LoadingError('native_source_signature_observation_invalid')
        path = self.physical(Path(record['path']))
        if path.parent != self.system_directory:
            raise LoadingError('native_source_os_path_invalid')
        raw = path.read_bytes()
        if len(raw) != record['bytes'] or digest(raw) != record['sha256'] or record['machine'] != 0x8664:
            raise LoadingError('native_source_current_bytes_changed')
        if signature['method'] == 'CryptCATAdmin+WinVerifyTrust:catalog':
            catalog = self.physical(Path(signature['catalog']))
            root = self.system_directory / 'CatRoot' / '{F750E6C3-38EE-11D1-85E5-00C04FC295EE}'
            if catalog.parent != root.resolve(strict=True) or catalog.suffix.casefold() != '.cat':
                raise LoadingError('native_source_catalog_domain_invalid')
            body = catalog.read_bytes()
            if len(body) != signature['catalog_bytes'] or digest(body) != signature['catalog_sha256']:
                raise LoadingError('native_source_catalog_current_bytes_changed')
        return path, record


class NativeResolver:
    def __init__(self, store, profile, policy, source_context):
        self.store = store
        self.records = profile['native']
        self.profile, self.context = profile, source_context
        self.system_directory = source_context.system_directory
        self.contracts = {identifier: policy['system_contracts'][identifier] for identifier in profile['system_contract_ids']}
        self.system_by_name = {}
        for identifier, contract in self.contracts.items():
            if contract['id'] != identifier or profile['name'] not in contract['profiles'] or contract['basename'] in self.system_by_name:
                raise LoadingError('native_system_contract_invalid')
            self.system_by_name[contract['basename']] = identifier
        self.aliases = [group for group in policy['native_alias_groups'] if group['profile'] == profile['name']]
        self.alias_members = {}
        for group in self.aliases:
            if group['canonical'] != group['expected_actual_origin'] or group['basename'] != 'msvcp140-a4c2229bdc2a2a630acdc095b4d86008.dll':
                raise LoadingError('native_alias_policy_invalid')
            for member in group['members']:
                name = member['identity']['relative_path']
                if name in self.alias_members or self.store.entries.get(name) != member['identity'] or member['machine'] != 0x8664:
                    raise LoadingError('native_alias_member_invalid')
                self.store.read(member['owner_record']['relative_path'])
                self.alias_members[name] = group
        self.conditional = [entry for entry in policy['conditional_search_directories'] if entry['profile'] == profile['name']]
        self.source_codes = {}
        components = profile['native_sccs']
        flat = [name for component in components for name in component]
        if len(flat) != len(set(flat)) or set(flat) != set(self.records):
            raise LoadingError('native_scc_membership_invalid')
        self.in_progress = set()
        self.verified = set()
        self.handles = []
        self.cookies = []
        self.kernel = None
        self.preloaded_aliases = set()
        self._state = threading.local()
        self.lock = threading.RLock()

    @property
    def internal(self):
        return getattr(self._state, 'internal', 0)

    def source_record(self, identifier):
        self.store._state.checking = self.store.checking + 1
        try:
            return self.context.record(identifier)
        finally:
            self.store._state.checking -= 1

    def register_source_code(self, code, module, name):
        matching = [entry for entry in self.conditional if entry['module'] == module and entry['source'] == self.store.entries[name]]
        if not matching:
            return
        for entry in matching:
            owners = [owner for owner in self.profile['distributions'] if owner['metadata_directory'] == entry['owner'] and owner['name'].lower() == 'ctranslate2' and owner['version'] == '4.8.2']
            if len(owners) != 1 or entry['source']['sha256'] != 'a2a1954f726c88d527279d0284695f6011285ee6f7bd75ba76e61c1bdb2be646':
                raise LoadingError('conditional_native_caller_owner_invalid')
            self.store.read(owners[0]['metadata_files']['RECORD'])
        # Hold the actual objects; equality/co_filename/global module fields are
        # not caller credentials and ids cannot be recycled while these live.
        pending = [code]
        while pending:
            current = pending.pop()
            self.source_codes[id(current)] = (current, module, name, matching)
            pending.extend(value for value in current.co_consts if isinstance(value, types.CodeType))

    def canonical(self, name):
        return self.alias_members[name]['canonical'] if name in self.alias_members else name

    def system_path(self, identifier):
        contract = self.contracts.get(identifier)
        if contract is None:
            raise LoadingError('native_system_relation_unlisted')
        path, record = self.source_record(identifier)
        if contract['source_kind'] == 'api_set':
            targets = self.context.observation['api_set_mappings'].get(identifier)
            if targets != [path.name.casefold()]:
                raise LoadingError('native_api_set_source_mapping_invalid')
        elif path.name.casefold() != contract['basename']:
            raise LoadingError('native_system_source_name_invalid')
        if contract['source_kind'] == 'external_vc':
            floor = contract.get('minimum_file_version')
            if not isinstance(floor, list) or len(floor) != 4 or record.get('file_version') is None or record['file_version'] < floor:
                raise LoadingError('native_external_vc_floor_unverified')
        return str(path)

    def resolve(self, name):
        if not isinstance(name, str) or not name:
            raise LoadingError('unlisted_native_request')
        path = Path(name)
        if path.is_absolute():
            try:
                relative_name = path.resolve(strict=True).relative_to(self.store.root).as_posix()
            except (ValueError, OSError):
                identifier = self.system_by_name.get(path.name.casefold())
                if path.parent.resolve(strict=True) != self.system_directory or identifier is None or Path(self.system_path(identifier)) != path.resolve(strict=True):
                    raise LoadingError('unlisted_native_request')
                return str(path)
            if relative_name not in self.records:
                raise LoadingError('unlisted_native_request')
            self.verify(relative_name)
            return str(self.store.path(self.canonical(relative_name)))
        if path.name != name:
            raise LoadingError('unlisted_native_request')
        matches = [key for key in self.records if Path(key).name.casefold() == name.casefold()]
        if len(matches) == 1:
            self.verify(matches[0])
            return str(self.store.path(self.canonical(matches[0])))
        if matches and all(item in self.alias_members for item in matches):
            groups = {self.alias_members[item]['id'] for item in matches}
            if len(groups) == 1:
                self.verify(matches[0])
                return str(self.store.path(self.canonical(matches[0])))
        if matches or name.casefold() not in self.system_by_name:
            raise LoadingError('native_basename_ambiguous_or_unknown')
        return self.system_path(self.system_by_name[name.casefold()])

    def verify(self, name):
        with self.lock:
            self._verify(name)
            if self.kernel is not None:
                for edge in self.records[name]['alias_dependencies']:
                    group = self.alias_members.get(edge['requested_member'])
                    if group is None or edge not in group['importer_bindings'] or edge['canonical'] != group['canonical']:
                        raise LoadingError('native_alias_importer_binding_invalid')
                    self.preload_alias(group)

    def _verify(self, name):
        if name in self.verified or name in self.in_progress:
            return
        if name not in self.records:
            raise LoadingError('unlisted_native_object')
        self.in_progress.add(name)
        try:
            self.store.read(name)
            record = self.records[name]
            if record['unresolved']:
                raise LoadingError('native_dependency_relation_unresolved')
            for dependency in record['payload_dependencies']:
                self._verify(dependency)
            for identifier in record['system_contract_dependencies']:
                self.system_path(identifier)
            self.verified.add(name)
        finally:
            self.in_progress.remove(name)

    def configure_windows_search(self):
        import ctypes
        kernel_path, _ = self.source_record('kernel32.dll')
        kernel = ctypes.WinDLL(str(kernel_path), use_last_error=True)
        self.kernel, self.ctypes = kernel, ctypes
        kernel.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
        kernel.GetModuleHandleW.restype = ctypes.c_void_p
        kernel.GetModuleFileNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint32]
        kernel.GetModuleFileNameW.restype = ctypes.c_uint32
        self.verify_creation_binding()
        self.loaded_origin(kernel._handle, kernel_path)
        for module in ('_ctypes',):
            record = self.profile['modules'].get(module)
            if record is None or record['kind'] != 'extension':
                raise LoadingError('native_bootstrap_extension_missing')
            self.check_loaded(self.store.path(record['file']), required=True)
        kernel.SetDefaultDllDirectories.argtypes = [ctypes.c_uint32]
        kernel.SetDefaultDllDirectories.restype = ctypes.c_int
        # No application/CWD/PATH fallback. Explicit payload dirs still do not
        # enforce closed directory membership against a malicious same-user writer.
        if not kernel.SetDefaultDllDirectories(0x800 | 0x400):
            raise LoadingError('native_search_policy_failed')
        self.original_add_directory = os.add_dll_directory
        for directory in self.records_directory_roots():
            self.cookies.append(self.original_add_directory(str(directory)))
        resolver = self
        def controlled_directory(directory):
            caller = sys._getframe(1).f_code
            return resolver.add_directory(directory, caller)
        os.add_dll_directory = controlled_directory
        original = ctypes._dlopen
        def indexed_dlopen(name, *args, **kwargs):
            resolved = self.resolve(name)
            self._state.internal = self.internal + 1
            try:
                handle = original(resolved, *args, **kwargs)
                self.loaded_origin(handle, Path(resolved))
                if Path(resolved).is_relative_to(self.store.root):
                    self.post_loaded(Path(resolved).relative_to(self.store.root).as_posix())
                return handle
            finally:
                self._state.internal = self.internal - 1
        ctypes._dlopen = indexed_dlopen

    def loaded_origin(self, handle, expected):
        buffer = self.ctypes.create_unicode_buffer(32768)
        size = self.kernel.GetModuleFileNameW(handle, buffer, len(buffer))
        if not size or size >= len(buffer):
            raise LoadingError('native_actual_origin_unavailable')
        actual = NativeSourceContext.physical(Path(buffer.value))
        if actual != expected.resolve(strict=True):
            raise LoadingError('native_actual_origin_mismatch')
        if actual.is_relative_to(self.store.root):
            self.store.read(actual.relative_to(self.store.root).as_posix())
        else:
            identifiers = [identifier for identifier, record in self.context.observation['files'].items() if Path(record['path']).resolve(strict=True) == actual]
            if not identifiers:
                raise LoadingError('native_actual_origin_unlisted')
            for identifier in identifiers:
                _, record = self.source_record(identifier)
                self.verify_file_identity(actual, record)
        return actual

    def verify_file_identity(self, path, record):
        ctypes, kernel = self.ctypes, self.kernel
        class FileTime(ctypes.Structure):
            _fields_ = [('low', ctypes.c_uint32), ('high', ctypes.c_uint32)]
        class Information(ctypes.Structure):
            _fields_ = [('attributes', ctypes.c_uint32), ('creation', FileTime), ('access', FileTime), ('write', FileTime),
                        ('volume', ctypes.c_uint32), ('size_high', ctypes.c_uint32), ('size_low', ctypes.c_uint32),
                        ('links', ctypes.c_uint32), ('index_high', ctypes.c_uint32), ('index_low', ctypes.c_uint32)]
        kernel.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
        kernel.CreateFileW.restype = ctypes.c_void_p
        kernel.GetFileInformationByHandle.argtypes = [ctypes.c_void_p, ctypes.POINTER(Information)]
        kernel.GetFileInformationByHandle.restype = ctypes.c_int
        handle = kernel.CreateFileW(str(path), 0x80000000, 1, None, 3, 0, None)
        if handle in (None, ctypes.c_void_p(-1).value):
            raise LoadingError('native_source_identity_open_failed')
        try:
            info = Information()
            if not kernel.GetFileInformationByHandle(handle, ctypes.byref(info)) or (info.volume, info.index_high << 32 | info.index_low, info.write.high << 32 | info.write.low) != (record['volume_serial'], record['file_index'], record['modified_filetime']):
                raise LoadingError('native_source_file_identity_changed')
        finally:
            kernel.CloseHandle(handle)

    def check_loaded(self, expected, required=False):
        handle = self.kernel.GetModuleHandleW(expected.name)
        if handle:
            self.loaded_origin(handle, expected)
        elif required:
            raise LoadingError('native_module_not_loaded')

    def preload_alias(self, group):
        if group['id'] in self.preloaded_aliases:
            return
        closure = group['dependency_closure']
        if group['canonical'] not in closure or any(self.records.get(name) != record for name, record in closure.items()):
            raise LoadingError('native_alias_closure_invalid')
        if digest(json.dumps(closure, sort_keys=True, separators=(',', ':')).encode()) != group['dependency_closure_sha256']:
            raise LoadingError('native_alias_closure_digest_invalid')
        for member in group['members']:
            self.store.read(member['identity']['relative_path'])
        self._verify(group['canonical'])
        for name in closure:
            self.check_loaded(self.store.path(name))
        canonical = self.store.path(group['canonical'])
        self.check_loaded(canonical)
        self._state.internal = self.internal + 1
        try:
            handle = self.ctypes.WinDLL(str(canonical), winmode=0x100 | 0x800 | 0x400)
            self.loaded_origin(handle._handle, canonical)
            self.handles.append(handle)
        finally:
            self._state.internal -= 1
        self.check_loaded(canonical, required=True)
        for name in closure:
            self.check_loaded(self.store.path(name))
        self.preloaded_aliases.add(group['id'])

    def post_loaded(self, name):
        pending, seen = [name], set()
        while pending:
            current = pending.pop()
            if current in seen:
                continue
            seen.add(current)
            record = self.records[current]
            normal = {item.casefold() for item in record['static_imports']}
            for target in record['payload_dependencies']:
                self.check_loaded(self.store.path(self.canonical(target)), required=Path(target).name.casefold() in normal)
                pending.append(target)
            for identifier in record['system_contract_dependencies']:
                self.check_loaded(Path(self.system_path(identifier)), required=self.contracts[identifier]['basename'] in normal)

    def verify_creation_binding(self):
        ctypes, kernel = self.ctypes, self.kernel
        class FileTime(ctypes.Structure):
            _fields_ = [('low', ctypes.c_uint32), ('high', ctypes.c_uint32)]
        kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel.GetProcessTimes.argtypes = [ctypes.c_void_p, *([ctypes.POINTER(FileTime)] * 4)]
        for prefix in ('host', 'child'):
            pid = self.context.binding[prefix + '_pid']
            handle = kernel.OpenProcess(0x1000, False, pid)
            if not handle:
                raise LoadingError('native_process_creation_unavailable')
            try:
                born, end, system, user = (FileTime() for _ in range(4))
                if not kernel.GetProcessTimes(handle, ctypes.byref(born), ctypes.byref(end), ctypes.byref(system), ctypes.byref(user)) or (born.high << 32 | born.low) != self.context.binding[prefix + '_creation_filetime']:
                    raise LoadingError('native_process_creation_mismatch')
            finally:
                kernel.CloseHandle(handle)

    def add_directory(self, directory, caller):
        path = Path(directory)
        if not path.is_absolute():
            raise LoadingError('unlisted_native_search_directory')
        target = path.resolve(strict=False)
        code = self.source_codes.get(id(caller))
        if code is not None and code[0] is caller:
            for entry in code[3]:
                if target == self.store.root / relative(entry['relative_path']):
                    if entry['mode'] != 'absence_only' or entry['platform'] != 'windows-amd64' or entry['compute_profile'] != 'cpu':
                        raise LoadingError('conditional_native_rule_invalid')
                    # The held caller package must exist and remain indexed.
                    self.store.read(entry['source']['relative_path'])
                    for parent in target.parents:
                        if parent.exists():
                            NativeSourceContext.physical(parent)
                        if parent == self.store.root:
                            break
                    if not target.exists() and not target.is_symlink():
                        # Never call the Win32 API. If the path appears after
                        # this check, it still cannot acquire a directory cookie.
                        raise FileNotFoundError(2, 'Optional indexed CPU sibling is absent', str(target))
                    raise LoadingError('conditional_native_directory_present_unknown')
        if target not in self.records_directory_roots():
            raise LoadingError('unlisted_native_search_directory')
        NativeSourceContext.physical(target)
        cookie = self.original_add_directory(str(target))
        self.cookies.append(cookie)
        class RetainedCookie:
            # Third-party disposal must not invalidate the resolver's cookie
            # while native code still runs. The actual owner closes it at exit.
            def close(self):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                self.close()
        return RetainedCookie()

    def records_directory_roots(self):
        return sorted({self.store.path(name).parent for name in self.records})


class IndexedExtensionLoader(importlib.machinery.ExtensionFileLoader):
    def __init__(self, native, fullname, path):
        self.native = native
        super().__init__(fullname, path)

    def create_module(self, spec):
        module = super().create_module(spec)
        # Windows may already execute DLL initializers before this observation;
        # this is an actual post-load origin check, not a pre-execution sandbox.
        if self.native.kernel is not None:
            self.native.check_loaded(Path(self.path), required=True)
            self.native.post_loaded(Path(self.path).relative_to(self.native.store.root).as_posix())
        return module

    def exec_module(self, module):
        super().exec_module(module)
        if self.native.kernel is not None:
            self.native.check_loaded(Path(self.path), required=True)
            self.native.post_loaded(Path(self.path).relative_to(self.native.store.root).as_posix())


class IndexedPathImporter:
    def __init__(self, finder, directory):
        self.finder, self.directory = finder, directory

    def find_spec(self, fullname, target=None):
        return self.finder.find_spec(fullname, target=target)

    def iter_modules(self, prefix=''):
        found = {}
        for fullname, item in self.finder.modules.items():
            if self.directory == '' and item.get('top_level'):
                found[fullname] = item['kind'] in ('package', 'namespace')
            elif self.directory in item.get('parent_directories', [item.get('parent_directory')]):
                found[fullname.rsplit('.', 1)[-1]] = item['kind'] in ('package', 'namespace')
        return iter((prefix + name, package) for name, package in sorted(found.items()))


class IndexedFinder:
    def __init__(self, store, profile, native):
        self.store, self.profile, self.native = store, profile, native
        self.modules = profile['modules']
        self.directories = set(profile['module_roots'])
        for item in self.modules.values():
            self.directories.update(item.get('portions', []))
            if item.get('directory'):
                self.directories.add(item['directory'])

    def find_spec(self, fullname, path=None, target=None):
        if fullname in self.profile['builtins']:
            return importlib.machinery.BuiltinImporter.find_spec(fullname)
        if fullname in self.profile['frozen']:
            return importlib.machinery.FrozenImporter.find_spec(fullname)
        item = self.modules.get(fullname)
        if item is None:
            # With this as the only finder, None preserves optional find_spec
            # probes while actual import still fails without directory fallback.
            return None
        if item['kind'] == 'namespace':
            spec = importlib.machinery.ModuleSpec(fullname, loader=IndexedNamespaceLoader(self.store, item['portions']), is_package=True)
            spec.submodule_search_locations = [str(self.store.root / part) for part in item['portions']]
            return spec
        file = self.store.path(item['file'])
        if item['kind'] == 'extension':
            self.native.verify(item['file'])
            loader = IndexedExtensionLoader(self.native, fullname, str(file))
        else:
            loader = IndexedSourceLoader(self, fullname, item)
        return importlib.util.spec_from_file_location(fullname, file, loader=loader,
            submodule_search_locations=[str(self.store.root / item['directory'])] if item['kind'] == 'package' else None)

    def path_hook(self, path):
        if path == 'video-creator-index:' + self.profile['name']:
            return IndexedPathImporter(self, '')
        try:
            directory = Path(path).resolve(strict=True).relative_to(self.store.root).as_posix()
        except (ValueError, OSError):
            raise ImportError('unlisted_import_path')
        if directory not in self.directories:
            raise ImportError('unlisted_import_path')
        return IndexedPathImporter(self, directory)

    def find_distributions(self, context=None):
        import importlib.metadata
        store = self.store
        class IndexedDistribution(importlib.metadata.Distribution):
            def __init__(self, entry):
                self.entry = entry
            def read_text(self, filename):
                if filename not in self.entry['metadata_files']:
                    return None
                return store.read(self.entry['metadata_files'][filename]).decode('utf-8', errors='strict')
            def locate_file(self, name):
                path = (store.root / self.entry['root'] / str(name)).resolve(strict=True)
                try:
                    relative_name = path.relative_to(store.root).as_posix()
                except ValueError:
                    raise LoadingError('distribution_resource_escaped')
                store.read(relative_name)
                return store.path(relative_name)
        requested = None if context is None else context.name
        def normalized(name):
            return name.lower().replace('-', '_').replace('.', '_')
        return (IndexedDistribution(item) for item in self.profile['distributions']
                if not requested or normalized(item['name']) == normalized(requested))


def install(root, policy, profile_name, system_directory, data_roots, policy_raw, source_context):
    if policy['format'] != 'portable-engine-load-policy-v2-candidate' or profile_name not in policy['profiles']:
        raise LoadingError('load_policy_profile_invalid')
    profile = policy['profiles'][profile_name]
    if profile['implementation'] != sys.implementation.name or profile['python_version'] != list(sys.version_info[:3]):
        raise LoadingError('load_policy_python_identity')
    if set(profile['builtins']) != set(sys.builtin_module_names):
        raise LoadingError('load_policy_builtin_identity')
    import _imp
    if set(profile['frozen']) != set(_imp._frozen_module_names()):
        raise LoadingError('load_policy_frozen_identity')
    store = FileStore(root, policy['files'])
    policy_sha256 = digest(policy_raw)
    store.entries['LoadPolicy.json'] = {'relative_path':'LoadPolicy.json','bytes':len(policy_raw),'sha256':policy_sha256}
    if Path(system_directory).resolve(strict=True) != source_context.system_directory:
        raise LoadingError('native_system_directory_consistency')
    native = NativeResolver(store, profile, policy, source_context)
    finder = IndexedFinder(store, profile, native)
    sys.meta_path[:] = [finder]
    sys.path_hooks[:] = [finder.path_hook]
    sys.path_importer_cache.clear()
    sys.path[:] = ['video-creator-index:' + profile_name]
    sys.dont_write_bytecode = True
    native.configure_windows_search()
    data_roots = tuple(Path(path).resolve(strict=True) for path in data_roots)
    if any(path.is_relative_to(store.root) or store.root.is_relative_to(path) for path in data_roots):
        raise LoadingError('resource_and_data_domains_overlap')
    def audit(event, values):
        if store.checking:
            return
        if event == 'open' and values and isinstance(values[0], str):
            path = Path(values[0]).resolve()
            if path == Path(os.devnull).resolve():
                return
            data = any(path.is_relative_to(directory) for directory in data_roots)
            mode, flags = values[1:3]
            writing = (isinstance(mode, str) and any(char in mode for char in 'wax+')) or (isinstance(flags, int) and bool(flags & 3))
            if writing and not data:
                raise LoadingError('unlisted_resource_write')
            if not writing and not data:
                try:
                    name = path.relative_to(store.root).as_posix()
                except ValueError:
                    raise LoadingError('unlisted_resource_read')
                store.read(name)
        elif event == 'ctypes.dlopen' and not native.internal:
            native.resolve(values[0])
        elif event == 'os.add_dll_directory':
            if Path(values[0]).resolve() not in native.records_directory_roots():
                raise LoadingError('unlisted_native_search_directory')
        elif event == 'subprocess.Popen':
            executable, argv = values[:2]
            resolved = native.resolve(str(executable))
            if resolved not in [str(store.path(name)) for name in profile['tool_executables']]:
                if not isinstance(argv, (list, tuple)) or '--load-policy' not in argv or '--profile' not in argv:
                    raise LoadingError('unlisted_child_profile')
                try:
                    role = argv[argv.index('--profile') + 1]
                    child = policy['profiles'][role]
                    policy_argument = argv[argv.index('--load-policy') + 1]
                    digest_argument = argv[argv.index('--load-policy-sha256') + 1]
                    bootstrap = str(store.path(child['bootstrap']))
                    prefix = [resolved, '-I', '-S', '-B', '-X', 'utf8', bootstrap]
                    if len(argv)<len(prefix) or Path(argv[0]).resolve() != Path(resolved).resolve() or list(argv[1:6])!=prefix[1:6] or Path(argv[6]).resolve()!=Path(bootstrap).resolve() or resolved != str(store.path(child['executable'])) or Path(policy_argument).resolve() != store.root/'LoadPolicy.json' or digest_argument != policy_sha256:
                        raise LoadingError('child_bootstrap_binding_mismatch')
                except (KeyError, ValueError, IndexError):
                    raise LoadingError('unlisted_child_profile')
        elif event in ('os.system', 'os.exec', 'os.posix_spawn'):
            raise LoadingError('uncontrolled_process_execution')
    sys.addaudithook(audit)
    return finder
