# LocalChainEndToEndTest

统筹任务卡，2026-10-25。角色：测试开发唯一写入者。前置：后端开发宿主 + 集成注册切片已交付。

## 目标

在**真实**本地安装切片上跑通并留证一条端到端创作链：`素材（静图/视频片段）→ plan 审核 → 真实 ffmpeg 母版 → quality 审核 → 0.4 作品包 → 可播放 mp4`，全程只经产品入口（`serve-dev` + `worker-dev` + HTTP API），不使用 mock 媒体、不伪造哈希。

## 允许写

`tests/development/`、`tools/testing/`、`docs/acceptance/criteria/COMMANDS.md`（登记实际命令与结果）。不改产品源码。

## 必须覆盖

1. **端到端主链**（一个 pytest 用例 + 一个可重复脚本 `tools/testing/RunLocalChain.ps1`）：
   - 准备实例目录：`icacls <dir> /inheritance:r` + 授权当前用户与 SYSTEM（`infrastructure/owner_identity.py` 要求 owner 为当前 SID 且无其他可写主体）。
   - 用 `EngineService`/API 创建项目（Owner scope 需要真实存在的 project id）。
   - **人工前置**：`owner-init initialize --owner-subject local-user --project-id <id> --expires-at <ISO8601>` 必须在真实 TTY 中执行（脚本检测缺少 binding 时打印该命令并跳过/失败，不得绕过）。
   - 注册四条 local route（集成给 JSON）。
   - `worker-dev` + `serve-dev` 启动；API 受理 production（`interactive`、`outputs=["video"]`、`policy.allowed_provider_routes` 含四条 route）。
   - 在 `waiting_user` 时对该 plan revision 提交 `approve` 决定；再对 quality revision 提交 `approve`。
   - 断言：production 终态、`bundle_ref` 非空、manifest `schema_version=0.4.0-candidate`、mp4 经 ffprobe 校验（编码/时长/帧数）、事件序列包含 accept/review/bundle 关键事件、Operation 账本无 unknown。
2. **负例**：
   - dev 三条件各缺一次（无 env / env 不匹配 / 参数缺失 exit 2）。
   - 生产 `serve` 不返回 `X-VideoCreator-Installation` 头；dev health 返回该头。
   - 改动任一 engine `.py` 后启动 worker-dev 必须 `development_code_changed`，且不得被 park 成 `resource_not_ready`。
   - 注册文件改成 v2 格式 → 拒绝码符合 ADR0077 §6。
3. **证据登记**：`docs/acceptance/criteria/COMMANDS.md` 追加一节，写实际命令、exit、产物 SHA、ffprobe 输出、环境（Python/ffmpeg 版本）。

## 约束

- 测试不得调用模型、不得联网、不得使用系统 ffmpeg 替代注册包内 ffmpeg。
- 需要人工前置时，用 `pytest.skip` + 明确提示，**不得**伪造 owner binding、不得 patch `isatty`、不得预写确认答案。
- 一次真实运行的全部原始输出保存在 `Codex/VideoCreatorImplementation/Test/LocalChainEndToEnd/`。

## 交付

`Handoff.md`：用例清单、实际运行命令与 exit、通过的用例数、真实产物路径与 SHA、未通项与原因、给评审的核对点。回报 ≤700 字。不要 git commit。
