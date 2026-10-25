# ADR0023：便携引擎的索引加载与资源准入

2026-10-09。状态：**准入后续实现设计，真实加载与发行资格待独立验证**。A19 只架构；不启动、import、下载或安装产品，不重开编排收费实验，不冻结 Crew/LangGraph胜负。完整 R1 三平台自主视频/多模态/API-MCP 后连续 R2 保持。

## 1 已固定事实

I26 NamespaceSourceGap `36a1b783f4609c0fd44687ce95de32bd253d774381460aab13bdd7ed853c063a` 与正式 MD/JSON/Freeze 已核。I26-B12-W14-Windows-resource-candidate-v1 的 StageMoved 有20568文件，58普通源码/迁移、147生产传递包、381原生静态import/delay表。静态local-import缺件0、纯解释器Initial0和Moved补充0不证明产品、多Agent、动态包、DLL或命名空间通过；原wrapper解码exit1保留。

I24固定ResourcePins保持已列文件及祖先句柄，Windows原文件拒write/delete、祖先拒rename/delete；目录句柄允许write share，不能阻新增目录项。POSIX普通open也不锁写入或目录成员。`._pth`隔离环境/CWD/site，不是后续import许可表。当前host只用旧python_source `-B -m`/PYTHONPATH分派，未固定Migrations env；当前manifest/index没有已准入的加载策略。

I26是B12服务+W6/W7/W11/W13/W14普通overlay；B16 Stage三件未拼入，B17/B18活源未读取。B16新37操作/当前适配器必须另建完整artifact，不回填I26、不把旧I23/现I24compile当新API ready。完整来源与细读范围由本轮snapshot固定。

## 2 最小方案及可信来源

保留现Python3.13.16标准GIL/便携侧车/框架候选。新增**同一可信build生成的 LoadPolicy 索引与受控bootstrap**；按已锁package的实际全部内容允许动态import，不按静态调用图删模块，不全面禁止entrypoints/package-data。先实现一个Windows候选，再按同语义做macOS/Linux平台适配与真实测试。

唯一依赖顺序：固定Backend/Media完整ordinary源+精确锁/wheel/RECORD/CPython→生成资源文件index与LoadPolicy→独立Review/Test资源准入→可信native host build绑定manifest/LoadPolicy全SHA→host验证并hold→受控bootstrap→实际CLI/API/Worker/MCP/ASR。资源准入及许可证/完整运行是分别的事实，角色自写JSON `complete=true`/`namespace_qualified`或目录名称不能代准入。

Installation升级为私有 `native-engine-installation-v2-candidate`，增加独立artifact/version、LoadPolicy相对路径/SHA、bootstrap入口/基础archive身份、固定migrations相对目录、Backend source set与同次实际contract export身份。保resource files/FFmpeg/ffprobe原语义。LoadPolicy引用下级资源hash，不反引Installation自己的hash；host build嵌入精确Installation hash，禁止renderer/env/模型提供可信根。v1开发python_source可保明确dev-only原行为，但不能充v2便携资格或静默绕新gate。

LoadPolicy为唯一 `portable-engine-load-policy-v1-candidate`，闭集schema，至少包含：

| 索引部分 | 必须记录 |
|---|---|
| identity | artifact version、OS/arch/Python ABI/implementation、源码set/lock/RECORD hash、启动角色及真实entry模块 |
| boot | CPython基础binary/必要系统条件、受控bootstrap与基础stdlib archive的文件ID/SHA、允许的builtin/frozen与启动前必要模块 |
| modules | 精确fullname、kind（source/package/namespace/extension）、原资源文件与hash；namespace的显式有限portion/子模块集合 |
| distributions | 精确distribution/version、METADATA/RECORD/entry_points正文hash、实际module映射，保extras与原package元数据 |
| data | package/resource相对身份、实际文件hash/MIME或用途；含证书、模板、tokenizer/config、许可文本等真实数据，不只.py |
| native | 每exe/pyd/dll/so/dylib的实际身份/ABI/hash、静态及delay关系、已识别的动态请求/选择条件、固定解析位置与系统/CRT来源规则 |
| service resources | 迁移原文件集与顺序、FFmpeg/模型/字体/ASR独立profile身份；可写DataDir/TEMP仅数据域 |

多路径fullname/大小写碰撞、重复entrypoint/conflicting metadata、未知resource/native关系明确失败，不按目录优先级猜一个。build前后source、完整文件成员与hash、锁和overlay全部核，所有新增必须通过新artifact及准入；不能运行中pip install、editable/source path回退或动态扫本机环境补包。

## 3 实际Python加载边界

host只以精确绝对解释器/受控bootstrap启动，使用已验证的 `-I -S -B -X utf8` 与不含 `import site` 的固定`._pth`。不能依赖PYTHONPATH给portable入口；忽略PYTHON*配置不意味着应用token/资源env被删除，应用env由可信宿主单独精确构造。

**bootstrap之前的加载也须封闭**：以host已hold的基础stdlib archive满足CPython必要初始化/纯Python bootstrap解析，`._pth`不先开放Code/第三方/用户可写目录。archive来自同精确CPython固定源码，不把全部第三方硬塞zip；bootstrap所需builtin/frozen/可选accelerator行为列明确，不能bootstrap先import任意site包再装守卫。若实际CPython初始化不能按该最小闭包工作，先交精确失败接缝，不偷回完整PathFinder/CWD。

bootstrap解析host已认证并保持的LoadPolicy之后，安装**索引驱动的唯一module finder/loader**，再运行原CLI模块；builtin/frozen只取该精确解释器实际允许表。生产source/namespace/extension未知fullname拒ImportError/受控加载错误，不能落入默认目录扫描、自动sys.path扩展或zip/path fallback。常规import、importlib.import_module、entrypoint.load与pkgutil模块枚举都由同索引解析；namespace允许已登记全部portion，不接受后来新增portion/子模块。

source loader只取对应受控文件/保持对象的实际bytes并核hash后compile，不自动寻找未列pyc/__pycache__；禁写pycache。Windows保持文件/祖先直到child结束，重开路径必须仍对应实际已验证对象；其他OS必须实际核identity并从已核bytes执行，不能把普通fd当防写锁。extension loader先走本节的native准入再调用真实CPython扩展加载。

distribution/entrypoint枚举只来自固定metadata，原合法entrypoint/lazy import可照常用；新dist-info或新entrypoint不自动生效。package resource reader及legacy pkgutil读取按固定data索引，保实际文件布局、__file__及必要resource API兼容；并非所有包都zip-compatible，第三方完整physical data布局优先保持。需要filesystem path的库只拿已列实际文件，不能让未知package data被当代码/配置能力扩张。

对Python层的resource open/明确ctypes及subprocess入口实施索引验证和审计，未知代码/native请求在受控调用前拒绝；package所需正常JSON/schema/template读取保留。审计不是任意C库系统调用的sandbox，也不能声称拦截所有open/exec。Pydantic/Crew等受信库正常代码生成不一刀切禁用；模型输出只经原受控tool/domain协议，不注册新module、finder、脚本或shell。已信任解释器/库被攻破后不在本加载许可表的保证内。

## 4 Native/DLL与目录竞态：能保证什么

Native resolver按LoadPolicy将每个**受控加载请求**解析为已核绝对文件或明确系统来源，unknown、DataDir/CWD/PATH同名候选、错误ABI/hash在调用loader前拒绝。保必要pywin32目录与numpy/PyAV/CTranslate2实际vendor库；不能去掉这些依赖使namespace负向测试变绿。绝对pyd本体不等其所有依赖已安全，静态imports/delay表只是候选关系，动态CPU/后端/vendor选择还须真实运行盘点。

Windows需在最早可控制阶段限制DLL搜索，禁CWD/PATH/用户数据搜索，使用明确payload目录/绝对库身份与实际System32/CRT来源。系统/API-set与可更新Microsoft runtime为独立系统规则，核实际来源/架构/签名或可信系统身份及支持条件，不能从System32复制任意文件或把当时一个机器SHA冻结为所有OS永久值。既有CRT发行硬门/干净机证据按ADR0014保持。需预加载的实际依赖按真实关系保持句柄，basename冲突不猜；非兼容依赖须固定失败交owner，不能强行混配或默换版本。

**限制必须如实声明**：ResourcePins不是封闭文件系统；一次目录成员scan、file readonly属性或新JSON不阻止新目录项竞态。Python索引finder可不选择新模块，但CPython/扩展的Win32动态依赖及已信任C代码自行LoadLibrary并不都经过Python审计。post-load模块枚举/发现异常后停止不是“未知DLL执行前被阻断”；不能用它冒更强安全保证。

本轮采用的威胁边界：防普通项目/模型输入、未信任插件声明、DataDir/TEMP/CWD/继承环境和新增Python namespace影响受控加载；资源build/准入、解释器及随包native实现属于信任基座。**不声称同OS用户/管理员恶意修改受信安装命名空间时仍是完备native执行sandbox**。对这个更强威胁若产品/criteria要求，必须另有真实OS强制封闭存储/权限机制及实测；不能虚构ACL、悄悄要求UAC或拿本ADR缩改旧criteria。

独立测试仍须注入newDLL及目录项，区分“加载请求被受控resolver拒绝”“加载前完整性扫描拒绝”“已载后发现”“同用户根命名空间竞态尚无强制保证”。若当前受控正常路径仍能经CWD/DataDir或未声明native请求加载未知库，该路径不得ready，需有限修复与复验；不能把其风险归入信任基座逃过原范围。现没有任何actual namespace/native资格获批。macOS dyld/签名与Linux ELF/rpath/LD环境须同样独立做实际来源与加载验证，不继承Windows句柄语义。

## 5 宿主、迁移、各child与数据

可信host固定DataDir、资源root、migrations实际绝对路径。Migrations只由v2 manifest中已核相对目录/五原文件推导，宿主设置 `VIDEO_CREATOR_MIGRATIONS_DIR`，不得继承用户外来值或回退DataDir目录。版本/schema与当前Backend真实CLI/export绑定，新生产源需新artifact，不改运行中旧Stage或把B12默认小写migrations冒候选Migrations已接。

宿主显式构造child env，去继承Python/site/customize/PATH注入和Windows/Linux/macOS加载环境；SystemRoot等系统位置必须可信实际解析，不能任意继承伪造同名路径。CWD为受信资源域，TEMP/TMP/DataDir独立可写数据域，数据域不加入sys.path、metadata扫描、DLL roots或源码/插件目录。API/MCP token仍私有childenv，BYOK只走原SecretHandle/权限账本，日志/索引/导出不收secret。

LoadPolicy及bootstrap适用于所有实际进程入口：API、独立Worker、MCPstdio、ASR子进程/FFmpeg工具按自己的固定角色和profile起动，不只主API。现ASR独立runtime/权重复用保版本/hash与许可，新增profile也要准入；不能ASR继续用裸脚本回退绕main loader。Integration定义固定启动数据/资源接口，Backend/Media各在自己owner边界消费，ASR stdin数据ABI与源微秒/方法资格不得默改。

每个活跃child/后台worker持有其资源guard与实际监督所有权直到真实退出；窗口/API关闭不误drop独立Worker资源、也不凭hold句柄宣后台制作仍在。跨进程guard继承仅明确资源/控制必需句柄，不复制Bearer到renderer。更新按新版本目录、停止相关资源消费者并核schema/回滚兼容后切换；不能修改被hold运行目录。真实EOF/shutdown/取消和父异常仍按既有生命周期契约分开。

动态multi-agent/Flow/provider能力仍在：批准目录内的完整Crew候选依赖、已声明workflow driver和正常entrypoints可动态选择；Backend的三原dynamic import站点和Media完整overlay须正向实测。框架未冻结、费用次数和原未知副作用恢复账本保持；环境guard不授外网/收费/发布权限。

## 6 实施切片与独立反例

1. **Integration**：新candidate builder/LoadPolicy/基础bootstrap archive与loader、v2 native Installation/Root绑定/环境/Migrations/资源guard和受控native resolver。先对同一真实147包/58ordinary集合做无产品的导出/加载接口有限验证，再按正式任务作实际免费API/Worker/MCP/媒体批。不能为避失败只包一个health入口。
2. **Backend/Media**：只在正式资源启动接口交接后接自己CLI/factory/ASR启动；Backend仍唯一公开contract源，Media不写root index/锁/OS guard。资源匹配其完整最终版本后才允许native联调，不读对方WIP。
3. **TestDevelopment**：独立criteria及反例：已列文件替换/修改/祖先rename、new module/package/namespace portion、new dist-info/entrypoint/.pth/sitecustomize/usercustomize、DataDir/CWD/PYTHONPATH注入、unlisted pyc、wrong resource hash/direct package-data行为、合法lazy import/metadata/pkgutil/namespace正向、new/同名DLL及delayload/DataDir/PATH候选、已载后检测不可冒前拒、parent/childguard lifetime、移动/空白中文路径/Migrations/完整CLI/Job/Worker/MCP/ASR。保原失败，不改criteria求绿；本节仅验证输入。
4. **Review/Acceptance**：独立核真实机制、threat范围、固定构建来源与许可、产品可用性和每OS证据。署名或metadata不替第三方合法分发；PyAV23库/CRT/BtbN GPL/source/147包/Small权重/font条件继续ADR0014硬缺件。

所有阶段分别收据：静态/stdlib resource、Python loader正负、native请求及来源、实际完整产品、发行/干净OS。任一未知required module/entrypoint/data/native关系、丢失资源身份或不匹配Backend/export版本必须诚实unready/typed失败，给有依据的缺件动作；不是永久默认503或删多Agent/媒体。需要受控补依赖时新build/index版本、独立准入与有限复验，不热装/猜兼容。

本ADR提供可实施的加载规则并承认系统边界，不批准所有第三方已兼容bootstrap或native已封闭。资源only收据与当前无运行源不变；没有model/ASR/API/Worker/MCP、测试、网络、下载、凭证或费用操作。正文/source pins/Handoff固定后释放，后续owner推进完整目标。
