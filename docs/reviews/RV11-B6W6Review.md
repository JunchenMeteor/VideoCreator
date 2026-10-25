# RV11：B6/W6 持久执行与媒体接缝有限静态复审

2026-10-08。永久独立评审；FINAL。本批静态读取和普通证据核对完成，发现 **RV11-P01（P2）恢复入口缺口**。未执行产品、测试、媒体解码、收费或凭证读取；不把 owner 结果或未来 T13 结果当独立验收。完整 Gate0、R1、连续 R2 均未获本报告通过。

## 固定身份与读取范围

仓库 AGENTS SHA `6de878f514b02788f8af5ba512f71c56bb053f6800d76cf19f3cdd955b7f6a0d`；RV11 卡 SHA `145f87b7f5d5df7a6b1bb5e5cc708874b020dab84691c14a20cb0e11c0454532`。ADR0009 SHA `885695657a68c00b1e5c331dff4136537aa3c34430265ba1cfe17d602cde0c9f`，只批准实验接口，未冻结技术或通过实现。

B6 正式 MD SHA `5a96c094ebd275dcc3f49401b08c074c611ab54ba72b8675170c79a28f0e115a`、JSON SHA `96aed973b06ed5eba377724ab0b7bb1703141b8e703c2164f3eb73bcb1626d7e`；W6 MD SHA `ee40ab1daa6d167741db5234927d68ef9080710d99073189719a73944975e122`、Snapshot SHA `9487cd7dc78385e703d16a6c51a5ffdbe720af5469b23605fc3cf14dd16ed232`；接口 SHA `a73d0921351f2863a5258ef979faa5191ec7591349c781fcbd0591bde0ecb311`。

B6 八源均与交接逐 hash 匹配；W6 十四源当前字节和 `W6/SourceFinal/{Workflows,Providers,Media}/` 十四份普通副本均匹配。语义审查聚焦下表十源，其余 W6 十二源仅核身份，不冒称重新语义审查历史 provider/协议。读取完毕的固定正文与身份保存在自身 `Review/RV11Snapshot.json`，SHA `ea8b7840fe671330a227fb2da0f6548409c91d795d36ad8271dd0978bfa01618`；后续报告只使用该固定快照，不读取并发新源。未读 I12 WIP、T13、私有 Cases、ValidationInstance 或 .ssh。

| 固定文件（均相对 repo） | SHA256 |
| --- | --- |
| services/engine/src/video_creator/domain/worker.py | 4ee8dbdf1d441f87939e5b19208aa33417d624498bea1bca7efb25e6c723ec19 |
| services/engine/src/video_creator/application/worker.py | 7c53bfd06bd4cf1a388a958783acda911b943e4fe9a2782012860bafaf7ace9f |
| services/engine/src/video_creator/application/engine.py | b7177032a8429b90dac457dc8b8adf465134d2e4deeeb34c8af4d4fdbcb6d233 |
| services/engine/src/video_creator/application/assets.py | 2ede5f08f96872bc7ecd29aed3515796313d764970947f0eeb9bd450f5e7951b |
| services/engine/src/video_creator/infrastructure/database.py | 08623e27f1165981b91781f11c28e8d20514751b8fc1bd405424f8bf9c5d8339 |
| services/engine/src/video_creator/api/app.py | 646041d7ead2b7bcdbcffa6aae8bb169e890dbd9ecd580f05cbe7e5e08e14217 |
| services/engine/src/video_creator/cli/main.py | 9976b43c110baebf0f621555ea3e3b2a4b546a62fdf2a506109d29baab7da21b |
| services/engine/migrations/0003_local_worker.sql | 15c03c77eef6e8c76cc0750d76a6a4b11769d4be88a5b3270183d446fef130a6 |
| services/engine/src/video_creator/workflows/local_render.py | 173c9a474821e87cb1ac19d8717b48a9b71a0417e3fa1e24983b37940be25581 |
| services/engine/src/video_creator/media/local_render.py | 8fa206e0940b2be35efaf0d1d900d4b0563ccbaf4078bcda85446a84e5987285 |

## RV11-P01：固定 Worker 无法进入 unknown 原 Operation 的核实阶段

**P2；OPEN；归属 Backend（租约/领取/核实权限）与 Agent/媒体（受控文件核实）。证据类型为固定源码静态路径，未由本评审或已纳入独立测试实跑硬 kill。**

触发：真实固定 driver 已 `claim_operation`，生成文件已完成精确 allocation 的 fsync/rename，进程在 `observe_operation(succeeded)` 落库前崩溃；或多文件生成只完成部分文件后崩溃。租约过期后必须保留 unknown，并仅依据持久归属、输入与真实文件解码核实，不能重交 render 或从目录扫描认领。这是 ADR0009“文件、未知受理和恢复”及下游硬 kill 窗口要求。

源码链：

1. `application/engine.py:209–219` 把过期 Run 的 `submitting` Operation 改成 `unknown`，Run 改成 `needs_reconciliation`，清持有人；此保存未知语义正确。
2. `application/worker.py:174–182` 调用 recover 后只查询 `r.status='queued'`，并只用默认 `acquire_run(... reconciliation=False)`。固定 CLI 没有核实选择入口；`--once` 无可领任务会退出，不能拿退出 0 推断该 Run 恢复完成。
3. W6 的真实完整文件核实在 `workflows/local_render.py:289–348`，依据原 reservations 检查完整文件、真实 decoder，再以原 Operation 的 `reconciliation=True` 观察成功。然而上述 Run 永远进不了本次 invocation/kickoff，因此这段分支不能解决该硬崩溃后恢复。
4. 不能仅把领取 SQL 放宽：`engine.py:73–80` 默认 `_lease` 不接受 `needs_reconciliation`；`worker.py:90/102` 的 bind 和 `engine.py:264–297` 的 begin_step/prepare 都采用默认权限；即使用既有 `acquire_run(reconciliation=True)` 领到核实租约，正常 Flow 在 plan/revision/Step 阶段亦会被挡住。需要独立受控核实阶段，而非将所有写权限一并放宽。

影响：不盲重交和费用真实性保住了，但完整受控文件或部分文件留下后，固定 CLI 缺少原 Operation 核实/继续端口；不能认定“文件未DB”及 unknown 的自动可恢复闭合。Operation 已成功结清、仅 Step/Flow 未完成的另一窗口会回到 queued，本项不否定那条正常恢复的静态设计，也不声称它已独立实测通过。

最小修订建议：由原后端 owner 明确固定核实领取/读取/观察权限；在允许新 Step/提交前，媒体只核原 binding/allocation/input/manifest 及真实字节/decoder，并对原 Operation 记录有证据的观察。完整文件可核实后回正常阶段；partial、缺失或损坏保持 needs_reconciliation，禁止清 unknown、重新 claim/render、扩大目录读取或重置预算。独立测试保留原源、真实 kill/原账本/文件/新进程与 render 次数，证明原 Operation 未重复提交；本评审不实现或代跑。

## 固定源码可支持的窄正向结论

- 唯一内部 v1 模型限制 workflow/outcome，无 Production/Bundle succeeded。Binding 限本 Production 的固定 request_revision、本人输入 Asset hash、资源 manifest hash；媒体不写业务 SQL、不接受模型 argv/filter/module。原 budget_group/费用能力不在本地 driver 中授权；本实验仅 credential-free owned_local、0 元。
- `worker.py:278–312` 在 decoder/对象复制之外单独开最终事务，重核当前 lease、Step input/fence、持久 allocation 和 owner，要求关联 Operation 全部 succeeded+settled，并确认每份提交 manifest 已记入 Operation。`assets.py:131–145` 与 `_complete_step` 同 connection，使 Asset+Step 事务回滚一致。decoder 耗时期间换 fence 的拒绝是 owner receipt 的实际机制证据，独立并发/kill 尚未在本批纳入。当前 W6 对提交文件与完整 reservations 逐项相等；通用后端仅作 manifest 成员包含检查，不因此外推任意新 driver 的完整输出契约已经验收。
- `finish_output` 只读精确 allocation complete 路径，partial 不被当成功；文件/Objects 与 DB 两阶段保留可核实孤立物。对象复制后 hash 复核，输入/结果路径同时受 owner、Production scope 与真实对象 hash 检查。没有凭 checkpoint 自动授权提交或改费用。
- Flow 每次先读业务 Step/Revision/Decision 并检查 binding；成功 Step 复用对象，业务成功后再 save_state。恢复中的 `shot_asset_ids` 由本次业务读取逐镜重建，旧 Flow 状态不直接授予 Step/Operation 写权。但 RV11-P01 限制了 unknown 状态入口，不能由 checkpoint 存在推断全部恢复完成。
- quality revision 持久后 wait_for_review 清 Run lease/worker，返回挂起而非线程等人；固定 revision/同键异输入/旧版本以及最多轮次沿域守卫。同 Production feedback 新 Run，原计费/保留计数不重置；前两镜按旧 Step input/Asset scope 复用，第三镜与合成各新 Operation。
- approve 后保存 `local-review-approved` Step；固定调度明确跳过该 succeeded Step，防止 release→queued 热循环，仍不写 Production succeeded。unattended 分支仅保存本地策略与 bundle_pending，并非无人模型制作/完整策略质量验收。
- Presence 注册真实当前 PID，heartbeat 仅原 worker_id/PID，state/TTL/version 供 API 动态 health 读取；静态 True 参数不能冒充连接。实际存活/失联的瞬时、硬崩溃和连续 heartbeat 仍需独立 OS 证据，当前 TTL 不是 OS 进程监督器。线程取消有界依赖固定 driver 配合，不是任意 Python 沙箱。
- schema3 三表不重建旧费用/Operation，迁移 writer 事务核版本，旧schema2拒3的 owner机制单列。数据兼容备份、真实并发迁移和回滚尚未据此验收。

## owner 证据核对及不可继承的范围

B6 `B6DeveloperReceipt.json` SHA `3eff02210fd298e07ff8cef90ddcb38362aaf68e44deb719f664bd4bfd694d8c`，15 个 owner case，真实文件/FFmpeg/decoder/事务与 fence；Operation/创意/短 callback 明确 synthetic，expiry 注入 clock，并不是 W6 CLI、真实15秒失联、完整 kill 矩阵或独立验收。首次只读 fd fsync 红由 `B6FirstProbeFailure.md` SHA `211472c57ca546211f7b483a6dbe30c7eda071efb43980ca9ab9976a2f0d8629` 留存；provisional/最终 receipt 共路径被覆盖，旧收据缺口诚实保留，不能重构早期 receipt 或把它当最终冻结。

W6 四个 CLI 原 CommandReceipt 及 stdout/stderr 均实际 hash 匹配 snapshot；各 56 scope 前后差异与声明范围外变化皆空。分层如下，首红未洗掉：

| owner 命令目录 | 收据 SHA | exit / elapsed | Flow 源身份 |
| --- | --- | --- | --- |
| InitialWorkerCommand | c547a774fbb87760098b44b33e87e1e087276f78cc7065ea09ef3e0814a96bc7 | 1 / 16.466s | 951272…原 dict→canonical AttributeError |
| InitialWorkerAfterJsonFix | 49c56ca97e62c9732c01d606bd283281566558b1580851b3112a2d21424fda13 | 0 / 22.079s | 173c9a…最终候选 |
| FeedbackWorkerCommand | 6ba0c34305039dcb55eed53c91149b3440f832c541a0f9269c488db189b35ab9 | 0 / 18.271s | 173c9a…最终候选 |
| ApprovalResumeWorkerCommand | 1cc7ca56978f55354f452e4f3e43b8c2f3022e0dcbfb89ebfa13a1c1a56840ea | 0 / 9.873s | 173c9a…最终候选 |

批准恢复原 stdout 有真实加载 Flow UUID 的日志，不以日志替代独立 crash/checkpoint 验收。snapshot 记录初5成功 Step/4结清 Operation/6 Asset；反馈 Operation4→6、Asset6→9；批准恢复维持6/9；前两镜 Asset ID/input相同且新Operation0，第三镜换Asset/input且新Operation1。该意见与批准由 owner 在真实域接口注入，是机制实验。

实际读取四份公开 Output 字节核 hash/size：InitialVideo `8f15b2…`/205896、FeedbackVideo `cd7608…`/208876，两份 Mixed.wav 同 `28cd40…`/1920078，均与登记 snapshot 一致。10秒、720×1280、有声和decoded来自 owner 实际 probe；本评审没有重解码、连续播放、观看帧或听审。已有 SAPI WAV 分段+三色板/中文实验标签是模板媒体，不是模型写剧本/动画/新旁白，也不代表语义时码对齐、自然语言通用指导或音视频质量通过。

固定指导只接受“表达更年轻，只修改第三镜头”，其他意见422/local_revision_unsupported。缺通用模型协作、完整 Bundle/RAG/文本/独立旁白等交付、新后端完整入口与真实父/API断开后后台持续、双Worker/硬kill四窗口/失fence取消/资源失败/unknown核实、macOS/Linux/安装/商业均保留未测或未实现。I12/T13 后续证据必须另批绑定源身份，不能倒填本报告。R1 独立验收后连续 R2 总目标不变。

## 交接

RV11-P01 交 Backend/AgentMedia，经统筹维护冻结与归属；本评审不修实现、不改标准、不自兼验收。阶段读写终态；测试运行0、产品操作0、费用0、key读取0。正式报告与自身 RV11Handoff 已保存后释放本阶段，不等待 T13 或 I12。
