//! Actual native-only input. No IPC accepts the challenge text or confirmation.
#[cfg(windows)]
mod windows {
    use std::{mem::zeroed, ptr::{null, null_mut}, sync::OnceLock, time::Instant};
    use windows_sys::Win32::{Foundation::{HWND, LPARAM, LRESULT, WPARAM},
        System::{LibraryLoader::GetModuleHandleW, Threading::{GetCurrentProcessId, GetCurrentThreadId},
            RemoteDesktop::ProcessIdToSessionId,
            StationsAndDesktops::{CloseDesktop, GetThreadDesktop, GetUserObjectInformationW, OpenInputDesktop, DESKTOP_READOBJECTS, UOI_NAME}},
        UI::{Input::KeyboardAndMouse::{EnableWindow, SetFocus}, WindowsAndMessaging::*}};

    fn wide(value:&str)->Vec<u16>{value.encode_utf16().chain(Some(0)).collect()}
    fn desktop_name(handle:*mut core::ffi::c_void)->Result<Vec<u16>,&'static str>{
        let mut value=vec![0u16;256]; let mut required=0;
        if handle.is_null() || unsafe{GetUserObjectInformationW(handle,UOI_NAME,value.as_mut_ptr().cast(),512,&mut required)}==0
            || required==0 || required>512{return Err("setup_interactive_desktop_unavailable");}
        value.truncate(required as usize/2);Ok(value)
    }
    pub(crate) fn interactive_session()->Result<u32,&'static str>{
        let mut session=0;
        if unsafe{ProcessIdToSessionId(GetCurrentProcessId(),&mut session)}==0||session==0{return Err("setup_interactive_session_unavailable");}
        let input=unsafe{OpenInputDesktop(0,0,DESKTOP_READOBJECTS)};
        if input.is_null(){return Err("setup_interactive_desktop_unavailable");}
        let input_name=desktop_name(input); unsafe{CloseDesktop(input);}
        if input_name?!=desktop_name(unsafe{GetThreadDesktop(GetCurrentThreadId())})? {return Err("setup_desktop_changed");}
        Ok(session)
    }
    pub(crate) struct NativeInput { pub(crate) accepted_at:Instant }
    struct WindowState<'a> {
        challenge:&'a str, edit:HWND, confirm:HWND,
        check:&'a dyn Fn()->Result<(),&'static str>, deadline:Instant,
        outcome:Option<Result<NativeInput,&'static str>>,
    }
    unsafe extern "system" fn procedure(hwnd:HWND,message:u32,wparam:WPARAM,lparam:LPARAM)->LRESULT{
        if message==WM_NCCREATE {
            let create=unsafe{&*(lparam as *const CREATESTRUCTW)};
            unsafe{SetWindowLongPtrW(hwnd,GWLP_USERDATA,create.lpCreateParams as isize);}
        }
        let state=unsafe{GetWindowLongPtrW(hwnd,GWLP_USERDATA)}as *mut WindowState<'_>;
        if !state.is_null() {
            let state=unsafe{&mut *state};
            let invalid=||{if Instant::now()>=state.deadline{Err("setup_confirmation_expired")}else{(state.check)()}};
            match message {
                WM_TIMER=>{if let Err(code)=invalid(){state.outcome=Some(Err(code));unsafe{DestroyWindow(hwnd);}return 0;}}
                WM_COMMAND=>{
                    // Only this original Edit and native Button. Webview has no
                    // window message bridge, AUTHORIZE payload or approval IPC.
                    if wparam & 0xffff==1 && lparam as HWND==state.confirm && wparam>>16==BN_CLICKED as usize {
                        let mut value=vec![0u16;512];
                        let count=unsafe{GetWindowTextW(state.edit,value.as_mut_ptr(),value.len()as i32)};
                        if count>0 && String::from_utf16(&value[..count as usize]).ok().as_deref()==Some(state.challenge) {
                            match invalid(){Ok(())=>state.outcome=Some(Ok(NativeInput{accepted_at:Instant::now()})),Err(code)=>state.outcome=Some(Err(code))}
                            unsafe{DestroyWindow(hwnd);}return 0;
                        }
                    } else if wparam & 0xffff==2 {state.outcome=Some(Err("setup_declined"));unsafe{DestroyWindow(hwnd);}return 0;}
                }
                WM_CLOSE=>{state.outcome=Some(Err("setup_declined"));unsafe{DestroyWindow(hwnd);}return 0;}
                WM_DESTROY=>{unsafe{PostQuitMessage(0);}return 0;}
                _=>{}
            }
        }
        unsafe{DefWindowProcW(hwnd,message,wparam,lparam)}
    }
    pub(crate) struct TrustInput { pub(crate) accepted_at:Instant }
    pub(crate) struct RecordInput { pub(crate) accepted_at:Instant }
    pub(crate) fn show_record(parent:usize,details:&str,deadline:Instant,check:&dyn Fn()->Result<(),&'static str>)->Result<RecordInput,&'static str>{
        let input=show_with_title(parent,details,"AUTHORIZE",deadline,check,"确认本机安装验证结果")?;
        Ok(RecordInput{accepted_at:input.accepted_at})
    }
    pub(crate) fn show_trust(parent:usize,details:&str,deadline:Instant,check:&dyn Fn()->Result<(),&'static str>)->Result<TrustInput,&'static str>{
        let input=show_with_title(parent,details,"AUTHORIZE",deadline,check,"确认本机安装来源")?;
        Ok(TrustInput{accepted_at:input.accepted_at})
    }
    pub(crate) fn show(parent:usize,details:&str,challenge:&str,deadline:Instant,check:&dyn Fn()->Result<(),&'static str>)->Result<NativeInput,&'static str>{
        show_with_title(parent,details,challenge,deadline,check,"确认本次创作设置")
    }
    fn show_with_title(parent:usize,details:&str,challenge:&str,deadline:Instant,check:&dyn Fn()->Result<(),&'static str>,title:&str)->Result<NativeInput,&'static str>{
        let session=interactive_session()?;check()?;
        if details.contains('\0')||challenge.contains('\0')||challenge.encode_utf16().count()>510{return Err("setup_dialog_invalid");}
        let parent=parent as HWND;let mut parent_pid=0;
        if parent.is_null()||unsafe{GetWindowThreadProcessId(parent,&mut parent_pid)}==0||parent_pid!=unsafe{GetCurrentProcessId()}{return Err("setup_dialog_parent_denied");}
        let class=wide("VideoCreatorOwnerSetupV1");let module=unsafe{GetModuleHandleW(null())};
        static REGISTERED:OnceLock<bool>=OnceLock::new();
        let registered=*REGISTERED.get_or_init(||{
            let mut value:WNDCLASSW=unsafe{zeroed()};value.lpfnWndProc=Some(procedure);value.hInstance=module;value.lpszClassName=class.as_ptr();
            (unsafe{RegisterClassW(&value)})!=0
        });
        if !registered{return Err("setup_dialog_class_failed");}
        let mut state=WindowState{challenge,edit:null_mut(),confirm:null_mut(),check,deadline,outcome:None};
        let hwnd=unsafe{CreateWindowExW(WS_EX_DLGMODALFRAME,class.as_ptr(),wide(title).as_ptr(),
            WS_OVERLAPPED|WS_CAPTION|WS_SYSMENU|WS_VISIBLE,CW_USEDEFAULT,CW_USEDEFAULT,820,730,parent,null_mut(),module,(&mut state as *mut WindowState<'_>).cast())};
        if hwnd.is_null(){return Err("setup_dialog_create_failed");}
        let create=|class:&str,text:&str,style:u32,x:i32,y:i32,width:i32,height:i32,id:usize|unsafe{
            CreateWindowExW(0,wide(class).as_ptr(),wide(text).as_ptr(),WS_CHILD|WS_VISIBLE|style,x,y,width,height,hwnd,id as HMENU,module,null())};
        let details_window=create("EDIT",details,WS_BORDER|WS_VSCROLL|ES_MULTILINE as u32|ES_READONLY as u32|ES_AUTOVSCROLL as u32,20,20,760,485,0);
        let instructions=create("STATIC",&format!("请核对完整范围。只有在此系统窗口键入下列确认句，再点击“确认并继续”才会继续：\r\n{challenge}"),0,20,515,760,55,0);
        state.edit=create("EDIT","",WS_BORDER|WS_TABSTOP|ES_AUTOHSCROLL as u32,20,580,760,30,3);
        state.confirm=create("BUTTON","确认并继续",WS_TABSTOP|BS_DEFPUSHBUTTON as u32,580,625,200,35,1);
        let cancel=create("BUTTON","暂不确认",WS_TABSTOP,380,625,175,35,2);
        if [details_window,instructions,state.edit,state.confirm,cancel].iter().any(|h|h.is_null())||unsafe{SetTimer(hwnd,1,250,None)}==0 {
            unsafe{DestroyWindow(hwnd);}return Err("setup_dialog_controls_failed");
        }
        unsafe{EnableWindow(parent,0);SetFocus(state.edit);}
        let outcome=(||{let mut message:MSG=unsafe{zeroed()};loop{
            let result=unsafe{GetMessageW(&mut message,null_mut(),0,0)};
            if result==-1{return Err("setup_dialog_message_failed");}if result==0{break;}
            if unsafe{IsDialogMessageW(hwnd,&message)}==0{unsafe{TranslateMessage(&message);DispatchMessageW(&message);}}
        }
        let result=state.outcome.take().ok_or("setup_dialog_unknown")?;
        if interactive_session()?!=session{return Err("setup_session_changed");}check()?;result})();
        unsafe{KillTimer(hwnd,1);if IsWindow(hwnd)!=0{DestroyWindow(hwnd);}EnableWindow(parent,1);}
        outcome
    }
}
#[cfg(windows)]
pub(crate) use windows::{interactive_session,show,show_trust,show_record,TrustInput,RecordInput};
