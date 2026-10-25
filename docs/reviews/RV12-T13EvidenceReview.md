# RV12：T13 固定故障证据有限复审

2026-10-08，永久独立评审，FINAL。**T13-KILL-01 支持 RV11-P01（P2）在一个真实 kill 窗口的产品恢复反例；保持 OPEN，未修复。** 五批结果为四红、一绿，三轮夹具/观察错误、补充解码和产品恢复红分别保留。未关闭 P01，未判全 T13、Gate0、R1 或 R2 通过。

评审只读已终态证据和历史固定副本；没有执行产品/测试/解码、看帧/听审、收费、读 key、修改实现/测试/标准/ACL，未读取未来当前生产源或 I13 WIP。完整目标仍为 Gate0 → R1 独立验收 → 连续完整 R2。

## 身份与核验范围

仓库 AGENTS SHA `6de878f514b02788f8af5ba512f71c56bb053f6800d76cf19f3cdd955b7f6a0d`；RV12 卡 SHA `f440562784516bca90ada1efa3f7f70f7711903f91bf5820670746dac39c30d4`。

- 正式 T13 MD：`7300da3446c48e3307b2896e8f4047867f7e5fbea062080b7d9a36587c7b7b3f`。
- 正式 T13 JSON：`3a56a7cb3405c1428dfc33ec854e0a5ec643025065c910627076030243c28367`。
- canonical 普通副本清单 `TestDevelopment/T13ReviewCopiesManifest.json`：`3fff4f987f94536bfb34e87148f3a8680c739c95fe6e29ecc231a623afa9ec71`。任务中的 `ReviewHandoff/T13EvidenceCopyManifest.json` 别名不存在，采用正式 Handoff 实际引用的同 hash 路径，没有改权限。
- 109 普通副本逐 hash/size 全部匹配各自声明 original/copy SHA；实际读的是普通副本，未逐个打开私有 original。核对记录 `Review/RV12CopyChecks.json`：`edb5b28f3a0360671e99b7abff1d171ebf513ef030f3be3334da3fbb2c42ce53`。
- T13 22 consumed-source 副本 SHA 同 before/after；五个命令的22固定生产输入均匹配，未用后续修源冒充原身份。RV11 十个语义源与 T13 历史副本相同。关键历史 application.worker=`7c53bfd06bd4cf1a388a958783acda911b943e4fe9a2782012860bafaf7ace9f`、engine=`b7177032a8429b90dac457dc8b8adf465134d2e4deeeb34c8af4d4fdbcb6d233`、workflow.local_render=`173c9a474821e87cb1ac19d8717b48a9b71a0417e3fa1e24983b37940be25581`、media.local_render=`8fa206e0940b2be35efaf0d1d900d4b0563ccbaf4078bcda85446a84e5987285`。

固定评审材料已保存 `Review/RV12Snapshot.json`，SHA `0e4f4ee0942ebf853706171aafd0e7b7132023ef21354cc4c34a921aaa43539d`。报告只用该快照，不再读取并发生产源。

## 五批真实结果与时间分层

实际读取五份 CommandReceipt、JUnit/原失败，以及必要 child/业务观察/测试闩副本。每批1 case，errors/skip 均0；源码前后 map 计算差异0，声明范围外变化0。范围是本批明确依赖，不能外推所有 OS/stdlib/传递二进制。

| 批 | exit / pass / fail | JUnit case / suite 秒 | 原命令墙钟秒 | scope | 分类 |
| --- | --- | --- | --- | --- | --- |
| LiveRoundOne | 1 / 0 / 1 | 6.530 / 7.121 | 13.279860 | 912 | 自有 child 缺 USERPROFILE，Chroma Path.home 导入失败 |
| LiveRoundTwo | 1 / 0 / 1 | 6.292 / 6.822 | 23.978207 | 2866 | child home 的 AppData 目录缺失，appdirs KnownFolder 失败 |
| LiveRoundThree | 1 / 0 / 1 | 97.999 / 98.541 | 103.405230 | 3162 | observer 把 Objects 交给 Staging 限定 decoder，被正确403拒绝 |
| ObjectObservationBatch | 0 / 1 / 0 | 5.562 / 5.738 | 7.886980 | 3163 | 原失败之后独立只读补观察/受控字节副本解码 |
| KillWindowRoundOne | 1 / 0 / 1 | 62.791 / 63.411 | 65.607132 | 3166 | 真实 kill 后原完整文件无法自动核实/推进 |

原会话71304/8391/16687/12328及同步观察chunk d268b9 的终态由正式交接登记；本评审核终态文件，不操作他人的历史 handle 或把 launch 当完成。suite/case 时间不是 wrapper 全墙钟；全部失败原文与原断言保留，补批通过没有改原整批红。

五份 receipt SHA，依表顺序：`13be2d9d17c015e464f0a528c8fe1e75e54f2359ffaafcbdd8abac669b507e80`、`b26d4e4b4c827f2e0701323800c9b304cf825c4a1511361f7e7d7357ebc6a36b`、`4c408d3137679ec3b7cc618f9f10ff4fe29eabdbd7966eb4257fd32a9d255b9c`、`5202d1531b15b49b40a3f8101884869c04247e0f463d6435e977faf5e8658c01`、`3db08cdc8388e956b846c7189a2a321eb2a1ef32200a44e961f8e821aa0c8492`。

## RV11-P01：真实反例支持范围

**P2，OPEN，归属 Backend + Agent/媒体，经统筹/A7交接。新增证据级别：独立测试真实 Windows OS kill、业务 DB/文件与真实墙钟租约过期；没有声称评审自己重跑。**

1. 历史测试 `test_t13_kill_window.py` SHA `03966d95f336c6f14cff14ac7653aaaba26317a9f9eb1963d371cb7c40bf2a52`；`CrashLatch.py` SHA `a784c6423b618c254c4081df87165f53ad5f3feec80c0452b542a425d98fc4be`。闩只包目标 Run 的真实 `finish_output` 成功返回：先调用原方法，再写真实成功闩并阻塞；没有替换结果、伪 Asset/checkpoint、SQL补业务、费用调用或改 clock。LatchWorker 调真实 B6 CLI，限定70秒；这是受控故障点，不能扩为任意指令崩溃或未实施的 commit_generated_step 闩。
2. 原 Run=`run-ac5a60c533d94be6994e7656e1765e3d`；唯一 Operation=`operation-2f58380f6a01458a8ad6ae080d2d744a`。杀前 local-shot-1 running，Op submitting/settled0/observation null；唯一 allocation 的 staging ready、无 asset_id、无 partial，只有原输入音频 Asset。真实已完成文件91883bytes，SHA `341e80fd13c29157bf8f33392351127c350c0ea4f91d4d32e0d23db7803e2776`。
3. 捕获旧树 root52412，真实 Worker PID17484、parent52412、Creation `2026-10-08T01:58:02.7366360Z`。闩 PID与树/Creation核对；helper force_owned 再查 root PID/Creation 才 taskkill /T /F。实际 tool0、旧进程exit1、捕获旧树随后缺失。此是自有测试故障清理，不能称优雅退出或生产监督器通过。
4. 真实 lease_until=`1791424722919923`µs；wall before=`1791424696111425`、after=`1791424723109383`µs，实际等待26.997958秒，after确实越过租约约0.189460秒。没有注入 clock 或直接改业务状态。
5. 替换进程为原生固定 Worker CLI，`--max-seconds 12` 且没有 `--once`；root49288，真实 Worker PID36952、Creation `2026-10-08T01:58:43.1326710Z`，属于新捕获树，持久新 presence idle。自然窗口退出0，捕获新树消失；12秒是 Worker配置运行窗口，包含导入的全进程墙钟不冒称精确12秒。
6. 替换结束后 Run仍 needs_reconciliation、worker=null/lease0、fence与attempt仍1；同唯一 Operation unknown/settled0/observation null，唯一 allocation身份未变，仍只有原音频Asset。完整文件 path/hash/size/mtime_ns全部等同杀前。原断言 `waiting_user` 在第48行真实失败；JUnit SHA `8a0b59334e1e82b7a9499388b810b900151e4c7228f118074f9ff118f119af91`，原业务 Receipt SHA `cfe11b5993f8ee04f41ade6895f024b19adad917395acd43121e4228e14c9a3c`。
7. 受保护真HTTP sibling PID50300/Creation `2026-10-08T01:58:02.1432340Z` 前后相同，响应200，随后正常exit0/remaining空。资源manifest、授权音频、PowerShell/taskkill和FFmpeg等14项 before/after/final一致。未新增Operation/allocation，原文件未改写，结合旧固定调度可支持该实例没有重做的观察；不能升级成所有外部供应商调用审计。

该现象与 RV11 固定源码链一致：recover 把 submitting保存为unknown/Run needs_reconciliation，invocation只领queued，W6核实分支无法执行。**退出0只证明替换CLI自然结束，不证明作品恢复成功。** 修复不能擦unknown、重render、扩大路径/预算或只放宽SQL；需原Operation受控核实领取/读取/观察，再恢复正常Step阶段。修后原断言及不重交/文件身份须新冻结批复验，本报告没有读取B7/W7或预判修后结果。

本次仅证实成功 `finish_output` 后、Operation成功观察未持久的一个窗口；没有证明 partial/坏媒体、Step已提交未Flow、失fence最终提交、HTTP受理后丢响应等其他矩阵。

## LiveRoundThree 与补观察的可支持边界

原 test 历史副本中，在第48行 decoder403之前已经依序执行：第一Run审核等待且释放槽；同一个非once Worker处理HTTP第二Run；第二Run执行中API正常exit0、TCP关闭与捕获API树缺失；Worker仍活并PID/Creation一致；第二Run审核等待且心跳增加；每Run5成功Step/4结清0元Operation；各Run真实Flow UUID检查点≥6。原JUnit到后面403失败支持这些先行断言已执行，但原 Receipt 的 facts.update 位于第52行，未执行到，故中间Creation/heartbeat/两Run时序没有逐项原raw落盘。

这是明确证据缺口：不把源码断言或后来的快照当原创建收据，不宣原live整批绿，不把该测试父直接持API/Worker外推成I12/I13 Node监督器或生产后台App通过。后续补测应即时保存中间身份/状态，再继续有界观察，保留原失败。

独立 post-run receipt SHA `9590033f434afc9c549917b255928d62ed15d520dbf470f5ef9e577af655eee7`：只读原 DB，两个 Run waiting_user且worker=null/lease0、10Step succeeded、8Op succeeded+settled1+0元、11Asset、presence stopped/expiry0。11份对象按登记SHA原字节复制到补观察自身受控Staging，真实decoder全部通过；原DB before/after SHA `ccd4ad3e9551570dee565ac6b4dcfef38b879ac63bfc366bc5a3d9cab1dde45e` 相同，原对象/资源亦保持。记录三原child exit0、roots加presence PID `[33908,16028,26412,53852]` 在补观察时缺失、API49885 TCP不可连接。这只支持补观察时的持久结果/解码/清理，不倒填早期创建身份或连续看听。

## 未测与交接

保留正式T13列出的：同实例第二Worker真实409、Step后未Flow kill、直接stale-fence生成提交、真实TTL失联HTTP边界、未知HTTP上游接缝、partial/未结清/坏媒体/越scope/binding反向、旧/重复/异输入审核及第三镜反馈独立保留、新监督器完整入口、Windows安装器/macOS/Linux、真正父硬崩溃/JobObject。模板与旧授权SAPI音频不代表新模型创作、自然语言通用指导或质量验收；完整Bundle导出/引用/RAG对齐、Portal/MCP、R1独立完成和R2商业仍未完成。

RV11-P01保持P2 OPEN；真实反例交原 Backend/Agent媒体 owner修，测试独立固定批验证，RV/AV分别评审验收。本有限阶段FINAL，全部读取终态、无live；评审测试运行0、产品操作0、解码/看听0、费用0、key0、代码/测试/标准改动0。只写docs/reviews及本人Review，不等待B7/W7或T14。
