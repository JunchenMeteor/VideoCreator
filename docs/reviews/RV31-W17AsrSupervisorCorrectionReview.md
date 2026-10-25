# RV31 — W17 完整纠正候选独立复审

结论：**CANDIDATE_NOT_APPROVED_FOR_PRODUCTION_APPLY，RV31-P01（P2）OPEN**。RV29-P01原四项接口缺口已在该候选静态表达，但真实native/authtransport/Backend注册仍不存在本轮实现或运行证据；不因文本和类型宣布运行闭合。新P2为首次child身份未锁存比较的具体候选源问题，未运行复现。Review不修改候选，也不代人类授权。

## 固定身份与范围

W17根 `G:/开发测试/Codex/VideoCreatorImplementation/AgentMedia/AsrSupervisorCorrection-W17/`，候选只在 `CorrectedProposal/Providers/`，不是已应用生产源。自身过程 `G:/开发测试/Codex/VideoCreatorImplementation/Review/AsrSupervisorCorrection-RV31/`。

- Handoff MD `738cb03955c4f8890cc636cd0493236fea0aea7d28880de05ab176d7e0da4b08`；JSON `fa389f7d42f3447e4aa775f1398561aa369aa54c6b99afdfa7b9e442a8526ece`。
- SourceSnapshot `3b4078cb77a0448e5eb2fc48ac37256fd2cbe2e4999dd076e0b26514c4e9c0cf`；CorrectedInterfaces `3390ae7a6b1201f7f068f1a9288bfd7c2446e22b9b3213f60b383a0935e2ca38`；FinalManifest `2192cb855b7a96361f5305a18003f620f854977b271d4c7eda32cb4310b7c165`；完整diff `ac6a561e728c9c6f2239c9415532aeea32646a82cc943e56d14686786cf2abb2`（43789 bytes）。
- indexed_asr_launch.py `22638c5fb859fded32d7d5fda53f1d5dbb88c166c41c2551df4627e83425399c`（285行）；local_asr.py `a93e4730e1455dbf8cc308a53ddfa3018652ac19013b25dc1479d2c1c04fb549`（701行）；asr_resources.py `38a2fc1a3e4bd20708d5b8ca3e9f55d578f7ec05c60299edcc66c68065710988`（94行）。
- 基线严格为W16四BeforeCopies ad9/ecb/781/8fb、原RejectedPatch `16ecea619a3ce0ef45efff166ef6c04d83f1451654b1ec7b9a6b1bef6df38fc3`、RV29报告 `c298ccfd4ea7762ac66d0e6cc8a0ffc223d8b67a3a5cdc27ccdb4f4ccc06c39e` 与I28普通 IndexedRuntimeContract `e9ec56f67259c02fd96f9fa65b5cfdf58232419c2088a12583b4b49b19af8693`。未读B19/I29或当前生产来补旧身份。

26固定pins匹配，审查前后变化0。完整三源已读；保护段分别逐字核原基线。完整diff仅三文件，逐hunk核旧context零差异，在内存得出新文本与三候选逐行一致；没有apply文件。完整输入与正文/原证据在RV31Snapshot/InputPins/FactsCheck/SourceAfter。

## RV31-P01 — P2：终态比较未绑定首次已核child身份

归属：**Media原owner的过程候选**。不是Review或root修源。Integration真实client的immutable属性/authenticated frame与native单child注册也是必要保证，但不能用未来保证代替当前消费层的身份漂移拒绝。

位置：普通 `CorrectedProposal/Providers/local_asr.py:398–405,478–488`，完整SHA如上。接收时检查child的attempt/launch_id/PID并在405行保存到evidence；清理时484–485只将重新读取的 `process.launch_id`/`process.pid` 与该时刻terminal receipt对比，没有比较首次保存的原值。

静态最小反例：start返回同attempt的child A（launch_id=A、PID=a），后续child属性和terminal receipt共同漂移到B（launch_id=B、PID=b）。attempt仍相同、strict整数return/poll/wait/cached codes都为0、tree/guard事实字段结构有效。484–485仍可全部通过，487清理判known；原JSON/full validator可到590，再由701走succeeded。这个推演证明缺少消费层漂移检查，**不证明真实native发生该行为或OS漏洞已复现**；ABC/dataclass本身也不证明真实注册的属性不变。

关闭条件：首次接收时将同一child的attempt、launch_id、PID分别读取一次并严格验证、锁存为独立primitive/immutable值；evidence只记录这些锁存值。以后child观察、terminal receipt、poll/wait/cached事实都必须与该初始child及同attempt/session/epoch/install域一致，不能用一组后来共同漂移的字段互相证明。任一漂移只走asr_cleanup_failed→unknown，不造成功，不清除原unknown或重新start。原owner补新完整candidate/diff/hash后另独立静态复审；当前hash不批准作为正确生产apply候选。

## RV29-P01四项静态补全与原运行缺口分开

1. `indexed_asr_launch.py:34–50,115–125,244–254` 定义原Operation/run/fence/route SHA，以及发起前attempt/session/epoch/install/runtime/context/input关联；`local_asr.py:365–380` 在record前已保attempt/evidence，contacted在调用前置true。
2. `indexed_asr_launch.py:129–141,269–274` 提供record/no-child封闭受理证明；222–235的private ABI明确record durable但不spawn、start最多一次、no-child必须seal接受。只有认证native frame之后结构判断才有意义，普通字段不是认证。
3. `local_asr.py:459–497` 在start无回复或process尚None时仍用同attempt reconcile_close；没有第二次start。missing child的真实terminal不能造缺失结果（478–479），无证明或quarantine保unknown。
4. `indexed_asr_launch.py:196–203,222–230,262–266` 有控制timeout，消费≤0.25s/剩余deadline，清理独立总5s；native必须实际满足有界性。该表达修补RV29接口层缺件，**不是native实现/持久查询/运行安全关闭证据**。

因此原四项方案要求“已在候选源表达”；当前总体因RV31-P01不批准。RV29原真实注册/guard/运行边界没有通过本批关闭。没有真实protocol/spawn/Job/guard/OS后代或运行授权，不能把source callsite count当真实单次委派/启动证明。

## 其他分支、保护与明确限制

- before contact的参数/cancel/deadline/生产缺口明确前拒；None不默认裸Popen。生产manifest的resource入口只接受indexed launch，DevelopmentAsrLaunch仅显式且无production manifest，标unqualified。裸Popen只在该开发分支（411），不授开发分支生产资格。
- record异常/无回复默认受理不明，经同attempt reconcile；invalid record/accepted/type/ref触发protocol_fault。没有child/launch_id不推未spawn；sealed no-child proof与unknown分开，取消/deadline在已record后仍需seal或终态。
- `terminal_proven:277–285` 严格四int/非bool/一致、sameattempt；local480–485再核poll/wait/cached及已有poll结果。这里已有严格退出码，但初始身份链是新P2缺口；真实内容仍需native actual OS/journal依据，receipt JSON不能自资格。
- 部分stdout捕获先登记再初始化stderr（414–417）；Stream/read/close、writer、外部控制/cleanup/diagnostics/progress的异常被保守标记。finally逐reader/writer用剩余总预算join，未终态/failed/缺半管道未知；writer活不强关锁住stdin。559–560未知压过取消/超时/看似成功；未知保runtime、不自动删除，已知才核自有目录再删。实际线程/文件系统/Job故障均未实跑，不能把这些分支当OS沙箱。
- sealed no-child、actual terminal+线程终态及结果成功三类分开。终态缺失/错码/错响应/quarantine不造结果；取消/timeout清理确认后保原失败，cleanup不明才unknown。原cleanup_failed→Operation unknown接线697–701仍在。
- 八保护段独立逐字一致：完整validate_asr_result、_rational_us、_time_base、_original_context_bytes、validate_original_asr_result、validation_context_bytes、_cancel_requested、_ProcessTree。worker未列diff；原context/stdin/result/progress、_admit/审核/quality未改。不回填旧artifact或继承旧P95。
- asr_resources.py44–54拒controls覆盖launch、固定传播；60–67核binding/manifest/index，再沿原资源字节验证。其isinstance/dataclass/SHA仅事实语法，**不证明真实注册client**。Backend必须从原实际permit和私有固定factory注入，Integration必须把channel认证、注册/epoch/单child关联、sealed proof与held guard做到真实实现；普通request/renderer/MCP/dict/callback不得构造控制权。

原owner AST/Ruff E4/E7/E9/F自然0只支持语法/basic diagnostics。FinalizerTerminal238d16自然0只是候选文档/身份收尾，没有candidate import/call/native/ASR证明。真正ExecutionPermit/factory、native durable Operation→attempt查询与重复/迟到排斥、系统环境/资源index/build/三OS接线仍须其归属者正式冻结及独立证据；类型和未来任务计划不能代真实口存在。

## 最小独立Test与后续具体权限

Test原owner应先在明确纯机制范围设计：稳定初始A正向；PID或launch_id单独/共同漂移B；同attempt但迟到错session/epoch/ref；strictbool/None退出码；start丢回复、record异常、sealed no-child迟到接受禁止；无child终态不得成功。身份漂移负向应unknown且完整validator不被用于洗绿，整个attempt仍只一次start，不由bridge自动补正确字段。

另覆盖每个控制/属性/partial stream/writer-reader/finally异常、cancel/deadline/EOF分别、cleanup预算耗尽和quarantine、客户端失联后native保guard/查询同Op、禁止普通callback冒安装注册。纯double只支持机制，之后真实无模型child/native Job/OS后代/guard失联与真实ASR分别按精确source/resource/argv/env/实例与终态另准入；本报告不授launch。

未来生产权限涉及恰三路径：新增 `services/engine/src/video_creator/providers/indexed_asr_launch.py`；修改 `providers/local_asr.py` 的Stream/启动清理/constructor-control消费；修改 `providers/asr_resources.py` 的可信launch注入传播。无需改公开DTO、worker、Backend SQL、root index/锁/host或protected validator/context。**需先修RV31-P01、另固定正确完整diff/hash并独立审查，才向人类展示该具体变更及剩余依赖请求最终具体source权限。** 本hash不是可盲批准的正确成品；不得应用原W16坏patch。

原自动审批拒绝（具体supervisor/guard持久安全边界授权不足、中断/错误放行风险）与原patch字节保留，无绕角色/tool写入。未授实际ASR/模型/费用/key/网络/安装/部署。本轮全部工具、fixed input/candidate reader终态、live[]已释放；产品/测试/候选import/call/apply/收费/key均0，仅Review文档写。正式FINAL释放，完整R1独立验收后连续R2不缩。
