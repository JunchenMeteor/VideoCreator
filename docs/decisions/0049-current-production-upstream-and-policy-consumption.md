# ADR0049 — 同一 Run 的自动创作上游与当前权限消费

状态：APPROVED_DESIGN_ONLY。批准下述有限接口供原责任角色实施；尚未实现、运行、独立测试或验收。日期：2026-10-10。完整 R1 独立验收后连续 R2；本地免产品注册/BYOK、一次预授权 API/MCP 自动制作、五步界面、安装实例持有数据及三 OS 目标不变。

## 固定事实与范围

任务卡 `docs/task-board/CurrentProductionUpstreamAndPolicyContract.md` SHA256 `32657e9ac3600e964bee9771f5dcdcd459fb422ecbb07cbd380a98b0bb5750ca`。仅读普通固定副本：

- Backend102 `Backend/GoalReceiptIntentCorruptionCorrection/SourceStage/SourceIndex.json` SHA `0bbbd04a5014b0b512ed64d077b9058d80abfb24bb7178a68541ef7936adbd5e`。
- Media `AgentMedia/MediaCurrentEngineConsumption/SourceSnapshot.json` SHA `f605f65afa23c3521152727cf5619eba12587db4a0a218385a2f73627c198b45`；Handoff `02c85331cbf9ac9e22b97a5811f25e1ade23c208938a6e2d6df515abbacc1c33`、FactoryConsumption `ca0e99e15b2a96692da603a636872cd997024cf8dcce83ae7f8195b17268e883`、BackendGaps `128484c9ae37afb6874d024c9c7ce4296fd882190cb69fc810bea2b29c0f181f`。

`application/media_registration.py:32–44,97–132,162–211,239–275` 当前只有完整 Engine/ASR/FFmpeg 注册；invoke 直接读取六稿及四个 master，没有自主上游。`workflows/current_engine_production.py:18–81` 精确接收旧 ProductionPorts；不能强转 PolicyExecutionPorts。`production_admissions.py:716–744` 当前 production_rights 可在未提交计划时返回事实，必须调整时序。`autonomous_production.py:104–163` 原人工 _admit 不修改。`bundle_authorization.py:26,305–325` 授权材料已有独立 grammar；公开 Manifest 没有 production_authorization_refs 字段。上述事实不是产品通过；完整逐件 SHA/读取区间由本任务 InputPins 固定。

## 一、唯一注册与调用入口

后端唯一维护私有 `registered-media-config-v2`，extra=forbid/frozen，保留 v1 的所有字段和原意义：engine_source_sha256、asr_resource_manifest、asr_resource_manifest_sha256、asr_runtime_manifest_sha256、ffmpeg/ffmpeg_sha256、ffprobe/ffprobe_sha256、asr_route_id。只增加：

| 字段 | 精确意义 |
| --- | --- |
| autonomous_registration | 原 AutonomousRegistration，仍为 registered-autonomous-production-v1；五 route ID、driver_profile、max_duration_us 原类型/限制不变 |
| production_resource_manifest | 受信安装根内本地资源 manifest 位置；不是请求/模型可选路径 |
| production_resource_manifest_sha256 | 原 ProductionResources 所消费资源 manifest 的实际完整 SHA256 |
| production_runtime_manifest_sha256 | 同一资源 manifest 对应 runtime index 的实际完整 SHA256 |
| upstream_profile | literal current-registered-autonomous-upstream-v1，只选固定源工厂 |

v1 解析和既有成片行为保持；v1 不冒充已具备完整自主链。v2 解析、定位、安装覆盖及调用方签名归后端。同一原配置 SHA 是 registration_sha256，不再注册第二个配置、第二个执行身份或队列。生产资源必须落在原 installed resource map/PreparedLaunch/held resource/current issuer 所验证的同一安装闭包；包含实际 Python/Engine/Media 工厂、文本/图片/旁白/剪辑 route 与原 ASR/FFmpeg/FFprobe 全依赖。新增路径/SHA 只是完整性输入，不制造安装资格、许可、模型权益或 Owner 确认。集成按完整 source/lock/resource/build receipt 重建；保留原全部能力，不删缺证依赖求绿。

真实 RegisteredExecutionIdentity/current guard 的 registration/resource/runtime 身份须与实际 v2 闭包一致。旧 Run 已绑定 v1 时，不就地换配置 SHA 或改 immutable execution_binding；继续保留旧可恢复安装，或沿已有 Owner 有限重新授权/恢复机制迁移，不能暗改 floor/预算/unknown。AutonomousRegistration.rights_declaration 在人工路径是原有限 Owner 声明；在策略路径仅保留兼容配置数据，不能用它的 project_ids 替代原 current policy/delegated-project 实际范围，更不能伪造新项目成员或 wildcard。

`RegisteredMediaRuntime.invoke` 前半段调用受信固定自主上游，仍在原 worker bind 之后、master_assets 之前。复用该 Runtime 的同一 WorkerService/Engine/Bundle/Executor 对象及 PROFILE；消除现有重复 WorkerService 构造接缝。传原 ordinary lease、同一 cancel、deadline_monotonic、原 attempt/fence；心跳、停止与租约撤销照原 worker。Flow checkpoint 仅保存进度，不成为授权源。不得创建第二 Run/Production/预算、另起任务队列、接受客户端模块名/callback/path，或把预授权请求退化成必须手交四素材。

## 二、Backend 唯一维护的权利提案

新增私有 typed `ProductionRightsProposal`，extra=forbid/frozen，format literal production-rights-proposal-v1。后端定义实现并交普通固定接口；Media 只消费：

| 字段 | 类型/验证 |
| --- | --- |
| instance_id, production_id, run_id, request_revision_id, project_id | 原 c.Identifier；均取当前真实原 Run/Production/请求，不取模型声明 |
| request_sha256, registration_sha256 | 原 c.Sha256；与实际 immutable binding/原注册一致 |
| declaring_subject, declaration_id | c.Identifier；原 Owner 声明实际身份 |
| declaration_sha256 | c.Sha256；复用原声明 canonical/SHA 定义，不换序列化算法 |
| rights | 非空、rights_id 唯一的 tuple[c.RightsSnapshot,...]；当前此端口只允许 user_asserted |
| source | literal owner_declaration / owner_policy / delegated_project |
| policy_ref, owner_action_ref | 原 ProductionPolicyRef、AuthorizationActionRef，可空但必须满足分支规则 |
| fencing_token, checked_at_us, valid_until_us | strict 正整数；fence=实际 ordinary lease，valid_until>checked，受租约/实际权限/权利有效期共同限制 |

owner_declaration 分支只能来自可信安装携带的原 Owner 有限声明，policy_ref/owner_action_ref 必须为空；此时不是 human_review，因为尚无计划审批。owner_policy/delegated_project 分支必须携带完整原 policy_ref 与真实 owner_action_ref，来自原 _bound/current record，按原 derived source 区分。project_id 始终取当前 Production；原声明本体/hash 不改写项目成员。子项目范围由真实 derived authorization 链证明，不能由提案 JSON 扩大。拒秘密字段/未知字段。提案没有 plan ID/SHA、ApprovalRef、ProductionAdmissionRef、allowed 布尔或执行权；不能从 user_asserted 升为 owned/licensed。

精确增加 `PolicyExecutionPorts.rights_proposal(ordinary_lease) -> ProductionRightsProposal`：复用实际 current_guard、_bound/current binding 与 begin_execution 事实检查，读取同一声明和真实来源，按原短 writer/读取规则给快照；不得新建 policy/admission/费用操作。人工 `ProductionPorts.rights_proposal(ordinary_lease)` 返回同型 owner_declaration，按原 binding/Owner/project/有效期核实，不取消原 `production_rights` raw tuple ABI。

模型拟定的 plan 提案只合并服务返回的完整 rights 和提案来源快照；模型自带 rights/scope/approval 不能覆盖。第一次提交时把提案快照与 plan 同步存入原 immutable creative revision。恢复已有 plan 时复用原字节/原 SHA，不因新 fence/时刻重写计划；以当前可信来源重新校验执行。历史提案过期不是新执行许可，也不能覆盖新 current source 或实际撤销。提案记录与之后的实际权利事实分开。

## 三、实际时序与三个权限来源

| 阶段 | 唯一真实来源与顺序 |
| --- | --- |
| request | unattended：原 bind_request 不是执行权；进入 CreativeCrew/任何新创作副作用前调用现有 PolicyExecutionPorts.begin_execution(lease)，保完整 CurrentProductionAdmission，核 allowed/同 request/registration/fence/time/current。interactive：沿原普通请求/lease guard；禁止伪造 source=human_review 的 request-phase 事实，现模型明确不允许 |
| insight→brief→script→storyboard→plan | 同一 Run 原创作版本与实际文本 route/账本；先取 rights_proposal，再提交真实 plan；不可提前猜计划 SHA 申请许可 |
| plan | unattended：复用 production_admission(lease,实际已提交 plan ID,phase=plan,action=execute_plan)，核真实 revision SHA/全部 refs/time/fence。interactive：保持原 _admit/实际 ReviewDecision，再读当前真实 typed 人审事实。非 allowed 不生成 |
| plan rights | 将现有 PolicyExecutionPorts.production_rights(lease,plan_id) 收紧为已提交、当前 execute_plan 已准入后的原 ProductionRightsFact；校验实际 plan.rights 与原声明一致，保 declaring subject/声明 SHA、全部来源 refs/time/fence。不得再将未来 plan 当实际事实 |
| generation/master | 前述计划事实当前有效，原 prepare/claim/current_operation guard 逐次复核；所有副作用先原 Operation/Reservation/预算账本，传原 full OutputReservation、cancel/deadline。不得把事实序列化快照当长期许可 |
| quality | 实际 master/探针/QC 形成真实 quality revision，随后现有 production_admission(...,phase=quality,action=continue_bundle_validation)；允许继续校验不代表 QC/版权/精度通过 |
| final_manifest | 原唯一 Bundle publisher 用实际 Ready/Manifest 完整校验上下文，在发布同一 writer 调用既有 finalize_bundle current hook；以实际 Manifest SHA 为目标，保 full refs/time/fence，禁止预猜 Manifest 或自包含最终许可哈希循环 |

策略 Media 工厂唯一固定为 `create_current_policy_engine_services`，位于已有 current_engine_production 模块，接同一 Engine/Worker/Bundle/Executor、真实 PolicyExecutionPorts、原 AutonomousRegistration 和原资源参数；返回新受控策略消费 services，与原人工 factory/旧 callback ABI 分开。新增策略消费者直接保留 CurrentProductionAdmission/ProductionRightsFact，不能强转成旧 tuple、虚构 ReviewDecision 或给旧 _admit 一个“同意”回调。共享固定 driver builders/生成/剪辑方法，不注册第二套框架。

人工桥接由后端在原 ProductionPorts 增加 `current_production_admission(lease,revision_id,*,phase,action)->CurrentProductionAdmission` 与 `current_production_rights(lease,plan_id)->ProductionRightsFact`。前者只支持 plan/execute_plan、quality/continue_bundle_validation，读取原实际 immutable revision/真实 approved decision/完整 ApprovalRef、安装绑定与 lease/current 有效期；后者仅在该真实计划审批当前有效后构造 human_review 分支。原 production_admission/admit_revision/production_rights 兼容；原人工 _admit 代码/真实待审流程不改。桥接不写假审批、不接受 renderer/model 布尔、不把无人值守改为 human-only。所有 current 校验在原受信 service 中；Media 仅保留事实，不复制权限规则。

## 四、结果、租约与唯一成片生产

后端定义跨角色私有 `CurrentProductionUpstreamResult`（extra=forbid/frozen）：run_id:c.Identifier、fencing_token:strict正int、state literal masters_ready/waiting_user/waiting_authorization/resource_not_ready/denied/needs_reconciliation、media_roles:dict[str,c.Identifier]、blocker_code:c.Identifier|None。masters_ready 必须恰有 video/narration_audio/mixed_audio/cover 四个不同实际 Asset ID，无 blocker；其他状态不得声称 masters_ready。不向公共请求暴露这个模型，不从任意 provider JSON 构造成功。原旧 UpstreamResult ABI 保持，人工受信适配器在验证真实 Run/lease/返回状态后映射，不伪装策略结果。

- masters_ready：核结果同 Run/fence，重新读取当前真实六稿/已 settled 原 Operation、原 master_assets，四 Asset ID 必须与结果一致；再取当前真实 plan/quality admission 与完整 RightsFact，进入原 create_registered_media_producer。仅最后实际 Bundle published 才生成 ProductionSuccess。
- waiting_user：原人工 wait_for_review 已释放 lease 时，读取真实同 Run 已待审状态后直接结束本轮；不能再调用 park、写 master 或用已撤销 lease 更新。若仍持有 lease，后端原 park 路径仅一次转换/释放。
- waiting_authorization/resource_not_ready：后端用同一原 Run 的受控前置阻塞记录及既有 waiting_user 状态表示具体缺授权/资源，单次释放；不得伪造审核 revision/ReviewDecision。具备真实原预授权与资源时自动继续同 Run，不再逐项目提示；恢复必须实际解除 blocker/current/source，再由原队列取得新 fence，预算/限次不重置。
- needs_reconciliation：实际原 Run/Operation 必须确实需核实；保原 unknown/submitting/settled 状态、原 allocation/输出文件/费用记录，结束本轮。查询/核实走该原 provider 的受控端口；不得把 ASR journal 当 WAN 查询器，或重新提交 unknown。尚缺查询资源保持具体 not_ready。
- denied：按原 Run 失败/拒绝记录结束且无后续生成/发布；不重新授权、不清 unknown、不放大预算。deadline/cancel/租约失效采用原终态逻辑。

Media 为唯一 producer 增加兼容私有 keyword `plan_admission:CurrentProductionAdmission|None=None`、`production_rights_fact:ProductionRightsFact|None=None`。v2 由可信 Runtime 提供完整当前事实并校验实际 plan/request/source/fence；v1 旧调用保持。不得把 artifact/plan scope 传成来源宽 grant。

policy 分支另从原 issuer.authorization_document(实际 plan_admission.admission_ref) 获取真实 document；使用现有 Backend `stage_production_authorization`，分配并提交独立 material/Ready receipt，唯一 schema_kind/role=production_authorization、MIME=application/json、路径 `Checks/production-authorization.json`。实际文档可为原非派生版本或 derived V02，严格按原 grammar 派发，不自行改版本。将材料进入原 ArtifactIndex/完整 Ready/Manifest 闭包，refs_from_ready 得到真实来源供 rights/current publication 校验。公开 Manifest 不新增 production_authorization_refs；该集合是原私有 final context。human_review 分支保原真实 ApprovalRefs 和 rights 快照，不伪造 policy authorization document。

继续原源稿/字幕/实际 ASR/旁白/混音/视频/封面/RAG/Bundle 原子交付、原音视频坐标和原 precision/版权/许可/预算校验。承诺完整媒体 chain 不能以四素材人工分支当完成；也不能因成包接口批准就跳过 ASR 被拒 supervisor 变更或真实独立资格。

## 角色切片与独立验证

后端先固定上述私有类型/ports/config-v2、实际 guard 和 invoke/dispatch 接缝，唯一维护字段/序列化/可信来源；无新增公开路由或新 DB 许可账本的默认授权。若现 blocker 持久字段不足，先交最小迁移/接口实际差异供架构确认，不能用 fake quality revision 填空。Media 随固定接口实现策略 services/Flow、人工事实消费、唯一 producer 授权材料；绝不写 Owner/预算/权限/领域模型。集成由唯一公开源生成必要契约，重建完整 current Engine+Media/资源/许可 producer，与原真实安装 carrier/current source 对齐，不让新 config SHA 自证资格。前端消费既有阶段/具体 blocker，无模型审批按钮或逐项目反复日常授权。

测试开发独立固定并运行：同一 accepted Run 自动六稿→plan→真实四 master→原 Bundle；interactive 真实待审/三来源完整 refs；已提交 plan 与未来 ID 拒绝、提案被模型改写拒绝、历史 plan 恢复不改 SHA；v1 兼容、v2 identity/whole-map/current/revocation/missing resources；等待后不二次 park/旧 lease 不写、masters_result 与 ledger 不符拒绝；plan/quality current 到期或新 fence拒绝；original unknown 查询不重交/费用限次不重置；授权材料与实际 receipt/hash/版本一致、不存在公开虚构字段；真实齐全作品的全部原 QA/精度/许可/原子发布。模拟只验证状态，不冒真实作品。评审独立读源/标准；验收独立看视频听音频并核真实接口/三 OS，当前文档不批准标准/资源/法律事实或质量。

缺 actual installed qualification、文本/图片/旁白 route 凭证及权益、许可、WAN 原 unknown 查询、模型服务预算、三 OS 或被拒 ASR 补丁，逐项 not_ready 并继续无依赖实现；不永远以占位 503 代替已要求的完整产品实现。此 ADR 不授权模型调用/付费、ASR 激活、Owner 行为、安装/系统/native 执行或部署；已有共享预算和原拒绝保持。本轮架构没有读热源、运行产品或测试。
