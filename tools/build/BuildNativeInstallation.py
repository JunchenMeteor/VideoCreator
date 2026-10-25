"""External final-host receipt producer. Does not install or issue authority.

The field mapping is Backend's native_execution_registration Slice A contract.
Run only with an independently fixed build input after the final host was built.
No product import, dependency resolution, signature claim or vendor execution.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def document(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = value
        return result
    return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def physical(path):
    path = Path(path)
    if (not path.is_absolute() or str(path).startswith(('\\\\', '//'))
            or any(ord(char) < 32 or 0xD800 <= ord(char) <= 0xDFFF for char in str(path))
            or any(part in ('.', '..') for part in str(path).replace('\\', '/').split('/'))):
        raise ValueError('Exact local absolute path required')
    if os.name == 'nt' and (len(path.drive) != 2 or path.drive[1] != ':'):
        raise ValueError('Exact Windows drive path required')
    if os.name == 'nt' and any(':' in part or part.endswith((' ', '.')) for part in str(path)[2:].replace('\\', '/').split('/')):
        raise ValueError('Windows alias or alternate stream denied')
    for parent in reversed((path, *path.parents)):
        info = parent.lstat()
        if parent.is_symlink() or getattr(info, 'st_file_attributes', 0) & 1024:
            raise ValueError('Linked physical input denied')
    return path.resolve(strict=True)


def read(path, *, limit=None):
    """Hash the original opened file, preserving its exact source bytes."""
    path = physical(path)
    with path.open('rb') as stream:
        before = os.fstat(stream.fileno())
        if not path.is_file() or (limit is not None and before.st_size > limit):
            raise ValueError('Nonregular or oversized input')
        result, count, body = hashlib.sha256(), 0, bytearray() if limit is not None else None
        while block := stream.read(65536):
            count += len(block)
            if count > before.st_size:
                raise ValueError('Input grew while reading')
            result.update(block)
            if body is not None:
                body.extend(block)
        after = os.fstat(stream.fileno())
        named = path.stat()
        identity = lambda item: (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns, item.st_ctime_ns)
        if count != before.st_size or identity(before) != identity(after) or identity(after) != identity(named):
            raise ValueError('Physical input changed while reading')
    return {'path': str(path), 'bytes': count, 'sha256': result.hexdigest()}, bytes(body) if body is not None else None


def checked(ref, *, limit=None):
    fact, body = read(ref['path'], limit=limit)
    if type(ref['bytes']) is not int or (fact['bytes'], fact['sha256']) != (ref['bytes'], ref['sha256']):
        raise ValueError('Pinned source changed')
    return fact, body


def relative(value):
    path = PurePosixPath(value)
    if (type(value) is not str or not value or '\\' in value or ':' in value
            or path.is_absolute() or path.as_posix() != value
            or any(part in ('.', '..', '') for part in value.split('/'))
            or any(ord(char) < 32 or 0xD800 <= ord(char) <= 0xDFFF for char in value)):
        raise ValueError('Exact payload member required')
    return value


def identifier(value):
    if (type(value) is not str or not 1 <= len(value) <= 128
            or any(char not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.:-' for char in value)):
        raise ValueError('Finite Backend Identifier required')
    return value


def membership(root):
    """The exact owned payload, including data/native/NOTICE, never a trim."""
    pending, names = [root], set()
    while pending:
        directory = pending.pop()
        for item in directory.iterdir():
            info = item.lstat()
            if item.is_symlink() or getattr(info, 'st_file_attributes', 0) & 1024:
                raise ValueError('Linked payload member denied')
            if item.is_dir():
                pending.append(item)
            elif item.is_file():
                names.add(item.relative_to(root).as_posix())
            else:
                raise ValueError('Nonregular payload member denied')
    return names


def produce(plan, output):
    host, _ = read(plan['host_image'])
    if not 0 < host['bytes'] <= 9_223_372_036_854_775_807:
        raise ValueError('Final linked host image required')
    manifest, manifest_raw = checked(plan['payload_manifest'], limit=16 * 1024 * 1024)
    if Path(manifest['path']).name != 'InstallationManifest.json':
        raise ValueError('The unique payload manifest basename is required')
    payload_root = physical(Path(manifest['path']).parent)
    composition_root = physical(plan['composition_root'])
    host_path = Path(host['path'])
    if host_path.is_relative_to(payload_root) or output.is_relative_to(payload_root):
        raise ValueError('Host and external receipt cannot be payload members')
    if not host_path.is_relative_to(composition_root) or not payload_root.is_relative_to(composition_root):
        raise ValueError('Installation composition must contain actual host and payload')
    installation = document(manifest_raw)
    if (installation['format'] != 'native-engine-installation-v2-candidate'
            or installation['launcher_mode'] != 'indexed_python'):
        raise ValueError('Complete indexed payload required; no plain CLI fallback')
    files, seen, source_facts = [], set(), [manifest, host]
    for row in installation['files']:
        name = relative(row['relative_path'])
        if name.casefold() in seen or type(row['bytes']) is not int or not 0 <= row['bytes'] <= 9_223_372_036_854_775_807:
            raise ValueError('Duplicate or invalid complete file map')
        seen.add(name.casefold())
        fact, _ = checked(dict(path=str(payload_root / name), bytes=row['bytes'], sha256=row['sha256']))
        source_facts.append(fact)
        files.append(dict(relative_path=name, bytes=fact['bytes'], sha256=fact['sha256']))
    # The manifest itself is held independently and belongs to the complete
    # installation map. It contains no host SHA/receipt/control record.
    if 'installationmanifest.json' in seen:
        raise ValueError('Payload manifest cannot contain its own digest')
    files.append(dict(relative_path=Path(manifest['path']).name, bytes=manifest['bytes'], sha256=manifest['sha256']))
    files.sort(key=lambda row: row['relative_path'])
    by_name = {row['relative_path']: row for row in files}
    if membership(payload_root) != set(by_name):
        raise ValueError('Full physical payload membership differs; no omitted files admitted')
    engine = plan['engine_file_names']
    if (type(engine) is not list or not engine or engine != sorted(set(engine))
            or not set(engine) < set(by_name)):
        raise ValueError('Exact sorted nonempty Engine strict partition required')
    # Preserve NativeLaunchContext's original noncompact files-array bound.
    if len(json.dumps(files, ensure_ascii=False, allow_nan=False).encode('utf-8')) > 32 * 1024 * 1024 - 16384:
        raise ValueError('Complete map exceeds the original context margin')
    identities = {}
    for field in ('registration', 'resource_manifest', 'runtime_manifest'):
        name = relative(plan['identity_files'][field])
        identities[field + '_sha256'] = by_name[name]['sha256']
    refs, distinct = [], set()
    for row in plan['evidence_inputs']:
        if row['kind'] not in ('host_source', 'lockfile', 'tool', 'producer_input', 'license', 'qualification'):
            raise ValueError('Unknown Backend build evidence kind')
        key = (row['kind'], identifier(row['reference_id']))
        if key in distinct:
            raise ValueError('Duplicate build evidence')
        distinct.add(key)
        fact, _ = checked(row)
        source_facts.append(fact)
        refs.append(dict(kind=key[0], reference_id=key[1], content_sha256=fact['sha256']))
    if not 4 <= len(refs) <= 256 or not {'host_source', 'lockfile', 'tool', 'producer_input'} <= {row['kind'] for row in refs}:
        raise ValueError('Actual source/lock/tool/producer evidence required')
    receipt = dict(format='native-build-receipt-v1', build_id=identifier(plan['build_id']),
                   target=identifier(plan['target']), host_image_bytes=host['bytes'],
                   host_image_sha256=host['sha256'], payload_manifest_sha256=manifest['sha256'],
                   evidence_refs=refs, **identities)
    receipt_raw = canonical(receipt)
    proposal = dict(composition_root=str(composition_root), installed_native_image=str(host_path),
                    installed_native_image_bytes=host['bytes'], installed_native_image_sha256=host['sha256'],
                    payload_root=str(payload_root), payload_manifest_sha256=manifest['sha256'],
                    expected_files=files, engine_file_names=engine, build_receipt=receipt,
                    build_receipt_sha256=digest(receipt_raw), **identities)
    # Final revalidation does not claim a Windows deny-write guard or build
    # sandbox. The fixed build runner must retain its independent provenance.
    for fact in source_facts:
        checked(fact)
    if membership(payload_root) != set(by_name):
        raise ValueError('Payload membership changed during production')
    output.mkdir()
    for name, raw in [('NativeBuildReceipt.json', receipt_raw), ('NativeInstallationInputs.json', canonical(proposal)),
                      ('ProducerFacts.json', canonical(dict(source_files=source_facts, host_embeds_receipt=False,
                       owner_action=False, qualification='not_admitted', artifacts_are_build_facts_only=True)))]:
        with (output / name).open('xb') as stream:
            stream.write(raw)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--input-sha256', required=True)
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    _, raw = read(args.input, limit=32 * 1024 * 1024)
    if digest(raw) != args.input_sha256:
        raise ValueError('Fixed producer input changed')
    output = Path(args.output_dir)
    if not output.is_absolute() or output.exists():
        raise ValueError('Fresh independently owned output required')
    physical(output.parent)
    produce(document(raw), output)


if __name__ == '__main__':
    main()
