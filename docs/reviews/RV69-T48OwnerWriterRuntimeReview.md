# RV69 — T48 Owner writer 组件运行独立复核

结论为 **LIMITED_COMPONENT_RUNTIME_REVIEW_FINAL**。独立核原 21 项：**19 pass / 0 failure / 2 error / 0 skip，整体自然 exit1 / NOTPASS**。没有发现本有限切片新的生产缺陷。RV67-I01（缺 begin_step 的 helper）与 RV67-I02（诊断 kind 冲突）在固定 T48 范围可关闭；RV63-P01 仅支持已经到达的 DataDir/unheld Control 组件窗口，**held 新 inode / writer 替换后守卫仍 OPEN**。本轮不授真人 Owner、API/MCP、安装/native/ASR、三 OS、Gate/R1/R2 资格。

## 精确输入与执行身份

正式根：`G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/OwnerWriterValidation-T48/`。普通根：`G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T48OwnerWriterValidation/`。正式 MD SHA `08068d6b5e341806e4bc5b9ce965a62995b05c9019d268e338ed90cfb3f61eb9`；JSON `cf31a6bd9bf69f907478c7e6200629f95603a9efb3ffaff0f14961697941fcdf`；Snapshot `67163f48c7cc2ac9cd45c7725fa6f499bc50344f135dd7d27979fcc104f2e068`；普通 manifest `dcbe4657d67f374c3e9d8ff62dc6dcb390494703a5f526c71775844ecd575de9`。

100 普通副本逐个实际 hash/size 等于 manifest 原/副本身份；加规则、正式文件、必要 B32 五源码及已固定 T47 原断言索引/Probe，共 114 必要路径，末核无变化。只读普通历史源，不读 B31/I50 热源，不重新核 1688 环境文件。原 Test 的 1688 before/after changes=[] 是原批观察范围，本 Review 独立末核仅上述 114 路径。

原命令：system pwsh `-NoProfile -NonInteractive -File .../OwnerWriterValidation-T48/RunT48.ps1 -ExpectedInputIndex a7641d112e0e2dcdf7dede4c515ee546d37259e7e9e21a0ea2d6eead1a8bab4e`，cwd 同正式根。原工具 session90143 / c1ea43 → 03785c 自然1。

| 原对象 | PID / creation UTC | 真实终态 |
| --- | --- | --- |
| Probe | 41308 / 2026-10-09T15:03:48.1700477Z | 自然1，21项原JUnit19pass2error，两原 BaseStream 字节 EOF |
| ActualMain driver | 46540 / 2026-10-09T15:04:22.1090150Z | 自然0，仅匹配预期负向；两字节 EOF |
| driver 内 cli.main | 同独立 ActualMain 批 | **业务 exit1 / owner_directory_denied403**，真实继承 ACL 先拒，TTY 未到 |

原 RunT48:43–56 持有原 Process/creation 并 CopyToAsync 原字节流；67–77 等终态/EOF再 Dispose。forced=false、errors=[]、no_replay=true；整批不能因 ActualMain driver0 或 19绿洗成0。原 raw/红保留；ActualMainStderr.raw 对应不安全目录可写主体拒绝，未更改 ACL。C01 单独真实 redirected stdin 确认拒绝403，不是真人 TTY 已授权。

## 原断言与实际组件边界

固定 ProbeT48.py SHA `be421914185ba4a2ecf41a25e6149ed61d5c77fadc0835ab03841002e8f5ddc3`。独立归一化任务名后与固定 T47 Probe 比较：原19仍在，18方法 AST 完全相同；只有 C18 增加 try/finally 观察，**原19全部确切 assert/error 调用保留**；新 C19/C20 不替代旧目标。Helper:161 真正先 `Engine.begin_step(lease,'t48-step','a'*64)`，随后同 lease/step/hash prepare→claim→observe unknown（162–165）。B32 Engine:521–541 在真实 SQLite 创建 running Step；prepare:586–588 仍拒缺 Step，没有 SQL 插入 fake Step 或绕过 Engine。

实际 Methods 记录 begin_step/prepare/_prepare_writer/claim/observe 各5；OwnerServices._management_transaction2。Counts 辅助真实调用链和原 Rows，不单独当功能通过。Probe.rows:108–115 保存 metadata/commands/projects/policy/budget/production/run/op；**没有独立 steps/events 表镜像**。真实 Step 的到达支持来自原调用、生产 prepare 条件及实际 Op 同 step/hash，不能伪称已经保存每个 Step 行。

Probe.mechanism:116–140 透明替换 OS inspector/confirmation/memorySecret：真实文件 stat(dev,inode)，明确 test-os SID/admin、测试确认和内存秘密，actual_owner_authorization=false。底层 Engine/SQLite/Store/Registry/Control 与实际文件动作照原源码执行；这些 adapters 不建立实际 OS Owner、vault、权利/安装资格。测试 route 的 verified=True、固定 fake manifest digest 和声明 rights 只用于组件布局，没有实际 provider/生成/收费许可。

固定 B32 必要源码身份：

| 相干源码（B32 SourceCopies） | SHA-256 |
| --- | --- |
| application/owner_bootstrap.py | d53044244c7206420e7961f97dd09a75d9bd3d8a4fcf452ad7e2ceea3797dec7 |
| application/owner_services.py | 57ea29425bb0e71b7d920ff292c21a3630421fdfb975d29cc23fddc3d57e5968 |
| application/production_authorization.py | dbec8e2002a00c39c7c908e8636f0db66d73a908c38bdf99ca88dcd0539bf6ff |
| application/engine.py | 3cfb8351560e53b97cded1fcc26748479da70694ca69d2e45c7506d86c59b823 |
| infrastructure/database.py | 96f1971b1b1980d39cb0575d6acce0325de657c24fa5d78e313aa2dcc8c6bef7 |

## 哪些实际 Rows 支持关闭

| Case / 精确普通收据目录（ExecutionRoundOne 下） | 独立结果及范围 |
| --- | --- |
| C04_management_revoke_keeps_policy_budget_unknown | before-management-revoke → after-management-revoke 只 metadata/commands 改变；policy/budget/production/run/op逐值不变。unknown Op reserved_units=1000000；Production/Group cap=10000000、spent0、reserved1000000，Run/Production仍needs_reconciliation。原 Owner 管理撤销后旧cap及重建registry两403，原 policy floor bytes不变；不重新提交 Op。 |
| C05_committed_revoke_exact_retry_completes_original_floor | pending-commit/before-exact-retry/after-exact-retry/terminal 全表相同。真实 DB revoke已commit后透明complete故障产生floor2 pending，current先503；同key/body完成原floor，pending消失，返回canonical原receipt、commands只有一个原revoke、撤销仍403。不是进程kill/restart，也不是新Op重试。 |
| C10_policy_key_revoke_separate_from_management | replay before/after 全表相同；changed body同key409/foreignproject403保持。policy revoke只metadata/commands/policy变化，policy.revoked=1；budget/production/run/unknownOp不变，Owner current未revoked、原Owner floor不变。 |

三者真正到达原 pending/unknown/预算断言，**关闭 RV67-I01 仅 T48 helper/组件到达缺口**。不表示真实 provider 未知成本对账、全产品运行/恢复通过；1 CNY 的reservation没有真实收费。

## 目录窗口按证据分列

- **C11（Probe365–404）**：实际把长驻 DataDir rename/copy，新 inode `281474978373268 → 6473924466007706`，原 DB 和 Owner Control bytes 复制并逐字节断言相等。`DirectorySwapResults.json` 真实记录旧 current/cap/action_guard/旧 OwnerAuthorizationService writer 全部 `owner_directory_changed409`。重建 Store 的 revocation_target 另在 Events 中确切 `owner_binding_denied403`；旧四回调的原 oracle接受403/409/503未被改成求绿，本次实际是409。**只有 Rows-after-directory-swap / terminal；没有独立 before Rows**，因此支持实际旧缓存拒绝，不给此 case 单独的逐表 noCommit 前后证明，不猜 `Replacement-DataDir.json` 或回填。
- **C16（519–534）**：原测试确认返回前真实替换 DataDir；helper423使用 directory_kind 修复旧诊断冲突，原确认后 Store.change:162 新鲜目录检查实际409。`Replacement-DataDir.json` dev保持、新 inode `281474978373328 → 2251799815347926`，原文件 size/hash完整映射。before-confirmation-swap / after-confirmation-swap / terminal 全表相同，floor原bytes不变、oldcap409。**关闭 RV67-I02，支持此确认窗口 noCommit 的组件通过**；不表示真人确认已执行。
- **C20（626–639）**：无held锁时真正Control rename/copy，dev保持、新 inode `2251799815347971 → 1970324838637319`、原filemap同 bytes/hash。current / oldcap / 原测试认证值 authenticate 三个确切409，before-unheld-Control-swap / after / terminal 全表相同、floor不变。支持 _control_identity 分支的实际组件拒绝，**不覆盖 held C17**。

据此 RV63-P01 增加 **PARTIAL_COMPONENT_RUNTIME_SUPPORTED**：固定 Windows文件系统 + TestOS真实stat 的长驻DataDir/确认窗口/unheldControl到达支持；原 cachedidentity源码修复支持仍保持。不能总关闭所有held/short-writer/全部TOCTOU。

## C17 / C18 原错误和 C19 正向不能互换

**C17 ERROR**：Probe:542–545 真正进入 action_guard、heldrecord非空，Control.rename:414 被 Windows WinError5 拒绝。没有新 inode，oldcap替换后的409和后续floor/Rows断言未到；before-held-swap 与 terminal相同仅保观察，不能签原目标PASS。

**C18 ERROR / 部分真实rollback支持**：production_authorization:172–180 使用原短writer transaction；OwnerServices:26–32 复用同一 connection；Probe:565先真正 `connection.execute(INSERT...)`，记录实际 `_Connection` 后568尝试Control swap，才被WinError5拒。B32 Database:159–169 因异常执行真实 rollback/rethrow/close；finally581–586在原writer异常退出后观察，**Rows-before-policy-writer / Rows-after-original-writer-attempt / terminal全表相同**。`ActualWriterAttemptObservation.json` 原SQL reached1、original_rows_equal=true、policyfloor minimum_revision2 + pending hash保留。原 policy/未知Op/预算不变，没有重建floor或吞异常。

这支持“真实INSERT后的原事务回滚和保留raised pending floor”，**不支持替换后 _management_transaction 最终current检查真的抛409**；异常在 rename就发生，587–596 的原检查/`ActualWriterRollback.json` 未达，不能用 finally 观察代替原后续断言。不是产品允许旧principal提交的反例，也不宣完整 writer TOCTOU 已验收。

**C19 PASS（598–624）**：另一独立case在真实held record范围内验证 rename确切WinError5、原目录/inode/filebytes不变、原cap仍有效，正常退出guard后heldrecord清理，before-Windows-lock / after-cleanup / terminal全表相同。`WindowsLockBoundary.json` 坦明替换source target NOT_REACHED。它覆盖此Windows锁保护条件，不能证明所有第三方权限/所有锁因果或替代C17/C18的新inode目标。

下一步由 Test 原角色在实际允许rename的受支持平台/已批准场景验证held新inode、oldcap、同SQLite短writer、commit前当前身份检查、确切409/noCommit/floor/unknown/预算保留；先证实真实新inode和原bytes再判守卫。Windows本批保ERROR；不关真实锁、不mock stat、不fake identity、不把PermissionError改成旧409期待绿，不写SQL/floor造状态。POSIX/macOS和真实安装/Owner权威还需独立准入；评审不要求当前批重跑。

## 限定结论和终态

RV65-P01的三TEXT消费者已在RV67窄组件关闭，T48 C12–15继续通过且原strict9样本/实际损坏/原pending恢复断言不变；不扩大成为真实Owner/新后端安装通过。原 C00–15 已有正向和原19目标都保留；T44/T46/T47/T48原红均不覆盖。

本轮没有新生产P1/P2，两个真实Error的source targets仍OPEN，归后续实际平台Test/Integration准备；若以后出现真实守卫接受/错误提交再按准确源归Backend。自身 artifact parser 首次952959因旧RV67索引字段误用pins/after产生StopIteration exit1，保原脚本和 `RV69OwnParserOriginalFailure.json`；读取真实records字段后29cf46自然0。它不是产品红或Test重跑，旧结果/期望/生产源均未改。

末核114路径无变化；所有自身输入reader已关闭、无live handle。仅自身报告/标准库artifact解析，产品/DB/Test/网络/native/ASR/模型/安装/秘密读取/费用0。正式 `RV69FinalizerTerminal.json` 与最后工具实际返回给终态，不以文件存在冒通过。完整目标仍三平台R1独立验收后连续R2。
