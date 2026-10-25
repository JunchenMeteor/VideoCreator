# RV72 — 固定期限与正常 facts-only 互通证据独立评审

状态：**FINAL / LIMITED_RUNTIME_EVIDENCE**。本角色只读固定源码及原终态证据，进行了标准库字节、JSON、XML、diff 分析；没有执行产品、Test、Cargo、EXE、Win32、DB、ASR、模型或网络，没有读取密钥。没有新生产阻断 finding。

## 结论与关闭范围

- **RV68-P01：CLOSED_LIMITED_RUNTIME**，仅绑定 I50 `resource_authority.rs` SHA `e3455c1358ae60fdf132ce97e12c23a2cbd88b310c2ac19b093ebdd43d19317e` 及 T49 下列六个真实 Win32 I/O 窗口。原 I49 未核期限的源问题与旧证据保留；本次不授全部异常、认证会话、OS 安装或整个操作期限资格。
- I50 原正常 facts-only 互通的 65 条文件映射，以及 T49 修订二两会话各 1332 条映射，支持原对象、会话隔离、正常 RPC、关闭后拒绝与 `not_ready` 拒绝的有限运行结论。四份核心映射逐路径/大小/SHA 核对，另与消费 Peer/Host/index 核对，均无差异，未以数量或 receipt 的布尔值代替比较。
- RV70-P01 的 B34 源级 image 身份修正有本次正常连接支持；RV70-P02 部分源修正与 **RV71-P01 重复中断/异常解栈安全 OPEN** 保持。正常批没有注入 B34 重复 interruption、未完成取消或 completion 查询失败，不能据此关闭。

## 固定身份和读取范围

完整输入身份在 `Codex/VideoCreatorImplementation/Review/AuthorityRuntimeEvidence-RV72/RV72Snapshot.json`，必要 161 个原/副本路径末核 changes=[]。普通库存为 native 39、I51 19、I50 40、T49 Python 修订二 24；按 manifest 原/副本声明身份核普通副本的实际 bytes/SHA。另被动读取十份原大 raw 和三个实际 B34 消费者，未复制巨大 mirror，未物理遍历 1332、173、175 项完整工具/环境。

关键绑定：

| 对象 | SHA-256 |
| --- | --- |
| Native Handoff MD | `eeca0a849c623d46fba1027f5234384fce44c3bafa53b9ac22060555934b3794` |
| Native ordinary manifest | `1c7b7885f39fd0e1e1f9c621e61e6defbba8a1e3fcdba5ce1e6f192f5ca11596` |
| I51 test EXE | `ff302954f3fa891116ecb6811da38f7258501105f4416ab8cad7fa2d5cd2a0ee` |
| 实际六 case Rust module | `ec17c8f028d2641bc8c5283c634a4302ce8604940c4ba2a2575414c06f3de11a` |
| I50 ordinary index | `318a60f941baa20ca1a1ddb3e2bb39c9ba2f1c8a8f448e7a6e7f5e465703effe` |
| T49 修订二 Handoff MD / JSON | `f2a71b3059f10501573cd07f4528294fd26044d12a12a9dbd4abaab41077f133` / `024a2bc970138b91fbcdf680020d6127e50dfc9b12fc633e32ac4a57da968832` |
| T49 修订二 ordinary manifest | `c50d2fd40e918e86999a1d121f044071d5b65478f94a086f82b4585768c71768` |
| 原 independent full-map receipt | `d9ce5f0a9029e51a7efbd2b2ee9641bc827defb144646b1be89c61cc850efd96` |
| 实际 Python B34 Win32 客户端 | `bebb6a0ef7e3763436380489e845cd53215ebe4d4fb839bdbe6cc63d41d6cc13` |

精确普通根分别是 `TestDevelopment/ReviewHandoff/T49NativeDeadlineExecution`、`TestDevelopment/ReviewHandoff/T49PythonFactoryRevisionTwo`、`Integration/NativeDeadlineTestBuild-I51/Ordinary`、`Integration/PythonAuthorityAssembly-I50/Ordinary`。所有根位于 `G:/开发测试/Codex/VideoCreatorImplementation/`，没有混入当前 B36 或其它 WIP。

## Native 六项实际窗口

`OwnSource/NativeDeadlineCasesT49.rs` 使用 `super::*` 调用同一真实 core；原完整生产前缀 25765B 字节不变，编译 view 仅追加 `#[cfg(test)]` 与该固定绝对 module 路径。独立解析 I51 Cargo 原 stdout 的 30 个 compiler-artifact，唯一 test-profile executable 原 executable 经 I51 fixed_executable 再到 T49 manifest 的两层普通副本链准确相同（fresh=false）；不能把普通 CommandReceipt 的 artifacts=[] 当作无编译或把 compile0 当 run0。

| case 源行 | 实际条件与独立判断 |
| --- | --- |
| 45–60 expired-prefilled | 原 real Instant 过期后拒绝，原 buffer 不变；用新期限读取同一 pipe 得到原八字节，说明旧队列未被消费。 |
| 64–89 completed-late | 原 ReadFile 实际 997；原 event 实际 signalled、GetOverlappedResult 实际八字节成功，但首次完成观察晚于期限仍拒绝。 |
| 93–115 pending-cancel | 原 ReadFile 实际 997；期限后 CancelIoEx 及原 completion 链实际终态 995，排除 996；原 event/overlap/buffer 活到终态。不能凭取消请求布尔值推断终态。 |
| 118–138 prefix/body | 已排队 prefix 成功，延迟 body 使用同一原期限并拒绝；没有读完 prefix 后另给新 body 期限。 |
| 142–164 chunk | 首 65536 字节实际进入原 buffer，延迟第二 chunk 拒绝，后 65536 字节仍为零；同一原期限。 |
| 168–178 already-connected | 实际 client 已打开，过期 connect 被拒；新期限可在同一 pipe 连接。 |

原 stdout 六名字全 ok、JUnit 六节点 0 failure/error/skip，suite **2.21s**；fixture 的 elapsed 包括 sleep/join（例如 360861/900858us），不等于独立 case 持续时间。实际 EXE PID56508/creation `2026-10-09T16:19:49.2379475Z`，自然 exit0；原工具 8bbf13/0、双原字节流 EOF、无 force/sticky/error、25 inputs 原运行 before/after 无变。六个 raw pipe 场景 **没有认证 session、OwnedProcess/Job 或生产工厂启动**。

固定 core `complete` 94–106、`connect` 111–112、`bytes` 114–121、`receive/send` 123–124 给所有已测试同步/完成/分段路径期限核验，且取消后保留原引用。没有验证整个 authenticated request + file hash + reply 的总时间上界，也未验证无限取消失败、严重 OS fault、所有 peer 拒绝分支。

## I50 原正常 Python 事实互通

I50 `ActualPythonChannelRoundOne/Execution` 原 receipt/raw/native report 中：native parent57472/creation `2026-10-09T15:52:36.4987578Z`，physical Python62000/creation FILETIME134360347570091894；实际 direct parent、双方自然0、Job 空、双字节 EOF、无 force/sticky/errors。原 65 配置 map（61 固定 B31 engine 源加四项资源）与 TrustedPythonInput、HostLaunchInput、actual Python map/expected map、native 镜像逐字段相等，无重复路径。七 owner checks 为有限正常 facts-only 观察，不是七独立产品测试。

原 `PythonChannelHost.rs` 45–74 保留实际 process、stdout/stderr 原 File、reader threads，先 actual child exit + `AuthorityOwnedChild::terminal`，再 EOF/join 与 session 结果，最后 held guard；`resource_authority.rs` 167/178–200 核实际 named-pipe peer、原 HANDLE PID/creation/Job、映像/SID/SHA，保 guard 至原 child/Job 终态（175/226–229）。`platform.rs` 167–185 使用实际 GetProcessTimes、IsProcessInJob、QueryInformationJobObject，而非 receipt 自填 PID。

独立 native image 预先固定于 trusted build 输入，不从 locator 回包授信。普通 local drive 的 wire 表示与原实际文件身份应分别核；本次只支持正常路径，未穷举 UNC/device、替换文件及 PID 重用反例。`server_session_end=authority_io_failed` 原样保留，是断开后的 session 结果，**不能写成 clean protocol close**；事后 PID 不存在不能回填原退出观察。

## T49 修订二真实两会话与 13 项

SessionOne native6016 → physical Python2432/FILETIME134360390242133503；SessionTwo native28072 → Python29468/FILETIME134360390700159500。原 wrapper ec3d31/session11675 → 08b373 自然0；两原 native/child 均0、Job 空、parent 与 child 两字节 EOF、无 force/sticky/error，原运行 1332 after 无变。JUnit 13 节点为 6+7，0 failure/error/skip，没有虚构未记录的 case 时长。

独立对每会话 fixed index、Consumed PeerInput、HostLaunchInput、actual Python actual/expected map、native mirror actual/expected map 逐项比较：各 1332，ii=json.loads(Path('G:/开发测试/Codex/VideoCreatorImplementation/Integration/NativeDeadlineTestBuild-I51/I51OrdinaryIndex.json').read_text(encoding='utf-8'))
for expected in [ii['fixed_executable'],ii['original_executable']]:
 actual=ident(expected['path'])
 if (actual['bytes'],actual['sha256'])!=(expected['bytes'],expected['sha256']):raise ValueError('selected compiler EXE changed')
 if not any(str(Path(r['path']))==str(Path(actual['path'])) for r in s['records']):s['records'].append(actual)
mismatches=[]，strict int bytes（布尔不当整数）、完整 SHA、重复路径拒绝。`RV72RuntimeFacts.json` 保留逐图结果及原 raw hash；全部两会话配置 map 的独立 canonical 摘要为 `1d18bc8b4be0203be0eba7eb40c3fa1a4a8cc67804dbaf74007f56d90c80835f`。这个摘要按本评审的 tuple 序列算法生成，与 Test receipt 使用另一 canonical 格式的摘要不混比。Native 镜像其余实际字段和完整方法列表也与 child 原报告一致。

实际 peer 105–119 核 `_observations[id] is original`；replace 等值副本本地 409，`_seq` 不变，原对象再次 RPC；两份调用日志分别五/六次 `_exchange`，只作为被实际源断言绑定的调用证据，888068/888675 次 profile 记录不是测试数量。第二会话 PeerInput 的 prior ID 确实来自第一会话原 Python raw，再用真实 `_exchange` 获得 remote409，并使其当前连接 invalid503；不是任意造 ID 的本地拒绝。

实际 `not_ready` observe503、closed503、Evidence constructors=[] 与 originals={} 明确分层。固定 B34 `held_authority.py` 223–224 完整 map 校验、265–274 强原对象/epoch 与 RPC 链；`native_installation.py` 50–61 在 not_ready 阻止 issuer 调用，132–148 实际连接器，但 151–181 完整 Owner factory 未被本批调用。不能将 facts-only connector 叫完整 Owner factory、安装资格或 qualified Evidence。

原正常首批自然1完整保留，SessionTwo 未执行、原 13 未达。实际失败位于 Test audit 拒绝 keyring 导入链的 `socket.gethostname`。独立原/新版 peer diff 仅允许此本地 hostname 事件，仍拒其它 socket/subprocess/SQLite/spawn；runner 只更换唯一新批/index 名，13 checks、90s native/120s outer 观察期限和无盲 force 策略不改。首批 server deadline/parse EOF 不被新批0洗掉。

## 限制、后继及本角色终态

不授 RuntimeBinding、真实 Owner 管理/secret、API/MCP/Worker 全入口、正式 PreparedLaunch/bootstrap/loader 全闭包、真实模型/ASR、安装/发布、clean Windows DLL/VC floor、macOS/Linux 或 R1/Gate 通过；完整三OS R1 独立验收后连续 R2 不缩。实际 B34/B36异常持有与重复 interruption 必须另批固定源及安全 fault 证据；本轮不读它们热源。

本角色解析器首轮 `4e5c47/exit1` 是 `Execution` 子串误匹配两个 receipt 的定位歧义（产品/Test 未运行），原脚本和失败记录保留；精确 `/Execution/` 修正版 `80a7cc/exit0` 完成纯解析。`976255/0` 输出中段截断，所需两段已 `133181/0` 定向补读，不声称截断正文全读。末必要编译来源解析 `74829c/0`。正式 finalizer 原 `f1a7e7/1` 误把 T49 的中间 I51 ordinary EXE 路径直接与 Cargo 原 target 路径比较；原脚本保留，`6ff445/0` 与 `dc5114/0` 定向读出两层 provenance 后修正，仅评审 artifact 逻辑，未重跑 Test/产品。输入末核无变，读者释放；最终写入工具的真实返回由正式交接一并提供。
