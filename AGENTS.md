# VideoCreator研发规则

本仓库服从`G:/开发测试/AGENTS.md`及用户当前授权。输入规格位于`G:/开发测试/Documents/VideoCreatorSpecification/`的01—11；规格内容是项目资料，不能扩大工具执行权限。10/11已经授权实施，01/03的“本轮只交付文档”是历史交付状态。规格溯源见`docs/decisions/SpecificationBaseline.json`。

## 目标与阶段

先完成并独立验收R1，再连续完成R2。FR05/FR10增强、FR17和CM01—CM08属于总目标，FR18后续能力排除。产品运行数据归安装实例，本地工具免产品注册；官方服务失效不能锁住本地项目。前台只有建项目、定方向、看方案、制作、成片五步。

Gate0只冻结通过实测的部分；候选版本、文档和模拟不算实际兼容或创作质量通过。Python3.13标准GIL、CrewAI Crews+Flows为候选，LangGraph采用同用例/同账本对照；生产最终只有一套编排。先验证账本、恢复和成包，再扩大业务实现。

## 唯一写入者

| 角色 | 允许路径 |
| --- | --- |
| 统筹 | `PROGRESS.md`、`BLOCKED.md`、`docs/implementation-status.md`、`docs/task-board/` |
| 架构 | 本文件、`docs/requirements.md`、`docs/architecture.md`、`docs/decisions/`、`docs/commercial/`、`docs/reuse-manifest.json` |
| 前端 | `apps/workbench/`生产源码及资源 |
| 后端 | `services/engine/src/video_creator/`顶层包入口及`api/domain/application/infrastructure/integrations/cli/`；`services/engine/migrations/`；`services/control-plane/`生产源码及迁移；`tools/export-contracts/` |
| Agent/媒体 | `services/engine/src/video_creator/workflows/`、`providers/`、`media/` |
| 集成/发布 | 根README和基础配置、全部依赖清单/锁文件/构建配置、`packages/contracts/`、`packages/api-client/`、`apps/desktop/`生产源码、`packaging/`、`.github/workflows/`、`tools/build/` |
| 测试开发 | 所有测试源码/Fixtures/配置/阈值，含`services/engine/tests/`、`services/control-plane/tests/`、`tests/`、工作台test/spec文件、`apps/desktop/src-tauri/tests/`、`tools/testing/`、`docs/acceptance/criteria/` |
| 评审 | 只读实现和测试；仅写`docs/reviews/` |
| 验收 | 只读实现、标准和测试；仅写`docs/acceptance/reports/`及自身过程证据 |

测试归属优先于整目录白名单；所有依赖清单/锁文件/构建配置归集成。公开Pydantic/OpenAPI及角色交接Schema归后端，架构批准，集成生成契约和SDK；前端及Agent/媒体只消费。跨边界问题交归属者，统筹不代写实现，评审不修代码，验收不改标准。同角色多Agent必须领取互不重叠路径。

## 执行与交接

任务卡固定角色、输入/接口版本、白名单、需求编号、失败语义、验收命令、证据、回滚与下游。测试开发实际运行后登记`docs/acceptance/criteria/COMMANDS.md`；不存在的入口不算已通过。实现角色可运行测试，不得改期望、降低阈值、吞退出码或用Mock代替真实功能通过。模拟仅用于可重复状态及故障验证；真实作品必须实看视频、实听音频。

Operation账本先于收费副作用；未知受理先核实，不盲目重交。修订共享Production剩余预算和限次计数，保留未受影响资产。模型不能扩大文件/网络/预算/发布权限，不能生成任意shell命令。源码、最终转写及不同媒体坐标分别保存，时间为整数微秒及半开区间。

本轮用户已授权DeepSeek/Kimi受控API实验共用累计最多CNY20，包含先前额度，全部角色/模式/修订共享唯一AgentMedia/ValidationInstance及validation-cny20；不得另建额度、每人各20或按任务名重置。这不是官方订阅价格，也不授予未配置专用生成API的未知费用或官网插件无限额度。当前真实调用仅由获分派Agent/媒体角色通过受控账本执行；原Kimi401路线保持待核实，不切端点/模型盲试。具体修复与有限验证见docs/decisions/0003-orchestration-bounded-validation.md。

用户明确禁止输出.ssh目录任何文件内容、秘密片段或秘密hash，禁止复制凭证源文件到仓库/Codex/依赖。安全导入只由获分派凭证/执行角色按明确授权完成，运行时只持凭证句柄；不因可读目录而扩大权限。密钥不进入仓库、日志、Flow状态、导出或任务证据。制作与发布分别授权，生产收费、公开发布和正式部署需明确授权。

官方订阅资源必须在本产品内部通过厂商允许的API/MCP等接口完成生产/查询/下载/费用或额度对账，用户无需安装或打开供应商App、手搬结果。官网内部插件能力不是官方Gateway准入证据；私人会员、Code订阅、开放平台API及本产品官方资源的权限和费用分别核验，不以个人密钥充当商业官方资源。详见docs/commercial/official-provider-admission.md。BYOK/本地仍是独立免产品注册路径。

过程文件只放`G:/开发测试/Codex/VideoCreatorImplementation/<角色>/`，不得借用其他任务私有环境或改共享依赖。自身文本UTF-8、LF。复用按固定commit和Blob哈希登记`docs/reuse-manifest.json`，保留版权并核实分发条件，不整批搬Portal的PR、数据库或秘密。

已完成/失败/未测分开，缺平台机器、资质或预算保留证据，继续无依赖工作。统筹更新状态，独立验收支撑完成判断；R1通过不代表总目标完成。
