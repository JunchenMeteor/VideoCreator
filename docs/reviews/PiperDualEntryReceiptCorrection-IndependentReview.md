# Piper 双入口终态收据修复独立源码评审

结论：原 PDM-P01 在本次两个精确冻结入口可裁定 `CLOSED_SOURCE_STATIC_ONLY`。本次独立确认原 metadata 入口存在同类末次保存漏门，并确认它也补上该源码缺口。没有新确认 P1/P2。正常保存、实际磁盘/ACL/目录消失注入、stderr 故障、真实子进程及网络/归档运行均为 `NOT_RUN`；此报告不授运行准入，不关闭 Test87 的 PDRT-P01/PDRT-I01，不证明安装、ABI、许可、媒体或完整 R1/R2。

评审角色：唯一永久 Review；写入仅 docs/reviews 与本过程目录。任务卡 SHA 为 `e0bd2bb8e7b5fac98beeca238d8a05f1cbe82e0661af1b49e150aa4dc6ecc634`。完整 R1 三 OS 真实作品、多模态交付后连续完成 R2 的目标保留。

## 固定来源与独立身份

实际正式根为 `G:/开发测试/Codex/VideoCreatorImplementation/Integration/PiperDependencyMetadataReceiptCorrection/SourceRepairStage`；历史卡的 SourcePreparationStage 表述不是本批文件路径。ActualInterfaces 在其父级根下。

| 文件 | SHA-256 |
| --- | --- |
| SourceRepairStage/Handoff.md | 852ca3d9943f12ec0818d7931ca0bc4d31d454930a4fea8f3dd889818d8e7119 |
| SourceRepairStage/Handoff.json | a6e15c401154080058b425118f7fe0e6487013efeb49fedc42849f3f356bcf66 |
| ActualInterfaces.md | ce6e0f9aaf401acd2e061e7727063fc03da7775ba301432d5b53c23c943ed7a4 |
| SourceRepairStage/OrdinaryIndex.json | d8d768eba5bb5183ee220b53dc1dec2db8ac27ea621329047b5dadb349b6643a |

独立前后核对 167 个固定路径：144 普通副本、16 精确原工具/材料、7 规则及正式控制文件。160 条 indexed 身份逐项大小/SHA 匹配，167 条末核无变化。没有扫描或重复制运行环境，也没有把作者 InputsBefore/After 的一致当本人的独立检查。完整定位保存在本过程 `SourceLocators.json`，原件与实际 ordinary 路径分列。

| 入口/材料 | 原 SHA-256 | 新 SHA-256 |
| --- | --- | --- |
| Semantic runner，8896→9398 B | 9fd3b5af423e2f3505c843bd5acb7a60763ca95c85a54812f388649884bdb24d | 441ae75d2836031509f92dcf89cba8a68f5490c6dc43ec95529bb98aa51d1ba0 |
| Semantic helper，37505→37523 B | 85446bdb3783653d1b5fa997848d59c778ba6f95ea4eda6515092d0f90146143 | 7f904e8f8ca7a8cb21dffb950858bba736f632108dd28ad3803f5c59b9e2433a |
| Semantic Plan，55240→59401 B | 292edfd85fd5fe08c5a4cfed501f2b1dfdf92ac8db26584c81eaf07e75a10327 | 96abae4eb1558a263986edce685655929afeb9e778a62ce788a8c74dfac0b80c |
| Metadata runner，9188→9706 B | 20bd0c4399b54f3d578567d8fd399b6c3df85a50c379fd9bf7bc483d315496a7 | 1f48addc0b2608e6d98c9ec10cd5e4d3c30f596a6df4bbd5a31f53f17fd87c37 |
| Metadata helper，8803→8820 B | e2a4add9bd54a046aaa13182ccd889cfe4e3adcb0b0d28dcff3f7c9a85763a9b | 2818287198f443458e4c9412ab2fa7e9087a159386f979e73a441462d8a4487d |
| Metadata Plan，49979→54050 B | db703ef566ffeaf579929f343a75ad653c47459c4c02c658a595edee89a60bbe | 2c6b922615bf6c0dff491a153020bb591566c5dee7ad110291e0e8d238a1c1c5 |

## 末次保存失败的真实源码链

评审所读 runner 普通副本分别是 SourceRepairStage/OrdinaryCopies 下 `Input140-RunSemanticInspectionRevisionTwoRoundOne.ps1` 与 `Input149-RunTransitiveMetadataRoundOne.ps1`；原件分别是 Input147 与 Input156，同名不同 prefix。所有行号以下均针对这些冻结副本。

原 Semantic runner 83–89、原 Metadata runner 87–90 都先检查 errors/选择成功 state，才执行最后 SaveOwner；旧 SaveOwner catch 只加入 ReceiptWrite，最后写首次失败可能仍按此前 actual_exit=0 退出。Metadata 同类风险现已由本人读取原完整入口确认，未直接继承作者说法。

新 Semantic 12–22、新 Metadata 10–20 的 SaveOwner：仅创建独占 batch 后设置 ReceiptRequired；此后目录缺失主动抛错，写入/序列化错误都进入 catch。先保留 ReceiptWrite 类型，再把 actual_exit 置 1、state 置 FAILED_FIRST_ERROR_PRESERVED，并向原 stderr 写实际类型/消息。catch 内没有第二次写、旧成功 receipt 读取、清错误或替代路径。新 Semantic 97 执行最终 SaveOwner，99 在 finally 后重核 errors/input_changes；新 Metadata 98 执行最终 SaveOwner，100 再核。最终出口因此覆盖最后保存首次产生的错误。

源码支持的具体关闭条件是：任意该 checkpoint 的错误不能被后来的成功结果/最终状态计算洗成零退出；必要 batch 目录缺失不能静默声称已保存。保存失败并不产生可信终态文件，本报告不会仅因内存 state 或 console 文本宣称 receipt 已写入。

原 first ReceiptWrite 类型在 stderr 写入前已锁存；若 stderr 写本身再抛错，它将沿原外层 catch/finally 传播，而不会进入一个成功重试分支。该双故障的实际异常输出与磁盘可观察性尚未执行，不能声称已经捕获全部原异常消息或完成故障注入。

## 原进程与故障后 checkpoint 的边界

两 family 的完整 OwnedChild 正文前后文本相等，分别保留原启动、真实 Process 对象、PID/creation 观察、同对象 WaitForExit、两路原 byte stream CopyToAsync/排空、sticky deadline 和原 finally。没有新增 PID 重发现、kill、新 child/replay、替代成功 EOF 或 timeout 清零。启动后 running SaveOwner 即使失败，内层 finally 仍等待原对象自然终态并排空两路原输出；外层 finally 仍处理原资源，并在 started && terminal 后才 Dispose Process。该结论是源码控制流支持，尚不是实际 OS 观察。

后续原 running/child-ended/outer-final checkpoint 仍可依原生命周期执行；它们不是 catch 内重写失败 receipt 或重复发起归档/GET。errors 不清除，后续写成功也不能令 OwnedChild 成功条件或最终出口忽略原错误。中间原 RUNNING state 可能与 actual_exit=1/errors 同时存在，不能把它读作无错运行。

此源码没有承诺任意 early SaveOwner 错误都阻止尚未创建的首个 child：最初 SaveOwner 调用之后仍有原 OwnedChild 调用。评审关闭的是终态漏门及原 handle 保留，不把未启动/零请求或所有故障窗口都已实测作为关闭依据。900s 超时仅粘性标记失败并持原对象等待，不是强制终止时限。

## 全文差异、Plan 与保护门

两个 CompleteSourceDelta 和 CompletePlanDelta 全部 hunk 已独立解码重建完整 before/after 正文。Semantic runner 89/101 行、helper 725/725 行；Metadata runner 90/102 行、helper 82/82 行；两个 Plan hunk 都是 1079/1145 行。声明行数、从第 1 行开始以及全部实际正文逐项匹配。首个 observer 用最小 unified diff 比较作者“整文件全删/全加”表示，字符串比较 false 保留在 FamilyComparison；这不是代码差异，也不是候选执行失败。此前 commentary 对“换行导致”的归因不准确，正式结论以全 hunk 正文核对为准。

Semantic 110 inputs 完整保留原 102；Metadata 51 完整保留原 43，旧 path/size/SHA 无改动。新加各 8 条，绑定任务/finding、旧 Plan、新 runner/helper/diff、准备器。Plan 非 inputs 的变化仅精确新 root、argv/cwd/TEMP/TMP 相应路径和 receipt_correction 声明。其余完整对象比较相同，包括 source_map、archive/targets、incoming 原始声明、caps、旧失败来源、qualification=false 与无需运行的声明。

两个 helper 各只有一个任务根 literal；按精确新 root→旧 root 逆变换，完整原始 bytes 相等。Python helper 整模块 AST 也相等，20 个原函数和 1 个原 class 保留。原 RequirementRepresentation.py 普通件 14205 B、SHA `9eae0ad968c464189810a62e0ecf2579a2dc5ef11de1fc6dd3b523e3018ac382` 未改；169 原 raw 及原 marker/operator/unsupported 表示边界未被本窄修重新定义或执行。

Semantic 六固定 archive 共 4425126 B，原 source_map_declared=20、CRC/ZIP64/RECORD/header/EOF/安全路径、WHEEL/许可/静态 native 来源门均由完整 helper 与 Plan 的不变部分保护；data-only、no vendor import/native load、no network/install/model/fee 保留。源代码门存在不等于六 archive 新运行通过，也不授权重新检查归档。

Metadata 精确十个官方 PyPI JSON URL、各 60s/8MiB、总 80MiB、owner 900s、TLS/identity/no redirect/proxy/auth/HEAD/Range/retry/recursive 未改变。完整 targets/incoming 源对象、原 14 JSON 与 3 原 PASS raw incoming 的保留关系、未激活 extras/未执行 marker/range 及各平台区分都保持；没有把 metadata 数据资格升为可用模型/许可或 runtime。helper 的首个目标错误仍停止后续目标，保留 NOT_STARTED。新输出是 MetadataRevisionOne/MetadataRoundOne，未改为 RequestMetadataRoundOne。

## 后续真正验证与未测

原 Test 后继需独立定义、固定并执行正常最终保存，以及仅最后一次 SaveOwner 失败、运行中保存失败后原 child/双 EOF、required batch 消失、stderr 自身故障等边界；核实际退出码、原异常/receipt 是否真实写入及原对象终态，不用一个非空 JSON 或 author parse0 自证。本报告不授这些运行，也不授六归档/十 GET/87 case 或第四旧19目标。

原 literal12差异红、c6271d 准备红、两未执行、原 PDRT-P01/PDRT-I01 及所有原失败材料保留。Test87 的独立标准与本 dual-receipt source 修复分开。没有真实完整制作、可信 Owner、安装整包、三 OS、媒体/ASR、商业权益/发布验收证据被本报告新增。

## 本人过程错误与终态

65ff8e/1 是错误猜测 SourceRepairStage/ActualInterfaces 路径；11a69c/0 纠正到父级正式根。0aada1/1 是本人 observer 未处理 16 retained 条目的 ordinary=null，后续 8f9f2e/0 按正式索引实际路径核对；未改 candidate。期间一次 require_escalated 命令因自动审批服务 usage-limit 拒绝，实际未执行、未产生 live handle；通道恢复后仅继续自己的只读元数据观察。以上不是产品红或安全绕过。

0f80e1/0、82828d/0 为自身 stdlib diff/JSON/AST 解析；09bebd/0 的大 projection 输出截断保留，581d3c/0 定向输出必要完整摘要，未宣称截断 console 全文。输入末核由本报告 finalizer 对原 167 条完成，无差异；本轮正式报告和 JSON 写入 UTF-8/LF，原输入字节未转换。正式末工具真实返回后另写 FinalizerTerminal/FinalHandoff，才由本人声明无 live handle/全部 reader 释放。作者静态 0 和准备 metadata 0 不能替代此评审或运行验收。
