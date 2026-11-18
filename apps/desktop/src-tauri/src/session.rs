//! Source/readiness guard only. Credential-returning IPC was not admitted by
//! automatic review and is deliberately absent; no fake ready DTO is returned.
use std::{fs::{File,OpenOptions}, path::{Path,PathBuf}, sync::{atomic::{AtomicBool,Ordering},Mutex,Arc}};
use tauri::Url;
use crate::{route_contract::{Contract,random_id,TransportError},transport::{Broker,Descriptor}};

#[derive(Clone,Copy,PartialEq,Eq)]
pub enum Phase { Starting, Ready, Stopping, Failed, Closed }
pub struct HostState {
    expected_url:Url,
    phase:Mutex<Phase>,
    pub closing:AtomicBool,
    _instance_lock:File,
    pub instance_dir:PathBuf,
    generation:Mutex<Option<String>>,
    pub setup:crate::owner_setup::SetupController,
    broker:Mutex<Option<Arc<Broker>>>,
    lifecycle:tokio::sync::Mutex<()>,
    #[cfg(windows)]
    api:Mutex<Option<Arc<crate::engine::ApiRuntime>>>,
    #[cfg(windows)]
    product:Mutex<Option<Arc<crate::product_launcher::ProductRuntime>>>,
    #[cfg(windows)]
    workbench:Mutex<Option<crate::workbench_host::WorkbenchHost>>,
    #[cfg(windows)]
    origin:Mutex<Option<String>>,
}
impl HostState {
    pub fn new(expected_url:Url,instance_dir:&Path)->Result<Self,&'static str>{
        std::fs::create_dir_all(instance_dir).map_err(|_|"native_instance_unavailable")?;
        let root=instance_dir.canonicalize().map_err(|_|"native_instance_unavailable")?;
        let lock=OpenOptions::new().read(true).write(true).create(true).truncate(false).open(root.join("native-owner.lock")).map_err(|_|"native_instance_unavailable")?;
        lock.try_lock().map_err(|_|"native_instance_in_use")?;
        // Instance identity belongs to the Backend metadata row. No native
        // directory-name/JSON identity is invented here.
        Ok(Self{expected_url,phase:Mutex::new(Phase::Starting),closing:AtomicBool::new(false),_instance_lock:lock,instance_dir:root,generation:Mutex::new(None),setup:crate::owner_setup::SetupController::new(),broker:Mutex::new(None),lifecycle:tokio::sync::Mutex::new(()),#[cfg(windows)]api:Mutex::new(None),#[cfg(windows)]product:Mutex::new(None),#[cfg(windows)]workbench:Mutex::new(None),#[cfg(windows)]origin:Mutex::new(None)})
    }
    pub fn authorize(&self,label:&str,url:&Url)->Result<(),&'static str>{
        if label!="main"||url!=&self.expected_url{return Err("native_source_denied");}Ok(())
    }
    pub fn session_unavailable(&self,label:&str,url:&Url)->Result<(),&'static str>{
        self.authorize(label,url)?;
        let _phase=self.phase.lock().map_err(|_|"native_session_unavailable")?;
        let _closing=self.closing.load(Ordering::Acquire);
        Err("native_session_unavailable")
    }
    pub fn backend_contract_pending(&self){if let Ok(mut phase)=self.phase.lock(){*phase=Phase::Failed;}}
    pub fn startup_failed(&self){if let Ok(mut phase)=self.phase.lock(){if *phase!=Phase::Closed{*phase=Phase::Failed;}}}
    pub fn document_started(&self){
        self.setup.document_started();
        let old=self.generation.lock().ok().and_then(|mut g|g.take());
        let broker=self.broker.lock().ok().and_then(|b|b.clone());
        if let(Some(generation),Some(broker))=(old,broker){tauri::async_runtime::spawn(async move{broker.invalidate_generation(&generation).await;});}
    }
    pub fn document_finished(&self,label:&str,url:&Url)->Result<(),&'static str>{
        self.authorize(label,url)?;
        let mut generation=self.generation.lock().map_err(|_|"native_state_unavailable")?;
        if generation.is_none(){*generation=Some(random_id()?);}Ok(())
    }
    pub fn context(&self,label:&str,url:&Url,generation:Option<&str>)->Result<(Arc<Broker>,String),TransportError>{
        self.authorize(label,url).map_err(|c|TransportError::new(c,"validation",false))?;
        if self.closing.load(Ordering::Acquire)||self.phase.lock().map_err(|_|TransportError::new("native_state_unavailable","session",false))?.ne(&Phase::Ready){return Err(TransportError::new("native_session_unavailable","session",false));}
        #[cfg(windows)]
        {
            let api_alive=self.api.lock().map_err(|_|TransportError::new("native_state_unavailable","session",false))?.as_ref().is_some_and(|api|api.alive());
            let product_alive=self.product.lock().map_err(|_|TransportError::new("native_state_unavailable","session",false))?.as_ref().is_some_and(|product|product.alive());
            if !api_alive&&!product_alive{return Err(TransportError::new("native_engine_exited","session",false));}
        }
        let actual=self.generation.lock().map_err(|_|TransportError::new("native_state_unavailable","session",false))?.clone().ok_or(TransportError::new("native_document_not_ready","session",false))?;
        if generation.is_some_and(|expected|expected!=actual){return Err(TransportError::new("native_generation_invalid","validation",false));}
        let broker=self.broker.lock().map_err(|_|TransportError::new("native_state_unavailable","session",false))?.clone().ok_or(TransportError::new("native_session_unavailable","session",false))?;
        Ok((broker,actual))
    }
    pub fn descriptor(&self,label:&str,url:&Url)->Result<Descriptor,TransportError>{let(broker,generation)=self.context(label,url,None)?;broker.descriptor(&generation)}
    /// Independent authenticated pre-API UI context. This never grants Broker,
    /// bearer, execution identity, Owner confirmation or APIReady.
    pub fn setup_context(&self,label:&str,url:&Url,expected:Option<&str>)->Result<String,TransportError>{
        self.authorize(label,url).map_err(|c|TransportError::new(c,"validation",false))?;
        if self.closing.load(Ordering::Acquire){return Err(TransportError::new("native_host_stopping","session",false));}
        let actual=self.generation.lock().map_err(|_|TransportError::new("native_state_unavailable","session",false))?.clone().ok_or(TransportError::new("native_document_not_ready","session",false))?;
        if expected.is_some_and(|value|value!=actual){return Err(TransportError::new("native_generation_invalid","validation",false));}Ok(actual)
    }
    /// Native-only assembly before Backend supplies its actual SQLite instance.
    /// There is no renderer callable, JSON identity issuer or fallback ID.
    #[cfg(windows)]
    pub(crate) fn bind_installed_setup(&self,installation:Arc<crate::native_installation::NativeInstallationGuards>,control:Arc<crate::resource_pins::ResourcePins>,parent:usize)->Result<(),&'static str>{
        if self.closing.load(Ordering::Acquire){return Err("native_host_stopping");}
        let resources=Arc::new(crate::engine::LaunchResources::load_setup_installed(installation.clone())?);
        let driver=crate::owner_setup_runtime::InstalledSetupDriver::create_with_qualification(installation,control,resources,&self.instance_dir,parent)?;
        self.setup.install_driver(driver)
    }
    #[cfg(windows)]
    pub async fn start_api(self:&Arc<Self>,resources:crate::engine::LaunchResources)->Result<(),&'static str>{
        let _lifecycle=self.lifecycle.lock().await;
        if self.closing.load(Ordering::Acquire){return Err("native_host_stopping");}
        let api=Arc::new(crate::engine::ApiRuntime::launch(resources,&self.instance_dir).await?);
        let contract=Arc::new(Contract::load()?);let broker=Arc::new(Broker::new(api.connection.clone(),contract));
        *self.api.lock().map_err(|_|"native_state_unavailable")?=Some(api);
        *self.broker.lock().map_err(|_|"native_state_unavailable")?=Some(broker);
        if self.closing.load(Ordering::Acquire){return Err("native_host_stopping");}
        *self.phase.lock().map_err(|_|"native_state_unavailable")?=Phase::Ready;
        let owner=Arc::downgrade(self);
        tauri::async_runtime::spawn(async move{
            loop{
                tokio::time::sleep(std::time::Duration::from_millis(250)).await;
                let Some(state)=owner.upgrade()else{break;};
                if state.closing.load(Ordering::Acquire)||!state.phase.lock().is_ok_and(|p|*p==Phase::Ready){break;}
                let alive=state.api.lock().is_ok_and(|a|a.as_ref().is_some_and(|api|api.alive()));
                if !alive{
                    state.startup_failed();
                    let broker=state.broker.lock().ok().and_then(|b|b.clone());
                    if let Some(broker)=broker{broker.stop().await;}
                    eprintln!("{}",serde_json::json!({"event":"native_engine_exited","scope":"api"}));break;
                }
            }
        });Ok(())
    }
    /// Product installation path: the shell drives the installed
    /// `product-serve`/`product-worker` (ADR0084) instead of an indexed native
    /// installation. The bearer never leaves this process.
    #[cfg(windows)]
    pub async fn start_product(self:&Arc<Self>)->Result<(),&'static str>{
        let _lifecycle=self.lifecycle.lock().await;
        if self.closing.load(Ordering::Acquire){return Err("native_host_stopping");}
        let product=Arc::new(crate::product_launcher::ProductRuntime::launch().await?);
        let plan=crate::product_launcher::plan()?;
        let host=crate::workbench_host::WorkbenchHost::start(plan.workbench,format!("http://127.0.0.1:{}",product.port),product.token.clone())?;
        let origin=host.origin.clone();
        println!("{}",serde_json::json!({"event":"product_workbench_host","origin":origin,"engine_port":product.port}));
        *self.workbench.lock().map_err(|_|"native_state_unavailable")?=Some(host);
        *self.origin.lock().map_err(|_|"native_state_unavailable")?=Some(origin);
        let contract=Arc::new(Contract::load()?);let broker=Arc::new(Broker::new(product.connection.clone(),contract));
        println!("{}",serde_json::json!({"event":"product_engine_ready","instance_id":product.instance_id,"port":product.port}));
        *self.product.lock().map_err(|_|"native_state_unavailable")?=Some(product);
        *self.broker.lock().map_err(|_|"native_state_unavailable")?=Some(broker);
        if self.closing.load(Ordering::Acquire){return Err("native_host_stopping");}
        *self.phase.lock().map_err(|_|"native_state_unavailable")?=Phase::Ready;
        let owner=Arc::downgrade(self);
        tauri::async_runtime::spawn(async move{
            loop{
                tokio::time::sleep(std::time::Duration::from_millis(250)).await;
                let Some(state)=owner.upgrade()else{break;};
                if state.closing.load(Ordering::Acquire)||!state.phase.lock().is_ok_and(|p|*p==Phase::Ready){break;}
                let alive=state.product.lock().is_ok_and(|p|p.as_ref().is_some_and(|product|product.alive()));
                if !alive{
                    state.startup_failed();
                    let broker=state.broker.lock().ok().and_then(|b|b.clone());
                    if let Some(broker)=broker{broker.stop().await;}
                    eprintln!("{}",serde_json::json!({"event":"product_engine_exited","scope":"api"}));break;
                }
            }
        });Ok(())
    }
    /// Read-only status for the native About dialog; never a renderer DTO with
    /// credentials. The port is the loopback API port only.
    #[cfg(windows)]
    pub fn status(&self)->(&'static str,Option<u16>){
        let phase=self.phase.lock().map(|phase|*phase).unwrap_or(Phase::Failed);
        let port=self.product.lock().ok().and_then(|product|product.as_ref().map(|product|product.port));
        let label=match phase{Phase::Ready=>"已连接",Phase::Starting=>"连接中",Phase::Failed=>"引擎启动失败",Phase::Stopping=>"正在停止",Phase::Closed=>"已停止"};
        (label,port)
    }
    #[cfg(windows)]
    pub fn workbench_origin(&self)->Option<String>{self.origin.lock().ok().and_then(|origin|origin.clone())}
    pub async fn stop_api(&self)->Result<Option<crate::engine::StopReceipt>,&'static str>{
        self.setup.close();
        let _lifecycle=self.lifecycle.lock().await;
        if let Ok(mut phase)=self.phase.lock(){*phase=Phase::Stopping;}
        #[cfg(windows)]
        {
            // Stop the loopback host first so no request outlives the engine.
            if let Ok(mut host)=self.workbench.lock(){if let Some(mut host)=host.take(){host.stop();}}
            if let Ok(mut origin)=self.origin.lock(){origin.take();}
        }
        let broker=self.broker.lock().map_err(|_|"native_state_unavailable")?.take();
        if let Some(broker)=broker{broker.stop().await;}
        #[cfg(windows)]
        let api=self.api.lock().ok().and_then(|mut api|api.take());
        #[cfg(windows)]
        let product=self.product.lock().ok().and_then(|mut product|product.take());
        #[cfg(windows)]
        let receipt=if let Some(product)=product{
            Some(tauri::async_runtime::spawn_blocking(move||product.stop()).await.map_err(|_|"native_cleanup_failed")?)
        }else{
            match api{Some(api)=>Some(tauri::async_runtime::spawn_blocking(move||api.stop()).await.map_err(|_|"native_cleanup_failed")?),None=>None}
        };
        #[cfg(not(windows))]
        let receipt=None;
        if let Ok(mut phase)=self.phase.lock(){*phase=Phase::Closed;}Ok(receipt)
    }
    pub fn close_without_api(&self)->Result<(),&'static str>{
        let mut phase=self.phase.lock().map_err(|_|"native_session_unavailable")?;
        *phase=Phase::Stopping;*phase=Phase::Closed;Ok(())
    }
}

/// Mirror of pinned tauri2.12.1 manager/protocol resolver for the single fixed
/// App(index.html) entry, local frontendDist, no devUrl and HTTPS=false.
/// The resolver is pub(crate); the actual webview URL is separately guarded.
pub fn fixed_main_url(config:&tauri::Config)->Result<Url,&'static str>{
    if config.build.dev_url.is_some(){return Err("native_dev_origin_unverified");}
    if !matches!(config.build.frontend_dist,Some(tauri::utils::config::FrontendDist::Directory(_))){return Err("native_bundle_entry_invalid");}
    Url::parse(if cfg!(windows){"http://tauri.localhost"}else{"tauri://localhost"}).map_err(|_|"native_bundle_entry_invalid")
}
