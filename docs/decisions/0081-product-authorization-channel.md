# ADR0081：产品内授权通道（替换终端 TTY 确认）

状态：DESIGN_FROZEN_ONLY，2026-10-25。只冻结"产品内授权"的对象协议、受限启动、确认凭据、审计、动作清单、失败语义、前端契约与退役；**不改源码、不改迁移、不改契约、不新增表**。不放宽任何生产校验，不让配置文件/环境变量/模型输出直接构成授权。

用户已把"正式产品应弹窗请求授权，而不是让人操作终端"定为最高优先级；本 ADR 只做产品形态设计，headless/CI 的 TTY 路径保留为兜底。

## 0 实读证据（行号取 HEAD `8e56109`；`vc/` = `services/engine/src/video_creator`）

| 事实 | 位置 |
| --- | --- |
| 首次 Owner 初始化等动作走 `change()`：`None` 分支强制 TTY 逐字确认 | `vc/application/owner_bootstrap.py:173-175,388-398` |
| `change()` 另有两个精确类型分支：dev 自动初始化、原 native setup | `vc/application/owner_bootstrap.py:176-194` |
| 产品形态的确认对象已存在，但只能由 native 连接构造（instance/generation/attempt/epoch/thread 保留表） | `vc/application/owner_setup_confirmation.py:36-158` |
| 前端已有 setup 视图协议 `native-setup-ui-v1`：status/prepare/present/abort + phase 机 + `request_identity` + `current_document` | `apps/desktop/OwnerSetupPort.ts:1-40` |
| 该视图只能由桌面 shell 注入 invoke，无 HTTP/loopback 形态 | `apps/workbench/src/nativeSetup.ts:1-20` |
| `serve` 先 `install_startup_services` 再 `listener.bind`；无 factory 时 bundle 为 None | `vc/cli/main.py:317-323` |
| 启动装配硬门：`NativeOwnerServices` 精确类型、authority 同一对象、registry/management 均 None | `vc/cli/startup_services.py:65-91` |
| `assemble_owner_services` 只在受信启动调用；每次都建 `LocalCopyInputService` 并 `configure_local_copy_inputs` | `vc/application/owner_services.py:101-130` |
| 同一进程二次安装 copy 服务会被拒（配置不可静默替换） | `vc/application/engine.py:90-99` |
| 无执行身份时任何执行 `production_authorization_unconfigured` 403 | `vc/application/engine.py:119-125` |
| 管理动作（policy/execution/creation）在 CLI 各自调 `confirm_local_action` | `vc/cli/owner.py:163,180,228` |
| API 鉴权：安装会话 token；管理面需要**另一个** management credential | `vc/api/app.py:113-155` |
| `/health` 五字段 + 已有 dev 响应头先例 | `vc/api/app.py:168-175`；ADR0077 §5 |
| 管理 registry 由 Owner secret 绑定，能力经 `registry.authenticate` | `vc/application/owner_bootstrap.py:337-367` |
| dev 自动初始化是显式 flag、默认关，且只写首次绑定 | ADR0079 §13.1；`vc/cli/development_host.py:76,91,383` |
| 规范 06：模型设置页、创建时"审核与指导/预授权自动制作"、审核卡片、必须设计"授权过期"状态 | `Documents/VideoCreatorSpecification/06-界面与交互规范.md:63,65,67,89` |

## 1 结论摘要

1. **受限启动**：无 Owner binding 时引擎可以监听，但只暴露 `/health` 与 `/api/v1/authorization/*`；其余全部 403 `owner_authorization_required`。
2. **必须重启，不做同进程解锁**：授权成功后受限进程只写 binding 并输出"可重启"，全功能（执行/管理）由启动器重启进入正常装配。理由见 §2。
3. **每个进程只能有一次 OwnerServices 装配**（`owner_services.py:129-130` + `engine.py:90-99`），因此 R1 产品授权只覆盖**首次 Owner 初始化**；管理动作（policy/预算/execution/daily）的产品化需要独立的 management 进程装配，属后继卡（§7）。
4. **确认凭据**＝一次性 nonce + 范围哈希 + 本机授权会话 secret（启动器注入，API 永不返回）+ same-origin/token；TTY 路径保留、dev 自动初始化保留但默认关。
5. **审计先于生效**：任何"界面点同意"必须在写 Owner binding 之前落审计；审计写失败即拒绝，杜绝"点了同意但无审计"。

## 2 受限启动模式（结论：可监听，但不可同进程解锁）

**允许监听**：授权通道本身必须经 HTTP 才能到工作台，否则就只能继续走终端。因此 `serve`/`worker` 在无 Owner binding 时不再于启动期直接失败，而是进入受限模式：
- 只挂 `/api/v1/health` 与 `/api/v1/authorization/*`；其余路由、SSE、静态媒体一律 `403 owner_authorization_required`（不是 503：授权后同一 URL 会成功，语义是"未授权"而非"不可用"）。
- 不调用 `install_startup_services`、不装配 `OwnerServices`、不登记执行身份、不建/读 `ProductionAdmissions`；因此**受限进程没有任何执行能力**，`/health` 只有五字段 + 一个新响应头（§9）。
- 授权会话及其 pending 请求只存在于本进程内存（ADR0005 的 `_retained_*` 同形态），进程退出即失效；不引入新表、不改迁移。

**为什么必须重启、不能同进程解锁**（三条硬约束，均可核对）：
1. `install_startup_services` 的类型门要求 `NativeOwnerServices` 且 `admissions.installation_authority is native.authority`（`startup_services.py:74-91`）。产品（非 dev、非 native）进程没有 installation authority，**即使有了 Owner binding 也构造不出执行身份**：`engine._authorization_identity` 仍是 `production_authorization_unconfigured` 403（`engine.py:119-125`）。同进程"解锁执行"在类型上是不可能事件，不是实现偷懒。
2. 每个进程只能装配一次：`assemble_owner_services` 无条件新建并安装 `LocalCopyInputService`，第二次会被 `local_copy_configuration_conflict` 拒绝（`owner_services.py:129-130`；`engine.py:90-99`）。受限进程先装配、授权后再装配第二套服务是**设计上不可行**的。
3. `assemble_owner_services` 文档明确"Trusted host/CLI startup only"（`owner_services.py:105-110`）。在请求线程里装配会让"绑定/身份/锁序"变成可被 HTTP 触发的运行期动作，违反既有信任根。

**重启契约**：授权成功 → 受限进程写 binding + 审计 + 命令收据 → `/health` 头变 `complete`，`GET /api/v1/authorization/pending` 返回 `state='complete'` 与 `restart_required=true` → 启动器（DevRuntime/桌面 host）检测到该状态后重启引擎；无启动器（手工 CLI）时 CLI 打印固定的重启命令并以 exit 0 结束。**不得**在授权完成后继续把 `/health` 说成"实例可用"，也不得在受限进程里返回假的 `ready`。

## 3 待授权对象协议

```text
application/product_authorization.py（新增，仅本 ADR 冻结形态）

class ProductAuthorizationRequest:        # 私有值对象，不进入公开契约
    format = 'product-authorization-request-v1'
    authorization_id      # 'authorization-' + sha256(instance,generation,kind,scope_sha256)[:40]
    instance_id, generation            # generation = Owner 控制面 generation（无 binding 时为 0）
    kind                  # 'owner_initialize' | 'owner_renew' | 'owner_revoke' | 'policy_install'
                          # | 'policy_select' | 'policy_revoke' | 'budget_authorize'
                          # | 'daily_creation_install' | 'daily_creation_revoke'
    scope                 # 结构化范围：owner_subject、project_ids、expires_at_us、金额上限、
                          # 目标对象引用；绝不含 secret/路径/凭据
    scope_sha256          # canonical(scope) 的 sha256，决定本次批什么
    requested_by          # {'role','pid','executable','module','launcher_origin'}
    created_at_us, expires_at_us       # 有效期 ≤ 10 min，必须 > created
    nonce                 # 128-bit hex，一次性；只在 approval 提交时使用
    state                 # pending | approved | applied | denied | expired | superseded
    result_ref            # applied 后的 commands/Owner 记录引用
```

- **存储**：pending 阶段只在进程内存（同 `_retained_consumers` 形态），**不新建表**。最终事实写两处既有位置：①Owner 动作自己的 `commands` 行与 `metadata['owner_management_binding']`（由既有 `change()` 写入）；②`Control/ProductAuthorization.json` 审计文件 + 同事务 metadata 摘要（§6）。崩溃后 pending 丢失是预期：重启重新生成，不得"恢复上一次未决批准"。
- **状态机**：`pending → approved → applied`；`pending → denied`；`pending → expired`（`engine.clock() >= expires_at_us`）；同一实例只允许一个 pending，新请求把旧的置 `superseded`（等价于 `owner_setup_one_pending` 的单槽语义）。
- **幂等**：同 `authorization_id` + 同 `scope_sha256` + 同 decision 重复提交 → 返回同一 `result_ref`；同 id 不同 scope/decision → `409 authorization_conflict`。`approve` 只在 `pending` 且未过期时生效；第二次 `approve` → `409 authorization_already_decided`。
- **并发**：进程内 RLock + 授权通道单槽；`approve` 与 Owner 写入在 `OwnerManagementControl.locked()` 内串行（复用 `change()` 的锁序：OwnerControl → ProductionControl → 短 DB writer）。两个并发 approve 只有一个能进入 writer。

## 4 确认凭据（界面"同意"提交什么）

`POST /api/v1/authorization/{authorization_id}/approve` 必须同时具备四项，缺一即拒：

| 项 | 内容 | 防什么 |
| --- | --- | --- |
| 安装会话 token | `Authorization: Bearer <VIDEO_CREATOR_API_TOKEN>`（内存值，≥32） | 非本安装调用 |
| 授权会话 secret | 每次启动生成的 128-bit `authorization_session_secret`，**只由启动器交给页面**（R1：一次性 URL fragment `#a=<secret>`；桌面壳：isolated preload 注入），API 响应/头/日志一律不回显；页面只在内存持有并放进 `X-VideoCreator-Authorization` 头 | 仅有 token 的后台进程冒用、重放上一进程的批准 |
| 一次性 nonce | 请求里的 `nonce`，服务端 `compare_digest` 并立即消费；与 `authorization_id` 绑定 | 重放/并发双花 |
| 范围哈希 | 提交 `scope_sha256`；服务端重算 canonical(scope) 比对 | 偷换批准范围（例如把项目集合换掉） |

补充约束：Origin 必须在既有 `startup_origins` 白名单内、Host 必须在 `allowed_hosts` 内、`Sec-Fetch-Site` 若存在必须是 `same-origin`；授权路由**不参与 CORS 预检放行**（不加入 `allow_origins` 之外的任何来源）、不支持 `GET` 决策（决策只有 `POST`）；`deny` 与 `approve` 一样需要四项。`nonce` 与 secret 都不落盘、不写日志、不进入审计原文（审计只记 `sha256(secret)[:16]` 指纹）。

**与 dev 自动初始化共存**：ADR0079 的 `--development-auto-owner-init` 保留、默认关闭，且与产品通道**互斥**：同一进程只允许其中一种来源（dev flag 存在时授权路由整体不挂载）。dev 来源仍写 `authentication_source='development_owner_initialization'`。产品通道写第四个字面量 `'product_authorization'`（`ManagementPrincipal.authentication_source` 扩为四值）——理由同 ADR0079 §2.4：不能把"界面点同意"记成"真人 TTY"或"dev"。

**为什么这不是新的权限放宽**：本通道的 approve 只做一件事——把"现有会话 token 已经能代表本机 Owner 做生产 API 调用"这一既有事实，转成一次**有范围、可见、可审计**的 Owner 绑定写入；它不产生 management capability（management 仍需 Owner secret + `registry.authenticate`），不产生执行身份（§2.1），不写 policy，不签 qualification。同 OS 用户的后台进程若已拿到 token，今天就能调用全部 OWNER_ONLY 端点；产品通道新增的是**知情同意与审计**，不是新特权。真正的边界仍是 ADR0036 已声明的：OS 保护不抵御同 Owner 的原生代码。

## 5 需要新接缝的位置（类型门不放宽）

- `owner_bootstrap.change()` 增加**第四分支** `elif type(confirmation_source) is ProductOwnerAuthorizationSource:`，与 ADR0079 dev 分支同形态（延迟导入、精确类型、保留表/epoch/thread/实例校验）。`None`（TTY）与 setup 分支逐字不变。
- `ProductOwnerAuthorizationSource` 只能在受限/正常进程内由授权状态机一次性签发，且必须携带：`authorization_id`、`scope_sha256`、`generation`、`nonce` 的消费回执、`instance_id`、OS 目录身份；不可序列化、不可重建、不可跨进程。
- `cli/main.py` 的 factory 命令域守卫（`:164-176`）不放宽；受限模式是**另一条启动分支**（无 factory），不经过 `install_startup_services`。
- `api/app.py` 的 `management_access`（`:146-155`）语义不变：授权路由属于"安装会话"面，不属于 management 面。

## 6 审计（不得出现"点了同意但审计缺失"）

顺序固定：**写审计 → 写 binding/命令 → 返回**。审计写失败即整体拒绝（`authorization_audit_unwritten` 503），binding 不写。

- 文件：`<data-dir>/Control/ProductAuthorization.json`（与 `OwnerManagementControl.json`、`DevelopmentOwnerInitialization.json` 同目录），JSON/LF/canonical、≤64 KiB、`xb` 创建 + `fsync` + `os.replace`，SHA256 取全文件字节。
- 同事务：metadata `product_authorization_audit` = 审计文件 SHA256，与 `owner_management_binding` 同一 `db.transaction()` 提交。
- 字段（全必填）：`format='product-authorization-audit-v1'`、`authorization_id`、`instance_id`、`generation`、`kind`、`scope`、`scope_sha256`、`requested_by`、`created_at_us`、`decided_at_us`、`expires_at_us`、`decision`、`session_secret_fingerprint`、`nonce_fingerprint`、`origin`、`caller_module`、`os_identity`（os_subject/administrator_id/directory_device/device_inode）、`result_ref`。
- 与 `owner_setup_journals`：**不写**任何 setup 行（没有 first-Goal），不占 `owner_setup_one_pending`；两者只在"都是 Owner 动作来源"这一层对齐。
- 与 `production_admissions`：无直接关系；授权本身不产生 admission，后续生产仍按各自 current/policy/rights 门逐次校验。

## 7 哪些动作走产品内授权（清单与优先级）

| 优先级 | 动作 | 走产品通道 | 说明 |
| --- | --- | --- | --- |
| P0 (R1) | 首次 Owner 初始化 `owner_initialize` | **是** | 受限进程内完成；写 binding 后重启 |
| P0 (R1) | Owner `renew` / `revoke` | **是** | 已有 binding 的正常进程可直接做（不装配执行服务即可），仍写审计 |
| P1 | policy `install`/`select`/`revoke`/`reauthorize`、预算授权（现上限内） | **是，但需 management 进程** | 受 §2.2 单装配限制，必须由独立 `owner-management` serve（一次 `for_management=True` 装配）承载；另立卡 |
| P1 | daily project creation `install`/`revoke` | 同上 | 同上 |
| 不可 | execution registration `install`/`replace`/`select`/`revoke` | **否** | 必须有 native observer/held facts（`cli/owner.py:226-246`），产品通道无权代签 |
| 不可 | installation qualification / evidence policy / benchmark / ASR 资源准入 | **否** | 需独立 authority 与真实语料，属证据准入，不是 Owner 授权 |
| R2 | 对外发布/导出授权、引用再分发 grant、付费提供方启用、unattended 预授权（规范 06 的"预授权自动制作"） | **R2** | 本 ADR 只登记清单，不设计 |

## 8 失败语义

| 情形 | 返回 |
| --- | --- |
| 受限进程访问非授权路由 | `403 owner_authorization_required`（`/health`、`/api/v1/authorization/*` 除外） |
| 无 pending / 已被 superseded | `404 authorization_not_found` |
| 已过期 | `409 authorization_expired` |
| 已 decided（含重复 approve） | `409 authorization_already_decided` |
| 同 id 不同 scope/decision | `409 authorization_conflict` |
| nonce 已消费或与 id 不符 | `403 authorization_nonce_denied` |
| 授权会话 secret 缺失/不符/已轮换 | `403 authorization_session_denied` |
| Origin/Host/`Sec-Fetch-Site` 不符 | `403 origin_denied`（复用既有码） |
| 跨实例（请求体 instance_id/generation 不符） | `409 authorization_instance_conflict` |
| 审计写失败 | `503 authorization_audit_unwritten`（binding 未写） |
| Owner 写入失败（既有校验，如项目不归该 owner） | 原码透传（如 `production_management_project_denied` 403） |
| 授权完成后仍访问执行面 | `403 production_authorization_unconfigured`（`engine.py:121`，与今天同码） |

失败一律不改变既有 binding、不写命令收据、不发 `ready` 之外的任何"成功"信号；`expired/denied` 可重新发起新请求（新 `authorization_id`）。

## 9 前端契约

- `GET /api/v1/health`：五字段不变；新增响应头 `X-VideoCreator-Authorization: pending | complete | none`（`none` = 已有 active binding 且无 pending）。**不写进 OpenAPI**（沿用 ADR0077 §5 的运行时头做法），`mode` 与 `schemas.json` 不变。
- `GET /api/v1/authorization/pending` → `ProductAuthorizationView`：`version='product-authorization-ui-v1'`、`authorization_id`、`kind`、`scope`（人类可读字段 + 原始 scope）、`scope_sha256`、`created_at_us`、`expires_at_us`、`state`、`restart_required`、`can_decide`（只在本会话未决时为真）。
- `POST /api/v1/authorization/{id}/approve`、`POST .../deny`：body = `{scope_sha256, nonce}`；头 = 安装 token + `X-VideoCreator-Authorization`。返回同上的 view（`state='complete'` 时带 `restart_required=true`）。
- `GET /api/v1/authorization/{id}`：只读回执（供页面刷新后展示，不重放决策）。
- 首次启动引导：工作台启动先读 `/health`；若头为 `pending` → 直接进入授权页（复用 `NativeSetupView` 的 phase 机：`unavailable|idle|preparing|review|confirming|applying|completed|blocked`），展示范围（owner/项目/有效期/金额上限）、"同意/拒绝"与倒计时；`complete` → 显示"需要重启完成初始化"并轮询 `/health`（或由启动器自动重启）。授权页与设置页（规范 06:63）共用外壳；审核卡片（06:67）不需要改动。

## 10 退役

- `confirm_local_action` 的 TTY 路径**保留**：headless/CI、无浏览器、启动器未注入 secret 时仍是唯一兜底；它不因本通道上线而删除或放宽。
- native setup 通道**保留**（更强：secret 不进 URL/历史，由 preload 注入）；产品通道是它的 loopback 降级形态。
- ADR0079 dev 自动初始化：产品通道在桌面壳可用后按 ADR0079 §8 退役（先清点含 dev 来源的 data-dir，再移除字面量与分支）；在此之前保持默认关。
- 本通道自身退役条件：桌面壳注入成为唯一入口（即 §4 的 R1 fragment 形态不再需要）时，删除 URL fragment 与"手输配对码"兜底，只保留 preload 注入。

## 11 与规范 06 的对应

| 规范 06 | 本 ADR |
| --- | --- |
| 模型设置页（`:63`）"能力来源/测试连接/费用/数据目的地" | 设置页承载授权入口与"待授权"卡片；费用上限就是 `scope` 里的金额上限 |
| 创建时"审核与指导 / 预授权自动制作"（`:65`） | 前者=interactive（现有审核卡片不变）；后者=unattended 预授权，属 R2（§7） |
| 审核卡片（`:67`）确认/修改意见/来源 | 不改；产品授权是**前置授权**，不是内容审核 |
| 必须设计的状态（`:89`）"等待审核…授权过期" | 本 ADR 的 `pending/expired/denied` 与 `X-VideoCreator-Authorization` 头直接对应 |

## 12 不做

- 不做同进程解锁执行（§2）；不第二次装配 OwnerServices。
- 不新增数据库表/迁移；pending 只在内存，最终事实落既有 `commands`/metadata 与 Control 目录审计文件。
- 不放宽 `install_startup_services`、`ProductionAdmissions`、`assemble_owner_services`、native 校验或任何类型门。
- 不允许配置文件/环境变量/模型输出/URL 参数直接构成授权；URL fragment 只是**传输** secret，服务端仍要 nonce+scope+token 三项。
- 不做远程访问：授权路由只在 loopback + Host/Origin 白名单内可用。
- 不让产品通道签发 execution registration、qualification、evidence policy 或发布授权（§7）。

## 13 交接

- **后端**：新增 `application/product_authorization.py`（请求/状态机/审计/`ProductOwnerAuthorizationSource`）；`owner_bootstrap.change()` 第四分支；`api/app.py` 四个授权路由 + 受限模式路由开关 + `/health` 新头；`cli/main.py` 受限启动分支（不调 `install_startup_services`）；`production_management.py` 第四个字面量。审计先于写入、nonce 单次消费、secret 不回显为硬要求。
- **集成**：启动器生成并注入 `authorization_session_secret`（R1 用 fragment，桌面用 preload）；检测 `restart_required` 后重启引擎；保证 token 只在内存、secret 不落盘。
- **前端**：授权页 + 首次引导 + `pending/complete` 轮询；复用 `native-setup-ui-v1` 的 phase 机与 `request_identity` 比对思路；不得缓存 secret 到 localStorage。
- **测试**：正例（受限启动→pending→approve→binding→审计 SHA 相等→重启后全功能）；负例（无 secret、错 nonce、重放、错 scope 哈希、过期、跨实例、非白名单 Origin、受限模式访问生产路由 403、审计写失败不写 binding、二次 approve、并发 approve）。
- **评审**：核对 §2 的三条不可能性、§4 四项凭据、§6 顺序，以及 `None`/setup 分支零 diff。
