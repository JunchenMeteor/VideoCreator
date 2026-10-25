# BSC-P01 父来源快照窄修复独立评审

结论：**BSC-P01/P2 可 CLOSED_SOURCE_STATIC_ONLY**，仅针对本固定修复的原读后→最终 writer 父 intent 快照遗漏。未发现新增 P1/P2；实际 SQL 并发、拒绝后的事务 rollback、合法正常发布/重放均 NOT_RUN。原 finding 和失败原件不改，源码闭合不能代替运行关闭、安装、完整视频/音频/字幕/RAG 制作或 R1/R2 验收。

## 固定版本及独立身份核验

任务卡：`G:/开发测试/Projects/VideoCreator/docs/task-board/BackendSelectedChildCtcParentSnapshotIndependentReview.md`，SHA `0f76450b097a453d3901386eb4166ef84b5f803f7878a4762e7a991bf80c9429`。

唯一修后根：`G:/开发测试/Codex/VideoCreatorImplementation/Backend/SelectedChildCtcParentSnapshotRepair/`。旧根：`G:/开发测试/Codex/VideoCreatorImplementation/Backend/SelectedChildCtcReadComposition/`。全部实现读取使用两个固定 SourceStage/SourceIndex.json 所列 ordinary_copy，不使用 source_path 指向的生产源码，不读取热 ADR0058 实现。

| 修后固定件 | SHA-256 |
| --- | --- |
| Handoff.md | 62502e4c6f25c4aada7bdfc6da7a3c618f1af98dc5bd5814f5393d6ab58a4034 |
| Handoff.json | 2e74cb4d7aea329e5dbf9c90e2f0728346a399ca765f0bcea18cd3a55b381f70 |
| Interfaces.md | dc7346125f524ed45daddb7a540fc4b774ed3e67384f578fe2e3478c491f5c65 |
| SourceStage/SourceIndex.json | 094612107d288c485a66d7466793830e3ff22f9a9f3401cc1050a790fb2a3060 |
| SourceStage/Checks.json | c89016ea3f9f11b07451e873ba2d03a049aa4206a965e8af37cbe95b97c8adc3 |
| SourceStage/Changes.diff（1644B） | 461cc1226cf692a3cc9370f0d01a9fc6f406986f768e8b25465fe29e111b9e6e |
| 新 committed_alignment_read.py（34826B） | 55534b5feef0d2e7bd3ba52c8aebc0520df33008c20b2bff938084cad815d70e |
| 旧 committed_alignment_read.py（34544B） | 30d3d413ca810a166979064fabd7bf2af839ef55565a298f624b73fd78694a40 |

原121 Index `c0ab833f165fb5cde13f23f54e6c7041107f115e3868b92f0b29f2f3a8d2acdf`；ADR0057 `19472f7635a40be25630d0a84e0426bbd06283522f513128caa437e2499c1b57`；原完整报告 `85e3a0544caa39a9fbdd0659b78b93f8cfe9552fec557fe9667bb881290bfc46`；原 Finding-BSC-P01.md `821b9f48b54f0690b0867025941807b980f6ab7258d7f362666f00d7e6f7aba4`；原 FinalHandoff `03c76fb629d904004a1bda8977b96d015040a93c24b68f91cec4f749c730a289` 均保原件。

独立核 121 修前与121修后完整普通件：只有上述一个模块变化，其余120件字节相等。110 Python模块各两版由标准库 AST 解析；完整1644B diff从原字节独立重建并逐字一致。仅删除新模块69行快照 append与131行 rows首项后，完整 AST 与旧模块相同；不是用作者 Checks/Ruff 或两个局部函数相等推断保护。256有限唯一输入前后 bytes/SHA无漂移，六正式件预期SHA全部一致，详见自身 InputBefore/InputAfter/StaticFacts/RebuiltComplete.diff。

## 原触发与修复后的实际源码链

原 finding 指向最近 realignment child 早返回：selector读取、核父 intent，却未把父 row交给最终 writer；共享 guard再核父 intent也未捕获它。最后来源读成功与最终 writer之间改变父 intent时，writer只查已经captured的行，无法发现该变化。本单原始等级是 SOURCE_STATIC，并无原实际 SQL 竞态失败证据。

修后唯一模块绝对普通路径：
`G:/开发测试/Codex/VideoCreatorImplementation/Backend/SelectedChildCtcParentSnapshotRepair/SourceStage/SourceCopies/services/engine/src/video_creator/application/committed_alignment_read.py`。

1. **真实每个 lineage parent 即时捕获。** `_committed_ctc_select:53–54`仍先捕获当前节点；68行通过原 `_preparation`取得 parent，69行立即追加 `('bundle_revisions','id',parent['id'],{id,run_id,revision_id,intent_json})`。70–72的原 parent revision/intent核验、73–94的 v2原 command核验都保留。初始/realignment最近源98/100行提前返回之前，父tuple已在同一个 snapshot；正常继续祖先101行再读取该节点时，也保留之前捕获，不覆盖它。无lineage初始仍有54行当前源tuple；legacy完整祖先遍历也复用这个相同快照。
2. **guard实际原source再次捕获。** `_committed_ctc_guard:114–121`原请求 grammar/current/binding/intent/安装来源校验不变；116行按实际 initial preparation或affected parent取row，131行把这份真实row四字段加入返回的rows。它不是从caller、command摘要或资格对象捏造一份父identity。route/companion/assembly/creative/权限来源仍是原校验。
3. **快照没有在组合/报告链中丢弃。** `_committed_ctc_composition:207–211`把selector全部snapshot与guard返回source_rows合并；316行补原Op/Step/allocation/staging/ASRcontext，317及323–325仍走原返回前重核。`_validate_composed_ctc_work_source:385–402`继续返回完整snapshot；不是只返回新投影或把旧来源清掉。原 getter只返回五事实，而最终shared report source保留完整snapshot。
4. **实际最终writer按原连接比较。** 固定 `application/registered_alignment.py:451–472`（SHA `dd0e31fda18b6359ce84adb23fbfb8147a2e83d6fd8d793d4bf7fe50b651c3cb`）对每个 tuple查询对应真实row；bundle_revisions只投影原captured字段，删除或任一四字段改变使observed!=original，触原 `work_ctc_source_changed`/409。没有引入writer回调、repair权限或第二套validator。
5. **原 transaction内前后接线不变。** 固定 `application/bundles.py`（SHA `218588d7e66afc856b349e0810264f71463b7d28df44167f2d6edc67d3abc90c`）1319–1333在原manifest writer前、后都把同一个ctc_work_source交原口；1419–1420和1462–1464在原发布transaction前后保同样核验。原静态触发窗口的parent intent不再没有查询项。此说明真实源码使用同connection，不等于已经执行SQLite、证明事务rollback或操作系统原子安全。

## 合法变化、重复tuple及原保护

新tuple仅包含id/run_id/revision_id/intent_json。原 `_preparation` 在 bundles.py792–797使用原lease/scope和同run/owner查询并核request revision，所捕获不是任意可读父row。没有加入 status、manifest_json、manifest_sha256、published_at_us、后附asset行等合法可变状态，因此本增量不会仅因这些值变化而触发新的tuple不等。独立运行正常发布/合法变化样本仍未做，不能把这一静态条件判断叫“合法发布已通过”。

同一父可能在parent边、下一循环current、guard各捕获一次。列表不去重、不修改源row，每个tuple仍进入原逐项比较；四immutable字段相同的重复记录只是重复SELECT，不改变任何预算/权限/账本。若两次读取期间四字段已经不一致，它们不可能同时与最终同一row相等，拒绝符合来源变化语义，而不是把后一个值覆盖前一个以洗掉变化。

guard新增首项没有破坏 `rows[-1]` assembly关联：133–137原两metadata append仍在首项之后，138行末项仍是原assembly；返回只被snapshots.extend消费，不存在本片新增的序号依赖。无source table/schema迁移、公开DTO/SDK或签名变化。

除精确两addition外完整原模块AST相同，其余120源原字节相同。因此原held九执行/initial口及第十read口、执行guard、claim/fence/current/thread、nearest选择/grammar/legacy拒绝、ASR/CTC两个实际Op、MethodEvidence顺序、precision只允许独立overlay、两真实authority/200000us/READY不可变、unknown预算与限次保持。这里的保护是源码identity/语义范围，不是现实权限、资源、零副作用或精度通过。

## 限定关闭与后继验证

BSC-P01在本固定版本 **CLOSED_SOURCE_STATIC_ONLY**；运行关闭继续OPEN。原 Finding文本和旧报告保持历史OPEN原值，不回填旧版本成功。没有新增P1/P2。

独立Test后继需在真正合法initial/affected/祖先来源和正常journal/fence下，明确在最后read与writer之间分别删除父、改变父intent/身份，核原409和真实无commit/rollback；同时核正常及合法status/manifest/asset附加的可完成路径、重复tuple、current撤销/错fence不绕过。资格producer、真实Owner或受权human事实不能SQL造；评审没有批准此测试运行或第四等价原目标。

M44-I01、旧历史method兼容、RRD/0058均不在本单关闭范围。真实CTC质量/weights/license/安装/SQL-HTTP-MCP/完整视频音频字幕RAG、三OS与完整R1/R2未由本片通过。总目标仍是完整R1独立验收后连续R2。

## 工具终态与读者释放

本片只读普通副本、正式文档与原证据；仅在评审白名单写数据/report。标准库分析入口 `C:/Python314/python.exe -I -S -B -X utf8` 不import/call产品/vendor/测试。没有产品/DB/模型/native/网络/费用/密钥读取或安装。

bee3ab/0全文规则/卡；d5bd2d/0正式Handoff/接口/diff/原finding；fea517/0完整身份/diff/AST；889ffa/0完整selector/guard与实际writer；65d3e4/0其余完整组合链与原交接；303376/0原8356B报告全文和_preparation；c5e35e/0末256输入与六正式SHA，无drift/no live。原作者aa8dde/87a9dd静态终态仅作为已有证据，不当本Review实际产品验证。

全部source reader已停止并释放。正式writer与最终封存的实际返回以FinalHandoff/FinalizerTerminal及本角色最后真实工具结果确认，不以文件存在或作者摘要推测终态。
