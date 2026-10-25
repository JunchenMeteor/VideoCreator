# ADR0074 本地计划顶层合同独立评审

**DESIGN_PARTIAL_SUPPORTED；两项 P2 / OPEN_DESIGN，归属 Architecture。** 十一字段、两个窄 Ref、严格纯 parser/source validator及fit/gain方向支持 Backend sole DTO源码实施；完整本地成片/Bundle应用链仍缺真实版本与适用outputs合同、静态图片范围语义。Review不批准应用或运行，不因这些缺口新增普通制作资格门，也不以局部设计支持关闭完整R1后连续R2。

## 固定输入与实际覆盖

任务卡 LocalMaterialPlanTopLevelIndependentReview.md SHA14b4ec62a72538a14973e30c76265abe39e3c695aefa330011b907c2c58c4ed5。ADR0074全文49行/8841B，SHAfe82d5db54489e48080efa4bbda03fe7c4d5c6f76bdd56c395f48d321fbd953e；架构停止过程 G:/开发测试/Codex/VideoCreatorImplementation/Architect/LocalMaterialPlanTopLevelContractApproval/，Handoff.md3252105d…/Interfaces89315aa9…/Impactb9fa6549…及完整Handoff.json/Delta/Snapshot/13 ordinary由正式InputPins定位。原架构025234自然0/TRUEFINAL。

完整读取停止提案4984B a12dc74f…、EarlyInterfaces3768B e309d56d…、sole EarlyLocalMaterialProduction.py9449B7187ac4c…及OldRegisteredProduction.py7748B9dcac6ce…。必要旧事实仅读取原Asset/MediaProbe/CreativeRevision/RevisionRef/CapabilityRoute和accepted Goal/ref/intent数据段；0072相关计划/权限/输出段，0073固定连接键作为已完成设计边界，不重审旧53源。

原实际端口从0072停止Backend SourceIndex（d4af043b78ab48fcb60acb51576fef7b8c0a7956c90208afd97304d5b3fe5a8a）定位ordinary_copy，未读source_path或热文件：production_ports.py14163B/e767d5a8a7a77ce957a995bcecc951dcd2e502795f2b2b060c352710807514ab（完整非空方法正文），production_admissions.py73957B/5c6548b4…（完整相关policy方法），bundles.py232751B/a6d9b58b…（六版本/full-only/固定附件/关系正文），旧media_registration.py60800B4964c2ef…（_current_services两权限分支）。没有把全Bundle或旧大图逐行审完。

29有限输入逐件核identity，13架构ordinary及3原端口与各停止索引bytes/SHA相符；最终InputAfter differences=[]。InputPins在首合同/源读取之后建立，只声称该捕获到末核的区间无变。原旧rg路径失效a3c24b自然1保留，89d395改用Get-Command得到当前已有rg自然0；b0e30d定位输出及双读聚合输出超过预算均保截断，后续只补缺的policy760–775及必要具体记录/方法，不称截断为全文或产品失败。原Source/Pydantic/SQL/媒体/第三方/网络/费用均未执行。Root所给新EarlyPlanSourcesAbi候选不为本合同裁定所需，未读取或混入。

## 十一字段实施裁定

| 字段 | 确切来源与裁定 |
| --- | --- |
| format | 新local-v1 literal，不能冒旧v1/v2/v3。支持sole类型。 |
| request_ref | 五字段来自原Production/Run/request revision/canonical request SHA；原binding已保这些身份。与Goal SHA分开。 |
| goal_ref | 三字段来自ProjectGoalAccepted与_AcceptedGoalIntent；原ProjectScopeDerivationRef恰两字段。daily/native要完整关联；direct null必须受控读者证实absence，损坏/缺失不能转null。 |
| material_refs | 原完整AssetRecord含source/rights/probe，集合恰等于bindings的asset集合，同Asset多usage仍只一条。读取许可另核。 |
| input_bindings | 原八字段、0073唯一asset/usage连接键；原source字符串/真实bytesSHA/probe相等且当前可读。多镜头复用允许。 |
| timeline | 既有strict尺寸/fps/微秒range和usage解析支持；图片source_range额外语义缺口见P02。 |
| source_script_revision_ref | 原RevisionRef kind=script，原CreativeRevision没有contentSHA；Ref须核原完整持久record/canonical内容，不只hash文本、不造Creative种类。 |
| source_script_origin | 三literal可实施；model/user/settled input-audio ASR来源须actual application核查，不能从字段或finalmix转写自行认定。 |
| rights_proposal | 原完整ProductionRightsProposal只是预审批声明；不得嵌postapproval fact或授权。旧saved fence/time保历史字节；原rights/admission须精确版本桥见下段。 |
| selected_capabilities | 已安装/已选择原CapabilityRoute的完整记录、unique ID；local零费/no credential，BYOK单独原权限/Operation。verified bool/source equality不授权。 |
| outputs | 完整保原request解析结果与顺序，不加默认/省略；真实适用master/Bundle映射缺口见P01。 |

ADR第31–36行把strict1MiB UTF8/noBOM/duplicate/nonfinite/extra拒绝、纯数据比较、受控application来源/absence/许可和原writer提交分开，支持实施。新DTO本身不查询数据库、没有写者资格；原403/409/422和资源NOT_READY/等待语义应保留。不因parsed/hash相等跳过current/fence、预算、未知Operation或真实source失效。

## 原 rights/admission 可保持，但不能原样直穿

旧human ProductionPorts.current_production_admission第84–121行先调用production_admission，再核实际sameRun immutable target/decision SHA、当前lease和原Owner声明；current_production_rights第123–139行依此生postapproval fact。production_admission第153–160行只有旧v2来源validator，且统一读revision.body['rights']；production_rights第36–52行只接受同Run的autonomous.plan.<run_id>和真实Owner/project/期限。

旧PolicyExecutionPorts委托production_admissions：第665–683行旧v2 source preflight后在原current_guard+transaction内核root body.rights等于record.policy.rights，再原_persist；第760–775行rights fact还核原plan ID、targetSHA、已提交execute_plan和root rights。故合法0074十一字段body只含rights_proposal，直接沿旧实现会到production_rights_conflict409；若私造别的plan ID还会触production_rights_scope_denied403。这里是已确认必要源码适配，不是实际运行失败，也不是必须另造授权系统。

Backend可以在显式local格式分支用sole strict model及受控原来源把rights_proposal.rights/声明主体/ID/SHA/原request/registration关系，精确连接原完整Owner declaration或policy rights比较；继续同一实际plan revision/approval targetSHA、human decision或policy action、原current/lease/期限/事务pre-post guard和独立postapproval fact。旧格式/root-rights/旧source validator原样保；不能加第12个rights字段违反闭集、伪装旧plan格式、仅从caller nested dict取rights便允许，或放宽plan target为任意ID。Local ID/复用选择必须由受控原路径明确保持实际sameRun，不自授ID通配。

恢复时旧proposal的fence/checked/validUntil是被冻结历史声明；不能改旧字节或要求与新即时提案的时间/fence整对象相等来伪续权/误拒。应核完整稳定声明与实际新current authority及当前审批有效性，失效按原拒/等待，不跳过旧unknown/reconcile或重收费。来源验证须落在真实caller和原短writer/current检查内，pure validator结果不替其权限。这些实现保护要求在ADR34/36的方向内，无新增设计P2；实际新Backend实现尚未在本片审查，不能称source/SQL已闭合。

## 必须窄补的两项设计问题

**LMPT-P01 / P2 / Architecture / OPEN_DESIGN。** ADR第7/19/23/34/40–43行未给local真实planner/script/quality/必要来源版本与旧Bundle六Creative和固定附件的唯一适配，也没有audio-only/no-voice等request适用集合。原Bundle _check_revisions1224要求实际insight/brief/plan/script/storyboard/quality；verify1275先查原持久refs，1278只完整八outputs、1281全部FIXED_FILES；_validate_relations2586–2595另核真实insight/brief/plan附件和output paths。原CurrentProductionUpstreamResult101–118在masters_ready要求四distinct video/narration_audio/mixed_audio/cover，不能表示audio-only或no-voice合法masters集合。

不能据此断言每个真实local full-voiced-video永远不能产生六个真实版本；确证的是合同没有规定这些版本/方法的真实出处和适用映射，不能用本地plan+script+四master概称满足原门。最小后继由Architecture给explicit version/profile合同：哪些真实local版本/附件、对应原核查关系、适用requested/master集合、暂不适用时明确NOT_READY/等待/拒绝；旧完整模型profile保持原门。不得造六Creative、伪insight/brief、静音旁白/假video、删QC/ASR/CTC/RAG/两authority或宽松改公共Bundle格式。Backend唯一类型/版本/权限host，Media保存并消费真实方法/来源；Review不代批准新Bundle版本。

固定Finding-LMPT-P01.md SHA1579f2f1055502207c52365a63217abc48e6ccd2fca467ce9a98c1bfda8f0d2f。

**LMPT-P02 / P2 / Architecture / OPEN_DESIGN。** ADR18只复用Early shot的source_range:c.MediaRange；27只定义fit/gain。MediaRange要求end>start，而静态图片实际probe.duration_us=None；0072亦未把图片source_range区别定义为display hold。按视频原duration范围限制会拒图片，按候选自行用[0,D)又不能宣称源图像有D时间。因此需明确static MIME/probe、source_range是否display hold/零起点、与timeline和目标帧量化关系、派生输出source_media_range=None及原probe不能反写伪duration。Video/audio仍需真实源时间和有界range；不得为此猜新field/伪duration。此项独立于先前Media has_video错误。

固定Finding-LMPT-P02.md SHA5858396972ae8890503cea3c98eb21041aee456e3998763fbe75752ad24b0604。

## fit/gain、职责与停止

ADR27的contain/cover保比例填充/裁切、gain有限非负线性乘数0/1语义完整，禁bool/string/NaN/Inf、不增任意上限或clamp；支持source消费。先前Media LOMD-P01 gain>4与LOMD-P02图片has_video SOURCE P2仍OPEN，本文不当作者已修。Gain合法不等于失真/时长/真实质量通过，fit不产生权限。最终ASR/CTC/两authority、四master真实内容与适用性、Bundle完整证据和R1/R2未运行。

Architecture仅两处精确设计补充；Backend可继续sole十一字段/parser/Refs/受控rights桥及同Engine host，不跨写Media。Media actual composer/Flow/factory/Bundle消费待新合同和原源码修复，Integration只按Backend冻结唯一source生成SDK/真实资源封装，Frontend不授renderer权限。无需独立Test签发成为普通用户制作前置。source/application候选各自后继独评，本片不授实现应用、运行、发布或费用。

回滚为不消费未完整合同，原0074/0072/0073及源保持。正式过程 G:/开发测试/Codex/VideoCreatorImplementation/Review/LocalMaterialPlanTopLevelIndependentReview/；InputPins/InputAfter、两Finding、Impact、FinalHandoff/Terminal作为伴件。已完成全部必要读取，末工具自然返回和全部reader释放由Agent实际回报，不从文件存在推断。完整R1后连续R2仍未验收。
