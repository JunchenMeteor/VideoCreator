//! Trusted, pre-Python Windows source observations. Not a renderer DTO.
//! Signature/source observations do not certify general MinOS or redistribution.
use std::{collections::BTreeMap,fs::{self,File,OpenOptions},io::{Read,Seek,SeekFrom,Write},path::{Path,PathBuf},sync::{Arc,Mutex}};
use serde::Serialize;
use serde_json::{Value,json};
use sha2::{Digest,Sha256};

#[derive(Clone,Serialize)]
pub(crate) struct FileObservation {
    pub path:String,pub bytes:u64,pub sha256:String,pub machine:u16,
    pub volume_serial:u32,pub file_index:u64,pub modified_filetime:u64,
    pub file_version:Option<[u16;4]>,
    pub static_imports:Vec<String>,pub delay_imports:Vec<String>,
    pub signature:SignatureObservation,
}
#[derive(Clone,Serialize)]
pub(crate) struct SignatureObservation {
    pub method:String,pub wintrust_status:i32,pub publisher_organization:Option<String>,
    pub signer_certificate_sha256:Option<String>,pub catalog:Option<String>,
    pub catalog_sha256:Option<String>,pub catalog_bytes:Option<u64>,
    pub online_revocation:String,
}
#[derive(Serialize)]
pub(crate) struct SourceObservations {
    pub format:String,pub windows_directory:String,pub system_directory:String,
    pub os_version:[u32;3],pub architecture:String,pub files:BTreeMap<String,FileObservation>,
    pub errors:BTreeMap<String,String>,pub api_set_mappings:BTreeMap<String,Vec<String>>,
    pub supported_minimum_os_build:String,pub redistribution:String,
}
// No Deserialize or constructor from observed JSON. Only collect() below can
// produce the in-memory source guard consumed by PreparedLaunch.
pub(crate) trait CatalogReadPort: Read {
    fn length(&self)->std::io::Result<u64>;
}
impl CatalogReadPort for File {
    fn length(&self)->std::io::Result<u64>{self.metadata().map(|value|value.len())}
}
pub(crate) struct CatalogReadBudget {reserved:u64,rejected:u64,failed_reads:u64}
impl CatalogReadBudget {
    const CAP:u64=128*1024*1024;
    fn new()->Self{Self{reserved:0,rejected:0,failed_reads:0}}
    fn reserve(&mut self,bytes:u64)->Result<(),&'static str>{
        if bytes>Self::CAP||bytes>Self::CAP.saturating_sub(self.reserved){self.rejected=self.rejected.saturating_add(1);return Err("native_source_catalog_budget_exceeded");}
        // Reservation is conservative and never refunded after short/error
        // reads, later signature rejection or identity failure.
        self.reserved+=bytes;Ok(())
    }
    pub(crate) fn read_catalog(&mut self,file:&mut File)->Result<Vec<u8>,&'static str>{self.read_port(file)}
    pub(crate) fn read_port(&mut self,file:&mut impl CatalogReadPort)->Result<Vec<u8>,&'static str>{
        let size=file.length().map_err(|_|"native_source_catalog_info_failed")?;
        self.reserve(size)?;
        let mut body=Vec::new();
        let result=(&mut *file).take(size).read_to_end(&mut body);
        if result.is_err()||body.len()as u64!=size||file.length().map(|length|length!=size).unwrap_or(true){
            self.failed_reads=self.failed_reads.saturating_add(1);return Err("native_source_catalog_read_failed");
        }Ok(body)
    }
}
// Both the native signature consumer and cfg(test) fixture signatures use this
// reservation/read/verification order. Verification never owns another budget.
pub(crate) fn verify_catalog_candidate(budget:&mut CatalogReadBudget,mut file:File,verify:impl FnOnce()->SignatureObservation)->Result<(SignatureObservation,Option<File>),&'static str>{
    let body=budget.read_catalog(&mut file)?;
    let mut result=verify();
    result.catalog_sha256=Some(format!("{:x}",Sha256::digest(&body)));
    result.catalog_bytes=Some(body.len()as u64);
    Ok((result,Some(file)))
}
pub(crate) struct VerifiedSystemContext {
    observations:SourceObservations,_held:Vec<File>,profile:String,artifact:String,policy_sha:String,
    host_pid:u32,host_creation:u64,
    catalog_budget:Mutex<CatalogReadBudget>,catalog_members:Vec<(PathBuf,u64,String,(u32,u64,u64))>,
    source:Arc<dyn SourcePort>,
}
pub(crate) struct LaunchSourceCarrier {pub path:PathBuf,pub sha256:String,pub context:Arc<VerifiedSystemContext>,_held:File,bound:bool}
impl LaunchSourceCarrier {
    pub fn bind_before_resume(&mut self,pid:u32,creation:u64,stdin:&mut impl Write)->Result<(),&'static str>{
        if self.bound{return Err("native_source_carrier_already_bound");}
        self.context.recheck()?;
        let value=json!({"host_pid":self.context.host_pid,"host_creation_filetime":self.context.host_creation,
            "child_pid":pid,"child_creation_filetime":creation,"profile":self.context.profile,"artifact_version":self.context.artifact,
            "policy_sha256":self.context.policy_sha,"context_sha256":self.sha256});
        let mut frame=b"NATIVE_SOURCE_BIND ".to_vec();frame.extend(serde_json::to_vec(&value).map_err(|_|"native_source_binding_invalid")?);frame.push(b'\n');
        if frame.len()>1024||!frame.is_ascii(){return Err("native_source_binding_oversize_or_nonascii");}
        // Fits within the owned anonymous pipe's minimum Win32 buffer; no child
        // reader is required before Resume. Actual timeout/failure still needs
        // a native lifecycle batch; this source is not that evidence.
        stdin.write_all(&frame).and_then(|_|stdin.flush()).map_err(|_|"native_source_binding_write_failed")?;
        self.bound=true;Ok(())
    }
}

// Crate-private trusted dispatch. Production only constructs WindowsSources;
// cfg(test) consumers can implement a fixture port, never a renderer DTO.
mod source_sealed {pub trait Source{}}
#[cfg(test)] impl<T> source_sealed::Source for T{}
#[cfg(all(windows,not(test)))] impl source_sealed::Source for WindowsSources{}
pub(crate) trait SourcePort:source_sealed::Source+Send+Sync {
    fn roots(&self)->Result<(PathBuf,PathBuf,[u32;3]),&'static str>;
    fn host_identity(&self)->Result<(u32,u64),&'static str>;
    fn open(&self,path:&Path)->Result<File,&'static str>;
    fn identity(&self,file:&File)->Result<(u32,u64,u64),&'static str>;
    fn signature(&self,path:&Path,file:&File,system:&Path,budget:&mut CatalogReadBudget)->Result<(SignatureObservation,Option<File>),&'static str>;
    fn loaded_origin(&self,name:&str,path:&Path)->Result<(),&'static str>;
    fn file_version(&self,path:&Path)->Result<[u16;4],&'static str>;
}
#[cfg(windows)] struct WindowsSources;
#[cfg(windows)] impl SourcePort for WindowsSources {
    fn roots(&self)->Result<(PathBuf,PathBuf,[u32;3]),&'static str>{windows::roots()}
    fn host_identity(&self)->Result<(u32,u64),&'static str>{Ok((std::process::id(),windows::creation()?))}
    fn open(&self,path:&Path)->Result<File,&'static str>{open_held(path)}
    fn identity(&self,file:&File)->Result<(u32,u64,u64),&'static str>{windows::identity(file)}
    fn signature(&self,path:&Path,file:&File,system:&Path,budget:&mut CatalogReadBudget)->Result<(SignatureObservation,Option<File>),&'static str>{windows::signature(path,file,system,budget)}
    fn loaded_origin(&self,name:&str,path:&Path)->Result<(),&'static str>{windows::loaded_carrier_origin(name,path)}
    fn file_version(&self,path:&Path)->Result<[u16;4],&'static str>{windows::file_version(path)}
}

fn local_text(path:&Path)->Result<String,&'static str>{
    let text=path.to_str().ok_or("native_source_path_invalid")?;
    if let Some(value)=text.strip_prefix("\\\\?\\"){
        let b=value.as_bytes();if b.len()<3||!b[0].is_ascii_alphabetic()||b[1]!=b':'||b[2]!=b'\\'{return Err("native_source_path_invalid");}return Ok(value.to_owned());
    }
    if text.starts_with("\\\\")||text.starts_with("//"){return Err("native_source_path_invalid");}Ok(text.to_owned())
}
fn check_physical(path:&Path)->Result<(),&'static str>{
    let mut next=Some(path);
    while let Some(value)=next{
        let metadata=fs::symlink_metadata(value).map_err(|_|"native_source_missing")?;
        #[cfg(windows)] {use std::os::windows::fs::MetadataExt;if metadata.file_attributes()&1024!=0{return Err("native_source_reparse");}}
        if metadata.file_type().is_symlink(){return Err("native_source_reparse");}next=value.parent();
    }Ok(())
}
fn open_held(path:&Path)->Result<File,&'static str>{
    check_physical(path)?;
    let mut options=OpenOptions::new();options.read(true);
    #[cfg(windows)] {use std::os::windows::fs::OpenOptionsExt;options.share_mode(1);}
    options.open(path).map_err(|_|"native_source_hold_failed")
}
fn pe_machine(body:&[u8])->Result<u16,&'static str>{
    if body.len()<64||&body[..2]!=b"MZ"{return Err("native_source_pe_invalid");}
    let offset=u32::from_le_bytes(body[60..64].try_into().unwrap())as usize;
    let bytes=body.get(offset..offset+6).ok_or("native_source_pe_invalid")?;
    if &bytes[..4]!=b"PE\0\0"{return Err("native_source_pe_invalid");}Ok(u16::from_le_bytes(bytes[4..6].try_into().unwrap()))
}
fn pe_imports(body:&[u8])->Result<(Vec<String>,Vec<String>),&'static str>{
    pe_machine(body)?;let pe=u32_at(body,60)?as usize;
    let count=u16::from_le_bytes(body.get(pe+6..pe+8).ok_or("native_source_pe_invalid")?.try_into().unwrap())as usize;
    let optional=u16::from_le_bytes(body.get(pe+20..pe+22).ok_or("native_source_pe_invalid")?.try_into().unwrap())as usize;
    if count>128||optional<112{return Err("native_source_pe_invalid");}let header=pe+24;
    if body.get(header..header+2)!=Some(&[0x0b,0x02]){return Err("native_source_pe_abi_invalid");}
    let image_base=u64::from_le_bytes(body.get(header+24..header+32).ok_or("native_source_pe_invalid")?.try_into().unwrap());
    let directories=u32_at(body,header+108)?as usize;
    let address=|rva:u32|->Result<usize,&'static str>{
        for index in 0..count{let section=header+optional+40*index;let va=u32_at(body,section+12)?;let raw_size=u32_at(body,section+16)?;let raw=u32_at(body,section+20)?;
            if rva>=va&&rva-va<raw_size{let at=(raw as usize).checked_add((rva-va)as usize).ok_or("native_source_pe_invalid")?;if at>=body.len(){return Err("native_source_pe_invalid");}return Ok(at);}}
        Err("native_source_pe_rva_unmapped")
    };
    let name=|rva:u32|->Result<String,&'static str>{let at=address(rva)?;let tail=&body[at..body.len().min(at+32768)];let length=tail.iter().position(|byte|*byte==0).ok_or("native_source_pe_name_invalid")?;let name=std::str::from_utf8(&tail[..length]).map_err(|_|"native_source_pe_name_invalid")?.to_lowercase();if name.is_empty()||!name.is_ascii()||name.contains(['/', '\\', ':']){return Err("native_source_pe_name_invalid");}Ok(name)};
    let table=|index:usize,width:usize,field:usize,delay:bool|->Result<Vec<String>,&'static str>{
        if directories<=index{return Ok(Vec::new());}let offset=header+112+8*index;
        if offset+8>header+optional{return Err("native_source_pe_invalid");}let rva=u32_at(body,offset)?;let size=u32_at(body,offset+4)?as usize;
        if rva==0{return Ok(Vec::new());}if size<width||size>4*1024*1024{return Err("native_source_pe_table_invalid");}let start=address(rva)?;
        let mut imports=Vec::new();let mut ended=false;
        for at in (start..start.checked_add(size).ok_or("native_source_pe_invalid")?).step_by(width){let row=body.get(at..at+width).ok_or("native_source_pe_invalid")?;
            if row.iter().all(|byte|*byte==0){ended=true;break;}let value=u32_at(row,field)?;
            let rva=if delay&&u32_at(row,0)?&1==0{u32::try_from((value as u64).checked_sub(image_base).ok_or("native_source_pe_delay_invalid")?).map_err(|_|"native_source_pe_delay_invalid")?}else{value};
            imports.push(name(rva)?);}
        if !ended{return Err("native_source_pe_table_unterminated");}imports.sort();imports.dedup();Ok(imports)
    };
    Ok((table(1,20,12,false)?,table(13,32,4,true)?))
}

#[cfg(windows)]
mod windows {
    use super::*;
    use std::{ffi::OsString,mem::{size_of,zeroed},os::windows::{ffi::{OsStrExt,OsStringExt},io::AsRawHandle},ptr::{null,null_mut}};
    use windows_sys::Win32::{Foundation::{FILETIME,HANDLE},Storage::FileSystem::{GetFileInformationByHandle,BY_HANDLE_FILE_INFORMATION,GetFileVersionInfoSizeW,GetFileVersionInfoW,VerQueryValueW,VS_FIXEDFILEINFO},
        System::{SystemInformation::{GetSystemDirectoryW,GetWindowsDirectoryW},LibraryLoader::{GetModuleHandleW,GetProcAddress},Threading::{GetCurrentProcess,GetProcessTimes}},
        Security::{Cryptography::{CertGetNameStringW,CERT_NAME_ATTR_TYPE,CERT_CONTEXT,Catalog::*},WinTrust::*}};
    fn wide(path:&Path)->Result<Vec<u16>,&'static str>{let mut text=path.as_os_str().encode_wide().collect::<Vec<_>>();if text.contains(&0){return Err("native_source_path_invalid");}text.push(0);Ok(text)}
    fn wide_string(text:&str)->Vec<u16>{text.encode_utf16().chain(Some(0)).collect()}
    fn filetime(time:FILETIME)->u64{((time.dwHighDateTime as u64)<<32)|time.dwLowDateTime as u64}
    pub fn creation()->Result<u64,&'static str>{
        let(mut born,mut end,mut kernel,mut user):(FILETIME,FILETIME,FILETIME,FILETIME)=unsafe{zeroed()};
        if unsafe{GetProcessTimes(GetCurrentProcess(),&mut born,&mut end,&mut kernel,&mut user)}==0{return Err("native_source_host_identity_failed");}Ok(filetime(born))
    }
    pub fn identity(file:&File)->Result<(u32,u64,u64),&'static str>{
        let mut info:BY_HANDLE_FILE_INFORMATION=unsafe{zeroed()};
        if unsafe{GetFileInformationByHandle(file.as_raw_handle() as HANDLE,&mut info)}==0{return Err("native_source_file_identity_failed");}
        Ok((info.dwVolumeSerialNumber,((info.nFileIndexHigh as u64)<<32)|info.nFileIndexLow as u64,filetime(info.ftLastWriteTime)))
    }
    pub fn loaded_carrier_origin(name:&str,expected:&Path)->Result<(),&'static str>{
        use windows_sys::Win32::System::LibraryLoader::GetModuleFileNameW;
        let module=unsafe{GetModuleHandleW(wide_string(name).as_ptr())};if module.is_null(){return Err("native_metadata_carrier_not_loaded");}
        let mut value=vec![0u16;32768];let length=unsafe{GetModuleFileNameW(module,value.as_mut_ptr(),value.len()as u32)}as usize;
        if length==0||length>=value.len(){return Err("native_metadata_carrier_origin_unavailable");}
        let actual=PathBuf::from(OsString::from_wide(&value[..length]));check_physical(&actual)?;
        if actual.canonicalize().map_err(|_|"native_metadata_carrier_origin_unavailable")?!=expected.canonicalize().map_err(|_|"native_metadata_carrier_origin_unavailable")?{return Err("native_metadata_carrier_origin_mismatch");}Ok(())
    }
    #[repr(C)] struct VersionInfo{size:u32,major:u32,minor:u32,build:u32,platform:u32,service:[u16;128]}
    pub fn roots()->Result<(PathBuf,PathBuf,[u32;3]),&'static str>{
        let mut win=vec![0u16;32768];let mut sys=vec![0u16;32768];
        let wc=unsafe{GetWindowsDirectoryW(win.as_mut_ptr(),win.len()as u32)}as usize;
        let sc=unsafe{GetSystemDirectoryW(sys.as_mut_ptr(),sys.len()as u32)}as usize;
        if wc==0||sc==0||wc>=win.len()||sc>=sys.len(){return Err("native_source_os_root_unavailable");}
        let win=PathBuf::from(OsString::from_wide(&win[..wc])).canonicalize().map_err(|_|"native_source_os_root_unavailable")?;
        let sys=PathBuf::from(OsString::from_wide(&sys[..sc])).canonicalize().map_err(|_|"native_source_os_root_unavailable")?;
        check_physical(&win)?;check_physical(&sys)?;
        if sys.parent()!=Some(win.as_path())||sys.file_name().is_none_or(|name|name.to_string_lossy().to_lowercase()!="system32"){return Err("native_source_os_root_invalid");}
        let module=unsafe{GetModuleHandleW(wide_string("ntdll.dll").as_ptr())};if module.is_null(){return Err("native_source_os_version_unavailable");}
        let function=unsafe{GetProcAddress(module,c"RtlGetVersion".as_ptr() as _)}.ok_or("native_source_os_version_unavailable")?;
        let function:unsafe extern "system" fn(*mut VersionInfo)->i32=unsafe{std::mem::transmute(function)};
        let mut version:VersionInfo=unsafe{zeroed()};version.size=size_of::<VersionInfo>()as u32;
        if unsafe{function(&mut version)}!=0{return Err("native_source_os_version_unavailable");}
        Ok((win,sys,[version.major,version.minor,version.build]))
    }
    fn organization(context:*const CERT_CONTEXT)->Option<String>{
        if context.is_null(){return None;}
        let mut text=vec![0u16;1024];
        let length=unsafe{CertGetNameStringW(context,CERT_NAME_ATTR_TYPE,0,c"2.5.4.10".as_ptr()as _,text.as_mut_ptr(),text.len()as u32)}as usize;
        if length<=1||length>text.len(){None}else{Some(String::from_utf16_lossy(&text[..length-1]))}
    }
    fn signer(data:&WINTRUST_DATA)->(Option<String>,Option<String>){
        let provider=unsafe{WTHelperProvDataFromStateData(data.hWVTStateData)};if provider.is_null(){return(None,None);}
        let signer=unsafe{WTHelperGetProvSignerFromChain(provider,0,0,0)};if signer.is_null(){return(None,None);}
        let cert=unsafe{WTHelperGetProvCertFromChain(signer,0)};if cert.is_null(){return(None,None);}
        let context=unsafe{(*cert).pCert};if context.is_null(){return(None,None);}
        let bytes=unsafe{std::slice::from_raw_parts((*context).pbCertEncoded,(*context).cbCertEncoded as usize)};
        (organization(context),Some(format!("{:x}",Sha256::digest(bytes))))
    }
    fn verify(data:&mut WINTRUST_DATA,method:&str,catalog:Option<String>)->SignatureObservation{
        data.cbStruct=size_of::<WINTRUST_DATA>()as u32;data.dwUIChoice=WTD_UI_NONE;
        data.fdwRevocationChecks=WTD_REVOKE_NONE;data.dwProvFlags=WTD_CACHE_ONLY_URL_RETRIEVAL|WTD_REVOCATION_CHECK_NONE;
        data.dwStateAction=WTD_STATEACTION_VERIFY;
        let mut action=WINTRUST_ACTION_GENERIC_VERIFY_V2;
        let status=unsafe{WinVerifyTrust(null_mut(),&mut action,data as *mut _ as _)};
        let(org,cert)=if status==0{signer(data)}else{(None,None)};
        data.dwStateAction=WTD_STATEACTION_CLOSE;unsafe{WinVerifyTrust(null_mut(),&mut action,data as *mut _ as _);}
        SignatureObservation{method:method.to_owned(),wintrust_status:status,publisher_organization:org,signer_certificate_sha256:cert,catalog,catalog_sha256:None,catalog_bytes:None,online_revocation:"not_checked_cache_only".into()}
    }
    struct Admin(isize);impl Drop for Admin{fn drop(&mut self){unsafe{CryptCATAdminReleaseContext(self.0,0);}}}
    pub fn signature(path:&Path,file:&File,system:&Path,budget:&mut CatalogReadBudget)->Result<(SignatureObservation,Option<File>),&'static str>{
        let path_text=wide(path)?;let mut info=WINTRUST_FILE_INFO{cbStruct:size_of::<WINTRUST_FILE_INFO>()as u32,pcwszFilePath:path_text.as_ptr(),hFile:file.as_raw_handle()as _,pgKnownSubject:null_mut()};
        let mut data:WINTRUST_DATA=unsafe{zeroed()};data.dwUnionChoice=WTD_CHOICE_FILE;data.Anonymous.pFile=&mut info;
        let embedded=verify(&mut data,"WinVerifyTrust:file",None);
        if embedded.wintrust_status==0{return Ok((embedded,None));}
        let mut admin=0;let algorithm=wide_string("SHA256");
        if unsafe{CryptCATAdminAcquireContext2(&mut admin,&DRIVER_ACTION_VERIFY,algorithm.as_ptr(),null(),0)}==0{return Ok((embedded,None));}let admin=Admin(admin);
        let mut count=0;
        if unsafe{CryptCATAdminCalcHashFromFileHandle2(admin.0,file.as_raw_handle()as _,&mut count,null_mut(),0)}==0||count==0||count>128{return Ok((embedded,None));}
        let mut hash=vec![0u8;count as usize];
        if unsafe{CryptCATAdminCalcHashFromFileHandle2(admin.0,file.as_raw_handle()as _,&mut count,hash.as_mut_ptr(),0)}==0{return Ok((embedded,None));}
        let tag=wide_string(&hash.iter().map(|byte|format!("{byte:02X}")).collect::<String>());
        // One bounded candidate. Do not reuse a released HCATINFO as the
        // enumeration cursor; unresolved additional catalogs remain explicit.
        let mut previous=0;let catroot=system.join("CatRoot").join("{F750E6C3-38EE-11D1-85E5-00C04FC295EE}").canonicalize().map_err(|_|"native_source_catalog_root_unavailable")?;
        let handle=unsafe{CryptCATAdminEnumCatalogFromHash(admin.0,hash.as_ptr(),count,0,&mut previous)};
        if handle==0{return Ok((embedded,None));}
        struct CatalogGuard(isize,isize);impl Drop for CatalogGuard{fn drop(&mut self){unsafe{CryptCATAdminReleaseCatalogContext(self.0,self.1,0);}}}
        let _context=CatalogGuard(admin.0,handle);
            let mut catalog:CATALOG_INFO=unsafe{zeroed()};catalog.cbStruct=size_of::<CATALOG_INFO>()as u32;
            if unsafe{CryptCATCatalogInfoFromContext(handle,&mut catalog,0)}==0{return Err("native_source_catalog_info_failed");}
            let end=catalog.wszCatalogFile.iter().position(|value|*value==0).ok_or("native_source_catalog_path_invalid")?;
            let name=PathBuf::from(OsString::from_wide(&catalog.wszCatalogFile[..end]));check_physical(&name)?;
            let physical=name.canonicalize().map_err(|_|"native_source_catalog_path_invalid")?;
            if physical.parent()!=Some(catroot.as_path())||physical.extension().is_none_or(|value|value.to_string_lossy().to_lowercase()!="cat"){return Err("native_source_catalog_path_invalid");}
            let catalog_guard=open_held(&physical)?;
            let catalog_text=wide(&physical)?;
            let mut catalog_info:WINTRUST_CATALOG_INFO=unsafe{zeroed()};catalog_info.cbStruct=size_of::<WINTRUST_CATALOG_INFO>()as u32;
            catalog_info.pcwszCatalogFilePath=catalog_text.as_ptr();catalog_info.pcwszMemberTag=tag.as_ptr();catalog_info.pcwszMemberFilePath=path_text.as_ptr();
            catalog_info.hMemberFile=file.as_raw_handle()as _;catalog_info.pbCalculatedFileHash=hash.as_mut_ptr();catalog_info.cbCalculatedFileHash=count;catalog_info.hCatAdmin=admin.0;
            let mut data:WINTRUST_DATA=unsafe{zeroed()};data.dwUnionChoice=WTD_CHOICE_CATALOG;data.Anonymous.pCatalog=&mut catalog_info;
            let catalog_name=local_text(&physical)?;
            verify_catalog_candidate(budget,catalog_guard,||verify(&mut data,"CryptCATAdmin+WinVerifyTrust:catalog",Some(catalog_name)))
    }
    pub fn file_version(path:&Path)->Result<[u16;4],&'static str>{
        let text=wide(path)?;let mut ignored=0;let size=unsafe{GetFileVersionInfoSizeW(text.as_ptr(),&mut ignored)};
        if size==0||size>16*1024*1024{return Err("native_vc_version_unavailable");}
        let mut bytes=vec![0u8;size as usize];
        if unsafe{GetFileVersionInfoW(text.as_ptr(),0,size,bytes.as_mut_ptr()as _)}==0{return Err("native_vc_version_unavailable");}
        let mut value=null_mut();let mut length=0;
        if unsafe{VerQueryValueW(bytes.as_ptr()as _,wide_string("\\").as_ptr(),&mut value,&mut length)}==0||length<size_of::<VS_FIXEDFILEINFO>()as u32||value.is_null(){return Err("native_vc_version_unavailable");}
        let info=unsafe{std::ptr::read_unaligned(value as *const VS_FIXEDFILEINFO)};
        if info.dwSignature!=0xfeef04bd{return Err("native_vc_version_unavailable");}
        Ok([(info.dwFileVersionMS>>16)as u16,info.dwFileVersionMS as u16,(info.dwFileVersionLS>>16)as u16,info.dwFileVersionLS as u16])
    }
}

fn u32_at(data:&[u8],offset:usize)->Result<u32,&'static str>{Ok(u32::from_le_bytes(data.get(offset..offset+4).ok_or("native_api_set_schema_invalid")?.try_into().unwrap()))}
fn text_at(data:&[u8],offset:u32,length:u32)->Result<String,&'static str>{
    if length%2!=0||length>65536{return Err("native_api_set_schema_invalid");}
    let bytes=data.get(offset as usize..offset as usize+length as usize).ok_or("native_api_set_schema_invalid")?;
    String::from_utf16(&bytes.chunks_exact(2).map(|part|u16::from_le_bytes([part[0],part[1]])).collect::<Vec<_>>()).map(|s|s.to_lowercase()).map_err(|_|"native_api_set_schema_invalid")
}
fn api_set_table(body:&[u8])->Result<BTreeMap<String,Vec<String>>,&'static str>{
    pe_machine(body)?;let pe=u32_at(body,60)?as usize;let sections=u16::from_le_bytes(body.get(pe+6..pe+8).ok_or("native_api_set_schema_invalid")?.try_into().unwrap())as usize;
    let optional=u16::from_le_bytes(body.get(pe+20..pe+22).ok_or("native_api_set_schema_invalid")?.try_into().unwrap())as usize;
    let mut blob=None;
    for index in 0..sections.min(128){let at=pe+24+optional+40*index;let row=body.get(at..at+40).ok_or("native_api_set_schema_invalid")?;
        if row[..8].starts_with(b".apiset"){let size=u32_at(row,16)?as usize;let offset=u32_at(row,20)?as usize;blob=Some(body.get(offset..offset+size).ok_or("native_api_set_schema_invalid")?);}}
    let data=blob.ok_or("native_api_set_schema_missing")?;
    if u32_at(data,0)?!=6{return Err("native_api_set_schema_version_unverified");}
    let size=u32_at(data,4)?as usize;if size>data.len(){return Err("native_api_set_schema_invalid");}let data=&data[..size];
    let count=u32_at(data,12)?as usize;let start=u32_at(data,16)?as usize;if count>16384{return Err("native_api_set_schema_invalid");}
    let mut out=BTreeMap::new();
    for index in 0..count{let at=start+24*index;let name=text_at(data,u32_at(data,at+4)?,u32_at(data,at+8)?)?;let values=u32_at(data,at+16)?as usize;let count=u32_at(data,at+20)?as usize;
        if count>64{return Err("native_api_set_schema_invalid");}let mut targets=Vec::new();
        for index in 0..count{let at=values+20*index;let alias_length=u32_at(data,at+8)?;
            if alias_length!=0{continue;} // importer-specific alternatives require a separately explicit mapping; no guessed selection.
            let target=text_at(data,u32_at(data,at+12)?,u32_at(data,at+16)?)?;
            if !target.is_empty(){if target.contains(['/', '\\', ':']){return Err("native_api_set_schema_invalid");}targets.push(target);}}
        targets.sort();targets.dedup();if out.insert(name,targets).is_some(){return Err("native_api_set_schema_duplicate");}
    }Ok(out)
}

#[cfg(windows)]
impl VerifiedSystemContext {
    pub(crate) fn collect(contracts:&BTreeMap<String,Value>,ids:&[String],profile:&str,artifact:&str,policy_sha:&str)->Result<Arc<Self>,&'static str>{
        Self::collect_from(contracts,ids,profile,artifact,policy_sha,Arc::new(WindowsSources))
    }
    #[cfg(test)]
    pub(crate) fn collect_for_test(contracts:&BTreeMap<String,Value>,ids:&[String],profile:&str,artifact:&str,policy_sha:&str,source:Arc<dyn SourcePort>)->Result<Arc<Self>,&'static str>{
        Self::collect_from(contracts,ids,profile,artifact,policy_sha,source)
    }
    fn collect_from(contracts:&BTreeMap<String,Value>,ids:&[String],profile:&str,artifact:&str,policy_sha:&str,source:Arc<dyn SourcePort>)->Result<Arc<Self>,&'static str>{
        let(windows,system,version)=source.roots()?;
        let(host_pid,host_creation)=source.host_identity()?;
        let mut context=Self{observations:SourceObservations{format:"windows-native-source-observations-v1".into(),windows_directory:local_text(&windows)?,system_directory:local_text(&system)?,os_version:version,architecture:"amd64".into(),files:BTreeMap::new(),errors:BTreeMap::new(),api_set_mappings:BTreeMap::new(),supported_minimum_os_build:"unknown_target_matrix_pending".into(),redistribution:"not_authorized_by_source_verification".into()},_held:Vec::new(),profile:profile.into(),artifact:artifact.into(),policy_sha:policy_sha.into(),host_pid,host_creation,catalog_budget:Mutex::new(CatalogReadBudget::new()),catalog_members:Vec::new(),source};
        if version[0]<10||!cfg!(target_arch="x86_64"){return Err("native_source_platform_condition_unverified");}
        // These are the already-linked metadata API carriers, not DLL payloads
        // chosen by the renderer or a source record. Their own origin is observed.
        for name in ["kernel32.dll","ntdll.dll","wintrust.dll","crypt32.dll"]{
            context.observe(&system,name,name)?;
            context.source.loaded_origin(name,&system.join(name))?;
        }
        let schema=system.join("apisetschema.dll");let mut table=None;
        if ids.iter().any(|id|contracts.get(id).is_some_and(|value|value["source_kind"]=="api_set")){
            context.observe(&system,"apisetschema.dll","api-set-schema")?;
            let mut file=context.source.open(&schema)?;let mut body=Vec::new();file.read_to_end(&mut body).map_err(|_|"native_api_set_schema_unavailable")?;table=Some(api_set_table(&body)?);
        }
        for id in ids{
            let contract=contracts.get(id).ok_or("native_system_contract_missing")?;
            if !contract["profiles"].as_array().is_some_and(|roles|roles.iter().any(|value|value==profile))||contract["architecture"]!="amd64"||contract["os"]!="windows"{return Err("native_system_contract_scope_invalid");}
            let name=contract["basename"].as_str().ok_or("native_system_contract_invalid")?;
            let result=(||{match contract["source_kind"].as_str(){
                Some("windows_component")=>context.observe(&system,name,id),
                Some("external_vc")=>context.observe_vc(&system,name,id,contract),
                Some("api_set")=>{
                    let targets=table.as_ref().and_then(|map|map.get(name.trim_end_matches(".dll"))).ok_or("native_api_set_target_unverified")?;
                    if targets.len()!=1{Err("native_api_set_mapping_not_unique")}else{
                        context.observations.api_set_mappings.insert(id.clone(),targets.clone());context.observe(&system,&targets[0],id)
                    }
                },
                _=>Err("native_source_kind_unknown"),
            }})();
            if let Err(error)=result{context.observations.errors.insert(id.clone(),error.into());}
        }
        Ok(Arc::new(context))
    }
    fn observe(&mut self,system:&Path,name:&str,id:&str)->Result<(),&'static str>{
        if name.contains(['/', '\\', ':'])||name.to_lowercase()!=name{return Err("native_system_basename_invalid");}
        let path=system.join(name);check_physical(&path)?;let path=path.canonicalize().map_err(|_|"native_source_missing")?;
        if path.parent()!=Some(system){return Err("native_source_os_path_invalid");}
        let mut file=self.source.open(&path)?;let size=file.metadata().map_err(|_|"native_source_metadata_failed")?.len();
        if size>128*1024*1024{return Err("native_source_oversize");}
        let mut body=Vec::new();file.read_to_end(&mut body).map_err(|_|"native_source_read_failed")?;
        let machine=pe_machine(&body)?;if machine!=0x8664{return Err("native_source_architecture_invalid");}
        let(static_imports,delay_imports)=pe_imports(&body)?;
        let identity=self.source.identity(&file)?;file.seek(SeekFrom::Start(0)).map_err(|_|"native_source_read_failed")?;
        let(signature,catalog)={
            let mut budget=self.catalog_budget.lock().map_err(|_|"native_source_catalog_budget_poisoned")?;
            self.source.signature(&path,&file,system,&mut budget)?
        };
        let signature_ok=signature.wintrust_status==0&&signature.publisher_organization.as_deref()==Some("Microsoft Corporation")&&signature.signer_certificate_sha256.is_some();
        if let Some(file)=catalog{
            let bytes=signature.catalog_bytes.ok_or("native_source_catalog_identity_missing")?;
            self.catalog_members.push((PathBuf::from(signature.catalog.as_ref().ok_or("native_source_catalog_identity_missing")?),bytes,signature.catalog_sha256.clone().ok_or("native_source_catalog_identity_missing")?,self.source.identity(&file)?));
            self._held.push(file);
        }
        self.observations.files.insert(id.into(),FileObservation{path:local_text(&path)?,bytes:body.len()as u64,sha256:format!("{:x}",Sha256::digest(&body)),machine,volume_serial:identity.0,file_index:identity.1,modified_filetime:identity.2,file_version:None,static_imports,delay_imports,signature});self._held.push(file);
        if !signature_ok{return Err("native_source_signature_or_publisher_unverified");}Ok(())
    }
    fn observe_vc(&mut self,system:&Path,name:&str,id:&str,contract:&Value)->Result<(),&'static str>{
        // External VC/MFC is not an OS-component exemption. A future pinned
        // payload toolset floor must be explicit; unknown never defaults to zero.
        self.observe(system,"version.dll","version-api-carrier")?;
        self.source.loaded_origin("version.dll",&system.join("version.dll"))?;
        self.observe(system,name,id)?;
        let version=self.source.file_version(Path::new(&self.observations.files.get(id).ok_or("native_vc_source_unavailable")?.path))?;
        self.observations.files.get_mut(id).ok_or("native_vc_source_unavailable")?.file_version=Some(version);
        let floor=contract["minimum_file_version"].as_array().ok_or("native_vc_toolset_floor_unverified")?;
        if floor.len()!=4{return Err("native_vc_toolset_floor_unverified");}
        let mut minimum=[0u16;4];for(index,value)in floor.iter().enumerate(){minimum[index]=u16::try_from(value.as_u64().ok_or("native_vc_toolset_floor_unverified")?).map_err(|_|"native_vc_toolset_floor_unverified")?;}
        if minimum[0]<14{return Err("native_vc_toolset_floor_unverified");}
        if version<minimum{return Err("native_vc_version_below_payload_floor");}Ok(())
    }
    pub(crate) fn carrier(self:Arc<Self>,directory:&Path)->Result<LaunchSourceCarrier,&'static str>{
        check_physical(directory)?;
        self.recheck()?;
        let value=json!({"format":"native-system-source-context-v2-candidate","host_pid":self.host_pid,"host_creation_filetime":self.host_creation,
            "profile":self.profile,"artifact_version":self.artifact,"policy_sha256":self.policy_sha,"observations":self.observations});
        let body=serde_json::to_vec(&value).map_err(|_|"native_source_carrier_invalid")?;
        if body.len()>16*1024*1024{return Err("native_source_carrier_oversize");}
        // A per-prepare create_new file. No replace or deletion of previous
        // failed carriers. The context and file handle remain with the child.
        let nonce=std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map_err(|_|"native_source_carrier_clock_invalid")?.as_nanos();
        let path=directory.join(format!("NativeSource-{}-{}-{nonce}.json",self.host_pid,self.host_creation));
        let mut output=OpenOptions::new().write(true).create_new(true).open(&path).map_err(|_|"native_source_carrier_unavailable")?;
        output.write_all(&body).and_then(|_|output.sync_all()).map_err(|_|"native_source_carrier_unavailable")?;drop(output);
        let held=open_held(&path)?;
        Ok(LaunchSourceCarrier{path,sha256:format!("{:x}",Sha256::digest(&body)),context:self,_held:held,bound:false})
    }
    pub(crate) fn observations(&self)->&SourceObservations{&self.observations}
    pub(crate) fn assert_qualification_identity(&self,artifact:&str,policy_sha:&str)->Result<(),&'static str>{
        if self.artifact!=artifact||self.policy_sha!=policy_sha{return Err("qualification_source_identity_mismatch");}
        self.recheck()
    }
    pub(crate) fn recheck(&self)->Result<(),&'static str>{
        let(win,system,version)=self.source.roots()?;let(pid,creation)=self.source.host_identity()?;
        if local_text(&win)?!=self.observations.windows_directory||local_text(&system)?!=self.observations.system_directory||version!=self.observations.os_version||pid!=self.host_pid||creation!=self.host_creation{return Err("native_source_context_changed");}
        for record in self.observations.files.values(){let mut file=self.source.open(Path::new(&record.path))?;let identity=self.source.identity(&file)?;
            let mut body=Vec::new();file.read_to_end(&mut body).map_err(|_|"native_source_read_failed")?;
            if identity!=(record.volume_serial,record.file_index,record.modified_filetime)||body.len()as u64!=record.bytes||format!("{:x}",Sha256::digest(&body))!=record.sha256{return Err("native_source_context_changed");}}
        for(path,bytes,sha,expected)in &self.catalog_members{let mut file=self.source.open(path)?;if self.source.identity(&file)?!=*expected{return Err("native_source_catalog_changed");}let body=self.catalog_budget.lock().map_err(|_|"native_source_catalog_budget_poisoned")?.read_catalog(&mut file)?;if body.len()as u64!=*bytes||format!("{:x}",Sha256::digest(&body))!=*sha{return Err("native_source_catalog_changed");}}
        Ok(())
    }
}
#[cfg(not(windows))]
impl VerifiedSystemContext {
    pub(crate) fn collect(_: &BTreeMap<String,Value>,_: &[String],_: &str,_: &str,_: &str)->Result<Arc<Self>,&'static str>{Err("native_source_platform_unqualified")}
    pub(crate) fn observations(&self)->&SourceObservations{&self.observations}
    pub(crate) fn carrier(self:Arc<Self>,_:&Path)->Result<LaunchSourceCarrier,&'static str>{Err("native_source_platform_unqualified")}
    fn recheck(&self)->Result<(),&'static str>{Err("native_source_platform_unqualified")}
}
