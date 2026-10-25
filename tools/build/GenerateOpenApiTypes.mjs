// Fixed local OpenAPI object -> official openapi-typescript, no CLI config search.
import {readFile,writeFile} from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import openapiTS,{astToString} from 'openapi-typescript';
const args=process.argv.slice(2);
if(args.length!==2||!args.every(path.isAbsolute))throw new Error('Two absolute input/output files required');
const api=JSON.parse(await readFile(args[0],'utf8'));
function validate(value){
  if(!value||typeof value!=='object')return;
  if(Object.hasOwn(value,'$ref')&&(typeof value.$ref!=='string'||!value.$ref.startsWith('#/')))throw new Error('Only internal OpenAPI refs are admitted');
  for(const child of Object.values(value))validate(child);
}
validate(api);
const ast=await openapiTS(api,{cwd:pathToFileURL(path.dirname(args[0])+path.sep)});
await writeFile(args[1],'/* Generated from unique fixed OpenAPI by openapi-typescript@7.13.0. Do not edit. */\n'+astToString(ast));
