//! Read the generated transport mapping. No second domain model or free URL API.
use std::{collections::{BTreeMap, BTreeSet}, sync::Arc};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use reqwest::{Method, Url, header::{HeaderName, HeaderValue, HeaderMap}};

const MANIFEST: &[u8] = include_bytes!("../../../../packages/contracts/NativeRouteManifest.json");
pub struct Contract { pub sha256: String, pub version: String, pub format: String, operations: BTreeMap<String, Arc<Route>> }
pub struct Route { pub operation_id: String, pub method: Method, template: String,
    parameters: Vec<Value>, header_rules: BTreeMap<String, Value>, body: Value,
    pub response_headers: BTreeSet<String>, pub response_kind: String, responses:Value,request_body: Value }
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RequestBody { pub kind: String, pub length: Option<String> }
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OpenRequest {
    pub generation: String, pub client_request_id: String, pub operation_id: String,
    pub path_params: BTreeMap<String, Value>, pub query: BTreeMap<String, Value>,
    pub headers: BTreeMap<String, String>, pub body: RequestBody,
}
#[derive(Serialize, Clone)]
pub struct TransportError { pub code: &'static str, pub phase: &'static str, pub may_have_been_accepted: bool }
impl TransportError { pub fn new(code: &'static str, phase: &'static str, accepted: bool) -> Self { Self { code, phase, may_have_been_accepted: accepted } } }
pub fn random_id() -> Result<String, &'static str> {
    let mut bytes = [0; 32]; getrandom::fill(&mut bytes).map_err(|_| "native_entropy_unavailable")?;
    Ok(bytes.iter().map(|n| format!("{n:02x}")).collect())
}
fn string<'a>(value: &'a Value, name: &str) -> Result<&'a str, &'static str> { value[name].as_str().ok_or("native_contract_invalid") }
fn string_set(value: &Value) -> Result<BTreeSet<String>, &'static str> {
    value.as_array().ok_or("native_contract_invalid")?.iter().map(|v|v.as_str().map(|s|s.to_ascii_lowercase()).ok_or("native_contract_invalid")).collect()
}
fn control(value: &str) -> bool { value.bytes().any(|b| b < 32 || b == 127) }
fn matches(value: &Value, schema: &Value) -> bool {
    if let Some(items) = schema["anyOf"].as_array() { return items.iter().any(|s| matches(value, s)); }
    if schema["enum"].as_array().is_some_and(|values| !values.contains(value)) { return false; }
    let typed = match schema["type"].as_str() {
        Some("string") => value.is_string(), Some("integer") => value.is_i64() || value.is_u64(),
        Some("number") => value.is_number(), Some("boolean") => value.is_boolean(), Some("null") => value.is_null(), None => true, _ => false,
    };
    if !typed { return false; }
    if let Some(text) = value.as_str() {
        let length = text.chars().count() as u64;
        if control(text) || schema["minLength"].as_u64().is_some_and(|n| length < n) || schema["maxLength"].as_u64().is_some_and(|n| length > n) { return false; }
        if let Some(pattern) = schema["pattern"].as_str() { if !regex::Regex::new(pattern).is_ok_and(|r| r.is_match(text)) { return false; } }
    }
    if let Some(n) = value.as_f64() {
        if schema["minimum"].as_f64().is_some_and(|m|n < m) || schema["maximum"].as_f64().is_some_and(|m|n > m) { return false; }
    }
    true
}
impl Contract {
    pub fn load() -> Result<Self, &'static str> {
        let value: Value = serde_json::from_slice(MANIFEST).map_err(|_| "native_contract_invalid")?;
        if string(&value,"format")? != "native-route-manifest-v1-candidate" || string(&value,"transport_format")? != "native-ipc-v1-candidate" ||
            value["engine_transport"]["native_constraints"]["arbitrary_url_method_path"] != false ||
            value["engine_transport"]["native_constraints"]["redirects"] != "reject" ||
            value["engine_transport"]["native_constraints"]["environment_proxy"] != "disabled" { return Err("native_contract_invalid"); }
        let source = value["operations"].as_object().ok_or("native_contract_invalid")?;
        let mut operations = BTreeMap::new();
        for (id, operation) in source {
            let transport = &operation["transport"];
            if operation["operation_id"] != *id || transport["format"] != "engine-http-transport-v1-candidate" || transport["automatic_http_retry"] != false ||
                !["none","json_bytes","raw_bytes"].contains(&string(&transport["body"],"kind")?) { return Err("native_contract_invalid"); }
            let mode = string(&transport["authorization"],"mode")?;
            // Owner-management operations are never renderer reachable: the
            // shell holds no management credential, so they stay unmapped
            // instead of failing the whole manifest.
            if mode == "actual_owner_management" { continue; }
            if !["installation_owner_only","current_principal_registration"].contains(&mode) { return Err("native_contract_invalid"); }
            let security = operation["security"].as_array().ok_or("native_contract_invalid")?;
            if security.is_empty() || security.iter().any(|s| s.as_object().is_none_or(|a| a.is_empty() || a.iter().any(|(name,scopes)| {
                value["security_schemes"][name]["type"] != "http" || value["security_schemes"][name]["scheme"] != "bearer" || scopes.as_array().is_none_or(|v|!v.is_empty())
            }))) { return Err("native_contract_invalid"); }
            let headers = operation["header_rules"].as_object().ok_or("native_contract_invalid")?;
            if string_set(&transport["request_headers"] )?.iter().any(|n| !headers.contains_key(n)) { return Err("native_contract_invalid"); }
            let route = Route { operation_id:id.clone(), method:Method::from_bytes(string(operation,"method")?.as_bytes()).map_err(|_|"native_contract_invalid")?,
                template:string(operation,"path_template")?.to_owned(), parameters:operation["parameters"].as_array().ok_or("native_contract_invalid")?.clone(),
                header_rules:headers.iter().map(|(k,v)|(k.clone(),v.clone())).collect(), body:transport["body"].clone(),
                response_headers:string_set(&transport["response_headers"] )?, response_kind:string(&transport["response"],"kind")?.to_owned(),responses:operation["responses"].clone(), request_body:operation["request_body"].clone() };
            operations.insert(id.clone(), Arc::new(route));
        }
        if value["engine_transport"]["operation_count"].as_u64() != Some(source.len() as u64) { return Err("native_contract_invalid"); }
        Ok(Self { sha256:format!("{:x}",Sha256::digest(MANIFEST)),version:string(&value,"contract_version")?.to_owned(),format:string(&value,"transport_format")?.to_owned(),operations })
    }
    pub fn unique_json_operation(&self,schema:&str)->Result<String,&'static str>{
        let reference=format!("#/components/schemas/{schema}");
        let found=self.operations.values().filter(|route|route.method==Method::GET&&route.response_kind=="json"&&route.responses["200"]["content"]["application/json"]["schema"]["$ref"]==reference).collect::<Vec<_>>();
        if found.len()!=1{return Err("native_metadata_operation_unavailable");}Ok(found[0].operation_id.clone())
    }
    pub fn resolve(&self, input: &OpenRequest, base: &Url) -> Result<(Arc<Route>, Url, HeaderMap, Option<u64>), &'static str> {
        let route = self.operations.get(&input.operation_id).ok_or("native_operation_unknown")?.clone();
        if input.client_request_id.is_empty() || input.client_request_id.len()>128 || control(&input.client_request_id) { return Err("native_request_id_invalid"); }
        let mut url=base.clone();
        if url.scheme()!="http" || url.host_str()!=Some("127.0.0.1") || url.port().is_none() || url.path()!="/" || !url.username().is_empty() || url.password().is_some() || url.query().is_some() || url.fragment().is_some() { return Err("native_target_invalid"); }
        for (kind, values) in [("path",&input.path_params),("query",&input.query)] {
            let declared:Vec<_>=route.parameters.iter().filter(|p|p["in"]==kind).collect();
            for (name,v) in values { let rule=declared.iter().find(|p|p["name"]==*name).ok_or("native_parameter_unknown")?;if !matches(v,&rule["schema"]){return Err("native_parameter_invalid");} }
            if declared.iter().any(|p|p["required"]==true&&!values.contains_key(p["name"].as_str().unwrap_or(""))) { return Err("native_parameter_missing"); }
        }
        {
            let mut segments=url.path_segments_mut().map_err(|_|"native_target_invalid")?;segments.clear();
            for segment in route.template.trim_start_matches('/').split('/') {
                if let Some(name)=segment.strip_prefix('{').and_then(|s|s.strip_suffix('}')) {
                    let text=input.path_params.get(name).and_then(Value::as_str).ok_or("native_parameter_missing")?;
                    if [".",".."].contains(&text)||text.contains('%') {return Err("native_path_invalid");}
                    segments.push(text);
                } else { segments.push(segment); }
            }
        }
        for (name,v) in &input.query { if !v.is_null(){url.query_pairs_mut().append_pair(name,&v.as_str().map(str::to_owned).unwrap_or_else(||v.to_string()));} }
        let mut headers=HeaderMap::new();
        for (original,value) in &input.headers {
            let name=original.to_ascii_lowercase();let rule=route.header_rules.get(&name).ok_or("native_header_unknown")?;
            if ["authorization","host","origin","cookie","proxy-authorization","sec-fetch-site"].contains(&name.as_str()) || headers.contains_key(&name) || control(value) || !matches(&Value::String(value.clone()),&rule["schema"]) {return Err("native_header_invalid");}
            if let Some(pattern)=rule["x-native-value-pattern"].as_str(){if !regex::Regex::new(pattern).is_ok_and(|r|r.is_match(value)){return Err("native_header_invalid");}}
            if let Some(types)=rule["media_types"].as_array(){let mime=value.split(';').next().unwrap_or("").trim().to_ascii_lowercase();if !types.iter().any(|m|m=="*/*"||m.as_str().is_some_and(|m|m.eq_ignore_ascii_case(&mime))){return Err("native_content_type_invalid");}}
            headers.insert(HeaderName::from_bytes(name.as_bytes()).map_err(|_|"native_header_invalid")?,HeaderValue::from_str(value).map_err(|_|"native_header_invalid")?);
        }
        if route.header_rules.iter().any(|(n,r)|r["required"]==true&&!headers.contains_key(n)){return Err("native_header_missing");}
        let length=match input.body.kind.as_str(){"none" if input.body.length.is_none()=>None,"bytes"=>Some(crate::wire::decimal(input.body.length.as_deref().ok_or("native_body_invalid")?)?),_=>return Err("native_body_invalid")};
        if route.body["kind"]=="none"&&length.is_some() || route.request_body["required"]==true&&length.is_none() ||
            route.body["minimum_bytes"].as_u64().is_some_and(|min|length.unwrap_or(0)<min) || route.body["maximum_bytes"].as_u64().is_some_and(|max|length.unwrap_or(0)>max) {return Err("native_body_invalid");}
        Ok((route,url,headers,length))
    }
}
