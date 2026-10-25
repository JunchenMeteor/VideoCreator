# 开发安装宿主与本地最终装配独立源码评审（RV-DevelopmentHostAndLocalAssembly）

**结论：OPEN_P1_BLOCKED。** 任务 A（`serve-dev`/`worker-dev` 开发安装宿主）的三重条件、`listener.bind` 前拒绝、真实磁盘证据、非 `NativeInstallationAuthority` 与零 qualification 写入，在源码与我独立复跑的负例层面成立；生产 `serve` 的 HTTP/契约字节未被改变。任务 B（`validate_local_assembly`）只做到“模块存在 + 探针派发”，真实 local 0.4 路径在到达新模块之前已被现有 4 母版门拒绝，且当前没有任何代码写入 `LocalFinalAssemblyContextV1`，不能按任务卡“任何 local 0.4 作品包的最终证据校验”验收。未发现可远程绕过的三重条件旁路、生产契约字节变化或 qualification 写入。

## 0 评审基线与方法

- 分支 `recovery/local-chain-20261025`。评审开始时 HEAD 为 `fb68343`；评审期间媒体角色提交了 `4f6ea4b`（`feat(media): local 0.4 final producer wired to the registered factory`），HEAD 前进，故本评审的基线是“**被评后端 5 个对象仍未提交**，叠在新 HEAD `4f6ea4b` 之上的工作树”。被评对象是未提交工作树，不是提交。评审时刻 2026-10-25 14:17–14:27（Asia/Shanghai），最终核对在 14:29 前后。
- 被评对象的实际字节（sha256 前缀）：`api/app.py` `2d3aaf92…`、`api/development_marker.py` `f98b174e…`、`application/development_installation.py` `b9804ed7…`、`application/local_bundle_assembly.py` `34016822…`、`cli/development_host.py` `785c6945…`。四份新增文件与 `app.py` 在评审期间 mtime 未变（`app.py` 14:08、`development_host.py` 14:14、`local_bundle_assembly.py` 14:09）；结论只对这些字节有效。
- **工作树在评审期间被其他角色继续修改并提交**：`media/bundle_evidence.py` 在交接稿 14:16 之后于 14:18 被改（`d4e5ae7b…`），`workflows/local_bundle_producer.py` 14:20:57 仍在变化（`a11161cb…`）；两者随后与另外三个媒体/工作流文件一起提交为 `4f6ea4b`，其提交内容哈希与本评审引用的工作树快照逐个一致。因此 `Evidence/static-checks.log` 的 188 与 `run-checks.log` 的 `pos-consistent` 只对应 `fb68343` 时的工作树；`4f6ea4b` 已再次改变 engine 全集哈希。本评审不把媒体角色文件当被评对象，只把它们的当前版本作为链路上下文。
- 我实际执行：`ruff check` 5 个被评文件（exit 0）、`ast.parse` 5 文件（全 OK）、`tools/build/ExportContracts.py` 输出到 `/tmp` 临时目录并对比 `packages/contracts/*.json` SHA、`_package_sources(PACKAGE_ROOT)` 计数与首文件真实哈希、`serve-dev`/`worker-dev` 缺参/缺 env/env 不匹配/frozen 四个负例、`TestClient` 的 `/health` 生产/开发/请求头伪造三态、关键 import 与 `LocalFinalAssemblyContextV1` 构造点全仓 grep、`git status` 禁止清单核对。自己写出的临时文件只在 `/tmp`，没有改实现、没有 commit。
- 行号缩写：`vc/` = `services/engine/src/video_creator/`；`repo/` = `G:/开发测试/Projects/VideoCreator/`。

## 1 逐条核验

| # | 核验点 | 结论 | 证据（file:line） |
| --- | --- | --- | --- |
| 1 | 生产零影响：只在 dev 进程加头；生产 `serve` 路径不变；OpenAPI/Schemas 字节不变 | **PASS**（两个 P3 附带项） | 头只来自进程内标记：`vc/api/app.py:17-21,169-175`、`vc/api/development_marker.py:11-21`；唯一 `mark_development_host()` 调用在 `vc/cli/development_host.py:312`；生产 `serve` 传 `installed_service_factory=None` 时 `bundle=None` 且 factory 不运行：`vc/cli/main.py:307-321`（`:312-321` 先建 Engine/Bundle，`:319-321` 才是 `install_startup_services`，`:323` 才 `bind`）。独立导出到临时目录的 `openapi.json` SHA-256 为 `e1f4011cbd16e9524c80696a070cf948f1459978d55530ae2b02dec16cc6e270`，与 `packages/contracts/openapi.json` 及 `git show HEAD:packages/contracts/openapi.json` 三者完全相同（HEAD 前进到 `4f6ea4b` 后我再次导出，SHA 仍相同）；`schemas.json` 的生成差异仅是 `media_diagnosis` 枚举（`vc/domain/contracts.py:295`，该文件 `git status` 为空），且 HEAD 的 `schemas.json` 本就不含该值 → 属既有漂移，不是本次改动。`TestClient` 实测：生产无头、mark 后有 `local-development`、请求头/query 伪造无效、OpenAPI 未声明该头。 |
| 2 | 三重条件不可绕过；均早于 `bind` 与 `assemble_owner_services`；不能由请求头/query/配置伪造；worker TOCTOU | **PASS**（三个 P3 附带项） | (a) 三参数必填：`vc/cli/development_host.py:59-64,74-77`（argparse，缺参 exit 2，我在新 data-dir 上复跑确认未创建目录）；(b) env 与 `engine.instance_id` 比较：`:144-149`，factory 首段 `:264`，worker wrapper `:333-340`；(c) frozen：`:261-263,329-331`。factory 经 `install_startup_services` 在 `vc/cli/main.py:319-321` 调用，`bind` 在 `:323`；`assemble_owner_services` 在 `vc/cli/development_host.py:308-311`。请求头/query/注册文件不能设置条件：`mark_development_host` 无路由、env 只读 `os.environ`；我实测伪造请求头无效。worker 的 wrapper 预检与 factory 复检之间若 env 或 data-dir/实例变化，factory 用**实际 engine**重新比较，失败即拒绝（fail-closed）；没有“两次读同一旧值”的放行路径。 |
| 3 | dev authority 不是 `NativeInstallationAuthority`，不触发 qualification，不写 `installation_qualification_*` | **PASS** | 类型：`vc/application/development_installation.py:177`（类名不同、无 `qualification_issuer`）；qualification 分支只在 `type(authority) is NativeInstallationAuthority` 时取 issuer：`vc/application/production_admissions.py:241-258`，否则 `nullcontext(None)`；`_guard` 只调 `installation_session_guard.assert_local_current(...)`：`:280-281`。dev 复用 `NativeOwnerServices` 并通过硬门：`vc/cli/development_host.py:313`、`vc/cli/startup_services.py:74-91`（`type(native)`、`_closed`、context instance/role、authority/connection 同一对象、`admissions.installation_authority/session_guard` 同一对象）。仓库内 `installation_qualification_*` 的写入者只有 qualification consumer（`vc/application/installation_record_consumer.py`、`installation_trust_consumer.py`），dev 路径不调用；`assemble_owner_services` 也不写资格表（`vc/application/owner_services.py:101-175`）。 |
| 4 | 证据真实性：哈希来自磁盘、时钟真实、`assert_current` 真重哈希、无配置哈希冒充 | **PASS**（两个 P3 附带项） | `engine_source_facts()` 用安装器自己的 `_package_sources/_local_file/_hash` 逐文件重算：`vc/application/development_installation.py:41-60`；资源用 `parse_local_material_resources` + `_hash` 后与配置哈希比较：`:71-114`（`:109-112`）。`observe()` 每次现取 `engine.clock()` 并从刚算出的 facts 建 evidence：`:231-243`（`:239`）；`assert_current()` 每次重新执行 `_current_facts()`（重读注册文件、重哈希 engine 与资源）再逐元组比较：`:255-264`→`:221-229`；没有哈希缓存/布尔短路（`_originals` 只存 evidence 对象，`:197,242`）。我独立验证：`_package_sources` 与 `rglob('*.py')`（排除 `__pycache__`）均为 **188**；`engine_source_facts()[0]` 的 sha/size 与磁盘 `sha256sum` 一致且按名排序。`observed_at_us` 是真实 `time.time_ns()//1000`（`vc/application/engine.py:58`）。 |
| 5 | 绑定一致性：`NativeLaunchContext` 与 `RegisteredMediaRuntime.sha256`/`installation_resource_identity`；8 字段；expiry 在 ADR 窗口 | **PASS**（两个 P3 附带项） | `launch_context` 用同一次 evidence facts 构造 `expected_files`/`engine_file_names` 与三 SHA：`vc/application/development_installation.py:138-146`；`NativeLaunchContext.__post_init__` 强校验 role/三 SHA/非空、不重名、engine 名真子集：`vc/infrastructure/held_authority.py:107-125`。worker 侧：`_runtime_registration` 核 `type(runtime.config) is RegistrationConfigLocalV1`、`runtime.path`、`runtime.sha256`：`vc/cli/development_host.py:184-204`；`RegisteredMediaRuntime` 本身先核文件 SHA 与 engine 全集：`vc/application/media_registration.py:126-146`；local 的 `installation_resource_identity` 三 SHA：`:315-320`。8 字段 dict：`vc/cli/development_host.py:300-307`，被 `owner_services.py:139-144` 精确集合校验，`register_execution_identity` 再核 project 真实存在/owned（`production_admissions.py:121-142`）。`_expiry` 用 `now` 与 `min(owner_expires, now+7d)`：`development_host.py:245-251`，与 ADR §4.3 一致。 |
| 6 | `local_bundle_assembly` 是否真实校验；有无“查不到就放行”/宽 except；与调用契约匹配 | **FAIL（P1）** | 派发真实：`vc/application/current_final_evidence_recovery.py:102-105`；返回形态在 `:359` 被当作 `asr`，在 `current_final_evidence_service.py:217` 被忽略。校验器确实逐项读 DB/磁盘：`:83-112`（binding/intent/clock）、`:116-130`（creative revision 三重一致）、`:132-160`（plan）、`:162-171`（selection 重算）、`:175-215`（committed media-master、Asset 字节、真实 decoder）、`:219-291`（speech）、`:300-328`（mapping）、`:332-367`（documents）；无宽 `except`（只有 `:148` 捕获 plan 解析的 `EngineError/TypeError`）。但真实 local 路径在到达它之前已被 4 母版门拒绝，且没有生产者写 local context（见 P1-1）；另有跨进程 held-context、`ReadSet.asr` 类型与部分跨项对照问题（P2-1..3）。 |
| 7 | 越界：禁止清单、白名单 | **PASS**（附带说明） | `git status --porcelain` 对 `production_admissions.py`、`cli/startup_services.py`、`application/native_installation.py`、`application/local_installation_authority.py`、`application/owner_services.py`、`application/media_registration.py`、`domain/contracts.py` 为空（我复跑，与 `Evidence/static-checks.log:22` 一致）。`api/app.py` 仅 `:17-21`（import）、`:52-54`（既有 I001 排序，见 P3-1）、`:169-175`（health 头）；`packages/contracts/` 无改动。评审开始时媒体角色文件（`media/bundle_evidence.py`、`media/local_material_edit.py`、`workflows/bundle_producer.py`、`workflows/local_bundle_inputs.py`、未跟踪 `workflows/local_bundle_producer.py`）仍在工作树；评审期间它们被提交为 `4f6ea4b`，当前工作树只剩 `app.py` M 与 4 个后端未跟踪文件。它们不在本次被评对象内；“禁止清单为空”对 `4f6ea4b` 仍成立。 |
| 8 | 作者自测复核：`ruff`/`ast`、拒绝码、engine 188 | **PARTIAL** | 我重跑 `ruff check` 5 文件 exit 0、`ast.parse` 全 OK；188 与 `_package_sources`/`rglob` 双向一致（ADR0077 的 183 已过时）。`run-checks.log` 的 14 个拒绝码逐条对得上代码：`development_installation_denied`（`development_host.py:148-149`）、`development_installation_unavailable`（`:262-263`）、`development_code_changed`（`development_installation.py:126-127`，消息逐字一致）、`development_registration_changed`（`development_host.py:161-162`）、`_profile_unsupported`（`:174-175`）、`_invalid`（`:171-172,179-180`）、`_missing`（`:157-158`）、`_engine_incomplete`（`development_installation.py:122-123`）、`_asr_unsupported`（`development_host.py:219-220`，422）、`_expiry_invalid`（`:89-98`）、resource missing/changed（`development_installation.py:67-68,111-112`）。**但** `grep-imports.log:9-14` 引用的 `development_host.py:246-312` 是旧行号（现为 261-331）；`ConsistentProbe.py:6` 预期 `owner_not_initialized`，实际日志是 `owner_directory_denied`；交接稿 §4 把 `author=True` 调用写成 `current_final_evidence_service.py:286`，实际在 `current_final_evidence_recovery.py:286`。所以“证据真实性”成立，“证据行号/快照”不成立。 |

## 2 P1（阻断任务 B 验收）

### P1-1 任务 B 的目标路径在到达 `validate_local_assembly` 之前就失败：4 母版门 + 无 local context 生产者

三个互相独立的事实：

1. **2/3 母版本地作品在 service 入口被 4 母版门拒绝。** `current_final_evidence_service.py:194-200` 在读取 assembly 之前先 `if len(intent.media_asset_ids) != 4: raise production_media_capability_missing 503`；`current_final_evidence_runtime.py:258-259` 在 recovery probe 里重复同一门（422 `bundle_output_missing`）。任务 B 声称要修的 `service:217` 在这两处之后，永远到不了。
2. **本地静音视频的母版数就是 2，不是 4。** `select_local_masters` 对无音轨视频给出 `('video','cover')`：`vc/domain/local_bundle.py:54-71`；媒体 local producer 构造 intent 时 `media_asset_ids=tuple(assets[role].asset_id for role in selection.master_roles)`：`vc/workflows/local_bundle_producer.py:413-418`；后端本地的 `resolve_preparation_masters` 也要求它恰等于所选集合：`vc/application/affected_repair_service.py:630-632`。因此“静音视觉作品”必在 `service:198` 503。
3. **唯一能过 4 母版门的有声本地作品被本地 producer 明确拒绝。** `local_bundle_producer.py:95-98,402-404` 对 `audio=True` 直接 `_speech_error`（“does not load ASR resources”）。所以在当前 local profile 里，**没有任何作品能同时满足 4 母版门与 producer 分支**。

补充：`LocalFinalAssemblyContextV1` **没有任何构造/持久化点**。全仓 `grep -rn "LocalFinalAssemblyContextV1"` 只有：领域类 `vc/domain/local_bundle.py:302`、读取分派 `current_final_evidence_recovery.py:92,103`、`persist_current_final_assembly_context` 的类型检查 `:279`、新校验器自身、以及探针。媒体 local producer 走的是 `bundle.prepare_local(...)` + `bundle.verify_local(...)` + `bundle.publish(...)`：`vc/application/bundles.py:919-949`、`vc/workflows/local_bundle_producer.py:419-451`，**不写** `current-final-assembly` 元数据。故 `_read_final_assembly` 的 local 分支目前不可被真实运行触发。媒体角色自己的独立评审 `docs/reviews/RV-LocalFinalProducerBundleV04.md:3,11` 也已判定 local 0.4 发布路径 `OPEN_P1_BLOCKED`，并明确“本生产者仍未调用任何 local assembly 持久化”；与本条互相独立地一致。

**反例条件（可复现的设计级路径）：** 一条无音轨、只有 `video`+`cover` 的 local 0.4 作品（当前 producer 唯一实现分支）→ `verify_current_final_evidence` / recovery → `current_final_evidence_service.py:198` 或 `current_final_evidence_runtime.py:258` → 503/422；`validate_local_assembly` 一次也不会执行。若改成 4 母版（加伪造 narration/mixed）才能过门，则违反 ADR0077 §7/ADR0075 的“不得伪造语音/音频”。

**结论：** 任务卡的前提“任何 local 0.4 作品包的最终证据校验都会 ImportError”只被修复到语法层；真实链路仍被上游 4 母版假设阻断。要关闭，必须由后端（`current_final_evidence_service.py`/`current_final_evidence_runtime.py` 不在禁止清单）把“4 母版”改为“所选 applicable 母版 + 与 selection 一致”，或由统筹明确本卡只做 source-level 准备并另立卡。**在此之前不能给 PASS。**

## 3 P2（非远程安全旁路，但契约/正确性未闭合）

### P2-1 `_masters` 依赖进程内 held context，跨进程恢复必然 409

`vc/application/local_bundle_assembly.py:179` 调 `source.runtime.master_assets(self.lease, selection=selection)`；`media_registration.py:346-353` 在 `selection is not None` 时先调 `self.local_plan_sources.assert_selection_current(lease, selection)`；`vc/application/local_material_sources.py:330-338` 要求 `self._contexts` 中存在同 lease、同 selection 的项，否则 409 `local_master_selection_invalid`。`_contexts` 只在 `final_context(...)` 内填充（`local_material_sources.py:282-308`），进程启动时为空（`:69` `WeakKeyDictionary()`）。

**反例条件：** `LocalFinalAssemblyContextV1` 已持久化、worker 重启后 `resume_current_final_evidence` → `read_continuation_inputs` → recovery:359 → 新校验器 → `_masters` → `assert_selection_current` 抛 409；`media_registration.py:884-888` 把 409 当 `still_blocked`，轮询永远不前进。若 P1-1 修好，这条会立即成为 P1。修法应是 validator 只用已提交的 media-master Step（`master_assets(lease)`）并与 `selection.master_roles` 逐项比较，而不是要求 live held context。

### P2-2 `validate_local_assembly` 的返回值违反 `CurrentFinalEvidenceReadSet.asr` 类型契约

`vc/domain/current_final_evidence.py:219-229` 声明 `asr: CurrentFinalAsrRead | None`；`local_bundle_assembly.py:370-378` 返回 `LocalSpeechEvidenceV1 | None`，并在 `current_final_evidence_recovery.py:359,437` 直接塞进 `.asr`。`workflows/bundle_recovery.py:100-130` 的 `_validate_readset` 不检查 `assembly`/`asr` 类型；一旦 local readset 进入 `_actual()`（`bundle_recovery.py:145` 访问 `source.context_ref/status/observation`），得到的是未捕获的 `AttributeError`（进程级 500），不是具名 `EngineError`。当前 local producer 不消费 readset，所以是潜在缺陷；但 ADR 要求的“返回形态与调用契约匹配”并未真正满足（只能算 `:217` 忽略返回值这一条匹配）。

### P2-3 speech/transcript/document 的跨项对账不完整，`_mappings` 在缺 ASR 时被跳过

- `local_bundle_assembly.py:250-291` 对有声分支只核 `audio_roles` 非空、`asr_operation_id` 非空、`audio_mappings` 非空、`Text/actual-transcript.json` 被索引、`read_settled_original_asr` 非 None；**没有**把 `speech.input_audio_asset_id/sha256` 绑定到实际 `mixed_audio` Asset、把 `speech.transcript_artifact_id/alignment_artifact_id/subtitle_artifact_ids` 绑定到实际索引文档。对照 `local_bundle_relations.py:103-165`（发布阶段）才做这些。
- `local_bundle_assembly.py:251-253`：`if speech is None: return`，于是 `allow_missing_asr=True` 时 `_mappings()` 完全不执行；`current_final_evidence_recovery.py:359` 正是这样调用。
- `_documents`（`:332-367`）只 `validate_text`，不把 `sources/summary.source_refs`、`script.script_revision_ref` 等与 `context.source_refs/creative_revision_refs` 对账（V2 分支在 `recovery.py:160-163` 做了），也不核 `approval_refs`。

**反例条件：** 构造 schema 合法但 `input_audio_asset_id` 指向另一 Asset、或无 mapping 的有声 assembly；`validate_local_assembly` 可通过并持久化，直到 `local_bundle_relations.py` 发布阶段才报错。不是“静默通过”，但“提交前逐项一致”的声明过强；测试角色必须用真实 fixture 覆盖，不能只跑派发探针。

## 4 P3（需记录/后续修正）

1. **`api/app.py:52-54` 的 import 重排是越界的生产源码改动，但属既有 lint 债。** 我用 `git show HEAD:.../app.py | ruff check --stdin-filename ... -` 复现 HEAD 已报 I001（exit 1），所以它是“改动文件 ruff exit 0”的必要代价，不是本次逻辑改动；但 PR 应单列说明，避免被误读为 health 头的一部分。
2. **frozen 判断在 argparse 之后。** `development_host.py:327` 先 `parse_args`，`:329-331` 才 frozen；frozen 产物缺参会 exit 2，而不是 ADR §2 的 `development_installation_unavailable`。没有 Engine/端口副作用，但顺序与 ADR “frozen → dev argv”不完全一致。
3. **`worker-dev` wrapper 额外创建一个 `EngineService`，拒绝不是无副作用的。** `development_host.py:333-340` 先 `EngineService(start.data_dir)` 再转发；我实测无 env 的 `worker-dev` 在新 data-dir 上创建了 `Metadata.sqlite` 后才 exit 1。没有绕过（factory 用实际 engine 复检 env），但双 Engine、双实例读取和 side effect 应记录；相对路径 `--development-registration` 在 worker 侧会由 `RegisteredMediaRuntime` 报生产码 `production_resource_denied`，而不是 `development_registration_missing`（错误码映射偏差）。
4. **dev 标记是无保护的模块全局。** `api/development_marker.py:11-21` 任何 import 方都可 `mark_development_host()`；生产 `/health` 随之为 dev 头。请求头/query 不能设置（我实测无效），但 ADR §5 “只来自进程内 dev 绑定”依赖 import 纪律，不是强制；只影响自述，不是资格。
5. **`DevelopmentInstallationAuthority` 构造器自身不检查 frozen/env/CLI。** 三重条件全在 `cli/development_host.py`（`:261-264`）；`application/development_installation.py:187-199` 可被任意 in-process 调用者与 `assemble_owner_services` 组合，从而跳过三重条件。当前唯一 import 方是 dev host（grep 证实），console entry 也不暴露 factory，所以不是可达旁路；但应作为防御性约束记录（或在 `launch_context`/authority 里加“仅 dev 进程”自检）。
6. **Owner 读两次、严格度不同。** `development_host.py:235-242` 用 `allow_inactive=False` 预检；`owner_services.py:117` 在 assembly 内又用 `allow_inactive=True` 重读。撤销发生在两次读之间时，dev 仍会注册身份；它最终受 `registered.expires_at_us` 约束（`production_admissions.py:176-180`），且 ADR §8.6 已接受“运行中撤销不即时”，所以只是窄竞态 P3。
7. **`_expiry` 与 `register_execution_identity` 的时钟竞态。** `development_host.py:245-251` 用采样 `now`，`production_admissions.py:121-125` 再用更新后的 `clock()` 比较；若时钟前跳，用户会看到 `production_execution_registration_invalid` 而不是 `development_expiry_invalid`。语义仍 fail-closed。
8. **`installation_resource_identity` 的 worker 校验是重言式。** `development_host.py:200-203` 比较 `runtime.installation_resource_identity` 与 `(runtime.sha256, config.production_resource_manifest_sha256, config.production_runtime_manifest_sha256)`，而 `media_registration.py:315-320` 对 local 正是这样定义的；该断言永不失败。真实绑定来自 `:195-198` 的 path/sha 与 `RegisteredMediaRuntime` 构造时的文件哈希（`:136-140`），所以不是漏洞，但别把这条当独立证据。
9. **dev 未在入口拒绝 unattended。** ADR0077 §7 要求 `automation.mode` 必须 `interactive`；dev factory 没有任何 mode 判断，unattended 请求会进入 production policy 分支（`production_admissions.py:892-903,946-950`），最终由已装 policy 决定，而不是 `development_*` 拒绝。低于 ADR 的显式范围。
10. **证据/交接的时效与行号问题。** `Evidence/grep-imports.log:9-14` 行号已过时；`ConsistentProbe.py:6` 的 `owner_not_initialized` 与实际 `owner_directory_denied` 不符；交接稿 §4 的 `current_final_evidence_service.py:286` 实际在 `current_final_evidence_recovery.py:286`；`static-checks.log` 的 188 是 14:15 的快照，14:18 后 `media/bundle_evidence.py` 改变并于评审期间提交为 `4f6ea4b`，任何那时的注册文件都已因 engine 哈希变化而失效（ADR §8.3 的预期，但证据应带快照哈希与 HEAD）。
11. **`local_bundle_assembly` 的音频分支对 audio-only 永远失败。** `_mappings`（`:304-309`）要求 `video` 非空，而 audio-only 的 `committed` 无 `video`；当前模型虽允许 2 母版 local context，audio-only 会被 `local_assembly_mapping_invalid` 拒绝。当前 producer 拒绝音频作品，所以不可达；若后续开放 audio-only，需先修此分支。
12. **无自动化测试。** 本卡没有在 `tests/` 增加任何宿主/装配测试；作者的自测是过程目录探针（`LocalAssemblyProbe.py` 只到 binding 派发），任务卡把正向路径留给测试角色可以理解，但意味着新模块没有回归保护。

## 5 未覆盖项（本评审明确没证明的）

- **任务 A 的真实正向路径**：受保护安装目录 + 真实 TTY `owner-init initialize` 下的 `serve-dev` 全链、`/health` 头端到端、`worker-dev` 正向、`installed_principal_id`（ready 的 `principal_id`）、`confirm_api_cleanup`、`NativeOwnerServices.close()` 顺序。作者也承认本机不可完成，我未改环境去伪造。
- **未触发的拒绝码**：`development_role_denied`（dev parser 无 mcp 命令，factory 的 role 分支实际不可达）、`development_evidence_foreign`、`development_installation_retired`、`development_identity_collision`（engine/资源重名）、`development_expiry_invalid` 的 7 天上限分支、注册文件 >1 MiB、symlink/junction、`for_management=True`/`registered_runtime` 非空/错误 bundle engine 等 factory 分支。
- **任务 B 的真实正向/负向**：静音 0.4 包的 plan/quality/selection/media_roles/音频映射/零语音证据逐项核对；发布阶段 `local_bundle_relations` 的联动；缺件、篡改、跨 Run、跨 preparation 的真实错误码。现有探针只证明 import/派发与 binding 拒绝，且 `LocalAssemblyProbe.py:67` 用 `SimpleNamespace(engine=...)`，没有 DB、没有 committed 事实。
- **跨进程恢复**：P2-1 的 held-context 拒绝、`current_final_evidence_runtime.py:258` 的 4 母版门、`_probe_final_inputs:271` 的 ASR 阻塞都只做了代码级判断，没有用真实 journal 跑过。
- **并发/生命周期**：`assert_local_current` 的 `installation_session_busy` 竞争、`observe()` 长哈希期间 close、`_originals` 长跑增长（与 native 同构，作者已注明）、`_retired` 之后四方法的完整拒绝表。
- **生产 `serve` 的实际进程**：我只用 TestClient/导出验证了头与契约，没有起真实 `serve` 进程做 HTTP 抓包；`openapi.json` 字节相同是最强证据。
- **`schemas.json` 的可重现性**：本次生成与 committed 有既有 `media_diagnosis` 漂移（HEAD 源码已含、HEAD 生成物缺），我未在 HEAD 的干净 checkout 上重新生成来逐字节证明“HEAD 也漂移”；但差异定位与 `git show HEAD` 已足以排除本次改动。
- **Windows 专属路径**：junction/symlink、UNC、设备路径、大小写/长路径只做了代码阅读，没有逐项构造。
- **任务 A 的资格语义边界**：dev 证据只证明“本 checkout 字节一致”，不是安装/发布/Gate0/验收证据（ADR0077 §1/§8.1），本评审不把任何 dev 绿色当生产资格。

## 6 结论边界

- 任务 A：源码层面 **PASS**（三重条件、pre-bind、真实证据、零 qualification、生产契约不变、禁止清单未动），但只到“负例 + 进程内接线”证据，正向路径仍待测试角色。
- 任务 B：**OPEN_P1_BLOCKED**（P1-1）。在 P1-1 修复并补真实 local fixture 之前，`validate_local_assembly` 不能算“已实现并可用”；P2-1..3 是修 P1 后必须一起处理的契约问题。
- 本评审只读实现；没有改代码、没有提交、没有把 `docs/reviews/` 之外的任何文件写回工作树。

## 7 收口窄复审（HEAD `213fa61`，2026-10-25 14:49 后）

**窄复审结论：PASS（无剩余 P1）。** 原 `OPEN_P1_BLOCKED` 保留为上一轮历史结论；本节只复核 A1–A5、残留 1–3 与 B1/B2 是否闭合。基线：上一轮评审提交 `80c548e` → 后端收口 `831e2cf` → 媒体收口 `213fa61`；工作树 clean，上一轮 5 个后端对象已包含在 `831e2cf`，媒体 producer 已包含在 `213fa61`。我独立执行：7 文件 `ruff/ast`（exit 0）、`ExportContracts.py` 到临时目录（`openapi.json` SHA `e1f4011…` 仍与 committed 相同）、`ClosureProbe.py`（**67 PASS / 3 FAIL**，见 P2-3）、以及自写的 `has_original_masters`/2 母版 service/空 `_contexts` resolver/空 `_contexts` `_masters`/`_assembly_context`/A4/A5 探针（均在 `/tmp`，未写仓库）。

### 7.1 P1-1：2 母版越过旧四母版门——已闭合

| 核验 | 结论 | 证据与我的实际调用 |
| --- | --- | --- |
| 2 母版本地装配进入真实 `validate_local_assembly` | **PASS（方法级）** | `current_final_evidence_service.py:210-218` 先读已提交 assembly，`assembly is None` 才保留旧 4 母版门（`:211-213`），否则 `has_original_masters`（`:214`），并把 `assembly.selection` 传给 resolver（`:216-218`）。我实际调用 `_resolve_current_final_inputs`（本地 2 母版、空 `_contexts`）：返回 `CurrentFinalEvidenceInputs`，resolver 收到同一 selection，`_validate_final_assembly_facts` 收到同一 local context；未抛 `production_media_capability_missing`。`ClosureProbe` T2 实际跑 `verify_current_final_evidence`，栈进入 `local_bundle_assembly._scope`，失败码是 `local_assembly_binding_invalid` 409（不是旧 503）。 |
| 旧格式（含 `None`）仍要求 4 | **PASS** | `current_final_evidence_recovery.py:53-68` 的 `has_original_masters` 对非 local/`None` 返回 `len(intent.media_asset_ids)==4`；`current_final_evidence_runtime.py:285-299` 同样是“assembly 为 None 才旧门 / 否则按版本”。我自测：V2 0..6 个 id 只在 4 时为 True；`None` + 2 为 False、4 为 True。实际 service 调用：legacy V2 2 母版 → 503 `production_media_capability_missing`；legacy V2 4 母版 → 进入原校验；无 assembly 2 → 503；无 assembly 4 → 503 `final_assembly_unavailable`。旧 `verify(..., manifest)` 仍走原 `verify`（T3 以 sentinel 验证）。 |
| `resolve_preparation_masters` 的 local 判据可靠 | **PASS** | `affected_repair_service.py:693-696` 的判据是 `slot.schema_kind.endswith('_local') or in {'local_master_selection','local_speech_evidence'}`，与 `bundles.py:972-973` 的 `has_local` **逐字同义**；本地 `LOCAL_REQUIRED_FILES`（`domain/local_bundle.py:17-22`）与 producer `DOCUMENT_KINDS` 均含这两个 kind，旧 0.2/0.3 kind 无 `_local`。我实际调用 resolver（空 `_contexts`、无 selection）：本地 2 母版返回 `('video','cover')` 且顺序等于 `selection.master_roles`，legacy 返回 `('video','narration_audio','mixed_audio','cover')`；显式 selection 不读 assembly；`_local_source` 0 次。 |
| 跨进程 `_masters` 不再依赖 held context | **PASS（方法级）** | `local_bundle_assembly.py:175-222` 的 `_committed_masters` 直接读已提交 `media-master` Step + operations，不再调 `master_assets(selection=...)`；`:224-241` 仍逐项核 selection/intent/context，`:243-263` 仍核 Asset 字节/真实 decoder。我在空 `_contexts`、`_local_source` 设为“调用即失败”的对象上实际执行 `_masters()`：成功返回 `{'video':'asset-video','cover':'asset-cover'}`，`_local_source` 0 次。`ClosureProbe` T4 同样通过。 |
| 残留限制 | **PARTIAL** | 以上是方法/分派级，不是真实 Run/DB 的 `verify_current_final_evidence` 或 `read_continuation_inputs` 全链；真实 DB/port 需要 Owner/authority，本轮没有伪造。 |

### 7.2 P1-2：producer 在 prepare 与 verify 之间持久化——源码闭合，E2E 未证

| 核验 | 结论 | 证据 |
| --- | --- | --- |
| 确实在 prepare 与 verify 之间 persist | **PASS（源码）** | `workflows/local_bundle_producer.py:484` `prepare_local` → `:514-525` 构造并 `:518` `persist_assembly_context(lease, preparation_id, assembly)` → `:528` `verify_local` → `:530` `publish`。`ASSEMBLY_DOCUMENT_ROLES`（`:83-95`）与 Backend `DOCUMENT_PATHS` 的路径→角色逐条一致（我独立 import 比较，含 `LOCAL_REQUIRED_FILES` 全覆盖）；`ContractCheck.py` 输出 `prepare_at=28753 < persist_at=31265 < verify_at=31913`。 |
| 字段来自真实 Manifest/selection/binding | **PASS（源码+构造探针）** | `_assembly_context`（`:357-397`）：`binding` 来自 `bound_context`（`:375-377`），`preparation_id/intent sha/fence` 来自实际 preparation/intent/lease（`:381-383`），`manifest_created_at_us/timeline/creative refs/approval/feedback/source/outputs/methods/rights/quality_ref` 全部取自实际 `BundleManifestLocalV1`（`:384-391`），`media_artifacts` 来自真实 `_media_artifacts`（`:300-316`，按 selection 顺序），`document_artifact_ids` 来自 manifest artifact（`:372-374`），`audio_mappings=()`、`asr_operation_id=None`（`:390-392`）且 `mixed_audio`/非空映射先 409（`:369-371`）。我用真实 `BundleManifestLocalV1` 字段形状的 manifest + 真实 `LocalMasterSelectionV1`/`BundleArtifact` 调 `_assembly_context`：media artifacts、selection、binding、documents、`asr=None`、空 mappings 全部一致；`mixed_audio` 选择得到 `local_assembly_audio_mapping_unexpected` 409。 |
| 失败具名、不静默 | **PASS（源码）** | 端口缺失 `require_final_port(None)` → 503 `current_final_evidence_port_required`（我实跑）；`LocalFinalAssemblyContextV1` 模型失败捕获为 422 `local_assembly_context_invalid`（`:393-397`）；persist 返回 ref 逐项核对失败 409 `local_assembly_commit_invalid`（`:520-525`）；缺文档/角色/资产/ASR 由 Backend `local_bundle_assembly` 给具名码。没有宽 `except`/静默跳过：`require_final_port` 在 `prepare_local` 之前（`:406,421`），不再允许无 port。 |
| 真实读回 | **未证（P2）** | 媒体交接稿 §3.4/§4 明确真实 `prepare_local→persist→verify_local→publish` 未跑（Owner TTY 阻塞，`owner_init` 返回 `owner_interactive_confirmation_required`），`VerifyPersistedAssembly.py` 只得到 `no_persisted_assembly`；我复核了该原始日志与实例：无 `current_final_assembly:*` 行。故“源码实现”闭合，“真实落盘/读回”仍是测试角色或 TTY 后的 P2，不是代码 P1。 |

### 7.3 新引入风险复核

- **`affected_repair_service.py` 227 行 diff 除分派外无业务语义变化（PASS，P3 细节）。** 函数级 AST 对比 `80c548e..213fa61` 只显示 5 个函数变化：`_affected_execution`、`observe_current_affected_masters`（仅未用变量改 `_journal/_request`）、`authorize_current_affected_execution`、`assert_current_production_services`（仅合并嵌套 `with` 与 import 重排）、`resolve_preparation_masters`（本卡分派）。旧四角色默认值、`_master_roles_from_step`、非 local lineage 分支未改；我实际测 legacy 4 角色仍成功、本地 2 角色成功。
- **`current_final_evidence_service.py` 329 行 diff 是 lint + A1（PASS，P3 错误优先级）。** 函数级 AST 只变 `_current_repair_scope`（合并 `with`）、`_resolve_current_final_inputs`（A1）、`revise_current_final_preparation`（import/未用变量改名）；无其他语义。唯一可见行为差：assembly 现在在旧 4 母版门之前读取（`:210`），已存在的坏 assembly 会先报 `final_assembly_invalid` 而不是旧 503；两者都 fail-closed。
- **`runtime.py` 的 ASR 跳过条件不会误跳过非 local（PASS）。** `:301-303` 条件严格为 `type(assembly) is local.LocalFinalAssemblyContextV1 and operation_id is None`；非 local（含 `CurrentFinalAssemblyContext`/V2）仍走原 `_probe_waiting_original_asr`；local 有 ASR 仍 probe。`ClosureProbe` T9 与我的 A3 探针（`final_read_set_asr(local) → None`，非 local 原样返回）一致；`CurrentFinalEvidenceReadSet.asr` 注解仍是 `CurrentFinalAsrRead | None`。
- **A4/A5（PASS，P3 运维面）。** 我在临时目录实测：`_existing_instance_id` 对中文路径的已有实例返回相同 id；无 env 的 `worker-dev` exit 1 且**不创建** data-dir；`sys.frozen=True` 时缺参也返回 1 `development_installation_unavailable`（不再 exit 2）。A4 的 `create_production(interactive)` 通过、`unattended` 422 `development_mode_unsupported`、Goal 入口 422 且原函数未调用；生产 `BundleService` 类未被 patch。Goal 创建在 dev 被整体拒绝，意味着 dev 端不能用 Goal 建项目（符合 ADR0077 §7，但运行手册要写明）。

### 7.4 剩余 P2 / P3

**P2**
1. **B1/B2 真实落盘/读回仍未执行**：无 Owner/TTY + 注册包 `production_code_changed`；只证到源码/契约/构造器。需要测试角色在真实 dev host 上跑 `prepare_local→persist→verify_local→publish` 并用 `VerifyPersistedAssembly.py` 读回。
2. **跨进程 recovery 只到方法级**：我证明空 `_contexts` 的 resolver/`_masters`/2 母版 service gate 不再 409/422，但没有真实 `current_production_final_evidence:*` journal + Run/DB 的 `read_continuation_inputs` 全链。
3. **`ClosureProbe.py` 在 HEAD `213fa61` 为 67 PASS / 3 FAIL**：3 个 T8 “pre-fix”检查用 `git show HEAD:...` 当旧代码，HEAD 已是修复版，故必然失败；后端交接的“70 PASS / 0 FAIL”是 `4f6ea4b` 时结果，当前不可复跑为 70。产品断言（T2/T4/T8 fixed/T9/T10）均 PASS，但证据需改为固定 `80c548e:` 或记录基线。

**P3**
1. `has_original_masters` 对“local 但 media_artifacts 角色/顺序/资产不符”的 assembly 在 service/runtime 返回通用 503 “All four original masters required”，而不是 `local_assembly_*`；仍是 fail-closed，但错误信息误导。
2. service 先读 assembly（`:210`）改变旧坏 assembly 的错误优先级（`final_assembly_invalid` 先于旧 503），交接已记录。
3. `resolve_preparation_masters` 的 held 分支仍用 `master_assets(selection=...)` 的 step `media_roles` 顺序返回，未按 `selection.master_roles` 重排；非 held 分支最后重排（`:743-744`）。当前 local publish 不走该 held 分支，但两分支顺序不一致是未来漂移点。
4. `resolve_preparation_masters` 对非 local 且调用方误传 selection 时静默 `selection=None`（`:711-712`），不拒绝；当前唯一调用方只对 local 传。
5. `final_read_set_asr` 对 local 一律返回 `None`，local 若有真实 ASR（本 profile 不实现）会丢 speech read；类型契约正确，语义面需未来 local speech 卡重审。
6. `ASSEMBLY_DOCUMENT_ROLES` 用 dict 按 path 覆盖，manifest 同路径重复 artifact 时后者覆盖前者；Backend 只查 required 覆盖，不查文档重复路径，靠 manifest verify 兜底。
7. `persist` 在 `verify_local` 之前写 assembly；若 verify 失败，assembly 已不可变落盘（媒体交接 §6.5 已记录），重试同字节可过、不同字节 409。
8. A4 用实例属性 monkeypatch（`bundle.create_production`、`runtime.invoke`、`bundle.create_project_goal`）只在 dev factory 返回的同一对象上；我用替身验证入口，但未用真实 `create_app`/HTTP 跑；生产不受影响需靠 factory 不安装。
9. `_existing_instance_id` 用 `mode=ro` 打开 WAL 数据库，若 live worker 持有 `-shm` 且只读打开失败会返回 None（403），不会创建；这是可用性边界，不是绕过。
10. `_committed_masters` 与 `media_registration.master_assets` 的 Step/Operation 校验重复（交接 §7.1 已记录），后续媒体角色语义需双向锁定。

### 7.5 窄复审结论

- **P1-1 闭合**：旧四母版门只在无 assembly/非 local 保留；2 母版本地装配以实际 service 方法进入 `validate_local_assembly`，旧格式仍 4；resolver 判据与既有 `has_local` 同义，空 `_contexts` 不再 409/422。
- **P1-2 源码闭合**：persist 位于 prepare 与 verify 之间，字段来自真实 manifest/selection/binding，失败具名；真实读回仍待 Owner/TTY 与测试角色（P2）。
- **无剩余 P1**；结论 **PASS（窄复审）**。原 `OPEN_P1_BLOCKED` 只作为上一轮历史，不覆盖本节。
