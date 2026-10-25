# RV33：B19 授权机制与 T26 原唯一实际批独立复核

结论：**NOTPASS 保持；RV33-P01 / P2 / OPEN，归 Backend。** 原批重授权错误由完整服务实际运行产生；固定源码支持 core `release_run` 与重授权前置条件之间的实现契约缺口。没有证据要求 Test 把合法 core 租约改装成 Worker 私有 invocation 才能结束。Review 未运行产品、数据库或测试；未批准 RuntimeBinding、安装资格或 R1/R2。

## 固定输入与身份

唯一普通副本根为 `G:/开发测试/Codex/VideoCreatorImplementation/ReviewHandoff/T26ProductionAuthorization/`。任务卡曾错误拼到 TestDevelopment/ProductionAuthorization-T26 下；该目录不存在的读取错误保留，统筹已纠正。以正式 Manifest 的 copy 字段定位，未读 B20 或任何当前生产源。

T26 普通 Manifest SHA `799d793d9d9eca5319a6eeaf09c8ed49ae0ddc44d02597e91e9230f3a2edb7a7`：136 bounded copies 全部实核 SHA/size，与其记录的 original SHA 一致；另 4 terminal copies 全部一致。B19 Snapshot `4961e3076bf0113e0f2ac145daf73da2caf75de027eb95b382c4df01a286ae6c` 的 46 source_map 与这些普通源逐项匹配。仅阅读相干完整方法/协议/测试正文，不声称 46 个文件逐行全审。

T26 正式 Handoff MD `e15c16c24e0314dd720d02cd69b1728f84e64acb79b8b36cb4ea7d3a9cc3c6f5`、JSON `e06ddd0ed32dad80db82eb754adb42913e16b3d446ed3cb5b80412763a20e56e`、FinalSnapshot `c443a54783336de95d7fd14cc14cb2eff951c777a763026bfd3ccba32b783234`、Terminal `6d9de5cf22a36df78a2f5c545257a18278f534b43e0167f3a0371860e223554a` 均实核。Test Analysis `c2e62d1e86743570704589a6eb711e081b1a2b700f60f7454b2b305c2b546543` 只作线索，结论来自独立读取原 raw 和源码。

原批准 index `61ed79f69d7177f42ef4d0ae0eaaba97662387de4e195039a28515655d3c92fb` 含 1283 records：Backend46 / packages233 / runtime999 / documents5；原 InputBefore 与 InputAfter SHA 同为 `3c3565de65c0ebdb2155ea794f3e11cc212319818ad15b8b1e0ef180b378ba87`，实际路径映射各 **3572**，逐值变化 0。这两个计数不是同一口径。1232 包/运行时既有正文归档仅按原 index、前后映射及 Manifest 复用，Review 未重扫运行时、不把它当完整已安装资格。自身 InputPins151 条，末次固定输入复核150条/0变化；统筹可修改的任务卡不纳入末次源稳定性断言。

## 原唯一批真实结果与支持范围

原工具 `8cd1f8 / session90256 → b8e8c6` exit1。wrapper PID46536 / CreationFILETIME134359695663917833 与 Probe PID51468 / CreationFILETIME134359695677999800 均自然 exit1，forced=false、原 lifecycle_errors=[]、retained wait terminal=true。argv 为便携 CPython3.13.16 的 `-I -S -B -X utf8`，不是正式 root.venv 产品闭包。Stdout、Stderr、JUnit 与两级退出收据一致：**9 tests / 8 pass / 0 failure / 1 error / 0 skip，unittest45.365s**。原唯一 error 是 planned第6组（实际按 unittest 名排序最后运行）的 `test_unknown_and_budget_survive_reauth_new_fence_without_resubmit`，并非 assertion failure、XML helper 故障或进程超时。

原 JUnit SHA `384d16596bcef6bd4b5af5729b9758320794dbeb1aa958429cf9d5d7b5a5b81d`；Stderr `595bada20fd2d8918071c2139d44084448e327926e38bb79eb2ebbc17ef72a89`；CommandReceipt `1592257b994a10dd1018af0ca72acb86ac2c4aab8d9df6bf86a10737b980c9f6`。方法统计 SHA `eea0f72b90ce651a6087399393d6a7f9f0800d06cbb6435f793007ccd090b2de`，403 个统计 key 包含 module/class 等，不能称403项业务通过；全批聚合中实际 acquire_run9、release_run2、recover12、observe_operation3、reauthorize5、_target6、Worker.finish_reconciliation1。这些计数不补成逐组逐调用 trace。

原 82 Events = test_started9、actual_instance9、terminal SQLite查询9、实际拒绝18、fixture hash观察36、restricted范围记录1。九个实例均 schema6，失败组真实末层查询为 Production1/Run1/Step1/Operation1/Admission2/Policy2/Command4；它只证明表数量，没有失败前 lease 的逐字段快照。Probe 全包 import 后真实服务写 SQLite；fixture 未 SQL 插授权/发布事实，网络/外部子进程被 audit hook 拒绝。

八个通过组有限支持：旧0.2规范正文/幂等与0.3缺alignment保持等待；独立管理 capability 及撤销；selection不自动复活旧Run、显式无未知同Run重授权及current pointer；prepare缺guard拒绝/去重/撤销后claim保250000预留；phase/action及expiry拒绝；原text Asset、route/floor/resource漂移；cancel/旧Run拒复活；真实restricted Worker原target读取与finish。**不把第3组 pointer 通过或第7组 finish 通过倒填第6组。**

fixture authority 实际重核46份源与3个测试文件，并返回 typed evidence；Registration/Resource/Runtime 原文件明确 `actual_owner_authenticated=false`、`complete_product_installed=false`。这是隔离机制的真实文件哈希，不是真实 Owner、资源安装、OS许可、权利或生产准入。管理凭据为公开 dummy；paid 只是测试 CNY5 group/Production1/route0.25，未碰实际 CNY20/ValidationInstance。

## RV33-P01：core release 未清持有者，阻断显式同 Run 重授权

**P2，OPEN；Backend 唯一生产修复 owner，Test 补独立原断言和即时观测。**

固定普通源：
- `Inputs/Backend/services/engine/src/video_creator/application/engine.py` SHA `ace4a97cf676fa7aafd8ad96615860a58ac6617b1d2daf3dce0d46e8b4662d8e`。
- `application/production_reauthorization.py` SHA `8ec7166a3bdbbbefce03e4c1fb2896cb56da8129061f98ea7ef49f4807cfe111`。
- `application/worker.py` SHA `5058afc2e32a2047015c68b9563447838cac47fdbfa5487bb37bf754d03130be`。
- `TestSources/ProbeT26.py` SHA `b1b97d94ef03834d07c5fbdfddc7e749e0be1c1765e53e6125b868a01257871f`。

最小触发：最新 unattended Run 有原 pending/unknown Operation 和真实 authorization wait；core 使用 `acquire_run(..., reconciliation=True)` 得到有效租约，以原 Operation观察 unknown，然后调用 `release_run`；在未重交/未清账的前提下执行合法同原Run/Request管理重授权。

完整源链：
1. Engine157–167：`_lease(..., allow_cancel=True)` 接受 needs_reconciliation，核 worker/fence/expiry；LeaseGrant242–246 没有“只能由Worker finish”的模式字段。Engine410–436 给 core 核实租约，不要求 Worker presence。
2. Engine574–579 仅对有 active Worker presence 的 needs_reconciliation caller 要求私有 evidence port；原 core caller没有这种presence。合法 core observe/release 不需要虚构 binding/allocation/Worker invocation。
3. Engine614–632：unknown 将 Run/Production 设 needs_reconciliation，未清 worker。Engine671–676 的文档明确“Stop holding this attempt, preserving uncertain dispatch for recovery”，方法允许上述租约，却仅更新 lease_until_us=0，然后调用 recover。
4. Engine397–403：recover 仅选择 running/waiting_provider/cancel_requested，排除已 needs_reconciliation 的 Run，所以这次 release 不进入清 worker_id 的分支。
5. Reauthorization107–125 先核原最新Run/Request/真实wait/unattended，再要求 worker_id为NULL且expiry不活跃。原 Probe322–338 顺序到达这里，实际 _target125 抛 `production_reauthorization_active_lease / 409`。
6. Worker471–491 另外有完整受限 finish：清 worker/expiry并释放presence；这条第7组已绿。它依赖真实私有 invocation/execution binding/固定渲染原allocations（Worker297–338），不是对任意core原未知账本的替代结束口。

ADR0024 原81–83允许撤销后原核实继续、未知不清账，同原Request显式恢复；B19 Interfaces35–37承诺释放普通ownership、未知保needs_reconciliation再同Run重授权。core release 的合法调用及公开承诺与现实现不一致。修改 Test 改走完全不同 Worker fixture只能回避该接缝；删除 _target 的持有者防护则会放宽并发安全条件，均不足以关闭。

**实际 / 推导边界：**原 raw 证实 release 未抛异常、接着安装新policy、实际重授权拒绝；不是 Review 新复现。固定源与固定 Clock1000000 支持“release置expiry0但保worker标记”的解释；取得租约时推导expiry61000000是计算值。原运行未单独记录这时 worker_id、实际fence、expiry或budget逐值，报告不宣称这些缺失行值是即时原观察。来源与因果源码足以定位 P2 契约缺口，但进一步验证需要 Test 在独立新版本补真实快照；不直读旧私有DB补作原事实。

最小关闭条件：
- Backend在同短writer核当前 exact Run/worker/fence/有效租约后，真正释放该attempt的ownership；needs_reconciliation路径亦不得留已释放的持有者标记。保unknown/原Operation/external ID/预留/spent/Request/限次及wait；不盲settle、不自动provider重交、不把策略变更当恢复完成。
- _target继续拒绝真正当前持有者/活跃lease，stale lease不能清新worker。维护Worker私有finish的presence协议；不能泛写任意Run、清current fence或降低guard。
- Test保原 Probe/raw/9项结果与失败期望，新固定批真实观察 core获取后、observe后、release前后、reauthorize前后 Run(status/worker/fence/expiry/clock)、原wait/pointer、Operation/外部ID/费用与请求快照；原第6组后续断言必须实际达到。
- 独立覆盖普通租约观测unknown后release、core核实租约unknown后release、当前持有者拒绝/stale lease拒绝、新核实fence/旧lease拒绝、完整Worker finish回归；既有unknown唯一Op和预算/限次不变。当前并发、非零settled spent、真实provider核实/退款仍需另固定实验，不能借本批绿。

## 未到达与未测

Probe339–350 没有执行：未知状态下重授权后的request SHA/revision_cycles/reserved/spent比较、normal领取拒绝、新核实fence大于原restricted fence、旧heartbeat拒绝、最后唯一原Operation/status/external ID逐值核对。方法聚合、行数、其他组绿不能补齐。原 NOTPASS 原样保留；不取消费用未知、不降低原阈值。

未支持：实际Owner/独立管理员认证与安装adapter、真实权限/权利、policy声明/七项QC/final current Bundle、自动创作/导出/import、真实ASR/TTS/模型/媒体、HTTP/MCP、OS Worker生命周期/Job与当前writer撤销竞争、完整68标准、三OS/Gate/R1后连续R2。缺接线不是永久503设计结论。数据安装实例持有、前台五步及完整R1→R2目标保持。

## 过程与终态

只写本报告与 `G:/开发测试/Codex/VideoCreatorImplementation/Review/ProductionAuthorization-RV33/`。RV33InputPins/FactsCheck/SourceAfter固定全部身份与既有事实；全部源码/evidence readers终态释放，无当前生产freeze，live=[]。Review本轮产品/测试/SQL/ASR/provider/key/fee/network/install/apply=0。

保留只读过程问题：卡误拼路径exit1、假定ProgramFiles rg路径不存在exit1；之后用Manifest实际copy及现有rg入口。一次PowerShell数组拼接导致ReadAllLines错误（进程exit0但有读取错误），已用Join-Path纠正；若干过大元数据输出截断，不计全文已读或产品失败，关键Lease/release/recover/reauthorize/Probe方法与原raw均有界实读。未执行被拒ASR补丁，也未评审代人类授权。

