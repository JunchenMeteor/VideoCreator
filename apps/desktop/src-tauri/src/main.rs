#![cfg_attr(not(debug_assertions),windows_subsystem="windows")]
mod session;
mod platform;
mod resource_pins;
mod engine;
mod load_policy;
mod windows_native_sources;
#[cfg(windows)]
mod resource_authority;
mod native_startup;
mod native_installation;
mod qualification_record;
#[cfg(windows)]
mod qualification_pack;
#[cfg(windows)]
mod qualification_commit;
#[cfg(windows)]
mod qualification_registry;
#[cfg(windows)]
mod installation_record;
#[cfg(windows)]
mod qualified_authority;
mod owner_setup;
mod owner_setup_window;
#[cfg(windows)]
mod owner_setup_channel;
#[cfg(windows)]
mod owner_setup_runtime;
#[cfg(windows)]
mod owner_setup_directory;
#[cfg(windows)]
mod owner_setup_initialize;
#[cfg(windows)]
mod installation_trust;
mod commands;
mod wire;
mod route_contract;
mod transport;
use std::sync::{Arc,atomic::Ordering};
use tauri::{Manager,WebviewUrl,WebviewWindowBuilder,WindowEvent,webview::PageLoadEvent};
use session::HostState;

fn startup_rejected(app:&tauri::App,code:&'static str){
    eprintln!("{}",serde_json::json!({"event":"startup_rejected","code":code}));
    #[cfg(windows)]
    {
        let text=if code=="native_instance_in_use"{"该实例已在运行"}else{"无法打开本地创作实例，请检查实例目录权限"};
        let title="VideoCreator".encode_utf16().chain(Some(0)).collect::<Vec<_>>();
        let message=text.encode_utf16().chain(Some(0)).collect::<Vec<_>>();
        unsafe{windows_sys::Win32::UI::WindowsAndMessaging::MessageBoxW(std::ptr::null_mut(),message.as_ptr(),title.as_ptr(),windows_sys::Win32::UI::WindowsAndMessaging::MB_OK|windows_sys::Win32::UI::WindowsAndMessaging::MB_ICONINFORMATION);}
    }
    app.handle().exit(2);
}

fn main(){
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![commands::get_engine_session,commands::engine_request_open,commands::engine_upload_chunk,commands::engine_upload_finish,commands::engine_response_head,commands::engine_response_read,commands::engine_request_abort,commands::engine_request_release,commands::owner_setup_prepare,commands::owner_setup_present,commands::owner_setup_status,commands::owner_setup_abort])
        .setup(|app|{
            let expected=session::fixed_main_url(app.config()).map_err(std::io::Error::other)?;
            let root=if cfg!(debug_assertions){
                match std::env::var_os("VIDEO_CREATOR_NATIVE_DATA_DIR"){
                    Some(value)=>{let path=std::path::PathBuf::from(value);if !path.is_absolute(){startup_rejected(app,"native_instance_unavailable");return Ok(());}path},
                    None=>app.path().app_data_dir()?.join("Instances").join("Main"),
                }
            }else{app.path().app_data_dir()?.join("Instances").join("Main")};
            let state=match HostState::new(expected.clone(),&root){Ok(state)=>Arc::new(state),Err(code)=>{startup_rejected(app,code);return Ok(());}};
            app.manage(state.clone());
            let main_window=WebviewWindowBuilder::new(app,"main",WebviewUrl::App("index.html".into()))
                .title("VideoCreator")
                .inner_size(1280.0,850.0)
                .min_inner_size(720.0,600.0)
                .use_https_scheme(false)
                .on_navigation(move|url|url==&expected)
                .on_new_window(|_,_|tauri::webview::NewWindowResponse::Deny)
                .on_page_load(|window,payload|{
                    let state=window.state::<Arc<HostState>>();
                    match payload.event(){
                        PageLoadEvent::Started=>state.document_started(),
                        PageLoadEvent::Finished=>{if state.document_finished(window.label(),payload.url()).is_ok(){println!("{}",serde_json::json!({"event":"native_document_loaded","label":"main"}));}},
                    }
                })
                .build()?;
            #[cfg(windows)]
            {
                // Pre-API setup is independent of the APIReady broker gate.
                // Only the protected producer layout can supply real guards.
                // No instance is invented; one indexed child initializes it.
                let setup_binding=main_window.hwnd().map_err(|_|"setup_window_unavailable").and_then(|parent|
                    native_installation::NativeInstallationGuards::from_packaged_host().and_then(|(installation,control)|
                        state.bind_installed_setup(installation,control,parent.0 as usize)));
                if let Err(code)=setup_binding{eprintln!("{}",serde_json::json!({"event":"native_setup_unavailable","code":code}));}
                let resources=app.path().resource_dir()?;let state=state.clone();
                tauri::async_runtime::spawn(async move{
                    let loaded=tauri::async_runtime::spawn_blocking(move||engine::LaunchResources::load(&resources)).await;
                    let result=match loaded{Ok(Ok(resources))=>state.start_api(resources).await,Ok(Err(code))=>Err(code),Err(_)=>Err("native_runtime_unavailable")};
                    match result{Ok(())=>println!("{}",serde_json::json!({"event":"native_engine_ready","scope":"api"})),Err(code)=>{state.startup_failed();eprintln!("{}",serde_json::json!({"event":"native_engine_unavailable","code":code}));}}
                });
            }
            #[cfg(not(windows))]
            state.backend_contract_pending();
            println!("{}",serde_json::json!({"event":"native_shell_started","session_status":"starting"}));
            Ok(())
        })
        .on_window_event(|window,event|{
            if let WindowEvent::CloseRequested{api,..}=event{
                api.prevent_close();
                let state=window.state::<Arc<HostState>>().inner().clone();
                if state.closing.swap(true,Ordering::AcqRel){return;}
                // No qualified tray/Worker yet: never hide or promise background work.
                let app=window.app_handle().clone();
                tauri::async_runtime::spawn(async move{
                    let code=match state.stop_api().await{
                        Ok(Some(receipt))=>{println!("{}",serde_json::json!({"event":"native_api_stop","scope":"api","classification":receipt.classification,"actual_exit":receipt.actual_exit,"api_marker":receipt.api_marker,"port_closed":receipt.port_closed,"owned_tree_empty":receipt.owned_tree_empty}));if receipt.classification=="normal"{0}else{1}},
                        Ok(None)=>{println!("{}",serde_json::json!({"event":"native_host_stop","scope":"host","api_started":false}));0},
                        Err(_)=>1,
                    };app.exit(code);
                });
            }
        })
        .run(tauri::generate_context!())
        .unwrap_or_else(|_|{eprintln!("native_host_start_failed");std::process::exit(1)});
}
