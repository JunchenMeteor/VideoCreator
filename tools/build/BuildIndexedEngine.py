"""Fresh indexed candidate from fixed payload + ordinary source; no engine import.

This builder records complete physical package data instead of trimming a static
import graph. Its policy/manifest are build identities, not self-issued runtime
or distribution qualifications.
"""
from __future__ import annotations

import argparse
import base64
import csv
import email.parser
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import time
import zipfile
import _imp

REPO = Path(__file__).resolve().parents[2]

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def pin(root, path):
    return {'relative_path': path.relative_to(root).as_posix(), 'bytes': path.stat().st_size, 'sha256': sha(path)}

def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8', newline='\n')

def walk(root):
    pending = [root]
    seen = set()
    while pending:
        directory = pending.pop()
        physical = directory.resolve(strict=True)
        if physical in seen:
            raise ValueError('Repeated physical directory')
        seen.add(physical)
        for item in sorted(directory.iterdir()):
            stat = item.lstat()
            if item.is_symlink() or getattr(stat, 'st_file_attributes', 0) & 1024:
                raise ValueError('Linked resource input')
            if item.is_dir():
                pending.append(item)
            elif item.is_file():
                yield item
            else:
                raise ValueError('Non-file resource input')

def checked_document(path, expected):
    if sha(path) != expected:
        raise ValueError('Pinned document changed: ' + str(path))
    return json.loads(path.read_text(encoding='utf-8'))

def refresh_asr_resource_index(root):
    """Rebind changed isolated runtime bytes; never inherit execution admission."""
    asr = root/'LocalAsr'
    resource = json.loads((asr/'ResourceManifest.json').read_text(encoding='utf-8'))
    old = json.loads((asr/'RuntimeFileManifest.json').read_text(encoding='utf-8'))
    files = {file.relative_to(asr).as_posix():pin(asr,file) for file in walk(asr)
             if file.name not in ('ResourceManifest.json','RuntimeFileManifest.json')}
    if set(files) != {item['relative_path'] for item in old['files']} | {'Runtime/Python/python313._pth'}:
        raise ValueError('ASR input index membership differs; no omitted resource allowed')
    for key in ('provider','worker','loader'):
        if sha(asr/resource[key]) != resource[key+'_sha256']:
            raise ValueError('ASR protocol source changed outside admitted overlay')
    resource.update(schema='indexed-engine-ASR-resource-candidate',
                    execution_qualification='not_admitted', actual_compute_type=None,
                    actual_execution_configuration_sha256=None,
                    factory_registration='requires-indexed-child-launch-consumer',
                    whole_engine_sidecar=False)
    save(asr/'RuntimeFileManifest.json',{'schema':'indexed-engine-ASR-resource-index-candidate',
                                      'files':[files[name] for name in sorted(files)]})
    save(asr/'ResourceManifest.json',resource)

def module_index(files, roots, ownership, extension_suffixes):
    modules, namespaces = {}, {}
    for root in roots:
        prefix = root + '/'
        for name in files:
            if not name.startswith(prefix):
                continue
            parts = Path(name[len(prefix):]).parts
            suffix = Path(parts[-1]).suffix
            if suffix not in {'.py', '.pyd'}:
                continue
            leaf = Path(parts[-1]).stem.split('.', 1)[0]
            package = leaf == '__init__'
            segments = (*parts[:-1],) if package else (*parts[:-1], leaf)
            if not segments or any(not item.isidentifier() for item in segments):
                continue
            fullname = '.'.join(segments)
            directory = str(Path(name).parent).replace('\\', '/')
            parent = directory.rsplit('/', 1)[0] if package else directory
            if suffix == '.pyd' and not any(parts[-1] == leaf+tag for tag in extension_suffixes):
                raise ValueError('Extension suffix not supported by this CPython: '+name)
            record = {'kind': 'package' if package else ('extension' if suffix == '.pyd' else 'source'),
                      'file': name, 'directory': directory, 'parent_directory': parent,
                      'root':root, 'top_level': len(segments) == 1}
            if fullname in modules and modules[fullname] != record:
                previous=modules[fullname]
                pair=[previous,record]
                if 'variants' in previous or {item['kind'] for item in pair}!={'source','extension'} or previous['directory']!=directory or previous['root']!=root:
                    raise ValueError('Module fullname collision: ' + fullname)
                owners=[ownership.get(item['file'],[]) for item in pair]
                if len(owners[0])!=1 or owners[0]!=owners[1]:
                    raise ValueError('Module variant lacks unique same-distribution ownership: '+fullname)
                selected=next(item for item in pair if item['kind']=='extension')
                modules[fullname]={**selected,'variants':[{**item,'identity':files[item['file']]} for item in pair],
                    'selection':{'rule':'CPython ExtensionFileLoader before SourceFileLoader',
                                 'distribution':owners[0][0],'selected':selected['file'],
                                 'extension_suffixes':extension_suffixes,
                                 'runtime_fallback':'none; required extension load failure remains a failure'}}
            else:
                modules[fullname] = record
            for count in range(1, len(segments)):
                parent_name = '.'.join(segments[:count])
                portion = root + '/' + '/'.join(segments[:count])
                namespaces.setdefault(parent_name, set()).add(portion)
    folded = {}
    for fullname in set(modules) | set(namespaces):
        if fullname.casefold() in folded and folded[fullname.casefold()] != fullname:
            raise ValueError('Case-insensitive module collision')
        folded[fullname.casefold()] = fullname
    for fullname, portions in namespaces.items():
        if fullname not in modules:
            parent = next(iter(portions)).rsplit('/', 1)[0] if len(portions) == 1 else None
            modules[fullname] = {'kind': 'namespace', 'portions': sorted(portions), 'parent_directory': parent,
                                 'parent_directories': sorted({portion.rsplit('/', 1)[0] for portion in portions}),
                                 'top_level': '.' not in fullname}
    return modules

def distribution_index(root, files, site):
    distributions = []
    for name in sorted(files):
        if not name.startswith(site + '/') or not name.endswith('.dist-info/METADATA'):
            continue
        folder = name.rsplit('/', 1)[0]
        metadata = email.parser.Parser().parsestr((root/name).read_text(encoding='utf-8'))
        metadata_files = {Path(item).name:item for item in files if str(Path(item).parent).replace('\\','/') == folder}
        entry = {'name':metadata['Name'], 'version':metadata['Version'], 'root':site,
                 'metadata_directory':folder, 'metadata_files':metadata_files,
                 'metadata_identities':{key:files[path] for key,path in metadata_files.items()}}
        if not entry['name'] or not entry['version']:
            raise ValueError('Distribution metadata missing name/version')
        distributions.append(entry)
    normalized = [item['name'].lower().replace('-','_').replace('.','_') for item in distributions]
    if len(set(normalized)) != len(normalized):
        raise ValueError('Conflicting distribution metadata')
    return distributions

def distribution_ownership(root, files, distributions):
    """RECORD-owned identity, never package-name or directory-prefix guessing."""
    owners={}
    for distribution in distributions:
        record=distribution['metadata_files'].get('RECORD')
        if record is None:
            continue
        with (root/record).open(encoding='utf-8',newline='') as stream:
            for row in csv.reader(stream):
                if len(row)!=3:
                    raise ValueError('Malformed installed distribution RECORD')
                path=(root/distribution['root']/row[0]).resolve()
                if not path.is_relative_to(root):
                    raise ValueError('Distribution RECORD escapes resource installation')
                relative=path.relative_to(root).as_posix()
                if relative not in files or not row[1].startswith('sha256=') or not row[2]:
                    continue
                digest=base64.urlsafe_b64decode(row[1].removeprefix('sha256=')+'='*((-len(row[1].removeprefix('sha256=')))%4)).hex()
                if digest!=files[relative]['sha256'] or int(row[2])!=files[relative]['bytes']:
                    raise ValueError('Distribution RECORD file identity differs: '+relative)
                owners.setdefault(relative,[]).append(distribution['metadata_directory'])
    return owners


ALIAS_BASENAME='msvcp140-a4c2229bdc2a2a630acdc095b4d86008.dll'
ALIAS_SHA256='a4c2229bdc2a2a630acdc095b4d86008e5c3e3bc7773174354f3da4f5beb9cde'

def pe_machine(path):
    with path.open('rb') as stream:
        header=stream.read(64)
        if len(header)!=64 or header[:2]!=b'MZ':raise ValueError('Invalid native machine header')
        offset=int.from_bytes(header[60:64],'little')
        if offset>path.stat().st_size-6:raise ValueError('Invalid native header offset')
        stream.seek(offset);signature=stream.read(6)
        if len(signature)!=6 or signature[:4]!=b'PE\0\0':raise ValueError('Invalid native COFF header')
        return int.from_bytes(signature[4:6],'little')

def native_sccs(records):
    counter=0;stack=[];active=set();numbers={};low={};components=[]
    def visit(name):
        nonlocal counter
        numbers[name]=low[name]=counter;counter+=1;stack.append(name);active.add(name)
        for dependency in records[name]['payload_dependencies']:
            if dependency not in records:raise ValueError('Unindexed payload dependency')
            if dependency not in numbers:visit(dependency);low[name]=min(low[name],low[dependency])
            elif dependency in active:low[name]=min(low[name],numbers[dependency])
        if low[name]==numbers[name]:
            component=[]
            while True:
                member=stack.pop();active.remove(member);component.append(member)
                if member==name:break
            components.append(sorted(component))
    for name in sorted(records):
        if name not in numbers:visit(name)
    return sorted(components)

def native_index(root,files,prefix,pe_parser,declarations,ownership,distributions,role,extras=()):
    extra_dirs={Path(name).parent.as_posix() for name in extras}
    names=[name for name in files if (name.startswith(prefix+'/') or Path(name).parent.as_posix() in extra_dirs) and Path(name).suffix.lower() in {'.dll','.pyd','.exe'}]
    by_basename={}
    for name in names:by_basename.setdefault(Path(name).name.casefold(),[]).append(name)
    parsed={name:pe_parser(root/name) for name in names}
    machines={name:pe_machine(root/name) for name in names}
    if any(item['status']!='static_tables_only' for item in parsed.values()):raise ValueError('Native table unavailable')
    by_owner={item['metadata_directory']:item for item in distributions}
    aliases=[];members={}
    candidates=by_basename.get(ALIAS_BASENAME,[])
    if candidates:
        canonical=prefix+'/Lib/site-packages/numpy.libs/'+ALIAS_BASENAME
        expected={canonical} if role=='asr' else {canonical,prefix+'/Lib/site-packages/google_re2.libs/'+ALIAS_BASENAME}
        if set(candidates)!=expected:raise ValueError('Finite alias member set differs')
        identities=[]
        for member in sorted(expected):
            owner=ownership.get(member,[])
            if len(owner)!=1 or owner[0] not in by_owner:raise ValueError('Alias RECORD owner not unique')
            distribution=by_owner[owner[0]]
            wanted=('numpy','2.5.3') if '/numpy.libs/' in member else ('google-re2','1.1.20251105')
            if (distribution['name'].lower().replace('_','-'),distribution['version'])!=wanted:raise ValueError('Alias owner version differs')
            if files[member]['bytes']!=575056 or files[member]['sha256']!=ALIAS_SHA256 or machines[member]!=0x8664:raise ValueError('Alias bytes/PE machine differ')
            if parsed[member]!=parsed[canonical]:raise ValueError('Alias static/delay table differs')
            record=distribution['metadata_files'].get('RECORD')
            if record is None:raise ValueError('Alias RECORD absent')
            identities.append({'identity':files[member],'machine':machines[member],'owner':owner[0],'owner_name':wanted[0],'owner_version':wanted[1],'owner_record':files[record]})
        group={'id':role+':numpy-re2-vc-alias','profile':role,'basename':ALIAS_BASENAME,'canonical':canonical,'members':identities,'importer_bindings':[],
               'expected_actual_origin':canonical,'preload':'dependencies_then_canonical_before_vendor_init','dynamic_requests':'exact declared owner member or exact group basename only',
               'qualification':'actual pre/post handle-origin and delayed/dynamic proof pending'}
        aliases.append(group);members={item['identity']['relative_path']:group for item in identities}
    records={};contracts={}
    for name in names:
        payload=[];sysdeps=[];unknown=[];alias_edges=[]
        for dependency in sorted(set(parsed[name]['imports']+parsed[name]['delay_imports'])):
            candidates=by_basename.get(dependency.casefold(),[])
            table='delay' if dependency in parsed[name]['delay_imports'] else 'normal'
            if dependency.casefold()==ALIAS_BASENAME and candidates and all(item in members for item in candidates):
                group=members[candidates[0]];owners=ownership.get(name,[])
                requested=[item['identity']['relative_path'] for item in group['members'] if owners==[item['owner']]]
                if len(requested)!=1:unknown.append({'name':dependency,'reason':'alias_importer_owner_not_unique','candidates':candidates});continue
                payload.append(group['canonical'])
                edge={'importer':name,'owner':owners[0],'requested_member':requested[0],'canonical':group['canonical'],'group_id':group['id'],'table':table}
                alias_edges.append(edge);group['importer_bindings'].append(edge)
            elif len(candidates)==1:payload.append(candidates[0])
            elif candidates:unknown.append({'name':dependency,'reason':'basename_collision','candidates':candidates})
            elif dependency.casefold() in declarations:
                declaration=declarations[dependency.casefold()]
                contract=contracts.setdefault(declaration['id'],dict(declaration,profiles=[role],importers=[]))
                contract['importers'].append({'file':name,'profile':role,'table':table});sysdeps.append(declaration['id'])
            else:unknown.append({'name':dependency,'reason':'no_exact_source_contract','table':table})
        records[name]={'identity':files[name],'machine':machines[name],'payload_dependencies':sorted(set(payload)),
                       'system_contract_dependencies':sorted(set(sysdeps)),'alias_dependencies':alias_edges,'unresolved':unknown,
                       'static_imports':parsed[name]['imports'],'delay_imports':parsed[name]['delay_imports'],'dynamic_requests':'unknown controlled requests rejected; actual qualification pending'}
    components=native_sccs(records)
    for group in aliases:
        seen=set();todo=[group['canonical']]
        while todo:
            current=todo.pop()
            if current in seen:continue
            seen.add(current);todo.extend(records[current]['payload_dependencies'])
        group['dependency_closure']={name:records[name] for name in sorted(seen)}
        group['dependency_closure_sha256']=hashlib.sha256(json.dumps(group['dependency_closure'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
        group['finite_sccs']=[item for item in components if set(item)&seen]
    return records,contracts,aliases,components

def conditional_directories(files,prefix,distributions,role):
    if role!='asr':return []
    source=prefix+'/Lib/site-packages/ctranslate2/__init__.py'
    owner=[item for item in distributions if item['name'].lower()=='ctranslate2' and item['version']=='4.8.2']
    if len(owner)!=1 or files.get(source,{}).get('sha256')!='a2a1954f726c88d527279d0284695f6011285ee6f7bd75ba76e61c1bdb2be646':raise ValueError('CT2 conditional caller differs')
    return [{'profile':role,'relative_path':prefix+'/Lib/site-packages/'+name+'/bin','owner':owner[0]['metadata_directory'],'module':'ctranslate2','source':files[source],
             'platform':'windows-amd64','compute_profile':'cpu','mode':'absence_only','reason':'fixed package probes optional ROCm siblings and catches FileNotFoundError/OSError',
             'present_policy':'reject_unindexed_content','caller':'registered_exact_compiled_code_object'} for name in ('_rocm_sdk_core','_rocm_sdk_libraries_custom')]

def main():
    parser=argparse.ArgumentParser()
    for field in ('base-stage','base-index','backend-snapshot','contract-freeze','production-lock','interpreter-facts','system-contract-source','target','owner-dir','receipt'):
        parser.add_argument('--'+field,required=True,type=Path)
    for field in ('base-index-sha256','base-installation-sha256','backend-snapshot-sha256','contract-freeze-sha256','production-lock-sha256','interpreter-facts-sha256','system-contract-source-sha256','artifact-version'):
        parser.add_argument('--'+field,required=True)
    parser.add_argument('--production-input-plan',type=Path)
    parser.add_argument('--production-input-plan-sha256')
    args=parser.parse_args()
    production = None
    production_builder = None
    if bool(args.production_input_plan) != bool(args.production_input_plan_sha256):
        raise ValueError('Production input plan and its exact SHA must be supplied together')
    if args.production_input_plan:
        # Own build-only data module, never an Engine/provider or arbitrary plugin.
        production_spec=importlib.util.spec_from_file_location('_fixed_production_build',REPO/'tools/build/BuildProductionResources.py')
        production_builder=importlib.util.module_from_spec(production_spec)
        production_spec.loader.exec_module(production_builder)
        production = production_builder.prepare(args.production_input_plan,
            args.production_input_plan_sha256,args.backend_snapshot_sha256)
    root=args.target
    owner=args.owner_dir.resolve(strict=True)
    if not root.is_absolute() or root.parent.resolve(strict=True)!=owner or root.exists():
        raise ValueError('Fresh exact owned stage required')
    for ancestor in owner.parents:
        if ancestor.is_symlink() or ancestor.is_junction():
            raise ValueError('Linked owner ancestor')
    if owner.is_symlink() or owner.is_junction():
        raise ValueError('Linked owner directory')
    base=args.base_stage.resolve(strict=True)
    if root==base or root.is_relative_to(base) or base.is_relative_to(root):
        raise ValueError('Original stage must be preserved')
    old_index=checked_document(args.base_index,args.base_index_sha256)
    snapshot=checked_document(args.backend_snapshot,args.backend_snapshot_sha256)
    contracts=checked_document(args.contract_freeze,args.contract_freeze_sha256)
    fact_receipt=checked_document(args.interpreter_facts,args.interpreter_facts_sha256)
    facts=fact_receipt['facts']
    declarations=checked_document(args.system_contract_source,args.system_contract_source_sha256)
    if declarations['format']!='windows-native-contract-declarations-v1':raise ValueError('System contract declaration version differs')
    for key,record in declarations['records'].items():
        if key!=key.casefold() or record['basename']!=key or '/' in key or '\\' in key or record['source_kind'] not in ('windows_component','api_set','external_vc'):raise ValueError('Invalid exact source declaration')
    if fact_receipt['actual_exit']!=0 or fact_receipt['timeout_sticky'] or fact_receipt['forced'] or fact_receipt['source_changes'] or fact_receipt['child']['actual_exit']!=0 or not fact_receipt['child']['natural_terminal']:
        raise ValueError('Exact interpreter fact batch did not finish naturally')
    if facts['implementation']!=sys.implementation.name or facts['python_version']!=list(sys.version_info[:3]) or set(facts['builtins'])!=set(sys.builtin_module_names) or set(facts['frozen'])!=set(_imp._frozen_module_names()):
        raise ValueError('Actual interpreter builtin/frozen facts differ from builder')
    if not facts['hash_primitive_builtin'] or '_sha2' not in facts['builtins']:
        raise ValueError('No admitted builtin bootstrap hash primitive')
    if sha(args.production_lock)!=args.production_lock_sha256:
        raise ValueError('Pinned production lock changed')
    if contracts['backend_snapshot']['sha256'] != args.backend_snapshot_sha256:
        raise ValueError('Backend/contract export source version mismatch')
    original={item['relative_path']:item for item in old_index['files']}
    # The old index and its separately held installation document are provenance
    # inputs too; nothing may be silently omitted from the source directory.
    for filename in ('EngineFileManifest.json','CandidateInstallationManifest.json'):
        path=base/filename
        expected=args.base_index_sha256 if filename=='EngineFileManifest.json' else args.base_installation_sha256
        if sha(path)!=expected:
            raise ValueError('Base manifest changed')
        original[filename]=pin(base,path)
    members={file.relative_to(base).as_posix() for file in walk(base)}
    if members != set(original):
        raise ValueError('Base stage directory membership differs')
    for name,item in original.items():
        if pin(base,base/name) != {key:item[key] for key in ('relative_path','bytes','sha256')}:
            raise ValueError('Base resource changed: '+name)
    for relative,item in snapshot['source_map'].items():
        source=Path(item['ordinary_copy'])
        if production:
            target = ('Code/'+relative.removeprefix('services/engine/src/')
                      if relative.startswith('services/engine/src/') else
                      'Migrations/'+relative.removeprefix('services/engine/migrations/'))
            selected_source = production['sources'].get(target)
            expected = Path(selected_source['path']) if selected_source else None
        else:
            expected=args.backend_snapshot.parent/'FinalSourceCopies'/relative
        if expected is None or source.resolve(strict=True)!=expected.resolve(strict=True) or sha(source)!=item['sha256'] or source.stat().st_size!=item.get('bytes',item.get('size')):
            raise ValueError('Ordinary Backend input mismatch')
    if shutil.disk_usage(owner).free < sum(item['bytes'] for item in original.values())*2+512*1024*1024:
        raise ValueError('Insufficient isolated stage space')
    report={'status':'BUILDING','actual_exit':None,'started_at_ns':time.time_ns(),'ended_at_ns':None,'source_stage':str(base),'target':str(root),'original_stage_modified':False,'product_import_or_run':False,'source_changes':[]}
    args.receipt.parent.mkdir(parents=True,exist_ok=True)
    save(args.receipt,report)
    root.mkdir()
    try:
        for name,item in original.items():
            destination=root/name
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(base/name,destination)
            if sha(destination)!=item['sha256'] or sha(base/name)!=item['sha256']:
                raise ValueError('Copy/source drift')
        overlay=[]
        for relative,item in snapshot['source_map'].items():
            if relative.startswith('services/engine/src/'):
                target='Code/'+relative.removeprefix('services/engine/src/')
            elif relative.startswith('services/engine/migrations/'):
                target='Migrations/'+relative.removeprefix('services/engine/migrations/')
            else:
                raise ValueError('Unexpected Backend source')
            destination=root/target
            destination.parent.mkdir(parents=True,exist_ok=True)
            before=sha(destination) if destination.exists() else None
            shutil.copyfile(item['ordinary_copy'],destination)
            if sha(destination)!=item['sha256']:
                raise ValueError('Overlay copy mismatch')
            overlay.append({'target':target,'old_sha256':before,'source':item})
        if production:
            production_builder.overlay(root,production)
        provenance=root/'Provenance'
        provenance.mkdir()
        shutil.copyfile(args.production_lock,provenance/'uv.lock')
        shutil.copyfile(args.system_contract_source,provenance/'WindowsNativeContracts.json')
        if sha(provenance/'uv.lock')!=args.production_lock_sha256:
            raise ValueError('Production lock copy mismatch')
        bootstrap=root/'Bootstrap'
        bootstrap.mkdir()
        for filename in ('IndexedBootstrap.py','IndexedLoader.py'):
            shutil.copyfile(REPO/'packaging/python'/filename,bootstrap/filename)
        runtime=root/'Runtime/Python'
        if sha(runtime/'python.exe') != sha(Path(sys.base_prefix)/'python.exe') or tuple(sys.version_info[:3])!=(3,13,16) or '_sha2' not in sys.builtin_module_names:
            raise ValueError('Bootstrap/runtime builtin facts need exact CPython admission')
        archive=bootstrap/'BaseStdlib.zip'
        with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_STORED) as output:
            for file in walk(runtime/'Lib'):
                if file.is_relative_to(runtime/'Lib/site-packages') or file.suffix!='.py':
                    continue
                info=zipfile.ZipInfo(file.relative_to(runtime/'Lib').as_posix(),date_time=(2026,1,1,0,0,0))
                output.writestr(info,file.read_bytes())
            for filename in ('IndexedBootstrap.py','IndexedLoader.py'):
                output.writestr('_video_creator_boot/'+filename,(bootstrap/filename).read_bytes())
            output.writestr('_video_creator_boot/__init__.py',b'"""Trusted build bootstrap only."""\n')
        (runtime/'python313._pth').write_text('../../Bootstrap/BaseStdlib.zip\n',encoding='utf-8',newline='\n')
        asr_runtime=root/'LocalAsr/Runtime/Python'
        if sha(asr_runtime/'python.exe') != sha(runtime/'python.exe'):
            raise ValueError('ASR profile interpreter differs from the exact base')
        (asr_runtime/'python313._pth').write_text('../../../Bootstrap/BaseStdlib.zip\n',encoding='utf-8',newline='\n')
        refresh_asr_resource_index(root)
        production_outputs = production_builder.build(root,production) if production else None
        files={item['relative_path']:item for item in (pin(root,file) for file in walk(root))}
        helper_path=REPO/'tools/build/EngineResourceInventory.py'
        spec=importlib.util.spec_from_file_location('_fixed_pe_inventory',helper_path)
        helper=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        profiles={};system_contracts={};native_alias_groups=[];conditional_search_directories=[]
        tools=['LocalAsr/Media/FFmpeg/bin/ffmpeg.exe','LocalAsr/Media/FFmpeg/bin/ffprobe.exe']
        if production:
            tools=[production['drivers']['edit'][name] for name in ('ffmpeg','ffprobe')]
        for name,command,entry,prefix,code in [('api','serve','video_creator.cli.main','Runtime/Python','Code'),('worker','worker','video_creator.cli.main','Runtime/Python','Code'),('mcp','mcp-stdio','video_creator.cli.main','Runtime/Python','Code'),('asr',None,'video_creator.media.asr_worker','LocalAsr/Runtime/Python','LocalAsr/Code'),('owner-setup',None,'video_creator.cli.native_owner_setup','Runtime/Python','Code'),('owner-setup-trust',None,'video_creator.cli.native_owner_setup','Runtime/Python','Code'),('owner-setup-qualified-install',None,'video_creator.cli.native_owner_setup','Runtime/Python','Code')]:
            site=prefix+'/Lib/site-packages'
            roots=[code,site,site+'/win32',site+'/win32/lib',site+'/pythonwin',site+'/pywin32_system32',prefix+'/Lib',prefix+'/DLLs']
            distributions=distribution_index(root,files,site)
            ownership=distribution_ownership(root,files,distributions)
            extension_suffixes=list(_imp.extension_suffixes())
            modules=module_index(files,roots,ownership,extension_suffixes)
            native,system,aliases,components=native_index(root,files,prefix,helper.pe_imports,declarations['records'],ownership,distributions,name,tools)
            for contract_id,record in system.items():
                if contract_id not in system_contracts:system_contracts[contract_id]=record
                else:
                    system_contracts[contract_id]['profiles'].extend(record['profiles'])
                    system_contracts[contract_id]['importers'].extend(record['importers'])
            native_alias_groups.extend(aliases)
            conditional_search_directories.extend(conditional_directories(files,prefix,distributions,name))
            if entry not in modules:
                raise ValueError('Role entry absent: '+name)
            profiles[name]={'name':name,'implementation':facts['implementation'],'python_version':facts['python_version'],'builtins':facts['builtins'],'frozen':facts['frozen'],'executable':prefix+'/python.exe','entry_module':entry,'command':command,'module_roots':roots,'modules':modules,'native':native,'system_contract_ids':sorted(system),'native_sccs':components,'distributions':distributions,'tool_executables':tools,'bootstrap':'Bootstrap/IndexedBootstrap.py','bootstrap_archive':'Bootstrap/BaseStdlib.zip','required_migration_files':sorted(item for item in files if item.startswith('Migrations/')),'execution_qualification':'independent actual runtime/native/role qualification pending'}
            profiles[name]['adapter_module']='video_creator.cli.native_startup' if name in ('api','worker','mcp') else None
            profiles[name]['adapter_callable']='main_qualified' if name in ('api','worker','mcp') else None
        if (len(profiles['api']['distributions']) < 148 if production
                else len(profiles['api']['distributions']) != 148):
            raise ValueError('Expected147 production distributions plus internal engine metadata; no dependency trimming allowed')
        migrations=sorted(item for item in files if item.startswith('Migrations/'))
        snapshot_migrations=sorted(path[len('services/engine/migrations/'):]
            for path in snapshot['source_map'] if path.startswith('services/engine/migrations/'))
        if not snapshot_migrations or migrations!=['Migrations/'+name for name in snapshot_migrations]:
            raise ValueError('Complete exact formal Backend migration source set required')
        policy={'format':'portable-engine-load-policy-v2-candidate','artifact_version':args.artifact_version,'platform':'windows-amd64','python_abi':'cp313','backend_snapshot_sha256':args.backend_snapshot_sha256,'contract_freeze_sha256':args.contract_freeze_sha256,'source_identity':{'base_file_manifest_sha256':args.base_index_sha256,'base_installation_manifest_sha256':args.base_installation_sha256,'production_lock':files['Provenance/uv.lock'],'interpreter_fact_receipt_sha256':args.interpreter_facts_sha256,'backend_ordinary_source_count':len(snapshot['source_map']),'overlay':overlay},'boot':{'archive':'Bootstrap/BaseStdlib.zip','bootstrap':'Bootstrap/IndexedBootstrap.py','hash_primitive':'builtin:_sha2.sha256','preboot_source_scope':'exact host-held ZIP_STORED CPython pure stdlib plus build bootstrap modules; physical Code/site-packages not exposed','system_condition':'exact CPython/native payload and trusted Windows system/CRT sources require separate real qualification'},'files':list(files.values()),'profiles':profiles,'system_contracts':system_contracts,'native_alias_groups':native_alias_groups,'conditional_search_directories':conditional_search_directories,'data':{name:{'purpose':'physical-package-or-service-resource'} for name in files},'source_state':'B18 support/W14 media source-only candidate; B17/W15 not included','namespace_native_qualification':'pending independent actual proof','threat_boundary':'index and controlled requests; not an absolute same-user native filesystem sandbox'}
        if production:
            production_native={}
            for group in production['groups']:
                if group['role']!='piper':
                    continue
                prefix=group['prefix']+'/'+group['python_prefix']
                site=prefix+'/Lib/site-packages'
                distributions=distribution_index(root,files,site)
                ownership=distribution_ownership(root,files,distributions)
                native,system,aliases,components=native_index(root,files,prefix,helper.pe_imports,
                    declarations['records'],ownership,distributions,'piper-resource')
                production_native[prefix]={'native':native,'distributions':distributions,
                    'system_contracts':system,'native_alias_groups':aliases,'native_sccs':components,
                    'qualification':'static data only; real Piper child/ABI/licence observation not admitted'}
            policy['source_state']='explicit immutable current-production input; no hot Backend source or qualification inheritance'
            # Document is deny_unknown_fields in the existing native consumer.
            # Provenance belongs in its existing data-valued source_identity.
            policy['source_identity']['production_resources']={'input_plan':production['plan_fact'],'outputs':production_outputs,
                'source_provenance':production['source_provenance'],'resource_groups':production['groups'],
                'native_resource_indices':production_native,
                'qualification':'not_admitted; complete native ABI, licence and role observations required'}
        save(root/'LoadPolicy.json',policy)
        files['LoadPolicy.json']=pin(root,root/'LoadPolicy.json')
        save(root/'IndexedFileManifest.json',{'format':'portable-engine-file-index-v2-candidate','artifact_version':args.artifact_version,'files':list(files.values()),'overlay':overlay,'backend_snapshot_sha256':args.backend_snapshot_sha256,'contract_freeze_sha256':args.contract_freeze_sha256})
        files['IndexedFileManifest.json']=pin(root,root/'IndexedFileManifest.json')
        installation={'format':'native-engine-installation-v2-candidate','launcher_mode':'indexed_python','artifact_version':args.artifact_version,'executable':'Runtime/Python/python.exe','bootstrap':'Bootstrap/IndexedBootstrap.py','bootstrap_archive':'Bootstrap/BaseStdlib.zip','load_policy':'LoadPolicy.json','load_policy_sha256':sha(root/'LoadPolicy.json'),'migrations_directory':'Migrations','migrations_files':migrations,'backend_snapshot_sha256':args.backend_snapshot_sha256,'contract_freeze_sha256':args.contract_freeze_sha256,'files':list(files.values()),'ffmpeg':tools[0],'ffprobe':tools[1]}
        save(root/'InstallationManifest.json',installation)
        if production:
            production_builder.recheck(production)
        for relative,item in snapshot['source_map'].items():
            if sha(Path(item['ordinary_copy']))!=item['sha256']:
                report['source_changes'].append(relative)
        if sha(args.system_contract_source)!=args.system_contract_source_sha256:
            report['source_changes'].append('system_contract_source')
        if sha(args.production_lock)!=args.production_lock_sha256:
            report['source_changes'].append('production_lock')
        if sha(args.interpreter_facts)!=args.interpreter_facts_sha256:
            report['source_changes'].append('interpreter_facts')
        after_members={file.relative_to(base).as_posix() for file in walk(base)}
        if after_members!=set(original):
            report['source_changes'].append('source_stage_membership')
        for name,item in original.items():
            if pin(base,base/name)!={key:item[key] for key in ('relative_path','bytes','sha256')}:
                report['source_changes'].append('source_stage:'+name)
        if report['source_changes']:
            raise ValueError('Source changed during build')
        report.update(status='RESOURCE_CANDIDATE_BUILT_NOT_QUALIFIED',actual_exit=0,ended_at_ns=time.time_ns(),installation_manifest=pin(root,root/'InstallationManifest.json'),load_policy=pin(root,root/'LoadPolicy.json'),files=len(files)+1,source_stage_files_before=len(original),source_stage_files_after=len(after_members),source_stage_sha_size_membership_unchanged=True,production_distributions=len(profiles['api']['distributions'])-1,profile_counts={name:{'modules':len(item['modules']),'distributions':len(item['distributions']),'native':len(item['native']),'unresolved_native':sum(bool(record['unresolved']) for record in item['native'].values())} for name,item in profiles.items()})
        if production:
            report['production_resources']=production_outputs
    except Exception as error:
        report.update(status='FAILED_PARTIAL_PRESERVED',actual_exit=1,ended_at_ns=time.time_ns(),error=type(error).__name__+': '+str(error))
        save(args.receipt,report)
        raise
    save(args.receipt,report)
    print(json.dumps({'status':report['status'],'actual_exit':0,'files':report['files'],'profiles':report['profile_counts']},ensure_ascii=False))

if __name__=='__main__':
    main()
