# F11 八项恢复组件机制独立复核

结论：**LIMITED_COMPONENT_MECHANISM_SUPPORTED**。固定八项均真实到达并通过，原 F11-P01“首次受理后丢 ACK，再核实被拒却误清 pending”的当前 React/SDK 组件窗口有有限关闭依据。原首批仍为 1 次夹具交互失败、7 项未执行、整体 exit 1，未回写成通过。本轮未运行任何产品或测试，也未授 Owner、Backend API、安装、原生资源或 R1/R2 资格。

## 1. 固定身份与独立核对

正式根为 `G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/F11RecoveryCorrectedFixture/`，普通根为其 TestDevelopment 同级 `ReviewHandoff/F11RecoveryCorrectedFixture/`。Handoff MD `e3241fdba60dc4f7c2e1c390dad0692ad69664ce03004d4e3ff78ed53c1f73ae`；JSON `dbcf166d94de6aa6636fdb6ba4933752c0257dd31cafe3d2aa08b19f6f427d21`；Snapshot `deb7da52ebcc9515ef3226daaff5532ca89b4206b9a5b89f2c09454747a72959`；65 件普通清单 `69a59b8c4d7366c34182d7aaea08534833fb963b4a4b686c96fead142b9ed562`。独立逐 original/copy 核 130 路径及 3 个显式 sidecar，无 size/SHA 差异；末核有限 141 路径 changes=[]。

完整读八 Case、实际 HTTP 夹具、runner、Harness、相干组件与保存/导航调用链；纯解析完整 Result、285 条 Events 和 JUnit 八节点逐名对应。23 个完整源副本含 14 Frontend、1 Desktop port、8 SDK；不以这些副本代运行环境资格。运行自核的 8768 records/528 links、前后 changes=[] 是声明索引覆盖，本评审未重复扫描全部环境或宣称覆盖所有 OS 读取。

Case 源 `12a2513a9a70be0e5dce2d94a0768ee45a589f1ee034f511b8060cf6a4ca3fd5`；runner `961397f81f14440a0321a6ae335f96c6eac825cd650bf16fd3f0f493c03c3397`；PS launcher `7f44aaa6aa458cc669ae6a3688bdd126acc2841fbfd10fe448ccfbfda1e26f83`。完整普通 Case 与原批 `SourceBodies/CasesExecutionF11.mjs` 的真实 unified diff 与所交 FullFixtureDiff.patch 字节文本相同；八目标和原 5000ms poll/page 条件未改。

## 2. 八项实际到达

| 实际 Case | 耗时 ms | 有证据的窄支持 |
|---|---:|---|
| 丢 ACK → 401 → 核实 | 2088 | 原 pending、body/key、重载恢复；3 次 transport 到达，1 次夹具业务受理；原任务回执与导航 |
| 丢 ACK → 403 → 核实 | 1647 | 同上；3 次 transport，1 次受理 |
| 丢 ACK → 明确 not_sent → 核实 | 1617 | 2 次真实 POST；透明派发前 not_sent 另记原 body/key；1 次受理 |
| fresh 401 后明确新动作 | 904 | 首拒无受理；第二个显式动作使用新 body/key，1 次受理 |
| fresh 403 后明确新动作 | 930 | 同上 |
| fresh not_sent 后明确新动作 | 900 | 首动作派发前拒，只有第二个动作 1 次实际 POST/受理 |
| foreign-instance 回执 | 1119 | 外实例回执不结算原 pending、不选原任务；正确核实后返回原任务 |
| A→B 后迟到 recovery 403 | 1249 | A 原 pending/body/key 保留，B 不导航原任务；返回 A 后核实原受理 |

八项 Result outcome=passed、page_errors=[]，Result errors/not_executed=[]。JUnit tests=8/failures=0/errors=0/skipped=0；285 事件含 case_started=8、case_terminal=8，每条 terminal 的完整 case 值与 Result 相等、先后顺序相等，八项请求实际 body SHA 均匹配其原 UTF-8 正文。五个丢 ACK 窗口各记录唯一业务受理、浏览器已见 200 headers 与半 JSON 后断链；本批未观察到首次传输自行重复到达。支持夹具中的重复到达只读原受理代码，不把“允许重复”的源码当实际重复已测。

原错误把一次 transport arrival 等同唯一业务受理且直接 destroy，无 usable response。修订保留唯一业务受理和每次到达相同 body/key 断言，增加 headers/半 JSON 确证；恢复计数从绝对两到达改为“首阶段实际到达 + 一次显式核实”。这修的是独立夹具和观察口径，不降低 exactly-once 业务要求。原失败 Case 6015ms、poll 的原 5s 上限错误及原 overall 1 完整保留。

真实 React/ReactDOM、Query、完整 Workbench/SDK 被执行；HTTP 服务、managed instance/principal 为透明合成。not_sent 是 Harness 在 fetch 前抛出的受控 RequestFailure，不是后端未受理证明。fresh 和 recovery 语义分别实测，后继核实的 401/403/not_sent 不被误用为首次业务未受理依据。

## 3. 原进程与终态

原命令由 `4a2370/session13931` 启动，原 owner `4d978f` 观察自然 exit 0；Node PID 34624、creation `2026-10-10T02:54:30.7558000Z`、原 .NET Process handle 2108、argv 绑定 RunCorrectedF11 与 index `ffc65dd12547360784788b6c67d0c0c676cc267c968d1becfa8a47817c554cb5`。原 CommandReceipt ended `02:54:47.1968588Z`，actual_node_exit=0、stdout_eof/stderr_eof=true、forced=false、no_restart=true、errors=[]，实际原 stdout 汇总同值、原 stderr 0 字节。

浏览器 PID 2256/creation `02:54:33.5184856Z`；Node 留原 BrowserServer.process()，另 .NET 句柄仅观察。Result 保原 close event exit 0/signal null、Vite close 与两个 loopback 端口 61359/61362 关闭；独立原观察同 PID/creation has_exited=true。没有把新进程/PID 再查询冒原退出码。outer PowerShell 完整 raw 未单独保存，浏览器 prelaunch raw 未捕获；只保 Node 两 byte streams 与浏览器 post-launch stderr（Vite/DevTools info）。不称全链 raw provenance 齐全。

## 4. F11-MECH-I01：原 Goal 关联合同与覆盖缺口

**P2 / OPEN_CONTRACT_AND_COVERAGE，SOURCE_STATIC assurance gap；非已复现运行缺陷。归 Frontend，Backend/Integration 提供唯一固定公开合同，Test 后继独立覆盖。**

精确固定路径均在上述普通根：`FixedFrontend/NativeSetupView.tsx` SHA `a3cfb57656df6454b2fa3a2338753cf85d848ff14814aab33dbefe35d2db198c` 55–64 行；`goalIntents.ts` SHA `02107a19bd1460df4b56de9dca7df70a27c5e09bdfa9fdd1fd0c5f90af55f051` 43–55 行；`Workbench.tsx` SHA `0b36abcf511c9af43d693e82868572506c7f012a5213a8aefbc59628c6ecb6a9` 195–203 行。

sendApi 核原请求 bodyHash/current，收到回应后只核 isGoalReceipt 与 instance；isGoalReceipt 将 goal_sha256 核为 64 hex 并核内部 project/production/run 一致。随后 accepted 保存，当前 UI 触发导航。若服务返回“同实例、内部 IDs 合法，但属于另一完整 Goal”的回执，这些门自身没有建立原 Goal 对应关系。八个夹具总返回原 body 的 digest，foreign 负例仅改 instance，未执行同实例 wrong-Goal 负例；因此本轮不能给原 Goal 关联全覆盖结论，也不认定真实 Backend 已错配。

不能直接要求 `goal_sha256 === original.bodyHash`：固定 `engine.ts` 189–191 的 inputHash 是 SHA256(JSON.stringify 原 body)。新增独立固定合同输入 ADR0039 SHA `f07037c4bd66a56dc03115a9c357940bb96640bb5c52f35d64424f3a7cd7198f` 的 16/18/40/44 行区分 full canonical Goal 与 normalized ProductionRequest；SDK schema 2502–2503 只有 string 定义，没有给 canonical bytes 算法。前端原 JSON.stringify、fixture raw-body SHA 都不能擅自充当服务端算法。此前“直接相等即可修”的候选条件撤回，未要求对合法 normalized 回执误拒。

最小后继：先由实际固定公开合同明确 full canonical Goal/hash 或同等严格请求—回执关联，再由 Frontend 实现合同支持的严格核实；独立 Test 同时保合法 canonical/normalization 正向、同实例 wrong-Goal 负向与本八项原 body/key/pending/identity 断言。不可核实回应继续保原 pending，不能给它换新 key、清原意图或凭 fixture hash 升资格。本报告不新增接口/算法或批准实施。

## 5. 自身分析错误与未测范围

自身最初 MechanismFacts.json 对 case_terminal 错取 case 字段（真实字段为 name），导致 per-case 假零；aggregate 8 正确。该原件 SHA `1003bb18db4f4e0ffbf9ca7c12cfcc236e392945cbc832a8550573f2fba2b264` 保留。后只读工具 `0f413f` 还误用 Result.results，KeyError 自然 1 且输出截断，未执行测试；新 `85aba3` 自然 0 以实际 cases/name 核八条全值一致，另存 MechanismFactsCorrected/OwnAnalysisErrors。初步显示截断（a74de8/194037/9e6363）不声称全 console 阅读；完整原文件未改，必要源段与语义由定向读取核清。自身分析错误均不计为产品/Test 失败。

本轮未授 native lost-prepare 关联、真实 Owner/本人确认、Backend API/MCP、启动/安装/Win32 资源及预算 authority、媒体/ASR/RAG、三 OS 或完整 R1→R2 通过。现有 native、真实资格、合同关联与其他未覆盖矩阵仍 OPEN；本八组件机制支持不继承到未来改源。原预算/unknown/floor、历史失败与完整 R1 后连续 R2 目标不改。

完整独立过程：`G:/开发测试/Codex/VideoCreatorImplementation/Review/F11RecoveryMechanism/`。本阶段只读固定材料、仅写评审白名单；无运行/改实现/测试/费用/网络/秘密读取。
