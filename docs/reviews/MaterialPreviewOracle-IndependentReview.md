# MaterialPreviewOracle 独立准备版本评审

结论：**MCCR-P01 在 ORACLE_SOURCE_STATIC_ONLY 范围关闭**；本次固定准备版本的有限 oracle 审查通过，无新增阻断 Finding。此结论不授予实际启动许可或 RuntimeBinding。原 corrected 14 批次仍为 13 PASS、M14 输入不可见且目标未达、整体自然退出 1；该原结果及历史报告不得回填。新候选没有执行。

## 固定范围与身份

任务卡：`G:/开发测试/Projects/VideoCreator/docs/task-board/MaterialPreviewOracleReview.md`，SHA `f41b6189726dbf69e7c852c17f857d99bdef53ec8d4018d0f77c9dd81d0b3573`。

普通根：`G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/MaterialPreviewPreparationCorrection/`。独立逐项核 26 ordinary 原/副本声明与实际副本大小/SHA，差异为空；加必要正式文件、治理和原固定 Workbench，共 35 唯一路径前后无漂移。未重新 hash 8842 环境文件或 528 链接；其数量及 metadata0 是原作者记录，不代表本评审逐路径 OS 覆盖。

| 固定文件 | SHA-256 |
|---|---|
| PreparationHandoff.md | 457f69fae412ae91e2876e479130b7495dec5df1c27f87d89ff0f1469f465603 |
| PreparationHandoff.json | 77cc0be978658f10e1be94ccca3376a229d2198b160e6497498ce239b91a5fba |
| PreparationOrdinaryManifest.json | f105f27b3f3efad3815d4f7b790f2b06a0222435501f21575b9a46cc5b0f2896 |
| PreparationSnapshot.json | a4a7290a1c30cdc63bfaede8ee3eb46e829ef89050deeebcb57eeeecec2d2f01 |
| ConnectionCasesPreview.mjs | e3760c8f4b8ba88cb66a55e69f8fb78a2ff1a459385237b7e711fea7b9ba747c |
| PreparationObservation.mjs | 127a2bafdbebd201f4461a884c821e54b702f1bc4cf9c3ac9d28e11c466506e1 |
| RunPreviewConnection.mjs | 48458a19709f7662142c0f7c08bed17031c7acb925e525e0a5d0dcdfdeb04600 |
| RunPreviewConnection.ps1 | c3d545c30572f4903fd46da7d92831578128e2ca3b1cf5bff0c20b8dbc0fc086 |
| PreviewInputIndex.json | ea9f3f28fe188786627ddd03fdfc5ef0897b072c5572b22f9a906a368332aaa0 |
| PreviewLaunchRequest.json | 1e80661b199a0129ca59801621a503aa0327df2351bbd2193ae172a2fc78a5a6 |
| Harness/Entry.tsx | e3b63ff891897f215a198b7c4c4e8312c8d8b58ee820dfe0eed27ddcf29b834b |
| Harness/index.html | 36b59355dac930d83486534ab56a5635597844f5ea2605ba511fb535e86bad58 |
| JUnitWriter.mjs（原样） | dfc3640f19e2e643dca1aa5ec5fab781f418d2dc30b95ff842dc882e1c1da6df |

本批准仅绑定以上准备版本和 index 所声明原范围，实际环境准入、唯一输出与执行由统筹另行判断。未读取热 Backend/native/Frontend 或改变任何实现、测试、标准。

## 独立语义核对

1. 原固定 Workbench 普通副本是 `G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/MaterialConnectionCorrectedExecution/WholeSourceClosure/SourceSets/Fixed/Workbench.tsx`，62262B，SHA `180f205942ee3185f213aa4da7a3ce6d5f2d06c4df9d3cf8b7bbde0558b3b5fb`。其 425 行素材编号位于没有 `open` 属性的 `details.advanced-settings`，summary 为“打开已有实例素材”。该副本与新 index 的原 runtime Workbench 声明大小/SHA相同，不通过读取热文件补证。
2. 新 Case 228–256 行仅修 M14 前置：在真实素材导航后定位该 details/summary/input；245 行记录点击前，247 行正常 `summary.click()`，248–249 行在原 5s poll 内要求实际 open、input visible/enabled，255 行记录点击后，256 行正常 fill。读取 tag/open/visible/enabled/value 只观察真实 DOM；没有 force、设置 open/value 属性、DOM 事件伪造、Query 写入或替换产品 hook。250–253 行失败观察不会吞掉原异常。匹配非唯一或缺失仍会由原 locator 操作拒绝，不能被观察记录冒充成功。
3. 新 Case 257–260 行保原目标：真正打开 asset-A，持有 A metadata 响应；必须等实际 held 请求，到 B 后主动释放 A，断言后续 `/content` 请求数为 0。原 Workbench 349–374 行的 openAsset 在 asset、metadata 和 content 各续步检查捕获的原 connection/instance/controller；这只是源码关联，尚不是新实际迟到响应验证。
4. 对实际新旧完整 Case 独立逆向替换新增前置，结果与原 20366B Case 整体文本相等；14 名称/顺序和 34 个完整 assert 调用逐字同序，原 13 个分支、M14 原目标及收尾均未改变。三份 FullDiffs 分别以实际新旧正文独立重建，字节相同，不只依赖 AssertionPreservation 的作者布尔字段。
5. 两个 runner 的实际新旧正文仅 task namespace、index 与 case/runner 文件名替换后相等。Node 106 行 240000ms sticky forced、113 行首个非 PASS 停止、123–127 行未执行/错误/强制收尾为非零；PS 80–83 行 300s sticky CLOSE 原 stdin、不 PID 重启，88–100 行等原 Process 终态/双 byte EOF并保持非零条件。Case 115/153 行原 5s 不增；观察准备并未降低目标断言。
6. 原 PreparationObservation.mjs 全文为 Query/DOM/connection 只读观察，M02/M05/M06 原 held-health 分支继续跳过 readiness 等待；M07–M09 B 新输入与真实 busy 前置继续保留。Harness 使用真实 ReactDOM、Query、Workbench 和冻结 SDK，经透明 loopback fixture 加测试标签；它没有给予真实 Owner/安装/Backend 权限。Fixture 的 goal_sha256/body-hash 行仍是透明旧样本，不能作为正式 Backend canonical 合同证明。

## 原证据等级与剩余范围

原 StaticToolTerminal 记录 metadata `1325ef/0`、四个 Node `--check` `b988c4/0` 和 PS ParseFile `20bf3d/0`；PreparationFinalizerTerminal `769a1f/0` 记录候选停止、reader/tool 空和 runtime execution0。它们只证明准备和语法阶段，不能证明 14 个业务机制通过。新 PreviewLaunchRequest 明确 `execution_authorized=false`、`needs_independent_oracle_review=true`，本报告没有覆盖或替换该门。

下一原 Test 只能按统筹另行批准的相同 Fixed/index/唯一新输出启动一次完整 14 项批次；保留原 held-health、B-held→主动释放 A→late target、unknown 原 body/key/assetset、disposer、M14 preview 全部目标和时窗。必须从新实际 Events/Result/JUnit/requests/终态独立核 M14 是否到达、实际 summary 前后和 metadata→切换→content 观察，不能从本次源码批准宣称迟到行为已通过。

完整 Owner/API/native/真实媒体/RAG作品包、安装、三 OS、Gate0/R1独立验收与随后 R2 均不在本准备范围。本报告不关闭这些缺项。

## 本评审过程

自有过程：`G:/开发测试/Codex/VideoCreatorImplementation/Review/MaterialPreviewOracle/`。`OracleFacts.json` 保存独立完整 assert/逆向正文/diff证明；`InputSnapshot.json` 与 `InputAfter.json` 保存35有限输入前后。自身展示工具 `c09524` 请求到439行但原 Workbench 仅437行，发生 IndexError/exit1且合并输出截断；原错误存 `OwnReadError.json`，`35a090/0` 只补读遗漏 Harness/formal 和必要349–374/425行，不执行测试，不将展示错误称产品红。最后独立解析工具 `37047f/0` 自然终态；所有源码读取结束，无 live reader。实际末正式写入工具终态在 FinalHandoff/Agent FINAL 单独记录，不以前置文件存在替代工具终态。
