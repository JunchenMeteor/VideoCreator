# RV60 — T42 固定 F10 React 恢复机制独立评审

结论：**SUPPORTED_LIMITED_REACT_UI_MECHANISM**。固定原 19 + 新 27 共 46 项实际通过及测试导入闭包修正，证据支持本轮透明 HTTP / storage 故障下的真实 ReactDOM、Query、F10 Workbench 与 SDK 机制。未发现本切片新增 P1/P2 阻断。新增 **RV60-I01 / P3** 是历史失败 JUnit 的格式缺陷；不改变 T40 原 NOTPASS，不否定可解析的 T42 新 XML，也不授完整产品资格。

## 固定输入与独立动作

- 正式根：`G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/WorkbenchRecoveryClosure-T42`。Handoff MD `0de10a4c4ce3c8bfc9af11712aa2698d095f68d1d027e4c0f5fb061234a85942`；JSON `3e00be97ae2bfb7fb18e3daa1be52df21a8ff6f4b8334285143f712ea8809825`。
- 普通根：`G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T42F10UIExecution`；manifest `92d9b4fef161d0fd4f6063af84dfa6c58a79d323c2bd45e0b27337e9162c3d14`。33 副本逐项大小/SHA 与 formal 原件声明匹配。
- 独立核 74 个必要路径，输入前后无变化。含 11 个 F10 固定源、四测试模块、旧 T40 必要原件、T42 原 raw/Result/XML/SDK/启动器；不重新扫描 8804 依赖或环境。完整输入在 [RV60Snapshot.json](G:/开发测试/Codex/VideoCreatorImplementation/Review/WorkbenchRecoveryExecution-RV60/RV60Snapshot.json)，逐项事件/请求事实在 [RV60FactsCheck.json](G:/开发测试/Codex/VideoCreatorImplementation/Review/WorkbenchRecoveryExecution-RV60/RV60FactsCheck.json)。
- Workbench SHA `6cc07b96c542668dbf3378efd88dcf8d3f0e64d7148fb21cf582cb6a5bad9b39`；useProjectEditor SHA `b1c085fcce215a2e90b035f6df45091bc5276661ffdb1991c6856e9f8ef8f573`。固定 SDK 通过 T42 alias 使用，无当前 SDK 替换。Review 没有执行 UI、Node、Test、产品、API、SQL、native、ASR、网络、安装或模型；费用与 key 读取均 0。

## 导入闭包与原失败保护

`CasesT42.mjs` 只重新导出原 `CasesT40.mjs`。原 19 `IntentCases.mjs`、原 27 `RecoveryCases.mjs`、`RecoveryFixture.mjs`、aggregator 四文件与 T40 普通源逐字节一致；Entry.tsx/index.html 一致。Run/观察器差异仅唯一 T42 namespace、index/批次/导出引用与 suite 名称；240s Node、300s outer、5s case/hold、15s navigation 阈值未降低。新增 2020B `native.frame.ts` SHA `fee1909d78f760035cfb95dfc7413cee1bdcf6cbf3aa17d311f0205772b04f6a`，其余七 SDK 文件与旧 index 身份一致。独立从 import/export/import() 语句解析得到 15 次语句引用、12 条唯一相对依赖边，八文件全部闭合；12 指唯一边，不是 12 条声明。

T40 原实际只有首项 setup error、HTTP 请求 0、行为断言未达，剩余 45 未执行；另有 1 runner boundary。原 `native.ts` 缺 `./native.frame.ts` 的 Vite 错误和原退出 1 保留，不能改称 46 项产品失败或已全绿。原 XML 有 47 个 testcase 文本标签（含 runner），但因 I01 不能称标准 XML 解析出的 47 节点。本轮补齐测试自持 SDK 导入闭包；不是改 Frontend 实现或测试断言求绿。

## 实际逐项与原始事件对应

T42 新 JUnit SHA `c6d5e2430c4e480b2347b93e11ccb27237ba6529259f596e9b827e2b350ecacd` 可严格解析：46 tests、failure/error/skip 各 0，46 名称/顺序与原 T40 arrival matrix、CaseCoverage、Result 一致。46 case_started / case_terminal 与每项 Result 的 outcome/duration/observed 完全一致，所有项 passed；无 not_executed、runner error 或 forced。

| 核验层 | 本轮可支持的具体事实 | 限制 |
|---|---|---|
| 实际入口 | createRoot/StrictMode、真实 QueryClient/Provider、F10 Workbench；首次公共 Entry warmup 一次后实际 browser DOM 导航，551 条 module response 均 200 | 没有真实 Owner 启动或 native Bridge |
| 原 19 | 9 种 unknown 故障后阻止改 body/key 重建；明确拒绝与真正未发送可允许新身份；导入 7 项保原 project/instance/staging/origin/body/key，当前 B 可显式重试原 A但不改绑，跨实例不得发送 | ZIP 为透明结构夹具，未验证真实 Bundle/授权 |
| 新 27 | 恢复原 A 时保 dirty B/当前 B task/草稿，回执先持久化再 GET latest run；旧 load/save/flush 成功、错误、finally 不提交当前新身份；取消 ABA 需新确认，迟到 ACK/取消与旧 finally 不解锁新操作 | 使用真实组件+透明 HTTP 和 storage 注入，不是 Backend 同步/并发证据 |
| 身份与存储 | 566 请求与原 events/Result 每项对应，全部正文 SHA 重算一致；同 intent 的完整 body/key/dispatch instance 均保持；storage 不可用前 0 POST，hash/instance 错误、错/缺 ACK、回执写入失败及后续拒绝保持 unknown | 合法 JSON 的字段篡改已覆盖；畸形 JSON 文本未加独立断言 |
| 审计边界 | 每项实际 DOM/assertion 成功后才生成 terminal；无 pageerror、外部请求/未知路由、Vite error；19 held route 显式释放，自动 hold 超时未被成功路径接受 | 迟到回包是这些有界场景，不覆盖无限延迟或多窗口竞态 |

实际 48 条 browser error console 与注入故障对应：原 19 共 27（reset10/5023/5038/4081/4091/4224），新 27 共 21（reset14/5036/4221）；25 request_failed 为 reset24、导航/流关闭 ERR_ABORTED1。保留原 fault console，不称干净无故障运行，也不以预期故障日志判业务失败。case duration 合计 85.656s；Result 开始到结束 88.962s；原 Node creation 到 wrapper ended 91.019432s，三个口径分列。

## 原进程与清理范围

真实执行 `ba7506/session94214 → d6d4d4` 自然 tool 0，Node 0，wrapper CommandReceipt 0，stdout/stderr 两字节泵实际 EOF，forced=false、errors=[]、no_restart=true。原 Node Process 引用 PID3208 / creation `2026-10-09T12:00:37.0733502Z`；Node 原 BrowserServer.process() PID47824 / creation `2026-10-09T12:00:39.8011544Z` 与独立 .NET observation 相同。Browser 原 close event code0/signalnull，观察器同 PID/creation has_exited=true，Vite.close 完成，原探针本机 HTTP65259 / Browser53001 closed=true。

这支持本测试 Node/browser leader 的终态和两端口收尾，不证明 Job containment/全后代无泄漏。portClosed 实现将 connect error 记 closed，未保存精确 socket errno；不能升级为精确 ECONNREFUSED 或全部 Windows 进程资格。InputBefore/After 原 guardian 声明 8804 records/528 links/changes[]，源读守卫在运行前后核 byte/hash/realpath；两 55B 输出是计数与变化摘要，不是独立逐文件 before/after 向量。Review 只核 74 必要路径，不冒称重核全 8804。最终准备/复制 `a79193/e9c263` 自然 0 为交接工具，不冒充额外 UI 测试。

## RV60-I01 — P3：原失败信息中的 ESC 使 JUnit 不符合 XML 1.0

归属 **Test**。固定 [RunT40.mjs](G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T40F10Original/ConsumedSources/RunT40.mjs:120) SHA `e483035eb3cb952c0ef190367dd234e771c6ece3a75320407a63945376781c8e`，以及继承的 [RunT42.mjs](G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T42F10UIExecution/ConsumedSources/RunT42.mjs:120) SHA `c0514f54f27c4959885413e0460a9cd92b5b39ce3f8f88fafc15265173b91f22`，第 120 行 escape 只处理 &、<、>、引号；121 行把 Playwright error/runner error 直接写入 XML。触发：错误文本含 ANSI ESC，例如 T40 实际 locator 超时的 `\x1b[2m`/`\x1b[22m`。固定 [原 JUnit.xml](G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T40F10Original/F10RoundOne/JUnit.xml) SHA `9d8e994cd6b84f700299b46bc4fe35a64f7628ec770c7cf9d1a604d52402a3dd` 的 byte offsets244/303 为 ESC(27)，strict ElementTree 报 line3,column0 invalid token；47 仅文本标签数。

影响：失败报告可能不能被标准 JUnit consumer 读取。原 Result/Events/raw 仍保存完整失败，T42 全绿 XML 本身合法；不作为本 46 项通过阻断。最小整改条件：原 Test owner 后续仅修 writer，在 XML payload 对 XML1.0 非法控制字符作显式可读转义/清理并保留原 raw；新增失败正文含 ANSI/control 的纯 writer 反例及 parser 验证。**不覆盖或重写这份原失败 XML，也不重跑原 UI 求绿。** 本轮仅静态/既有字节事实，无新产品实验。

## 尚未支持与最终范围

- 真实 GET/SSE 的 run path 已核；fixture 发错 run event，但缺单独 DOM 断言验证坏事件未渲染，不能说 SSE 错 run 过滤通过。
- 模态确认经真实 health instance 改变被清除；同实例底层 navigation inert/强制导航未测；畸形 storage JSON 未测。
- 一次 fresh Entry warmup 不确定原 cold setup 的其它根因；不能回填原 T40/T37 setup 红。
- 没有真实 Backend/API/Owner/MCP/权限/回执事务、媒体/ASR 精度、native/Job/OSkill、多窗口、安装/三 OS、商业订阅/授权发布或 R1/R2完成资格。完整三 OS R1 独立验收后继续 R2，不缩水；五步前台和数据实例持有不变。

本轮所有固定 input readers 已释放，Review 实际工具终态后以正式 Handoff 交接。未修改实现、测试、标准或原失败。
