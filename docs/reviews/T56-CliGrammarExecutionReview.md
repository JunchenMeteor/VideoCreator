# T56 CLI 原始请求语法：独立执行证据复核

结论为 **LIMITED_CLI_REQUEST_GRAMMAR_SUPPORT**。固定原 B41 完整 CLI 的 `_request` 十二项原语法断言在本轮确实到达并通过；原十二方法 AST 和断言保持，原始两轮导入失败各自仍为 NOTPASS / 十二项 NOT_STARTED。**T56-CLI-P01（P2，Test，OPEN）不因十二项绿而关闭**：Windows 路径字符串比较失配使 Methods 记录与同分支 before-body deny 不生效，不能用空记录授予业务行为或禁用动作未发生的证明。

本报告仅续审执行固定件，不覆盖 [原源码报告](T56-CliGrammarSourceReview.md)。评审没有导入或执行 Test/helper、产品、Pydantic、keyring、数据库、native、模型或 ASR，没有改源码、断言或标准。

## 固定输入和身份

正式根为 `G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/OwnerSetupValidation-T56/CliMetadataReaderRevision/`。执行普通根为 `G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T56CliMetadataReaderExecution/`。五正式身份如下，完整普通路径及前后检查保存于自身 Snapshot / InputAfter。

| 文件 | SHA-256 |
|---|---|
| T56CliMetadataExecutionHandoff.md | 04038fc7d8b146866fd6c767695b491403fcdb5253306dd73bd108da9d1ebeb5 |
| T56CliMetadataExecutionHandoff.json | 42959858277f2906099e77519953cb7fbf3e2437129d83f1fc11daa717f5ace8 |
| T56CliMetadataExecutionSnapshot.json | e6467a8f29843f0a566a8b7e0fd7b6ba3fd164c2cd2363c831a21e1783b731fd |
| T56CliMetadataExecutionOrdinaryManifest.json | 74d8e62fd7a0dae9f9889ed85b00c07ce556f78f644212500d943c13433ab0c3 |
| T56CliMetadataExecutionToolTerminal.json | 6183b85a2d0d3629630efe9fe6892bd621fb6c9a1f56a114e961591b9d7f28cb |

独立逐文件对照 43 原件/普通副本的 size 和 SHA，全部相等；有限 165 个唯一输入（包含原副本、五正式件、固定源码、必要旧失败与评审治理入口）前后无变化。没有扫描或重哈希整个 runtime。执行 Index `0e6d6be457c62eb53469865c4289109d2ebfc8ac84e1cfac40a856ba02f1d7e3`，Probe `ebdb19bcf346cf0c59ba814f7dd3715a9679f3dd074db3d1080347caa0726112`，原 CLI `native_owner_setup.py` 为 `28694e66c32ff7cfc77aadeddcb32f470c220c3c7ca4ade312fac2fd86c86c2a`。

49 项实际 loaded-module 名单、原路径和源码 SHA 与原 Index 逐项一致，也与首个 whole_cli_loaded 事件一致；固定49源码正文 SHA 另核相同。执行原捕获的 1623 个 path/size/SHA 在 InputBefore 与 InputAfter 逐值相同，并与 Index 逐项对应。这是原捕获数据和有限固定正文的复核，不是评审重新运行环境盘点，也不是 B42 当前源码运行证据。

## 十二项实际到达和原断言

原 `MethodRoundOne/Cases/JUnit.xml` 有十二原名、0 failure/error/skip；Summary、十二 test_started / test_finished 与 ArrivalMatrix 原事件逐项相符。stderr 原字节记 `Ran 12 tests in 0.106s / OK`；十二节点 duration 求和为 0.09950370000660769s，两种计时口径分列。实际 3 次返回、45 次拒绝均落在对应原 case 起止区间，源中 `parse` / `reject` 直接调用原 `self.cli._request`（Probe 388 / 396），未抽取替代校验器。

| 原 case | 实际返回/拒绝 | 支持的有限语义 |
|---|---:|---|
| F01 | 1 / 0 | 完整 canonical 原字段、DTO dump 与一帧消费 |
| F02 | 0 / 4 | 0–3 字节头拒绝，实际消费0–3 |
| F03 | 0 / 3 | 0、limit+1、uint max 413，停在四字节头，八字节剩余 body 未消费 |
| F04 | 0 / 3 | 声明 body 不完整 422 |
| F05 | 0 / 2 | exact limit 到 body-read；limit+1 于长度门拒绝。测试是有限空 body，不是最大尺寸有效目标 |
| F06 | 0 / 4 | 坏 UTF-8 / BOM 422 |
| F07 | 0 / 4 | 畸形 / 重复 / 连续 JSON 422 |
| F08 | 0 / 10 | 非有限常量及指数溢出，两种嵌套位置 422 |
| F09 | 0 / 4 | 非 canonical 字节拒绝 |
| F10 | 0 / 7 | 缺字段 / 未知字段 / 旧格式 / 错 root 拒绝 |
| F11 | 1 / 1 | 实际小端头、错误大端长度413与正常帧 |
| F12 | 1 / 3 | 中文嵌套原字段、一帧后剩余帧、旧嵌套格式和 bool 计数字段拒绝；不是 main EOF 测试 |

逐 case 错误码与原断言相同：`owner_setup_request_invalid/422` 22次、`owner_setup_request_limit/413` 5次、`installation_frame_invalid/422` 18次。拒绝事件原 emitter 未包含 method 字段；其直接调用来源由原完整 Test 源码定位，不能凭空补字段。

## 缓存尝试和 metadata 真实结果

`MissingCacheReadEvents.json` 与原 JSONL 逐记录相同，68 个不同路径均对应准备 map 的原 source/path/size/SHA，并来自 frozen importlib `get_data` 1218。它们是 guard 的 absent/read-attempt 记录；**不是 68 次独立 OS 返回，也不是640项准备 map 全执行**。`OS_read_result_not_replaced` 标志本身不提供调用返回观测。

10 个不同 `entry_points.txt` 记录逐项绑定原 distribution 的 METADATA / RECORD 和准备 map。六层 caller 顺序为 pathlib `open/read_text/read_text` →原 PathDistribution.read_text →原 Distribution.entry_points →Pydantic get_plugins，行号537/632/546/915/496/40。Read JSON/JSONL 相同；Outcomes JSON 与 JSONL 中每对 `actual_exception` → `original_return` 的完整路径和原异常字段相同。十对实际 FileNotFoundError（errno2）随后原 read_text 返回 None，原 metadata 自行处理可选文件不存在；未注入异常、替换返回或关闭插件加载。**没有独立 Win32 HANDLE / syscall 观察**，不把 Python 原异常升级为安装或 System DLL 路径资格。

## P2 仍 OPEN：失效的 profiler 与 before-body deny

固定普通 `ProbeCliFramesT56.py:322` 使用 `str(Path(frame.f_code.co_filename)) in INDEX['profile_module_paths']`；原 Index49路径是 forward-slash 字符串，Windows Path 表示反斜杠。源码静态逐49比较失配。本轮 `Methods.json == {}`，Summary.actual_methods也为空，符合这个缺口；尚无安全的独立 observer 阳性或 deny-before-body 阴性证据。

**归属 Test。**影响不仅是323–324计数：325–333的指定产品函数拒绝也在同一分支，空 ForbiddenCalls 不证明它有效。keyring独立名称分支334–340以及资源 audit 278–312仍存在，不能宣称所有防护关闭。原metadata使用 Path 对 Path 匹配（198–209/226），不受该字符串失配影响。

最小后继修订是在原正文和完整路径/SHA约束下统一两侧表示，再用安全的独立机制 fixture 证明观察阳性和 before-body 拒绝阴性；不得造 Methods、删除禁用名单或调用危险 Owner/数据库/native 来凑计数。没有要求重跑已绿的十二语法项。真正业务/权限禁用证明必须另固定准入和证据。

## 原失败及真实进程终态

首轮原 `CliFramePreparation` 在 Cases.bind → importlib.get_data 的缺失 `__pycache__/__init__.cpython-313.pyc` 被 Test audit拒，原 probe19172自然1、双byteEOF、forced=false，Summary/JUnit未生成，十二 NOT_STARTED。第二轮 `CliCacheReaderRevision` 实际走到原 Pydantic插件/stdlib metadata，可选 entry_points.txt 被旧 Test audit拒，原probe35088自然1、双byteEOF、forced=false，十二仍 NOT_STARTED。两轮 missing_original_summary 原生命周期错误保留；它们不是十二 grammar 产品失败，也没有洗成通过。

修订轮使用原归档Python `-I -S -B -X utf8`、exact Index SHA 和 whole Probe argv。由 PowerShell 保留的 **Python runner** PID37140 / creation134360673767041864自然0；其原 Popen probe37264 / creation134360673775478243自然0。LaunchReceipt / CommandReceipt / 同一 retained wait 身份一致，两进程实际 stdout/stderr byte EOF、无 lifecycle_errors，probe forced=false，输入变化空。PID37140不是 PowerShell自身；没有用后来PID消失代替原终态，没有重新运行此批。

## 评审自有解析错误和未测范围

自有工具0158ac自然0的初版检查错误假定拒绝事件有 method 字段、所有错误码相同，产生17条检查错误；原 Facts/Snapshot 原件保留。工具3e21bc定向只读原Probe后，78c158自然0另存 RevisionTwo，用原逐case调用数和三类错误码纠正自有解析，errors=[]；没有更改原Test、事件、期望或运行产品。此错误不归后端或原测试。

本片支持原完整 CLI `_request` 请求语法与透明原 metadata行为。CLI main、正常服务/DB构造、真实Owner、native authority/stdio、OS安装/实际System DLL绝对加载路径、B42状态/恢复、媒体与ASR、三OS、完整R1/R2均不由本片通过。十二项绿不自动替换任何旧runner或整体资格门，原SOURCE P2保持OPEN。

自身过程：`G:/开发测试/Codex/VideoCreatorImplementation/Review/CliGrammarIndependentReview-T56/`。完整FactsRevisionTwo和SnapshotRevisionTwo给出每case事件、每模块身份、每metadata对及两原失败收据；原输入after与正式Handoff另存。本轮只读冻结证据并写上述Review白名单，费用/模型/网络/产品执行0。
