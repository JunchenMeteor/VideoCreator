# RV35：W18 候选与 T27 子进程身份消费机制复核

结论：固定 W18 候选的本轮消费机制证据可支持，未发现这一有限切片的新 P2 阻断。T27 原始 12 项测试、59 个场景、0 failure/error/skip，unittest 2.116 秒；原工具、UTF-8 wrapper 和 Probe 各自然退出 0，未强制结束。Review 没有执行候选或测试。此结论不授予生产 apply、RES13、RuntimeBinding、真实 native/认证/guard、ASR 精度或 Gate 资格。

RV31-P01 的消费层 SOURCE_STATIC 关闭保持 RV32 原范围。T27 为同一固定候选增加合成端口机制证据，不能把这个关闭扩展到真实 native 实现或完整产品。

## 固定输入及实际身份

普通根为 `G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T27AsrChildIdentity`，路径由原 Manifest 的实际 copy 字段确定。45 份普通副本及 4 份正式末层材料均核 SHA/size；加规则、任务卡和 Manifest 共 52 项初始 pin，无 mismatch。结束重核 51 项固定输入，0 变化；协调者可更新的 RV35 任务卡只保留首次 pin。没有读 I30/T28 或当前生产源，后续报告仅消费已保存事实。

| 固定文件 | SHA-256 |
|---|---|
| FixedSources/video_creator/providers/local_asr.py | `911d7471f52c8de027f90d4127a62d7023f6b2a879abbe1017ed6dea4b778e49` |
| FixedSources/video_creator/providers/indexed_asr_launch.py | `22638c5fb859fded32d7d5fda53f1d5dbb88c166c41c2551df4627e83425399c` |
| FixedSources/video_creator/providers/asr_resources.py | `38a2fc1a3e4bd20708d5b8ca3e9f55d578f7ec05c60299edcc66c68065710988` |
| FixedDocuments/FullFutureProduction.diff | `06f0fd25fadfd08cbbff13adf5467ca8c2baa82bee5f57b1d853cf326a0c002b` |
| TestSources/ProbeT27.py | `d57e9353d2d34af3a4fdf23d17fa7326ad26ea47255580d4478e537513e881f6` |
| TestSources/NativePortDoublesT27.py | `f117bfcd8bd32e3ee8335811c051354f8951bb1391dad0f5011e96bd8563fe46` |
| TestSources/FixtureFilesT27.py | `cbdf9b762fb3261b84f1dd9f8cd1e5cb5c5381d9db2ee99e9ad4bd6c28e1b55d` |
| T27Handoff.json | `e3e86a4587a3df629b9d74996d7ff54bdf8374c880d1c5b269eca8cf284c09d1` |
| T27Handoff.md | `7479aafd42f8e4ced760d9ecfb247432bd59e82d048cafcbfce4fd4a7ef7af22` |
| T27HandoffSnapshot.json | `b250db4cce3c748322c061a63cf0d1e98feddd47aa101ab49aa37924ae97f1c6` |
| T27OrdinaryManifest.json | `5e2d59d751d889dd262f974c31118589efd6240042d14b822ef63666c5985bec` |
| T27TerminalReceipt.json | `50c14b8fc10c1e6245d0bde3a172dd7569c63f5bcef30e82995264da0908ee53` |

全部输入和原/副本身份见 [RV35InputPins.json](G:/开发测试/Codex/VideoCreatorImplementation/Review/AsrCandidateMechanisms-RV35/RV35InputPins.json)，末次固定身份见 [RV35SourceAfter.json](G:/开发测试/Codex/VideoCreatorImplementation/Review/AsrCandidateMechanisms-RV35/RV35SourceAfter.json)。复用的 1232 项包/runtime 归档没有在本次重复扫描；案例 dummy 文件未全部再复制，使用原始 Events 中保留的事实，不把占位文件当安装资格。

## 源码与原执行证据支持什么

完整候选三源、实际 Probe、double 和 fixture 正文已读。Test 通过实际模块导入完整 `run_local_asr`、`LocalAsrDriver.__call__`、未替换的 `validate_asr_result`；不是 AST 摘取函数或另一份影子实现。实际方法计数为 59/8/4，逐场景 validator 增量之和为 4。`validate_original_asr_result`、`load_asr_resources` 没有本批执行记录；worker 仅核 hash，没有调用。

[local_asr.py:360](G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T27AsrChildIdentity/FixedSources/video_creator/providers/local_asr.py:360) 将 pre-contact attempt 冻结为独立 primitive 值；376–396 每次快照读取 attempt/launch/PID，锁存首次 child 身份及 sticky fault。403–449 在 contact 前形成 attempt、记录后只 start 一次，不能从异常、无响应或无 launch_id 推断未创建。515–567 始终向原 attempt 对账，最终 receipt、四处严格整数退出码、首次 child 身份及已有异常必须一致；不会让后来共同漂移的 launch/PID 自洽替代首次事实。

59 个原 Events 的独立汇总：所有 expected/observed error 相符；指定 drift_at/raise_at 的实际 port_events 全部含目标事件，0 未触达；每个场景 records=1、starts 最大 1，record/start/reconcile 的 primitive 参数保持同一初始 tuple，0 不一致。原始事件 SHA 为 `b4e213a6b50f2ad532af0f741ffc3f3c62e15ce783d922cebf3418c305c5156a`；逐场景事实见 [RV35FactsCheck.json](G:/开发测试/Codex/VideoCreatorImplementation/Review/AsrCandidateMechanisms-RV35/RV35FactsCheck.json)。

| 已执行机制组 | 场景数 | 有限支持 |
|---|---:|---|
| 稳定调用与 Driver | 2 | 已知终态才解析完整结构，Driver 成功 |
| 单独/共同身份漂移及各控制阶段漂移 | 3+8 | pipe、writer、poll、wait、cached、terminal receipt 到达后的漂移均 unknown，不使用替代身份 |
| 原初 attempt 不符 | 9 | operation/run/fence/route、session/epoch/install、input/context 不符拒绝 |
| getter、stdio、observer 异常 | 10 | 实际目标事件到达，异常进入 cleanup unknown |
| 严格 PID/退出码 | 8 | bool/None、阶段退出码矛盾不当终态成功 |
| record/start 回复丢失及不确定收尾 | 3+8 | 无已知原 child/树/guard 或部分流失败时保留 runtime |
| sealed no-child 与坏 ref 不可洗白 | 2+2 | 封闭证明有限正向；未封闭、错误 record/accepted ref 仍 unknown |
| cancel/deadline 与坏结构 | 2+2 | cleanup unknown 优先，Driver unknown；坏结构经原完整 validator 返回 failed |

Probe 57–119 在断言前保存原事件，再核 starts、同 attempt 参数、runtime 留存和原 child evidence。稳定组 125–134 及结构负例 190–194 真正进入完整 validator。cleanup unknown 的场景 validator 增量为 0。612–647 的 observer/cleanup 错误不能被 cancel/deadline 或正常文本覆盖。预算仍是候选原值：control 最大 0.25 秒、cleanup 总 5 秒，没有为本批降低预算。有限 BytesIO 和 Test 端口不能证明真实 RPC 在超时内返回。

原 JUnit SHA `a131b95a689fa7be734f04dbebce62fc50542b36e1051ecbf86babf63088528d`、CommandReceipt SHA `b97258a5010c89e826bd9bd9c009f76a65ca459d4038c6e08666c65c622ed0b9`、保留句柄 wait receipt SHA `ca4648e15ffb92ef414e38e658ba8f62bcbd9549a2df8909d5610493c836b0b2` 相互一致。工具 `303c07/session77569 → 6d7daa`，wrapper PID 48840/CreationFILETIME 134359722030906649、Probe PID 26580/134359722044290115 各 natural 0；这是实际测试宿主进程，不能叫真实 ASR native child。原 evidence-only PowerShell 错误、截断读和准备路径错误保留，没有候选重跑或洗红。

## RV35-I01：P3，冻结交接计数口径需分列

归属 Test，非阻断。固定 [T27Handoff.json:69](G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T27AsrChildIdentity/T27Handoff.json:69) 的 `input_before_after_equal=true` 正确；71 行把 `path_identities` 写为 3487。实际 runner [RunT27.py:20](G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T27AsrChildIdentity/TestSources/RunT27.py:20) 先收集 all_records 的 original/copy/execution_original 去重路径，再加入 7 个 Test 源路径及 pwsh。

三种真实口径分别为：1244 条 all_records；3487 个去重 record 路径；实际 InputBefore/InputAfter 各 3495 个观察路径。Review 逐值比较全部 3495 项，0 改动/新增；两原 map SHA 同为 `8f0cda1ff536ee316a464d05b3170978dadbf2440c3d1a0460e0503251412f94`。不是源漂移、测试失败或原结果无效。保留原冻结 Handoff/Terminal/raw，不改旧文件或打断 T28；后续只追加明确命名的口径说明，不能把这三种数互换。

## 仍未覆盖与后续真实准入条件

本批端口记录文件、封闭 no-child、terminal/tree/guard 字段来自 Test double。59 个事件均明确 `installed_qualified=false/native_authenticated=false/real_audio_or_model=false`，native 执行标志为 0。候选输出中的 `supervisor_owned` 等字段是对端口协议陈述的消费，不构成认证或 guard 的独立证明。原 fixture 的 Python/model/audio 是标明 NeverExecute/NotInstalled 的 dummy bytes；成功的「甲乙」结构不是实际转写。

Integration 必须另交真实安装 registry/source pins、认证私有 channel、pre-spawn durable attempt 记录、同 attempt 查证、真实 child 与进程树/guard 归属、封闭未受理与确切 terminal 证明；Media/Backend 必须接真实受权 factory、Operation/context journal 和原结果 commitment。`AsrInstallationBinding`/ABC/tuple 类型检查不能自授这些资格。开发模式独立显式入口保持，不得替换成生产 fallback。原 automatic patch refusal 不因本批绿被绕过；正确生产 diff 与权限另处理。

后续 Test 可补尚未执行的最小边界：attempt_id/runtime_directory 原初不符及锁存后的 attempt 内容漂移；末次 getter/receipt 属性异常；stderr.close、writer 异常、实际阻塞/限额/真实 EOF、共享 cleanup deadline 耗尽及 native 认证客户端丢失与晚受理。当前 tearDown 只证明父测试组结束时无新增存活的 Test stream 线程，不证明每个场景即时 OS pipe/Job 收尾。这些是未覆盖范围，不凭源码推导写为真实失败。

ASR 实际 decode/模型、P95/独立 authority、真实 journal 恢复、原 T26 第六组后续未达断言、完整安装/SDK/HTTP/native 接线、macOS/Linux 均不能借本批通过。T26 原 9 项 NOTPASS 不变。本阶段 SOURCE_AND_SYNTHETIC_MECHANISM_REVIEW_FINAL，全部输入 reader 终态并释放；完整 Gate0→R1 三 OS 独立验收→连续 R2、数据由安装实例持有及前台五步不缩减。
