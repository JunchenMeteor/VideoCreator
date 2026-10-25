# A0架构与Gate0接口候选

状态：候选设计v0.1，2026-10-07。依赖、接口实现、框架恢复和安装均待I0/T0及媒体同用例证据；本文件不冻结未测事实。

## 运行和权威边界

模块化单体引擎加一个独立Worker。桌面壳启动受控engine/Worker，React通过受认证loopback连接；Linux由原生服务或可选容器运行同一引擎，静态工作台经浏览器访问。R1不引入Redis/Kafka/微服务集群。桌面退出后若要继续，必须有真实存活的托盘/服务进程。

SQLite业务账本记录领域版本、Step、ProviderOperation、预算和Outbox；独立Flow状态库只持有引用及少量状态。磁盘Objects以哈希标识、暂存校验后提交；DataDir由实例配置，数据库不放网络盘。CrewAI聊天和Flow快照都不是资产、权限或收费执行事实。官方control-plane是R2独立可选运行组件，不进入本地启动依赖。

依赖方向：API/MCP → application受理/权限/账本 → workflows创作与协调 → application受控Operation入口 → providers/media实际工具 → application验证资产/Step/Bundle → Outbox事件。基础领域与公开接口由后端维护；Agent/媒体不得从框架工具直接绕过受理入口收费或任意访问文件。

## 八组公开契约

后端在domain/application/api维护Pydantic及OpenAPI唯一源；架构批准设计，集成从源生成packages/contracts与api-client。下面字段是必要语义候选，具体名称、约束和导出清单待后端实现/测试后冻结；不新增第二套手写TS类型。

| 契约组 | 必要输入/输出与消费者 |
| --- | --- |
| Production | Request固定goal、受控inputs、可选source_bindings/brief/insight、解析后的policy/automation/outputs/delivery及请求哈希；Accepted含instance/project/production/run/request_revision ID及状态/事件入口。UI/HTTP/MCP共用application命令 |
| Revision/Review | Insight/Brief/Script/Storyboard/角色/计划固定版本；ReviewDecision有target revision、approve/revise/reject、主体；Feedback保留原意见/约束及新计划引用。旧版本冲突409，意见不等于扩大权限 |
| Task/Plan | TaskContext含run/production/step_key、固定输入/来源/工作流/策略引用；CreativePlan/DelegatedTask含角色、依赖、输入/输出Schema、能力路线和限次预算。剩余预算快照仅供建议，执行时必须重验 |
| Capability/Route | 能力名、支持规格、数据目的地、已配置凭证引用、成本规则及可用/验证状态；RouteDecision记录候选允许路线、选择及回退理由。可用能力不能仅凭Provider存在判定 |
| Operation | Intent含稳定去重键、输入哈希、Step/路线、预留/成本状态；Observation为pending/succeeded/failed/unknown、external_id、真实结果、usage/cost证据。未知不等于失败，也不等于0费用 |
| Asset/Media | AssetCandidate为受控暂存引用、规格/哈希/大小/来源/权利；Timeline有画布、轨道、固定资产版本、入出点、混音/字幕；Alignment/Quality分实际证据与模型判断。无任意shell或外部绝对路径 |
| Bundle/Semantic | Manifest和BundleRef固定版本/哈希/outputs；源稿与实际转写分别保存；SemanticSegment/RAG chunk含来源namespace/版本及实际音视频定位。requested outputs核验齐备才成功，索引状态独立 |
| Event/Error | EventEnvelope含event_id、单调sequence、run/production/step/实体版本及真实状态；错误code/message/retryability/request_id。SSE游标补读，Outbox至少一次投递，消费者按event_id去重 |

HTTP前缀/api/v1；变更Idempotency-Key，编辑revision/If-Match。MCP一次production_create立即返回引用，连接结束不取消业务。最小只有goal/inputs，默认配置必须已授权；缺主旨/风格/分镜由模型生成，缺必要权限/能力/预算才阻断。

## 受控服务接缝

| 后端提供的接口 | Agent/媒体可做的事 | 后端必须核验 |
| --- | --- | --- |
| Production/Revision服务 | 读取固定资料、提出洞察/剧本/分镜/计划及反馈影响范围 | 主体/项目权限、来源事实、版本冲突及保留约束 |
| CapabilityRegistry | 查询授权能力，提出ModelRouteDecision | 实际配置、数据目的地及允许回退边界 |
| OperationService | 请求执行、查询、取消/核实已有Operation | 稳定去重、租约/fencing、预算/预留、外发权限、收费意图持久化 |
| AssetService | 返回受控暂存结果，申请登记及复用已有资产 | 地址/路径边界、大小/类型、哈希、真实解码、来源/许可 |
| Media/Bundle服务 | 提交Timeline、对齐及审片报告，申请Render和包构建 | 时间坐标/范围、轨道关系、实际文件与全部outputs、原子提交 |
| Review/Event服务 | 发布需要审核的产物引用，读取已经受理的决策 | 明确人工批准或预授权政策、决策幂等、不能用模型替人批准 |

Provider驱动由Agent/媒体实现，网络提交仅由已受理OperationExecutor调用；它取得受限执行上下文和凭证句柄，不自行开户、扩预算、改账本或把临时URL登记为成片。RenderBackend接收已校验计划和参数数组，后期Agent决定剪辑方案，实际进程由执行器管理。

## 状态与恢复候选

保留规格状态：queued、running、waiting_user、waiting_provider、succeeded、failed、cancel_requested、cancelled、needs_reconciliation。暂停新步骤通过独立调度控制标志表示，已受理上游状态单独保留；不因UI暂停伪称供应商停止。

queued经有效租约进入running；等待审核→waiting_user，异步上游→waiting_provider，不明受理→needs_reconciliation。决策/查询结果受理后重新排队；取消先cancel_requested，停止后续调度与受控本机进程，上游取消结果/费用仍须记录。succeeded只在全部请求交付核验并提交后成立；failed保留诊断和可恢复操作。

收费顺序：持久化Intent与稳定键 → 执行允许的提交 → 记录external_id → 查询/校验结果 → 暂存媒体并独立检查 → Asset/Step/领域事件短事务提交 → 推进Flow。网络/FFmpeg不放数据库事务。租约过期禁止旧Worker提交。

两库不能原子提交；恢复先读业务Step/Operation及暂存文件，再修复Flow推进。文件已产出未入库、Step已提交未存Flow、上游已接收但ID未落库分别注入崩溃。没有查询或供应商幂等证据的未知请求不能再次收费提交。

反馈产生新计划/输入版本及修订Run，继承同Production消耗/预留与最多2轮默认修订；不改旧Flow伪装版本。局部重做只使相关依赖失效，其他资产哈希和Provider调用数保持。

## 数据与时间

全部领域时间整数微秒、半开区间；最终编码按帧量化，保留原始timebase证据。视频时间线、旁白/混音及源素材坐标显式映射。计划源稿不能当实际转写，生成提示不能当最终画面描述。默认包是可移植JSON/JSONL和真实媒体，embedding/向量数据库不为必需。

媒体Range/ETag和短期授权入口服务固定版本。BundleRef的instance/bundle/revision/哈希不是访问密钥；授权到期/撤销实时检查。纯引用实例离线不可取片，完整导出副本由调用方持有。Portal保持独立事实审批、索引选择和投放决策。

## 冻结待办

2026-10-08的架构续跑裁决见0002—0005 ADR：范围和证据规则已获架构批准，技术栈及Gate0仍未冻结。A1时的资源缺口保留历史；后续I3/AV0已实际运行带媒体资源的Windows内部API/CLI候选，不等于Tauri/安装器或干净系统成功。AV0两次CTRL_BREAK exit3保持失败，I4只纠正过程脚本。MSVC/UAC、桌面IPC/成包与macOS/Linux仍按具体证据保留缺口，不以SDK/Rust存在或开发代理HTTP200替代App安装。

T2独立B2机制57绿和W1原31绿4红保持历史；后续W3/T3局部机制修复已绿，RV1/T4新增完整Crew解析接缝反证仍需原owner免费修复，不能把局部绿升格为真实自主协作。LangGraph真实经理委派和成果消费、反馈跨进程免费恢复有局部证据；unattended失败，不能据此选定整栈或虚报成片。最终生产只保留一套编排，历史两框架实验与旧任务版本仍可追溯。生命周期A2的免费准入不调整ADR0003原三轮或收费限制。

0005批准serve默认关闭的--control-stdin私有固定帧接缝；EOF只通道失联，明确指令只停当前API，不取消Run/Worker或改未知费用。固定stderr api_stopped/API-scope marker须实际loop/lifespan/listener清理完成，且与真实退出状态分开检查。后端B4唯一实现，集成可信host/新包消费，测试/评审/验收独立；当前正常停止尚未实现通过。

用户已授权DeepSeek/Kimi共用CNY20实验，唯一实例/账本与凭证治理见AGENTS；不读取/输出/复制.ssh内容。官方路线必须通过commercial/official-provider-admission.md，私人订阅/API权益不当成商业官方资源。项目和媒体长存安装实例，官方Gateway仅处理授权执行必需的临时数据，TTL/删除/已受理结果取回窗口在准入前明确。未配置生成API、跨OS、商户/平台资质及分发许可继续保留缺口。
## 首次本地 App 的同子进程实例初始化

ADR0042固定新的私有indexed initialize_and_bind入口，先用原held OS peer/data/host来源初始化一次原Engine并读实际SQLite instance_id，再由同原child接受原六字段record和两个instance-bound locators，复用同Engine进入ADR0038/0039首次真实Goal流程。原后台唯一identity模型、安装资格、人审与制作授权相互独立；stdio/ID/locator不是authority。前端四命令和五步可独立source接入，没有新增instance/路径/确认参数。副作用包括原schema升级一致性备份，未知初始化保实际数据、不盲重开/造ID/重发Goal。仅架构设计准入，peer/原process/实际迁移/安装资格/setup-aware恢复及三OS运行尚未验证。

## 真实安装资格注入

ADR0043固定唯一qualified私有wire v2/同原Engine和held peer的具体issuer，保旧v1仅facts-only；原Daily装配不另造。真实完整资源测验、许可/构建/ABI和独立接受报告形成离线资格pack，发布/本机受保护verifier来源各自验证，免产品账号。Owner接纳镜像、JSON、SHA或编译0不能qualify；current撤销/期限/升级floor/原对象与短writer本地hook都必核。现有源仅有portNone且v1永远not_ready，producer/wire/实际资格suite与三个平台尚未实现或运行。

## 开发安装资格宿主

ADR0077批准一条显式、非生产的本地安装资格路径，使native宿主尚未编译的开发检出也能跑通local-v1本地素材制作到0.4作品包。边界：`ProductionAdmissions`的`_identity`/`_installation`/`_guard`、`register_execution_identity`前置、`install_startup_services`的type校验、native路径及`serve`/`worker`/`mcp-stdio`入口一律原样；dev对象只由`cli/development_host.py`的`serve-dev`/`worker-dev`在"CLI注册文件参数+`VIDEO_CREATOR_DEVELOPMENT_INSTALLATION`等于实例id+非frozen产物"三重条件下构造，且必须复用`NativeOwnerServices`（其类型硬校验不放宽）。证据由真实磁盘哈希与真实时钟得出，但来源是checkout而非受保护安装，不构成安装、发布或Gate0/R1证据。`/health`以`X-VideoCreator-Installation: local-development`响应头标出，`InstanceHealth.mode`、OpenAPI与`packages/contracts`字节不变。第一版仅human(interactive)模式，不支持v2/v3、ASR与unattended；dev身份以Owner binding有效期加7天上限自我终止，退役以Rust native宿主可编译并具备真实安装记录与资格为前提。零cue字幕/转写不实现：无声作品的`subtitles`/`actual_transcript`按2026-10-25统筹裁定具名422拒绝，不得伪造空字幕或无语音证据。2026-10-25负例实测修订（无Owner时实测码、三种漂移码分工、执行顺序、零cue裁定）见ADR0077 §0.2/§6.1。

## 开发宿主首次 Owner 自动初始化

ADR0079按用户明确选择，允许开发模式在**没有** Owner binding 的首启实例上自动完成一次初始化；正式产品仍必须真人在真实 TTY 确认。唯一接缝是`OwnerBootstrapStore.change()`新增的第三个、精确类型的来源`DevelopmentOwnerInitializationSource`：它只能由`cli/development_host.py`以模块私有`_FACTORY`+保留表构造，并在同一进程内绑定真实`DevelopmentInstallationAuthority`、dev注册文件实算SHA、注册声明的`local-user`项目与OS身份；布尔、字典、字符串、JSON、argv或环境变量都不能冒充。只在`action='initialize'`、实例无任何既有binding、dev三重条件成立、注册SHA与本次实际使用一致、`owner_subject='local-user'`、项目真实归其所有、且Owner有效期落在`now < t <= now+7d`内时才写入。审计是一份不可静默的`Control/DevelopmentOwnerInitialization.json`（时间、实例、owner、项目、到期、注册SHA、OS主体、三个dev参数原文、调用栈来源模块），其SHA256在同一事务写入metadata；它与`owner_setup_journals`无关，不写setup行、不占唯一pending、不可由应用删除，人工TTY renew可覆盖来源并保留文件。`confirm_local_action`的TTY语义、生产`serve`/`worker`/`mcp-stdio`入口、迁移与`packages/contracts`均零变化；自动初始化不renew、不revoke、不隐式建项目，到期后只能真人TTY处理。退役以Tauri桌面弹窗可提供真人确认为前提，届时恢复ADR0077的"无Owner即拒"并删除本接缝。实现已于`292b615`落地（独立评审`docs/reviews/RV-LocalChainRealRunFixes.md`）：自动初始化由显式`--development-auto-owner-init`开关控制，未传时行为仍与ADR0077逐字一致；dev装配在`assemble_owner_services`之前用产品`ProductionAuthorizationControl.initialize_new()`补一次空首启floor（仅当floor不存在、四张授权表全空、Owner来源为dev且带该flag；非空一律`development_control_state_denied`503），否则dev实例会因缺`Control/ProductionAuthorizationControl.json`在`production_control_unconfigured`503卡死。这两项超出冻结正文，已由ADR0079 §13追认并冻结边界：审计必须先于floor创建、floor创建失败不得留下"已创建"审计（评审P2，修复中）；`ManagementPrincipal.authentication_source`第三值使生产可读到dev来源binding，经核对不构成能力绕过，但需后继收口（ADR0079 §13.3）。

## 本地0.4语音证据最小集合

ADR0080裁定：`utterance_verified`不要求`precision.measured`，也不要求CTC，它只固定`units=utterance`；真正决定是否要独立测量的是0.3的`alignment_evidence_policy`——`qualified_method_runtime_v1`允许`precision=not_measured`（N/P95为null）但必须集齐已准入policy/qualification/benchmark与每片`WorkAlignmentValidationReport`，`strict_reference_v1`才强制每片独立reference与复算。本地语音必须用`AlignmentRevisionV03`：用旧`AlignmentRevision`会落到`_verify_strict_precision`的"必须measured"硬门。R1仍要求注册CTC，理由不是它测精度（它自报`not_measured`），而是ADR0075 §3已冻结"原注册CTC alignment必需"且它是当前唯一有注册执行身份的对齐方法；faster-whisper的分段/词级时间戳只作转写单位来源并如实标注`whisper_word_estimate_not_forced_alignment`，单独不足以发布。字幕不额外要求CTC或measured，只受alignment门与精确序列化字节约束。当前真正的总阻断是evidence policy/qualification准入缺失（`evidence_registry.resolve`无policy即`alignment_required`409，`install`需`EvidenceAdminCapability`），在准入前whisper与CTC都发布不了。详见ADR0080 §2最小证据集合与§6三角色接口。

## 产品内授权通道

ADR0081把"终端TTY逐字确认"换成产品内弹窗授权：无Owner binding时引擎**允许监听**但只暴露`/health`与`/api/v1/authorization/*`，其余一律`403 owner_authorization_required`；授权成功后**必须重启**进入正常装配，不做同进程解锁——三条硬理由：产品进程没有installation authority，有了binding也构造不出执行身份（`production_authorization_unconfigured`403）；每进程只能装配一次`OwnerServices`（第二次被`local_copy_configuration_conflict`拒）；`assemble_owner_services`是trusted startup-only，不能在请求线程里运行。确认凭据四项齐全才生效：安装会话token、启动器注入且API永不回显的授权会话secret（R1用URL fragment，桌面壳用preload）、一次性nonce、范围哈希；Origin/Host/`Sec-Fetch-Site`沿用既有白名单，授权路由不进CORS。审计先于binding写入：`Control/ProductAuthorization.json`+同事务metadata摘要，写失败即拒绝，杜绝"点了同意但无审计"。P0覆盖首次Owner初始化与renew/revoke；policy/预算/daily需独立的management进程装配（单装配限制），另立卡；execution registration、资格/证据准入与发布授权永久不走本通道。TTY路径与native setup通道保留为headless/兜底，dev自动初始化保留但默认关且与本通道互斥；身份来源如实记第四个`authentication_source='product_authorization'`。该通道不新增表/迁移、不放宽任何类型门，新增的只是知情同意与审计。详见ADR0081 §2/§4/§6/§7。
