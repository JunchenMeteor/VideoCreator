# ADR0057：选中子作品的原 CTC 结果读取组合

状态：APPROVED_CONTRACT_ONLY。仅批准本节列明的私有读取合同及必要共享校验接线；不批准运行、资源资格、推理、收费或修订权限改变。原 ADR0056、九个已有 held 方法、旧标准与失败记录不修改。

## 1. 已核实的缺口和唯一决策

固定 Backend120 与 Media44 的必要方法表明，现有入口不能完成本场景的合法组合：

- `read_affected_execution_inputs` → `_affected_claim` 要求当前 journal 为 executing/repair，返回的可执行对象也绑定该原 repair continuation。选中子作品等待后以 retry_final_validation/new fence 继续，不能借此复活原对象。
- `read_registered_alignment_result` / `registered_alignment_request` 通过 `assert_alignment_writer` 要求 repair；直接传原 command SHA 或自行构造 AffectedRepairExecution 不能成为读取权限。
- `registered_ctc_work_source` 的入参需要已存在的 ActualTranscriptDocumentV03 和 WorkAlignmentValidationReport。它可以校验已生成报告，不能生成尚不存在的首份报告所需事实。
- Media `_generate_candidate` 在同步 repair 分支有原 Observation；后续 retry 只有原 11 成员 readset，会误走 initial-only 方法。原 child 实际 speech/assembly 已持久，首个 candidate/report 还未 READY，形成来源读取缺口。

批准新增一个 CurrentFinalEvidencePorts 私有 held 读取方法。它从原服务的当前 continuation 选择已提交的 CTC，返回既有数据类型的有限组合；不产生或登记可执行 AffectedRepairExecution，不暴露 command/SQL 查找，不引入第二套请求/结果 DTO。Backend 同时把已提交结果的纯读取校验与派发/Step commit 权限校验分开，以同一选择和来源核验供 getter、报告校验与最终 writer 使用。不得将 repair-only 执行 guard 改为接受 retry。

本次选取规则是读已存在事实，不是新的修订目标授权或无限重试机制。被拒的 role intersection/subset 变更不在本决策范围。

## 2. 唯一新增 held ABI

Backend 是类型、grammar、来源与检查的唯一 owner；Media 只消费：

```text
CurrentFinalEvidencePorts.read_selected_alignment_result(
    ordinary_lease: c.LeaseGrant,
    continuation: CurrentFinalEvidenceContinuation,
) -> tuple[
    bytes,                                       # 原 canonical request UTF-8 bytes
    c.AlignmentRevision | c.AlignmentRevisionV03,
    GeneratedFileManifest,
    c.OperationObservation,
    c.MethodEvidence,
] | None
```

位置：原 application/current_final_evidence.py 的 held port，委托原 BundleService/RegisteredAlignmentMixin 的私有读取实现。参数不接受 preparation/command/Operation/registry/model ID、调用方配置或 report。返回的 bytes 使用既有 InitialAlignmentRequest 或 AffectedAlignmentRequest 的严格 format dispatch；不是新 grammar，不能从调用方重编码替换原字节。

当前 port 必须仍在原 service identity registry，线程相同、ordinary lease 相同且当前有效；continuation 必须是原 journal 当前 binding、完整 snapshot、executing、retry_final_validation 和本次 fencing_token 的一致值。仅同一安装 instance / Owner / Project / Production / Run / request / 当前原 runtime 的源可读。序列化 continuation、tuple、hash 或复制 port 不获得权限。

None 仅表示“原合法 legacy 源确实没有 CTC”：Backend 已完整核实选中源链不存在任何 initial/affected CTC 注册，选中作品的原 ASR、assembly/actual document 以及原证据策略明确允许该 legacy ASR 方法，且无 CTC 方法/command/输出残缺或冲突。不能以缺失的原 affected companion、未知状态、配置未就绪、报告未生成或捕获任意异常返回 None；需要 CTC 的当前原 policy/源不得降为 ASR。原 initial_runtime 的 legacy 兼容事实仍须成立，不增加任何新默认或新 fallback。

返回值是只读数据，不是运行 permit。不能给原 intent getter、register、commit、Worker.begin、claim/resume 或其他写口作权限源；不登记到 _affected_execution_held。原八方法和第九 registered_initial_alignment_method 的签名、执行及写入限制保持。

## 3. 原源选择与完整闭包

先读原当前 claim/readset；选中 preparation 必须由 journal snapshot 和真实原 intent 指定，不由 Media 传 ID。先核原四 masters 的完整 bytes/MIME/实际 decoder 与 authenticated lineage，不把 Asset/报告中的任意 locator 当真实子作品。

同一 Backend 私有 selector 从选中节点向原已提交祖先走：优先本节点的真实 initial 注册；否则本节点 v2 lineage 的真实 realignment command；否则沿经完整核实的原 parent 继续。沿途核 binding、Run、child/parent preparation/revision/intent SHA、原 command/source SHA、原 source_report_ref/affected_artifact_ids/failed_unit_ids、选中 child 的原关联和完整 request grammar。环、跨 Run、孤立边、歧义或同时冲突的“本节点 initial + realignment”不能择一洗掉。

保留现有有限界：不得超过原 Production revision_cycles+1 所容许的 preparation 链，且不超过已存在 CTC selector 的 32 节点保护；不增预算/计数/循环上限。原 v1/v2 lineage 语义保持，v1 没有真实 command 的节点只可向真实父源走，不能补造 realignment。

最近的有 CTC 来源的节点是确定源；已有该节点的注册/command 却缺 companion/result/Step 时不得越过它取更老“可用”结果。祖先来源仅在该选中作品实际 ASR transcript、mixed-audio asset/SHA/size/track、mapping 全量 SHA、unit IDs/order/scalar text 和 boundaries 的实际输出匹配时可复用。换过 audio/text/mapping 的子作品不得继承旧 CTC。新 audio 的既有 child ASR/initial CTC 仍走原真实登记规则。

每个 affected 来源必须保完整主 command 及原 companion：canonical_body 的原 sort_keys/compact/UTF-8 编码及现有摘要算法，不改变全局 engine.canonical 或 Goal hash；同原 command SHA、parent intent、原 plan/quality refs、批准/预授权目标、失败范围、一个 alignment Step descriptor、选中 child intent/lineage 的对应关系都要一致。只有可读祖先/文件不构成执行或再分发授权。

读取来源还包括原 saved assembly bytes/association、实际 settled ASR result 与完整原 ASR validation context、原 READY transcript、音频/mapping、resource/runtime manifests、route/config/worker/model/qualification/许可证与原当前安装 source。仍用两次真实 authority/current 来源检查与原 rights/policy 或真实 human admission；普通对象、参考材料、哈希和模型声明不顶替这些检查。资格/资源缺失仍 NOT_READY，不推导资格通过。

## 4. 已提交 CTC、实际身份与 MethodEvidence

复用原 _load_alignment 的 immutable companion/两严格请求 grammar、_alignment_result_facts 的实际结果完整检查、_read_alignment 的 succeeded Step 原结果检查；将它们所需的“可读已提交来源”前提实现为独立的私有验证分支。不能通过默认 flag、传 execution=None 或全局扩大 assert_alignment_writer 达成。

唯一实际结果满足：

1. 原 descriptor/input/route/dedupe 只对应一个原 Operation，succeeded 且 settled；Observation 为该 Operation 持久原字节的解析结果。
2. 原一个 alignment-result/application-json generated allocation 已 READY；manifest/attempt/staging/full SHA/size/source/rights 与原账本一致，读取完整 JSON 有界，读取前后实际文件稳定。
3. 原请求 SHA、实际 result.execution_identity、定位字段、输出 revision、ASR/transcript/audio/unit/subset 与实际结果一致；CTC 的 not_measured/P95=null 不被当作本片独立测量。
4. 原同一 Step 已 succeeded/committed，输入及 result_json 必须准确包含原 Operation ID、alignment_content_sha256 和这个原完整 manifest。已 settled 未 Step commit 时返回原 alignment_step_commit_required；只可由原受权 commit 路径完成，不在 getter 偷写或重新推理。
5. identity 必须取自已校验的实际 Observation，且与原 registered request、当前真实 qualification 的期望身份完全相符。不能只从 MethodQualificationRef.execution_identity 构造“实际执行”。保原独立 ASR operation/context 与真实 CTC operation 为两份来源。

Backend 从这些实际事实生成既有 MethodEvidence：method/tool/version/model/config/resource/原 model_revision、唯一实际 CTC Operation ID、原 mixed_audio artifact；不能信 Media 提议的 MethodEvidence。上述五元组合须来自同一来源快照，不分次选择不同 locator。

Media 用返回的 Observation + MethodEvidence.operation_ids[0] 走原 runtime_actual/finish_v03_evidence，report.operation_ids 保原 ASR 和实际 CTC ID。本片 WorkAlignmentValidationReport 仍由原真实当前 validator 得出；原 measurement、independent reference/benchmark/两 authority 继续分别来源验证。getter 的存在或旧 qualification 不能使 report READY/质量通过。

方法序列不泛化为集合包含：已有 selected assembly.methods 的原顺序保持；若其中已有此实际 CTC MethodEvidence，必须完全相同且只出现一次。原 initial pre-CTC assembly（或真实未更改该源的合法 descendant）尚无该方法时，仅可原有顺序追加这一实际 initial MethodEvidence。affected realignment 子作品的已持久 authored assembly 必须保它实际写入的 CTC 方法；缺失/冲突的 authored pair 不从 getter 猜 author intent 或改 assembly。相同 method_id 但旧 Operation/config 等不同不可覆盖或忽略。

## 5. 读取、报告校验和最终 writer 顺序

Backend getter 的实际入口为原 held port，不增加公共 API/MCP/SDK：

1. port._current；原 production services 来源/current、原 issuer guard；核本次 executing/retry claim，读原 selected 11 readset/lineage/注册/command/Operation/Step/allocation/源 row 快照。
2. SQL 事务外读完整 held/source bytes、实际音频/ASR/context/CTC JSON 与资源当前检查。不得在 SQLite 短 writer 内跑 decoder/推理/远程或大量读。
3. 再以短只读连接核 lease/fence、原 journal 全字节、binding/runtime、选中/祖先 intent/lineage/command/companion、Operation/Step/generated/staging/assets/assembly/context/route/registry 等同一个快照，原 current guard 再核；一致才返回五元组。不得保留旧 lease 的返回值为新 fence 权限。
4. Media 读取此源后，以原 continuation 与真实 reauthorize_continuation/rights/resolved evidence 完成首个 report/candidate。已 READY 的 report/candidate 保其原字节，不能在旧 material ID 下重写。纯 retry 不进行原 run_alignment、register、authorize_affected_execution、Worker.begin 或新的 child/Operation/allocations/UUID。
5. Backend shared report reader/validator 在报告存在后，使用同一 selector/已提交来源核验，再核实际 transcript/alignment（仅允许已有 precision 独立测量差异）、原双 Operation 身份和 report.execution_identity/qualification。不能依 report ID、caller identity、最后一个成功 Operation 来倒查任意源。
6. 最终 publish 的原短 writer 保留同连接 current/lease/claim/来源 rows 的重核与原 assert_registered_ctc_work_writer 类快照检查；在 writer 外完成两个真实 authority 与大文件校验，writer 内不调用它们。reader 的成功不替代 writer 重核，不跳第二次 authority。

共享私有校验在原 executing/repair 的同步 child report 情况也可读“原该 command 真正已选中的 child”，由原 current repair claim + command/child lineage 校验限定。这个内部 child 选择来自真实 command，不是新 getter 的参数。该纯读取分支不允许派发/commit、也不登记执行对象；原 repair 写/执行分支完整保留。因此既解决 retry 首报告，又避免同步 report/final verifier 再回 repair-only 的错误读取路径。

## 6. 失败、兼容和真实验证需求

保原 EngineError/ErrorEnvelope 和状态治理，不改变已公开 DTO：

| 条件 | 必要结果 |
|---|---|
| 假 port/线程、错 lease、非真实 current source、撤销/过期 scope、非法祖先/权限 | 原 403/current 来源拒绝；不能取旧 report 继续副作用 |
| journal 非 executing/retry、旧 fence、claim/snapshot 或 row 在读期间改变 | 原 409 claim/current/source changed；不 queue/park 第二次 |
| unknown/unsettled/submitting 或 Operation/Step 未可靠完成 | 原 reconciliation_required/Step commit required；保原 unknown，不重发 |
| 源 grammar/hash/unit/mapping/完整 result/lineage 不一致、多个候选 | 原 422 integrity/source 错误；不选“最近能成功”的历史项 |
| 原 command/companion/actual bytes/assembly/ASR context 或必需资源/资格缺失 | 原明确 unavailable/NOT_READY；不是 None、不造 report，不循环推理 |
| 原本片真实 P95 超 200ms 或其他质量失败 | 原拒绝/有限 affected repair 规则；本 getter 不授修复或质量权 |

仅在原合法允许的等待路径保存真实等待；本次不改变 park/resume 所需 journal/authority，也不以 503 永久占位代实现。CLI/API/MCP 五步自动预授权完整制作与 interactive 原真实确认保持；本地无需产品注册、BYOK/资源路线不强制 Wan。

独立 Test/Review 后继至少须分别证明：无 candidate/report 的 realignment child retry 能只读取原事实并完成首报告；已有 candidate/report 的原字节复用；直接 initial、合法不变祖先及真正 legacy；换 audio/text/mapping/错误 command/ambiguous/cycle/过深拒绝；两个 Operation 身份保留；未知/未 settled/未 commit 不重发；假对象/错线程/错 fence/current revoke 和 read/write 间源变化拒绝；返回 MethodEvidence 与真实 Observation 而非 qualification 伪身份；getter 全程零写/零新 Step/Operation/child/allocations/预算变化；原 repair 执行 guard 仍拒 retry；shared report 校验与最终 writer 不绕过两个真实 authority。源级设计不等运行或独立标准批准。

## 7. 角色接棒和来源身份

Backend：唯一新增 port/内部 selector 与已提交结果读取验证，复用现有 storage/grammar/11 readset，接 shared report reader/最终 writer；不需公开契约或数据库 migration。静态 caller/执行边界先冻结给 Media；如实际实现发现新公开/持久性需求，另交架构，不自行扩类型或权限。

Media：唯一替换 retry 的 initial-only 假设；消费五元组，区分原 initial/affected 实际来源，保实际 ASR/CTC identities、原 assembly/method 顺序、READY 字节与两测量来源；同步受权 repair 仍用原原对象/口，不从新 getter 获取执行权限。

Integration：仅按真实 producer 闭包把最终 approved 源纳包，资源/许可/三 OS 与 Intel Mac 资格仍独立未证；本 getter 不产生资格资源。
Test/Review/Acceptance：独立定义与执行上述真正反验证，保旧失败，不把本 ADR 当它们的通过证据。

已核固定来源（完整必要方法，非产品运行）：

| 普通源/固定文件 | SHA-256 | 实读范围 |
|---|---|---|
| ArchitectureSelectedChildCtcReadComposition.md | e5190059902af0293fb61b9ef5a24e3a39b8a9b05a2484bca6786685730dae56 | 全文 |
| Media44 ChildRuntimeRecoveryGap/Gap.md | b169c9e01f5dbdd3261d6fb7725c3c5a8b8b106650ebf9c2bf9212fd86166198 | 全文 |
| 同 Gap.json | 1e98799a54f73968ad06957259a64618fdc9de855424300e5634b85fcbd5574f | 全文 |
| Backend120 SourceStage/SourceIndex.json | 9a22dec995223337c8221ab6c3b14733a2413716426e73b3625142cd0ed2172e | 身份/source_map 必要成员 |
| application/current_final_evidence.py | bd079e1437d285a38969e82173a917b8f1afdf288718a8ad259f9fe57bc0a123 | 全文 |
| domain/current_final_evidence.py | 7f9e99b42a39ca6a14119ab13be1134235034e884107245aefed243f0a116932 | 全文，原 11 readset |
| application/registered_alignment.py | ea3242d19e7cac1026b5fb464a90a4a0eca8bd9104eea1cb0491a743e5266890 | 314–579、685–811、886–1055 |
| application/affected_repair_service.py | 1b7624f7bd6a75ae0f52d6cba1296317899cd6a0d7e0419a2f745f5c4ffd88a1 | 44–218、592–652 |
| application/current_final_evidence_recovery.py | 2348faa0cc2fb6d021503e6a6807f3ef71bfcf5c1abff9066f62e77dfdaeb735 | 303–419，完整 continuation reader |
| domain/affected_repair.py | 9768bc4220283c2265d7e185a32343d1b5d88e83733ee1b4efd1d5252e05589d | 全文 |
| domain/registered_alignment.py | 72895e603a275bd1127d8f7fdcdf7da987fbb6bed692649ec6fc6fcb73cc7197 | 全文，两 grammar/canonical |
| Media44 workflows/alignment_recovery.py | db6df61634ddab7e8f6a5c52665589467ff24884710f7d644681a86efb7d20db | 全文 |
| Media44 workflows/bundle_recovery.py | c8ea3d9add3c348bfd8c7a8fbefee3f9c7ec9c1c14a886a6e6737a251eeb5d13 | 344–604，完整 candidate/continue/repair |
| Media44 FactoryConsumption.md | 6a8e9498e6fc352264e2477846ecedcbce1f2cfd9e5bd6459cbf9323574fa3f9 | 全文 |
| Media44 Handoff.md | 5681bf7df5beb8b79b27b4a89219ba5099bf021220894b52f68c0e63b2ae3db5 | 全文 |
| 原 ADR0056 | d4e651f07f982b77469ca73de143a1b2fec691909647b56b36c9f314534cb144 | 原永久 Architecture 已全文核，保持不改 |
| 原 repair-role-dependency-analysis.md | 4e35939e01d9291f501db95086519a24d4147d1dd052e651c3439eeddcd6db8b | 原 §6 第九方法准入保持；role 变更不在本卡 |

准确普通路径、工具自然终态与读者释放在 Architecture/SelectedChildCtcReadComposition/Handoff/输入索引固定。完整 R1 未验收，R1 完整独验后连续 R2。
