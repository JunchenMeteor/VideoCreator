# Media — 本地中文对齐驱动与初始方案 v2 的实现续接

状态：QUEUED；原 agent_media；仅在 Architecture 当前 a3766d2 的真实停止交接、读者释放及统筹核对完成后占用其释放的槽位。不启动第五角色。

目标：继续未完成的 343d2a 与 5c923f2c，不以 Media37 源码阶段替代完整创作能力。完成实际本地对齐驱动及 0054 初始方案 v2 消费；保留 R1→完整 R2 总目标。

固定输入：停止的 Media37 Handoff ac9c33af1854defe51dd5ee639f83dfeede4ef877f345c742b7e3b03381e5d53；Factory c274fc51d69f47b42a2de6d13e3a60df18ff09298f5aa353b044f95fa993d79f；Backend PlanTargetsAbi Interfaces cabd6b2d51b3293312db7434fc8c430f9239244cd00a87155b419e6a8fc175bc，SourceIndex 07cf108fb8866d6c014862c4132940c30e6fec7de2652da41ed18e6f22388472；ADR0054 615fff067a1a377b6f16a4d3a7e671b853a24d59350f9b170faa03786d4c7797。0055 及其完整实现合同/资源计划仅在真实停止后由统筹另附精确身份；不得读热 ADR 或猜测接口。

白名单：仓库 services/engine/src/video_creator/workflows、providers、media 下生产源码；过程材料仅自身 AgentMedia 任务目录。依赖清单/锁文件/构建配置归 Integration，公开交接类型归 Backend，测试归 Test。

实施：实际 rights/script/storyboard 提交后调用原 prepare_plan_repair_targets，构成原 RegisteredProductionPlanV2，整份计划交原批准入口；旧计划恢复不得补写审批。按冻结 0055 实现真实音频+源稿驱动的中文 CTC 对齐，资源身份检查、有限子进程输入输出、整数微秒/半开区间及失败/取消语义。不得用字数摊时、评价参考边界或假 READY。驱动与现有受控制作/质量/局部修订接入，同一路径继续观察、子级资产、转写和作品包，不复制授权与账本。

本卡授权源码实现、AST/Ruff 等不导入业务的静态检查和完整源码交接；不授权模型/包下载、安装、推理、Pydantic/product/SQL/ASR/native/provider 运行、密钥、收费、提交或部署。实际资源与三平台资格验证交 Integration/后续独立测试。Intel Mac 仍必需；源码生产路线、200ms 精度、内存和分发条件未验证必须保留，不能缩范围或降低阈值。

证据：保留既有红结果与保护方法；实际命令、退出码、修改范围、完整停止源码快照/差异/合同及 Handoff。无模型资源时如实报告未就绪，源码完整也不计真实创作通过。下游由独立 Review/Test/Acceptance 验证；只回滚本阶段归属变更，不改其他角色源码或冻结输入。
