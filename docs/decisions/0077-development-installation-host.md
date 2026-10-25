# ADR0077：开发安装资格宿主（Development Installation Host）

状态：ARCHITECTURE_APPROVED_CONTRACT_ONLY，2026-10-25。冻结边界、启用条件、对象协议、装配顺序、健康可见性与失败语义；没有实现、没有运行、没有独立验证。不新增数据库表或迁移，不改迁移，不改生产校验，不支持 v2/v3，不做 unattended。实现/集成/测试/评审按原角色白名单另立任务。

## 0 实读证据（本 ADR 据此冻结，非文档推断）

行号取自 2026-10-25 实际源码。`services/engine/src/video_creator` 简称 `vc/`。

| 事实 | 位置 |
| --- | --- |
| 证据协议与两个 guard Protocol（`observe`/`assert_current`/`assert_local_current`） | `vc/application/production_admissions.py:34-65` |
| 执行身份登记的前置与写入 | `vc/application/production_admissions.py:111-142` |
| `_identity` / `_installation` / `_issued_guard` / `_guard` | `vc/application/production_admissions.py:176-203,240-265,267-287` |
| `current_guard` 的 guard 生命周期与 writer 外观察 | `vc/application/production_admissions.py:205-237` |
| `assemble_owner_services` 装配、8 字段白名单与 Owner 校验 | `vc/application/owner_services.py:101-175` |
| `install_startup_services` 对返回对象的硬校验 | `vc/cli/startup_services.py:56-91` |
| `installed_principal_id` ready 条件 | `vc/cli/startup_services.py:106-129` |
| factory 允许的命令域与 `serve` 分支装配顺序 | `vc/cli/main.py:164-176,307-358` |
| `RegisteredMediaRuntime` 的配置/引擎/资源校验 | `vc/application/media_registration.py:126-146,200-255` |
| `_package_sources` / `_local_file` / `_hash` 实际判定 | `vc/application/media_registration.py:86-123` |
| `installation_resource_identity` 三 SHA 元组 | `vc/application/media_registration.py:315-320` |
| worker 侧三 SHA 相等断言 | `vc/application/media_registration.py:394-423` |
| `RegistrationConfigLocalV1` / `LocalRegistrationV1` 字段 | `vc/domain/local_material_production.py:50-89` |
| `parse_local_registration_config` 严格解析 | `vc/domain/local_material_production.py:209-239` |
| `OwnerBootstrapStore.current()` 的返回条件 | `vc/application/owner_bootstrap.py:124-134` |
| `owner-init` 的真实 TTY 确认 | `vc/cli/owner.py:116-117` + `vc/application/owner_bootstrap.py:151-185,340-350` |
| `NativeLaunchContext` 强校验 | `vc/infrastructure/held_authority.py:92-125` |
| `NativeOwnerServices` 字段与 close 顺序 | `vc/application/native_installation.py:121-141` |
| native 启动 factory 模板（dev 入口仿此，不改它） | `vc/cli/native_startup.py:19-75` |
| 现有 authority 只能由受保护对象构造 | `vc/application/local_installation_authority.py:108-125`、`vc/application/native_installation.py:46-118` |
| `InstanceHealth.mode` 固定 `Literal["local"]` | `vc/domain/contracts.py:234-239` |
| 传输声明从 OpenAPI 派生 response_headers | `vc/api/transport_contract.py:269-275` |
| 默认 Bundle principal `local-user` | `vc/application/bundles.py:235-244,276-287` |
| 本地-v1 资源/工具哈希校验 | `vc/application/media_registration.py:206-227` |

### 0.1 必须在写代码前验证的四项（已验，结论如下）

1. **`install_startup_services` 对 factory 返回对象的硬校验（`vc/cli/startup_services.py`）**：①`type(native) is not NativeOwnerServices` → `installed_services_binding_invalid` 503（74-76）；②`native._closed` 为假（80）；③`native.connection.context.instance_id == engine.instance_id`（80）；④`native.connection.context.role == role`（80）；⑤`native.authority.connection is native.connection`（81）；⑥`services.bootstrap.engine`/`services.authorization.engine`/`services.admissions.engine` 都是同一个 engine（82-84）；⑦`services.admissions.installation_authority is native.authority` **且** `installation_session_guard is native.authority`（85-86）；⑧`services.copy_inputs.engine/bundle` 相符（87）；⑨`services.registry is None` 且 `services.authorization.management is None`（88）。另有角色域校验：role ∈ {api,mcp,worker}、`bundle.engine is engine`、worker 必须有同一 engine/bundle 的 `registered_runtime`、非 worker 必须没有（65-71）。
   **结论：dev 必须复用 `NativeOwnerServices`**（放宽 74-76 属修改生产校验，需统筹决定）。构造它的最小字段见 3.2。
2. **`register_execution_identity` 的全部前置条件**：`project_ids` 非空且唯一、`allowed_source_namespaces` 对不重复、`type(expires_at_us) is int` 且 `> engine.clock()`，否则 `production_execution_registration_invalid` 503（121-125）；`c.SourceBinding(system=owner_subject, namespace=executing_principal_id)` 必须合法（126）；每个 project 要过 `c.SourceBinding(system=project_id, namespace='production-project')`（127-128）；每个 source 对要过 `c.SourceBinding(system, namespace)`（129-130）；`registration_sha256` 要过 `c.BundleRef`，两个 manifest sha 要过 `c.AssetCandidate`（131-135）；**在 writer 内**对每个 project 调 `management_service._project_scope`，即该 project 必须真实存在于 `projects` 表且 `owner==owner_subject`（136-137 → `vc/application/production_authorization.py:92-95`，否则 `production_management_project_denied` 403）。
3. **`OwnerBootstrapStore.current()` 返回 binding 的条件**：`assert_current_directory()` 通过（安装目录 OS 主体/设备/inode 与记录一致，`owner_bootstrap.py:67-76`）；Owner 控制文件存在且 `assert_revision(record.generation)` 通过（124-130，pending 或 DB 落后 → `production_restore_refresh_required` 503）；`metadata['owner_management_binding']` 存在并可规范解码（`owner_not_initialized` 503 / `owner_binding_invalid` 422 / `owner_binding_denied` 403）。`allow_inactive=False` 时还要求未撤销且未过期（131-132）。
   **`owner-init initialize` 确实需要 TTY**：`cli/owner.py:116-117` 不传 `confirmation_source`，`change()` 因此在 `owner_bootstrap.py:168-170` 调 `confirm_local_action`，后者要求 `sys.stdin.isatty()` 与 `sys.stdout.isatty()` 都为真并按字输入 `AUTHORIZE <instance_id> initialize`（340-350）。所以 dev 首次初始化必须有真实交互终端，不能 headless、不能 `--yes`、不能由 dev host 代办。
4. **`_package_sources(PACKAGE_ROOT)` 的实际判定**（`media_registration.py:110-123`，`PACKAGE_ROOT = Path(media_registration.py).resolve().parents[1]` = `services/engine/src/video_creator`，行 42）：从包根递归遍历；目录名为 `__pycache__` 的整枝跳过；遇到 symlink/junction 直接 `production_resource_denied` 403；**只有后缀为 `.py` 的普通文件算 package source**，键为相对包根的 POSIX 路径。当前 checkout 实测 **183 个 `.py`**（含各级 `__init__.py`，不含 `__pycache__`）。`engine_source_sha256` 的键集合必须与该集合完全相等，否则 `production_engine_incomplete` 503；任一文件哈希不符 `production_code_changed` 503（142-146）。任何 engine 源码编辑都会让已生成的注册文件失效。

## 1 边界：dev 资格与生产资格的差别

生产资格只有两条现成来源，都必须由受保护对象构造：`NativeInstallationAuthority`（held pipe facts + 已准入 qualification，`native_installation.py:46-118`）与 `LocalInstallationAuthority`（只能经 `local_authority_from_connection`/`local_authority_from_observer` 构造，`local_installation_authority.py:108-125`）。二者都要求真实 `OwnedAuthorityConnection`/`OwnerProtectedNativeBuild`/保留 observer，且 `observe()` 的 `observed_at_us` 必须等于受保护端给的 `facts.observed_at_us`（`native_installation.py:71`）。

**dev 资格不是第三种生产来源**。它是"开发检出在自己身上充当安装实例"的显式、非生产事实源：证据同样由真实磁盘字节哈希得出，但来源是 checkout 与本地资源文件，不含 held pipe、Owner-protected build、qualification、独立安装记录（ADR0036）或 OS 级完整图核对。因此它证明的是"这些字节在该 checkout 上一致"，**不证明**"这些字节来自受保护安装"，不得作为 Gate0/R1 完成、发布或安装验收证据。

以下校验**保持原样、一行不改**，dev 只能满足它们，不能放宽：

- `ProductionAdmissions._identity`（176-180）、`_installation`（182-203）、`_issued_guard`（240-265）、`_guard`（267-287）、`current_guard`（205-237）；
- `register_execution_identity` 全部前置（121-142）与 `engine.configure_production_authorization`（`vc/application/engine.py:94-118`）；
- `install_startup_services` 与 `installed_principal_id`（`cli/startup_services.py` 全文）；
- `RegisteredMediaRuntime` 的 `engine_source_sha256` 覆盖/哈希、local-v1 资源与工具校验（`media_registration.py:126-255`）；
- native 路径全部文件：`application/native_installation.py`、`application/local_installation_authority.py`、`application/native_qualified_*`、`infrastructure/held_authority.py`、`infrastructure/windows_authority_pipe.py`、`cli/native_startup*.py`、`cli/native_owner_*.py`；
- 生产入口 `serve`/`worker`/`mcp-stdio` 三个分支与 `main()` 的 factory 命令域守卫（`cli/main.py:164-176,203-221,293-358`）。

**dev 只能由哪个入口、在什么条件下构造**：

- 唯一入口是新增的开发专用模块 `cli/development_host.py`，形态照抄 `cli/native_startup.py:63-75`：私有 wrapper → 构造 factory → 调 `cli.main.main(installed_service_factory=factory)`。公开命令字为 `serve-dev` 与 `worker-dev`，由**该模块自己的 parser**给出，再改写成 `serve` / `worker --workflow registered-media-bundle-v1` 后转发。
- factory 只在进程内以闭包绑定一次；不存在环境变量/argv/HTTP 型 factory 注册（`startup_services.py:19-28` 明确禁止）。生产模块不得 import `video_creator.application.development_installation`；只有 `cli/development_host.py` 可 import，且必须能用一个 grep 证明。
- 条件（三重同时成立）：见第 2 节。任一不成立即拒绝，且拒绝发生在监听端口之前。

`cli/main.py` 的行为不需要改变（`main()` 已接受外部 factory，且 factory 命令域已允许 `serve` 与 registered worker）。若后端为可发现性把 `serve-dev`/`worker-dev` 加进 `cli/main.py` 的 parser，只能新增分支，不得改动既有三个分支、既有 flag 默认值或 `main():164-176` 的守卫语义。

## 2 启用条件与拒绝语义

三重条件缺一即拒绝：

- (a) **CLI 显式参数**：`--development-registration <绝对路径>`、`--development-registration-sha256 <64hex>`、`--development-expires-at <带时区 ISO8601>` 三者皆必填。缺任一参数时 argparse 直接 usage 退出（exit 2），不进入任何组装，不创建 Engine、不碰 DB。
- (b) **环境变量**：`VIDEO_CREATOR_DEVELOPMENT_INSTALLATION` 必须存在且与该进程的 `engine.instance_id` 逐字相等。instance_id 来自 data-dir 的 SQLite（`engine.py:59-61`），因此该项在 factory 第一行检查——早于任何 `assemble_owner_services`、早于 `install_startup_services`、早于 listener。
- (c) **非 frozen 产物**：`getattr(sys, 'frozen', False)` 必须为假，检查置于 wrapper 最前，早于 Engine 构造。冻结产物一律拒绝，即使 (a)(b) 齐全。

顺序固定为：frozen → dev argv → `EngineService` → 环境变量 → 注册文件 → 证据 → 组装。不允许"先起服务再补校验"。

| 拒绝条件 | code | status_code | 能否继续 |
| --- | --- | --- | --- |
| frozen 产物 | `development_installation_unavailable` | 503 | 否 |
| 环境变量缺失或不等于 instance_id | `development_installation_denied` | 403 | 否 |
| role 不是 `api`/`worker`（含 `mcp`） | `development_role_denied` | 403 | 否 |
| 域 Owner 不等于 `bundle.principals.owner_subject` | `development_installation_denied` | 403 | 否 |
| 注册文件缺失/非普通文件/symlink/junction/>1 MiB | `development_registration_missing` | 503 | 否 |
| 注册文件 SHA256 与入参不符 | `development_registration_changed` | 503 | 否 |
| 非 UTF-8/重复键/非有限数/schema 不符 | `development_registration_invalid` | 422 | 否 |
| format 不是 `registered-media-config-local-v1` | `development_registration_profile_unsupported` | 400 | 否 |
| engine 覆盖集不等于 `_package_sources` | `development_engine_incomplete` | 503 | 否 |
| engine 文件哈希不符 | `development_code_changed` | 503 | 否 |
| 资源文件缺失 | `development_resource_missing` | 503 | 否 |
| 资源文件哈希不符 | `development_resource_changed` | 503 | 否 |
| evidence 不是本 authority 当前原对象 | `development_evidence_foreign` | 409 | 否 |
| authority 已 close | `development_installation_retired` | 503 | 否 |
| `--development-expires-at` 越窗 | `development_expiry_invalid` | 422 | 否 |
| engine/资源相对名冲突 | `development_identity_collision` | 422 | 否 |

**HTTP 语义**：以上全部发生在 `listener.bind` 之前（`cli/main.py:319-321` 先 `install_startup_services` 再 bind），因此**不存在 HTTP 响应**。CLI 按 `main():360-364` 只向 stderr 打印 `{"code","message"}` 并 exit 1。上表 `status_code` 只为统一 `ErrorEnvelope` 词表与既有 403/422/503 分级保留，不得据此在别处改 HTTP 状态，也不得让 `/health` 报告"dev 已被拒绝"。

新增错误码一律**不得**加入 `RESOURCE_WAIT_CODES`（`media_registration.py:43-53`），否则 dev 漂移会被 worker 当成 `resource_not_ready` park 而不是失败。

## 3 对象协议

### 3.1 精确签名（协议文本，不是实现）

```text
application/development_installation.py

class DevelopmentLaunchConnection:
    context: NativeLaunchContext        # 真实构造，见 3.3；不是 duck type
    def close(self) -> None             # 幂等

class DevelopmentLaunchBuild:
    def close(self) -> None             # 幂等；不触达文件

class DevelopmentInstallationAuthority:
    connection: DevelopmentLaunchConnection    # 每次属性访问返回同一对象
    def observe(self) -> InstalledProductionEvidence
    def assert_current(self, observation: InstalledProductionEvidence) -> None
    def assert_local_current(self, observation: InstalledProductionEvidence) -> None
    def close(self) -> None
```

对照实际调用点，dev 必须实现的只有这些，且不得多出可选关闭：

- `ProductionAdmissions.__init__` 只保存 `installation_authority` 与 `installation_session_guard`（100-109）；
- `_installation` 调 `authority.observe()`（185），核 `isinstance(observation, InstalledProductionEvidence)`、六字段精确相等、`type(observed_at_us) is int` 且 `0 < observed_at_us <= engine.clock()`、两个 tuple 非空（188-193），再核名字规范与不重名（194-199）、每个 sha 过 `c.AssetCandidate`（200-201），最后调 `authority.assert_current(observation)`（202）；
- `_guard` 在每个 writer 里调 `installation_session_guard.assert_local_current(guard.installation)`（280-281）；
- `_issued_guard` 只有在 `type(authority) is NativeInstallationAuthority` 时才取 `qualification_issuer`（245-246），因此 dev authority 必须是**别的类型**且不实现 qualification；
- `install_startup_services` 要求 `admissions.installation_authority is native.authority`、`installation_session_guard is native.authority`、`native.authority.connection is native.connection`（81,85-86）。

### 3.2 dev 必须复用 `NativeOwnerServices`（构造所需最小字段）

`startup_services.py:74-76` 的 `type(native) is not NativeOwnerServices` 是硬门。字段（`native_installation.py:121-127`）：

| 字段 | dev 取值 |
| --- | --- |
| `services` | `assemble_owner_services(...)` 的返回值（见 4.3） |
| `connection` | `DevelopmentLaunchConnection`，与 `authority.connection` **同一对象**；`startup_services` 只从中读 `.context.instance_id`/`.context.role`（79-80,115-116） |
| `authority` | `DevelopmentInstallationAuthority`，同时充当 `installation_session_guard`（同一对象，满足 85-86） |
| `build` | `DevelopmentLaunchBuild`；`NativeOwnerServices.close()` 会调 `authority.close()` 与 `build.close()`（130-135） |

不得用 `LocalInstallationAuthority` 冒充：它没有公开 `connection` 属性（`local_installation_authority.py:14-21`），构造它又必须持有真实 `OwnedAuthorityConnection`/`OwnerProtectedNativeBuild`（108-125）。也不得放宽 74-76——那属于修改生产校验，需统筹决定。

### 3.3 `NativeLaunchContext` 必须真实构造

`held_authority.py:92-125` 的 `__post_init__` 强校验：instance_id 文本合法；role ∈ {api,worker,mcp}；三个 SHA 必须 64 hex；`expected_files` 非空、每项是 `HeldFileFact`、不重名；`engine_file_names` 非空、不重名且是 names 的**真子集**；序列化体积 < 32 MiB−16 KiB。dev 取值：role=启动角色；三 SHA 同 3.4；`expected_files`=engine 文件 ∪ 资源文件；`engine_file_names`=engine 文件名集合。它给 `install_startup_services` 提供的只有 instance_id 与 role，不提供任何资格。不得为省事传一个只有两个属性的对象：那会让"完整文件图/分区"这条既有不变量在 dev 侧悄悄消失。

### 3.4 `InstalledProductionEvidence` 字段来源（逐字段）

| 字段 | dev 精确来源/取值 |
| --- | --- |
| `instance_id` | `engine.instance_id`（`engine.py:59-61`） |
| `registration_sha256` | dev 注册文件的**实际全文件 SHA256**；必须同时等于 `--development-registration-sha256`，并在 worker 侧等于 `RegisteredMediaRuntime.sha256`（`media_registration.py:140`） |
| `resource_manifest_sha256` | `config.production_resource_manifest_sha256`（`local_material_production.py:72`） |
| `runtime_manifest_sha256` | `config.production_runtime_manifest_sha256`（`:73`） |
| `workflow_version` | 常量 `'registered-media-bundle-v1'`（`media_registration.py:41` 的 `PROFILE`；`_installation:191` 精确比较） |
| `driver_profile` | 常量 `'registered-production-drivers-v1'`（`production_admissions.py:47`；`_installation:191`） |
| `observed_at_us` | 每次 `observe()` 现取 `engine.clock()`（`engine.py:58`，即 `time.time_ns() // 1000`）；禁止常量、配置值、未来值或"稍后修正" |
| `engine_source_sha256` | 对 `_package_sources(PACKAGE_ROOT)` **完整集合**逐文件 `sha256`，`((相对路径, hex), ...)` 按相对路径排序；不得只覆盖部分模块 |
| `indexed_resource_sha256` | 对配置点名的非 engine 文件逐文件 `sha256`，按相对路径排序，且**非空**：`production_resource_manifest`、其索引的 `runtime_manifest`、`ffmpeg`、`ffprobe`，以及 ASR 四联非空时的 `asr_resource_manifest` |

哈希算法固定为 `hashlib.sha256` 分块读全文件 + `hexdigest()` 小写 64 hex（与 `media_registration.py:86-91` 的 `_hash` 同一语义）；`_installation:200-201` 会再逐个过 `c.AssetCandidate(sha256=…)`，非小写 64 hex 直接 503。

名字约束：`_installation:198` 要求每个名字是固定相对文件（无前导 `/`、无反斜杠、无 `:`、无空段/`.`/`..`），分区内不重名（194-196）。engine 名是包内相对路径，资源名是配置父目录的相对路径；合并进 `NativeLaunchContext.expected_files` 时必须全局唯一，冲突即 `development_identity_collision` 422，不允许改名掩盖。

**哈希来源的硬要求**：`engine_source_sha256` 必须调用既有的 `media_registration._package_sources` 与 `_local_file`（或逐字节同义实现），不得另写一套遍历，否则 dev 与安装器会漂移。API 角色不构造 `RegisteredMediaRuntime`（理由见 8.5），因此 local-v1 的 manifest/runtime/tools 校验由 dev 复刻 `media_registration.py:206-216` 的语义，错误情况映射到第 2 节 dev 码表。

### 3.5 生命周期与身份绑定

- `observe()` 每次新建 evidence，并登记 `id(evidence) → (evidence, epoch, thread_id)`；`assert_current` / `assert_local_current` 只接受该表内同一对象、同一 epoch、同一线程（与 `LocalInstallationAuthority:70-93` 同构）。不序列化、不跨进程、不缓存、不复活。
- `assert_current` 是**writer 外重核**：重新哈希 engine 全集与资源全集，逐项等于 observation 的两个 tuple；不等即 `development_code_changed` / `development_resource_changed` 503。不得返回 bool，不得只信配置里的哈希。
- `assert_local_current` 是**短 writer 钩子**：只做对象/epoch/thread/closed 判定与一次非阻塞锁获取（忙即 `installation_session_busy`，同 `local_installation_authority.py:86-93`）；禁止文件 I/O、哈希、DB 读、阻塞锁。
- `close()` 幂等；retire 后四个方法一律 `development_installation_retired` 503，并从保留表移除。

## 4 装配顺序

### 4.1 serve-dev（API 角色）

1. wrapper 检查 frozen，解析 dev 参数。
2. 把 argv 改写为 `['video-creator-engine', 'serve', …]`，只允许转发白名单 flag：`--data-dir`、`--host`、`--port`、`--allowed-origin`、`--allowed-host`、`--native-origin`、`--ffmpeg`、`--ffprobe`、`--control-stdin`；出现未知 flag 即 usage 退出 2（不做透传）。
3. 调 `cli.main.main(installed_service_factory=dev_factory)`；`main()` 既有守卫（164-176）允许 `serve` + factory。
4. 走既有 `serve` 分支（307-320）：origins → `VIDEO_CREATOR_API_TOKEN` → `EngineService(data_dir)` → `configured_media_validator(engine, ffmpeg, ffprobe)` → `BundleService(engine, TrustedBundleValidators(media_validator))` → `install_startup_services(factory, engine, bundle, role='api')`。
5. factory 内部顺序：frozen → 环境变量 → `role == 'api'` → `for_management is False` → `registered_runtime is None` → `bundle.engine is engine` → 读 active Owner binding → `owner == bundle.principals.owner_subject` → 注册文件（绝对路径/普通文件/非链接/≤1 MiB/SHA256） → `parse_local_registration_config` → format 必须 local-v1 → engine 覆盖集与逐文件哈希 → 资源解析与哈希 → `NativeLaunchContext` → 8 字段 dict → `DevelopmentInstallationAuthority` → `assemble_owner_services(engine, owner, bundle=bundle, for_management=False, installation_authority=authority, installation_session_guard=authority, execution_registration=…, owner_setup_bootstrap=None)` → `NativeOwnerServices(services, authority.connection, authority, build)`。任一步失败必须先 `authority.close()`（再 `build.close()`）再抛原始错误。
6. `install_startup_services` 复核（74-91）并返回 `StartupInstallation`。
7. `create_app(..., bundle_service=bundle, copy_input_service=installed.native.services.copy_inputs)`（`cli/main.py:339-345`）。
8. `ready()` → `installed_principal_id(held, engine=engine, bundle=bundle, role='api')`：要求 `services.execution_identity` 非空、`engine.production_admissions is services.admissions`、`engine.daily_projects is services.daily_projects`、`engine._authorization_identity(actor) is registered`、`registered.owner_subject == registered.executing_principal_id == actor.subject_id`、`actor.owned_projects`（106-129）。这些由 `assemble_owner_services:147-173` 与 `InstancePrincipalRegistry.owner()` 的 `owned_projects=True` 满足。
9. 关闭：`confirm_api_cleanup`（94-103）→ `installed.finish_shutdown(original_threads)`（43-53）→ `NativeOwnerServices.close()`。

serve-dev 的 `--ffmpeg`/`--ffprobe` 必须解析到 dev 注册配置点名的同两个文件（`config.ffmpeg`/`config.ffprobe` 相对配置目录）；不等即 `development_installation_denied` 403，防止用系统 ffmpeg 冒充同一注册。

### 4.2 worker-dev

wrapper 改写成 `worker --workflow registered-media-bundle-v1 --data-dir … --production-config … --production-config-sha256 … --max-seconds … [--once] [--control-stdin]`；`cli/main.py:203-221` 既有分支构造 `RegisteredMediaRuntime` 后调 `install_startup_services(..., role='worker', registered_runtime=runtime)`。dev factory 额外核：

- `type(runtime.config) is RegistrationConfigLocalV1`；
- `runtime.sha256 == --development-registration-sha256` 且 `runtime.path.resolve() == Path(--development-registration).resolve()`；
- `runtime.installation_resource_identity == (sha, config.production_resource_manifest_sha256, config.production_runtime_manifest_sha256)`（`media_registration.py:315-320`）——这正是 dev evidence 的三个 SHA，故 worker 侧 `_current_services:405-407` 的相等断言自然成立；
- `runtime.bundle.principals.owner_subject == owner`。

dev authority 必须直接消费 runtime 已解析的 `config`/`path`/`sha256`/`engine`，不二次解析同一文件（避免两套对象给出不同哈希）。

### 4.3 `execution_registration` 8 字段由谁给出

| 字段 | 给出者 | dev 约束 |
| --- | --- | --- |
| `owner_subject` | `OwnerBootstrapStore(engine).current()` 的 `binding.principal.owner_subject` | 必须 active 且未过期；必须等于 `bundle.principals.owner_subject` |
| `executing_principal_id` | 同上 | 第一版必须等于 `owner_subject`（`owner_services.py:143`，否则 `owner_execution_registration_denied` 403） |
| `project_ids` | `binding.principal.project_ids`（`owner-init --project-id` 显式给出） | 非空且唯一；每个 project 必须在 DB 中由该 Owner 拥有，否则 `production_management_project_denied` 403 |
| `registration_sha256` | dev 注册文件实际 SHA256 | 见 3.4 |
| `resource_manifest_sha256` | `config.production_resource_manifest_sha256` | 见 3.4 |
| `runtime_manifest_sha256` | `config.production_runtime_manifest_sha256` | 见 3.4 |
| `allowed_source_namespaces` | 固定 `()` | local-v1 human 链不带 source binding；`_record:388-396` 会拒绝任何未列入的 binding，因此本轮不给"方便"的宽集 |
| `expires_at_us` | `--development-expires-at`（带时区 ISO8601 → 整数微秒） | `type is int` 且 `engine.clock() < t <= min(binding.principal.expires_at_us, engine.clock() + 7*86400_000_000)`，越界 `development_expiry_invalid` 422 |

`expires_at_us` 的有限性理由：dev 身份没有 native 安装记录这一持久锚，只能以"本次 Owner binding 有效期 + 7 天上限"自我终止；`_identity:178` 与 `_persist:471` 会用 `min(policy.expires_at_us, registered.expires_at_us)` 自然失效。禁止用环境变量、配置默认值或"无穷大"延长它；环境变量只授权启用，不携带范围。长度上限是架构冻结常量，改动需要修订本 ADR。

### 4.4 dev factory 不做的事

- 不构造 `native_registration_store`/`native_current_registration`（`assemble_owner_services:131-136,148-153` 的绑定分支不进入）；
- 不传 `owner_setup_bootstrap`，因此 `assemble_owner_services:113-115` 的 setup 校验分支不进入；
- `for_management` 必须为 `False`，因此 `services.registry is None`、`authorization.management is None`（`startup_services:88`）；
- 不调 `engine.configure_production_authorization` 之外的注册副作用；该调用由 `assemble_owner_services:154` 完成，dev 不重复。

## 5 健康可见性

- `InstanceHealth.mode` 是固定 `Literal["local"]`（`contracts.py:234-239`），**不复用、不拓宽**，也不新增 JSON 字段。拓宽 `mode` 或加字段都会改动 OpenAPI、`schemas.json` 与由 OpenAPI 派生的传输声明（`api/transport_contract.py:269-275`），需要集成重新生成 `packages/contracts`/`api-client`，并对严格客户端构成破坏性变更——那属于另一张卡，需统筹决定。
- dev 用**响应头扩展**标出：dev 进程的 `GET /api/v1/health` 返回 `X-VideoCreator-Installation: local-development`；生产进程不返回该头；值只来自进程内 dev 绑定，绝不来自请求头、query、cookie 或模型输出。
- 该头**不写进 OpenAPI 的 responses 声明**，只在运行时 `Response` 上设置；health 增加一个 `response: Response` 形参不会被生成成参数（FastAPI 跳过 Response 类型），因此 `export-contracts` 输出保持逐字节不变。
- `/health` 其余四字段、`VIDEO_CREATOR_API_TOKEN` ≥32 的要求与鉴权（`api/app.py:73-83,115-122,163-166`）不变；不得存在"dev 是否已启用"的探测型响应。
- ADR0005 冻结的 ready stdout 三字段（+已安装时的 `principal_id`）不改：dev 不新增 ready 字段，`instance_id` 足以对账。
- 该头只说明"这是开发宿主"，不是资格、不是可发布、不是 Worker 存活证明（后者仍是 `worker_connected`）。

## 6 失败语义

| 情形 | 返回 | 能否继续 |
| --- | --- | --- |
| engine 任一 `.py` 哈希不符 | `development_code_changed` 503 | 不能；该 code 不在 `RESOURCE_WAIT_CODES`，worker attempt 直接失败而非 park。编辑源码即等于该注册失效，必须重生成注册文件 |
| 资源配置哈希不符 | `development_resource_changed` 503 | 不能，同上 |
| 配置不是 local-v1（v2/v3/未知 format） | `development_registration_profile_unsupported` 400 | 不能；dev 不尝试 v2/v3 分支、不降级到 v1 猜测 |
| 缺少 Owner binding | `owner_not_initialized` 503（`owner_bootstrap.py:128-129`） | 不能；先做真实 TTY 的 `owner-init initialize` |
| Owner binding 已撤销/已过期 | `production_management_denied` 403（`owner_bootstrap.py:131-132`） | 不能。dev 用 `allow_inactive=False`，比执行角色更严：没有 native 记录时，撤销的 Owner 不得继续授权 dev 执行 |
| dev 环境变量缺失/不等 | `development_installation_denied` 403 | 不能；进程 exit 1，未开端口 |
| frozen 产物 | `development_installation_unavailable` 503 | 不能；即使参数齐全也不构造 |
| 进程运行中源码/资源被改 | 下一次 `current_guard` 的 `assert_current` 抛 `development_code_changed`/`development_resource_changed` | 不能；AF 前已提交事实保留，但本次 attempt 失败 |
| dev 身份过期 | `production_execution_identity_denied` 403（`_identity:178`）或 `production_admission_expired` 403（`_persist:471`） | 不能；重启并用新的 `--development-expires-at` 重新登记 |
| 运行中撤销 Owner binding | 本次进程不感知（dev 只在启动读一次） | 已在跑的 attempt 仍会因身份 `expires_at_us` 到期而失效；要立即生效必须停进程。这是 dev 专属限制，见第 8 节 |

`owner-init` 的 TTY 要求不是 dev 引入的：它是既有 `confirm_local_action` 语义，dev 只是无法绕过它。

## 7 不做的事

- 不写 qualification 表、不实现 `QualifiedInstallationIssuer`、不触碰 `native_qualified_*` 与 `installation_qualification_*`。
- 不新增数据库表、不改迁移、不写任何迁移文件。
- 不放宽 `_identity`/`_installation`/`_guard`/`_issued_guard`、`register_execution_identity` 的任一前置、`install_startup_services` 的任一 `is`/type 校验。发现"必须改生产校验才能通过"的地方一律停下回报统筹。
- 不支持 v2/v3（生成式链），不支持 `mcp` 角色。
- 不做 unattended/policy 模式：`automation.mode` 必须是 `interactive`。unattended 需要 `bind_request` 的不可变策略事实链与已装 policy，本卡不提供，也不伪造。
- 不做 ASR：local-v1 的 ASR 四联必须全为 null；一旦 `mixed_audio` 进入 selection，按真实 `production_asr_resource_required` 阻塞，不伪造字轨或空转写。
- 不改 ready 字段、`InstanceHealth`、OpenAPI、`schemas.json`、传输声明或 `packages/contracts`。
- 不新增携带范围的环境变量；只有用于授权的 `VIDEO_CREATOR_DEVELOPMENT_INSTALLATION`。
- 不把 dev 证据写成生产 evidence，不做哈希缓存或布尔短路，不接受调用方传入的 evidence/哈希。

## 8 风险与后继

1. **语义差（dev vs native）**：dev 没有 held pipe、Owner-protected build、qualification、独立安装记录、OS 级完整图与进程/角色绑定；也不核宿主镜像。它能证明的只有"checkout 字节与配置一致"。任何一方把 dev 绿色当安装/发布证据，都是本 ADR 明确禁止的越级。
2. **哈希成本**：`_installation` 每次 `current_guard` 都调 `observe()` + `assert_current()`，等于每次约 183 个 engine 文件 + 全部资源文件的两次全量哈希。API 受理、worker 每次 `_current_services`/`_remember_current_services` 都会重复。这是"真实哈希"的直接代价，禁止用缓存、mtime 或"启动时算一次"优化掉；若确需性能，只能另立卡改协议语义（需统筹决定）。
3. **源码漂移**（最可能的日常失败）：任何 engine `.py` 编辑都会让注册文件同时触发 `development_engine_incomplete` 或 `development_code_changed`。dev 流程必须把"重生成注册文件"作为固定步骤，否则表现为每次制作都在 `_installation` 处 503。
4. **Owner 主语被钉死为 `local-user`**：`RegisteredMediaRuntime` 内部 `BundleService` 不传 principals（`media_registration.py:233-234` → `bundles.py:287` 默认 `local-user`），而 `assemble_owner_services:111-112` 要求 `bundle.principals.owner_subject == owner_subject`。因此当前切片下 dev 的域 Owner 必须是 `local-user`（`serve-dev` 侧同一要求，保持 API/worker 同主体）。要支持任意 Owner，需要改生产 producer 构造——需统筹决定，本卡不擅自改。
5. **API 角色不构造 `RegisteredMediaRuntime`**：那会额外产生第二个 `BundleService`/`WorkerService`/`AsrResultJournal` 并覆盖 `engine._registered_plan_source`、`bundle._production_services_runtime` 等既有接线（`media_registration.py:233-255`）。代价是 dev 必须复刻 local-v1 的 manifest/runtime/tools 三个哈希校验并与 `media_registration.py:206-216` 保持同义；漂移应由集成/测试用同一 fixture 双向锁定。
6. **运行中撤销不生效**：dev 只在启动时用 `current()` 读一次 binding；native 路径靠安装记录 + 短 writer 的 epoch 校验补足，dev 没有这个锚。缓解是有限的 `expires_at_us`。这必须在运行手册里写明，不能宣称 dev 与 native 同等即时撤销。
7. **退役路线**：一旦 Rust native 宿主可编译并有真实安装记录与资格（ADR0036/ADR0043 方向），dev host 应整体删除而非长期双轨：删除 `cli/development_host.py`、`application/development_installation.py`、该环境变量与 `/health` 头，把 `tests/development/` 迁到 native 入口，并在 README 撤销"非生产"说明。退役前，dev 的存在必须在运行手册中标注"非生产、不可发布"。
8. **未覆盖**：本地-v1 human 链仍需真实提交审核决定才能过 `ProductionPorts.current_production_admission`（`vc/application/production_ports.py:111-149`）；这属于测试角色的真实链路义务，不是 dev 边界，dev 不得替人批准。

## 9 下游交接

- **后端**（白名单 `application/`、`cli/`）：新增 `application/development_installation.py`（`DevelopmentLaunchConnection`/`DevelopmentLaunchBuild`/`DevelopmentInstallationAuthority`）与 `cli/development_host.py`（parser + argv 改写 + factory 闭包 + 三重条件），按第 2/3/4 节实现；`cli/main.py` 必要时只加不改变既有分支的转发；`api/app.py` 只加 `/health` 响应头来源（不写 OpenAPI）。提交前用 grep 证明除 `cli/development_host.py` 外无人 import `development_installation`。
- **集成**（白名单 `packaging/`、依赖/配置、`packages/contracts`、根 README）：生成 `RegistrationConfigLocalV1` JSON（字段见 `local_material_production.py:60-89`；`engine_source_sha256` 必须覆盖当时 `_package_sources` 全集）、`LocalMaterialResourcesV1` 资源清单与运行时索引、真实 ffmpeg/ffprobe 路径；不改契约生成物的字节。运行手册写清：TTY 跑 `owner-init initialize --owner-subject local-user --project-id … --expires-at …`、注册四条 local route、`serve-dev`/`worker-dev` 的三重条件与 `local-development` 头。
- **测试**（白名单 `tests/`）：端到端只走 `serve-dev` + `worker-dev`；必须验证 dev 未启用时拒绝（三条件各缺一次）、health 头仅 dev 出现、生产 `serve` 无该头且无 dev 对象、源码被改后 `development_code_changed`、frozen 模拟拒绝、真实 ffmpeg 渲染与 0.4 包。
- **评审**：只读第 2/3 阶段源码，核对本 ADR 第 1 节"保持原样"清单未被触碰。
