"""Own fixture: write a real pipe before spawning Node, no product logic."""
from __future__ import annotations
import argparse,json,os,subprocess,sys,threading,time
from pathlib import Path

def emit(event,**facts):
    print(json.dumps({'event':event,**facts},ensure_ascii=False),flush=True)

p=argparse.ArgumentParser()
p.add_argument('--node',required=True)
p.add_argument('--entry',required=True)
p.add_argument('--python',required=True)
p.add_argument('--data-dir',required=True)
p.add_argument('--manifest',required=True)
p.add_argument('--port',required=True,type=int)
p.add_argument('--receipt-dir',required=True)
a=p.parse_args()
for value in [a.node,a.entry,a.python,a.data_dir,a.manifest,a.receipt_dir]:
    if not Path(value).is_absolute():raise ValueError('Fixture path must be absolute')
if not 1024<=a.port<=65535:raise ValueError('Fixture port invalid')
env={name:os.environ[name] for name in ['SystemRoot','WINDIR','ComSpec','PATH','PATHEXT','TEMP','TMP','PSModulePath','LOCALAPPDATA','APPDATA'] if name in os.environ}
env.update(VIDEO_CREATOR_PYTHON=a.python,VIDEO_CREATOR_RESOURCE_MANIFEST=a.manifest,PYTHONUTF8='1',PYTHONIOENCODING='utf-8',OTEL_SDK_DISABLED='true',CREWAI_TRACING_ENABLED='false')
read_fd,write_fd=os.pipe()
frame=b'shutdown\n'
written=os.write(write_fd,frame)
write_before_spawn_ns=time.monotonic_ns()
emit('t11_prebuffer_written',bytes_written=written,hex=frame.hex(),write_before_spawn_ns=write_before_spawn_ns,actual_pipe=True)
argv=[a.node,a.entry,'--data-dir',a.data_dir,'--workbench-port',str(a.port),'--control-stdin']
folder=Path(a.receipt_dir);folder.mkdir(parents=True,exist_ok=True)
output={'stdout':bytearray(),'stderr':bytearray()}
child=None
try:
    child=subprocess.Popen(argv,stdin=read_fd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,cwd=Path(a.entry).parent.parent.parent,shell=False,close_fds=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    spawned_ns=time.monotonic_ns()
    emit('t11_fixture_spawned',pid=child.pid,argv=argv,spawned_ns=spawned_ns)
    os.close(read_fd);read_fd=-1
    def consume(name,stream):
        while chunk:=stream.read(4096):output[name].extend(chunk)
    threads=[threading.Thread(target=consume,args=(name,getattr(child,name)),daemon=True) for name in output]
    for t in threads:t.start()
    try:
        code=child.wait(timeout=40)
        for t in threads:t.join(timeout=2)
        emit('t11_fixture_child_closed',pid=child.pid,actual_exit_code=code)
    except subprocess.TimeoutExpired:
        code=None
        emit('t11_fixture_timeout',pid=child.pid,meaning='Unknown product termination; fixture does not kill by name or arbitrary PID')
    facts={'pipe_frame_hex':frame.hex(),'bytes_written_before_spawn':written,'write_before_spawn_ns':write_before_spawn_ns,'spawned_ns':spawned_ns,'actual_node_pid':child.pid,'actual_node_argv':argv,'actual_node_exit_code':code,'supplier_key_reads':0,'provider_calls':0,'scope':'Actual OS pipe written before Popen; no event emit or control parser substitution. Fixture result is not product success.'}
    for name,data in output.items():(folder/(name.title()+'.txt')).write_bytes(data)
    (folder/'Receipt.json').write_bytes((json.dumps(facts,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
    sys.exit(0 if code is not None else 3)
finally:
    if read_fd>=0:os.close(read_fd)
    os.close(write_fd)
