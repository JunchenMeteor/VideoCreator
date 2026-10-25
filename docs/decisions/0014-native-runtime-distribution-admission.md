# ADR0014：Windows ASR资源的运行库与发行准入

2026-10-08。状态：批准下面工程发行方案和缺件清单，不批准当前内部stage公开或商业发行。保持Python3.13.16、faster-whisper1.2.1、CTranslate2 4.8.2、PyAV19.0.1和模型revision，不换框架/版本或产品最低OS。本轮只读I15/I16固定证据与官方文档，不读B9/W9 WIP、不运行产品/资源/测试，不下载或安装。

## 1 已有事实和证据边界

I16正式Handoff MD17e7153245e9fa608dff2d324f5065bf277d8240bed7c72a6f67ac963bcf24a9、JSON2d3909029dbca3ffbd22c01d06ba2f516bb8bd46e829dc924850087a9e72dce2；DeploymentResourceManifest为ac28f82d86e281e1f4779a5a9a3db880d5a1f8e18b0872b4fc525d4e9fe13cd8。固定stage有4614文件/780009532逻辑字节，真实搬迁后ASR运行是集成owner有限证据；不是完整App、干净安装、三OS或精度验收。

实际外部依赖为System32 MSVCP140.dll（643512 bytes，SHA7c26614e1d733892c2deac7e245ce115504b1d80592dd0a01b08e3e5a55f89ca）和MSVCP140_1.dll（35768 bytes，SHA206c931bf90fdad8816de3b5e2ef80b2bcaa9406c89ecc05fe6fddffe251e982）。这些是该机加载身份，不是所需最低CRT版本或随包权利证明；stage自身VCRUNTIME文件也需许可溯源。I16原生采样保留首次枚举错误，不能说全程文件/网络访问已审计。

I15 LicenseInventory SHA5a48d18e88144a601dfdd2a247eb5be36ac072e809f24e89f4ba042086083b1c列出PyAV av.libs实际23个随包DLL，含libx264-165/libx265、libiconv及GCC C++/线程运行库等。FFmpeg库configuration启用libx264/libx265、enable-version3而自报LGPL version3 or later；7库实际版本如avcodec63.1.102已保存。这一清单不等于每个DLL均在I16采样中加载，也不因ASR只解码就免除其随包分发条件。

## 2 Windows CRT采用官方安装前置

主方案为EXE安装器链式安装微软原版、对应x64的受支持Visual C++ v14 Redistributable，然后部署应用及相对路径ASR资源目录。集成未来须固定官方最终URL/原包FileVersion、SHA256、Microsoft签名、架构、条款与构建所需CRT版本；微软文档当前不公布动态latest链接的精确包号，本轮不能编造或固定一个号。CRT必须不早于实际native构建工具要求，不能拿本机DLL hash推版本。官方最新v14文档列Windows10/11及Server2016/2019/2022/2025，这是候选运行条件，不自动修改本项目最低OS。[微软受支持运行库](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170)。

分发微软包/独立DLL受相应Visual Studio许可用户及Distributable Code/REDIST清单条件约束。当前仅存在Build Tools的工具状态和System32加载事实，未核发行主体许可或拟包条款，因此“官方可下载”不等于我们已获随包权利。[微软分发说明](https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files?view=msvc-170)。下一集成先核许可来源，不复制System32任意DLL、不把Build Tools/SDK装到用户机充CRT、不替换系统库。

优先在许可已核后随安装器附微软原包，便于离线安装；权利未核时只能准备官方运行库前置检测/文档和直接微软来源取包方案，不把未核包发布。联网bootstrap和完全离线安装两种范围须明确，不能宣称离线可用却首次必须联网。每次安装核实际x64 runtime/version；较新已装则跳过旧包，失败/重启要求显式处理，不吞退出码。卸载/回滚VideoCreator不移除机器上其他应用共用的CRT。

App-local独立CRT仅作另行有证据候选：来自微软许可清单允许的redist文件、完整所需集合及更新责任，不能从System32抄两件或随意混配。当前不采用它绕开安装权限或发行许可；无需为A11安装/改PATH或再开未知Build Tools安装。Windows干净机安装/无开发工具、重复安装/较新runtime、缺runtime、升级/卸载与真实中文音轨运行是下一owner/测试实证，不由文档担保。

## 3 PyAV与媒体库仍为发行硬缺件

PyAV代码实际LICENSE.txt为BSD-3-Clause；wheel自带FFmpeg是官方安装文档所述，Context7官方PyAV索引也支持此一般事实，但索引main无精确版本，不证明当前wheel完整构建来源。复用A9 PyAV安装来源，本轮Context7没有取得精确19.0.1 wheel的FFmpeg/vendor commit或逐库许可。[PyAV官方安装](https://pyav.basswood.io/docs/stable/overview/installation.html)。

FFmpeg官方明确启用GPL部分/库可能改变其适用许可，并在LGPL路径中指出libx264问题，要求对应实际二进制的源码、构建信息及开放组件的合规链接/替换条件；不能据单一license字符串完成裁定。[FFmpeg官方许可说明](https://ffmpeg.org/legal.html)。当前enable x264/x265与LGPL3自报间缺组件构建/授权依据，本轮不判整包仅LGPL、也不凭字符串推断整个产品必须采用某开源许可证。

当前保留同hash PyAV资源为内部candidate，公开发行门保持pending。下一集成对实际wheel和23库形成逐件Binary→Publisher/精确版本或commit→Build recipe/patches→License/NOTICE→Corresponding-source映射，特别核x264/x265、libiconv、GCC运行库/exception及其他链接库。通用文档的FFmpeg8.x源码构建说明与avcodec63等实际版本不能充精确源码匹配；缺commit/补丁或条件无法证明则保持缺件，不取随机FFmpeg源码贴个GPL文件补齐。

选定确实满足的许可路线后才准备发行：保留实际适用许可/版权，获取与二进制对应源码及构建说明/改动记录、提供可取得方式，验证所选动态链接/替换或重链接条件；产品条款不能覆盖开放组件允许的行为。完整NOTICE要覆盖所有随包依赖，不仅进程当时加载项。原FFmpeg渲染器/libx264发行条件也单列，不以ASR资源清单替整个App许可。

若当前发布者无法提供足够资料，集成回报具体缺件及同版本自构建的候选成本/兼容影响，交架构另判；不默换av/FFmpeg版本、去掉DLL破坏依赖或擅自选另一底层。本ADR不授付费商业codec采购。H264/AAC等产物允许用途/权利仍按正式产品范围核验，库许可不自动授素材或平台商业使用权。

## 4 Python、模型与资源清单

实际Runtime/Python/LICENSE.txt在固定文件清单中，22055 bytes、SHA76900732e5f075b725f754000ad5cab1b2cf89e355c1570138476956b6413cd3。应原字节随包保留；官方Python许可允许按条件复制/分发，派生变更有对应说明，且含集成第三方许可，不能只写“Python开源”。[Python3.13官方许可](https://docs.python.org/3.13/license.html)。

下一集成同时核本任务实际CPython发行基座的发布者/精确build/来源归档、Python及随包OpenSSL/SQLite/TclTk等实际组件与许可证据，不假定python.org文档涵盖standalone构建的一切。现机VCRUNTIME亦须许可映射。I15 24包保留wheel notices，并补CTranslate2 4.8.2、flatbuffers25.12.19、tokenizers0.23.2等Inventory notice_count=0项的准确许可/版权来源；metadata标签不等于全文已附。

模型保持Systran/faster-whisper-small@536b0662742c02347bc0e980a01041f333bce120及可信四文件SHA；核心486212372 bytes。复用A9发布者模型卡MIT及OpenAI代码/权重MIT声明，不再次下载。固定stage模型目录未列LICENSE/COPYING/NOTICE；下一集成补上游权重版权/完整许可和Systran转换来源/原模型revision，作为单独许可附件，保留原模型字节/hash，不把许可标签或自算SHA当安装身份。[发布者模型卡](https://huggingface.co/Systran/faster-whisper-small)、[OpenAI上游说明](https://github.com/openai/whisper#license)。

DeploymentResourceManifest增加可审计发行部分即可：resource revision、OS/arch/实际最低条件、每个运行文件/hash/来源build、依赖及redist策略、组件license/NOTICE/source映射、模型commit/各hash、独立运行/安装收据、distribution_clearance及缺件。内部原manifest不覆盖，生成新candidate版；License/NOTICE引用在固定相对目录解析，不夹凭证、绝对运行依赖或原cache。source/NOTICE本体与下载来源记录分别纳管，不以一句pending作为可发行状态。

## 5 下一集成任务与边界

1. 先准备固定候选文件的分发材料差距表：CRT发行主体许可/原版redist、23库精确构建与源码/NOTICE、Python实际基座、24包零notice项、权重完整许可；不得重下载I15已核包或重跑ASR凑证据。
2. 在后续明确分派中，仅取缺失的官方redist/条款/对应源码材料，核最终URL、签名、版本和hash，禁止不可信镜像。先记录取得和许可结果，安装/源码构建另按分派执行；A11本轮不授权立即起installer或变系统。
3. 做精确资源发行candidate与Windows安装前置接缝；干净机实测CRT完整依赖、相对路径、中文WAV/MP4、原进程清理及离线行为。只有许可/安装/实际运行证据足够才交独立评审验收判断资源发行，不能继承I16现机绿。

当前不存在干净Windows/macOS/Linux验收；Mac arm64 PyAV14、Mac x64 11、Linuxglibc2.28仍只是先前wheel候选条件，不改变支持矩阵。集成可推进许可材料和资源部署，不要求后端/媒体停写。架构只决策，集成独占资源/manifest/Installer/依赖；测试/RV/验收独立。产品内官方订阅必须经允许接口直接生成/查询/下载/对账，私人会员插件不等于商业Provider准入；上述本地资源方案不替代R2。完整三平台安装和R1→R2目标保持。

本轮4/4个新Firecrawl官方scrape、Context7一次library/一次docs实际exit0；credits观察769→765，差额4仅共享服务观察，不混模型CNY20。所有句柄终态，模型费用0/凭证读取0/安装下载0；详细源hash与命令/错误边界见Architecture/A11Snapshot.json及Handoff。文档资料不等于已满足具体发行主体的许可，缺证保持pending。
