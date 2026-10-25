# RV6 — T9 历史固定清理证据复审

阶段 FINAL。永久独立评审，只读源码、测试与普通证据；未执行测试、模型调用、产品进程操作、安装、构建、部署或验收签字。

## 结论与适用身份

对 **I5 历史固定三源**，RV4-P01、RV4-P02 的具体缺陷在下述实测机制范围内关闭。没有新增阻断性发现。本结论不覆盖当前 I7 新端口接缝、完整 DevRuntime 启停/UI/信号、Worker、原生父进程崩溃、安装包或整体 Gate0/R1/R2。统筹可登记局部关闭；完整目标仍为 Gate0 → R1 独立验收 → 连续 R2。

| 历史源 | 实际读取的普通副本 | SHA256 |
| --- | --- | --- |
| tools/build/EngineProcess.mjs | Integration/I7Original/EngineProcess.mjs | 874d0adc2205cc55dca0138963aa349c0389cab42bf6073d401ba6082ad95a28 |
| tools/build/DevRuntime.mjs | Integration/I7Original/DevRuntime.mjs | c0683c9a523398c0c866d5b711b605ea87f1e8864946e53fd0056d8acf820af8 |
| packaging/RuntimeContract.md | Integration/I6Original/RuntimeContract.md | 0434a26717fc8cc6a82794e3908b9322202e7c713d9ee34b75679e2824d584b4 |

以上副本均与 T9InputIdentity、I5Handoff 及四批原子收据一致。当前 I7 两源未读取或导入；I6 后续纯文档修正的新 hash 不倒填 T9。这里的行号指表中的历史副本。

正式输入：T9Handoff.md SHA `0911c67cc2ab39adb588f959b5c72fd99aa0f4779463e4feb47960757db97fb2`；JSON SHA `ac8989db982caa586a9fce655b966839d3ded12f2ef82df8556b67ca2fcfae2c`；82 份普通副本 manifest SHA `ce763e42b62dada49e6121539e4b66a7baeaf97761fa7c49339f4f1eafdce579`。

## 独立执行证据核对

| T9 实际批 | JUnit 实际 case/失败/跳过 | Node / UTF8 包装记录 | 总耗时 | 原子读取范围 |
| --- | --- | --- | --- | --- |
| T9CimRoundTwo | 1 / 0 / 0 | 0 / 0 | 2.2475373s | 284，前后与范围外变化 0 |
| T9HostRoundOne | 15 / 0 / 0 | 0 / 0 | 91.6531046s | 283，前后与范围外变化 0 |
| T9ViteRoundTwo | 2 / 0 / 0 | 0 / 0 | 22.3680656s | 286，前后与范围外变化 0 |
| T9TargetRoundTwo | 1 / 0 / 0 | 0 / 0 | 11.6315742s | 6，前后与范围外变化 0 |

共 19 项。评审逐份读取/hash 82 个普通副本，均与 copy_sha256、清单声明的 original_sha256 一致；未绕过 ACL 读取私有案例。四份 CommandReceipt 的命令、stdout/stderr SHA、JUnit SHA、测试数及正式交接 before/after 均一致，JUnit 无 error。UTF8 外包装 exit 是正式 T9 终态交接记录，CommandReceipt 中的 exit 是实际 Node 子命令；不把两者混为单个来源。

289 个源依赖并集逐项核对：三源使用上表历史副本，其余使用精确列明路径，全部匹配。四批内部及 all_source before/after 无变化。该观察不冻结当前并发工作树，不代表完整依赖链、OS 镜像或产品已验收。

资源收据另核 12 个 host 运行文件、263 个 Vite 运行文件（15 个包的记录闭包）、3 个 target 工具；共 278 次路径/hash 核对，均匹配，原子 before/after 一致。Vite 文件清单与实际 pinFiles 263 路径一致，未将该文件闭包称全机工具链冻结。

实际命令均为 `C:/Program Files/nodejs/node.exe --test --test-concurrency=1 --test-reporter=spec --test-reporter-destination=stdout --test-reporter=junit --test-reporter-destination=<对应独立 XML>`，分别执行：

- `tests/gate0/t7_cim_lookup_boundary.test.mjs`
- `tests/gate0/t7_host_lifecycle.test.mjs`
- `tests/gate0/t9_real_vite_cleanup.test.mjs`
- `tests/gate0/t9_target_metadata_recheck.test.mjs`

完整 argv、cwd、开始/结束时间及原子 map 保存在四份普通 CommandReceipt（T9Evidence005、009、013、021）及本评审 RV6Snapshot.json。评审只解析既有文件，未重跑上述命令。

## RV4-P01 — P2，固定机制范围关闭

原触发：CIM 查询失败使 captured 为空，但真实 Python close0、单 marker、端口关闭后，旧 EngineProcess 将 ownership 标为 verified/normal。T7 原红继续保留，不删除、不覆盖。

修复链：历史 EngineProcess:72 只在确实未取得 PID、已有 close 且无 inspectionError 时接受空捕获；正 PID 且无 rootIdentity 保持未验证。:78–79 保留查询错误粘性；:185 的 normal 条件仍同时要求 exit0、单精确 marker、端口关闭和已验证且无剩余后代。

T9CimRoundTwo 与原 T7 使用同一测试 SHA `2a134c0525ff554ccf832a2dab6763f42c04c80c00f1a76823ee12e86ad5f5b8` 和 helper SHA `b8c45a3d49258a82aa9646cce54c21fd6362391bb7b63680e0ce5e1d8664fdf5`。普通 T9Evidence025 收据（SHA `67fde96de07fbefa33e77ccc90a998b5b3ab5919a2fc5f6c5501386439ccff59`）显示：实际 API HTTP200；随后 Python close0、frame9bytes、marker1、port_closed=true；controlled CIM lookup 失败后 classification=error、verified=false、inspection_error=owned_inspection_failed、cleanup_complete=false、fallback.actions=[]。已消除原误报，未靠改断言或盲 force 通过。

原 15 项 host 测试 SHA `7a12b16ced2d8740baad8d97b89a68793191ab38c8cf5ed36c1236e6ba9a35f3` 不变，新源另批实际通过。包含正常两个独立 cycle 原始记录、WAV 导入/UTF8 项目重启持久、EOF/断管/default forced、启动正反、marker 字节变体和实际兄弟身份保护。字节 split 样本不等于已保证多次 OS data 事件；未独立声称捕获竞态、所有 fast-exit 情况或 JobObject 通过。

归属：Integration。关闭仅针对上述旧空捕获/查询失败误判路径；未来新 host 身份需消费新批证据。

## RV4-P02 — P2，固定机制范围关闭

原触发：顺序 await engine.shutdown 抛错/拒绝后跳过 Vite 清理；旧 force 的即时 metadata 查询抛错又可将失败向上游传播。T7 原隔离 callback 1 红只证明模拟 Vite.force 未调用，未证明真实 OS 残留。

修复链：历史 EngineProcess:199–204 用两个 Promise.resolve().then 配合 allSettled，API 同步 throw 也不阻止另一分支启动；DevRuntime:47–54 分别处理两路结果，保留 error、清理未完成和 exitCode1，任意错误文本不公开。EngineProcess:90–94 捕获即时目标身份复核失败，记录 identity_unverified 并跳过目标，不盲 taskkill。

T9 新测试 SHA `ebffd197896757ad3d71b06c6be73ffdd8cdd96b9fb2ab69b5f040b9253c709f` 绑定完整历史 DevRuntime SHA、原 stop callback 字节范围 [2798,4218) 及 SHA `4f8aa508d5e568e7e0eeca594e26b44b0be3460698650bbd5116af01c1eb40b9`。两份 Receipt 的 callback 字节/hash 与历史源逐字一致。受控 SyncThrow/AsyncReject 各记录 engine_shutdown 一次、real_vite_force 一次，并使用生产 cleanupRuntimeChildren 和 watchOwnedChild。

T9Evidence054 / 047 两份真实 Vite 收据分别 SHA `3ce13500b1d26c48289703796f7bf6f3502d9d8e4d1dbdc54ad8e0b8f43d3132` / `664e04515fd003ad61069d5213ea0615e18c499ac080b35ac8fa06eec06a6928`：独立 loopback 端口返回自有 HTML HTTP200 后，真实 Vite 以 taskkill 结束 exit1/signalnull、tool_exit0、捕获 root/后代为空剩余、port_closed=true；主 API 及兄弟 API 都继续 HTTP200，兄弟 PID/创建时间相同，随后各自私有正常关闭。

切片上下文的 process.exitCode=1 是回调失败分类状态；测试进程实际 exit0，Vite 实际 exit1。它不是完整 DevRuntime host 实际 exit1 或真实 API shutdown 异常的端到端复现。两路清理调用、真实 Vite 资源释放和失败日志分类足以关闭原具体 skip 分支，不能扩大为完整入口/信号/UI 通过。

补充 target 边界：T9Evidence080 测试 SHA `515f3310e3dd5ab9f3dde2578571a3743776e0a1fa192aadd6b12c44dff84b93` 按固定源码即时复核行 90 和实际 captured PID 集合注入 execFile 失败，不依赖“第三次查询”或单 leaf 假设。T9Evidence062 收据 SHA `3638c53c44df2d4339a3e9d89f966c3c843ce02d66ff27f1856114d9898c3da0` 有两次精确 callsite/PID 注入；taskkill 调用0、两目标 action 均 identity_unverified、verified=false、inspection_error 粘性保留、force exit=null。目标与兄弟真实 HTTP200/创建身份不变，最终分别通过自身 IPC 自然 exit0、端口关闭和 independent_remaining=[]。这证明受控即时未知身份不 force，未证明真实系统 CIM 故障或任意 TOCTOU 已解决。

归属：Integration。P02 两个已列分支在 I5 身份局部关闭；完整入口、native 监督和强父崩溃继续独立验证。

## 失败保留与证据限制

- T9CimRoundOne：缺 VIDEO_CREATOR_T7_CASES，在模块加载阶段 exit1、产品未 spawn；新命令仅补环境后使用 RoundTwo，不改原测试。
- T9ViteRoundOne：scope 准备缺文件、包装 exit1、未产生 CommandReceipt/产品子进程；普通 T9Evidence070 只是指向工具 chunk fb58d1 的观察 JSON，本批没有持有恢复的原始工具输出，不当原子测试收据。
- T9TargetRoundOne：旧测试 SHA `24ebfeedf6c70c49af646d5677f020cd2cfdc80aacf2971544536f055f936706` 假设 captured1，实际2导致故障注入前失败；原 stdout/XML/测试源及真实自有 IPC 清理保留。新测试改变自身注入绑定，未降低产品期望，不将该脚手架红称产品失败。
- T7 原两红、15 绿/GBK 外包装 exit1、T6 unknown 首轮 raw 缺失、AV0 旧包两次 exit3 继续有效；本批不重建缺失原始记录、不向旧候选倒填通过。T8 两项另批已由 RV5 窄关闭，不计入 T9 的19项。
- host/Vite 两批记录22508确实存在且 PID/创建时间前后相同；target 批 legacy_before/after 都为空，只能证明记录无变化，不能声称当时保护了一个运行中的22508。target 自有兄弟的真实 live/身份保护另有实测。
- CIM 查询与 taskkill 非原子，未知未来后代、父进程硬杀/OS退出、Worker、完整 UI/signal、三 OS/安装及自主音视频/Bundle/RAG/正式商业接口、支付、发布未在本批通过。制作、付费、发布与部署授权边界保持。
- RV5-P01 文档格式问题的0434历史状态保留；I6后续修正属于新文档身份，本批不冒认重新评审该新文件。原 Crew 三轮限制及真实委派0失败不因免费清理绿解除。

## 交接与复核动作

无须为本批再跑19或原83来取得相同观察。I7新接缝、A4控制协议及下一候选按各自新的精确身份由测试/评审/验收接续，不继承本历史身份绿。本批不签技术整体冻结或独立验收。

评审产物：`docs/reviews/RV6-T9CleanupEvidenceReview.md`；过程 `G:/开发测试/Codex/VideoCreatorImplementation/Review/RV6Snapshot.json` 和 `RV6Handoff.json`。自有读取脚本只用 fs/crypto 解析/hash，未导入产品或测试；默认 NodeREPL/exec 的 F盘 BitLocker 启动失败、一次 PowerShell 数组读命令错误及一次旧manifest字段适配错误均作为评审工具失败保存，安全 require_escalated 恢复只读；未解锁卷、改系统或 ACL。

测试运行0、provider/费用0、真实key读取0、产品进程操作0、实现/测试/标准写入0、安装/构建/部署0。仅写评审白名单。阶段完成后释放槽。
