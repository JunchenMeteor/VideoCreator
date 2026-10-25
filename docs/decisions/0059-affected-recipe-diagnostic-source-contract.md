# ADR0059 — 受认证组件诊断与有限修复来源

状态：APPROVED_CONTRACT_ONLY。仅批准本节类型、来源、调用次序和版本兼容设计，不批准产品执行、具体实现、独立标准或验收。原 RRD-P01、完整 R1 与后续 R2 仍 OPEN。ADR0058 原字节不改；被拒的 dependencies intersection/subset 补丁不在本合同中。

本合同补齐真实自动路径：Media 从同一 Run 的实际作品、原剧本/分镜/质量资料与受控诊断方法产生可追溯诊断；Backend 验真、不可变记录、提供只读配方提议。人类审核或原 Owner 自动预授权决定是否执行完整新计划。诊断不是授权、独立测量报告或资格。

## 1. 已核源码结论与范围

停止 Early124 中，`AffectedRepairService.authorize_current_affected_execution` 365–540 读取原 READY `repair.source_report_ref`，以边界最大误差大于 200000us 选出 failed units。`PrecisionEvaluationReport` 896–913 的 boundary pairs 只有预测/参考时码，没有旁白/画面/封面/环境声原因。`WorkAlignmentValidationReport` 1612–1644 的自由 reasons/source_gaps 也不形成组件因果记录。

`CurrentFinalEvidenceService.verify_current_final_evidence` 238–307 当前只把真实独立测量失败构造成 `FinalEvidenceRepair`；`_current_repair_scope` 69–124 返回的 allowed_action 是可用性资料，不是正确原因或执行权。`CurrentFinalEvidenceJournal` 的旧 v1 repair 固定 MaterialReceipt。不得把新的私有 JSON 伪成 READY PrecisionReceipt、把时码差改称 TTS 故障、给旧报告补不存在的 visual/cover 边界。

Early sole mapper 接受 `failure_component/source_shot_ids/regenerate_narration/ambient_required`，纯 mapper 无法认证来源。以下持久来源是其唯一新入口。原 v1/v2 命令、原 canonical bytes、原 Goal encoder、原 200ms/MM05、两次真实 authority、budget/unknown/限次/current/fence 保护均保留。

## 2. 唯一数据事实与信任边界

Backend 在 domain 中唯一维护以下私有 strict/frozen 类型；Media 只消费。命名与格式固定，不开放公共诊断 bool、renderer Owner 字段或通用 payload 门。

### 2.1 输入与生产调用

`RegisteredComponentDiagnosisInputsV1` 是 service-held、frozen、eq=False 的非序列化对象，登记同 service/Runtime、ordinary lease、thread、current binding、execution fence；不能凭反序列化或对象相等取得 held 身份。它包含：

- `input_key_sha256`：第 6 节稳定诊断输入键；`binding`、真实 `parent_preparation_id`、`parent_intent_sha256`。
- `parent: CurrentFinalEvidenceReadSet`：原受控读取结果，actual four masters/assembly、原 script/storyboard/plan/quality revision refs、素材 provenance、READY 文本和有则真实 candidate/ASR context。候选 Manifest 可以尚未形成，assembly 和实际源不能编造。
- `precision_report_ref: MaterialReceipt | None`、真实报告原 bytes/coordinate/failed units 的受控视图。有值必须来自同 parent READY receipt；无值不是 P95=0。
- `source_media_refs`：Backend 从实际 parent Asset/Operation/Observation/probe/mapping 推导的有限索引；每项有 artifact/asset ID、角色、完整 SHA/size/probe、原源 Operation IDs、intrinsic/timeline 半开范围与映射 refs、原 shot IDs。索引不接受用户 URL/路径/猜测 shot 列表。Media 只沿原保护资源读取/原许可用途使用其 bytes 或 stream。
- 当前真实 `diagnostic_method_refs` 与 Backend 登记的 `analysis_intents: tuple[OperationIntent,...]`。只读资料提取不先扣款；实际运行或模型调用始终由原 Worker/Executor 用这些真实意图写 Operation 账本后执行，不自造 Worker/任意 key。

只有固定 registered Media factory 的生产分析/验证 callable 可消费此 held 输入。沿原 `assert_current_production_services` 和当前 installation/resource guard 验证真实来源；配置 SHA、方法名称或 JSON `verified=True` 均不替代它。

### 2.2 一份不可变诊断正文

`ComponentDiagnosticObservationV1` 待验正文固定只有 format=`current-component-diagnostic-observation-v1`、input_key_sha256、method_ref、analysis_operation_ids、checks、limitations。不得带 Owner/approval、最终 recipe、changed roles、result bool 或覆写 parent/source refs；这些结论由 Backend 受控重建。checks 中的 expected_ref/observed_ref 仅可引用输入闭集的原 revision/READY report/Asset、实际已观察 Operation output，或该 registered method 真实解码的 sample ref（source Asset SHA、原范围、sample bytes SHA/size、decoder ref）；解码 sample 必须可沿真实原素材和固定方法重算。任意 URL、路径、free-form evidence blob 或只有模型口述的 source ID 都拒绝。模型 observation 自身也必须有真实模型 Operation output ref，不能只提交最终说法。

`ComponentDiagnosticFactV1`，format=`current-component-diagnostic-fact-v1`；完整 canonical 正文固定含：

1. `input_key_sha256`、原 `ProductionBinding`、parent preparation/intent、实际 authored fence、candidate file SHA 或明确 null。
2. 原 script/storyboard/plan/quality revision refs；原 request/registration/resource/runtime SHA。不能追加未提交新计划当作诊断来源。
3. `precision_report_ref` 或 null、`failure_event_kind: precision_timing | component_observation`。前者保原实际报告/failed units；后者没有伪造独立报告。
4. 前项受控 `source_media_refs`、原 source/ref/mapping 闭包与完整摘要；Backend 重建索引并逐项比对，不信任模型给的素材身份。
5. `method_ref`：实际 method ID/version、indexed implementation source refs、规则/template SHA、runtime/resource refs、实际 route/model binding（无模型时明确 null）。方法资格仅为允许该有界诊断生产的真实安装/注册来源；不能代替 ASR/CTC/精度资格。
6. `analysis_operation_refs`：真实同 Run succeeded/settled 的 Operation、input/route SHA 与不可变 observation/output SHA；使用模型必须保其真实原响应和请求来源，敏感材料不写入 fact。原模型响应在实例内按其实际许可保存，fact 引完整受控 ref。
7. `checks: tuple[ComponentDiagnosticCheckV1,...]`，每项有唯一 check_id、闭集 check_kind、component、实际 source refs/原 shot/range、expected ref、observed ref/结果、`assertion_status: supported | not_supported | undetermined`、`evidence_strength: deterministic_observation | attributed_model_assessment`、限制和 uncertainty codes。check 不能只含一句“请重做画面”。
8. 由 Backend 的固定验证/投影器推导 `result: timing_only | component_repair | information_required | no_component_failure`、`failure_component: cover | narration | mix | visual | ambient | null`、`source_shot_ids`、`speech_change: required | not_required | undetermined`、`ambient_change: required | not_required | undetermined`、真实受影响 artifact IDs、failed unit IDs、intrinsic/timeline ranges。多原因不能被隐式合并为全量重做。
9. `uncertainty_codes` 和有限 `information_requests`，见第 7 节。自由理由只是说明，不是可执行字段。

正文不含自身 content SHA/未来 command/child ID/批准 ID，因此没有 hash 环。`ComponentDiagnosisRefV1` 固定只有 format=`current-component-diagnosis-ref-v1`、record_id、完整 content SHA、size、input_key SHA；record_id 由 Backend 持久记录给出，ref 是定位/完整性资料，绝非许可。注册后的 `RegisteredComponentDiagnosisV1` 再由同 service 以 eq=False held 对象保真实身份、当前 thread/lease/fence 和 ref。

### 2.3 模型参与的实际边界

Media 的导演/剪辑/录音等角色可以分析，但必须从同一受控 readset 阅读实际 audio/video/frame/text 和原方向，并按以上 check 格式提交有出处的意见。不能只看时码、文件名或模型摘要便宣称听审/视觉检查。

Backend 验证 provenance、实际 Operation/原响应绑定、允许的 check 范围与完整性；确定性 check 通过同 registered Media 验证 callable 在 SQL 外复算。语义模型分析不能被伪装成确定性物理测量：保 `attributed_model_assessment`、不确定性与真实方法来源，并且仅在原完整计划/当前 Owner 已覆盖该有限分析方法和后续配方时参与自动提议。其意见本身仍不授执行权，不证明 P95、不代独立参考/资格。

原 Owner 一次预授权后的自动流程可以使用合规、受控的语义诊断；不要求每部作品人工标注或手填内部证据。交互模式可以显示真实诊断和新完整计划供真人审核，禁止构造假 ReviewDecision。

## 3. 有限检查与配方投影规则

真实 method 生产与核验以下闭集，不开放任意工具/代码。各 check 的具体解码参数、容差、语义 template 由 Media 固定实现，Integration 将精确 source/resource 纳入 producer；Test 独立审验，未知配置保持未 ready，不由架构编造数值通过。

| check_kind | 实际来源及支持范围 | 允许数据投影 |
| --- | --- | --- |
| precision_boundary | 原 READY 独立测量报告、真实参考、原 boundary/coordinate/mapping；两 authority 仍原逻辑 | 只有时码失败则 timing_only→原 realignment；不得重做 speech/clip/cover |
| cover_frame | 真实 cover bytes/probe，原 video 解码帧、原封面配方与原 shot 源；语义封面判断保模型意见属性 | 支持 cover 故障时选择 cover-from-preserved-video-v1；只有 cover 输出 |
| narration_source | 原 approved script/实际 TTS input+observed audio/实际 ASR+其限制；必要时实际听审型语义分析 | 只有支持 speech 必须改变才 required；ASR 文本差或时码差单独不足。支持 narration 故障且 required 才 audio-remix +真实 narration 组件 |
| mix_source | 原 mixed audio 与 narration/实际 clips 的原配方、采样/声道/增益/clock/观察资料 | 支持 mix 故障而 speech 不需变更则 audio-remix，保原 narration 与 clips |
| visual_source | 实际对应 clip/video/frame、原 storyboard/方向/shot mapping、原生成 input/Observation；语义判断真实引用实际画面 | 支持有限原 shot 画面故障且 ambient 不需变更，则 visual-preserve-mix；保 parent mix/narration |
| ambient_source | 实际 clip ambient track/原 remix 输入，真实源 shot 与原配方明确需消费新 ambient | 只有 ambient 必须更换且所需输出全部有实际故障闭包及批准才 ambient-remix；不得为了使角色 exact 随意重混 |

同一有出处的 diagnosis 只能选一份有限配方；多组件原因如没有原 catalog 的精确组合，返回 information_required/具体计划修订建议，不自动上升为 ambient/full masters。合法 cover/audio/visual 单分支不被时码报告缺失永久拒绝。

`source_shot_ids` 从真实被观察素材和原 storyboard/Operation 输入映射验证；不从全部 impacted shots 推出生成。空 failed_units 对无时码组件故障合法；空 source shots 只用于无需生成 clip 的分支，cover 仍保其真实首帧源。所有时间为整数微秒和半开范围，完整映射须与原音轨 SHA 匹配；不得用 narration clock 代 mix clock。

component_repair 的 actual failed-role 上界从受支持的原失败 asset/原 dependency closure 推导；不是从 proposed changed roles 倒推。原 mapper 仍严格 `O == changed_media_roles` 且 O 在该真实失败闭包和整份计划授权内。首帧 picture 变化需其真实 cover 来源/失败依赖和明确批准，不能把原无关 cover 扩成允许写出。

只要本轮唯一诊断仅支持 timing，继续原 registered alignment；缺 alignment 资源转具体 resource wait，不改用 TTS。no_component_failure 不代表独立精度通过，原 final verifier 仍可失败。

## 4. 唯一实际端口与调用顺序

在现有 service-held `CurrentFinalEvidencePorts` 上增加四个私有端口，由 Backend 唯一维护；不建立新通用 RPC、公共管理 scope 或 SQL 给 Media：

1. `prepare_component_diagnosis(preparation_id, *, continuation=None) -> RegisteredComponentDiagnosisInputsV1`。要求同 ordinary lease/current Runtime，读取真实 parent assembly/素材/方法来源；有 continuation 时重核原 journal/current selector。返回输入及已登记的真实分析意图，不运行分析，不生成 repair command。
2. `record_component_diagnosis(inputs, observation: ComponentDiagnosticObservationV1) -> RegisteredComponentDiagnosisV1`。observation 是 Media 待验资料，不是 permit；Backend 从输入与已 succeeded/settled Operation 重建 fact、复核 checks、写不可变 record；不能直接持久模型给出的结论 bool。
3. `read_component_diagnosis(continuation) -> RegisteredComponentDiagnosisV1 | None`。只从同 parent/原 current journal 指定 ref 读，不按“最新同类”猜选；None 表示确未记录。已引用但缺损/不匹配返回明确错误，不能变成 None。重启以持久 bytes 重建读者 held 身份，不能恢复旧执行权。
4. 既定 `prepare_affected_recipe_proposal(continuation) -> AffectedRepairProposalV2`。必须通过前一端口消费已记录且当前的 component_repair fact，并用 sole mapper 重算；不能接受诊断入参 bool/模型 recipe。timing_only 不调用它，Media 转原真实 realignment 方法；information_required 返回第 7 节具体等待，不创建 command。

Media 的有限自动入口置在真实 masters/assembly/原质量资料 ready 后、原 final publish 前：prepare→原 Worker/Executor 执行真实 analysis_intents→record。恢复时先 read 指定 record，已 ready 不重复分析/扣款；原 unknown 先 reconcile，禁止换版本/任务名重交。

`verify_current_final_evidence` 在原全部质量/precision verifier 旁消费该同 parent 当前事实：真实组件 failure 生成下节新私有诊断失败 assessment/journal；独立精度失败仍保原 report/原因。不能用 component QC 替代原 verify，也不能把“诊断成功”发布为成片成功。若两个失败同时存在，分别保原精度来源和组件来源，先按真实 current 控制选择有限可授权步骤，最终两类条件都须重新验证，禁止清掉超 200ms 记录。

新 journal/continuation ready 后：read diagnosis→prepare proposal→原真实 whole-plan/human 或 Owner execute_plan/continue_bundle_validation admission→原 authorizer→短 writer 登记实际 command/steps→Media 原 Worker effect→Observation/masters/child→原 ASR/CTC/final verifier/两 authority/RAG/Bundle。全链同 Run、Production、原预算和限次。尚无真实 plan/current coverage 时只产生数据提议、等待原 Owner/settings 或真人审核，绝不造许可。

## 5. 最小显式版本与旧字节兼容

禁止对旧 v1 journal 或已批准 execution-v2 的 source_report_ref 增加“也可私有 JSON”解释。为新组件诊断分支明确新增以下有限 grammar，全部仍由原 Backend service/issuer/current resolver 维护：

- `CurrentFinalDiagnosticJournalV1` format=`current-production-final-evidence-diagnostic-v1`，沿原 binding/control/blocked_at/last_transition 状态机。snapshot 绑定 parent preparation/intent、真实 READY refs、可有真实 candidate SHA、指定 diagnostic_ref；component repair 源含原 failed asset/dependency closure、无时码时 failed_units=()、可有真实 precision_report_ref。只有对应诊断已 supported 且实际 component failure 才 repair_required；未诊断/未知源是 waiting_diagnosis，并附具体补充项。不得把未完成诊断当 ready 修复。
- `AffectedDiagnosticCommandV1` format=`current-final-affected-execution-v2-diagnostic-v1`，保 ADR0058 V2 原 binding/current/plan/projection/recipe/targets/route/resources/父素材和真实 step/child/lineage 写序，新增 diagnostic_ref 和完整诊断输入键。其 `failure_source` 是严格 tagged union：precision_with_component_diagnosis（真实原 MaterialReceipt 不空）或 component_diagnosis（只有新真实 diagnostic_ref，precision_report_ref 明确 null）。不生成伪 MaterialReceipt 或独立 P95。该新格式唯一注册 `AffectedRepairExecutionDiagnosedV1` eq=False held 类型，不能把普通 V2/data DTO 传入其注册方法。
- 新版本在原 held authorizer/readset/Worker/selected reader 中显式解析；旧格式走原全部字节/原 exact/旧合法 fallback。未支持新标签拒绝明确版本错误；不能因当前 optional 字段缺失 reinterpret 旧记录。原 v1 realignment 保旧命令格式与真实 selected CTC ABI；诊断标签不新授 dispatch。
- 诊断分支 command 使用 ADR0058 的有限 component step/dedupe 原规则，并把诊断 ref/格式纳入整个 source SHA；不得给旧 unknown command 换 sha 获新键。诊断不建立第二 Run/budget/修订计数。
- 对只需 timing 的原 journal 保持原版本；有组件 diagnosis 的新 snapshot 不把原计数/current来源丢掉。原 resumer/issuer 只在显式新 grammar 的实际事实中核相同 request/plan/current/scope/已登记 source，不能把格式升级当 allow。
- 真实 lineage-v3、初始/修订 CTC 的原九 held 口和旧 0056/0057 来源边界不改；新 resolver 只认识已真实登记的 diagnosed command/ref 关联，不能凭诊断 SHA 替资格/权限。原范围/深度/节点/rights closure 保护不变。

这一增量是新私有数据来源，不新增 owner 管理权限、免费无限模型权益或“全项目” scope。

## 6. 记录、短事务、恢复和实际资源

### 6.1 确定输入、无环哈希与不可变存储

Backend 稳定 input key 用原 request/registration/binding、parent preparation/intent、真实 plan/storyboard/script/quality refs、candidate 或明确 null、完整实际媒体/源 Operation ref/mapping 与 method/template/resource/route version 构造。采用已批准 recursive JSON、sort_keys、compact、ensure_ascii=False、allow_nan=False、UTF-8 全正文 SHA256；不调用只支持 BaseModel 的 helper 来假定 dict 已 canonical。

input key 不含新 fence/record ID/未来 child/未来 command。事实正文的 authored fence 只记录原真实生成时刻；重新 claim 同 unchanged 输入先读原 record，再以新当前 lease/fence 建立新 held 读者，不改原 authored bytes、不重跑已完成分析。

原数据库 metadata 或同归属私有表可存 typed bytes（Backend 选原适合实现），索引键闭集 `component-diagnosis.<input-key>.<record-sha>` 与同 parent 已选择 ref。对同 input key 的 conflicting result 409；原未接受的新复查必须有实际变化的来源/方法/原真实修订，不能伪装旧 command 新版本。fact/ref 内容不可覆盖，不采用 latest。不得把同 hash 当 current 授权或把 foreign imported ref 当本机登记身份。

### 6.2 真实检查次序

prepare 的初次 current/lease/service/installation 守卫→只读读实际 source→原 Worker Operation 先登记→SQL 外真实检测/模型分析/确定性 check 复算→第二 current/resource/许可检查→短 writer：

1. 重核同 Run 当前 ordinary lease/fence、parent intent/assembly/原 READY 与真实 current selector/journal；原权限源、方法安装源仍 current。
2. 从实际 operation 原 ledger 验 succeeded/settled、input/route/model/source hash 和 immutable observation，确认所需 sources 完整；unknown 不进 record。
3. 严格写 fact 和唯一 ref/同 parent 指定指针，emit 原 event；幂等原 bytes相同即复用，冲突不覆盖。
4. writer 内再核完整 source、issuer/current scope，原 guard 的 outside-writer 当前检查仍保留；文件/模型计算不持 SQL 长事务。

proposal 和 command writer 都从持久 record 重读同 ref/full SHA、重算来源/mapper，并核全部原真实 admission/routes/rights/resources/cost/budget/限次。第二 precision authority false 仍 403；诊断 getter、record 绝不绕过它。诊断记录不减少 revision_cycles；真正 child 提交才按原同 writer计数。模型诊断费用与所有生成修订共享原 Production/Run 账本，未知额度不按免费处理。

### 6.3 明确实际生产/资源归属

- Backend：唯一 DTO、记录/读取/held 注册、actual source 与原 current/writer/issuer/selector 核、唯一 schema/版本分派、mapper 投影、真实 local analysis意图与已存在 text路由意图的登记。
- Media：registered factory 新诊断 producer/确定性 verifier callable；实际有界 decode/compare 和真实模型协作。只能读取原许可范围的 actual material，不能直接改 metadata、构造 current/资格、自行扩 reader 或跑任意 shell。
- Integration：真实 producer 纳入精确诊断 code/rules/template/runtime/decoder/source闭包，生成 SDK 如公开 schema发生实际变化。资源型增量固定 format=`registered-production-driver-resources-v3-diagnostic-v1`，原 V3 全成员不变，增加 `diagnosis` 有限方法 source refs/规则 template SHA/actual local route或actual text route binding；原 installer qualification/full coverage 和同 Owner 原资源身份必须更新，JSON catalog不是资格。
- 固定本地方法可使用原真实诊断本地处理路由；若现 capability enum没有相应合法值，由 Backend 仅增有限 `media_diagnosis` local-only、无凭证、max_operation_cost=真实0 的注册能力并沿原 scope验证；不能把架构这句话当安装已批准。模型方法只能用当前已配置、被 Owner 覆盖的原 text route 和真实账本，不因为有账号就调用。免费本地诊断不强制登录、Wan 或付费模型；缺可用方法具体 not_ready，配置后可真实继续。
- Test/Review/Acceptance：独立验证实际方法支持的断言、资源/输入限制、正反与跨进程故障，不把来源签名/SHA/模型 confidence 当真实质量或兼容通过。

这些资源均未在本卡安装、执行或资格验证。本地/BYOK factory queued 目标保持；不能把未配 Wan 或诊断模型转为所有本地工具的普遍前置。

## 7. 缺失、补充、错误与可继续路径

缺报告/actual source、方法资源或真实 observation 时：返回 information_required/waiting_diagnosis，保清晰 reason_code 与可恢复项目；原 blocker/resumer 保原 trusted caller/current/writer→queued/new fence，不重复 park 已释放 lease，也不启动全局盲恢复。

有限 information_requests 固定为 source_material_missing、source_mapping_incomplete、diagnostic_method_not_ready、analysis_operation_unsettled、analysis_inconclusive、competing_causes、finite_recipe_missing。每项只引用真实父 source/需要的角色，显示人可读的“原素材缺失/需要再次分析/方案需要修改”等操作。用户可在产品内补原素材、授权或配置实例资源、指导方向/审核实际完整新方案；不让用户填写 authority_ref、method SHA、内部 proof 或反复每项目 CLI。

配置/材料补齐或实际复查完成后：原受控读取重核指示变化→同 Runtime 真实 analysis→record→原 trusted resume/新 fence→指定 record→proposal/admission→真实制作。不得永久返回 guidance_required 冒已实现；缺件保持具体 NOT_READY，并保完整可接续方法与 owner。

403：当前 Owner/rights/source/资源权限撤销、held identity失效、第二 authority拒绝；不作缺资源。422：错 parent/素材/Operation/坐标/shot/正文/报告绑定；409：immutable input/record/command冲突、错误 current/fence/超原限次；503：确未配置实际方法/源资源。unsupported/unknown模型结论不是失败事实，也不强制 whole-master fallback；真实 P95>200ms继续原失败/有界修复，不能用真人审核、资源重检或诊断“通过”清除。

## 8. 后继实施与独立验证要求

Backend 先交唯一 types + 上述四口 + 新 private journal/diagnosed command显式 dispatcher/current writer ABI，接通实际 select/record/resume/proposal链。Media 再将自动诊断调用置原作品实际接缝，随后原四 recipe组件 driver；Integration 对实际source/资源闭包与 SDK 生成固定版本。禁止 Media造第二DTO、审查角色代实现或架构读 hot源。

必须验证：纯时码不dispatch TTS/Wan；真实 narration 与 mix 分离；实际 cover首帧/visual shot/ambient源分别绑定；null/P95未测不变；模型无 actual sources/Operation、无法观测音视频或不确定时不伪成功；假 record/不同 Run/thread/expired fence/撤销拒绝；同输入恢复不重分析/不扣两次、unknown先核实；新版本组件源无fakeMaterialReceipt而旧原bytes兼容；failure闭包不能从 changed roles倒推；整份实际 human/Owner批准独立；两个 authority current检查；同 budgets/计数/范围；原全质量/RAG/Bundle最终交付。真正听审/视觉观察与 Windows/macOS arm64+x64/Linux实际测试仍后继执行，不由本设计宣布通过。

## 9. 固定来源

本次仅停止 ordinary读取，未读后续 hot0058：

- 任务卡：0dcc16e4726caeb7c89bb43656e02aa55f01f029f6f1b9edb4bb4cbeeb8920f2。
- EarlyInterfaces.md：d772406a377646e998e7c7e1f327aa602375a538b652fc69b4f66b2791069a58。
- FailureDiagnosisGap.md：703dcedf246dbe886d4f0bf70b05350f0f40d5e049580d5834c1bd223180e52f；JSON：f5e84d4dbc2015b137495c32f55d898004531e2e29b74cd279845584bc0ed812。
- EarlySourceStage/SourceIndex.json：7a0f9fc0ae35d4e973f7d93fb310f8eac239cca1779dc12e3098c4686dbb362e，124固定来源；本卡不宣称全部124正文已读。
- ordinary application/affected_repair_service.py：1b7624f7bd6a75ae0f52d6cba1296317899cd6a0d7e0419a2f745f5c4ffd88a1，350–565。
- ordinary domain/contracts.py：175d105c6c80415b14d0f4a5b69f841548b7fbc968d3058f55d13e1cba5284ec，865–920/1590–1655。
- ordinary domain/affected_recipe.py：cf636f50ea47b1405ef64e3f69265d5cfb71254e2570127514430db3706606ff；affected_recipe_mapping.py：4eae9e36897f7b61f5f62bfcb803b097ebf70262bb1f9694c184d06a1af90b92，两完整正文。
- ordinary application/current_final_evidence_service.py：224de8ddc0cef702eac3bb452146d5d62c13c3ba13c880f2c2b04942b9ed042c，1–125/238–307；domain/current_final_evidence.py：7f9e99b42a39ca6a14119ab13be1134235034e884107245aefed243f0a116932，完整正文。
- ADR0058：a2660ba525f88fc81539e238fafb9c7c51eaf7b3c46f70f4726db785f44b6857，原已停止合同，本卡不改。

实际读者/工具由本人续原 handle自然终态，最终 InputPins/SourceAfter/Handoff 保存普通副本与逐件身份。本轮无产品/Pydantic/SQL/ASR/模型/网络/keys/fees/install/部署/第四目标；上述新增类型只是准入设计，不是已实现或发行资格。
