//! A committed file is evidence only when it matches the original installer
//! action and retained candidate. Native never opens the qualification SQLite.
use std::{fs::{File,OpenOptions},io::Read,path::{Path,PathBuf},sync::Arc};
use serde::{Deserialize,Serialize};
use serde_json::{json,Value};
use crate::{installation_trust::TrustAdmissionOriginal,native_installation::canonical,
    owner_setup_directory::OwnerDirectory,qualification_pack::VerifiedQualificationCandidate,
    qualification_record::{digest,QualificationRef,I64_MAX},resource_pins::{PinnedFile,ResourcePins}};
const LIMIT:usize=4*1024*1024;
const CONTROL:&str="InstallationQualificationControl.json";
const SNAPSHOT:&str="QualificationTrustSnapshot.json";
const EVIDENCE:&str="CommittedInstallationEvidence.json";
#[derive(Deserialize,Serialize)]#[serde(deny_unknown_fields)]
struct Control {format:String,namespace:String,instance_id:String,minimum_revision:u64,pending_request_sha256:Option<String>}
#[derive(Deserialize,Serialize)]#[serde(deny_unknown_fields)]
struct Snapshot {format:String,instance_id:String,registry_revision:u64,trust_admission_ref:Option<QualificationRef>,current_record_ref:Option<QualificationRef>,state:String}
#[derive(Deserialize,Serialize)]#[serde(deny_unknown_fields)]
struct Request {action_id:String,kind:String,trust_admission_ref:QualificationRef,record_ref:Option<QualificationRef>,expected_registry_revision:u64}
#[derive(Deserialize,Serialize)]#[serde(deny_unknown_fields)]
struct TrustCommit {admission_ref:QualificationRef,action_ref:QualificationRef,request:Request,request_sha256:String,registry_revision:u64,source_receipt:Value}
#[derive(Deserialize,Serialize)]#[serde(deny_unknown_fields)]
struct RecordCommit {record_ref:QualificationRef,action_ref:QualificationRef,request:Request,request_sha256:String,registry_revision:u64,source_receipt:Value}
#[derive(Deserialize,Serialize)]#[serde(deny_unknown_fields)]
struct Evidence {format:String,instance_id:String,registry_revision:u64,trust_commit:TrustCommit,record_commit:Option<RecordCommit>}
struct HeldCompletion {control:Control,snapshot:Snapshot,evidence:Evidence,pins:ResourcePins,directory:OwnerDirectory,_selected:Vec<File>}
fn value<T:Serialize>(item:&T)->Result<Value,&'static str>{serde_json::to_value(item).map_err(|_|"qualification_completion_invalid")}
fn parse<T:for<'a>Deserialize<'a>+Serialize>(raw:&[u8],lf:bool)->Result<T,&'static str>{
    let body=if lf{raw.strip_suffix(b"\n").ok_or("qualification_control_noncanonical")?}else{raw};
    let item:T=serde_json::from_slice(body).map_err(|_|"qualification_completion_invalid")?;
    if canonical(&value(&item)?)?!=body{return Err("qualification_completion_noncanonical");}Ok(item)
}
impl HeldCompletion {
    fn hold(root:&Path,instance:&str)->Result<Self,&'static str>{
        let root=root.join("Control");let sid=crate::resource_authority::current_identity()?.sid;
        let directory=OwnerDirectory::hold(&root,&sid)?;
        let mut selected=Vec::new();let mut raw=Vec::new();let mut entries=Vec::new();
        use std::os::windows::fs::OpenOptionsExt;
        for name in [CONTROL,SNAPSHOT,EVIDENCE]{
            let file=OpenOptions::new().read(true).share_mode(1).custom_flags(0x0020_0000).open(root.join(name)).map_err(|_|"qualification_completion_unavailable")?;
            if !file.metadata().map_err(|_|"qualification_completion_unavailable")?.is_file(){return Err("qualification_completion_invalid");}
            let mut body=Vec::new();(&file).take(LIMIT as u64+1).read_to_end(&mut body).map_err(|_|"qualification_completion_unavailable")?;
            if body.is_empty()||body.len()>LIMIT{return Err("qualification_completion_size");}
            entries.push(PinnedFile{relative_path:name.into(),bytes:body.len()as u64,sha256:digest(&body)});raw.push(body);selected.push(file);
        }
        let control:Control=parse(&raw[0],true)?;let snapshot:Snapshot=parse(&raw[1],false)?;let evidence:Evidence=parse(&raw[2],false)?;
        if control.format!="installation-qualification-control-v1"||control.namespace!="installation-qualification"
            ||snapshot.format!="installation-qualification-trust-snapshot-v1"||evidence.format!="installation-committed-evidence-v1"
            ||control.instance_id!=instance||snapshot.instance_id!=instance||evidence.instance_id!=instance
            ||control.minimum_revision==0||control.minimum_revision>I64_MAX||snapshot.registry_revision!=control.minimum_revision
            ||evidence.registry_revision!=control.minimum_revision||control.pending_request_sha256.is_some()
            ||!matches!(snapshot.state.as_str(),"not_ready"|"qualified"|"revoked"){return Err("qualification_completion_changed");}
        let pins=ResourcePins::hold(&root,&entries)?;
        for(index,name)in [CONTROL,SNAPSHOT,EVIDENCE].iter().enumerate(){if pins.read_held_bytes(name,LIMIT)?!=raw[index]{return Err("qualification_completion_changed");}}
        let held=Self{control,snapshot,evidence,pins,directory,_selected:selected};held.assert_current()?;Ok(held)
    }
    fn assert_current(&self)->Result<(),&'static str>{self.directory.assert_current()?;let observed=self.pins.observe_all()?;self.pins.assert_current(&observed)}
    fn assert_trust(&self,original:&TrustAdmissionOriginal)->Result<(),&'static str>{
        original.assert_installer_current()?;let trust=&self.evidence.trust_commit;let receipt=original.admission()?;
        let body_sha=digest(&canonical(&receipt)?);let reference=&trust.admission_ref;
        for item in [reference,&trust.action_ref,&trust.request.trust_admission_ref]{item.validate()?;}
        if trust.source_receipt!=receipt||reference.document_id!=format!("trust.{body_sha}")||reference.revision!=1||reference.sha256!=body_sha
            ||trust.registry_revision!=1||trust.action_ref.document_id!=receipt["action_id"]||trust.action_ref.revision!=trust.registry_revision||trust.action_ref.sha256!=body_sha
            ||trust.request.action_id!=trust.action_ref.document_id||trust.request.kind!="trust_admit"||trust.request.record_ref.is_some()
            ||trust.request.expected_registry_revision!=0||trust.request.trust_admission_ref!=*reference
            ||digest(&canonical(&value(&trust.request)?)?)!=trust.request_sha256
            ||self.snapshot.trust_admission_ref.as_ref()!=Some(reference){return Err("qualification_trust_action_mismatch");}Ok(())
    }
}
/// A strong original trust action plus the exact committed receipt relation.
/// Mutable completion files are checked in a short held read and released
/// before seq4 lets Backend replace them. This is not production current.
pub(crate) struct CommittedTrustSource {original:Arc<TrustAdmissionOriginal>,root:PathBuf,reference:QualificationRef,revision:u64}
impl CommittedTrustSource {
    pub(crate) fn read(original:Arc<TrustAdmissionOriginal>,root:&Path)->Result<Arc<Self>,&'static str>{
        original.assert_current()?;let held=HeldCompletion::hold(root,original.instance())?;held.assert_trust(&original)?;
        if held.snapshot.state!="not_ready"||held.snapshot.current_record_ref.is_some()||held.evidence.record_commit.is_some()||held.evidence.registry_revision!=1{return Err("qualification_first_trust_required");}
        let reference=held.evidence.trust_commit.admission_ref;
        Ok(Arc::new(Self{original,root:root.into(),reference,revision:1}))
    }
    pub(crate) fn assert_current(&self)->Result<(),&'static str>{let held=HeldCompletion::hold(&self.root,self.original.instance())?;held.assert_trust(&self.original)?;
        if held.evidence.registry_revision!=self.revision||held.evidence.record_commit.is_some()||held.snapshot.state!="not_ready"{return Err("qualification_trust_changed");}Ok(())}
    pub(crate) fn original(&self)->&Arc<TrustAdmissionOriginal>{&self.original}
    pub(crate) fn reference(&self)->&QualificationRef{&self.reference}
    pub(crate) fn revision(&self)->u64{self.revision}
    pub(crate) fn root(&self)->&Path{&self.root}
}
/// Installed only by the original driver after actual seq4 commit. The three
/// opened files remain deny-write/delete held members throughout this epoch.
/// A writer transition must first close/drain and retire this epoch; sharing
/// failures are busy/unknown, never a reason to weaken the pin.
pub(crate) struct CommittedQualificationSource {held:HeldCompletion,action:Arc<crate::installation_record::RecordAdmissionOriginal>,target_source:Arc<crate::windows_native_sources::VerifiedSystemContext>}
impl CommittedQualificationSource {
    pub(crate) fn read(action:Arc<crate::installation_record::RecordAdmissionOriginal>,target_source:Arc<crate::windows_native_sources::VerifiedSystemContext>)->Result<Self,&'static str>{
        let held=HeldCompletion::hold(action.trust().root(),action.instance())?;
        let source=Self{held,action,target_source};source.assert_current()?;Ok(source)
    }
    pub(crate) fn candidate(&self)->&Arc<VerifiedQualificationCandidate>{self.action.candidate()}
    pub(crate) fn instance(&self)->&str{self.action.instance()}
    pub(crate) fn registry_revision(&self)->u64{self.held.evidence.registry_revision}
    pub(crate) fn revocation_floor(&self)->u64{self.held.control.minimum_revision}
    pub(crate) fn assert_original_target_source(&self,source:&Arc<crate::windows_native_sources::VerifiedSystemContext>)->Result<(),&'static str>{
        if !Arc::ptr_eq(source,&self.target_source){return Err("setup_production_original_source_required");}self.assert_current()
    }
    pub(crate) fn assert_current(&self)->Result<(),&'static str>{
        self.held.assert_current()?;self.held.assert_trust(self.action.trust().original())?;
        self.action.assert_installer_current()?;let record=self.held.evidence.record_commit.as_ref().ok_or("qualification_record_not_committed")?;
        self.candidate().assert_target_current(&self.target_source)?;
        let reference=self.candidate().record.reference()?;let receipt=self.action.admission()?;
        record.record_ref.validate()?;record.action_ref.validate()?;
        let request=&record.request;request.trust_admission_ref.validate()?;
        let expected=request.expected_registry_revision.checked_add(1).filter(|value|*value<=I64_MAX).ok_or("qualification_revision_exhausted")?;
        if self.held.snapshot.state!="qualified"||self.held.snapshot.current_record_ref.as_ref()!=Some(&reference)||record.record_ref!=reference
            ||record.source_receipt!=receipt||request.kind!="record_admit"||request.action_id!=receipt["action_id"]
            ||record.action_ref.document_id!=request.action_id||record.action_ref.revision!=expected||record.action_ref.sha256!=digest(&canonical(&receipt)?)
            ||record.registry_revision!=expected||expected!=self.registry_revision()||request.expected_registry_revision!=self.action.trust().revision()
            ||request.trust_admission_ref!=*self.action.trust().reference()||request.record_ref.as_ref()!=Some(&reference)
            ||record.request_sha256!=digest(&canonical(&value(request)?)?){return Err("qualification_record_action_mismatch");}
        self.candidate().record.assert_time(crate::qualification_registry::checked_at_us()?)
    }
    pub(crate) fn binding(&self,checked_at_us:u64)->Result<Value,&'static str>{
        self.candidate().record.assert_time(checked_at_us)?;
        Ok(json!({"record":self.candidate().record.as_value()?,"record_sha256":self.candidate().sha256(),"registry_revision":self.registry_revision(),"revocation_floor":self.revocation_floor(),"checked_at_us":checked_at_us}))
    }
}
