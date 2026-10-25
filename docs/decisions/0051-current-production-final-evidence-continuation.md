# ADR0051 — 同 Run 最终证据等待、继续与有限修复

状态：APPROVED_DESIGN_ONLY；2026-10-10。仅补最终成包接缝，不修改 ADR0049/0050、原规范、质量阈值或现有付费/ASR审批。完整 R1 独立验收后连续完整 R2；本地免产品注册/BYOK、五步 UI、一次预授权的 API/MCP 自动制作、安装实例持有数据与三 OS 目标保持。设计批准不等于资源准入、实现、运行或作品验收。

## 固定事实

任务卡 SHA `8dd0b4a933444d96e49bdc614a506c184468545c6993c9ba02a53ee9d4e1481d`。Backend/CurrentProductionBlockerImplementation/Gap-ProducerWaiting.md `e3bcbbf2c4e57fc8cd2316fcf98357c3188d8a14c1d856e5dc521ba4797c2d49`、JSON `c84521403c46f51e8201210d361782e6ab43b571e3bb61f204c91d715aaf1e26`，四份 ProducerWaitingInputs 普通副本：MediaBundleProducer `5c6156f36e1e2dd502979c20f9fea4866781bac811dd8d87d28ad1032365b23a`，OriginalBundleService `7d88ba046b4d39590a4527e8270af0be43b9c3d8eef4240cec036c22e68c6538`，OriginalBundleValidators `504649b976d62abf0fb0875e5659a528d348414489d2640daefda06775754083`，CurrentRuntimeWorker `9eb3fef8a356ee02203c41e381fe7c74da1477894feeb2e0e6ad2a0969b0ae06`。Backend 最终 SourceIndex `f4abd9bab3e06d4ae8ebc755932808619c724d10d237cdc22da10f54d2cfe08d` 是 103 源固定交接身份，不是运行通过。

原 Bundle._block:1175–1187 写 quality/waiting_revision 并释放 lease。原严格验证:2264–2294 将报告/authority缺失、authority拒绝、绑定错误和 P95>200ms 混为 alignment_required；不能按同一错误码自动恢复。Media:414–429 只把该码捕获成旧 BundleProductionResult.waiting_user，v2 Runtime 不接受这个 postproducer 结果。真实成包验证:1255–1314、0.3验证:2296–2489 仍是唯一质量/身份/许可来源。prepare:852–891 保持原 intent/material allocation；READY 材料和已保存 Manifest SHA 不可原地改写。

## 1. 唯一准入及返回 ABI

Backend 唯一定义私有 strict/frozen、extra-forbid 的以下类型及服务实现；不新增公开状态、Manifest 字段或路由。Media 仅消费，不创建判断、权限或 metadata。v1 原 verify、_block、等待结果与请求默认语义保持。

v2 受信 Runtime 创建原 BundleService 所持有的 `CurrentFinalEvidencePorts`，绑定实际 runtime registration、同 Production/Run/request/lease/fence 及原 preparation。该对象通过原已批准工厂私有参数 `final_evidence_ports` 交给唯一 Media producer；默认 None 仅维持 v1，v2 不可缺省、从 HTTP/模型配置生成或退回 legacy。不能把任意 callback、布尔或序列化 DTO 当此 port 的身份。

准确服务入口：

`BundleService.verify_current_final_evidence(ordinary_lease, preparation_id, manifest: BundleManifestAny | None) -> CurrentFinalEvidenceAssessment`。

该入口复用原完整 verifier 与当前 evidence_registry/validators；实现共享校验分支，禁止复制一套较弱规则。必须在旧 _block 写 quality/释放 lease **之前**按真实原因分流。0.3 原 verify_alignment_evidence 的实际运行报告校验也纳入此边界，不能先由旧入口写等待再重新 park。原准备、完整材料字节/路径/SHA/类型、所有 settled Operation、原许可/审批/source/current、decoder/frame/QC、时间坐标、最终 publisher 规则仍逐项执行。

Backend 私有可序列化 `CurrentFinalEvidenceSnapshot` 完整字段：

| 字段 | 唯一含义 |
| --- | --- |
| preparation_id | 原 BundlePreparation 实际 ID |
| preparation_intent_sha256 | 原 canonical intent 完整 SHA |
| candidate_manifest_file_sha256 | 完整候选 Manifest 文件字节 SHA，未形成完整候选时为 null；不是 canonical对象摘要 |
| ready_material_refs | 原完整 MaterialReceipt 元组；实际数据库及文件重核，非 renderer 提交 refs |
| state | waiting_evidence 或 repair_required；ready 不作为持久等待记录 |
| reason_code | Backend 从具体校验分支产生的安全 Identifier |
| dependencies | 原请求所需的 `FinalEvidenceDependency` 元组；不得扩 scope |
| repair | 原真实失败所对应的 `FinalEvidenceRepair` 或 null |

`FinalEvidenceDependency` 完整字段为 kind（work_validation / method_qualification / independent_reference / precision_measurement / verifier_resource）、completion_kind（consume_ready_evidence / generate_runtime_report）、target_artifact_id（原 allocation 的 ID或null）、expected_schema_kind（原 SchemaKind或null）、source_ref（原请求/政策/qualification/authority的实际版本化完整引用或null）、reason_code。null 只表示该项目前没有可真实定位的来源；必须保具体 NOT_READY 原因，不能由模型补来源身份。generate_runtime_report 仅允许本片真实运行验证报告，或已具备真实独立参考后的确定性本片测量；不允许生成独立参考、算法资格或authority。缺这类本片报告不是永远等待它自发出现。

`FinalEvidenceRepair` 完整字段为 failed_check_code、source_report_ref（真实完整报告 artifact/material ID及完整文件SHA）、affected_artifact_ids（原候选实际受影响子集）、failed_unit_ids（报告实际单位）、allowed_action（realignment / regenerate_affected_media / guidance_required）。Backend 只根据实际失败报告和原计划/当前策略的动作范围确定 allowed_action；没有许可时只能 guidance_required，不自动升级权限。

`CurrentFinalEvidenceAssessment` 是 BundleService 实际持有、eq=False 的短期受控对象，成员为 assessment_id、binding（原 ProductionBinding）、snapshot（上述等待快照或null）、verified_material（原 VerifiedBundleMaterial 或null）。只能二选一：ready 有真实 verified_material；等待/修复有 snapshot。服务按同对象身份/当前线程或受控调用作用域/原 lease/fence 检查，不凭字段或 token 文本授信。该对象和原 30 秒验证 token 均不写 journal、不跨进程恢复、不当许可票。

manifest=None 只允许实际 preparation 已存在且**原 allocation 中必要最终证据尚未 READY**的等待检查；从实际已 READY 音视频/文本及原 request 推导依赖。缺普通视频、四 masters、稿件或实际 ASR 输出属于原制作未完成/具体失败，不借 None 伪装最终报告等待。None 不能返回 verified_material，也不能发布。完整候选形成后必须提供真实 Manifest 并重跑全部校验。

在原 finish_v03_evidence/报告staging之前，同 ports 的 `resolve_inputs(ordinary_lease, preparation_id) -> CurrentFinalEvidenceInputs | CurrentFinalEvidenceAssessment` 实际核依赖。CurrentFinalEvidenceInputs 是服务持有的非序列化对象，成员为 binding、preparation_id、preparation_intent_sha256、ready_material_refs、resolved（原registry真实返回的完整policy/qualification/benchmark与来源作用域，不是新DTO声明）。输入齐全时 Media直接生成原本片确定性报告并继续，不先park；确缺原可信输入/资源时返回受控等待assessment。该对象不是执行许可，保原rights/plan/current/operation guard。旧strict本片测量使用同端口实际已获准参考解析来源，不能把旧版本升级为0.3。

Media 的原 BundleProductionResult 仅加默认 null 的私有成员 `final_evidence: CurrentFinalEvidenceAssessment | None`。v2 增加 state=waiting_evidence / repair_required：必须附同服务真实 assessment，原 preparation/receipts 与 snapshot 一致，bundle_ref=null；published 必须真实 bundle_ref 且 final_evidence=null。Runtime 按受控对象识别这两种结果，不按字符串或旧 waiting_user 转型。ready 时 Media 使用 assessment.verified_material 调原 publish；不得再次调用会触发旧 _block 的 legacy verify。

## 2. 缺失、失败和真实审核分开

- 可等待：确实未配置/未安装的原获准 verifier resource；真实所需独立参考/测量/运行报告未到达；原 method qualification/benchmark 的可信来源或必要许可闭包尚未就绪。写确切依赖和原因，不将 false authority 回调解释成“仅缺资源”。
- 可受控修复：有真实完整测量报告且 P95>200ms；真实可定位的时序/QC失败。保持失败报告和原单位，按本节 repair 范围继续；不能通过 resource resume、真人“通过”或改报告数值使失败作品达标。
- 损坏/伪造/来源或正文不匹配、无权披露、非法坐标/单位/依赖循环：保原 422/403/409 精确错误，不写等待来掩盖非法输入。authority明确拒绝/撤销不等 authority不存在；不得自动换 issuer/criterion/policy。
- 真正人审仍有原实际 waiting_revision_id 和原 ReviewDecision；等待最终证据不创建 quality、人审 revision、Owner action 或 approval。guidance_required 表示真实指导/修改或原有限权限不足，不能拿通用“审核通过”替代精度证据。
- 旧严格请求/strict_reference_v1 继续要求完整独立参考及本片实测。显式获准 0.3 自动策略、真实 qualification/benchmark/work validation 完整且允许无本片参考时，不等待本片参考：保持原 not_measured/指标 null，不造 PrecisionEvaluationReport、不复制算法基准分数。原抽样 P95≤200ms/MM05门槛不改。已有测量则必须保留并验证，超阈值不能降成 not_measured。

## 3. 精确停止 writer 与持久 checkpoint

Backend 私有 `RegisteredMediaRuntime.park_current_final_evidence(ordinary_lease, assessment) -> None` 为唯一 writer。只接服务所持有的真实等待/修复对象；短 writer 检查原活 lease/fence/cancel、最新同 Run、完整 request/binding/registration、实际 preparation/intent/receipts及 assessment身份。停止是 denial-only 边界，按0050不要求给已失效执行权重新授信；不放宽后续执行 guard。

原 metadata 唯一 key 为 `current_production_final_evidence:<run_id>`。`CurrentFinalEvidenceJournal` 恰有六个 required 字段：format=`current-production-final-evidence-v1`、binding、snapshot、control、blocked_at_us、last_transition_at_us。control 恰为 phase（waiting / queued / executing）、resume_mode（retry_final_validation / repair / null）、execution_fence（当前恢复 lease 的真实 fence 或null）。初次 waiting 的后两项必须 null；blocked_at_us 为真实停止时钟，后续不可重置。canonical/SHA只作 CAS，非权源；时间同原整数微秒规则。没有新表/迁移。

无 unsettled/submitting/pending/unknown，且无真实人工待审时，原子写 waiting journal、同 Run waiting_user/waiting_revision_id=null、释放 worker/lease，最新 Production 同步；事件 production.final_evidence_blocked 关联该日志SHA。原 fence/attempt/预算/counters/Operation/资产/分配/审批/floor不变。SQL回滚不留半记录；同 key 非同一来源快照拒409。恢复后再次缺证时，仅当前executing checkpoint的真实活lease/新fence及同源受控修订lineage可CAS回waiting并更新实际snapshot，保原blocked_at及历史事件，不从旧waiting/queued记录任意覆盖。重复已成功释放的结果仅观察，不再次 park/写事件。

有真实未结算/unknown 时转原 reconciliation，不清日志/费用、不重发 Operation；不能把 prepared改名unknown，也不凭结果标签造核实状态。cancel/pause和真实人审沿原流程。旧 legacy _block 已释放的 lease 只观察原真实等待/修订；不能用它新建此日志、重新挂起或自动把历史人审改为证据等待。新v2必须走前置入口防止再次产生此接缝。

## 4. 可以实际接续的唯一调用路径

`RegisteredMediaRuntime.resume_current_final_evidence(run_id) -> (state, reason_code)`；state 仅 queued / still_blocked / guidance_required / not_blocked / needs_reconciliation。唯一生产调用方是原 run_registered_worker 的固定 v2 循环，在 acquire 前，与0050资源候选共用“每poll最多一个、同Run至少5秒”预算；按明确run_id只检查该Run。非once worker 在依赖真正到达后自动继续；once只探测一次；停止后不探测。不开全局startup恢复、新队列/调度框架、HTTP/MCP管理入口或ASR后台hook。安装可信worker仍是未启动实例的原接续入口。

writer外读取真实候选/完整journal、原 READY材料与新增报告的真实来源/许可/registry当前资格、完整源/资源current观察；探测不运行provider/ASR/model/FFmpeg，不创建报告或资产，不下载、不收费、不替Owner行动。恢复身份按0050同服务持有的 `_authorization_identity(实际Production owner)`、原 issuer.current_guard(registered)，保原 native/session/qualification held作用域；不是释放lease、模型Owner或JSON。

Backend增加唯一有限 helper：

`ProductionAdmissions.assert_final_evidence_resume_current(connection, guard, *, run_id, binding, journal_sha256, resume_mode, affected_artifact_ids) -> None`。

它识别原同线程活guard，复用0050真实 _guard/_request/_bound/当前或实际derived policy与原Scope/控制floor来源。unattended 必须当前 begin_execution/原计划及下一阶段动作范围；repair 还需当前 original plan/quality facts及相应 repair action 的有限范围，不发新 policy/fact。interactive 保当前原Owner有限声明与实际既有审批，只允许原已准后续校验或修复，不造 unattended授权/人审。源撤销、过期、替换、显式AuthorizationWait保留，交原真正重授权路径，不以报告到达清空。

短writer内重核同journal字节/SHA、原 preparation/intent/READY receipts及候选身份、最新waiting/null revision/无worker lease/无cancel pause终态、无unsettled unknown，并在原current guard内核当前源/资格/scope。writer内不做RPC/文件I/O；writer外真实材料/held current检查跨writer保原观察保护，若资源/报告可变必须由原held/不可变READY材料保证当前，单次hash不够。资格拒绝/依赖缺失保持具体still_blocked；损坏422、竞争409不覆盖新状态。

满足当前真实性与scope时，仅原子将同journal.control改queued/resume_mode/执行fence=null，同 Run及最新Production queued，发 production.final_evidence_resumed；旧 blocked_at/binding/snapshot仍保留为实际 checkpoint，不能删除后丢 preparation/修复目标。consume_ready_evidence 必须真实到达并验证；generate_runtime_report 只要求真实获准输入/资格/资源和原受控报告producer已就绪，允许queue后生成报告，不要求报告先在等待态生成。预检不得声称最终校验通过；scope不足或没有可真实调用的producer保具体still_blocked。排队不是许可，不生成/扣额度。正常 acquire 新lease/fence/attempt，Runtime在同活 lease+真实重新begin/plan/current guard下调用 `claim_current_final_evidence(ordinary_lease) -> CurrentFinalEvidenceContinuation`，原子CAS control.executing及新fence。返回只读 continuation 成员为 binding、snapshot、resume_mode、execution_fence；这是本Run进度输入，不替代执行权限。queued checkpoint允许原队列acquire；waiting checkpoint不得被普通过期lease恢复成queued。

claim必须核同真实request/registration/preparation；保原费用/计数。kill在queue后、claim前或执行中按原真实ledger/lease恢复，checkpoint保留；executing只有原真实ownerlease可转换，不能旧fence重放。恢复时所有正常 guard/最终许可/实际报告校验重做，不能复用30秒验证token、旧begin/planfact或assessment。最终发布后原publisher的实际成功才可归档/删除精确checkpoint，crash后先观察实际published Bundle，不二次成包/写成功。与0050日志或真人等待同时存在且阶段冲突拒409，不择一绕过。

## 5. 报告到达、版本与有限修复的实际生产路径

同 Run、同 Production、原approved script/plan及已settled四masters/ASR等Operation不重生成。已经READY的材料不能替换；已保存Manifest SHA不能覆盖。若仅原 verifier authority/resource 后来就绪且候选字节不变，继续原 preparation，重新原验证/发布。若缺报告slot已按原intent分配且未READY，则原有正确SchemaKind的 allocation可由原受控staging填入实际报告；不得给READY receipt换正文。

若新证据或修复改变已READY的报告/文本/音频/字幕/quality或既有Manifest，必须在原Bundle同Run的真实修订链创建新bundle_revision/preparation intent；明确 parent preparation/revision及实际受影响材料，保原报告/receipts/分配/全部副作用ID，引用可安全复用的实际旧Asset。不能以新增material伪造旧preparation完整性或偷偷换请求/政策。新allocation是合法新修订，原allocation仍唯一；新许可复制范围依原权限和完整祖先闭包重核。Backend唯一维护此原controlled修订入口/lineage和完整SchemaKind，不扩公开grant或依赖披露。

取得新lease后，Media唯一本轮生产入口 `continue_current_final_evidence(*, ordinary_lease, continuation, policy_execution_ports, control) -> BundleProductionResult`。它由原受信工厂持有实际BundleService、原driver/decoder/ASR观察端口；参数不接受外部任意factory。Backend的v2 invoke先识别原queued checkpoint，正常新begin并重新admit实际旧plan/quality与当前权限，然后claim并调用这个入口；不重跑上游创作/四masters来“开始新任务”。Backend须先重获原ProductionRightsFact/document及真实plan/quality admission，Media才能取证/修复；不将 request-bound rights_proposal 当执行权。沿原ledger/预算、控制deadline/cancel/fence、source/license/实际原Operation观察执行，最终调用第1节验证入口与原publish。

retry_final_validation只做原允许的证据生成/接入和最终验证：WorkAlignmentValidationReport由Media确定性读取原真实ASR child-observed identity、原operation result、全部实际音频/文本/字幕/映射/检查，Backend registry验证并返回完整获准policy/qualification/benchmark引用。旧原ASR观察若缺实际OS/config/资源/runtime身份，不能用宿主hash补全；明确缺证，只有原实际已准执行路径获得真实观察后才能继续。该合同不启动被拒ASRsupervisor或授新调用预算。

method benchmark/qualification的独立基准由原独立Test/授权证据生产方按固定标准生成，Backend原registry执行真实来源/资格/许可/撤销准入；Integration包装完整合法分发和实际安装资源，Media不自行签发算法资格。strict per-work参考由原可信独立听审/仲裁证据来源生产完整PerWorkReferenceDocument，Backend原authority校验、原allocation/staging接入，再从真实参考+实际alignment确定性计算报告。听审缺资源仍明确等待，不由模型/HMAC/通用基准制造本片独立性。显式0.3获准自动无本片参考路径不依赖逐作品人工标注，需本轮R1真实接通、完整work report及null语义，不能永久等待当完成。

repair在同Run原预算/实际允许动作中只重做受影响步骤；原frame/media生成或ASR有新实际副作用时创建原正常Operation并入账，保旧Operation与失败报告，不reset预算或复用unknown。无自动repair许可返回guidance_required；许可具备却实际预算/重试/期限已耗尽，按原有限失败终态，不无限重新queued或换任务名。Backend有限终态入口 `finish_current_final_evidence_failed(ordinary_lease, assessment) -> None` 仅凭该服务真实当前失败assessment与原账本实际limit/deadline结论，在同活lease/fence下沿0050 denial-only规则结束同Run；没有未结算/unknown才failed并释放lease，保实际报告/费用/counters与checkpoint审计身份，不能通过reason字符串或旧lease终结。guidance_required不自动当failed；损坏/非法证据仍由原错误终态处理。修复后新实际报告必须重新满足同阈值，实测失败、来源拒绝或非法证据在原有明确终态/指导路径呈现。不能改reported P95、复制benchmark分数或删measurement避阈值。

## 6. 角色接缝、后继和独立验证

Backend：唯一定义上述私有类型/受控assessment、共享真实校验分流、原prepared/READY修订lineage、journal writer/resumer/claim、Admissions helper、同workerloop与实际inspect接线。Media：工厂传入/消费真实ports，完整 report生成/来源引用和受影响steps继续，原uniqueproducer/publisher不另造总流程。Integration：真实完整资源/authority/benchmark许可包装和固定注册caller ABI；唯一公开Schema/SDK仍由Backend源生成，若仅私有增量不得另手写公有字段。Frontend：五步界面区分缺具体证据、实际待修复、真正待审，不加每作品伪确认。Test/Review/Acceptance各自独立，不将本ADR作测试通过。

独立必测：严格缺参考/authority不存在与authority拒绝/伪报告区分；完整0.3无本片参考自动发布且指标null；实测P95>200ms绝不被资源重检/真人通过/改not_measured发布；真实scope允许的修复后真实新报告达标；无权限/预算耗尽有界结束；报告到达后同Run queue→新fence→真实begin/plan/current→原最终publish；None候选/材料missing/READY换字节/Manifest覆盖拒；报告材料及许可来源完整闭包；released/stale assessment/伪serialized result不重park；SQL回滚/CAS竞争/cancel/pause/真实人审/AuthorizationWait/政策与资格撤销；old v1兼容；queue/claim/publish各窗口真实kill后单副作用/原budget与操作唯一；unknown保持核实、不重发；全部真实音视频/文本/ASR/微秒坐标/RAG和完整bundle实际成片仍验。

固定Integration资源请求已指出Piper/Wan绑定与Wan未配；真正本地素材/BYOK factory替代已是独立后继LocalAndByokProductionFactoryContract，不扩本卡。其缺实现不能被此证据等待判为本地工具完成；原四masters/Operation/权限不变。当前所有真实资格、可用资源、独立报告、三OS、最终作品及R2资源仍按真实证据not_ready/待验；本契约给可实施接通路径，不虚报通过。

本阶段仅固定普通源码/规格只读与架构文本写入，未运行产品/SQL/模型/媒体/Owner/native/网络/收费。旧ADR0049 SHA `59743e9ae79c6998c1540b3fdb4e5cb68788926e95720a2da28cd1ab3ca27e68`、0050 SHA `4ae9376326e5f52d09cce2fcd96d884985d0e906b1cce8b423426d2d81d19dc4` 保原字节。
