# RV9 — I9 来源分类与 reader 顺序有限复审

阶段 FINAL（静态及获授权的窄机制证据）。永久评审只读源码/标准/普通证据；没有运行测试、产品或进程操作。I9 owner结果不是独立验收。T11完整交接未完成，仅按统筹追加授权消费 T11MechanismRoundOne 的公开原红、原子收据及源绑定测试，不能借未来绿或签Gate。

## 固定身份与结论

I9Handoff.json SHA `398eefab00d6fd3db5c9e8a9da1f71cf958cc826e60c2ceb7bd0528054da885b`；MD SHA `bcc1f5b84a21cdbcb2edc2ba06be19839543175d64050f5139d645caec158c97`；SourceFreeze SHA `a30fde8e46caca7c325424678186c645efe64764fddce58b38d8cf7f4b4b18fd`。ADR0008 SHA `5a1438215ad5845c3e90b876509c0ba7938681601cb6b346ef860a51c4d8f84f`。四源和交接列出的12份普通源/收据/探针证据均实读hash匹配：

| 固定源码 | SHA256 |
| --- | --- |
| tools/build/DevRuntime.mjs | c45c5132bcc457afdbb84808809873511a05c78a09199a52af6d962bec53b034 |
| packaging/RuntimeContract.md | 4ea9615f3d26ead3cb5b127ed14eb933a5ae6704ae52c8c4e456e230882970bf |
| tools/build/EngineProcess.mjs（I9未改） | 3b6716f93e05122a718e41d4bfbbcf330d706be3b4412f271816729c08eed076 |
| apps/workbench/vite.config.ts（I9未改） | c5cf940ca7aba73896e70ae37a4fd0177fd1d1d0e16370e972c35047d8ff6932 |

来源映射修复初次调用和cleanup Promise pending时的原缺口，reader原创建顺序差异已消除；**RV7-P01尚未完整关闭**，settled后、host实际exit前仍有非零锁存缺口，见RV9-P01。RV7-I01仅原静态顺序差异可局部关闭，新的真实预缓冲/资源阶段行为仍待独立证据。未签整个入口、技术冻结、安装或Gate0/R1/R2。

## RV9-P01 — P2，延续 RV7-P01 的 settled 后异常窗口

归属 Integration；Architecture保持ADR0008分类要求；测试归T角色。触发顺序：可信合法帧已启动停止Promise，两路清理完成、原汇总报告controlled，host尚未实际退出，此时SIGTERM注册回调到达。

固定 DevRuntime:46 `lifecycleFailed ||= abnormal || cause !== 'host_control'` 确实锁存失败；但:49 `if (stopping) return stopping` 立即返回已settled的旧Promise。唯一按controlled设置exitCode1的位置为首次异步closure:63，而它已经执行结束，不会因复用旧Promise再次执行。结果可能留下lifecycleFailed=true但exitCode字段仍0。

ADR0008:11要求SIGINT/SIGTERM即使资源清理完整仍非零；:13要求每次stop先锁当前异常、复用Promise且合法帧先到/异常后到不洗成功。先锁布尔值不足以保证更晚的宿主退出码。

本项已获**实际运行的源绑定VM机制反证**，不是Windows实际OS信号或真实host close0缺陷的已复现声明：

- T11MechanismRoundOne：7项6pass/1fail/0skip，Node实际exit1，113.1157ms；6个源scope前后及范围外变化0，Dev before/after均为c45c5132…b034。
- 红例 `ControlSettledThenSigTermBeforeHostExit` 的原断言 actual0≠expected1，测试断言保持。另六种首次/Promise pending来源顺序通过，只证明各自机制路径。
- 公开测试源 SHA `a9d4b140503256ba403fbd6cf6c0e85ea50b0a68049b95a7f275507b25b03422` 与原子收据一致；截取真实DevRuntime从`let engine;`至控制reader之前的源码块，在VM中注册原signal回调，使用真实cleanupRuntimeChildren配合**synthetic** API/Vite回调、process.exitCode和console。实际产品进程0、实际OS signals0。
- Stdout SHA `aa1c5a46131855b430266246a7526a6c07eec2f0a0e5cbea0bc2990301a80812`；CommandReceipt SHA `977eb4653a32360e69f9408b09cfad1dc01be620ad204237dd39d3f3fbd3f384`；JUnit SHA `d2f8712e7340f47e2450e05ff0fbf831dd9d70e3262229c688b7a652f7732424`。Stdout摘要/完整XML/Node退出相互一致，未运行第二次或改期望；完整T11外包装/正式handoff尚不在本有限签认范围。

建议：异常来源到达时把宿主非零事实在复用Promise之前锁存，不能依赖首次cleanup closure再次执行。保留同一清理Promise与单次两路清理，不重发帧或放宽来源；已发清理日志与更晚异常分别如实呈现，不能用先前controlled日志替实际宿主退出。Integration在当前读取批终态并解除冻结后修自己的生产源；T角色在新hash上保原红/原断言独立复验，真实Windows可达性继续单列未测。评审不代修或降标准。

## RV7-P01 的已修范围与未闭范围

DevRuntime:45–49在Promise复用前识别所有非host_control来源并锁lifecycleFailed，:47只记可信成功请求，:61另要求trustedStopRequested及无粘性失败。SIGINT/SIGTERM handler仍调用同一stop，但其非控制cause现可被识别；首次signal及cleanup pending阶段不再具备旧默认false直接走controlled的静态条件。API正常事实与Vite actual owned_force不因host异常被伪装为graceful。

owner机制批11checks在真实完整API/Vite中通过`process.emit('SIGTERM')`验证合法控制先到、后signal、cleanup pending的分支，host实际自然1/error、cause仍host_control，即使API normal0/marker1及owned_cleanup_complete=true。该证据不包含上述settled窗口，不能据其全关闭P2；也不是Windows OS handler真实触发。T11六个机制绿同样不能覆盖第七原红。

## RV7-I01 — P3，原静态创建顺序差异局部关闭

ADR0008:17明确保持0007“在创建engine并await ready之前建立reader”的硬要求，不是批准放宽。固定DevRuntime:34–44先初始化engine/pending/失败/回收状态及:45–66可调用stop；:70–92建立reader，:89订阅data；异步prepareEngine从:95开始，:96让预缓冲输入有消费机会，资源准备:99以后、目录创建:119、launchEngine:121均后于reader。因此原“先launchEngine再建立reader”的源码差异在c45身份已消除。

未有engine的合法帧仅:50锁pending；不直接引用空资源、不发虚构API停止marker。准备中:97/104/118/120检查pending，未创建引擎:125–129回收reader、非零、API/Vite not_started/marker0/cleanup_complete=false。若API实际已创建，:132明确将pending移交stop，:137/161避免再启动Vite或虚假hostready。非法帧/EOF仍不调用stop；默认off、精确9/64、Socket准入、origin/token/manifest及两路helper保留。

这里仅关闭**原静态位置/初始化/明确交接差异**。setImmediate与OS管道的真实预缓冲消费点、资源准备各窗口、创建后交接/异常时序及自然handle终态，还需新hash的T11独立行为证据；没有从旧T10十八项或owner早帧绿继承完整验收。

## owner事实、原红和缺口

| I9 owner层 | 实际工具/host | 支持范围 |
| --- | --- | --- |
| 完整正向 session4469 | 工具0 / host自然0 | 15checks、API normal0/marker1、Vite actual owned_force、独立原listener关闭和已捕获身份无剩余；新源before/after一致，仍是owner自查 |
| 原finite边界批 | 工具1 / 已完成早帧case host1 | 该case5checks、无目录/API/Vite/假ready/marker；整个原批缺ended_at和source_after，第二child原stderr缺失，不称整个边界绿 |
| 修自己脚手架后的机制新名批 | 工具0 / host自然1 | 11checks，process.emit机制；不补WindowsOS信号、原缺失或完整T11 |

原脚手架ready等待未关联child close，留下Node unsettled top-level await；后续Windows--import file URL与ready/close关联只是owner脚手架纠正。原部分收据、工具exit1、缺第二stderr及整批终态缺口保持，不以当前旧PID查询为空重建历史退出。未重启22508、未借空集作保护证明。

本有限阶段没有新增跨OS/TTY/未知stream/后台Worker/费用、native父硬崩溃/JobObject/TOCTOU、精确新包或独立作品视听、官方商业/支付发布通过。完整目标仍为Gate0 → R1独立验收 → 连续R2；模型原收费三轮限制和未通过结果不变。

## 交接

统筹登记RV9-P01延续P2、Integration修复归属及P3仅静态闭合范围。当前冻结源不可中途修改来消失原结果；T11完整交接后另有限复审，不等全历史或重复旧18/83。报告 `docs/reviews/RV9-I9HostReview.md`；过程 `G:/开发测试/Codex/VideoCreatorImplementation/Review/RV9Handoff.json`。

评审只写报告及自身Review。测试运行、费用、真实key读取、产品进程操作、实现/测试/标准修改、构建安装部署均0。全部读取用安全require_escalated路径，未解锁F盘/改ACL。阶段FINAL后释放槽。
