//! Pre-API setup UI. Renderer input is a proposal, never confirmation authority.
use std::sync::{Arc, Mutex};
use serde::{Deserialize, Serialize};
use serde_json::Value;

pub const FRAME_LIMIT: usize = 32 * 1024 * 1024;
#[derive(Clone, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum SetupPhase { Unavailable, Idle, Preparing, Review, Confirming, Applying, Completed, Blocked, Aborted }
#[derive(Clone, Serialize)]
pub struct SetupView {
    pub version: &'static str,
    pub generation: String,
    pub attempt: Option<String>,
    pub phase: SetupPhase,
    pub message: String,
    pub project_name: Option<String>,
    pub can_present: bool,
    // Opaque original business receipt; never a confirmation source or credential.
    pub goal_receipt: Option<Value>,
    // A read-only association with the original native-held proposal. This
    // never authorizes another prepare, confirmation, scope or credential.
    pub request_identity: Option<RequestIdentity>,
    pub current_document: bool,
}
#[derive(Clone, Serialize)]
pub struct RequestIdentity {
    pub original_generation: String,
    pub idempotency_key: String,
    pub goal: Value,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PrepareInput { pub generation: String, pub idempotency_key: String, pub goal: Value }
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AttemptInput { pub generation: String, pub attempt: String }

/// Implemented by the original indexed launch owner, not by the Webview.
/// A driver must retain PreparedLaunch, both installation guards and actual
/// child/Job until terminal. Result/event data cannot construct confirmation.
pub(crate) trait SetupDriver: Send + Sync {
    fn start(&self, input: PrepareInput, events: Arc<SetupAttempt>) -> Result<(), &'static str>;
}
pub(crate) struct SetupAttempt {
    pub generation: String,
    pub id: String,
    pub(crate) document_generation: u64,
    view: Mutex<SetupView>,
    pub(crate) cancelled: std::sync::atomic::AtomicBool,
    present: std::sync::atomic::AtomicBool,
}
impl SetupAttempt {
    pub(crate) fn prepared(&self, name: &str) -> Result<(), &'static str> {
        let mut view = self.view.lock().map_err(|_| "setup_state_unavailable")?;
        view.phase = SetupPhase::Review;
        view.message = "请查看本次创作范围，再打开系统确认窗口。".into();
        view.project_name = Some(name.into());
        view.can_present = true;
        Ok(())
    }
    pub(crate) fn wants_present(&self) -> bool { self.present.load(std::sync::atomic::Ordering::Acquire) }
    pub(crate) fn applying(&self) {
        if let Ok(mut view) = self.view.lock() { view.phase = SetupPhase::Applying; view.can_present = false; view.message = "正在保存本次设置并继续原来的创作请求。".into(); }
    }
    pub(crate) fn completed(&self, receipt: Value) {
        if let Ok(mut view) = self.view.lock() { view.phase = SetupPhase::Completed; view.can_present = false; view.goal_receipt = Some(receipt); view.message = "设置已完成，原来的创作请求已受理。".into(); }
    }
    pub(crate) fn failed(&self, _code: &'static str) {
        if let Ok(mut view) = self.view.lock() { view.phase = SetupPhase::Blocked; view.can_present = false; view.message = "本次设置尚未完成。请查看诊断结果；已取得的请求回执会保留。".into(); }
    }
}
struct SetupState { driver: Option<Arc<dyn SetupDriver>>, attempt: Option<Arc<SetupAttempt>>, document_serial: u64 }
pub struct SetupController { state: Mutex<SetupState> }
impl SetupController {
    pub fn new() -> Self { Self { state: Mutex::new(SetupState { driver: None, attempt: None, document_serial: 0 }) } }
    pub(crate) fn install_driver(&self, driver: Arc<dyn SetupDriver>) -> Result<(), &'static str> {
        let mut state = self.state.lock().map_err(|_| "setup_state_unavailable")?;
        if state.driver.is_some() || state.attempt.is_some() { return Err("setup_driver_already_bound"); }
        state.driver = Some(driver); Ok(())
    }
    pub(crate) fn document_started(&self) {
        if let Ok(mut state) = self.state.lock() {
            state.document_serial = state.document_serial.saturating_add(1);
            if let Some(attempt) = &state.attempt { attempt.cancelled.store(true, std::sync::atomic::Ordering::Release); }
        }
    }
    pub fn status(&self, generation: &str) -> Result<SetupView, &'static str> {
        let state = self.state.lock().map_err(|_| "setup_state_unavailable")?;
        if let Some(attempt) = &state.attempt {
            let mut view=attempt.view.lock().map_err(|_| "setup_state_unavailable")?.clone();
            view.current_document=attempt.generation==generation && attempt.document_generation==state.document_serial;
            if !view.current_document {
                view.generation=generation.into();view.can_present=false;
                if !matches!(view.phase,SetupPhase::Completed|SetupPhase::Applying) {
                    view.phase=SetupPhase::Blocked;view.message="页面已更新，原来的设置请求不会自动重发。请查看恢复状态。".into();
                }
            }
            return Ok(view);
        }
        Ok(SetupView { version:"native-setup-ui-v1", generation:generation.into(), attempt:None,
            phase:if state.driver.is_some(){SetupPhase::Idle}else{SetupPhase::Unavailable},
            message:if state.driver.is_some(){"可以准备本次创作设置。"}else{"本地创作资源尚未完成安装检查。"}.into(),
            project_name:None, can_present:false, goal_receipt:None,request_identity:None,current_document:true })
    }
    pub fn prepare(&self, input: PrepareInput) -> Result<SetupView, &'static str> {
        // Backend's one ProjectGoalInput model validates the complete Goal.
        // No Owner/scope/options/module/env/image/confirmation fields admitted here.
        if input.idempotency_key.is_empty() || input.idempotency_key.len()>128
            || !input.idempotency_key.bytes().all(|b|b.is_ascii_alphanumeric()||b"_.:-".contains(&b))
            || !input.goal.is_object() || serde_json::to_vec(&input.goal).map_err(|_|"setup_proposal_invalid")?.len()>FRAME_LIMIT-16384 {
            return Err("setup_proposal_invalid");
        }
        let (driver, attempt) = {
            let mut state = self.state.lock().map_err(|_| "setup_state_unavailable")?;
            if state.attempt.is_some() { return Err("setup_original_attempt_retained"); }
            let driver = state.driver.clone().ok_or("setup_installation_unavailable")?;
            let id = crate::route_contract::random_id()?;
            if state.document_serial==0||state.document_serial==u64::MAX{return Err("setup_generation_exhausted");}
            let attempt = Arc::new(SetupAttempt { generation:input.generation.clone(), id:id.clone(), document_generation:state.document_serial,
                view:Mutex::new(SetupView { version:"native-setup-ui-v1",generation:input.generation.clone(),attempt:Some(id),phase:SetupPhase::Preparing,
                    message:"正在核对创作目标并准备本次设置。".into(),project_name:None,can_present:false,goal_receipt:None,
                    request_identity:Some(RequestIdentity{original_generation:input.generation.clone(),idempotency_key:input.idempotency_key.clone(),goal:input.goal.clone()}),current_document:true }),
                cancelled:std::sync::atomic::AtomicBool::new(false),present:std::sync::atomic::AtomicBool::new(false) });
            state.attempt = Some(attempt.clone()); (driver, attempt)
        };
        if let Err(code) = driver.start(input, attempt.clone()) { attempt.failed(code); return Err(code); }
        self.status(&attempt.generation)
    }
    fn original(&self, input: &AttemptInput) -> Result<Arc<SetupAttempt>, &'static str> {
        let state = self.state.lock().map_err(|_| "setup_state_unavailable")?;
        let attempt = state.attempt.as_ref().ok_or("setup_attempt_missing")?;
        if (attempt.id.as_str(),attempt.generation.as_str()) != (input.attempt.as_str(),input.generation.as_str()) { return Err("setup_attempt_foreign"); }
        Ok(attempt.clone())
    }
    pub fn present(&self, input: AttemptInput) -> Result<SetupView, &'static str> {
        let attempt = self.original(&input)?;
        if attempt.cancelled.load(std::sync::atomic::Ordering::Acquire) { return Err("setup_source_closed"); }
        {
            let mut view = attempt.view.lock().map_err(|_| "setup_state_unavailable")?;
            if !view.can_present { return Err("setup_presentation_not_ready"); }
            view.phase = SetupPhase::Confirming; view.can_present=false;
            view.message = "请在系统弹出的窗口中核对项目、资源、费用与操作范围。".into();
        }
        // This only permits presentation. No accepted/confirmed state or text input.
        attempt.present.store(true, std::sync::atomic::Ordering::Release);
        self.status(&input.generation)
    }
    pub fn abort(&self, input: AttemptInput) -> Result<SetupView, &'static str> {
        let attempt = self.original(&input)?;
        let mut view=attempt.view.lock().map_err(|_|"setup_state_unavailable")?;
        if !matches!(view.phase,SetupPhase::Preparing|SetupPhase::Review|SetupPhase::Confirming) { return Err("setup_acceptance_already_contacted"); }
        attempt.cancelled.store(true, std::sync::atomic::Ordering::Release);
        // In-flight accepted actions are not cancelled, unknown or receipts cleared.
        view.phase=SetupPhase::Aborted;view.can_present=false;view.message="已中止尚未确认的设置。已取得的请求回执会保留。".into();drop(view);
        self.status(&input.generation)
    }
    pub(crate) fn close(&self) { if let Ok(state)=self.state.lock() { if let Some(attempt)=&state.attempt { attempt.cancelled.store(true,std::sync::atomic::Ordering::Release); } } }
}
