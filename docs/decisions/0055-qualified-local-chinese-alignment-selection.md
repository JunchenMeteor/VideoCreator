# ADR0055 — 中文本地 forced alignment 默认算法与资源路线

- 状态：APPROVED_SELECTION_DESIGN_ONLY；2026-10-10。批准原角色按下述精确算法/模型继续实现和准备资源，不批准当前 runtime、许可闭包、算法资格、200ms质量或三OS交付已经通过。
- 任务：QualifiedLocalAlignmentDriverSelection，SHA a3766d2fb6c0b6771c32ead0839389440960819e7f8a8cf69477544d24ee3ea2；此前 Backend task 缩写准确为 ed5eb884，不修改旧卡。ADR0053/0054 原字节不改，原两个真实 precision authority、200ms/MM05、ASR被拒执行边界及本轮有限测试/预算原样保持。
- 本轮仅8次官方公开资料请求；Firecrawl与Context7均实际使用。没有模型/package下载、安装、推理、产品/SQL/原生执行、账号操作、凭证读取或模型费用。

## 1. 选定默认，明确完整平台尚未成立

默认实现选择固定 WhisperX 3.8.6 的 CTC forced-alignment 算法，配固定中文 Wav2Vec2-XLSR-53 模型，CPU/float32，专用本地 worker。不是运行 WhisperX 完整 CLI；不重新转写、不启用 diarization，不加载会员插件或自动联网下载模型。既有最终 ASR、原源稿与 actual transcript 保持独立原文；对齐输出是新 AlignmentRevision。

| 候选 | 本轮一手事实 | 决定 |
| --- | --- | --- |
| WhisperX 3.8.6 | 官方API区分 load_align_model/align 与 transcription；说明语言专用模型及CPU/Mac用法。PyPI实给Python>=3.10,<3.14、Torch/torchaudio~=2.8.0和BSD-2-Clause；官方tag已解析真实commit | 默认CTC路线，后继复用精确alignment源码/必要import闭包，不让完整ASR/diarization依赖和联网行为自动入包 |
| stable-ts 2.19.1（官方版本提交 d89c6250fd4745115b44b83a8a3f7ebfd0e2a1f1） | 官方README给文本 align/align_words、Whisper与Faster-Whisper用法、MIT；main另有新算法实验性变动，不能当2.19.1行为 | 此轮不设第二默认，不沿原Whisper时间戳做“自证精度”；其模型/runtime闭包本轮没有完整核定，未来替换需另有固定来源/独测 |

选中的是可实现的算法和中文资源方案，完整跨平台供应链尚未证明。原02§11/299明确Windows x64 EXE、macOS arm64和x64 DMG、Linux x64 native/OCI；保留全部范围。Mac arm64资料不能替代Intel Mac，平台无资格时不能注册成ready或宣R1通过。

## 2. 精确代码、模型及分发条件

代码来源：
- 官方Git tag v3.8.6 → commit 3ccc17b8de34f305300f8a3fd3c9f76ba820c0d0，type=commit，实际metadata已取得。[官方tag](https://api.github.com/repos/m-bain/whisperX/git/ref/tags/v3.8.6)
- PyPI wheel whisperx-3.8.6-py3-none-any.whl，16,486,941 bytes，SHA256 cb6d4fcd3fb6c42305cb8b222a33a0b78f6b657e9db3b714345fe43dc0a69c1f；sdist 16,490,881 bytes，SHA256 d647aecaa6c2f413bb924d722d925878ef300c99093ca49cd6cb7840bdbffe0e。元数据发布日期2026-05-25；这些是发布方metadata身份，未下载核实际字节，也未证明source↔wheel完整构建绑定。[官方PyPI](https://pypi.org/pypi/whisperx/json)
- 代码声明BSD-2-Clause。Integration必须取得固定tag的完整LICENSE、版权与实际复用源码/import闭包，并保留原通知/修改标记及producer记录。Media不能拿main示例或tag metadata当作已审固定3.8.6代码。

模型来源：
- repo：jonatasgrosman/wav2vec2-large-xlsr-53-chinese-zh-cn，commit 99ccb2737be22b8bb50dcfcc39ad4d567fb90cfd，公开、non-gated、language=zh、模型卡声明Apache-2.0；无需产品注册或云账号。[官方模型metadata](https://huggingface.co/api/models/jonatasgrosman/wav2vec2-large-xlsr-53-chinese-zh-cn?blobs=true)
- 本默认只用 pytorch_model.bin：1,276,296,151 bytes（约1.19GiB），公布LFS SHA256 de031fd4b29e0c0667e5346450fadfe1326c89936b888b59c4ede608db763ee4。不打包另一份1,276,132,578B Flax权重。
- 必要原文件：config.json（1567B）、preprocessor_config.json（158B）、special_tokens_map.json（85B）、vocab.json（44357B）；另保留README/model card（7722B）、完整许可/必要NOTICE。metadata中的Git blobId是Git SHA1身份，不是可填进model_files的SHA256；实际取得每件文件后才能生成资源索引的完整SHA。
- vocab就是该固定模型字表，不引入另一个MFA词典/网络词库或默认为其另有再分发权；它连同模型文件进入同许可闭包。模型卡Apache-2.0声明只是来源资料，Integration仍须携带固定许可/通知并核上游基础权重、词表、代码和实际分发义务；不能靠一个布尔值授owned/licensed。
- 模型卡报告的CER19.03、WER82.37且verified=false不是本系统对齐P95、中文游戏术语效果或200ms资格。必须实测，不能复制为本系统报告。

资源成本明确：最小权重本身约1.276GB，再加CPU Torch/必要依赖、Python、算法worker、许可和当前Engine已有全功能资源。最终压缩安装包、磁盘总量、峰值RSS、加载时间和CPU吞吐量尚未测；不能只按16MB代码包估算安装成本。集成须给实测清单，不将估算伪作实测，也不偷偷删除原147+24能力闭包换小包。

## 3. CPU runtime及Intel Mac后继

选择与上游发布要求一致的Torch 2.8.0 CPU系列、标准GIL CPython3.13（当前Engine基线3.13.16不降级）。本轮实际读取官方CPU wheel索引：

| 必需目标 | 已取精确候选二进制身份 | 状态 |
| --- | --- | --- |
| Windows x64 | torch-2.8.0+cpu-cp313-cp313-win_amd64.whl；SHA e1ee1b2346ade3ea90306dfbec7e8ff17bc220d344109d189ae09078333b0856 | 仅供应商索引；未取得/加载/核CRT和实际producer |
| Linux x64 | torch-2.8.0+cpu-cp313-cp313-manylinux_2_28_x86_64.whl；SHA 8f81dedb4c6076ec325acc3b47525f9c550e5284a18eae1d9061c543f7b6e7de | 同上；wheel tag含glibc2.28条件，不修改项目冻结的minOS或宣全部发行版 |
| macOS arm64 | torch-2.8.0-cp313-none-macosx_11_0_arm64.whl；SHA 057efd30a6778d2ee5e2374cd63a63f63311aa6f33321e627c655df60abdd390 | 同上；不能拿这个tag替其他native依赖或整App最低OS |
| macOS x64 | 已抓同官方索引未列Torch2.8 CP313标准GIL的macOS x64项 | **binary producer缺口**，不当缺机器就算实现完，也不宣平台不可能 |

[官方CPU索引](https://download.pytorch.org/whl/cpu/torch/)。只用cp313标准GIL项，不用cp313t；Linux默认不装PyPI可能关联的CUDA/NVIDIA包，Windows不用CUDA默认runtime。CPU配置不需要GPU/云令牌，optional GPU须独立固定设备/config/native/resource和精度资格，不自动激活。

Intel Mac唯一下一工程路线是**同Torch2.8.0的受控CPU source producer**，沿同中文模型/算法，不新增未研究的ONNX或另一默认。不把这条计划说成已经可编译：
1. Integration先有限官方来源核Torch v2.8.0精确源码commit、必要submodule、第三方来源/许可与native构建支持；再固定Mac x64 CPython3.13.16、Apple Clang/SDK、构建工具、原minOS、CPU/无CUDA/MPS策略与实际receipt。当前这些sourceproducer完整事实未取得，本轮8/8已用完，后继另按Root卡处理。
2. 在实际Intel Mac构建wheel/私有runtime；必要torchaudio2.8.0等import闭包也须对应producer与license/native记录。结果要绑定原源码/工具/锁/产物内容SHA，不冒称上游wheel、不借Windows/arm64构建证明Intel。资源root与运行期loader/held-source护栏照原合同。
3. 真实 import、CTC forward、完整中文alignment、取消/超时/恢复/实际peer/资源变化和原质量门均在该目标机器独立验证。没有实机或构建失败保留准确SourceGap；Root随后基于有限新一手证据裁替代，不偷偷换Python3.12、旧Torch2.2、minOS、删Intel或将长期unsupported当完整产品。

完整WhisperX3.8.6元数据还包含faster-whisper、CTranslate2、nltk、numpy、omegaconf、pandas、pyannote-audio、huggingface-hub<1、Torchvision0.23、Torchcodec、Linux triton、Transformers>=4.48等范围。**不直接pip install整个包当默认worker**。Media/Integration从固定3.8.6源码审实际alignment调用与必要import闭包，做受控专用worker；不需要的transcription/diarization模块不入此worker的执行闭集，原Engine已需要的能力仍保留。未审闭包时不能直接宣布“只要Torch+Transformers”。其余实际依赖必须由Integration解出精确锁、可重现build/source/版权/native/平台清单；本轮未选出所有transitive版本，实际runtime资格为NOT_READY。

Torch及其他runtime完整LICENSE/THIRD_PARTY_NOTICES/native版权与producer闭包本轮未取得；许可准入待取得固定产物核验，不靠代码BSD或模型Apache标签替整个runtime。没有下载资源之前，配置/注册/manifest存在也不算ready。新增runtime隔离在held生产资源包中，不变更全局环境或替换主Engine编排框架。

## 4. 固定driver ABI、离线加载与中文语义

继续0053 sole profile qualified-local-forced-alignment-v1、RegistrationConfigV3和生产resources-v2；Backend唯一typed grammar、登记与权限，Media只实现其既有固定builder，不新增公开capability/第二model。

具体builder沿原BoundProductionDriver接口：

`create_registered_alignment_driver(request_data,allocated_outputs,*,ordinary_lease,cancel,deadline_monotonic)->BoundProductionDriver`

输入只由原同runtime services/held command提供0053原完整事实：actual source transcript/ref与单位文本/ID、实际decoded audio ID/SHA及其音频时钟/映射、真实允许affected单位集合/必要边界闭包、完整command/child/source绑定、当前resource/qualification refs与原Worker分配的child输出。原真实permission/current与两个precision authority在外层执行；JSON只是payload，不是身份。独立基准/本片独立参考的目标时间和人工边界**不允许进入推理请求/切窗/归一化参数**。

算法worker固定执行：
- 只调用选定CTC acoustic forward+WhisperX alignment/trellis/backtracking与char alignment路径；上游API load_align_model/align中选择CPU并显式return_char_alignments=True，不调用load_model/transcribe/diarize。实际3.8.6签名与import闭包由后继固定源码核准；README主分支示例只是API选择依据，不代实际3.8.6源码验证。
- 使用原decoder取得单声道16kHz PCM；保实际source sample_count/audio_sha和原音频mapping，重采样是已固定配方且进入input/config SHA。加载时必须核模型preprocessor/config真实sampling_rate为16000及固定CTC模型类型/字表，否则拒资源，不依文件名猜配置。frame/sample步长从实际配置/输出长度取得，不宣已有20ms或更高精度实测。
- 模型只从本次held资源包内实际本地文件加载，local_files_only=True、trust_remote_code=False、eval/no_grad、CPU float32；不存在文件立即NOT_READY，不能隐式Hugging Face下载、torch.hub、gated模型、远程代码/telemetry。pytorch_model.bin是非safetensors序列化权重，后继须用固定Torch安全加载/weights_only和真实源码检查；若实际loader不能满足安全加载，先固定失败证据/生产期安全转换方案及新内容SHA，不用任意pickle加载蒙混。
- 中文字符与原语句/词单位分开：保持原text/utterance/word IDs和原字符串跨度；NFC、模型字表case/空白及可忽略标点的确定映射记录为配置和审计映射。不能借英文空格分词重定义中文验收单位；不能猜数字、货币、简称或游戏术语发音后偷改原文。词/语句区间由其实际匹配字符区间聚合到原单位，标点不伪造独立发音。
- 对字表外字符/实际未发声、缺失区间、低覆盖、单调/重叠/越界错误显式返回不可完整对齐；不复制旧ASR词时间、不补等间距时间、不把插值的缺字当已观察证据。固定覆盖/异常策略随method configuration identity与独测一起准入。
- 必要上下文可以读取完整实际音频/文本，但输出只替换已授权affected单位及其真正边界一致性闭包，未影响单位原字节/identity保留。没有合法单位映射不全片fallback；需要扩范围回原真实目标授权。
- CPU模型上下文内存有界：Media实现最多30秒声学窗口、固定0.5秒上下文重叠的候选切窗配置；较长作品仍按原最多600秒总范围分窗处理，不能降低作品时长支持。切窗只用实际转写的粗窗口/纯音频上下文和源文本单位，不用独立reference边界；原单位跨窗匹配合并及不确定覆盖要真实核验。无法合法分窗则明确缺能力，后继必须完成长音频路径而非永久拒所有长作品。窗口/阈值参数属于待独测固定method config，不是已合格值。

资源映射保持原alignment字段恰kind、model_revision、model_files、configuration_sha256、worker_resource、runtime_resource、license_artifact_ids。model_revision用上述40字commit；model_files含选择的权重、config/preprocessor/vocab/special_tokens各真实SHA；configuration_sha256绑定上述algo/version/commit、模型/语言、CPU/dtype/sample_rate、char映射/缺失策略/窗口、线程/版本锁与输出量化；worker/runtime/source/native/license都需完整当前资源索引。新增profile配置由Backend唯一定义/校验，Media不造另一个schema；资源路径不是下载URL，未知SHA不能填0或null伪可用。

## 5. 输出、进程与精度权威

BoundProductionDriver.invoke只能在原executor签发的真实Operation permit之后执行，账本/当前权限/固定input/dedupe/原scope/取消/期限先于效果。zero-cost owned_local、alignment capability、credential-free不等于可绕原账本/unknown预算或改scope。worker为固定资源入口和固定参数，不能执行模型shell/任意module；它只读取已授音频/文本和held模型，写原allocated child文件，不承接API/MCP/ASR stdin通道或建立通用RPC。

- 解码/driver资源由本次原held authority与实际child/process身份保持；使用已批准host进程约束/资源观察/current验证。worker不得临时下载或再spawn任意工具/未知后代。线程数固定候选上限4并受实例限制；deadline/cancel用原attempt真实单调时间/回调，父异常/正常终态沿既有平台实际机制。本卡没有批准被拒的ASR supervisor变体。
- 长推理不占SQL writer。actual cancellation/timeout按原owned进程生命周期终止、确认真实终态并保存结果；没有确定终态/Observation即原unknown/reconcile，不重交新key。partial输出不能登记成Asset/READY。
- 输出为原AlignmentRevision/V03、新文档完整source/音频/方法/执行身份和原半开区间整数微秒；真实char/frame时间转换采用固定decimal/sample量化规则，记录原时钟/映射。输出整数微秒只是存储坐标，不宣微秒测量精度。实现需验证0<=start<end<=实际audio duration、原文本/单位覆盖/顺序、有效source mapping和完整SHA。
- Worker原文件manifest→真实Observation→settle→原decoder/验证→READY登记后才参与child/Bundle；外层canonical context、原READY/子ASR lineage及0053/0054目标关系不可省。builder返回/配置hash不是合格算法或许可。
- 原基准 qualification 与 per-work runtime WorkValidation分别保留。实际独立基准标注只供Test/真实qualification report/authority；其时间不进入infer。无本片reference的0.3自动路径P95=null，完整真实method/runtime报告不可缺，不能复制基准分数到每片。旧strict/reference路径仍需要本片真实参考；真实P95>200ms须拒绝或原有界repair，不靠审核变绿。
- 两次真实precision authority继续验证当前source/时机；second=false保持403，不能把CPU运行或模型卡指标当authority。

缺资源/资格/安全加载/合法切窗配方时是具体NOT_READY；合法文本不能完全匹配则不可对齐/有界修复或指导，不能输出成功。private错误映射/唯一ErrorEnvelope由Backend沿原契约实现，不创建另套公开错误或永久503占位当产品完成。

## 6. 最先可实现的角色切片与验收

1. Integration（原角色）：先按Root授权另取得精确代码/模型小文件及许可材料、公布内容SHA和普通副本；此卡未下载。复核精确3.8.6源码↔发布artifact/source绑定及actual alignment闭包；按上表准备CPU资源/全transitive锁/native/build/NOTICES与原来源guard，给真实包体/RSS/加载测量计划。Intel source producer单独有限后继；旧147+24功能资源保留。没有资格时交candidate stage与准确缺件，不能fake registration ready。
2. Media（原角色）：从固定普通源码实现专用CTC worker/硬编码builder，完成中文单位映射、离线加载/选择输出、实际window/长音频、cancel/deadline/日志和原BoundProductionDriver/Operation/child接口；不创建Worker、authority或许可。first actual CPU算法/模型推理由Root后继授权，保持原ASR边界。
3. Backend（原角色）：唯一config/resources/profile校验、当前资格/Owner/action/source/route/目标与预算、actualmethod refs和两authority；接同实际factory+heldABI，不以seed/policy bool授ready。资源增量coverage和未知/恢复原规则不变。
4. Test/Review：固定独立中文reference和单位映射，测试清晰/快语速/数字简称/中英夹杂/游戏专名/静音缺读/背景混音/TTS；独立验证，不新增阈值，沿原200ms/MM05既有criterion完整单位和原数学口径，不只展示好样本。测受影响子集与未变边界、错误模型/vocab/resource/license/current/guard、remote-download拒绝、partial/kill/restart/dedupe/费用及长音频真实终态。每个平台包括IntelMac实际ABI/推理/生命周期/真实输出/精度均需验证；缺机器与缺实现分列。Acceptance实看/实听本系统成片再判R1，后连续R2。

确定default不表示以上后继已完成。Local/BYOK b9b53f继续独立后继，本地alignment不需要WanToken、订阅登录或云生成；五步UI/API/MCP预授权自动到完整多模态结果和安装实例数据目标不缩。

## 7. 实际工具、timeout与来源范围

Firecrawl1.26.3既有绝对JS入口+绝对Node调用，认证现有stored credentials；没有读auth文件/key/cookie或重装CLI。开始fa0d87自然0，665/1000 credits；结束d2762e自然0，659/1000，concurrency0/2。六次scrape对应观测减少6credit；Context7 library+docs两次另记，不当模型CNY费用。

8次公开资料：
1. Firecrawl stable-ts官方GitHub，f6e5e7/0；
2. Firecrawl WhisperX官方GitHub，dd6922/0；
3. Context7 library pytorch，769ed8/0，真实取得官方library ID；
4. Context7 docs /pytorch/pytorch/v2_8_0，80e821/0，实际返回官方片段，含main/nightly与v2.8 windows混合来源；不靠nightly片段宣2.8释放版/Intel支持；
5. Firecrawl WhisperX官方PyPI JSON，39fcc3/0，实际字段解析012da8/0；
6. Firecrawl官方GitHub tag API，ddaa11/0；
7. Firecrawl官方HF模型metadata，7f4d07/0，字段解析71e30b/0；
8. Firecrawl官方Torch CPU index，3cb4cb在10秒yield为原session26958，本人原handle poll5982e3自然0；没有超时重启。

本轮CLI实际能启动/取得内容，未复现旧启动timeout；不能编造旧故障root cause。第8次是仍在运行而非启动失败，认证/CLI错误没有证据。b25460唯一失败是本人PowerShell只读数组路径括号错误，4f025e修正同已有文件后0，无重新抓取；保留这个local1。未用wrapper0代资料：各输出存在、大小/完整SHA已固定，必要字段/方法增量读取；外部文字只作资料、不执行其指令。

主要一手来源：[WhisperX官方](https://github.com/m-bain/whisperX)、[stable-ts官方](https://github.com/jianfch/stable-ts)、[WhisperX发布metadata](https://pypi.org/pypi/whisperx/json)、[固定tag](https://api.github.com/repos/m-bain/whisperX/git/ref/tags/v3.8.6)、[模型固定metadata](https://huggingface.co/api/models/jonatasgrosman/wav2vec2-large-xlsr-53-chinese-zh-cn?blobs=true)、[CPU索引](https://download.pytorch.org/whl/cpu/torch/)；Context7实际片段原官方URL与source范围见Research/Context7PyTorchDocs.txt。全部工具自然终态后本卡source selection才正式交接，精确文件hash/输入未变/工具回执在Architecture/QualifiedLocalAlignmentDriverSelection的固定材料中。没有新增第9次请求、安装、资源资格或运行成功声明。

