# HyperFramesRenderProvider

统筹任务卡，2026-10-25。**状态 QUEUED**：等 `LocalChainEndToEndTest` 真实出片通过后再激活。
用户已定：优先 HyperFrames（不是 Manim）；场景只允许**模板 + 参数**，不允许模型生成任意代码。

## 目标

新增一个确定性的"代码渲染"画面生产者，把模板 + 参数渲染成真实视频母版，接入现有 `local-v1` 制作链（母版 → 0.4 作品包），替代当前缺失的"视频生成模型"。

技术选型依据：`G:/开发测试/.dsh/research/code-video-refs.md`（本机已实测 HyperFrames 0.8.181 + Chrome headless，300 帧/10 秒渲染 13.7 秒）。

## 角色与白名单

- **Agent/媒体**：`services/engine/src/video_creator/{providers,media,workflows}/` 下新增渲染 provider 与 driver，以及模板校验。
- **集成**：把 HyperFrames 运行时、Chrome headless、字体打进资源包并逐文件哈希；新增一条 render 路由的注册样例。
- 模板资产放仓库内 `resources/render-templates/`（需集成确认白名单归属），每个模板文件参与资源哈希。

## 设计约束（先由架构补一份短 ADR，编号顺延）

1. **确定性**：帧数 = `round(duration_us × fps / 1e6)`；模板内禁止 `Date.now()`/随机（需要随机必须固定 seed）；同一模板+参数必须产出同一帧序列哈希。
2. **不做任意代码**：场景 = `{template_id, params, duration_us, fps, width, height}`；参数过模板自带的 JSON Schema；不执行模型生成的 JS/HTML。模板文件本身是受控资源。
3. **受限子进程**：渲染在无网、限时（默认 300 s）、工作目录限定实例内 `ProductionRuntime/` 的子进程里跑；只允许调用资源包内的 `node`、`hyperframes.mjs`、`chrome-headless-shell`、`ffmpeg`；`HYPERFRAMES_SKIP_SKILLS=1`。
4. **真实证据**：渲染命令、exit、stdout/stderr 原始字节、帧序列/产物的 SHA256、ffprobe 结果写入 Operation 结果；产物必须过 `BundleMediaEvidence` 校验才能进作品包。
5. **资源资格**：渲染器与字体必须在安装资源清单里逐文件哈希；缺件返回具名 `render_resource_not_ready`，不降级到系统 ffmpeg 或网络下载。
6. **不加模型调用**：本卡不接 LLM；文案来自请求/脚本（已有 script revision）。

## 交付顺序

1. 架构：`docs/decisions/00NN-code-render-template-provider.md`（模板合同、参数 schema、证据、失败语义、与 local-v1 的接口）。
2. 集成：`RenderResourcePack` 生成器 + 清单（HF/Chrome/字体/node 版本固定），给测试一条复现命令。
3. 媒体：`providers/hyperframes_render.py` + `workflows/` 接线，产出 `video` 母版（可与既有素材镜头混排）。
4. 测试：模板参数负例（非法参数/超时长/未知模板）、确定性（同输入两次渲染帧哈希一致）、真实 3 秒竖屏渲染 + ffprobe 校验。

## 验收

- 同模板同参数渲染两次，产物 SHA 一致（或帧序列逐帧哈希一致）。
- 3 秒 1080×1920 渲染 exit 0，ffprobe 编码/帧数/时长与计划一致。
- 非法参数被拒（具名错误），不触发渲染进程。
- 资源缺件时明确 `render_resource_not_ready`，不联网、不调用系统 ffmpeg。
- 至少一条链路证据：模板渲染的镜头 + 本地素材镜头混排进同一个 0.4 作品包。
