# RV21 — W12第1轮整改独立静态复审

**FINAL / STATIC_REVIEW_ONLY。原四问题：P01与P04只关闭固定候选的静态缺口；P02 OPEN；P03首跳结构部分关闭，祖先闭包与再分发许可仍OPEN。** 未签运行、Binding、业务Bundle或R1。仅允许W12两个workflow及B11历史副本；当前Backend/B14 application、B13API、T19 WIP均未读取/import。完整R1独立三OS后连续R2、安装实例持有数据、五步工作台不变。

## 精确固定输入

| 输入 | SHA-256 |
| --- | --- |
| RV21卡 | fef8602f75779251a9474b2e2282551f2d9b83ad41b205bbc1e404e6dee323e5 |
| 原RV20报告 | 19c5859781b09e62b39b2e3c608bd6ca3d299960b3bd4bb3f22eb9219f57e826 |
| W12Handoff Markdown | 55070a5b2548655c5a4016dfc09bb3a374335cb42b04da7cc478fcda2bc73e37 |
| W12Handoff JSON | 30a3b9f146b720a48aae5231b4d87400067895c6a161c04521e74941b228afd5 |
| W12SourceSnapshot | 9bbe7f8c26e298a51de3497ec77fcc35c19bccd1f4d318cc7cfff142e18991f9 |
| bundle_producer.py | 3940a67705c5eab3198cd7fc79965620d8fb87c7d11e8dad2ddcf7f16efb7622 |
| bundle_v03.py | 51c107f7d3d0048a1b83cfdf295724c5b9cfbee25eeb41439b4e626491873cfc |
| 成功SourceDiff | 801852978a71394c9e8c09cbbd73fc8f4f15953fa6234b53726889982685c751 |
| B11历史bundles正文 | fa4e26de0833bb4bee4cb3e41a38e0cd955beb1bc85db8de54812689f4b0ca69 |

本轮独立核当前允许的两源码、SourceCopies与BeforeCopies全部相符；旧Before保持fe1153c3608626429d7ef8e202f8640f4a62e6354823cb0566c29f3d5cac42c1 / 93d4ed63287bf92f7213ee4a8586c3928f871c17beae15d8ddc1398dd2580e09。只核元数据记录的另外三ASR pin，不读取其当前源。历史Backend仅读[固定B11副本](G:/开发测试/Codex/VideoCreatorImplementation/Backend/B11/FinalSourceCopies/Application/bundles.py)，未读当前生产路径。本文所有Backend行号都指该fa4e历史身份，不能外推B14未来新源。

## 原四问题结论

| 问题 | 本轮判断 | 精确范围 |
| --- | --- | --- |
| RV20-P01/P1 | CLOSED_STATIC_RUNTIME_GAP_SCOPE_ONLY | 不再把合法无本片P95恒写成未解决runtime gap，真实失败/缺项仍阻断 |
| RV20-P02/P1 | OPEN | 质量rights仍not_measured，缺实际普通lease权利事实端口与消费 |
| RV20-P03/P2 | PARTIAL_FIRST_HOP_STRUCTURE_ONLY / OPEN | 首层原bytes、新Allocation/Receipt、role/forwardedge补齐；祖先闭包和再分发许可未完成 |
| RV20-P04/P2 | CLOSED_STATIC_EXPIRY_PROPAGATION_ONLY | RagChunk.valid_until_us等于实际所引用right.expires_at_us；并非授权/发布通过 |

### P01：固定误记缺口已修，原状态转换未改

[Producer第130行](G:/开发测试/Projects/VideoCreator/services/engine/src/video_creator/workflows/bundle_producer.py:130)在0.3只保controlled actual.runtime_source_gaps，0.2仍原字段。 [v03第49—67行](G:/开发测试/Projects/VideoCreator/services/engine/src/video_creator/workflows/bundle_v03.py:49)核runtime gap必须为明确非空文本条目列表/tuple；_work_runtime_gaps保Transcript实际gap、actual报告gap及原失败/未观测检查。failed alignment仍成为gap；非alignment的not_measured保未解决；rights仅在不属runtime policy时跳过，其最终质量权利门未跳过。

[第219—240行](G:/开发测试/Projects/VideoCreator/services/engine/src/video_creator/workflows/bundle_v03.py:219)用真实gaps决定complete/result/source_gaps，不再恒附“没有独立P95”句。无参考PrecisionAssessment仍not_measured/null，方法限制留原对应scope；真实gap/failed check不会因旧quality转换而洗掉。对照历史B111536—1539原拒绝条件，旧必然错误gap这一静态因果已解除。没有真实qualification/完整合法Bundle正向，故只关闭此源码缺口，不能称runtime验证通过。

第212—214行原quality_checks状态赋值与Before原文**逐字相等**，包括alignment→verified的原tuple。本轮肯定的是“未实施被拒状态差异”，不把保留原代码当新语义审批；原失败事实另保在WorkReport gap/incomplete。后续若需调整该状态行为必须按具体证据另审批，不换writer、工具或编码通道绕拒绝。

### P02：实际权利事实仍待，OPEN

[Producer201—205](G:/开发测试/Projects/VideoCreator/services/engine/src/video_creator/workflows/bundle_producer.py:201)仍为rights not_measured。历史B111819—1836先要求七项verified，再核真实Owner assertion/authority/许可。缺前置事实不能形成可释放不可变quality；W12没有翻True或降低后端门。BackendFactsRequest e3cb82e3c5189c547ee2b70420aa57e68d17cbdd0e23d7e63fa1d9340f4dc3da仅提出普通当前lease/preparation绑定的私有rights事实与原件许可来源端口，不是已实现接口/实际权限。B14正在处理，本轮不读取、不预借其结果。

### P03：首跳已补，但新增明确的祖先缺口仍OPEN

[v0370—79、126—150](G:/开发测试/Projects/VideoCreator/services/engine/src/video_creator/workflows/bundle_v03.py:70)保存受控原bytes并核完整文件SHA，使用typed CorrectionOriginRef选择旧precision_report/新precision_report_v03，保原artifact_id，拒碰撞；加入原件slot。 [159—166](G:/开发测试/Projects/VideoCreator/services/engine/src/video_creator/workflows/bundle_v03.py:159)实际调用fresh material_allocation→stage，核新materialID/grammar/SHA，不以源materialID冒新交付。[198—199](G:/开发测试/Projects/VideoCreator/services/engine/src/video_creator/workflows/bundle_v03.py:198)新增measurement→原artifact前向依赖；[Producer242—257](G:/开发测试/Projects/VideoCreator/services/engine/src/video_creator/workflows/bundle_producer.py:242)确实把该receipt加入Manifest，并给precision_evaluation role。这修复了原“读后丢byte/完全没索引首件”的结构缺口。

**RV21-P01（归属原RV20-P03，P2，Media/Backend事实端口，OPEN_STATIC_NOT_EXECUTED）：第二次及后续修订未带祖先闭包。**

具体反例条件：新测量C的corrected_from指真实已ready原0.3报告B，而B自身corrected_from又指A。历史B11_correction_closure1183—1195遍历所有索引中的PrecisionEvaluationReportV03；它既检查C→B，也检查已作为“原件”索引的B→A，要求祖先A实际material、文件SHA/精确类型及B artifact的forward依赖。W12只对一个origin读取/prepare/stage一次；仅给measurement(C)加origin(B) edge，correction_origin(B)依赖沿默认空tuple，A没有slot/receipt/artifact。因而这一合法历史形状仍会触发correction_origin_unavailable。这是固定源码推演，未拿synthetic byte fixture称真实历史或业务红。

后续由Backend受控原件事实口提供实际必要祖先与每层来源/许可闭包，Media按新Allocation/Receipt保持原byte/typed grammar/文件SHA/记录身份和逐层forwardedge；不能改历史、漏祖先、把可读取当可再分发，或借普通payload自选旧grammar。每层许可/expiry/用途必须真实成立。当前新原件artifact仍使用现plan right，尚未承接原件真实right/许可来源，故首跳结构修好也不代表再分发合法。最大链、重复/cycle、恢复/越权与实际事务尚未独立验证，本轮不发明上限或批准无限递归；结构限界交后续架构/测试。

### P04：期限字段静态已修

[Producer196—200](G:/开发测试/Projects/VideoCreator/services/engine/src/video_creator/workflows/bundle_producer.py:196)直接填valid_until_us=right.expires_at_us，永久为None、有期限不超父期限。对照B111816—1818旧拒绝条件，原字段遗漏解除；没有删父期限、扩大用途或绕过expired权利。真实权利是否成立、跨版本Backend行为和实际发布仍未测。

## 原owner证据与拒绝边界

owner Handoff记录ffb526、退出0，argv为仓库.venv Python -B -X utf8 FactsProbe.py；FactsReceipt28ec2eb8f507a5a44d0aa5c06d62ae41794ea2ca1d3e68cf6a93c91dc42f3533与原stdout FactsCommandedd84db7b6d853ac29c8ef974978a904797d89610e87d8ef105af9e93d27504b已读核。它是六组纯DTO/helper/source事实，**不是六个真实业务case**。

FactsProbe用SourcePort double返回synthetic bytes，只证明调用返回值/双版本kind/hash/collision；fresh Allocation、roles/edges是AST/字符串结构检查，没有真实stage、Ready材料、历史报告、权限或DB。RAG使用旧公共实验shape改期限，不是新获准record/hash。未覆盖祖先修订链。Reviewer未执行或重跑FactsProbe，不自造业务退出0。

[自动审批记录](G:/开发测试/Codex/VideoCreatorImplementation/AgentMedia/BundleRemediation-W12/AutomaticApprovalRejections.md) SHA958471c14eab846526c16cb30d6ae2a38f3475bfc317921fafbe0736c0907d3f、[被拒片段](G:/开发测试/Codex/VideoCreatorImplementation/AgentMedia/BundleRemediation-W12/DeniedStateDiffFragments.txt) SHAdac41cb9dfcc7daeaeaec8c876e3343a69a642bf99ce10193a77bb168c6d9c3c保留：两次拟alignment状态guard调整均未落，理由为可能削弱独立精度/质量门。片段不冒完整工具patch日志。拒绝后已停止该状态动作，成功SourceDiff仅含不受影响scope、byte/index与expiry修复；本轮不撤销拒绝、不代签状态变更。

## 结束与未测

本轮Source/copy/Before完整身份和原状态片段独立核匹配，原标准/失败不改。实际rights/原件再分发与祖先事实口、独立听审/benchmark/qualification、完整Bundle/API/MCP/三OS/MM05、真正Test harness/starter/Binding均未批准。旧B11副本不能证明当前B14接口已修。

全部源码reader与工具已终态，无live；后续本片只引用固定Snapshot，不再读当前生产。Reviewer产品/import/业务DB/ASR/解码/测试/模型/费用/key/网络/安装均0；仅写docs/reviews及自身Review/BundleRemediation-RV21。正式FINAL释放，后续Backend/Media实施、Test真实业务、Acceptance独立验收分别负责。

收尾source-after：仅两允许workflow重新核SHA，分别仍3940a67705c5eab3198cd7fc79965620d8fb87c7d11e8dad2ddcf7f16efb7622 / 51c107f7d3d0048a1b83cfdf295724c5b9cfbee25eeb41439b4e626491873cfc，无源变化。该仅文件身份读取已终态，reader释放。
