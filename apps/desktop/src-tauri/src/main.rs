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
#[cfg(windows)]
mod product_launcher;
#[cfg(windows)]
mod workbench_host;
use std::sync::{Arc,atomic::Ordering};
use tauri::{Manager,WebviewUrl,WebviewWindowBuilder,WindowEvent,webview::PageLoadEvent};
use tauri::menu::{MenuBuilder,MenuItemBuilder,SubmenuBuilder};
use tauri::tray::{MouseButton,MouseButtonState,TrayIconBuilder,TrayIconEvent};
use session::HostState;

fn show_main(app:&tauri::AppHandle){
    if let Some(window)=app.get_webview_window("main"){let _=window.show();let _=window.unminimize();let _=window.set_focus();}
}

/// The workbench is a single page with sidebar state, so the native menu asks
/// it to switch to the settings page instead of opening a second window.
fn open_settings(app:&tauri::AppHandle){
    if let Some(window)=app.get_webview_window("main"){
        let _=window.show();let _=window.unminimize();let _=window.set_focus();
        let _=window.eval("(()=>{const button=[...document.querySelectorAll('nav button')].find(item=>item.textContent.trim()==='设置');if(button){button.click();return;}const fallback=[...document.querySelectorAll('button')].find(item=>item.textContent.trim()==='设置');if(fallback){fallback.click();}})()");
    }
}

fn quit(app:&tauri::AppHandle){
    let state=app.state::<Arc<HostState>>().inner().clone();
    if state.closing.swap(true,Ordering::AcqRel){return;}
    let app=app.clone();
    tauri::async_runtime::spawn(async move{
        let code=match state.stop_api().await{
            Ok(Some(receipt))=>{println!("{}",serde_json::json!({"event":"native_api_stop","scope":"api","classification":receipt.classification,"actual_exit":receipt.actual_exit,"api_marker":receipt.api_marker,"port_closed":receipt.port_closed,"owned_tree_empty":receipt.owned_tree_empty}));if receipt.classification=="normal"{0}else{1}},
            Ok(None)=>{println!("{}",serde_json::json!({"event":"native_host_stop","scope":"host","api_started":false}));0},
            Err(_)=>1,
        };app.exit(code);
    });
}

#[cfg(windows)]
fn about(app:&tauri::AppHandle){
    use windows_sys::Win32::UI::WindowsAndMessaging::{MessageBoxW,MB_ICONINFORMATION,MB_OK};
    let state=app.state::<Arc<HostState>>().inner().clone();
    let(status,port)=state.status();
    let(install,data)=if product_launcher::configured(){
        match product_launcher::plan(){Ok(plan)=>(plan.root.display().to_string(),plan.instance.display().to_string()),Err(code)=>(format!("不可用 ({code})"),state.instance_dir.display().to_string())}
    }else{
        (std::env::current_exe().ok().and_then(|image|image.parent().map(|parent|parent.display().to_string())).unwrap_or_default(),state.instance_dir.display().to_string())
    };
    let engine=port.map(|port|format!("{status} (端口 {port})")).unwrap_or_else(||status.to_owned());
    let text=format!("VideoCreator {}\n\n安装目录：{install}\n数据目录：{data}\n引擎：{engine}",env!("CARGO_PKG_VERSION"));
    let title:Vec<u16>="关于 VideoCreator".encode_utf16().chain(Some(0)).collect();
    let message:Vec<u16>=text.encode_utf16().chain(Some(0)).collect();
    unsafe{MessageBoxW(std::ptr::null_mut(),message.as_ptr(),title.as_ptr(),MB_OK|MB_ICONINFORMATION);}
}

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
        .plugin(tauri_plugin_single_instance::init(|app,_arguments,_directory|{show_main(app);}))
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
            let settings_item=MenuItemBuilder::with_id("settings","设置…").accelerator("CmdOrCtrl+Comma").build(app)?;
            let file_quit=MenuItemBuilder::with_id("quit","退出").accelerator("CmdOrCtrl+Q").build(app)?;
            let file_menu=SubmenuBuilder::new(app,"文件").items(&[&settings_item,&file_quit]).build()?;
            let refresh=MenuItemBuilder::with_id("refresh","刷新").accelerator("CmdOrCtrl+R").build(app)?;
            #[cfg(debug_assertions)]
            let devtools=MenuItemBuilder::with_id("devtools","开发者工具").accelerator("F12").build(app)?;
            #[cfg(debug_assertions)]
            let view_menu=SubmenuBuilder::new(app,"视图").items(&[&refresh,&devtools]).build()?;
            #[cfg(not(debug_assertions))]
            let view_menu=SubmenuBuilder::new(app,"视图").items(&[&refresh]).build()?;
            let about_item=MenuItemBuilder::with_id("about","关于 VideoCreator").build(app)?;
            let help_menu=SubmenuBuilder::new(app,"帮助").items(&[&about_item]).build()?;
            let menu=MenuBuilder::new(app).items(&[&file_menu,&view_menu,&help_menu]).build()?;
            app.set_menu(menu)?;
            let tray_open=MenuItemBuilder::with_id("open","打开主窗口").build(app)?;
            let tray_settings=MenuItemBuilder::with_id("settings","设置…").build(app)?;
            let tray_quit=MenuItemBuilder::with_id("quit","退出").build(app)?;
            let tray_menu=MenuBuilder::new(app).items(&[&tray_open,&tray_settings,&tray_quit]).build()?;
            let _tray=TrayIconBuilder::with_id("video-creator-tray")
                .icon(app.default_window_icon().cloned().ok_or_else(||std::io::Error::other("native_tray_icon_unavailable"))?)
                .tooltip("VideoCreator")
                .menu(&tray_menu)
                .show_menu_on_left_click(false)
                .on_menu_event(|app,event|match event.id().as_ref(){"open"=>show_main(app),"settings"=>open_settings(app),"quit"=>quit(app),_=>{}})
                .on_tray_icon_event(|tray,event|{if let TrayIconEvent::Click{button:MouseButton::Left,button_state:MouseButtonState::Up,..}=event{show_main(tray.app_handle());}})
                .build(app)?;
            let main_window=WebviewWindowBuilder::new(app,"main",WebviewUrl::App("index.html".into()))
                .title("VideoCreator")
                .inner_size(1280.0,850.0)
                .min_inner_size(720.0,600.0)
                .decorations(true)
                .resizable(true)
                .minimizable(true)
                .maximizable(true)
                .closable(true)
                .use_https_scheme(false)
                .on_navigation({let state=state.clone();let expected=expected.clone();move|url|url==&expected||state.workbench_origin().is_some_and(|origin|url.as_str().starts_with(&origin))})
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
                let resources=app.path().resource_dir()?;let state=state.clone();let handle=app.handle().clone();
                tauri::async_runtime::spawn(async move{
                    if product_launcher::configured(){
                        let result=state.start_product().await;
                        match result{Ok(())=>{println!("{}",serde_json::json!({"event":"native_engine_ready","scope":"api","source":"product_installation"}));if let(Some(window),Some(origin))=(handle.get_webview_window("main"),state.workbench_origin()){if let Ok(url)=tauri::Url::parse(&origin){let _=window.navigate(url);}}},Err(code)=>{state.startup_failed();eprintln!("{}",serde_json::json!({"event":"product_engine_unavailable","code":code}));}}
                        return;
                    }
                    let loaded=tauri::async_runtime::spawn_blocking(move||engine::LaunchResources::load(&resources)).await;
                    let result=match loaded{Ok(Ok(resources))=>state.start_api(resources).await,Ok(Err(code))=>Err(code),Err(_)=>Err("native_runtime_unavailable")};
                    match result{Ok(())=>{println!("{}",serde_json::json!({"event":"native_engine_ready","scope":"api"}));if let Some(window)=handle.get_webview_window("main"){let _=window.eval("location.reload()");}},Err(code)=>{state.startup_failed();eprintln!("{}",serde_json::json!({"event":"native_engine_unavailable","code":code}));}}
                });
            }
            #[cfg(not(windows))]
            state.backend_contract_pending();
            println!("{}",serde_json::json!({"event":"native_shell_started","session_status":"starting"}));
            Ok(())
        })
        .on_menu_event(|app,event|match event.id().as_ref(){
            "settings"=>open_settings(app),
            "quit"=>quit(app),
            "refresh"=>{if let Some(window)=app.get_webview_window("main"){let _=window.eval("location.reload()");}},
            "devtools"=>{#[cfg(debug_assertions)]if let Some(window)=app.get_webview_window("main"){window.open_devtools();}},
            "about"=>{#[cfg(windows)]about(app);},
            _=>{},
        })
        .on_window_event(|window,event|{
            if let WindowEvent::CloseRequested{api,..}=event{
                // Closing the window only hides it: background production is not
                // cancelled. The engine stops only from the explicit quit item.
                api.prevent_close();
                // Win32 hide is used because the tao hide path races the close
                // notification on a navigated (http) webview.
                if let Ok(hwnd)=window.hwnd(){
                    use windows_sys::Win32::UI::WindowsAndMessaging::{ShowWindow,SW_HIDE};
                    unsafe{ShowWindow(hwnd.0 as _,SW_HIDE);}
                }
                let hidden=window.hide();
                println!("{}",serde_json::json!({"event":"native_window_hidden","scope":"main","hidden":hidden.is_ok()}));
            }
        })
        .run(tauri::generate_context!())
        .unwrap_or_else(|_|{eprintln!("native_host_start_failed");std::process::exit(1)});
}
