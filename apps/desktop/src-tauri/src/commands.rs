//! Fixed IPC grammar; the actual invoking Webview is the authorization source.
use std::sync::Arc;
use serde::{Deserialize,de::DeserializeOwned};
use serde_json::{Value,json};
use tauri::{WebviewWindow,State,ipc::{Request,InvokeBody,Response}};
use crate::{session::HostState,route_contract::{OpenRequest,TransportError},transport::{Broker,Descriptor,Head,UploadAck},wire};
fn error(code:&'static str)->TransportError{TransportError::new(code,"validation",false)}
fn authorize(window:&WebviewWindow,state:&HostState)->Result<(),TransportError>{
    let url=window.url().map_err(|_|error("native_source_unavailable"))?;
    state.authorize(window.label(),&url).map_err(error)
}
fn context(window:&WebviewWindow,state:&HostState,generation:&str)->Result<Arc<Broker>,TransportError>{
    let url=window.url().map_err(|_|error("native_source_unavailable"))?;
    state.context(window.label(),&url,Some(generation)).map(|(broker,_)|broker)
}
fn json_body<T:DeserializeOwned>(request:&Request<'_>)->Result<T,TransportError>{
    match request.body(){InvokeBody::Json(value)=>serde_json::from_value(value.clone()).map_err(|_|error("native_arguments_invalid")),_=>Err(error("native_arguments_invalid"))}
}
#[derive(Deserialize)]#[serde(deny_unknown_fields)]
struct Handle {generation:String,request_handle:String}
#[derive(Deserialize)]#[serde(deny_unknown_fields)]
struct Finish {generation:String,request_handle:String,seq:String,total_bytes:String}
#[derive(Deserialize)]#[serde(deny_unknown_fields)]
struct Read {generation:String,request_handle:String,seq:String,offset:String,max_bytes:usize}
#[tauri::command]
pub fn get_engine_session(window:WebviewWindow,state:State<'_,Arc<HostState>>,request:Request<'_>)->Result<Descriptor,TransportError>{
    authorize(&window,&state)?;
    if !matches!(request.body(),InvokeBody::Json(v) if v.as_object().is_some_and(|o|o.is_empty())){return Err(error("native_arguments_invalid"));}
    let url=window.url().map_err(|_|error("native_source_unavailable"))?;state.descriptor(window.label(),&url)
}
#[tauri::command]
pub fn engine_request_open(window:WebviewWindow,state:State<'_,Arc<HostState>>,request:Request<'_>)->Result<Value,TransportError>{
    authorize(&window,&state)?;let input:OpenRequest=json_body(&request)?;
    let broker=context(&window,&state,&input.generation)?;broker.open(input).map(|handle|json!({"request_handle":handle}))
}
#[tauri::command]
pub async fn engine_upload_chunk(window:WebviewWindow,state:State<'_,Arc<HostState>>,request:Request<'_>)->Result<UploadAck,TransportError>{
    authorize(&window,&state)?;
    let private_header=|name:&str|request.headers().get(name).and_then(|v|v.to_str().ok()).map(str::to_owned).ok_or(error("native_arguments_invalid"));
    let handle=private_header("x-video-creator-request-handle")?;let generation=private_header("x-video-creator-generation")?;let seq=private_header("x-video-creator-sequence")?;
    let broker=context(&window,&state,&generation)?;
    let bytes=match request.body(){InvokeBody::Raw(bytes) if bytes.len()<=wire::CHUNK+24=>bytes.clone(),_=>return Err(error("native_arguments_invalid"))};
    broker.upload(&handle,&generation,&seq,&bytes).await
}
#[tauri::command]
pub async fn engine_upload_finish(window:WebviewWindow,state:State<'_,Arc<HostState>>,request:Request<'_>)->Result<(),TransportError>{
    authorize(&window,&state)?;let p:Finish=json_body(&request)?;let broker=context(&window,&state,&p.generation)?;
    broker.finish(&p.request_handle,&p.generation,&p.seq,&p.total_bytes).await
}
#[tauri::command]
pub async fn engine_response_head(window:WebviewWindow,state:State<'_,Arc<HostState>>,request:Request<'_>)->Result<Head,TransportError>{
    authorize(&window,&state)?;let p:Handle=json_body(&request)?;let broker=context(&window,&state,&p.generation)?;broker.head(&p.request_handle,&p.generation).await
}
#[tauri::command]
pub async fn engine_response_read(window:WebviewWindow,state:State<'_,Arc<HostState>>,request:Request<'_>)->Result<Response,TransportError>{
    authorize(&window,&state)?;let p:Read=json_body(&request)?;let broker=context(&window,&state,&p.generation)?;
    broker.read(&p.request_handle,&p.generation,&p.seq,&p.offset,p.max_bytes).await.map(Response::new)
}
#[tauri::command]
pub async fn engine_request_release(window:WebviewWindow,state:State<'_,Arc<HostState>>,request:Request<'_>)->Result<(),TransportError>{
    authorize(&window,&state)?;let p:Handle=json_body(&request)?;let broker=context(&window,&state,&p.generation)?;broker.release(&p.request_handle,&p.generation).await
}
#[tauri::command]
pub async fn engine_request_abort(window:WebviewWindow,state:State<'_,Arc<HostState>>,request:Request<'_>)->Result<(),TransportError>{
    // HTTP cancellation only: no Production cancel operation is synthesized.
    authorize(&window,&state)?;let p:Handle=json_body(&request)?;let broker=context(&window,&state,&p.generation)?;broker.release(&p.request_handle,&p.generation).await
}

fn setup_context(window:&WebviewWindow,state:&HostState,generation:Option<&str>)->Result<String,TransportError>{
    let url=window.url().map_err(|_|error("native_source_unavailable"))?;
    state.setup_context(window.label(),&url,generation)
}
#[derive(Deserialize)]#[serde(deny_unknown_fields)]
struct SetupStatusInput { generation:Option<String> }
#[tauri::command]
pub fn owner_setup_status(window:WebviewWindow,state:State<'_,Arc<HostState>>,request:Request<'_>)->Result<crate::owner_setup::SetupView,TransportError>{
    authorize(&window,&state)?;let input:SetupStatusInput=json_body(&request)?;
    let generation=setup_context(&window,&state,input.generation.as_deref())?;
    state.setup.status(&generation).map_err(error)
}
#[tauri::command]
pub fn owner_setup_prepare(window:WebviewWindow,state:State<'_,Arc<HostState>>,request:Request<'_>)->Result<crate::owner_setup::SetupView,TransportError>{
    authorize(&window,&state)?;let input:crate::owner_setup::PrepareInput=json_body(&request)?;
    setup_context(&window,&state,Some(&input.generation))?;
    state.setup.prepare(input).map_err(error)
}
#[tauri::command]
pub fn owner_setup_present(window:WebviewWindow,state:State<'_,Arc<HostState>>,request:Request<'_>)->Result<crate::owner_setup::SetupView,TransportError>{
    authorize(&window,&state)?;let input:crate::owner_setup::AttemptInput=json_body(&request)?;
    setup_context(&window,&state,Some(&input.generation))?;
    state.setup.present(input).map_err(error)
}
#[tauri::command]
pub fn owner_setup_abort(window:WebviewWindow,state:State<'_,Arc<HostState>>,request:Request<'_>)->Result<crate::owner_setup::SetupView,TransportError>{
    authorize(&window,&state)?;let input:crate::owner_setup::AttemptInput=json_body(&request)?;
    setup_context(&window,&state,Some(&input.generation))?;
    state.setup.abort(input).map_err(error)
}
