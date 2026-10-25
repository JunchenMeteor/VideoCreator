//! Original host/control/payload ownership. Facts are not an Owner action,
//! publisher anchor, persistent current registration or qualified Evidence.
//! Native structures consume Backend B39's single private model field mapping.
use std::{collections::BTreeSet,path::{Component,Path,PathBuf},sync::{Arc,atomic::{AtomicBool,Ordering}}};
use serde::{Deserialize,Serialize};
use sha2::{Digest,Sha256};
use crate::resource_pins::{ResourcePins,PinnedFile,HeldFileObservation};

#[derive(Deserialize,Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct EvidenceRef{kind:String,reference_id:String,content_sha256:String}
#[derive(Deserialize,Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct BuildReceipt{
    format:String,build_id:String,target:String,host_image_bytes:u64,host_image_sha256:String,
    payload_manifest_sha256:String,registration_sha256:String,resource_manifest_sha256:String,runtime_manifest_sha256:String,
    evidence_refs:Vec<EvidenceRef>,
}
#[derive(Deserialize,Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct InstallationInputs{
    composition_root:String,pub installed_native_image:String,installed_native_image_bytes:u64,pub installed_native_image_sha256:String,
    payload_root:String,payload_manifest_sha256:String,pub registration_sha256:String,pub resource_manifest_sha256:String,pub runtime_manifest_sha256:String,
    pub expected_files:Vec<PinnedFile>,pub engine_file_names:Vec<String>,build_receipt:BuildReceipt,build_receipt_sha256:String,
}
pub(crate) fn canonical(value:&serde_json::Value)->Result<Vec<u8>,&'static str>{
    fn emit(value:&serde_json::Value,out:&mut Vec<u8>)->Result<(),&'static str>{
        match value{
            serde_json::Value::Object(map)=>{out.push(b'{');let mut keys=map.keys().collect::<Vec<_>>();keys.sort_unstable();
                for(i,key)in keys.into_iter().enumerate(){if i!=0{out.push(b',');}out.extend(serde_json::to_vec(key).map_err(|_|"native_installation_invalid")?);out.push(b':');emit(&map[key],out)?;}out.push(b'}');},
            serde_json::Value::Array(values)=>{out.push(b'[');for(i,item)in values.iter().enumerate(){if i!=0{out.push(b',');}emit(item,out)?;}out.push(b']');},
            _=>out.extend(serde_json::to_vec(value).map_err(|_|"native_installation_invalid")?),
        }Ok(())
    }let mut result=Vec::new();emit(value,&mut result)?;Ok(result)
}
fn valid_id(value:&str)->bool{(1..=128).contains(&value.len())&&value.bytes().all(|b|b.is_ascii_alphanumeric()||b"_.:-".contains(&b))}
fn digest(value:&str)->bool{crate::load_policy::digest_valid(value)}
fn absolute(value:&str)->Result<PathBuf,&'static str>{
    if value.is_empty()||value.len()>32768||value.chars().any(char::is_control)||value.starts_with("\\\\")||value.starts_with("//")
        ||value.replace('\\',"/").split('/').any(|part|part=="."||part==".."){return Err("native_installation_path_invalid");}
    let path=PathBuf::from(value);if !path.is_absolute(){return Err("native_installation_path_invalid");}
    #[cfg(windows)]{let bytes=value.as_bytes();if bytes.len()<3||!bytes[0].is_ascii_alphabetic()||bytes[1]!=b':'||![b'\\',b'/'].contains(&bytes[2])
        ||value[2..].split(['\\','/']).any(|part|part.contains(':')||part.ends_with([' ','.'])){return Err("native_installation_path_invalid");}}
    Ok(path)
}
fn member(value:&str)->bool{!value.is_empty()&&!value.contains(['\\',':'])&&!value.chars().any(char::is_control)
    &&!value.split('/').any(|part|part.is_empty()||part=="."||part==".."||cfg!(windows)&&part.ends_with([' ','.']))
    &&Path::new(value).components().all(|part|matches!(part,Component::Normal(_)))}
fn physical_name(path:&Path)->Result<(),&'static str>{
    let mut cursor=PathBuf::new();
    for part in path.components(){cursor.push(part.as_os_str());if matches!(part,Component::Prefix(_)){continue;}let metadata=std::fs::symlink_metadata(&cursor).map_err(|_|"native_installation_unavailable")?;
        if metadata.file_type().is_symlink(){return Err("native_installation_alias_denied");}
        #[cfg(windows)]{use std::os::windows::fs::MetadataExt;if metadata.file_attributes()&0x400!=0{return Err("native_installation_alias_denied");}}
    }Ok(())
}
impl InstallationInputs{
    fn validate(&self)->Result<(),&'static str>{
        let receipt=&self.build_receipt;
        if receipt.format!="native-build-receipt-v1"||!valid_id(&receipt.build_id)||!valid_id(&receipt.target)
            ||self.installed_native_image_bytes==0||self.installed_native_image_bytes>i64::MAX as u64{return Err("native_build_receipt_invalid");}
        let names=self.expected_files.iter().map(|entry|entry.relative_path.as_str()).collect::<BTreeSet<_>>();
        let mut previous=None;let mut case_names=BTreeSet::new();
        for file in &self.expected_files{if !member(&file.relative_path)||!digest(&file.sha256)||file.bytes>i64::MAX as u64
            ||previous.is_some_and(|name:&str|name>=file.relative_path.as_str())||!case_names.insert(file.relative_path.to_lowercase()){return Err("native_installation_map_invalid");}previous=Some(&file.relative_path);}
        let engine=self.engine_file_names.iter().map(String::as_str).collect::<BTreeSet<_>>();
        if engine.is_empty()||engine.len()!=self.engine_file_names.len()||engine.len()>=names.len()||!engine.is_subset(&names)
            ||!self.engine_file_names.windows(2).all(|pair|pair[0]<pair[1]){return Err("native_startup_partition_invalid");}
        for sha in [&self.installed_native_image_sha256,&self.payload_manifest_sha256,&self.registration_sha256,&self.resource_manifest_sha256,&self.runtime_manifest_sha256,&self.build_receipt_sha256]{if !digest(sha){return Err("native_build_receipt_invalid");}}
        if (receipt.host_image_bytes,&receipt.host_image_sha256,&receipt.payload_manifest_sha256,&receipt.registration_sha256,&receipt.resource_manifest_sha256,&receipt.runtime_manifest_sha256)
            !=(self.installed_native_image_bytes,&self.installed_native_image_sha256,&self.payload_manifest_sha256,&self.registration_sha256,&self.resource_manifest_sha256,&self.runtime_manifest_sha256){return Err("native_build_receipt_mismatch");}
        let mut seen=BTreeSet::new();let mut kinds=BTreeSet::new();
        for reference in &receipt.evidence_refs{if !["host_source","lockfile","tool","producer_input","license","qualification"].contains(&reference.kind.as_str())
            ||!valid_id(&reference.reference_id)||!digest(&reference.content_sha256)||!seen.insert((&reference.kind,&reference.reference_id)){return Err("native_build_receipt_invalid");}kinds.insert(reference.kind.as_str());}
        if !(4..=256).contains(&receipt.evidence_refs.len())||!["host_source","lockfile","tool","producer_input"].iter().all(|kind|kinds.contains(kind)){return Err("native_build_receipt_invalid");}
        let raw=canonical(&serde_json::to_value(receipt).map_err(|_|"native_build_receipt_invalid")?)?;
        if format!("{:x}",Sha256::digest(&raw))!=self.build_receipt_sha256{return Err("native_build_receipt_mismatch");}Ok(())
    }
}

/// Separate Arc/File owners. Host and control stay outside payload; the
/// Backend's protected Owner record/current object remains a separate issuer.
pub struct NativeInstallationGuards{
    pub(crate) inputs:InstallationInputs,pub(crate) payload:Arc<ResourcePins>,host:Arc<ResourcePins>,control:Arc<ResourcePins>,
    host_name:String,pub(crate) host_path:PathBuf,receipt_path:PathBuf,composition:PathBuf,valid:AtomicBool,
}
pub struct InstallationObservation<'guard>{issuer:&'guard NativeInstallationGuards,
    host:HeldFileObservation<'guard>,control:HeldFileObservation<'guard>,payload:HeldFileObservation<'guard>}
impl InstallationObservation<'_>{
    pub(crate) fn payload_files(&self)->&[PinnedFile]{self.payload.files()}
    pub(crate) fn observed_at_us(&self)->u64{self.payload.observed_at_us()}
    pub(crate) fn host_file(&self)->&PinnedFile{&self.host.files()[0]}
    pub(crate) fn receipt_file(&self)->&PinnedFile{&self.control.files()[0]}
}
impl NativeInstallationGuards{
    /// The original held receipt selects Control. No locator or renderer path
    /// can supply a replacement root or build identity for trust admission.
    pub(crate) fn control_root(&self)->Result<&Path,&'static str>{self.receipt_path.parent().ok_or("native_installation_control_invalid")}
    pub(crate) fn receipt_sha256(&self)->&str{&self.inputs.build_receipt_sha256}
    pub(crate) fn full_file_map_sha256(&self)->Result<String,&'static str>{
        Ok(format!("{:x}",Sha256::digest(canonical(&serde_json::to_value(&self.inputs.expected_files).map_err(|_|"native_installation_map_invalid")?)?)))
    }
    pub(crate) fn engine_partition_sha256(&self)->Result<String,&'static str>{
        // This is the original sorted context partition, not a second file map.
        Ok(format!("{:x}",Sha256::digest(canonical(&serde_json::to_value(&self.inputs.engine_file_names).map_err(|_|"native_startup_partition_invalid")?)?)))
    }
    /// Portable fixed producer layout: Composition/Host/<final image>,
    /// Composition/Control/{NativeInstallationInputs,NativeBuildReceipt}.json,
    /// and the separately held complete payload. Relative layout is selected
    /// by the native producer; the record is data and conveys no Owner grant.
    pub(crate) fn from_packaged_host()->Result<(Arc<Self>,Arc<ResourcePins>),&'static str>{
        let image=std::env::current_exe().map_err(|_|"native_startup_image_unknown")?.canonicalize().map_err(|_|"native_startup_image_unknown")?;
        let host=image.parent().ok_or("native_installation_layout_invalid")?;
        if host.file_name().and_then(|name|name.to_str())!=Some("Host"){return Err("native_installation_layout_invalid");}
        let composition=host.parent().ok_or("native_installation_layout_invalid")?;
        let control=composition.join("Control");physical_name(&control)?;
        let input=control.join("NativeInstallationInputs.json");physical_name(&input)?;
        let metadata=std::fs::metadata(&input).map_err(|_|"native_installation_unavailable")?;
        if !metadata.is_file()||metadata.len()>32*1024*1024{return Err("native_installation_invalid");}
        let raw=std::fs::read(&input).map_err(|_|"native_installation_unavailable")?;
        let installation=Self::hold(&raw,&control.join("NativeBuildReceipt.json"))?;
        if installation.composition_root()!=composition{return Err("native_installation_layout_invalid");}
        installation.image_is_current_process()?;
        let pins=Arc::new(ResourcePins::hold(&control,&[PinnedFile{relative_path:"NativeInstallationInputs.json".into(),bytes:raw.len()as u64,sha256:format!("{:x}",Sha256::digest(&raw))}])?);
        if pins.read_held_bytes("NativeInstallationInputs.json",32*1024*1024)?!=raw{return Err("native_installation_control_changed");}
        Ok((installation,pins))
    }
    /// Called only by a trusted installation consumer after original Backend
    /// parsing. raw is data; this opens original facts and emits no authority.
    pub fn hold(raw:&[u8],external_receipt:&Path)->Result<Arc<Self>,&'static str>{
        if raw.len()>32*1024*1024{return Err("native_installation_invalid");}
        let inputs:InstallationInputs=serde_json::from_slice(raw).map_err(|_|"native_installation_invalid")?;inputs.validate()?;
        if canonical(&serde_json::to_value(&inputs).map_err(|_|"native_installation_invalid")?)?!=raw{return Err("native_installation_noncanonical");}
        let composition=absolute(&inputs.composition_root)?;physical_name(&composition)?;
        let composition=composition.canonicalize().map_err(|_|"native_installation_unavailable")?;
        let host_path=absolute(&inputs.installed_native_image)?;let root=absolute(&inputs.payload_root)?;
        physical_name(&host_path)?;physical_name(&root)?;
        let host_name=host_path.file_name().and_then(|name|name.to_str()).ok_or("native_installation_path_invalid")?.to_owned();
        let host=Arc::new(ResourcePins::hold(host_path.parent().ok_or("native_installation_path_invalid")?,&[PinnedFile{relative_path:host_name.clone(),bytes:inputs.installed_native_image_bytes,sha256:inputs.installed_native_image_sha256.clone()}])?);
        let host_path=host.resolve(&host_name)?;
        let payload=Arc::new(ResourcePins::hold(&root,&inputs.expected_files)?);
        let receipt_raw=canonical(&serde_json::to_value(&inputs.build_receipt).map_err(|_|"native_build_receipt_invalid")?)?;
        let receipt_path=absolute(external_receipt.to_str().ok_or("native_installation_path_invalid")?)?;
        physical_name(&receipt_path)?;
        let receipt_name=receipt_path.file_name().and_then(|name|name.to_str()).ok_or("native_installation_path_invalid")?;
        let control=Arc::new(ResourcePins::hold(receipt_path.parent().ok_or("native_installation_path_invalid")?,&[PinnedFile{relative_path:receipt_name.into(),bytes:receipt_raw.len()as u64,sha256:inputs.build_receipt_sha256.clone()}])?);
        if host_path.starts_with(payload.root())||control.resolve(receipt_name)?.starts_with(payload.root())
            ||!host_path.starts_with(&composition)||!payload.root().starts_with(&composition){return Err("native_installation_recursive_input");}
        if control.read_held_bytes(receipt_name,32*1024*1024)?!=receipt_raw{return Err("native_build_receipt_mismatch");}
        let manifest=inputs.expected_files.iter().find(|entry|entry.relative_path=="InstallationManifest.json").ok_or("native_installation_manifest_unpinned")?;
        if manifest.sha256!=inputs.payload_manifest_sha256{return Err("native_installation_manifest_mismatch");}
        let receipt_path=control.resolve(receipt_name)?;
        let owner=Arc::new(Self{inputs,payload,host,control,host_name,host_path,receipt_path,composition,valid:AtomicBool::new(true)});
        let observation=owner.observe()?;owner.assert_current(&observation)?;drop(observation);Ok(owner)
    }
    pub fn observe(&self)->Result<InstallationObservation<'_>,&'static str>{
        if !self.valid.load(Ordering::Acquire){return Err("native_installation_observation_closed");}
        let result=(||{self.assert_payload_membership()?;let observation=InstallationObservation{issuer:self,host:self.host.observe_all()?,control:self.control.observe_all()?,payload:self.payload.observe_all()?};self.assert_payload_membership()?;Ok(observation)})();
        if result.is_err(){self.invalidate();}result
    }
    pub fn assert_current(&self,observation:&InstallationObservation<'_>)->Result<(),&'static str>{
        let result=(||{self.assert_local_current(observation)?;self.assert_payload_membership()?;self.host.assert_current(&observation.host)?;self.control.assert_current(&observation.control)?;self.payload.assert_current(&observation.payload)?;self.assert_payload_membership()?;self.assert_local_current(observation)})();
        if result.is_err(){self.invalidate();}result
    }
    /// Only this original borrow/current epoch. No OS, filesystem, hash or RPC
    /// in the Backend's short writer. Backend checks Owner/store/floor itself.
    pub fn assert_local_current(&self,observation:&InstallationObservation<'_>)->Result<(),&'static str>{
        if !std::ptr::eq(self,observation.issuer)||!self.valid.load(Ordering::Acquire){return Err("native_installation_observation_closed");}Ok(())
    }
    pub fn invalidate(&self){self.valid.store(false,Ordering::Release);}
    fn assert_payload_membership(&self)->Result<(),&'static str>{
        let expected=self.inputs.expected_files.iter().map(|entry|entry.relative_path.as_str()).collect::<BTreeSet<_>>();
        let mut seen=BTreeSet::new();let mut pending=vec![self.payload.root().to_owned()];
        // Compare the complete physical file membership. Empty packaging
        // directories grant no module/native permission; indexed loading still
        // rejects a source absent from the original LoadPolicy.
        while let Some(directory)=pending.pop(){
            for entry in std::fs::read_dir(&directory).map_err(|_|"native_installation_membership_unknown")?{
                let entry=entry.map_err(|_|"native_installation_membership_unknown")?;let path=entry.path();
                let metadata=std::fs::symlink_metadata(&path).map_err(|_|"native_installation_membership_unknown")?;
                if metadata.file_type().is_symlink(){return Err("native_installation_alias_denied");}
                #[cfg(windows)]{use std::os::windows::fs::MetadataExt;if metadata.file_attributes()&0x400!=0{return Err("native_installation_alias_denied");}}
                let relative=path.strip_prefix(self.payload.root()).map_err(|_|"native_installation_membership_unknown")?;
                if metadata.is_dir(){pending.push(path);}
                else if metadata.is_file(){let name=relative.to_str().ok_or("native_installation_path_invalid")?.replace('\\',"/");if !expected.contains(name.as_str())||!seen.insert(name){return Err("native_installation_membership_changed");}}
                else{return Err("native_installation_membership_changed");}
            }
        }
        if seen.len()!=expected.len(){return Err("native_installation_membership_changed");}Ok(())
    }
    pub(crate) fn manifest_bytes(&self)->Result<Vec<u8>,&'static str>{self.payload.read_held_bytes("InstallationManifest.json",16*1024*1024)}
    pub(crate) fn image_is_current_process(&self)->Result<(),&'static str>{
        if std::env::current_exe().map_err(|_|"native_startup_image_unknown")?.canonicalize().map_err(|_|"native_startup_image_unknown")?!=self.host_path{return Err("native_startup_image_mismatch");}
        let observation=self.host.observe_files(&[&self.host_name])?;self.host.assert_current(&observation)
    }
    pub fn composition_root(&self)->&Path{&self.composition}
    pub(crate) fn receipt_path(&self)->&Path{&self.receipt_path}
    pub(crate) fn inputs_sha256(&self)->Result<String,&'static str>{Ok(format!("{:x}",Sha256::digest(canonical(&serde_json::to_value(&self.inputs).map_err(|_|"native_installation_invalid")?)?)))}
}
