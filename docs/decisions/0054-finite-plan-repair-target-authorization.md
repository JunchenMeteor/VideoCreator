# ADR0054 — 原方案有限修复目标与真实执行权的关联

- 状态：APPROVED_DESIGN_ONLY，2026-10-10。批准本合同的实现方向，不代表实现、权限实测、素材许可、作品质量或 R1/R2 验收通过。
- 范围：当前 AffectedRepairTargetAuthorizationContract（d597e95bbcc96f090c1ebfdbe0b3dff8303a6d4cd5fd4fcbdbbf8acd74ece958）。仅具体化 ADR0053 第3节缺失的原 plan 目标；0053 原字节不改，其他账本/恢复/precision/child 规则继续适用。
- 唯一接口/存储作者：Backend。Media 只消费该作者的类型和 held ports；Architecture 不写产品类型或实现。本卡没有产品运行、DB、网络、模型/ASR、凭证或费用动作。

## 1. 已核事实与决定

固定 Media 原方案仅包含 proposal、rights_proposal、rights、timeline_duration_us、workflow_candidate，没有修复制作目标。真实原生产依次执行 production-narration、每个 production-<shot_id>、production-edit；最后四母版来自原 Worker 的实际登记映射。不能把模型提议、质量 approval、失败单位或 clip/Asset 哈希当作重新生成权。

固定 Backend human bridge 从原 decisions 读取真实 approve，关联同 Run 的不可变 plan revision/body SHA；policy bridge 从当前 Owner record、原 bind_request 和 execute_plan action 关联同一完整 plan SHA。原政策已有有限 routes、input/source/rights、预算与 max_revision_cycles，不需要新增公开 capability 或第二套授权系统。

批准唯一方案：Backend 生成有限制作目标投影，Media 在新 plan 的不可变正文中保存它；原 execute_plan 真实审批绑定整份新 plan（包含投影）的 SHA。允许修复是对原已准目标和原输入的有限再执行，绝非新创作目标授权。Backend 在 authorize_affected_execution 中独立重算投影及当前权限，并将实际失败依赖闭包与原目标相交。缺投影的旧 plan 保持原字节/原批准，不自动回填、补签或扩大语义。

## 2. 唯一私有数据合同及生成入口

Backend 在现有 affected_repair/registered_production 领域层维护 strict、frozen、extra-forbid 的 PlanRepairTargetsV1，format=current-plan-repair-targets-v1。它是方案数据，不是 authority，可序列化进入 plan body。完整成员：

| 成员 | 语义 |
| --- | --- |
| binding | 原 ProductionBinding；沿用原格式/字段，包含同 instance/Production/Run/request/registration 和实际输入 Asset ID/SHA |
| resource_manifest_sha256、runtime_manifest_sha256 | 原真实 registered runtime 的两个完整身份，不接受 Media、模型或 renderer 填写 |
| script_ref、storyboard_ref | 各为 {revision_id, content_sha256}，指已提交同 Run 的实际 script/storyboard 完整 CreativeRevision 字节 |
| rights_declaration_sha256 | 从本次实际 ProductionRightsProposal/真实声明来源取得；同 plan.rights_proposal 与 plan.rights，不升级 user_asserted 为 owned/licensed |
| allowed_action | 恰 regenerate_affected_media；realignment 继续0053原合同，不由本投影增加 ASR/对齐执行权 |
| max_revision_cycles | 原 request 的剩余规则所用总上限；unattended 同时受原真实 policy 上限，保存两者最小总上限，0允许但不能修复 |
| targets | 有序、不同、有限 PlanRepairTarget 数组，恰覆盖当前真实原方案组件，不能任意追加 |

PlanRepairTarget 完整成员：target_id、kind、shot_ids、timeline_range、route_id、route_sha256、resource_section、resource_section_sha256、input_revision_refs、input_payload_sha256、prerequisite_target_ids、output_roles、dependent_media_roles。

- target_id 是原组件 Step 身份（production-narration、production-<实际shot_id>、production-edit），不是新 Asset ID。kind 恰 narration / shot_clip / edit；shot_ids 是原方案中的不同 shot ID 子集；timeline_range 为原整数微秒半开区间 {start_us,end_us}。不得使用毫秒、模型浮点、范围外 shot。
- route_id/SHA 从原 AutonomousRegistration 指定的 narration/picture/edit route 与真实 configured_route 完整正文取得；不得接受任意 route/module/callback。resource_section 恰 narration/picture/edit，对应同真实资源索引的该部分 canonical JSON SHA；完整 resource/runtime identity 同上层。资源路径、代码、模型、许可仍受原安装 coverage/held guard，不由此 DTO 取得资格。
- input_revision_refs 是有序不同 {revision_id,content_sha256} 数组，指原已提交的同 Run 源稿/分镜；请求中的文章/选题版本与原 input Assets 由 binding.request_sha256、input_assets 和原 source policy 继续完整约束，不能只检查名字。
- narration 的实际输入 payload 来自原 script.body；shot_clip 来自原 proposal 与 storyboard 中逐项相同的原 StoryboardShot；edit 的稳定模板来自实际 storyboard.body、按原顺序的 clip target IDs、narration target ID 和本驱动的实际输出角色。template 中 target locator 只是组件引用，绝不能伪装成尚不存在的 Asset ID。运行时由 Backend 从真实原 Step 或同 command 的已登记新 Step 解引用为实际 Asset，形成具体 Step input。
- input_payload_sha256 绑定上述原 payload/稳定 edit 模板；prerequisite_target_ids 恰表达原组件依赖，narration/clip 没有假的前置，edit 指向实际 narration 与 clips；环、缺失引用或新增组件均拒绝。
- output_roles 只记该原组件的实际输出角色：narration_audio；shot_clip 这一组件输出类别（其实际 clip role 仍是 shot_id）；或 edit 的 video/mixed_audio/cover 有序子集。dependent_media_roles 只可取最终四 role：video、narration_audio、mixed_audio、cover。映射须来自原受资源覆盖的真实驱动/编辑配方与源码、实际媒体映射，不能由模型猜测或默认全四母版。Backend 固定当前驱动的真实配方映射，Media 实现按选中角色输出的实际 driver；缺少配方/选择性输出实现是明确 NOT_READY，不计作支持。生成许可不能靠“反正重做全部”扩大。
- arrays 按原方案/配方的固定顺序编码；不同键重复、shot/route/refs 对不上原事实、无源 payload、secret、NaN/Infinity、未知字段拒绝。合法组件数由实际原方案决定；当前固定 CreativeProposal 恰三 shot 的事实不等于新通用 shot 数量限制。

唯一新增数据生成入口：

`production_services.prepare_plan_repair_targets(ordinary_lease, *, proposal:CreativeProposal, script_revision_id:Identifier, storyboard_revision_id:Identifier) -> PlanRepairTargetsV1`

入口由 Backend 注入实际同 runtime services，human 与 policy 共用确定的数据生成算法，但消费不同真实 source/current guard。它从服务持有的 registration/resource/index、原 request 和已提交源稿/分镜读取真实身份；传入 proposal 只是候选意图，须与实际提交的 storyboard、源稿选择、时间范围和来源逐项核实。不接受 caller binding/route/resource/authority、user bool 或 replacement Asset IDs。生成投影不声称 plan 已批准，不消耗修复次数，也不开始 Operation。数据取得阶段只有原 request/pre-plan 权限；execute_plan 仍在真实 commit 以后才取得。

## 3. 新方案写序与无环身份

新 plan body 用 format=registered-production-plan-v2，保留原五字段，增加 repair_targets=上述 model_dump(json) 原数据。公开 CreativeRevision 外层/ReviewDecision 原类型不变，body 继续既有 JsonValue；新版本由 Backend 唯一 strict dispatcher 验证。不是向公开请求增加生产 capability。

顺序：真实 rights_proposal → 原 insight/brief/script/storyboard commit → 上述 Backend prepare → Media 构建 v2 plan → 原 commit_creative_revision → 原真实 human/policy execute_plan admission → 当前 ProductionRightsFact → 原制作与后续质量流程。Backend commit 对此 format 重读实际源、registration 和投影模板，独立重算；数据来源不一致拒绝提交。它不在 commit 时伪造 Owner 审批。人审/政策 admission 在数据已提交后再核同一投影和整份 plan SHA；旧“只检查 rights 数组”不能成为 v2 的全部校验。

投影不包含自己的 plan_id、plan SHA、执行 admission/decision ref、future command SHA 或 future Asset ID；这些身份由真实 commit/admission 后的原记录与0053命令关联，避免自哈希循环。恢复不生成第二投影/第二 plan，不按最新时间随便挑 plan。父 preparation/assembly/原 journal 与已提交 command 所绑定的确切 plan ID/SHA 是选中目标；writer CAS 与实际当前 admission 都要一致。真正需要新 plan 时须新不可变 revision、parent/input refs 和真实新 target approval，原正文/旧 approval 永不覆盖。

所有新数据 SHA 明确采用递归 JSON 数据编码：Backend 自己的 typed model.model_dump(mode='json')/已验证 JSON tree → json.dumps(ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False) → UTF-8 bytes → SHA-256。defaults/null 依唯一 Backend 类型实际 dump 保留；禁止 JS JSON.stringify、字符串拼接或调用仅接受 BaseModel 的 engine.canonical(dict)。固定 engine.canonical47/digest51 的已有行为和原 Goal hash 不改。revision_ref SHA 仍取原数据库保存的完整 CreativeRevision canonical 字节，不误用 inner body SHA；文件 SHA/有LF文件 SHA 与新 typed payload SHA 分列。现旧111 revise 的 canonical(dict) 是正在作者处理的源缺陷，不是本卡运行成功事实。

## 4. 权限来源：原动作内的有限再次执行

新的 allowed_action 是数据中对原 execute_plan 的有限修复用途描述，不添加 policy.allowed_actions 枚举或把 continue_bundle_validation 升成生成权。

- unattended：原可信 issuer/current_guard、同 request 的当前 binding、真实 Owner policy/action、begin_execution、execute_plan、continue_bundle_validation、rights、route/cost/resource/source/input、期限和原共享 revision_cycles 全部需当前适用。新 v2 plan 由真实 execute_plan admission 绑定；repair 只重新执行投影中的原组件及完全原输入/编辑模板，在当前 min(request,policy,投影总上限) 的剩余次数中进行。原已经安装的政策若真实允许这些 execute_plan/routes/input/成本/有限修订，可直接批准这个新 v2 plan，不再逐作品/逐修复伪人审，不需要另建公开 repair capability。旧没有投影的 plan 或超出这些原条件不因此获授权。
- interactive：原 subject/production scope 与真实 ReviewDecision.approve 必须指向包含投影的新 plan revision，原 decisions 的 request/decision SHA、target SHA和 human_approval_ref 均按固定 production_ports 方法读取核验；后续 repair 只消耗该实际已批准范围与原 request 修订次数。原 quality approve 只准质量阶段，绝不代替 plan 执行 approval。新范围不在实际已批准投影中则 guidance_required，不借旧 plan/quality 自动填目标。
- expansion：改变源稿/语义输入、增加 shot/route/来源/输出角色、改资源身份、增加预算或次数，都不是“同目标再执行”。交回原真实修改/审批流程：同 Run 的新 plan 只有实际新 immutable target 的真人 approve 和仍然合法的原 request/Owner scope 才能用；原 submit_decision(action=revise) 若按既有规则创建新 Run，保持该真实语义，不能假装同 Run 原 repair。Owner policy 外范围需要其原真实管理/再授权来源，不由本卡创建这个权力或用 model DTO/CLI receipt 冒充。
- current/revoke：数据/历史 approval 可保留供恢复和诊断，不能冻结权限。每次实际受控 prepare/claim/观察/child 写入/发布之前仍真实重核原 issuer、当前人审来源、许可用途和有效期、policy 撤销/替换与 binding、lease/fence、取消/期限、unknown/共享预算。旧 fence、另一 policy/action/request 或过期文件身份不能复活旧命令。Owner user_asserted 不能冒独立 owned/licensed 许可；Bundle 完整许可闭包不削减。
- realignment 继续0053原 actual audio/text、原权限与 qualified driver 路径；该投影既不授权额外 ASR，也不重开被拒的 ASR supervisor。

## 5. 既有 held 执行口与持久恢复

保持0053 sole `authorize_affected_execution(ordinary_lease,continuation,proposal:AffectedRepairProposal)->AffectedRepairExecution` 和它的成员原样，不向 Media 加一份第二授权 DTO。Backend 从原 report/actual failed units、material/input lineage、实际父四母版和上述确切 plan 投影重算：

1. proposal IDs/action/roles/shots 必须恰是原 observed failure 的允许依赖闭包与原有限 targets 的交集；模型只可提议缩小确有依据的集合。没有真实 failure 或没有 dependency map，不生成 held execution。
2. 再生成只有 projection 里的组件/原payload可执行。使用实际依赖闭包决定 changed_media_roles；未影响角色保原 Asset ID/SHA/时钟。新配方若实际要求额外输出变化且不在已准交集，拒绝并指导，不自动重做四母版。不能用原合格音频作为新音频的假 ASR/precision 证据。
3. 当次真实 current source/plan admission/rights、scope与 lease/fence 核验后，以原0053短 writer 持久当前完整 immutable repair command。原 current-final-affected-execution-v1 不改成员和 schema；其封闭 canonical command payload 的 plan/source/route/resource identities 内增加 repair_targets 格式与 body SHA、确切 target IDs 和原 input 模板 SHA。没有 command 就不能派发，也不能仅因返回 held对象而跳 SQL 内核验。
4. 原 writer 外真实 guard+资源/文件检查与 writer 内实际 scope/lease/journal/来源 CAS 两段都保持。恢复由这条 command、选中父/子和原 target refs 重获当次 held execution；无最新方案猜测、无新 key 重交。原 unknown/unsettled 仍仅原受控 reconcile，不被 target 数据清除。
5. 同原 Production、共享预算和 counter：command/replay 不增额度、不加 Run、不重计修订；0053 child/counter 一次原子提交和失败保账语义继续。恢复 target 未变而 fence 更新只能当前 scope 后重新签发 held对象，不改实际旧 Operation 身份。
6. Media 用同 ProductionServices 请求真实 target 数据，提交方案后保持真实 plan/rights fact，再从 report 提出原 proposal、调用上述 held口、按选中 targets 构建原 registered drivers/Step。输入和 output allocations/decoder/READY/观察/child选中依旧 Backend 签发；Media 不私读 metadata、SQL 或填新 Asset ID。

不新增业务表/公开路由作为本卡前置：目标原文在原 creative_revisions.body 持久；关联在原0053 immutable command；实际 approval/source 在原 admissions/decisions。Backend须让 initial、恢复、preclaim、child/发布都用同一严格 target resolver，不能只在 initial 校验后恢复忽略。本卡元数据版本不覆盖已存在 v1 command；带目标绑定的新 command canonical payload 明确标 target format，旧未绑定 regeneration command拒绝/待指导，不就地补“已经获批”事实。

## 6. child-ASR 私有读取的必要具体化

作为0053第5节“真实登记且消费”的具体 ABI，批准 Backend 同唯一 held port registry 的：

`registered_child_asr_intent(ordinary_lease,execution:AffectedRepairExecution)->c.OperationIntent|None`

只返回从原真实已持久 command/selected child/audio/input/完整 SHA 精确登记中取出的原 intent，不猜 route_id、不信 renderer config、不由 route SHA 反推。调用先真实 current guard、当前 lease和 retained execution registry、同 Run/完整 command/selected child lineage重核。None 仅服务从实际父子 audio byte/time 身份核实没有新 ASR需求；有需求却未登记/丢记录、无 child/command、冲突、unknown，须分别明确 waiting/not-ready/conflict/reconciliation，不能None掩盖。返回的是原 intent 数据，不授第二 dispatch 权；context先commit/claim/dispatch/settle和确切 ASR alias闭集按0053。若为验证旧unknown而需要读取，继续原受限 reconcile 口，不借本口重新发起。

## 7. 实施与独立证据

| Owner | 最小可实施切片 |
| --- | --- |
| Backend | 唯一 target 类型与 prepare服务；commit/admission严格 v2验证；原 current_repair_scope/held authorize 的 human/policy两真实分支；原 command/恢复/Operation/child/发布共用 resolver；精确 child-ASR getter；限原 metadata不猜权限 |
| Media | 同 runtime ProductionServices 声明并消费唯一 prepare类型；在第一次真实 plan commit前加入v2投影；旧恢复不补造；failed-unit真实闭包与held command；实际 selective driver输出/原input再执行，缺能力明确NOT_READY |
| Integration | 仅当sole接口确有公开形状变化时从Backend唯一源再生成；私有方法不手写SDK。实际装包资源索引须覆盖新增Backend/Media源码与驱动配方，不凭旧index授新源资格 |
| Test/Review/Acceptance | 分别维护标准/运行、独立审查、最终实看实听验收；本ADR不是这些证据 |

独立至少覆盖：有真实Owner预授权的同Run新v2 plan下合法失败子集能完成修复/child/成片而无假人审；interactive真实plan批准同目标可修，quality-only不能；未准shot/role/新input/route/来源扩大拒绝；错误plan targetSHA/原payload/source/currentrights/route或资源身份、撤销/过期/旧fence拒副作用；仅picture问题不悄悄重TTS/其他母版；错误/缺依赖图不采用全角色fallback；同command重放/kill/restart恢复target和实际输出，Operation不重交、shared budget/counter不重计；legacy无target正文/审批不变且不能regen；two authorities/实际P95>200ms不得靠审核洗绿；准确子ASR原intent/None与缺登记区别。状态测试可用受限可重复 fixture；真实许可/来源/解码/生产路径必须另有真实证据，不能mock True当生产。

当前生产缺件和配方选择性输出仍要由原Owner实现与实测。qualified-local-alignment选型a3766d2、Local/BYOK factory b9b53f继续queued；Wan未配不等于通用本地工具无功能，但不在本卡研究/安装。完整R1五步、API/MCP一次真实预授权到视频/音频/文本/RAG/Bundle、本地持有/免注册、三OS和后续完整R2目标不缩。

## 8. 固定来源

以下均普通停片；只读了必要完整方法/范围并核完整文件SHA，没有读 Backend/Media 活源，没有运行这些实现。

| 来源 | 完整SHA / 必要读段 |
| --- | --- |
| Repo AGENTS.md | 6de878f514b02788f8af5ba512f71c56bb053f6800d76cf19f3cdd955b7f6a0d，全文 |
| 本卡 | d597e95bbcc96f090c1ebfdbe0b3dff8303a6d4cd5fd4fcbdbbf8acd74ece958，全文 |
| PlanRepairTargetSourceGap.md / JSON | 02d575103f7ea8e12b1ffb12a75d005f3b8b29bc45065296b34a9c3030e96816 / 3b007e673e5d06b288853f7f84fba130a9986657185f8084d029df559183f178，全文 |
| Media BeforeSources/workflows/autonomous_production.py | cf48034e3aabae421414ef65eb0f7a3dbe401e830dabf18ef086356d44c93e10；170–360、418–460 |
| Backend EarlySources/domain/affected_repair.py | 9768bc4220283c2265d7e185a32343d1b5d88e83733ee1b4efd1d5252e05589d，全文 |
| Backend111 domain/production_authorization.py | 292aa2230c6247b39f7859277f3580e7d9520921f255a182338dea5ef0f4c5ef；1–206 |
| Backend111 application/production_ports.py | 8ca2a680ac338a5f8d8f9c77972f9d54a978781bf3398c7098d9d28e97ffb324；80–179 |
| Backend111 application/production_admissions.py | 3b98f33b18711652ebb3850a3c8a2f23aaa368cadc8baa835e543b7938644e05；545–629、639–678 |
| Backend111 application/engine.py | 2147139ec45b84ad495536df66e03ebdf5de356473b80d06d0f992ac3a5277ff；47–53、813–901 |
| Backend111 domain/contracts.py | 175d105c6c80415b14d0f4a5b69f841548b7fbc968d3058f55d13e1cba5284ec；421–511 |
| Backend111 domain/registered_production.py | 9dcac6ce2b27bb7e3f7cb541e57e790ebb5d415796fb8e66158c7cae021eeb0a；19–102 |
| Backend111 application/current_final_evidence_service.py | 6a8181ee3507ca03810d98a68f8e9b058f89b5e1d750c57cd3f321f8a215444b；68–113及索引，不声称审完整实现 |
| ADR0053 | 8d03886c3cb905ae5399811b7e2e0f95bcdbea62f81c396e58c6771d3522477e，第3/5节必要条款；原字节不改 |

准确普通路径和读后未变检查在本任务Architecture目录InputPins/SourceAfter；schema/实现/API/测试标准仍分别由原角色接续。本ADR冻结后不跟随活实现追改，新的冲突另固定来源再裁定。

