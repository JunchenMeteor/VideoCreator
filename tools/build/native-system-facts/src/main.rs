//! Source-only bounded facts frontend. The caller still needs a separately
//! fixed compile/run plan for every system read, carrier and catalog access.
#[path = "../../../../apps/desktop/src-tauri/src/windows_native_sources.rs"]
mod windows_native_sources;
use std::{collections::BTreeMap,fs,path::PathBuf};
use serde_json::Value;
use sha2::{Digest,Sha256};

const TARGETS:[&str;36]=["aclui.dll","activeds.dll","avicap32.dll","avrt.dll","bcryptprimitives.dll","combase.dll","credui.dll","d2d1.dll","dsound.dll","dwrite.dll","dxgi.dll","imagehlp.dll","imm32.dll","ktmw32.dll","loadperf.dll","lz32.dll","mfc140u.dll","mpr.dll","msimg32.dll","msvcrt.dll","mswsock.dll","ntdsapi.dll","odbc32.dll","oleacc.dll","pdh.dll","propsys.dll","query.dll","rasapi32.dll","sfc.dll","urlmon.dll","usp10.dll","uxtheme.dll","webservices.dll","wevtapi.dll","wininet.dll","wsock32.dll"];

fn run()->Result<(),&'static str>{
    let args=std::env::args().skip(1).collect::<Vec<_>>();
    if args.len()!=4||args[0]!="--contracts"||args[2]!="--contracts-sha256"{return Err("facts_fixed_arguments_required");}
    let path=PathBuf::from(&args[1]);
    if !path.is_absolute()||path.file_name().is_none_or(|name|name!="WindowsNativeContracts.json"){return Err("facts_input_path_invalid");}
    for ancestor in path.ancestors(){let metadata=fs::symlink_metadata(ancestor).map_err(|_|"facts_input_unavailable")?;if metadata.file_type().is_symlink(){return Err("facts_input_reparse");}#[cfg(windows)]{use std::os::windows::fs::MetadataExt;if metadata.file_attributes()&1024!=0{return Err("facts_input_reparse");}}}
    let body=fs::read(&path).map_err(|_|"facts_input_unavailable")?;
    if body.len()>1024*1024||format!("{:x}",Sha256::digest(&body))!=args[3]{return Err("facts_input_integrity");}
    let value:Value=serde_json::from_slice(&body).map_err(|_|"facts_input_invalid")?;
    if value["format"]!="windows-native-contract-declarations-v1"{return Err("facts_input_version");}
    let mut records=BTreeMap::new();let mut ids=Vec::new();
    for name in TARGETS{
        let mut record=value["records"][name].clone();let id=record["id"].as_str().ok_or("facts_exact_contract_missing")?.to_owned();
        if record["basename"]!=name||!matches!(record["source_kind"].as_str(),Some("windows_component"|"external_vc")){return Err("facts_exact_contract_invalid");}
        record["profiles"]=serde_json::json!(["facts"]);records.insert(id.clone(),record);ids.push(id);
    }
    // No product, target DLL LoadLibrary, arbitrary directory argument, Python
    // or Tauri main. Same native verifier; observation errors remain visible.
    let context=windows_native_sources::VerifiedSystemContext::collect(&records,&ids,"facts","source-only-facts-v1",&args[3])?;
    println!("{}",serde_json::to_string(context.observations()).map_err(|_|"facts_output_invalid")?);
    if !context.observations().errors.is_empty(){return Err("facts_sources_or_support_conditions_unverified");}Ok(())
}
fn main(){if let Err(error)=run(){eprintln!("{error}");std::process::exit(1);}}
