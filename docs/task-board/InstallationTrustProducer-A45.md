# InstallationTrustProducer-A45

- 状态：ASSIGNED；阶段：Gate0/R1安装及同实例生产接线；唯一角色：集成/发布。
- 总目标：完整R1独立验收后连续R2；数据归安装实例，本地免账号，前台五步。本任务不是阶段验收。
- 前置：ADR0044正式FINAL；读取工作区及仓库AGENTS、规格10/11及相关01—09、PROGRESS和BLOCKED后续跑。
- 固定设计：docs/decisions/0044-installation-qualification-contract-closure.md，SHA256 2731ca4ca38dae284ff628269f226f8f4c48eb080c5e614f676eb54248c33e8e；Architecture/QualificationContractClosure-A45/Handoff.md及json为正式交接。以当前精确源码为准记录起点commit及完整输入哈希，不借用历史副本假装当前。
- 只写：apps/desktop/生产源码、packaging/、tools/build/、根基础配置及全部依赖清单/锁文件；自身Codex/VideoCreatorImplementation/Integration/InstallationTrustProducer-A45/。测试源码归测试角色；禁止后端、媒体、工作台业务、规格或其他项目写入。
- 产物：实际InstallationTrustProducer/Prepared/Bound强成员、独立安装信任确认及同原子进程绑定；固定owner-setup-trust计划与seq3；独立installation-trust-admission管道；原Registry及真实资源持有的v2精确14字段begin/end RW lease；原v1兼容。补齐cryptography直接依赖及实际打包闭包，不把包自身密钥当独立来源。
- 与Backend并行：先交具体ABI/文件/调用接口，再按ADR0044唯一合同实施；不可另发明协议、callback/布尔资格或第二Engine。遇跨白名单问题交归属者。
- 成功条件：真实生产源接线可审查，实际运行检查有完整原始输出；缺独立信任材料/真实套件/机器时保留NOT_READY，不能制造资格、记录或报告。
- 验证：先固定真实工具、argv、读写闭包及输入索引，再执行本角色可用构建/静态/已有定向测试；不得重跑无关已绿检查、改测试或隐藏失败。每个自身process/session/cell由自己持续跟踪到真实terminal与双EOF，观察超时不重启。
- 费用/权限：无新付费、模型/密钥探测、全局安装、公开发布或正式部署授权；不读输出或复制.ssh秘密。默认不产生外部副作用。
- 交接：完整Handoff、源码/补丁/输入输出SHA、实际命令退出与失败、能力及未测矩阵、回滚仅本阶段变更；FINAL前确认所有自身工具及读写者释放。下游Backend、Test、独立Review及Acceptance。
