# ADR0025：Windows 原生来源、有限同名别名与条件目录

2026-10-09。状态：**准入有限后续实现设计；系统事实、实际加载、完整能力与发行资格待验**。仅 Architecture；不读 System32 文件、不加载 DLL、不运行产品或测试、不安装、不接凭证或调用模型。原 ADR0023 的边界及全部原标准不变；完整 R1 三平台自主视频、八类交付、API/MCP、后台制作后连续 R2。

## 固定事实和官方依据

I29 正式 Handoff、FinalInputFreeze、NextRuntimeSourceAdmission 与分类已核身份。新候选20577文件、147生产依赖和24 ASR依赖；分类182固定源/RECORD无漂移。API/Worker/MCP各53个受影响PE、65条未决边，ASR37个PE、45条边；FFmpeg/probe传递9个PE、CPU ASR86个PE必须保留。资源构建0和分类0不是实际加载通过，原红、partial产物及旧资源不回填。I28 RuntimeContract/loader/builder普通副本是消费接缝，未证明当前产品兼容。

官方事实与本次设计分别记录：

- Windows 会先考虑同名已载模块；主库指定绝对路径仍不等于依赖绝对路径。多个 AddDllDirectory 目录的搜索顺序未指定。因此按字典排序增加目录不能解决同名冲突。[Microsoft DLL search order](https://learn.microsoft.com/en-us/windows/win32/dlls/dynamic-link-library-search-order)、[LoadLibraryExW](https://learn.microsoft.com/en-us/windows/win32/api/libloaderapi/nf-libloaderapi-loadlibraryexw)。
- GetModuleFileNameW 返回当前进程已载模块路径；必须处理缓冲不足、路径格式及实际文件身份，不能以请求路径代替。[Microsoft GetModuleFileNameW](https://learn.microsoft.com/en-us/windows/win32/api/libloaderapi/nf-libloaderapi-getmodulefilenamew)。
- Python3.13 的 add_dll_directory 为扩展依赖和 ctypes 增加搜索目录，返回可关闭对象并发出 audit event；它不替代 Python 模块索引。[Python3.13 os](https://docs.python.org/3.13/library/os.html#os.add_dll_directory)。
- 官方 CTranslate2 安装文档要求 Windows VC runtime；Context7 返回 master 文档而非4.8.2专属版本。固定包4.8.2的真实 `__init__.py` 先添加本包和两个 ROCm sibling/bin，捕获 FileNotFoundError/OSError，再加载本包DLL；精确调用条件以固定包正文为准。[CTranslate2 installation](https://github.com/OpenNMT/CTranslate2/blob/master/docs/installation.md)。
- 复用 A11 官方 CRT 来源：所装redist版本须不早于构建工具版本；当前v14文档列 Windows10/11及指定Server版本，分发权须核实际许可证/REDIST清单。此事实不冻结产品最低OS或授予当前发行者许可。[Microsoft supported redist](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170)、[Microsoft redistribution](https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files?view=msvc-170)。

## 1 唯一私有来源合同

Integration 在**新** artifact 中生成 `portable-engine-load-policy-v2-candidate`；Installation及Rust consumer仍同一可信build绑定其全文SHA。旧v1资源保持原字节，严格dispatch未知版本拒绝；实现同步更新builder/bootstrap/loader/consumer，不能把仅更新版本号的v1当v2。公开API/SDK及账本无本次变更。

v2保完整modules、metadata、data、native及四profile，增加下面三组明确记录；不以一个 `qualified=true`、basename前缀或文件SHA授信。所有引用是同artifact相对身份，不允许模型/renderer传目录、策略或来源事实。

| 记录 | 最少成员与含义 |
| --- | --- |
| `system_contracts` | exact basename/contract ID、source_kind、OS/arch、适用profile和importer边、官方依据、OS/工具版本适用条件、实际来源验证方法、分发方式/许可状态；已记录minimum build或unknown，unknown不得变null/默认通过 |
| `native_alias_groups` | exact basename、显式canonical payload、有限members、每成员完整SHA/size/PE machine/owner RECORD、三类import/delay/dynamic对应边、相同完整关系闭包的依据、期望实际origin及预加载顺序 |
| `conditional_search_directories` | exact relative path、owner distribution/module/source SHA及受控调用、Windows/CPU profile、`absence_only`、允许缺失的固定理由、存在时唯一允许身份或明确拒绝；不含通配符/用户路径 |

`system_contracts`分三类：Windows OS组件、明确API-set合同、外部VC运行库。`ucrtbase.dll`/旧`msvcrt.dll`的OS组件身份与`vcruntime140*`/`msvcp140*`/`mfc140u.dll`的VC前置分开；wheel内改名MSVCP属于payload，不属于OS库。现builder的 SYSTEM_NAMES 混合列表及任意 `api-ms-win-*`/`ext-ms-win-*`前缀不是来源合同，必须派生到明确记录和目标OS实际映射，不能整个前缀无限放行。

I29提案36个exact路径只是候选事实输入：35个OS候选和单独MFC候选均不是自动已准库。Integration按后续固定批读取精确文件、物理身份/架构/静态表/版本；缺失、reparse、未知API-set目标、来源或支持未证保持具体失败，不用PATH/别处替换。本ADR不执行或直接授权该事实批，完整helper、工具/依赖/读写范围与独立终态仍先交统筹准入。

宿主从可信OS API取得实际系统根与系统目录，拒绝继承SystemRoot/WINDIR/`--system-directory`自报值成为权威。针对OS组件，需可信Windows安装/目录来源及Microsoft签名或系统catalog验证结果；静态PE/版本/SHA、.NET返回目录或文件存在单独都不证明发行者。离线catalog/签名核实应记录使用的方法、链/信任与未检查的在线撤销，不将未检查撤销写成绿；不强求每个OS DLL都有嵌入签名。若本机验证方法或信任材料尚未配，具体缺项与下一动作保留，不能用假Bool解锁。

`bcryptprimitives.dll`按这套OS组件来源受控核实，不能从其名字、PE头或BCrypt另一公开API文档推定它的独立公开ABI/MinOS/可分发权。支持矩阵需目标系统实际加载及官方支持条件；开发机存在只证明该机器事实。VC/MFC采用ADR0014的官方redist前置或已许可app-local完整闭包；不从System32复制文件补包。发行者实际许可/REDIST、版本下限及干净机器条件仍待证。

MinOS不偷偷调整：当前v14支持条件给Windows候选的必要系统约束，具体最低build仍按原Gate0由完整CPython/VC/WebView2/全部native目标机冻结；单库API的旧最低版本不是整个产品最低版本。macOS/Linux保持原目标、对应签名/dyld或ELF/系统ABI验证另做，不继承Windows规则，也不因Windows当前证据推三OS通过。

## 2 本次唯一有限alias

仅对固定关系授予设计准入：`msvcp140-a4c2229bdc2a2a630acdc095b4d86008.dll`，两成员各575056 bytes，SHA `a4c2229bdc2a2a630acdc095b4d86008e5c3e3bc7773174354f3da4f5beb9cde`。API/Worker/MCP成员是同根 `Runtime/Python/Lib/site-packages/numpy.libs/` 与 `google_re2.libs/`；各自NumPy2.5.3及google-re2 1.1.20251105的RECORD必须保留。canonical明确选**numpy.libs这一成员**；不是运行时按首个找到/路径排序选择。ASR profile若只有自己的NumPy成员，独立记录其本profile身份；不跨解释器/根共用句柄或搬运主环境DLL。

builder将两个NumPy importing PE映射到NumPy owner，re2 importing PE映射到re2 owner；owner对应的requested member再指向有限group canonical。完整正文相同之外仍核PE machine、static/delay关系、有效闭包及RECORD归属；某边不能唯一判owner、同名新成员、SHA/size/ABI/闭包不符则明确collision，不自动为其他同字节库产生alias。保留两文件及原provenance/许可，不改名、不删文件、不修改第三方代码。相同字节不替代真实兼容/分发权验证。

consumer在任何相关扩展/vendor初始化之前，核两成员和完整依赖并串行按依赖顺序从canonical绝对路径受控预加载，保持真实handle。预加载前检查进程已载同basename：未知或非canonical origin不能继续靠预加载覆盖。受控ctypes对已登记member的绝对请求规范映射canonical；记录requested importer/member与实际canonical origin两者，不伪称每个owner路径都已加载。不可依赖AddDllDirectory顺序；循环依赖作为显式有限SCC核闭包，不能递归跳过未知边。

实际origin以模块handle/已载模块枚举及规范化后的真实文件身份为准，与held canonical文件、SHA/size、machine/依赖对应核；不能检查LoadLibrary参数后写`actual_origin_verified`。首次/正常动态及delayed loads都留来源收据。多handle/非canonical member实际加载等差异须真实报出并独立裁定，不扩大有限origin集合求绿。未观察到使用只能写未观察，不证明延迟能力完整。

## 3 CTranslate2缺目录语义

仅Windows CPU ASR固定4.8.2受控来源的两个路径：以本profile已held site-packages为根，`_rocm_sdk_core/bin`、`_rocm_sdk_libraries_custom/bin`。登记owner/source hash与完整父路径边界。原`ctranslate2/`本包目录必须实际存在、属于native/data index并受guard；不能把本包缺失也归入可忽略条件。

用受控 `os.add_dll_directory`入口与audit协同：固定合法路径**确实不存在**时直接产生原调用可捕获的 FileNotFoundError（明确缺目录原因），不调用Win32添加、不返回假cookie、不新增搜索目录。不能在audit只放行后让目录出现再被Win32注册；缺失路径不得解析到DataDir/TEMP/CWD、reparse或外来祖先。受控caller归属须由已indexed/核源的调用上下文验证，不能把filename字符串或audit仅有path参数冒充owner证明。正常cookie须由resolver保留并在child终态关闭，不能因第三方没保留返回值提前释放搜索资源。

同一条件路径实际存在时：只有新artifact登记其完整真实native/data/owner/用途并明确准入该profile才可增加；本CPU候选没有ROCm内容声明，故**存在的未知目录明确LoadingError拒绝**。其它未知存在/不存在目录也不享此例外；不宽泛捕获LoadingError、不猴补第三方、不把ROCm未装写成GPU能力通过。以后增GPU条件需正式完整资源/版本及验证，CPU的86 required PE、PyAV、NumPy、tokenizers和VAD资源均保持，不借此删除required能力。

## 4 消费、生命周期和独立证明

四profile共用v2严格语义，按各自解释器/资源根区分native来源。原I28固定argv、Installation/LoadPolicy/Bootstrap/archive、闭集env、Migrations、data域隔离、私有Bearer、Worker/MCP/ASR guard及owned自然终态不变；supervisor保持guard到所有实际child终态。更新用新版本目录/新全SHA，不热修I29 Stage、锁或运行资源。window/API退出不等后台Worker取消，OS/VC更新或资源身份失效需重新核当前事实，不能将上次来源收据永久缓存为有效。

系统runtime facts是本次可信host启动上下文，绑具体OS/arch/build、所用方法、实际路径/file identity/版本及观测范围；OS组件可正常更新，不能固定一个开发机SHA为所有OS永远值。payload/alias仍精确artifact SHA。来源未满足的required controlled请求在loader调用前拒绝，具体错误交consumer，不能永久默认503代完整实现。现安装策略不是任意C代码的OS sandbox；post-load发现异常不能叫执行前拒绝，ADR0023原威胁边界、未知native/新增目录独立反例及更强标准要求均不放宽。

Integration下一切片只改自身builder/LoadPolicy/loader/native consumer与发行来源记录，先固定新ordinary/diff/artifact和精确事实读取批，再正式Bootstrap API、Worker、MCP、ASR/工具完整运行批。Backend/Media只消费正式私有launch/profile，业务/公开DTO/费用权限不扩；不能裁掉动态Agent包、metadata、entrypoints、package data或后台执行规避错误。真实完整制作的版本接通与三OS验收仍有后续任务，不以health批或expected-red终态代成品。

Test独立准备并Review其标准：系统路径/env伪造、OS/VC类别混用、缺系统组件/MinOS边界/签名或catalog未证；wrong-owner alias、同名不同bytes/PE/依赖/new member、reverse import order/预载foreign origin/actual DLL路径、真正延迟和动态加载；合法CT2 CPU目录缺失、未知现存ROCm目录、缺本包、reparse/目录在核实时出现、未知缺目录及cookie/handle终态；完整合法147/24、FFmpeg9/ASR86、lazy import/metadata/data/namespace、四profile与移动/中文路径、独立Worker guard/父异常。这些是验证输入，不由架构改标准、实现测试或宣布验收。

原I29资源/原红保持，准确已验事实仅资源/静态和本轮官方研究。现没有系统文件读取/actual DLL load/guard兼容/产品/API/MCP/ASR/作品/许可/干净三OS资格。完整owner动作和未证项交接后释放；不等待机器或许可证占槽。
