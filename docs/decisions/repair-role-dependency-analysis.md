# 局部媒体修订：配方依赖与写出角色差异分析

状态：ANALYSIS_FINAL_AWAITING_INDEPENDENT_REVIEW，2026-10-11。本文不批准角色范围变更或被拒补丁；仅第6节是ADR0056真实结果消费的必要私有接口具体化。原0053/0054/0056、标准、生产源码、审批及账本字节不改。没有运行产品、SQL、模型、媒体、测试、联网、安装、密钥或费用。

任务2f09b40672402f0adcf1665c63fdfb9ade64607c0d538880c1413103554045de；补输入6818102e515977217e3216b6e9417c3b44d937798ba2b43a284c83e5fb28c23f。固定身份、完整ordinary源及必要读段在Architecture/RepairRoleDependencyAnalysis/InputPins.json。Backend118索引db340317…；拒绝Gap a3940fa2…/63d0a972…两份旧普通源分别5d502bf9…/658f03e2…，不能混称最终118。独审c7a65b99…保持原source-static结论，B118-P01另归Backend，不在本分析修复。

## 1. 实际结论

已有选择输出源码与已批准目标的配方不同步，video-only尚未形成可运行的完整受控链。旧exact检查正在拒绝原clip ambient参与混音的范围失配；不能为此把dependency截成交集或把等式改subset。0053“纯画面不重TTS”和0054“真实配方映射/按选中角色输出”要求完成视觉修订能力；它们没有授权用旧plan hash/approval重新解释其依赖。

Media37快照80185a86…与38快照af99a993…中四件实际完整ordinary hash相同：affected_production b27f7955…、production_drivers de95cd8a…、production_edit 9f2c2f2b…、wan_video 91502007…。不是只依据作者“未改”声明。没有新runtime证明。

## 2. 四种集合必须分清

- 输入读取：真实源clip、旁白或原混音、原video、稿/分镜、时间轴和资源。读取需既有本地范围及许可用途；读原mix不意味着可生成新mix或授再分发。
- 组件输出：Wan的shot_clip本身可含ambient音轨；它是原已批准组件和原Operation成本的真实输出，不能仅因最终不写mixed_audio便称没有产生clip音频。
- 配方影响的最终角色：当新clip音轨进入bed，mixed_audio及video会变化；首clip的第一帧还影响cover。当前dependent_media_roles表达这种重新执行影响，而非一般“读取哪些文件”。
- 当次允许新写：changed_media_roles/真实failed材料与已准plan目标共同限定。其外母版保原Asset ID、完整SHA、size/MIME、decoder时钟和lineage；新video虽然用了同mix，其AAC嵌入轨是新video的实际编码事实，不能冒称原encoded track未变。

| 固定实际配方/分支 | 读取与实际行为 | 新最终输出 / 保留 |
| --- | --- | --- |
| 初始full edit | 三clip画面/ambient＋speech，concat bed、amix，再把同mix嵌入video；首帧出cover | video/mixed_audio/cover；旁白由独立TTS提供 |
| affected且remix=True | 新/原clip＋实际旁白，重新bed/amix | video/mixed_audio，必要时cover；无另行准TTS不重旁白 |
| affected且remix=False | clip只读画面；原mixed_audio直接进入新video，不建bed/amix | 选中video/cover；原mix、旁白及未选cover保留 |
| only-cover源码分支 | 解码原preserved_video取第一帧 | cover；三个其他母版保留。整链是否能产生合法此proposal未验证 |

真实源码：plan_repair_service20–133把narration投影为video/narration_audio/mixed_audio；首shot为video/mixed_audio/cover，其他shot为video/mixed_audio；edit模板输出video/mix/cover。其174–269在恢复/writer核原完整plan、target IDs/body/input SHA和人审/政策。Gap authorizer343–463及118版本420–429要求依赖等于changed roles且不超actual failed roles。production_edit完整正文的remix=False已有上述选择输出，但没有与旧目标区分的可信recipe身份。changed_media_roles参数只是数据，不是配方准入。

## 3. 当前应拒与条件可能匹配，均非运行成功

| 请求 | 当前静态判据 |
| --- | --- |
| 旧plan下video-only或video+cover、选择shot重新生成 | clip依赖仍含mixed_audio；exact不等，guidance_required。不能截掉mix后继续 |
| 旧plan下晚shot的video+mixed_audio；首shot的video+mixed_audio+cover | 该配方等式可能匹配；仍须真实failed范围恰覆盖、shot来源、整份plan admission、当前rights/route/resource/预算/unknown及原writer全部成立。未测试 |
| 声音改变却要求只输出narration或保原mix | 已有依赖还含video/mix，应拒；没有“保mix”理由可隐去已改变speech |
| 只改cover | driver有源码，不能据此宣整链支持。Backend先要求真实failed units推导shots；Media仅在pure-video条件映射shots，二者还需独评可达性 |
| 未准shot、time/duration、源稿、route/资源或角色；缺真实failure/目标 | 拒绝。质量approve、选择输出bool、model建议不授生成 |
| 原Operation unknown/partial、撤销/过期/旧fence | 原reconcile/当前拒效果；不换key/Run、清unknown或建新预算 |

另一个需原Review确认的具体一致性项：Media affected_production109–125仅在video且无narration/mix时填写failed-unit→shots；Backend authorizer381–386对所有提议比较真实failed ranges→shots。组合音频修订和cover-only的自动proposal可能在角色等式之前已失配。这里只登记source-only条件，不改shot检查、不猜合法正向或重标运行失败。

## 4. 完整方案比较：没有方案在本卡生效

| 方案 | 对原权源/恢复的影响 | 本卡结论 |
| --- | --- | --- |
| 维持旧full-ambient exact | 不改旧plan/command/审批；匹配依赖的既定请求可继续原guard | 作为旧版本兼容底线保留；不能当永久拒绝纯画面即R1完成 |
| 被拒intersection/subset | 将同一旧目标重新解释为更小写集，恢复不再同等式；旧hash不能证新行为 | 原拒绝仍有效，不应用/重试/换工具/建议等价绕过 |
| 为失败顺带重做mix或全部母版 | 超出actual failed/批准边界、成本/音频证据可能变化 | 拒绝，不能拿“依赖”自动扩生成或以all-master fallback省实现 |
| 显式、独立版本的视觉保mix/封面配方及新不可变投影 | 将实际选择输出模式连同源/资源/成本/保留事实明确纳入新target和整份plan admission，旧记录不改 | 可供独评的候选；不是已批准patch或既有授权的自动等价解释 |

候选差异必须完整准备，不能只换版本名后执行旧subset：
1. Backend唯一strict新投影/plan dispatcher需显式绑定有限recipe ID、实际producer/source/import/installed资源完整身份、原route/body SHA；候选至少区分ambient-remix、visual-preserve-mix、cover-from-preserved-video。Media不能用运行时changed_roles任意选配方。
2. 每个候选variant固定原source target/shot、整数微秒timeline、实际input模板SHA、prerequisite IDs、必须读取/保留的父角色、恰允许新写角色、cover来源规则。计划中的“父mix角色引用”只作封闭定位规则，不能造未来Asset ID；实际command才受控绑定其父Asset/文件/clock。所选target写出闭包与当次允许写集仍exact一致，并仍必须全部属于真实failed/原有限审批范围。
3. visual-preserve-mix不执行TTS、不用新clip音轨参与mix，不分配mix/narration输出；所有未改clip用原successful Step及真实完整文件。改变首画面且配方要求新cover时，范围须同时允许cover，否则拒绝，不能暗留失配封面或自动扩范围。新video完整duration/encoded音轨→原mix实际mapping重核，许可/WorkValidation/字幕/RAG/成片报告随新作品重建；不得拿旧视频编码clock当新clock或靠旧ASR音频证据宣布整个新作品精度通过。
4. 新recipe即新行为身份，不能回填旧projection/旧command或借旧approval适用于新target。新作品可在已真实覆盖该完整新plan的Owner预授权下自动admit；interactive保持真实整份plan approve。已有作品改变配方按0054 expansion原实际修改/审批来源处理，若原流程创建新Run不能伪装同Run修复。缺对应权源时具体guidance，不伪造人审或永久要求全部自动用户手工处理。
5. 旧v1/v2投影、commands/approvals、已settled/READY bytes和原Goal canonical不迁移改写。新版本必须显式dispatch，共用同严格resolver贯穿initial/恢复/preclaim/observe/child/verify/publish；旧非匹配命令仍拒绝，unknown只原核实，不新key重发。预算、修订counter和一child原子幂等继续。

## 5. 独评与必要批准点

先交原Review核本分析、四recipe源码、两处exact门及自动proposal shots一致性，判候选是否明确改变授权行为/原合同语义。再由原架构独立卡冻结新版本字段、注册与迁移兼容；任何需调整原权限或被拒边界的步骤取得具体审批前不得实施。本卡不替自动审批或法律许可作决定。

Backend准备唯一新目标/recipe来源与guard差异；Media准备actual selective source/网络payload/输出与原资产证明；Integration准备真实source/许可/安装coverage。禁止改旧exact以迁就未映射配方。后继Test由其owner准备/独评判据并获实际运行范围后验证：
- 合法视觉修订只新video/必要cover；原mix/narration/其他clip ID、SHA、clock不变且无TTS/mix allocation或Operation；新video完整decode/音轨mapping/同步与成片实际看听。
- 已准组合remix真实正向，以及未准mix/cover/TTS/shot、错recipe/hash/资源、超failed范围/时长/输入、policy撤销/许可过期/old fence全部拒，不能仅测试集合公式。
- Media提议与Backend范围独立重算一致；失败范围没shot证据不能fallback全部shots；only-cover可达性单独证明。
- 真实settled→commit/child kill恢复不重复Operation/成本/counter，未知不重交；复制祖先/未变材料取得合法新receipt但不重生成母版；原两authority第二false403、200ms/MM05、null来源及rights完整闭包保持。

完整R1五步、API/MCP一次可信预授权到视频/音频/文本/RAG/Bundle、本地免注册/BYOK、三OS/Intel及连续R2均OPEN；没有把Wan缺配当所有本地路径必须登录或只能导出。B118-P01由原Backend另修，0056当前CTC实施另链不受本候选等待阻挡。

## 6. ADR0056必要消费具体化：初始真实MethodEvidence

仅此节批准原0056“真实CTC结果及方法来源”的最小私有实现具体化，不授任何role方案。初始assembly必须CTC前持久，其methods/body/sourceSHA保持不可变；不提前造operation_id。完整manifest的期望方法列表由同Backend共享resolver重建为：原assembly.methods原顺序＋恰一个同注册initial alignment成功settled Operation、已commit Step及真实输出绑定的CTC MethodEvidence。不能把严格相等改成泛superset或“有alignment标签即可”。

若原三元read getter不能向Media提供真实ledger Operation关联，允许同CurrentFinalEvidencePorts增加最窄private registered_initial_alignment_method(ordinary_lease,preparation_id)->既有c.MethodEvidence。Backend从原持久registration/request/Step/Operation/manifest实际构造；不接caller方法对象、不新DTO/authority/公开route、不改原八方法签名。返回是只读来源事实，仍要本次真实port/current lease/thread/fence及同preparation验证，不首次dispatch。

初始actual ASR、preparation/intent、request/full input/route/resource/config、实际CTC output文档ID/SHA和原Operation/Step/settled结果必须精确闭合；不得从Media日志或hash猜Operation ID。Media消费这一已有typed method事实，不能任意追加manifest方法。shared reader/verifier、正常verify与publish均用相同exact expected列表及当前两authority；原context/hash、原READY文件/Observation账本不回填。缺真实Step/settled结果、不同prep/audio/config、额外方法/旧fence/资源撤销均拒；Op成功Step未完成只补原commit，不能先宣方法完成。是否真正实现/兼容由原Backend与Media后继固定源、独立Review/Test验证。
