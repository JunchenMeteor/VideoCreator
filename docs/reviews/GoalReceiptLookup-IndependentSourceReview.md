# Goal receipt lookup 独立源码评审

结论：**SOURCE_STATIC_FINDINGS_OPEN**。ADR0048 的唯一只读查询、原 Goal 解析／历史关联及权限边界有源码支持；存在两项 **P2，归 Backend，OPEN_SOURCE_STATIC**：GRL-P01 的损坏 intent 类型未进入唯一错误边界，GRL-P02 的普通 SQLite 打开器在路径消失分支仍能创建数据库文件。这里没有实际 SQL／HTTP／MCP／OS 反例，不将源码判断写成运行失败或验收通过。

## 固定范围与完整性

只读固定 `G:/开发测试/Codex/VideoCreatorImplementation/Backend/GoalReceiptAssociationImplementation/SourceStage/SourceCopies/`，没有读取热生产或后继修复源。全部 **102** 普通件大小／SHA 匹配：94 不变、7 修改、1 新增；加任务、治理、正式件、技能及完整差异去重为 **114** 有限输入，末核 differences=[]。完整实际路径、大小和 SHA 见本过程 `InputSnapshot.json`、`InputAfter.json`，不冒充全运行环境核验。

任务卡 SHA `0d534cb0584c4ad6a0c80f728a1ba8c49e84b2848b383ff9a7a4f96d4ed4c86e`；ADR0048 SHA `b3cd8ab43acc9b3e021693c327050c251a90ee4df4394ab9738d5019c660a047`；SourceIndex SHA `3cb7498acc52d68935a9700f694a1143ac9bd0ea6da04e6ee2169da850b90ba3`；Complete.diff SHA `65541a41269a2e21917faa1819e6c62d9aff6b669d524db266c130ddea7da056`；StaticChecks SHA `d74be55d5aa08241d806d58e9e9cf114d0544f7e8d9c34a844a913443d39f789`。

| 固定改动源 | SHA-256 |
| --- | --- |
| application/goal_receipt_lookup.py，新增 | bfd9100ca2291ba6c00286bf5ee7b6e8c7f42bc6b353d5ad70f4fc0ffe0a1833 |
| application/owner_setup_history.py | 50d5ec431ff4370a50a9c5163f508858cbca9c10e22bc6b263d36b1fd8e2e773 |
| domain/daily_project_authorization.py | f9483593c9cfe6e9d7d13bc51defbe1a3dcb48bf1973410a516b91387311c838 |
| application/bundles.py | 7d88ba046b4d39590a4527e8270af0be43b9c3d8eef4240cec036c22e68c6538 |
| api/app.py | e4f1a7cf559bf01392435cd529a35b54c284bba2fe8f540d91620caa05a72546 |
| api/transport_contract.py | 521f6edef0018b00bda19bbfde6216538704db251ed325bd2f34db69d82b57c7 |
| integrations/mcp.py | 0568ac4d55e8c149a7babaafb214bc0bca63344e58142a38f71dd3259553e475 |
| cli/main.py | 482d87de04e9fe54fa2b4ced7a65110116a3964eb8007fbae2f8de3983bb9e39 |

独立全文读 26,274 B Complete.diff；其 8 节对实际普通源的每个上下文／新行匹配，并反向重建 7 个原文件字节，其 SHA 与固定索引 before_sha256 均相等；新增文件的 before 为空。独立解析完整改动文件 AST，并确认 15 个旧 domain 类、API／Bundle 原 create_project_goal AST 未变。本轮没有重读整个旧 101 件物理目录；差异保护证据的准确范围是实际新源、完整差异及索引记录的原 SHA，不把作者 91 AST 计数当语义证明。

必要原纯解析器、child、原接受回执、Owner setup 历史校验、DB 连接、registry、实际 API/MCP 和导出接线已按相干方法全文读取，范围见 `SourceReadCoverage.json`。其余无关旧业务路径只核普通件身份，没有宣称全部语义审查。首次 source_map 元数据输出过大、后一次组合源码输出有截断，记录在 `ReadIssues.json`；完整差异及所缺 resolver79–112另经精确补读，无重跑或原运行结论。

## GRL-P01：损坏的 intent BLOB 绕过唯一错误分类

**P2；Backend；OPEN_SOURCE_STATIC。**

最小条件：可信当前 actor／合法 typed query／实例及原 key 的 request_sha256 正常，但原 commands 的 `project.goal.intent.result_json` 是 SQLite BLOB，读取值为 bytes。这是存储损坏或受控 fault 分支，不是用户输入产生授权。

实际链：新 `application/goal_receipt_lookup.py:96–100` 不检查实际 TEXT 类型便调用原 `_parse_goal_intent`；固定未变 `application/daily_projects.py:94–105` 的 97 行先做 `body.encode('utf-8')`。bytes 没有 encode，产生 AttributeError，尚未进入原 strict_json／authorization._model 的损坏拒绝。新 resolver185–194 只捕 EngineError、OSError、sqlite3.Error、ValueError、TypeError、UnicodeError，未捕该异常。`migrations/0002_cancellation_and_commands.sql:2–6` 的 TEXT NOT NULL 是 affinity，没有 STRICT 或 typeof(TEXT) 约束，不能凭 DDL 保证损坏行一定返回 str。

`api/app.py:152–161,230–237` 只定义 EngineError 与 RequestValidationError 的唯一 ErrorEnvelope 映射，该 AttributeError 逸出此业务边界；`integrations/mcp.py:103–104,135–142` 则落 catch Exception，生成 mcp_service_unavailable／reconcile。由此源码不能兑现 ADR0048 的原损坏 422 与 HTTP/MCP 同语义。未运行 HTTP，不报告“实际500”；也没有推导泄露、权限放宽、成功、absent、denied 或新增账本写入。

最小改法：Backend 在复用原 intent parser 前验证持久结果的实际受支持 TEXT 类型和原有界大小，损坏以稳定原 422 EngineError 拒绝。保持原 parser／canonical／create 行为；不能用全局 catch AttributeError 掩盖其他编程错误，也不能转成 absent／denied 或把实际存储 unavailable 改成成功。独立 Test 另用真实 SQLite BLOB intent、其他坏类型通过完整 resolver／Bundle／HTTP／MCP 检查 code、ErrorEnvelope、pending保留及账本无变化；本报告不授权执行。

早单 `EarlyFinding-GRL-P01.json` SHA `bb79cf05d66edbd83780924d474617603c6e4d3c6aecb07dbf3a48e3fc0ba08a`，包含完整五源 pins。

## GRL-P02：query_only 之前仍有数据库创建能力

**P2；Backend；OPEN_SOURCE_STATIC。**

最小条件：初始 path.stat 和首一致读成功，但首 reader 关闭后、第二次连接打开前 Metadata.sqlite 路径消失。这是条件性存储／文件系统 race，不是实际 OS 故障复现。

新 `goal_receipt_lookup.py:79–85` 在观察路径后调用 `engine.db.connect()`；152–160 行退出首 reader，再调用同一方法打开 fresh snapshot，随后才设置 `PRAGMA query_only=ON`。固定 `infrastructure/database.py:156–161` 是普通 `sqlite3.connect(self.path, timeout=5, isolation_level=None, factory=_Connection)`，没有 existing-only／只读 mode，仍有默认 CREATE 能力。即使随后缺表错误被 resolver191–192 映为 unavailable503，打开路径的副作用已先发生；query_only 约束后续 SQL，结尾 inode 检查和错误分类不能撤回此前的打开能力。

此分支可创建新的 Metadata.sqlite 再失败，与本接口“只读原事实”不符。没有实际创建文件、SQL 或故障注入，不声称原数据库已丢失，也不把这一条件扩大为所有正常查询写入或全部 WAL／SHM 旁文件行为。

最小改法：Backend 为两个 snapshot 使用只能打开现有原目标、不能 CREATE 的专用只读连接，保留实际 identity、coherent read 和 unavailable503。普通 Database.connect、正常 writer／迁移／创建调用保持原行为。查询不能删除新观察到的数据库或通过创建器重试。独立 Test 另按平台真实句柄约束注入两次读之间的精确路径消失，检查不生成替代 DB、原文件／账本不变与错误语义；此处不授 runtime。

早单 `EarlyFinding-GRL-P02.json` SHA `a84c8827ae1d920e7415062b3c29e1b09d85f4a708b3292afa98ec19e6577202`；DB 固定源 SHA `ee0a8a5829f8305688976336e83f4bacb8a9175524837c7c9852648a92ba6f46`。

## 其余源码支持与准确边界

- DTO：`daily_project_authorization.py:300–371` 外层 strict／frozen／extra-forbid 且四个 Query 字段必填；goal 的 before validator 复用原 ProjectGoalInput，保默认值／null及原大小，完整 typed query另限32MiB。四状态严格 discriminator union；pending／absent无receipt字段，denied需原reason和严格正整数时码，accepted核嵌套原 instance／GoalSHA。旧 Goal 和 receipt 类 AST、原 engine canonical／digest及 daily source字节保护保持。没有声称 Pydantic 实际 parse 或边界运行通过。
- 权限：Bundle1490–1495 在 lookup前后调用 `_actor(production.read,playback)`；1415–1421 核当前 registry和实际AccessContext。registry207–245 禁Portal注册成Owner、expiry拒绝并以真实注册主体生成 context。resolver34–41／73只按实际subject和key读原三scope，先核现有 intent／accepted 的项目可见性，再给冲突；query expected_instance不是权限，foreigninstance409。错误或absent不调用创建、不申请新key。
- accepted：resolver112–126复用原 `_original_result`、完整 `_child` 与原 Production／Run／acceptance event读规则，并额外核原 key、GoalSHA、production/run/requestRevision和规范化RequestSHA，不把 GoalSHA当RequestSHA。原 `_acceptance_receipt`保历史status快照并核原event的Run，不假定仍queued。child合法撤销仍按原不可变历史证明解析，不授当前运行权。没有source中的issuer构造、current_guard、accept、recover、reserve或writer调用。
- pending／denied／v2：resolver127–175保完整原 intent parser／canonical与主体身份，pending读精确 AcceptedGoal bytes；v2调用完整 `validate_setup_goal_history`，核 DraftOrigin／AcceptedSetupRef／journal、原Project create command、各step与原Owner／execution／creation commands及依赖、planned IDs和严格终态矩阵。仅pending要求两个受保护恢复文件。history47–81新增默认check_recovery_file=True，只有具 committed_result／committed_denial的lookup终态可不再要求恢复文件，旧调用默认不放宽。denied核原intentSHA／GoalSHA／主体／实例／ref／revision及v2 blocked/no goal_result，不能新造拒绝来清pending。
- snapshot：新 resolver两个读段显式 query_only／BEGIN，传递旧纯校验只读 SELECT；fresh段重核原三commands、必要v2 journal和instance，随后比较DB inode及pending root／文件stat身份。它是有限观察，不能称OS原子锁或所有传递历史行逐项fresh复验；GRL-P02 的打开能力另列。`_History.__init__`只保存engine，类方法复用不构造DailyProjectService或issuer，也不把所有历史路径占位503。
- 传输／生成：HTTP230–237新增POST lookup且成功200／no-store；无第二Idempotency-Key参数。MCP48、103–104消费同一Query和Bundle方法，annotations只说明只读。transport24和220–223声明真实read/playback及mutating=false，无rawHTTPbytecap假声明。CLI81–114新增TypeAdapter联合schema导出、私有base不被枚举；尚未运行导出或生成 SDK，不能当接口或 native 已接线。

## 交接与未测

后端修复两项固定源码问题；Integration在新的止写源上生成唯一契约／SDK／native metadata；独立 Test需真实 parser／SQLite／权限／v1-v2四状态／损坏／race／HTTP-MCP／no-store及只读账本测试。不得以作者 AST／静态0或本报告替代这些实际证据。F11-MECH-I01、实际Owner／native认证与生产、安装、真实多模态作品、三OS／Gate0／完整R1及后续R2仍未验收。原所有失败不回填。

本阶段全部源码读者已释放；末次有限114输入读取工具1cee85实际exit0、无live。正式报告写入工具的实际终态在独立FinalHandoff／FinalizerTerminal和tool result记录，不提前把 return-pending说成退出。
