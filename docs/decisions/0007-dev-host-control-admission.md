# ADR 0007：开发host固定管道控制准入

2026-10-08；状态：批准以下最小方案与修正，I7实现及T10独立整入口验证待交。永久架构只写治理，不运行/终止进程、不读key或收费。范围仅Windows现有开发host，不增加通用跨OS生命周期框架。

依据：I7HostControlPlan.md SHA256 `204ffb4ef26d7d98ab4e957c96a0b705efb1c9adddf836c4b592532f39d82f90`已实读。观察DevRuntime.mjs SHA `f76ac93568a013c92174da391ebbed994aa3ca6ad06326e9c6416951fd075e6e`、EngineProcess.mjs SHA `9f4627e0bfea921020dfb3101b905e29f1f184b0fa1c9c0facb5b16521b6113c`是I7端口WIP，不冻结成已验源。T9原19独立绿是固定I5局部机制，不证明本整入口。ADR0005仅API私有接口，不自动批准host控制。

## 固定协议与Windows输入准入

仅 `tools/build/DevRuntime.mjs --control-stdin` 显式启用，默认off；重复flag拒绝。可信父以shell:false、stdio pipe持有本host stdin；后端子管道由launchEngine独立持有。控制不来自HTTP/页面/MCP/模型，自由命令或shell均不接受。不开关不读/检查stdin。

启用前验证Node stdin为可读的 `node:net` Socket、非TTY（isTTY不得为true），并以fd0元数据排除regular file和character device；检查失败或类型不符为固定启动错误、非零，未创建资源不得假清理。**Windows实际合法spawn管道的fstat FIFO/socket/file/character可全部false，不能要求POSIX isFIFO/isSocket为true，也不能只靠非TTY或排file/character即接受任意Readable。** Socket是当前有限Node运行时识别条件，父持管道是信任前提；这不是同OS用户权限隔离、父身份认证或生产安全沙箱。集成提供该Node版本下真实合法pipe/重定向文件/TTY等证据；跨OS另验证，不能为兼容默默放行未知输入。

完整精确ASCII `shutdown\n` 为9bytes，最多64bytes含LF；不trim、不接受CRLF/非ASCII/JSON/空格/部分帧。未知固定诊断无回显；超长丢弃到LF，不能把该帧后缀当合法新命令。EOF只结束reader，不调用stop，不停止/取消制作、改账本/费用或假称后台移交。明确完整帧仅请求自身host已持有的API与Vite清理。

## ready前、并发与自然退出

输入验证通过后，在创建engine并await ready之前建立reader；此前管道已缓冲的字节必须被消费。合法早帧锁存一次请求，不等待完整UI ready才登记。ready后若已stopping，禁止启动Vite/发dev_runtime_ready；API若实际提供ready，仍只是真实API三字段，不能虚构整host可用。若API未完成ready、实际ready失败或资源启动失败，按真实启动失败/提前停止分类并非零，不凭“请求是合法”伪正常。未创建Vite时标not_started及真实无资源范围，不冒充已启动并清理。

重复帧、signal、child退出共用同一stop Promise，两路清理仍由现cleanupRuntimeChildren各自allSettled安排；某一路同步throw/异步reject不得跳另一条。启动/child异常必须粘性记录，不能被并发合法帧覆盖；结果以最终两路真实状态分类，不用第一次请求cause代替后续失败。

明确stop后回收本host控制reader/监听和保持存活的stdin句柄；未知输入或EOF不得清理API。有限等待、ready拒绝/计时器及辅助句柄必须实际终态，不以设置exitCode/打印marker代替host close。不得process.exit(0)跳清理；Windows SIGTERM/taskkill仍为强制行为，不能伪装可信控制触发。

## host/API/Vite的不同终态

修正现dev_runtime_stopped的scope：使用 `scope:host`、`api_scope:api`，保留API真实classification/exit/signal及分别Vite真实exit/signal、清理方式、owned身份完整性。API normal依既有marker1、实际close0/no signal、端口关闭和所有权条件；不借此推断host/Vite/Worker正常。

**现helper对Vite调用owned force。允许此Windows开发host既有清理策略在身份及终态均确认时完成一次受控host退出，但不得称Vite graceful。** 明确控制正常路径的host分类用`controlled`：API normal、已启动Vite实际终止且owned清理确认（或明确not_started）、无启动/child错误，host才可自然exit0；Vite清理方式与实际code/signal/force动作原样保留。这里的controlled是开发host受控清理，不是整个剧组正常结束。计划中笼统“forced一律host非零”应细分：API forced/error、Vite清理失败/身份未知/存活后代、启动或意外child失败均非零；已明确授权的Vite owned_force且实际清理完整可按上述controlled结束。若owner不采用该有限策略，则须真实Vite正常停止机制且另交证据，不能改名掩盖强杀。

dev_runtime_stopped只报告实际清理结果，未确认/error/forced API保持失败分类与完整false，不能无条件成功marker。独立成功仍需父探针观察host真实close0、API及Vite原端口关闭、captured PID+创建身份终态；host日志本身不是退出证明。有限快照/CIM即时复核及TOCTOU限制保持，不新增无范围kill、不碰其他实例/后台Worker/受保护旧进程。硬父崩溃和生产监督/后台移交仍未测，不能发正常承诺。

## owner交接与独立要求

I7集成唯一实现既有DevRuntime及必要`packaging/RuntimeContract.md`，不改后端/业务/测试/SDK/依赖；若发现EngineProcess需额外接口，先给精确接缝，不借本批准跨扩。保持127.0.0.1、strictPort、token只内存/子环境、same-origin标记及资源manifest核验；不注册paid Worker/预算。固定新源hash后运行自身免费整入口再交T10/RV，原I5/T9和端口WIP身份保留。

T10独立：真实合法Windows PIPE/默认off/文件及TTY拒绝；严格完整/非法/oversize后缀/部分/EOF；早于API ready合法停止且无Vite/无虚假host ready；重复及并发错误不洗成功；真实HTML/同源health及foreign/missingOrigin/missingMarker拒绝；controlled API+actual Vite owned cleanup+自然host close、occupied-port原持有者保护、真实启动/清理失败非零、端口/后代与句柄终态。缺资源明确失败，不以模拟/--check替整入口。当前通过0、费用key0；Gate0/R1/R2、框架及三OS/商业准入未冻结，ADR0003收费限制与完整目标保持。
