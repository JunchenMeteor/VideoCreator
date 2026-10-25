# RV16 — T15 Bundle/ASR候选标准与拟夹具评审

FINAL；永久独立评审。评审未执行产品、测试、ASR、decoder或DB，未改实现/标准/测试、读key或付费；未读取B9 WIP或I16实验源。

## 审批结论

**不批准当前revision1标准/fixture的整套审批单位。** 两处实际拟夹具与标准存在静态缺口，交TestDevelopment原owner修订，不把源码推演称产品运行红，也不代修/要求B9停写。

单独批准固定criterion JSON的precision_computation_candidate数学定义：对固定独立人工语料的每个语句，取起点/终点绝对误差最大值，以精确nearest-rank ceil(95N/100)取P95，保持≤200000µs。这是原MM03语句指标的明确化，未降低门槛，不批准词级精度、具体基准、authority或完整报告。当前语料/标注听审/authority/30×60基准均not_ready；算法定义批准**不授产品launch**，不解除alignment_required/waiting_user。

38项计划的覆盖方向与现有规格/ADR一致，可用于继续准备：33 real、5 injection，全部not_run；计划不是38个可执行adapter。服务/API/MCP/业务Driver、精确生产源/资源/ZIP限额与独立评价输入仍须绑定并独立准入。T15整套单位待修订新hash复审，旧candidate保留。

## 固定身份与实读范围

| 固定输入 | SHA256 |
| --- | --- |
| RV16任务卡 | 019d821e9591ca40582a8843c653f3c06490ac2d250988bce7b5146ca241afb7 |
| T15PreparationHandoff.json | b8330e6c2df346ee887a2eb4f9bb819d27e02070d4df1addc09aff704dbad86e |
| T15PreparationHandoff.md | 850e775d6a75f0e0e36bab0a00b3dfbb359246fc60ba021ce9b58c36b02d9998 |
| criteria JSON | 7e0761220eb17f52ce733d40354616502995b443d4e45be2af1e49ab37a36ea4 |
| criteria Markdown | 2b32a713722e24315a6136659eb9a4042bc89a0350771ca02963ebf754bfd28c |
| T15CasePlanRevisionOne.json | 62df492dfe7bf27bab7016bf4cb3536b0ddc5a4424203b4e1d8dac4755788225 |
| T15IndependentBaselinePlan.json | 2aaa04d0ebe71aa68228a63c638d0d93057bd31c3ce9f4dffbb2a6f426428dd5 |
| T15FixtureManifestRevisionOne.json | 945728a49ed2ffa943cada7210586018a886d9ea1990ef002a839d8a7b49d791 |
| T15PreparationCopiesManifest.json | 482a666fdb99938cbe1c152711685b665401bb6e26a2134b5b120ac6d8befc2c |

17个普通副本位于G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T15Preparation/，实算SHA/size全匹配原/副本声明。manifest列出的15个实际候选/夹具/准备收据也实算匹配；未访问私有Case、凭证或运行资源。criteria与计划的38个cases逐值相同，状态均not_run。公开Schema始终后端唯一源；评审没有把T15 oracle当第二公开模型。

支持文档精确身份：ADR0012 2155cb4a068203bf3a9bb0527deebb5b5bd99a2852f0acf6bc91218f9dde6918；ADR0013 ba32e14cd9ea8427dc731ab37be2424e487b6b4dfadca704109419e07fa975e2；W8Handoff31a7d6fc4c42819e18c203c27b933b669f4024d01e8ae0ccb33323672e57ab32；W9Handoff923acbc84c4fc0ec43142167a7f37992f9ad7e0825ad69887114902fcb51ed2e。原09 MM03行345与MM05行347分别保持P95≤200ms、至少30题/60作品precision≥90%并报告recall/refusal。

## RV16-P01 — strict JSON遗漏合法数字的非有限转换

严重性P2，归属TestDevelopment；标准/观察器缺口，**static inspection、未执行反例**。

源码G:/开发测试/Projects/VideoCreator/tests/bundle/t15_evidence.py SHA dc8149ed4597a74f458eea9b0cddf67697613f1f450108d6665fa5a24471e48d，lines16—29（普通副本Evidence13）。strict_json用object_pairs_hook拒重复键，parse_constant拒NaN/Infinity，但没有parse_float或解码后的递归有限性检查。

静态触发：`{"x":1e999}`、`{"x":-1e999}`或嵌套数组中的同类数字。它们是数字token，走json.loads默认float解析，可能溢出成inf/-inf，不会经过只处理特殊常量token的parse_constant。函数因此可把非有限值交给后续oracle，违反T15-04及ADR0012的“重复键/非有限数拒绝”。后面某些record_hash可能再拒绝inf，不等于所有strict_json调用入口已有所声称的守卫。

实际纯sanity源码t15_fixture_sanity.py SHA36d4e926110366d969bed78511e39290a9fe4befa8674b96376b4eff5f3dc5a8，lines15—20仅覆盖NaN/Infinity/-Infinity和重复键，不覆盖合法指数溢出。九项sanity绿不反证此静态缺口。

最小修订：保留现有重复键/原数组/Unicode规则，在strict parser入口拒绝数字转换产生的非有限值，覆盖正负和嵌套；明确不偷偷修补或规范化原JSON。由Test原owner新增纯fixture负例并保留原候选/原绿收据，提交新hash。若采用精确数值解析，须保持公开规范记录hash与生产数值语义，不能引入镜像Schema或把允许有限范围自行放宽。

## RV16-P02 — precision先折叠重复unit，使候选坏边界消失

严重性P2，归属TestDevelopment；独立精度oracle缺口，**static inspection、未执行反例**。

源码G:/开发测试/Projects/VideoCreator/tests/bundle/t15_oracles.py SHA4a561367b46a4f07985788ee1f5467b3d2b18f4b4f0296c37ae0da938b4075f0，lines103—117（普通副本Evidence15）。lines104—105用dict comprehension从alignment.boundaries按transcript_unit_id构造predicted，随后lines107—109核dict数量与ID集合。没有先检查原alignment.boundaries长度和ID唯一性。

静态触发：在原独立语料的unit U上，候选alignment先放一个同ID、误差超过200ms但仍在真实时长内的range，随后再放同ID准确range。例如时长20s下U参考[0,1000000)，候选先[500000,1500000)，再[0,1000000)。其他语料unit保持。报告只放每个独立unit的一条好range，按真正record_hash规则重新计算候选alignment/report hash；没有篡改独立reference/authority。dict仅保留最后一条，len(predicted)=N、report pairs=N、expected=N仍成立，P95可由保留下来的好范围得到0。原候选多出的坏边界不经interval/误差/完整性核验。

这是“全unit候选边界不得挑选/隐藏”的断言漏洞。正确自算hash只证明字节一致，无法补回被oracle丢弃的边界；也不能把未来公开模型或adapter可能拒绝重复作为当前独立oracle已经核验的证据。不据此宣称B9产品接受非法alignment。

最小修订：在建任何ID→range映射前，核原boundaries列表长度、unit ID严格类型及唯一性，要求完整原列表与独立reference/report集合一一对应；全原条目均验证range。保留原数组，不通过去重求绿。纯fixture加入“坏先/好后”“好先/坏后”、同值重复和遗漏/额外ID负例，再核正常完整语料/P95算法。该修订不降低200000µs，也不要求虚构人体标注或运行ASR。

## 标准方向、边界和待绑定证据

默认8输出与固定附件、独立旁白/编码前PCM混音、源稿与实际主转写分离保留；相同音频字节不能替代真实生产用途链。主转写仅最终mixed或登记MP4解码音轨，原稿不能送ASR。空segments不是静音/音乐证据，词概率/跨容器估计差不是人体边界误差。W8/W9有限真实ASR和坏raw注入必须分列；本阶段不能把这些owner收据补成独立precision或完整Bundle正向。

数学定义选择每语句max起止误差比把两端拆成2N个样本更能保留语句坏端，nearest-rank使用精确Fraction避免浮点分位插值改变门槛。N为独立批准语料的完整语句总体，不能由candidate决定；N=0不通过，词标准另行。此批准不指定新样本最小数，不把一个合成unit演示当可用人工语料。真实正向前须固定音频/sample/PTS、所有unit与gap、独立听审/裁决、reference bytes/hash、authority注册与服务可信入口，防candidate自标为ground truth。

源sample/PTS及最终时间轴分别持有，有理数crop/place/stretch/encoding关系先据实际变换核，边界独立half_up_us；SRT/VTT按contain-capped，误差<1000µs，与ASR精度分开。语义/rights/RAG须实际最终帧和音频依据，计划文字/色板/自报frame_verified不能替代framevalidator。MM05至少30题/60作品人工标签、四类反例、precision≥0.90与recall/refusal保留；纯引用与Portal索引分别评估，模型标签或全拒答不通过。

权限必须来自可信AccessContext且在Range/304/分页/语义读前，payload recipient不授权；expire/revoke/不同主体/不同实例origin单列。完整ZIP与projection、严格全集/path/重名/CRC/实际限额、第二实例原origin字节与本地授权分离方向可接受。mutator目前只9个有界ZIP和5类raw输出构造；其存在不等于真实API/driver拒绝，更不覆盖全部CRC/链接/限额场景，缺真实绑定维持not_run，不删计划。

原子可见方向沿ADR：不可变文件先持久化，Bundle/交付Step/Run/Production/outbox同短事务，unknown/unsettled/旧fence/cancel不得publish；cleanup_unknown不得settled/refund。atomic_visible当前是被动snapshot断言，仅布尔/计数自洽不能证明实际事务及文件持久化；未来真实read-only observer须给原事务/ID/hash/fence/journal/outbox和真实kill前后窗口。不把fake snapshot、record hash或CLI0当生产成功。

这些是未来执行准入条件，当前没有声称全部由几份纯oracle完成；不要求Test为此轮准备冒造完整positive或冻结B9 WIP。未来实际adapter/资源/基准绑定是另一审批单位，所有实际源正文在launch前归档，并单独root授权，不拿新源补T14历史。

## 原纯sanity与收尾

原工具chunk137b95/tool0，收据SHA7cf2caa0ab5b586d66bdc82a4f90307d99ae4fb513ffb1b4d15c1fded3a528c2，StdoutSHA6009c6df9242fd398ba5ae3f9ba6577e62d820e5c43c1db15266386fa496ed68。实际9tests/0failure/error/skip、0.1862400000100024s（raw0.186s），6个own source/Python before-after hash相同。AST/stdlib字节/dict/ZIP sanity没有产品import、ASR/decoder/DB/网络/child。重复ZIP预定warning及未单独保存整壳stderr限制保留，不补造JUnit或产品exit；RV16也未重跑这些夹具。

Snapshot G:/开发测试/Codex/VideoCreatorImplementation/Review/RV16Snapshot.json SHA e65a9f12888c233b71c6faa2fd5d1e461bd09aaa2ad452fe7a06eff151b08b95 保存精确候选正文、17副本/15实际文件核验、支持文档及静态触发。标准/fixture整套revision1 NOT_APPROVED；metric definition only批准；execution_readiness仍not_ready_for_execution。原RV15局部关闭与所有剩余窗口不变，Gate0→独立R1→连续R2不缩。全部评审工具终态、无live，结束本批。
