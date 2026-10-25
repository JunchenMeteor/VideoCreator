# ADR0024：无人值守制作的真实预授权与同 Run 准入

2026-10-09。状态：**协议设计准入，实际授权入口/持久实现/全自动作品待独立验证**。A21只架构。完整R1自动创作、多模态/API-MCP/三OS后连续R2保持；不重开旧收费编排实验。

## 1 固定缺口与唯一选择

已完整核B17 UnattendedAdmissionGap `f1ad12c70d5332eed083d8a42676e91bb71a1b11ce83f04565ad33ea6619c6eb`、Snapshot `8aed536b2568e461721f3690bddc96a940ca1c09169e907cbbd06d9c67c3c23d`。7个SourceGapCopies只读ordinary，未读B17活源。

当前EvidencePolicy/Registry只管理alignment方法/benchmark；当前wait_for_review拒unattended，submit_decision要求真实waiting_user/exact target，Media仍只认Engine真实approve。候选ProductionRightsDeclaration只是Owner user_asserted提案，配置hash不是授权动作或法律权源。**新增独立ProductionAuthorizationPolicy与实际Owner授权记录，给同一Run签发typed准入事实；不写假ReviewDecision，不复用alignment grammar，不另建队列或费用账本。**

制作预授权、当前素材/输出合法权利、方法质量、发布平台授权是四个守卫。生产策略只授权在明确范围内执行/自动通过创作阶段；不能凭策略补owned/licensed authority、benchmark资格、七项QC、媒体真实证据、商用服务权益或平台发布权限。

## 2 谁授权、怎样安装与撤销

授权来源必须是**实际认证且获范围许可的Owner/项目管理主体执行的明确授权动作**：本机免产品账号的设置/Owner管理操作，或安装实例明确登记的调用系统管理主体。普通production.create/MCP执行身份没有策略管理权，模型工具不暴露策略安装/管理口；模型JSON/配置文件、`approved=true`、普通方案approve或root任务指派不能自行成为授权。

Backend新增独立受控AdministrationPort（能力对象不入HTTP/model DTO）。native Owner设置、受限headless管理API可适配这个同一服务。若提供API，使用**独立受信管理员权限** `production.authorization.manage` 与现实际principal/project ownership检查；默认Portal制作credential不含该能力，不能“为自己注册预授权”。本机Owner可明确登记调用系统的管理/执行权限，但不能从其自报subject/project推断。管理授权与执行credential分开，正常MCP工具只有执行/观察/原审核权限，无策略自提升端口。

实际create/replace/select/revoke/重新授权某Production动作形成服务端AuthorizationActionReceipt：实例、实际管理主体及scope、动作、精确policy ID/revision/body SHA、实际授权时间、幂等key/request SHA与真实认证来源。没有secret、模型造签名或伪human ReviewDecision。客户端只提交proposal；通过认证的明确管理命令才将它安装为策略。安装器配置可定位真实授权来源，不能用一份配置hash代已发生的Owner动作。

策略revision body及receipt不可变。replace产生新revision并推进当前active revision/floor；旧Run原policy绑定不静默升级。revoke持久保存实际receipt/生效时间，phase/dispatch/final writer均核当前状态。管理幂等使用原commands机制的独立scope，不重置费用组或重复签授权。

恢复/备份不能把撤销悄悄倒退：维护独立production-authorization registry revision和可信安装控制面已知最低revision（不借alignment表）。发现恢复落后先停新制作并要求真实管理刷新/重授权，不默认所有旧策略有效。本地可信安装控制状态不依赖产品账号；该机制不声称抵抗同时篡改所有本机信任状态的管理员。

## 3 明确的最小策略与既有预算

Backend唯一定义公开管理proposal/读取模型和私有安装事实，独立kind `production_authorization_policy` / version `0.1.0-candidate`；其Ref为policy_id/revision/content_sha256。body不含自己的SHA，server按规范正文计算并绑定实际receipt。

必须为有限、可判定的范围：

| 组 | 字段/约束 |
|---|---|
| identity | actual instance、owner/declaring subject、允许executing principal/registration与project；无任意通配所有主体/安装实例 |
| lifetime/version | valid_from/expires整数微秒、current revision、workflow/driver/profile及实际资源注册版本/SHA |
| creative scope | 明确允许的创作类型/profile、language/duration/aspect、输出profile/交付方式、phase plan/quality及其实际动作；不以模型评分替判据 |
| inputs/source | owned Asset身份/SHA或允许来源系统/namespace与调用身份，caller-supplied text是否允许、source version固定规则；SourceBinding自报不能越scope |
| routes/transfer | allowed route IDs和实际route配置/cost-rule版本、source类别、本地/远程及external_transfer边界；资源/credential/厂商许可另由当前route守卫核 |
| budget | max cost perProduction、必须使用的已存在budget_group_id及实际group身份/currency；max operation成本/总group余额仍由原账本原子核 |
| revision | 不高于request现有max_revision_cycles，沿Production剩余限次/已花/unknown预留，不按新Run/policy重置 |
| declaration/quality | 明确user_asserted Owner声明或实际独立权源引用；固定实际必需质量/精度门和自动交付条件，不允许降低阈值 |

拒无限未来expiry、未知resource/route scope冒匹配、修改request max_cost或默认转移授权。paid用已Owner实际授权的**现budget_groups**：policy不新增cap、不另存spent/reserved、不创建每角色预算；同group在原prepare/claim/settle事务承担多Production/修订共享总额。free policy可明确max_cost=0，不强加收费组。官方资源与BYOK/local的身份/权益/额度分别核，策略不能让现route_guard未支持的official路线通过。

source constraints以真实认证调用身份、原固定Request、实际同owner/project Assets/hash和来源版本为输入；内容主题可允许一定范围，但“模型认为合规/相似”不能授权限。策略允许使用不证明文章事实或版权；实际rights/dependency证据继续独立核。

**不改旧ProductionRequest0.2/0.3、automation默认或请求规范hash。**可信Owner设置可为subject/project/registration选择默认policy；新unattended Production在accept事务中将所选精确ref和认证调用身份绑定到其request_revision_id/request SHA。后续同幂等key返回原绑定，不取更新后的默认。无需调用方每作品填proof；无绑定时可以由明确Owner管理动作对当前Production的原Request重新授权，不通过普通任务参数替换policy。

## 4 持久接缝与typed消费

最小迁移：新增两张领域表，不复用alignment_admissions/revocations，不重写existing decisions：

1. `production_authorization_policies`：不可变revision正文/SHA、实际AuthorizationActionReceipt、current/revoked状态及receipt；current floor/default selection放现metadata受控键，更新同管理事务。
2. `production_admissions`：生产/Run、target_kind（request/creative_revision/final_manifest）、target ID/SHA、phase/action、精确policy ref、调用/registration/resource/budget绑定、rights声明SHA、签发fence、checked/valid_until、规范fact正文/SHA。accept时的request绑定使用`phase=request, action=bind_request, fence=null`，它仅保存原选择且**不是执行许可**；Worker取得真实普通lease后须签发当前fence的`begin_execution`事实，才能进入首次Operation。creative/final条目记录同Run实际阶段授权。

严格唯一键覆盖Production/Run/target/phase/action/policy revision/fence；相同事实幂等返回，异正文拒409。fee/Operation/reservation仍原表，无新调度账本。旧DB迁移不得回填假允许行。恢复新fence后旧receipt只是历史；在当前fence重新核同精确policy/target后可产生新current fact，不把旧fence当执行许可。

Backend扩展候选私有ProductionAdmission：保state/revision ID/SHA，phase明确`request | plan | quality`、`source=human_review | owner_policy`、`action=begin_execution | execute_plan | continue_bundle_validation | finalize_bundle`、actual instance/Production/Run/request/registration binding、checked_at/valid_until、当前非null fence及admission_ref。request执行事实仅owner_policy；human分支仅有真实ApprovalRef，policy分支仅有ProductionPolicyAdmissionRef/实际AuthorizationActionRef，**不得给它造ApprovalRef**。没有lease的bind_request用独立内部绑定记录，不冒这个Current Admission。缺/拒绝/待配置fact保具体blocker，不用bool。

私有口：`production_admission(ordinary_lease, revision_id, *, phase, action=...) -> ProductionAdmission` 与 `assert_production_admission_current(connection, ordinary_lease, admission_ref, *, stage, final_context=...)`。request阶段target是实际Production.request_revision_id/request_sha256，而非伪CreativeRevision；plan/quality才查同Run真正creative row。名字/模型由Backend唯一定义；它们不让普通API/MCP提交“我已admitted”。签发需真实同Run不可变revision/body/输入rights和当前普通fence；核实lease不能借此取得制作权限。

Media `_admit`必须直接消费上述typed分支及准确target/binding，删除“调用后一定再read_review_decision才算允许”的假设。human仍由Backend读取实际approve/revise/reject并核target；policy由Backend真实记录+当前检查允许，无须一个没发生的人类决定。正常interactive无approve才原wait_for_review释放lease/等真人；unattended有效fact保原lease、同Run继续，不能先伪waiting_user再写approve。

## 5 rights与质量不能混成策略许可

`production_rights`提供**typed声明来源事实**，不是裸模型tuple授权：声明ID、policy/真实Owner-action ref、同主体/project/request/input范围、完整RightsSnapshot正文SHA、validity、当前fence。形成plan前它是明确范围的候选声明；plan真正commit后，admission对**实际plan SHA与精确rights正文**作绑定，不批准未来版本。Media原tuple需求由本角色消费适配，不靠getattr/True猜字段。

Owner policy仅可自动绑定其明确`user_asserted`声明（同内容、用途/输入范围/限制），其意义仍是实际Owner声明，不是独立法律权利认证。owned/licensed必须真实已准入authority/许可、祖先/复制/再分发闭包等ADR0020事实，default未准入不因本策略变True。对源声明较宽、跨Production/来源映射变化或新的用途不得复用一条泛Owner声明。

**portable证据最小增量**：新增严格 `ProductionAuthorizationDocument`（kind=production_authorization，version0.1.0-candidate）和artifact role/schema_kind `production_authorization`，由Backend从真实policy/action/plan-admission事实构造验证，Media只分配/stage原bytes。正文含可披露的policy scope/revision/SHA与实际Owner-action/plan target/rights声明绑定，不含credential、内部secret或任意审批token。preflight/private PreparedRightsContext新增独立 `production_authorization_refs`，user_asserted核验可在实际human或这个真实Owner-policy来源二选一；不将policy源塞原ApprovalRef。

旧Manifest0.2/0.3顶层/schema及approval_refs类型保持；policy-only原approval_refs为空tuple而非假human。RightsSnapshot.approval_ref在这个新路径明确定位实际Owner声明identifier，只有严格新typed document+当前本机admission解析才可解释为policy来源；旧路径继续原human语义，不靠ID前缀/文件hash自动选择较宽分支。依赖索引/许可/质量/导出/import必须识别该独立kind与role；缺正式消费就not_ready，不以audit_summary泛JSON冒新事实。

最终Manifest/Quality尚未生成的SHA不得放进前置doc。前置doc绑定已有plan与policy条件；final Manifest/Quality实际定稿后签发的最终current admission可含真实final SHA，但不反写进Manifest自身引起hash循环。导出doc只是原授权来源审计，不成为外国实例ticket/新policy安装；导入保持origin_snapshot_only，不能自授新制作或复活被撤销policy。

Media当前quality草案含precision/rights=not_measured；其policy准入的`continue_bundle_validation`只授权继续真实factory检查，**不是QC通过或可发布**。`finalize_bundle`在实际完整Bundle、七必需QC/rights/precision/evidence/输出profile全部通过并符合策略后由最终writer重新核；用户预授权可以省逐片人工点击，不能省真实检查。失败的真实媒体或报告保持失败，不把policy pass复制成作品实测值。

## 6 当前检查、暂停与恢复

在第一模型/媒体Operation前核request级绑定；plan之后每受影响dispatch及Operation prepare/claim，再核policy current/revoke/expiry、caller/resource/route版本、实际input/right scope、cap/group及现fence。策略允许不替原route_guard、Operation账本或alignment守卫。网络/完整hash在writer外完成；prepare/claim/final publish短writer以同connection核实际当前policy/绑定/期限/撤销版本/lease，不能writer内调用模型、provider或FFmpeg。

最终出版与撤销按现本机writer顺序：已经撤销/过期/stale的路径不得提交；不承诺取回已发bytes或已受理provider任务。未知Operation保持unknown/原预留，政策撤销不清账、不重新收费、不自动provider cancel。受限原Operation核实继续依原权限/原只读核实lease协议；不能因制作policy缺失换normal lease重交。

新增明确可恢复状态 `waiting_authorization`（Backend唯一公开enum/错误/恢复实现），用于unattended缺真实policy、策略撤销/过期/需重新授权。记录真实blocker/target/request，释放普通lease，不插ReviewDecision，不自动变interactive approve；真正资源未配置另给明确resource-not-ready原因。Owner通过真实管理动作安装/选定或重新授权**该原Production/Request**后，核范围并回queued，由新普通fence恢复同Run和已有Step/Operation；不能全局默认改动就擅自放行旧绑定。

越scope/声明冲突403/409、坏不可变事实422、预算不足原402、当前source/authority确未安装503分别保留。waiting_authorization不是成品永远的占位；本轮必须实现授权→自动继续→真实最终交付正向链。已预授权且资源/质量正常的API/MCP任务应自动完整完成，调用者只收到状态与Bundle/video/audio/text/RAG交付，无须人工逐项筛选/批准。interactive仍原真实审核与指导/修订流程。

## 7 owner与验证输入

- **Backend**：唯一policy管理/真实动作/两表迁移及state、accept原绑定、预算复用、typed private ports、Owner声明与prepared/final current检查、严格portable doc与public管理DTO/ErrorEnvelope/CLIexport。生产与商用control-plane账本不混，官方账号失效不锁本地。
- **Media**：仅消费actual typed human/policy admission与rights事实，适配_admit/声明/严格新material，保同Run/普通fence/未知Op/限次，不创建policy/决定/validator。
- **Integration/Frontend**：Integration封装可信admin与resource/profile接口并从Backend实际schema生成；Frontend给简单的一次预授权配置/明确缺项恢复，普通制作不要求每片手填proof。管理员与模型执行能力不混，仍五步。
- **Test/Review/Acceptance**：独立准备/批准/执行原human不变、真正Owner注册/撤销/currentfloor/错误subjectproject/ref/fence、policy替换/恢复、预算组不重置、scope/route/rights mismatch、质量草案不发布、当前writer撤销竞争、旧unknown不重复、副本doc不自授，以及已授权真实API/MCP完整链。这里不是标准文件或通过声明。

本轮已有材料仅接口候选，真实管理动作/安装floor、policy准入、质量/许可和自动全链都未运行/批准。必须按上述本轮R1完整路径推进；外部服务/资质缺项保持证据，继续本地无依赖工作，不永久503/等待缩范围。全工具/source pins/UTF8-LF/JSON与费用/key/产品/测试/import/网络0在本轮正式Handoff固定。
