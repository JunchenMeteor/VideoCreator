import json,os,sys,threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
class H(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_GET(self):
  raw=b'T13 self-owned live sibling';self.send_response(200);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
server=ThreadingHTTPServer(('127.0.0.1',0),H);server.daemon_threads=True
print(json.dumps({'event':'sibling_ready','port':server.server_address[1],'actual_pid':os.getpid()}),flush=True)
def stop():
 for line in sys.stdin.buffer:
  if line==b'shutdown\n':server.shutdown();return
threading.Thread(target=stop,daemon=True).start()
try:server.serve_forever(poll_interval=.1)
finally:server.server_close()
