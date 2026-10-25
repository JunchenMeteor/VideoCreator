//! Strict marker consumer used by the T22 owned Rust driver.
//! A marker is a channel/role observation, never proof of natural process exit.
use serde::{de::{MapAccess, SeqAccess, Visitor}, Deserialize, Deserializer};
use serde_json::{Map, Number, Value};
use std::fmt;

#[derive(Clone, Copy)]
pub enum StreamChannel { Stdout, Stderr }

#[derive(Clone, Copy)]
pub enum StopRole { Api, Worker { pid: u32, created_filetime: u64 }, Mcp }

struct StrictValue(Value);
impl<'de> Deserialize<'de> for StrictValue {
    fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        struct StrictVisitor;
        impl<'de> Visitor<'de> for StrictVisitor {
            type Value = StrictValue;
            fn expecting(&self, formatter: &mut fmt::Formatter) -> fmt::Result { formatter.write_str("strict JSON") }
            fn visit_bool<E: serde::de::Error>(self, value: bool) -> Result<Self::Value, E> { Ok(StrictValue(Value::Bool(value))) }
            fn visit_i64<E: serde::de::Error>(self, value: i64) -> Result<Self::Value, E> { Ok(StrictValue(Value::Number(Number::from(value)))) }
            fn visit_u64<E: serde::de::Error>(self, value: u64) -> Result<Self::Value, E> { Ok(StrictValue(Value::Number(Number::from(value)))) }
            fn visit_f64<E: serde::de::Error>(self, value: f64) -> Result<Self::Value, E> {
                Number::from_f64(value).map(|n| StrictValue(Value::Number(n))).ok_or_else(|| E::custom("nonfinite JSON"))
            }
            fn visit_str<E: serde::de::Error>(self, value: &str) -> Result<Self::Value, E> { Ok(StrictValue(Value::String(value.into()))) }
            fn visit_string<E: serde::de::Error>(self, value: String) -> Result<Self::Value, E> { Ok(StrictValue(Value::String(value))) }
            fn visit_unit<E: serde::de::Error>(self) -> Result<Self::Value, E> { Ok(StrictValue(Value::Null)) }
            fn visit_seq<A: SeqAccess<'de>>(self, mut access: A) -> Result<Self::Value, A::Error> {
                let mut values = Vec::new();
                while let Some(value) = access.next_element::<StrictValue>()? { values.push(value.0); }
                Ok(StrictValue(Value::Array(values)))
            }
            fn visit_map<A: MapAccess<'de>>(self, mut access: A) -> Result<Self::Value, A::Error> {
                let mut values = Map::new();
                while let Some(key) = access.next_key::<String>()? {
                    if values.contains_key(&key) { return Err(serde::de::Error::custom("duplicate marker field")); }
                    values.insert(key, access.next_value::<StrictValue>()?.0);
                }
                Ok(StrictValue(Value::Object(values)))
            }
        }
        deserializer.deserialize_any(StrictVisitor)
    }
}

fn keys(value: &Map<String, Value>, names: &[&str]) -> bool {
    value.len() == names.len() && names.iter().all(|name| value.contains_key(*name))
}

pub fn accepted_stop_marker(channel: StreamChannel, role: StopRole, raw: &[u8]) -> bool {
    if !matches!(channel, StreamChannel::Stderr) || raw.len() > 65_536 || !raw.ends_with(b"\n") || raw.contains(&b'\r') { return false; }
    let Ok(StrictValue(Value::Object(value))) = serde_json::from_slice::<StrictValue>(raw) else { return false; };
    let text = |name| value.get(name).and_then(Value::as_str);
    match role {
        StopRole::Api => keys(&value, &["event", "scope"]) && text("event") == Some("api_stopped") && text("scope") == Some("api"),
        StopRole::Worker { pid, created_filetime } => {
            let identity = value.get("process_creation").and_then(Value::as_object);
            keys(&value, &["event", "scope", "pid", "process_creation", "cleanup_completed", "process_exit_pending"])
                && text("event") == Some("worker_stopped") && text("scope") == Some("worker")
                && value.get("pid").and_then(Value::as_u64) == Some(u64::from(pid))
                && value.get("cleanup_completed") == Some(&Value::Bool(true))
                && value.get("process_exit_pending") == Some(&Value::Bool(true))
                && identity.is_some_and(|id| keys(id, &["kind", "value"])
                    && id.get("kind").and_then(Value::as_str) == Some("windows-filetime-100ns")
                    && id.get("value").and_then(Value::as_str) == Some(created_filetime.to_string().as_str()))
        }
        StopRole::Mcp => keys(&value, &["event", "scope", "cleanup_completed", "process_exit_pending", "worker_cancelled"])
            && text("event") == Some("mcp_stopped") && text("scope") == Some("mcp")
            && value.get("cleanup_completed") == Some(&Value::Bool(true))
            && value.get("process_exit_pending") == Some(&Value::Bool(true))
            && value.get("worker_cancelled") == Some(&Value::Bool(false)),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    const API: &[u8] = b"{\"event\":\"api_stopped\",\"scope\":\"api\"}\n";
    const WORKER: &[u8] = b"{\"event\":\"worker_stopped\",\"scope\":\"worker\",\"pid\":4242,\"process_creation\":{\"kind\":\"windows-filetime-100ns\",\"value\":\"233\"},\"cleanup_completed\":true,\"process_exit_pending\":true}\n";
    const MCP: &[u8] = b"{\"event\":\"mcp_stopped\",\"scope\":\"mcp\",\"cleanup_completed\":true,\"process_exit_pending\":true,\"worker_cancelled\":false}\n";
    fn worker() -> StopRole { StopRole::Worker { pid: 4242, created_filetime: 233 } }
    #[test] fn only_stderr_accepts_actual_three_roles() {
        for (role, raw) in [(StopRole::Api, API), (worker(), WORKER), (StopRole::Mcp, MCP)] {
            assert!(accepted_stop_marker(StreamChannel::Stderr, role, raw));
            assert!(!accepted_stop_marker(StreamChannel::Stdout, role, raw));
        }
    }
    #[test] fn missing_wrong_scope_and_nested_are_rejected() {
        for raw in [b"{}\n".as_slice(), b"{\"event\":\"api_stopped\",\"scope\":\"worker\"}\n".as_slice(),
            b"{\"data\":{\"event\":\"api_stopped\",\"scope\":\"api\"}}\n".as_slice()] {
            assert!(!accepted_stop_marker(StreamChannel::Stderr, StopRole::Api, raw));
        }
    }
    #[test] fn mixed_messages_duplicates_and_extra_claims_are_rejected() {
        for raw in [b"INFO {\"event\":\"api_stopped\",\"scope\":\"api\"}\n".as_slice(),
            b"{\"event\":\"other\",\"event\":\"api_stopped\",\"scope\":\"api\"}\n".as_slice(),
            b"{\"event\":\"api_stopped\",\"scope\":\"api\",\"exit\":0}\n".as_slice(),
            b"{\"event\":\"api_stopped\",\"scope\":\"api\"}\n{}\n".as_slice()] {
            assert!(!accepted_stop_marker(StreamChannel::Stderr, StopRole::Api, raw));
        }
    }
    #[test] fn worker_creation_and_cleanup_are_bound() {
        assert!(!accepted_stop_marker(StreamChannel::Stderr, StopRole::Worker { pid: 4243, created_filetime: 233 }, WORKER));
        assert!(!accepted_stop_marker(StreamChannel::Stderr, StopRole::Worker { pid: 4242, created_filetime: 234 }, WORKER));
        let changed = String::from_utf8(WORKER.to_vec()).unwrap().replace("\"cleanup_completed\":true", "\"cleanup_completed\":false");
        assert!(!accepted_stop_marker(StreamChannel::Stderr, worker(), changed.as_bytes()));
    }
    #[test] fn cross_role_no_LF_and_CRLF_are_rejected() {
        assert!(!accepted_stop_marker(StreamChannel::Stderr, worker(), API));
        assert!(!accepted_stop_marker(StreamChannel::Stderr, StopRole::Mcp, WORKER));
        assert!(!accepted_stop_marker(StreamChannel::Stderr, StopRole::Api, &API[..API.len() - 1]));
        assert!(!accepted_stop_marker(StreamChannel::Stderr, StopRole::Api, b"{\"event\":\"api_stopped\",\"scope\":\"api\"}\r\n"));
    }
}
