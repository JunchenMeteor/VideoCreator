# ARP-P01/P02 后端窄修：独立源码复核

结论：ARP-P01、ARP-P02 在本固定124源码版本可裁定 CLOSED_SOURCE_STATIC_ONLY；没有确认新的 P1/P2。本报告不是 Pydantic、数据库、HTTP、生产资源或媒体执行验证，不关闭 RRD 全链/完整0059/安装或R1→R2验收。原两份 OPEN finding 和原报告不修改；本文件记录后继精确版本的独立源码裁定。

## 固定输入与独立对照

任务卡：`G:/开发测试/Projects/VideoCreator/docs/task-board/BackendAffectedRecipeCorrectionIndependentReview.md`，244a51b85367ddc80e147399f8b77013e6e570663d2fc4b7cc1d550470f9ca2c；QUEUED 文字是原固定治理状态，本轮激活来自统筹明确角色分派，未改卡。

新停止根：`G:/开发测试/Codex/VideoCreatorImplementation/Backend/AffectedRecipeReviewCorrections`。

- Handoff.md 01064286195888d4254cdc2ac87bec9321cb0ec7a381c11144dd847d57c6de67；Handoff.json 312917c4cd7a4cd60598392af5cc29483eb931e14a5cf61ed95ad12d9d401643；Interfaces.md d71f67e801eb4144a905ef1c65640f6e786cee4237fb76d0175466a1ad131534，完整读取。
- SourceStage/SourceIndex.json 16d94d493f3b5e77690a501703c7c713376c233629fb428d1fb97c99dbe4f4bb；SourceBefore/SourceIndex.json 5af0f31e3f4b85c12609266a38b636db9fe720120846c7999beb9204b3190bfe。
- 原独立停止124基线：`G:/开发测试/Codex/VideoCreatorImplementation/Backend/AffectedRecipeComponentImplementation/SourceStageRevisionTwo/SourceIndex.json`，9b050d8eb5fc14c3c34a2bf121ad9f7cb4fc9f640317b8646149e83b3911b177。
- 独立读取三组各124普通副本的完整 bytes/SHA，各113 Python AST，不读各索引的 production source_path。新 SourceBefore 的124份逐件与原停止基线一致；修后只有下述两源改变，其他122份完整字节不变。
- Changes.diff 3162B／470ac3eb10d95c25a5026d1e945fb6ea2146f845904867c073713fa3d4efc3b6，从真实 before/after 完整件独立重建逐字节相同。四窄修的精确 AST 逆变换后，两完整模块等于原完整 AST，不依作者 Checks 的 bool。

新普通源完整路径与身份：

`G:/开发测试/Codex/VideoCreatorImplementation/Backend/AffectedRecipeReviewCorrections/SourceStage/SourceCopies/services/engine/src/video_creator/domain/affected_recipe.py`：18117B／9c9a3e1b80e223238ec484e0cb926cfa8af395648d28f2d45d9639a861ccb4bb；修前66574a395cecf1d7e80e5243e06513aad25056867c8946b2afdbef16ad00b0c1。

`G:/开发测试/Codex/VideoCreatorImplementation/Backend/AffectedRecipeReviewCorrections/SourceStage/SourceCopies/services/engine/src/video_creator/application/affected_recipe_plan.py`：7838B／2687e00a7fd5351c0e634a46e58c139f024746e0996444a070ff345dd17c3e52；修前eaa5ca332abc8d569ee3d9507d76b79d2b86ed6afc326b499bdb8531876114b0。

原报告 `G:/开发测试/Projects/VideoCreator/docs/reviews/BackendAffectedRecipePartial-IndependentReview.md` ccb8eb237d7c50ee314d37aed7f52ed2a14435ccefad3f77925418b47f240d1b，以及原 P01/P02 完整finding 80f3cf01c661e27f479546de50fb2a43e966cf1831a981b77dd5376dc5aa3e07／3a6f4c881ec9fa92dcc67b9d229c48323c0116d7e694dc6c03601dd19e848050 均保留。原 InputBefore384 精确路径，显式原finding补充2件，末核386路径无变化；不是386项执行测试或全环境扫描。

## ARP-P01：仅源码关闭

原缺口是初始 ambient catalog 可只引用 edit，不涵盖 narration/所有 clips。新 domain affected_recipe.py 162–164 精确要求 ambient-remix-v1.component_target_ids 等于全局 component_targets 中每个 non-edit 的原顺序，再接唯一 production-edit.ambient-remix-v1。不能靠 set 包含或 intersection 通过。结合原 140–181：ID/recipe distinct、首个且唯一 narration、所有 non-edit 在 edit 前、前置refs与不同script/storyboard精确SHA、recipe顺序/route和唯一matching edit保护，漏 narration/任意 clip、重复、多项、错顺序均不能满足该 equality。

RegisteredProductionPlanV3 204–225 保初始 ambient 固定存在、rights declaration/request/run/registration一致、全局 clips 与 proposal.shots 同序、所有 half-open clock 和总duration真实对应。新guard并未把全局零碎列表当完整storyboard。

实际 prepare 链也有独立新guard：application affected_recipe_plan.py 48–50 用原真实 `original.targets[:-1]` 的完整顺序和唯一ambient edit作比较，错误为原 plan_repair_recipe_not_ready503；这发生在生成新 edit template/PlanRepairTargetsV2 之前。不是 caller 自供route/template覆盖原source。

相干原源已读：同停止目录 application/plan_repair_service.py prepare_plan_repair_targets 21–117 在原lease/current guard/readonly来源中核 committed script/storyboard 和proposal全字段；79–107真实构造单narration、每个原ordered shot和最后edit；domain/plan_repair_targets.py 48–105 强制首narration、末唯一edit、中间全部clips、原edit依赖 exact ids[:-1]。因而新actual guard不是盲切掉任何末项。新prepare85–87及validate_registered_plan_v3 97–102继续held current、manifest bytes与完整重新投影比较。

初始完整catalog和后续本次修复selection不同。domain/affected_recipe_mapping.py 50–122 完整未改，audio/cover保持 regenerated=()；98–105按recipe+本次实际重做narration/shot仅选必要component，cover/audio不得列shot_clip的原 domain175–177仍保。新增guard只针对初始ambient目录，不要求每次audio/cover/visual修复全量生成，也不把旧 exact output_roles 改成subset。

本版本具备原finding要求的双层精确来源检查，故 ARP-P01 为 CLOSED_SOURCE_STATIC_ONLY。实际正常/漏目录/局部修复的 Pydantic/服务/DB行为尚未测试，不能升级成运行关闭。

## ARP-P02：仅源码关闭

domain affected_recipe.py 的两个严格解析入口分别在 290–292 和 309–311 获取format后检查 `type(version) is str`，然后才在294／313的固定字典查找。array/object不再进入unhashable-key分支；null/bool/number/缺字段均在同门拒绝，既不stringify也不catch后fallback。

plan入口仍返回 EngineError plan_repair_body_invalid422，resource入口 production_resource_invalid503；未知string仍走原unknown-version错误。合法 known v2/v3 的字典模型选取及297–300／316–319 strict model_validate/catch边界保持。新增局部version变量只替换原resource查找参数，完整AST精确逆变换已核，没有扩大允许格式、删除strict模型或改变原调用权限。

故原 format=[]/{ } 导致查表前 TypeError 的源码缺口已关闭，为 CLOSED_SOURCE_STATIC_ONLY。没有构造/导入 Pydantic 模型、运行入口或发送HTTP；不能声称已复现/修复实际HTTP500或两API正反样本全过。

## 保护及明确开放范围

124中122全字节保持，包括原 plan_repair_service、repair2算法、mapper、parent snapshot、registered CTC、precision两authority、200000us、source rights/current/thread/fence、unknown/共享预算/限次/registration/child代码。对两changed模块精确逆变换仅去本次四guard及resource lookup局部变量表达式后完整AST equals原件；其余原字段/validator/方法无暗改。本结论是原源码保护，不能把 byte equality 当既有运行资格全部重签。

资源V3 loader尚未接线、完整0059诊断 source/registry/command writer/effect recovery/Worker/lineage仍是独立后继工作。停止Media旧loader v1/v2缺口在原报告明确，本轮未读取热Media或把新Domain.guard当实际prepare已成功。没有新immutable许可源、Owner/human授权或installation资格；没有使用已拒 intersection/subset补丁绕门。

新的真实pure算法标准/fixtures由Test所有者另准备；正常初始full catalog、missing/duplicate/order拒绝、audio/cover合法partial selection，以及 format各JSON类型/unknown/known v2/v3 均是后继实际检查要求，本评审不授其执行。原累计三次19失败限制和所有历史红/被拒patch保持，不能借新卡重置第四次。

## 工具与正式交接

4f7836/0读治理与卡，d20dbe/0读完整formal；1c2c99/0仅自身stdlib hash/AST/diff核。合并read输出曾截断，不冒充遗漏段全文；0dd5f7/0按固定copy补读domain尾和prepare前段。2380f0/0、7c3221/0读原actual source方法/有限graph/完整mapper，均自然终态，无候选执行。

过程根：`G:/开发测试/Codex/VideoCreatorImplementation/Review/BackendAffectedRecipeCorrectionIndependentReview`。InputBefore、InputSupplement、InputAfter、SourceFacts、独立ReconstructedChanges.diff与正式Handoff保存精确来源和原失败，report不修改作者或旧Review材料。

本轮产品/Pydantic/SQL/native/model/HTTP/网络/安装/收费/密钥读取与测试执行全部0；仅自身stdlib source/AST数据核对。所有源码读者在有限末核后释放，最后artifact writer自然终态另按实际工具结果确认。本阶段两个P2只源码关闭，没有新confirmed P1/P2；R1三OS真实作品多模态独验后连续完整R2仍未验收。
