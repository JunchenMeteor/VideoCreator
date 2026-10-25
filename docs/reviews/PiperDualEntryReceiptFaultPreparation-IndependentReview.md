# Piper 双入口收据故障准备独立评审

结论：`SOURCE_STANDARD_SUPPORTED_ONLY`。本固定四个候选包未发现新的已确认 P1/P2；源码及拟定 oracle 可以支持“两个正常末保存应返回 0、两个末保存真实共享锁异常应返回 1”的有限准备范围。四项仍为 `NOT_EXECUTED`，本报告不授运行，也不将之前 PDM-P01 的源码关闭提升为实际故障关闭。

## 固定范围和身份

只读 TestDevelopment/PiperDualEntryReceiptFaultTestPreparation 的正式交接、54 ordinary、四个完整 Case/Plan/runner、完整 observer/oracle、两个原入口、完整来源映射和差异。全部绝对路径及 SHA 保存在本过程 `InputBefore.json`/`InputAfter.json`，不是从作者布尔摘要推导。过程目录：

`G:/开发测试/Codex/VideoCreatorImplementation/Review/PiperDualEntryReceiptFaultPreparationIndependentReview/`

正式输入根：`G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/PiperDualEntryReceiptFaultTestPreparation/`。

| 输入 | SHA-256 |
| --- | --- |
| FaultPreparationHandoff.md | c0b121495dd6e805b861a0ad62bb95e60d6ec430170f379fcc57a8eb6211f107 |
| FaultPreparationHandoff.json | 7a5976117ca6dbc87b1162ae25261a147c535a721f99d4b1c549190b9d52bdd7 |
| ActualInterfaces.md | 6b18481d8bad15de0d794fac6dc266da74d0e7416ffaaead6eb7a0e69d0503c4 |
| FaultInputIndex.json | c458b3201f125345ab19931cae58350dd815e1441befbdd11b31a79989c75fdb |
| FaultLaunchRequest.json | 10d16c8896b23f388bd2cd58bd1f7ffa153a921cc16d728336d4020f1859610f |
| SourceStage/OrdinaryIndex.json | 39c8da245720a389270f337f0b8fc1b61fafee0da902f3657d0d8c68866c0539 |
| Input014-ReceiptFaultHost.ps1 | c6ff8dd76d7867ae3ef5aad377ad22f038dcf17a98990b249a522e1696bbe99a |
| Input016-RunReceiptFaults.ps1 | 2d72d9cd7ef7995259f03be275bf8c0e20feb68daa3bc5d05dcd32f7d4b5beb3 |
| Input008-FullSourceDiff.diff | ae71e19df5c4ee0d74ee2deee23f38fb42e06a1e50206da0f7259d2c811d02b6 |
| Input009-OracleAlignmentFullDiff.diff | 50888e874e4c093bdf998558c06691833acd2692a7f834d08c0be6c89aa83d9e |

上表 Input 文件全部位于该正式根的 `SourceStage/Ordinary/`。原语义入口完整 SHA `441ae75d2836031509f92dcf89cba8a68f5490c6dc43ec95529bb98aa51d1ba0`，原 metadata 入口完整 SHA `1f48addc0b2608e6d98c9ec10cd5e4d3c30f596a6df4bbd5a31f53f17fd87c37`。每个新 runner 全文仅逆替换本 Case 根路径后恢复原 SHA；没有抽取被测函数或生成影子 SaveOwner。

| Case | 新 runner SHA-256 | 拟定原入口 exit | 实际状态 |
| --- | --- | --- | --- |
| SemanticNormal | a0a4d5cee28b3d82094cd7dd630611f088f7ac9e6987b747dca236e9520de49b | 0 | NOT_EXECUTED |
| SemanticFinalLock | 4be7be3ef4cf08f909518c0ad949abe0e1877475d3b6cdfaabefec23351f845d | 1 | NOT_EXECUTED |
| MetadataNormal | 94c5ee84c6370dfef7e268f46141efff4cca665cd51dccd557e652e0004b4ef3 | 0 | NOT_EXECUTED |
| MetadataFinalLock | 8b28446a48fdd4f35d0938154059df1044118f9fd59343fd3b262c9739454412 | 1 | NOT_EXECUTED |

四 Case 各 24 完整输入，Plan 各 23 输入；逐 path/size/SHA 关联到 future index 均一致。完整 diff 含实际完整 before/after 文本，oracle 差异亦含两个真实全文。结果见 `SourceComparisonCorrection.json`，不是 len 相等证明。

## 实际源码方法链和 oracle

1. Host 普通副本 Input014 第 5–15 行在任何观察目录写入前核绝对物理路径、父目录 reparse、Case SHA 和全部 Case 输入；输出目录必须不存在。第 20–29 行要求真实 Owner/child/ReceiptRequired、再次核原完整 runner SHA，并用实际 call stack 的脚本路径和原 SaveOwner 行号关联。语义入口四 callsites 是 81/44/68/97，metadata 是 88/42/75/98。无法取得 scope/callsite 时拒绝，不能产生被测行为已观察的假阳性。
2. Host 第 30–38 行只捕获观察快照和之前实际收据字节；末调用前要求原 Owner exit 0、无旧错误、唯一原 child 已自然终态/双 EOF/未触 sticky。第 42–48 行仅 FinalLock 对原 batch 的 CommandReceipt.json 持有实际 FileStream、FileShare.None；Normal 不注入。第 63–71 行在原完整 script 的 SaveOwner command breakpoint 建立观察，随后调用原入口；finally 只释放本观察器的锁和 breakpoint，不替原入口写成功收据或改变 Owner。
3. 两个原完整 runner 的 SaveOwner 分别在语义第 12–22 行、metadata 第 10–20 行对真实 CommandReceipt.json 写入；异常记录实际 type/message、ReceiptWrite、actual_exit=1 和 FAILED_FIRST_ERROR_PRESERVED。原 finally 的最后保存分别第 97/98 行；异常不能被最后状态或返回码洗成 0。原异常收据、实际 stderr、先前成功收据残留是不同证据。
4. 外层 Input016 第 43–79 行持原 Process 对象，记录启动 argv/cwd/PID/creation，保双 raw pump；120 秒等待是 sticky 观察门，无 kill/restart。若进入 finally 仍未终态，续同一原 handle 观察；不能把 checkpoint 当成重新执行。实际 Raw EOF 仅在 pump 成功结束后记录，启动/flush/receipt save 的错误都参与非零结果。
5. 外层第 82–114 行同时检验原 exit、自然终态/双 EOF、四实际 checkpoint、完整 prior receipt 与上一 Owner 观察对象相等、原 benign child stdout/stderr marker。Normal 要求原成功终态且无 ReceiptWrite；FinalLock 要求锁命中原收据路径、末收据字节 size/SHA 与前一版本一致、真实 stderr 含实际 ReceiptWrite/type/message、原 stdout 呈现失败且原 exit 1。没有只凭一个作者 bool 判 PASS。
6. 第 117–128 行首不符合预期就停止余下 case；原 partial result、BatchErrors 和输入末核参与实际外层 exit。把内层故障的预期 exit 1 与外层检验成功分开，不吞原错误。

两个 benign child 为完整自有 stdlib/PowerShell 脚本，只在本 case 自有 batch 输出拟定结果与双 raw marker。metadata 的 `http_attempts` 是原 runner 所需字段，fixture 明确 `actual_HTTP_requests=0`；语义 fixture 明确 `archive_inspections=0`/parser=0/qualification=false。这四项检查原入口收据与生命周期机制，不能被称为真正六归档、十 URL、parser 或业务成功。原 parser/helper/URL cap、900 秒原入口预算等原源码保护完整保留，但这里不执行其业务路径。

## 仍未证明的边界

- PowerShell breakpoint 在真实 script/action scope 内取得原对象、实际 call stack 行号、实际 Windows FileShare.None 故障是否按该四标准被观察，均 NOT_RUN。未来若不符要保真实 setup/runner失败，不靠改标准产生绿。
- 原 child 启动、两层原 handle 自然终态、原 PID/creation/raw EOF 和真实最终 I/O 错误仍无本批运行证据。source 条件不是 OS 行为实测。
- running-save、required-directory-absence、stderr transport 额外故障 proposals 仍 NOT_READY，不能并入本四项结论。
- 原 999 runtime records 只是既有完整声明；本次不重扫其树。只核 122 有限唯一物理输入和 54 ordinary，后者 hash/size 一致；全部 1059 future entries 关联中含 999 声明与 60 有限记录。future LaunchRequest 仍 runtime_approved=false，绝不由本报告变更。
- 保留旧 literal 12 差异、准备失败、原 19 三次边界/20元与历史结果；本评审不执行任何目标，不能重置原次数或资格。R1 后连续完整 R2、Owner/API/MCP/native/media/三 OS 安装与作品验收均未因此成立。

## 输入变化和评审自身原错误

初读任务卡 SHA 为 `d0eda5bf4bf0ad659924545423391453373df16fbfd68aa6e3a9e8d1b775f84b`。Root 08b5a8 在活跃窗口追加定位段，当前 SHA 为 `b773ef483fe0a941b40905b7eaf5279d299423c2647eb2dac9e0461f575678eb`。独立去掉追加段后的字节恢复原 SHA，原/新卡和完整追加文本记录于 `TaskOriginalRead.md`、`TaskCurrentLocator.md`、`InputSupplement.json`。这是 Root 输入管理变化，不是产品失败，不能宣称历史全无漂移。追加段不改范围/标准；后续有限 122 输入窗口末核 differences=0，InputAfter SHA `72a443a6a49c248bef70042472dbe7ded1192ecd27b5bc6a889241de99f424f1`。

评审自己的 bc7f72/1 比较错误使用 PowerShell 自动变量 `$input`，pipeline 中对象被遮蔽，导致虚假 closure 红；原 `SourceComparison.json` 和 `SourceComparisonOriginalFailure.json` 保留。da1e8f/1 随后把 plan 对象当路径，60735d/0 核准 plan.path；305bef/0 使用独立 casePin/planPin 标量比较后，四项每项 24/23 关联 errors=0。纠正文件 SHA `b5671c6752ff3e0daad92bbb1f487a0a0c96c3c0effdca98772d43e375809f6b`。629128/1 是旧 rg 入口定位错误；输出截断均保留，只对确实漏段补读或做有限投影，不假称巨大 LaunchRequest 全文字段输出已读。以上都不是目标测试失败，不改候选/期望/旧证据。

末固定源读取工具 3bec15 自然 exit 0，122 有限输入 differences=0；所有原工具已自然返回、无 live session。随后仅写自身报告/交接，不再持目标源 reader。没有实现修改、候选运行或运行授权。
