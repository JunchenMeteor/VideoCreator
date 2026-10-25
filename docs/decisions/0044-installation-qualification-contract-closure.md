# ADR0044 — 安装资格精确合同与首次信任接线

状态：A45 ARCHITECTURE_SOURCE_ONLY，2026-10-10。补充ADR0043，解决固定AbiSlice Interfaces的A—E；不是实现、资格报告或安装许可。原v1、公开SDK、单Engine/Daily、四profile、147生产+24ASR、独立Review/Acceptance及R1后连续R2不变。本地/BYOK不要求产品账号，数据仍由安装实例持有。来源全路径/完整SHA/实际读取范围见A45 InputPins.json。

## 1. 严格共用类型

所有对象拒未知键、重复JSON键、bool代整数、非canonical UTF8、NaN、重复集合项。canonical沿ADR0043；集合按下面固定顺序，文件按relative_path Unicode码点升序。Identifier/RelativePath/SHA沿原领域语法；不扩大到URL、UNC、遍历、任意模块路径。Ref恰document_id/revision/sha256；所有引用必须在原受保护材料索引找到完全相符的实际内容，不能仅比较客户端给的SHA。

I64=0..9223372036854775807；PositiveI64=1..该上限。SQL/Control/record的revision、registry_revision、revocation_floor、checked_at_us、valid_from_us、expires_at_us、Ref.revision、文件bytes全部用严格I64，时间/revision须正数（floor可0）。原wire seq保strict uint64；不得把大于I64的record整数存成REAL/TEXT、截断、取模或补0。reserve在DB revision达到I64上限时明确拒新变更，不溢出。valid_from_us < expires_at_us；不自动续期。

### A. target

恰os/arch/conditions。允许实际发行目标对windows/x86_64、linux/x86_64、macos/x86_64、macos/aarch64；新增目标须显式版本变更及真实资格，不推断已有机器。windows-amd64 LoadPolicy明确归一windows/x86_64；其余由实际发行构建receipt/目标机报告同时匹配，不从字符串猜测native ABI。target不能由renderer/Goal选取。

conditions为以下tagged union数组，顺序os_floor、python_abi、cpu_features、windows_crt、libc；每kind最多一次；windows有前四项，linux有前三项和libc，macos有前三项。未知floor/缺report直接not_ready，不能默认最新版或最低0。

| kind | 其余精确键与值 |
| --- | --- |
| os_floor | product=windows_nt/linux_kernel/darwin（随os）；version=[三个uint32]；report_ref=Ref |
| python_abi | implementation=cpython；version=[3,13,16]；abi_tag=cp313；gil=standard；report_ref=Ref |
| cpu_features | features为闭集x86_sse2/x86_avx/x86_avx2/arm_neon的去重有序数组，按此顺序；report_ref=Ref。只能列实际全依赖所需/已测能力，不能编造AVX需求；不得混入异架构能力 |
| windows_crt | components为八项数组，每项恰name/floor，floor=[四个uint32]。name顺序mfc140u.dll、msvcp140.dll、msvcp140_1.dll、msvcp140_2.dll、msvcp140_atomic_wait.dll、msvcp140_codecvt_ids.dll、vcruntime140.dll、vcruntime140_1.dll；report_ref=Ref。实际floor来自原批准依赖闭包及实测，缺件拒 |
| libc | family=glibc；version=[三个uint32]；report_ref=Ref。本版linux artifact仅此ABI，musl另版本 |

目标权威来源为原NativeInstallationGuards.host/control/payload观察、NativeBuildReceipt、实际LoadPolicy platform/python_abi和独立目标机报告的交集。必须核实际CPU/loader/平台peer及后代机制，后者仍在资格suite与报告，不为条件表新增假平台保证。

### B. profiles

record.roles恰[api,mcp,worker]；profiles恰四项按[api,worker,mcp,asr]。每项精确键name/artifact_version/executable/bootstrap/entry_module/command/adapter_module/adapter_callable/load_policy_sha256/required_files/required_files_sha256/report_refs。

| name | entry_module | command | adapter_module / adapter_callable |
| --- | --- | --- | --- |
| api | video_creator.cli.main | serve | video_creator.cli.native_startup / main_qualified |
| worker | video_creator.cli.main | worker | 同上 |
| mcp | video_creator.cli.main | mcp-stdio | 同上 |
| asr | video_creator.media.asr_worker | null | null / null，保原stdin ABI及独立解释器闭包 |

artifact_version取原固定发行元数据，不是临时git或profile自报；executable/bootstrap取原对应LoadPolicy条目。required_files每项恰relative_path/bytes/sha256，包含该profile实际全部模块/namespace/metadata/distribution/data/native/SCC/工具/迁移/bootstrap归属文件；required_files_sha256为整个canonical数组SHA。builtin/frozen无伪文件，通过原LoadPolicy及report_refs绑定真实解释器图。profile的地图必须与原完整payload/full_file_map和engine_partition映射相合，不能用相交子集求绿；版本差异须明确完整闭包。至少保现有147生产distribution及独立24ASR，数字不是可删除其它文件的上限。原owner-setup额外pre-API入口继续索引并纳入完整文件/机制测验，不挤掉asr。report_refs非空实际suite报告Ref数组，按document_id/revision/sha256排序。

现有IndexedBootstrap仍调用旧main，Integration必须将可信固定LoadPolicy/indexed qualified计划接main_qualified；禁止env/publicselector/任意import决定资格模式。ASR不能误接API adapter。

## 2. C — 真正安装动作先于资格：唯一强来源路线

signature恰128个小写hex，decode为64字节Ed25519；trust_mode恰publisher/local_verifier。public key为32个原始字节，只从已接纳原强trust source取得；record/pack/locator/env没有可信key入口。full record SHA含signature；verify签名输入为仅移除signature的完整canonical record。issuer_id与所接纳anchor匹配，与business Owner、OS SID分别处理。无算法协商、fallback或自己实现密码学。

首次安装没有OwnerBinding/Daily/qualified Engine，必须以原安装主宿主已有OS来源创建安装信任动作，而非调用生产management gate。实际接线点是固定I62 native_installation.rs82–114的NativeInstallationGuards::from_packaged_host/原三组ResourcePins，owner_setup_directory.rs48–84原OwnerDirectory HANDLE/祖先/Owner保护，owner_setup_window.rs18–83原interactive_session/show/NativeInput，owner_setup_runtime.rs9–26原InstalledSetupDriver持有同installation/resources/instance/parent关系。这些只提供真实宿主、目录、GUI输入事实，目前没有qualification trust producer；新增具体producer由Integration实施，不能把现有NativeInput或OwnerSetup confirmation直接提升成报告批准。

唯一新native类InstallationTrustProducer持上述原对象，crate-private prepare_trust(*,installation,control,resources,directory,parent,trust_materials)->PreparedInstallationTrust。trust_materials只能从固定受保护安装输入中实际持有的材料选择：publisher独立产品发布者锚/provenance，或local_verifier完整固定代码索引、suite、独立Review/Acceptance refs及本机锚生成来源。禁止候选pack内自供key自动入库。unsigned本地安装可由实际OS Owner在原native独立确认窗口明确接纳这套来源；这只接纳可信来源，不批准候选资源。展示全部host/build/目录/来源/key指纹/代码版本与有限权限，不在webview新增AUTHORIZE bridge。

PreparedInstallationTrust仅native原成员，无Deserialize/Clone构造；持有原guard/NativeInput/完整intent/nonce/OS session/期限。首次未知instance时不含伪空ID。ADR0042原child初始化实际SQLite identity并完成原bind_setup后，唯一bind_instance(prepared, original_owned_child, actual_instance_id) -> BoundInstallationTrust；核同原PreparedLaunch/OwnedProcess/OS peer/build/目录及同实际Engine，消费一次。identity phase不写trust/Control、不碰vault/Owner/Goal。人工等待阶段没有writer lease。

BoundInstallationTrust端点locator只通过原同child stdin在setup_bound之后、任何OwnerSetup动作之前交付，不加NativeStartupRecord十字段或原bind_setup六字段。首次trust计划唯一固定索引入口video_creator.cli.native_owner_setup.initialize_bind_and_admit_trust(*,initialization_record:bytes)->int，复用ADR0042同Engine前两阶段；旧initialize_and_bind/旧计划不等待新帧。Integration在原bootstrap增加固定内部owner-setup-trust计划，仍保全部四production profiles与原owner-setup，不由env/renderer选取；同Engine continuation在成功第三阶段后才进入OwnerSetup，不能调用旧入口再造Engine。新增第三阶段stdin恰wire=native-owner-instance-trust-handshake-v1/event=admit_installation_trust/seq=3/instance_id/locator；locator为下述purpose精确对象。成功stdout恰wire/event=installation_trust_committed/seq=3/instance_id；失败恰wire/event=error/seq=3/code/status，沿原安全错误闭集，勿回显输入。每帧32MiB，10s绝对接收期限。只接受已绑定原host/同Engine此阶段一次帧；normal qualified factory不接收此命令。首次缺trust材料明确结束为not_ready，不循环重启。此独立第三阶段仅新可信计划启用，旧ADR0042两阶段wire/形状/行为不扩宽，identity phase不安装trust。
新增私有purpose=installation-trust-admission，wire=held-installation-trust-v1-candidate，复用原Pipe底层FIRST_INSTANCE/remote拒/Owner+SYSTEM DACL、OpenedChild HANDLE/绝对deadline/原注册，不使用日常Owner或qualified票。locator恰pipe/session/role/server/purpose/instance_id；role和purpose均固定installation-trust-admission，server恰原pid/creation_filetime/sid/image/image_sha256，instance_id必须为post-bind实际值；接收端先核真实OS peer再核关联数据。唯一request恰wire/session/seq/method/instance_id，method=admit；reply恰wire/session/seq/status/code/instance_id/trust_admission。成功code=trust_source_admitted；trust_admission恰action_id/accepted_at_us/issuer_id/trust_mode/public_key_hex/material_refs/host_build_receipt_sha256/intent_sha256，其中public_key_hex为64小写hex，material_refs=非空Ref数组。该JSON不是票，只有同原已绑定native producer成员及实际accepted动作当前的exchange能返回；Backend保存的是认证后强对象，不能从reply泛用构造。错误trust_admission=null，原422/403/409/503规则，单次10s exchange；拒绝/EOF/crash/未知不重放确认、不fallback。BoundInstallationTrust只能被原consumer消费一次，unknown保原动作状态待exact receipt核实。

Backend唯一NativeInstallationTrustConsumer在原initialize_and_bind完成之后、OwnerSetup/日常生产装配之前消费该purpose，由同Engine/Bundle原business身份映射产生InstallationTrustAdmissionSource（强member对象）；来源包含原peer/build/held目录/完整intent和真实安装动作。其固定方法admit_source(*,engine,bundle,bound_connection)->InstallationTrustAdmissionSource，只能安装trust/floor/admission，不能Owner初始化、Execution登记或制作。首次不依赖OwnerControl已初始化：持原DataDir排他安装锁和QualificationControl，empty registry校验后由这个真实source初始化资格Control并落真实action。后续改锚/撤销走已有Owner管理认证+同安装source来源，不让初装模式重复替换已接纳锚。

流程明确为原OS安装事实→独立信任材料→实际安装确认→同child实际ID→post-bind可信trust admission/action→正常OwnerSetup→真实资源资格记录/独验→qualified生产装配。不存在先qualified才可确认、先Daily才可运行verifier的循环。local_verifier是独立有界安装/构建工具，允许离线固定合法样本，无生产Goal/云Provider/费用；自身代码与validator先独评独验，实际资源suite/许可/ABI闭包通过后才签有限记录。其私钥由原受保护本机工具/vault句柄持有，本文不生成或读取。确认来源不能替代真实测试。未知、unsigned或报告不齐仍not_ready，不无限startup验证。

外部factory签名保持ADR0043不加anchor参数；内部唯一open_native_qualification_trust(*,engine,bundle,connection,build)->NativeQualificationTrustSource，从同held native build/peer持有来源和本实例真实已commit trust action/admission/Control读取锚。原v2bind只传事实，随后该固定读取核当前protected trust snapshot和同DB/action/ref/floor，得到原成员不可复制source；无callback/setter/Protocol注入。Native registry同样从原安装guard+受保护trust snapshot/action关联读取。两端签名/完整refs/同build/instance/current均一致才构造Concrete issuer，缺来源准确qualification_unavailable。不重播初装窗口、不接受旧DTO为live来源。

## 3. D — 同SQLite、原Control、精确持久边界

以下是后端下一迁移的逻辑DDL合同，不在本文执行；实际编号由后端按最终schema分配，不覆盖旧迁移。全部表在原SQLite。TEXT JSON按canonical原字节保存并验证限长；public_key_hex严格64hex。禁止UPDATE/DELETE不可变admission/record/event；服务写者在同connection核键/ref/hash，迁移用触发器防改。重启均重验真实source，不反序列化强对象。

| 表/主键 | 精确列（除注明外NOT NULL） |
| --- | --- |
| installation_qualification_trust / admission_id TEXT PK | revision INTEGER UNIQUE、action_id TEXT UNIQUE、issuer_id TEXT、trust_mode TEXT、public_key_hex TEXT、materials_json TEXT、host_build_receipt_sha256 TEXT、intent_sha256 TEXT、accepted_at_us INTEGER、source_receipt_json TEXT |
| installation_qualification_records / record_id TEXT + revision INTEGER联合PK | record_sha256 TEXT UNIQUE、record_json TEXT、trust_admission_id TEXT FK→trust.admission_id |
| installation_qualification_events / registry_revision INTEGER PK | kind TEXT枚举trust_admit/record_admit/replace/revoke/trust_revoke、action_id TEXT UNIQUE、request_sha256 TEXT、trust_admission_id TEXT nullable FK、record_id TEXT nullable、record_revision INTEGER nullable（成对null或联合FK→records）、receipt_json TEXT、occurred_at_us INTEGER |
| installation_qualification_current / singleton INTEGER PK CHECK=1 | registry_revision INTEGER FK→events、trust_admission_id TEXT nullable FK、record_id TEXT nullable、record_revision INTEGER nullable（成对/FK）、state TEXT枚举not_ready/qualified/revoked |

所有INTEGER加范围CHECK；revision和时间PositiveI64；registry从1开始，current无记录时不是qualified。events保存完整可信action receipt/ref；source_receipt_json只是持久事实，只有受保护当前强consumer核验才有权写。current qualified要求真实完整record、当前trust admission、未撤销/期限有效和原registration/maps/target/build/role/profile一致。无现成报告时可以只有真实trust admission+not_ready，不mint伪record。

复用原commands(owner,scope,idempotency_key,request_sha256,result_json)，PK原三列；scope=installation-qualification，owner来自Bundle业务映射。canonical request精确action_id/kind/trust_admission_ref/record_ref/expected_registry_revision，nullable ref按action语义固定；同key不同SHA冲突，exact retry保IDs/body/结果。kind trust_admit要求trustref、recordref null；record_admit/replace要求两refs；revoke引用当前record；trust_revoke引用当前trust、recordref null。首次admission的trustref由原consumer确定admission_id/revision及canonical持久body SHA，action接受不能由caller自填。

QualificationControl复用AbiSlice InstallationQualificationControl.py及ProductionAuthorizationControl原锁、reserve→pending/fsync→短DB commit→complete→单调floor，不能initialize_new当资格。外部minimum_revision高于DB、pending或snapshot不一致均拒production；只exact source/request/key/receipt恢复。snapshot采用原Control受保护目录内QualificationTrustSnapshot.json，恰format=installation-qualification-trust-snapshot-v1/instance_id/registry_revision/trust_admission_ref/current_record_ref/state；指向固定不可变admission/material附件。原来源/Owner/DACL/HANDLE、action/Control/DB一致共同建立信任，文件自hash不授权。Native仅读原held snapshot/material对象，pending时不授新lease。首次/升级先reserve，DB提交，写受保护snapshot并fsync，complete后才native验证切current；任何崩溃窗口not_ready/unknown，不清原Operation/预算。

日常锁序：原Admissions RLock→OwnerControl→ProductionControl→QualificationControl→Native Registry读lease→原SQLite短writer。原file lock非可重入；一个outer scope持有并向inner传原guard，禁止重开同.lock或递归RPC取lease。初装走上节DataDir安装锁→QualificationControl，不取得不存在的Owner/Production资格；安装后不能用初装route修改。Native handler绝不持Registry写锁再等待Backend file lock：revoke先关闭新lease入口，待原读lease实际释放，再按既有控制锁序持QualificationControl修改/commit/snapshot，最后native exclusive切epoch/current；pending期间无新发放。source验证/file读取/RPC均在SQLite transaction之前；writer只同connection核行和本地原guard。

## 4. E — v2的有限lease扩展及纯本地writer

本节明确修订ADR0043的v2候选（尚未发行），旧v1一个字节不改。v2请求方法闭集由bind/observe/assert_current增加begin_writer_lease/end_writer_lease。begin恰wire/session/seq/method/observation_id；end恰wire/session/seq/method/lease_id；其余方法原字段不变。完整reply在原12字段+qualification_binding之外增加lease_binding，因此v2恰14顶层字段，不允许同时接受13字段宽松语法。lease_binding平时/错误null；成功begin/end恰lease_id/observation_id/record_ref/registry_revision/revocation_floor。begin code=writer_lease_acquired，end code=writer_lease_released，status200；qualification_binding保持对应完整原record不变。descriptor仅协议关联，不能独立构造授权对象。

Native begin必须从原session成员取已认证borrowed observation+QualificationRegistry实际RW read guard，同时保持原资源/附件/HANDLE guard；与同original OwnedProcess绑定。end消费该session实际active RAII guard后回ACK，不能从bool/JSON判断释放。每session仅一个outer lease；重复begin或错误lease_id返回409 lease_conflict，不把重入当第二授权。inner多个writer钩子可复用原outer成员，不再次锁文件/取lease。无跨thread、跨Engine/session/connection复用。

Backend具体issuer保ADR0043issue/assert_current/纯local assert_local_current签名，新增唯一私有current_writer_lease(*,evidence)->ContextManager[QualifiedWriterLease]和assert_writer_current(*,sql_connection,lease)->None。强lease仅原issuer创建、原同thread member identity-map，含原Evidence/observations/ref/floor/epoch/native session/实际guard生命周期；不是bool。assert_writer_current用传入的原SQLite connection核current/event/admission/record、pending/floor、原成员/epoch/thread/lease，禁止另开connection/RPC/hash/OS/vault。assert_local_current在qualified branch仅核原缓存source/lease成员，不能调用v1 transport.assert_local_current（它实际检查OS）。旧facts-only支路不静默升级。

原ProductionAdmissions.current_guard/management_guard在Owner/Production guards后、SQLite之前取得QualificationControl和current_writer_lease；原_AdmissionGuard保存该强lease，所有实际短writer以同connection在开始及commit前调用assert_writer_current。Goal/OwnerSetup/注册/恢复各原qualified短writer接同钩子；Backend负责完整transitive writer audit，DG-P01仍独立修复/评审。standalone observe/assert_current可核当前source，但不得长持writer lease到child空闲。已accepted资源工作PreparedLaunch/原pins/driverchild继续按原真实后代终态持有，其生命周期与短writer lease独立。

get/release沿原10s绝对exchange期限。begin失败不启动writer；timeout/EOF/crash无法知道Native是否已持lease，Backend不可重发begin或用新session绕过，invalidate本地epoch、拒后续writer，由原OwnedProcess清理/真实终态回收。end必须在commit/rollback结束后；end失败保未知状态，不能撤回可能已commit的结果或说已释放；Native保实际guard直到成功end或原child/持有scope真实终态。不能到点自动丢guard让未结束DB writer继续commit。正常close先拒新操作/失效issuer成员，已进入writer先结束/回end，再关原connection/build；强行close走原child终态，不能close布尔值假释放。不能在writer lease内等待人工、Provider/下载/生成/模型/GUI、长空闲或获取其它外部锁。revoke/replace阻新lease、已有短writer结束、原锁序变更+epochinvalidate后新current验证；已有accepted任务/unknown账本仍保真，资格撤销不伪称取消已受理媒体。

## 5. 各owner的下一交付与未测边界

Backend：严格A/B/Ref/签名/parser14字段；首次NativeInstallationTrustConsumer/admission表及原commands/Control恢复；固定open_native_qualification_trust内部强source+Concrete issuer；当前outer writer lease与同connection前后钩子；原入口签名不变。冻结独立source/interface，不自供key/通用dict/假issuer；不混独Review的DG-P01闭合。

Integration：原host/window/directory来源上实现InstallationTrustProducer与独立purpose，实际publisher锚或已独评local verifier接纳、保护持久snapshot及完整pack/材料；原held v2 Registry/RW guard/session/lease/fault清理；可信indexed main_qualified路由及四profile完整闭包。将cryptography50.0.2作为engine直接依赖候选并固定锁/实际native ABI图，现root lock的传递依赖不证明成包。缺合法许可/CRT floor/ASR/PyAV23/full147+24等必须逐件交真实来源和报告。

Test：严格unknown/duplicate/int64边界/假key/复制descriptor/跨Engine与thread/错误profile闭包；真实首次无Owner安装、samechildID、sourceadmission后Owner再qualified启动；pending/DB/snapshot/Control断点和exactretry；重入/获取与释放超时/EOF/crash/真实终态、revoke与短writer竞争；检测writer不发生RPC/OS/file/vault调用。真实资格suite覆盖四profile/full许可/ABI/workflow/driver及合法离线样本；Review/Acceptance各自独立，设计签字不能代报告。

当前缺上述producer/consumer/strong source、真正qualification pack/verifier/锚接纳action、完整资源/license/ABI/三OS报告及独评独验，仍not_ready；无新增账号前置。本文不授运行/签名/安装/费用。本轮只读源+两工具官方资料，未产品import/SQL/OS授权/测试/密钥/模型/安装/部署。

Ed25519按[cryptography50.0.2官方文档](https://cryptography.io/en/50.0.2/hazmat/primitives/asymmetric/ed25519/)的32字节公钥与InvalidSignature语义、[RFC8032](https://www.rfc-editor.org/rfc/rfc8032.html)的64字节签名；SQLite边界按[官方datatype3](https://www.sqlite.org/datatype3.html)。Firecrawl三个实际status200，Context7 /pyca/cryptography取官方main文档（非50.0.2索引版本）；无密码算法运行或签名生成，工具证据与失败/截断限制随A45交接保留。
