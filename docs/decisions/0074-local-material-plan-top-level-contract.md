# ADR0074：本地素材计划顶层结构

状态：APPROVED_CONTRACT_ONLY；待独立设计评审。只批准下列数据合同及接线职责，不代表实现、运行、权限、资源或作品质量通过。

## 决策

采纳停止提案 `PlanTopLevelProposal.md`（SHA256 `a12dc74ff3a99b65903aabc4913be1635744a1581b6a1e0c481c15db5c8f6b4d`），补齐其类型与来源约束。唯一维护者为 Backend 的 `domain/local_material_production.py`。0072、0073及旧 Goal、request、Creative、注册和作品包格式保持原字节及语义；本补充不新增发行资格、授权门、账本或 Engine。

`LocalMaterialPlanV1` 恰有以下 **11 个顶层字段**，禁止额外字段、重复 JSON 键或隐式别名：

| 字段 | 唯一类型及来源 |
| --- | --- |
| `format` | Literal `registered-local-material-plan-v1`。 |
| `request_ref` | 新数据类型 `LocalProductionRequestRef`，恰含 `instance_id, production_id, run_id, request_revision_id: c.Identifier` 及 `request_sha256: c.Sha256`。来自同一实际 Production/Run 的原不可变 request revision 与原 Engine canonical request SHA；不是 Goal SHA，也不重新用本地计划编码计算它。 |
| `goal_ref` | 新数据类型 `LocalAcceptedGoalRef` 或 null；恰含 `project_id: c.Identifier, goal_sha256: c.Sha256, derivation_ref: ProjectScopeDerivationRef`。后者复用既有 `{derivation_id, content_sha256}`，不使用 `RevisionRef` 假充 Goal。真实 daily/native Goal 路径必须关联原 `_AcceptedGoalIntent`、`ProjectGoalAccepted` 和同 Production/Run/request revision。null 仅用于原受控记录证实没有 accepted Goal 关联的 direct production；缺失、损坏、悬空或冲突的 Goal 记录不是 null。 |
| `material_refs` | `tuple[c.AssetRecord, ...]`，按每个不同 `asset_id` 保存原完整记录，含原 `source/rights/probe`。其 asset 集合恰等于 `input_bindings` 的 asset 集合；同 Asset 的不同 usage 共用一条原 AssetRecord。文件路径、URL、输出 masters 或新造 Asset 均不能代替原已导入素材事实。 |
| `input_bindings` | `tuple[LocalInputBindingV1, ...]`，复用0073及停止 EarlyTypedAbi 的八字段。对应 asset/SHA/size/MIME/probe/source_ref 均须等于原 AssetRecord；`source_ref` 是其原 source 字符串。按0073生成唯一 binding_id，所有 timeline 引用只用 input_binding_id。 |
| `timeline` | 停止 EarlyTypedAbi 的 `LocalTimelineV1`；shot/track、尺寸、帧率、整数微秒半开区间及 binding usage 规则不变。下述 fit/gain 为实际合成参数，不是权限。 |
| `source_script_revision_ref` | 原 `c.RevisionRef`，`kind` 必须为 `script`，绑定真实已保存的 script revision 及其原完整内容 SHA。`CreativeRevision` 对象本身没有 contentSHA 属性；须复用原持久记录及原内容编码，不能仅 hash 文本或虚构七种 Creative 版本。 |
| `source_script_origin` | Literal `user_provided`、`model_inference`、`input_audio_transcript`。应用层核原输入/模型方法或原 settled input-audio ASR 来源；后者不允许把最终 mix 转写或上传源稿冒充实际输入音频转写。 |
| `rights_proposal` | 原 `ProductionRightsProposal` 全结构，只是制作前版权声明。绑定原 instance/project/Production/Run/request revision/request SHA、registration SHA 和原声明主体/来源；保原 user_asserted basis、时间及 fence 字段。它不产生制作、读取、发布或再分发权限。 |
| `selected_capabilities` | `tuple[c.CapabilityRoute, ...]`，unique route_id，逐条等于实际已安装并选定的原路由。local audio/visual/edit/index 路由为 owned_local、零费用、credential_ref=null；既有 BYOK text 路由独立按原权限/预算准入。不能由调用方注入路径、模块、凭证或 provider；记录中的 verified bool 不构成可信准入。 |
| `outputs` | 原 request OutputRole 的 tuple，恰等于原不可变 request 的实际解析结果并保留顺序；不得增加、隐式省略或借默认值改写已接受请求。 |

素材顺序保留计划的实际选定顺序；唯一性以 asset_id 判断，不能因输入排序更换已保存计划。原 Asset 可在不同镜头复用；visual binding 仅供 shots，narration/background_audio 仅供 audio tracks。

`fit=contain`：保宽高比，完整内容放入目标画布，余处填充；`fit=cover`：保宽高比，覆盖画布并裁去超出部分。`gain` 为严格有限、非负浮点线性幅度乘数：0静音、1原幅度；禁止 bool、字符串、NaN/Infinity，不增设任意上限或暗中 clamp。流存在性、源范围、真实解码、裁剪/帧映射、混音失真及最终音视频质量仍由原媒体执行和验收检查；字段合法不等于这些检查通过。

## 唯一接口与接线顺序

1. `parse_local_material_plan(data: bytes) -> LocalMaterialPlanV1`：沿停止 EarlyTypedAbi 的 strict JSON 入口，限1MiB、UTF-8无BOM、禁止重复键/非有限数/未知字段；JSON数组到tuple沿原严格 JSON 模型路径处理。此 parser 不读取数据库或授予能力。
2. `validate_local_material_plan_sources(plan, *, request, request_ref, accepted_goal, original_assets, original_script, original_routes) -> None`：纯类型/相等性校验。request 用原 `c.ProductionRequestAny`，request_ref 用上述类型，accepted_goal 用原 `ProjectGoalAccepted | None`，assets/routes 用上述原类型 tuple；original_script 用原 `(c.RevisionRef, c.CreativeRevision)` 数据对，其中 Ref SHA 已由应用层从原持久记录取得并核实。该函数核上述关联、集合/绑定、script kind、routes 与 outputs；不把调用者提供的数据对当能力，也不凭参数 null 判可信 absence。

实际 Backend application caller 先通过原同 Engine lease/current 和真实 human `ProductionPorts` 或 `PolicyExecutionPorts` 取得受控原 request/Asset/revision/Goal/路由及来源事实，完成可信 absence、script origin 与声明来源检查，再调用纯 validator，随后沿原真实 plan admission、immutable plan revision 和 production rights commit。语法错误沿原422；已存来源/身份/不可变关系冲突沿原409，授权/current失效沿原403，资源未配沿既有真实 NOT_READY/等待状态；不得吞掉未知 Operation 或用宽泛错误冒成功。

制作前 body/hash **不嵌入** postapproval `ProductionRightsFact`，避免自哈希循环。旧 saved rights_proposal 的 fence/time 是历史声明事实；重启或新 lease 不改其字节来伪造续权，也不把旧 fence 当当前许可。当前执行资格、原审批是否仍可用、版权事实及必要续授权，始终由原 current/fence/来源规则在 body 外重新核；恢复、unknown核实、预算和限次不变。

## 职责与验证影响

- Backend：唯一新增11字段模型/parser/source validator；从实际原 application host/受控 readers 装配期望事实和 final-context，不更改原 Goal/request canonical。`RegisteredMediaRuntime._current_services/_invoke_current` 实际位于 `application/media_registration.py`，仍归 Backend。
- Media：消费同模型与原已批准 local factory，在 workflows composer/Flow/driver/Bundle 中使用真素材和真 script/plan；不自建 Ref grammar、Asset、版权授权或 binding算法。
- Integration：后端冻结后按唯一源生成必要契约/SDK与原资源封装；不由普通字段签发资格。Frontend：消费原接口，不能让 renderer ref/hash/verified bool 成为授权来源。
- Test/Review：独立核正向 direct-null 与有真实Goal两路径、同Asset不同usage及多镜头复用、两fit/有限gain；反向覆盖损坏Goal不能null、Goal/request SHA互换、伪script kind/SHA、素材来源/rights丢失、binding mismatch、额外route/output、postapproval fact、自改旧fence、重复键/NaN/额外字段。检查原真实权限、同Run/Operation、ASR/CTC、两authority及作品包门保持；这份设计不授予运行或改标准。

原 R1 完整独立验收后连续 R2 保持。本地免产品注册、BYOK、实例持有数据及五步体验不变；缺真实转写/对齐资源不以源稿或模板替代最终证据。本合同不宣称当前产品已成片或已兼容三OS。

## 固定来源

任务卡 `LocalMaterialPlanTopLevelContractApproval.md`：`7270a0f2fc80e6f54027befe6a0bfb1ea994522d720009206c06e22c53a685d1`。EarlyTypedAbi Interfaces：`e309d56d6e2c9df661fe3edb289b0d9cf083d9ec09e02bebdedbb23ae32d0765`；SourceIndex：`178f3f0871b12833566f9aac87c6eb231f2495eab67367dc608d16f63766b963`；sole module：`7187ac4cf7dc0fd9fdfa941f1c88ae0c62bc03131c7fb88ccaf551f0679e92d4`。准确绝对路径、既有类型停止副本及有限读取范围见本阶段 InputPins；未读取活动 Backend/Media 源。
