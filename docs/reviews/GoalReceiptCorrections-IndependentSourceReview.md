# GoalReceiptCorrections 独立源码复审

结论：**GRL-P01、GRL-P02 仅在 CLOSED_SOURCE_STATIC 范围关闭**。固定两源修复覆盖原问题；未发现本有限修复片的新源码阻断。实际 SQLite／文件系统／WAL／HTTP／MCP 行为仍为 **NOT_RUNTIME_VERIFIED**，没有授予 RuntimeBinding、运行、安装或产品验收资格。原两项独立发现、旧102副本及所有历史失败保持不变。

## 独立版本与范围

任务卡 `G:/开发测试/Projects/VideoCreator/docs/task-board/GoalReceiptCorrectionsIndependentReview.md` SHA `e4426fd84c5118eba45767ea85be0f1f58c5b5b1e9b46da2b162fc9af5cb1d91`。

旧固定根 `G:/开发测试/Codex/VideoCreatorImplementation/Backend/GoalReceiptAssociationImplementation/SourceStage/`；新固定根 `G:/开发测试/Codex/VideoCreatorImplementation/Backend/GoalReceiptIntentCorruptionCorrection/`。读取仅索引中的 ordinary_copy，未读取索引的生产 source_path。旧新各102实际副本大小/SHA均匹配；相同102相对路径中100字节身份不变、2变化。必要正式/治理合计217唯一输入前后无差异，未盘点或复制工具环境。

| 固定输入 | SHA-256 |
|---|---|
| 旧 SourceStage/SourceIndex.json | 3cb7498acc52d68935a9700f694a1143ac9bd0ea6da04e6ee2169da850b90ba3 |
| 新 SourceStage/SourceIndex.json | 0bbbd04a5014b0b512ed64d077b9058d80abfb24bb7178a68541ef7936adbd5e |
| 新 SourceStage/Complete.diff | da75346d51a96d6feb5991d335995afa73d05c9bd508798e4ac4fd101725b1b6 |
| 新 Handoff.md | 6cb6a11ec322695344c3dc445bed66556b126643f583af3f967bff872cc42880 |
| 新 Handoff.json | 65c5800d5a5e68fdf840beb1c9dffe20b8b44a7eea135210feec147d920055a7 |
| 新 Interfaces.md | 695db9d5f181907bdb91658298967fedac6c291293ec8244da43335574f18ef1 |
| ADR0048 | b3cd8ab43acc9b3e021693c327050c251a90ee4df4394ab9738d5019c660a047 |
| 原独立报告 | d469eb97bc664318d26c053080211a03b38b2aa2a07b56bbffd28c03b0cfe3a4 |

两个新源完整绝对路径均位于：`G:/开发测试/Codex/VideoCreatorImplementation/Backend/GoalReceiptIntentCorruptionCorrection/SourceStage/SourceCopies/services/engine/src/video_creator/`。

- `application/goal_receipt_lookup.py`：11823B，SHA `9939fbcd6ca1ed631924a08d29a2844c023f239869a23b3f2f25187d27efabe0`；旧SHA `bfd9100ca2291ba6c00286bf5ee7b6e8c7f42bc6b353d5ad70f4fc0ffe0a1833`。
- `infrastructure/database.py`：11592B，SHA `f8c68c5ad83a6c1ca649d888feb20a5cc055688d81ed2125195183704e7ebbd9`；旧SHA `ee0a8a5829f8305688976336e83f4bacb8a9175524837c7c9852648a92ba6f46`。

以下行号均指该固定新副本，而不是当前生产文件。公开调用链必要副本也来自相同新索引，其正文与旧版相同。

## GRL-P01 — 已支持源码层关闭

原触发是 commands 的 intent.result_json 实际为 SQLite BLOB/bytes，却直接进入原 `_parse_goal_intent` 的 `body.encode`，产生未分类 AttributeError；这不是原报告中已运行的 HTTP500 或实际数据库损坏。

新 lookup 95–99 行先检查 `type(value) is str`，再检查原 `GOAL_INTENT_LIMIT` 的字符数及 UTF-8字节数；不支持类型在短路分支被拒，不再对bytes/数字/None执行encode。原 `daily_projects.py:40` 限额为32MiB，此处未降低原已合法Goal/request边界。坏类型或超限持久行以 `daily_project_intent_invalid`／422／never EngineError拒绝，然后才在99行调用未改变的原parser。没有 blanket AttributeError/Exception catch、无吞损坏，也没有返回absent／denied／成功以清pending。

原 `daily_projects.py:94–105`、Bundle `strict_json:110–130` 及 `ProductionAuthorizationService._model:59–63` 仍检查严格UTF-8、重复key、非有限数、版本和原模型；lookup100–102行再核原canonical与project visibility。原Unicode/JSON/model损坏仍沿原422分类，不将所有损坏强制改成同一个新code。真实OSError/SQLite异常保留lookup192–193的 `goal_receipt_unavailable`503。

Bundle1490–1495保留查询前后 `_actor(production.read,playback)`；1415–1421重核实际当前主体／安装／operation／purpose。新422是既有EngineError：HTTP app152–155生成原 ErrorEnvelope与status；MCP135–142生成同code/message/retryability的ErrorEnvelope，而不再因本BLOB类型分支进入generic unavailable。HTTP230–237的成功200/no-store和同一typed query保持，未宣称真实错误响应或SDK状态已测。

独立后继测试仍须实际SQLite BLOB、非TEXT、原字符/UTF-8限额、坏JSON及正常中文通过完整resolver／Bundle／HTTP／MCP；核稳定422、不伪造关联状态、客户端保原unknown/pending、账本零变化。本评审没有构造或执行这些行。

## GRL-P02 — 已支持源码层关闭

lookup83与159行的两次快照均调用唯一 `Database.connect_readonly()`，原两个默认 `connect()`已被实际替换；无reader遗漏。

DB163–176行以原绝对目标的 `Path.as_uri()`转义URI再追加 `?mode=ro`，并向sqlite传 `uri=True`；没有creator fallback、路径替换、删除后重建或`immutable=1`。这消除原“默认CREATE opener先于query_only”的源码能力。原timeout5、isolation_level=None、_Connection factory、Row、foreign_keys/busy_timeout配置保持，query_only也在开始read事务前设置。连接setup发生SQLite错误时close后原样抛出；connect本身失败进入lookup192–193既有503。成功上下文由原 `_Connection.__exit__:16–21` 负责关闭，异常亦不保留该read连接。

新lookup两个BEGIN/coherent snapshot、真实instance、三scope原subject/key、protected pending文件及fresh事实、DB inode/root/current检查均保留。第一读关闭后路径消失，第二只读opener的源码不会转用普通creator；此为静态支持，不是已经完成该平台OSrace注入。若文件被其他程序替换、权限变化或WAL/SHM有平台旁文件行为，仍须实际故障测试，不能由URI语法证明全部路径TOCTOU原子性或零OS副作用。

独立移除新DB中唯一新增connect_readonly方法后，**整个原Database模块AST相同**：普通connect156–161、transaction、备份、正常constructor／迁移版本11，以及_Connection均没有改写。完整diff按实际旧新正文独立重建与冻结3030B diff逐字相同；不是依赖作者 `both_readers_mode_ro_uri=true` 或AST pass布尔字段。

## 回归支持与准确缺口

100不变件包括原canonical/create、公开Query／四分支Association DTO、API/MCP、transport、完整history与权限源。lookup仍只按原subject/key查三scope，expected_instance冲突409；先核已有项目可见性，不让注册主体读其他Owner。accepted仍复用原不可变Production/Run/acceptance event、完整child/derivation及原key／GoalSHA／normalizedRequestSHA／requestRevision；pending-v1/v2及denied仍用原完整intent、setup history／journal和终态矩阵，只有pending要求恢复文件。源码改动不使历史回执成为当前运行授权，也不改变canonical、新建key或恢复writer。

这是原源码回归保护，**没有新增实际状态或并发通过结果**。accepted/pending/denied/absent、changedfacts503、撤销/过期读身份、foreign scope、pending文件、HTTP/MCP/no-store、实际只读rows/fees/floor以及平台WAL和路径行为均须独立Test／Acceptance另批。原三轮素材完整批次M02/M07/M14失败与不得第四次重置尝试保持；M14oracle只读批准不转成第四轮运行许可。本报告不批准任何执行、Owner、native、媒体、安装、三OS、Gate0／R1或R2资格；完整R1独立验收后连续R2总目标不缩。

## 工具与过程保留

自有过程 `G:/开发测试/Codex/VideoCreatorImplementation/Review/GoalReceiptCorrections/`：FixedSourceInputs.json保存204实际普通源身份；SourceClosureFacts.json保存diff/整个Database保护证明；InputSnapshot/InputAfter保存217前后输入。自身 `ff0154`误把Complete.diff定位于正式根，FileNotFoundError／exit1保存在OwnLocatorError；实际应位于SourceStage。`985d61`输出source_map过大与`141a85`合并源码/ADR展示被截断均保留范围记录；后续只定向补读必要固定正文，不称产品失败或声称原截断输出全文已读。没有产品import、SQL/服务、测试执行、模型／凭证／费用／网络行为。

最后源码事实解析 `a4d69a`自然exit0，无live session；全部源码读取完成。正式报告和末输入写工具实际返回后，由独立FinalHandoff／Agent FINAL记录其自然终态，不把产物存在当作工具已完成。
