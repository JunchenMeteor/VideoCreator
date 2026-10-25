# ADR0075：本地作品包适用集合与静态图时间

状态：APPROVED_CONTRACT_ONLY，待独立设计评审；不授实现应用或运行，不关闭 LMPT-P01/P02。0072—0074及旧格式原字节保持。这里只补其实际 Bundle/语义消费者缺口，不增加普通本地制作的发行资格门。

## 1. 唯一版本与真实创作来源

新增独立 `BundleManifestLocalV1`：`schema_version="0.4.0-candidate"`、`bundle_format_version=2`、`content_profile="local-material-bundle-v1"`。显式分支匹配真实已批准的 `registered-local-material-plan-v1` 与原本地安装注册，不由 renderer/profile 字符串自行选择宽松验证。旧0.2/0.3仍走原六 Creative、FULL_OUTPUTS、FIXED_FILES和关系验证，不能自动升级或删门。

新 Manifest **复用原 BundleManifest 全部字段名称、类型、唯一性、秘密拒绝和 Artifact/Output/Method/Rights/DAG 规则**，仅改变上述版本常量，并增加以下闭集字段：

| 新字段 | 类型与来源 |
| --- | --- |
| `content_profile` | 上述唯一 literal。 |
| `request_format_version` | 原已接受请求的 `0.2.0-candidate | 0.3.0-candidate | null`；null保原legacy身份，不能冒0.3政策。 |
| `selection_artifact_id` | Identifier，指实际 `LocalMasterSelectionV1` 文档。 |
| `speech_evidence_artifact_id` | Identifier，指实际 `LocalSpeechEvidenceV1` 文档。 |
| `visual_mapping_artifact_id` | Identifier或null；video作品必须指实际下述映射文档，audio作品必须null。 |

`workflow_version` 保原安装/执行注册真实身份。Manifest SHA、原 request revision/SHA和 bundle revision 分别保存，**不改原请求版本/hash来迎合旧 verify 的版本相等判断**。新分支核上表 request_format_version及原完整request SHA；交付要求、precision policy/default和真实当前授权按原请求执行。

本地必需的真实 Creative 是 `plan/script/quality` 各一条：plan为0074原十一字段 body，script为原真实保存的 source_script_revision_ref，quality为本Run实际检查产生的版本。plan输入refs包含实际script和本次真实其他输入；script、plan、quality各核原持久body/kind/contentSHA、Production/Run适用关系和原 human/policy批准。可以保留真正存在、被引用且有方法来源的 insight/brief/storyboard，各kind至多一条，附原完整版本；**三者不是本地必需，也不允许造空版本填六个门**。本地timeline的镜头记录来自已批准plan及实际decode，不冒称单独的 storyboard Creative。

始终存在的本地附件为 `Creative/production-plan.json`、`Text/approved-script.json`、`Checks/quality-report.json`、`Checks/local-master-selection.json`、`Checks/local-speech-evidence.json`、`Semantics/work-summary.json`、`Semantics/source-bindings.json`、`Semantics/semantic-segments.jsonl`、`Semantics/rag-chunks.jsonl`；真实可选 Creative 各附相应原body。script附件沿原实际批准的文本内容；有旁白时是 spoken script，无旁白时是真实 production script/剪辑指导，不能当成已识别话语。summary/topic/main_thesis来自真实Goal/request/脚本、用户来源或实际模型/观察方法，逐字段标来源，不能把plan冒成insight/brief附件。

## 2. 确定的master与requested outputs

Backend唯一维护 `LocalMasterSelectionV1`，恰含 `format="local-master-selection-v1"`、`request_ref:LocalProductionRequestRef`、`plan_revision_ref:c.RevisionRef(kind=plan)`、`content_kind:video|audio`、`master_roles:tuple[video|narration_audio|mixed_audio|cover,...]`、`outputs:tuple[c.OutputRole,...]`、`narration_binding_ids:tuple[c.Identifier,...]`、`script_purpose:spoken_script|production_script`。它是原受控request/plan事实，**不是权限**。

- content_kind=video iff原outputs包含video；需要实际visual shots，master含video及由实际成片帧产生的cover。否则有实际audio tracks时为audio，master没有video/cover，不能造黑视频或假cover。无任何可制作音画的请求返回具名 `local_media_input_required`，不宣布本地工具完成。
- 有实际计划audio tracks就有真正独立mixed_audio；无audio tracks的video不得制造静音mix。视频源的音频仅经明确audio binding/track进入mix，不能暗中保留未授权流。
- 有narration usage tracks才有narration_audio及spoken_script；它是真实旁白子mix，mixed_audio为完整声音，两个master不能同Asset。否则没有narration_audio，script_purpose=production_script。无旁白**不等于无speech**，背景/原素材也可能含话语。
- master_roles按原固定顺序 `video,narration_audio,mixed_audio,cover` 取适用子集，actual Asset IDs各distinct；每个都是原Operation→真实decode→settled/fenced commit产物，并保持原来源/版权/许可闭包。

Output适用规则：video仅video作品；narration_audio仅真实旁白；mixed_audio仅真实音频；approved_script是上述真实批准脚本；actual_transcript/subtitles要求实际音频并沿下一节处理；semantic_manifest/rag_chunks用于全部有真实音画的本地作品。Manifest outputs与selection.outputs和原request.outputs **逐项及顺序一致**，不偷偷增加或省略。请求了物理上不存在的旁白/音频转写等，执行前给 `local_output_not_applicable`/422及具体role，不能用假媒体填齐或用长期503掩盖；纠正须原真实新请求/审批路径，不能改已接受request字节。

新增 `CurrentProductionUpstreamResultV2` 恰含 `format="current-production-upstream-v2"`、`profile="local-material-bundle-v1"`、`run_id`、`fencing_token`、原state枚举、`selection:LocalMasterSelectionV1|null`、`media_roles:dict[上述master role,c.Identifier]`、原 `blocker_code`。masters_ready必须有真实selection，mapping恰等于selection.master_roles、无blocker且全是真实distinct已提交Asset；阻塞时mapping为空，尚未产生/批准plan时selection=null，不造plan_ref。只有本地显式分支消费V2；旧结果仍强四master。必要的 `CurrentProductionBlockerJournalV2` 恰为 `format="current-production-blocker-v2"`、原真实 `binding:ProductionBinding`、`result:CurrentProductionUpstreamResultV2`、原 `blocked_at_us`，显式版本dispatch保旧V1字节，仍仅原waiting_authorization/resource_not_ready可进入该journal；原waiting_user、denied、unknown各沿原真实服务。binding不由selection授新scope。waiting/unknown/reconcile不可跑旧master，原resume核来源/current、同Run、原journal CAS并只queue新fence，park/lease释放不二次park。

## 3. 实际speech与精度，不能由选项猜absence

`LocalSpeechEvidenceV1` 恰含 `format="local-speech-evidence-v1"`、`state:speech_observed|no_speech_observed|no_audio_observed`、`input_audio_asset_id:Identifier|null`、`input_audio_sha256:Sha256|null`、`transcript_artifact_id:Identifier|null`、`alignment_artifact_id:Identifier|null`、`subtitle_artifact_ids:tuple[Identifier,...]`、`method_refs:tuple[Identifier,...]`、`proof_artifact_ids:tuple[Identifier,...]`。ID全部指该实际Manifest中的受控原Material/Asset/Method；不能是URL、bool或未验证opaque证明。

- speech_observed：最终mix或原受控解码音频的实际ASR Observation、完整actual transcript、原注册CTC alignment与真实subtitle材料必需。复用原policy/reference/qualification/runtime report、两真实authority与200ms/MM05标准；只展示可选requested输出不免除内部完整证据。生产脚本不是话语时，不以脚本正文替换actual transcript；CTC依原真实转写而不是猜稿件。已有speech却无资源/可信报告就具名等待，不能转no_speech。
- no_speech_observed：必须有实际最终音频、原成功settled ASR及完整覆盖的观察gaps；只有真实method支持并观察的no_speech/music可确认，not_observed、失败或单纯空字符串均不能确认absence。保留原 `ActualTranscriptRevision` 的真实空text/utterances和实际gaps，不造“无语音”文字。无可对齐单位时alignment/subtitles不伪造单位，alignment_artifact_id=null；记录不适用的原因和原观察证据，P95/sample_count=null，不能填0或沿用算法通用分数。若requested subtitles，输出真实零cue的SRT/VTT并在下述文档明确observed no speech；这不是有话语字幕通过。
- no_audio_observed：必须由实际成片decode证明无音轨，并核plan无audio tracks/没有mix/narration master；transcript/alignment/subtitles及input_audio字段为null，proof仍指实际decode/Operation材料。actual_transcript/subtitles若被requested按上一节明确拒绝，不能生成假ASR或假空音频。

新增 `LocalActualTranscriptDocumentV1` 恰含 `format="local-actual-transcript-v1"`、`schema_version="0.4.0-candidate"`、`transcript:原ActualTranscriptRevision`、`alignment:原适用0.2/0.3 AlignmentRevision|null`、`subtitles:原SubtitleTrack|null`、`speech_evidence_artifact_id`。no_speech允许上述真实无单位null分支，speech_observed仍要求完整原绑定/检查，no_audio不生成此文档。actual_transcript output指此实际文档；subtitles指实际SRT/VTT。旧ActualTranscriptDocument及验证不变。

本地 `LocalBundleQualityEvidenceV1` 恰含 `schema_version="0.4.0-candidate"`、原 `quality_revision_ref/checks/content_sha256/allowed_degradation_approval_ref`、`speech_evidence_artifact_id`、`alignment_report_artifact_ids:tuple[Identifier,...]`、`applicability:tuple[LocalCheckApplicabilityV1,...]`。Applicability项恰含 `check_id,status:applicable|not_applicable,reason_code,proof_artifact_ids`；由真实selection/speech事实决定，缺测不是not_applicable。实际audio/visual absence检查自身始终applicable。语音存在时，report集合必须包含原请求对应的真实policy/benchmark/qualification/runtime/reference材料，按原typed schema/受控来源逐份核，不能普通ID/hash就授资格；无speech只标语音边界不适用，不能宣称算法抽样200ms已通过。原QC失败→原拒绝/有界修复，缺测/资源→等待；不因human确认放过真实超阈值。质量版本绑定本Run、actual Asset与checks；最后仍两authority、完整rights/current及原原子发布。

## 4. 本地语义与数据包同版本

旧 `SemanticSegmentV1` 强video/对齐ID，不能塞假ID来表达audio-only。新增 `SemanticSegmentLocalV2`：保原字段和来源检查，`record_format_version=2`，增加必需 `timeline_range:c.MediaRange`；`video_asset_id/video_range` 改为成对nullable，`alignment_revision_id` 改nullable。audio-only两video字段null、frames/shot IDs空；有video则实际派生video/frame/镜头refs必需。无speech speech_text及transcript_unit_refs为空，alignment ID=null，原speech absence证据从Manifest关联；audio_spans仅真实声音与原sample/clock mappings。summary/visual_description等仍真实观察/用户/模型来源，absence不用伪视频/假转写支持。

新增 `RagChunkLocalV2`：复用原RagChunk全部字段，record_format_version=2，chunk_type允许原三种及 `audio_segment`。audio-only video_ranges为空、audio_spans为真实范围；无speech不造speech_segment；visual_segment必须真frames。真实work_summary/source_refs/topic/main_thesis保原来源/权利/访问范围，仍能由Portal自动关联原文章/选题。各text/material完整SHA与方法、来源、音视频/微秒范围闭包必核。

新增独立 `ShotEvidenceLocalV1` 复用原ShotEvidence字段；video作品来自实际plan镜头/派生video/frame，不借缺失storyboard造Creative。其shot_revision_id是原plan内容SHA与shot_id的确定派生记录ID（`shot-`加恰含 `plan_content_sha256,shot_id` 两字段的sorted/compact/UTF-8 JSON完整SHA256），对应真实持久shot Material，不声称存在storyboard Creative；audio-only不产shot文件。Media/Backend共同用上述本地typed文档，不能给同role两种随意JSON。reference/export/import、BundleRef、DeliveryProjection及授权metadata必须显式识别0.4；同Manifest/同artifact/HASH，旧客户端不支持则明示版本不支持，不能冒0.3或以origin旧ref当本机ticket。所有leaf/full disclosure、purpose、过期/撤销、许可证祖先闭包与原保护reader不变。

## 5. 静图display hold与确定帧映射

不增加LocalTimelineShotV1字段。真实受支持静态image（当前PNG/JPEG）由actual decoder确认、原width/height/probe有效且duration_us=None；**不要求 has_video=true**，动画/多帧输入不能自行归静图。该shot的 `source_range` 唯一表示display hold：`start_us=0`，`end_us=timeline_range.end_us-timeline_range.start_us`。它不是源图像时间；原Asset.probe及版权/source不修改。video/audio继续真实有duration、源入出点在实际intrinsic范围内，不用None绕范围检查。

Media保存 `LocalVisualMappingDocumentV1`，恰含 `format="local-visual-mapping-v1"`、`fps_num/fps_den`、`timeline_duration_us`、`rows`。每row恰含 `shot_id,input_binding_id,source_asset_id,source_sha256,source_media_range:MediaRange|null,display_hold_us:PositiveInt|null,timeline_range:MediaRange,frame_start:NonnegativeInt,frame_end:PositiveInt`。static行source_media_range=null、display_hold_us为上述hold；video行source_media_range为真实源范围、display_hold_us=null。文档在 `Semantics/visual-mapping.json`，有video也须 `Semantics/shots.jsonl`。

设fps=p/q；第n帧时间的整数微秒唯一采用 `T(n)=floor((2*n*1_000_000*q+p)/(2*p))`（正数nearest、ties向上）。仅video规划在原plan批准前选实际帧边界并保存 `timeline_range=[T(n0),T(n1))`、work duration=T(N)；Backend验证n0>=0/n1>n0/N边界与严格整数结果，**parser不暗改已批准plan**。静图hold等于该范围长度；实际导出占[n0,n1)帧，派生video duration/frame count按实际decode与计划N及原decoder容差核，不能把hold写成原图像duration。audio-only不套视频帧格，仍按原实际audio sample/clock映射及解码长度验证；video中的音频也保原sample/clock mapping。帧格处理不能替代字幕时钟量化、ASR/CTC或放宽200ms。若既有video plan不在该帧格，返回具体计划冲突/有界重新规划审批，不静默裁切/拉伸或伪造source范围。

## 6. 唯一caller、提交与失败顺序

1. Backend original application host：由sameRun实际local plan/request/source和当前原human/policy权限构造/核selection，保存原真实Creative与Selection Material；dispatch既有local factory。Media真driver只消费原受控Assets、same lease、Operation/output reservations，返回上述V2的实际master。
2. Media local final producer：在原受控preparation中按selection建立真实masters、source/plan/script/material；执行实际适用ASR/CTC，保存speech/quality/semantic/RAG/visual mapping等完整材料。无资源沿原同Run blocker/resume，unknown沿原reconcile不重复副作用，不造Worker/permit，不因结果选择少master就退回旧all-master。
3. Backend BundleService：显式local版本入口复用原prepare/held reader及原identity、source前后、Operation settled、版权用途、current/fence与两authority。只在此分支以真实三版本、selection、上述必需/适用文件和新typed关系替换旧full-only条件；没有相应真实文档不得发布。保完整一次verify、短writer/CAS/lease撤销和不可变READY/commit次序。
4. script/plan/quality审查仍真实human decision或当前合法Owner预授权policy；selection/speech字段不授权。缺失/未知来源→原等待/NOT_READY或明确冲突；真实QC/许可/请求冲突→原拒绝/422/409/403，不以“仅本地”删门。首次与恢复都用原持久readset/context/typed reader，缺旧context保持missing，不重跑未知ASR/生成来修复文档。

Backend独占上述sole DTO、schema dispatch、selection规则、Bundle关系/适用检查及application host；Media独占planner/Flow/local factory、真实drivers/semantic及Bundle material生产；Integration按冻结唯一源生成0.4契约/SDK和实际资源包装；Frontend消费原五步及明确不适用/缺资源提示，不构造可信结果。Test/Review独立核voice视频、背景speech/no-speech视频、无音轨video、audio-only、同源静图hold、requested不适用、损坏来源/旧格式误入、frame/Asset/hash/rights/current/unknown恢复和真实报告负例。尚未实施的0.4路由具名NOT_IMPLEMENTED，不能称产品已完成；设计明确完整后继实现，不以永久503代交付。

完整R1独立验收后连续R2、三OS、本地免注册/BYOK、实例数据与API/MCP同引擎目标不缩。回滚只是不消费本新分支，旧格式及历史证据保持。

固定主输入：任务卡SHA `269c3cd15129598fa5692d0b6cae32782dd8cc03af4e4cb557d42a6074a175c1`；LMPT-P01 `1579f2f1055502207c52365a63217abc48e6ccd2fca467ce9a98c1bfda8f0d2f`；LMPT-P02 `5858396972ae8890503cea3c98eb21041aee456e3998763fbe75752ad24b0604`；停止BundleApplicabilityGap `9f73ab1abefe81bce79a00b4f9477c9b1efe222a243f0eb92e3cca0fcc16cf90`。完整准确路径、必要停止类型段/普通副本及保留的截断/路径错误见阶段InputPins/交接。
