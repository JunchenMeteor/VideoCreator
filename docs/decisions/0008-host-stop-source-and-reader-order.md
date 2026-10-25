# ADR 0008：host停止来源与reader顺序窄纠正

2026-10-08；批准最小纠正，I9实现与新源独立验证待交。永久架构，只写治理，不实施/测试/操作进程，不改标准，无费用/key。补充0007，不倒改其原字节或旧收据；不扩建JobObject/通用跨OS框架。

依据：实读RV7报告SHA `c6a4c792b0c05e33e7982518613b943031b2d8665f050685464cd4854d457081`、Handoff SHA `5095c7ae1b1b81bc99ee1bc0fda6bcf0787d41654f9059e4d901eb2bd76318ea`、当前DevRuntime SHA `eaf146f36afc674770efa4d4c65e75ae232e8a96d5b96206d8a5cd4f466265da`均匹配。RV7-P01是默认abnormal=false使SIGTERM条件可能controlled0的静态推演，Windows真实触发未测；RV7-I01是launchEngine先于reader的顺序差异，未证明丢帧。统筹交T10原1+4+13合18pass终态并释放冻结；其中真实早帧非零且无假Vite/hostready不否定静态顺序差异，也不证明signal/真TTY/并发异常。

## 仅允许的成功来源

`controlled`且host自然exit0必须由**已准可信stdin的精确完整host_control帧**触发，满足0007的ready、API normal、Vite实际owned清理确认及无粘性异常。cause只记录起因，不能替代可信来源条件；日志/设置exitCode不能证明资源或真实退出。

SIGTERM按0007强制/非控制来源保持中断/异常、非零，即使API和Vite随后实际清理完整。SIGINT在本有限开发host也明确规定为中断来源、非零；这是本ADR补充来源政策，不宣称0007原文已规定所有SIGINT。可继续调用同一两路清理，保留API/Vite真实exit/signal/marker/ownership，`owned_cleanup_complete=true`可作为独立资源事实，但不得将host分类改为controlled。signal不会调用Production cancel/pause/费用修改。

启动/ready失败、意外API/Vite退出及清理失败维持异常。EOF/非法输入仍不调用stop。每次stop调用先锁存当前异常来源/失败，再复用同一Promise；合法帧先到、signal或child异常后到不得洗成功，不额外重发控制或扩大清理范围。最终分类在已确认的受控清理终态汇总粘性事实；原合法帧所导致、已明确授权的Vite owned_force仍按0007区分，不误当意外child失败。真正后来的OS强终止仍保留实际exit/signal，不可保证异步清理运行。

## 不放宽reader创建前顺序

0007“在创建engine并await ready之前建立reader”保持硬要求。完成纯同步参数/管道准入后，先初始化可记录pending控制/失败及reader回收的最小状态，安装reader，再进行可能创建资源的异步准备及launchEngine。reader不得直接引用未初始化的engine/stop变量；完整帧在engine尚未存在时只锁存pending请求，非法/EOF按原协议处理。

若准备阶段已锁存合法早帧，禁止新建API/Vite以完成一次无意义停止，有限结束已开始的准备、回收本host reader/句柄，记录`stopped_before_ready`/非零与API/Vite `not_started`，不发API成功marker或hostready。若请求发生在API已创建而未完整hostready时，按原早停路径清理实际已有资源、跳Vite/hostready、保持非零。检查pending与创建后处理必须形成明确交接，不能忽略预缓冲字节或把已锁存请求重置。

合法早帧的静态前序和真实Node/OS消费点分别取证；原实现的缓冲样本绿不授权放宽顺序，顺序差异也不倒填丢帧/残留。所有ready和资源状态仍来自实际创建/退出；未启动不是已清理成功。

## 唯一owner及下游

I9 Integration唯一修改既有`tools/build/DevRuntime.mjs`及必要`packaging/RuntimeContract.md`：最小来源异常映射/可信成功条件、创建前reader及pending接缝。不改后端/业务/测试/SDK/锁/标准或EngineProcess接口。保持0007字节9/64、Windows Socket准入、EOF、同源/token/资源核验、有限PID身份及TOCTOU限制。T10旧批已终态仅解除该批冻结，新源另hash，不覆盖旧18绿、owner失败、RV7或旧包。

T角色独立新源验证合法受控路径与原早帧非零/无fake ready、真实预缓冲及创建顺序、文件/非法/EOF、异常来源粘性与并发次序及实际资源终态。Windows OS signal必须有真实受支持触发和handler可达证据；emit/回调注入只能验证分支，Node kill/taskkill父进程不能冒充该handler被调用。可达性仍缺时明确未测，继续可执行免费验证，不能以此改协议求绿。RV分别复审P2/P3，架构批准不直接关闭它们，不替验收。

完整Gate0→R1独立验收→连续R2、ADR0003三轮/收费边界、三OS/商业和作品缺口均保持；本轮没有产品运行或新通过声明。
