# RV23 — T20 测试整改候选独立复审

FINAL；SOURCE_PREPARATION_REVIEW_ONLY。原 RV22-P01/P02/I01 在下述精确准备/静态范围关闭。本轮未发现这三个原问题的遗留静态阻断；不批准 Runtime Binding、实际产品启动、任何完整业务批、68 项产品通过或 Gate0/R1/R2。缺真实资源与业务证明保持，不能将整个 T20/full harness 标为完成。

## 固定材料与原标准

T20 Handoff MD f0623bbbc7c3cb4be52f9ca74967aa2343b1596d0d35b459e04e16674e55280b；JSON8735d86ef85f89b4a0b297ea00083e0e0d20f6cdf02f278ed7345a5433c95386。
T20Snapshot b76a1e4a1d68abc2c403914e1007d7ffa4ab90b0eb5ec96c684e0a1697ad59fc；T20CopiesManifest cc9d967545bec82b7ef77b5432f35d426edc5bded49e8b29f8d7148b4eafbb75；Coverage7eea2ce5e9eaa77938b84b721974cdf1217c1494a63acd19300291825561bd54。

独立核 9 个固定 Test 源的 18 个源副本与 36 个历史/实际证据副本，54 项全匹配；另核 5 个 finalizer 普通副本，0 mismatch。OriginalT19 四个归档源与 RV22 固定版本完全一致，旧正文/反例未改。源码后核及 hash 见本角色 Snapshot/FactsCheck/Handoff。没有读取当前 W13、I25、Backend 或任何生产 WIP，也没有持生产 freeze。

| 关键整改源 | SHA-256 |
|---|---|
| tools/testing/T19LaunchRules.psm1 | e633e2e894b518bf02a1a2a2a1104a4db9387f6ff740f88e79f728b48c02c3ab |
| tools/testing/StartT19Business.ps1 | 052c7dffc307cc291d804be95a5d491a890ed61c8901b3d077d6da03eb28fe52 |
| tools/testing/T19BusinessHarness.py | abfb27616723b68677f8ff9654cf2948e968dcd267c0a697827046921ee53c9e |
| tests/bundle/t19_bundle_cases.py | 4b21881250a40452c453a4426715aa9f28bb9e1a6ede94ae37f140f98fbf47ca |

68 项与已批准 revision2 的 38＋20＋10 数组逐值、顺序一致；criterion 字节 SHA 仍为 2f5203983e5c696ad6cb2ee89d81ed2bf7b5d51a31abbdfe5a6f6d9a576b85d2。所有 68 项仍 not_run。max(start,end)、完整独立 N/nearest-rank P95≤200000 整数微秒、MM05 30选题×60作品、来源/权限与原件闭包要求未降低。

## RV22-P01 — CLOSED_STATIC_AND_PATH_MECHANISM；原严重度 P2

固定 [T19LaunchRules.psm1](<G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T20Preparation/FinalSourceCopies/tools/testing/T19LaunchRules.psm1:44>) 44–79 新增无写入 Assert-T19OwnedWriteTarget。从卷根向目标逐层检查全部已存在组件，在更高祖先 reparse 处拒绝，不再仅看最近目录。检查完整自身前缀、输入闭包重叠、歧义组件、文件/目录类型及 RequireAbsent；不存在尾部不会触发写入。合法准备路径由原实验建立 proof/output 时实际使用；这不是完整 starter 正向准入。

固定 [StartT19Business.ps1](<G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T20Preparation/FinalSourceCopies/tools/testing/StartT19Business.ps1:68>) 68–86 先对 DataDir、output、cache 和全部计划收据目标核父链，并拒 source/resource/body/授权文件重叠；首次 mkdir 在90，PrePythonReceipt 在96，Python Start 在115。cache 在创建前另复核一次。原“DataDir/output 高祖先 junction 可漏检、先写后 Python resolve”的静态链已移除。

已有真实 cf0dea/exit0，仅运行一个 Test 自有 junction 路径机制。Receipt0266f9c69400136829b77960cac26f90f90a2254cd4bf1d577f900a14588d39c、CommandReceipt976e3e07ad2b6b9619bb297098b268d09984e7bc518b66addbaa40f58ddd850e。实际 PowerShell PID19668/creation12:52:47.3017160Z；旧归档原三行最近祖先代码接受，四种新目标均 T20_WRITE_PARENT_LINK_DENIED、target_created=false、outside_allowed_files=0。源与宿主前后不变；唯一 junction 以 Literal 非递归移除，先确认 target 保留，再核自己的空非链接目录后删除；link/proof_absent=true。outer wall12:52:47.2786155→49.5022146 与内部实验12:52:48.9941538→49.3983891 分列，不是生产耗时。

关闭范围仅完整已存在父链机制及其静态 starter 接入；完整严格 header/可信宿主/全部写入与 Python启动链未执行，不能外推 race-free、OS sandbox、宿主认证或清理监督通过。

## RV22-P02 — CLOSED_STATIC_WIRING_AND_PER_ANCESTOR_ORACLE；原 P2

固定 [T19BusinessHarness.py](<G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T20Preparation/FinalSourceCopies/tools/testing/T19BusinessHarness.py:214>) 214–227 要求 correction_oracle 与每份 ancestor 原件分别存在于独立批准 Binding 的资源 pin，并核文件字节；238–247 明确将 bundle-correction 派发 consume_actual_correction，不再只有死审计函数。

固定 [t19_bundle_cases.py](<G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T20Preparation/FinalSourceCopies/tests/bundle/t19_bundle_cases.py:139>) 139–145 取真实 service-visible Manifest，先 audit_v03_published，再实际调用 audit_actual_correction。63–93 要求全部实际/预期 corrected artifact、parent/evaluation ID 集合及逐边一致、每份 ancestor 唯一、无额外/缺项/环。96–136 逐 ancestor 使用独立 file_path/file_sha，检查实际 artifact hash/size/原件精确字节、schema/report/internal hash/alignment 声明与正向 dependency；不共用单 expected_origin_file。

12 项 pure 中的关联反例只执行 plain graph oracle：交换边、共用一个 origin、重复/缺 report、多 ancestor、环均按原期望拒绝。没有执行 audit_actual_correction 的真实 Bundle/typed metadata/rights positive；上述关闭仅断言函数的候选接线及逐 ancestor 设计，不能关闭 RV20/RV21 的生产原件许可问题或声称已验证实际发布包。真实独立 oracle、资格/听审参考、原件再分发许可与 published Bundle 仍待外部资源准入及后续真实测试。

## RV22-I01 — CLOSED_STATIC_COMPOSITION_AND_PURE_TYPE_MECHANISM；原 P3

固定 harness31–47 的 call_setup 仅捕获传入旧 guard 类型，保 __cause__、phase=setup_bootstrap、原 exception type 与 traceback frame；not_ready_record 写 exit78/actual_cases0/skip0。actual_context146–156 从真实旧 t16_guard 导入 NotReadyForExecution，包围 admit_runtime 和 B11ServiceAdapter 构造，再传真实该类给 call_setup。main230 的 actual_context 后，在255–257 捕获新 NotReady 并输出结构化 JSON/78。普通 RuntimeError/AssertionError 不进入转换，不能洗成准备不足或通过。

已有 9a0161/exit0、Python exit0、12 checks/0fail/error/skip，stderr明确 Ran12 in0.001s。PureReceipt e8f54e1425abe9451187b659470269b9f37cf714f1b0037360d8302bdbe12afc；Command73945bb32b7a67d465637bb0434ca9504b6dbc00f9ed5dedb8a7efdf667a05e7。机制使用真实旧 NotReadyForExecution 类，比较旧本地 NotReady 不同类，并核 cause/frames/structured 字段及普通失败原对象不被转换。其阶段只 import Test-owned stdlib 顶层及数据/分类函数，没有运行 actual_context/main/service。source_changes=[]、blocked_product_import_attempts=[]。

解释器为 Integration/Runtime/Python/cpython-3.13-windows-x86_64-none/python.exe，前后 SHA ed57c54b4fca7ef7e0e77e791129c32a516a4b8efbd814b06ccb12212f437d50；并非正式 root .venv 服务执行闭包。wrapper wall12:57:23.9356466→24.2121351、pure receipt 时间窗约0.0020735秒、unittest0.001秒分列。三个 PS Parser.ParseFile 0 只是语法。不能借 pure12、旧T19准备13或 finalizer 绿称新完整启动器已运行。

## 准入限制与最终交接

已读正式终态：finalizer116816/exit0，固定五个普通副本匹配；只归档/序列化。原55aa89读错文件名工具失败及纠正保留，不冒充产品红；原四源、原标准、所有旧失败和新有限绿保留，未倒填历史版本。

当前仍缺执行 PowerShell 前可信宿主认证、独立外部 immutable pins 与完整 Python/site/native/PS/source-resource/body 闭包、当前最终生产 Binding/Review 准入/Root 精确运行授权。角色目录不等 OS ACL；现 CIM PIDCreation/Parent 查→Stop-Process 仍非 Job Object，TOCTOU 和未观察子孙/完整清理未证明。

6 个 batch 派发名称（19 service＋1 HTTP＋4 Bundle batch）不是完整 68 executable case mapping；实际业务运行均0。独立 OS 非once持续Worker及第二Run、真MCP宿主、资格/rights/素材/参考听审与独立标注 fixture/bootstrap、完整视频成包/崩溃消费/跨实例、MM05、三OS/native/TTY/signal均未通过本片。模板或 plain 图不算 Agent 自主作品，Test不创建自准 authority、不修改 rights/precision True、不编造 published 行。

本轮只保存独立评审产物，不实现、不重跑测试、不启动产品/ASR/解码/API/Worker/MCP、不授 Binding。全部读者及工具终态，无缓存生产 reader/freeze/live handle；正式 FINAL 后释放槽。原完整 Gate0→R1 三OS独立验收→连续R2、实例持有数据、五步前台与权限/费用边界保持。后续由原 Test 实现剩余驱动/准入并提交新固定资源；独立 Review 与 Acceptance 各按职责继续。

