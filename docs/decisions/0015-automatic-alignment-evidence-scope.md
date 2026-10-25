# ADR0015：自动制作与对齐证据的两层准入

2026-10-08。状态：批准本轮R1必须实施的显式新证据策略及下一契约/标准准备，不批准任何当前算法、基准或authority。旧请求、ADR0013 strict语义、RV17固定T15修订2及pinned实现不改；本轮只写设计，不读B9/I18 WIP或运行/联网。

## 范围纠正

02第8节允许真实TTS时码、独立对齐及经授权校正，要求记录方法/精度；09/MM03和G0-ALIGN要求真实样本、抽样听检及语句边界P95≤200ms。原文没有要求每条正常作品都由人重新标完整语句。ADR0013及T15当前strict positive把独立参考、authority和逐unit报告作为每作品默认发布前提，确实加严并会阻碍用户一次API/MCP自动完成的R1目标。对此作显式版本修正，不用通用算法分数伪装单作品测量，也不删除报告/降低原门槛。

RV17报告SHA02d1d644842b52c26e81905bf22eac6981528db7403cb218a6c4331e7854f25e仅批准criteria JSON40afb746a669df341adc815491bc9e8d5962038591241081149931ddb6d43ecb、MD6546e6ad8383f9e2c01bb48fb3ef9a23b1ac629b3de6ce665cfef22296ab23a0及准备fixture8365c21f4af6e1ea5a6d367f66d778ee53c83ebd4416f96b0f9e4767fb470c30；真实基准/authority/产品运行仍not_ready，21纯sanity不授真实准入。

## 1 显式新策略，旧路径保留

后端下一准备版本增加明确的请求/证据策略版本，不就地改0.2已存ProductionRequestRevision、默认utterance_verified、空降级、hash/幂等或旧报告。新公开契约建议0.3.0-candidate，实际名称/生成由唯一后端固定；这是数据契约修订，不更换技术栈/库/数据库。未指定新版本的旧调用仍按旧strict解释，不能升级后自动把其阻断改成成功。

| 新DeliveryRequirements字段 | 语义 |
| --- | --- |
| alignment_requirement | 保留utterance_verified/word_verified；词级仍需另获批准标准 |
| alignment_evidence_policy | strict_reference_v1 或 qualified_method_runtime_v1，协议显式区分；不能看见失败就换策略 |
| evidence_policy_revision_ref | 安装实例/项目可信政策的固定revision/hash，列已批准method profile、适用范围及质量要求，和原预算/许可交集；不是prompt或客户端true |

新App/SDK/MCP明确使用新契约；安装实例或Portal一次可信预授权qualified_method_runtime_v1后，后续只传目标/资料即可自动完成创作、对齐及成包，人员主要审核/指导，不逐作品填写标注。这条自动路径属于本轮R1必做，不推到R2或总目标外。interactive/unattended及原审核点、八输出、来源/费用/权限规则不变。缺政策/合格能力时明确等待配置或能力恢复；不能暗选人工、扩大收费或改旧default。

新旧策略的allowed_degradations仍默认空；新自动策略不是旧strict请求的隐式降级。word_verified缺独立词级准入仍阻断，不能用语句P95或默认自动策略补其资格。

strict_reference_v1继续要求该作品实际音频/Alignment与独立参考逐unit绑定和复算报告。当前已批准T15严格positive仍要真实人工标注及可信注册。生成器原生timing可成为将来独立准入的一类参考，但须确指实际返回音频sample/事件、独立于受评ASR/Alignment并经人工基准验证；不因TTS名称、planned文本或ASR两次一致即可信。本轮无此已准入资源，不能给旧strict填假reference。人为校正/标注是这个显式严格路径的职责，不隐瞒为普通自动路径必选项。

## 2 基准报告与本片报告分别持有

| 对象/字段 | 本轮R1新策略的最小映射 |
| --- | --- |
| MethodQualificationRef | profile_id/revision/hash、method/tool/model/resource/实际compute身份、OS/arch、语言/输入/变换适用范围、独立benchmark_report_ref、criterion版本、authority/有效期/状态 |
| 独立BenchmarkReport | corpus/ref/实际音频hash与坐标、标注/听审/裁决身份及独立性、全部unit误差/样本数/P95/缺口；evaluation_scope=capability_benchmark，只能评价这个固定方法与条件 |
| 每片WorkAlignmentValidationReport | work/run/request、实际input_audio SHA、Transcript/Alignment/Mapping/Subtitle各版本、实际工具/资源/compute、qualification/policy引用、执行检查/原证据、差异/不可辨/范围缺口、结果和原因；evaluation_scope=work_runtime_validation |
| 每片PrecisionAssessment | 保留真实报告及status/metric/sample_count/p95/evaluation_report/criterion/limitations；另明确evaluation_scope和reference_ref。没有该片独立reference，status=not_measured、sample_count与p95=null，不能填基准分数或称本片≤200ms |
| BundleQualityEvidence | 按固定新政策核required checks，分别引用上述报告；“合格方法+本片核验通过”可得新自动策略的release eligibility，不冒称该片独立精度已测。旧strict判据不调用这条捷径 |

这些是后端唯一模型下一准备稿的精确内容要求，不是已存在源码或自动授信。每片仍保存实际ASR/Alignment及PrecisionAssessment/Quality报告，方法为词时间估计就如实标记，不改名forced alignment。即使采用可信TTS边界，也需对真实音频做转写/核验，不抄源稿。独立Benchmark report也不能证明每条任意输入都有≤200ms误差；展示与API分别说“方法已通过基准、本片检查通过”和“本片误差未独立测量”。

## 3 runtime validator确实检查什么

自动策略发布前必须核：真实主音轨及hash/完整解码/样本率数/PTS；源稿与实际转写分离、完整结果与差异；所用方法/profile/resource和实际compute一致且覆盖该输入条件；ASR/对齐所有unit严格ID及时间完整性、不越界/不重复/不隐藏坏项；真实裁切/变速/编码关系和逐piece映射；字幕从实际结果生成及量化误差；音乐/静音/不可辨的证据和未观测缺口；默认八输出/固定附件、来源/权利/批准及有效fence。只有这些检查的真实产物与结果能被validator登记，媒体返回的passed/confidence不是授权。

对齐来源可以是当前候选ASR、实际独立对齐器或真实TTS timing，均须独立准入其精度和适用范围；运行检查本身不是独立听觉ground truth，不计算没有reference的本片P95。ASR置信、自洽metadata、VAD/字幕边界或第二个模型一致不能补此测量。无法核输入范围/缺工具、资源身份漂移/方法未准入/本片检查失败/authority撤销，保存alignment_required及具体reason、waiting_user可恢复动作，无完整BundleRef/成功事件；保留实物和原账本，不重生成凑报告。

一次政策预授权只能使用已批准profile。改模型/资源、实际compute、OS、关键配置或对齐算法后需对应新qualification，不继承旧基准。runtime在执行前及发布前重核registry状态与policy版本；撤销/过期阻止新发布，既有包不改字节，保留历史证据和适用状态。

## 4 基准与authority由谁提供

独立方法准入由Test维护真实中文/漏词多词/静音音乐/非零偏移和实际变换的固定语料，授权标注人员实际听音/逐unit标边界、记录工具/坐标/争议裁决；参考不从被评ASR/Alignment复制，完整样本不挑好段。使用RV16/RV17已批数学定义：unit误差=max起止绝对误差，nearest-rank ceil(95N/100)，P95≤200000us；原阈值不降，无新增样本数字冒充原批准。语料/条件、真实标签与人员收据还须独立Review/Acceptance审批，模型可助标但不能自签ground truth。

authority来自安装实例可信配置/受信资源分发及独立审批事实，登记issuer、获批criterion/corpus/method范围、报告/资源hash、状态/有效期/撤销版本。普通Production、模型工具或API payload不能注册/批准自己，测试synthetic authority不进入生产注册。后端实现受控resolve/verify/revoke端口及真实报告完整性复算；集成只封装固定已批准资料与身份，不能因为文件有hash或自身清单写approved就授信。离线本地策略不依赖官方产品登录；撤销资料与更新以明确可信渠道导入，不因缺云账号锁项目。

对本轮R1合格自动方法，研发一次建立并发布可安装的资格资料，用户无需为每片做人工标注。严格每片测量则由明确授权的独立标注/qualified timing来源给原音轨reference，再生成per_work_reference_measurement报告；缺这种资源时该strict请求仍等待，不能让正常成片审核点击代标注。当前语料、听审工具/人员、注册、算法真实精度和OS范围全部pending，不把设计或原W8/I16 ASR成功作资格。

MM05同样是至少30选题/60作品独立人工标注基准的阶段门，precision≥90%并报告recall/refusal、全拒答不达标；不是每次检索都要人标所有候选。新查询运行时仍做实际权利/失效过滤、来源版本精确关系、方法/索引配置、匹配证据与no_qualified_match，不把语料90%填成某候选正确概率。原100%来源版本关系和检索验收范围保持。

## 5 必须在本轮分派的下一任务

- 后端：先交独立新契约/策略版本、三类报告映射及registry/validator端口，保旧0.2幂等/strict和schema4事实；待当前pinned批释放后按新任务实施，不边测边改。集成再由真实源生成SDK；请求新版本固定到Revision，不能默认替换旧记录。
- Test：保RV17精确candidate/原红绿不动；新增自动策略标准/拟case版本，分别测基准scope≠per_work、无reference P95=null、没有每条必选标注、未准入/漂移/撤销/差异阻断、严格路径旧反例及一次API/MCP完成。准备真实语料/独立标注计划和MM05资料，交Review独立批准，不以此ADR代标准审批。
- 媒体：消费新端口，产出真实Transcript/Alignment/Mapping/Subtitle与WorkValidation材料，质量意见/局部修订继续同预算；不得造reference/report、改账本或自行签authority。没有资格时可测真实阻断，但不能称完整自动成片通过。
- 集成/评审/验收：固定实际资源/算法身份和资格资料、不同OS范围；审批真实基准/authority及标准，独立实听/实看并验收默认自动路径。缺外部人员/语料继续记pending，不跳门或把人标工作丢给每个普通使用者。

本轮未修改测试/生产/锁/SDK、不下载/联网/读key/收费，不批准当前authority或真实产品pass。全部读取终态后正式交接释放；完整自动制作、多模态交付/引用检索、三OS及R1后连续R2仍在总目标。
