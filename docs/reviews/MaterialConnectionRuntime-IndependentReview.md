# MaterialConnectionRuntime 独立有限评审

结论：**LIMITED_COMPONENT_EVIDENCE / NOTPASS**。Old 的跨连接错误发送已由实际请求证明；Fixed 的 M01–M06 有真实 React/Query/Workbench/SDK 组件支持。Fixed M07 失败在未建立的准备谓词处，M08–M14 未执行，不能据此宣布完整 GMNR-P01 或晚到回包保护通过，也不能把 M07 当作已经复现的前端缺陷。

## 固定输入与读取范围

只读取 MaterialConnectionOld / MaterialConnectionFixed 的 52 / 55 普通件、10 正式交接件、3 治理输入，共 **120 个独立路径**，最终大小与 SHA-256 全部一致。原执行索引 8773 文件与 528 链接的前后记录已读；本评审没有重扫、复制或重新验证整套运行环境。完整 14 个产品模块的字节身份与两版本差异独立比对：只有 `engine.ts`、`Workbench.tsx` 变化，其余 12 个相同；完整两文件 diff 已保存。完整 14 case、runner、PowerShell 原进程包装、Harness、相关 Workbench / engine / Goal / editor / SDK 调用链已读。其余完整模块副本保留在索引，本结论不等于对整个产品所有页面作功能审计。

Fixed 正式 Handoff.md SHA：`c1c7fc4d91c8397e99db1a30dd6d8a8355afcb0c0d663a268f58c1f5c2f8ce42`；json：`f7c410e82ddfc156ed4dacd04aec4c27c98c92c7cc396f80125c40ce511978d3`。全部原件路径与完整 SHA 见自身 `FormalInputs.json`、`OrdinaryInputs.json`、`InputAfter.json`；差异见 `IndependentProductDelta.json/.diff`。

固定根：`G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/MaterialConnectionFixed/` 和 `MaterialConnectionOld/`。自身过程：`G:/开发测试/Codex/VideoCreatorImplementation/Review/MaterialConnectionRuntime/`。

## MCR-P01：准备判据依赖未建立的 Goal 条件

**P2 / TestDevelopment / OPEN_TEST_PREPARATION**。固定 `ConnectionCases.mjs` SHA `32f2376813f804d43d8fcd063a3fabad7c995fffa9e011de3137ee1d593f6a43`，182 行把“开始创作” enabled 当作 “new B health ready”。156–157 行只填写初始 A Goal；175–181 行切换 B 并关闭导入弹窗，没有填写 B Goal；实际填写后续 Goal 的 helper 在 134–138 行，要到 191 行才调用。

相关真实源链：Fixed `Workbench.tsx:49–58` 用 connection epoch 请求 health，再把实例传给 editor；`useProjectEditor.ts:6,15,46–64` 允许新实例恢复独立草稿或空 Goal；`NativeSetupView.tsx:14–19,75,128` 的提交按钮还要求合法 API context、非 busy / setup busy / uncertain / pending / native-block，以及 **非空 `form.goal`**。因此按钮 enabled 不是单纯的 health-ready 谓词。这是可明确归属测试准备的源码缺陷，不需要修改产品安全门或延长 5 秒来解决。

实际 Fixed M07 的错误为 `Original5s condition bound: new B health ready`，栈指向 `ConnectionCases.mjs:182`。原请求记录确有 B 的 health/projects/productions GET，保存 UI 文本含“本地实例”；没有 B 新文件 staging/import POST，也没有 Goal POST。没有独立保存该时刻 `#creative-goal.value`，故不能宣称观察到了具体空值或断定是哪一个 disabled 条件实际生效。183–191 行的新 B held staging、主动放行 A、旧回包不得覆盖 B / 清 busy / 发 B-only Goal 等目标均未到达。M07 的 A import 响应于 06:04:19.231Z 被 **case finally 清理**放行，不能作为目标窗口断言已经执行的证据。

同一复合谓词继承于 M08/M09 共用分支及 M10:193、M13:211；这些 case 本批未执行。不能把它们的准备问题或行为结果记为已经复现。

归属者最小修订要求：保留原 14 目标、原 5 秒、原失败、first-red 和完整源绑定。若后续确实需要 B Goal，通过真实 DOM 明确填写、读取新实例 Goal，再检查合法按钮前置；若这里只准备素材阶段，则依据真正当前 B connection epoch / identity、实际完成的 B health 与可用文件入口建立准备条件，不借复杂 Goal 按钮代表单一 health。保存真实 B 表单值和连接/响应事实，不注入 Query cache、伪造身份或直接改 React 状态。准备成立后仍须执行原 B held staging、主动 A 放行、success/error/finally、B-only asset IDs 断言。修订以新固定 namespace 和单独运行授权推进；Review 未修改或运行它。

## 原实际结果与未到达范围

| 批次 | 实际 case | JUnit 原节点 | 原整体退出 |
| --- | --- | --- | --- |
| Old | M01 PASS；M02 assertion failure；其余 12 NOT_EXECUTED | 15：1 pass / 1 failure / 13 error / 0 skip，其中 12 未执行、1 runner incomplete | 1 |
| Fixed | M01–M06 PASS；M07 interaction failure；其余 7 NOT_EXECUTED | 15：6 pass / 1 failure / 8 error / 0 skip，其中 7 未执行、1 runner incomplete | 1 |

Old M02 实际 B `POST /api/v1/assets/staging` 收到了原 A 的 70 字节，SHA `7bfad5da296ca6ed4f035fd65159fd909131fc3ae65cd57cf52407b3ea715069`。透明 fixture 在记录真实请求后拒绝外来正文并留下 HTTP 500 / handler error；不能把这一响应当作真实 Backend 故障，也不能抹掉之前的错误发送。Old M02 的 Query cache 前置断言执行且未失败，但失败后没有独立 cache 快照，限制保持。

Fixed 六个 PASS 分别支持：M01 真实导入/选择后 Goal 引用 asset-A；M02 缓存 A health 时不向 B 发送旧文件；M03 A staging 晚到不在 B 跟进 import；M04 A→B→A 不复活旧 staging 生命周期；M05 同实例 principal 更换退役旧文件；M06 同 client 新安装退役旧文件。这些是透明本机 HTTP fixture 与真实组件的机制覆盖。每个 reached case 的 Result request 行与实际 Events 字段逐项相符。M03/M04 的有限后续观察包含原源码的 60ms 断言窗口，不能外推任意长时间所有竞态。

M07 的晚到 import success 目标、M08/M09 error/finally、M10 外来已知 asset IDs、M11 同连接重试正文/rights、M12 原 unknown Goal body/key/asset set、M13 旧 disposer、M14 旧 preview metadata→content 均不能记为本批运行通过。Fixed source 为这些材料操作加入不可变连接对象、当前连接检查、回包/后续发送检查、实例和 mount 关联；源码支持与实际未到达的窗口分列。

原第一阶段加载/浏览器启动限制没有隐藏：`ConnectionLaunchRequest.json` 的准备 `execution_authorized:false` 保留，不能据这份请求本身推出权限授予；本评审只确认另已正式交接的原实际执行。原 outer PowerShell 全 raw 与 browser pre-launch raw 未捕获，不用后置日志补写这些缺口。

## 原进程与清理证据

Old Node PID 24928，creation `2026-10-10T05:58:33.5743740Z`，原 retained Process handle 2120，原工具 728747/session81609 → 9097c1 自然 1；Fixed Node PID 36740，creation `2026-10-10T06:04:03.0362811Z`，handle 2204，40d4ab/session38657 → b36ba7 自然 1。两份原 CommandReceipt 均 `actual_terminal:true`、stdout/stderr EOF、forced false、no restart、errors 空。Node 的 stderr 原 0 字节；stdout 原实际结果 JSON 已解析，未把字段 bool 当作全目标通过。

Node 保留 `BrowserServer.process()` 原 child，Old browser PID35556 / creation05:58:36.2364340Z，Fixed9696 / creation06:04:05.6606480Z，原 terminal code0 / signal null / close_event true。PowerShell 的 GetProcessById 是明确的独立 observer，不是创建者句柄。原 Vite close 及 assigned HTTP/browser 两端口关闭分别为 Old64537/64540、Fixed51741/51745；不宣称所有浏览器孙进程或 Windows Job 全部验收。后置 BrowserStderr 已完整读取，仅 Vite/React DevTools 信息，不把后置读取冒作 pre-launch raw。

Test 的 finalizer 自然 0 和 reader release 是交接终态，不能改写两组执行总体 1。自身纯解析有一次大输出截断，遗漏 diff 尾段与必要字段已定向补读；原显示截断保留，不称产品失败或重跑原绿。

## 有限裁定与后继

GMNR-P01 有源码机制及 Fixed M01–M06 的局部组件支持，**保持 PARTIAL**，原完整 14 窗口未闭合。MCR-P01 归 Test 准备谓词修订；本批没有据未到达断言确认新的 Frontend 运行缺陷。真实 Backend 权限、Owner、安装/native、媒体、资格生产者、三 OS、完整 R1→连续 R2 未由本批证明。透明资产与 fixture Goal hash 不能成为真实许可或服务端 canonical Goal hash 算法；不得比较前端 JSON.stringify hash 与未规定相同语义的服务端 hash 来拒绝合法回执。

本 Review 没有启动或导入产品/Test/vendor、重跑原批、修改实现/标准/阈值、读取秘密或收费。正式报告对应的全部固定 reader 在末核后释放；工具 natural terminal 由最终交接实际 chunk 补充，未等待后继实现或资源。
