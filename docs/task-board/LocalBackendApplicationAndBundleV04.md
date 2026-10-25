# LocalBackendApplicationAndBundleV04

ACTIVE，唯一原 backend_instance。只写仓库 `services/engine/src/video_creator/` 的顶层入口及 `api/domain/application/infrastructure/integrations/cli/`、`services/engine/migrations/` 和自身 `Backend/LocalBackendApplicationAndBundleV04/` 过程；不改 Media/Frontend/Integration/Test/Review/Acceptance 文件或生成依赖/SDK。目标是把已停止 Backend134 经当前工作树三向核对真正应用到产品源码，并实现 ADR0075 本地0.4适用作品包/宿主入口；不得再次只交影子源。

固定输入：Backend `LocalPlanBackendCompletion/SourceStage/SourceIndexLf.json` SHA-256 `0c662eecb4727586d84e102e527481c99fdb4cc818116ad551b052beffc849ef`、`FullVersusApplied131.diff` SHA-256 `a042bf2ddb74f052136dd50f85b5f801a5b8827a412c7a34d73de12d52c76b5c`、Handoff SHA-256 `ab2004a1b3f601ce4d356baf1213863a5e33430d80eeef3b14150b6f92277fc5`；Media55 index SHA-256 `95dc15020b56965c169b0c108d519290e1743115480e288164f3d1c86c6b68c1` 仅接口消费，不写其源码；ADR0075 SHA-256 `776a1bb058bc79d9beee04aa9da129219e786c33707a01732a1c9b942a071091`、独立设计报告 SHA-256 `54b550e100b4ed75e496b7a6c65ecba66433ab21fa915464cd60526075ef7061`；独立源码报告 SHA-256 `22a4e9b0553e90a891ed0d070635070d543d83c326394c6f10e3a54de8b2b55b`。原LMF-P01归Media修，Backend不得换裸executor；LOMD两项仅源码关闭。

第一实际里程碑：检查当前Repo Backend131每件哈希/既有未提交改动与134完整停止源，按白名单逐件三向合并，保旧qualified分支、权限/账本/恢复和现有用户改动；不得强覆盖冲突。把无冲突Backend实现真正写入当前产品目录，记录文件数、diff/变更SHA、AST/Ruff及可跑的原测试命令/exit。若某单文件冲突只停该文件并报告，不因此把整个工作回退为文档。

接着按0075实现 Backend sole 0.4 DTO/schema/strict dispatch、真实原request+已批准plan算 `LocalMasterSelectionV1`、V2 upstream/blocker journal、sameRun local host/首次与恢复来源、Bundle prepare/verify/附件/关系/适用输出、真实current/fence/Operation settled/rights/两authority/原子READY，保原0.2/0.3六Creative/四master/八输出字节行为。no-speech requested字幕须核实际两份零cue SRT/VTT Material/解析/MIME/hash与output绑定；V03报告核真实typed来源，不只ID/hash。Media负责生成真实素材/映射/转写；Backend只消费其明确接口，缺件给具名等待或拒绝而不造假/长期503作终局。API/MCP同Engine调用入口按可用接口接通；缺资源暂WAITING不冒成功。

每个可运行增量留下真实命令/exit、动态输入身份、失败原红及回归范围。原 Pydantic19/三败限制不得换名/换壳补第四次；该门阻断时继续独立可验证的纯模块/静态和后续真实新变更合理测试，并明确未跑。费用、凭证、生产部署、公开发布均不在本卡。与并行Media/Integration只按停止文件或明确定义接口交接；最终给真实仓库 diff、已接/未接明细、Impact/回滚与自然终态，不能自评独验 R1/R2。
