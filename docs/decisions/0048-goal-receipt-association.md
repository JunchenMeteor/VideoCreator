# ADR 0048：原 Goal 请求与回执的只读关联

状态：批准本有限接口设计，尚未实现或独立验证。日期：2026-10-10。范围：在原项目 Goal 接收之上增加准确的历史关联查询；ADR0039 原首次草稿复用、旧 Goal v1 / 私有 intent v2、原授权与预算语义不变。完整 R1 验收后连续 R2。

## 固定事实与结论

服务端使用原 `ProjectGoalInput` Pydantic 解析器，`model_dump(mode="json")` 保留默认值与 null；再用原 `engine.canonical` 的 Python `json.dumps(..., ensure_ascii=False, sort_keys=True, separators=(",", ":"))` UTF-8 无 BOM/换行字节计算 SHA-256。它不是 JavaScript `JSON.stringify`、JCS 或规范化 ProductionRequest 的哈希。字段省略与显式默认值可等价；列表顺序、中文、字符串空格、名称等按原解析器保留。旧解析器不是全局 strict，不另发明转换或 Unicode 归一化。Goal 验证已有有限大小、敏感字段与非有限数字约束，原规则保持。 GoalSHA 不包含 key、principal、完整 SetupPreparationRequest 或 normalized Request；`creation_authorization_ref=null` 不能为查询改写为当前 parent ref。

原 commands 唯一事实以 `(实际 subject, project.goal.accept, 原 key)` 定位，其 `request_sha256` 是 GoalSHA。相同 Goal / 不同 key 可以得到相同 SHA。原 POST/MCP 精确重放在无记录时会首次接收，不能作为只读查询。批准单独只读查询，由服务端核原主体、key、完整解析 Goal 与原持久结果；前端无需重造服务端 canonical 算法。

来源：Backend/GoalReceiptAssociationContract/{ExistingSemantics,Gap,Handoff,InputPins,SourceDerivedVectors} 已固定；SourceIndex SHA `4ceea4bb916a5223133fe15c881bb61c864752ca6f735ff3bc1c663c4524035c` 的九必要普通源及额外 AccessContext/transport_contract 已核。精确路径、全文 SHA、读取范围见本任务 `InputPins.json`。Vectors 只是 source-derived，不是 Pydantic/API 运行结果。

## 唯一公共接口与字段

HTTP 新增 `POST /api/v1/project-goals/receipt-lookup`，operationId `lookup_project_goal_receipt`，成功 200；使用 POST 仅为承载完整有限 Goal，业务上只读。MCP 同名工具仅接受 `{query: ProjectGoalReceiptQueryV1}`，使用同一 Pydantic 模型、同一服务方法和真实 context_provider。旧创建 POST 202 与 `ProjectGoalAccepted-v1` 原字节/格式不改。

`ProjectGoalReceiptQueryV1` 外层字段均必填且禁止额外字段：`format="project-goal-receipt-query-v1"`、`expected_instance_id: Identifier`、`idempotency_key: Identifier`、`goal: 原 ProjectGoalInput`。expected_instance 是调用方对当前可信连接的非秘密断言，不是权限。不得增加 owner、principal、scope、候选 receipt、GoalSHA 或规范化 RequestSHA 输入；不得将 Idempotency-Key 头作为查询的第二键来源。

`ProjectGoalReceiptAssociationV1` 是以 `state` 判别的严格四分支联合。各分支共同必填：`format="project-goal-receipt-association-v1"`、`instance_id`（实际 Engine）、`principal_id`（实际 AccessContext.subject_id）、`original_scope="project.goal.accept"`、`idempotency_key`（原查询键）、`goal_sha256`（服务端解析原 Goal 后计算）、`canonicalization_id="project-goal-pydantic-json-v1"`、`state`。该 canonicalization_id 只是命名已有算法，不迁移旧数据或更改算法。

| state | 唯一附加字段 | 所证事实 |
| --- | --- | --- |
| accepted | `receipt: 原 ProjectGoalAccepted` | 原接收已提交，返回当时不可变回执；不证明当前 Run 可执行或仍 queued |
| pending | 无 | 同主体/key 的完整原 accepted intent 已持久化，尚无接收或拒绝终态；不是 Run 状态 |
| denied | `reason_code: Identifier`、`resolved_at_us: 原严格正整数微秒` | 原已接收 intent 以真实拒绝事实结束；不是新审批，旧创建接口的拒绝仍不变 |
| absent | 无 | 本次一致读快照在此主体/key 的三原 Goal scope 均无事实；不证明在途旧 POST 将永不提交 |

其他分支字段禁止出现，不用 null receipt 冒充 accepted。正常持久状态没有 unknown 分支；断线、超时、无法可靠读取、损坏或权限错误使客户端保持未确认/unknown，不能伪造 absent、denied 或清除原 pending。

## 主体、读事实与失败语义

1. 复用 `BundleService._actor(actor, "production.read", "playback")` 及原可信鉴权；实际当前 instance/registry/subject/scope 验证仍保留，并在响应前重核。expected_instance 不符以 `goal_receipt_instance_conflict` / 409 ErrorEnvelope 拒绝。只按 actor.subject_id 查询；注册 Portal 主体不映射为本地 Owner，不读其他 Owner 的 commands。原创建权限不因此改变。对实际存在的 intent/accepted/denied，其原 project 按既有 `owned_projects` 或显式 `project_ids` 读范围隐藏，越界 404，不回传身份或事实；其他主体同 key 不作为匹配或冲突证据。
2. 一个一致只读 DB 快照读取该主体/key 的 `project.goal.intent/accept/denied`；任何存在记录先核相同原 GoalSHA。相同键/不同服务端解析 Goal 409 `idempotency_conflict`，含仅名称、有效列表顺序等变化；不能按相似文字或 Production 列表匹配。accepted 与 denied 同时存在为损坏，不选优先级。无三个原事实才 absent。读不调用 accept、recover_pending、OwnerSetup.recover、issuer.current_guard、Control reserve/complete 或任何 writer，不追加 query commands/事件、Project/Production/Run、计数、quota、fee 或 fence。
3. accepted 复用/提取原 `_original_result` 的纯校验：原 command、ProjectGoalAccepted、实际原 Production/Run/acceptance event、不可变 ProductionAccepted 和 `_child` 的完整 derivation/receipt/撤销事实互证。并精确核 derivation receipt 的原 key、GoalSHA、production/run/request_revision 和原 ProductionRequestSHA；后者绝不能用 GoalSHA代替。原 nested IDs 不一致、缺原 Run/事件/child 或结果被改，沿既有 422 完整性错误，不重新拼一个成功。原 acceptance 的 status、revision、paths 保留历史快照，当前进度另用 production_get。
4. pending 使用原完整 intent v1/v2 parser 与 Goal、key、主体、instance 的身份检查；核原受保护文件与 DB intent 字节一致。v2 使用原 DraftOrigin/AcceptedSetupRef 和真实 setup journal 的只读关联验证，不调用 active/qualified recovery，不将 journal/JSON 当执行能力。denied 核完整原 intent 与 `_DeniedGoal` 的 intentSHA/GoalSHA/主体/instance/registry revision 和真实原拒绝事实；v2 的原 blocked journal / 无成功 goal_result 语义保留。已终态 accepted/denied 不额外要求仍存在 pending 恢复文件或原创建委托仍 current；复用原终态读规则。文件读取/原 root 观察在短 writer 外，若读期间关联改变，重读一致快照或有限返回 unavailable，不能缓存文件后假成功。
5. 查询服务从现有 Engine/DB 与可信 Bundle 鉴权读取原事实；不能因当下 creation delegation 过期、撤销或资源暂未 qualified 就永远拒绝历史查询。原身份/读权限仍须 current；创建/运行资格、Owner management、费用/unknown 安全边界另在真实副作用前重验。过期创建权可以查询历史 accepted/denied，不能由查询恢复执行。当前读凭证撤销/过期、scope改变仍按原 401/403 拒绝，不能凭旧回执进入。
6. 请求合同错误 422；有界请求/Goal 超限 413（沿原 limits，不缩小已合法 Goal）；同 key 不同 Goal 或 instance断言冲突 409；原完整性损坏沿原 422 codes；存储/必要读事实暂不可用或无法安全确定快照 503 `goal_receipt_unavailable`。全部使用唯一 ErrorEnvelope 和 sanitized 细节，Host/Origin 的原传输错误另保持。任何错误、HTML/text 错误或 unsupported version 不得被 SDK/UI 转成 absent。HTTP response `Cache-Control: no-store`，MCP 返回同语义；readOnly annotations 只描述行为，不授权限。

## 页面、SDK 与兼容

前端只通过唯一生成 SDK/native 可信 request transport 发查询。每次查询保留不可变原完整 Goal、key、预期 instance，以及宿主/连接的非秘密请求关联与 generation；它们不是授权来源。响应必须属于这次仍有效的受保护调用，且外层 instance/principal/key/scope、分支 grammar 与 receipt 嵌套身份均由 SDK/服务核定。输入 Owner 字段、模型 DTO、JSON bool、WebView 任意事件、GoalSHA/URL本身不能认领回执。

无需前端预测 GoalSHA：服务端已对该次完整请求核原 canonical。只有可信查询的 accepted 可以结束对应 pending，采用返回的原 Project/Production/Run。仅凭结构有效的缓存 receipt、自造哈希、任务相似或不同主体/key/instance 的结果不可清除 pending；若使用缓存 receipt，它须与这次查询返回的原 receipt 全字段一致，否则隔离缓存并采用经关联核定的新原事实，不混拼两个 receipt。迟到响应属于已变更 Goal/key/context 时忽略，不提交新键。

pending 继续等待/再查询；denied 显示原拒绝，无自动新 key、新授权或 Run；absent 保留原 key/完整 Goal，不将快照缺失当永久未受理。在明确继续原提交时，可用原创建接口同 key/body 精确重放，但这是可能首次接收的写动作，须原 current 授权/预算，不能隐含在 lookup 或自动标为只读。断线不取消原制作。源资格、预算 unknown、后台 Run 的 needs_reconciliation 与已 accepted 关联为不同事实。

无需新 DB schema、索引或对旧 receipts 回填 principal/key：原 commands、原 child receipt/intent 有实际关联。旧 public v1、native private v2 与原规范 GoalSHA继续有效；SDK新增查找操作和严格新 DTO，禁止手写相同权限声明替代唯一 OpenAPI/transport manifest 生成。

## 实施归属与独立验证

Backend 唯一维护 Query/Association 联合、纯历史 resolver、API/MCP ErrorEnvelope及真实 `DELEGATED` 权限元数据；可提取共同纯校验，禁止以创建服务缺席把所有查询常态503。Integration 随 Backend 固定源重生 OpenAPI/SDK/native route metadata，保原 Rust来源、auth/context校验与请求关联，HTTP/MCP同模型。Frontend 替换自造 canonical/candidate匹配，以 query accepted 结束 pending；保原完整 body/key和generation。Test独立验证下列 cases并保存旧红/有限八夹具；Review与Acceptance独立消费真实证据。架构不代改 DTO/SDK/tests 或宣称 F11-MECH-I01 已关闭。

必验：省略/default/null/空 nested对象在原 parser 等价；中文/名称/数组顺序/空格与原算法非等价；非法 strict revision/bool、额外字段、非有限数、大小；same Goal/different key 两个真实不同 Project 回执只认原 key；duplicate key/different body409；foreigninstance/subject、注册主体不能读 Owner、缺读operation/purpose/projectscope/current撤销；pending-v1/v2、真实denied及草稿唯一；无记录与在途提交 race 不生成新key；历史委托过期/child撤销仍仅只读原回执；错误/超时/损坏/unsupported version保 unknown；nested ID/child原key/GoalSHA/normalizedRequestSHA/revision改变拒绝；readonly 前后 commands/Project/Production/Run/events/计数/fees/floor 完全不变；受保护 transport 迟到响应与不相关但结构合法缓存不能清 pending。上述是实施/验证需求，不替 Test批准的实际 criteria，也不以 stdlib vectors 或自制 oracle 算运行通过。
