# ADR0083：安装器供给与首次运行（Installer Provisioning and First Run）

状态：ARCHITECTURE_FROZEN_DESIGN_ONLY，2026-10-26。冻结"新实例在用户点同意之前必须先被供给什么、由谁供给、失败如何恢复、R1 安装包能交付什么、第三方如何复跑验证"。**本卡只写文档**：不改源码、不改迁移、不改契约、不新增表、不写测试、不产出安装包。§8 的验证清单全部 **NOT_EXECUTED**（仅 V6/V7 的引擎侧行为在本卡之前由真实空实例跑过，见 §0.2）。同日按用户裁定做**定点修订**：空 floor 归入供给、执行权威另立卡 ADR0084；逐条见 §0.3 与 §2.2/§3.3/§5.1/§7/§8/§9。

## 0 实读证据（行号取 HEAD `3f039df`；`vc/` = `services/engine/src/video_creator`）

| 事实 | 位置 |
| --- | --- |
| 无 Owner binding 时引擎**允许监听**但只挂 `/health` 与 `/api/v1/authorization/*`；其余 403 `owner_authorization_required` | `vc/cli/main.py:415`；`vc/api/app.py:142-155` |
| 受限分支不装配 OwnerServices、不登记执行身份、不读 admissions | `vc/cli/main.py:411-415,444-462` |
| 产品内 approve 只写有范围的 Owner binding；**不创建** management secret | `vc/application/owner_bootstrap.py:317-322` |
| management registry 对 `product_authorization` 来源直接 403 | `vc/application/owner_bootstrap.py:385-394` |
| 产品通道的 approve 只允许 `owner_initialize` | `vc/cli/main.py:451`；`vc/application/product_authorization.py:82-83` |
| 没有 factory 时 `install_startup_services` 直接返回 `None`（不装配任何服务） | `vc/cli/startup_services.py:56-62` |
| 无执行身份时任何执行都 403 `production_authorization_unconfigured` | `vc/application/engine.py:140-146`；`vc/application/bundle_authorization.py:117` |
| `configure_production_authorization` 只在 `execution_registration is not None` 时被调用 | `vc/application/owner_services.py:145-154` |
| 非 worker 的 `serve` 没有 factory 就没有 installation authority ⇒ 无执行身份 | `vc/cli/main.py:426-427`；`vc/application/owner_services.py:145-147` |
| `Control/` 目录与 `OwnerManagementControl.json` 由 `change()` 自己创建（首启 `folder.mkdir` + `initialize_new`） | `vc/application/owner_bootstrap.py:211-213,277-280` |
| `Control/ProductionAuthorizationControl.json` **不会**由 `change()` 创建（是另一个 floor） | `vc/application/production_management.py:107-125` |
| 该 floor 缺失时任何 control 读取点 503 `production_control_unconfigured` | `vc/application/production_management.py:128-131,159-161` |
| 完整装配前必须已有空首启 floor（否则 `assemble_owner_services` 路径死锁） | `vc/cli/development_host.py:490-510`；`vc/application/development_owner_initialization.py:600-618` |
| 生产路径没有任何管理动作会创建该 floor；唯一创建者是 dev 宿主 | `vc/application/product_authorization.py:608-658`；`vc/cli/development_host.py:506`（全仓仅此一处调用） |
| 唯一"只写 empty-first floor"的产品口径实现（四张授权表必须全空） | `vc/application/product_authorization.py:609-623,639-650`；表清单 `:82-83` |
| 但该实现要求 binding 已是 `product_authorization` 来源 ⇒ 安装器**不能**复用它（同意之前没有 binding） | `vc/application/product_authorization.py:631-634` |
| floor 的原子写（`.pending` + `fsync` + `os.replace`） | `vc/application/production_management.py:170-190` |
| Owner 目录 OS 身份（主体/设备/inode）只能由真实目录取得，且不得跨链接 | `vc/infrastructure/owner_identity.py:107-129` |
| Owner binding 绑定 OS 主体与目录 inode，换机/换目录即拒 | `vc/application/owner_bootstrap.py:78-95,88-94` |
| Owner 范围要求每个 project 真实存在且 `owner==local-user` | `vc/application/owner_bootstrap.py:113-121` |
| 项目 id 由引擎随机生成（不可预知，注册必须事后绑定） | `vc/application/engine.py:279` |
| `register_route` 只校验 `verified` 与非 official，**无** Owner/管理校验；重复登记是 UPSERT | `vc/application/engine.py:239-246` |
| 未登记路由时执行 503 `route_unavailable`，且该码在 `RESOURCE_WAIT_CODES` 里（worker 会 park 而不是失败） | `vc/application/engine.py:248-253`；`vc/application/media_registration.py:46-52` |
| 注册文件必须由启动器钉定文件+SHA 才能启用；不一致 503 | `vc/cli/main.py:188-209,396-406`；`vc/application/media_registration.py:142-147` |
| `engine_source_sha256` 只计 `.py`，从 `PACKAGE_ROOT` 实算 | `vc/application/media_registration.py:44-45,89-101,113-126` |
| 冻结产物刻意保留 `.py` 源作为 data（否则上述全集算不出来） | `packaging/engine/Engine.spec:10-13` |
| 冻结入口负责迁移目录、UTF-8 与 ffmpeg 参数 | `packaging/engine/Entry.py:12-32` |
| 引擎固定 commit 构建、写收据；收据明确排除 Tauri 壳与安装器 | `tools/build/BuildEngine.mjs:10,55-56` |
| 工作台必须由受信 host 注入 managed-proxy 描述符；静态构建下该字面量是 `undefined` | `apps/workbench/vite.config.ts:22-28,55`；`apps/workbench/src/engine.ts:20-21,53`；`apps/workbench/src/main.tsx:21` |
| 引擎不服务静态工作台（只有资产/媒体 `FileResponse`） | `vc/api/app.py:450,468` |
| dev 宿主三条件里的 frozen 拒绝发生在最前 | `vc/cli/development_host.py:441-443,535-537` |
| 现"供给者"是一次性脚本：ACL → 建项目 → 生成注册 → TTY owner-init → 登记路由（glob `Routes/*.json`，含 asr 共五条）→ `serve-dev` | `Codex/.../LocalInstallationRegistrationBuild/RunLocalChain.ps1:201-208,209-216,218-249,274-314,331-338,340-364` |
| 该脚本的只读观测工具（`source-status` / `ensure-project` / `owner-status`）可被第三方复跑 | 同目录 `PrepareLocalChain.py:41-68,71-91,94-125` |
| 独立注册校验（六项，含真实 `RegisteredMediaRuntime` 构造） | 同目录 `check_local_registration.py:214-238` + `--runtime` |
| 真实注册切片：192 个引擎源、`Package/`+`AsrPackage/` 相对路径、五条 route id | 同目录 `Registration.json`；`Routes/{input_audio,input_visual,edit,master_index,asr}.json` |
| 已实测：产品内授权真实可用（受限启动→approve→重启→`/health: none`→`/projects 200`） | `PROGRESS.md`「2026-10-25 24:00 前后」节 |

### 0.1 本卡冻结前必须核清的四件事（结论如下）

1. **"注册路由/写资源清单"在能力定义上不是 management 动作。** `register_route`（`engine.py:239-246`）只要求 `verified=True` 且非 official；`create_project`（`engine.py:255,268-298`）是 owner 作用域内的普通写入；`ProductionAuthorizationControl.initialize_new()`（`production_management.py:192-197`）是普通方法，写入的是 `minimum_revision=0` 的空 floor。三者**都不持有 `AdministrationCapability`、不经 `registry.authenticate`、不写 policy/admission**。因此它属于"安装器职责的配置写入"，不属于"管理能力动作"——这正是它能与 ADR0081「产品内授权不授予管理能力」共存的技术原因（§3.2）。
2. **但它是 management 动作的替代品，不能由产品内授权代做。** ADR0081 §7 已把 policy/execution registration/qualification/evidence 永久移出产品通道；本卡不扩大该通道，只把"配置事实"提前到安装时（§3.2 理由 R2）。
3. **Owner 控制文件不是供给项。** `Control/OwnerManagementControl.json`、`metadata['owner_management_binding']`、`commands` 行、`Control/ProductAuthorization.json` 全部由 `change()` 在真人同意时按固定顺序写入（`owner_bootstrap.py:211-376`）。安装器写它们等于伪造同意。安装器只建 **`Control/` 目录本身**（因为 `change()` 会自己建，安装器建只是为了提前切 ACL/inode 基线）与**空 production floor**（§2 C 组 vs B 组）。
4. **产品路径今天缺一次 floor 引导，且只被 dev 补过。** 全仓唯一调用 `create_product_authorization_control` 的位置是 `cli/development_host.py:506`；产品 `serve` 分支没有等价调用。结论：该 floor 必须由供给写入（B4），否则"已同意 Owner 的重启"在第一个 control 读取点 503。注意该既有实现**不能**被安装器直接复用：它在 `:631-634` 要求 binding 已是 `product_authorization` 来源——同意之前没有 binding，所以供给器只能复用它的**判定**（四表全空 + `instance_id` 相符 + empty-first），复用不了它的前置。该 503 本卡 **NOT_EXECUTED**（依据是 `:609-623` 的 docstring 与 dev 侧同一 bootstrap gap 的既有记录），实现阶段必须在真实安装实例上先复现再修。

### 0.2 已实测与未实测的分界

| 项 | 状态 |
| --- | --- |
| 受限启动、`/health: pending`、四项凭据 approve、审计先于 binding、`restart_required`、重启后 `none` + `/projects 200` | **已实测**（真实空实例，2026-10-25，见 `PROGRESS.md`） |
| 产品内 approve 不产生 management secret（registry 403） | 源码路径已核（`owner_bootstrap.py:317-322,385-394`）；registry 403 的运行时观测 **NOT_EXECUTED** |
| 全新实例缺路由时 `route_unavailable` | **已实测**（本卡委托人 2026-10-26 报：起引擎即 503） |
| 全新实例缺 `Control/ProductionAuthorizationControl.json` 时 `production_control_unconfigured` | **NOT_EXECUTED**（仅 dev 侧同源记录 + docstring） |
| 本卡的供给器、启动器、`InstallationProvisioning.json`、升级/卸载路径 | **全部 NOT_EXECUTED**（本卡只冻结形态） |
| 冻结产物内 `_package_sources` 覆盖"安装树 `.py` data" | **NOT_EXECUTED**（依据 `Engine.spec:10-11` 的 datas 与 `Entry.py:14` 的 `_MEIPASS`；实现阶段必须实测一次全集相等） |

### 0.3 定点修订（2026-10-26 用户裁定，覆盖本卡初稿的两处留白）

本卡初稿把"空 floor 由谁写"与"执行权威怎么办"开成待决。用户已裁定，以下是**有效条文**，与初稿冲突处以本节为准。

**裁定 1：空 floor 由安装器在供给阶段写入。**

- 理由：floor 是"花费/单位上限"，`minimum_revision=0` 等于**授权不了任何东西**；它不是授权授予，而是让控制面处于"**存在但为空**"的确定状态。不写才会出现 `production_control_unconfigured` 这种"已装好却不能用"的中间态（`production_management.py:128-131,159-161`）。
- 约束（三条，缺一即不得写）：①**可审计**——`InstallationProvisioning.json` 必须记录该 floor 为空（`minimum_revision=0`、`pending_request_sha256=null`）及其全文件 SHA；②**同批完成**——与实例 ACL（B1）在同一次供给里完成，不得拆成两次；③**不得顺带授权**——不得写入任何非零额度、任何 `budget_groups` 行、任何 policy/admission。
- 落地位置：§2.2 B4（动作与前置）、§2.4 D 组（禁止项）、§3.3（供给 ≠ 同意）、§5.1 INV-3（新增不变量）。

**裁定 2：执行权威认账，单独立卡 ADR0084《ProductTrustedStartupAuthority》。**

- 认账事实：frozen 无 factory ⇒ `install_startup_services(None,…)→None`（`startup_services.py:56-62`）⇒ 无执行身份 ⇒ 制作 403 `production_authorization_unconfigured`（`engine.py:140-146`）。R1 **不能**停在"只能浏览"。
- 该卡冻结：权威四要素＝**安装记录 + 实例 OS 所有者/ACL 身份 + registration sha + 资源清单 sha（+ 安装目录与实例目录的固定关系）**；构造在 trusted startup（监听前）；授予"制作/发布"、**不授予**任何 management 能力；与 ADR0081 的关系是"Owner 同意只写 binding，执行权威来自安装事实，二者互不替代"；失败具名；诚实边界写明同账户伪造不可防。
- 三条禁止（本卡同样适用）：禁止复用 dev 三重条件；禁止环境变量/配置文件直接构成 authority；禁止伪造 `InstalledProductionEvidence`/`NativeLaunchContext`/qualification。
- 落地位置：§7-6、§9 后继 1、ADR0084 全文。

**对 §8 的影响（不改结论，只定顺序）**：V1-V11 仍是 **NOT_EXECUTED**，且**没有 `installer-admin provision` 实现就无法执行**（V1/V3/V4 直接依赖它写的记录、路由行与 floor）。固定顺序：①后端实现供给（含空 floor，§2.2 B1-B6）；②测试角色在**真实安装实例**上跑 V1-V11 并登记 `docs/acceptance/criteria/COMMANDS.md`；③评审/验收。本卡不预填任何通过结论。

## 1 结论摘要

1. **供给是一类独立动作**：只写"可核对的配置事实"（程序/资源文件、注册文件、五条路由行、Owner 项目行、空 floor、ACL、供给记录），不产生任何 capability、不写 policy/admission/execution registration/qualification/evidence、不建立任何 secret。
2. **供给由安装器一次完成**（不是首次启动的管理进程）。唯一理由链见 §3.1：注册必须绑定"已落盘字节 + 随机项目 id"，而这只有装完之后、Owner 之前才是可算的；首启的管理进程在 ADR0081 下不存在（受限进程不装配、无 management 能力）。
3. **实现形态固定为"引擎内的一次性无监听子进程"**：新增 `installer-admin provision` 子命令域（与 `evidence-admin install` 同形态，`cli/main.py:171-177,353-358`），由安装器/启动器以固定参数拉起；**用户永不输入命令**。它必须复用引擎自己的 `_package_sources`/`_local_file`/`_hash`（`media_registration.py:89-126`），不能另写一套遍历（ADR0077 §3.4 同一纪律）。
4. **用户只做一次产品内确认**：安装 → 双击启动 → 授权页 → 点"同意" → 启动器自动重启 → 五步工作台。全程无终端。
5. **三条不变量**（§5.1）：永不出现"有 Owner 但无路由/无注册/无 floor"；永不把"有路由但无 Owner"当成可用实例；供给完成时 **floor 必须存在且为空**（`minimum_revision=0`、无 pending），此后只由真实管理动作推进，供给器永不回写。
6. **R1 安装包可交付**：引擎 onedir（固定 commit）+ 资源（FFmpeg/字体/许可/迁移）+ 可选 ASR 包 + 静态工作台 + 启动器（静态+loopback 代理）+ 安装时生成的注册与供给记录。**明确不做**：签名安装器、Tauri 桌面壳、自动更新、macOS/Linux 包、服务化常驻、静默安装（§7）。
7. **执行权威不在本卡，另立 ADR0084《ProductTrustedStartupAuthority》**（§0.3-2）。事实：冻结产物无 factory ⇒ `install_startup_services(None,…)→None` ⇒ 无执行身份 ⇒ 制作端点 403 `production_authorization_unconfigured`。该卡用**安装记录 + 实例 ACL/OS 所有者 + registration sha + 资源清单 sha** 构造产品形态受信启动权威，**不得**用 dev 三重条件、环境变量/配置文件或伪造对象绕过；实现前 R1 包不得宣称"可制作"。
8. **`serve-dev`/`worker-dev` 保留为开发者路径**，明确标注非产品、不进启动器、不可由安装包触达（§6）。

## 2 供给内容清单（逐项：写入方 / 时机 / 是否需要管理能力 / 审计）

四组：**A 组**＝安装器写文件；**B 组**＝引擎内 `installer-admin provision` 写实例数据；**C 组**＝用户同意时由引擎写（不是供给，列出以避免混淆）；**D 组**＝谁都不写。

### 2.1 A 组：文件与资源（写入方＝安装器；时机＝安装；需要管理能力＝**否**；审计＝供给记录 `items.<id>`）

| # | 项 | 精确内容 | 说明 / 失败后果 |
| --- | --- | --- | --- |
| A1 | 程序目录 | 引擎 onedir（`VideoCreatorEngine.exe` + `_internal/video_creator/**.py` 源 data + 依赖） | 由固定 commit 构建（`BuildEngine.mjs`）；`.py` 源必须在树内，否则 `engine_source_sha256` 全集算不出来（`Engine.spec:10-11`） |
| A2 | 媒体资源 | `Resources/Media/**`（FFmpeg 11 件 + `LICENSE.txt`）+ `Fonts/…otf` + `Licenses/*` + `Media/manifest.json`（逐件 bytes/sha256） | `Entry.py:23-28` 每次 `serve` 自检，不等即 `bundled_resource_changed` |
| A3 | 迁移 | `Resources/Migrations/*.sql`（当前 11 个） | `Entry.py:15` 用 `VIDEO_CREATOR_MIGRATIONS_DIR` 指向它；供给与首启都必须用同一份 |
| A4 | ASR 资源（可选组件） | `AsrPackage/**` + `AsrPackage/ResourceManifest.json` | 缺失时注册的 asr 四联必须为 `null`（诚实降级），**不得**写假 SHA；装了但缺文件 → `asr_resource_changed` |
| A5 | 静态工作台 | `Workbench/**`（`apps/workbench` 生产构建 dist） | 引擎不服务静态（只有资产 `FileResponse`），必须由启动器提供（§7-启动器） |
| A6 | 启动器 | `VideoCreatorLauncher.exe`（loopback 静态 + `/api` 代理 + token/secret 注入 + 供给门 + 重启编排）+ 快捷方式 | token 只进子进程环境，**不得**进页面/日志/文件（ADR0081 §4） |
| A7 | 路由输入 | `Routes/{input_audio,input_visual,edit,master_index,asr}.json`（`CapabilityRoute`，`source=owned_local`、`verified=true`、零成本、`credential_ref=null`） | 只是登记输入；生效在 B5。当前 `check_local_registration.py:214-238` 只核前四条，asr 需另核 |
| A8 | 注册与清单 | `Registration.json`（`registered-media-config-local-v1`）+ `Package/RuntimeFileManifest.json` + `Package/LocalMaterialResources.json` | 三者必须在**同一次原子产出**里生成，且 `Registration.json` 必须落在能让 `Package/`、`AsrPackage/` 相对路径解析的根（现布局：注册在 delivery 根，资源在 `Package/`） |

A8 的关键约束（不可省）：

- `engine_source_sha256` 的键集合必须**逐字等于**安装树内 `_package_sources(PACKAGE_ROOT)` 的结果，哈希用 `_hash`（`media_registration.py:89-101`）；禁止手抄、禁止另写遍历。
- `rights_declaration.project_ids` 必须**恰好**是 B3 建出的项目 id（**一个**，不得为空/多值/占位）；`declaring_subject` 固定 `local-user`。
- 四/五个 `*_route_id` 必须与 A7 的文件逐字一致，否则 `check_routes`（同文件 `:214-238`）直接失败。
- 资源路径（`ffmpeg`/`ffprobe`/`production_resource_manifest`/`asr_resource_manifest`）是相对注册根的 POSIX 路径，必须与实际安装布局一致；相对名不得含前导 `/`、反斜杠、`:`、空段、`.`、`..`（`held_authority.py:47-51` 同一命名纪律）。

审计：A 组每项在供给记录里记 `{id, path, bytes, sha256, count}`；A8 额外记 `registration_sha256`（供启动器钉定 `--production-config-sha256`）。

### 2.2 B 组：实例数据（写入方＝引擎内 `installer-admin provision`；时机＝安装末（A 组之后）；需要管理能力＝**否**；审计＝供给记录 + DB 行）

| # | 项 | 精确动作 | 前置 | 幂等语义 |
| --- | --- | --- | --- | --- |
| B1 | 数据目录 + ACL | 建 `<data-dir>`（`%LOCALAPPDATA%\VideoCreator\Instance`，绝对、非 UNC、非 junction）；**先** `/inheritance:r`，再只授予当前用户 SID 与 `NT AUTHORITY\SYSTEM` `(OI)(CI)F` | 目录可建、路径不跨链接（`owner_identity.py:108-112`） | 已存在则只校验 ACL，不重写更宽 |
| B2 | 实例与迁移 | `EngineService(data_dir)`：跑迁移到当前 `user_version`（当前 11），写入 `metadata.instance_id` | B1 | 已存在则只补迁移，**不**重生 instance_id |
| B3 | Owner 项目 | `create_project('local-user', ProjectInput(name=…))`，或按 `(name, owner)` 复用现有一行 | B2 | 按名复用；**不隐式**建第二个项目 |
| B4 | 空 production floor（**由安装器在供给阶段写入**，见 §0.3-1） | 写 `Control/ProductionAuthorizationControl.json`：`minimum_revision=0`、`pending_request_sha256=null`、`instance_id` 相符；**仅当**四张授权表（`production_authorization_policies`/`production_admissions`/`daily_project_authorizations`/`execution_registrations`）全空。前置是"四表全空 + 实例相符"，**不是**"已有 binding"（同意之前没有 binding，故不能复用 `product_authorization.py:631-634` 的入口，只复用 `:639-650` 的判定）。三条约束：记录进供给记录（含文件 SHA）、与 B1 同批完成、**不得**写非零额度/`budget_groups`/policy | B2 | 已存在且是 empty-first → 采纳；已存在且不是 → 拒绝（不覆盖） |
| B5 | 五条路由行 | 逐份 `Routes/*.json` → `engine.register_route`（`routes` 表 UPSERT by `route_id`） | B2；A7 | 重复登记=UPSERT；`route_id` 相同但 body 变化=重新登记（见 §5.3 升级） |
| B6 | 供给记录 | `Control/InstallationProvisioning.json`（`installation-provisioning-v1`）：`complete`、`installer_version`、`provisioned_at_us`、`instance_id`、`project_id`、`registration_sha256`、`items[]`、`counts{}`、`revision`；**另含权威锚点**（ADR0084 §3.1）：`install_root`、`engine_package_relative`、`instance_dir`、`os_subject`、`administrator_id`、`instance_device`、`instance_inode`、`resource_manifest_sha256`、`runtime_manifest_sha256`、`expected_files`、`engine_file_names`、`dacl_summary_sha256`。**同一文件就是启动器钉定的 `--installation-record`**（ADR0084），不另立第二份记录 | A+B 全部完成并逐项复算通过 | 原子写（`.pending`+`fsync`+`os.replace`，同 `production_management.py:170-190`）；`revision` 单调递增，历史条目只追加 |

B4 为什么必须由供给写（三条，逐条可核）：

1. 它是"零授权的空 floor"，`initialize_new()` 写入的 `minimum_revision=0` 不授予任何东西（`production_management.py:192-197`）；它与"第一次真实管理动作"写的内容完全相同，只是时机提前。
2. 产品路径没有任何管理动作会写它（`change()` 只写 `OwnerManagementControl.json`，`owner_bootstrap.py:277-280`），而完整装配要求它已存在（`development_host.py:490-510` + `product_authorization.py:609-623`）。
3. 它的写入前提可被第三方核验：四张授权表全空 + `instance_id` 相符 + empty-first（`product_authorization.py:639-650` 同一判定）。

B5 的诚实边界：`register_route` 没有能力校验（`engine.py:239-246`）。因此"路由由安装器写"不是授权边界，而是**时序与记录**约束：任何同 OS 用户的原生进程今天就能改这些行（ADR0036 已声明的边界不变）。本卡不新增 HTTP/MCP/模型可达的路由写入口。

### 2.3 C 组：用户同意时写入（**不是供给**，列出以防混淆）

| # | 项 | 写入方 | 时机 | 管理能力 | 审计 |
| --- | --- | --- | --- | --- | --- |
| C1 | `Control/` 目录（0700）+ 目录身份基线 | `change()`（`owner_bootstrap.py:211-213,229-236`） | 点"同意" | 否 | ProductAuthorization.json |
| C2 | `metadata['owner_management_binding']` + `commands` 行 | `change()` 事务（`:347-369`） | 点"同意" | 否 | 同上 + commands |
| C3 | `Control/OwnerManagementControl.json`（empty-first） | `change()`（`:277-280`） | 点"同意" | 否 | 同上 |
| C4 | `Control/ProductAuthorization.json`（先于 binding） | approve 路径 | 点"同意" | 否 | metadata `product_authorization_audit` = 文件 SHA |
| C5 | **Owner 管理 secret：不写** | 产品来源分支跳过 `secrets.create`（`:317-322`） | — | — | 由 §8 V8 负例证明 |

### 2.4 D 组：谁都不写（供给与产品通道都不得产生）

**三条硬禁止**（用户 2026-10-26 要求逐条写入）：①**安装器不得写 Owner 控制文件**（`Control/OwnerManagementControl.json`、`Control/ProductAuthorization.json`、`metadata['owner_management_binding']`、`owner.bootstrap.*` 命令行）——那是同意而非供给；②**安装器不得建 management secret**（不调 `secrets.create`，不向 OS vault 写 `VideoCreatorOwnerManagement` 条目）；③**安装器不得写任何 policy / qualification / evidence**（含 evidence policy、benchmark、admission、installation qualification）。

其余禁止项：任何 `production_authorization_policies`、`production_admissions`、`daily_project_authorizations`、`execution_registrations` 行；**任何非零 floor 额度、任何 `budget_groups` 行**（floor 只允许 `minimum_revision=0` 的空首启态）；unattended 预授权；任何 `VIDEO_CREATOR_DEVELOPMENT_INSTALLATION`、`--development-registration*`；任何 HTTP/MCP 可达的注册或路由写入口；任何"跳过确认"的开关。

## 3 谁执行供给

### 3.1 结论：**安装器，安装时一次性执行**；执行体是引擎内的 `installer-admin provision` 一次性子进程（无监听、不装配 OwnerServices）

四条理由，按硬度排序：

- **R1（字节可算性）**：注册的 `engine_source_sha256` 必须等于**已落盘字节**的全集（`media_registration.py:113-126`）；冻结产物里 `PACKAGE_ROOT` 指向 `_MEIPASS/video_creator`（`Engine.spec:10-11` 把 `.py` 作为 data 落在那里）。只有装完之后，在同一进程内调用 `_package_sources` 才能得到不会被后续复制污染的集合。放到首次启动再做，等于允许"装完 → 首启之间"被替换而无人复算。
- **R2（首启没有可写配置的进程）**：若把供给放到首次启动，那个进程只能是 `serve`。而无 Owner 时 `serve` 走受限分支（`main.py:415`），不装配服务、不持有管理能力（`owner_bootstrap.py:317-322,385-394`），在请求线程里写路由/项目会把 trusted startup 动作搬到可被 HTTP 触发的运行期——这正是 ADR0081 §2 第 3 条判定不可的事。要绕开它就得再引入"第二个首启进程/第二套状态机"，复杂度与风险都高于"安装时做完"。
- **R3（顺序天然正确）**：注册必须绑定项目 id，而项目 id 随机（`engine.py:279`），所以顺序只能是"建实例 → 建项目 → 生成注册 → 登记路由 → （用户）同意"。安装时正好覆盖前四步；用户同意是最后一步，且**只做一次**。
- **R4（可审计）**：一次安装 = 一份 `InstallationProvisioning.json`（安装版本、逐件 SHA、实例 id、项目 id、注册 SHA）。升级时 `revision+1`、旧记录只追加不改写，第三方可对任意时点复算。

### 3.2 与「产品内授权不授予管理能力」如何不冲突

| 维度 | 供给（本 ADR） | 产品内授权（ADR0081） |
| --- | --- | --- |
| 执行身份 | 安装器/受信启动进程，OS 用户身份 | 受限引擎进程 |
| 是否持有 `AdministrationCapability` | **否**（不经 `registry.authenticate`） | **否**（`owner_bootstrap.py:317-322` 跳过 secret） |
| 写入对象 | 文件字节、配置行（routes/projects）、空 floor、ACL | 一次 Owner binding + 审计 |
| 是否构成"同意" | **否**。它不写 binding、不写 policy、不写 admission | **是**。它是唯一的 Owner 同意动作 |
| 谁保证边界 | 安装目录 ACL + 用户双击安装 + 引擎内的固定校验 | 四项凭据 + 审计先于 binding |
| 失败是否可回退 | 是（删数据目录/重装/修复模式） | 是（不写 binding，重新发起） |

一句话：**供给只写"事实配置"，同意才写"授权"**。二者既不同时、也不同主体、也不同写入集合；供给能成立恰恰因为**它不需要管理能力**——如果需要，它就会撞上 ADR0081 刻意不授予管理能力的决定。

再补一条反面证明：如果让安装器去创建 management secret（走 C5 的相反路径），它就必须调 `secrets.create` 并落 OS vault，之后 `PersistentOwnerManagementRegistry` 会把该来源当成可用管理身份——那就等于用安装器**绕过** ADR0081 的核心决定。本 ADR 明文禁止（D 组）。

### 3.3 三条硬禁止与一句界分（供给 ≠ 同意）

| # | 禁止 | 依据 / 违反后果 |
| --- | --- | --- |
| 1 | 安装器**不得**写 Owner 控制文件（`OwnerManagementControl.json`、`ProductAuthorization.json`、`metadata['owner_management_binding']`、`owner.bootstrap.*` 命令行） | 这些只能由 `change()` 在真人同意时写（`owner_bootstrap.py:211-376`）；安装器写＝伪造同意，且会让 `current()` 读出"真人已同意"的假陈述 |
| 2 | 安装器**不得**建 management secret（`secrets.create` / OS vault `VideoCreatorOwnerManagement`） | 会让 `PersistentOwnerManagementRegistry` 拿到可用管理身份（`owner_bootstrap.py:385-394` 只拦 `product_authorization` 来源），等于绕过 ADR0081「产品内授权不授予管理能力」 |
| 3 | 安装器**不得**写任何 policy / qualification / evidence（含 benchmark、admission、installation qualification） | ADR0081 §7 已把它们永久移出产品通道；安装器更无权代签，且它们需要独立 authority 与真实语料 |

**界分一句话**：**安装器供给 ≠ 用户同意**。供给把实例变成"配置齐全、**零授权**、只等一个人点同意"的状态（空 floor 的 `minimum_revision=0` 就是这一点的机器可读证据）；同意把 binding 写进 `metadata` 并留审计。前者由安装器以 OS 用户身份完成，后者只能由真人在产品内完成；两者写入集合无交集，且**供给不做任何一件事能让实例获得执行能力**——执行能力来自 ADR0084 的受信启动权威，且该权威**仍然**要过 Owner binding 与 `assemble_owner_services` 的现有门。

## 4 用户可见流程（全程无终端）

### 4.1 时序

| 步 | 用户看到 | 实际发生 | 真实产物 |
| --- | --- | --- | --- |
| 1 | 双击 `VideoCreatorSetup-<ver>.exe`；选安装位置；**无 UAC 提升**（per-user 安装） | 校验包完整性，解包 | `<Install>/…`（A1-A6） |
| 2 | 进度："复制程序" → "检查资源" → "准备本机实例" | 逐件复算并写清单；拉起 `VideoCreatorEngine.exe installer-admin provision --install-root … --data-dir …`（一次性、无监听） | A7/A8、B1-B6 |
| 3 | "安装完成，正在启动 VideoCreator"（可取消自动启动） | 启动器：读供给记录 → `complete` 且逐件 SHA 复算相等 → 起引擎 `serve` | 引擎监听 `127.0.0.1:<port>`（token/secret 只进子进程环境） |
| 4 | 浏览器窗口打开 → 直接落在**授权页**（不是终端） | 引擎发现无 Owner binding → 受限分支（`main.py:415`）；启动器注入 `#a=<secret>`；页面读 `/health` 得 `X-VideoCreator-Authorization: pending` | 只可达 `/health` 与 `/api/v1/authorization/*`；其余 403 `owner_authorization_required` |
| 5 | 授权页展示范围：Owner=`local-user`、项目名、有效期、零成本、无外发；"同意 / 拒绝" + 倒计时 | `GET /api/v1/authorization/pending` → `product-authorization-ui-v1` | pending 仅在内存 |
| 6 | 点"同意" | 四项凭据（token + `X-VideoCreator-Authorization` + nonce + `scope_sha256`）→ 写 `Control/ProductAuthorization.json`（先）→ `change('initialize')` 写 binding/commands（后） | C1-C4；返回 `state=complete, restart_required=true` |
| 7 | "需要重启完成初始化"，随后窗口自动重连 | 启动器检测 `restart_required` → 停引擎 → 重启（**不做同进程解锁**，ADR0081 §2） | 新进程重新装配 |
| 8 | 五步工作台（规范 06） | `/health` 头 `none`；`/projects` 200 | 若执行权威未就绪，工作台显示具名阻断卡（§7-6），不伪装"可用" |

### 4.2 供给完成门（启动器职责，不改引擎校验）

启动器在**起引擎之前**必须：读 `Control/InstallationProvisioning.json` → `format` 相符、`complete=true`、`instance_id` 与数据目录实际实例相符、`items` 逐件 SHA 复算相等、`registration_sha256` 与实际 `Registration.json` 相等、五条 route id 与注册声明的 route id 逐字相等。任一不成立 → **不启动引擎**，显示具名错误（§5.2），提供"修复安装"入口。

这个门放在启动器而不是引擎，理由：①不改任何生产校验（`install_startup_services`/`assemble_owner_services`/`ProductionAdmissions` 一行不动）；②启动器本来就是 trusted startup 的位置（ADR0077/0081 一致）；③失败时用户看到的是安装问题，而不是"引擎 503"。

### 4.3 首启的三种可见状态（必须互斥，不得混）

| 状态 | 页面 | 边界 |
| --- | --- | --- |
| 供给未完成 | 启动器错误页（无引擎） | 不出现授权页；不允许用户在此状态点同意 |
| 供给完成、无 Owner | 授权页（`X-VideoCreator-Authorization: pending`） | 只可达 health 与授权路由 |
| 供给完成、有 Owner | 五步工作台（`none`） | 执行能力另受执行权威门（§7-6） |

## 5 失败与恢复

### 5.1 两条不变量

- **INV-1：永不出现"有 Owner 但无路由/无注册/无 floor"。** 三道防线叠加：①供给完成门在授权页之前（§4.2）；②供给顺序固定 A→B，且 B6 是最后一步；③即使门被绕过，重启后会以 `production_configuration_missing`/`production_configuration_changed`（`main.py:199-204`）、`route_unavailable`（`engine.py:248-253`）、`production_control_unconfigured`（`production_management.py:159-161`）**明确失败**，不会静默降级。此时 Owner 已存在，恢复只能走"补齐供给"（§5.3 修复模式），**不得**重新授权、不得删 binding。
- **INV-2：永不把"有路由但无 Owner"当成可用实例。** 这是安装后的正常中间态，且被 ADR0081 的受限启动精确覆盖：`/health` 与授权路由之外一律 403 `owner_authorization_required`（`app.py:142-155`），并且该状态**没有**执行身份（`serve` 无 factory ⇒ `startup_services.py:61-62`）。
- **INV-3：供给完成时 floor 必须存在且为空。** "存在"＝`Control/ProductionAuthorizationControl.json` 在 B6 之前已落盘且 SHA 进了供给记录；"为空"＝`minimum_revision=0` 且 `pending_request_sha256=null`，且四张授权表全空（`product_authorization.py:639-650` 同一判定）。三条推论：①缺失 = 供给失败（`installation_provisioning_incomplete`），不是"首启自愈"；②非空 = 拒绝写入（`installation_provisioning_denied`），因为那意味着这个目录已经历过管理动作、不是新实例；③此后 floor 只允许被**真实管理动作**推进（`reserve`/`complete`），供给器与修复模式**永不回写** floor，也永不写入非零额度或 `budget_groups`。INV-3 的意义是把"已装好却不能用"（`production_control_unconfigured`）与"装好就被授权"（非零 floor）两种坏态同时排除。

### 5.2 失败码表（供给器/启动器词汇；发生在监听之前，因此**不是** HTTP 响应）

| code | 阶段 | 含义 | 是否留下状态 |
| --- | --- | --- | --- |
| `installation_provisioning_unavailable` | 供给 | 非安装器调用 / 参数不全 / 目标不可写 | 无 |
| `installation_provisioning_denied` | 供给 | 目标目录跨链接；已存在非 empty-first floor；目录已属别的实例；试图覆盖既有 binding | 拒绝前不写 |
| `installation_provisioning_conflict` | 供给/启动 | 数据目录实例与供给记录实例不符（换目录、恢复他人库） | 保留原状，拒绝继续 |
| `installation_provisioning_incomplete` | 启动门 | 记录缺失/`complete=false`/SHA 不符/路由缺失 | 引擎不启动 |
| `installation_registration_stale` | 升级 | 注册声明的引擎哈希 ≠ 安装树实算全集 | 拒绝启动（上层同义 503 `production_configuration_changed`） |
| `installation_upgrade_required` | 升级 | 程序版本与供给记录版本不一致且未完成换 pin | 提示升级 |
| `installation_uninstall_denied` | 卸载 | 存在 Owner binding 且未二次确认删数据 | 数据保留 |

审计口径：以上错误以 `{"code","message"}` 单行 JSON 打到 stderr、exit 1（与 `main.py:510-514` 同形态），并抄送一份到 `<data-dir>\Control\InstallationProvisioning.json` 的 `last_failure`（若数据目录已存在）。

### 5.3 半完成 / 重复安装 / 升级 / 卸载

| 情形 | 固定处理 |
| --- | --- |
| **供给中途失败** | 记录先落 `complete=false` + `failed_step` + `counts`（`xb` 首建，之后原子替换）。程序目录可整体重装；数据目录若由本次新建且**无** binding → 整体移到 `<data-dir>.failed-<stamp>` 后重建；已有 binding → 只走修复，不删 |
| **崩溃窗口 C1**：程序文件写一半 | 重装覆盖程序目录（A 组幂等）；数据未动 |
| **崩溃窗口 C2**：迁移一半 | SQLite 迁移在事务内；下次 `EngineService` 启动补迁移；记录 `failed_step=migrations` |
| **崩溃窗口 C3**：项目已建、注册未生成 | 修复模式按 `(name, owner)` 复用项目（与 `PrepareLocalChain.py ensure-project` 同语义），不建第二个 |
| **崩溃窗口 C4**：注册已生成、路由未登记 | 修复模式重登记（UPSERT by `route_id`），并与注册声明的 id 逐字比对 |
| **崩溃窗口 C5**：floor 已建、记录未写 | 修复模式验收 empty-first 后**采纳**（adopt），不重写、不回滚（与 dev `_adopt_created_record` 同语义） |
| **崩溃窗口 C6**：换机/换目录后旧数据 | Owner binding 会以 `owner_directory_changed`/`owner_binding_denied` 拒绝（`owner_bootstrap.py:78-95`）。供给器**不得**"修复"此状态：换机＝重新授权，旧 binding 不迁移 |
| **重复安装（同版本、同目录）** | 有 binding → 修复/校验模式：只验 ACL、注册、路由、floor、记录，任何不一致即报错；**绝不**重新 `initialize`、绝不改 binding、绝不动 floor 的 `minimum_revision` |
| **重复安装（不同版本）** | 走升级路径（下一行） |
| **升级（注册变更）** | 固定顺序：写 `Registration.json.new` → 全量校验（`check_local_registration` 六项 + `RegisteredMediaRuntime` 构造）→ 原子替换注册 → 更新启动器 `--production-config-sha256` 钉定 → 重登记五条路由 → 写供给记录 `revision+1`。任何一步失败：**保留旧注册与旧钉定**（旧钉定仍可启动旧程序），不回滚路由（UPSERT 幂等） |
| **升级不得做的事** | 改 Owner binding、改 floor 的 `minimum_revision`、删历史供给记录、改已发布的 route id 语义（route id 是请求侧 `allowed_provider_routes` 的引用值） |
| **卸载（默认）** | 只删程序目录、启动器、快捷方式；保留数据目录（Owner/项目/作品/记录），写 `InstallationUninstall.json`（`uninstalled_at_us`、版本、保留的数据目录路径） |
| **卸载并删除数据** | 需二次确认（输入实例 id 前 8 位）；删除后不可恢复；不得删除其它实例目录 |
| **卸载后同目录重装** | 走升级/修复；Owner 仍有效；注册必须按新程序字节重新钉定，否则 503 `production_configuration_changed`（fail-closed，是设计而非缺陷） |

**"有 Owner 但无路由"为何仍可能出现一次**：升级时若"原子替换注册"成功而"重登记路由"失败，会出现新注册 + 旧路由的短暂态。此时 `installation_upgrade_required` 生效、启动门拒绝启动，`serve` 不会进入可用态；修复模式补登记即可。**不允许**把该态标成"完成"。

## 6 与现有 dev 宿主的关系

| 项 | 决定 |
| --- | --- |
| `serve-dev` / `worker-dev` | **保留**，明确为开发者路径，非产品路径；继续受 ADR0077 三重条件约束（frozen 拒绝在最先，`development_host.py:441-443,535-537`） |
| 与供给的关系 | dev 的"供给"仍是 `RunLocalChain.ps1`（ACL/项目/注册/路由/TTY 或 `--development-auto-owner-init`），**不采用**本卡的供给器；两条路径共享的只有"必须复算真实字节"这一条纪律 |
| 安装包内是否可达 | 不可达：①`Entry.py` 只调 `main()`，parser 无 `serve-dev`/`worker-dev`（`main.py:128-185`）→ argparse exit 2；②即使 dev 模块被 `Engine.spec:13` 的 hiddenimports 打进包，frozen 时在构造前即 503 `development_installation_unavailable`（`development_host.py:441-443,535-537`，顺序注释见 `:533`） |
| 安装包不得携带 | 任何 `--development-registration*`、`VIDEO_CREATOR_DEVELOPMENT_INSTALLATION`、dev 自动 Owner 初始化开关（ADR0079 §13.1 的 `--development-auto-owner-init`）。验证见 §8 V9 |
| 退役 | 本卡不退役任何 dev 路径。native 宿主可编译且真实安装记录/资格就位后，按 ADR0077 §8/ADR0079 §8 另行退役 |

## 7 安装包形态（R1 范围）

**R1 可交付（包内清单）**

1. 引擎 onedir：`VideoCreatorEngine.exe` + `_internal/`（含 `video_creator/**.py` 源 data、依赖、`Resources/`）。固定 commit 构建（`tools/build/BuildEngine.mjs`），构建收据随包。
2. 资源：`Resources/Media/**`（FFmpeg 11 件 + 许可）、字体、`Resources/Migrations/*.sql`、`Media/manifest.json`（逐件 SHA，`Entry.py:23-28` 每次 `serve` 自检）。
3. ASR 资源包（可选组件）：`AsrPackage/**`（当前 4,644 文件 / 989 MB）；缺省时注册 asr 四联为 `null`。
4. 静态工作台：`Workbench/**`（生产构建 dist）。
5. 启动器：`VideoCreatorLauncher.exe` —— loopback 静态服务 + `/api` 同源代理（token 只在代理侧）+ 授权会话 secret 注入（R1 用 URL fragment）+ 供给完成门 + `restart_required` 重启编排 + 卸载入口。
6. 注册与供给记录：`Registration.json`、`Routes/*.json`、`Control/InstallationProvisioning.json`（安装时生成，不预置）。

**明确不做，及替代与门槛**

| # | 不做 | R1 替代 | 门槛 / 原因（可核） |
| --- | --- | --- | --- |
| 1 | 签名安装器（Authenticode/MSI/MSIX + 系统卸载项） | 免安装目录 + 双击启动器 + 自解压引导 | 无代码签名证书与签名链 CI；`packaging/windows/` 为空目录。签名前不得宣称"正式安装包" |
| 2 | Tauri 桌面壳 / 原生安装记录 | 启动器 + 浏览器窗口 | `cli/native_startup.py:1` 自述 UNAPPLIED；held pipe/owner-protected build/资格无实现；Rust 工具链与三 OS ABI 未验 |
| 3 | 自动更新 | 手动覆盖安装（数据目录不变），按 §5.3 升级路径换注册与钉定 | 自动更新需签名 + 回滚通道 + 注册原子换 pin；未具备 |
| 4 | macOS/Linux 包 | Windows 优先 | 无对应构建机、资格与 FFmpeg 对应源/许可闭环（GPL 对应源未闭合前不可宣可分发） |
| 5 | Windows 服务 / 托盘常驻 | 前台运行，关闭即停 | 服务化需特权安装与生命周期重定义（ADR0005 语义不变），R1 不做 |
| 6 | **执行权威（installation authority）** | **另立 ADR0084《ProductTrustedStartupAuthority》**（§0.3-2），本卡不提供 | 冻结产物无 factory ⇒ `install_startup_services(None,…)→None`（`startup_services.py:61-62`）⇒ `engine._authorization_identity` 403（`engine.py:140-146`）。ADR0084 用**安装记录 + 实例 ACL/OS 所有者 + registration sha + 资源清单 sha** 在 trusted startup 构造权威，**不授予**任何 management 能力，且仍必须过 Owner binding 与 `assemble_owner_services` 现有门。门槛：实现 + 真实安装实例上完成一次成功制作并登记 `COMMANDS.md`；在此之前安装包只能浏览/建项目，且工作台必须显示具名阻断 |
| 7 | 打包内 dev 入口 | 无 | §6 |

对第 6 项的纪律：**不得**为"让安装包能出片"而放宽 `install_startup_services` 的类型门、不得伪造 `InstalledProductionEvidence`、不得在安装包里塞 dev 参数、不得把 `RouteDecision`/`route` 行当成执行能力。R1 的"可用"必须由真实证据决定，不由包形态决定。

## 8 验证清单（第三方可复跑；本卡全部 NOT_EXECUTED）

约定：`<Install>`＝安装根（含 `Registration.json`、`Package/`、`Routes/`、`Workbench/`）；`<Data>`＝实例数据目录；`<Port>`＝启动器分配的 loopback 端口；`<Engine>`＝`<Install>\VideoCreatorEngine.exe`；`<checkout>`＝构建该包时的仓库检出（V2/V7 需要）。V1-V5、V9、V10 只读；V6/V7 会在**一次性测试实例**上写一次真实 Owner binding（V8/V11 依赖它），不得在生产数据目录上跑。

| # | 目的 | 命令 | 期望输出 / 产物 |
| --- | --- | --- | --- |
| V1 | 供给记录自洽 | `pwsh -NoProfile -Command "$r=Get-Content '<Data>\Control\InstallationProvisioning.json' -Raw \| ConvertFrom-Json; $r.format; $r.complete; $r.instance_id; $r.project_id; $r.registration_sha256; ($r.items.id -join ',')"` | `installation-provisioning-v1`；`True`；`instance-<32hex>`；`project-<32hex>`；64 位小写 hex；items 覆盖 A1-A8+B1-B6 全部 id。落盘产物：`<Data>\Control\InstallationProvisioning.json` |
| V2 | 注册 ↔ 安装字节 ↔ 真实运行时（**核心**） | `python <checkout>\Codex\VideoCreatorImplementation\Integration\LocalInstallationRegistrationBuild\check_local_registration.py --repo <同一提交的 checkout> --out <Install> --runtime --instance-dir <Data> --output V2.json` | exit 0；`ok: true`；六项 `registration_schema`/`engine_source_sha256`/`local_material_resources`/`routes`/`bundled_tools_version`/`registered_media_runtime` 全真。产物：`V2.json` |
| V3 | 五条路由行存在且与注册一致 | `python -c "import sqlite3,json;c=sqlite3.connect(r'file:<Data>/Metadata.sqlite?mode=ro',uri=True);print(json.dumps([r[0] for r in c.execute('select id from routes order by id')]))"` | 恰好 5 条且逐字等于注册的五个 route id：`local.asr.faster-whisper-small-cpu-int8`、`local.edit.ffmpeg-v1`、`local.input-audio.ffmpeg-v1`、`local.input-visual.ffmpeg-v1`、`local.master-index.v1` |
| V4 | 空 floor | `Get-Content '<Data>\Control\ProductionAuthorizationControl.json' -Raw; (Get-FileHash '<Data>\Control\ProductionAuthorizationControl.json' -Algorithm SHA256).Hash` | `{"format":"production-authorization-control-v1","instance_id":"<instance>","minimum_revision":0,"pending_request_sha256":null}`；SHA 等于 V1 记录里该项的值 |
| V5 | ACL 收紧 | `(Get-Acl '<Data>').Access \| Select-Object IdentityReference,FileSystemRights,IsInherited` | 恰好 2 条：当前用户 SID 与 `NT AUTHORITY\SYSTEM`，均 `FullControl`、`IsInherited=False`；不含 `BUILTIN\Users`/`Everyone`/`Authenticated Users` |
| V6 | 授权前（负例，已实测的引擎侧行为） | `Invoke-WebRequest 'http://127.0.0.1:<Port>/api/v1/projects' -SkipHttpErrorCheck`；`Invoke-WebRequest 'http://127.0.0.1:<Port>/api/v1/health'` | 前者 403 `owner_authorization_required`；后者 200 且响应头 `X-VideoCreator-Authorization: pending` |
| V7 | 同意后（正例，已实测的引擎侧行为） | 同上，重启后再跑；另跑 `<checkout>\Codex\VideoCreatorImplementation\Integration\LocalInstallationRegistrationBuild\PrepareLocalChain.py --repo <checkout> owner-status --data-dir <Data> --project-id <project>` | `/health` 头 `none`；`/projects` 200；`owner-status` exit 0 且 `owner_initialized:true`、`project_in_binding:true`、`owner_subject:"local-user"`；`<Data>\Control\ProductAuthorization.json` 存在，`format=product-authorization-audit-v1`、`kind=owner_initialize`、`decision=approve`，且 `select value from metadata where key='product_authorization_audit'` 等于该文件 SHA |
| V8 | **无管理凭据**（诚实性负例） | ①从 V3 的连接读 binding 的 `authentication_binding_id`；②`python -c "import keyring;print(keyring.get_password('VideoCreatorOwnerManagement','owner-<instance_id>-<binding_id>'))"`；③同一实例用管理端点带安装 token | ②输出 `None`（Windows 走 keyring）；③403 `production_management_denied`。二者同时成立才证明"有 Owner 但无管理能力" |
| V9 | 无 dev 痕迹 | `Select-String -Path '<Install>\*.json','<Install>\*.cmd' -Pattern 'VIDEO_CREATOR_DEVELOPMENT_INSTALLATION\|--development-registration'`；`& '<Engine>' serve-dev --data-dir <Data>` | 前者无匹配；后者 argparse exit 2（`Entry.py` 只暴露 `main()` 的命令域），且包内 dev 模块即使存在也在 frozen 前拒（`development_installation_unavailable` 503） |
| V10 | 工作台可达且不泄 token | `Invoke-WebRequest 'http://127.0.0.1:<Port>/' -SkipHttpErrorCheck`；`Invoke-WebRequest 'http://127.0.0.1:<Port>/api/v1/health'`；`Select-String -Path <页面源码> -Pattern '<token 前 8 位>'` | 前者 200 且含 `<div id="root">`；`/api/v1/health` 经同源代理 200；页面源码与静态资源**无** token/secret 任何片段 |
| V11 | 执行权威现状（必须显式记录） | `Invoke-WebRequest -Method POST 'http://127.0.0.1:<Port>/api/v1/productions' -SkipHttpErrorCheck -Body <最小请求> -ContentType 'application/json'` | R1 当前预期：403 `production_authorization_unconfigured`；工作台必须显示具名阻断卡而不是"可用"。该负例必须在**真实安装实例**上跑并登记 `COMMANDS.md` 后，§7-6 才可判为"已解决" |

纪律：V1-V11 的**真实执行**必须由测试开发在安装实例上跑完后登记 `docs/acceptance/criteria/COMMANDS.md`（含 exit、逐字输出、产物路径与 SHA）；本卡不预填任何通过结论。**执行顺序是硬的**：V1/V3/V4 直接依赖 `installer-admin provision` 写出的供给记录、路由行与空 floor，故必须先有该实现（后端）再执行验证；在实现落地前 V1-V11 一律记 `NOT_EXECUTED`，不得以"脚本可跑"代替"实际跑过"。V2 必须与"构建该包的同一 commit"配对，否则 `engine_source_sha256` 必然不等——这是预期失败，不是缺陷。

## 9 不做与后继

- 不做：改任何生产校验（`install_startup_services`、`assemble_owner_services`、`ProductionAdmissions`、`assemble` 的类型门、`management_access`）；新增数据库表/迁移；让供给写 Owner binding/secret/policy/admission；让供给或产品通道签发 execution registration、qualification、evidence policy；远程访问；静默/无人值守安装；自动更新；三 OS 打包。
- 后继（按顺序）：
  1. **ADR0084《ProductTrustedStartupAuthority》**（独立卡，本卡只登记）：解决 §7-6。以**安装记录 + 实例 ACL/OS 所有者 + registration sha + 资源清单 sha** 构造产品形态受信启动权威；架构先出窄设计（谁验、验哪些字节、失败如何具名、与 ADR0081 §2 重启语义如何配合），后端再实现。三条禁止：不得复用 dev 三重条件、不得让环境变量/配置文件直接构成 authority、不得伪造对象。
  2. 本卡实现：`installer-admin provision` 子命令域（含空 floor）+ `InstallationProvisioning.json` + 启动器供给门 + 修复/升级/卸载（后端 + 集成）。
  3. 工作台受信 bootstrap 的产品侧等价物（前端 + 集成）：现字面量只在 vite dev 模式定义（`vite.config.ts:55`），静态构建下为 `undefined`，`engine.ts:20-21` 明确"缺 bootstrap 即不可用"。
  4. 真实安装实例的 V1-V11 执行与 `COMMANDS.md` 登记（测试开发；必须在第 2 项之后）。
  5. 独立评审 + 验收（评审/验收角色）。

## 10 交接

- **后端**：`installer-admin provision`（一次性、无监听、不装配 OwnerServices；复用 `_package_sources`/`_hash`；写 B1-B6）；`InstallationProvisioning.json` 的 canonical/原子读写；错误码 §5.2；**不动**任何既有启动分支与校验。
- **集成**：安装器/自解压引导、启动器（静态 + 代理 + token/secret 注入 + 供给门 + 重启编排 + 卸载）、`Engine.spec`/`BuildEngine.mjs` 产出物与收据、包内不得含 dev 参数。
- **前端**：产品侧受信 bootstrap 等价物（§9-3）；授权页在"供给未完成"时**不可达**（由启动器保证，前端只需不缓存 secret）。
- **测试**：V1-V11 的真实执行与登记；负例必须覆盖 C1-C6 六个崩溃窗口、重复安装、升级失败保留旧钉定、换机拒绝；不得用 Mock 代替真实 `RegisteredMediaRuntime`。
- **评审**：核对 §0 证据行号、§2 四组不重叠、§3.2 的"无 capability"论证、§5.1 两条不变量的三道防线、§7-6 的门槛，以及"未改任何生产校验"的 `git diff`。

## 11 复核清单

1. `git diff` 只含 `docs/decisions/0083-installer-provisioning-and-first-run.md` 与 `docs/architecture.md`；源码/测试/契约零改动。
2. 逐条核对 §0 的全部证据行与 HEAD `3f039df` 一致。
3. 核对 §2.1/2.2 每一项都填了"写入方/时机/是否需要管理能力/审计"四列，且 C 组与 A/B 组无交集。
4. 核对 §3.2 的表格每一行都能在源码找到对应行号；核对"供给不持有 capability"的三条依据（`register_route`、`create_project`、`initialize_new`）。
5. 核对 §5.1 INV-1 的三道防线与 §5.3 六个崩溃窗口一一对应。
6. 核对 §8 每条命令都可直接复制执行，且期望输出是**可判定的**（不是"应该正常"）。
7. 核对 §7-6 没有被任何措辞软化：R1 包在无执行权威时不得宣称"可用"。
8. 核对 §0.3 的两条裁定已逐条落到 §2.2 B4、§2.4、§3.3、§5.1 INV-3、§7-6、§8 纪律、§9 后继 1，且没有留下"待决"措辞。
