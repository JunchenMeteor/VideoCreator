# LocalInstallationRegistrationBuild

统筹任务卡，2026-10-25。角色：集成/发布（原 integration_release）唯一写入者。前置：`LocalFinalProducerBundleV04` 的源码已合入（否则哈希会变，需重跑本卡）。

## 目标

由**当前产品源码**重建一份可被 `RegistrationConfigLocalV1` 接受的本地安装注册切片，并给测试角色一套可复现的生成脚本：资源包（Code/Media/Migrations）+ 运行时索引 + 注册配置 + 四条本地路由 + 权利声明。

## 为什么必须重建（统筹实测）

- `Codex/.../LocalOwnedMaterialPackageResources/PackageBuildRoundOne` 的 `Code/` 是 10-12 的停止快照；`RegistrationConfigTemplate.json` 只有 178 个源，当前产品源码 183 个，其中 18 个哈希已变。
- `providers/local_material_resources.py:60-66` 要求每个 `implementation_source_refs` 的哈希等于资源包内实际文件；`media_registration.py:141-146` 要求 `engine_source_sha256` 的键集合**恰好等于** `_package_sources(PACKAGE_ROOT)` 的当前集合，逐个哈希匹配。
- 因此直接把旧模板给引擎会在 `production_engine_incomplete` / `local_source_changed` 处失败。

## 产出物（写入 `Codex/VideoCreatorImplementation/Integration/LocalInstallationRegistrationBuild/`，不进仓库）

1. `build_local_registration.py`（或 .ps1）：幂等生成下面全部内容；只读产品源码与 203 资源包里的 FFmpeg 二进制，不联网、不安装。
2. `Package/`：`Code/video_creator/**.py`（当前源码完整拷贝）、`Migrations/*.sql`（11 个）、`Media/FFmpeg/bin/{ffmpeg,ffprobe}.exe + 7 个 DLL`、`Media/FFmpeg/LICENSE.txt`。
3. `Package/RuntimeFileManifest.json`：`format=local-material-runtime-files-v1-candidate`，逐文件 `relative_path/bytes/sha256`（相对 `Package/`）。
4. `Package/LocalMaterialResources.json`：`registered-local-material-resources-v1`，`runtime_manifest`、三段 `implementation_source_refs`（`kind` 分别为 `uploaded-audio`/`owned-material`/`ffmpeg`，edit 段含 `ffmpeg`/`ffprobe` 相对路径），引用的每个文件必须同时出现在 RuntimeFileManifest。
5. `Registration.json`：`registered-media-config-local-v1`，字段齐全（`engine_source_sha256`/ffmpeg/ffprobe/asr 全 null/资源清单+两 sha/`local_registration`/`alignment_registration: null`），其中 `local_registration.rights_declaration` 用真实 owner 与项目 id，`max_duration_us` 与测试计划一致。
6. `Routes/*.json`：四条 `CapabilityRoute`（`source=owned_local`、`credential_ref=null`、`max_operation_cost=0`、`destination=local:*`），能力分别覆盖 input audio / input visual / edit / master index，id 与 Registration 中一致。
7. `Receipt.json`：输入集合、每步命令、exit、产物 SHA，以及"哪些文件来自旧停止包、哪些是现算"的清单。

## 硬约束

- 不使用旧 `Code/` 快照冒充当前源码；不用系统 ffmpeg 冒充包内二进制；不下载。
- 所有文本 UTF-8/LF；不复制 `.ssh`、凭证、密钥、`node_modules`、`.venv`。
- 不改仓库源码、不改依赖锁；只写自己的过程目录。
- 若发现当前源码中有文件无法被 `_package_sources` 收录（例如新增目录层级），如实报告，不要裁剪集合去凑。

## 自测（必须真实执行）

1. 用 Python 直接 `parse_local_material_resources` 与 `RegistrationConfigLocalV1.model_validate` 校验两个清单与注册文件（用仓库 `.venv` 的 PYTHONPATH）。
2. 用 `LocalMaterialResources(manifest_path=..., manifest_sha256=..., runtime_manifest_sha256=...)` 实际构造一次，必须不抛异常（它会逐个核对全部文件大小与 SHA）。
3. 用包内 ffmpeg 跑一次 `-version`，记录 exit 与版本串。
4. 把上述命令与原始输出写进 `Receipt.json`。

## 交付

`Handoff.md`：注册文件路径与 SHA、四条 route id、权利声明内容、`max_duration_us`、包内文件数/总字节、自测 exit、以及给测试角色的"一条命令复现"的调用序列。回报 ≤800 字。
不要 git commit。
