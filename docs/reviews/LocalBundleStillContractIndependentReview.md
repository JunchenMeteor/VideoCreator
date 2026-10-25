# ADR0075 本地作品包适用集合与静图时间独立设计评审

**结论：DESIGN_SUPPORTED，LMPT-P01/P02 仅在设计级可关闭；源码、运行、产品与验收仍未通过。** 本评审未发现必须重写 ADR0075 的设计级阻断。新增 `0.4.0-candidate` 显式本地分支和版本化语义类型足以表达原合同不能表达的合法本地作品；0.2/0.3 原六版本、八输出、固定文件及四母版门不得转入新分支。结论不批准应用候选源码、安装、发布或费用。

## 固定输入和覆盖

任务卡 SHA-256 `76be1e639fb53e8a2049bc780ed86a06bcb530b805e1e613bd212716e0f77ef0`；ADR0075 17356B/SHA-256 `776a1bb058bc79d9beee04aa9da129219e786c33707a01732a1c9b942a071091`；架构停止 Handoff/Interfaces/Impact 的 SHA-256 分别为 `101570a2099d276f568b725f2ede82129f187381448613887575535248e33945`、`91610e0c7fb7c2fc1ffe599675fcc4eef46d5da19fcc1d7d2c4c5c20ae52a475`、`e4c1d30775edfc7d669342c8f8bde729d574e0f1f856ed4442318630d7b9dd88`，全部与任务卡相符。原独评 `LocalMaterialPlanTopLevelIndependentReview.md` SHA-256 `9c175607b4fa92a9b14d000636d1aae48f53899cb243728211eb5e05404e7acb`。逐行只读 ADR及必要旧 `domain/contracts.py`、`domain/registered_production.py`、`application/bundles.py`；没有执行源码、Pydantic、SQL、媒体、模型或测试。`rg` 对不存在的旧路径曾返回1，随后从实际 repo 路径完成有限定位；不把该定位失败当产品失败。

## LMPT-P01：设计级可关闭，实施仍开放

旧 `bundles.py:1223-1257` 要求六种真实 Creative 与实际 script/quality 审批，`:1266-1282` 要求原请求同版、完整八输出和 FIXED_FILES；`:2583-2615` 依赖 insight/brief/plan、四母版及实际说话的转写/对齐。旧 `registered_production.py:101-120` 的 ready 状态只接受四个 distinct master。ADR0075:7-23 给出只由受控本地注册选择的独立0.4版本、原请求版本/SHA隔离、真实 plan/script/quality 三版本、可选真实 Creative和最小附件；`:25-36` 给出由原请求/已批准计划算出的适用母版与 requested outputs、V2 upstream/blocker 和同 Run 恢复；`:38-56` 按实际speech/no-speech/no-audio、音频单独作品定义 transcript/quality/semantic/RAG/Shot的版本化证据；`:66-73` 限定 sole Backend dispatch、原受控准备/版权/Operation/current/fence/双权限与首次/恢复的适用关系门。因而不靠伪 insight、伪 narration、黑视频或改写原请求来绕过旧门。

设计负例逐项可判：原请求要 `narration_audio` 而计划无旁白轨、要转写/字幕而最终实际无音频，应按 ADR:29-34/44 拒绝不适用；无旁白但实际背景 speech 必走真实 ASR/CTC、两真实authority与200ms，不能按 no-speech 省略（:31,40-48）；实际无speech须 settled ASR 与完整 observed gaps，not_observed/空文本不够（:43；旧 `contracts.py:941-973`）；no-audio 不造 ASR/字幕（:44）；audio-only 不造 video/cover/shot（:29,52-56）；unknown Operation 不重交（:36,69-71）。原0.2/0.3不可因请求版本同为旧值就获local宽松分支，必须核本地注册、已批准计划与0.4 profile全链（:7,19,68-70）。旧 `bundles.py:783-895,1977-2005,2092-2135` 显示 prepare、material-kind与 import 还有 full-only/version分支，均是 Backend/Integration 后续必须实际改通并保旧支路的源码工作，不能以 ADR 已写视为已完成。

**实施核验点 / P3 / Backend、Media、Integration、Test：** no-speech且请求字幕时，ADR:43,46 允许 `LocalActualTranscriptDocumentV1.subtitles=null`，同时要求实际零cue SRT/VTT；旧 `SubtitleTrack` 在 `contracts.py:990-1012` 明确拒绝零cue。新分支必须独立按实际 `LocalSpeechEvidenceV1` 绑定两份受控字幕 Material，核解析后零cue、MIME/哈希、所选 output 的两个artifact ID与原request逐项一致，不能借旧 `SubtitleTrack` 验证、放任任意空字节或将字幕 null 算缺产物。此检查可由现有 ADR:40,43,46,70 的“真实零cue/原关系/同Manifest”直接落实，不构成新设计 P2；未实现前不可声明该案例通过。另须将 V03 真实policy、benchmark、qualification、runtime/reference 报告按 ADR:42,48 的原 typed 来源逐份验证；`alignment_report_artifact_ids` 只是索引，不能只核一个字符串ID或hash。

## LMPT-P02：设计级可关闭，实施仍开放

旧 `contracts.py:355-374` 的 `MediaRange` 是正长度整数区间，`MediaProbe.duration_us` 可为 null；原本地计划 source_range 复用同一范围，不能把图片时长伪装为 intrinsic。ADR0075:58-64 明确真实单帧 PNG/JPEG 与 width/height/probe、duration=null 的静图判别，既不要求 `has_video=true`，也不把动画/多帧当静图；原 shot.source_range 必为零起点且长度恰等 timeline hold。独立的 `LocalVisualMappingDocumentV1` 使静图 `source_media_range=null`、display_hold_us 为实际时长，video 则有真实源范围；`T(n)` 整数帧格、预批准计划、实际decode帧数/时长核验和audio sample/clock分开，给出了唯一可执行含义。未对齐已批准帧格须重新规划审批，不能暗裁/伸缩。该语义解决原 P02 设计空白，尚须 Media/Backend 真代码与静图、动图、越界、帧格负例证明。

## 结论边界与交付

LMPT-P01、LMPT-P02 可由统筹标为 **DESIGN_CLOSED_BY_ADR0075_REVIEW**，但原 source/runtime 验证、ASR/CTC资源、真实作品包读/写/导出/导入、三OS安装、API/MCP、独立R1及连续R2均保持开放。Backend负责唯一schema/显式dispatch/适用与原安全关系；Media负责实际母版、ASR/CTC、语义及静图映射；Integration负责由 sole source 派生的0.4契约/SDK；Test/Review/Acceptance各作自己的独立验证。回滚不消费0.4分支，旧字节和历史证据原样保留。
