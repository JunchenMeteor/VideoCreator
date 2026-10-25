"""Success-return barrier; actual production import occurs only at runtime install."""
import functools,json,os,threading,time
from pathlib import Path
ALLOWED_POINTS=frozenset({'finish_output','commit_generated_step'})

def wrap_after_success(original,point,directory,target_run_id,target_step='local-shot-1',evidence_kind='actual_product_call'):
 if point not in ALLOWED_POINTS:raise ValueError('Unapproved fault boundary')
 folder=Path(directory)
 if not folder.is_absolute() or 'TestDevelopment' not in folder.parts:raise ValueError('Own absolute latch directory required')
 if not target_run_id or not target_step:raise ValueError('Exact target Run/Step required')
 if evidence_kind not in {'actual_product_call','fixture_sanity'}:raise ValueError('Evidence kind required')
 used=False;lock=threading.Lock()
 @functools.wraps(original)
 def wrapper(self,lease,*args,**kwargs):
  nonlocal used
  result=original(self,lease,*args,**kwargs)
  reservation=args[0] if args else kwargs.get('reservation');step=(getattr(reservation,'step_key',None) if point=='finish_output' else reservation)
  if lease.run_id!=target_run_id or step!=target_step:return result
  with lock:
   if used:return result
   used=True
  folder.mkdir(parents=True,exist_ok=True);ready=folder/'LatchReady.json';partial=folder/'LatchReady.partial';facts={'event':'t14_success_return_latch','point':point,'run_id':target_run_id,'step_key':target_step,'pid':os.getpid(),'wall_us':time.time_ns()//1000,'monotonic_ns':time.monotonic_ns(),'underlying_call_returned':True,'evidence_kind':evidence_kind,'scope':'Barrier after returned original method; not fake media, fee, checkpoint, lease or business transaction'}
  with partial.open('xb') as output:output.write((json.dumps(facts,indent=2)+'\n').encode('utf8'));output.flush();os.fsync(output.fileno())
  os.replace(partial,ready);deadline=time.monotonic()+30
  while not (folder/'ReleaseLatch').exists():
   if time.monotonic()>=deadline:raise TimeoutError('Test barrier expired; not product success')
   time.sleep(.02)
  return result
 return wrapper

def install_after_success_latch(point,directory,target_run_id,target_step='local-shot-1'):
 from video_creator.application.worker import WorkerService
 original=getattr(WorkerService,point);wrapper=wrap_after_success(original,point,directory,target_run_id,target_step);setattr(WorkerService,point,wrapper)
 return lambda:setattr(WorkerService,point,original)
