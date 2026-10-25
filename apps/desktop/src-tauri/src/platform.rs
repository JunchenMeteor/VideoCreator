//! Windows ownership primitive, not yet wired to the pending formal API contract.
//! No renderer command surface, credential DTO or arbitrary process API exists.
pub(crate) mod owned_launch {
    use std::{ffi::OsString,io::Write,path::Path};
    mod sealed {pub trait Lifecycle{}}
    #[cfg(test)] impl<T> sealed::Lifecycle for T{}
    #[cfg(all(windows,not(test)))] impl sealed::Lifecycle for super::windows_owned::Win32Lifecycle{}
    pub(crate) struct LaunchSpec<'a>{pub executable:&'a Path,pub args:&'a [String],pub cwd:&'a Path,pub environment:&'a [(OsString,OsString)]}
    pub(crate) trait NativeLifecyclePort:sealed::Lifecycle {
        type Created;
        type Stdin:Write;
        type Owned;
        fn create(&mut self,spec:&LaunchSpec<'_>)->Result<Self::Created,&'static str>;
        fn assign(&mut self,created:&Self::Created)->Result<(),&'static str>;
        fn identity(&mut self,created:&Self::Created)->Result<(u32,u64),&'static str>;
        fn stdin<'a>(&mut self,created:&'a mut Self::Created)->&'a mut Self::Stdin;
        fn resume(&mut self,created:&Self::Created)->Result<(),&'static str>;
        fn terminate(&mut self,created:&Self::Created)->(bool,bool);
        fn terminal(&mut self,created:&Self::Created)->Result<bool,&'static str>;
        fn active(&mut self,created:&Self::Created)->Result<u32,&'static str>;
        fn pause(&mut self){std::thread::sleep(std::time::Duration::from_millis(50));}
        // Infallible move of this exact owned bundle, never a PID lookup.
        fn transfer(&mut self,created:Self::Created,identity:(u32,u64))->Self::Owned;
    }
    struct PostCreateGuard<'a,P:NativeLifecyclePort>{port:&'a mut P,created:Option<P::Created>}
    impl<P:NativeLifecyclePort> Drop for PostCreateGuard<'_,P>{
        fn drop(&mut self){if let Some(created)=self.created.as_ref(){loop{
            let _requests=self.port.terminate(created);
            // Evaluate both observations. UNKNOWN or a live descendant keeps
            // the exact bundle and the caller's PreparedLaunch on this stack.
            let terminal=self.port.terminal(created);
            let active=self.port.active(created);
            if terminal==Ok(true)&&active==Ok(0){break;}
            self.port.pause();
        }}}
    }
    pub(crate) fn launch<P:NativeLifecyclePort>(port:&mut P,spec:&LaunchSpec<'_>,before_resume:impl FnOnce(u32,u64,&mut P::Stdin)->Result<(),&'static str>)->Result<P::Owned,&'static str>{
        let created=port.create(spec)?;
        let mut pending=PostCreateGuard{port,created:Some(created)};
        let created=pending.created.as_ref().ok_or("native_process_unowned")?;
        pending.port.assign(created)?;
        let identity=pending.port.identity(created)?;
        before_resume(identity.0,identity.1,pending.port.stdin(pending.created.as_mut().ok_or("native_process_unowned")?))?;
        pending.port.resume(pending.created.as_ref().ok_or("native_process_unowned")?)?;
        let created=pending.created.take().ok_or("native_process_unowned")?;
        Ok(pending.port.transfer(created,identity))
    }
}
#[cfg(windows)]
mod windows_owned {
    use std::{ffi::{OsStr,OsString},fs::File,mem::{size_of,size_of_val,zeroed},os::windows::{ffi::OsStrExt,io::FromRawHandle},path::Path,ptr::{null,null_mut}};
    use windows_sys::Win32::{
        Foundation::{CloseHandle,FILETIME,HANDLE,HANDLE_FLAG_INHERIT,SetHandleInformation,WAIT_OBJECT_0,WAIT_TIMEOUT},
        Security::SECURITY_ATTRIBUTES,
        System::{JobObjects::{AssignProcessToJobObject,CreateJobObjectW,JobObjectBasicProcessIdList,JobObjectBasicAccountingInformation,JobObjectExtendedLimitInformation,JOBOBJECT_BASIC_ACCOUNTING_INFORMATION,JOBOBJECT_BASIC_PROCESS_ID_LIST,JOBOBJECT_EXTENDED_LIMIT_INFORMATION,JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,QueryInformationJobObject,SetInformationJobObject,TerminateJobObject},
            Pipes::CreatePipe,
            Threading::{CreateProcessW,CREATE_NO_WINDOW,CREATE_SUSPENDED,CREATE_UNICODE_ENVIRONMENT,DeleteProcThreadAttributeList,EXTENDED_STARTUPINFO_PRESENT,GetExitCodeProcess,GetProcessTimes,InitializeProcThreadAttributeList,PROCESS_INFORMATION,PROC_THREAD_ATTRIBUTE_HANDLE_LIST,ResumeThread,STARTF_USESTDHANDLES,STARTUPINFOEXW,TerminateProcess,UpdateProcThreadAttribute,WaitForSingleObject}},
    };
    struct Handle(HANDLE);
    // Only this owned wrapper uses its stable OS handles; no PID command lookup.
    unsafe impl Send for Handle {}
    impl Drop for Handle{fn drop(&mut self){if !self.0.is_null(){unsafe{CloseHandle(self.0);}}}}
    impl Handle{fn take(mut self)->HANDLE{let h=self.0;self.0=null_mut();h}}
    use super::owned_launch::{LaunchSpec,NativeLifecyclePort};
    fn wide(value:&OsStr)->Result<Vec<u16>,&'static str>{let mut v:Vec<u16>=value.encode_wide().collect();if v.contains(&0){return Err("native_argument_invalid");}v.push(0);Ok(v)}
    fn quote(value:&str)->Result<String,&'static str>{
        if value.contains('\0'){return Err("native_argument_invalid");}
        let mut out=String::from("\"");let mut slashes=0;
        for c in value.chars(){if c=='\\'{slashes+=1;continue;}if c=='\"'{out.extend(std::iter::repeat_n('\\',slashes*2+1));out.push(c);}else{out.extend(std::iter::repeat_n('\\',slashes));out.push(c);}slashes=0;}
        out.extend(std::iter::repeat_n('\\',slashes*2));out.push('\"');Ok(out)
    }
    fn pipe(parent_read:bool)->Result<(Handle,Handle),&'static str>{
        let(mut read,mut write)=(null_mut(),null_mut());let attrs=SECURITY_ATTRIBUTES{nLength:size_of::<SECURITY_ATTRIBUTES>() as u32,lpSecurityDescriptor:null_mut(),bInheritHandle:1};
        if unsafe{CreatePipe(&mut read,&mut write,&attrs,4096)}==0{return Err("native_pipe_failed");}
        let(read,write)=(Handle(read),Handle(write));let parent=if parent_read{read.0}else{write.0};
        if unsafe{SetHandleInformation(parent,HANDLE_FLAG_INHERIT,0)}==0{return Err("native_pipe_failed");}Ok((read,write))
    }

    pub(crate) struct Created {
        job:Handle,process:Handle,thread:Handle,pid:u32,parent_stdin:File,
        input_read:Handle,output_read:Handle,output_write:Handle,error_read:Handle,error_write:Handle,
    }
    pub(crate) struct Win32Lifecycle;
    impl NativeLifecyclePort for Win32Lifecycle {
        type Created=Created;type Stdin=File;type Owned=OwnedProcess;
        fn create(&mut self,spec:&LaunchSpec<'_>)->Result<Created,&'static str>{
            let(executable,args,cwd,env)=(spec.executable,spec.args,spec.cwd,spec.environment);
            if !executable.is_absolute()||!cwd.is_absolute(){return Err("native_resource_invalid");}
            let app=wide(executable.as_os_str())?;let dir=wide(cwd.as_os_str())?;
            let mut command=quote(executable.to_str().ok_or("native_resource_invalid")?)?;for arg in args{command.push(' ');command.push_str(&quote(arg)?);}let mut command=wide(OsStr::new(&command))?;
            let mut environment=env.to_vec();environment.sort_by_key(|(k,_)|k.to_string_lossy().to_uppercase());let mut block=Vec::new();
            for(key,value)in &environment{if key.to_string_lossy().contains('='){return Err("native_environment_invalid");}let mut item=key.clone();item.push("=");item.push(value);block.extend(wide(&item)?);}block.push(0);if block.len()==1{block.push(0);}
            let job=Handle(unsafe{CreateJobObjectW(null(),null())});if job.0.is_null(){return Err("native_job_failed");}
            let mut limits:JOBOBJECT_EXTENDED_LIMIT_INFORMATION=unsafe{zeroed()};limits.BasicLimitInformation.LimitFlags=JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
            if unsafe{SetInformationJobObject(job.0,JobObjectExtendedLimitInformation,&limits as *const _ as _,size_of_val(&limits)as u32)}==0{return Err("native_job_failed");}
            let(input_read,input_write)=pipe(false)?;let(output_read,output_write)=pipe(true)?;let(error_read,error_write)=pipe(true)?;
            let mut size=0;unsafe{InitializeProcThreadAttributeList(null_mut(),1,0,&mut size);}if size==0||size>65536{return Err("native_handle_list_failed");}
            let mut storage=vec![0usize;(size+size_of::<usize>()-1)/size_of::<usize>()];let attrs=storage.as_mut_ptr() as _;
            if unsafe{InitializeProcThreadAttributeList(attrs,1,0,&mut size)}==0{return Err("native_handle_list_failed");}
            let inherited=[input_read.0,output_write.0,error_write.0];
            if unsafe{UpdateProcThreadAttribute(attrs,0,PROC_THREAD_ATTRIBUTE_HANDLE_LIST as usize,inherited.as_ptr()as _,size_of_val(&inherited),null_mut(),null())}==0{unsafe{DeleteProcThreadAttributeList(attrs);}return Err("native_handle_list_failed");}
            let mut startup:STARTUPINFOEXW=unsafe{zeroed()};startup.StartupInfo.cb=size_of::<STARTUPINFOEXW>()as u32;startup.StartupInfo.dwFlags=STARTF_USESTDHANDLES;
            startup.StartupInfo.hStdInput=input_read.0;startup.StartupInfo.hStdOutput=output_write.0;startup.StartupInfo.hStdError=error_write.0;startup.lpAttributeList=attrs;
            let mut info:PROCESS_INFORMATION=unsafe{zeroed()};
            let parent_stdin=unsafe{File::from_raw_handle(input_write.take())};
            let created=unsafe{CreateProcessW(app.as_ptr(),command.as_mut_ptr(),null(),null(),1,CREATE_SUSPENDED|CREATE_NO_WINDOW|CREATE_UNICODE_ENVIRONMENT|EXTENDED_STARTUPINFO_PRESENT,block.as_ptr()as _,dir.as_ptr(),&startup.StartupInfo,&mut info)};
            if created==0{unsafe{DeleteProcThreadAttributeList(attrs);}return Err("native_process_create_failed");}
            // After successful Create, only non-fallible ownership moves and
            // attribute-list release remain before the shared guard is armed.
            let bundle=Created{job,process:Handle(info.hProcess),thread:Handle(info.hThread),pid:info.dwProcessId,parent_stdin,input_read,output_read,output_write,error_read,error_write};
            unsafe{DeleteProcThreadAttributeList(attrs);}
            Ok(bundle)
        }
        fn assign(&mut self,created:&Created)->Result<(),&'static str>{
            if unsafe{AssignProcessToJobObject(created.job.0,created.process.0)}==0{Err("native_job_assignment_failed")}else{Ok(())}
        }
        fn identity(&mut self,created:&Created)->Result<(u32,u64),&'static str>{
            let(mut birth,mut end,mut kernel,mut user):(FILETIME,FILETIME,FILETIME,FILETIME)=unsafe{zeroed()};
            if unsafe{GetProcessTimes(created.process.0,&mut birth,&mut end,&mut kernel,&mut user)}==0{return Err("native_creation_identity_failed");}
            Ok((created.pid,((birth.dwHighDateTime as u64)<<32)|birth.dwLowDateTime as u64))
        }
        fn stdin<'a>(&mut self,created:&'a mut Created)->&'a mut File{&mut created.parent_stdin}
        fn resume(&mut self,created:&Created)->Result<(),&'static str>{
            if unsafe{ResumeThread(created.thread.0)}==u32::MAX{Err("native_process_resume_failed")}else{Ok(())}
        }
        fn terminate(&mut self,created:&Created)->(bool,bool){unsafe{(TerminateJobObject(created.job.0,1)!=0,TerminateProcess(created.process.0,1)!=0)}}
        fn terminal(&mut self,created:&Created)->Result<bool,&'static str>{
            match unsafe{WaitForSingleObject(created.process.0,5000)}{WAIT_OBJECT_0=>Ok(true),WAIT_TIMEOUT=>Ok(false),_=>Err("native_wait_failed")}
        }
        fn active(&mut self,created:&Created)->Result<u32,&'static str>{
            let mut accounting:JOBOBJECT_BASIC_ACCOUNTING_INFORMATION=unsafe{zeroed()};
            if unsafe{QueryInformationJobObject(created.job.0,JobObjectBasicAccountingInformation,&mut accounting as *mut _ as _,size_of_val(&accounting)as u32,null_mut())}==0{Err("native_job_query_failed")}else{Ok(accounting.ActiveProcesses)}
        }
        fn transfer(&mut self,created:Created,identity:(u32,u64))->OwnedProcess{
            let Created{job,process,thread,pid:_,parent_stdin,input_read,output_read,output_write,error_read,error_write}=created;
            drop(thread);drop(input_read);drop(output_write);drop(error_write);
            OwnedProcess{job,process,pid:identity.0,created_filetime:identity.1,stdin:Some(parent_stdin),stdout:Some(unsafe{File::from_raw_handle(output_read.take())}),stderr:Some(unsafe{File::from_raw_handle(error_read.take())})}
        }
    }
    pub struct OwnedProcess{
        job:Handle,process:Handle,
        pub pid:u32,pub created_filetime:u64,pub stdin:Option<File>,
        stdout:Option<File>,stderr:Option<File>,
    }
    impl OwnedProcess{
        /// Executable and argv must be fixed internally from verified resources.
        /// App setup does not call this until the formal backend contract exists.
        pub fn launch(executable:&Path,args:&[String],cwd:&Path,env:&[(OsString,OsString)])->Result<Self,&'static str>{
            Self::launch_with_before_resume(executable,args,cwd,env,|_,_|Ok(()))
        }
        /// Trusted native lifecycle only. The hook never runs before Job ownership
        /// and the actual creation identity exist; no renderer callback exists.
        pub(crate) fn launch_with_before_resume(executable:&Path,args:&[String],cwd:&Path,env:&[(OsString,OsString)],before_resume:impl FnOnce(u32,u64)->Result<(),&'static str>)->Result<Self,&'static str>{
            Self::launch_with_before_resume_stdin(executable,args,cwd,env,|pid,creation,_|before_resume(pid,creation))
        }
        /// A single trusted owner may write its fixed bootstrap binding while
        /// the child is still suspended. Not a renderer or arbitrary-frame API.
        pub(crate) fn launch_with_before_resume_stdin(executable:&Path,args:&[String],cwd:&Path,env:&[(OsString,OsString)],before_resume:impl FnOnce(u32,u64,&mut File)->Result<(),&'static str>)->Result<Self,&'static str>{
            let spec=LaunchSpec{executable,args,cwd,environment:env};
            super::owned_launch::launch(&mut Win32Lifecycle,&spec,before_resume)
        }
        pub fn take_output(&mut self)->Result<(File,File),&'static str>{Ok((self.stdout.take().ok_or("native_output_already_owned")?,self.stderr.take().ok_or("native_output_already_owned")?))}
        pub fn take_stdin(&mut self)->Result<File,&'static str>{self.stdin.take().ok_or("native_stdin_already_owned")}
        pub fn close_stdin(&mut self){self.stdin.take();}
        /// Checks the pipe's OS client PID against this exact process HANDLE
        /// and Job. A new OpenProcess(PID) is never ownership evidence.
        pub(crate) fn authority_peer_handle(&self,peer_pid:u32)->Result<HANDLE,&'static str>{
            use windows_sys::Win32::{System::Threading::GetProcessId,System::JobObjects::IsProcessInJob};
            if peer_pid!=self.pid||unsafe{GetProcessId(self.process.0)}!=self.pid{return Err("authority_peer_pid_mismatch");}
            let(mut birth,mut end,mut kernel,mut user):(FILETIME,FILETIME,FILETIME,FILETIME)=unsafe{zeroed()};
            if unsafe{GetProcessTimes(self.process.0,&mut birth,&mut end,&mut kernel,&mut user)}==0{return Err("authority_peer_creation_unknown");}
            if (((birth.dwHighDateTime as u64)<<32)|birth.dwLowDateTime as u64)!=self.created_filetime{return Err("authority_peer_creation_mismatch");}
            let mut in_job=0;
            if unsafe{IsProcessInJob(self.process.0,self.job.0,&mut in_job)}==0||in_job==0{return Err("authority_peer_job_unknown");}
            if self.wait_exit(0)?!=None{return Err("authority_peer_terminal");}
            Ok(self.process.0)
        }
        pub fn alive(&self)->bool{unsafe{WaitForSingleObject(self.process.0,0)==WAIT_TIMEOUT}}
        pub fn wait_exit(&self,ms:u32)->Result<Option<u32>,&'static str>{match unsafe{WaitForSingleObject(self.process.0,ms)}{WAIT_TIMEOUT=>Ok(None),WAIT_OBJECT_0=>{let mut code=0;if unsafe{GetExitCodeProcess(self.process.0,&mut code)}==0{Err("native_exit_query_failed")}else{Ok(Some(code))}},_=>Err("native_wait_failed")}}
        pub fn job_pids(&self)->Result<Vec<u32>,&'static str>{
            let size=size_of::<JOBOBJECT_BASIC_PROCESS_ID_LIST>()+128*size_of::<usize>();let mut data=vec![0usize;(size+size_of::<usize>()-1)/size_of::<usize>()];
            if unsafe{QueryInformationJobObject(self.job.0,JobObjectBasicProcessIdList,data.as_mut_ptr()as _,size as u32,null_mut())}==0{return Err("native_job_query_failed");}
            let list=unsafe{&*(data.as_ptr()as *const JOBOBJECT_BASIC_PROCESS_ID_LIST)};let count=list.NumberOfProcessIdsInList as usize;
            if count>128||list.NumberOfAssignedProcesses as usize!=count{return Err("native_job_tree_unconfirmed");}
            let pids=unsafe{std::slice::from_raw_parts(list.ProcessIdList.as_ptr(),count)};pids.iter().map(|p|u32::try_from(*p).map_err(|_|"native_job_pid_invalid")).collect()
        }
        pub fn force(&self)->Result<Option<u32>,&'static str>{if unsafe{TerminateJobObject(self.job.0,1)}==0{return Err("native_job_force_failed");}self.wait_exit(5000)}
    }
}
#[cfg(windows)]
pub use windows_owned::OwnedProcess;
#[cfg(windows)]
pub(crate) use windows_owned::Win32Lifecycle;

/// Actual listener ownership is an observation on the already-owned Job,
/// never permission to kill a process discovered by PID.
#[cfg(windows)]
pub fn owns_listener(process:&OwnedProcess,port:u16)->Result<bool,&'static str>{
    use windows_sys::Win32::{NetworkManagement::IpHelper::{GetExtendedTcpTable,MIB_TCPROW_OWNER_PID,TCP_TABLE_OWNER_PID_LISTENER},Networking::WinSock::AF_INET};
    let mut size=0;
    unsafe{GetExtendedTcpTable(std::ptr::null_mut(),&mut size,0,AF_INET as u32,TCP_TABLE_OWNER_PID_LISTENER,0);}
    if size<4||size>16*1024*1024{return Err("native_port_inspection_failed");}
    let mut bytes=vec![0u8;size as usize];
    if unsafe{GetExtendedTcpTable(bytes.as_mut_ptr()as _,&mut size,0,AF_INET as u32,TCP_TABLE_OWNER_PID_LISTENER,0)}!=0{return Err("native_port_inspection_failed");}
    let count=u32::from_ne_bytes(bytes[..4].try_into().map_err(|_|"native_port_inspection_failed")?)as usize;
    let width=std::mem::size_of::<MIB_TCPROW_OWNER_PID>();
    if 4usize.checked_add(count.checked_mul(width).ok_or("native_port_inspection_failed")?).is_none_or(|n|n>size as usize){return Err("native_port_inspection_failed");}
    let owned=process.job_pids()?;
    for row in 0..count{
        let value=unsafe{std::ptr::read_unaligned(bytes.as_ptr().add(4+row*width)as *const MIB_TCPROW_OWNER_PID)};
        if value.dwLocalAddr.to_ne_bytes()==[127,0,0,1]&&u16::from_be(value.dwLocalPort as u16)==port{return Ok(owned.contains(&value.dwOwningPid));}
    }Ok(false)
}
pub fn port_closed(port:u16)->bool{
    if port==0{return false;}
    matches!(std::net::TcpStream::connect_timeout(&std::net::SocketAddr::from(([127,0,0,1],port)),std::time::Duration::from_millis(250)),Err(error)if error.kind()==std::io::ErrorKind::ConnectionRefused)
}
