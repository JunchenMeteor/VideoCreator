//! ADR0043/44's single record model. Parsing/signature verification creates a
//! candidate only. Original committed trust/installation current is separate.
use std::collections::BTreeSet;
use ed25519_dalek::{Signature,VerifyingKey};
use serde::{Deserialize,Serialize};
use sha2::{Digest,Sha256};
use crate::{native_installation::canonical,resource_pins::PinnedFile};

pub(crate) const RECORD_LIMIT:usize=1024*1024;
pub(crate) const I64_MAX:u64=i64::MAX as u64;
#[derive(Deserialize,Serialize,PartialEq,Eq,PartialOrd,Ord)]
#[serde(deny_unknown_fields)]
pub(crate) struct QualificationRef {pub document_id:String,pub revision:u64,pub sha256:String}
impl QualificationRef {
    pub(crate) fn validate(&self)->Result<(),&'static str>{
        if !identifier(&self.document_id)||self.revision==0||self.revision>I64_MAX||!sha(&self.sha256){return Err("qualification_ref_invalid");}Ok(())
    }
}
#[derive(Deserialize,Serialize)]#[serde(deny_unknown_fields)]
pub(crate) struct Target {pub os:String,pub arch:String,pub conditions:Vec<Condition>}
#[derive(Deserialize,Serialize)]#[serde(tag="kind",deny_unknown_fields)]
pub(crate) enum Condition {
    #[serde(rename="os_floor")]OsFloor{product:String,version:[u32;3],report_ref:QualificationRef},
    #[serde(rename="python_abi")]PythonAbi{implementation:String,version:[u32;3],abi_tag:String,gil:String,report_ref:QualificationRef},
    #[serde(rename="cpu_features")]CpuFeatures{features:Vec<String>,report_ref:QualificationRef},
    #[serde(rename="windows_crt")]WindowsCrt{components:Vec<CrtComponent>,report_ref:QualificationRef},
    #[serde(rename="libc")]Libc{family:String,version:[u32;3],report_ref:QualificationRef},
}
#[derive(Deserialize,Serialize)]#[serde(deny_unknown_fields)]
pub(crate) struct CrtComponent {pub(crate) name:String,pub(crate) floor:[u32;4]}
impl Condition {
    fn kind(&self)->&str{match self{Self::OsFloor{..}=>"os_floor",Self::PythonAbi{..}=>"python_abi",Self::CpuFeatures{..}=>"cpu_features",Self::WindowsCrt{..}=>"windows_crt",Self::Libc{..}=>"libc"}}
    pub(crate) fn report(&self)->&QualificationRef{match self{Self::OsFloor{report_ref,..}|Self::PythonAbi{report_ref,..}|Self::CpuFeatures{report_ref,..}|Self::WindowsCrt{report_ref,..}|Self::Libc{report_ref,..}=>report_ref}}
}
impl Target {
    fn validate(&self)->Result<(),&'static str>{
        let expected:&[&str]=match(self.os.as_str(),self.arch.as_str()){
            ("windows","x86_64")=>&["os_floor","python_abi","cpu_features","windows_crt"],
            ("linux","x86_64")=>&["os_floor","python_abi","cpu_features","libc"],
            ("macos","x86_64"|"aarch64")=>&["os_floor","python_abi","cpu_features"],
            _=>return Err("qualification_target_invalid"),
        };
        if self.conditions.len()!=expected.len()||!self.conditions.iter().zip(expected).all(|(condition,name)|condition.kind()==*name){return Err("qualification_conditions_invalid");}
        for condition in &self.conditions {
            condition.report().validate()?;
            match condition {
                Condition::OsFloor{product,version,..}=>{
                    let expected=match self.os.as_str(){"windows"=>"windows_nt","linux"=>"linux_kernel",_=>"darwin"};
                    if product!=expected||version.iter().all(|v|*v==0){return Err("qualification_floor_unknown");}
                },
                Condition::PythonAbi{implementation,version,abi_tag,gil,..}=>if implementation!="cpython"||version!=&[3,13,16]||abi_tag!="cp313"||gil!="standard"{return Err("qualification_python_abi_invalid");},
                Condition::CpuFeatures{features,..}=>{
                    let order=["x86_sse2","x86_avx","x86_avx2","arm_neon"];
                    let mut previous=None;
                    for feature in features {
                        let position=order.iter().position(|item|*item==feature).ok_or("qualification_cpu_invalid")?;
                        if previous.is_some_and(|old|old>=position)||(self.arch=="aarch64")!=(feature=="arm_neon"){return Err("qualification_cpu_invalid");}previous=Some(position);
                    }
                },
                Condition::WindowsCrt{components,..}=>{
                    let names=["mfc140u.dll","msvcp140.dll","msvcp140_1.dll","msvcp140_2.dll","msvcp140_atomic_wait.dll","msvcp140_codecvt_ids.dll","vcruntime140.dll","vcruntime140_1.dll"];
                    if components.len()!=names.len()||!components.iter().zip(names).all(|(component,name)|component.name==name&&component.floor.iter().any(|v|*v!=0)){return Err("qualification_crt_floor_unknown");}
                },
                Condition::Libc{family,version,..}=>if family!="glibc"||version.iter().all(|v|*v==0){return Err("qualification_libc_unknown");},
            }
        }Ok(())
    }
}
#[derive(Deserialize,Serialize)]#[serde(deny_unknown_fields)]
pub(crate) struct QualificationProfile {
    pub name:String,pub artifact_version:String,pub executable:String,pub bootstrap:String,pub entry_module:String,
    pub command:Option<String>,pub adapter_module:Option<String>,pub adapter_callable:Option<String>,pub load_policy_sha256:String,
    pub required_files:Vec<PinnedFile>,pub required_files_sha256:String,pub report_refs:Vec<QualificationRef>,
}
#[derive(Deserialize,Serialize)]#[serde(deny_unknown_fields)]
pub(crate) struct QualificationRecord {
    pub format:String,pub record_id:String,pub revision:u64,pub target:Target,
    pub registration_sha256:String,pub resource_manifest_sha256:String,pub runtime_manifest_sha256:String,
    pub host_build_receipt_sha256:String,pub full_file_map_sha256:String,pub engine_partition_sha256:String,
    pub workflow_version:String,pub driver_profile:String,pub roles:Vec<String>,pub profiles:Vec<QualificationProfile>,
    pub qualification_suite_ref:QualificationRef,pub runtime_report_refs:Vec<QualificationRef>,pub license_evidence_refs:Vec<QualificationRef>,pub build_provenance_refs:Vec<QualificationRef>,
    pub independent_review_ref:QualificationRef,pub independent_acceptance_ref:QualificationRef,
    pub valid_from_us:u64,pub expires_at_us:u64,pub issuer_id:String,pub trust_mode:String,pub signature:String,
}
pub(crate) fn identifier(value:&str)->bool{!value.is_empty()&&value.len()<=128&&value.bytes().all(|byte|byte.is_ascii_alphanumeric()||b"_.:-".contains(&byte))}
fn sha(value:&str)->bool{crate::load_policy::digest_valid(value)}
pub(crate) fn digest(raw:&[u8])->String{format!("{:x}",Sha256::digest(raw))}
fn ordered_refs(refs:&[QualificationRef])->Result<(),&'static str>{
    if refs.is_empty()||refs.len()>4096||!refs.windows(2).all(|pair|pair[0]<pair[1]){return Err("qualification_refs_invalid");}
    for reference in refs{reference.validate()?;}Ok(())
}
fn relative(value:&str)->bool{!value.is_empty()&&!value.contains(['\\',':'])&&!value.chars().any(char::is_control)&&value.split('/').all(|part|!part.is_empty()&&part!="."&&part!=".."&&!part.ends_with([' ','.']))}
pub(crate) fn decode_hex<const N:usize>(value:&str)->Result<[u8;N],&'static str>{
    if value.len()!=N*2||!value.bytes().all(|byte|byte.is_ascii_digit()||(b'a'..=b'f').contains(&byte)){return Err("qualification_hex_invalid");}
    let mut output=[0;N];for(index,pair)in value.as_bytes().chunks_exact(2).enumerate(){
        let digit=|byte:u8|if byte<=b'9'{byte-b'0'}else{byte-b'a'+10};output[index]=(digit(pair[0])<<4)|digit(pair[1]);
    }Ok(output)
}
impl QualificationRecord {
    pub(crate) fn parse(raw:&[u8])->Result<Self,&'static str>{
        if raw.is_empty()||raw.len()>RECORD_LIMIT{return Err("qualification_record_size");}
        let record:Self=serde_json::from_slice(raw).map_err(|_|"qualification_record_invalid")?;
        if canonical(&serde_json::to_value(&record).map_err(|_|"qualification_record_invalid")?)?!=raw{return Err("qualification_record_noncanonical");}
        record.validate()?;Ok(record)
    }
    fn validate(&self)->Result<(),&'static str>{
        if self.format!="installation-qualification-record-v1"||!identifier(&self.record_id)||!identifier(&self.issuer_id)||!identifier(&self.workflow_version)||!identifier(&self.driver_profile)
            ||self.revision==0||self.revision>I64_MAX||!matches!(self.trust_mode.as_str(),"publisher"|"local_verifier")
            ||self.valid_from_us==0||self.valid_from_us>=self.expires_at_us||self.expires_at_us>I64_MAX{return Err("qualification_record_invalid");}
        decode_hex::<64>(&self.signature)?;
        for hash in [&self.registration_sha256,&self.resource_manifest_sha256,&self.runtime_manifest_sha256,&self.host_build_receipt_sha256,&self.full_file_map_sha256,&self.engine_partition_sha256]{if !sha(hash){return Err("qualification_record_identity_invalid");}}
        self.target.validate()?;
        if self.roles!=["api","mcp","worker"]||self.profiles.len()!=4{return Err("qualification_roles_invalid");}
        for(profile,name)in self.profiles.iter().zip(["api","worker","mcp","asr"]){
            let service=name!="asr";let command=match name{"api"=>Some("serve"),"worker"=>Some("worker"),"mcp"=>Some("mcp-stdio"),_=>None};
            if profile.name!=name||!identifier(&profile.artifact_version)||!relative(&profile.executable)||!relative(&profile.bootstrap)
                ||profile.entry_module!=if service{"video_creator.cli.main"}else{"video_creator.media.asr_worker"}
                ||profile.command.as_deref()!=command||profile.adapter_module.as_deref()!=service.then_some("video_creator.cli.native_startup")
                ||profile.adapter_callable.as_deref()!=service.then_some("main_qualified")||!sha(&profile.load_policy_sha256)||!sha(&profile.required_files_sha256)
                ||profile.required_files.is_empty(){return Err("qualification_profile_invalid");}
            let mut folded=BTreeSet::new();let mut previous=None;
            for file in &profile.required_files{
                if !relative(&file.relative_path)||!sha(&file.sha256)||file.bytes>I64_MAX||!folded.insert(file.relative_path.to_lowercase())
                    ||previous.is_some_and(|old:&str|old>=file.relative_path.as_str()){return Err("qualification_profile_map_invalid");}previous=Some(&file.relative_path);
            }
            if digest(&canonical(&serde_json::to_value(&profile.required_files).map_err(|_|"qualification_profile_map_invalid")?)?)!=profile.required_files_sha256{return Err("qualification_profile_map_invalid");}
            ordered_refs(&profile.report_refs)?;
        }
        self.qualification_suite_ref.validate()?;self.independent_review_ref.validate()?;self.independent_acceptance_ref.validate()?;
        ordered_refs(&self.runtime_report_refs)?;ordered_refs(&self.license_evidence_refs)?;ordered_refs(&self.build_provenance_refs)?;Ok(())
    }
    /// Standard library primitive, no algorithm fallback or self-provided key.
    /// A caller can verify a candidate before admission; this returns no permit.
    pub(crate) fn verify_signature(&self,key:&[u8;32])->Result<(),&'static str>{
        let key=VerifyingKey::from_bytes(key).map_err(|_|"qualification_anchor_invalid")?;
        let signature=Signature::from_bytes(&decode_hex::<64>(&self.signature)?);
        let mut unsigned=serde_json::to_value(self).map_err(|_|"qualification_record_invalid")?;
        unsigned.as_object_mut().ok_or("qualification_record_invalid")?.remove("signature");
        key.verify_strict(&canonical(&unsigned)?,&signature).map_err(|_|"qualification_signature_invalid")
    }
    pub(crate) fn as_value(&self)->Result<serde_json::Value,&'static str>{serde_json::to_value(self).map_err(|_|"qualification_record_invalid")}
    pub(crate) fn reference(&self)->Result<QualificationRef,&'static str>{Ok(QualificationRef{document_id:self.record_id.clone(),revision:self.revision,sha256:digest(&canonical(&self.as_value()?)?)})}
    pub(crate) fn assert_time(&self,checked_at_us:u64)->Result<(),&'static str>{
        if checked_at_us==0||checked_at_us>I64_MAX||checked_at_us<self.valid_from_us||checked_at_us>=self.expires_at_us{return Err("qualification_record_expired");}Ok(())
    }
}
