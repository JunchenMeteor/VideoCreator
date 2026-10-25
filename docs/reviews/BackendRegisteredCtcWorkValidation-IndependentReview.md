# 登记 CTC WorkValidation 与 READY 恢复修复独立评审

结论：原 **B120R-P01 的 ASR-only 身份误拒反例 CLOSED_SOURCE_STATIC_ONLY**。停止 ReadyRecoveryGap 的“初始已有一份 speech READY 就先要求其余四份”“合法 changed-audio child 在零份 speech READY 时先要求派生文档”两处顺序反例，均取得 **SOURCE_STATIC 修复支持**。本片未确认新的 P1/P2；完整消费端、实际 SQL／崩溃恢复／CPU CTC／资格作品均 **NOT_RUN**，这些源码结论不能充当完整制作流程、安装整包或 R1／R2验收通过。

## 固定版本与独立核对

- 卡356375ed6ab1a09b7365f504f00bc5b91545aa3a387bfed6c38b430065220f9b；ReadyRecovery补充b84f98a8f3667b4d01fb79e94c0751ca3a605ffb653aca2aabc8a0574fea2c60；停止输入定位884d45c787d865349dc47ed595c315d6477fa7cb01b305c347a6e5e20ae86baf。
- 原最终 P03 索引124c951d82c25f000bc9541117a6938b8c872ee321588fff2e0b7028236cb6fd；新索引9a22dec995223337c8221ab6c3b14733a2413716426e73b3625142cd0ed2172e。旧／新各120完整普通件大小及SHA逐件匹配，仅下面三文件改变，117字节保持。各109 Python源码只作AST解析，未导入产品。
- 完整23777B差异由本人标准库重建，字节与b7ddb06d04c8bcf5a383cbcdc128d0bee3f0aa1b6973c4baa4345f84eece7632完全一致；没有凭作者摘要认定修复。
- 新 Handoff MD accffaa8040f29a6d82052aa7f320b6eb19c3f0b7c1a610b22614bf21a013324／JSON8146dd77f9890355db708df01b7ae15253760463b4ee6ee22bcaecc9b082ed41，Interfaces87c6b7e629ef9f44118a43af5280405561563cd6e61f8a941aa3c92609f1caf8。原历史 finding/report及停止 Gap 保留原字节。

| 新停止源 | 完整SHA256 |
| --- | --- |
| [bundles.py](G:/开发测试/Codex/VideoCreatorImplementation/Backend/RegisteredCtcWorkValidationRepair/SourceStage/SourceCopies/services/engine/src/video_creator/application/bundles.py) | `218588d7e66afc856b349e0810264f71463b7d28df44167f2d6edc67d3abc90c` |
| [registered_alignment.py](G:/开发测试/Codex/VideoCreatorImplementation/Backend/RegisteredCtcWorkValidationRepair/SourceStage/SourceCopies/services/engine/src/video_creator/application/registered_alignment.py) | `ea3242d19e7cac1026b5fb464a90a4a0eca8bd9104eea1cb0491a743e5266890` |
| [current_final_evidence_recovery.py](G:/开发测试/Codex/VideoCreatorImplementation/Backend/RegisteredCtcWorkValidationRepair/SourceStage/SourceCopies/services/engine/src/video_creator/application/current_final_evidence_recovery.py) | `2348faa0cc2fb6d021503e6a6807f3ef71bfcf5c1abff9066f62e77dfdaeb735` |

## B120R-P01：真实 ASR A 与独立 CTC B

[registered_ctc_work_source](G:/开发测试/Codex/VideoCreatorImplementation/Backend/RegisteredCtcWorkValidationRepair/SourceStage/SourceCopies/services/engine/src/video_creator/application/registered_alignment.py:435)从本 preparation／同 Run 的原不可变 ancestry 选择来源，先选本节点 initial 登记；否则真实 v2 realignment 主 command 必须绑定该 child及完整intent SHA（448–474）。报告提供的 operation_ids不能用于任意选择资格记录。最多32节点且拒循环；选择后仍经过原完整 `resolve_preparation_masters`（477），其592–637对同Run祖先、child/parent intent/revision、原committed command与实际master角色核验。较近登记缺失、lineage、主command的原行（包括缺失事实）进入snapshot。

原 `_read_alignment` 与 `_alignment_result_facts` 并未改写。945–1015先走原 current held／qualification／resource／route／原ASR context与时码 preflight，随后要求一个成功settled Operation、完整request/input/dedupe/route、受控单JSON allocation、完整文件size/SHA/稳定stat、原严格模型/semanticSHA/全部单位ID与顺序、真实execution_identity和preparation/command关联；precision仍为not_measured。1038–1055要求实际复合键 `(run_id, step_key)` 的成功Step及原result/input，不能把文件存在当commit。未知或缺成功事实仍具体拒绝，无新增推理、预算或Operation。

480–497独立保持真实CTC文档、原ActualTranscript文字／时码/音频，精度派生只排除precision及content_sha256；再从原ASR journal读取真实settled ASR并核input／route／context。WorkReport必须使用真实登记CTC资格与执行身份，且包含两原Op。原ASR身份没有改成CTC，也没有给CTC补假actual_transcript payload。

[bundles._validate_work_runtime](G:/开发测试/Codex/VideoCreatorImplementation/Backend/RegisteredCtcWorkValidationRepair/SourceStage/SourceCopies/services/engine/src/video_creator/application/bundles.py:2384)从这个可信来源得runtime_match，另用原 `matches_actual_asr`对报告中的成功settled observations建立asr_match（2428–2444）。因此不同A/B可分别满足各自证据；没有登记CTC时仍沿原ASR runtime完整匹配路径，不能借None取得假CTC资格。原全run Operation核查、request/revision/audio、mapping、政策、registry qualification、units／word不可降级、资源manifest/checks全部保留。

503–537保存原registration／assembly／ASRcontext、两完整Op、完整成功Step、generated_attempts、CTC/ASR staging和audio行。541–551在实际connection逐行精确复核；其actual database竞态能力未实跑，不能写成OS原子安全。verify1314／publish1384以真实READY indexed字节取得同一源；verify1323/1333与publish1420/1464前后检查。私有verification token保存原源1347，publish1390要求fresh源与原值一致。normal验证2368–2381、v03/current完整验证2533均走同一runtime门。

**有限关闭**仅针对原“只有ASR形态且runtime必须等于CTC B才允许”的源码反例。真实A/B合法作品、错误登记／child／Step／文件／撤销／fence故障、ASR-only兼容均未运行。

## READY 恢复顺序：支持范围和仍开放的消费边界

[recovery._validate_final_assembly_facts](G:/开发测试/Codex/VideoCreatorImplementation/Backend/RegisteredCtcWorkValidationRepair/SourceStage/SourceCopies/services/engine/src/video_creator/application/current_final_evidence_recovery.py:97)对原五个speech路径取实际status。len=5且ready<5时，zero-READY可走原source assembly校验；partial-READY仅author=False并且本preparation已有真实initial登记才走该路径（101–112）。移除原“child必须不存在”及“只看transcript未READY”的前置，故实际 admitted changed-audio child 可在首份派生speech前持久原源。调用仍由原_selected_affected_child155–179和held journal/readset308–329核准同Run command、原parent/child完整intent、当前fence／claim／policy，不能 caller指一个child就取得权利。

[registered._initial_assembly_facts](G:/开发测试/Codex/VideoCreatorImplementation/Backend/RegisteredCtcWorkValidationRepair/SourceStage/SourceCopies/services/engine/src/video_creator/application/registered_alignment.py:83)继续核真实same-preparation/context/allocations、已READY资料完整bytes/grammar、原有效四master和creative/approval/feedback、真实当前factory/execution、原成功ASR及音频、不可变correctionPair。author=True仍拒任何既有speech READY（111–113）；partial读取先要求原真实CTC成功Step/输出，已READY transcript必须保留原transcript与CTC全部不可变字段及semanticSHA（114–126）。它不把缺失派生槽标READY，也不构造measurement或重dispatch。

五份全READY回原完整普通文档、subtitle/mapping/clock、ActualTranscript、source/revision和rights门（recovery113–202）。原persist269–301与新fence前后current、same-writer correctionPair严格例外完全保持；原材料readset读取实际bytes/allocations（308–419）没有用placeholder代替资料。只读ReadSet不是执行权限，不能把class-body或source tuple当guard运行证据。

**本片不关闭**尚未提交本任务的realignment selected-child consumer ABI／getter/command暴露缺口；新partial条件明确仅本preparation已登记initialCTC，不能推广为所有repair child阶段均可恢复。父报告／candidate尚未READY的完整消费计划、真正恢复不第二ASR/prepare/CTC/child、真实kill/restart仍需原Media／Backend端口与独立Test闭合。不读取热Media或用作者未来计划补证。

## 原三修复及原门保护

本人逐函数AST比较，保留 `_alignment_sources`的initial ASR method与原单位区间exact检查、affected `initial=False`区分；默认 `assert_correction_pair_writer`严格snapshot与validated首次绑定唯一例外；`assert_initial_alignment_manifest`只允许独立precision/contentSHA派生、完整8列原材料snapshot及前后writer。相关方法与原P03字节版本的AST一致，详见ProtectedBodies.json，不能把这些静态比较当实际行为通过。

原 `_verify_v03_documents`、`_verify_per_work_precision`、`_verify_strict_precision`、mapping checker、full relations等保持：两独立authority、完整reference/listener/arbitration来源与许可、全N/max(start,end)/nearest-rank P95、200000us、原字节/方法/时码、current权限/取消/lease/fence、剩余预算/unknown没有新豁免。当前未进入任何SQL／媒体/ASR/CTC/provider/native运行；第四原目标、被拒role交集、§1–5候选均未触及。

## 证据终态与下游

本轮263个有限固定输入前后大小/SHA不变；完整索引/源码/Diff及必要规则原件见InputBefore/InputSupplement/InputAfter。实际读取工具均已自然exit0；fdf23a、d9cc82、2c86e4有可见输出截断，不宣全文：相干函数在4fc8b2／0250cc／2f9fe7／0a7217／86a082逐段补读；未从截断推新事实。全部source reader在末数据核对返回后释放，没有live产品／测试／DB／秘密句柄。

后继独立Test需真实source qualification下分别证明A/B合法、ASR-only兼容、初始/partial/changed-audio恢复及fault拒绝；保旧三失败与原19累计耗尽限制。独立Acceptance仍须实看视频、实听音频和多模态产物，三OS安装完整R1后连续R2。**本片没有完整制作流程或安装整包已通过的独立证据。**
