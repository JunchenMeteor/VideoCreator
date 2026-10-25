# RV22 — T19 业务 Harness 准备材料独立评审

状态：FINAL / SOURCE_PREPARATION_REVIEW_ONLY。认可本文所列固定材料及有限准备证据；不批准实际 Binding、产品启动、真实业务批或任何 Gate/R1/R2 通过。两个 P2 候选问题 OPEN，一个 P3 分类问题 OPEN。原标准、原失败、此前评审限制保持。

## 固定身份与实际读取

正式 T19 Handoff MD：e9191b2e8e7d708a6d17fe9a4cc999ba9e5bfa174014ddd5aca79dd9ebc231ef。
JSON：7db0b5d240e8aaf65cf2d0a5f1a7fcccdb3c35f19b375ae513f53dac272c6866。
T19Snapshot：7e73799edbbb7935f6df5ecd2ebea39b15633f50a925f6b54719fe8d8663d47b。
当前 T19CopiesManifest：92cecd7eb6fbf0c2b3cca8a76ca235be3569574e113f05158771d47b8dfeccd2。
历史 T18 PreparationCopiesManifest 为 4b49f37f1de541e0c25f27c122cd7aa4ba4b7316a6fc5fac37b3464bccf6bd6d；这两个清单不混称同一身份。

独立核 10 个最终 Test 源的 20 个副本、47 个实际准备/语法证据副本，共 67 个，0 hash mismatch；另核 6 个终态 finalizer 副本，0 mismatch。历史 T18 13 个 Test helper 同 hash 正文全部保存，0 mismatch；不把它们当新接口运行证明。旧 consumer ABI 是历史 B11/W11 源级 6 consumer/16 构造与 v0.3 port，不证明当前 B14。

关键最终源：

| 文件 | SHA-256 |
|---|---|
| tools/testing/StartT19Business.ps1 | 0a7ca14e00e691035e140e6341d176280c3b8b219cb62f30f0a736f22e7a666b |
| tools/testing/T19LaunchRules.psm1 | 2e80f89d5bd6b2bb15b63cdbd219431f8277621b19ea43eefbdc1affc9f1c457 |
| tools/testing/T19BusinessHarness.py | 90ca38fd9409ea41f19229594934224030f92ae2c682fedd948c96cc892b554c |
| tests/bundle/t19_business_cases.py | 5986b9541d4de18835f6d1014393349fa3254d24d0679ee9d55dd2b3c74583b0 |
| tests/bundle/t19_bundle_cases.py | e0b7bc98e04d84f6dcb240610d3d262ec68429ca51b0e71af124fddbbd961a76 |
| tests/bundle/t19_transport_cases.py | cdf35e274d6ff2b759001897fa7d0d69eda517f3d42d63903fbf9f5ee13ba280 |

全文来自固定普通副本与评审自有 Snapshot；未读取/import 当前 Backend B14、T20 或任何生产 WIP。源码后核结果见 FactsCheck 与 Handoff，不持生产读取冻结。

## 可支持的有限范围

T19CoverageManifest 的 68 项与 RV19 固定 criterion revision2 的 38＋20＋10 数组逐值、顺序完全一致；criterion 文件字节 SHA 仍为 2f5203983e5c696ad6cb2ee89d81ed2bf7b5d51a31abbdfe5a6f6d9a576b85d2。200000 整数微秒、max(start,end)、完整独立 N/nearest-rank P95、30 选题×60 作品 MM05、来源/权限/原件要求均未降低。68 项全部 not_run。

ec64a1/exit0 的旧准备批有 13 own-fixture 检查、failures0、source_tool_changes=[]；实际只创建 PowerShell PID19708，11:41:30.7692123Z，自然 exit78，拒绝原因 ROOT_AUTHORIZATION_NOT_PUBLISHED，没有产品 Python。Receipt SHA500d72600c88bb56dd613d5e8cce336efaaf1c43603184bc147afa5f04cbeb2e，ChildReceipt SHA8aa7111898d9ce1292a798e4de4e6e0bfedb0e6a8e9c59b9f5a16a1cf06bc962。

旧 starter 为 eae4caf9279184d4aaea3e03cc24272701155c2d4084fbe1490acc01bdfff1f1，旧 harness 为 f33b337156d2f0fe716290a3f6676915637f683a2d813689ec3bc32fa6c36855，与最终版不同。最终 strict header、DataDir、NotReady 分类及清理分支没有继承这 13 项绿。4cd2fd、d51376、d8e6db 各层语法结果仅 AST/compile/Parser.ParseFile，未执行编译后的业务；中间外层 shell/Python-c 文本未分别归档的缺口保留。7e6f4a finalizer 实际 exit0 与六个普通终态副本一致，仅归档/序列化，不是业务运行。

静态可支持：starter 15–51 在 helper Import-Module 前用内建严格 JSON 核 root/review/header 与 starter/helper hash；规则 59–151 对非空闭包、完全集合、文件及祖先 reparse、source body、目录未列项、目标/父包链逐项检查。Python 115–139 的后续调用为 admit_runtime→真实 B11ServiceAdapter→实际 Engine/Bundle/媒体 factory；19 service 函数确实写有真实服务调用，HTTP 函数使用真实 loopback socket/uvicorn，Bundle 函数读取实际服务可见字节。以上只确认候选代码语义，所有 ABI/service/HTTP/ASR/Bundle 调用运行数仍为 0。

## RV22-P01 — P2：DataDir/output 的祖先 reparse 检查不完整

归属 Test。固定 [StartT19Business.ps1](<G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T19Preparation/FinalSourceCopies/tools/testing/StartT19Business.ps1:68>) 68–72 仅检查 DataDir 最近已存在祖先自身；82–88 对新 output/cache 只核词法前缀与未存在。规则 Get-T19CanonicalPath（36–41）只是 GetFullPath，不消解 junction。

源码触发推演：T19Owned/Link 是指向范围外的 junction，Link/Existing 自身是普通目录。DataDir=Link/Existing/NewData 时，最近存在祖先 Existing 不含 ReparsePoint，更高祖先 Link 未检查。output=Link/Existing/NewBatch 未存在也可满足词法前缀；86–92 在 Python 检查前创建目录并写 PrePythonReceipt。Python load_trusted_launch 83–87 的 resolve/范围检查随后能拒绝范围外路径，但不能撤销这些先行写入，也不能证明“启动 Python 前已核完整自身实例边界”。

修法建议：为 DataDir、output、cache 及 body/output 目标明确扫描完整已存在父链；拒绝任何祖先 reparse，并在写/启动前核解析后的实际路径属于批准实例。Root/Review 可信宿主还须在执行 PowerShell 前认证宿主/启动器及完整外部闭包；此修法不声称消除所有文件系统 TOCTOU，不把治理目录当 OS ACL。

本项是静态分支问题，未运行 junction 反例，未观察任何范围外写入，未证实真实 OS 产品漏洞。待 Test 在新固定版本补独立原断言/反向边界后另审；本轮不修改代码。

## RV22-P02 — P2：Correction 原件 oracle 没有接入业务批

归属 Test。固定 [t19_bundle_cases.py](<G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T19Preparation/FinalSourceCopies/tests/bundle/t19_bundle_cases.py:63>) 63–89 定义 audit_actual_correction，但 produce_from_actual_fixture 118 与 consume_actual_bundle 127 只调用 audit_v03_published。T19BusinessHarness 199–204 导入/派发也没有 audit_actual_correction，整个最终调用链没有此函数调用。

触发：即使未来提供真实合格 Correction fixture 并成包，原件文件 hash、精确字节、corrected_from 元数据与 artifact dependency 的独立断言仍不执行；不能以“函数已存在”称 RV20-P03/RV21 原件闭包获得测试覆盖。当前 5 个 Bundle 函数中，审计辅助函数不是 5 个已注册执行 case。

修法建议：把 correction scenario 接入明确业务 case，使用外部绑定的实际原件材料及实际 published manifest，并记录已执行 oracle/输出证据。多次修订须按各 ancestor 的预期原件映射核索引及正向边，不能让 78 行对每一份 corrected report 都比较同一个 expected_origin_file；不得制造 SQL published 行、改原报告或以 self-asserted rights 绕过真许可。

本项是静态可达性缺口，未运行 Correction case，不称业务红；生产 rights/再分发许可与原件祖先闭包仍由真实 Backend/Media 事实及后续独立业务验证证明。

## RV22-I01 — P3：setup 期 NotReady 异常未统一分类

归属 Test。T19BusinessHarness 23 定义本地 NotReady；load_trusted_launch/fixture 缺项使用它，main 212–214 仅捕获该类并返回78。actual_context 123–131 调旧 t16_guard/B11ServiceAdapter；旧 t16_guard 15 的 NotReadyForExecution 是另一独立 RuntimeError 子类。run_cases 158 的 isinstance 分类仅在 callback 内生效。

精确静态触发：通过外层字段/文件检查但 admission 缺 t18_trusted_resource_profile，main 191→actual_context→B11ServiceAdapter 7–9→旧 ServiceAdapter 47→t18_bootstrap 18–24 抛 NotReadyForExecution，发生在 run_cases 前，不能被 main 的 except NotReady 捕获。因此是未处理 traceback/非零退出，缺准备期结构化 not_ready/actual_cases=0 收据；不能倒称某个业务断言失败。对应 profile bootstrap 尚未具备，当前没有实际跑到该分支。

修法建议：在 setup 边界统一捕获本地和旧 guard 的准入异常并保留阶段/原因、0 actual cases 与非成功退出；真正业务异常继续保留 failure，不能宽泛吞掉异常或写成 pass。严重度独立为 P3，不称运行成功/安全绕过。

## 仍不具备的运行准入与交接

缺 Root 精确 RuntimeAuthorization、独立 runtime Binding 批准、执行 PowerShell 前的可信宿主认证，以及最终全 Python/site/native/PS/source-resource/body 闭包。角色目录没有 OS ACL 的同等隔离；有限 CIM snapshot/PIDCreation/Parent 核对并非 Job Object，查→Stop-Process 的 TOCTOU 与未观察子孙仍未证明，强制或未核清理不能记 normal。

历史 t18_bootstrap 47–57 固定 precision_authorities={}、rights_authority=None；合格作品与权利核验的真实正向初始化仍缺，单 fixture flag 不能使它成立。实际听审/独立标注 benchmark、作品 reference 原件、资源/素材授权、完整 fixture/bootstrap、独立 OS 非 once Worker 存活及第二 Run、真实 MCP host、完整 68 case 映射、跨实例/崩溃消费、三 OS、真 TTY/signal、MM05 均未通过本批。模板状态 fixture 不算模型自主创作。

结论限于已冻结 T19 候选准备材料。Test 按原角色处理问题并提交新 hash 后，另经独立 Review 准入及 Root 精确授权；本报告不发布 Binding，不启动任何产品。完整 Gate0→R1 独立验收与三 OS→连续 R2 的总目标不变。费用、key 读取、网络、安装、产品/test/import/解码进程均为 0。所有评审读取已终态，无缓存生产 reader、无 live handle；本阶段 FINAL，释放读取与角色槽位。

