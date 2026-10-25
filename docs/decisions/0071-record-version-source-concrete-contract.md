# 0071：安装记录协议版本的真实来源

状态：APPROVED_CONTRACT_ONLY / DESIGN_ONLY。这是 0070 的私有版本选源具体化，尚未实施、独审或运行。0070、0068、0069 及历史记录原字节不变；本决策不签发资格、执行权或新增 Owner 确认。

## 1. 已核事实与唯一选择

停止输入为 Integration 的 RecordVersionSourceAbiProposal（ee152449…），Backend 的 RecordProtocolAbi（Interfaces 1f919cff… / Index bfd20c50…）和 CheckSourceAbi（de87ba56… / cc1ba0fc…）。有限完整来源见本阶段 InputPins/OrdinaryIndex。

现仓库 Profile 使用 deny_unknown_fields，未定义 record_admission_wire。PreparedLaunch 已保留实际 policy SHA、role、资源持有对象及实际启动参数。InitializationCurrent 保留实际 child/host/session/installation，尚无该 launch 选择；初始化旧消息也没有版本字段。IndexedBootstrap 只在 qualified-install 分支调用安装记录入口，但尚不传版本。Backend open_instance_source 未保存版本来源；OwnedInstallationRecordConnection 虽接受两个 wire，却只比较自己的 _wire 与 _original_wire。这些不是新功能已实现的证据。

唯一选择：版本来自实际安装中、完整哈希覆盖的 LoadPolicy.json 的 owner-setup-qualified-install profile。Native 从原 IndexedPolicy/PreparedLaunch 固定，Python 从原已认证初始化 source 持有同安装的实际 policy 字节固定；两者通过同一实际 child 和原安装记录 OS 通道闭合。入口 keyword 仅请求该版本，不是权源；安装记录的真实 Owner action、0070 root/proof、current、Registry CAS 和消费权限仍分别检查。

不在旧初始化 carrier、peer frame、record locator 或回执添加版本字段；不得以 receipt 格式、candidate 内容、Root 配置、环境变量、renderer 字段或任意 keyword 推断版本。

## 2. 唯一 policy grammar 与生产者

在现有 Profile 增加唯一私有字段 record_admission_wire，规则如下。

| profile 与字段 | 结果 |
|---|---|
| owner-setup-qualified-install，字段缺席 | held-installation-record-v1-candidate |
| 同 profile，显式字符串 held-installation-record-v1-candidate | 同一 v1 |
| 同 profile，显式字符串 held-installation-record-v2 | v2 |
| 同 profile，null、非字符串、未知字符串 | 拒绝 |
| 任何其它 profile，字段出现，包括 v1 或 null | 拒绝 |

字段缺席与 JSON null 必须区分，不能用普通 Option<String> 的默认反序列化把 null 当缺席。保留原 exact key/deny_unknown_fields、完整 policy/version/profile/executable/entry/module/producer 验证。Rust、IndexedBootstrap 和 Backend 的私有 selector 采用同一表；不得各自增加别名。

已核 IndexedLoader.install 的原实际 interpreter/builtins/frozen/FileStore/audit 源检查；它没有 record selector。Integration 在 IndexedBootstrap 进入 install/导入 Backend 之前执行本表的有限完整 profile 字段检查，原 IndexedLoader 的加载与子进程 source 保护继续执行，不能把新 selector 检查替代 install，也不能因 Backend 第二次检查便跳过 Bootstrap 检查。

Integration 唯一维护 BuildIndexedEngine.py 的 build-only --record-admission-wire 开关，闭值为表中两个完整字符串。开关缺席时不写该字段，旧 producer 默认语义仍是 v1；显式选择仅写 qualified-install profile。新 artifact 不原地修改旧 policy。新完整 LoadPolicy SHA、payload map、build receipt/provenance、Native/Engine 资源闭包和资格报告必须对应实际新 artifact。

同一 IndexedBootstrap.py 有物理 Bootstrap 和 BaseStdlib.zip 内 _video_creator_boot 两份实际构建输入，必须同源一致并都纳完整清单；不能只改其中一份。任何构建源码变更都可能改变归档/产物 SHA，即使选择 v1，也不继承旧 artifact 的资格。原完整资源、模块、工具、平台能力与旧限制不减少。

## 3. Native：在真实 launch 上固定，不从确认结果反推

Integration 在 load_policy.rs 定义私有闭合 RecordAdmissionWire 枚举，只有 LegacyV1 与 V2，对外编码仅 §2 两字符串。IndexedPolicy.prepare 是唯一 selection 工厂；为 qualified-install 的 PreparedLaunch 保留私有不可变 selection 成员，绑定实际 policy SHA、原 ResourcePins/LaunchSourceCarrier、role 及完整 profile。其它 role 没有此成员；不能由公开构造器、字符串或反序列化地图构造。

这里的 selection 是原 PreparedLaunch 的私有持有成员，不能单独当 installation/qualification/Owner approval。getter 返回原成员的只读借用或 Arc，不能返回可重新组装的授权 DTO。launch_owned 后保留同一个成员及实际 args/executable/environment；其 current 检查覆盖完整原资源与实际启动。

现 InstalledSetupDriver.launch 在 prepare_role 之前调用 prepare_record_input；需要调整这一真实 caller 的顺序，而非制造未启动 child 的事实：

1. 按原 trust_materials/qualification_candidate 的真实存在关系选择原三个 role；candidate 有而 trust 缺仍拒绝。
2. 调用原 resources.prepare_role，核 candidate.assert_target_current 的实际 source context，从该 PreparedLaunch 取得 selection。此时尚未创建 child 或授记录权限。
3. 进行原实际 trust/record UI 确认。prepare_record_input 新增私有参数 selection，必须是该实际 PreparedLaunch 成员；不能从 candidate format 选择 wire。v1 原 intent/确认字节保持；v2 仅确认 0070 定义的真实 v2 input/action，不能把旧 v1 确认升为 v2。
4. PendingInitialization.create 新增私有 launch_source 参数，保留同一 PreparedLaunch 来源。qualified-install 必须含 selection，原两个非记录 role 不含。
5. start 后的原 initialization registration 改为 register(actual_process, &started.prepared)。只接受该实际原 launch、实际 args/executable/environment、资源/selection 同源及实际 child OS identity，不能只传一个 Arc<OwnedProcess> 便认为已绑定。
6. 原真实 bind 成功后，InitializationCurrent 保留同一 selection、实际 child/host/session/installation 和启动来源；原 peer 4-key request / 5-key reply 的 exact grammar 不变。
7. PreparedRecordInput.bind(trust, initialized_source) 在原 seq3 trust commit 后核同一实际 InitializationCurrent、child、instance、installation、trust original action 和 selection，产生原 RecordAdmissionOriginal。若旧 CommittedTrustSource 尚无原 initialization accessor，Integration 在它上增加仅核原持有成员的 assert_initialization_source；不是 bool callback 或接收 JSON 的工厂。

上面的方法增量目前 NOT_IMPLEMENTED。实际 caller 是 owner_setup_runtime.rs 的 InstalledSetupDriver.launch，不能只修改孤立 struct。

RecordAdmissionOriginal 保留原 selection。BoundInstallationRecord 的请求 wire、reply wire 和 admission parser/producer 均由它决定，收到的 wire 只作 exact comparison。v1 发旧 10-field admission；v2 发 0070 的 admission-v2/root/proof，不得在本卡发明第三 admission grammar。两者复用原 locator 六键、reply 七键、seq1/method admit_record、原帧界限与 deadline；outer seq4/5 record-handshake-v1 和 seq6 production-carry-v1 也不变。v2 资格尚缺时明确不可用，不降级发 v1。

## 4. Bootstrap 与 Backend：请求值不是可信 pin

唯一入口增量为：

`initialize_bind_admit_trust_and_record(*, initialization_record: bytes, record_wire: str = 'held-installation-record-v1-candidate') -> int`

IndexedBootstrap 在原隔离启动、完整 policy SHA、实际 interpreter/entry、NativeSourceContext 和 carrier 校验后，按 §2 从其实际 qualified-install profile 取值，明确传给该入口。其它两个 owner-setup 分支和原 API/Worker/MCP 路径不传、不获得 record 能力。Bootstrap 不从 initialization JSON、环境或新 CLI 参数取得运行时版本。

Backend 内部 _initialize_bind_and_admit_trust_state 新增 record_wire=None，现 trust-only caller 保持 None；record entry 明确传闭值。open_instance_source(record, data_dir, *, deadline, record_wire=None) 是对应私有工厂增量。None 仅表示原非记录初始化没有 record pin；不是 qualified-install profile 缺席字段的含义。记录入口的缺省字符串仍须经过真实 source 检查，不能默认授权。

_NativeInstanceSource 的 _open 必须完成现有实际 Owner directory、受保护 host/external receipt、pipe 双向 OS peer、PID+creation/image/SID/session、deadline/current 验证。要求版本时，再持有该原安装 payload_root/LoadPolicy.json 的实际只读文件对象，拒 link/junction、异 Owner/异安装，核它在原完整 expected_files 中唯一的 SHA/完整长度/文件身份，并核原外部 build receipt 与完整 payload map/实际 Native launch 的关系。不得把 initialization 的 expected_files 地图自身当证明；原 Native 持有输入、实际 host/receipt、保护 carrier 和同 child OS 联系必须成立。仅凭文件能读、配置 SHA 相同或普通 bytes 不形成 pin。

Backend 用该实际 policy 字节按 §2 解析唯一 qualified-install profile，核固定 entry 是 video_creator.cli.native_owner_setup、command=None、同实际 interpreter/profile/安装闭包；requested record_wire 必须等于实际选值。缺完整源关联或 protected reader 属 NOT_IMPLEMENTED/NOT_READY，不自造强 source。这个校验可复用现有受保护文件 primitive，必要的私有 reader 归 Backend；本决策不声明旧 image reader 已适合 policy 用途。

成功后，仅在原 _NativeInstanceSource 内保存私有只读 pin 与实际 held policy handle、policy SHA/文件身份/完整 profile、同 child/host/receipt/GUI session 关联。原 seq2 retain_engine/complete_setup_binding 再将它关联到唯一原 Engine/database/instance；pin 不能由调用者 setter、可解析 dict 或普通 Python keyword 设置。没有 record pin 的实际 trust-only source 继续可用，构造安装记录 connection 则拒绝。

Backend 新增唯一私有消费方法：

`source.assert_record_wire_current(engine, wire, *, local_connection=None) -> None`

outside-writer 模式做原 actual-source/current、held policy/文件/安装链与同 Engine/instance 校验；local_connection 模式只做原 held/local/相同连接 instance/失效状态与不可变 pin 校验，不在短 writer 内打开 policy、重连、做网络或替代原外部检查。模式不可由 public request 改写；None 或任意 EngineError 不能被当 True。原 qualification/rights 两 authority 和各原 current 检查仍分别执行。

OwnedInstallationRecordConnection 构造在打开记录 transport 之前调用该方法，要求 requested wire == source 的实际 pin；对自己的 _wire/_original_wire 比较仍可保留，但不能充当此来源校验。原实际记录 pipe 的 server/child peer 校验、Native RecordAdmissionOriginal 的实际 launch selection 和第一份 exact reply 再闭合 Native→Python 一致性。改变 pin 不可补发请求；不得按收到的 reply 重选 parser、探测两版本或创建第二 action。

Native 的真实初始化/record producer 与 Python 同安装 protected policy 是两个必要接点；只做其中一个不足以通过独测。keyword 保留仅为本次请求 discriminator，不是新 issuer、public DTO 或管理 binding。

## 5. 当前性、旧字节、失败和生命周期

版本绑定贯穿原 source/connection/短 writer/commit/current 读取，不能在 record 已接受后换 profile、child、Engine、instance、Owner、receipt、policy 或 selected version。现有 current 检查增加实际 held policy 的身份/哈希/失效覆盖；短 writer 仅核预先持有对象与相同事务的原行。检查失败回滚原事务，不输出安装成功、不产生新预算或执行注册。

| 情况 | 必要处理 |
|---|---|
| policy null/错类型/未知值/错 profile、非法请求 wire | 原闭合 grammar 拒绝；安装记录路径映射 frame_invalid 422 |
| 没有真实 source/原 peer/Owner/同 child 能力 | 原 source_denied 403；不能靠 keyword 补齐 |
| 实际 pin 与 requested wire、policy、child、Engine/instance/current 变化 | 原 changed 409；不能 fallback |
| 原 source 尚缺真实实现、资格缺失或 deadline | 按原 unavailable/timeout 503，明确具体缺件；不能降级或报告成功 |
| commit 结果未知 | 原 unknown/reconciliation 语义，保同 action/key/事实；不重连重做确认或制造新 action |

selector 自身不改变 v1 admission/request/receipt、初始化与 setup carrier 的原 canonical bytes，不为旧历史回填该字段。旧产物在未出现字段的 qualified-install profile 上继续选 v1；这并不取消旧资格/current/Owner 门。v2 是明确新 artifact 的版本请求，不能复活被撤销 grant、把旧 root/proof 升版本或挪用历史 H 当当前 C。

PreparedLaunch、InitializationCurrent、record original、Python source 和 policy 持有对象继续保留到原实际 child 退出及真实 Job 后代终态。pipe EOF/thread结束/窗口关闭不证明这些资源终态。disable/实际 peer 或文件失效立即使 pin 不可消费，保原 held 对象直到既有真实清理条件；冷重启必须重新取得原真实来源，序列化 pin 不是恢复 capability。现非 Windows 等价实现和各真实机器验证仍独立未完成，不由本卡降低三 OS 范围。

## 6. 后继 owner 与独立验证

Integration：唯一负责 Profile strict parser/enum、IndexedPolicy/PreparedLaunch 原持有成员、InstalledSetupDriver 顺序、PendingInitialization 真实注册、InitializationCurrent、原 trust/record original 的同源接点、两处 Bootstrap 副本、BuildIndexedEngine 开关及新 artifact 完整 producer/版权/资源清单。不得代独立 producer 签发报告。

Backend：唯一负责 Python 入口/私有 helper/factory 的上述 signatures、实际 protected policy reader/source pin、OwnedInstallationRecordConnection 来源与 current/local 校验，以及原 v1/v2 grammar/consumer/事务映射。领域/API/SDK 公共契约本卡不新增。

Test：先固定来源和 case/oracle，再独立跑合法旧缺字段 v1、显式 v1、新明确 v2 的完整同 child 路径；三者均须真实资格/Owner/current 门。比较旧请求与旧 receipt 原字节。负向覆盖 null/布尔/未知/错 profile、keyword-only、trust-only source、相同 SHA 却不同 held source、异 policy/child/Engine/instance、初始化前版本替换、启动后参数改动、两个 Bootstrap 副本不一致、构造 source setter、connection/parser 降级、seq/reply篡改、deadline/EOF/失效、短 writer 变化与 unknown commit 不重放。不得用测试专用 bool 或 fixture 签名当生产资格。

独立 Review 核 source→caller 的完整接线、closed grammar/absence-null、真实文件和 OS 同 child 闭包、兼容字节及 writer/lifetime；Acceptance 仍验真实可安装产品及四平台完整目标。0071 不是其结果；19 原三失败、31/105、三 binding、CNY20 和其它原限次/失败全部保留，不授第四次或任何本轮运行。
