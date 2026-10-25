# InstallationTrustConsumer-A45

- 状态：ASSIGNED；阶段：Gate0/R1安装及同实例生产接线；唯一角色：后端。
- 总目标：完整R1独立验收后连续R2；安装实例持有数据，本地免账号，前台五步。源码完成不等于验收。
- 前置：ADR0044正式FINAL；读取工作区/仓库AGENTS、规格10/11及相关01—09、PROGRESS/BLOCKED。原DailyIntentWriterStage固定89源码已FINAL，独立评审及Test未完成，保留副本和失败证据。
- 固定设计：docs/decisions/0044-installation-qualification-contract-closure.md SHA256 2731ca4ca38dae284ff628269f226f8f4c48eb080c5e614f676eb54248c33e8e；Architecture/QualificationContractClosure-A45正式Handoff。记录实际起点commit/完整输入索引，以当前生产源为准。
- 只写：services/engine/src/video_creator/顶层入口及api/domain/application/infrastructure/integrations/cli；services/engine/migrations/；tools/export-contracts/；自身Codex/VideoCreatorImplementation/Backend/InstallationTrustConsumer-A45/。所有依赖及锁文件归Integration，测试归Test，禁止媒体/桌面/工作台源或他项目写入。
- 产物：同原Engine initialize_bind_and_admit_trust seq3、强NativeInstallationTrustConsumer与open_native_qualification_trust唯一factory、严格record/target/profile/Ed25519与I64解析、不可变SQLite admissions/records/events及current、QualificationControl受保护snapshot/pending/floor恢复；v2精确14字段与真实current_writer_lease RAII、所有qualified短writer同connection纯本地前后检查。原v1、原2phase入口及公共SDK语义保持。
- 先向Integration交精确内部ABI及迁移实际序号；不跨白名单代改依赖。不能DTO/bool/callback假资格、不制造Owner/信任确认/报告，不以永久503代替目标实现。
- 成功条件：具体生产接线及可审查完整源；实际信任材料/资源套件/机器缺失留NOT_READY，不影响无依赖实现。保留原Daily修复及待评审范围，不覆盖冻结证据。
- 验证：固定真实工具/argv/闭包后执行可用静态和已有定向检查，完整保存原始输出及退出码；不降阈值、不改测试、不开付费探测。自身全部process/session/cell由原owner跟踪至真实terminal/双EOF，超时不视终止或重启依据。
- 回执与交接：实际起点及变更SHA、ABI、迁移/恢复失败语义、命令/失败/未测矩阵、有限回滚和下游；FINAL前释放所有自身工具/读写者。下游Integration/Test/独立Review/Acceptance。
