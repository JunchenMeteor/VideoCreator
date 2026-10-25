# 0060 — 完整失败评估与诊断的同源连接、受控续步

状态：APPROVED_CONTRACT_ONLY。架构准入设计；不是独立评审批准、实现完成、运行授权、质量通过或 R1/R2 验收。任务 CombinedFailureDiagnosticJoinContract，含固定 BDE-P01/P02。原0058/0059、原公开版本、200000us、两次真实 authority、权限、预算与限次不改。R1完整自动创作/本地免注册/BYOK/五步工作台/API/MCP/多模态交付/三OS后连续R2的目标保持。

## 1. 已核事实与最小变更

仅消费停止127普通源，不读热 Review/Test/Backend。原 verify_current_final_evidence 在274调用一次 self.verify；275–305将真实 _FinalEvidenceProblem 转成原 precision repair 或 evidence wait，并立即返回；306的 diagnostic_block_after_verified 只有验证成功才可到达。诊断与精度联合失败的连接缺口确实存在。Runtime._probe_final_inputs 161–163 对 waiting_diagnosis 无条件 still_blocked；park已释放lease，claim/read诊断只接受真实executing，因此没有等待后的实际续步出口。两项都是 SOURCE_STATIC 缺口，未运行。

立即失败出口可复用原 held assessment、四诊断端口、明确 record、原 park/resume/claim。必须补两处最小私有数据：现 DiagnosticSnapshotV1 不存原 reason/dependencies/精度闭包，需按准确 journal SHA 读取的源伴件；同输入的不可变 inconclusive observation 不能靠重试或时间戳变成新输入，真正补充证据的分析输入需一个严格v2 grammar。不新增公开DTO/公共授权接口/新Run/调度层；不改旧 journal/Facts/commands 的原字节，不引入第二套诊断权源。

完整调用结束指原 self.verify 返回成功或抛出其原真实失败，不代表它已执行所有后续关卡。例如精度失败发生在 rights/final writer 之前。任何保存的失败来源都不能声明未执行的关卡通过，不能生成 VerifiedBundleMaterial 或跳 publication_guard。不能复试被拒的 pre-verifier earlyreturn/checkpoint，不能为分支选择再调用第二次整体验证。

## 2. 原验证结束后的唯一连接

Backend保留 verify_current_final_evidence(lease, preparation_id, manifest) 的原返回类型/权限端口。内部有限拆分为“原一次调用及原失败投影→连接额外诊断拒绝→保留assessment”，不能移到原调用之前。manifest=None的前置缺材料出口不计完整验证失败，不能冒充已验证结果。

新增服务私有方法 join_current_final_diagnosis(lease, preparation_id, manifest, *, outcome, diagnostic) -> CurrentFinalEvidenceAssessment。outcome 是本服务/本lease/同thread登记、短期held的真实结果，只能由本次原调用的成功、原 _FinalEvidenceProblem catch 或下述准确QC throw现场建立；diagnostic 为本次实际registered纯 reader/record返回的 RegisteredComponentDiagnosisV1 或 None。用户/模型/renderer不能构造outcome、选择错误code或用JSON恢复held身份。方法不调用wholeverify、provider、ASR或新的诊断Operation；没有当前diagnostic时保原结果，原成功额外拒绝仍复用已有helper语义。

原精度 catch 先完整建立原 CurrentFinalEvidenceSnapshot/FinalEvidenceRepair：准确 MaterialReceipt、真实report bytes及audio/alignment/reference/criterion、max(start/end)>200000us failed_unit_ids、原依赖闭包、failed_check_code/allowed_action全部保留。连接时只增加诊断事实，不改原分位数、null、闭包、原因或标签。diagnostic的precision_report_ref及failed_unit_ids须和此真实源相等；旧诊断输入尚无该报告、不同report或失效source只能409/请求新证据分析，不能把它暗改为当前报告。

report=None 的 _FinalEvidenceProblem 保原依赖等待理由；可以在真实supported组件诊断存在时加入组件修复来源，但该组件修复不能补造 independent reference/authority/qualification 或清除原依赖。diagnostic为timing_only/no_component_failure不消除原失败：纯精度仍回原realignment；缺证据仍回原dependency路径。information_required保原失败并等待明确补充；component_repair保组件闭包，另保原精度闭包，不能取二者union作为新的生成授权。

泛 EngineError 原样传播。仅允许准确 bundle_quality_incomplete 的原2723–2725检查现场，在原current-final scope内部产生私有held QualityFailureFacts；必须捕获该throw现场的真实quality MaterialReceipt/正文SHA、quality_ref、required_check_ids和实际非verified/缺失check_ids，并保当前候选/实际readset。外层只接这一个准确held marker；不是根据 error.code/status/message 做宽catch。若该现场不足以取得准确READY正文/原revision关系、diagnostic没有当前supported/明确inconclusive事实，保原 EngineError，不造quality失败报告或waiting成功。其他identity/integrity/rights/许可/authority/source/未settled错误不进入此分支。QC失败也不意味着其后rights关卡执行过。

outcome分类严格为 precision_failure、evidence_wait、quality_incomplete、verified_then_diagnostic_block。前二者携原完整snapshot；quality_incomplete携上述准确quality事实且original_snapshot=null；成功额外拒绝携原成功调用事实但不持久/恢复verification token。同prepared/source多条不同diagnostic ref不能选latest，仍409；必须由当前registered input/已选择ref唯一确定。

## 3. 一个私有源伴件，journal旧字节不动

新增私有严格格式 current-final-diagnostic-source-v1，Backend唯一定义/写入/读取。它只保存来源与续步计划，不授执行。以 metadata 的 key `current_final_diagnostic_source:<run_id>:<sha256(exact_journal_body)>` 存不可变canonical正文；正文不回填自身SHA，journal不引用伴件，因此无哈希循环。hash只是定位；真实作者为原park/queue/claim短writer及其held/current来源。

必填字段：format；binding；journal_sha256；snapshot_sha256（canonical(snapshot) UTF8完整SHA）；preparation_id；preparation_intent_sha256；candidate_manifest_file_sha256|null；ready_material_refs；origin_kind；original_snapshot|null；quality_failure|null；diagnostic_ref|null；diagnostic_input_key_sha256|null；previous_source_ref|null；resume_context|null；authored_fence。SourceRef仅含真实metadata record_id/content_sha256/size，不是任意URL/身份声明。origin字段互斥，完整READY/parent/候选关系须和journal一致；original_snapshot保原所有report/failed_units/dependencies/闭包/reason/allowed_action，不能仅摘要。quality_failure使用第2节准确事实。origin为success也不持久VerifiedToken。

resume_context严格字段：work_kind（reuse_record、analyse_changed_input、final_validation_after_analysis）；previous_waiting_journal_sha256；previous_diagnostic_ref|null；registered_input_ref（实际不可变input metadata的record_id/size/SHA/input_key）；completion_source_refs；expected_diagnostic_ref|null。它不存未产生的OperationID；已有真实completed record才可给expected ref。最终执行目标/权限仍原plan authorizer；context不是修复command。

park先服务held来源检查，再按原current guard/lease/thread/TTL、prepared/source rows、settled和wait conflict检查。同一原SQLite短connection：以old exact journal CAS写new journal，再INSERT准确new journal SHA伴件；已有同key/body原样幂等，不同body409；最终重核全部源与current后提交，任一步失败整体rollback。大文件/注册资源/纯verifier在SQL外。source检查不能因自己的CAS忽略其他metadata/READY/route/Operation行；只按已有assert_diagnostic_assessment_writer checkpoint_body规则，先核确为自己的准确新journal，再排除已获准的那一旧checkpoint捕获项。

queue/claim/park/failed-finalization均在同短writer将原已选source复制为新的exact journal SHA伴件，保previous_source_ref形成显式历史链；只改变确实发生的control/fence/resume_context/新诊断ref。blocked_at、计数、原失败内容不重置。新source lookup从准确当前journal body派生，禁止latest、清指针或仅凭snapshot相似选择。source链不得形成循环；只沿既有当前Run/selected parent路径，不用它扩祖先许可/授权。旧普通v1 journal不要求伴件且完全沿旧路。

旧0059 DiagnosticJournal无伴件不能被反解释为precision通过。Backend可在真实Owner current、准确旧journal/ref/readset及原Operation纯重核之后，写compatibility来源 origin_kind=legacy_diagnostic_block（唯一兼容例外）；保准确旧body/ref/所有实际失败报告，completed whole outcome保持unknown。它不是“成功origin”；旧source未证明的gate继续待原最终验证。禁止从candidate SHA或模型意见补成功史。原已记录真实precision repair若可读取则逐字携带，无法证明历史失败上下文则明确original_snapshot=null且reason historical_assessment_unavailable。旧immutable记录损坏保持409/422，不能repair字节。

## 4. waiting_diagnosis 的实际恢复，而不是强queued

仍使用原 Runtime.resume_current_final_evidence(run_id) 为可信原worker loop/明确原Runtime管理调用入口。不得从全局startup盲恢复，不给Media SQL或自己造continuation；普通窗口关闭与制作cancel仍分开。waiting_diagnosis改为调用 probe_current_diagnostic_resume(journal, exact_raw, source) -> held DiagnosticResumeProbe | concrete blocked result。这是Backend服务私有、当前Owner/同binding/no-lease检查，不能调用带伪lease的 _diagnostic_factory 或假的Worker。外部补材料/指导仍走原受认证资料/feedback接口；接口本身不能直接queue。

探针不dispatch分析/settle/rewrite observation，SQL外验证准确被引用READY/反馈正文/原安装资源；原Owner issuer current_guard、registered原registration SHA、request/项目/source scope、原parent/assembly/current journal及原失败source均必须可读/当前。资源就绪由同原安装coverage/真实held resource authority检查取得；只有配置文件或Bool/相同哈希不能证明就绪。没有实际绑定producer/纯verifier则具体503/not_ready并列原Backend+Media+Integration接入责任，不能永久用缺入口当完成。

允许有意义续步的三类真实变化：新增且当前被请求的READY补充材料；原受认证实例/Portal/用户已持久的feedback/指导revision；同一批准资源catalog内，原明确缺失项现在经真实安装/held authority证明可用的资源完成事实。缺少precision报告/新reference亦只能消费真实允许来源。不得修改原masters/READY字节、原完整计划/rights或原registration/resource identity。更新到不同注册/route/资源版本须走原Owner实际重新准入，不在此自动重绑。

资源完成事实由Backend在原resource observer/current source守卫实际返回后登记不可变 completion metadata，字段限binding、原缺失项、当前准确qualified/resource/source refs及其正文SHA、原等待reason、原安装观察来源ref。其record_id/size/SHA为completion_source_ref；这是已观察事实，绝非新的authority。当前writer必须再次调用/消费原实际assert_current，不接受renderer送来的相同JSON；若现有observer没有所需资源观察入口，Integration补它的有限普通ABI后Backend接入，不能把普通脚本的文件存在当qualification。

探针结果矩阵：同输入已有succeeded/settled诊断→纯读取并复用，不新Operation/费用；同输入但原Operation submitting/unknown/unsettled→needs_reconciliation原核实，不新key；没有原实际required补充/资源变化且原record仍inconclusive→still_blocked具体缺项；新真实完整sources满足时→持有新input registration及显式previous_ref关系，然后原current+CAS排同Run下一续步。单纯时间、重试按钮、随机nonce、窗口重开、反馈空白重复或变key要求不算输入变化。

## 5. 严格新输入grammar和同输入复用

仅确有第4节补充源需要时，新增私有 registered-component-diagnostic-input-v2 metadata envelope；顶层仍只有format/stable/analysis_intents，stable.format=current-component-diagnostic-input-v2。stable复制v1全部原字段并增加 completion_source_refs：真实反馈 c.RevisionRef、同prepared/原允许来源 MaterialReceipt、上述真实resource completion SourceRef的严格tagged union。至少一个实质不同的被请求source；每项闭集、稳定去重、准确身份/正文SHA，不含墙钟、fence、attempt nonce或verification token。previous_ref存源伴件/resume_context，不作为人为轮次盐重复改变同源key。

完整recursive JSON canonical沿原affected_repair_service.canonical_body/plan_payload_bytes：显式null、严格类型、mode=json模型叶、sort_keys、compact、UTF8。不得把dict传只接受model的engine.canonical，不得JS JSON.stringify代服务源编码。Input key=该完整stable body SHA；原Step/dedupe模板仍component-diagnosis-key32-methodSHA16，reserved_cost原route上限。v1的原key/body/step/dedupe字节不变；同v2 sources/current method相同则同key/Operation。无需变ComponentDiagnosticFactV1或ObservationV1：原ref输入SHA指向准确v1/v2注册源，checks允许的补充refs闭集由该source重建，Fact的precision_ref/failed_units及source媒体仍原真实值。

RegisteredComponentDiagnosisInputsV2 为Backend唯一私有held增量：包含原V1全部字段及completion_source_refs、registered_input_ref；eq=False、同服务/lease/thread登记，不是第二公开DTO。prepare_component_diagnosis保原调用默认；新增私有 keyword resume_probe=None，仅消费原Runtime登记的当前probe/continuation。probe在新的actual lease下由claim重建受控held身份，不能把旧lease/thread对象跨进程序列化当授权。record_component_diagnosis与纯reader严格按已存input format dispatch，v1原bytes/parser兼容；未知版本422。

每个completion ref既要进入新key，也要被实际driver读取并保入check.expected/source_ref（或真实resource availability分析上下文）；若driver完全忽略它不能建立“新分析”事实。新增资料仅可帮助原父组件观察/来源映射，不能覆盖原脚本/masters或用用户的“音频错了”直接生成supported测量。模型只保attributed assessment及实际Operation输出；deterministic检查仍真实媒体观察，精度时码差不能变TTS/Wan/ambient组件故障。

## 6. queue→claim→分析→再次等待/准确选择

探针在SQL外产真实held input与captured readset。resume的同原短writer重核exactold journal/source、Owner current、request/source scope、unsettled、暂停/取消/human revision、计数/预算和actual新资料。保原 issuer.assert_final_evidence_resume_current(..., resume_mode='retry_final_validation', affected_artifact_ids=())；实际908–954对unattended仍独立begin_execution/execute_plan/continue_bundle_validation/finalize_bundle，对interactive仍真实原plan/quality ReviewDecision。此次只排analysis/reuse子任务，额外不授生成scope。没有这些原许可仍403/待真实批准；不得为自动路径伪human，也不向已可信预授权路径强塞新每项目确认。

写queued journal和同SHA伴件resume_context，CAS仅old准确body；无费用预扣/未知清理。原worker取得新lease/fence后claim仍原issuer门且同source重核；只在已登记的work_kind=analyse_changed_input/reuse_record时，原producer在continue_current_final_evidence最前消费对应诊断续步，不调用旧master生成、修复dispatch、ASR或整体验证。这不是把旧mode全改为分析：无此准确伴件的旧retry_final_validation完全原路。

新lease下通过原CurrentFinalEvidencePorts的prepare/record或明确record pure读取，登记新的真实原Step/Operation；unknown沿原核实。预算保同production/current route/原费用账，修订和分析次数按原计数/实际Operation预算，不改max_revision_cycles、不另建Run/扣费槽。输入/费用unknown时不能按0或换key重发。分析完成后选择准确newref，先held pure验证，park短writer将其写为唯一当前journal/ref，保旧诊断ref与失败源历史，原source captured/lease/fence最终重核。崩溃后source不存在且journal已写不可能作为成功路径：二者同SQL事务；已完成record但未park时按已注册resume input/key纯读复用，不新模型调用。

新事实 component_repair→原DiagnosticSnapshot修复闭包只取fact，resume_context清为已完成选择事实，后续单独原repair mode/全新完整plan authorizer执行；information_required→新waiting_diagnosis保确缺项/原失败，继续第4节有界路径；timing_only/no_component_failure→若original_snapshot有真实precision failure/evidence wait，原writer切回它的原v1失败路径并将新的诊断ref/来源历史保在该new journal SHA伴件，不清失败。若origin为verified_then_diagnostic_block且新实际补充解决诊断，保显式ref，标work_kind=final_validation_after_analysis；下一独立真实续步按原最终validator一次校验/全部当前发布门，不从历史Verified token直接publish。

“不调用第二次wholeverify”指本次原结果分类/失败join/diagnosis-only续步不得通过再次运行整套验证来补连接或探测分支。真实修复、新证据/新分析完成后的下一受控最终验证，按原完整生产链一次运行，是正常验收步骤；没有真实变化、仅想让同失败材料再次通过，不允许借此重跑。quality_incomplete且诊断不能支持真实组件或所需QC仍未实际补齐时保准确原失败/具体资料请求，不凭新诊断通过它。旧legacy_diagnostic_block恢复后也是原最终验证，历史unknown不是success。

## 7. 精确有限ABI与失败归属

Backend新增/调整的方法必须可从原调用处直达，不能只加声明：

| 方法/归属 | 真实输入/结果 | 原调用点/约束 |
| --- | --- | --- |
| BundleService.join_current_final_diagnosis | current lease/prep/manifest、真实held outcome和registered diagnosis→原assessment | 原一次verify成功或真实失败投影后；无provider/wholeverify |
| BundleService.read_current_final_diagnostic_source | actual continuation→held源伴件 | ports同lease/thread/current journal SHA；纯受控读，不latest |
| Runtime.probe_current_diagnostic_resume | exact waiting journal/body/source→held probe或blocked | 原resume无lease的可信Owner范围；SQL外大校验，无效果 |
| Runtime claim/park/failed | 原类型、原assessment，伴件同事务 | 原CAS/current；新fence后的probe消费只能走真实claim |
| Ports.prepare_component_diagnosis | 保旧prep/continuation，私有resume_probe增量 | 同原注册source/type，sole InputsV2由Backend产生 |
| 原 record/read_component_diagnosis | 已注册V1/V2输入或显式选择ref→原RegisteredDiagnosisV1 | 纯verifier+actualOperation+source rows；不重分析 |

read_current_final_diagnostic_source不得向Media返回SQL/可选任意metadata key；只给原snapshot/failure facts、准确selectedref/registered input/completion refs、当前fence的held只读结果。Media不能自建companion/选择source/ref或错把serializedcontext作scope。

必要错误保有限语义：403原Owner/rights/source/安装current撤销、假的held/probe/plan/第二authority拒绝；409准确journal/input/record/source/CAS冲突、unknown先核实、超原限次、不同准备/新旧fence；422正文/精度/签名/不可变材料损坏、未知grammar；503只有确未装producer/verifier/原实际resource observer或材料，保具体source缺项。waiting不是失败已修复，完整execute_plan+continue_bundle_validation审批不同，费用与资格事实也不同。

## 8. 分支保护与独立验证要求

| 分支 | 允许结果 | 必须保留/禁止 |
| --- | --- | --- |
| precision失败，诊断空/timing_only | 原realignment snapshot | 原report/failed_units/closure/reason；0媒体重做 |
| precision+supported component | 诊断repair +原失败伴件 | 不union生成闭包；原P95>200000仍失败，两authority原路 |
| 缺precision/authority+component | 诊断repair并保原dependency | 修复组件不能生成独立参考或授资格，null不变0 |
| 原verify成功+component | 原success后额外deny | 无READY/publish；明确diagref；旧成功token不能持久当权限 |
| 原verify成功+inconclusive | waiting_diagnosis | 无变化stillblocked；真实变化可同Runqueue/newfence |
| 精确quality_incomplete现场+诊断 | 准确QC事实连接或原错误 | 必须真实throw/READY正文；泛EngineError不吞 |
| 无source/authority/integrity/rights/unknown | 原拒绝/核实 | 不造失败测量、不清unknown、不reissue |
| 已记录同input | 原record pure复用 | 0新模型调用/重复预留；differentrecord409 |
| 新实际completion inputs | V2 key/显式旧ref关系 | 空/nonce/time/retry不算改变；不得随意扩scope |
| waiting→queued→claim→record前/后崩溃 | 原CAS/newfence恢复 | companion/journal原子、费用/计数保留，record复用 |
| source/version/current撤销 | 403/409/具体notready | 不换registration或用已保存body复活权限 |

Test独立验证真实source/body调用顺序：一次wholeverify（含成功、_FinalEvidenceProblem及精准QC）、第二authority false403和原报告与闭包未变；多个诊断ref冲突；未observed/unknown无重复dispatch；nochange inconclusive不queue；实际补充后queue/newfence、probe伪造/跨thread/旧fence/feedback空白/资源Bool拒绝；新input确被driver消费；同输入与崩溃0新成本；park前/后source CAS损坏整事务rollback；精度失败新诊断clear/union不能生成；旧bytes、timing/edit fallback/targets及新V2解析兼容。任何独测均由Test另批准执行，本轮只提出标准场景，不编写或改现测试。

## 9. 实施顺序、来源与边界

1. 原Review独审本增量与实际源码保护；不以架构doc关闭P01/P02。Backend唯一types/companion/原validator失败出口/资源事实读者/Runtime短writer、旧format兼容及sole API错误声明，先固定真实可消费ABI。不能借该设计重试原拒绝组合。
2. Media只在原producer消费held Inputs/source/明确诊断续步和真实verifier，不能直接SQL、第二DTO/假Operation或代Owner批准；完整最终quality/RAG/Bundle照原路径。Integration对真实source/resource observer和factory/runtime闭包形成可安装包/SDK；新v2 source按原安装coverage准入，不能漏动态能力。
3. 独立Test/Review/Acceptance验证真正呼叫链与故障恢复。外部资源未准仍NOT_READY，不能把实现声明或旧19通过当该合同运行资格；R1/R2保持OPEN。还在排队的Local/BYOK与IntelMac/source/native资格不能被此设计删除。

本次固定任务初版02890d37及末增补a9ea1fbe均保过程普通副本；127 SourceIndex2647be66；Handoff22d68925/d41ca4eb；ActualInterfaces aa5ce1d9；Gap a1afecab/89994c22；Finding P01 107c9413/P02 9318b8b4。全文或有限必要方法实际读取：current_final_evidence_service SHA42a48b47（126–190,238–320）；runtime4609dcea（1–25,93–258,288–349）；journal0a3cc2ce全文；component servicefa2d8f89（29–80,81–156,158–283,284–360,403–475,542–581,596–681）；domain component669b09c7及旧 domain final7f9e99b4全文；application ports d99d5e5b 1–130；bundles589a0d4f（1170–1215,1266–1417,2322–2366,2452–2517,2582–2655,2714–2732）；production_admissions5c6548b4 908–954完整方法及有限后继边界。不是127全部正文已读。

旧ADR0059 1e4246a3只读§7及尾部，0058 a2660ba5只作为已冻结语义基线不改。过程InputPins保存完整64位SHA/实际范围/命令exit与观察错误（单范围PowerShell展平导致空body后已有限纠正；rg无命中不当方法不存在证明；输出截断不冒全文）。本轮产品/SQL/Pydantic/ASR/provider/模型/网络/native/install/keys/fees/第四历史target均0；正式架构source身份核对不登记COMMANDS产品通过。
