"""Copy an inventoried payload to a fresh private stage; no package/engine execution."""
from __future__ import annotations
import argparse,hashlib,json,shutil,time
from pathlib import Path

def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--inventory',type=Path,required=True);parser.add_argument('--inventory-sha256',required=True);parser.add_argument('--input-plan',type=Path,required=True);parser.add_argument('--receipt',type=Path,required=True);args=parser.parse_args()
    if sha(args.inventory)!=args.inventory_sha256:raise ValueError('Inventory changed')
    inventory=json.loads(args.inventory.read_text(encoding='utf-8'));plan=json.loads(args.input_plan.read_text(encoding='utf-8'))
    if sha(args.input_plan)!=inventory['input_plan_sha256'] or inventory['errors']:raise ValueError('Invalid input scope')
    root=Path(plan['stage_initial']);owner=args.input_plan.resolve().parent
    if not root.is_absolute() or root.parent.resolve()!=owner or root.exists():raise ValueError('Fresh owned stage required')
    if owner.is_symlink() or getattr(owner.lstat(),'st_file_attributes',0)&1024:raise ValueError('Linked owner directory')
    usage=shutil.disk_usage(owner)
    if usage.free<inventory['logical_bytes']*2+512*1024*1024:raise ValueError('Insufficient stage/move budget')
    report={'started_at_ns':time.time_ns(),'ended_at_ns':None,'actual_exit':None,'stage':str(root),'inventory_sha256':args.inventory_sha256,
            'input_plan_sha256':sha(args.input_plan),'source_changes':[],'copied_files':0,'copied_bytes':0,'space_before':{'free':usage.free,'total':usage.total},
            'product_import_or_launch':False,'model_or_asr':False,'namespace_qualified':False,'runtime_ready':False}
    args.receipt.parent.mkdir(parents=True,exist_ok=True);save(args.receipt,report);root.mkdir()
    pins=[]
    try:
        for item in inventory['files']:
            source=Path(item['source']);destination=root/item['relative_path']
            if source.is_symlink() or getattr(source.lstat(),'st_file_attributes',0)&1024:raise ValueError('Input became linked')
            if sha(source)!=item['sha256'] or source.stat().st_size!=item['bytes']:raise ValueError('Input changed before copy')
            destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,destination)
            if sha(destination)!=item['sha256'] or destination.stat().st_size!=item['bytes']:raise ValueError('Copy mismatch')
            if sha(source)!=item['sha256']:report['source_changes'].append(item['source']);raise ValueError('Input changed during copy')
            pins.append({'relative_path':item['relative_path'],'bytes':item['bytes'],'sha256':item['sha256']})
            report['copied_files']+=1;report['copied_bytes']+=item['bytes']
            if report['copied_files']%500==0:save(args.receipt,report)
        def generated(relative,body):
            destination=root/relative;destination.parent.mkdir(parents=True,exist_ok=True);destination.write_text(body,encoding='utf-8',newline='\n')
            pins.append({'relative_path':relative,'bytes':destination.stat().st_size,'sha256':sha(destination),'generated':True})
        paths=['Lib','DLLs','Lib/site-packages','../../Code','Lib/site-packages/win32','Lib/site-packages/win32/lib','Lib/site-packages/pythonwin','Lib/site-packages/pywin32_system32']
        generated('Runtime/Python/python313._pth','\n'.join(paths)+'\n')
        # The service package replaces the editable entry, not the original .venv prefix.
        generated('Runtime/Python/Lib/site-packages/video_creator_engine-0.1.0.dist-info/METADATA','Metadata-Version: 2.4\nName: video-creator-engine\nVersion: 0.1.0\nSummary: Fixed ordinary-source internal engine candidate\n\n')
        generated('Runtime/Python/Lib/site-packages/video_creator_engine-0.1.0.dist-info/WHEEL','Wheel-Version: 1.0\nGenerator: VideoCreator-Integration-I26-internal\nRoot-Is-Purelib: true\nTag: py3-none-any\n')
        # Preserve the four trusted model digests and code identities; no qualification inheritance.
        old=json.loads((Path(plan['asr_stage'])/'ResourceManifest.json').read_text(encoding='utf-8'))
        asr_pins=[{**pin,'relative_path':pin['relative_path'].removeprefix('LocalAsr/')} for pin in pins if pin['relative_path'].startswith('LocalAsr/')]
        asr_index=root/'LocalAsr/RuntimeFileManifest.json'
        save(asr_index,{'schema':'I26-internal-asr-resource-index-candidate','files':asr_pins,'stage_root_relative_paths':True})
        old.update(schema='I26-internal-ASR-resource-candidate',runtime_manifest='RuntimeFileManifest.json',execution_qualification='not_admitted',actual_execution_configuration_sha256=None,
                   factory_registration='pending-real-backend-registration',whole_engine_sidecar=False)
        # Provenance-only old paths are not consumer paths; retain them in process evidence instead.
        for name in ['old_I16_provenance','trusted_model_hash_source','support_snapshot_sha256']:old.pop(name,None)
        old['admitted_code']=[pin for pin in asr_pins if pin['relative_path'].startswith('Code/')]
        for name in ['admitted_loader_support','external_os_condition','license_distribution_clearance']:old.pop(name,None)
        old['resource_distribution_state']='pending-original-CRT-PyAV-FFmpeg-package-license-obligations'
        asr_manifest=root/'LocalAsr/ResourceManifest.json';save(asr_manifest,old)
        for name in ['LocalAsr/RuntimeFileManifest.json','LocalAsr/ResourceManifest.json']:
            destination=root/name;pins.append({'relative_path':name,'bytes':destination.stat().st_size,'sha256':sha(destination),'generated':True})
        save(root/'EngineFileManifest.json',{'format':'portable-engine-file-index-v1-candidate','files':pins,'namespace_qualified':False,'scope':'static existing payload; no independent runtime qualification'})
        full_index=root/'EngineFileManifest.json';pins.append({'relative_path':'EngineFileManifest.json','bytes':full_index.stat().st_size,'sha256':sha(full_index),'generated':True})
        installation={'format':'native-engine-installation-v1-candidate','launcher_mode':'python_source','executable':'Runtime/Python/python.exe','source_root':'Code','files':pins,
                      'ffmpeg':'LocalAsr/Media/FFmpeg/bin/ffmpeg.exe','ffprobe':'LocalAsr/Media/FFmpeg/bin/ffprobe.exe'}
        save(root/'CandidateInstallationManifest.json',installation)
        report.update(actual_exit=0,ended_at_ns=time.time_ns(),generated_files=len(pins)-report['copied_files'],
                      installation_manifest={'relative_path':'CandidateInstallationManifest.json','bytes':(root/'CandidateInstallationManifest.json').stat().st_size,'sha256':sha(root/'CandidateInstallationManifest.json')},
                      engine_file_manifest={'relative_path':'EngineFileManifest.json','sha256':sha(full_index)},
                      asr_manifest_sha256=sha(asr_manifest),asr_index_sha256=sha(asr_index),local_static_import_missing=inventory['local_import_missing'],
                      pth_policy='fixed-relative-paths-no-import-site; not namespace or DLL qualification',
                      migration_environment_required='VIDEO_CREATOR_MIGRATIONS_DIR=$INSTALL_ROOT/Migrations',
                      current_backend_version='B12 ordinary final; B16 Stage/live not selected; Media W14 source-only composition')
    except Exception as error:
        report.update(actual_exit=1,ended_at_ns=time.time_ns(),failure_type=type(error).__name__,failure=str(error));save(args.receipt,report);raise
    save(args.receipt,report)
    print(json.dumps({'actual_exit':report['actual_exit'],'files':len(pins),'copied_bytes':report['copied_bytes'],'installation_manifest':report['installation_manifest'],'source_changes':len(report['source_changes'])}))
if __name__=='__main__':main()
