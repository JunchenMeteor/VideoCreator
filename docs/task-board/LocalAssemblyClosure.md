# LocalAssemblyClosure

统筹任务卡，2026-10-25。依据 `docs/reviews/RV-DevelopmentHostAndLocalAssembly.md`（OPEN_P1_BLOCKED）。
两个角色并行，写不重叠路径；接口以本卡为准，不得互改对方文件。

## 缺口（评审已证）

1. `application/current_final_evidence_service.py:194-200` 与 `application/current_final_evidence_runtime.py:258-259` 写死"必须 4 个母版"，而本地静音作品按 `select_local_masters` 只有 `video`+`cover` 两个（`domain/local_bundle.py:54-71`），必被 503/422 拒在装配校验之前。
2. 当前没有任何代码写 `LocalFinalAssemblyContextV1`：`local_bundle_producer.py` 只做 `prepare_local`/`verify_local`/`publish`，而 `persist_current_final_assembly_context` 需要它。
3. `local_bundle_assembly._masters` 走 `runtime.master_assets(selection=…)`，依赖进程内 `_contexts`，跨进程恢复必 409。
4. 返回值违反 `CurrentFinalEvidenceReadSet.asr` 类型契约（会 500 而不是具名错误）。

## A. 后端角色（`application/`、`cli/`、`api/`）

- **A1 版本分派**：把两处"母版数必须 4"改为：当 manifest/assembly 是本地版本（`BundleManifestLocalV1` / `LocalFinalAssemblyContextV1`）时，要求母版集合**恰等于** `selection.master_roles`（并与此前 `intent.media_asset_ids` 逐项一致）；旧 v0.2/v0.3 仍要求 4。不得放宽旧格式，不得伪造缺失母版。
- **A2 `_masters` 去进程内依赖**：`local_bundle_assembly._masters` 只用已提交的 `media-master` Step 与 `selection.master_roles` 逐项比对（含 Asset 字节/真实解码 spec），跨进程可复用；不得要求 live held context。
- **A3 `asr` 类型契约**：`validate_local_assembly` 返回的 `asr` 必须满足 `CurrentFinalEvidenceReadSet.asr` 的声明类型（`CurrentFinalAsrRead | None`），或与调用方一起改成显式 union 并在所有访问点做判别；任何情况下不得让 `AttributeError` 泄漏成 500。
- **A4 dev 拒绝 unattended**：`cli/development_host.py` 在请求进入 production policy 分支前显式拒绝 `automation.mode != 'interactive'`，给具名 `development_mode_unsupported`（422），与 ADR0077 §7 一致。
- **A5 小修**：frozen 判断提前到 argparse 之前（ADR §2 顺序）；`worker-dev` wrapper 避免在拒绝前创建 data-dir（或明确记录该副作用并保证 exit 码正确）。
- 不改：`production_admissions.py`、`startup_services.py`、`native_installation.py`、`local_installation_authority.py`、`owner_services.py`、`media_registration.py`、`domain/contracts.py`。

## B. Agent/媒体角色（`workflows/`、`providers/`、`media/`）

- **B1 持久化装配上下文**：在 `prepare_local` 成功后、`verify_local` 之前，构造 `LocalFinalAssemblyContextV1`（binding/intent/selection/master roles/文档/媒体制品/音频映射/`asr_operation_id`）并调用 `bundle.persist_current_final_assembly_context(lease, preparation_id, context)`（入口若在 `_final_producer` 的 produce 闭包内，用其已有 `bundle` 与 `preparation_id`）。
- **B2 与 A1 对齐**：`media_artifacts` 的 roles 必须**逐个等于** `selection.master_roles` 顺序；`asr_operation_id` 当且仅当 `mixed_audio` 在母版集合内时非空；静音作品为 `None`。
- **B3 不改 A 的白名单文件**；`_masters` 的调用面若需要参数调整，由 A2 提供，Media 只消费。

## 验收（自测，真实执行）

- `ast.parse` + `ruff` 全绿。
- 后端：构造一份 2 母版本地装配（video+cover）走 `verify_current_final_evidence` 入口，必须**越过 4 母版门**并进入 `validate_local_assembly`；构造 4 母版旧格式仍按旧路径。给出实际调用与错误码。
- 后端：模拟跨进程（新对象、空 `_contexts`）调用 `_masters`，不得 409。
- 媒体：真实跑 `prepare_local` → `persist` → `verify_local` → `publish` 的组合（可用测试实例，只需到 publish 前的真实调用链），断言持久化成功后 `_read_final_assembly` 能读回同一 context。
- 两侧都**不得**伪造母版或字幕；静音作品 `audio_mappings=()`。

## 停止条件

- 若 A1 的分派需要改 `BundleManifestLocalV1` 或旧 v0.3 语义，停止回报统筹，不得自行改契约。
