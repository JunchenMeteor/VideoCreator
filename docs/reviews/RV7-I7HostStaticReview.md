# RV7 — I7 完整开发入口静态评审

阶段 FINAL（静态）。永久独立评审只读固定源码与 owner 普通证据，未运行测试、产品或进程检查。I7 owner 实跑不能替代 T10。统筹新报的 T10 正向终态尚未以正式副本/完整身份纳入本批，后续另批复审；本阶段不等待其他负向批。

## 固定身份与结论

I7Handoff.json SHA `3a77cfdd5e7ce4b575c604b2a03b2c5d36ef98de61574b00185036f3e999ea05`；MD SHA `02e120ec32fea2152a11815c9df3b359994de133894d5f8160bcb8cd2d3b4fab`。ADR0007 `docs/decisions/0007-dev-host-control-admission.md` SHA `86935d5fb24ea9b1f7e5efe758f3cf6eda6dfa34ce8b0641a8347fe7fd21167c`。

| 最终源码 | 实读 SHA256 |
| --- | --- |
| tools/build/DevRuntime.mjs | eaf146f36afc674770efa4d4c65e75ae232e8a96d5b96206d8a5cd4f466265da |
| tools/build/EngineProcess.mjs | 3b6716f93e05122a718e41d4bfbbcf330d706be3b4412f271816729c08eed076 |
| apps/workbench/vite.config.ts | c5cf940ca7aba73896e70ae37a4fd0177fd1d1d0e16370e972c35047d8ff6932 |
| packaging/RuntimeContract.md | 5b3200f5dd5c96aa44abd26045a38a553c29a34a0633d2838d152883f23bce4b |

四源及 I7 声明的21份普通交接/证据/探针源码均核 hash 匹配。EngineProcess 与 I5 历史874d副本逐字比较，仅 origin 的固定1420校验替换为严格 canonical loopback port 校验，其他机制没有文本变化；历史 T9 通过仍只绑定原源，不能自动继承新源通过。

静态发现一项 P2 条件分支和一项 P3 准入顺序差异，均未实跑复现。交 Integration/Architecture，不修改当前冻结身份、测试或标准。端口、PIPE、字节控制和现有分路清理可支持下述有限静态结论；不能签整入口/技术/Gate0/R1/R2 通过。

## RV7-P01 — P2，SIGTERM 异常来源未进入失败判定（静态）

归属 Integration，Architecture确认来源分类。源码链：DevRuntime:84 `stop('host_sigterm')` 不传 abnormal，进入:63 的默认 false；:64 的 lifecycleFailed 不被此来源置真；:77 仅检查 API normal、Vite完整、hostReady/非early及无粘性失败，不检查 cause；:79 仅在 controlled=false 时置 exitCode1。

条件触发：SIGTERM handler **实际可达**，此前hostReady=true，API可normal清理且Vite owned_force真实清理完成，其他错误均未发生。该源码分支可报告 cause=host_sigterm、classification=controlled，且不会置host非零。这是条件源码推演，**当前Windows实际信号可达性、真实OS触发及最终host退出未测**，不能称已复现SIGTERM host0。

ADR0007:21 原文：“Windows SIGTERM/taskkill仍为强制行为，不能伪装可信控制触发。” :27 明确仅允许已授权Vite owned_force的有限controlled策略；其他异常不能被请求来源洗成成功。SIGINT也走同一默认false handler（:83），但该ADR原句特指Windows SIGTERM/taskkill，不能由此擅自断言所有SIGINT都必须非零。

建议：Architecture冻结各来源的允许/异常分类；Integration在stop的来源到异常粘性映射上保证非授权/异常来源不能走controlled0，保留实际API/Vite事实并继续两路清理；T10在精确冻结批下证明可达性与分类，模拟emit/回调不能冒充Windows实际OS信号。源变更须等待当前独立批释放，以新身份复验，不倒填旧结果。

## RV7-I01 — P3，reader 建立顺序与批准文本不同（静态准入差异）

归属 Architecture/Integration。ADR0007:17 精确原文：“输入验证通过后，在创建engine并await ready之前建立reader”。实现 DevRuntime:54 已调用launchEngine创建真实API子进程，:87–109才建立reader，:106才订阅stdin data，:113才await engine.ready。因此实现满足await-ready之前订阅，未满足创建engine之前订阅。

此前stdin字节可能由Node/OS缓冲；owner旧源早帧样本确有提前停止、未Vite/未host ready的记录。该证据不能证明批准的创建顺序已经满足，静态顺序差异也**不能单独推出丢帧、虚假ready或清理残留**。本项严重度P3，暂为准入/实现一致性差异，不冒充生产故障。

建议：Architecture判断创建前建立reader的必要性、可接受的缓冲前提及早字节消费点；保留ADR原要求，未获明确新决定前不由评审放宽。若该顺序是硬要求，由Integration按批准接缝改源，确保早帧被锁存且不引用尚未初始化变量；T10独立验证实际预缓冲/创建/早停行为。任何澄清或修复都使用新hash，不中途消除原批身份。

## 其他静态可支持范围

- DevRuntime:27–31 默认1420，重复/缺值拒绝；正十进制格式配合String(Number(text))===text及1024—65535限制，拒绝前导零、小数、空白、末尾LF/CRLF和URL。EngineProcess:123–124除数字范围还要求match[0]===origin，防止JS正则$的末尾换行匹配。Vite:7–10使用相同canonical端口；:41–44固定127.0.0.1、allowedHosts及strictPort。
- Vite:11–16仅可信进程环境配置loopback HTTP与私有token，:25–33保留同源/fetch-site/客户端marker校验，:49只在server代理注入Authorization并移除marker。token不在VITE_变量或renderer配置。该guard不声称同OS用户隔离，真实请求行为待独立验证。
- DevRuntime:17–24只在显式唯一flag开启时检查可读Socket、非TTY及fd0非file/character；不要求Windows匿名PIPE必须POSIX FIFO/socket。检查失败先于资源创建。默认off不读stdin。真实TTY/未知stream及该Node运行时Socket判定的独立证据尚缺。
- :87–109采用字节比较精确9bytes LF、最多64含LF；超长丢到LF，不把同帧后缀当命令；非法/部分/EOF只给固定诊断，不接受自由命令或回显。:105明确stop时移除reader并pause/destroy，EOF本身不调用stop，不取消/对账制作。已建立reader后的早帧由:65锁存；:115/139避免stopping后启动Vite/发host ready。有限ready等待与句柄自然终态仍由实际测试证明。
- :64在复用stop Promise之前锁存abnormal；:68拒绝pending Vite-ready；:70调用分路allSettled helper，API失败不跳Vite；API异常退出与意外Vite退出保失败。源后续已有stop逻辑不等于SIGTERM来源已经正确分类，见P01。
- :77–79区分scope=host/api_scope=api、API真实normal与Vite实际owned_force。Vite必须有实际成功force action和已验证无剩余身份，不能用该force掩饰graceful；APIforced/error、未知所有权、early/启动失败均不能controlled。owned_cleanup_complete仅是两资源清理事实，early可能true但classification/error及host非零，不能混为启动成功。

## owner 真实证据与缺口

四源固定仅最终canonical owner批可直接归属：原88315工具exit0、16check，合法完整入口host自然close0；API normal0/marker1/端口闭；Vite actual owned_force exit1；父探针记录原API/Vite两个listener明确关闭及captured身份无剩余；四源before/after一致。它是实际owner自查，**不是独立T10/AV通过**。成功scope不会扩大为Worker/费用取消或完整作品。

早期原74884的17check/exit0包含MP4真实代理入库及同源三个403；绑定较早guard/Contract身份，不能归入最终四源的全部独立覆盖。原70558批原raw ended=null，四场景有终态、occupied fixture收尾挂住；按实际自有root创建身份检查后的4PID树force，工具exit1，B5 sibling也forced，不称原整6例绿。自己net fixture纠正后新名仅补两例、11check/工具0，真实非空兄弟HTTP200/creation保持后private normal0；不覆盖历史原失败。末尾LF/CRLF新源两个非法入口子命令exit1/未资源，仍是owner证据。

正向及canonical正向的protected_before/after均空；原“旧22508创建身份不变”check只能保留为空集观察，不能证明旧进程存活保护。原51858端口缺立即afterclosed；第一次.NET followup未确认，后续Node ECONNREFUSED只证明新时点，不能回填原历史。本批未读/终止实际进程，不因缺失重启旧实例。

原raw、有限force动作/实际exit、未终态及工具失败继续保留。源码与日志不是实际close证明；旧68候选/AV0exit3、T6 unknown首raw缺失、Crew真实委派0与三轮限制均不被本批改变。

## 交接

正式静态发现先交架构A5/集成后续处理，当前T10固定源不改。后续正式T10副本、源码/资源身份、实际退出与独立TCP观察另批复审，已报正向不借进本静态结论。完整输入边界、并发失败、实际TTY/未知类型、parent hard crash/JobObject、Worker、三OS/安装/自主视听Bundle-RAG、Gateway商业/支付发布均未由本阶段验收；完整目标Gate0→R1独立验收→连续R2不变。

过程 `G:/开发测试/Codex/VideoCreatorImplementation/Review/RV7Snapshot.json` 保存四源文本、21证据SHA、owner原终态及两个具体静态条目；只读文件工具使用获授权安全require_escalated，未解锁F盘、改ACL/配置、读key或执行测试。仅写docs/reviews及自有Review。测试运行、费用、真实key读取、产品进程操作、源/测试/标准修改、构建安装部署均0。FINAL后释放槽，未签整技术/Gate/R1/R2通过。
