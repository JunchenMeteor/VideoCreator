//! Original directory HANDLEs and OS owner, not serialized directory proof.
use std::{fs::{File,OpenOptions},path::{Component,Prefix,Path,PathBuf},os::windows::{fs::{MetadataExt,OpenOptionsExt},io::AsRawHandle}};
use windows_sys::Win32::{Foundation::{HANDLE,LocalFree},Storage::FileSystem::{GetFileInformationByHandle,BY_HANDLE_FILE_INFORMATION},
    Security::{GetAce,GetAclInformation,ACL,ACL_SIZE_INFORMATION,AclSizeInformation,DACL_SECURITY_INFORMATION,OWNER_SECURITY_INFORMATION,PSID},
    Security::Authorization::{ConvertSidToStringSidW,GetSecurityInfo,SE_FILE_OBJECT}};

fn file_id(file:&File)->Result<(u32,u64),&'static str>{
    let mut info:BY_HANDLE_FILE_INFORMATION=unsafe{std::mem::zeroed()};
    if unsafe{GetFileInformationByHandle(file.as_raw_handle()as HANDLE,&mut info)}==0{return Err("owner_setup_directory_unavailable");}
    Ok((info.dwVolumeSerialNumber,((info.nFileIndexHigh as u64)<<32)|info.nFileIndexLow as u64))
}
fn open(path:&Path)->Result<File,&'static str>{
    let file=OpenOptions::new().read(true).share_mode(1|2).custom_flags(0x0020_0000|0x0200_0000).open(path).map_err(|_|"owner_setup_directory_unavailable")?;
    let metadata=file.metadata().map_err(|_|"owner_setup_directory_unavailable")?;
    if !metadata.is_dir()||metadata.file_attributes()&0x400!=0{return Err("owner_setup_directory_alias_denied");}Ok(file)
}
fn sid_text(sid:PSID)->Result<String,&'static str>{
    if sid.is_null(){return Err("owner_setup_directory_owner_unknown");}
    let mut raw=std::ptr::null_mut();
    if unsafe{ConvertSidToStringSidW(sid,&mut raw)}==0{return Err("owner_setup_directory_owner_unknown");}
    let result=(||{let mut length=0;while length<256&&unsafe{*raw.add(length)}!=0{length+=1;}if length==256{return Err("owner_setup_directory_owner_unknown");}
        String::from_utf16(unsafe{std::slice::from_raw_parts(raw,length)}).map_err(|_|"owner_setup_directory_owner_unknown")})();
    unsafe{LocalFree(raw.cast());}result
}
fn owner(file:&File,expected:&str)->Result<(),&'static str>{
    let mut descriptor=std::ptr::null_mut();let mut owner=std::ptr::null_mut();let mut dacl:*mut ACL=std::ptr::null_mut();
    if unsafe{GetSecurityInfo(file.as_raw_handle()as HANDLE,SE_FILE_OBJECT,OWNER_SECURITY_INFORMATION|DACL_SECURITY_INFORMATION,&mut owner,std::ptr::null_mut(),&mut dacl,std::ptr::null_mut(),&mut descriptor)}!=0{return Err("owner_setup_directory_owner_unknown");}
    let result=(||{
        if sid_text(owner)?!=expected||dacl.is_null(){return Err("owner_setup_directory_owner_denied");}
        let mut info:ACL_SIZE_INFORMATION=unsafe{std::mem::zeroed()};
        if unsafe{GetAclInformation(dacl,(&mut info as *mut ACL_SIZE_INFORMATION).cast(),std::mem::size_of_val(&info)as u32,AclSizeInformation)}==0{return Err("owner_setup_directory_owner_unknown");}
        let unsafe_rights=0x1000_0000|0x4000_0000|0x0008_0000|0x0004_0000|0x0001_0000|0x100|0x40|0x10|0x4|0x2;
        for index in 0..info.AceCount{
            let mut entry=std::ptr::null_mut();if unsafe{GetAce(dacl,index,&mut entry)}==0{return Err("owner_setup_directory_owner_unknown");}
            let bytes=entry as *const u8;let kind=unsafe{*bytes};let flags=unsafe{*bytes.add(1)};
            if flags&0x08!=0{continue;}
            if [0,5,9,11].contains(&kind){let mask=unsafe{std::ptr::read_unaligned(bytes.add(4)as *const u32)};
                if mask&unsafe_rights!=0{
                    if kind!=0{return Err("owner_setup_directory_owner_denied");}
                    let sid=sid_text(unsafe{bytes.add(8)}as PSID)?;
                    if ![expected,"S-1-5-18","S-1-5-32-544"].contains(&sid.as_str()){return Err("owner_setup_directory_owner_denied");}
                }
            }
        }Ok(())
    })();
    unsafe{LocalFree(descriptor.cast());}result
}
pub(crate) struct OwnerDirectory {
    root:PathBuf,subject:String,held:Vec<(PathBuf,File,(u32,u64))>,
}
fn local_path(path:&Path)->Result<PathBuf,&'static str>{
    let mut parts=path.components();
    let drive=match parts.next(){Some(Component::Prefix(prefix))=>match prefix.kind(){Prefix::Disk(value)|Prefix::VerbatimDisk(value)=>value,_=>return Err("owner_setup_directory_invalid")},_=>return Err("owner_setup_directory_invalid")};
    if !matches!(parts.next(),Some(Component::RootDir)){return Err("owner_setup_directory_invalid");}
    let mut result=PathBuf::from(format!("{}:\\",drive as char));
    for part in parts{match part{Component::Normal(name)=>result.push(name),_=>return Err("owner_setup_directory_invalid")}}
    Ok(result)
}
impl OwnerDirectory {
    pub(crate) fn hold(path:&Path,subject:&str)->Result<Self,&'static str>{
        // Only local drive verbatim spelling is equivalent. UNC/devices and
        // traversal are not admitted; each ancestor still has an original HANDLE.
        let path=local_path(path)?;
        let root=path.canonicalize().map_err(|_|"owner_setup_directory_unavailable")?;
        let mut ancestors=path.ancestors().collect::<Vec<_>>();ancestors.reverse();let mut held=Vec::new();
        for name in ancestors{let file=open(name)?;let identity=file_id(&file)?;held.push((name.to_owned(),file,identity));}
        let directory=held.last().ok_or("owner_setup_directory_invalid")?;owner(&directory.1,subject)?;
        Ok(Self{root,subject:subject.into(),held})
    }
    pub(crate) fn assert_current(&self)->Result<(),&'static str>{
        for(name,file,original)in &self.held{
            if file_id(file)?!=*original||file_id(&open(name)?)?!=*original{return Err("owner_setup_directory_changed");}
        }
        owner(&self.held.last().ok_or("owner_setup_directory_invalid")?.1,&self.subject)
    }
    pub(crate) fn assert_intent(&self,path:&str,subject:&str,administrator:&str)->Result<(),&'static str>{
        self.assert_current()?;
        if subject!=self.subject||administrator!=self.subject{return Err("owner_setup_directory_owner_denied");}
        let path=local_path(Path::new(path))?;
        if path.canonicalize().map_err(|_|"owner_setup_directory_unavailable")?!=self.root{return Err("owner_setup_directory_changed");}
        // Native rechecks its original HANDLE identity. Backend independently
        // computes st_dev/st_ino and validates its unique Directory model;
        // BY_HANDLE_FILE_INFORMATION is never passed off as Python stat.
        if file_id(&open(&path)?)?!=self.held.last().ok_or("owner_setup_directory_invalid")?.2{return Err("owner_setup_directory_changed");}Ok(())
    }
}
