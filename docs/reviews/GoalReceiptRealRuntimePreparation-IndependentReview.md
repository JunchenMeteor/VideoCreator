# GoalReceipt 真实组件运行准备：独立有限评审

本次结论为 **SOURCE_DATA_REVIEW_FINAL，当前候选存在 GRRP-P01（P2，Test，OPEN_SOURCE_STATIC）**。它会在固定 Windows 入口的预检查阶段拒绝合法、完整的候选路径；这是原字节与源码的静态判断，未执行 PowerShell 入口、19 个测试或任何产品。原角色须保留该候选并另固定修订版本。本评审不授运行许可、RuntimeBinding、Owner、安装或 R1/R2 资格。

其余已读相干源码未发现第二项已确认阻断。GRRP-I01 只保留共享数据库故障的归因边界，不是实际重建文件、rename 失败或只读 resolver 缺陷的复现。合法 accepted、pending、denied/history 阳性仍为 **NOT_READY**，不能用 SQL 故障行替代真实原消费者或授权事实。

## 固定输入与证据层级

任务卡为 `GoalReceiptRealRuntimePreparationReview.md`，SHA-256 `cd97ad821268be0dbeda1f9f2020e604768a96dddc6c4d3e4b625f4985ffd313`。唯一实现与测试证据来自已停止写入的 `TestDevelopment/GoalReceiptRealRuntimePreparation`、其 `ReviewHandoff/GoalReceiptRealRuntimePreparation` 普通副本及两份精确锁定的 SDK/标准库正文。未读取后继热修。

独立核对 124 个普通副本大小及 SHA，无差异；有限末核为 135 个唯一输入，`InputAfter.json` 的 `changes=[]`。其中包含规则、卡、正式交接、普通副本、候选元数据和两份有限依赖正文；它不代表重新核验 3619 个环境文件或 Windows 原生加载结果。完整源副本 102 件的执行路径/大小/SHA 与候选 Index 逐项关联；相干 Engine、Database、Registry/Bundle、lookup、HTTP/MCP 及完整测试/Probe/内外 runner 调用链由评审直接读取，不以作者 AST 计数替代语义。

候选 Index 有 3619 个唯一记录，Runtime 999 必需路径集与其一致。缓存覆盖中 1257 个预期不存在的 `.pyc` 均与各原 `.py`、`cpython-313` 文件名及源身份逐项匹配；854 个已声明现有缓存与覆盖表无差异。116 个可缺省 `entry_points.txt` 与其原 `METADATA` 目录/身份关联一致。91 个产品 profile 路径集与固定源对应。上述为 **固定数据关联**，不是实际 import、缺缓存 OS 返回、物理目录成员全集或 native 资格证明。

正式准备交接的 metadata/static 命令自然退出 0；现有 AST/PowerShell 语法证据仅说明准备语法层。当前候选没有实际运行批次、JUnit、Methods 或 19 项通过记录，独占输出目录在准备阶段记为未创建。旧实际失败与 material 三轮门禁不改变，不以本次准备改写旧 I44/I62 的 overall 1。

## GRRP-P01：双方绝对路径表示不一致

- 严重度/归属：**P2 / 原 Test 角色**。
- 固定源码：`G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/GoalReceiptRealRuntimePreparation/RunGoalReceipt.ps1`，SHA-256 `35bfe687c159312a0de015e57ebe9ac10a7860ab3389c6a042827e279f6f8f59`，第 44–45 行。
- 固定 Index：`G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/GoalReceiptRealRuntimePreparation/GoalReceiptInputIndex.json`，SHA-256 `fee3d145d575a02a7193bdddb2e9de629dc5bffe400f264113a0a17d2d04627b`。

入口将 `Join-Path $Root $Name` 的反斜杠全部换为 `/`，随后对原 `Index.records.path` 做大小写敏感的集合比较。原 Index 中三个入口记录却保留 Windows `str(Path)` 的反斜杠形式：`RunGoalReceipt.ps1`、`RunGoalReceipt.py`、`ProbeGoalReceipt.py` 各完整 native 路径均存在；对应 forward-slash 路径均不存在。因而在三个文件实际大小/SHA 全部正确时，仍会抛出 `Test entry body missing from pins`，先于输出目录建立、Python 启动和 19 个 case。

独立派生比较使用原固定 JSON 和原源码，不执行入口。具体原值、三个比较结果、完整身份与触发条件见本过程 `Finding-GRRP-P01.md/json`。归属者须在双方使用同一完整绝对路径表述；保留 physical/fileidentity、完整路径、大小及 SHA 检查。不能改成 basename/suffix 匹配、通配目录、自动补授权或缩小 allowlist。修订另固定，不覆写旧 Index、原 19 范围或历史失败。

## 完整 19 个候选的实际目标与局限

完整原 case 方法与计划逐名一致。以下记录源码中真实调用和独立期望，不表示它们已经运行：

| 候选 | 实际方法与断言目标 | 可支持的有限范围 |
| --- | --- | --- |
| G01 | 原 Engine/Database/Registry/Bundle，中文 Goal、canonical hash 查询未存在命令 | absence、项目 scope、全部 Rows 不变；不是合法成片或 accepted |
| G02 | 原 Registry 当前 principal；旧 actor、权限不足及过期 | 各原拒绝码；不自造 Owner 权限 |
| G03 | 请求异实例 | 原 409 边界 |
| G04 | SQLite BLOB、整数经 TEXT affinity 后的非法命令内容 | 真实存储类型/非法解析 422；非合法 receipt |
| G05 | 字符数超上限 | 原大小拒绝 422 |
| G06 | 中文字符未超字符限、UTF-8 字节超限 | 独立字节限拒绝 422 |
| G07 | accepted `{}`、缺 intent 的 denied 故障命令 | 原 union/关联非法拒绝；不冒 lawful positive |
| G08 | 第一次真实只读连接前移走原 Metadata | 原 unavailable、禁止代建；原文件恢复同 inode/hash |
| G09 | 第二次真实只读连接前同样移走 | 双读取的有限缺失窗口 |
| G10 | held 旧 reader 事务及独立 committed 故障 writer，观察非空 WAL | fresh read 见当前故障；没有完整 WAL 一致性或有效授权阳性 |
| G11 | 第二次读取前由真实连接提交一条故障 command | changed facts 503；原非 command Rows 不变、command 精确 +1 |
| H01 | 原 HTTP app/route、loopback、真实注册的非 Owner actor | absence 200、`no-store`；无安装/Owner 正常链 |
| H02 | 原 HTTP 中 BLOB 故障 | 原 error envelope/422 |
| H03 | 字符及 UTF-8 超限 HTTP 两个透明 subtest | 两个原 422；仍是一项 outer case |
| H04 | HTTP 读取期间的第二读前缺失 | 原 503 和生命周期观察；共享 export 线程归因另见 I01 |
| M01 | 原 MCP server + SDK memory transport/client initialization/list/call | 实际 SDK 协议 absence；不是 stdio 进程恢复或 per-call 真实 Owner 认证 |
| M02 | MCP BLOB 故障 | 原结构化 error code/isError |
| M03 | MCP 两类超限 | 原拒绝及 retryability；非两项工具计数 |
| M04 | MCP 第二读前缺失 | 原 unavailable/retryability；不是 native lifecycle 验收 |

Fixture 正常创建测试专属 Engine/Database11 并通过原 Registry 注册合成非 Owner actor。故障行只插入非法 `commands`，没有 SQL 构造 policy、Project、Run、approval、资格、floor、Operation 或未知成本结算。`logical_rows` 使用原 SQLite 只读事务 SELECT 全部用户表，长文本/BLOB 仅作可比较投影；不篡改业务事实。文件移走/恢复只限该测试自身 Metadata，并保留原 identity/hash。原断言仍不足以提供 lawful accepted/pending/history 链，准备矩阵正确将其留待真实 producer。

原 pure resolver 在第一只读事务获取 scope 事实，按完整 canonical/hash、typed union、历史/child 关联作验证，再开第二真实只读事务核当前事实及原文件身份；pending 还依赖原 control/file/journal。原故障窗口仍须由后继实际证据判断，不能用方法名、AST 或 SQL 能插入来证明有效 receipt。

## 真实 transport 和 runner 边界

HTTP driver 源码调用原 `create_app`、uvicorn loopback 随机端口、原 route 和 EngineError handler，httpx 禁用环境代理；服务线程非 daemon。关闭会设置 `should_exit`，先按原 5 秒 join，再持续观察同一线程直到终态；超时锁存失败，不能用后来结束洗绿。末尾保原 socket 关闭和端口 connect 拒绝观察。此源码设计不证明实际 OS 返回或自然退出。

MCP driver 用固定 SDK `create_connected_server_and_client_session`；评审直接读其第 50–98 行，确认第 95 行确实调用 `initialize()`，再通过 `list_tools`/`call_tool` 走原 server。它是内存 transport，不是真 stdio 子进程/重启恢复。fixture 的 context provider 使用原 Registry authenticate 当前非 Owner actor；不能外推真实 Owner/native/per-call wire 鉴权。MCP/HTTP lifespan 都真实启停 export 服务，未换成 dummy manager。

Probe 在输出建立和产品 import 前核 Index/解释器绑定/物理路径与 pinned bodies。缺缓存 observer 限于原标准库 get-data/read-text 调用栈，不伪造内容或假 `FileNotFoundError` 返回；固定 `PathDistribution.read_text` 正文真实允许原 `FileNotFoundError` 被标准库抑制为 `None`。冷 `ctypes` 初始化例外仅在标记窗口内一次允许，`finally` 撤销；具体 DLL 绝对加载来源不由该计划证明。

Audit/方法 guard 限制输出写入、固定 source 读取、注册 loopback 端口、测试 SQLite；拒外部网络、subprocess、keyring/credential、Owner/native 与模型调用。profile 针对实际 `str(Path(co_filename))` 的固定 91 路径，并有限记录真实原方法进入；生成 dataclass 额外用 module/file/code 对象关联。这些仍是待执行 guard，不能用类名或缓存 attempt 数量代表构造/OS 返回或费用资格。

Python wrapper 使用固定 argv、隔离环境、stdin DEVNULL、原 `Popen` 对象与真实 handle/creation FILETIME 记录，两条原字节 pump 保留 stdout/stderr。90 秒超时锁存失败，只在同一 held child handle/creation 匹配时至多 terminate 一次；继续等待原对象终态及双 EOF，不按 PID 盲杀或开启重复批次。外层 PowerShell 同样持有原 Process/creation 与原字节流，要求自然终态；收尾错误/forced/输入变化不以 exit 0 洗绿。观察等待可能长于 90 秒，不能宣传为每个阻塞路径可被硬中断的总期限。候选通过还须确为原 19、0 failure/error/skip、无未执行、无异常/forced/输入漂移及双 EOF；当前没有任何这样的实际结果。

## GRRP-I01：共享数据库故障的归因限制

此项仅为 **SOURCE_INSPECTION_ONLY_NOT_REPRODUCED**。H04/M04 期间原 lifespan 启动 export daemon；`bundles.py` export loop 会调用 `acquire_export`，其真实 transaction 经 `Database.connect` 打开可写 SQLite。若原 Metadata 正在被故障 fixture 移走，后继出现 rename 被锁拒绝或目录中的新文件，须保留实际线程、method、connection-opener 事实再归属；不能仅据全局文件现象称只读 lookup 自己代建。

该有限相干链并未证明候选一定遇到竞争或任何文件重建，不列第二个阻断 finding，不要求为求绿禁真实生命周期、换 fake connection 或削弱原不代建断言。现 19 候选仍未运行。

## 原结果、观察错误与交接

评审的任务卡简称定位曾查 `Handoff.md` 失败（`37e997/1`），已由唯一原目录确认实际文件名 `PreparationHandoff.md`（`25c8f0/0`）；保存 `OwnLocatorError.json`，不当产品/Test 红。另一次自己输出 runtime prefix 表时截断（`c1b694/0`），保原输出限制并以定向 `f5aa83/0` 补确实未显示的 PowerShell 段，不能声称原截断全文已读。两份依赖正文只作精确 pinned source 阅读，未 import vendor/标准产品库。

必要下一动作归原 Test：修 GRRP-P01 的双方完整绝对路径表示、另固定唯一新候选并独立核版本；保原 19、原大小/物理/缓存/metadata/期限/EOF/故障与 NOT_READY 阳性约束。本次没有 Runtime grant，也没有 DB/HTTP/MCP/native/ASR/模型/费用/安装执行。完整 R1 三 OS 真作品与多模态交付、独立验收后连续 R2 的目标保持。

固定输入与派生证据见 `G:/开发测试/Codex/VideoCreatorImplementation/Review/GoalReceiptRealRuntimePreparation/`。最终工具真实返回及 reader 释放由该过程 FinalHandoff/FinalizerTerminal 与终态消息交接，不以文件存在代替当前写工具完成。
