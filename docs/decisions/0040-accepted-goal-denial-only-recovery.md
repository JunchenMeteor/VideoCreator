# ADR0040 — 过期后仅收口原已受理 Goal 的真实事实通道

状态：A37 设计批准，RV80-P01 尚待 Backend 实施及独立验证。2026-10-10。
依据 RV80 正式报告222d7313…、P01 f46da2…、B41固定gap c4f8a035…、B40必要普通Store/issuer/Daily源，ADR0037/0039；完整身份见 A37InputPins.json。不批准产品/DB/Owner/安装资格。完整R1独验后连续R2不变。

## 1. 实际断点与唯一权限

Daily811 reserve→816 issuer._guard→Store599–605 expiry409；重启Store472–514在读原Goal proof后仍507 _active，issuer211还先_identity。_deny_intent790/797再次依赖活跃执行。此源码闭环不能处理原真实受理但已知不再允许执行的Goal；不是实测停摆。

增加私有 accepted-fact 通道，唯一能力为“确定拒绝这一个已受理但未commit的Goal”或“完成这一个已commit回执的原floor”。不创建/恢复可执行 identity，不授制作/管理/再授权，不放宽 current/_identity/_active/_guard；与ADR0041真实新Owner权限彻底分开。禁止 allow_expired/skip_current Bool、客户端恢复票据、替换登记来冒原角色。

## 2. 原入口、强根与最小端口

Backend 原可信 CLI/native/headless 启动装配，在查 Store.current/assemble_owner_services/issuer.current_guard 之前调用本路线。原已在内存对象的 guard 失败也转交同真实事实根重新取源，不把旧 CurrentExecutionRegistration 或异常403直接当源。执行-only Worker不加载管理vault。

固定内部接口：
- 原 trusted startup/OwnerBootstrap 工厂提供 LocalOwnerFactSource，仅供准确账本事实恢复。
- ExecutionRegistrationStore.accepted_goal_facts(root: LocalOwnerFactSource) -> ContextManager[AcceptedGoalFactContext | None]。
- DailyProjectService.resolve_accepted_goal_fact(context: AcceptedGoalFactContext) -> None。
- Store.assert_goal_fact_writer(connection, context) -> None，退出上下文失效。

LocalOwnerFactSource 来自当前真实OS Owner/同实例/原受保护data与Control目录及原 DB identity 的固定启动源：native消费原实际peer/PID+creation/原PreparedLaunch-held代码/目录对象；headless固定Owner入口以原inspect_owner_directory和当前实际进程/原可信装配取得身份。普通HTTP/MCP bearer、Goal/JSON、manifestSHA或未认证locator都不能提供它。无须重新取得已过期的 execution current，也不要求每Goal人工确认；新入口仅为免费确定性账本收口。原代码/启动来源、实际OS目录不能核实就保持明确缺件，不用安装 qualified证据/私密凭据/GUI确认替代真实性，后继必须接正常事实根。

AcceptedGoalFactContext 为 eq=False 原Store成员、同Engine/Daily/bootstrap/Control/issuer、原根对象、thread/epoch/context与强持有源。它含且仅含原intent/proof的精确事实，以及封闭用途 deny_uncommitted 或 finish_committed。用途由服务从原 DB/floor事实判断，调用者不能选；已知拒绝 reason也由封闭检查器确定。外层检查OS/文件/peer/源，短writer内只原对象成员/不可逆失效/thread/已核缓存及同连接DB事实。跨Engine/克隆/关闭/expired root/外来context拒绝；已知权限到期不等真实性根到期，后者不可放宽。

## 3. 历史真实性与已知拒绝判据

在原 OwnerControl→ProductionControl 锁下，重用原严格parser、原commands/metadata/受保护 AcceptedGoal字节和规范hash核验，不通过 current()先取得执行身份：

- 原实例、实际domain Owner、OS subject/目录device+inode、DB identity与原OwnerControl高水位；原OwnerBinding完整体与其实际 bootstrap command/action应链到 intent.owner_body_sha256。当前同Owner相同目录的真实renew记录可作已知代际变更，但旧完整体须从原真实命令重建核对，不能凭hash补造。更换OS/目录/domain Owner或无法证明旧动作不是自动拒绝条件。
- 原Goal/key/canonical input/hash、original normalized request/hash、所有planned IDs、原 creation父体/ref及真实Owner动作/commands，完整原installed/各role registration原body/ref/action与status。复用 Store._record/_installed/_read_action 的真实性核查，不能在这层调用_active或用新登记代旧parent refs。
- 外部pending SHA必须恰指原受理journal及完整 protected副本；原scope/namespace、原revision、唯一未解决/已解决命令和实际floor相合。v2额外核ADR0039实际DraftOrigin/原create回执/acceptedSetup及steps关系，旧人审记录只是历史接受事实。
- 已知不可执行仅限真实期限已过，或有完整原命令/receipt支撑的准确parent/registration/installed/child撤销、替换、同Owner代际失效；只凭status异常、缺row、丢receipt、未知源、宽泛403/409都不构成确定拒绝。期限采用原整数微秒和真实clock，不猜余额/受理结果。
- 格式/身份/命令损坏、DB低于floor、未知namespace/另pending、owner更换、原v2关系缺失保持repair/pending并明确错误；不能catch-all洗成denied、zero cost或complete。资格 not_ready没有执行许可，但不是原事实损坏，也不应永远阻已知期限拒绝的无媒体通道。

原read_pending_goal_intent的外部文件读取/真实关系核心拆为严格事实解析与执行current两层，v1原规范字节、v2显式dispatch不变。新factory不是对外“读取任意过期record”的端口。

## 4. 原writer、收口与生命周期

仅未commit：DB revision=D，外部floor=R=D+1，pending=原intentSHA，无原accept/denied。同原SQLite短writer初始/final核原context、Owner/目录缓存、本次完整历史rows/commands和原intent/floor snapshot；append原 _DeniedGoal/GOAL_DENIED_SCOPE，revision置原R，保original intent/hash/planned IDs并留准确reason及内部事实来源关联；commit后 complete(R, 原intentSHA)。不再次reserve/新revision/新key；无Project/child/Production/Run/lease/预算/Operation/计数/dispatch变化。v2真实首草稿保留且未授权。

仅已commit：DB revision=原R，完整原accepted/denied回执、实际Project/child/Production/Run/命令/消耗结果一致，外部原R仍pending，context只finish_committed→complete原R。不得改成功为拒绝、重复原副作用/计数或尝试执行。无pending/已complete的精确历史结果只幂等返回；相互冲突多回执拒绝。收口初次/重启/已有对象/commit后失响应均复用原同事实，不依赖第二次客户端请求。

同原_store._lock及Owner→Production锁序，不在短writer新OS/hash文件/RPC。context退出/根失效/connection关闭不可逆invalidate；清pending成功后才按原 full current 正常启动/dispatch，过期身份仍拒。正常active-success恢复继续原完整current/quota/资格路径，本context绝不能接 _commit_intent/注册/reauthorize。源变化竞态导致rollback和重新准确核实，不把不确定结果标成功。

拒绝收口不撤销/改写健康兄弟的Owner/登记/generation/lease/fence/资产/预算/unknown；原reserved/spent/未核受理保持。清此准确已知pending后其它合法current工作可继续，不永久全503。若别的真实缺件仍存在，如实区分；不能为启动绿绕过资格。

## 5. 后继与独验

Backend负责实际fact根及startup/current前接线、两层严格proof/context、原拒绝writer与exact complete；原 _identity/_active/current writer安全门不变。原commands/metadata可留事实来源，必要新增journal版本/迁移在其实际最后版本之后由Backend唯一维护，不能改原0009或旧intent。Integration仅消费Backend正式固定startup事实factory/生命周期接口，客户端无新恢复token/SDK字段；Frontend只显示准确拒绝或待核实状态，Media无denial权限。

Test独立运行reserve→executionexpiry→restart与原对象两种真实入口、commit前/后崩溃、完整同floor只一次denied/complete与健康兄弟继续；核无新增作品/预算/Operation/计数，v2保同draft，v1字节/parser/history兼容。损坏/缺原命令/foreign/克隆/closed/错namespace/Owner替换/未知floor保pending且不生产。仅fixtures不得证明OS/Owner/资格；RV80-P01由独立Review复验后处理，架构不关闭finding。

A37仅读固定普通源/写架构文档；生产/DB/Owner/native/API/模型/凭证/联网/收费/测试0。

## 6. B41 final82 的实际消费与本轮精确接线

A37后来消费B41正式最终源（非早77模型）：Handoff af2e3b61481af271adf559da7b2ddbbe404d637461e11c6d5a97c0002e2b61ca，ImplementationInterfaces ea71557613d3210d0454a57e0919f70d24d9e6461465669fb566794d506da593，SourceIndex856de0b767dbd95393a87cf27de9a673a5fd4e94ab3f5ce9cfd11f17244e2c41。所有精确ordinary pins见A37InputPins；schema10为正式源事实，未实际迁移。

Daily v2采用既有 DraftOrigin/AcceptedSetupRef 与明确 _parse_goal_intent；read_pending128–190仍比当前Owner体，recover832–909仍先active guard；v2成功分支885–889要求原setup strong source。OwnerSetup.recover280–296、_accepted_local304–328、goal_source549–632及_configure_execution517–546同样要求准备会话、原setup期限、Owner current和实际 qualified authority；不能用这些入口伪造P01过期denial源，也不能把journal/API/MCP启动body变AcceptedOwnerSetupSource。

原 trusted startup在 current/assemble_owner_services 的active checks之前，构造仅事实用途的原Engine/Bootstrap/ProductionControl/Store/Daily同源装配（management=None，不读取vault、register_execution_identity或configure执行映射），消费真实 LocalOwnerFactSource；这只是本ADR明确批准的只收口装配，不是执行服务success。若没有这样的已认证根，Backend/Integration须接固定端口，不能以serialize fallback或永远503代它。已在内存的setup/issuer failure同样转入这个真实事实根。

Backend在原owner_setup_service/journal维护严格历史v2事实核查：实际owner_setup_journals preparation/accepted body与成对SHA、受保护accepted文件、origin/AcceptedSetupRef、owner_setup_steps proposal/final command/dependency与原动作receipt/commandSHA、metadata五个原planned IDs。仅事实validator不调用 _issue/recover/goal_source/assert_accepted_current，不构造确认或执行authority；外部文件/OS检查在writer外，短writer缓存+同connection各rows初始/final核。每个相连步骤完整核，未确定动作保持pending。

v2未commit拒绝时保原draft及真实已完成steps，不填 goal_result_json（它是ProjectGoalAccepted成功格式）；与原GoalDenied回执的独立明确progress关联和原blocked阶段/error码留在setup journal，后继准确status返回该原拒绝，不继续旧Goal/重新生成五IDs。已commit则核与 owner_setup_journals.goal_result_json/sha256/phase=completed 一致再finish，不因之后改draft调用 _draft要求仍旧revision。accepted journal/旧Goal字节不改；必要新progress关联由Backend在schema10之后按实际选择准确迁移，不能覆盖原0010。成功v2自动restart仍须实际新authenticated preparation、原accepted-source工厂/qualified执行原assembly接通，是独立必须实现项；P01 facts通道不替代它。
