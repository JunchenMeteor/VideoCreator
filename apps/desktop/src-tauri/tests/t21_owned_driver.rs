//! Test-owned consumer of I24's frozen V2 Rust-only ABI. Not run or compiled yet.
//! Input ResourcePins must come from independently admitted complete closure;
//! taking a caller list of files is deliberately not an admission mechanism.
//! Real stdio handles are available; cross-language Test host bridge is pending.
#[cfg(windows)]
pub mod owned_shutdown {
    use std::{ffi::OsString, fs::File, io::{BufRead, BufReader, Read, Write}, thread, time::{Duration, Instant}};
    use video_creator_desktop::{platform, resource_pins::ResourcePins, supervisor::{NativeSupervisor, OwnedIdentity}};

    pub struct ShutdownObservation {
        pub identity: OwnedIdentity,
        pub actual_exit: Option<u32>,
        pub forced: bool,
        pub marker_seen: bool,
        pub port_closed: bool,
        pub job_empty: bool,
        pub sibling_identities: Vec<(u32, u64)>,
    }

    pub struct OwnedStdio { pub input: File, pub output: File, pub errors: File }

    pub fn take_owned_stdio(process: &mut NativeSupervisor) -> Result<OwnedStdio, &'static str> {
        let input = process.take_stdin()?;
        let (output, errors) = process.take_output()?;
        Ok(OwnedStdio { input, output, errors })
    }

    pub fn write_protocol_frame(input: &mut File, frame: &[u8]) -> Result<(), &'static str> {
        // The caller's protocol determines frame validity. Deliberate illegal
        // bytes are delivered unchanged to the actual Backend parser.
        input.write_all(frame).and_then(|_| input.flush()).map_err(|_| "test_owned_stdin_write_failed")
    }

    pub fn actual_eof(input: File) { drop(input); }

    fn capture(pipe: File, mut raw: File, expected_marker: String) -> thread::JoinHandle<Result<bool, &'static str>> {
        thread::spawn(move || {
            let mut input = BufReader::new(pipe);
            let mut found = false;
            loop {
                let mut bytes = Vec::new();
                let count = input.by_ref().take(65_537).read_until(b'\n', &mut bytes).map_err(|_| "test_pipe_read_failed")?;
                if count == 0 { break; }
                raw.write_all(&bytes).map_err(|_| "test_raw_write_failed")?;
                raw.flush().map_err(|_| "test_raw_write_failed")?;
                if count > 65_536 || !bytes.ends_with(b"\n") { return Err("test_frame_invalid"); }
                if let Ok(value) = serde_json::from_slice::<serde_json::Value>(&bytes) {
                    if value.get("event").and_then(|v| v.as_str()) == Some(expected_marker.as_str()) { found = true; }
                }
            }
            raw.sync_all().map_err(|_| "test_raw_write_failed")?;
            Ok(found)
        })
    }

    pub fn run_fixed_shutdown(pins: ResourcePins, executable: &str, args: &[String],
        environment: &[(OsString, OsString)], siblings: &[NativeSupervisor], stdout_raw: File, stderr_raw: File,
        marker_event: String, port: Option<u16>, ready: impl FnOnce(&NativeSupervisor) -> Result<(), &'static str>)
        -> Result<ShutdownObservation, &'static str> {
        if siblings.is_empty() || port == Some(0) { return Err("test_live_sibling_required"); }
        let before: Vec<_> = siblings.iter().map(|s| (s.identity().root_pid, s.identity().created_filetime)).collect();
        if siblings.iter().any(|s| !s.alive()) { return Err("test_live_sibling_required"); }
        let mut process = NativeSupervisor::launch(pins, executable, args, environment)?;
        let identity = process.identity();
        let (stdout, stderr) = process.take_output()?;
        let output = capture(stdout, stdout_raw, marker_event);
        let errors = capture(stderr, stderr_raw, String::new());
        ready(&process)?;
        if !process.alive() { return Err("test_actual_ready_required"); }
        if let Some(value) = port { if !process.owns_listener(value)? { return Err("test_actual_ready_listener_required"); } }
        process.send_shutdown()?;
        let mut exit = process.wait_exit(15_000)?;
        let mut forced = false;
        if exit.is_none() { forced = true; exit = process.force_owned()?; }
        let deadline = Instant::now() + Duration::from_secs(5);
        while !process.owned_pids()?.is_empty() && Instant::now() < deadline { thread::sleep(Duration::from_millis(25)); }
        let job_empty = process.owned_pids()?.is_empty();
        let port_closed = port.is_some_and(platform::port_closed);
        let marker_seen = output.join().map_err(|_| "test_stdout_reader_panicked")??;
        errors.join().map_err(|_| "test_stderr_reader_panicked")??;
        for (sibling, (pid, creation)) in siblings.iter().zip(&before) {
            if !sibling.alive() || sibling.identity().root_pid != *pid || sibling.identity().created_filetime != *creation {
                return Err("test_sibling_changed");
            }
        }
        // ResourcePins/Job remain owned until this function drops process.
        Ok(ShutdownObservation { identity, actual_exit: exit, forced, marker_seen,
            port_closed, job_empty, sibling_identities: before })
    }
}
