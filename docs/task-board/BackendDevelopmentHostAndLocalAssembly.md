# BackendDevelopmentHostAndLocalAssembly

统筹任务卡，2026-10-25。角色：后端（原 backend_instance）唯一写入者。设计依据：[ADR0077](0077-development-installation-host.md)（架构已冻结）。前置：媒体已交付 `workflows/local_bundle_producer.py` 与 `bundle_producer.py` 的 local 分支（未提交，勿改）。

## 范围（只写后端白名单）

写 `services/engine/src/video_creator/{application,cli,api}/`。不改 workflows/、media/、domain/、tests/、docs/。

## 任务 A：开发安装宿主（按 ADR0077 实现，不得自行放宽）

1. 新建 `application/development_installation.py`：
   - `DevelopmentLaunchConnection`（含 `context: NativeLaunchContext`、`close()`）。
   - `DevelopmentLaunchBuild`（`close()`）。
   - `DevelopmentInstallationAuthority`：`connection`、`observe() -> InstalledProductionEvidence`、`assert_current(observation)`、`assert_local_current(observation)`、`close()`。evidence 必须由真实磁盘哈希得出；`assert_current` 在 writer 外重哈希 engine 全集与资源全集并逐项比对；`assert_local_current` 只做对象/epoch/thread/closed 检查，禁止 I/O/哈希/DB。
   - 必须**不是** `NativeInstallationAuthority` 类型（避免触发 qualification 分支），且不写 `installation_qualification_*` 表。
2. 新建 `cli/development_host.py`：新增 `serve-dev`、`worker-dev` 子命令；把 argv 改写成现有 `serve` / `worker --workflow registered-media-bundle-v1`，然后调用 `cli.main.main(installed_service_factory=dev_factory)`。
   - 三重条件：命令行给出注册文件、`VIDEO_CREATOR_DEVELOPMENT_INSTALLATION == engine.instance_id`、`not getattr(sys, 'frozen', False)`。任一不满足即拒绝（exit 1 + `{code,message}`），且必须在 `listener.bind` 之前。
   - factory 严格按 ADR 第 8 节顺序；复用 `NativeOwnerServices`（`cli/startup_services.py:74` 的类型门）；失败时先 close authority/build 再抛原错。
3. `api/app.py`：仅当本次是 dev 进程时，`/api/v1/health` 响应加头 `X-VideoCreator-Installation: local-development`。不改 `InstanceHealth`、不改 `mode`、不改 OpenAPI 生成物。
4. **禁止修改**：`production_admissions.py`、`cli/startup_services.py`、`application/native_installation.py`、`application/local_installation_authority.py`、`application/owner_services.py`、`application/media_registration.py`、`domain/contracts.py`。若必须改才能通过，停下回报统筹。

## 任务 B：补 `application/local_bundle_assembly.py`

`application/current_final_evidence_recovery.py:104` 与 `current_final_evidence_service.py:217` 会 `from video_creator.application.local_bundle_assembly import validate_local_assembly`，但该模块**不存在** —— 任何 local 0.4 作品包的最终证据校验都会 ImportError。

实现 `validate_local_assembly(self, lease, row, intent, binding, context, *, author) -> ...`，对 `domain/local_bundle.py:302 LocalFinalAssemblyContextV1` 做真实校验：context 绑定的 plan/quality/selection/media_roles/音频映射/零语音证据必须与同 Run 已提交的创作版本和资产记录逐项一致；缺件给具名 `EngineError`，不得返回伪造通过。先读 `current_final_evidence_service.py:200-240` 与 `current_final_evidence_recovery.py:90-120` 确认调用方期望的返回形态。

## 自测（必须真实执行，保留原始输出）

- 全量 `ast.parse` 通过；`ruff check` 改动文件 exit 0。
- 负例：在无 env / env 不匹配 / 伪造 frozen 三种情况下，dev 入口分别拒绝且不绑定端口。
- 正向：用临时 data-dir + 一份**故意哈希不符**的注册文件启动 `serve-dev`，必须得到 `development_code_changed` 而不是崩溃或静默通过（证明校验真的在跑）。
- 说明本机当前没有可用的完整注册文件（集成角色正在生成），因此 positive path 留给测试角色；不要伪造注册文件通过。

## 交付

过程目录 `Codex/VideoCreatorImplementation/Backend/BackendDevelopmentHostAndLocalAssembly/` 下 `Handoff.md`：文件清单、关键签名、三重条件实现位置、负例原始输出、任务 B 的校验规则与返回形态、未完成点。回报 ≤800 字。不要 git commit。
