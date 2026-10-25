# RV39：I32 catalog 预算与 post-create ownership 有限独立复审

结论：**SOURCE_STATIC_AND_EXISTING_COMPILE_REVIEW_FINAL。RV37-P01、RV37-P02 / P2 / Integration 在固定 I32 源码范围内关闭（CLOSED_SOURCE_STATIC_FIXED_I32）。** 本轮未发现这两个窄修复的新阻断；没有实际运行 reader、post-create 故障或真实 Windows 生命周期，不能据此授予 OS/native、RuntimeBinding、安装/发行、Gate 或完整 R1/R2 资格。T31 的实际消费者故障及后续真实 OS/Acceptance 仍需独立证据。

## 1 固定来源

本轮唯一输入根：`G:/开发测试/Codex/VideoCreatorImplementation/Integration/NativeSourceCorrections-I32/`。源正文来自 `SourceStaticRoundOne/SourceCopies/`，修改前正文来自 `BeforeSourceCopies/`；编译关联读取 CompiledOrdinarySourceIndex 的真实 input/compiled_source/ordinary_copy 字段，未猜路径或读取当前生产实现。未读 B24、T30 或其它 WIP。

| 正式对象 | SHA256 |
| --- | --- |
| I32Handoff.md（执行前阶段） | f4c309d007b01285e808688a072b216c29a6b73e559ee164ef0df9dc77d2f859 |
| I32Handoff.json（执行前阶段） | 0fe2c15bc8e3e32cde53a881b56a1d7e48414a4ff328a786c8d795a692bcd800 |
| I32SourceFreeze.json | 25438af4d348e2db83a06baab43a266166a27cf6522bb5ca5579e8bc176fb96f |
| I32CompilationHandoff.md | f1e322492ca3185fa75a2cc17e1eb304f87eaeb0986fad7c70c82700f5ed0ca3 |
| I32CompilationHandoff.json | 1367899203856dea2112d93b095e0ddbba1cebb74766c00c03f99be51a01e006 |
| I32CompiledFreeze.json | 3c775ca2c2db63fce087e95801f5f29424ddccf0cc10624cca63f9e4b4ca81c4 |
| CompiledOrdinarySourceIndex.json | 57f08fab3f029d61106c2bf5cd3862c818ca122f484a4ff4e1af8e3f7c141edd |
| CompilationFinalizationReceipt.json | 0dd2876b1b857dc50c98892ae26411b083c10f9dd7b2b429bc8d8f6ffeb2a9b8 |
| 原 compile CommandReceipt.json | 2612c8e23ac8f098b1dc379a423e457aba83c08373bb493b5f596632473cd6a0 |
| 原 RV37 报告 | 9eec917fa8973e4ca865ce4f2eee6ee479c3082bc719f799723d85eb109357a0 |

自身142个固定路径记录 SHA/size 全匹配，末核142项无变化。14份阶段源、三份 Before/三份 diff、40个 compiled member 的 input/Workspace/ordinary 三方字节逐项相同。只用标准库在内存核三份 diff：collector7 hunks、platform3、合同1，其结果分别与新普通正文逐行相同；没有执行/apply patch、产品 import、编译或 Test。没有重新hash全部6302工具/缓存输入，也不声称读取了40源全部正文。

## 2 RV37-P01：实际 catalog body 前置额度

精确文件：`SourceStaticRoundOne/SourceCopies/apps/desktop/src-tauri/src/windows_native_sources.rs`，SHA `459f3c9e9e3a8b9de88c160fa0aa246ea3f1b34d5b74cf04077d0dc887daf6a3`；原 Before SHA `4429283373e71f6320433307fb29ac96dcc8033858f49d5872b873ba617b0002`。关闭仅对应原“完整读后才核累计额度”的显式 reader 缺口。

32–50的 CatalogReadBudget 以128MiB为常量。43行从实际 held File 的metadata取得size，44行先reserve；36–40同时核单文件与剩余总额，才在46行以take(size).read_to_end进入body reader。拒绝预约不会读body；short/error、读后metadata变化47–48明确失败，已预约额度没有退回。metadata失败发生在body之前，亦不会以未知size进入读取。成功、签名拒绝及身份检查后失败都不会清账。

signature199–234只用唯一API首candidate，physical parent/exact CatRoot GUID/扩展名、held handle保持；225行唯一catalog正文读取调用同budget.read_catalog。observe322–324锁同context Mutex传入signature。collect280只在创建该context时建立一账；后续各目标、metadata carrier及external VC路径都经observe，共用它；308行保存错误后继续目标也不新建budget。Arc carrier 不复制或重置此账。

recheck366–373同样在catalog identity已核后用372行的同Mutex/read_catalog，不是直接read_to_end的旁路。Mutex poison会拒绝，错误读取/后SHA不符也不退款。其它`read_to_end`读取的是目标PE正文，并非catalog；本关闭不扩成整个OS I/O累计配额。

原静态80+80MiB反例在新源码中：第一文件预留并最多读80MiB；第二文件在reserve时发现只剩48MiB，返回budget_exceeded，未进入第二个80MiB body读取。下一目标继续只能使用原剩余额度。此为静态推演，**没有制造或读取任何真实catalog**。

边界保持：quota是同context的应用显式catalog reader累计预留，独立context没有被宣称共用全局账；WinTrust/CryptCAT provider内部I/O不由此全面计量。重复collect/recheck/carrier/bind读取保守耗用可能拒绝合法路径，兼容性仍未测，不能放宽128MiB求绿。firstcandidate/GUID、签名publisher、未知VC floor及错误留存条件没有因此取得真实资格。

## 3 RV37-P02：所有成功创建后错误统一持柄收口

精确文件：`SourceStaticRoundOne/SourceCopies/apps/desktop/src-tauri/src/platform.rs`，SHA `8e79b81246b3be07e2f3f22518819dc9062d5cff718ae66ecf4a6f625b04fab2`；原 Before SHA `7b55ac03346112e91aba4bc721ef4b9d8120a54f4b14ce23dee4c697ac419c40`。

87–90：成功CreateProcess后先将hProcess/hThread包为原Handle，立即建立借用同process/job的armed PostCreateGuard，再删除属性列表。创建失败88可无child返回；之后AssignJob92、GetProcessTimes94、可信before_resume hook97–99、Resume102的所有Err均经过guard.Drop；普通Rust unwind也经过同Drop。没有原来的5秒等待未核后直接释放分支。

Drop22–35只对这两个原持有HANDLE请求TerminateJob/TerminateProcess，并以WaitForSingleObject==WAIT_OBJECT_0作为process terminal，以同Job的QueryInformationJobObject成功且ActiveProcesses==0作为tree empty。只有两条件同时成立31才结束。Terminate返回true/false都不是终态证明；WAIT_TIMEOUT/WAIT_FAILED或Job查询失败持续保guard及句柄，不查PID替杀、不重开child。AssignJob失败时，即使Job为空，仍须等原process terminal；同样不能只拿Job empty跳过child等待。

外层 `engine.rs` SHA `91c8fa8bd2838e8b5ac7d06823d914b9f22c2a846636a5e17e46f7cbd05daf6e` 99–103保存PreparedLaunch并借用其source_carrier调用同步native launch；该调用尚未返回期间，错误Drop没有机会提前释放外层prepared/resources。固定 `load_policy.rs` SHA `4e260df7a6425dd30182d8007a58165b6b79558c95722e95386e78495304f629` 35–38实际持有Arc<ResourcePins>和LaunchSourceCarrier，123–143从同collect/carrier构造；carrier57持context Arc与文件句柄，不是只有typed字段或注释。

成功Resume后103才disarm/drop临时guard，105–106把原process/job/stdio转入OwnedProcess，调用方103接入PendingApi；成功路径未被改成提前terminal或kill。PendingApi/ApiRuntime既有Drop仍在真实process exit、同Job empty之后释放guard。源码安全转移与真实故障执行分层；本轮不验证恢复、真实exitcode/端口/后代、Job竞态或Windows caller可达性。

未知会持柄等待，可能阻塞；这是保留UNKNOWN的源码行为，不能把卡住伪作成功收尾。Rust abort/OOM、系统级故障/恶意OS root及完整通用sandbox不在本关闭范围；没有新增public arbitrary process API或Renderer callback。

## 4 编译来源与原真实证据

I32执行前Handoff保留其准确“尚未编译”阶段；随后CompilationHandoff单列获准的新一次编译，二者不能相互倒填。原444f46/session65279→759b72自然0，CommandReceipt实际两command与正式children逐字段相等：FactsBuild43664/creation00:34:07.3924579Z、DesktopBuild29184/creation00:34:19.0554941Z均natural0，owner_error=null，双stream EOF、timeout_sticky=false、force=false。不是只用marker或PID消失。

两命令使用准确Windows x86_64-pc-windows-msvc目标、offline/locked及固定Workspace/CargoHome/Target；完整raw SHA相符，Finished事实分别11.60s/2m11s。Facts stderr SHA `d1a8b501456581eacf8aa66e99863eb2143cfa160a393f4b1a9c436bed741165`；desktop stderr SHA `e09a0dbe8728d1034d9667642ec6cfcc5edba64cffbccaad35981e2c7e73b3b8`。facts4、desktop lib5/bin8（含duplicate）warnings保留，未cargo fix。6302输入无漂移是原owner receipt的范围；Review独立末核仅自身142固定路径。

新facts EXE828416 bytes/SHA `8bc2b6572f23b6b8714adf65fc3504fef912b11b7bb19b06f55a346be28fc20e`；desktop21306880/SHA `a882c1a8bff91907a472f3368201774befac402364048095acc925cf0ac52824`，仅hash读、未运行。facts lock5354bytes/SHA `4ed28469188fd84f03b734a5e4b13ebd1c05b66d92684e3f200c635b50667183` 与固定I31原lock相同，无新dependency resolve。40成员确为39 source/config加1facts lock，不把编译成员数称全系统依赖准入数量。

direct Cargo原Process+EOF不证明未观察build-service后代的atomic Job/sandbox；编译器隐式OS加载也不是collector/WinTrust事实执行。本轮不重新审全部runner或重复原I31全历史；旧两EXE/raw/red、原错误猜文件名保留，不覆盖。

## 5 后续独立Test与资格缺项

以下是必要最小实测设计建议，不授运行、不改变阈值或由Review代测试：

- 固定真实reader消费者：80+80时第二body调用0；exact cap及下一个非零读取被拒；短读/部分失败/读后size变化、签名或identity失败后预约不退，后续目标不能重置；collect→carrier→bind/recheck重复或并发Arc路径使用同Mutex账。分列应用reader字节与WinTrust内部访问，不能用返回error代实际读量证明。
- 固定PostCreate消费：分别注入AssignJob/GetProcessTimes/hook Err/普通unwind/Resume失败；原handle终止请求失败、WAIT_TIMEOUT/WAIT_FAILED、Job query failure或ActiveProcesses>0时实际observed guard/pins不得释放；直到同process terminal与同Job empty才放行原Err；成功转移保同process identity且不走failure cleanup。Test合成端口机制与另准真实Windows生命周期分开，不能fake terminal或按任意PID force。

T31的这些实际故障/Windows证据本轮未出现，不借未来绿。没有固定并执行新的facts runner或两个EXE，没有admitted InstallationManifest/完整payload/source/runtime闭包、真实origin/ABI/认证/ASR监督接线。八个binary-bound VC numeric floor仍unknown；本轮不读取A24或以当前host/编译器版本补floor，不删MFC/147+24能力。完整四profile、FFmpeg9/ASR86、MinOS/合法发行、干净Windows/macOS/Linux、完整作品与ASR精度/恢复均不继承编译绿。

源码层有限关闭不会把缺资源或未接线定成永久不可用，也不缩目标：完整R1三OS独立验收后连续R2，数据由安装实例持有、前台五步保持。真正产品运行和Acceptance仍须后续独立准入与验收。

## 6 自身证据与终态

过程根 `G:/开发测试/Codex/VideoCreatorImplementation/Review/NativeSourceCorrections-RV39/` 保存InputPins、FactsCheck、三diff内存关联、Snapshot、SourceAfter与Handoff。静态相关完整方法已按实际行补读；919cb0的宽source输出截断后以bd60ac有界补齐，不声称截断全文全审。末次d19e72实际0，142固定输入无变化、源码/evidence reader全部终态释放，live=[]，不持production freeze。

Review只写此报告及自身过程；产品/Test/DB/OSfacts/System32/store/DLL/EXE/compiler/ASR/provider/network/key/fee/install/apply=0。自身标准库脚本3e5989自然0仅解析既有字节/文本/JSON，不是产品或测试运行。评审不修源、不改标准、不代人类许可或Acceptance。
