# T56 DTO grammar 独立组件评审

结论：**LIMITED_DTO_GRAMMAR_SUPPORT**。固定修订批十二项确实到达真实原 DTO/Pydantic 校验，独立核对未发现本片新增 P1/P2。仅认可下述组件证据，不授予 Owner、原生通道、系统权限、CLI、B42 恢复或 R1/R2 验收资格。评审未导入或执行产品、测试、DLL、数据库或服务。

## 固定输入与版本

正式根为 `G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/OwnerSetupValidation-T56/DtoGrammarStdlibRevision/`，普通副本根为 `G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T56DtoGrammarStdlibExecution/`。独立检查 53 项原件/副本的 size/SHA，全部匹配；有限新增旧失败材料见 AdditionalInputs。输入前后核验结果见 [DtoReviewInputAfter.json](G:/开发测试/Codex/VideoCreatorImplementation/Review/DtoGrammarIndependentReview-T56/DtoReviewInputAfter.json)，未扫描实际运行环境或系统 DLL。

| 文件 | SHA-256 |
| --- | --- |
| T56DtoGrammarExecutionHandoff.md | daa60374abe2fa65cac1b6866dd699abd4150029114bfb0a70da778724e17a0b |
| T56DtoGrammarExecutionHandoff.json | bd0e9cbc73ddfa8d402634eba4faa26ee08e3553e703e2eb913308cb7da80e85 |
| T56DtoGrammarExecutionSnapshot.json | c404fed0bdd654e3c36f3255a913b0debe7048401e92f41f3e82e7c04d96a999 |
| T56DtoGrammarOrdinaryManifest.json | b6f3c5a5288fb400be13f638fa0dcd1b05fcfae0e357d8e42f087e9748ade1e0 |
| ProbeDtoGrammarRevisionT56.py | b0ee8335d43aaa4e61a6f7b8f5338b8b050bfdde3e5925f5267fe34d1a42ba6a |
| 原 ProbeDtoGrammarT56.py | 4d65d168effc54e9336cfc80ce8621b3439d5c9738de84cb2c82d1f7a929cd5b |
| 修订运行输入索引 | 8ffb0055670018941a8043bb11f20c1bb086de9a5017e71d2cb2878eaeb61245 |

## 原失败与窄修订

原批的 MethodRoundOne/Stderr.bin 从原 Probe.main → Cases.bind → owner_setup/daily_project_authorization/native_execution_registration → held_authority/windows_authority_pipe → 标准 ctypes 冷导入；标准库 `windll.kernel32.GetLastError` 经 `ctypes.__init__:379` 发出 `ctypes.dlopen`，被原审计规则拒绝。原 child PID14544、creation134360633564864090 自然退出1；原外层退出1、forcedfalse 与双 byte EOF 保留。未生成测试 Summary/JUnit/Methods，十二方法为 **NOT_STARTED**，不能记作十二个已运行产品错误。缺 Summary 的原生命周期记录仍保留。

完整 FullSourceDiff.diff 只涉及 Probe、Python runner、PowerShell runner。独立解析原/修订十二方法 AST 和完整 Cases 类 AST 均相同；所有原断言保持。Runner 更换固定命名空间/索引，90秒原持有等待机制保留；没有修改产品 DTO 或用 mock 替代原模块。

新 Probe 的 `initialize_standard_ctypes`（90–122）在产品导入前开启一次专用阶段，`finally` 撤回 `STDLIB_INITIALIZING`。`standard_ctypes_event`（73–87）限制原固定标准 ctypes 调用栈、模块名、仅 `('kernel32',)` 且不能重复；audit（125–146）在该阶段外仍拒新 DLL、进程、网络等调用。实际 StandardCtypesInitialization 收据记录一次事件，三标准模块 path/SHA 与原索引匹配，kernel32 handle 非零、pythonapi 与原 sys.dllhandle 相同。**没有观察实际系统 DLL 的绝对加载路径，也没有另跑产品阶段新 DLL 加载的负例**；撤回规则是源码证据，不能虚构额外故障运行通过。

## 实际到达与逐项关联

实际 `Cases.bind`（167–192）以原固定模块的 `__file__` 与完整 SHA 校验，十三 product 模块逐名/path/SHA 和普通正文副本对应；首个 whole_original_modules_loaded 事件与 ActualLoadedModules 同值。版本来自实际导入的 Pydantic **2.12.5**、pydantic_core **2.41.5** 校验。模块加载包含 windows_authority_pipe 类定义，不能由此推断 Win32 客户端构造、连接或权利确认已运行。

| 方法 | 实际组件范围 |
| --- | --- |
| G01 | 完整 draft 身份与序列化往返 |
| G02 | 新 create receipt 四项身份必填 |
| G03 | 版本、时间、hash、完整正文篡改拒绝 |
| G04 | 严格整数与未知字段拒绝 |
| G05 | expected Owner 精确身份对约束 |
| G06 | status 不得授予 api_ready |
| G07 | 本地路径语法；不检查实际 OS 对象 |
| G08 | native origin 序列化语法；不生成真实确认 |
| G09 | api/mcp/worker 三角色完整且唯一 |
| G10 | goal 字段保留、错格式拒绝 |
| G11 | 有限选项、expiry、native 入口及质量/权利字段约束 |
| G12 | 完整请求 DTO 往返、缺字段/未知字段拒绝；仅 proposal |

十二方法与 Summary.nodes、JUnit 十二 testcase、十二 test_started 和十二 test_finished 按名称与先后时刻逐一匹配；各终态 failures/errors/skipped 均空。实际 stderr 为 `Ran 12 tests in 0.115s` 和 `OK`。93 个事件另含67个 model_rejected、一个 canonical_proposal_only，不能把子负例/事件计数当作额外业务测试。

Methods 的237个 key 与 Summary.actual_methods 逐值相同；其中 includes 类体/模块体定义事件，不是237项服务测试。实际 validator profile 包含 complete_original_create:8、setup_sha256:61、never_api_ready:4、complete_roles:2、original_goal:9、finite_original_scope:12。完整逐项校验见 [DtoReviewFacts.json](G:/开发测试/Codex/VideoCreatorImplementation/Review/DtoGrammarIndependentReview-T56/DtoReviewFacts.json)。

## 原进程与身份收束

原修订实际调用链为 PowerShell launcher → 留存的 Python runner → 留存原 probe。两层原 CommandReceipt、ActualCommand 与 retained wait 对齐：

| 层 | PID / creation FILETIME100ns | 终态 |
| --- | --- | --- |
| PowerShell 包装层原进程 | 36308 / 134360644492107059 | actual_exit0、双 byte EOF、无 lifecycle error |
| 原 probe | 18824 / 134360644499524473 | actual_child_exit0、forcedfalse、双 byte EOF、无 lifecycle error |

ActualCommand 的原 `-I -S -B -X utf8` argv、固定索引 SHA 与关闭环境保留。Python runner 依原 Popen/creation 等待与读取两原流，PowerShell 依原 Process 持有及原 BaseStream 泵收束。原 Test 实际工具 e2294b/session77521 →1db857 自然0；本评审仅分析既有证据。

原索引、InputBefore、InputAfter 的1281条捕获 size/SHA 映射逐 path/值全部相同。此为历史运行保存映射的完整比较，不是评审重哈希999份环境/233份依赖，也不证明环境或系统 DLL 的安装资格。

## 发现、限制与交接

本片无新增阻断 finding。支持固定十二项 DTO grammar；原失败批未改写。没有 CLI parser、SQLite、真实 Owner/确认、native 权利服务、API、MCP、安装、ASR、媒体、三 OS 或 B42 applied candidate 的运行证据。G12 canonical proposal 不等于 accepted/authorized。B42 和既有 RV80/RV82 运行项、审批同期 raw 缺口由其独立片继续处理。

评审解析的输出截断均保留：62d66a/1ab570/47f5f5/92d8ca/e1fd61 的大输出不能声称全文展示；后续定向读及完整标准库解析才构成本文字段证据。评审工具 fb4652 因将事件字段误读为 event 发生 StopIteration/exit1，cf0d7c 按原 kind 字段纠正，6e25aa 全部有限交叉检查 errors[]/自然0；没有重跑测试、修改原期望或改变原红绿。

评审读者已释放，无生产冻结、产品/测试执行、网络、费用、凭证读取或安装。完整 R1 真实作品/多模态及三 OS 独立验收后连续 R2 的目标保持未完成。
