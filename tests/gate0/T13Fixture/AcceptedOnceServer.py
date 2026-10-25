"""Owned free loopback accept-then-disconnect server; no vendor or key access."""
from __future__ import annotations
import argparse,hashlib,json,re,socket,sqlite3,sys,threading,uuid
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse,parse_qs
p=argparse.ArgumentParser();p.add_argument('--receipt-dir',required=True);a=p.parse_args();folder=Path(a.receipt_dir)
if not folder.is_absolute() or 'TestDevelopment' not in folder.parts:raise ValueError('Fixture requires own task absolute directory')
folder.mkdir(parents=True,exist_ok=True);database=folder/'AcceptedRequests.sqlite3'
with sqlite3.connect(database) as c:
 c.execute('PRAGMA journal_mode=WAL');c.execute('PRAGMA synchronous=FULL');c.execute('CREATE TABLE IF NOT EXISTS accepted (key TEXT PRIMARY KEY,input_sha256 TEXT NOT NULL,accepted_id TEXT NOT NULL,posts INTEGER NOT NULL,queries INTEGER NOT NULL,drop_done INTEGER NOT NULL)');c.commit()
def key_valid(key):return bool(key and re.fullmatch(r'[A-Za-z0-9._-]{1,120}',key))
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def setup(self):super().setup();self.connection.settimeout(5)
 def json(self,status,obj):
  raw=json.dumps(obj).encode('utf8');self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
 def do_POST(self):
  if self.path!='/accept':return self.json(404,{'code':'fixture_path_denied'})
  key=self.headers.get('Idempotency-Key');length=int(self.headers.get('Content-Length','0'))
  if not key_valid(key) or length<0 or length>65536:return self.json(400,{'code':'fixture_input_invalid'})
  sha=hashlib.sha256(self.rfile.read(length)).hexdigest()
  with sqlite3.connect(database) as c:
   c.execute('PRAGMA synchronous=FULL');row=c.execute('SELECT * FROM accepted WHERE key=?',(key,)).fetchone()
   if row and row[1]!=sha:return self.json(409,{'code':'fixture_same_key_conflict'})
   if row:
    c.execute('UPDATE accepted SET posts=posts+1 WHERE key=?',(key,));accepted_id=row[2];drop=False
   else:
    accepted_id='T13-'+str(uuid.uuid4());c.execute('INSERT INTO accepted VALUES (?,?,?,1,0,1)',(key,sha,accepted_id));drop=True
   c.commit()
  if drop:
   # HTTP request really accepted durably, then response lost before producer sees id.
   try:self.connection.shutdown(socket.SHUT_RDWR)
   except OSError:pass
   self.connection.close();self.close_connection=True;return
  return self.json(200,{'accepted_id':accepted_id,'input_sha256':sha,'scope':'synthetic free owned loopback only'})
 def do_GET(self):
  u=urlparse(self.path);key=parse_qs(u.query).get('key',[''])[0]
  if u.path!='/observation' or not key_valid(key):return self.json(404,{'code':'fixture_path_denied'})
  with sqlite3.connect(database) as c:
   c.execute('PRAGMA synchronous=FULL');row=c.execute('SELECT * FROM accepted WHERE key=?',(key,)).fetchone()
   if not row:return self.json(404,{'code':'fixture_no_acceptance'})
   c.execute('UPDATE accepted SET queries=queries+1 WHERE key=?',(key,));c.commit()
  return self.json(200,{'accepted_id':row[2],'input_sha256':row[1],'posts':row[3],'queries':row[4]+1,'accepted_before_response_drop':bool(row[5]),'scope':'Actual free loopback HTTP/SQLite, no supplier billing or generation claim'})
http=ThreadingHTTPServer(('127.0.0.1',0),Handler);http.daemon_threads=True
print(json.dumps({'event':'t13_loopback_ready','port':http.server_address[1],'actual_pid':__import__('os').getpid()}),flush=True)
def read_control():
 for line in sys.stdin.buffer:
  if line==b'shutdown\n':http.shutdown();return
threading.Thread(target=read_control,daemon=True).start()
try:http.serve_forever(poll_interval=0.1)
finally:http.server_close()
