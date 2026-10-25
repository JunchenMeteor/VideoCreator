# ADR0072 独立设计评审：真实本地制作与发行资格分离

裁定：DESIGN_SUPPORTED_FOR_ROLE_IMPLEMENTATION。本固定合同未确认新的 P1/P2 设计阻断。支持原 Backend 先实现真实本地 authority、同 Engine 首 Goal 装配和固定 local factory；支持原 Media 实现真实素材制作。CPSC-I01 是 P3 连接键澄清，在唯一 local plan grammar 与 Media 共同消费前应明确，不阻止上述独立工作。

这是设计与必要实际源码调用点的评审。新 LocalInstallationAuthority、RegistrationConfigLocalV1、local plan、local Flow、可变时间线 driver 及 qualified capture bridge 均未由本评审证明已实现或已运行。普通本地制作不要求独立 Test/Review/Acceptance 签发发行资格；显式 qualified 通道及独立安装/发行验收保持原门。本文不授权应用、产品执行、费用、安装、发布或验收。

## 固定范围与身份

当前任务卡 G:/开发测试/Projects/VideoCreator/docs/task-board/ConcreteProductionSourceContractIndependentReview.md，4768B，SHA-256 1db4fee2326ea43462871f777b3b18cfb62e4fcbb9a480b017380228109e21e6。末 ACTIVE 段生效；架构普通集内历史 Task.md 是2852B/10bc9c30919bfd64b43a0ebb9e7fd7ab444d81ce71cc448c7c21f067214c5521，单列历史，不替换当前卡。

唯一正式设计根为 G:/开发测试/Codex/VideoCreatorImplementation/Architect/ConcreteProductionSourceContract/。全文读取普通 Decision/0072.md 的187行：28206B，SHA-256 1c4fc5782213a364b1504bb9b9456ede231f7f1cdac8d780e309cb0722aceec3。普通正文、正式 Handoff/Delta/Interfaces/Impact/Errors/Terminal 与索引按各自身份保存。

| 输入 | SHA-256 |
| --- | --- |
| Handoff.md | a915349bcf1d13e5657911f026d79933394a6a2738e6679cb63550da7237e01f |
| Handoff.json | 5b5fad86431da12b5489a46eecce907f6b6ba7e96fb3d5c61bcba4c0fcc153c8 |
| Snapshot.json | 8d0ca7defa8d212050f6913766217dda1ecce123217be5a11d6d411af90e657e |
| InputPins.json | 33b3413d46519995ac2a7796d8042de84ae8f361e34e70e5ad11ed154c992c74 |
| OrdinaryIndex.json | dbcdacdca892ef4257a0141fbaa6481e049d3cf1c27f21c6b64c53a34218c179 |
| SourceAfter.json | 2df4d69748a7355e703e1c65e206398b680f9729b7c6a43a561b6244f9608af4 |
| Delta.md | 25efb6b8de980244422c1b86daaf27d62f471355962f1085c2222803ee0ebf1f |
| Interfaces.md | 55db041dd5f18d804cc66d13ea3a2595efd7469d9bdf603085dadfe4876d9070 |
| Impact.json | 2df07daf0162ac577165151a6571d26c3ef5851386da889fc569fba2498882ca |
| Errors.md | 6367284ecb42ec5c3b59a7b71bea39963a46e5babd3764b0d8f561559ac3b134 |
| TerminalReadback.json | 827e9e14cc34513740d9744797937616d21bddf23779df7ef7d3d3193d4e3db3 |

独立核53普通副本大小/SHA与索引一致；当前工作区/仓库 AGENTS、当前卡和11正式件组成初始67唯一输入。为核完整 API/MCP/Worker 原入口，仅按该停止 Backend SourceIndex 的 ordinary_copy 单列增加 main.py 与 startup_services.py 两件，来源是 Backend/CoverageProducerCompletion/ResumeStage/CheckpointSourceStage/SourceCopies，未读 source_path 或热生产源。两件分别23550B/482d87de04e9fe54fa2b4ced7a65110116a3964eb8007fbae2f8de3983bb9e39、6966B/143a8484c61474866b8bc6423cdf9d50313f213aaa07b2aea73d60c1cc056cc7，记录于 EntryInputSupplementBefore.json。

InputAfter.json 将原67和单列2件逐路径前后大小/SHA对比，69唯一路径 differences=[]，SHA-256 60fc86f8eb8671d55294fd1c30cb4f097cbf6a71e2648e9bac5722a72eb5b63e。未重新遍历环境、143后端全树或48 Native/Media全树。原架构 SourceAfter 只说明其 finalizer interval，不能推出作者整个阶段无漂移。ReadCoverage.json 明列55份普通文本的全文、必要段和仅身份范围；53大小/SHA一致不等于53件所有语义全部审过。

## 普通 authority 与 qualified 边界

ADR第26–58行保留真实 OS peer、PID/creation/SID、实例、host image/full map、原 held 对象、thread/epoch、Owner/current/lease/fence/CAS、rights 与 unknown 账本；删除的只是普通制作对独立发行签发的依赖。它没有允许由签名、DTO、任意 callback 或 copied object 获得执行身份。

实际调用点位于固定 Backend 普通副本：

- Sources.application.native_installation.py 第45–61行，旧 observe 因 not_ready/无 issuer 拒绝；第143–159行普通 connect 仍构造该旧 authority。新 concrete adapter 必须替换此显式普通装配，不能给旧 facts 填 qualified 或令显式 qualified 分支降级。旧 qualified connect 第197–221行仍单独消费 OwnedQualifiedAuthorityConnection、trust source 和 NativeQualifiedIssuer。
- Sources.infrastructure.held_authority.py 第188–227行，普通 v1 回复包含实际文件事实但 qualification 为 not_ready；第229–282行有原 peer/current、序列、deadline、original observation identity 与本地 epoch/member 检查。数据状态不是发行资格，实际原对象仍能成为普通本地 source。字段变成 qualified 不会补出原 source。
- Sources.application.production_admissions.py 第181–202行核原 evidence 文件分区与真实 current；第205–286行将外部 current 放在原短 writer 前，writer 内检查原同 thread/member/session/current。第239–265行只对真实 NativeInstallationAuthority+NativeQualifiedIssuer取得 qualified lease；新 local adapter 不能借 exact type 名称、假 issuer 或 copied facts 触发发行路径。
- Sources.application.native_qualified_issuer.py 第37–64、74–149行，原成员、same-thread writer lease、原 QualificationControl/native lease、same-connection local rows、expiry/floor 与 unknown close 仍有效。0072将该强链留给显式 qualified 工作，不应在实现普通路径时删除。

因此本地 adapter 可以采用现有 InstalledProductionEvidence/current_guard 的真实事实与锁序，具备具体接点；这里只支持设计。实现必须保存完整原连接/held source，而不是把 SHA/路径列表封成长期权限。每个 API/MCP/Worker 新进程重建本次真实连接；关闭、线程转交、禁用或实例变化不得复活旧对象。短 writer 不执行 RPC、重 hash、密码学或其他外部 I/O。

## 首 Goal 与原入口的完整连接位置

Sources.application.native_execution_observer.py 第33–59行 observe 是一次性的；第61–93行核真实 original member/observer/connection，并在 close 时失效。新 production_authority(original_observation) 必须消费已经保存的原 observation，不能为构造 adapter 再调用一次 observe，也不能只按相同字段认另一对象。

Sources.cli.native_owner_setup.py 第72–115行是原 preparation→真人 modal/TTY确认→同 OwnerSetupService.execute→close 路径。Sources.application.owner_setup_service.py 第463–492行在真实 observe 后 registration.install、保存原步骤再继续；第495–499行同一次服务实例保存在 _services，第528–557行 _configure_execution 当前要求 authority 后才使用同 Store.current/projection、register_identity、bind_native/configure_authorization。0072第60–64行指定的安装点准确：以原 observation 构造 adapter/session guard并绑定同一个 _services.admissions，发生在原 _configure_execution 前。不能另建 Engine/admissions、从持久 receipt 伪造当前 source，或借失败清除原已接受 Goal。

第432–441行原 immutable result replay 与第685–704行原 close 失效须保持。完成首次 setup 后仍需实际 API/MCP/Worker 自己取得当前 source，首 Goal 的已保存结果不是以后线程/进程的活 authority。

单列原 main.py 全368行与 startup_services.py 全129行表明：main 第210–217行将同 Engine、runtime.bundle、registered_runtime 交 Worker；第298–304行将同 Engine/Bundle交 MCP；第313–345行将同 Engine/Bundle 和同 installed copy_inputs 交 HTTP create_app。startup_services 第65–90行校验 Bundle.engine is engine、Worker runtime三对象、真实返回 NativeOwnerServices、同 role/instance、同 admissions、same source且 execution-only 不带管理 Registry/management；第34–53及94–103行在原进程服务真正结束前保留原对象。新普通 adapter 有真实共引擎装配点，不需要增加另一管理 server或收费入口。这里是原源码连接证据，不是 HTTP/MCP wire、后台断线或正常 shutdown 实测。

## 本地 typed registration、输入与费用

0072第68–86行的新 RegistrationConfigLocalV1 和 registered-local-material-resources-v1 是独立版本，保旧 v1/v2/v3、selected code/runtime source与 decoder/font 路径/SHA/current保护。仅 renderer 提供 Asset ID/Goal/资料，不能提供原 input authority、master IDs、native证明、FFmpeg参数或可执行模块。旧 ProductionRightsDeclaration 的 user_asserted 也不等于许可已核；仍须同 Run可读 Asset、真实 decode/MIME/probe、原 rights plan/usage/current 与输出权限。

固定 Sources.domain.registered_production.py 第101–119行只接四个 distinct 同 Run master。Media Sources.providers.production_common.py 第18–49、51–71行有真实 reservations、permit和安装检查：new outputs不得指向既有普通 input ID，不因成本0省略 Operation。新本地 route必须真的 installed/owned_local、无 credential/无外部调用、cost0，并保原 OperationIntent/input hash、Step、output refs、成功 Observation/settled/fence。不能借 profile 名称给 Piper/Wan/text route签无限预算或把 unknown改成功。BYOK文稿/完全模型模式另走原权限和成本账本。

CPSC-I01/P3/OPEN_DESIGN_CLARIFICATION：0072第90–92行 input_bindings 声明固定七字段，却由 shots/audio_tracks 用 input_binding_id 连接，没有 binding_id 字段或唯一键定义。同 Asset用于 visual 与 background_audio 时，现合同不能唯一说明目标记录。需要 Architecture明确连接键、唯一性、重复/悬空/角色不符的拒绝语义，Backend维护sole grammar、Media消费同一规则。不是实际运行失败，也不支持任意禁止合法复用；它不阻止 authority/首 Goal/factory先行实施。固定独立 Finding-CPSC-I01.md，2081B/SHA37c52afbe4e92b29a80c83826da825f7f6f67ec3a452497cd79fcddeaa8044e7。

## 真正 local Flow、四 masters 与 Bundle

现有 Media Sources.workflows.production_drivers.py 全83行仍只有真实 Piper narration、Wan picture、旧/affected FFmpeg edit。current_engine_production.py 第89及160行硬连接该原 factory；production_edit.py 第30–105行是三个素材、25fps、旧720p构图及受控混音。它们证明旧功能，不能因新 ADR 或实验 local_render 成为完整已有素材制作。

新 create_local_material_production_drivers 必须由 Backend 固定分派，并由 Media提供新的 LocalMaterialEditDriver和真实 local Flow。图片/视频规范化成新的 derived outputs、保原素材 lineage；上传配音完整 decode 后生成新 PCM WAV，合成最终 video/mix/cover，独立 narration保留。镜头数、范围、目标比例/尺寸与帧映射来自受控 typed timeline，不能硬编码三色块/三片/10秒，也不能把音频复制两份充作 mix。无旁白/纯音频需要原 outputs的明确适用版本，不能往现有四 master硬门填假文件或悄悄删除要求；本轮首本地完整作品仍需实际上传配音与四份 master。

autonomous_production.py 第333–370行 _generated 是可复用的真实 begin_step→output allocation→Operation→succeeded Observation→settled fenced commit；第398–442行真正提交四 master的 Step与quality/source事实。new profile必须将 request/plan/input SHA/resources/route/timeline绑定到原 step/input/dedupe，恢复读原 Operation/Step，不能重置任务名或在 unknown 后再输出收费重试。production_common原 existing-output冲突应进入原 reconciliation，而不是覆盖旧文件。

Backend media_registration.py 第261–446行 _current_services/_remember/_checked_upstream_result/_invoke_current 保 same factory/Engine/member、same Run/fence、lease已释放的 waiting与有真实 ledger的 reconciliation，并只在 masters_ready 进入后续 Bundle。第646–846行原 Worker claim/renew/cancel、presence、reconcile、wait、原资源释放/drain提供真正 caller。新 local profile须有显式 registration/Flow/Worker资源等待分派；只替第三镜头或输入body不能完成此链，blocked上游不得拿旧 masters继续。

关键未实现边界：media_registration.py 第120–186行旧 constructor会全局 load ASR 与 Bundle producer；Bundle factory 第636–644行也立即 load ASR。0072允许本地配置 ASR字段全部null以保 API/编辑准备可启动，必须在新版本实际分派和延迟构造中实现。不能仅将旧 config字段变nullable，仍调用旧 eager loader，然后称无 ASR可制作。无 ASR/必要对齐时应保真实阶段文件与 resource请求，完整 Production/Bundle仍不成功。

bundle_producer.py 全670行已核。第188–214行旧六种 Creative refs与真实 source script有硬门，第216–325行 finalmix 实际 ASR、原音轨坐标、Alignment与字幕，第326–386行真实 storyboard/RAG/quality，第451–541行 rights、assembly checkpoint、真实 CTC/独立测量与两authority，第598–627行 sole verifier/publish。0072第114行明确要求 Backend sole local plan/version mapping与Media消费者同步新分支；没有模型产物时保存真实 local planner的方法与限制，不造假的 insight/script/quality六版本来骗旧门。

实际输入音频 ASR派生稿必须先形成独立源稿并准入，最终mix ASR是另一输出，CTC/参考测量又是另一责任；supplied text不能写入 actual_transcript。真实 SRT/VTT、JSON/JSONL关联/RAG、严格 context、N/P95/null与两authority、whole verifier和immutable READY/publish仍保留。未有本片合法reference与显式策略时不得复制通用精度。导出仍用原固定 Bundle/ref/grant/content/Range及 rights，不以 renderer/origin ID或已下载副本授新本机执行权。

## 延后的 qualified bridge 与责任划分

Native Sources.src.qualification_handler_capture.rs 全126行核实，registered reader保存的是同 authenticated实际child/process/source Arc、原 raw frames、seq/method/time及有界记录；第105–124行读原 capture并验证thread/member/Registry/process/current与原 token字节。0072第130–142行提出的 held-resource-capture-reader-v1仅是后继强 object/source桥：需要在同原reader thread上读取已有 exchange，通过有界队列，不能 reobserve、新mint、JSON stringify重编码或以回传dict替Python原对象 membership。source_terminal/disable/foreign/limit不得成为成功；原child/Job清理未终态时保持真实引用与unknown。

这一新强bridge与首 qualified bootstrap、issuer/source/H+C、真实安装资格仍NOT_IMPLEMENTED；不是普通 local制作的隐含前置。原 qualification_execution_capture.py 第66–83行的 hold_qualification_attempt_source 可覆盖普通真实 Runtime/AttemptControl，并不自动签发资格；其第111–171行 begin_capture才要求实际qualified证明。不能把普通hold与独立qualification suite等同，也不能删除原捕获与费用事实来实现“解耦”。

可交实施的最小责任是：Backend实现具体 ordinary adapter、原Owner注入、唯一local registration/plan及版本映射、原Current/Worker/source保护；Media实现固定local factory/Flow/可变timeline及Bundle新version真实消费；Integration补正常host启动/原当前连接与资源完整性，强qualified capture bridge另阶段；Frontend只提供Goal/资料/素材权限/计划编辑/进度导出等五步，公开DTO由Backend/Integration生成，不让普通用户签发行报告；Test在独立另授运行边界核真实路径，Review/Acceptance保持职责。当前CPSC-I01归Architecture后继澄清，不由Review造第二套grammar。

## 运行缺口与原记录

本轮0 candidate/product/import/Python/Pydantic/SQL/native/network/model/fee/install运行，未改任何实现/设计/测试/阈值/账本；新source factory和typed schemas未由本文产生。旧19累计耗尽、三binding、31/105 NOT_READY及费用原记录不重开、不洗绿。原所有SOURCE/DESIGN closure只保其原范围，不迁移成0072正常Owner/安装或制作通过。

实际后继需要独立准入且检查：无发行签发时真实普通Owner首Goal和同instance API/MCP；copied/expired/closed/thread转交source拒绝；真实素材权限/完整decode/selected routes费用0；不同镜头数与1080p两比例、真实独立四master/混音；输入ASR稿与finalmix转写的分别来源；实际字幕/RAG/context/precision；资源缺失保文件与等待、不READY；原Step/Operation unknown恢复和撤销/新fence；客户端断线时同Worker继续与合法导出。完全模型自主创作、至少三真实新镜头、所有目标OS/架构安装、商业分发与完整R1后连续R2另验收。0072的“阶段”不是ETA、实际通关或自动新运行额度。

阅读错误按原件保留：初始合并输出截断，仅对确实缺的编号段补读；a5f84f中未呈现的Spec01关键词段不称已读。自有8ee395 metadata工具自然exit0，但 -match路径正则产生非终止\N错误；仅ReadCoverage分类受影响，原ReadCoverage-InitialRegexError.json保留，04892e改用字面EndsWith及准确文件名前缀。69输入末核独立完成且 differences=[]，没有重跑产品或为元数据重hash全环境。外部历史Errors.md的定位/metadata错误仍是原治理事实，不冒产品失败。

完整封存由自有 Handoff/FinalHandoff/FinalizerTerminal给出当前实际已返回工具及最后调用返回边界；不从文件存在、作者AST/标签、角色running或timeout推工具终态。所有本轮读取均在自然返回后关闭，末工具实际返回再向Root报告TRUEFINAL及no live/all reader release。
