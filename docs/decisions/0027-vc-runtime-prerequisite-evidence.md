# ADR0027：VC运行库下限的证据与安装前置

2026-10-09。状态：**官方规则/准确缺证与后续工程路径固定，八项实际toolset floor仍未证**。补充ADR0014/0025，不改I31/RV37实现、阈值或既有candidate。Architecture不读System32/store/catalog、collector/installer EXE、不load/import/运行产品、不安装/UAC/下载binary/密钥或费用。完整147生产+24 ASR、四profile、三OS及R1后连续R2保持。

## 官方规则和固定事实

Firecrawl/Context7按既有技能和认证CLI使用。Microsoft官方文档确认：2015及以后的14系有跨版本binary兼容，目标redist须不早于构建payload所用工具；重链接的linker须足够新，/GL及/LTCG对象另要求精确工具版本。**这些兼容规则没有给当前各wheel的真实编译小版本**。[Microsoft binary compatibility](https://learn.microsoft.com/en-us/cpp/porting/binary-compat-2015-2017?view=msvc-170)。

官方支持页推荐最新v14，要求目标架构匹配，列Windows10/11及Server2016/2019/2022/2025；版本更新频繁所以网页不列当前exact版本，要求从实际下载包属性取得。`aka.ms/vc14/vc_redist.x64.exe`是变化的入口，不是已固定release/hash，本轮未下载。[Microsoft supported redist](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170)。

官方推荐central redist以便Microsoft维护；merge modules已deprecated，app-local DLL部署存在但官方不推荐其维护方式。redist、merge modules、individual DLL均须实际发行者的Visual Studio许可及对应REDIST条款；Python/wheel的PSF/MIT声明不能替Microsoft组件分发权。[Microsoft redistribution](https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files?view=msvc-170)。

pywin32官方main构建说明要求VS2022 v143/WindowsSDK/MFC/ATL，另列旧工具链；举Python3.13的MSC1941例子。它不是pywin32-312具体wheel或当前CPython3.13.16 standalone的编译attestation，不能拿该例子填14.41。[pywin32 build environment](https://github.com/mhammond/pywin32/blob/main/build_env.md)。Context7也只返回main，无312版本ID；固定wheel的WHEEL/METADATA实际只给cp313/cp313/win_amd64、setuptools版本、包版本/License。旧builtin事实包含Python版本和builtin集合，没有compiler/banner/toolset。

I31正式CompiledFreeze `7cd50ae4…`及普通WindowsNativeContracts `76ceb1ae…`已核：确有八项external_vc，version_condition明确toolset_floor_unknown，minimum OS build也未冻。两EXE编译自然0、未执行；本轮不把compile当source或运行资格。I29精确LoadPolicy及RECORD是有限payload身份/静态依赖来源，不是编译器证明。官方文档、固定包metadata、PE推断及实际运行必须分别记。

## 八项准确前置表

表中统计仅I29固定**api和asr**的正常/延迟表去重边，不将worker/mcp重复累计；不等动态能力完整。完整importer/payload身份及源artifact全文SHA在A24研究表/Snapshot。所有numeric toolset floor均**unknown**，没有填0、当前host版本或推断小版本。

| external VC声明 | 固定静态依据 | 可证下限 / 还缺什么 |
| --- | --- | --- |
| mfc140u.dll | 4个Pythonwin PE，pywin32-312 RECORD：dde/win32ui/win32uiole/Pythonwin；当前未决 | MSVC14系/MFC的一般要求有官方支持；精确312 wheel构建toolset/对应redist下限仍unknown，须原构建记录或同版本受控重建 |
| msvcp140.dll | 9边；CT2 4.8.2、ORT1.30.0、chromadb1.1.1及pywin32对应native；原表按system声明 | 各真实importer的最高工具链要求未知；需要每owner的确切binary/RECORD/构建记录，不以已装DLL版本替代 |
| msvcp140_1.dll | 4边；主环境及ASR的ORT DLL/pyd | ORT1.30.0精确wheel编译/链接小版本及组件兼容证明未知 |
| msvcp140_2.dll | 此api/asr静态seed表未见直接边，I31仍明确external_vc记录 | 不据此删声明或称optional；补对应build/组件来源及真实动态用途，未证保持未知 |
| msvcp140_atomic_wait.dll | 同上 | 官方redist精确release/component清单与需要该组件的payload证据未绑定 |
| msvcp140_codecvt_ids.dll | 同上 | 同上，不用文件名或引入年代给所有payload推最低版本 |
| vcruntime140.dll | 329边，当前解析到随CPython资源内的payload，不是329项System32依赖 | 随包runtime身份与依赖者工具链/发行权都须核；payload解析不让I31外部合同unknown变合格 |
| vcruntime140_1.dll | 99边，当前同样有payload解析 | 同上；不把随包CRT和已装CRT混配、也不从某个DLL版本推所有依赖者的MSVC floor |

RECORD/WHEEL证明哪份文件属于哪份分发包，不证明其编译器。PE linker/version/Rich线索、DLL filename、Python ABI tag或setuptools/CMake/rustc版本分别不足以独立推MSVC实际编译/链接/CRT下限。可记录这些静态线索用于定位owner，但必须标inference，不写confirmed floor。自己的I31 Rust/desktop编译工具也不证明第三方wheel使用相同工具。

## 唯一工程前置与消费字段

保持原规则 `actual_redist_version >= actual_payload_toolset_floor`，按数字版本分量比较，不字符串比较。这里的floor必须是由实际工具链证据映射到Microsoft对应**14系redist版本域**的要求；不能直接把compiler的19.xx、Visual Studio的17/18.xx或某组件file version与redist package版本混作同一数值。package→组件版本/支持关系另绑定准确官方记录；映射缺失仍unknown。Integration在**新**来源合同/资源版中为每条有限记录固定：

- exact basename/source kind/target arch、适用profile；每真实importer与其owner/RECORD/artifact SHA、normal/delay/dynamic关系。
- `payload_toolset_floor`及独立state（confirmed或unknown）、实际支持结论/evidence refs。证据需绑定精确binary或产生它的可追溯构建：source revision、wheel/artifact SHA、真实MSVC compiler/linker/toolset/CRT provenance、相应构建配置。某组件共享多个依赖者时取所有已核要求的最大值；缺一个必要来源不能对已知子集取max后冒全证。
- 选定正式redist的exact release/version/arch、完整包SHA、Microsoft发布/签名来源、组件闭包、适用OS条件、许可出处及实际发行者rights状态。网页latest链接或当前机器file version不是该对象。app-local另绑精确许可redist目录/所有组件/依赖文件身份与本地维护更新责任。
- runtime事实另记actual current library source/arch/version与核实方法，不回填到toolset floor字段；clean-target最低OS/完整使用/更新兼容与发行者许可分别待验。

现collector会对未知floor准确error，应保持；元数据观察可以诚实记录error，不能叫八项/source/产品qualified，更不能把expected-red或仅health入口当R1。A24不修改私有JSON语法或RV37源；Integration按其完整owner任务实现/冻结后交独立Test/Review，不另起公开DTO或Backend SDK版本。

## 可完成的补证和发行路径

默认工程路线为**正式x64 central redist安装前置**，从官方入口取得待固定package、核发布者/完整包版本/许可、与真实payload要求比较；后续在允许安装的独立任务处理已有更高版/重启/失败/离线条件。不能把0x80070666等“已装其它版本”结果盲算安装成功，须核实际版本/完整来源；不降级或删他人共享runtime。无需为运行本工具让使用者安装完整VS编译器。

若确需便携无系统安装，使用实际许可允许的**完整app-local redist闭包**，按正确exe资源位置/受控loader和三OS对应方案验证；不得从System32捡八文件或只复制MFC一件，不能把它混成Windows系统组件。central/app-local改变需要新完整资源/来源合同、actual loaded-origin及全部native能力验证，旧I31不回填。

下一个有限Integration任务先建立**确切owner构建证据清单**，从固定package/官方release构建attestation或可追溯CI输出定位所用compiler/linker和runtime。泛main文档、release发布日期、猜“latest构建”不能补证。若owner不能提供所需记录，明确收束这条补证路线并准备**同版本/同source、同cp313目标ABI的受控重建**清单，固定真实工具链/配置/产物/NOTICE；或提出有足够构建来源的明确artifact候选，须先架构裁定、版本/资源准入和独立兼容验证。本轮不自行换锁、版本栈、框架、安装/执行重建，也不授权无限网络试探。

重建/候选范围由实际需要补证的binary closure决定，保147/24完整内容及MFC/工具/CPU ASR/动态Agent功能，不裁功能绕过重包。形成真实toolset bound后再固定redist release满足它；所定版本是有依据的发行前置，不能将一次当前host成功的版本命名为所有系统“最小可用版”。最后由独立干净OS/完整四profile/实际作品验收冻结产品MinOS，Windows官方redist OS清单不能代这件事；macOS/Linux不装VC runtime也不继承Windows通过。

## 责任与终态

Integration负责唯一private合同/owner构建来源/installer或app-local资源/实际consumer及后续来源事实批，执行仍先固定完整scope与统筹准入；Backend/Media只消费合格固定launch/resources，不补floor/许可Bool、shell或复用未准ASR身份。Test/Review/Acceptance分别核真实下限/错误比较/缺MFC/架构/来源/已有版本/更新/干净OS与完整能力，不由架构改标准。

本轮Firecrawl4官方scrape、Context7官方library+docs均自然0，共享credits715→711观察差额4（非独立账单），没有服务启动超时或盲重启/认证内容输出。所有研究句柄和reader terminal，固定正文/来源/表/Handoff后释放。当前八项floor/实际redist下载身份/实际publisher许可/actual native/干净三OS仍未证，不停留在无限pending：上述owner补证→同版本可追溯重建/候选→正式redist前置→完整验证是具体下一任务链。无System32/catalog/EXE读取或执行、安装/产品/测试/模型/key/费用操作；完整总目标保持。
