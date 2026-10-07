# VideoCreator

安装实例持有数据的视频创作工具。开发目标为 R1 本地创作与 API/MCP 后，连续实现 R2 可选官方服务；五步工作台：建项目 → 定方向 → 看方案 → 制作 → 成片。

当前正在 Gate0 验证。目录骨架不是功能完成证明。实际启动、测试与平台支持以 `docs/acceptance/criteria/COMMANDS.md`、架构冻结记录和独立验收报告为准。

## 开发边界

业务源码由后端、前端及 Agent/媒体角色维护，依赖/锁文件/构建及安装由集成角色维护。原始规格在 `G:/开发测试/Documents/VideoCreatorSpecification/`，执行过程在 `G:/开发测试/Codex/VideoCreatorImplementation/`。

Node 24 LTS 是构建候选；Python 3.13、Tauri 2、CrewAI、FFmpeg 的精确版本由 Gate0 实测后冻结。本地模式不依赖官方账号。
