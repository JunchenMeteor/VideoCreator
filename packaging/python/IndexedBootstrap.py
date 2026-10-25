"""Entry only for the exact host-bound archive/policy and retained resource guard."""
import argparse
import importlib.machinery
import importlib
import os
from pathlib import Path
import runpy
import sys

from _video_creator_boot.IndexedLoader import LoadingError, NativeSourceContext, digest, install, load_document


def source_binding(args, policy):
    # Use the underlying raw pipe: API control may later use os.read(fileno),
    # so even buffered read-ahead must not hide following product bytes.
    raw_stdin = getattr(sys.stdin.buffer, 'raw', None)
    if raw_stdin is None:
        raise LoadingError('native_source_binding_raw_pipe_missing')
    frame = bytearray()
    while len(frame) < 1024:
        byte = raw_stdin.read(1)
        if not byte:
            raise LoadingError('native_source_binding_missing')
        frame.extend(byte)
        if byte == b'\n':
            break
    prefix = b'NATIVE_SOURCE_BIND '
    if not frame.endswith(b'\n') or not frame.startswith(prefix) or not frame.isascii() or b'\r' in frame:
        raise LoadingError('native_source_binding_frame_invalid')
    binding = load_document(bytes(frame[len(prefix):-1]))
    carrier = NativeSourceContext.physical(args.native_source_context)
    roots = [NativeSourceContext.physical(path) for path in args.data_root]
    if not any(carrier.is_relative_to(root) for root in roots) or carrier.is_relative_to(args.installation_root.resolve(strict=True)):
        raise LoadingError('native_source_carrier_domain_invalid')
    raw = carrier.read_bytes()
    if len(raw) > 16 * 1024 * 1024 or digest(raw) != args.native_source_context_sha256:
        raise LoadingError('native_source_carrier_integrity')
    return NativeSourceContext(load_document(raw), binding, args.native_source_context_sha256,
                               args.profile, policy['artifact_version'], args.load_policy_sha256)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--installation-root', required=True, type=Path)
    parser.add_argument('--load-policy', required=True, type=Path)
    parser.add_argument('--load-policy-sha256', required=True)
    parser.add_argument('--profile', required=True, choices=['api', 'worker', 'mcp', 'asr', 'owner-setup', 'owner-setup-trust', 'owner-setup-qualified-install'])
    parser.add_argument('--system-directory', required=True, type=Path)
    parser.add_argument('--native-source-context', required=True, type=Path)
    parser.add_argument('--native-source-context-sha256', required=True)
    parser.add_argument('--native-startup-binding', type=Path)
    parser.add_argument('--native-startup-binding-sha256')
    parser.add_argument('--data-root', required=True, action='append', type=Path)
    parser.add_argument('arguments', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if not all((sys.flags.isolated, sys.flags.no_site, sys.flags.ignore_environment, sys.dont_write_bytecode)):
        raise LoadingError('bootstrap_isolation_required')
    root = args.installation_root.resolve(strict=True)
    policy_path = args.load_policy.resolve(strict=True)
    if not policy_path.is_relative_to(root) or policy_path.is_symlink():
        raise LoadingError('bootstrap_policy_path_invalid')
    raw = policy_path.read_bytes()
    if len(raw) > 32 * 1024 * 1024 or digest(raw) != args.load_policy_sha256:
        raise LoadingError('bootstrap_policy_integrity')
    policy = load_document(raw)
    if policy.get('format') != 'portable-engine-load-policy-v2-candidate':
        raise LoadingError('bootstrap_policy_version')
    profile = policy['profiles'][args.profile]
    if Path(sys.executable).resolve(strict=True) != (root / profile['executable']).resolve(strict=True):
        raise LoadingError('bootstrap_interpreter_identity')
    if policy_path != root/'LoadPolicy.json':
        raise LoadingError('bootstrap_policy_name_invalid')
    context = source_binding(args, policy)
    finder = install(root, policy, args.profile, args.system_directory, args.data_root, raw, context)
    entry = profile['entry_module']
    if entry not in finder.modules or finder.modules[entry]['kind'] != 'source':
        raise LoadingError('bootstrap_entry_unlisted')
    arguments = args.arguments[1:] if args.arguments[:1] == ['--'] else args.arguments
    if profile['command'] is not None and arguments[:1] != [profile['command']]:
        raise LoadingError('bootstrap_role_command_mismatch')
    sys.argv = [entry, *arguments]
    if args.profile in ('owner-setup', 'owner-setup-trust', 'owner-setup-qualified-install'):
        # Separate pre-API callable. No renderer-selected module, authority,
        # service token or management secret. The original native owner holds
        # this initialization carrier and the original instance-independent
        # bootstrap connection. Existing channels bind only after actual ID.
        if entry != 'video_creator.cli.native_owner_setup' or profile['command'] is not None:
            raise LoadingError('native_owner_setup_entry_invalid')
        if args.native_startup_binding is None or args.native_startup_binding_sha256 is None:
            raise LoadingError('native_owner_setup_binding_required')
        path = NativeSourceContext.physical(args.native_startup_binding)
        data_roots = [NativeSourceContext.physical(item) for item in args.data_root]
        if not any(path.is_relative_to(item) for item in data_roots) or path.is_relative_to(root):
            raise LoadingError('native_owner_setup_binding_domain_invalid')
        data = path.read_bytes()
        if len(data) > 32 * 1024 * 1024 or digest(data) != args.native_startup_binding_sha256:
            raise LoadingError('native_owner_setup_binding_integrity')
        module = importlib.import_module(entry)
        # These are separate source-bound internal plans. The legacy plan does
        # not wait for trust admission; no environment/renderer selects a name.
        if args.profile == 'owner-setup-qualified-install':
            result = module.initialize_bind_admit_trust_and_record(initialization_record=data)
        elif args.profile == 'owner-setup-trust':
            result = module.initialize_bind_and_admit_trust(initialization_record=data)
        else:
            result = module.initialize_and_bind(initialization_record=data)
        if type(result) is not int:
            raise LoadingError('native_owner_setup_adapter_result_invalid')
        raise SystemExit(result)
    if args.profile in ('api', 'mcp', 'worker'):
        if args.native_startup_binding is None or args.native_startup_binding_sha256 is None:
            raise LoadingError('native_startup_binding_required')
        binding_path = NativeSourceContext.physical(args.native_startup_binding)
        data_roots = [NativeSourceContext.physical(path) for path in args.data_root]
        if (not any(binding_path.is_relative_to(path) for path in data_roots)
                or binding_path.is_relative_to(root)):
            raise LoadingError('native_startup_binding_domain_invalid')
        binding_bytes = binding_path.read_bytes()
        if (len(binding_bytes) > 32 * 1024 * 1024 - 16384
                or digest(binding_bytes) != args.native_startup_binding_sha256):
            raise LoadingError('native_startup_binding_integrity')
        # Fixed Backend-owned consumer. No public module selector, fallback to
        # an unassembled service, or substitute Engine/Bundle implementation.
        adapter_name = 'video_creator.cli.native_startup'
        if adapter_name not in finder.modules or finder.modules[adapter_name]['kind'] != 'source':
            raise LoadingError('native_startup_adapter_unlisted')
        locator = os.environ.pop('VIDEO_CREATOR_HELD_RESOURCE_CHANNEL', None)
        if locator is None:
            raise LoadingError('native_startup_locator_missing')
        configured_adapter = (profile.get('adapter_module'), profile.get('adapter_callable'))
        if configured_adapter == (None, None):
            adapter_callable = 'main'
        elif configured_adapter == (adapter_name, 'main_qualified'):
            adapter_callable = 'main_qualified'
        else:
            raise LoadingError('native_startup_adapter_invalid')
        result = getattr(importlib.import_module(adapter_name), adapter_callable)(
            startup_record=binding_bytes, locator_bytes=locator.encode('utf-8'))
        if type(result) is not int:
            raise LoadingError('native_startup_adapter_result_invalid')
        raise SystemExit(result)
    if args.native_startup_binding is not None or args.native_startup_binding_sha256 is not None:
        raise LoadingError('native_startup_service_role_invalid')
    runpy.run_module(entry, run_name='__main__', alter_sys=True)


if __name__ == '__main__':
    main()
