# 本地链路真实运行修复独立评审（RV-LocalChainRealRunFixes）

**结论：OPEN_P1_BLOCKED。** 对“这批改动里有没有任何一处让生产路径比评审前更宽松”的直答：**有，`executor.py` 的零成本重抛没有限定 `owned_local`/无 credential/`local:` 目标，任何零成本远程 route 在驱动失败时都不再写 `unknown` 观测与 reconciliation；这是生产失败会计的放宽。** 其余：非 local 实例的 8 输出门与 V03 证据策略门逐字未变；local production 的 subset/证据跳过只由实例内的 `_local_material_plan_source`/`_development_local_registration` 触发，请求字段不能伪造（属本卡目标的本地放宽）；`ManagementPrincipal` 第三字面量让生产进程能**读取** dev 创建的 Owner binding（P2，管理命令仍需 TTY）；ADR0079 还夹带了 ADR 未冻结的 flag、`ProductionAuthorizationControl` 引导和可选审计键（P2 越界）。

固定输入：分支 `recovery/local-chain-20261025`，HEAD `5522f01`，工作树 clean；评审对象 `292b615`（engine，11 文件）与 `5522f01`（media，2 文件）；ADR0079；作者交接 `Codex/VideoCreatorImplementation/Backend/DevelopmentOwnerAutoInit/Handoff.md`、`.../AgentMedia/LocalFinalProducerBundleV04/Handoff.md`（我只把它当作者陈述，独立核源码/自跑）。我实际执行：`ast`/`ruff` 12 个改动 py（exit 0）、`git diff --exit-code packages/contracts services/engine/migrations`（空）、`pytest tests/development`（默认实例 6 passed/13 errors；干净 RegressionInstance 15 passed/2 failed/2 skipped）、owner ACL 四组反例、`Money` 20 例、`_local_material_profile` 全组合、零成本/非零成本 executor 探针、`create_development_production_control` 无审计探针、`ManagementPrincipal` 字面量探针。没有改代码、没有 commit。

## 1 逐条核验

| # | 核验点 | 结论 | 证据（file:line 与我的结果） |
| --- | --- | --- | --- |
| 1 | `owner_identity.py` 信任 `S-1-3-4` 是否只在目录 owner == 当前 SID 时生效；其他主体借 OWNER RIGHTS 获得写权限 | **PASS（P3 继承边角）** | 先核 owner：`owner_identity.py:70-71` 在 DACL 前比较 `sid_string(owner) == current_sid`，不等即 `owner_directory_denied` 403；信任集合 `:79-86`；非信任 SID 的 unsafe ACE 在 `:95-98` 仍拒绝。我的实验：①当前用户 owner + SYSTEM/Administrators/current ACL → accepted；②加 `BUILTIN\Users:(OI)(CI)F` → 403；③再加 `*S-1-3-4:(F)` 与 Users 并存 → 仍 403；④把 owner 设为 `BUILTIN\Administrators` 后加 `*S-1-3-4:(F)` → 在 `:71` 先 403。结论：OWNER RIGHTS 只在 owner（当前 SID）上生效，没有发现第三方借它获得写权限。P3：`:93` 跳过 INHERIT_ONLY ACE，继承到“由他人拥有”的子对象时 OWNER RIGHTS 会给该子对象 owner 权利；当前目录 owner-only ACL 下需要管理员先创建/改 owner（管理员本就在信任集合），不是本次新增可利用路径。 |
| 2 | `executor.py` 零成本重抛判据是否严格；非零成本是否逐字未变；零成本但有外部副作用 | **FAIL（P1）** | `executor.py:54-61` 仅判 `permit.route.max_operation_cost.units() == 0`，**未限制 source/credential/destination**。`CapabilityRoute`（`domain/contracts.py:301-326`）允许 `source='owned_remote'`、HTTPS、`max_operation_cost=Money('0')`、`verified=True`，只有 `media_diagnosis` 被强制 local；因此零成本远程 route 合法。我的探针：同一 driver 先做外部副作用再抛错——cost=0 → 原 `RuntimeError` 直接抛出，`observe_operation` **0 次**；cost=1 → 返回 `OperationObservation(status='unknown')`，`observe_operation` 1 次。`claim_operation` 已把 operation 置 `submitting`（`application/engine.py:777`），重抛后没有 unknown；若外部已受理/计费（即使 route 声明 0），账本不会进 reconciliation。非零成本分支文本未变（`:62-63` 仍是 unknown），这点 PASS。 |
| 3 | `engine.py` 的 `_local_material_profile`/`_local_skips_evidence_policy` 是否只由实例配置触发；非 local 8 输出/证据策略逐字未变；请求字段能否伪造 | **PASS（local 生产路径有意放宽，P3）** | `_local_material_profile` 只读 `engine._local_material_plan_source`/`_development_local_registration`（`engine.py:490-501`）；前者的唯一写者是 `media_registration.py:265` 的 local runtime，后者唯一写者是 `development_installation.py:201-207` 的 dev authority；没有请求/环境/argv 写点。非 local 分支 `_full_output_profile` 仍是 `set(outputs) == _OUTPUT_ROLES`（`engine.py:507-515`），V03 受理/`_evidence_execution_guard` 只在 `_local_skips_evidence_policy` 且 `delivery_requirements is None` 时跳过（`:412-424,525-530`）。我的全组合：非 local full=True、subset=False、skip=False；local full=True、subset=True、empty/dup/unknown=False、skip video=True、skip speech/full=False。结论：非 local 生产门逐字不变；local production（worker 的 `_local_material_plan_source`）确实比改动前更宽——这是 ADR0075 local 适用集的预期，但也是非 dev 生产路径的一处实际放宽，且请求不可伪造。 |
| 4 | `media_registration.py` 158 行：local decoder 根 data_dir 是否仍限实例内；held-services 去线程后跨线程复用是否仍受 lease/fence/ports/policy/注册身份约束；v2/v3 是否改语义 | **PASS（P3 读面扩大）** | local 根只在 `_initialize_local_runtime` 改为 `engine.db.data_dir`（`media_registration.py:227-236`）；`FFmpegRuntime._path` 仍 `resolve` 后拒绝 UNC/`is_relative_to(staging_root)`（`media/ffmpeg.py:49-57`），所以仍在实例内。v2/v3 分支仍用 `<data_dir>/Staging`（`media_registration.py:173`），diff 未动。held-services `:313-328` 删除线程相等，但保留 `len==1`、`execution_ports is`、`lease ==`、policy、注册/资源身份，并继续 `bound_context` + binding 比对；`_remember_current_services` 仍按 `(lease.run_id, id(services))` 记录（`:503-537`）。没有 v2/v3 语义改动。P3：decoder 根从 `Staging` 扩大到整个 `data_dir`，`Control/` 也在可读范围；当前调用方只传 Asset/受控路径，未发现请求可控路径，但 least-privilege 变宽。 |
| 5 | `domain/contracts.py` Money 字符串转 Decimal 是否精确、拒绝 float/bool/NaN/Inf/超精度；`_parse(strict=True)` 是否未改 | **PASS** | `Money.fixed_point_input`（`domain/contracts.py:46-60`）先拒 float/bool，再 `Decimal(str)`，拒 `InvalidOperation` 和非 finite；原 `Field(ge=0,max_digits=18,decimal_places=6)` 仍管超精度。我的 20 例：`'0'`,`'1.123456'`,`'0.000001'`,`'1e-6'`,`'-0'`,`' 1.0 '` accepted；`'0.0000001'`,`'1.1234567'`,`'NaN'`,`'Infinity'`,`'-Infinity'`,`'1e9999'`,`'abc'`, `Decimal NaN/Inf`, float `1.0`, bool `True/False` rejected；`Decimal('1.5')`, int accepted。`domain/local_material_production.py:209-233` 的 `_parse(..., strict=True)` 不在本 commit diff 中（`git diff --name-only` 无该文件）。 |
| 6 | ADR0079 落地：是否一致；`None`(TTY)/原 setup 分支逐字未变；生产入口/打包不可构造；审计同事务、可否被静默删除 | **PARTIAL（P2 越界与生产读取）** | **一致部分**：工厂 12 步（`development_owner_initialization.py:287-337`）、来源断言 `:348-380`、审计写/读 `:383-460,607-652`；`owner_bootstrap.change` 第三分支 `:168-182`、dev-only 无 binding 复核 `:198-218`、审计先于 pending `:277-300`、metadata 审计摘要与 binding 在同一事务 `:310-331`；`None` 分支 `:173-175`、setup 分支 `:183-194`、`confirm_local_action` 均无 diff（`git diff -U0` 无命中）。**不一致/越界**：新增 `--development-auto-owner-init`（`cli/development_host.py:73-92`）与 `create_development_production_control`（`development_owner_initialization.py:531-572`，`development_host.py:464-473`）**不在 ADR0079 §2/§9 的冻结对象中**；后者只检查 `type(engine) is EngineService`、floor 不存在、四张授权表为空，**没有检查 auto flag/dev source/audit**，我直接在临时 Engine 上调用（Control 目录已存在、无审计）→ 先创建 `ProductionAuthorizationControl.json`，再以 `development_owner_audit_missing` 503 失败，floor 残留（P2 侧效果+越界）。**生产读取**：`ManagementPrincipal.authentication_source` 增加 `'development_owner_initialization'`（`production_management.py:29-31`）；`OwnerBootstrapStore._decode`（`owner_bootstrap.py:82`）与 `current`（`:123-134`）没有拒绝该来源，生产 `serve`/其它读 binding 的路径会接受 dev 创建的 binding；`owner-execution` 仍在 `cli/owner.py:228` 调 `confirm_local_action`（TTY），management receipt 仍只能两值，所以不是完整 management 绕过，但生产可读取/使用 dev Owner binding，属 P2 放宽。**审计删除**：`_parse_audit` 先读 metadata digest（`development_owner_initialization.py:575-604`），文件缺失/不符分别 503/409；删审计不能静默成功。**审计同事务**：metadata 摘要与 binding 在同一 `db.transaction()`（`owner_bootstrap.py:310-331`），PASS。 |
| 7 | 媒体两文件：请求体 JSON 规范化是否只在唯一边界、驱动形态是否复核；`canonical_object` 是否未放宽；`input_sha` 是否同一 body | **PASS（P3 无回归）** | 唯一规范化在 `local_material_drivers.py:27-61` 的 `derivative_body`；`derivative_driver_input`（`:72-111`）在 driver 边界按 kind 严格重校验并转回 tuples；`local_material_production.py:69-83` 的 `derivative_input_sha` 用同一 `derivative_body` 结果计算 `canonical_object`，并在 `:377-387` 把同一 `body` 交给 builder；`canonical_object`（`workflows/production_json.py:10-35`）无 diff，仍拒非 JSON/超深/非有限。`clips` 改为 JSON list pairs（`local_material_production.py:427-437`），正是旧 tuple 会被 `canonical_object` 拒绝的修正；`input_sha` 与 driver body 同源。P3：无测试覆盖该边界（见 #8）。 |
| 8 | 作者自测（ast/ruff/探针/17 passed）是否可复跑；`tests/development` 是否覆盖本批 | **PARTIAL / 无回归保护** | `ast` 12 文件 OK、`ruff` 12 文件 exit 0、contracts/migrations 空 diff（我复跑）。`pytest tests/development`：默认 Integration ChainInstance → **6 passed / 13 errors**（owner-state probe 读 `ManagementPrincipal.executing_principal_id` 不存在）；按交接改用 `VIDEO_CREATOR_LOCAL_INSTANCE=...RegressionInstance` → **15 passed / 2 failed / 2 skipped**；2 failed 是 `production_code_changed`，因为 Integration `Registration.json` 只覆盖到 media commit 之前（`source-status`: changed `workflows/local_material_drivers.py`、`local_material_production.py`，declared/current 189）。作者“17 passed / 1 skipped”无法在当前 HEAD 直接复跑，需先用当前源码重生成注册（会改变 engine 哈希绑定）。`tests/development` 目录在本两个 commit 中**没有任何新增/修改**（stat 无 tests）；没有 auto-init、audit、Money、owner ACL、executor zero-cost、engine local profile、media derivative 的用例 → **无回归保护**。 |

## 2 P1

### P1-1 零成本重抛扩大到所有零成本 route，生产失败会计被放宽

- 代码：`executor.py:50-63`。判据只有 `permit.route.max_operation_cost.units() == 0`；注释写“owned-local zero-cost route”，但类型/契约没有这个保证。
- 反例：注册 `CapabilityRoute(route_id='free-remote', capability='render', source='owned_remote', destination='https://provider.example', max_operation_cost=Money(amount='0'), cost_rule_version='free-v1', verified=True)`，生产 request policy 允许该 route；driver 做外部请求后抛异常。`OperationExecutor.execute` 捕获后因 cost=0 **原样重抛**，不调用 `observe_operation`；operation 在 `engine.py:777` 已是 `submitting`，没有 `unknown` 观测、没有 `needs_reconciliation`。改动前同一 driver 会得到 `OperationObservation(status='unknown')` 并进入 reconciliation。
- 我的实测（fake engine/route，真实 `OperationExecutor`）：cost=0 → 抛 `RuntimeError`，observed=0；cost=1 → 返回 `unknown`，observed=1。
- 影响：零成本远程 route 若已发生外部受理/计费/不可撤回副作用，账本不会留下 unknown；这不是新的授权能力，但**生产失败会计比评审前宽松**，且与“无已计费风险”注释不符。修复：把重抛限定为 `route.source == 'owned_local' and route.credential_ref is None and route.destination.startswith('local:')`（或由本地 driver 显式标记），否则保留原 unknown。

## 3 P2

1. **（上轮结论；本轮修复后的实测定论见 §8.3）ADR0079 之外的 `create_development_production_control`（P2 越界/部分副作用）**：`development_owner_initialization.py:531-572`、`cli/development_host.py:464-473`。ADR0079 §9 没有该对象/flag；函数自身只查 Engine/floor 不存在/四表空，不查 auto flag、dev source、audit 或 caller。上轮实测在无审计的临时 Engine + 已存在 Control 目录调用：先创建 floor，再 `development_owner_audit_missing` 503，floor 残留。应在 ADR/任务卡追加授权并让函数自检（或只在 dev host 内置且先验审计）。
2. **`ManagementPrincipal` 第三字面量使生产读取 dev Owner binding（P2）**：`production_management.py:29-31`；`owner_bootstrap._decode:82` 与 `current:123-134` 无来源拒绝，生产 `serve`/读 binding 可接受；`owner-execution` 仍需 TTY（`cli/owner.py:228`），`AuthorizationActionReceipt` 仍两值（management 会失败），故不是完整 management 绕过，但违反“生产只接受 native/headless”的来源语义。生产应显式拒绝 `development_owner_initialization`（或只在 dev host 允许）。
3. **新增 `--development-auto-owner-init` 不在 ADR（P2/P3）**：`cli/development_host.py:73-92`；无 flag 时保持旧 `owner_restore_refresh_required`（好），但 ADR §3/§10 的自动初始化条件没有该 flag，运行手册/任务卡未冻结。若按 ADR 应默认启用，需修订 ADR；若保留 flag，需写明。
4. **审计扩展键 `production_control_created` 不在 ADR §5.2（P3）**：`development_owner_initialization.py:48-54,601-604`；旧审计仍通过，但 ADR 说字段“全部必填、无可选省略”，这是文档/契约偏差。
5. **测试与证据不可复跑/无新覆盖（P2）**：见 #8；`tests/development` 无新增，默认 6 passed/13 errors，RegressionInstance 15/2/2，author 17/1 取决于重生成注册；`local_chain_probes.py:66` 的 `executing_principal_id` 是既有工具缺陷，但会让默认 fixture 直接崩。任何“真实链路已验证”的声明都不能替代当前 HEAD 下的可复跑回归。
6. **（已由统筹更正，见 §8.5）`docs/task-board/ProductDirection.md` 与 `CurrentCapabilityInventory.md` 均为统筹提交，不是后端越界；上轮本条作废。**
7. **`ManagementPrincipal` 第三值需要用户追加授权（P3/P2）**：ADR0079 §9 明说 `production_management.py` 不在三文件接缝内、需用户追加授权；本提交只显示作者 handoff 声称追加，没有仓库内授权记录。若用户已口头授权，记录到任务卡；否则属越界。
8. **（上轮；本轮已改顺序，见 §8.3）审计/floor crash 窗口**：上轮 `create_development_production_control` 先 `control.initialize_new()` 再 `_append_audit_record`；后者失败时 floor 已创建、审计无 `production_control_created`。本轮已改为先写审计，但 floor 失败后不删除已建 floor，且 crash 窗口仍可能留下“有审计无 floor”；见 §8.3。

## 4 P3

- `owner_identity.py:93` 跳过 INHERIT_ONLY ACE（既有）——对“由他人拥有”的子对象，继承的 OWNER RIGHTS 可给该 owner 权利；需要管理员先创建/改 owner，本机未构造，安全影响有限。
- `media_registration.py:227-236` decoder 根扩到整个 `data_dir`；`FFmpegRuntime._path` 仍拒绝实例外/UNC，但 `Control/` 也在可读范围；没有找到请求可控路径，建议后续收窄到 `Objects`/`Staging`。
- `media_registration.py:313-323` 去掉 thread id 后，`values[0][3]` 仍存但不再使用；同进程任意持有 `execution_ports`/lease/policy 的线程可调用 `final_context`，边界靠对象身份+lease/fence+注册身份，不是 thread。当前 Flow 用例合理，但记录该边界变化。
- `engine.py:490-515` 的 local 标记是实例属性；任何 in-process 代码可设置 `_development_local_registration`/`_local_material_plan_source` 来放宽本地门（请求/环境不可），不是远程旁路。
- `development_installation.py:201-207` 的 `_development_local_registration` 在 dev authority 构造时设置，`close()` 不清除；dev 进程生命周期内有效，P3。
- `development_owner_initialization.py:607-652` 的 `assert_development_owner_audit` 只校验 audit 形状/绑定字段，不比较 audit 的 `os_identity` 值到当前目录（binding 的 `_decode` 另核目录），复制审计+metadata 的伪造需要 DB/Control 权限；P3。
- `Money` 接受 `' 1.0 '`/指数形式（`Decimal` 语义），属输入宽容而非精度放宽；P3 文档化。
- `local_material_drivers.py:27-61` 的 `derivative_body` 允许 `clips`/`narration_audio` 出现在任意 kind，`derivative_driver_input` 会按 kind 拒绝；hash 已包含被忽略字段的 body（driver 拒绝），无静默放过；P3。
- `local_material_production.py:69-83` `derivative_input_sha` 的 `projection` 与 `builder` body 同一对象，PASS；但没有单元测试验证“hash body == driver body”。

## 5 越界清单

| 文件/对象 | 状态 | 说明 |
| --- | --- | --- |
| `docs/task-board/ProductDirection.md`、`CurrentCapabilityInventory.md` | **非越界（已更正）** | 二者均由统筹提交，见 §8.5；上轮误记为后端越界，作废。 |
| `application/development_owner_initialization.py` 的 `create_development_production_control` | **超出 ADR0079（P2）** | ADR §2/§9 未冻结；新增 flag `--development-auto-owner-init`、控制面引导、审计可选键 `production_control_created`。作者 handoff 称追加授权，仓库无对应决定/任务卡。 |
| `application/production_management.py:29-31` | **ADR 要求追加授权（P2）** | ADR0079 §9 明确“不在三文件接缝内，需用户追加授权”；本提交有改动但无仓库内授权记录。 |
| `infrastructure/owner_identity.py:79-86` | **追加授权声明（P3）** | 用户任务/交接称追加授权；ADR0079 未列该文件。实验证明不向第三方放宽。 |
| `application/engine.py` local profile / `development_installation.py` 信号 | **超出 ADR0079（P3，运行修复）** | 属 local 0.4 运行修复，不是 ADR0079 对象；非 local 门不变，local production 有实际放宽（见 #3）。 |
| `application/media_registration.py` decoder/thread | **超出 ADR0079（P3，运行修复）** | 同上；v2/v3 语义未改。 |
| `workflows/local_material_*.py` | 媒体白名单内（PASS） | 两文件本地请求形态；未改生产/契约。 |

## 6 未覆盖项

- 真实 `serve-dev --development-auto-owner-init` + 首次 Owner + 控制面 + 本地链到 `ready`/审核/worker/成片的全链（作者 evidence 有，但当前 HEAD 注册已漂移，我未重生成注册/未跑真实 worker）。
- 生产 `serve`/`worker` 读取一个 **dev 创建的 binding** 的实际行为（`ManagementPrincipal` 接受已证，端到端未跑）；生产 `owner-execution` 仍需 TTY 已由代码确认，未实跑。
- 零成本 **远程** route 的真实 provider 受理/计费反例（我只用 fake route/driver 证明 executor 分支）。
- Windows ACL 的 INHERIT_ONLY/OBJECT ACE/父目录继承全矩阵；我只做了 owner-only、Users:F、OWNER RIGHTS、非当前 owner 四组。
- `create_development_production_control` 的审计写失败注入、floor 已存在但审计版本旧、并发首启。
- Money 的 fuzz/所有字符串语法（下划线、超长、指数边界）；`_parse(strict=True)` 全模型。
- 媒体 `derivative_body`/`derivative_driver_input`/`input_sha` 的完整 Flow 真实运行与负例；无测试。
- `tests/development` 的 17/1 需在当前 HEAD 重生成 Integration `Registration.json` 后才可复跑；未做（会改 Integration 文件）。
- 生产 contracts/API 实际启动/`/health`/OpenAPI（本提交未改 packages/contracts；未起生产 serve）。

## 7 结论边界

- **P1：executor 零成本分支**：必须收窄到 owned-local、无 credential、`local:` 目标（或本地 driver 显式标记）才能关闭；否则任何零成本远程 route 的失败不再进入 unknown/reconciliation，生产失败会计比评审前宽松。
- **P2**：ADR0079 之外的自动 flag/生产控制面引导、`ManagementPrincipal` 生产读取 dev binding、测试不可复跑/无新覆盖、production_management 追加授权记录（task-board 两项已更正为统筹提交，见 §8.4）。
- **P3**：owner ACL 继承边角、decoder 根扩大、held-services thread 边界、audit 形状/复制、Money 输入宽容、媒体 hash/body 无测试。
- **对“生产路径更宽松”的直答**：有，**一处跨 profile 的明确放宽**（`executor.py` 零成本重抛，不限于 owned-local）；**一处生产读取面**（`ManagementPrincipal` 第三值 + 无来源/审计拒绝，P2）；local production 的 8→subset/证据跳过是**按实例信号的本地放宽**（请求不可伪造，PASS 但属本地生产路径）；非 local 的 8 输出/证据门与 v2/v3 解码/门语义逐字未变。
- 本评审只读实现；没有改代码、没有提交，只写了本文件。

## 8 窄复审：P1/P2 修复（未提交工作树）

**窄复审结论：仍有 P1。** 原 `executor` 的 P1 判据已真正收窄并通过五路由实测；但 P2 的控制面顺序只做到“审计先于 floor + 异常回滚审计”，**floor 创建后失败不会删除 floor**，进程崩溃还可能留下“有审计无 floor”；按本轮验收口径“control 文件必须不存在 / 不能留有 floor 无审计或有审计无 floor”，P2 未闭合，且这条授权 floor/审计一致性问题按 P1 处理。基线：HEAD `073c748`（ADR 文档已提交）；工作树未提交 `executor.py`、`development_owner_initialization.py`；我未采信作者日志，以下均为自跑。

### 8.1 P1：`executor.py` 判据收窄——PASS

- 代码：`executor.py:22-32` 的 `_local_zero_cost_without_dispatch(route)` 四条同时成立：`route.source == 'owned_local'`、`route.credential_ref is None`、`route.destination.startswith('local:')`、`route.max_operation_cost.units() == 0`；`:64-70` 仅该函数为真时 `raise`，否则仍写 `OperationObservation(status='unknown')`。
- 我用真实 `OperationExecutor` + fake engine/route + 抛错的 driver 实测五个路由：

| 路由 | 期望 | 实际 |
| --- | --- | --- |
| `owned_local` / `local:x` / credential None / cost 0 | 原错重抛，observe 0 | `RuntimeError`，observed=0 |
| `owned_remote` / `https://example.com` / cost 0 | unknown，observe 1 | returned `unknown`，observed=1 |
| `owned_local` / `local:x` / credential `'cred'` / cost 0 | unknown | returned `unknown`，observed=1 |
| `owned_local` / `https://127.0.0.1/x` / cost 0 | unknown | returned `unknown`，observed=1 |
| `owned_remote` / cost 1 | unknown | returned `unknown`，observed=1 |

（`owned_local`+credential 用例注入了 fake vault `resolve`，否则会在 vault 处提前失败，未进入 driver 分支。）非零成本路径与其余异常处理后文本未变。**P1 闭合。**

### 8.2 P2：控制面顺序——FAIL（floor 残留 / crash 窗口）

- 当前顺序：`previous_body` 保存（`development_owner_initialization.py:567`）→ `_append_audit_record` 写 `production_control_created` 并经 `_write_audit_body` fsync 文件、写 metadata 摘要（`:498-520,523-532,575`）→ `ProductionAuthorizationControl(...).initialize_new()`（`:576-578`）→ `read()` 复核（`:579-583`）。异常时只 `_write_audit_body(previous_body)` 恢复审计+metadata（`:584-589`），**不删除已创建的 floor**。
- 我注入 `initialize_new()` 失败的实测（真实 `create_development_production_control` + 合成合法 dev 审计/空四表）：
  - **floor 文件创建前抛错**：原 `RuntimeError` 重抛；审计字节 == 原值；metadata 摘要 == 原值；`ProductionAuthorizationControl.json` **不存在**。PASS。
  - **floor 文件创建后抛错**：原 `RuntimeError` 重抛；审计字节 == 原值；metadata == 原值；但 **floor 文件存在**（`floor_exists=True`）。这正是“有 floor 无审计”；不满足“control 文件应不存在”。`initialize_new()` 的 `_install` 成功后 `read()` 失败也能产生同一状态。
  - **崩溃窗口**：审计已写 `production_control_created`、floor 尚未创建时进程被杀；下次 `create_development_production_control` 在 `:564-566` 看到审计已有该键，直接 `development_owner_audit_changed` 409，**不会补建 floor**，形成“有审计无 floor”且不可自动恢复。ADR §13.2 要求的是“attempt 审计→建 floor→created”，当前实现是“created→floor→异常回滚”，两者不等价。
- 结论：异常前 floor 的情况已修，异常后 floor/crash 未修；P2 **未通过**。应改为“attempt/未创建”状态或 floor 失败时删除 floor，且启动恢复要能识别两种中间态；在此之前不能写 P2 已闭合。

### 8.3 可达性：控制面调用点有 dev 门，函数本身仍无自检

- **dev host 调用点**：`cli/development_host.py:464-473` 只在 `start.auto_owner_init` 为真且 Owner binding 的 `authentication_source == 'development_owner_initialization'` 时调用；函数内再要求 floor 不存在、四表全空。生产 parser（`cli/main.py` 的 `serve`/`worker`/`mcp-stdio`）无 `--development-auto-owner-init`/`serve-dev`，全仓调用点只有 dev host `:473`；frozen 在 wrapper/factory 及 source 工厂先拒绝。**按文档入口，生产 `serve`/非 dev/frozen 不可达；此点 PASS。**
- **但函数仍是公开可调用**：`development_owner_initialization.py:535-589` 只查 `type(engine) is EngineService`、floor 路径、四表空、审计已存在；没有 auto flag/dev source/caller 自检。我用一个**合法的合成 dev 审计**、空四表、无 flag/无 owner source 直接调用，仍可创建 floor（先写 created 审计）。故“只在 dev 进程+flag+真实 dev 来源时可达”**只在 dev host 调用点成立，函数级不成立**；P2 残留，建议改私有/接收并断言 `DevelopmentOwnerInitializationSource`。
- **executor**：它是生产代码，不是 dev-only；可达性由 route 四条件约束，五路由已验证；非 local/零成本远程均回退 unknown，不存在进程级门，这是预期的生产代码路径。

### 8.4 更正：task-board 文件归属

- 上轮把 `docs/task-board/ProductDirection.md`（以及 `CurrentCapabilityInventory.md`）记为后端越界，**不成立**：二者由统筹提交。已在上文 P2-6 与 §5 行更正，并从越界清单移除；ADR §13（`073c748`）追认 flag/控制面引导，但 §13.2 的“attempt→floor→created”要求与当前实现仍不一致。

### 8.5 剩余 P2/P3

**P2**
1. `create_development_production_control` 异常后 floor 未删除 + crash 时“审计 created/floor 缺失”的恢复空缺（本节的 P1 结论即由此）。
2. 函数无 flag/dev source/caller 自检，仍是公开 API；生产入口不调用不等于函数不可达（in-process）。
3. `ManagementPrincipal` 第三值仍允许生产读取 dev binding（management 仍需 TTY/`AuthorizationActionReceipt` 两值；非完整绕过，但来源语义未在读取点拒绝）。
4. `tests/development` 无新覆盖；作者 17/1 依赖重生成注册，当前默认 6 passed/13 errors、RegressionInstance 15/2/2。
5. ADR §13.2 文档仍写“当前 initialize 后 append、未完成”，与工作树“append 后 initialize、回滚”不一致；文档/代码须同步。

**P3**
- `_write_audit_body` 在 metadata 写失败时审计文件已替换（跨文件事务），崩溃窗口仍可能不一致。
- `initialize_new` 后 `read()` 失败已由 after-floor 注入覆盖；建议为 floor/审计增加可重入恢复标记。
- `executor` 五路由测试是 fake engine；真实 `owned_remote` 零成本 provider 未跑。
- `owner_identity` INHERIT_ONLY 继承、decoder data_dir 读取面、held-services thread 边界仍与上一节相同。
- 媒体 hash/body 无单测；测试目录没有本批新增用例。

**窄复审最终：P1 executor 已闭合；P2 未完全闭合（floor/audit 原子性），按本轮验收口径仍有 P1。**

## 9 三相位控制面对账窄复审（未提交工作树）

**窄复审结论：PASS。** §8 的 P2“floor 失败残留/409 死路”已在当前工作树闭合为 `attempt → floor → created` 状态机；原 executor P1 仍保持闭合。我未采信作者日志，以下为自跑；未改代码、未提交。

### 9.1 三相位与正常路径

- 代码：`development_owner_initialization.py:601-709`；`_append_audit_record(attempt)` 在 `initialize_new` 前（`:678-684`），floor 成功且 `_floor_is_empty` 后写 `created`（`:685-692`）；失败时 floor 存在写 `failed_with_floor`、不存在恢复 entry 原审计（`:693-709`）；`_parse_audit` 允许并校验 attempt/created/failed 三键（`:712-735`，`:493-532`）。审计是唯一 journal，仍写 metadata 摘要（`:552-574`）。
- **正常路径实测**：`create_development_production_control(e, auto_owner_init=True)` → 审计键 `production_control_attempt` + `production_control_created`；floor 存在；`created.control_sha256 == sha256(floor bytes)`；metadata digest == sha256(audit bytes)；`_floor_is_empty` 已保证 `minimum_revision==0`；全部 True。
- **attempt 残留（审计后/floor 前崩溃）实测**：先仅写入合法 `production_control_attempt`、无 floor，再调用 → 补齐 `attempt`+`created`，floor 创建，无 409。
- **floor 后失败实测**：注入 `initialize_new` 成功创建 floor 后抛 `RuntimeError` → 审计留 `attempt`+`failed_with_floor`（无 created）、floor 存在；再次调用 → 成功 `adopt` 并补 `created`，`created.control_sha256`/metadata 均正确，**无 409**。
- **floor 前失败实测**：注入 `initialize_new` 直接抛错 → 审计字节与 metadata 摘要均恢复为进入时原值，floor 不存在，原 `RuntimeError` 重新抛出。
- **四表非空**：分别插入 `production_authorization_policies`、`production_admissions`、`daily_project_authorizations`、`execution_registrations` 各一行（admissions/execution 用 FK-off/父行辅助），每表调用两次均 `development_control_state_denied` 503；审计字节不变、floor 不存在，无写入。
- **无其他入口**：`cli/development_host.py:464-473` 只在 `start.auto_owner_init` 且 Owner binding 来源为 dev 时调用；`create_development_production_control` 自检 `sys.frozen`、`auto_owner_init is not True`、`_development_local_registration is None`（`:624-632`）；我实测无 flag、无 local 信号、frozen 分别 403/403/503，floor/审计不变。生产 `serve` 无 dev parser/flag、无调用点；frozen 产物在 source 工厂先拒绝。**文档入口层不可绕过。**
- **残留 P3**：函数仍是公开 API，自检依赖可变的 `engine._development_local_registration`（不是类型化源）；in-process 代码可设置该属性后直接调用（我正常路径测试即如此）。生产入口不调用，但函数级不是“构造不出”。

### 9.2 更正 task-board 归属

- `docs/task-board/ProductDirection.md` 与 `CurrentCapabilityInventory.md` 均为统筹提交，**不是后端越界**；§3 P2-6 与 §5 行已按统筹说明更正。`§8` 的越界结论保留为上一轮历史。

### 9.3 剩余 P2/P3

- **P3**：`failed_with_floor` 与后续 `created` 可并存（正常 adopt 路径）；审计读者必须以 created 为准，不能把 failed 当当前态。
- **P3**：`_write_audit_body` 仍先替换审计文件、后写 metadata；跨文件崩溃窗口（审计已换、metadata 未换）由 `_parse_audit` digest 检查发现，但需要人工/恢复，不是静默通过。
- **P3**：`created` 的 `control_sha256` 对旧审计可选；旧记录可被接受，但新路径均写入实际 floor SHA。
- **P3**：executor 五路由仍是 fake engine/route；真实零成本 `owned_remote` provider 未跑（判据已按四条代码收窄）。
- **P3**：本窄复审未跑 `tests/development` 全量/新增 auto-init/executor 测试，只做了上述进程内真实函数调用；测试覆盖与真实 dev host 链仍待测试角色。

