# RV36：B21 / T28 core 租约释放独立关闭评审

结论：**RV33-P01 / P2 / Backend 在固定 B21 core release 与真实隔离 SQLite 机制范围关闭。** 修复确实消除「已合法释放的 core 核实租约仍保留 worker，阻断同原 Run 显式重授权」的缺陷，并保留当前 ownership/fence 防护及 unknown 账本。本次没有新增阻断 finding。

闭合依据来自固定源码、原 T26 红、T28 实际完整服务调用与 24 份调用间即时 SQLite SELECT 快照；不由 root/Test 的 PASS 摘要代替独立结论。Review 只读原证据，产品/测试/DB 查询/ASR/native/provider/network/key/fee=0。关闭不授 RuntimeBinding、真实安装/Owner 权限或完整 Gate/R1/R2 资格。

## 固定身份与材料

唯一 T28 ordinary 根为 `G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T28CoreLeaseRelease`，按实际 Manifest copy 字段定位。114 ordinary 的 SHA/size 与记录的原件一致；另外实核 B21 SourceSnapshot 的 47 个 ordinary 源，每项与 T28 对应完整文件同 SHA/size。只审相干完整方法和 Test 正文，不称 47 源逐行全审；不读 B22/I30 当前源。

| 固定对象 | SHA-256 |
|---|---|
| B21 engine.py | `24aad20ab71ace1c1e03110f448b973c620007de79a17ea9656440d90c92c351` |
| B21 SourceSnapshot.json | `24638bc7c206ba33a88a2395380e978ae5ae8e785358e1c4d220ca4d212b8a4e` |
| B21 AcceptedSourceChanges.diff | `826056bcb37e390ed809c036b191a77f24561cc332f9b5cc00a77604e0b3ff86` |
| B21 Interfaces | `239c94c0723c1d3ebd1d53d4f70427e5a9fd9dbddae13544e23eb6eb144af52d` |
| T28 ProbeT28.py | `2507d169e6e3735e1e48242b5bea5f13cc6a018ec8e6947ea6fd4521c13efd7f` |
| T28 Handoff MD | `7c4181860af7b1ee534c950163e5219aca6a0e2cd9c4caf3b0d3f70f25a32784` |
| T28 Handoff JSON | `818a3b319e644066fde301197ffb9ac85056e8659534b16f8cf704a6c02fbd81` |
| T28 HandoffSnapshot | `df02cde06034317a08cf2fd13e10a2503c4f0c080d16b262fd412c025e7c2f8c` |
| T28 OrdinaryManifest | `c096386e7d73fc1eace287a233ed0f5ea320d66b617ef9d5efdfb906f03481aa` |
| T28 TerminalReceipt | `9f71efacf27fe3529c71a66d989757481a33ee7ac309ca0d96a1c2a4d94ca4d4` |

自身 [RV36InputPins.json](G:/开发测试/Codex/VideoCreatorImplementation/Review/CoreLeaseRelease-RV36/RV36InputPins.json) 有 177 个实际读取输入 pin；[RV36SourceAfter.json](G:/开发测试/Codex/VideoCreatorImplementation/Review/CoreLeaseRelease-RV36/RV36SourceAfter.json) 末核 176 个固定输入，0 变化，协调者可改任务卡只保首次 pin。复用 233 包/999 runtime 旧归档，不重新扫描或把归档资格升级为安装通过；未复制/重新查询私有数据库。

## 原红保持，新版本原断言实际到达

原 T26 的 JUnit `384d16596bcef6bd4b5af5729b9758320794dbeb1aa958429cf9d5d7b5a5b81d`、Stderr `595bada20fd2d8918071c2139d44084448e327926e38bb79eb2ebbc17ef72a89` 与 CommandReceipt `1592257b994a10dd1018af0ca72acb86ac2c4aab8d9df6bf86a10737b980c9f6` 已重新按原固定 ordinary 读取核 SHA：9 tests / 8 pass / 1 error / natural exit1；原 Probe338 到 _target125 的 `production_reauthorization_active_lease` 真实错误保持。原失败运行没有 lease 逐字段即时快照；本次仍不倒填那些缺失事实。

独立对照固定原 ProbeT26 与 ProbeT28：九个原 test 方法的全部非空正文行均在新方法中按原顺序保留；原第六组28行及所有原 assert/error_code 保持，只在相干调用间追加只读快照及断言。完整新 Probe 绑定实际 B21 模块与 SQLite，没有 AST 摘取或替代 Engine/_target/Worker 方法。原第六组 [ProbeT28.py:360](G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T28CoreLeaseRelease/TestSources/ProbeT28.py:360) 的 reauthorize 后 request/revision/reserved/spent、normal acquire 拒绝、新核实 fence、旧 heartbeat、唯一原 Op/external ID 断言全部执行，之后才写 Snapshot8 和 Events marker；原 JUnit 对这组为绿，不以 marker 单独充当完成证明。

T28 原唯一工具 `84f261/session93268 → e51d64` 自然 exit0；wrapper PID30372/CreationFILETIME134359736462274736，Probe PID45824/134359736476018916，各真实 natural0，forced=false、lifecycle_errors=[]。原 retained child wait 收据 SHA `aef955907e1dd45dbb6844f96009a36404ca6e13fff5dd30bc94adfd32b81292`；CommandReceipt `bfa1138e7d434a6be7d1df8da7ab8dc1edfd612e9e2453256942b6b24cfc2372`；JUnit `00e57508e26fc5dfb558ae9d57c069edd085c81bd2aa87f6d5d3ce48ee1f4d0e`。原 Stderr 是 11 tests / 0 failure/error/skip / unittest44.276s，不是标准或安装自查时间。

原 input index 含1286 records；实际 InputBefore/InputAfter 各3579路径，逐值变化0、两文件 SHA 同为 `84580437bd8b28ebb682b239e8023188b2209d6d36c8ee31de187cb8c16e721c`。没有用方法计数补未达断言：实际聚合 acquire16/release8/observe6/heartbeat3/reauthorize7/_target10/Worker.finish1/heartbeat_presence1，只与完整代码、raw 和即时快照相互核对。

## 为什么可以关闭 RV33-P01

[engine.py:671](G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T28CoreLeaseRelease/FixedInputs/Backend/services/engine/src/video_creator/application/engine.py:671) 的唯一 B21 窄修，在原 `db.transaction()` 中先调用未放宽的 `_lease(...,allow_cancel=True)`，再对已核 exact Run 同时 SET worker_id=NULL、lease_until_us=0。原 `_lease` 157–167 仍核当前 worker、fence、未到期 expiry 和允许 status；[Database.transaction:158](G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T28CoreLeaseRelease/FixedInputs/Backend/services/engine/src/video_creator/infrastructure/database.py:158) 为 BEGIN IMMEDIATE、异常 rollback、成功 commit。因此校验与 ownership 释放同一 writer，不靠放宽 _target 或伪造 Worker invocation。

原 recover393–408 仍不访问 needs_reconciliation；本次该状态由 release 自身释放 owner，不需要修改恢复分类。_target107–125 继续拒活跃 worker/expiry，reauthorize153–177 继续在真实 wait/Request/最新 Run 条件下重新核授权，清 wait、写 current pointer；原未知 Op 仍使状态保持 needs_reconciliation。acquire431–436 仍生成新 fence；Worker.finish471–491 的私有 scope、presence 行为未改。

24份快照由 Probe214–237 在下一业务调用前真正 SELECT Production/Run/Operations/Steps/budget/wait/pointer/presence 后保存。独立核所有文件 SHA 与 Events 中 path/hash/actual_rows，24/24一致。原139 Events含24即时快照、28真实拒绝、11新实例和11终态查询；以下是实际行值，不是从 B21 SQL 推算：

| 已核调用窗口 | 释放前 → 释放后或拒绝后的事实 |
|---|---|
| 普通 lease 观测 unknown 后 release | worker `t26-worker`→NULL；fence1→1；expiry61000000→0；attempt1保持；unknown/reserved500000/spent0保持 |
| 原 core reconciliation group6 release | worker `core-reconcile-mechanism`→NULL；fence2→2；expiry61000000→0；attempt2保持；needs_reconciliation/唯一原 unknown Op 保持 |
| 原同 Run 显式 reauthorize | 同 request/revision/Run/原Op/预算；wait 有→无，current pointer 无→有；下一 core fence3/attempt3，普通领取仍无结果 |
| 当前 core owner 未释放时 reauthorize | 真409 active_lease；完整 Production/Run/Op/budget/wait/pointer 未变化 |
| 已释放 lease重复/旧lease作用于新owner | 真409 stale_lease；新owner fence3/expiry61000000 与其Run/原Op未被清；新owner活跃时仍拒重授权 |
| Worker 私有 finish回归 | Run worker→NULL/expiry0，fence2/unknown Op 保持；presence executing→idle、active_run_id→NULL；随后同presence heartbeat实际可达 |

对于 ordinary、原 core、当前 core 三个释放窗口，独立比较完整 Production、Operations、Steps、budget group、wait原字节、pointer原字节全部相等；Run 的 fence/attempt 及 needs_reconciliation 均保留，只释放 worker/expiry。原 unknown Op 的 actual_units=NULL、settled=0、reserved_units=500000 仍在，不自动 settle/重交；Production 的 reserve500000/spent0及 budget group完整值保持。原core request原JSON/hash/revision及外部ID留存，新重授权不变成新的production。

具体快照关联及逐值比较见 [RV36FactsCheck.json](G:/开发测试/Codex/VideoCreatorImplementation/Review/CoreLeaseRelease-RV36/RV36FactsCheck.json)。这满足 RV33 原有限关闭条件：正确释放 core/ordinary ownership、保护真正当前 owner/新 fence、保持 unknown/request/budget、原后段断言到达、Worker私有finish回归。旧 T26原9项仍 NOTPASS历史，B21/T28新11项为所测机制通过，两者分版本记录。

## 保持未测与阶段边界

Test 实际 Engine/SQLite 是11个隔离新实例，注入 clock=1000000；expiry61000000是这些新快照的真实存储值，但不是 OS 墙钟或并发实验。测试authority重hash完整47源和明示NotInstalled三文件，Owner/admin/凭据为公开dummy；CNY5隔离ledger不是用户真实额度或费用。不能由 typed receipt/文件hash推真实安装、法律权利、Owner认证或 native guard 资格。

并发 owner/writer/撤销竞争、非零 settled spent/真实退款、实际 provider受理/adoption、HTTP/MCP、跨进程持续 Worker/native/ASR/媒体/Bundle、完整68/Gate0/三OS和R1后连续R2仍未测。本轮不新增这些为 RV33-P01 的反向冻结门，也不以有限绿签全产品。RV35-I01 的 frozen T27计数说明保持，本次不改 T27原证据。

Review过程的宽读截断已用关键链有界补读；`7a386f` 曾误猜不存在的 T26OrdinaryManifest.json，只读查找错误（进程exit0含错误）保留，后由自身 RV33 pins获得实际 oldraw路径，不当产品红或源漂移。全部 reader/tool 终态、source读者释放、live=[]；只写本报告与 `G:/开发测试/Codex/VideoCreatorImplementation/Review/CoreLeaseRelease-RV36`。本阶段 FINAL，完整R1三OS独立验收后连续R2、安装实例持有数据和前台五步不缩减。
