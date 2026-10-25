# 局部修订配方与权限差异独立评审

结论：SOURCE_STATIC_ONLY。候选“显式新 recipe＋新不可变投影＋完整真实授权”的方向可作为下一架构合同输入，尚未形成可实施/可执行的获准合同。发现 RRD-P01（P2/OPEN）：固定 Media37/38 自动组合声音或 cover-only 提案的 shots 与 Backend118 的独立失败映射不一致。本文不批准权限变更、不解除原自动评审拒绝、不改原实现或标准，不授产品/模型/SQL/测试/安装/RuntimeBinding。

## 1. 固定来源与审查范围

任务卡 RepairRoleDependencyIndependentReview.md：87f214f1afe9ce1cc6b1453a78be62b6430edeaa9055ffeec13363c545749df2。固定分析 repair-role-dependency-analysis.md：12210 bytes / 4e35939e01d9291f501db95086519a24d4147d1dd052e651c3439eeddcd6db8b，完整审查§1–5；§6只作为已另链0056的方法来源背景，不重审或自迁移 Backend120/B118-P01 结论。

固定普通根：G:/开发测试/Codex/VideoCreatorImplementation/Architecture/RepairRoleDependencyAnalysis/Ordinary。OrdinaryIndex：bc97d500d9101110d54ddb8bef3ce5fe993b954c7eb9ac1573e9c9577cc62471，30份完整普通副本；本评审记录39个唯一有限输入（含治理、原分析及正式交接），InputAfter changes=[]。未读热 Backend/Media/Architecture，也不把 Backend120 或 Media44 版本带入本片。

完整阅读 Media38 四个实际 recipe 源码（37对应全字节相同）、Backend118 两个相干 authorizer/plan writer/恢复和母版 resolver、原拒绝 Gap 与 ADR0053/0054；未以作者“没改”或集合数量代源码审查。

| 停止文件 | 完整 SHA-256 |
| --- | --- |
| Media37/38 workflows/affected_production.py | b27f7955e775b28caeab35f51dc6ef6321f7b8e2e5da915e1886b0ef55ca4a0e |
| Media37/38 workflows/production_drivers.py | de95cd8a13d84a8b74a68f4b308d1cc2a554a3f28994eb2b94f66b87dd263969 |
| Media37/38 media/production_edit.py | 9f2c2f2b613ca407b54b0b33b0d3e8f57bcad1a3b7ef0ed99fd9e37cb132a199 |
| Media37/38 providers/wan_video.py | 91502007d6420ac01ced8869239d6ae5e9c4497c2ef39c5aac9c3ec2b7c3467b |
| Backend118 affected_repair_service.py | 92a70eea9c7d9f81b30cc9d8d69ca333bb789b38818f61da9eae787f1c3e3c2b |
| Gap affected_repair_service.py（不同旧版，不能当118全文） | 5d502bf91c0d0a84b9923badae81d9cda589126340813f8663ef74621b9326cc |
| Gap/118 plan_repair_service.py（全文相同） | 658f03e23e877c4fd7a0cb957aa576fd2da0b42aca8b90017c6357c22a2f0085 |

完整路径/bytes/SHA 与独立原件对照见本过程 InputBefore、InputAfter、IdentityAndFunctions、OriginalGuardChecks。

## 2. 输入、组件输出、最终依赖与允许新写是四件事

原 WanVideoDriver 63–69 的固定 prompt 明确生成 ambient soundtrack；提交 payload/config SHA 真实包含该模式。因此新的 shot_clip 即使只取画面，也可能已经生成 clip 音轨并产生原 Operation 成本。“不新写 mixed_audio”不能描述为“没有产生任何音频”。

固定 production_edit.py 30–105 初始 edit 实际读取三 clip 的画面/音轨及旁白，clip 音轨形成 bed，与 speech 混音，一份 mix 同时嵌入新 AAC video，cover 从成片第一帧产生。PlanRepairService 71–102 对此设定的依赖来源有实际源码依据：narration→video/narration_audio/mixed_audio；首 shot→video/mixed_audio/cover；其余 shot→video/mixed_audio。

| 分支与源行 | 实际读取/执行 | 最终新写与保留 |
| --- | --- | --- |
| 初始 full edit，production_edit.py:65–105 | clip 画面＋ambient bed＋实际 speech；amix/asplit | 新 video、mixed_audio、cover；旁白由原独立组件生成 |
| affected remix=True，146–203 | 读 clips 和实际 narration；重新 bed/amix | 只分配选中 video/mix/必要 cover；是否另重 TTS取决于真实 narration目标 |
| affected remix=False，146–203 | 只取 clips 的画面，原 preserved_mixed_audio进入新 video，不建 bed/amix | 新 video/选中 cover；原 WAV mix/旁白保留。新 video的AAC和视频 clock仍是新编码事实 |
| cover-only，119–128 | 解码 preserved_video，取第一帧 | 新 cover；其余父母版保留。仅有这个 driver 分支不能证明整链可达 |

读取父媒体仍需当前本地范围、用途、复制/再分发许可；读 grant 或 Asset ID 不是新生成许可。父 mix/旁白“保留”应以实际 ID、完整 bytes/SHA、size/MIME、decoder clock/probe、lineage 和许可证明，不能只设一个布尔字段。新 video 必须重新解码并建立实际音画映射，不能把原 video 的 encoded track/clock 复制成新事实。

## 3. RRD-P01 — 声音组合与封面提案不能匹配统一失败映射

严重度 P2；状态 OPEN；等级 SOURCE_STATIC_ONLY。归属 Media 的 proposal consumer、Backend 的失败/target authorizer，及 Architecture 的唯一 recipe/component 语义合同。没有实际 SQL/provider/媒体运行反例。

最小触发条件是 regenerate_affected_media，真实失败报告中至少一个 predicted_range 与原 storyboard shot 重叠；其他实际父来源、权限和 failed role 前置条件具备。changed roles 包含 mixed_audio 或 narration_audio，或者只有 cover。

- Media38普通 affected_production.py 87–108形成角色，但109–125仅在含video且不含narration_audio/mixed_audio时形成shot_ids；组合声音及cover-only返回空 tuple。
- Backend118普通 affected_repair_service.py 403–408对所有 proposal 重算 failed predicted ranges 的 storyboard交集；结果非空时要求与空 tuple 相同，先抛 affected_proposal_invalid422。Gap旧版相应为381–386，不混版本行号。
- 一个只覆盖晚 shot 的失败可具有完整合法旧依赖 video+mixed_audio；或者 narration+video+mixed_audio 的角色范围与原 targets及 actual failed roles恰匹配。该路径仍在目标/命令/Operation之前失败；不是旧exact正确拒绝未准mix的同一个问题。
- cover-only在同样的非空failed-shot条件下也被先拒。若仅填入shots，Media193–197又因 affected_shot_ids 非空但无video而拒 affected_execution_scope_invalid403。
- 若直接给声音组合填全部shots，Media208–220以“video＋shot_ids”派发 picture/Wan，而非只重编辑音轨。这证明“失败影响到的镜头”与“本次允许重生成的画面组件”不能混为同一字段意义。

完整最小Finding及三源完整path/SHA在 Finding-RRD-P01.md/json；没有从未测推实际运行失败。修复不能删 Backend 重算、放宽 exact、自动 fallback全shots或顺带生成母版；须以真实 recipe规定受影响时段/镜头与当次准再执行组件的区别，Frontend/Media只消费Backend唯一 typed映射。

纯video分支也采用 semantic segment/transcript refs选择shot_revision_ids，而 Backend使用实际失败range与storyboard时间重叠。这是两个算法；本轮没有原作品数据证明二者所有输入等价，不额外虚构一个已复现缺陷。后继共享映射必须明确同一权威规则及原数据来源。

## 4. 旧权界为何必须保留

独立 AST 对照确认 Gap authorizer343–500 与 Backend118 authorizer365–522完全相同；两个 plan_repair_service 全文件字节相同。原完整 read/write checks没有应用被拒的 dependencies &= actual_roles 或“changed roles <= dependencies”变更。

需要准确区别：现有 authorizer426–427与 plan writer216–217，在没有非edit target时已有 changed roles∩edit依赖的 fallback。它是冻结旧逻辑，后续仍比较原 selected IDs及 exact dependencies；不能说源码“没有任何交集”，也不能用这个 fallback作为批准把 clip/声源真实依赖截小的理由。

原 Wan clip音轨参与mix；旧 shot target依赖含mixed_audio。所以旧plan下纯video或video+cover选择新shot而不准mix，authorizer428–429的 guidance_required403 是正确的权限拒绝。一个支持 preserve-mix 的选择性driver不能自动让旧target/旧plan hash代表不同配方。

原被拒 Gap明确记录：安全边界从exact变成subset，没有具体授权，不得绕过。保留该实际拒绝及源身份；Review不建议换工具、换模块、换名称提交等价补丁。

同时，永久拒绝所有视觉修订也不能满足R1。真实视觉保mix或单独cover能力应通过显式新recipe、新不可变投影和真实原授权链完成，而不是删除需求或顺带重做所有音频。候选方向合理，实施合同仍未冻结。

## 5. 下一最小合同与具体批准条件

下列是交给Architecture/Backend的必要差异清单，不是Review批准的新类型、版本值、权源或源变更。

1. 有限 recipe身份与完整实际源码/资源。至少明确 ambient-remix、visual-preserve-mix、cover-from-preserved-video 的读入、组件输出、最终写出闭包和保留项。声音-only remix是否重画面、首shot是否新cover必须明示；不由 runtime changed_roles 推定。源/import/installed whole identity、route/config/payload SHA、价格/成本来源和用途许可必须与实际实现一致。clip音轨产生与最终mix使用分别表述。
2. 两种镜头集合与组件目标。失败单位→原媒体时间/镜头闭包和“准重生成的 narration/clip/edit组件目标”分别有明确语义；真失败来源与新recipe共同决定。声音编辑可以保原clip时不能因video输出变化自动派Wan；cover-only不能被迫填不准执行的画面target。投影和command保存精确有限选择，新写闭包恰等允许角色且属于实际failed/批准范围。
3. 无环、不可变的原source绑定。新target固定原shot、微秒半开timeline、完整script/storyboard refs、原 payload模板SHA、prerequisite IDs、父角色引用规则和cover来源。plan阶段不造未来Asset/command/admission IDs；原实际command在真实观察后解引用父或新Step的完整Asset/file/clock。改变源稿/route/资源/用途/预算/限次是expansion，不能混成原target replay。
4. 整份新plan的真实权限。仅数据prepare不授执行。unattended需实际Owner policy仍覆盖完整新recipe/目标/route/input/source/rights/成本与有限修订，由原execute_plan admission绑定新整份plan SHA；interactive须实际human approve同完整新immutable revision。旧quality approve、旧plan批准、bool/typed target都不补权。权限或拒绝边界变更须具体合同和原真实审批；本文不能代人类或自动审批。
5. 单一严格版本dispatcher贯穿全链。旧format/body/commands/approvals/READY/settled/Goal canonical一律不回填；新格式明确dispatch，同resolver在initial、proposal、admission、prepare/claim、observe、child、恢复、verify/publish全重核。保持原当前issuer、人审/Owner来源、rights有效期、lease/thread/fence、同Runtime与完整资源，而不是仅初次检查。
6. 音画与许可证据。视觉保mix不得TTS/mix allocation/Operation；原mix和narration事实保留，新video实际解码/时钟/编码音轨映射重做；字幕/RAG/WorkValidation与成片来源重建。只有相同audio bytes/decoded time才可引用原ASR；新音频走原已登记child-ASR/context-first账本链。独立reference、两authority、200ms/MM05与null语义不降低。
7. 原命令、预算和恢复。相同command/source/target版本恢复原Operation/Step和已有输出，不新key/Run清unknown，不新预算或重置三次/修订计数；真实child/counter一次原子幂等。不同配方必须原真实变更/批准后新immutable来源，不原地解释旧未知操作。既有 submit_decision.revise若实际创建新Run，保其真实含义，不能假称同Run修复。
8. 独立验证判据。旧exact拒绝、超failed/roles/shots/route/资源、撤销/过期/old fence必须仍拒。合法组合声音保画面、合法视觉保音频、cover-only分别验证真实分配/调用/解码/许可来源；未知不重复submit，kill窗口恢复不重复成本/counter，two authority第二false仍403。集合公式、AST或author self-check不能替真实成片看听或授权来源。

字段/schema/ABI/版本和具体新target来源由Backend唯一声明、Architecture另卡裁定；Integration纳入真实完整source/资源许可后才可能成安装资格。Media不能私改公开DTO、读取私有SQL、以模型-selected模块或runtime flags补许可。新合同若改变原被拒权界，必须先取得针对确切变更的授权，不能把“新版本”当绕过标签。

## 6. 原恢复源码的支持与未测边界

固定 Backend118 _affected_execution74–97保持同原held object/thread/lease/fence、原持久command/parent/intent/source SHA，并回调同assert_command_targets_writer；read_current_affected_execution_inputs181–218从原journal/command重获parent/child/masters。observe220–363要求真实successful settled source/indexOperations、生成 manifests、actual Assets/hash/MIME与前后writer源快照，恢复既有观察不再写新事实。resolve_preparation_masters574–682按同Run v1/v2 lineage恢复四母版并保未变role。

Media regenerate_masters171–178优先恢复已有 masters；_generated296–328原begin_step/dedupe/route/ordered allocation、原executor/真实manifest/原Step commit，非成功且pending/unknown保持reconcile，未新建额度或“成功”。这些只说明原来源和恢复机制的源码路径，未证明SQL并发、真实权限或provider结果通过。

§6第九MethodEvidence具体化已另链0056，不借本次角色recipe提案扩大MethodEvidence、ASR或authority。Backend118历史P01、后继120修复及当前热Media均不纳入本报告关闭范围。

本阶段没有产品/测试/SQL/Pydantic/provider/模型/native/网络/安装执行、收费或密钥读取，没有完整作品、安装整包、三OS或R1/R2验收。保五步UI、实例自持数据、本地免注册/BYOK、API/MCP一次可信预授权和完整R1后连续R2。

## 7. 工具与正式交接

0d7287独立核30普通副本、37/38四recipe全字节及39有限inputs；0808ac确认旧authorizer AST/plan字节保护并末核39inputs changes=[]。这些是stdlib静态数据检查，测试运行数为0。

合并输出的651b66/另一并行源读取与55ddb7部分显示被工具截断，未冒称截断内容全读；eeffe0补affected尾/driver全文/edit前段，adb99b补plan62–85，fd0e73补ADR0054中段与原source，f1877b完成相干observer/母版resolver。原输出截断保留，没有重跑产品或扩大环境。

RRD-P01交原Media/Backend/Architecture；候选下一合同清单和实际权限变更均待具体批准。Input reader已完成，所有已有工具实际自然返回，无live。最终输出工具终态以FinalHandoff/FinalizerTerminal和角色实际返回消息为准。
