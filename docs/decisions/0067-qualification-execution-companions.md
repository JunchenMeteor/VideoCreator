# ADR 0067：资格执行伴件的唯一 grammar 与真实导出

状态：DESIGN_ONLY_READY_FOR_INDEPENDENT_REVIEW。仅响应固定 QCOR-P01（996b5b40）；不改0066（593569ba）及其36输入，不提前裁定其它 finding。本合同未获独评，不授源码应用、资格、运行或费用。完整 R1 独验后连续 R2 保持。

## 1. 真实已有来源与缺项

停止 Backend 索引为 ChildWriterLeaseCorrection/AppliedStage/SourceIndex.json，131源，SHA b58c610f5d6228cda30e0014bff77c18249a302836e24b2aaeb03c1ada0fd93a。只读其 ordinary_copy；不是热仓库。完整来源路径和SHA在本阶段 InputPins/OrdinaryIndex，以下是必要定义身份：

| 来源 | 完整 SHA256 | 已有真实语义 |
| --- | --- | --- |
| domain/contracts.py | 3562a76f3082953b67cbecd60989a3d891a574473255c21895188806bc3624fb | OperationIntent、OperationObservation、ExecutionPermit、Money、CapabilityRoute；并无资格执行导出类型 |
| application/engine.py | e6d0d39730907b4ac9ccb93072aa4412bb918c49f3a50bfacdef66f6b07600b6 | 原 Step 固定 input；原 Operation prepare→claim→observe；settled 成本和 unknown/reconcile；原 complete_step |
| application/executor.py | b4b9c89f10520dfa7715c38834c0da4206d0ff95db93594377a0a27db02f804e | 唯一原 dispatch boundary，实际 driver 与原 Observation 落账；未持久调用 deadline/起止 |
| application/component_diagnosis_service.py | b73938149e2ba87daf9c4c88ef6b996dfa7b025db3acc922c248d363f0cf965b | _diagnostic_operation_facts 校验真实 succeeded/settled/route/input/output；原 factory verifier；同真实 writer 提交诊断 fact/index |
| domain/component_diagnosis.py | 1d3b07b9a253e56f812e99517841a30b509a584b473f4cce77c014bad871ac3b | 原 MethodRef、RegisteredComponentDiagnosisInputsV1、Observation、Fact、Ref；不是完整执行伴件 |
| domain/affected_recipe.py | f771221639397aa0488e72da13df3427923fe73d6820cd0f8a805f71d1eb8aa0 | RecipeSourceRef 精确 resource_name/sha256 |
| application/media_registration.py | e5e0747af2df54f01235c15d660713e8c90c4e67657b9fcf77e0acc96c35edc3 | Worker 的真实 attempt deadline 与原 registered runner；不能据此推断每次诊断调用已持久测量 |
| infrastructure/qualified_authority.py | f67431c13c0260948e40099735a5197ab61424d308ea9706980588aee69614a8 | 原受认证 reply、真实 member/current/lease；没有资格 source 前后伴件导出 |
| 原 Native qualification_registry.rs 普通副本 | ec436f54ceec091ad649ecf8f887009c1cfc52938bf485e2c6731e7194fc5eee | 真正观察/epoch/record/lease/Process+Job；没有本合同七伴件 serializer |

七种伴件的 serializer、protected archive reader、真实调用 timing journal、消费 commit receipt 和 invalidation barrier **均 NOT_IMPLEMENTED 于上述必要调用链**。这不是宣全机不存在。原类型存在不等新导出存在；旧 Operation.created_at_us 不是 dispatch/finish，succeeded 不是 settled 或消费成功；Worker attempt deadline 不是已导出的每次调用 deadline。缺项必须 not_ready，不能猜值。

## 2. 封闭格式注册表和共同字段

仅允许下列七个 format，无自由 schema 名、任意 parser callback 或通过 outcome 推导事实。全部 version 固定在 format 的 v1；新格式须另行批准，未知格式为 unrecognized/not_ready。Backend 是唯一 domain 定义/serializer，Integration 从冻结 grammar 同源生成 Native reader；本合同不改公开业务 DTO。

| 0066 引用角色 | 唯一 format |
| --- | --- |
| request_ref | diagnostic-qualification-request-v1 |
| result_ref | diagnostic-qualification-result-v1 |
| operation_ref | diagnostic-qualification-operation-v1 |
| consumption_ref | diagnostic-qualification-consumption-v1 |
| before_source_ref | diagnostic-qualification-source-before-v1 |
| after_source_ref | diagnostic-qualification-source-after-v1 |
| attempt_ref | diagnostic-qualification-invalidation-attempt-v1 |

每个 body 的 exact 共同字段为 format、producer_ref、binding、suite_ref、check_id、execution_id、source_definitions；再加第3节对应的 exact 字段。binding 完整复用0066 ResourceCoverageBindingV1；producer_ref 和 suite_ref 均原 QualificationRef；check_id/execution_id 均原 Identifier。execution_id 是同一次真实资格观察的关联 ID，由原服务生成并注册，只是数据索引，不是新 Run、permit 或权限。source_definitions 为按 resource_name 排序且唯一的原 RecipeSourceRef 集合，指向实际 held 文件索引中的定义/parser/exporter/消费者/原 source 代码；不是用户填的路径或 source SHA。上述基线SHA用于说明来源，不假装是未来新 exporter 的 SHA。新 exporter 未写则无合法运行源定义；实施后的真实代码SHA须进入同已准入完整 map/producer provenance，不能填文档SHA或沿用基线证明新代码。

共享 exact 身份 IdentityV1 字段：instance_id、production_id、run_id、operation_id，均原 Identifier。Identity 不含 Owner/subject/permission bool；真实 owner/current/lease 由原强源检验。StepSnapshotV1 exact 字段：run_id、step_key、input_sha256、status（running/succeeded）、fencing_token（严格正I64）、result_body_sha256（Sha256或null）。它是原 steps 行的事实快照；不对原运行修改 status。资格诊断消费可提交 fact 而 Step 仍 running，不伪造 step.completed。

所有 body：原 strict recursive sorted/compact UTF-8 canonical JSON、无重复键/额外键、strict I64/boolean、无 NaN/Infinity、无秘密；原 ref 的 document_id/revision/sha256 和 purpose=qualification_report 保留。原材料/数量/合计/帧限额不提高；单伴件上限2 MiB。大于限额/缺完整集合不能以截断集合证明 absence。QualificationRef 指向完整伴件的 actual bytes；内部 payload/row/raw reply SHA只指相应原 bytes，绝不回指自身 ref。全闭包保持无环。

## 3. 七种 exact body 与允许状态

### 3.1 Request / result

request 额外字段：identity、intent、route、registered_input_ref、payload。intent 完整复用原 OperationIntent 的 step_key/dedupe_key/input_sha256/route_id/reserved_cost 五字段；route 是完整原 CapabilityRoute。registered_input_ref 是原 DiagnosticMetadataRef（record_id/content_sha256/size），指向真实已存 component-diagnostic-input 原 bytes。payload exact 两字段 input_key_sha256、method_ref（完整原类型），对应原 _diagnostic_operation_facts 实际 hashing 输入，不接受 arbitrary provider dict。

约束：payload.method_ref == binding.method_ref；intent.route_id == route.route_id，route == method_ref.route；原 recursive JSON canonical SHA(payload) == intent.input_sha256；输入索引、原 registered member、实际 scope/lease/step/dedupe 必须对应 identity，不从 Test fixture/renderer重建。原 source/body/input SHA均由原服务实读。不同 input、route 或 key 409，不准备新 Operation。

result 额外字段：identity、request_ref、observation_body_utf8、observation_body_sha256、result_json_body_utf8、result_json_sha256。observation_body_utf8 是实际 operations.observation_json 原UTF-8字符串，解析后全量复用原 OperationObservation 的 status/external_id/result_asset_ids/actual_cost/cost_evidence/usage/result_json 七键，原 default/null全部显式；允许 status pending/succeeded/failed/unknown，actual_cost/cost_evidence 原配对不变。observation_body_sha256精确hash该字符串的UTF-8原bytes，不拿重序列化值代替。result_json_body_utf8为真实result_json的原recursive canonical UTF-8字符串或null；其SHA同步非空或null，非空bytes须等于该实际canonical observation body中result_json值的原字节片段。两reader使用原字符串字节和strict JSON token spans比对，禁止用各自float重新编码来猜输出SHA；也不将str容器当不解析的日志。

result_json 保留原业务 JsonValue数据类型，不造第二结果DTO；有限数值只作为该原payload的数据，不改变共同字段的strict整数/布尔规则，也不是通过/权限声明。positive bounded_call 必须 succeeded、真实 actual_cost非null、result_json非null，并经3.3真实已登记消费者的原 factory verifier校验消费。仅有 succeeded/result dict/签名、没有消费收据不能通过。legacy observation 无原bytes、不是上述七键canonical原Observation、cost unknown或无真实result不填默认值；不是任意文本/日志都能装入str容器获准。

### 3.2 Operation / 真实调用时限

operation 额外字段：identity、request_ref、result_ref（QualificationRef或null）、step、status、settled、claimed_fence、input_sha256、route、reserved_units、actual_units、cost_evidence、observation_body_sha256、call_window。

step 为真实 StepSnapshotV1；status 仅 prepared/submitting/pending/succeeded/failed/unknown；settled 为 strict bool且取实际行0/1；claimed_fence为实际operations.claimed_fence（strict正I64或null），prepared时null，实际已dispatch时非null；reserved_units为非负I64；actual_units为非负I64或null；cost_evidence沿原四枚举；observation_body_sha256为原真实 bytes SHA或null。status=prepared/submitting 可无 result；有 result必须与原 result body完全对应。settled真只允许 succeeded/failed、actual_units非null、原 cost evidence已知。成功资格只允许 succeeded且settled真，实际原 Observation和单位数完全一致。历史已settled Operation的claimed_fence不伪改成恢复后的Step fence；actual timing必须绑定原那次claim，不从新fence造第二次调用。未知/未结算保原 reconciliation，不导出“已完成”或重发。

call_window 为null或 exact CallWindowV1：clock_origin_id、started_at_us、started_monotonic_us、finished_monotonic_us、deadline_monotonic_us、finished_at_us、deadline_us。clock_origin_id 为同一真实执行进程/创建期和该时钟实例注册的原私有观察ID，不是 PID 字符串身份；数值均严格正I64。三个 monotonic 字段取实际同进程 monotonic_us；映射 finished_at_us = started_at_us + finished_monotonic_us - started_monotonic_us，deadline_us同理。started_at_us 为真实 dispatch anchor 的UTC微秒；映射用于0066比较，不声称 wall clock 无跳变。要求 start ≤ finish ≤ deadline；origin/采样期间进程变化、缺 deadline、溢出或超时不能 qualified。

新增 timing 数据必须在原 dispatch intent **之前或同原 claim writer**绑定原 identity/intent/fence与实际 active attempt bound；实际执行时从原 runtime control取得 deadline，不能由 Test/renderer 参数或事后给一个大 deadline。真正 driver进出及原 cancel/deadline 检查点由真实受控调用源记录，finished 是实际退出不是 observed提交时间。Core旧Executor没有该 capture，Media attempt_control的实际定义/导出亦未在本卡伪定SHA；Backend与原Media控制源必须以真实已实现 typed成员交接，不能由普通 Callable产生有效bound。若原driver无法证实受控deadline/结果退出就报告 missing，不把线程仍运行/异常/unknown当bounded成功。本合同不修改deadline数值、oracle、取消或费用策略。

原 call timing companion journal 为观察数据，归同 Engine metadata/原 command identity；只记录原发生的dispatch/exit，不授 claim。原 claim成功先于driver、observe/settlement语义完整保持。旧无窗口记录仍 call_window=null/not_ready，不从 created_at_us/heartbeat/日志猜过去窗口。一次既有Operation重复读取复用同窗口；unknown核实前不重开调用。

### 3.3 Consumption：真实诊断 fact 原 writer

consumption 额外字段：identity、request_ref、result_ref、operation_ref、consumer_kind、consumer_source_ref、input_key_sha256、diagnosis_ref、diagnosis_fact、step、committed_at_us。consumer_kind仅 component_diagnosis_record；consumer_source_ref为实际 application/component_diagnosis_service.py的原 RecipeSourceRef；diagnosis_ref/fact完整复用原 ComponentDiagnosisRefV1/ComponentDiagnosticFactV1；step为真实提交时 StepSnapshotV1；committed_at_us来自同writer的新实际receipt，不是后续读时间。

唯一合法生产源为原 _record_component_diagnosis 的原强inputs/current检查→_diagnostic_operation_facts→_diagnostic_check_refs→实际factory-bound verify_component_observation→原issuer.current_guard→真实同writer record/index/events。消费receipt须与原fact/index在这个短writer同事务持久，复用路径核原同immutable fact及receipt后只读复用，不新伪造第一次消费时间。原只读legacy fact若无receipt不能推提交窗口。

解析时必须逐项核 diagnosis_ref大小/SHA原factbytes；diagnosis_fact/input_key与实际request注册input一致；该operation存在于fact.analysis_operation_refs并准确绑定 input/route/原 observation SHA/output SHA；fact.method_ref ==binding.method_ref；真实check的DiagnosticOperationOutputRef指向同原result；原consumer actual factory verifier已校验真实Observation和原输出、source/限制，而非调用者回true。fact被提交不表示组件应重做或版权/计划被授权；只证明这个结果确被该原生产消费者使用。scope/current/两次原真实 authority不删。

### 3.4 Source-before / source-after

两者额外字段均为 instance_id、authority_wire、authority_method、raw_request、raw_request_sha256、raw_reply、raw_reply_sha256、captured_at_us；after另有before_source_ref。wire只允许原 held-resource-authority-v2-candidate；method为before=observe、after=assert_current。before.raw_request exact键为wire/session/seq/method；after在相同四键外加observation_id。wire/method与外层一致，session为原非空受认证会话字符串，seq保留原wire的strict正U64（1..2^64-1），不改旧序号上限；after.observation_id必须等于before真实reply的observation_id。raw_request_sha256取真实发送的canonical body，不回指伴件。raw_reply可为原严格14字段 qualified reply或null，非null时SHA是实际受认证frame的完整canonical body SHA；null时SHA=null，只表示未获取，不能作失效拒绝证明。captured_at_us为实际读后UTC微秒，不代Native observed_at_us。

raw_reply exact keys为 wire/session/seq/status/code/observation_id/observed_at_us/files/qualification/registration_sha256/resource_manifest_sha256/runtime_manifest_sha256/qualification_binding/lease_binding。类型、允许status/code/state/null/排列完整复用停止 infrastructure/qualified_authority.py._reply 的冻结grammar：files为原HeldFileFact、qualification_binding为原QualificationBinding或null、lease_binding为原LeaseBinding或null；session/seq和真实OS peer/current由原受保护连接校验，不能由raw bytes取得能力。

before须为真实 observe成功 qualified/fullfiles/非nullbinding及真实observation_id。after须是原 assert_current_facts 对**同一个原registered before观察成员**进行实际assert_current的真实request/reply；after.before_source_ref准确指向该before，双向frame的wire/session/seq必须一致，same-session seq递增。不能拿新observe成功替老member失效，也不能单凭关闭TCP/管道、epoch描述或source文件SHA相等推失败。原closed409 qualification_changed/revoked/expired/observation_unknown_or_foreign等源拒绝按实际reply保留；或真实200reply的record/revision/floor与before不同且原 assert_current_facts实际产生qualification_changed，两reader重算同一差异。503/timeout/无raw_reply=unknown/unavailable，不满足“已证失效”。真实source变化操作由原Owner/平台控制源执行，不在这里授replace或修改文件。

Integration在原authoritative handler发出的真实reply处记录exact canonical bytes/该注册member关系，Backend的原connection仅受认证接收同源frame并冻结为观察data；不新增公开source观察route或第二issuer。本合同不改变v2旧frame，不将0066待评replace wire当已实现依赖。

### 3.5 Invalidation attempt 与实际无新增副作用

attempt额外字段：instance_id、before_source_ref、after_source_ref、request_ref、attempted_entry、started_at_us、finished_at_us、outcome、error、effects_before、effects_after、driver_entries。

attempted_entry仅 assert_original_source/prepare_original_operation/claim_original_operation/consume_original_diagnosis；对应原真实source.assert_current、Engine.prepare_operation、Engine.claim_operation、原组件消费者四条入口，不能指代任意其它发布/管理动作。outcome仅 rejected/accepted/unavailable；error为null或 exact原EngineError数据 code（原Identifier）/status_code（strict int，400..599）/retryability。v1仅接受本固定源实际出现的never/reconcile，未识别值not_ready，不改变原业务异常允许值。不能由调用方new EngineError产生证明；原实际入口执行捕获。driver_entries为strict非负I64，来自原唯一Executor同capture真实进出计数。

EffectSnapshotV1 exact字段为 production_id、run_id、step_rows、operation_rows、production_spent_units、production_reserved_units、budget_group_id、budget_group_spent_units、budget_group_reserved_units、diagnostic_completions。所有来自原一致性read snapshot而非调用者dict；单位沿原非负I64。group三个字段必须全部null或真实配套；step_rows为原本Run全部StepSnapshotV1有序集合；operation_rows为本Run全部RowV1按id排序唯一。RowV1 exact字段：operation_id/step_key/dedupe_key/input_sha256/route_body_sha256/status/settled/claimed_fence/reserved_units/actual_units/observation_body_sha256，类型同3.2，原真实NULL保留。诊断入口唯一可能新增的completion闭集为本Run诊断 fact/result index/selected index，diagnostic_completions为全部这三类原metadata行的exact有序SnapshotRowV1：family（fact/result_index/selected_index）、key（非空原metadata键字符串≤512）、body_sha256；不能只取有利行或把缺行补成空集合。

上述闭集只对四个diagnostic入口证明无新增completion，不宣全系统任意Bundle/外部副作用absence。生产publish/fullverify/unknown/预算原约束不因此减少。原入口发现可写该闭集之外副作用时，该入口不符合v1，必须not_ready并由原owner补精确source合同，不把未采集事实当0。

通过资格需要：真实after拒绝对应同before source；attempt实际入口在原current失效后被拒，error与真实拒绝一致；driver_entries=0；step/operation/诊断completion全部前后字节相同；Production和共享group成本/预留全相等，无新prepare/claim/observe/收费/fact。一次负向窗口内若有其它合法任务/结算导致共享值变化，本次结果inconclusive，不猜是本attempt零收费；不冻结或偷改其它任务为求绿。effect采样和入口由原真实服务capture边界连起来，前后两份任意取样不能证明无变化。存在旧unknown只保原unknown/reconcile；不把它settle/queue或换key。未执行、timeout或缺snapshot不能满足negative。

## 4. 精确读取、采集与幂等 caller

新增唯一私有导出归Backend，不是新执行授权factory。源侧调用链为 ComponentDiagnosisService.begin_qualification_execution_capture(lease, inputs: RegisteredComponentDiagnosisInputsV1, *, suite_ref, check_id) → HeldQualificationExecutionCapture（eq=False、原service实际注册member/线程/lease/fence/原inputs/source）。方法先复用 _diagnostic_inputs_current和原当前qualified/source/member，只采集观察，不授Operation permit；suite/check必须为原held真实case。Test可调原合法用户/Owner运行路径并选case，不能构造capture/member、Run许可或授收费。

现有OperationExecutor/Engine真实入口和原消费writer在该实际capture scope内记录：原request/input/current；实际claim前的绑定window；原dispatch/exit/observe结算；原消费同事务receipt；原sourceframe与负向入口/前后read snapshots。新方法 capture/export为NOT_IMPLEMENTED，不能用原一般dict返回值冒实现。传typed普通DTO不能注册capture，只有原service已持有实际inputs/lease/source的caller；与当前source不一致、跨线程/实例/Run/fence拒绝。

Backend新增 export_qualification_execution_companion(capture, *, kind) → (QualificationRef, exact_bytes)，kind只有七注册格式。只能从原已采集/persisted对应源事实导出；没有该种事实返回明确 companion_not_recorded，不接受body、result/outcome、callback、fakepermit或自行改过去时刻的参数。同execution/kind原bytes唯一；已有同键不同bytes409；仅只读导出，不执行driver或重新消费。真实采样过程中的unknown必须保原needs_reconciliation，输出不能清它。冷重启只能经同原授权读持久源/原immutable receipts重建观察，不用serializedcapture再grant；旧缺timing/commit/effect capture仍not_ready。

消费者的唯一读取入口为 read_qualification_execution_companion(trust_source, ref, *, kind) → PreparedQualificationExecutionCompanion（eq=False）及 shared verify_qualification_execution_set(trust_source, observation_body) → PreparedQualificationExecutionSet。kind为七格式闭集；先用0066原read_required_ref(ref,purpose=qualification_report,limit)从真实held材料读exact raw bytes，验ref/SHA/canonical/schema，然后验所有本合同cross-ref/实际源definitions、原Suitecase、case/Execution/binding和provenance。每次closure读前后原source.assert_current；不能改成任意 path/URL/body/JSON加载或只信signature。

正向集合关系：同header/execution/binding/suite/check；request payloadSHA=真实Operation.input；result observation/JSON SHA=真实Operation和Consumption.fact.analysis refs；operation.request/result引用精确且settled/费用/Step/窗口合法；consumption.refs覆盖同三件并真实同fact/source。负向集合关系：同before原member→after原拒绝→同request/实际入口→真实effects相等/driver0。request→原input、result→request、operation→request/result、consumption→前三者/fact、attempt→before/after/request的有向引用，不回指上层observation/suite结果/report/record，避免SHA环。

Prepared成员只是已验证事实，短writer仍原current/captures和两authority；SQL外文件/pipe/provenance检查与SQL内本地重核分开。Native对称reader必须冻结相同七grammar和crossrefs，不能用Python一枚true替代。原trust只签原purpose map，不因此证明任意外来case独立/运行通过；独立producer/真实材料源仍需原0066准入与独Review。

## 5. 最小后继、缺件和独立验证

Backend唯一新增私有grammar/capture/export/shared reader，优先复用原Engine metadata和组件fact/index同writer；新receipt存储键按instance/execution/kind唯一、原immutable409。必要schema迁移只归Backend并另交Integration完整producer，不在此执行。Integration在原qualified handler冻结真实frame观察与Native对称reader；Media若需提供原attempt_control真实typed deadline/退出事实，只提供原控制源观察端口，不授新invoke权限，不改oracle/被拒补丁。Test负责真实case与原始结果；Review/Acceptance各自职责独立。本合同不授费用/新资格运行，合法权限/平台/driver/provenance仍未就绪时not_ready，不能伪造可运行capture。

最小独立正向：实际同method/route/source的原合法调用，真实窗口、settled费用、原fact同writer消费和exact七body/ref可被两reader共解析；真实旧member失效后原入口拒绝，原账本/effects不变且driver0；原Operation去重/原immutable receipts跨fence只读复用；后补相同缺失材料可以继续，未重复调用/收费。

反向必须拒绝：未知/extra/重复key/错format、弱数字/default填充、错case/binding/producer/sourceSHA；created_at伪窗口、deadline事后放大、线程仍运行、wrongclock、无原bound；succeeded但未settled/unknown费用；有result但无原consume/fakefact/时间猜测；变造result/route/input/source/ref/跨Run；新member代旧member、无真实reply/timeout当失效；effect只截部分行、共用budget变化、driver已入、旧unknown被清、新dedupe重发；record/json/signature/Testfixture自行造capture。正反验证与原oracle不改；本阶段0产品/SQL/native/模型/网络/测试/费用，所有具体运行资格保持未验。
