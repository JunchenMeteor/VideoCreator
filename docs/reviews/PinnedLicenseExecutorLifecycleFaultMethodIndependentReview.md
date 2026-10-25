# PinnedLicenseExecutor 五例生命周期故障方法独立评审

结论为 **SOURCE_METHOD_REVIEW_WITH_THREE_OPEN_P2 / NOT_READY_FOR_EXECUTION**。五例全部 NOT_EXECUTED。PLFM-P01/P02/P03 是当前 Test 方法源码中的条件性问题，未称实际 OS 失败；Integration 后继事件合同、完整 benign Plans、整文件映射和 outer runner 尚未实现。本报告不改变上一轮新 Owner 的 PLEE-P01/P02 CLOSED_SOURCE_STATIC_ONLY，也不把它们升为运行关闭。

任务卡实际 SHA-256：`33ed33061dd265c42d190aa59a5be9b711007c4241d50b07d0d0847c28fe2f82`。唯一停止 Test 根为 `G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/PinnedLicenseExecutorLifecycleFaultTestPreparation/`。过程根为 `G:/开发测试/Codex/VideoCreatorImplementation/Review/PinnedLicenseExecutorLifecycleFaultMethodIndependentReview/`。所有正文取自索引声明的 SourceInputs 普通件；没有读取热 Native、Backend 或新事件实现。

## 确认的问题与责任

三张独立 finding 位于上述过程根，保留完整源路径、SHA、行号、触发与最小条件。

| Finding | 严重度 / Owner | 固定真实调用位置 | 源码影响 |
| --- | --- | --- | --- |
| PLFM-P01 | P2 / Test | FixtureChild.py 37–46；LifecycleObserver.ps1 44–47、56–62 | 双 OS pipe 已关闭、两 Task GetResult 成功不能保证 child 随后的 ready 文件已创建；合法调度可误判 C04/C05 setup 红。须用有界真实 handshake 等两个独立条件，保同原 clock 与红后自然 release。 |
| PLFM-P02 | P2 / Test；Integration 提供真实字段 | LifecycleObserver.ps1 9、14–26、34–37；VerifyLifecycleEvidence.ps1 7–38 | C02 未锁存 pipe/target/attempt，也未核 C02 注入及恢复事件链；相同 receipt 首错及 raw 不足以证明恢复同 pipe/target。须真实对象 ReferenceEquals、明确首尝试与恢复顺序，不能由 Test 提供替代对象。 |
| PLFM-P03 | P2 / Test | LifecycleObserver.ps1 13–28 在 39–63 的 gate finally 之外；FixtureChild.py 49–50 | gate case 已启动时前置检查或 TestTrace 持续抛出，可始终到不了 release finally，benign child 只能等 gate。须对 callback/outer setup 首红路径安排 own gate 的真实释放责任，不 kill 原 child、不伪终态。 |

P01 是同步前置的真时序缺口，P02 是 oracle 证明力缺口，P03 是 Test 自有 gate 失败清理缺口；均只在源码层确认。前一修正 Owner 对同 pipe/target 的实际源锁存正确，不能把 P02 回写为该 Owner 已实际发生替换。新缺陷不授权测试运行或修改原期望，整改归原 Test，事件实现归原 Integration。

## 已有五例方法的真实支持与限制

FixtureChild.py 是完整独立 benign 程序：`write_all` 处理 partial write/no progress；small/gate 为各 8×4096 个 O/E 字节，high 为各 512×4096 字节，即每通道独立 2MiB。它在 gate mode 读取实际 raw.closefd，按所有权关闭 stdout/stderr 及 descriptor，再等待自身目录的 release 文件。源码确实请求关闭实际 OS 端而不是返回 EOF 标志；当前没有 Windows close 返回、真实 pipe/task 或运行输出证据。

Observer 只接受实际 Diagnostics.Process 和实际 Task，用强 context 锁存 Process/已经出现的 Task 引用；一旦 Task 已存在不得替换。C01/C02 例分别在未来原 getter try / channel setup try 的内部 throw once，而不是复制 RunOriginal。C01 明确只是受控 creation observation 边界异常，不能称 Windows StartTime 实际失败。C02 首次 stderr throw 要求已有 stdout Task 且还无 stderr Task。对应事件目前不存在，故这些是方法源码支持，不是已触发。

| Case | 原标准与源码机制 | 当前独立裁定 |
| --- | --- | --- |
| C01 | actual Start/drains 后 once-only creation boundary throw；原 inner=1、main child=0、32768B×2、无 downstream | 条件机制合理；须冻结真实内部 try 端口、observations/outer 接线后才能证明到达。PID/creation 未观测则保持 unknown。 |
| C02 | 真实 stdout task 已存在时首 stderr attachment throw；恢复同 pipe/target、已有 stdout task 不换 | 当前证据链不足，PLFM-P02 OPEN；首错保持 red、只缺 task 可同 pipe 再附着不等于 child retry。 |
| C03 | 真实并发双 drain，独立 2MiB O/E 原始字节、双 GetResult/EOF、自然 main=0、benign downstream 一次 | fixture 与 literal oracle 匹配；尚无真实大输出、pipe 吞吐或完整 outer 证据，不能以源码计数称通过。 |
| C04 | 原 Tasks 已成功且 child 仍活；同原 Stopwatch 跨 proposed 1s 后 gate release；实际 WaitForExit true/zero 仍 sticky reject | 需整改 PLFM-P01/P03；原 deadline 算法针对真实 clock 的方法意图成立，运行稳定性及端口来源未证。 |
| C05 | 同 gate/Task 路径在 proposed 1s 内 release、实际 Wait true、正常 downstream 一次 | 同 P01/P03；1s 标准未批准，初始化、GetResult、ready、trace/fsync、调度和 Wait 全计同原启动时钟，不能重置 clock 保绿。 |

Observer 的 GetResult 真失败会 throw；callback 的 IsRunning/HasExited 读取不是假 clock/result。Oracle 检查 sole main row、原 inner exit、natural-zero main、双 EOF、input_changes[]、真实 raw 的 size/SHA、outer no kill/retry 和 C04/C05 gate/true-wait/年龄。它没有把 Task completion 直接称 EOF。

现有这些 checks 仍不能替代所缺真实来源：C02 原 pipe/target/attempt、原 running clock 的首次引用、精确真实事件顺序、outer 原 Process/PID/creation/两 Task 与实际退出码/raw关联、正常 downstream 的实际 marker/body 和 child 终态都须在后继完整 runner/contract 中接上。对当前尚不存在的 consumer 不宣已实现，也不因 oracle 收到非空 JSON 就判目标实到。PLFM-P02 的证明缺口需先修。

## 1s 门、异常与自然生命周期

五标准的 1s 仅是未批准的小算法提案，不替换生产 acquisition22000/inspection900 秒。真实原 Owner 在 sole Start 前启 clock；Task/GetResult、metadata/Save、Wait/flush/cleanup 都处同一 clock。C05 不存在与 OS 调度和磁盘延迟无关的保证：源码无法预先证明 Python startup、所有前置观察与自然返回都在 1s 完成。当前更有 P01 的确定竞态；修复 handshake 不能靠重置时钟、降低“Tasks+child alive”门或 silent 放宽阈值。若 Test 要提出新标准，必须保原冻结标准并另行精确版本/独评/准入；本评审不批准 1s 或任意新数值。

C04 等待实际 clock 跨边界，C05 观察实际年龄；GetResult 若不能结束会同步阻塞，Test gate 释放不能仅依赖该同步调用之后的 finally 来承诺所有异常都有界。P03 要求的 own-gate 生命周期修复须包括对应 outer setup 首红分支。真实未知 process/drain 可保留，不可 kill、重开 Process、重试 faulted Task 或伪 EOF。原 corrected Owner 的持久不可观察保留仍是明确限制；五例不覆盖该无限保留分支。

## 完整原 Owner 与事件/映射缺项

Test 的 New Owner 为 16501B / `deb19c5d2dde425048bcfabc21542107970aeae5f6891a0f46c0a0c876c14b71`，完整240行已独立读。其 97–115 行负责原 channel 再附着，125–131 元数据，135–143 实际 Wait，145–160 实际 Task/GetResult，188–212 原持有/flush/disposal/Save；第214行在首错/sticky/缺EOF后禁止 downstream。old140行仍另为 `833c5ca6f2a1ebc224a2f172c7784556b73fe0f7358cef59066e40907cf65ff7`，不混版本。

目前两版本均无 Test 事件。SourceSeamsRequest 精确请求 before_creation_getter、before_pump_start、before_wait_for_exit、after_wait_for_exit、before_command_success；Integration 必须提供 exact frozen caller/try 边界、实际对象及布尔返回，不吞 callback error、不允许回传替代 Process/Task/clock/EOF。Test 的 clock/task 强关联和 trace 来源要消费实际 contract，不能据提案即认为存在。

FutureLaunchRequest 明确 runtime_approved=false、entry_ready=false、argv=null；只有参数模板，没有可执行 outer entry。whole-owner mapping 未发生、benign case Plans 未生成、尚无 event consumer 或真实 ExecutionRoundOne。新 Owner 的固定 task root/ToolMembership 指向 Integration 未材料化私有29工具，不能直接以 Test T26 runtime 替换冒通过。后继 Test 只可在评审后的完整文件根/tool 两项关联和完整真实 Test map 中接线，CheckPins/ToolMembership 必须保持完整且非空；禁止复制函数作影子控制流。

## 独立预期、输入与覆盖

ExpectedRaw 是字面预期，不是实际捕获：本轮以独立 .NET 字节与 SHA 计算复核10组，各 case stdout O / stderr E 的 size/hash 均相同于声明；未执行 FixtureChild。对应结果保存在 FixedInputFacts.json。作者准备 before/after 的49路径逐完整 path/size/SHA saved 值比较相同；这不等于重新访问其原 runtime 文件。

本轮核完整49 ordinary 和16 own source/metadata，另明确治理/正式件形成73个去重路径。InputBefore 身份基线建立于 edb847，晚于核心正文首次阅读；前面真实源输出 SHA 与该固定索引互相一致，不冒称全部73路径在首次阅读前即核完。InputAfter 只复核同73路径。999-member RuntimeReference 只读声明 JSON，两个 executable pins 也仅记录为原 Test 已声明身份，本 Review 未物理扫或启动；没有借 Integration29 私有环境。

49件中完整方法相关三源码、准备源码、五标准/方法/端口/请求、ExpectedRaw、新 Owner 均正文实读。旧/新13 families 完整 bytes/SHA 与停止索引匹配，并用前轮已完成的全差异/语义审读作源上下文；不把无改的历史装配源码重复标成本轮重新逐行评审。所有 source hash、声明和作者 matrix 都不算五例行为结果。

| 生命周期分支 | 五例覆盖意图 | 当前状态 |
| --- | --- | --- |
| controlled creation observation / 首 stderr setup exception | C01/C02 | 未执行；具体方法整改/端口缺件如上 |
| 大输出并发 capture、正常完整 raw | C03 | 未执行 |
| completed Tasks + alive child + Wait true 的 late/normal 边界 | C04/C05 | 未执行；P01/P03 与1s稳定性未解 |
| 实际单通道 faulted Task/部分 raw、持久缺 task/未知 terminal | 无 | 未覆盖，不称双 EOF或有界终止 |
| Save/flush/cleanup 迟到或失败、末 command save 跨期限 | 无当前例 | 未覆盖 |
| 正常 Save/实际末 sharing failure | 原四 case 是另版本/对象 | 旧有限结果保持，不能继承为新 Owner 当前全路径运行支持 |
| 22000/900s、真实 GET/archive/Inspector/安装/Owner/媒体 | 排除本方法 | 未运行，无资格授予 |

原四方法的语义是 SemanticNormal/FinalLock、MetadataNormal/FinalLock，依旧 full runner 第四 Save 原 sharing failure；不是这里的五例，也不覆盖 running-save/live-child/EOF。原19三次、31/105 NOT_READY、原绑定失败及共用20元仍原样保留；完整 R1后连续R2未验收。

## 正式交接

三 finding 均归原 Test；Integration 仅承担其未来 exact event source contract。当前方法不采用即可回滚，旧标准、原失败、已闭源码修复和所有额度不改。本 Review 未写测试/实现/标准/COMMANDS，未执行任何候选、归档、Python/Pydantic、OS fixture、SQL、network、费用或安装。

正式末核和输入身份见过程 InputAfter.json；末工具实际返回及全 reader release 不由本报告生成自己预签。FinalizerTerminal.json 保存已实际观察的封存工具终态，最终 metadata 工具实际 chunk/exit 在本人返回后另报。


末核：同73有限路径 bytes/SHA 无变化，changes=[]；49 ordinary全部匹配，10字面预期raw SHA复核一致。

| 独立 Finding | SHA-256 |
| --- | --- |
| PLFM-P01 | 1a36062d39f7509b0024e6c41944d1a5d620e4104ef489ab86fb7d7aab3ad04a |
| PLFM-P02 | a5ddbea7b6d01ee015e59d124e51c2a8fe3518f7c70976467a71c3d778d5b5b7 |
| PLFM-P03 | 720f511e26bd7e023b7eddd3afb4ac6422b58920830169549d5c8b9ac0f6ab79 |

