# RV44 — T32 诊断修复与原故障证据有限评审

结论：**SOURCE_EVIDENCE_REVIEW_FINAL。** RV41-P01/P02 仅在 T32 即时诊断/保留进程 helper 的源码及这次有限机制范围关闭；真实产品 profiler、阻塞子进程终止和 Windows Job 不在关闭范围。RV41-P03/P04 仅 CLOSED_SOURCE_STATIC，human/H01 未运行。新增 **RV44-P01 / P2 / Test / OPEN_STATIC**：未运行的 future Probe JUnit 仍读取已无生产者的旧事件。原 T30 两轮 NOTPASS、90秒 forced red、缺栈/缺attempt和完整历史作品资格均保留。

## 1 固定身份与真实范围

唯一普通根：G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T32HistoricalDiagnostics/。只读165有限 ordinary、正式交接四入口及其包含的旧 ReferenceBodies；未访问主过程私有实例、当前 B26/I36、产品/DB/native/网络/key。没有重跑 T32、新业务批或延长 T30，也没有复制/重核999环境。

165 ordinary +4独立正式入口 =169路径全匹配，末核0变化。保存的输入 index为1029记录/3057记录路径，实际 before/after地图均3058且相等；记录路径全部被地图覆盖。本轮解析的是原保存地图，不把当前环境倒填成当时身份。

| 正式材料 | SHA-256 |
|---|---|
| T32Handoff.md | 706c6d068495ff77b65970c5b51a22de97363ed405da38dfda63e8c976de78a5 |
| T32Handoff.json | 9fba6699c598f6a662bf1fa0e89ba4906f94314f9b7b7475d0e033ba8e579464 |
| T32HandoffSnapshot.json | e8ee1f967425b304b4edb03fa98e2662bc951d846fbdabc2a05cde530269940f |
| T32OrdinaryManifest.json | 854d1a921c58fab67f1c6d760d7a7f81ca039c6fe3f6ff29425528ba6a011393 |
| T32FaultInputPins.json | 44a5cca85496d796d06378cfb85aed7bca6230c4469706fa876eac884385b93e |
| T32FinalSourceDiff.patch | ea288f653498156a4b3faac5e0fe6fa823e59321cebf091d8784c97de4a77515 |
| FaultRoundOne/Cases/JUnit.xml | 714b53440afeab0ab2aaaef04601ca82bda1431f627cfbcda62836cb40ac27df |
| FaultRoundOne/CommandReceipt.json | 57d1963c6d9d15beaf50677f461ec59fbf60fcad253e1a6abe73acab126a2f06 |
| FaultRoundOne/InputBefore.json 与 InputAfter.json | 139a9e716d61052d6550ef293536b97a8c1781250294abe7396b9fd6ce1acf54 |

仓库 AGENTS SHA6de878f514b02788f8af5ba512f71c56bb053f6800d76cf19f3cdd955b7f6a0d；任务卡初读eb6910674c372fbbab5160f5d94b0b8c71efd629edb687ff1a45891d5b8abe56。165准确copy路径、正文hash/size由Manifest与本角色InputPins固定。

## 2 原一次fault的实际证据

原2cbb85/session55191→3eb7ec→b77873，实际工具0，不是另一次启动。原JUnit12 testcase名字、tests12 / failures0 / errors0 / skip0，与原stderr的12行ok和 **6.807s** 一致。该耗时来自unittest stderr，不当作完整launcher墙钟或真实OS故障耗时。

真实外层 Python wrapper13808 / creation134359910895528014 / actual0；内层 fault child19016 / creation134359910907863091 / actual0 / forcedfalse；两层保存的lifecycle_errors空。RunFaultT32.ps1:76–115用同 Process、双输出pump、真正wait和pump结束后关闭；RunFaultT32.py:97–124成功Popen进入同finally，再用真实 RetainedChild helper等该child退出，输出重定向文件关闭后保存 terminal收据。内层是文件重定向，明确 redirected_files_not_pipe_EOF_proof，不能称native/Job后代或每个文件为pipe EOF证明。

FaultProbe17–27的审计边界拒产品/Pydantic/SQLite/socket及新child/network；12项执行真实本地journal I/O和明确 SyntheticPopen端口。synthetic pid170032/handle字符串不传OS，其5/7/8/0等返回码不是任何真实OS退出码。原wrapper/child自然0只证明该机制批自然结束。

13条journal链共95个真实JSON事件，sequence/previousSHA/partial/clock顺序均匹配：外层case批37、内层场景55、真实wrapper ChildLifecycle3。另有1个故意预置的非JSON collision marker，原bytes/hash保持；它不是坏事件被吞掉。

## 3 RV41-P01 — 有限源码/即时I/O机制关闭

固定 [DurableDiagnosticsT32.py](G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T32HistoricalDiagnostics/SourceBodies/DurableDiagnosticsT32.py:22)，SHA5619700b23d0c1190622eb9e0917bf318dfb0275faa6040699230f5bfd3738e7。record22–36加锁、exclusive xb、write/flush/fsync后才递增seq/SHA；每个记录带case/clock/pid/source、partial=true，不能覆盖原记录。addError61–63/addFailure65–67/addSubTest69–73在下一case前记录真实异常类型、最多64KiB栈及全栈bytes/SHA/truncated标记；stopTest83–88、success/skip也即时保存。

原case_error链实际先 start→error→stop，再following start→success→stop，failure同理；subtest failure/error保parent，后续KeyboardInterrupt链仍保先前error且无suite_returned。collision场景实际拒覆盖，原marker保持。phase/counts场景真实保存了明确的 own-fixture 计数/文件标签，不能当产品方法已经运行。

future Probe275–305接该Result和实际 sys.setprofile；固定 MechanismBaseT32:33–46计源码call事件、首次/私有边界/public实际对象入口持久记录，22–25将phase入journal。**这段产品profiler没有执行**，12故障项的phase/计数是自身机制场景，不授真实调用栈或真实产品计数资格。

关闭范围为原“整套结束才存已发生错误/前进诊断”的具体保存机制。整套产物一致性另受下文新增P2阻断。原T30缺失栈不重构；真实产品/阻塞profiling仍待。

## 4 RV41-P02 — 有限源码/合成保留端口机制关闭

固定 [RetainedChildT32.py](G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T32HistoricalDiagnostics/SourceBodies/RetainedChildT32.py:6)，SHA096b2847ebd9ae09b3e0f29bee3562a61b4d48af9e0e1019c478ab0370daa1fb。deadline28–45锁存forced红，查原handle creation；明确unknown/mismatch拒terminate，matches才记录request并调用同child.terminate，分别保存return或exception。finally50–64只等相同Popen到actual exit；观察timeout/error不drop、不换进程/新PID。每个journal记录独立文件，terminal不覆盖原attempt/check/request/结果。

原timeout端口链实际为 deadline→identity→request→return→wait_timeout→wait_return→terminal，且 forced永久红。unknown/mismatch、identity观察错误、terminate异常、初wait异常场景各自保原错误与same-object等待；请求return明确不是终态证明，unknown synthetic最终0也未洗forced。真实wrapper自然退出路径实际有initial_wait_return→child_terminal→redirected_output_closed三个独立记录。

原缺attempt记录保持缺失，本批不证明真实终止请求、原handle身份失败或Windows Job故障通过。saved11–19对journal写失败保lifecycle_errors并继续持原child，实际caller139–140把forced/errors/输入漂移纳入失败；该保全分支目前**只有源码**。

覆盖缺口：12项未注入 stream.write/flush/fsync故障，也未在wait_owned_child.saved中注入journal_write异常；collision测试是直接journal拒已有文件。不能以这12绿宣布全部存储故障和native清理已验。未来若需要此类资格，应由Test另固定真实最小fault计划，不由Review追加运行。

## 5 RV41-P03/P04 — 仅 source-static关闭

固定 [ProbeT32.py](G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T32HistoricalDiagnostics/SourceBodies/ProbeT32.py:211)，SHA11f136f43a0c5cecfadd78d359b88fa4263d490a99ea3927a908e455ff513edd。human211–213增加必填 method_ref='human-canonical-only'。与原Probe8a118d60…逐方法AST核，去除这唯一keyword后原10方法体/断言完全一致。未运行真实DTO/approval/human链；canonical-only、not-staged/not-published/NoSourceFileClaimed仍明确，不授真实成包/历史阳性。

固定 [HistoricalConsumersT32.py](G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T32HistoricalDiagnostics/SourceBodies/HistoricalConsumersT32.py:28)，SHA025712d4929b7f76c5569865b1a5fe613d7b718c97b5a64ddd7c8a9a55add8ab。actual_index14–31保真实Bundle.verify index前提、canonical bytes/hash，28严格UTF8str传原parse ABI；与原c40ca090…AST仅此decode变化。未调用实际H01/index/parser或篡改产品契约，H01–07真fullBundle/八输出/全部许可/ASR/MM05/Owner前置继续待。

首次source-only候选import顺序纠正、早PreparationReceipt保早身份；正式身份以FinalSourceDiff/SourceBodies/index为准。FutureBusinessInputPins仍未提供/未准未跑，不借本故障批绿启动它。

## 6 RV44-P01 / P2 / Test / OPEN_STATIC：future Probe JUnit失去case事件生产者

精确源即上表11f136f43…的SourceBodies/ProbeT32.py。275–277改用DurableTestResult，303用该Result执行suite；DurableDiagnostics45–47只向journal写case_started。固定Probe/Base全文没有任何emit('test_started')生产者，但Probe312–318仍在base.EVENTS中筛test_started来创建testcase。

最小静态触发：未来任意非空suite真正返回，result.testsRun=N>0；这条生成链产生JUnit tests=N，却0 testcase，失败/error也没有对应case节点承载。缺口尚未实际运行，不叫已有OS或产品红。FaultProbe264–269读取真实BatchDiagnostics case_started，原12个JUnit节点和真实绿保持，不能倒填其未覆盖的future generator。

归原Test owner最小修复：以真实case journal/结果中有生产者的身份构造future JUnit，保逐case failure/error/subtest归parent和partial/suite_returned区分；独立检查tests数与实际节点/结果一致。保原10断言、原raw和无future准入；不得仅填N个空节点、改tests=0求绿或用AST/合成结果声称业务已运行。先固定修订源及纯生成器最小正反计划，另经独立准入，再考虑实际业务批。

## 7 终态与下游

本角色标准库d54831实际0只解析保存JSON/XML/journal/AST，不import或运行任何T32 helper/Test/产品。169末核0变；固定reader全终态释放、live=[]、production freeze false。Facts SHA8d85ab86658e1eeb470bff7a9a667fbffafe2456715032b35dcfad7b23e99bf8；SourceAfter SHAdd5ea1fe3c0f117cd7026aff07d948838a04a19d8bd4a157ef983bf3746adbd3。只写本报告和Review/HistoricalDiagnostics-RV44/。

原T30两NOTPASS/90秒红及缺栈/attempt不洗；新增future JUnit静态P2仍OPEN。真实产品profiler、human/H01/current-final许可联核、完整作品、安装/Windows/三OS仍未通过。本报告不发runtime/测试/费用/发布许可，不代Acceptance。完整R1三OS独立验收后连续R2、数据实例持有、前台五步保持。
