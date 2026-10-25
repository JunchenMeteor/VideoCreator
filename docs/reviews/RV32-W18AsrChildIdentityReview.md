# RV32 — W18 首次child身份锁存独立复审

结论：**RV31-P01 CLOSED_STATIC_CONSUMER_SOURCE_SCOPE_ONLY**，仅绑定本报告的W18固定候选。原首次identity未用于最终比较的具体源码缺口已补；未执行候选或故障测试，不宣布真实native/OS/ASR问题运行闭合。没有新增阻断finding。不批准production apply、人类source权限或任何runtime/Gate资格。

## 固定身份及完整变更

W18根：`G:/开发测试/Codex/VideoCreatorImplementation/AgentMedia/AsrChildIdentityCorrection-W18/`；自身过程 `G:/开发测试/Codex/VideoCreatorImplementation/Review/AsrChildIdentity-RV32/`。

- SourceSnapshot `24c3669c73e1f12a31aa75203c97d939288acb25647133af74b6247e435e0708`；Handoff MD `ce8f21d9c7450c3b854c3f463d64a39848e1b13886e1187f0e81d9afdc541748`，JSON `8808764b20b6f50c7441a68e09148c73a206e8031e92984fc87691c4dd35026d`；IdentityChangeNotes `a9f763eddd62a3a7b7e78029596d7329e996b938094da9500d2e4ec7fc17b423`；FinalManifest `9a0fab9e6e2fdc006e51a4f5acf38a68648d29ef7cc36e6a6907774925959d63`。
- local_asr.py：W17原 `a93e4730e1455dbf8cc308a53ddfa3018652ac19013b25dc1479d2c1c04fb549` → W18 `911d7471f52c8de027f90d4127a62d7023f6b2a879abbe1017ed6dea4b778e49`（776行）。
- indexed_asr_launch.py `22638c5fb859fded32d7d5fda53f1d5dbb88c166c41c2551df4627e83425399c`、asr_resources.py `38a2fc1a3e4bd20708d5b8ca3e9f55d578f7ec05c60299edcc66c68065710988` 均与W17字节相同。
- W17ToW18.diff `95ad163753df2422f64c3e1345884417d50f1dfe1640e80ea1e4638e14bc98b0` 仅local_asr一文件；FullFutureProduction.diff `06f0fd25fadfd08cbbff13adf5467ca8c2baa82bee5f57b1d853cf326a0c002b` 为W16原BeforeCopies→W18完整三文件。

30固定ordinary/candidate/formal/原审批及I28契约pins逐身份匹配，审查前后变化0。完整三候选与两diff已固定自有Snapshot；逐hunk原context零差异，纯内存比对得增量和完整future diff均精确描述完整新源。没有apply/import/call。W17/RV31原材料与W16 baselines保留；未读B19/I29/current生产回填身份。

## RV31-P01 精确关闭依据

行号为普通 `CorrectedProposal/Providers/local_asr.py`。

- 360–374 `freeze_attempt_identity` 从exact AsrAttemptRef/AsrOperationRef复制独立str/int tuple，严格fence/epoch与runtime Path等语法；408行在原attempt控制接触前冻结。不是继续引用后来客户端view来作比较。
- 376–386 每次snapshot中child.attempt、launch_id、PID各单个读取点，launch/PID严格str/正int（非bool）；445–449首次核与原attempt tuple、锁存initial_child_identity，evidence记录初值。
- 388–396 `check_original_child` 对首次tuple比较，异常/不一致锁存protocol_fault和child_identity_fault。pipe对象取前后（458–466）、writer写/close前后（468–478）、poll前后（486–490）、final poll/wait/cached每次前后（543–549）、最终stdin close前后（603–607）均增加检查。
- 535–542 terminal receipt的原attempt/launch/PID tuple先与同首次值匹配；共同漂移B不再能与清理时的B互相自证。先拒wrong/缺初值/既有fault，再核当前child和strict四退出码及已观察code；555–558 supervisor证据身份仍取首次锁存值。
- record/accepted/no-child/quarantine ref均比较原attempt primitive snapshot（423、435、440、523、560），不仅与潜在共同变化的对象作==。未知/线程故障仍在634–649覆盖取消/超时/看似成功，774–775仍仅cleanup_failed→Operation unknown；无restart。

这些真实源码条件满足RV31提出的锁存/最终同child比较要求，故关闭其**静态消费源码**finding。没有使用owner“每property1读点”代运行计数，未用tuple/dataclass/ABC/hash/bool代认证、guard或OS终态。观测点检查不宣称在任意恶意Python回调下构成sandbox；真实native client不可变注册与pipe归属仍由Integration实现/验证。

## 保护与其他边界

八保护正文与W17及W16基线逐字相同：完整validate_asr_result、_rational_us、_time_base、_original_context_bytes、validate_original_asr_result、validation_context_bytes、_cancel_requested、_ProcessTree。worker未改，原context/stdin-result-progress/微秒/方法精度/_admit/审核/quality不在diff。只有local_asr身份观察与比较增加，没有新增private ABI字段或公开授权参数。

原RV29静态接口补全仍保：原Op/run/fence/route/context/input/session/epoch/install/runtime关联在接触前形成；record durable且不可spawn、start只一次源码点；无child回复仍同attempt reconcile；sealed no-spawn须关闭迟到受理；缺/错proof、terminal或quarantine保持unknown。该保证仍是Media消费和native ABI规则，真实native持久记录、原Operation查询、注册认证、actualchild/guard未实现/未实跑，不能关闭其运行边界。

partial stream逐个登记、writer/readers有限join、全部外部cleanup异常、5s清理总预算、unknown保runtime、原cancel/deadline/EOF分别、strict int退出一致及显式开发模式均未被此次增量放宽。缺production注册口/None前拒，显式Development无production manifest且unqualified，不能silent裸fallback。helper/loader同W17，不因source闭合给其factory、目录/OS guard或实际安装准入。

真实factory与ExecutionPermit/Operation关联须Backend正式实现，认证私有channel/registry、sealed no-child和真实guard/child/controlled descendants须Integration实际实现；窗口/API/客户端丢失不得提前drop，未知不重提交。类型签名和未来任务卡不是实际port存在证据。

## 必要独立Test及下一步具体变更

Test owner须独立验证稳定A正向、launch/PID单项或共同漂移B、wrongattempt/ref/session/epoch/install/context/input、属性异常、pipe取用/writer/poll/wait/cached/terminal各观察点漂移、bool/None或不一致退出码。负向应cleanup_failed→unknown，evidence身份保持初值且原validator不能把错身份洗成功；同attempt清理无第二start。还需保start丢回复/record异常/sealed no-child迟到接受、cleanup异常/partial streams/未终态/quarantine、cancel/deadline/EOF机制反例。

本报告只给Test条件，没有设计或执行测试标准；纯double只支持机制，随后真实无模型native/Job/guard/失联/后代及真实ASR分别另准入。当前没有candidate或double执行，更没有精度/P95/安装/完整68/三OS通过。

未来完整生产变更恰三路径：新增 `services/engine/src/video_creator/providers/indexed_asr_launch.py`；修改 `services/engine/src/video_creator/providers/local_asr.py`；修改 `services/engine/src/video_creator/providers/asr_resources.py`。具体可审文本是以上三源完整SHA与FullFutureProduction.diff SHA；不是W16坏patch或W17旧local源。此静态候选可进入原Test角色独立准备阶段，**不授其launch或人类production写权限**。独立Test/实际可信端口条件与具体授权按各scope处理；一旦候选改变必须新hash复审。新生产source/resource/manifest要新artifact，旧stage/qualification/P95不回填。

自动审批原拒绝理由（supervisor/guard持久安全边界具体授权不足与中断/错误放行风险）保持，本轮不换角色/tool绕过。当前回滚状态是未应用，后续统筹只能向人类展示正确固定diff及具体依赖风险后请求必要权限，Review不代授权。

StaticReceipts906bb4/26693d与FinalizerTerminaleea64f自然0仅文本/AST/basicRuff/身份收尾，candidate import/call均0。全部本轮reader/tool terminal、live[]、已释放；费用/key/network/product/test/ASR/candidate apply均0。正式FINAL，完整R1独立验收后连续R2不缩。
