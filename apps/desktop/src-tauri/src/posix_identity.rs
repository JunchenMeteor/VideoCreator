//! Private POSIX facts. No JSON field constructs a retained kernel reference.
//! A read-only FD is not a resource immutability or installation credential.
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::{
    ffi::CString,
    fs::{File, Metadata},
    io::{Read, Seek, SeekFrom},
    os::{
        fd::{AsRawFd, FromRawFd, OwnedFd},
        unix::{ffi::OsStrExt, fs::MetadataExt},
    },
    path::{Component, Path, PathBuf},
    sync::atomic::{AtomicBool, Ordering},
};

pub type Fault = &'static str;

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(tag = "platform", deny_unknown_fields)]
pub enum ProcessBirth {
    #[serde(rename = "linux")]
    Linux { boot_id: String, start_ticks: u64 },
    #[serde(rename = "darwin")]
    Darwin {
        start_seconds: u64,
        start_microseconds: u64,
        pid_version: Option<u32>,
    },
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct ProcessIdentity {
    pub pid: u32,
    pub parent_pid: u32,
    pub uid: u32,
    pub gid: u32,
    pub birth: ProcessBirth,
    pub image: PathBuf,
    pub image_device: u64,
    pub image_inode: u64,
    pub image_bytes: u64,
    pub image_sha256: String,
}

/// Open each physical path component relative to the previous owned FD.
/// No symlink is followed, including an ancestor. No executable is loaded.
pub(crate) fn open_physical(path: &Path, directory: bool) -> Result<File, Fault> {
    if !path.is_absolute() {
        return Err("posix_path_not_absolute");
    }
    let mut anchor = unsafe {
        libc::open(
            c"/".as_ptr(),
            libc::O_RDONLY | libc::O_DIRECTORY | libc::O_CLOEXEC,
        )
    };
    if anchor < 0 {
        return Err("posix_root_open_failed");
    }
    let mut owner = unsafe { File::from_raw_fd(anchor) };
    let parts = path.components().collect::<Vec<_>>();
    for (index, part) in parts.iter().enumerate() {
        if matches!(part, Component::RootDir) {
            continue;
        }
        let Component::Normal(name) = part else {
            return Err("posix_path_component_invalid");
        };
        let name = CString::new(name.as_bytes()).map_err(|_| "posix_path_component_invalid")?;
        let is_directory = index + 1 < parts.len() || directory;
        let flags = libc::O_RDONLY
            | libc::O_CLOEXEC
            | libc::O_NOFOLLOW
            | if is_directory { libc::O_DIRECTORY } else { 0 };
        anchor = unsafe { libc::openat(owner.as_raw_fd(), name.as_ptr(), flags) };
        if anchor < 0 {
            return Err("posix_physical_open_failed");
        }
        owner = unsafe { File::from_raw_fd(anchor) };
    }
    let metadata = owner.metadata().map_err(|_| "posix_fstat_failed")?;
    if directory != metadata.is_dir() || (!directory && !metadata.is_file()) {
        return Err("posix_file_type_invalid");
    }
    Ok(owner)
}

pub(crate) fn assert_named_file(file: &File, path: &Path, directory: bool) -> Result<(), Fault> {
    let current = open_physical(path, directory)?;
    let held = file.metadata().map_err(|_| "posix_fstat_failed")?;
    let named = current.metadata().map_err(|_| "posix_fstat_failed")?;
    if held.dev() != named.dev() || held.ino() != named.ino() {
        return Err("posix_name_identity_changed");
    }
    Ok(())
}

pub(crate) fn assert_unchanged_metadata(before: &Metadata, after: &Metadata) -> Result<(), Fault> {
    if before.dev() != after.dev()
        || before.ino() != after.ino()
        || before.len() != after.len()
        || before.mtime() != after.mtime()
        || before.mtime_nsec() != after.mtime_nsec()
        || before.ctime() != after.ctime()
        || before.ctime_nsec() != after.ctime_nsec()
    {
        return Err("posix_file_changed_during_read");
    }
    Ok(())
}

fn image_facts(mut file: File) -> Result<(u64, u64, u64, String), Fault> {
    let before = file.metadata().map_err(|_| "posix_image_stat_failed")?;
    if !before.is_file() {
        return Err("posix_image_type_invalid");
    }
    let mut digest = Sha256::new();
    let mut buffer = [0; 65_536];
    let mut bytes = 0u64;
    loop {
        let count = file
            .read(&mut buffer)
            .map_err(|_| "posix_image_read_failed")?;
        if count == 0 {
            break;
        }
        bytes = bytes
            .checked_add(count as u64)
            .ok_or("posix_image_size_invalid")?;
        if bytes > before.len() {
            return Err("posix_image_changed");
        }
        digest.update(&buffer[..count]);
    }
    assert_unchanged_metadata(
        &before,
        &file.metadata().map_err(|_| "posix_image_stat_failed")?,
    )?;
    if bytes != before.len() {
        return Err("posix_image_changed");
    }
    file.seek(SeekFrom::Start(0))
        .map_err(|_| "posix_image_read_failed")?;
    Ok((
        before.dev(),
        before.ino(),
        bytes,
        format!("{:x}", digest.finalize()),
    ))
}

#[cfg(target_os = "linux")]
fn trusted_proc() -> Result<File, Fault> {
    let root = open_physical(Path::new("/proc"), true)?;
    let mut stat = std::mem::MaybeUninit::<libc::statfs>::uninit();
    if unsafe { libc::fstatfs(root.as_raw_fd(), stat.as_mut_ptr()) } != 0 {
        return Err("posix_procfs_stat_failed");
    }
    if unsafe { stat.assume_init() }.f_type != libc::PROC_SUPER_MAGIC {
        return Err("posix_procfs_source_invalid");
    }
    Ok(root)
}

#[cfg(target_os = "linux")]
fn proc_data(root: &File, name: &str, limit: u64) -> Result<Vec<u8>, Fault> {
    // Only fixed kernel-provided proc paths; this is not an arbitrary reader.
    let name = CString::new(name).map_err(|_| "posix_proc_path_invalid")?;
    let fd = unsafe {
        libc::openat(
            root.as_raw_fd(),
            name.as_ptr(),
            libc::O_RDONLY | libc::O_CLOEXEC | libc::O_NOFOLLOW,
        )
    };
    if fd < 0 {
        return Err("posix_proc_read_failed");
    }
    let mut bytes = Vec::new();
    unsafe { File::from_raw_fd(fd) }
        .take(limit + 1)
        .read_to_end(&mut bytes)
        .map_err(|_| "posix_proc_read_failed")?;
    if bytes.len() as u64 > limit {
        return Err("posix_proc_data_oversize");
    }
    Ok(bytes)
}

#[cfg(target_os = "linux")]
fn linux_row(root: &File, pid: u32) -> Result<(u32, u64), Fault> {
    let bytes = proc_data(root, &format!("{pid}/stat"), 16_384)?;
    let text = std::str::from_utf8(&bytes).map_err(|_| "posix_proc_data_invalid")?;
    // comm may itself contain ')'; fields after its last ')' start at field 3.
    let end = text.rfind(')').ok_or("posix_proc_data_invalid")?;
    let start = text.find('(').ok_or("posix_proc_data_invalid")?;
    if text[..start].trim().parse::<u32>().ok() != Some(pid) {
        return Err("posix_proc_pid_mismatch");
    }
    let fields = text[end + 1..].split_ascii_whitespace().collect::<Vec<_>>();
    let parent = fields
        .get(1)
        .ok_or("posix_proc_data_invalid")?
        .parse()
        .map_err(|_| "posix_proc_data_invalid")?;
    let ticks = fields
        .get(19)
        .ok_or("posix_proc_data_invalid")?
        .parse()
        .map_err(|_| "posix_proc_data_invalid")?;
    Ok((parent, ticks))
}

#[cfg(target_os = "linux")]
pub fn query_identity(pid: u32) -> Result<ProcessIdentity, Fault> {
    if pid == 0 || pid > i32::MAX as u32 {
        return Err("posix_pid_invalid");
    }
    let proc = trusted_proc()?;
    let (parent, ticks) = linux_row(&proc, pid)?;
    let boot = proc_data(&proc, "sys/kernel/random/boot_id", 64)?;
    let boot = std::str::from_utf8(&boot)
        .map_err(|_| "posix_boot_id_invalid")?
        .trim()
        .to_owned();
    if boot.len() != 36 || !boot.bytes().all(|b| b.is_ascii_hexdigit() || b == b'-') {
        return Err("posix_boot_id_invalid");
    }
    let process_dir = open_physical(&PathBuf::from("/proc").join(pid.to_string()), true)?;
    let credentials = process_dir
        .metadata()
        .map_err(|_| "posix_proc_stat_failed")?;
    // exe is intentionally the kernel procfs link, after fs type verification.
    let exe_name = CString::new(format!("{pid}/exe")).map_err(|_| "posix_proc_path_invalid")?;
    let image_fd = unsafe {
        libc::openat(
            proc.as_raw_fd(),
            exe_name.as_ptr(),
            libc::O_RDONLY | libc::O_CLOEXEC,
        )
    };
    if image_fd < 0 {
        return Err("posix_image_open_failed");
    }
    let image = std::fs::read_link(PathBuf::from("/proc").join(pid.to_string()).join("exe"))
        .map_err(|_| "posix_image_query_failed")?;
    let (device, inode, bytes, sha) = image_facts(unsafe { File::from_raw_fd(image_fd) })?;
    let check_fd = unsafe {
        libc::openat(
            proc.as_raw_fd(),
            exe_name.as_ptr(),
            libc::O_RDONLY | libc::O_CLOEXEC,
        )
    };
    if check_fd < 0 {
        return Err("posix_image_open_failed");
    }
    let check_file = unsafe { File::from_raw_fd(check_fd) };
    let check = check_file
        .metadata()
        .map_err(|_| "posix_image_stat_failed")?;
    if check.dev() != device
        || check.ino() != inode
        || check.len() != bytes
        || std::fs::read_link(PathBuf::from("/proc").join(pid.to_string()).join("exe"))
            .map_err(|_| "posix_image_query_failed")?
            != image
    {
        return Err("posix_image_changed");
    }
    if linux_row(&proc, pid)? != (parent, ticks) {
        return Err("posix_birth_changed");
    }
    let after = process_dir
        .metadata()
        .map_err(|_| "posix_proc_stat_failed")?;
    if after.uid() != credentials.uid() || after.gid() != credentials.gid() {
        return Err("posix_credentials_changed");
    }
    Ok(ProcessIdentity {
        pid,
        parent_pid: parent,
        uid: credentials.uid(),
        gid: credentials.gid(),
        birth: ProcessBirth::Linux {
            boot_id: boot,
            start_ticks: ticks,
        },
        image,
        image_device: device,
        image_inode: inode,
        image_bytes: bytes,
        image_sha256: sha,
    })
}

#[cfg(target_os = "macos")]
fn darwin_row(pid: u32) -> Result<libc::proc_bsdinfo, Fault> {
    if pid == 0 || pid > i32::MAX as u32 {
        return Err("posix_pid_invalid");
    }
    let mut info = std::mem::MaybeUninit::<libc::proc_bsdinfo>::uninit();
    let size = std::mem::size_of::<libc::proc_bsdinfo>();
    let count = unsafe {
        libc::proc_pidinfo(
            pid as i32,
            libc::PROC_PIDTBSDINFO,
            0,
            info.as_mut_ptr().cast(),
            size as i32,
        )
    };
    if count != size as i32 {
        return Err("posix_birth_query_failed");
    }
    let info = unsafe { info.assume_init() };
    if info.pbi_pid != pid || info.pbi_start_tvusec >= 1_000_000 {
        return Err("posix_birth_invalid");
    }
    Ok(info)
}

#[cfg(target_os = "macos")]
pub fn query_identity(pid: u32) -> Result<ProcessIdentity, Fault> {
    let before = darwin_row(pid)?;
    let mut bytes = vec![0u8; libc::PROC_PIDPATHINFO_MAXSIZE as usize];
    let count =
        unsafe { libc::proc_pidpath(pid as i32, bytes.as_mut_ptr().cast(), bytes.len() as u32) };
    if count <= 0 || count as usize >= bytes.len() {
        return Err("posix_image_query_failed");
    }
    let nul = bytes
        .iter()
        .position(|b| *b == 0)
        .ok_or("posix_image_query_failed")?;
    let image = PathBuf::from(std::ffi::OsStr::from_bytes(&bytes[..nul]));
    let (device, inode, bytes, sha) = image_facts(open_physical(&image, false)?)?;
    let after = darwin_row(pid)?;
    if before.pbi_pid != after.pbi_pid
        || before.pbi_ppid != after.pbi_ppid
        || before.pbi_uid != after.pbi_uid
        || before.pbi_gid != after.pbi_gid
        || before.pbi_start_tvsec != after.pbi_start_tvsec
        || before.pbi_start_tvusec != after.pbi_start_tvusec
    {
        return Err("posix_birth_changed");
    }
    // Audit-token pidversion is not fabricated from libproc birth. A later
    // SDK-bound LOCAL_PEERTOKEN adapter must add it when actually available.
    Ok(ProcessIdentity {
        pid,
        parent_pid: before.pbi_ppid,
        uid: before.pbi_uid,
        gid: before.pbi_gid,
        birth: ProcessBirth::Darwin {
            start_seconds: before.pbi_start_tvsec,
            start_microseconds: before.pbi_start_tvusec,
            pid_version: None,
        },
        image,
        image_device: device,
        image_inode: inode,
        image_bytes: bytes,
        image_sha256: sha,
    })
}

/// The retained FD is private; text PID and serialized birth cannot recreate it.
pub struct RetainedProcess {
    identity: ProcessIdentity,
    reference: OwnedFd,
    invalid: AtomicBool,
}
impl RetainedProcess {
    pub fn capture(pid: u32) -> Result<Self, Fault> {
        let before = query_identity(pid)?;
        #[cfg(target_os = "linux")]
        let fd = unsafe { libc::syscall(libc::SYS_pidfd_open, pid as libc::pid_t, 0) } as i32;
        #[cfg(target_os = "macos")]
        let fd = unsafe { libc::kqueue() };
        if fd < 0 {
            return Err("posix_process_reference_failed");
        }
        let reference = unsafe { OwnedFd::from_raw_fd(fd) };
        #[cfg(target_os = "macos")]
        {
            let event = libc::kevent {
                ident: pid as libc::uintptr_t,
                filter: libc::EVFILT_PROC,
                flags: libc::EV_ADD | libc::EV_ENABLE | libc::EV_CLEAR,
                fflags: libc::NOTE_EXIT | libc::NOTE_EXEC | libc::NOTE_FORK,
                data: 0,
                udata: std::ptr::null_mut(),
            };
            if unsafe { libc::kevent(fd, &event, 1, std::ptr::null_mut(), 0, std::ptr::null()) } < 0
            {
                return Err("posix_process_registration_failed");
            }
        }
        if query_identity(pid)? != before {
            return Err("posix_birth_changed");
        }
        let result = Self {
            identity: before,
            reference,
            invalid: AtomicBool::new(false),
        };
        result.assert_live()?;
        Ok(result)
    }
    pub fn identity(&self) -> &ProcessIdentity {
        &self.identity
    }
    pub fn assert_live(&self) -> Result<(), Fault> {
        if self.invalid.load(Ordering::Acquire) {
            return Err("posix_process_reference_invalid");
        }
        let result = self.check_live();
        if result.is_err() {
            self.invalid.store(true, Ordering::Release);
        }
        result
    }
    fn check_live(&self) -> Result<(), Fault> {
        #[cfg(target_os = "linux")]
        {
            let mut event = libc::pollfd {
                fd: self.reference.as_raw_fd(),
                events: libc::POLLIN,
                revents: 0,
            };
            let count = unsafe { libc::poll(&mut event, 1, 0) };
            if count < 0 {
                return Err("posix_process_observation_failed");
            }
            if count != 0 {
                return Err("posix_process_not_live");
            }
        }
        #[cfg(target_os = "macos")]
        {
            let mut events = [unsafe { std::mem::zeroed::<libc::kevent>() }; 4];
            let zero = libc::timespec {
                tv_sec: 0,
                tv_nsec: 0,
            };
            let count = unsafe {
                libc::kevent(
                    self.reference.as_raw_fd(),
                    std::ptr::null(),
                    0,
                    events.as_mut_ptr(),
                    events.len() as i32,
                    &zero,
                )
            };
            if count < 0 {
                return Err("posix_process_observation_failed");
            }
            if count != 0 {
                return Err("posix_process_event_changed");
            }
        }
        if query_identity(self.identity.pid)? != self.identity {
            return Err("posix_process_identity_changed");
        }
        Ok(())
    }
}
