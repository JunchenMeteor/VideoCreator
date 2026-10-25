# RV37：I30/I31 原生来源及启动接缝独立评审

结论：**RV37-P01、RV37-P02 / P2 / Integration / OPEN_STATIC。** 分别是 catalog 累计读取边界后置、三条 post-CreateProcess 失败分支未确认实际终态就返回。均来自固定真实源码链，Review 未运行反例；不能称 Windows/系统来源已实跑失败。编译实际成功保留，来源/认证/guard/完整运行资格仍未授予。

NextNativeFactsScope 是 proposal_only：36文件+5 metadata carrier+首catalog累计128MiB，runner未固定；本评审不代人类或统筹授执行。P01直接影响这个边界；P02影响宿主真实启动失败收尾，facts-only main不调用该启动方法。两切片分开整改与验证，不为静态报告等待未来事实运行。

## 固定身份与编译结果

普通路径来自 I30SourceFreeze 和 I31 CompiledOrdinarySourceIndex，未读当前实现、Backend/Test/Frontend/Architecture WIP。I30最终14源码/14diff与 I31对应编译源全部同SHA；I31完整39普通副本、两EXE、新lock及原raw实际核size/SHA。自身93 pins、92固定末核0变化；协调者任务卡只保首次pin。

| 固定对象 | SHA-256 |
|---|---|
| I30SourceFreeze | `6b69a810b595ee9ab7c1f724ea4888f8dff8e8d5f7a28b48ac7754aba5809f40` |
| ADR0025 | `dcf1f9de6f96c23aa6f21071dbaebc379d6000a32f0806a4e10c345f31d2b877` |
| I31 CompilationHandoff MD | `282727857e97e97f79ee3bbf61fc39cddb0eda652388b09f51486b5e38e86ca9` |
| I31 CompilationHandoff JSON | `51066a2153dd40fa8d2b0f1e8e9fe68f3a05826949f04c7774f0c5a4992ae67c` |
| I31 CompiledFreeze | `7cd50ae42d472109d71fcca47012b838d6e7e6e3abaf28078e00aea5b8bbff94` |
| I31 39ordinary index | `fdd1cf7eaf7db0d3f5e0dee9cdeb1520258d6c6b2501ac8f71e4e6fd77e77793` |
| collector windows_native_sources.rs | `4429283373e71f6320433307fb29ac96dcc8033858f49d5872b873ba617b0002` |
| platform.rs | `7b55ac03346112e91aba4bc721ef4b9d8120a54f4b14ce23dee4c697ac419c40` |
| IndexedLoader.py | `6caed5931f5f75a7ac7e690815ef8330fd74ffd361b149253cd97dc5ce9c7849` |
| IndexedBootstrap.py | `99b117702bbd19cec5c9c1596cad88f7f4563215502dce4100579683a21c456e` |
| load_policy.rs | `4e260df7a6425dd30182d8007a58165b6b79558c95722e95386e78495304f629` |
| engine.rs | `91c8fa8bd2838e8b5ac7d06823d914b9f22c2a846636a5e17e46f7cbd05daf6e` |
| new facts Cargo.lock | `4ed28469188fd84f03b734a5e4b13ebd1c05b66d92684e3f200c635b50667183` |
| facts EXE /815616 bytes | `a2210b2f5c3f398739acb0815a986c1b31a4ccbdf120ebd306a24e24027367c7` |
| desktop EXE /21294080 bytes | `41110466e1e1d680792e6d52abfa48148ba1dec5dd158cc4c3825e6aca80d8d6` |

实际原工具session95925本人4764e2 natural0，CommandReceipt `7a037000d58803ac3f7e2fe0bce0e48c4b0cf52f088bbdc5153000bc2528cbbf`：FactsResolve30492、FactsBuild20616、DesktopBuild29552逐项自然0，creation/argv/cwd/ended记录存在、stdout/stderr EOF、owner_error=null、timeout_sticky=false、force=false。原stderr Finished字段相符，facts4warnings、desktop lib5/bin8warnings保留，未cargo fix。新lock24个package条目包含本地root1和registry23；23的name/version/checksum与固定旧index/archive可用记录一致，不把「23依赖」误称24总条目错误。

6294是原Plan.inputs/owner末核口径，原receipt input_changes=[]；Review末核的是自身93/92输入，没有声称重新hash6294工具/cache。原全锁139缺archive涉及其他目标，不能说Windows编译必缺或三平台已补齐。compile使用隐式Windows API/DLL，不等于显式执行collector或catalog读取；两EXE均未执行，desktop没有admitted InstallationManifest编译绑定。

原compiler runner `ef1060f832ae13b2f15df27c61eb0f9bd94dfb2e0d49a0b0369aa36b5d3365e1` 的Start后metadata/receipt/stream不在即时finally；原稿保留未混作实际运行。修后 `7d3acb37f01fc1f86082a52400251ec83420afc7684da190c2d3674f297044ed` 将这些置入原Process持柄try/finally，直到同句柄自然terminal与双stream EOF；本次原正常批支持这些终态，不证明故障注入或未观察build-service后代。原误猜.md读取错误仍保持。

## RV37-P01：累计 catalog 额度在完整读取后检查

**P2，Integration，OPEN_STATIC；精确文件是上述collector固定SHA。**

[windows_native_sources.rs:204](G:/开发测试/Codex/VideoCreatorImplementation/Integration/NativeCompilePreparation-I31/CompileRoundOne/Workspace/apps/desktop/src-tauri/src/windows_native_sources.rs:204) 在 `signature` 打开首catalog并核单文件≤128MiB后，207–208已经read_to_end和SHA；随后调用WinVerifyTrust。调用方 observe303–308到signature返回之后，才把catalog_bytes加进总额并检查累计≤128MiB。collect274–289将目标错误写errors后继续下一目标；累计超额不会前置阻止下一个catalog的读取。

最小静态反例：metadata carriers使用embedded签名，两个所选目标各返回一个80MiB合法域首catalog。每个通过单文件cap；第二个完整读完已160MiB，才返回budget_exceeded。后续目标还可先读再报错。即使最后EXE exit1、observations含error，也不能撤回已超出提案累计读取边界的副作用。这里只是源码反例，没有访问、制造或运行真实系统catalog。

最小整改：将剩余总额/配额在catalog metadata与body读取之前传至唯一读取者，未知或失败读取不能不记账后继续消耗；不得以errors最终有值或累计「保留材料」≤128MiB充当实际读取有界。其它目标可在同一剩余额度内安全处理，不能换版本或提高额度求绿。保首候选、物理GUID域、单文件cap和签名失败语义。独立Test应在固定源码/可控端口层观察实际reader调用及耗用：80+80第二次不允许80MiB body读取，总额≤128MiB，错误保留且后续目标不得旁路预算；不要先跑真实System32反证。

## RV37-P02：三条 post-create 错误路径提前丢 ownership

**P2，Integration，OPEN_STATIC；platform固定SHA如表。**

[platform.rs:67](G:/开发测试/Codex/VideoCreatorImplementation/Integration/NativeCompilePreparation-I31/CompileRoundOne/Workspace/apps/desktop/src-tauri/src/platform.rs:67) 的CreateProcess成功后已拥有真实hProcess/hThread。70行AssignJob失败、72行GetProcessTimes失败、88行ResumeThread失败都只调用terminate与WaitForSingleObject(5000)，忽略终止返回/等待返回，再Err退出作用域。Handle.drop关闭process/job；[engine.rs:100](G:/开发测试/Codex/VideoCreatorImplementation/Integration/NativeCompilePreparation-I31/CompileRoundOne/Workspace/apps/desktop/src-tauri/src/engine.rs:100) 的`?`在PendingApi构造前传播，使prepared/carrier/source/resource guard随调用失败释放。

最小触发是其中任一post-create失败，同时terminate失败或5秒等待仍WAIT_TIMEOUT/WAIT_FAILED。此时没有实际terminal依据：未分配Job的suspended child可能仍存，已分配Job的kill-on-close也不能把请求终止当真实exit。没有实际OS故障注入，不称已发生孤儿或实际安全突破。

对照75–84的before_resume回调失败路径已经保原句柄循环到WAIT_OBJECT_0；这一保护没有覆盖另三支。最小整改是所有成功CreateProcess后的失败都进入同一原handle持有收口；terminal未确认期间保持原process/job及prepared guard，不换PID、不盲restart。创建失败可返回无child，但创建后不得用5秒等待值未核的Err抹掉unknown。独立Test需针对三支终止失败、timeout、查询失败/随后terminal各注入并观察guard释放顺序；再另准真实OS批，不能仅检查源码含TerminateJob或kill-on-close。

## 其余相干链的源码支持与限制

collector真实源码采用GetWindowsDirectory/GetSystemDirectory/RtlGetVersion，否认env根权威；source文件/祖先reparse、PE amd64/static/delay、只读share=READ持柄、file identity及SHA、embedded或exact hash首catalog WinTrust路径均存在。签名记录保Microsoft organization/cert hash及cache-only online_revocation未查，不宣MinOS/发行权。APIset只处理v6/.apiset/default唯一target；importer-specific/多目标保持未证。VC独立观察version.dll与version floor，当前合同没已核floor会明确失败。观察JSON并不构造可信guard；Rust仅collect生成不可反序列化context。

carrier在CreateProcess前create_new、sync/hold、SHA固定；实际child PID/creation在suspended→Job assigned后形成八字段ASCII LF≤1024B帧，hook在Resume前只写原stdin。Bootstrap精确raw read(1)到一帧，不预取后续MCP/ASR/shutdown；builtin _sha2验carrier/policy、实际PID/PPID，后续受信_ctypes复核creation与实际file/module identity。正确路径具有源码支持，真实短写/EOF/birth/auth/不可变namespace和系统update场景未实跑；P02失败路径仍阻断整体收尾。

builder只对明确exact合同建立关系，不放行api-ms前缀。96声明=71OS/17APIset/8externalVC，全部是声明，未知MinOS/许可不变通。唯一NumPy/re2 alias保两RECORD/owner/version/575056bytes/已冻结完整SHA与static/delay闭包，canonical明确NumPy，ASR独立单成员；其它碰撞仍unresolved。Loader核importer绑定/闭包digest、预载foreign origin、真实handle/GetModuleFileName/file identity及canonical postload；不以DLL请求参数充实际origin，也不称initializer执行前sandbox。真正动态/延迟来源、反向import顺序与全部SCC仍待Test。

CT2固定4.8.2/source SHA由IndexedSourceLoader编译并登记实际code对象及co_consts对象，hold后id不可回收；caller用对象is判断，不用co_filename字符串冒名。absence_only两个CPU sibling检查合法祖先，缺失直接FileNotFoundError且不调用Win32，出现的未知目录抛LoadingError(ImportError)，不会被原OSError/FileNotFoundError捕获洗过。本包目录不属于缺目录例外。正常directory cookie和DLL handles由resolver列表保留，第三方RetainedCookie.close不提前释放；本轮没有真实cookie/child终态关闭证据，不把注释或list当实测。宿主成功路径ApiRuntime/PendingApi retain guard直至root实际exit且Job empty，错误/query不作成功；P02例外独立列明。

## 后续事实批必须先具备的执行边界

准确提案是facts EXE a221…、程序/collector/contracts/newlock/原compile receipt固定，argv只contracts/path+全文SHA，目标36与metadata5、实际OS根差异停止；target DLL不LoadLibrary。catalog仅API返回首个exact hash候选/GUID物理域，动态具体路径未知，必须独立准入这一有界命名空间或先准metadata发现，不凭静态列表默许。P01需先改正并产生新source/EXE身份。

runner尚未固定；必须独立核唯一输出目录初始不存在、实际工具/隐式OS provider依赖及可能store/cache/log副作用、闭集env、exact Process从Start起try/finally持柄、真实creation/argv/raw、120秒sticky失败不kill/retry、原句柄自然终态和源前后检查。WinTrust cache-only不是在线撤销通过；VC floor未知、复杂APIset及MinOS/REDIST/干净目标机仍具体失败/未测。EXE读点/编译不是facts runner权限。

完整147+24、四profile、FFmpeg9/ASR86、Backend/Media新版本接线、实际guard/auth/安装/作品/ASR精度、Windows/macOS/Linux及完整R1后连续R2均不继承编译绿。当前builder/consumer仍固定B18/W14、五migration版本，不能混作后续六migration/新业务支持。旧I29资源/红、原runner和未测保留，五步前台/数据安装实例持有目标不缩减。

## 终态

只写此报告及 `G:/开发测试/Codex/VideoCreatorImplementation/Review/NativeSourceIntegration-RV37`。自身 [FactsCheck](G:/开发测试/Codex/VideoCreatorImplementation/Review/NativeSourceIntegration-RV37/RV37FactsCheck.json)、[InputPins](G:/开发测试/Codex/VideoCreatorImplementation/Review/NativeSourceIntegration-RV37/RV37InputPins.json)、[SourceAfter](G:/开发测试/Codex/VideoCreatorImplementation/Review/NativeSourceIntegration-RV37/RV37SourceAfter.json) 保存精确来源与静态/编译分层。广枚举依赖文件名/宽读截断保为Review过程错误；使用nonrecursive正式index及有界关键链补读，不声称所有cache正文已读。所有source readers/tool终态释放、live=[]，无System32/store/DLL加载/EXE/compiler/测试/产品/ASR/network/key/费用执行；SOURCE_AND_EXISTING_COMPILE_REVIEW_FINAL，不代修或验收。
