# ADR0080：本地 0.4 语音链的最小证据集合

状态：NARROW_DESIGN_RULING，2026-10-25。只裁定"本地 0.4 作品包在 上传音频 + 真实转写 + 字幕 时的最小语音证据集合、是否强制 CTC、字幕如何生成"。**不改源码、不改契约、不新增迁移、不批准任何资格/基准/authority**；不推翻 ADR0015/0016/0075/0076，只把它们的语音部分收成一条可执行的窄裁定。

## 0 实读证据（行号取 HEAD `0ac4935`；`vc/` = `services/engine/src/video_creator`）

| 事实 | 位置 |
| --- | --- |
| `DeliveryRequirements.alignment_requirement` 默认 `utterance_verified`，降级默认空 | `vc/domain/contracts.py:126-133` |
| 0.3 `DeliveryRequirementsV03` 恰两个 evidence policy：`strict_reference_v1` / `qualified_method_runtime_v1`，且禁止任何降级 | `vc/domain/contracts.py:1418-1428` |
| `PrecisionAssessment.status='measured'` ⇔ N/P95/report/criterion 全非空；`not_measured` ⇔ 全为 null | `vc/domain/contracts.py:882-905`；V03 同义 `:1437-1457` |
| `AlignmentRevisionV03(AlignmentRevision)` 只换 precision 类型 | `vc/domain/contracts.py:1460-1461` |
| `SubtitleTrack` 必带 `actual_transcript_revision_id`/`alignment_revision_id`/`mapping_revision_id` + srt/vtt artifact + 量化误差 | `vc/domain/contracts.py:984-1012` |
| 本地语音证据恰九字段、`speech_observed` 要求 audio+transcript+alignment+恰好两份字幕材料 | `vc/domain/local_bundle.py:129-157` |
| 本地转写文档：transcript + `AlignmentRevision\|AlignmentRevisionV03\|null` + `SubtitleTrack\|null` + `speech_evidence_artifact_id` | `vc/domain/local_bundle.py:160-166` |
| 本地装配：`asr_operation_id` 当且仅当 `mixed_audio` 选中时非 null | `vc/domain/local_bundle.py:302-323`（`:320-321`） |
| 本地校验入口 `validate_local_relations`：`speech_observed` 分支 | `vc/application/local_bundle_relations.py:98-167` |
| 其中：转写必须有 utterance/text；alignment 与 subtitles 都不得为 null | `:140-142` |
| 其中：alignment 类型分派——V03 走 `_verify_local_v03_reports`，否则走 `_verify_strict_precision` | `:155-158` |
| 其中：字幕字节必须等于 `serialize_subtitles` 且绑定本 transcript/alignment/timeline | `:159-165` |
| 其中：有声作品必须有非空 `audio_mappings` | `:186-187` |
| 非 V03 严格门：`precision.status != 'measured' or units != 'utterance'` → `alignment_required`（阻断） | `vc/application/bundles.py:2466-2471` |
| V03 门：必须集齐 `evidence_policy`+`method_qualification`+`work_alignment_validation`，且恰好一份 benchmark 或 licensed reference | `vc/application/bundles.py:2937,2964-2965,2970-2980` |
| V03 门：`precision=measured` → 走每片独立测量；`not_measured` 只在 policy≠`strict_reference_v1` 时允许 | `vc/application/bundles.py:2981-2986` |
| 运行时资格：`report.execution_identity` 必须在准入 qualification 范围内；units 必须等于 qualification 的 units；要求 0.3 request 且 `delivery_requirements` 非空 | `vc/application/bundles.py:2530,2560,2564,2567,2569` |
| 运行时匹配：`runtime_match` 可来自真实 CTC source，**或**来自 ASR observation 自带的 `execution_identity` | `vc/application/bundles.py:2576-2592` |
| 独立测量可选：`measure_alignment` 无 reference 时原样返回；测量永不进 CTC worker | `vc/workflows/bundle_v03.py:255-269` |
| 每片运行报告要求执行身份等于 qualification 身份 | `vc/workflows/bundle_v03.py:281-283,293-313` |
| CTC worker 自报 `precision=PrecisionAssessmentV03(status='not_measured')` | `vc/media/alignment_worker.py:248-252` |
| ASR worker 自报 `timestamp_method='whisper_word_estimate_not_forced_alignment'` 与完整 execution identity | `vc/media/asr_worker.py:236-243` |
| 注册 CTC 驱动：`alignment`/`qualified_local_forced_alignment` 资源段 + 资格执行身份 | `vc/providers/local_alignment.py:79-118` |
| evidence registry：无 policy → `alignment_required` 409；install 需 `EvidenceAdminCapability`；admission 存于 `alignment_admissions` | `vc/application/evidence.py:360-381,103-141,292-297` |
| Media 现状：任何 audio 作品都被 `_speech_error` 拒绝；装配上下文硬拒 audio mappings 且 `asr_operation_id` 恒 null | `vc/workflows/local_bundle_producer.py:135-140,545-556,389-391,413` |
| 本地材料 schema kind 已存在：`actual_transcript_local`、`srt_local`、`vtt_local` | `vc/application/bundles.py:84-104`；`vc/workflows/local_bundle_inputs.py:236-256` |
| ADR0075 已冻结：`speech_observed` 需要"原注册 CTC alignment 与真实 subtitle 材料" | `docs/decisions/0075-local-material-bundle-and-still-semantics.md:43` |
| ADR0015：`qualified_method_runtime_v1` = 合格方法 + 本片核验，不声称本片精度已测；对齐来源可以是候选 ASR，但须独立准入 | `docs/decisions/0015-automatic-alignment-evidence-scope.md:18-21,34-37,43` |

## 1 裁定摘要

1. **`utterance_verified` 本身不要求 `precision.measured`**，也不要求 CTC。它只固定 `units='utterance'` 且不许未批准降级。
2. **真正决定"要不要独立测量"的是 `alignment_evidence_policy`**：
   - `qualified_method_runtime_v1`：允许 `precision=not_measured`（N/P95/report/criterion 全 null），前提是准入 policy+qualification+benchmark 与每片 `WorkAlignmentValidationReport` 齐备（`bundles.py:2964-2986`）。
   - `strict_reference_v1`：必须 `precision=measured` + 每片独立 reference + 复算报告 + 200ms 判据（`bundles.py:2983-2984`；测量门 `_verify_per_work_precision:2598`）。
3. **本地 0.4 必须用 `AlignmentRevisionV03`**：用旧 `c.AlignmentRevision` 会落到 `_verify_strict_precision`，那里硬要求 `measured`（`bundles.py:2466-2471`），whisper 与 CTC 都产不出 measured。
4. **R1 仍要求 CTC**：不是因为它能"测出精度"（它自报 `not_measured`），而是因为 ADR0075 §3 已冻结"原注册 CTC alignment 必需"，且当前唯一有注册执行身份与运行时报告的对齐方法就是注册 CTC worker。**whisper 分段/词级时间戳不足以单独发布**：它只能作 transcript 的 `timestamp_method` 与 CTC 的输入单位锚点。
5. **字幕不额外要求 CTC 或 measured**：字幕的硬要求是 transcript/alignment/mapping 绑定 + 精确序列化字节（`local_bundle_relations.py:159-165`）。它只是在 R1 中"顺带"继承了 alignment 必须是注册 CTC 这一条。
6. **当前真正的阻断不是 CTC，而是 qualification 准入缺失**：`evidence_registry.resolve` 无 policy 即 `alignment_required` 409（`evidence.py:360-381`），而 `install` 需要 `EvidenceAdminCapability`（`evidence.py:103-141`），仓库无任何入口能造出 policy/qualification/benchmark/approval。**在准入之前，无论走 whisper 还是 CTC，语音作品都不可能发布。**

## 2 最小可行证据集合（`speech_observed`）

前提：0.3 request；`DeliveryRequirementsV03(alignment_requirement='utterance_verified', alignment_evidence_policy='qualified_method_runtime_v1', evidence_policy_revision_ref=<已准入 policy>, allowed_degradations=())`。

| 材料 | 必填内容 | 彼此约束 |
| --- | --- | --- |
| `Text/actual-transcript.json`（kind `actual_transcript_local`） | `LocalActualTranscriptDocumentV1`：`transcript`（input audio/asset = 最终 `mixed_audio` 的 asset+sha、`duration_us`=timeline、utterances 非空、`text`=逐 utterance 拼接、`gaps` 真实）、`alignment`（`AlignmentRevisionV03`，`precision=not_measured`）、`subtitles`（真实 cue 表）、`speech_evidence_artifact_id` | transcript/alignment/subtitles 三者互相绑定且绑定本 Run 的 mix（`local_bundle_relations.py:103-109,144-146,162-165`） |
| `Checks/local-speech-evidence.json`（kind `local_speech_evidence`） | `state='speech_observed'`、`input_audio_asset_id/sha256`、`transcript_artifact_id`、`alignment_artifact_id`、`subtitle_artifact_ids`（恰 2 个）、`method_refs`（≥ ASR 与 CTC 两个方法）、`proof_artifact_ids` | artifact id 必须在 manifest 索引内且与 manifest 的 `speech_evidence_artifact_id` 相同（`local_bundle.py:129-157`；`local_bundle_relations.py:33-36,83-84`） |
| `Text/subtitles.srt` / `.vtt`（kind `srt_local` / `vtt_local`） | 由 `serialize_subtitles(subtitles)` 生成的精确字节；`quantization_errors` 与之一致；毫秒 contain/上限策略 | cue 文本必须等于其 transcript unit 文本拼接；每 cue 不得在量化后塌陷（`bundles.py:3027-3047`；`local_bundle_relations.py:159-165`） |
| `Checks/quality-report.json`（kind `quality_local`） | `actual_transcript`/`alignment`/`subtitles` 三项 `status='applicable'` 且 `verified`；`alignment_report_artifact_ids` 恰为 `evidence_policy`、`method_qualification`、`work_alignment_validation`、`method_benchmark` 或 `method_benchmark_reference` | 每项 method_ref 与 evidence 必须已索引（`local_bundle_relations.py:295-316`；`bundles.py:2937-2980`） |
| `manifest.audio_mappings` | 非空真实 piece（mix placement：source_range/timeline_range/sample 边界/rate/rounding） | 有声作品必须有映射（`local_bundle_relations.py:186-187`），并过 `_check_mapping_piece` |
| 装配上下文 `LocalFinalAssemblyContextV1` | `audio_mappings` 非空、`asr_operation_id` = 真实 settled ASR Operation | `mixed_audio` 选中 ⇔ `asr_operation_id` 非 null（`local_bundle.py:320-321`） |
| ASR/CTC 取证 | ASR：`kind='observed'` 方法 + 同 Run settled 成功 Operation，observation 逐字匹配 transcript（`matches_actual_asr`，`bundles.py:155-174`）；CTC：`providers/local_alignment.py` 的注册 worker 输出 + `WorkAlignmentValidationReport` 的执行身份 | `resource_manifest_sha256` 必须在已准入集合内（`local_bundle_relations.py:110-113`；`bundles.py:2592`） |

**不需要**的东西（本轮明确可以缺）：每片独立 reference、`precision.sample_count/p95`、`precision_report_v03`/`precision_reference_v03`、word 级降级批准（0.3 禁止降级）、Piper 旁白、零 cue 字幕。

## 3 字幕是否强制 CTC / `precision.measured`

**都不强制，但都受 alignment 门支配**：

- 字幕本身只做字节与绑定校验（`local_bundle_relations.py:159-165` + `bundles.py:3027`），不读 `precision`。
- 若 alignment 是 V03 且 policy=`qualified_method_runtime_v1`：`not_measured` 可通过，字幕正常发布（`bundles.py:2981-2986`）。
- 若 alignment 是 V03 但 policy=`strict_reference_v1`：`alignment_required` 409（`bundles.py:2983-2984`），字幕随之不能发布。
- 若 alignment 用旧 `c.AlignmentRevision`：`_verify_strict_precision` 硬要求 `measured`（`bundles.py:2469-2471`），无论用 whisper 还是 CTC 都无法满足（CTC 自报 `not_measured`，`alignment_worker.py:250-252`）。
- 因此**字幕不是 CTC 的理由**；CTC 的理由是 ADR0075 §3 的冻结语义与"唯一有注册执行身份的方法"。

## 4 为什么"whisper 时间戳即可"在 R1 不成立、以后怎样才能成立

代码层面非 CTC 路径确实存在：`runtime_match` 可由 ASR observation 自带的 `execution_identity` 满足（`bundles.py:2576-2592`），即"被准入的 whisper 方法"可以充当运行身份。但要让这条路合法，需要同时满足三件事，缺一不可：

1. 修订 ADR0075 §3 的"原注册 CTC alignment 必需"（本 ADR 不改，属后继裁定）；
2. 为 faster-whisper 方法取得真实 benchmark + qualification + authority 并 `install` 进 `alignment_admissions`（ADR0015 §4：真实语料、独立听审、签名审批；仓库现无任何资格资料或入口）；
3. 保持 `timestamp_method` 的诚实标注（`whisper_word_estimate_not_forced_alignment`），不得改名 forced alignment。

R1 不满足其中任一条件，所以 **R1 的判断是：CTC 必需；`precision.measured` 不必需（`qualified_method_runtime_v1` 下）；whisper 时间戳只作单位来源与诚实方法标注。**

## 5 不做 / 后继

- 不实现 word_verified：0.3 禁止降级（`contracts.py:1424-1428`），词级需另立标准与准入。
- 不实现 no_speech / 零 cue 发布：沿用 2026-10-25 统筹裁定（`local_bundle_producer.py:299-308`），零 cue 另立架构卡。
- 不支持 audio-only 作品：`local_bundle_relations.py:172-173` 明确 `local_audio_work_mapping_required` 503，ADR0076 的 audio-only 目标映射未实现。
- 不实现 Piper 旁白（缺 voice 模型），不做远程/付费 ASR。
- 不自造 policy/qualification/benchmark/approval，不手写 `alignment_admissions` 行，不把 `timestamp_method` 改名。
- 不缓存/不短路上面的哈希与 Operation 取证。
- 后继（按优先级）：①evidence 准入的真实入口与首份 qualification（解锁一切）；②whisper-method qualification + ADR0075 修订（若要去掉 CTC）；③audio-only mapping（ADR0076）；④零 cue/no_speech；⑤Piper 旁白；⑥word 级与独立 reference 测量（strict 路径）。

## 6 接口清单

**Backend**
1. 放开 dev 宿主的 `development_asr_unsupported`：允许 local-v1 注册带 ASR 四字段（仍要求真实哈希与零成本 owned_local 路由，见 `media_registration.py:217-224`），否则语音链在 dev 里根本起不来。
2. `_validate_work_runtime` 的 `request.delivery_requirements` 空值防护：当前 `bundles.py:2560` 直接取属性，0.3 请求省略 delivery_requirements 时会变成未捕获 `AttributeError`；应改为具名 409/503（ADR0016 §1 允许由可信配置解析 policy，该解析若未实现就明确 `alignment_required`）。
3. 提供 evidence policy/qualification/benchmark 的可信准入路径（现仅 `evidence_registry.install` + `EvidenceAdminCapability`）；在它存在前，语音作品必须停在 `alignment_required`，不得用 dev 特判绕过。
4. 保持 `local_bundle_relations`/`_verify_*` 一行不改；本裁定不需要任何生产校验放宽。

**Media**
1. `local_bundle_producer`：把 `_speech_error`（`:135-140`）的 audio 拒绝替换为真实语音路径；`_assembly_context`（`:389-391,413`）必须产出真实 `audio_mappings` 与 `asr_operation_id`，不得再硬拒。
2. 新增材料槽：`Text/actual-transcript.json`（`actual_transcript_local`）、`Text/subtitles.srt|vtt`（`srt_local`/`vtt_local`），并把它们加入 `_document_artifacts` 的依赖（transcript/mix、字幕/transcript+alignment）。
3. 产出顺序：mix → ASR Operation（settled）→ transcript → 注册 CTC → alignment(V03, not_measured) → subtitles → speech evidence → quality 的 reports/applicability → manifest/assembly。
4. 必须真实写 `audio_mappings`（`_check_mapping_piece` 的全部字段），并从真实 CTC/ASR Operation 取 `method_refs` 与 `proof_artifact_ids`。
5. 不得自造 reference/report/authority；缺 qualification 时按 `alignment_required` 等待。

**Test**
1. 正例：真实中文 WAV + 一张图 → `outputs` 含 `actual_transcript`/`subtitles` → 0.4 包；断言字幕文本与 ASR 文本一致、`precision=not_measured` 且 N/P95 为 null、`asr_operation_id` 非空、mapping 逐 piece 通过、`serialize_subtitles` 字节相等。
2. 负例：旧 `AlignmentRevision`（非 V03）→ `alignment_required`；policy=`strict_reference_v1` 且无 reference → `alignment_required`；无 policy admission → `alignment_required`；audio 作品无 mapping → `audio_mapping_invalid`；`speech_evidence` 只有 1 份字幕 → 模型 422；篡改 srt/vtt 字节 → `subtitle_quantization_invalid`；把 whisper 标成 forced alignment → 拒绝改标（方法身份不匹配 `alignment_required`/`work_execution_identity_missing`）。
3. 不得用 mock ASR/CTC 产物通过；缺资源记 BLOCKED 而不是跳过断言。

## 7 失败语义（语音链）

| 情形 | 返回 |
| --- | --- |
| 无 evidence policy admission | `alignment_required` 409（`evidence.py:373`） |
| policy=`strict_reference_v1` 且 `not_measured` | `alignment_required` 409（`bundles.py:2984`） |
| 用旧 `c.AlignmentRevision` | `alignment_required` 409（`bundles.py:2471`，经 `_block` 落 waiting_user） |
| 报告集缺 policy/qualification/work validation | `work_evidence_material_missing` 422（`bundles.py:2964-2965`） |
| 执行身份不在准入范围 | `work_execution_identity_missing` 409（`bundles.py:2592-2594`） |
| units 与请求/资格不符 | `alignment_required` 409（`bundles.py:2569-2571`） |
| 有声作品无 mapping | `audio_mapping_invalid` 422（`local_bundle_relations.py:187`） |
| audio-only 无视频目标映射 | `local_audio_work_mapping_required` 503（`local_bundle_relations.py:172-173`） |
| 字幕字节/量化不符 | `subtitle_quantization_invalid` 422（`local_bundle_relations.py:159-161`） |
| 缺 ASR 资源/失败 | `actual_asr_evidence_missing` 422 / `actual_asr_unavailable` 409+reconcile |
| 缺 CTC 资源/运行时 | `alignment_resource_changed` 503 / `alignment_child_failed` 503 / `alignment_timeout` 409 |

新增码不得加入 `RESOURCE_WAIT_CODES`（`media_registration.py:43-53`）以外的等待语义；`alignment_required` 属可恢复等待（`bundles.py:1280-1297` 持久 blocker + waiting_user）。
