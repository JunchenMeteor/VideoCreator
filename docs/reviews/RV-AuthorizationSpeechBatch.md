# 产品内授权 / 本地自签证据 / 语音路径独立评审（RV-AuthorizationSpeechBatch）

**结论：OPEN_P1_BLOCKED。** 用户在受限通道的四要素、路由隔离、签名/HMAC 与语音材料构造上多数成立；但发现三处 P1：

1. **Owner 产品授权并不是“只写有范围 binding、绝不产生 management capability”**：`approve('owner_initialize')` 走 `change('initialize')`，实际写入 `ManagementPrincipal(scope='production.authorization.manage', authentication_source='product_authorization', authentication_binding_id=...)`，并在 `OwnerSecretStore.create()` 中生成 48 字节 OS-vault 管理 secret（`owner_bootstrap.py:312-317`，`infrastructure/owner_secret.py:29-50`）。policy/execution identity/admissions 确实为 0，但 management principal + 管理凭据已产生，与 ADR0081 的硬声明不符。
2. **自签 evidence helper 会接受伪造的 `metadata` + `alignment_admissions` 行**：`local_evidence_resource_manifest_hashes()`（`local_evidence.py:185-225`）只校验记录字段、issuer 前缀、qualification body 的 content/execution identity，并不检查 `approval_json`、HMAC 签名或 evidence registry。我用 `approval_json='{}'`、`benchmark_json='{}'` 的合成 qualification 行，helper 直接返回了资源 manifest sha。
3. **没有真实 settled ASR 观测也能装**：`_settled_observation()`（`local_evidence.py:346-408`）只要求 operations 行 `status='succeeded' AND settled=1`、result_json 的形状、audio asset 存在；不校验 ASR route/capability、driver、真实资源或执行身份是否由本次 ASR 产生。我插入一条合成 operation + asset（无真实 ASR），helper 接受了 `op` 并返回完整 facts；`evidence_admin_install` 会把这些 facts 用 OS-vault key 签成 policy/qualification。

## 0 固定输入与方法

- 分支 `recovery/local-chain-20261025`，范围 `4d71beb..HEAD`（HEAD `62bfc16`）；工作树干净。
- 我执行：`ruff`/AST 6 个改动 py（通过）、`tests/development` 全量 **35 passed / 1 skipped**、受限 app 的 51 条路由枚举与真实 TestClient 请求、授权/四条负例/过期/重放、审计失败、真实 assembly 入口、合成 operation/admission 的 helper 探针、真实 ChainInstance2 产物只读读取。没有改代码、没有提交。

## 1 逐条核验

| # | 核验点 | 结论 | 证据（file:line 与实测） |
| --- | --- | --- | --- |
| 1 | 没有 secret、错 nonce、错 scope、跨实例、过期、重放、错 Origin 是否拒绝；approve 是否只写 binding | **P1（management），其余 PASS** | `approve`：`product_authorization.py:937-982`；`_assert_caller` 验 secret/Origin/fetch-site（`:898-909`），`_assert_identity` 验 instance/generation（`:911-916`），`_assert_decision_credentials` compare_digest nonce + 重算 scope hash（`:918-931`）；过期 `_expire_if_stale`（`:933-935`）；applied 重放同 decision 返回、不同 scope 拒绝（`:943-952`）。我的实测：无 secret/错 secret `authorization_session_denied` 403；错 Origin/fetch-site `origin_denied` 403；错 nonce `authorization_nonce_denied` 403；错 scope `authorization_conflict` 409；错实例/ generation `authorization_instance_conflict` 409；过期 `authorization_expired` 409；重放返回同一 view。**但** Owner approve 调用 `owner_bootstrap.change(action='initialize')`，在 `owner_bootstrap.py:312-317` 构造 `ManagementPrincipal(scope='production.authorization.manage')` 并 `self.secrets.create(...)`；`owner_secret.py:29-50` 向 OS vault 写入 48-byte 管理 secret。policy/admissions/execution 表仍为 0（我的实测），所以“无执行身份/policy”成立，“无 management capability”不成立。 |
| 2 | 受限进程除 `/health` 与 `/authorization/*` 外是否还有路径可达（全部路由枚举） | **PASS（HTTP 数据面）；P2（CORS 预检）** | `api/app.py:137-149` 的 middleware 只放行精确 `/api/v1/health` 和以 `/api/v1/authorization/` 开头的 path。我用真实 app 枚举 51 条路由并逐条请求：`/health` 200；`/projects`、`/openapi.json`、`/docs`、`/redoc`、`/runs/x/events` 全部 403 `owner_authorization_required`；`/authorization` 403；`/health/` 403；`/authorization/pending` 可达（空实例无 project 时 503）；授权 POST 可达；无 WS/static 路由。**但** CORS middleware 在受限 middleware 外层，`OPTIONS /api/v1/projects` 与 `OPTIONS /openapi.json` 对白名单 Origin 返回 200（无 body），不符合“只有两条路径”的字面约束；这是无数据/无动作的 P2，非 P1。 |
| 3 | 自签证据是否可伪造；无真实 settled ASR 能否装；execution identity/resource sha 是否可配置/请求/环境注入；伪造 metadata/admissions 是否被丢弃；not_performed 是否会被当作 capability_benchmark | **P1（helper/fake operation）** | key 只来自 OS vault（`local_evidence.py:137-156`），`_rooted_registry` 用 key 作 HMAC root（`:159-163`），签名 `_sign`/`EvidenceApproval`（`:429-440`），`PersistentEvidenceRegistry.install/_load` 验 HMAC（`evidence.py:110-168,325-344`）；resource manifest sha 不从 config/argv/env/request 读取（`local_evidence.py:185-225`）——**但** helper 只查 `metadata` + `alignment_admissions` 的外形，不验 `approval_json`/签名（我用 `approval_json='{}'` 的合成行通过，返回虚假 sha）；`_settled_observation` 只查 operations 行的 settled/succeeded + result 形状（`:346-408`），不验 ASR route/driver/资源，我插入合成 operation（无真实 ASR）/asset 后返回 `op`。因此真实观测与签署链可被 DB 行伪造；`evidence_admin_install` 随后会用 key 签 `facts.execution_identity`（`:535-678`），并把虚假 manifest 写入 `local_evidence_resource_manifest`。`capability_benchmark_not_performed` 在 `_validated_benchmark` 中明确走 `LocalSelfIssuedBenchmarkV1`，不会当 `capability_benchmark`（`evidence.py:69-80`；contracts `:1393-1400,1610-1636`），该点 PASS；`_load` 仍未交叉校验 qualification 的 `benchmark_report_ref` 与 benchmark 身份（P2）。 |
| 4 | HMAC 密钥来源、scope/绑定、篡改签名、跨实例复用 | **PASS（helper 旁路除外）** | key identifier = `local-evidence-issuer-<instance>`（`local_evidence.py:133-145`），OS vault `CredentialVault`；每个 instance 独立，receipt 检查 instance/issuer/authority（`:535-593`）；approval 签名覆盖 issuer/approval_id/document_sha/benchmark_sha（`:429-440`），`PersistentEvidenceRegistry._signature` 用 trust root + `hmac.compare_digest`（`evidence.py:110-116`），篡改会 403；`install` 检查 approval/document/benchmark 绑定（`:139-151`）。`local_evidence_resource_manifest_hashes` 绕过 registry 是 §3 的 P1；`evidence-admin` 在 key 缺失时 `create=True` 生成（`:588`），没有产品 session secret，属于同 OS 用户的 P2。 |
| 5 | 语音路径诚实性：precision 恒定、字幕/转写同源、audio_mappings 逐 piece、asr_operation_id 可否伪造/为空、CTC lineage | **PASS（材料构造）；P1 在证据入口** | `run_local_asr` 只接受 owned_local/transcription/无 credential/0 cost/local: 路由，settled succeeded operation，actual result/driver context、input/duration、execution identity（`local_speech_evidence.py:46-100`）；alignment 恒 `precision='not_measured'`、`units='utterance'`（`:137-147`）；字幕由同一 transcript/alignment 用 `serialize_subtitles` 生成并逐 cue 校验文本/ID（`:168-187`）；`audio_mappings` 从实际 mixed/video tracks/decoded samples 生成单个最终 mix piece（`:149-167`），没有伪造多 piece；`asr_operation_id` 来自 `operation['id']`，`require_settled` 拒空（`:33-43,200-205`）；没有 CTC 字段/lineage。**但** `_settled_observation` 对合成 operation 的接受（§3/P1）意味着证据侧仍可能把不真实观测签成 qualification；语音材料本身不写 CTC。 |
| 6 | 审计：approve/deny 是否都写、审计先于状态、写失败 503 无副作用 | **PASS（P3 边角）** | `approve` owner 走 `change`，`write_product_authorization_audit` 在 pending/binding 写入前（`owner_bootstrap.py:299-332`），审计文件 + metadata digest；`deny` 先 `write_product_denial_audit` 再改 state（`product_authorization.py:1053-1065`）；local evidence `_approve_local_evidence` 先 `_install_audit_file` + `_commit_audit_digest`，再 `finalize_receipt`（`:1020-1033`）。我注入 `_install_audit_file` 失败：approve 抛 `authorization_audit_unwritten` 503，`owner_management_binding`/`commands`/audit metadata 均 0。P3：owner binding 写失败会留下已写审计；local evidence `prepare_receipt` 在审计前写 `.pending`，失败/崩溃依赖 discard 恢复。 |
| 7 | 新枚举是否只在自签 bench 出现；`evidence.py install/_load` 是否可能把未执行读成已执行 | **PASS（dispatch）；P2（_load 交叉校验）** | `_validated_benchmark` 按 `evaluation_scope` 选 `LocalSelfIssuedBenchmarkV1`，`validate_self_issued_benchmark` 固定 not_performed/`not_measured`/local authority；full `MethodBenchmarkReport` 仍走 `validate_benchmark`（`evidence.py:49-80`）。`bundles.py` 的 `benchmark_models`/`benchmark_types` 将 `embedded_self_issued` 与 full/reference 分开，strict reference 拒自签（`:2727-2770,3012-3030`）；导入路径同样。未执行基准不会被读成 capability_benchmark；但 `_load` 只验 approval 与 document/benchmark，不比较 `qualification.benchmark_report_ref` 与 loaded benchmark 的 report/identity（`evidence.py:325-344`），伪造/混搭 signed row 可产生不一致的 resolved pair（P2）。 |
| 8 | 测试覆盖 | **P2（无定向回归）** | `tests/development` **35 passed / 1 skipped**；`test_product_authorization.py` 只覆盖 restricted→pending→approve→restart 正例；`grep` 未发现 no-secret/wrong nonce/wrong scope/cross-instance/expired/replay/audit-failure 的定向用例；`local_evidence`、`local_speech_evidence`、`evidence-admin`、not_performed/伪造 admission、CORS 预检均无测试。 |

## 2 P1（阻断）

1. **`approve('owner_initialize')` 产生 management capability**：`owner_bootstrap.py:312-317` 写 `ManagementPrincipal(scope='production.authorization.manage', authentication_source='product_authorization', authentication_binding_id=...)`，`owner_secret.py:29-50` 实际生成 OS-vault 48-byte 管理 secret。ADR0081 `product_authorization.py:661-668` 注释/ADR“无 management capability”不成立。我的实测 `production_admissions`/`policies`/`execution_registrations` 均 0，但 `owner_management_binding` 与管理 secret 已存在；这不是“只写有范围 binding”。
2. **自签 helper 信任伪造的 metadata/admissions**：`local_evidence.py:185-225` 的 `local_evidence_resource_manifest_hashes()` 不验 `approval_json`/HMAC/registry；我用 `approval_json='{}'`、`benchmark_json='{}'` 的合成 qualification 行，helper 返回虚假 `resource_manifest_sha256`。该值进入 worker `TrustedBundleValidators.resource_manifest_hashes`，可让伪造资源 manifest 通过发布校验。
3. **无真实 ASR 观测可装**：`local_evidence.py:346-408` 仅凭合成的 `operations` 行（status=succeeded, settled=1, result_json 形状）+ asset，就返回 facts/`op`；没有校验 ASR route、driver、真实资源或执行身份来源。`evidence_admin_install` 随后用 OS-vault key 签这些 facts（`:535-678`），所以“未被真实观测支撑”的 policy/qualification 可以安装；若再取得合法 local-evidence policy 授权/receipt，可生成自签语音证据。

## 3 P2

1. **受限模式 CORS 预检泄漏**：`api/app.py:137-149` 的 middleware 在 `CORSMiddleware`（`:150`）内层；实测 `OPTIONS /api/v1/projects`、`OPTIONS /openapi.json` 对白名单 Origin 返回 200。无数据/动作，但违反“只有 `/health` 与 `/authorization/*` 可达”的字面 ADR 约束。
2. **local-evidence receipt 不可认证**：`_validated_receipt`（`local_evidence.py:285-315`）只校验 canonical JSON 形状/scope/audit_sha；receipt 本身无 HMAC。`evidence-admin` 无 session secret，仅凭 receipt + `Control/LocalEvidenceAuthorization.json` + metadata digest；能读/写同目录的进程可伪造 receipt（同 OS 边界内）。审计 digest 提供了弱绑定，但不是产品会话凭据。
3. **`_load` 缺 benchmark/qualification 交叉校验**：`evidence.py:325-344` 未比较 `document.benchmark_report_ref` 与 loaded `benchmark.report_id/content_sha256/execution_identity`；`install` 有校验（`:139-151`），直接伪造/混搭的 admissions 行可绕过该一致性（P2，需 DB/签名条件）。
4. **测试缺口**：§1#8；`test_product_authorization` 仅正例；无 local evidence/speech 测试；0 覆盖错误 nonce/scope/过期/跨实例/重放/审计失败/CORS。
5. **`local_evidence_resource_manifest_hashes` 不验签名**是 P1 #2 的实现根因；应改为经 registry 验签/读取 `approval_json` 后再返回。
6. **receipt 的 `install_by_us`/origin/fingerprints** 只做形状校验，不证明 receipt 确由批准进程签发；P2。

## 4 P3

- `_approve_local_evidence` 在审计前 `prepare_receipt` 写 `.pending`；审计失败会 discard，但进程崩溃留下 pending 需要恢复。
- owner binding 写失败可能在审计文件留下 deny/approve 记录（审计先于 binding 的必然残留）；应有恢复标记。
- `_context`/speech 的 `audio_mappings` 目前只支持一个 final-mix piece（实际最终混音路径正确）；多 piece 场景未实现。
- `local_evidence.load_local_evidence_key(create=True)` 在 evidence-admin 中可首次创建 key；没有独立产品确认，只靠 receipt/audit；同 OS 用户 P3。
- `DevRuntime.mjs` 打印 `authorization_url`（含 fragment secret）到 stdout；明确 dev-only，但日志保留面 P3。
- `evidence.py._load` 的 benchmark 混搭风险（P2 边界）在真实 install 路径被 `install` 拦截，非正常 API 可达。

## 5 越界清单

| 文件/路径 | 归属 | 结论 |
| --- | --- | --- |
| `application/product_authorization.py`、`local_evidence.py`、`evidence.py`、`bundles.py`、`api/app.py`、`cli/main.py`、`infrastructure/credentials.py`、`domain/*` | 后端 | 白名单内。 |
| `workflows/local_speech_evidence.py`、`workflows/local_bundle_producer.py`、`workflows/bundle_producer.py` | Agent/媒体 | 路径属媒体；语义我核过，无后端代写证据。 |
| `tools/build/DevRuntime.mjs`、`EngineProcess.mjs` | 集成/发布 | 白名单内；secret 只交 engine child，Vite 不接收。 |
| `packages/contracts`、`packages/api-client` | 集成生成 | 生成契约，随 schema 变更。 |
| `apps/workbench` + vitest | 前端 | 授权 UI，路径匹配。 |
| `tests/gate0/*` | 测试开发 | 路径匹配；测试无新授权/证据负例。 |
| `PROGRESS.md` | 统筹 | 进度记录，未改实现。 |

**未发现路径越界**；本批没有 BE 代写 Media 生产实现（媒体文件在 media 路径，且我按语义独立核验）。

## 6 未覆盖项

- 未在受限进程实测 WebSocket/静态（本 app 无 WS/static 路由）；SSE/docs/openapi 已实测 403。
- 未真实运行 `evidence-admin install` 的完整 receipt→observation→policy 链；只直接验证 helper 接受合成 operation/admission。
- 未跑 direct `local_speech` 真实语音包（PROGRESS 说发布停在 `alignment_required`）；材料构造基于代码和真实产物读取。
- 未构造 HMAC 篡改/跨实例 key 的独立用例；代码检查了 root/compare_digest，但 helper 旁路优先。
- 未跑 `tests/development` 之外的全量测试；35 passed 只覆盖开发场景。

## 7 最终

**OPEN_P1_BLOCKED**。产品授权四要素与受限 HTTP 数据面大体成立，语音材料构造也基本诚实；但 (a) owner approve 实际生成 management principal/secret，(b) 自签 helper 接受伪造 metadata/admissions，(c) 合成 settled operation 可被当成真实 ASR 观测并签成证据。三者任一都足以阻断。

**对关键问题的直答：有。** 在能写实例 `metadata`/`alignment_admissions`/`operations` 的边界内，伪造的 settled operation + qualification/admission 可以进入自签证据链，进而支撑“未被真实观测”的语音发布；若同时持有合法 local-evidence receipt，签出的 policy/qualification 会让该路径成立。正常 HTTP API 没有发现绕过四要素的“未同意”路径，但 owner approve 的 management secret 本身是另一个 P1 语义缺口。
