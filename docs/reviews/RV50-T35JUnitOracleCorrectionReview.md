# RV50 — T35 JUnit oracle 有限关闭评审

结论：RV47-P01 在固定源修订及单个纯 unittest/JUnit 机制范围 CLOSED。原 helper 没有改动；错误期望按实际 CPython/unittest 事件修正。没有发现本有限输入的新阻断。此结论不授业务、OS/native、RuntimeBinding、安装、ASR、精度或 Gate 资格。

## 固定身份与评审方式

过程根：G:/开发测试/Codex/VideoCreatorImplementation/Review/JUnitOracleCorrection-RV50。

只读取 T35JUnitOracleCorrection 普通副本和两份必要原 T34 失败文件。69 ordinary、4 formal、2治理文件、2原失败文件共77个路径全部匹配；327项字节、AST、事件链、XML和收据核对一致，输入前后0变化。没有读取或重新 hash 999运行时文件，没有执行被审 helper、Probe、Test、产品、数据库或模型。

| 文件 | SHA-256 |
|---|---|
| T35Handoff.md | a54625f7e622a49c35678684430b1d91f4cc4e036200e594f7fdd01f256a863a |
| T35Handoff.json | 19d67567e84aa97de72a36ae7d9dcbed17c4d1876975da0c58f7c9f2a36034ad |
| T35HandoffSnapshot.json | 0cf6a85590b3136a43a5d7f312265f9b82e1b0ec9204a288f1b30d45d9110a31 |
| T35OrdinaryManifest.json | 0839ce5bcefbf850e21e65f8b8e72baf497ff5ae42a9908e923f12b82a29a838 |
| ProbeMixedT35.py | e578344dae106c499a8fd56c1e2f9e3420854910345ac51be6ed7016cc3030c9 |
| T35SourceDiff.patch | c30852173560b3e95004884845872a316d9e5bc714cc8667447f664deee489a0 |
| FixedInputs/JournalJUnitT34.py | 9cd7c4f7c5246cfea9a76c6da5eaaa4a6d72088adb1350175b0a864a6e3f00b3 |
| FixedInputs/DurableDiagnosticsT32.py | 5619700b23d0c1190622eb9e0917bf318dfb0275faa6040699230f5bfd3738e7 |
| FixedInputs/OriginalProbeJUnitT34.py | f7db835d41c09061f4320760c890aff1389c42fff59e88c370b151512dcb2146 |

表中相对名统一位于 G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T35JUnitOracleCorrection/。完整绝对路径、size与前后身份见 RV50InputPins.json / RV50SourceAfter.json。

## RV47-P01 — P2 / Test：有限关闭

原缺陷是测试 oracle 把没有 case_success 的 SuccessSubSkip 期望为 success_with_skipped_subtests。T35 ProbeMixedT35.py:122–130 改为 failure_or_error_or_skip，并核实际事件恰为 case_started → case_skipped → case_stopped、没有 case_success、skip 的 parent/detail ID 和 reason 保留。131–134 同时验证普通 Success 的 start → success → stop 和 XML success，避免将正常成功统一降级。

135–142 核全部 skip 与真实 result.skipped、真实 suite_returned 计数。原 T34 失败点之后未达到的 error 文本和 partial=false 断言现位于143–144，实际单个测试成功结束及保存的 Generated.xml 支持它们已达到；不是只替换输出文案。九个其它 test 方法、七个 fixture 和 bind/setUp/nested/render AST 均未改。完整差异逐字等于保存 patch：除这项 oracle/加强断言，main 只换批准 index 和单个用例选择，helper 未改、阈值未改。

## 实际证据支持的范围

原工具 ff8de8 / session98125 → 41b60b 自然0，单个 mixed case 外层1测试、0失败、0错误、0跳过，实际 stderr 为 Ran 1 test in 2.207s / OK，外层 JUnit 仅1节点。ProbeMixedT35.py:222 明确 loadTestsFromName 单个方法，没有执行另外九项。外层 suite 名称保留历史 T34 标签，不能据此把这次1项写成原10项。

实际 nested suite 是6个自制测试，预期产生2 failure、2 error、3 skipped；这些真实负向结果被保留在6个 XML 节点中。21条 nested、4条 outer、3条 lifecycle journal 的序号、原字节 previous_sha256 链、PID、index 和单调时间一致。SuccessSubSkip 的第18–20条事件没有 success；普通 Success 的第1–3条有 success。outer 的 start/success/stop/suite_returned 支持单个 mixed oracle 成功；不能把 nested 的故意 failure/error 写成业务失败被修复。

原 held child PID33700 / creation134359974898924424，wrapper PID14560 / creation134359974886696115。保存的收据记录同一持有对象等待后实际 exit0、terminal=true、forced=false、lifecycle_errors=[]，没有本次重开进程。Driver 在 finally 等同一 Popen；wrapper 等同一 Process，先启动两输出 pump 再观察身份。这些是该自有机制进程的源/收据支持，不是产品 native 清理或 Job 资格。重定向文件关闭记录明确不是管道 EOF 证明。

SingleRoundOne/InputBefore.json 与 InputAfter.json 字节完全相同（SHA 8f425e56580a8d0ecde71ca1ec67a295fd0c5cc565036e5eab55b3b81f242bc4）。计数分别是1010记录、index展开3019路径、实际 observed 3020路径；不同计数口径不能写成漂移。自然0和无强制/无变证据均来自原收据，本评审没有重新验证运行时文件。

## 原失败与未测边界

原 T34 十项整体仍是10测试/1失败的 NOTPASS；原 XML（c9949cc66644f0b8257094e93791cfb89c2083153e2d4e614ec187551be4566d）和 stderr（f1cb4384724aef8a1e095267c69ee1ff1ebcdcf0f1d9d7456acd760e97658e13）保留。原其余九项有限机制结果不改，本次仅证明它们 AST 未变，不提供新执行证据。

RV44 后续生成器相关准备/机制覆盖必须继续分列原 T34 结果和本次单个修订结果；不能写成十项重跑全绿或全部生成器分支资格。业务68、真实业务结果生产、产品 profiler、真实 Owner/人类审核、完整 OS/native/H01 均未在本轮运行或获准。原 T30 两次失败及其未覆盖条件不变。完整 R1 三 OS 独立验收后连续 R2 的目标不缩小。

所有固定输入 reader 已结束；自有解析工具 c6ec11 自然0、无 live handle。最终文书写入完成后释放本阶段。复核补充与产品验证应另批，不等待未来实现。
