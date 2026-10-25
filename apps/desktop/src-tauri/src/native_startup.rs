//! Fixed installed startup input. No renderer factory or qualification issuer.
use std::{collections::BTreeSet,fs,sync::Arc};
#[cfg(windows)]
use std::{fs::{File,OpenOptions},io::Write,path::Path};
use serde::{Deserialize,Serialize};
use sha2::{Digest,Sha256};
use crate::resource_pins::{PinnedFile,ResourcePins};
#[cfg(windows)]
use crate::{load_policy::{ChildRole,PreparedLaunch},resource_authority::{AuthorityOwnedChild,FactsContext}};

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct InstalledBinding {
    format:String,instance_id:String,installed_native_image:String,
    registration_record:String,resource_manifest:String,runtime_manifest:String,
    engine_file_names:Vec<String>,
}
#[derive(Serialize)]
struct ChildBinding<'a> {
    format:&'static str,instance_id:&'a str,role:&'a str,
    installed_native_image:String,installed_native_image_sha256:&'a str,
    registration_sha256:&'a str,resource_manifest_sha256:&'a str,runtime_manifest_sha256:&'a str,
    expected_files:&'a [PinnedFile],engine_file_names:&'a [String],
}
pub struct StartupBinding {
    guard:Arc<ResourcePins>,
    instance_id:String,engine_file_names:Vec<String>,files:Vec<PinnedFile>,image:String,image_sha:String,
    registration_sha:String,resource_sha:String,runtime_sha:String,
    installed:Option<Arc<crate::native_installation::NativeInstallationGuards>>,
}
fn canonical_json(value:&serde_json::Value,out:&mut Vec<u8>)->Result<(),&'static str>{
    match value {
        serde_json::Value::Object(map)=>{
            out.push(b'{');let mut keys=map.keys().collect::<Vec<_>>();keys.sort_unstable();
            for(i,key)in keys.into_iter().enumerate(){if i!=0{out.push(b',');}
                out.extend(serde_json::to_vec(key).map_err(|_|"native_startup_record_invalid")?);out.push(b':');canonical_json(&map[key],out)?;}
            out.push(b'}');
        },
        serde_json::Value::Array(values)=>{out.push(b'[');for(i,value)in values.iter().enumerate(){if i!=0{out.push(b',');}canonical_json(value,out)?;}out.push(b']');},
        _=>out.extend(serde_json::to_vec(value).map_err(|_|"native_startup_record_invalid")?),
    }Ok(())
}
impl StartupBinding {
    /// The record and all referenced objects are independently held by the
    /// trusted installation. Locator.server is never an image trust source.
    pub fn load(pins:Arc<ResourcePins>)->Result<Self,&'static str>{
        let raw=fs::read(pins.resolve("NativeStartup.json")?).map_err(|_|"native_startup_record_unavailable")?;
        if raw.len()>1024*1024{return Err("native_startup_record_invalid");}
        let mut input:InstalledBinding=serde_json::from_slice(&raw).map_err(|_|"native_startup_record_invalid")?;
        if input.format!="native-installed-startup-v1-candidate"||input.instance_id.is_empty()
            ||input.instance_id.len()>128||input.instance_id.chars().any(char::is_control){return Err("native_startup_record_invalid");}
        let observation=pins.observe_all()?;pins.assert_current(&observation)?;
        let mut files=observation.files().to_vec();files.sort_unstable_by(|a,b|a.relative_path.cmp(&b.relative_path));
        let names=files.iter().map(|f|f.relative_path.as_str()).collect::<BTreeSet<_>>();
        let engine=input.engine_file_names.iter().map(String::as_str).collect::<BTreeSet<_>>();
        if engine.is_empty()||engine.len()!=input.engine_file_names.len()||!engine.is_subset(&names)||engine.len()==names.len(){return Err("native_startup_partition_invalid");}
        input.engine_file_names.sort_unstable();
        let identity=|name:&str|files.iter().find(|f|f.relative_path==name).map(|f|f.sha256.clone()).ok_or("native_startup_object_unpinned");
        let image_path=pins.resolve(&input.installed_native_image)?;
        let actual=std::env::current_exe().map_err(|_|"native_startup_image_unknown")?.canonicalize().map_err(|_|"native_startup_image_unknown")?;
        if actual!=image_path{return Err("native_startup_image_mismatch");}
        let image=crate::load_policy::text(&image_path)?;
        let image_sha=identity(&input.installed_native_image)?;
        let registration_sha=identity(&input.registration_record)?;
        let resource_sha=identity(&input.resource_manifest)?;
        let runtime_sha=identity(&input.runtime_manifest)?;
        drop(observation);
        Ok(Self{guard:pins,instance_id:input.instance_id,engine_file_names:input.engine_file_names,files,image,image_sha,registration_sha,resource_sha,runtime_sha,installed:None})
    }
    /// The real installed path receives the original independently held host,
    /// external receipt and Engine map. No host member/self-hash in payload.
    /// Backend must still authenticate current Owner/registration/qualification.
    pub fn from_installation(installed:Arc<crate::native_installation::NativeInstallationGuards>,instance_id:&str)->Result<Self,&'static str>{
        if instance_id.is_empty()||instance_id.len()>128||!instance_id.bytes().all(|byte|byte.is_ascii_alphanumeric()||b"_.:-".contains(&byte)){return Err("native_startup_record_invalid");}
        installed.image_is_current_process()?;
        let observation=installed.observe()?;installed.assert_current(&observation)?;drop(observation);
        let facts=&installed.inputs;
        Ok(Self{guard:installed.payload.clone(),instance_id:instance_id.into(),engine_file_names:facts.engine_file_names.clone(),files:facts.expected_files.clone(),image:crate::load_policy::text(&installed.host_path)?,image_sha:facts.installed_native_image_sha256.clone(),
            registration_sha:facts.registration_sha256.clone(),resource_sha:facts.resource_manifest_sha256.clone(),runtime_sha:facts.runtime_manifest_sha256.clone(),installed:Some(installed)})
    }
    #[cfg(windows)]
    pub fn launch(&self,mut prepared:PreparedLaunch,role:ChildRole,instance:&Path)->Result<StartupOwnedChild,&'static str>{
        if matches!(role,ChildRole::Asr){return Err("native_startup_service_role_invalid");}
        if !Arc::ptr_eq(&self.guard,&prepared.guard){return Err("native_startup_guard_mismatch");}
        if let Some(installed)=&self.installed{let observation=installed.observe()?;installed.assert_current(&observation)?;}
        let profile=prepared.args.iter().position(|arg|arg=="--profile").and_then(|i|prepared.args.get(i+1));
        if profile.map(String::as_str)!=Some(role.name()){return Err("native_startup_service_role_invalid");}
        if !instance.is_absolute(){return Err("native_instance_invalid");}
        let binding=ChildBinding{format:"native-startup-binding-v1",instance_id:&self.instance_id,role:role.name(),
            installed_native_image:self.image.clone(),installed_native_image_sha256:&self.image_sha,
            registration_sha256:&self.registration_sha,resource_manifest_sha256:&self.resource_sha,runtime_manifest_sha256:&self.runtime_sha,
            expected_files:&self.files,engine_file_names:&self.engine_file_names};
        let compact_files=serde_json::to_vec(&self.files).map_err(|_|"native_startup_record_invalid")?;
        // NativeLaunchContext's existing Python default separators add one
        // space after each of the 3 colons/2 object commas and each row comma.
        let context_size=compact_files.len().checked_add(self.files.len().checked_mul(6).ok_or("native_startup_map_oversized")?).and_then(|v|v.checked_sub(1)).ok_or("native_startup_map_oversized")?;
        if context_size>32*1024*1024-16384{return Err("native_startup_map_oversized");}
        let mut raw=Vec::new();canonical_json(&serde_json::to_value(&binding).map_err(|_|"native_startup_record_invalid")?,&mut raw)?;
        if raw.len()>32*1024*1024{return Err("native_startup_map_oversized");}
        let temp=instance.join("Temp");let path=temp.join(format!("NativeStartup-{}.json",crate::resource_authority::private_startup_id()?));
        let mut file=OpenOptions::new().create_new(true).write(true).open(&path).map_err(|_|"native_startup_carrier_failed")?;
        file.write_all(&raw).and_then(|_|file.sync_all()).map_err(|_|"native_startup_carrier_failed")?;drop(file);
        use std::os::windows::fs::OpenOptionsExt;
        let held=OpenOptions::new().read(true).share_mode(1).custom_flags(0x0020_0000).open(&path).map_err(|_|"native_startup_carrier_failed")?;
        // Binding is data, never a module selector. This guard remains through
        // every failed launch cleanup and the original child's Job terminal.
        if held.metadata().map_err(|_|"native_startup_carrier_failed")?.len()!=raw.len()as u64
            ||fs::read(&path).map_err(|_|"native_startup_carrier_failed")?!=raw{return Err("native_startup_carrier_changed");}
        let separator=prepared.args.iter().position(|v|v=="--").ok_or("native_startup_bootstrap_invalid")?;
        prepared.args.splice(separator..separator,["--native-startup-binding".into(),crate::load_policy::text(&path)?,"--native-startup-binding-sha256".into(),format!("{:x}",Sha256::digest(&raw))]);
        let context=FactsContext{instance_id:self.instance_id.clone(),role:role.name().into(),registration_sha256:self.registration_sha.clone(),resource_manifest_sha256:self.resource_sha.clone(),runtime_manifest_sha256:self.runtime_sha.clone()};
        let child=match &self.installed{Some(installed)=>AuthorityOwnedChild::launch_prepared_installed_facts_only(prepared,context,installed.clone())?,None=>AuthorityOwnedChild::launch_prepared_facts_only(prepared,context)?};
        Ok(StartupOwnedChild{child,_binding:held,_installation:self.installed.clone()})
    }
}
#[cfg(windows)]
pub struct StartupOwnedChild{pub child:AuthorityOwnedChild,_binding:File,_installation:Option<Arc<crate::native_installation::NativeInstallationGuards>>}
#[cfg(windows)]
impl StartupOwnedChild{pub fn process(&self)->Arc<std::sync::Mutex<crate::platform::OwnedProcess>>{self.child.process.clone()}}
