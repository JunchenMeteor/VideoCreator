# LocalMaterialFlowSourceIndependentReview

结论：本片为 SOURCE_STATIC 独立评审。LOMD-P01、LOMD-P02 在下列固定 edit 实现中可记 CLOSED_SOURCE_STATIC_ONLY；新增 LMF-P01 为 P2 / OPEN_SOURCE_STATIC / Agent-Media，阻断两个候选的正常本地工厂装配。Media55 / Backend134 整体仍 NOT_READY_FOR_APPLICATION，未应用、未运行；没有完整制作流程、安装整包、三系统 R1 或连续 R2 已通过的证据。

## 输入与覆盖

任务卡 `G:/开发测试/Projects/VideoCreator/docs/task-board/LocalMaterialFlowSourceIndependentReview.md` SHA256 `887ddd0122d52a4f523fe6bf405f189c4342e103c6c929e87c24d658808967d0`。治理和正式交接先读后 pin；实现源码评审从 InputBefore 后开始。所有读取限定停止 ordinary，未用热生产 source_path 作证据。

| 固定材料 | SHA256 |
| --- | --- |
| Media55 SourceIndex.json | 95dc15020b56965c169b0c108d519290e1743115480e288164f3d1c86c6b68c1 |
| Media CompleteSourceDiff.patch，62436B | 790ceb5512f2020d348b8899192ffbed43e9a4f0bc4442e2a2f0827fdb56ceb4 |
| Media Handoff.md | ac7922a6ef3f36525dd2c0bc3027c01cafce3936aa7a59038d60a7f84451b3f9 |
| Backend134 SourceStage/SourceIndexLf.json | 0c662eecb4727586d84e102e527481c99fdb4cc818116ad551b052beffc849ef |
| Backend Full.diff，47144B | 0a1c4062f7172e6a855d7264b62cbd262e8e73fa09d580ba8931c2e18670cee4 |
| Backend FullVersusApplied131.diff，92446B | a042bf2ddb74f052136dd50f85b5f801a5b8827a412c7a34d73de12d52c76b5c |
| Backend Handoff.md | ab2004a1b3f601ce4d356baf1213863a5e33430d80eeef3b14150b6f92277fc5 |

过程根 `G:/开发测试/Codex/VideoCreatorImplementation/Review/LocalMaterialFlowSourceIndependentReview/`。InputBefore 的221条包括55 Media、134 Backend、5 EarlyAbi、27治理/正式材料；35条补充独立保存在 InputSupplement，不回填 Before。InputAfter 去重核239路径，大小和 SHA 全部一致，differences=[]，SHA256 `352d700eb1011255b915b96b217805f6c8fafa217cf1e997c0236b122936fb8c`。这不是环境或依赖资格扫描。

独立消费全部三个 patch：分别917/683/1447行、5/8/12文件，逐 hunk 验证旧 context/removal/count，再在内存重建 UTF-8/LF 新字节，与各实际普通副本完全匹配；不 apply patch。DiffReconstruction.json 保留逐件结果。全文读 Media 四个新增模块及改动 edit、必要旧 drivers/FFmpeg/Worker；全文读 Backend sole domain、local source reader，并完整读其余实际差异及 permissions/host/ASR journal/final consumer/authority/setup 的相关完整方法。55/134 全件有大小/SHA身份核；未声称对所有未变文件逐行重复全文审计。

## LMF-P01：实际注册 Executor 被新工厂拒绝

P2 / OPEN_SOURCE_STATIC / Agent-Media。固定 Media 普通源：
`G:/开发测试/Codex/VideoCreatorImplementation/AgentMedia/LocalMaterialFlowAndBundleCompletion/CompleteSourceCandidate/workflows/local_material_production.py`，32969B，SHA256 `9cb8730648cf12b61d838d814f1e181b8c2712e446dd428c5ff2c4fa248b70cb`。

`_services` 第104–111行以 `type(executor) is not OperationExecutor` 拒绝子类。实际 Backend 普通源 `G:/开发测试/Codex/VideoCreatorImplementation/Backend/LocalPlanBackendCompletion/SourceStage/SourceCopies/services/engine/src/video_creator/application/media_registration.py`，SHA256 `956da9606f53ef2c2d1daaced1cd998516ba06efdd4f459aa918632fdb37b60a`，第241行创建 `RegisteredOperationExecutor(engine, self.journal)`；第418–423行原样传入 self.executor，第447/461行调用 policy/human 两个 local factory。

同固定源 `application/asr_result_journal.py` 第307–310行声明 `RegisteredOperationExecutor(OperationExecutor)`；25540B，SHA256 `3a89b57b078c2a75ba012bc6afffb2c0fa1b440806e9fc03045fb2143ecc0ee5`。第312–350行保留真实 ASR/CTC、child 与原 journal 的职责，普通 local Step 委派原父类路径。

触发条件：本地注册、资源和原 human/policy 授权满足，宿主按真实当前代码进入 `_current_services`。新工厂将这一真实 executor 判错，抛 `local_services_binding_conflict` /409，发生在 drivers/Flow 构造之前，两正常入口均受影响。这是完整实际调用链的静态条件证明，未构造对象或观察实际 API/OS 故障。

最小修复交 Agent/媒体：按实际注册宿主的明确安全类型/来源接纳该 executor，继续检查同 Engine、Worker、Bundle、原对象身份与 journal/guard；不能换成无 journal 的裸 executor、创建另一个 Engine，或放宽任意 duck object。独立早单 `Finding-LMF-P01.md` SHA256 `95363b78eea3a70fa90c988e3c0f6fa1f2af9509a43200d4bac3ef1312e425f4` 已交 Root。Review 未修实现。

## LOMD 两项有限关闭

固定 `CompleteSourceCandidate/media/local_material_edit.py`，24334B，SHA256 `6e83f65a7024949adfaf93a3fe89248149c729d3bbaaa8d6ecdff5f3e9d3e665`。

LOMD-P01：第74–80行取消任意 gain>4 拒绝；Backend sole domain 第168行仍要求有限、非负线性幅度，不擅加上限或 clamp。音频第119行真实 volume 消费 gain；gain=0 的合法静音 track 与第180行 narration 正增益条件区分，混音 normalize/limiter 保留。原有限性、音轨用途、解码、来源和输出检查保持。CLOSED_SOURCE_STATIC_ONLY；实际 FFmpeg 音量、失真和听感未测。

LOMD-P02：第161–163行 cover JPEG 和第217–222行 JPEG/PNG still 接受真实 `has_video=False`、无音频、duration=None、真实尺寸/MIME；MP4 仍须真实 video。原 `media/ffmpeg.py` 第449–457行 image probe 确实按 `bool(videos) and not image` 返回 has_video，静图尺寸来自实际 stream。第83–96/147–171行原字节 SHA、decoder、MIME、原输出契约保持。CLOSED_SOURCE_STATIC_ONLY；实际 JPEG/PNG、cover 输出未运行，也没有关闭 still display-hold 语义的 LMPT-P02。

以上只更新本报告中的有限裁定，原 LOMD 报告、原错误和固定51基线没有回填。

## 相干实现支持与仍开放事项

Backend sole 11 字段严格 grammar、UTF-8/duplicate/nonfinite/extra 拒绝、原 request/Goal/script/input-ASR 来源已真实接入。local source reader 第65–143行查询原 Goal/accepted、原 user script 或真实 settled Op/committed Step 与实际 input audio；损坏不会当合法缺席。第145–206行先在原 held source 获取六事实及查询快照，释放读 guard 后执行原 verifier；第232–239行在同实际 writer connection 校验同 lease/source 快照并重读原 rows。`production_admissions.py` 第650–706行将该原快照检查置于持久化前后，原 transaction 异常 rollback 路径保持。这是源码保护支持，未作 SQLite 事务或竞态实验。

Media 新 Plan 保留原有序 asset set、完整 body/request、accepted Goal 与实际 script ref；原存储 plan 恢复不会另造来源或改预算。human/policy 分支使用不同真实授权 port，rights 全 tuple/source/目标/lifetime 与同原 checked proposal 保持。生成路径沿原 beginStep、OperationExecutor、零费 selected route、原 reservation/Worker 输出与 fence/current commit；unknown/pending 明确进入 reconciliation，不能重发当新成功。四个母版、最终混音 ASR、质量 observations/RAG/对齐有真实调用源码，不以单一回复、多观点或 hash 作独立质量证明。

仍开放：

- 新 LMF-P01 必须先修；尚不能把此 host/factory ABI 算可正常消费。Early source reader 的六事实/strict domain 与当前源码的数据接口可对应，不能消除该真实类差异。
- LMPT-P01 的真实本地 Creative/固定 insight+brief、原 Bundle 六版本与 applicable outputs/audio-only/noVoice 合同，以及 LMPT-P02 的 still source-time/display-hold 关系仍待 Architecture 的独立后继版本。本片未读活动0074修订；没有删旧 Bundle 门、造六版本或静音旁白。
- Backend `current_final_evidence_runtime.py` 第72–100行要求原真实 final producer 消费 local 七事实，新 consumer 参数缺失明确返回 `production_local_final_consumer_missing` /503；Media 私有 composition helper 不等注册的最终 Bundle producer。三脚本/四母版中间产物也不等最终 Bundle。后继 consumer/factory/实际 applicability 未闭合。
- 精确安装资源、ASR/CTC/RAG、两 authority、200ms、QC/Bundle、HTTP/MCP/Owner、人审、媒体成片、冷启动与真实 OS lifetime/竞态均 NOT_RUN；源中免费 route 不构成任何模型或费用授权。没有安装整包、完整制作流程、三系统 R1 或连续 R2 的验收证据。

## 原工具与停止边界

独评只运行 PowerShell 文本读取、SHA/大小、JSON 元数据与内存 diff 重建；0候选或被测 import/执行，0数据库、模型、FFmpeg、网络。作者 AST/Ruff/metadata 收据仅保来源，不能授运行。Media 原1850b7静态 exit1、后续6904ea/fc96df source0 和 Backend 原冻结/边界收据保留，未重跑或洗绿。

自有 a6af1f /1 是 ReadPart 参数数组类型错误，后14d83e/617118纠正；不是产品失败。3个聚合输出曾截断，已按精确遗漏方法补读：21128c 补 Backend Handoff，617118/0fcfc3 补 port/admission/preflight，0fcfc3 补原 host invocation/Worker 生命周期差异。完整 patch 字节消费由7f2cb3独立重建另证。原错误与截断不作全文成功声明。

当前末核099464自然 exit0，无 live shell/session；239输入无漂移。停止所有来源读者后仅写本 Review 的正式文档。完整原工具记录与最终文档 SHA 见本过程 Handoff/FinalizerTerminal；实际最后写入工具自然返回须由 Reviewer 的 TRUE FINAL 消息确认，不能由文件存在推断。
