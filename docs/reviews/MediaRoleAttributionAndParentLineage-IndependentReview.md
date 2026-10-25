# ADR0065 四角色、当前父素材与冷启动独立设计评审

结论：DESIGN_SUPPORTED_WITH_ONE_P3_CLARIFICATION。固定合同对 MDG01/02/04 给出了可由原归属者实施的主要接口和保护顺序；本次未确认新的 P1/P2。MRPL-I01 是非阻断 P3 基数歧义，归 Architecture 明确。这个结论不关闭 MDG 功能、不证明任何实际角色调用、父谱系持久化、冷启动或资源资格；没有实现、测试或运行授权。

本次只读停止 ADR0065、Architecture ordinary 及其停止 Media48/Backend130 来源。没有读取活动 Backend/Integration 来源候选，没有采用后继0067新输入或把其他设计/源码结论合并成运行通过。RMCP-P01/P02 保持另一报告的 OPEN，不在此修改。完整 R1 三OS真实作品及连续 R2 仍未验收。

## 固定输入与真实范围

活动卡 G:/开发测试/Projects/VideoCreator/docs/task-board/MediaRoleAttributionAndParentLineageIndependentReview.md，4460B，SHA256 3af8301ab442d9fb420085e4b51855f8c229dfa3bf790589413946754131e4c6。

合同 G:/开发测试/Projects/VideoCreator/docs/decisions/0065-media-role-attribution-and-parent-lineage.md，26704B/153行，SHA256 c88eb3620d0567cb3aa349c1fd4bd952e8c944342e19546c7e8f27da803fd313；全文已读。实际停止过程根 G:/开发测试/Codex/VideoCreatorImplementation/Architecture/MediaRoleAttributionAndParentLineage/。

| 正式件 | SHA256 |
| --- | --- |
| Handoff.md | 2ef51ab79e701123aa19a4f2e134a3ab4ebb16d0810a42b4e00e2d8926f3df6e |
| Handoff.json | 14612347e4fbf37548aa2aa57b60b02b8109c1fe41ce1fbd81a2562f86c7da10 |
| Snapshot.json | a362eb8965d13fd1f0dfa8b506466c4d4a6641ab3b9b30c13b7dd0c178e525cc |
| InputPins.json | 04c78f621ed8632ce41db3e9f3ffd0721838ee3eba92a1a29dd1396a2a962fc0 |
| OrdinaryIndex.json | 2f320ba1048f5b798ab63db89023b6f5c416248c0859b7ca648198a8ef153122 |

独立实际核全部86 ordinary 大小/SHA 与固定索引一致；自己的 InputBefore/InputAfter 共97 unique paths，差异0。97包括卡、规则、合同、必要正式件及86普通副本，不是97运行依赖资格。未从 source_path 读取热生产源。所有普通件身份核对不等于逐行审所有48/130生产模块。

全文实际读 domain/component_diagnosis、domain/diagnostic_recovery、Media component provider/Flow、diagnostic_samples、production_edit、recipe_production、production_drivers；按真实必要方法读 Backend service、private port、Worker、affected service，及初始/affected Flow。精确范围/所有固定普通源完整SHA在自身 ReviewFacts.json；未读其他源正文明确为 identity-only。原旧0060—64只保存固定身份/保护依据，不声明本片重新全审它们，也不把0064设计口当已实施认证。

## MDG01：真实四角色与原账本

停止普通源 Ordinary/Sources/Media48/providers_component_diagnosis.py，第129—167行只发起一个文本模型请求，在同一返回中记录 director/editor/sound 观点；第196—216行 verifier依赖 _contexts 且要求一个 operation_observations。SHA256 d82545388add21f5f1379103585253a11b1f12270ede91b3b8b1e5ebb873b3e0。Ordinary/Sources/Media48/workflows_component_diagnosis.py 第36—64行实际选一 method、原 begin_step/prepare_operation/Executor/complete_step；SHA256 5b9b4e283e38657e0a5089a50929bcbe0a9ca698414b9e35357adea0af4b4c04。既有三观点不是四独立角色。

ADR第28—43、47—55行要求显式 catalog V2/input V3/Observation与Fact V2；四不同 method 各原意图、独立实际 Op/输出/成本，method注册完整内容和安装 resource/runtime SHA受原来源门覆盖。nested observation保自己的 method/op/checks，checks按 method identity 区分，不扁平化同名 check。旧 V1/V2 bytes/default/哈希保持，读者显式 dispatch，不用未知版本空 checks fallback。自身输入/record定位沿原同input不可变结果，selected/publication两writer不新增第三selector。

这对应停止 Backend Ordinary/Sources/GapSources/application_component_diagnosis_service.py 第303—306行按 method内容登记意图；375—399行逐 op 核原 step/input/route、succeeded/settled、真实 actual_cost；520—599行先复用原record、不同结果409并于短writer重核原captures。SHA256 a2747f788f03cb5d207685d7b56d400b6856fbb36814c1b91726dd916af2bd15。新增组合必须在这些真实门内扩展，不用新Run/newkey/零费用遮多次请求。

合同允许同模型但不允许复制一次输出冒多角色；角色未真实看到图像/波形时保持 undetermined。多组件、冲突、缺源、precision-only各保原 information_required/timing_only；任何诊断不授人审/Owner权限或生成。部分成功仅从原成功、结算 Observation 恢复；unknown先原reconcile，不能额外发起已未知受理的请求。新版本不重置原限次或预算。

MRPL-I01（P3）：第29行的“恰好四项”与可追加 evidence 第五项须由 Architecture 固定唯一严格基数/顺序。具体条件及责任在自身 Finding-MRPL-I01.md。本片未把该措辞歧义描述为真实 parser 拒绝或运行失败。

## MDG02：实际当前父 clip/track 与四配方

停止 Ordinary/Sources/Media48/workflows_recipe_production.py 第64—82行从 fact.source_media_refs 筛 shot_clip；Backend _diagnostic_parent 第257—273行生成的是四 master 引用，这不足以提供当前父 clip来源。recipe_production SHA256 4cb402e632251cd40b5e9bdad60d4777ad0b58ad63e7dcfebef0f64f1f555c0b。ADR第61—80、84—95行采用正常 FFmpeg 成功 Operation 的 edit_lineage 与 Backend 唯一 held reader，不以初始 production-shot/latest/hash匹配替代实际父素材。

原编辑真实证据在 Ordinary/Sources/Media48/media_production_edit.py：35—105行初始有序三clips、旁白、probe、25fps trim/concat、无音轨才 silence、0.18 ambient、48000Hz mix；124—133行 cover-only保留视频；151—210行 visual-preserve-mix不重混原mix；218—257行 audio-remix用原video stream copy和真实clips ambient。完整SHA256 4e5d4f04d8327f49286ba25c92aca0c313a18bd980e0d83093c68591261bad66。本片只读源码，没有执行 FFmpeg 或媒体质量测试。

ADR的 ordered_clips/track字段与真实分支对应；None仅真 silent clip，不能缺旁白造 silence；preserved_mix须沿原mix祖先来源，而不能声称本次重生成内部轨道。原video/mix分别确定root，cover-only不要求四 masters同一 edit Op。各代保留边以实际 Asset/Operation输出及本次request preservedID连接；AssetRecord/clip allocation不能冒 Bundle artifact或许可。

原真实首次 _generated公式在 Ordinary/Sources/Media48/workflows_autonomous_production.py 第333—370行，是 request+stage+body+route 的inputSHA、原 allocations/Executor/GeneratedFileManifest/Worker commit。第404—432行实际master-index保存 media_roles/source_steps。affected_production 第194—260行由原command恢复，只有授权的 regenerated shots生成，其余recipe经当前父 reader；第299—300行保存本次source_steps。实际source SHA在ReviewFacts，未把后继热实现回填本片。

Backend Worker普通副本第596—634行是原真实事务：Operation成功结算，exact manifest/durable allocation、MIME与真实Asset登记，最后完成Step；SHA256 219d91ecdfb25dbc3e3a167869da418c5ed330bc4896323dd28b8cf8304dd248。affected service第237—365行由原command/Step/input/Op/receipts重建有效四masters、保留parent及旧body exactmatch路径；SHA256 344c9ef354dbcd0563aed45c0990ecbbacdcbb5c9df8d0c7a199d825d5a4749a。合同第63、67、69行把来源ID与 allocation→Asset映射留给Backend，producer只报告真实输入/attempt，不自填来源authority。

read_parent_edit_sources签名在第75行明确；第78—80行规定 held身份/thread/lease/current以及immutable companion完整body、元数据insert-or-exactmatch、完整captured rows/parent/journal/selected/currentlease重核，bytes/probe/有限graph在SQL外。伴件不是权限；旧完整事实可免费重建同伴件，缺真实track/input则具体 source_material_missing/information_required，不按字段猜旧历史。不因新合同强制所有合法旧输入迁移或重生成，不把历史不足改成永久503/仅cover支持。

实施时Backend须把 parent素材成员/范围/decoder来源纳入唯一引用校验和确定性投影：停止 _diagnostic_check_refs 第401—453行及 _diagnostic_project 第455—494行当前只按 inputs.source_media_refs 建资产/shot/artifact闭包；不能仅给decoder增加 clips，却保留未扩的引用门。要用真实lineage把sample/clip/track回连原master及shot，不能伪artifact或放宽接受任意Asset。此为明确未实施写集，不是声称旧停止类型已有新能力。

## MDG04：同服务fresh context、冷重建与合法 replay

ADR第103、109行分别固定唯一 Media verifier增量与 Backend assert。第105—126行以原 genuine ordinaryLease、registered input/ref、完整 authenticated completion bytes及parent sources登记本次 frozen eq=False context；factory绑定同一个真实 final-evidence port。verifier前后实际assert，Backend finally与port.close都注销，不能把旧 _contexts/driver缓存、JSON值/ref/SHA当权源，不重派 paid analysis填缓存。

停止 service第538行首次验证及第772行 explicit reader实际只传 inputs/observation/operations；record/append共用同body，selected通过 explicit reader。ADR第117—124行要求四caller最终共用同helper，读取exact input/record/selected/source/journal、原成功Op成本/route/checks，当前认证完整body，然后验证、再次核captures、短writer/current与finally清理。public接口不泄露这些私有对象。

原合法 immutable replay明确保持：原成功/结算 Op、原 Fact/selected/source字节不因新thread/newfence改写，新的实际Lease和当前来源重新认证即可重建 context；fact.authored_fence不成为“必须等于当前fence”的新拒绝。停止 _record第524—531行已有相同输入/输出复用，不同body拒；explicit第723—785行重建exact原输入、Op bytes/checks/投影并重核captures，合同沿此保护而非全部拒绝冷恢复。原未知Operation仍reconcile；当前撤销/retire/缺完整body等必须具体拒绝，历史成功Fact不复活旧grant。

V3 parent sources、真实 completion body grammar与全部消费必须由Backend唯一正式DTO/reader固定给Media；停止旧 union/Check类型本身不证明兼容新资源伴件。后继0067如果用于实现 execution companion，仅能作为另行固定设计输入/接口依赖，不能倒填0065这86输入或视作已真实生产资格。本片没有新增0067输入，旧0064尚未实施认证分支仍独立 not_ready。

## 可交实施责任及未实现条件

- Architecture：明确MRPL-I01唯一严格基数/可选evidence处理，保持四required职责、原两authority和200000us；不替Test/Review标准或审批。
- Backend：唯一versioned grammar/dispatcher、角色意图与组合投影；完整父来源持久reader/短writer；实际registry/context/assert/四caller helper；Worker正常初始及affected lineage原commit校验。应先冻结唯一DTO/端口、合法replay与缺源错误给Media，再审真实实现。
- Media：各role的真实能力/producer/template与独立Op Flow；实际FFmpeg lineage结果；四recipe改用真实父读口；当前上下文decoder/verifier，保旧V1独立consumer。不能用假资源/MIME或一回复观点完成角色要求。
- Integration：真实source/runtime/resource/template/model/decoder/许可/平台闭包，公开SDK仅Backend正式契约生成，私有held对象不送renderer。安装sidecar或source hash不能变资格。
- Test/独立Acceptance：后继实际四role成本/partial/unknown、parent→child→child四recipe、不变Asset/许可撤销、cold restart不同fence、contextfinally/close、同input exactreplay/conflict和完整publication两authority/参考报告，仍需按各自正式标准独立执行。

本片0候选/产品/Pydantic或其他第三方导入、0SQL/native/网络/模型/费用/安装；所有真实role/媒体/冷恢复/资源/Owner/API/三OS均NOT_RUN。没有完整制作流程或安装整包通过证据。原19耗尽与31 NOT_READY、旧失败范围不重置或覆写。

## 原错误与终态交接

Architecture ReadbackHistory完整保留7b58c7自然1：错误使用SourceAfter.items.ordinary_copy，后续按InputPins exactlabel修正，83dd86自然0；是metadata准备错误，非产品红、不是源码运行通过。本次输出截断2acb5c/8f475c/1c1328/c6e289保留，缺失必要段分别由bdf604/79c3d2/f0042d/ffeadc补读，07ecb5完整重核合同后半，不声称原截断全文。

本次自己的来源读取和有限SHA元数据工具均自然exit0，无产品启动。末输入核574549自然0，97路径前后一致；正式末工具与reader release见自身FinalHandoff.json/FinalizerTerminal.json。评审停止后无live reader，不等待活动来源候选或外部资源资格才结束这份有限设计审。
