# LocalMaterialFlowSourceIndependentReview

ACTIVE，唯一原 integration_review。只读实现与候选；仅可写 `docs/reviews/` 和自身 `Review/LocalMaterialFlowSourceIndependentReview/` 过程证据，不写/应用源码、测试、架构合同或任务卡。当前槽位由原 Backend 134 源自然终态释放。

固定输入：Media `AgentMedia/LocalMaterialFlowAndBundleCompletion/SourceIndex.json` SHA-256 `95dc15020b56965c169b0c108d519290e1743115480e288164f3d1c86c6b68c1`、`CompleteSourceDiff.patch` SHA-256 `790ceb5512f2020d348b8899192ffbed43e9a4f0bc4442e2a2f0827fdb56ceb4`、Handoff SHA-256 `ac7922a6ef3f36525dd2c0bc3027c01cafce3936aa7a59038d60a7f84451b3f9`；Backend `LocalPlanBackendCompletion/SourceStage/SourceIndexLf.json` SHA-256 `0c662eecb4727586d84e102e527481c99fdb4cc818116ad551b052beffc849ef`、`FullVersusApplied131.diff` SHA-256 `a042bf2ddb74f052136dd50f85b5f801a5b8827a412c7a34d73de12d52c76b5c`、Handoff SHA-256 `ab2004a1b3f601ce4d356baf1213863a5e33430d80eeef3b14150b6f92277fc5`。原报告 `docs/reviews/LocalOwnedMaterialDriversIndependentReview.md` 的 LOMD-P01/P02 与 `docs/reviews/LocalMaterialPlanTopLevelIndependentReview.md` 的 LMPT-P01/P02 不由作者自关。

任务：有限但真实的独立源码评审。先核精确哈希/完整差异/独立白名单，再追数据与权限流：sole 11 字段/原请求与Goal及script和input-ASR来源、human/policy授权与同连接前后稳定性、Step Operation/登记、视频/音频/静图解码与gain、四母版/ASR/quality/Bundle的真实接缝、恢复和错误/回滚。用源码行证据判断 LOMD-P01/P02 修正是否成立；标明 Backend/Media ABI 是否可消费，以及哪些仍因 LMPT-P01/P02 合同未定、资源/生产者/运行未测而不得应用。严格区分静态支持、独立运行、成片/三系统验收；不得以 AST/Ruff 或源索引替代产品验证。

输出简明正式报告到 `docs/reviews/`，每项发现给优先级、准确路径/行与触发条件；Impact/Handoff记录精确输入、原命令/退出码、未测范围、交回角色及自然终态。未获得额外授权不得调用模型付费、改生产、发布或部署。尽快给可执行修复意见，勿扩大成整库漫游。
