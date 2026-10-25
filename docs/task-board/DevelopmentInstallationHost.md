# DevelopmentInstallationHost

统筹任务卡，2026-10-25。角色：架构 → 后端 → 集成 → 测试 → 评审，按顺序单槽执行。

## 背景与目标

当前唯一能产出真实作品的路径 `RegisteredMediaRuntime`（`application/media_registration.py:126`）要求安装器签发的完整注册与 native 资格链：`engine.production_admissions.current_guard` 需要 `installation_authority.observe() -> InstalledProductionEvidence` 且 identity 已注册（`production_admissions.py:182-203`）。native 宿主（`apps/desktop/src-tauri`）从未编译，因此开发检出无法跑出任何作品包。

目标：新增一条**显式、非生产**的本地安装资格路径（Development Installation Host），使开发检出可以用真实文件、真实哈希、真实 ffmpeg 跑通 `local-v1` 注册的本地制作到 0.4 作品包，并保留全部现有生产门：正式安装/资格/注册代码路径不变，dev 路径必须显式启用、可被审计、在冻结产物中不可用。

用户已授权：路线 A（Python 开发宿主）；过程按仓库原角色流程（架构设计 → 实现 → 集成 → 测试 → 独立评审）。

## 固定输入（实施前必须读完）

- `application/production_admissions.py:91-330`：`ProductionAdmissions`、`register_execution_identity`、`current_guard`、`_installation`、`_issued_guard` 的实际协议。
- `application/owner_services.py:101-175`：`assemble_owner_services` 的装配与校验（8 字段 execution_registration）。
- `application/native_installation.py`、`application/local_installation_authority.py`：现有 authority 形态与 `InstalledProductionEvidence` 要求。
- `application/media_registration.py`：`RegistrationConfigLocalV1` 分支、`_initialize_local_runtime`、`_current_services`、`_final_producer`。
- `domain/local_material_production.py:50-135`：`RegistrationConfigLocalV1` / `LocalRegistrationV1` / `LocalMaterialResourcesV1` 字段。
- `cli/startup_services.py:56-91`：`install_startup_services` 对 factory 返回对象的硬校验。
- `cli/main.py:117-290`：`serve` / `worker` 入口与 `installed_service_factory` 注入点。
- ADR0005、ADR0014、ADR0016、ADR0036（`docs/decisions/`）。

## 必须满足的约束

1. 生产路径零行为变化：不修改 native 校验、不放宽 `production_admissions` 对正式 identity 的要求；dev 资格对象只在显式 dev 入口构造。
2. 显式启用：必须同时满足（a）CLI 显式参数指向 dev 注册文件；（b）环境变量 `VIDEO_CREATOR_DEVELOPMENT_INSTALLATION` 等于该实例 id。缺一即拒绝。`getattr(sys, 'frozen', False)` 为真时一律拒绝（打包产物无 dev 路径）。
3. 真实证据：`InstalledProductionEvidence` 的 `engine_source_sha256` 与 `indexed_resource_sha256` 必须由实际磁盘文件哈希得出，`observed_at_us` 为真实时钟，`assert_current` 必须重新核对持有文件（不能只信配置）。
4. 不新增 DB 表、不改迁移；dev 资格不写入 `installation_qualification_*`。
5. 文本 UTF-8/LF；只写各角色白名单路径。

## 交付顺序与验收

| 阶段 | 角色 | 产物 | 验收 |
| --- | --- | --- | --- |
| 1 | 架构 | `docs/decisions/00NN-development-installation-host.md` + `docs/architecture.md` 增补 | ADR 冻结 dev/production 边界、CLI 入口、对象协议、失败语义 |
| 2 | 后端 | `cli/development_host.py`、`application/development_installation.py`、`cli/main.py` 接线 | `serve-dev` 能起 API 且 health 标明 `local-development`；生产 `serve` 不变；dev 未启用时拒绝 |
| 3 | 集成 | 由 203 文件资源包生成本地注册配置与资源/运行时清单 | 配置通过 `RegistrationConfigLocalV1` 校验，哈希齐全 |
| 4 | 测试 | `tests/development/` 端到端测试：一图 + 固定时长 → 真实 ffmpeg 渲染 → 0.4 作品包 → 可播放 mp4 | 实际退出 0，产出文件经 ffprobe 校验，事件流与账本可查 |
| 5 | 评审 | `docs/reviews/` 独立报告 | 仅评审 1-2 阶段源码；不改代码 |

真实链通过标准（测试角色必须逐条给证据）：
- 一次真实生产从 `queued` 走到 `succeeded` 或明确的 `waiting_user`（若需人工审核，测试必须实际提交审核决定后继续）。
- 生成 `BundleManifestLocalV1`（0.4）且 `bundle_ref` 非空。
- 产出 mp4 可由系统播放器/ffprobe 读取，时长与请求一致。
- 全程无 mock 媒体、无伪造哈希；模型调用为 0（本地素材链不需要模型）。

## 允许的取舍

- 允许 dev host 只服务 `local-v1` 注册（本地素材链），不支持 v2/v3 生成式。
- 允许第一版只支持 human（interactive）模式；unattended/policy 模式留后继卡。
- 允许 ASR/TTS 为空（纯视频、无字幕），但必须走真实的"无语音"合同分支，不得伪造字幕条目。

## 停止条件

- 若发现必须修改 `ProductionAdmissions` 的正式校验语义才能跑通，停止并回报统筹，不得自行放宽。
- 若 203 资源包与本机 ffmpeg 版本不一致导致真实渲染失败，保留原始失败并回报，不得换成系统 ffmpeg 冒充同一注册。


## 2026-10-26 02:50 新增两张卡（R1 收尾前置）

### 卡 A：installer-admin provision（供给实现）
按 ADR0083 实现 `installer-admin provision`：一次性、无监听、不装配 OwnerServices、不建 management secret；从已落盘字节实算注册并逐件写清单；写实例 ACL、迁移、Owner 项目、**空 production floor**、五条路由行、`InstallationProvisioning.json`。
验收：V1–V11（ADR0083 §验证）在真实安装实例全绿，并把命令与输出登记到 `docs/acceptance/criteria/COMMANDS.md`。

### 卡 B：ProductTrustedStartupAuthority（产品受信启动权威）
背景：frozen 引擎无 factory ⇒ `install_startup_services(None, …)` ⇒ 制作 403 `production_authorization_unconfigured`，工作台只能浏览。R1 需要产品形态的执行权威。
要求：由**安装记录 + 实例 ACL + 注册钉定（registration sha / 资源清单 sha）**构造；禁用 dev 三重条件、禁用环境变量/配置文件直接构成 authority；失败具名；与 ADR0081 的重启语义配合。
先由架构出窄设计，再由后端实现，测试在真实安装实例验证"可制作/不可越权"两侧。
