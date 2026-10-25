# 0062 子级诊断选择及耗尽出口 — 独立合同评审

**结论：SUPPORTED_DESIGN_ONLY / DESIGN_SOURCE_REVIEW_FINAL。** 对固定新 0062 与实际停止 130 源的相关 caller/callee 完整对照后，未确认新的 P1/P2 合同阻断。新合同给出了可实施的 held parent→child 来源、原 park 内选择及 terminal 原子顺序，补足原 0061 拒绝边界的具体设计。此结论只支持这份精确合同的设计范围，不授予实现、应用或运行；Backend、Media、Integration 均须在各自获分派范围实现后独立源码/真实行为复核。原 BDE-P01/P02、child/耗尽实现和 BCF-R01 不由本设计评审关闭。完整作品、Owner、OS、SQL竞态、安装及三OS完整R1→连续完整R2均未验收。

## 输入与独立核对

任务卡 G:/开发测试/Projects/VideoCreator/docs/task-board/DiagnosticSelectionTerminalOrderingIndependentReview.md SHA b0085f22053d8904e9a013256128d200480e99a34179d80e17f3ccdf92b3b393。新 0062 使用停止普通副本 G:/开发测试/Codex/VideoCreatorImplementation/Architecture/DiagnosticSelectionTerminalOrdering/Ordinary/Decisions/0062-diagnostic-selection-terminal-ordering.md；23412 B，132 行全文，SHA 8ca4b139804905d6ddacd67de7fabe5417d68db23abf5f2f71e69edc48178496。

架构根为 G:/开发测试/Codex/VideoCreatorImplementation/Architecture/DiagnosticSelectionTerminalOrdering/：

| 输入 | 实际 SHA-256 |
| --- | --- |
| Handoff.md，完整读取 | 8698c811c233537dbcb29d411a859ab2ee2257a51d1e4a6eb70c2d49d76cac03 |
| Handoff.json，完整读取 | 1f91974c4606731eecff6ec8f6e40f7cead1250b6ce4ee3b18d90f49cde68193 |
| OrdinaryIndex.json，34 件实际成员 | e67724e6a88c78e4545e7b73319af25b515000326a40079155e11d47830526bf |
| InputPins.json | bfd671050fefc6d3ae3db8409e750f87cdfe62692854d64737c987c7d97d28ec |
| SourceAfter.json | 4ec6f5ba41caae1a7c6c11e0bb631e619ee544306d567da34777b79f729693c0 |
| ReadObservations.json | c14ceb2e48bf40ed2294f2090051bf130b78da8a029ce3998f334db7a84ec9f3 |
| 原 0060 普通原件 | 8fc928e2ea0ff418a0ee1cfe998baf5d86873d542989bf2f22f100df114d184f |
| 原 0061 普通原件 | 04b522d08cec343bbd420869f37b949dcd6f301d837dd3bc8319ce071e00776d |
| 原停止 Backend 130 SourceStage/SourceIndex.json | 41b2f0e2650b10b97a7353a574e5f131164ae9a597d763435df11c5ab912c83d |

原 130 完整源索引根 Backend/CombinedFailureDiagnosticRecoveryImplementation/；所有源码只读其 ordinary_copy，或上述架构索引对应的 Ordinary/Source/Application、Domain 副本，未读 source_path 生产文件。新缓存整改、Media生产消费、资源Mapping及后继热合同不在本次输入。

本轮 174 条路径记录覆盖架构 34普通件、停止130普通源、索引/正式材料、任务卡及原正式独评；记录口径不是全机文件数。InputBefore SHA 6bdf6072748be3eea0b1dab9bee88ffcaa2b9a007b3ab18dbecfaf71fee0ee21，InputAfter SHA 1c48e1562ee95da5258011e0f40ea8f482920e228f5f49e3b4aa34938919e126，逐条 bytes/SHA differences=[]。没有重新扫描环境、执行产品或以作者34/130/AST数量证明业务兼容。

原130完整独评的报告 ce9a2b585b7f0a21dddf06978ad1b45a769c4ad0c0a9bdfd12455e109f6753a7、FinalHandoff 3ade5e7b05a738e1ce3ad699ed364024e1ddbe2b5a37b4ce3866eb567830201b 为已停止背景；本轮必要完整方法再定向对照，没有以设计覆盖原源码仍未实现的门。

## 1. parent→child proof 的必要性与来源

旧 diagnostic_selection.py:304–350 的 prepare_current_diagnostic_selection 要求实际 held record；320–326 要 current journal preparation 等于候选，且 previous source diagnostic_ref 等于候选准备旧 selected。子级创建时原 journal 仍指父准备，因此原合法 child 第一次选择会被拒。旧 affected_repair_service.py:163–193 的 _selected_affected_child 只核唯一 command、parent/child intent 和 lineage/report/subset，不能独自给选择、Owner或 FullPlan许可。

0062:37–56 没有删除原同准备门：普通不匹配仍409，只有原 Selection service 根据实际 current journal 自动触发内部 prepare_selected_affected_child_transition。proposed helper 收实际 connection、lease、current父journal、child和实际 held recorded；eq=False、service/lease/fence/thread、30s真实登记防止调用方参数或序列化记录自授资格。recorded.fact.parent_preparation_id 表示被诊断 child，lineage 父准备另有准确事实，不复用旧字段冒父诊断。

proof 要求 parent executing/repair/current fence、原整 journal body/source及selected、唯一已提交 command/lineage、父子原 intent、child allocation/READY/input/index/不可变 Fact、原真实 failure/recipe/subset/route和全部 captures。诊断父必须有原 source/selected；普通精度父可保真实 absence及完整失败报告，不制造父诊断。child 仅首次 absence或合法相同ref retain；任意 child、不同command/ref及孙级不泛化。

真实权限对照不是只看关联函数。diagnosed_affected_service.py:72–194 检查原 FullPlan、script/storyboard/quality、同 current verified诊断reader、单mapper/recipe、完整route和当前rights；政策 execute_plan 真实admission与human整plan批准分别存在。affected_repair_service.py:386–565 的 ordinary precision 分支读真实全报告、200000us失败unit/媒体闭包、实际资源及两 admission；无finite generation target或实际 alignment qualification就拒绝。0062:49–54明确要求复用这套 current/targets保护及全Run settled，不能用 lineage 或 SHA 替代授权。

revise_current_final_preparation:326–494 的实际父 journal/fence、command/fulltarget、child ASR/CTC/asset身份、同command幂等及共享 revision_cycles+1 逻辑也逐段核对。0062要求保留唯一原child及真实未受影响资产，而非新增计数或重新生成。新 proof 不可用当前已有单 `_selected_affected_child` 结果代替上述完整来源；原诊断parent只读组合须由Backend从已登记事实重建，不能伪造父 live continuation。

## 2. 两个 writer 与 source-v3 接点

0062:60–80 把迁移放入原 Runtime.park 的 current_guard和同一短connection：先全部原/current权源核验，再 child absence或same-ref selected CAS、父 executing journal整body CAS为实际child snapshot、精确新source同事务写入。父 selected/body/source历史不覆盖，只允许替换本次CAS成功的新child selected及current journal captures；parent/source/资源/其他原行继续必须相符。原 first publication不作为已有父journal的捷径，无第三选择writer。

这与旧 Runtime.park:94–155、selection.commit:362–389、final_writer:391–409 的结构能对应。实际原 park 中 child关联检查在 selected commit后，但仍同事务；新合同要求完整证明在选择前，后续拒绝仍整体rollback。终态或子级所需改动应落在原服务实现，不能仅新增 helper但仍让旧320/325无条件挡住合法分支。

新严格私有 source-v3 继承 v2 的完整来源及 selection_evidence，并增加 selected_child_transition/terminal_failure 两个 typed成员，至少一个非null。child proof 精确列 parent/child intent、原 parent journal body+SHA、parent source/ref/selected、command/lineage bounded refs、父失败snapshot SHA与真实fence。旧父 body只作历史，新的 source/preparation/selection必须是真child；child old selected不能填父body。无新 public DTO/SDK变更，也不将 parent history变成当前执行许可。

现130的 parse_source:34–44 只收 v1/v2，domain/diagnostic_recovery.py:91–156 只有旧selection/source grammar，443–473 的queue/claim source copy重parse，475–495 current读要求真实 executing lease/continuation，497–517 的首次publication只允许实际原Verified关联。因此新增 v3 必须同时由Backend维护唯一 grammar、CurrentDiagnosticSourceRead union、parse、history/current read、copy及publication入口，不只添加类型名。0062:68/80/118已明确这些职责和旧 v1/v2字节/parser语义保持，设计没有授权兼容fallback、吞422或使用历史父权源。

source定位指向 exact新 journal SHA；原 parent journal正文及原source refs另存历史，不含“新source自己的SHA”，没有自SHA循环。修改 journal→source同 connection，response丢失只能读取原 committed材料，不能重新生成时间或拼半个source。当前130尚无这些 v3实现，设计支持不等调用链已闭合。

## 3. 成功 child 的待提交选择与独立新 attempt

0062:82–84明确只接受真实一次 wholeverify结果和 actual held outcome/Verified，而非“文档ready”。已有父 journal的成功 child仍不能 first-publication；原 join生成waiting_diagnosis/final_validation_required、准确child intent/candidate/READY/ref和repair=None，保 verified_then_diagnostic_block，关联真实 held selection。

原 park提交child选择和v3 source，建立准确 final_validation_after_analysis context；原 no-lease probe在真实 current permission/settled事实下 queue，原claim获得新fence。新 attempt只能重新走原完整 once verifier、两authority/QC/rights/current，再发布；不能同attempt第二wholeverify、持久恢复旧Verified、重诊断/ASR/生成/扣费或增加修订。

这是对真实 current_final_evidence_service.py:268–323 once-verifier、diagnostic_selection.py:165–218 已有 clear-analysis等待及 Runtime.claim:333–366 的具体接线要求；原claim确允许 queued或合法旧executing/fence恢复，不必造假continuation。若 original wholeverify实际失败则保原完整 failure/source，不能借成功等待路径洗掉失败。当前Media final-validation真实消费仍需另实施，不能把未来描述当真实callee已就绪。

## 4. 耗尽 terminal 的可实现顺序

旧实际 Worker:754–770 在外部读counter后直接 finish；old finish:368–419 只收 retain，pending:411–421 刻意409。原 park在150释放lease，之后153的某些诊断终检存在live-lease前置。因此不能用“先调用park、再调用finish”解决，也不能放宽pending finish或构造新lease。

0062:88–104 把决定权留Backend的原park：Worker只交真实held assessment，三种waiting_evidence/repair_required/waiting_diagnosis状态仍要求bundle_ref为空、state/preparation/materials全文相符和服务身份。Media维护自己实际grammar，不由Backend伪造结果。limit predicate以原真实finite repair失败、非guidance、全Run settled、当前Owner/request/action/resources和实际counter为前提；cap是immutable request及已批准whole-plan/projection更窄cap的min。无额外plan cap时保原request，不把模型建议或全局配置当权源。

设计顺序可以落入同一原 transaction：

1. live `_lease`、pause/cancel/human review优先、conflictingwait、settled、held/parent/selection/counter/cap源全部真实核验；不得先释放。
2. 判waiting或terminal，原两个writer中的park执行选择CAS、journal CAS及source。
3. 原failure snapshot/blocked历史保留，terminal journal的executing/currentfence只代表最后真实claim；实际Run/Production failed才是终态。
4. 在lease仍有效时完成全部需要 `_lease` 的assessment、selection、plan、Operation、资源与已获得两authority结果来源的final检查，准确替换本次CAS行。
5. 同事务最后更新 failed、清worker/lease，写原事件；之后检查精确持久终态/source/selected，及实际 issuer/current guard。不得再调用需要live lease的旧assert，或用True/失效lease代验。
6. 任一冲突整事务rollback，不出现可见 waiting→failed窗口，不queue/new fence/dispatch。

该顺序是对现有livelease冲突的实际设计修正；这里没有 SQL竞态实测。新 FiniteDiagnosticTerminalEvidence 的reason/counter/requestcap/真实approvedplanRef+cap/min/request/action/fence/time来自writer实际facts，仅供历史解释，不是新grant。ordinary无diagnostic的失败保原journal/source absence语义，不为v3造Fact或selection。inconclusive/guidance/信息或resource等待、unknown、成功token均不满足terminal predicate。已retain独立finish可复用同一失败predicate及source/current终检，但不新增选择提交。

## 5. 崩溃、拒绝及未关闭项

0062:108–114 分别约束 append已commit但park前、park事务中、waiting commit响应丢失及terminal响应丢失：只能原事实纯复用或完整commit/rollback观察，不重复旧lease、不重新child或counter、没有新的扣费。terminal观察要实际failed Run/Production、精确 journal/v3/source/selected与原binding/input一致；不能据executing历史字段复活权限，输入变化也不得自动恢复耗尽或偷加cap。必要新授权仍走原权限/预算服务。

unknown/submitting/unsettled继续needs_reconciliation，零queue/claim/dispatch/收费；pause/cancel、人审及current失效优先。403/409/422/503区分真实身份、CAS/版本、immutablegrammar、确缺注册服务，禁止泛EngineError吞成retry或None。原两authority、200000us完整测量、rights、共享预算与限次、未受影响资产保护不缩。

原自动审批拒绝同call的unknown转换与child hunk完整保留，不重放、不拆开换工具。新0062要求的是更窄且完整的 held/source/current proof和原writer顺序，未直接授权那两个旧 patch；后端提交实际新实现仍受独立实施/正常自动审批边界。

未关闭：BCF-R01 active输入生命周期另修另审；BDE-P01/P02整体；真实child选择/terminal/v3消费者实现；qualified-resource observer/安装权源及真实Media方法消费；SQLite竞态/kill恢复、Owner/OS/native/API/MCP/模型/媒体、安装和三OS完整R1→连续完整R2。新架构文档不能替这些真实源和结果。

## 职责与最小后继核验

Backend负责唯一helper/held类型、prepare内部合法child分支、closed v3 parser/history/current/copy/publication、原park finite终态、retain finish和Worker实际caller；实现应逐项展示旧130→新差异，不仅AST或接口存在。Media仅消费真实ports、assessment/source/input、child-ready与final-validation，保真实result grammar及零重生成；Integration按实际源码/私有grammar覆盖，不把缓存文件或SHA升资格。Review不自行修合同、实现或测试，实施/运行由统筹另明确分派。

后继独立Test可依据§7提出实际基于真实权源的正反窗口：两类父来源→唯一child、parent/current/command/lineage/input/CAS竞争、successful child只park再新fence验证、first/successor/retain不同cap耗尽、lease释放前后kill及响应丢失、unknown与pause/cancel、人审/两authority/rights撤销、旧v1/v2和legacysame-ref兼容。本文不是可执行Test标准或运行准入，原历史次数与三败19仍保留。

## 过程与终态

新0062 132行全文读取；相关实际方法按完整目标区间对照，原130报告作已停止上下文。34ordinary与130身份全核，不声称全130功能或01—11正文再次完整审查。675bf6索引显示截断93tokens但结构化对象完整解码用于pins；c3cbe3的元数据正则包含services/engine前缀导致投影过宽并截断，不当环境扫描/全文body证明；c83f95源码合并显示61tokens截断不用于新qualification。所有原source/拒绝/报告未修改，未从文件存在推工具终态。

174条有限InputAfter在本人23e900自然exit0后无漂移，全部source readers释放；其后只写自身报告和交接。MethodMapping.json SHA 99e657b63ba2123f2c9791ef271249dda61e14c420015b79c3fbf9d456455561保具体现有method→所需设计变更，并逐项标 implemented_in130=false。新合同无新增confirmed P1/P2；**仅设计支持，不关闭实现finding、不授任何代码应用/运行/资源/Gate0/R1/R2。** 最后正式写工具的自然终态及无live由FinalizerTerminal/FinalHandoff和本人FINAL消息确认。