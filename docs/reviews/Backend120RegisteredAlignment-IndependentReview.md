# Backend120 registered Alignment 独立源码评审

结论：SOURCE_REVIEW_FINAL；三个 P2 / OPEN 均归 Backend。没有产品、Pydantic、SQLite、推理、模型、原 19、OS 或作品执行；不能据此授资格、验收 Gate/R1/R2 或实际安装。原 B118-P01 的共同 pair 匹配比较已获局部源码支持，但本版仍有 B120-P02 的 writer 源消失分支，因此不能关闭整个 current/发布一致性目标。

## 固定版本与审查范围

任务卡 SHA `21bcb1e8b5e87903c5195a69c1bac9415dd04896f9fc3e2d557e149f3108e523`。只消费 Backend/RegisteredAlignmentImplementation/SourceStage 的 120 普通源，索引 `7022d167fe0ef30a05aba3972dacd1be012d440c6f9a98e543e0d5669e167660`；对照停止 118 索引 `db3403175d6bec860cbe4b9aacc9a07300d1d1e9387c3b481a4a6b815baeda1f`。实际 2 新增、9 变更、109 原件相同；109 Python AST 可解析仅作为源码身份事实。独立从完整前后文本重建作者的全部 115119B diff，逐字相同，SHA `36808549d0ccb4ebf372fee1fdde54648221edd3e8c2bfd6009e8ffdaab55332`。没有调用 patch 或 product import。

全文审读两个新 domain/application registered_alignment 源，以及九个变更源的完整新增/改变方法和必要原事务/调用上下文。原未变的 109 源由固定前后字节身份保护，未把“全部正文重新阅读”或 AST 通过作为行为验收。主要链包括 affected 授权/同 command companion、原 ASR journal executor、唯一单 JSON Worker、Engine 新 gate 与原 Operation prepare/claim/observe、私有 Step 提交、actual result reader、第九 MethodEvidence、正常 verify/publish 和 correction pair writer。仅消费 ADR0056/0055 与 architecture 角色文档 §6；§1–5 候选、被拒 intersection、热 Media 和 Backend 修订均不属本版。

另按精确固定定位补充原 Media38 的 workflows/bundle_v03.py，23176B，SHA `69e31a91a7977df3d57966af9a98fff09724d350b6b2bf451e31956e741affd8`，用于独立精度派生契约核对。没有读取 current 热 Media。

## 独立问题

| 编号 | 等级/状态 | 实际源码条件与影响 | 修复归属 |
|---|---|---|---|
| B120-P01 | P2 / OPEN / SOURCE_STATIC | registered_alignment.py `_alignment_sources` 212–225 校对实际 ASR transcript，但 255–273 把 prediction.intrinsic_range 自身写入 canonical predicted_range，未比较对应原 ASR 时间。initial 登记 629–648 与回读 preflight 沿用该来源，允许保 ID/text/order、改合法时间并重算自有语义 SHA 的初始输入跨过此门。 | Backend；仅 initial 来源比较；affected 合法 CTC 边界不能被误按 ASR 强制相等。 |
| B120-P02 | P2 / OPEN / SOURCE_STATIC | current_final_evidence_recovery.py `assert_correction_pair_writer` 224–233 默认 allow_new_assembly=None；actual 从原 observed text 变 None 时，`actual != observed[0] and actual != allow_new_assembly` 第二项为 false，未拒消失。normal verify/publish 默认调用也受此分支影响。 | Backend；用明确“没有授权新值”语义区分默认参数与实际 None，保原首 persist 显式允许新完整 body 的路径。 |
| B120-P03 | P2 / OPEN / SOURCE_STATIC | registered_alignment.py 793–794 正确要求推理 not_measured，却在 450–456 对最终 READY Alignment 作完整对象相等。Media38 prepare_v03_evidence 221–241 合法补独立 reference 后变 measured 并派生内容 SHA；Backend bundles.py 2434–2491 与 2538–2548 对 strict 独立测量正要求此状态。故保原预测边界的合法 measured 文档仍被 alignment_result_invalid/422 拒。 | Backend；比较原 CTC 不可变身份/边界/方法，合法 precision 派生保留原两 authority、完整来源/数学和记录 SHA 核验，不能让推理伪装 measured 或删除门。 |

三个原完整 Finding 在本过程目录，内含固定源完整路径/SHA、最小条件、调用行、影响及修复要求。本结论是源码中的可达条件，不是已运行 SQL、真实许可 Bundle 或 OS 复现。P02 也不宣称存在正常公开删除 assembly 的入口；它是保护 current/source 故障边界失效的精确条件。

## 有限源码支持与保留门

两 private grammar 与 canonical 原输入保留 strict / extra-forbid / secret 拒绝、完整 binding 与 own semantic hash。来源预核依赖实际同 preparation ASR/context、实际注册资格/route/文件身份；它们是 gate 调用实现，不是登记数据或运行资格已经可用的证明。初始与 affected 只使用唯一 registered request，原 failed units、主 command SHA 和原始 transcript/context 保留。affected 旧无效应 continuation 可附 companion，已有 child/Op/allocation 效应拒绝；原角色 exact 判定未放宽。

RegisteredOperationExecutor 312–325 在 prepare/claim 前对完整 intent 与 canonical request payload 作比较。原 executor 首先保存 dispatch intent，已有 settled 读原结果；非 prepared 拒重提交，异常后保 unknown。原 Engine prepare/claim 当前授权、暂停/cancel、route、fence、预算及共享账本代码不变；成功/失败只有真实可核成本才 settled，unknown 不释放预算也不自动 retry。

Worker allocate_output 493–533 只准 alignment-result/application/json，绑定原执行 inputs，事务前后真实源门；finish_output 542–572 只读原持久 allocation，READY 后禁止换 bytes。generic commit 拒该 JSON 当媒体 Asset；公开 complete_step 拒该 namespace。私有 alignment consumer 738–848 检查唯一成功 settled Op、原 generated allocation/candidate 全身份、真实文件 stat/size/SHA、严格 schema/完整原单位顺序、allowed-unit/音频时长和 not_measured；同 writer 重核 Op/allocation/source 后只以空 asset_ids 提交原 Step，回读必须是原 committed Step 内容。此处没有新 Asset、影子执行账本或 caller 指定成功 MethodEvidence。

registered_initial_alignment_method 387–413 先读实际 successful settled 结果和 committed Step，再从原登记 execution/resource、真实 Operation ID 与同音频 artifact 派生 MethodEvidence；expected methods 恰原 assembly methods 加唯一实际 CTC，重复 method 拒绝。该源级第九方法来源有支持；本轮没有真实 driver/native execution/result/原两 authority 运行，P01/P03 仍影响合法完整闭环。

原 B118-P01：`assert_current_correction_pair` 198–221 新共同比较能够拒原保存 assembly 与 READY report 不一致；persist/normal verify/current/continuation/selected child/publish 接线存在，并在短 writer 前后/verification token 使用原 snapshots。其稳定 source-present 比较缺失可标为 CLOSED_SOURCE_STATIC_ONLY；整个当前 pair/writer 完整目标保留 OPEN，尤其本版 P02 的 text→None 反例。没有任何 SQL/并发/重启/发布数据证明。

保护核：原 executor、public contracts、plan_repair_service 整件前后字节相同；实际索引内 12 个 cli/ 文件相同。Engine `_observe_operation`、observe_operation、原 prepare/claim writers、_complete_step/heartbeat/canonical/digest 等 AST 保持；Worker 仅 allocate/finish/通用 JSON commit 三方法改变。原 private strong service/thread/lease/held guard、原 Child/counter/预算与许可门保持相干调用。原 bundles 两 authority 和 200000us/full-unit N/nearest-rank P95 校验未改；MM05/precision null、真实独立来源及权限缺项不得自赋通过。

## 证据与未执行边界

InputBefore 原记录、InputBeforeSupplement、MediaPrecisionInputAddendum、InputAfter 与 CompleteDiffProtectionCheck/ProtectedBodiesAddendum 给出完整有限身份和原 diff。当前/基线/治理和必要停止补充 input 的末核无漂移；未遍扫 runtime 或环境。CompleteDiffProtectionCheck 中最初 `cli.py` 逻辑键不存在，保留原记录；精确 cli/12 路径另附，不伪装猜键命中。

原 97631d/1 是错误定位 Checks.json 根路径；bdccdc/0 的 InputBefore 大输出截断不能作全文读取证据；原 f56253 片段截断已以 9403f8 精确补齐。恢复后 d2e817 合并输出有截断，仅缺失的 Media 段以 266f3e/edcd1b 及原完整文件相干读补齐。209b59 的旧 rg 可执行路径已不存在，shell 同批退出0且保命令错误，随后改用只读 Select-String；它不是产品失败。原脚本所有结果和历史 Finding 不重写。abc120/0 是自有标准库身份/AST/diff分析，不是作者测试重跑。

实际兼容、原资源注册与 issuer/native/auth transport、有效 human/policy 审核、真实 CTC 推理/unknown 恢复、两 authority 与完整独立参考、SQL 原子/并发 writer、当前完整 Bundle、UI/API/MCP、三平台安装和作品看听均未执行。原 exhausted 目标、原红、拒补丁、其余 exact 角色缺口和 R1→连续 R2 总目标保持。
