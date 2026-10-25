# RV42 — B25 本地素材图修复有限独立评审

结论：**SOURCE_REVIEW_FINAL；RV40-P01 在固定 B25 两源范围记 CLOSED_SOURCE_STATIC。** 模型及 resolver 的通用 depth32 误用均已移除，新增报告计数/祖先计算按 ADR0029 区分 R 与 H。没有发现本修复切片新增静态阻断。该结论不包含 Pydantic 构造、实际 resolver/管理/安装/current/final、版权许可或完整作品通过，原 RV40/B24 结果不回填，后续独立 Test 和 Acceptance 资格仍待。

## 1 输入、来源与边界

仅 B25 正式 SourceCopies、最终 B24 Implementation 的旧副本、ADR0029、原 RV40 报告及对应正式收据；没有读取当前生产、T32/I35 或其他活跃任务。53 新普通源、53 旧普通源、20 正式材料共 126 路径身份全部匹配；末核 126 路径 0 变化。只两源变化，其余 51 与旧 B24 最终身份完全一致。RV40 原 SliceA 的 50 源范围仍独立，不能把本批最终 53 倒填为当时已审。

| 固定对象 | SHA-256 |
|---|---|
| ADR0029 | b0cd003a825f8927a6cdff7970c5a38e9a2e3c10276e023546d8b4ec4f7543af |
| B25Handoff.md | 3d670e10637bc422465f01f7cb30e2056d3fc3eb3ab6ff36ba03601ff1984b4f |
| B25Handoff.json | 76610c6d7ba3a6a3b3cd7e76002e7b3b8db133afb1d3c3608d1bd69bae6ecb2a |
| B25Interfaces.md | 22cd14b7ae71b710a43bbfd551e956ca2daa46c7965649aa6f165c2c2e27162e |
| 新 SourceSnapshot.json | a1ef904625049abfb62b90062728d467e6009bc8772a473cc71446ee8cc20187 |
| 旧 B24 最终 SourceSnapshot.json | ac382ef290a45993ea69f0748824cdb0741f755c6091548b0be7da01e6c0244b |
| AcceptedSourceChanges.diff | 3feb82ae110fa9864294b59d76effbbe9a9ed31eec8848890a3a099deaf11bc4 |
| StaticReceipt.json | e8997f7a3878ac31842eb56766d40701be2861fc57ce8ff1928c472c56467ae8 |
| FinalSourceIdentityReceipt.json | 1cdc3d496ba6ff7f9e9707d593c03ef7a11d5fd59d052bfacaddda43bcbb03a1 |

本轮卡 SHA6db29ea1789da8c7b72946a2a472a54304998279c6b5fcdce32cfe955c5984de；AGENTS SHA6de878f514b02788f8af5ba512f71c56bb053f6800d76cf19f3cdd955b7f6a0d。准确绝对路径/字节/hash 见 Review/CopyGraphCorrection-RV42/RV42InputPins.json。

唯一新源码根：G:/开发测试/Codex/VideoCreatorImplementation/Backend/CopyGraphCorrection-B25/SourceCopies/services/engine/。

| 相对源码 | B24 旧 SHA | B25 新 SHA |
|---|---|---|
| src/video_creator/domain/local_copy_input_scope.py | eab4044a5c6031008d240ae4db1398a85095766bb00aaf8fdb81b69b44338764 | 32b274d97f2122e8bdc8dffe28353e5d1c574700adcd1d7e7b2e4a746a8daae0 |
| src/video_creator/application/local_copy_source_resolver.py | c4195f7d08ecee2722560ca684d1f1b5382782c544c1b4e0c9f0a522b8e3b7a3 | e7f254a06169f0c97d8c43e1991258ed1c42e14a182e82b1416bd9e9ca4debc0 |

自有标准库仅对固定文本做 diff/AST 身份分析：存储 diff 与实际两份旧/新正文逐行一致；模型除 complete_graph、resolver 除 _resolve 的 AST 均不变。没有 apply diff、import 产品或执行 Pydantic/业务测试。

## 2 RV40-P01 的有限源码关闭

ADR0029 明确 G 通用 DAG 不新增 32 门，N≤256；R 是真实历史报告≤32，H 是真实 corrected_from 报告祖先节点数≤32。原 RV40 的 33 普通非报告节点静态反例仍保留为旧实现反例，未曾实跑。

固定 [local_copy_input_scope.py](G:/开发测试/Codex/VideoCreatorImplementation/Backend/CopyGraphCorrection-B25/SourceCopies/services/engine/src/video_creator/domain/local_copy_input_scope.py:142) 的 complete_graph:142–171 不再计算通用 depth 或比较 MAX_SOURCE_REPORTS。137–139 的有限 tuple 边界、143–153 的重复/冲突/引用/self-edge 核验、154–170 的当前递归栈 cycle、visited memo 和全部 root 可达检查均保留。MAX_SOURCE_REPORTS 常量仍存在不代表残存门；该方法已不使用它拒全图。模型没有真实文件，不凭 roles 或 caller 数量宣布核过 R/H。

固定 [local_copy_source_resolver.py](G:/开发测试/Codex/VideoCreatorImplementation/Backend/CopyGraphCorrection-B25/SourceCopies/services/engine/src/video_creator/application/local_copy_source_resolver.py:97) 的 visit:97 起不再有 depth 参数/统一 depth>32 条件；普通 dependency167–169、license170–176、真实 ancestor191、roots203–204、proof248 都调用同一无通用深度 visit。132–136 仍核有限节点、实际实例 max_bytes、全 size/SHA；不截断第33节点或返回 partial。

因此旧 finding 所指的“两处把 report32 当全部 DAG 深度”的额外拒绝已在精确源身份消除。**只关闭该源码偏差**；不声称 33-node 已构造/运行、256-node 已通过、任何实际 scope 安装或版权门已通过。

## 3 R/H 的实际识别与冲突边界

resolver:49–90 的同 Owner/project/instance 精确 published BundleRef、原请求/manifest 身份、actual manifest bytes/hash 先核；122–147 核 Ready 行、完整 file SHA/size、文本 receipt grammar 或真实 decoded Asset。文本141 调固定 bundles.validate_text；后者152–190 以有界 UTF-8/LF bytes、strict JSON、独立 schema model、record SHA 校验返回解析对象。固定 bundles:119–127 的 record_sha 去除自包含 content_sha256 再按唯一 canonical 计算。该调用链是源码事实，不是本轮真实原件阳性或 precision authority。

R 仅在 resolver:156–166 的实际 parsed PrecisionEvaluationReport/PrecisionEvaluationReportV03 分支增加。evaluation_id 对应 receipt.schema_kind、完整 recordSHA、全 fileSHA、size、MIME；同 ID 不同真实身份在161–162拒422，不能以重复 ID/hash 冲突假去重。同一严格报告/已核索引副本可共用 R 计数，但不能共用来源权限：nodes 始终按完整 BundleRef/artifact key，报告去重没有替代每项 source Ready/file/right 检查。

H 只由 V03 typed corrected_from177–193 建 report→report edge；180–199 要求 parent indexed forwardedge、hash/role、唯一 original index、完整 reference 约束及 locator/record/alignment 身份。即使 original 已在 nodes 中被 memo，263–273 的完整原件重校仍保留。274–292 仅在真实 report_graph 上 memo+当前栈求报告祖先节点数，拒 report cycle/缺 verified origin、H>32；license、creative proof、普通依赖不计成更正代数。R≤32 和无环已使 H 有限，此 H 门没有变成新的较小全图配额。

本源码范围不把 parsed 报告或传入 authority_ref 当已独立测得精度；真实 source 是否曾通过完整 Bundle/可信 authority、全部 H 正反病例仍待固定 Test。

## 4 shared DAG、许可、canonical 和 current/final 的保留

visit:101 先查 walking；103–112 对重复完整 member 合并 required_uses 和更严 handling，同约束返回 memo，加严则撤原 observation、调整原 logical_bytes 并重新核验、遍历全部必要边。118–131 的实际用途/有效期、user_asserted 之外明确503、真实 historical assertion 或 human Owner declaration 未移除；170–176 每个 license child 仍须自己的 Ready grammar、唯一 license role、text/plain/full bytes。报告 R 去重不按不同来源的权利“取最宽值”。

B25 保留既有完整 member 计数与 logical_bytes 累加/加严重算机制；本报告没有验证真实物理副本数量或字节去重边界。后续应按 ADR 的实际 source 身份独立核 B，不能因为同报告 R 合并就自动减少 N/B 或省略某个来源许可。

proof218–262 与完整原件263–273 未削弱；模型143–170 防全图 cycle、缺成员、不相关不可达。共享 DAG 用 visited/memo，不把共享路径误当 cycle，也不靠 32 通用上限防遍历。用途枚举及边 tuple 原有有限资源边界保持。

canonical:17–26、所有公开字段/version0.1、scope SHA/root/items/edges 顺序、原 ref/action/request/policy/budget、SQL7 和其它51源身份保留。旧合法对象仍按旧 canonical 计算；新合法长图有自己的新 SHA，不伪造旧 rejected request 为成功。schema/SDK 尚需唯一 export 的新固定准入及实际生成，旧两源 pin 不能执行新版本。

resolver:311–352 的 resolver-issued 对象/Owner/project/TTL、manifest/member/right/Ready/Asset 及当前权利重新核验；354–371 的实际 manifest/source/proof full-file 重核均在 _resolve 外，AST 与旧源一致。_resolve307–308 仍在返回前调用 assert_sources_current。固定 bundles:627–641 的 final source file recheck 接线仍在未改的源码中，真 current/fence/final writer、撤销/过期/更严许可和抗并发行为未实测。user_asserted 条件不授真实 owned/licensed preflight，它们仍明确未准入；不能以此静态关闭版权或再分发门。

## 5 原收据、独立待测和终态

owner 原 a1fab2/CaptureSourceStage 自然0、owner50448、Ruff child50752 communicate/wait 后0、53 copy/46 AST/两目标 Ruff0/no drift，只支持 source/static；FinalSourceIdentityReceipt 1cdc3d49…只支持 identity。原 B24 两轮静态红及其它原失败未覆盖。本角色没有重跑它们、运行产品或测试。

后续 Test 应固定并独立批准范围后区分：32/33 非report链、256/257成员、真实0/32/33报告与多root、报告祖先夹普通license/proof、同report副本不同rights/同ID异完整身份、shared DAG/cycle/缺依赖/不可达、真实 max_bytes/完整 proof/用途加严，以及 preview/install/execution/current/final 同源一致性。该列表不授 Test launch、RuntimeBinding 或真实作品/三OS通过。

自有文本分析3b8047实际exit0：diff一致、保护 AST 两项一致、51源相同、126结束身份无变。固定 source/evidence reader 已全部终态释放，live=[]，不持生产 freeze；只写本报告及 Review/CopyGraphCorrection-RV42/。未运行产品/Pydantic/SQL/DB/schema/native/Test/ASR/provider/network/key/fee。正式 Findings/Snapshot/SourceAfter/Handoff 固定结论和精确身份。完整 R1 三 OS 独立验收后连续 R2、实例持有数据、五步不变。
