# RV83：T56 数据库夹具修订独立评审

结论：LIMITED_COMPONENT_SUPPORTED。没有发现本切片新的 P1/P2 阻断。Test 自身重复 INSERT 的最小修订已由原八个完整测试主体和真实 SQLite 结果支持，原首批仍为 8 errors / NOTPASS。这里只认可固定 B40/B41 Database 的 D01—D08 数据库机制，不批准真实 Owner、可信恢复、RuntimeBinding 或任何 Gate/R1/R2。

## 版本与证据身份

修订正式 MD SHA-256 `a355751f0bb06d5955d926b0facea2328b21fdf8b2dd5eac16ff65b64cf91fd4`；JSON `211ee00d4413e080f776617e0be313fccf7d584eabb9ef50f1caf4c36e623427`。正式根为 G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/OwnerSetupValidation-T56/FixtureRevision；80 普通件位于 G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T56DatabaseFixtureRevision。其 OrdinaryManifest SHA `30a23e69c2d7945f36315f7debf394739db59cc2f4322cb9630d594159023217`，ExecutionSnapshot SHA `c7fb57b638fe890f153ec2b35241e0ca298db8f6d8ce213ccf8149621a1c0dbd`。80 份原件/副本逐大小和 SHA 对照无 mismatch；原 Rows、原 snapshot、原迁移与原失败材料均按准确索引读取，没有复制 999 runtime。

原首批正式 MD `ae16b4c4cff0a7d086ce48674942bb64f4ebb7ec295c69a60897660b3fd19490`；JSON `263a9a6332f9dcb216e9e9e5bd870f13131db282c51d15f9fafaf5b6dbe6e774`。原普通根为 G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T56DatabaseOriginal，原 JUnit SHA `d45ba744594dfd42745e1fbf52c6a9171cfa3832e0ac057edc97660e11d3d41c`，修订 JUnit SHA `2904389a06dc518ea2d16a14feb7c325307cb921902185c0510f60dcd0911a0c`。

完整 B40 Database SHA `88e0ad177fe50b74819b7c66c7b7754dd111725214fab7754b48dc53e187ba99`，完整 B41 Database SHA `925e322e2f0e78b34ca5877fe441803b60b5827961104d80ccfea0a308bbd8ca`。两整模块正文差异仅 schema10 的构造迁移/已知备份版本扩展；普通正文大小/SHA 与实际声明的运行模块和 before 输入图一致。十份迁移均与运行前索引对应 SHA/大小一致。此处没有读取热 B42 或重构数据库方法。

## 原失败与最小修订

[原 Probe](G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T56DatabaseOriginal/ProbeDatabaseT56.py:145) 在 setUp/seed_structural_ledger 重复 INSERT `production_authorization_registry_revision='7'`；原 [0006 迁移](G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T56DatabaseOriginal/DatabaseSourceStage/B41/services/engine/migrations/0006_production_authorization.sql:42) 已写同 key、值 `'0'`，SQLite 原 UNIQUE 正确拒绝。八个原错误都为同栈 IntegrityError；原事件只有八 test_started，没有 case_started，原即时 BeforeRows/AfterRows 未生成且未补造。不能将其描述为八个 Backend 漏洞或迁移主体失败。

[修订 Probe](G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T56DatabaseFixtureRevision/SourceBodies/ProbeDatabaseT56Revision.py:145) 只 SELECT 原值并 emit，没有 UPDATE/override registry 或 fake 资格。独立 AST 对照八个 test_D 函数逐值相同；三份 runner/Probe 实际完整 diff 与 FullSourceDiff 的全部内容一致。其余差异只有新输入索引/脚本名/独立批命名。原实现/SQL/90s 超时/原断言均未降低。八 metadata 事件均为 value='0'、test_override_or_insert=false。

## 八项实际支持范围

下面逐项结合完整测试代码、8 个原 JUnit 节点、41 原事件、即时 Rows 和原 snapshot 字节判断；没有只取 Summary 的 pass 布尔值。

| 用例 | 实际到达与支持 | 有限边界 |
| --- | --- | --- |
| D01，Probe 202—221 行 | 保持原连接后提交项目 revision 3→4；CommittedWALBeforeRows 与升级后的全部十个观测表逐值相同。schema9→10、新增两 journal 表；本案实际 archive Metadata.sqlite 字节 SHA 匹配原 document，三文件引用逐 path/size/SHA 相同，partial 原字节保持。 | 初始 BeforeRows 的项目 revision3 与 After4 是测试主动提交；不能把升级结论写成两者整包相同。支持已提交 WAL 包含在快照，不支持并发未提交/外部实际费用。 |
| D02，223—238 行 | 实际将本任务快照 copytree 到独立 SeparateRestore，完整 Database9 重开验证 schema9/原行，再完整 Database10 升级验证 schema10/原行。原 archive Metadata.sqlite SHA 保持；restore_boundary 明确外部 floor 未恢复。 | Test 自有复制加原 Database 验证，尚无独立可信 restore 服务、可信 revocation floor 或更新费用对账。独立 restore 中间 Rows 没有单独导出，覆盖依原未改断言与实际 case pass。 |
| D03，240—249 行 | 原 Database9 拒 schema10、Database10 拒人工置成 schema11，两次真实 `schema_too_new` / EngineError，原 assert_error 检查 status503。最终 Rows 保持、schema11 未降级。 | BeforeRows 是9、AfterRows 是11；两次拒绝前后的中间状态由完整断言验证，没有另存中间 Rows。不是 schema11 兼容支持。 |
| D04，262—266 行 | 在 Test 自有 FaultMigrations 的原0010末尾附未完成 CREATE；事件 fault SHA 与原 SQL 加确切 suffix 的独立字节计算一致。实际 `migration_incomplete`；Before/After schema9、表和全部观测行完全相同，原 snapshot SHA 与引用字节匹配。 | 只验证这一确切未完成尾句和原 writer 回滚。 |
| D05，268—272 行 | 同方式附 `PRAGMA user_version=9;`，原 SQL+suffix SHA 与事件一致；实际 `migration_version_mismatch`，schema/table/Rows 完全回滚，原 snapshot 完整。 | 不是所有 SQL/磁盘失败分支验证。两坏迁移只改本案透明故障文件，生产十迁移保持。 |
| D06，274—278 行 | 实际改本案 Objects 既有引用字节，原 Database10 在备份阶段给 `backup_source_changed`；原 Rows/schema9 未变。原断言验证无 complete Snapshot.json。 | 验证这项自产坏引用，不等同媒体 decode/许可/运行资格。已创建的 incomplete 备份目录不被冒充可恢复快照。 |
| D07，280—289 行 | 实际删除自产引用；schema9→10、原 Rows 保持。Snapshot.json 明确一个 originally_missing Objects 项、all_referenced_files_present=false、rollback_compatibility_verified=false；两 Staging 引用 byte SHA/size 匹配，没有伪造丢失文件。 | missing 仍允许完成这项 schema 迁移，不授恢复兼容资格或可运行权限。 |
| D08，291—314 行 | 实际执行原0010 paired CHECK：三个 journal JSON 无 paired SHA 的 UPDATE 及不完整 step receipt INSERT 均被 SQLite IntegrityError 拒。前序项目 revision99 同事务回滚，原十观测表 Rows 保持；实际 step COUNT=0。 | 原结构 journal parent 是测试 SQL 夹具，未创建真实接受/Owner。TABLES 不含两 journal 表，parent/所有 journal 列没有独立 Rows 全量快照；支持这些完整 CHECK 断言与 count，不支持全部 stateful Setup 语义。 |

所有八案即时 Operation 都保留 status='unknown'、settled=0、reserved_units=1720000；预算保持 cap20000000/spent77518/reserved1720000，metadata 原 registry revision0 不变。这些是透明结构 SQL 夹具；金额与 unknown 行保留不能升级为真实费用核实、授权产生或真实 Operation 运行。快照 cost_knowledge 明确原 unknown operation，外部凭证、资源和撤销/新费用依赖仍在原 document 中。

## 生命周期、映射与 profiler

新真实批原 e4788d / session5506 经本人 poll774fc1 自然 tool0。wrapper PID340 / creation134360604384257546；child PID35344 / creation134360604390772679。独立对照 LaunchReceipt、RetainedChildWait、CommandReceipt、MainToolTerminal，PID/creation 完全一致，两进程实际exit0，stdout/stderr 原 byte EOF 均 true，forcedfalse，lifecycle errors=[]。原 Launcher stdout 中的 JSON 与 Method CommandReceipt 逐值相同；原 Method stderr 逐名八 ok、Ran8/OK，Method stdout 和 Launcher stderr 真实为空。

八 case duration 总和15.340084299998125s；原 unittest raw 为15.342s；child LaunchReceipt 的 wallclock 到 CommandReceipt ended 为16.3570667s。它们分别是 case 累计、suite 用时及进程观察窗口，不互相冒称。原90s child deadline、实际保留 Popen handle、Win32 GetProcessTimes、byte pumps 与原 Process.WaitForExit 源已全文核，不据 after 手工 marker 推自然0。

旧原批 wrapper31576/creation134360599532302243、child10396/creation134360599538821437 均自然1、双 EOF、forcedfalse/lifecycle[]；原 tool1、8 errors 仍保留。新 1126 before/after 原全部路径-大小-SHA 图逐值相等，且与实际修订索引423aff0b123716c48149ab5114725b42e66a6b0fd406ac01a2a7643daa3e24a3一一对应；旧1115图同样一致且在新图全部保留，仅新增11条。评审没有对当前999环境重扫描或回填历史运行身份。

已知证据限制 L01：Probe77—80 的 profiler 使用 filename 字符串精确匹配；原 Methods 只有 B40 计数，没有 B41 方法次数。不能补造 B41 _apply_migration/snapshot/connect 次数或依据 B4072次冒称已测 B41。B41 实际支持来自完整模块 path/hash、绑定定位检查成功后八主体启动、原方法代码/实际 SQLite 结果与未改断言。若后继必须量化 B41 方法计数，应由 Test 新命名批记录 frame/module 实际身份，不修改本批 Methods 或作事后推算。

## 当前问题状态与交接

本有限切片没有新的 P1/P2。原 Test 重复 INSERT 的修订在 D01—D08 范围可记为闭合；旧运行从不改为通过。原 RV80 两项、RV82 三项 P2 保持 OPEN；本批没有触达 B42 facts/未应用 candidate 的回归，不能替这些 finding 关闭。

未测仍包括独立可信恢复和外部 floor/更新费用、真实 Owner/native/安装资格、DTO/frame/stateful Setup、授权正常创作/真实多模态作品、三OS完整R1及连续R2。不能把 schema复制恢复或透明SQL fixture 当成可信管理动作。评审自身产品/DB/测试/OS执行、凭证读取、模型/网络、费用均为0。

自身过程根为 G:/开发测试/Codex/VideoCreatorImplementation/Review/DatabaseFixtureRevision-RV83。最初108683/0输出误展开完整输入映射被截断；后来仅按固定字段补读，原输出截断不作产品失败。末核 f1212e/0 的五条差异只是评审索引 bytes/size 字段名不一致，原大小/SHA均相同；原结果保存在 RV83InputAfterOriginalAnalyzer.json，纯解析归一后226个有限输入实际变化为0，没有修改 Test、期望或产品。具体源码/断言、RuntimeFacts、FiniteEvidenceChecks、Snapshot/InputAfter 为独立过程证据。当前读者全部释放，live reader=[]，无生产冻结；正式写工具实际终态另记 RV83FinalizerTerminal，最终交接为 RV83Handoff.md/json。
