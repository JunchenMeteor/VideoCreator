# RV29 — W16 私有 ASR supervisor 方案独立审查

结论：**方向可继续，精确私有 ABI 尚不批准冻结，RV29-P01（P2）OPEN**。这是文档/接口准备缺口，不是已复现的生产或 OS 运行故障。纠正方案已表达正确的所有权、未知受理和清理原则；但尚未成为完整可审具体代码修复。本轮不批准原被拒 patch、任何 production apply、人类授权、RuntimeBinding 或 ASR/native 执行。

## 固定输入与未落证据

实际 W16 根为 `G:/开发测试/Codex/VideoCreatorImplementation/AgentMedia/IndexedAsrLaunch-W16/`；过程根为 `G:/开发测试/Codex/VideoCreatorImplementation/Review/AsrSupervisorProposal-RV29/`。

- SupervisorProposal SHA：`bb863745d7a6b6d9b5183ac07fd6afd9082be2df4d4af5e1a88012aa36432232`。
- Handoff MD：`5e49598d1826d58b9dc847fe74bb8cd37d32a89a338eca8787732f77743f0272`；JSON：`51889dcde36535d98dc0e550a43d20905a1e134ff8004d3165518667915bdca2`。
- SourceSnapshot：`5cd7572fb4e2d65105bce809a54be825bbaa7e17a93310c8354d65ff527e1207`；RejectedPatch：`16ecea619a3ce0ef45efff166ef6c04d83f1451654b1ec7b9a6b1bef6df38fc3`；RejectionRecord：`cad71defee40e0088ba151daf07c1e2d14c578047d2dd9cbbe16e747f8e2aff9`。
- 固定 BeforeCopies 四源的完整 SHA 与原 before/after 记录一致：local_asr `ad9dbd7c6037a6dcd4bf075b71371e733e103cd7b1114b13e419e08d0443b058`，asr_resources `ecb693dc7adb98426d62138ebfdee20b20feea230a4838fc74c7c788ae31be74`，worker `7811c33e6947a1091d1a03ed03cb5fff1b9767135ed141a7851788f119ac53c3`，autonomous_production `8fb53084b5cb66a3f3972b9fb56c6b52e1043f8979c77ab052cc0084cb2a384f`。
- SourceDiff 实际 0 bytes；固定 FinalizerTerminal `f72d219b9295f5a912d6c7133c94c479f7075f7fcbd1348cfee9976a34355889` 记录文档脚本自然0、四源相同、新模块 absent。它不是 guard/child/后代终态测试。本轮未读当前生产路径来倒补历史事实。
- I28SourceFreeze `4ff684159a7a752425e1f6a83f3522f22916c77f5b61e14bd7be12b0c1a102ab`，十 ordinary 文件身份核匹配；仅相干 IndexedRuntimeContract `e9ec56f67259c02fd96f9fa65b5cfdf58232419c2088a12583b4b49b19af8693` 和 load_policy.rs 正文用于此接缝。ADR0023 `d261fa9513ea923af14ef4a0ac83aac59b72282b88987f438b62db2120248b51`。不是 I28 全 loader Review。

26 固定输入 pins 匹配、审查前后变化0，完整路径/身份见 RV29InputPins/SourceAfter，必要正文及原拒绝/未落证据已保存 Snapshot。未读 B19/Test 或其他生产 WIP。

## RV29-P01 — P2：受理未知后的同调用关联和核实/清理 ABI 缺件

**归属**：Media 原 owner 补精确消费接口/正确 proposal diff；Integration 提供实际 authenticated supervisor 注册、同调用事实与 guard/child 所有权；Backend 仅经 trusted factory 注入，并把核实事实接到原 Operation unknown。不能由 Review/root 自造实际 native 口或把普通 bool 赋为通过。

**位置**：`AsrSupervisorPortProposal.md:35–60,91–100`，完整 SHA 如上。`start_asr(binding, runtime_directory, deadline_monotonic)` 只在成功回复后返回 child；launch_id 是 child/terminal receipt 中的回复字段。声明里没有发起前固定的调用关联、受理分类证明，或在 child 未返回时对同一尝试查询/清理/取得终态的私有端口。

**最小触发**：supervisor 已受理并创建/hold child+guard，回复在 Media 获得 child/launch_id 前丢失或无效。方案95行要求 unknown 正确，但仅用当前声明方法无法把该 unknown 绑定到实际同一个 native child/guard，更不能证明异常属于明确未受理。`process=None`、无响应、没有 launch_id 或普通 transport 异常都不证明没有创建 child。此为静态接口反例，未实际启动进程或复现 OS 故障。

**必要补全事实**：

1. 发起前由 trusted factory/当前执行域建立不可变 attempt 关联，绑定原 Operation/会话、held installation/epoch、runtime 数据域；不是 renderer/model 自报身份或授权字段。supervisor 在创建任何 child 前保存同一关联。
2. 明确区分 authenticated `not_accepted/no_child` 证明、已受理、受理未知。明确未受理可按固定失败返回；start 已调用后无证明默认走 `asr_cleanup_failed → unknown`。不能由异常类型或缺 child 猜 definite failed。
3. child 尚未返回时，也能凭同一可信 attempt 查询/请求清理并取 terminal/quarantine 事实，或等价的启动前 owned attempt handle；不会生成第二次 ASR。成功回复后的 launch_id 与该关联、installation/epoch/实际 child 一致，重复/迟到/错会话响应不得改绑。
4. 当前 channel 的 poll/kill/close/核实要明确非阻塞或固定有界规则；cleanup 预算到期仍无真实终态时保 unknown/quarantine/guard，不因总deadline已过或客户端丢失放 guard。记录的是事实，不把 kill 请求当终态。

这些要求只补现有规则的可表达性，未修改公开 DTO、ASR result/context 或 Test 标准。正确完整候选需要进一步独立 Review；本报告不冻结方法名或批准实现。

## 纠正方案可支持的方向与仍待实现项

方案7–9、72–74、84–96、100–102行将注册/authenticated channel、真实 spawn/containment、ResourcePins/guard 和清理留给 native/独立 supervisor，Media 只消费受控 stdin/stdout/stderr 与原 input/result；Backend 只可信 factory 注入。固定 I28 `load_policy.rs:33–35,87–101` 仅可核 PreparedLaunch 持 `Arc<ResourcePins>` 和固定 bootstrap/env 构造，**没有实现 W16 supervisor/transport/start/terminal 端口**。path/hash/dataclass/ABC/descriptor 不能证明 guard，也不能替代真正注册关系。

Media 变更面应恰为 local_asr.py 的启动/清理消费、asr_resources.py 的固定注入，以及新增私有 indexed_asr_launch.py；`LocalAsrResources.driver` 的 launch 传播必须同一可信 factory、同原安装/数据域，不能让 `**controls` 或普通 callback 替换生产 supervisor。禁止修改 worker、原 local-asr-v2 stdin/result/progress、完整 validator、W15 canonical/context 方法、_admit/审核/quality。新源/资源索引/manifest 必须新 artifact，不能继承旧资格/P95。

生产配置缺真实注册口在发起前 `asr_indexed_launch_required`；只有明确 DevelopmentAsrLaunch 且无生产manifest才可开发分支，标 unqualified，None 不默认裸 Popen。固定 asr entry、`--` 后零自由参数、闭集 env 和系统 API 来源、guard 到 actual child+受控 descendants terminal 的规则均合理，但无真实安装/运行证据，Windows/POSIX支持不因此通过。

## 原被拒初稿与错误接线

原 `RejectedPatch.patch:157–165,220–225,238–259` 可见 start后无效 child 抛普通启动错误、`process` 可能尚未赋值使 finally 不执行 close；将 IndexedAsrLaunchError 一律 asr_indexed_supervisor_failed；cleanup 只捕有限错误；terminal 的 return_code 未与最后 poll/wait/returncode核一致。原初稿不能直接应用。纠正方案95–96行已指出这些问题，但没有具体纠正代码，不是已修复的源证据。

固定 `BeforeCopies/local_asr.py:344–415,512–518` 实际接线为：只有 `asr_cleanup_failed` 返回 OperationObservation unknown；其它 AsrProcessError definite failed，且 succeeded 在 run_local_asr 正常返回后生成。故所有受理未知/cleanup不明必须在消费层确定转换到现有 cleanup_failed；不得用其它 launch error 洗成 failed。未知清理应压过原取消/超时/结果，保诊断/原核实，不重跑模型。

| 条件 | 必须保留的结论 |
|---|---|
| 原取消/deadline 在 start 前；或可信未受理/no-child证明 | 既有明确失败/取消，不能创建 child |
| start 可能已受理，回复丢失/partial launch/坏 binding | unknown，按同 attempt 核实/清理；禁止重 start |
| child 已有，receipt错关联/缺失/错类型/returncode不一致 | unknown；guard不能据普通字段释放 |
| 取消/deadline 已发生，但清理与管道线程终态真实确认 | 保原取消/deadline；不能 succeeded |
| 清理异常/timeout/后代仍活/管道reader-writer未收口 | cleanup_failed→unknown，native继续保guard或隔离 |
| child/tree/guard顺序可信一致，退出0，原完整validator通过 | 才能沿原成功路径；不能 receipt 或模型文字代 validator |

## 最小独立 Test 设计建议（未运行、未写标准）

- 同一个无模型 fake transport/owned attempt：发起前拒绝、受理后断回复、partial launch、错/迟到关联、重复核实。检查单次 start 与 unknown，不能 bridge 自动补字段或再发 ASR。
- descriptor/receipt 错类型、bool冒int、install/epoch/launch不匹配、poll/wait/terminal returncode不一致；原输出即使像成功结果也不能绕过 unknown。
- 每个 poll/kill/wait/close/reader-writer 异常或stall，取消/deadline/EOF分开；核 bounded return、unknown优先、native持guard与最终终态/隔离，不凭对象drop或窗口关闭。
- factory 缺真注册、普通 dataclass/ABC/伪callback、None/生产manifest+dev分支、自由参数/env/module，全部前拒且不发 input；合法输入只在 containment 后发原字节。
- 原context两方法、完整validator和stdin/result/progress时码负例原断言保留；正确diff逐段确认保护字节及新source-resource身份。

纯double仅支持协议机制。随后真实无模型 child、真实 native Job/guard/客户端失联与ASR应分别以固定来源/资源/argv/env/权限/自有实例和终态准入；本轮没有批准这些执行。

## 交接与授权边界

先由 Media 原 owner 在自己的过程目录补 RV29-P01，并准备完整纠正 proposal sources/diff/精确三文件变更面；Integration/Backend 的缺实际端口仍分别待正式交接。再次有限独立 Review 后，统筹才能向人类展示正确具体可审源码变更并请求最终具体授权。不能拿已知坏原 patch 请求盲批准，不能用任务卡或本方案替代 native port存在/运行资格。

自动审批原拒绝理由是持久 ASR supervisor/guard 安全边界与运行行为的具体授权不足、失败可能中断ASR或错误放行；本轮保持拒绝、不换角色/tool绕过。全部本轮 reader/tool已终态释放，运行/ASR/测试/费用/key/network/源码与标准修改均0。仅文档方案审查阶段FINAL；完整R1独立验收后连续R2不变，RV28全loader审另待。
