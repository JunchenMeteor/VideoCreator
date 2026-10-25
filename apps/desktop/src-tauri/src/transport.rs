//! Native HTTP broker. Bearer is private memory and never a serializable DTO.
use std::{collections::BTreeMap, future::Future, io, pin::Pin, sync::{Arc, Mutex, atomic::{AtomicBool, Ordering}}, task::{Context, Poll}, time::Duration};
use bytes::Bytes;
use futures_core::Stream;
use serde::Serialize;
use tokio::sync::{Mutex as AsyncMutex, mpsc, watch};
use tokio::io::AsyncReadExt;
use tokio_util::io::StreamReader;
use reqwest::{Client, Url, header::{ACCEPT_ENCODING, CONTENT_LENGTH}};
use sha2::{Digest, Sha256};
use crate::{route_contract::{Contract, OpenRequest, Route, TransportError, random_id}, wire};

const IDLE: Duration = Duration::from_secs(30);
#[derive(Serialize, Clone)]
pub struct Limits { pub max_http_handles: usize, pub max_chunk_bytes: usize, pub max_buffered_frames: usize,
    pub open_timeout_ms: u64, pub head_timeout_ms: u64, pub upload_idle_timeout_ms: u64, pub read_idle_timeout_ms: u64 }
impl Default for Limits { fn default() -> Self { Self { max_http_handles:8,max_chunk_bytes:wire::CHUNK,max_buffered_frames:2,open_timeout_ms:10000,head_timeout_ms:30000,upload_idle_timeout_ms:30000,read_idle_timeout_ms:30000 } } }
#[derive(Serialize)]
pub struct Descriptor { pub mode:&'static str, pub instance_id:String,pub generation:String,pub contract_version:String,
    pub route_manifest_sha256:String,pub transport_format:String,pub limits:Limits }
pub struct Connection { base:Url, bearer:String, instance_id:String, valid:AtomicBool, client:Client }
impl Connection {
    /// Only the owned child/health verifier calls this. No renderer constructor exists.
    pub fn verified(base:Url,bearer:String,instance_id:String)->Result<Self,&'static str>{
        if base.scheme()!="http"||base.host_str()!=Some("127.0.0.1")||base.port().is_none()||base.path()!="/"||base.query().is_some()||base.fragment().is_some()||!base.username().is_empty()||base.password().is_some()||bearer.len()<32{return Err("native_connection_invalid");}
        let client=Client::builder().no_proxy().redirect(reqwest::redirect::Policy::none()).no_gzip().no_brotli().no_deflate().no_zstd()
            .http1_only().connect_timeout(Duration::from_secs(5))
            .build().map_err(|_|"native_client_unavailable")?;
        Ok(Self {base,bearer,instance_id,valid:AtomicBool::new(true),client})
    }
    pub fn invalidate(&self){self.valid.store(false,Ordering::Release);}
    pub fn is_valid(&self)->bool{self.valid.load(Ordering::Acquire)}
    pub async fn verify_health(&self,contract:&Contract)->Result<(),&'static str>{
        let deadline=tokio::time::Instant::now()+Duration::from_secs(5);
        let operation_id=contract.unique_json_operation("InstanceHealth")?;
        let input=OpenRequest{generation:"host".into(),client_request_id:random_id()?,operation_id,path_params:BTreeMap::new(),query:BTreeMap::new(),headers:BTreeMap::new(),body:crate::route_contract::RequestBody{kind:"none".into(),length:None}};
        let(_,url,headers,_)=contract.resolve(&input,&self.base)?;
        let mut response=tokio::time::timeout_at(deadline,self.client.get(url).headers(headers).header(ACCEPT_ENCODING,"identity").bearer_auth(&self.bearer).send()).await.map_err(|_|"native_health_unverified")?.map_err(|_|"native_health_unverified")?;
        if response.status()!=200{return Err("native_health_unverified");}
        let mut body=Vec::new();
        loop{let item=tokio::time::timeout_at(deadline,response.chunk()).await.map_err(|_|"native_health_unverified")?.map_err(|_|"native_health_unverified")?;
            match item{None=>break,Some(bytes)=>{if body.len()+bytes.len()>4096{return Err("native_health_invalid");}body.extend(bytes);}}
        }
        let value:serde_json::Value=serde_json::from_slice(&body).map_err(|_|"native_health_invalid")?;
        if value["instance_id"]!=self.instance_id||value["schema_version"]!=contract.version{return Err("native_health_instance_mismatch");}Ok(())
    }
}
#[derive(Serialize,Clone)]
pub struct Head { pub status:u16,pub headers:BTreeMap<String,String>,pub body_kind:&'static str,#[serde(skip_serializing_if="Option::is_none")]pub content_length:Option<String> }
#[derive(Serialize,Clone)]
pub struct UploadAck { pub seq:String,pub next_offset:String }
struct Upload { sender:Option<mpsc::Sender<Result<Bytes,io::Error>>>,length:Option<u64>,offset:u64,seq:u64,
    last:Option<(u64,u64,[u8;32],UploadAck)>,finished:bool }
struct HttpStream { inner:Pin<Box<dyn Stream<Item=Result<Bytes,reqwest::Error>>+Send>> }
impl Stream for HttpStream {
    type Item=Result<Bytes,io::Error>;
    fn poll_next(mut self:Pin<&mut Self>,cx:&mut Context<'_>)->Poll<Option<Self::Item>>{
        self.inner.as_mut().poll_next(cx).map(|item|item.map(|r|r.map_err(|_|io::Error::other("native_http_read_failed"))))
    }
}
struct Read { response:Option<StreamReader<HttpStream,Bytes>>,offset:u64,seq:u64,last:Option<(u64,u64,Vec<u8>)>,eof:bool,consumer:Consumer }
#[derive(Clone,Copy,PartialEq,Eq)]
enum Consumer { None, Stream, Save }
pub struct Request { pub id:String, pub generation:String, pub route:Arc<Route>,upload:AsyncMutex<Upload>,read:AsyncMutex<Read>,
    head:watch::Sender<Option<Result<Head,TransportError>>>,head_rx:watch::Receiver<Option<Result<Head,TransportError>>>,task:Mutex<Option<tokio::task::AbortHandle>>,closed:AtomicBool,cancel:watch::Sender<bool> }
struct BodyStream { receiver:mpsc::Receiver<Result<Bytes,io::Error>>,timer:Pin<Box<tokio::time::Sleep>>,ended:bool }
impl Stream for BodyStream {
    type Item=Result<Bytes,io::Error>;
    fn poll_next(mut self:Pin<&mut Self>,context:&mut Context<'_>)->Poll<Option<Self::Item>>{
        if self.ended{return Poll::Ready(None);}
        match self.receiver.poll_recv(context){
            Poll::Ready(value)=>{if value.is_some(){self.timer.as_mut().reset(tokio::time::Instant::now()+IDLE);}else{self.ended=true;}Poll::Ready(value)},
            Poll::Pending=>{if self.timer.as_mut().poll(context).is_ready(){self.ended=true;Poll::Ready(Some(Err(io::ErrorKind::TimedOut.into())))}else{Poll::Pending}},
        }
    }
}
struct Handles { requests:BTreeMap<String,Arc<Request>>,client_ids:BTreeMap<String,(String,[u8;32])> }
pub struct Broker { pub contract:Arc<Contract>,connection:Arc<Connection>,handles:Arc<Mutex<Handles>> }
fn error(code:&'static str,phase:&'static str,accepted:bool)->TransportError{TransportError::new(code,phase,accepted)}
impl Broker {
    pub fn new(connection:Arc<Connection>,contract:Arc<Contract>)->Self{Self{contract,connection,handles:Arc::new(Mutex::new(Handles{requests:BTreeMap::new(),client_ids:BTreeMap::new()}))}}
    pub fn descriptor(&self,generation:&str)->Result<Descriptor,TransportError>{
        if !self.connection.is_valid(){return Err(error("native_session_unavailable","session",false));}
        Ok(Descriptor{mode:"native",instance_id:self.connection.instance_id.clone(),generation:generation.to_owned(),contract_version:self.contract.version.clone(),route_manifest_sha256:self.contract.sha256.clone(),transport_format:self.contract.format.clone(),limits:Limits::default()})
    }
    pub fn get(&self,id:&str,generation:&str)->Result<Arc<Request>,TransportError>{
        let book=self.handles.lock().map_err(|_|error("native_state_unavailable","session",false))?;
        let request=book.requests.get(id).ok_or(error("native_handle_unavailable","validation",false))?.clone();
        if request.generation!=generation||request.closed.load(Ordering::Acquire){return Err(error("native_generation_invalid","validation",false));}Ok(request)
    }
    pub fn open(&self,input:OpenRequest)->Result<String,TransportError>{
        if !self.connection.is_valid(){return Err(error("native_session_invalid","session",false));}
        let (route,url,headers,length)=self.contract.resolve(&input,&self.connection.base).map_err(|c|error(c,"validation",false))?;
        let signature=serde_json::to_vec(&(&input.operation_id,&input.path_params,&input.query,&input.headers,&input.body.kind,&input.body.length)).map_err(|_|error("native_body_invalid","validation",false))?;
        let digest:[u8;32]=Sha256::digest(signature).into();
        let mut book=self.handles.lock().map_err(|_|error("native_state_unavailable","open",false))?;
        if let Some((id,hash))=book.client_ids.get(&input.client_request_id){
            if hash!=&digest{return Err(error("native_request_replay_conflict","open",true));}
            let current=book.requests.get(id).ok_or(error("native_request_already_released","open",true))?;
            if current.generation!=input.generation{return Err(error("native_generation_invalid","open",true));}return Ok(id.clone());
        }
        if book.requests.len()>=8{return Err(error("native_handle_limit","open",false));}
        // Bound retained replay identities; never evict and silently resend an old operation.
        if book.client_ids.len()>=4096{return Err(error("native_generation_exhausted","open",false));}
        let id=random_id().map_err(|c|error(c,"open",false))?;
        let (sender,receiver)=mpsc::channel(1);let(head,head_rx)=watch::channel(None);let(cancel,_)=watch::channel(false);
        let request=Arc::new(Request{id:id.clone(),generation:input.generation,route:route.clone(),upload:AsyncMutex::new(Upload{sender:if length.is_some(){Some(sender)}else{None},length,offset:0,seq:0,last:None,finished:length.is_none()}),
            read:AsyncMutex::new(Read{response:None,offset:0,seq:0,last:None,eof:false,consumer:Consumer::None}),head,head_rx,task:Mutex::new(None),closed:AtomicBool::new(false),cancel});
        book.client_ids.insert(input.client_request_id,(id.clone(),digest));book.requests.insert(id.clone(),request.clone());drop(book);
        let connection=self.connection.clone();let actual=request.clone();let all_handles=self.handles.clone();
        let task=tauri::async_runtime::spawn(async move{
            let mut outgoing=connection.client.request(route.method.clone(),url).headers(headers).header(ACCEPT_ENCODING,"identity").bearer_auth(&connection.bearer);
            if let Some(size)=length{outgoing=outgoing.header(CONTENT_LENGTH,size).body(reqwest::Body::wrap_stream(BodyStream{receiver,timer:Box::pin(tokio::time::sleep(IDLE)),ended:false}));}
            let result=outgoing.send().await;
            match result{
                Err(_)=>{actual.head.send_replace(Some(Err(error("native_http_unknown","head",true))));},
                Ok(response)=>{
                    let status=response.status().as_u16();if status==401{connection.invalidate();}
                    if response.headers().get("content-encoding").is_some_and(|v|v.as_bytes()!=b"identity"){
                        actual.head.send_replace(Some(Err(error("native_content_encoding_unsupported","head",true))));return;
                    }
                    let mut visible=BTreeMap::new();
                    for name in &route.response_headers{
                        if let Some(value)=response.headers().get(name){match value.to_str(){Ok(text)=>{visible.insert(name.clone(),text.to_owned());},Err(_)=>{actual.head.send_replace(Some(Err(error("native_response_header_invalid","head",true))));return;}}}
                    }
                    let head=Head{status,headers:visible,body_kind:if [204,205,304].contains(&status)||route.method==reqwest::Method::HEAD{"none"}else{"bytes"},content_length:response.content_length().map(|n|n.to_string())};
                    {let mut read=actual.read.lock().await;read.response=Some(StreamReader::new(HttpStream{inner:Box::pin(response.bytes_stream())}));}
                    actual.head.send_replace(Some(Ok(head)));
                    // Publish early refusal before touching a currently in-flight upload lock.
                    if let Ok(mut upload)=actual.upload.try_lock(){upload.sender.take();}
                    if status==401{
                        let others=all_handles.lock().map(|book|book.requests.values().filter(|r|r.id!=actual.id).cloned().collect::<Vec<_>>()).unwrap_or_default();
                        for other in others{Self::close_request(other).await;}
                    }
                }
            }
        });
        if let Ok(mut handle)=request.task.lock(){*handle=Some(task.inner().abort_handle());}
        if length.is_none(){Self::head_deadline(request);}
        Ok(id)
    }
    pub async fn upload(&self,id:&str,generation:&str,sequence:&str,raw:&[u8])->Result<UploadAck,TransportError>{
        let request=self.get(id,generation)?;let frame=wire::decode(raw).map_err(|c|error(c,"upload",true))?;
        if frame.eof{return Err(error("native_upload_frame_invalid","upload",true));}
        let seq=wire::decimal(sequence).map_err(|c|error(c,"upload",true))?;
        let digest:[u8;32]=Sha256::digest(raw).into();
        let mut state=request.upload.try_lock().map_err(|_|error("native_upload_busy","upload",true))?;
        if let Some((previous,offset,hash,ack))=&state.last{if *previous==seq{return if *offset==frame.offset&&hash==&digest{Ok(ack.clone())}else{Err(error("native_upload_replay_conflict","upload",true))};}}
        if request.head.borrow().is_some(){return Err(error("native_upload_closed","upload",true));}
        if state.finished||seq!=state.seq||frame.offset!=state.offset||state.length.is_none_or(|length|frame.next>length){return Err(error("native_upload_sequence_invalid","upload",true));}
        let sender=state.sender.as_ref().ok_or(error("native_upload_closed","upload",true))?.clone();
        Self::cancelable(&request,tokio::time::timeout(IDLE,sender.send(Ok(Bytes::copy_from_slice(frame.payload))))).await?.map_err(|_|error("native_upload_timeout","upload",true))?.map_err(|_|error("native_upload_closed","upload",true))?;
        let ack=UploadAck{seq:seq.to_string(),next_offset:frame.next.to_string()};state.offset=frame.next;state.seq=state.seq.checked_add(1).ok_or(error("native_sequence_exhausted","upload",true))?;
        state.last=Some((seq,frame.offset,digest,ack.clone()));Ok(ack)
    }
    pub async fn finish(&self,id:&str,generation:&str,sequence:&str,total:&str)->Result<(),TransportError>{
        let request=self.get(id,generation)?;
        let(seq,size)=(wire::decimal(sequence).map_err(|c|error(c,"upload",true))?,wire::decimal(total).map_err(|c|error(c,"upload",true))?);
        let mut state=request.upload.try_lock().map_err(|_|error("native_upload_busy","upload",true))?;
        if seq!=state.seq||size!=state.offset||state.length!=Some(size){return Err(error("native_upload_length_invalid","upload",true));}
        let was_finished=state.finished;state.finished=true;state.sender.take();drop(state);
        if !was_finished{Self::head_deadline(request);}Ok(())
    }
    pub async fn head(&self,id:&str,generation:&str)->Result<Head,TransportError>{
        let request=self.get(id,generation)?;let mut receiver=request.head_rx.clone();
        loop{if let Some(head)=receiver.borrow_and_update().clone(){return head;}receiver.changed().await.map_err(|_|error("native_request_closed","head",true))?;}
    }
    pub async fn read(&self,id:&str,generation:&str,sequence:&str,offset:&str,maximum:usize)->Result<Vec<u8>,TransportError>{
        let request=self.get(id,generation)?;if maximum==0||maximum>wire::CHUNK{return Err(error("native_frame_limit","read",true));}
        let(seq,position)=(wire::decimal(sequence).map_err(|c|error(c,"read",true))?,wire::decimal(offset).map_err(|c|error(c,"read",true))?);
        let mut state=request.read.try_lock().map_err(|_|error("native_read_busy","read",true))?;
        if state.consumer==Consumer::Save{return Err(error("native_response_single_consumer","read",true));}state.consumer=Consumer::Stream;
        if let Some((last_seq,last_offset,frame))=&state.last{if *last_seq==seq{return if *last_offset==position{Ok(frame.clone())}else{Err(error("native_read_replay_conflict","read",true))};}}
        if seq!=state.seq||position!=state.offset||state.eof{return Err(error("native_read_sequence_invalid","read",true));}
        // A new sequence acknowledges the previous frame before allocating the next.
        state.last.take();
        let mut payload=vec![0;maximum];
        let reader=state.response.as_mut().ok_or(error("native_response_not_ready","read",true))?;
        let count=Self::cancelable(&request,tokio::time::timeout(IDLE,reader.read(&mut payload))).await?.map_err(|_|error("native_read_timeout","read",true))?.map_err(|_|error("native_body_incomplete","read",true))?;
        payload.truncate(count);state.eof=count==0;
        let frame=wire::encode(position,&payload,state.eof).map_err(|c|error(c,"read",true))?;
        drop(payload);
        state.offset=state.offset.checked_add(count as u64).ok_or(error("native_offset_invalid","read",true))?;state.seq=state.seq.checked_add(1).ok_or(error("native_sequence_exhausted","read",true))?;
        state.last=Some((seq,position,frame.clone()));Ok(frame)
    }
    pub async fn release(&self,id:&str,generation:&str)->Result<(),TransportError>{
        let request={let mut book=self.handles.lock().map_err(|_|error("native_state_unavailable","cleanup",true))?;
            if let Some(request)=book.requests.get(id){if request.generation!=generation{return Err(error("native_generation_invalid","cleanup",true));}}
            book.requests.remove(id)};
        if let Some(request)=request{Self::close_request(request).await;}Ok(())
    }
    pub async fn invalidate_generation(&self,generation:&str){let ids=self.handles.lock().map(|book|book.requests.values().filter(|r|r.generation==generation).map(|r|r.id.clone()).collect::<Vec<_>>()).unwrap_or_default();for id in ids{let _=self.release(&id,generation).await;}}
    pub async fn stop(&self){
        self.connection.invalidate();
        let requests=self.handles.lock().map(|mut book|std::mem::take(&mut book.requests).into_values().collect::<Vec<_>>()).unwrap_or_default();
        for request in &requests{request.closed.store(true,Ordering::Release);request.cancel.send_replace(true);}
        for request in requests{Self::close_request(request).await;}
    }
    async fn cancelable<T>(request:&Request,future:impl Future<Output=T>)->Result<T,TransportError>{
        let mut cancellation=request.cancel.subscribe();
        if *cancellation.borrow(){return Err(error("native_request_closed","cleanup",true));}
        let mut future=Box::pin(future);let mut canceled=Box::pin(cancellation.changed());
        std::future::poll_fn(move|cx|{
            if canceled.as_mut().poll(cx).is_ready(){return Poll::Ready(Err(error("native_request_closed","cleanup",true)));}
            future.as_mut().poll(cx).map(Ok)
        }).await
    }
    fn head_deadline(request:Arc<Request>){
        tauri::async_runtime::spawn(async move{tokio::time::sleep(IDLE).await;
            if !request.closed.load(Ordering::Acquire)&&request.head.borrow().is_none(){
                request.head.send_replace(Some(Err(error("native_head_timeout","head",true))));
                if let Ok(task)=request.task.lock(){if let Some(task)=task.as_ref(){task.abort();}}
            }
        });
    }
    async fn close_request(request:Arc<Request>){
        request.closed.store(true,Ordering::Release);
        request.cancel.send_replace(true);
        if let Ok(task)=request.task.lock(){if let Some(task)=task.as_ref(){task.abort();}}
        request.head.send_replace(Some(Err(error("native_request_closed","head",true))));
        request.upload.lock().await.sender.take();let mut read=request.read.lock().await;read.response.take();read.last=None;
    }
}
