# 当前真实能力清单（2026-10-25 19:20，可核）

目的：只写**能自己复核**的事实，不写完成度百分比、不写预计时间。每条都给复核命令或文件。

## 一、已经有真实证据的

| 能力 | 证据 | 你自己怎么复核 |
| --- | --- | --- |
| Gate0 测试基线全绿 | 169 passed / 4 skipped / 0 failed / 0 error | `cd Projects/VideoCreator && .venv/Scripts/python.exe -m pytest tests/gate0 -q` |
| 本地注册切片可构造真实运行时 | 189 源逐哈希、209 文件资源、四条 route；`RegisteredMediaRuntime` 构造成功 | 跑 `Integration/LocalInstallationRegistrationBuild/check_local_registration.py --out . --runtime` |
| 开发宿主可启动并授权 | `serve-dev` → `ready`；Owner 绑定 + `Control/DevelopmentOwnerInitialization.json` 审计；`/health` 带 `local-development` 头 | 看 `Instance/ChainInstance/Control/` 目录与 `Metadata.sqlite` 的 `owner_management_binding` |
| 素材真实导入 | PNG 10440 B，经包内 ffmpeg 真实解码（`tool_version n9.0.2-22`） | `ProductionRuntime` 旁的 Objects/Staging 与 API `/assets/{id}` |
| 受理与审核 | production 受理 → script/plan 生成 → `review.required` → `review.decided` | 事件流 `GET /runs/{id}/events` |
| **第一个真实镜头渲染完成** | `step.started → operation.prepared → operation.dispatch_intent → operation.observed → step.completed`（route `local.input-visual.ffmpeg-v1`） | 同一事件流 + `operations` 表该行 `settled` |

## 二、有代码但没有证据的

| 能力 | 状态 |
| --- | --- |
| 本地 0.4 最终生产者（`local_bundle_producer.py`） | 源码完成、独立评审 P1 已闭环；**从未发布过作品包** |
| 合成（masters）/质量证据/最终装配 | 源码存在；`production-edit` 步骤尚未成功跑过 |
| 独立评审 | 本批修复正在评审（`RV-LocalChainRealRunFixes`），尚未出结论 |

## 三、明确没有的

- **作品包（0.4）与可播放 mp4**：没有。
- **配音 / 转写 / 字幕 / RAG**：运行环境无 ASR/TTS 模型，未跑过。
- **HTTP/MCP 单次调用到完整交付**：未验证。
- **任何安装包**：只有 PyInstaller 内部引擎候选（825 MB，`--help` 可运行），无 Tauri、无签名、无安装器。
- **发布到抖音/小红书**：零实现。
- **官方账号/订阅/额度**：`services/control-plane` 为空。
- **模型设置界面（FR02）**：后端有机制，界面未接通。
- **CI**：`.github/workflows` 为空。

## 四、当前未提交/未评审的改动（真实风险）

分支 `recovery/local-chain-20261025`：
- `292b615` wip(engine)：dev owner 自动初始化、受理分派、6 个运行期修复
- `5522f01` wip(media)：派生步骤请求体统一为 JSON 形态

**两笔都标注为 WIP、未经评审。** 独立评审进行中。main 分支停在 `6aaa0dc` + tag `checkpoint/2026-10-12-local-v04`。

## 五、已知缺陷（不修就会反复撞）

1. `OperationExecutor` 对非零成本驱动异常仍统一吞成 `unknown`（对本地零成本已改为重抛）——诊断性仍弱。
2. worker 日志在 Windows GBK 控制台下被 CrewAI 的 emoji 事件刷屏，`'gbk' codec can't encode` 大量噪声，影响排障。
3. 注册文件与源码哈希强绑定：任何引擎源码改动都必须重生成注册，否则 `development_code_changed`。开发期这点会反复咬人。
4. 本地档案与云端全量档案的差异还有若干已知门（四母版、8 输出、证据策略已处理；`unattended`、`audio-only`、`zero-cue` 仍未处理）。


## 2026-10-25 21:40 更新：静音成片已真实验收（证据）

| 能力 | 证据 | 复核方式 |
| --- | --- | --- |
| 真实端到端成片（静音 3 秒） | `production-1d22330e09ed4557975f26f6b4a609a0` → **succeeded**；bundle `local-bundle-revision-e362c12a…`；manifest `0.4.0-candidate` / `local-material-bundle-v1`，13 个 artifact | `GET /api/v1/productions/{id}`、`GET /api/v1/bundles/{rev}/manifest` |
| 视频真实可播放 | h264 1080×1920 / 25fps / 75 帧 / 3.000000 s / 8,316 B；磁盘对象 SHA = manifest SHA = API 下载 SHA `ae433171…`；解帧内容为上传静图 | `ffprobe`、`GET …/artifacts/{id}/content`、解帧比对 |
| 两次人工审核真实生效 | plan 与 quality 各一次 `ReviewDecision`（经 API 提交） | 事件 `review.required/decided` |
| 本地 ASR 运行时（链外） | faster-whisper-small 在盘；SAPI 合成 6.29 s 中文 WAV → 正确转写 | `LocalSpeechPipeline.md` 实测段 |

仍未完成：带音频/字幕/转写/RAG 的作品包、Piper 旁白（缺 voice 模型）、HTTP/MCP 单次交付、安装包、发布、官方订阅、模型设置界面、CI。

## 2026-10-25 21:45 评审状态

`7a32420` 批次独立评审：**LIMITED_PASS_WITH_P2，无 P1**；明确结论"未发现未批准/其它 Run/篡改输入可发布作品包的路径"。P2 处理中：同 Run 审批已显式化（`bundle_approval_conflict`）；权利/重入/有序/identity 的定向回归测试随语音链补。


## 2026-10-26 02:10 真实语音作品发布（证据）

| 项 | 值 |
| --- | --- |
| production | `production-2f621e4e2d9946a19d8f1d102e7e1953` → **succeeded** |
| 作品包 | `local-bundle-revision-80ff2155…`，manifest `0.4.0-candidate` / `local-material-bundle-v1`，17 个 artifact |
| 输出 | video、mixed_audio、actual_transcript、subtitles、semantic_manifest、rag_chunks |
| 视频 | h264 1080×1920 + **aac 48 kHz**，6.280 s；`Media/mixed-audio.wav` |
| 转写 | 1 utterance、6,280,000 µs，文本与音频一致（ASR 原样，未修改误识） |
| 字幕 | srt/vtt 同源序列化，quantization errors 全 0 |
| 证据诚实性 | `units=utterance`、`timestamp_method=whisper_word_estimate_not_forced_alignment`、`precision.status=not_measured`、N/P95/reference 全 null |
| 成本 | CNY 0 |

### MCP 路径（新发现，进行中）
MCP `production_create` 可创建 production，但实测发现：① MCP 启动时 `media_validator_missing`（同样的 ffmpeg 路径在 serve-dev 下可用）；② 该 production 直接出现 quality 版本、无 plan 步骤；③ MCP 没有暴露"列出待审版本"的工具，客户端无法取得 revision id 去 decide。已列为 R1 缺口并派给后端。


## 2026-10-26 02:32 MCP 单次交付闭环（真实 JSON-RPC）

| 步骤 | 真实结果 |
| --- | --- |
| `initialize` / `tools/list` | 15 个工具（含新增 `production_revisions`） |
| `production_create` | `production-579acf93…` / `run-9d72ecc0dec34cfe8cc6c030fa56708b` |
| `production_revisions` | 发现 `script`、`plan`、随后 `quality` |
| `production_decide`（plan） | 同意成功 |
| `production_decide`（quality） | 同意成功（另有一次对已消费版本的重复决定被 `revision_conflict` 正确拒绝） |
| `production_get` | `succeeded`，bundle `local-bundle-revision-bc6b34ea…` |
| `bundle_get` | `0.4.0-candidate`，输出 video/mixed_audio/actual_transcript/subtitles/semantic_manifest/rag_chunks |
| 产物复核 | 视频 h264 + **aac** 音轨、6.280 s |

原始 JSON-RPC：`Dsh/MediaOsContext-20261025/mcp/delivery-rpc.jsonl`。

### 同时确认的设计事实
新装实例经产品内授权后仍无 ffmpeg/ASR 路由（`route_unavailable`）——**注册路由是管理动作，产品内授权刻意不授予**。因此安装器/受信启动必须先完成一次"管理性供给"，之后用户只需在产品内确认 Owner。这条需要单独立卡（安装器供给），并影响 R1 的安装包设计。
