//! Trusted launcher pins, held before a child can execute. No renderer file API.
use std::{collections::BTreeSet,fs::{File,OpenOptions},io::{Read,Seek,SeekFrom},path::{Component,Path,PathBuf},sync::Mutex,time::{SystemTime,UNIX_EPOCH}};
use serde::{Deserialize,Serialize};
use sha2::{Digest,Sha256};

#[derive(Clone,Debug,Deserialize,Serialize)]
#[serde(deny_unknown_fields)]
pub struct PinnedFile {pub relative_path:String,pub bytes:u64,pub sha256:String}
pub struct ResourcePins { root:PathBuf,files:BTreeSet<PathBuf>,_held:Vec<Mutex<File>>,_entries:Vec<PinnedFile>,_paths:Vec<PathBuf>,_directories:Vec<File>,_directory_paths:Vec<PathBuf> }
/// Actual facts read from this guard's owned handles. This is neither an
/// installation qualification nor a transferable authentication credential.
/// Its private issuer and borrow prevent another guard or a deserialized DTO
/// from being substituted when checking whether these facts remain current.
pub struct HeldFileObservation<'guard> {
    issuer:&'guard ResourcePins,
    indices:Vec<usize>,
    observed_at_us:u64,
    facts:Vec<PinnedFile>,
}
impl HeldFileObservation<'_> {
    pub fn observed_at_us(&self)->u64{self.observed_at_us}
    pub fn files(&self)->&[PinnedFile]{&self.facts}
}
fn open_file(path:&Path,directory:bool)->Result<File,&'static str>{
    #[cfg(any(target_os="linux",target_os="macos"))]
    {return crate::posix_identity::open_physical(path,directory);}
    #[cfg(not(any(target_os="linux",target_os="macos")))]
    {
    let mut options=OpenOptions::new();options.read(true);
    #[cfg(windows)]{
        use std::os::windows::fs::OpenOptionsExt;
        // Files deny write/delete; ancestor directories deny rename/delete.
        options.share_mode(if directory{1|2}else{1});
        options.custom_flags(0x0020_0000|if directory{0x0200_0000}else{0});
    }
    #[cfg(not(windows))]{let _=directory;}
    options.open(path).map_err(|_|"native_resource_pin_failed")
    }
}
fn local_path(path:&Path)->bool{
    path.is_absolute()&&!path.to_string_lossy().starts_with("\\\\")&&!path.to_string_lossy().starts_with("//")
}
impl ResourcePins {
    pub fn hold(root:&Path,items:&[PinnedFile])->Result<Self,&'static str>{
        if !local_path(root)||items.is_empty(){return Err("native_resource_root_invalid");}
        if std::fs::symlink_metadata(root).map_err(|_|"native_resource_root_invalid")?.file_type().is_symlink(){return Err("native_resource_root_invalid");}
        let root=root.canonicalize().map_err(|_|"native_resource_root_invalid")?;
        let mut held=Vec::new();let mut entries=Vec::new();let mut paths=Vec::new();let mut files=BTreeSet::new();let mut parents=BTreeSet::new();let mut directories=Vec::new();let mut directory_paths=Vec::new();
        // Anchor physical ancestor names before resolving or hashing any executable.
        let mut ancestors=root.ancestors().collect::<Vec<_>>();ancestors.reverse();
        for parent in ancestors{
            let directory=open_file(parent,true)?;
            #[cfg(windows)]{use std::os::windows::fs::MetadataExt;if directory.metadata().map_err(|_|"native_resource_pin_failed")?.file_attributes()&0x400!=0{return Err("native_resource_reparse_denied");}}
            parents.insert(parent.to_owned());directories.push(directory);directory_paths.push(parent.to_owned());
        }
        for item in items{
            let relative=Path::new(&item.relative_path);
            if relative.is_absolute()||relative.components().any(|c|!matches!(c,Component::Normal(_)))||item.sha256.len()!=64||!item.sha256.bytes().all(|b|b.is_ascii_digit()||(b'a'..=b'f').contains(&b)){return Err("native_resource_entry_invalid");}
            let mut current=root.clone();
            for part in relative.components(){current.push(part.as_os_str());
                let metadata=std::fs::symlink_metadata(&current).map_err(|_|"native_resource_missing")?;
                #[cfg(windows)]{use std::os::windows::fs::MetadataExt;if metadata.file_attributes()&0x400!=0{return Err("native_resource_reparse_denied");}}
                if metadata.file_type().is_symlink(){return Err("native_resource_reparse_denied");}
                if metadata.is_dir()&&parents.insert(current.clone()){
                    let directory=open_file(&current,true)?;
                    #[cfg(windows)]{use std::os::windows::fs::MetadataExt;if directory.metadata().map_err(|_|"native_resource_pin_failed")?.file_attributes()&0x400!=0{return Err("native_resource_reparse_denied");}}
                    directories.push(directory);directory_paths.push(current.clone());
                }
            }
            let canonical=current.canonicalize().map_err(|_|"native_resource_missing")?;
            if !canonical.starts_with(&root)||!files.insert(canonical.clone()){return Err("native_resource_entry_invalid");}
            let mut file=open_file(&canonical,false)?;
            if !file.metadata().map_err(|_|"native_resource_pin_failed")?.is_file()||file.metadata().map_err(|_|"native_resource_pin_failed")?.len()!=item.bytes{return Err("native_resource_integrity_failed");}
            let mut digest=Sha256::new();let mut bytes=[0;65_536];
            loop{let count=file.read(&mut bytes).map_err(|_|"native_resource_pin_failed")?;if count==0{break;}digest.update(&bytes[..count]);}
            if format!("{:x}",digest.finalize())!=item.sha256{return Err("native_resource_integrity_failed");}
            file.seek(SeekFrom::Start(0)).map_err(|_|"native_resource_pin_failed")?;
            held.push(Mutex::new(file));entries.push(item.clone());paths.push(canonical);
        }
        Ok(Self{root,files,_held:held,_entries:entries,_paths:paths,_directories:directories,_directory_paths:directory_paths})
    }
    pub fn resolve(&self,relative:&str)->Result<PathBuf,&'static str>{
        let relative=Path::new(relative);
        if relative.is_absolute()||relative.components().any(|c|!matches!(c,Component::Normal(_))){return Err("native_resource_entry_invalid");}
        let path=self.root.join(relative).canonicalize().map_err(|_|"native_resource_missing")?;
        if !self.files.contains(&path){return Err("native_resource_unpinned");}Ok(path)
    }
    pub fn root(&self)->&Path{&self.root}
    /// Bounded control bytes from the same original deny-write/physical file.
    /// No second pathname open is used to replace the held observation source.
    pub(crate) fn read_held_bytes(&self,relative:&str,limit:usize)->Result<Vec<u8>,&'static str>{
        let path=self.resolve(relative)?;
        let index=self._paths.iter().position(|candidate|candidate==&path).ok_or("native_resource_unpinned")?;
        let before=self.read_held_fact(index)?;
        if before.bytes>limit as u64{return Err("native_resource_control_oversized");}
        let mut file=self._held[index].lock().map_err(|_|"native_resource_observation_lock_failed")?;
        file.seek(SeekFrom::Start(0)).map_err(|_|"native_resource_observation_read_failed")?;
        let mut raw=Vec::new();let result=(&mut *file).take(before.bytes+1).read_to_end(&mut raw);
        let restored=file.seek(SeekFrom::Start(0));drop(file);
        result.map_err(|_|"native_resource_observation_read_failed")?;
        restored.map_err(|_|"native_resource_observation_read_failed")?;
        if raw.len()as u64!=before.bytes||format!("{:x}",Sha256::digest(&raw))!=before.sha256{return Err("native_resource_integrity_failed");}
        let after=self.read_held_fact(index)?;
        if after.bytes!=before.bytes||after.sha256!=before.sha256{return Err("native_resource_observation_changed");}Ok(raw)
    }
    /// The trusted host selects the complete held map. RPC callers cannot
    /// supply paths or narrow the installation being observed.
    pub fn observe_all(&self)->Result<HeldFileObservation<'_>,&'static str>{
        let names=self._entries.iter().map(|entry|entry.relative_path.as_str()).collect::<Vec<_>>();
        self.observe_files(&names)
    }
    fn read_held_fact(&self,index:usize)->Result<PinnedFile,&'static str>{
        let entry=self._entries.get(index).ok_or("native_resource_observation_invalid")?;
        let path=self._paths.get(index).ok_or("native_resource_observation_invalid")?;
        if self.resolve(&entry.relative_path)?!=*path{return Err("native_resource_observation_path_changed");}
        let mut file=self._held.get(index).ok_or("native_resource_observation_invalid")?
            .lock().map_err(|_|"native_resource_observation_lock_failed")?;
        #[cfg(any(target_os="linux",target_os="macos"))]
        {
            for(directory,name)in self._directories.iter().zip(&self._directory_paths){crate::posix_identity::assert_named_file(directory,name,true)?;}
            crate::posix_identity::assert_named_file(&file,path,false)?;
        }
        let result=(||{
            let metadata=file.metadata().map_err(|_|"native_resource_observation_read_failed")?;
            if !metadata.is_file()||metadata.len()!=entry.bytes{return Err("native_resource_integrity_failed");}
            #[cfg(windows)]{use std::os::windows::fs::MetadataExt;if metadata.file_attributes()&0x400!=0{return Err("native_resource_reparse_denied");}}
            file.seek(SeekFrom::Start(0)).map_err(|_|"native_resource_observation_read_failed")?;
            let mut digest=Sha256::new();let mut buffer=[0;65_536];let mut bytes=0u64;
            loop{
                let count=file.read(&mut buffer).map_err(|_|"native_resource_observation_read_failed")?;
                if count==0{break;}
                bytes=bytes.checked_add(count as u64).ok_or("native_resource_integrity_failed")?;
                if bytes>entry.bytes{return Err("native_resource_integrity_failed");}
                digest.update(&buffer[..count]);
            }
            let sha256=format!("{:x}",digest.finalize());
            if bytes!=entry.bytes||sha256!=entry.sha256{return Err("native_resource_integrity_failed");}
            #[cfg(any(target_os="linux",target_os="macos"))]
            {
                crate::posix_identity::assert_named_file(&file,path,false)?;
                crate::posix_identity::assert_unchanged_metadata(&metadata,&file.metadata().map_err(|_|"native_resource_observation_read_failed")?)?;
            }
            Ok(PinnedFile{relative_path:entry.relative_path.clone(),bytes,sha256})
        })();
        // A failed observation leaves all handles owned by this guard. Failure
        // to restore the shared file position also refuses a successful result.
        let restored=file.seek(SeekFrom::Start(0)).map_err(|_|"native_resource_observation_read_failed");
        match result{Err(error)=>Err(error),Ok(fact)=>{restored?;Ok(fact)}}
    }
    pub fn observe_files<'guard>(&'guard self,relative_paths:&[&str])->Result<HeldFileObservation<'guard>,&'static str>{
        // POSIX produces original-FD facts only. These checks do not deny a
        // concurrent writer and cannot construct installation qualification.
        if !cfg!(any(windows,target_os="linux",target_os="macos")){return Err("native_resource_observation_platform_unsupported");}
        if relative_paths.is_empty(){return Err("native_resource_observation_empty");}
        let mut seen=BTreeSet::new();let mut indices=Vec::new();let mut facts=Vec::new();
        for relative in relative_paths{
            let path=self.resolve(relative)?;
            let index=self._paths.iter().position(|candidate|candidate==&path)
                .ok_or("native_resource_unpinned")?;
            if !seen.insert(index){return Err("native_resource_observation_duplicate");}
            indices.push(index);facts.push(self.read_held_fact(index)?);
        }
        let observed_at_us=u64::try_from(SystemTime::now().duration_since(UNIX_EPOCH)
            .map_err(|_|"native_resource_observation_clock_invalid")?.as_micros())
            .map_err(|_|"native_resource_observation_clock_invalid")?;
        if observed_at_us==0{return Err("native_resource_observation_clock_invalid");}
        Ok(HeldFileObservation{issuer:self,indices,observed_at_us,facts})
    }
    pub fn assert_current(&self,observation:&HeldFileObservation<'_>)->Result<(),&'static str>{
        if !std::ptr::eq(self,observation.issuer){return Err("native_resource_observation_issuer_invalid");}
        if observation.indices.len()!=observation.facts.len()||observation.indices.is_empty(){return Err("native_resource_observation_invalid");}
        for(index,prior)in observation.indices.iter().zip(&observation.facts){
            let actual=self.read_held_fact(*index)?;
            if actual.relative_path!=prior.relative_path||actual.bytes!=prior.bytes||actual.sha256!=prior.sha256{
                return Err("native_resource_observation_changed");
            }
        }
        Ok(())
    }
}
