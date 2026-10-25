# RV51 — I37/T36 实际消费者有限评审

结论：固定 I37 编译来源与 T36 后续独立18项消费者机制运行相干，支持本片 LIMITED_MECHANISM_PASS，未发现新的本片阻断。不授 OS/微软签名/真实 native child/Job/安装、实际 ASR、147+24资源、VC floor、完整产品或 Gate 资格。历史红不改。

## 固定输入与身份

过程：G:/开发测试/Codex/VideoCreatorImplementation/Review/NativeConsumerExecution-RV51。
普通根：G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T36NativeConsumerExecution。

42份普通副本、正式件、编码旁件及治理共59路径实际匹配，前后0漂移。自有有限解析250项核对一致；没有执行被审 EXE/helper/Cargo/Test/产品，没有读取或重新 hash 大 fixture、5573工具或999运行时。唯一 EXE 的身份由固定 compiled/原输入/实际argv收据互证，本 Review 未重新读取 EXE 字节。

| 固定件 | SHA-256 |
|---|---|
| T36Handoff.md | d36bc61a745b32cb60e994433d289b057295e17923e29e48496f83851ef8ecda |
| T36Handoff.json | 55642caf5f9c60daf6508a6931a14d4d4f6d898dbdf936387faf5e0f5686a829 |
| T36HandoffSnapshot.json | 6fc179cc9809031f1676a49c776d465da6ef04100022450968872ebadfc1ed30 |
| T36OrdinaryManifest.json | 25ef453b88ad485eb5d15c8f8b6a219a7316fcef4f478f2bbf9b02633b78a2db |
| 原 T36InputPlan.json | dc66e7db453e0832b4d022ef417750e64ebcd8ca845482be86ef33ed003846fd |
| 原 RunT36.ps1 | 4e2295fbc781598b42e579561aa00e67bd0bc7579405b7609ba8745486369a4e |
| 唯一 EXE（1849344B；记录身份） | 398215c83f41b1a0c7a957b338a9b220b7c641f67248f23e5e9023cd0cb545de |

完整路径、字节数和前后核见 RV51InputPins.json / RV51SourceAfter.json。原正式根 NativeConsumerFaults-T33 的4件与普通副本保持相同身份，目录中的 T33 历史名称不改变本次 T36 阶段。

## 编译身份和真实源码链

I37 原 dd0e1d/session67118 经324daa记录实际 terminal0；唯一 cargo test --lib --no-run --offline --locked / win64-msvc 的原收据自然0、双 EOF、无 force/timeout/input_changes。保存的 compiler stdout 有唯一 test-profile executable 和 build-finished success=true，路径对应上述唯一 EXE；原 stderr 保留2条 warning diagnostic 和1条 warning summary，Finished19.23s。

普通 Source-15-OrdinaryBuildSourceIndex.json 的11源/config与预运行保存的实际正文逐项匹配。对 windows_native_sources/platform/load_policy/resource_pins 四完整原 prefix 的字节长度/SHA和追加 cfg(test) suffix 独立复算一致；三个 test child 原文保持，未抽取影子 guard/budget。lib.rs 直接接四模块，仅 library，没有 desktop main/engine 的运行覆盖。I37 原 no-run 状态继续保留；18实际运行证据来自之后 T36，不能回填为 I37 当时已跑。

共享消费者链实际为 Source-01-windows_native_sources.rs:38–66 的先 metadata/reserve 再有限读取、失败不退 reservation；collect 与 collect_for_test 都调用同 collect_from:324，observe:359、carrier:396、recheck:413 和 bind_before_resume:76 共用同一 Context/Mutex预算。Source-02-platform.rs:25–46 的真实 PostCreateGuard 保持 exact Created，只有 terminal=Ok(true) 且 active=Ok(0) 才释放。Source-03-load_policy.rs:44–61 的 production/test 两入口都进入 launch_using，保留真实 PreparedLaunch/ResourcePins/Context 至清理完成；fixture_only 在真实 launch_owned 前拒绝。ResourcePins 使用实际持有文件/祖先目录句柄，观察 Weak 的对象是这个真实 guard，未用 DropMarker 替代。

## 18项实际支持范围

从三个固定 child 的 #[test] 函数独立提取8+6+4名称，与原 stdout 的18个唯一名称、全 ok、原 receipt 和映射逐项一致。准确逐名/源行/SHA见 RV51FactsCheck.json 与 RV51TestSourceMapping.md；不是仅凭测试标题判覆盖。

| 组 | 真实消费者断言与透明边界 |
|---|---|
| collector 8项 | metadata失败先于reserve/read；short/partial/error/size-change不退预算；实际80MiB+80MiB文件在第二次read前拒绝；完整collect→carrier→bind同预算与二次bind拒绝；8个真实Rust线程共享128MiB账户；identity/host端口变化和实际PE字节篡改拒绝；signature失败及真实catalog读16B后error，下一target沿用原预算。File/PE/catalog/Mutex/线程是真实；签名、身份、版本、loaded-origin由 FixtureSource 返回。 |
| lifecycle 6项 | create失败不宣称创建/清理；assign/identity/hook/resume error和unwind走同 Created 清理；UNKNOWN/非terminal/live-descendants与失败termination request不能提前释放；成功只转移 exact Created/stdin。调用真实 owned_launch/PostCreateGuard；Created/Sink/terminal/active/terminate 是 ScriptPort，不是 Win32 child或Job。 |
| PreparedLaunch 4项 | assign/identity/resume、写失败/partial binding和fresh source拒绝时，真实资源/context保持到清理完成；unwind遇UNKNOWN/descendants仍保持；成功返回同 PreparedLaunch 与有界ASCII绑定帧；fixture调用实际 production入口先拒绝。实际 ResourcePins/VerifiedContext 与文件被使用；原生生命周期仍经透明 ScriptPort。 |

原执行工具 c2c666 无session，实际自然0（8.3231493s）。Rust原 summary为18 passed、0 failed/ignored/measured/filtered，6.62s。原 stdout SHA 00461b7df631f6887b002db6c045ae29d699f46a6719fe303a746f258c0f3c6c，stderr SHA e626374c14914f43a6bb03c3bdbd862b35453373002f5331e1016613b51ff316。stderr保留5次受控 panic：binding、assign、identity、hook、resume，对应两组 catch_unwind 与后续清理断言。没有删 panic 日志，没有构造 JUnit 代替 Rust 原结果。

## 原 Process、输入和编码边界

实际 test child PID51236，creation2026-10-09T06:17:36.1475169Z；原持有 Process 的自然 terminal、双 bytepump EOF、forced=false、timeout_sticky=false、owner_errors=[]、termination_attempts=[] 有原收据及工具终态支持。RunT36.ps1 在所有 mkdir 前验证全部祖先物理边界、固定输入和精确 fixture 字面；成功 Start 后所有观察/receipt/pump异常在同 finally 收口，未换PID lookup。原闭集argv/env及源码正文预运行保存。此正向运行没有实际注入启动器超时/pump/身份观察故障；那几支只有静态逻辑，不冒称实跑。

原23输入 before/after 字节相同，SHA cd771e84fc7fdb5bb84e0c0f125e5a77a9c91d137b15e5d56e6b053b2bfb518f；21正文副本与各原pin一致，批准Plan另核未变。same Process+真实双EOF只支持该原直属进程/输出终态，不能证明未知后代原子Job containment。Source/Lifecycle ports不能替代真实WinTrust/System32权源或Job会计。

原批准Plan、部分JSON/receipt的 CRLF 字节保持不动。三CanonicalLf sibling分别仅做 CRLF→LF（原281/365/511个CRLF），JSON语义完全一致、新SHA不同、executed_as_replacement=false；不能把衍生LF Plan说成曾运行。编码旁件属于呈现追加，原42 manifest的冻结身份不被替换。

post-run inventory只记录129文件的名称/logical size，总211903813B。约202MiB是计划估计；没有读取/复制/重hash大fixture，没有测实际磁盘blocks/RSS，set_len不代表已经证明稀疏或资源上界。

## 限定结论、缺项和原记录

本片可以登记固定18消费者机制实跑及相干编译来源通过。没有新本片阻断，没有因机制端口返回模拟微软信息而给真实授权；fixture production拒绝阳性尤其不能被当作真实native启动阳性。

系统collector/微软证书与撤销事实、完整DLL闭包、真实native child及原子Job、147+24/8VCfloor、完整ApiRuntime/安装/实际ASR/三OS/作品/Bundle/Gate均未在本片证明，后续归Integration和Test按独立新批固定输入、事实端口和实际资格验证。不得扩大本片 source/lifecycle PASS。原 T33“18未运行”、I37“只编译未运行”、T30两红、T34首红均保留；完整R1三OS独立验收后连续R2不缩。

自有首轮解析 e6ca82 有1项通道假设差异（stdout warning count预期2，实际0）；原 RoundOne脚本/Facts/Checks/Snapshot保留。随后135f9c仅从原两raw确认stderr2 diagnostic+1 summary，纠正自有计数为250项一致，没有修改Test、期望、阈值或重跑消费者/编译。原测试结果不因此改变。

全部固定输入reader和工具实际终态、live_handles=[]、生产freeze=false。正式文书写入工具实际结束后FINAL释放，不等待资格外环境或其他活角色。
