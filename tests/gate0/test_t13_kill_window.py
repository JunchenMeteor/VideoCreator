"""Real killed file-success gap and real wall-clock expiry, not a mocked Flow."""
import hashlib,json,os,sqlite3,time,urllib.request
from datetime import UTC,datetime
from pathlib import Path
from video_creator.application.assets import AssetService
from video_creator.application.engine import EngineService
from video_creator.cli.main import configured_media_validator
from video_creator.domain.contracts import AssetCandidate,Automation,CapabilityRoute,CreativeBriefInput,ExecutionPolicy,Money,ProductionInputs,ProductionRequest,SourceBinding
from t13_live_worker_helpers import force_owned,launch,metadata,ready,require_environment,safe_env,save_process,tree
ROOT,MANIFEST,INPUT,RUNTIME=require_environment('VIDEO_CREATOR_T13_CASES','VIDEO_CREATOR_T13_MANIFEST','VIDEO_CREATOR_T13_AUDIO','VIDEO_CREATOR_T13_RUNTIME');REPO=Path(__file__).resolve().parents[2];PYTHON=REPO/'.venv/Scripts/python.exe'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_bytes((json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
def rows(data,table):
 assert table in {'runs','steps','operations','worker_presence','generated_attempts','staging','assets','productions','events','execution_bindings'}
 with sqlite3.connect((data/'Metadata.sqlite').as_uri()+'?mode=ro',uri=True) as c:
  c.row_factory=sqlite3.Row;return [dict(r) for r in c.execute('SELECT * FROM '+table)]
def snapshot(data):return {t:rows(data,t) for t in ['runs','steps','operations','worker_presence','generated_attempts','staging','assets','productions','execution_bindings']}
def pin():return {p:sha(Path(p)) for p in json.loads(RUNTIME.read_text('utf8'))['paths']}
def test_completed_file_before_observation_kill_reconciles_without_rerender():
 ROOT.mkdir(parents=True,exist_ok=False);data=ROOT/'Instance';runtime_before=pin();resources=json.loads(MANIFEST.read_text('utf8'));engine=EngineService(data);validator=configured_media_validator(engine,Path(resources['ffmpeg_path']),Path(resources['ffprobe_path']));assets=AssetService(engine)
 staged=assets.stage_bytes('local-user',INPUT.read_bytes(),'audio/wav');asset=assets.import_asset('local-user',AssetCandidate(**staged,source='T13 public self-created authorized local stimulus',rights='authorized local experimental use'),validator)
 engine.register_route(CapabilityRoute(route_id='gate0-local-render-v1',capability='render',source='owned_local',destination='local:gate0-local-render-v1',max_operation_cost=Money(amount='0'),cost_rule_version='local-free-v1',verified=True))
 request=ProductionRequest(goal='T13 exact killed file-success gap',inputs=ProductionInputs(asset_ids=(asset.asset_id,),source_text='Deterministic local mechanism only'),source_bindings=(SourceBinding(system='local',namespace='T13-public-experiment',confirmed_facts=('Zero-cost controlled template',)),),brief=CreativeBriefInput(target_duration_us=10_000_000,aspect_ratio='9:16'),automation=Automation(mode='interactive',max_revision_cycles=2),policy=ExecutionPolicy(allowed_provider_routes=('gate0-local-render-v1',)),outputs=('video','mixed_audio'))
 accepted=engine.accept_production('local-user','t13-kill-window',request);latch=ROOT/'SuccessLatch';sibling=launch(REPO,[str(PYTHON),'-B','-X','utf8',str(REPO/'tests/gate0/T13Fixture/OwnedSibling.py')],safe_env(REPO),ROOT/'Sibling');sibling_ready=ready(sibling,'sibling_ready');sibling_identity=metadata([sibling['process'].pid]);assert sibling_identity
 old=launch(REPO,[str(PYTHON),'-B','-X','utf8',str(REPO/'tests/gate0/T13Fixture/LatchWorker.py'),'--data-dir',str(data),'--resource-manifest',str(MANIFEST),'--target-run',accepted.run_id,'--latch-dir',str(latch)],safe_env(REPO),ROOT/'KilledWorker');old_tree=tree(old['process'].pid);new=None;new_tree=[];facts={'observed_start':datetime.now(UTC).isoformat(),'accepted':accepted.model_dump(mode='json'),'runtime_before':runtime_before,'fault_scope':'Controlled test-only post-success return latch; actual file, DB, FFmpeg and Worker OS kill. No altered engine clock, SQL business writes, paid API or fake asset.'};cleanups={}
 try:
  end=time.monotonic()+45
  while not (latch/'LatchReady.json').exists():
   assert old['process'].poll() is None,'Real Worker exited before exact fault point';assert time.monotonic()<end,'Exact success latch did not arrive';time.sleep(.05)
  latch_fact=json.loads((latch/'LatchReady.json').read_text('utf8'));before=snapshot(data);old_tree=tree(old['process'].pid);target=metadata([latch_fact['pid']]);assert target and any(r['pid']==latch_fact['pid'] and r['created_utc']==target[0]['created_utc'] for r in old_tree)
  operation=before['operations'][0];assert len(before['operations'])==1 and operation['status']=='submitting' and operation['observation_json'] is None and operation['settled']==0;assert len(before['generated_attempts'])==1;attempt=before['generated_attempts'][0];stage=next(r for r in before['staging'] if r['id']==attempt['staging_id']);assert stage['status']=='ready';file=data/'Staging'/stage['id'];file_before={'path':str(file),'sha256':sha(file),'size':file.stat().st_size,'mtime_ns':file.stat().st_mtime_ns};assert file_before['sha256']==stage['sha256'];assert not file.with_name(file.name+'.partial').exists();assert len(before['assets'])==1
  facts.update({'success_latch':latch_fact,'before_kill':before,'captured_old_tree':old_tree,'exact_target_identity_before_kill':target,'completed_file_before_kill':file_before});write(ROOT/'Receipt.json',facts)
  kill=force_owned(old,old_tree);assert kill['mode']=='creation_verified_test_teardown_force' and kill['tool_exit']==0;old_after=metadata([r['pid'] for r in old_tree]);assert old_after==[];assert metadata([sibling['process'].pid])==sibling_identity
  expiry=before['runs'][0]['lease_until_us'];wall_start=time.time_ns()//1000;mono_start=time.monotonic();assert expiry>wall_start
  while time.time_ns()//1000<=expiry+150000:
   assert time.monotonic()-mono_start<40,'Real lease wall-clock expiry exceeded finite observation';time.sleep(.1)
  wall_end=time.time_ns()//1000;assert wall_end>expiry;facts.update({'actual_identity_checked_kill':kill,'old_tree_after_actual_kill':old_after,'lease_expiry_us':expiry,'wall_before_wait_us':wall_start,'wall_after_wait_us':wall_end,'actual_wait_seconds':time.monotonic()-mono_start});write(ROOT/'Receipt.json',facts)
  new=launch(REPO,[str(PYTHON),'-B','-X','utf8','-m','video_creator.cli.main','worker','--data-dir',str(data),'--workflow','gate0-local-render-v1','--resource-manifest',str(MANIFEST),'--max-seconds','12'],safe_env(REPO),ROOT/'RecoveryWorker');new_tree=tree(new['process'].pid);finish=time.monotonic()+8;active=None
  while time.monotonic()<finish:
   presence=rows(data,'worker_presence')[0]
   if presence['worker_id']!=before['worker_presence'][0]['worker_id'] and presence['pid'] in [r['pid'] for r in tree(new['process'].pid)]:active=presence;break
   assert new['process'].poll() is None;time.sleep(.1)
  assert active,'Actual new nononce Worker presence missing';new_tree=tree(new['process'].pid);new_exit=new['process'].wait(timeout=25);assert new_exit==0;after=snapshot(data);file_after={'path':str(file),'sha256':sha(file),'size':file.stat().st_size,'mtime_ns':file.stat().st_mtime_ns};runtime_after=pin();assert runtime_after==runtime_before;assert metadata([r['pid'] for r in new_tree])==[]
  with urllib.request.urlopen('http://127.0.0.1:'+str(sibling_ready['port']),timeout=4) as response:assert response.status==200
  assert metadata([sibling['process'].pid])==sibling_identity
  facts.update({'new_actual_presence':active,'new_captured_tree':new_tree,'new_natural_deadline_exit':new_exit,'after_new_worker':after,'completed_file_after_new_worker':file_after,'runtime_after':runtime_after,'live_sibling_identity_before':sibling_identity,'live_sibling_identity_after':metadata([sibling['process'].pid]),'live_sibling_http_after':200,'provider_calls':0,'real_key_reads':0});write(ROOT/'Receipt.json',facts)
  assert len(after['operations'])==1 and after['operations'][0]['id']==operation['id'];assert len(after['generated_attempts'])==1 and after['generated_attempts'][0]['id']==attempt['id'];assert file_after==file_before,'Completed file was rewritten instead of reconciling exact output'
  assert after['runs'][0]['status']=='waiting_user','Completed durable file was not reconciled and continued to quality wait by the actual replacement Worker'
 finally:
  if old['process'].poll() is None:cleanups['old']=force_owned(old,old_tree)
  if new and new['process'].poll() is None:
   try:cleanups['new']=new['process'].wait(timeout=30)
   except Exception:cleanups['new']=force_owned(new,new_tree)
  sibling['process'].stdin.write(b'shutdown\n');sibling['process'].stdin.flush();cleanups['sibling_exit']=sibling['process'].wait(timeout=8);cleanups['sibling_remaining']=metadata([sibling['process'].pid]);assert not cleanups['sibling_remaining']
  for child in [old,new,sibling]:
   if child:save_process(child)
  facts.update({'ended_at':datetime.now(UTC).isoformat(),'cleanup':cleanups,'runtime_final':pin()});write(ROOT/'Receipt.json',facts)
