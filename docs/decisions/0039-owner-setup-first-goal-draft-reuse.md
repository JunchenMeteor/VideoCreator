# ADR0039 — 首次 OwnerSetup 复用唯一真实 Goal 草稿

状态：A36 私有接缝设计批准；未实施、未运行、未独立验证。2026-10-10。
来源：ADR0037/0038、B40 final74 的正式 Interfaces/Handoff/索引，以及 B41 DraftReuseGap 五个固定普通源。逐件身份和消费区间见 Architecture/OwnerSetupDraftReuse-A36/A36InputPins.json。完整 R1 独立验收后连续 R2、三 OS、本地免产品注册/BYOK、五步与 API/MCP 一次 Goal 到成片不变。

## 1. 实际缺口与唯一增量

固定 OwnerBootstrapStore.project_scope107–115/change152 必须已有同 Owner 的实际 Project；Engine.create_project222–239 用原 project.create 命令保存真实随机草稿及精确幂等回执。B40 ProjectGoalInput213–221 没有 project_id；DailyProjectService.accept694–703 再计划随机项目，_commit_intent822–824 INSERT。先准备真实草稿再调用公开 accept 会产生第二个项目；不能改公开请求加 ID、模型指定范围、伪项目/Asset、任意跳 INSERT 或另起制作队列。

选择唯一私有 accept_owner_setup_goal(source) 入口与明确 accepted-daily-project-goal-v2。仅原 OwnerSetupService 已受理的首次真实 Goal 草稿可以复用；普通 API/MCP/native 日常 ProjectGoalInput-v1 仍新建实际项目。v1 原规范字节、哈希、默认、parser 和恢复语义不改。只有私有 origin 决定原 writer 的 create/reuse 分支，不能根据“项目 ID 存在”或正文相似自行推断。

## 2. 准备草稿、身份与不可变事实

准备发生在初始化 Owner 之前，必须来自 ADR0038 固定 pre-API NativeSetup 原会话/已认证配置 child 的 OwnerSetupPreparationSource：同实例、实际 OS Owner/GUI 会话、当前原 data/Control 目录身份、原 host/source/peer 与 Backend 实例 principal 映射。domain owner 由原可信实例/Bundle principal 工厂取得，并与原 OS/目录绑定；不读 Goal/JS/bearer 的 owner 字段，不以未存在的 OwnerBinding 造票。该强源只允许保存真实草稿和准备展示意图，不授管理/制作/安装资格，也不伪人审。没有可信映射时明确缺件，后继须实现正常来源而非永久占位。

OwnerSetupService.prepare_first_goal(key, goal, *, preparation) -> OwnerSetupIntentV1：key 是有界幂等请求键，服务派生独立固定 project.create 内部键；保原同 Owner + 规范 ProjectInput 的命令。重入准备先找原命令/持久准备映射；相同 key+完整 canonical Goal 返回同草稿，不重新随机创建；异 Goal 409。实际 ProjectInput 恰为 name/goal/inputs.source_text，其余输入/brief/source/delivery/creation ref 保在完整规范 Goal 中，不拿投影 hash 代 full Goal hash。先把同 key/Goal 的准确准备事实持久关联，再恢复原 create 回执；不得在丢响应后生成新 key/项目。准备一次仅有一个待确认首 Goal，改变 Goal 是明确新准备修订，不删除旧命令或自动替换已确认意图。

本次不可变 DraftOrigin：instance_id、owner_subject、实际 project_id、严格 expected_revision、saved_at_us、完整 ProjectInput 规范体及 SHA、完整 ProjectDraft 规范 SHA、原 project.create 命令 key/request SHA/实际回执 SHA、完整 canonical Goal 及 goal_sha256、setup_id/intent revision/规范 intent SHA。服务读实际行和原命令确认所有关系；revision/body/saved_at/owner 任一不吻合即拒绝。SHA/JSON/ID 都是比对事实，不是 authority。草稿是用户真实目标，可见且未授权；取消/过期/未确认保留为诚实草稿，无 child/Production/Run/配额消耗/收费，不自动删文件或伪称制作完成。

原生展示和确认仍 ADR0038 原完整意图，包括此唯一草稿和有限预算/配额。Owner 初始化继续用此实际 project_id 通过原 project_scope；不初始化空范围或换 Owner 身份。确认前后草稿修订变化均需重新明确准备/人审，禁止只刷新 hash 延续旧确认。

## 3. 私有强源、签名与生命周期

Backend 唯一实现以下私有端口（非 HTTP/MCP/OpenAPI 字段）：

- OwnerSetupService.prepare_first_goal(key: str, goal: ProjectGoalInput, *, preparation: OwnerSetupPreparationSource) -> OwnerSetupIntentV1。
- OwnerSetupService.goal_source(accepted: AcceptedOwnerSetupSource) -> ContextManager[OwnerSetupGoalSource]；accepted 是原服务持久受理/恢复后的强对象，不是 AcceptedOwnerSetupIntent DTO。
- OwnerSetupService.assert_goal_current(source) / assert_goal_local_current(source) / close_goal_source(source)。
- DailyProjectService.accept_owner_setup_goal(source: OwnerSetupGoalSource) -> ProjectGoalAccepted；不另接 subject/project_id/goal/entry/Bool。
- 原 recover_pending(registered, installation) 保签名；v2 内部调用原 OwnerSetupService 恢复工厂取得本次精确强源，不接受 caller source DTO。

OwnerSetupPreparationSource/AcceptedOwnerSetupSource/OwnerSetupGoalSource 皆 eq=False、不可序列化授票、原服务强成员集合/同 Engine+Bundle+Daily/ProductionAdmissions/注册对象/原 issuer、同 thread/context 与不可逆关闭 epoch。GoalSource 完整绑定原 AcceptedOwnerSetupIntent ref/full SHA、真实确认来源、实际 OS/目录、DraftOrigin、原 Goal/key/entry=native、真实 Owner 初始化/安装/执行/creation 各 action receipts/current refs、原预算/有限父委托及固定 planned IDs。由同 OwnerSetupService 仅在限定真实 steps 完成且原角色/资源/parent current 后颁发，普通 Daily install capability 或同值构造不能得到它。首次执行原安装资源资格仍须真实；确认不补 qualified evidence/rights。

writer 外原 source assert_current 重核会话/peer/目录/持有资源/原 action/current/到期和原 accepted intent；保持 OwnerControl→ProductionControl 锁顺序。进入短 writer 前已有原 guard；writer 内只原对象集合/epoch/thread/不可变缓存和同连接 DB/current 行核验，禁止新 OS/hash文件/RPC/await。返回/异常/上下文退出/原连接失效立即移除或不可逆失效；外部泄露旧强对象、克隆、跨 Engine/thread/issuer/closed/expired source 一律拒绝。

ADR0038 确认后未受理的120s限制与已持久受理后的恢复是两个阶段。受理前仍要求实际原生确认 current；受理后仅由原受保护 intent/receipts/floor 和同实际 OS/目录/当前安装/Owner/父授权重建仅此次恢复强源，不重放旧 challenge/JSON，不要求每一步或每日新确认。恢复新对象仍须当前资源/权限与 intent 有效期，不能用“已受理”突破撤销、替换、到期。

## 4. v2 journal 与唯一原子 writer

_AcceptedGoalIntentV2.format=accepted-daily-project-goal-v2：保 v1 全部共同事实（完整 Goal/hash、确切 normalized 原 ProductionRequest、父授权/真实 creation action、Owner body SHA、entry/key、Project/Production/Run/requestRevision/derivation/receipt planned IDs、accepted_at_us），增加固定 project_origin=owner_setup_draft 与完整 DraftOrigin/原 accepted_setup_ref。project_id 必须等原 draft ID；正常 request.project_id 同值，Goal hash 与 normalized request hash 分开。字段严格、未知/重复/错误版本/Bool integer 拒绝；32MiB 原上限不变，不默认补 origin。

受理的不可变 setup intent 先包含 Goal/草稿/已确认步骤，不回填后继 GoalIntent SHA。v2 GoalIntent 可引用这个已固定 setup ref；后来完成/Goal 回执保独立 progress/command record，只前向引用原 intent。禁止 SHA 自循环或通过改已确认正文满足新ref。OwnerSetupIntent-v1 已要求的草稿完整事实由 Backend 正确实现；此次不改变六字段 startup/wire/native confirmation ABI，也不把 Goal v2 混进公开 v1 schema。

在原 GOAL_INTENT_SCOPE/metadata/受保护 AcceptedGoal 文件显式按 format 分派 v1/v2，原 v1 不重写。初次接收先保准确 v2 和 recovery copy，固定所有 planned IDs，再 reserve 原 floor；同 key+相同 Goal 但 origin/setup/draft 不同也409，不能靠单 Goal SHA 覆盖另一 setup。公开 accept 只能新建 v1；若该键已是 v2 pending，只由私有源/固定恢复路径续跑，不能回退随机 v1。公开同主体同 key+Goal 对已完成 v2 可取历史 ProjectGoalAccepted-v1 回执，不授重新执行权；异正文/身份仍冲突。

_commit_intent 与原 _GoalWriterContext/engine._accept_production_connection 复用同 connection。v1 保原 INSERT。v2 在同 writer 初始与 final 本地检查：

1. 原 prepared/accepted setup journal、真实 receipts、DraftOrigin/父委托/Owner/current/完整 Goal/key/权限/配额/原资源 guard 相符。
2. SELECT 精确同 owner/id 的实际草稿；revision/body/saved_at 与完整原快照一致、原 project.create 回执相符。首次消费前无其他 Production/child/另一 setup 受理绑定；只能此原 setup 对此草稿消费一次。
3. 不 INSERT/UPDATE 该 Project，不伪升 revision/改 saved_at；exact request 使用原 ID。原同事务写唯一 Production、Run、child/receipt、原 acceptance/绑定命令、setup Goal 消费结果与 created_projects+1。final current/guard 核验后 commit，再 complete 原同 floor。

无 nested public transaction，无临时宽泛 skip_insert/allow_existing 布尔。失败 rollback 不计数、不派发、不收费用，保真实 pending/已提交历史；不直接调用 create_project_goal 再建项目。Goal接受后的 ordinary 项目编辑不回写已受理 Goal/normalized Request 或历史 DraftOrigin，不把以后编辑版本当原 setup 核实。已完成同键回执只验证原 immutable acceptance，不能因后来的编辑把它再次接收或计数；实际制作仍依原当前授权/lease/fence/费用门。

配额按原派生作品定义：prepare真实草稿0，首次完成本派生+1，exact retry/recovery+0，后续各新 Goal 各+1；原 native 展示有限 max_created_projects 包含首作品，不能偷赠额度、加1上限或新建预算组。max_active_productions 原同事务检查；首 Goal/修订共享原真实 budget_group/cap/operation reserved+spent+unknown，原动作次数/资源/rights/源范围不变。新无关项目不改旧 Run、父/子 snapshot、注册 generation、活动 lease/fence 或 unknown 状态。

## 5. 准确恢复、失败与版本兼容

断点为草稿创建回执前后/prepare保存前后、确认接受前后、各原 setup steps reserve/commit/complete、v2 intent持久化前后及 Goal reserve/commit/complete。用原稳定准备键、actual DraftOrigin、原 accepted setup 和真实 step receipts 恢复同 project/planned IDs；已commit步骤/Goal只返回原回执+complete其原pending，不重新初始化Owner或生成新制作 key/ID/队列。reserve前已保v2尚无floor的受理亦由原固定OwnerSetup恢复发现，不只依客户端retry。

尚未 Goal commit：草稿变更、foreign/current revoke/expiry/parent失效明确不授权，不创建新项目。已拥有准确pending且能核原事实时，按原 protocol 以同预留 revision 写确定 denied/cancelled 结果及setup阶段，再 complete；不造成功或丢草稿。409修改冲突可记录准确拒绝，但损坏/缺失/未知命令、unknown floor或不可信source不能泛化为零费拒绝后清floor，须保待核实/原Owner恢复。已Goal commit后只核原回执/消耗事实来complete，权限失效阻之后新副作用，不撤销未知已受理收费/清账重提。

统一原 ErrorEnvelope/私有错误：严格grammar/body缺项422（原size超限413）、foreign/伪源/未允许403、changed draft/key/origin/setup/generation/重复消费409、原实际源或资格缺件503；过期拒绝不自动续期。历史 source 恢复/receipt读取不是普通人审 ReviewDecision；确认不授生产作品/版权/发布权。原 provenance0.1/derived0.2 grammar、其完整父/子/真实 action 与祖先许可闭包保持，不将私有 v2 Origin 塞进旧公开文档。accepted setup/DraftOrigin 的完整关联由本机受保护 journal 留存；已有允许的历史导出若携带该关联，仅作 origin证据并按其明确版本/索引表达，不导出秘密/临时强对象或扩旧 grammar；导入不能成为本机 setup/Goal source。

Backend 唯一维护 private DTO/format dispatch/current/recovery/commands 与必要 journal 唯一约束。B40 实际 schema9/0009_daily_project_authorizations 已固定；B41 正在拥有的 setup schema10/后继以其正式源为准，本卡不读取热源、不假定已完成。优先原 commands/metadata+唯一 setup journal 落事实；若尚不能表达唯一 draft消费与 prepared/accepted恢复，由 Backend 在实际最后迁移之后追加一次准确迁移并交 backup/version/restore闭包，不能改原0009或以DTO版本2冒DB版本。旧v1 accepted files/provenance0.1与derived0.2不静默迁移。

## 6. 最小后继与独立验证

Backend：在B41本角色接 prepare真实 source、private GoalSource/v2 dispatcher、原writer分支/同事务消费与恢复；早 native consumer/startup/wire 可以继续，不能把新增源交给 renderer。Integration：沿原 ADR0038 安装/确认 carrier，展示同 original Goal/draft snapshot；仅消费 Backend 固定 prepare/status/execute ABI，后按唯一源生成安全公开契约/SDK与完整新 artifact。Frontend：首settings真实Goal一次配置，显示同 draft/原阶段与成片查询；不复制ID再POST projects/Goal，不传confirmed/origin。AgentMedia：继续原 typed admission/原队列与委托 provenance，不创造第二首项目或管理权限。

Test独立真实正向：非TTY首次本人原生确认后总一Project/一child/一Production/一Run，prepare/接受/恢复returned ID均同原草稿；两个后续 App/API/MCP新Goal真实不同ID且无每天重复确认。真实断点逐步核所有ID、floor/receipt、计数首+1/重入0、预算/unknown保持；并发重复samekey唯一、foreign/另keytakeover/clone/跨Engine/thread/关闭/过期/草稿修改/已有Production/新Goal409、public project_id拒绝、v1原字节/parser/恢复兼容。确认正向不能以fixture/假TTY/JSbool证明。Review独立看固定差异，Acceptance原R1/R2范围与阈值不改。设计/AST支持不能称这些运行通过。

A36仅读固定普通源并写架构材料；生产/DB/Owner/native/UI/API/模型/联网/凭证/安装/费用均0。初次只读范围输出有PowerShell单区间数组错误与截断，已用明确整数区间补读；不是产品失败或全机缺失结论。真实资源资格、媒体精度/完整作品和三OS仍按原缺项与独验推进。
