# LocalFinalProducerBundleV04

统筹任务卡，2026-10-25。角色：Agent/媒体（原 agent_media）唯一写入者，后继测试/评审另卡。

## 目标

把本地 0.4 作品包的**最终生产者**真正接上，使 `RegisteredMediaRuntime._final_producer` 的 local 分支可以调用一个真实可执行的 producer，从已批准 plan 的素材生成视频/音轨/封面并按 `BundleManifestLocalV1`（0.4）原子发布作品包。

## 已经确认的缺口（统筹实测）

- `application/current_final_evidence_runtime.py:72-96`：local 分支要求 `create_registered_media_producer(..., local_material_context=...)` 与 `final_evidence_ports=...` 同时存在；若签名里没有 `local_material_context` 直接 503 `production_local_final_consumer_missing`（:82）。
- `workflows/bundle_producer.py:636-666`：`create_registered_media_producer` 当前签名**没有** `local_material_context`，且无条件 `load_asr_resources(resource_manifest_path, ...)`（:641-643）。local-v1 配置允许 ASR 四字段全 null（`domain/local_material_production.py:77-89`），因此现在 local 路径必然在 ASR 资源加载处失败。
- `produce` 返回的函数只接受 v2/v3 的 `video_asset_id/narration_asset_id/mixed_asset_id/cover_asset_id`（:646-656），而 local 调用方传的是 `selection`+`media_roles`（`application/media_registration.py:606-608`）。

## 固定输入

- `application/local_material_sources.py:32-45`：`LocalMaterialFinalContext`（plan/plan_revision/quality_revision/两 admission/rights/selection 属性）。
- `domain/local_bundle.py:25-100`：`LocalMasterSelectionV1`、`select_local_masters`、`BundleManifestLocalV1` 及 `MASTER_ORDER`。
- `workflows/bundle_producer.py:100-660`：现有 v0.2/0.3 `produce_bundle`、`continue_bundle` 的全部写入/证据/原子性语义。
- `application/media_registration.py:583-611`：local 调用点的准确参数与顺序。
- ADR0075（本地 0.4 作品包）、ADR0076（纯音频时间映射，`docs/decisions/0076-*.md`）。

## 必须做到

1. `create_registered_media_producer` 增加 `local_material_context` 关键字参数；local 模式**不加载 ASR 资源**（不得复用 `load_asr_resources`）；v2/v3 行为逐字节不变。
2. 新增 local produce 入口，接受调用方现有实参（`selection`、`media_roles`、`asr_route_id`、`cancel`、`deadline_monotonic`、`plan_admission`、`production_rights_fact`），返回与现有 produce 一致的 bundle 发布结果。
3. 真实素材生成：静图按 display-hold 的整数帧映射、视频按 source_range 截取、`fit=contain|cover` 生效；音频轨按 timeline 混音；封面从视频或原图真实提取。全部使用 `media/local_material_edit.py` 与 `media/production_edit.py` 的真实 ffmpeg 路径，不新增第二个编码器。
4. 无语音/无音轨必须走**真实**分支：请求字幕而 selection 无 narration 时，实际生成并解析两份零 cue 的 SRT/VTT 材料，绑定 hash/MIME/output，不得写空文件了事；请求转写而无语音时按合同拒绝或给具名 blocker，不许造转写。
5. 0.4 manifest 必须是 `BundleManifestLocalV1`：script/plan/quality 三份同 Run 创作版本、真实媒体资产与关系、`audio_mappings` 按 ADR0076 只用真实视频或混音资产、原子 READY 发布。
6. 失败语义：资源缺失/输入不适用/证据不足分别给具名 `EngineError`（可恢复的用同 Run WAITING），不得静默降级、不得长期 503 当终局。

## 验收（自测，不由本人签验收）

- 纯 Python 静态：改动文件的 `ast.parse` 与目标 `ruff check` 退出 0。
- 真实运行：用 `tools/build` 生成的本地注册配置 + 203 文件资源包，跑一次真实 local 生产，产出可被 ffprobe 识别的 mp4，时长与 plan 一致；把命令、exit、产物 SHA/时长、事件序列写入过程目录。
- 若运行被前置（注册配置/开发宿主）阻塞，先交付完整源码与自测，并在交接中写明准确阻塞点与所需输入，不得声称成片通过。

## 边界

只写 `services/engine/src/video_creator/workflows/`、`providers/`、`media/` 与自身过程目录 `Codex/VideoCreatorImplementation/AgentMedia/LocalFinalProducerBundleV04/`。不改 application/、cli/、tests/、docs/。任何需要改 Backend 接口的，列清单交统筹。
