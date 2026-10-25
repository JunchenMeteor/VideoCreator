# PinnedLicenseExecutor 生命周期修正独立源码复审

本轮在固定新源码中将 **PLEE-P01、PLEE-P02 分别裁定为 CLOSED_SOURCE_STATIC_ONLY**，归属 Integration。没有新确认的 P1/P2。旧报告及两张 OPEN finding 原件保持不变；此结论只适用于下列新版本，不证明真实 OS 故障、实际取证、工具材料化、安装或产品验收通过。

当前任务卡 SHA-256 为 `831375baab76f62ef82ff870264a9dfc683eda157b42d9fa62cce372cb65e238`。正式候选根为 `G:/开发测试/Codex/VideoCreatorImplementation/Integration/PinnedLicenseExecutorLifecycleCorrection/`；评审读取 SourceStage/SourceCopies、BaselineSources、正式索引与证据，没有执行 CandidateSources。自有过程根为 `G:/开发测试/Codex/VideoCreatorImplementation/Review/PinnedLicenseExecutorLifecycleCorrectionIndependentReview/`。

## 独立来源与完整差异

SourceStage/SourceIndex.json 的实际身份为 13989B、`2bcaa1bf97eded452cbc95814f571c64b0399fc127e0400f7508b03764aa2cc1`。Full.diff 为 255769B、4856 行、`2bd0eb2136308e3d51d46c49949edc1e40b19ff17c7c77882206cb187914e7d6`。评审按每个 hunk 的旧正文、上下文、位置、计数和完整尾部，从真实旧普通字节重建六个新文件，再逐完整文件核对实际新字节；所有重建结果相同。没有使用作者的 inverse 声明作为证明。六段依次为 Acquire、Commit Plan、Inspector、Loader、Owner、Wheel Plan；另外七件与真实原件逐字节相同。

Owner 新旧完整正文、Acquire 完整正文、Inspector 全部 692 行均已独立阅读。两个完整 Plan 及 Loader 由完整 JSON 值比较和字面投影复核；对象键顺序不影响比较，数组顺序、类型、absence/null 和全部叶值保留。核实新源码 pin 后只逆还明确的候选根迁移、相应源码身份和新增生命周期说明：Wheel 590、Commit 519、Loader 268 个原叶值没有未解释残差，两个 Plan 嵌入的完整 Loader 与新 Loader 相同。七件未变的历史装配/收据源在完整字节相等基础上继承前轮语义审读；不称为本轮重新逐行审读，也不把其历史装配成功算作当前 future 入口执行。

独立证据见过程目录的 DiffReconstruction.json、PlanAndProtectionComparison.json、PlanLiteralSupplement.json。PlanAndProtectionComparison 的 added_provenance 是为了对比而进行根逆还后的投影，不代表 actual new_source_root；PlanLiteralSupplement.embedded_loader_proof.actual_provenance 保存实际新根。正式未来命令与下面的新源身份来自原始声明，未据投影改写。

## PLEE-P01：原 Process 与双字节流的持有

新 `SourceStage/SourceCopies/RunPinnedLicenseEvidence.ps1` 为 16501B，SHA-256 `deb19c5d2dde425048bcfabc21542107970aeae5f6891a0f46c0a0c876c14b71`。旧 Owner 的 PID/creation 访问先于两个 pump；异常可能令真实已启动 child 缺少 drain，finally 仍走到释放。新版本对这一实际控制流作了修正：

- 第 75–78 行为 stdout、stderr 分别强持有原 pipe、原 target、原 task 和完成状态；第 97–115 行只为缺失 task 接同一原 pipe，不替换已有 task，不从 faulted task 重新复制。
- 第 116–169 行在 PID/creation 访问前先接两个独立 drain；第 125–131 行元数据只在实际 task 都已建立后观察，各 getter 的异常只记录首错误，不绕过后续原对象生命周期观察。
- 第 135–166 行继续观察同一原 Process。真实任务完成后，第 150 行读取该任务结果；成功才记 EOF，任务失败明确保留 NOT_EOF 和部分 raw。null task、未知 process terminal 不是 EOF。
- 第 178–185 行仅一个原 Process、一次 Start。第 188–192 行接续原对象；第 202–204 行只有未启动，或真实 terminal 且两个实际任务都完成，才释放原资源。未调用 kill、替代 child、第二次 Start 或重试 faulted drain。
- 第 214 行和外层第 228 行把首异常、未知退出码、缺 EOF 或超时记为拒绝，不能因稍后自然 exit 0 抹掉早先故障或进入下游。

因此旧 P01 在此版本的来源级条件关闭。这里的“完成”不是伪造双 EOF：faulted 实际 task 可以真实完成且仍 NOT_EOF，命令保持失败。若 pipe/task/terminal 持久不可观察，代码选择继续持有原资源；不承诺任何错误下都能有界自然结束。此边界必须在后继真实故障测试中如实观察，不能靠提前 Dispose 或伪 EOF 换取成功。

## PLEE-P02：同一时钟、成功路径和永久失败

同一新 Owner 第 181 行在 sole Start 前启动 Stopwatch，第 182 行唯一 Start。第 83–90 行将超过原精确 22000/900 秒上限记为永久 sticky 状态；它不是清零后可恢复的计时器。

第 97–115 行 drain 接线、PID/creation getter、第 135–136 行包括返回 true 的 WaitForExit、任务结果观察、SaveObservation、flush/cleanup，均接同一启动时钟。第 208–212 行在末命令行保存后再次检查，若此时刚越界则保存红状态；clock 停止前仍检查。第 214 行和外层第 228 行不接受 sticky 命令，即使 child 本身 exit 0。外层最终 CommandReceipt 保存第 237 行异常直接传播，不被转成 outer success。

这关闭旧 P02 中“成功 wait/task 路径绕过期限”和“时钟太晚启动”的源码条件。同步阻塞的 getter、保存、flush 或调用不能由事后检查抢占；返回后会成为 sticky 红，不保证在期限点即时中断。没有在本评审执行睡眠、child 或文件系统故障来验证这一点。

## 原安全门与两 future 入口

Acquire 的唯一实质文本差别是固定候选根。完整函数保持正式 HTTPS 闭集、一次请求、正常 TLS、禁自动跳转/代理/凭据/cookie/预认证、原超时与 exact cap、边界多读一字节拒绝、CreateNew/no overwrite、完整 archive size/SHA 和先红后续不启动。六个 wheel URL 与四个 commit URL 的原字段未放宽；旧 FlatBuffers 只作为独立 preflight 后的只读重用声明，新增 GET 为零。本评审未读取或解释 wheel/archive 实体。

Inspector 完整源码逆还根后与旧完整正文一致。有限 stdlib 全文件身份、隔离 sys.path/import、duplicate key、UTF-8/LF、ZIP 路径/特殊文件/CRC/ZIP64/大小/比例、完整 RECORD/set/SHA、metadata/WHEEL/LICENSE/notice 和输出 cap 均保持。只做静态 PE 观察，不能因此取得 DLL 加载或许可证分发资格。commit 元数据语法不能证明 wheel 与上游 source 的完整关联。

未来声明仍是 wheel/commit 两个独立入口：原 pwsh NoProfile/NonInteractive、固定 Owner/Phase/Plan SHA/cwd/batch；Owner 只替换该 Plan 的 exact SHA 占位。Acquire 与私有 Python `-I -S -B -X utf8` 分开；命令 env 闭集保留。每 Plan 原 23 inputs 和两个子命令保留，全部未知历史计数继续 null，不改成零。完整 body/reuse/metadata cap、旧失败额度、模型与费用边界保持。当前声明为 NO_EXECUTION_GRANT。

Loader 的 29 个 source/target 声明与两 Plan 对应：19 source、3 启动编码、1 linecache、5 binary、1 pth；6899063B 是声明量，不是本轮材料化或原生加载观察。private29 仍 NOT_READY_NOT_MATERIALIZED；本评审没有实体重扫、复制 runtime、加载 DLL 或确认 ABI/许可证闭包。声明的普通工具 map 和源 hash 不是实际可执行资格。

## 后继验证责任与未完成范围

Integration 后继须提供真实原 Process/PID/creation、独立 stdout/stderr raw 与 EOF、原 task/资源持有和自然终态证据。至少覆盖：元数据 getter 异常；两个 pump 的独立接线失败；单通道失败而另一通道继续；WaitForExit true 且已经越界；原 task 已完成但越界；Save/flush/cleanup 迟到或异常；末 receipt 写失败；真实子进程 exit 0 后不得清除 sticky；永久未知状态不能用假 EOF 或强制释放洗成成功。实际 fault 与正常路径测试均未执行，不以作者 parse0、装配0或本评审工具0替代。

原历史来源/失败、旧三次19目标耗尽、31 NOT_READY、未知获取次数、费用上限和全部许可证/材料资格缺口原样保留。此报告未授权应用、材料化、网络请求或新的运行；也不关闭 Owner、API/MCP、媒体、安装、三 OS 或完整 R1→连续 R2。

## 输入末核与工具记录

本轮初始 85 个有限路径来自正式固定输入及自身既有来源记录，不是 runtime 全树扫描。末核及差异保存在 InputAfter.json，正式统计由封存脚本写在下方。所有新评审文件为 UTF-8/LF；目标源码和原旧报告/finding未修改。

原工具输出截断在 ToolHistory.json 明确保留：3acfb1、283d8e、c79ad4 不称全文；后续必要定向正文、完整差异字节重建和完整 JSON 比较分别补足。486400 将数组/嵌套字段误作顶层作了 null 投影，自然 exit 0 不等于字段已核；c79ad4 用真实结构纠正，原输出保留。这些属于评审元数据观察界限，不是候选或产品失败。

当前报告写入本身不提前声明写工具终态。最终实际返回、no live 和全部 reader release 以 FinalizerTerminal.json 与 FinalHandoff.json 及本人随后消息为准。

## 最终身份与末核附表


末核：85/85 有限路径 bytes/SHA 相同，changes=[]；13 个新普通源均与固定索引实际 bytes/SHA 相同。未新增 runtime 扫描。

| 固定新普通文件 | Bytes | SHA-256 |
| --- | ---: | --- |
| AcquirePinnedEvidence.ps1 | 8882 | c41f250af416eeac9f6691b4c83c57f57519d77699884ba9b3f3507794363290 |
| AssembleSourceProposal.ps1 | 15612 | ff474a9fcbf01831ac1e61a0e67132772b75400c8fa8cc88e9b67b159b6a2b9c |
| CommitExecutionPlan.json | 41532 | 457b6695e3bc80a4ebf99edddbb752b2b1d7d270c12951d73e2a2f34604fb88c |
| FinalizeSourceProposalRevisionTwo.ps1 | 23533 | 7fcd80b6afb43e295baa1e17d8d23a1f798af7ccef9dfe2572bd6c607615a1ff |
| InspectPinnedLicenseEvidence.py | 35049 | 9858e12791b3f1f9427d6737e009930e43b04278a135994f5e5f023e6f9c9573 |
| LicenseInspectorTail.py.txt | 10415 | d664c859dec17a715ca0be6b36018976c6526c5cb29df218102fd6e6f998757b |
| LoaderProposal.json | 22676 | 1c802acdc45f014cdbcab84832b4afe8c091d6d0fdf1281676be5216d393d2b3 |
| PreparationDelta.json | 2340 | 6ac0ad817a851bb8010007bfc0d5c838fa1e9391f63e5af00feac49da7a6e3f3 |
| PythonPathProposal.txt | 6 | 82cfe92f04fbacfdcb908eccc04c6c9bfb662bd6e554615a67e53d573d544387 |
| RunPinnedLicenseEvidence.ps1 | 16501 | deb19c5d2dde425048bcfabc21542107970aeae5f6891a0f46c0a0c876c14b71 |
| RunSourceAssembly.ps1 | 3580 | db73399349626f8694c9ac1bb2343503384ed33ea8658b2139e043b62d8d149d |
| SourceAssemblyReceipt.json | 10173 | 694663a396b2df817726d36c1ee25dad9fc3e41e47ec263e9eae1a8bb8b1ddd1 |
| WheelExecutionPlan.json | 46517 | d432deb41a3319ecd1f076d3460f68fb345b810d6cdef4297fe8389ed3af4fb2 |

完整绝对路径与身份另存 SourceCoverage.json；85 初末路径另存 InputBefore.json/InputAfter.json。

