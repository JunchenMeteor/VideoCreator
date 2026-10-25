//! Trusted indexed pre-API launch. Proposals and facts never issue Evidence.
use std::{fs::{File,OpenOptions},io::{Read,Write},path::{Path,PathBuf},sync::{Arc,Mutex,mpsc},thread::{self,JoinHandle},time::{Duration,Instant}};
use sha2::{Digest,Sha256};
use serde_json::{json,Value};
use crate::{owner_setup::{PrepareInput,SetupAttempt,SetupDriver,FRAME_LIMIT},native_installation::NativeInstallationGuards,
    load_policy::PreparedLaunch,platform::OwnedProcess,resource_authority::PendingInstallationObserver};

#[derive(Clone)]
pub(crate) struct InstalledSetupDriver {
    installation:Arc<NativeInstallationGuards>,resources:Arc<crate::engine::LaunchResources>,
    instance:PathBuf,parent:usize,options:Value,_control:Arc<crate::resource_pins::ResourcePins>,directory:Arc<crate::owner_setup_directory::OwnerDirectory>,
    trust_materials:Option<Arc<crate::installation_trust::TrustMaterials>>,
    qualification_candidate:Option<Arc<crate::qualification_pack::VerifiedQualificationCandidate>>,
    registry:Arc<Mutex<Option<Arc<crate::qualification_registry::QualificationRegistry>>>>,
}
impl InstalledSetupDriver {
    pub(crate) fn create(installation:Arc<NativeInstallationGuards>,control:Arc<crate::resource_pins::ResourcePins>,resources:Arc<crate::engine::LaunchResources>,instance:&Path,parent:usize)->Result<Arc<Self>,&'static str>{
        Self::create_using(installation,control,resources,instance,parent,None,None)
    }
    pub(crate) fn create_with_trust(installation:Arc<NativeInstallationGuards>,control:Arc<crate::resource_pins::ResourcePins>,resources:Arc<crate::engine::LaunchResources>,instance:&Path,parent:usize)->Result<Arc<Self>,&'static str>{
        let materials=Arc::new(crate::installation_trust::TrustMaterials::hold(&installation)?);
        Self::create_using(installation,control,resources,instance,parent,Some(materials),None)
    }
    pub(crate) fn create_with_qualification(installation:Arc<NativeInstallationGuards>,control:Arc<crate::resource_pins::ResourcePins>,resources:Arc<crate::engine::LaunchResources>,instance:&Path,parent:usize)->Result<Arc<Self>,&'static str>{
        let materials=Arc::new(crate::installation_trust::TrustMaterials::hold(&installation)?);
        let candidate=crate::qualification_pack::VerifiedQualificationCandidate::hold(installation.clone(),materials.clone(),&resources)?;
        Self::create_using(installation,control,resources,instance,parent,Some(materials),Some(candidate))
    }
    pub(crate) fn current_registry(&self)->Result<Arc<crate::qualification_registry::QualificationRegistry>,&'static str>{
        self.registry.lock().map_err(|_|"qualification_registry_busy")?.clone().ok_or("qualification_unavailable")
    }
    fn create_using(installation:Arc<NativeInstallationGuards>,control:Arc<crate::resource_pins::ResourcePins>,resources:Arc<crate::engine::LaunchResources>,instance:&Path,parent:usize,trust_materials:Option<Arc<crate::installation_trust::TrustMaterials>>,qualification_candidate:Option<Arc<crate::qualification_pack::VerifiedQualificationCandidate>>)->Result<Arc<Self>,&'static str>{
        if !Arc::ptr_eq(&installation.payload,&resources.pins){return Err("owner_setup_resource_owner_mismatch");}
        installation.image_is_current_process()?;
        let identity=crate::resource_authority::current_identity()?;
        let directory=Arc::new(crate::owner_setup_directory::OwnerDirectory::hold(instance,&identity.sid)?);
        // Complete finite Backend SetupPreparationOptions, included in the
        // original full payload map. This is a proposal, not policy authority.
        // Missing real producer input is an explicit source/artifact gap.
        let raw=installation.payload.read_held_bytes("SetupPreparationOptions.json",FRAME_LIMIT-16384)?;
        let options:Value=serde_json::from_slice(&raw).map_err(|_|"owner_setup_options_invalid")?;
        if crate::native_installation::canonical(&options)?!=raw||options["format"]!="owner-setup-preparation-options-v1"{return Err("owner_setup_options_invalid");}
        let observed=installation.observe()?;installation.assert_current(&observed)?;drop(observed);
        Ok(Arc::new(Self{installation,resources,instance:instance.to_owned(),parent,options,_control:control,directory,trust_materials,qualification_candidate,registry:Arc::new(Mutex::new(None))}))
    }
    fn launch(&self,input:PrepareInput,events:Arc<SetupAttempt>)->Result<(),&'static str>{
        let trust=match &self.trust_materials{Some(materials)=>Some(crate::installation_trust::InstallationTrustProducer::prepare_trust(
            self.installation.clone(),self._control.clone(),self.resources.clone(),self.directory.clone(),self.parent,materials.clone())?),None=>None};
        let record_input=match(&trust,&self.qualification_candidate){(Some(trust),Some(candidate))=>Some(crate::installation_record::InstallationRecordProducer::prepare_record_input(trust,candidate.clone(),self.parent)?),(None,Some(_))=>return Err("installation_record_original_source_required"),_=>None};
        let role=if record_input.is_some(){crate::load_policy::ChildRole::OwnerSetupQualifiedInstall}else if trust.is_some(){crate::load_policy::ChildRole::OwnerSetupTrust}else{crate::load_policy::ChildRole::OwnerSetup};
        let mut prepared=self.resources.prepare_role(role,&self.instance,None,
            vec!["--data-dir".into(),crate::load_policy::text(&self.instance)?])?;
        if let Some(candidate)=&self.qualification_candidate{candidate.assert_target_current(&prepared.source_carrier.context)?;}
        let request=crate::native_installation::canonical(&json!({"format":"owner-setup-preparation-request-v1","idempotency_key":input.idempotency_key,"goal":input.goal,"options":self.options}))?;
        if request.len()>FRAME_LIMIT-16384{return Err("owner_setup_request_oversized");}
        let initialization=crate::owner_setup_initialize::PendingInitialization::create(self.installation.clone(),self.directory.clone())?;
        let record=crate::native_installation::canonical(&json!({"format":"native-owner-instance-initialization-v1","bootstrap_locator":initialization.locator(),
            "installation_inputs":self.installation.inputs,"external_receipt_path":crate::load_policy::text(self.installation.receipt_path())?,
            "expected_host_image":self.installation.inputs.installed_native_image,"expected_host_sha256":self.installation.inputs.installed_native_image_sha256}))?;
        if record.len()>FRAME_LIMIT{return Err("owner_setup_record_oversized");}
        let carrier=self.instance.join("Temp").join(format!("OwnerSetup-{}.json",crate::resource_authority::private_startup_id()?));
        {let mut file=OpenOptions::new().write(true).create_new(true).open(&carrier).map_err(|_|"owner_setup_carrier_failed")?;
            file.write_all(&record).and_then(|_|file.sync_all()).map_err(|_|"owner_setup_carrier_failed")?;}
        use std::os::windows::fs::OpenOptionsExt;
        let held=OpenOptions::new().read(true).share_mode(1).custom_flags(0x0020_0000).open(&carrier).map_err(|_|"owner_setup_carrier_failed")?;
        let mut actual=Vec::new();(&held).take(FRAME_LIMIT as u64+1).read_to_end(&mut actual).map_err(|_|"owner_setup_carrier_failed")?;
        if actual!=record{return Err("owner_setup_carrier_changed");}
        let separator=prepared.args.iter().position(|v|v=="--").ok_or("owner_setup_bootstrap_invalid")?;
        prepared.args.splice(separator..separator,["--native-startup-binding".into(),crate::load_policy::text(&carrier)?,"--native-startup-binding-sha256".into(),format!("{:x}",Sha256::digest(&record))]);
        let deadline=Instant::now()+Duration::from_secs(20);
        let(initialization_registration,current_rx,initialization_thread)=initialization.start(deadline)?;
        let started=match prepared.launch_owned(){Ok(result)=>result,Err(code)=>{drop(initialization_registration);let _=initialization_thread.join();return Err(code);}};
        let process=Arc::new(Mutex::new(started.process));
        // Ownership is established before any post-Create fallible operation.
        let mut owned=OwnedSetupRun{process:process.clone(),_prepared:started.prepared,_installation:self.installation.clone(),_carrier:held,
            sessions:vec![initialization_thread],stderr:None,stdout:None,stdin:None,trust_action:None,record_action:None,registry:None,continuation:None};
        initialization_registration.send(process.clone()).map_err(|_|"owner_setup_registration_failed")?;
        let(output,error)=process.lock().map_err(|_|"owner_setup_process_busy")?.take_output()?;
        owned.stderr=Some(thread::spawn(move||drain(error)));
        let(output_tx,output_rx)=mpsc::sync_channel(1);
        owned.stdout=Some(thread::spawn(move||read_frames(output,output_tx)));
        let source=current_rx.recv_timeout(deadline.saturating_duration_since(Instant::now())).map_err(|_|"owner_instance_handshake_timeout")?;
        source.assert_current()?;
        let ready=receive_frame(&output_rx,deadline)?.ok_or("owner_instance_handshake_incomplete")?;
        let instance=handshake(&ready,"instance_ready",1)?.to_owned();
        source.assert_current()?;
        let observer=PendingInstallationObserver::create(self.installation.clone(),&instance)?;
        let confirmation=crate::owner_setup_channel::PendingSetupChannel::create(self.installation.clone(),self.directory.clone(),&instance,events.clone(),self.parent,input.goal)?;
        let startup=json!({"format":"native-owner-installation-startup-v1","instance_id":instance,"installation_inputs":self.installation.inputs,
            "external_receipt_path":crate::load_policy::text(self.installation.receipt_path())?,"expected_host_image":self.installation.inputs.installed_native_image,"expected_host_sha256":self.installation.inputs.installed_native_image_sha256});
        let bind=crate::native_installation::canonical(&json!({"wire":"native-owner-instance-handshake-v1","event":"bind_setup","seq":2,"startup_record":startup,"installation_locator":observer.locator(),"confirmation_locator":confirmation.locator()}))?;
        if bind.len()>FRAME_LIMIT{return Err("owner_instance_handshake_limit");}
        let(installation_registration,installation_thread)=observer.start()?;owned.sessions.push(installation_thread);
        installation_registration.register(process.clone())?;
        let(confirmation_registration,confirmation_thread)=confirmation.start()?;owned.sessions.push(confirmation_thread);
        confirmation_registration.send(process.clone()).map_err(|_|"owner_setup_registration_failed")?;
        let input_file=process.lock().map_err(|_|"owner_setup_process_busy")?.stdin.take().ok_or("owner_setup_stdin_missing")?;
        let(input_tx,input_rx)=mpsc::sync_channel(1);owned.stdin=Some(thread::spawn(move||write_frames(input_file,input_rx)));
        source.assert_current()?;send_frame(&input_tx,bind,deadline)?;
        let bound=receive_frame(&output_rx,deadline)?.ok_or("owner_instance_handshake_incomplete")?;
        if handshake(&bound,"setup_bound",2)?!=instance{return Err("owner_instance_binding_changed");}
        source.assert_current()?;
        if let Some(trust)=trust{
            let bound=trust.bind_instance(process.clone(),source.clone(),&instance)?;
            owned.trust_action=Some(bound.original());
            let trust_frame=crate::native_installation::canonical(&json!({"wire":"native-owner-instance-trust-handshake-v1","event":"admit_installation_trust","seq":3,"instance_id":instance,"locator":bound.locator()}))?;
            if trust_frame.len()>FRAME_LIMIT{return Err("installation_trust_frame_limit");}
            owned.sessions.push(bound.start()?);
            let trust_deadline=Instant::now()+Duration::from_secs(10);
            send_frame(&input_tx,trust_frame,trust_deadline)?;
            let committed=receive_frame(&output_rx,trust_deadline)?.ok_or("installation_trust_outcome_unknown")?;
            if trust_handshake(&committed)?!=instance{return Err("installation_trust_binding_changed");}
            source.assert_current()?;
            if let Some(record_input)=record_input{
                let trust=crate::qualification_commit::CommittedTrustSource::read(owned.trust_action.as_ref().ok_or("installation_trust_original_missing")?.clone(),&self.instance)?;
                let bound=record_input.bind(trust)?;let action=bound.original();owned.record_action=Some(action.clone());
                let frame=crate::native_installation::canonical(&json!({"wire":"native-owner-instance-record-handshake-v1","event":"admit_installation_record","seq":4,"instance_id":instance,"locator":bound.locator()}))?;
                if frame.len()>FRAME_LIMIT{return Err("installation_record_frame_limit");}
                owned.sessions.push(bound.start()?);let deadline=Instant::now()+Duration::from_secs(10);
                send_frame(&input_tx,frame,deadline)?;
                let committed=receive_frame(&output_rx,deadline)?.ok_or("installation_record_outcome_unknown")?;
                record_handshake(&committed,"installation_record_committed",4,&instance)?;
                let verified=crate::qualification_commit::CommittedQualificationSource::read(action.clone(),owned._prepared.source_carrier.context.clone())?;
                let reference=action.candidate().record.reference()?;let revision=verified.registry_revision();
                if committed["action_id"]!=action.action_id()||committed["record_ref"]!=serde_json::to_value(&reference).map_err(|_|"installation_record_frame_invalid")?||committed["registry_revision"].as_u64()!=Some(revision){return Err("installation_record_changed");}
                let registry=crate::qualification_registry::QualificationRegistry::new(self.installation.clone(),&instance)?;
                registry.install_committed(verified,deadline)?;owned.registry=Some(registry.clone());
                let frame=crate::native_installation::canonical(&json!({"wire":"native-owner-instance-record-handshake-v1","event":"installation_record_current","seq":5,"instance_id":instance,"action_id":action.action_id(),"record_ref":reference,"registry_revision":revision}))?;
                let deadline=Instant::now()+Duration::from_secs(10);send_frame(&input_tx,frame,deadline)?;
                let ready=receive_frame(&output_rx,deadline)?.ok_or("installation_record_outcome_unknown")?;
                record_handshake(&ready,"installation_record_ready",5,&instance)?;
                source.assert_current()?;
                *self.registry.lock().map_err(|_|"qualification_registry_busy")?=Some(registry.clone());
                let continuation=self.resources.hold_setup_api_continuation(&owned._prepared,&action.candidate().record)?;
                let deadline=Instant::now()+Duration::from_secs(10);registry.assert_setup_continuation(&continuation,deadline)?;
                let context=crate::resource_authority::FactsContext{instance_id:instance.clone(),role:"api".into(),
                    registration_sha256:self.installation.inputs.registration_sha256.clone(),resource_manifest_sha256:self.installation.inputs.resource_manifest_sha256.clone(),runtime_manifest_sha256:self.installation.inputs.runtime_manifest_sha256.clone()};
                let pending=crate::qualified_authority::PendingQualifiedAuthority::create_qualified(registry.clone(),continuation.image(),context)?;
                let locator=serde_json::to_value(pending.locator()).map_err(|_|"setup_production_frame_invalid")?;
                // Original strong member is retained before any fallible spawn.
                owned.continuation=Some(continuation);
                let(registration,session)=pending.start()?;owned.sessions.push(session);registration.register(process.clone())?;
                let startup=json!({"format":"native-startup-binding-v1","instance_id":instance,"role":"api",
                    "installed_native_image":self.installation.inputs.installed_native_image,"installed_native_image_sha256":self.installation.inputs.installed_native_image_sha256,
                    "registration_sha256":self.installation.inputs.registration_sha256,"resource_manifest_sha256":self.installation.inputs.resource_manifest_sha256,"runtime_manifest_sha256":self.installation.inputs.runtime_manifest_sha256,
                    "expected_files":self.installation.inputs.expected_files,"engine_file_names":self.installation.inputs.engine_file_names});
                let frame=crate::native_installation::canonical(&json!({"wire":"native-owner-setup-production-carry-v1","event":"bind_production","seq":6,"instance_id":instance,"startup_record":startup,"production_locator":locator}))?;
                if frame.len()>FRAME_LIMIT{return Err("setup_production_frame_limit");}
                let deadline=Instant::now()+Duration::from_secs(10);send_frame(&input_tx,frame,deadline)?;
                let bound=receive_frame(&output_rx,deadline)?.ok_or("setup_production_unknown")?;production_handshake(&bound,&instance)?;
                source.assert_current()?;registry.assert_setup_continuation(owned.continuation.as_ref().ok_or("setup_production_original_launch_required")?,deadline)?;
            }
        }
        send_frame(&input_tx,request,Instant::now()+Duration::from_secs(10))?;drop(input_tx);
        let service_deadline=Instant::now()+Duration::from_secs(720);
        let mut expected=0;let mut receipt=None;
        while let Some(value)=receive_frame(&output_rx,service_deadline)?{
            source.assert_current()?;
            if value["wire"]!="native-owner-setup-result-v1"||value.as_object().is_none_or(|map|map.len()!=3||!["wire","event","document"].iter().all(|key|map.contains_key(*key))){return Err("owner_setup_result_invalid");}
            match(expected,value["event"].as_str()){
                (0,Some("prepared"))=>events.prepared(value["document"]["goal"]["name"].as_str().ok_or("owner_setup_result_invalid")?)?,
                (1,Some("accepted"))=>events.applying(),
                (2,Some("goal_accepted"))=>receipt=Some(value["document"].clone()),
                _=>return Err("owner_setup_result_order_invalid"),
            }expected+=1;
        }
        let code=owned.wait_terminal()?;
        for session in owned.sessions.drain(..){session.join().map_err(|_|"owner_setup_session_panicked")??;}
        if let Some(reader)=owned.stderr.take(){reader.join().map_err(|_|"owner_setup_stderr_panicked")??;}
        if let Some(reader)=owned.stdout.take(){reader.join().map_err(|_|"owner_setup_stdout_panicked")??;}
        if let Some(writer)=owned.stdin.take(){writer.join().map_err(|_|"owner_setup_stdin_panicked")??;}
        if code!=0||expected!=3{return Err("owner_setup_execution_failed");}
        events.completed(receipt.ok_or("owner_setup_receipt_missing")?);Ok(())
    }
}
impl SetupDriver for InstalledSetupDriver {
    fn start(&self,input:PrepareInput,events:Arc<SetupAttempt>)->Result<(),&'static str>{
        let driver=self.clone();let failed=events.clone();
        thread::Builder::new().name("indexed-owner-setup-child".into()).spawn(move||{
            if let Err(code)=driver.launch(input,events){failed.failed(code);eprintln!("{}",json!({"event":"native_setup_failed","code":code}));}
        }).map_err(|_|"owner_setup_launch_thread_failed")?;Ok(())
    }
}
fn drain(mut file:File)->Result<(),&'static str>{drain_bytes(&mut file)}
fn drain_bytes(file:&mut File)->Result<(),&'static str>{let mut bytes=[0;65536];loop{if file.read(&mut bytes).map_err(|_|"owner_setup_stream_failed")?==0{return Ok(());}}}
type Frame=Result<Option<Value>,&'static str>;
fn read_frames(mut file:File,sender:mpsc::SyncSender<Frame>)->Result<(),&'static str>{
    let result=(||{loop{
        let mut header=[0u8;4];if file.read(&mut header[..1]).map_err(|_|"owner_setup_stdout_failed")?==0{let _=sender.send(Ok(None));return Ok(());}
        file.read_exact(&mut header[1..]).map_err(|_|"owner_setup_stdout_incomplete")?;
        let size=u32::from_le_bytes(header)as usize;if size==0||size>FRAME_LIMIT{return Err("owner_setup_result_oversized");}
        let mut bytes=vec![0;size];file.read_exact(&mut bytes).map_err(|_|"owner_setup_stdout_incomplete")?;
        let value:Value=serde_json::from_slice(&bytes).map_err(|_|"owner_setup_result_invalid")?;
        if crate::native_installation::canonical(&value)?!=bytes{return Err("owner_setup_result_invalid");}
        if sender.send(Ok(Some(value))).is_err(){return drain_bytes(&mut file);}
    }})();
    if let Err(code)=result{let _=sender.send(Err(code));let _=drain_bytes(&mut file);}result
}
fn receive_frame(receiver:&mpsc::Receiver<Frame>,deadline:Instant)->Frame{
    if Instant::now()>=deadline{return Err("owner_instance_handshake_timeout");}
    let value=receiver.recv_timeout(deadline.saturating_duration_since(Instant::now())).map_err(|_|"owner_setup_result_unknown")??;
    if Instant::now()>=deadline{return Err("owner_instance_handshake_timeout");}Ok(value)
}
fn handshake<'a>(value:&'a Value,event:&str,sequence:u64)->Result<&'a str,&'static str>{
    if value["wire"]!="native-owner-instance-handshake-v1"||value["seq"].as_u64()!=Some(sequence)||crate::native_installation::canonical(value)?.len()>16*1024{return Err("owner_instance_handshake_invalid");}
    if value["event"]=="error"{
        let code=value["code"].as_str().filter(|code|!code.is_empty()&&code.len()<=128&&code.bytes().all(|byte|byte.is_ascii_lowercase()||byte.is_ascii_digit()||byte==b'_')).ok_or("owner_instance_handshake_invalid")?;
        let status=value["status"].as_u64().filter(|status|(400..=599).contains(status)).ok_or("owner_instance_handshake_invalid")?;
        if value.as_object().is_none_or(|map|map.len()!=5||!["wire","event","seq","code","status"].iter().all(|key|map.contains_key(*key))){return Err("owner_instance_handshake_invalid");}
        // Preserve the unique Backend migration/schema/source error without
        // logging a Goal, locator, credential, path or arbitrary detail body.
        eprintln!("{}",json!({"event":"native_setup_backend_failed","code":code,"status":status,"seq":sequence}));
        return Err(match(code,status){("owner_instance_handshake_invalid",422)=>"owner_instance_handshake_invalid",("owner_instance_handshake_limit",413)=>"owner_instance_handshake_limit",("owner_instance_source_denied",403)=>"owner_instance_source_denied",("owner_instance_binding_changed",409)=>"owner_instance_binding_changed",("owner_instance_handshake_timeout",503)=>"owner_instance_handshake_timeout",("owner_instance_source_unavailable",503)=>"owner_instance_source_unavailable",_=>"owner_instance_reported_failure"});
    }
    if value["event"]!=event
        ||value.as_object().is_none_or(|map|map.len()!=4||!["wire","event","seq","instance_id"].iter().all(|key|map.contains_key(*key)))
        {return Err("owner_instance_handshake_invalid");}
    value["instance_id"].as_str().filter(|id|!id.is_empty()&&id.len()<=128).ok_or("owner_instance_handshake_invalid")
}
type WriteFrame=(Vec<u8>,mpsc::SyncSender<Result<(),&'static str>>);
fn trust_handshake(value:&Value)->Result<&str,&'static str>{
    if value["wire"]!="native-owner-instance-trust-handshake-v1"||value["seq"].as_u64()!=Some(3){return Err("installation_trust_handshake_invalid");}
    if value["event"]=="error"{
        if value.as_object().is_none_or(|map|map.len()!=5||!["wire","event","seq","code","status"].iter().all(|key|map.contains_key(*key))){return Err("installation_trust_handshake_invalid");}
        return Err(match(value["code"].as_str(),value["status"].as_u64()){
            (Some("installation_trust_source_denied"),Some(403))=>"installation_trust_source_denied",
            (Some("installation_trust_changed"),Some(409))=>"installation_trust_changed",
            (Some("installation_trust_frame_invalid"),Some(422))=>"installation_trust_frame_invalid",
            (Some("installation_trust_timeout"),Some(503))=>"installation_trust_timeout",
            (Some("installation_trust_unavailable"),Some(503))=>"installation_trust_unavailable",
            _=>"installation_trust_reported_failure"});
    }
    if value["event"]!="installation_trust_committed"||value.as_object().is_none_or(|map|map.len()!=4||!["wire","event","seq","instance_id"].iter().all(|key|map.contains_key(*key))){return Err("installation_trust_handshake_invalid");}
    value["instance_id"].as_str().filter(|id|!id.is_empty()&&id.len()<=128).ok_or("installation_trust_handshake_invalid")
}
fn record_handshake(value:&Value,event:&str,seq:u64,instance:&str)->Result<(),&'static str>{
    if value["wire"]!="native-owner-instance-record-handshake-v1"||value["seq"].as_u64()!=Some(seq){return Err("installation_record_frame_invalid");}
    if value["event"]=="error"{
        if value.as_object().is_none_or(|map|map.len()!=5||!["wire","event","seq","code","status"].iter().all(|key|map.contains_key(*key))){return Err("installation_record_frame_invalid");}
        return Err(match(value["code"].as_str(),value["status"].as_u64()){
            (Some("installation_record_frame_invalid"),Some(422))=>"installation_record_frame_invalid",(Some("installation_record_frame_limit"),Some(413))=>"installation_record_frame_limit",
            (Some("installation_record_source_denied"),Some(403))=>"installation_record_source_denied",(Some("installation_record_changed"),Some(409))=>"installation_record_changed",
            (Some("installation_record_conflict"),Some(409))=>"installation_record_conflict",(Some("installation_record_unavailable"),Some(503))=>"installation_record_unavailable",
            (Some("installation_record_unknown"),Some(503))=>"installation_record_unknown",(Some("installation_record_timeout"),Some(503))=>"installation_record_timeout",_=>"installation_record_reported_failure"});
    }
    let keys:&[&str]=if seq==4{&["wire","event","seq","instance_id","action_id","record_ref","registry_revision"]}else{&["wire","event","seq","instance_id"]};
    if value["event"]!=event||value["instance_id"]!=instance||value.as_object().is_none_or(|map|map.len()!=keys.len()||!keys.iter().all(|key|map.contains_key(*key))){return Err("installation_record_frame_invalid");}Ok(())
}
fn production_handshake(value:&Value,instance:&str)->Result<(),&'static str>{
    if value["wire"]!="native-owner-setup-production-carry-v1"||value["seq"].as_u64()!=Some(6){return Err("setup_production_frame_invalid");}
    if value["event"]=="error"{
        if value.as_object().is_none_or(|map|map.len()!=5||!["wire","event","seq","code","status"].iter().all(|key|map.contains_key(*key))){return Err("setup_production_frame_invalid");}
        return Err(match(value["code"].as_str(),value["status"].as_u64()){
            (Some("setup_production_frame_invalid"),Some(422))=>"setup_production_frame_invalid",(Some("setup_production_frame_limit"),Some(413))=>"setup_production_frame_limit",
            (Some("setup_production_source_denied"),Some(403))=>"setup_production_source_denied",(Some("setup_production_binding_changed"),Some(409))=>"setup_production_binding_changed",
            (Some("setup_production_unavailable"),Some(503))=>"setup_production_unavailable",(Some("setup_production_unknown"),Some(503))=>"setup_production_unknown",
            (Some("setup_production_timeout"),Some(503))=>"setup_production_timeout",_=>"setup_production_reported_failure"});
    }
    if value["event"]!="production_bound"||value["instance_id"]!=instance||value.as_object().is_none_or(|map|map.len()!=4||!["wire","event","seq","instance_id"].iter().all(|key|map.contains_key(*key))){return Err("setup_production_frame_invalid");}Ok(())
}
fn write_frames(mut file:File,receiver:mpsc::Receiver<WriteFrame>)->Result<(),&'static str>{
    for(bytes,reply)in receiver{let result=file.write_all(&(bytes.len()as u32).to_le_bytes()).and_then(|_|file.write_all(&bytes)).and_then(|_|file.flush()).map_err(|_|"owner_setup_request_write_failed");let _=reply.send(result);result?;}Ok(())
}
fn send_frame(sender:&mpsc::SyncSender<WriteFrame>,bytes:Vec<u8>,deadline:Instant)->Result<(),&'static str>{
    if Instant::now()>=deadline{return Err("owner_instance_handshake_timeout");}let(tx,rx)=mpsc::sync_channel(1);sender.send((bytes,tx)).map_err(|_|"owner_setup_request_write_failed")?;
    rx.recv_timeout(deadline.saturating_duration_since(Instant::now())).map_err(|_|"owner_instance_handshake_timeout")??;
    if Instant::now()>=deadline{return Err("owner_instance_handshake_timeout");}Ok(())
}
struct OwnedSetupRun {
    process:Arc<Mutex<OwnedProcess>>,_prepared:PreparedLaunch,_installation:Arc<NativeInstallationGuards>,_carrier:File,
    sessions:Vec<JoinHandle<Result<(),&'static str>>>,stderr:Option<JoinHandle<Result<(),&'static str>>>,stdout:Option<JoinHandle<Result<(),&'static str>>>,stdin:Option<JoinHandle<Result<(),&'static str>>>,
    trust_action:Option<Arc<crate::installation_trust::TrustAdmissionOriginal>>,
    record_action:Option<Arc<crate::installation_record::RecordAdmissionOriginal>>,
    registry:Option<Arc<crate::qualification_registry::QualificationRegistry>>,
    continuation:Option<crate::load_policy::SetupApiContinuation>,
}
impl OwnedSetupRun {
    fn wait_terminal(&self)->Result<u32,&'static str>{
        loop{let owned=self.process.lock().map_err(|_|"owner_setup_process_busy")?;
            if let Some(code)=owned.wait_exit(100)?{if owned.job_pids()?.is_empty(){return Ok(code);}}drop(owned);thread::sleep(Duration::from_millis(20));}
    }
}
impl Drop for OwnedSetupRun {
    fn drop(&mut self){
        // Failed exchange/EOF/window closure cannot release the actual launch.
        // This is owned Job cleanup, never a PID enumeration/kill substitute.
        if let Ok(owned)=self.process.lock(){let _=owned.force();}
        loop{let terminal=self.process.lock().is_ok_and(|owned|owned.wait_exit(100).is_ok_and(|code|code.is_some())&&owned.job_pids().is_ok_and(|pids|pids.is_empty()));if terminal{break;}thread::sleep(Duration::from_millis(20));}
        for session in self.sessions.drain(..){let _=session.join();}
        if let Some(reader)=self.stderr.take(){let _=reader.join();}
        if let Some(reader)=self.stdout.take(){let _=reader.join();}
        if let Some(writer)=self.stdin.take(){let _=writer.join();}
    }
}
