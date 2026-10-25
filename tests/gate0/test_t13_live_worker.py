"""Real deterministic local template/worker facts, not autonomous media or Bundle."""
import hashlib,json,os,secrets,socket,sqlite3,time,urllib.request
from pathlib import Path
from video_creator.application.assets import AssetService
from video_creator.application.engine import EngineService
from video_creator.cli.main import configured_media_validator
from video_creator.domain.contracts import AssetCandidate,Automation,CapabilityRoute,CreativeBriefInput,ExecutionPolicy,Money,ProductionInputs,ProductionRequest,SourceBinding
from t13_live_worker_helpers import force_owned,http_json,launch,metadata,read_rows,ready,require_environment,safe_env,save_process,stop_api,tree,wait_for

ROOT,MANIFEST,INPUT,RUNTIME=require_environment('VIDEO_CREATOR_T13_CASES','VIDEO_CREATOR_T13_MANIFEST','VIDEO_CREATOR_T13_AUDIO','VIDEO_CREATOR_T13_RUNTIME');REPO=Path(__file__).resolve().parents[2];PYTHON=REPO/'.venv/Scripts/python.exe'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pin():return {p:sha(Path(p)) for p in json.loads(RUNTIME.read_text('utf8'))['paths']}
def write(p,v):p.write_bytes((json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
def port_closed(port):
 with socket.socket() as s:s.settimeout(2);return s.connect_ex(('127.0.0.1',port))!=0

def test_same_live_nononce_worker_releases_quality_slot_and_second_run_survives_api_close():
 ROOT.mkdir(parents=True,exist_ok=True);data=ROOT/'Instance';assert not data.exists();before=pin();resources=json.loads(MANIFEST.read_text('utf8'));engine=EngineService(data);validator=configured_media_validator(engine,Path(resources['ffmpeg_path']),Path(resources['ffprobe_path']));assets=AssetService(engine)
 staged=assets.stage_bytes('local-user',INPUT.read_bytes(),'audio/wav');asset=assets.import_asset('local-user',AssetCandidate(**staged,source='Public self-created Chinese SAPI stimulus reused as an authorized local experiment input',rights='authorized local experiment; no new autonomous speech claim'),validator)
 engine.register_route(CapabilityRoute(route_id='gate0-local-render-v1',capability='render',source='owned_local',destination='local:gate0-local-render-v1',max_operation_cost=Money(amount='0'),cost_rule_version='local-free-v1',verified=True))
 request=ProductionRequest(goal='Independent T13 finite local-template Worker persistence test',inputs=ProductionInputs(asset_ids=(asset.asset_id,),source_text='Self-created public experiment facts, no Portal or meeting content'),source_bindings=(SourceBinding(system='local',namespace='T13-public-experiment',confirmed_facts=('Local deterministic mechanism only',)),),brief=CreativeBriefInput(target_duration_us=10_000_000,aspect_ratio='9:16'),automation=Automation(mode='interactive',max_revision_cycles=2),policy=ExecutionPolicy(allowed_provider_routes=('gate0-local-render-v1',)),outputs=('video','mixed_audio'))
 first=engine.accept_production('local-user','t13-first',request);token=secrets.token_hex(32);env=safe_env(REPO,token);sibling=launch(REPO,[str(PYTHON),'-B','-X','utf8',str(REPO/'tests/gate0/T13Fixture/OwnedSibling.py')],safe_env(REPO),ROOT/'Sibling');sibling_ready=ready(sibling,'sibling_ready');sibling_before=metadata([sibling['process'].pid]);assert sibling_before
 api=launch(REPO,[str(PYTHON),'-B','-X','utf8','-m','video_creator.cli.main','serve','--data-dir',str(data),'--port','0','--control-stdin','--ffmpeg',resources['ffmpeg_path'],'--ffprobe',resources['ffprobe_path']],env,ROOT/'Api');api_ready=ready(api);base=api_ready['base_url'];api_capture=tree(api['process'].pid);assert http_json(base,'/api/v1/health',token)[1]['worker_connected'] is False
 worker=launch(REPO,[str(PYTHON),'-B','-X','utf8','-m','video_creator.cli.main','worker','--data-dir',str(data),'--workflow','gate0-local-render-v1','--resource-manifest',str(MANIFEST),'--max-seconds','90'],safe_env(REPO),ROOT/'Worker');worker_capture=tree(worker['process'].pid);facts={'first':first.model_dump(mode='json'),'input_asset':asset.model_dump(mode='json'),'runtime_before':before,'worker_cli_once':False};cleanups={}
 try:
  def first_wait():
   run=read_rows(data,'runs','id=?',(first.run_id,))[0];pres=read_rows(data,'worker_presence')
   return {'run':run,'presence':pres[0]} if run['status']=='waiting_user' and run['worker_id'] is None and run['lease_until_us']==0 and pres and pres[0]['state']=='idle' and pres[0]['active_run_id'] is None else None
  waited=wait_for(first_wait,worker,55);presence=waited['presence'];worker_identity=metadata([presence['pid']]);assert worker_identity and presence['pid'] in [r['pid'] for r in tree(worker['process'].pid)];worker_capture=tree(worker['process'].pid);status,health=http_json(base,'/api/v1/health',token);assert status==200 and health['worker_connected'] is True
  first_steps=read_rows(data,'steps','run_id=?',(first.run_id,));first_ops=read_rows(data,'operations','run_id=?',(first.run_id,));assert len(first_steps)==5 and all(r['status']=='succeeded' for r in first_steps);assert len(first_ops)==4 and all(r['status']=='succeeded' and r['settled']==1 and r['actual_units']==0 and r['reserved_units']==0 for r in first_ops)
  status,second=http_json(base,'/api/v1/productions',token,'POST',request.model_dump(mode='json'),'t13-second');assert status==202
  def second_executing():
   run=read_rows(data,'runs','id=?',(second['run_id'],))[0];pres=read_rows(data,'worker_presence')[0]
   return {'run':run,'presence':pres} if run['status']=='running' and run['worker_id']==presence['worker_id'] and pres['active_run_id']==second['run_id'] else None
  executing=wait_for(second_executing,worker,10);api_exit=stop_api(api);assert api_exit==0;assert port_closed(int(base.rsplit(':',1)[1]));api_absent=metadata([r['pid'] for r in api_capture]);assert not api_absent;assert worker['process'].poll() is None;assert metadata([presence['pid']])==worker_identity
  def second_wait():
   run=read_rows(data,'runs','id=?',(second['run_id'],))[0];pres=read_rows(data,'worker_presence')[0]
   return {'run':run,'presence':pres} if run['status']=='waiting_user' and run['worker_id'] is None and run['lease_until_us']==0 and pres['state']=='idle' and pres['active_run_id'] is None else None
  second_done=wait_for(second_wait,worker,45);assert second_done['presence']['worker_id']==presence['worker_id'] and second_done['presence']['pid']==presence['pid'];assert second_done['presence']['heartbeat_us']>presence['heartbeat_us'];assert worker['process'].poll() is None;assert metadata([presence['pid']])==worker_identity
  second_steps=read_rows(data,'steps','run_id=?',(second['run_id'],));second_ops=read_rows(data,'operations','run_id=?',(second['run_id'],));assert len(second_steps)==5 and all(r['status']=='succeeded' for r in second_steps);assert len(second_ops)==4 and all(r['status']=='succeeded' and r['settled']==1 and r['actual_units']==0 for r in second_ops)
  flow_path=data/'WorkflowState/LocalRender.sqlite';assert flow_path.exists()
  with sqlite3.connect(flow_path.as_uri()+'?mode=ro',uri=True) as c:
   c.row_factory=sqlite3.Row;flows=[dict(r) for r in c.execute('SELECT flow_uuid,method_name,state_json FROM flow_states')]
  for run_id in [first.run_id,second['run_id']]:
   matches=[r for r in flows if json.loads(r['state_json']).get('run_id')==run_id];assert len(matches)>=6 and len({r['flow_uuid'] for r in matches})==1
  output_rows=read_rows(data,'assets');assert len(output_rows)==11;decoded=[]
  for row in output_rows:
   p=assets.content_path('local-user',row['id']);assert sha(p)==row['sha256'];probe=validator(p,row['media_type']);assert probe.decoded;decoded.append({'asset_id':row['id'],'sha256':row['sha256'],'media_type':row['media_type'],'probe':probe.model_dump(mode='json')})
  for prod in read_rows(data,'productions'):assert prod['status']=='waiting_user' and prod['spent_units']==prod['reserved_units']==0
  with urllib.request.urlopen('http://127.0.0.1:'+str(sibling_ready['port']),timeout=5) as response:assert response.status==200
  sibling_after=metadata([sibling['process'].pid]);assert sibling_after==sibling_before
  facts.update({'first_quality_wait':waited,'first_steps':first_steps,'first_operations':first_ops,'worker_process_identity':worker_identity,'second_accepted':second,'second_executing_before_api_close':executing,'api_actual_exit':api_exit,'api_pid_absent':api_absent,'second_quality_wait_after_api_close':second_done,'second_steps':second_steps,'second_operations':second_ops,'true_flow_checkpoints':flows,'actual_assets_independently_decoded':decoded,'live_sibling_before':sibling_before,'live_sibling_after':sibling_after,'sibling_health_after':200})
  worker_exit=worker['process'].wait(timeout=100);assert worker_exit==0;closed_presence=read_rows(data,'worker_presence')[0];assert closed_presence['worker_id']==presence['worker_id'] and closed_presence['state']=='stopped' and closed_presence['expires_us']==0
  after=pin();assert after==before;facts.update({'worker_actual_natural_deadline_exit':worker_exit,'worker_presence_after_exit':closed_presence,'runtime_after':after,'worker_remaining':metadata([r['pid'] for r in worker_capture])});assert not facts['worker_remaining']
 finally:
  if api['process'].poll() is None:
   try:cleanups['api']=stop_api(api)
   except Exception:cleanups['api']=force_owned(api,api_capture)
  if worker['process'].poll() is None:
   try:cleanups['worker']=worker['process'].wait(timeout=100)
   except Exception:cleanups['worker']=force_owned(worker,worker_capture)
  sibling['process'].stdin.write(b'shutdown\n');sibling['process'].stdin.flush();cleanups['sibling']=sibling['process'].wait(timeout=8)
  for run in [api,worker,sibling]:save_process(run,token)
  write(ROOT/'Receipt.json',{**facts,'cleanup':cleanups,'scope':'Real API and long-lived nononce Worker CLI independently held by this test parent, real deterministic template/old authorized speech/FFmpeg/SQLite/CrewFlow. No I12 supervisor claim, paid calls, vault, model autonomy, complete Bundle or Production success.'})
