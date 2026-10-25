"""Inventory pinned ordinary source and installed Windows payload; never import engine."""
from __future__ import annotations
import argparse,ast,base64,csv,email,hashlib,json,os,struct,sys,tomllib
from pathlib import Path,PurePosixPath

def sha(path:Path)->str:
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def walk(root:Path):
    seen=set()
    def visit(directory):
        resolved=directory.resolve(strict=True)
        if resolved in seen:raise ValueError('Repeated physical directory')
        seen.add(resolved)
        if directory.is_symlink() or getattr(directory.lstat(),'st_file_attributes',0)&1024:raise ValueError('Linked input directory')
        for item in sorted(directory.iterdir(),key=lambda p:p.name.casefold()):
            if item.is_symlink() or getattr(item.lstat(),'st_file_attributes',0)&1024:raise ValueError('Linked input resource')
            if item.is_dir():
                if item.name!='__pycache__':yield from visit(item)
            elif item.is_file() and item.suffix.lower() not in {'.pyc','.pyo'}:yield item
    yield from visit(root)

def pe_imports(path:Path)->dict:
    """Static import/delay tables only; this never loads a DLL and cannot prove runtime search."""
    try:
        with path.open('rb') as stream:
            def at(offset,count):
                if offset<0 or count<0 or offset+count>path.stat().st_size:raise ValueError('PE bounds')
                stream.seek(offset);data=stream.read(count)
                if len(data)!=count:raise ValueError('PE short read')
                return data
            if at(0,2)!=b'MZ':return {'status':'not_pe'}
            header=struct.unpack('<I',at(60,4))[0]
            if header>16*1024*1024 or at(header,4)!=b'PE\0\0':raise ValueError('PE signature')
            coff=at(header+4,20);sections=struct.unpack_from('<H',coff,2)[0];optional_size=struct.unpack_from('<H',coff,16)[0]
            optional=at(header+24,optional_size);magic=struct.unpack_from('<H',optional)[0]
            directory_offset=112 if magic==0x20b else 96 if magic==0x10b else None
            if directory_offset is None:raise ValueError('PE format')
            section_bytes=at(header+24+optional_size,sections*40)
            def offset(rva):
                for number in range(sections):
                    section=section_bytes[number*40:(number+1)*40]
                    size,virtual,raw_size,raw=struct.unpack_from('<IIII',section,8)
                    if virtual<=rva<virtual+max(size,raw_size):return raw+rva-virtual
                if rva<struct.unpack_from('<I',optional,60)[0]:return rva
                raise ValueError('PE RVA')
            def name(rva):
                position=offset(rva);value=bytearray()
                for index in range(1024):
                    byte=at(position+index,1)
                    if byte==b'\0':return value.decode('ascii').lower()
                    value.extend(byte)
                raise ValueError('PE DLL name limit')
            imports=[];delayed=[]
            for number,width,output in [(1,20,imports),(13,32,delayed)]:
                if directory_offset+(number+1)*8>len(optional):continue
                rva,size=struct.unpack_from('<II',optional,directory_offset+number*8)
                if not rva:continue
                position=offset(rva)
                for index in range(min(size//width+1,65536)):
                    descriptor=at(position+index*width,width)
                    if not any(descriptor):break
                    dll_rva=struct.unpack_from('<I',descriptor,12 if number==1 else 4)[0]
                    if number==13 and struct.unpack_from('<I',descriptor)[0]&1==0:
                        image_base=struct.unpack_from('<Q' if magic==0x20b else '<I',optional,24 if magic==0x20b else 28)[0]
                        dll_rva-=image_base
                    output.append(name(dll_rva))
            return {'status':'static_tables_only','imports':sorted(set(imports)),'delay_imports':sorted(set(delayed))}
    except (ValueError,struct.error,UnicodeError,OSError) as exc:return {'status':'unparsed','reason':type(exc).__name__}

def inventory(plan:dict):
    records=[];errors=[];excluded=[];packages=[]
    destinations={}
    def add(source,relative,origin,expected=None):
        source=Path(source);relative=PurePosixPath(relative).as_posix()
        if not relative or '\\' in relative or any(p in {'','..','.'} for p in PurePosixPath(relative).parts):raise ValueError('Unsafe output locator')
        if source.is_symlink() or getattr(source.lstat(),'st_file_attributes',0)&1024:raise ValueError('Linked source file')
        actual=sha(source)
        if expected is not None and expected!=actual:raise ValueError(f'Input digest mismatch: {relative}')
        existing=destinations.get(relative.casefold())
        if existing:
            if existing['sha256']!=actual:raise ValueError(f'Conflicting output bytes: {relative}')
            return
        entry={'relative_path':relative,'source':str(source),'bytes':source.stat().st_size,'sha256':actual,'origin':origin}
        if source.suffix.lower() in {'.exe','.dll','.pyd'}:entry['native']=pe_imports(source)
        records.append(entry);destinations[relative.casefold()]=entry
    for source in plan['sources']:add(source['path'],source['relative_path'],source['version'],source['sha256'])
    python_root=Path(plan['python_root'])
    for source in walk(python_root):
        rel=source.relative_to(python_root)
        if rel.parts[:2]==('Lib','site-packages') or source.suffix.lower()=='.pth':
            excluded.append({'source':str(source),'reason':'base-site/pth-not-executed'});continue
        add(source,'Runtime/Python/'+rel.as_posix(),'CPython3.13.16-owned-runtime')
    site=Path(plan['site_packages']);lock=tomllib.loads(Path(plan['uv_lock']['path']).read_text(encoding='utf-8'))
    # Explicit dependency metadata code only, isolated -S means no .pth processing.
    sys.path.append(str(site))
    from packaging.markers import Marker,default_environment
    marker_environment=default_environment();marker_environment['extra']=''
    normalize=lambda name:name.lower().replace('_','-').replace('.','-')
    locked={}
    for package in lock['package']:locked.setdefault(normalize(package['name']),[]).append(package)
    selected={};queue=[('video-creator-engine',set())]
    while queue:
        name,extras=queue.pop();candidates=locked.get(normalize(name),[])
        if len(candidates)!=1:errors.append({'kind':'lock-package-not-unique','name':name});continue
        package=candidates[0];old=selected.get(name)
        if old is not None and extras.issubset(old[1]):continue
        active=(old[1] if old else set())|extras;selected[name]=(package,active)
        dependencies=list(package.get('dependencies',[]))
        for extra in active:dependencies.extend(package.get('optional-dependencies',{}).get(extra,[]))
        for dependency in dependencies:
            marker=dependency.get('marker')
            if marker and not any(Marker(marker).evaluate({**marker_environment,'extra':extra}) for extra in active|{''}):continue
            queue.append((dependency['name'],set(dependency.get('extra',[]))))
    installed={}
    for directory in sorted(site.glob('*.dist-info')):
        message=email.message_from_string((directory/'METADATA').read_text(encoding='utf-8'))
        installed.setdefault(normalize(message['Name']),[]).append((directory,message))
    for name,(package,extras) in sorted(selected.items()):
        if name=='video-creator-engine':continue
        matches=installed.get(normalize(name),[])
        if len(matches)!=1 or matches[0][1]['Version']!=package['version']:
            errors.append({'kind':'installed-version-not-matching-lock','name':name,'locked':package['version']});continue
        directory,message=matches[0];record=directory/'RECORD'
        package_report={'name':name,'version':package['version'],'metadata_sha256':sha(directory/'METADATA'),'record_sha256':sha(record),'extras':sorted(extras),
                        'license':message.get('License'),'license_expression':message.get('License-Expression'),'license_files':message.get_all('License-File',[]),
                        'official_locked_wheels':package.get('wheels',[]),'copied_files':0,'record_hash_checked':0,'record_unhashed':0}
        with record.open(encoding='utf-8',newline='') as stream:
            for relative,encoded,size in csv.reader(stream):
                candidate=(site/Path(relative)).resolve(strict=True)
                if not candidate.is_relative_to(site.resolve()):
                    excluded.append({'source':str(candidate),'reason':'installed-console-script-outside-site-packages','package':name});continue
                if candidate.suffix.lower() in {'.pyc','.pyo','.pth'} or candidate.name=='direct_url.json' or candidate.name.startswith('_editable'):
                    excluded.append({'source':str(candidate),'reason':'cache/editable/pth/local-install-provenance','package':name});continue
                digest=sha(candidate)
                if encoded:
                    algorithm,expected=encoded.split('=',1)
                    if algorithm!='sha256':errors.append({'kind':'unexpected-record-algorithm','package':name,'file':relative})
                    elif base64.urlsafe_b64encode(bytes.fromhex(digest)).decode().rstrip('=')!=expected:errors.append({'kind':'installed-record-digest-mismatch','package':name,'file':relative})
                    else:package_report['record_hash_checked']+=1
                else:package_report['record_unhashed']+=1
                if size and int(size)!=candidate.stat().st_size:errors.append({'kind':'installed-record-size-mismatch','package':name,'file':relative})
                add(candidate,'Runtime/Python/Lib/site-packages/'+candidate.relative_to(site.resolve()).as_posix(),'locked-package:'+name+'=='+package['version'],digest)
                package_report['copied_files']+=1
        packages.append(package_report)
    # Reuse only the fixed ASR resource bytes. Code is rebuilt from this source set.
    asr=Path(plan['asr_stage']);index=json.loads((asr/'RuntimeFileManifest.json').read_text(encoding='utf-8'))
    indexed=index['files']
    if isinstance(indexed,dict):indexed=[{'relative_path':k,**v} for k,v in indexed.items()]
    for item in indexed:
        relative=item['relative_path']
        if relative.startswith(('Runtime/','Models/','Media/','Licenses/')):
            add(asr/relative,'LocalAsr/'+relative,'I23-fixed-resource-bytes-no-inherited-qualification',item['sha256'])
    for item in plan['sources']:
        tail=item['relative_path'].removeprefix('Code/')
        if tail in {'video_creator/__init__.py','video_creator/domain/__init__.py','video_creator/domain/errors.py','video_creator/providers/__init__.py','video_creator/media/__init__.py','video_creator/providers/local_asr.py','video_creator/providers/asr_resources.py','video_creator/media/asr_worker.py'}:
            add(item['path'],'LocalAsr/Code/'+tail,'I26-current-fixed-ASR-code',item['sha256'])
    media=json.loads(Path(plan['media_manifest']['path']).read_text(encoding='utf-8'))
    add(media['font']['path'],'Fonts/NotoSansCJKsc-Regular.otf','verified-OFL-font',media['font']['sha256'])
    add(media['font']['license_path'],'Fonts/OFL.txt','verified-OFL-license',media['font']['license_sha256'])
    modules={}
    for item in plan['sources']:
        relative=item['relative_path']
        if relative.startswith('Code/') and relative.endswith('.py'):
            name=relative[5:-3].replace('/','.')
            if name.endswith('.__init__'):name=name[:-9]
            modules[name]=item
    local_missing=[];dynamic=[];external=set()
    for module,item in modules.items():
        tree=ast.parse(Path(item['path']).read_text(encoding='utf-8-sig'))
        package=module if item['relative_path'].endswith('/__init__.py') else module.rpartition('.')[0]
        for node in ast.walk(tree):
            names=[]
            if isinstance(node,ast.Import):names=[alias.name for alias in node.names]
            elif isinstance(node,ast.ImportFrom):
                prefix='.'.join(package.split('.')[:len(package.split('.'))-node.level+1]) if node.level else ''
                names=['.'.join(p for p in [prefix,node.module or ''] if p)]
            elif isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr in {'import_module','spec_from_file_location','run_module','exec_module'}:
                dynamic.append({'module':module,'line':node.lineno,'call':node.func.attr,'literal_first_argument':node.args[0].value if node.args and isinstance(node.args[0],ast.Constant) else None})
            for name in names:
                if name.startswith('video_creator'):
                    # Namespace packages still require an inventoried subtree, not fabricated init.
                    if name not in modules and not any(key.startswith(name+'.') for key in modules):local_missing.append({'source_module':module,'line':node.lineno,'missing_module':name})
                elif name:external.add(name.split('.')[0])
    native=[{'relative_path':item['relative_path'],'sha256':item['sha256'],**item['native']} for item in records if 'native' in item]
    return {'format':'portable-engine-resource-inventory-v1-candidate','status':'static-payload-candidate-not-runtime-qualification',
            'files':sorted(records,key=lambda x:x['relative_path']),'file_count':len(records),'logical_bytes':sum(item['bytes'] for item in records),
            'packages':packages,'production_lock_packages':len(selected)-1,'excluded':excluded,'errors':errors,
            'source_modules':sorted(modules),'local_import_missing':local_missing,'dynamic_import_sites':dynamic,'external_import_roots':sorted(external),
            'native_static_tables':native,'python_metadata_imports':[{ 'module':name,'origin':str(getattr(module,'__file__',''))} for name,module in sorted(sys.modules.items()) if name.startswith('packaging')],
            'engine_imported':any(name.startswith('video_creator') for name in sys.modules),'namespace_qualified':False,'product_launch':False}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--input-plan',type=Path,required=True);parser.add_argument('--input-plan-sha256',required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if sha(args.input_plan)!=args.input_plan_sha256:raise ValueError('Plan digest mismatch')
    plan=json.loads(args.input_plan.read_text(encoding='utf-8'));result=inventory(plan)
    result['input_plan_sha256']=args.input_plan_sha256;result['input_plan_after_sha256']=sha(args.input_plan)
    if result['engine_imported']:raise ValueError('Unexpected engine import')
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'files':result['file_count'],'bytes':result['logical_bytes'],'packages':len(result['packages']),'errors':len(result['errors']),'local_import_missing':len(result['local_import_missing']),'output_sha256':sha(args.output)}))
    return 1 if result['errors'] else 0

if __name__=='__main__':raise SystemExit(main())
