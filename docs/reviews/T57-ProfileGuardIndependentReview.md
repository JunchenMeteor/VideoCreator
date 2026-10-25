# T57 profile guard 四项机制独立评审

**结论：LIMITED_PROFILE_GUARD_MECHANISM_SUPPORT。T56-CLI-P01/P2 在当前 T57 固定 hook 的源码匹配、chosen before-body拒绝和 foreign-module四机制范围内关闭（CLOSED_LIMITED_MECHANISM）。**旧 T56 失效 hook / 空Methods和两原失败保留，原十二语法项没有重新运行、没有回填。关闭不等于修订 hook 的完整CLI/main/Owner/native或产品资格通过。

本轮仅读固定源码、原raw/JSON/XML及普通副本，用标准库解析既有artifact，写Review白名单。没有导入或执行Test/helper/vendor/product，没有启动CLI/服务/DB/native、收费/联网/安装，未读取后继F11/B43热材料。

## 精确版本和独立身份

正式根：`G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ProfileGuardRevision-T57/`。普通根：`G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T57ProfileGuardExecution/`。

| 固定件 | SHA-256 |
|---|---|
| T57ExecutionHandoff.md | a249c2ca2858267e84c0dc0aee4936601a3648d84971135673cb3fd2c0e88814 |
| T57ExecutionHandoff.json | aa8d17d057c55516b7b75cc4cee844f1c7cca1fd6a307a302aeb711394caf3a5 |
| T57ExecutionSnapshot.json | abf74a10f13ba57fca778be773e7105b6464e501ad5356baea7b8e98c0f35ffc |
| T57ExecutionOrdinaryManifest.json | 75113308a787c110164c2eab075ea704ee31ba25aece76b0c4b8c87c0cdd87d5 |
| T57ExecutionToolTerminal.json | 2e573809d3e4996f1b891d0051dddc7ed6835192476598457efd1aa30c3d6cfa |
| ProbeProfileGuardT57.py | f5e2167a2b624dc6ffab49b0e0150e5877f74a0744f425fc7e491d273e00cbbc |
| T57ProfileInputIndex.json | e407de0240a71403611eed0affd47a8a4674ae1187c8b916a4c37ae598c6b793 |
| T57ProfileLaunchRequest.json | 06915ee863c0fa2d8b32d04307fe2339890aa204f697cca6b0fe5957b53eaa3f |

47原件/普通副本的实际size/SHA逐项一致，不只信manifest.equal。112必要唯一输入前后无变，未遍hash runtime。原捕获的1632 InputBefore/InputAfter逐path/size/SHA相同并与新Index对应；新Index保留旧1623绑定，加9条有限Test输入。旧product_modules/function_names/profile路径/metadata observer/maps相同；原640 exact cache map保留，只加foreign完整源码的一个缺失cache路径，当前641准备项不是641执行项。

原 T56 两评审报告字节保持：Execution `b476b2291bf190418fad12ab22e7c22e1c7e443ad1ef7a2f335f0502bb35ee10`，Source `be76e4465597eea483c57d808eb12f4d46c6d4cbde6cb8caf899dfcbc9bc69f5`。

## 实际源码与防护范围

固定普通Probe316–319将actual/index两侧都转换为 `Path(...).as_posix()`；329–337先约束产品module存在和完整指定filename，再确认profile映射存在；342–344要求function map存在。随后计数和matched event不授予权限；原domain/`_request`/held严格JSON allowlist未扩大，350–353指定函数仍在body前拒绝。独立keyring分支354–360与原AST相同。

独立AST核原16个顶层helpers/完整Cases class不变，包括audit/cache/metadata/标准ctypes/whole-module/原Result；原十二方法及所有原断言完整保持。三份runner/Probe完整diff与实际固定旧/新源码生成diff逐字相同。准备材料打印工具c2ed5a有小段截断，未将截断输出冒全文；原完整diff和完整AST已由7d19f4有限解析核实。

ProfileGuardCases.bind552–562通过正常import加载完整errors和credentials，在原audit/profile下核原module.__file__和完整body SHA。五个实际产品module逐项与Index、原完整源码、ConsumedWholeSources原/普通字节一致。EngineError原393B/SHA`4bb8b859a340af0cd6f6093a5f97863c00e7f02d0a5f9ff95f523da389c6e6a5`；credentials原2812B/SHA`a7895c401874344a784b7b2d75dc4a1bbd05d585b0fe8359e84aefc2a0f5bdd0`。没有抽取影子函数。

## 四项原执行及为何足以限定关闭

原JUnit为4 tests、0 failure/error/skip，四个完整原名与原Summary/Arrival/Events对应，stderr原字节`Ran 4 tests in 0.012s / OK`。四节点duration求和0.01042300000335672s，与stderr整批计时分列。

| 原case | 原实际链和完整断言 | 限定支持 |
|---|---|---|
| G01 | 原EngineError构造一次matched；字段/code/message/status原断言通过，正文line6/7/8/9/10实际trace | 原profile能命中且允许选定原构造，line observer非仅空输出 |
| G02 | 实际co_filename与旧forward-slash字符串不同、新source_key相同；再构造一次matched，原字段及同五行trace | 修复原Windows表示失配，第二次真实调用进入正文 |
| G03 | 604–631直接调用完整原`SecretHandle.__repr__(None)`；matched后denied，原RuntimeError断言、增量1、exact forbidden key和body_lines=[]通过 | chosen原受限函数body前拒绝；未构造SecretHandle或访问secret |
| G04 | 633–664正常SourceFileLoader执行同393B原errors于新固定物理路径；module入口foreign拒，body_lines=[]、无EngineError定义、原sys.modules对象相同 | 同字节不能替代source-location绑定；透明foreign Test反例body前拒绝 |

Methods10键总11次，逐项等于原matched events：8次module/class-body定义，2次EngineError.__init__，1次被拒__repr__。**SecretHandle/CredentialVault class-body名字是类定义，不是实例构造。**不能把methods次数当runtime权限，未出现这两个__init__/vault/服务调用的资格阳性。

两精确ForbiddenCalls为 `video_creator.infrastructure.credentials.__repr__` 与 `video_creator.domain.errors.<module>:foreign_source`；case起止区间内分别有matched→denied→零body与foreign拒→零body事件。G03原22–23行纯常量repr不读取self或secret，None不是伪Owner/secret。G04原源码同SHA但physical path不同，未安装进sys.modules，不是替换产品行为。预期受限profile拒绝后，原同一callback在finally626/657重新安装；这里支持已执行的两个安全隔离反例，不声明通用OS安全沙箱。

此前缺口是路径比较令匹配/同分支before-body都失效；现在真实匹配阳性、正body控制和两个负向真实零body齐全，因此可在这个固定hook与chosen条件下关闭。**未执行其余49映射函数、runtime unlisted module-name分支、路径alias/case/reparse/TOCTOU变体或修订hook完整CLI十二项；这些不从四项结论继承绿。**

## 原进程与辅助观测

原tool记录cell1→274064/session47439→owner5536f8自然0；原最终metadata工具6114e7/0和最后86117c/0已在固定Terminal登记。评审不把自己读取工具当原执行。

由PowerShell持有的Pythonrunner PID32604 / creation134360693325603458自然0；原Popen probe33692 / creation134360693334070172自然0。LaunchReceipt、CommandReceipt和同一retained wait身份一致；两进程stdout/stderr双byteEOF，forced=false、lifecycle_errors=[]、input_changes={}。实际argv归档Python `-I -S -B -X utf8`、whole Probe及expected Index SHA一致。PID32604不是PowerShell自身；外层tool raw只有原chunks观察，未倒造完整byte流。

24个不同cache guard read-attempt记录与原JSONL/641准备map/source/caller逐项匹配，caller为frozen importlib.get_data1218。**没有独立OS返回证明**。本轮optional metadata read/return为0，不继承T56十对为本轮执行。原cold ctypes记录仅requested kernel32/非零handle及原module pins，actual loaded filepath未观察；hostname记录也是原有限初始化事实，不授安装/OS资格。

## 保留范围与交接

无新阻断finding。T56-CLI-P01关闭标记为CLOSED_LIMITED_MECHANISM/current T57 hook；旧source报告的OPEN是旧版本事实，不改其字节或原运行记录。原两轮十二NOT_STARTED和第三轮十二grammar绿分别保留；没有重放CLI12/DTO12/DB8，也没有给未来runner自动替换授权。

完整CLI/main、服务/DB/vault、真实Owner/native/安装/强source、System DLL实际路径、API/Worker、媒体/ASR/模型、三OS、Gate0、完整R1后连续R2均不由本片通过。本轮F11及B43后继不读，另卡另版本评审。

自身过程：`G:/开发测试/Codex/VideoCreatorImplementation/Review/ProfileGuardIndependentReview-T57/`，Facts/Snapshot/InputAfter提供完整有限原/copy身份、旧AST保护、四case原事件区间、五完整source及同原process收据；所有读者在正式交接后释放，live=[]。费用/网络/产品或测试执行0。
