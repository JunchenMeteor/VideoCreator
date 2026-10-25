//! Trusted installation launch, separate from IPC. No secret data is serialized.
use std::{fs,io::{Read,Write},path::{Path,PathBuf},sync::{Arc,atomic::{AtomicBool,Ordering}},time::{Duration,Instant}};
use serde::Deserialize;
use serde_json::Value;
use sha2::{Digest,Sha256};
use crate::{resource_pins::{PinnedFile,ResourcePins},route_contract::random_id,transport::Connection};

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Installation {
    format:String,launcher_mode:String,executable:String,source_root:Option<String>,files:Vec<PinnedFile>,
    ffmpeg:Option<String>,ffprobe:Option<String>,
    artifact_version:Option<String>,bootstrap:Option<String>,bootstrap_archive:Option<String>,load_policy:Option<String>,load_policy_sha256:Option<String>,
    migrations_directory:Option<String>,migrations_files:Option<Vec<String>>,backend_snapshot_sha256:Option<String>,contract_freeze_sha256:Option<String>,
}
pub struct LaunchResources { pub pins:Arc<ResourcePins>,startup:Option<crate::native_startup::StartupBinding>,executable:PathBuf,python_source:Option<PathBuf>,indexed:Option<crate::load_policy::IndexedPolicy>,ffmpeg:Option<PathBuf>,ffprobe:Option<PathBuf> }
impl LaunchResources {
    #[cfg(windows)]
    pub(crate) fn assert_qualification_profiles(&self,record:&crate::qualification_record::QualificationRecord)->Result<(),&'static str>{
        self.indexed.as_ref().ok_or("qualification_indexed_policy_required")?.assert_qualification_profiles(record,&self.pins)
    }
    #[cfg(windows)]
    pub(crate) fn hold_setup_api_continuation(&self,prepared:&crate::load_policy::PreparedLaunch,record:&crate::qualification_record::QualificationRecord)->Result<crate::load_policy::SetupApiContinuation,&'static str>{
        self.indexed.as_ref().ok_or("qualification_indexed_policy_required")?.hold_setup_api_continuation(prepared,&self.pins,record)
    }
    /// Trusted composition consumer: original guards come from the private
    /// installed/current lookup. This is not a renderer/config factory.
    pub fn load_installed(installed:Arc<crate::native_installation::NativeInstallationGuards>,instance_id:&str)->Result<Self,&'static str>{
        Self::load_installed_inner(installed,Some(instance_id))
    }
    /// Pre-API identity initialization uses the same held payload and index,
    /// without manufacturing the service StartupBinding's unknown instance.
    pub(crate) fn load_setup_installed(installed:Arc<crate::native_installation::NativeInstallationGuards>)->Result<Self,&'static str>{
        Self::load_installed_inner(installed,None)
    }
    fn load_installed_inner(installed:Arc<crate::native_installation::NativeInstallationGuards>,instance_id:Option<&str>)->Result<Self,&'static str>{
        let bytes=installed.manifest_bytes()?;
        let expected=option_env!("VIDEO_CREATOR_NATIVE_ENGINE_MANIFEST_SHA256").ok_or("native_runtime_unavailable")?;
        if format!("{:x}",Sha256::digest(&bytes))!=expected{return Err("native_installation_integrity_failed");}
        let install:Installation=serde_json::from_slice(&bytes).map_err(|_|"native_installation_invalid")?;
        if install.format!="native-engine-installation-v2-candidate"||install.launcher_mode!="indexed_python"||install.source_root.is_some()
            ||install.ffmpeg.is_some()!=install.ffprobe.is_some()||install.bootstrap.as_deref()!=Some("Bootstrap/IndexedBootstrap.py")||install.bootstrap_archive.as_deref()!=Some("Bootstrap/BaseStdlib.zip"){return Err("native_installation_invalid");}
        let pins=installed.payload.clone();
        let mut expected_files=install.files.clone();expected_files.push(PinnedFile{relative_path:"InstallationManifest.json".into(),bytes:bytes.len()as u64,sha256:expected.into()});
        expected_files.sort_unstable_by(|a,b|a.relative_path.cmp(&b.relative_path));
        if expected_files.len()!=installed.inputs.expected_files.len()||!expected_files.iter().zip(&installed.inputs.expected_files).all(|(a,b)|a.relative_path==b.relative_path&&a.bytes==b.bytes&&a.sha256==b.sha256){return Err("native_installation_membership_mismatch");}
        let executable=pins.resolve(&install.executable)?;
        let indexed=crate::load_policy::IndexedPolicy::load(&pins,&install.files,install.load_policy.as_deref().ok_or("native_installation_invalid")?,install.load_policy_sha256.as_deref().ok_or("native_installation_invalid")?,
            install.artifact_version.as_deref().ok_or("native_installation_invalid")?,install.backend_snapshot_sha256.as_deref().ok_or("native_installation_invalid")?,install.contract_freeze_sha256.as_deref().ok_or("native_installation_invalid")?,
            install.migrations_directory.as_deref().ok_or("native_installation_invalid")?,install.migrations_files.as_ref().ok_or("native_installation_invalid")?)?;
        let ffmpeg=install.ffmpeg.map(|name|pins.resolve(&name)).transpose()?;let ffprobe=install.ffprobe.map(|name|pins.resolve(&name)).transpose()?;
        let startup=instance_id.map(|instance|crate::native_startup::StartupBinding::from_installation(installed,instance)).transpose()?;
        Ok(Self{pins,startup,executable,python_source:None,indexed:Some(indexed),ffmpeg,ffprobe})
    }
    pub fn load(resource_directory:&Path)->Result<Self,&'static str>{
        // These values are supplied by the trusted build, never runtime renderer/env input.
        let manifest=if cfg!(debug_assertions){
            option_env!("VIDEO_CREATOR_NATIVE_ENGINE_MANIFEST").map(PathBuf::from).unwrap_or_else(||resource_directory.join("Engine/InstallationManifest.json"))
        }else{resource_directory.join("Engine/InstallationManifest.json")};
        let expected=option_env!("VIDEO_CREATOR_NATIVE_ENGINE_MANIFEST_SHA256").ok_or("native_runtime_unavailable")?;
        let bytes=fs::read(&manifest).map_err(|_|"native_runtime_unavailable")?;
        if bytes.len()>16*1024*1024||format!("{:x}",Sha256::digest(&bytes))!=expected{return Err("native_installation_integrity_failed");}
        let install:Installation=serde_json::from_slice(&bytes).map_err(|_|"native_installation_invalid")?;
        let v2=install.format=="native-engine-installation-v2-candidate"&&install.launcher_mode=="indexed_python";
        let dev_v1=cfg!(debug_assertions)&&install.format=="native-engine-installation-v1-candidate"&&["engine_standalone","python_source"].contains(&install.launcher_mode.as_str());
        if (!v2&&!dev_v1)||install.ffmpeg.is_some()!=install.ffprobe.is_some(){return Err("native_installation_invalid");}
        let root=manifest.parent().ok_or("native_installation_invalid")?;
        let pins=Arc::new(ResourcePins::hold(root,&install.files)?);
        let executable=pins.resolve(&install.executable)?;
        let indexed=if v2{
            if install.source_root.is_some()||install.bootstrap.as_deref()!=Some("Bootstrap/IndexedBootstrap.py")||install.bootstrap_archive.as_deref()!=Some("Bootstrap/BaseStdlib.zip"){return Err("native_installation_invalid");}
            Some(crate::load_policy::IndexedPolicy::load(&pins,&install.files,install.load_policy.as_deref().ok_or("native_installation_invalid")?,install.load_policy_sha256.as_deref().ok_or("native_installation_invalid")?,install.artifact_version.as_deref().ok_or("native_installation_invalid")?,install.backend_snapshot_sha256.as_deref().ok_or("native_installation_invalid")?,install.contract_freeze_sha256.as_deref().ok_or("native_installation_invalid")?,install.migrations_directory.as_deref().ok_or("native_installation_invalid")?,install.migrations_files.as_ref().ok_or("native_installation_invalid")?)?)
        }else{None};
        let python_source=if install.launcher_mode=="python_source"{
            let relative=install.source_root.ok_or("native_installation_invalid")?;
            let source=pins.resolve(&format!("{relative}/video_creator/cli/main.py"))?;
            Some(source.parent().and_then(Path::parent).and_then(Path::parent).ok_or("native_installation_invalid")?.to_owned())
        }else{if install.source_root.is_some(){return Err("native_installation_invalid");}None};
        let ffmpeg=install.ffmpeg.map(|p|pins.resolve(&p)).transpose()?;
        let ffprobe=install.ffprobe.map(|p|pins.resolve(&p)).transpose()?;
        let startup=if v2{Some(crate::native_startup::StartupBinding::load(pins.clone())?)}else{None};
        Ok(Self{pins,startup,executable,python_source,indexed,ffmpeg,ffprobe})
    }
    #[cfg(windows)]
    pub fn launch_service_role(&self,role:crate::load_policy::ChildRole,instance:&Path,private_token:Option<&str>,arguments:Vec<String>)->Result<crate::native_startup::StartupOwnedChild,&'static str>{
        let prepared=self.prepare_role(role,instance,private_token,arguments)?;
        self.startup.as_ref().ok_or("native_startup_record_required")?.launch(prepared,role,instance)
    }
    /// Trusted native consumers only. Independent Worker/MCP/ASR owners must
    /// retain the returned guard until their real child exits; no IPC spawn.
    pub fn prepare_role(&self,role:crate::load_policy::ChildRole,instance:&Path,private_token:Option<&str>,arguments:Vec<String>)->Result<crate::load_policy::PreparedLaunch,&'static str>{
        self.indexed.as_ref().ok_or("native_indexed_profile_required")?.prepare(self.pins.clone(),role,instance,private_token,arguments)
    }
}
#[derive(Clone)]
pub struct StopReceipt {pub classification:&'static str,pub actual_exit:Option<u32>,pub api_marker:bool,pub port_closed:bool,pub owned_tree_empty:bool}

#[cfg(windows)]
pub struct ApiRuntime {process:Arc<std::sync::Mutex<crate::platform::OwnedProcess>>,_startup:Option<crate::native_startup::StartupOwnedChild>,_resources:LaunchResources,_prepared:Option<crate::load_policy::PreparedLaunch>,pub connection:Arc<Connection>,base:tauri::Url,marker:Arc<AtomicBool>,outputs:std::sync::Mutex<Vec<std::thread::JoinHandle<()>>>}
#[cfg(windows)]
struct PendingApi {process:Option<Arc<std::sync::Mutex<crate::platform::OwnedProcess>>>,startup:Option<crate::native_startup::StartupOwnedChild>,prepared:Option<crate::load_policy::PreparedLaunch>,outputs:Vec<std::thread::JoinHandle<()>>}
#[cfg(windows)]
impl Drop for PendingApi {
    fn drop(&mut self){
        if let Some(process)=self.process.take(){let owned=process.lock().unwrap_or_else(|p|p.into_inner());retain_until_terminal(&owned);drop(owned);drop(process);}
        for reader in self.outputs.drain(..){let _=reader.join();}
    }
}
#[cfg(windows)]
fn retain_until_terminal(process:&crate::platform::OwnedProcess){
    // A timeout/query error cannot release the source guard. Use only the
    // owned Job handle, retaining both the installation and observation files.
    let _=process.force();
    loop{if process.wait_exit(1000).is_ok_and(|exit|exit.is_some())&&process.job_pids().is_ok_and(|pids|pids.is_empty()){break;}std::thread::sleep(Duration::from_millis(50));}
}
#[cfg(windows)]
impl Drop for ApiRuntime {
    fn drop(&mut self){let process=self.process.lock().unwrap_or_else(|poisoned|poisoned.into_inner());retain_until_terminal(&process);drop(process);let readers=self.outputs.get_mut().unwrap_or_else(|poisoned|poisoned.into_inner());for reader in readers.drain(..){let _=reader.join();}}
}
#[cfg(windows)]
fn line_reader(mut file:fs::File,callback:impl Fn(&[u8])+Send+'static)->std::thread::JoinHandle<()>{
    std::thread::spawn(move||{let mut bytes=[0;512];let mut line=Vec::new();let mut overflow=false;
        while let Ok(count)=file.read(&mut bytes){if count==0{break;}for byte in &bytes[..count]{
            if *byte==b'\n'{if !overflow{callback(&line);}line.clear();overflow=false;}
            else if !overflow{if line.len()>=4096{line.clear();overflow=true;}else{line.push(*byte);}}
        }}
    })
}
#[cfg(windows)]
impl ApiRuntime {
    pub async fn launch(resources:LaunchResources,instance:&Path)->Result<Self,&'static str>{
        if !instance.is_absolute(){return Err("native_instance_invalid");}
        let contract=crate::route_contract::Contract::load()?;
        let bearer=random_id()?;let mut args=Vec::new();
        if resources.python_source.is_some(){args.extend(["-B","-X","utf8","-m","video_creator.cli.main"].map(str::to_owned));}
        args.extend(["serve".into(),"--data-dir".into(),crate::load_policy::text(instance)?,"--host".into(),"127.0.0.1".into(),"--port".into(),"0".into(),"--allowed-host".into(),"127.0.0.1".into(),"--native-origin".into(),"http://tauri.localhost".into(),"--control-stdin".into()]);
        if let(Some(ffmpeg),Some(ffprobe))=(&resources.ffmpeg,&resources.ffprobe){args.extend(["--ffmpeg".into(),crate::load_policy::text(ffmpeg)?,"--ffprobe".into(),crate::load_policy::text(ffprobe)?]);}
        let(_,mut environment)=crate::load_policy::trusted_system_environment()?;
        let temp=instance.join("Temp");fs::create_dir_all(&temp).map_err(|_|"native_instance_invalid")?;
        environment.extend([("TEMP".into(),temp.as_os_str().to_owned()),("TMP".into(),temp.as_os_str().to_owned()),("VIDEO_CREATOR_API_TOKEN".into(),bearer.clone().into()),("PYTHONUTF8".into(),"1".into()),("PYTHONDONTWRITEBYTECODE".into(),"1".into())]);
        if let Some(source)=&resources.python_source{environment.push(("PYTHONPATH".into(),source.as_os_str().to_owned()));}
        let mut prepared=if resources.indexed.is_some(){Some(resources.prepare_role(crate::load_policy::ChildRole::Api,instance,Some(&bearer),args.clone())?)}else{None};
        let mut startup=None;
        let process=if let Some(launch)=prepared.take(){
            let owner=resources.startup.as_ref().ok_or("native_startup_record_required")?.launch(launch,crate::load_policy::ChildRole::Api,instance)?;
            let process=owner.process();startup=Some(owner);process
        }else{Arc::new(std::sync::Mutex::new(crate::platform::OwnedProcess::launch(&resources.executable,&args,resources.pins.root(),&environment)?))};
        let mut pending=PendingApi{process:Some(process),startup,prepared,outputs:Vec::new()};
        let(stdout,stderr)=pending.process.as_ref().ok_or("native_engine_unowned")?.lock().map_err(|_|"native_engine_lock_failed")?.take_output()?;let(marker,ready)=(Arc::new(AtomicBool::new(false)),std::sync::mpsc::sync_channel(1));
        let(sender,receiver)=ready;let output=line_reader(stdout,move|line|{
            if let Ok(value)=serde_json::from_slice::<Value>(line){
                if value["event"]=="ready"&&value.as_object().is_some_and(|m|m.len()==3&&m.contains_key("base_url")&&m.contains_key("instance_id")){
                    let _=sender.try_send(value);
                }
            }
        });
        let stopped=marker.clone();let error_output=line_reader(stderr,move|line|{if line==br#"{"event":"api_stopped","scope":"api"}"#{stopped.store(true,Ordering::Release);}});
        pending.outputs=vec![output,error_output];
        let value=tauri::async_runtime::spawn_blocking(move||receiver.recv_timeout(Duration::from_secs(15))).await.map_err(|_|"native_engine_ready_timeout")?.map_err(|_|"native_engine_ready_timeout")?;
        let base=tauri::Url::parse(value["base_url"].as_str().ok_or("native_engine_ready_invalid")?).map_err(|_|"native_engine_ready_invalid")?;
        let instance_id=value["instance_id"].as_str().ok_or("native_engine_ready_invalid")?.to_owned();
        let connection=Connection::verified(base.clone(),bearer,instance_id)?;
        {
            let process=pending.process.as_ref().ok_or("native_engine_unowned")?.lock().map_err(|_|"native_engine_lock_failed")?;
            if !process.alive()||!crate::platform::owns_listener(&process,base.port().ok_or("native_engine_ready_invalid")?)?{return Err("native_engine_port_unowned");}
        }
        connection.verify_health(&contract).await?;
        {
            let process=pending.process.as_ref().ok_or("native_engine_unowned")?.lock().map_err(|_|"native_engine_lock_failed")?;
            if !process.alive()||!crate::platform::owns_listener(&process,base.port().ok_or("native_engine_ready_invalid")?)?{return Err("native_engine_port_unowned");}
        }
        Ok(Self{process:pending.process.take().ok_or("native_engine_unowned")?,_startup:pending.startup.take(),_resources:resources,_prepared:pending.prepared.take(),connection:Arc::new(connection),base,marker,outputs:std::sync::Mutex::new(std::mem::take(&mut pending.outputs))})
    }
    pub fn alive(&self)->bool{self.process.lock().is_ok_and(|p|p.alive())}
    pub fn stop(&self)->StopReceipt{
        self.connection.invalidate();
        let mut receipt=StopReceipt{classification:"error",actual_exit:None,api_marker:false,port_closed:false,owned_tree_empty:false};
        if let Ok(mut process)=self.process.lock(){
            let sent=process.stdin.as_mut().is_some_and(|pipe|pipe.write_all(b"shutdown\n").and_then(|_|pipe.flush()).is_ok());
            if sent{receipt.actual_exit=process.wait_exit(15000).ok().flatten();}
            if receipt.actual_exit.is_none(){receipt.actual_exit=process.force().ok().flatten();receipt.classification="forced";}
            let until=Instant::now()+Duration::from_secs(3);
            while Instant::now()<until{
                receipt.owned_tree_empty=process.job_pids().is_ok_and(|p|p.is_empty());
                receipt.port_closed=crate::platform::port_closed(self.base.port().unwrap_or(0));
                if receipt.owned_tree_empty&&receipt.port_closed{break;}std::thread::sleep(Duration::from_millis(25));
            }
            receipt.api_marker=self.marker.load(Ordering::Acquire);
            if sent&&receipt.actual_exit==Some(0)&&receipt.api_marker&&receipt.port_closed&&receipt.owned_tree_empty&&receipt.classification!="forced"{receipt.classification="normal";}
            if !receipt.owned_tree_empty{let _=process.force();receipt.classification="forced";receipt.owned_tree_empty=process.job_pids().is_ok_and(|p|p.is_empty());}
        }
        if let Ok(mut readers)=self.outputs.lock(){for reader in readers.drain(..){let _=reader.join();}}
        receipt
    }
}
#[cfg(not(windows))]
pub struct ApiRuntime;
