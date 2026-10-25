# 0061诊断选择转移合同独立复核

本轮结论：固定ADR0061的CFDJ-P01可裁定为 **CLOSED_DESIGN_CONTRACT_ONLY**。新合同把不可变Fact追加、待提交候选和当前已提交选择分开，补全原暂停事务及首次发布事务的选定接缝。未确认新增P1/P2合同阻断。这一裁定不关闭BDE-P01/P02，不代表旧127源已实现新合同，也不授予任何产品、测试、安装或R1/R2运行资格。

任务卡：G:/开发测试/Projects/VideoCreator/docs/task-board/CombinedFailureDiagnosticSelectionIndependentReview.md，SHA256 8205ccbead94d5ea1e3bdd2ae70c7e217043fd0ba1c6343777d881ca9038e512。原Architecture已正式停止的交接与普通副本作为输入；本轮没有消费热实现或未来故障准备。

## 固定身份与读取范围

唯一批准的合同版本是ADR0061 18253B，SHA256 **04b522d08cec343bbd420869f37b949dcd6f301d837dd3bc8319ce071e00776d**。原件为G:/开发测试/Projects/VideoCreator/docs/decisions/0061-diagnostic-selection-transfer.md；实际评审普通副本为G:/开发测试/Codex/VideoCreatorImplementation/Architecture/CombinedFailureDiagnosticSelectionCorrection/Ordinary/Decisions/0061-diagnostic-selection-transfer.md。旧ADR0060 24496B，SHA256 8fc928e2ea0ff418a0ee1cfe998baf5d86873d542989bf2f22f100df114d184f，完整字节保留。

正式Handoff.md/JSON分别为69635d66aa8a988b1de5f7afe75971d23c95d63e6f11793d4245f538c4f664f6、727af656e1d637fe71c97cfcfaeb72b926eb271a8346337f697310a3a6c2644f；OrdinaryIndex为c044f83b3377618e71a6238470e7608fdfe957b41ed5ac6d494d0d019f600cdc；Snapshot为669c4d45cb072cb643e3afc022f2778a17e8936f073ce2af6d1feaa34a4dfb35。均位于Architecture/CombinedFailureDiagnosticSelectionCorrection。本人实核13份ordinary的size/SHA与索引一致；25项有限输入前后无差异。完整逐路径身份保存在本过程InputBefore.json/InputAfter.json，不将127索引理解为127全文读取。

全文读取新旧ADR、原CFDJ-P01和正式交接；旧报告与FinalHandoff普通副本身份实核，以已完成旧合同独审作为上下文，不把本轮身份核对称为重新全文审读旧报告。必要源码来自同一ordinary根Source/application下：

| 固定普通源码 | 完整文件SHA256 | 本轮相干正文 |
| --- | --- | --- |
| component_diagnosis_service.py，58971B | fa2d8f8974ac9432364b14b623089deef21c1ee7a1047bbf10d0672286e9d08e | 1–80、284–338、477–541、596–681 |
| current_final_evidence_runtime.py，27280B | 4609dcea36b97a003305dd9a25c3117cc41fdd465e9c40e5e4e5e2fab7009913 | 93–175、209–258、288–318 |
| bundles.py，232590B | 589a0d4f99e60784c7d7531699bcab4ca063c79b898ba72f6768de86dc3ea137 | 1372–1450 |

这不是三份大文件所有正文或全127实现复审；用途是核实原记录、读取、暂停和发布的真实调用位置。

## 原问题与新合同闭环

原CFDJ-P01，P2，原Architecture合同归属／Backend后继实现归属，原Finding SHA256 b28e7c008fffe1db69daf5d2c6eab1f20685cc0e5e74095f21d7a6f8d2771923保持。原component_diagnosis_service.py:518–525拒绝不同selected ref，529–531把Fact与selected同时写入。596–619显式reader来自当前journal，31–55发布门来自SELECT_PREFIX；仅改journal无法让新input的合法结论成为同一当前来源。原bundles.py:1413–1418确实在publication_guard及可见性事务中执行这一发布门，不能绕过。

新合同逐项补齐如下，行号指固定0061普通副本：

1. **Fact追加与选择分离（15–22）。** 新append只提交真实已settled分析Fact及component-diagnostic-result.<full_input_sha256>准确canonical Ref索引；read_recorded只按真实held input读取，None仅从未记录。索引与Fact同事务，same-input不同Fact409、损坏422。旧record默认first-select／同ref行为和selected冲突时整事务拒绝保留，不能先commit新Fact再抛旧409。原输入key在component service:284–307由稳定来源及methods产生，authored_fence在493进入Fact；因此20行规定恢复读旧Fact而不在新fence重构，确有必要。

2. **准确旧来源与受控held（26–38）。** PreparedDiagnosticSelection为Backend本服务登记的eq=False短期对象；old selected整body、old journal及source全文／实际absence、new Fact/index/Operation与completion均由服务读取。retain、first_select、successor分别有明确条件；successor必须不同input并由原previous诊断及真实completion证明，损坏不当absence。尚未合法准备的新Fact仅为历史记录，不授修复／发布。

3. **恢复暂停的同一writer（42–53）。** 原Runtime.park_current_final_evidence:97–139已有一个current_guard下的短connection、原assessment核实、journal准确body CAS、Run waiting事件及最终诊断writer。0061要求在此connection先重核old captured rows，再CAS selected、journal和准确journal SHA的source-v2，最后全源复核；失败全部rollback。内部commit方法不得另开事务或向Media/API暴露。只对已核old且本次成功CAS的selected/journal两项以准确new整行替代最终readset；没有过滤所有metadata或True守卫。source-v2保旧v1字段并增加old/new选择证据，单向journal SHA定位避免自hash环。

4. **首次无waiting的原发布writer（57–65）。** 真实wholeverify成功但无journal时，首次选择只能在原publication_guard与visibility connection内、_preparation之后、原1418发布门之前提交；绑定实际verification_id、原30秒/lease/thread/files及真实VerifiedMaterial。仅old selected和journal均实际不存在、first_select及非repair/information_required结论可走此路。该事务写selected及严格publication selection source，随后仍执行原1418门、correction/CTC、Operations、creative、rights、current、文件签名、_finalize和交付Step；任何失败连首次选择一起rollback。已有不同选择或journal不能借publish作successor。没有伪READY或用Fact替代Verified。

5. **三消费者与恢复一致性（73–88）。** 显式reader、失败join和发布门需要同一committed selected整body／current journal-source／唯一input索引／实际Fact；无诊断ref的普通v1精度等待必须从真实v2伴件关联。pending join仅通过准确registered input及held selection输出给受控writer，不作affected/publication许可；首次发布例外仍由第5节受控事务转为committed后跑原门。no-lease probe、queue和claim捕获并重核old selected，只复制已commit来源，不选择candidate。原Runtime:230–252、295–318确有同connection的journal与fence转换位置，实施需在这些实际位置接入，而非另写影子队列。

6. **崩溃、未知和历史（20、84–88、92–94）。** append后park前崩溃保持old selected/journal/source，新fence按准确registered input复用原settled Fact，零新dispatch／扣费；unknown先原reconcile。park／first_publish响应丢失只观察真实一致的committed状态，半提交冲突不能自动补写。历史lineage的不可变Fact读取与当前选择分开，不让后来selected覆盖旧command，也不复活旧权利。

据此，原“新Fact被record的旧selected409挡住；journal与发布门消费不同来源”的合同缺口已得到足够具体的端口、真实caller和原子writer约束，设计层无需再以模糊覆盖指针补充。原代码尚未加入这些新方法、索引和v2语法，不把它的现有409当成设计修正已运行的反例或成功。

## 旧保护与后继实施限制

0061:3明确仅替代旧0060的record/current选择及source证据接缝，15、42、49、63和94保留原所有current／权限／精度／来源保护。旧0060完整规范仍要求一次真实wholeverify失败后join、精准QC现场held来源、原reason/receipt和微秒单位、两authority、>200000us判定、整份plan/rights双权限、原费用和unknown账本核实；禁止pre-verifier提前return、泛EngineError吞失败和为求绿第二次wholeverify。新选择索引不是授权。本文没有重新批准0039、0058／0059、公共DTO或任何角色变更。

Backend后继必须实际实现两ports、唯一input索引、受控held选择、严格v2／publication source、原park和publish writer及三消费者一致门；Media只消费append/read，不构造选择或公共DTO。新的author source/type/caller固定交接应独审。独立Test之后才可核真实事务CAS、竞争／撤销rollback、崩溃复用和first_publish失败门；本合同94行仅后继设计要求，不是已批准执行的测试标准。

BDE-P01/P02仍 **OPEN_SOURCE_STATIC**，未由本设计闭合；实际SQL竞态、current撤销、OS进程、Owner、生产资格、媒体质量、六归档/TTS、完整安装和三OS均NOT_RUN／未验收。完整R1独立验收后连续R2保持；原19三败、费用上限、所有历史红和原失败材料未改。

## 过程异常与末核

原72e901读取工具自然exit1：PowerShell单区间嵌套数组被展开，尚未展示bundles行，并有合并输出中段截断。这是评审展示错误，没有运行目标或改任何输入。c2d799、9af218、cd86e2定向补读必要缺段均自然exit0；dad292/f9f3d4完整复读任务和合同没有截断。原816d8e旧合同全文保持。

InputAfter由7fe8aa自然exit0保存：13ordinary、25有限pins，differences=[]，SHA256 3eff4e40b469ea842a948fa3c3d0f0f15653b25922343d37dc6413502b2413fb。没有重新扫描runtime树或复制环境。所有源读取工具已自然终态，未持有源码读者或live句柄。最终元数据写入工具的真实返回将在FinalHandoff／最终交接明确，不从文件存在推终态。
