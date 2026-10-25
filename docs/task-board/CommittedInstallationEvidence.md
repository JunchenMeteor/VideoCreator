# CommittedInstallationEvidence

- 状态：QUEUED；唯一角色：原架构师，实际槽释放后执行。保持完整R1→R2范围，不把有限设计算验收。
- 固定输入：ADR0044/0045；Backend/InstallationTrustConsumer-A45/ControlLayout-Early.md SHA2c45e81da18e7e134465265e1ecc4b4f7edecc4a0cae361e3bc158b3fea743d5，Root20144f已全文收；固定Integration MaterialsAndProducerAbi-Early.md SHA150d902e16480ab19463455d10a0bb7e83af2f0bd5583e3e01e82444e741709c。后端原immutable trust receipt仅SQL，无Native held sidecar；不能由六键snapshot/marker推定committed action。
- 仅解决：Native在ADR0045 seq4提交后、seq5前核实际原trust/record/action/current所需的唯一已提交证据对象。先查已有固定合同可否直接消费；仅缺失时补最小protected sidecar唯一filename/schema/版本、canonical与精确hash/ref语义。
- 必须明确：原trust receipt/ref、record action receipt/ref、request SHA/revision与原native retained action的关联；SQLcommit→证据atomic fsync→snapshot/Control complete的唯一先后；真实安装文件/目录持有与限界；首commit及exact unknown恢复、revoke/floor/expiry、source释放。只持久化原事实，不创造source/权限或公开DTO授权。
- 禁止：Native开数据库/读取秘密；普通caller JSON/签名/候选record/marker替代原独立来源；改已有snapshot六键、trust八键、v2十四键或seq4/5的公开含义；另起Engine/数据库/账号/生产lease循环。若既有合同已完整，给精准引用直接实施，不泛化重设计。
- 写白名单：Architecture原docs/decisions/与相关架构文档、自身Codex/VideoCreatorImplementation/Architecture/CommittedInstallationEvidence/；实现、测试及标准只读。
- 交付：唯一精确可实现合同/Handoff/固定inputs+SHA、必要失败恢复矩阵，直接Backend/Integration；实际最后toolterminal及读者释放。禁止签名/key/SQL/产品/安装/模型/收费执行。不读双方热修改源当固定接口。
