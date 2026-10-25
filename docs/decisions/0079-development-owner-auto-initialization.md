# ADR0079：开发宿主首次 Owner 自动初始化

状态：ARCHITECTURE_FROZEN_DESIGN_ONLY，2026-10-25。冻结对象协议、接受条件、审计、生产不可达性、失败语义、退役条件与影响面。**本卡只写文档**：不改源码、不改迁移、不新增数据库表、不改 `packages/contracts`、不写测试、不 commit 源码。实现已于 commit `292b615` 落地（独立评审 `docs/reviews/RV-LocalChainRealRunFixes.md`）；其中两项超出本文冻结正文的新增由 §13 追认并给出边界，**未传 `--development-auto-owner-init` 时行为仍与 ADR0077 逐字一致**（无 Owner 即 `owner_restore_refresh_required` 503）。正向主链以实测记录为准，不由本 ADR 声明通过。

用户已明确选择：**允许开发模式自动完成首次 Owner 初始化；正式产品仍必须真人确认**。本 ADR 不把该选择扩展到生产，也不提供任何"总是返回 True"的确认入口。

## 0 实读证据（本 ADR 据此冻结，非文档推断）

行号取自 2026-10-25 HEAD `562e555` 实际源码。`services/engine/src/video_creator` 简称 `vc/`。

| 事实 | 位置 |
| --- | --- |
| `change()` 只接受两种来源：`None` 走 TTY，否则必须是 `OwnerActionConfirmationSource`（§13 起另有第三个精确类型来源，见 §13.1/§13.3） | `vc/application/owner_bootstrap.py:151-182` |
| `None` 分支调用 `confirm_local_action(...)`，无注入点 | 同文件 `:168-170` |
| `confirm_local_action` 强制 stdin/stdout 都是真实 TTY 并按字输入 `AUTHORIZE <instance_id> <action>`（实现后行号 `:388-398`） | 同文件 `:340-350`（`562e555` 冻结稿） |
| `project_scope()` 要求每个 project 真实存在于 `projects` 且 `owner==owner_subject` | 同文件 `:113-121` |
| 首次初始化才允许建立 Control identity；已存在 binding 时走 restore 拒绝 | 同文件 `:184-198` |
| 事件顺序：pending 文件 → 控制面 reserve → 单事务写 metadata+commands → complete → 删 pending | 同文件 `:242-286` |
| 幂等早返回路径（同 action_key 同 request） | 同文件 `:205-217` |
| 绑定记录格式 `local-owner-binding-v1` 与字段 | 同文件 `:28-37` |
| `ManagementPrincipal.authentication_source` 目前只有两个值 | `vc/application/production_management.py:23-31` |
| 该枚举**未**出现在已发布契约：`ManagementPrincipal` 不在 `schemas.json`；带该枚举的只有 `LocalCopyInputActionReceipt`、`DailyProjectActionReceipt` 及其内嵌副本 | `packages/contracts/schemas.json` 检索结果；本 ADR §2.4 |
| dev 宿主当前在 `authority` 之后硬读 active Owner，缺失即拒 | `vc/cli/development_host.py:366-374` |
| `_active_owner` / `_expiry` 现实现 | 同文件 `:310-326` |
| factory 既有顺序（frozen→env→role→management→bundle→注册→ASR→媒体→证据→Owner→组装） | 同文件 `:329-404` |
| 三重条件与拒绝顺序（frozen、`VIDEO_CREATOR_DEVELOPMENT_INSTALLATION`、三个 dev 参数） | 同文件 `:145-151,407-438`；ADR0077 §2 |
| dev authority 的注册路径/SHA/根目录私有字段 | `vc/application/development_installation.py:187-199` |
| `DevelopmentStart` 与 argv 改写（改写后 dev 参数不再在 `sys.argv`） | `vc/cli/development_host.py:45-54,114-142,427-435` |
| 私有 token 工厂形态参考 | `vc/application/local_installation_authority.py:9-21,108-125` |
| `owner_setup_journals` 要求 preparation/accepted/goal 三段真实记录与唯一 pending 索引 | `services/engine/migrations/0010_owner_setup_journals.sql:1-41` |
| setup 建立的 Owner 必须是 `native_owner_session`，否则后续 setup 拒绝 | `vc/application/owner_setup_service.py:321-334` |
| `assemble_owner_services` 读 active binding；`for_management=False` 时 registry 为 None | `vc/application/owner_services.py:101-120` |
| 启动装配硬校验 registry/management 均为 None 且 authority 同一对象 | `vc/cli/startup_services.py:56-91` |
| 生产 `serve` 在 `install_startup_services` 之后才 `listener.bind` | `vc/cli/main.py:317-323` |
| CLI 失败只向 stderr 打印 `{"code","message"}` 并 exit 1 | `vc/cli/main.py:360-364` |
| 注册文件已声明项目范围与声明主体 | 实际 `Registration.json`：`local_registration.rights_declaration.declaring_subject='local-user'`、`project_ids=['project-f6a84…']` |
| OS 主体/设备/inode 只能由真实目录取得 | `vc/infrastructure/owner_identity.py:100-122` |

## 1 决策：修改 `change()` 增加第三来源；拒绝"伪造等价 journal"

**选定**：在 `OwnerBootstrapStore.change()` 增加第三种、显式受限的 `confirmation_source` 分支，类型为本文 §2 冻结的 `DevelopmentOwnerInitializationSource`。`None` 与 `OwnerActionConfirmationSource` 两条既有分支保持原语义与调用点不变。

**拒绝**：在 dev 宿主里直接构造 `owner_setup_journals`/`owner_setup_steps`/`commands`/`OwnerManagementControl`/secret 来"等价"一次 Owner 动作。

| 维度 | 修改 `change()`（选定） | 伪造 journal（拒绝） |
| --- | --- | --- |
| Owner 写入点数量 | 仍只有 `change()` 一个；评审可用"Owner binding 只有一个 writer"证明 | 出现第二套 writer，必须复制锁、幂等、pending、secret、控制面、目录复核；无法用单点证明 |
| journal 语义 | 完全不写 setup 表 | `owner_setup_journals` 绑定真实 preparation→accepted→goal 三段摘要、真实 draft 与 `project.create` receipt（`owner_setup_service.py:107-130,135-187`）；dev 没有 first Goal/draft，填不出真实链，只能写假历史 |
| 唯一 pending | 不受影响 | `owner_setup_one_pending`（0010:25-26）被假行占用，真实 `prepare_first_goal` 会被 `owner_setup_pending` 409 挡住 |
| 后续 setup 校验 | 不受影响 | setup 要求 binding 的 `authentication_source=='native_owner_session'`（`owner_setup_service.py:331-333`）；伪造行要么撒谎、要么让真实 setup 永久拒绝 |
| 可观察面 | 只多一个 metadata key 与一个 Control 文件 | `owner-setup status/history/abort_preparation/recover` 会把假行当真实 setup 暴露给 API/CLI |
| 失败恢复 | 沿用既有 pending/控制面恢复语义 | 需要新恢复语义，且与真实 setup 恢复冲突 |

结论：伪造 journal **不等价于一次 Owner 动作**，它把"一次受控身份写入"降级为"一行可被业务读取的假记录"。若评审认为改 `change()` 风险过大，备选是**不做自动初始化**（保持 ADR0077），而不是退化为伪造 journal。

## 2 对象协议

### 2.1 新模块与类型（仅开发路径）

```text
application/development_owner_initialization.py        (新增；dev-only)

_FACTORY = object()                                    # 私有构造 token，模块内唯一
_retained_sources: dict[int, DevelopmentOwnerInitializationSource] = {}

DEVELOPMENT_OWNER_SUBJECT = 'local-user'
DEVELOPMENT_AUTHENTICATION_SOURCE = 'development_owner_initialization'
AUDIT_METADATA_KEY = 'development_owner_initialization_audit'
AUDIT_FILENAME = 'DevelopmentOwnerInitialization.json'
AUDIT_FORMAT = 'development-owner-initialization-audit-v1'
_MAX_OWNER_LIFETIME_US = 7 * 86400_000_000             # 架构冻结常量，改值需修订本 ADR

class DevelopmentOwnerInitializationSource:
    __slots__ = (... 全部字段，见下 ...)
    def __init__(self, token, *, engine, authority, config, role,
                 registration_path, registration_sha256, resource_manifest_sha256,
                 runtime_manifest_sha256, raw_arguments, environment_value,
                 os_identity, owner_subject, project_ids, action_key, expires_at_us,
                 caller_module, pid, executable, created_at_us): ...
    # 只读属性：action_key / owner_subject / project_ids / expires_at_us
    def __repr__(self): return '<DevelopmentOwnerInitializationSource>'

def development_owner_initialization_source(*, engine, registration_path, registration_sha256,
        expires_at_us, data_dir, role, bundle, authority, config, raw_arguments) -> DevelopmentOwnerInitializationSource
def assert_development_owner_source(source, *, engine, proposal, os_identity) -> None
def write_development_owner_audit(source, *, action_id, generation, authorized_at_us,
        request_sha256, engine) -> str
def assert_development_owner_audit(engine, *, action_id, authentication_source, instance_id,
        owner_subject, project_ids, expires_at_us) -> None
```

对象不可用布尔、字典、字符串、pydantic model 或任何可序列化载体冒充：

- 构造必须传 `_FACTORY`（`if token is not _FACTORY: raise EngineError('development_owner_source_denied', …, 403)`），与 `local_installation_authority.py:13-21` 同形态；
- 构造后登记 `_retained_sources[id(self)] = self`；所有断言同时要求 `type(source) is DevelopmentOwnerInitializationSource`、`_retained_sources.get(id(source)) is source`、`source._epoch is <本次进程 epoch>`、`source._thread_id == threading.get_ident()`；
- 不实现 `model_dump`/`model_validate`/`__reduce__`，不进入任何 JSON/HTTP/MCP/argv 通道；`repr` 不泄露字段；
- `__slots__` + 无 setter，字段只在 `__init__` 写入；`__init__` 完成后覆写 `__setattr__` 拒绝任何赋值；相等性用默认对象身份。
- 保留表随进程结束消失，没有删除/复活 API；来源对象只在本次启动内有效，不缓存到下一次启动。
- `_FACTORY` 与 `local_installation_authority.py:9` 一样是**进程内约定**，不是密码学边界；真正的不可达性来自"生产入口不存在此 factory、frozen 拒绝、真实 dev authority 与注册文件实算"三者叠加（§6）。不把 `_FACTORY` 的私有性当唯一防线。

### 2.2 构造只能发生在开发宿主进程内（工厂检查顺序）

`development_owner_initialization_source(...)` 每次调用按固定顺序自检，任一不成立即具名拒绝；**不信任调用方已做的检查**：

1. `type(engine) is EngineService`；`type(role) is str and role in {'api','worker'}`；`data_dir` 为绝对、非 UNC、非 symlink/junction，且 `Path(data_dir).resolve() == Path(engine.db.data_dir).resolve()`。
2. `getattr(sys, 'frozen', False)` 必须为假，否则 `development_installation_unavailable` 503（复用 ADR0077 码；与 `development_host.py:336-338,411-414` 同义，再次核）。
3. `os.environ.get('VIDEO_CREATOR_DEVELOPMENT_INSTALLATION')` 必须逐字等于 `engine.instance_id`，否则 `development_installation_denied` 403。
4. 注册文件必须绝对、非链接、普通文件、≤1 MiB；读全文件 `hashlib.sha256` 必须等于入参 `registration_sha256`（64 小写 hex），否则 `development_registration_missing` 503 / `development_registration_changed` 503。
5. `type(config) is RegistrationConfigLocalV1`，且 `config.local_registration.rights_declaration.declaring_subject == 'local-user'`；否则 `development_owner_subject_denied` 403。
6. `type(bundle) is BundleService`、`bundle.engine is engine`、`bundle.principals.owner_subject == 'local-user'`；否则 `development_owner_subject_denied` 403。
7. `authority` 用**函数内延迟导入** `DevelopmentInstallationAuthority` 后精确校验：`type(authority) is DevelopmentInstallationAuthority`、`authority._engine is engine`、`authority._registration_sha256 == registration_sha256`、`authority._registration_path.resolve() == Path(registration_path).resolve()`、`authority._root.resolve() == Path(registration_path).resolve().parent`、`authority._closed is False`、`authority._retired is False`、`authority.connection.context.instance_id == engine.instance_id`、`authority.connection.context.role == role`、`authority.connection.context.registration_sha256 == registration_sha256`；否则 `development_owner_registration_conflict` 409。
8. `project_ids` 只取自**本次实际解析的注册配置**：`tuple(config.local_registration.rights_declaration.project_ids)`；要求非空、无重复、每项通过 `c.SourceBinding(system=item, namespace='owner-project')`，并以只读连接逐项核 `SELECT 1 FROM projects WHERE id=? AND owner='local-user'`；缺失即 `development_owner_project_required` 503（message 给出 `PrepareLocalChain.py ensure-project` 命令）。**不隐式创建项目**。
9. 有效期：单次 `engine.clock()` 取得 `now`，要求 `type(expires_at_us) is int and now < expires_at_us <= now + _MAX_OWNER_LIFETIME_US`，否则 `development_owner_expiry_invalid` 422。Owner 管理有效期就取该值（不另行放宽），因此 dev 身份（ADR0077）与 Owner binding 同时到期。
10. `raw_arguments` 必须恰为三个 dev 参数的**原文** `(('--development-registration', <text>), ('--development-registration-sha256', <text>), ('--development-expires-at', <text>))`：注册路径 `resolve()` 后必须等于 `registration_path`，SHA 文本必须逐字等于 `registration_sha256`，时间文本必须能解析为同一 `expires_at_us`；否则 `development_owner_source_denied` 403（宁拒绝不猜测）。
11. 调用栈来源：`sys._getframe(1).f_globals.get('__name__')` 必须等于 `'video_creator.cli.development_host'`，并连同 `os.getpid()`、`sys.executable` 写入对象；否则 `development_owner_source_denied` 403。该检查是名义性的，不是本 ADR 的信任根。
12. `action_key` 由工厂固定派生：`'development-owner-initialize.' + digest(engine.instance_id)`；**没有任何调用方参数**能改 action、owner、项目集合或有效期上限。

### 2.3 `change()` 内的接入点

```text
owner_bootstrap.py:151  def change(..., confirmation_source=None)   # 签名与默认值不变
168  if confirmation_source is None:                 # 原 TTY 分支，一行不改
172  elif type(confirmation_source) is DevelopmentOwnerInitializationSource:
         # 与既有 setup 分支一样，在本函数内延迟导入，顶部 import 列表零变化
         from video_creator.application.development_owner_initialization import (
             assert_development_owner_source)
         assert_development_owner_source(confirmation_source, engine=self.engine,
                                         proposal=proposal, os_identity=self.os_identity)
         authentication_source = 'development_owner_initialization'
     else:                                            # 原 setup 分支，一行不改
```

- 分支顺序保证：`None` 仍走 TTY；任何非该精确类型的对象仍进入原 `owner_setup_confirmation_denied` 403（`owner_bootstrap.py:177-180`）；只有精确类型才进入新分支。
- 延迟导入是刻意的：`owner_bootstrap.py` 顶部 import 列表保持逐行不变，生产模块的导入图不变；审计读写同样在 dev 分支内延迟导入。
- `change()` 内不出现任何 dev 环境变量、argv、HTTP 或可调用 confirmer 逻辑；dev 细节全部在 §2.1 模块。
- 在 control 锁内、既有 `_control_identity is None` 检查之前增加 dev-only 复核：`if dev_source: with engine.db.connect(): if self._read(connection) is not None: raise EngineError('development_owner_existing_denied', …, 409)`；随后 `old is None` 与 `_control_identity is None` 仍是硬条件。
- 事务内（`owner_bootstrap.py:267-280`）增加 dev-only 一步：写 metadata 审计摘要（同一事务，见 §4）；其余 metadata/commands 写入与既有 project 重核不变。
- 哈希纪律：注册文件的实算哈希只发生在工厂与 `assert_development_owner_source`（都在 control 锁外）；审计写入本身只做对象保留校验 + 创建/fsync 审计文件，不在 control 锁内重算 engine/资源哈希。若文件随后被换，后续 `observe()`/`assert_current()` 会以 `development_registration_changed` 失败，Owner binding 不因此获得执行能力。
- 幂等早返回（`:205-217`）增加 dev-only `assert_development_owner_audit(...)`，审计缺失/不符时不得静默返回成功。

### 2.4 `authentication_source` 第三值

`ManagementPrincipal.authentication_source` 追加 `'development_owner_initialization'`，成为 `Literal['native_owner_session', 'headless_administrator', 'development_owner_initialization']`。

- 这是**证明来源**所必需：复用 `'headless_administrator'` 会把"开发宿主自动写入"持久地记成"真人在 TTY 确认"，是假陈述；复用 `'native_owner_session'` 更危险（会让 setup/native 校验把 dev 绑定当作原生会话）。
- 该类型**不是已发布契约**：`packages/contracts/schemas.json` 中没有 `ManagementPrincipal`；带同一枚举的只有 `LocalCopyInputActionReceipt`、`DailyProjectActionReceipt` 及其内嵌副本，本次**不**拓宽它们（dev 拿不到 management capability，见 §6）。
- 因此 `openapi.json`、`schemas.json`、`api-client` 字节不变；评审必须用 `git diff --exit-code packages/contracts` 证明。
- 其余四个领域 model 的 `authentication_source` 字面量保持两值；若未来 dev 路径意外构造它们，会以 `ValidationError` 明确失败而不是静默记错来源。
- **已考虑并拒绝的替代**：①保留两值、把 dev 来源另存 metadata 键。这样 binding 会持久声称"真人 TTY 确认"，任何只读 binding 的代码与审计都会被误导，且额外键可被单独删除而不影响 binding，不构成来源证明。②用 `model_copy(update=...)`/`model_construct` 绕过字面量。持久记录在读取时会被 `OwnerBindingRecord.model_validate` 重新校验，直接 `owner_binding_invalid` 422。诚实来源必须落在 binding 的 `principal` 上，因此只加一个字面量是**最小且唯一诚实**的改动。

## 3 接受条件（全部满足才允许写入 Owner binding）

| # | 条件 | 实现点（预期） | 失败码 / HTTP 词表 |
| --- | --- | --- | --- |
| 1 | `action == 'initialize'`；dev 不得 renew/revoke | `assert_development_owner_source` 比对 `proposal['action']`；工厂不提供 action 参数 | `development_owner_source_denied` 403 |
| 2 | 现有实例**没有** Owner binding；有则拒绝，不静默替换 | dev 宿主只在 `_active_owner` 抛 `owner_restore_refresh_required`（无 `Control/` 的真首启）时尝试；`owner_not_initialized`（Control 在但无 binding）等其他状态原样传播、不自动初始化。`change()` 的 dev 分支在 control 锁内复核 `_control_identity is None`、`Control/` 不存在、`_read() is None` | binding 存在：`development_owner_existing_denied` 409；Control 存在/identity 已建立等非首启态：`development_owner_state_denied` 503 |
| 3 | dev 宿主三重条件全部成立：`frozen=false`、`env==instance_id`、三个 dev 参数齐全 | 工厂步骤 2/3/10 重新核；`cli/development_host.py` 既有顺序与 parser 保持 | `development_installation_unavailable` 503 / `development_installation_denied` 403 / `development_owner_source_denied` 403；参数缺失 argparse exit 2；`--development-expires-at` 非法 `development_expiry_invalid` 422 |
| 4 | dev 注册文件 SHA 与本次进程实际使用的一致 | 工厂步骤 4 重哈希文件；步骤 7 三方相等（文件实算 = `--development-registration-sha256` = `authority._registration_sha256`）；`change()` 的 `assert_development_owner_source`（control 锁外）再核 authority 存活且文件 SHA 未变 | `development_registration_missing` 503 / `development_registration_changed` 503 / `development_owner_registration_conflict` 409 |
| 5 | `owner_subject == 'local-user'`，与 `RegisteredMediaRuntime` 内部 Bundle principal 一致 | 工厂步骤 5/6：Bundle principal = 注册声明主体 = 常量；`change()` 比对 proposal | `development_owner_subject_denied` 403 |
| 6 | `project_ids` 全部真实存在且归该 owner | 工厂步骤 8 只读核；`change()` 的 `project_scope()`（`:159,113-121`）与事务内重核（`:276-278`）仍为权威 | `development_owner_project_required` 503（dev 前置）；既有 `production_management_project_denied` 403 / `owner_project_scope_invalid` 422 |
| 7 | `expires_at_us` 在有限窗口内 | 工厂步骤 9：`now < expires_at_us <= now + 7d`；Owner 有效期取同值，窗口不宽于 ADR0077 的 `min(owner, now+7d)` | `development_owner_expiry_invalid` 422 |

说明：`project_ids` 直接来自注册文件的 `rights_declaration.project_ids`，因此 Owner 范围、dev 注册 SHA 与审计三者绑定同一份输入；链式前提是该注册声明的项目已由集成的 `PrepareLocalChain.py ensure-project` 建好，dev 宿主**不**代替创建。

## 4 写入顺序与幂等

`change()` 的 dev 分支在既有控制面锁内按下列顺序执行；任何一步失败都不得留下"已成功"的假象：

1. `assert_current_directory(require_control=False)`（`_control_identity is None`）。
2. 既有 action/`action_key`/`project_scope`/有效期类型检查（不变）。
3. 构造 `proposal` 与 `request_sha`（不变）。
4. `assert_development_owner_source(...)`（§2.3）。
5. 进入 `self.control.locked()`；dev-only 复核"无 binding、无 Control identity"（§3 条件 2）。
6. 走既有 "首启" 分支：`folder.mkdir(0700)`、`inspect_owner_directory(folder)`、`old = _read()`、命令幂等查询、`initialize_new()`；确认 `old is None`。
7. 既有 `ManagementPrincipal`/`OwnerBindingRecord` 构造与 `secrets.create(...)`（`owner_bootstrap.py:248-257`，不变）。
8. **在 pending 之前写审计**：`write_development_owner_audit(...)`，`Control/DevelopmentOwnerInitialization.json` 以 `xb` 创建、写全、`flush`、`fsync`；失败即 `development_owner_audit_unwritten` 503，此时控制面未 reserve、DB 未写。
9. 写既有 `OwnerManagementPending.json`（同 `:258-263` 的 canonical 字节与 fsync）。
10. `control.reserve(revision=0, request_sha)`；不符即既有 `owner_binding_conflict` 409。
11. 单事务：dev-only 写 `metadata['development_owner_initialization_audit'] = sha256(审计文件字节)`，随后既有 `metadata['owner_management_binding']` 与 `commands` 行；再核项目归属（`:276-278`）。
12. `control.complete`、删除 pending 文件、返回 record。

崩溃窗口与恢复：

- 第 8 步后、第 9 步前崩溃：审计文件存在但 metadata 摘要不存在、无 binding、无 pending。下次 dev 尝试把审计文件**改名**为 `Control/DevelopmentOwnerInitialization.aborted-<sha256>.json`（保留证据，不删除），再按同流程重试。第 7 步已建但从未绑定的 secret 文件成为无引用死字节（任何 registry 都不会加载它），按既有 secret 生命周期保留，不构成 capability。
- 第 9–10 步后、第 11 步前崩溃：pending 文件与审计文件都属于同一 `action_id`；重试走既有 pending 恢复（`request_sha` 相同）并**复用**字节相同的审计文件与 pending 记录。
- 第 11 步后崩溃：重试走既有幂等早返回；返回前用 `assert_development_owner_audit(...)` 复核 metadata 摘要与文件内容，缺失/不符即失败，不得静默成功。
- 审计文件名固定，每个 data-dir 只允许一次成功的 dev 初始化；第二次写入只会走"已有 binding 拒绝"或幂等路径。
- 若本次走的是既有 pending 恢复分支（`:228-241`，pending 记录与 `request_sha` 相符），在校验 pending 记录之后、reserve 之前执行同一审计写入/复用；不得因为"pending 已存在"就跳过审计。

## 5 审计

### 5.1 路径与格式

- 路径：`<engine.db.data_dir>/Control/DevelopmentOwnerInitialization.json`（受保护 Control 目录，`inspect_owner_directory` 复核；与 `OwnerManagementControl.json`、`ProductionAuthorizationControl.json` 同目录）。
- 格式：UTF-8、LF、canonical JSON（`sort_keys=True, separators=(',',':'), ensure_ascii=False`）追加一个 `\n`；单对象、≤64 KiB；SHA256 取**文件全部字节**（含 `\n`）。
- 不可静默：写入失败即拒绝初始化；写成功后的摘要进入同一 SQLite 事务；dev 每次启动都复核。

### 5.2 字段（全部必填，无可选省略）

| 字段 | 值 |
| --- | --- |
| `format` | `'development-owner-initialization-audit-v1'` |
| `action` | `'initialize'` |
| `action_key` | `'development-owner-initialize.' + digest(instance_id)` |
| `instance_id` | `engine.instance_id` |
| `owner_subject` | `'local-user'` |
| `project_ids` | 注册声明并按 §3 第 6 条核实的项目列表 |
| `expires_at_us` | Owner 管理有效期（= dev 身份到期） |
| `owner_binding` | `{action_id, generation, authorized_at_us}`，来自实际写入的 record |
| `request_sha256` | 本次 `change()` 的 canonical proposal 摘要 |
| `registration` | `{path, sha256, resource_manifest_sha256, runtime_manifest_sha256}` |
| `development_arguments` | 三个 dev 参数的**原文值**（逐字，支持 `--flag value` 与 `--flag=value`；来源为改写前的 `sys.argv`） |
| `environment` | `{'VIDEO_CREATOR_DEVELOPMENT_INSTALLATION': '<instance_id 原文>'}` |
| `process` | `{role, frozen:false, pid, executable, caller_module:'video_creator.cli.development_host', thread_id}` |
| `os_identity` | `{os_subject, administrator_id, directory_device, directory_inode}` |
| `created_at_us` | 写文件时的 `engine.clock()` |

### 5.3 与 `owner_setup_journals` 的关系

- **不复用、不另建数据库表**：`owner_setup_journals` 仍是 native setup 的真实 first-Goal 日志；dev 初始化不写任何 setup 行，因此不占用 `owner_setup_one_pending`、不出现在 `owner-setup status/history`、不参与 setup 恢复。
- 审计是 Control 目录下的单文件 + SQLite metadata 摘要，二者在同一次 Owner 写入中形成：文件在事务前 fsync，摘要与 binding 在同一事务提交。
- **可被后续删除吗**：应用没有任何删除/覆盖路径；只有具备 Owner 级文件权限的操作者能手工删除。删除可被检测：metadata 摘要与 binding 的持久 `authentication_source='development_owner_initialization'` 仍在，`serve-dev`/`worker-dev` 启动即 `development_owner_audit_missing` 503（内容不符则 `development_owner_audit_changed` 409）。恢复路径是：真人 TTY `owner-init renew`（以 `headless_administrator` 覆盖来源并保留历史文件），或丢弃该 dev data-dir 重建。
- 人工 TTY `owner-init renew` 可以把来源从 dev 改成 `headless_administrator`；此后 dev 不再校验审计文件，审计文件作为历史证据保留。
- 审计里的注册 SHA 是**初始化当时**的注册。之后为每次源码编辑重生成注册文件是正常开发动作，不要求与审计 SHA 相同；Owner 范围也不会因新注册声明而自动扩展。若声明项目集合变化，只能真人 TTY `owner-init renew`。

## 6 生产不可达

1. **入口**：`serve-dev`/`worker-dev` 只存在于 `cli/development_host.py` 自己的 parser，再改写成 `serve`/`worker --workflow registered-media-bundle-v1` 转发；`cli/main.py:164-176` 的 factory 命令域不放宽，生产 `serve`/`worker`/`mcp-stdio` 分支不构造 dev factory，因而不触及本 ADR 的任何对象。
2. **无 HTTP/契约面**：本变更是启动期私有装配，没有路由、没有 OpenAPI 字段、没有请求头；`packages/contracts` 字节不变。
3. **打包产物**：wrapper 与工厂都以 `getattr(sys,'frozen',False)` 为第一道拒绝；冻结产物即使 dev 参数齐全也 `development_installation_unavailable` 503。
4. **非 dev 进程**：仅有环境变量不足；还需要由 dev 宿主在本进程内构造的真实 `DevelopmentInstallationAuthority`、注册文件实算 SHA、注册配置声明的项目与 `local-user` 主体。生产模块不得 import 新模块（§9 的 grep 断言）。
5. **不可伪装**：类型用 `type(x) is ...`；构造需要模块私有 `_FACTORY` + 保留表 + epoch + 线程 + 调用栈模块；没有 bool/dict/str/pydantic/JSON 入口。
6. **不修改 TTY 语义**：`confirm_local_action` 全函数一行不改；`confirmation_source is None` 的行为、文案、TTY 检查与 `AUTHORIZE` 挑战完全不变；生产 `owner-init` 仍必须在真实终端确认。
7. **不提供可注入 confirmer**：`change()` 签名不新增 callable、不加 `--yes`、不加环境变量开关；唯一新增分支要求精确类型。
8. **不新建宽权限开关**：环境变量只用于启用 dev 宿主（ADR0077 既有语义），不携带 owner/project/expiry/action 中任何范围；范围只来自注册文件、真实 DB 与 OS 身份。
9. **失败先于监听**：dev 初始化发生在 `install_startup_services` 内，早于 `listener.bind`（`cli/main.py:317-323`），因此不存在"先起服务再补确认"的窗口。

## 7 失败语义

启动期，不走 HTTP；dev 入口的错误经 `cli/main.py:360-364` 打印 `{"code","message"}` 到 stderr 并 **exit 1**；argparse 缺参为 **exit 2**；不会产生 HTTP 响应、不会 bind 端口、不会写 `/health`。

| 情形 | code | status_code 词表 | 可否继续 |
| --- | --- | --- | --- |
| frozen 产物 | `development_installation_unavailable` | 503 | 否 |
| 环境变量缺失/不等于 instance_id | `development_installation_denied` | 403 | 否 |
| 三个 dev 参数缺失/非法 | argparse usage / `development_expiry_invalid` | exit 2 / 422 | 否 |
| 注册文件缺失、非普通文件、链接、超限 | `development_registration_missing` | 503 | 否 |
| 注册文件 SHA 与入参不符 | `development_registration_changed` | 503 | 否 |
| 文件实算 SHA ≠ authority 在用的 SHA | `development_owner_registration_conflict` | 409 | 否 |
| 域主体不是 `local-user` 或与 Bundle/声明不符 | `development_owner_subject_denied` | 403 | 否 |
| 注册声明的项目在 DB 中不存在/不归该 owner | `development_owner_project_required` | 503 | 否；按 message 先跑 `PrepareLocalChain.py ensure-project` |
| Owner 有效期越出 `now < t <= now+7d` | `development_owner_expiry_invalid` | 422 | 否 |
| 已存在 Owner binding（含已撤销/已过期） | `development_owner_existing_denied` | 409 | 否；只能真人 TTY renew/revoke |
| Control 已存在但无 binding（`owner_not_initialized`）/ 其他非首启态 | 宿主原样 `owner_not_initialized` 503；若进入 dev 分支复核则 `development_owner_state_denied` | 503 | 否；需人工检查 |
| 来源对象类型/保留/线程/epoch/调用栈不符 | `development_owner_source_denied` | 403 | 否 |
| 审计文件写失败 | `development_owner_audit_unwritten` | 503 | 否；Owner 未写入 |
| 启动时审计文件缺失/内容不符 | `development_owner_audit_missing` / `development_owner_audit_changed` | 503 / 409 | 否；真人 renew 或重建 data-dir |
| 生产授权 floor 引导状态不允许（链接路径、授权库不可读、四表非空、新 floor 不是空首启） | `development_control_state_denied` | 503 | 否；绝不覆盖或重建既有 floor，见 §13.2 |
| 既有 `change()` 校验（项目、幂等、floor、pending、secret） | 原码不变（如 `owner_binding_conflict`、`idempotency_conflict`） | 原值 | 否 |
| 生产 TTY `owner-init` 无终端 | `owner_interactive_confirmation_required` | 403 | 否；语义不变 |

新增错误码一律**不得**加入 `RESOURCE_WAIT_CODES`，不得被 worker 当作 `resource_not_ready` park。

## 8 退役条件（Tauri 桌面弹窗可用后）

触发条件：Tauri/桌面原生宿主能提供真人可见、可审计的 Owner 确认（ADR0018/ADR0036/ADR0043 方向可编译并有真实安装记录），开发流程不再需要"无终端初始化"。

1. `cli/development_host.py` 的 Owner 门恢复为 ADR0077 行为：无 binding 即 `owner_restore_refresh_required` 503；删除自动初始化调用。
2. 删除 `application/development_owner_initialization.py`、`change()` 的 dev 分支与审计 hook、metadata key 写入；`docs/architecture.md` 与 ADR0077 交叉引用标注退役。
3. `ManagementPrincipal.authentication_source` 的第三值**先保留只读容忍**：清点所有 dev data-dir（`metadata['owner_management_binding']` 中该值），用桌面/TTY 重新初始化或丢弃 dev data-dir；确认无残留后，再单独一次变更移除该字面量（旧库届时会 `owner_binding_invalid` 422，属预期硬失败）。
4. `confirm_local_action` 与生产 `owner-init` 始终不动；`serve`/`worker`/`mcp-stdio` 无任何变更。
5. 测试把"自动初始化"正例替换为桌面/TTY 正例；`RunLocalChainE2E.ps1` 的无 Owner 跳过路径恢复为跳过。
6. Control 目录下历史 `DevelopmentOwnerInitialization*.json` 不迁移、不删除，作为开发实例历史证据随实例归档。

## 9 影响面与授权

| 文件 | 变更 | 角色 | 授权状态 |
| --- | --- | --- | --- |
| `docs/decisions/0079-development-owner-auto-initialization.md` | 新增本 ADR | 架构 | 本卡 |
| `docs/architecture.md` | 追加一段摘要与交叉引用 | 架构 | 本卡 |
| `application/development_owner_initialization.py` | 新增 dev-only 类型、工厂、审计读写（约 200 行）；§13.2 另有控制面引导函数与 `production_control_created` 审计键 | 后端 | 新文件；需后端任务卡 |
| `application/owner_bootstrap.py` | `change()` 增加一个 `elif` 分支、dev-only 复核、审计 hook（约 25 行）；`_decode`/`current`/`revocation_target`/`confirm_local_action` 一行不改 | 后端 | 原 dev 宿主卡标为禁止修改；本次用户明确授权放开，**仅限该接缝** |
| `cli/development_host.py` | Owner 门改为"读 active，缺失则构造来源并初始化，成功后重读"；保留三重条件、顺序、`NativeOwnerServices` 硬校验 | 后端 | 同上，仅限该接缝 |
| `application/production_management.py` | 仅 `ManagementPrincipal.authentication_source` 追加一个字面量 | 后端 | **不在三文件接缝内，需用户追加授权**；不加则无法诚实记录来源（见 §2.4） |
| `application/owner_services.py` | **不修改** | 后端 | 初始化发生在 `assemble_owner_services` 之前；其 `bootstrap.current()`（`:117-119`）在初始化后自然通过，`for_management=False` 的 registry=None 语义不变 |
| `tests/development/*`、`tools/testing/RunLocalChainE2E.ps1` | 更新无 Owner 预期与新增拒绝用例 | 测试 | 另立测试卡 |
| `docs/acceptance/criteria/COMMANDS.md` | 更新实测行（无 Owner 不再必然 `owner_restore_refresh_required`） | 验收 | 另交验收 |

`change()` 现有调用点（`cli/owner.py:116`、`owner_setup_service.py:473`）不改；生产 `owner-init` 仍不传 `confirmation_source`。

## 10 评审要核的具体断言

1. `git diff --name-only` 仅含 §9 列出且已授权的文件；`git diff --exit-code packages/contracts services/engine/migrations` 为空。
2. `git diff -U0 services/engine/src/video_creator/application/owner_bootstrap.py`：`confirm_local_action` 函数体无任何变更行；`change()` 的 `None` 分支与 setup 分支无变更行；新增只有 `elif type(...) is DevelopmentOwnerInitializationSource`、dev-only `_read` 复核、审计写入与事务内 metadata 写入。
3. `grep -rn "DEVELOPMENT_AUTHENTICATION_SOURCE\|development_owner_initialization" services/engine/src/video_creator` 只命中新模块、`owner_bootstrap.py`、`production_management.py`（字面量）与 `cli/development_host.py`；`cli/main.py`、`api/`、`application/production_admissions.py`、`application/owner_services.py`、native 文件均无命中。
4. `grep -rn "development_installation" services/engine/src/video_creator` 只命中 `cli/development_host.py` 与新模块的**函数内延迟导入**；新模块顶层 import 列表中不含 dev 模块。
5. `grep -rn "VIDEO_CREATOR_DEVELOPMENT_INSTALLATION" services/engine/src/video_creator` 只命中 `cli/development_host.py` 与新模块；生产入口无读取。
6. `grep -rn "lambda.*True\|always.*confirm\|--yes" services/engine/src/video_creator` 无新增确认旁路；`change()` 无 callable 参数。
7. 在无 TTY 环境跑 `python -m video_creator.cli.main owner-init …`（无 `confirmation_source`）仍得 `owner_interactive_confirmation_required` 403，且 metadata 无新增 binding。
8. 构造四类假来源：裸 `object()`、`{'action':'initialize'}` 字典、伪造的 `OwnerActionConfirmationSource` 三者必须落到原 setup 分支的 `owner_setup_confirmation_denied` 403；再用 `object.__new__` 伪造一个 `DevelopmentOwnerInitializationSource`，必须落到 dev 分支的 `development_owner_source_denied` 403（保留表/epoch/线程任一不符）。四者均不得写入 binding。
9. 在已有 active binding 的实例上跑 `serve-dev`：不写任何新记录、不写第二个审计文件；在 revoked/expired binding 上跑：`production_management_denied` 403，不尝试自动初始化；并发首启时后到进程（先读到无 binding、后在 `change()` 锁内看到 binding）得 `development_owner_existing_denied` 409，binding 字节不变。
10. `serve-dev` 首次成功后，`git diff` 无源码改动，且 `<data-dir>/Control/DevelopmentOwnerInitialization.json` 的 SHA256 等于 `metadata['development_owner_initialization_audit']`；审计字段逐项等于 §5.2 与本次命令行/注册文件/OS 身份。
11. 把审计文件改名后重启 `serve-dev`：`development_owner_audit_missing` 503；恢复后正常启动；binding 与项目不变。
12. 运行生产 `serve`（无 dev factory，设置/不设置 `VIDEO_CREATOR_DEVELOPMENT_INSTALLATION` 各一次）：行为、`/health` 无 dev 头、契约与启动日志均与改动前一致；`serve-dev` 的 `/health` 行为不变。
13. `serve-dev`/`worker-dev` 在注册文件 SHA 漂移、engine 字节漂移、资源漂移下仍分别在 `Owner` 门之前得到 ADR0077 既有码（§0.2/§6.1），不得被新的自动初始化掩盖。
14. 单元/进程级用例证明审计写入失败时 DB 中没有 `owner_management_binding` 行、没有 `owner.bootstrap.initialize` 命令行、Control floor 未被 reserve。

## 11 下游交接

- **后端**（白名单 `application/`、`cli/`）：
  - 新增 `application/development_owner_initialization.py`：`DevelopmentOwnerInitializationSource`、`_FACTORY`/`_retained_sources`、`development_owner_initialization_source(...)`、`assert_development_owner_source(...)`、`write_development_owner_audit(...)`、`assert_development_owner_audit(...)`；三常量与审计路径按 §2.1/§5。
  - 改 `application/owner_bootstrap.py`：`change()` 第三分支（§2.3）、dev-only 无 binding 复核、审计写入与事务内 metadata 摘要、幂等早返回审计复核。
  - 改 `cli/development_host.py`：`main()` 在改写 argv 前快照 `sys.argv[1:]` 并把三个 dev 参数原文传入 factory；`_factory` 的 Owner 门改为"`_active_owner` 成功则校验来源/审计并继续；仅 `owner_restore_refresh_required` 时构造来源 → `OwnerBootstrapStore.change(action='initialize', action_key=source.action_key, owner_subject=source.owner_subject, project_ids=source.project_ids, expires_at_us=source.expires_at_us, confirmation_source=source)` → 重读 binding"；其余顺序与 `NativeOwnerServices` 硬校验不变。
  - 改 `application/production_management.py`：字面量追加一值（需追加授权）。
  - 不新增表/迁移；不碰 `owner_setup_*`、`confirm_local_action`、`current()`、`revocation_target()`、`_decode()`、`cli/main.py`、`api/`、native 文件、`packages/contracts`。
- **测试**（`tests/development/`、`tools/testing/`）：正例改为"无 Owner 首启 → 自动初始化成功 → 生成注册文件 → 真实制作"；负例覆盖 §7 表全部新码、§10 第 8/9/11/14 条、并发双进程首启（后到者 `development_owner_existing_denied` 409）、审计写失败注入。不得用 mock 代替真实注册文件与真实 DB。
- **集成**（`packages/contracts`、`packaging/`、文档）：确认契约产物零字节变化；运行手册把"先 `PrepareLocalChain.py ensure-project`，再 `serve-dev` 自动初始化"写成固定顺序，并写明"自动初始化只发生一次、不会 renew/revoke、到期后必须真人 TTY"。
- **评审**：只读按 §10 断言；若发现 `change()` 既有分支出现任何非 dev-only 变更、或 `confirm_local_action`/生产入口被触碰，直接判不通过。
- **验收**：`COMMANDS.md` 的原"无 Owner → `owner_restore_refresh_required`"记录改为"未授权/已禁用自动初始化时仍为该码；首次 dev 启动成功时记录自动初始化证据与审计 SHA"；不得把 dev 自动初始化当生产或安装验收证据。

## 12 不做的事

- 不做 renew/revoke 的自动完成；不因 Owner 过期而自动重建；不替换已有/已撤销/已过期的 binding。
- 不隐式创建项目、不伪造 draft/Goal/setup 记录、不写 `owner_setup_*`。
- 不新增数据库表、不改迁移、不放宽 `private models`/契约、不改 `InstanceHealth`/OpenAPI/`schemas.json`。
- 不放宽 `confirm_local_action`、`ProductionAdmissions`、`register_execution_identity`、`install_startup_services` 或任何 native 校验。
- 不引入 bool/str/dict/环境变量/argv/HTTP 形式的"确认开关"，不提供可注入 confirmer 或 `--yes`。
- 不让 dev 绑定被当作 native/安装资格证据；不把自动初始化计入 Gate0/R1/发布/验收。

## 13 追认：实现超出冻结正文的两项（评审 P2）

实现 commit `292b615` 在本文 §2/§9 冻结对象之外新增了两项；评审 `docs/reviews/RV-LocalChainRealRunFixes.md` 将其记为越界（P2-1/P2-3/P3-8）。本节追认并冻结其边界与顺序要求，不替换 §1–§12 的任何既有条件，也不放宽任何生产校验。

### 13.1 `--development-auto-owner-init`：显式开关，默认关闭

- **位置**：`cli/development_host.py:76`（`serve-dev`）与 `:91`（`worker-dev`），`action='store_true'`；映射进 `DevelopmentStart.auto_owner_init`（`:60,153`）。
- **语义**：只有传该 flag 才允许 §2/§3 的自动初始化。不传时 `_owner_binding`（`:365-397`）只调 `store.current(allow_inactive=False)` 并核审计，失败原样抛出——无 Owner binding 仍是 `owner_restore_refresh_required` 503，与 ADR0077 逐字一致。gate 原文即 `if not start.auto_owner_init or error.code != 'owner_restore_refresh_required': raise`（`:383`）。
- **边界**：该 flag 只决定"是否尝试一次首次初始化"，不携带 owner/project/expiry/action 任何范围；不存在于 `serve`/`worker`/`mcp-stdio` 的 parser（`cli/main.py:117-161`）；不改变 §3 的 7 条接受条件、§4 写入顺序或 §7 失败码；不使能 renew/revoke。
- **为何追认而非要求改回默认启用**：ADR0079 正文把"自动初始化"当作无条件的 dev 行为，实现把它降为**显式选择**——这是收紧（默认仍是 ADR0077 的拒绝），不是放宽；同时避免"只想跑一次 dev 服务却被静默写入 Owner"的意外副作用。因此冻结为显式 flag。

### 13.2 dev 生产控制面引导：`create_development_production_control`

- **真实鸡生蛋**：`OwnerBootstrapStore` 只建 `Control/OwnerManagementControl.json`（`owner_bootstrap.py:57`，`:262` 初始化的是这个子类）；`Control/ProductionAuthorizationControl.json` 在生产里只由受认证的管理/执行动作创建（`production_authorization.py:158`、`execution_registration.py:149-154`、`local_copy_input_service.py:215`、`installation_trust_consumer.py:176`）。而 dev 装配必须传 `execution_registration`，于是 `assemble_owner_services` 在 `registered is not None` 分支用 `daily.control`（即 `authorization.control`，`daily_projects.py:232`）执行 `read()`（`owner_services.py:165-173`），floor 缺失即 `production_control_unconfigured` 503（`production_management.py:159-161`）。dev 永远不执行那些管理动作 → **owner-init 成功后仍无法启动**。
- **触发条件（全部成立才创建）**：
  1. 走 dev 入口且传 `--development-auto-owner-init`（§13.1）；
  2. 当前 Owner binding 的 `authentication_source == 'development_owner_initialization'`（`development_host.py:464-465`；TTY/生产 binding 永不触发）；
  3. `Control/ProductionAuthorizationControl.json` 不存在（存在即直接返回 `None`，永不覆盖/重建，`development_owner_initialization.py:549-550`）；
  4. 四张授权表计数全为 0：`production_authorization_policies`、`production_admissions`、`daily_project_authorizations`、`execution_registrations`（`:55-56,472-482`，只读连接）；
  5. 调用点在 `assemble_owner_services` **之前**（`development_host.py:464-473` 早于 `:474`）。
- **拒绝条件**：

  | 条件 | code | status |
  | --- | --- | --- |
  | engine 不是 `EngineService` | `development_owner_source_denied` | 403 |
  | floor 路径是 symlink/junction | `development_control_state_denied` | 503 |
  | 授权库不可读（无法证明为空） | `development_control_state_denied` | 503 |
  | 任一授权表计数 > 0（message 附 counts JSON） | `development_control_state_denied` | 503 |
  | 新建 floor 不是 `(instance, minimum_revision=0, pending=None)` | `development_control_state_denied` | 503 |
  | 审计写失败 | `development_owner_audit_unwritten` | 503 |
  | 审计已记录 `production_control_created` 但与实际 floor 不符 | `development_owner_audit_changed` | 409 |

  已有 floor 时返回 `None`：不覆盖、不重建、不补写"由 dev 创建"的审计（真实存在就如实保留；不得伪造创建记录）。
- **审计**：复用 §5 的同一份 `Control/DevelopmentOwnerInitialization.json` 与同一 metadata 摘要，追加键 `production_control_created`，记录固定为 `{created_at_us, recorded_at_us, floor: 0, path: 'Control/ProductionAuthorizationControl.json', counts: {四表: 0}}`（`:53-54,485-495,564-571`）；写入经 `_append_audit_record`（`:498-528`）：读现审计 → 追加键 → canonical 字节写 `.pending` → fsync → `os.replace` → 新摘要写 metadata（同一事务）。同键同值幂等返回同摘要；同键不同值即 409。文档仍受 64 KiB、canonical、LF 约束（`:40-44,463-469`），字段集见 §5.2（本节只追加一个键，不新增文件）。
- **顺序要求（评审 P2，后端正在修，未完成前不得声称满足）**：必须**先写审计、后建 floor**，且 floor 创建或校验失败时不得留下"已创建"的审计：
  1. 只读测四表计数（此时仍全 0）；
  2. 写"创建尝试"审计事实并 fsync（键名/字段由实现择一，例如 `production_control_pending` 或 `state:'attempted'`，语义固定为**尚未创建**）；
  3. `ProductionAuthorizationControl(path, instance_id).initialize_new()`；
  4. `read()` 复核 `(instance, minimum_revision=0, pending=None)`；
  5. 追加/翻转为 `production_control_created` 并 fsync，摘要写入 metadata。
  第 3 或第 4 步失败时：只允许存在第 2 步的"尝试"事实，**不得**出现 `production_control_created`，不得 catch 后补写成功审计。当前实现是 `initialize_new()` 之后再 `_append_audit_record()`（`:556-571`），评审已实测"floor 残留 + 审计缺 created"（`RV-LocalChainRealRunFixes.md` §P2-1/P3-8）——这是**未完成的 P2 修复**，不是已冻结行为。
- **必须函数内自检，不能只靠调用点**：评审用直接调用（无 flag、无 dev source、Control 目录已存在）复现了"先建 floor 再 `development_owner_audit_missing` 503、floor 残留"（`RV-…:31`）。冻结要求：该函数要么接收 dev 来源对象并在内部核 `type`/保留表/epoch/线程，要么至少核"本实例存在 dev 初始化审计 + 自动初始化生效位"，否则不得保持为任意调用者可调用的公开函数（可降为 `_` 私有、仅被 dev factory 调用）。归属：后端。
- **为什么不是生产放宽**：
  - 除 `initialize_new()`（与生产首启同一实现，`production_management.py:192-197`）外不写任何 command/receipt/binding；不写四张授权表；不产生 management capability（`install_startup_services:88` 仍要求 `registry is None`、`authorization.management is None`）；
  - 不改变生产 floor 的 reserve→DB commit→complete、锁序、revision 与恢复语义；
  - 只在 floor **不存在**且授权库**为空**时生效；任何已有事实的实例一律拒绝且不覆盖；
  - 创建的是"空首启 floor"，与生产在该实例上的第一次管理动作会创建的内容逐字相同（`minimum_revision=0`、`pending=None`）。
- **生产路径不可达（三重 + 补充）**：
  1. **生产 parser 无该 flag**：`--development-auto-owner-init` 只存在于 `cli/development_host.py:76,91`；`cli/main.py:117-161` 的 `serve`/`worker`/`mcp-stdio` 均无此参数，也无 `serve-dev`/`worker-dev` 命令；
  2. **非 dev 进程无调用点**：全仓 `create_development_production_control` 只有 `cli/development_host.py:40` 的 import 与 `:473` 的调用；生产模块不 import 该模块（§10 第 3/4 条的 grep 断言同样适用）；
  3. **frozen 不可用**：wrapper 与 factory 第一道 `getattr(sys,'frozen',False)` 拒绝（`development_host.py:336-338,411-414`），`development_owner_initialization_source` 在 frozen 时也拒绝（§2.2 步骤 2），因此构造不出 dev 来源 → 调用点 gate 不可能成立；
  4. **补充**：即使有人把 Control 目录搬到生产实例，函数也只在"floor 不存在 + 四表全空"时动作——那已是一个空实例，创建空 floor 与生产首启等价，不新增任何权限事实。

### 13.3 P2：`ManagementPrincipal.authentication_source` 第三值的生产可读性

- **事实**：`production_management.py:23-31` 追加 `'development_owner_initialization'`（§2.4 已批准，为诚实记录来源所必需）。其余 model 仍两值：`domain/production_authorization.py:155`（`AuthorizationActionReceipt`）、`domain/daily_project_authorization.py:157`、`domain/local_copy_input_scope.py:247`、`domain/native_execution_registration.py:193`；`domain/owner_setup.py:249` 只允许 `native_owner_session`。
- **读取现状**：`OwnerBootstrapStore._decode`（`owner_bootstrap.py:78-95`）与 `current()`（`:124-134`）**不**按来源拒绝，因此任何读到该 data-dir 的代码都会接受并看到 dev 来源的 binding；评审据此记为 P2（"生产可读取/使用 dev Owner binding"）。
- **为什么当前不是 capability 绕过（逐条）**：
  1. **写入点唯一且不可伪造**：只有 `change()` 的 dev 分支写该值（`owner_bootstrap.py:198,209,244,277`），前置是真实 `DevelopmentOwnerInitializationSource`（`_FACTORY`+保留表+epoch+线程+调用栈+真实 `DevelopmentInstallationAuthority`+注册文件实算 SHA+ADR0077 三重条件）。生产 `owner-init` 不带 `confirmation_source`，走 TTY 分支写 `headless_administrator`。
  2. **生产入口不读 binding 也能干活，读到了也不够**：生产 `serve` 不注入 installed factory，`assemble_owner_services` 不被调用、`engine.production_admissions is None` → 任何执行 `production_authorization_unconfigured` 403；Owner 管理路径虽读到 binding，但每次变更仍需 `registry.authenticate`（Owner secret 句柄）+ `confirm_local_action` 的真实 TTY 确认。
  3. **执行登记不接受 dev 来源**：`execution_registration.py:456-457` 要求安装动作的来源与 principal 逐字相等，而安装动作 receipt 只有两值（`domain/native_execution_registration.py:193`）→ dev principal 永远对不上，登记被拒。
  4. **native setup 不接受**：`owner_setup_service` 要求 `native_owner_session`（§0 已列），dev binding 进不去。
  5. 结论：第三值让 binding 的来源不再等于"真人 TTY"，但**不能**让持有该 data-dir 的一方获得超出"能读写该 data-dir 且持有 Owner secret 的本机主体"的能力。
- **残余风险与收口（需要后继收口，不得视为已关闭）**：
  a. 任何依赖"来源=真人确认"的读者必须**正向匹配**它接受的字面量，禁止"不等于其它值"的负向判断；当前只有 `owner_setup_service` 做正向匹配。新增此类读者必须显式枚举三值。
  b. `daily_projects.py:377` 与 `local_copy_input_service.py:221` 会把 principal 来源透传进两值模型，理论上对 dev principal 会 `ValidationError`；当前路径不可达（dev 拒绝 Goal 创建、execution-only 无 management capability），应以后继卡加显式拒绝代替"意外抛错"。
  c. 后继卡至少加两条断言：①生产 `serve` 在 dev data-dir 上启动后仍 `production_authorization_unconfigured`、不产生执行身份；②`owner-execution install` 对 dev binding 仍 403。
  d. 退役按 §8 第 3 条：先清点含该值的 data-dir，再移除字面量。

### 13.4 与既有章节的关系

- §3 的 7 条接受条件、§4 写入顺序、§5 审计字段（本节只追加 `production_control_created` 一个键）、§7 失败码（已补 `development_control_state_denied` 行）、§10 评审断言**全部继续有效**；§13 只追加两项新对象与一条顺序要求。
- §6 生产不可达清单追加 §13.2 末尾三条（生产 parser 无 flag、函数只有 dev 调用点、frozen 下无法构造来源）。
- §10 评审断言追加：控制面引导的顺序（先审计后 floor、失败不留"已创建"）、函数内自检、§13.3 的 ①②两条。新增码不得加入 `RESOURCE_WAIT_CODES`。
