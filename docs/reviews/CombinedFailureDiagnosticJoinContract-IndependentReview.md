# ADR0060 — 失败诊断合并与受控续步合同独立评审

结论：本固定合同的失败合并、私有来源伴件及恢复安全约束有源码依据，可支持限定 DESIGN_REVIEWED_SOURCE_ONLY。完整“新分析→当前选定诊断→最终发布”实施合同暂不批准：新增 CFDJ-P01 为 P2 / OPEN_DESIGN_CONTRACT，归原 Architecture，后继实现归 Backend。原 BDE-P01/P02 继续 OPEN_SOURCE_STATIC，设计不关闭它们。没有产品、SQL、媒体、安装、三OS、R1或R2通过结论，也没有运行授权。

## 冻结身份与读取范围

本审查完整读取任务卡 CombinedFailureDiagnosticJoinContractIndependentReview.md，SHA 0c1a6bc852aed865e1fb982f9f265673371bf708d13fbb9320fd50fae309aa3f。

ADR0060：G:/开发测试/Projects/VideoCreator/docs/decisions/0060-combined-failure-diagnostic-join.md，24496 B，SHA 8fc928e2ea0ff418a0ee1cfe998baf5d86873d542989bf2f22f100df114d184f，全文1–118行。

正式架构根：G:/开发测试/Codex/VideoCreatorImplementation/Architecture/CombinedFailureDiagnosticJoinContract/
Handoff.md：3a5fd5d3a9f38708adcbf0d2bac92cf234b236860b96a1238962e38c23ac96e8。
Handoff.json：e6a14aff2c0dfea8e50024a0593c5edaf137082125135db23cc5900cbd603742。
OrdinaryIndex.json：81beb263bac2b83a110e3c3a3d807a16ab9248970f310c1a8ddfc297dda08cea。

23 停止普通副本逐件大小/SHA匹配；加入正式交接/治理控制件共31有限输入，InputBefore到InputAfter差异0。原127索引2647be662e31cafb8c9870c5276b8740df3ffd9bbfc701dcea79a5d67e38a424固定一致；本次不是127全部正文评审。精确实际代码范围与显示限制见 ReadScope.json。未读取热 Test、Backend、Architecture 或未来实现来补当前合同。

## 已支持的安全设计范围

1. 原一次 self.verify 的真实返回/失败之后才 join。原 current_final_evidence_service.py:241–312 保真实精度失败 receipt、max(start/end)>200000us单位、依赖闭包和原返回；ADR0060:15–25 明确 manifest=None 不冒完整结果、真实held outcome不由JSON构造、timing_only不能清精度失败、component闭包不与精度闭包union授生成。没有第二次整体验证或被拒pre-verifier早返。
2. QC只从 Bundle:2723–2725 精准检查现场捕获，必须有原READY quality/body/修订关系和实际readset；泛 EngineError、source/integrity/rights/authority拒绝原样保留。QC本身位于最终rights/publication之前，合同明确不能证明后续关卡通过。原precision:2332–2359两次authority、v0.3完整参考/数学:2452–2513不被诊断结论替代。
3. DiagnosticSnapshotV1确实没有原precision reason/dependencies闭包，保存私有伴件是必要增量。ADR0060:29–39用exact journal SHA定位、完整snapshot SHA和来源/readset、原短writer同connection CAS/INSERT/最终current检查；immutable不同body拒绝、失败整体rollback，不改变旧journal/Fact/command正文，也不持久VerifiedToken。这与原 journal bounded TEXT/canonical/current和 Runtime原lease/fence/CAS相衔接，不能只靠hash宣权。
4. 原 waiting_diagnosis:Runtime161–163无条件停止、park93–139释放lease、claim288–318要求原queued/executing。合同43–69准确提出Backend no-lease当前Owner探针，真正READY/反馈/资源事实才入新输入，claim在实际新lease重建held，原Runtime管理入口/同Run/newfence续步；producer的analysis-only分支不能混成重新生成master或直接整体验证。
5. 新v2仅改变真正completion来源，保持v1字节/原canonical encoder/原Step与dedupe关系，不用时间/nonce/新key掩饰重复收费。原 service362–385必须实际succeeded/settled/actual_cost和正确原route/intent；合同unknown先reconcile、same-input record纯复用、no-change inconclusive still_blocked、driver实际消费completion的要求正确。实施和独测须明确矩阵优先级，不能把同一已选inconclusive当新变化反复queue。
6. 原 admissions908–954的同当前Owner、unattended四动作、interactive原真实plan/quality批准仍独立；新context只是诊断续步，不是生成scope。原 publication经真实VerifiedMaterial、原rights/current/source和选定诊断门，不能凭历史success或component修复发布。

上述是设计约束的源码支持，不证明新私有类型、observer、producer、companion writer和真正恢复已实现。缺实际factory/resource observer时应具体NOT_READY并留归属，不用永久503冒完成。

## CFDJ-P01：当前选定指针转移缺件

完整 Finding：本Review根 Finding-CFDJ-P01.md，3435 B，SHA b28e7c008fffe1db69daf5d2c6eab1f20685cc0e5e74095f21d7a6f8d2771923。

ADR0060:59/69–71/85–86新增input-v2 dispatch、record以及“写为唯一当前journal/ref”，但未明确真实 component-diagnostic-selected.<preparation_id> 的安全迁移方法和same-connection CAS边界。

原固定 application/component_diagnosis_service.py，58971 B，SHA fa2d8f8974ac9432364b14b623089deef21c1ee7a1047bbf10d0672286e9d08e：
- 23行为实际 SELECT_PREFIX。
- record:518–531已有旧selected时，524–525对不同新ref一律409；Fact追加与选定指针写入目前耦合。合法新completion→v2新key并不能仅靠parser dispatch绕过它。
- publish guard:31–49继续从SELECT_PREFIX+preparation读取ref，旧information_required或component_repair仍拒绝。
- 真正消费者为 bundles.py:1418，在原publication_guard/同SQLite可见性事务中调用上述门。Bundle固定SHA589a0d4f99e60784c7d7531699bcab4ca063c79b898ba72f6768de86dc3ea137。

因此合法旧inconclusive→真实新input/newsettled fact时，如果保原record语义，先409；若只改journal选新ref，最终门仍读旧source拒绝。不能关闭这个门、清pointer或任意覆盖旧选择求通过。合同需要明确新Fact只追加而尚不选择的阶段；原old selected row/body也纳probe/readset；当前held/Owner/current/lease/fence、exact journal/source与old-selected CAS后，在原同事务完成唯一新选择并保旧Fact/历史伴件。record后park前崩溃、重复恢复及journal/selected/source任一冲突应复用或整体rollback，不能重新分析/收费或洗旧拒绝。

这是准确的静态合同缺件，不是已运行的SQL/恢复/出版错误。原Architecture应补完整具体caller/ABI与失败语义后交新固定版本复审；Backend仍是唯一实现者。

## 下游与未测

本版本整体等待 CFDJ-P01 修订；失败join/companion方向和权限保护的限定支持可交接，不是对任意实现的批准。原两生产findings仍OPEN。0039/0058/0059的既有版本、公开DTO、原quality/RAG/Bundle与human/Owner/rights/费用门不被此合同替换。

后继独测至少分别覆盖：原一次verify成功/真实precision失败/精准QC与泛EngineError；current/ref/源被替换时rollback；真正新input与旧selected迁移；新fact记录后park前崩溃复用；同输入differentfact拒绝；无变化inconclusive不queue；unknown原账本不重交；两authority第二次拒绝；200ms与两闭包不被清除/union。测试另由原Test获明确准入，Review不编写/修改或运行它们。

原BDE-P01/P02固定报告、所有历史失败、原19三次用尽和正在另角色进行的87均不改、不读取。未授产品/Pydantic/SQL/HTTP/MCP/provider/native/媒体模型/安装/网络/fees/keys或第四历史目标。完整R1后连续R2目标保持，当前均未验收。

## 工具和停止

完整ADR读取3ca06b/0；31输入前核da8ec8/0；有限原body自然0。聚合源码显示曾截断，只补确实遗漏范围，未假称原聚合全文。旧rg.exe入口在6479bb不可执行，保错误；同调用后续精确1418–1448读出，不能把整体0洗成搜索成功。69fcb4改用同固定文件Select-String仅定位，不安装或扫描环境。

末核630fa3实际自然exit0，23ordinary/31输入差异0。所有冻结源读取已停止，无live handle。正式写报告命令的真实自然返回在后续工具响应中单独确认，不从文件存在推TRUE FINAL。
