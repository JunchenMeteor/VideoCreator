"""Test-only immediate immutable observations; no product imports or credentials."""
import hashlib,json,os,threading,time
from datetime import UTC,datetime
from pathlib import Path

def sha_bytes(data):return hashlib.sha256(data).hexdigest()
def atomic_json(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);raw=(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf8');partial=path.with_name(path.name+'.partial')
 with partial.open('xb') as output:output.write(raw);output.flush();os.fsync(output.fileno())
 os.replace(partial,path);return sha_bytes(raw)

class Journal:
 def __init__(self,directory,evidence_kind):
  self.root=Path(directory)
  if not self.root.is_absolute() or 'TestDevelopment' not in self.root.parts:raise ValueError('Own absolute process directory required')
  if evidence_kind not in {'actual_os_observation','fixture_sanity','synthetic_mechanism'}:raise ValueError('Explicit evidence kind required')
  self.root.mkdir(parents=True,exist_ok=False);self.kind=evidence_kind;self.sequence=0;self.previous=None;self.lock=threading.Lock()
 def record(self,event,facts):
  if not isinstance(event,str) or not event:raise ValueError('Named observation required')
  text=json.dumps(facts,ensure_ascii=False)
  if any(name in text for name in ['VIDEO_CREATOR_API_TOKEN','Authorization','Bearer ','PRIVATE KEY']):raise ValueError('Credential-bearing observation prohibited')
  with self.lock:
   self.sequence+=1;record={'event':event,'sequence':self.sequence,'evidence_kind':self.kind,'observed_utc':datetime.now(UTC).isoformat(),'wall_us':time.time_ns()//1000,'monotonic_ns':time.monotonic_ns(),'previous_event_sha256':self.previous,'facts':facts};path=self.root/('Event'+str(self.sequence).zfill(4)+'.json');digest=atomic_json(path,record);self.previous=digest;return path,digest
