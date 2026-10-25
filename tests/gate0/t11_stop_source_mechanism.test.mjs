import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readFile,writeFile,mkdir } from 'node:fs/promises';
import path from 'node:path';
import vm from 'node:vm';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { cleanupRuntimeChildren } from '../../tools/build/EngineProcess.mjs';
const repo=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const caseRoot=process.env.VIDEO_CREATOR_T11_CASES;
assert(caseRoot&&path.isAbsolute(caseRoot));
const hash=(value)=>createHash('sha256').update(value).digest('hex');
const sourcePath=path.join(repo,'tools/build/DevRuntime.mjs');
const sourceBytes=await readFile(sourcePath);assert.equal(hash(sourceBytes),'c45c5132bcc457afdbb84808809873511a05c78a09199a52af6d962bec53b034');
const source=sourceBytes.toString('utf8');const begin=source.indexOf('let engine;');const end=source.indexOf('\nif (controlEnabled) {',begin);assert(begin>=0&&end>begin);const actualBlock=source.slice(begin,end);
function fixture(){
 let resolveGate;const gate=new Promise((resolve)=>resolveGate=resolve);const calls=[];const logs=[];const handlers=new Map();
 const ownership={verified:true,captured:[],alive:[],unproven_children:[],inspection_error:null};
 const api={classification:'normal',scope:'api',exit:{code:0,signal:null},marker_count:1,port_closed:true,ownership};
 const vite={exit:{code:1,signal:null},actions:[{pid:10001,tool_exit_code:0}],ownership};
 const context={cleanupRuntimeChildren,injectedEngine:{child:{exitCode:null,signalCode:null},shutdown:async()=>{calls.push('synthetic_api_cleanup');await gate;return api;}},injectedVite:{force:async()=>{calls.push('synthetic_vite_cleanup');await gate;return vite;}},process:{exitCode:0,once:(name,callback)=>handlers.set(name,callback)},console:{log:(line)=>logs.push(line),error:(line)=>logs.push(line)}};
 const state=new vm.Script(actualBlock+'\nengine=injectedEngine; viteOwned=injectedVite; hostReady=true; ({stop, getPromise:()=>stopping, getFlags:()=>({lifecycleFailed,trustedStopRequested,earlyStopRequested})});',{filename:sourcePath+':T11SourceBoundMechanism'}).runInNewContext(context);
 return {state,context,calls,logs,handlers,release:resolveGate};
}
const cases=[
 {name:'SigTermOnly',actions:['SIGTERM']},
 {name:'SigIntOnly',actions:['SIGINT']},
 {name:'ControlThenSigTermPending',actions:['control','SIGTERM']},
 {name:'SigTermThenControlPending',actions:['SIGTERM','control']},
 {name:'ControlThenSigIntPending',actions:['control','SIGINT']},
 {name:'ControlThenChildFailurePending',actions:['control','child_failure']},
 {name:'ControlSettledThenSigTermBeforeHostExit',actions:['control','settle','SIGTERM']},
];
for(const scenario of cases)test('source-bound '+scenario.name+' preserves abnormal exit and single cleanup promise',async()=>{
 const f=fixture();let firstPromise;let samePromise=true;const checkpoints=[];
 for(const action of scenario.actions){
  if(action==='settle'){f.release();await f.state.getPromise();checkpoints.push({action,flags:f.state.getFlags(),exitCode:f.context.process.exitCode});continue;}
  if(action==='control')f.state.stop('host_control');else if(action==='child_failure')f.state.stop('engine_exited',true);else f.handlers.get(action)();
  const promise=f.state.getPromise();if(!firstPromise)firstPromise=promise;else samePromise&&=promise===firstPromise;
  checkpoints.push({action,flags:f.state.getFlags(),exitCode:f.context.process.exitCode});
 }
 f.release();await firstPromise;
 const folder=path.join(caseRoot,scenario.name);await mkdir(folder,{recursive:true});const receipts={source_path:sourcePath,source_sha256:hash(sourceBytes),block_character_start:begin,block_character_end:end,block_sha256:hash(actualBlock),actual_block_source:actualBlock,actions:scenario.actions,checkpoints,actual_same_promise:samePromise,actual_exit_code_field:f.context.process.exitCode,calls:f.calls,public_logs:f.logs,final_flags:f.state.getFlags(),actual_os_signals_sent:0,actual_product_processes_started:0,synthetic_cleanup_resources:true,provider_calls:0,real_key_reads:0,scope:'Actual frozen source stop declarations and registered signal callbacks in isolated VM, real cleanupRuntimeChildren with synthetic resource callbacks. Callback/exitCode field evidence only; no real Windows signal, host close, or OS resource claim.'};
 await writeFile(path.join(folder,'Receipt.json'),JSON.stringify(receipts,null,2)+'\n');
 assert.equal(f.calls.filter((name)=>name==='synthetic_api_cleanup').length,1);assert.equal(f.calls.filter((name)=>name==='synthetic_vite_cleanup').length,1);assert.equal(samePromise,true);assert.equal(f.state.getFlags().lifecycleFailed,true);
 assert.equal(f.context.process.exitCode,1,'An abnormal callback before actual host exit must retain nonzero even when cleanup promise is reused');
 if(!scenario.actions.includes('settle'))assert.equal(JSON.parse(f.logs[0]).classification,'error');
 });
