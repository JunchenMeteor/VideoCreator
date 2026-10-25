# RV53 补充：T37 后继测试语义

这是统筹在F6有限源评审结束后追加的单文档裁定，不能改写原测试或证明F6已运行。固定输入仅 T37NextNamespaceProposal.md，原普通路径：
G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T37WorkbenchOriginalF5/T37NextNamespaceProposal.md
SHA b980ed25560b79b57c5f9f726aa16a5541db2ca3bab36d4f5cac13208721c89b，3769字节。314d0a实际exit0；未读T37活输出或测试源码，未重跑/改期望。

## 有限批准的语义修订原则

1. **批准新namespace动作选择按固定F6映射。** 原精确文本“重试同一导入”与新源“重试原项目的同一导入”不同（提案9行；F6 BundleImportView 133行）。新测试应精确选择该恢复动作并独立核其实际请求，不能把旧selector未找到新按钮当产品动作失败，也不能声称旧测试已覆盖F6。不能用任意“导入”按钮宽匹配取绿。
2. **批准去掉“currentProject不同则必须disabled”的额外UI约束，限同实例、显式重试原项目。** 基本要求是原意图不得改绑，不是当前视图必须留在原项目。固定F6 83–108行读取原retained intent，wasUnknown=true时校验原body/key并直接使用intent.body；133行明确按钮为重试原项目。因此选择B时可显式恢复A，前提是实际POST始终绑定A及原同一请求身份。没有要求“可在B创建一份新请求”，也没有批准跨实例派发。

## 不得删减的反向检查

必须保留原离开A再返回A后的意图丢失反例；旧F5与原19/14 NOTPASS保持，不用本裁定重写原断言或原结果。新namespace仍须核实际完整body、固定key、staging_id、archive_sha256、原origin全部字段、发起project_id及实例/连接边界；B视图不得重定向到B body，不重暂存或新建身份。实例切换不得通过另一安装实例发送A的旧意图。原unknown重放再次拒绝不得抹去首次unknown，重选/卸载/重开、本机存储错误/hash-key不符的保护也保留。

首个useState null且未挂载/未到API POST，应分类为执行准备或前端启动失败，不能从“未观察到POST”推导产品已发送然后abort/cancel。本轮仅消费提案5行的既有说明，未独立复读原browser/raw，不能确认React重复、优化器竞态或其它根因。

## 批准范围与尚不批准

只批准上述两处**测试语义原则**；没有修改或批准一份未固定的新测试源码、selector映射、runner、bootstrap、Vite优化设置、闭包或实际执行Plan。原Test应在新namespace保留原文件，提交精确新版本/hash和动作→请求oracle，再按原角色/准入流程固定与执行。提案7行的设置方案仍待具体Plan审查；不改版本/阈值、不丢首例、不反复warm/reload求绿。

原RV53 F6源码报告SHA fb2341f30cc1d802540268d34dd021174cc1d5b8960a009c5f04e84070bf105e和源交接JSON ff779de1e6697365abec8730d9d1e4e6bbf9aabe2d0f80ad5ba2ffbe4c289023不改；两P2仅CLOSED_SOURCE_STATIC。补充1份固定文档不冒充新的36项产品依赖复测；原35pins已结束核对。有限追加后所有reader释放、无live handle，不等Test。完整R1独验后连续R2、真实制作/ASR/三OS范围保持。
