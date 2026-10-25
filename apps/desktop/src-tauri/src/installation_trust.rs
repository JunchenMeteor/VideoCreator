//! Native installation-source admission. The index is a selection, not trust.
//! Only the original OS input, held installation and registered child can bind
//! it. No Deserialize/Clone constructor exists for Prepared/Bound members.
use std::{collections::BTreeSet,fs::{File,OpenOptions},io::Read,path::{Component,Path},sync::{Arc,Mutex,mpsc},thread::{self,JoinHandle},time::{Duration,Instant,SystemTime,UNIX_EPOCH}};
use serde::{Deserialize,Serialize};
use serde_json::{json,Value};
use sha2::{Digest,Sha256};
use crate::{native_installation::{canonical,NativeInstallationGuards},owner_setup_directory::OwnerDirectory,owner_setup_initialize::InitializationCurrent,
    owner_setup_window::{self,TrustInput},platform::OwnedProcess,resource_authority::OwnerSetupPipe,resource_pins::{PinnedFile,ResourcePins}};

pub(crate) const MATERIAL_INDEX:&str="QualificationMaterialsIndex.json";
const WIRE:&str="held-installation-trust-v1-candidate";
const LIMIT:usize=32*1024*1024;
const TOTAL:u64=128*1024*1024;
pub(crate) type MaterialRef=crate::qualification_record::QualificationRef;
#[derive(Deserialize,Serialize)]#[serde(deny_unknown_fields)]
struct Material {r#ref:MaterialRef,relative_path:String,bytes:u64,purpose:Purpose}
#[derive(Deserialize,Serialize,PartialEq,Eq,Copy,Clone)]#[serde(rename_all="snake_case")]
enum Purpose {TrustAnchor,PublisherProvenance,VerifierCodeIndex,QualificationSuite,IndependentReview,IndependentAcceptance,AnchorGeneration,QualificationReport,LicenseEvidence,BuildProvenance}
#[derive(Deserialize,Serialize)]#[serde(deny_unknown_fields)]
struct MaterialsIndex {format:String,issuer_id:String,trust_mode:String,public_key_hex:String,materials:Vec<Material>}
fn id(value:&str)->bool{!value.is_empty()&&value.len()<=128&&value.bytes().all(|b|b.is_ascii_alphanumeric()||b"_.:-".contains(&b))}
fn relative(value:&str)->bool{!value.is_empty()&&!value.contains(['\\',':'])&&!value.chars().any(char::is_control)
    &&value.split('/').all(|p|!p.is_empty()&&p!="."&&p!=".."&&!p.ends_with([' ','.']))&&Path::new(value).components().all(|p|matches!(p,Component::Normal(_)))}
fn now()->Result<u64,&'static str>{let value=SystemTime::now().duration_since(UNIX_EPOCH).map_err(|_|"trust_clock_unavailable")?.as_micros();
    if value==0||value>i64::MAX as u128{return Err("trust_clock_unavailable");}Ok(value as u64)}
fn digest(raw:&[u8])->String{format!("{:x}",Sha256::digest(raw))}

pub(crate) struct TrustMaterials {
    index:MaterialsIndex,pins:ResourcePins,_selected_index:File,directory:OwnerDirectory,index_sha256:String,
}
impl TrustMaterials {
    /// Only the original installation receipt selects this protected Control.
    /// Candidate key bytes cannot be admitted by this parser: prepare_trust
    /// additionally requires the separate actual native confirmation below.
    pub(crate) fn hold(installation:&Arc<NativeInstallationGuards>)->Result<Self,&'static str>{
        installation.image_is_current_process()?;let root=installation.control_root()?;
        let identity=crate::resource_authority::current_identity()?;
        let directory=OwnerDirectory::hold(root,&identity.sid)?;
        use std::os::windows::fs::OpenOptionsExt;
        let selected=OpenOptions::new().read(true).share_mode(1).custom_flags(0x0020_0000).open(root.join(MATERIAL_INDEX)).map_err(|_|"installation_trust_materials_unavailable")?;
        if !selected.metadata().map_err(|_|"installation_trust_materials_unavailable")?.is_file(){return Err("installation_trust_materials_invalid");}
        let mut raw=Vec::new();(&selected).take(LIMIT as u64+1).read_to_end(&mut raw).map_err(|_|"installation_trust_materials_unavailable")?;
        if raw.len()>LIMIT{return Err("installation_trust_materials_oversized");}
        let index:MaterialsIndex=serde_json::from_slice(&raw).map_err(|_|"installation_trust_materials_invalid")?;
        if canonical(&serde_json::to_value(&index).map_err(|_|"installation_trust_materials_invalid")?)?!=raw
            ||index.format!="installation-qualification-material-index-v1"||!id(&index.issuer_id)
            ||!matches!(index.trust_mode.as_str(),"publisher"|"local_verifier")||index.materials.is_empty()||index.materials.len()>4096
            ||index.public_key_hex.len()!=64||!crate::load_policy::digest_valid(&index.public_key_hex){return Err("installation_trust_materials_invalid");}
        let mut entries=vec![PinnedFile{relative_path:MATERIAL_INDEX.into(),bytes:raw.len()as u64,sha256:digest(&raw)}];
        let mut names=BTreeSet::new();let mut previous=None;let mut bytes=raw.len()as u64;let mut anchor=None;
        for material in &index.materials {
            let reference=&material.r#ref;
            if !id(&reference.document_id)||reference.revision==0||reference.revision>i64::MAX as u64||!crate::load_policy::digest_valid(&reference.sha256)
                ||!relative(&material.relative_path)||material.relative_path==MATERIAL_INDEX||material.bytes>LIMIT as u64
                ||!names.insert(material.relative_path.to_lowercase())||previous.is_some_and(|old:&MaterialRef|old>=reference){return Err("installation_trust_materials_invalid");}
            previous=Some(reference);bytes=bytes.checked_add(material.bytes).ok_or("installation_trust_materials_oversized")?;
            if bytes>TOTAL{return Err("installation_trust_materials_oversized");}
            if material.purpose==Purpose::TrustAnchor{if anchor.replace(material).is_some()||material.bytes!=32{return Err("installation_trust_anchor_invalid");}}
            entries.push(PinnedFile{relative_path:material.relative_path.clone(),bytes:material.bytes,sha256:reference.sha256.clone()});
        }
        let required:&[Purpose]=if index.trust_mode=="publisher"{&[Purpose::PublisherProvenance]}else{
            &[Purpose::VerifierCodeIndex,Purpose::QualificationSuite,Purpose::IndependentReview,Purpose::IndependentAcceptance,Purpose::AnchorGeneration]};
        if !required.iter().all(|purpose|index.materials.iter().any(|m|m.purpose==*purpose)){return Err("installation_trust_source_incomplete");}
        let anchor=anchor.ok_or("installation_trust_anchor_invalid")?;
        let pins=ResourcePins::hold(root,&entries)?;
        let key=pins.read_held_bytes(&anchor.relative_path,32)?;
        let key_hex=key.iter().map(|byte|format!("{byte:02x}")).collect::<String>();
        if key.len()!=32||key_hex!=index.public_key_hex{return Err("installation_trust_anchor_invalid");}
        directory.assert_current()?;
        Ok(Self{index,pins,_selected_index:selected,directory,index_sha256:digest(&raw)})
    }
    pub(crate) fn assert_current(&self)->Result<(),&'static str>{self.directory.assert_current()?;let observation=self.pins.observe_all()?;self.pins.assert_current(&observation)}
    pub(crate) fn key(&self)->Result<[u8;32],&'static str>{let anchor=self.index.materials.iter().find(|m|m.purpose==Purpose::TrustAnchor).ok_or("installation_trust_anchor_invalid")?;
        self.pins.read_held_bytes(&anchor.relative_path,32)?.try_into().map_err(|_|"installation_trust_anchor_invalid")}
    pub(crate) fn issuer(&self)->&str{&self.index.issuer_id}
    pub(crate) fn mode(&self)->&str{&self.index.trust_mode}
    pub(crate) fn index_sha256(&self)->&str{&self.index_sha256}
    pub(crate) fn require_ref(&self,reference:&MaterialRef,purpose:&str)->Result<(),&'static str>{
        let expected:Purpose=serde_json::from_value(Value::String(purpose.into())).map_err(|_|"qualification_material_purpose_invalid")?;
        let material=self.index.materials.iter().find(|m|&m.r#ref==reference&&m.purpose==expected).ok_or("qualification_material_missing")?;
        let bytes=self.pins.read_held_bytes(&material.relative_path,LIMIT)?;
        if bytes.len()as u64!=material.bytes||digest(&bytes)!=reference.sha256{return Err("qualification_material_changed");}Ok(())
    }
    pub(crate) fn refs(&self)->Vec<&MaterialRef>{self.index.materials.iter().map(|m|&m.r#ref).collect()}
}

pub(crate) struct InstallationTrustProducer;
pub(crate) struct PreparedInstallationTrust {
    installation:Arc<NativeInstallationGuards>,control:Arc<ResourcePins>,resources:Arc<crate::engine::LaunchResources>,directory:Arc<OwnerDirectory>,
    materials:Arc<TrustMaterials>,input:TrustInput,intent:Value,action:String,accepted_at_us:u64,session:u32,deadline:Instant,
}
impl InstallationTrustProducer {
    pub(crate) fn prepare_trust(installation:Arc<NativeInstallationGuards>,control:Arc<ResourcePins>,resources:Arc<crate::engine::LaunchResources>,directory:Arc<OwnerDirectory>,parent:usize,materials:Arc<TrustMaterials>)->Result<PreparedInstallationTrust,&'static str>{
        if !Arc::ptr_eq(&installation.payload,&resources.pins)||control.root()!=installation.control_root()?{return Err("installation_trust_owner_mismatch");}
        let session=owner_setup_window::interactive_session()?;let action=crate::resource_authority::private_startup_id()?;
        let deadline=Instant::now()+Duration::from_secs(120);
        let intent=json!({"format":"native-installation-trust-intent-v1","action_id":action,"host_image":installation.inputs.installed_native_image,
            "host_sha256":installation.inputs.installed_native_image_sha256,"host_build_receipt_sha256":installation.receipt_sha256(),
            "control_root":crate::load_policy::text(installation.control_root()?)?,"issuer_id":materials.index.issuer_id,"trust_mode":materials.index.trust_mode,
            "public_key_hex":materials.index.public_key_hex,"material_refs":materials.refs(),"os_session":session,"permission":"installation-trust-source-only"});
        let check=||{installation.image_is_current_process()?;let observed=installation.observe()?;installation.assert_current(&observed)?;
            directory.assert_current()?;materials.assert_current()?;let observation=control.observe_all()?;control.assert_current(&observation)?;
            if owner_setup_window::interactive_session()?!=session{return Err("installation_trust_session_changed");}Ok(())};
        check()?;
        let details=format!("接纳本机安装验证来源，不批准项目制作或缺少的测试。\n安装程序：{}\n构建收据：{}\n受保护目录：{}\n来源：{} ({})\n公钥指纹：{}\n完整材料：{}\n权限：仅建立本机安装验证来源；资源仍需完整测试、许可与独立验收。",
            installation.inputs.installed_native_image,installation.receipt_sha256(),crate::load_policy::text(installation.control_root()?)?,materials.index.issuer_id,materials.index.trust_mode,
            digest(&materials.key()?),String::from_utf8(canonical(&serde_json::to_value(&materials.index.materials).map_err(|_|"installation_trust_materials_invalid")?)?).map_err(|_|"installation_trust_materials_invalid")?);
        let input=owner_setup_window::show_trust(parent,&details,deadline,&check)?;check()?;
        let accepted_at_us=now()?;
        Ok(PreparedInstallationTrust{installation,control,resources,directory,materials,input,intent,action,accepted_at_us,session,deadline})
    }
}
pub(crate) struct BoundInstallationTrust {
    original:Arc<TrustAdmissionOriginal>,pipe:OwnerSetupPipe,
}
/// Shared strong original action. No pipe/I/O is shared across threads; its
/// original OS input and files survive even if thread creation fails.
pub(crate) struct TrustAdmissionOriginal {
    prepared:PreparedInstallationTrust,process:Arc<Mutex<OwnedProcess>>,source:Arc<InitializationCurrent>,instance:String,
}
impl PreparedInstallationTrust {
    pub(crate) fn installation(&self)->&Arc<NativeInstallationGuards>{&self.installation}
    pub(crate) fn materials(&self)->&Arc<TrustMaterials>{&self.materials}
    pub(crate) fn action_id(&self)->&str{&self.action}
    pub(crate) fn deadline(&self)->Instant{self.deadline}
    pub(crate) fn bind_instance(self,process:Arc<Mutex<OwnedProcess>>,source:Arc<InitializationCurrent>,instance:&str)->Result<BoundInstallationTrust,&'static str>{
        if !id(instance)||Instant::now()>=self.deadline||self.input.accepted_at>=self.deadline{return Err("installation_trust_binding_invalid");}
        source.assert_owned_process(&process)?;self.directory.assert_current()?;self.materials.assert_current()?;
        if owner_setup_window::interactive_session()?!=self.session{return Err("installation_trust_session_changed");}
        let pipe=OwnerSetupPipe::create_trust(self.installation.clone(),instance)?;
        Ok(BoundInstallationTrust{original:Arc::new(TrustAdmissionOriginal{prepared:self,process,source,instance:instance.into()}),pipe})
    }
}
#[derive(Deserialize)]#[serde(deny_unknown_fields)]
struct Admit {wire:String,session:String,seq:u64,method:String,instance_id:String}
impl BoundInstallationTrust {
    pub(crate) fn original(&self)->Arc<TrustAdmissionOriginal>{self.original.clone()}
    pub(crate) fn locator(&self)->Value{let source=&self.pipe.locator;json!({"pipe":source.pipe,"session":source.session,"role":"installation-trust-admission",
        "server":source.server,"purpose":"installation-trust-admission","instance_id":self.original.instance})}
    pub(crate) fn start(self)->Result<JoinHandle<Result<(),&'static str>>,&'static str>{
        thread::Builder::new().name("installation-trust-admission".into()).spawn(move||self.serve()).map_err(|_|"installation_trust_unavailable")
    }
    fn serve(self)->Result<(),&'static str>{
        let original=&self.original;
        let deadline=original.prepared.deadline.min(Instant::now()+Duration::from_secs(10));
        let result=(||{
            self.pipe.connect(&original.process,deadline)?;original.assert_current()?;
            let raw=self.pipe.receive(deadline)?;
            let request:Admit=serde_json::from_slice(&raw).map_err(|_|"installation_trust_frame_invalid")?;
            // Typed reserialization rejects duplicate keys as well as unknowns.
            let value:Value=serde_json::from_slice(&raw).map_err(|_|"installation_trust_frame_invalid")?;
            if canonical(&value)?!=raw||request.wire!=WIRE||request.session!=self.pipe.locator.session||request.seq!=1||request.method!="admit"||request.instance_id!=original.instance{return Err("installation_trust_frame_invalid");}
            self.pipe.assert_peer(&original.process)?;original.assert_current()?;
            self.pipe.send(&json!({"wire":WIRE,"session":request.session,"seq":1,"status":200,"code":"trust_source_admitted","instance_id":original.instance,"trust_admission":original.admission()?}),deadline)?;
            // A successful send is not a committed Backend trust receipt. There
            // is no retry, second admit, or new action on an unknown outcome.
            Ok(())
        })();
        if let Err(code)=result{
            // Only an authenticated original peer receives a bounded safe
            // error. A failed write remains the original unknown outcome.
            if Instant::now()<deadline&&self.pipe.assert_peer(&original.process).is_ok(){
                let status=match code{"installation_trust_frame_invalid"=>422,"installation_trust_session_changed"=>403,"installation_trust_source_changed"=>409,_=>503};
                let _=self.pipe.send(&json!({"wire":WIRE,"session":self.pipe.locator.session,"seq":1,"status":status,"code":code,"instance_id":original.instance,"trust_admission":null}),deadline);
            }
        }
        // Keep the actual admission, input and all original handles after EOF,
        // error or successful send until this exact child and Job are terminal.
        loop{let terminal=original.process.lock().unwrap_or_else(|poisoned|poisoned.into_inner());let done=terminal.wait_exit(20).is_ok_and(|value|value.is_some())&&terminal.job_pids().is_ok_and(|pids|pids.is_empty());drop(terminal);
            if done{break;}thread::sleep(Duration::from_millis(20));}
        self.pipe.disconnect();result
    }
}
impl TrustAdmissionOriginal {
    pub(crate) fn action_id(&self)->&str{&self.prepared.action}
    pub(crate) fn assert_current(&self)->Result<(),&'static str>{self.source.assert_owned_process(&self.process)?;self.assert_installer_current()}
    pub(crate) fn assert_installer_current(&self)->Result<(),&'static str>{self.prepared.installation.image_is_current_process()?;self.prepared.materials.assert_current()?;self.prepared.directory.assert_current()?;
        let observed=self.prepared.control.observe_all()?;self.prepared.control.assert_current(&observed)?;
        if !Arc::ptr_eq(&self.prepared.installation.payload,&self.prepared.resources.pins)||owner_setup_window::interactive_session()?!=self.prepared.session{return Err("installation_trust_source_changed");}Ok(())}
    pub(crate) fn admission(&self)->Result<Value,&'static str>{Ok(json!({"action_id":self.prepared.action,"accepted_at_us":self.prepared.accepted_at_us,"issuer_id":self.prepared.materials.index.issuer_id,
        "trust_mode":self.prepared.materials.index.trust_mode,"public_key_hex":self.prepared.materials.index.public_key_hex,"material_refs":self.prepared.materials.refs(),
        "host_build_receipt_sha256":self.prepared.installation.receipt_sha256(),"intent_sha256":digest(&canonical(&self.prepared.intent)?)}))}
    pub(crate) fn installation(&self)->&Arc<NativeInstallationGuards>{&self.prepared.installation}
    pub(crate) fn materials(&self)->&Arc<TrustMaterials>{&self.prepared.materials}
    pub(crate) fn instance(&self)->&str{&self.instance}
    pub(crate) fn process(&self)->&Arc<Mutex<OwnedProcess>>{&self.process}
    pub(crate) fn source(&self)->&Arc<InitializationCurrent>{&self.source}
}
