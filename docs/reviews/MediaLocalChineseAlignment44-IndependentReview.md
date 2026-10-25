# Media44 本地中文 CTC 对齐独立源码评审

结论等级：SOURCE_STATIC。本轮未确认新的 P1/P2；初始制作、原已结算对齐结果恢复、部分 Ready 补全，以及持原 repair command 的受影响 realignment 分支，具有本文所述源码支持。已选中 realignment child 后，在尚无 candidate/WorkReport 时执行 retry_final_validation 的原运行来源读取缺口仍为 OPEN。它不能由本轮静态支持或已完成的 Backend120 源码修复替代。

本轮没有执行或导入产品、Pydantic、CTC/ASR、模型、SQL、HTTP/MCP、原测试、native、安装或联网，费用与密钥读取均为 0。没有 RuntimeBinding、资格、精度、完整制作流程、安装整包、三 OS、Gate0、R1 或 R2 验收结论。原完整 R1 后连续 R2 目标保持。

## 1. 固定输入与实际审查

依据工作区和仓库 AGENTS、固定任务卡 MediaLocalChineseAlignment44IndependentReview.md（5398cabfab561f4b15146b0d39bd75be5641ada035d71ce2118b8ab4635e7560）、ADR0055/0056，仅读取停止普通副本。

- Media44 SourceSnapshot：2f95d1ed59a1055fc75cb66f21740e846a625400b784331bfe197694029544be。
- 原 Media38 SourceSnapshot：af99a9939734da9bee1ba8d2d5a3ffd2b50dc904abae095e0bab395a81f1c600。新阶段 BeforeCopies38 与原38对应副本逐份字节一致。
- Complete.diff：1323112906c2ce2a6ceb1001c243d2e69b92cb73abb46a0275de03601e9a5e3c，95034 bytes。本评审由原38与新44逐文件重新生成 unified diff，完整字节相同；6 新文件、4 修改、原38内34不变。
- 44 份新源码和38份原源码分别核 bytes/SHA 与索引并用 stdlib AST 解析；完整阅读10份增量源码，定向阅读实际相干的原 ASR 子进程/流、资源、安全准入、affected/恢复、Backend 登记/执行/当前来源端口。没有以作者摘要或 AST 数量代替调用链审查。
- 原 InputBefore 保存151个唯一有限输入；InputSupplement 追加固定 Backend domain/current_final_evidence.py 一份。InputAfter 共152份，changes=[]。没有重新扫描整个 runtime 或复制依赖环境。全部完整身份见本过程 InputBefore、InputSupplement、InputAfter 与 IdentityDiffAst。

十份增量源码（普通根为 AgentMedia/LocalChineseAlignmentImplementation/SourceCopies）：

| 源码 | Bytes | SHA-256 |
| --- | ---: | --- |
| workflows/alignment_documents.py | 8296 | cdab4b53b14a386f80f40b4e8ffe127c94557e4e7d48b8a1203f576763a7623b |
| workflows/alignment_recovery.py | 12450 | db6df61634ddab7e8f6a5c52665589467ff24884710f7d644681a86efb7d20db |
| workflows/bundle_producer.py | 51769 | ac012151e79583d6384e35efdf7e6e09a34351cb47b85077f45d79a12fd7b56c |
| workflows/bundle_recovery.py | 45339 | c8ea3d9add3c348bfd8c7a8fbefee3f9c7ec9c1c14a886a6e6737a251eeb5d13 |
| workflows/bundle_v03.py | 24846 | 5acd7c028b87b432e5b208a04ed7f9caf0f6cd226ecd2ec42c78135cdc0da8ae |
| workflows/current_engine_production.py | 10094 | bd12bda27475a66a7e037062efb1f9f0afaafcc817e0da60c41f4c8ce653b3e6 |
| workflows/registered_alignment.py | 9125 | 945312a4de0fcf5c4350f224beb1c180191fcf3e0e39ea7b4a67467095ff4436 |
| providers/local_alignment.py | 12906 | e5c173d2e0a66044e32faeed30e761206de8f5b64d0a244b952bd7dc1ecce1d3 |
| media/alignment_worker.py | 16475 | 3687d6f2a0f6bd8a0faff96f946f0e5320e6576070c75733ed15fc1bbe52d0e6 |
| media/ctc_alignment.py | 4815 | d181dfc6c0214ab3d9c589c855466858747a68faa1a3c21ae79b1aa9ae071667 |

原同目录 Handoff、FactoryConsumption、FailureNotes、ObservedToolTerminals、FinalStatic、ChildRuntimeRecoveryGap 均保留原件身份。Backend 必要上下文只来自 RegisteredCtcWorkValidationRepair/SourceStage/SourceIndex.json（9a22dec995223337c8221ab6c3b14733a2413716426e73b3625142cd0ed2172e）与对应普通副本，没有读取后继热实现。

## 2. 原保护与引用来源

独立字节对照确认 providers/local_asr.py、providers/asr_resources.py、media/asr_worker.py 三份完整原件不变。workflows/autonomous_production.py 完整文件也不变，包含原 _admit；未改为用新 role/tool 执行先前被拒动作。

两处原质量赋值按独立 AST 全值对照：

- bundle_producer.py 旧356–360/新364–368：alignment 与 rights 保持 not_measured，明确“assembly evidence only”，不能当独立用户验收。
- bundle_v03.py 旧262–264/新284–286：alignment 的 verified 仅声明实际音频、单元、映射与 schema 装配，保留 no per-work precision claim。

五份选取的上游算法节点 Point、Segment、get_trellis、backtrack、merge_repeats 与冻结 WhisperX alignment.py 对应 AST 完全一致（上游 SHA cc3607dcc25e592ae218f74a6ca644d6ce1c77d9cee4672f01c751da8feb9aa7）。media/ctc_alignment.py 保留完整 BSD 2-Clause/Max Bain 2024 声明。许可证全文来自正式匿名普通副本 TextViews/Source-0001.txt，1297 bytes，SHA cddc25bce26226b4a04ed12839d9006b7a4403da9020ef6428ef7282a6567441，并由 OrdinaryIndex 与有限补充定位卡绑定。文件名未含 LICENSE 不代表许可证缺失；没有联网补造来源。

这只是指定算法源码与许可证文本的对照；不证明全 WhisperX runtime、模型权重许可、分发包许可或独立资格 producer 已满足。

## 3. 调用链的有限源码支持

### 3.1 工厂与原 Operation

providers/local_alignment.py 38–128 只接受实际 Backend Initial/Affected 请求语法、原一份 output scope、原 run/fence/registration/input SHA。工厂核资源完整索引、固定 worker/runtime 与当前 installed source，对实际音频路径及完整 SHA 重新检查。它不凭 qualification 构造实际 Observation，不授付费 provider，也不通过任意入口加载模型。

_run 130–197 的新 worker 子进程路径保留原受控 stream/ProcessTree，用固定 -I/-B/-X utf8 入口、有限 stdin/stdout/stderr、超时和 cancellation 条件。输出必须为严格唯一 JSON、原 request SHA、生成文件 SHA/size 与实际 execution identity；未知子进程或清理终态保持需要 reconciliation。实际 Windows 句柄、线程、Job、取消期限和进程终态均未运行验证。

workflows/registered_alignment.py 14–86 的链为原 begin_step → prepare_op → 原 executor。已结算结果只走 held reader；对已结算 Observation 尚需 Step commit 的特定恢复使用原 manifest/commit，不重新推理。非 prepared 的未知/在途状态拒绝自动重试。只有 prepared 的原请求才能分配一份 alignment-result 并提交原驱动。Backend executor 的 post-dispatch 异常仍进入 UNKNOWN；源码不存在“无响应即未受理”的新授权。

### 3.2 真实 CTC 数据与参考数据隔离

media/alignment_worker.py 71–104 对实际选定音轨解码，核 rate/timebase/样本数/origin；整数微秒从解码与模型帧映射获得。107–143 使用实际模型 log-softmax、CTC trellis/backtrack 与完整 token coverage，未用均匀插值或预置稿时码冒充实际推理。146–272 限本地 CPU float32、实际配置/权重/whole-map 身份，权重加载限定 weights_only，拒 auto_map/异常配置，不调用 from_pretrained 或联网下载。

长 utterance 分窗依实际词锚及完整字符覆盖；OOV、缺实际锚、低置信度、非法时序拒绝。受影响请求之外的单元保持原预测区间，初始完整允许集和 affected 允许子集由 Backend 请求语法继续限定。生成 Alignment precision 为 not_measured，推理请求不包含独立 gold 或精度参考。

alignment_documents.py 53–103 由实际 aligned cues、实际解码 frame hash、镜头重叠及原 ASR 文本/来源生成字幕、语义音频片段与 RAG。没有把源稿标为实际音频转写。measure_alignment 的独立参考读取在实际结果之后；bundle_v03.py 255–269 仍逐 utterance 取 start/end 绝对误差最大值并以 nearest-rank 求 P95，整数微秒/200000us阈值未变。数学、独立标注 authority、资格与真实音频听审仍须各自证据，不能由 worker 自证。

### 3.3 初始、部分 Ready 与受影响路径

bundle_producer.py 129–623 在原 ASR/解码/资料和创作事实基础上保留初始准备，再执行登记的实际 CTC；独立测量、五份语音文档 Ready、原第九 method getter、WorkReport 两类 Operation 来源及最终两 authority/rights 校验依次接续。typed registration 或资源文件存在均不等 ready。

continue_bundle 与 alignment_recovery.py 25–80 用原 allocation/material IDs、原 ASR/context、稳定初始文档身份恢复缺少的五份文档。_slot_stage 对既有 Ready 读完整字节核一致，只补原 slot；不新增 ASR/UUID/重派原 UNKNOWN。reference/correction 原来源及后续 restored corrected_from/reason 保持独立，没有丢弃原 author pair。

持真实原 repair command 的 _repair 路径（bundle_recovery.py 523–604）先读取或执行其原 alignment Operation，再按原 atomic child 选择和实际允许单元重建必要产物。alignment_recovery.py 105–189 使用 child 实际 source/媒体/独立参考，对未受影响原字节及既有 Ready 作一致性检查；质量、审计、WorkReport 与精度按实际新来源重新形成，而非复制父工程过期结论。changed-audio generation 继续原完整制作/ASR消费者；旧三 ASR 源和原完整上下文门没有绕过。

以上只支持这些已实现源码分支。原修复运行、权限、预算/UNKNOWN账本、writer/fence/current事实、精度及真实全包均未在本轮执行。

## 4. 已知 OPEN：选中 realignment child 的独立重试来源读取

M44-I01，P2，既有 SOURCE_INTEGRATION_GAP，OPEN。归属：Architecture/Backend 的 held current evidence 读取契约，以及 Media 之后对该固定接口的消费。这里不是新增运行失败，也未以未来接口关闭问题。

最小触发是：已选择真正 realignment child，五份 speech/assembly 已 Ready，candidate/WorkReport 尚不存在；后续只从当前 child 执行 retry_final_validation，并非继续持原 repair command 调用 _repair。

完整冻结链：

1. bundle_recovery.py 449–472 从原 current readset/continuation 恢复；生成 candidate 时，370–373 没有 alignment_execution 参数则调用 initial_runtime。
2. alignment_recovery.py 83–102 用 child preparation_id 调三份 registered_initial_alignment getter。真正 realignment 来源属于原 repair command 的 affected registration，而非该 child 的 initial 登记。
3. 若原 initial 登记不存在，91–94 仅回退原实际 ASR Operation/assembly methods。bundle_v03.py 75–77 又要求实际 execution identity 与 admitted CTC qualification 相同，不能把 ASR runtime 冒充 CTC。
4. 固定 Backend domain/current_final_evidence.py 219–231 的 CurrentFinalEvidenceReadSet 只有11成员；没有允许作者恢复原 affected Execution/command 的事实。现有 affected getter 需要原真实 Execution；已有 WorkReport 才能走其来源 reader，不能用来先生成第一个 WorkReport。

修复须提供原 held reader 能核实的真实 command/Operation/request/文件/CTC identity 关联及消费者；不能从 qualification 反推 Observation、用 ASR 伪装 CTC、读私有 SQL 拼 Execution、重新 dispatch 已结算/UNKNOWN 工作，或放宽身份门。当前 ChildRuntimeRecoveryGap 已独立对照，原 Architecture 正处理契约，未读取其活设计。后续实际恢复成功需要 Test 的真实来源闭环，不是本轮批准。

## 5. 原检查结果、失败与证据等级

作者原 FinalStatic/Summary 与原文本收据分别保留：44 AST、10增量 Ruff 自查退出0；完整目录 Ruff 退出1的两处原 BLE001 位于 media/asr_worker.py:276 与 media/bundle_probe_worker.py:98。两文件对应旧源码未变。本评审没有重跑 Ruff，也没有把作者自查当独立产品测试。原初轮 lint 红及完整目录最终1保留，不标整目录 green。

本评审自身原定位错误 c16a20/1：将固定 Backend actual executor.py 误定位成 production_executor.py，触 KeyError。原脚本/Failure 单独保留，纠正后 cf6e04/0 才保存151 pins与diff对照；不当产品反例。合并源码读取输出截断保留，随后只定向补读未显示段，不以截断输出冒称完整读取。许可证匿名文件定位历史同样保留；最终精确副本和正式索引已核。

本轮独立 stdlib 数据检查：cf6e04/0、保护/有限末核076244/0；152输入0变化、完整diff字节一致、五算法 AST及两质量赋值一致。它们不是测试数、CTC模型兼容性或实际 OS 运行证明。作者的 Handoff/ObservedToolTerminals 仍仅证明其自查与停止交接范围。

## 6. 尚未验证和交接要求

- initial/partial/affected 三条真实 producer/Operation/Step/current/fence/两 authority 的联调，包含原 UNKNOWN 不重发、预算不丢以及权限来源。
- 原 selected child retry_final_validation 来源接口与真实恢复；M44-I01 保持 OPEN。
- CPU 实际 CTC、中文/OOV/长窗、decoder/词锚时码、gold 隔离与独立标注/听审 authority。P95 标准不降低。
- 取消、超时、清理失败、原 retained Win32 I/O/Job/线程终态；实际 local factory 安装和 full map 资格。
- 完整制作成片及多模态 Bundle、真实 API/MCP、桌面/native、Windows/macOS/Linux安装与完整 R1→R2。没有完整安装整包或制作流程已经通过的独立证据。

评审不代实施、不修源、不降低原验收、不授权运行。下一独立 Test/Backend/Media 应消费固定版本与真实权限来源；本文不得被用作 RuntimeBinding 或发行许可。输入 reader 已完成并释放，正式交接以最后真实工具自然返回与 FinalHandoff/FinalizerTerminal 为准。
