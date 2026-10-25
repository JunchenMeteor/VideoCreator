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
