# ADR0037 — 一次 Owner 授权后的有界日常项目派生

状态：A34 设计批准，尚未实现/运行/独立验证。2026-10-10。
依据：ADR0036；B39 SliceB 正式 DailyProjectScopeGap/七源索引/Interfaces/StaticFinal；01、09、10、11 的本地免产品注册、五步及 API/MCP 一次目标到成片要求。逐件身份见 A34InputPins.json。完整 R1 三 OS 独验后连续 R2 不变。

## 1. 唯一路线与三处真实缺口

create_project 为每个新项目生成随机 ID；OwnerBinding、InstalledExecutionRegistration-v1 与 ProductionAuthorizationPolicy-v0.1 都只允许已存在的有限 project_ids，issuer._request/_record 拒新 ID。源码静态通过不等于日常自动项目接通。

选择“真实 Owner 一次批准有界创建委托→可信业务服务为实际新 ID 派生精确项目权限”。拒绝逐项目 CLI renew/replace、预造空项目、无限 wildcard 或模型管理权。原三处 v1 范围/字节/strong issuer 对象保持不变；新项目走有明确来源的派生分支，不能往旧 tuple 偷加 ID、假造 OwnerBinding/政策安装 receipt。

## 2. 一次真实授权及有限父委托

Backend 唯一维护 DailyProjectAuthorization-v1：id/revision/instance/domain Owner；原 Owner binding generation/action/authentication_binding_id；实际安装 record 及各角色原 current execution refs；明确 executing_principal_ids（本首版仍只有真实 Owner）、允许调用入口 api/mcp/native、有限精确 source system+namespace及原 article/topic revision要求；有效期；明确正整数 max_created_projects 和 max_active_productions；完整创作约束模板；原预算组 ID/不可变身份及每作品 cap；真实 Owner 原动作/ref/registry floor；current/revoked 状态。数量上界必须是真实 Owner 看见并确认的有限值，不能默填无限、循环重置或换任务名取得新计数。

模板保留原 Policy 的 routes/cost rule、语言/画幅/时长、交付/转移限制、allowed_actions、调用者文本是否允许、有限 input Asset ID+SHA、有限 source范围、alignment及全部质量检查、原 rights声明和修订限次，唯独不将未知未来 project_id 作为 wildcard。未来新 project 的权限来自“创建该实际项目并派生”的特定动作，不能挂到任意现存/外部项目。模板、预算、Owner声明、安装资格是不同事实；声明不变成 owned/licensed 权威，发布/平台权限不在此委托内。

install/replace/revoke/get 仅由实际 Owner OS/TTY 或受控 Native/headless 管理会话，经原 registry/capability/action_guard 明确执行。生产 bearer、模型建议、项目创建参数、Goal与 namespace 均不能安装父委托。父委托有效期不超过原 Owner/执行/模板有效期；当前权限不超出原实际安装、角色与 sources/预算资格。管理 binding 有限项目权限不自动获得未来项目权：Owner 确认的独立 creation 动作及其原 receipt 才是派生根；这是明确增量，不是管理 scope 偷升执行 scope。

首次空实例不预造占位项目：用户输入的第一个真实 Goal 可先保存为真实未授权草稿项目。一次真实 Owner 安装确认展示这个项目及上述有限创建范围，并明确授权完整 setup intent；Backend 按原 OS/目录与原 action/floor 协议完成 Owner绑定、真实环境登记和父委托。各动作有各自真实 receipt，链到同一已确认规范 intent/会话；不能用 True confirmer、模型字句或自动点击伪造原 AUTHORIZE。步骤中断保原 pending/exact intent，不能自动重复初始化。现有安装直接以原 Owner管理会话新增父委托，不 renew Owner或替换原执行登记。五步工作台把这一可选预授权放在初次配置/制作确认；后续作品不重复审核安装权限。普通交互审核模式保持。

## 3. 单 Goal 的可信、精确派生

可信 DailyProjectService 在同 Engine/Bundle/原 issuer 与安装 current 下接受实际认证执行主体；首版 App/Portal/API/MCP 均使用已映射为本实例 Owner 的真实执行身份，不能由 body 声称 Owner或把 source namespace 当身份。若未来要服务主体/多租户，必须另外版本授权，不在此偷偷接受 foreign actor。

输入仅项目目标/资料和原创作选项；creation_authorization_ref 可为非秘密 locator，或由实例为该主体明确选择的父委托解决。ref 本身不是票据。新 ProjectGoalInput-v1 保留 canonical Goal hash；服务生成实际随机 project_id，按该 ID 建唯一 ProjectScopeDerivation-v1：父委托 ref/fullSHA、原真实 Owner action ref、同实例/Owner/执行主体、实际项目 ID、Goal/input hash、原安装/执行 refs、精确 source/模板有效范围、expires_at、实际派生 service receipt/registry revision。子项目权限只取父允许范围的交集，不能改变模板、素材许可、资料库可见范围或源授权。

project-create+scope-derive+规范化原 ProductionRequest/Production/Run 接受与其绑定，在一个短 DB 事务中提交（Backend 抽取原 writer 核心接收同 connection，不嵌套调用另开事务的 public 方法）。writer 外先持原资源/资格 guard、OwnerControl→ProductionControl锁及父委托 current；按实际合法主体、入口/源/目标、到期、配额、安装/ref、预算与强对象核验。reserve 前先持久保存已实际认证受理的 Goal intent（固定原主体、父ref、规范输入/key、计划随机项目/Run ID、原接收事实），并按原 Owner pending 文件模式在受保护 Control 保留其规范恢复副本；它是已受理请求记录，不是可提交的管理票据。reserve 原 floor→原子写项目/精确子scope/唯一派生receipt/Goal journal/原Run→complete。同 key+同 canonical Goal 返回同项目/Run/子scope且计数一次；异 input 冲突。计数由原记录/事务承担，max_active_productions 在接受新Run时确定性检查，不按客户端连接或模型声称释放。

保 Goal 原始规范 hash 与服务注入 project_id 后的 ProductionRequest 原规范 hash，两者分开且关联；不能声称它们相等、改写既有请求字节或拿 Goal hash替 Operation 输入。响应 ProjectGoalAccepted-v1 指向真实 project_id、production_id、run_id及状态/查询；HTTP202 与 MCP create_project_goal 同源，同一次调用持续至原持久 Worker 制作/交付，断连不取消。已有 POST projects 行为保持：可保存未授权草稿，未选创建委托时不自动授执行。App日常创建及Portal一次新Goal必须走新同源入口，不能要求人再复制ID、换终端或补剧本。

派生耗用的是父委托的有限创建计数，不为每个项目造预算组或额度。所有项目/修订沿原同预算组的预留/实际/unknown；父配额耗尽只阻新派生，不撤销已授权子项目的进行中任务，不能回收子记录后重复利用 lifetime quota。收费/副作用仍先原 Operation；unknown不清、不重提，新项目不重置原次数。

## 4. 运行期权限接缝及版本

Backend 增加最小父委托/子派生两组持久事实（新迁移在已有8之后，编号以唯一实际源为准）；沿原 commands/registry revision/外部 ProductionControl保留 floor，不新建第二授权系统。原 Owner/执行/Policy记录不因新子scope更新；global revision增长是高水位，不能把“全局版本与启动时相等”当守卫。父/子 immutable body/ref、current/revoked/expiry与原命令/派生receipt分别重核；活动子scope snapshot不得包含别的项目消耗变化的 usage counter。新项目不切换原 Owner generation、不改变同role current执行指针，不使无关 Run/lease/fence/strong current失效。

原 issuer 保同 Engine 原 RegisteredExecutionIdentity 与 native binding。增加私有 typed DerivedProjectScope/current guard，来源必须为该 Engine 的真实父委托/子记录且绑定同原强对象/role/安装；复制 DTO/ref 不能构造它。_request 对原 project_ids 保旧判断，仅对确切派生项目核新scope；_record/bind_request/_bound 对新分支核明确派生 policy/selection/current来源。不得生成假的 human AuthorizationActionReceipt/create/select；派生 receipt 的 issuer=trusted_project_derivation，权限根=原 Owner creation action。子有效政策为明确 project_ids=[实际ID] 的完整有限体，分派模型仅能缩窄输入，不能更改授权模板。

新模型明确命名 DailyProjectAuthorization-v1、ProjectScopeDerivation-v1、ProjectGoalInput-v1、ProjectGoalAccepted-v1、DerivedProjectAuthorization-v1；ProductionAuthorizationDocument 新分支使用 version=0.2.0-candidate 与 source_kind=delegated_project，携真正 Owner creation action 和独立派生 receipt，旧 version=0.1.0-candidate/owner_policy grammar 不变。显式新 selection 来源 grammar 保旧v0.1 owner_policy字节与解析不变；新来源必须含完整父体/真实Owner动作/精确子体/派生receipt及原request/Run/admission关联。Media继续消费既有 CurrentProductionAdmission/lease执行接口；来源增加由Backend统一定义，Integration生成契约/SDK，不在媒体复刻权限。Bundle/RAG导出留完整派生来源闭包，导入仅 origin不授本机票据。

每次原 acceptance/prepare/claim/各制作阶段/finalize：资源/hash/RPC在 writer外；持原Owner→Production锁，短 writer重核父/子ref/current/expiry、原Owner/安装/执行current、真正项目所有权、完整政策/许可/预算及local strong epoch/thread/fence。父明确 revoke/replace/到期、Owner或安装执行换代应阻相关后续新副作用，保原 journal/已生成资产/unknown核实；需要恢复的请求只能走原可信 reauthorize，不假造人工ReviewDecision。单子项目撤销只影响该子项目；其 get/revoke 由父委托明确授给同一真实 Owner 的有限派生子管理动作处理，经原真实管理会话/capability及父→子准确链重核，不能因此扩大旧 ManagementPrincipal.project_ids 或普通执行 token的管理权限。新项目创建不会替换父授权或旧子scope。

## 5. 分派与独立验收

Backend先固定新父/子/Goal/source版本/迁移、真实Owner creation入口及同connection writer；再接 issuer、恢复和原预算账本，normal合法记录不得长期403/503占位。启动时和原执行 current 入口先运行有限 Goal-intent恢复：只识别本任务的固定 scope/原受理事实及完整受保护 intent，核原 key/input/父ref/current/Owner/资源/剩余额度，以相同计划ID完成尚未commit的无收费派生，或对已commit事实精确complete。父权限已失效或请求已不合法时，只以原 intent 记录明确 denied/cancelled 的无授权结果并提交同预留revision后complete（不建子scope、不收费），不能降floor、伪造成功或派发旧意图。恢复后的旧活动Run继续原current/lease/fence；普通项目派生的pending仅短时阻派发且不写撤销/失效到无关Run，不得长期全403/503或永久waiting。未知其它scope的pending/恢复副本损坏依原协议拒绝并等待真实Owner恢复，不尝试宽泛自动修库。恢复不依赖第二次客户端请求，DB/Control实际恢复和并发须独验，不能靠循环retry掩盖丢失事实。代码/模型唯一后端。

Integration消费新正式接口后生成SDK/MCP与完整新artifact；其原原生ABI/I57、installed record/guard仍独立必须真实接通。Frontend初次有界配置一次真实确认，日常建项目只目标资料→其余四步，使用新Goal入口/查询/事件。AgentMedia消费原typed admission，不管理父委托/项目授权，不补假流程作品。Test/Review/Acceptance分别独立：

- 空实例首个真实项目setup、已有实例安装委托；重启后真实App/API/MCP新Goal无需逐项目CLI到完整作品/多模态包，至少两个不同实际项目ID。
- 同key并发/中断/restart只一项目一scope一Run一计数，另一正文409；floor reserve/commit/complete边界恢复不重收费。
- A项目制作或unknown核实时并发建B，A原current/lease/fence/资产/费用/次数保持；配额耗尽只阻新创建，已有任务仍按原有效授权继续。
- 模型/普通bearer伪管理、foreign Owner/ref/instance、任意旧项目挂委托、模板/素材/source/预算扩大、父或子撤销/expiry/替换/DBrestore/tamper/跨issuer伪对象均明确拒绝；真实剩余预算共享，不能只有expected拒绝的测试。
- 原v1显式项目、真人审核及旧导出仍兼容；新来源导入不能授权，规定精度/质量/许可门及三OS不降。完整R1独验后连续R2，文档不算功能通过。

A34仅设计/固定普通源读取；产品/DB/Owner动作/native/模型/凭证/联网/费用均0。未修改01—11或独立标准，不读取B39热源。
