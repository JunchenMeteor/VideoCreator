//! Current qualification lives in this original Registry; a descriptor cannot
//! create it. Short writer leases are real RW read guards in the pipe thread.
use std::{sync::{Arc,Mutex,RwLock,RwLockReadGuard,atomic::{AtomicBool,AtomicU64,Ordering}},thread,time::{Duration,Instant,SystemTime,UNIX_EPOCH}};
use serde_json::{json,Value};
use crate::{native_installation::NativeInstallationGuards,platform::OwnedProcess,qualification_commit::CommittedQualificationSource,
    qualification_record::{identifier,QualificationRef,I64_MAX}};

pub(crate) struct QualificationRegistry {
    pub(crate) installation:Arc<NativeInstallationGuards>,instance:String,current:RwLock<Option<CommittedQualificationSource>>,
    gate:AtomicBool,epoch:AtomicU64,
}
pub(crate) struct QualifiedObservation<'registry>{registry:&'registry QualificationRegistry,epoch:u64,record_ref:QualificationRef}
pub(crate) struct QualifiedWriterLease<'registry>{
    registry:&'registry QualificationRegistry,guard:Option<RwLockReadGuard<'registry,Option<CommittedQualificationSource>>>,
    process:Arc<Mutex<OwnedProcess>>,epoch:u64,id:String,observation:String,released:bool,qualification:Value,
}
pub(crate) fn checked_at_us()->Result<u64,&'static str>{
    let value=SystemTime::now().duration_since(UNIX_EPOCH).map_err(|_|"qualification_clock_unavailable")?.as_micros();
    if value==0||value>I64_MAX as u128{return Err("qualification_clock_unavailable");}Ok(value as u64)
}
impl QualificationRegistry {
    pub(crate) fn new(installation:Arc<NativeInstallationGuards>,instance:&str)->Result<Arc<Self>,&'static str>{
        if !identifier(instance){return Err("qualification_instance_invalid");}
        installation.image_is_current_process()?;
        Ok(Arc::new(Self{installation,instance:instance.into(),current:RwLock::new(None),gate:AtomicBool::new(false),epoch:AtomicU64::new(0)}))
    }
    pub(crate) fn instance(&self)->&str{&self.instance}
    pub(crate) fn assert_setup_continuation(&self,member:&crate::load_policy::SetupApiContinuation,deadline:Instant)->Result<(),&'static str>{
        let current=self.read_current(deadline)?;let source=current.as_ref().ok_or("qualification_unavailable")?;
        source.assert_original_target_source(member.source())?;member.assert_current(&source.candidate().record)?;
        if Instant::now()>=deadline{return Err("qualification_registry_busy");}Ok(())
    }
    /// No Registry write lock is held while a Backend file lock/commit is
    /// awaited. The original protected completion proof is checked first.
    pub(crate) fn install_committed(&self,source:CommittedQualificationSource,deadline:Instant)->Result<(),&'static str>{
        self.close_new_leases();source.assert_current()?;
        if !Arc::ptr_eq(&source.candidate().installation,&self.installation)||source.instance()!=self.instance{return Err("qualification_original_source_required");}
        loop{
            if Instant::now()>=deadline{return Err("qualification_registry_busy");}
            match self.current.try_write(){
                Ok(mut current)=>{
                    if current.as_ref().is_some_and(|old|old.registry_revision()>=source.registry_revision()){return Err("qualification_registry_rollback");}
                    source.assert_current()?;
                    if Instant::now()>=deadline{return Err("qualification_registry_busy");}
                    let next=self.epoch.load(Ordering::Acquire).checked_add(1).ok_or("qualification_epoch_exhausted")?;
                    *current=Some(source);self.epoch.store(next,Ordering::Release);self.gate.store(true,Ordering::Release);return Ok(());
                },
                Err(std::sync::TryLockError::WouldBlock)=>thread::sleep(Duration::from_millis(10)),
                Err(std::sync::TryLockError::Poisoned(_))=>return Err("qualification_registry_poisoned"),
            }
        }
    }
    pub(crate) fn close_new_leases(&self){self.gate.store(false,Ordering::Release);}
    pub(crate) fn invalidate(&self){self.close_new_leases();}
    /// The caller must retire the real epoch BEFORE asking Backend to acquire
    /// its mutable-file locks. This method never holds a file lock while waiting
    /// for that Backend operation, and never drops an active writer's read guard.
    pub(crate) fn retire_current(&self,deadline:Instant)->Result<(),&'static str>{
        self.close_new_leases();loop{if Instant::now()>=deadline{return Err("qualification_registry_busy");}
            match self.current.try_write(){Ok(mut current)=>{let epoch=self.epoch.load(Ordering::Acquire).checked_add(1).ok_or("qualification_epoch_exhausted")?;
                current.take();self.epoch.store(epoch,Ordering::Release);return Ok(());},
                Err(std::sync::TryLockError::WouldBlock)=>thread::sleep(Duration::from_millis(10)),
                Err(std::sync::TryLockError::Poisoned(_))=>return Err("qualification_registry_poisoned")}}
    }
    fn read_current(&self,deadline:Instant)->Result<RwLockReadGuard<'_,Option<CommittedQualificationSource>>,&'static str>{
        loop{
            if !self.gate.load(Ordering::Acquire){return Err("qualification_unavailable");}
            if Instant::now()>=deadline{return Err("qualification_registry_busy");}
            match self.current.try_read(){
                Ok(current)=>{
                    if !self.gate.load(Ordering::Acquire){return Err("qualification_unavailable");}
                    let source=current.as_ref().ok_or("qualification_unavailable")?;source.assert_current()?;
                    source.candidate().record.assert_time(checked_at_us()?)?;
                    if Instant::now()>=deadline||!self.gate.load(Ordering::Acquire){return Err("qualification_registry_busy");}return Ok(current);
                },
                Err(std::sync::TryLockError::WouldBlock)=>thread::sleep(Duration::from_millis(10)),
                Err(std::sync::TryLockError::Poisoned(_))=>return Err("qualification_registry_poisoned"),
            }
        }
    }
    pub(crate) fn assert_role(&self,role:&str,image:&str,deadline:Instant)->Result<(),&'static str>{
        let current=self.read_current(deadline)?;let source=current.as_ref().ok_or("qualification_unavailable")?;
        let profile=source.candidate().record.profiles.iter().find(|profile|profile.name==role).ok_or("qualification_role_invalid")?;
        if profile.executable!=image{return Err("qualification_role_image_mismatch");}Ok(())
    }
    pub(crate) fn observe(&self,deadline:Instant)->Result<QualifiedObservation<'_>,&'static str>{
        let current=self.read_current(deadline)?;
        let source=current.as_ref().ok_or("qualification_unavailable")?;
        Ok(QualifiedObservation{registry:self,epoch:self.epoch.load(Ordering::Acquire),record_ref:source.candidate().record.reference()?})
    }
    pub(crate) fn assert_observation(&self,observed:&QualifiedObservation<'_>,deadline:Instant)->Result<(),&'static str>{
        let current=self.read_current(deadline)?;self.assert_local_member(observed,&current)
    }
    fn assert_local_member(&self,observed:&QualifiedObservation<'_>,current:&Option<CommittedQualificationSource>)->Result<(),&'static str>{
        let source=current.as_ref().ok_or("qualification_unavailable")?;
        if !std::ptr::eq(self,observed.registry)||self.epoch.load(Ordering::Acquire)!=observed.epoch||source.candidate().record.reference()?!=observed.record_ref{return Err("qualification_observation_changed");}Ok(())
    }
    pub(crate) fn binding(&self,observed:&QualifiedObservation<'_>,deadline:Instant)->Result<Value,&'static str>{
        let current=self.read_current(deadline)?;self.assert_local_member(observed,&current)?;
        current.as_ref().ok_or("qualification_unavailable")?.binding(checked_at_us()?)
    }
    pub(crate) fn begin_writer_lease<'registry>(&'registry self,observed:&QualifiedObservation<'registry>,observation:&str,process:Arc<Mutex<OwnedProcess>>,deadline:Instant)->Result<QualifiedWriterLease<'registry>,&'static str>{
        let current=self.read_current(deadline)?;self.assert_local_member(observed,&current)?;
        if !process.lock().map_err(|_|"qualification_process_busy")?.alive(){return Err("qualification_child_terminal");}
        let qualification=current.as_ref().ok_or("qualification_unavailable")?.binding(checked_at_us()?)?;
        Ok(QualifiedWriterLease{registry:self,guard:Some(current),process,epoch:observed.epoch,id:crate::resource_authority::private_startup_id()?,observation:observation.into(),released:false,qualification})
    }
}
impl QualifiedWriterLease<'_>{
    pub(crate) fn id(&self)->&str{&self.id}
    pub(crate) fn binding(&self)->Result<Value,&'static str>{
        let source=self.guard.as_ref().and_then(|guard|guard.as_ref()).ok_or("qualification_lease_released")?;
        if self.registry.epoch.load(Ordering::Acquire)!=self.epoch{return Err("qualification_lease_changed");}
        Ok(json!({"lease_id":self.id,"observation_id":self.observation,"record_ref":source.candidate().record.reference()?,"registry_revision":source.registry_revision(),"revocation_floor":source.revocation_floor()}))
    }
    pub(crate) fn qualification_binding(&self)->Result<Value,&'static str>{
        if self.guard.is_none(){return Err("qualification_lease_released");}Ok(self.qualification.clone())
    }
    /// Only this original session member can release its actual read lock.
    pub(crate) fn end(mut self)->Result<Value,&'static str>{let binding=self.binding()?;self.guard.take();self.released=true;Ok(binding)}
}
impl Drop for QualifiedWriterLease<'_>{
    fn drop(&mut self){
        if self.released{return;}
        // Timeout, EOF and unwinding cannot unlock a still-active writer.
        // Keep the real RW guard through this exact original child AND Job.
        loop{let terminal=self.process.lock().unwrap_or_else(|poisoned|poisoned.into_inner());
            let done=terminal.wait_exit(20).is_ok_and(|exit|exit.is_some())&&terminal.job_pids().is_ok_and(|pids|pids.is_empty());drop(terminal);
            if done{break;}thread::sleep(Duration::from_millis(20));}
        self.guard.take();
    }
}
