//! Backend B42's exact independent confirmation wire. No renderer authority.
use std::{sync::{Arc,Mutex}, thread::{self,JoinHandle}, time::{Duration,Instant,SystemTime,UNIX_EPOCH}};
use serde::Deserialize;
use serde_json::{json,Value};
use sha2::{Digest,Sha256};
use crate::{owner_setup::{SetupAttempt,FRAME_LIMIT},native_installation::NativeInstallationGuards,
    platform::OwnedProcess,resource_authority::{OwnerSetupPipe,ProcessIdentity,assert_registered_identity}};
const WIRE:&str="native-owner-setup-confirmation-v1";
#[derive(Deserialize)]#[serde(tag="method",deny_unknown_fields)]
enum Request {
    #[serde(rename="bind")] Bind{wire:String,session:String,seq:u64,setup_id:String,intent_sha256:String},
    #[serde(rename="present")] Present{wire:String,session:String,seq:u64,setup_id:String,intent_sha256:String,intent:Value},
    #[serde(rename="take")] Take{wire:String,session:String,seq:u64,setup_id:String,intent_sha256:String,challenge_id:String},
    #[serde(rename="assert_current")] Current{wire:String,session:String,seq:u64,setup_id:String,intent_sha256:String,challenge_id:String,confirmation_id:String},
    #[serde(rename="close")] Close{wire:String,session:String,seq:u64,setup_id:String,intent_sha256:String,confirmation_id:Option<String>},
}
struct OriginalSource {
    process:Arc<Mutex<OwnedProcess>>,child:ProcessIdentity,host:ProcessIdentity,
    installation:Arc<NativeInstallationGuards>,directory:Arc<crate::owner_setup_directory::OwnerDirectory>,attempt:Arc<SetupAttempt>,os_session:u32,
}
impl OriginalSource {
    fn assert_current(&self)->Result<(),&'static str>{
        if self.attempt.cancelled.load(std::sync::atomic::Ordering::Acquire){return Err("declined");}
        assert_registered_identity(&self.process,&self.child)?;
        self.directory.assert_current()?;
        self.installation.image_is_current_process()?;
        let observation=self.installation.observe()?;self.installation.assert_current(&observation)?;
        let actual=crate::resource_authority::current_identity()?;
        if (actual.pid,actual.creation_filetime,actual.sid.as_str(),actual.image_sha256.as_str())
            !=(self.host.pid,self.host.creation_filetime,self.host.sid.as_str(),self.host.image_sha256.as_str()){return Err("owner_changed");}
        let mut child_session=0;
        if unsafe{windows_sys::Win32::System::RemoteDesktop::ProcessIdToSessionId(self.child.pid,&mut child_session)}==0
            ||child_session!=self.os_session||crate::owner_setup_window::interactive_session()?!=self.os_session{return Err("owner_changed");}Ok(())
    }
}
struct NativeConfirmation { confirmation_id:String, accepted:Instant }
struct Challenge {
    id:String,intent:Value,deadline:Instant,source:Arc<OriginalSource>,
    dialog:Option<JoinHandle<()>>,result:Arc<Mutex<Option<Result<NativeConfirmation,&'static str>>>>,
    confirmed:Option<NativeConfirmation>,taken:bool,
}
impl Drop for Challenge { fn drop(&mut self){self.source.attempt.cancelled.store(true,std::sync::atomic::Ordering::Release);if let Some(thread)=self.dialog.take(){let _=thread.join();}} }
pub(crate) struct PendingSetupChannel {
    pipe:OwnerSetupPipe,installation:Arc<NativeInstallationGuards>,directory:Arc<crate::owner_setup_directory::OwnerDirectory>,attempt:Arc<SetupAttempt>,parent:usize,goal:Value,
}
impl PendingSetupChannel {
    pub(crate) fn create(installation:Arc<NativeInstallationGuards>,directory:Arc<crate::owner_setup_directory::OwnerDirectory>,instance:&str,attempt:Arc<SetupAttempt>,parent:usize,goal:Value)->Result<Self,&'static str>{
        Ok(Self{pipe:OwnerSetupPipe::create(installation.clone(),instance)?,installation,directory,attempt,parent,goal})
    }
    pub(crate) fn locator(&self)->&crate::resource_authority::ChildLocator{&self.pipe.locator}
    pub(crate) fn start(self)->Result<(std::sync::mpsc::SyncSender<Arc<Mutex<OwnedProcess>>>,JoinHandle<Result<(),&'static str>>),&'static str>{
        let(sender,receiver)=std::sync::mpsc::sync_channel(1);
        let handle=thread::Builder::new().name("native-owner-setup".into()).spawn(move||self.serve(receiver)).map_err(|_|"owner_setup_thread_failed")?;Ok((sender,handle))
    }
    fn serve(self,receiver:std::sync::mpsc::Receiver<Arc<Mutex<OwnedProcess>>>)->Result<(),&'static str>{
        let deadline=Instant::now()+Duration::from_secs(20);
        let process=receiver.recv_timeout(Duration::from_secs(20)).map_err(|_|"owner_setup_child_missing")?;
        let result=(||{let child=self.pipe.connect(&process,deadline)?;
            let os_session=crate::owner_setup_window::interactive_session()?;
            let source=Arc::new(OriginalSource{process:process.clone(),child,host:self.pipe.locator.server.clone(),installation:self.installation.clone(),directory:self.directory.clone(),attempt:self.attempt.clone(),os_session});
            source.assert_current()?;self.calls(&process,source)})();
        self.pipe.disconnect();
        // Window/ACK/EOF never prove child/Job terminal. Original installation
        // and actual process ownership survive every ambiguous exchange.
        loop{let terminal=process.lock().is_ok_and(|owned|owned.wait_exit(20).is_ok_and(|code|code.is_some())&&owned.job_pids().is_ok_and(|pids|pids.is_empty()));if terminal{break;}thread::sleep(Duration::from_millis(20));}result
    }
    fn calls(&self,process:&Arc<Mutex<OwnedProcess>>,source:Arc<OriginalSource>)->Result<(),&'static str>{
        let mut expected=0u64;let mut binding:Option<(String,String)>=None;let mut challenge:Option<Challenge>=None;
        loop{
            self.pipe.assert_peer(process)?;
            let deadline=Instant::now()+Duration::from_secs(10);let bytes=self.pipe.receive(deadline)?;
            let raw:Value=serde_json::from_slice(&bytes).map_err(|_|"owner_setup_frame_invalid")?;
            if crate::native_installation::canonical(&raw)?!=bytes{return Err("owner_setup_frame_noncanonical");}
            let request:Request=serde_json::from_value(raw).map_err(|_|"owner_setup_frame_invalid")?;
            let(wire,session,seq,setup,sha)=match &request{Request::Bind{wire,session,seq,setup_id,intent_sha256}|Request::Present{wire,session,seq,setup_id,intent_sha256,..}|Request::Take{wire,session,seq,setup_id,intent_sha256,..}|Request::Current{wire,session,seq,setup_id,intent_sha256,..}|Request::Close{wire,session,seq,setup_id,intent_sha256,..}=>(wire.clone(),session.clone(),*seq,setup_id.clone(),intent_sha256.clone())};
            if wire!=WIRE||session!=self.pipe.locator.session||seq!=expected||setup.is_empty()||setup.len()>128||!crate::load_policy::digest_valid(&sha){return Err("owner_setup_sequence_invalid");}
            if binding.as_ref().is_some_and(|(id,digest)|id!=&setup||digest!=&sha){return Err("owner_setup_intent_changed");}
            let mut reply=json!({"wire":WIRE,"session":session,"seq":seq,"status":200,"code":"bound","setup_id":setup,"intent_sha256":sha,"challenge_id":null,"remaining_us":0,"intent":null,"confirmation_source":null});
            let mut closing=false;
            match request {
                Request::Bind{setup_id,intent_sha256,..}=>{if seq!=0||binding.is_some(){return Err("owner_setup_bind_replay");}binding=Some((setup_id,intent_sha256));}
                Request::Present{intent,..}=>{
                    if binding.is_none()||challenge.is_some(){return Err("owner_setup_present_replay");}
                    let body=crate::native_installation::canonical(&intent)?;
                    if body.len()>FRAME_LIMIT-16384||format!("{:x}",Sha256::digest(&body))!=sha||intent["format"]!="owner-setup-intent-v1"
                        ||intent["setup_id"]!=setup||intent["instance_id"]!=self.pipe.locator.instance_id||intent["goal"]!=self.goal
                        ||intent["directory"]["os_subject"]!=source.child.sid
                        ||intent["expected_host_sha256"]!=source.host.image_sha256
                        ||intent["expected_host_image"].as_str()!=Some(self.installation.inputs.installed_native_image.as_str())
                        ||intent["external_receipt_path"].as_str()!=Some(crate::load_policy::text(self.installation.receipt_path())?.as_str())
                        ||crate::native_installation::canonical(&intent["installation"])?!=crate::native_installation::canonical(&serde_json::to_value(&self.installation.inputs).map_err(|_|"owner_setup_installation_invalid")?)? {return Err("owner_setup_intent_changed");}
                    source.assert_current()?;
                    source.directory.assert_intent(intent["directory"]["path"].as_str().ok_or("owner_setup_directory_invalid")?,intent["directory"]["os_subject"].as_str().ok_or("owner_setup_directory_invalid")?,intent["directory"]["administrator_id"].as_str().ok_or("owner_setup_directory_invalid")?)?;
                    let expires=intent["expires_at_us"].as_u64().ok_or("owner_setup_expiry_invalid")?;
                    let now=SystemTime::now().duration_since(UNIX_EPOCH).map_err(|_|"owner_setup_clock_invalid")?.as_micros()as u64;
                    let remaining=expires.checked_sub(now).ok_or("owner_setup_expired")?.min(600_000_000);
                    if remaining==0{return Err("owner_setup_expired");}
                    let id=crate::resource_authority::private_startup_id()?;
                    self.attempt.prepared(intent["goal"]["name"].as_str().ok_or("owner_setup_goal_invalid")?)?;
                    challenge=Some(Challenge{id,intent,deadline:Instant::now()+Duration::from_micros(remaining),source:source.clone(),dialog:None,result:Arc::new(Mutex::new(None)),confirmed:None,taken:false});
                    reply["status"]=json!(202);reply["code"]=json!("pending");
                }
                Request::Take{challenge_id,..}=>{
                    let current=challenge.as_mut().ok_or("owner_setup_present_required")?;
                    if current.id!=challenge_id||current.taken{return Err("owner_setup_take_replay");}
                    self.start_dialog(current)?;
                    let result=current.result.lock().map_err(|_|"owner_setup_dialog_unknown")?.take();
                    if let Some(result)=result{current.confirmed=Some(result?);}
                    if current.confirmed.is_some(){current.taken=true;self.attempt.applying();self.confirmed_reply(current,&mut reply)?;reply["code"]=json!("confirmed");}
                    else{reply["status"]=json!(202);reply["code"]=json!("pending");}
                }
                Request::Current{challenge_id,confirmation_id,..}=>{
                    let current=challenge.as_ref().ok_or("owner_setup_confirmation_missing")?;
                    if current.id!=challenge_id||!current.taken||current.confirmed.as_ref().is_none_or(|original|original.confirmation_id!=confirmation_id){return Err("owner_setup_confirmation_foreign");}
                    self.confirmed_reply(current,&mut reply)?;reply["code"]=json!("current");
                }
                Request::Close{confirmation_id,..}=>{
                    if binding.is_none()||confirmation_id.as_ref().is_some_and(|id|challenge.as_ref().and_then(|item|item.confirmed.as_ref()).is_none_or(|item|&item.confirmation_id!=id)){return Err("owner_setup_close_foreign");}
                    reply["code"]=json!("view_closed_native_ownership_retained");closing=true;
                }
            }
            if !closing{if let Some(current)=&challenge{if Instant::now()>=current.deadline&&current.confirmed.is_none(){return Err("owner_setup_expired");}reply["challenge_id"]=json!(current.id);if reply["remaining_us"]==0{reply["remaining_us"]=json!(current.deadline.saturating_duration_since(Instant::now()).as_micros()as u64);}}}
            self.pipe.assert_peer(process)?;source.assert_current()?;self.pipe.send(&reply,deadline)?;
            expected=expected.checked_add(1).ok_or("owner_setup_sequence_exhausted")?;
            if closing{return Ok(());}
        }
    }
    fn start_dialog(&self,challenge:&mut Challenge)->Result<(),&'static str>{
        if challenge.dialog.is_some()||!self.attempt.wants_present(){return Ok(());}
        let source=challenge.source.clone();let result=challenge.result.clone();let deadline=challenge.deadline;
        let details=human_details(&challenge.intent)?;
        let body=crate::native_installation::canonical(&challenge.intent)?;
        let digest=format!("{:x}",Sha256::digest(body));
        let text=format!("AUTHORIZE {} setup {}",self.pipe.locator.instance_id,&digest[..16]);let parent=self.parent;
        challenge.dialog=Some(thread::Builder::new().name("native-setup-dialog".into()).spawn(move||{
            let observed=crate::owner_setup_window::show(parent,&details,&text,deadline,&||source.assert_current())
                .and_then(|input|Ok(NativeConfirmation{confirmation_id:crate::resource_authority::private_startup_id()?,accepted:input.accepted_at}));
            if let Ok(mut value)=result.lock(){*value=Some(observed);}
        }).map_err(|_|"owner_setup_dialog_thread_failed")?);Ok(())
    }
    fn confirmed_reply(&self,current:&Challenge,reply:&mut Value)->Result<(),&'static str>{
        let original=current.confirmed.as_ref().ok_or("owner_setup_confirmation_missing")?;
        let deadline=(original.accepted+Duration::from_secs(120)).min(current.deadline);
        if Instant::now()>=deadline{return Err("owner_setup_confirmation_expired");}current.source.assert_current()?;
        reply["intent"]=current.intent.clone();reply["remaining_us"]=json!(deadline.saturating_duration_since(Instant::now()).as_micros()as u64);
        let source=&current.source;reply["confirmation_source"]=json!({"authentication_source":"native_owner_session","session_id":self.pipe.locator.session,
            "challenge_id":current.id,"confirmation_id":original.confirmation_id,"os_subject":source.child.sid,
            "gui_session_id":format!("windows-session-{}",source.os_session),"document_generation":self.attempt.document_generation,
            "host_pid":source.host.pid,"host_creation_filetime":source.host.creation_filetime,"child_pid":source.child.pid,"child_creation_filetime":source.child.creation_filetime,
            "expected_host_sha256":source.host.image_sha256});Ok(())
    }
}
fn human_details(intent:&Value)->Result<String,&'static str>{
    let mut text=format!("项目：{}\r\n创作目标：{}\r\n\r\n本次会保存当前创作草稿，设置本地创作范围，再继续同一请求。确认本身不会购买服务或生成素材。\r\n\r\n完整目标与输入：\r\n{}\r\n\r\n",
        intent["goal"]["name"].as_str().ok_or("owner_setup_goal_invalid")?,intent["goal"]["goal"].as_str().unwrap_or("见下面完整目标"),serde_json::to_string_pretty(&intent["goal"]).map_err(|_|"owner_setup_goal_invalid")?);
    let steps=intent["steps"].as_array().ok_or("owner_setup_steps_invalid")?;
    for step in steps{match step["type"].as_str(){
        Some("owner_initialize")=>text.push_str(&format!("初次本地设置：仅当前项目。有效期（UTC微秒）：{}\r\n",step["expires_at_us"])),
        Some("execution_install")=>text.push_str(&format!("可执行创作范围、预算和有效期：\r\n{}\r\n",serde_json::to_string_pretty(&step["proposal"]["registrations"]).map_err(|_|"owner_setup_steps_invalid")?)),
        Some("creation_install")=>text.push_str(&format!("后续项目数量上限：{}；同时制作上限：{}\r\n可用入口：{}\r\n完整资源、费用、素材权利和操作范围：\r\n{}\r\n",step["max_created_projects"],step["max_active_productions"],step["allowed_entries"],serde_json::to_string_pretty(&step["template"]).map_err(|_|"owner_setup_steps_invalid")?)),
        Some("continue_goal")=>text.push_str("继续原始项目草稿和原始创作请求，不另建第二项目。\r\n"),_=>return Err("owner_setup_steps_invalid")}}
    text.push_str(&format!("\r\n本次确认有效期（UTC微秒）：{}\r\n",intent["expires_at_us"]));Ok(text)
}
