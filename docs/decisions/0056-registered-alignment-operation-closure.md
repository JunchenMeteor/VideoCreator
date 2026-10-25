# ADR0056 — 初始／受影响对齐的原 Step／Operation 与 held 输入闭包

- 状态：APPROVED_CONTRACT_ONLY；2026-10-11。仅批准原 Backend／Media 实施既定0053／0055的初始与受影响私有对齐接缝，不证明运行、平台、分发许可、200ms或完整R1／R2已通过。
- 任务卡 RegisteredAlignmentOperationContract，SHA d8c3ae479edb36459ee2df98c6526111a2f6146008c660e693c40bfad15082b4。0053／0054／0055原字节不改；被拒role intersection/subset不属于本卡，也不以新分支绕过。
- 没有产品import、Pydantic实例化、SQL、provider、模型／ASR／native执行、网络／下载、密钥／费用、安装或第四目标测试。

## 1. 实际固定来源与初始路径

Backend118停止索引db3403175d6bec860cbe4b9aacc9a07300d1d1e9387c3b481a4a6b815baeda1f；Media38停止快照af99a9939734da9bee1ba8d2d5a3ffd2b50dc904abae095e0bab395a81f1c600。完整普通源身份在本人InputPins／SourceAfter；关键事实：

- affected_repair_service.py（92a70eea…）：365—522已有真实报告、原ordered failed units、原claim/current、human/policy来源和本地合格route；465—475仅为regenerate构造steps，realignment实际为空。74—97对Execution作原service object／lease／thread／fence和完整command查验，不能由JSON或新dataclass替代。
- affected_step_guard.py（1d75149a…）仅识别generation和child-ASR命名空间，核主command、current plan targets和原journal；domain/affected_repair_steps.py（01795af6…）只允许四个generation stages。添加对齐必须是独立严格分支，不能放宽这些分支。
- CurrentFinalEvidencePorts（b1069678…）每次查实际service registry／thread／ordinary lease；原executor（b4b9c89f…）先prepare／claim再invoke，settled回原Observation，非prepared不重交。
- Worker（5058afc2…）493—548有持久OutputReservation和finish_output；550—607的媒体commit经过MediaProbe／Asset importer。对齐JSON不得伪称媒体Asset或送给音视频decoder。
- 当前bundle_producer.py（4c12154f…）232—292实际调用原ASR，再复制其语句边界生成AlignmentRevision，明确precision=not_measured；375—376审计也说明word estimates不是forced alignment。当前没有初始CTC调用／Operation，不把本卡新repair接口当它已存在。本卡新增下述初始CTC独立来源分支，保原真实ASR来源，不把其估计值当CTC，也不伪造失败report或repair command。旧strict仍需真实reference／measurement；0.3/null仍保实际资格/runtime报告。bundle_v03.py（69e31a91…）109—237实在第184行prepare原材料、后在234—237行计算measurement：Media应在初次prepare及真实源持久化后、measurement计算及首份最终文档READY前接CTC，而非先READY后覆盖。

Integration取得0055固定alignment源码／许可和实际资源后才能做driver；其artifact下载或inspector状态不能推定资格。全部Win x64、Mac arm64＋x64、Linux x64和147＋24能力仍保留。

## 2. 唯一私有接口与类型

在实际CurrentFinalEvidencePorts上新增下列方法，均先调用原_current，委托同一个BundleService／AffectedRepairService；Backend唯一类型、grammar、存储、guard和实现。没有公开HTTP／MCP动作、第二OperationIntent／Execution／审批DTO、新Engine／Worker或caller可安装authority。

| 接口 | 唯一返回／作用 |
| --- | --- |
| registered_alignment_intent(ordinary_lease, execution: AffectedRepairExecution) | 既有c.OperationIntent；仅真实requested_action=realignment，绝不None成功／generic key |
| registered_alignment_request(ordinary_lease, execution: AffectedRepairExecution) | 不可变canonical UTF-8 bytes；下述sole私有数据grammar，不是权限。服务从原持久记录返回，不由Media拼正文 |
| commit_registered_alignment_result(ordinary_lease, execution: AffectedRepairExecution, *, files: tuple[GeneratedFileManifest, ...]) | 既有c.AlignmentRevision或c.AlignmentRevisionV03；从真实原Operation读取Observation并受控完成原Step，caller不传Observation／成功bool／Asset IDs |
| read_registered_alignment_result(ordinary_lease, execution: AffectedRepairExecution) | 既有AlignmentRevision对象、GeneratedFileManifest、OperationObservation组成的固定三元组；只有原成功settled记录／实际完整输出可返回，否则具体missing／commit-required／reconcile错误 |

这些读接口不首次authorize、不创建Step／输出／Operation、不修改预算或child；解析bytes只得到数据。type相同或hash相同仍不替原held/current检查。commit只提交已真实发生的原Operation输出，不推理或重新dispatch。

registered_alignment_request的唯一私有format为registered-affected-alignment-request-v1，extra禁止、strict、无秘密。Backend使用现有ProductionBinding、MaterialReceipt、RevisionRef、AudioTrackRef／AudioTimelineMapping、AlignmentUnit、MethodQualificationRef及原实际转写类型作为成员，避免重复公开类型。正文精确成员：

1. format、binding、repair_command_sha256、parent_preparation_id、parent_intent_sha256、source_report_ref（仅定位身份，绝不携带reference/predicted对照报告正文）。
2. audio：原混音Asset ID、完整SHA／size／MIME、实际decoded input_track（sample_count、sample_rate、duration等原clock）、原source→timeline mapping对象／内容SHA。原四master和音频不改，不以相同ID或猜路径代相同字节。
3. transcript：原ActualTranscriptRevision ID／content SHA、实际READY transcript文档receipt／文件SHA、语言、immutable actual text；approved script原RevisionRef／完整SHA与实际原ASR Operation／input／完整validation context的引用SHA，用于来源核定，不重做ASR。
4. unit_sources：按原验收units保存原alignment_unit_id、transcript_unit_id／utterance_id／word_id（适用时）、原text、在其原字符串内Unicode scalar半开span、原预测区间和原单位顺序。failed_unit_ids为实际报告产生的原ordered subset；allowed_unit_ids为Backend核定的必要边界一致性闭包。不得由Media扩充、按英文空格改中文单位或凭reference时间找窗。
5. source_alignment_revision_id／content SHA及原单位预测边界；这些是既有预测的上下文，precision／独立reference／gold边界／通用benchmark成绩不进入推理数据。source report只供Backend生成failed subset及质量验证，不能交driver当答案。
6. alignment_registration：原ForcedAlignmentRegistration及实际完整route SHA；resource_manifest_sha256、runtime_manifest_sha256、alignment model revision／逐文件SHA、configuration_sha256、worker／runtime固定资源身份、license_artifact_ids、method_qualification_ref及其原source identities。它们来自当前held source／resolve，不由caller填、布尔ready或配置hash授资格。
7. output_alignment_revision_id：Backend一次分配并持久，重读不换ID；输出采用原AlignmentRevision schema family和原units。没有output内容SHA、attempt路径、wall time、当前lease fence、cancel或deadline进入这个稳定请求身份。

严格检查text／span／ID可从原完整READY文本和单位唯一恢复；不明映射是具体source缺失／不可对齐，不猜稿、不改词。资源配置沿0055固定CTC、离线加载、CPU和中文映射；qualified ref须覆盖实际driver configuration及受影响单位保留／合并行为。没有该实际资格时NOT_READY，不能拿完整CTC基准自动替一个未验证混合方法。


## 2A. 初始CTC：同一端口，独立真实来源

初始路径不是受影响修复，没有failed report／AffectedRepairExecution、child或revision_cycles。实际production v2制作使用初始CTC；旧已settled／READY的ASR估计文档不改字节、不标CTC，通过原真实报告门决定是否需要既有repair。唯一CurrentFinalEvidencePorts另提供以下四个明确私有方法，原类型仍由Backend维护：

| 接口 | 作用 |
| --- | --- |
| register_initial_alignment(ordinary_lease, preparation_id: str, *, transcript: c.ActualTranscriptRevision, prediction: c.AlignmentRevision或c.AlignmentRevisionV03, mapping: c.AudioTimelineMapping) | 返回既有c.OperationIntent；真实初始源登记及exact replay。三个typed值是待核数据，不是来源权或执行权。仅未提交首份最终转写／字幕材料的原initial preparation可首次登记 |
| registered_initial_alignment_request(ordinary_lease, preparation_id: str) | 返回服务已持久的唯一canonical UTF-8 bytes，不首次登记或分配。preparation ID只作定位，仍核原port／lease／sameRun／current源 |
| commit_registered_initial_alignment_result(ordinary_lease, preparation_id: str, *, files: tuple[GeneratedFileManifest, ...]) | 返回原AlignmentRevision家族；从真实原成功settled Observation受控提交原Step，复用§4的JSON输出验证和短writer规则 |
| read_registered_initial_alignment_result(ordinary_lease, preparation_id: str) | 返回同样固定三元组AlignmentRevision、GeneratedFileManifest、OperationObservation；纯读原成功完整事实，不推理或新建Operation |

原公开OperationIntent、Goal、approval、Bundle schema不新增；不把preparation_id变公共授权字段。四个affected方法仍只接受原held Execution。共享端口和实现内部验证，不使用一个宽generic action／key把两种权限来源混在一起。

**真实初始来源：** Media保原successful settled ASR Operation、其真实输出allocation／canonical validation context和独立decoder音频时钟／mapping。Backend通过原受控ASR read与实际source registry取回原结果，比较传入transcript/prediction：actual text／language／segment和word ID、原估计边界、input audio完整SHA／duration及原approved script RevisionRef必须对应原actual result；content SHA按原schema核验。原ASR粗边界只作推理上下文，不是CTC或独立精度。无法从原settled结果唯一恢复的调用者ID/单位转换拒绝；稳定document／transcript／mapping IDs可由原producer一次分配，必须先与实际preparation及原assembly固定持久，replay不能换ID。没有原ASR context的旧记录保持真实missing，不能重新ASR或猜context补登记。

Backend另核实际original preparation intent、原四master当前字节、请求／版本、真实committed与admitted plan、原human或policy执行来源、ProductionRightsFact、原许可与alignment route范围、services实际安装资源身份及method资格；复用原已批准强来源，不由三个模型值、仅qualification或配置hash授制作权。原CurrentFinalAssemblyContext/V2及其correctionPair沿0052/0053真实来源持久到同preparation；独立reference可以原材料链留存，但gold／measurement正文绝不进入CTC请求。不得给未READY的transcript虚造MaterialReceipt。

**初始sole grammar：** registered-initial-alignment-request-v1，Backend strict／extra-forbid。成员固定为format、binding、preparation_id、preparation_intent_sha256、assembly_context_sha256、asr_source（原Operation ID、input/route SHA、实际result allocation/full-file SHA、原validation context ref/full SHA）、audio、transcript、unit_sources、source_alignment_revision_id/content SHA、alignment_registration、output_alignment_revision_id。audio／transcript／units／registration沿§2真实成员；transcript来源改为asr_source＋未READY的真实typed transcript内容，不含假READY receipt。unit_sources完整覆盖当前实际初始单位；allowed_unit_ids恰其完整有序集合，不带failed_unit_ids、repair_command_sha256或source_report_ref。预测precision/gold不进入正文。原mapping完整字节／content SHA、approved script全文来源、runtime资源/许可与qual refs均绑定；不能只填route名。稳定request不含此次fence／wall time／attempt path或未来output SHA。

持久初始record为metadata key current_initial_alignment:<实际preparation_id>，format current-initial-alignment-binding-v1，存完整初始grammar canonical_request_utf8／SHA、实际preparation intent及assembly/ref SHA、一次分配的output_alignment_revision_id和同Run源身份。canonical与§3相同。step_key与dedupe_key均为bundle-alignment-<完整request SHA前32位>，input_sha为完整request SHA、route为实际登记alignment route、原free-local reserved_cost=0；short key碰撞仍核full SHA/body/route并拒绝。记录不含其自身SHA／Step状态造成循环。registration／original IDs／必要assembly source在同原writer持久，恢复无需再次identity()或第二Bundle.prepare。初次real source登记与current scope重核明确先于效果。

§4的输出/原executor/真实Worker/settle/commit规则完整复用；唯一新增**initial Step guard**在begin／prepare／claim／commit／短writer核原当前安装services、真实initial登记与原preparation/ASR/context/plan/rights/route/资格及当前lease/fence。它不调用affected journal／_claim、不伪造FinalEvidenceControl或Execution、不放宽generation/child-ASR分支。每次强current仍来自原service来源；JSON/prefix注册仅数据。实际operation result_json对初始返回request_sha和preparation绑定，取代repair command；成功原file内保新alignment ID、原实际transcript/text/audio/units，全体合法单位通过本次CTC，不把ASR边界fallback成功。

**Media初次实际顺序：**
1. 原ASR成功settled及完整context→真实decoder、actual transcript和原粗alignment/mapping；一次固定bundle/revision/document IDs，原Bundle.prepare（v03沿prepare_v03_evidence）得到原allocations。先持久原initial assembly/IDs/context。若模型/资格还缺，保这些原事实与具体等待原因，可信恢复后不第二ASR／prepare。
2. 在prepare_v03_evidence中，将本片measurement与其报告生成移到CTC结果以后；原独立reference绑定／来源校验、correction许可及现有来源材料READY可以先完成，不能把它们传driver。没有reference的自动0.3分支不新增人工材料要求。不要用后置P95成绩授权前置CTC。
3. register_initial_alignment→getter→原strict initial guard begin→§4恰一个真实allocation／原prepare/claim/permit／本地CTC／settle／private commit。未成功完整时不写首份final transcript/srt/vtt/segments/RAG READY、不finished；初始不加修订次数或产生child。
4. 用真实CTC alignment生成原subtitle cues/quantization与派生文档，再算原per-work validation／precision（独立reference存在时）及两次authority；然后首次原MaterialAllocation READY和原Bundle验证/publish。原corrected intent、rights／source／methods／报告沿真实链，不丢authorPair。真实P95>200ms仍原有界repair，不把CTC运行当精度通过。

首次登记前无独立method资格／实际资源时返回具体NOT_READY并沿原可信blocked/final-evidence等待/恢复路径继续，不能把缺CTC资源写成未知Operation或永久stub成功。已effect后按§5同Operation恢复：settled成功但Step未完成只补commit、Step已完成只读原输出并复用同preparation/材料；pending/unknown/partial走原核实不重推理。旧未持久initial源不能猜UUID/context补效果；旧READY估计只能依其真实版本报告读/已有合法repair。新initial源撤销或替换仍拒新效果，历史读不等当前授权。

## 3. Command、canonical与持久注册

保留原主command format／SHA计算及完整route/resource/parent/failed/plan/current绑定，不将新的随机输出、Step或输出SHA回填主source造成哈希循环。新的alignment完整数据在同短writer写不可变伴随记录：

- metadata key：current_affected_alignment:<完整repair_command_sha256>；
- format：current-affected-alignment-binding-v1；
- 记录canonical_request_utf8（或同等精确JSON文本）、request_sha256、主command完整SHA、原route/qualification/resource来源身份、一次分配的output_alignment_revision_id。内容必须从真实parent/readset/current sources取得；key本身不授权限。
- canonical request bytes：对严格typed JSON递归编码，UTF-8、ensure_ascii=False、sort_keys=True、separators=(',',':')、allow_nan=False，保显式null／实际默认值／数组顺序。SHA256为完整bytes SHA；沿原私有recursive encoder，不调用仅收BaseModel的engine.canonical(dict)，不改全局Goal canonical/digest。
- 原command.steps增加且仅增加一个五字段descriptor：stage='alignment'、shot_id=null、input_sha256=request_sha256、dedupe_key=step_key、route_id=原alignment route。唯一step_key='repair-alignment-'+原commandSHA前32位，由Backend生成。全SHA、route和正文同时验证，截短碰撞／不同payload一律冲突，不由Media按字符串造key。
- 当前realignment只能这一个alignment Step，不存在generation／master-index／new-ASR Step，也不改changed_media_roles、原failed范围或原活动任务。

原authorize_affected_execution扩展realignment分支：SQL外取完整READY字节、实际音频与mapping、source文本、原配置／资源／许可／资格，保持真正held guard；SQL内重核原_claim／Execution／主source／current plan与quality及human或policy来源、原route范围、journal、parent与源rows。原command／伴随记录／descriptor原子写入，exact replay返回同一事实；预检后源改变仍拒绝。随后与prepare／claim／commit短writer中的guard核定一致，不能只在getter验证一次。资源／文件检查在SQL外，不在writer做模型推理或联网。

原命令兼容：generation、child-ASR、原Goal和旧报告字节保持。对旧realignment steps={}，不默认全局迁移或改主command SHA。只有同原runtime以真实当前repair continuation再authorize，且没有selected child、原alignment Step／Operation／output效果时，才允许在上述current writer为同主command补完整伴随记录／单descriptor；重核actual原来源，不猜缺失context。已有child／effects而无登记保持真实missing/reconcile，不能adopt、伪造或换key。已完整注册但资源替换／撤销时旧记录可历史核实，不能继续新效果；再制作依原current范围和既有限次规则明确决定。

## 4. Step／输出／原Operation的实际顺序

1. Media保原services／execution_ports对象，复用原guard及当前AttemptControl；先取得实际held Execution、parent readset和sole intent／请求bytes，再查与原请求／fence／registered source一致。它不得创建Execution／permit或从model JSON得到执行权。
2. engine.begin_step用返回原intent的step_key／input_sha；新增alignment专用assert_affected_step分支，每次核one main command＋one companion＋descriptor、原realignment／parent／report／journal executing当前fence、实际source/resources/route/qualification和原human/policy current。generation分支的exact角色拒绝不变；保原prepare／claim强guard，不把新prefix当allowlist。
3. 用原Worker.allocate_output分配恰一个output_key='alignment-result'、media_type='application/json'的持久OutputReservation；无caller path。同Step/input/输出键恢复原allocation，不开新key。它是对齐数据输出，尚不是Asset／Bundle READY。
4. 原0055 builder消费Backend请求数据和这一真实reservation，得到原BoundProductionDriver；仅在原executor已prepare／claim给真实ExecutionPermit后invoke。当前cancel／deadline／held process identity与离线资源检查照原控制。request_payload必须为原解析正文，不能另有未登记单位／audio／model；Backend guard核固定输入，不能假设原executor对所有local route已有Kimi式payload校验。
5. worker在原.partial fsync＋原completed_path原子完成；原finish_output产生GeneratedFileManifest；driver返回真实OperationObservation，result_json含原generated_files、原request_sha／command与actual method/runtime执行事实。输出完整AlignmentRevision家族：原实际transcript/audio，新的一次分配alignment ID；仅允许集合内边界改变，集合外原单位ID／顺序／边界和来源不变。原文本、clock/mapping、四master字节均不改；实际变化和未变来源分别在原audit／MethodEvidence明确，不冒称未重算单位已做CTC或全片测量。
6. executor.observe／settle完成原Operation。成功confirmed_no_charge来自真实free-local规则与实际执行，不将unknown费用写0。pending／unknown仍原核实，不创建新key／新Run／ASR或另修订重交。
7. commit_registered_alignment_result在SQL外读实际原settled成功Observation、精确file manifest／实际bytes／schema／semantic content SHA与full-file SHA、输出JSON限制、原unit／audio／clock／mapping／method及resource/source current。不得调用commit_generated_media_step或假MediaProbe进口JSON；不产生媒体Asset IDs。
8. 其短writer从原Operation和generated_attempts重核exact Step/input/route/dedupe／settled／Observation manifest＋held current／原command＋companion＋当前fence，将既有engine._complete_step以asset_ids=()提交原Step，result_json保存实际输出manifest／文档SHA／source／Operation关联。caller不能提供成功状态。JSON仍是原allocated Staging数据文件；恢复只能从持久allocation定位／验证，不读取caller URL或任意路径。

原precision authority不由这次document验证替代：输出不得标独立precision通过，P95按原0.3无本片reference为null、strict真实measurement判原200ms/MM05。真实失败照原有界repair／guidance；两次真实authority和second=false403保持。

## 5. Child、READY及恢复

成功原alignment Step／settled Observation及完整输出核定后，才调用既有revise_preparation创建原atomic child。Backend在原child writer重核此次actual alignment结果和原command，不单凭services／quality批准：exact parent/child lineage、原affected_artifact_ids、原四master/音频、counter和remainingbudget；一次真实child才加原共享revision_cycles，replay不加第二次，command／Operation不新建预算。

Media把真实alignment结果并入child的原actual transcript／subtitles／semantic/RAG／quality/report等既定依赖文档，写原新MaterialAllocation；无新媒体Asset。未受影响材料完整复制原bytes但取得child新receipt；已READY不能覆盖。原correctionPair作者intent、parent origin、许可/rights和源引用原样传递，不从祖先或reference猜。保selected-child resolver／原assembly persistence／实际report生成／shared verify／publish和两authority；不能将JSON Step结果直接标Bundle READY或finished。

恢复顺序：
- 重新取得同Run的新ordinary lease／services／真实current admission／claim，恢复原command及companion的相同key/input。旧Execution对象、thread/fence或已close port无效。
- Step成功：read_registered_alignment_result只读原真实settled输出和allocation，核当前允许消费，再进既有selected child／材料恢复；不invoke、不生成第二文件／Operation／child／计数。
- Operation成功settled但Step未完成：从原Observation取得原manifest，调用同commit接口补原Step；不CTC重跑。complete Step后的child writer窗口同理只复用。
- 原Operation prepared且从未claim可按原执行器同intent继续；pending／unknown／缺settled／partial或缺manifest必须原reconcile。文件存在／自称operation_id／配置hash不是受理或输出权威。原worker reconciliation driver可核原allocation、实际held生成来源与process终态后记录原Operation；无法证明时保持unknown，不靠本卡放宽核实。
- 原source／资源／许可／资格／Owner撤销或新fence不匹配拒新效果；历史读不等执行授权。音频变化属于原regenerate＋child-ASR另链，本realignment绝不悄悄触发它。
- 缺资源/qualification/source mapping/legacy context是具体NOT_READY／missing，后继补真实材料后由原可信resume路径继续；不能永久stub完成或通过停用旧strict／注册fakeMethod。

## 6. 归属和真实验证

Backend：原application/current_final_evidence.py、current_final_evidence_service/recovery与原Bundle initial guard、affected_repair_service.py、affected_step_guard.py及必要sole domain私有grammar；原engine/worker短writer仅必要接缝。保持public OperationIntent及guards/lease/预算／原approved schemas。伴随记录复用metadata，无需为本卡新建公共表/API；逐版本拒绝不明内容。

Media：原registered alignment builder／affected continuation，仅消费上述两种严格来源的八个held方法和原Worker reservation／executor；初始production v2在首份READY之前接真实CTC；实现0055实际固定算法后，不借generic free provider、caller key或第二DTO。Integration：固定源码/import/license／模型／runtime／安装coverage与实际process包；Metadata-only和源级compile不授ready。Test独测，Review只读评审，Acceptance实看/听后判；架构未做其职责。

后继必要正反证据：真实新注册→begin→one allocation→prepare/claim→CPU结果→settle→one Step→one child/READY/report/verify；成功settled至Step和Step至child的真实kill/restart不能重复；unknown/partial不得重推理；同SHA不同来源／伪Execution/port/thread／错fence／route/model/text/span/audio/mapping／companion/descriptor漂移/碰撞/撤销均拒；无独立gold输入或网络下载；集合外单位、四master及原材料hash保持；两authority第二false403、真实200ms失败不变。初始须独立证明原真实ASR/context→one original preparation→one CTC Operation/JSON allocation→one Step→首次真实文档READY；假ASR来源、初始伪failed report、reference时间泄露、measurement前置授权、第二prepare/ASR/UUID、READY覆盖均拒绝。旧ASR估计事实保持，不叫CTC通过。四平台、实际资格、driver/资源取得及完整R1/R2均OPEN，不借架构批准当运行通过。
