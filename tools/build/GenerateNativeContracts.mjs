import {createHash} from 'node:crypto';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import path from 'node:path';

export async function generateNativeContracts(openapiFile,contractFile,manifestFile,typescriptFile){
  const bytes=await readFile(openapiFile),api=JSON.parse(bytes);
  const schemas=JSON.parse(await readFile(contractFile,'utf8'));
  const root=api['x-engine-transport'];
  if(root?.format!=='engine-http-transport-v1-candidate'||root.contract_set_version!==schemas.schema_version||root.api_info_version!==api.info.version||root.native_constraints?.native_ipc_format!=='native-ipc-v1-candidate')throw new Error('Unknown or inconsistent unique transport contract');
  if(root.native_constraints.arbitrary_url_method_path!==false||root.native_constraints.redirects!=='reject'||root.native_constraints.environment_proxy!=='disabled')throw new Error('Unbounded native target constraint');
  const operations={};
  for(const [template,item]of Object.entries(api.paths))for(const method of ['get','post','put','patch','delete','head','options']){
    const op=item[method];if(!op)continue;
    const metadata=op['x-engine-transport'];
    if(!op.operationId||operations[op.operationId]||metadata?.format!==root.format||!['none','json_bytes','raw_bytes'].includes(metadata.body?.kind)||!['json','json_or_sse','original_file_bytes'].includes(metadata.response?.kind)||!['installation_owner_only','current_principal_registration','actual_owner_management'].includes(metadata.authorization?.mode)||metadata.automatic_http_retry!==false)throw new Error('Missing or unknown operation transport declaration');
    // Preserve management declarations; this manifest does not grant an installation session management authority.
    if(metadata.authorization.mode==='actual_owner_management'&&(metadata.authorization.owning_principal_required!==true||metadata.authorization.installation_session_accepted!==false||typeof metadata.native_admission!=='string'||!metadata.native_admission))throw new Error('Management declaration lacks its separate authority constraint');
    const security=op.security??api.security;
    if(!Array.isArray(security)||!security.length||security.some(alternative=>Object.entries(alternative).some(([name,scopes])=>{const s=api.components?.securitySchemes?.[name];return s?.type!=='http'||s?.scheme!=='bearer'||!Array.isArray(scopes)||scopes.length;})))throw new Error('Native operation has no declared host bearer security');
    const parameters=[...(item.parameters??[]),...(op.parameters??[])];
    const headerRules={};
    for(const p of parameters.filter(p=>p.in==='header')){
      const name=p.name.toLowerCase();
      if(headerRules[name])throw new Error('Conflicting unique header declarations');
      headerRules[name]=p;
    }
    if(op.requestBody?.content){
      const types=Object.keys(op.requestBody.content);
      const declared=headerRules['content-type'];
      headerRules['content-type']={...(declared??{name:'Content-Type',in:'header',required:false}),media_types:types,source:declared?'operation.parameter+requestBody.content':'operation.requestBody.content'};
    }
    for(const name of metadata.request_headers??[])if(!headerRules[name.toLowerCase()])throw new Error('Allowed header has no unique source grammar');
    if(!Array.isArray(metadata.request_headers)||!Array.isArray(metadata.response_headers))throw new Error('Missing header constraints');
    if(metadata.body.kind!=='none'&&!op.requestBody?.content)throw new Error('Body mode has no unique OpenAPI body');
    operations[op.operationId]={operation_id:op.operationId,method:method.toUpperCase(),path_template:template,parameters,header_rules:headerRules,request_body:op.requestBody??null,responses:op.responses,security,transport:metadata};
  }
  if(Object.keys(operations).length!==root.operation_count)throw new Error('Unique transport operation count mismatch');
  const manifest={format:'native-route-manifest-v1-candidate',contract_version:schemas.schema_version,transport_format:root.native_constraints.native_ipc_format,openapi_sha256:createHash('sha256').update(bytes).digest('hex'),engine_transport:root,security_schemes:api.components.securitySchemes,components:api.components.schemas,operations};
  const serialized=JSON.stringify(manifest,null,2)+'\n',sha=createHash('sha256').update(serialized).digest('hex');
  await mkdir(path.dirname(manifestFile),{recursive:true});await mkdir(path.dirname(typescriptFile),{recursive:true});
  await writeFile(manifestFile,serialized);
  const ts='/* Generated only from the unique OpenAPI transport declaration. Do not edit. */\n'+
    'export const NATIVE_ROUTE_MANIFEST_SHA256 = '+JSON.stringify(sha)+' as const;\n'+
    'export const NATIVE_CONTRACT_VERSION = '+JSON.stringify(manifest.contract_version)+' as const;\n'+
    'export const NATIVE_TRANSPORT_FORMAT = '+JSON.stringify(manifest.transport_format)+' as const;\n'+
    'export const NATIVE_CONSTRAINTS = '+JSON.stringify(root.native_constraints,null,2)+' as const;\n'+
    'export const NATIVE_COMPONENTS = '+JSON.stringify(manifest.components,null,2)+' as const;\n'+
    'export const NATIVE_ROUTES = '+JSON.stringify(operations,null,2)+' as const;\n';
  await writeFile(typescriptFile,ts);
  return{manifest_sha256:sha,openapi_sha256:manifest.openapi_sha256,operation_count:Object.keys(operations).length};
}
