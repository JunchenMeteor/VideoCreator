# ADR0064：分批资源恢复中的历史完成事实与当前认证

状态：DESIGN_ONLY_READY_FOR_INDEPENDENT_REVIEW。只修正固定 DRC-P01 的合同冲突；不是独评批准、实现、安装资格或运行验收。ADR0063 的 28230B、SHA `62b0d2e751c5698fa61a3acf26a9bc89d4a6d4f33026b9f2413f9e1a97fe6d98` 保持。0060—0062、原失败、额度、unknown、200000us/两 authority 和完整 R1 独验后连续 R2 均保持。后续媒体归因任务不属于本卡。

## 1. 固定反例与最小决定

DRC-P01 SHA `fd18d3e9e42b57d5502e12d577c09192b6c25732246e7b8a91c3910f60b8b126`、正式独评 SHA `87c264013c7c050caefd61e3b3d1adbe97ef84ca5de9e6d5465365e9ad2582d2` 已全文核。原53普通件索引 SHA `5fd80570338e760c0a1da8ec4909a3b929faea0e7ad56416c3be583ef202defc`。必要实际消费者为其 Ordinary 中：

| 固定普通源 | SHA / 本轮实际方法范围 |
| --- | --- |
| 12-backend-application-diagnostic_resume.py.py | `fdbc5385ecd866d1502e6396f774ee133c90a0d18ca05009295b24894304e9e9`；37—224 |
| 13-backend-application-diagnostic_selection.py.py | `4de38cab02bae5bafccbf37f3db6547abfe5708d792c073b6052f0dae2192078`；48—156 |
| 14-backend-domain-diagnostic_recovery.py.py | `af1c2532538104597ebfc2cbbff887e90b24f044fe7824fd7d0ce2f0dae0b9c0`；1—200 |
| 18-backend-application-component_diagnosis_service.py.py | `a2747f788f03cb5d207685d7b56d400b6856fbb36814c1b91726dd916af2bd15`；273—373 |

原 resume119/147—151 累加完整 completion ref；178—182、selection76 和136—156读全部 ref。原 stable/envelope V2 没有资源版本关联。安装 R2 的 a2 因 record/action/revision 不同，不能等于已在 R1 消费的 a1。不能把 a1 传给只读当前集合的0063端口，也不能删 a1、覆盖旧输入或把 a2 当作同一原事件。

唯一决定：**stable 的 a1 是原已提交历史输入；消费它时，由原同一 issuer 读取其真实不可变提交闭包，并用当前有效 a2 单独证明同一实际资源方法现在可用。返回仍是 a1 的原 bytes；a2 只成为当前 held 认证和 writer captures，不成为盐化输入的替换项。** 真正首次完成的 B 才沿原 v2 累加一次。无需新 issuer、通道、资格表、诊断 input grammar、public DTO 或授权政策。

## 2. 两种事实及允许关联的精确边界

历史提交证明 H 与当前资格证明 C 必须同时成立，二者不是同一安装事件。

H：原 Engine 的 immutable completion 行、其完整0063集合、原 qualification record 原 bytes/signature、records/events/commands 及当时被 publisher 核验的实际资源报告来源必须相互对应；completion ref 的 record_id/size/SHA、action/request/revision、报告 ref、catalog/method 全一致。历史 source 只能从原 trusted reader 获取，不能从 caller body、sidecar、旧 observation 或父任务推导。原注册 input 确实声明该 ref，且该 input 是此 Run、同 preparation/intent、当前 journal/selected/source 链的真实原件。未被原 input 消费的新 ref 不走历史豁免。

C：0063 原 current observe/read 返回当前真实 committed completion，而非 absence；原 Registry/current source、原 peer/session/child、完整材料、安装 target、真实报告覆盖/许可/权利、有效期、floor/revoke 与完整方法 guard 均真通过。该 C 只来自当前 event；不能向 native reader 请求历史 a1 来跳过 exact current-ref 检查。

关联相等项为：同 instance、原 ProductionBinding 的 registration/resource/runtime 三 SHA、完整 diagnostic catalog SHA、完整 method_ref（含 route/model/source/check_kinds/rule SHA）、full_file_map_sha256、engine_partition_sha256、完整 target。H 与 C 每件均须其签名 record/实际报告的覆盖关系有效，不能只比 method_id、route_id 或模型名。原 Owner/current/request/fence、制作及版权许可另在原 guard 校验，不从资源关联授予。

允许不相等项仅为两次真实安装提交身份、其 record/action/request/revision/floor、当时/当前 validity，及在同上述资源身份上的**独立真实报告 ref 与报告来源闭包**。不同报告是两个不同事实，不能宣称同一报告或同一 action；C 必须按0063完整实际检查准入。旧报告只证明当时 H 来源，当前执行只用 C。若资源、完整 route、catalog、target 或完整 map 真变化，即使名字相同也不关联，沿原 binding/source changed409；本卡不授迁移权限。

历史报告/record在真实原 admission 时须有效，之后自然过期不改写历史；当前报告/record必须在此刻有效。原真实撤销/拒绝来源若否定 trust、报告真实性、资源/source、许可或当前执行权，仍拒绝，不能用新 ref 映射消除该拒绝。合法 Owner `replace` 导致原 record/session 被 supersede、epoch/floor前进，本身不等于历史 bytes 被撤回；仅在原真实 replace 事件链和当前 C 均被核实后允许读取 H。不得自造 revocation reason、豁免标记或新的报告撤销体系。

## 3. 原 publisher 保留与原 reader 的来源闭包

0063 的 completion body/set、v2 committed evidence 与 wire 格式原样保持。历史集合和完成行原事务已经要求保留；现增加最小必要的**原资源报告 bytes 的不可变保留**，防止 replace 释放旧文件后只能猜报告正文：

- `NativeInstallationRecordConsumer.admit_record/replace_record` 在0063原外部 prepare时，读取原材料 purpose=`qualification_report` 的确切 bytes，完成原报告覆盖及资格验证。Prepared member 同时持有本次派生 completion 所实际用的原报告 bytes/ref与原签名 record、当时时间/captures；不是 API 任意 archive 参数。
- 在0063同短 transaction，仅将这些原已核资源报告 bytes insert-or-exact-match 到原 metadata，key=`diagnostic-resource-report.`+完整 QualificationRef 的 canonical SHA；保原三字段 ref、严格 size/SHA 和用途。值是原 bytes 的 UTF-8 文本，不能重排、改 format、删字段或追加 record SHA。同 key 不同 bytes409并整事务回滚。报告与 signed record/ref 的来源关系通过原 records/event/command/set核，不让 archive 自己成为准入来源。
- 不复制全环境、密钥、安装文件或所有历史材料；不建新表/issuer/资格账本。旧 record 原 body/signature、实际 event/command 已有原存储，仍用其原格式。当前原报告全依赖/许可/检查覆盖由原材料 verifier核；历史 archive不能替代 C 的任何实际报告或授权。
- 读取 H 时，从原 metadata/records/events/commands 精确读取 completion、集合、报告及其源 record，核完整 body/ref、canonical、关联、原 accepted/event 时刻与当时 validity，核原 trusted signature/anchor来源及真实提交链；全部来源验证/crypto在短 writer之外。单条 completion行、一个 archive 或签名有效分别都不够。
- 原完整真实更换链只允许同 instance/trust来源下原真实 record_admit→有限 replace事件及其前后 expected/current revision 关系；每层 source都来自原 committed records/commands，与现在的 current一致。不是 caller 给一个 old_revision。每层真实 revision严格减一，最多读取当前与H的实际 revision差这么多层，终止于H的原event；循环/缺层/不单调422或明确unknown，不能截断称完整。沿原probe已有30秒有效期，预读开始就起同一个30秒deadline，外部验证与后续writer共用它；超时503且没有positive/queue，不延时或在writer重开遍历。正常单次/有限多次更换必须完整核实，限时不是另建资格政策或时间盐。

兼容：未实施该保留的历史记录，不从文件名/manifest回填 H。若旧报告目前仍在**原受保护且原已声明的材料 index**中，可用原 `read_required_ref` 取得并验证同 bytes，读前后原 current；可以按原受控 publisher 准入后保存，不能将 reader偷写 archive 当成功。都没有则 `diagnostic_resource_history_unavailable`503，保 journal/Operation；由原 Owner真实安装更换的材料来源补齐，不能伪造旧报告或重分析来弥补。没有历史证据缺口的正常新安装路径须由上述 publisher一次保留完整 H，不以长期503代替实现。

## 4. 一个唯一 held 认证端口，不新增 wire

Backend在原 `NativeInstallationAuthority`/`NativeQualifiedInstallationIssuer`的具体绑定中维护唯一私有方法：

```text
reauthenticate_diagnostic_resource_completion(*,
    evidence: InstalledProductionEvidence,
    current: HeldDiagnosticResourceObservation,
    historical_ref: DiagnosticMetadataRef,
    registered_input_ref: RegisteredDiagnosticInputRef,
    binding: ProductionBinding,
    preparation_id: Identifier,
    preparation_intent_sha256: Sha256)
    -> HeldDiagnosticResourceReauthentication
```

这些 ref/binding 参数是检索条件，不是权限。该方法只能由原同 Engine/Bundle 的 resume/diagnostic service，以原 trusted source/input reader 已实际读取并捕获的上下文调用；内部必须复核其真实同 Run/preparation/input/selected/source 关联。不能仅凭 caller JSON 调用成功，不对 public API/MCP、renderer、任意 provider 暴露。返回 frozen/eq=False/不可序列化成员，由原 issuer 注册；同值构造、拷贝 DTO/随机ID均无效。

成员最小内容：原 issuer/connection/Engine/Bundle/member epoch/thread/有效期，原同 Run/preparation/intent及 registered_input_ref，H 的完整 ref/原 bytes/提交闭包与 SQL captures，C 的原 current observation/完整 current ref/原 bytes/报告与当前资格 binding，已验证的完整资源相等项。只对同一真实原资格 observation创建；当前证据来自0063四sole端口，成员不新建 native session 或观察权限。H=C 时仍核所有声明/captures，可复用当前原 exact reader，不能认两个同hash但不属于 input 的 ref。

读取旧completion正文沿原 `read_diagnostic_completion(lease,inputs,completion)` 和 `_diagnostic_completion_bytes_no_lease`，使用该成员的 H bytes；每次均保 H 的 size/SHA及 input membership，前后原 input/source/current断言。当前执行资格用成员的 C，而不是 H 的旧 observation、旧 floor或旧 grant。原资源 writer assertion需绑定 C 与其 original native lease；它再核 H/captures/注册 input/完整更换链和原current行。lease active时只缓存/本地断言，不临时 pipe/crypto；外部认证在原 native begin/SQL writer之前。

Integration无需新 wire：0063 v3 `observe_diagnostic_resource/read_diagnostic_resource`仍仅服务当前 exact ref a2，不接受 historical_ref或 Backend 提供历史正文；原 protected peer/session/Registry/current source全部保留。Backend从该真实 current端口取得 C；原 trusted SQL/material reader取得 H，在同原 issuer内组合。Native任何返回的 a2都不得冒 a1正文。

## 5. stable successor、去重与费用

原 `DiagnosticStableInputV2`、`RegisteredDiagnosticEnvelopeV2`、`DiagnosticResumeContext`、`CurrentFinalDiagnosticSourceV1/V2`及旧 bytes均不变。新 held成员/captures不写进 stable、不写入模型参数的权源，不加时钟、Registryrevision、当前 a2 或新的pair DTO来盐化 key。canonical仍原递归 sorted/compact/UTF-8编码，原 Goal/hash不改。

原 v2中每个 qualified_resource ref始终保存原完整历史指向。probe必须为**全部**旧资源 ref读取 H，并为每个完整方法找到唯一当前 C，形成该次 held成员闭集；不能只查询尚未消费的 B来跳过 A。不同旧 ref可关联同一当前 C，但每个 H 均须其实际原来源/声明，catalog仍最多16 methods，不放大原 frame/input/材料上限。

判断“旧方法已消费”不用 a2==a1，也不用 method_id；对全部 H 与完整 current C 采用§2相等项和同原 stable/input消费者事实。若已经有该真实完整资源身份的已消费 H，则 C只是认证，不追加 a2。即使 current record/报告 ref更新，单纯资格重新认证不构成信息补充，不生成新 input/Operation/费用。

真正请求 `diagnostic_method_not_ready`且原 stable没有该完整资源方法已消费 H，当前 C证明首次资源完成时，将 C原 exact ref按原 qualified_resource union追加一次。同准备源的 READY/feedback按原规则添加；排序/去重仍按完整 completion canonical SHA。a1保持，b2新增；无a2盐化项。复查/重启同 C不得产生另一个 b2或新key。若新材料/feedback改变真实创作输入，仍走其原严格变化路线；不会由本关联吞掉这些真实信息。

该规则不修改已有 analysis-intent算法或合法 changed-input限次：纯重新认证没有新的 analysis；真正 B补齐后是原同 Run的一次实际 changed-input分析，仍须原 Operation-before-side-effect、真实授权和剩余共享预算。原已 settled的旧 Operation不得再派发/再扣费；同 successor input/key已有 RESULT/Operation时只复用原已提交事实，pending/unknown只原 reconciliation，不重交。不得为保 no-fee而谎称旧 A分析已经包含当时未就绪的 B，亦不得用新Run/动作key重置预算。原 settled分析是否能跨**真实不同输入**复用仍受其原完整输入/结果关联，不能在本卡创设跨输入结果授权。

## 6. 三条实际 caller 顺序和同事务 CAS

1. 原 `DiagnosticResumeRuntime.probe_current_diagnostic_resume`37—76先读真实waiting/journal/selected/input/preparation/source并结束reader，核所有原input和H的出处。原registered binding与完整strict held catalog确定方法；原同current源外部observe/read C及 H报告/签名验证，登记全部old-ref reauthentication与新 B observations。原77—78 guard提前的当前流程必须按0063的预读顺序接线；不在active native lease或SQL reader/writer加外部操作。
2. 原 guard、原 current request/scope/Owner/licensing 与held当前资格重核；若无真实新信息，仅返回still_blocked且不提交新key。不能因为历史认证成功直接queue。真正 B等变化才构造原 old_completions+new stable、原 key/原 intents及probe；181—182缓存全部H的原 bytes和当前成员/captures，不再用原当前 exact resource reader直接读a1。
3. 原 `commit_diagnostic_probe_writer`203—224在原 Runtime resume短writer中，和原 journal/selected/current/preparation/source、H记录/原来源行、C current set/body/event/command/record及原qualified lease/floorcaptures逐项重核；先后均核。原 registered input/source只insert-or-exact-match，不覆盖。原queue/新fence及续步context与这些原 CAS是同事务；任何current/Owner/revocation/输入漂移整事务 rollback409/403，不留下半个新source或queued。writer不运行文件/pipe/crypto。原unknown Operation检查先于queue，仍needs_reconciliation。
4. 原claim新fence后，`DiagnosticSelectionService._prepare_diagnostic_resumed_input`106—134从实际原committed source/context/input读取；它不能复用上一线程/旧session的reauth member。claim阶段在其原SQL/nativestart之前，用同端口重新构造全部old-ref的 H+C；预读current外部来源先于 `_diagnostic_v2_inputs`73—98 reader。原V1基底比较、intents/字节一致、resumecontext/input全等不变，H+C captures纳 `_diagnostic_resumed_captures`。
5. `ComponentDiagnosisService.prepare_component_diagnosis`311—349在原320 guard/321writer之前完成reauth，短writer纳其成员/捕获与原source snapshots。`_diagnostic_inputs_current`351—373纳 H+C当前和原lease/fence/member；`read_diagnostic_completion`136—156仍前后两次核，再返回exact H bytes。模型只看真实输入正文，不能构造认证成员、current grant或扩大版权。
6. record后park前失败、ACK丢失或重启仍沿0060—0062原唯一 Fact/selected/journal/source writers与 immutable409重读。同输入H原bytes没变；current C可以在新session重新核，不能重写旧Fact以换认证。已unknown不queue/收费，不clear pointer。最终 publication继续原完整verify、真实precision/authority/current等全部门；此任务无新READY分支或第二wholeverify。

认证成员是瞬时当前证明；历史原件永久保留于原实例账本，重启由真实original source重建，不把一个序列化映射当grant。旧Runtime/Bundle并发reader若currentepoch变化，必须失败并重取真实proof；不在writer内部自动“升级”到新current。

## 7. 正常路径及有限失败语义

正常实例：R1当前报告准入A→a1原提交/input/分析成功并settled→同Run真实waiting B；Owner沿0063真实replace、同完整payload/catalog/method/target且R2真实报告覆盖A/B→Registry/floor安装完成→旧session关闭、新真实startup重建原scope。probe验证历史a1＋当前a2并首次b2；stable=a1+b2，a2只在captures；原短writer CAS queue/newfence；claim再核a1→a2及b2；原changed-input一次续步/复用结果；最终完整验证。全程a1/旧input/journal/Operation原字节不变，同Production预算/限次，没有安装revision单独导致的费用。

| 实际条件 | 唯一结果 |
| --- | --- |
| a1仍当前exact ref | 原exact读＋input membership/current，H=C；不新增ref或费用 |
| a1→a2仅合法replace/报告更新，完整资源身份相同，H及当前C真通过 | 允许历史读取与当前认证；a1不改，a2不盐化key |
| 旧报告/record在原admission时有效、现在自然过期；新C报告/record实际有效 | H仍是历史，当前仅用C；不宣旧报告当前有效 |
| 旧报告未被新record引用，但H原archive及签名/提交链真存在，当前另一个有效C完整覆盖同资源 | 仅以新C执行，H可读历史；移除旧ref不是伪absence，不能绕显式撤销/权利拒绝 |
| 当前A无positive、报告过期/移除后无合法替代、actualrevoke/许可或scope拒绝 | absence仅依0063完整集合认证；无C不返回可执行reauth；保持waiting或原403/409原因，不queue/收费；由真正Owner/原材料准入来源更新，非手填proof |
| 旧H报告/签名/提交链未持久或没有真正来源 | history_unavailable503或明确unknown；不猜旧报告、不重分析“补证”，原Owner材料恢复路径保留 |
| H原admission时报告已过期、签名/来源或scope不成立 | 历史无效403/422；现在的C不洗掉旧伪事实，保原件等待调查 |
| current pending/busy/通信未知或替换链缺层 | 原not-ready/unknown，绝不认证absence，不queue/新key/重收费 |
| H/body/source/SHA破损、同key不同bytes或原选择行/CAS改变 | 原422/409；不是null/无事发生，不覆盖原行 |
| 新payload/route/catalog/map/target、不同instance/Owner/current授权不符 | 原403/409；本卡不授迁移或新namespace/Run |
| 已有successor RESULT、同input settled、unknown Operation | 分别原事实复用/0重复派发、原needs_reconciliation；不以资源变化洗unknown |

新私有错误仅`diagnostic_resource_history_unavailable`503、`diagnostic_resource_history_invalid`422、`diagnostic_resource_reauthentication_denied`403、`diagnostic_resource_reauthentication_changed`409；保原具体下层异常，不把泛EngineError吃成still_blocked/absence。已存在原错误能精确表达时复用原code，不新增publicDTO。

## 8. 原角色实施与独立证据

Backend唯一维护 archive行/原publisher增量、唯一私有方法及held类型、H与C verifier/current/captures和三consumer接线；准确路径为 domain/diagnostic_recovery.py、application/installation_record_consumer.py、native_installation.py、native_qualified_issuer.py、diagnostic_resume.py、diagnostic_selection.py、component_diagnosis_service.py及原infrastructure/native_qualification_trust.py受控签名/材料reader。复用原metadata和安装四表，不改公开契约/旧grammar/全局canonical。必要旧archive材料恢复也只原真实publisher，不reader偷写。

Integration实施0063原Owner replace/current.Registry/材料保留、samewire原资源读及生命周期；正确保留历史资源报告的原purpose/ref材料闭包，不能installer manifest/sidecar制造positive。无新增历史wire、第二qualified通道或renderer票据。Media继续原completion getter消费exact原bytes，实际方法/operation/current均原接口；不自行映射refs/制造新权限。Test维护独立真实case、Review审设计/源，Acceptance独验；本Architecture不代写或执行。

独立后继必须覆盖：上述完整A后B正常同Run路径及两个以上replace；原a1/旧input/journal/Operation/费用bytes不变；仅资格变化0queue/0analysis/0fee、新B仅一个successor及原budget；历史报告过期/更新/移除与显式source撤销的区分；缺archive不伪造；同名不同fullroute/map拒绝；所有旧ref都读而非跳A；probe→writer/claim之间current替换、Owner/revoke/floor/expiry变化rollback；claim新thread/member重建；DBcommit/ACK未知复用原action/记录；sameinput409及unknown不重交；publication两authority/precision/completeverify不削。静态合同支持不等于这些真实SQL/OS/资源或作品已通过。

完整报告、许可、原Owner确认载体、原平台和实际资源资格尚须各原角色证明。R1本地免产品注册/BYOK与完整五步/API/MCP自动制作、Windows x64、macOS arm64/x64、Linux x64和后续全部R2不缩。当前真实资格NOT_READY不得被历史archive、当前签名或本合同文档当作通过。
