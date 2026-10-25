# ADR 0065：独立角色归因、当前父素材读取与冷启动验证

状态：DESIGN_ONLY_READY_FOR_INDEPENDENT_REVIEW。仅批准形成待独评的确定合同，不授产品执行、资源资格、收费或finding关闭。实施须由原Review独评后交原Backend、Media、Integration；当前没有运行/性能/三OS验收证据。

本增量只覆盖MDG01、MDG02、MDG04。旧0060—0064原字节、旧single-method记录、原诊断/selected两writer、完整verify、两次实际authority、Owner/current/CAS/fence、原Operation/unknown/费用限次和200000us阈值保持。MDG03已有Media48接线，另行独审。本合同不采用尚未独评的0064后继认证方法。完整R1的多角色、四配方、音视频/文本/实际ASR/字幕/RAG/整包、三OS与连续R2不缩减；缺资源准确not_ready，不能把文档或安装sidecar当成功资源。

## 1. 已查实际接缝

基线是停止Media48和停止Backend130，不是正在0062变更的后端。普通文件身份、完整JSON目录和实际读取范围由同名Architecture过程InputPins保存。

| 固定源 | 实际事实 |
| --- | --- |
| Backend domain/component_diagnosis.py 20—231 | ObservationV1仅一个method_ref；FactV1同样单method；RegisteredInputs已有有限method_refs和每method独立analysis_intents。 |
| Backend component_diagnosis_service.py 151—225、375—599、723—785 | 原注册核安装来源/fullroute；每analysis Operation必须同一method原intent/inputSHA/route、succeeded/settled/实际费用；首次record及explicit reader只向verifier传inputs、observation、OperationObservation。 |
| Media providers/component_diagnosis.py 25—55、129—223及workflows/component_diagnosis.py 1—103 | 原driver一次模型调用产生director/editor/sound观点；不是三个独立agent。缓存_contexts留旧lease/completions；冷进程显式读无法恢复该缓存；verifier还限定len(operations)==1。 |
| Media autonomous_production.py 333—442、affected_production.py 186—302 | 初始及修订都以原Executor/Worker运行；master-index Step保存media_roles/source_steps，具体剪辑来源仍在真实生成Operation观察中。 |
| Media media/production_edit.py 30—257 | 成功结果已有有序source_clip_asset_ids、旁白或原mix/原video来源；三段微秒trim/concat、实际clip有无ambient、0.18 bed、48000Hz混音与复制video由实际FFmpeg路径决定。没有完整版本化shot/track lineage。 |
| Backend worker.py 574—634、affected_repair_service.py 195—365 | 原提交在全部源Operation成功且结算后核精确GeneratedFileManifest/持久allocation并登记Assets/Step；affected-master受真实command/源Step/当前issuer与短writer保护。没有供Media读取完整当前parent clip/track lineage的held口。 |

原_parent从assembly四masters生成source refs，不能把原固定production-shot Step或latest Operation当当前父镜头。clip的Worker allocation不是Bundle artifact，不能为满足DiagnosticSourceMediaRefV1.artifact_id伪造artifact ID。

## 2. MDG01：一个角色一个真实method/intent，有限组合

### 2.1 唯一新目录与版本

Backend唯一维护严格grammar和dispatcher，Media只消费：

- 保留diagnostic-methods-v1及registered-production-driver-resources-v3-diagnostic-v1的原parser/default/bytes。新增catalog `registered-component-diagnostic-methods-v2`；同ProductionDriverResources原三配方资源骨架新增显式wrapper `registered-production-driver-resources-v3-diagnostic-v2`。format不符/未知版本422，不将v1无声升级。
- V2 catalog字段仅format、methods（复用原ComponentDiagnosticMethodRegistrationV1，原1..16上限）、role_bindings。role_bindings按director、visual、sound、editor固定顺序，恰好四项；每项role_id、method_id、method_version。四项引用不同method，恰为本次四个独立角色；本版本其余methods只能明确登记为evidence，不能增加动态agent或自动选任意method。若配置evidence，追加一项role_id=evidence且唯一method；不用重复注册相同method。required角色不可缺省成三观点。
- 每method仍独立实际producer/source refs、template SHA、完整已验证route、model_binding/check_kinds。角色不同仅可改变已登记template/有限职责，不能增加管理scope/调用工具白名单。共享模型或route允许，method与原intent仍不同。注册按原method_ref完整内容哈希，role catalog和producer闭包实际受原resource/runtime SHA覆盖。
- 四角色作用：director核原主题/叙事目标；visual核原shot与真实图像/clip证据；sound核真实旁白/ambient/mix来源；editor核有序剪辑、保留素材、时钟及cover。每角色独立调用原Executor中的自己的method intent，保自己的输入、真实输出、费用/失败/limitations；可同一个模型，但不能拆一份回复伪造四次Operation。可用真实本地method或已准模型method；是否读到真实画面/波形与模型能力必须据证据申明。仅文本元数据不足时，相关语义保持undetermined，不能宣称看/听过内容。

### 2.2 输入、Observation、Fact的最小显式增量

完整父片段与角色必须进入不可变输入，不能偷偷修改旧source refs。新增严格`current-component-diagnostic-input-v3`和`registered-component-diagnostic-input-v3`：

- stable字段为原V2的binding、parent_preparation_id、parent_intent_sha256、candidate_manifest_file_sha256、creative_revision_refs、quality_ref、source_media_refs、audio_mappings、precision_report_ref、diagnostic_method_refs、completion_source_refs，再增role_bindings和parent_edit_lineage_ref。
- completion_source_refs复用原CompletionRef union，初次允许空tuple，恢复必须保真实实际追加closure；parent_edit_lineage_ref为本合同§3原不可变DiagnosticMetadataRef，必需，不能None冒完整来源。四masters仍原DiagnosticSourceMediaRefV1；clips/tracks由lineage ref中的原AssetRecord和实际allocation/Operation关联表达，不伪造Bundle artifact。
- envelope仍stable+analysis_intents；Backend生成原step/input/dedupe/route/reserved_cost。input_key是该stable完整递归sorted/compact/UTF-8 canonical SHA，明确用原plan_payload_bytes/sha256等正确dict编码，不能调用仅支持BaseModel的engine.canonical(dict)，不改Goal全局canonical。旧V1/V2哈希/grammar不变。
- Held RegisteredComponentDiagnosisInputsV3复用原InputsV1全部成员，再加role_bindings、completion_source_refs、original_input_ref、parent_edit_sources（§3真实held对象）。各field由Backend源重建，不以JSON值当权源。
- 新Observation `current-component-diagnostic-observation-v2`仅format、input_key_sha256、method_observations（四角色按catalog顺序及可选evidence的原ObservationV1 tuple）、limitations。每nested V1一个完整method_ref和自己的analysis_operation_ids/checks/limitations；nested inputkey相同，method不重复，checks的身份为(method_id,method_version,check_id)，不能丢method后用重名check覆盖。
- 新Fact `current-component-diagnostic-fact-v2`保FactV1全部非单method归因字段；去除原method_ref/analysis_operation_refs/checks三个单method字段，改为role_bindings和method_results。每method_results项为role_id、method_ref、analysis_operation_refs（原AnalysisOperationRefV1）、checks（原CheckV1）、limitations。另保parent_edit_lineage_ref，result/failure_component/affected_artifacts/shot_ids/范围/uncertainty/infoRequests等原有限投影字段。不得同时在新Fact保一份无归因扁平checks。
- 原ComponentDiagnosisRefV1及record定位/有界body用作不可变opaque ref，内容SHA决定真实version；唯一reader显式dispatch FactV1/V2。RegisteredDiagnosis仅在Backend将fact扩为明确V1|V2，registered身份保持，不新建平行diagnosis数据库。旧record原byte读取不重写；selected/publication两writer必须共同接受同一个dispatcher，不从不认识version默认空checks。

### 2.3 实际执行及守卫

原prepare负责一次登记全部需要的method intents；同Run原budget、每Op reserved/actual、同input唯一性和原analysis限次规则不变。增加真实角色可能使总reservation超过余额/预算，必须在原账本真实拒绝/等待，不能用零成本或一笔消费遮四次调用；不能给每角色新Run预算。已准有限catalog定义一轮角色组合，限次按原规则记录组合attempt及其实际各Op，不能逐角色换inputkey重置。

Media `select_method` V1保原路径；新增 `select_methods(inputs_v3)`只按真实held role_bindings返回有序(method_ref,原OperationIntent)。任何missing/duplicate/未登记method/完整inputSHA或route不符拒绝。原begin_step/Executor/Step commit分别完成每method，未知任一Op保needs_reconciliation，不发新key；已成功且结算的角色从原Observation读取，冷重启不重收费。

Backend `_diagnostic_operation_facts`按每nested Observation严格应用原全部限制，且Operation不能归两个角色。每method checks必须实际引用自己的真实输出和允许source/sample/completion，不能借另一method的输出冒本method看/听。每completion必须有明确真实消耗（可被多个角色引用），整个组合不能遗落completion；不强迫每角色声称消费其无需的资源。

统一verifier逐method原有限producer验证，再Backend确定性投影：supported differs的多个组件、undetermined/冲突或来源缺损保持information_required；precision-only保timing_only，不能由时码误差归因TTS。只有真实证据支持唯一失败组件才component_repair。模型proposal、角色多数票或Fact均不授媒体；后续仍原整plan/human或真实Owner预授权、有限target/recipe、rights/current及两authority。

首次record/append复用原一input一immutable result和CAS：组合必须完整才record新Fact；部分已成功角色留原Steps/Operations，不凑缺项发布。原selected/publication、诊断恢复两writer和完整verify不新增第三selector；同input同body复用、不同body409。

## 3. MDG02：真实当前父剪辑来源

### 3.1 原producer补结果，不造生成权限

Media在实际FFmpeg edit成功Operation结果中增加严格`edit_lineage`，格式`production-edit-lineage-v1`。字段：format、recipe_id（四原recipe之一；None仅确切旧初始全编辑路径）、edit_request_body（实际传入driver的完整有限canonical对象，保原字段及原storyboard bytes）、edit_request_sha256、ordered_clips、audio_tracks、preserved_video_asset_id、preserved_mix_asset_id、timeline_duration_us、output_attempt_roles。

ordered_clips每项shot_id、asset_id、intrinsic_range、timeline_range；范围复用c.MediaRange，整数微秒、半开区间，原storyboard顺序，timeline累计真实剪辑duration。asset_id必须原driver实际读取的Asset。producer不能查询SQL或填入自称的source_operation_ids；Backend在规范化lineage时，初始按原真实request/已准storyboard的固定原生成Step/input/intent，修订按已登记command的exact picture/narration Step以及已认证父保留edge，从真实GeneratedFileManifest→allocation→Asset对应取得唯一原Operation IDs。该来源不能只按asset hash匹配所有历史Op，也不能据shot名称猜最新Step；ID仅由该原服务加入持久规范body和held结果。该列表描述实际图像/ambient来源；cover-only可没有重组clips，必须引用真实preserved video lineage。

audio_tracks每项track_id、kind（narration/clip_ambient/preserved_mix/silence）、asset_id或None、shot_ids、intrinsic_range、timeline_range、stream（audio:0或none）、gain_decimal、sample_rate_hz。复用实际轨道/clock事实；None只在真实clip probe无audio而实际FFmpeg anullsrc分支，不能为缺失旁白造silence。音源Operation IDs同样仅由Backend上述原Step/receipt关联取得，producer不造来源ID。每种gain/rate/filter语义必须和本次已准producer/source及实际recipe一致，不允许模型声明新DSP。原mix直接保留时明确preserved_mix，不把其内部speech/ambient伪装当前生成；继续沿该原mix的真实上一代来源读取。

output_attempt_roles只绑定原ordered GeneratedFileManifest的attempt_id→本次真实changed role；Backend commit后由原allocation+receipt映射真实Asset。Producer不得自指定最终AssetID。所有结果仍由原Executor写真实OperationObservation，Worker原_commit_generated_step在同事务核成功/结算/manifest/allocation并登记Asset/Step；不另发布同来源新master或绕原权限。

Backend对结果grammar与真实性的校验不能只有SHA：核原实际request、registered plan/storyboard body、真实recipe/command/step mapper、原fullroute/resource/source版本、每input Asset/probe/rights、所有实际outputs。初始inputSHA按原_generated公式从实际request/stage/body/route完整重算；affected inputSHA按原已登记完整command/mapper核，实际edit_request_body还必须等于由该command、当前父来源及真实子生成Steps唯一构造的原输入。哈希不授权。provider bytes/probes/hash检查SQL外，短writer保原lease、step、all op rows、allocation/receipts及current/rights重核；不以driver result的一段声明代这些事实。

### 3.2 唯一held读口和持久伴件

在原CurrentFinalEvidencePorts新增且只Backend实现：

`read_parent_edit_sources(ordinary_lease: c.LeaseGrant, preparation_id: str, *, continuation=None, execution=None) -> HeldParentEditSources`

- preparation必须该真实当前诊断/repair parent，continuation若给必须原registered identity/current snapshot/fence；execution若给必须原service-held command，parent/input/recipe/currenttargets匹配。Backend `_diagnostic_parent`调用相同私有实现；Media `preserved_clips`和audio-remix读取同一个口。无Media SQL或公开管理scope。
- HeldParentEditSources是frozen eq=False，仅该原service登记、同thread、ordinarylease、binding、current parent。字段为binding、execution_fence、parent_preparation_id、parent_intent_sha256、assembly_sha256、lineage_ref、ordered_clips、audio_tracks、effective_media_roles、operation_observations；clip/track中的Asset用现有c.AssetRecord，不复制资产DTO或冒Bundle artifact。每来源关联原GeneratedFileManifest/实际allocation、完整Step/Operation/观察来源；consumer取得路径只调用原bundle.content_path，不能用source URL/filelocator升权。
- immutable body `current-parent-edit-lineage-v1`字段为format、binding、parent_preparation_id、parent_intent_sha256、assembly_sha256、effective_media_roles、edit_nodes、ordered_clips、audio_tracks。每edit_node保存operation_id、step_key、input_sha256、route_sha256、observation_sha256、result_sha256、原edit_lineage及实际输出attempt→Asset映射。root选取由当前assembly真实master/affected-master source_steps/command关联决定，绝不按时间或latest。lineage_ref复用DiagnosticMetadataRef；本body是来源事实，不是许可/当前执行资格。
- 真实reader收集源row/file/生成Observation后在SQL外核bytes/decoder/有限graph，原issuer/current/rightsguard保持；必要首次持久化伴件只用原metadata和唯一短writer insert-or-exactmatch，重核完整captured rows、parent/journal/selected/currentlease。相同canonical body复用；同parent不可变定位不同body409。伴件locator不能回填主资产或改原Operation。冷读原bytes同时重认证当前来源；不因body曾登记就跳当前许可/retire检查。

### 3.3 当前代及四配方的准确闭包

当前父timeline root由真实视频/混音实际来源分别确定，保master原source_steps。不能要求四masters必同一个edit Op：visual-preserve-mix新video/cover而mix旧；cover-only仅cover新；audio-remix新video/mix且video stream来自旧；ambient-remix按真实scope生成。每个保留edge必须以原Asset/原Operation真实输出和本次request中的preserved ID匹配，跨父子每代精确连边，不能把最初production-shot当当前版本。

- ambient-remix-v1：有序真实clip图像/ambient、当前真实旁白，经本次actual graph生成允许video/mix/cover；只有原target授权的shots可生成。
- visual-preserve-mix-v1：新/保留clips图像按原序；旁白和mixed_audio本体保持真实父ID/bytes，bed不能暗重混。
- audio-remix-preserved-clips-v1：原video流、全部实际保留clips的ambient、允许的新/原旁白；实际video_stream_copied证明来自该原video。未授权shots不生成；不能从mixed_audio反推三段原ambient。
- cover-from-preserved-video-v1：真实当前父video来源/全clock和已准选帧；不要求重新渲染clips/audio，也不暗发布其余masters。

每shot源必须唯一、真实当前、顺序/clock与原plan一致，source SHA/size/probe/MIME完整核。保留资产ID/hash/bytes不变，原AudioTimelineMapping仍按真实source/time证据，不把codec时长约等替200000us合格测量。

每lineage node最多引用本次原finite shot/track/output闭集；实际图边/深度资源预算复用原Bundle/repair已有上限和祖先许可闭包，不发明较小限制拒合法历史。cycle、缺/重复shot、不相干Run、unknown/unsettled、未认证source报具体错误；未知Ops仍reconcile，无新render/付费key。旧Operation可在exact已知producer/fullroute版本、完整原result+真实storyboard+master source_steps+完整command/Step/inputSHA可证明全部事实时构造同一伴件；这不是按字段相似默认迁移。缺实际track/输入时返回明确source_material_missing/information_required，提出补原已认证来源的具体请求，不猜。

新producer必须从正常首次制作产生完整lineage，旧有精确信息可恢复；不能以永久503、只cover支持或要求用户填写内部proof替代本轮完整制作。后端导出的held ordered_clips供Media替换当前从四master fact筛shot_clip的错误来源。其余recipe/target/exact/fallback授权规则不改，拒绝过的intersection/subset补丁不在此合同。

## 4. MDG04：当前真实验证上下文取代driver缓存

### 4.1 最小私有ABI

原Media factory `ComponentDiagnosticPorts.verify_component_observation`唯一签名增量：

`verify_component_observation(inputs, observation, *, operation_observations, validation_context: HeldComponentDiagnosticValidationContext) -> 同版本observation`

新增Backend private frozen eq=False held context，仅原registered CurrentFinalEvidencePorts/service可生成/登记。字段：ordinary_lease（原c.LeaseGrant实例/value）、binding、execution_fence、input_key_sha256、original_input_ref、parent_edit_sources（V3必要，V1/V2可None）、completion_bodies（按真实inputs.completion_source_refs原顺序的tuple[(CompletionRef, bytes)]）、resource/runtime SHA。原V1无completion时空tuple；V2/V3必须含每个完整原认证body。不得只透传ref、SHA、jsondict或reader URL当成功报告。

同原CurrentFinalEvidencePorts增加：

`assert_component_diagnostic_validation_context(context) -> None`

这是原service登记的context身份/thread/当前ordinarylease/fence/原input/完整源captures和真实completion资格检查，不是Media可自构造True guard。context登记只限这次验证调用；Backend finally无论成功失败都注销，port.close也清理。context不得持久/导出/进入Flow state/renderer/模型。`assert`失败403或原具体not_ready；不得catch泛EngineError默认为没有资源或跳第二次。

factory bind_services时绑定同一原final-evidence port，Media verifier在验证前后调用该真实assert，并使用context.ordinary_lease、completion_bodies、真实parent_sources完成实际decoder/规则检查。移除_contexts作为authority/必要成功条件；可有非权威缓存但每次当前事实验证一致，不能用旧lease/completion覆新context。调用到原ASR的被拒supervisor改变仍不授权。

### 4.2 四个实际caller及顺序

首次 `_record_component_diagnosis`、append、`_read_explicit_diagnostic_record`、selected reader最终通过同一Backend helper `_verify_component_diagnostic_observation`：

1. 原service-held输入/port/currentOwner/auth/ordinarylease先核；读取exact原输入/record/selected/source/journal captures。
2. 重建新进程的typed输入（值不是权源），原原Intent/全method catalog/route/source闭包、原成功结算Operation/真实成本与checks引用先核。以现有read_diagnostic_completion实际reader及原当前qualified completion verifier读取完整body；首次从driver拿过的bytes不能直接升为认证body。
3. 构造并登记本次held context；validation前真实current/assert。使用原genuine LeaseGrant，不能从binding/run/fence拼一份lease或重复begin分析。
4. 一次verifier逐method实际执行已准本地验证（不是再跑paid model）；仍完整原wholeverify，两authority以及其caller原顺序不变。driver冷缓存缺失不重派LLM。
5. validation后真实current/assert，原checks/完整bytes/captures再次一致核；短writer核same immutable input/Operation/source/journal/current before record/select/append；既有read路径原final guard/两次实际authority保持，期间撤销/replace不能伪authenticated。
6. finally释放context。冷进程用真实新ordinarylease/fence重建fresh context，原input/op/Fact byte不改；身份只从原issuer registered/current/readers，历史成功Fact不能复活旧grant。successor resource reauth若需要尚未审0064，必须明确not_ready等其独审/实现，不能在此借其他接口绕过。

OperationObservations按实际nested method/op顺序返回且与真实全部Op对应，不把一份输出重复凑四角色。首次partial方法未完成保其真实Step；selected cold reader从原Fact逐method重建Observation，不丢归因。验证失败保原事实，明确403/409/422/503来源，不能重新分析清记录；修复走原受控已批准material/resource补充及诊断恢复，unknown仍needs_reconciliation。

## 5. 同Run正常链与角色任务

正常新安装的唯一链：Integration真实索引新catalog/role templates/edit producer → Backend原安装coverage/registry接收显式版本 → 首次Media四masters实际edit_lineage随原Operation提交 → Backend原parent读口得到完整父sources与不可变ref → 原prepare登记V3及所有原method intents → Media固定四角色分别用原Executor → Backend原verifier+fresh held context组合record → 原完整quality/precision → 真实whole-plan/current权限及有限repair proposal → 原四recipe消费受控当前clips/tracks → 新child真实Operation/lineage → 原Bundle/ASR/字幕/RAG整包验证/交付。

这是本轮必须实施的路径。自动Owner预授权与interactive真审批沿原PolicyExecutionPorts/actualadmission，不将模型导演结论当人审，也不每个project要求再注册。精准缺资源可等待其真实补齐/恢复，不把等待本身宣制作完成。

| owner | 唯一实施写集/依赖 |
| --- | --- |
| Backend | domain的catalog/Observation/Fact/input version唯一dispatcher；service原method-intent/组合投影/原selected与journal版本接受；held parent读口、来源伴件短writer、context registry/assert/helper；原Worker/Executor commit的lineage严格验证只在自己路径接线。无Media复制DTO/SQL。 |
| Media | actualFFmpeg结果lineage、初始/affected真实来源传递；四独立method producer/固定Flow使用原intent；显式verifier context与真正当前decoder；preserved_clips/audio-remix改用held parentreader。保旧V1独立consumer，MDG03已接线不再新造。 |
| Integration | 新版本所有模板/代码/资源/provider/模型/工具/许可实际producer闭包及source/resource/runtime索引；由Backend唯一公开契约生成必要SDK，私有held对象无renderer输送。没有真实资源不标qualification ready。 |
| Test/Review/Acceptance | 由各自角色独立制定/审查/执行证据，架构不代测试标准或验收；本ADR不关闭MDG finding。 |

Backend先冻结唯一DTO/ports普通副本供Media；Media和Integration再固定实际实现/资源普通件；独Review再Test真实场景。无真实模型/许可/机器或ASR可执行权限时应列具体待验，不假阳性。Platform为Windowsx64、macOSarm64/x64、Linuxx64均须实际验证，不能据本机源码或一处DMG构建宣全范围完成。

## 6. 独立验证所需最小真实正反例

这只是给Test的验证需求，不修改其原criteria：

- 四角色确有四个不同method/原intent/实际Op/输出/实际费用，同一完整input；same模型允许，单回复三观点、复制输出/费用、methodroute错、跨method source误借必须拒。partial成功恢复只读取原成功角色；unknown不重发，预算按原合计，不因新V3重置原限次。
- 当四真实role支持单组件，确定性projection支持原有限recipe；冲突/不可见/缺音源/precision-only分别information_required或timing-only，无质量→媒体权限提升。
- 各四recipe真实parent→child→再child含保留片段/mix/video边，原未影响Asset ID/hash/mtime保持；非初始父版本不能退回production-shot；duplicate roots/cycle/clock/missing真实track/跨Run/替换source/许可撤销拒。clip allocation不可冒Bundle artifact。
- 原edit succeeded/settled但Step未commit、原Asset提交但伴件未写、伴件已有但lease撤销各窗口按原receipt/shortwriter恢复，只读/免费核不render；原record有未知Operation保持reconcile。
- 全冷进程：原四Method Steps/Fact/selected持久，新ordinarylease不同fence，原厂verifier无driver调用/空_contexts仍用真正当前完整completion验证并复用原Fact无第二扣费。认证body缺失/伪context/旧thread/旧lease/port关闭/验证期间撤销/第二真实authorityfalse均不能成功。
- 旧V1/V2原body/哈希/key/Fact读取与原exact/fallback行为保持；新版本未知字段422而不是silentfallback；旧缺实际lineage准确missing并由新制作正常提供，不能选latest凑完成。
- 每个真publication仍完整wholeverify、独立报告/参考与P95200000us、两真实authority/selected门；所有本合同源码检查、静态正文或AST通过都不等真实视频质量、运行资格、三OS或R1/R2验收。
