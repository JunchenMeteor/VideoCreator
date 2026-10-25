# RV79 — T54 两个 C01 precontact 变体独立有限评审

结论：**SUPPORTED_LIMITED_RUNTIME_C01_PRECONTACT**。固定 B37 上两个原对象的 known-precontact Python 故障窗口、强持有恢复和真实正常关闭获得有限支持，本片没有新 P1/P2。只支持 line463 执行前的两个变体，不支持其它 14 个未执行单元，不关闭全故障矩阵、未知受理、重复中断、句柄复用或双异常条件。

## 固定范围与身份

读取 `G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T54PrecontactExecution/` 的 49 个 ordinary 件，原 manifest 声明的大小/SHA 均匹配。加六正式身份、治理入口和三个必要 B37 历史源码/原快照，共 **62 records、58 唯一路径**；末核无变化。未读取 B40 热源或重新扫描/散列全部运行时资源。完整前后 pins、独立解析事实、读工具记录在 `G:/开发测试/Codex/VideoCreatorImplementation/Review/PrecontactExecution-RV79/`。

| 固定文件 | SHA-256 |
| --- | --- |
| T54ExecutionHandoff.md | d1b701c28767933c62713bad665e85fab387bb682aa495c0ec9e7bf78156d576 |
| T54ExecutionHandoff.json | 2daa1817f86986cb77976755f8908b2b6a15de4b25f5f0786685dffa53f5eba6 |
| T54ExecutionOrdinaryManifest.json | 6be0a36bed5b59193ae144f0b8a99908b0caa774454d808bab9c2cbd7205953e |
| T54CatalogReachMatrix.json | 4d04c6782ed6645b37f4d9a091cdd17b042574182d95dca02c646f9540f131f0 |
| T54StoredFullMapComparisonReceipt.json | 407c3326f0510c034f7040689c3a0a0b17c969e77127751a8d63b5531922a99f |
| T54ExecutionFinalToolTerminal.json | 034418497ba69e99b525458a42be1cd4be854f0ab10dde702671dde1571f869a |
| Source/PeerPrecontactT54.py | 6f6ffa9d981d013d5ab5dc47d4617b5897cf7a1dc6675af55dc6c72b9cd27b2a |
| Source/RunPrecontactT54.ps1 | 8918ce0e45296d36be9226a5532d943b8b9c325527a431a7b2ca288e3de91291 |
| 实际 B37 windows_authority_pipe.py | 491c1e0d3d8472b7dc87ab06740f5f3ec28e3f78509e97882cbe84c75946aecd |
| B37 SourceSnapshot.json | 0e58fcd24620e39f6f5d8f80f6868f0ecf65560a5e4954843a8ed72e4789a494 |

实际 source_root 是 B37/SourceCopies；三个必要源码与固定 B37 Snapshot 及 T54 Index 声明均一致。NativeReport 中旧“B31 factory”只作继承标签保留，不替代实际 B37 身份。

## 注入与原对象恢复的实到范围

B37 windows_authority_pipe.py:249–260 的 module dictionary 强持有原 owner/API/数值 HANDLE。450–479 中459创建 holder，463才设置 contacted=True，465才实际调用原 close。固定 Peer:169–200 精确匹配原文件 SHA、方法、目标角色与 **line463 的 line event**，还核注册表中同 holder、原 owner/API、false 标记及原 RLock 已持有后，抛出同一个预建异常。它不修改生产源码或用假的 OS 返回值；没有声称原 catalog 的字面 line460 已注入。

| 变体 | 目标原 HANDLE | 原 holder / owner ID | 故障角色 | 边界总调用 / 目标调用 |
| --- | --- | --- | --- | --- |
| Pipe | 760 | 2645870124336 / 2645870122992 | pipe primary | 0 / 0 |
| Process | 696 | 1243387046928 / 1243388107408 | process cleanup、无 primary | 1 / 0 |

两个 FaultReceipt 的原 traceback 均到实际 held_authority.py:288 → WindowsAuthorityPipe.close:488 或494 → `_close_retained_handle`:463 →原 trace 抛出；异常对象相同、cause=None。Peer:202–247 在解栈后核同一个强 holder/owner/HANDLE、注册表仍保存该对象，contacted/confirmed=false、error=None，原目标 GetHandleInformation BOOL=1/error=0，目标实际 CloseHandle 次数0。

Process 边界总次数1是另一 **pipe 764** 已正常关闭，不能扩大成全部 OS 接触0。Pipe 原主异常解栈时，finally 正常关闭另一 **process 764**。各 FaultReceipt 的 other_handle_calls 都等于最终 OS 日志第一条，目标原句柄仍保持有效；这是单线程原锁下两个明确 Python precontact 异常，不是任意异步 OS 受理故障。

Peer:248–269 通过**同一原连接、transport 与原 holder**继续已知未接触的目标关闭。B37 held_authority.py:139–167 创建原 RLock，284–288 在该锁内失效连接再关闭 transport；B37 close:450–479 找回原 holder，原 marker 后只接触一次并确认，随后清 None、删除记录。实际 RLock/连接身份检查支持本次窗口，不代替并发锁或所有中断安全验证。

## 真实关闭、原 raw 与终态

Peer:145–163 的 recorder 保存原 kernel.CloseHandle，传同一个原 HANDLE，记录原 BOOL/LastError，立即 GetHandleInformation 后恢复原 LastError并返回原 BOOL。关闭与无效查询之间没有另建 OS HANDLE；不合成系统调用结果。

- Pipe 变体 OS 顺序为 process764 → pipe760；Process 变体为 pipe764 → process696。各原 HANDLE 总计一次实际 CloseHandle，均 BOOL=1、last_error=0，随后的原 GetHandleInformation 均 BOOL=0/error=6。
- 两个 owner 字段最终 None，原 owner 的 retained I/O 与 close 注册表均为空。同一连接第二次 healthy close 的 OS 总次数仍是2；Peer finally 又经原 authority.close 后总数仍2、cleanup_errors=[]。这不构成未知数值 HANDLE 的盲重关。
- 两案 ParentStdout 原 JSON 均等于原 NativeReport，PythonStdout 原 JSON 均等于原 CaseReceipt及 native 内嵌 python_report；OsCalls.jsonl 均逐值等于 case 两条实际记录。原 JUnit **各1节点，共2 cases、0 failure/error/skip**；每案8 peer/3 outer是内层检查，不是22个测试。自有纯解析每案28项全部成立。

| 变体 | 原 guardian PID / FILETIME | 原 Python PID / FILETIME |
| --- | --- | --- |
| Pipe | 34152 / 134360520033822626 | 31452 / 134360520082305581 |
| Process | 26968 / 134360520276900702 | 37308 / 134360520324853131 |

两原 guardian 的 PID/creation 与连接内 server/parent 一致；CommandReceipt 和 NativeReport 支持 guardian及物理 Python 自然0、Job active zero、主子 stdout/stderr 双字节 EOF，forced=false、deadline_sticky=false、errors/observation_errors/inputchanges=[]。原 runner:69–95 持有原 Process 到退出并完成实际字节泵，不用后来进程消失代替原 exit。exec 未提供外层 pwsh wrapper creation，未补造该身份。

## 已存储的完整资源表与未测边界

这次两个 case 都保存 ActualFullMap.json 和 ExpectedFullMap.json；四件原字节均 **357656B / SHA45b71266492b3690e2f4ee33bb88494412fd324e861c480169843d09a2871180**。本评审重新解析这些固定正文，与未变 T54InputIndex.expected_files 按 relative_path 逐项核 **路径、大小、SHA、精确字段类型**，均为1333个唯一条目，实际/预期/独立表一致。复算 canonical 摘要 `6746da14608778f38409665ec8bf574c03673aa7ceb159f504c62d7572b053e8` 与两案原 FullMapReceipt/StoredFullMapComparisonReceipt 一致；不是只比条数或采信一个布尔值。

这些是原运行所存表的独立比较，没有发新 RPC、重新核当前实体资源或授安装许可。与 RV78 的实际表正文缺失限制分开：本次确有完整实际表，不回填旧 N01。

两个 **server_session_end=authority_io_failed** 原值保留，不能因资源正常释放/主子自然0洗成 graceful protocol 完成。qualification=not_ready、issuer=None、evidence_constructors=[]；没有实际 Owner、UI人审、完整 Worker/媒体/ASR、真实作品、安装或三 OS 资格。

Catalog 仅显示历史 N01 加两个 C01，共 **3/17 observed、14 NOT_EXECUTED**；T53没有重跑，RV78范围不扩大。marked unknown close、受理后未观察、close 返回后异常、重复中断、HANDLE复用、双异常、其余I/O与主机条件仍未测，不以本片关闭。

原 T54 主运行 `8e7004/session47413 → 90f776` 实际自然0，固定终态证据的 finalizer `18eb73` 自然0；任务卡另记录 last hash `68d43f/0`，不拿它替代运行证据。评审的并行源码输出曾截断，随后只补 Peer270–312/runner1–22；该呈现限制及原工具保留，不当产品失败或再运行。完整 R1 三 OS 真实作品多模态独立验收后连续 R2 总目标不缩。

评审仅固定字节/源码/JSON/XML/stdlib解析，产品、Test、DB、native/OS故障、网络、凭证和费用调用0；原读者已释放，正式末工具终态后结束本轮。
