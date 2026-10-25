//! Native POSIX facts-session slice. The caller owns the actual child and
//! original guard. This module neither creates installation Evidence nor
//! releases a resource version merely because its socket closes.
use crate::{
    posix_identity::{self, Fault, ProcessIdentity, RetainedProcess},
    resource_pins::{HeldFileObservation, PinnedFile, ResourcePins},
};
use serde::{Deserialize, Serialize};
use std::{
    collections::BTreeMap,
    fs::File,
    io::{Read, Write},
    os::{
        fd::AsRawFd,
        unix::{
            fs::{DirBuilderExt, FileTypeExt, MetadataExt, PermissionsExt},
            net::{UnixListener, UnixStream},
        },
    },
    path::{Path, PathBuf},
    process::Child,
    sync::{Arc, Mutex, OnceLock},
    time::{Duration, Instant},
};

const WIRE: &str = "held-resource-authority-v1-candidate";
const TRANSPORT: &str = "unix-domain-v1-candidate";
const MAX_FRAME: usize = 32 * 1024 * 1024;
const LAUNCH_DEADLINE: Duration = Duration::from_secs(20);
const CALL_DEADLINE: Duration = Duration::from_secs(10);

#[derive(Clone, Debug, Serialize)]
pub struct ChildLocator {
    pub transport: &'static str,
    pub socket: PathBuf,
    pub session: String,
    pub instance_id: String,
    pub role: String,
    pub server: ProcessIdentity,
}

#[derive(Clone, Debug)]
pub struct FactsContext {
    pub instance_id: String,
    pub role: String,
    pub registration_sha256: String,
    pub resource_manifest_sha256: String,
    pub runtime_manifest_sha256: String,
}

impl FactsContext {
    fn validate(&self) -> Result<(), Fault> {
        if self.instance_id.is_empty()
            || self.instance_id.len() > 128
            || !matches!(self.role.as_str(), "api" | "worker" | "mcp" | "asr")
            || [
                &self.registration_sha256,
                &self.resource_manifest_sha256,
                &self.runtime_manifest_sha256,
            ]
            .iter()
            .any(|s| {
                s.len() != 64
                    || !s
                        .bytes()
                        .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
            })
        {
            return Err("authority_context_invalid");
        }
        Ok(())
    }
}

/// This takes the original std Child, not a PID supplied by a request. The
/// caller must still retain its PreparedLaunch and pre-code start gate. That
/// gate/closed-scope assembly is a separate unfinished slice, not inferred by
/// this constructor from a parent relationship.
struct OwnedRecord {
    child: Child,
    reference: RetainedProcess,
    guard: Arc<ResourcePins>,
}
pub struct OwnedPeer {
    record: Option<OwnedRecord>,
}
impl OwnedPeer {
    pub fn retain_actual_child(
        child: Child,
        guard: Arc<ResourcePins>,
        child_image_relative: &str,
    ) -> Result<Self, (Child, Fault)> {
        let expected = match guard.observe_files(&[child_image_relative]) {
            Ok(observed) => observed.files()[0].clone(),
            Err(error) => return Err((child, error)),
        };
        let expected_image = match guard.resolve(child_image_relative) {
            Ok(path) => path,
            Err(error) => return Err((child, error)),
        };
        let reference = match RetainedProcess::capture(child.id()) {
            Ok(value) => value,
            Err(error) => return Err((child, error)),
        };
        if reference.identity().parent_pid != std::process::id() {
            return Err((child, "authority_child_parent_invalid"));
        }
        if reference.identity().image != expected_image
            || reference.identity().image_bytes != expected.bytes
            || reference.identity().image_sha256 != expected.sha256
        {
            return Err((child, "authority_child_image_invalid"));
        }
        Ok(Self {
            record: Some(OwnedRecord {
                child,
                reference,
                guard,
            }),
        })
    }
    fn record(&self) -> &OwnedRecord {
        self.record
            .as_ref()
            .expect("owned record is removed only during Drop")
    }
    pub fn identity(&self) -> &ProcessIdentity {
        self.record().reference.identity()
    }
    pub fn guard(&self) -> &ResourcePins {
        &self.record().guard
    }
    pub fn confirm_owned_scope_terminal(&mut self) -> ScopeTerminal {
        match self
            .record
            .as_mut()
            .expect("owned record is removed only during Drop")
            .child
            .try_wait()
        {
            Ok(None) => ScopeTerminal::StillLive,
            Ok(Some(_)) => ScopeTerminal::Unknown("descendant_scope_and_output_eof_not_bound"),
            Err(_) => ScopeTerminal::Unknown("original_child_wait_observation_failed"),
        }
    }
}

#[derive(Debug, Eq, PartialEq)]
pub enum ScopeTerminal {
    Confirmed,
    StillLive,
    Unknown(&'static str),
}

/// Deliberate retention on an unconfirmed scope, instead of dropping the guard
/// after a direct child exit. Host-crash durability remains unimplemented.
impl Drop for OwnedPeer {
    fn drop(&mut self) {
        // Retain the ORIGINAL child, pidfd/kqueue and Arc, not a shadow guard.
        // No current caller can prove descendant closure in this source slice.
        static QUARANTINE: OnceLock<Mutex<Vec<OwnedRecord>>> = OnceLock::new();
        if let Some(record) = self.record.take() {
            match QUARANTINE.get_or_init(|| Mutex::new(Vec::new())).lock() {
                Ok(mut records) => records.push(record),
                // A poisoned quarantine must not become permission to release.
                Err(_) => std::mem::forget(record),
            }
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct PeerCredentials {
    pid: u32,
    uid: u32,
    gid: u32,
}
fn actual_peer(stream: &UnixStream) -> Result<PeerCredentials, Fault> {
    #[cfg(target_os = "linux")]
    {
        let mut cred = std::mem::MaybeUninit::<libc::ucred>::uninit();
        let mut size = std::mem::size_of::<libc::ucred>() as libc::socklen_t;
        if unsafe {
            libc::getsockopt(
                stream.as_raw_fd(),
                libc::SOL_SOCKET,
                libc::SO_PEERCRED,
                cred.as_mut_ptr().cast(),
                &mut size,
            )
        } != 0
            || size as usize != std::mem::size_of::<libc::ucred>()
        {
            return Err("authority_peer_query_failed");
        }
        let cred = unsafe { cred.assume_init() };
        if cred.pid <= 0 {
            return Err("authority_peer_invalid");
        }
        Ok(PeerCredentials {
            pid: cred.pid as u32,
            uid: cred.uid,
            gid: cred.gid,
        })
    }
    #[cfg(target_os = "macos")]
    {
        let mut pid: libc::pid_t = 0;
        let mut size = std::mem::size_of::<libc::pid_t>() as libc::socklen_t;
        if unsafe {
            libc::getsockopt(
                stream.as_raw_fd(),
                libc::SOL_LOCAL,
                libc::LOCAL_PEERPID,
                (&mut pid as *mut libc::pid_t).cast(),
                &mut size,
            )
        } != 0
            || size as usize != std::mem::size_of::<libc::pid_t>()
            || pid <= 0
        {
            return Err("authority_peer_query_failed");
        }
        let mut uid = 0;
        let mut gid = 0;
        if unsafe { libc::getpeereid(stream.as_raw_fd(), &mut uid, &mut gid) } != 0 {
            return Err("authority_peer_query_failed");
        }
        Ok(PeerCredentials {
            pid: pid as u32,
            uid,
            gid,
        })
    }
}

/// Cannot be deserialized or created from locator fields. Its borrow ties the
/// kernel connection to the exact child and original held object.
pub struct AuthenticatedPeer<'owner> {
    owner: &'owner OwnedPeer,
    credentials: PeerCredentials,
}
impl AuthenticatedPeer<'_> {
    fn assert_current(&self, stream: &UnixStream) -> Result<(), Fault> {
        if actual_peer(stream)? != self.credentials {
            return Err("authority_peer_changed");
        }
        self.owner.record().reference.assert_live()?;
        Ok(())
    }
    pub fn observe_original(&self) -> Result<HeldFileObservation<'_>, Fault> {
        self.owner.guard().observe_all()
    }
}

pub fn authenticate_actual_peer<'owner>(
    stream: &UnixStream,
    owned_launch: &'owner OwnedPeer,
) -> Result<AuthenticatedPeer<'owner>, Fault> {
    let credentials = actual_peer(stream)?;
    let expected = owned_launch.identity();
    if credentials.pid != expected.pid
        || credentials.uid != expected.uid
        || credentials.gid != expected.gid
        || expected.parent_pid != std::process::id()
    {
        return Err("authority_peer_identity_invalid");
    }
    owned_launch.record().reference.assert_live()?;
    if posix_identity::query_identity(credentials.pid)? != *expected {
        return Err("authority_peer_identity_changed");
    }
    Ok(AuthenticatedPeer {
        owner: owned_launch,
        credentials,
    })
}

fn fresh_id() -> Result<String, Fault> {
    let mut value = [0u8; 16];
    getrandom::fill(&mut value).map_err(|_| "authority_random_failed")?;
    Ok(value.iter().map(|b| format!("{b:02x}")).collect())
}
fn deadline_check(deadline: Instant) -> Result<(), Fault> {
    if Instant::now() >= deadline {
        Err("authority_deadline")
    } else {
        Ok(())
    }
}
fn ready(stream: &UnixStream, writing: bool, deadline: Instant) -> Result<(), Fault> {
    loop {
        deadline_check(deadline)?;
        let left = deadline.saturating_duration_since(Instant::now());
        let milliseconds = left.as_millis().min(i32::MAX as u128) as i32;
        let mut event = libc::pollfd {
            fd: stream.as_raw_fd(),
            events: if writing { libc::POLLOUT } else { libc::POLLIN },
            revents: 0,
        };
        let count = unsafe { libc::poll(&mut event, 1, milliseconds.max(1)) };
        deadline_check(deadline)?;
        if count < 0 {
            if std::io::Error::last_os_error().kind() == std::io::ErrorKind::Interrupted {
                continue;
            }
            return Err("authority_poll_failed");
        }
        if event.revents & (libc::POLLERR | libc::POLLNVAL) != 0 {
            return Err("authority_io_failed");
        }
        if count > 0 {
            return Ok(());
        }
    }
}
fn bytes(
    stream: &mut UnixStream,
    data: &mut [u8],
    writing: bool,
    deadline: Instant,
) -> Result<(), Fault> {
    let mut offset = 0;
    while offset < data.len() {
        ready(stream, writing, deadline)?;
        let end = (offset + 65_536).min(data.len());
        let outcome = if writing {
            stream.write(&data[offset..end])
        } else {
            stream.read(&mut data[offset..end])
        };
        deadline_check(deadline)?;
        match outcome {
            Ok(0) => return Err("authority_io_eof"),
            Ok(count) => offset += count,
            Err(error)
                if matches!(
                    error.kind(),
                    std::io::ErrorKind::WouldBlock | std::io::ErrorKind::Interrupted
                ) =>
            {
                continue;
            }
            Err(_) => return Err("authority_io_failed"),
        }
    }
    deadline_check(deadline)
}
fn receive(stream: &mut UnixStream, deadline: Instant) -> Result<Vec<u8>, Fault> {
    let mut prefix = [0; 4];
    bytes(stream, &mut prefix, false, deadline)?;
    let size = u32::from_le_bytes(prefix) as usize;
    if size == 0 || size > MAX_FRAME {
        return Err("authority_frame_size");
    }
    let mut body = vec![0; size];
    bytes(stream, &mut body, false, deadline)?;
    Ok(body)
}
fn send(stream: &mut UnixStream, reply: &Reply, deadline: Instant) -> Result<(), Fault> {
    let mut body = serde_json::to_vec(reply).map_err(|_| "authority_frame_invalid")?;
    deadline_check(deadline)?;
    if body.is_empty() || body.len() > MAX_FRAME {
        return Err("authority_frame_size");
    }
    let mut prefix = (body.len() as u32).to_le_bytes();
    bytes(stream, &mut prefix, true, deadline)?;
    bytes(stream, &mut body, true, deadline)
}

#[derive(Deserialize)]
#[serde(tag = "method", deny_unknown_fields)]
enum Request {
    #[serde(rename = "bind")]
    Bind {
        wire: String,
        session: String,
        seq: u64,
        instance_id: String,
        role: String,
    },
    #[serde(rename = "observe")]
    Observe {
        wire: String,
        session: String,
        seq: u64,
    },
    #[serde(rename = "assert_current")]
    Assert {
        wire: String,
        session: String,
        seq: u64,
        observation_id: String,
    },
}
#[derive(Serialize)]
pub struct Reply {
    pub wire: &'static str,
    pub session: String,
    pub seq: u64,
    pub status: u16,
    pub code: String,
    pub observation_id: Option<String>,
    pub observed_at_us: Option<u64>,
    pub files: Vec<PinnedFile>,
    pub qualification: &'static str,
    pub registration_sha256: String,
    pub resource_manifest_sha256: String,
    pub runtime_manifest_sha256: String,
}

pub struct PendingAuthority {
    listener: UnixListener,
    directory: File,
    parent: File,
    parent_path: PathBuf,
    directory_path: PathBuf,
    socket_inode: u64,
    socket_device: u64,
    locator: ChildLocator,
    context: FactsContext,
}
impl PendingAuthority {
    /// caller_directory is a unique trusted host input, never request/renderer
    /// input. No existing directory/socket is overwritten or removed here.
    pub fn create_facts_only(
        caller_directory: &Path,
        context: FactsContext,
    ) -> Result<Self, Fault> {
        context.validate()?;
        let parent_path = caller_directory
            .parent()
            .ok_or("authority_directory_invalid")?
            .to_owned();
        let parent = posix_identity::open_physical(&parent_path, true)?;
        let metadata = parent
            .metadata()
            .map_err(|_| "authority_directory_stat_failed")?;
        let uid = unsafe { libc::geteuid() };
        if metadata.uid() != uid || metadata.mode() & 0o077 != 0 {
            return Err("authority_parent_permissions_invalid");
        }
        std::fs::DirBuilder::new()
            .mode(0o700)
            .create(caller_directory)
            .map_err(|_| "authority_directory_create_failed")?;
        posix_identity::assert_named_file(&parent, &parent_path, true)?;
        let directory = posix_identity::open_physical(caller_directory, true)?;
        let metadata = directory
            .metadata()
            .map_err(|_| "authority_directory_stat_failed")?;
        if metadata.uid() != uid || metadata.mode() & 0o077 != 0 {
            return Err("authority_directory_permissions_invalid");
        }
        let socket = caller_directory.join("authority.sock");
        let listener = UnixListener::bind(&socket).map_err(|_| "authority_socket_create_failed")?;
        std::fs::set_permissions(&socket, std::fs::Permissions::from_mode(0o600))
            .map_err(|_| "authority_socket_permissions_failed")?;
        let socket_metadata =
            std::fs::symlink_metadata(&socket).map_err(|_| "authority_socket_stat_failed")?;
        if !socket_metadata.file_type().is_socket()
            || socket_metadata.uid() != uid
            || socket_metadata.mode() & 0o077 != 0
        {
            return Err("authority_socket_permissions_invalid");
        }
        listener
            .set_nonblocking(true)
            .map_err(|_| "authority_socket_nonblocking_failed")?;
        let locator = ChildLocator {
            transport: TRANSPORT,
            socket,
            session: fresh_id()?,
            instance_id: context.instance_id.clone(),
            role: context.role.clone(),
            server: posix_identity::query_identity(std::process::id())?,
        };
        Ok(Self {
            listener,
            parent,
            parent_path,
            directory,
            directory_path: caller_directory.to_owned(),
            socket_inode: socket_metadata.ino(),
            socket_device: socket_metadata.dev(),
            locator,
            context,
        })
    }
    pub fn locator(&self) -> &ChildLocator {
        &self.locator
    }
    fn assert_endpoint(&self) -> Result<(), Fault> {
        posix_identity::assert_named_file(&self.parent, &self.parent_path, true)?;
        posix_identity::assert_named_file(&self.directory, &self.directory_path, true)?;
        let socket = std::fs::symlink_metadata(&self.locator.socket)
            .map_err(|_| "authority_socket_stat_failed")?;
        if socket.dev() != self.socket_device
            || socket.ino() != self.socket_inode
            || !socket.file_type().is_socket()
            || socket.uid() != unsafe { libc::geteuid() }
            || socket.mode() & 0o077 != 0
        {
            return Err("authority_socket_identity_changed");
        }
        Ok(())
    }
    pub fn serve_original(&self, owned_launch: &OwnedPeer) -> Result<(), Fault> {
        let start = Instant::now() + LAUNCH_DEADLINE;
        // Registration already exists, independent of API ready. The child
        // itself opens this pathname; no inherited socketpair peer is trusted.
        let (mut stream, authenticated) = loop {
            deadline_check(start)?;
            self.assert_endpoint()?;
            match self.listener.accept() {
                Ok((stream, _)) => {
                    stream
                        .set_nonblocking(true)
                        .map_err(|_| "authority_socket_nonblocking_failed")?;
                    if let Ok(authenticated) = authenticate_actual_peer(&stream, owned_launch) {
                        break (stream, authenticated);
                    }
                }
                Err(error) if error.kind() == std::io::ErrorKind::WouldBlock => {
                    std::thread::sleep(Duration::from_millis(5))
                }
                Err(error) if error.kind() == std::io::ErrorKind::Interrupted => continue,
                Err(_) => return Err("authority_accept_failed"),
            }
        };
        let mut sequence = 0u64;
        let mut bound = false;
        // Stable borrowed originals, never deserialize/reopen/clone an issuer.
        let mut observations = BTreeMap::<String, HeldFileObservation<'_>>::new();
        loop {
            authenticated.assert_current(&stream)?;
            self.assert_endpoint()?;
            let frame_deadline = if bound {
                Instant::now() + CALL_DEADLINE
            } else {
                (Instant::now() + CALL_DEADLINE).min(start)
            };
            let request: Request = serde_json::from_slice(&receive(&mut stream, frame_deadline)?)
                .map_err(|_| "authority_request_invalid")?;
            let (wire, session, seq) = match &request {
                Request::Bind {
                    wire, session, seq, ..
                }
                | Request::Observe { wire, session, seq }
                | Request::Assert {
                    wire, session, seq, ..
                } => (wire, session, *seq),
            };
            if wire != WIRE || session != &self.locator.session || seq != sequence {
                return Err("authority_sequence_invalid");
            }
            sequence = sequence
                .checked_add(1)
                .ok_or("authority_sequence_exhausted")?;
            let mut reply = Reply {
                wire: WIRE,
                session: session.clone(),
                seq,
                status: 200,
                code: String::new(),
                observation_id: None,
                observed_at_us: None,
                files: Vec::new(),
                qualification: "not_ready",
                registration_sha256: self.context.registration_sha256.clone(),
                resource_manifest_sha256: self.context.resource_manifest_sha256.clone(),
                runtime_manifest_sha256: self.context.runtime_manifest_sha256.clone(),
            };
            match request {
                Request::Bind {
                    instance_id, role, ..
                } => {
                    if bound
                        || seq != 0
                        || instance_id != self.context.instance_id
                        || role != self.context.role
                    {
                        return Err("authority_bind_invalid");
                    }
                    bound = true;
                    reply.code = "bound_facts_only".into();
                }
                Request::Observe { .. } => {
                    if !bound {
                        return Err("authority_bind_required");
                    }
                    if observations.len() >= 64 {
                        return Err("authority_observation_limit");
                    }
                    let observed = authenticated.observe_original()?;
                    let id = fresh_id()?;
                    reply.observation_id = Some(id.clone());
                    reply.observed_at_us = Some(observed.observed_at_us());
                    reply.files = observed.files().to_vec();
                    reply.code = "observed_facts_only".into();
                    observations.insert(id, observed);
                }
                Request::Assert { observation_id, .. } => {
                    if !bound {
                        return Err("authority_bind_required");
                    }
                    if let Some(observed) = observations.get(&observation_id) {
                        owned_launch.guard().assert_current(observed)?;
                        reply.code = "current_facts_only".into();
                    } else {
                        reply.status = 409;
                        reply.code = "observation_unknown_or_foreign".into();
                    }
                }
            }
            authenticated.assert_current(&stream)?;
            self.assert_endpoint()?;
            let reply_deadline = if seq == 0 {
                (Instant::now() + CALL_DEADLINE).min(start)
            } else {
                Instant::now() + CALL_DEADLINE
            };
            send(&mut stream, &reply, reply_deadline)?;
        }
    }
}
