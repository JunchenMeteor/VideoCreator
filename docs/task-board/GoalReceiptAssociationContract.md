# 原 Goal 与受理回执关联：唯一公开合同

状态：ASSIGNED_ORIGINAL_BACKEND_SOURCE_CONTRACT_INTAKE。独立Review已真实FINAL：docs/reviews/F11-RecoveryMechanisms-IndependentReview.md，SHA99ea2126d9d0ffc85f90b1fe27b86492f19d26ac096fb6e6ca0e9a918d90f3fd；F11-MECH-I01为OPEN_CONTRACT_AND_COVERAGE，不是已复现Backend缺陷。角色：Backend维护实际DTO/公共语义，Architecture批准必要合同变更，Integration生成契约/SDK，Frontend消费；并发槽真实释放后分批。当前A45实现优先；该合同是后续回执关联实现的前置，不阻挡前端已有明确契约的素材选择与缓存文案工作。

输入：固定ADR0039 f07037c4bd66a56dc03115a9c357940bb96640bb5c52f35d64424f3a7cd7198f规定完整canonical Goal/hash与normalized ProductionRequest/hash分开；固定UI/SDK目前只给goal_sha256:string。前端bodyHash是JSON.stringify原正文；8个受控fixture都返回自己的bodyHash，只验证组件恢复机制，不定义服务端canonical化算法。

后端应只读定位原已实现的完整Goal输入解析/defaults/normalization/canonical字节/hash与ProjectGoalAccepted回执关联，固定版本、源、合法调用示例及明确无效输入/序列化边界。交付可直接生成/消费的唯一公开合同与至少正向等价/非等价示例，不私造另一套算法。精确讨论同instance但异原Goal、错误回执、foreign实例/principal、重复key异body，是否及如何核准原已受理Goal/派生事实；SHA比对不是授权能力。

不得直接令服务端goal_sha256等于前端JSON.stringify bodyHash；不同hash定义不强制相等，不因fixture简化拒绝合法API。若原合同无法提供客户端严格关联，需要Architecture明确有限API/版本与失败语义决定，再由归属角色生成SDK/实现，不额外开放任意范围/authority/Owner字段或在Frontend手写新DTO。保原v1合法行为、API/MCP/native共用唯一输入、完整原请求/幂等key、未知状态和同任务导航；坏/未证回执不误清pending、不重提新Goal。

后继Test以固定合同核真实与对应fixture负例：相同原Goal规范字节正确回执可结算，合法normalized差异按真实合同处理，同实例结构合法异Goal不能结算，当前8目标/5秒与原失败历史不改。独Review/Acceptance按实际范围，不把静态/模拟当真实Backend或完整R1通过。没有此公开契约前，旧8passed保持原有限结果、新关联未覆盖保OPEN。

本卡只冻结依赖和目标，当前不授权收费/秘密/安装/发布/生产部署；总代码/角色白名单与完整R1独验后连续R2不变。统筹不代写算法、SDK或审查实现。

2026-10-10 queued bounded intake: original Backend after its TRUE FINAL7b8b65 and next actual available role slot. Current coherent source is QualifiedSetupDependencyRetention/SourceStage Index4ceea4bb916a5223133fe15c881bb61c864752ca6f735ff3bc1c663c4524035c; all101 ordinary bytes/SHA verified Rootb152a7. First deliver exact existing public Goal parse/defaults/canonicalization/accepted receipt association source and limited gap handoff; preserve old canonical/normalized distinction. Do not invent another canonical algorithm, edit frontend/SDK/tests, or alter public contract without original Architecture approval when required. This intake can proceed independently of media generation/fees/installation, but is not yet activated. Independent CWI source review and corrected14case oracle are currently higher-priority finite handoffs; no fifthrole.

Activation: independent CWI fixreview TRUE FINALbdb947/0/readers released, Rootc6f147 FULL report2bf2ed8f529a7845035efc03d537f32108188376500619f1698a76be9289ed45 and FinalHandoff6ec408f6dbc04f550d64510458d87e5118066c7ebf7b8d0d0e2a74e440a57e07; all3 exact defects CLOSED_SOURCE_STATIC only. Next released slot assigned original Backend for finite source contract intake in own Backend/GoalReceiptAssociationContract/. No public contract implementation or SDK/frontend/test changes in this intake. Exact existing contract and source gap first; Architect decides a necessary public change separately. Do not wait for providers or expand into generic authorization design.
