//! Loopback workbench host: serves the installed Workbench directory and
//! proxies `/api/*` to the owned engine with the session bearer. The renderer
//! therefore runs on a trusted loopback origin and never sees the token, which
//! is what the shipped workbench actually requires.
#![cfg(windows)]

use std::{io::{Read, Write}, net::{TcpListener, TcpStream}, path::{Path, PathBuf}, sync::{Arc, atomic::{AtomicBool, Ordering}}, thread, time::Duration};

const MAX_HEADER: usize = 64 * 1024;
const MAX_BODY: usize = 512 * 1024 * 1024;
const HOP: [&str; 8] = ["connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers", "transfer-encoding", "upgrade"];

fn content_type(path: &Path) -> &'static str {
    match path.extension().and_then(|value| value.to_str()).unwrap_or("").to_ascii_lowercase().as_str() {
        "html" => "text/html; charset=utf-8", "js" | "mjs" => "text/javascript; charset=utf-8",
        "css" => "text/css; charset=utf-8", "json" => "application/json", "svg" => "image/svg+xml",
        "png" => "image/png", "jpg" | "jpeg" => "image/jpeg", "ico" => "image/x-icon",
        "woff" => "font/woff", "woff2" => "font/woff2", "map" => "application/json",
        _ => "application/octet-stream",
    }
}

struct Request { method: String, path: String, headers: Vec<(String, String)>, body: Vec<u8> }

fn read_request(stream: &mut TcpStream) -> Result<Option<Request>, &'static str> {
    let mut buffer = Vec::new();
    let mut chunk = [0u8; 8192];
    let header_end = loop {
        if let Some(position) = buffer.windows(4).position(|window| window == b"\r\n\r\n") { break position + 4; }
        if buffer.len() > MAX_HEADER { return Err("host_header_too_large"); }
        let count = stream.read(&mut chunk).map_err(|_| "host_read_failed")?;
        if count == 0 { return Ok(None); }
        buffer.extend_from_slice(&chunk[..count]);
    };
    let head = String::from_utf8_lossy(&buffer[..header_end]).into_owned();
    let mut lines = head.split("\r\n");
    let mut request_line = lines.next().ok_or("host_request_invalid")?.split_whitespace();
    let method = request_line.next().ok_or("host_request_invalid")?.to_ascii_uppercase();
    let path = request_line.next().ok_or("host_request_invalid")?.to_owned();
    if !path.starts_with('/') { return Err("host_request_invalid"); }
    let mut headers = Vec::new();
    for line in lines {
        if line.is_empty() { continue; }
        let (name, value) = line.split_once(':').ok_or("host_request_invalid")?;
        headers.push((name.trim().to_ascii_lowercase(), value.trim().to_owned()));
    }
    let length = headers.iter().find(|(name, _)| name == "content-length").and_then(|(_, value)| value.parse::<usize>().ok()).unwrap_or(0);
    if length > MAX_BODY { return Err("host_body_too_large"); }
    let mut body = buffer[header_end..].to_vec();
    while body.len() < length {
        let count = stream.read(&mut chunk).map_err(|_| "host_read_failed")?;
        if count == 0 { break; }
        body.extend_from_slice(&chunk[..count]);
    }
    Ok(Some(Request { method, path, headers, body }))
}

fn write_response(stream: &mut TcpStream, status: u16, content_type: &str, body: &[u8]) -> std::io::Result<()> {
    let reason = match status { 200 => "OK", 204 => "No Content", 403 => "Forbidden", 404 => "Not Found", 405 => "Method Not Allowed", 500 => "Internal Server Error", 502 => "Bad Gateway", _ => "OK" };
    let head = format!("HTTP/1.1 {status} {reason}\r\nContent-Type: {content_type}\r\nContent-Length: {}\r\nCache-Control: no-store\r\nConnection: close\r\n\r\n", body.len());
    stream.write_all(head.as_bytes())?;
    stream.write_all(body)?;
    stream.flush()
}

fn write_proxy_response(stream: &mut TcpStream, status: u16, headers: &[(String, String)], body: &[u8]) -> std::io::Result<()> {
    let reason = match status { 200 => "OK", 201 => "Created", 202 => "Accepted", 204 => "No Content", 304 => "Not Modified", 400 => "Bad Request", 401 => "Unauthorized", 403 => "Forbidden", 404 => "Not Found", 409 => "Conflict", 422 => "Unprocessable Entity", 500 => "Internal Server Error", 503 => "Service Unavailable", _ => "OK" };
    let mut head = format!("HTTP/1.1 {status} {reason}\r\nContent-Length: {}\r\nCache-Control: no-store\r\nConnection: close\r\n", body.len());
    for (name, value) in headers {
        if HOP.contains(&name.as_str()) || name == "content-length" { continue; }
        if name.contains('\r') || name.contains('\n') || value.contains('\r') || value.contains('\n') { continue; }
        head.push_str(&format!("{name}: {value}\r\n"));
    }
    head.push_str("\r\n");
    stream.write_all(head.as_bytes())?;
    stream.write_all(body)?;
    stream.flush()
}

fn forward(client: &reqwest::Client, base: &str, token: &str, request: &Request) -> Result<(u16, Vec<(String, String)>, Vec<u8>), &'static str> {
    let method = reqwest::Method::from_bytes(request.method.as_bytes()).map_err(|_| "host_method_invalid")?;
    let url = format!("{base}{}", request.path);
    let body = if request.body.is_empty() { None } else { Some(request.body.clone()) };
    let mut builder = client.request(method, &url).header("Authorization", format!("Bearer {token}")).header("Origin", "http://tauri.localhost").header("Accept-Encoding", "identity");
    for (name, value) in &request.headers {
        if HOP.contains(&name.as_str()) || matches!(name.as_str(), "host" | "authorization" | "origin" | "content-length" | "accept-encoding") { continue; }
        builder = builder.header(name, value);
    }
    if let Some(body) = body { builder = builder.body(body); }
    let response = tauri::async_runtime::block_on(builder.send()).map_err(|_| "host_proxy_unavailable")?;
    let status = response.status().as_u16();
    let headers = response.headers().iter().map(|(name, value)| (name.as_str().to_ascii_lowercase(), String::from_utf8_lossy(value.as_bytes()).into_owned())).collect::<Vec<_>>();
    let body = tauri::async_runtime::block_on(response.bytes()).map_err(|_| "host_proxy_unavailable")?.to_vec();
    Ok((status, headers, body))
}

fn serve_static(root: &Path, request: &Request) -> (u16, String, Vec<u8>) {
    if request.method != "GET" { return (405, "text/plain; charset=utf-8".into(), b"Method Not Allowed".to_vec()); }
    let raw = request.path.split(['?', '#']).next().unwrap_or("/");
    let relative = raw.trim_start_matches('/');
    let candidate = if relative.is_empty() { root.join("index.html") } else { root.join(relative) };
    let resolved = match candidate.canonicalize() { Ok(path) => path, Err(_) => root.join("index.html") };
    let resolved = if resolved.is_file() && resolved.starts_with(root) { resolved } else { root.join("index.html") };
    match std::fs::read(&resolved) { Ok(bytes) => (200, content_type(&resolved).to_owned(), bytes), Err(_) => (404, "text/plain; charset=utf-8".into(), b"Not Found".to_vec()) }
}

pub struct WorkbenchHost {
    pub origin: String,
    pub port: u16,
    stop: Arc<AtomicBool>,
    accept: Option<thread::JoinHandle<()>>,
}

impl WorkbenchHost {
    pub fn start(workbench: PathBuf, engine_base: String, token: String) -> Result<Self, &'static str> {
        let root = workbench.canonicalize().map_err(|_| "launcher_files_missing")?;
        let listener = TcpListener::bind(("127.0.0.1", 0)).map_err(|_| "host_listen_failed")?;
        listener.set_nonblocking(true).map_err(|_| "host_listen_failed")?;
        let port = listener.local_addr().map_err(|_| "host_listen_failed")?.port();
        let stop = Arc::new(AtomicBool::new(false));
        let signal = stop.clone();
        let client = reqwest::Client::builder().no_proxy().redirect(reqwest::redirect::Policy::none()).no_gzip().no_brotli().no_deflate().no_zstd().http1_only().build().map_err(|_| "host_client_unavailable")?;
        let accept = thread::spawn(move || {
            while !signal.load(Ordering::Acquire) {
                match listener.accept() {
                    Ok((mut stream, _)) => {
                        let root = root.clone(); let base = engine_base.clone(); let token = token.clone(); let client = client.clone();
                        thread::spawn(move || {
                            let _ = stream.set_read_timeout(Some(Duration::from_secs(30)));
                            let request = match read_request(&mut stream) { Ok(Some(request)) => request, _ => return };
                            let result = if request.path.starts_with("/api/") {
                                match forward(&client, &base, &token, &request) {
                                    Ok((status, headers, body)) => write_proxy_response(&mut stream, status, &headers, &body),
                                    Err(_) => write_response(&mut stream, 502, "text/plain; charset=utf-8", b"Bad Gateway"),
                                }
                            } else {
                                let (status, content_type, body) = serve_static(&root, &request);
                                write_response(&mut stream, status, &content_type, &body)
                            };
                            let _ = result;
                        });
                    }
                    Err(_) => thread::sleep(Duration::from_millis(25)),
                }
            }
        });
        Ok(Self { origin: format!("http://127.0.0.1:{port}"), port, stop, accept: Some(accept) })
    }

    pub fn stop(&mut self) {
        self.stop.store(true, Ordering::Release);
        if let Some(handle) = self.accept.take() { let _ = handle.join(); }
    }
}

impl Drop for WorkbenchHost {
    fn drop(&mut self) { self.stop(); }
}
