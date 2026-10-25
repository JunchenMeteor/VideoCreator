//! Private build-bound indexed policy. Never supplied through renderer IPC.
use std::{collections::BTreeMap,ffi::OsString,fs,path::{Path,PathBuf},sync::Arc};
use serde::Deserialize;
use serde_json::Value;
use sha2::{Digest,Sha256};
use crate::resource_pins::{PinnedFile,ResourcePins};
use crate::windows_native_sources::{LaunchSourceCarrier,VerifiedSystemContext};

#[derive(Clone,Copy,PartialEq,Eq)]
pub enum ChildRole { Api,Worker,Mcp,Asr,OwnerSetup,OwnerSetupTrust,OwnerSetupQualifiedInstall }
impl ChildRole {
    pub fn name(self)->&'static str {match self{Self::Api=>"api",Self::Worker=>"worker",Self::Mcp=>"mcp",Self::Asr=>"asr",Self::OwnerSetup=>"owner-setup",Self::OwnerSetupTrust=>"owner-setup-trust",Self::OwnerSetupQualifiedInstall=>"owner-setup-qualified-install"}}
    fn entry(self)->&'static str {match self{Self::Asr=>"video_creator.media.asr_worker",Self::OwnerSetup|Self::OwnerSetupTrust|Self::OwnerSetupQualifiedInstall=>"video_creator.cli.native_owner_setup",_=>"video_creator.cli.main"}}
    fn command(self)->Option<&'static str> {match self{Self::Api=>Some("serve"),Self::Worker=>Some("worker"),Self::Mcp=>Some("mcp-stdio"),Self::Asr|Self::OwnerSetup|Self::OwnerSetupTrust|Self::OwnerSetupQualifiedInstall=>None}}
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Profile {
    name:String,implementation:String,python_version:Vec<u16>,builtins:Vec<String>,frozen:Vec<String>,executable:String,
    entry_module:String,command:Option<String>,module_roots:Vec<String>,modules:BTreeMap<String,Value>,native:Value,
    system_contract_ids:Vec<String>,native_sccs:Vec<Vec<String>>,distributions:Value,tool_executables:Vec<String>,bootstrap:String,bootstrap_archive:String,
    required_migration_files:Vec<String>,execution_qualification:String,
    #[serde(default)]adapter_module:Option<String>,#[serde(default)]adapter_callable:Option<String>,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Document {
    format:String,artifact_version:String,platform:String,python_abi:String,backend_snapshot_sha256:String,
    contract_freeze_sha256:String,source_identity:Value,boot:Value,files:Vec<PinnedFile>,profiles:BTreeMap<String,Profile>,data:Value,source_state:String,
    namespace_native_qualification:String,threat_boundary:String,
    system_contracts:BTreeMap<String,Value>,native_alias_groups:Vec<Value>,conditional_search_directories:Vec<Value>,
}
pub struct IndexedPolicy {
    document:Document,pub policy_path:PathBuf,pub policy_sha256:String,migrations:PathBuf,
}
pub struct PreparedLaunch {
    pub executable:PathBuf,pub args:Vec<String>,pub environment:Vec<(OsString,OsString)>,
    pub guard:Arc<ResourcePins>,
    pub(crate) source_carrier:LaunchSourceCarrier,
    selected_role:Option<ChildRole>,selected_policy_sha256:String,
    launched_args:Option<Vec<String>>,launched_executable:Option<PathBuf>,launched_environment:Option<Vec<(OsString,OsString)>>,
    #[cfg(test)] fixture_only:bool,
}
pub(crate) struct StartedPreparedLaunch<P>{pub process:P,pub prepared:PreparedLaunch}
impl PreparedLaunch {
    #[cfg(windows)]
    pub(crate) fn launch_owned(self)->Result<StartedPreparedLaunch<crate::platform::OwnedProcess>,&'static str>{
        #[cfg(test)] if self.fixture_only{return Err("native_fixture_not_os_qualified");}
        self.launch_using(&mut crate::platform::Win32Lifecycle)
    }
    fn launch_using<P:crate::platform::owned_launch::NativeLifecyclePort>(mut self,port:&mut P)->Result<StartedPreparedLaunch<P::Owned>,&'static str>{
        let spec=crate::platform::owned_launch::LaunchSpec{executable:&self.executable,args:&self.args,cwd:self.guard.root(),environment:&self.environment};
        // self keeps the actual ResourcePins and source context alive throughout
        // every post-Create error/unwind cleanup. Transfer returns that same self.
        let process=crate::platform::owned_launch::launch(port,&spec,|pid,creation,stdin|self.source_carrier.bind_before_resume(pid,creation,stdin))?;
        self.launched_args=Some(self.args.clone());self.launched_executable=Some(self.executable.clone());
        self.launched_environment=Some(self.environment.clone());
        Ok(StartedPreparedLaunch{process,prepared:self})
    }
    #[cfg(test)]
    pub(crate) fn fixture(guard:Arc<ResourcePins>,executable_relative:&str,source_carrier:LaunchSourceCarrier)->Result<Self,&'static str>{
        let executable=guard.resolve(executable_relative)?;
        Ok(Self{executable,args:Vec::new(),environment:Vec::new(),guard,source_carrier,selected_role:None,selected_policy_sha256:String::new(),launched_args:None,launched_executable:None,launched_environment:None,fixture_only:true})
    }
    #[cfg(test)]
    pub(crate) fn launch_for_test<P:crate::platform::owned_launch::NativeLifecyclePort>(self,port:&mut P)->Result<StartedPreparedLaunch<P::Owned>,&'static str>{self.launch_using(port)}
}
/// Only the indexed policy can create this member from its original prepared
/// launch. It retains the original payload and native context, not a DTO.
#[cfg(windows)]
pub(crate) struct SetupApiContinuation {pins:Arc<ResourcePins>,source:Arc<VerifiedSystemContext>,image:String,policy_sha256:String,artifact_version:String}
#[cfg(windows)]
impl SetupApiContinuation {
    pub(crate) fn image(&self)->&str{&self.image}
    pub(crate) fn source(&self)->&Arc<VerifiedSystemContext>{&self.source}
    pub(crate) fn assert_current(&self,record:&crate::qualification_record::QualificationRecord)->Result<(),&'static str>{
        let api=record.profiles.first().filter(|profile|profile.name=="api").ok_or("setup_production_profile_required")?;
        if api.executable!=self.image||api.artifact_version!=self.artifact_version||api.load_policy_sha256!=self.policy_sha256{return Err("setup_production_binding_changed");}
        self.source.assert_qualification_identity(&self.artifact_version,&self.policy_sha256)?;
        let observed=self.pins.observe_all()?;self.pins.assert_current(&observed)?;
        if observed.files().len()!=api.required_files.len()||!observed.files().iter().zip(&api.required_files).all(|(actual,expected)|actual.relative_path==expected.relative_path&&actual.bytes==expected.bytes&&actual.sha256==expected.sha256){return Err("setup_production_profile_closure_mismatch");}Ok(())
    }
}
pub(crate) fn text(path:&Path)->Result<String,&'static str>{
    let value=path.to_str().ok_or("native_resource_invalid")?;
    // Win32 canonical paths use a device prefix. Python domain ports deliberately
    // reject UNC input; strip only a local drive prefix, never an UNC authority.
    #[cfg(windows)] if let Some(local)=value.strip_prefix("\\\\?\\"){
        let bytes=local.as_bytes();if bytes.len()<3||!bytes[0].is_ascii_alphabetic()||bytes[1]!=b':'||bytes[2]!=b'\\'{return Err("native_resource_invalid");}
        return Ok(local.to_owned());
    }
    if value.starts_with("\\\\")||value.starts_with("//"){return Err("native_resource_invalid");}Ok(value.to_owned())
}
pub fn digest_valid(value:&str)->bool{value.len()==64&&value.bytes().all(|b|b.is_ascii_digit()||(b'a'..=b'f').contains(&b))}

impl IndexedPolicy {
    #[cfg(windows)]
    pub(crate) fn hold_setup_api_continuation(&self,prepared:&PreparedLaunch,pins:&Arc<ResourcePins>,record:&crate::qualification_record::QualificationRecord)->Result<SetupApiContinuation,&'static str>{
        if !Arc::ptr_eq(&prepared.guard,pins)||prepared.selected_role!=Some(ChildRole::OwnerSetupQualifiedInstall)||prepared.selected_policy_sha256!=self.policy_sha256
            ||prepared.launched_args.as_ref()!=Some(&prepared.args)||prepared.launched_executable.as_ref()!=Some(&prepared.executable)||prepared.launched_environment.as_ref()!=Some(&prepared.environment){return Err("setup_production_original_launch_required");}
        self.assert_qualification_profiles(record,pins)?;
        let setup=self.document.profiles.get("owner-setup-qualified-install").ok_or("setup_production_profile_required")?;
        let api=self.document.profiles.get("api").ok_or("setup_production_profile_required")?;
        if setup.entry_module!="video_creator.cli.native_owner_setup"||setup.command.is_some()||prepared.executable!=pins.resolve(&setup.executable)?
            ||setup.implementation!=api.implementation||setup.python_version!=api.python_version||setup.builtins!=api.builtins||setup.frozen!=api.frozen
            ||setup.executable!=api.executable||setup.bootstrap!=api.bootstrap||setup.bootstrap_archive!=api.bootstrap_archive||setup.module_roots!=api.module_roots
            ||setup.modules!=api.modules||setup.native!=api.native||setup.system_contract_ids!=api.system_contract_ids||setup.native_sccs!=api.native_sccs
            ||setup.distributions!=api.distributions||setup.tool_executables!=api.tool_executables||setup.required_migration_files!=api.required_migration_files{return Err("setup_production_profile_closure_mismatch");}
        for module in ["video_creator.cli.native_owner_setup","video_creator.cli.native_qualified_setup","video_creator.application.native_installation"]{
            if !api.modules.get(module).is_some_and(|entry|entry["kind"]=="source"){return Err("setup_production_continuation_unlisted");}
        }
        let member=SetupApiContinuation{pins:pins.clone(),source:prepared.source_carrier.context.clone(),image:api.executable.clone(),policy_sha256:self.policy_sha256.clone(),artifact_version:self.document.artifact_version.clone()};
        member.assert_current(record)?;Ok(member)
    }
    pub(crate) fn assert_qualification_profiles(&self,record:&crate::qualification_record::QualificationRecord,pins:&ResourcePins)->Result<(),&'static str>{
        if self.document.platform!="windows-amd64"||record.target.os!="windows"||record.target.arch!="x86_64"||self.document.python_abi!="cp313"{return Err("qualification_target_artifact_mismatch");}
        for qualified in &record.profiles{
            let profile=self.document.profiles.get(&qualified.name).ok_or("qualification_profile_unlisted")?;
            if qualified.artifact_version!=self.document.artifact_version||qualified.executable!=profile.executable||qualified.bootstrap!=profile.bootstrap
                ||qualified.entry_module!=profile.entry_module||qualified.command!=profile.command||qualified.adapter_module!=profile.adapter_module
                ||qualified.adapter_callable!=profile.adapter_callable||qualified.load_policy_sha256!=self.policy_sha256{return Err("qualification_profile_artifact_mismatch");}
            // This producer requires each profile's report to cover the full
            // installed physical map. No discarded distribution, ASR sibling,
            // namespace/data file or setup entry is hidden by a subset claim.
            let observed=pins.observe_all()?;pins.assert_current(&observed)?;
            if observed.files().len()!=qualified.required_files.len()||!observed.files().iter().zip(&qualified.required_files).all(|(actual,expected)|
                actual.relative_path==expected.relative_path&&actual.bytes==expected.bytes&&actual.sha256==expected.sha256){return Err("qualification_profile_closure_mismatch");}
        }Ok(())
    }
    pub fn load(pins:&ResourcePins,held:&[PinnedFile],relative:&str,expected:&str,artifact:&str,backend:&str,contracts:&str,migration_directory:&str,migration_files:&[String])->Result<Self,&'static str>{
        if !digest_valid(expected)||!digest_valid(backend)||!digest_valid(contracts)||relative!="LoadPolicy.json"{return Err("native_load_policy_invalid");}
        let policy_path=pins.resolve(relative)?;
        let raw=fs::read(&policy_path).map_err(|_|"native_load_policy_unavailable")?;
        if raw.len()>32*1024*1024||format!("{:x}",Sha256::digest(&raw))!=expected{return Err("native_load_policy_integrity_failed");}
        let document:Document=serde_json::from_slice(&raw).map_err(|_|"native_load_policy_invalid")?;
        let profile_names=document.profiles.keys().map(String::as_str).collect::<std::collections::BTreeSet<_>>();
        let base=["api","worker","mcp","asr"].into_iter().collect::<std::collections::BTreeSet<_>>();
        if document.format!="portable-engine-load-policy-v2-candidate"||document.artifact_version!=artifact||document.platform!="windows-amd64"||document.python_abi!="cp313"||document.backend_snapshot_sha256!=backend||document.contract_freeze_sha256!=contracts
            ||!base.is_subset(&profile_names)||profile_names.iter().any(|name|!base.contains(name)&&!["owner-setup","owner-setup-trust","owner-setup-qualified-install"].contains(name))
            ||["owner-setup-trust","owner-setup-qualified-install"].iter().any(|name|profile_names.contains(name)&&!profile_names.contains("owner-setup")){return Err("native_load_policy_version_mismatch");}
        // Policy identity comes from the trusted installation, not JSON claims.
        // Every policy payload must be one of the already-held exact files.
        let held_by_name=held.iter().map(|item|(item.relative_path.as_str(),item)).collect::<BTreeMap<_,_>>();
        let mut seen=std::collections::BTreeSet::new();
        for item in &document.files{
            let actual=held_by_name.get(item.relative_path.as_str()).ok_or("native_load_policy_unpinned")?;
            if !seen.insert(item.relative_path.to_lowercase())||actual.bytes!=item.bytes||actual.sha256!=item.sha256{return Err("native_load_policy_integrity_failed");}
            pins.resolve(&item.relative_path)?;
        }
        let payload_names=held_by_name.keys().filter(|name|**name!="LoadPolicy.json"&&**name!="IndexedFileManifest.json").map(|name|name.to_string()).collect::<std::collections::BTreeSet<_>>();
        if seen!=payload_names.iter().map(|name|name.to_lowercase()).collect(){return Err("native_load_policy_membership_mismatch");}
        if migration_directory!="Migrations"||migration_files.is_empty(){return Err("native_migrations_invalid");}
        let mut sorted=migration_files.to_vec();sorted.sort();sorted.dedup();
        if sorted.len()!=migration_files.len(){return Err("native_migrations_invalid");}
        // Complete exact producer-pinned migration membership, rather than
        // inheriting the old five-file artifact into schema10 startup.
        let actual_migrations=held_by_name.keys().filter(|name|name.starts_with("Migrations/")).map(|name|name.to_string()).collect::<std::collections::BTreeSet<_>>();
        if actual_migrations!=sorted.iter().cloned().collect(){return Err("native_migrations_invalid");}
        let mut migration_root=None;
        for file in &sorted{
            if !file.starts_with("Migrations/")||!file.ends_with(".sql"){return Err("native_migrations_invalid");}
            let path=pins.resolve(file)?;let parent=path.parent().ok_or("native_migrations_invalid")?.to_owned();
            if migration_root.as_ref().is_some_and(|known|known!=&parent){return Err("native_migrations_invalid");}migration_root=Some(parent);
        }
        // Existing four-profile artifacts keep their strict original roles.
        // A new setup launch itself requires the separately producer-indexed
        // fifth profile; absence never enables a fallback command/module.
        let setup_roles=[ChildRole::OwnerSetup,ChildRole::OwnerSetupTrust,ChildRole::OwnerSetupQualifiedInstall].into_iter().filter(|role|document.profiles.contains_key(role.name()));
        for role in [ChildRole::Api,ChildRole::Worker,ChildRole::Mcp,ChildRole::Asr].into_iter().chain(setup_roles){
            let profile=document.profiles.get(role.name()).ok_or("native_role_profile_missing")?;
            if profile.name!=role.name()||profile.implementation!="cpython"||profile.python_version!=[3,13,16]||profile.entry_module!=role.entry()||profile.command.as_deref()!=role.command()||profile.required_migration_files!=sorted||profile.bootstrap!="Bootstrap/IndexedBootstrap.py"||profile.bootstrap_archive!="Bootstrap/BaseStdlib.zip"||!profile.builtins.iter().any(|s|s=="_sha2"){return Err("native_role_profile_invalid");}
            if !profile.modules.get(&profile.entry_module).is_some_and(|entry|entry["kind"]=="source"){return Err("native_role_entry_unlisted");}
            match(profile.adapter_module.as_deref(),profile.adapter_callable.as_deref()){
                (None,None)=>{},
                (Some("video_creator.cli.native_startup"),Some("main_qualified")) if matches!(role,ChildRole::Api|ChildRole::Worker|ChildRole::Mcp)=>{
                    if !profile.modules.get("video_creator.cli.native_startup").is_some_and(|item|item["kind"]=="source"){return Err("native_role_adapter_unlisted");}
                },_=>return Err("native_role_adapter_invalid"),
            }
            pins.resolve(&profile.executable)?;pins.resolve(&profile.bootstrap)?;pins.resolve(&profile.bootstrap_archive)?;
            let pth=Path::new(&profile.executable).parent().ok_or("native_role_profile_invalid")?.join("python313._pth");
            pins.resolve(pth.to_str().ok_or("native_role_profile_invalid")?)?;
            let mut ids=std::collections::BTreeSet::new();
            for id in &profile.system_contract_ids{
                let record=document.system_contracts.get(id).ok_or("native_system_contract_missing")?;
                let basename=record["basename"].as_str().ok_or("native_system_contract_invalid")?;
                if !ids.insert(id.clone())||record["id"]!=*id||record["os"]!="windows"||record["architecture"]!="amd64"||!matches!(record["source_kind"].as_str(),Some("windows_component"|"api_set"|"external_vc"))||basename.contains(['/', '\\', ':'])||basename.to_lowercase()!=basename||!record["profiles"].as_array().is_some_and(|roles|roles.iter().any(|value|value==role.name())){return Err("native_system_contract_invalid");}
                if record["official_evidence"].as_array().is_none_or(|urls|urls.is_empty()||urls.iter().any(|value|value.as_str().is_none_or(|url|!url.starts_with("https://learn.microsoft.com/")))){return Err("native_system_contract_evidence_missing");}
            }
            let native=profile.native.as_object().ok_or("native_role_native_invalid")?;
            for(name,record)in native{
                let identity=held_by_name.get(name.as_str()).ok_or("native_object_unpinned")?;
                if record["identity"]["sha256"]!=identity.sha256||record["identity"]["bytes"]!=identity.bytes||record["machine"]!=0x8664{return Err("native_object_identity_invalid");}
                for dependency in record["system_contract_dependencies"].as_array().ok_or("native_object_relation_invalid")?{if !dependency.as_str().is_some_and(|id|ids.contains(id)){return Err("native_system_relation_unlisted");}}
                for dependency in record["payload_dependencies"].as_array().ok_or("native_object_relation_invalid")?{if !dependency.as_str().is_some_and(|name|native.contains_key(name)){return Err("native_payload_relation_unlisted");}}
            }
            let mut component_members=std::collections::BTreeSet::new();for component in &profile.native_sccs{if component.is_empty(){return Err("native_scc_invalid");}for name in component{if !native.contains_key(name)||!component_members.insert(name){return Err("native_scc_invalid");}}}
            if component_members.len()!=native.len(){return Err("native_scc_membership_invalid");}
            for group in document.native_alias_groups.iter().filter(|group|group["profile"]==role.name()){
                if group["basename"]!="msvcp140-a4c2229bdc2a2a630acdc095b4d86008.dll"||group["canonical"]!=group["expected_actual_origin"]{return Err("native_alias_invalid");}
                let canonical=group["canonical"].as_str().ok_or("native_alias_invalid")?;
                let prefix=Path::new(&profile.executable).parent().ok_or("native_alias_invalid")?;
                if Path::new(canonical)!=prefix.join("Lib/site-packages/numpy.libs/msvcp140-a4c2229bdc2a2a630acdc095b4d86008.dll"){return Err("native_alias_canonical_invalid");}
                let members=group["members"].as_array().ok_or("native_alias_invalid")?;if members.len()!=if matches!(role,ChildRole::Asr){1}else{2}{return Err("native_alias_members_invalid");}
                for member in members{let name=member["identity"]["relative_path"].as_str().ok_or("native_alias_invalid")?;let identity=held_by_name.get(name).ok_or("native_alias_unpinned")?;
                    if member["identity"]["sha256"]!=identity.sha256||member["identity"]["bytes"]!=identity.bytes||identity.bytes!=575056||identity.sha256!="a4c2229bdc2a2a630acdc095b4d86008e5c3e3bc7773174354f3da4f5beb9cde"||member["machine"]!=0x8664{return Err("native_alias_identity_invalid");}
                    pins.resolve(member["owner_record"]["relative_path"].as_str().ok_or("native_alias_record_missing")?)?;
                }
            }
            for rule in document.conditional_search_directories.iter().filter(|record|record["profile"]==role.name()){
                let prefix=Path::new(&profile.executable).parent().ok_or("native_conditional_directory_invalid")?;let name=rule["relative_path"].as_str().ok_or("native_conditional_directory_invalid")?;
                let allowed=[prefix.join("Lib/site-packages/_rocm_sdk_core/bin"),prefix.join("Lib/site-packages/_rocm_sdk_libraries_custom/bin")];
                if !matches!(role,ChildRole::Asr)||!allowed.contains(&PathBuf::from(name))||rule["mode"]!="absence_only"||rule["platform"]!="windows-amd64"||rule["compute_profile"]!="cpu"||rule["caller"]!="registered_exact_compiled_code_object"||rule["source"]["sha256"]!="a2a1954f726c88d527279d0284695f6011285ee6f7bd75ba76e61c1bdb2be646"{return Err("native_conditional_directory_invalid");}
                pins.resolve(rule["source"]["relative_path"].as_str().ok_or("native_conditional_source_invalid")?)?;
            }
        }
        Ok(Self{document,policy_path,policy_sha256:expected.to_owned(),migrations:migration_root.ok_or("native_migrations_invalid")?})
    }
    pub fn prepare(&self,pins:Arc<ResourcePins>,role:ChildRole,instance:&Path,private_token:Option<&str>,arguments:Vec<String>)->Result<PreparedLaunch,&'static str>{
        if !instance.is_absolute(){return Err("native_instance_invalid");}
        fs::create_dir_all(instance).map_err(|_|"native_instance_invalid")?;
        let data=instance.canonicalize().map_err(|_|"native_instance_invalid")?;
        if data.starts_with(pins.root())||pins.root().starts_with(&data){return Err("native_resource_data_overlap");}
        let temp=data.join("Temp");fs::create_dir_all(&temp).map_err(|_|"native_instance_invalid")?;
        let profile=self.document.profiles.get(role.name()).ok_or("native_role_profile_missing")?;
        if profile.command.as_deref().is_some_and(|command|arguments.first().map(String::as_str)!=Some(command)){return Err("native_role_command_invalid");}
        let(system_directory,mut environment)=trusted_system_environment()?;
        let context=VerifiedSystemContext::collect(&self.document.system_contracts,&profile.system_contract_ids,role.name(),&self.document.artifact_version,&self.policy_sha256)?;
        if PathBuf::from(&context.observations().system_directory).canonicalize().map_err(|_|"native_system_root_unavailable")?!=system_directory{return Err("native_system_root_changed");}
        let source_carrier=context.carrier(&temp)?;
        environment.extend([("TEMP".into(),text(&temp)?.into()),("TMP".into(),text(&temp)?.into()),("VIDEO_CREATOR_MIGRATIONS_DIR".into(),text(&self.migrations)?.into())]);
        if let Some(token)=private_token {if token.len()<32{return Err("native_private_session_invalid");}environment.push(("VIDEO_CREATOR_API_TOKEN".into(),token.into()));}
        let executable=pins.resolve(&profile.executable)?;let bootstrap=pins.resolve(&profile.bootstrap)?;
        let mut args=vec!["-I".into(),"-S".into(),"-B".into(),"-X".into(),"utf8".into(),text(&bootstrap)?,"--installation-root".into(),text(pins.root())?,"--load-policy".into(),text(&self.policy_path)?,"--load-policy-sha256".into(),self.policy_sha256.clone(),"--profile".into(),role.name().into(),"--system-directory".into(),text(&system_directory)?,"--data-root".into(),text(&data)?,"--data-root".into(),text(&temp)?,"--".into()];
        // Append before the product '--' delimiter; the carrier SHA is already
        // immutable before CreateProcess and actual child binding uses stdin.
        args.pop();args.extend(["--native-source-context".into(),text(&source_carrier.path)?,"--native-source-context-sha256".into(),source_carrier.sha256.clone(),"--".into()]);
        args.extend(arguments);
        Ok(PreparedLaunch{executable,args,environment,guard:pins,source_carrier,selected_role:Some(role),selected_policy_sha256:self.policy_sha256.clone(),launched_args:None,launched_executable:None,launched_environment:None,#[cfg(test)] fixture_only:false})
    }
}

#[cfg(windows)]
pub fn trusted_system_environment()->Result<(PathBuf,Vec<(OsString,OsString)>),&'static str>{
    use std::os::windows::ffi::OsStringExt;
    use windows_sys::Win32::System::SystemInformation::{GetSystemDirectoryW,GetWindowsDirectoryW};
    let mut system=vec![0u16;32768];let mut windows=vec![0u16;32768];
    let sc=unsafe{GetSystemDirectoryW(system.as_mut_ptr(),system.len() as u32)} as usize;
    let wc=unsafe{GetWindowsDirectoryW(windows.as_mut_ptr(),windows.len() as u32)} as usize;
    if sc==0||wc==0||sc>=system.len()||wc>=windows.len(){return Err("native_system_root_unavailable");}
    let system=PathBuf::from(OsString::from_wide(&system[..sc])).canonicalize().map_err(|_|"native_system_root_unavailable")?;
    let windows=PathBuf::from(OsString::from_wide(&windows[..wc])).canonicalize().map_err(|_|"native_system_root_unavailable")?;
    if !system.is_absolute()||!windows.is_absolute()||system.parent()!=Some(windows.as_path())||system.file_name().is_none_or(|n|n.to_string_lossy().to_lowercase()!="system32"){return Err("native_system_root_invalid");}
    Ok((system.clone(),vec![("SystemRoot".into(),windows.as_os_str().to_owned()),("WINDIR".into(),windows.as_os_str().to_owned()),("COMSPEC".into(),system.join("cmd.exe").as_os_str().to_owned()),("PATHEXT".into(),".COM;.EXE;.BAT;.CMD".into())]))
}
#[cfg(not(windows))]
pub fn trusted_system_environment()->Result<(PathBuf,Vec<(OsString,OsString)>),&'static str>{Err("native_platform_profile_unqualified")}
