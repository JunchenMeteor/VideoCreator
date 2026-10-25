# ADR0012：Gate0完整作品包与本地实际转写接缝

日期：2026-10-08。状态：批准下述最小设计及角色接缝；ASR版本、支持OS、对齐精度、成包和完整创作仍是待实测候选。此ADR不批准实现者更改测试标准，不宣布Gate0/R1通过，也不重开ADR0003收费编排实验。R1独立验收后连续R2及官方产品内API/MCP要求不变。

## 依据及当前缺口

依据01—11、02第6—11节、03 Gate0、09第3—7节和原G0-MEDIA/G0-ALIGN/G0-CONTRACT、MM02—06、AC07/08/13/17—19；固定来源见自身过程A9SourceTrace.json。B7正式交接JSON为42a1fe256e4e30d61b22031b13a5f4c6309dce7c923217d6ec70490a07c73d96；其核实接缝和ADR0010/0011保持。

公开源当前只有BundleRef、简化SemanticSegment和八项默认outputs，没有完整Bundle清单/转写/音轨映射契约。LocalAsrDriver与asr_worker静态可见独立本地CPU子进程、实际解码/音频哈希、离线参数及词时间估计标识；这不是本轮运行证明，主引擎也未据此拥有可分发ASR资源。历史W6模板/旧SAPI及W7恢复证据不等于实际ASR、模型自主作品或已验收作品包。本轮不读取W7/T14私有实例，不要求改正在测的源。

## 1 最小交付契约

后端仍为唯一Pydantic/公开Schema源。以下是下一实施接口清单，名称是候选，须先由后端固定可消费字段/版本；集成再由真实源生成OpenAPI/JSON Schema/SDK。不得手写第二份公开模型或直接修改现有SCHEMA_VERSION来冒充已生成。

| 最小对象 | 必须绑定的内容 |
| --- | --- |
| BundleManifest | instance/bundle/revision、格式版本、production/run/request revision、批准的洞察/Brief/计划/脚本/反馈与来源版本、工作流/工具版本、全部输出角色及依赖、资产/文本文件索引、派生关系、质量和权利范围 |
| BundleOutput | 固定角色、逻辑artifact/asset ID、内容SHA256、字节数、MIME、文件相对路径或受控ID解析、规格/实际时长、方法与许可引用；requested output和固定溯源附件分开列举，拒绝任意额外私有文件 |
| ActualTranscriptRevision | 实际input_audio_asset_id/SHA、音频坐标/采样证据、完整文本、语句/可选词范围、不可识别/非语音区间、ASR模型commit/运行时版本、方法/精度/置信及缺口；approved_script_revision_id只作对照，不能供ASR伪抄 |
| AudioTimelineMapping | 输入音轨固有范围→作品时间线范围的逐片段映射、裁切/拼接/变速的有理数关系、原始sample/timebase证据；旁白、编码前最终混音、MP4编码音轨分别关联 |
| SubtitleTrack | 引用实际转写/对齐版本及映射，cue的整数微秒范围和文本、SRT/VTT导出量化规则；不得按字数摊时码 |
| SemanticSegment与RagChunk | 补齐09中的audio_spans、镜头版本、实际speech/画面证据、summary/topic/main_thesis、来源namespace及文章/选题/事实准确版本、rights/有效期、方法及记录哈希；chunk保留segment和媒体定位 |

默认八项outputs继续全部要求：video、narration_audio、mixed_audio、approved_script、actual_transcript、subtitles、semantic_manifest、rag_chunks。SRT/VTT均提供；封面、洞察/Brief/制作计划、来源/镜头表、摘要、质量报告是固定清单附件。附件只按明确导出权限带入，审核纪要和路线摘要不能夹带凭证/私有日志。当前请求没有“无旁白”契约，不能擅自交空文件；未来仅经固定请求版本显式not_applicable后可省旁白，其他请求不得事后改需求。

旁白为独立真实旁白，mixed_audio为编码前最终时间线PCM WAV。两者可能在无其他声音时内容相同，但必须有真实生产链和用途证据，不能复制文件充混音。MP4编码音轨与混音另记录实际偏移/编码关系。音效/音乐独立stems按请求及许可导出，不默认分离授权。

源稿、实际转写、强制对齐分别持有版本。ASR必须输入真实音轨，完整迭代识别结果；音乐/静音不造台词，不可识别区间明确标识。当前词时码是whisper_word_estimate_not_forced_alignment；未测边界误差和无可比置信时为null/未测，不填写虚构0.95。需要已达精度的请求缺能力时保留waiting_user及可恢复alignment_required，只有请求中明确允许的降级可以继续。

全部公开范围为整数微秒和半开区间，音轨/素材固有坐标与最终作品原点分别标记。范围非负且不越实际解码时长；原始PTS/timebase与编码偏移另保留，偏移可为有符号值，不能当负MediaRange。拼接/变速用逐片段映射，现有单一video_audio_offset_us不足以表达全部R1时间线；本轮不修改它。SRT/VTT毫秒量化不覆盖原微秒表，记录量化误差；词估计不等于满足MM03语句P95≤200ms。

画面描述必须依据最终帧或实际观测，声明observed/model_inference/user_provided及取证范围；prompt、色板标签和计划描述不能充实际语义。精确来源关系与新选题语义检索分别交付；向量/索引建立不影响标准文本包完整性，也不能据JSONL存在宣布MM05精确率达标。

## 2 原子可见与恢复

复用现有AssetService/Operation/Step/lease体系，新增一个BundleService和BundleRevision持久事实即可，不增通用调度器。

1. 固定请求、创作/来源版本、输出角色、权利及批准政策后，已知且结清的Operation结果经实际解码/哈希/范围校验进入实例不可变资产库。媒体和ASR进程在DB事务外运行。
2. 为一个固定bundle_revision_id制作有界暂存清单与文件集。后端验证请求全集、附件白名单、ID归属、哈希/尺寸、真实媒体/音轨关系、转写/字幕/来源关联、质量和批准。缺文件、缺实转写、缺来源版本、漂移、坏媒体或未知Operation均不能发布。
3. 文件/清单完成持久化和不可变定位后，在短事务内重核有效lease/fence、Run未取消/终止、固定版本及全部核验结果；提交BundleRevision、交付Step、Run/Production终态与bundle.ready/production.succeeded outbox。只有此提交后才返回可见BundleRef或成功事件，随后推进Flow。不得先成功再补文件。
4. 文件已落盘而DB未提交时，只核实账本已记录的原revision/精确文件集及哈希；不扫描任意目录、重调生成或修改源稿求齐。DB已提交而Flow未推进时以Bundle/Step事实恢复，不重成包/收费。取消、旧fence、未知/不完整结果保持原失败或待核实语义；ADR0010专用核实权限不因此获得正常写权。

后端须说明落盘与原子替换策略；集成/测试验证所支持OS的实际flush/rename/重启窗口，不能凭“rename原子”声称所有电源故障可恢复。DB与文件系统不是一个事务：先准备不可变文件、后提交可见指针，孤立候选可保留待受控核实，禁止发布半包或删原证据。manifest_sha256对确定UTF-8/LF的实际清单字节计算，manifest自身不递归包含自身哈希；语义记录哈希规则由唯一后端契约固定，重复键/非有限数拒绝。

bundle_get、bundle_export、bundle_reference及语义读取最终共用同一BundleService和固定BundleRef，HTTP/MCP调用同一应用入口；路径按09，不另立Portal数据库。导出解析为包内相对路径，引用通过主体/项目/资产范围、有效期/撤销实时授权并提供Range/ETag。固定ID不是访问密钥；票据不进清单，跨实例ID不得绕权限。导入另一实例先验证全文件/引用一致性再可用，可重建文本索引，无厂商账号/原embedding依赖。

沿唯一ErrorEnvelope：版本/lease/状态冲突409；未授权403/会话401；不存在404；尺寸413；明确不支持媒体415；缺项、哈希/坐标/转写契约无效422；未配置ASR运行时/模型或媒体资源503。错误retryability区分never/safe/reconcile，待核实不能提示盲重交。API需显式声明新增错误并重新生成；“missing”不能包装成成功空转写。

## 3 本地ASR候选准入

2026-10-08实取一手资料，详细URL、精确wheel哈希/大小、模型revision及许可声明见A9LocalAsrResearch.md/A9ResearchSources.json。优先验证现有隔离LocalAsrDriver，候选faster-whisper1.2.1 + CTranslate2 4.8.2 + PyAV19.0.1；这不是锁定版本。CPU int8、不依赖GPU；Python3.13标准GIL、转写隔离资源环境/进程与主编排环境解耦，避免把ASR重依赖强塞主锁。是否共锁由集成真实解析/导入/成包证据决定，不忽略requires_python或借其他任务环境。

small多语言模型候选固定Systran/faster-whisper-small@536b0662742c02347bc0e980a01041f333bce120。model.bin为483546902字节；config/tokenizer/vocabulary与模型共486212372字节，尚不含运行时/全部依赖和安装器，不能宣称包只有该体积。模型FP16存储、CPU int8加载，部署不得凭名称自动连网换revision。

PyPI有cp313标准GIL CTranslate2 Windows x64/macOS x64及arm64/Linux x64 wheels；PyAV19.0.1为cp312-abi3、Python≥3.12。当前wheel标签给出macOS arm64最低14、x64最低11，Linux x64 PyAV最低glibc2.28；CTranslate2 Windows还要求VC++ runtime。标签/官方支持声明不是实机成功：必须另跑干净四目标环境及完整中文decode/transcribe/成包。若目标OS不满足，只能由集成提交有证据的维护版本/自构建候选再准入，不能偷偷升最低OS或无证据降级。

faster-whisper/CTranslate2和模型声明MIT，OpenAI明确代码及权重MIT；保留版权/许可。PyAV代码BSD-3-Clause且wheel包含FFmpeg；实际PyAV/FFmpeg/渲染libx264构建和传递二进制许可、NOTICE/对应源码与分发条件仍须集成核实，不能由MIT源代码推导全部安装包已获准。ASRResourceManifest至少固定运行时/目标OS-arch/依赖锁、模型仓库commit及每文件SHA/大小、许可和NOTICE引用、离线能力/安装完整性；下载/打包由集成后续获分派，不由本轮架构执行。备用whisper.cpp1.9.5仅文档候选，不切换现有实现；中文质量/时间精度未测。

## 4 下一owner与准入顺序

| Owner | 下一可交接工作与边界 |
| --- | --- |
| 后端 | 固定最小Pydantic Bundle/Transcript/映射/语义/RAG字段与版本、BundleService事务/恢复、HTTP/MCP/权限/错误；不改媒体算法或测试判据 |
| Agent/媒体 | 消费后端受控端口；真实独立旁白/混音/音轨关系、ASR与字幕/时码、最终帧语义、候选包材料和质量证据；不改权限/账本/公开模型/生成SDK |
| 集成 | 精确依赖解析、隔离ASR资源与许可清单、离线资源校验、三OS四架构支持矩阵、真实成包及公开源生成SDK；不代写后端模型或修改标准 |
| 测试开发 | 在既有G0/MM/AC下提出实际中文/漏词多词/音乐静音/非零偏移、完整/缺项/崩溃/导入/权限负例，固定标准与执行证据；架构不编写或运行其测试 |
| 评审/验收 | 独立批准标准/接缝并实际视听、检查跨实例/机器/许可证据；只读实现，不能用架构研究替实测 |

先固定最小端口与免费资源，再实转写与成包危险前提验证；不让依赖未冻结阻止后端纯契约准备，不让契约草案充当完成。已有本地模板/授权旧SAPI可测物理交付和源稿差异，明确标实验，不能计自主创作/真实供应商接通。相关owner只在各正在运行批的读取冻结解除后改源。无模型下载授权、实机、许可材料或独立听审时保留blocked/not_run；不新增收费、不动W7/T14私有环境，完整Gate0→R1→R2目标不缩。
