//! A Rust-only launch primitive for trusted host/test callers; no IPC endpoint.
use std::{ffi::OsString,fs::File,io::Write};
use crate::resource_pins::ResourcePins;

#[derive(Clone,Copy)]
pub struct OwnedIdentity {pub root_pid:u32,pub created_filetime:u64}
#[cfg(windows)]
pub struct NativeSupervisor {process:crate::platform::OwnedProcess,_pins:ResourcePins}
#[cfg(windows)]
impl NativeSupervisor {
    pub fn launch(pins:ResourcePins,executable_relative:&str,args:&[String],environment:&[(OsString,OsString)])->Result<Self,&'static str>{
        let executable=pins.resolve(executable_relative)?;
        let process=crate::platform::OwnedProcess::launch(&executable,args,pins.root(),environment)?;
        Ok(Self{process,_pins:pins})
    }
    pub fn identity(&self)->OwnedIdentity{OwnedIdentity{root_pid:self.process.pid,created_filetime:self.process.created_filetime}}
    pub fn take_output(&mut self)->Result<(File,File),&'static str>{self.process.take_output()}
    pub fn alive(&self)->bool{self.process.alive()}
    pub fn send_shutdown(&mut self)->Result<(),&'static str>{self.write_stdin(b"shutdown\n")}
    /// Trusted caller bytes only: JSON-RPC/negative parser probes are not renderer commands.
    pub fn write_stdin(&mut self,bytes:&[u8])->Result<(),&'static str>{
        let pipe=self.process.stdin.as_mut().ok_or("native_stdin_closed")?;
        pipe.write_all(bytes).and_then(|_|pipe.flush()).map_err(|_|"native_stdin_write_failed")
    }
    pub fn take_stdin(&mut self)->Result<File,&'static str>{self.process.take_stdin()}
    pub fn close_stdin(&mut self){self.process.close_stdin();}
    pub fn wait_exit(&self,milliseconds:u32)->Result<Option<u32>,&'static str>{self.process.wait_exit(milliseconds)}
    pub fn owned_pids(&self)->Result<Vec<u32>,&'static str>{self.process.job_pids()}
    pub fn owns_listener(&self,port:u16)->Result<bool,&'static str>{crate::platform::owns_listener(&self.process,port)}
    pub fn force_owned(&self)->Result<Option<u32>,&'static str>{self.process.force()}
}
