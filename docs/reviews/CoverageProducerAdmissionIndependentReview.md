# ADR0068 Coverage Producer Admission 独立设计评审

结论：**DESIGN_REVIEW_FINAL；三个 P2／OPEN_DESIGN，归 Architecture。完整实施合同仍 NOT_READY，实际 producer、角色资格、资源、安装和运行均未通过本评审。** 本报告只裁定停止合同与实际停止 caller 的对应关系，不修改合同、不批准实现或应用。原 QECP-P01、其他实现和运行缺口保持原状态。

## 固定输入与实际读取

过程根为 `G:/开发测试/Codex/VideoCreatorImplementation/Review/CoverageProducerAdmissionIndependentReview/`。先完整读取工作区、仓库规则及本轮任务卡，再读取正式 Handoff、Delta、Impact、Interfaces、Snapshot，完整逐行读取 ADR0068 的 183 行；对三项接缝读取实际停止 caller、原 TrustAdmission/consumer 完整正文和相干 coverage、capture、原0066条款。没有把作者的布尔结论作为独立结论。

任务卡为 `G:/开发测试/Projects/VideoCreator/docs/task-board/CoverageProducerAdmissionIndependentReview.md`，4681B／SHA256 `1b6e145f2223b08ec37b886d8df3b31e3521425dbf56364ec3461e4f43dda8bc`。正式 Architecture 根为 `G:/开发测试/Codex/VideoCreatorImplementation/Architecture/CoverageProducerAdmissionContract/`。

| 原停止输入 | 完整 SHA256 |
| --- | --- |
| `Ordinary/ADR0068.md`，35781B，与仓库原决定同字节 | `08d067c3d842699c64f5e5633a79e11e44e7d8c3bb2f6921a212a78cebe8224f` |
| `Handoff.md`，1905B | `4c120d5f607b237dfeba756c978eab966ea501d9c264be1aed98ee9c454f76db` |
| `Handoff.json`，4701B | `766b9d1bec7fe43b9032b78214fb370501e567bee65b2dde7ce8082cb138e577` |
| `Snapshot.json`，3203B | `818a34f976beb52166519533eecba280a500e13ab1e244ecf09a31e42f70df96` |
| `OrdinaryIndex.json`，14824B | `dcc34f3d809279f49c805e575009a32df099532e2fddd167307825ab9639a43f` |
| `InputPins.json`，14487B | `862256a59cfa621ef156b7e967aae87fe01636c56bd766bd9f2eba83f0ad8cd7` |
| `ContractDelta.md`，1373B | `0e0b87b36e1eddaf230441434088350e734dae8d11973816f81a8d86728dd638` |
| `Impact.md`，1211B | `6d34640285f6aeb7519ecfc85a0863df52a38bcff33819ed5fffb7d88add250a` |
| `Interfaces.md`，2058B | `b6ab9f78c480d4b206ce4e55fb2267419b001656eb67add89081b890b8000577` |

独立身份核对覆盖 25 个 indexed ordinary、24 个原停止输入、10 个正式交接输入、当前 Review 卡、原 ADR0068、一个由停止137索引精确定位的必要 capture caller，共 **62 条唯一实际路径**。25 个普通件均核实际大小/SHA，不能把这个身份数量称为25个源码全文业务通过。必要语义审读包含本合同全文和上述 caller/body；原137完整源码/diff、0066/0067既有独评只作为已停止同字节上下文，本窗没有重复扫描依赖或将其既有结论升级为运行事实。

`InputBefore.json` SHA256 `c1287f7e032442c7eb6020e209c870fd9053cda2f784160320cb8b3d09415e86`；末核 `InputAfter.json` SHA256 `3b9880333f833aef6aac35d03e4fb104b23d03e55272a476df2904c89efdaaa0`，62/62 大小和SHA一致，`differences=[]`。原件和 ordinary 两侧均属于已停止输入；没有读 source_path 热生产正文、后继 Backend QECP 修复或新的 Integration 候选。所有输入逐路径身份保存在这两件内。

## CPAI-P01：执行前来源能力和事后报告证明缺少独立接线

**P2／OPEN_DESIGN／Architecture**，实施涉及原 Backend、Integration、Test。

0068 第26行允许 suite/check 由同一 Test 工作方完成，但43–47行的准入正文只有一个 exact role。112–114行 `read_admitted_coverage_producer(... role, binding, report_ref, at_us, usage)` 要求已完成报告及其3.2工作证明、完整 report/work 闭包才注册来源。102行又要求 check 的 `actual_case_runs` 来自真实原 capture。报告来源门定义充分不等于执行前工作能力入口已定义。

真实停止 caller 为 `G:/开发测试/Codex/VideoCreatorImplementation/Backend/DiagnosticResourceCompletionImplementation/SourceProposalWithExecutionCompanions/PartialSourceStageOne/SourceCopies/services/engine/src/video_creator/application/qualification_execution_capture.py`，21541B／SHA256 `20d4bb03bb2edb70c3fba2437d6347a73c329fce342c99c1fd27c8b6a25f8df3`。`begin_capture` 105–157 行在 case 执行前启动，127行把 `suite.producer_ref` 按 `role='check'` 送来源门，130行继续把这个 ref 写入 execution header。

合法的单职责 suite 资格S和 check 资格C，不会使 S 同时具有 check role；保持127行必然角色不匹配。仅为该调用增加112行新参数，也要求尚未产生的 check/observation/work proof，形成前置工作必须先有事后证明的启动环。不能以未来ref、预生成pass、借别次proof或双role解释避开。0068 的102行和新reader尚未为这个真实 caller 提供确定的合法转换。

Architecture 应明确：真实已准入 check 原source在原资源许可、同Engine/Bundle、lease/thread、有限attempt门内如何注册执行前成员；该成员如何进入 `begin_capture`，header的check producer来自C、suite正文仍来自S；完成后如何取得原件和逐ref工作证明供事后消费。这个前置成员不能自行签资源资格，不能用source标签、泛JSON、未来报告或Infrastructure key handle替代。具体 actual caller、失效及 writer 关系必须固定后才交实施者。

对应冻结早单 `Finding-CPAI-P01.md` SHA256 `cbdaf084d918eeab3013b7f0d9b8a0aa40680690b0c63bd666f45590d1198ab6`。后继独立验证需求是两合法职责能启动真实有限工作、wrong-suite-role拒、结果尚不存在时不要求未来proof、实际失败/unknown不签pass，同时原限次、费用和current不放宽。此处没有执行反例或证明实际 Pydantic/工作运行失败。

## CPAI-P02：每个 observation 的工作证明缺少唯一完整父投影

**P2／OPEN_DESIGN／Architecture**；下游原 Backend/Integration 同源实现。

0068 第47行允许 check-report、check-observation 和七伴件格式；57–63行要求 proof 自己的 exact `report_ref`，check 的 `check_report_refs` 必须为空；66行唯一 check work 却要求完整 Binding 的 observation/companion、case closure SHA及实际原完整 `CheckSection` canonical SHA。120行另明确每个 observation 单独按自己的 ref 核来源，不得用一份 check proof覆盖其它文件名。

原严格类型位于 `G:/开发测试/Codex/VideoCreatorImplementation/Architecture/CoverageProducerAdmissionContract/Ordinary/19-diagnostic_resource_coverage.py`，11784B／SHA256 `84f9042301940f234e37164570eb5cb08c6d874377c8b7a6c69e8427ce03bf99`。`CheckSectionV1` 92–99行有 binding/results；`ResourceCheckReportV1` 244–247行有 suite_ref/coverage；`ResourceCheckObservationV1` 156–178行只含单case原观察，没有完整 CheckSection、suite_ref 或父 check-report ref。

实际停止 consumer 在同根 `Ordinary/21-qualification_coverage.py`，22594B／SHA256 `309701109142b8d3e1bb8c8099197da4b616b4c90f3e37310e58a32cf9b172e6`：298–302行 check-report 和315–321行单observation是不同ref的来源消费。按新120行，后者应有自己的proof，但单obs正文不能唯一求出66行完整结果投影；新exact proof没有冻结唯一父report选择/严格按format的work分支。

不能在实现阶段自行沿用report proof、把单obs当CheckSection、任选材料中的有利父report或降低为producer/key相等。合同应规定被逐ref读取的各format如何唯一关联真实case/suite/父check报告/原七伴件，如何可计算完整SHA及处理重复、竞争父、排序与冲突；若调整caller关系仍须完整验证这个实际 observation ref 的原工作来源。伴件作为工作闭包材料或独立proof目标的界限也需明确。此项不主张已有算法无法设计，问题是当前冻结合同没有给实施者唯一严格算法。

冻结早单 `Finding-CPAI-P02.md` SHA256 `5238cee68ad8985817c01496ae860044eb1f58099a73901d4dc85b43affc0ac7`。后继需覆盖多case、多Binding、同obs竞争父、foreign case/parent、错误section SHA及真实red/unknown保留；不得删除来源核验或由Review发明新宽松schema。

## CPAI-P03：replacement 新 index 根与原 immutable admission 未确定关联

**P2／OPEN_DESIGN／Architecture**；实施归原 Backend/Integration 安装与 Owner replacement。

0068 第78行要求唯一3.3根由真正 `TrustAdmission.material_refs` 明确绑定；144–146行同时要求 H 保旧资料、真实 Owner replace 接受新index。原0066第72行 replacement仍同issuer/trust admission，123行在同当前 admission 做 expected-current CAS。

实际 `TrustAdmission` 严格正文的材料refs参与完整canonical身份，见停止 `Ordinary/22-installation_qualification.py` 246–259行，SHA256 `c317c9b0fb8122a74149bdb6dab594b480a3f5e4688c63f3e70837d7c21c3996`。同根 `Ordinary/23-installation_trust_consumer.py` 130–133行拒首次路径替已有trust或改同action正文，160–162/198–199行保持原source，SHA256 `40317c88df1b01290c04c594d213340e6421118f538f60069ebd7be223f2dbba`。`Ordinary/20-native_qualification_trust.py` 334–338行核原trust_ref，405–406行要求原admission材料仍在，SHA256 `a0d54a13fc3b114a191295dab554ed3d4032056842e24727aa616c047a878175`。

合法目标是原 T/I1/A 已接受和归档，后来真实 Owner 补B及其实际报告/proof，产生新SHA的I2。原T没有尚未产生的I2；保持第78行只能选I1，改T则改原immutable身份，直接选材料中的I2又缺唯一已接受root。即使I1、I2同锚且均真实held，也不能证明本次哪一root由哪次原action接受。

需要在原安装/replace action、record、受保护current和archive中精确指定初次/H/current/replace/resume 的已接受root selector、同issuer/anchor、expected-current CAS和恢复关系。T/I1的旧bytes不变；I2须由真实原Owner action接受，不热改文件、回填T、扫描同锚root或开公共mint。若需新增exact字段/分派，由 Architecture 单独定义、Backend唯一实现；评审不自行批准新schema。

冻结早单 `Finding-CPAI-P03.md` SHA256 `9b729c6d2f85e41655b906b14604022f2a1ad131f101a8fb1ffc550730b28a69`。后继须覆盖A已消费后补B、H继续I1而C只用已接受I2、同action ACK丢失/冷恢复不新事件、不重复费用和current CAS冲突拒。没有 SQL、OS、Owner replacement 实测。

## 已明确的设计约束及实施边界

三份 exact grammar 以3.1准入、3.2工作证明、3.3producer index分层，不靠typed body或私钥持有本身发资格。3.1 possession签名排除两签名，anchor签名保留possession而排除自身；3.2 role签名和3.3 anchor签名分别排除自身，完整refs包含签名。有效期和实际工作区间分别约束，不把签名等同真实工作。本文支持这些投影的明确设计意图，没有执行Ed25519或canonical实现。

3.1/3.3允许1–16个排序去重Binding；每份工作证明限定自己的Binding、role、report。全材料unique ref/depth/node/字节门及4096refs、128MiB界限保留，不能用同key扩到未准Binding或让一个proof跨所有报告。publisher真实build可与client host不同，但须完整独立源图；local来源也须原已接受锚和有限工作范围，不能拿label、两条声明或publicdict补齐独立权源。suite/check可同Test但分别准入，Review/Acceptance的实际职责、source和工作保持独立。

84–90行DAG从实际build/case/criterion到准入、真实suite/check/观察/伴件、Review、Acceptance、index，再到record/action；准入/index不反指未来 TrustAdmission SHA。这个总体方向避免索引自证循环，**不消除 CPAI-P01 的真实启动门环、CPAI-P02 的父投影缺件或 CPAI-P03 的新根接受关系**。工作source完整读取与真实完工receipt也不能被actor对材料列表的echo替代。

126–138行要求从原成功注册现场保留实际 Native handler/Arc/session/Job 和 Python actual connection/original observation/frame capture，下一assert同object而非重新observe。原close/generation/thread失效及真正terminal前保留资源均有要求。首安装只在原已接受installer action内产生未ready/nonqualified记录，不发ProductionPermit。实际 bridge/caller、role factory、独立权源、原Frame捕获、精确跨语言规范和完整Native生产消费仍 NOT_IMPLEMENTED或未证明。

同writer应只执行同冻结source成员的本地current检查，外部文件、RPC、签名验证在事务外形成不可变证据；真正current/CAS、归档、原authority和撤销门不能靠新source注册跳过。H按原接受时刻和原archive，C按当前资格、expiry/revocation与Ownercurrent核验；新补件不换key强收费，unknown先reconcile，合法immutable replay不重新消费。这些保护应由后继实际完整实现和独立测试验证，当前没有SQL并发、短writer行为、费用账本或Owner机器证据。

Architecture应先补三个exact接缝；Backend负责唯一完整grammar和consumer/capture接线；Integration负责真实issuer/role source custody及Native/安装/同对象桥接；Test、Review、Acceptance只能由各自实际工作形成本职责证明。0068第166–179行矩阵仍是待实施、待验证要求，不能算已执行标准或阳性。原137候选 NOT_FOR_APPLICATION，原 QECP-P01及另阶段路径问题没有在本设计审关闭。

## 终态与未执行范围

本角色只运行自有 PowerShell 文件身份脚本；目标候选函数/抽取函数执行、第三方import、Pydantic、SQL、Test、native、网络、模型、凭据、安装及费用均为0。旧19三次失败/耗尽、原17pass1error/2pass/12pure、31 NOT_READY 和所有原日志/失败保持，不换目录重置原目标次数。

末输入核工具 `19b2fb` 已实际自然exit0、62条无漂移；报告封存和交接的实际末工具由 FinalizerTerminal 与最终消息记录。没有原live产品工具，没有尚待poll的reader。报告/交接写入完成并实际工具自然返回后，全部本轮reader释放；该声明不从文件存在推断工具终态。

没有完整制作流程、安装整包、真实四角色、可信Owner、完整媒体多模态或三OS通过的独立证据。完整 R1 后连续完整 R2 的目标保持，设计审、源码SHA、AST和接口表述均不替代这两轮验收。本轮报告之后即停止读当前输入，后继任务由Root另行激活。
