//! Actual v2 session producer. IDs refer to this thread's original borrowed
//! installation/Registry observations; JSON cannot construct those members.
use std::{collections::HashMap,sync::{Arc,Mutex,mpsc},thread::{self,JoinHandle},time::{Duration,Instant}};
use serde::Deserialize;
use serde_json::{json,Value};
use crate::{native_installation::{canonical,InstallationObservation},platform::OwnedProcess,
    qualification_registry::{QualificationRegistry,QualifiedObservation,QualifiedWriterLease},resource_authority::{ChildLocator,FactsContext,OwnerSetupPipe}};
pub(crate) const WIRE:&str="held-resource-authority-v2-candidate";
#[derive(Deserialize)]#[serde(tag="method",deny_unknown_fields)]
enum Request{
    #[serde(rename="bind")]Bind{wire:String,session:String,seq:u64,instance_id:String,role:String},
    #[serde(rename="observe")]Observe{wire:String,session:String,seq:u64},
    #[serde(rename="assert_current")]Assert{wire:String,session:String,seq:u64,observation_id:String},
    #[serde(rename="begin_writer_lease")]Begin{wire:String,session:String,seq:u64,observation_id:String},
    #[serde(rename="end_writer_lease")]End{wire:String,session:String,seq:u64,lease_id:String},
}
struct Observed<'scope>{files:InstallationObservation<'scope>,qualified:QualifiedObservation<'scope>}
pub(crate) struct PendingQualifiedAuthority{pipe:OwnerSetupPipe,registry:Arc<QualificationRegistry>,context:FactsContext}
pub(crate) struct QualifiedRegistration{sender:Option<mpsc::SyncSender<Arc<Mutex<OwnedProcess>>>>}
impl QualifiedRegistration{pub(crate) fn register(mut self,process:Arc<Mutex<OwnedProcess>>)->Result<(),&'static str>{self.sender.take().ok_or("authority_registration_consumed")?.send(process).map_err(|_|"authority_registration_failed")}}
impl PendingQualifiedAuthority{
    pub(crate) fn create_qualified(registry:Arc<QualificationRegistry>,child_image_relative:&str,context:FactsContext)->Result<Self,&'static str>{
        context.validate()?;
        if context.instance_id!=registry.instance()||(&context.registration_sha256,&context.resource_manifest_sha256,&context.runtime_manifest_sha256)
            !=(&registry.installation.inputs.registration_sha256,&registry.installation.inputs.resource_manifest_sha256,&registry.installation.inputs.runtime_manifest_sha256){return Err("authority_installation_identity_mismatch");}
        registry.assert_role(&context.role,child_image_relative,Instant::now()+Duration::from_secs(10))?;
        let pipe=OwnerSetupPipe::create_qualified(registry.installation.clone(),&context.instance_id,&context.role,child_image_relative)?;
        Ok(Self{pipe,registry,context})
    }
    pub(crate) fn locator(&self)->&ChildLocator{&self.pipe.locator}
    pub(crate) fn start(self)->Result<(QualifiedRegistration,JoinHandle<Result<(),&'static str>>),&'static str>{
        let(sender,receiver)=mpsc::sync_channel(1);
        let session=thread::Builder::new().name("qualified-resource-authority".into()).spawn(move||self.serve(receiver)).map_err(|_|"authority_thread_failed")?;
        Ok((QualifiedRegistration{sender:Some(sender)},session))
    }
    fn response(&self,seq:u64,status:u16,code:&str)->Value{
        json!({"wire":WIRE,"session":self.pipe.locator.session,"seq":seq,"status":status,"code":code,
            "observation_id":null,"observed_at_us":null,"files":[],"qualification":"not_ready",
            "registration_sha256":self.context.registration_sha256,"resource_manifest_sha256":self.context.resource_manifest_sha256,
            "runtime_manifest_sha256":self.context.runtime_manifest_sha256,"qualification_binding":null,"lease_binding":null})
    }
    fn calls(&self,process:&Arc<Mutex<OwnedProcess>>)->Result<(),&'static str>{
        let mut observed:HashMap<String,Observed<'_>>=HashMap::new();let mut expected=0u64;let mut bound=false;
        // RwLockReadGuard is never sent to another thread. Its custom Drop
        // retains the original process/Job on every unknown/unwind path.
        let mut lease:Option<QualifiedWriterLease<'_>>=None;
        loop{
            let deadline=if expected==0{Instant::now()+Duration::from_secs(10)}else{match self.pipe.wait_request(process)?{Some(deadline)=>deadline,None=>return Ok(())}};
            self.pipe.assert_peer(process)?;
            let raw=self.pipe.receive(deadline)?;
            let request:Request=serde_json::from_slice(&raw).map_err(|_|"authority_frame_invalid")?;
            let value:Value=serde_json::from_slice(&raw).map_err(|_|"authority_frame_invalid")?;
            if canonical(&value)?!=raw{return Err("authority_frame_invalid");}
            let(wire,session,seq)=match &request{Request::Bind{wire,session,seq,..}|Request::Observe{wire,session,seq}|Request::Assert{wire,session,seq,..}|Request::Begin{wire,session,seq,..}|Request::End{wire,session,seq,..}=>(wire,session,*seq)};
            if wire!=WIRE||session!=&self.pipe.locator.session||seq!=expected{return Err("authority_sequence_or_context");}expected=expected.checked_add(1).ok_or("authority_sequence_exhausted")?;
            let mut response=match request{
                Request::Bind{instance_id,role,..}=>{if bound||seq!=0||instance_id!=self.context.instance_id||role!=self.context.role{return Err("authority_bind_invalid");}bound=true;self.response(seq,200,"bound_facts_only")},
                Request::Observe{..}=>{
                    if !bound||lease.is_some()||observed.len()>=64{return Err("authority_observation_scope_invalid");}
                    let files=self.registry.installation.observe()?;self.registry.installation.assert_current(&files)?;
                    let qualified=match self.registry.observe(deadline){Ok(value)=>value,Err(_)=>{self.pipe.send(&self.response(seq,503,"qualification_unavailable"),deadline)?;continue;}};
                    let id=crate::resource_authority::private_startup_id()?;let mut response=self.response(seq,200,"observed_qualified");
                    response["qualification"]="qualified".into();response["qualification_binding"]=self.registry.binding(&qualified,deadline)?;
                    response["observation_id"]=id.clone().into();response["observed_at_us"]=files.observed_at_us().into();response["files"]=serde_json::to_value(files.payload_files()).map_err(|_|"authority_frame_invalid")?;
                    observed.insert(id,Observed{files,qualified});response
                },
                Request::Assert{observation_id,..}=>{
                    if !bound||lease.is_some(){return Err("authority_assert_scope_invalid");}
                    if let Some(observation)=observed.get(&observation_id){
                        self.registry.installation.assert_current(&observation.files)?;self.registry.assert_observation(&observation.qualified,deadline)?;
                        let mut response=self.response(seq,200,"current_qualified");response["qualification"]="qualified".into();response["qualification_binding"]=self.registry.binding(&observation.qualified,deadline)?;response
                    }else{self.response(seq,409,"observation_unknown_or_foreign")}
                },
                Request::Begin{observation_id,..}=>{
                    if !bound{return Err("authority_bind_required");}
                    if lease.is_some(){self.response(seq,409,"lease_conflict")}
                    else if let Some(observation)=observed.get(&observation_id){
                        self.registry.installation.assert_current(&observation.files)?;
                        let retained=self.registry.begin_writer_lease(&observation.qualified,&observation_id,process.clone(),deadline)?;
                        let mut response=self.response(seq,200,"writer_lease_acquired");response["qualification"]="qualified".into();response["qualification_binding"]=retained.qualification_binding()?;response["lease_binding"]=retained.binding()?;
                        lease=Some(retained);response
                    }else{self.response(seq,409,"observation_unknown_or_foreign")}
                },
                Request::End{lease_id,..}=>{
                    if !bound{return Err("authority_bind_required");}
                    if lease.as_ref().is_none_or(|held|held.id()!=lease_id){self.response(seq,409,"lease_conflict")}
                    else{
                        let held=lease.take().ok_or("qualification_lease_missing")?;let qualification=held.qualification_binding()?;
                        // end consumes and actually drops the read guard before
                        // ACK. An ACK timeout cannot fabricate another lease.
                        let binding=held.end()?;let mut response=self.response(seq,200,"writer_lease_released");response["qualification"]="qualified".into();response["qualification_binding"]=qualification;response["lease_binding"]=binding;response
                    }
                },
            };
            self.pipe.assert_peer(process)?;
            // The exact 14-field reply cannot grant qualified without the
            // current original binding, including all five lease fields.
            if response["qualification_binding"].is_null(){response["qualification"]="not_ready".into();}
            self.pipe.send(&response,deadline)?;
        }
    }
    fn serve(self,receiver:mpsc::Receiver<Arc<Mutex<OwnedProcess>>>)->Result<(),&'static str>{
        let process=receiver.recv_timeout(Duration::from_secs(20)).map_err(|_|"authority_registration_missing")?;
        let result=(||{self.pipe.connect(&process,Instant::now()+Duration::from_secs(20))?;self.calls(&process)})();self.pipe.disconnect();
        loop{let owned=process.lock().unwrap_or_else(|poisoned|poisoned.into_inner());let terminal=owned.wait_exit(20).is_ok_and(|exit|exit.is_some())&&owned.job_pids().is_ok_and(|pids|pids.is_empty());drop(owned);if terminal{break;}thread::sleep(Duration::from_millis(20));}result
    }
}
