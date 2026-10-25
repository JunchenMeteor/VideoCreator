# ADR0020：受限准备权利事实与修订祖先许可闭包

2026-10-08。批准本协议设计与后续实施输入，不批准当前任何真实 rights authority、许可、Bundle 发布或产品通过。完整 R1 后连续 R2、实例持有数据、五步 UI、原 MM03/MM05/全部质量门保持；不改 alignment 状态或绕过其历史自动审批拒绝。

完整读 A17卡80505b3c7a96a2215840553506922c1be748ec501a9dd92365b270dee6a3cac6、正式 RV21报告2d5f7cbb93eee45fdaa4d57c35e668aa8396d2553a9314391dba681f44a89717、W12需求e3cb82e3c5189c547ee2b70420aa57e68d17cbdd0e23d7e63fa1d9340f4dc3da；只读 B11历史 bundles fa4e26de0833bb4bee4cb3e41a38e0cd955beb1bc85db8de54812689f4b0ca69 的权利/修订接缝及正式消费说明。Backend供架构的稳定协议5b33ab3ea9a425a91251f6f847e9df6f5236472272be25b6a07b8688768c60cf、私有模型普通副本00277bb46d614a41940b436827d6a5af1bdaa27142cdf2df172947faa0bf35e9 已核；未读取 B14 当前 application/bundles.py 或 bundle_facts.py、未执行/import/测试。

RV21只关闭部分固定静态问题：rights前置事实缺失仍OPEN；第二次修订C→B→A缺祖先/许可仍OPEN，不拿源码推演冒业务红或架构批准冒整改绿。

## 1 保持两个受控服务口与真实准备事实

批准 `verify_rights_evidence(lease, preparation_id, *, rights, approval_refs, creative_revision_refs, artifacts, required_uses=...) -> VerifiedRightsEvidence` 与 `correction_origin_evidence(lease, reference, *, purpose='derivative') -> CorrectionOriginEvidence` 为普通当前制作lease的私有服务口。名字/唯一类型由Backend定义于自身 bundle_facts，不注册API/MCP、不生成第二套公开DTO。两口都重核同实例主体/项目/Production/Run/固定Request/preparation/当前fence；核实lease、旧fence、外来payload不得取得制作或复制权限。

`required_uses`不是Media可缩的白名单。Backend从当前真实输出/交付/来源复制意图与可信policy算最小集合，再核请求参数只可等于或加严：制作需要derivative；独立音轨/检索/平台商用等按实际目的补standalone_audio/rag_index/commercial_use；完整包实际导出需要export。原件或许可正文嵌入新可移植交付时还需其实际复制/redistribution授权，不把只有playback/同项目读取当许可。用途、平台、地域、归属/署名、有效期和限制均取真实批准，未知不默认无限；某分支不涉及某用途不虚构它已获准。

PreparedRightsContext保候选全部identity、rights/ApprovalRef/RevisionRef和ReadyRightsArtifact成员；只能由BundleService从真实journal/Asset/不可变文件构造。每Ready artifact须精确匹配同准备的真实Asset或ready Material、实际文件SHA/size/MIME/kind、稳定slot/receipt、关联right/method及许可引用；普通调用方BundleArtifact只是待核描述，不因类型签名/路径存在而成为事实。先逐原列表核重复/冲突/坏范围再建map，不折叠坏项。

ApprovalRef必须解析实际决策记录：主体权限、run/production范围、approve动作、固定target_revision_id、原decision_sha256及不可变CreativeRevision正文/SHA全部匹配。user_asserted仅在原真实Owner声明与完整RightsSnapshot相等、目的落在该明确授权内时可核验；这证明实际声明/审核，不称独立法律所有权认证。模型生成rights字段、一般“看起来不错”的建议、读取原件或root任务分派不授权。

context_sha256覆盖规范身份/全部权利正文、实际artifact/内容SHA/receipt身份、审批/用途及来源绑定，不含绝对Path本身作权威，也不含自己的hash。无future Quality/Manifest hash、未ready Allocation或伪占位。受限content handle仅是服务解析定位，不是许可票据。

## 2 可信 authority 准入及私有类型必要增量

批准可选 PreparedRightsAuthority 协议 `verify(context)->tuple[RightsAuthorityObservation,...]` 和 `assert_current(context, observations, *, now_us, connection)->None`。协议存在不等真实authority获准。可信安装构造必须固定：authority_id/revision、实际adapter源码/配置SHA、issuer/来源身份、获批主体/项目/rights basis/用途/平台/地域范围、实际许可/批准证据、有效期、可信更新/撤销渠道与本地revision floor。独立资源评审/准入后由Backend可信factory注入；用户/模型/普通API不能注册、指定module/path、回调True或自产approved。哈希只绑定字节，不能凭哈希或角色目录证明许可真伪。

安装配置属于受信启动边界，不宣称隔离能改本机文件的同OS用户/管理员；若adapter允许任意同用户可写文件自产“licensed”，没有真实来源/作用域/准入，仍不可启用。数据可本地持有、离线核可信已获准范围，免产品登录；官方账号状态不作为本地权利可信根。

Backend在候选私有类型上补以下明确成员，公开117类/旧contracts/API/SDK不因此改变：

- PreparedRightsContext增加 `stage: pre_quality | final_manifest`、`final_manifest_sha256: None | SHA` 及 `origin_bindings`。pre_quality只含当时实际ready文件；final_manifest在真实Quality/Manifest定稿后才含其actual hash/所有实际artifact。Manifest不反引final context SHA。
- `origin_bindings`为服务构造的不可变CopiedRightsBinding：完整原BundleRef/原artifact+file/record身份、原rights SHA、当前artifact/material/right身份与SHA、源许可ID→新许可ID映射、当前固定声明/批准/用途；无秘密或任意路径。它定位真实原件与当前声明，不能由Media伪造给authority。
- RightsAuthorityObservation保候选authority_id/context_sha256/rights_sha256/observed_at_us/有限valid_until_us/QualityCheck/evidence_artifact_ids，再增加 `authority_revision/configuration_sha256/revocation_revision` 与实际不可变 `grant_evidence_refs`（来源identity/revision/SHA/作用域）。每right逐项覆盖，验证完整去重/无额外许可扩张；bool/缺证明/旧context不接收。
- Verification_id仍仅私有事实定位，服务保存实际签发关系；不作为跨run/准备的可转移ticket。QC=verified仅在全部必要right/用途/证据成立；部分verified+未配项聚合仍not_measured/明确失败，不能补一个总True。

观察的有限valid_until不得晚于lease/来源许可/authority/适用证据的最早期限与获批刷新窗口；无永久伪fresh观测，未来observed时间拒绝。未配置authority时owned/licensed准确not_measured/not_ready；非None但未准入配置继续rights_preflight_admission_required(503)。实际许可否定/过期/用途缺失给原明确失败，不当“暂未测”掩盖。安装真实adapter/授权资料及独立准入是后续明确任务，不永久以placeholder代完整路径。

## 3 无环前验与最终 writer 重核

先固定实际媒体/文本/许可ready → 构造pre_quality context → 在writer外调用受控verify并核观测来源/范围 → Media消费真实VerifiedRightsEvidence定稿Quality → stage不可变Quality、构造真实完整Manifest → Bundle.verify在writer外重核全文件/完整许可与所有晚生成artifact，构造final_manifest context并取得对应实际观测 → 最终发布短writer assert_current并提交。

前置QC只声明其当时真实ready范围，不预授尚未生成文件；late Quality/Manifest不能改变已有rights正文或加入没授权新artifact。final观测为私有发布事实，不回填或重写旧Quality/Manifest，依赖顺序因此无环。真正需要完整Manifest的legacy authority只在此真实final阶段调用，不能用临时Manifest/未来hash骗前验。

writer内服务与authority必须本地、确定性、短时、只读核：实际当前lease/Run/preparation/fence、完整Manifest与final context绑定、权利/审批目标及receipt/journal版本、可信authority/config/current撤销revision floor、valid_from/expiry/observed期限、每source grant和用途/许可闭包。使用同一DB connection/受控发布顺序；撤销/配置变化与发布必须同writer次序。不能网络、hash整文件、读取任意文件、调用FFmpeg或供应商，也不能把外部“刚才True”当当前许可。

文件/完整内容hash在writer外实核，writer比较受控不可变存储/journal精确身份；这保障应用内有序写入，不承诺对本机特权篡改绝对免疫。外部许可状态通过可信实际获取/有期限本地事实进入此顺序，不假装离线知道所有尚未同步撤销。若adapter没有安全本地撤销/版本重核接缝，其真实authority准入仍not_ready；Backend补受控事实源而不是在writer里偷偷联网。

重启后临时签发事实不恢复成永久许可，重新核已有实物/声明/来源；不重生成/收费、不清未知预留。前置成功后撤销/改范围/lease换fence/Quality多artifact均拒最终publish，保持实际原因与恢复动作。既有完整published历史字节不覆写，当前可使用/导出状态另判。

## 4 原件 C→B→A 的确定闭包

correction_origin_evidence返回完整报告链、许可及必要来源依赖。每层必须来自实际持久Ready原Bundle的全文Manifest SHA与索引：source_bundle_ref、原BundleArtifact及其rights_ref/实际RightsSnapshot、受限content、原审批refs；原文件size/fullSHA、typed schema、report_id/content_sha256/alignment身份全部核。整个文件SHA与内部record hash不同，不能混用。0.3只按严格已解析corrected_from继续，0.2为历史叶，不用普通payload猜grammar或把旧错误精度授新资格。

从C的新locator解析B，B实际report自身再解析A。不仅读到A的原文件，还核B原Manifest中A的实际索引/byte身份及B→A forward edge；上级索引允许new copy materialID不同于locator原materialID，但完整文件/record身份一致。原件索引的权利与其引用来源许可也分别保留核验；不同snapshot不互相覆盖成较宽权利。

Backend私有CorrectionOriginEvidence增加 `dependency_edges` 与 `source_set_sha256`：每edge含实际父report/source BundleRef、其持久Manifest中子artifact索引identity/rights、typed child CorrectionOriginRef及实际child source identity。许可文档/额外许可依赖以候选CorrectionSourceArtifact类型存入 `license_documents`（包含完整必要依赖，并保roles，不冒仅license role）；来源集合hash覆盖实际manifest/index/right/file/审批/edge identity。Media不能getattr猜缺字段/只拿首件。

遍历每层report/其rights→license_document_artifact_ids→许可文档自身权利及实际必须的dependency，核正文/用途/期限/披露条件。真实权源可为已核authority/明确Owner许可终端；不能默认“license文本总可复制”、自指自批准或无限递归寻找虚构许可。read/同owner/project只是定位条件，不是衍生/导出/再分发许可；缺一层许可或真实披露权就拒完整闭包，保具体缺项。祖先基准分数、错误2N原报告和origin locator都不授本片精度/方法资格。

资源上界采用独立明确裁定：最多32个**不同源祖先报告**（不计新C）、最多256个全部不同源artifact（报告/许可/必要依赖合计），祖先深度也≤32，逻辑总字节≤实际实例AssetService.max_bytes（候选默认512MiB，实际配置较小时取较小值）。这是资源拒绝门而非精度采样；超过明确source_closure_limit/对应原Envelope，不截断、漏坏项或返回空祖先。较大合法链可后续按明确实例资源授权提高候选上限并独立复验，不能失败后自动放宽。

canonical source identity以实际source BundleRef/原artifact/material/fileSHA为键；共享祖先只分配/读一次，仍核每入边的全部约束/许可。相同artifact/report ID异hash/grammar/record/来源声明冲突拒绝；不同权源不能只因同bytes去重。用visiting与visited区分回环与共享DAG，report/许可/依赖环、自引用、互指、深度超限均确定失败，不无限递归。所有原列表先校验，去重不藏坏条。

Media先prepare完整必需slots，再为每报告/许可用**新**MaterialAllocation取得当前journal ID，stage原byte一次并核新Receipt；不得复用源materialID或回写旧件。祖先report的原artifact_id与原typed corrected_from locator保持，保证C→B→A身份可对照；与当前新C或其他source的ID碰撞拒绝，不改原byte消冲突。新BundleArtifact的复制元数据可以有新的material/current right/dependency引用；原source Artifact/rights完整事实另保。

按依赖拓扑先stage许可/最深祖先，再逐层报告，C最后引用B；Manifest索引包含每层精确role/版本/原file hash，以及C→B、B→A和各自新索引许可/必须依赖。源无关旧音轨/Alignment文件不因一个历史locator自动全部复制；其identity保持来源审计，凡声明为当前artifact dependency的则必须真实索引/许可完整。new measurement report只评新实际Alignment/reference，不能重测或修写B/A补绿。

## 5 原许可与当前声明的映射

每个复制artifact必须保SourceRightsSnapshot原字节/identity与许可来源，另有**当前**RightSnapshot和CopiedRightsBinding供新Manifest使用。当前声明不得较源更宽：permitted uses/platform/territory/归属署名/limitations按实际约束交集，期限不晚于任何依赖source许可/权威截止，起效不早于必要来源。license IDs可按真实新allocation索引映射，但不修改原source RightSnapshot或报告byte；将新映射固定到当前不可变rights声明后才能审核/核验，不能approve后悄悄改ID。

同Production且原声明完全未改时，只能按现正式审核规则复用仍有效匹配target/body的实际批准，不发明新批准。跨Production的旧ApprovalRef仅证明源条件，不满足新声明审核；当前user_asserted需当前Production的明确Owner声明/批准target。已真实预授权的受限policy/权源可以由已准入authority作当前精确自动绑定，记录来源和范围，从而支持unattended；一般方案approve或模型解释不能冒权利行政批准。未给此事前许可时明确等待当前声明/权限，不强塞旧决定或推断默认再分发。

不能把源licensed改成user_asserted/owned绕许可证据；真正独立新权源如证明不同basis，须新实际证据与批准，而非Media换字符串。原件、license文档自身的新复制permission也要核。RAG/引用的valid_until不得晚于其**实际**effective right最早期限；其他未受影响资产可保留，不以此重做收费。

原完整Manifest的legacy rights_authority签名/旧0.2请求/hash/报告和历史读取行为保持。只有legacy callback而没有受限prepared adapter时，不能用其造准备QC；owned/licensed前置仍not_ready。user_asserted的服务内真实声明核验可继续。已有合法历史包读取/导出仍走原当前授权，不为新adapter缺失锁本地；新的prepared发布同时核typed final事实与原完整Manifest守卫，不移除七项verified或最终license门。

import保原manifest/files/IDs/hash和origin_snapshot_only；源已导入/可读不自动安装authority、授复制或新制作资格。当前本地Ready源协议不以外国locator冒本地权限；若后续支持受控跨实例来源，需要真实来源授权/本地信任映射及同样闭包，而非从zip自授。投影可按实际许可只导合法内容并注明限制，不能删祖先后称完整correction Bundle；撤销不能改已合法导出原字节。

## 6 后续 owner 与独立验证

Backend按批准后的唯一私有Context/Observation/Binding/Edges成员固定消费说明和hash，负责从真实准备构造、受控authority安装/撤销接缝、user_asserted精确批准、完整祖先读和final writer。其当前WIP由自身完成，架构不读/不改；default not_ready实施可以继续，真正authority启用另需实际源/授权/独立准入，不因本文直接放503。

Media仅消费两个正式口及全部typed事实/链/许可，不生成validator、私有SQL/批准或反射兼容。先把返回observations与actual context对应，再用实际质量检查；rights未测保持未测，不改变alignment/其他QCguard。按新allocation/receipt与完整edges组装，保原precision/null/200ms/全部材料及数据归属规则。

Test准备实际标准/病例，Review独立批后运行：真实Ready/fence/主体/原列表冲突；false observation/错误target/decision/hash/用途；前置成功后撤销/期限/配置/fence/晚artifact变化；writer禁网络与同序撤销竞争；legacy不伪前验；C→B→A跨0.2/0.3/共享祖先、各层license/权限/自身依赖、环/深度/数目/bytes上界、ID碰撞、新material/原file与record、跨Production批准及import不授信。独立真实Bundle/导出导入/多层业务验证不能用synthetic source/helper AST冒通过。

Integration只按后端实际生成/可信安装资源封装，前端只展示明确等待/权限事实；无需普通使用者填写内部proof对象，缺资源时保可恢复动作。当前rights authority/真实许可/真正原件链/全Bundle/API/MCP/三OS/自主作品尚未批准，不占槽等外部资源。本轮费用/key/ASR/model/网络/安装/部署/测试均0，固定来源和正式交接后FINAL释放。
