# RV-LocalFinalProducerBundleV04 独立源码评审

结论：**OPEN_P1_BLOCKED**（源码可读、可导入、ruff/AST 通过，但按现有接线不存在任何可成功的 local 0.4 发布路径；两个独立 P1 在真实运行中必然阻断，且任务卡 must-4 的零 cue 分支不可达）。本结论仅为源码/静态与最小导入级验证，**未运行整链**。

- 评审版本：分支 `recovery/local-chain-20261025`，HEAD `017d3c3`；工作树未提交改动。
- 改动面（`git status --porcelain` / `git diff HEAD --numstat`）：
  - `workflows/bundle_producer.py` +39/−9
  - `workflows/local_bundle_producer.py` 新增 418 行（untracked）
  - `workflows/local_bundle_inputs.py` +26/−7
  - `media/local_material_edit.py` +22/−9
  - 本改动之外没有本次产生的 tests/docs 跟踪改动。评审期间工作树出现并行角色的文件（`api/app.py` 修改，`application/local_bundle_assembly.py`、`application/development_installation.py`、`cli/development_host.py`、`api/development_marker.py`、`docs/task-board/*.md` 新增），不在本次评审对象内；尤其 `local_bundle_assembly.py` 的出现会使交接 §5-3 的“缺该模块”过期，但本生产者仍未调用任何 local assembly 持久化。
- 本文行号：4 个改动文件为工作树行号；`application/`、`domain/` 为 HEAD 行号。

## 1. 逐条核验

| # | 事实 | 结论 | 证据与说明 |
| --- | --- | --- | --- |
| 1 | v2/v3 行为不变 | **PASS（有 1 个 P3 签名弱化）** | 用 `git show HEAD:...` 与工作树逐字比较：v2/v3 分支的 `produce_bundle(...)` 调用实参逐字相同，`load_asr_resources(resource_manifest_path, resource_manifest_sha256, runtime_manifest_sha256)` 实参逐字相同，`BundleMediaEvidence(resources.python, storage_root)` 相同（`bundle_producer.py:641-648`, `:675-686`）。差异只在：新增 local 分支、`produce` 的 v2/v3 形参由必填改默认 `None`（P3-1）。自测 `v2v3_asr_loads=1` 与源码一致。 |
| 2 | local 不加载 ASR | **PASS（仅限工厂；运行时另有前置加载通道）** | local 分支跳过 `load_asr_resources`，`media=BundleMediaEvidence(Path(sys.executable), storage_root)`（`bundle_producer.py:649-654`），与 `media_registration._initialize_local_runtime` 已有的同一解释器语义一致（`application/media_registration.py:225-232`）。但 `_require_selected_asr` 在 local 配置四字段非 null 时会真正 `load_asr_resources`（`application/media_registration.py:257-268`），因此“local 永不加载 ASR”只对 null-ASR 安装配置成立；标准 local 配置为 null 时在 `media_registration.py:295-296` 先退化为 `production_asr_resource_required` 503/park。 |
| 3 | manifest 是否全来自真实渲染/解码 | **PARTIAL** | 媒体资产时长/宽高/音频时钟来自注册资产的真实 probe 与真实 `media.clock`（`local_bundle_producer.py:227-239`）；文档 sha/size 来自真实 `stage_material` 回执（`:360-367`）；shots 来自真实末版帧采样（`local_bundle_inputs.py:96-116`）；visual mapping 来自 plan + 真实 probe（`:62-93`）；`audio_mappings=()` 是无音轨的真实缺席，不是伪造音轨。未发现“文件存在即通过”、空实现、硬编码时长/分辨率；`'0'*64` 只作 `_record` 前的占位（`:156`, `:179`）。但 `_methods` 的 `config_sha256`/`tool_version` 不是真实 ffmpeg 配置与版本（P2-2），且生产者本身不做任何渲染，只消费上游 `production-*`/`media-master` 产物；must-3 的“真实生成”在本 diff 中不可验证。 |
| 4 | 零 cue / 无音频 | **零 cue 材料真实可回解；但不可达且未绑定**；无音频 `audio_mappings=()` 语义正确 | 我独立调用 `validate_text(b'\n','srt_local','text/srt')` 与 `validate_text(b'WEBVTT\n\n','vtt_local','text/vtt')`，均原样返回（`application/bundles.py:181-193`），空字节仍被拒。但 `_documents` 从不生成 `Text/subtitles.srt/.vtt`（`local_bundle_producer.py:185-200`），`_validate_outputs` 对 `subtitles` 必 422（`:208-217`），而 `select_local_masters` 对无声作品直接拒绝 `subtitles`/`actual_transcript`（`domain/local_bundle.py:70-76`）；零 cue 分支整体不可达（P1-3）。无音轨：后端在 `no_audio_observed` 下允许空 `audio_mappings` 且重解码最终视频验证 `has_audio=False`（`application/local_bundle_relations.py:86-105`），不是伪造音轨；但“真正产出无音轨视频”的是上游 `LocalMaterialEditDriver`（`media/local_material_edit.py:262-270`），本 diff 未运行它。 |
| 5 | 失败语义 | **PARTIAL / 有回退** | 新文件无 `except`、`pass`、宽异常、空实现（grep 为空）；受阻给具名 `EngineError`。但 P1-1/P1-2 产生 `local_final_facts_conflict` 409 / `local_output_not_applicable` 422，二者都不在 `RESOURCE_WAIT_CODES`/`AUTHORIZATION_WAIT_CODES`（`application/media_registration.py:43-53`, `application/production_reauthorization.py:17-29`），会走“release+raise”终局（`media_registration.py:984-990`）。改动前同一位置抛 `production_local_final_consumer_missing`，该码在 `RESOURCE_WAIT_CODES`（`media_registration.py:52`）会 park 为 `resource_not_ready`；改动后由 wait 变成终局，属失败语义回退。 |
| 6 | 自测声明复核 | **证据与代码大体一致，但覆盖很浅** | 我自跑 `ruff check` 4 文件：`All checks passed!` exit 0；自跑 `ast.parse`：700/418/188/393 行均通过。`selfcheck.out.json` 的 v2/v3 ASR 次数、dispatch 码、零 cue 字节/SHA、ffmpeg 图/90 帧/3.000s、mp4 SHA 与代码/产物一致；filter graph 抽取前后逐字等价（我另用 still/video × contain/cover 四组独立比对）。但 `selfcheck.py:42-91` 只到 `local_final_services_invalid`（服务类型检查），未进入 `_validate_outputs`、facts、prepare/verify/publish；详见 §5。 |
| 7 | 越界检查 | **PASS（本改动）** | 本改动的跟踪改动只有上述 3 改 1 新，均在 `workflows/`、`media/`；`tests/` 无改动，未改 v2/v3 测试期望，本改动未写 `application/`、`cli/`、`docs/`。评审期间工作树出现并行角色的 `api/app.py` 修改与 `application/`、`cli/`、`docs/task-board/` 新文件，均不属这 4 个改动文件（见 §6）。仓库 `services/engine/tests/` 为空，`tests/` 未跑。 |

## 2. P1（阻断）

### P1-1 本地 final context 的“值比较”仍含实时时间戳，真实运行必 409

**事实**

- 新比较在 `local_bundle_producer.py:297-300`：

  ```python
  if (plan_admission != local_material_context.plan_admission
          or production_rights_fact != local_material_context.production_rights_fact):
      raise EngineError('local_final_facts_conflict', ...)
  ```

  以及 `local_bundle_inputs.py:40-48` 对 `plan_admission`、`quality_admission`、`production_rights_fact` 的同字段比较。

- 这些 Fact 是 pydantic 值对象，包含 `checked_at_us`/`valid_until_us`（`domain/production_authorization.py:266-267`, `:318-319`），且是**每次调用现算**的：
  - `ProductionPorts.current_production_admission` 用 `now = self.engine.clock()` 生成 `checked_at_us`、`valid_until_us`（`application/production_ports.py:111-148`）。
  - `ProductionPorts.current_production_rights` 用 `proposal.checked_at_us`（`production_ports.py:150-166`），而 `rights_proposal` 每次都 `now = self.engine.clock()`（`production_ports.py:81-109`）。
  - 策略路径 `PolicyExecutionPorts.production_rights` 同样每次 `now`（`application/production_admissions.py:773-805`）。
- `LocalMaterialSourceService.final_context` 每次都构造新的 `LocalMaterialFinalContext`，不做按 lease 缓存（`application/local_material_sources.py:282-309`，`:307`）。
- 调用链：`media_registration.py:589` 建 context A → `:596` 建 plan admission → `:602` 建 rights R1 → `:604` `_final_producer` 在 `:293` 再建 context C（含 plan admission 与 rights R2）→ `:607-608` 把 `plan_admission=plan`、`production_rights_fact=R1` 传入；生产者 `:297` 比较 R1 与 R2。

**反例条件**

任意真实 local 运行（未冻结时钟）：
- interactive：`plan_admission` 与 `production_rights_fact` 两侧 `checked_at_us` 不同；
- unattended：`plan_admission` 可能稳定，但 `production_rights_fact` 两侧 `checked_at_us` 必不同（两次 DB/解析之后调用 `engine.clock()`）。

结果：第一步就 `local_final_facts_conflict` 409；即使删除该守卫，`read_local_final_inputs` 的 `:47` 仍会在 context C 与再次读取的 D 之间因 rights 的 `checked_at_us` 不同而 `local_final_context_changed` 409。

**影响**

改动前该位置会 park 为 `resource_not_ready`（`production_local_final_consumer_missing` 在 `RESOURCE_WAIT_CODES`）；改动后变为终局 409（不在任何 wait 码集），因此本次改动把“可等待”变成“不可恢复失败”。这是比“原 `!=` 恒真”更隐蔽的同类缺陷：修了对象身份，没修时间戳。

**修复方向**

不要比较 live Fact 整体；比较不可变身份：`admission_ref`（`admission_id`+`content_sha256`）、`production_rights_fact.declaration_id`/`declaration_sha256`/`policy_ref`/`rights`，以及 plan/quality `RevisionRef`。或在 `final_context` 内复用同一份已持久化 admission/rights 快照；任何情况下不得把 `checked_at_us`/`valid_until_us` 纳入 held-context 等值判断。测试必须用真实时钟或显式固定时钟并验证“隔一次 DB 读写仍相等”，否则会掩盖此问题。

### P1-2 `_validate_outputs` 只拿文本文档集合比对，任何视频作品必 422

**事实**

- `_validate_outputs` 的 `produced = set(documents)`（`local_bundle_producer.py:208-217`）；`documents` 由 `_documents` 构造，只含 `Checks/…`、`Creative/production-plan.json`、`Semantics/…`、`Text/approved-script.json`（`:173-200`），**不含 `Media/*`**。
- `OUTPUT_PATHS` 却把 `video → ('Media/video.mp4',)`、`narration_audio → ('Media/narration.wav',)`、`mixed_audio → ('Media/mixed-audio.wav',)`、`subtitles → ('Text/subtitles.srt','Text/subtitles.vtt')`、`actual_transcript → ('Text/actual-transcript.json',)` 放进了同一张表（`:50-56`）。
- 对视频作品，`select_local_masters` 由 `video = 'video' in request.outputs` 定义 `content_kind='video'`（`domain/local_bundle.py:59-79`），因此 `request.outputs` 必含 `video`。

**反例条件**

任意 silent video 请求（`outputs=('video','approved_script','semantic_manifest','rag_chunks')`）。我直接调用（只读导入，不写文件）：

```text
_validate_outputs({...仅文档...}, Req(outputs=('video',...)))
→ EngineError local_output_not_applicable: Requested output video has no actual applicable local material.
```

即唯一已实现的 `no_audio_observed` 分支在 `_validate_outputs` 处 100% 失败（`:347`），永远到不了 `prepare_local`/`verify_local`/`publish`。

**影响**

local 0.4 无任何可发布路径；且 422 不在 wait 码集，终局失败。`artifact_ids` 其实已包含 `Media/video.mp4`（`:331-332`），`manifest.outputs` 生成逻辑也能找到它（`:368-369`），只是 `_validate_outputs` 的 `produced` 集合漏了媒体产物与零 cue 文档。

**修复方向**

`produced` 应为 `set(documents) | set(ROLE_PATHS[role] for role in selection.master_roles)`（并只对真实存在的文档/媒体判定）；`subtitles`/`actual_transcript` 在无对应真实材料时仍应拒绝，不能靠“把路径塞进 documents”绕过。

### P1-3 任务卡 must-4（无旁白→真实零 cue SRT/VTT）不可达

**事实**

- 选择器在无音频时直接拒绝 `subtitles`/`actual_transcript` 输出（`domain/local_bundle.py:70-76`）。
- 生产者 `_documents` 从不生成两份字幕文档（`local_bundle_producer.py:185-200`），`_slots`/`OUTPUT_PATHS` 也没有绑定它们；`_validate_outputs` 对 `subtitles` 必 422（`:208-217`）。
- 后端只允许在 `no_speech_observed` 且 `'subtitles' in request.outputs` 时才要求零 cue 文档（`local_bundle_relations.py:133-138`），而该状态需要真实 settled ASR gaps，当前冻结 ASR 拒绝空文本（`local_bundle_inputs.py:157-172` / 交接 §5-2）。
- `zero_cue_subtitle_materials()` 只被 `selfcheck.py` 调用（全仓 grep 仅 `local_bundle_producer.py:90-96` 与自测），生产路径无调用者。

**反例条件**

视频作品请求 `subtitles` → selection 阶段 `local_output_not_applicable` 422；即使绕过 selection，`_documents` 无字幕文档 → `_validate_outputs` 422；即使补文档，`_documents` 也没有 `Text/subtitles.*` 槽位。

**影响**

must-4 的字面要求未达成；当前只能给具名 blocker。交接 §6-6 已承认与 `local_bundle_relations.py:123-138` 的冲突，但任务卡仍未更新，验收口径应明确记为“未达成/需 ADR 或后端契约变更”，不能按“已实现”签收。

## 3. P2（需裁定/后端配套）

### P2-1 音频作品的阻塞码与实际路径不一致，且可能重新加载 ASR

- 标准 null-ASR local 配置：`media_registration._final_producer:295-296` 先调 `_require_selected_asr`，直接抛 `production_asr_resource_required` 503；该码在 `RESOURCE_WAIT_CODES`（`media_registration.py:50`），会 park 为 `resource_not_ready`，属可恢复等待。
- 因此生产者 `_speech_error` 的 `local_speech_observation_required`/`local_speech_evidence_unavailable`（`local_bundle_producer.py:99-104`）在标准配置下不可达；交接 §6-A2 要求 Backend 映射这两个码，但实际需要映射的是前者。
- 若 local 配置四字段非 null（`RegistrationConfigLocalV1` 允许全非 null，`domain/local_material_production.py:60-89`），`_require_selected_asr` 会真正 `load_asr_resources`（`media_registration.py:266-268`），与 must-1“local 不加载 ASR”冲突；随后生产者抛未映射 503，成为终局。需要明确 local 是否允许非 null ASR，并统一阻塞码。

### P2-2 method 证据不是实际工具配置/版本

`_methods`（`local_bundle_producer.py:160-170`）把 `config_sha256` 设为 `plan_ref.content_sha256`（EDIT）与 `digest('bundle-source-clock-and-frame-v1')`（DECODER），`tool_version` 写 `'local-owned-assets-v1'`/`'bundle-media-evidence-v1'`，不是实际 ffmpeg 版本或真实配置；后端 `_validate_shared_rights_methods` 只校验 artifact id 与 operation id（`application/bundles.py:2903-2935`），不会发现。字段能过 schema，但 manifest 的 method provenance 不是“真实测量”。建议写实际 ffmpeg/ffprobe 版本与资源 sha，或把这些声明为 profile 常量并加对应 limitation。

### P2-3 local 中途崩溃后无法恢复（无 assembly 持久化）

- 生产者不调用 `persist_initial_assembly`，也没有 local checkpoint；`verify` 依赖内存 `_local_preparation_contexts`（`application/bundles.py:1360-1373`），`publish` 依赖内存 `_verified_local_contexts`（`:1492-1503`）。进程重启后 `local_preparation_context_missing` 409，无法续跑。
- `continue_current_final_evidence` 对 local 把 `resources=None` 传给 `continue_bundle`（`bundle_producer.py:688-698`），而 `continue_bundle` 需要 assembly（`workflows/bundle_recovery.py:479-483`）；local 没有可读 assembly 时会 `final_assembly_unavailable` 503。
- 交接把“不走 assembly 路径”当作设计选择，但任务卡 must-5/6 要求原子 READY 与可恢复等待；至少应显式记为边界并给恢复方案（local assembly 或可重放 prepare/verify），否则任何崩溃都不可恢复。

### P2-4 unattended 发布的 8 输出硬门与 local 适用输出冲突

若 local 以 unattended/policy 运行并走到 `publish`，`_finalize_bundle_current` 要求 `requested_outputs` 恰为完整 8 输出（`application/production_admissions.py:853-856`），而 local 的选择器只产生适用子集（silent video 恰为 4 个左右）。这会 403 `production_publication_binding_invalid`。若 local 只支持 interactive，需在任务卡/ADR 写明；若支持 unattended，这项门必须按 local 适用输出调整（Backend 改动，非本 diff 能修）。

### P2-5 零 cue helper 不要求任何缺席观察

`zero_cue_subtitle_bytes(transcript=None)` 在 `transcript is None` 时跳过 `validate_no_speech_coverage`（`local_bundle_inputs.py:175-188`），`zero_cue_subtitle_materials()` 恰以 `None` 调用（`local_bundle_producer.py:90-96`）。当前是死代码，但一旦后续接线，就能在没有 `no_speech`/`gaps` 观察的情况下产出“零 cue”文档，违反 must-4 的“真实分支”。建议强制传入真实 transcript 或把该函数降为纯语法工具并在调用点显式断言观察来源。

## 4. P3（低风险/潜伏）

- **P3-1 v2/v3 形参弱化**：`produce` 的 `video_asset_id` 等由必填改默认 `None`（`bundle_producer.py:655-659`）。现有调用都传值，故 v2/v3 行为不变；但未来遗漏会静默把 `None` 传入 `produce_bundle`，而不是原来的 `TypeError`。建议 v2/v3 分支保持显式非 None 校验。
- **P3-2 音频内容路径潜伏 KeyError**：`_document_artifacts` 无条件构造 `'Semantics/semantic-segments.jsonl': (artifact_ids['Semantics/shots.jsonl'],)`（`local_bundle_producer.py:242-254`），而 `artifact_ids` 只在 `content_kind=='video'` 时含 shots（`:331-336`）。当前 audio 路径先被 `_speech_error` 拦住，尚不可达；一旦放开音频就是未捕获 `KeyError`（500），应改为具名 409。
- **P3-3 `sys.executable` 未核身份**：local 工厂用 `Path(sys.executable)`（`bundle_producer.py:654`）启动 `bundle_probe_worker.py`；与既有 local runtime 同义（`media_registration.py:225-232`），但未像 ASR 资源那样对解释器做 hash/路径注册。若宿主不是 Python 解释器（例如冻结 sidecar），`-I -B -X utf8 worker` 可能失败或启动错误进程；建议至少校验解释器身份/版本并给具名错误。
- **P3-4 证据文件编码/内容**：`selfcheck.out.json` 为 CP936+CRLF（含中文路径），`evidence.log` 为 CRLF；不符合工作区“UTF-8/LF”约定，且 `evidence.log` 的 ruff 记录没有命令行与文件列表，无法独立复现“哪 4 个文件”。`selfcheck.out.json` 的 `driver_class` 写 `LocalMaterialEditDriver`，但图来自 `visual_filter_graph`，不是 driver 实例；`still_hold` 只是合成素材，不是 Bundle 母版。
- **P3-5 工作树并行文件**：评审期间出现的 `api/app.py`（修改）与 `application/local_bundle_assembly.py`、`application/development_installation.py`、`cli/development_host.py`、`api/development_marker.py`、`docs/task-board/*.md`（新增）不属本次 4 文件改动；提交前需与并行角色拆分。其中 `local_bundle_assembly.py` 可能为 local 恢复提供新入口，但本生产者未调用，故不改变 P2-3 对“本生产者不持久化 assembly”的结论；该模块本身未审。

## 5. 自测声明独立复核

| 声明 | 复核结果 |
| --- | --- |
| 4 文件 `ruff check` exit 0 | **真**。我用 `.venv/Scripts/python.exe -m ruff check` 复跑，`All checks passed!` |
| 4 文件 `ast.parse` exit 0 | **真**。700/418/188/393 行全部解析通过 |
| v2/v3 仍调用 `load_asr_resources` 1 次，local 0 次 | **真**（`selfcheck.out.json` 与源码一致；我另行用 HEAD/工作树抽取确认 `produce_bundle` 调用与 ASR 实参逐字相同） |
| local dispatch 到 local 消费者 | **仅入口级**。`selfcheck.py:75-87` 的第二次调用在 `local_final_services_invalid`（服务类型检查，`local_bundle_producer.py:289-290`）即停；未执行 `_validate_outputs`、facts 比较、`prepare_local`、`staging`、`verify_local`、`publish` |
| 零 cue 可回解 | **真**。我独立调用 `validate_text`，得到 `'\n'`/`'WEBVTT\n\n'`；空字节仍拒绝 |
| filter graph 抽取无行为变化 | **真**。still/video × contain/cover 四组与 HEAD 内联表达式逐字等价；自测 ffmpeg 产物 90 帧/3.000s/H.264 与声明一致 |
| 真实运行/整链 | **未做**。`selfcheck.py` 自述“No model, network, database or Backend registration is used. This is not an acceptance or an end-to-end Bundle run.”；交接 §7 也承认 |
| 行数声明 +39/−9、+26/−7、+22/−9、418 行 | **真**（`git diff --numstat` 与 `wc -l`） |

## 6. 边界与未覆盖项

- **未运行整链**：没有 `tools/build` 生成的 `registered-media-config-local-v1`、没有 203 文件资源包、没有开发宿主、没有 Engine/SQLite/Worker/Step、没有 `bundle.prepare_local/verify_local/publish` 的真实执行，因此不存在“local 作品已发布”的运行证据。
- **未运行**：真实 ASR/CTC、音频作品、零 cue 端到端、unattended 发布、Windows 打包安装、仓库 `tests/`（本次未跑任何 pytest/acceptance；`services/engine/tests/` 为空）、v2/v3 回归。
- **仅执行**：4 文件 ruff/AST、HEAD↔工作树的调用逐字比较、`_validate_outputs` 的只读直接调用、零 cue 的 `validate_text` 回解、filter graph 四组等价比较、自测产物/日志核对。
- **未覆盖**：并行角色的 API/application/cli/docs 改动（含 `local_bundle_assembly.py`）；`docs/task-board/LocalChainEndToEndTest.md`；真实安装环境的解释器身份；外部并发/崩溃注入；任何“可发布”或“已验收”结论。
- 本文不关闭任何 P1；P1-1/P1-2 修复后仍需按 P2-1/P2-3/P2-4 决定 Backend 接口与 local 恢复/发布语义，再由 Test 角色补整链正例与失败负例。
