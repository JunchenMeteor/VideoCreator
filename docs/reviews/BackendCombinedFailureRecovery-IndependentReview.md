# Backend Combined Failure Recovery — 独立源码评审

结论为 **SOURCE_REVIEW_FINAL，有一项新的 P2/OPEN_SOURCE_STATIC：BCF-R01**。本固定 130 源已实现原 whole verify 失败后的诊断 join、精确 QC throw 现场、实际 no-lease 恢复探针及 selected/journal/source 的原事务转移；这些机制有源码支持。BDE-P01/P02 只获得下述局部修复支持，完整制作/恢复问题继续 OPEN；Media 消费、qualified-resource observer、合法 child 首次选择和耗尽时 pending 出口尚未闭合。没有执行产品、Pydantic、SQL、Worker、provider、模型或任何测试，没有安装、OS、API/MCP、完整作品或 R1/R2 通过结论。

## 固定范围与身份

本次卡：G:/开发测试/Projects/VideoCreator/docs/task-board/BackendCombinedFailureRecoveryIndependentReview.md，SHA bb974ac0f82bd041bf4af9bdf72a7dfda4894ba3bae9189339bab3ab956ab9a3。只读停止普通副本及原合同；未读取热 0062、实际 Test 输出或后继实现。本次评审也没有授予新 117 材料或旧 19 第四次运行。

固定 Backend 根：G:/开发测试/Codex/VideoCreatorImplementation/Backend/CombinedFailureDiagnosticRecoveryImplementation/。实际新源依据 SourceStage/SourceIndex.json 的 source_map[*].ordinary_copy，未使用生产 source_path。

| 输入 | 实际 SHA-256 |
| --- | --- |
| 新 130 SourceStage/SourceIndex.json | 41b2f0e2650b10b97a7353a574e5f131164ae9a597d763435df11c5ab912c83d |
| 原 127 BaselineIndex.json | 2647be662e31cafb8c9870c5276b8740df3ffd9bbfc701dcea79a5d67e38a424 |
| 批准 128 ReviewableCurrentSource/SourceIndex.json | a69f08ef105996a83112505384a9a40e675af109fe0ef65f6cb377c9d6c29067 |
| FullDiff.patch，120459 B | 4656e7b54535be18ad7669f38d3031c33ad0aaf6cd36a0ea517f62b77be18c38 |
| AuthorizedContinuationDiff.patch，102832 B | ae7ff4a72772fa46fa4b25a9755a243d62208fa5472af0c201decc0a6453470c |
| Handoff.md | e680c9fd355de70a880d143a64936dc536d8107d1c7a9ab267de0f2da2611659 |
| Handoff.json | 658a8f8c1284ab0e9c6df7d2eb29386a7e8a332f593963f2dacbc21301676a7c |
| ActualInterfaces.md | f3b711980aa986fe8aeb096558c5627d8518bade48a191376a6f7dce675e900b |
| OpenSeams.md | 49609474054b7e8e3bbc98f8077eeb9e28629bddbdc84508019703d5f896864e |
| ADR0060 停止普通原件 | 8fc928e2ea0ff418a0ee1cfe998baf5d86873d542989bf2f22f100df114d184f |
| ADR0061 停止普通原件 | 04b522d08cec343bbd420869f37b949dcd6f301d837dd3bc8319ce071e00776d |

ADR 普通路径为 Architecture/CombinedFailureDiagnosticSelectionCorrection/Ordinary/Decisions/0060-combined-failure-diagnostic-join.md 和 0061-diagnostic-selection-transfer.md。原 BDE 两 Finding 保留，SHA 分别为 107c9413fa493f65ca96d84f773f4e8b6217352242c7a6330923b8085d9eabfa、9318b8b4007894ab53d1c64fc9de99b453076baafe4e9d9b3a5db0cb362eb0fb。

独立身份核对覆盖新 130、原 127、批准 128 普通源，以及卡、规则、合同、原 Finding 和正式件，共 411 条路径记录（这是记录口径，非全机/独立文件总数）。InputBefore SHA 73b17d4e1ab21ca414448537fde332ee623ed29d7dd44efb74b13a36fd1cb104；InputAfter SHA b138a0f18cec8f8bb9970a0f537f4f69df46a078ffda434a949ef3d732d2e08b，411 条逐条 bytes/SHA 无差异。

两个 diff 均由评审自己的 PowerShell 文本分析器完整读取，逐 hunk 校验原 context/removal，再在内存重建全文并对照真实新副本；未 apply、import 或执行被测模块。原 127 对新 130：11 个差异文件全文相符，余 119 件 SHA 不变；批准 128 对新 130：10 个差异文件全文相符，余 120 件不变。DiffComparison.json SHA d31de79a974e55d96703e2e5b5668ac7a7a5cc2755bc614f428872e72787a391，21 个文件重建结果均 true/errors=[]。其中 all_new_source_count 被评审自己的 PowerShell 属性枚举写成 130 个 1，原件保留；独立 DiffComparisonCountAddendum.json（SHA 1c6d03754f27462ccc6f10ac9f6e764bcceb16789ef2618b857e35be9c50126c）明确实际 scalar=130，不回写原结果，也没有为此重跑目标。

## BCF-R01：释放后的 active 输入阻挡当前登记

**P2，Backend，OPEN_SOURCE_STATIC。** 固定 Finding 位于 Review/BackendCombinedFailureRecoveryIndependentReview/Finding-BCF-R01.md，SHA cdd63c85bd22e83aeed6414e0a6f13932c4eadfe700b643bf7c9964baea85e21。它是条件性源码反例，没有 SQL、Worker 或 UI 实测。

最小条件是同一 service、Run、preparation、线程已经 prepare_component_diagnosis；旧端口关闭；正常恢复取得新 lease/fence；在下一次 whole verify 前没有再次 prepare 覆写缓存。即使当前 selected 合法，join 仍取旧输入并收到 diagnostic_source_denied403，当前 selected 读取不会到达。

完整普通源根是本 Backend 根的 SourceStage/SourceCopies/services/engine/src/video_creator/application/：

- component_diagnosis_service.py:343–348 同时记入 held 和以 Run/preparation/thread 为键的 active；351–356 拒绝已释放、不同 lease/thread/fence 输入。SHA a2747f788f03cb5d207685d7b56d400b6856fbb36814c1b91726dd916af2bd15。
- current_final_evidence.py:159–172 删除 held、记录及 source/selection/outcome 等，却未删 active。SHA 6cdbdd5c9789bf88a27c9fb243e4712138f9469a337e1a4b73948e918cf5379e。
- media_registration.py:825–834 是实际 Worker finally 的 close 调用链。SHA 72ce559d18adb2bef283e3cb7fe9de4453f9c1ee3a173386601459286e483681。
- diagnostic_selection.py:220–230 命中 active 即 return，没有证明其属于当前端口/lease/fence；不进入 selected 分支。SHA 4de38cab02bae5bafccbf37f3db6547abfe5708d792c073b6052f0dae2192078。
- current_final_evidence_service.py:305–321 将失败和成功后 join 都接到该读入口。SHA cc3956af0ae7fc346622a61a4ed7f975c877bc790c12500dae2770c240a954b1。

固定 130 件文本中 active 只有创建、赋值、读取三处，未见另一实际清理。诊断清除后的 final_validation_after_analysis 也不应被迫重新发起已 settled 的诊断来覆写缓存。若合法消费者先重新 prepare，缓存会覆写，故不宣称所有新 fence 必败；未来 Media 顺序未实现也不能当运行反证。

修复归 Backend：把 active 所有权完整绑定实际端口/lease/fence/thread，并随关闭移除，或在优先 active 前证明其仍为当前有效输入。不得删除 held/current 拒绝、吞 403、强换 input/key、清 unknown 或绕 selected/source。后继 Test 应检查关闭→同 Run 新 fence 正常 selected 读取、同 lease 当前输入和错误线程/fence 的原拒绝。

## 原 BDE-P01：一次验证失败后的 join 已接入，完整链仍 OPEN

current_final_evidence_service.py:268–323 设置真实同线程验证 scope，275 只有一次原 self.verify 调用。_FinalEvidenceProblem 的 precision 分支保原完整报告 raw/ref、max(start,end)>200000us 的实际 failed units 和依赖闭包，再注册 precision_failure；无报告的原证据失败保 reason/依赖并注册 evidence_wait。所有这些结果在305–312进入 join。没有新 READY、第二次 whole verify、将不合格精度改 verified 或删原两 authority 门。

bundles.py:2724–2727 仅在原 bundle_quality_incomplete throw 现场调用 _current_quality_failure。diagnostic_selection.py:232–256 要求真实验证 scope、同 lease、当前持有 diagnostic fact、实际 READY QC 文本与 manifest ref，保原 required/incomplete checks；不在泛 EngineError catch 中猜 QC。current_final_evidence_service.py:313–317 只捕 CurrentQualityFailure，没诊断时抛原错误。其他权限、资源、版本、来源错误继续传播，不能洗成组件判断。

join 的原 outcome 强身份/lease/thread/30s TTL，诊断与原 precision ref/failed units 必须相符；组件判断不可抹去先前 precision/evidence 失败。CurrentFinalDiagnosticSource 保 original_snapshot/quality_failure、exact journal SHA 与精确 original ref。timing_only/no_component 分支保原未闭快照；没有 Verified token 的恢复只标 final_validation_required，源码不会伪造发布权限。

因此原“失败直接 early return、不 join”的具体机制已有 **LIMITED_SOURCE_SUPPORT**。BCF-R01、实际 Media 消费及真实运行未闭，BDE-P01 的完整制作链继续 OPEN；本报告不以新增接口、119 AST 或作者布尔自关。

## 原 BDE-P02：真实变化的恢复探针与原 writer 接线，局部支持

DiagnosticResumeRuntime 实际由 current_final_evidence_runtime.py:176–187 的 waiting_diagnosis 路径调用。无 lease 的探针使用原 current Owner 注册/held guard，读取原 journal、selected/source、完整 parent/Fact/index 和已 settled 原 ASR；它没有构造假 lease 或自行产生 qualification。new READY material、实际 accepted 非空反馈才形成 completion，排序后的严格 v2 canonical input 保原 full input 和 completion refs；原 v1 字节及 input-result 不为新 fence 改盐。

相同 input 的实际 settled 结果复用而不重发收费 Operation。component_diagnosis_service.py 的 append/read 检查实际 factory/driver 产生的方法 refs、原 Operation 成功/settled、cost、route 与 source/expected/observed；不能以 completion 文件或长度相等代消费。缺 qualified-resource producer 分支明确 diagnostic_resource_observer_not_ready503。这个拒绝是未接线边界，不证明原资源本身无效，也不代表观察器已经存在。

Runtime:246–265 的 needs_reconciliation 只在 exact journal/current/request、pause/cancel/human review 和实际 unsettled 账本检查下更新原状态，既不 queue、新 lease、换 key，也不新收费。正常变化:271–293 在原事务执行 journal CAS、实际 probe writer/current 检查和 source 复制；claim 再以原 admission 得新 fence。已 committed source 与 queue/claim 对应新 journal，但原 ref/source bytes仍保持。没有将 unknown 暗转 retry_final_validation。

恢复后的 no_component/timing 分支（diagnostic_selection.py:165–218）读取 actual settled recorded 强对象，保原失败快照；首次仅诊断而未 whole verify 的场景生成显式 final_validation_after_analysis，下一步仍需真实 whole verifier。它不发布产物，也不能因诊断不报组件错就忽略原精度失败。

上述真实 READY/反馈、同 input 复用、unknown 及同事务 source 接线有 **LIMITED_SOURCE_SUPPORT**。qualified-resource、Media driver 的全部 v2 消费/结果映射和 child/耗尽窗口未闭，因此 BDE-P02 整体仍 OPEN。

## ADR0061：两个选择 writer 与三个消费者

component_diagnosis_service.py 的 Fact/input-result 是 append-only 原事实：select=False 不等 selected。相同 input 不同 Fact/来源 409；旧 default select 的冲突仍在原事务 rollback，既不 author新 fence 改 Fact，也不强选已收费结果。现有正常 reader/完整 Operation 当前事实保护保留。

diagnostic_selection.py:304–350 生成 eq=False actual PreparedSelection，强绑定 record、lease/thread、TTL、captured whole selected/journal/source/相关事实及真实当前 context；旧 selected 完整 body 或 absence 被保留。362–389 只接受 park/first_publish，使用实际 connection 对旧值 CAS。391–409 只替换本次实际新 selected/journal 的 capture；其他原 capture 必须逐项 current，不能以广泛“自己的写入”放行来源变化。

park writer 使用原 current guard + 一个事务，先提交 selection，再写新 journal及 exact companion，并在末门核 current。first publication 由 bundles.py:1413–1468 原 publication_guard+transaction 调用 commit_first_publication_diagnosis；随后原诊断、correction pair、CTC writer、所有 Operations、request/rights/authorization、文件 identity、deliver-step 和原末检查继续执行。infrastructure/database.py:179–189 的 BEGIN IMMEDIATE/commit/except BaseException rollback/finally close 说明后面的拒绝会回滚前面的本次 selected/publication source 写入；这是静态事务语义，未实测竞态。

publication companion 的 manifest/selected/ref/input/binding 仍指向实际 Verified 关联。read、join、publish 都依据原 selected/source，不消费 pending Fact 作为发布权限；原合法 immutable 已发布观察仍有原 replay 分支，未重装 request/policy。保留原 human rights、真实两 authority、200000us、method闭合和所有版本/引用保护。

## 保留拒绝与明确未完成接口

原 call_abb97cb9b0144316b52fe11d329044a9 同次工具拒绝两个 patch。OriginalToolInput/Output 和 UnexecutedPatch1/2 完整保留：needs_reconciliation→retry_final_validation 未应用；同调用 child hunk 也未单独重试。本评审不把不同 safe reconciliation writer 当作原被拒动作已获允许，更没有 apply 或授权该原 patch。

停止源码真实拒绝与待实施分列：

1. **合法 child 首次选择未闭**：prepare_current_diagnostic_selection 对 journal preparation 与候选 child 不同，以及 previous source ref 与旧 selected 不同仍409。新架构0062不属于本次依据，不能用待定合同说这条已修。
2. **耗尽且 pending 选择未闭**：finish_current_final_evidence_failed 的新 companion 只接受 retained committed selection；pending首次/successor 明确409。原 Worker 的实际耗尽调用需正确 park/terminal 顺序；本片没有第三选择 writer，未把409当成功失败终态。
3. **Media 消费未闭**：media_registration.py:396–406 实际 invoke 对带 context 的恢复增加 diagnostic_source 关键字；没有改 Media source。analysis-only、全部 completion 消费、append/read、下一 whole verification、waiting_diagnosis 的 producer/Worker返回映射仍需真实消费者接线。接口被调用不证明 callee 已兼容。
4. **qualified-resource observer 未闭**：真实安装 authority/current/revoke/floor/catalog/method/route/runtime 来源及 exact completion/readset仍缺，不能 caller JSON、file/SHA 或已有有限 native probe授 qualification。
5. **BCF-R01 缓存所有权缺口**：已交原 Backend；新窗口使用修复版本须另固定输入与独立复审，不能回填本片旧130。

这些问题不得通过降精度、放宽权限、清 unknown、换 key/fence、省人审或直接 queue 来求绿。必要安全接口/终态排序由原归属者给出具体固定实现和获准合同，之后另 Test/Acceptance 验证。Review 不代架构实施、不修源码、不授运行。

## 方法、错误和工具终态

本次读完整新/变更模块正文与相关原事务/Worker路径，全文核 ADR0060/61、正式 Handoff/Interfaces/OpenSeams、原 BDE Findings、原拒绝原件及两个完整 diff；不是全机扫描或每个不变源的全功能审计。130 件身份/119作者 AST 也不等真实业务覆盖。具体普通输入和 SHA 全在 InputBefore/After；source readers 在 4f391d 自然0的末输入核后释放，之后仅写评审自己的文件。

以下原自有错误、截断不删、不当产品红：820a86 对对象 map误用 records 定位；104770 PowerShell管道 ParserError；07ad47 bare false 元数据错误；96ffdd及3c2ca2/be83ef/3b415e/697de0大输出截断，仅必要遗漏段定向补读；d2af0e旧 rg入口不存在，bf3d8d Get-Command 定位现有 rg；b7e5bf publish中段输出截断由29a61d精确补齐。da44ec 的 Count枚举误写保原receipt+独立addendum。它们没有运行目标、修改 source、回写原结果或触发新额度。

读工具最后实际执行为 4f391d，exit0/no live，InputAfter differences=[]；正式文件输出工具终态由 FinalizerTerminal 和 FinalHandoff 另记录，不从文件存在或角色 running推断成功。本报告所有结论停在 SOURCE_STATIC。旧19三次、原准备/运行/工具红和未执行范围继续保存。六归档、TTS/ASR、真实中文 CTC质量、完整作品多模态、Owner/OS/native/API/MCP、安装及三OS完整R1→连续完整R2均未由本报告验收。