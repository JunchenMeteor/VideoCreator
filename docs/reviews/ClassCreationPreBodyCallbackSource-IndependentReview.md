# ClassCreationPreBodyCallbackCorrection 独立源码复审

结论：**GCTS-P01 仅在本固定版本的 SOURCE_STATIC 范围关闭（CLOSED_SOURCE_STATIC_ONLY）**。未发现新的确认 P1/P2。已有5项自有完整 Test 源码＋真实标准库机制证据支持新增类体前回调门；它们没有运行 Pydantic 或产品19项，不能关闭原 GRTSD-P01 的实际兼容性问题，不能批准第四个等价目标或完整运行/安装资格。

## 固定身份与审查范围

任务卡 `G:/开发测试/Projects/VideoCreator/docs/task-board/ClassCreationPreBodyCallbackSourceReview.md`，SHA-256 `53022abd5a31cc1200b821913988c7f3cd22ed16901c7b76b3f568b5d07f9654`。

本轮只读原停止交接 `G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ClassCreationPreBodyCallbackCorrection/`，实现/原结果正文来自普通根 `G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/ClassCreationPreBodyCallbackCorrection/`。正式索引定位47普通件并全部独立核对大小/SHA，无差异。52初始有限输入加11历史固定引用共63唯一输入，末核无变化；其中旧/新候选和1018运行前后记录仅作既存数据逐值比较，没有重新扫描3733/1018物理环境。

| 文件 | 实际 SHA-256 |
| --- | --- |
| PreBodyHandoff.md | f64b63b51d0e7f6fcfc5187123c55ef98d04d9bdb9a6fc4997b47c7d41ed50ea |
| PreBodyHandoff.json | 45bb9f1e1a44d5ae6039d21252246ceb72ac878118b5596afc9c592750820dce |
| 原根 PreBodyOrdinaryIndex.json | 063a674f1331522b50ca078a1ed1aa4508e884d1117b25f5179d0238b33b50a9 |
| PreBodySnapshot.json | c5f4054589112d6dfcbd4514f0bbeab0f8071da8b5b30a6a84480c003b38e882 |
| 新 ClassCreationTransition.py（8584B） | 0fde353851d1e92b23bd915c687391712836357b6c0c968f11339a4b529c078d |
| 旧 ClassCreationTransition.py（8162B） | 8d49a0947ffe9e4479521b7b185ab48c5ccbddcc82bcd50d04a11ef5f29188bb |
| FullSourceDiff.md | acdd5de698f8820ea352a864339e33e91ab589b79ffbdf5e3cc94ff8fe390539 |
| 新 GoalReceiptInputIndex.json | ca533118fcee6b68dbfbb3050aa0165fab71c0c5f17ff8d438dbfeccb0344d78 |
| 新 GoalReceiptLaunchRequest.json | 007199118b09bac640a0101d25071c04b73be0b9a9ba6c508d30afc2d9e19d9b |

## GCTS-P01 的准确闭合条件

原 GCTS-P01 是 Test 守卫遗漏：原 helper 只在 `episode['body'] is not None` 后验证回调，原 builtin 创建期间的 `__prepare__` 等 Python 回调可先于类体执行；当时没有原运行反例，本问题属于源码层。

新普通 `ClassCreationTransition.py:65–90` 保留原 builtin 对象/原创建 owner 的 episode；76–79仍先识别真实原类体，并要求它的直接调用 owner 是该原创建 frame。80–89把剩余所有尚未返回的 episode 回调都纳入原 `authentic_call`，依据实际 body 是否已见记录 pre_body/post_body。回调需满足强原 CodeType 树、真实模块对象、该模块原 globals；标准库路线还需原函数代码和固定 fingerprint。没有新增按回调名、文件名、类型名或库名豁免。拒绝在 callback 的 profile call 时抛出，早于该 callback 函数体。

共同 `calls` 列表仍有128上限；两个新增计数只是诊断，不能代替认证条件。65–69与91–118没有从 builtin c_return 读取类结果的行为。成功返回后仅保存已观察的 namespace 检查点，actual class 仍只能在119–136的真实 original dataclasses.wrap 首次强绑定；138–145和原 SourceDomain 的后续 require_bound/原 builder/原 process/namespace 核验保持。

独立对旧/新完整 helper 的所有类方法 AST 比较，只有 `observe_profile` 改变。独立从完整旧/新源码重建 helper39行与单独新 pure harness210行的全部 unified-diff hunk，和正式 FullSourceDiff 文档逐行一致；只排除描述性文件标签及 Markdown fence 分隔空行，不归一代码。它是两个实际差异段，并非“完整源码 fence”；先前派生的完整源码匹配为空、包括文件标签的比较 false 是文档格式不同，后续正确 hunk 比较为 true，不是源码差异或测试红。

## 五项既有实际样例与调用链

完整读取新 PureGeneratedTypeChecks.py、PreBodyTestsBody.py、PreBodyFixture.py、UnregisteredCallback.py；五方法在实际 harness 与独立 body 的 AST 相等。实际 profile 先调用原 Probe.profile，再调用可选透明 fault；guarded() 创建真实候选 Boundary、安装同一 profile，finally 撤回 profile/ACTIVE/FAULT/GENERATED_TYPES。没有用假 episode 或手动调用 helper 跳过正常 loader/profile/class 流程。

原 ProbeGoalReceipt.py:205–239 仍首先调用 GeneratedTypes.observe_profile，原产品/provider/native/vault/Owner/Daily writer 守卫保持；DataclassSourceDomain.py:51–82仍仅通过原 SourceFileLoader.get_code→exec_module→真实模块执行登记 whole source 的原代码树/模块/globals。只是文件固定、未登记来源域的模块不能进入该允许路线。

| 原实际样例 | 独立核得的支持 |
| --- | --- |
| test_01_authentic_prepare_nested_and_after_body_callbacks | 真实 metaclass.__prepare__→nested_prepare→类体→__new__→标准 dataclass；断言实际值42、三项callback sentinel顺序及body sentinel；原Events记录13个回调=4 pre_body＋9 post_body。 |
| test_02_equal_content_foreign_prepare_code_before_body | 通过 originalCode.replace() 制作内容相等但对象不同的 CodeType；真实 build 触达准确 class_creation_foreign_callback；callback_code_id 与注入代码一致，pre_body、body_seen=false，两个 sentinel 均空。 |
| test_03_original_prepare_code_foreign_globals_before_body | 保持原 CodeType、换为复制 globals；真实 build 在同一门拒绝，同样精确匹配代码对象/阶段/未见类体，sentinel均空。 |
| test_04_pinned_file_without_allowed_callback_record_before_body | whole文件已固定却没有 source-domain record；真实 load 不等于已获回调来源认证；真实 build 被同一门拒，包含该模块 EFFECTS 的三个 sentinel 均空。 |
| test_05_real_ordinary_generic_class_body_is_not_foreign | 真实 Generic 类体与标准 dataclass 得到值7，实际 authenticated_source_domain；原Events的创建回调10=2 pre_body＋8 post_body。 |

负向三项均同时检查真实抛出的准确 predicate、实际 profile 关联和副作用前 sentinel，不能由后来无关错误满足。14原 Events 逐条读取，其中创建/拒绝记录与 ActualCallbackFacts.records 完全相同；其余真实 source-domain 记录保留六项原对象关联为 true。计数/声明不是 sole oracle。

原 Cases 五项均 success，JUnit恰有5 testcase、0 failure/error/skip，stderr原文 `Ran 5 tests in 0.113s / OK`；stdout/Summary 5/0/0/0，summary elapsed `0.5114274000079604` 是含 after hash/结果整理的窗口，不混同 unittest0.113秒。

## 原进程与输入保持

读取原 PureLauncherRoundOne 的 LaunchReceipt/CommandReceipt/stdout/stderr，以及完整 RunPureBoundary.ps1。原 Python PID29352、creation_filetime100ns=134361215649212970，记录真实 original Process.started/terminal、actual_exit0、stdout/stderr双byteEOF、timeout_sticky=false、errors=[]。argv 使用 own固定 Python `-I -S -B -X utf8`，--expected-pins 为4d15b7328e26586b30531df7a72fdd481da95c1488ec786c1000f475caee1d06，cwd为新停止根。90s timeout仍sticky红；finally只继续等原 Process并取该实际ExitCode/两pump GetResult，不强杀、不重开。读取原记录不能代本评审重新执行或全OS资格。

原1018份 InputBefore/InputAfter全映射相等，且逐键/大小/SHA和 PureInputPins.records 全相等，changes={}。新3733候选逐记录保留旧3714，没有把旧身份改填新绿。DataclassSourceDomain、GeneratedTypeBoundary、GeneratedTypeCatalog、ProbeGoalReceipt、GoalReceiptCases、Python/PS两入口及PositivePrerequisiteMatrix共8文件与旧普通版本逐字相同，原19名字/次序/断言/90s/5s保持。旧11项是先前独立批，未在新5项中重跑；新5项不得继承为11项全回归或替代原19。

## 保留范围、归属与终态

GCTS-P01：P2 / Test / **CLOSED_SOURCE_STATIC_ONLY**，仅绑定本8584B helper及上述来源链和5项原机制支持。没有发现新的确认 P1/P2。原 GRTSD-P01 真实 Pydantic/来源 transition 兼容性、class首次可见绑定的实际目标范围仍 **OPEN/NOT_PROVEN**；旧actual失败中 namespace成员/key/value未捕获，本报告没有补猜。c_return不是类结果、strong tuple/计数不是运行资格。

三次实际原19目标已 exhausted，旧1error18NOT_EXECUTED、17pass1error、另外2项、12/11旧pure批全部保持原身份/结果。新LaunchRequest仍 runtime_approved=false / lawful positives NOT_READY。新5项是自有 Test 源与真实标准库，不是 Pydantic/Engine/SQLite/HTTP/MCP/Owner/native/媒体/精度、安装/三OS或R1/R2验收；本报告不授运行、不代人类审批、不修改标准，也不导入候选。完整R1独立验收后连续R2目标没有缩减。

自身读工具408304、fccaea、6e3111、6142d4、556b5d、08a074、8e15d7均自然exit0；08a074的JSON包装显示截断只导致Domain中段缺页，该47–82段已8e15d7补读，未据截断声称全文。原工具与结果全部保留。末63有限输入无漂移见本过程InputAfter.json。报告写入工具终态及最终工具/读者释放以随后 FinalHandoff.json/FinalizerTerminal.json 记录为准，不由文件存在推断终态。
