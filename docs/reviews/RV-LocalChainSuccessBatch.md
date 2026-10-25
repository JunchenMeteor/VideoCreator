# 本地 0.4 首个成功作品包独立评审（RV-LocalChainSuccessBatch）

**结论：LIMITED_PASS_WITH_P2。** 对“有没有任何一处让未批准/其它 Run/篡改的输入发布出作品包”的直答：**没有发现可利用路径**。权利绑定由“当前 Run 的 quality revision + quality body 内的精确 declaration + 该 revision 的真实 approve decision”三层约束；实际成功包的 quality/rights/approval/manifest 自洽。剩余是 P2：同一 Run 的 approval 未显式写入 verifier、无权利/重入的负向回归测试、8 个 `workflows/` 文件被 engine commit 携带的角色边界，以及非 local 的 `json_body` 规范化和 API 字节未独立复核。没有 P1。

固定输入：分支 `recovery/local-chain-20261025`，评审对象 `7a32420`（父 `393c9b1`），工作树另有未提交 tests/docs（评审只看作辅助证据）。我执行：`ast`/`ruff` 12 个改动 py（exit 0）、`tests/development` 全量（RegressionInstance **34 passed / 1 skipped**）、`test_executor_zero_cost`+`test_media_derivative_request`（7 passed）、真实 assembly 的 `model_validate_json`/canonical、reentry fence 矩阵、`_publication_right` 实际/无审批/篡改/换 ref、ChainInstance2 的 manifest/object/assembly/decisions/quality 读取。没有改代码、没有提交。

## 1 逐条核验

| # | 核验点 | 结论 | 证据（file:line 与我的结果） |
| --- | --- | --- | --- |
| 1 | 权利绑定是否可伪造；未批准/其它 Run quality 能否发布；approval 与 decisions 一致性 | **PASS（P3 同 Run 未显式）** | `local_material_production.py:87-102` 从计划声明派生 rights，唯一改动是绑定本 Run quality id；`local_bundle_producer.py:438-476` 从 `composition['quality_revision']` 重读 body rights，要求 `quality_ref` 是同一 quality revision、rights 精确等于安装声明 + `approval_ref=quality id`、且存在 target 该 quality 的 approval；`:479-487` 只重绑 rights 供所有消费者。发布阶段 `bundles.py:314-348` 的 `_assert_owner_right` 再核 approval 的 decision 行：必须 `action=approve`、target 同一 revision、body SHA 一致，且 `plan_rights_body(revision.body)` 包含该 right；`approval_refs:880-890` 只收集 approve 决策。实际包：manifest rights 的 `approval_ref=autonomous.quality.run-260…`，quality body 含同一 rights，quality decision 为 approve。我的 `_publication_right` 实测：正常通过；无 approval → `local_quality_approval_missing` 409；换 target revision → 409；quality body rights 篡改 → `local_quality_rights_conflict` 409；quality_ref 换其它 revision → `local_quality_revision_conflict` 409。其它 Run：quality revision id/`read_local_composition` 均按 `autonomous.quality.<lease.run_id>` 取，当前 Run 外不可替换。P3：`_assert_owner_right` 查 decision 用 production，不要求 `approval.run_id == lease.run_id`；跨 Run 的同一 production approval 仅在能令另一 Run 等待该 quality revision 时才会被接受，当前 API/flow 未构造该路径。 |
| 2 | 装配重入是否只放宽 `authored_fence`/`manifest_created_at_us`；旧 fence > 当前、跨 run、篡改是否 422 | **PASS（P3 context fence）** | `_read_final_assembly` 改 `model_validate_json(raw)`（`current_final_evidence_recovery.py:144-151`），仍要求 `raw == canonical(context)+'\n'`、preparation/intent/binding 精确；我用真实 `assembly-995f…`（7590 B）实测入口/canonical。`_same_assembly_newer_fence`（`:269-280`）要求同类型、binding 相同且 run_id 相同、`actual.authored_fence <= lease.fencing_token`、把 fence 换成 context 后模型整体相等；我的矩阵：同 fence true、旧 fence→新 lease true、旧 fence > lease false、改 timeline false、换 run false。媒体 `_persisted_assembly_context`（`local_bundle_producer.py:421-435`）只复用保存的 `authored_fence`/`manifest_created_at_us`（manifest `:591-619`）；实际 assembly fence 3、manifest_created 1792934887645755 与 manifest 一致。P3：`_same` 只要求 persisted fence <= lease，未要求 **context.authored_fence** <= lease；context 自带更大 fence 时只要其它字段相同仍被视为同一保存体（不写新数据，但语义上应加该上限）。`_context_field_diff` 把字段值截断后写 stderr，含 rights/IDs，P3。 |
| 3 | 媒体 JSON 规范化是否只在唯一边界、canonical_object 未放宽、identity 只 str | **PASS（P3 无定向测试）** | `production_json.py:17-89` 的 `json_body` 只在边界把 BaseModel/Enum/Decimal/PurePath/tuple 归一为 JSON；`canonical_object`（`:91-`）未改；`require_body` 归一后按模型 round-trip 校验（`:28-60`）。`local_material_composition.py:26-47` 的 `ordered_media_roles` 只按 selection 顺序输出，拒缺失/多余/重复；`local_bundle_producer.py:114-131` 的 `_identity` 只接受非空 str 部分并 hash JSON list，`_selection_part`/`_bundle_revision_id` 同源。我的 7 个媒体/executor 测试通过；`_identity` 非 str/空 → `local_identity_invalid`；ordered 缺/多/重复 → `local_master_roles_invalid`。`json_body` 也用于 `creative.py`/`autonomous_production.py`/`local_render.py` 的非 local revision body（P2 影响面，见 §3）。 |
| 4 | 此前两处 P1 修复仍成立（零成本四条件、控制面三相位） | **PASS** | `executor.py:22-32` 四条件（owned_local、无 credential、`local:`、units 0），`:64-70` 仅此重抛；新增 zero-cost 测试 7 项通过。`development_owner_initialization.py` 三相位 attempt→floor→created/failed 未被 7a 修改；`tests/development` 34 passed/1 skipped（含 auto-init/executor）。无回归破坏。 |
| 5 | 越界：`7a32420` 中工作流/角色边界是否合理 | **P2（角色边界）** | `git show --stat 7a32420` 有 12 文件；其中 **8 个 `workflows/` 文件**（`local_bundle_producer`、`local_material_production`、`local_material_composition`、`local_material_plan`、`local_render`、`creative`、`autonomous_production`、`production_json`）属 Agent/Media 白名单。语义我独立核过：producer 的 rights/identity/reentry 与 `local_material_production` 的 JSON/quality rights 是正确且必要的，不是互相签字；但一个 engine commit 携带全部 8 个媒体文件，媒体 handoff 只确认 producer 保留，其它 7 个没有独立媒体 co-review/ownership 记录。 |
| 6 | 测试与证据是否覆盖新行为 | **P2（无定向回归）** | 全量 `tests/development` 在 RegressionInstance 34 passed/1 skipped；新增 `test_acceptance_dispatch`/`test_development_owner_auto_init`/`test_executor_zero_cost`/`test_media_derivative_request` 有效。`grep -R` 对 `publication_right`/`_same_assembly_newer_fence`/`authored_fence`/`ordered_media_roles`/`_identity` 在 tests/development **无命中**；E2E 成功只覆盖正例。且新增测试是未跟踪/未提交工作树文件，commit 7a 本身无 tests。 |
| 7 | 真实产物复核 | **PASS（API 未独立）** | ChainInstance2：production `production-1d2233…` / run `run-260d0e…` succeeded；manifest `manifest-local-bundle-revision-e362c12a…` 12689 B，SHA-256 `148349d50f1fecb4559c2b85cdb7e2191176278ed7ad7d1e2b86ef2d10c0b7d6` 与 DB `manifest_sha256` 相同；`Media/video.mp4` artifact sha `ae433171…` size 8316，Objects 同 sha 同 8316；ffprobe：h264 1080×1920 25/1 3.000s 75 帧。`current_final_assembly:preparation-304…` ref `995f5405…` size 7590，`CurrentFinalAssemblies/assembly-995f…` 同 SHA/字节，`model_validate_json` 可读且 canonical 精确；assembly fence 3、manifest_created 1792934887645755 与 manifest 一致；quality revision body rights 与 manifest rights、approve decision SHA 一致。API 进程未重跑，因此“API 返回字节一致”只由 manifest/object 关系复核，未独立抓 HTTP。 |

## 2 P1

**无。** 未发现未批准 quality、其它 Run quality、篡改 rights/approval 或伪造 manifest 能穿过 `_publication_right` + `_assert_owner_right` + 真实 decision 的三层门；实际成功包也自洽。

## 3 P2

1. **approval 未显式绑定同一 Run**：`_assert_owner_right`（`bundles.py:314-348`）只按 production 查 decision，不要求 `approval.run_id == lease.run_id`。当前 quality id 按 Run 生成、API 的 `submit_decision` 又要求目标等于该 Run 的 waiting revision，所以没有演示出跨 Run 路径；但作为负向断言应在 verifier 加同 Run 校验。
2. **回归测试**：权利绑定、`_same_assembly_newer_fence`、`ordered_media_roles`、`_identity` 没有直接用例；E2E 成功是正例，负例（无审批/换 quality/跨 Run/篡改 fence/非 str identity）未覆盖；34 passed 不能替代这些边界。新增测试文件还未提交。
3. **角色边界**：`7a32420` 的 8 个 `workflows/` 文件由一个 engine/media commit 携带；producer 与 rights 语义我核过正确，但其它 7 个文件没有媒体角色的独立 co-review/ownership 记录，应补归属或拆分提交。
4. **非 local 规范化**：`json_body` 被加到 `creative.py`/`autonomous_production.py`/`local_render.py` 的 revision body；对 JSON-native 输入应恒等，但 Decimal/Path/tuple 会改变规范字节/revision SHA。没有全量非 local 回归，属跨 profile 影响面。
5. **真实 API 字节**：我只复核 manifest/object/assembly/ffprobe，未起 API 进程抓 `GET` 字节；用户所述 API 一致性仍需 HTTP 证据。

## 4 P3

- `_same_assembly_newer_fence` 未限制 `context.authored_fence <= lease`（只限制 persisted actual），不写新数据但语义应收紧。
- `_context_field_diff` 把差异字段值（截断 120 字符）写 stderr，可能含 rights/ID；本地诊断可接受。
- `_publication_right` 只检查存在 target quality 的 approval，不单独校验 decision action；当前 `approval_refs` 只收 approve，且最终 `_assert_owner_right` 复核；未来复用该函数需保留后置门。
- `_identity()` 无参数会抛 TypeError 而非 `local_identity_invalid`（调用点总带 prefix）；P3。
- `json_body` 把 `PurePath` 转成本机路径字符串，进入 revision body 可能泄露绝对路径；本地文档。
- `media_registration._stale_registration_binding`（`:338-374`）只把“仅 registration SHA 不同”的旧 binding 判为 stale 并 `needs_reconciliation`，没有自动重绑；这是正确 fail-closed，但真实运行会产生多个 reconciliation 记录（本次实例可见）。

## 5 越界清单

| 文件/对象 | 状态 | 说明 |
| --- | --- | --- |
| `workflows/local_bundle_producer.py` | 语义 PASS / 角色 P2 | 后端 commit 修改；媒体后来确认保留；rights/identity/reentry 经独立核验正确，但归属仍应记录媒体 co-review。 |
| `workflows/local_material_production.py`、`local_material_composition.py`、`local_material_plan.py`、`local_render.py`、`creative.py`、`autonomous_production.py`、`production_json.py` | 角色 P2 | 同 commit 的其它 7 个 Agent/Media 文件；语义属于 JSON 规范化/本地成功链，但没有在 commit 中体现媒体 owner。 |
| `application/*`（recovery/assembly/media_registration）、`cli/development_host.py` | 后端白名单内 | 权利/重入/控制面/registration 修复。 |
| `tests/development/*` 新增 | 未提交、非 commit 内容 | 只作本地证据，不能算 commit 回归保护。 |

## 6 未覆盖项

- **真实 HTTP API 字节**未抓；只核了 manifest artifact 与 Objects 同 SHA/size、ffprobe 规格。
- **跨 Run approval**、**context fence > 当前**、**非 local json_body 变更后的旧 revision 重放**没有真实负例。
- 权利绑定的 **API 决策路径**（人类/测试 harness 提交 approve）未重跑；实际 decision 行存在且为 approve。
- `tests/development` 的权利/重入/ordered/identity 定向测试不存在；未补。
- 未跑生产 `serve`/`worker` 的另一注册/旧 Run 恢复矩阵；本批只核 local 成功包。

## 7 结论

- **对关键问题的回答：没有发现“未批准/其它 Run/篡改输入”能发布作品包的路径。** 权利声明、quality 版本、真实 approve decision、manifest 与 assembly 在代码和实际成功包上闭合。
- **结论 LIMITED_PASS_WITH_P2**：功能成功与安全门 PASS；P2 为同 Run approval 断言、负向测试、8 个 workflows 的角色边界、非 local JSON 影响面、API 字节独立证据。
- 本评审只读实现；没有改代码、没有提交，只写了本文件。
