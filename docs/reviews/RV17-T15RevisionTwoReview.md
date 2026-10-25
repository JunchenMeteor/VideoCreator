# RV17 — T15修订2标准与准备夹具复审

FINAL；永久独立评审。审批单位仅固定T15 revision2标准、38拟计划及stdlib准备夹具，不是B9/W9产品执行或完整验收。

## 决定与边界

**APPROVED_CRITERIA_AND_PREPARATION_FIXTURES_REVISION2_ONLY。** 精确批准下表criteria JSON/MD、CasePlanRevisionTwo及FixtureManifestRevisionTwo引用的固定准备源码/证据版本；历史Before旧helper与原红作为对照保留，不能被理解为旧helper也通过。RV16-P01/P02在此Test标准/夹具范围关闭，没有发现阻断此次有限审批的新问题。

执行状态仍为**not_ready_for_execution**。35普通副本和21项纯sanity并未提供38个业务adapter；实际服务/API/MCP/ASR业务Driver、生产/工具资源固定、独立人体标注/听审/authority、MM05人工30题60作品语料尚未就绪。此审批不授产品import/launch/freeze、收费、对外发布或Gate0/R1/R2通过。数学算法、真实语料、可信注册与产品执行准入分别判断。

## 固定审批身份

| 文件 | SHA256 |
| --- | --- |
| RV17任务卡 | bad21b9458dd099b801a95a7a0196efe39280cc83b33e548425181f45e4b7901 |
| T15RevisionTwoHandoff.json | e768cbc2af960a31b35bfccccfc1b7a59ee22b343a156ca8f7b761a5248ab604 |
| T15RevisionTwoHandoff.md | 8fa144256f300b8e59ec87833c4aaadedf521cd74b347394adc05c8cf30cf1c5 |
| criteria JSON | 40afb746a669df341adc815491bc9e8d5962038591241081149931ddb6d43ecb |
| criteria Markdown | 6546e6ad8383f9e2c01bb48fb3ef9a23b1ac629b3de6ce665cfef22296ab23a0 |
| T15CasePlanRevisionTwo.json | d8dbe9916e78422fb5a7f504ca4a70f2206670239e1f5c635dd57cb5e8800753 |
| T15FixtureManifestRevisionTwo.json | 8365c21f4af6e1ea5a6d367f66d778ee53c83ebd4416f96b0f9e4767fb470c30 |
| T15RevisionTwoCopiesManifest.json | 61c0036b6824688388a29b47bf076c5a140760b29fa1f02b3312ee8fb3b22c87 |
| T15RevisionTwoSourceBodiesManifest.json | a1d8c85b37eaa43a31c80cf77275b036d2061fce6a0274eccf3e56b16db80f82 |

普通副本根：G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T15RevisionTwo/。35副本实算SHA/字节均匹配原/副本声明；manifest中的34实际文件匹配；12份Before/After消费正文与各原receipt的before/after完全匹配；旧revision1的17普通副本实算未变。AGENTS仍6de878f514b02788f8af5ba512f71c56bb053f6800d76cf19f3cdd955b7f6a0d，角色白名单不变。

当前准备源码六项为adversarial30e730180b4eed24029d223d29b0c97bd0561bee21140eed9dfc8c2af0b04c42、evidence e910e3b02a0f6a1b971d54225575a18eb9f6df3eab1e4a64d3941a7e6edee918、原fixture_sanity36d4e926110366d969bed78511e39290a9fe4befa8674b96376b4eff5f3dc5a8、oracles5dbd348912a14099c3d8c8a96316ddea40541456aef201b0507a4b3ed94e3a8c、revision_two_sanity78749e68de2005d597644a9fd483c52cc5b3b4e4dfc647369de53492a443b8fc、runner3c8d29d31568d7371e62111b211ca906bc8b5268f54aedab1f8e42b5be19878a。精确路径/size及其他准备证据以批准manifest为准。旧t15_prepare仅revision1历史入口，不冒充新版21项入口。

## RV16-P01闭合

归属TestDevelopment，原P2，仅Test夹具范围关闭。

原strict reader dc8149ed…一并保留。修订2的tests/bundle/t15_evidence.py（普通副本Evidence12、After正文Evidence29）lines29—36将json.loads合法float token交给finite_float：按原float语义转换后立即math.isfinite检查，不有限即ValueError。原重复键object_pairs_hook与parse_constant仍在；不采用Decimal、去重或修补原数组，不改变有限float公开hash语义。

新增断言lines68—75覆盖正负1e999、顶层数组和嵌套对象/数组中的溢出，同时验证1e3/-2.5/1e-3正常保持。Before原helper真实未拒绝这些token，After同断言拒绝；原九项NaN/Infinity/嵌套重复键等断言源码不变。此证据修复了RV16指出的入口缺口，不能扩大成产品JSON/API拒绝已实测。

## RV16-P02闭合

归属TestDevelopment，原P2，仅Test独立oracle范围关闭。

tests/bundle/t15_oracles.py（Evidence14、After正文Evidence31）lines103—133先核独立reference键/range、原alignment.boundaries列表长度、每条dict、严格非空字符串own/transcript ID、二者唯一性及每条range，且完整ID集合与reference对应。report原列表同样核完整长度、唯一ID及各range；只有此后lines134—135建立映射。原坏先好后/重复同ID无法再被折叠后漏检，也没有通过去重/修改reference求绿。

新增同一断言源码覆盖坏先好后、好先坏后、同值重复、遗漏/额外/替换ID、bool/int/空/None/list ID、重复own ID、report重复/遗漏/替换及候选隐藏坏range。每次通过真正record_hash规则重算候选hash，不能因“hash本身不对”替代内容完整性检查。reference与authority为明确synthetic字典，只做oracle机制，不是真标注/可信注册。

证据细界：隐藏坏range用例插入额外条目，也可能先被完整长度检查拒绝；不能仅凭该用例名称宣称实命中每个range循环。逐原条目range守卫是本次静态源读可见的行为，重复/完整性守卫的真实纯fixture拒绝有After收据。本有限审批不要求额外扩大实验或补造覆盖数字。

## 原红→新绿与身份

| 批次 | 原tool chunk/exit | tests | failure记录/error/skip | 用例墙钟 |
| --- | --- | ---: | --- | ---: |
| Before旧helper | 9c9a69 / 1 | 21 | 17失败subtest记录 / 1 / 0 | 0.10219279999728315s |
| After修订helper | 6a05dc / 0 | 21 | 0 / 0 / 0 | 0.09086799999931827s |

Before Receipt12b4b1d4bca796cb58b5915f8f956eaf14fc540c9ec378e6dc6f4a630421891d；Stdoutbc5db30530cd84eb28342dab08dec82b3dbcf0c60520c252b04d1a31197e85a1。原list ID造成TypeError的1error保留，不解释成正常拒绝，也不把17subtests写成17个顶层测试方法。

After Receipt393a0e1a18b487c7cd055f3d448df14a5023c48ee29a3f2516ed28427d879ac6；Stdoutfcb42b9afb5339d100e3742e8b74960175b5355709162132df010a2de5a6e2c1。原log分别Ran21tests in0.102s /0.091s，真实Before FAIL、After OK。不是pytest/JUnit或产品childexit；两份另存的in-process Stderr均26691288614aea0e39c8a93175729df5dab02378c2d03f42b616dd8dc083f488，保留预定重复ZIP警告。

实际准备命令：项目.venv/Scripts/python.exe运行tools/testing/t15_revision_two.py --output-dir，分别指向自身TestDevelopment/T15RevisionTwoBefore与After。runner AST检查和stdlib观察/字节/dict/ZIP，不import产品。每批7项source/Python before=after；跨批只evidence dc8149ed→e910e3b0、oracles4a561367→5dbd3489，原9测试、新12测试、adversarial和runner hash全不变。未修改断言求绿，未skip失败。范围只是声明7项，不冒称全repo/OS输入穷尽不变。

12份消费正文档案的archive_timing明确为post-run matching original before=after identity；两份旧helper来自已有同hash旧副本，其余根据不变hash核定。它们不是虚构运行前归档，不是生产正文，也不补T14 37源码历史缺口。未来产品launch前生产/测试正文与资源归档要求继续保留。

## 门槛、准备范围和未就绪项

criteria JSON/CasePlan仍38cases且逐值相同，全部not_run。对revision1的case修改只有T15-04补数字溢出反例、T15-10补映射前原列表完整性。顶层修改仅candidate_revision、P95对象审批记录、上述cases、execution_readiness及revision_history；baseline_status完全不变。

P95对象原八项定义全部相同，只增加approval记录，正确写RV16 mathematical definition only、human_baseline/authority/product_launch=false。新代码仍max(abs(start差),abs(end差))、精确nearest-rank ceil(95N/100)及≤200000us；纯正常例200000通过、200001拒、完整20unit误差10k…200k的P95=190k。没有词级继承、擅改参考总体/阈值或批准合成reference。原MM05至少30题60作品、precision≥90%与recall/refusal，全拒答不通过，未改变。

本次准入的是标准/准备夹具，不是producer能力。实际主转写/音轨/媒体解码、原稿分离、frame语义/rights、默认八项和固定附件、原子Bundle-Step-Run-Production-outbox、真实kill/cancel/unknown、AccessContext/Range/304/分页、完整ZIP/projection/跨实例origin、HTTP/MCP同入口等仍需要固定业务adapter与真实证据。producer服务/资源/精度authority/独立听审和MM05基准均未准入；无基准维持alignment_required/waiting_user，不用fake report/true callback凑正向。所有R1真实作品视听、安装三OS、Portal/API/MCP、自主Agent及连续R2商业目标保持。

RV17未运行纯测试或产品，不代Test修代码/标准，不读取B9/W9实现或WIP私有实例；只读固定候选及历史对照，写自身Review/正式报告。Snapshot G:/开发测试/Codex/VideoCreatorImplementation/Review/RV17Snapshot.json SHA332a36f06f726b3577d725dd5bed58fe3b584538782768c8b5a0d1acdb214344；全部工具终态，无live。精确revision2准备审批完成，结束本批并释放槽。
