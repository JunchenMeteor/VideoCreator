//! Independent native installer action. Trust admission is not consent to a
//! qualification record, and a parsed sidecar never constructs this member.
use std::{sync::Arc,thread::{self,JoinHandle},time::{Duration,Instant}};
use serde::Deserialize;
use serde_json::{json,Value};
use crate::{native_installation::canonical,owner_setup_window::{self,RecordInput},
    qualification_commit::CommittedTrustSource,qualification_pack::VerifiedQualificationCandidate,
    qualification_record::digest,resource_authority::OwnerSetupPipe};
const WIRE:&str="held-installation-record-v1-candidate";
pub(crate) struct InstallationRecordProducer;
pub(crate) struct PreparedRecordInput {
    candidate:Arc<VerifiedQualificationCandidate>,input:RecordInput,session:u32,action:String,
    accepted_at_us:u64,intent:Value,deadline:Instant,trust_action_id:String,
}
pub(crate) struct RecordAdmissionOriginal {
    trust:Arc<CommittedTrustSource>,candidate:Arc<VerifiedQualificationCandidate>,_input:RecordInput,
    session:u32,action:String,accepted_at_us:u64,intent:Value,deadline:Instant,
}
pub(crate) struct BoundInstallationRecord {original:Arc<RecordAdmissionOriginal>,pipe:OwnerSetupPipe}
impl InstallationRecordProducer {
    pub(crate) fn prepare_record_input(trust:&crate::installation_trust::PreparedInstallationTrust,candidate:Arc<VerifiedQualificationCandidate>,parent:usize)->Result<PreparedRecordInput,&'static str>{
        if !Arc::ptr_eq(trust.installation(),&candidate.installation)||!Arc::ptr_eq(trust.materials(),&candidate.materials){return Err("installation_record_original_source_required");}
        candidate.assert_current()?;
        let session=owner_setup_window::interactive_session()?;let action=crate::resource_authority::private_startup_id()?;
        // This independent input is collected BEFORE child launch, with the
        // complete signed record and exact original trust action in view. The
        // resulting SQLite instance/ref is bound once after seq3; no waiting
        // window can silently extend any 10-second protocol exchange.
        let intent=json!({"format":"native-installation-record-intent-v1","action_id":action,"trust_action_id":trust.action_id(),
            "expected_registry_revision":1,"record_ref":candidate.record.reference()?,
            "record_sha256":candidate.sha256(),"record":candidate.record.as_value()?,"host_build_receipt_sha256":candidate.installation.receipt_sha256(),
            "material_index_sha256":candidate.materials.index_sha256(),"os_session":session,"permission":"installation-record-admission-only"});
        let deadline=trust.deadline().min(Instant::now()+Duration::from_secs(120));
        let check=||{candidate.assert_current()?;
            candidate.record.assert_time(crate::qualification_registry::checked_at_us()?)?;
            if owner_setup_window::interactive_session()?!=session{return Err("installation_record_source_denied");}Ok(())};
        check()?;
        let details=format!("接纳此安装包的完整验证结果，不批准项目制作或扩大费用。\n完整目标、资源、许可、测试与签名记录：\n{}",
            String::from_utf8(canonical(&intent)?).map_err(|_|"installation_record_frame_invalid")?);
        let input=owner_setup_window::show_record(parent,&details,deadline,&check)?;check()?;
        if input.accepted_at>=deadline{return Err("installation_record_timeout");}
        Ok(PreparedRecordInput{candidate,input,session,action,accepted_at_us:crate::qualification_registry::checked_at_us()?,intent,deadline,trust_action_id:trust.action_id().into()})
    }
}
impl PreparedRecordInput {
    pub(crate) fn bind(self,trust:Arc<CommittedTrustSource>)->Result<BoundInstallationRecord,&'static str>{
        if Instant::now()>=self.deadline||self.input.accepted_at>=self.deadline||trust.original().action_id()!=self.trust_action_id
            ||!Arc::ptr_eq(trust.original().installation(),&self.candidate.installation)||!Arc::ptr_eq(trust.original().materials(),&self.candidate.materials){return Err("installation_record_original_source_required");}
        trust.original().assert_current()?;trust.assert_current()?;
        let original=Arc::new(RecordAdmissionOriginal{trust,candidate:self.candidate,_input:self.input,session:self.session,action:self.action,accepted_at_us:self.accepted_at_us,intent:self.intent,deadline:self.deadline});
        original.assert_installer_current()?;
        let pipe=OwnerSetupPipe::create_record(original.candidate.installation.clone(),original.instance())?;
        Ok(BoundInstallationRecord{original,pipe})
    }
}
impl RecordAdmissionOriginal {
    pub(crate) fn trust(&self)->&Arc<CommittedTrustSource>{&self.trust}
    pub(crate) fn candidate(&self)->&Arc<VerifiedQualificationCandidate>{&self.candidate}
    pub(crate) fn instance(&self)->&str{self.trust.original().instance()}
    pub(crate) fn action_id(&self)->&str{&self.action}
    pub(crate) fn assert_installer_current(&self)->Result<(),&'static str>{
        self.trust.original().assert_installer_current()?;self.candidate.assert_current()?;
        if owner_setup_window::interactive_session()?!=self.session{return Err("installation_record_source_denied");}Ok(())
    }
    pub(crate) fn admission(&self)->Result<Value,&'static str>{Ok(json!({"action_id":self.action,"accepted_at_us":self.accepted_at_us,"kind":"record_admit",
        "trust_admission_ref":self.trust.reference(),"expected_registry_revision":self.trust.revision(),"record":self.candidate.record.as_value()?,
        "record_sha256":self.candidate.sha256(),"host_build_receipt_sha256":self.candidate.installation.receipt_sha256(),
        "intent_sha256":digest(&canonical(&self.intent)?),"material_index_sha256":self.candidate.materials.index_sha256()}))}
}
#[derive(Deserialize)]#[serde(deny_unknown_fields)]
struct Admit {wire:String,session:String,seq:u64,method:String,instance_id:String}
impl BoundInstallationRecord {
    pub(crate) fn original(&self)->Arc<RecordAdmissionOriginal>{self.original.clone()}
    pub(crate) fn locator(&self)->Value{let locator=&self.pipe.locator;json!({"pipe":locator.pipe,"session":locator.session,"role":"installation-record-admission",
        "server":locator.server,"purpose":"installation-record-admission","instance_id":self.original.instance()})}
    pub(crate) fn start(self)->Result<JoinHandle<Result<(),&'static str>>,&'static str>{thread::Builder::new().name("installation-record-admission".into()).spawn(move||self.serve()).map_err(|_|"installation_record_unavailable")}
    fn serve(self)->Result<(),&'static str>{
        let original=&self.original;let process=original.trust.original().process();let deadline=original.deadline.min(Instant::now()+Duration::from_secs(10));
        let result=(||{
            self.pipe.connect(process,deadline)?;original.trust.original().assert_current()?;original.assert_installer_current()?;original.trust.assert_current()?;
            let raw=self.pipe.receive(deadline)?;let request:Admit=serde_json::from_slice(&raw).map_err(|_|"installation_record_frame_invalid")?;
            let value:Value=serde_json::from_slice(&raw).map_err(|_|"installation_record_frame_invalid")?;
            if canonical(&value)?!=raw||request.wire!=WIRE||request.session!=self.pipe.locator.session||request.seq!=1||request.method!="admit_record"||request.instance_id!=original.instance(){return Err("installation_record_frame_invalid");}
            self.pipe.assert_peer(process)?;original.assert_installer_current()?;original.trust.assert_current()?;
            self.pipe.send(&json!({"wire":WIRE,"session":request.session,"seq":1,"status":200,"code":"record_source_admitted","instance_id":original.instance(),"record_admission":original.admission()?}),deadline)
        })();
        if result.is_err()&&Instant::now()<deadline&&self.pipe.assert_peer(process).is_ok(){let _=self.pipe.send(&json!({"wire":WIRE,"session":self.pipe.locator.session,"seq":1,"status":503,"code":"installation_record_unavailable","instance_id":original.instance(),"record_admission":null}),deadline);}
        loop{let owned=process.lock().unwrap_or_else(|poisoned|poisoned.into_inner());let terminal=owned.wait_exit(20).is_ok_and(|exit|exit.is_some())&&owned.job_pids().is_ok_and(|pids|pids.is_empty());drop(owned);if terminal{break;}thread::sleep(Duration::from_millis(20));}
        self.pipe.disconnect();result
    }
}
