# BackendAffectedRecipePartial — 独立源码评审

结论：SOURCE_STATIC / 两项 P2 OPEN（ARP-P01、ARP-P02，归属 Backend）。本停止片段的有限类型、mapper、投影准备与 repair2 算法已有实际源码；它没有形成完整 0058 执行链，不能关闭 RRD-P01 或称自动制作完成。无产品/SQL/Pydantic/模型/native/网络/安装/收费运行，未批准运行或 RuntimeBinding。

## 固定版本及核对

任务卡 BackendAffectedRecipePartialIndependentReview.md：802bdf35db62fa82695a5a8e03e31ef7946eeb54f7aff1daab970971a4069d25。唯一新源来自停止 Backend/AffectedRecipeComponentImplementation/SourceStageRevisionTwo/SourceCopies；未读热 Backend、Architecture0059 或 Media。

- SourceIndex.json：9b050d8eb5fc14c3c34a2bf121ad9f7cb4fc9f640317b8646149e83b3911b177，124 普通源/113 Python AST。
- 真正修前索引是 SourceBefore/SourceIndex.json：99246161cecc1d31b519e8b3f6aea30552784e5aba6ad00129781488910ca383。其 121 文件与独立停止 ParentSnapshotRepair 索引 094612107d288c485a66d7466793830e3ff22f9a9f3401cc1050a790fb2a3060 对应普通件完整 bytes/SHA 一致；两者各 110 AST。
- 3 新模块、2 改动模块、无删除，119 原文件完整字节不变。独立按 before/after 完整原件重建 Changes.diff，38541B/SHA 081760242e970958ed0c1175a19228be78b9e3b0ec24d043ea1678e5243f586b，逐字节等于作者停止 diff。
- Handoff.md 18d7d1d081b30ec39af9477a9e27620bd05ed78c197208a27ce21d4229433352；Handoff.json 4bd417903fbab5d91699679bfa7d14afa8c436c9dd5606a0f80e8a787bcfd370；InterfacesRevisionTwo.md 2c8b23f2861a439881102b5697c83817372bad48ebaf9f1669e0d66b0d1b3e94；ADR0058 a2660ba525f88fc81539e238fafb9c7c51eaf7b3c46f70f4726db785f44b6857。完整接口/类型/mapper/两改动模块已读；不依作者 Checks 的 bool 代独评。
- 初始 InputBefore 382 个有限路径，末核原 382 与显式依赖补充 2，共 384；差异为空。不是 384 项运行测试或全环境盘点。InputAfter SHA f388fb03653c88215db2e5309eac15203d62333137be5cf33a6e61c146d8bef8。

三新源：application/affected_recipe_plan.py eaa5ca332abc8d569ee3d9507d76b79d2b86ed6afc326b499bdb8531876114b0；domain/affected_recipe.py 66574a395cecf1d7e80e5243e06513aad25056867c8946b2afdbef16ad00b0c1；domain/affected_recipe_mapping.py 4eae9e36897f7b61f5f62bfcb803b097ebf70262bb1f9694c184d06a1af90b92。
两改动源：application/plan_repair_service.py 65b668671d2a3bc2a4fc99d69fdfe94f026016f79026933621066fc4ccf27767；domain/affected_repair_steps.py a5269358daeaed978b3db5b01041615bf3d5753e2c4236c49ecba6fffdb4bf14。

## 已确认问题

### ARP-P01 / P2 / Backend / OPEN：初始 ambient 目录可漏完整初次生成组件

固定 ordinary affected_recipe.py 100–120、160–178、205–216 只检验模式、引用顺序、route、唯一 edit、初始 recipe 存在及全局 storyboard 对应；未要求初始 ambient recipe.component_target_ids 完整覆盖 production-narration、每个原 clip 和自身 edit。一个完整全局 component_targets，搭配只列自身 edit 的 ambient recipe，满足这些静态条件。affected_recipe_plan.py 60–63 允许空 prerequisites，71–81 创建同一空前置 edit；94–99 重建同目录的 equality 无法补回该不变量。

ADR0058 33 规定初次全部 clips/narration 原完整生成，73 区分目录和本次选择。漏目录会使未来按唯一码目录执行的初始计划不能选择被漏掉的生成组件。本 finding 是新完整计划数据不变量，非要求每次修复都全量生成、非权限绕过或真实产品失败。当前 V3 loader 未接通，所以并未观察这份计划真正准备/执行成功。

修复边界：新增整个初始计划/投影的 exact 覆盖校验，保后续 mapper 的合法部分选择及旧计划字节。独立后继测试应有完整目录阳性、漏 narration/任意 clip 拒绝及 audio/cover 小写集仍合法。完整 finding：Review/BackendAffectedRecipePartialIndependentReview/Finding-ARP-P01.md，SHA 80f3cf01c661e27f479546de50fb2a43e966cf1831a981b77dd5376dc5aa3e07。

### ARP-P02 / P2 / Backend / OPEN：严格 format 解析的错误边界漏非字符串

affected_recipe.py 288–289/304–305 在 try/model_validate 之前用 JSON format 作 dict key；{"format":[]} 或 {"format":{}} 会在此引出不可 hash 的 TypeError。它不走既定 plan_repair_body_invalid 422 / production_resource_invalid 503。未执行解析器或 HTTP，不能将此写成已复现 HTTP500；当前两 helper 尚无生产 direct-call 接线也不等于实现正确。

修复：查固定表前精确检查 string；保所有未知格式拒绝/strict model，不 stringify，不让 malformed 格式 fallback。后继测试覆盖 array/object/null/bool/number/未知字符串及合法 v2/v3。完整 finding：Finding-ARP-P02.md，SHA 3a6f4c881ec9fa92dcc67b9d229c48323c0116d7e694dc6c03601dd19e848050。

## 本片已有源码支持与保留保护

affected_recipe.py 40–179 分开新 component 的实际 output_roles、recipe_id 与原 dependent_media_roles；graph 使用 preceding references，禁止环、自引用、重复目标/recipe/source/route，保 script/storyboard 不同原 revision 与 SHA。四 recipe 固定图及 ordered output variants 明确，原共享 narration/clip recipe_id 为 null 而 edit 必须命名；execution/readset 的 frozen、eq=False 是数据形状，尚无新 registry permit。

mapper 13–47 从原 failed_unit_ids 有序选择 predicted_range：work_timeline 不重映射；audio_intrinsic 按实际 source SHA/有理播放率作整数 half-up，逐片要求完整无 gap/duplicate coverage，越 piece 半开范围拒绝；其他 coordinate/无 mapping 明确 guidance_required。旧 AudioMappingPiece 保正且约分 rational、实际 sample/PTS 证据及 decoded bounds。真实 source/目标 clock/许可仍需后继 held reader核实，纯函数不能认证传入对象。

mapper 66–122 按原 storyboard 求 impacted，visual/ambient 再取真正获准 source shots；audio/cover 保 regenerated 空，不因写出 video 派 picture。新 narration 仅 optional recipe 可选；cover 固定单写、visual 保 mix，首 shot 重做才增 cover，ambient/audio remix 增真实 mixed_audio。ordered 写集 O 严格来自固定 variant；O 属于 actual failed roles 是上界，而不是把旧 dependent roles 作 intersection。changed_media_roles 直接写 exact O，未把旧 exact 改成 subset。失败组件/需改 speech/需 ambient 的来源目前只是假设的 caller authenticated facts，不能 model bool 补权。

prepare_plan_repair_targets_v2 20–21 重用原真实 script/storyboard/rights/source 准备，不重用旧角色依赖；其后读取同 held manifest SHA/上限、源文件/index、实际 route完整 SHA/cost_rule，创建 distinct edit template/projection，82–84 重核 held current/manifest。validate_registered_plan_v3 对整体投影精确重建比较。这里能看见正确的调用设计，当前资源 V3 接线仍缺，不能宣已通过。

旧 PlanRepairService 的 prepare、commit_guard、source_writer、held_writer、command_targets_writer 5 方法 AST 保持；validate_registered_plan 原 V2 函数尾部在新增两段版本 dispatch 后 AST 保持；旧 affected_master_step/affected_step_recipe 两方法 AST 保持。原合法 edit fallback 223–225、随后 exact equality、真实 whole-plan human/Owner execute_plan source、预算/限次/route/rights/current/guard 原保护没有在本片被截小。ParentSnapshotRepair/registered CTC/两 authority/200ms 的全部原文件亦完整字节不变，不据此重签其运行。

repair2 只为新 V2 数据求 sole 确定性 step/dedupe/input SHA；component_id 精确来自选中 narration、regenerated clips、recipe edit 或 production-master，canonical JSON UTF-8/sort/compact/allow_nan=false。算法未创建 Operation、writer、permit 或给旧 unknown 换 key；没有真实 registry 不授执行。

## 明确未实施/未运行范围

原 SourceIndex 不包含 Media-owned ProductionResources，因此补充读取停止 SelectedChildCtcReadConsumption 的 SourceSnapshot 5f61cba8b75a0f39a1f25d9cb029edaf66ac078df3e4f74954a714286cb6abf2 与普通 providers/production_resources.py fc61303f9b56947cec508ea14b6d52074531fff8c825033599716d36d2c4e046（6606B），独立核 SHA/size 后全文读取；原 InputBefore 不回填。其 constructor 86–103 只接受旧 v1/v2，当前 prepare 在29要求 V3，再32调用旧 loader，尚不能走通 V3。这是已披露跨角色接线缺项，非本轮运行红或已完成准备口。路径/无 symlink/junction/安装 containment、complete index/size/SHA 和 current_attempt check 原保护真实存在；不能用资源哈希代安装资格、许可、Owner批准或 producer 实际 profile。

实际 V1 authorizer 365–388 只接受旧 proposal，读取原报告并判断 >200000us 边界，不提供声音/画面/cover/source诊断。新 held prepare_affected_recipe_proposal、V2 registry/command/short writer、真实 effect/recovery、Worker/masters、atomic lineage-v3、0057祖先版本 dispatch 尚未实施；113模块 AST 中新 mapper/parse 无 direct-call 服务接线，不能从此静态列表推所有动态行为。FailureDiagnosisGap 的 source claim与实际入口相符，真实诊断数据/批准仍 OPEN。

没有正常新计划、真实 DB rollback/replay/竞态、Operation未知受理/费用、原子 child/counter、完整 CTC/独立 gold/200ms/MM05、音视频听审、安装整包、多平台或发行证据。本报告没有完整制作流程/安装整包通过的独立证据。R1三OS真实作品多模态独验后连续完整R2、五步UI、自持数据、Portal/API/MCP目标仍保留。

## 原记录与工具边界

保留原作者 locator失败/输出截断与未运行状态，不改任何旧红/被拒 intersection 补丁/累计三次目标限制。评审原0151b5尝试 SourceBefore/Index.json 的定位错误、cb21f1 absent providers key导致 exit1 保留为读路径错误；未称产品红。008cee/15ff8f 输出截断已对缺失正文定向补读，不声称截断部分全文已见。无全运行环境扫描或新依赖。

关键纯解析：ae6d31自然0（366份普通原件三组身份/AST及完整diff）；3fef19自然0（旧函数/停止loader补充）；323ab2自然0（AST位置/旧诊断）；c567f4自然0（384有限末核）。过程目录保存 InputBefore/InputSupplement/InputAfter、SourceFacts/ProtectionFacts/SourceCallLocations、重建diff和两个finding。后续修订由原Backend与Media归属者完成，Review不修实现/测试或批准运行。