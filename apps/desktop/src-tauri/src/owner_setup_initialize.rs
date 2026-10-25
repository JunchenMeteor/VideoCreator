//! Instance-independent original child binding. Never creates an instance ID.
use std::{sync::{Arc,Mutex,mpsc},thread::{self,JoinHandle},time::{Duration,Instant}};
use serde::Deserialize;
use serde_json::{json,Value};
use crate::{native_installation::NativeInstallationGuards,owner_setup_directory::OwnerDirectory,
    platform::OwnedProcess,resource_authority::{OwnerSetupPipe,ProcessIdentity,assert_registered_identity}};
const WIRE:&str="native-owner-instance-peer-v1";
#[derive(Deserialize)]#[serde(deny_unknown_fields)]
struct Bind {wire:String,session:String,seq:u64,method:String}
pub(crate) struct InitializationCurrent {
    process:Arc<Mutex<OwnedProcess>>,child:ProcessIdentity,installation:Arc<NativeInstallationGuards>,
    directory:Arc<OwnerDirectory>,host:ProcessIdentity,os_session:u32,
}
impl InitializationCurrent {
    pub(crate) fn assert_owned_process(&self,process:&Arc<Mutex<OwnedProcess>>)->Result<(),&'static str>{
        if !Arc::ptr_eq(&self.process,process){return Err("owner_instance_binding_changed");}
        self.assert_current()
    }
    pub(crate) fn assert_current(&self)->Result<(),&'static str>{
        assert_registered_identity(&self.process,&self.child)?;self.directory.assert_current()?;
        self.installation.image_is_current_process()?;
        let observation=self.installation.observe()?;self.installation.assert_current(&observation)?;
        let current=crate::resource_authority::current_identity()?;
        if(current.pid,current.creation_filetime,current.sid.as_str(),current.image_sha256.as_str())
            !=(self.host.pid,self.host.creation_filetime,self.host.sid.as_str(),self.host.image_sha256.as_str()) {return Err("owner_instance_binding_changed");}
        let mut child_session=0;
        if unsafe{windows_sys::Win32::System::RemoteDesktop::ProcessIdToSessionId(self.child.pid,&mut child_session)}==0
            ||child_session!=self.os_session||crate::owner_setup_window::interactive_session()?!=self.os_session {return Err("owner_instance_source_denied");}Ok(())
    }
}
pub(crate) struct PendingInitialization {pipe:OwnerSetupPipe,installation:Arc<NativeInstallationGuards>,directory:Arc<OwnerDirectory>}
impl PendingInitialization {
    pub(crate) fn create(installation:Arc<NativeInstallationGuards>,directory:Arc<OwnerDirectory>)->Result<Self,&'static str>{
        Ok(Self{pipe:OwnerSetupPipe::create_initialize(installation.clone())?,installation,directory})
    }
    pub(crate) fn locator(&self)->Value{
        let source=&self.pipe.locator;
        json!({"pipe":source.pipe,"session":source.session,"role":source.role,"server":source.server})
    }
    pub(crate) fn start(self,deadline:Instant)->Result<(mpsc::SyncSender<Arc<Mutex<OwnedProcess>>>,mpsc::Receiver<Arc<InitializationCurrent>>,JoinHandle<Result<(),&'static str>>),&'static str>{
        let(sender,receiver)=mpsc::sync_channel(1);let(current_tx,current_rx)=mpsc::sync_channel(1);
        let thread=thread::Builder::new().name("native-owner-instance-initialize".into()).spawn(move||self.serve(receiver,current_tx,deadline)).map_err(|_|"owner_instance_source_unavailable")?;
        Ok((sender,current_rx,thread))
    }
    fn serve(self,receiver:mpsc::Receiver<Arc<Mutex<OwnedProcess>>>,current_tx:mpsc::SyncSender<Arc<InitializationCurrent>>,deadline:Instant)->Result<(),&'static str>{
        let process=receiver.recv_timeout(deadline.saturating_duration_since(Instant::now())).map_err(|_|"owner_instance_handshake_timeout")?;
        let outcome=(||{
            let child=self.pipe.connect(&process,deadline)?;
            let source=Arc::new(InitializationCurrent{process:process.clone(),child,installation:self.installation.clone(),directory:self.directory.clone(),host:self.pipe.locator.server.clone(),os_session:crate::owner_setup_window::interactive_session()?});
            source.assert_current()?;
            let exchange=deadline.min(Instant::now()+Duration::from_secs(10));
            let bytes=self.pipe.receive(exchange)?;
            if bytes.len()>16*1024{return Err("owner_instance_handshake_limit");}
            let value:Value=serde_json::from_slice(&bytes).map_err(|_|"owner_instance_handshake_invalid")?;
            if crate::native_installation::canonical(&value)?!=bytes{return Err("owner_instance_handshake_invalid");}
            let bind:Bind=serde_json::from_value(value).map_err(|_|"owner_instance_handshake_invalid")?;
            if bind.wire!=WIRE||bind.session!=self.pipe.locator.session||bind.seq!=1||bind.method!="bind"{return Err("owner_instance_handshake_invalid");}
            self.pipe.assert_peer(&process)?;source.assert_current()?;
            self.pipe.send(&json!({"wire":WIRE,"session":bind.session,"seq":1,"status":200,"code":"bound"}),exchange)?;
            current_tx.send(source.clone()).map_err(|_|"owner_instance_source_unavailable")?;
            // B43 current is local actual OS/held-file recheck, not another RPC.
            // Keep the original connection and source through the whole child.
            loop{
                let terminal=process.lock().is_ok_and(|owned|owned.wait_exit(20).is_ok_and(|exit|exit.is_some())&&owned.job_pids().is_ok_and(|pids|pids.is_empty()));
                if terminal{break;}
                thread::sleep(Duration::from_millis(20));
            }Ok(())
        })();
        // Failure/disable cannot drop original guards on an unknown child.
        loop{let terminal=process.lock().is_ok_and(|owned|owned.wait_exit(20).is_ok_and(|exit|exit.is_some())&&owned.job_pids().is_ok_and(|pids|pids.is_empty()));if terminal{break;}thread::sleep(Duration::from_millis(20));}
        self.pipe.disconnect();outcome
    }
}
