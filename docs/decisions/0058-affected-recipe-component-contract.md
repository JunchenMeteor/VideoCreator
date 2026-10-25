# ADR0058：修订配方、失败影响与获准组件的独立不可变合同

状态：APPROVED_SCHEMA_AND_MAPPING_CONTRACT_ONLY。批准后端唯一新版本和下列严格映射的设计；不批准产品/模型运行、用户审批、供应商权益或被拒的 intersection/subset 补丁。RRD-P01 保持 OPEN，待真实实现及独立验证。旧 ADR0053/0054/0056/0057、旧记录、exact 校验、质量标准和未知操作恢复不修改。

## 1. 来源事实与修复边界

正式独评 RepairRoleDependency-IndependentReview.md（c6eb3fac8c357098f9d11b63022c45eba917db832f776d3f21ad7aeb14947b70）§1–5及 Finding-RRD-P01（f5e2fcf6…/c278ca6f…）已全文读取。原30完整普通副本均全文件核 SHA/size 一致；四 Media37/38 recipe 的对应 SHA 相同，相关 Media38 源完整读取，Backend118 authorizer 完整必要方法与 plan mapper/writer 全文读取。不是当前热 Media 或后继 Backend0057 的实现/运行结论。

现有事实：

- Media 只为 pure-video 求 affected_shot_ids；Backend118 对全部提案求失败范围和分镜交集。组合音频和 cover-only 遇非空交集会先 422；只给它们补 shots，会分别误派 picture/Wan 或因无 video 被 403。
- clip 的 ambient 音轨实际由供应商产生；full/remix edit 把它放入 bed。visual preserve-mix 分支只用 clip 画面，并把原混音嵌入新 video。两者是不同的实际配方，旧 clip target 的 mixed_audio 依赖不能原地删掉。
- 旧 authorizer/plan writer 在“没有非 edit target”时已有合法 edit 角色交集 fallback，后续仍 exact 比较。它不是被拒的把 clip 依赖截小补丁；该旧分支及旧语义全部保留。

唯一修复方向：新增显式配方/投影/整份计划/提案/命令版本；失败影响镜头、获准重生成组件、最终写出角色、父资产读取/保留四者分开。新版本从真实完整 plan 和配方得出 exact 写出闭包；不把旧 target 重新解释、不把 dependencies 截成 actual_roles、不把 equality 换成 subset，不让最终写 video 自动派 picture。

## 2. 唯一版本与兼容 dispatcher

类型、字段实现、canonical parser、持久 command 与公共 Schema 唯一归 Backend。下列名字/format 是新设计合同，不由 Media 重建：

| 对象 | 新格式/类型 | 旧兼容 |
|---|---|---|
| 整份注册计划 | RegisteredProductionPlanV3 / registered-production-plan-v3 | 原 RegisteredProductionPlanV2 字节/解析/approval 保持 |
| 修订投影 | PlanRepairTargetsV2 / current-plan-repair-targets-v2 | 原 PlanRepairTargetsV1 保持 |
| 有限配方绑定 | PlanRepairRecipeV1 / current-plan-repair-recipe-v1 | 旧数据不回填 recipe |
| 提案 | AffectedRepairProposalV2 / current-affected-repair-proposal-v2 | 原 v1 的 affected_shot_ids 意义和检查保持 |
| 持久执行源 | current-final-affected-execution-v2 | 原 current-final-affected-execution-v1 和其 source/steps/child 不改 |
| 母版观察/已提交子 lineage | current-final-affected-masters-v2 / current-final-evidence-lineage-v3 | 原 masters-v1 / lineage-v1/v2 字节和恢复意义不变 |
| 当前 held 执行对象 | AffectedRepairExecutionV2（frozen, eq=False；同原 service registry） | 不让 v1 JSON/model_copy 成为 v2 permit |

ProductionRequest/Goal/授权政策/Bundle/ASR/CTC grammar 无须因本合同改默认或版本；CreativeRevision 的 body 由明确 format 严格 dispatch 新计划。若该 body/私有交接类型实际进入 OpenAPI，Backend 显式声明并由 Integration 生成；Media/Frontend 不手写 DTO/SDK。未知 format/未知 recipe/未知 source 不能用 legacy fallback。

新计划保原 proposal、rights_proposal、rights、timeline_duration_us、workflow_candidate；repair_targets 改为 V2，initial_recipe_id 固定 ambient-remix-v1（初次全部 clips/narration 的原完整生成；新字段不由失败角色选默认）。新版本 initial consumer 必须明确 dispatch，不能沿旧 targets[-1] 假设。V2 保 binding、资源/runtime完整 SHA、script/storyboard refs、rights_declaration_sha256、allowed_action、max_revision_cycles，增加下面唯一的 component_targets 与 recipes。不通过新版本改变原权源、限次、预算或费用身份。

新修订 JSON canonical 使用原 plan_payload_bytes 的递归 JSON：model_dump(mode=json)、sort_keys、compact separators、ensure_ascii=False、allow_nan=False、UTF-8，然后 SHA-256；数字整数/金额/微秒与字段 null 由 Backend strict model 固定。命令 source 用同一递归 canonical_body，derived steps/child/Observation 不参与 source hash 的循环。原全局 engine.canonical、Goal SHA、旧 v1/v2 字节不变；不能据旧 dict 调用名推导实现已可执行。

## 3. 四个有限配方及 exact 输出

新 recipe catalog 只允许下表固定 ID；相同 ID/版本必须对应真实固定的 installed producer/graph/template/resource，不能由模型/参数选择任意模块或 shell。以下 profile 是新增投影的真实语义，不是重新标记旧目标。

| recipe_id | 获准执行组件（由真实失败和新计划决定） | 实际输入/处理 | 最终新写闭包；必须保留 |
|---|---|---|---|
| ambient-remix-v1 | 指定 shot_clip；可另含 narration；一个 edit | 新/保留 clips 的画面和 ambient bed，实际新/父 narration，重新 amix | video+mixed_audio；若首 shot 新生成则加 cover；若 narration 组件执行则加 narration_audio。其外父母版保留 |
| visual-preserve-mix-v1 | 指定 shot_clip；一个 edit；绝无 narration | 新/保留 clip 画面；父 mixed_audio 直接嵌入新 video，clip ambient 不参与 bed/mix | video；首 shot 新生成必须同时写 cover，其余不得自动改 cover。父 mixed_audio/narration_audio 完整保留，无 TTS/mix reservation/Operation |
| audio-remix-preserved-clips-v1 | 一个 edit；可另含 narration；绝无 shot_clip | 全部 clip 画面及实际原 ambient 来自原已成功 Step；新/父 narration；新 mix 和 video | video+mixed_audio；仅实际获准 narration 组件时加 narration_audio。原 cover 和全部 clips 保留，不能因 video 输出派 picture |
| cover-from-preserved-video-v1 | 一个 cover edit；绝无 narration/shot_clip | 解码父 video，固定第一个 decoded frame（时间0）；不读任意 model prompt 替换来源 | 仅 cover；父 video/narration_audio/mixed_audio 完整保留 |

顺序固定为 narration、storyboard 顺序的 shot_clip、edit、master_index；其中 narration/shot_clip 是否出现完全由新 selection 的精确 component_target_ids 决定。master_index 是原必需免费真实索引 Step，不是第五母版或免费生成权。

选择 profile 不根据 runtime changed_roles 猜 graph。ambient/visual 至少一个合法 regenerated_shot；audio/cover 的 regenerated_shot_ids 必须为空，即使 impacted_shot_ids 非空。cover 对失败范围影响到哪些镜头保持真实数据，但不因此生成 clip。视觉首 shot 新生成却没有实际 cover 许可/失败覆盖，须拒绝该 variant；不能暗扩大 cover，也不能以“保留”掩盖与规定来源不一致的新首帧。声音配方的新 video 必须取相同 clip 画面；保留 cover 的真实来源关系须复验。

新 shot_clip 可能含供应商实际生成的 ambient 音轨及相应成本，即使 visual profile 不消费它也须在 component Observation/source/audit 中如实记载。若需要真正无音 clip，是另一个需注册/真实许可的 producer/profile，不借本合同伪称已有。

O = 按上表和所选组件求得的确切最终新写角色；
changed_media_roles 必须逐项等于 O 的固定角色顺序，且 O 必须完全属于原 READY failed report/原 candidate 的 actual failed artifact roles 和真实完整批准范围。该 actual-role 上界不是把旧依赖作交集。所有未写角色是明确保留集合 four_roles - O；不能自动重做全部母版或仅为达到 exact 多生成声音。

## 4. PlanRepairTargetsV2 的最小完整字段

component_targets 使用新的 PlanRepairComponentTargetV1，不复用旧 dependent_media_roles 作另一语义。严格字段：

- target_id、kind（narration/shot_clip/edit）、shot_ids、timeline_range（原整数微秒半开区间）。
- route_id/route_sha256、resource_section/resource_section_sha256。
- input_revision_refs（原 script/storyboard 的精确 revision/body SHA）、input_payload_template_sha256、prerequisite_target_ids。
- output_roles（组件实际输出；clip 是 shot_clip，不把其 stream 伪当完整 mixed_audio）、component_output_key（原受控单 clip/旁白或固定 edit 角色顺序，Backend 唯一）。
- recipe_id：edit 必须是上表某个 ID，target_id 固定 production-edit.<recipe_id>；共用 narration/shot_clip 模板必须是显式 null，并由 recipe 的 component_target_ids 引用。null 不表示未知配方，不能用来执行 edit。clip/narration 原共同模板不能据此挑任意实现。

共同 narration/shot targets 来源仍是原完整 script/每个 storyboard shot；timeline、文本/visual/camera/输入模板和真实 provider payload/config 语义均纳入固定来源。原 target IDs 仅定位数据，v2 target body/完整 projection SHA 是新身份，不使同名旧 target 自动兼容。

每个 PlanRepairRecipeV1 严格字段：

- format、recipe_id（上表四者）、implementation_version。
- producer_source_refs：tuple(resource_name, sha256)，必须是原已持有完整安装 index 中的 factory、mapper consumer、实际 driver/provider/edit graph 和所有执行模块的有限真实来源；没有任意 import/path/URL。resource/runtime/projection 完整身份与它关联。
- component_target_ids：本 profile 允许的有限原目标目录，按原依赖顺序（共同 narration/shot_clip 模板及本 recipe 唯一 edit）；edit 目标唯一且其模板 SHA 明示真实 graph/profile、原分镜/时长、父角色输入规则和 exact 输出规则。不是“本次实际选择”。
- routes：本 profile 可能实际执行的固定 route/完整 body SHA/cost_rule_version；每个实际 target 必须对应同一 route。price/cost 仍要真实来源，unknown 不填0。
- frame_source：仅 first_frame_of_new_video 或 first_frame_of_preserved_video，按上表固定；不能任意选择帧。
- clip_audio_mode：ambient_consumed 或 ambient_ignored，按上表固定。
- narration_mode：optional_registered_narration 或 preserved_narration_only；mixed_audio_mode：remix_actual_inputs 或 preserve_parent_bytes。
- allowed_output_variants：有限有序角色元组，恰为上表的合法规则展开。是否首 shot 和是否 narration 必须仍由 canonical mapper 独立验证，声明 variant 不是 permit。

V2 targets graph 必须 distinct/finite/无环，prerequisite 只指前置原 component templates；recipe IDs、引用和 source refs 唯一。script/storyboard 是不同原 revisions，recipe 不携带未来 Asset、child/command/admission/Operation IDs。原分镜 shot/duration/order 不因修复改变。实现不新增任意 recipe rule 字符串或通用解释器。

真实 producer/source closure 尚未建立前，这些只是待持有的 exact 名称/模板，不构造伪 source SHA 或资格。Integration 需按 Backend sole resource grammar 纳入 registered-production-driver-resources-v3：保现 narration/picture/edit/alignment 成员，增加上述有限 recipe producer/index/template refs。使用哪个 profile，只要求其实际用到的 provider/route/凭证/资源就绪，不能因为本次只做 cover 或 audio edit就强制调用未配置 Wan；所有被实际加载/声明的代码资源仍须原完整安装 coverage。新增本地/BYOK factory/provider另卡，不在这里假设已经完成。

## 5. Backend 唯一失败映射与 selection

Backend 同一个纯 typed mapper 贯穿 prepare、proposal、admission、writer、dispatch、恢复、observe、child、final verify/publish。输入为原真实 report/failed units、完整 storyboard/source clocks、新 approved plan/projection、原 current binding/resources；模型和 Media 不独立从 semantic segments 重算另一组。

impacted_shot_ids：按 storyboard 原顺序，取实际 failed predicted_range 映射到原成片 timeline 后，与原 shot [start_us,end_us) 有严格交集者。若报告已经是成片坐标，不再映射；若是音频内坐标，先用原完整 AudioTimelineMapping 的 segment/整数微秒规则。没有完整合法 mapping/失败时间源不能假当同坐标或 fallback 全部 shots。原 failed_unit_ids/threshold200000/原失败报告字节保持；纯画面/source-integrity无独立unit时间来源时，只能使用原真实明确 artifact/shot source 闭包，不能造音频失败单位。

regenerated_shot_ids：确实获准重新生成的 clip 组件；ambient/visual 为 mapper 从失败 source 和本 recipe 显式可修复目标所得的 finite 非空集合，不能超 impacted/source-authenticated shot 范围；audio/cover 必为空。impact 集合本身不授组件权限。

recipe 选择来自整份新计划的有限允许 profiles 与真实失败原因/需要修复的组件。固定选择顺序：cover-only 的目标故障选 cover；narration 或 mix/source-clock 问题选 audio（仅确实需要改变speech时选 narration组件）；真实画面/semantic-source问题选 visual；只有原失败及许可/新计划明确要求消耗新 clip ambient 并覆盖全部 exact 角色时才可选 ambient。多个矛盾失败、无法判断音轨/画面组件或没有合法 exact variant，返回具体 guidance_required，不以顺序掩盖坏音频或超范围。用户指导可产生新的真实有限 plan/目标来源，不能 model bool 补权。

新增唯一 held 数据准备口：
```text
CurrentFinalEvidencePorts.prepare_affected_recipe_proposal(
    ordinary_lease, continuation
) -> AffectedRepairProposalV2
```
它读取原Executing/repair/new-fence claim和真实源，返回数据；不 register command、不 begin Operation、不扣额度，不授执行。仅新计划 v3+投影v2用此口。旧 plan/proposal v1 继续旧 mapper/authorizer，不能吞旧拒绝改走v2。

AffectedRepairProposalV2 的完整字段为：
format、parent_preparation_id、affected_artifact_ids、failed_unit_ids、requested_action（regenerate_affected_media）、changed_media_roles、impacted_shot_ids、regenerated_shot_ids、recipe_id、projection_sha256、recipe_binding_sha256、component_target_ids。
所有数组 distinct/有限/原权威顺序；projection/recipe hashes由原 Backend prepare 的真实对象提供，再由authorizer独立重算，不接模型的hash当权。原CTC realignment提案和0056/0057继续v1，不混profile2。

原 authorize_affected_execution 同 held口按严格 type/format dispatch v1/v2，v2返回 AffectedRepairExecutionV2；这个新eq=False对象保原 execution 的 binding/fence/parent/command/report/affected/failed/action/roles，增加与提案完全一致的五项选择（impact、regenerated shots、recipe/projection绑定、component IDs）；其字段由原 common execution字段加 proposal中 projection_sha256、recipe_binding_sha256、recipe_id、impacted_shot_ids、regenerated_shot_ids、component_target_ids 组成，v2没有旧 overloaded affected_shot_ids；完整形状Backend sole声明。只有原service registry在同线程/lease/newfence中登记后可用。JSON、mapper结果、hash、无registry对象、plan数据或model建议都不是执行权。

原 read_affected_execution_inputs 按原命令 format 返回 AffectedRepairReadSet 或新增 AffectedRepairReadSetV2；v2仍是 frozen/eq=False 的四成员 execution（V2）、parent（原11 readset）、child（原11 readset或None）、masters（原服务登记的 AffectedMasterObservation或None）。不是Media第二DTO。原 observe_affected_masters 签名保持，接受原service登记的V1/V2执行对象；返回原观察类型，通过command完整SHA绑定recipe/targets及exact O。v2持久观察body用 masters-v2，完整绑定原component Steps、实际Operations/assets/probes/clock；其重核不能沿v1的“video+impactshots”推定steps。

## 6. 命令、实际输入与 effects 顺序

newcommand源绑定：格式v2、同原 binding/parent intent/report/failed/affected/plan_ref/quality_ref、完整 projection/recipe/source/template SHA、精确 impacted/regenerated/component选择、O、真实 route/cost/resource/runtime/rights；另外绑定 preserved_role_refs 与原 component 输入定位。preserved refs 来自原观察资产，保存原 Asset ID/完整 SHA/size/MIME/probe/实际clock/source Step和用途许可；Media不能据renderer Asset ID/URL补入。

计划阶段只有原 target/parent role/原source Step 的封闭定位规则；command准备读取父已存在事实后才能解引用真实 parent Asset。尚未执行的前置组件用同一 command 内的原 target 引用，不填未来输出 UUID。真实 Operation登记、ordered allocation、Step完成后，才解引用它的实际 GeneratedFileManifest/Asset/clock。source SHA不包含未来派生descriptor/child/Observation，steps由原 source SHA+stage+component target确定，再校验固定 exact 表；没有自哈希环。v2 Step/dedupe 的唯一确定性 grammar 是 repair2-<stage>-<sourceSHA前32>-<sha256(target_id UTF-8)前16>；stage闭集为 narration/picture/edit/master。master用固定target_id production-master，edit用本recipe edit target。它仅用于首次真正获准的新v2命令；不得拿它为已有v1/v2 unknown 换key重交。

source写入顺序：真实 held/current/lease/repair claim → 读完整失败/计划/投影/父source/实际许可/资源 → 重算 exact selection → 同原 issuer/runtime取得当前整份plan+quality与有限修订资格 → SQL外实际文件/decoder/authority校验 → 原短writer重核原claim、当前权源和immutable source并原子登记command/确定Step descriptors → 效果前再核当前原执行对象 → 原 Worker原Operation先登记后调用已准component → 原实际Observation/完整allocation/Step commit → 原 master index观察exact O及四effective roles → 原子幂等child/计数 → 原ASR/文本/对齐/精度/RAG/Bundle验证和publish重核。

Media只能迭代原 execution.component_target_ids；picture仅来自原 regenerated_shot_ids，音频配方和cover无picture目标就不得调用picture；narration仅来自真正选中的narration target。edit从固定recipe ID执行固定 graph和ordered O，不由 changed_roles推图。原builder/Executor/Worker/permit/输出reservation保持，不构造Worker、伪permit或任意driver。

v2 route_bindings/steps只列本次真正选中组件及必需index；原权源/计划catalog仍完整核对。读父clips不自动需要一个新的picture permit；cover不要求新的provider视频生成权益。父输入读取/derivative/export/standalone_audio/rag/复制再分发仍按实际用途与完整 license closure，不额外公开grant或凭oldorigin本机授票。

原 child commit持久 lineage-v3 保原 parent/child preparation/revision/intent/source-report/affected来源字段，并固定实际 v2 command/sourceSHA、projection/recipe绑定和exact O；这些值来自真实同writer观察，不由Media/model填写。原 bounded resolver识别该明确新grammar并核所有component/source/保留项；不能因未知lineage格式跳边。0056/0057的ASR/CTC私有读取ABI不变，只有原共享祖先resolver增加严格已认证v3边的辨识，32/原revision限次和同Run/实际audio/text/mapping/current条件保持。realignment仍原v1 command，不通过v2recipe获得CTC或权限。

保留 input dependency 与写集区别：clip/narration父input即使未执行也是实际 prerequisite read-source；不能从 graph删除其来源。v2组件 execute/reuse选择明确记录在command，所有父未变母版完整身份保持；变更用新真实Asset不能原地替换旧文件。visual新MP4的AAC/encoded track是新实际事实，重做完整decode/时钟/源混音mapping；同bytes/decode-clock的实际mix才允许保原ASR/context。新音频走原child-ASR intent/context-first/CTC登记闭包，不用估计文本或旧音频reference当新证据。

## 7. 真实批准与被拒边界

本ADR批准 schema/mapping 设计，不能代三类不同批准：

1. 新源/schema/recipe implementation 的独立审查和正常自动审批：原 rejected dependencies &= actual_roles / changed<=dependencies 仍不执行；新实现必须证明是在明确新计划/配方/whole source和许可下的独立 exact 路径，旧函数分支不变。不能只改名字/format包住同被拒补丁。RRD-P01的关闭必须由独立Review/Test，不由本文宣告。
2. interactive 真实human批准：同原真人ReviewDecision approve 新整份 CreativeRevision ID/body SHA，包括全部v3 recipe/catalog/输入/资源/rights/route/费用/限次。旧plan或quality批准不授这份新plan。派发前仍是同真实审批来源和current。
3. unattended 原Owner一次预授权：须真正的native/headless Owner安装/选择/派生来源及当前 ProductionAuthorizationPolicy/同Run execute_plan admission，覆盖新完整 registration/resource/runtime身份、catalog所用route/cost_rule、输入源/用途、rights、输出/时长、有限revision与原预算组；execute_plan事实绑定这份新完整plan SHA。原policy类型字段足以表达这些边界，本卡不增加新宽action/wildcard或另建授权体系。不得回填Owner action/hash替换原政策；已安装旧source与新source不同须按真实Owner replace/reauthorize及原层级恢复。已覆盖的设置后正常App/Portal自动运行，不能每作品伪人审或永久改成human-only。

新plan prepare只是数据不授执行。若实际现有issuer不能证明某新profile的完整覆盖，Backend记录具体 waiting_authorization/source gap，并接原真实Owner更新；不静默把原旧policy解释为新增route/provider权。合法已覆盖的完整新plan须实现自动正向，不永久503代成品。软件升级/新资源资格和真实rights许可分别检查，不把source SHA当真实权利或资格。

已有作品改变recipe、script/storyboard/route/资源/用途/时长/budget或范围属于原0054 expansion；保持其真实修订/确认路径和当前源绑定。若实际submit_decision.revise创建新Run，标明真实新Run，不冒同Run修复；新Run不能用来清理同Production旧unknown、换共享预算或重置限次。新recipe只可由新真实获准plan源首次登记，绝不迁移原未知command为v2或换key重发。

## 8. 兼容、错误与防重复

初始/prepare/claim/dispatch/observe/recover/child/final verify/publish用同一个严格版本dispatcher；不是仅初次schema核。旧v1命令有unknown/pending/partial时仍调用原受限核实与原exact目标/原resources，不以v2可用制造第二Operation；same原source/version/key重复只读原结果。不同recipe/模板与原同一failed源已登记command冲突，返回409，先完成原明确恢复/真实修订，不造双子作品。

新source资格/current/许可/Owner过期撤销403；错recipe/role/shot/target/输入/route/sourceSHA 403或原422 integrity；错phase/fence/旧journal409；资源/许可证/driver未就绪明确NOT_READY；质量P95>200ms/MM05真实失败沿原有界修复/拒绝，不靠选profile通过。没有完整坐标/原source证明时不能填unknown为null继续。

source/文件/媒体/authority大检查在SQL外；writer只原本地current/guard/source snapshot/command/claim/Step/asset/registry/license rows短重核。两真实authority保持，第二false仍403；allocator/完成Observation/commit/counter原链不跳。全Production原counter/剩余预算/未知费用状态共享；child一次原子计数，不因profile/version/task名给新次数。

## 9. 独立真实验证与角色切片

Backend：新增sole域v2/v3类型与严格parse；prepare_plan_repair_targets_v2从原实际固定source派生；新 held prepare proposal及原authorize type dispatch；原persist registry/command/steps/guard/resolver各点接同mapper；保旧v1/v2全分支；移除新路径把impacted_shots当picture permission的推导。新command仍可用原metadata持久键前缀、严格format区分，无回填旧行；如需新DB迁移另明确真实必要，不因schema新名自动写migration。

Media：实际四个固定profile消费者、picture/narration组件选择、父实际输入/保留、graph/output/probe/sourceclock/audit闭包；新声/封面正向，不调用未获准组件；只能消费Backend typed执行/注册口，无SQL/第二DTO。本卡不默认承认厂商/本地资源已装或权益可用。

Integration：完整固定producer/resource/license/held-index/catalog/template/code源供Backend核，旧artifact/unknown资源不可混；如需生成public契约/SDK只从Backend sole源；所有平台（Winx64、mac arm64/x64、Linuxx64/OCI）仍需真实资源/执行证据。本地/BYOK新factory按其原排队任务保留，不能把Wan配不出当全产品结束。

Test/Review/Acceptance 独立owner标准与执行，至少真实验证：
- 原旧plan video-only被exact拒，原edit合法fallback和original ambient组合兼容，原被拒patch仍未应用。
- new visual只生成合法clips/video/必要cover；无TTS/mix allocation/Op，父mix/narration ID/fullbytes/probe-clock/许可不变，ambient副产及真实成本如实记录；新encoded video实际看听/同步。
- new audio从原clips重edit，impacted_shots非空也零picture调用；需要narration时仅真narration target一次；保cover。
- cover-only影响shots非空仍只cover，原video被真实完整decode；无picture/TTS/video/mix新输出。
- same mapper得到唯一有序影响/重生成/组件/O，与所有writer/consumer一致；跨坐标mapping/半开区间边界/未知时间/无法diagnose不能fallback全shots。
- 超actualfailed/approval roles、首shot缺cover权限、假profile/source/template/target/price、撤销/过期/线程/旧fence/current源变化全部拒；质量批准不授生成。
- 原Operation pending/unknown与真实kill窗口恢复不第二submit/成本/输出/counter；混旧format或same failed源新recipe冲突不能新command。
- 原双authority第二false403、真实独立来源/200ms/MM05/null规则、audio变更后的ASR/CTC/context/字幕/音视频文本/RAG和整包真实闭环不降低。

没有本轮运行/模型/网络/SQL/测试/审批或资源资格证明。完整五步UI、安装实例自持数据、本地免产品注册/BYOK、API/MCP已预授权自动至完整成片与R1独验后连续R2仍OPEN。此合同解决来源及组件选择语义，不能单靠文档关闭功能。

## 10. 固定输入与交接

本卡4be1ffe6d47a432de91d31d058b1e410e5896fa20ab15e5fe697f8fb4621c2fd。原30 OrdinaryIndex bc97d500d9101110d54ddb8bef3ce5fe993b954c7eb9ac1573e9c9577cc62471；完整普通件由自身Architecture/AffectedRecipeComponentContract/Ordinary复制并固定，必要FULL/方法范围及工具自然退出列InputPins。

四recipe：affected_production b27f7955e775b28caeab35f51dc6ef6321f7b8e2e5da915e1886b0ef55ca4a0e；production_drivers de95cd8a13d84a8b74a68f4b308d1cc2a554a3f28994eb2b94f66b87dd263969；production_edit 9f2c2f2b613ca407b54b0b33b0d3e8f57bcad1a3b7ef0ed99fd9e37cb132a199；wan_video 91502007d6420ac01ced8869239d6ae5e9c4497c2ef39c5aac9c3ec2b7c3467b。
Backend118 authorizer92a70eea9c7d9f81b30cc9d8d69ca333bb789b38818f61da9eae787f1c3e3c2b、plan mapper/writer658f03e23e877c4fd7a0cb957aa576fd2da0b42aca8b90017c6357c22a2f0085。补充准确停止domain plan_repair_targets40669dff8cf22f5fa874315c3cc0a3f653c79dc1d6fd0820186024a14ad7e0f6、production_authorization292aa2230c6247b39f7859277f3580e7d9520921f255a182338dea5ef0f4c5ef。
这些只是source-only固定身份；本轮不读热Media/Backend，不改任何旧停止件。
