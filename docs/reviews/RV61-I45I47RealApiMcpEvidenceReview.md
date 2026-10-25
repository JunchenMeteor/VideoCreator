# RV61：I45 HTTP / I47 MCP 有限真实接口证据评审

结论：**SUPPORTED_LIMITED_REAL_INTERFACE_ACCEPTANCE**。固定证据支持 I45 的 18 项 SDK/HTTP 检查，以及 I47 的 33 项协议与业务检查；没有新增 SOURCE_STATIC P1/P2。**I45 原批 overall exit=1 仍为 NOTPASS，I46 原启动失败仍保留；本报告不授完整运行资格或 R1/Gate 通过。**

## 身份与方法

Review 只解析已有普通副本、原始回应、原收据和必要固定源码，未执行产品、测试、数据库、模型、ASR、DLL、OS 观察或收费。39 个 I45/I47 ordinary（22+17）、5 个必要 I46 原红 ordinary、10 个必要固定 B28 源码，以及正式/治理文档共 **70 路径**，输入前后 bytes/SHA 均一致。I45/I47 记录的完整固定源名单均为 53；其观察向量分别为 72/77 且无变化。547/768 是执行者保存的已加载模块文件记录数，不是 Review 重新盘点或资格验证整个环境。

正式来源根分别为 `Integration/CurrentEngineApi-I45`、`Integration/CurrentEngineMcpLoader-I47`、`Integration/CurrentEngineMcp-I46`，均在 `G:/开发测试/Codex/VideoCreatorImplementation/` 下。ordinary 路径由各自 OrdinaryIndex 的实际条目解析，未猜 stderr 名称或读取当前 B29 生产源。

| 输入 | 实际 SHA-256 |
|---|---|
| I45Handoff.md | 779a89e1885f09385c8b65dadb6b49ff679aa4e969efd3590ca2442438cf9402 |
| I45Handoff.json | b9c5d662854c6dd69b8f1e3ed246f5faad7d543a7426fc750cbcba0d44f138ec |
| I47Handoff.md | c5f27ed56e903b877fef2a0243d7aae2c834e0019e96140dcab65ddac927315b |
| I47Handoff.json | ad6923c0e4543f1a79f7500666263cbd54f0520a4c937d921077febf78afe00f |
| I45 原 CommandReceipt | a7886f72c4de3a9f32f0d146582da899d90f9057fed169d4f062743b5583e1af |
| I47 原 CommandReceipt | e92f3bcd8588a04fb0e9045c85a93b371c820a31def1085b829ca28102ad5fce |
| I46 原 CommandReceipt | 0d0dff0ee67f4642323df1ecaca4d97a6d35045698050ae48c31121355333bf8 |

## 可支持的实际范围

**I45。** 原 SDK 收据 18/18 passed、SDK actual exit=0。真实请求覆盖健康、错误 token 401、空请求 422、Project 创建/读取、production 创建、显式默认值重放、同 key 改 body 409、取消及取消后原受理快照重放、普通会话访问管理接口 403。生产受理状态为 `waiting_user`；取消后当前详情为 `cancelled`。三个 HTTP 原响应 `ProductionAccepted/Replay/ReplayAfterCancel` 的 502 字节完全一致，SHA 为 `adf7a9e5c8929cac64d89680f3d75c0a06f996c5c8f304c49da7662fd995e2bf`。这支持原受理快照与当前 Run 状态分离，而不是取消无效。

API 和 SDK 原 Process 均自然 exit=0、两输出 EOF、无强制/超时 sticky；API 原 stderr 有唯一精确 `api_stopped/scope=api`。原 runner 对端口 63757 的关闭观察为 `timeout_not_closure`，connection_refused=false，故整体 **exit=1**。独立 AfterObservation 在后续时刻无该端口监听、保存的两子进程当前不存在，actual exit=0；它只支持后来的状态，不回填原窗口，不将原整体改绿，也不证明全 Job/重父化后代。

**I47。** 原实际 JSON-RPC 初始化返回 `2025-11-25`、VideoCreator `0.3.0-candidate`；发现 12 工具。33 检查由 **24 个回应协议检查（8×3）+9 个初始化/发现/业务检查**组成。9 请求帧含 initialized 通知，8 有 id 回应；6 个 tools/call 仅实际调用 `production_create`、`production_get` 两类。未测其余 10 工具。

逐行原 stdout JSON 与 8 个保存回应语义一致。无授权帧得到 `mcp_session_invalid`，授权空参得到 `invalid_request`，同 key 改目标得到 `idempotency_conflict`；错误经合法 ToolResult 的 `isError=true`、文本内容和 structuredContent 表达，不误记为 JSON-RPC transport error。受理与 GET 绑定同一 instance/project/production/run，状态 waiting_user、operations 空、BundleRef null，spent/reserved 的十进制文本均为 `0`，允许路由为空。未调用 provider 或生成媒体。

同会话受理重放的 **structuredContent 相同**，响应 id 不同，两个保存回应 SHA 分别为 `1c13ab734eb6370987d2352e00c0daa218d23122994308c8368093ef4a3eeecd` 与 `cf0e9d447764253ab1cc870ace85e2a5c958f03f300ac37fa15f2607c4c20478`。保存回应是解析后重新格式化的 JSON，stdout 是解码后按 LF 记录的行；不宣称原整体 wire byte 相等，不宣称跨会话或重启恢复。

I47 原 runner/child 自然 exit=0、两个 EOF、无 force/timeout/errors；protocol stdin 已关闭，原 stderr ready/stopped 诊断与收据对应。stopped 的 `process_exit_pending=true` 本身不能证明退出；真实 Process exit 和后续保存身份观察提供本批有限退出证据。EOF 不等 Worker 取消、HTTP shutdown 或 Windows Job 完整清理。

## 固定真实委托源码

必要源全部来自 I44 `FinalSourceCopies/services/engine/src/video_creator/`，不是当前生产源。MCP CLI 真实构造 Engine/BundleService 后启动 stdio；`integrations/mcp.py` 的 TypeAdapter、授权主体提供器和 `_invoke` 委托 `BundleService.create_production/production`。`bundles.py:1401–1407` 比较当前 principal 与 instance 并检查 operation/purpose；`1456–1472` 再检查项目归属并进入 Engine。

`engine.py:338–409` 在同事务进行原 key/body 查询、请求解析、项目/资产/预算关联、受理与 commands 快照保存。`421–434` 的真实证据策略解析/执行 guard 没有被测试请求伪造；当前无资格资源产生 waiting_user，不是已自动完成创作。`249–336` 的原快照校验与 `442–455` 当前详情、`834–853` 取消分支相干。API 管理访问 `api/app.py:135–142` 独立拒绝普通会话；本批 local-owner AccessContext 不证明真实人类 Owner/production capability。

MCP stdio 逐调用读取 `_meta.authorization` 并核验当前会话/实例；runner 正向使用私有内存 session token，记录请求时去掉 `_meta`。Review 未读取 token/environment/private stdin 或其 hash。Bundle export 线程 start/stop 和 CLI 清理确有接线，但本批无 export job、无 worker；不得据线程代码或空队列声称 Bundle 完整发布/许可链通过。

## 原红、修正及剩余边界

I46 原原生导入失败：initialize 已发送但 response/stdout=0、CLI 自然 exit=1、stderr 为 `ModuleNotFoundError: pywintypes`。固定 launcher 使用 `-I -S` 并只加 SOURCE/SITE，遗漏已有 pywin32 的三个路径/指定 bootstrap。I47 的普通 diff 只增加这些显式路径、精确 bootstrap 与自身命名空间；断言逻辑保留。实际记录 pywin32_bootstrap/_win32sysloader/pywintypes313.dll/win32api/win32job 来源支持此开发入口修正。它不证明包发行、完整 native floor、DLL 信任、许可或真实 Job 行为。I46 原红不删除、不合并为原批通过。

没有重启、crash/OS kill、unknown 费用恢复、真实 Owner、生产授权、模型/媒体/ASR、发布 Bundle、installer、三 OS 或支付/发布实测。HTTP/MCP 一次受理接口现有有限证据成立；自动持续制作、完整五步工作台、本地数据交付及独立 R1→连续 R2 完成仍需后续独立验证。本报告不代 Test/Acceptance，不批 RuntimeBinding、技术 Gate 或分发。

自身解析 AttemptOne 因误期待金额文本 `0.000000` 而 actual exit=1，原实际文本为 `0`；已记录为 Review 解析假设错误，只改自身解析器并以 af692e actual exit=0 收束，未改产品/测试/原证据。

## 正式过程证据

- Snapshot：`G:/开发测试/Codex/VideoCreatorImplementation/Review/RealApiMcp-RV61/RV61Snapshot.json`，SHA `fcc88e31a8c63825aa3f21c1f2fd8863608ce65efbc71307c61a8a9d2f34addf`。
- FactsCheck：`G:/开发测试/Codex/VideoCreatorImplementation/Review/RealApiMcp-RV61/RV61FactsCheck.json`，SHA `a0643c91330a04f3d45bb9d91176ccbc2919ceeeccf567673c413574144825d0`。
- InputAfter：`G:/开发测试/Codex/VideoCreatorImplementation/Review/RealApiMcp-RV61/RV61InputAfter.json`，70/70 无变化，SHA `4cde19f9ade56c26649e0f3c87dc777394a56eb169c3371bc28dadff5b9c2feb`。

全部固定源码 reader 已释放，无产品/测试持有进程，无 live 工具待 poll；最后读/解析 af692e actual exit=0。正式交接只含本有限切片。
