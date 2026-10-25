//! Trusted native-only held-resource channel. No renderer command or credential.
//! Facts-only observations never construct InstalledProductionEvidence.
use std::{collections::HashMap,ffi::{OsStr,OsString},fs::File,io::Read,mem::{size_of,zeroed},
    os::windows::ffi::OsStrExt,path::PathBuf,ptr::{null,null_mut},sync::{Arc,Mutex,mpsc,atomic::{AtomicU32,Ordering}},
    thread::{self,JoinHandle},time::{Duration,Instant}};
use serde::{Deserialize,Serialize};
use sha2::{Digest,Sha256};
use crate::{platform::OwnedProcess,resource_pins::{ResourcePins,HeldFileObservation,PinnedFile}};
use windows_sys::Win32::{
    Foundation::{CloseHandle,GetLastError,LocalFree,FILETIME,HANDLE,INVALID_HANDLE_VALUE,
        ERROR_IO_PENDING,ERROR_IO_INCOMPLETE,ERROR_PIPE_CONNECTED,WAIT_OBJECT_0,WAIT_TIMEOUT,GENERIC_READ,GENERIC_WRITE},
    Security::{Authorization::{ConvertSidToStringSidW,ConvertStringSecurityDescriptorToSecurityDescriptorW,SDDL_REVISION_1},
        GetTokenInformation,TokenUser,TOKEN_QUERY,TOKEN_USER,SECURITY_ATTRIBUTES},
    Storage::FileSystem::{CreateFileW,ReadFile,WriteFile,FILE_FLAG_OVERLAPPED,FILE_FLAG_FIRST_PIPE_INSTANCE,
        OPEN_EXISTING,PIPE_ACCESS_DUPLEX},
    System::{IO::{CancelIoEx,GetOverlappedResult,OVERLAPPED},
        Pipes::{ConnectNamedPipe,CreateNamedPipeW,DisconnectNamedPipe,GetNamedPipeClientProcessId,
            GetNamedPipeServerProcessId,PeekNamedPipe,PIPE_TYPE_BYTE,PIPE_READMODE_BYTE,PIPE_WAIT,PIPE_REJECT_REMOTE_CLIENTS},
        Threading::{CreateEventW,GetCurrentProcess,GetCurrentProcessId,GetProcessTimes,OpenProcess,
            OpenProcessToken,QueryFullProcessImageNameW,WaitForSingleObject,PROCESS_QUERY_LIMITED_INFORMATION},
        Diagnostics::ToolHelp::{CreateToolhelp32Snapshot,Process32FirstW,Process32NextW,PROCESSENTRY32W,TH32CS_SNAPPROCESS}},
};

pub const WIRE:&str="held-resource-authority-v1-candidate";
pub const MAX_FRAME:usize=32*1024*1024;
const LAUNCH_DEADLINE:Duration=Duration::from_secs(20);
const CALL_DEADLINE:Duration=Duration::from_secs(10);
struct Handle(HANDLE);
unsafe impl Send for Handle{}
impl Drop for Handle{fn drop(&mut self){if !self.0.is_null()&&self.0!=INVALID_HANDLE_VALUE{unsafe{CloseHandle(self.0);}}}}
fn wide(value:&OsStr)->Result<Vec<u16>,&'static str>{let mut out=value.encode_wide().collect::<Vec<_>>();if out.contains(&0){return Err("authority_string_invalid");}out.push(0);Ok(out)}
fn random_id()->Result<String,&'static str>{
    use windows_sys::Win32::Security::Cryptography::{BCryptGenRandom,BCRYPT_USE_SYSTEM_PREFERRED_RNG};
    let mut bytes=[0u8;24];if unsafe{BCryptGenRandom(null_mut(),bytes.as_mut_ptr(),bytes.len()as u32,BCRYPT_USE_SYSTEM_PREFERRED_RNG)}<0{return Err("authority_random_failed");}
    Ok(bytes.iter().map(|value|format!("{value:02x}")).collect())
}
pub(crate) fn private_startup_id()->Result<String,&'static str>{random_id()}
#[derive(Clone,Debug,Serialize,Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ProcessIdentity {pub pid:u32,pub creation_filetime:u64,pub sid:String,pub image:PathBuf,pub image_sha256:String}
fn identity(handle:HANDLE,pid:u32)->Result<ProcessIdentity,&'static str>{
    let(mut birth,mut end,mut kernel,mut user):(FILETIME,FILETIME,FILETIME,FILETIME)=unsafe{zeroed()};
    if unsafe{GetProcessTimes(handle,&mut birth,&mut end,&mut kernel,&mut user)}==0{return Err("authority_creation_unknown");}
    let mut token=null_mut();if unsafe{OpenProcessToken(handle,TOKEN_QUERY,&mut token)}==0{return Err("authority_sid_unknown");}let token=Handle(token);
    let mut size=0;unsafe{GetTokenInformation(token.0,TokenUser,null_mut(),0,&mut size);}
    if size==0||size>65536{return Err("authority_sid_unknown");}let mut storage=vec![0usize;(size as usize+size_of::<usize>()-1)/size_of::<usize>()];
    if unsafe{GetTokenInformation(token.0,TokenUser,storage.as_mut_ptr()as _,size,&mut size)}==0{return Err("authority_sid_unknown");}
    let user=unsafe{&*(storage.as_ptr()as *const TOKEN_USER)};let mut sid_text=null_mut();
    if unsafe{ConvertSidToStringSidW(user.User.Sid,&mut sid_text)}==0{return Err("authority_sid_unknown");}
    let sid=(||{let mut len=0usize;while len<256&&unsafe{*sid_text.add(len)}!=0{len+=1;}if len==256{return Err("authority_sid_invalid");}String::from_utf16(unsafe{std::slice::from_raw_parts(sid_text,len)}).map_err(|_|"authority_sid_invalid")})();
    unsafe{LocalFree(sid_text as _);}let sid=sid?;
    let mut path=vec![0u16;32768];let mut length=path.len()as u32;
    if unsafe{QueryFullProcessImageNameW(handle,0,path.as_mut_ptr(),&mut length)}==0{return Err("authority_image_unknown");}
    let image=PathBuf::from(String::from_utf16(&path[..length as usize]).map_err(|_|"authority_image_invalid")?).canonicalize().map_err(|_|"authority_image_unknown")?;
    let mut file=File::open(&image).map_err(|_|"authority_image_unknown")?;let mut digest=Sha256::new();let mut buffer=[0;65536];
    loop{let n=file.read(&mut buffer).map_err(|_|"authority_image_unknown")?;if n==0{break;}digest.update(&buffer[..n]);}
    Ok(ProcessIdentity{pid,creation_filetime:((birth.dwHighDateTime as u64)<<32)|birth.dwLowDateTime as u64,sid,image,image_sha256:format!("{:x}",digest.finalize())})
}
pub fn current_identity()->Result<ProcessIdentity,&'static str>{identity(unsafe{GetCurrentProcess()},unsafe{GetCurrentProcessId()})}
pub(crate) fn assert_registered_identity(process:&Arc<Mutex<OwnedProcess>>,expected:&ProcessIdentity)->Result<(),&'static str>{
    let owned=process.lock().map_err(|_|"owner_setup_process_busy")?;
    if !owned.alive(){return Err("owner_setup_child_exited");}
    let actual=identity(owned.authority_peer_handle(expected.pid)?,expected.pid)?;
    if !same_identity(&actual,expected){return Err("owner_setup_peer_changed");}Ok(())
}
fn parent_pid()->Result<u32,&'static str>{
    let snapshot=Handle(unsafe{CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS,0)});if snapshot.0==INVALID_HANDLE_VALUE{return Err("authority_parent_unknown");}
    let mut row:PROCESSENTRY32W=unsafe{zeroed()};row.dwSize=size_of::<PROCESSENTRY32W>()as u32;
    let mut more=unsafe{Process32FirstW(snapshot.0,&mut row)};while more!=0{if row.th32ProcessID==unsafe{GetCurrentProcessId()}{return Ok(row.th32ParentProcessID);}more=unsafe{Process32NextW(snapshot.0,&mut row)};}Err("authority_parent_unknown")
}
fn same_identity(actual:&ProcessIdentity,expected:&ProcessIdentity)->bool{actual.pid==expected.pid&&actual.creation_filetime==expected.creation_filetime&&actual.sid==expected.sid&&actual.image.canonicalize().ok().zip(expected.image.canonicalize().ok()).is_some_and(|(a,b)|a==b)&&actual.image_sha256==expected.image_sha256}
fn local_wire_image(path:&std::path::Path)->Result<PathBuf,&'static str>{
    let text=path.to_str().ok_or("authority_image_invalid")?;
    if let Some(local)=text.strip_prefix("\\\\?\\"){
        let bytes=local.as_bytes();if bytes.len()<3||!bytes[0].is_ascii_alphabetic()||bytes[1]!=b':'||bytes[2]!=b'\\'{return Err("authority_image_invalid");}
        return Ok(PathBuf::from(local));
    }
    if text.starts_with("\\\\")||text.starts_with("//"){return Err("authority_image_invalid");}Ok(path.to_owned())
}

/// Locator/expected peer originate only from native installation/PreparedLaunch.
/// This is not an authenticated descriptor when deserialized from untrusted JSON.
#[derive(Clone,Serialize,Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ChildLocator {pub pipe:String,pub session:String,pub instance_id:String,pub role:String,pub server:ProcessIdentity}
#[derive(Clone)]
pub struct FactsContext {pub instance_id:String,pub role:String,pub registration_sha256:String,pub resource_manifest_sha256:String,pub runtime_manifest_sha256:String}
impl FactsContext {pub(crate) fn validate(&self)->Result<(),&'static str>{
    if self.instance_id.is_empty()||self.instance_id.len()>128||!matches!(self.role.as_str(),"api"|"worker"|"mcp"|"asr")||[&self.registration_sha256,&self.resource_manifest_sha256,&self.runtime_manifest_sha256].iter().any(|s|s.len()!=64||!s.bytes().all(|b|b.is_ascii_digit()||(b'a'..=b'f').contains(&b))){return Err("authority_context_invalid");}Ok(())
}}
struct Pipe(Handle);
fn create_pipe(name:&str,sid:&str)->Result<Pipe,&'static str>{
    let name=wide(OsStr::new(name))?;let sddl=wide(OsStr::new(&format!("D:P(A;;GA;;;SY)(A;;GA;;;{sid})")))?;let mut sd=null_mut();
    if unsafe{ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl.as_ptr(),SDDL_REVISION_1,&mut sd,null_mut())}==0{return Err("authority_acl_failed");}
    let attrs=SECURITY_ATTRIBUTES{nLength:size_of::<SECURITY_ATTRIBUTES>()as u32,lpSecurityDescriptor:sd,bInheritHandle:0};
    let raw=unsafe{CreateNamedPipeW(name.as_ptr(),PIPE_ACCESS_DUPLEX|FILE_FLAG_FIRST_PIPE_INSTANCE|FILE_FLAG_OVERLAPPED,PIPE_TYPE_BYTE|PIPE_READMODE_BYTE|PIPE_WAIT|PIPE_REJECT_REMOTE_CLIENTS,1,65536,65536,0,&attrs)};
    unsafe{LocalFree(sd as _);}if raw==INVALID_HANDLE_VALUE{return Err("authority_pipe_create_failed");}Ok(Pipe(Handle(raw)))
}
/// On deadline or observation failure, cancel this exact operation, then retain
/// its OVERLAPPED/event/buffer until the OS reports completion, never UNKNOWN.
fn complete(pipe:HANDLE,overlap:&mut OVERLAPPED,deadline:Instant)->Result<u32,&'static str>{
    let mut sticky=None;let mut cancel_requested=false;
    loop{
        if Instant::now()>=deadline&&sticky.is_none(){sticky=Some("authority_deadline");}
        let mut transferred=0;
        if unsafe{GetOverlappedResult(pipe,overlap,&mut transferred,0)}!=0{
            if Instant::now()>=deadline&&sticky.is_none(){sticky=Some("authority_deadline");}
            return sticky.map_or(Ok(transferred),Err);
        }
        let error=unsafe{GetLastError()};if error!=ERROR_IO_INCOMPLETE{return Err(sticky.unwrap_or("authority_io_failed"));}
        if sticky.is_some()&&!cancel_requested{unsafe{CancelIoEx(pipe,overlap);}cancel_requested=true;}
        match unsafe{WaitForSingleObject(overlap.hEvent,20)}{WAIT_OBJECT_0|WAIT_TIMEOUT=>{},_=>{sticky=Some("authority_io_observation_failed");}}
    }
}
fn overlapped()->Result<(Handle,OVERLAPPED),&'static str>{let event=Handle(unsafe{CreateEventW(null(),1,0,null())});if event.0.is_null(){return Err("authority_event_failed");}let mut operation:OVERLAPPED=unsafe{zeroed()};operation.hEvent=event.0;Ok((event,operation))}
fn check_deadline(deadline:Instant)->Result<(),&'static str>{if Instant::now()>=deadline{Err("authority_deadline")}else{Ok(())}}
impl Pipe {
    fn connect(&self,deadline:Instant)->Result<(),&'static str>{check_deadline(deadline)?;let(_event,mut operation)=overlapped()?;
        if unsafe{ConnectNamedPipe(self.0.0,&mut operation)}!=0{return check_deadline(deadline);}match unsafe{GetLastError()}{ERROR_PIPE_CONNECTED=>check_deadline(deadline),ERROR_IO_PENDING=>{complete(self.0.0,&mut operation,deadline)?;check_deadline(deadline)},_=>Err("authority_connect_failed")}
    }
    fn bytes(&self,data:&mut[u8],write:bool,deadline:Instant)->Result<(),&'static str>{let mut offset=0;
        check_deadline(deadline)?;
        while offset<data.len(){check_deadline(deadline)?;let(_event,mut operation)=overlapped()?;check_deadline(deadline)?;let count=(data.len()-offset).min(65536);let mut transferred=0;
            let ok=unsafe{if write{WriteFile(self.0.0,data[offset..].as_ptr(),count as u32,&mut transferred,&mut operation)}else{ReadFile(self.0.0,data[offset..].as_mut_ptr(),count as u32,&mut transferred,&mut operation)}};
            if ok==0{if unsafe{GetLastError()}!=ERROR_IO_PENDING{return Err("authority_io_failed");}transferred=complete(self.0.0,&mut operation,deadline)?;}
            check_deadline(deadline)?;
            if transferred==0||transferred as usize>count{return Err("authority_io_eof");}offset+=transferred as usize;
        }check_deadline(deadline)
    }
    fn receive(&self,deadline:Instant)->Result<Vec<u8>,&'static str>{check_deadline(deadline)?;let mut prefix=[0u8;4];self.bytes(&mut prefix,false,deadline)?;let size=u32::from_le_bytes(prefix)as usize;if size==0||size>MAX_FRAME{return Err("authority_frame_size");}check_deadline(deadline)?;let mut body=vec![0u8;size];self.bytes(&mut body,false,deadline)?;check_deadline(deadline)?;Ok(body)}
    fn send<T:Serialize>(&self,value:&T,deadline:Instant)->Result<(),&'static str>{check_deadline(deadline)?;let mut body=serde_json::to_vec(value).map_err(|_|"authority_frame_invalid")?;check_deadline(deadline)?;if body.is_empty()||body.len()>MAX_FRAME{return Err("authority_frame_size");}let mut prefix=(body.len()as u32).to_le_bytes();self.bytes(&mut prefix,true,deadline)?;self.bytes(&mut body,true,deadline)?;check_deadline(deadline)}
}
#[derive(Deserialize)]
#[serde(tag="method",deny_unknown_fields)]
enum Request {
    #[serde(rename="bind")] Bind{wire:String,session:String,seq:u64,instance_id:String,role:String},
    #[serde(rename="observe")] Observe{wire:String,session:String,seq:u64},
    #[serde(rename="assert_current")] Assert{wire:String,session:String,seq:u64,observation_id:String},
}
#[derive(Serialize,Deserialize,Debug)]
#[serde(deny_unknown_fields)]
pub struct Reply {pub wire:String,pub session:String,pub seq:u64,pub status:u16,pub code:String,
    pub observation_id:Option<String>,pub observed_at_us:Option<u64>,pub files:Vec<PinnedFile>,
    pub qualification:String,pub registration_sha256:String,pub resource_manifest_sha256:String,pub runtime_manifest_sha256:String}
fn reply(locator:&ChildLocator,context:&FactsContext,seq:u64,status:u16,code:&str)->Reply{Reply{wire:WIRE.into(),session:locator.session.clone(),seq,status,code:code.into(),observation_id:None,observed_at_us:None,files:Vec::new(),qualification:"not_ready".into(),registration_sha256:context.registration_sha256.clone(),resource_manifest_sha256:context.resource_manifest_sha256.clone(),runtime_manifest_sha256:context.runtime_manifest_sha256.clone()}}

pub struct AuthorityStatistics{rejected_peers:AtomicU32}
impl AuthorityStatistics{pub fn rejected_peers(&self)->u32{self.rejected_peers.load(Ordering::Acquire)}}
enum ChannelObservation<'guard>{Payload(HeldFileObservation<'guard>),Installation(crate::native_installation::InstallationObservation<'guard>)}
impl ChannelObservation<'_>{
    fn files(&self)->&[PinnedFile]{match self{Self::Payload(observed)=>observed.files(),Self::Installation(observed)=>observed.payload_files()}}
    fn observed_at_us(&self)->u64{match self{Self::Payload(observed)=>observed.observed_at_us(),Self::Installation(observed)=>observed.observed_at_us()}}
}
pub struct PendingAuthority {pipe:Pipe,locator:ChildLocator,context:FactsContext,guard:Arc<ResourcePins>,expected_image:PathBuf,expected_sha:String,statistics:Arc<AuthorityStatistics>,installation:Option<Arc<crate::native_installation::NativeInstallationGuards>>}
impl PendingAuthority {
    /// The expected child image must itself be held by this original guard.
    pub fn create_facts_only(guard:Arc<ResourcePins>,child_image_relative:&str,context:FactsContext)->Result<Self,&'static str>{
        context.validate()?;let fact=guard.observe_files(&[child_image_relative])?;let expected_sha=fact.files()[0].sha256.clone();let expected_image=guard.resolve(child_image_relative)?;drop(fact);
        // QueryFullProcessImageNameW in the actual Python peer returns a local
        // drive path. Strip only Win32's equivalent canonical drive prefix for
        // the wire; retained identities still resolve the same actual file.
        let mut server=current_identity()?;server.image=local_wire_image(&server.image)?;
        let pipe_name=format!("\\\\.\\pipe\\VideoCreator-Held-{}",random_id()?);let pipe=create_pipe(&pipe_name,&server.sid)?;
        let locator=ChildLocator{pipe:pipe_name,session:random_id()?,instance_id:context.instance_id.clone(),role:context.role.clone(),server};
        Ok(Self{pipe,locator,context,guard,expected_image,expected_sha,statistics:Arc::new(AuthorityStatistics{rejected_peers:AtomicU32::new(0)}),installation:None})
    }
    fn create_installed_facts_only(installation:Arc<crate::native_installation::NativeInstallationGuards>,child_image_relative:&str,context:FactsContext)->Result<Self,&'static str>{
        installation.image_is_current_process()?;
        if (&context.registration_sha256,&context.resource_manifest_sha256,&context.runtime_manifest_sha256)
            !=(&installation.inputs.registration_sha256,&installation.inputs.resource_manifest_sha256,&installation.inputs.runtime_manifest_sha256){return Err("authority_installation_identity_mismatch");}
        let observed=installation.observe()?;installation.assert_current(&observed)?;drop(observed);
        let mut pending=Self::create_facts_only(installation.payload.clone(),child_image_relative,context)?;
        pending.installation=Some(installation);Ok(pending)
    }
    pub fn locator(&self)->&ChildLocator{&self.locator}
    pub fn statistics(&self)->Arc<AuthorityStatistics>{self.statistics.clone()}
    pub fn start(self)->Result<(AuthorityRegistration,JoinHandle<Result<(),&'static str>>),&'static str>{
        let(sender,receiver)=mpsc::sync_channel(1);let join=thread::Builder::new().name("held-resource-authority".into()).spawn(move||self.serve(receiver)).map_err(|_|"authority_thread_failed")?;
        Ok((AuthorityRegistration{sender:Some(sender)},join))
    }
    fn serve(self,receiver:mpsc::Receiver<Arc<Mutex<OwnedProcess>>>)->Result<(),&'static str>{
        let deadline=Instant::now()+LAUNCH_DEADLINE;
        // Registration is before Python factory/ready, never waits for API ready.
        let process=receiver.recv_timeout(LAUNCH_DEADLINE).map_err(|_|"authority_registration_missing")?;
        let outcome=(||{
            loop{self.pipe.connect(deadline)?;
                let mut peer=0;let valid=unsafe{GetNamedPipeClientProcessId(self.pipe.0.0,&mut peer)}!=0&&self.check_peer(&process,peer).is_ok();
                if valid{break;}self.statistics.rejected_peers.fetch_add(1,Ordering::Release);unsafe{DisconnectNamedPipe(self.pipe.0.0);}if Instant::now()>=deadline{return Err("authority_peer_deadline");}
            }
            self.calls(&process)
        })();
        unsafe{DisconnectNamedPipe(self.pipe.0.0);}
        // Disconnect invalidates all IDs, but neither releases guard nor stops
        // authorised work. UNKNOWN keeps exact original HANDLE, Job and Arc.
        loop{let terminal=if let Ok(owned)=process.lock(){matches!(owned.wait_exit(20),Ok(Some(_)))&&matches!(owned.job_pids(),Ok(pids)if pids.is_empty())}else{false};if terminal{break;}thread::sleep(Duration::from_millis(20));}
        outcome
    }
    fn check_peer(&self,process:&Arc<Mutex<OwnedProcess>>,peer:u32)->Result<(),&'static str>{
        let process=process.lock().map_err(|_|"authority_process_lock_failed")?;let raw=process.authority_peer_handle(peer)?;let actual=identity(raw,peer)?;
        if actual.sid!=self.locator.server.sid||actual.image!=self.expected_image||actual.image_sha256!=self.expected_sha{return Err("authority_peer_image_or_sid");}Ok(())
    }
    fn calls(&self,process:&Arc<Mutex<OwnedProcess>>)->Result<(),&'static str>{
        let mut observations:HashMap<String,ChannelObservation<'_>>=HashMap::new();let mut expected=0u64;let mut bound=false;
        loop{
            let mut peer=0;if unsafe{GetNamedPipeClientProcessId(self.pipe.0.0,&mut peer)}==0{return Err("authority_peer_unknown");}self.check_peer(process,peer)?;
            let raw=self.pipe.receive(Instant::now()+CALL_DEADLINE)?;
            let request:Request=match serde_json::from_slice(&raw){Ok(value)=>value,Err(_)=>{self.pipe.send(&reply(&self.locator,&self.context,expected,422,"invalid_frame"),Instant::now()+CALL_DEADLINE)?;return Err("authority_frame_invalid");}};
            let(wire,session,seq)=match &request{Request::Bind{wire,session,seq,..}|Request::Observe{wire,session,seq}|Request::Assert{wire,session,seq,..}=>(wire,session,*seq)};
            if wire!=WIRE||session!=&self.locator.session||seq!=expected{return Err("authority_sequence_or_context");}expected=expected.checked_add(1).ok_or("authority_sequence_exhausted")?;
            let mut response=match request{
                Request::Bind{instance_id,role,..}=>{if bound||seq!=0||instance_id!=self.context.instance_id||role!=self.context.role{return Err("authority_bind_invalid");}bound=true;reply(&self.locator,&self.context,seq,200,"bound_facts_only")},
                Request::Observe{..}=>{if !bound{return Err("authority_bind_required");}if observations.len()>=64{return Err("authority_observation_limit");}
                    let observed=match &self.installation{Some(installation)=>ChannelObservation::Installation(installation.observe()?),None=>ChannelObservation::Payload(self.guard.observe_all()?)};
                    let id=random_id()?;let mut response=reply(&self.locator,&self.context,seq,200,"observed_facts_only");
                    response.observation_id=Some(id.clone());response.observed_at_us=Some(observed.observed_at_us());response.files=observed.files().to_vec();observations.insert(id,observed);response},
                Request::Assert{observation_id,..}=>{if !bound{return Err("authority_bind_required");}
                    if let Some(observed)=observations.get(&observation_id){match observed{
                        ChannelObservation::Payload(observed)=>self.guard.assert_current(observed)?,
                        ChannelObservation::Installation(observed)=>self.installation.as_ref().ok_or("authority_installation_owner_missing")?.assert_current(observed)?,
                    }reply(&self.locator,&self.context,seq,200,"current_facts_only")}
                    else{reply(&self.locator,&self.context,seq,409,"observation_unknown_or_foreign")}},
            };
            // Actual peer is rechecked after a potentially long held-file hash.
            self.check_peer(process,peer)?;response.qualification="not_ready".into();self.pipe.send(&response,Instant::now()+CALL_DEADLINE)?;
        }
    }
}
pub struct AuthorityRegistration{sender:Option<mpsc::SyncSender<Arc<Mutex<OwnedProcess>>>>}
impl AuthorityRegistration {pub fn register(mut self,process:Arc<Mutex<OwnedProcess>>)->Result<(),&'static str>{self.sender.take().ok_or("authority_registration_consumed")?.send(process).map_err(|_|"authority_registration_failed")}}

/// Independent pre-API setup role. Reuses the exact I50 deadline-safe I/O;
/// the only authenticated process is the original registered HANDLE/Job.
pub(crate) struct OwnerSetupPipe {
    pipe:Pipe,pub(crate) locator:ChildLocator,
    installation:Arc<crate::native_installation::NativeInstallationGuards>,
    expected_image:PathBuf,expected_sha:String,
}
impl OwnerSetupPipe {
    pub(crate) fn create_record(installation:Arc<crate::native_installation::NativeInstallationGuards>,instance:&str)->Result<Self,&'static str>{
        Self::create_role(installation,instance,"installation-record-admission","VideoCreator-InstallationRecord-")
    }
    pub(crate) fn create_qualified(installation:Arc<crate::native_installation::NativeInstallationGuards>,instance:&str,role:&str,image:&str)->Result<Self,&'static str>{
        if !matches!(role,"api"|"worker"|"mcp"|"asr"){return Err("qualification_role_invalid");}
        Self::create_role_image(installation,instance,role,"VideoCreator-Held-",image)
    }
    pub(crate) fn create_trust(installation:Arc<crate::native_installation::NativeInstallationGuards>,instance:&str)->Result<Self,&'static str>{
        Self::create_role(installation,instance,"installation-trust-admission","VideoCreator-InstallationTrust-")
    }
    pub(crate) fn create(installation:Arc<crate::native_installation::NativeInstallationGuards>,instance:&str)->Result<Self,&'static str>{
        Self::create_role(installation,instance,"owner-setup","VideoCreator-OwnerSetup-")
    }
    pub(crate) fn create_initialize(installation:Arc<crate::native_installation::NativeInstallationGuards>)->Result<Self,&'static str>{
        // No instance exists at this stage. The private initialization locator
        // emits only pipe/session/role/server; the empty internal slot is never
        // serialized as an instance, permission, or confirmation descriptor.
        Self::create_role(installation,"","owner-setup-initialize","VideoCreator-OwnerSetupInit-")
    }
    fn create_role(installation:Arc<crate::native_installation::NativeInstallationGuards>,instance:&str,role:&str,family:&str)->Result<Self,&'static str>{
        Self::create_role_image(installation,instance,role,family,"Runtime/Python/python.exe")
    }
    fn create_role_image(installation:Arc<crate::native_installation::NativeInstallationGuards>,instance:&str,role:&str,family:&str,image:&str)->Result<Self,&'static str>{
        installation.image_is_current_process()?;
        let observed=installation.observe()?;installation.assert_current(&observed)?;drop(observed);
        let expected_image=installation.payload.resolve(image)?;
        let observed=installation.payload.observe_files(&[image])?;
        let expected_sha=observed.files()[0].sha256.clone();drop(observed);
        let mut server=current_identity()?;server.image=local_wire_image(&server.image)?;
        let name=format!("\\\\.\\pipe\\{family}{}",random_id()?);
        let pipe=create_pipe(&name,&server.sid)?;
        let locator=ChildLocator{pipe:name,session:random_id()?,instance_id:instance.into(),role:role.into(),server};
        Ok(Self{pipe,locator,installation,expected_image,expected_sha})
    }
    pub(crate) fn assert_owned(&self,process:&Arc<Mutex<OwnedProcess>>)->Result<ProcessIdentity,&'static str>{
        let process=process.lock().map_err(|_|"owner_setup_process_busy")?;
        if !process.alive(){return Err("owner_setup_child_exited");}
        let actual=identity(process.authority_peer_handle(process.pid)?,process.pid)?;
        if actual.sid!=self.locator.server.sid||local_wire_image(&actual.image)?!=local_wire_image(&self.expected_image)?||actual.image_sha256!=self.expected_sha{return Err("owner_setup_peer_denied");}
        let observed=self.installation.observe()?;self.installation.assert_current(&observed)?;Ok(actual)
    }
    pub(crate) fn assert_peer(&self,process:&Arc<Mutex<OwnedProcess>>)->Result<ProcessIdentity,&'static str>{
        let mut peer=0;if unsafe{GetNamedPipeClientProcessId(self.pipe.0.0,&mut peer)}==0{return Err("owner_setup_peer_unknown");}
        let actual=self.assert_owned(process)?;
        if peer!=actual.pid{return Err("owner_setup_peer_denied");}Ok(actual)
    }
    pub(crate) fn connect(&self,process:&Arc<Mutex<OwnedProcess>>,deadline:Instant)->Result<ProcessIdentity,&'static str>{
        loop{self.pipe.connect(deadline)?;match self.assert_peer(process){Ok(peer)=>return Ok(peer),Err(_)=>{self.disconnect();check_deadline(deadline)?;}}}
    }
    pub(crate) fn receive(&self,deadline:Instant)->Result<Vec<u8>,&'static str>{self.pipe.receive(deadline)}
    /// Idle is not an exchange. Peek consumes no byte or borrowed protocol
    /// buffer; a complete frame gets one deadline from its first available
    /// byte. The original child, never a reopened PID, governs idle lifetime.
    pub(crate) fn wait_request(&self,process:&Arc<Mutex<OwnedProcess>>)->Result<Option<Instant>,&'static str>{
        loop{
            if !process.lock().map_err(|_|"authority_process_lock_failed")?.alive(){return Ok(None);}
            let mut available=0;
            if unsafe{PeekNamedPipe(self.pipe.0.0,null_mut(),0,null_mut(),&mut available,null_mut())}==0{return Err("authority_io_failed");}
            if available>0{return Ok(Some(Instant::now()+CALL_DEADLINE));}
            thread::sleep(Duration::from_millis(20));
        }
    }
    pub(crate) fn send(&self,value:&serde_json::Value,deadline:Instant)->Result<(),&'static str>{
        let mut body=crate::native_installation::canonical(value)?;
        if body.is_empty()||body.len()>MAX_FRAME{return Err("owner_setup_frame_size");}
        let mut prefix=(body.len()as u32).to_le_bytes();self.pipe.bytes(&mut prefix,true,deadline)?;self.pipe.bytes(&mut body,true,deadline)
    }
    pub(crate) fn disconnect(&self){unsafe{DisconnectNamedPipe(self.pipe.0.0);}}
}

/// This wrapper retains the exact child/Job and guard on every teardown path.
pub struct AuthorityOwnedChild {pub process:Arc<Mutex<OwnedProcess>>,guard:Arc<ResourcePins>,session:Option<JoinHandle<Result<(),&'static str>>>,_prepared:Option<crate::load_policy::PreparedLaunch>}
impl AuthorityOwnedChild {
    pub fn from_registered(process:Arc<Mutex<OwnedProcess>>,guard:Arc<ResourcePins>,session:JoinHandle<Result<(),&'static str>>)->Self{Self{process,guard,session:Some(session),_prepared:None}}
    /// Native-only production startup seam. The same PreparedLaunch survives
    /// errors and teardown; current facts-only qualification cannot admit an
    /// InstalledProductionEvidence. Backend thin factory remains required.
    pub(crate) fn launch_prepared_facts_only(prepared:crate::load_policy::PreparedLaunch,context:FactsContext)->Result<Self,&'static str>{Self::launch_prepared(prepared,context,None)}
    pub(crate) fn launch_prepared_installed_facts_only(prepared:crate::load_policy::PreparedLaunch,context:FactsContext,installation:Arc<crate::native_installation::NativeInstallationGuards>)->Result<Self,&'static str>{
        if !Arc::ptr_eq(&installation.payload,&prepared.guard){return Err("authority_installation_guard_mismatch");}
        Self::launch_prepared(prepared,context,Some(installation))
    }
    fn launch_prepared(mut prepared:crate::load_policy::PreparedLaunch,context:FactsContext,installation:Option<Arc<crate::native_installation::NativeInstallationGuards>>)->Result<Self,&'static str>{
        let relative=prepared.executable.strip_prefix(prepared.guard.root()).map_err(|_|"authority_child_unpinned")?.to_str().ok_or("authority_child_unpinned")?;
        let pending=match installation{Some(installation)=>PendingAuthority::create_installed_facts_only(installation,relative,context)?,None=>PendingAuthority::create_facts_only(prepared.guard.clone(),relative,context)?};
        if prepared.environment.iter().any(|(key,_)|key=="VIDEO_CREATOR_HELD_RESOURCE_CHANNEL"){return Err("authority_locator_duplicate");}
        let locator=serde_json::to_string(pending.locator()).map_err(|_|"authority_locator_invalid")?;
        prepared.environment.push((OsString::from("VIDEO_CREATOR_HELD_RESOURCE_CHANNEL"),OsString::from(locator)));
        let(registration,session)=pending.start()?;
        let started=match prepared.launch_owned(){Ok(value)=>value,Err(error)=>{drop(registration);let _=session.join();return Err(error);}};
        let process=Arc::new(Mutex::new(started.process));
        let child=Self{process:process.clone(),guard:started.prepared.guard.clone(),session:Some(session),_prepared:Some(started.prepared)};
        registration.register(process)?;Ok(child)
    }
    pub fn terminal(&self)->Result<bool,&'static str>{let process=self.process.lock().map_err(|_|"authority_process_lock_failed")?;Ok(process.wait_exit(0)?.is_some()&&process.job_pids()?.is_empty())}
    pub fn join_session(&mut self)->Result<(),&'static str>{if !self.terminal()?{return Err("authority_child_not_terminal");}self.session.take().ok_or("authority_session_joined")?.join().map_err(|_|"authority_session_panicked")?}
}
impl Drop for AuthorityOwnedChild{fn drop(&mut self){loop{let clean=if let Ok(process)=self.process.lock(){let _=process.force();matches!(process.wait_exit(20),Ok(Some(_)))&&matches!(process.job_pids(),Ok(pids)if pids.is_empty())}else{false};if clean{break;}thread::sleep(Duration::from_millis(20));}if let Some(session)=self.session.take(){let _=session.join();}let _held=&self.guard;}}

/// Separate private Owner-action observation wire. It is neither an execution
/// role nor an Owner capability. Backend still authenticates/asks the real TTY
/// or Native UI, and independently checks every current Owner/store field.
pub const INSTALLATION_WIRE:&str="native-installation-observer-v1";
#[derive(Deserialize)]
#[serde(tag="method",deny_unknown_fields)]
enum InstallationRequest{
    #[serde(rename="bind")]Bind{wire:String,session:String,seq:u64,installation_inputs_sha256:String},
    #[serde(rename="observe")]Observe{wire:String,session:String,seq:u64},
    #[serde(rename="assert_current")]Assert{wire:String,session:String,seq:u64,observation_id:String},
    #[serde(rename="close")]Close{wire:String,session:String,seq:u64,observation_id:Option<String>},
}
#[derive(Serialize)]
struct AbsoluteFileFact{path:String,bytes:u64,sha256:String}
#[derive(Serialize)]
struct InstallationReply{
    wire:&'static str,session:String,seq:u64,status:u16,code:&'static str,installation_inputs_sha256:String,
    observation_id:Option<String>,observed_at_us:Option<u64>,host_image:Option<AbsoluteFileFact>,
    build_receipt_file:Option<AbsoluteFileFact>,payload_files:Vec<PinnedFile>,qualification:&'static str,
}
pub struct PendingInstallationObserver{
    pipe:Pipe,locator:ChildLocator,installation:Arc<crate::native_installation::NativeInstallationGuards>,
    expected_image:PathBuf,expected_sha:String,input_sha:String,
}
impl PendingInstallationObserver{
    /// No arbitrary process descriptor/renderer/command/module/Owner fields.
    /// The physical Python image is selected from the original full payload.
    pub fn create(installation:Arc<crate::native_installation::NativeInstallationGuards>,instance_id:&str)->Result<Self,&'static str>{
        if instance_id.is_empty()||instance_id.len()>128||!instance_id.bytes().all(|b|b.is_ascii_alphanumeric()||b"_.:-".contains(&b)){return Err("installation_observer_instance_invalid");}
        installation.image_is_current_process()?;
        let observed=installation.observe()?;installation.assert_current(&observed)?;drop(observed);
        let expected_image=installation.payload.resolve("Runtime/Python/python.exe")?;
        let observed=installation.payload.observe_files(&["Runtime/Python/python.exe"])?;
        let expected_sha=observed.files()[0].sha256.clone();drop(observed);
        let input_sha=installation.inputs_sha256()?;
        let mut server=current_identity()?;server.image=local_wire_image(&server.image)?;
        let name=format!("\\\\.\\pipe\\VideoCreator-Install-{}",random_id()?);let pipe=create_pipe(&name,&server.sid)?;
        let locator=ChildLocator{pipe:name,session:random_id()?,instance_id:instance_id.into(),role:"owner-installation".into(),server};
        Ok(Self{pipe,locator,installation,expected_image,expected_sha,input_sha})
    }
    pub fn locator(&self)->&ChildLocator{&self.locator}
    pub fn start(self)->Result<(AuthorityRegistration,JoinHandle<Result<(),&'static str>>),&'static str>{
        let(sender,receiver)=mpsc::sync_channel(1);let session=thread::Builder::new().name("native-installation-observer".into()).spawn(move||self.serve(receiver)).map_err(|_|"installation_observer_thread_failed")?;
        Ok((AuthorityRegistration{sender:Some(sender)},session))
    }
    fn peer(&self,process:&Arc<Mutex<OwnedProcess>>)->Result<(),&'static str>{
        let mut peer=0;if unsafe{GetNamedPipeClientProcessId(self.pipe.0.0,&mut peer)}==0{return Err("installation_observer_peer_unknown");}
        let process=process.lock().map_err(|_|"installation_observer_process_lock_failed")?;
        let actual=identity(process.authority_peer_handle(peer)?,peer)?;
        if actual.sid!=self.locator.server.sid||actual.image!=self.expected_image||actual.image_sha256!=self.expected_sha{return Err("installation_observer_peer_denied");}Ok(())
    }
    fn response(&self,seq:u64,code:&'static str)->InstallationReply{InstallationReply{wire:INSTALLATION_WIRE,session:self.locator.session.clone(),seq,status:200,code,installation_inputs_sha256:self.input_sha.clone(),observation_id:None,observed_at_us:None,host_image:None,build_receipt_file:None,payload_files:Vec::new(),qualification:"not_ready"}}
    fn calls(&self,process:&Arc<Mutex<OwnedProcess>>)->Result<(),&'static str>{
        let mut observations=HashMap::new();let mut expected=0u64;let mut bound=false;
        loop{
            self.peer(process)?;let deadline=Instant::now()+CALL_DEADLINE;
            let raw=self.pipe.receive(deadline)?;let request:InstallationRequest=serde_json::from_slice(&raw).map_err(|_|"installation_observer_frame_invalid")?;
            let(wire,session,seq)=match &request{InstallationRequest::Bind{wire,session,seq,..}|InstallationRequest::Observe{wire,session,seq}|InstallationRequest::Assert{wire,session,seq,..}|InstallationRequest::Close{wire,session,seq,..}=>(wire,session,*seq)};
            if wire!=INSTALLATION_WIRE||session!=&self.locator.session||seq!=expected{return Err("installation_observer_sequence_invalid");}expected=expected.checked_add(1).ok_or("installation_observer_sequence_exhausted")?;
            let mut closing=false;let response=match request{
                InstallationRequest::Bind{installation_inputs_sha256,..}=>{if bound||seq!=0||installation_inputs_sha256!=self.input_sha{return Err("installation_observer_bind_invalid");}bound=true;self.response(seq,"bound_facts_only")},
                InstallationRequest::Observe{..}=>{
                    if !bound||observations.len()>=64{return Err("installation_observer_not_bound_or_full");}
                    let observed=self.installation.observe()?;self.installation.assert_current(&observed)?;
                    let id=random_id()?;let mut response=self.response(seq,"observed_facts_only");
                    response.observation_id=Some(id.clone());response.observed_at_us=Some(observed.observed_at_us());
                    response.host_image=Some(AbsoluteFileFact{path:crate::load_policy::text(&self.installation.host_path)?,bytes:observed.host_file().bytes,sha256:observed.host_file().sha256.clone()});
                    response.build_receipt_file=Some(AbsoluteFileFact{path:crate::load_policy::text(self.installation.receipt_path())?,bytes:observed.receipt_file().bytes,sha256:observed.receipt_file().sha256.clone()});
                    response.payload_files=observed.payload_files().to_vec();observations.insert(id,observed);response},
                InstallationRequest::Assert{observation_id,..}=>{if !bound{return Err("installation_observer_bind_required");}let observed=observations.get(&observation_id).ok_or("installation_observer_original_observation_required")?;self.installation.assert_current(observed)?;self.response(seq,"current_facts_only")},
                InstallationRequest::Close{observation_id,..}=>{if !bound||observation_id.as_ref().is_some_and(|id|!observations.contains_key(id)){return Err("installation_observer_original_observation_required");}
                    observations.clear();closing=true;self.response(seq,"view_closed_native_ownership_retained")},
            };
            self.peer(process)?;self.pipe.send(&response,deadline)?;
            if closing{return Ok(());}
        }
    }
    fn serve(self,receiver:mpsc::Receiver<Arc<Mutex<OwnedProcess>>>)->Result<(),&'static str>{
        let deadline=Instant::now()+LAUNCH_DEADLINE;
        let process=receiver.recv_timeout(LAUNCH_DEADLINE).map_err(|_|"installation_observer_child_missing")?;
        let outcome=(||{loop{self.pipe.connect(deadline)?;if self.peer(&process).is_ok(){break;}unsafe{DisconnectNamedPipe(self.pipe.0.0);}check_deadline(deadline)?;}self.calls(&process)})();
        unsafe{DisconnectNamedPipe(self.pipe.0.0);}
        // An ACK closes an observation view, never releases native ownership.
        // The same actual registered HANDLE/Job survives every unknown result.
        loop{let terminal=if let Ok(owned)=process.lock(){owned.wait_exit(20).is_ok_and(|exit|exit.is_some())&&owned.job_pids().is_ok_and(|pids|pids.is_empty())}else{false};if terminal{break;}thread::sleep(Duration::from_millis(20));}
        // Ending this action/session invalidates its IDs by dropping the
        // session-local observations. It must not invalidate an independent
        // API/Worker session sharing the original installation Arc.
        outcome
    }
}

pub struct AuthorityClient {pipe:Pipe,server:Handle,locator:ChildLocator,seq:u64,valid:bool}
impl AuthorityClient {
    /// Caller is a fixed native/Python bootstrap consumer with trusted locator;
    /// arbitrary JSON/renderer descriptors may not call this as an authority.
    pub fn open(locator:ChildLocator)->Result<Self,&'static str>{
        if !locator.pipe.starts_with("\\\\.\\pipe\\VideoCreator-Held-")||locator.pipe.len()>160{return Err("authority_locator_invalid");}
        let name=wide(OsStr::new(&locator.pipe))?;let raw=unsafe{CreateFileW(name.as_ptr(),GENERIC_READ|GENERIC_WRITE,0,null(),OPEN_EXISTING,FILE_FLAG_OVERLAPPED,null_mut())};
        if raw==INVALID_HANDLE_VALUE{return Err("authority_client_open_failed");}let pipe=Pipe(Handle(raw));let mut peer=0;
        if unsafe{GetNamedPipeServerProcessId(raw,&mut peer)}==0||peer!=locator.server.pid||parent_pid()?!=peer{return Err("authority_server_parent_invalid");}
        let server=Handle(unsafe{OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION,0,peer)});if server.0.is_null(){return Err("authority_server_unknown");}
        if !same_identity(&identity(server.0,peer)?,&locator.server){return Err("authority_server_identity_invalid");}
        let current=current_identity()?;if current.sid!=locator.server.sid{return Err("authority_server_sid_invalid");}
        let mut client=Self{pipe,server,locator,seq:0,valid:true};let bind=serde_json::json!({"method":"bind","wire":WIRE,"session":client.locator.session,"seq":0,"instance_id":client.locator.instance_id,"role":client.locator.role});
        if client.exchange(&bind)?.status!=200{return Err("authority_bind_refused");}Ok(client)
    }
    fn exchange<T:Serialize>(&mut self,request:&T)->Result<Reply,&'static str>{if !self.valid{return Err("authority_connection_invalid");}
        let result=(||{if !same_identity(&identity(self.server.0,self.locator.server.pid)?,&self.locator.server){return Err("authority_server_identity_invalid");}
            self.pipe.send(request,Instant::now()+CALL_DEADLINE)?;let raw=self.pipe.receive(Instant::now()+CALL_DEADLINE)?;
            if !same_identity(&identity(self.server.0,self.locator.server.pid)?,&self.locator.server){return Err("authority_server_identity_invalid");}
            let reply:Reply=serde_json::from_slice(&raw).map_err(|_|"authority_reply_invalid")?;if reply.wire!=WIRE||reply.session!=self.locator.session||reply.seq!=self.seq{return Err("authority_reply_context_invalid");}self.seq=self.seq.checked_add(1).ok_or("authority_sequence_exhausted")?;Ok(reply)})();
        if result.is_err(){self.valid=false;}result
    }
    pub fn observe(&mut self)->Result<Reply,&'static str>{self.exchange(&serde_json::json!({"method":"observe","wire":WIRE,"session":self.locator.session,"seq":self.seq}))}
    pub fn assert_current(&mut self,id:&str)->Result<Reply,&'static str>{self.exchange(&serde_json::json!({"method":"assert_current","wire":WIRE,"session":self.locator.session,"seq":self.seq,"observation_id":id}))}
    pub fn invalidate(&mut self){self.valid=false;let old=std::mem::replace(&mut self.pipe.0.0,null_mut());if !old.is_null(){unsafe{CloseHandle(old);}}}
}
