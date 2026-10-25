# MaterialConnection corrected runtime 独立评审

结论：**LIMITED_COMPONENT_EVIDENCE；整批 NOTPASS**。当前唯一修订执行有 14 个实际 JUnit 节点：M01–M13 通过，M14 在测试准备阶段失败，原 Node 自然退出 1。13 项支持固定 React／SDK／受控本机 HTTP 的已到达机制；M14 的跨实例素材预览目标未到达。发现 **MCCR-P01 / P2 / TestDevelopment / OPEN_TEST_PREPARATION**，不据未到达的断言归责 Frontend，也不把零请求算作 M14 通过。

本评审只读取冻结普通副本、源码、测试正文及原运行记录，未 import／运行产品、测试、浏览器、数据库、原生程序或媒体工具。没有修实现、改期望、提高时窗或重跑历史结果。完整 R1 后连续 R2 的目标不缩减。

## 固定版本与独立输入

任务卡为 `G:/开发测试/Projects/VideoCreator/docs/task-board/MaterialConnectionCorrectedRuntimeReview.md`，SHA-256 `700a60e845b80e9e199bda18b4ad7c799a5017af5f85bdaea55ec20a28894a34`。普通根为 `G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/MaterialConnectionCorrectedExecution/`。

独立逐项核对 75 个有限普通副本的大小和 SHA；加治理、正式件及终态件去重后共 **83 个固定输入，末核 differences=[]**。完整路径和 SHA 见本过程的 `InputSnapshot.json`、`InputAfter.json`。没有重新盘点或复制 8824 项运行环境；原 InputBefore／InputAfter 的 8824 records、528 links 和 changes=[] 属原执行记录的范围。

| 关键固定件 | SHA-256 |
| --- | --- |
| ExecutionHandoff.md | 25f356e0a2ece2db2551a39cbae76272f12809ec8ba85d155ac536359541ffae |
| ExecutionHandoff.json | d139a771dfde5b296f9a5c268009173bab1f6a27ac25ad481e864db1e1c5bd92 |
| ExecutionOrdinaryManifest.json | 7c2abc55be487aba02f98dda41049f68089be54b0f3985b93b0ada540e427a2a |
| ExecutionSnapshot.json | b1e85390eddee31249b077c3cab135a675aa5e8b53ff157a1a1a56ca4bb6ddf1 |
| ExecutionFinalizerTerminal.json | d4dcfaf92eddec90e91307a0f3a72f2df3cc3e76bdb9c2bf26fb7a9317410793 |
| Preparation/ConnectionCasesCorrected.mjs | a849ada622f96d56c95ef389790e917811efacf850a624cee633eb335cc0b1c6 |
| WholeSourceClosure/SourceSets/Fixed/Workbench.tsx | 180f205942ee3185f213aa4da7a3ce6d5f2d06c4df9d3cf8b7bbde0558b3b5fb |
| FixedExecutionRoundOne/Result.json | 6db922ec0d5f488163d4f3da52030440b54add0ba548c82b50c11ba5da82a225 |
| FixedExecutionRoundOne/Events.jsonl | 8a137575e727e8a206029f1ccc9d5cb77d305b135f4d163e295c8220e27257c2 |
| FixedExecutionRoundOne/JUnit.xml | f44f6e91ccffae8d9d349627c982a0319666eb9a2039363e49d3cc15b4269483 |

Case 正文与前一独立批准的准备版本 SHA 相同；14 名称、顺序及原 34 个目标断言保持。原 Actual A→B 请求失败和前一 Fixed 的 M07 准备超时／后 7 项未执行保持原件，不用本轮结果覆盖它们。

## 原执行终态与范围

原调用为固定 `RunConnectionCorrected.ps1 -ExpectedInputIndex b87f1612fde27758b0e91554ead523031660ed87c99de776deb0ee05d8f9f982 -SourceSet Fixed`。原函数 cell 11／a419d3／session 87090 由原 owner 续到 5660e8，实际整体退出 1。

Node PID **32264**，creation **2026-10-10T07:32:47.6646520Z**，保留的原 .NET 进程句柄 2192；原 Node stdout、stderr 两个字节流 EOF 均到达，forced=false，实际 stdout 295 B、stderr 0 B。stdout summary 与 Result 的 14 cases／1 failure／0 case errors／0 not_executed 对应。浏览器 leader PID **33360**，creation **2026-10-10T07:32:50.3389572Z**；原 BrowserServer ChildProcess close 记录 exit 0，.NET exited=true 仅作观察。原 cleanup 记录 Vite 62349 与浏览器 62355 两端口关闭，原收据、事件、摘要对应。没有全浏览器子孙或 Job 终态证明，也没有完整外层 PowerShell 原始字节文件；不能据此宣称全进程树或安装生命周期验收。

Result 从 **07:32:49.599Z 到 07:33:18.318Z，28.719 s**；各 case duration_ms 合计 **25.229 s**，与外层工具墙钟口径分开。JUnit 实有 14 节点、1 failure、0 error、0 skip。M14 原失败 payload 保留，未改成 skip 或 pass。

独立解析 Events：全部 14 个 `case_terminal` 对象与 Result 对应 case 逐值相同；全部 14 项 fixture 请求事件与 Result 请求数组逐值相同，不能仅靠非空 JSON 或汇总数判断。自己的首次派生解析误用 `case` 取 terminal 名，实际 terminal 字段是 `name`，得到错误的 terminal_count=0；原 `IndependentRuntimeFacts.json` 保留，纠正文件 `IndependentRuntimeFactsCorrected.json` 明确说明并保存 14/14 匹配。这是评审解析问题，不是产品或原测试失败。

## 已到达的 13 项机制

| Case | 实际 duration_ms | 原目标已到达的有限事实 |
| --- | ---: | --- |
| M01 | 1867 | A staging、import、Goal 原请求链；导入后的 A asset ID 进入 A Goal，携原 key。 |
| M02 | 858 | B health 被持留、缓存仍是 A 的窗口没有 staging／import POST。 |
| M03 | 1418 | A staging 被持留，切 B 后释放 A 成功响应，不续发 import。 |
| M04 | 1444 | A→B→A 新世代后释放原 A staging，原 lifetime 不复活、不续发 import。 |
| M05 | 836 | 同实例 principal 变化、健康检查持留时原文件不发送。 |
| M06 | 850 | 同 client 新 installation 世代、健康检查持留时原文件不发送。 |
| M07 | 2268 | B 正确准备后，原 A import 成功迟到不能接管 B；B 后续正常 import／Goal 只含 B asset。 |
| M08 | 2301 | A staging 422 迟到及 finally 不清 B busy；B 后续正常 import／Goal 只含 B asset。 |
| M09 | 2216 | A import 422 迟到及 finally 不清 B busy；B 后续正常 import／Goal 只含 B asset。 |
| M10 | 1459 | 已知 A asset 切 B 后未进入 B Goal，B 请求 asset_ids=[]。 |
| M11 | 1232 | 同连接 retry 复用原 staging；两次 import 的完整请求正文保留原 bytes／source／rights。 |
| M12 | 1490 | Goal 响应丢失后切 B，原断言检查 pending 原 body／key／asset set 不被改绑。 |
| M13 | 1213 | 同 client 新 installation 建立后，旧 disposer 不清新状态；新 A staging／import 到达。 |

M07–M09 的实际准备 snapshot 显示 B 在 establishGoal 前为空、之后为本轮目标；主动释放 A 前及 A 回包后目标断言前都是 B epoch=2／identity B／is_current=true，“正在校验”按钮仍 disabled=true、alerts=[]。请求和 held/release 事件保持对应次序，原目标断言随后执行，再完成 B import／Goal；不是靠 finally 清理代替原迟到响应窗口。

M11 的 rights 是透明 fixture 提供的测试事实，不是生产许可核验。M12 的实际请求 body／key／asset set 与执行到的原 localStorage 断言支持该机制；没有另存浏览器 localStorage 前后快照，不补造这一层原始观察。若通过项 Result 没另存 page_errors 或 unexpected 字段，不将缺字段冒称额外实际数组；原 source 的相应断言到达与 Result 原 pass 分开记录。

这些是实际 React／DOM／Query／生成 SDK 与受控本机 HTTP 的机制证据。fixture 的身份、not_sent、rights、asset ID、Goal 回执不能冒充真实 Backend、Owner、native、权限签发或真实素材处理。

## MCCR-P01：M14 缺少展开素材输入的准备操作

**P2；归属 TestDevelopment；OPEN_TEST_PREPARATION。**

固定 `Preparation/ConnectionCasesCorrected.mjs:228–233` 中，229 行先点击“素材”导航，再立即 `fill('#asset-id', 'asset-A')`。230–233 行才设置 holdMetadata、点击“打开”、等 A metadata held、切 B、主动释放 A，并断言无 follow-up `/content`。填充失败使后面整条目标链没有执行。

固定 `WholeSourceClosure/SourceSets/Fixed/Workbench.tsx:408` 将导航切到 assets；425 行把 `#asset-id` 放在原生 `<details className="advanced-settings">` 内，其 `<summary>` 是“打开已有实例素材”，源码没有 open 属性。测试在填充前没有展开 summary，也没有观察 open／visible。固定 `openAsset` 的完整 349–374 行使用 capture/current/instance/controller 门，依次读取 asset、metadata、content 并在回包及状态写入前检查；M14 未调用该 handler，不能从此失败评判这些门的运行表现。

原 Playwright 错误明确为 **locator.fill Timeout 5000 ms**，匹配到实际 `id="asset-id" value=""` 输入，但它不可见，栈定位 Case **229:108**。M14 duration 为 **5777 ms**，包含先前 A 准备，不表示提高了 5 s 时窗。原保存的页面正文已在素材库，包含“还没有打开素材”“打开已有实例素材”；page_errors=[]，当时连接仍是 A epoch=1／current=true。实际请求只有 A health／projects／productions 等准备请求，没有 asset GET、metadata GET、content GET、metadata hold 到达或 B 切换。因而“零 content 请求”不能当作 M14 的目标通过。

没有保存 details.open、截图或 Playwright trace；初始折叠是源码依据，不伪装成已记录 DOM 属性。结合实际不可见输入与缺少 summary 操作，可将该次失败归测试前置遗漏；没有证据归责 Frontend 的跨实例预览逻辑。

后继最小修正：在新的固定 Test 候选中用真实用户式 summary 交互展开折叠区，观察 details.open 与输入 visible/enabled，再执行原 fill。保持 14 名称／顺序、全部 34 原目标断言、5 s 条件和 240 s Node／300 s outer 时限；保留 A metadata held→切 B→主动释放 A→无 stale content 的目标链。不得 force-fill、直接改 DOM 开关、修改产品默认状态、放宽时间、删除 M14 或把原红改绿。修订 oracle 需独立复核，实际新执行需另行精确准入；本报告不授新运行权限。

EarlyFinding 的完整源／raw pins 见 `EarlyFinding-MCCR-P01.json`，SHA `b0eeaa158b240194321b393e26bad6cbe0551f904e560db62b231b4ed494e6c4`。原 Result／Events／JUnit／自然 1 均保持。

## 尚未支持的资格与交接

M14 目标仍 OPEN，整批仍 NOTPASS。未覆盖实际 Backend API／Owner 真人确认／native wire／可信许可与资格 producer／真实视频音频／完整三 OS 安装或 Gate0／R1／R2。未观察全浏览器子孙、完整 Job 关闭、外层 PowerShell 全字节或 M14 details.open／trace；这些限制不能靠源码、fixture、历史绿色或 Root 摘要补成通过。

本阶段只交付独立有限组件证据与 Test 的具体准备修正条件。InputAfter 的 83 项末核无漂移，源码读者已结束；正式写入工具的实际终态由本过程 FinalHandoff 和 FinalizerTerminal 另记，不将 return-pending 写成已退出。
