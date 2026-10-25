# LocalOwnedMaterialDrivers 独立源码评审

结论：**NOT_READY_FOR_APPLICATION — 两项 P2 / OPEN_SOURCE_STATIC，归属 Media。** 本片只评停止的未应用候选。三个新增实现可以继续窄修，不能把本报告当成 FFmpeg、素材、安装、普通制作或 R1/R2 运行通过。

## 固定范围与证据

任务卡：G:/开发测试/Projects/VideoCreator/docs/task-board/LocalOwnedMaterialDriversIndependentReview.md，SHA256 4b2a5ff6a5ca17eb8a691ce20d0227227bf8109ace0ca1193ed8fcbfe2644046。Media 停止根为 G:/开发测试/Codex/VideoCreatorImplementation/AgentMedia/LocalOwnedMaterialProductionImplementation/RevisionTwo/，原作者 f54c19 自然0、停止候选读写；本 Review 未读取生产 target 或热 Backend/Architecture。

正式 Handoff 5cd5781a…、SourceIndex f939763d…、Interfaces 2f326bb6…、FinalCandidate.patch fa4f0cce…、RevisionDiff.patch a588f753…，完整值在 InputPins。51 个 ordinary 实际 bytes/SHA 均与停止索引逐件相符。48 个保护副本的索引 first SHA 与本次 SHA 相同；该结论是停止副本/索引一致性，不是对当前生产库的读取证明。

全文审读三新增：media/local_material_edit.py（341行、24000B、65a058ca4ac1b5ee2dfa9e4537994308dde432fb19f3eca9166c49966a4787c4）、providers/local_material_resources.py（77行、5177B、b7b1f9f428305d92518417da02e086cabb2b355d70fb09b515b5a6d651edb6b0）、workflows/local_material_drivers.py（84行、5806B、9f0de70aa67b6c6f3c01e96b07296276e8e2685821749c52225711e09d2f8a72）。全文审停止 Backend EarlyTypedAbi 的 Interfaces、SourceIndex、9449B 唯一 domain/local_material_production.py（7187ac4c…）；实际 common/resource/AttemptControl 共用 helper 全文，以及 FFmpegRuntime 的路径、输入格式、_run/probe 和原 Flow _generated 实际调用段。其余48源码是完整性保护核，未冒充全48逐行独审。

完整35796B新增 patch 的全部502行 body逐字重建，三件 bytes/SHA均等于真实停止副本；完整2630B RevisionDiff 的两段 current hunk 逐行匹配，逆重建分别匹配索引中的首批 SHA。逆重建是派生文本，不声称重新读到原首批物理副本。详见 DiffReconstruction.json。

64 个有限输入最终 differences=[]，包括51源、6正式件、3 EarlyTypedAbi、任务卡/两AGENTS、有限新增停止 ADR0074。InputPins 在初始全文读取之后建立，报告只声称该捕获边界到末核无变化，不倒填首次读取前快照。ADR0074经 InputSupplement 单列：8841B、fe82d5db54489e48080efa4bbda03fe7c4d5c6f76bdd56c395f48d321fbd953e；第3行仍待独立设计审，本片只核其 gain 明确语义，不关闭完整 top plan/still 设计。

## 两项必须修复的源码问题

### LOMD-P01：任意 gain 上限拒绝合法 typed 输入

P2，Media，OPEN_SOURCE_STATIC。local_material_edit.py 第74–76行在等长检查之外，追加 track.gain > 4 并抛 local_audio_range_invalid /422。三个 driver 都由 _LocalDriver 第122行在实际渲染前调用此校验。一个其他来源、引用、range、网格均合法且 gain=5.0 的音轨会因此被拒；不需要运行媒体才能确认这一控制流。

停止唯一 ABI 第162–167行仅规定 strict finite float、ge=0；ADR0074第27行明确不得增设任意上限/clamp。实际合成仍需真实解码、失真和质量检查，这不构成用无合同阈值替代输入语义的理由。由 Media 移除新增任意上限，与唯一类型一致；保留 range/样本网格、finite/非负、原权限/lease/费用门和真实质量检查。volume 在第115行，旁白 limiter 在第186–187行、最终 mix limiter 在第318–319行。原早 Finding 中“旁白 limiter 第190行”定位不准确，已独立 LineAddendum 保留原件并更正；主违规行和结论不变。

固定早单 Finding-LOMD-P01.md SHA ae880aa0a2865c6df04c94c8ae351cd0985fc6f665ed7005d1b5b3e0297e37a2。高增益的真实 FFmpeg 数值/失真行为 NOT_RUN，本结论不宣称任意合法 gain 必然成片。

### LOMD-P02：原静态图片 has_video=False，被新增输入/封面门误拒

P2，Media，OPEN_SOURCE_STATIC。停止原 media/ffmpeg.py（23252B、9a64674190c7b7206905e809647a041a68953e6e928094abe1dadf4314babfdf）第363–373行确认静态单帧/正确 codec，随后第449–457行返回 image MIME、decoded、尺寸、duration_us=None、has_audio=False，且 has_video=bool(videos) and not image，因此正常静态图 has_video=False。

若可信 decoder 沿这条原 probe，新增 LocalVisualMaterialDriver 第212–214行在 still 分支之前要求 has_video=True，合法 JPEG/PNG 已在 local_visual_source_invalid /422 处被拒，后续保持/运动分支不可达。另一独立路径：即使输入全部是真实 video，edit 第326–334行真实生成并检查 JPEG cover，_complete 第157–159行同样要求 has_video=True，正常 cover 将触 local_cover_invalid /422；该门位于任何 finish_output 第161–166行之前。不能把这一源码推导称实际生成、登记或 Bundle 失败。

由 Media 区分 image 的 MIME/decoded/尺寸/无音轨/无时间事实与 video 真流事实；video/mp4 继续要求 has_video=True。不得伪改原 probe/已注册 Asset、图片 duration 或取消完整 decode/三输出预检查/finish_output。此问题不依赖 still display-range 最终合同。后继应独立验证实际图片视觉与有声视频 cover 正向，损坏/多帧/音轨/尺寸反向；本片不授运行。

固定早单 Finding-LOMD-P02.md SHA c7a822dfbc60e66ee985c20e57108d5df85630a9689206c5b034eaa91e4b36c8。

## 剩余源码链的有限支持与边界

**根与实际来源。** RevisionTwo 改为 manifest.parent 作为安装根，移除 factory runtime_root 为安装根的首批错误假设；该 factory 参数实际是实例 scratch。loader 第17–27行要求绝对 manifest、逐父路径无 symlink/junction、文件/上限/固定SHA及 contained_file；第31–60行核实际索引、唯一 casefold 路径、size/SHA及所选工具/source_ref。check_sources 第62–77行在 build 前重核 manifest、index、所选源及本 helper SHA集合。来源完整性、固定 hash 和调用方传入 registration 仍不是 Owner/current 权源；新类是 Path 读取，没有因此证明所有 TOCTOU 原子安全或真正安装资源存在。源标识集合核不等于已完成 native-held 当前对象安装授权。

**同 Run、权限和旧账本。** factory 保原 builders 签名与 BoundProductionDriver，原 output_scope 检查同 Run、step/hash、distinct attempts、受控目录及不覆盖已有文件；原 permit_scope 核当前 AttemptControl、run/fence、route/capability/destination、owned_local/no secret/credential/maxcost=0并委托 engine.get_request。新 driver 不创建自己的 Operation、lease、key 或预算，也不把 hash/source fields 当授权。原 Flow _generated 第333–370行保 begin_step、已完成 Step 的真实 Asset复读、allocate、OperationIntent→executor、unknown/pending reconcile、原 ordered manifests 和 worker commit。其 body 仍是旧 Creative/request 结构，与新 {bindings,timeline}/clips/narration 并未接通；不能称本候选已进入真实本地 Flow。

**真实输入和输出。** binding_asset 第79–92行从原 bundle/lease读取 Asset和content，逐项核八字段、bytes/SHA、真实 decoder probe 并后核 bytes/SHA；plan probe 与实际不一致会拒。derived input 保 same lease读取、独立 Asset/MIME/SHA/probe与 clip顺序，但实际成功 Step→clip/narration来源须由未实现新 Flow提供，不能用任意 Asset IDs冒 Step lineage。_complete 对所有 partial 完整 decode并检查 MIME/actual duration/dimensions/流，在任何 finish 之前完成整组检查；原 install_output 使用 no-overwrite硬链接、当前 get_request、decode、worker.finish_output，变化/失败保 reconciliation证据。该序列并非三文件原子提交；不凭源码声称 rollback、竞态和 crash 已实测。

**视觉/音轨与真实 master。** 视觉 derivative 明确 -an、实际范围裁剪/归一化/固定 contain或cover和整数帧网格；图片的 display hold 是候选假设，不能解释为源图像固有 duration。旁白是独立 PCM WAV，仅选 narration tracks，真实 trim/resample/volume/延时/混音，最终 edit用受控 silent clips +该旁白 +显式 background_audio；不会暗接原视频音轨，选用视频音轨作背景需真实 has_audio/source_range。最终编码同时产带音轨 video、mixed WAV、cover，独立 narration由前一步保存；未把文件改名当编码。_complete 的图片错误仍使这条声称完整的路径被阻断。

actual_probes 来源为真实 decoder（未在本轮运行）；timeline、derived_duration、target_frame_count/fps和sample_rate字段为目标/计划值。现 MediaProbe 不测 MP4 帧数/FPS或PCM实际样本数，不能把这些计划字段称实际计数或 precision。实物 AAC/容器时间舍入、帧/样本映射、失真及最终四 master质量仍须真实媒体证据，源码 argv/严格 duration 比较不能替代。

**固定 argv与生命周期。** 源路径由 bundle和受控 storage解析，FFmpeg为 indexed工具，shell=False，固定输入格式/protocol白名单；filter仅已 typed 的数字、fit枚举和内部label，未接用户 filter/path/provider/凭证。AttemptControl 合并 cancel/父deadline，ContextVar finally撤回；_run 保真实 Popen/ProcessTree、输出cap、取消/超时kill/wait/tree_empty与失败reconcile。旧 decoder含完整 probe和真实 null decode、整体timeout剩余检查。保持同原句柄/无偷偷重 dispatch及 partial留证方向；本片没有 OS/Job/descendant/时钟/cleanup实际观察。

## 四项原声明缺口与后继责任

1. Top-level plan、trusted final-context、新 LocalMaterialServices/PolicyServices与真正 local Flow/Backend application接线仍未实现。Backend维护 sole grammar/facts/current host，Media维护 composer/Flow/factory/Bundle消费；旧 Flow不被新类出现自动替代。
2. Still display范围目前是零起点 hold假设；原图像 duration=None必须保持，具体 top grammar/still含义待合同及后继独评，不伪计视频时间。LOMD-P02修复不能绕过此独立缺口。
3. Integration真实 installed local manifest、完整源/tools/license，以及 Backend已安装/current rights/零费 routes尚未就绪；普通 JSON/verified/hash不能授权。
4. 当前仅 explicit voiced-video算法；无旁白/纯音频等 requested outputs分支和实际 Step lineage尚未完成。不能隐式增加、省略原 outputs，也不能用旧 shot/任意已存在 Asset作新来源。

这些原 Gaps 不冒充新P2，也不由本 Review静态支持关闭。真实 ASR/CTC、两authority/precision、RAG/字幕、完整Bundle/HTTPMCP同Engine和三OS资源/权限要求均保；未运行任何产品或媒体、未应用候选或授资格。

## 保留历史、交接与停止

原首批 scratch根假设由 RevisionTwo窄改；只支持该来源链的 SOURCE修正，不说运行关闭。原51索引全输出读取57f36e超过输出预算且Depth3告警，保留该截断，之后按实际必要记录/全文源码定向补齐；不声称全索引输出为全文证据。原完整 source与patch实际读取/文本重建不依作者AST bool。Root自身6a7850 PowerShell语法错误不是本产品结果，保为交接定位历史。早 finding不准确旁白 limiter行经独立勘误，不回填原件。

Review未修改实现/标准/依赖，未读热文件，未执行候选、第三方import、FFmpeg、Pydantic、SQL、测试、网络/模型/费用。回滚范围为未应用候选材料，无生产回滚操作。两P2由原Media新停止阶段窄修，后续独立源复审及另行真实测试准入；Review不代修、不审批应用。

过程：G:/开发测试/Codex/VideoCreatorImplementation/Review/LocalOwnedMaterialDriversIndependentReview/。InputPins/InputAfter、ADR补充、完整DiffReconstruction、两Finding/行号勘误、Handoff及FinalizerTerminal为正式伴件。最终工具自然终态由末回报记录，所有本 Review工具/读者释放后 TRUE FINAL；不能从文件存在推运行终态。完整 R1 独验后连续 R2仍未完成。
