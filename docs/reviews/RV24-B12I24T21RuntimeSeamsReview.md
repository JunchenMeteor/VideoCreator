# RV24：B12 / I24 / T21 固定运行接缝独立评审

状态：FINAL，SOURCE_PREPARATION_REVIEW_ONLY。结论：三项静态 P2、一项条件性 P3，均归 Test；不批准 RuntimeBinding、业务批启动或产品通过。不修改实现、测试、标准；不运行产品/测试/ASR/模型，不访问网络、读取密钥或发生费用。只审固定普通副本，未读取 W14/B16 等活跃生产源码。本轮不是全历史审计或独立验收。

## 固定身份与读取边界

99 份普通副本结束 SHA 与开始及声明全部相同：B12 36、I24 Host 18、I24 SharedSupervisorV2 9、T21 36。T21 的 36 是 25 输入正文、9 静态证据、2 正式交接，不能混称 36 个新业务测试。另 20 份固定正式文档/原收据身份无差异。完整原路径、普通路径与 SHA 见 [RV24InputPins.json](G:/开发测试/Codex/VideoCreatorImplementation/Review/RuntimeSeams-RV24/RV24InputPins.json)；本报告链接均指固定副本。正文已保存于 RV24Snapshot.json；语义审查只覆盖下文相干调用链，不能因归档了全部正文就称全部依赖通过。

| 输入 | SHA-256 |
| --- | --- |
| B12Handoff.json | d97ce274614e9f5945edf01ce6e112ff6b00402e805709719ba858f91b74da7f |
| B12SourceSnapshot.json | 04ff336eb1b95809453db90585916c9338ee6b22b79e8d0212d828ff7ac67d68 |
| I24PhaseHandoff.json | e631dddeac1a2216fa6f3266ce9f7707652269816a3890339c46ca5d77c08ac4 |
| I24HostSourceFreeze.json | e429edade7b836d5ef5dfe8ba4c09ce8e3f82bbfda5560b8e56d673d9c13e4fb |
| SharedSupervisorV2Freeze.json | 94768be471b156d59eaba90bbcaf878fc1eba8fad13cf49426eca8f48240712c |
| T21PreparationHandoff.json | 40833879ba70ba397a9c66f2d88511fa76cb5fcbd25e753f6f9f8fe6be4387e0 |
| T21OrdinaryCopyManifest.json | 7c327afc89392c6e14b05f7de85833632bece2e1b34fec6429814e7cf6ce011f |
| ADR0005 | 528329d3738ebf3aa421d5fd4cf1f2493d81e450e79cbcaf1f8f9818186c9991 |

## RV24-P01：P2，停止 marker 消费了错误通道

归属 Test。固定 [Source10-t21_owned_driver.rs](G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T21Preparation/Source10-t21_owned_driver.rs:65)，完整 SHA b488b542b69f84bebcf568bac3dc9093f29e4782bb337271009a2f896e7416ba。

65–67 行把 marker_event 交给 stdout 的 capture，而 stderr 的 expected_marker 是空字符串；79 行仅用 stdout reader 的布尔值生成 marker_seen。36–49 行还只校 event，没有角色/scope 或该角色需要的身份/清理字段。

相干固定后端链：
- [cli/lifecycle.py](G:/开发测试/Codex/VideoCreatorImplementation/Backend/MediaRegistration-B12/FinalSourceCopies/services/engine/src/video_creator/cli/lifecycle.py:201)，SHA a9ee0861937166810bbd1d464472b7f7e526dacea8c0966b21b45eff1e82331a：201–202 的 api_stopped 写入 stderr，事件及 scope 固定。
- [cli/worker_lifecycle.py](G:/开发测试/Codex/VideoCreatorImplementation/Backend/MediaRegistration-B12/FinalSourceCopies/services/engine/src/video_creator/cli/worker_lifecycle.py:104)，SHA 33024611acffc99fa9b1196def85f8b092f62a99123a09ddd460b5f8a3d3e292：104–110 清理判定后 worker_stopped 写 stderr，包含身份与 cleanup_completed/process_exit_pending。
- [integrations/mcp_stdio.py](G:/开发测试/Codex/VideoCreatorImplementation/Backend/MediaRegistration-B12/FinalSourceCopies/services/engine/src/video_creator/integrations/mcp_stdio.py:132)，SHA 7d6bbf124f5d130a9f4daec328760a0cce5564d4184b2ee12e7572812932d635：132 的 diagnostic 经 22 行写 stderr。MCP stdout 保留真实协议帧。
- [ADR0005](G:/开发测试/Projects/VideoCreator/docs/decisions/0005-private-engine-control-lifecycle.md:21) 21 明定 stderr marker；31 要求 marker、实际 exit0、端口关闭及自身后代结束共同成立。

最小条件：真实子进程只在合法 stderr 发 stopped marker，stdout 无此事件，实际自然退出0且 Job 空。该 driver 仍返回 marker_seen=false；反向 stdout 伪事件又可能被接受。这里是静态源码结论，Rust driver 尚未编译/运行，未证明任何真实 OS 停止失败。

整改边界：在固定、按角色批准的 stderr 通道独立解析严格 marker；缺/错 marker、stdout 伪 marker 均保留负例。不得在两通道宽匹配任意 JSON event。实际退出码、自然/强制、Job 后代、API 端口分别观察，marker 不替代进程退出。

## RV24-P02：P2，真实 MCP 正向调用没有 per-call 授权

归属 Test。固定 [Source01-t21_process_cases.py](G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T21Preparation/Source01-t21_process_cases.py:162)，完整 SHA 9e6097e84ff0eeb7c54c2d41370c9bb50b33f0eae6f47678092c4ca324aac161。

162–163 的 tools/call params 只有 name/arguments，经原 request 原样发送；170–191 的 actual_mcp_host 却要求 bundle_get 返回 not_found、actor 注入返回 invalid_request。固定 B12 [mcp_stdio.py 105–110](G:/开发测试/Codex/VideoCreatorImplementation/Backend/MediaRegistration-B12/FinalSourceCopies/services/engine/src/video_creator/integrations/mcp_stdio.py:105) 先读取真实 request_context.meta.authorization 并校验私有 Bearer；没有该字段时在业务/参数检查之前返回 mcp_session_invalid。原字节写入接缝没有补授权。

最小条件：合法私有 session token 已配置，initialize 成功，而此 client 发送目前无 _meta.authorization 的 tools/call。结果是授权拒绝，达不到两个预期业务错误。桥尚未绑定，未实际运行此反例；原 B12 owner 的已授权调用不能替它证明通过。

整改边界：正向由批准的私有 session token handle 构造真实 _meta.authorization，禁止把 token 放 arguments、日志、收据、持久化文件或 secret hash。无/错 auth 负向保持原字节，桥不得自动补 token 或改变服务授权门。授权、工具参数、真实 service 结果分别留证据。

## RV24-P03：P2，未知 Worker 控制帧被错误要求自然非零退出

归属 Test。同 Source01 完整 SHA。固定 [235–253 行](G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T21Preparation/Source01-t21_process_cases.py:235) 将超长帧后 EOF、invalid LF 帧标 expected_early_exit=True，随后等待实际非零 exit、forced=false 与 Job 空。

固定后端调用链：
- lifecycle.py 36–60：只精确 shutdown LF 返回停止请求；未知/非ASCII/超长/未完成帧固定诊断并丢弃；EOF 清除未完成帧。
- worker_lifecycle.py 59–68：EOF 只结束 reader，只有 parser 接受的帧设置 requested；没有未知帧终止 Worker 的分支。
- [application/media_registration.py](G:/开发测试/Codex/VideoCreatorImplementation/Backend/MediaRegistration-B12/FinalSourceCopies/services/engine/src/video_creator/application/media_registration.py:230)，SHA 300052f16a9f4486d6263a7985fc4d425f7ff4bca1ef864f847a8d318d1e8b3b：230 的循环由 control.stop_requested 决定，无 lease 时 246 wait 后继续，presence/heartbeat 仍有真实循环职责。

ADR0005 18 原文：“未知/非ASCII/超长/未完成帧只固定诊断，不回显内容，不停API或改账本”；19 原文：“只表明控制通道失联，结束reader，不推断停止/暂停/取消Production或API”。这是 API 原协议，B12 Worker 沿用同 parser 和 EOF 语义；不是凭 ADR 推断已经完成独立 Worker 验收。

最小条件：已注册、空闲的持久 Worker 收到上述无效帧。固定实现拒绝并继续存活，candidate oracle 却等非零自然退出，随后超时或走 owned Job 清理。这是静态 oracle/实现协议不一致，未实跑，不称 OS 红。

整改边界：原 invalid/超长/EOF 字节负例保留；与已批准协议一致地独立观察固定诊断、真实身份存活、fresh heartbeat、Run 未取消以及 lease 状态。reject 不能被吞掉来换绿。若要改为终止策略，应由 Architecture/Backend 单独批准和实现，不能为测试盲改生产 exit。

## RV24-I01：P3，省略版本的新请求与旧存量版本被混为一类

归属 Test，条件性。固定 [Source04-t21_v03_cases.py](G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T21Preparation/Source04-t21_v03_cases.py:15)，完整 SHA 62df7d6829d15b81c30a61baff99cf92d6cd34c1a0bf68dccb1639a1dab84e1c。

fixed_request_versions 的15允许 legacy.request_format_version=None，16却以新身份提交，20要求持久化值仍等于输入None。固定 [application/engine.py 225–228](G:/开发测试/Codex/VideoCreatorImplementation/Backend/MediaRegistration-B12/FinalSourceCopies/services/engine/src/video_creator/application/engine.py:225)，SHA 8a3251ee6a6a25e3d8945e77a3203b91ef3cc074d861db2a22f1415617a8e737：_resolve_request 明确仅新身份填入 SCHEMA_VERSION；162–181 的旧存量幂等分支另保原 body/hash。

仅当 V03-01 的实际 legacy fixture 省略版本时触发；fixture 未绑定，不记 runtime 失败。测试应分别核旧存量无迁移/原 hash 不变与新身份省略版本解析为 0.2.0-candidate，不改 Backend 默认或以显式版本 fixture 掩盖省略版本范围。

## 有限可支持范围与原失败

B12 源码没有新建第二业务队列：真实 presence、现有 claim/lease/fence、succeeded Step 与 settled Operation 是 authority；media_registration 166–194 从实际 committed Asset/Step/Operation核四份 master，不让调用方直接赋质量或伪造 master。缺创意上游/模型路线等必要 capability 时 park waiting_user，不能称自动成片。235–241 的 unknown 查询只报告原事实，没有自动重新提交、归零收费或 Run 复活。实际未决对账适配、完整媒体 drain/cancel/deadline 传播与真实制作仍是缺口；未读取 W14 来填补旧身份。

两轮 owner 红保持：
- 原 OwnerBatch CommandReceipt SHA 8a3b61d536d437acde9e6571b8c6e870618152e98b14039c165ce3ba60c89baf：exit1，WorkerLf wrapper PID47108 与实际 worker20732 的早期断言失败；wrapper forced=true、原 owned_descendants 非空。后续 CleanupObservation SHA60cb81e32cbf644221ddc9cd629cf03c8768f40ac98b5905e1bb6974ea986bec 只记录原 PID 当前不存在/OpenProcess87/退出码null，不能改判自然退出。
- 原 OwnerMcpBatch CommandReceipt SHA18c16280aef32a76fefb73b005d103d5d9fb856728ea2f2189776d5b7b6d074e：exit1，9 检查中8绿；第9误以为新请求仍缺 request_format_version。真实生产只是默认0.2 queued/null，无成片。wrapper53288 exit0与读者结束，不等于其子37892实际自然退出。
- CompletionObservationReceipt SHA5b5ac0ab4696dc6d21bd7a6c4dd3e8163f073c9d9122f5038c9e84d9b0fae818：原 exit1、ledger1 queued/Op0/published0/presence0保留，原37892/12356后来不存在且实际 exit=null。cleanup_completed=true/process_exit_pending=true只表清理声明，不提供实际退出码或 Job 证明。缺配置/token 负向等未运行范围保持未测。

I24 固定源码提供 host-only Bearer、主窗口 full URL/document generation/session capability、唯一生成 RouteManifest、64KiB private framing/seq-offset/回压/abort/unknown 分类及 Windows suspended process→Job→resume 的归属链；不凭 CIM 发现 PID 授予 kill 权限。正常停止仍要求真实退出、marker、port/tree；forced 保留分类。ResourcePins 的列举文件、祖先持有与 SHA 约束不等于完整 namespace/native DLL/Python 导入闭包已批准；共享 V2 和主 Host 的 Cargo/config身份不同，不能互借编译结果。

BuildRoundFiveReceipt SHA39538e10bf5b12279106a27807ace02f36a72bca624c755b0749bfca487b4d57 的实际构建 exit0/source_changes=false/native_ready=false；本轮只核普通候选 exe 20,567,552字节/SHA516654f4986211be00dcd339b914deac704bd1a12f60ffaf0c57ee83c624d0df，未启动。先前非Sync跨await编译101、早期E0599/LINK1181/launcher失败与后来新源编译0须分版本保留，不能称旧源编译通过。完整安装资源 manifest/可信闭包、实际 host/API/Worker/MCP、metadata/tray、POSIX与三OS均未证明。

固定前端 source map SHA49e34f85ec526efa1f38e044fe093f5bb8076931b41f24c3b8d69e8cd512d040 中 engine.ts 27–29/112–118 仍是 managed-proxy 入口；native IPC workbench 尚未接，是后续 Frontend F4 依赖，未泛化为本源码 slice 实际运行失败。既有 API health 显式声明版本，与 NativeManifest 的0.3检查相干；未把 domain 默认0.2错记为 health缺陷。

T21 25输入/9静态证据/2交接副本全部相符。独立文本比较原68字段逐值、顺序、criterion均相同；旧 criterion SHA2f5203983e5c696ad6cb2ee89d81ed2bf7b5d51a31abbdfe5a6f6d9a576b85d2、原200000us/P95/N标准未改变。静态收据 SHA02dd27b6ba157f928b05555734fa7edd9a134d2eeaf5ed3aa7c6f50e7f8b12c4 仅7个 AST/UTF8/映射检查，CommandReceipt SHA0fa74aacadd4ea82239321b8158470df9e09e6babc3527a607f9fd5ddc53f3eb actual_exit0，Rust未编译，actual_product_cases/fixture_functions/candidate_module_imports均0。

prepared precision/reference 驱动通过当前 ordinary lease 和 recover_preparation/read_material 消费真实准备，不重新 claim published Run；published observation 通过可见 Bundle 只读。full-population数学由独立 t16_assertions 与实际 reference计算，再调用真实 evidence registry/service；transparent publisher hook先调用原 write/publish再在有限观察点闩住，不伪造 SQL/账本。上述是静态调用安排，并不批准外部 fixture、authority、已听审基准、实际 fault role 或最终业务结果。68函数/kwargs存在不等于68可执行已通过；Host/bridge、独立私有绑定、完整 bootstrap/素材许可/qualification及真实角色仍缺。suite 的 not_ready/CaseBlocked不能算 pass 或 skip。

## 交接

RV24-P01/P02/P03/I01交永久 Test，由 T22 在自身白名单修正并独立保留原字节/原断言语义和负向范围。生产 owner 与 Architecture 仍分别持真实实现与协议资格；Review 不代修、Test 不自批 RuntimeBinding、owner 检查不代 Acceptance。本报告不关闭先前产品问题，不批准实际业务运行。

读取源已释放，结束哈希只核固定副本，所有本轮命令已终态，无 live handles。Review 自身只读脚本的空字段/区间索引错误及修正记录在 Snapshot，不当产品失败。本轮产物只有 docs/reviews 与 Review/RuntimeSeams-RV24，UTF-8 LF。完整 Gate0→R1三OS独立验收→连续R2目标、实例持有数据与五步前台不缩减。
