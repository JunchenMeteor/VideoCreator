//! Product installation launcher: the desktop shell takes over the installed
//! launcher's duties. It reads `<InstallDir>/launcher.config.json`, pins the
//! provisioned `Control/InstallationProvisioning.json`, starts the installed
//! `product-serve` and `product-worker`, and keeps the session token in native
//! memory only. No renderer DTO carries the bearer or the base URL.
#![cfg(windows)]

use std::{ffi::OsString, fs, io::{BufRead, BufReader}, path::{Path, PathBuf}, sync::{Arc, Mutex, atomic::{AtomicBool, Ordering}}, thread::JoinHandle, time::{Duration, Instant}};
use serde::Deserialize;
use sha2::{Digest, Sha256};
use crate::{engine::StopReceipt, platform::OwnedProcess, route_contract::Contract, transport::Connection};

const CONFIG: &str = "launcher.config.json";
const PROVISIONING: &str = "Control/InstallationProvisioning.json";
const DEFAULT_ROOT: &str = "D:\\VideoCreator";
const READY_TIMEOUT: Duration = Duration::from_secs(60);

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Config { format: String, engine: String, instance_dir: String, registration: String, ui_port: u16, workbench: String }

#[derive(Clone)]
pub struct Plan { pub root: PathBuf, pub engine: PathBuf, pub instance: PathBuf, pub registration: PathBuf, pub record: PathBuf, pub record_sha: String, pub registration_sha: String, pub workbench: PathBuf }

fn hex(bytes: &[u8]) -> String { bytes.iter().map(|value| format!("{value:02x}")).collect() }

/// Windows canonicalization returns a verbatim `\\?\` path. The installation
/// record keeps ordinary drive-letter paths, so compare and pass those.
fn plain(path: &Path) -> PathBuf {
    let text = path.to_string_lossy();
    if let Some(rest) = text.strip_prefix("\\\\?\\UNC\\") { return PathBuf::from(format!("\\\\{rest}")); }
    if let Some(rest) = text.strip_prefix("\\\\?\\") { return PathBuf::from(rest); }
    path.to_owned()
}

/// Install root precedence: explicit env, then the shell image next to the
/// config, then the documented per-user install location.
fn install_root() -> Result<PathBuf, &'static str> {
    if let Some(value) = std::env::var_os("VIDEO_CREATOR_INSTALL_DIR") {
        let path = PathBuf::from(value);
        if !path.is_absolute() { return Err("launcher_config_missing"); }
        return Ok(path);
    }
    let image = std::env::current_exe().map_err(|_| "launcher_config_missing")?;
    if let Some(directory) = image.parent() {
        if directory.join(CONFIG).is_file() { return Ok(directory.to_owned()); }
    }
    Ok(PathBuf::from(DEFAULT_ROOT))
}

/// True when a product installation is the configured engine source. The
/// indexed native installation path stays untouched when this is false.
pub fn configured() -> bool {
    if std::env::var_os("VIDEO_CREATOR_INSTALL_DIR").is_some() { return true; }
    if Path::new(DEFAULT_ROOT).join(CONFIG).is_file() { return true; }
    std::env::current_exe().ok().and_then(|image| image.parent().map(|directory| directory.join(CONFIG).is_file())).unwrap_or(false)
}

pub fn plan() -> Result<Plan, &'static str> {
    let root = install_root()?;
    let raw = fs::read(root.join(CONFIG)).map_err(|_| "launcher_config_missing")?;
    if raw.len() > 64 * 1024 { return Err("launcher_config_invalid"); }
    let config: Config = serde_json::from_slice(&raw).map_err(|_| "launcher_config_invalid")?;
    if config.format != "video-creator-launcher-config-v1" { return Err("launcher_config_invalid"); }
    let root = plain(&root.canonicalize().map_err(|_| "launcher_config_missing")?);
    let engine = plain(&root.join(&config.engine).canonicalize().map_err(|_| "launcher_files_missing")?);
    let workbench = plain(&root.join(&config.workbench).canonicalize().map_err(|_| "launcher_files_missing")?);
    if !engine.is_file() || !workbench.is_dir() { return Err("launcher_files_missing"); }
    let instance = PathBuf::from(&config.instance_dir);
    if !instance.is_absolute() { return Err("installation_not_provisioned"); }
    let instance = plain(&instance.canonicalize().map_err(|_| "installation_not_provisioned")?);
    let registration = PathBuf::from(&config.registration);
    if !registration.is_absolute() { return Err("installation_registration_missing"); }
    let registration = plain(&registration.canonicalize().map_err(|_| "installation_registration_missing")?);
    let record = instance.join(PROVISIONING);
    if !record.is_file() { return Err("installation_not_provisioned"); }
    let record_raw = fs::read(&record).map_err(|_| "installation_not_provisioned")?;
    if record_raw.len() > 2 * 1024 * 1024 { return Err("installation_provisioning_incomplete"); }
    let value: serde_json::Value = serde_json::from_slice(&record_raw).map_err(|_| "installation_provisioning_incomplete")?;
    let registration_raw = fs::read(&registration).map_err(|_| "installation_registration_missing")?;
    let registration_sha = hex(&Sha256::digest(&registration_raw));
    let instance_text = instance.to_string_lossy().into_owned();
    let root_text = root.to_string_lossy().into_owned();
    if value["format"] != "installation-provisioning-v1" || value["complete"] != true
        || value["registration_sha256"].as_str() != Some(registration_sha.as_str())
        || value["instance_dir"].as_str() != Some(instance_text.as_str())
        || value["install_root"].as_str() != Some(root_text.as_str()) {
        return Err("installation_provisioning_incomplete");
    }
    Ok(Plan { root, engine, instance, registration, record, record_sha: hex(&Sha256::digest(&record_raw)), registration_sha, workbench })
}

fn environment(instance: &Path, token: &str, secret: &str) -> Result<Vec<(OsString, OsString)>, &'static str> {
    let (_, mut environment) = crate::load_policy::trusted_system_environment()?;
    let temp = instance.join("Temp");
    fs::create_dir_all(&temp).map_err(|_| "installation_not_provisioned")?;
    environment.extend([
        ("TEMP".into(), temp.as_os_str().to_owned()), ("TMP".into(), temp.as_os_str().to_owned()),
        ("VIDEO_CREATOR_API_TOKEN".into(), token.into()),
        ("VIDEO_CREATOR_AUTHORIZATION_SESSION_SECRET".into(), secret.into()),
        ("PYTHONUTF8".into(), "1".into()), ("PYTHONIOENCODING".into(), "utf-8".into()),
    ]);
    for name in ["USERPROFILE", "LOCALAPPDATA", "APPDATA", "PROGRAMDATA"] {
        if let Some(value) = std::env::var_os(name) { environment.push((name.into(), value)); }
    }
    Ok(environment)
}

fn serve_arguments(plan: &Plan) -> Result<Vec<String>, &'static str> {
    let text = |path: &Path| path.to_str().map(str::to_owned).ok_or("launcher_files_missing");
    Ok(vec!["product-serve".into(), "--data-dir".into(), text(&plan.instance)?, "--install-root".into(), text(&plan.root)?,
        "--installation-record".into(), text(&plan.record)?, "--installation-record-sha256".into(), plan.record_sha.clone(),
        "--production-config".into(), text(&plan.registration)?, "--production-config-sha256".into(), plan.registration_sha.clone(),
        "--native-origin".into(), "http://tauri.localhost".into()])
}

fn worker_arguments(plan: &Plan) -> Result<Vec<String>, &'static str> {
    let mut arguments = serve_arguments(plan)?;
    arguments[0] = "product-worker".into();
    arguments.extend(["--max-seconds".into(), "600".into()]);
    Ok(arguments)
}

fn drain(mut file: fs::File, label: &'static str) -> JoinHandle<()> {
    std::thread::spawn(move || {
        let mut reader = BufReader::new(&mut file);
        let mut line = Vec::new();
        loop {
            line.clear();
            match reader.read_until(b'\n', &mut line) {
                Ok(0) | Err(_) => break,
                Ok(_) => {
                    if line.len() > 8192 { continue; }
                    let text = String::from_utf8_lossy(&line);
                    eprintln!("{}", serde_json::json!({"event": "product_child_output", "scope": label, "line": text.trim_end()}));
                }
            }
        }
    })
}

fn random_hex(bytes: usize) -> Result<String, &'static str> {
    let mut buffer = vec![0u8; bytes];
    getrandom::fill(&mut buffer).map_err(|_| "native_entropy_unavailable")?;
    Ok(hex(&buffer))
}

struct WorkerSpec { engine: PathBuf, arguments: Vec<String>, root: PathBuf, environment: Vec<(OsString, OsString)> }

fn spawn_worker(spec: &WorkerSpec) -> Result<(OwnedProcess, Vec<JoinHandle<()>>), &'static str> {
    let mut process = OwnedProcess::launch(&spec.engine, &spec.arguments, &spec.root, &spec.environment)?;
    process.close_stdin();
    let (stdout, stderr) = process.take_output()?;
    Ok((process, vec![drain(stdout, "worker"), drain(stderr, "worker")]))
}

pub struct ProductRuntime {
    serve: Arc<Mutex<OwnedProcess>>,
    worker: Arc<Mutex<Option<OwnedProcess>>>,
    stopping: Arc<AtomicBool>,
    pub connection: Arc<Connection>,
    pub port: u16,
    readers: Mutex<Vec<JoinHandle<()>>>,
    supervisor: Mutex<Option<JoinHandle<()>>>,
    pub instance_id: String,
    pub token: String,
}

impl ProductRuntime {
    pub async fn launch() -> Result<Self, &'static str> {
        let plan = plan()?;
        let token = random_hex(32)?;
        let secret = random_hex(16)?;
        let environment = environment(&plan.instance, &token, &secret)?;
        let serve_arguments = serve_arguments(&plan)?;
        let worker_arguments = worker_arguments(&plan)?;
        let serve_plan = plan.clone();
        let serve_environment = environment.clone();
        let (serve, ready, mut readers) = tauri::async_runtime::spawn_blocking(move || -> Result<(OwnedProcess, serde_json::Value, Vec<JoinHandle<()>>), &'static str> {
            let mut process = OwnedProcess::launch(&serve_plan.engine, &serve_arguments, &serve_plan.root, &serve_environment)?;
            let (stdout, stderr) = process.take_output()?;
            let stderr_lines = Arc::new(Mutex::new(Vec::<String>::new()));
            let collected = stderr_lines.clone();
            let stderr_reader = std::thread::spawn(move || {
                let mut reader = BufReader::new(stderr);
                let mut line = Vec::new();
                while let Ok(count) = reader.read_until(b'\n', &mut line) {
                    if count == 0 { break; }
                    if line.len() <= 8192 {
                        if let Ok(mut lines) = collected.lock() { lines.push(String::from_utf8_lossy(&line).trim_end().to_owned()); if lines.len() > 8 { lines.remove(0); } }
                    }
                    line.clear();
                }
            });
            let (sender, receiver) = std::sync::mpsc::sync_channel(4);
            let stdout_reader = std::thread::spawn(move || {
                let mut reader = BufReader::new(stdout);
                let mut line = Vec::new();
                loop {
                    line.clear();
                    match reader.read_until(b'\n', &mut line) {
                        Ok(0) | Err(_) => break,
                        Ok(_) => {
                            if let Ok(value) = serde_json::from_slice::<serde_json::Value>(&line) {
                                if value["event"] == "ready" && value["base_url"].is_string() && value["instance_id"].is_string() {
                                    let _ = sender.try_send(value);
                                }
                            }
                        }
                    }
                }
            });
            match receiver.recv_timeout(READY_TIMEOUT) {
                Ok(value) => Ok((process, value, vec![stdout_reader, stderr_reader])),
                Err(_) => {
                    let code = process.wait_exit(0).ok().flatten();
                    let detail = stderr_lines.lock().ok().and_then(|lines| lines.last().cloned()).unwrap_or_default();
                    eprintln!("{}", serde_json::json!({"event": "product_engine_not_ready", "exit": code, "detail": detail}));
                    let _ = process.force();
                    drop(process);
                    for reader in [stdout_reader] { let _ = reader.join(); }
                    let _ = stderr_reader.join();
                    Err(if code.is_some() { "engine_start_failed" } else { "engine_start_timeout" })
                }
            }
        }).await.map_err(|_| "engine_start_timeout")??;
        let base_url = ready["base_url"].as_str().ok_or("engine_start_failed")?;
        let base = tauri::Url::parse(base_url).map_err(|_| "engine_start_failed")?;
        let instance_id = ready["instance_id"].as_str().ok_or("engine_start_failed")?.to_owned();
        let port = base.port().ok_or("engine_start_failed")?;
        let connection = Arc::new(Connection::verified(base, token.clone(), instance_id.clone())?);
        let contract = Contract::load()?;
        if let Err(code) = connection.verify_health(&contract).await {
            drop(serve);
            return Err(code);
        }
        let spec = WorkerSpec { engine: plan.engine.clone(), arguments: worker_arguments.clone(), root: plan.root.clone(), environment: environment.clone() };
        let (worker_process, worker_readers) = tauri::async_runtime::spawn_blocking(move || spawn_worker(&spec)).await.map_err(|_| "engine_start_failed")??;
        let worker = Arc::new(Mutex::new(Some(worker_process)));
        readers.extend(worker_readers);
        let stopping = Arc::new(AtomicBool::new(false));
        let supervisor = {
            let holder = worker.clone();
            let stopping = stopping.clone();
            let spec = WorkerSpec { engine: plan.engine.clone(), arguments: worker_arguments, root: plan.root.clone(), environment };
            std::thread::spawn(move || {
                loop {
                    std::thread::sleep(Duration::from_millis(500));
                    if stopping.load(Ordering::Acquire) { break; }
                    let mut guard = match holder.lock() { Ok(guard) => guard, Err(poisoned) => poisoned.into_inner() };
                    if guard.as_ref().is_some_and(|process| process.alive()) { continue; }
                    guard.take();
                    match spawn_worker(&spec) {
                        Ok((process, readers)) => {
                            eprintln!("{}", serde_json::json!({"event": "product_worker_restarted", "pid": process.pid}));
                            for reader in readers { let _ = reader.join(); }
                            *guard = Some(process);
                        },
                        Err(code) => { eprintln!("{}", serde_json::json!({"event": "product_worker_unavailable", "code": code})); break; },
                    }
                }
            })
        };
        Ok(Self { serve: Arc::new(Mutex::new(serve)), worker, stopping, connection, port, readers: Mutex::new(readers), supervisor: Mutex::new(Some(supervisor)), instance_id, token })
    }

    pub fn alive(&self) -> bool {
        self.serve.lock().is_ok_and(|process| process.alive())
    }

    pub fn stop(&self) -> StopReceipt {
        self.connection.invalidate();
        self.stopping.store(true, Ordering::Release);
        let mut receipt = StopReceipt { classification: "forced", actual_exit: None, api_marker: false, port_closed: false, owned_tree_empty: false };
        let serve = match self.serve.lock() { Ok(guard) => guard, Err(poisoned) => poisoned.into_inner() };
        receipt.actual_exit = serve.force().ok().flatten();
        if let Ok(mut worker) = self.worker.lock() {
            if let Some(process) = worker.take() { let _ = process.force(); }
        }
        let until = Instant::now() + Duration::from_secs(5);
        loop {
            receipt.port_closed = crate::platform::port_closed(self.port);
            receipt.owned_tree_empty = serve.job_pids().is_ok_and(|pids| pids.is_empty());
            if (receipt.port_closed && receipt.owned_tree_empty) || Instant::now() >= until { break; }
            std::thread::sleep(Duration::from_millis(50));
        }
        if receipt.owned_tree_empty { receipt.classification = "normal"; }
        drop(serve);
        if let Ok(mut supervisor) = self.supervisor.lock() { if let Some(handle) = supervisor.take() { let _ = handle.join(); } }
        if let Ok(mut readers) = self.readers.lock() { for reader in readers.drain(..) { let _ = reader.join(); } }
        receipt
    }
}
