# LocalSpeechPipeline

统筹任务卡，2026-10-25。目标：把本地链从"静音视频"推进到"真实语音 + 转写 + 字幕 + RAG"。
当前状态：静音 0.4 作品包已真实产出（`production-1d22330e…` succeeded）；语音路径被显式拒绝。

## 已核实的资源现状（2026-10-25 实测）

| 项 | 状态 |
| --- | --- |
| faster-whisper-small 模型 | **在盘**：`Integration/Runtime/Models/FasterWhisperSmall`（`model.bin` 483 MB） |
| ASR 运行时 | 本机 venv 已装 `faster-whisper 1.2.1` + `ctranslate2 4.8.3`（**PyAV 必须 `av<19`，19 版删了 `metadata_errors`，faster-whisper 1.2.1 会直接 TypeError**） |
| 实测转写 | Windows SAPI 合成 6.29 s 中文 WAV → 识别「这是一段本地生成的测试旁白，用来验证语音识别链路。」（小模型有个别字错，属预期） |
| Piper 旁白 | **缺 voice 模型**（`Integration/Runtime` 下无 `.onnx`）→ 本地 TTS 旁白不可用 |
| 对齐（CTC/whisperx） | 代码存在（`media/alignment_worker.py` + `ctc_alignment.py`），运行时未装 torch/whisperx |

## 结论：先做"自带音频"而不是"本地 TTS 旁白"

- 旁白（narration）需要 Piper voice 模型，缺件，先记 BLOCKED。
- **上传音频**路径不需要 TTS：用真实 WAV 作为输入 → 混音 → ASR 转写 → 字幕 → RAG。这条能把 R1 的"真实转写/字幕/RAG"跑通。

## 缺口清单（按归属）

1. **集成**：产出 ASR 资源包与清单（模型目录逐文件哈希、运行时清单、`asr_route_id`），格式对齐 `providers/asr_resources.load_asr_resources`；并把依赖固定进 `pyproject`/锁：`faster-whisper==1.2.1`、`ctranslate2==4.8.3`、`av==18.1.0`（**不能用 19**）。
2. **后端**：dev 宿主目前**拒绝非 null ASR**（`development_asr_unsupported`，我此前要求的）。本卡要求放开为：允许 local-v1 注册带 ASR 四字段，但仍要求真实资源哈希与零成本本地路由；不得允许远程/付费 ASR。同时评估 local 的 `alignment_registration` 是否可为空（若字幕只需 utterance 级时间戳）。
3. **媒体**：把 `local_bundle_producer` 的 `_speech_error` 分支替换为真实语音路径：对 `mixed_audio` 跑已注册 ASR（`RegisteredOperationExecutor` + ASR journal），产出 `actual-transcript.json`、`subtitles.srt/.vtt`、`semantic_manifest`、`rag_chunks`；零语音作品仍走现有 `no_audio_observed`。
4. **测试/验收**：一条真实请求（视频素材 + 真实中文 WAV，`outputs` 含 video/narration?/mixed_audio/actual_transcript/subtitles/semantic_manifest/rag_chunks）跑通并校验字幕文本与音频内容一致（人工实听 + 文本比对）。

## 验收

- 真实运行产出 0.4 作品包，含非空 `Media/mixed-audio.wav`、`Text/actual-transcript.json`、`Text/subtitles.srt|vtt`、语义/检索材料；
- 字幕文本与音频实际内容一致（人工核对，给出转录文本与音频 SHA）；
- 成本 0、无远程调用；
- 不得用"空字幕/零 cue"或伪造转写通过。

## 明确不做

- 不实现 Piper 旁白（缺 voice 模型，记 BLOCKED）；
- 不启用付费/远程 ASR；
- 不降低对齐与质量门。


## ADR0080 裁定后的修订（2026-10-25 22:00）

架构裁定见 `docs/decisions/0080-local-speech-evidence-minimum.md`。要点：

1. `utterance_verified` **不要求** `precision.measured`、**不要求** CTC；要独立测量的是 0.3 的 `alignment_evidence_policy`（`qualified_method_runtime_v1` 允许 `not_measured`，`strict_reference_v1` 强制每片 reference）。
2. 本地语音**必须** `AlignmentRevisionV03`；旧 `AlignmentRevision` 必落"必须 measured"硬门。
3. **R1 仍强制注册 CTC**（ADR0075:43 已冻结），whisper 时间戳只能作单位来源并诚实标注，单独不可发布。→ **需要 torch/whisperx 运行时与 `alignment`/`qualified_local_forced_alignment` 资源段**（`providers/local_alignment.py:79-118`）。
4. 字幕不额外强制 CTC/measured，只受 alignment 门与精确序列化字节约束。
5. **真正的总阻断：evidence policy/qualification/benchmark 准入缺失** —— 无 policy 即 `alignment_required` 409（`evidence.py:373`）；`install` 需 `EvidenceAdminCapability` 且要 `EvidenceApproval` 签名（`evidence.py:101-141`），仓库无任何准入入口与可信 issuer。**准入前 whisper 与 CTC 都无法发布语音作品。**

### 修订后的缺口（按归属）

| 角色 | 缺口 |
| --- | --- |
| 集成 | ① ASR 资源包（已有模型，需清单/route）；② 锁 `faster-whisper==1.2.1`/`ctranslate2==4.8.3`/`av==18.1.0`；③ **CTC 运行时（torch/whisperx）** 与 `alignment` 资源段 |
| 后端 | ① dev 放开 ASR 四字段（已实现，待真实清单验证）；② `delivery_requirements=None` 的 AttributeError 具名化；③ **evidence 准入入口**（可信 issuer + policy/qualification/benchmark 安装），这是发布总开关 |
| 媒体 | ① `_speech_error` → 真实路径；② 三份新材料槽 `actual_transcript_local`/`srt_local`/`vtt_local`；③ 真实 `audio_mappings` 与 `asr_operation_id`；④ `alignment_registration` **不可为空**（R1） |
| 测试 | 按 ADR0080 §6 正负例；缺资源记 BLOCKED，不得 mock 通过 |

### 明确后继（不做）

零 cue、no_speech 发布、audio-only、Piper 旁白、`word_verified`、whisper 方法资格。


## 用户决定（2026-10-25 23:05）——C 的拍板结果

1. **证据签发方：本地安装实例自签**。由本机 Owner 通过产品内授权签一份**仅本机、零成本、不出网**的作品证据策略；界面必须明确标注"本地自签、未做精度实测"，不得对外表述为第三方认证或官方合规。
2. **对齐方法：whisper 时间戳**。不安装 CTC（torch/whisperx）；允许 whisper 分段/词级时间戳作为本地方法，需修订 ADR0075 中"R1 强制注册 CTC"的条款，并在证据中诚实标注 `whisper_word_estimate_not_forced_alignment`。
3. **精度：`not_measured`**。不编造 N/P95，不生成独立 reference；发布允许，但报告写"未测量"。

### 由此产生的实现顺序

- 前置：产品内授权（ADR0081，进行中）——"Owner 签自签策略"这一步必须走那条通道，不再用终端。
- 架构：新 ADR（本地自签证据策略 + ADR0075 修订）。
- 后端：自签策略/资格/基准的安装入口（仅本地、仅零成本、仅本机 Owner、审计；不得允许远程或付费能力）。
- 媒体：`_speech_error` → 真实 whisper 路径（转写、字幕、RAG、`audio_mappings`、`asr_operation_id`）。
- 测试：真实 WAV → 0.4 包；断言 `not_measured`、字幕字节、mapping 逐 piece；负例见 ADR0080 §6。

### 明确不做（本次）

CTC、word 级认证、第三方认证、官方合规表述、Piper 旁白、audio-only、零 cue。


## 2026-10-26 01:20 真实链路到达证据门（实测）

真实 run `run-277a1a8e2dab40a4a41207f0a8d1c9bc`（production `production-60e44d2718394eb9898104d8573c5781`）事件：

```
… step.started → operation.prepared → dispatch_intent → observed → step.completed
→ bundle.prepared → production.final_assembly_committed → run.recovered
code = alignment_required
message = "Speech publication needs an explicit 0.3 evidence request with admitted requirements."
```

即：真实 ASR（注册 operation、settled）、转写、字幕、语音证据、装配与提交全部通过，**只剩证据策略解析**。

### 已裁定的产品行为（待后端实现）
本地 profile 在"已安装并启用自签 policy"时**自动解析该实例策略**，不要求客户端拼 0.3 `delivery_requirements`；未安装/验签失败/过期仍 `alignment_required` 409（默认关闭语义不变）；非本地 profile 不变。

### 今天暴露的"模块间隐含约定"清单（应写入各角色 Handoff）
1. 角色名必须来自 `MASTER_ORDER`/`OutputRole` 常量，禁止简写（`mixed` ≠ `mixed_audio`）。
2. `DOCUMENT_PATHS` 白名单必须包含语音三材料，否则会误报"静音作品"。
3. artifact 依赖必须单向 DAG：script→plan→selection、mixed_audio→transcript→{srt,vtt}→speech evidence。
4. bundle 级 ASR operation 的 `step_key` 必须是后端 `asr_result_journal.STEP`，`dedupe_key` 必须是 `bundle-asr-<run_id>`。
5. SQLite 布尔/整数列一律用值比较（`in (1, True)`），禁止 `is True`。
