# RV13：T14 分阶段恢复判据的独立版本评审

2026-10-08，永久独立评审，FINAL。**不批准当前标准+拟执行夹具整包进入运行。** K/R/N 与显式70秒Worker/55秒quality窗口的版本化方向成立，但当前实际断言存在两处不能区分错误关联的证据缺口（RV13-P01/P02，P2，TestDevelopment归属）。修订须新固定hash再审，不由评审代改。

这是拟执行标准的静态审批结果，不是产品实跑失败，也不否定架构裁定。RV11-P01仍P2 OPEN；本轮没有产品/测试/AST/解码/看听/费用/key操作，不签Gate0/R1/R2。仅只读固定文档、拟执行测试/夹具和必要固定domain/consumer签名；没有读取B7/W7实现、私有实例或I14 WIP。

## 固定依据与审批单位

AGENTS SHA `6de878f514b02788f8af5ba512f71c56bb053f6800d76cf19f3cdd955b7f6a0d`；RV13卡 `25669fcd4e361e4725b3666221564aaf5ae96642a49bb6e4ef448b9da83bd58d`。

A8 ADR0011 `02f1dfb8333c4529fee34fb74c8f560f2aca972651502206dadad85d2a14b174`、A8Handoff JSON `2715861139e085b5574570ba835ab75dcdbcbb551207796c10337d56fd5af1b0`；实际T14CriteriaHandoff JSON `e7edb3e75564149a070408a24b337c357bde9cc3c1d0cb868a780a9af13b0dae`、MD `aea2ff5bd2ef2eefc5f82bd0e0af5e465bc431bda58c1b02f349e9bc65ac05f7`均已核hash。必要domain=`7aa24bd8f0e8555d408f59b7b42ff97f8d60841f7fff09910867fc6db43a10cc`、consumer=`f033d9ea23fd14adae364cbbbc2b97a7bdd6eb6d54595b4a949d6b848b07c7ba`；finish_reconciliation(invocation)和独立ReconciliationInvocation/Outcome与包装签名一致，不借这些接口方向判实现通过。

以下是本次**不批准进入运行的具体版本单位**；其中不涉及问题的依赖未发现本批阻断，但不构成独立可运行批准。标准文本的规范方向可认可，因其绑定的实际夹具未完整实现这些判据，整包执行授权不批准。

| 文件（repo相对路径，manifest例外） | 固定 SHA256 |
| --- | --- |
| docs/acceptance/criteria/gate0-local-recovery-phased-evidence-v1.json | 4e6c10f84f689ac170717ee31ca601703c69dce42765af216879262c2fc4f18a |
| docs/acceptance/criteria/gate0-local-recovery-phased-evidence-v1.md | b732ecfe21e1d7571c19c8e92af92df826427561b5dbf5bfa75a40ea9367f3ce |
| TestDevelopment/T14PhasedFixtureVersions.json（Codex过程manifest） | 1b752948f6ae16f380cd42f497bee80f3174c4def060dbe94716325f48e76447 |
| tests/gate0/t14_process_helpers.py | fcfaff96a9bbd9d35d39ad99f7419a3f823af28819a774883d4b61dd119b9db7 |
| tests/gate0/t14_evidence.py | c91f05efdd92db5fb4a283c7305c4d735adc6aef84012801ee4b9a36a411bb9d |
| tests/gate0/t14_phased_assertions.py | 49a5835fa9ec2ef01625bad9a3ae81afa17a7ab1d65a08758ac3108c13251c51 |
| tests/gate0/test_t14_recovery_phased.py | 1726d71b6631cb4771ad40d3f457dffc0d51eeb61bd12feb115e0ae2acc80eef |
| tests/gate0/T14Fixture/PhasedTrace.py | 77250b41dd099e54a32c2b331d4aee947e78ff2dcd7135675209220d560672d5 |
| tests/gate0/T14Fixture/PhasedWorker.py | bf2fcffbff702746058032b8755991dabe02740eaee77b382f4933ad97c6fb60 |
| tests/gate0/T14Fixture/SuccessLatch.py | 5a7f33533e9be3013064d40fff1214be03d5b02661d5c66a839dcb688cca0a56 |
| tests/gate0/T13Fixture/OwnedSibling.py | e8db5d8c8f35e96ce139644268ccb8449c9c4f70482dc487de583ce8d04556ab |
| tools/testing/run_recorded.py | 5094d5829d7e1a76540334d1f48763d18836c581b907ac2af89124e8a5bfdbba |

九源码hash/字节与manifest一致，UTF8/LF无BOM；“AST已检查”是测试owner交接事实，本评审只读，不重新执行AST。固定全文与身份已保存 `Review/RV13Snapshot.json`，SHA `ca1501c3862a26713a52a7c5718d049b0dbeb283b000004c0de25fff2ee5e3c4`，本报告仅使用该快照，读取终态后不追当前新版本。

## RV13-P01：R解码事件未绑定原文件

**P2，OPEN，TestDevelopment；阻断此夹具版本审批。静态可区分性缺口，未运行合成或真实反例。**

规范R-01/R-03要求原allocation的完整文件真实解码后才settled，decoder与render分开。实际 `PhasedTrace.py:40–44` 正确包装真正原renderer/probe，`observed:29–35` 调原方法、失败重抛，不替结果；但probe事件只保存`decode_requested`和返回的MediaProbe，没有保存真正输入path/hash/size及目标allocation关联。`t14_phased_assertions.py:49`只要求任何`decode_returned`事件的decoded=True。

因此若核实阶段实际解码的是另一合法输入（例如已授权音频或其他同规格视频），同时原Operation被写入原文件manifest，这个断言仍能满足。Rfile不变、manifest包含K的hash不能证明该次decoder处理了它。该逻辑反例只依据条件推演，不声称当前B7/W7实际这样执行。

最小改法：原probe调用前后记录真实受控输入的规范化path、实际hash/size、decode_requested、返回probe及可关联调用身份；R断言绑定K中唯一attempt/staging的精确完整文件及Operation manifest，核decoded=True与预期视频/时长/画幅/音频。保留真实原调用与异常，不能为了记录主动另跑解码、替换结果、修改业务SQL或把version/probe误记render。失败或文件变化须保原red。由测试owner修Trace/断言，重固定相关JSON/manifest/Handoff hash。

## RV13-P02：N媒体/Step/Asset/Flow关联未逐项断言

**P2，OPEN，TestDevelopment；阻断此拟case/断言版本审批。静态判据覆盖不足，未运行实际坏关联。**

N-02与ADR0011明确要求Operation输出manifest、allocation、实际Asset、Step结果和Flow对应。实际 `assert_N:54–73`保5Step/4Op/5allocation按step分组、原Op观察不覆盖、原身份/文件、normalfence>Rfence；`74–77`仅核各Step资产数量和ID存在。main `197–219`对N全部Asset做真字节副本独立decoder并核各Step引用的时长/流/画幅；`191`只核Flow行数≥6和同UUID集合。

这些条件不能排除同规格资产的错误绑定。例如shot2和shot3均3秒，交换两Step的asset refs或让它们共用一份3秒视频，剩余Asset仍存在、Op/allocation按step计数不变、decoder规格仍满足；错误的Flow ordered shot/output refs也不被UUID/行数检查捕获。原shot1保护保持并不能覆盖另外两镜及compose关联。此推演没有修改测试或生产、没有执行伪通过。

最小改法：按run/step/output_key和原有序输出全集把Operation.generated_files逐项对到allocation attempt/staging、staging.asset_id、Asset的真实hash/size/MIME/source/rights，再对Step有序asset_ids及其result manifest；要求每个预期allocation恰有对应结果，避免一份Asset多处冒充或孤立输出凑数量。实际Flow checkpoint的run_id/binding、plan revision及有序shot/output asset refs要与本次真实Step结果相符。只使用已有内部/持久字段，不新增生产测试API；允许ready→imported、Asset登记与合法新Step fence，不把这些正常变化硬固定。独立decoder继续保留，不能用metadata关联代替解码。

## 已符合方向的实际静态内容

- 原03966测试及完整副本hash保持 `03966d95f336c6f14cff14ac7653aaaba26317a9f9eb1963d371cb7c40bf2a52`；原kill JUnit `8a0b59334e1e82b7a9499388b810b900151e4c7228f118074f9ff118f119af91`、RV12报告 `977068677151216997103a649c6527f8da13816fcab00129983f8a71fdab2672`保持。原最终全Run1/1与最终完整quality矛盾是真实固定流程冲突，不是根据未来实现降门槛；规范将1/1移至R并保原目标唯一，N恢复完整5Step/4Op/5allocation。4/5仅本三镜profile，不泛化供应商。
- K保存原render_shot真实一次、1 submitting/unsettled Op/1 ready allocation、无partial、原对象字节与Flow，再即时持久PID/Creation/树和真实kill/墙钟过期。R全部render及allocate/Asset/Step新增调用为0，保存queued/workerNULL/lease0/idle、原allocation_fence、binding/已有Step/Asset/Flow不变；N保原Op identity/dedupe/manifest、文件path/hash/size/mtime不变，允许正常新fence下后续产物增加。
- R闩 `PhasedTrace.py:62–76`先真实finish_reconciliation成功返回，才持久闩并等待有界ReleaseLatch；不替原返回、不提前normal、不直接写SQL/status或接管heartbeat。R的真实后端queued/撤lease事实在闩内读取；N freshfence与quality不是用退出0代替。具体finish权限实现不在本轮审批范围。
- renderer与decoder以不同事件记录；原renderer调用、异常传播、0收费本地路线与独立后续decoder方向正确。当前缺口是事件与数据关联，不要求重写编排或降低质量目标。
- criteria JSON显式保存旧12秒及原红；新K/RN Worker70秒、N quality55秒、各闩30秒、墙钟lease等待40秒、natural wait85秒与拟case固定数值一致。是新的有界实验窗口，不是旧字面测试原样全绿，也不定义生产SLA。闩期间采证超过30秒应真实失败/清理，不放宽为无限等待。
- Journal每次fsync/rename即时存事件与hash前链；自有PID/Creation树、真实非空HTTP兄弟、元数据/端口终态和force/normal分列方向改善了T13迟落盘缺口。需实跑确认CIM/时序、异常清理、子进程终态；静态阅读不代表这些实际通过。run_recorded wrapper只记真实退出/前后scope，不推Gate或虚构provider调用次数。

## 下游与剩余边界

测试owner仅修上述观测/关联断言及版本绑定，原标准要求不降、旧失败不覆盖。新标准/manifest/实际拟执行文件hash固定后回RV作有限复审；最终B7/W7源码/资源冻结、统筹明确准launch仍是后续运行条件，不能拿本报告或A8设计裁定替代。实现owner不因本测试审批缺口被要求迎合错误计数或额外造测试端口。

保留partial/多输出/缺损/篡改、旧fence、取消不复活、同证据幂等/异证据冲突、slot公平性、Step已成功未Flow等独立样本，以及真实模型创作/完整Bundle/RAG/Portal/MCP/三OS/安装/商业/R1→R2未完成。RV11-P01继续OPEN；后续实际新源+T14结果及独立AV才支持关闭。本阶段全部读取终态，费用key/产品测试0，仅review白名单写入，正式FINAL释放，不等I14或测试运行。
