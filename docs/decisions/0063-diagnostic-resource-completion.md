# ADR0063：诊断资源完成事实、原持有读取与可信缺席

状态：DESIGN_ONLY_READY_FOR_INDEPENDENT_REVIEW。本文件仅裁定可实现的私有合同，须独立评审后由原角色实施；不授予安装、原生通道、SQL、模型或媒体运行资格，不关闭实现 finding。原 ADR0060、0061、0062 原字节不变，完整 R1 独验后连续 R2。

## 1. 已核事实与唯一决定

固定 Mapping.md SHA `5c39b550871f3755c906cbfaf2e624885c62e7b5b0c65a1a50a5533cf6c976a7`、Mapping.json SHA `0c9fbe931978dcb7c7c86b5726695d72ed51a8d291a53d19ef74d4214315575a`。JSON 全部合同字段、methods 0–33、before/after 各42及其余末字段分段完整读取；不能据 Mapping 的结论代替原源码核对。

Backend130 原 `NativeInstallationRecordConsumer.admit_record` 已有真实 record、event、current、command 同事务提交，其后才导出 committed evidence、安装 snapshot、完成 floor。该路径只支持初次 `record_admit`，明确拒绝已有 record 或 Owner 状态。Native `CommittedQualificationSource` 对原 action 与真实 committed evidence、完整 target/source 重核，`QualificationRegistry.install_committed` 才将该 source 置为 current。它们目前没有诊断资源专属报告语法、完成事实提交、正文读取和认证缺席。`replace` 历史数据字段不等于已有更换 caller。

唯一决定：**复用同一 qualification record、原已准 issuer/材料、原安装准入 writer 和原 Registry。只有在该 record 的真实资源专属报告已验证，且原准入事务同时提交其完成事实后，该 current Registry 才可提供完成 body/ref。** 不新建资源 issuer、资格数据库、通用 observer 插件或第二套授权。安装成功但缺该报告不产生 positive completion。不能把安装 sidecar、清单、签名校验成功、字段 `passed` 或客户端声明分别当作实际资源通过。

资源完成只证明该注册诊断方法的资源已按原资格条件准入且目前仍受原持有守卫保护。它不证明某作品质量、独立听审、200ms 精度、生成许可或一次诊断 Operation 已完成；所有原生产权限、账本、预算/限次、完整验证和两次 authority 门保留。

## 2. 使用原 qualification_report 的有限资源分支

Backend 唯一维护私有严格模型 `DiagnosticResourceReadinessReportV1`；仍使用原材料目的 `qualification_report`，必须被同一签名 record 的 `runtime_report_refs` 明确引用。普通历史报告继续其原语法，不能按 filename 或有某个布尔字段识别为资源报告。新的精确 `format` 才分派此分支，未知版本保持未就绪，损坏已声明版本报422。

| 完整字段 | 精确来源和约束 |
| --- | --- |
| `format` | `diagnostic-resource-readiness-report-v1` |
| `registration_sha256`、`resource_manifest_sha256`、`runtime_manifest_sha256` | 原安装三身份，与当前 record、原 launch、原 ProductionBinding 全等 |
| `diagnostic_catalog_sha256` | 原 resource manifest 内 `production_drivers.diagnosis` 完整严格对象的 canonical SHA，不是 URL、整个安装 sidecar 或可选 selector |
| `method_ref` | 完整原 `ComponentDiagnosticMethodRefV1`：method_id/version/implementation_source_refs/rule_template_sha256/完整 CapabilityRoute/model_binding/check_kinds及resource/runtime SHA；与 catalog 对应条目加两SHA逐字段相等 |
| `full_file_map_sha256`、`engine_partition_sha256`、`target` | 原 record 的完整 map、partition 与 QualificationTarget；不以 method 局部地图删掉四 profile/147+24依赖 |
| `qualification_suite_ref`、`independent_review_ref`、`independent_acceptance_ref` | 同 record 原三 ref，均需原材料闭包、实际用途和真正对应的独立通过证据；不是本 ADR、模型输出或自生成报告 |
| `check_report_refs` | 非空、distinct、按 QualificationRef 三元组排序；均在 record.runtime_report_refs 和原材料 index 中，目的 qualification_report，排除本报告自引用 |
| `passed_check_ids` | 非空 distinct/sorted 的真实 suite case ID；必须确实覆盖该完整 method 的实际资源装载、实际有界诊断调用及结果消费、完整 route/source 绑定、current/失效保护；Test维护实际 case/原报告，Review/Acceptance原职责核证。不凭名称存在或此数组声明判通过 |
| `valid_from_us`、`expires_at_us` | 严格正整数微秒半开区间，包含实际检查发生时刻；最终有效期取报告与 qualification record 的交集，空交集拒绝 |

报告不包含 qualification record SHA/ref、commit action 或完成 body SHA，避免“record引用报告→报告引用record”自哈希循环。原 signed record 对本报告 ref、完整 suite/Review/Acceptance/许可/构建闭包作承诺；原独立验收来源必须实际覆盖上述 method/target/source/check refs，验证代码必须检查这种覆盖，不将签名或材料齐备当成功运行。当前材料没有此真实覆盖证明，因此当前 positive eligibility **NOT_READY**。这是原 qualification verification 的必要资源语法分支，非新算法验收标准或新的信任机构。

同一 record 同一 catalog+完整method最多一个有效资源报告；重复完全相同 ref 可规范化一次，不同报告冲突409。诊断 catalog 最多原16 methods。报告 bytes 每件上限2MiB，原 qualification material index/总大小、record1MiB、evidence4MiB和原 frame限制全部保持；不截断或放大限制求成功。

## 3. 完成 body、原子事实集合与版本

Backend 私有 `DiagnosticResourceCompletionBodyV1` 的精确完整字段如下。严格 extra-forbid，整数拒bool，SHA小写64hex，无NaN/duplicate keys；沿原 `installation_qualification.canonical_bytes`（递归模型转JSON、sort_keys、compact、UTF-8、allow_nan=False），不修改 engine.canonical 或原 Goal SHA。

| 字段 | 值/来源 |
| --- | --- |
| `format` | `diagnostic-resource-completion-v1` |
| `instance_id` | 原 instance，不跨实例导入授资格 |
| `registration_sha256`、`resource_manifest_sha256`、`runtime_manifest_sha256`、`diagnostic_catalog_sha256`、`method_ref` | §2 已验证的原报告与原 catalog；保持完整 route 和源码 refs |
| `qualification_record_ref` | 真正同事务准入的完整 signed record 的 QualificationRef |
| `installation_action_ref` | 原 event.action_id / event.registry_revision / 原 PersistedRecordReceipt canonical SHA 三元组 |
| `installation_request_sha256` | 原 InstallationActionRequest 的 canonical SHA，不是完成 body SHA |
| `registry_revision`、`revocation_floor` | 原准入 reserved revision；发布时 floor完成且无pending。不是另建资源计数或时间戳 |
| `resource_report_ref` | §2 的实际原材料 QualificationRef |
| `valid_from_us`、`expires_at_us` | §2交集，不超原record validity；无“永久ready” |

完成 body 不含自身 record_id/content SHA、observation/session ID、Run、费用或 `approved=True`。`DiagnosticMetadataRef` 保原三字段：`record_id='diagnostic-resource-completion.'+SHA(body)`、`content_sha256=SHA(body)`、`size=len(body)`，1..2MiB。该 ref 指原 Engine immutable metadata completion行，不是文件路径。

同原安装准入事务还保存一个严格 `DiagnosticResourceCompletionSetV1`：format=`diagnostic-resource-completion-set-v1`、instance_id、qualification_record_ref、installation_action_ref、installation_request_sha256、registry_revision、diagnostic_catalog_sha256、`entries`（0..16个完整 completion ref+body，按完整 method canonical SHA排序且唯一）。metadata key=`diagnostic-resource-completion-set.`+原 action_id；完成行分别用其 ref.record_id。集合必须是从**完整原 catalog和该 record全部明确资源报告**验证后派生的完备集合，零项也必须真实提交，不能把未运行派生或部分导出当空集。没有该集合的历史记录为 legacy-unobserved；不会自动回填资格事实。

私有 committed evidence 增加精确新版本 `installation-committed-evidence-v2-diagnostic-v1`：保原顶层 format/instance_id/registry_revision/trust_commit/record_commit语义，只新增必填 `diagnostic_resource_completion_set`，取上述同事务集合和实际行。原 v1 全 bytes/schema 保留；record/签名/安装 ActionRequest 不改。v2只允许有真实 record_commit及同event集合。export必须从原SQL事件/command/record/current及集合/完成行读取并完整交叉核对，不能从 manifest 或安装计划现场生成一个“完成”集合。

Native也从原 retained record admission action、原签名record、原 held 报告和catalog独立验证并确定性重建集合，再与 v2 exported集合逐字节/ref相等；不是读到一个sidecar就信任。原 `CommittedQualificationSource.read/assert_current`仍需原installer动作、真实commit relation、target/原持有对象、floor及无pending。v1保持其已有安装资格语义，但不提供资源完成观察或认证缺席。无新增资源sidecar/签名/自提供key；v2是原事务事实的输送，不是资格来源。

## 4. 唯一 publisher 与真正提交位置

Backend在原 `NativeInstallationRecordConsumer.admit_record` 外部验证材料之后、control.reserve之前，调用私有 `prepare_diagnostic_resource_completion_set(*, original_record_action, original_materials, original_installation, expected_catalog)`，返回 frozen/eq=False、不可序列化的 `PreparedDiagnosticResourceCompletionSet`。只原 consumer可登记该member，绑定同 connection/action/Engine/Bundle/materials/安装、thread/epoch、expected registry/current、全部完整 bytes/ref和捕获行；仅解析DTO不产生此member。原installer record来源未真准入或已声明资源报告无法验证时，不产生成功准备对象；原安装资格真通过、完备遍历确无资源报告时可准备真实零项集合，但不能准备任何positive body。

原 `admit_record` 的**同一个短 transaction**：原 `_local`和current/expected revision检查→原 records/event/current/commands写入→完整派生集合及每个完成body insert-or-exact-match→再同连接原current/member/报告缓存、行快照重核→commit。事务内禁止OS/pipe/file读、crypto、独立报告扫描。相同action/key/完整request+record+集合返回原事实；同key不同body409，部分已提交行缺损/矛盾unknown，不补一半并声称成功。它不修改 Production budget，不发模型/ASR/生成调用。

事务之后原 export v2→evidence/snapshot持久化→control.complete→原 receipt当前性→Native `CommittedQualificationSource`核确切动作/集合→原 `QualificationRegistry.install_committed`，才可被resource reader观察。DB commit后sidecar/ACK/floor部分完成均未知：原同action恢复读取已提交完整行，不再插入第二事件，不新key、不重收费。Registry之前不能positive，传输超时不能认证absence。

已有 qualified安装需要添加/更新资源报告时，固定源码尚缺真实 `replace` producer/consumer。最小接点为**原安装record动作的Owner受认证更换分支**，不借生产Worker、模型proposal或一般execution scope：

1. 原OS Owner/session确认一个确切安装更换动作（原实例、旧 record/current/floor、同原trust anchor、新完整record/ref/material index及expected registry revision），由原native确认/安装source登记真实 action member；原私有 `NativeInstallationRecordConsumer.replace_record(*, engine, bundle, bound_connection)`只消费这种当前Owner动作。不能复用初次installer consume去绕已有Owner拒绝，不把 ProductionAdmissions 的执行或策略guard当安装管理capability。
2. retire原Registry、关新leases；原 writer/read guard和OS文件持有要真实drain。必须释放的原Process/Job后代实际terminal后才能改其拒写/删除材料，窗口/EOF/返回码不算terminal。不得持 Backend Control/file锁等待Registry写锁。
3. 更换分支沿原安装lock/control.reserve、原current/trust/expected revision CAS、真实Owner动作member及原许可/报告验证，复用本节同原records/events/current/commands/集合短writer；event.kind=`replace`，record新revision，保原旧不可变行。原 Native `CommittedQualificationSource`新增显式replace动作来源分支并核完整前后current，不把宽字符串kind放行。
4. 完成原v2导出/floor后安装新的原current source；旧session/observation全部失效，原qualified服务按真正固定startup来源重建。相同action未知恢复必须由原Owner/current恢复动作读取实际facts，不假confirmed。

此分支是当前要实现的必要生命周期缺件，不声称已有。若真实Owner确认载体或replace source未配，明确安装管理not-ready，保已支持初次路径；不能用永久503代整个功能实现完成。更换必须有实际Owner权限来源，不能由本ADR自动扩旧caps。首次安装/更换确认属于环境准入，不要求每个作品或项目重复确认。

同payload只更新真实报告可使原waiting Run使用同三身份/catalog/method的新完成事实。若payload/route/catalog/registration真改变，则旧Run binding不能静默换成新安装；维持原scope/current不匹配错误及原授权迁移规则，不新Run/预算洗旧任务，不在本卡发明迁移权限。

## 5. 原 held reader 与认证 absence

Backend在原 `NativeInstallationAuthority`/`NativeQualifiedInstallationIssuer`上加以下唯一私有具体端口，原同Engine工厂创建，Runtime/Bundle仅消费原对象；不给public API/MCP、renderer、任意provider注入observer：

```text
observe_diagnostic_resource(*, evidence: InstalledProductionEvidence,
    method_ref: ComponentDiagnosticMethodRefV1, diagnostic_catalog_sha256: Sha256)
    -> HeldDiagnosticResourceObservation
read_diagnostic_resource(*, observation: HeldDiagnosticResourceObservation,
    completion_ref: DiagnosticMetadataRef) -> bytes
assert_diagnostic_resource_current(*, observation: HeldDiagnosticResourceObservation) -> None
assert_diagnostic_resource_writer_current(*, sql_connection,
    observation: HeldDiagnosticResourceObservation, qualified_writer_lease) -> None
```

`HeldDiagnosticResourceObservation`是frozen/eq=False/非DTO的原成员，固定issuer/原QualifiedHeldFactsObservation/connection/原Native session observation/Engine/Bundle、thread/epoch、完整method/catalog、原record/action/request/current/floor/报告refs、SQL集合与完成行captures、body bytes/ref、观察状态及原限时。只真实observer注册；同值对象、反序列化 JSON、随机ID不能造member。

状态只有 `committed` 和 `absent`：

- committed：当前原Registry已安装本次原v2完整commit source；该完整method在集合中且body/报告均真核；Backend还读取原DB原同event的集合和完成行、body/size/SHA全等。正文严格正且≤2MiB，read前后均原current/held/source一致。
- absent：当前同原Registry和原v2事务的**完备集合**有效，完整method确在原catalog但在集合无匹配项；Backend同current/event集合及该查询位置真实不存在。证明仅为“该版本未提交此方法的完成事实”，不证明磁盘没文件、资源永远不可用或方法禁用。空集也须已提交。capture包含集合全行和absence查询键；事务内再次确认无该完成member。absence不产生 completion_ref/body，不加入stable input，不触发分析/queued/新fence/付费。
- legacy v1、缺集合、传输未完成、busy、pending、未知提交、报告或安装current不可用：原明确not-ready/unknown错误，绝不翻译为absent或null。损坏有指向的不可变行为422/unknown而非无事发生。

观察只来自原已绑定Child Process/peer的原qualified channel；原 `QualifiedRegistration`一次真实OwnedProcess、PID/creation/SID/peer与同instance/role/image规则、原Registry Arc/epoch、观察对象同thread都保留。新观察ID原session内唯一、有界，最多原64；原session/child/Job终态及close/revoke/epoch变化失效，不能借借用线程退出后的ID继续assert。

Integration为同一通道新增精确私有wire `held-resource-authority-v3-diagnostic-v1`。v2原五method/14field回复原字节兼容，资源能力不能偷偷接受v2。v3原五method除wire版本外保持原shape/语义，新method仅两项：

```text
observe_diagnostic_resource:
  wire/session/seq/method/observation_id/method_key_sha256/diagnostic_catalog_sha256
read_diagnostic_resource:
  wire/session/seq/method/resource_observation_id/completion_ref
```

method_key为完整原method_ref canonical SHA，由Backend已验证catalog决定，Native从原payload held manifest重新分派这个finite key；非法key403，不是caller提供filepath/role/route定义。请求仍strict/有界/顺序单调/原peer前后核。新的成功回复单独strictgrammar：wire/session/seq/status/code/resource_observation_id/qualification_binding/method_key_sha256/diagnostic_catalog_sha256/completion_ref/body_utf8，observe不带正文，committed有ref、absent ref和body为null；read只接受本session已登记committed member且exact ref，返回exact canonical UTF-8 body，其字节size/SHA必须与ref相等。original qualification_binding仍完整原record/revision/floor；新resource ID不是原安装observation ID，也不是任何授权token。

observe成功code仅`diagnostic_resource_committed`或`diagnostic_resource_absent`，read成功仅`diagnostic_resource_body`，均status200；读absence拒403。拒绝status/code闭集为403 `diagnostic_resource_scope_denied`/原peer_denied，409 `diagnostic_resource_changed`/原qualification_changed/revoked/expired/lease_conflict/observation_unknown_or_foreign，422 `diagnostic_resource_body_invalid`/invalid_frame，503 `diagnostic_resource_observer_not_ready`/qualification_unavailable/qualification_unknown。拒绝的resource ID/ref/body必须null，不能夹带positive。新factory在原OwnedQualifiedAuthorityConnection内选择经可信startup固定的wire版本/strictparser；不接renderer版本参数、不另接受任意subclass或更换现concrete issuer类型检查。

资源body、原qualification/source与method信息均来自 `CommittedQualificationSource`及 `TrustMaterials`；Native仅新增 `TrustMaterials.read_required_ref(ref, purpose, limit)`，用原ResourcePins已持有索引member读bytes，前后assert_current，不能从caller路径open。限定purpose=qualification_report与真实原catalog源码/原v2commit材料。body_utf8包含转义后整个wire frame仍须≤原FRAME_LIMIT；超限503而非拆成通用下载/放大上限。拒绝不返回伪body/ref/observation；错误闭集保持403/409/422/503类别及具体原因。

资源observe/read均在**原短SQL writer之外，且在原native writer lease begin之前**执行；不允许在已active native lease上observe或另开嵌套Registry读锁。准备的resource member绑定原qualification观察；之后原 `current_writer_lease`只能基于同原evidence/facts/record/revision/floor进入，沿原真RW guard固定source。writer端口仅本地member/epoch/原lease及同SQL captures/absence重核，禁止RPC/files/crypto。read后再assert原current；close或release未知不得谎称guard已释放。

## 6. 三consumer接线及实际调用顺序

Backend唯一创建并绑定原resource ports到RegisteredMediaRuntime/Bundle production services；constructor不接受public module、caller-qualified Bool、catalog任意路径或第二issuer。Runtime安装身份沿v2完整registration/productionresource/runtime三SHA，不能ASR-only回退。Media只消费原 completion_source_refs 与原CurrentFinalEvidencePorts，不能创造完成报告或调用Owner安装动作。

1. `DiagnosticResumeRuntime.probe_current_diagnostic_resume`固定130的37–76读真正waiting journal/Fact/input/preparation/current capture；它从原registered binding及**原strict已持有catalog**确定被请求且尚未消费的methods。在原current_guard/native begin之前、无SQL writer且已结束外部reader时，调用§5 observe，并读取committed的body。原 `diagnostic_method_not_ready`信息需求才允许此资源变化入口，不给每次poll加时间戳产生new input。
2. 原qualified current_guard再核原registered request、waiting journal/selected/current CAS/captures、same qualification；committed resource行/集合captures和heldmember纳原probe。仅新真实completion ref按原canonical排序加入v2 stable input；原方法、precision report、source/ref不丢。相同ref早已used不新增，认证absent保持still_blocked/diagnostic_resource_not_admitted。未知Operation仍needs_reconciliation，不能以资源完成覆盖unknown或自动重发。
3. `_diagnostic_completion_bytes_no_lease`固定189–201对qualified_resource读取原held observer已认证exactbody，无synthetic lease；现有READY/feedback分支保留。probe的原同thread/fence/限时/captures机制继续。资源输入变化由原resume writer/CAS提交，之后原queued/newfence/claim才能分析；observer不写Run状态。
4. `DiagnosticSelectionService._diagnostic_v2_inputs`固定48–103的资源else分支替为唯一原resource read：准备阶段先外部observer读取原集合/body、与stable已有completion ref及原method/binding全等，然后和原captured source_rows结合。原 registeredinput immutable409门不变；**不能在现有SQL reader/writer中新增pipe/crypto**，必要将这一个resource分支预读提到该reader之前。ComponentDiagnosisService.prepare固定311–349仍先factory+methods核，resource读在它的320原guard前；321短writer只check缓存/行和原guard。
5. `DiagnosticSelectionService.read_diagnostic_completion`固定136–156保 `_diagnostic_inputs_current`前后两次以及completion∈原heldinput。资源正文由原resource observation读；若已active native lease，则使用该member在begin之前真实读出的原bytes，并仅原短writer/member重核；缺此预读不得在SQL或lease中临时开RPC。原methods/current/resources/parent/fence和完整ref仍核，changed409/denied403/integrity422，不能generically吃EngineError变absence。
6. 原resource getter与writer assertion的member附在同原 `_diagnostic_resumed_captures`、`_diagnostic_resume_probes`和 `_diagnostic_inputs_held` 生命周期内，不新parallelFlow/调度器。ComponentDiagnosisService的351–373输入current核把原resource member和captures纳入；Registry revoke/floor变化不得继续生成、分析或publication。原whole verifier/两authority/precision gate始终在其原位置。

没有 `diagnostic_method_not_ready`请求、method不在原catalog、同method但report不同scope、input未声明这个ref均不授消费。competing_causes/timing不足不能凭ready资源自动判断失败组件或重做TTS。catalog完整与原factory.methods相等、各源码ref/fullroute verified仍由原 `_diagnostic_methods`151–177检查，资源positive不能跳过此检查。

## 7. 失败、幂等与归属

| 触发 | 真实结果 |
| --- | --- |
| 有效v2集合无该method完成 | authenticated absent；仍waiting，无body/ref/Operation/费用 |
| legacy v1未完成资源派生；report/suite/独评/许可未配 | diagnostic_resource_observer_not_ready /503；不是认证absence、功能完成或伪positive |
| current/revoke/floor/expiry/待替换变化 | 原qualification_changed/revoked/expired或pending unknown；旧member不可重用 |
| peer/role/instance/成员/fence/输入范围错 | 403；无renderer参数升级scope |
| 同action/同key不同完整body、旧mutable/current CAS变化 | 409；wholetransaction rollback，不覆盖原immutable事实 |
| 指向的body/完整size/SHA损坏、严格grammar错误 | 422；不翻为不存在或重建report |
| commit后evidence/floor/ACK失联、Process/Job未终态、unknown Operation | 保明确unknown/reconciliation；原action只核实，不新key、重收费或把needs_reconciliation改queued |

Backend负责唯一所有私有模型、metadata写/读、event-export v2、真实Owner replace来源消费和Runtime/Bundle三分支、原current/captures守卫；必要迁移仅其负责，使用现metadata与原安装四表，不为此新增第二资格账本。精确生产路径：domain/installation_qualification.py及committed_installation_evidence.py、domain/diagnostic_recovery.py；application/installation_record_consumer.py、committed_installation_evidence.py、native_installation.py、native_qualified_issuer.py、component_diagnosis_service.py、diagnostic_resume.py、diagnostic_selection.py、media_registration.py；infrastructure/native_qualification_trust.py、qualified_authority.py及原native_installation_record确认载体消费。文件归属不授现在写或执行。

Integration负责严格v3-diagnostic当前资源builder、完整有限catalog/method/indexed source/runtime/许可/报告打包；Native TrustMaterials/qualification_pack/qualification_commit/qualification_registry/qualified_authority/original安装Owner action source的v2evidence+v3wire实现及原Process/Job/held生命周期。固定builder BuildProductionResources.py179–213仍只v1四键，必须显式支持严格当前catalog而非把有限recipes/diagnosis丢弃；完整最终Backend+Media ordinary闭包、四profiles/147+24保留，历史102+12检查不算当前包。BuildNativeInstallation独立host receipt无环规则保留，provenance未准入不得改qualified。

Media保已有绑定方法调用和完成body实际消费，只从原ports读取；不编写Backend DTO、不发布环境资格。Test维护真实suite/case和实施验证；Review独评合同/实现/证据；Acceptance独立实际资格，Architect不代任何角色。

## 8. 后继独立验证必须取证的最小集合

1. 实际资源报告覆盖该完整method的真实调用/有界输出、原source/route/target/四profile及实际suite/独评/验收/许可关系；缺任何项不能commit positive。用模板/模拟须标synthetic，不能当实际qualified运行。
2. 真实首record事务原子写完集合+body，与记录/event/current/command及Native Registry原动作全部一致；DB失败整组rollback；commit后sidecar/floor/ACK故障同action复读0新增event。Legacy v1 bytes/raw签名和原安装行为保持，资源观察明确not-ready。
3. 真实无匹配已提交完备集合认证absent；未提交集合/EOF/timeout/busy/格式未知/当前撤销不被伪装为absence；本项不需要伪造报告证明资源通过。
4. 错catalog/method/version/fullroute/source/index/三SHA/profile/instance/报告validity、改body/size/SHA、假same-value member、跨thread/session/fence均拒绝；前后变化/current/floor/revoke/expiry实际阻断短writer和consumer。
5. 原Owner真实replace在退役和实际Process/Job释放后提交新resource事实；无Owner/source不能从worker放行。同payload真实报告变化可被原waiting input消费一次，未变input复用、不循环分析；payload身份变旧Run不静默迁移。Unknown Operation不queue/不再收费。
6. 三consumer实际读exactbody并把其纳immutablev2input；sameinput冲突409、保原200ms/完整验证/两authority/预算限次/未影响资产。断点在probe/read/park/claim之间按同current/CAS恢复，不永久占位声称已完成。
7. 实际记录无SQL writer内OS/pipe/crypto I/O，无nestednativelease/重入Registry死锁；未知release保原guard到确切Process与Jobterminal。Windows、macOS arm64/x64、Linuxx64真实平台资格仍独立待验，设计/编译/manifest不替运行。

本次仅固定源文本、JSON和身份观察；当前真实资源专属报告、原Owner replace source、更换/守卫运行、三OS、完整R1/R2验收未由本阶段证明。上述接口让原角色能实现正常positive、认证absence、未知恢复及三个consumer完整路径，不把当前缺件改为永久503或伪成功。
