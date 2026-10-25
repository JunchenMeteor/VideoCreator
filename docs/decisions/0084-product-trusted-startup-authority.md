# ADR0084：产品受信启动权威（Product Trusted Startup Authority）

状态：ARCHITECTURE_FROZEN_DESIGN_ONLY，2026-10-26。冻结产品形态**执行权威**的四要素与判定顺序、对象协议、构造时机与装配衔接、授予/不授予、与 ADR0081 的关系、失败语义、防伪造边界、Backend/Test 接口与验收。**本卡只写文档**：不改源码、不改迁移、不改契约、不写测试、不产出安装包。§9 的全部用例 **NOT_EXECUTED**。

上游事实（已实测）：冻结产物没有 factory ⇒ `install_startup_services(None, …)` 返回 `None` ⇒ 无执行身份 ⇒ 制作 403 `production_authorization_unconfigured`（ADR0083 §0.3-2、§7-6）。本卡把这个缺口补上一个**非 dev、非 native** 的第三类可信来源。

## 0 实读证据（行号取 HEAD `3f039df`；`vc/` = `services/engine/src/video_creator`）

| 事实 | 位置 |
| --- | --- |
| 装配硬门只认 `NativeOwnerServices` 精确类型，并逐项核 authority 身份 | `vc/cli/startup_services.py:56-91`（类型门 `:74-76`，身份门 `:80-90`） |
| 无 factory 时直接返回 `None` | `vc/cli/startup_services.py:61-62` |
| `NativeOwnerServices` 是普通 dataclass（`authority` 注解不参与运行时校验） | `vc/application/native_installation.py:121-141` |
| 该对象的 `close()` 会调 `authority.close()` 与 `build.close()` | `vc/application/native_installation.py:130-135` |
| 权威实际被调用的只有 5 个成员：`connection`、`observe`、`assert_current`、`assert_local_current`、`close` | `vc/application/production_admissions.py:100-109,182-237,267-287`；ADR0077 §3.1 |
| 证据协议字段（6 个精确相等 + 两个非空 tuple） | `vc/application/production_admissions.py:35-51` |
| 每次观测必须现取 `engine.clock()`，且不得重名/不得绝对名 | `vc/application/production_admissions.py:186-203` |
| `_issued_guard` 只在 `type(authority) is NativeInstallationAuthority` 时取 qualification_issuer | `vc/application/production_admissions.py:240-247` |
| 短钩子 `assert_local_current` 在每个 writer 内被调用（禁止 I/O/哈希/DB/阻塞锁） | `vc/application/production_admissions.py:280-281` |
| 执行身份有效期必须有限且大于当前时钟 | `vc/application/production_admissions.py:118-125`；`vc/application/owner_services.py:136-147` |
| `configure_production_authorization` 只在 `execution_registration is not None` 时调用 | `vc/application/owner_services.py:145-154` |
| 装配会无条件新建并安装 copy 服务（第二次被拒）⇒ 每进程一次 | `vc/application/owner_services.py:129-130`；`vc/application/engine.py:90-99` |
| `serve` 在 `listener.bind` 之前调用 `install_startup_services` | `vc/cli/main.py:426-427` vs `:465-468` |
| 有 factory 但装配因 Owner 缺失失败时，注入 session secret 则回落受限 | `vc/cli/main.py:428-443`（条件 `:435-437`） |
| 受限分支只挂 health 与授权路由 | `vc/api/app.py:142-155` |
| factory 命令域只允许 `serve`、`mcp-stdio`、registered worker | `vc/cli/main.py:216-219` |
| 无执行身份时执行 403 | `vc/application/engine.py:140-146` |
| 无 management 时管理动作 503 | `vc/application/production_authorization.py:37-41` |
| `NativeLaunchContext` 强校验（role、三 SHA、完整文件图、engine 真子集） | `vc/infrastructure/held_authority.py:92-125` |
| 相对名规范（无前导 `/`、无反斜杠、无 `:`、无空段/`.`/`..`） | `vc/infrastructure/held_authority.py:47-51` |
| dev 权威已实现同形状（`observe`/`assert_current` 外重核、`assert_local_current` 短钩子、epoch+thread 保留表、retire 码） | `vc/application/development_installation.py:178-292` |
| dev 的 `launch_context` 用同一批已哈希事实构造真实 `NativeLaunchContext` | `vc/application/development_installation.py:139-148` |
| 引擎源全集/资源全集的唯一实现（必须复用，不得另写遍历） | `vc/application/media_registration.py:44-45,89-101,113-126` |
| 注册必须被钉定文件+SHA 才能启用 | `vc/cli/main.py:188-209,396-406`；`vc/application/media_registration.py:142-147` |
| worker 侧三 SHA 必须等于安装资源身份 | `vc/application/media_registration.py:342-347,862` |
| `RegisteredMediaRuntime` 的 `sha256` 就是注册文件实算值 | `vc/application/media_registration.py:130-152` |
| Owner 目录 OS 身份只能由真实目录取得（主体/设备/inode，非链接） | `vc/infrastructure/owner_identity.py:107-129` |
| 无 binding 时 `assemble_owner_services` 的 `current()` 直接失败 | `vc/application/owner_services.py:116-119`；`vc/application/owner_bootstrap.py:124-134` |
| dev factory 的完整装配顺序可作模板（但含 frozen 拒绝与环境条件，产品不得照抄这两处） | `vc/cli/development_host.py:434-518` |
| 产品内授权只写 binding、不产生管理能力 | `vc/application/owner_bootstrap.py:317-322,385-394` |

### 0.1 五项必须核清的事（结论如下）

1. **类型门不需要放宽。** `type(native) is NativeOwnerServices` 对 `authority` 字段只做 `is` 比较（`startup_services.py:81,85-86`），而 `NativeOwnerServices` 是普通 dataclass、`authority` 的 `NativeInstallationAuthority | LocalInstallationAuthority` 注解不参与运行时校验（`native_installation.py:121-127`）。因此**新的产品权威类型可以直接放进 `NativeOwnerServices.authority`**，一行生产校验都不用改。这是本卡成立的技术前提。
2. **不会误走 qualification 分支。** `_issued_guard` 与 `_management_transaction` 都写死 `type(authority) is NativeInstallationAuthority` 才取 `qualification_issuer`（`production_admissions.py:240-247`；`owner_services.py:52-53`）。产品权威只要是**别的类型**且**不实现** `qualification_issuer`，qualification 路径自动为空。
3. **"每进程只能装配一次"天然满足。** factory 只由 `install_startup_services` 调用一次，而 `serve` 在 `listener.bind` 之前调用它一次（`main.py:426` → `:467`）；装配内部无条件 `configure_local_copy_inputs`，第二次会 `local_copy_configuration_conflict`（`owner_services.py:129-130`、`engine.py:90-99`）。所以"首次请求再构造"在设计上不可行（§4.2）。
4. **"权威存在但无 Owner 同意"有现成机制。** 有 factory 时 `restricted` 为假（`main.py:415`），走 `install_startup_services`；`assemble_owner_services` 因无 binding 抛 `owner_not_initialized`/`owner_restore_refresh_required`；`main` 在**启动器注入了 authorization session secret** 时改为受限并挂授权通道（`main.py:428-443`），否则原样抛出（fail-before-bind）。不需要新写分支。
5. **dev 路径的另外两道门不能带过来。** dev factory 的 frozen 拒绝（`development_host.py:441-443`）与环境变量条件（`:185-190`）都是 dev 专有：产品形态**必须**能在冻结产物里跑，且**不得**读 `VIDEO_CREATOR_DEVELOPMENT_INSTALLATION`。这两处是本卡与 dev 的根本分界。

## 1 结论摘要

1. **权威＝四要素的合取**：①安装记录（`Control/InstallationProvisioning.json`，含权威锚点）②实例目录的 OS 所有者/设备/inode ③registration sha（文件实算 = 钉定 = 记录）④资源清单 sha（`resource`/`runtime` 两个）；四者任一不成立即拒绝（§2）。
2. **记录复用 ADR0083 B6 的同一份文件**，不另立第二份（避免两份记录漂移）。ADR0083 B6 增补权威锚点字段（§3.1）。
3. **构造时机＝trusted startup（进程启动、监听之前）**：`product-serve`/`product-worker` → 校验四要素 → 构造真实 `NativeLaunchContext` → 构造 `ProductInstallationAuthority` → 调 `cli.main.main(installed_service_factory=factory)`；factory 在 `install_startup_services` 内被调一次。
4. **授予"制作/发布"，不授予任何管理能力**：`services.registry is None` 与 `for_management=False` 是硬门；policy/budget/daily/execution registration/qualification/evidence 全部不出自本权威（§5）。
5. **与 ADR0081 正交**：同意只写 binding；权威只读安装事实。组合矩阵四种状态全部有确定行为（§6）。
6. **失败全部具名、全部发生在监听之前**（一个例外：运行期字节漂移发生在 writer 内，返回 503）。
7. **诚实边界**：同 OS 账户的原生代码仍可同时改写程序/注册/记录/钉定——本设计**不宣称**防它（ADR0036 既有边界），只防跨实例复制、挪目录、非安装器写入、重放旧记录、字节漂移。
8. **零放宽**：`install_startup_services`、`assemble_owner_services`、`ProductionAdmissions`、`NativeLaunchContext`、`management_access` 一行不改；不新增表/迁移（记录是 `Control/` 下的文件）。

## 2 权威四要素与判定顺序

### 2.1 四要素

| # | 要素 | 精确来源 | 由谁写 | 防什么 |
| --- | --- | --- | --- | --- |
| E1 | **安装记录** | `<instance-dir>/Control/InstallationProvisioning.json`（ADR0083 B6，`installation-provisioning-v1`）：`complete=true`、`record_revision`、`instance_id`、`install_root`、`engine_package_relative`、`instance_dir`、三个 SHA（registration/resource/runtime）、`os_subject`、`administrator_id`、`instance_device`、`instance_inode`、`expected_files`、`engine_file_names`、`items[]` | 安装器（`installer-admin provision`，ADR0083 §2.2） | 非安装器写入、被裁剪/伪造的记录、重放旧记录 |
| E2 | **实例目录 OS 身份** | `inspect_owner_directory(instance_dir)` 的 `os_subject`/`administrator_id`/`directory_device`/`directory_inode`，且路径非链接、非 UNC、真实目录（`owner_identity.py:107-129`） | OS（安装时建目录）+ 记录（比对值） | 跨实例复制、镜像内挪目录、换机 |
| E3 | **registration sha** | `Registration.json` 全文件 `sha256`，必须同时等于 ①文件实算 ②启动器钉定 `--production-config-sha256` ③记录 `registration_sha256` | 安装器生成、启动器钉定 | 换注册、旧注册配新程序、钉定与文件不符 |
| E4 | **资源清单 sha** | 注册里的 `production_resource_manifest_sha256` 与 `production_runtime_manifest_sha256`，必须同时等于 ①记录 ②注册解析结果 ③被索引文件的实算集合 | 安装器生成 | 资源被替换/裁剪、清单与字节不符 |

补充：`engine_source_sha256` 不在四要素里另立一项，因为它是 E3 的一部分（注册文件的字段），但**必须**在启动时用 `_package_sources` 重算并与注册字段逐字相等——那是 §2.2 的第 12 步。

### 2.2 判定顺序（逐项 fail-closed；任一步失败即拒绝，不进入下一步）

| 步 | 判定 | 失败码 | 阶段 |
| --- | --- | --- | --- |
| 1 | 入口是 `product-serve`/`product-worker`，且 argv/env 中**不存在**任何 `--development-*`、`VIDEO_CREATOR_DEVELOPMENT_INSTALLATION` | `trusted_startup_entry_denied` 403 | 解析前 |
| 2 | 两个钉定参数齐全：`--installation-record <绝对路径>`、`--installation-record-sha256 <64hex>`；`--production-config` 与 `--production-config-sha256` 齐全 | argparse 使用错误 exit 2（不产生 HTTP） | 解析 |
| 3 | 记录存在、普通文件、非链接、≤1 MiB | `trusted_startup_record_missing` 503 | 启动前 |
| 4 | 记录全文件 SHA == 钉定 | `trusted_startup_record_changed` 503 | 启动前 |
| 5 | 记录可解析：严格 JSON（无重复键/无 NaN）、`format` 相符、字段集精确、数值为 int/字符串长度受限 | `trusted_startup_record_invalid` 422 | 启动前 |
| 6 | `record.complete is True` 且 `record.record_revision ≥ 1` | `trusted_startup_record_incomplete` 503 | 启动前 |
| 7 | `record.instance_id == engine.instance_id` | `trusted_startup_instance_conflict` 409 | 启动前 |
| 8 | `record.instance_dir` 解析后 == `--data-dir` 解析后，且两者非链接/非 UNC | `trusted_startup_instance_conflict` 409 | 启动前 |
| 9 | 程序确实在 `record.install_root` 内：`PACKAGE_ROOT` 与 `sys.executable`（或 `_MEIPASS`）都 `is_relative_to(record.install_root)`，且 `engine_package_relative` 相符 | `trusted_startup_layout_conflict` 409 | 启动前 |
| 10 | E2：`inspect_owner_directory(instance_dir)` 的四个值与记录逐字相等 | `trusted_startup_owner_changed` 409 | 启动前 |
| 10b | 记录里的规范化 DACL 摘要（若存在）与当前实例目录 DACL 摘要相等 | `trusted_startup_acl_changed` 409 | 启动前（见 §8.3） |
| 11 | E3：注册文件实算 == 钉定 == 记录；解析出的 `resource`/`runtime` 两 SHA == 记录 | `trusted_startup_registration_conflict` 409（文件缺失/链接 → `trusted_startup_record_missing` 503） | 启动前 |
| 12 | E4 + 引擎全集：`_package_sources(PACKAGE_ROOT)` 的键集合 == 注册 `engine_source_sha256` 键集合（不等 → `trusted_startup_bytes_changed` 503），逐文件 `_hash` 相等（不等 → 同码）；被索引资源（`ffmpeg`/`ffprobe`/两份清单/ASR 清单）实算 == 注册 | `trusted_startup_bytes_changed` 503 | 启动前（一次全量观测） |
| 13 | 名字规范与不重名：engine 名 ∖ resource 名 = ∅；每名过 `held_authority._relative` 同语义；`engine_file_names ⊂ names` 且非空 | `trusted_startup_identity_invalid` 422 | 启动前 |
| 14 | role ∈ {api, worker}，且与命令匹配（`product-serve`→api、`product-worker`→worker） | `trusted_startup_role_denied` 403 | 启动前 |

第 12 步的**唯一实现**要求：必须调用 `media_registration._package_sources`/`_local_file`/`_hash`（或与之逐字节同义、且被同一测试覆盖的共享实现），不得另写一套遍历（ADR0077 §3.4 纪律；`development_installation.py:15-20` 就是照这个做的）。建议把 dev 的 `engine_source_facts`/`indexed_resource_facts`（`development_installation.py:42-105`）**上提**为共享模块（如 `application/installation_facts.py`），dev 与 product 都调用它；这是唯一允许的"搬位置不改语义"重构，且 dev 行为必须零变化。

### 2.3 三个被拒的候选来源

| 候选 | 拒绝理由 |
| --- | --- |
| 环境变量（如 `VIDEO_CREATOR_INSTALLED=1`） | 任何进程都能设；ADR0081 §12 已禁止"环境变量直接构成授权"。产品权威只接受来自 argv 的**钉定**，而 argv 由启动器给、且钉定值是 SHA（改了就与实际字节不符） |
| 配置文件自声明的 authority（例如记录里写 `authority: true`） | 记录本身可被同账户改写；它必须锚定**不可自证**的事实（OS inode、实际字节哈希）才有意义 |
| 安装器自签 token/密钥 | 无代码签名证书与可信密钥分发（ADR0083 §7-1、§7-4），自签会让"看起来像密码学保证"而实际只由安装器生成；本卡拒绝引入这种假象 |

## 3 对象协议

### 3.1 安装记录（复用 ADR0083 B6 的文件，不另立）

```text
Control/InstallationProvisioning.json          format = 'installation-provisioning-v1'
  # ADR0083 B6 已有
  complete, installer_version, provisioned_at_us, instance_id, project_id,
  registration_sha256, items[], counts{}, revision
  # 本卡新增的权威锚点（同一文件，revision+1 时只追加）
  install_root, engine_package_relative, instance_dir
  os_subject, administrator_id, instance_device, instance_inode
  resource_manifest_sha256, runtime_manifest_sha256
  expected_files: [{relative_path, bytes, sha256}], engine_file_names: [str]
  dacl_summary_sha256: str | null          # §8.3，可为 null
```

约束：`expected_files` 必须是**完整有限图**（engine 全集 ∪ indexed resources，不多不少），`engine_file_names` 是非空真子集；`instance_dir`/`install_root` 绝对、非 UNC；总体积 ≤ 8 MiB（`NativeLaunchContext` 的 32 MiB 上限在 `held_authority.py:122-125` 已守一次，记录侧再守一次以免解析期就爆）。

### 3.2 三个类

```text
application/product_installation.py（新增；frozen 可用）

class ProductStartupBuild:
    def close(self) -> None            # 幂等；不触达文件、不持 OS 句柄

class ProductStartupConnection:
    context: NativeLaunchContext       # 真实构造（3.3），不是 duck type
    def close(self) -> None            # 幂等

class ProductInstallationAuthority:
    connection: ProductStartupConnection          # 每次访问返回同一对象
    def observe(self) -> InstalledProductionEvidence
    def assert_current(self, observation) -> None
    def assert_local_current(self, observation) -> None
    def close(self) -> None
```

硬要求（与 ADR0077 §3.1/§3.5 同构，逐条可核）：

- **不实现** `qualification_issuer`、`observe_facts`、`assert_current_facts`、`assert_local_observation`；类型**不是** `NativeInstallationAuthority`、也不是 `LocalInstallationAuthority`、也不是 `DevelopmentInstallationAuthority`（`production_admissions.py:240-247` 靠类型分派）。
- `observe()` 每次新建 evidence，登记 `id(evidence) → (evidence, epoch, thread_id)`；`assert_current`/`assert_local_current` 只接受保留表内同一对象、同一 epoch、同一线程（`development_installation.py:239-292` 同构）。不序列化、不跨进程、不缓存、不复活。
- `assert_current` 是 writer 外重核：重新实算 E3/E4 与两份全集，逐项等于 observation 的两个 tuple；不等 → `trusted_startup_bytes_changed` 503。
- `assert_local_current` 是短钩子：只做对象/epoch/thread/closed 判定 + 一次非阻塞锁（忙即 `installation_session_busy` 503）；**禁止**文件 I/O、哈希、DB 读、阻塞锁（`production_admissions.py:280-281` 在 DB writer 内调它）。
- `close()` 幂等；retire 后四个方法一律 `trusted_startup_retired` 503，并从保留表移除。

### 3.3 证据逐字段来源（`InstalledProductionEvidence`，`production_admissions.py:35-51`）

| 字段 | 取值 |
| --- | --- |
| `instance_id` | `engine.instance_id`（并已与记录比对） |
| `registration_sha256` | 注册文件**实算**全文件 SHA（每次 observe 重算，且必须 == 钉定 == 记录） |
| `resource_manifest_sha256` | 解析出的 `config.production_resource_manifest_sha256`（并 == 记录） |
| `runtime_manifest_sha256` | 解析出的 `config.production_runtime_manifest_sha256`（并 == 记录） |
| `workflow_version` | 常量 `'registered-media-bundle-v1'` |
| `driver_profile` | 常量 `'registered-production-drivers-v1'` |
| `observed_at_us` | 每次现取 `engine.clock()`；禁止常量/配置/未来值 |
| `engine_source_sha256` | `((相对路径, hex), ...)` 按相对路径排序，覆盖 `_package_sources(PACKAGE_ROOT)` **完整集合** |
| `indexed_resource_sha256` | 配置点名的非 engine 文件逐文件 sha，按相对路径排序，**非空**（manifest、runtime manifest、ffmpeg、ffprobe、ASR 清单若声明） |

`NativeLaunchContext` 必须**真实构造**（`held_authority.py:92-125`）：`expected_files` = engine ∪ resources 的完整 `HeldFileFact` 元组；`engine_file_names` = engine 名集合（真子集）；三 SHA 来自记录。不得为省事传只有两个属性的对象（那会让"完整文件图/分区"这条既有不变量在本路径消失）。

### 3.4 生命周期与身份绑定

- authority 与 connection 只在**本次进程**有效；`ProductStartupBuild` 无 OS 句柄、无 held pipe（这是与 native 的本质差别，也是本卡的诚实边界之一：它没有受保护构建事实）。
- `close()` 顺序：`authority.close()` → `build.close()`（与 `NativeOwnerServices.close()` 的调用序一致，`native_installation.py:130-135`）；`services.execution_identity` 由 `NativeOwnerServices.close()` 注销（`:133-134`）。
- 并发：authority 内 `RLock` 只保护保留表；`observe()` 可与其他线程的 writer 并发（`assert_local_current` 在忙时返回 503，不排队）。

## 4 构造时机与装配衔接

### 4.1 固定时序（全部在 `listener.bind` 之前）

1. 启动器拉起 `VideoCreatorEngine.exe product-serve|product-worker …`（固定参数，用户不输入）。
2. `Entry.py` 只做**前缀分派**到 `cli/product_host.main(argv)`；`cli/main.py` 的 parser 与分支一行不改（`main.py:128-185`）。
3. `product_host` 解析两个钉定，按 §2.2 的第 3-14 步判定（此时**尚未**构造 `EngineService`，除第 7 步需要实例身份——实现可先用只读连接读 `metadata.instance_id`，**不建库**，与 `development_host.py:203-224` 同一做法）。
4. 通过后构造 `EngineService(data_dir)` → 构造 `NativeLaunchContext` → `ProductStartupConnection(context)` → `ProductStartupBuild()` → `ProductInstallationAuthority(...)`。
5. `product_host` 立刻做**一次** `observe()` + `assert_current()`（fail-fast：字节不符就在此失败，绝不进入监听）。
6. `product_host` 调 `cli.main.main(installed_service_factory=factory)`，argv 改写为 `serve` / `worker --workflow registered-media-bundle-v1`（与 `development_host.py` 同法）。
7. `serve` 仍按现有顺序：`EngineService` → `installed_local_registration` → `install_startup_services(factory)` → `factory(...)` → `assemble_owner_services(...)` → `listener.bind`（`main.py:397-468`）；`worker` 分支同理，factory 还会收到同一 engine/bundle 的 `RegisteredMediaRuntime`。
8. factory 内（一次）：校验 `for_management is False`、role 与上下文一致、`registered_runtime.installation_resource_identity == 上下文三 SHA`（`media_registration.py:342-347,862`）；取 Owner binding 的 `owner_subject`/`project_ids`/`expires_at_us`；构造 `execution_registration` 字典（8 个键，`owner_services.py:136-144`）；`assemble_owner_services(..., installation_authority=authority, installation_session_guard=authority, execution_registration=...)`；返回 `NativeOwnerServices(services, connection, authority, build)`。

### 4.2 为什么不能"首次请求再构造"（四条，逐条可核）

1. `install_startup_services` 的类型门要求 `NativeOwnerServices` 且 `admissions.installation_authority is native.authority`（`startup_services.py:74-91`）；请求线程里构造 authority 与在请求线程里装配 `OwnerServices` 是同一件事，而后者被 `assemble_owner_services` 文档明确限定为 "Trusted host/CLI startup only"（`owner_services.py:105-110`）。
2. 每进程只能装配一次（`owner_services.py:129-130` + `engine.py:90-99`）；受限进程先跑、请求期再装配第二套是设计上不可行。
3. `engine._authorization_identity` 是进程内映射，`configure_production_authorization` 只在装配时调用（`engine.py:113-138`）；晚装配等于把"身份写入"变成 HTTP 可触发动作。
4. ADR0081 §2 已经为"授权后同进程解锁"给出三条不可能性；本卡沿用同一结论：**权威只能在启动时构造，授权后靠重启生效**。

### 4.3 命令域与 `Entry.py` 分派

- 新增：`product-serve`、`product-worker`（二者都由 `cli/product_host` 自己的 parser 定义，再改写成 `serve`/`worker`）。
- `Entry.py` 只加"名字前缀 → 不同 host 模块"的分派；`video_creator.cli.main` 的 `parser()` 与 `main()` 零变化，`main()` 的 factory 命令域守卫（`main.py:216-219`）零变化。
- `--production-config`/`--production-config-sha256` 继续透传给 `serve`/`worker`，由它们完成 `installed_local_registration` 与 `RegisteredMediaRuntime`（`main.py:188-209,399-406`）。
- R1 准入 role = `api`、`worker`；`mcp` 不在本卡（MCP 需要 `VIDEO_CREATOR_MCP_TOKEN` 与证据接线，另立卡）→ `trusted_startup_role_denied`。

### 4.4 失败清理与受限回落

- factory 在 `try/except` 内自建三件套；任何失败**先**按 `authority.close()` → `build.close()` → `connection` 已被 `authority.close()` 关闭的顺序释放，再原样抛出**原始** `EngineError`（不包装、不改码），与 `development_host.py:519-526` 同法。
- 若失败码是 `owner_not_initialized`/`owner_restore_refresh_required`（即"没有 Owner 同意"），`serve` 会在启动器注入 session secret 时回落受限（`main.py:428-443`）；此时必须保证没有遗留打开对象（否则 `install_startup_services` 的后续检查与 SDK 生命周期会混）。**这是"权威存在但不可用"的唯一合法路径。**
- 启动器**必须**注入 `VIDEO_CREATOR_AUTHORIZATION_SESSION_SECRET`；缺失时不回落，进程以 503 失败（fail-closed，首次启动应显示具名错误而不是启动一个没有授权页的实例）。

## 5 授予 / 不授予

### 5.1 授予（精确能力清单）

| 能力 | 机制 | 边界 |
| --- | --- | --- |
| 一次 `register_execution_identity` | `assemble_owner_services` 内调用（`owner_services.py:145-154`） | 仅在 `registered_runtime` 与三 SHA 相符时；产物是**进程内**对象，随进程消失 |
| 作为 `ProductionAdmissions.installation_authority` 与 `installation_session_guard` | `install_startup_services:85-86` | 提供"已安装字节当前性"观测 + 短钩子；不提供 qualification |
| **interactive 制作** | `POST /api/v1/productions` → worker 执行 | 仍需 Owner binding、policy、routes、预算逐项通过既有门 |
| **发布本地 0.4 作品包** | bundle/assembly 路径 | 仍需证据门（ADR0082 自签 policy 未装时语音作品 `alignment_required` 409） |
| worker 的 `RegisteredMediaRuntime` 装配 | `main.py:265-273` + 本权威三 SHA 相符 | 三 SHA 不符即 `production_installation_binding_invalid` 503 |

### 5.2 不授予（逐项，均有硬门可核）

| 不授予 | 硬门 |
| --- | --- |
| 任何 `AdministrationCapability` | `install_startup_services` 要求 `services.registry is None` 且 `services.authorization.management is None`（`:88`）；本卡固定 `for_management=False` |
| policy install/select/revoke、预算授权、daily creation | 无 management ⇒ `production_management_unconfigured` 503（`production_authorization.py:37-41`） |
| execution registration install/replace/select/revoke | 需要 native observer / held facts（`cli/owner.py` 的 `owner-execution`），本权威不实现 `observe_facts` |
| qualification / evidence policy / benchmark / admission | 需独立 authority 与真实语料；本权威不实现 `qualification_issuer`；自签证据仍走 ADR0082 的一次性 `evidence-admin` + 产品授权收据 |
| 注册路由 / 写注册 / 改 floor / 建 secret / 写 Owner binding | 属于安装器（ADR0083 §2）或 `change()`（同意）；本权威只有读与观测 |
| unattended 自动制作 | 需 policy + `require_operation_current`（`engine.py:734-737`）；本权威不产生 policy |
| 跨实例能力 | evidence 绑定 `instance_id` + 目录 inode + 三 SHA；任一不符即 409/503 |
| "改字节还能跑" | 每次 `observe`/`assert_current` 重算全集（§3.2） |
| 同进程解锁 | §4.2 第 4 条（ADR0081 §2 不变） |

### 5.3 一句判据

**本权威只回答一个问题："这份安装的字节、注册与目录身份，现在是否仍然是安装器当初写下的那一份？"** 它不回答"谁同意了什么"（Owner binding）、不回答"允许做什么"（policy）、不回答"方法是否合格"（qualification）。三件事各有各的来源，互不代签。

## 6 与 ADR0081 的关系

### 6.1 两个独立事实

- **Owner 同意**（ADR0081）：只写一次有范围的 binding + 审计；不产生管理能力；完成后必须重启。
- **执行权威**（本卡）：只读安装事实；不写任何持久状态；不产生任何"同意"。

### 6.2 四种组合的确定行为

| Owner binding | 执行权威 | 进程行为 | 用户可见 |
| --- | --- | --- | --- |
| 无 | 无（今天的冻结包） | `restricted`（`main.py:415`） | 授权页 |
| 无 | **有**（本卡实现后） | factory 抛 `owner_not_initialized` → 回落受限（需注入 secret） | **授权页**（权威存在但不可用） |
| 有 | 无 | 无 factory ⇒ `install_startup_services(None) ⇒ None` ⇒ 制作 403 | 工作台 + 具名阻断 |
| 有 | 有 | 装配成功 | 可制作 |

第二行是本卡的核心语义：**权威不替代同意**。它不会因为"安装是可信的"而让实例跳过授权页；授权页是否出现只由 binding 是否存在决定。

### 6.3 重启语义

授权完成 → 受限进程写 binding 与审计 → `state=complete, restart_required=true` → 启动器停引擎、重启 → 新进程在 trusted startup 构造权威 → 装配成功 → `/health: none` + 可制作。**权威绝不在授予后"补构造"**到已在运行的进程里（§4.2）。

### 6.4 不得做的事

不得让授权进程在 approve 之后**自查**本权威以跳过重启；不得把"安装记录完整"当成"可以免授权"；不得让本权威写 binding/审计/policy；不得让本权威在 `for_management=True` 下被装配。

## 7 失败语义

| code | 步骤 | 含义 | 监听？ |
| --- | --- | --- | --- |
| `trusted_startup_entry_denied` | 1 | 从 dev 入口带 dev 参数调用，或 env 里出现 dev 变量 | 否 |
| `trusted_startup_record_missing` | 3、11 | 记录/注册缺失、非普通文件、链接、超限 | 否 |
| `trusted_startup_record_changed` | 4 | 记录全文件 SHA ≠ 钉定 | 否 |
| `trusted_startup_record_invalid` | 5 | 记录不可解析/字段集不符/数值非法 | 否 |
| `trusted_startup_record_incomplete` | 6 | `complete != true` 或 `record_revision < 1` | 否 |
| `trusted_startup_instance_conflict` | 7、8 | 实例 id 或实例目录与记录不符（跨实例复制、换 data-dir） | 否 |
| `trusted_startup_layout_conflict` | 9 | 程序不在记录的安装根内（镜像内挪目录、混装） | 否 |
| `trusted_startup_owner_changed` | 10 | OS 所有者/管理员/设备/inode 不符（换机、换目录、ACL 被改所有权） | 否 |
| `trusted_startup_acl_changed` | 10b | 规范化 DACL 摘要与记录不符（见 §8.3） | 否 |
| `trusted_startup_registration_conflict` | 11 | 注册实算/钉定/记录三者不相等，或两清单 SHA 不符 | 否 |
| `trusted_startup_bytes_changed` | 12、运行期 | 引擎全集或资源字节与注册不符（含启动后漂移） | 否（12）/ 是（运行期 503） |
| `trusted_startup_identity_invalid` | 13 | 名字不规范、重名、engine 名不是真子集 | 否 |
| `trusted_startup_role_denied` | 14 | role 不是 api/worker 或与命令不配 | 否 |
| `trusted_startup_retired` | 运行期 | authority 已 close | 是（503） |
| `installation_session_busy` | 运行期 | 短钩子遇到并发观测 | 是（503） |

共同纪律：错误以 `{"code","message"}` 单行 JSON 打到 stderr、exit 1（与 `main.py:510-514` 同形），**不得**静默降级、不得用"稍后重试"掩盖；`trusted_startup_*` 一律**不得**加入 `RESOURCE_WAIT_CODES`（`media_registration.py:46-52`），否则漂移会被 worker 当 `resource_not_ready` park 而不是失败。

## 8 防伪造：能防什么、不能防什么

### 8.1 能防（每条都对应一个机制）

| 攻击 | 防线 |
| --- | --- |
| 把 A 实例的 `Control/` 拷到 B 实例 | `instance_id` + `instance_dir` + `device/inode` 三者同时匹配（步骤 7/8/10）；拷来必 409 |
| 镜像内/盘符内挪目录 | inode/device 变（步骤 10）→ 409；换机同理 |
| 非安装器写入的"假记录" | 记录格式严格 + 全文件 SHA 必须等于启动器钉定（步骤 4/5） |
| 重放旧记录（升级后） | 记录 `registration_sha256` 必须等于当前钉定（步骤 11）；旧记录配新注册必 409 |
| 换注册/换程序/换资源 | 引擎全集与资源实算（步骤 12）+ 每次 `observe`/`assert_current` 重算 |
| 用 dev 条件冒充产品 | 入口/参数/环境三重拒绝（步骤 1），且产品权威类型不是 dev 类型 |
| 安装记录存在但供给未完成 | `complete`/`record_revision` 门槛（步骤 6） |

### 8.2 不能防（诚实边界，必须写进产品文档与验收报告）

1. **同 OS 账户的原生代码**可以同时改写程序、注册、记录与启动器钉定——本设计不引入签名/TPM，因此**不宣称**防它；这是 ADR0036 已声明的既有边界（"OS 保护不抵御同 Owner 原生代码"）。
2. **未签名的安装器**本身可被替换（ADR0083 §7-1 明确不做签名安装器）。
3. **进程内调试/注入**：不属于静态可信启动的防御范围。
4. **DACL 之外的文件系统语义**（例如把数据目录放到可被他人写入的网络/共享盘）：由步骤 8/10 的"绝对、非 UNC、非链接 + OS 所有者"部分覆盖，但网络重定向后的等价性不做密码学保证。

结论：本卡把"可伪造面"收敛到**同账户原生代码**这一个既有边界，并把其他所有伪造路径都变成具名拒绝；**不**把"安装记录可信"表述为"实例不可篡改"。

### 8.3 DACL 的定位（为什么有 `trusted_startup_acl_changed` 却仍以 owner/inode 为主）

- 主判定是 E2（OS 所有者 + 设备 + inode），因为它是 `owner_identity.py:107-129` 已实现、且与 Owner binding 同源的事实。
- DACL 摘要（`dacl_summary_sha256`）是**补充审计项**：安装器写入时计算"规范化后的 (SID, rights, inherited) 三元集合"的 SHA256，启动时重算比对；不等即 409。它防"其他账户被加进 ACL / Everyone 被放开 / 继承被恢复"这类**非所有者变更**，对同账户自身改写无效（同账户本来就能改）。
- 实现约束：必须按 SID + 权限位解析，**不得**依赖本地化文本（`icacls` 输出随语言变化）；不可用时 `dacl_summary_sha256` 写 `null` 并在记录里标注 `dacl_summary_unavailable`，此时步骤 10b 跳过（**不是**静默通过，而是记录里明写未覆盖）。

## 9 给 Backend 的接口与给 Test 的验收

### 9.1 Backend 清单（实现顺序）

1. `application/installation_facts.py`（搬位置不改语义）：`engine_source_facts()`、`indexed_resource_facts(root, config)`、`assert_engine_registration(config, facts)`、`assert_distinct_identities(...)`、`launch_context(...)`（源自 `development_installation.py:42-148`）。dev 改为调用它，行为零变化。
2. `application/product_installation.py`：`ProductStartupBuild`、`ProductStartupConnection`、`ProductInstallationAuthority`（§3.2）+ 记录解析器（严格 JSON、字段集、体积上限）。
3. `cli/product_host.py`：`main(argv)`；`product-serve`/`product-worker` 两个 parser；argv 改写；钉定解析；§2.2 判定；**一次** fail-fast 观测；调 `cli.main.main(installed_service_factory=factory)`；factory 内 §4.1-8 的装配与 §4.4 的清理。
4. `packaging/engine/Entry.py`：只加"命令名前缀 → host 模块"分派；`main.py` 零改动。
5. 供给侧（ADR0083）：`InstallationProvisioning.json` 增补 §3.1 的锚点字段（同一文件、`revision+1` 追加），并让启动器把 `--installation-record`/`--installation-record-sha256` 传给 `product-serve`。

硬约束：不新增表/迁移；不改 `install_startup_services`/`assemble_owner_services`/`ProductionAdmissions`/`NativeLaunchContext`/`management_access`；`api/app.py` 零改动；`packages/contracts` 与 `openapi.json` 字节不变（本权威不进任何公开契约）。

### 9.2 正例（"可制作"的唯一定义，必须真实运行）

| # | 用例 | 期望 |
| --- | --- | --- |
| P1 | 真实安装实例 → 产品内同意 → 重启 `product-serve` + `product-worker` | `/health` 无 `pending`；`ready` 行带 `principal_id`（`main.py:476-478`） |
| P2 | `POST /api/v1/productions`（interactive，本地 0.4） | 202/200 且 production 推进；worker 真实执行 |
| P3 | 走到 `succeeded` 且有 `bundle_ref` | 真实作品包（静音素材即可）；`RunSummary` 记录命令/exit/产物 SHA |
| P4 | 同一实例第二次制作 | 仍成功（证明权威不是一次性） |
| P5 | 重启后重复制作 | 仍成功（证明重启可重建权威） |

**P3 是"R1 可制作"的门槛**：只到 P2 不算。若缺 ASR/字体等资源，按 ADR0083 §8 的方式记 `NOT_EXECUTED`，不得用 Mock 或降低请求（例如把语音作品改成静音作品）冒充。

### 9.3 负例（"不可越权"，逐条必须失败且码相符）

| # | 用例 | 期望码 |
| --- | --- | --- |
| N1 | 删 `InstallationProvisioning.json` | `trusted_startup_record_missing` 503 |
| N2 | 改记录任意一个字节（不改钉定） | `trusted_startup_record_changed` 503 |
| N3 | 记录 `complete=false` | `trusted_startup_record_incomplete` 503 |
| N4 | 把 A 实例的 `Control/` 拷进 B 实例 | `trusted_startup_instance_conflict` 409 |
| N5 | `--data-dir` 指向另一个实例 | `trusted_startup_instance_conflict` 409 |
| N6 | 改动一个引擎 `.py` 或一个 ffmpeg DLL | `trusted_startup_bytes_changed` 503 |
| N7 | 换注册文件但保留旧钉定 | `trusted_startup_registration_conflict` 409 |
| N8 | 记录里的 `registration_sha256` 改为别值（不改钉定） | `trusted_startup_record_changed` 503（先在第 4 步失败） |
| N9 | 带 `VIDEO_CREATOR_DEVELOPMENT_INSTALLATION` 或 `--development-registration` 调用 | `trusted_startup_entry_denied` 403 |
| N10 | `product-serve` 别名为 `mcp` role | `trusted_startup_role_denied` 403 |
| N11 | 装配成功但调用任何管理端点（policy/budget/daily） | `production_management_unconfigured` 503；`services.registry is None` 恒真 |
| N12 | 未同意 Owner 就启动（有权威） | 落入授权页；`/projects` 403 `owner_authorization_required` |
| N13 | 运行中把某引擎文件改掉再触发制作 | writer 内 503 `trusted_startup_bytes_changed`（不静默） |
| N14 | Owner binding 到期后制作 | 403 `production_execution_identity_denied`（`production_admissions.py:176-180`） |
| N15 | 用 `owner-execution install` 走本权威 | 需要 native observer ⇒ 明确拒绝（不因权威存在而放宽） |

纪律：N11/N12/N15 是"权威不能越权"的核心三条；N12 必须证明**权威存在也不会跳过授权页**。

## 10 不做

- 不做签名/证书/TPM 形态的可信启动（无证书链，ADR0083 §7-1）；不把本卡表述为"防篡改"。
- 不做 native 宿主（Rust/held pipe/owner-protected build 仍按 ADR0036/ADR0077 另线）；本卡不实现 `observe_facts`/`NativeLaunchContext` 之外的事实源。
- 不做 management 装配的权威（policy/budget/daily 需要另一个 `for_management=True` 进程，ADR0081 §7 P1 另立卡）。
- 不做 MCP 角色准入、不做同进程解锁、不新增表/迁移、不改任何公开契约。
- 不做自动续期：Owner binding 到期即执行 403，必须 renew（产品内授权）+ 重启。

## 11 交接

- **Backend**：§9.1 五项；重点是"搬位置"的 `installation_facts`（dev/product 共用，dev 零变化）、`ProductInstallationAuthority` 的 5 个成员与保留表纪律、`product_host` 的判定顺序与清理顺序、`Entry.py` 的前缀分派。
- **集成**：启动器传 `--installation-record`/`--installation-record-sha256`；包内两处钉定与 `InstallationProvisioning.json` 同批生成（ADR0083 §5.3 升级路径）；`Engine.spec` 产出物不变。
- **测试**：§9.2（P1-P5，必须真实运行并登记 `COMMANDS.md`）与 §9.3（N1-N15，逐条断言具名码）；负例不得用 Mock 替代真实文件替换。
- **评审**：核对 §0 行号、§0.1 五项与源码一致、§2.2 判定顺序无跳步、§5.2 每行都有硬门、§6.2 矩阵四格行为、§8.2 四条边界未被措辞软化、`git diff` 未改任何生产校验。

## 12 复核清单

1. `git diff` 只含 `docs/decisions/0084-product-trusted-startup-authority.md`（如需）`docs/architecture.md`；源码/测试/契约零改动。
2. 逐条核对 §0 的行号与 HEAD 一致；特别核 `startup_services.py:74-91`、`production_admissions.py:240-247`、`main.py:428-443`、`owner_services.py:129-130`。
3. 核对 §2.2 每步都有唯一失败码，且没有"继续执行"的分支。
4. 核对 §3.2 的 5 个成员与 `production_admissions.py` 的实际调用点一一对应；确认没有多余的可选关闭。
5. 核对 §4.2 四条理由都能落到具体行号；确认 §4.1 的类型门与 `NativeOwnerServices` 字段完全匹配。
6. 核对 §5.2 九行不授予都有硬门，没有一行只靠"文档承诺"。
7. 核对 §6.2 第二行（有权威无同意）没有被任何措辞写成"可制作"。
8. 核对 §8.2 四条边界与 ADR0036/ADR0083 §7 的表述一致，且 §8.3 的 DACL 定位没有把它说成密码学防线。
