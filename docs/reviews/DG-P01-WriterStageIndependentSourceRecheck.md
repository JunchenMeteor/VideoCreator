# DG-P01 WriterStage 独立源码复审

结论：`PARTIAL_SOURCE_STATIC / OPEN`。原 DG-P01 的 Project/Command 及 accepted 记录两处缺口已有同连接前后检查的源码支持；完整相关短 writer 目标仍受下述 `DG-WRITER-P01`（Backend/P2）阻断。未运行数据库、产品、测试、模型或 OS 调用，未授 Owner、安装、资格、R1/R2 通过。

## 固定身份与方法

唯一新实现来源为 `G:/开发测试/Codex/VideoCreatorImplementation/Backend/QualifiedIssuerAndWriters/WriterStage/SourceCopies/`，由正式 `SourceIndex.json` 的 `ordinary_copy` 定位。未读当前 IssuerStage 或生产实现。任务范围是统筹本次明确分派消息；工作区与仓库规则已核读。

| 固定输入 | SHA-256 |
| --- | --- |
| Handoff.md | 613bcb49c186839ca2e6df2a04b2511ce50cb23696b6a74b749eaf8b5f13ebf1 |
| SourceFreeze.json | bca8942ed3b83eaa8a777f1eb82f13b9fdc781ffa9de709bf6735e9310c5a750 |
| SourceIndex.json | a2b47484cedc37c5be7f50ee77605e8af2d9bdc600a6e66a92286c6bc5bf0e98 |
| SourceDiff.patch | 23dfbbbe25abcf3c6a9ad10bb9e1c6b24fa7c758b2a8f6cc5d4b433ec7756a54 |
| 原 DG-P01 问题单 | 7106a9747f8c35f5ca9f5421b1423728f04dafa2fdb701ae4d70c405e4958bd8 |

独立读取校验 88 完整普通源，解析 78 Python AST，与原 DailyGoal 固定索引逐项核对：85 不变，3 增量；读取三个历史普通正文并重建 11777 字节 patch，与交接原文完全一致。99 个有限输入末次 bytes/SHA 均未变。没有产品模块 import；AST/标准库解析不构成业务运行。证据为自身 `Review/GoalWriterCorrection/SourceVerification.json`、`ProtectedSurfaceCheck.json`、`CallChainReview.json`、`FixedInputs.json` 与 `InputAfter.json`。

三增量完整身份：

- `application/engine.py`：a459d2cd8d6d765e7695a13e3c0440970c13f6b1f0ff91f4f64ed6249223f62e。
- `application/owner_setup_confirmation.py`：88fdc999fbfafbbc48b527bb147bd3022c2923042389f710014ff96df5789bc0。
- `application/owner_setup_service.py`：d8f307d2806a43c27954d8b319515b649e9fe572fcb920525598d40dc8c6298f。

## [P2] DG-WRITER-P01：V2 Goal 意图 writer 缺后置原实例源检查

归属 Backend；状态 OPEN；证据 SOURCE_STATIC。该分支继承自原固定 DailyGoal 源，不是本次三增量新引入。固定文件为 `G:/开发测试/Codex/VideoCreatorImplementation/Backend/QualifiedIssuerAndWriters/WriterStage/SourceCopies/services/engine/src/video_creator/application/daily_projects.py`，SHA `08bd9b43520b230abfe5b6adba2fd25be09260c0ff169e330031040e1b670d9a`。

`OwnerSetupService._execute_current:467–468` 经原 `goal_source` 调用 `accept_owner_setup_goal`。`daily_projects.py:833–849` 开启独立原事务，834 行在同 connection 调 `service.assert_goal_local_current`，随后 838–839 行 INSERT Goal 意图 Command、848–849 行 INSERT pending locator，退出块前没有同 source/connection 后置检查。`Database.transaction:165–167` 随即 commit；850 行才调用 `_commit_intent`，后者 935 行的完整 source 校验已经晚于前一个事务提交。`ProductionAdmissions._issued_guard:237–243` 和 `ExecutionRegistrationStore.current_guard:580–597` 收尾只清除 guard，没有补该原实例检查。

最小触发是：834 行校验成功之后、原事务退出之前，初始化源、原数据库文件身份，或同连接 `metadata.instance_id` 不再符合原绑定；当前代码可能先提交 Command/locator，再在下一事务入口拒绝。这是静态条件链，不是实际 Windows 复现；不声称外部 SQLite 写连接可越过 `BEGIN IMMEDIATE`。同连接元数据故障和真实文件/句柄失效应各自独立验证。

最小修正应在原意图事务内写入之后、所有正常/原意图重放分支退出之前，再调现有原 source 的同连接局部检查；由原 `Database.transaction` 在异常时回滚。不能修复或重造 instance_id、换 Engine、扩新 callback/True 权限、清 pending/floor/预算，或绕过原人审与资格来源。准确早问题单已固定为 `Review/GoalWriterCorrection/EarlyFinding-DG-WRITER-P01.md`（4f8c07f28a0efe49d708bab166768a8395a348d5b0942ce2e378326095d34485）。

## 已有源码修复支持

| 实际 writer / 调用链 | 核到的前后检查 |
| --- | --- |
| 初始及 prepared journal，owner_setup_service:144–164、178–186 | 原 preparation + initialization source，在同 connection 写前/写后校验。已完成 prepared 的只读重放保持原 draft/key 校验，未改为新写入。 |
| Project/Command，engine:225–261 | Native consumer:106–112 从原 Bundle.owner 派发；严格 concrete `_NativeInstanceSource`，246 写前、260 写后；精确 project 重放在253再次局部校验。 |
| accepted_json，owner_setup_service:267–277 | 268–269 与276–277均检查原确认和 preparation，传同一 connection。 |
| step、receipt、blocked、planned IDs、completed、abort | service:396–410、418–430、449–457、582–589、651–658、660–669均有原同连接前后检查。blocked 只核初始化身份、不新获取人审；marker 失败通过458–460保持原 EngineError。 |
| 实际 Owner 初始化 | owner_bootstrap:267–283 经原 action source 转 service.assert_action_local → _accepted_local，269/283处检查同 connection。 |
| execution 与 creation 安装 | owner_services:48–56 的原 OwnerAuthorizationService 管理事务，51/56处 _setup_local；execution_registration:171–188 与 daily_projects:384–391均使用该原 wrapper。原独立 floor/pending 不被 SQL rollback 清掉。 |
| 最后首次 Goal/production/derivation | daily_projects:950–984 在958/981–983检查；engine:380–454及commit_child:989–1029使用传入原 connection，没有另开提交事务。此保护不能倒回已提交的833–849意图事务。 |

`infrastructure/native_instance_source.py:193–207` 的真实实现检查 retained 原对象、原 Engine/Database/root/file、transport local current，并查询传入 connection 的 `metadata.instance_id`；不是作者列表或 guard 数量推定。`Database.transaction:161–172` 的 `except BaseException` 明确 rollback 后重抛。因此这些后置异常的源码路径仍在原业务提交之前；本次没有实跑 rollback 或并发。

## 兼容、重放和期限边界

`Engine.create_project` 第222行公开参数及返回注解与原版 AST 相同，只派发原私有共享业务 core，不向普通 public 调用暴露 setup guard。原 canonical/body/key/Project/Command 处理保持在 core，未自动修改 public 权限。旧 main、native setup entry、Database 三件逐字节不变；其它85原件身份保持，预算、unknown、外部 floor、历史回执及资源资格路径不能据此认为已运行。

`_NativeInstanceSource.assert_engine_current:163–180` 仅在尚未 `_setup_bound` 时使用初始化 deadline；完成后原 source/full OS 与同连接 local 检查不会重启或重用20秒作为人审期限。确认消费者仍通过原 intent.expires_at_us 与原 retained native confirmation deadline 拒绝超期；没有续期或清除权限。超过初始化20秒但仍在合法业务人审期限内的实际成功、合法幂等重放及拒绝都仍待独立 Test。

恢复保持原 `recover_pending/_deny_intent:852–929` 的 issuer/native proof 与外部 pending floor；不能拿历史只读回执当新执行许可，也不扩大拒绝恢复权限。本轮不宣所有恢复 writer 或 OS TOCTOU 已安全。

## 留给独立验证与交接

独立 Test 需冻结正确修订源后核：真实原实例源的阳性、outside-check 与 writer 之间元数据改变/删除的原前置拒绝、各原 writer 写后到 commit 之前失效的同连接局部拒绝与完整 Rows 回滚、V2 意图 Command/locator 特别窗口、合法重放、合法人审期限、原预算/unknown/floor 不被重造。不能用 SQL/Mock 自授 Owner 或资格；元数据机制与真实 OS/held source 失效分层。

本轮 B43-I01（同步 stdout 未可中断）与 I02（OS buffered early Goal）继续独立 OPEN；qualified issuer、真实 native/Owner/三 OS/多模态成片/RAG 交付与完整 R1 独立验收后连续 R2 全目标未获本片资格。历史失败、原拒绝和原工具记录保持原件，本片无新产品/测试执行。两次读取输出的显示截断已定向补遗漏必要段，未冒全文或执行失败。源输入读者在有限读取与末核后释放；正式工具终态另见自身 Terminal 及 Handoff。
