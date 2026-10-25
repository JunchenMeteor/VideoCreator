# Piper 双入口四项真实收据机制独立评审

结论：`LIMITED_COMPONENT_MECHANISMS_SUPPORTED`。固定四项原结果与完整原方法、磁盘收据、checkpoint、raw 字节和两层进程记录相互支持；没有新的已确认 P1/P2。两个正常项原入口自然退出 0，两个末保存共享锁故障原入口自然退出 1；外层匹配预期的汇总退出 0，不能用该 0 覆盖故障入口的 1。只支持本版本两个入口的正常末保存及“子进程已终态后最后一次保存发生首个真实 I/O 异常”的组件窗口，不是原全部故障分支、业务数据或资格通过。

PDM-P01 先前仅源码关闭的末保存机制，在以下四个固定候选及实际条件下有有限组件运行支持。运行中保存、required batch 消失、stderr transport 故障仍 OPEN/NOT_RUN；不将整个 PDM 安全范围、历史其他失败或后继 117 输入材料对象一并关闭或授权。

## 固定版本与有限输入

任务卡：`G:/开发测试/Projects/VideoCreator/docs/task-board/PiperDualEntryReceiptFaultResultsIndependentReview.md`，SHA-256 `2c4583ec40325b6b8fbcc71e644afe1ea9fd69ba24953ea59334db908ae9b393`。

正式根：`G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/PiperDualEntryReceiptFaultActualValidation/`。普通根为同根 `ReviewHandoff/Ordinary/`，按正式 OrdinaryIndex.records 的 source→ordinary_copy 读取，没有扫描环境或读热源。

| 正式输入 | SHA-256 |
| --- | --- |
| ExecutionHandoff.md | a47a3334bf728cb3532c48d35994dd8e316853632b679c947ba85f6dd3a9f46e |
| ExecutionHandoff.json | c78e5701a48301e1cf3dd0374a3dfe756eb32fdfb8f63061421d9527162896fb |
| ReviewHandoff/OrdinaryIndex.json | ac94aebe8bcd2fbf223d1f09e095c0b494ccfb533101968488c241be566f79e2 |
| ActualCaseEvidence.json | 25ecf12c2e2d2993ccbd8274aa200f7b07caad4cc05b9391294c145a75949835 |
| MainToolTerminal.json | 9e94cbdcaeb89b2119b2ef2b89495f751f67832e6fec2ced93e1002b4db2d515 |
| 原 BatchResult.json，普通 Input035 | d6d958dc040fce4e44ae3ea88843c1fa2fb2d1789a1cf5eaa688a46235951171 |
| 原 InputAfter.json，普通 Input036 | e026c685cde653221aa33078eec5dac458d986e79ad9851b2b01c2f0d2059b83 |
| FaultInputIndex.json，普通 Input059 | c458b3201f125345ab19931cae58350dd815e1441befbdd11b31a79989c75fdb |
| FaultLaunchRequest.json，普通 Input060 | 10d16c8896b23f388bd2cd58bd1f7ffa153a921cc16d728336d4020f1859610f |

本次 InputBefore 固定 75 有限路径：67 ordinary、正式索引/交接/本卡及必要治理/前序独评。两份由 Handoff 精确指出的 ActualCaseEvidence/MainToolTerminal 另存 InputSupplement；有限 InputAfter 共 77，大小/SHA differences=[]。普通 67 逐件与索引一致。InputAfter SHA `06f6d98539c6a5ebd5025c72b71c9fb6333d3c627d4561307f49cfceec271e62`。这些是本读窗观察，不回填之前准备卡的治理漂移。

原方法独评 `G:/开发测试/Projects/VideoCreator/docs/reviews/PiperDualEntryReceiptFaultPreparation-IndependentReview.md` SHA `76f0479e81e5392ab61340b3886aeab3785c54019d7c2141b9d72c45413c96bc`、原 FinalHandoff `d6af4336c8d892b6c8262a71f85cabb7d90f55c0371769463f9463b81b6cbfe1` 保留。该旧报告的 NOT_EXECUTED 是其当时范围，本报告另审新实际证据，不覆盖历史。

## 四项原结果与身份

| Case | 原 whole-runner SHA-256 | Host PID / 原 exit | Child PID / exit | 末收据 |
| --- | --- | --- | --- | --- |
| SemanticNormal | a0a4d5cee28b3d82094cd7dd630611f088f7ac9e6987b747dca236e9520de49b | 31500 / 0 | 34944 / 0 | 14230B，完整末 Owner 相等 |
| SemanticFinalLock | 4be7be3ef4cf08f909518c0ad949abe0e1877475d3b6cdfaabefec23351f845d | 10000 / 1 | 40356 / 0 | 7644B，原 stale 字节保留 |
| MetadataNormal | 94c5ee84c6370dfef7e268f46141efff4cca665cd51dccd557e652e0004b4ef3 | 10020 / 0 | 29336 / 0 | 14157B，完整末 Owner 相等 |
| MetadataFinalLock | 8b28446a48fdd4f35d0938154059df1044118f9fd59343fd3b262c9739454412 | 28380 / 1 | 38860 / 0 | 7646B，原 stale 字节保留 |

四项各为原 `EXPECTED_MECHANISM_OBSERVED`，没有 UNEXPECTED_RED/NOT_EXECUTED/skip；BatchResult 与 PartialResults 的四项完整对象结构相等。冻结入口未生成 JUnit，本报告不制造 XML 或把机制汇总称为归档/HTTP 测试套件。

Host creation UTC 顺序为 `2026-10-11T04:03:00.2899706Z`、`04:03:01.7428806Z`、`04:03:02.9547821Z`、`04:03:04.5157251Z`；Child creation 分别 `2026-10-11T04:03:01.178948Z`、`04:03:02.5454825Z`、`04:03:03.7609347Z`、`04:03:05.3389867Z`。原四 Host LaunchReceipt 与末 CommandReceipt 的 PID/creation/executable/完整 argv/cwd 相等；末记录均 natural_terminal=true、stdout_byte_eof=true、stderr_byte_eof=true、timeout_sticky=false、errors=[]、ended_at 非空。四 Child 的完整 argv/cwd/PID/creation/exit/EOF/errors 在末 checkpoint、BatchResult、正式投影之间相等，并在锁前已终态。

Host 的 executable 是原 Index 固定 `C:\Program Files\PowerShell\7\pwsh.exe`；argv 精确是 NoProfile/NonInteractive/File/原 Host/CasePath/Case SHA。Semantic child 使用原 portable Python `-I -S -B -X utf8` 与该 case 的完整 fixture 路径及 Plan SHA；Metadata child 使用原 pwsh 与完整 fixture/PlanPath/Plan SHA。实际字符串完整保存于自身 RuntimeArtifactFacts.json，没有以显示 command 字符串替代真实 ArgumentList，也没有给 exe/hash 资格含义。

## 原方法到真实输出的核验

所有下述 Input 文件绝对根均为 `G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/PiperDualEntryReceiptFaultActualValidation/ReviewHandoff/Ordinary/`。

1. 完整 Input064-ReceiptFaultHost.ps1，SHA `c6ff8dd76d7867ae3ef5aad377ad22f038dcf17a98990b249a522e1696bbe99a`，第 20–36 行要求原 Owner/ReceiptRequired、核 whole runner SHA、捕获原 Get-PSCallStack 并读取真实上一收据。四项各四实际栈命中：Semantic 81/44/68/97；Metadata 88/42/75/98。第 63–64 行 command breakpoint 后实际调用完整 runner，未替换 SaveOwner 或原返回值。
2. 对每项 checkpoint 2–4，独立比较实际 prior_receipt 与前一个 owner_before 的完整 JSON 结构，12 项均相等，不只接受正式投影的 true。四项每个 observed Owner.errors/input_changes 均空；每个 Owner.inputs_before 的原 23 条 path/size/SHA 与该 Plan.inputs 按序相等，末次 before/after 亦完整相等。case 本身 24 条准备输入和原接口闭包保持旧版本。
3. Host 第 38–48 行在末次调用前核唯一 child 已自然退出且双 EOF；仅 FinalLock 第 44 行对实际 case CommandReceipt.json 持有 FileMode.Open/ReadWrite/FileShare.None FileStream。实际 checkpoint 的锁只出现在 ordinal4，lock_target 命中原收据路径。第 66–69 行退出后才释放本锁/breakpoint。不是凭异常名伪造故障，也不是随机睡眠竞争。
4. Input029-RunSemanticInspectionRevisionTwoRoundOne.ps1 全文与 Input021 故障版，仅逆换固定 case task-root 后相等；Input018-RunTransitiveMetadataRoundOne.ps1 与 Input010 故障版同样相等。两个原 SaveOwner 分别第 12–22/10–20 行执行真实 WriteAllText，catch 留 ReceiptWrite/type、actual_exit=1/FAILED_FIRST_ERROR_PRESERVED、真实 stderr；原最后调用在第 97/98 行，随后第 99/100 行再次保错误非零，最后 exit 原 Owner.actual_exit。既有前序方法独评已证明四版本逆换原根恢复原完整入口 SHA；本批运行输入使用同四 SHA。
5. 两 Normal 的真实磁盘最终收据完整结构等于末次 owner_before，state/ended_at/child/fixedinputs 同时成立；host stdout 含 actual_exit=0、host stderr 是 0B。Semantic final SHA `6f0a740dc578c363521a662b8032ed519dce6e6248293227e5af6bc131bb72b1`；Metadata final SHA `cf2d8def0c772520484629dbee2e4e90dd17bcd53d3d46ff770e88200336bd61`。
6. 两 FinalLock 的真实磁盘收据完整结构等于末次 prior_receipt，size/SHA 与先前捕获值相等。Semantic stale SHA `4537299e9b27ab1a586aa397098d163e209b1e2082c9462adcda0fb0eab9374b`；Metadata stale SHA `c45848bcfe61236abb73d5da74a79661b74048013c64849d9827eecfb8c78be1`。它们是子进程结束后、原外层最终处理前的旧 checkpoint：ended_at=null、inputs_after 仍空、actual_exit 仍原默认 1，不能算“已保存最终失败收据”或“最终成功收据”。不要求被锁文件魔术更新成失败状态，不另写 fallback 掩盖。
7. 故障原 stdout 含 FAILED_FIRST_ERROR_PRESERVED 与 actual_exit=1；原 stderr 保留 ASCII `ReceiptWrite:MethodInvocationException:` 及 `The process cannot access the file` / `because it is being used by another process.`。这是 CLR 调用包装异常的原诊断与实际共享锁源码/路径/旧字节的相干支持，不虚构未捕获 HRESULT 或更细内部异常字段。
8. Input066-RunReceiptFaults.ps1，SHA `2d72d9cd7ef7995259f03be275bf8c0e20feb68daa3bc5d05dcd32f7d4b5beb3`，第 41–79 行从 Start 持同原 Process，finally 同 handle 等待、原 byte pump 完成后记录 EOF，120 秒只 sticky，无 kill/restart；第 82–114 行检验完整前序收据、实际原 child/原 raw marker、正常或锁定两类不同 oracle；第 117–128 行首不符就停，并让输入末核及 BatchErrors 参与汇总 exit。本次原所有四 Host/Child 无 sticky/error，只支持实际已走窗口，不证明未触发的等待/transport 异常分支。

四组 child stdout/stderr 是原捕获的 benign marker 字节：Semantic 各 30B，SHA `0817f46a958140528451b275f421c0dab068d897fc6b92e8a5153f713dfee9f5` / `c9d92cf111219b17f90d8bd9ce38ed33cd03caea690247daf89bacda973e8dec`；Metadata 各 31B，SHA `3a99e7537bdfff5427568326ad3b6d8870ebc507ea15141bb8d9b34e54198823` / `4576587929baf428aefe813db7f6c51cc68d96c6ed81389a0252cc111324f667`。PS child 的 CRLF raw 与 Python child 的 LF raw 均保原二进制，不转换。

完整固定 fixture Input062/063 全文独核：MetadataReceipt 的十条及 http_attempts 仅满足原字段形状，actual_HTTP_requests=0；InspectionReceipt 六个字段明确 not_an_archive_result，archive_inspections=0/parser_operations=0/qualification=false。这是透明替代业务 child 的 mechanism fixture，不是原业务 helper/parser 的真实进口或归档/网络数据。

## 输入与证据等级限制

原 Index.records、LaunchRequest.read_closure、实际 InputBefore.records 共 1059 项，独立逐条既存 path/size/SHA 按顺序对照残差 0；它们的 path 身份使用 Windows GetFullPath 进行源/副本定位，完整实际 argv 字符串仍原样保留。原 InputAfter 的 changes/errors 空、external_index_baseline_sha256=c458…；ActualCaseEvidence 与 Handoff 四个投影完整结构相等，16 个正式 receipt/checkpoint/raw pin 与实际普通字节一致。这些不是作者计数相等替代逐值核验。

999 运行时文件是原声明及原 before/after 检查记录，不重新遍历、复制或实测所有加载。原 1059 外部 Index 不包含本次新的117材料对象；此报告不赋该对象执行权限。LaunchRequest 历史 runtime_approved=false、source_only_not_execution_ready 字段未改，实际本次 Root 单次准入属于另有治理事实，不把旧 JSON 回填 true。

最外层 MainToolTerminal 记录初始28a424/session70334→原作者616c8c actual0/no restart；默认只读 launcher b9c652/1 未启动 runner。该层没有独立原 Process PID/creation、两路 byte pump/raw EOF 收据。四 Host/Child 的真实 EOF 不能向上继承，也不能用 Root/tool exit0补造最外层观察。保持该缺证据，未为凑闭合额外运行。

两故障 Host stderr：Semantic 368B，SHA `f50b27105d70565685d6cf7d0f83d8471b60c3d09d8aa929f3dba5149447a056`；Metadata 347B，SHA `f9420f9f71601befde6b3fa52ac22b1eae58b8c1e166cc2639c25f3f027297f8`。独立严格 UTF8 decoder 对两份拒绝；原 encoding 未捕获，不能宣称 GBK/具体 code page，不能将含 replacement 的 UTF8投影称完整原中文诊断。自身只用保原 byte/SHA及可见 ASCII 区间支持上述有限 I/O 文字；非 ASCII 的问号是分析投影，不是原字节改写。

未测仍包括 running-save/live-child、required-batch disappearance、stderr transport failure；真实六归档/十 URLs、后继117绑定 runner、全部 parser/业务、Owner/API/MCP/native/安装/模型/收费与真实视频质量均不因本批通过。旧 literal12差异、准备失败、原19三次与20元预算保持，完整 R1 三OS真实作品和连续完整R2没有独立通过证据。

## 自身工具记录与停止交接

自行元数据定位45f7c8/1（缺数组索引）、34f546/0（错字段导致 null）原记录保留；e98954/1 仅自有静态分析脚本 catch 语法 ParserError，失败脚本原文留 InspectExistingArtifacts-InitialParserFailure.ps1。修正该 Review-only 脚本后5dfeaf自然0，四原artifact对照 problems=[]，未执行任何目标代码。e01d54、b00156输出截断保；后续只补必要字段/既存记录比较，不假称大型 console全文已读，不重跑Test。前序 methodReview中的 Root 活卡追加、原自身错误及全部原 Test 红亦不覆盖。

过程：`G:/开发测试/Codex/VideoCreatorImplementation/Review/PiperDualEntryReceiptFaultResultsIndependentReview/`。RuntimeArtifactFacts.json 保存完整两层身份/实际callstack/逐比结果/raw pins，FormalMetadataChecks.json 保存正式pin/decoded launch关联，ToolHistory.json 记录原自身失败。末读窗29d642自然0；77有限InputAfter cd3ad3自然0、differences=[]。全部源 reader 已释放，无live handle；后续只生成本报告/正式交接及其自然返回事实。没有源码/测试/标准/原证据修改，也没有新运行授权。
