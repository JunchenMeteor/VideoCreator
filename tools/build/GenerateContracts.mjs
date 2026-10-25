import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';
import { generateNativeContracts } from './GenerateNativeContracts.mjs';
const root=fileURLToPath(new URL('../../', import.meta.url));
const args=process.argv.slice(2);
const snapshotMode=(args.length===2||(args.length===3&&args[2]==='--skip-native-file-observation'))&&args[0]==='--source-snapshot'&&path.isAbsolute(args[1]);
const artifactMode=args.length===3&&args[0]==='--export-inputs'&&args.slice(1).every(path.isAbsolute);
if(args.length&&!snapshotMode&&!artifactMode)throw new Error('Use --source-snapshot <absolute snapshot> [--skip-native-file-observation] or --export-inputs <absolute openapi> <absolute schemas>');
const snapshot=snapshotMode?args[1]:null;
const python=process.env.VIDEO_CREATOR_BUILD_PYTHON || path.join(root,'.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python');
const out=path.join(root,'packages/contracts');
const sdk=path.join(root,'packages/api-client/src/schema.d.ts');
await mkdir(out,{recursive:true});await mkdir(path.dirname(sdk),{recursive:true});
// A partial export must never leave the previous interface manifest apparently current.
await writeFile(path.join(out,'generation.manifest.json'),JSON.stringify({status:'generating',current_backend_source_bound:false,native_runtime_ready:false},null,2)+'\n');
const childEnv=Object.fromEntries(['SystemRoot','WINDIR','COMSPEC','PATHEXT','TEMP','TMP'].filter(key=>process.env[key]).map(key=>[key,process.env[key]]));
const toolTrace=process.env.VIDEO_CREATOR_BUILD_TOOL_IMPORT_TRACE_DIR;
const traceHook=process.env.VIDEO_CREATOR_BUILD_TOOL_IMPORT_HOOK;
if(Boolean(toolTrace)!==Boolean(traceHook) || (toolTrace && (!path.isAbsolute(toolTrace)||!path.isAbsolute(traceHook)))) throw new Error('Invalid build-owned tool trace configuration');
if(toolTrace) childEnv.VIDEO_CREATOR_BUILD_TOOL_IMPORT_TRACE_DIR=toolTrace;
function run(exe,args){const instrumented=toolTrace && exe===process.execPath?['--import',pathToFileURL(traceHook).href,...args]:args;const r=spawnSync(exe,instrumented,{cwd:root,stdio:'inherit',shell:false,env:childEnv});if(r.error)throw r.error;if(r.status!==0)throw new Error('Contract generation failed with exit '+r.status);}
const exportArgs=snapshot?['-I','-S','-B','-X','utf8',path.join(root,'tools/build/ExportContracts.py'),out,'--source-snapshot',snapshot,'--dependency-root',path.join(root,'.venv',process.platform==='win32'?'Lib/site-packages':'lib/python3.13/site-packages')]:['-B',path.join(root,'tools/build/ExportContracts.py'),out];
if(snapshot&&args[2]==='--skip-native-file-observation')exportArgs.push('--skip-native-file-observation');
if(artifactMode){
  const inputs=[];
  for(const [index,name]of ['openapi.json','schemas.json'].entries()){
    const body=await readFile(args[index+1]);JSON.parse(body);
    inputs.push({path:args[index+1],bytes:body.length,sha256:createHash('sha256').update(body).digest('hex')});
    await writeFile(path.join(out,name),body);
  }
  await writeFile(path.join(out,'export.sources.json'),JSON.stringify({format:'formal-export-artifacts-v1',source_mode:'formal_export_artifacts',source_inputs:inputs,current_backend_source_bound:false,backend_import_performed:false,source_closure_verified_by_this_generation:false},null,2)+'\n');
  // Explicit object API avoids CLI config discovery and external ref loading.
  run(process.execPath,[path.join(root,'tools/build/GenerateOpenApiTypes.mjs'),path.join(out,'openapi.json'),sdk]);
}else{
  run(python,exportArgs);
  if(snapshot){
    // Formal snapshot export uses the same explicit object API as artifact input.
    run(process.execPath,[path.join(root,'tools/build/GenerateOpenApiTypes.mjs'),path.join(out,'openapi.json'),sdk]);
  }else{
    const generator=path.join(root,'node_modules/openapi-typescript/bin/cli.js');
    run(process.execPath,[generator,'packages/contracts/openapi.json','--output','packages/api-client/src/schema.d.ts']);
  }
}
const api=JSON.parse(await readFile(path.join(out,'openapi.json'),'utf8'));
const routes={};
for(const [template,item] of Object.entries(api.paths)){
  for(const method of ['get','post','put','patch','delete','head','options']){
    const operation=item[method];if(!operation)continue;
    if(!operation.operationId)throw new Error('OpenAPI operation has no operationId');
    routes[method.toUpperCase()+' '+template]={method:method.toUpperCase(),template,operationId:operation.operationId,requestMedia:Object.keys(operation.requestBody?.content||{}),responseMedia:Object.fromEntries(Object.entries(operation.responses||{}).map(([status,response])=>[status,Object.keys(response.content||{})]))};
  }
}
await writeFile(path.join(root,'packages/api-client/src/routes.generated.ts'),'/* Generated from the unique OpenAPI source. Do not edit. */\nexport const ROUTES = '+JSON.stringify(routes,null,2)+' as const;\nexport type RouteKey = keyof typeof ROUTES;\n');
await generateNativeContracts(path.join(out,'openapi.json'),path.join(out,'schemas.json'),path.join(out,'NativeRouteManifest.json'),path.join(root,'packages/api-client/src/native.routes.generated.ts'));
const trace=JSON.parse(await readFile(path.join(out,'export.sources.json'),'utf8'));
if(!artifactMode&&(trace.source_changes||trace.snapshot_source_changes||trace.denied_runtime_imports.length))throw new Error('Exporter source closure drifted or imported unadmitted runtime source');
const sourceFiles=artifactMode?['tools/build/GenerateContracts.mjs','tools/build/GenerateNativeContracts.mjs','tools/build/GenerateOpenApiTypes.mjs']:snapshot?['tools/build/ExportContracts.py','tools/build/GenerateContracts.mjs','tools/build/GenerateNativeContracts.mjs','tools/build/GenerateOpenApiTypes.mjs']:[...new Set(['tools/build/ExportContracts.py','tools/build/GenerateContracts.mjs','tools/build/GenerateNativeContracts.mjs','services/engine/src/video_creator/integrations/mcp.py',...Object.values(trace.engine_source_reads).map(item=>path.relative(root,item.before_source_read.path).replaceAll('\\','/')),...['services/engine/migrations/0001_ledger.sql','services/engine/migrations/0002_cancellation_and_commands.sql','services/engine/migrations/0003_local_worker.sql','services/engine/migrations/0004_bundles.sql','services/engine/migrations/0005_alignment_admissions.sql']])].sort();
const outputs=['packages/contracts/openapi.json','packages/contracts/schemas.json','packages/contracts/export.sources.json','packages/contracts/NativeRouteManifest.json','packages/api-client/src/schema.d.ts','packages/api-client/src/routes.generated.ts','packages/api-client/src/native.routes.generated.ts'];
const hash=async file=>createHash('sha256').update(await readFile(path.join(root,file))).digest('hex');
const source=Object.fromEntries(await Promise.all(sourceFiles.map(async f=>[f,await hash(f)])));
if(snapshot) for(const [relative,item] of Object.entries(trace.snapshot_source_identity)) source[relative]=item.after_export.sha256;
const generated=Object.fromEntries(await Promise.all(outputs.map(async f=>[f,await hash(f)])));
await writeFile(path.join(out,'generation.manifest.json'),JSON.stringify({status:artifactMode?'formal_export_interface_candidate':'current_export_interface',current_backend_source_bound:!artifactMode,native_runtime_ready:false,source_mode:trace.source_mode,source_snapshot:trace.source_snapshot||null,...(artifactMode?{export_artifact_inputs:trace.source_inputs,actual_export_artifact_provenance:'export.sources.json'}:{}),schema_version:JSON.parse(await readFile(path.join(out,'schemas.json'),'utf8')).schema_version,api_info_version:api.info.version,generator:'openapi-typescript@7.13.0',backend_entry:artifactMode?null:'video_creator.cli.main export-contracts',actual_export_closure:artifactMode?null:'export.sources.json',sources:source,outputs:generated},null,2)+'\n');
