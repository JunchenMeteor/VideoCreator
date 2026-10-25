# RV58：T41 两处 fixture 与真实 Engine/SQLite 证据独立评审

结论：**FINAL / LIMITED_COMPONENT_SUPPORTED**。固定 T41 的十三项真实 B28 Engine/SQLite/principal 组件证据成立；两处 Test fixture 修正保留原全部断言、方法名称/顺序与同步边界。无新增阻断 Finding。原 T39 **NOTPASS** 不改；本结论不授 API/MCP、真实 Owner/安装、媒体/ASR、作品、三 OS 或 Gate/R1/R2。

## 固定身份与实际范围

T41 正式 MD SHA-256 `9ffbe6156789540bf252b16f463c631d3f6b808f78bc0800f8304ac965cd7287`；JSON `f5c6d0b82976e2d873765cc67dc46c25986189b1aa21773fb38e078d7b25a717`。准确原根 `G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ProductionRecoveryFixtures-T41`；普通根 `G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T41FixtureCorrectionExecution`。

独立核 78 普通副本与 manifest 原/copy 声明的完整 size/SHA；固定 B28 53 源/SQL 全匹配。含必要原 T39 三源、22 原普通件、manifest、规则/卡/历史 RV54/技能和两原正式交接，共 163 观察路径；RV58Snapshot/RV58SourceAfter 逐项列出，前后漂移 0。此计数是本评审路径口径，不替代 owner 的 1316 运行闭包。53 源身份核不表示全产品逐行评审；语义读限完整测试、runner、受理/原回执、真实 Connection 与当前 principal 链。没有 current Backend/SDK/Frontend、活 T40/F8 或环境全扫描。

## 原红、修正及未降低的断言

原 T39 JUnit SHA `df50910d5518ca34448a5b6f553d8ae1b6a5fdea7bd53f0407960c3c8a670302`，13 节点、0 failure、2 error、0 skip，28.66060999999172 秒。原普通根为 `G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T39CoreOriginalExecution`。C05 在原 Probe:194 的真实 Pydantic 构造因缺 request_format_version 出错，未到 accept/wait/replay；C08 原真实 SELECT 到达，但 Database.transaction:162/166/169 对 Test 的 GeneratorContextManager 执行 execute/rollback/close 分别产生 AttributeError，原 receipt/唯一受理断言未达。不是后端受理失败的独立复现。

新 Probe SHA `9472ca499ee18dac9387eafe80acf2f9ccca5ba5b953aa0096c2b2b34c176786`，原 `f4b2486bae55e5ea10a05bfc9494519fb4ccfaba6d6904a756c7bbb6f6e3ef6e`。独立 AST 对照十三方法与所有 assert 调用保持；其它十一完整 body 不变。C05:194 仅显式 `request_format_version='0.3.0-candidate'`，与固定 contracts.py:1420–1423 的必填 Literal 一致。C08:251–270 新 __enter__/__exit__ 委派实际同一 Connection，connect 直接返回 Delegate；__getattr__/execute 保实际对象，未造 rows、替换 Engine/SQL 或删竞争。

固定 database.py:14–19 的 _Connection.__exit__ 委派真实 commit/rollback 并 finally close；connect:151–156 返回实际 sqlite3.Connection，transaction:159–169 直接 BEGIN IMMEDIATE/commit/rollback/close。新代理覆盖 direct/with 两条实际消费协议，原 contextmanager 返回值不满足 direct 合约。原 reader SELECT、writer/read_arrived/writer_done、5 秒 wait、10 秒 future 以及 child 的 90 秒/15 秒同句柄等待保持。runner 仅重命名 index/Probe 与新增双 byte EOF 收据，完整差分保存于本过程，不把修正设置当产品已通过。

## 十三项真实支持范围

实际 JUnit `8b49cded42e03117c6011dcf591c55ebf1e897c9c3cbd888a54b27928edc7e45` 与原 stderr 一致：13 passed、0 failure/error/skip；XML 26.737165800004732 秒，stderr 测试时钟 26.730 秒。126 Events 的十三 started/terminal 成功名称/顺序与 XML/原方法一致；49 份 Rows 的 bytes hash 和各表 counts 均与对应 event 一致。聚合 Methods 来自完整固定模块 profile：accept_production 39、_original_acceptance 61、_accept_production_writer 22、connect 204、transaction 184；是整批计数，不伪称逐 case 方法次数。

| Case | 可支持的实际组件结论与范围 |
| --- | --- |
| C01 | 原规范输入 SHA、完整受理回执 journal 与重放一致；一次 Production/Run/accepted 事件，重放所有 Rows 不变。 |
| C02 | JSON 键顺序等价；真实 goal 改变触发 idempotency_conflict 409，Rows 不变。 |
| C03 | 真实 acquire/revision/review/submit_decision 后 GET/list 使用反馈新 Run，重放仍原完整受理回执，Rows 不变。 |
| C04 | 真实 cancel 后 GET current status=cancelled，重放保原接受快照，Rows 不变。 |
| C05 | 无已安装对齐资格的 V03 真实 waiting_user；稳定原 waiting 回执、alignment_required 事件、Operation 0。未造资格。 |
| C06 | 实际 ledger fixture 的 unknown Operation 1、settled=0、actual_units=null、reserved_units=100000，Production reserved=100000/spent=0，Run needs_reconciliation、worker/fence1/attempt1及 Step 保持；重放全 Rows 不变。verified route 和 external_id 是明确无 provider 的 Test fixture，不能当真实费用对账。 |
| C07 | 两真实 ThreadPool first acceptance 经 Barrier，同完整回执；最终唯一 Production/Run/command/accepted 事件。仅此 SQLite 并发，不外推多进程/宿主。 |
| C08 | 真实 SELECT 先于同 DB 另一 Engine 的 writer；原 gate、writer future、receipt 比较与唯一 Production/command 断言实际通过。独立 Rows 为各1 Production/Run/command/event。 |
| C09 | 原真实 transaction 的 yield 后抛明确 Test 异常，Production/Run/events/operations/accept command 回滚；合法后继只受理1。不是 OS kill。 |
| C10 | commit 后重新构造实际 Engine 读取同 DB，原回执与 Rows 保持；模拟调用方丢响应，不是假称真实进程崩溃。 |
| C11 | 有限删除本任务生成的 accept journal 后仍由唯一原 accepted event 绑定原 Run，返回该原 Run 当前 status；不同于新 journal 不可变初始快照，无假回填。不是旧安装迁移实测。 |
| C12 | 实际 SQLite 写入 BLOB、bad JSON、非 canonical、错 Run、坏 SHA、缺/重复事件七种；各 acceptance_record_invalid 422，原损坏前后所有 Rows 保持，不重受理。仅矩阵列出的损坏。 |
| C13 | 真实 registry/BundleService：旧 actor 对撤回 operation/purpose/project 为 principal_scope_changed 403；重新 authenticate 的当前 actor 分别 bundle_scope_denied403/403/not_found404，到期401；Rows 不变。dummy 公共主体，不授真实 Owner/跨宿主认证。 |

固定 engine.py SHA `3cfb8351560e53b97cded1fcc26748479da70694ca69d2e45c7506d86c59b823`：249–260 显式读 BEGIN 共用快照，279–336 校原输入/journal/唯一事件/原 Run；338–409 同 BEGIN IMMEDIATE writer 重核并在同事务写受理和原回执。C08 的首次 reader 在旧快照未命中后走此新 writer，实际重核已提交的原记录而非新建；测试实际比较全部 DTO。历史无 journal:293–309 绑定原 Run 当前 status，与初始回执:320–336 的独立语义保持。

固定 bundles.py:214–231/1401–1407/1456–1465 在 Engine 重放前重新取当前注册主体，核当前 installation、operation/purpose 与显式 project 可见性。C13 实际调用该完整链；没有 API/MCP bootstrap。RV54 原 limited source 不被改成实际全入口通过。

## 命令、自然终态与限制

原命令为 `C:/Program Files/PowerShell/7/pwsh.exe -NoProfile -NonInteractive -File G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ProductionRecoveryFixtures-T41/RunT41.ps1 -ExpectedInputIndex 2c9e5a03c787d73369c2449b90387d2cb8ef52df3d7f7fbd60405528ea012b1c`。本 Review 没有执行它。实际 child/wrapper 使用自有固定 T26 解释器 -I/-S/-B/-X utf8、固定 B28 普通源/迁移/Packages；原 before/after 1316 个值完全一致，逐值等于批准 index。旧 T39 1309 before/after 亦一致；本次只解析记录、不重新核999环境。

原 child 49324/FILETIME134360183279151251、wrapper53236/134360183271637588 各 launch/terminal 身份一致；两收据自然0，forced=false、lifecycle_errors=[]、retained wait natural0。child launch→ended 墙钟28.9102623秒，与 suite/case 时钟分列。新原 wrapper 收据直接 stdout_byte_EOF=true/stderr_byte_EOF=true；真实 runner 等待原 CopyToAsync GetResult 后才记，失败保异常且不判通过。child 自身是输出文件句柄，不冒充它独立取得 byte EOF。旧 T39 无 EOF boolean，只保原终态与源码等待证据，不倒补字段；旧异常/forced 失败分支保持，未用本次正向证明其故障分支。

本批不含 API/C14、实际 MCP/session credential、真实 Owner/安装/原件许可、合法 authority、原生 Job/OS kill/完整后代清理、真实 media/ASR/full Bundle 或作品。没有以 nonempty hash、route verified、profile 或透明故障代替作品/费用/权限。仍需各归属角色独立后继实测，不为本片增加阈值或跑新批。没有新增阻断 Finding，原失败和未测保持。完整 R1 独立验收后连续 R2 不缩。

评审只 stdlib 解析固定材料及 hash/AST/XML；产品 import、执行测试、DB/API/UI/native/ASR/模型/网络/key/费用、修改 source/标准均0。全部固定输入读者结束，SourceAfter163漂移0；工具记录见自有 RV58ToolHistory，最终元数据命令必须由调用方观察实际 exit0 后发送 FINAL。
