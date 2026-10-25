"""Test-only barriers after real committed production calls; lazy import after freeze."""
from __future__ import annotations
import functools,json,os,threading,time
from pathlib import Path

def install_after_success_latch(point: str, directory: str, target_run_id: str):
    if point not in {'finish_output','commit_generated_step'}:
        raise ValueError('Only fixed T13 production boundary points are allowed')
    folder=Path(directory)
    if not folder.is_absolute() or 'TestDevelopment' not in folder.parts:
        raise ValueError('Latch requires this testing task absolute process directory')
    if not target_run_id:
        raise ValueError('Explicit self-owned target Run required')
    # This import does not occur merely by reading/compiling this fixture.
    from video_creator.application.worker import WorkerService
    original=getattr(WorkerService,point)
    guard=threading.Lock();used=False
    @functools.wraps(original)
    def wrapper(self,lease,*args,**kwargs):
        nonlocal used
        result=original(self,lease,*args,**kwargs)
        if lease.run_id!=target_run_id:
            return result
        with guard:
            if used:return result
            used=True
        folder.mkdir(parents=True,exist_ok=True)
        facts={'event':'t13_real_call_success_latch','point':point,'run_id':target_run_id,'pid':os.getpid(),'monotonic_ns':time.monotonic_ns(),'underlying_production_call_completed':True,'test_fault_barrier':True,'scope':'Real file/hash or Step/Asset transaction completed before blocking return; no fake checkpoint/fee/asset'}
        partial=folder/'LatchReady.partial';ready=folder/'LatchReady.json'
        with partial.open('wb') as f:
            f.write((json.dumps(facts,indent=2)+'\n').encode('utf8'));f.flush();os.fsync(f.fileno())
        os.replace(partial,ready)
        deadline=time.monotonic()+30
        while not (folder/'ReleaseLatch').exists():
            if time.monotonic()>=deadline:raise TimeoutError('T13 fault barrier expired; not a product success')
            time.sleep(0.02)
        return result
    setattr(WorkerService,point,wrapper)
    return lambda:setattr(WorkerService,point,original)
