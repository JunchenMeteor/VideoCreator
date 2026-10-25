# ADR0082：本地安装实例自签语音证据（whisper 时间戳方法）+ ADR0075 语音条款修订

状态：NARROW_DESIGN_RULING，2026-10-25。只裁定"本地 0.4 语音作品包如何获得**本机自签**的证据策略准入、以及该证据类的凭据/内容/安装入口/标注/红线"，并修订 ADR0075 的语音条款。**不改源码、不改迁移、不批准任何远程/付费/第三方资质、不放宽任何生产校验**；§3.4 与 §4.4 列出的契约与校验分支是后继实现必须逐条落地的**收紧型**增量，不在本 ADR 内实施。

用户已拍板（`docs/task-board/LocalSpeechPipeline.md:66-70`）：证据由本机 Owner **自签**（仅本机、零成本、不出网）；对齐方法用 **whisper 时间戳**而非 CTC；精度 **`not_measured`**。本 ADR 是把这三条落成可执行、不可冒用的窄裁定。

## 0 实读证据（行号取 HEAD `abb7d1c`；`vc/` = `services/engine/src/video_creator`）

| 事实 | 位置 |
| --- | --- |
| 引擎今天**永远**以无信任根构造 registry，故 `alignment_required` 是唯一结局 | `vc/application/engine.py:70`（`PersistentEvidenceRegistry(self)`，无 `trust_roots`） |
| 有根才可管理：`administration_capability()` 无根即 `evidence_authority_unconfigured` 503 | `vc/application/evidence.py:69-74` |
| 根至少 32 字节，且必须同时给配置身份与外部撤销下限 | `vc/application/evidence.py:53-67` |
| 签名＝HMAC-SHA256 over canonical JSON，按 `issuer` 查根，`compare_digest` | `vc/application/evidence.py:80-86` |
| 每次读都核撤销下限与有效期；`evidence_registry_revision` 播种为 `'0'` | `vc/application/evidence.py:88-94`；`migrations/0005_alignment_admissions.sql:28` |
| `install` 需 capability + 文档/基准/审批三方互绑，`approval_refs` 必须含 `sha256(issuer:approval_id)` | `vc/application/evidence.py:101-118`（`:108-110`） |
| 同一 (kind,id,revision) 不同 body ⇒ `evidence_admission_conflict` 409（准入不可变） | `vc/application/evidence.py:123-127` |
| `validate_benchmark`：语料必须非空、N/P95 必须等于真实 unit 误差的 nearest-rank、P95≤200000、`source_gaps` 必须空 | `vc/application/evidence.py:38-49`；`vc/application/alignment_math.py:11,45-50` |
| 基准报告**无** limitations/summary 字段，只有 `audios`/独立听审/裁决/独立性引用/权威/判据/N/P95 | `vc/domain/contracts.py:1567-1590` |
| `audios` 至少 1 条；`independent_listener_refs` 至少 2 条；另有 `arbitration_ref`/`independence_evidence_ref` | `vc/domain/contracts.py:1575-1578` |
| 每 unit 误差＝max(\|Δstart\|,\|Δend\|)，三组数组必须非空、unit id 集合完全一致 | `vc/domain/alignment_math.py:14-42` |
| 资格只能绑 `capability_benchmark` 范围的报告（校验写死） | `vc/domain/contracts.py:1388-1392` |
| **whisper 路径本身在代码层被允许**：`runtime_match` 可由 ASR observation 自带 identity 满足 | `vc/application/bundles.py:2582-2600` |
| 未注册 CTC 时 `ctc_source=None` 且 writer 断言直接返回（"ASR-only work remains the original runtime validator branch"） | `vc/application/registered_alignment.py:437-450,452-455` |
| ASR worker 自报完整 `execution_identity` 与 `timestamp_method='whisper_word_estimate_not_forced_alignment'` | `vc/media/asr_worker.py:236-244` |
| 本片校验会调 `registry.verify(...)` 用报告身份比对资格范围，并要求资源清单已由安装准入 | `vc/application/bundles.py:2570-2572,2598` |
| V03 门：三类报告必需；基准/授权披露恰一份且必须与准入字节相等并重验 | `vc/application/bundles.py:2959-2972` |
| `not_measured` 只在 policy≠`strict_reference_v1` 时放行；`measured` 走每片独立测量 | `vc/application/bundles.py:2976-2981` |
| `not_measured` 时 N/P95/reference/report/criterion 必须全为 null | `vc/domain/contracts.py:1448-1457` |
| 转写必须绑定 `kind='observed'` 且资源清单已准入的 ASR 方法 | `vc/application/local_bundle_relations.py:110-113` |
| 材料角色→模型映射表（新增基准类必须在此登记） | `vc/application/bundles.py:82-96`（`:88`） |
| Media 现状：任何 audio 作品都被 `_speech_error` 拒绝 | `vc/workflows/local_bundle_producer.py:135-140` |
| ADR0075 冻结"原注册 CTC alignment 必需" | `docs/decisions/0075-local-material-bundle-and-still-semantics.md:42` |
| ADR0080 冻结"R1 仍要 CTC"，并把自己列为待后继裁定 | `docs/decisions/0080-local-speech-evidence-minimum.md:45,79-83` |
| ADR0015 明确：**"ASR 两次一致"不能充当可信证据**；自洽 metadata/VAD/第二模型一致均不能补测量 | `docs/decisions/0015-automatic-alignment-evidence-scope.md` §1、§3 |
| ADR0081 把 evidence policy/qualification/benchmark 列为**永久不走**产品内授权通道 | `docs/decisions/0081-product-authorization-channel.md:120,173` |
| ADR0081 的授权面上限：只做首次 Owner 初始化，且 approve 不产生 management capability | `docs/decisions/0081-product-authorization-channel.md:32,92` |
| `cryptography==50.0.2`、`keyring==25.7.0` 已是依赖；凭证只进 OS 保险库且拒绝弱后端 | `services/engine/pyproject.toml:7,19`；`vc/infrastructure/credentials.py:29-49` |
| 安装资格已有"本地校验者"先例：`trust_mode='local_verifier'` + `public_key_hex` 锚 | `vc/domain/installation_qualification.py:213,229-243,251` |

## 1 裁定摘要

1. **自签是一个独立的、明确更弱的证据类**：issuer 与 authority 都是本机实例自身，因此它只能证明"本机 Owner 在知情下允许本机方法发布本机作品"，**不能**证明精度、不能证明独立性、不构成第三方认证或官方合规。
2. **方法是 faster-whisper 的分段/词级时间戳**，`units='utterance'`。不安装 CTC（torch/whisperx）。代码层无需放宽：只要该 Run 从不注册 CTC（不写 `current_initial_alignment:`/`current_final_evidence_lineage:`），`ctc_source` 即 `None`，`runtime_match` 由 ASR observation 自带 identity 满足（§0 两行证据）。
3. **精度 `not_measured`**，不产生也不展示 N/P95，不生成独立 reference。
4. **绝不安装 `MethodBenchmarkReport`**：它不能为空（§0），而唯一能填满它的本地内容（自洽/复跑一致）正被 ADR0015 §1 明文拒绝为证据。因此自签路径改签一份**"未执行基准"声明**（§3.4），这是一次**收紧型**契约增量，不是对 `validate_benchmark` 的放宽。
5. **唯一安装入口**：ADR0081 通道批准一个 `kind='local_evidence_policy'` 的**范围**（复用其 token/secret/nonce/scope_sha256/审计），再由启动器拉起**一次性 evidence-admin 子进程**执行 `install`+`preauthorize` 后退出（§4）。该进程**不装配 OwnerServices、不产生执行身份、不监听端口**，故不触碰 ADR0081 §2.1/§2.2 的两条不可能性。
6. **默认关闭**。未启用时语音作品仍停在 `alignment_required` 409（与今天逐字同码），静音作品不受影响。
7. 一个实例一把 issuer、一把密钥、一个 authority、一份配置哈希；**不跨实例、不覆盖远程/付费、不参与 strict**。

## 2 自签主体与凭据

### 2.1 主体命名（全部带实例标识，可直接判别）

| 项 | 取值 | 理由 |
| --- | --- | --- |
| `issuer` | `local-selfissued-<instance_id>` | `_signature` 按 issuer 查根；不同实例永不互认（`evidence_issuer_untrusted` 403） |
| `authority_ref`（policy 内 qualification 与 benchmark 必须相等） | `local-selfissued-authority-<instance_id>` | 出现在每个已发布包内，机器可判"这是自签类" |
| `policy_id` / `qualification_id` | `local-selfissued-policy-<project或instance>-<n>` / `local-selfissued-qualification-<同左>-<n>` | 实例/范围可读 |
| `profile_id` | `whisper-word-estimate-local-v1` | 方法族可判；判据仍是固定的 `alignment-unit-max-p95-200ms-v1` 字面量，但**不得**用它声称达标 |
| `key_id` | `local-evidence-key-v1`（轮换则 v2） | 与 `EvidenceApproval` 无关，仅审计/配置 |

### 2.2 密钥在哪：OS 凭证库（keyring），不落盘、不进库

- 生成：首次启用时 `secrets.token_bytes(32)`（≥32 字节满足 `evidence.py:60-62`）。
- 存放：走**既有** `CredentialVault`（`credentials.py:29-49`），`SERVICE_NAME='VideoCreator'`，credential id `evidence_local_issuer:<instance_id>`。
- 选择理由（不是偏好，是约束）：
  1. `_backend()` 已按模块白名单只接受 Windows/macOS/SecretService/kwallet，**弱后端直接 503**，不需要新写平台分支；
  2. Windows 上 keyring 落到凭据管理器（DPAPI 保护），无需引入 DPAPI 专用代码，**同时满足三 OS 目标**（ADR0075 R2 不缩）；直接 DPAPI 会把本地自签变成 Windows-only。
  3. `keyring`/`cryptography` 都已是依赖，零新增。
- 禁止：写入 `Control/*.json`、数据库、日志、环境变量、命令行参数。审计只允许 `sha256(key)[:16]` 指纹（同 ADR0081 §4 对 secret 的处理）。
- 信任注入：根**只能**由受信启动器在构造 `PersistentEvidenceRegistry` 时给出（`trust_roots={issuer: key}` + `trusted_configuration_sha256` + `minimum_registry_revision`）。配置文件/环境变量/模型输出不得构成根（与 `evidence.py:1-5` 的 docstring 及 ADR0081 §12 一致）。
- 撤销下限：本地纯离线实例取 `minimum_registry_revision=0`（`migrations/0005:28` 播种即为 `'0'`，故合法且不伪造外部撤销事实）；该值连同配置哈希写审计。若将来导入外部撤销资料，必须同时抬升该下限。

### 2.3 算法：HMAC-SHA256（既有实现，不新增密码学）

`_signature` 已固定为 `hmac.new(key, canonical_json, sha256)` + `compare_digest`（`evidence.py:80-86`）。**不**改用 Ed25519：Ed25519 在本仓库只服务安装资格锚（`installation_qualification.py:229-243`），把 evidence 改成非对称签名需要动 `_signature`、`_load`、`revoke`、`verify_work_reference` 四处共同路径，收益为零而风险为正。签名体是 `EvidenceApproval` 去掉 `signature` 字段后的 canonical JSON（`issuer`、`approval_id`、`document_sha256`、`benchmark_content_sha256`），`extra="forbid"`（`domain/evidence.py:19-26`）——因此**不能**靠给 approval 加字段来绑定实例，实例绑定必须靠 §2.1 命名 + §2.4 的文档内约束。

### 2.4 防重放 / 防跨实例冒用（逐条对应机制）

| 威胁 | 防线 | 失败码 |
| --- | --- | --- |
| 抓取 approval 字节重放 | 准入不可变 + 同身份幂等：同 (kind,id,revision) 同 body 返回原 sequence，不同 body ⇒ 409 | `evidence_admission_conflict` 409 |
| 重放到别的实例 | issuer 内嵌 `instance_id`，根按实例生成；别处无此根 | `evidence_issuer_untrusted` 403 |
| 重放到别的 owner/项目 | `resolve` 强核 `policy.owner_subject == subject` 且 `policy.project_id ∈ {null, 项目}` | `evidence_policy_scope_denied` 403 |
| 重放执行身份 | 资格/基准的 `execution_identity` 必须等于**真实子进程观测**的 identity，且 `resource_manifest_sha256` 必须在安装准入清单内；不同机器/配置/模型字节即不匹配 | `work_execution_identity_missing` 409 / `evidence_execution_out_of_scope` 409 |
| 长期有效被当永久授权 | 有效期是必填有限区间；过期/未生效/已撤销都在每次读时核 | `evidence_admission_inactive` 409 |
| 换人/换机继承 | 撤销只允许**原 issuer** 签（`evidence.py:151-153`）；重新启用＝新 `instance_id`、新根、新 issuer | `evidence_revocation_denied` 403 |
| 篡改已装文档 | `check_evidence_record` 每次读重算 `content_sha256` | `evidence_hash_invalid` 422 |

**结论**：一个实例的批准字节在别处既无根可用、又过不了 owner/project/execution 三重范围比对，故不可复用；同一实例内的重放在语义上是幂等空操作（不是特权放大）。

## 3 签什么（三份文档的最小合法内容）

共同前提：三份文档的 `issuer` 都是 §2.1 的自签 issuer；`approval_refs` 都含 `sha256(issuer + ':' + approval_id)`；有效期建议 **30 天**（短窗本身就是重放/漂移的时间上限，并天然给出规范 06:89 的"授权过期"状态）；`content_sha256` 按 canonical 记录自洽。

### 3.1 `EvidencePolicyRevision`（范围＝本实例 + 本 project）

| 字段 | 冻结值 |
| --- | --- |
| `owner_subject` | 本机 Owner 的既有 subject（不得为通配） |
| `project_id` | 该 project；仅当用户明确选择"本机实例级"时才为 `null` |
| `alignment_evidence_policy` | `qualified_method_runtime_v1`（**禁止** `strict_reference_v1`：自签无独立 reference，选它就是自欺） |
| `alignment_requirement` | `utterance_verified`（word 级不开放，见 §7） |
| `qualification_ref` | §3.2 的完整引用 |
| `required_checks` | 恰 3 项且去重：`local_transcript_observation`、`local_alignment_method_scope`、`local_subtitle_serialization`。它们必须由 Media 在 `WorkAlignmentValidationReport.checks` 里以 `status='verified'` + 真实 `evidence_artifact_ids` 给出（`bundles.py:2580` 要求全集命中） |
| `preauthorized` | `True`（该字面量只表示"预授权"，不表示证据更强） |

### 3.2 `MethodQualificationRef`（方法＝whisper 时间戳，标注 estimate）

| 字段 | 冻结值 / 来源 |
| --- | --- |
| `execution_identity` | **必须照抄某次真实 settled ASR Operation 的 `runtime.execution_identity`**（`asr_worker.py:236-239`）：`method_id`、`tool='faster-whisper'`、`tool_version`、`model_id`、`model_file_sha256`（逐文件）、`resource_manifest_sha256`、`configuration_sha256`、`compute_type`、`device`、`operating_system`、`architecture`。**不许**由本机猜补缺失字段 |
| `applicability.languages` | 观测到的真实 `language`（例 `zh`），不得为 `*` |
| `applicability.input_media_types` | 实际提交音频 asset 的 media type（按真实取值列举，不写通配） |
| `applicability.transformations` | Media 实际声明的解码/混音链标识集合；必须使 `report.transformations` 为其非空子集（`bundles.py:2570`、`evidence.py:388-390`） |
| `applicability.maximum_duration_us` | 本机可承载的明确上限（取实测作品时长的上界并留余量），不外推 |
| `applicability.units` | `utterance` |
| `benchmark_report_ref` | 指向 §3.4 声明；`evaluation_scope` 必须用新增字面量 `capability_benchmark_not_performed`（见 §3.4） |
| `criterion_version_ref` | `alignment-unit-max-p95-200ms-v1`（schema 固定；**不得**据此声称达标） |
| `authority_ref` | `local-selfissued-authority-<instance_id>` |
| 有效期 | 与 policy 同窗 |

### 3.3 为什么本地自签**不能**签 `MethodBenchmarkReport`（三条硬事实）

1. **它不是可选/可空的**：`audios` 至少 1 条（`contracts.py:1575`），`sample_count` 是 `PositiveInt`，且 `(sample_count, p95_error_us)` 必须**逐字等于**该语料真实 unit 误差的 nearest-rank（`evidence.py:45-47`、`alignment_math.py:45-50`）。"诚实空基准"在这个类型里不存在。
2. **它必须声明独立性**：`independent_listener_refs` 至少 2 条 + `arbitration_ref` + `independence_evidence_ref`（`contracts.py:1576-1578`）。本地实例没有两名相互独立的听审者和裁决事实；填任何"构造记录/同一脚本哈希"进 listener 字段就是**伪造独立 reference**（红线）。
3. **唯一可填的内容被既有裁定明文禁止**：本机零成本能造出的只有"同一方法跑两遍一致"或"自我相等"的语料，其 P95 必然为 0——这正是 ADR0015 §1/§3 直接拒绝的"ASR 两次一致/VAD/自洽 metadata 不能补测量"。把它装成 `capability_benchmark` 并随包发布（`bundles.py:2969-2972` 要求基准材料进包且与准入字节相等），等于把 p95=0 印在交付物上。

**因此裁定：自签路径不安装任何 `MethodBenchmarkReport`。** 真实基准仍只能走 ADR0015 §4 的语料 + 独立听审 + 裁决 + 独立 Review 路径，本 ADR 不抄近路。

### 3.4 自签"未执行基准"声明（新类型，收紧型增量）

新增 `LocalSelfIssuedBenchmarkV1`（`vc/domain/contracts.py`，与既有类型并列，**不改** `MethodBenchmarkReport` 任何字段）：

| 字段 | 值 |
| --- | --- |
| `schema_version` | `0.3.0-candidate`（与 `EvidenceReportRef` 的字面量一致） |
| `evaluation_scope` | `capability_benchmark_not_performed`（**新增** `EvidenceReportRef.evaluation_scope` 与 `contracts.py:1388-1392` 校验的分支；仅当 `authority_ref` 是 `local-selfissued-authority-*` 时接受，否则仍按原规则要求 `capability_benchmark`） |
| `report_id` | `local-selfissued-benchmark-not-performed-<instance>-<n>` |
| `execution_identity` / `applicability` / `authority_ref` | 与 §3.2 逐字相等（`install` 的互绑检查 `evidence.py:114-118` 对新型同样执行） |
| `precision_claim` | `not_measured`（字面量，唯一取值） |
| `independent_reference` | `none`（字面量，唯一取值） |
| `corpus_ref` / `sample_count` / `p95_error_us` / `independent_listener_refs` / `arbitration_ref` | **字段不存在**（不是 null）：无法被引用、无法被展示成数字 |
| `limitations` | 至少 4 条固定文案：`whisper_word_estimate_not_forced_alignment`、`no_independent_precision_benchmark`、`self_issued_local_instance_only`、`not_third_party_certification` |
| `disclosure_sha256` | 本 ADR §6 文案清单文件的 SHA256（把"界面必须说什么"钉进证据里） |
| `content_sha256` | canonical 自洽 |

**为何这不构成虚假测量**：该文档**不含任何测量值、不含任何参考边界、不含任何 listener/裁决声明**；它是一份"未执行 ××"的**声明**，其唯一可被程序读取的精度结论是字面量 `not_measured`。安装/读取时用专属校验器 `validate_self_issued_benchmark`（新建，仅核自洽 + 身份相等 + 字面量 + 有效期），**不调用** `validate_benchmark`。发布包内它占据独立角色 `method_benchmark_self_issued`（§8），因此任何读者看到的是一个明写"未执行"的对象，而不是一个 0 微秒。

## 4 安装入口的调用面（与 ADR0081 的正面衔接）

### 4.1 结论：B′＝"ADR0081 通道批准范围，一次性 evidence-admin 子进程执行安装"

ADR0081 §7 把 evidence policy/benchmark 列为"**不可**走产品通道"，理由写在同表："需独立 authority 与真实语料，属证据准入，不是 Owner 授权"。这个理由**对发布方证据成立，对自签不成立**：自签的 authority 定义上就是本机 Owner 本人。但 ADR0081 的**技术**理由（§2 三条不可能性）仍然有效，且被本 ADR 完整尊重：

- §2.1 `install_startup_services` 的类型门 ⇒ 一次性进程**不调用它**，不产生执行身份；
- §2.2 每进程只能装配一次 `OwnerServices` ⇒ 一次性进程**不装配** `OwnerServices`；
- `install` 所需的全部东西只有：一个 `engine`（db/clock）+ 已配置根的 registry + 进程内 capability（`evidence.py:69-78`），三者**都不需要** OwnerServices、admission 或执行身份。

所以本 ADR 的结论不是"让授权请求线程写证据"，而是：**授权只批准范围；安装由专用短命进程完成；产品主进程随后按启动器配置进入正常/受限形态。**

### 4.2 端到端顺序（固定，可审计）

1. **先有真实观测**：用户发起一次语音作品尝试。Media 走真实 whisper 路径，ASR Operation settled；发布在 `evidence_registry.resolve` 处落到 `alignment_required` 409（`evidence.py:372-373`）。
2. **产品内取证**：Media 把该 settled observation 的 `runtime.execution_identity`、语言、时长、媒体类型、transformations 交给 Backend；Backend 用 §3.1-3.4 生成**三份文档草案**（含 `disclosure_sha256`），计算 `scope`：instance_id、owner_subject、project_id、三份文档的 `content_sha256`、有效期、`alignment_evidence_policy`、方法 profile。
3. **产品内授权**：走 ADR0081 既有通道，新增 `kind='local_evidence_policy'`：`ProductAuthorizationRequest` 复用其 `authorization_id/scope/scope_sha256/nonce/expires_at_us/state` 机与四项凭据（安装 token + `X-VideoCreator-Authorization` secret + 一次性 nonce + `scope_sha256`）。**只批准范围，不写证据行**。
4. **写审计并出收据**：按 ADR0081 §6 顺序"审计先行"写 `Control/ProductAuthorization.json`（`format='product-authorization-audit-v1'`，追加 `kind='local_evidence_policy'` 与三份 `*_sha256`），随后写一次性收据 `Control/LocalEvidenceIssuance.json`（`format='local-evidence-issuance-v1'`：`issuer`、`authority_ref`、`instance_id`、`owner_subject`、`project_id`、三份文档 SHA、`policy_ref`、`expires_at_us`、`receipt_id`、`nonce_fingerprint`、`session_secret_fingerprint`、`audit_sha256`），`xb`+`fsync`+`os.replace`，全文件 SHA256 回写审计。
5. **启动一次性进程**：启动器拉起 `video_creator evidence-admin install --instance <id> --receipt <path>`（`serve`/`worker` 之外的新子命令域，不监听端口）。该进程：①重算收据 SHA 与审计 SHA 相等、`instance_id` 相符、未过期、`receipt_id` 未消费（metadata `local_evidence_receipt:<receipt_id>` 插入即消费，重复 ⇒ 拒绝）；②从 OS 凭证库取根；③构造 engine + `PersistentEvidenceRegistry(trust_roots=..., trusted_configuration_sha256=..., minimum_registry_revision=0)`；④`install(capability, policy, benchmark, approval)`、`install(capability, qualification, benchmark, approval)`、`preauthorize(capability, owner, project, policy_ref)`；⑤写审计完成行；⑥`exit 0`。
6. **消费/重启**：若主进程启动时未配置根，启动器在安装后重启产品进程（确定性，无"同进程解锁"）；已配置根则下一请求即可解析出 policy，无需重启。
7. **重试原作品**：同一 Run 的可恢复 `alignment_required` 等待按既有 resume 语义重试（`bundles.py:1280-1297` 持久 blocker + waiting_user）。

### 4.3 为什么不选 A / C

- **不选 A（授权请求线程内直接装）**：请求线程里做 DB 写入会把"绑定/锁序"变成 HTTP 可触发的运行期动作（ADR0081 §2 第 3 条已判定不可）；且 `install` 需要 capability 对象，该对象只能由持有根的进程在进程内构造（`evidence.py:69-74`），授权进程没有根。
- **不选 C（安装时预置签名）**：技术上**做不到**，因为资格必须绑定**某次真实运行的子进程观测身份**（`bundles.py:2594-2596` 要求与 ASR observation 的 `runtime.execution_identity` 逐字相等；`resource_manifest_sha256` 还要在安装准入清单内）。安装器不可能知道将来的 `configuration_sha256`/`compute_type`/`device`/模型文件哈希。此外"先签名后同意"会把知情同意变成事后追认，本 ADR 明确不接受。
- **默认关闭**：未启用时 `resolve` 仍 `alignment_required` 409；静音作品、无语音作品路径完全不变。启用是一次显式、有范围、有期限、可撤销的产品内动作。

### 4.4 对 ADR0081 的两处**定点修订**（其余逐字保留）

| ADR0081 位置 | 原文 | 修订后 |
| --- | --- | --- |
| §7 表行"不可"（`:120`） | installation qualification / evidence policy / benchmark / ASR 资源准入 **否** | 拆为两行：**发布方/远程/第三方** evidence policy·qualification·benchmark·installation qualification·ASR 资源准入 = **仍为否**；**本地自签** `local_evidence_policy`（仅本机、零成本、不出网、`not_measured`）= **是**，且其安装动作由 §4.2 的一次性 evidence-admin 进程执行，不由授权请求线程执行 |
| §12（`:173`） | 不让产品通道签发 qualification 或 evidence policy | 不让产品通道签发**任何发布方证据**，也不让它在授权线程内直接写证据；它只能批准一个**自签范围**，实际写入由专用进程以本机自签 issuer 完成 |

其余 ADR0081 约束全部继承：审计先于生效、secret/nonce/scope 四项凭据、`restart_required`、`403 origin_denied`、不新增表、pending 只在内存。

### 4.5 失败语义（本地自签）

| 情形 | 返回 |
| --- | --- |
| 未启用自签（默认） | `alignment_required` 409（`evidence.py:373`，与今天同码） |
| 自签被策略禁用/被撤销 | `evidence_admission_inactive` 409 / `alignment_required` 409 |
| 授权被拒绝或过期 | `409 authorization_expired` / `403 ...`（沿用 ADR0081 §8，不写收据） |
| 审计写失败 | `503 authorization_audit_unwritten`，收据与证据行都不写 |
| 收据实例不符 | `409 local_evidence_instance_conflict`（不消费收据） |
| 收据重复使用 | `409 local_evidence_receipt_consumed` |
| 收据/文档 SHA 与审计不符 | `403 local_evidence_receipt_invalid` |
| 尚无真实 ASR 观测身份 | `409 local_evidence_observation_missing`（先跑一次真实转写） |
| ASR 资源清单未由安装准入 | `409 evidence_execution_out_of_scope`（先做资源准入） |
| 该范围已装过同一 revision | 幂等返回原 sequence（`evidence.py:123-127`） |
| 同 revision 不同 body | `409 evidence_admission_conflict` |
| 请求选了 `strict_reference_v1` | `alignment_required` 409（`bundles.py:2978-2979`，自签永不能满足） |
| 试图把自签策略用于远程/付费提供方 | `403`（路由/凭证侧既有校验；自签资格不含 `credential_ref`，且 applicability 只覆盖本地解码链） |
| 别实例的文档 | `403 evidence_issuer_untrusted` |

## 5 ADR0075 修订（精确替换措辞）

**替换** `docs/decisions/0075-local-material-bundle-and-still-semantics.md:42` 中"原注册CTC alignment与真实subtitle材料必需"整句为：

> speech_observed：最终mix或原受控解码音频的实际ASR Observation、完整actual transcript、**由已准入方法产出**的alignment与真实subtitle材料必需。本地默认即本地自签的 whisper 时间戳方法（`timestamp_method='whisper_word_estimate_not_forced_alignment'`，`units='utterance'`，`precision=not_measured`）；**注册CTC降为可选高阶能力**，不再必需。仍复用原policy/qualification/runtime report，且 benchmark 可为本地自签的"未执行基准"声明（ADR0082 §3.4）。生产脚本不是话语时，不以脚本正文替换actual transcript。已有speech却无资源/无可信报告就具名等待，不能转no_speech。**word级不可用**；任何"强制对齐"或词级精度的表述都被禁止。

**替换** `:69` 中"执行实际适用ASR/CTC"为"执行实际适用ASR（CTC为可选）"。

**保留不变**：no_speech_observed / no_audio_observed 两段（`:43-44`）、`LocalSpeechEvidenceV1` 字段集（`:40`）、`LocalActualTranscriptDocumentV1`（`:46`）、quality/语义/RAG/帧格/静图/唯一caller/提交与失败顺序全部条款。

**同步修订 ADR0080**（其 §4 `:79-83` 已把自己列为待后继裁定，本 ADR 即该后继）：

- `:45`"R1 仍要求 CTC" → **R1 不再要求 CTC**；三条前置条件的现状态是：①ADR0075 修订＝本节；②方法资格＝本 ADR 的自签 qualification；③`timestamp_method` 诚实标注＝不变。
- §2 `:56` 的 `method_refs`"（≥ ASR 与 CTC 两个方法）" → "**≥ 1 个**：被准入的 ASR 方法；装 CTC 时再加 CTC 方法"。
- §2 `:58` 的 `alignment_report_artifact_ids` 名单中的 `method_benchmark` → 本地自签时改为 `method_benchmark_self_issued`。
- §7 `:129`"缺 CTC 资源"一行降级为"若请求/注册了 CTC 才适用"。

## 6 证据标注（产物字段 + 必须出现的文案）

**产物内必须出现的机器可读标注**

| 位置 | 必须值 |
| --- | --- |
| ASR observation | `timestamp_method='whisper_word_estimate_not_forced_alignment'`（既有，`asr_worker.py:244`）；`audio_provenance.alignment='whisper_word_estimate; independent_precision_not_measured'`（`:264`） |
| `AlignmentRevisionV03.precision` | `status='not_measured'`、`units='utterance'`、`sample_count/p95_error_us/reference_ref/measurement_report_locator/criterion_version_ref` **全为 null**；`limitations` ≥ `('whisper_word_estimate_not_forced_alignment','precision_not_measured','local_self_issued_evidence')` |
| `LocalSpeechEvidenceV1.method_refs` | 仅 ASR 方法（无 CTC 时不列 CTC） |
| `LocalBundleQualityEvidenceV1` | `actual_transcript`/`alignment`/`subtitles` 的 applicability 必须 `applicable`（有语音时不得落 `no_observed_speech`/`no_audio_observed`，`local_bundle_producer.py:185-198`）；`alignment` 对应的 `checks[*].findings` 必须含「本地自签、未做精度实测」与「时间戳来自 whisper 词级估计，非强制对齐」两条字面量（`findings` 是既有字段，`contracts.py:1123-1129`） |
| policy / qualification / 自签基准 | `issuer`/`authority_ref` 以 `local-selfissued-` 前缀；自签基准 `evaluation_scope='capability_benchmark_not_performed'`、`precision_claim='not_measured'`、`independent_reference='none'` |
| 包内材料角色 | 基准材料以 `method_benchmark_self_issued` 出现，**不得**以 `method_benchmark` 出现 |

**界面/API 必须逐字出现的文案**（缺任一条即视为发布缺陷；`disclosure_sha256` 就是这份清单的哈希）

1. 「本地自签、未做精度实测」
2. 「时间戳来自 whisper 词级估计，非强制对齐」
3. 「不构成第三方认证或官方合规」
4. 「此证据仅本机实例有效，不跨实例复用」
5. 「未启用时语音作品会被拒绝（alignment_required），静音作品不受影响」

禁用表述：任何"通过基准/误差≤200ms/精度已测/已认证/合规/官方/校验通过"用于描述本自签证据；禁用把 `criterion_version_ref` 的存在读成"达标"；禁用把 `not_measured` 渲染成绿色"通过"。

## 7 红线（含执行点）

1. **不得声称第三方认证/官方合规/独立评审**：`independent_reference='none'`、`limitations` 固定项、§6 文案 3、`authority_ref` 前缀，四重钉住。
2. **不得让自签覆盖远程或付费能力**：自签资格不含 `credential_ref`；`applicability.input_media_types`/`transformations` 只列本机本地解码链；ASR 路由仍要求 `owned_local`、`verified`、零成本（对照 `local_alignment.py:75-78` 的同类门）。若请求解析到付费/远程路由，按既有 403 拒绝，自签 policy 无任何放行权。
3. **不得伪造精度数字或独立 reference**：本 ADR 既禁止安装 `MethodBenchmarkReport`（§3.3），也禁止把 P95 填成 0、禁止把构造记录写进 listener 字段、禁止生成任何 `PrecisionEvaluationReportV03`/`PerWorkReferenceDocument`（`bundles.py:2980-2981` 会以 `precision_evidence_conflict` 422 拒绝未测量作品夹带已测证据）。
4. **自签策略不得跨实例复用**：`issuer`/`authority_ref` 内嵌 instance_id、根按实例生成、owner/project/execution 三重范围比对、有效期有限、撤销限原 issuer。
5. **不得放宽任何生产校验**：`validate_benchmark`、`_verify_strict_precision`、`_verify_per_work_precision`、`install_startup_services`、`assemble_owner_services`、`management_access`、`ProductionAdmissions` 一行不改；新增分支只服务 `local-selfissued-*`，其他 issuer 走原规则。
6. **不得 word 级**：`alignment_requirement` 只 `utterance_verified`；`DeliveryRequirementsV03` 仍禁止降级（`contracts.py:1424-1428`）。
7. **不得把"自签已启用"说成"实例已可用语音"**：语音仍受真实 ASR 资源准入、真实转写、真实字幕字节、真实 mapping 逐 piece 校验支配。

## 8 接口清单（含最小正负例）

### Backend

1. `vc/application/engine.py:70`：`PersistentEvidenceRegistry(self)` 改为接受受信启动器注入的本地证据配置（issuer + 根 + `trusted_configuration_sha256` + `minimum_registry_revision=0`）。无配置⇒保持今天的行为（无根）。
2. 新增 `application/local_evidence.py`：issuer/authority 命名派生、三份文档构造、`scope`/`scope_sha256` 计算、收据读写、`evidence-admin` 子命令实现；**不新增表、不新增迁移**。
3. `evidence.py`：`install`/`_load`/`_verify_local_v03_reports` 的基准类型按 `format` 分派（`MethodBenchmarkReport` 走 `validate_benchmark`；`LocalSelfIssuedBenchmarkV1` 走新的 `validate_self_issued_benchmark`）；`install` 的互绑检查（`:114-118`）对两类都执行；`resolve`/`verify` 不新增放行分支。
4. `contracts.py`：新增 `LocalSelfIssuedBenchmarkV1`；`EvidenceReportRef.evaluation_scope` 增加 `'capability_benchmark_not_performed'`；`MethodQualificationRef.benchmark_scope`（`:1388-1392`）仅当 `authority_ref` 为 `local-selfissued-authority-*` 时接受该字面量。
5. `bundles.py`：`TEXT_MODELS` 增 `method_benchmark_self_issued`；`_verify_local_v03_reports`（`:2965-2972`）的"恰一份"规则扩为三选一（`method_benchmark` | `method_benchmark_reference` | `method_benchmark_self_issued`），且自签分支额外硬拒 `request.delivery_requirements.alignment_evidence_policy == 'strict_reference_v1'`。
6. 失败码按 §4.5 新增（均为 `local_evidence_*` 前缀，不并入任何等待码集合）。
7. **正例**：真实 settled ASR observation → 生成三份文档 → 收据 → evidence-admin → `resolve` 返回 policy，`evidence_registry_revision` +1，审计 SHA 与收据一致。
   **负例**：篡改 policy 任一字节 → `evidence_hash_invalid` 422；换 instance_id 重放收据 → `local_evidence_instance_conflict` 409；同 revision 换 body → `evidence_admission_conflict` 409；未配置根时调用安装 → `evidence_authority_unconfigured` 503；拿别实例 issuer 的文档 → `evidence_issuer_untrusted` 403。

### Media

1. `local_bundle_producer.py:135-140` 的 `_speech_error` 换成真实 whisper 路径；`_assembly_context`（`:389-391,413`）产出真实 `audio_mappings` 与 `asr_operation_id`。
2. 产出顺序：mix → ASR Operation(settled) → `Text/actual-transcript.json`(`actual_transcript_local`) → `AlignmentRevisionV03(precision=not_measured, method_ref=ASR方法)` → `Text/subtitles.srt|vtt` → `Checks/local-speech-evidence.json` → `Checks/quality-report.json` 的 reports/applicability → manifest/assembly。
3. `WorkAlignmentValidationReport`：`execution_identity` 必须等于该 ASR observation 的 `runtime.execution_identity`；`operation_ids` 恰为本次真实 settled 操作；`mapping_refs` 与 manifest `audio_mappings` 逐对相等；`checks` 恰含 policy 的三项且 `verified`；`result='verified'`、`source_gaps=()`、`reasons=()`。
4. **禁止**写 `current_initial_alignment:*`/`current_final_evidence_lineage:*`（写了就等于自报 CTC，见 `registered_alignment.py:437-450`）。
5. **正例**：真实中文 WAV + 一图 → 0.4 包含转写/双语字幕；断言 `precision.status='not_measured'` 且 N/P95 为 null、`timestamp_method` 为 whisper 估计、字幕字节等于 `serialize_subtitles`、`alignment.units='utterance'`、`method_refs` 仅 ASR。
   **负例**：把 `timestamp_method` 改成 forced alignment → `work_execution_identity_missing` 409；`precision` 填 `measured` 但无 reference → `alignment_required` 409；自造 `PrecisionEvaluationReportV03` → `precision_evidence_conflict` 422；基准材料以 `method_benchmark` 角色出现 → 类型不匹配 422；写 CTC lineage 但无 CTC 资源 → `alignment_resource_changed` 503。

### Test

1. 正例（端到端）：真实 WAV → ASR → 自签安装 → 0.4 包；断言三份证据材料在包内、`authority_ref` 前缀、`evaluation_scope='capability_benchmark_not_performed'`、`evidence_registry_revision` 单调、审计文件 SHA 与 metadata `product_authorization_audit` 相等。
2. 负例（安全）：跨实例文档/收据、重放收据、过期 policy、撤销后发布、`strict_reference_v1` 请求、无 ASR 观测先装、资源清单未准入、`instance_id` 不符、审计写失败不写证据行。
3. 负例（诚实性）：任何把 `not_measured` 渲染为通过、把 `p95=0` 塞进自签基准、把 `criterion_version_ref` 表述为达标、把自签表述为认证的界面/API 快照断言必须失败。
4. 缺资源（无 whisper 模型、无 runtime 锁）记 BLOCKED，不得 mock ASR/evidence 通过。

## 威胁模型边界（2026-10-26 评审补充）

P1-3 的观测承诺使用**实例保险库密钥**做 HMAC（`application/asr_observation_signature.py`）。它防的是：只有 SQLite/文件写权限、没有保险库密钥的篡改；以及应用自身把未执行/错误观测当成真实观测。**同一个 OS 用户若能读该保险库密钥，仍可伪造**；这不是远程 attestation，也不是"本机用户不可篡改"。UI/文档不得声称不可篡改，只能表述为"本安装实例的已签观测承诺"。

## 9 不做与后继

- 不做真实 capability benchmark（语料 + 独立听审 + 裁决 + 独立 Review），不做 `strict_reference_v1` 的本地替代，不做每片独立测量。
- 不做 word 级、不做 CTC 安装（保留为可选高阶能力，需另立资源与资格卡）。
- 不实现零 cue/no_speech、audio-only、Piper 旁白（仍按 ADR0080 §5 的顺序排队）。
- 不新增表/迁移；pending 与收据事实落既有 metadata + Control 目录。
- 不做远程/付费提供方，不做跨实例同步，不做"自签自动续期"（到期即 `alignment_required`，由用户再次知情启用）。
- 后继（优先）：①本节实现（Backend 6 项 + Media 5 项）；②真实基准路径（ADR0015 §4）以提升为 `capability_benchmark`；③CTC 可选高阶能力；④零 cue/audio-only/Piper。

## 10 复核清单

1. `git diff` 只新增 `docs/decisions/0082-local-self-issued-evidence.md`；`docs/architecture.md` 与 ADR0081 零改动。
2. 逐条核对 §0 的 24 行证据（行号与 HEAD `abb7d1c` 一致）。
3. 核对 §3.3 三条硬事实：`audios` 非空、listener≥2、ADR0015 §1 拒绝自洽。
4. 核对 §4.4 只改 ADR0081 两行，且未放宽其 §2/§4/§6/§8/§12。
5. 核对 §5 的替换句覆盖 ADR0075:42、:69，并同步 ADR0080:45,56,58,129。
6. 核对 §6 五条文案与产物字段一一对应，且 `disclosure_sha256` 可复算。
