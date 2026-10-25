# Qualified completion 两项修复独立评审

结论：MDCP-P01、MDCP-P02 在下列两个 AppliedStage 精确版本上均为 **CLOSED_SOURCE_STATIC_ONLY**。本轮没有确认新的 P1/P2。该结论只消除原源码中的 completion 类型/MIME 与 evidence union 接缝，不证明实际资格资源 observer、Pydantic 解析、SQL 提交、媒体执行或完整制作流程成功，也不授运行。

评审角色：唯一原 Review。任务卡 `docs/task-board/QualifiedCompletionCorrectionsIndependentReview.md`，SHA-256 `9cd2bd4299a69f4af5453365c7f1495709930582c806cfbb5a88a1ae0ce9728b`。过程根为 `G:/开发测试/Codex/VideoCreatorImplementation/Review/QualifiedCompletionCorrectionsIndependentReview/`。只读停止普通副本；没有读取后继 0066/31 测试或热生产源，没有 import 或执行产品、第三方、Pydantic、SQL、native、模型、测试。

## 版本绑定与独立核对

Media 当前根：`G:/开发测试/Codex/VideoCreatorImplementation/AgentMedia/QualifiedCompletionKindCorrection/AppliedStage/`。48 件索引 SHA-256：`e90b574d8d179c280bbdad5da413ef854f8cc5fdc89d91ab1205370a339f228d`。Handoff MD `9566d362a93d6e63184607b2bcaa357010522599e473b503bd564e15f555d7e4`、JSON `b71a44a9192efd6d2453d17581e4b69a660d4bb3adfa98673c2644f4b451a8e3`、ActualInterfaces `3dbbf4ad899b4d1260cd5f91d17a62a04be46fce3053078b42b06ec9cbb097eb`；完整 Full.diff `39af29d12201044ac93a7ce77aa62e5766251fe14b1b4274c3e2c5cf1c00ce73`。

Media 修前停止根：`G:/开发测试/Codex/VideoCreatorImplementation/AgentMedia/ComponentDiagnosisAndRecipeProduction/SourceStage/`，48 件索引 `a7f27d6f44c1e9a1109545b835419cbdbdbd200f478b3405d7300d4bdb9dfff9`。实际只有 `providers/component_diagnosis.py` 变化，47 件原字节保持。

Backend 当前根：`G:/开发测试/Codex/VideoCreatorImplementation/Backend/QualifiedCompletionEvidenceCorrection/AppliedStage/`。131 件索引 SHA-256：`bb03b22b70fb4de8374512613d720e9b35bb7c33f67582f95f67f3f4d43edeea`。Handoff MD `698d60d9193816fd7caee6f22cea554811fb649665a0a4567662ebcb09066869`、JSON `89782c0a8b814984e75b9beaa6503748186289a2b3e9367476d22567fc78a3c0`、ActualInterfaces `e9ee5fe7bb262e66588831bc701b54c38ff5d8ee021b0cede5dfb76f863e9bff`；完整 FullDiff.patch `a1cc7c784198d3b882cb55cdf02744f145f849143d502c951f64318ea8b50fe4`。

Backend 修前停止根：`G:/开发测试/Codex/VideoCreatorImplementation/Backend/DiagnosticSelectionTerminalImplementation/SourceStageRevisionTwo/`，131 件索引 `68df7b4e54f9a4431645349df1d3cd1bd6b1154f86f87552b559acde336ffda1`。实际三个文件变化，128 件原字节保持。本报告没有用后继 DST 修复 b58c 索引替换 bb03。

| 当前 ordinary 相对路径 | 字节 | 修后 SHA-256 |
| --- | ---: | --- |
| Media `providers/component_diagnosis.py` | 19322 | `461a28d076c53d3a6c59ee11bd37ccebda3701f5a040580bd600e2c48cfc951e` |
| Backend `services/engine/src/video_creator/application/component_diagnosis_service.py` | 69481 | `b73938149e2ba87daf9c4c88ef6b996dfa7b025db3acc922c248d363f0cf965b` |
| Backend `services/engine/src/video_creator/domain/component_diagnosis.py` | 15359 | `1d3b07b9a253e56f812e99517841a30b509a584b473f4cce77c014bad871ac3b` |
| Backend `services/engine/src/video_creator/domain/diagnostic_recovery.py` | 12593 | `705a548d339d67ef85c868c679524cb064d51ddba2cff914279ae264a241b7a9` |

InputBefore 固定 381 个有限文件路径：两套 Media 48+48、两套 Backend 131+131 共 358 源副本，加四索引、规则/任务/正式证据及三个 Media 已消费 Backend domain 副本。逐路径大小与 SHA 核对没有 mismatch。三个外部普通 domain 副本与本次 Backend 的同名源大小/SHA 相符。完整两份 diff 共七个 hunk，独立逐上下文/删除行核对，在内存重建全部四份修后文件，大小/SHA/全部字节与实际普通文件一致；不是 apply、import、编译或产品运行。详见 InputBefore、InputCountCorrection、DiffReconstruction 和 InputAfter。

## MDCP-P01：三种实际 completion 不再共用不存在的 MIME 字段

归属原 Media。原 Finding-MDCP-P01.md 保留，SHA `b0a31ce0543fa47d452db1c21c2311615e52e4a79729929411f6f3a091982737`；原失败条件是实际 qualified_resource 的 DiagnosticMetadataRef 没有 media_type，而旧 text_sources 访问了该属性。原条件性 SOURCE P2 不改称实际 OS/媒体失败。

完整修后 `SourceCopies/providers/component_diagnosis.py:31–53` 的 `_completion_text_body` 检查真实类及 kind：DiagnosticFeedbackCompletion/feedback 与 DiagnosticResourceCompletion/qualified_resource 使用完整 UTF-8 body；仅 DiagnosticMaterialCompletion/ready_material 在确认 ref 的实际类为 MaterialReceipt 后于 42–43 读取原 MIME。其他类/kind、非 MaterialReceipt 或坏 UTF-8 明确 422；未补造 MIME、未截断 body、未用 hash 替代 text。非文本素材保持原文本路由边界返回 None，完整原二进制仍进入本地 observation 的 body_hex。

调用链完整核到：`workflows/component_diagnosis.py:16–33` 逐项读取全部注册 completion；每项先 attempt.check，再调用原 port.read_diagnostic_completion；只接受非空、至多 2MiB 的真实 bytes。analyse 44–60 先获取这些完整 body，再原 begin_step/prepare_operation/executor；未知或未 settled 仍拒绝且要求 reconcile，不新造操作。`providers/component_diagnosis.py:172–175` 在原 text_sources 中调用新 helper；95–158 的本地检查仍将所有原 completion ref 放入 source_refs，并保存每项真实 kind/ref/SHA/size/body_hex；227–247 的原 verifier 重算并比较 checks、measurements、input_key、完整 completion_sources 及 limitations。未 drop completion 来避免异常。

这支持原 P01 在本固定源的关闭。资格资源 body 是否来自真实 observer 仍由 Backend 原认证读取端口负责；类型或这份 helper 不授资源资格。

## MDCP-P02：唯一 strict 类进入原 evidence union，实际 held 成员仍必需

归属原 Backend。原 Finding-MDCP-P02.md 保留，SHA `abd1c59ceb76b11d3fe97f773dd058d2b8777e70d1c5d4b70f3963e7c383c308`；原问题是 qualified_resource.ref 被所有检查引用，而原 DiagnosticEvidenceRef union 无该严格类。不能靠删 completion 或放宽字典绕过。

完整修后 `SourceCopies/services/engine/src/video_creator/domain/component_diagnosis.py:59–65` 定义唯一 DiagnosticMetadataRef 并将其加入原五成员 union。三个字段与旧定义逐字相同：record_id 1..512、content_sha256 原 Sha256、size strict 整数 1..2MiB。原 FinalModel (`domain/current_final_evidence.py:25–26`) 的 forbid-extra/frozen/strict 保留。`domain/diagnostic_recovery.py:9–18` 从该唯一类 import/re-export，RegisteredDiagnosticInputRef 仍继承它并只加原 input_key_sha256；CompletionRef 三成员及原全部 source-v1/v2/v3 字段和 validators 保持。完整两个 domain 文件已读；相关依赖的反向 component import只出现在 affected_recipe 的函数内局部加载，没有新增顶层反向 recovery import。此为源码结构判断，尚未实际 import Pydantic 验证。

`application/component_diagnosis_service.py:419–474` 完整校验先把原全部 completion refs 加入有限 known 集合，442–444 的新分支对 MetadataRef 另要求：必须与实际 inputs.completion_source_refs 中 kind=qualified_resource 的 ref 相等。不能仅因 union 接受对象而成为来源；473–474 仍拒绝未被实际 attributed checks 消费的任何 completion。原实际媒体/shot/range、脚本、独立 precision report、actual Operation output 和 text assessment 约束保持。

校验真实消费者没有旁路：`_record_component_diagnosis:541–620` 在 actual held inputs/current 与原 settled Operation 后调用该校验（557），再调用原 factory-bound verifier（559）；immutable facts、索引/selection 冲突及同 writer 前后 current/source 行校验保持。`_read_explicit_diagnostic_record:744–806` 重新读取 canonical registered v1/v2 输入和实际 completion captures、核真实 Operation，再在 792 调同一校验，并于 793 调原 verifier。没有因新 union 停用整个 ref 认证或历史记录检查。

这支持原 P02 在本固定源的关闭；不构成已观察到的 Pydantic 正向、SQL current/CAS 或消费执行通过。

## 认证、未完成和运行边界

`application/current_final_evidence.py:130–149` 的同一原 owning port 委托保持；`component_diagnosis_service.py:311–391` 的原同 service/lease/thread/fence、source snapshots、factory 身份和 current 门未改变。

`application/diagnostic_selection.py:58–166` 保留原 registered v2 完整/canonical envelope、稳定来源、accepted feedback production/new_run/目标 revision 和 READY 素材正文 SHA/size 校验；read_diagnostic_completion 148/165 在读取前后核 actual held current，且 149 拒绝集合外 completion。反馈返回整段 row.body UTF-8，素材返回真实核对后的 bytes。qualified_resource 在该模块 107、164 仍明确 diagnostic_resource_observer_not_ready/503；`application/diagnostic_resume.py:189–201` 的无 lease 路径亦仍 503。未将未来真实 observer 假写成 ready，也未把不存在的正文生成出来。

MDG01/02/04、独立真实资源安装/资格/observer、实际当前 Owner、runtime current/lease/CAS、媒体完整生产验证、独立多代理/人审、API/MCP、安装整包、三 OS 和完整 R1→连续 R2 仍未闭合。单 completion 的三个角色观点不算三个独立 agent。已知原 DST writer 缺口与其另阶段修复报告不能由本两项关闭重写。作者的 AST/Ruff/metadata 结果只作原准备证据，不代运行；本轮没有新运行结果。原旧绿/红/未执行记录和原 19 三次限制全部保留。

后继独立 Test 需在真实 authenticated/current inputs 下覆盖三 actual kind、MaterialReceipt 文本/二进制、坏 UTF-8、错类/kind、集合外 MetadataRef、缺 completion、真实 v2 record→explicit reader 与 source 变化拒绝。前置缺件时继续 NOT_READY；测试授权由统筹另行给出，本报告不签运行。

## 评审工具与原记录

所有动作均为普通文件读取、有限 byte/SHA 核对、内存差异重建或自身报告写入。初次合并索引输出 465af0 截断，未当全文 rendered index；后续采用实际 schema 定向读取。cb4007 自有定位工具自然 1：旧 rg 可执行路径已不存在；1f8b38 更新实际 Get-Command 路径，猜的 diagnostic_recovery_service.py 不存在，其后按停止索引/固定 application 定位到 diagnostic_selection.py。02b214 对猜的 workflows/current_attempt.py 无命中，后按固定 workflow 确認 attempt_control 委托。52b0c6 自然 1 为末次 rg 无匹配，原输出保留；955c98 明确区分函数内局部 component import。上述是评审定位/查询记录，不是产品失败或可运行结果。

7d055a 输入核对自然 0；其 source_counts 因 PowerShell 属性枚举写成逐项 Count 数组，原 InputBefore 不覆盖，InputCountCorrection 单独准确记录 48/48/131/131 和 381 原路径，没有改源/基线。db5e6f 差异重建自然 0，全部四份修后 byte/SHA 一致。末次输入核对及真实自然终态将在同过程 FinalHandoff/FinalizerTerminal 固定；最终 Agent FINAL 在实际工具返回后确认，无 live 句柄，全部 reader 释放。文件存在本身不证明工具终态。
