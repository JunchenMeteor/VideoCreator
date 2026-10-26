# ADR0085：R2 非外部依赖部分的窄设计（模型设置 / 费用可见 / 发布前授权）

状态：ARCHITECTURE_FROZEN_DESIGN_ONLY，2026-10-26。只冻结 R2 中**不被外部条件阻塞**的三块：BYOK 与官方两种能力来源的产品面（FR02 剩余部分）、每步用量与费用的可见性、发布动作的独立人工授权。**本卡只写文档**：不改源码、不改迁移、不改契约、不写测试、不产出安装包、不生成账号。§10 的用例全部 **NOT_EXECUTED**。

上游事实：R1 已打 tag `checkpoint/2026-10-26-r1-complete`（安装、授权、静音/语音作品、HTTP 与 MCP 单次交付闭环）。R2 依赖的真实平台账号、支付与订阅额度、平台发布接口**在本机不存在**，不得用模拟替代（`docs/task-board/CurrentCapabilityInventory.md:187`）。本卡把 R2 拆成"S 面＝可做"与"X 面＝缺条件"两部分，只设计 S 面，并把 X 面的**产品表现**固定下来，避免"假装成功"。

## 0 实读证据（行号取 HEAD `4e218ec`；`vc/` = `services/engine/src/video_creator`）

| 事实 | 位置 |
| --- | --- |
| 规格：厂商账号不是本地创作前置；官方不可用不影响已有项目打开/修改/本地合成/导出 | `Documents/VideoCreatorSpecification/01-项目需求文档.md:9,16` |
| 规格：本地模式测试连接/项目打开/镜头编辑/预览/合成**不得**访问厂商认证服务器 | 同上 `:81` |
| 规格：每步保存能力来源（自有远程/自有本地/官方），用户设默认路由与允许回退，不得偷偷切到官方付费 | 同上 `:79` |
| 规格：调用前展示估算或标注无法估算；调用后区分估算/实际/未知费用 | 同上 `:83` |
| 规格：模型设置＝能力来源、测试连接、费用、数据目的地；错误"不显示0元" | `06-界面与交互规范.md:63,91` |
| 规格：制作授权与发布授权独立 | `09-自动制作与多模态交付规范.md:24` |
| 规格：`model_selection=auto_within_allowed_routes`；`allowed_provider_routes` 是硬边界；记录 `ModelRouteDecision` 与回退理由；金额为十进制定点，记录估算/预留/实际/未知 | 同上 `:165,167` |
| FR02 在需求映射里属 R1，但 R1 关账时只有后端机制、界面未接通 | `docs/requirements.md:19`；`docs/task-board/ProductDirection.md:24` |
| FR16 无发布授权不得发送；发布授权/草稿/受理/成功分别验证 | `docs/requirements.md:33,46` |
| 官方凭证只由 Gateway 持有，个人 BYOK 凭证不充当官方资源 | `docs/commercial/official-provider-admission.md:11,13,19` |
| 后端凭证保险库**只**接受 Windows/macOS/SecretService/kwallet，弱后端 503 | `vc/infrastructure/credentials.py:29-35` |
| `SecretHandle` 的 `__repr__`/`__str__` 已做脱敏 | 同上 `:13-26` |
| 唯一的密钥导入实现读**文件路径**并写 OS 保险库，返回 `vault:<id>` | 同上 `:37-49` |
| `resolve` 支持 `vault:` 与 `env:VIDEO_CREATOR_SECRET_*` 两类引用 | 同上 `:51-66` |
| `store_secret` 自述"trusted startup only"；`load_secret`/`remove_secret` 目前唯一调用者是本机自签证据 | 同上 `:75-109`；`vc/application/local_evidence.py:145-150` |
| 凭证导入今天只有终端子命令 `credential-import`（打印 `stored_in: os_vault`） | `vc/cli/main.py:149-152,261-263` |
| `api/app.py` 没有任何凭证、设置、路由清单或费用接口（routes 全表已核） | `vc/api/app.py:206-594` |
| 路由登记今天只有可信配置路径：引擎方法 + 终端 `register-route` | `vc/application/engine.py:240-247`；`vc/cli/main.py:271-273` |
| `register_route` 只校验 `verified`，并对 `source='official'` 直接 503 | 同上 `:242-245` |
| 未登记路由执行即 503 `route_unavailable`（且在等待码集合中） | 同上 `:249-254` |
| `CapabilityRoute` 的 destination 禁止内嵌账号/口令/query/fragment；远程必须 HTTPS；本地必须 loopback | `vc/domain/contracts.py:301-326` |
| 选路门：不在 `policy.allowed_provider_routes` 或行缺失 → 403 `route_denied`；未验证/官方 → 503；远程无外发授权 → 403 `transfer_denied` | `vc/application/engine.py:685-699` |
| `official` 在四处被硬拒（登记、policy 安装、创建模板、选路） | `vc/application/engine.py:244-245,694`；`vc/application/production_authorization.py:108-109`；`vc/application/daily_projects.py:312-313` |
| 引擎在受理时**不覆盖**调用方给的 `policy`（只补格式版本与交付要求） | `vc/application/engine.py:500-503` |
| 目标/模板路径把 `policy` 写成模板里的 routes，并**强制** `automation.mode='unattended'` | `vc/application/daily_projects.py:621-632` |
| 模板安装需要 management principal（`_principal` 无管理即 503） | 同上 `:395-398`；`vc/application/production_authorization.py:37-41` |
| `bind_request`（策略绑定）只在 `unattended` 受理时调用 | `vc/application/engine.py:467-480,735-738` |
| 预算门：reserve＝该 route 的 `max_operation_cost`；超任务上限 402；付费且无预算组 403；超共享组 402 | 同上 `:739-753` |
| 预算组只能由可信配置创建（唯一调用者是终端 `authorize-validation`），且 cap 不可改 | 同上 `:230-238`；`vc/cli/main.py:264-270` |
| 结算：reserved→spent 以 `actual_units` 落账；unknown/超预留 → `needs_reconciliation` | `vc/application/engine.py:831-851` |
| `budget_status` 返回 cap/spent/reserved，但**未暴露为 HTTP/MCP** | 同上 `:1064-1069` |
| `Money` 是 CNY 定点（六位小数，`units()` 微单位），拒绝 float/bool | `vc/domain/contracts.py:42-67` |
| `OperationSummary` 有 cost_status/actual_cost/cost_evidence/external_id，**没有** usage 字段 | 同上 `:213-219` |
| `ProductionCost` 只有 spent/reserved；`ProductionDetail` 聚合 operations | 同上 `:222-232` |
| `cost_evidence` 四值：provider_receipt / usage_price_calculation / confirmed_no_charge / unknown，且与实际费用必须同空同有 | 同上 `:337-348` |
| 价目规则只有两条字面量（`deepseek-flash-peak-20261007-v1`、`kimi-k2.6-cn-20261007-v1`），未知规则 503 `price_rule_unavailable` | `vc/application/pricing.py:10-16,19-37,93-95` |
| 供应商账单回执**目前无法采信**：见到 `provider_receipt` 即 409 `receipt_verifier_missing` | 同上 `:74-78` |
| 实际费用只能来自 usage×价目或 confirmed_no_charge，否则 409 `cost_evidence_missing` | 同上 `:79-86` |
| 驱动失败：本地零成本/无凭据/`local:` 路由重抛原错误，其他一律 `unknown` 且不重交 | `vc/application/executor.py:22-31,62-79` |
| 密钥只在不可逆派发前解析一次，交给驱动的是 `SecretHandle` | 同上 `:57-63` |
| 授权通道的 kind 白名单当前两值：`owner_initialize`、`local_evidence_policy` | `vc/application/product_authorization.py:73` |
| 非 Owner kind 必须由专用构造器给出精确 scope（不允许默认 scope） | 同上 `:726-738,841-871` |
| `approve` 按 kind 分派；自签证据分支只写审计+收据，不写证据行 | 同上 `:937-982,984-1000` |
| 正常装配进程只开放 `local_evidence_policy` 一种 kind；受限进程只开放 `owner_initialize` | `vc/cli/main.py:521-537` |
| 授权路由只在 restricted 进程挂载；`/health` 带 `X-VideoCreator-Authorization` | `vc/api/app.py:206-240` |
| 校验失败的错误信封不回显输入（防密钥/私文外泄） | 同上 `:200-203` |
| 前端已有 `product-authorization-ui-v1` 视图与 kind 标签表、scope 隐藏键过滤器 | `apps/workbench/src/productAuthorization.ts:18,292-306,336` |
| 工作台设置页只有 4 张只读卡片，无模型来源、无测试、无费用、无目的地 | `apps/workbench/src/Workbench.tsx:456` |
| 制作页/任务页费用只有一档文案："费用待核实" 或 "已记录 CNY n" | 同上 `:450`；`apps/workbench/src/ProductWorkspaceView.tsx:206` |
| MCP 15 个工具里没有发布、设置、凭证或预算工具 | `vc/integrations/mcp.py:52-70` |
| 交付（导出/引用授权）是 R1 既有路径，与平台发布无关 | `vc/api/app.py:511-535`；`vc/domain/contracts.py:1253-1305` |
| ADR0081 把"对外发布/导出授权、付费提供方启用、unattended 预授权"列为 R2 只登记不设计 | `docs/decisions/0081-product-authorization-channel.md:115-121` |
| ADR0082 已确立"授权只批范围 + 一次性子进程执行"这一形态 | `docs/decisions/0082-local-self-issued-evidence.md:161-171,183-184` |
| ADR0083 明确"不新增 HTTP/MCP 可达的路由写入口"，且路由属"配置事实"不属授权 | `docs/decisions/0083-installer-provisioning-and-first-run.md:128,137,153` |
| ADR0084 授予"制作/发布本地包"，不授予 management；权威不替代同意 | `docs/decisions/0084-product-trusted-startup-authority.md:212-229,252` |

### 0.1 六件必须核清的事（结论）

1. **FR02 的"模型设置"不是从零开始，缺的是产品面而非机制**：凭证保险库、`vault:` 引用、`credential_ref`、路由表、选路门、预算门、价目规则全都存在（上表 credentials/engine/pricing 各行）；缺失的是"页面能写凭证、能列来源、能测试、能显示去向"的接口。因此本卡不新造第二套凭证机制。
2. **官方能力不是"没接通"，是"准入未完成"**：`official` 在登记、policy、模板、选路四处硬拒（上表对应一行）。本卡不设计官方计费与官方凭证，只设计"官方不可用时如何诚实地不阻塞本地、不假装可用"。
3. **BYOK 写入口有两个真实缺口**：①凭证无产品写入路径（唯一实现是读文件的终端子命令）；②路由无产品写入路径（`register_route` 只由安装器/终端调用，ADR0083 §2.4 明确禁止新增 HTTP 写入口）。本卡必须为②给出**不越权**的形态，否则"配置自己的模型"在安装形态下永远不可达。
4. **费用账本已诚实，缺的是展示与上限预览**：`reserved=route.max_operation_cost`、`spent=actual_units`、四值 `cost_evidence`、回执无 verifier 即 409、未知即 `needs_reconciliation` 都已实现（上表预算门/结算/`budget_status`/价目/回执各行）。缺的是"提交前看见上限/看见排除原因"和"预算/额度可见"的只读面。
5. **授权通道是可扩展的单通道**：kind 白名单两值、按 kind 分派、`product-authorization-ui-v1` 视图、前端标签表都已存在（上表 kind 白名单/构造器/approve/装配/前端视图各行）。新增 kind 是"加一路作用域与一支审计"，不是新开一条授权通道。
6. **目标/模板路径与直接受理路径的门不同**：目标路径强制 unattended 且 policy 来自模板，模板安装需要 management（上表日模板与 `bind_request` 各行）；直接 `POST /api/v1/productions` 使用调用方 policy，引擎不覆盖（上表 `_resolve_request` 一行）。本卡据此把 BYOK 的**生效面**限定在"显式列出路由的交互式请求"，并禁止把 BYOK 偷偷并入模板。

## 1 结论摘要

1. **S/X 切分**：S1 模型设置、S2 费用可见、S3 发布前授权＝本卡范围；X1 平台账号、X2 支付与订阅额度、X3 平台发布接口与回执、X4 官方 Gateway/control-plane、X5 供应商账单回执核验器、X6 任意第三方供应商的"自报价目"＝**不做**，且每条在 §8 固定"缺条件时的产品表现"。
2. **BYOK 凭证只在 OS 保险库**，只经一条产品写入路径进入，只被 `OperationExecutor` 在派发前解析一次；密钥永不进库、日志、事件、审计原文、作品包、导出、页面存储（§3）。
3. **来源选择只在确定性裁决器一层生效**：模型只能建议，`policy.allowed_provider_routes` 是硬边界；官方缺失在**提交期**具名，不进入本地制作路径（§4）。
4. **BYOK 远程路由的登记走"授权范围 + 一次性 route-admin 子进程"**（同 ADR0082 形态），不授予 management、不改 `register_route` 签名、不写 Owner/floor/policy（§4.3、§9）。
5. **连接测试在同意之后、登记之前**，只发协议元数据或固定字面量 `ping`，不发素材/提示词/目标/资产 id；失败八码具名；`verified=true` 只表示"端点与鉴权在该次测试时成立"（§5）。
6. **费用只从账本读，不从页面算**；提交前只展示"上限与口径"，不展示编造的总估算；未知费用一律"待核实"，绝不显示 0（§6）。
7. **发布是一次独立的人确认**，复用 ADR0081 四项凭据与"审计先行"，新增 kind `publish_release`；approve 只批范围，实际发布由平台适配器负责，而适配器在 X 面不存在时以 `publish_unavailable` 具名失败（§7）。
8. **`MCP/API 调用方结构性无法发布**：approve 需要启动器注入的会话 secret，MCP 与第三方调用方从不持有（§7.8）。
9. **零放宽**：`register_route`、`install_startup_services`、`assemble_owner_services`、`ProductionAdmissions`、`management_access`、`_route_guard`、预算门一行不改；不新增表/迁移（§9、§12）。

## 2 交付面与外部条件的切分

| 编号 | 内容 | 是否被外部条件阻塞 | 本卡处置 |
| --- | --- | --- | --- |
| S1 | 模型设置：凭证写入/删除、来源清单与展示、连接测试、数据去向、官方缺席说明 | **否** | 冻结（§3-§5） |
| S2 | 费用可见：上限预览、逐 Operation 用量与口径、预算/额度提示、官方计费缺席口径 | **否** | 冻结（§6） |
| S3 | 发布前授权：独立人工确认、审计、拒绝路径、`publish_unavailable` | **否**（授权面可先建；发送面另属 X3） | 冻结（§7） |
| X1 | 抖音/小红书账号授权 | **是** | 不做，§8 |
| X2 | 支付、订阅权益、额度账本 | **是** | 不做，§8 |
| X3 | 平台发布接口、回执、限流与撤回 | **是** | 不做，§8 |
| X4 | 官方 Gateway / control-plane、官方能力准入 | **是** | 不做，§8 |
| X5 | 供应商账单回执核验器 | **是** | 不做，§8 |
| X6 | 任意第三方供应商由用户自报价目 | **是**（且本卡判为"不猜价"） | 不做，§8 |

**一句界分**：S 面只引用**本机已有事实**（OS 保险库、路由行、账本、审计文件、本机授权通道）；X 面才需要账号/支付/平台/官方回执。任何 S 面界面都不得让用户以为 X 面已经成立。

## 3 BYOK 凭证边界（冻结 1）

### 3.1 三类凭证必须分开，不互相冒充

| 类别 | 所有者/付费方 | 存放 | 读写者 | 出现位置 |
| --- | --- | --- | --- | --- |
| 模型商 API key（BYOK） | 用户自己；费用记在用户自己的供应商账户 | OS 保险库，条目 `byok-<instance>-<n>`，引用字符串 `vault:byok-<instance>-<n>` | 写：唯一产品接口（§3.4）；读：仅 `OperationExecutor` 派发前一次 | 只以引用/指纹出现在设置页与路由行 `credential_ref` |
| 官方服务凭证（Gateway） | 本产品 Gateway | **本产品不持有、不进 OS 保险库** | X4 未成立前不存在该对象 | 不存在 |
| 安装实例自身 secret（Owner management / 授权会话 / 本机自签 issuer） | 本安装实例 | OS 保险库 / 启动器内存 | 既有路径 | 既有审计 |

红线：**个人 BYOK key 永不标为 `source='official'`**（`docs/commercial/official-provider-admission.md:19`）；反过来，官方凭证也不得写入 BYOK 条目。

### 3.2 存在哪里

- **只** OS 保险库（`vc/infrastructure/credentials.py:29-35`）。弱后端（`keyrings.alt`、明文后端）直接 503 `secure_vault_unavailable`，不做"降级到文件"。
- **禁止**：SQLite 任何列、`Control/*.json`、`events` 表、`runs`/`steps` 的 `result_json`、作品包 artifact、导出、诊断日志、环境变量文件、浏览器 localStorage/sessionStorage/URL/IndexedDB。
- `env:VIDEO_CREATOR_SECRET_*` 引用继续存在（`credentials.py:60-61`），但**产品路由拒绝**它：`byok_route_install` 的 scope 与一次性执行器都会以 `byok_env_reference_denied` 403 拒收 `env:` 前缀（收紧，不放宽）。

### 3.3 谁能读

- 只有 `OperationExecutor.execute` 在**不可逆派发之前**调用一次 `vault.resolve(route.credential_ref)`（`vc/application/executor.py:57-63`），得到 `SecretHandle`（`repr`/`str` 脱敏，`credentials.py:13-26`）。
- 不缓存、不跨请求驻留、不进 `TaskContext`/`Flow` 状态、不随 Operation observation 落库。
- 页面与 API 只能读：`credential_ref`、`fingerprint=sha256(secret)[:16]`、`created_at_us`、`last_tested_at_us`。**任何响应、错误体、审计原文都不含明文**（复用 `api/app.py:200-203` 的不回显信封）。

### 3.4 唯一写入路径

```text
POST /api/v1/credentials            （安装会话 token + 同源 + Cache-Control: no-store）
  body: {provider_label, api_key}   # api_key 长度 16..512，不得含空白（沿用 credentials.py:41-42 的判定）
  1) 校验来源/长度/字符集 → 失败 400 invalid_credential（不回显内容）
  2) store_secret('byok-<instance>-<n>', api_key) → 失败 503 credential_store_failed
  3) 返回 {credential_ref, fingerprint, created_at_us}，明文立即丢弃
DELETE /api/v1/credentials/{credential_ref}   → remove_secret；仍被路由引用时 409 credential_in_use（列出 route_id）
```

硬约束：明文只在请求体内出现一次；服务端不写访问日志正文、不写 `print`/`logger`、不进审计、不进 `events`；页面输入框 `autocomplete="off"`、`type="password"`，提交成功后立即清空组件状态。

### 3.5 红线（可测）

任何一个成立即为发布缺陷：密钥出现在 SQLite 任意列；出现在 `Control/*.json`；出现在 `events`/`steps.result_json`/`observation_json`；出现在作品包或导出；出现在 stdout/stderr 日志；出现在错误 `message`；出现在 `/health` 或 MCP 返回；出现在页面 DOM/存储。

## 4 能力来源模型（冻结 2）

### 4.1 四层与生效点

| 层 | 内容 | 写入者 | 可否被模型/页面扩大 |
| --- | --- | --- | --- |
| L1 事实 | `routes` 表（`CapabilityRoute`：capability/source/destination/credential_ref/max_operation_cost/cost_rule_version/verified） | 安装器供给、一次性 `route-admin`（§4.3） | **否** |
| L2 边界 | `policy.allowed_provider_routes`、`external_transfer_allowed`、`max_cost`、`budget_group_id` | 请求字段（交互式）或已授权模板（目标路径） | **否**；模型只能读 |
| L3 请求 | `automation.mode`；`model_selection` **今天不是契约字段**（`Automation` 只有 mode/max_revision_cycles，`contracts.py:106-108`） | 调用方 | 否 |
| L4 裁决 | 确定性裁决器：候选集∩边界，写 `route.decided` 事件后交给原有选路门 | 引擎 | **否** |

**结论：选择只在 L4 生效。** L3 不新增 `model_selection` 字段：规格值 `auto_within_allowed_routes` 是当前唯一语义，缺省即该语义（`09:165`）；只有出现第二种策略时才加字段，避免为"只有一个取值"的枚举改公开契约。

### 4.2 裁决器（固定顺序，可测）

```text
candidates = { r ∈ routes(step.capability) : r.route_id ∈ request.policy.allowed_provider_routes }
excluded   = 其余每条路由 + 具名理由（route_denied / capability_unavailable / official_unavailable
             / transfer_denied / reservation_too_small / price_rule_unavailable / credential_missing）
order      = owned_local(零成本) → owned_local → owned_remote(有价目规则) → official
chosen     = order 中第一个候选；若无候选 → 具名失败（不进步骤重试）
event      = route.decided { step_key, candidates[], chosen_route_id, source, excluded[{route_id, reason}],
             policy_ref, price_rule_version, cost_ceiling_units }
```

- 裁决器**不改变**既有门：真正的拒绝仍由 `_route_guard`（`engine.py:685-699`）与预算门（`:739-753`）在 prepare 前重核；裁决器只是把"为什么选/为什么不选"变成可核记录。
- 事件用既有 `events` 表（`event_type: str`，`contracts.py:663-671`），**不新增表**。
- 模型/提示词可以写"推荐路线"进 plan 版本，但**不能**写 `route_id`；若推荐越界，执行仍 `route_denied` 403，不得静默换模型。

### 4.3 BYOK 路由登记（收紧型增量）

**问题**：路由写入今天只有安装器与终端（`engine.py:240-247`、`cli/main.py:271-273`），ADR0083 §2.4 明确"不新增 HTTP/MCP 可达的路由写入口"。若照抄，用户永远无法在安装形态下配置自己的模型。

**裁定**：新增授权 kind `byok_route_install`，由 **ADR0081 通道批准一个精确范围**，再由**一次性 `route-admin` 子进程**执行写入（与 ADR0082 §4.2 的 `evidence-admin` 同构）。理由与边界：

1. `register_route` 不需要任何 capability（`engine.py:240-247` 无鉴权），所以该写入**不属于 management 动作**；它与安装器供给是同一类"配置事实"（ADR0083 §3.2），不碰撞"产品内授权不授予管理能力"。
2. 写入者仍是短命子进程，**不在授权请求线程内写库**（ADR0081 §2 的三条不可能性逐条保留）。
3. scope 必填字段固定：`route_id`、`capability`、`destination`（**给用户核对只到 scheme+host+port**；完整 URL 存在路由行，仍受 `CapabilityRoute` 的"禁 query/账号口令/远程必须 HTTPS"校验）、`source`（`owned_remote`|`owned_local`）、`credential_ref`+`fingerprint`、`cost_rule_version`、`max_operation_cost`、`budget_group_id`+`budget_cap`（付费时）、`test_receipt_sha256`、`expires_at_us`。
4. **只有连接测试通过且收据 SHA 相符，才允许写 `verified=true`**（`register_route` 仍拒绝 `verified=false`）；子进程重核收据/审计/未过期/未消费，然后：写 route 行 → 付费时写 `budget_groups` 行（cap＝scope 的 `budget_cap`，`authorize_budget_group` 语义不变、cap 不可改）→ 写 `Control/ProviderConnections.json` 审计 → 一次性收据 → exit 0。
5. `route-admin` **不得**触碰：`Registration.json`、引擎源哈希、资源清单、`Control/ProductionAuthorizationControl.json`、Owner binding、policy/admission/qualified 证据。

**执行面（R2-unblocked 的真实边界，必须逐条落到 UI）**

| BYOK 形态 | R2-unblocked 能否执行 | 依据/门槛 |
| --- | --- | --- |
| `owned_local`（用户本机 loopback 端点，零成本） | **能** | reserve=0 不需要预算组；不需要外发授权；仍受 `_route_guard` 与 `route_unavailable` 门 |
| `owned_remote` 且 `cost_rule_version` ∈ {`deepseek-flash-peak-20261007-v1`, `kimi-k2.6-cn-20261007-v1`} | **能**（须先有预算组与外发授权） | 价目规则可核（`pricing.py:10-16`）；预算组由 §4.3 一次性写入；`external_transfer_allowed` 必须为真 |
| `owned_remote` 其他供应商 | **不能执行，只可保存与测试** | 无已核价目规则 ⇒ 结算必然 `unknown` ⇒ 任务必落 `needs_reconciliation`（`engine.py:838-840`）。本卡拒绝"猜价"（§8 X6） |

付费路由的**请求侧**必须同时满足两条，否则在 prepare 前具名失败：`policy.budget_group_id` 等于 §4.3 写下的组（否则 `budget_unauthorized` 403，`engine.py:743-745`），且 `policy.max_cost` 覆盖 `reserved`（否则 `budget_exceeded` 402，`:739-742`）。组 id 由 `GET /api/v1/capabilities` 返回给页面填入；引擎不替调用方补 policy（`engine.py:500-503`）。

### 4.4 官方不可用不阻塞本地创作（规格 01:16）

四条机制（都已在代码里，可核）：

1. **官方对象根本不存在**：`official` 在登记/policy/模板/选路四处被硬拒（`engine.py:244-245,694`、`production_authorization.py:108-109`、`daily_projects.py:312-313`），所以它不可能成为"必须存在才能开工"的前置。
2. **本地路由与官方无耦合**：本地 route 是 `owned_local`+零成本+`credential_ref=None`+`local:` destination（`media_registration.py:236-243`；`executor.py:22-31`），不经过任何厂商认证服务器（规格 01:81）。
3. **官方缺失只在引用它的路径上具名，且发生在派发之前**：`policy` 安装含 official 路由 → `official_unavailable` 503（`production_authorization.py:108-109`）；请求列出未登记的官方 route id → `route_denied` 403（`engine.py:690-691`）；若有人伪造了 official 行 → `capability_unavailable` 503（`:694`）。三种都在 prepare 之前失败，**不产生付费 Operation、不发任何外发请求**。
4. **官方失效不改既有事实**：已发布作品包、导出、引用授权都不依赖官方（`01:16`；`official-provider-admission.md:15`）。

四条禁则：

1. 禁止本地制作路径探测官方认证（测试连接、打开项目、编辑镜头、预览、合成一律不触达；规格 01:81）。
2. 禁止把官方缺失渲染成"整个制作按钮不可用"——只有引用官方来源的那次提交失败。
3. 禁止把 `verified=false` 或官方缺失翻译成"稍后自动重试成其他付费模型"。
4. 禁止把"官方未准入"写成"免费/0 元额度"（§6.6）。

### 4.5 回退语义（只允许向下、同集合）

- 允许：在 `allowed_provider_routes` **内部**、同 capability、成本不增的前提下，由裁决器顺序选择下一个候选（例：首选远程失败后按 policy 允许退回本地零成本）。
- **禁止**：跨来源类自动切换（`official`↔`owned_remote`↔`owned_local`）——跨类意味着数据外发或计费主体改变（`01:22`、`09:165`）。跨类必须由人重新选择来源并重新提交。
- 每次回退都写进 `route.decided` 的 `excluded[].reason`，页面展示"本次为何不用你选的 X"。

### 4.6 三个入口的适用面（避免"设置里能选、实际不生效"）

| 入口 | policy 来源 | BYOK 是否生效 | 产品表现 |
| --- | --- | --- | --- |
| 交互式 `POST /api/v1/productions` | 调用方显式 `policy`（引擎不覆盖，`engine.py:500-503`） | **生效**（受 §4.3 执行面限制） | 制作页显示本次来源与排除理由 |
| 目标/模板路径（`POST /api/v1/project-goals`） | 已授权模板（`daily_projects.py:621-632`），强制 unattended | **不自动生效** | 目标入口必须写"本入口只用实例已授权来源；自带模型请在制作页显式选择" |
| MCP `production_create` | 调用方 `request` | 与交互式同规则 | 工具描述里写明"来源受实例授权约束，不因配置了 BYOK 自动启用" |

模板并入 BYOK 需要 management 动作（`daily_projects.py:395-398`），本卡不做（§8 X4 相邻项）。

### 4.7 来源展示口径（逐字文案，测试可断言）

1. 本地："本地零成本 · 不出网"（当 `source=owned_local`, `credential_ref=null`, `max_operation_cost=0`）。
2. 自带模型（远程）："你的 `<provider_label>` · 数据发往 `<host>` · 单次上限 CNY x · 价目规则 `<rule_version>`"。
3. 自带模型（本机端点）："你的本机端点 `<host:port>` · 不出网"。
4. 官方："官方能力未开放（缺账号/权益/接口准入）"——**不得**出现"已连接""可用""免费"。
5. 不可执行原因：逐条用 `excluded[].reason` 映射成中文原因，禁止只显示"不可用"。

## 5 连接测试（冻结 3）

### 5.1 允许联网探测的最小信息

| 项 | 允许 | 禁止 |
| --- | --- | --- |
| 协议元数据 | `GET <destination>/models`（OpenAI 兼容）或厂商等价的**只读元数据**接口 | 任何生成调用（除非 5.2 的固定字面量回退） |
| 回退探测 | 固定字面量 `ping`，`max_tokens=1`、`stream=false`、`tools=none`、`n=1` | 任何素材、提示词、目标文本、项目 id、资产 id、转写、路径 |
| 请求体 | 上述固定体的 canonical 字节，SHA256 进测试收据 | 用户数据、上一轮来源、历史记录 |
| 传输 | 远程必须 HTTPS（`contracts.py:324-325`）；本机必须 loopback（`:321-323`） | 明文 HTTP 远程、内嵌账号口令、query 携带密钥 |
| 超时/重试 | 单次，`≤10s`，**不自动重试** | 后台轮询、批量探测、并发多端点 |

### 5.2 顺序固定：先同意，再探测，再登记

1. 用户填 `provider_label` + `destination` + `capability` + `max_operation_cost` +（付费时）`budget_cap` + key。
2. 后端构造 `byok_route_install` 的 scope（含 `destination_host`、`probe_kind`、`probe_bytes_sha256` 预览、"将发生一次固定探测"的说明）→ 产品内授权（ADR0081 四项凭据）。
3. 审计先行（`Control/ProductAuthorization.json`，`kind='byok_route_install'`）→ 一次性收据。
4. `route-admin` 子进程：先 probe（**这是本次唯一外发**）→ 通过才写 route（`verified=true`）；不通过则不写路由，收据记 `failed` 与失败码，审计仍落地。
5. 页面展示结果：成功＝"已保存，并于 <时间> 测试通过（端点与鉴权）"；失败＝具名原因 + "可修正后重新测试（会再次请求授权）"。

### 5.3 失败具名（新增码，均为 `connection_test_*`）

| 情形 | 码 | HTTP | 可重试 |
| --- | --- | --- | --- |
| DNS/TCP 不可达 | `connection_test_unreachable` | 503 | 修配置后 |
| TLS/证书失败 | `connection_test_tls_denied` | 503 | 否（须修证书或换端点） |
| 超时 | `connection_test_timeout` | 504 | 可 |
| 401/403 | `connection_test_auth_denied` | 403 | 修 key 后 |
| 429/额度耗尽 | `connection_test_quota_denied` | 429 | 稍后 |
| 响应不是预期协议 | `connection_test_protocol_mismatch` | 422 | 修端点/协议 |
| 该能力无法在不生成的前提下验证 | `connection_test_unknown_capability` | 409 | 否（只能标 `endpoint_and_auth`） |
| 未获外发授权就探测远程 | `connection_test_denied_by_policy` | 403 | 先授权 |

### 5.4 诚实标注

`Control/ProviderConnections.json` 记 `verification_level ∈ {endpoint_and_auth, endpoint_auth_and_probe}`：

- `endpoint_and_auth`：只证明端点可达且鉴权成立；
- `endpoint_auth_and_probe`：另有一次固定探测成功。

`verified=true` **只**表示上述之一，**不**表示"生成质量合格/能力已认证/价格已核"。设置页必须逐字写：「已测试的是端点与鉴权，不是生成质量」。

## 6 费用可见性（冻结 4）

### 6.1 四个来源（页面只读，不计算）

1. 账本：`productions.spent_units`/`reserved_units`、`budget_groups.cap/spent/reserved`（`engine.py:831-851,1064-1069`）。
2. 逐操作：`operations.actual_units`、`cost_evidence`、`observation_json.usage`（usage 写入 `engine.py:838`；`get_production` 目前只 SELECT 五个字段 `engine.py:560`，所以需要 §6.5 的加性字段才能显示用量）。
3. 价目：`cost_rule_version` 两条已核规则 + 各自单价（`pricing.py:10-16,54-71`）。
4. 官方回执：**当前不可达**（见到 `provider_receipt` 即 409，`pricing.py:74-78`）。

页面与前端**不得**自行乘算价格；所有金额来自上述 1-3 的服务端字段。

### 6.2 三个时机

| 时机 | 展示 | 来源 |
| --- | --- | --- |
| 提交前 | 本次上限 `policy.max_cost`、每条将用路由的单次上限 `max_operation_cost`、价目规则版本、是否"本地零成本"、被排除的来源与理由 | `POST /api/v1/productions/preview`（新增，只读干跑） |
| 执行中 | 已预留 `reserved`、已结算 `spent`、"待核实"计数 | `GET /api/v1/productions/{id}` 的 `cost` + `operations[].cost_status` |
| 结束后 | 每步用量与口径、总计、未核实项 | 同上 + §6.5 的 `usage` |

`preview` 语义固定：跑与受理相同的校验（路由、预算、证据、外发），**不创建 production/run、不 reserve、不调用供应商、不写事件**；返回 `{allowed_routes[], excluded[{route_id, reason}], cost_ceiling{currency, amount}, budget{group_id, cap, spent, reserved} | null, blockers[]}`。它是"按钮为何置灰"和"上限是多少"的唯一来源。

### 6.3 口径（逐字文案，缺任一条即发布缺陷）

| `cost_evidence` | 展示 | 禁止 |
| --- | --- | --- |
| `confirmed_no_charge` 且 `spent=0` 且无未结算操作 | 「本地零成本（未产生费用）」 | 有 `unknown` 时仍显示此句 |
| `usage_price_calculation` | 「按价目规则 `<rule>` 估算 CNY x（非供应商账单）」 | 说成"实际扣费/账单" |
| `provider_receipt` | 「供应商账单回执 CNY x」 | 在无 verifier 时显示（当前不可达，`pricing.py:77-78`） |
| `unknown` | 「费用待核实」 | **任何形式显示 0 元**（规格 06:91） |
| 未结算/进行中 | 「已预留 CNY x」 | 并入"已花费" |

### 6.4 预算与额度提示

- 有预算组：显示 `剩余 = cap - spent - reserved`，三项分列；超限时显示 `shared_budget_exceeded` 的具名原因。
- 无预算组且无付费路由：显示「本实例未授权付费预算；当前只用零成本能力」——**不**显示"额度 0 元"当成真实额度。
- `Control/ProductionAuthorizationControl.json` 的 `minimum_revision=0`/`pending_request_sha256=null`（`production_management.py:159-168,192-197`）：显示「尚未安装任何创作策略修订」。
- 额度只读接口：`GET /api/v1/budget` → `{groups:[{group_id, cap, spent, reserved}], floor:{minimum_revision, pending_request}]}`；不得暴露任何密钥或持有人身份细节。

### 6.5 每步实际用量（契约增量）

`OperationSummary`（`contracts.py:213-219`）**加两个可选字段**（架构批准、后端实现、集成重生成契约与 SDK）：

```
usage: {prompt_tokens:int, completion_tokens:int, cache_hit_tokens:int|null} | null
price_rule_version: str | null
```

规则：`usage` 只来自驱动的真实观测；缺失即 `null`（旧记录一律 `null`，不回填、不估算）；`usage=null` 且费用非 `confirmed_no_charge` 时必须显示"待核实"。这是**加性**变更，不改变既有字段语义与校验。

### 6.6 官方计费缺失时的诚实

官方能力不可用（X4 未成立）时：显示「官方额度不可用（未接入官方服务）」；**不得**显示 0 元、免费、无限量；不得展示任何"订阅剩余额度"数字（没有该数据源）。`price_rule_unavailable`（`pricing.py:93-95`）在 UI 上对应"该来源缺少可核价目规则，不能估价也不能执行"。

### 6.7 不做

不做服务端"总价估算"（会被读成报价）；不做跨供应商比价；不做汇率换算（`Money` 只有 CNY）；不做用量回填；不把 `usage` 从 `observation_json` 反解析成"估算"。

## 7 发布前授权（冻结 5）

### 7.1 与"制作同意"的区别（不可复用）

| 维度 | 制作（R1 既有） | 发布（本卡） |
| --- | --- | --- |
| 授权对象 | Owner 初始化 / 审核卡片确认 / 策略与预算 | **一次具体发布动作**：哪个作品版本、发到哪个平台账号、发什么文案 |
| 触发者 | 建项目与审核流程 | 人点"同意并发布" |
| 有效期 | 天级（binding/policy） | **≤10 分钟**（同 ADR0081 请求窗），且一次性 |
| 能否被 unattended 覆盖 | 制作可以按策略自动 | **绝对不可以**（`01:109`：正式制作的自动授权不包含发布/投放授权） |
| 被谁执行 | worker | 平台适配器（X3；当前不存在） |

### 7.2 通道增量

- `_SUPPORTED_KINDS` 增 `publish_release`（`product_authorization.py:73`），正常装配进程的 `allowed_kinds` 增该项（`cli/main.py:532-537`）。
- 复用**逐字不变**的四项凭据：安装会话 token + `X-VideoCreator-Authorization` 会话 secret + 一次性 nonce + 重算的 `scope_sha256`（ADR0081 §4）。
- 复用"审计先行"：先写 `Control/ProductAuthorization.json`（追加 `kind`、`bundle_revision_id`、`manifest_sha256`、`platform`），再写一次性收据 `Control/PublishAuthorization.json`；审计失败即 `503 authorization_audit_unwritten`，不写收据。
- `approve` 只批准范围：新增分支 `_approve_publish_release`，**不发起任何平台请求**，只写审计与收据（收据 `state='authorized'`），不创建 adapter、不写任何发布结果。

### 7.3 scope（精确、可核、无秘密）

```text
kind='publish_release'
bundle_revision_id, bundle_manifest_sha256   # 固定版本，禁止"始终最新"
project_id, platform ('douyin'|'xiaohongshu'|…), account_ref   # 账号引用，不含 token/cookie
publish_mode ('immediate'|'scheduled'), scheduled_at_us|null
caption_sha256, cover_artifact_id|null
max_posts = 1
expires_at_us                                # ≤10 min，且 ≤ 收据/会话窗
```

不含：任何平台 token、cookie、手机号、播放列表 id、URL 票据。`bundle_manifest_sha256` 必须与当前已发布作品包逐字相等，否则 `publish_bundle_conflict` 409。

### 7.4 界面（逐字文案，缺一条即缺陷）

- 标题：「发布到<平台>」
- 三行事实：「作品版本 `<revision>`（manifest `<sha8>`…）」「将发送：视频文件 + 文案 + 你的<平台>账号 `<account_ref>`」「发布后平台侧行为（删除/修改）由平台决定」
- 主按钮「同意并发布」；次按钮「拒绝」
- 副说明：「这是独立于制作的一次授权；制作同意、预授权自动制作都不覆盖它」
- 若 X3 未成立：主按钮 `disabled`，旁注「平台发布接口未接入（缺<平台>账号授权与发布接口），此版本不能从这里发布」——**不**出现"发布成功""排队中"。

### 7.5 拒绝与过期路径

| 情形 | 结果 |
| --- | --- |
| 拒绝 | 写 denial 审计（复用 `write_product_denial_audit`）；不写收据；不产生任何平台请求；任务回到"未发布"；可重新发起新 `authorization_id` |
| 过期 | `409 authorization_expired`；不写收据；须重新发起 |
| 重复 approve | 同 nonce + 同 scope + 同 decision → 幂等返回原 view；不同 nonce → `409 authorization_already_decided` |
| scope 与当前作品包不符 | `409 publish_bundle_conflict` |
| 平台未接入 | `503 publish_unavailable`（具名，不改作品包状态） |
| 平台受理结果不明 | `needs_reconciliation` 语义（同 Operation）：不重交、不显示成功 |

### 7.6 审计字段（发布）

`authorization_id`、`kind='publish_release'`、`instance_id`、`generation`、`scope`、`scope_sha256`、`decision`、`created_at_us`、`decided_at_us`、`expires_at_us`、`session_secret_fingerprint`、`nonce_fingerprint`、`origin`、`caller_module`、`os_identity`、`bundle_revision_id`、`manifest_sha256`、`platform`、`account_ref`、`result_ref`、`publish_receipt_sha256`（成功后）。

### 7.7 状态机与回执

`draft → authorized → submitting → accepted(receipt) → published`，异常分支 `failed` / `unknown(needs_reconciliation)`。**状态只落在两份 `Control/` 文件里**（`ProductAuthorization.json` 审计 + `PublishAuthorization.json` 收据的 `state` 字段），不新增表；回执字段：`platform_post_id`、`platform_account_ref`、`content_sha256`、`published_at_us`、`raw_status`（平台原文，≤2 KiB）。发送由一次性 `publish-admin` 执行（同 `evidence-admin` 形态），**X3 不存在时它直接 503 `publish_unavailable`**，收据 `state='unavailable'`；界面显示"已授权，但发送能力未接入"，绝不显示 `published`、也不把 `unavailable` 记成 `failed`（从未发送）。

### 7.8 MCP/API 结构性无法发布

approve 需要启动器注入的会话 secret（只进页面内存，ADR0081 §4）；MCP 与第三方调用方从不持有该 secret，因此**即使有人给它们完整安装 token，也无法完成 approve**。这是"发布必须由人确认"的技术保证，不是文案承诺。

### 7.9 不做

不做无人值守/批量发布；不做"记住这次同意"；不做跨平台同时发布；不把导出 ZIP 或引用授权当成发布（既有 R1 交付路径不变，`api/app.py:511-535`）；不在授权线程内调用平台。

## 8 不做清单与"缺条件时的产品表现"（冻结 6）

| # | 不做 | 缺条件时的产品表现（必须逐一实现） | 解除条件 |
| --- | --- | --- | --- |
| X1 | 抖音/小红书账号授权 | 设置页"官方/平台账号"卡片显示「未连接平台账号（本机无授权）」；发布入口无账号可选 | 真实账号 + 平台授权流程 + 准入证据 |
| X2 | 支付、订阅权益、额度账本 | 设置页显示「本实例未接入支付与订阅」；`GET /api/v1/budget` 只返回本机预算组；**任何地方不显示 0 元额度或免费承诺** | 支付沙箱 + 权益/额度服务 + 对账 |
| X3 | 平台发布接口与回执 | 发布按钮置灰 + 具名原因；已授权也停在 `publish_unavailable` 503；作品包状态不变 | 平台接口准入 + 回执核验 + 限流/撤回语义 |
| X4 | 官方 Gateway / control-plane、官方能力准入 | 所有官方来源显示「官方能力未开放」；`official` 仍 503；本地与 BYOK 不受影响 | `docs/commercial/official-provider-admission.md` §"每项能力必须有的准入证据"逐项通过 |
| X5 | 供应商账单回执核验器 | 见到 `provider_receipt` 仍 409 `receipt_verifier_missing`；页面显示"待核实" | 回执适配器 + 对账证据 |
| X6 | 任意第三方供应商自报价目 | 只可保存与测试；执行以 `price_rule_unavailable` 503 拒绝；页面写「缺可核价目规则，不能估价也不能执行」 | 另立卡（用户价目的诚实标注、审计、误填后果） |
| — | 无人值守发布 | 不存在该开关；`publish_release` 只能由人点同意 | 永不（规格 01:109） |
| — | 跨类自动回退（official↔BYOK↔local） | 具名失败并要求人重新选择来源 | 永不（`01:22`、`09:165`） |

## 9 与既有 ADR 的关系（含两处定点修订）

| 既有裁定 | 本卡关系 |
| --- | --- |
| ADR0081（产品内授权通道） | **复用**四凭据、审计先行、单槽、过期/拒绝语义、`restart_required`；新增两个 kind（`byok_route_install`、`publish_release`）；不放宽 §2/§4/§6/§8 |
| ADR0082（本机自签证据） | 只借用"授权批范围 + 一次性子进程执行"的形态；证据条款完全不变 |
| ADR0083（安装器供给） | 供给与同意仍严格分离；`route-admin` 属"配置事实写入"，不写 Owner/floor/secret/policy（§2.4 两处修订见下） |
| ADR0084（受信启动权威） | BYOK 路由**不构成**执行权威；制作仍需 ADR0084 权威 + Owner binding + 预算 + 路由门；本卡不新增 `observe`/`observe_facts` |
| ADR0036/0077（诚实边界） | 同账户原生代码仍可改库/改文件；本卡不宣称防它，只保证"无同意不发布、无凭据不外发" |

**定点修订 1**：ADR0083 §2.4 其余禁止项中"任何 HTTP/MCP 可达的注册或路由写入口"改为：

> 任何 **HTTP/MCP 可直接调用**的注册或路由写入口。唯一例外是 ADR0085 的 `byok_route_install`：它必须先取得产品内授权范围（ADR0081 四项凭据），再由一次性 `route-admin` 子进程写入，且只允许写单条 `owned_remote`/`owned_local` 用户路由与该路由的预算组；不得改写 `Registration.json`、引擎源哈希、资源清单、floor、Owner binding、policy 或证据。

**定点修订 2**：ADR0083 §2.2 B5"路由由安装器写"后追加：

> 安装后新增的用户自带模型路由按 ADR0085 §4.3 处理；安装器供给的五个本地 route id 语义不变，用户路由不得复用其 id。

## 10 接口清单（冻结 7）

### 10.1 Backend（`services/engine/src/video_creator/`；不新增表/迁移）

1. `api/app.py`：`POST /api/v1/credentials`、`DELETE /api/v1/credentials/{ref}`、`GET /api/v1/capabilities`（来源清单＋`verification_level`＋`excluded` 原因）、`POST /api/v1/capabilities/byok-routes`（发起 `byok_route_install` 授权请求；**不提供独立的测试端点**，探测只能在 `route-admin` 内发生）、`POST /api/v1/productions/preview`、`GET /api/v1/budget`；`GET /api/v1/authorization/pending` 视图支持新 kind。
2. `application/credentials_service.py`（新）：写入/删除/指纹/引用校验；**只**调 `CredentialVault`；拒绝 `env:` 前缀路由引用（`byok_env_reference_denied` 403）。
3. `application/provider_connections.py`（新）：探测（固定字节）、`Control/ProviderConnections.json` 读写（canonical/LF/原子写）、`verification_level`、失败码。
4. `application/byok_routes.py`（新）：scope 构造、测试收据读写、复用 `engine.register_route` 与 `engine.authorize_budget_group`（签名不变）。
5. `cli/route_admin.py` + 命令域 `route-admin install --receipt <path>`（一次性、无监听、不装配 OwnerServices）。
6. `application/product_authorization.py`：`_SUPPORTED_KINDS` 三值；`request_byok_route_install`、`request_publish_release`（照 `request_local_evidence_policy:841-871` 的形态）；`approve` 两条新分支；`_view` 的 summary 按 kind 分支。
7. `cli/main.py`：正常装配进程 `allowed_kinds=('local_evidence_policy','byok_route_install','publish_release')`；`serve` 进程不注入任何平台适配器，适配器只由一次性 `publish-admin` 子进程使用（X3 未成立时为 `None`）。
8. `application/publish_authorization.py`（新）：`PublishAuthorization.json` 收据、状态机、`publish_unavailable`、回执校验（manifest SHA 必须相等）；**不含**任何平台 HTTP 客户端（X3 另有卡）。
9. `application/engine.py`：裁决器 + `route.decided` 事件；`preview`（只读干跑）；`OperationSummary.usage/price_rule_version` 填充；其余门一行不改。
10. `domain/contracts.py`：`OperationSummary` 加两个可选字段；`Automation` **不加** `model_selection`（§4.1）。
11. `infrastructure/credentials.py`：不改语义；如需 `fingerprint` 辅助函数，只能返回 `sha256[:16]`。
12. 契约/SDK：由集成在架构批准后重生成 `packages/contracts`、`schemas.json`、`packages/api-client`；授权与凭证路由仍**不入 OpenAPI**（沿用 ADR0081 §9）。

### 10.2 Frontend（`apps/workbench/src/`）

1. 设置页替换 `Workbench.tsx:456` 的四张只读卡：来源列表（本地/自带/官方三分区）、每条来源的 `verification_level` 与"已测试的是端点与鉴权，不是生成质量"、数据去向（`host`）、单次上限、预算组与剩余。
2. `SettingsSourcesView.tsx`（新）：添加来源向导（label/host/capability/上限/预算/key）→ 一个"保存并测试"动作（同一次授权范围；探测只发生在 `route-admin` 内）→ 结果与具名原因。
3. 凭据输入：`type=password`、`autocomplete=off`、提交后清空、**不**入任何 storage；页面只显示 `fingerprint` 前 8 位。
4. 费用：制作页 `cost-note`（`Workbench.tsx:450`、`ProductWorkspaceView.tsx:206`）改为三档口径 + 预算条；任务中心每行显示来源与费用口径；提交前调 `preview` 展示上限与排除原因。
5. 发布：成片页新增"发布到平台"入口（X3 未成立时 `disabled` + 原因）；发布授权页复用 `product-authorization-ui-v1` 外壳与 phase 机；`productAuthorization.ts` 的 `KIND_LABELS` 增两项、`SCOPE_LABELS` 增 `platform/account_ref/bundle_revision_id/publish_mode`。
6. 授权页禁止把 `publish_release` 的 scope 渲染出任何 `token/cookie/secret` 字段（既有 `HIDDEN_KEY` 过滤保留）。

### 10.3 Test（全部须真实运行并登记 `docs/acceptance/criteria/COMMANDS.md`）

| # | 用例 | 类型 | 期望 |
| --- | --- | --- | --- |
| T1 | 写入 key 后扫描 SQLite/`Control/*.json`/日志/事件 | 负例 | 无明文命中；只有 `vault:` 引用与指纹 |
| T2 | 无 OS 保险库后端（弱后端） | 负例 | 503 `secure_vault_unavailable`，不落盘 |
| T3 | 删除仍被路由引用的凭证 | 负例 | 409 `credential_in_use` |
| T4 | 交互式请求显式列出 BYOK 本地零成本路由 | 正例 | 受理→执行→`route.decided` 含 chosen 与 excluded，费用"本地零成本" |
| T5 | 官方路径两条负例 | 负例 | ①`policy` 安装含 official 路由 → `official_unavailable` 503；②请求列出未登记官方 route id → `route_denied` 403，且**无付费 Operation、无外发** |
| T6 | 请求含本地路由 + 官方路由 | 正例 | 本地成功；`excluded` 里官方带原因，不影响结果 |
| T7 | 连接测试请求体检查 | 负例/正例 | 请求体只含固定字节；素材/目标/资产 id 一个都不在 |
| T8 | 测试失败矩阵 | 负例 | 八个 `connection_test_*` 各自具名，路由**未**登记 |
| T9 | 测试通过后登记 | 正例 | route 行 `verified=true`；`ProviderConnections.json` 有 `verification_level` 与探测 SHA |
| T10 | 未核价目的远程 BYOK | 负例 | 503 `price_rule_unavailable`；不执行、不猜价 |
| T11 | 未知费用展示 | 负例（前端快照） | 断言页面出现"费用待核实"，且**不出现** "CNY 0" |
| T12 | 发布：无会话 secret / MCP 调用 approve | 负例 | 403 `authorization_session_denied`；MCP 结构性不可达 |
| T13 | 发布：同意后 X3 缺失 | 负例 | 503 `publish_unavailable`；作品包状态不变；无"已发布" |
| T14 | 发布：拒绝与过期 | 负例 | denial 审计存在、无收据、可重新发起；过期 409 |
| T15 | 发布：作品包被替换后 approve | 负例 | 409 `publish_bundle_conflict` |
| T16 | 授权 kind 白名单 | 负例 | 不支持的 kind 403 `authorization_kind_denied` |

**最小验收（先做这 6 条）**：T1、T4、T6、T9、T11、T13。

### 10.4 集成

启动器注入 `VIDEO_CREATOR_AUTHORIZATION_SESSION_SECRET`（已有）；可选注入发布适配器（X3 前为 `None`）；包内不新增任何凭证/账号；`Engine.spec` 与构建收据不变；`route-admin` 必须能从冻结产物调用（Entry 前缀分派同 ADR0084 §4.3 形态）。

## 11 失败码（新增，全部不得加入 `RESOURCE_WAIT_CODES`）

`byok_env_reference_denied` 403 / `credential_in_use` 409 / `byok_route_scope_denied` 403 / `byok_route_receipt_invalid` 403 / `byok_route_receipt_consumed` 409 / `byok_route_instance_conflict` 409 / `provider_connection_unavailable` 503 / 八个 `connection_test_*`（§5.3）/ `production_preview_denied` 403 / `publish_unavailable` 503 / `publish_bundle_conflict` 409 / `publish_adapter_denied` 403 / `publish_receipt_invalid` 422 / `authorization_kind_denied` 403。

## 12 红线

1. 不得把 X1-X6 的任何一项写成"已支持/已接通/免费/0 元额度"。
2. 不得让 `verified=true` 被读成"能力已认证/价格已核/质量合格"。
3. 不得让连接测试携带素材、提示词、目标、资产 id 或任何用户数据。
4. 不得在任何界面把 `unknown` 费用显示成 0。
5. 不得复用制作同意、审核确认或 unattended 预授权来发布。
6. 不得让模型/提示词/页面扩大路由集合、外发授权或预算。
7. 不得在前端存储 secret/key；不得在服务端日志、事件、审计原文、作品包或导出中出现 key。
8. 不得新增表/迁移；不得放宽 `register_route`、`_route_guard`、预算门、`install_startup_services`、`assemble_owner_services`、`ProductionAdmissions`、`management_access` 任一行。
9. 不得让 `route-admin` 触碰 `Registration.json`、引擎源哈希、资源清单、floor、Owner binding、policy、证据。
10. 不得在授权请求线程内写路由、写预算组或调用平台。

## 13 实施顺序与门槛

1. **S1-a 只读面**：`GET /api/v1/capabilities` + 设置页来源列表 + 费用三档口径（无写入、无外发，可先交付）。
2. **S1-b 凭证与测试**：`POST/DELETE /api/v1/credentials` + `ProviderConnections` + `byok_route_install` 授权 + `route-admin`（本机零成本路由先跑通）。
3. **S2**：`productions/preview` + `usage` 契约增量 + 预算只读接口 + 任务/制作页改造。
4. **S3-a**：`publish_release` kind + 发布授权页 + 审计/收据 + `publish_unavailable`（无平台适配器也必须先跑通这条负例）。
5. **S3-b（X3）**：平台适配器与回执——**另立卡**，需真实账号与接口准入。
6. 每步门槛：文档阶段 `git diff` 只含本 ADR；实现阶段负例必须真实运行并登记 `COMMANDS.md`；X 面未成立时对应按钮必须置灰且理由可核。

## 14 复核清单

1. `git diff` 只含 `docs/decisions/0085-r2-unblocked-scope.md`；源码/测试/契约/迁移零改动。
2. §0 的每条行号与 HEAD `4e218ec` 一致（重点核 `credentials.py:29-35,75-90`、`engine.py:240-247,685-699,739-753,1064-1069`、`pricing.py:74-86`、`product_authorization.py:73,841-871,937-982`、`vc/cli/main.py:521-537`、`Workbench.tsx:456`）。
3. §3 的红线 8 条都能对应到一个可执行检查（T1/T2/T3 或日志扫描）。
4. §4.4 四条机制与四条禁则都能落到具体行号，且没有把"官方不可用"写成"实例不可用"。
5. §5 的探测体在测试里可逐字节复算（请求体 SHA 进收据）。
6. §6 的四档口径与 `pricing.py` 的四值一一对应，且 `unknown` 在任何路径都不会渲染成 0。
7. §7 的四凭据/审计先行/拒绝路径与 ADR0081 §4/§6/§8 逐字一致；`publish_unavailable` 没有被措辞软化成"稍后重试"。
8. §8 的 X1-X6 每条都有"产品表现"而不是"待定"。
9. §9 的两处定点修订只改 ADR0083 的两句，且未放宽其 §2.4 其余禁止项。
10. §10 的接口没有一项需要新增表/迁移，也没有一项让 API/MCP 直接写路由、预算组或发布。

## 附录 A：给统筹的 `docs/task-board/ProductDirection.md` 追加文本（本文件属统筹写入范围，架构不代写）

> ## R2 非外部依赖部分（ADR0085，2026-10-26）
>
> R2 依赖的真实平台账号、支付与订阅额度、平台发布接口在本机不存在，**不得用模拟替代**。但其中三块不依赖外部条件，已由 ADR0085 冻结：
>
> | 块 | 内容 | 权威位置 |
> | --- | --- | --- |
> | S1 模型设置 | BYOK 凭证只进 OS 保险库、一条写入路径、只被派发前解析一次；来源清单/连接测试/数据去向；官方缺席说明 | `docs/decisions/0085-r2-unblocked-scope.md` §3-§5 |
> | S2 费用可见 | 提交前只显示上限与口径（`productions/preview`）、执行中 reserved/spent、逐操作 `cost_evidence` 与 `usage`；未知一律"待核实"，绝不显示 0 | 同上 §6 |
> | S3 发布前授权 | 每次发布一次独立人工确认（kind `publish_release`，四项凭据 + 审计先行）；无平台接口时置灰并具名 `publish_unavailable` | 同上 §7 |
>
> **外部条件与其产品表现**（X1 平台账号、X2 支付/订阅额度、X3 发布接口与回执、X4 官方 Gateway、X5 账单回执核验、X6 第三方自报价目）逐条固定在 ADR0085 §8：缺条件时**置灰 + 具名原因 + 绝不假装成功、绝不显示 0 元额度**。
>
> **排序更新**（承接原"排序原则"第 3 条）：先 S1-a 只读来源与费用口径（无写入、无外网）→ S1-b 凭证与连接测试（本机零成本路由先跑通）→ S2 → S3-a 发布授权（先用 `publish_unavailable` 负例跑通）→ 才轮到需要外部条件的 S3-b/X 面。
>
> **口径纪律**：模型设置里的 `verified=true` 只表示"端点与鉴权在测试时成立"，不是能力认证、不是价格核准；`model_selection` 不新增字段，`auto_within_allowed_routes` 是唯一语义；目标/模板入口不会自动并入 BYOK（模板并入需管理面，未交付）。
