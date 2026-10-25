# RV75 — T50/T51 启动入口固定证据独立评审

结论：**LIMITED_COMPONENT_EVIDENCE_SUPPORTED**。T51 的原16项断言全部实际通过；T50 原12通过、4失败及自然退出1保持不变。本次未发现该有限输入内的新生产 P1/P2。支持的是固定 CLI 启动、API/MCP 传输、回调绑定和透明关闭接缝，不是完整 Worker、Owner、Native 安装或成片资格。

## 输入与独立核验

只读 `TestDevelopment/ReviewHandoff/T50StartupAssemblyOriginal` 和 `TestDevelopment/ReviewHandoff/T51StartupAssembly` 固定普通副本及治理入口；过程为 `G:/开发测试/Codex/VideoCreatorImplementation/Review/StartupAssemblyEvidence-RV75`。82+92份普通副本的字节数、完整SHA与原声明一致，另6份正式索引/交接及3份治理入口，共183条输入，逐项见 `RV75Snapshot.json`；本轮前后核验另存 `RV75InputAfter.json`。没有复制、扫描或重新验证2446/2454份依赖环境。

| 固定输入 | SHA-256 |
| --- | --- |
| T50Handoff.md | f129e7b8e0cf00ef2d3ddf8802f51bb936339ed3441b43bfb290ff38abc0b3fa |
| T51Handoff.md | 2b1b4585a37e7dc16552abb32c91e71b2d2ec471599bb00a56e1e736cf3075d0 |
| T51Handoff.json | 4d865e51cfdc375fa017cffe0260c6850bb9ef764d14fb9fd213880222acc8b3 |
| T51OrdinaryManifest.json | 30c23355719d82959ed5ca5615b33d8a2104ff1f5ba1de3620ca42651916c0c0 |
| 原新 ProbeT50.py | 132947d5ef163853d4b742c0b91fbcf1c70bf1cc039b6619bf0b7c880de6d71d |
| 原新 StartupFixtureT50.py | d7599f202cf4c8e7f138bd76631921de69e9093e9c772c1f64713d2767b43faf |

Probe及Fixture全文逐字节相等，16个原方法名/断言/观察时限保持。五份消费生产源也逐字节相等，来自历史 B36 固定源：`cli/main.py` 1b16663cc522493c7952d1a81046dc7d4fba2156a906ec5674b98f89fa4a76ca；`cli/startup_services.py` 2efa24aeea016b3ee566e603495886fc4d31accab412dbb48917cf99097890eb；`integrations/mcp_stdio.py` 7d6bbf124f5d130a9f4daec328760a0cce5564d4184b2ee12e7572812932d635；其余两份完整身份见 Snapshot/FactsCheck。没有用当前 B38/I53 或后继 B37 修复倒填本批身份。

旧2446条索引记录在新2454条索引中逐值保留；新增8项均是 T51 自身命名空间、启动器、准备/计划/差异文件。Review核对的是保存的索引和运行后收据；2454个物理环境文件的原运行后核验属于 Test 原收据，不冒称 Review 全环境复测。

## 原红、窄修与真实终态

T50 原 JUnit 16个节点/12通过4失败/0错误0跳过，主 Python32200（creation `2026-10-09T17:45:27.4469141Z`）及包装均自然1，双byteEOF、无force/观察超时。C07/C08/C15/C16原 stderr 均实际出现 pywintypes 缺失；只有 `test_main_enter`，未到 callback、MCP ready 或目标回应。归属是 Test 的 `-S` 显式 bootstrap，不能推为 Backend 回调/协议失败。原 e3c00f→ff9b7f及所有原raw/XML保留。

T51 的 `ActualMainT50.py`（03d8aaad0a0fb9f40173a9db25706ea830009e775860f3580eb6fb685b10b422）仅增加真实 pywin32 三条显式路径、核验并导入固定 `pywin32_bootstrap`、为同进程持有显式 DLL directory handle，以及新索引名称。其 `run()`、限制函数与原 main 调用未改。RunT51.ps1仅索引名/终态标签变更；没有执行通用 .pth、造假 pywintypes 模块或修改依赖。完整实际差异见 `ActualDiff.txt`。

T51 原82ac35/session95552→077bc4自然0；Python17460 creation `2026-10-09T17:56:48.3904853Z`，Python/包装均0、双byteEOF、force=false、observation_exceeded=false、errors=[]、input_changes=[]。原stderr实际报告16项/41.703s/OK，JUnit仍用原 `T50StartupAssembly` suite标签，16节点与 CasesReceipt 的逐方法结果一致。包装墙钟约43.23s与suite耗时分层，不互相替代。

十二实际 main 子进程逐个 LaunchReceipt/CommandReceipt 的PID与creation匹配，raw双通道已解析JSON与相应receipt事件逐值一致；均实际terminal/双EOF，无force或观察延迟。预期拒绝子进程退出1不是整个批次失败。API C02/C03分别实际使用60292/60334，原ready与健康回应关联同实例；各退出后原 `PortAfter.json` 记录真实 `socket.connect_ex` 拒绝。停止marker与实际退出、泵EOF、端口观察分别核对，未用marker代替进程退出。

## 逐组支持范围

| 原case | 本批真实到达及源码链 | 限制 |
| --- | --- | --- |
| C01、C04–C06 | 原完整 main：不允许命令/回调异常/错误实例或类型拒绝，无ready。C05原对象仍在强持有表，未close。main150–156、startup59–90；Probe227–264。 | 透明回调，不是实际Native资源受理故障。 |
| C02–C03 | 实际loopback HTTP health200/同instance。C03回调先于ready、使用同Engine/Bundle；api_stopped先于透明authority/build关闭，retained最终0。main296–337；Probe167–194、238–250。 | 未调用生产创建或验证安装资格。 |
| C07、C08、C15、C16 | 实际 MCP main、initialize回应、tools/list回应与stdout原帧一致；返回12个工具声明，包含production_get。C08实际回调错误先于ready。C15实际tools/call错误meta返回isError及mcp_session_invalid；C16无回调本地基线。main277–289；Probe196–225、266–278、374–379。 | 12是工具声明数，不是12个工具调用；合法授权生产正向NOTRUN。 |
| C09–C10 | 真完整Worker入口分别拒production_configuration_missing、production_engine_incomplete；无fixture callback/worker_ready。main186–200与media_registration98–102；Probe280–297。 | 没有成功进入完整RegisteredMediaRuntime/Worker制作。 |
| C11–C12 | 在Probe进程中调用真实startup helper，核同Engine/Bundle/runtime及错误role/runtime拒绝；Probe299–328。 | SimpleNamespace runtime和透明native ports，不是完整Worker进程。 |
| C13–C14 | 真实helper消费原NativeOwnerServices.close；透明close异常保原strong holder，实际创建的thread存活时先拒清理，thread结束后再关闭/解除持有；Probe330–372、startup38–52。 | authority/build close是Fixture函数；不是Win32未知受理或句柄复用故障。 |

MCP C07/C15/C16实际收到一次 mcp_stopped、worker_cancelled=false，继而原main自然退出。固定 `mcp_stdio.py` 的 per-call actor 保真实meta校验；本批错meta没有桥自动补token。EOF只对无生产任务的原transport闭合，不能证明活动任务取消、unknown费用对账或重启恢复。原 Fixture12–45清楚替换bootstrap/admission元数据及native close口；真实NativeInstallationAuthority50–61/86–94的资格门未被本批验证。

## 尚未达到与交接

本片无新增生产阻断finding。Test bootstrap 原失败原因及新namespace修正有有限运行证据；原T50 NOTPASS永久保留。完整注册Worker正向、MCP authenticated_production_positive、活动任务EOF/取消、真实Owner/资格/安装、危险B36/B37受理/CloseHandle故障、ASR/完整媒体、跨进程恢复、三OS和完整Gate/R1均未验证；R1独立完成后连续R2目标不缩。

Review没有启动、导入或执行产品/Test/native/ASR/DB/模型，没有读取真实凭证、收费、安装或网络调用。原输出截断被有限定向源码补读，原工具记录不洗。所有固定输入读取结束；正式过程 `RV75Handoff.json`、末次输入核验与 FinalizerTerminal 记录实际工具终态和reader release，不以本报告替代独立验收。
