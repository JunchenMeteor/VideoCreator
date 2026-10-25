"""Post-run independent decode supplement; original live batch remains red."""
import hashlib,json,os,socket,sqlite3
from datetime import UTC,datetime
from pathlib import Path
from video_creator.media.ffmpeg import FFmpegRuntime
from t13_live_worker_helpers import metadata,require_environment
ROOT,OLD,INPUTS,MANIFEST=require_environment('VIDEO_CREATOR_T13_OBSERVATION','VIDEO_CREATOR_T13_OLD_CASE','VIDEO_CREATOR_T13_RUNTIME','VIDEO_CREATOR_T13_MANIFEST')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,value):p.write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
def test_postrun_objects_decode_and_actual_children_terminal():
 ROOT.mkdir(parents=True,exist_ok=False);staging=ROOT/'Staging';staging.mkdir();db=OLD/'Instance/Metadata.sqlite';original=json.loads((OLD/'Receipt.json').read_text('utf8'));children=[json.loads((OLD/name/'ChildReceipt.json').read_text('utf8')) for name in ['Api','Worker','Sibling']];assert all(c['actual_exit']==0 for c in children)
 paths=[Path(p) for p in json.loads(INPUTS.read_text('utf8'))['paths']];before={str(p):sha(p) for p in paths};original_db_sha=sha(db)
 with sqlite3.connect(db.as_uri()+'?mode=ro',uri=True) as connection:
  connection.row_factory=sqlite3.Row;rows={table:[dict(r) for r in connection.execute('SELECT * FROM '+table)] for table in ['assets','runs','operations','steps','worker_presence','productions']}
 assert len(rows['runs'])==2 and all(r['status']=='waiting_user' and r['worker_id'] is None and r['lease_until_us']==0 for r in rows['runs']);assert len(rows['steps'])==10 and all(r['status']=='succeeded' for r in rows['steps']);assert len(rows['operations'])==8 and all(r['status']=='succeeded' and r['settled']==1 and r['actual_units']==r['reserved_units']==0 for r in rows['operations']);assert rows['worker_presence'][0]['state']=='stopped' and rows['worker_presence'][0]['expires_us']==0
 pids=list({*[c['root_pid'] for c in children],rows['worker_presence'][0]['pid']});current=metadata(pids);assert current==[]
 base=json.loads((OLD/'Api/Stdout.txt').read_text('utf8').splitlines()[0])['base_url'];port=int(base.rsplit(':',1)[1])
 with socket.socket() as socket_probe:socket_probe.settimeout(2);port_closed=socket_probe.connect_ex(('127.0.0.1',port))!=0
 assert port_closed
 resources=json.loads(MANIFEST.read_text('utf8'));runtime=FFmpegRuntime(Path(resources['ffmpeg_path']),Path(resources['ffprobe_path']),staging);decoded=[];old_objects={};assert len(rows['assets'])==11
 for row in rows['assets']:
  assert len(row['sha256'])==64 and all(c in '0123456789abcdef' for c in row['sha256']);source=(OLD/'Instance/Objects'/row['sha256']).resolve(strict=True);assert source.is_relative_to((OLD/'Instance/Objects').resolve());original_sha=sha(source);assert original_sha==row['sha256'];old_objects[str(source)]=original_sha;copy=staging/row['id'];copy.write_bytes(source.read_bytes());copy_sha=sha(copy);assert copy_sha==original_sha;probe=runtime.probe(copy,decode=True);assert probe.decoded and probe.media_type==row['media_type'];decoded.append({'asset_id':row['id'],'original':str(source),'original_sha256':original_sha,'copy':str(copy),'copy_sha256':copy_sha,'probe':probe.model_dump(mode='json')})
 after={str(p):sha(p) for p in paths};assert before==after;assert sha(db)==original_db_sha;assert all(sha(Path(p))==h for p,h in old_objects.items())
 write(ROOT/'Receipt.json',{'observed_at':datetime.now(UTC).isoformat(),'scope':'Post-run read-only DB/object observer supplement; original T13LiveRoundThree remains failed. Actual fixed decoder of exact byte copies within this observer controlled Staging. This does not recreate earlier snapshots, original holder creation receipts, or audiovisual quality approval.','original_case_receipt_sha256':sha(OLD/'Receipt.json'),'old_db_sha256_before':original_db_sha,'old_db_sha256_after':sha(db),'actual_child_receipts':children,'actual_root_pids_plus_presence_pid_now_absent':pids,'pid_observation':current,'api_port':port,'api_port_now_closed':port_closed,'durable_postrun_rows':rows,'decoded_assets':decoded,'runtime_before':before,'runtime_after':after,'provider_calls':0,'real_key_reads':0,'original_pipeline_test_pass':False})
