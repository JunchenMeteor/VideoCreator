# RV82：B42 原实例事实恢复与未应用 native 候选独立评审

结论：**SOURCE_STATIC / CHANGES_REQUIRED**。已接受但未激活的事实/拒绝代码存在两项 P2；未应用 native 候选另有一项 P2。原 RV80-P01/P02 均保持 OPEN。无产品、DB、Owner、native、API、模型、测试执行，费用、秘密读取、网络、安装均0；没有应用候选或批准 RuntimeBinding/资格。

## 固定身份与已读范围

固定85普通源、75 Python仅AST；完整原B41基线82份 BeforeCopies与正式SourceIndex `856de0b767dbd95393a87cf27de9a673a5fd4e94ab3f5ce9cfd11f17244e2c41`相同。连同正式件、ADR0040/0041、原RV80及治理共194个不同输入，前后无漂移。[Snapshot](G:/开发测试/Codex/VideoCreatorImplementation/Review/OwnerSetupRecovery-RV82/RV82Snapshot.json) / [InputAfter](G:/开发测试/Codex/VideoCreatorImplementation/Review/OwnerSetupRecovery-RV82/RV82InputAfter.json)保存完整路径/size/SHA，不读热源码或散列整环境。

| 正式件 | SHA-256 |
|---|---|
| B42Handoff.md | c267f9e5fc2e52b8319e2c8f3569b5bd8c38cda64a468f7e309b46f73edaa12f |
| B42Handoff.json | 5e4860ed9cb174ee61ded1cb9493e8b976af4dd3502f850f31811da19736ab93 |
| Interfaces.md | 04cd4d2f917f0195cc1049dfd9cffb8917d4c2b8f8c9bf47f6efd237ec167ac1 |
| SourceIndex.json | 960f155fcab5f4ce5143f560ac84c67e00795b2e60545a6045f6d3e74884bbd1 |
| StaticFinal/SourceSnapshot.json | 0016981aa755c1a1e64f503a8c400f23b7e4ffcdbcdc52ced870d71d038f0d9f |
| 原拒绝 patch | b5ee0b712e53896241254b67b97f4358e67f1b9f0d2c523f3b74e98453574ae9 |
| 未应用 candidate patch | 490c5f020ad34037747cec164337fb922dcb8860b0197cda61141d6ca18c1bdd |

全文审三新模块 owner_fact_sources / accepted_goal_facts / owner_setup_history，原delegate/历史/current/OwnerControl与ProductionControl相干方法、原Setup历史与planned写入、固定native/held代码，以及候选两源/完整patch与原拒绝patch。85源身份核不是85个文件全部方法的人审声明。展示截断只补缺失accepted191–323及Store434–546等段，未把截断输出当全文。

## RV82-P01 — committed收口未核原派生回执ID

**P2 / OPEN / SOURCE_STATIC / Backend。** 主源accepted_goal_facts SHA `11617eb3ef7a781e34782f1a2c1d4dbbf1d6d9e469eb4afc98844e1508549d0c`。

[accepted_goal_facts.py:272](G:/开发测试/Codex/VideoCreatorImplementation/Backend/OwnerSetupRecovery-B42/StaticFinal/SourceCopies/services/engine/src/video_creator/application/accepted_goal_facts.py:272)–276在GOAL_ACCEPT分支复用Daily._original_result，但只与protected intent比较project/production/run/derivation四ID，283产生finish_committed。Daily._original_result:726–733→_child:475–492核派生row自身canonical/hash/ref/command，没有将ProjectDerivationReceipt.receipt_id对回intent.receipt_id。原真实写入 [daily_projects.py:1007](G:/开发测试/Codex/VideoCreatorImplementation/Backend/OwnerSetupRecovery-B42/StaticFinal/SourceCopies/services/engine/src/video_creator/application/daily_projects.py:1007)明确使用该planned ID；ProjectGoalAccepted没有此字段，模型不会自动补核。

最小静态反例：完整committed原Goal、DB=R、同SHA floor仍pending，原protected intent/接受command/Production/Run/child body不变；仅改派生row receipt_json的receipt_id并更新它自己的receipt_sha256。当前历史验证接受自身一致的新receipt，缓存同连接也稳定，380–391可complete原floor。违反ADR0040完整五planned ID/原receipt才收口；未执行篡改或DB反例。

整改：finish前核真正原child/receipt与intent的五planned ID、instance/owner/key/parent/creation、原request canonical/hash与实际requestRevision完整关联；损坏保pending422。正常已commit只完成原floor，不重做副作用。[精确早Finding](G:/开发测试/Codex/VideoCreatorImplementation/Review/OwnerSetupRecovery-RV82/RV82-P01EarlyFinding.md)保存完整链与最小Test条件。

## RV82-P02 — native候选先写后核独立启动来源

**P2 / OPEN / SOURCE_STATIC_CANDIDATE / Backend。** candidateNative SHA `bdd7f0f3b94f468f6c0d81409ac65a949640e692774fd26e622c2edfbff78e2f`；candidateModule SHA `6b113651a364ee21b2e978c461c198b9b188d27a25deb32e928675125c87c75b`，均未apply/import/run。

[候选native:53](G:/开发测试/Codex/VideoCreatorImplementation/Backend/OwnerSetupRecovery-B42/ReviewCandidateNativeStartup.py:53)–62先用carrier image/context开真实held peer，再调用module:46→resolve_before_current，之后才Store.current。[module:29](G:/开发测试/Codex/VideoCreatorImplementation/Backend/OwnerSetupRecovery-B42/ReviewCandidateModule.py:29)–36只校typed对象、两context相等、instance/Engine相同；事实根增加同instance/真实observation，历史核遍原role，却未将本次caller carrier的完整map/image/role绑定到独立实际安装/登记来源。实际domainOwner与持久startup比对仍位于 [Store.current:491](G:/开发测试/Codex/VideoCreatorImplementation/Backend/OwnerSetupRecovery-B42/StaticFinal/SourceCopies/services/engine/src/video_creator/application/execution_registration.py:491)–492/:520–522，晚于可能的commit/complete。

条件：原pending已知expiry且原facts完整；peer/carrier自身一致且真实OS同Owner，但完整carrier与真实安装record不一致，或Bundle配置domainOwner不同。源码可先收口原Goal，再由正常current以409/403拒绝；本轮没启动peer，不声称外部caller实际能伪造此源。ADR0040摆脱执行expiry许可仍需原可信启动来源，两个相等context或自述map不能代它。

整改应在任何writer前校只真实性的完整原Owner/历史安装/action/carrier绑定或另一个真正不可序列化已认证宿主源；不能搬回_active/expiry再阻原过期事实通道，不强制新合法source等于旧pending refs，不创建execution。独立Test须确认错误carrier/Owner在任何commands/revision/floor变化前拒绝，合法过期原源仅可收口。[完整Finding](G:/开发测试/Codex/VideoCreatorImplementation/Review/OwnerSetupRecovery-RV82/RV82-P02CandidateFinding.md)。

## RV82-P03 — v2 completed无结果可被改写denied

**P2 / OPEN / SOURCE_STATIC / Backend。** owner_setup_history SHA `6d04c408606c44e07a5b3e7bc7f0389adb6f30a4b61591169f6d24fee3708ad6`。

[history:67](G:/开发测试/Codex/VideoCreatorImplementation/Backend/OwnerSetupRecovery-B42/StaticFinal/SourceCopies/services/engine/src/video_creator/application/owner_setup_history.py:67)允许completed；163–168无committed_result时仅要求结果两字段NULL，没有拒completed+NULL。真实v2未commit且已知expiry的完整pending仅将phase从running改completed，0010 schema仍接受；随后deny writer:375写blocked，final row缓存:336–339将phase改为blocked作为允许过渡，387–391能complete。

原Setup:644同writer一起写真实结果两字段和completed，这个无结果完成状态是历史矛盾，不能因known expiry洗成denial。整改是context颁发前的封闭阶段/原accept-or-denied/goal_result/独立denial进度矩阵；未commit不能completed，已拒绝必须原blocked进度，合法blocked恢复和已完成后draft编辑保留。反例未运行。[完整Finding](G:/开发测试/Codex/VideoCreatorImplementation/Review/OwnerSetupRecovery-RV82/RV82-P03HistoryFinding.md)。

## RV82-I01 — 窄只读变化的动作来源未齐

**P3 / OPEN / EVIDENCE_HISTORY / Backend。** ApprovalScope称被拒group的committed_denial只读改动remain unapplied，并保当时2635b4无符号的读结果；固定最终history:47/87/169与facts:296–299已实际含它们。现有正式材料未给后续独立被接受的窄patch/具体工具终态；统筹也明确尚无该记录，不代作者推断。需准确补原动作出处/时间顺序或明确缺证，保原拒绝，不用AST/Ruff0推许可。

四共享入口OwnerServices/issuer.current_guard/Setup/native startup的原源SHA与B41相同，故**全局hook确未应用**，上述只读差异不证明偷执行全局hook或审批绕过。[源历史记录](G:/开发测试/Codex/VideoCreatorImplementation/Review/OwnerSetupRecovery-RV82/RV82-I01SourceHistory.md)。

## 有限支持、候选范围与授权边界

- LocalOwnerFactSource是原Bootstrap成员、eq=False/frozen、Engine/PID/thread/epoch绑定、30秒单独事实寿命；实际OS/DataDir/Control/DB identity、Owner floor与native原observation核在writer外。writer仅原成员/缓存/current local observation及同连接Owner/instance行，没有新vault解引用。构造OwnerSecretStore只保存路径，未调用resolve。
- AcceptedGoalFactContext用途由原floor/commands/history选deny_uncommitted或finish_committed；未知namespace/原command/file缺损、冲突、多pending/partial side effects拒绝并保pending；合法active unresolved返回None留原执行路径。短writer前后精确查cached rows；仅原GOAL_DENIED_SCOPE、原reserved revision及v2blocked/progress字段可写，complete原R/原SHA在writer外；无reserve/新key/Project/Run/child/lease/budget/Operation/dispatch/qualification。上述结构有源支持，但P01/P03说明不等完整事实正确。
- 三旧源共同方法只有Bootstrap/Store构造加facts成员，原Daily方法AST全同；新增五delegate。全局startup/current门保持，产品入口不调用这些新writer。原schema10/contract0.3未改变或迁移。
- 候选完整patch由固定两源重建逐字相等，只触一个native indexed factory和一个新module；_current_execution_registration/main AST保持，_factory改变。for_management必须False，管理startup/HTTP/MCP普通route/issuer/Setup均没有新hook。范围确实比被拒global OwnerServices装配更窄，不是已执行“换模块绕过”；仍是正常native启动中会写的prospective动作，不能把它称read-only或自动已授权。其失败分支尝试authority和build关闭、释放原current并保原异常；实际Win32/unknown cleanup未测。

自动审批曾拒绝把历史恢复接入全局OwnerServices，理由是正常启动中广泛引入authorization/control-ledger副作用，原拒绝patch未应用。Review不代人类授权或自动审批；当前候选还有P02，不能请求盲批旧错误diff。修正并重新固定具体diff后按真实授权路线评审/处理，不能借另一工具或module应用被拒动作。

## 原结果、未达范围、终态

原StaticFirst075839自然1（八lint问题），StaticRevision01ccf2自然0、StaticFinal751a70自然0；原PID37332/34684→35352/32336→31728/2532、wait/communicate EOF/streams_closed、85/75及drift[]/sticky[]仅AST/Ruff/字节，不授业务/OS资格。原红和拒绝均保。本评审首94739b/1误猜B42Interfaces.md，实际文件Interfaces.md后81bcf7/0全文读取；是自身定位错误，已单独保记录，不产品红。

RV80-P01仍缺实际已认证startup激活、live失效转交、Setup denied消费和真正setup-aware成功restart；RV80-P02的有限真人Owner-child新政策/current选择尚未实现。本批native wire严格not_ready，NativeInstallationAuthority.observe拒not_ready或缺issuer；typed未来Protocol不是真实producer。所有headless/live/成功Owner/qualifiedproducer、真实DB并发/断点/预算unknown、媒体作品/ASR/多模态、完整三OS/R1/R2均未由本片验证，不能以永久503代最终交付。

末input核0ecdd8/0：194不变。全部输入reader和此前工具自然终态，无live句柄、生产冻结false；不等待Backend后继或T56证据。完整R1独验后连续完整R2目标保持。正式报告写入工具实际终态另存自身RV82FinalizerTerminal.json。
