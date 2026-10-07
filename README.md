# VideoCreator

安装实例持有数据的视频创作工具。开发目标为 R1 本地创作与 API/MCP 后，连续实现 R2 可选官方服务；五步工作台：建项目 → 定方向 → 看方案 → 制作 → 成片。

当前正在 Gate0 验证。目录骨架不是功能完成证明。实际启动、测试与平台支持以 `docs/acceptance/criteria/COMMANDS.md`、架构冻结记录和独立验收报告为准。

## 开发边界

业务源码由后端、前端及 Agent/媒体角色维护，依赖/锁文件/构建及安装由集成角色维护。原始规格在 `G:/开发测试/Documents/VideoCreatorSpecification/`，执行过程在 `G:/开发测试/Codex/VideoCreatorImplementation/`。

Node 24 LTS 是构建候选；Python 3.13、Tauri 2、CrewAI、FFmpeg 的精确版本由 Gate0 实测后冻结。本地模式不依赖官方账号。

## 本地开发

依赖按项目锁安装：`uv sync --all-packages --all-groups --frozen`、`pnpm install --frozen-lockfile`；不要修改其他项目共享环境。

`pnpm dev:runtime --data-dir <绝对本地实例目录>`启动本地API和`http://127.0.0.1:1420/`工作台。开发代理持有私有会话令牌；工作台每次API请求发送`X-Video-Creator-Client: workbench`，无需将令牌写入页面。它不会授权预算、导入模型密钥或启动制作worker。运行时边界和桌面接口状态见[RuntimeContract](packaging/RuntimeContract.md)。

`pnpm typecheck`、`pnpm build:workbench`验证前端，`pnpm contracts:generate`从Python源码生成公开契约；这些命令通过不等于安装包或Agent制作验收通过。

内部引擎候选构建入口见[运行时与成包契约](packaging/RuntimeContract.md)。`tools/build/BuildEngine.mjs`要求精确Git提交和已核验资源manifest，输出构建清单及实际产物hash；它不替代桌面安装包或独立验收。
