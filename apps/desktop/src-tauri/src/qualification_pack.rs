//! Original protected candidate file and complete material closure. This
//! verification object is not a trust admission/current Registry or permit.
use std::{fs::{File,OpenOptions},io::Read,sync::Arc};
use crate::{installation_trust::TrustMaterials,native_installation::{canonical,NativeInstallationGuards},
    qualification_record::{digest,QualificationRecord,RECORD_LIMIT},resource_pins::{PinnedFile,ResourcePins}};
pub(crate) const RECORD_FILE:&str="InstallationQualificationRecord.json";
#[cfg(target_arch="x86_64")]
fn current_cpu_feature(feature:&str)->bool{match feature{
    "x86_sse2"=>std::arch::is_x86_feature_detected!("sse2"),
    "x86_avx"=>std::arch::is_x86_feature_detected!("avx"),
    "x86_avx2"=>std::arch::is_x86_feature_detected!("avx2"),_=>false,
}}
#[cfg(not(target_arch="x86_64"))]
fn current_cpu_feature(_: &str)->bool{false}
pub(crate) struct VerifiedQualificationCandidate {
    pub(crate) record:QualificationRecord,pub(crate) installation:Arc<NativeInstallationGuards>,
    pub(crate) materials:Arc<TrustMaterials>,pins:ResourcePins,_selected:File,raw_sha256:String,
}
impl VerifiedQualificationCandidate {
    /// The producer layout selects only this record under its original held
    /// Composition/Control. Its signature is checked against the actual held
    /// raw key as a candidate; later committed-source admission is mandatory.
    pub(crate) fn hold(installation:Arc<NativeInstallationGuards>,materials:Arc<TrustMaterials>,resources:&crate::engine::LaunchResources)->Result<Arc<Self>,&'static str>{
        if !Arc::ptr_eq(&installation.payload,&resources.pins){return Err("qualification_installation_owner_mismatch");}
        installation.image_is_current_process()?;materials.assert_current()?;
        use std::os::windows::fs::OpenOptionsExt;
        let selected=OpenOptions::new().read(true).share_mode(1).custom_flags(0x0020_0000).open(installation.control_root()?.join(RECORD_FILE)).map_err(|_|"qualification_record_unavailable")?;
        if !selected.metadata().map_err(|_|"qualification_record_unavailable")?.is_file(){return Err("qualification_record_invalid");}
        let mut raw=Vec::new();(&selected).take(RECORD_LIMIT as u64+1).read_to_end(&mut raw).map_err(|_|"qualification_record_unavailable")?;
        let record=QualificationRecord::parse(&raw)?;record.verify_signature(&materials.key()?)?;
        if record.issuer_id!=materials.issuer()||record.trust_mode!=materials.mode(){return Err("qualification_anchor_mismatch");}
        let input=&installation.inputs;
        if (&record.registration_sha256,&record.resource_manifest_sha256,&record.runtime_manifest_sha256,record.host_build_receipt_sha256.as_str())
            !=(&input.registration_sha256,&input.resource_manifest_sha256,&input.runtime_manifest_sha256,installation.receipt_sha256())
            ||record.full_file_map_sha256!=installation.full_file_map_sha256()?||record.engine_partition_sha256!=installation.engine_partition_sha256()?{return Err("qualification_installation_identity_mismatch");}
        resources.assert_qualification_profiles(&record)?;
        Self::assert_material_refs(&record,&materials)?;
        let raw_sha256=digest(&raw);
        let pins=ResourcePins::hold(installation.control_root()?,&[PinnedFile{relative_path:RECORD_FILE.into(),bytes:raw.len()as u64,sha256:raw_sha256.clone()}])?;
        if pins.read_held_bytes(RECORD_FILE,RECORD_LIMIT)?!=raw{return Err("qualification_record_changed");}
        let value=Arc::new(Self{record,installation,materials,pins,_selected:selected,raw_sha256});value.assert_current()?;Ok(value)
    }
    fn assert_material_refs(record:&QualificationRecord,materials:&TrustMaterials)->Result<(),&'static str>{
        materials.require_ref(&record.qualification_suite_ref,"qualification_suite")?;
        materials.require_ref(&record.independent_review_ref,"independent_review")?;
        materials.require_ref(&record.independent_acceptance_ref,"independent_acceptance")?;
        for reference in &record.runtime_report_refs{materials.require_ref(reference,"qualification_report")?;}
        for condition in &record.target.conditions{materials.require_ref(condition.report(),"qualification_report")?;
            if !record.runtime_report_refs.contains(condition.report()){return Err("qualification_condition_report_unbound");}}
        for profile in &record.profiles{for reference in &profile.report_refs{materials.require_ref(reference,"qualification_report")?;
            if !record.runtime_report_refs.contains(reference){return Err("qualification_profile_report_unbound");}}}
        for reference in &record.license_evidence_refs{materials.require_ref(reference,"license_evidence")?;}
        for reference in &record.build_provenance_refs{materials.require_ref(reference,"build_provenance")?;}Ok(())
    }
    pub(crate) fn assert_current(&self)->Result<(),&'static str>{
        let observed=self.installation.observe()?;self.installation.assert_current(&observed)?;
        self.materials.assert_current()?;let observed=self.pins.observe_all()?;self.pins.assert_current(&observed)?;
        if self.pins.read_held_bytes(RECORD_FILE,RECORD_LIMIT)?!=canonical(&self.record.as_value()?)?{return Err("qualification_record_changed");}
        Self::assert_material_refs(&self.record,&self.materials)
    }
    pub(crate) fn sha256(&self)->&str{&self.raw_sha256}
    /// The original native collector, not a signed JSON report, establishes the
    /// current target. Its retained files and source are rechecked on every
    /// Registry read. The indexed policy already binds the actual CPython
    /// artifact/version/GIL and all four complete profile maps.
    pub(crate) fn assert_target_current(&self,source:&crate::windows_native_sources::VerifiedSystemContext)->Result<(),&'static str>{
        use crate::qualification_record::Condition;
        let profile=self.record.profiles.first().ok_or("qualification_profile_unlisted")?;
        source.assert_qualification_identity(&profile.artifact_version,&profile.load_policy_sha256)?;
        let facts=source.observations();
        if self.record.target.os!="windows"||self.record.target.arch!="x86_64"||facts.architecture!="amd64"
            ||!facts.errors.is_empty(){return Err("qualification_current_target_unverified");}
        for condition in &self.record.target.conditions{match condition{
            Condition::OsFloor{product,version,..}=>if product!="windows_nt"||facts.os_version<*version{return Err("qualification_current_os_below_floor");},
            Condition::PythonAbi{implementation,version,abi_tag,gil,..}=>if implementation!="cpython"||*version!=[3,13,16]||abi_tag!="cp313"||gil!="standard"{return Err("qualification_current_python_unverified");},
            Condition::CpuFeatures{features,..}=>for feature in features{
                if !current_cpu_feature(feature){return Err("qualification_current_cpu_unverified");}
            },
            Condition::WindowsCrt{components,..}=>for component in components{
                let mut original=None;
                for file in facts.files.values().filter(|file|std::path::Path::new(&file.path).file_name().and_then(|name|name.to_str()).is_some_and(|name|name.eq_ignore_ascii_case(&component.name))){
                    let version=file.file_version.ok_or("qualification_current_crt_unverified")?.map(u32::from);
                    if file.machine!=0x8664||file.signature.wintrust_status!=0||file.signature.publisher_organization.as_deref()!=Some("Microsoft Corporation")
                        ||file.signature.signer_certificate_sha256.is_none()||version<component.floor{return Err("qualification_current_crt_unverified");}
                    let identity=(file.volume_serial,file.file_index,file.modified_filetime,file.bytes,file.sha256.as_str(),version);
                    if original.is_some_and(|known|known!=identity){return Err("qualification_current_crt_ambiguous");}original=Some(identity);
                }
                if original.is_none(){return Err("qualification_current_crt_unavailable");}
            },
            Condition::Libc{..}=>return Err("qualification_current_target_unverified"),
        }}Ok(())
    }
}
