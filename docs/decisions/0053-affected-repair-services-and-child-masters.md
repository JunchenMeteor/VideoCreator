# ADR0053 — 受控修复的真实制作服务、子母版与对齐路由

状态：APPROVED_DESIGN_ONLY；2026-10-10。仅补充 ADR0052 的实际修复接线，不修改 ADR0049—0052、原规范、审批、阈值或旧失败。完整 R1 独立验收后连续完整 R2；五步工作台、安装实例持有数据、本地免产品注册/BYOK、一次预授权 API/MCP 自动完整制作及三 OS 保持。本文批准下述实施合同，不批准产品、ASR、provider、模型、费用或部署运行。

## 1. 固定事实与边界

任务卡 SHA `754ad062c3e9afe2f6b1fc394c8a5c8acae29ad063218b50b7d28f8c878a731f`；Media AffectedRepairSourceGap.md `d89438ab2276d62ef78ec279910cd48e53cfcd6308e1778a435d693ab57cb089` / JSON `c908548b5ca0b19b11aa317fe5767d899d7a1c20cbec8384a10584fdb01d6978`。固定 Backend111 SourceIndex `c8480592bacfde5d886267e8afd467b84e12ebdc9b903bfeafe0f78f2e1d0033`，Interfaces `82850b33bef74012e64e363ec2c59853955e0a2d9b7d6f68dd38671b56d2dc0b`；Media 初始34源 Snapshot `19ed596ee1eb4112d0d52a53e1e0f76d48fef5172527d2fe2e74bf1c9de36f2e`。只读固定普通副本的必要正文，不读 Media WIP，不将 owner source-stage/AST 结果当运行通过。

已核的实际接缝：

- `media_registration.py` `5c7a3fdfc0658b5ed8101d4b7a7135e5d5b5c45277b9eb3d28a1f540d840258f`：247—305 的 `_current_services` 已创建同 Engine/Worker/Bundle/executor、原生产资源、固定 builders、实际 human 或 policy ports；339—393 的初始和恢复路径均已持有该对象。
- `current_final_evidence_runtime.py` `8d939e90015d02a30d581fbc62c2b71a24e41d44f305d3e448f472699152e8ef`：64—82 工厂只传 ASR 清单和最终证据 port，丢失上述实际制作服务。
- `current_final_evidence_service.py` `6a8181ee3507ca03810d98a68f8e9b058f89b5e1d750c57cd3f321f8a215444b`：156—172 只接纳原成功 media-master 的四个 ID；284—356 已将材料 child/lineage/command/counter 原子提交，材料槽位不是母版许可。
- `worker.py` `5058afc2e32a2047015c68b9563447838cac47fdbfa5487bb37bf754d03130be`：493—607 已有持久输出分配、完成文件核验、成功 settled Operations 与实际 decoder 之后登记 Asset/role 的路径；调用方不提供 Asset ID。
- 固定 Media `AutonomousServices` / `CurrentPolicyServices` 是两种现存制作服务，工厂只实现 Piper/Wan/FFmpeg builders，没有 alignment builder。现有公开 `CapabilityRoute.capability` 已允许 `alignment`，无需新增公开 capability 或混用 transcription。

queued Local/BYOK factory 合同 `b9b53fe876c2aa80706c0388ddbeb763f4ec56b3feffed921cdd03179cb66abb` 保留。本文复用实际注册服务而不把通用本地工具限定为必须 Wan；该后继的合法本地素材/BYOK factory 仍须原角色完成。

## 2. 唯一服务注入 ABI 与真实性

Media 工厂 `create_registered_media_producer` 增加唯一可选关键字 `production_services=None`，其值只允许现存 `AutonomousServices` 或 `CurrentPolicyServices`。其他 ASR 参数、`final_evidence_ports` 和 bound continuation 的 `policy_execution_ports` 兼容保留。旧 v1/非修复调用默认 None；当前 v2 初始和 continuation 的真实 Backend caller 必须传入 `_current_services` 本次实际返回的同一个对象。None 不授权修复，不能用当前主机临时构造 Worker/builders/route。

Backend `_final_producer(lease, *, production_services, execution_ports)` 从真实 `_invoke_current` 接收其已创建对象：两个调用点都传同一 `services` 和 `ports`；不得在 `_final_producer` 再跑上游、重建 Worker 或再次伪造 admission。工厂用于 ASR 的清单仍是原 ASR 清单，生产资源仍来自实际 services 的固定 registered builders，二者不互换。

Backend 在 `_current_services` 的实际固定工厂返回点内部持有服务来源登记，关联 actual object identity、原 Runtime/Engine/Worker/Bundle/executor、原 ports object、ProductionBinding、registration、生产 resource/runtime identity、本次 lease/fence/thread。不是一个可由外部调用的通用 register/callback，也不接受模型/renderer 的类型或字段作为来源。完整 Engine/source coverage 和原 installed issuer/current_guard 在登记之前实际核验，原 Owner/request/source/actions 保持。

Backend 唯一 `CurrentFinalEvidencePorts` 增加：

`assert_production_services(ordinary_lease, production_services, execution_ports) -> None`。

它检查上述实际创建登记、端口当前 registry/thread/lease/fence、两种 automation mode 与实际 human/policy ports 一致，以及完整同实例/Run/注册/资源来源；调用纯字段等值或 isinstance 不够。它不生成许可。工厂保存已绑定对象，continuation 在任何使用及副作用前重新调用；close、lease 撤销、线程退出、Runtime 停止使登记失效。新 lease 必须由本次真实 `_current_services` 重建并登记，不能恢复一个序列化 service/permit。真实安装 guard 的 writer 内外机制原样保留，资源 I/O/provider 不进 SQL writer。

现存 services 类型与声明职责不搬家：Media 继续维护现有实现对象，Backend 唯一维护新跨角色类型/held port/注册 grammar/权限检查，Integration 纳入真正完整 source 与资源闭包。不得私设第二公开 schema、callback 或模型选模块。

## 3. 执行权限与最小修复命令

`allowed_action`、report、failed units、材料 affected 子集只描述已观察失败，不授新执行权。当前实际 `_current_repair_scope` 只有 unattended 原 scope 内 realignment，interactive 返回指导；本文不自动扩大这个事实。Backend 增强为从原失败报告和实际 committed plan/storyboard/quality 中验证的有限动作映射：

- realignment 保持同实际音频/文本、原已准目标和有限单位，只在原 begin/execute_plan/continue_bundle_validation、真实当前 rights、scope、合格 alignment 路由均适用时允许。
- regenerate_affected_media 仅当实际原 Owner 预授权政策或真实人审批准的 plan 已明确包含对应制作目标、route/action、输入来源和素材许可时允许；受影响 shot/role 的依赖闭包必须从原事实推出并核验。原通用质量审核不自动批准新制作动作，也不能用执行 DTO/JSON bool/真人指导替代缺失动作。
- 原 interactive admission 保持实际 ReviewDecision 的 target/revision/hash/source；缺对应修复制作批准时 guidance_required。unattended 若原政策已包含真实目标可自动跑，无逐项目/逐修复假人审；当前撤销/预算未知/unknown 操作仍拒副作用。

Backend 唯一新增 held port：

`authorize_affected_execution(ordinary_lease, continuation, proposal:AffectedRepairProposal) -> AffectedRepairExecution`。

Proposal 是 strict/frozen/extra-forbid 的私有数据，format=`current-affected-repair-proposal-v1`，完整字段为 parent_preparation_id、affected_artifact_ids、failed_unit_ids、requested_action、changed_media_roles、affected_shot_ids。action 仅 realignment/regenerate_affected_media；roles 仅原四 role 的有序不同子集；不含 Asset ID、route/module/callback、许可、预算、Owner 确认。Media 从原实际报告/计划映射提出，Backend 从原材料全文/失败单位/plan/storyboard/资产依赖逐项重算，不信提议。realignment 的 changed_media_roles 必须为空；纯图片变更只允许确有依赖的 video/cover，不能借机重 TTS。

服务生成并持有 `AffectedRepairExecution`，frozen/eq=False/非序列化，成员恰为 binding、execution_fence、parent_preparation_id、parent_intent_sha256、repair_command_sha256、source_report_ref、affected_artifact_ids、failed_unit_ids、requested_action、changed_media_roles、affected_shot_ids。只有原 port registry 签发的本次对象可使用，读取其字段不是许可。命令 SHA 由原 canonical 算法绑定上述实际来源及真实 plan/quality revisions、目标依赖闭包和固定 route/resource 身份；不由 Media 重造第二算法。

首次允许执行前，在原短 writer 持久化封闭命令 `current_final_affected_execution:<commandSHA>`，format=`current-final-affected-execution-v1`：完整 binding、parent/intent、真实 source_report_ref、上述实际子集/action/roles/shots、精确 plan/quality refs、固定 route/resource identities 与确定的各 Step/input/dedupe key。命令 ID 不是 authority，writer 外 actual guard + writer 内 current scope/lease/journal CAS/来源重核必须真实执行。原 source report 和 affected order 不能偷偷更换；相同 report/subset/action 的命令只有一个，改 payload/计划身份或另一 intent 409。

该记录只固定原有有限执行的幂等输入，不添加 Run、费用额度或新的 revision cycle。开始前检查原共享 cycle 剩余量、预算/unknown、取消/期限；实际 Operation 仍逐件原账本先于 effects。实际失败/unknown 沿原终态/核实，不以新 command/new key 重交。一个普通 Run lease/fence 下同命令只能走原同一系列 Step/Operations；重复请求返回原命令/原状态，不增加效果。成功后 child/counter 仍按第5节原子计一次；失败保原费用/操作失败，不能将未计 child 视为新一轮无限尝试。

## 4. 原母版不变，真实新输出先观察

新 Asset ID 必须由原 Worker 的成功 Step/settled Operation/实际 decoded 输出登记后出现，不能为了先建 child intent 造 ID。原 `media-master` 及其 result_json、四 Asset、READY、Manifest、ASR context 和费用账本全保留。

对于 regenerate_affected_media，Media 只调用上述同 services 的实际 narration/picture/edit builder 与原 executor/Worker；每件输入来自当前命令的真实闭包，route 由固定注册决定。Step key 固定为 `repair-master-` 加 commandSHA 的前32位；各依赖生成 Step 使用固定 stage/shot ID 加同命令摘要，且必须在 writer 中验证完整 SHA 与输入关联，截短名不能代完整身份。OperationIntent 的 input/dedupe/route/reserved cost 都由实际固定输入产生。原 `allocate_output`、driver、`finish_output`、`commit_generated_media_step` 链照常运行；新媒体 Step 只登记 changed roles，对未变 role 不复制生成文件。

Backend held port 增加：

`observe_affected_masters(ordinary_lease, execution:AffectedRepairExecution, *, step_key:Identifier) -> AffectedMasterObservation`。

传入 step_key 只定位当前命令的预登记 Step；不接受 caller Asset IDs/result/path。服务从同 Run 的实际 succeeded Step、全部 succeeded+settled Operations 和 typed Observation 中取原生成 manifests、output attempts/实际 Asset role 映射。重核完整 input/dedupe/route/成本/来源、原 Worker 输出登记及文件 SHA/size/MIME/decoder，所有新增 role 必须且仅覆盖 changed_media_roles。任一 pending/unknown/unsettled 保 needs_reconciliation，不能登记观察或重提交。scope 和 post-plan rights 在当前实际 guard 下重核。

Observation 是服务持有 frozen/eq=False 对象，成员恰为 binding、parent_preparation_id、repair_command_sha256、step_key、step_input_sha256、operation_ids、changed_media_roles、effective_media_roles。effective_media_roles 恰四个不同实际 ID：changed roles 取已登记新 Step，其他 role 取真实父母版（前一修复父本则按其已提交祖先读）。它不是读取/复制/再分发 grant。服务将不可变观察 metadata 提交为 `current_final_affected_masters:<commandSHA>`，format=`current-final-affected-masters-v1`，保存完整 command/binding/parent、原 Step/input/Operation IDs 和实际四 role 映射；文件检查在 writer 外，短 writer 再核原 settled rows/lease/current source，前后不能用假 True hook。

同命令相同实际结果幂等，不同 role/Step/Operation/Asset 409；metadata 不能覆盖原媒体事实。原 asset/path scope仍通过实际 Worker/Bundle 读取，观察不新增公开依赖 grant。只有真实新媒体成功并观察后，Media 才能构造含 actual effective media IDs 的新 child intent。不得先产生 original IDs 的 child 后改 immutable intent，也不改父 Step 来绕 resolver。

## 5. 子版本提交、统一母版 resolver 与恢复

沿用 `revise_preparation(lease,parent,intent,affected_artifact_ids=...)` 签名和 ADR0052 atomic 规则。realignment 没有新母版时四 ID 保持父 effective roles，原 atomic child/lineage/counter 先提交，再受控执行新的 alignment Operation。regenerate_affected_media 必须已有同 parent/report/subset/command 的第4节真实观察，child intent.media_asset_ids 精确为其四 role ID；原 writer 将 child/allocation/完整 lineage/命令绑定/一次 cycle 计数及该 master-observation ref **一并提交**，不先 commit child 再补来源。

现有 `current-final-evidence-lineage-v1` 历史正文不改。新增带 child master 关系的 lineage format=`current-final-evidence-lineage-v2`，保持 v1 所有原字段，增加 repair_command_sha256 和 master_observation_ref（commandSHA/full canonical metadata SHA）。v1 子本只可保同原有效四母版；v2 明确新的实际母版来源。相同命令+同 child intent 重试返回原 child/原 counter；不同 intent/旁系 parent/另一 report 409。成功 child 的重复读取不被当成申请新一轮 cycle；已耗尽限次不能创建另一个 child或新的修复效果。

Backend 实施一个私有 `resolve_preparation_masters(ordinary_lease, preparation_id)`，返回原四 role→实际 Asset 的服务读取事实，不能由 consumer 指定比较器。所有最终入口共用：resolve_inputs、read_continuation_inputs、persist_assembly_context、verify/完整 Manifest 对照与 publisher 的 preparation/媒体关联检查。它逐层读取同 Run 实际 lineage：无 lineage 必须 exact 原 media-master；v1 child 保祖先四 ID；v2 child 验父原事实、精确失败 report/command/子集、已提交 child/intent、观察 Step/Operations/全部实际 decoded Assets 与新 ID，再核 intent 四 ID。不能仅从任一 production 的成功 Step 授信。

循环、旁系/跨 Run、缺父、冲突/损坏关系拒422，错误当前 claim/fence/许可拒403/409，声称已提交而文件/必要源真实缺失503；不降成无候选。遍历沿原总资源/节点上界和 cycle 限次，不发明更宽公共访问或放宽原 DAG/许可边界。parent/ancestor 许可用途、复制/再分发与 source current 检查保留；可读事实不等权限。

初次 claim 的 journal 仍指父 failed report。child/allocation/lineage/counter commit 同时把该 command 的实际 child_preparation_id/child_intent_sha256 记入上述命令 metadata；此时 child 尚未有 assembly/报告，不假造 child等待 snapshot，也不修改原 journal grammar。原祖先只读事实与当前 selected child 是两件事。

Backend另增加唯一 held读取 `read_affected_execution_inputs(ordinary_lease, continuation) -> AffectedRepairReadSet`；成员恰为 execution、parent、child、masters。execution 是从实际同 journal/command/当前权限重获的本次 held对象；parent/child 为原十一成员 CurrentFinalEvidenceReadSet，child未提交时为null；masters为真实第4节观察或null。内部原reader仅允许当前命令明确的父/子 preparation关系，不能把通用ancestor读口开放给外部。父只读保真实原report/READY/assembly，子按其实际READY/context/candidate返回；服务重核child intent、lineage、command和父journal CAS，不使用模型/客户端的child ID。上述十一成员原签名保持，不能要求Media自行私读metadata/SQL。

恢复消费者先读此补充read-set：实际 settled新masters和committed child存在就恢复它们，不再派发生成；尚未完成的原Step/Operation仍按同dedupe/current权限及unknown核实处理。原 Runtime `_current_final_execution_facts` 和无lease预检从真实命令记录的原plan/quality refs及父assembly取来源，不因子尚无assembly而永久拒；不是挑当前最新plan或由command hash授信。子后续文档/ASR/assembly真实保存后走统一resolver、完整verify/publisher。出现实际子等待assessment时，park writer只在上述命令选中子与完整v2 lineage重核后原子替换journal snapshot为该实际子assessment，保原blocked time/binding并仅释放本次lease一次；不再次park父。实际成功发布则publication观察用同selected-child/lineage核它的scope，而不强迫制造一个“等待”的假snapshot。kill后原journal加已提交命令/child关联构成可读恢复源；没有提交记录的内存child/文件不作为事实。

若音频或媒体时间轴改变：旧 actual transcript/ASR context/report 不再作为新音频证据。新的确有权限 ASR Operation 用原正常原 context先提交→dispatch→真实 Observation→settle 链，绑定实际新 audio SHA/decoder clocks；旧 unknown 不重发。固定原 journal 只认 `bundle-actual-asr` 和 `bundle-asr-<RunID>`，这不是已支持新音频。Backend必须在同原journal/executor中增加仅由已提交repair command/selected child登记的精确 `repair-asr-<commandSHA前32位>` Step/dedupe关联，完整command SHA、child/audio/input/原route写入原命令。不是通配prefix：其 `_operation`、handle/allocation、context提交、settled读取和受限reconcile全走同一验证helper，仅接纳该真实登记的同Run新Step，原v1 exact检查与五值返回保持。RegisteredOperationExecutor须识别实际登记的child ASR并保持context先commit再claim/dispatch，不能因step_key不同绕过journal。新本地route仍原verified/owned_local/transcription/zero-cost/credential-free/source/current资格；不重开被拒ASR执行方式。若 only video 改但 narration byte/time不变，ASR原结果可合法引用原音频，新的实际 video↔audio mapping/assembly、字幕/RAG语义坐标/WorkValidation仍须重建并验证。独立 reference 听审/audio 绑定改变时需真实新来源或明确等待，不能沿用旧参考时间伪测新片。

## 6. 真正 forced alignment 的注册和执行

当前没有合格 forced-aligner，Piper/Wan/FFmpeg、ASR估计词和独立参考都不能代替它。新增兼容私有 installer `RegistrationConfigV3`：format=`registered-media-config-v3`，继承 v2 全部字段，加 alignment_registration，类型为 `ForcedAlignmentRegistration | None`。v1/v2 字节/行为不改；没有此登记的真实 realignment 返回具体 `alignment_resource_not_ready`，不硬判所有 ready validation失败。v3 仍满足完整 source、生产 resources/runtime 与原 installed registration/Owner信任来源；None 不伪造资格。

Backend 唯一 `ForcedAlignmentRegistration` strict/frozen/extra-forbid，成员恰为 format=`registered-forced-alignment-v1`、route_id、driver_profile=`qualified-local-forced-alignment-v1`、resource_section=`alignment`、method_qualification_ref（既有唯一类型）。这是有版本的候选登记，不是已合格算法；存在条目/hash 不替真正 current资格/许可。Media 在固定工厂增加可选 alignment builder，仅以此固定 profile 对接已实际实现、覆盖安装 source 的硬编码本地驱动；不收 model/module/URL/任意 shell/callback。

生产资源 grammar 新增 `registered-production-driver-resources-v2`（Backend唯一 typed grammar，Media loader消费）：保持 v1 narration/picture/edit 原字段与规则，加 alignment 可选严格对象，完整成员 kind=`qualified_local_forced_alignment`、model_revision、model_files（原资源索引 relative_path→SHA）、configuration_sha256、worker_resource、runtime_resource、license_artifact_ids。所有 path/ref必须属于当前 held生产资源索引；实际 model、runtime、worker、native依赖、许可/适用语言/单位/CPU/OS/真实 qualification/report source闭包由 Integration与原资格服务提供并核验。此处不选择或声称任何模型已测兼容，也不安装/下载资源。后继 Media须实现真正驱动并交具体 source/resources/实际推理证据，Integration封装三OS真实候选并独立验证，缺件列精确资源依赖，不永久stub算完成。

alignment route 只允许 actual configured `owned_local`、capability=`alignment`、credential-free、明确 zero-cost；route/action必须含于原当前 execution scope。这一路线不启用新增收费/BYOK调用，也不把私人会员权益当资源资格。新 provider 类型只给本地路径；其他 BYOK/official alignment路线需后继按原允许端点、预算和单独准入，不自动生效。

Media 在同实际 services绑定下用 fixed `create_registered_alignment_driver`；其请求输入恰为实际 source transcript/ref、decoded input audio ID/SHA、同单位失败子集、resource/qualification refs和 allocated child output，不带 independent reference的目标时间。通过原 executor、唯一 `OperationIntent`/真实 permit执行，input/dedupe SHA绑定 repair command/child/source文本音频/范围/实际算法与资源；先账本+原正常permission/cancel/deadline再效果。结果为真实推理的 intrinsic整数微秒边界及方法/实际执行身份；原 `AlignmentRevision`/V03、utterance/word IDs、time half-open、完整 audio/mapping和来源 grammar保持。

对齐可完整读取必要原音频/文本上下文，但仅替换核准 affected 单位及其实际必须的边界一致性闭包；未受影响 boundary 保留原字节/身份，扩范围需原真实动作另准，不以全片重新估计作fallback。原 ASR result文本及原 transcript输入身份保留，对齐修订是新文档，不能重写旧ASR。infer输出不含伪 independent truth；P95只由真实独立参考/测量得出，无本片参考0.3路径保持 null/完整实际算法与WorkValidation报告，旧 strict和200ms门不降。两次真实precision authority及second false403原样保留。

## 7. 成包前纠正作者意图的唯一保存与读取

追加固定 Media CorrectionContextSourceGap.md `5afbc2cf7b4ac6046495869a0a18ec93026c4fc55010d3e00ba7a9cca633fa4d` / JSON `d7a9fce85b3fdfa8110eb3354777bf2845089f1f91c8a3df42e1ca1a50573a25`。四份完整普通源身份按该JSON；已核原 `IndependentReferenceMaterials.corrected_from/correction_reason` 在 `prepare_v03_evidence` 经真实 `correction_origin_evidence`/完整复制闭包后仅存于 `PreparedV03Evidence`，之后才进入当前measurement；原context确未保存两字段，祖先bytes不足以推出作者选择。

Backend新增 `CurrentFinalAssemblyContextV2`，继承v1全部字段/严格规则，format=`current-final-assembly-context-v2`，仅增加 corrected_from（原唯一 `c.CorrectionOriginRef | None`）及 correction_reason（`str | None`，非空时1—1000字符）；两者必须同时有或同时null，沿原report规则，不造第二locator/宽dict。原context-v1 grammar/正文/Ref不改；原十一成员read-set的assembly允许实际v1/v2 union，成员数和held接口保持。

实际初始Media producer从上述原作者holder经过既有prepare校验后的确切pair填v2；没有纠正时两者null。持久时点仍是原必要input/祖先完整合法READY之后、任何resolve无candidate等待之前。Backend `persist_assembly_context` 原签名接受唯一版本解析后的实际context，必须原注册producer/同Run request/claim/intent/源scope，用真实 `correction_origin_evidence` 再核选中locator、全部复制祖先/边/许可与READY receipt/fileSHA，和prepared correction copy计划逐件相符。writer外真实source/rights守卫，短writer内原current机制与claim/材料关系再核；只能提交原作者实际pair，不由存在某祖先推断它。pair是审计来源和意图，不是许可、资格、precision或未来reportSHA。

原不可变context file先写/fsync再metadata/ref commit且同bytes幂等、不同bytes409；保存真实v2格式+全文SHA，旧v1 records不回填/覆盖。现有Ref四字段不变、无hash循环；恢复读按实际format严格dispatch。对于本轮正常新作品/子纠正，真正producer必须持久v2，reader能取实际原pair生成新report，而非永久missing。

有实际原candidate则保其完整bytes/fileSHA与实际当前report；当前measurement已READY则取完整校验后的原 `PrecisionEvaluationReportV03` 的原pair，再重获current纠正源并比较完整原复制闭包，不能修改READY ID/bytes/SHA。两来源及已有v2意图冲突422。旧v1上下文既无candidate也无当前measurement但有correction copies，继续明确 `correction_recovery_context_required`，不得选择祖先/编理由/去掉复制/重ASR。没有纠正材料的真正v1普通作品仍兼容；不要求不存在意图的普通作品作假声明。

## 8. 实施角色、失败与独立证据

Backend先实现唯一 typed proposal/held execution与注册、实际caller的同 services登记/注入、current scope动作映射、受控 Step/Operation观察/命令 metadata、v1/v2 lineage共享resolver和atomic child/实际子等待切换、补充parent/child读集及精确child ASR登记、v2纠正context保存读取；完整source停止后交固定 ABI。无公开SDK/DTO变更时不手写SDK，有公开schema影响由Backend唯一声明后Integration生成。Media随后只消费实际服务和端口，落实真正 bounded builders/aligner、子母版/新ASR/assembly/原作者纠正意图/报告、完整 verifier与发布路径。Integration纳入真实完整 Engine/Media源码、三OS资源及许可/current qualification，保持 Local/BYOK后继。前端仅显示具体资源、资格、指导或真实修复进度，不加伪人审。

独立 Test/Review/Acceptance 必须实际覆盖：同对象/同实例/Run/fence/thread/原资源来源与伪services拒；human/policy分开、未授权role/shot/route/action拒；原材料allocation无法变成Asset许可；同命令一次效果/一次counter、payload变化/预算未知/撤销/期限/unknown拒；真实Step输出登记之后才有新Asset、假role/Observation/跨Run成功Step拒；父母版/hash/mtime/READY/Manifest/ASRcontext不改、未受影响role原ID不重生成；v1/v2祖先闭包与全部resolver一致；command前后、文件完成未observed、观察提交未child、child/journal atomic各kill窗口及恢复不重复；真实alignment推理/方法资格缺项等待、ASRestimate/reference边界伪装拒；改变音频的精确已登记child-ASR key、新context/newaudio/current ASR审批及任意prefix拒、原unknown只核实；视频变化的真实新mapping/字幕/RAG及完整delivery；v2原纠正pair等待前commit、无candidate/measurement恢复原意图、旧v1缺失保missing、false origin/理由伪造/来源撤销/pair冲突拒以及旧READY/candidate不变；真实P95失败后有限修复和完整成片，second authority false仍403。本文不改测试criteria或宣这些已通过。

缺实际 driver/model/许可/qualification/机器或被拒执行前提保持具体 NOT_READY；完整真实源级实现和验证仍须接续，不能将503、模板或单独source green称R1完成。所有旧失败、原预算/修订计数和自动评审拒绝保留。本轮仅架构固定源只读与文本交付。
