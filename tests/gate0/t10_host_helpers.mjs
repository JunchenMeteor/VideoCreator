import assert from 'node:assert/strict';
import cp from 'node:child_process';
import path from 'node:path';
import net from 'node:net';
import { promisify } from 'node:util';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
export const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
export const caseRoot = process.env.VIDEO_CREATOR_T10_CASES;
assert(caseRoot && path.isAbsolute(caseRoot));
const execute = promisify(cp.execFile);
export const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
export const hash = (data) => createHash('sha256').update(data).digest('hex');
export function safeEnv() { const env = {}; for (const name of ['SystemRoot','WINDIR','ComSpec','PATH','PATHEXT','TEMP','TMP','PSModulePath','LOCALAPPDATA','APPDATA']) if(process.env[name]) env[name]=process.env[name]; return {...env, PYTHONUTF8:'1',PYTHONIOENCODING:'utf-8',OTEL_SDK_DISABLED:'true',CREWAI_TRACING_ENABLED:'false'}; }
export async function directory(name) { const p = path.join(caseRoot,name); await mkdir(p,{recursive:true});return p; }
export async function jsonFile(p,v){await writeFile(p,JSON.stringify(v,null,2)+'\n');}
export async function pin(paths){const output={};for(const p of paths)output[p]=hash(await readFile(p));return output;}
export async function metadata(pids,children=false){
 const ids=[...new Set(pids)];assert(ids.every((pid)=>Number.isSafeInteger(pid)&&pid>0)&&ids.length<=128); if(!ids.length)return [];
 const filter=ids.map((pid)=>'ProcessId='+pid+(children?' OR ParentProcessId='+pid:'')).join(' OR ');
 const script='$ErrorActionPreference="Stop"; $rows=@(Get-CimInstance Win32_Process -Filter "'+filter+'" -Property ProcessId,ParentProcessId,CreationDate | ForEach-Object { [pscustomobject]@{pid=[int]$_.ProcessId;parent_pid=[int]$_.ParentProcessId;created_utc=$_.CreationDate.ToUniversalTime().ToString("o")} }); ConvertTo-Json -InputObject $rows -Compress';
 const {stdout}=await execute(path.join(process.env.SystemRoot,'System32/WindowsPowerShell/v1.0/powershell.exe'),['-NoProfile','-NonInteractive','-Command',script],{encoding:'utf8',timeout:10000,windowsHide:true,env:safeEnv()});
 const result=JSON.parse(stdout.replace(/^\uFEFF/,'').trim()||'[]');return Array.isArray(result)?result:[result];
}
export async function tree(pid){const rows=new Map();let seeds=[pid];for(let depth=0;depth<10&&seeds.length;depth++){const batch=await metadata(seeds,true);const next=[];for(const row of batch){if(rows.has(row.pid))continue;rows.set(row.pid,row);next.push(row.pid);}assert(rows.size<=128);seeds=next;}return [...rows.values()];}
export async function freePort(){const server=net.createServer();await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolve);});const port=server.address().port;await new Promise((resolve)=>server.close(resolve));assert(port>=1024);return port;}
export async function portClosed(port){return new Promise((resolve)=>{const socket=net.createConnection({host:'127.0.0.1',port});const done=(value)=>{socket.destroy();resolve(value);};socket.once('connect',()=>done(false));socket.once('error',(error)=>done(error.code==='ECONNREFUSED'));socket.setTimeout(1500,()=>done(null));});}
export function collect(child){let stdout='',stderr='';child.stdout?.on('data',(part)=>stdout+=part.toString('utf8'));child.stderr?.on('data',(part)=>stderr+=part.toString('utf8'));const closed=new Promise((resolve)=>{child.once('close',(code,signal)=>resolve({code,signal}));child.once('error',()=>{});});return {child,closed,output:()=>({stdout,stderr}),events:()=>stdout.split(/\r?\n/).flatMap((line)=>{try{return [JSON.parse(line)];}catch{return [];}})};}
export async function bounded(promise,ms=25000){let timer;try{return await Promise.race([promise,new Promise((_,reject)=>timer=setTimeout(()=>reject(new Error('T10 actual close timeout')),ms))]);}finally{clearTimeout(timer);}}
export async function host(name,{port,control=true,args=[],env={},stdin='pipe',dataDir}={}){
 const folder=await directory(name);const argv=[path.join(repo,'tools/build/DevRuntime.mjs'),'--data-dir',dataDir||path.join(folder,'Instance'),...(port!==undefined?['--workbench-port',String(port)]:[]),...(control?['--control-stdin']:[]),...args];
 const child=cp.spawn(process.execPath,argv,{cwd:repo,env:{...safeEnv(),VIDEO_CREATOR_PYTHON:path.join(repo,'.venv/Scripts/python.exe'),VIDEO_CREATOR_RESOURCE_MANIFEST:path.resolve(repo,'../../Codex/VideoCreatorImplementation/Integration/Evidence/MediaRuntimeManifest.json'),...env},stdio:[stdin,'pipe','pipe'],shell:false,windowsHide:true});
 return {...collect(child),folder,argv,executable:process.execPath};
}
export async function event(run,name,ms=30000){const deadline=Date.now()+ms;while(Date.now()<deadline){const found=run.events().find((item)=>item.event===name);if(found)return found;if(run.child.exitCode!==null||run.child.signalCode!==null)throw new Error('T10 host exited before '+name);await sleep(50);}throw new Error('T10 event timeout '+name);}
export async function send(run,bytes){assert(run.child.stdin&&!run.child.stdin.destroyed);await new Promise((resolve,reject)=>run.child.stdin.write(bytes,(error)=>error?reject(error):resolve()));}
export async function save(run,facts){await writeFile(path.join(run.folder,'Stdout.txt'),run.output().stdout);await writeFile(path.join(run.folder,'Stderr.txt'),run.output().stderr);await jsonFile(path.join(run.folder,'Receipt.json'),{...facts,actual_executable:run.executable,actual_args:run.argv,root_pid:run.child.pid,provider_calls:0,real_key_reads:0});}
export async function holder(name,port=0){const folder=await directory(name);const argv=[path.join(repo,'tests/gate0/T10Fixture/OwnedPortHolder.mjs'),String(port)];const child=cp.spawn(process.execPath,argv,{cwd:repo,env:safeEnv(),stdio:['ignore','pipe','pipe','ipc'],windowsHide:true,shell:false});const run={...collect(child),folder,argv,executable:process.execPath};run.ready=await bounded(new Promise((resolve,reject)=>{child.once('message',resolve);child.once('error',reject);}),8000);assert.equal(run.ready.event,'holder_ready');run.identity=await metadata([child.pid]);assert.equal(run.identity.length,1,'Positive sibling protection requires live captured holder');return run;}
export async function closeHolder(run){if(run.child.connected)run.child.send('close');const exit=await bounded(run.closed,8000);assert.deepEqual(exit,{code:0,signal:null});return exit;}
export async function cleanupHost(run,captured=[]){if(run.child.exitCode!==null||run.child.signalCode!==null)return {mode:'already_closed',exit:await run.closed};try{await send(run,Buffer.from('shutdown\n'));return {mode:'private_frame',exit:await bounded(run.closed)};}catch(error){
 const current=await metadata([run.child.pid]);const original=captured.find((row)=>row.pid===run.child.pid);if(!original||!current.some((row)=>row.pid===original.pid&&row.created_utc===original.created_utc))return {mode:'identity_unknown_no_force',error:'owned_cleanup_unconfirmed'};
 const actions=[];try{await execute(path.join(process.env.SystemRoot,'System32/taskkill.exe'),['/PID',String(run.child.pid),'/T','/F'],{windowsHide:true,timeout:5000});actions.push({pid:run.child.pid,tool_exit_code:0});}catch{actions.push({pid:run.child.pid,error:'test_cleanup_force_failed'});}return {mode:'verified_owned_force_not_normal',actions,exit:await bounded(run.closed,8000)};
}}
