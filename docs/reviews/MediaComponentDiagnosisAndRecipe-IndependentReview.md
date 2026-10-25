# Media48 诊断与四配方消费者独立源码审查

结论：SOURCE_REVIEW_FINAL_WITH_OPEN_FINDINGS。固定 Media48 的 9 个修改、4 个新增源及相干调用链已独立审完；有两个条件性 P2，分别归 Media 与 Backend。当前不支持整个诊断／四配方流程完成。MDG03 仅“同一 BundleService 的既有 v2 准备方法接入当前 caller”获得 SOURCE_STATIC 支持；MDG01、MDG02、MDG04 仍 OPEN。没有产品、Pydantic、SQL、FFmpeg、模型、provider 或收费运行，也没有新运行授权。

## 固定输入与核对边界

任务卡 G:/开发测试/Projects/VideoCreator/docs/task-board/MediaComponentDiagnosisAndRecipeIndependentReview.md，SHA 9b336c27df6e9c8958d9b476a443f6e36672c45952d52e16b3b775fcfe7fc985。工作区／仓库 AGENTS 实际身份分别 af69f90a45d8b3ed80bc9b5e2cc4243ac8e2cc6f53785aa28ae2d423f93a17ec、6de878f514b02788f8af5ba512f71c56bb053f6800d76cf19f3cdd955b7f6a0d。未修改规则、任务卡或候选。

Media 唯一停止根为 G:/开发测试/Codex/VideoCreatorImplementation/AgentMedia/ComponentDiagnosisAndRecipeProduction/；普通源码来自 SourceStage/SourceCopies，未取索引的热 path。正式输入身份如下。

| 输入 | 完整 SHA-256 |
|---|---|
| Handoff.md | 427405a99970334e25a21b4ed0facbf69e8819cd4a5eb309d6ba66351dae6448 |
| Handoff.json | 8b5c48e53ce71e7261ee4a2de3700be9f0c1b0b45dfc6ca9aab34d152c3b0494 |
| ActualInterfaces.md | 4c5a0c0e0451877373c398a739f048847aa3508dd950a99697ce46478f09403c |
| SourceStage/SourceIndex.json 与 SourceSnapshot.json | a7f27d6f44c1e9a1109545b835419cbdbdbd200f478b3405d7300d4bdb9dfff9 |
| SourceStage/Full.diff（72798B／1072 行） | aa64deead2d149b2e4d4eabda018efbecc24df5ccbe7dd318486af3287aebbff |
| Before.json（原44普通基线） | e13161cb1e95d0067570eef62be5c30533413fb25147f49b482acae69d282b41 |
| 唯一 Backend130 SourceStage/SourceIndex.json | 41b2f0e2650b10b97a7353a574e5f131164ae9a597d763435df11c5ab912c83d |

原44基线与完整48均逐文件核大小／SHA。13个差异文件全文与完整 diff 已读取；自有只读统一差异解析核原 hunk 内容、位置和计数，从原普通副本重建后与现普通源完整 UTF-8 字节一致：9改、4新、35不变，13重建无残差。这是源码身份／差异证据，不是执行候选或运行测试。未声称35不变文件及整个Backend130在本轮逐行重审；必要原链和冻结依赖才定向读取。

InputBefore.json 原121路径保持；五份 BackendInputSupplement 独立记录11个必要普通依赖。末 InputAfter.json 共132唯一路径，大小／SHA differences=[]，SHA 2e4fe26d992c0a7153bfc7eebcb399d6eb54249f698319087ce65557d73009f8。第五补充明确 current_final_evidence.py 是先按固定索引做有限协议定位、第一次独立文件 hash 在收口捕获，不伪称该新增项有更早文件实测 before。未读后继131、0065或热生产源。

## 两个新增问题

### MDCP-P01 — 文本补充错误访问资源 ref 的 MIME（P2／Media）

OPEN_SOURCE_STATIC_CONDITIONAL。实际普通 source 为 G:/开发测试/Codex/VideoCreatorImplementation/AgentMedia/ComponentDiagnosisAndRecipeProduction/SourceStage/SourceCopies/providers/component_diagnosis.py，17664B，SHA d82545388add21f5f1379103585253a11b1f12270ede91b3b8b1e5ebb873b3e0，driver129–148，特别142–144。text_sources 对非 feedback 的 completion 无条件先读 completion.ref.media_type。原 Backend130 domain/diagnostic_recovery.py17–20、37–39 的 qualified_resource.ref 为 DiagnosticMetadataRef，仅有 record_id/content_sha256/size，没有 media_type；该源8475B，SHA af1c2532538104597ebfc2cbbff887e90b24f044fe7824fd7d0ce2f0dae0b9c0。

最小触发：真实同Run v2 input 含一个已认证 qualified_resource completion，原方法覆盖和固定 text route／MODEL 通过，reader返回完整 bytes。driver 构造 text_sources 访问不存在属性，尚未到本次 Executor／text 请求。原固定130的资源分支仍503，因此当前没有实际到达或属性异常复现；这是补齐资源端口后仍会存在的消费接缝。

窄修须由原 Media 按实际三种 completion 分支消费经认证完整 bytes，MIME只来自真实 MaterialReceipt。不能伪加字段、删补充、只传locator／hash、放宽上传或绕权限／原Operation。完整固定早单 Finding-MDCP-P01.md 的 SHA b0a31ce0543fa47d452db1c21c2311615e52e4a79729929411f6f3a091982737，原件不改。

### MDCP-P02 — check证据 union 不能承载声明的资源补充（P2／Backend）

OPEN_SOURCE_STATIC_CONDITIONAL，共享类型归原 Backend；Media 是实际消费者。固定 Backend130 domain/component_diagnosis.py，15145B，SHA 669b09c7264cceb0260307f6c5a5aca94c3524fb683d19614262fbf7f65001c0，59 的 DiagnosticEvidenceRef 及106–115的 source_refs/expected_ref/observed_ref 未含 DiagnosticMetadataRef，原各 union 成员均不是此三字段 ref。Media _local75、82、110–114将每个 completion.ref 加入真实 ComponentDiagnosticCheckV1，120的 precision check 同样加入。真实 qualified_resource ref 因而无法进入该严格语法。

不能省略补充求绿：固定 application/component_diagnosis_service.py401–453，67661B，SHA a2747f788f03cb5d207685d7b56d400b6856fbb36814c1b91726dd916af2bd15，将completion纳 known，并在452–453要求每一原completion被真实checks消费。须由 Backend 明确且窄修严格资源证据表示及真实来源／current验证，Media仅消费正式新类型。不能任意dict、放宽extra或伪造RevisionRef／OperationRef。当前资源positive未ready，未执行Pydantic，不记运行失败。完整固定早单 Finding-MDCP-P02.md SHA abd1c59ceb76b11d3fe97f773dd058d2b8777e70d1c5d4b70f3963e7c383c308，原件不改。

## 实际调用链与有限支持

所有以下路径均相对于上述 Media 固定 SourceStage/SourceCopies；不是热生产文件。

- workflows/bundle_producer.py658–666把实际 diagnostic_source 传入原 continue_bundle；workflows/bundle_recovery.py467–478在读取旧ASR／修复／生成／最终整体验证之前消费该来源，实际assessment原样进入 _final_wait。workflows/component_diagnosis.py80–103核 CurrentDiagnosticSourceRead、同Run binding／当前fence；reuse_record找不到原记录即409，不重分析；analyse_changed_input仅缺原记录时追加；final_validation_after_analysis返回原整体验证路径，不另做第二次wholeverify。初始603在原现成candidate后prepare_initial，旧服务没diagnostic_ports则保持原分支。
- _completions16–33逐个调用原 read_diagnostic_completion，并拒绝非bytes／空／超2MiB，不以locator替正文。analyse36–64使用已安装同services对象、原注册intent、begin_step／prepare_operation／Executor；未知或pending仅409 reconcile，不换key重新收费；输出ref绑定真实原operation id、input、observation与结果SHA。原记录的后端真实性仍由实际端口负责，不由typed字段或Media签名自授。
- providers/component_diagnosis.py39–54仅选一个覆盖原完整checks／RULE SHA的注册method；129–194核真实route、permit、原Run/fence/secret边界。Text分支一份completion返回三个视角并明确局限，不能算三个独立agent／三个Operation。196–216 verifier只在原driver已有同值input＋lease／completion cache时重验完整checks/measurements；没有真实冷启动新lease认证上下文。全部completion body_hex进入原 result，不洗为单locator。
- MDG03当前caller获有限源码支持。workflows/current_engine_production.py33–43只在完整 v3-diagnostic资源分支选择 bundle.prepare_plan_repair_targets_v2，同时校 MethodType、__self__ 与原方法/self均为同一实际bundle、__func__为 BundleService.prepare_plan_repair_targets_v2；两个factory124／188实际传入该方法并bind_services一次。原非diagnostic分支返回original。固定Backend130的 BundleService249 → CurrentFinalEvidenceService27 → CurrentFinalEvidenceRecovery38 → PlanRepairService20 → AffectedRecipePlanService16继承链真实存在。v2准备方法16–90保原认证准备、manifest/index/source/route及末current检查。只关闭旧caller接线这一源码缺口，不授plan权限、资源安装或实际调用通过。
- providers/production_resources.py88–110在固定唯一 parse_production_recipe_resources 完整语法下读v3／diagnostic，逐原recipe producer与diagnostic implementation source核indexed文件SHA，模型/worker/runtime资源依旧核；v1/v2旧分支保留。workflows/production_drivers.py61–75还核实际运行producer两个源hash、真实配方输出变体和禁止audio／cover重生成镜头，不凭声明hash建立资格。
- workflows/recipe_production.py22–48检查原合法execution/proposal、parent、input、report及command全部字段；51–61从同原plan完整V3 body取有限recipe、actual targets和shots；64–82只从当前受控readset的逐shot原clip来源读取、独立核Asset/path/probe/hash/size，缺件503，不猜latest或旧initial Step。affected_production49–79在每个副作用前重新authorize同command；186–302沿原parent creative refs、旧masters、原权限、source steps及真实fenced registration工作；321–360沿原Worker output reservation／Operation／commit闭合，unknown不换command。

四配方的真实源码分支与局限：

| 配方 | 固定源码行为 | 尚未证明／缺口 |
|---|---|---|
| ambient-remix-v1 | 原三clip+narration真实FFmpeg裁切/scale/pad/concat、原声低音量混合、视频/混音/首帧封面；initial V3 caller真实给recipe_id | 部分镜头修复需要MDG02受控原clips；没有实际FFmpeg／质量运行 |
| visual-preserve-mix-v1 | _affected保原mixed_audio完整decoded evidence，拒mixed_audio输出，生成video及所准cover | 保留镜头仍依赖MDG02，不以静态代码证明像素／音轨相等 |
| audio-remix-preserved-clips-v1 | production_edit163→218–257读真实preserved video／clips、精确两outputs；FFmpeg映射4:v:0且-c:v copy，只重算真实narration＋clip音轨的AAC／WAV，原duration/probe校验 | 原clip／soundtrack controlled lineage缺MDG02；没有实际bitstream／offset／FFmpeg观察 |
| cover-from-preserved-video-v1 | _affected119–133仅cover输出，禁止regenerated_shot_ids，从实际preserved video首帧输出独立新cover | 无实际图像／真实权利/安装证据；不伪造其余masters |

## 原保护、缺口与证据等级

DiffAndProtectionFacts.json 独立核四份完整字节保护：providers/local_asr.py、providers/asr_resources.py、media/asr_worker.py、workflows/bundle_v03.py；原 AutonomousProductionFlow._admit 1240B与首次 BundleQualityEvidence构造670B原块相同。原源码不把Word估计当CTC／独立测量；bundle_producer保真实mixed clock→原ASR→原CTC／两authority测量→字幕／语义／RAG→真实rights→一次完整finalverify→publish。bundle_recovery保完整Ready bytes／原allocations／原Operation validation context，不改Ready report原ID字节，不重跑缺失推理，合法child仍依原authorization及fence。该判断是源码保护与调用顺序，不是现场兼容或质量证明。

MDG01 OPEN：单method／单原Operation的三个视角不满足独立导演、剪辑、声音成员归因。MDG02 OPEN：Backend130父来源仅四masters，没有受控完整clip/ambient lineage；保留clips的三类配方及音源诊断因而有准确503缺口，不能借日志字段／initial-Step／latest重建。MDG04 OPEN：原record read仍通过缓存lease／completion verifier，没有新ordinary lease、认证completion正文进入冷进程／新fence verifier的固定合同；不许为恢复cache重跑收费分析。SourceGap原件保持，CatalogCallerAddendum仅由上述独立caller核得到MDG03有限SOURCE支持。

原Media第一/第二静态import-order红、ThirdStatic与FinalStatic的不同输入时点完整保留；FinalStatic只48AST及13目标Ruff，不是全目录lint、测试或运行。原两个未修BLE001宽异常警告保持，outer自然0不洗历史stderr。184242/1是本角色错把 owned_sources 当 source_map 的定位错误；该输出及39ddcd、1afb13截断保留，通过定向必要读取补齐，不声称截断输出已全文。462991/1是本角色补充JSON容器展平错误，2d4daa/0明确132无空path，c5dcee/0完成132末核；不是源码漂移／产品失败，没有重跑目标。

完整制作流程、真实Windows/macOS/Linux安装包、真实Owner/API/MCP、资源资格、多模态作品、听审／精度、原R1后连续R2均无本轮独立通过证据。新后端BCF/DALI/0062/0065接口未被本固定消费者吸收，不借设计或未来补件证明现流程完成。后继应由原Media/Backend窄修两问题；真实资源/current/全部completion、未知受理、合法同input复用、新fence冷恢复和四配方需独立Test/Acceptance原授权另批。

过程根：G:/开发测试/Codex/VideoCreatorImplementation/Review/MediaComponentDiagnosisAndRecipeIndependentReview/。完整121原pins、五补充、132末核、完整diff/protection事实及两原finding均固定。所有源码读者已释放；本报告只有SOURCE_STATIC结论，不自授实施或运行。最后文档写入工具的实际自然终态由正式FinalHandoff和末次回复另行记录，不以文件存在代终态。
