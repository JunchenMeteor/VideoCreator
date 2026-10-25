# ADR0041 — 派生作品的真实 Owner 有限同 Run 再授权

状态：A37 设计批准，RV80-P02 尚待实现/独立验证。2026-10-10。
依据固定RV80/P02、B40普通reauthorize/issuer/Daily/Owner/management/policy方法，ADR0037—0040。来源见 A37InputPins.json。此为新真实管理许可，绝非ADR0040拒绝事实权限。完整R1独验后连续R2不变。

## 1. 源码事实与唯一恢复来源

旧ManagementPrincipal有限project_ids正确拒新child；真实OwnerBootstrap.change227–235的renew确可获新cap，但改变Owner generation，不是日常有限子恢复。即使cap合法含child，reauthorize160–168→issuer._request291–294→Daily.derived_record447–456仍先旧parent current；_record301–307总选旧derived policy，拒真实新policy。

选择“真实Owner为这一个原作品确认有限新政策→原同Run reauthorize消费新的强source/current selection”。保旧cap tuple/Owner/执行/Policy正文，拒模型管理/wildcard/伪cap/把历史creation作当前许可；不为此恢复通常renew整个Owner。旧真实renew仍合法，其明确换代失效保留；若换代后新安装/执行source尚未合法恢复，不能靠管理cap造执行许可。

## 2. 真实 Owner 动作和有限目标

Backend新增固定 OwnerChildReauthorizationService 与私有 OwnerChildReauthorizationIntent-v1：instance/domain Owner、当前实际OS/目录/Owner generation+真实authentication binding、原child derivation ref/完整历史父→子→Goal/receipt、准确project/production/latest run/requestRevision/requestSHA、等待原因及原source状态、完整新policy正文/ref或明确policy-create proposal、当次实际current安装与各执行角色refs、原预算identity、有效期、封闭steps（若需创建政策则create-policy，再sameRun-reauthorize）、各canonical command/hash及原接受/恢复key。无任意module/shell/新的Goal/新Production/预算/请求修订。Owner看见真正期限/rights/来源/金额及原父/子撤销原因，明确确认继续此作品，不自动解释别的政策默认变更。

此新有限动作从当前真实OS Owner、原受保护目录/vault绑定的实际本机管理来源及真人确认颁发。TTY沿原 confirm_local_action 的真实stdin/stdout与精确AUTHORIZE；App沿ADR0038同等级OS Owner/session/peer/原生modal与完整intent校验，但使用独立固定 native-owner-child-reauthorization-confirmation-v1 / role=owner-child-reauthorization，不能将旧owner-setup票据/JS bool/普通renderer请求升用途。Integration按Backend正式闭集消费；此次不改变原setup/六field/wire ABI或请求用户现在操作。

原cap排除该child时，其authenticate结果只能证明当前Owner管理身份，不能跳旧 _principal(capability, child)；新的scope授予来自这次真实本机Owner精确确认及actual owned Project/完整派生链。唯一新 AcceptedOwnerChildSource 为eq=False本角色服务原成员/同Engine/Bundle/issuer/原Owner/root/thread/epoch/current、精确intent、真实确认与各receipts强源，不是扩旧cap/换credential。准备展示可读历史不授权；确认commit前需current，受理后的准确step恢复依原受保护intent/原Owner/current/floor，不重放旧GUIchallenge。

若已真正取得包含child的正常current AdministrationCapability且新政策经原真实管理服务安装，原 reauthorize(capability,key,command) 签名/旧tuple判断保持，合法cap可由原服务为精确目标构造 SameRunOwnerPolicySource；这不是免验证或第二套政策。无新增cap的常用路径则由上述有限本机动作提供同一消费源，不要求为了每个child整体Owner renew。普通新Goal仍ADR0037一次委托，未失效作品不反复弹确认。

## 3. 私有端口与原动作 Core

最小明确接口归Backend：
- OwnerChildReauthorizationService.prepare(key, target: ReauthorizeOriginalProduction, new_policy, *, actual_owner_source) -> OwnerChildReauthorizationIntentV1。
- accept(confirmed: ConfirmedOwnerChildReauthorization) -> AcceptedOwnerChildSource；execute(source) -> ChildReauthorizationResult。
- ProductionReauthorization.reauthorize_child(source: SameRunOwnerPolicySource) -> 原真实再授权动作回执；不接宽Bool/任意project tuple。
- DailyProjectService.historical_child_fact(connection, production, run) -> 私有不可授票历史fact。
- 原服务闭集factory/current context颁发 SameRunOwnerPolicySource，包含 AcceptedOwnerChildSource或真实普通current cap+已安装政策的来源，及确切policy/install/action/target/current refs。

准备/接受/执行各来源必须原对象成员而非Protocol任意实现或注册callback。同根/原Bundle/真实Owner，资源/OS/RPC在writer外assert_current，短writer内assert_local_current仅本成员/epoch/thread与同connection current rows。各有限policy-create/reauthorize步骤仍真实独立原action receipt、完整commandSHA、reserve/commit/complete，已commit步骤只返回其原receipt，不能拼假的create/install/select action。

原 ProductionAuthorizationService._action提取唯一内部connection/action Core，由两个不相混的前置适配接入：旧cap分支仍原_principal/project tuple；新child分支验证强源完整scope/acceptedIntent及真实Owner后只准精确child/原command/原目标。新consumer不伪构造AdministrationCapability；原policy资源/时间、Owner→Production锁、原floor和samewriter语义复用。持久 AcceptedOwnerChildIntent及恢复副本先于reserve；方案和最终receipt关联单向，禁止SHA回填闭环。各steps中断自动精确恢复或明确待核实，不以永久waiting/503作为交付。底层schema/journal/备份由Backend在其实际最后迁移之后唯一维护。

当次新政策 project_ids 仅此实际child，execution主体为本次实际Owner，期限不超当前Owner/真实execution/资源资格；routes/价格/inputs/source版本/转移/actions/质量/alignment/完整输出/rights均按原model与实际current资源校验。原immutable Request/Run的routes、maxcost、currency/group identity、cap_units、revision_cycles/剩余次数仍满足新政策；新Owner确认可合法授新期限，但不能改原请求、换budget、重置spent/reserved/unknown或直接授rights owned/licensed。没有合法current execution/安装资格则拒新执行、保已完成真实管理事实，不能用expired registration或本机确认造qualification。

## 4. 历史派生与当次执行选择分离

historical_child_fact严格使用原 _child/_record/真实commands以及本机Project/Production/Run/原request canonical/bodySHA读取完整origin；不调用旧 _identity、parent._current/derived_record，也不以foreign imported origin作本机票据。原父/子撤销/替换/expiry保历史可读，旧parent并非新授权的权限根。损坏/缺命令/foreign Owner/错实例/新请求目标拒绝。

后端新增 private CurrentPolicyBinding-v2，format=production-current-policy-binding-v2，source_kind=owner_child_reauthorization：保原instance/production/run/requestRevision/requestSHA/admission/action/key，增加确切原derivation ref、已受理child grant/当前Owner action ref、完整本次policy-install/reauthorize source及actual execution refs的持久关联。原v1 pointer/0.1 provenance与初始derived0.2字节/grammar不改。pointer/ref只是locator，必须核实际原local commands/accepted-grant/actions/current rows；不存在就不能按新分支猜默认政策。

issuer._request/_record/_bound/current_binding先按已核本次强source或持久current-binding v2分派，不能无条件先要求旧parent current：
- 原初始delegated_project分支保持原parent/child current门。
- 原owner_policy分支保持旧policy/cap校验。
- 新owner_child_reauthorization分支先核完整历史origin/确切目标，再核新的强scope、当前Owner/实际installed execution/source及真实新policy/actions，沿原所有request/route/price/inputs/budget/rights/质量校验；注册对象旧project_ids不含child时，权限仅取本次原强有限SameRunOwnerPolicySource，不修改registered.project_ids或准别的child。
- 持久v2供同实例合法API/MCP/Worker的原issuer/角色current重新颁发当前强source；仅JSON不能重建。原角色若已过期/被换代，须实际合法新登记；不能用v2恢复旧execution。

原child明确revoked时，新intent须展示该真实原因并明确恢复此作品，新的有限Owner action才为新来源；不改旧revoked row为active。新grant自身current/revoked/expiry及所有后来真正Owner目标撤销高水位重核，后来的真实撤销不能被旧新policy回执覆盖。不同作品/current来源互不影响；普通新项目创建不更新Ownergeneration/旧grant快照。

## 5. 同 Run 原writer、unknown与来源版本

继续原 _target核准确latestRun、immutable Request、非terminal/noncancelling、无当前worker/live lease以及原waiting状态；确认原requestJSON/hash、Project ownership和完整ancestry。以原同writer写新真实policy/admission/current v2 pointer及再授权command，清此作品authorization wait；unknown存在仍needs_reconciliation，无unknown才queued。既有Run/project/Production/请求ID不变，无替身Run/新计数/新budget，无clear Operation/settled/票据/原hash、无收费重交；lease释放保原fencing高水位，正常再次claim取得真正新fence，旧permit失效。未知操作只按原受控核实路线，其新管理权限不是普通operation permit。

同key+同完整新intent/command返回原receipts；不同目标/政策/body/current冲突409。reserve/commit/complete/restart保原revision/actions一次，不对已推进Run重复mutate。原历史acceptance/provenance/assets保原字节；对需要继续的stage生成新的真实admission/current事实，不伪造旧plan/review/lease。素材来源/许可撤销及MM/ASR/权利门仍独立，不因新管理动作恢复旧无效许可。

新可移植来源单独 ProductionAuthorizationDocumentV03，kind仍production_authorization，version=0.3.0-candidate、source_kind=owner_child_reauthorization：完整原DerivedProjectAuthorization origin+本次真实Owner accepted-child action/政策install及同Run reauthorize receipts/精确目标+current admission/rightexecution关联，封闭并前向无环。旧文档0.1/0.2不改、不能把新source塞旧枚举；Backend唯一固定正式DTO/版本解析与Bundle closure，Integration按同源生成。导出只事实/审计来源，不导出秘密/强对象；import仅foreign origin，不安装本机grant或执行票。Media消费新的typed source闭集，不把else当真人审核；最终成包/current rights检查识别正确当次source，原origin/source license闭包仍完整。

## 6. 后继与独立验证

Backend最先实现强有限Owner动作/来源工厂、历史childfact、原action/reauthorize Core以及新的current-selection分派，接原安装/current guard、receipt/floor恢复。保旧cap403与旧普通签名；不得只把错误改成另一个等待而不接合法路径。Integration接封闭真实确认carrier/同源contract SDK/native客户端；Frontend作品待授权显示原目标/新policy完整范围并请求真实原生确认，日常Goal不反复提示；Media按后端typed事实运行原Run，不拿模型授权。

Test须真实验证旧cap安全403、原真实renew可取得精确新cap但不隐式重授权、常用有限Owner确认不变Ownergeneration/不影响健康兄弟；父active和过期/替换/撤销两种新policy同原Run一次恢复，原身份/所有预算unknown/asset/hash/次数保持。真实同Run新fence/旧permit拒、unknown保持核实、各steps/floor断点、policy/current revoke/expiry/foreign/跨issuer/闭源/伪cap/JSON/body/祖先损坏/public token/其它child权限拒绝；旧v1和0.1/0.2兼容、新0.3完整闭包/import不授权。人审/OS/资格不能由fixture证明。Review和Acceptance独立，架构不关闭RV80-P02或宣布R1完成。

A37仅固定源/设计；无产品/DB/OS动作/Owner确认/模型/网络/凭证/费用/测试执行。

## 7. B41 最终来源兼容与实施顺序

已消费同上B41 final82/snapshot e986c16e752f362bb7674ceb5227fc9f76a4833c5af4f982d903a4855628de9a，而非早期77。新setup journal只是第一Goal原始creation事实；OwnerSetupService当前强源/期限制约和schema10不供这里新child管理许可。原新Goal/DraftOrigin/acceptedSetup关系原样保在历史链，不把过期setup confirmation当新的policy action。不同用途的真实Owner确认producer/新source另外固定；原startup/6field/owner-setup wire兼容。

后继Backend先实现ADR0040 known-denial/current前装配，解除这个准确pending后再执行本ADR有限新Owner动作；同一发生过两种状态的作品也不共享context。B41实际qualified authority entry、setup-aware成功restart未接，须Backend/Integration独立补真实端口，不能从本ADR的管理许可或新binding推断其已准入。现有原source/Policy/current函数无新运行证据；两个RV80 finding保持OPEN直至后续独立复验。
