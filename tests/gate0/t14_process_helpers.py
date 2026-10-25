"""Independent exact-PID and owned CLI observations; no production patches."""
import json,os,queue,sqlite3,subprocess,threading,time,urllib.request,urllib.error
from pathlib import Path

def safe_env(repo,token=None):
 env={name:os.environ[name] for name in ['SystemRoot','WINDIR','ComSpec','PATH','PATHEXT','TEMP','TMP','PSModulePath','LOCALAPPDATA','APPDATA'] if name in os.environ}
 home=Path(os.environ['VIDEO_CREATOR_T14_CASES'])/'ChildHome';home.mkdir(parents=True,exist_ok=True)
 for child in ['AppData/Local','AppData/Roaming','CrewAiStorage']:(home/child).mkdir(parents=True,exist_ok=True)
 env.update(USERPROFILE=str(home),CREWAI_STORAGE_DIR=str(home/'CrewAiStorage'),LOCALAPPDATA=str(home/'AppData/Local'),APPDATA=str(home/'AppData/Roaming'))
 env.update(PYTHONPATH=str(repo/'services/engine/src'),PYTHONUTF8='1',PYTHONIOENCODING='utf-8',OTEL_SDK_DISABLED='true',CREWAI_TRACING_ENABLED='false')
 if token:env['VIDEO_CREATOR_API_TOKEN']=token
 return env

def metadata(pids,children=False):
 ids=list(dict.fromkeys(pids));assert ids and len(ids)<=128 and all(isinstance(n,int) and n>0 for n in ids)
 flt=' OR '.join('ProcessId='+str(n)+(' OR ParentProcessId='+str(n) if children else '') for n in ids)
 script='$ErrorActionPreference="Stop"; $rows=@(Get-CimInstance Win32_Process -Filter "'+flt+'" -Property ProcessId,ParentProcessId,CreationDate | ForEach-Object { [pscustomobject]@{pid=[int]$_.ProcessId;parent_pid=[int]$_.ParentProcessId;created_utc=$_.CreationDate.ToUniversalTime().ToString("o")} }); ConvertTo-Json -InputObject $rows -Compress'
 p=subprocess.run([str(Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'),'-NoProfile','-NonInteractive','-Command',script],capture_output=True,text=True,encoding='utf8',timeout=12,creationflags=subprocess.CREATE_NO_WINDOW)
 assert p.returncode==0,p.stderr
 value=json.loads(p.stdout.lstrip('\ufeff').strip() or '[]');return value if isinstance(value,list) else [value]

def tree(pid):
 result={};seeds=[pid]
 for _ in range(10):
  if not seeds:break
  batch=metadata(seeds,True);seeds=[]
  for row in batch:
   if row['pid'] not in result:result[row['pid']]=row;seeds.append(row['pid'])
  assert len(result)<=128
 return list(result.values())

def launch(repo,argv,env,folder):
 folder.mkdir(parents=True,exist_ok=True);p=subprocess.Popen(argv,cwd=repo,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
 raw={'stdout':bytearray(),'stderr':bytearray()};lines=queue.Queue()
 def read(name):
  while line:=getattr(p,name).readline():
   raw[name].extend(line)
   if name=='stdout':lines.put(line)
 threads=[threading.Thread(target=read,args=(n,),daemon=True) for n in raw]
 for t in threads:t.start()
 return {'process':p,'argv':argv,'folder':folder,'raw':raw,'lines':lines,'threads':threads}

def ready(run,kind='ready',timeout=25):
 deadline=time.monotonic()+timeout
 while time.monotonic()<deadline:
  try:line=run['lines'].get(timeout=.15)
  except queue.Empty:
   if run['process'].poll() is not None:raise AssertionError('Owned child exited before ready')
   continue
  try:obj=json.loads(line)
  except Exception:continue
  if obj.get('event')==kind:return obj
 raise AssertionError('Owned child ready timed out')

def http_json(base,route,token,method='GET',body=None,key=None):
 headers={'Authorization':'Bearer '+token}
 if body is not None:headers['Content-Type']='application/json'
 if key:headers['Idempotency-Key']=key
 req=urllib.request.Request(base+route,data=None if body is None else json.dumps(body,ensure_ascii=False).encode('utf8'),headers=headers,method=method)
 with urllib.request.urlopen(req,timeout=8) as response:return response.status,json.load(response)

def read_rows(data,table,where='',args=()):
 assert table in {'runs','worker_presence','steps','operations','assets','productions','execution_bindings','creative_revisions','generated_attempts','staging','events'}
 with sqlite3.connect((data/'Metadata.sqlite').as_uri()+'?mode=ro',uri=True) as c:
  c.row_factory=sqlite3.Row;return [dict(r) for r in c.execute('SELECT * FROM '+table+(' WHERE '+where if where else ''),args)]

def wait_for(callback,worker,timeout=50):
 deadline=time.monotonic()+timeout
 while time.monotonic()<deadline:
  value=callback()
  if value:return value
  if worker['process'].poll() is not None:raise AssertionError('Actual Worker exited before required state')
  time.sleep(.1)
 raise AssertionError('Actual durable state wait timed out')

def stop_api(run):
 if run['process'].poll() is None:run['process'].stdin.write(b'shutdown\n');run['process'].stdin.flush()
 return run['process'].wait(timeout=25)

def save_process(run,token=''):
 for t in run['threads']:t.join(timeout=2)
 for name,raw in run['raw'].items():(run['folder']/(name.title()+'.txt')).write_bytes(bytes(raw).replace(token.encode('utf8'),b'[test-session-redacted]') if token else bytes(raw))
 (run['folder']/'ChildReceipt.json').write_bytes((json.dumps({'argv':run['argv'],'root_pid':run['process'].pid,'actual_exit':run['process'].poll(),'provider_calls':0,'real_key_reads':0},ensure_ascii=False,indent=2)+'\n').encode('utf8'))

def force_owned(run,captured):
 p=run['process'];old=next((r for r in captured if r['pid']==p.pid),None)
 if p.poll() is not None:return {'mode':'already_closed','actual_exit':p.returncode}
 current=metadata([p.pid]);assert old and any(r['pid']==old['pid'] and r['created_utc']==old['created_utc'] for r in current),'Unknown identity must not be forced'
 result=subprocess.run([str(Path(os.environ['SystemRoot'])/'System32/taskkill.exe'),'/PID',str(p.pid),'/T','/F'],capture_output=True,timeout=8,creationflags=subprocess.CREATE_NO_WINDOW)
 return {'mode':'creation_verified_test_teardown_force','tool_exit':result.returncode,'actual_exit':p.wait(timeout=10)}
