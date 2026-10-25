# 0072：普通本地创作与发行资格分离，接通真实素材制作

状态：ARCHITECTURE_CONTRACT_FIXED / PENDING_INDEPENDENT_REVIEW。这是架构设计裁定；独立评审通过后才由原角色实施。没有产品运行、素材合成、资格签发、费用或发布通过证据。

基线：Backend 停止 CheckpointSourceStage 143、Native 停止 CompleteSourceCheckpoint 48、Media 停止 QualifiedCompletionKindCorrection/AppliedStage 48。0070/0071、既有失败记录、验收阈值及角色职责保持原字节。本决策只纠正“普通本地制作也必须先有独立发行资格”的内部前置，并补当前实际缺失的本地素材生产链。

## 1. 实际问题与取舍

原规格 11§5 要求先实现已有素材及上传音频的免注册本地路径，再完成模型口播、动画。02§8/9、09要求按请求交付真实媒体与语义包。独立研发角色不是用户每次运行工具时必须配备的服务。

实读结果：

| 节点 | 停止源事实 | 本决策 |
| --- | --- | --- |
| `cli/native_startup.main` | 普通入口调用 `connect_native_installation`；仍是未应用候选，没有启动实证 | 保留入口，接真正普通本地安装适配器 |
| `NativeInstallationAuthority.observe/assert_current` | 原 v1 真实 held files 返回 `qualification=not_ready`，适配器仍要求 qualified issuer | qualified 专用类保持语义；普通入口使用下述独立具体适配器，不伪造 qualified |
| `native_owner_setup._continue_setup` | 原真实确认及 `NativeExecutionObserver` 已在；未注入 installation authority | 在同原观察成功后注入普通适配器，使真实首 Goal 能继续 |
| `RegisteredMediaRuntime._current_services/_invoke_current` | 有当前 Owner、同 Run/fence、human/policy、masters→Bundle 接缝 | 保留真实授权与账本；新增显式 local 配方分派 |
| `create_registered_production_drivers` | narration 硬绑 Piper，picture 硬绑 Wan；edit 才有 FFmpeg | 新增固定本地素材工厂；不把未配 Wan 作为所有模式的前置 |
| `FfmpegEditDriver` | 真正三 clips/旁白合成、混音、封面；固定 25fps、三镜头及 720p | 复用受控执行设计；新增可配置本地 timeline 驱动，旧类不冒充完整 R1 |
| `recipe_production` | 仅 affected repair 消费者 | 不用它作为初次创作入口 |
| `bundle_producer` | 真实 ASR/四 masters/六创作版本/验证发布路径，仍有缺资源与等待 | 复用唯一 Bundle 服务，新增真实本地版本映射，不跳检查 |

`LocalTemplateRenderer` 与 `workflows/local_render` 只属于 Gate0 的 10 秒色块实验，不能成为本决策的用户素材驱动，也不能算口播、动画、Bundle 或模型自主创作通过。

## 2. 保留两条真实来源路径，删除普通运行的发行资格前置

普通本地运行保留：原 OS peer/PID/creation/SID、原实例/安装根/宿主图像和完整文件图、实际 held 对象、同线程/epoch 生命周期、Owner 真实一次配置、有限项目/动作/路由、预算、lease/fence、写入前 current/CAS、许可与来源、未知 Operation 核实。

不参与普通本地运行：独立 Test/Review/Acceptance 的签发密钥、suite/check/review/acceptance 报告、qualified Registry record、七执行伴件、qualified writer lease、Root release-role 工厂。它们仍约束独立验收、发行及显式 qualified 路径；不撤销旧记录、复活已撤销 grant，也不把本地安装称为通过发行资格。官方账号、订阅、发布授权更不能成为本地创作前置。

具体迁移：

1. `connect_qualified_native_installation`、`main_qualified`、qualified setup/trust、v2/current-v3 qualification action 原逻辑不变；其调用者仍须有真实已准资料。
2. `connect_native_installation` 不再默认构造 qualified 专用 `NativeInstallationAuthority`。它从原真实 `OwnedAuthorityConnection` 和 `open_owner_protected_native_build` 构造闭合的 `LocalInstallationAuthority`。不得从布尔值、配置 hash、JSON、renderer 字段或任意回调构造。
3. 普通 startup 明确选普通安装路径；不得通过自动 fallback 把一次 qualified 拒绝转成 local 成功。显式请求 qualified 的失败仍是原失败。
4. 普通路径仍调用原 `ProductionAdmissions`，不增加另一权限服务/费用账本/调度器。其 `current_guard` 已允许实际安装适配器；原短 writer 内 `InstallationSessionGuard`、Owner current/floor 和登记身份重核继续使用。普通类不得装配伪 `qualification_lease`。

### 2.1 后端唯一私有安装适配器合同

复用现有 `InstalledProductionEvidence`；其字段是实际文件观察，不是资格声明。固定方法：

```text
LocalInstallationAuthority.observe() -> InstalledProductionEvidence
LocalInstallationAuthority.assert_current(original_evidence) -> None
LocalInstallationAuthority.assert_local_current(original_evidence) -> None
LocalInstallationAuthority.close() -> None
NativeExecutionObserver.production_authority(original_observation)
    -> LocalInstallationAuthority
```

最后一个方法是必要新增的原对象工厂，仅接受该 observer 原 `_retained` 中的同一个 `RetainedNativeInstallation`；不能接受普通 DTO 或相等副本。类的实例只由这两条固定来源工厂生产：原 ordinary connection，或 setup 的原真实 observer。两种来源分支在类内部固定，不能让调用者提供“验证函数”。

`observe` 取得/消费真实原 file observation；完整集合必须精确等于原 launch/setup 的 `expected_files`，按 `engine_file_names` 分区，禁止遗漏与重复。三个原 SHA、instance、观察时刻、workflow `registered-media-bundle-v1`、driver `registered-production-drivers-v1` 全部按现合同核验。adapter 持有 `(actual_source, original_observation, evidence, epoch, thread)` 的身份关系；证据相等不算成员。

`assert_current` 在 SQL 外调用原来源的 current 检查，重核真实 peer、held 文件及当前对象；setup 来源复用 `NativeExecutionObserver.assert_current`，不能观察第二套文件补旧证据。`assert_local_current` 在原短 writer 内只用原来源的本地成员/session/epoch 检查，不 RPC、不 hash、不阻塞等待。Owner/current/源文件更换不能被缓存证据覆盖。close/peer terminal/源 disable/线程转移使旧成员失效；不得复活原 ID。

这不是降低完整运行图保护：当前完整 Python 包源与所选实际资源仍有精确清单、实际文件存在/大小/hash/解码检查。未选择的 Wan/Piper 权重不作为本地资源包成员；保留其代码和可安装能力，不假称那些权重已安装。第三方分发许可、native supplier/toolchain 证明及三 OS 运行仍需独立发行证据。

### 2.2 首 Goal 的准确接线

`native_owner_setup._continue_setup` 保留实际 preparation→native modal/TTY 确认→accepted journal→`OwnerSetupService.execute`。`SetupExecutionInstall` 原 `NativeExecutionObserver.observe` 成功、实际 registration install 成功后，服务通过 `observer.production_authority(self._observation)` 保存适配器和 session guard，并在原 `_configure_execution` 前绑定原 admissions。应在同一服务实际 `_services` 对象上绑定；不得替换已登记 issuer、另建 Engine 或在 `_configure_execution` 提前伪建权限。

随后原 `store.current`→`original_projection`→`register_execution_identity`→`bind_native_registration`→`configure_production_authorization`→`accept_owner_setup_goal` 同原 draft/Goal/journal writer 继续。已完成 receipts 恢复复用；缺步骤由原真实来源恢复，不再确认每个日常项目。setup 连接结束只使该过程成员失效，已提交 Owner/执行登记是原持久事实；API/Worker 下一启动必须分别取得自己的真实 current connection，不能复用已关闭 setup 对象。

## 3. 本地素材生产合同：一份原请求、一条 Run、一个账本

用户只提交 Goal、已有图片/视频/配音/资料；文件先经现有受控 import 成为实际实例 Asset。外部 URL、磁盘路径、原 origin ID 或未授权 Portal 素材不能当成本机可读 Asset。HTTP `production_create` 和 MCP `production_create` 继续共用原 Engine；renderer 不传四个已制作 masters、安装 authority 或内部 proof。

后端维护唯一私有 `RegistrationConfigLocalV1`，`format=registered-media-config-local-v1`。旧 v1/v2/v3 exact parser 不变；未知版本拒绝，不自动迁移旧 Run。字段闭集为：

```text
format, engine_source_sha256,
ffmpeg, ffmpeg_sha256, ffprobe, ffprobe_sha256,
asr_resource_manifest, asr_resource_manifest_sha256,
asr_runtime_manifest_sha256, asr_route_id,
production_resource_manifest, production_resource_manifest_sha256,
production_runtime_manifest_sha256, local_registration,
alignment_registration
```

ASR 四字段必须全部实际有值或全部 null；不是许可丢失时默降。构造普通 API/素材编辑不能强制加载未选 ASR/Wan/Piper。申请转写/字幕/RAG的原 Run 在这些能力实际不可用时进入明确资源等待，不能发布完整包。alignment_registration 复用唯一既有类型/null，并保持当前实际准入。

`local_registration` 唯一闭集：`profile=local-owned-assets-v1`、原 `rights_declaration`、`input_audio_route_id`、`input_visual_route_id`、`edit_route_id`、`master_index_route_id`、`max_duration_us`。全部路线由实际实例/Owner 安装；本地源是 `owned_local`，无 credential、无外发，cost 明确为零。它没有 text/video/TTS 收费授权。可选 BYOK 文本规划独立消费已有被准路由；其费用先走原 Operation，不从这个本地 registration 推授权。完全模型工厂及新生成镜头标准保留。

资源 `production_drivers` 新 exact grammar：`format=registered-local-material-resources-v1`、`runtime_manifest`、`input_audio={kind:uploaded-audio,implementation_source_refs}`、`input_visual={kind:owned-material,implementation_source_refs}`、`edit={kind:ffmpeg,ffmpeg,ffprobe,implementation_source_refs}`。源 refs 精确覆盖所选 factory/driver/validator 依赖；完整 runtime index 无任意插件/module/shell/path。字体在 timeline 选择时必须命中原资源索引。Integration 生产清单，Backend 定义/校验 schema，Media 只消费。

### 3.1 真实计划与私有本地配方

新 `registered-local-material-plan-v1` 是 Backend 唯一领域 grammar，由 Media 原创作阶段产生真实版本，并由原 human plan review 或实际 `PolicyExecutionPorts` 准入。它包含原 Goal/request refs、真实资料 refs、`input_bindings`、`timeline`、`source_script_revision_ref`、`source_script_origin`、原 rights proposal/ref、所选能力/费用/outputs。所有 ID/refs 精确指向同 Run 当前可读原事实；不能以计划内容授文件、网络或预算权限。

`input_bindings` 每项固定 `asset_id,sha256,size,media_type,probe,source_ref,usage`，usage 为 narration/visual/background_audio；允许实际无 namespace 自有输入，按现 copy-input/rights 协议核验，不造 namespace 或拥有权。`timeline` 固定 `width,height,fps_num,fps_den,duration_us,shots,audio_tracks`；shots 每项 `shot_id,input_binding_id,source_range,timeline_range,fit`；audio_tracks 每项 `track_id,input_binding_id,source_range,timeline_range,gain`。范围为原整数微秒半开区间。素材选择、入出点和目标尺寸由 Media 提案，不由普通调用者直接给未验证 FFmpeg 参数。

R1 本地配方必须能用真实图片或视频与上传配音；镜头数可变，不能永久固定三色块/三素材/10 秒/720p。按原 1080p 两比例及参考时长验收，实际帧量化明确保存映射；超出已安装资源上限是明确拒绝/等待，不越界切旁白。纯音频/无旁白依原 outputs 与适用条件处理，不生成假的 narration。

有 BYOK 文本模型时沿原 Agent 洞察/剧本/分镜形成此计划。无文本模型的素材模式可由固定本地 planner 基于实际媒体、用户资料和约束提出可编辑的合成计划：不把规则草案叫模型洞察、不虚构受众/事实/新创作质量。只给 Goal/素材的日常 API 可用既有预授权有限策略继续合成，不要求人填写内部分镜。此模式不计完全模型自主创作 AC/MM 通过。

源稿来源必须是真实输入稿、真实模型稿或“输入音频实际转写派生的源稿版本”，对应 provenance 明示。最后一种要先有真实受控输入音频 ASR，形成独立创作稿再按原 human/policy 准入；最终混音再次实际转写仍是另一输出/坐标系。没有源稿或 ASR 时不能复制 supplied text 到 actual_transcript，也不能伪造六个创作版本来满足旧检查。

### 3.2 唯一工厂与真实输出

新增 Media 固定 `create_local_material_production_drivers`；签名采用原 `create_registered_production_drivers` 的 engine/worker/bundle/storage_root/runtime_root/decoder/资源 SHA 上下文，并接唯一 `local_registration`，返回原 `ProductionDriverBuilders`。Backend 单独固定调用，不能接收 model/caller 指定模块或 callback。服务仍由同 `ProductionPorts` 或 `PolicyExecutionPorts` 构造；普通权限与 unattended 权源不互相替代。

1. narration builder 消费计划内实际已准上传配音 Asset，真实完整解码，按原范围规范化到新的受控 PCM WAV output。即使源已是 WAV，也必须记录原 lineage 与零费用 Operation；不能把普通 input ID填成新 master。
2. picture builder 消费原实际图片/视频与入出点，输出计划范围的规范化 clip；图片只生成真实图像动效/构图，旧视频只重编排/编码。provenance 明确 `derived_from_owned_material`，不能叫文生视频/模型新镜头。重复利用一个素材可有不同受控 derivatives，input/output ID必须区分。
3. edit builder 是新增 `LocalMaterialEditDriver`，复用 `FFmpegRuntime`、`permit_scope`、`install_output`、真实 decode 与原输出 reservation。按受控 timeline 合成实际 video、最终 mix、最终帧 cover；独立旁白保留。混音含实际选择的环境音/音乐或明确无背景音，不能把旁白复制两份冒混音。`FfmpegEditDriver` 旧三镜头语义保持兼容，其构图/混音图可抽出共享纯实现，但原受控边界不变。
4. 流程复用 `_generated` 的 begin_step→allocate_output→原 OperationIntent/execute→真实 succeeded Observation→finish/settled/fenced commit。新 profile 的 step/input/dedupe 固定包含 request/plan/输入 SHA/资源/route/timeline；恢复读原 Step/Operation，不按任务名重置。
5. 原 `media-master` 验证四个真实独立输出并完成原 Step。Backend `_checked_upstream_result` 只接同 Run/fence 的 `masters_ready/waiting_user/needs_reconciliation`。不能从先前 master 回填一个已 blocked 上游。

### 3.3 Bundle 实际接线及输出完整性

Backend 在 `_current_services` 增加显式 local profile 分派，在 `_invoke_current` 的上游部分调用同原本地 Flow，再只在 `masters_ready` 进入 `_final_producer`。缺资源、等待真人审核、已释放 lease 或 unknown 不能继续旧 masters，也不能再次 park。

`create_registered_media_producer/produce_bundle` 接口保留。它增加显式 local plan 的版本解析与真实 Creative 版本映射：有模型产物消费真实原 refs，无模型产物保存本地 planner 的实际方法/限制，不能补假的 `insight/script/quality`。Backend 维护唯一映射/上下文；Media 不直接 SQL，也不定义第二套公开 DTO。原六种旧创作版本路径不变。

请求视频/音轨、真实转写、SRT/VTT、JSON/JSONL 源关联/RAG时仍经原 ASR Operation、真实 validation context、实际音轨映射、独立参考/算法及每作品检查、两次 authority、共享 whole verifier、不可变 READY/publish。默认阈值及 P95≤200ms 不变；没有本片 reference 的显式已准自动策略保 null，不能复制通用分数。源稿、输入音频转写、最终混音转写与强制对齐分开。

媒体已成、必要转写/对齐资源缺失时保真实阶段输出与 reason/resource 请求，完整 Production 不成功、不发 bundle.ready。单独早期素材编辑试用可展示真实中间视频，但不是完整 Bundle；本决策不添加隐藏 output 降级。已发布包走原 Bundle export/ref/grant/asset content/Range/元数据权限，引用撤销不能撤回已合法导出副本，origin 不自动授本机票。

## 4. 独立角色和首次验证：发行工作不在用户实例内签发

用户产品 AI 剧组继续按原创作能力工作；研发 Test/Review/Acceptance 独立角色只在构建与验收环境生产本角色事实。完整受保护图由 Integration 从真实独立角色 entrypoint、锁、实际 imports/native/tool/model/license/data closure 生成不可变 package index；工作脚本归 Test、review/acceptance 入口及实际报告归原独立角色。该 index 是 source identity，不是签名即资格。

0070/0071 的实际 role producer 由本角色执行入口初始化，凭 OS受限签名服务/凭证句柄及原 admitted role/source/work registration 创建，其他角色不获取其密钥。实例 installer 只验证可信归档，不持 Test/Review/Acceptance 的签发密钥，不在首次启动生成独立 passed 报告。实际工作 proof、report body、H 历史与 C 当前检查、S 套件、七执行伴件的原 DAG/用途/版本保持；Owner 管理绑定不升独立角色资格。

首次本地可执行验证改为 normal local profile 的真实有限制作 case，不再调用需要已 qualified 的 `qualification_execution_capture.begin` 来证明自己首次已 qualified。Test 通过真实首配置或原可信 headless Owner 路径、原 HTTP/MCP production_create 建原 Production/Run，固定实际有限素材、明确零预算路线/期限/修订上限；Worker 使用本地适配器与真实 attempt/lease/fence/current，执行实际规范化、编辑、解码、入账、Bundle。如资源缺失照实待验，不发资格。

这条 case 的 Run/Operation/文件/失效及费用记录是真实验收输入。后续独立 release producer 可按原资格合同收集证据、实际检查并签发；没有这些证据的 installer 只能是未正式发行的验证候选。资格案例若仍要求特殊受保护 capture，只在该显式独立 qualified 路径运行；不影响用户 ordinary route。禁止用已有19/31/105/三 binding 失败案例的新名字重试来替代此依赖修复：原案例须先明确实际原因、有限修订和原限次处理，本合同本身不授运行。

## 5. 原 Native capture 桥的实际最小后继

现停止 Native `RegisteredHandlerCapture.read_qualified_original` 只有 Native 半桥；Python `OwnedQualifiedAuthorityConnection.observe_facts` 只存 `_observations`，未持原 handler capture。现 reply 是精确 **14字段**，不是14条可重放帧。保原 reply grammar，不往旧字段偷偷塞 companion。

独立 qualified executor 需要桥时，Integration 在原同一个受认证 qualified pipe 增加显式私有 capability-negotiated `held-resource-capture-reader-v1` 子协议；旧端不支持时明确 NOT_IMPLEMENTED，不影响 ordinary local pipe。唯一方法 `read_original` 读取原已经成功发送并 recorded 的 `(observation_id,observe/assert_current,exchange_seq)`；后端方法 `OwnedQualifiedAuthorityConnection.read_original_capture(original_observation,exchange_seq,method)` 返回原 connection 保留的 held capture 成员。它不是第二次 observe 或资格 minting。

请求 exact fields：`wire,session,seq,method,observation_id,exchange_seq,exchange_method`；method=`read_original`，exchange_method 仅 observe/assert_current。response exact fields：`wire,session,seq,status,code,capture_id,exchange_seq,exchange_method,raw_request,raw_reply,captured_at_us`；失败末六证据字段全部 null，错误码仅 capture_not_recorded/capture_source_terminal/capture_foreign/capture_limit/capture_unsupported。JSON 仍使用原严格 canonical parser/有限 frame limits，不允许任意 dict。

Native 必须由原 `QualifiedRegistration.register_with_capture` 保存 `RegisteredHandlerCapture` 和原 process/Registry Arc；在其原 reader_thread 上执行原 reader，通过有界单请求队列响应同 session 的读取。不能把 thread guard 删除、把新对象登记成旧 capture，或跨线程直接拿 borrowed guard。成功 response 来自原 `HeldHandlerExchange.raw_frames/captured_at_us`，完整 raw_request/raw_reply 保原字节及 hash，原数据字段嵌入必须不重新序列化原 JSON。消息 transport 本身不产生资格。

后端先持有原 observation，在同连接顺序读同原 exchange；绑定原 connection/epoch、observation identity、seq/method、exact request/reply byte hashes/time，再只由原 source factory 生产 `OriginalNativeHandlerObservation` 所需成员。assert_current 同原 connection 请求实际 Registry/current 检查；short writer 只查原 retained member/epoch，本地不能凭 response JSON 重构能力。capture record失败、未到 send_exact 成功、漏帧、旧 epoch、同 PID 不同 creation、不同 Registry、关闭、原 reader owner 终态均 fail；不能再 observe 填过去的 capture。

pipe/handler scope exit 先 disable source/capture，再释放读者/连接；Job 后代终态未证时原资源引用仍按原生命周期保留，不能将 Arc 尚在当成员仍有效。root/native record retire 后 qualified future current失效；历史已提交事实保留。此桥的完整实现与独测是独立发行分支后继，不是本地用户制作的隐含前置。

## 6. 调用顺序、恢复与错误

唯一普通顺序：Native 准备真实 package/host/held file图→原 peer/instance bind→实际 Owner 首配置或 current登记恢复→API/MCP 原请求解析/幂等受理→原 persistent Run queued→独立 Worker 同实例真实 ordinary连接/有限登记→claim 新 fence→固定 local profile 实际 plan/admission/rights→逐 Step/Operation 制作→media-master→真实 Bundle证据/verify/publish→固定 export或授权引用。

资源及 peer/current 检查在 writer 外；writer 内重新查原 Owner/scope/revision/lease/fence 和本地 source member，不做媒体工作。更换资源、策略或输入不得悄悄改变原 Run 的 immutable版本，按现真实变更及重准入/受控修订流程继续。已提交结果先读原 Observation/READY/Step与lease恢复，未知受理/已写未登记先 needs_reconciliation，禁止清 unknown、重新 render、换 key收费、第二次建项目或覆盖旧 bundle。

| 情况 | 必须结果 |
| --- | --- |
| ordinary真实held文件、Owner和路线有效；没有qualified记录/独立签发密钥 | 可运行 local配方，不产生qualified事实 |
| explicit qualified 缺记录/报告/bridge | 原 NOT_READY/503，不转 ordinary“成功” |
| peer/原来源伪造、越scope、local route带凭证/外发/非零费 | 403，无副作用 |
| 同键不同canonical请求、同source成员不同hash、旧fence或原版本漂移 | 原409/CAS冲突，保已提交证据 |
| 坏MIME/解码失败、范围越界、旁白被截断、错误输出用途 | 原422/415具体错误；不登记可交付媒体 |
| 缺FFmpeg/选中ASR/所需真实alignment或许可事实 | 具体NOT_READY/资源等待，保已生成媒体；不全局永久503 |
| 未知Operation、partial/完成文件未入账 | 原needs_reconciliation，受控原输入核实；不盲重算 |
| 真人或实际预授权到期/撤销 | 拒后续副作用，原合法历史读取/已有导出按既有权限规则；不伪确认 |
| public连接断开/窗口关闭 | 不取消原后台制作；必须真实worker服务仍持有任务，进程全停不能冒后台 |

## 7. 直接可分派的实施切片与验证

| Owner | 精确实施接点与交付 |
| --- | --- |
| Backend | `native_installation`普通具体adapter/原source工厂；`NativeExecutionObserver.production_authority`；`OwnerSetupService`原观察后的实际注入；`media_registration`local config/parser/profile/final-context；唯一 local plan/resource schema；复用原admissions/rights/Operation/worker/Bundle/API/MCP，不建第二账本 |
| Media | 固定 local planner及两种 human/policy服务消费；上传音频规范化、已有图片/视频clip、可变timeline本地edit；复用原executor/output/decode/masters和Bundle证据；完全模型路线保留，上传素材不得冒新生成 |
| Integration | 普通 Native host→API/MCP/Worker原受保护connection/完整注册资源包，独立package graph/license；从Backend唯一schema重生contract/SDK；先本地路线接线，再显式qualified capture桥；不给用户包塞独立角色私钥 |
| Frontend | 五步保持；Goal+资料/原生上传素材配音、模式/能力实际可用性、方案审核、真实中间/最终预览、等待资源/恢复/导出引用；不显示内部资格字段让用户填写、不以JS bool授审核 |
| Test | 准备独立真实零费素材case及反例，不改旧阈值/19失败；检查账本崩溃、current/unknown、实际媒体、包完整性及同HTTP/MCP路径 |
| Review / Acceptance | 独评本解耦是否保权限/恢复/真实来源；分别审核实现、独立安装/看视频听音频/交付核验，不由架构关finding |

优先顺序：本合同独评→Backend具体adapter/唯一local ABI与首Goal注入＋Media固定driver并行→Integration普通入口/资源包/生成SDK与Frontend消费→原测试反向后真实有限正向→独立评审/验收。当前代码位置只有 source事实；不能把候选文件、编译0或 UI18471计为制作已通。

最低独测：没有qualified记录仍真实本地成功；三种伪source/相等副本拒绝；setup真实一次确认/重启同Goal无第二project；local禁止收费/外发；原input变更与撤销；图片+视频+音频实际内容可看听，variable timeline两比例；原succeeded文件崩溃恢复不重render；unknown不queue；视频完成但真实ASR缺失不发完整成功；源稿与最终转写差异可检测；真实mix不是旁白副本；sameHTTP/MCP幂等及客户端断开仍后台；导出hash/import origin与引用撤销；qualified请求不得偷偷普通降级；capture缺帧/错session/错线程/退役后不得重建强来源。

阶段交付：现 UI为交互候选→真实本地素材作品包→真实模型口播及≥3新生成镜头动画/API/MCP自动全流程→四OS/架构目标安装独验→R1完整独验→连续R2官方服务/账務/授权发布。每一步只凭实际证据记录；本地素材不是模型新片、ASR资源不齐不算多模态完整、macOS Intel路线/三OS native身份与后代/源包许可/商户和生成API缺项保持未证。不提供虚假ETA，不以阶段成果终止完整目标。

## 8. 固定来源

Backend143 SourceIndex `d4af043b78ab48fcb60acb51576fef7b8c0a7956c90208afd97304d5b3fe5a8a`；RequiredSourceInputs `d593ad74227eaa33098f3beebbe4e4e3c590a7f488454baff1cc972e6f22f88e`。

Native48 SourceIndex `337cd95ebf070105ab6f50acceaff9a02632bdf35b6b32943bdfe2e4fc98a529`；MissingProductionSeams `08ac6efe882cb59e5b6218b44fa165aa7049dd710d998ccbff7f9222ad097c7d`。

Media48 SourceIndex `e90b574d8d179c280bbdad5da413ef854f8cc5fdc89d91ab1205370a339f228d`；production_drivers `3ed2a7511ee1f4d1c2f9dd7798cf739012b044cffe31e5254816b83810ab8a67`；production_edit `4e5d4f04d8327f49286ba25c92aca0c313a18bd980e0d83093c68591261bad66`；bundle_producer `6253c04e9e7e5d89f21944672ee6c9063312d3ef98a265f3bb059abb362bb2cd`。

普通副本路径、实际读取范围、原自有读取错误及 before/after 身份放本阶段固定 InputPins/OrdinaryIndex/Handoff。源码 pin不等源码被运行；本决策不重写任何旧ADR/规格/标准/审批或原失败记录。
