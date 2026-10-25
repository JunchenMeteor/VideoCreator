# BCF-R01 诊断输入缓存生命周期修复独立评审

结论：原 BCF-R01 在本固定版本仅 CLOSED_SOURCE_STATIC_ONLY。新旧 lease/fence 缓存选择问题已获源码支持；尚无 SQL、Worker、产品或恢复运行验证。另确认 DALI-P01（P2，Backend，OPEN_SOURCE_STATIC）：已关闭旧端口重复 close 可以清除后来同一有效 lease/thread 端口的真实 factory 与诊断记录。这是继承清理段的缺口，不能称本次补丁新引入，也不能因原 finding 窄关闭而忽略它。整体验收、BDE-P01/P02、0062实现与 R1→连续R2均未关闭。

## 固定范围与独立证据

当前任务卡 G:/开发测试/Projects/VideoCreator/docs/task-board/DiagnosticActiveInputsLifecycleIndependentReview.md，2587B，SHA 5406af2920c0419548e1d1063e15711d83d77a9e72fc14eb95c4d61ecf442644。已全文读 workspace/repo AGENTS 和最后 activation。源码只用正式索引 ordinary_copy，不读取 source_path 生产路径，不读热 Media/Architecture 或其他后继版本。

新根：G:/开发测试/Codex/VideoCreatorImplementation/Backend/DiagnosticActiveInputsLifecycleCorrection/。

| 正式件 | SHA-256 |
| --- | --- |
| Handoff.md | 0fe961a001be2aba68ee5b60a098b8eab204412652c3cdd4f21164f18382106e |
| Handoff.json | 339efe5fea9c4478c6569de639a480c383e7f5f4b8610a714c0d3c952b271f98 |
| Interfaces.md | 8317fcf6b35d8386c112aad765d37f035fd3cff2656228b362e003288d0955dc |
| SourceStage/SourceIndex.json | ebb818fa78044533eb8ca924a445f732e02c8f8feed5eae48d2291140d06e9f1 |
| SourceStage/FullDiff.patch，7600B | c100e196ef350e65b30fca759710541b7f4e7d312ad888818d8ef788f1f7d1ee |
| SourceStage/MethodLocations.json | 27db8d8f8f693c1b251a4c3047ca1e1306178aaeb83edbbb3532c65a43f31223 |
| SourceStage/StaticChecks.json | 9d3c6c1f8924ef666785759eaa02d50f0253426dc85cc4ff596f32f2b77ba6b5 |

旧索引：G:/开发测试/Codex/VideoCreatorImplementation/Backend/CombinedFailureDiagnosticRecoveryImplementation/SourceStage/SourceIndex.json，SHA 41b2f0e2650b10b97a7353a574e5f131164ae9a597d763435df11c5ab912c83d。原 finding：G:/开发测试/Codex/VideoCreatorImplementation/Review/BackendCombinedFailureRecoveryIndependentReview/Finding-BCF-R01.md，3736B，SHA cdd63c85bd22e83aeed6414e0a6f13932c4eadfe700b643bf7c9964baea85e21；原件未改写。

自身过程：G:/开发测试/Codex/VideoCreatorImplementation/Review/DiagnosticActiveInputsLifecycleIndependentReview/。InputBefore 为146有限路径（完整新130 ordinary、旧三改动普通源、两个索引、规则、正式件和原 finding），InputSupplement 为四份原 Worker/factory/join 普通源；150路径末核无 byte/SHA差异。两个索引完整130键逐项对应，所有 before_sha 等于原索引，127成员版本SHA相同。本次没有重读旧127无关正文；其比较等级是已固定索引关系与完整新 ordinary 身份核，不冒全旧130再逐字审读。

三份变化源码全文已读：component_diagnosis_service.py 835行；current_final_evidence.py 179行；diagnostic_selection.py 533行。完整7600B diff逐文件、逐hunk用原三份停止普通文本在内存重建新完整 UTF-8/LF字节：2/3/1个hunk，共三文件均精确匹配。该自有文本核对不是产品测试。DiffProtection.json SHA f1b1f7490e774db0f3e733847d5a7d9e4e51ae1066b3905b4848438e2450dd9d。

| 改动源（相对 services/engine/src/video_creator/application/） | 新完整SHA | 原完整SHA |
| --- | --- | --- |
| component_diagnosis_service.py，69138B | 5e3efc3a0eb54d0c43d32a2737683032199e52c414035527b1f9891c8d997271 | a2747f788f03cb5d207685d7b56d400b6856fbb36814c1b91726dd916af2bd15 |
| current_final_evidence.py，11600B | 96c99854db5e08853266a1bdddc743c5f1ac8ddbbb41042f4c685ce49c6f020b | 6cdbdd5c9789bf88a27c9fb243e4712138f9469a337e1a4b73948e918cf5379e |
| diagnostic_selection.py，43981B | 2b05e9f36a92e85ed2a4826a51afcb14b384198d0f1dead1367e3def18ff1e0b | 4de38cab02bae5bafccbf37f3db6547abfe5708d792c073b6052f0dae2192078 |

三者绝对普通根为新根下 SourceStage/SourceCopies/services/engine/src/video_creator/application/；InputBefore 保存每个完整绝对路径，不以相同叶文件名替代归属。

## 原 BCF-R01 的源码修正范围

1. 实际 owner 来自注册端口。current_final_evidence_service.py:30–41 经 Engine lease 与 bound_context 实际绑定后登记原对象；current_final_evidence.py:35–44 要求登记对象本身、当前线程及原 lease，再查 Engine。新公开端口 prepare_component_diagnosis:130–132保持原签名，传 owner_port=self 至私有 service。没有公开序列化 grant 或允许调用者传一个自声明身份。
2. component_diagnosis_service.py:311–321 私有省略 owner 时只解析同 lease/thread 的实际登记，零/多候选403；显式 owner 必须登记对象、同 service、原 lease/thread。322–352继续实际 factory、方法来源、完整父事实、原账本/issuer/current transaction和资源检查。353–361在 RLock 下再次确认 owner 未关闭，保留原 held 前六项，加实际 owner 第七项；active 键加真实 fence，值包含实际输入、lease、线程、owner。
3. diagnostic_selection.py:220–240 在相同锁下只取本 Run/preparation/thread/fence 的条目，核完整 lease、线程、实际登记owner、同service、owner lease/thread、held input本身、held owner及parent fence。无效条目只在原 key 仍持该 exact entry 时剔除，后续到原 selected分支。有效 active仍调用 read_recorded，没有捕获 EngineError/403或在来源错误后放宽回退。
4. current_final_evidence.py:164–167只清 entry.owner is self 的 active；176–179 对诊断 inputs 按实际 owner保留另一端口输入。不同 Run、lease/fence或 owner 的 active并未按 Run名称批量清除。这些新段在同 BundleService RLock内执行，遍历 tuple稳定快照。
5. component_diagnosis_service.py:364–391 原 input身份、lease、线程、parent fence和完整 current/source检查继续存在，新增 owner登记门。375起完整校验尾与旧方法同字节。current/source变化仍403/409，不能以“缓存无效”吞掉。valid active 的 read_recorded:520–536 仍只查唯一输入结果及 exact legacy selection，不取latest；selected回退:241–246 原字节不变，仍查 Engine lease、当前指定 preparation selected、strict ref并进入原 immutable reader:741–803，重验 factory/method、输入完整body、来源/Operation、实际 verifier和issuer/current事实。

因此原反例“关闭旧lease端口，同线程同Run/preparation新fence，未再次prepare却命中旧active并在403提前挡 selected”不再由该缓存选择逻辑产生：新fence键不命中旧条目；关闭旧owner也清其active；同fence stale owner在进入active前被剔除。这只是原 finding 的指定 SOURCE机制闭合，不宣称存在合法 actual selected、实际恢复已通过，也不推所有错误都会回退成功。

多端口边界没有凭“输入不会串”宣称并行生产受支持。原 _final_binding:43–53要求同 lease/thread恰好一个登记端口；两个同时登记即拒绝，省略 owner解析同样拒绝。当前唯一合法端口的输入不能换到另一登记对象。后述新反例是先关闭旧A、再建立唯一B后的重复旧close，区别于同时两个端口通过原门。

## DALI-P01：继承的重复 close 清理缺口

详细正式早单：G:/开发测试/Codex/VideoCreatorImplementation/Review/DiagnosticActiveInputsLifecycleIndependentReview/Finding-DALI-P01.md，5138B，SHA 52ada4a069c164a4dff72f4d9391acce633eda60e87539917fb679e70ed1493c。严重度P2，Backend，OPEN_SOURCE_STATIC；未运行复现。

最小条件：同一实际 service/thread 和仍有效的同一个 lease/fence，A已正常close；原 trusted factory重新登记此lease的真实services，然后原 current_final_evidence_ports创建唯一B，B通过所有原门prepare实际inputs/record。保存旧A引用的消费者第二次close A。

current_final_evidence.py:162–163仅在A仍登记时pop，若已撤销没有early return；168–171继续按旧lease/thread删真实 _production_services_held，172–179除inputs的owner特例外继续按同lease/thread删后来B的records/source_reads/selections/outcomes。新active和inputs B得以保留，却不意味着B的依赖还在。有效active→diagnostic_selection:229–240→read_recorded:520–521→_diagnostic_inputs_current:375→_diagnostic_factory:104–110→_affected_services:65–70，由缺失真实factory抛 production_services_source_invalid（403），挡住selected。没有active时selected的完整reader:741–744也需要同factory。

原 factory登记来源是 media_registration.py:317–324和326–350，经唯一实际服务类型、Engine/Worker/Executor、原issuer/current、人审/Policy及manifest绑定才登记；本条件不以double造权源。原 _final_binding 唯一端口门满足，因为此时只有B。旧130 current_final_evidence.py:159–172已存在共享清理与缺少撤销后return，因此是本轮确认的继承缺陷，新owner保护没有解决它。实际 Worker finally:825–834调用原close，但本审未证明现场Worker一定产生二次A.close与同fence重建顺序，不能写成Worker已运行故障或权限绕过。

Backend最小修复应让已撤销旧端口重复close不再影响后来实际owner对象，同时保首次关闭自身缓存/资源和所有current/source拒绝；若允许多owner，需按实际owner处理其余held依赖。不能删除factory唯一来源门、吞403、清整个Run或为恢复新授费/预算/权限。需要独立Test真实登记和观测后才可运行关闭该问题。

## 原调用者和保护核

以下四个停止调用者全文件新旧 SHA 实核相同，原字节保持：

- media_registration.py 72ce559d18adb2bef283e3cb7fe9de4453f9c1ee3a173386601459286e483681。_invoke_current:384–407实际恢复先current services、claim、创建final ports、登记_active_final_ports；初始:440–445同入口；Worker finally:825–834取出并close实际端口，保原 source清理；没有新增Test影子cleanup。
- current_final_evidence_runtime.py 604327bb8e6ee51d1a30926bef58031a01e88c0f0927f5f0f36b0c079ff3783c。_final_producer:72–91取同Engine真实binding、登记port、assert实际services、原Mediafactory；构造失败close并原异常重抛。
- current_final_evidence_service.py cc3956af0ae7fc346622a61a4ed7f975c877bc790c12500dae2770c240a954b1。275的原whole verify及失败/等待/QC/成功后305–321都走当前join读取；finally322–324原scope释放；未新增第二whole verify、吞泛EngineError或成功伪token。
- affected_repair_service.py 344c9ef354dbcd0563aed45c0990ecbbacdcbb5c9df8d0c7a199d825d5a4749a。65–72唯一真实factory、566–594真实service/Engine/Worker/Executor/registered身份、issuer/current/request、资源manifest与模式门完整保留。

public prepare签名、新输入构造之外原 immutable登记writer、Operation successful+settled/actualcost、strict方法与实际factory verifier、200000us来源、原affected/counter/ref/账本/unknown/人审预算规则均没有diff修改。119 AST 是作者 stdlib 静态检查的历史证据，本审没有运行AST/产品/Pydantic或把该数当行为验收。原作者33a096定位失败、606a48叶文件名选择错误及其校正记录保留；不是产品失败或新运行资格。

## 后继必要动态覆盖（未授权执行）

- 原BCF精确顺序：actual A prepare/record→原close→同Run新fence/同线程→无需reprepare的actual selected读取；各精确ref与完整body/Operation/current门仍须真实有效。
- valid active必须实际进入原current和完整source校验；错误current、错fence、错线程、错误service/owner、改变source时保持拒绝，不允许catch403转selected蒙混。
- owner省略零/多匹配拒绝；当前单owner、不同Run/preparation/fence隔离；关闭A不能移除B的active/input；原同时两个port唯一绑定拒绝保持。
- DALI-P01同lease代际顺序，观察后来B真实factory、inputs、records、selection/outcome，并核旧A重复close与B自身首次/重复close；不要以删factory保护或Mock替真实权源。
- 实际Worker finally、实际后续Media复用与新fence恢复、真实SQL竞态、unknown/预算/permission控制与端口跨线程生命周期仍未执行。

这些是缺口与最小验证条件，不是新Test标准批准或runtimegrant。旧19第三次限制、原失败、provider/费用、安装与三OS/真实作品/完整R1后连续R2的要求未变化。0062仅此前设计支持，本版本未实施child选择/v3/terminal等新合同，不能以本cache修复关闭BDE或整链。

## 工具与正式停止

SourceStage/FullDiff的准确路径来自Handoff；自身583aa5/1误用根FullDiff简称保留，3cbfe3/0按正式引用纠正。3f1646/1原rg二进制路径失效保留，cd2c17/0 Get-Command仅定位当前9a7ba4b9ea0c44a3/rg.exe，再只检索索引列出的130普通件。8e850f/0合并源输出截断，确实未完整显示的段以7e8bf9/bec662/924588/a55348/d70652/131758/e4b342分段补齐；346989/0 factory短段输出截断以b806ac/0的326–351补读。没有把截断当全文、没有重启live工具或重跑产品。

截至报告写入，先前所有工具均自然终态，无live handle；本次150必要末核已完成且差异为空。源读取结束，不再持任何源读窗。报告生成工具的最终自然返回将由FinalizerTerminal/FinalHandoff和本人FINAL外部确认，文件存在不代工具终态。只写docs/reviews与自身Review过程；实施、标准、Test及生产源写入0，产品/SQL/Pydantic/native/模型/网络/安装/费用/秘密0。
