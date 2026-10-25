# ADR0042 — 同一原配置子进程先读实际实例，再绑定首次 Goal

状态：A43 私有接缝设计准入；未实施、未运行、未独立验证。2026-10-10。
依据：I62 固定 BackendInstanceHandshakeRequest（ff2fa02d5a65e66152c3e26c7ae157ceefe30c389535d7eb65b762296dd6c951）；B42 NativeCandidateApplication 固定86源索引（aecd0ec796b6d44d3a594f4b297d614addb03277564f7d4a219be1d0acf31fcd）；ADR0038—0041。完整输入身份/实际读取区间见 Architecture/StartupInstanceHandshake-A43/InputPins.json。完整R1独验后连续R2，三OS、本地免产品注册/BYOK与前台五步不变。

## 决策与真实缺口

EngineService.__init__ 唯一通过原 Database/data_dir 初始化、INSERT OR IGNORE 实际 metadata.instance_id 并读取同一行。现有 native_owner_setup.main 先接已含 instance_id 的六字段record与两个同实例locator，再创建Engine；首次安装无法提前知道该行。不能增加 instance.json、由Native随机造ID、直接读SQLite，或再启动一次Python探测。

批准一个新的固定索引入口 `video_creator.cli.native_owner_setup.initialize_and_bind(*, initialization_record: bytes) -> int`，保旧 `main` 及六字段record/确认wire签名和语义兼容。新入口在同一原 indexed child 上：认证instance-independent原启动来源 → 构造一次原Engine/读取实际ID → 返回身份数据 → 收到原三字节参数的严格封套 → 在同Engine上进入唯一已有配置服务。后台提取一个私有同Engine continuation 供新旧入口调用，不能新入口回调旧main使其再创建Engine，不能可注册factory/callback或公开module/env选入口。

## 初始化来源：沿原OS设施，不增加授权体系

初始化必须在真实当前本机Owner与受保护DataDir/Control、原已索引child/宿主/资源关系下进行。沿现有 held build、WindowsAuthorityPipe/对应平台peer、PreparedLaunch/OwnedProcess、ResourcePins/Job实现，只增加不依赖instance的有限身份绑定阶段。stdio仅传事实，不自带Owner权力。

Native在launch前持有真实DataDir与祖先/Owner/DACL、Control及安装输入/独立host/receipt/payload guards，持实例启动锁；根目录未存在时，由原受控宿主只创建并核验选定根目录，然后持原目录对象，不能先让未认证Backend按任意argv创建目录。Backend在数据库写入前以原inspect_owner_directory核实际根，并用原held host/receipt与实际OS peer验证宿主；Native核原打开的child HANDLE/creation/SID/映像/Job与原PreparedLaunch，而不是后来按PID重开冒原对象。路径/locator/session/SHA仅供比对。业务principal仍由原Bundle映射（如local-user），OS SID/UID另存另核，不能混用。

Windows目录持有身份取原Win32 directory HANDLE/file information与Owner/DACL；Python st_dev/st_ino只在其自身inspect_owner_directory命名空间比对，不等同Win32 volume/file index。Backend重核前后实际目录，Native持续重核其原held对象；两端不得数值互换。macOS/Linux沿原真实UID/peer/creation/目录对象规则，尚无实现/机器证据须明确保留，不能复制Windows DTO伪称跨平台成功。

为解除locator的instance循环，批准一个严格只做bind/current的私有初始化locator，Windows家族 `\\.\pipe\VideoCreator-OwnerSetupInit-`、role=`owner-setup-initialize`。若I62已有同等级instance-independent held peer，可重用其原连接实现此闭集，不另开新认证体系；不可借普通API/MCP/Broker ready或renderer。初始化连接与后续现有installation/confirmation连接用途分开，每条只建立一次且无重连；它们属于同一个原child。初始化来源只认证这个启动/data目标，不是安装资格、管理cap、确认票据、GoalSource或制作permit。

初始化通道两向认证复用原实际peer API。宿主handler核连接来自原child HANDLE等价实际身份/creation/Owner/映像，并与原PreparedLaunch匹配；Backend核实际server peer、held受保护host/receipt、同OS Owner/目录及GUI session。原独立expected host image/hash不能由locator覆盖。原初始化connection/source持有到本child及Job后代真实终态；阶段完结仅禁用其新方法，不提前释放held资源。

## 唯一Backend ABI（私有，不进入公开SDK）

初始化参数 canonical UTF8 JSON，无换行/未知或重复字段/NaN；恰六字段：

`format="native-owner-instance-initialization-v1", installation_inputs, external_receipt_path, expected_host_image, expected_host_sha256, bootstrap_locator`。

installation_inputs/路径/sha完整沿原 NativeOwnerStartupRecord 的相同唯一typed校验，独立host与installation声明相符。bootstrap_locator恰 `pipe, session, role, server`，role固定上述值，server恰原 `pid, creation_filetime, sid, image, image_sha256`。没有instance_id/Goal/权限/预算/Owner文本/credential/argv/env/任意source。DataDir由原固定Guardian受控 `--data-dir` 传入并与其held目录核验；renderer不能提供它。Backend唯一parser/schema/error实现，Integration按冻结字节消费。

初始化pipe request恰 `wire="native-owner-instance-peer-v1", session, seq=1, method="bind"`；response恰 `wire, session, seq=1, status=200, code="bound"`。这些值仅在实际peer/原closed handler已经核实后有效。后继current重核仍走原实际peer/held guards，不以成功JSON缓存代OS源。拒绝的response用相同字段，status/code为后述闭集；无通用RPC/任意方法/确认/登记。

身份stdout帧恰 `wire="native-owner-instance-handshake-v1", event="instance_ready", seq=1, instance_id`。instance_id为原Engine真实当前metadata行；按原Backend instance grammar核验，不新建第二ID模型。Native只在原channel/原child/原目录/源仍current时消费它。采用原 uint32LE长度+canonical JSON，整帧body上限32MiB；身份body额外上限16KiB。日志仅stderr，不能混入stdout。

后继stdin封套恰 `wire="native-owner-instance-handshake-v1", event="bind_setup", seq=2, startup_record, installation_locator, confirmation_locator`；三个值均是对应原canonical JSON对象，Backend严格解析并再编码原canonical bytes交已有parser。不得接任意byte数组/任意encoding、缺字段自动补全或扩原三参数。全部完整body≤32MiB。两locator及startup.instance_id必须等原Engine实际ID；installation/receipt/独立host全部必须等初始化原值，不能借bind换资源、DataDir、Owner或已确认范围。

成功确认stdout恰 `wire="native-owner-instance-handshake-v1", event="setup_bound", seq=2, instance_id`。Backend发此帧前重核初始化source/目录/实际SQLite行，并保同Engine进入已有consumer/observer/Bundle/OwnerSetupService路径。Native收到此帧后才发送原SetupPreparationRequest一帧，保持原原始Goal/key/options及现有 prepared→accepted→goal_accepted 输出ABI；不能把bind成功当人审或Goal接受。现有request、32MiB−16KiB完整Goal边界和旧12 grammar用例不改。

错误stdout统一恰 `wire="native-owner-instance-handshake-v1", event="error", seq, code, status`，seq只允许当前1或2，不回显输入/路径/Goal/secret。代码闭集由Backend实现：`owner_instance_handshake_invalid`422、`owner_instance_handshake_limit`413、`owner_instance_source_denied`403、`owner_instance_binding_changed`409、`owner_instance_source_unavailable`503、`owner_instance_handshake_timeout`503；现有schema/migration具体错误保原code/status，不catch-all改成source拒绝或成功。错误无额外detail/message字段。真正原source错误仍可安全stderr保诊断；stdout缺失/截断由Native列待核实。

## 同Engine初始化副作用与状态

阶段为 source-bound→instance-initialized→awaiting-bind→setup-bound→既有setup；仅原child内部不可序列化状态，不新造数据库身份表或跨实例token。初始化阶段允许原DataDir数据库/SQLite WAL与迁移/原instance行；实际Database从schema3–9升级会先调用原snapshot_backup，故允许原DataDir/Backups内一致性SQLite及其原已引用不可变文件/WorkflowState快照，不能删除该备份、跳过备份或宣称没有文件读取。升级/备份任何失败保持原错误，不输出instance_ready。Engine同时创建默认空信任根的内存PersistentEvidenceRegistry（包含私有随机admin对象），不能调用其admin/admit/配置/qualification方法，不对外输出其对象。

不打开vault、不authenticate管理secret、不assemble管理/登记execution、不恢复Goal/清pending、不保存草稿/准备intent、不Worker/API/模型/媒体生成/资源Evidence/人审/计数/预算/收费。OwnerControl及外部高水位/current-floor不由此阶段改写或降低；ADR0040事实收口仅在后续原authenticated factory正常顺序实施，不混进identity成功。原schema>10拒绝；不覆盖旧迁移/降级，future实际schema上限由Backend唯一版本维护。

原Engine存一份实际身份/根关联；bind前writer外重核实际Owner/目录/source，然后用原同数据库短读核metadata.instance_id仍等原值，原根对象与DataDir必须相同。不存在/改值/换DB/换目录拒绝，不INSERT补回或重新Engine/重新生成ID。SQLite连接由现有Database按操作短开；“同Engine”不要求长SQLite事务跨人审。父启动锁及原held目录/文件关系不能由新JSONkey替代。

## 超时、EOF、崩溃与重新启动

沿原20s绑定绝对单调deadline，单次peer exchange≤10s；迁移/备份未在期限内完成不得宣称ready或盲重开，Backend不人为中止已提交事实。Native原process owner保实际child/Job、双流读者和guards到真实终态，unknown≠terminal。实现若需迁移进度，不在此版本增加动态延期或超时成功；需另行固定变更。

一次child仅一个identity回复、一个bind_setup和一个原Goal帧，乱序/重复seq/多bind/changed bytes拒绝，无同channel重发。EOF前未写DB则失败；已初始化但ID回复丢失/timeout/child崩溃，保实际SQLite与备份并报未知初始化状态，不删根、不造新instance、不自动重启/复位。后来由原宿主一次明确获准的新启动读取同一原metadata行；它不是重放Goal或批准Owner动作。instance初始化提交不计项目受理。

setup_bound后Goal响应未知沿ADR0038/0039原journal/原key/fullGoal/draft恢复，不自动发新Goal/newkey/newproject；已接受有限intent只在原真实Owner/同资源/current/recovery工厂合法时续跑。变化/损坏/expiry保pending/准确拒绝，ADR0040只收口事实权限及ADR0041新Owner用途各自独立。bootstrap身份不能补真正InstallationAuthority/qualified resources、setup-aware接受恢复或Daily执行注册来源；这些真实缺口仍需后续实现。

## 实施与独立核验

Backend仅本角色CLI/domain/application/infrastructure：固定typed parser/封闭source工厂/同Engine continuation，复用原唯一Database与已有服务；源交接必须包含新增模块全索引以及三参数旧路径兼容，不改公开Goal模型。Integration仅desktop/native launcher/held peer初始化handler/严格frame driver及indexed payload同步，先读actual ID再调用原HostState::bind_installed_setup与InstalledSetupDriver，既有UI四命令可独立source接入，不能待此握手才开始UI。前端无新增instance/locator/路径/source参数，旧早接口completed仍仅Goal受理。

Test验证新实例/现有同实例identity、schema-too-new、实际升级备份/失败、同Engine一次构造、无vault/Goal/Worker副作用；错误peer/Owner/目录/host/receipt/资源替换/DB行变更、截断/duplicate/noncanonical/乱序/超限、EOF与初始化commit前后/response lost、同Goal一次恢复。parser/故障fixtures只证明机制；真实原HANDLE/GUI/Owner/保护DataDir/同child双流终态、合法首次一Project一Run及后继新Goal必须真实运行证据，不能用假source或12旧grammar绿替代。Review独立核固定差异；Acceptance仍完整R1/R2阈值。

A43本轮只读固定普通源与写设计，未import产品/跑DB/Owner/native/UI/安装/测试/联网/凭据/模型，费用0。真实安装资格、初始化peer实现、迁移运行、三OS和完整作品均未验证。初次ADR合并输出截断已补读0039/0040；末尾rg无0042匹配exit1属编号定位，非产品失败。
