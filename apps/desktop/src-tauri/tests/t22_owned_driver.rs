//! New Test-only version. T21 original driver and its fixed evidence are intact.
//! Native execution needs independent admission; current stage is source only.
#[path = "t22_stop_markers.rs"]
mod stop_markers;

#[cfg(windows)]
pub mod owned_shutdown {
    use super::stop_markers::{accepted_stop_marker, StopRole, StreamChannel};
    use std::{ffi::OsString, fs::File, io::{BufRead, BufReader, Read, Write}, thread, time::{Duration, Instant}};
    use video_creator_desktop::{platform, resource_pins::ResourcePins, supervisor::{NativeSupervisor, OwnedIdentity}};

    pub struct StopObservation {
        pub identity: OwnedIdentity, pub actual_exit: Option<u32>, pub forced: bool,
        pub stderr_marker_seen: bool, pub api_port_closed: Option<bool>, pub job_empty: bool,
        pub sibling_identities: Vec<(u32, u64)>,
    }

    fn capture(pipe: File, mut raw: File, channel: StreamChannel, role: StopRole)
        -> thread::JoinHandle<Result<bool, &'static str>> {
        thread::spawn(move || {
            let mut input = BufReader::new(pipe);
            let mut marker_seen = false;
            loop {
                let mut bytes = Vec::new();
                let count = input.by_ref().take(4_194_305).read_until(b'\n', &mut bytes).map_err(|_| "test_pipe_read_failed")?;
                if count == 0 { break; }
                raw.write_all(&bytes).map_err(|_| "test_raw_write_failed")?;
                raw.flush().map_err(|_| "test_raw_write_failed")?;
                if count > 4_194_304 || !bytes.ends_with(b"\n") { return Err("test_frame_invalid"); }
                // stdout is preserved as data/RPC output; it never grants a
                // lifecycle marker. stderr role/identity parser is strict.
                marker_seen |= accepted_stop_marker(channel, role, &bytes);
            }
            raw.sync_all().map_err(|_| "test_raw_write_failed")?;
            Ok(marker_seen)
        })
    }

    pub fn run_role_shutdown(pins: ResourcePins, executable: &str, args: &[String],
        environment: &[(OsString, OsString)], siblings: &[NativeSupervisor], stdout_raw: File, stderr_raw: File,
        role_name: &str, api_port: Option<u16>, ready: impl FnOnce(&mut NativeSupervisor) -> Result<(), &'static str>)
        -> Result<StopObservation, &'static str> {
        if siblings.is_empty() || siblings.iter().any(|s| !s.alive()) { return Err("test_live_sibling_required"); }
        let before: Vec<_> = siblings.iter().map(|s| (s.identity().root_pid, s.identity().created_filetime)).collect();
        let mut process = NativeSupervisor::launch(pins, executable, args, environment)?;
        let identity = process.identity();
        let role = match role_name {
            "api" if api_port.is_some_and(|port| port != 0) => StopRole::Api,
            "worker" if api_port.is_none() => StopRole::Worker { pid: identity.root_pid, created_filetime: identity.created_filetime },
            "mcp" if api_port.is_none() => StopRole::Mcp,
            _ => return Err("test_role_port_binding_invalid"),
        };
        let (stdout, stderr) = process.take_output()?;
        let output = capture(stdout, stdout_raw, StreamChannel::Stdout, role);
        let errors = capture(stderr, stderr_raw, StreamChannel::Stderr, role);
        ready(&mut process)?;
        if !process.alive() { return Err("test_actual_ready_required"); }
        if let Some(port) = api_port { if !process.owns_listener(port)? { return Err("test_actual_ready_listener_required"); } }
        if matches!(role, StopRole::Mcp) { process.close_stdin(); } else { process.send_shutdown()?; }
        let mut exit = process.wait_exit(15_000)?;
        let mut forced = false;
        if exit.is_none() { forced = true; exit = process.force_owned()?; }
        let deadline = Instant::now() + Duration::from_secs(5);
        while !process.owned_pids()?.is_empty() && Instant::now() < deadline { thread::sleep(Duration::from_millis(25)); }
        let job_empty = process.owned_pids()?.is_empty();
        let api_port_closed = api_port.map(platform::port_closed);
        let stdout_marker = output.join().map_err(|_| "test_stdout_reader_panicked")??;
        let stderr_marker_seen = errors.join().map_err(|_| "test_stderr_reader_panicked")??;
        if stdout_marker { return Err("test_stdout_cannot_authorize_stop"); }
        for (sibling, (pid, creation)) in siblings.iter().zip(&before) {
            if !sibling.alive() || sibling.identity().root_pid != *pid || sibling.identity().created_filetime != *creation { return Err("test_sibling_changed"); }
        }
        Ok(StopObservation { identity, actual_exit: exit, forced, stderr_marker_seen, api_port_closed, job_empty, sibling_identities: before })
    }
}
