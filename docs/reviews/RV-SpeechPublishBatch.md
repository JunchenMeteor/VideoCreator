# 语音发布链与 P1 修复复验（RV-SpeechPublishBatch）

**结论：OPEN_P1_BLOCKED。** 上一轮三个 P1 中，P1-1（product approve 产生 management secret）与 P1-2（helper 信任伪造 admission）已实质修复；P1-3 **只修到“空 journal 的伪造 operation 行”**，完整伪造 journal staging/context/binding 仍可通过，我实测它接受了一条伪造转写。因而对核心问题仍然是：**有路径能让未被真实观测支撑的语音证据/作品成立**；正常 HTTP 四要素没有发现绕过。

## 0 输入与实测

- `4d71beb..HEAD`，HEAD `3f039df`；工作树干净。执行 `ruff`/AST、`tests/development` 全量 **35 passed / 1 skipped**、真实受限 app 路由/`OPTIONS`、真机 ChainInstance2 的 2 个语音 production，以及一个 **journal 全量伪造探针**（复制真实实例后在临时目录修改 transcript/staging/context）。没有改代码、没有提交。

## 1 三个必答

### 1.1 还能不能造出未经真实观测的语音证据/作品？——**能（完整 journal 伪造）**

- **空 operation 行伪造：已拒绝。** 旧 `/tmp/probe_fake_obs.py` 只插入合成 operations 行/asset，现 `_settled_observation` 调用 `_verified_journal_facts`，在 `local_evidence.py:420-587` 要求 route/完整 journal/staging/context/对象探针；该探针返回 `local_evidence_observation_unverified`。
- **伪造 `approval_json`/admission：简单伪造已拒绝。** `local_evidence_resource_manifest_hashes`（`:198-256`）已改为通过 `registry.admitted` 走 `_load`，校验 HMAC approval、registry floor、expiry/revocation；我用 `approval_json='{}'` 的合成 qualification 行得到空集/拒绝。但 `_load` 仍缺 benchmark/qualification 交叉校验（P2）。
- **完整 journal staging 伪造：仍通过。** `_verified_journal_facts` 只比对 **DB 行和本地文件的 hash**：`generated_attempts`、`staging` 文件、`asr_validation_context:*` 文件、`execution_bindings`、route 行；这些都没有 key/MAC。我的探针复制 ChainInstance2，修改 operation 的 `observation_json` + staging 的 `StoredAsrObservation` + context 的 storage/audio 路径，把 transcript 改成“伪造的转写文本”，重算 staging/context sha 和 metadata ref；`_verified_journal_facts` 返回 `ACCEPTED operation-27276b95…`（无真实 ASR 运行）。`evidence_admin_install`（`:748-…`）随即把这些 facts 用 OS-vault key 签成 policy/qualification。**P1-3 未闭合。**
- **篡改 receipt / 跨实例重放：已拒绝。** `_validated_receipt`（`:352-380`）现在要求 `session_binding` + HMAC(session_secret) over 全部字段；`evidence_admin_install` 先要求 session secret（`:748-755`），并校验 instance、issuer、authority、receipt/audit digest；跨实例 instance/issuer/key 不同。没有 secret 时 503，错签名 403。
- **伪造 receipt + 伪造 audit** 需要同 OS 写 Control/metadata/DB；这是既有 OS 边界（P2/P3），不是四要素 HTTP 绕过。

### 1.2 能不能未测量却宣称 measured？——**正常路径不能；存在 metadata 分派旁路（P2）**

- 本地 whisper 材料构造固定 `precision='not_measured'`（`local_speech_evidence.py:137-147`），quality checks 也 `not_measured`（`local_bundle_producer.py:228-232`）。
- `bundles._verify_local_v03_reports` 对“非 registered CTC”路径调用 `_assert_whisper_not_measured`（`bundles.py:3054,3116-3121`），要求 sample/P95/reference/report locator 全 None。真实 2 个语音包：`status=not_measured`、`sample_count=null`、`p95_error_us=null`、`reference_ref=null`（实测）。
- **旁路**：`_registered_initial_alignment`（`registered_alignment.py:460-468`）只检查 metadata `current_initial_alignment:<prep>` 或 `current_final_evidence_lineage:<prep>` 键是否存在，并不验证真实 CTC 源。若为一条本地 whisper preparation 添加该键，发布走 registered-CTC 分支；该分支在 `actual.alignment.precision.status == 'measured'` 时调用 `_verify_per_work_precision`，不再调用 whisper not-measured 断言（`bundles.py:3037-3105`）。这需要伪造/污染 metadata 与 measured report，故 P2 而非正常路径 P1。
- `capability_benchmark_not_performed` 只被解析为 `LocalSelfIssuedBenchmarkV1`（`evidence.py:69-80`；contracts `:1393-1400,1610-1636`），没有被读成 `capability_benchmark`；`bundles` 的 `embedded_self_issued` 与 full/reference 分派也正确。P2：`evidence._load` 不比较 qualification 的 `benchmark_report_ref` 与 loaded benchmark（`evidence.py:325-344`），伪造/混搭 signed 行可产生不一致 pair。

### 1.3 产品内授权是否仍越权？——**P1-1 已修复；无可达 management capability**

- `owner_bootstrap.py:312-320` 对 `authentication_source == product_authorization` 不再调用 `secrets.create`；`PersistentOwnerManagementRegistry.__init__`（`:381-393`）遇 product source 直接 `production_management_denied` 403。
- 我复跑 product approve：`owner_management_binding` 生成，`production_admissions`/`policies`/`execution_registrations`/`daily_project_authorizations` 均 0；没有 `OwnerSecrets` 管理凭据生成。`renew/revoke` 不在 product channel 的 `allowed_kinds`（只有 `owner_initialize`）；`change` 的 product source 也要求 action=initialize。
- 残留 P3：product principal 仍有 `scope='production.authorization.manage'`（仅历史结构/无 secret）；pending 恢复路径在 `change` 的 `self.secrets.resolve` 会因 product 无 secret 失败（fail-closed，但缺恢复）。

## 2 逐条核验

| # | 点 | 结论 | 证据与实测 |
| --- | --- | --- | --- |
| 1 | 语音证据真实性 | **P1（完整 journal 伪造）** | 上文 `_verified_journal_facts` 无 keyed journal；伪造 staging/context/transcript 被接受；空 operation/伪造 approval 已拒。 |
| 2 | not_measured/measured | **PASS（正常）；P2（dispatch）** | 真实语音包全 `not_measured`/null；`_assert_whisper_not_measured`；metadata `_registered_initial_alignment` 可把 whisper 送入 CTC measured 分支。 |
| 3 | 产品授权/管理 | **PASS（P1-1）** | 无 secret、registry 403；policy/execution 0；renew/revoke 不可由 product source 发起；P3 pending 恢复。 |
| 4 | 真实语音作品自洽 | **PASS** | `production-2f621e4e…`、`production-579acf93…` 均 succeeded + bundle published；transcript/subtitle 同源；`audio_mappings` 1 piece 6.28s；precision all null。 |
| 5 | worker 领取顺序 | **P2** | `_next_runnable_local`（`media_registration.py:922-981`）跳过策略/binding/route 不匹配；但显式 `run_id` 仍绕过、要求全部四条 route 可能跳过合法子集、跳过 stale 不进入 pending、未检查 `route.verified`。 |
| 6 | 测试覆盖 | **P2** | 35 pass/1 skip；无 local evidence/speech/worker-selection 定向测试；product auth 只有 E2E 正例。 |
| 7 | 路由/越界 | **PASS（CORS 已修）** | 受限 app 51 routes；`/projects`、`/openapi.json`、`/docs`、SSE 403；`OPTIONS` 上述路径现 403，仅 `/health` 200。文件路径均匹配角色。 |

## 3 P1

1. **完整 journal staging 可伪造**（`local_evidence.py:420-587`）：`generated_attempts`/`staging`/`asr_validation_context`/`execution_bindings` 都是无 key 的 DB 行 + 本地文件，全部可由同 OS 写者伪造并满足 hash/对象探针。我的临时实例探针以伪造 transcript（“伪造的转写文本”）通过并返回 `operation-27276b95…`。`evidence_admin_install` 会签出相应 policy/qualification。**P1-3 未闭合。**

## 4 P2

- **`registered_ctc` metadata 旁路**：`registered_alignment.py:460-468` 只查 key；可让 whisper 走 CTC measured 分支（需要伪造 metadata + measured reports）。
- **worker 选择**：显式 `run_id` 绕过 `_next_runnable_local`；四条 route 全 required 会跳过合法子集；stale skip 只打事件不入 pending；`route.verified` 未验证；无测试。
- **`evidence._load` 无 qualification/benchmark 交叉校验**：`evidence.py:325-344`；`install` 有，伪造/混搭 signed row 可绕过一致性。
- **无定向测试**：local evidence journal/helper、speech materials、worker selection、measured 旁路均无测试。
- **receipt/audit 同 OS 伪造面**：receipt HMAC 使用 launcher session secret，但 evidence-admin 从 env 读取；能读进程环境/写 Control+DB 的同 OS 文件写者可伪造（非 HTTP 四要素绕过）。

## 5 P3

- Product principal 仍保留 management scope 字段但无 secret；`change` pending 恢复的 `secrets.resolve` 会失败（fail-closed）。
- Audit 在 binding 失败时可能留下已写记录（审计先于 binding 的残留）。
- `DevRuntime` 打印含 `#a=<secret>` 的 dev-only URL。
- `_context`/speech 只支持一个 final-mix mapping piece（当前真实路径正确）。
- `local_evidence_resource_manifest_hashes` 的诊断 stderr 可能反复打印；nonsecret。

## 6 真实作品证据

| production | bundle/manifest | 证据 |
| --- | --- | --- |
| `production-2f621e4e2d9946a19d8f1d102e7e1953` | `local-bundle-revision-80ff2155…` / manifest 18,391 B `07129252…` | `Text/actual-transcript.json` 7,693 B；1 utterance；precision `not_measured` 全 null；srt/vtt 与 transcript 文本相同；`audio_mappings` 1 piece 0–6.28s；`Media/mixed-audio.wav` `a17169ac…`。 |
| `production-579acf93c3144ec188beeb85afb979a7` | `local-bundle-revision-bc6b34ea…` / manifest 18,304 B `5ec46d2d…` | 同上；transcript/subtitle 同源，precision 全 null；bundle published。 |

两个包 manifest 的 artifact SHA 与 `BundleMaterials` 实际字节一致；未重跑 API 进程抓 HTTP 字节（只读实例复核）。

## 7 测试与未覆盖

- `tests/development` **35 passed / 1 skipped**；`test_product_authorization.py` 只 E2E 正向；没有 no-secret/wrong nonce/scope/expiry/cross-instance/replay/audit-failure 的定向用例。
- 未覆盖：local evidence journal/helper 伪造、speech 真实路径、`_next_runnable_local`、measured metadata 旁路、CORS 预检、cross-instance receipt。完整 journal 探针是我自建的临时证据，不是仓库测试。

## 8 越界

- `application/local_evidence.py`、`owner_bootstrap.py`、`product_authorization.py`、`api/app.py`、`media_registration.py`：后端；`workflows/local_speech_evidence.py`/`local_bundle_producer.py`：Agent/媒体；`tools/build`：集成；`tests/development`/`tests/gate0`：测试；`docs/task-board`/`PROGRESS`：统筹。**未发现路径越界。**

## 9 最终

**OPEN_P1_BLOCKED。** P1-1/P1-2 已修复；P1-3 的 journal 事实仍是无 key 的 DB/文件，完整伪造 staging/context/transcript 可被接受并签成证据。**对核心问题的直答：有——完整伪造 journal staging 的路径仍能生成未经真实 ASR 观测支撑的自签证据；正常 HTTP 四要素和真实语音包本身没有发现“未测量却 measured”的放行。**
