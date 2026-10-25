# ADR0043 — 原安装资格的真实 producer 与可信注入

状态：A44 最小实施路线/私有ABI设计准入，未实现/运行/取得资格。2026-10-10。依据ADR0014/0030/0032/0033/0036及固定 Backend/DailyGoalServiceAssembly、I62 NativeCompileOrdinary；精确输入/区间见 Architecture/InstallationQualificationIssuer-A44/InputPins.json。完整Gate0→R1三OS独验→完整R2不变，本地免注册/BYOK/实例持有数据不变。

## 1. 实际断点与选择

固定 Backend application/native_installation.py27–43 的 QualifiedInstallationIssuer 只是Protocol。cli/native_startup.py32–34不传issuer，NativeInstallationAuthority.observe53–54拒未配置或not_ready。更深的 infrastructure/held_authority.py129–133将qualification限为not_ready，_reply199–202拒其它值；I62 resource_authority.rs145/224也固定not_ready。因此只补一个issuer参数仍永远拒绝；DailyProjectService已经正常装配，不能重复它、绕到未安装CLI或把四键ready/SDK/编译0当资源资格。

选择：沿ADR0032原held OS peer/原资源观察，加一个版本化qualified wire与一个具体Backend issuer。资格由完整真实资源测验及许可/构建证据产生，与Owner安装/执行登记、ProductionPolicy/权利/预算分开。原文件map和两个原Evidence分区、registered-media-bundle-v1/registered-production-drivers-v1不改；不是另造管理、政策、通用授权或云账户系统。

## 2. 哪些实际证据能建立资格

每个目标OS/arch/profile的闭合资源集建立独立资格记录。Integration负责实际完整artifact/依赖锁图、原build receipt、对应源码/provenance/完整许可附件、版本floor与loader清单；Test负责固定独立测验代码与实际进程报告；Review核其范围、负例、资源/许可关系；Acceptance按原既有标准对真实结果签署有限资格结论。产品模型、包builder、Owner确认镜像以及本文均不能签发合格结论。

发布包在正式打包前，以待发行的完整固定payload和最终独立host执行资格测验。至少实际覆盖：全role API/MCP/Worker入口与正式required-file分区，全部四profile/CPU ASR/FFmpeg/Piper/原批准driver；原目标Python/tag/架构及所有必要native importer的静态/延迟/实际动态加载origin、CRT/native ABI/最低条件，禁用ambient模块/工具/动态下载；原workflow/driver真实编排与本地合法素材解码、配音/ASR/字幕/混音/渲染/成包调用及数据/时间语义。机制报告须含真正原child/后代/双EOF/exit/timeout/输入输出身份。原ASR/完整作品精度、收费Provider与模型自主性仍按各自资格/验收标准，不能用静音红圆样本或合成预期转写代人听/真实ASR资格。

每个能力行绑定actual finite test IDs/实际原报告、准确全部输入/工具/输出SHA、target/ABI/OS条件及期望；必需行缺测/skip/failed/unknown不得approved。合法的免费确定性资源测试可先执行，不需要启动Daily、安装管理secret、云账号或收费模型；因此不存在“先qualified才能运行qualifier、先ready才能qualified”的循环。独立qualification运行器是构建/安装阶段的固定白名单工具，不使用ProductionAdmissions绕过门生产用户作品；它只能固定有权本地样本/临时DataDir/有限argv，无用户Goal、外网Provider、授权登记、版权伪批准或费用。具体执行scope另由统筹按固定输入/原process计划授权，本文不授权本轮运行。

许可、source-build/native floor与资源能力逐项相交：完整安装包随包件须实际distribution clearance及对应notice/source/link条件，不能license字符串或拥有本地文件代它；用户本地自配置的非再分发资源只核其明确local-execution许可，不能提升为产品可分发。ADR0014/0030的CRT八组件floor、PyAV23库/模型/零notice与完整147生产+24ASR/四profile要求保留，未知必要项仍阻相应资格，不能改0/max或删资源求绿。收费/图片视频API及官方资源resale admission单独，Kimi私人会员/SDK不授其资格。

为有序完成，第一批落实Windows完整闭包的原缺失材料/依赖冲突，再固定离线资格runner和独立验收；其他平台按ADR0033补真实peer/保护/后代source及目标机，分别同完整标准。已有I62 Cargo check0含16生成写闭包遗漏，仅有限类型检查，不能继承为任何运行/资格正向。

## 3. 信任来源与免注册离线路线

资格记录为私有事实sidecar `installation-qualification-record-v1`，不是bearer/Owner权限。精确字段：format、record_id、revision、target、registration_sha256/resource_manifest_sha256/runtime_manifest_sha256、host_build_receipt_sha256、full_file_map_sha256、engine_partition_sha256、workflow_version、driver_profile、roles、profiles、qualification_suite_ref、runtime_report_refs、license_evidence_refs、build_provenance_refs、independent_review_ref、independent_acceptance_ref、valid_from_us、expires_at_us、issuer_id、trust_mode、signature。refs均恰document_id/revision/sha256，完整材料索引由原受保护安装pack保存；target明确OS/arch及已实测feature/ABI条件，不猜最低OS。整数strict，集合有限去重/完整，时间原整数微秒；signature针对去掉signature后的完整canonical字节，记录fullSHA含签名，无回填自循环。

发布发行模式：QualificationPack含原完整记录与独立实际报告/许可/构建附件；由独立已接纳资格发布者签名，验证锚来自安装/更新流程已可信的产品发布者公钥配置，不能读取pack自带key就信任。同一发布者可经营产品，但测试/评审/验收生产关系独立；签名不能代实际报告。这可完全离线验证，无产品注册/订阅/登录，用户数据不上传。

本人无签名/本地构建模式：真实OS Owner可一次明确接纳固定本机qualification verifier的完整代码/版本和资格证据来源（ADR0036的真实安装管理来源），而不是点按钮把候选包qualified。该原受保护verifier运行器必须已独立Review/Acceptance验证其测试覆盖和完整记录validator；它在固定工程白名单实际执行同suite、核全部第三方许可/出处/ABI关系，再形成带本机真实原issuer签名的有限记录。签名私钥只由本机受保护安装工具/vault句柄管理，不在pack/renderer/模型，公开验证锚由这次真实Owner接纳事实及原安装action/floor固定，不能首次读取候选自给公钥就建立信任。认可verifier的动作只建立来源，不补缺测/未明许可；这条本地离线路线不需厂商云批准或root强制安装。Local verifier尚无实现/独立验证，不能现在造一份local-approved JSON。

新增签名实现用固定Ed25519公钥验证suite，采用现有可审计密码库，算法/库精确版本及新依赖由Backend/Integration所属者固定官方文档/锁后实现，禁止手写密码学/把HMAC发布secret随包。资格issuer_id与业务Owner、OS SID各自不同；签名只证报告来源。已有publisher代码签名/OS信任仍有自己的安装验证，不因为report签名就认host。离线撤销以本机已接受的可信撤销pack/实际Owner revoke及单调floor为准，不声称实时获知未下载的全球撤销；有限expiry不自动续，离线可用性不能删期限。

## 4. 原强issuer与持久/current

Integration唯一native具体 QualificationRegistry 读取原受保护安装QualificationPack及可信锚，验证完整实际报告/许可closure/独立接受范围，按原actual target/required全部profile/fullmap/host/receipt与同PreparedLaunch绑定，持有原记录/附件/目录/文件对象及不可逆epoch。仅私有已校验构造返回borrowed QualifiedInstallationObservation；无public Deserialize/Clone、bool、客户端选择report/role子集。观察来自原ResourcePins/NativeInstallationGuards，不重开相同SHA冒原guard。

持久qualification/revoke使用现有ProductionAuthorizationControl框架下单独固定namespace `installation-qualification`：原短writer/外部reserve→record与command commit→complete/monotonic floor语义；不是第二权限库。Backend唯一定义私有正文/严格parser/持久refs与必要新增迁移（实际最终schema后），原OwnerControl→ProductionControl锁序不变。资格admission来源是已可信verifier/独立acceptance，不把普通production.authorization.manage或owner-execution install当qualification授权；Owner可撤销本机信任/安装绑定，不能以管理cap默认批准缺失报告。受保护sidecar供pre-API Native读取；DB关联与控制副本实际一致，损坏/pending/恢复较旧拒，不能取较低revision补绿。实现若用已有Control persistence表达完整事实，应复用它而非新迁移/新DB；具体唯一表由Backend固定。

每次启动验证record及全部attachment/signature/来源/floor/target/validity，与原实际held files及host对应。返回给某child的资格对象绑定其原launch/role/Engine instance/connection/session/完整三SHA和原文件分区/record ref。同package可有跨实例的签名报告，但每次实际安装绑定/当前source由该实例原受保护安装事实建立，JSON记录不能给别的实例授票。每次writer外current重核原peer/resource/license/proof/current registry/floor/期限；取得覆盖该资格和原版本的读lease并保到原短writer，revoke/replace沿原控制锁串行，先不可逆invalidate本地epoch再使新派发拒绝。writer只本成员/epoch/thread/已有lease/同connection rows，绝不RPC/hash/OS或等待外部checker。

升级创建新版本pack/record/host/fullmap并独立测验；不原地改旧版本、不以同version继承资格。新record真实commit/complete后才原子切current，旧lease/worker持原版本到真实终态；pending/unknown不能清旧预算/Operation或重提收费。重启新issuer重读真实current/floor/附件，不反序列化旧Evidence当live；恢复未知pending只原exact record/key/完整真实报告来源及原receipt，不自动造资格。revoked/expired停止新生产，不删除已成片/用户数据/unknown账本。资格checker/sidecar缺失不会触发无限启动或自动测试循环，App显示本机具体待完成资源，安装工具的固定显式repair才执行一次有界验证。

## 5. 唯一私有ABI与wire版本

保原 `held-resource-authority-v1-candidate` 全字段/方法/事实对象及not_ready严格语法，不扩它接受qualified。新的固定indexed入口 `video_creator.cli.native_startup.main_qualified(*, startup_record: bytes, locator_bytes: bytes) -> int` 与原record/locator参数一致，由原可信Native launch plan明确选择且索引包含该函数；不能env/public模块/renderer/任意factory注册。旧main remains facts-only/诊断，不静默提升或回退。

Backend唯一新装配函数 `connect_qualified_native_installation(*, engine, bundle, locator_bytes, context, installed_native_image, installed_native_image_sha256) -> (NativeInstallationAuthority, OwnerProtectedNativeBuild)`：核同Engine/Bundle/实际instance/role原source，先创建实际原held connection v2，绑定唯一 concrete `NativeQualifiedInstallationIssuer`，随后原 native_pending_goal_store/store.current/original_projection/assemble_owner_services 不变。原_factory建立qualified路径时必须确切调用此函数，不能给Protocol注入用户实现；issuer创建/记录读取不authenticate管理vault，不将Worker变管理者。对象同Engine/connection/context/Bundle/原可信verifier/registry，close实际原资源在既有顺序。公开Goal/OpenAPI/SDK及InstalledProductionEvidence DTO不加qualification票据。

具体Backend issuer继续原issue/assert_current签名，另新增私有 `assert_local_current(*, evidence, connection, original_facts, context)` 和 `close()`。原Evidence object→原HeldFacts/原strongqualification observation/ref/lease/epoch的identity-map须强引用、is成员核验；复制/跨issuer/Engine/session/thread/闭源拒。NativeInstallationAuthority.assert_local_current必须也核issuer的local hook，不只connection。外部assert_current负责取得current/lease；短writer hook仅原对象和本机不可逆缓存。同Adapter close同时撤销issuer原成员，再按原connection/build持有语义收尾，unknown不释放guards。

私有wire=`held-resource-authority-v2-candidate`，继承原bind/observe/assert_current、same原peer、20s启动/10s整帧exchange、uint32LE/canonical严格JSON、32MiB/seq/拒unknown/duplicate的全部规则。request仍原字段和闭集方法，只wire变v2；bind固定role/instance，observe不可指定子集。response原v1的12字段全部保留，新增唯一 `qualification_binding`。它要么null且qualification=`not_ready`，要么恰 `record, record_sha256, registry_revision, revocation_floor, checked_at_us` 且qualification=`qualified`。record是上述完整typed签名record，record_sha256为原canonical全SHA；所有int strictuint64，时间positiveus，record正文≤1MiB，不能truncate。完整报告附件由原held资格registry验证并保持，不经JS/任意URL下载。

bind成功code=`bound_qualified`或原`bound_facts_only`；observe=`observed_qualified`或原`observed_facts_only`；current=`current_qualified`或原`current_facts_only`，status200。同reply完整identity/maps/观测形状沿原method；qualified observe/current必须同原record ref/registry/floor、同原qualification object/held observation关系，current不得换report冒旧对象。首次bind没报告可只返回facts，不允许issuer发行；事实成功不是生产ready。not_ready binding必须null。资格变化current以409 `qualification_changed`/`qualification_revoked`/`qualification_expired`拒；503 `qualification_unavailable`/`qualification_unknown` 保未核事实。原坏frame422/peer403/foreign409/timeout503不变。Backend唯一最后冻结precise typedABI，Native按同源实现，不同时维护两手写模型。

Native生产producer增加 `PendingAuthority::create_qualified(original guards, original admitted registry source, exact launch context)`，原create_facts_only保持；create_qualified不能调用new Registry fromJSON，它只能消费原已核issuer强对象。每条session原registry持 `ID→(borrowed原held观察, borrowed原qualified观察)`，只有全scope当前时发qualified。startup SetupOwner配置仍旧安装事实not_ready，它只登记，不把原PendingInstallationObserver的retained observation当生产qualified。首次Goal要执行时通过上述真正生产authority；setup-aware恢复也消费同originalcurrent，不从Owner confirmation制造许可。

## 6. 实施顺序与真正完成条件

1. Backend先固定new wire/model/error/具体issuer identity-map/local-hook/两固定entry及control namespace存取ABI，完整交接源/迁移；不填approved默认，不改旧facts测试期望。缺actual qualified source时准确503但正向生产路径可实施。
2. Integration接native QualificationPack verifier/原强registry/current lease、qualified原Pipe producer和index/main_qualified路由，同时落实具体缺失artifact-license/provenance/floor/依赖图及三个平台原source。先能真实读取/验证有资格记录，不假签名/Owner点确认跑绿。
3. Test独立固定离线资格suite/工具及全部正负矩阵，Integration按具体受控scope运行原候选；Review审report闭包，Acceptance实际本地有限资格签署，完成后Integration产生真正pack/current binding。Windows先闭合，Linux/macOS紧接完成，不将缺机器改skip合格。若必要原资源实际缺件，明确每件owner/获取或重建scope，不反复写pending来代工程进展。
4. 后端/集成真实same instance/原OS peer/全部API-MCP-Worker从current强issuer装配Daily，正常firstGoal/accepted restart/后续新Goal→完整音视频/text/RAG/ref/export；本地无产品登录。Test覆盖复制report/伪selfkey/samehashforeignsource、全部必要scope任一缺件、ABI/许可源不对应、record或floor回退、revoke/expiry/change竞态与短writer无I/O、current断线旧Evidence失效、upgrade unknown不释放原worker/不重复费用。真实安装/许可/能力和独立标准通过方算qualified，source/编译/机制fixtures/本文不算。R1实际完整作品/三OS和后续R2另由独验。

本轮A44仅读固定材料、写架构文档；未产品import/DB/GUI/OS授权/测试/模型/联网/密钥/下载/安装/部署，费用0。已读旧报告/许可决策只作为既有需求，不声称其缺件已补或旧能力都合格。新wire/issuer/资格suite/verifier/local信任与三OS当前均未实施或实测。
