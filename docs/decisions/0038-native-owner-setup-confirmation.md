# ADR0038 — 首次 App 配置的真实原生 Owner 确认

状态：A35 设计准入，尚无实际人审/原生/产品运行。2026-10-10。
输入：B40 NativeObserver immutable71源及 NativeUiConfirmationGap/Interfaces；I57 Early与CompilationOrdinary main/lib/session/commands/ABI；ADR0036/0037。身份见 A35InputPins.json。完整R1三OS/免产品注册/BYOK/五步/单Goal→连续R2不变。

## 1. 真实缺口与唯一路线

原 confirm_local_action315–325要求真实 stdin/stdout.isatty() 与用户精确输入 AUTHORIZE；管道子进程不能满足，禁止 patch isatty、预写回答、模型点击或 True confirmer。B40六字段启动协议、I57 installation facts/not_ready及文件SHA没有人类确认语义。当前I57固定 session.context 还要求 API Phase::Ready，因此首次配置不能借普通 engine_request broker 授权，不能放宽其ready/source约束。

选择独立 pre-API OwnerSetup 原生会话：受控原生宿主以真实OS Owner/当前GUI会话启动唯一已索引配置子程序，显示原生OS模态和明确输入，由独立受保护本机通道交给Backend唯一强对象确认consumer，再调用原管理服务。Headless继续原真实TTY路径。未配置时可以显示setup状态，不虚报API/Worker ready、不要求用户安装另一供应商App或逐项目终端授权。

## 2. 配置意图、真实展示与人类动作

Backend唯一 OwnerSetupIntent-v1：setup_id、instance/domain Owner、实际受保护data目录身份、首个真实Goal/input hash及项目草稿、安装NativeInstallationInputs/外部receipt/独立host身份、有限role/source/template/rights声明/原预算组及cap/quota/expiry、预期原Owner状态/generation、固定有限step列表与各proposal规范SHA、固定源/版本。禁止秘密、argv/module/env/shell/任意路径/任意command selector。首个项目是用户真实目标，不预造空项目。安装资格/许可证不由确认产生。

部分后继ref必须来自前一步真实receipt：Intent可使用封闭 typed dependency（仅本次 owner_init结果和本次 installed/execution结果的精确ref），不能用通用JSON路径/表达式。Backend封闭resolver只填这些实际已核ID/revision/SHA，范围/金额/有效期/角色/资源绝不能改变；记录每个最终command完整hash及依赖receipt，越界需要新的真实确认。多个真实动作保各自原receipt/floor，不能拼一个假的总Owner动作。

Rust从已索引Backend真实准备结果接收完整canonical intent，校验唯一版本/严格字段/32MiB边界与原composition/source关系。主Webview只能以实际main label+固定URL+document generation请求 prepare/present/status/abort；不得接收或发送 approve(bool)、已输入AUTHORIZE文本、管理secret/capability或确认票据。新setup_context只允许文档来源已核、实例锁已持且未closing的 setup-required阶段，不调用要求API Ready的旧context，也不把setup就绪当API就绪。导航/换代/闭窗失效旧未接受challenge。

Native GUI使用宿主控制的OS模态（Windows实际Win32原生输入窗、macOS NSAlert原生输入控件、Linux实际GTK原生输入控件，由Integration按当前固定依赖准入实现）；标题/原Owner身份/实例/数据位置/首Goal/所有scope、expiry、quota、预算/转移/rights均从同一canonical intent生成，提供原生只读完整范围详情。不能让Webview给另一段说明或只显示不可核的hash。宿主生成挑战并要求用户在原生控件精确输入 AUTHORIZE <instance> setup <intent摘要> 后明确确认，取消/不匹配不授予。不增加新前端框架或云账号。

真实GUI会话身份取OS源：Windows当前进程TokenUser/TokenSessionId/实际认证会话及活动交互桌面；macOS/Linux真实UID/EUID、进程/audit或login session及宿主实际连接的GUI会话。环境DISPLAY、JS用户字符串、PID文本或窗口截图不是身份。Host与受保护实例同一实际Owner，session/目录/源与确认前后均current。各平台source尚需Integration实现并实际机器验证；Linux无GUI时选择真实Owner终端，不伪造PTY当人审。该确认不声称生物认证或抵御任意同OS Owner/管理员原生代码；模型/插件无本通道/原生输入/Control写权限，不得以自动化点击算真实Owner接受。

## 3. 私有强源与精确通道

新增固定索引 callable video_creator.cli.native_owner_setup.main(*, startup_record: bytes, installation_locator_bytes: bytes, confirmation_locator_bytes: bytes) -> int：startup_record仍原六field，另外两参数分别为原installation和独立confirmation locator身份字节；Backend唯一实现严格模型及输出ABI。固定 NativeOwnerConfirmationConsumer.accept_setup(expected_intent) -> ConfirmedOwnerSetup、assert_current(confirmed)、assert_local_current(confirmed)、close(confirmed|None)；OwnerSetupService.execute(confirmed, *, engine, bundle)只消费同一原issuer/Engine的强对象，不能接字典/布尔。旧 native_owner_startup/main、六field、十field及I57 facts协议保持。新入口只配置，不替代serve/MCP/Worker，不通过环境/public模块选择或旧plain-main回退。

确认wire=native-owner-setup-confirmation-v1，role=owner-setup，Windows独立VideoCreator-OwnerSetup管道，FIRST_INSTANCE/DACL真实Owner+SYSTEM/拒remote；子程序自己连接。Linux/macOS消费ADR0033等价原生peer/creation/held source，不靠socket路径/JSON/PID代强身份。父验证原PreparedLaunch/OwnedProcess的实际child HANDLE或等价进程身份/creation/Owner/source、同instance及角色；子程序验证实际父peer及独立OwnerProtectedNativeBuild/外部已核host来源、真实Owner/目录。locator/session/challenge/hash只是payload，不能独立授票；新channel不复用ASR/MCP stdin或I57事实字段。

通道固定bind→present→take→assert_current→close；uint32LE+严格canonical UTF8/版本/未知或重复字段拒绝，帧≤32MiB，严格seq、同一session/原子对象映射，无重连。present接完整Backend intent，立即返回pending，再由原生GUI线程打开模态；单次exchange沿原10s绝对期限，不把用户思考时间算网络成功。challenge可供用户查看至10分钟，确认后未消费窗口最多120s，以宿主单调时间判过期；初建/绑定沿原20s。数字/时间字段严格整数与已有微秒语义，不能接受bool或客户端时间扩大期限。

Host只在真实原生当前输入完成后生成原 ConfirmedSetup对象（不可Deserialize/Clone、强issuer成员、原dialog/session/intent/Owner/document/child身份），take只能交付给原已认证配置child。Backend NativeOwnerConfirmationConsumer.accept_setup(expected_intent)验证真实peer/原challenge关联/完整intent、实际Owner/源及deadline，产生eq=False ConfirmedOwnerSetup；其issuer/原connection/原host确认ID/同Engine绑定保强对象集合。来自JSON或同值DTO的构造不在集合，不可当确认。writer外assert_current重核session/peer/资源/确认源；writer内assert_local_current只原对象/epoch/thread/已缓存不可逆失效，不OS/hash/RPC/await。

take后各step只能由原Driver消费一次，以已确认intent+确切action/最终commandSHA/已核依赖receipt授给原服务。step剩余权限不允许model/API主体使用。重复take/foreign对象/不同Engine或child/changed intent/超时/关闭/OSsession变化均拒绝；take回复未知或丢失不能数值重试/reconnect造人审。确认是安装/创建配置授权，不能充当普通ReviewDecision、作品批准、媒体版权/独立精度或平台发布许可。

## 4. Backend原服务、持久受理与恢复

Backend新增私有 OwnerSetupService/OwnerActionConfirmationSource/ConfirmedOwnerSetup及固定原生consumer，严格唯一可信工厂接入；不是可注册的 bool callback。原 OwnerBootstrap.change 与CLI action调度保默认真实TTY行为，增量仅接受原固定setup服务持有的typed强确认 source。每个原管理方法仍验证实际OS/目录、当前Owner/原registry capability/完整command；既有Owner vault由原Backend受控访问，secret不跨JS/确认wire/普通bearer。实际GUI路径的authentication_source为native_owner_session，旧TTY仍headless_administrator，不伪造源。

首次空实例：prepare真实草稿及意图→原生人类确认→Backend将完整AcceptedOwnerSetupIntent-v1与本次确认来源/实际Owner身份/限定step/command依赖/有效期持久在受保护实例与Control恢复材料→按固定steps执行原Owner初始化、真实安装/执行登记和有界creation委托（视真实已有状态只执行已确认动作）→从同一个真实Goal继续原ADR0037项目/Run流程。每step遵守原OwnerControl→ProductionControl→短writer、reserve/commit/complete、原idempotency/action receipt及资源writer外观察。原Owner/current/project scope/预算/unknown不扩不重置，GUI不手填管理凭据或复写注册记录。

接受记录commit前必须确认源仍current；commit后已受理的准确intent只允许有限续跑，不要求每step再次人审。闭窗/断连/host死先使未受理确认和未授予step失效，不猜是否已受理。已持久受理且已有原receipts时，后继固定Recovery以同真实OS Owner/受保护directory/current、原intent/step/receipt/floor及同资源身份重核，重建仅可恢复该已受理intent的私有authority，不重放原临时确认票据。已commit step只返回原receipt；仅原待完成step继续，不重新init或造新goal/key/费用。换Owner/撤销/expiry/资源或范围改变明确停止，保已提交事实及pending，需新的真实Owner意图；不把非current源恢复成成功，也不循环弹窗恢复未知批准。原活动制作和unknown核实不因setup窗口关闭被取消。

持久确认来源记录用于恢复/provenance，不能导出作别人实例的本机授权。必要新表/metadata及迁移版本由Backend唯一维护；旧v1 Owner/执行/Policy与操作字节不批量改写。并发setup同实例互斥；同key+同intent复用原状态，异意图409。窗口关闭/配置取消/Worker取消为不同动作，原资源/Arc到真实child+后代/EOF终态才释放；close ACK/GUI结束不冒进程退出。

失败统一由Backend唯一ErrorEnvelope/私有ABI声明：malformed/不完整范围422；错误Owner/角色/源/取消或未真实确认403；changed intent/旧generation/replay或并发409；实际源/资格/会话不可用503；expired明确拒绝不自动延长。只输出安全code/status/intent或action非秘密ref，不回显私密Goal/凭据/消息输入。配置成功只表示对应真实actions提交；不以not_ready事实端口宣布作品/安装资格成功。

## 5. 后继顺序与独立验证

Backend先固定Intent/typed强源/service/原方法消费签名、接受恢复及ABI；不能将旧confirm函数换成永真，也不改B40正在实现的ADR0037源。Integration后接pre-API SetupState、固定索引Owner child/独立peer通道/原生模态/原资源生命周期及生成SDK（仅安全prepare/status接口），FrontEnd仅首次settings/Goal预览、请求显示原生确认和阶段状态，日常五步继续原scope，不能传confirmed。安装事实/6field、资格issuer和既有API Ready仍独立完成；三OS真实Owner/session/GUI或headless均必须实施验证，不能永久nonTTY503替目标。

Test独立验证：真实非TTY App首Goal配置由本人真实原生输入→不同原actions/receipts→同Goal继续；headless原TTY精确AUTHORIZE兼容；后续至少两个新项目无重复每天授权。反例覆盖JSbool/伪DTO、remote/错误child/Owner/session/role/源、navigation/generation、intent篡改/依赖插入/未展示范围、过期/重放/双消费/并发/close/断连/take未知，writer无I/O；断点为确认前/接受commit前后/各reserve-commit-complete及重启，已committed step不重复、scope扩大须新人审，旧Worker/预算/unknown保留。单位fixtures可验证grammar/状态但不得称真实人审通过；实际人审正向需本人操作证据，Test/Review/Acceptance各自职责保持。

本轮只读固定必要普通源/写架构文档；native/Owner/UI/DB/API/model/network/secret/费用/安装均0。最初有限路径定位有未命中（Early为阶段标签非目录），已按实际索引纠正，非产品失败或全机不存在结论。所有未运行/资格/三OS缺项如实保留，R1独验后连续完整R2。
