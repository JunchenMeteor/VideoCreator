"""ADR0084 product-serve/product-worker trusted startup; validates before listener."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from video_creator.application.engine import EngineService
from video_creator.application.installer_provisioning import _dacl_summary
from video_creator.application.media_registration import (
    PACKAGE_ROOT,
    _hash,
    _local_file,
    _package_sources,
)
from video_creator.application.product_installation import (
    ProductInstallationAuthority,
    ProductStartupBuild,
    ProductStartupConnection,
    ProductStartupContext,
)
from video_creator.domain.errors import EngineError
from video_creator.infrastructure.owner_identity import inspect_owner_directory


def _fail(code: str, message: str, status: int = 409):
    raise EngineError(code, message, status)


def _check_record(record_path: Path, expected_sha: str, data_dir: Path, install_root: Path, role: str):
    if not record_path.is_absolute() or record_path.is_symlink() or not record_path.is_file():
        _fail('trusted_startup_record_missing', 'Installation record is unavailable', 503)
    raw = record_path.read_bytes()
    if len(raw) > 2 * 1024 * 1024:
        _fail('trusted_startup_record_too_large',
              f'Installation record is {len(raw)} bytes; the admitted limit is {2 * 1024 * 1024}', 503)
    if hashlib.sha256(raw).hexdigest() != expected_sha:
        _fail('trusted_startup_record_changed', 'Installation record differs from its pinned bytes', 503)
    try:
        record = json.loads(raw)
    except (ValueError, TypeError):
        _fail('trusted_startup_record_invalid', 'Installation record is not JSON', 422)
    required = {'format', 'complete', 'installer_version', 'provisioned_at_us', 'instance_id', 'install_root',
                'engine_package_relative', 'instance_dir', 'project_id', 'registration_sha256',
                'expected_files', 'engine_file_names', 'os_subject', 'administrator_id', 'instance_device',
                'instance_inode', 'resource_manifest_sha256', 'runtime_manifest_sha256',
                'dacl_summary_sha256', 'route_ids', 'items', 'counts', 'revision', 'expected_trees'}
    if type(record) is not dict or set(record) != required or record['format'] != 'installation-provisioning-v1':
        _fail('trusted_startup_record_invalid', 'Installation record fields are not canonical', 422)
    if record['complete'] is not True or type(record.get('revision')) is not int or record['revision'] < 1:
        _fail('trusted_startup_record_incomplete', 'Installation record is not complete', 503)
    if record['instance_id'] != EngineService(data_dir).instance_id:
        _fail('trusted_startup_instance_conflict', 'Installation record belongs to another instance', 409)
    if record['instance_dir'] != str(data_dir.resolve()) or record['install_root'] != str(install_root.resolve()):
        _fail('trusted_startup_instance_conflict', 'Installation record paths differ from the actual installation', 409)
    if not PACKAGE_ROOT.resolve().is_relative_to(install_root.resolve()) or not Path(sys.executable).resolve().is_relative_to(install_root.resolve()):
        _fail('trusted_startup_layout_conflict', 'Running engine is not inside the recorded install root', 409)
    owner = inspect_owner_directory(data_dir)
    if (record['os_subject'], record['administrator_id'], record['instance_device'], record['instance_inode']) != (
            owner.os_subject, owner.administrator_id, owner.directory_device, owner.directory_inode):
        _fail('trusted_startup_owner_changed', 'Instance directory OS identity changed', 409)
    if record['dacl_summary_sha256'] != _dacl(data_dir):
        _fail('trusted_startup_acl_changed', 'Instance directory ACL changed', 409)
    actual_engine = {name: _hash(_local_file(PACKAGE_ROOT, name)) for name in _package_sources(PACKAGE_ROOT)}
    if set(actual_engine) != set(record['engine_file_names']):
        _fail('trusted_startup_bytes_changed', 'Engine file set differs from the record', 503)
    for fact in record['expected_files']:
        path = install_root / fact['relative_path']
        if (path.is_symlink() or not path.is_file() or path.stat().st_size != fact['bytes']
                or _hash(path) != fact['sha256']):
            _fail('trusted_startup_bytes_changed', 'Installed bytes differ from the record', 503)
    for tree in record['expected_trees']:
        target = install_root / tree['relative_path']
        files = _tree_files(target)
        digest = hashlib.sha256(json.dumps([(item[0], item[1], item[2]) for item in files],
                                           ensure_ascii=False, sort_keys=True,
                                           separators=(',', ':')).encode('utf-8')).hexdigest()
        if (len(files), sum(item[1] for item in files), digest) != (
                tree['file_count'], tree['bytes'], tree['sha256']):
            _fail('trusted_startup_bytes_changed',
                  'Installed tree differs from the record: ' + tree['relative_path'], 503)
    return record


def _tree_files(base: Path):
    if not base.is_dir():
        return []
    return [(path.relative_to(base).as_posix(), path.stat().st_size, _hash(path))
            for path in sorted(base.rglob('*')) if path.is_file()]


def _dacl(path: Path) -> str:
    return _dacl_summary(path)


def _factory(record_path: Path, record_sha: str, registration: Path, registration_sha: str, role: str):
    def assemble(*, engine, bundle, role, registered_runtime, for_management):
        if for_management is not False:
            _fail('trusted_startup_role_denied', 'Product startup never assembles management', 403)
        if role == 'worker':
            if registered_runtime is None or registered_runtime.engine is not engine or registered_runtime.bundle is not bundle:
                _fail('trusted_startup_role_denied', 'Product worker requires its exact registered runtime and Bundle', 403)
        elif registered_runtime is not None:
            _fail('trusted_startup_role_denied', 'Product API never accepts a worker runtime', 403)
        from video_creator.application.native_installation import NativeOwnerServices
        from video_creator.application.owner_services import assemble_owner_services

        record = json.loads(record_path.read_text(encoding='utf-8'))
        authority = ProductInstallationAuthority(engine, record_path=record_path, record_sha256=record_sha,
                                                 registration=registration, registration_sha256=registration_sha,
                                                 role=role)
        connection = ProductStartupConnection(ProductStartupContext(engine.instance_id, role))
        authority.connection = connection
        owner = bundle.principals.owner_subject
        registration_config = json.loads(registration.read_text(encoding='utf-8'))
        projects = tuple(registration_config['local_registration']['rights_declaration']['project_ids'])
        registered = {
            'owner_subject': owner, 'executing_principal_id': owner, 'project_ids': projects,
            'registration_sha256': registration_sha,
            'resource_manifest_sha256': record['resource_manifest_sha256'],
            'runtime_manifest_sha256': record['runtime_manifest_sha256'],
            'allowed_source_namespaces': ((owner, owner),),
            'expires_at_us': engine.clock() + 24 * 3600 * 1_000_000,
        }
        services = assemble_owner_services(engine, owner, bundle=bundle, for_management=False,
                                           installation_authority=authority,
                                           installation_session_guard=authority,
                                           execution_registration=registered)
        return NativeOwnerServices(services, connection, authority, ProductStartupBuild())
    return assemble


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog='video-creator-product')
    parser.add_argument('command', choices=['product-serve', 'product-worker'])
    parser.add_argument('--data-dir', required=True, type=Path)
    parser.add_argument('--install-root', required=True, type=Path)
    parser.add_argument('--installation-record', required=True, type=Path)
    parser.add_argument('--installation-record-sha256', required=True)
    parser.add_argument('--production-config', required=True, type=Path)
    parser.add_argument('--production-config-sha256', required=True)
    parser.add_argument('--native-origin', default='http://tauri.localhost')
    parser.add_argument('--max-seconds', type=int, default=300)
    parser.add_argument('--control-stdin', action='store_true')
    args = parser.parse_args(argv)
    try:
        if any(part.startswith('--development-') for part in sys.argv) or 'VIDEO_CREATOR_DEVELOPMENT_INSTALLATION' in __import__('os').environ:
            _fail('trusted_startup_entry_denied', 'Development startup flags are not a product entry', 403)
        data_dir = args.data_dir.resolve()
        install_root = args.install_root.resolve()
        _check_record(args.installation_record, args.installation_record_sha256, data_dir, install_root, args.command)
        registration_sha = hashlib.sha256(args.production_config.read_bytes()).hexdigest()
        if registration_sha != args.production_config_sha256:
            _fail('trusted_startup_registration_conflict', 'Registration file differs from its pinned hash', 409)
        # Reuse the real registration resource checks from provisioning.
        from video_creator.application.installer_provisioning import _registration
        _registration(args.production_config)
        role = 'api' if args.command == 'product-serve' else 'worker'
        factory = _factory(args.installation_record, args.installation_record_sha256,
                           args.production_config, registration_sha, role)
        from video_creator.cli.main import main as engine_main
        previous = sys.argv
        try:
            if args.command == 'product-worker':
                forwarded = ['worker', '--workflow', 'registered-media-bundle-v1',
                             '--data-dir', str(data_dir), '--production-config', str(args.production_config),
                             '--production-config-sha256', registration_sha,
                             '--max-seconds', str(args.max_seconds)]
                if args.control_stdin:
                    forwarded.append('--control-stdin')
            else:
                forwarded = ['serve', '--data-dir', str(data_dir), '--host', '127.0.0.1',
                             '--port', '0', '--native-origin', args.native_origin,
                             '--production-config', str(args.production_config),
                             '--production-config-sha256', registration_sha]
            sys.argv = [previous[0], *forwarded]
            return engine_main(installed_service_factory=factory)
        finally:
            sys.argv = previous
    except EngineError as error:
        print(json.dumps({'code': error.code, 'message': error.message}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
