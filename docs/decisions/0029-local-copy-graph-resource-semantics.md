# ADR0029：本地复制图的报告与资源边界

2026-10-09。状态：**精确契约解释及两处修复准入，真实运行/独立标准与finding关闭待验**。补充ADR0020/26/28；不改原报告/许可/授权/质量标准，不新增通用depth32。完整R1独立验收后连续R2保持。仅Architecture，无实现/测试/DB/schema/native/网络/收费。

## 固定问题与裁定

RV40正式报告 `21ccf9ac…` 的P01是P2/Backend/OPEN_STATIC：SliceA固定model `eab4044a…` 的LocalCopySourceSet.complete_graph将MAX_SOURCE_REPORTS32用于所有依赖路径。B24最终53普通源码Snapshot `ac382ef2…` 的resolver `c4195f7d…` 也在visit的所有边统一depth+1并以32拒绝。它们都是静态证据，不是实际作品运行失败；不能用后续候选覆盖SliceA或自签Review绿。

ADR0020 §4的“祖先深度≤32”指**真实更正报告的祖先链**，不是license/artifact/proof每个节点都占一个报告深度。ADR0028的256artifacts/32reports/max_bytes没有授通用依赖depth32。因此合法33节点、32个artifact_dependency边、0报告且实际bytes合限的无环可达文本链应允许通过结构和资源校验；它仍须真实Ready/权限/全许可检查，不凭此形状得到许可。

## 明确计数及上界

| 量 | 唯一语义 |
| --- | --- |
| N 来源成员 | 整个实际选中source closure内不同source BundleRef/artifact及实际Material或Asset身份，包含报告、许可、普通dependency、doc/plan核实proof；≤256 |
| R 历史报告数 | 从实际ready bytes严格解析的历史PrecisionEvaluationReport0.2/0.3，不计本次尚未生成的新作品报告；≤32。不是roles/edge.kind/caller声明数量 |
| H 报告祖先 | 由实际typed corrected_from及父index/原件身份验证形成的报告→报告祖先链，节点数≤32；普通artifact/license/proof边不直接当一次更正代数 |
| G 通用路径 | 全部依赖有向无环图内root到leaf的节点数，没有额外32门；在N≤256且acyclic条件下自然≤N≤256，作为遍历资源边界而非新增较小配额 |
| B 逻辑字节 | 按既有完整source物理身份去重后的实际file size总量，包含proof/许可及全部必要来源；≤实际AssetService.max_bytes，较小实例配置不忽略 |

R沿实际报告身份统计：严格schema/record SHA、evaluation_id和完整原byte身份一致的已证同一历史报告/索引副本可计一次，但每个source声明及入边的许可/限制分别核，N/B仍按既有真实来源/物理身份计。相同ID异hash/grammar或来源约束冲突不能通过去重隐藏；不是拿同bytes合成较宽权利。旧resolver的report-key表达是否完整对应这些实际身份，由Backend明确固定，不通过caller字符串“这是普通文本”绕32。

H在真实报告图计算，不能直接用全图path depth替代；若报告祖先通过copy/forwardedge指到同一真实报告，按已核原件关系计实际报告链，不能把中间license/proof计成新报告。R≤32且报告图无环已使H有限；不新增元数据字段、假report flag或独立低于原标准的门。

源node/root/edge原列表先校验重复/冲突，再构图；所有引用必须指向集合内实际身份，self-edge/环/缺成员/无关不可达成员仍拒。共享DAG不是cycle；visiting检测当前递归栈，visited/memo避免对每条共享路径指数枚举。遍历复杂度按实际V+E及真实用途加严重核控制，保现明确结构tuple资源上界，不在本轮额外放宽edge集合或取消bytes/closure限制。更强用途/handling合并必须保每项约束，不因memo返回漏掉任何rights门。不得截断第33节点、返回partial closure、把超限改成空集合/True。

## Backend两处归属与唯一接口

1. `domain/local_copy_input_scope.py::LocalCopySourceSet.complete_graph`：只做N、原有edge/tuple边界、重复/引用/可达/全图cycle与结构资源核。移除将MAX_SOURCE_REPORTS用于全图depth的条件；不能只把常量改名但仍=32，也不能加通用depth32的新字段。模型没真实bytes，不在这里凭roles断言实际R/H已核。
2. `application/local_copy_source_resolver.py::resolve/visit`：移除当前全种类边统一depth>32的拒绝；从实际已核观察/报告grammar维护R/H，普通license/dependency/proof链可走到N自然边界。初始预览、install重解与current请求/final source重核用同一规则；不能只修模型而服务仍拒33，或只修服务但模型还拒。

Backend唯一维护既有公开LocalCopySourceSet/Scope与private resolver/facts，不新建第二套parser或模型。保持kind/version0.1.0-candidate及字段、canonical有序items/roots/edges、原管理action/ref、scope/request/binding/admission SHA和预算身份。这是纠正候选validator的非规范额外拒绝，已有合法≤32节点对象仍原hash；新合法较长对象按原canonical生成自己新scope/action身份，不伪造旧请求或原被拒结果为成功。

不需要新SQL迁移/回填或重写已安装记录；schema7其他真实备份/恢复/Owner/current/撤销职责不变。发布新实现、固定ordinary/diff/接口后，Integration从Backend实际唯一export重生契约/SDK，实际schema若字节未变也留准确比对收据，不能手改schema暗放约束。旧资源/原SliceA和全部红保持原字节，不回填历史fixture或test输出。

## 独立验证要求与终态

Test独立标准/病例至少区分：32与33非report chain均合法、256有限合法结构及257超限；实际0/32/33 historical reports、不同report分散多root、报告祖先链与license插入不混计、相同报告副本不隐藏不同rights；共享DAG与cycle/self-edge/缺依赖/不可达/重复冲突；真实max_bytes边界、proof许可、root合法子集完整闭包及用途加严；模型construct与真实resolver/管理preview两处一致，实际current/final仍核source许可/撤销。该清单是设计输入，须Test固定实际criteria、Review独立批准再执行，不由架构跑Pydantic/产品或修改原期望。

RV40-P01仍待Backend真实修复及独立Test/Review关闭；本ADR不关闭finding、不把33静态反例说成业务实测红。安装/许可/实际复制/八交付/三OS资格仍待验，A24的八VC下限仍unknown，不授运行。source pins/正式Handoff及全部工具reader终态后立即释放；完整R1→连续R2不缩。
