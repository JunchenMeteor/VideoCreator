# 0062 — selected affected child与有限失败出口的原子顺序

状态：DESIGN_ONLY_READY_FOR_INDEPENDENT_REVIEW。只修正0061未闭合的“真实选中子级第一次诊断选择”及“耗尽时pending选择与失败终态”接缝。旧0060 SHA8fc928e2ea0ff418a0ee1cfe998baf5d86873d542989bf2f22f100df114d184f、0061 SHA04b522d08cec343bbd420869f37b949dcd6f301d837dd3bc8319ce071e00776d完整字节不变。本文不是实现、独审批准、运行/模型/费用授权，不关闭CFDJ/BDE或R1/R2。后端唯一定义私有类型与实现，原Review独审本合同后另由统筹分派实施。

## 1. 固定事实、拒绝及需求

基线停止Backend130 SourceIndex41b2f0e2650b10b97a7353a574e5f131164ae9a597d763435df11c5ab912c83d。以下是必要完整方法的源码观察，未执行SQL/Pydantic/产品：

- diagnostic_selection.prepare_current_diagnostic_selection:304–350，在320–326把当前journal准备及source诊断ref与候选的同准备old selected耦合。父修订journal仍指父准备时，合法已提交子级会409。
- affected_repair_service._selected_affected_child:163–193仅验证唯一command/child/lineage及原report/subset关联，不单独证明当前整份plan授权、真实资源、settled、当前Owner或新子级input。
- revise_current_final_preparation:326–494在437–491把child/allocation、lineage、command关联及原共享revision_cycles+1真实原子提交；403/409/422及相同command幂等必须保留。
- 原FullPlan/诊断目标门assert_diagnostic_command_targets_writer:72–194核原plan、脚本/分镜/quality、原diagnosis/source、唯一mapper/recipe、路线、政策execute_plan真实admission或真人全plan批准、当前rights。原precision修订授权386–565也核真实200000us失败闭包、原双action及限次。
- media_registration:754–770在达到实际revision限次时直接调用finish_current_final_evidence_failed；Runtime.finish:368–419只保已提交retain，pending first/successor在retain_failed_diagnostic_selection_writer:411–421真实拒409。
- 原park:94–155唯一等待选择writer，会在150释放lease。不能先单独commit park再用同失效lease调用finish。

原RejectedResumeConversion四件字节保留，原输入8a5f68b24e79f6132edca20cf70cef798c8e23de50ab15d7900a7255b3cb94a8、输出728e1e768b34cc85a2e305177091b59663cba314bc04b4f3c3f8e2164350d3a9；两未落hunk302ae4102a435294b50154f9ef48f51edee017ff0ea326fafd0f7ac3ac65ea00、38eb1c8841e26336718e0d795a35eadcb52584a456ef75063bb8afe6842d0428。自动审批拒绝把needs_reconciliation转成retry_final_validation，因可能绕过账本/状态安全门；两hunk均不重试或拆开应用。本文要求新的完整held来源、持久选择证据及原writer顺序，经独立评审后另派发，不以单调用_selected_affected_child代替完整证明，更不转换unknown。

需求沿FR08/FR11/FR13、01适用AC、09 MM03/MM06/MM07及02/03的限次、保未受影响资产和同账本要求。五步、免注册本地工具/自有模型、安装实例持有、API/MCP已预授权自动完整制作及R1独验后连续R2不缩。

## 2. 状态与writer边界

只有原Runtime.park_current_final_evidence及原BundleService.publish首次无journal/selected路径可以改变selected；无第三selection writer。旧append/唯一input索引仅追加Fact；finish不得自行提交first/successor。父selected历史不会被子级替换，选择key仍按preparation_id区分。

| 实际前提 | 选择与当前账本 | 原出口 |
| --- | --- | --- |
| 同准备已settled新input，尚有允许的有限修订 | 同0061 first/retain/successor；准确journal/source CAS | park→waiting；实际补充后原probe/queue/claim新fence |
| 父journal executing/repair；原command已原子选定准确child；child首次诊断且全部保护当前 | 父selected/source原字节保留；child absence CAS；父current journal整body CAS为child journal | 原park及§3–4真实子级转移 |
| 真子级once wholeverify成功，但child选择尚未commit且父journal仍存在 | 不能借first-publication或复活Verified token | §4真实“选择待提交”park→独立新fence原完整final-validation |
| 原真实repair失败，实际原有限额度耗尽，输入/Operations全部已settled；选择pending或retain | park内部一次提交选择、准确失败journal/source、Run/Production failed | §5同事务terminal；零queue/额外修订/生成 |
| information_required、guidance_required或确缺evidence/resource，没有真实有限repair失败 | 不用revision耗尽冒充该失败 | 原真实等待/补充；原分析次数/预算仍受限 |
| unknown/submitting/unsettled/待核实 | 不提交新选择或failed，不删除旧失败/source | 原needs_reconciliation；不queue/claim/dispatch/扣费 |
| pause/cancel/真人审核等待、current/权限/源改变 | 不提交候选，原对应状态优先 | 拒绝或原取消/等待；整体rollback |
| 已failed且响应丢失 | 只能读取真实terminal结果/历史 | 不复活lease、不自动重新queue或重收费 |

## 3. 真子级held来源：不删现有同准备门

保现有同prepared first/retain/successor逻辑及325 source==同准备oldref门；跨准备只能走明确子级来源分支。Backend在原prepare_current_diagnostic_selection内，由真实已读current journal自动决定是否需要子级proof，不能接受Media/模型的allow_child、parent_id、expected_old_body或Bool授权。普通不匹配仍原409。

新增唯一私有helper：

prepare_selected_affected_child_transition(connection, lease, *, current_parent_journal, child_preparation_id, recorded) -> PreparedSelectedChildDiagnosticTransition

该方法只由原Bundle/Selection service调用；不自开写事务，不开放公共API/MCP或让Media构造。返回eq=False、同服务/lease/fence/thread、原30秒且真实来源登记的held事实。参数必须和该connection准确原metadata body重读相符，模型/序列化journal不是身份。recorded.fact.parent_preparation_id这个旧字段仍须等于“正在诊断的child准备”；另有真实lineage父准备，两个概念不混淆。

必须实际读取、核全部并捕获整行/准确body：

1. 原current父journal/body/source；同binding/Run/Production/request，phase=executing、resume_mode=repair、真实lease fence，原repair来源/affected闭包。父selected完整body/ref与父source/journal准确一致；diagnosed分支不能把缺source当普通路径。普通precision父无诊断source/selected，只允许其真实absence和原完整report失败snapshot，不造父diagnostic ref。
2. 一条准确已登记affected command及child association，_selected_affected_child核的原lineage；实际parent/child intent原字节/SHA，child allocation/READY。不能只按childID存在或在所有command挑latest；唯一性、原source/failed units/recipe/subset/commandSHA均保持。任一真实别的command/child/版本409或422。
3. 原command源的当前整份plan、必要脚本/分镜/quality、原真实failed report/diagnosis及单mapper/target/路线。复用原assert_command_targets_writer，不以lineage代许可。policy分支原execute_plan与continue_bundle_validation admission/current；human分支真实whole-plan approve及声明/current；不把policy伪人审或把quality批准当媒体许可。
4. 原注册production services与资源/current许可、原父/子master真实性及未受影响资产，当前child ASR/CTC/完整validation来源。核实际command限定的Steps/Operations/observation/settled；全Run require_settled。任一unknown先原reconcile，不能只核本片新diagnosis Operation。
5. child唯一registered diagnostic input/result index/原不可变Fact，actual child candidate/assembly/报告/mappings及实际一次wholeverify或真实恢复分析来源。append后未选择仍只是候选；input盐值、旧父input冒child或新route不接受。
6. 当前Owner/request/action、原预算/unknown/原实际计数，以及父/子/source所有capture在原writer final再次核。新增proof不增加预算、cap、路线或制作权限。

held须含parent journal完整body、parent preparation/intent、父source完整body/ref或真实absence、父selected完整body/ref或真实absence、command/lineage完整body与bounded metadata refs、child intent/READY/Operation/输入/记录、原真实权源与资源/current captures。这些私有捕获不是可序列化grant。必要的原父诊断只读组合由Backend从原已登记服务来源重建，Media不执行SQL、制造AffectedRepairExecution或模板批准。

仅允许该准确child初次absence；旧legacy record已合法给child选中相同ref时可准确retain。child已有不同ref不能把父source当child successor许可；按原同child已commit的changed-input恢复门处理或409。跨孙级/不同Run/namespace/任意child不泛化。

## 4. 子级park与持久读取一致

在原park current_guard和同短connection中，先核§3全部parent/child/current、old父journal/body/source、父selected body和child selected absence/同ref、new input/index/Fact/settled，再调用原commit_current_diagnostic_selection_writer(...transition='park')。_selected_affected_child及FullPlan/rights不是放到选择已可见之后补审；任何后续拒绝均同事务rollback。

CAS：
- 父selected保完全原字节，不UPDATE或clear。
- child SELECT_PREFIX absence INSERT；合法legacy同refretain只核准确body。expected absence或整body失败409。
- 唯一current Run journal从真实parent executing完整body CAS为本次实际child snapshot；不能另建Run、假continuation或直接修改journal preparation_id。
- 新source与new exact journal SHA同connection写入；before/final source captures含command、lineage、父selected/source、child input/index/Fact和原全部保护。只替换自己CAS确认的新child selected及current journal整行捕获，其他父或资源行不忽略。

为准确区分“父已有诊断选择”与“child此前无选择”，新增唯一严格私有current-final-diagnostic-source-v3，继承v2全部字段和selection_evidence，另增加两个明确字段：selected_child_transition、terminal_failure，均为typed记录或null，至少一个非null。旧source-v1/v2原parser/bytes不改；正常同准备非terminal park仍写v2。无公共DTO/SDK版本变更。

SelectedChildDiagnosticTransitionEvidence确切成员：
- parent_preparation_id、parent_intent_sha256、child_preparation_id、child_intent_sha256；
- parent_journal_body、parent_journal_sha256（准确canonical原body及其SHA，不拿解析后重序列化替原body）；
- parent_source_ref: DiagnosticMetadataRef|null；
- parent_selected_body: str|null、parent_selected_ref: ComponentDiagnosisRefV1|null，两者同时null或真实原正文相符；
- affected_command_ref、child_lineage_ref: DiagnosticMetadataRef，均原准确bounded metadata正文/size/SHA；
- parent_failure_snapshot_sha256、authored_fence（真实parent executing snapshot及本次lease）。

上述parent_journal_body保存原历史；该字段不能单独授权或当当前journal。new source preparation/intent/selection仍必须准确child，新selection old_selected_body是child真实absence/旧same ref，不能填父body。previous_source_ref指实际原父source/null；原source chain不替换。原parent failure report/diagnosis/plan仍从原不可变source/command/lineage闭包读取，不能拷父失败充作本片child的实际测量。

写入时由原held proof产生v3 evidence；纯reader以后核v3严格grammar、parent body/SHA、原source/command/lineage历史闭包和child source/journal/selected/index一致，并重新核当前Owner/lease/fence、child/current资源及原授权。历史父proof只读，不复活父执行权；parent oldjournal已被原子替换后不能要求它仍当前，也不能拿保存body伪造live parent continuation。所有执行/修复仍原当前child及0057 held组合。

合法child once wholeverify成功、Fact为timing_only/no_component_failure但尚有父journal时，不允许publish绕过0061 first-publication absence要求。原join服务从真实HeldDiagnosticOutcome/VerifiedMaterial形成真实“选择尚待提交”assessment，snapshot为CurrentFinalDiagnosticSnapshotV1，child准确intent/candidate/READY/ref，state=waiting_diagnosis、reason_code=final_validation_required、information_requests=()、repair=None；保origin_kind=verified_then_diagnostic_block，不冒充失败或人类缺资料。关联原child held selection，Verified token只在原内存，绝不持久为可复活许可。

原park提交child选择及v3 source，并建立实际final_validation_after_analysis context：准确registered child input/ref、expected child诊断ref、原parent journal SHA/来源及真实completion refs（可空；不假补充）。原无leaseprobe按committed child/settled事实与真实current权限queued，claim新fence后由原Media final-validation分支只执行原完整once verifier/全部authority/QC/rights/current，再实际publish。不是同attempt第二wholeverify，不重新分析/生成/ASR，不消耗修订或费用。若没有真实current continuation/action来源仍拒绝，不能伪queue。若原wholeverify实际失败则保真实failure assessment及报告，不能用这条成功选择等待覆盖。

## 5. 耗尽：在原park事务内选择并终止

Backend保持原park签名，不给模型/Mediafinish_now参数。Worker的v2真实final assessment出口统一进入原park：由Backend从实际held assessment、current request/plan/生产计数计算等待或有限失败，不能在worker外部旧计数读取后直接finish pending选择。实际caller必须处理waiting_evidence、repair_required和本合同合法waiting_diagnosis三种准确状态，并保原result.bundle_ref=None、state==assessment.snapshot.state、preparation_id及materials全文相等、服务held身份门；不是接受任意state或伪assessment。Media唯一维护自身真实result grammar/mapping并消费该服务assessment，Backend不代造Media结果。旧finish调用可保留已committed retain的独立失败出口，但永不提交first/successor。

terminal predicate必须全部为真：真实服务-held assessment/current snapshot有原允许的finite repair且非guidance_required；源确为真实失败/完整原quality或precision闭包；全Run settled；当前Owner/request/action/resources；production.revision_cycles达到实际原effective cap。effective cap取不可变request max_revision_cycles及实际批准整份plan/repair projection更窄cap的min；legacy无已登记额外cap时只取原request。不从模型建议、max值/新Run/改配置推cap，不增加或重置counter。information/resource等待、无repair的选择待提交、成功token都不满足failure predicate。未知输入不能算“已用完故直接失败”。

在同一个原park current_guard/connection，严格顺序：
1. 原_lease、current/action/human pause/cancel/wait、reject_conflicting_wait、require_settled；held assessment、真实old journal/source及选择proof全部重核。捕获实际counter、request、批准plan及cap源，不能先释放租约。
2. 判定waiting或terminal；完成§4/0061原selection CAS，new current journal CAS，准确v2/v3 source。terminal只是在这个park的停止结果分支，不是第三selection writer。
3. terminal journal沿原failed-finalization格式：control=executing、resume_mode=repair、execution_fence=当前真实fence，snapshot保存实际本次failure、blocked_at保原历史；这个executing control是“最后真实claim”的历史，Run/Production failed才是终态，不能用它复活lease。等待路径仍原phase=waiting/无fence。
4. 有真实diagnostic association的terminal写source-v3.terminal_failure，selected_child_transition有真实子级迁移则同时填，否则null；原origin/original_snapshot/quality/diagnostic_ref及previous_source历史全部保。原ordinary失败没有诊断Fact/selection时保持原failed journal及已有source复制/absence语义，不为了v3伪造Fact或selection_evidence；同样在原park有限失败分支完成，其旧非诊断语义不扩大。
5. 所有需要live _lease的最终assessment/selection/整份plan/Operation/资源及两真实authority已有结果来源校验均在lease仍实际有效时完成；自己的selected/journal captures仅按成功CAS的准确new整行替换。最后在同事务写Run/Production failed、worker_id=NULL、lease_until_us=0，写原failed事件并核实际new journal/source/selected/终态完整一致；原真实issuer/current guard必须维持并作最终检查。不以True guard或已失效lease假验证。
6. 任一counter/Owner/许可/body/CAS/源冲突，全部选择/journal/source/终态一起rollback；Fact/index已有追加保持未选定，旧Run/journal/source不被清除。没有可见waiting→failed窗口，也不queue/new fence/再生成。

FiniteDiagnosticTerminalEvidence唯一成员：reason='revision_limit_exhausted'、revision_cycles:strict int>=0、request_revision_limit:strict int>=0、approved_plan_ref:RevisionRef|null、approved_plan_revision_limit:strict int>=0|null、effective_revision_limit:strict int>=0、requested_action（原实际repair行动）、request_sha256、authored_fence、committed_at_us。plan_ref/cap同时null或原真实批准plan，min规则及revision_cycles>=effective cap必核；没有实际来源不造字段。该记录由writer实际数据库/current源产生，仅事实历史，不是权限。journal SHA只向source定位，不有self-SHA闭环。

只finite repair失败才terminal，不能把inconclusive/信息等待按counter强fail。原同输入不得重收费、分析额度/失败限次不重置；合法非terminal等待仍可按真实补充自动恢复。本合同不授权额外生成、变更预算或越过原拒绝的subset/role边界。

finish_current_final_evidence_failed(lease,assessment)已有retain调用应复用同源实际counter/失败predicate和终态writer校验，但只重核已commit selected，不调用selection commit。pending直接finish继续409（提示原park出口）；正常Worker先走park闭合，不把这个保护409暴露为永久产品路径。不得“先park commit/releaseslease→再finish”，也不得造第三writer或fake新lease。

## 6. 崩溃、恢复与拒绝

- Fact/index commit后park前崩溃：父选择/current journal/source仍旧；准确registered input/result纯复用settled原Operation，原current新fence重建heldproof；0新key、分析/生成、费用及修订计数。未知原Operation先核实。
- 任一park事务中kill：SQLite原整体rollback或完整commit，不能拼接补半个选择/source。companion同key不同准确body409，原immutable损坏422。
- park waiting commit响应丢失：实际source/journal/selected一致后仅观察；原等待probe/queue/claim产生真实new fence，不重复用失效leasepark，不重做child或重复revision_cycles。
- terminal commit响应丢失：guarded历史读取准确failed Run/Production、journal/source-v3、选择及原binding，确认相同输入和原terminal源后只返回真实failed；不claim/queue/清pointer、恢复旧Verified、重新扣费。旧journal executing字段不是current资格。
- failed不是资源wait。后续输入改变不能自动恢复这次有限失败或偷增加cap；保失败报告/作品/来源及计数，明确返回原范围耗尽。任何用户真实新授权/版本改变仍走原独立权限/预算服务，不由本合同授予；waiting正常补充路径保同Run原有恢复能力。
- 403：伪held/跨服务/lease/thread、当前action/声明/rights/Owner撤销。409：准确current journal/source/父child选择/command/计数CAS改变、非合法child、同input不同Fact、待核实不得继续或pending直接finish。422：immutable正文/原report/lineage/严格v3 grammar破坏。503只确缺真实注册resource/服务；不能吞泛EngineError把冲突或未知变retry/失效源None。
- needs_reconciliation无queue/claim/dispatch/计数/费用；原安全unknown writer、历史19三败及CNY20边界完整保持。

## 7. 精确职责与独立验证建议

Backend唯一负责：上述helper/held类型；原prepare自动严格child分支；v3私有grammar/parser/guarded历史reader；原park等待/terminal同writer分支与Worker实际调用；已retain finish一致实现；真成功child join的有限选择待提交assessment及现有final-validation caller。不改公开DTO、ASR监督、原manager或模型/预算/素材权限。

Media保持sole CurrentFinalEvidencePorts/原result；只消费真实held诊断来源、准确registered input/index、actual assessment与child-ready；支持真final-validation context，不构造transition/terminal/approval，不能用全部master重做fallback。Integration只覆盖实际新增types/source及私有grammar资源资格；qualified-resource observer另未实施，不凭文件/SHA/Bool变ready。Test制定实际新cases并跑；Review独审设计和实际源，Acceptance独立确认作品/平台。本文不写测试/阈值/源码、不关闭finding。

独立正反用例须保原byte/费用/quality门：
1. 原已批准diagnosed repair及ordinary realignment两种真实child，从exact parent executing journal+command/lineage到child初次absence选择，保父pointer/source/未受影响媒体hash，revision_cycles只原child creation+1。
2. child已once验证成功的合法分支park选择待提交，再真实new fence原final-validation发布；不同attempt再跑wholeverify、0再诊断/ASR/生成/收费，旧失败历史不丢。
3. 伪/其他command、childintent、parentref/source、缺wholeplan审批、policy或human权源替换、资源/route/secondauthority变更，均整rollback；helper关联存在不足通过。
4. 每个parent journal、parent selected/source、child absence、command/lineage、input/index、counter CAS竞争；任何一处改变拒绝，新source/选择/失败状态不得部分可见。
5. first、successor、retain各在实际0/最后一轮cap耗尽失败时同park terminal，保完整失败report、source-v3、历史，0新增Operation/child/revision/费用；inconclusive/guidance/缺authority/resource不假terminal。
6. append后、CAS间、source前后、lease释放前后kill及响应丢失；准确纯复用或完整历史观察，旧lease不可重试，immutable409/损坏422不能吞。
7. unknown/submitting/unsettled全部仍needs_reconciliation，零queue/claim/dispatch/收费；取消、暂停、human review/current失效优先；原source-v1/v2/同prepared门/旧first-publication/whole-plan双权限及200000us阈值保持。

本轮固定输入BeforeAfter、完整普通件及实际方法范围在本人Architecture/DiagnosticSelectionTerminalOrdering/交接中保存。索引130不冒全130正文评审；01—11核身份及适用限次/恢复条款，非全文重读。所有工具只有文本/JSON/hash静态观察与本人metadata；产品/SQL/Pydantic/native/API/MCP/模型/网络/安装/费用/密钥/发布/历史第四目标均0。正式停止后独Review→Backend→Media/Integration→独立Test/Acceptance；完整R1后连续R2未验收。

