# ADR0070：覆盖生产者的工作前成员、逐报告证明与已接受根

状态：DESIGN_ONLY_READY_FOR_INDEPENDENT_REVIEW。只修 CPAI-P01/P02/P03 的合同缺件，不自行关闭 finding，不批准实施、资格、SQL、测试、模型或费用。0068/0069 原字节冻结。本文替代0068相应歧义条款的后继语义，其余职责独立、真实 held source、两 authority、许可、current/local、预算、unknown 与完整验证保护保持。

## 1. 实际停止来源与三处转换

停止137的真实 `qualification_execution_capture.begin_capture` 在执行前将 `suite.producer_ref` 按 check 来源读取并写进 header；suite/check 是两份单职责资格，不能将 suite source 改名或要求未来 check 报告。`verify_resource_coverage` 分别读取 check report 与 observation，单 observation 本文没有完整 CheckSection/父报告字段。原 `TrustAdmission.material_refs` 属于完整不可变正文，真实初次 trust consumer 拒绝替换已有 trust；新 index 不能回填该正文。

必要停止源完整 SHA：capture `20d4bb03bb2edb70c3fba2437d6347a73c329fce342c99c1fd27c8b6a25f8df3`；原 coverage types `84f9042301940f234e37164570eb5cb08c6d874377c8b7a6c69e8427ce03bf99`；coverage caller `309701109142b8d3e1bb8c8099197da4b616b4c90f3e37310e58a32cf9b172e6`；Native trust `a0d54a13fc3b114a191295dab554ed3d4032056842e24727aa616c047a878175`；TrustAdmission types `c317c9b0fb8122a74149bdb6dab594b480a3f5e4688c63f3e70837d7c21c3996`；trust consumer `40317c88df1b01290c04c594d213340e6421118f538f60069ebd7be223f2dbba`。原 record consumer/export 的实际 stopped caller 和新增输入身份另列 InputPins，不读取生产热源。

下列新增类型、方法和分派均为待实施合同，不能称 baseline 已存在。Backend 是唯一 schema/canonical/consumer owner；Integration 用同源 grammar 接真正 Native/角色 source，不自发 Test/Review/Acceptance 工作证明。

## 2. 唯一 primitive 与兼容分派

复用原 QualificationRef、ResourceCoverageBindingV1、RecipeSourceRef、Identifier、strict I64/PositiveI64、canonical_bytes、parse_exact、Ed25519 投影。完整显式字段/null、递归排序 compact UTF-8、无重复 key/NaN/额外字段；原2MiB单件、4096 unique refs/128MiB整体材料和原 wire FRAME_LIMIT 保持。所有列表沿原 ref/ID/source 排序去重。相同 ref 不同 bytes/purpose 拒绝；所有实际使用材料计入同一闭包。

新增 format 只有 `diagnostic-coverage-role-work-proof-v2`、`diagnostic-coverage-producer-index-v2` 和第5节的安装动作/提交版本。准入 `diagnostic-coverage-producer-admission-v1` 仍是单 role，不变更原资格正文、签名或职责范围。已有 work-proof-v1/index-v1 正确历史字节仍精确读；不得自动重编码为V2、补未来字段、将V1 observation 猜成新父关联。无法取得旧 observation 的真实父证明时是明确 evidence missing，保历史原件，不造新的接受事件。

## 3. CPAI-P01：有限真实工作前成员与报告后来源分层

### 3.1 接受能力目录，不要求未来报告

`diagnostic-coverage-producer-index-v2` exact 字段与0068 index-v1相同：format、index_id、revision、issuer_id、trust_mode、anchor_key_sha256、host_build_receipt_sha256、bindings、producers、revocations、valid_from_us、expires_at_us、signature；只更改 format 和条目语义。producers 仍为唯一排序的 `{producer_ref,work_proof_refs}`，1..4096项；每项 work_proof_refs 为0..4096，空集合只表示该真实单职责资格尚无完成工作。非空逐件接受实际 work-proof-v1/v2，并严格核 role/binding/report/实际 work；空集合不能核报告、正向资格或省略已引用的必要证明。

I0可在真实 suite正文/证明已产生、check工作尚未开始时包含 S资格及其 suite proof、C资格及空 work refs。原锚只签已实际准入的职责 source 与实际存在的证明，不预签未来结果。I0必须已由真实原 TrustAdmission 接受，或是第5节真实安装/Owner动作选择的根；“文件存在、签名正确、同锚”不等被接受。首安装没有任何已接受来源时不能凭I0自行成为 source。

实际角色入口只能由0068已准入的 Test source 工厂注册。publisher 运行发生在真实发行验证实例，不是客户安装器代 Test 执行；local_verifier 使用已接受的实际有限 Test source/key/entry。原许可、真实资源与有限 attempt 必须已满足。工作前成员既不证明资源通过，也不把 not_ready 安装变成生产 Worker 权力。首次未 qualified 的验证只能沿原真正 installer action 的受限资格验证入口或真实发行实例；不得伪造 RegisteredMediaRuntime、AttemptControl 或放宽普通生产 guard。该具体入口未实现时明确 NOT_IMPLEMENTED 并交原 owner 接线，而非永久以未来报告挡住已合法的 check 工作。

### 3.2 原强工厂的唯一新增私有成员

`open_coverage_check_work(self, *, check_source, attempt, suite_ref, binding, check_id, at_us) -> HeldCoverageCheckWork`。只能由同一原 NativeQualificationTrustSource 的 `_TOKEN`/真实受认证角色 bootstrap callsite 创建；check_source 是实际登记的 Test-check source 对象，attempt 是原 `hold_qualification_attempt_source` 注册的真实有限 HeldAttemptSource，不接受 JSON/renderer 传入资格对象。

工厂在 SQL 外验证：同 Engine/Bundle/实例/epoch/thread；原可信当前根及其中真实 C单role=check准入、同 Binding/target/source/build/key/有限有效期及无适用撤销；check_source 正是C登记入口而非S；实际 suite_ref 完整 bytes、S的 suite report-bound proof、该binding唯一case/check_id与冻结源；同原 lease/attempt/control/deadline、原当前安装或受限installer资格来源、资源许可/Operation预算与限次。不能沿用别次工作 proof 授新资源权限。

HeldCoverageCheckWork 为 frozen/eq=False/repr=False 私有注册成员，保 `_source,_check_source,_attempt,_producer_ref,_root_ref,_suite_ref,_binding,_check_id,_case_source_ref,_at_us,_epoch,_thread,_deadline` 的真实对象/身份。只有原工厂注册表 identity 成功可消费；plain dataclass/反序列化/同字段对象无效。

`assert_coverage_check_work_current(member)` 在 SQL 外核真正 peer/holds/current/accepted root、C资格、实际 check_source、同attempt/lease/deadline；`assert_coverage_check_work_local(member,connection)` 在短 writer 仅核已注册同对象/本地生命周期、原租约/fence与已固定 SQL/current captures，不做签名/文件/RPC。旧 source关闭、root/current改变、撤销、租约或线程失效即不能新启动。已完成事实不删除；unknown只核实原 Operation。

### 3.3 capture 实际接线与消费顺序

真实 Test-check 入口从上述工厂取得成员后调用 `begin_capture(service,lease,inputs,*,suite_ref,check_id,check_work)`。旧不带该来源的调用只保原拒绝/NOT_READY，不自动将 suite source 当 check source。begin_capture核 member的 suite/case/binding/inputs/attempt 完全相同；header.producer_ref来自C，header.suite_ref仍原suite，绝不来自S或请求字符串。

原 registration key 的 run/input/suite/check 口径不变，真实 header 初次登记在同原 writer 先后核 check_work_local、issuer guard、实际原注册 inputs/lease。已有同key必须保原 execution_id及完整header；不匹配C或原body为409，不覆盖旧错误header。capture原成员保强 check_work 引用，before_original_claim与原消费/导出持久点保原current/局部门。结束 attempt/connection/role source 后借用成员失效，不借旧 execution_id 重启工作。

然后原Executor/Operation账本执行 case，原 capture/exporter持久真实 request/result/operation/consumption/source前后/失效attempt。Test由实际 case runs生成原check/observation正文；完整真实工作对象产生第4节逐ref proof。报告后才 `read_admitted_coverage_producer(...,report_ref,at_us,usage)` 注册报告来源。前者不能当后者使用，后者不授首次 dispatch。失败/红/unknown仍如实输出，不签pass；合法已有结果/签发ACK丢失走原查询与immutable replay，不重发/重扣/换 key。

## 4. CPAI-P02：每个真实报告的唯一 work 投影

### 4.1 work-proof-v2 外层与角色分派

exact 字段：format、proof_id、revision、producer_ref、role、binding、report_ref、suite_ref、check_report_refs、independent_review_ref、source_definitions、work、started_at_us、finished_at_us、valid_from_us、expires_at_us、signature。身份/真实source/有效期与 role key 签名投影沿0068：canonical全部字段只去掉signature，完整ref包含签名。同 `(producer_ref,role,binding,report_ref)` 最多一份不可变证明；同身份不同body/proof竞争拒绝，不挑有利版本。

suite/review/acceptance 的 work exact字段及外层关系沿0068不变。check 按被读取的实际 report format 只允许下列两个不同 kind；不能由任意 kind 字符串扩大 source能力。check 的 `allowed_formats` 原声明可产真实七伴件，**不表示七伴件各是一份独立role报告**；伴件只作为原实际工作闭包证据，没有单独 role-work proof，也不走 report-bound producer注册。独立调用该reader把伴件当 report_ref 必须拒绝。

### 4.2 check_report 投影

当 report_ref 为完整原 `diagnostic-resource-check-report-v1`：role=check；suite_ref等于该body.suite_ref；check_report_refs=空；independent_review_ref=null；work exact字段为 kind=check_report、execution_ids、observation_refs、companion_refs、case_closure_sha256、result_section_sha256。

读取完整父 suite 与该 report；恰取 binding相等的原 CheckSection，不猜 Aggregate第一项。result_section_sha256是该完整section的 canonical SHA，case_closure_sha256是同Binding原SuiteSection.cases完整 canonical SHA。该 report 可以覆盖suite的合法case子集，不能把某一report proof称成全部suite已通过；所有report合并后仍由原validator检查全部cases恰一次、无缺失/重复/有利子集。

observation_refs是该section所有非null observation_ref完整排序唯一集合；execution_ids是这些完整原observation实际execution_id的唯一排序集合。对每个result核 check_id/case_source/时间/真实执行类型与该suite case相同；同一观察或execution用于两个不同case拒绝。companion_refs为这些观察按原required_observations真正引用、经0067共享验证器实际求得的完整七伴件并集，不按材料文件名扫描，不带无关伴件。列表允许真实无执行场景的空集合，但原红/error/skipped/not_run/unknown必须留在完整result section，不能成为资格pass。

### 4.3 check_observation 的明确父投影

当 report_ref 为完整原 `diagnostic-resource-check-observation-v1`：role=check；work exact字段为 kind=check_observation、parent_check_report_ref、parent_report_work_proof_ref、check_id、execution_id、case_source_ref、case_sha256、result_sha256、result_section_sha256、observation_body_sha256、companion_refs。外层 suite_ref=父report.suite_ref、check_report_refs恰为 `(parent_check_report_ref,)`、independent_review_ref=null。

父选择只来自这个已被接受 index中**唯一属于本 observation_ref/binding/C资格的 v2 proof**明确两个父refs；不扫描材料猜父。先读它指定的父report及父check_report proof，核 parent proof 的 report_ref/binding/producer_ref/suite_ref 与父body完全相等，kind=check_report，原全部section投影有效。父proof的 observation_refs恰含本ref一次。父section恰一个result引用本 observation_ref，并同 check_id/case_source/时间和本原observation；suite恰一个同case。两个proof或两个候选父争抢同observation，即使各自签名正确，也409，不能择优；合法多report分片要以不同真实case/observation形成唯一关系。

case_sha256、result_sha256、result_section_sha256分别来自该实际原完整case、该实际完整result、父完整CheckSection canonical SHA；observation_body_sha256等于本完整canonical body及report_ref SHA；execution_id、check_id、case_source_ref等于实际observation；companion_refs恰为本观察真实required dimensions的原共享verifier闭包，不借父其它case。outer source_definitions是该次原实际capture/exporter/case/签发source完整投影，须在真实准入图内，不能将父绑定扩大为不同source。

无环顺序：3.1资格→suite正文/proof→原七伴件/observation正文→check报告正文→check_report proof→各check_observation proof→index。父report只引用观察正文，父proof不反指子proof，观察正文不回填父proof/index；proof不引用未来index/接受事件。review/acceptance再以完整实际读/执行闭包产自身证明，最后签aggregate index，不改变其真实独立职责。

### 4.4 同一实际 reader/caller

0068的 `Closure.producer(ref,role,binding,*,report_ref,at_us,usage)` 及原强 `read_admitted_coverage_producer` 签名保留；实际 check-report loop先按本report_ref验证父proof并记录report→binding→result→observation的受控关系，observation loop仍按**本** observation_ref读来源，要求该explicit父正是前面已读原父，不凭producer相等跳过。

父 check_report proof 的投影核验只完整读取原 observation正文、原 capture/伴件并重算本section，不递归请求子 observation proof；子proof随后引用这个已验证父proof。外层完整 coverage loop 仍独立逐observation核子proof，任何缺项都不进入 PreparedResourceCoverage。证明DAG核验与整套资格核验分层，不能用“父已支持”删子来源门，也不能在父投影中调用第二次完整资格验证制造启动环。

suite/review/acceptance逐各自ref；七伴件经原 `Closure.companion`/共享execution-set核 source/headers/request/result/真实原member与C，不另 mint proof。完整grammar/source→外writer双current→原注册origin→writer内local/current/CAS→完整archive的顺序不变。每actual origin明确 `_report_ref,_proof_ref,_index_ref,_at_us,_usage`；所有actual origins均遍历，不能只检查第一份。

## 5. CPAI-P03：同原 TrustAdmission 下明确接受新根

### 5.1 根来源优先级是来源分派，不是扫描

T、T.material_refs、原trust row/event/TrustCommit完整不可变。初次 trust-only 阶段可从T.material_refs精确读唯一 v1/v2 producer index根作为**有限职责工作来源**，不能据此 qualified。实际首次record/replace准备阶段只取真正该action明确接受的 `coverage_producer_index_ref`；commit之后当前C只取原current record action的同字段。历史H只取其原真实已归档接受事件中的该字段与当时完整材料，不能借C补H。

旧无显式selector action的兼容读只可用其T原material_refs中恰一份已实际接受且完整归档的producer index根。零份是真实legacy缺来源，保原事实；多份/未知为冲突/unknown，不猜最大revision。新的真实Owner replace可以明确接受第一份当前root；若旧来源有真实根则必须expected该根，若严格旧grammar经受保护读证明确无根，expected值才为null。不能以I/O错误或缺archive把unknown变null。已有index revision较大或同锚签名不自动改变选择。

### 5.2 新动作 exact grammar

首次新 `installation-record-admit-request-v2` exact：format、action_id、kind=record_admit、trust_admission_ref、expected_registry_revision、record_ref、record_sha256、material_index_sha256、host_build_receipt_sha256、coverage_producer_index_ref、intent_sha256。record_ref是完整原record.ref，SHA、同build、T/issuer/anchor/实例严格一致；intent_sha256=canonical全部字段去掉intent_sha256的SHA。原scope/key/body canonical SHA为 command/control reserve 幂等身份，不改原Goal canonical。

首次新 `installation-record-admission-v2` exact：format、action_id、accepted_at_us、kind=record_admit、trust_admission_ref、expected_registry_revision、record、record_sha256、host_build_receipt_sha256、intent_sha256、material_index_sha256、coverage_producer_index_ref。真实Native installer action先持原root/ref/body及完整材料、固定上述request，再在原实际接受动作中建立原强 RecordAdmissionOriginal；请求从本receipt唯一重算。不是从新增字段实例化权力。原首次无Owner管理绑定/无record的限定和真正Trust/OS installer来源保持，不改初次trust_admit或把这个首入口变replace。

新 `installation-record-replace-request-v2` exact字段为0066 replace-request-v1全部原字段：format、action_id、kind=replace、trust_admission_ref、expected_registry_revision、expected_record_ref、expected_revocation_floor、expected_owner_binding_revision、expected_material_index_sha256、record_ref、record_sha256、material_index_sha256、host_build_receipt_sha256、intent_sha256；另增加 coverage_producer_index_ref、expected_coverage_producer_index_ref。format使用v2；新root非null，expected root按5.1为QualificationRef或可信legacy absence的null；intent按完整新request去掉自身重算，不能沿用v1digest。

`installation-record-replacement-v2` exact仍 format、accepted_at_us、request、record、owner_confirmation_ref；request为上述v2。真实Owner UI/TTY显示原旧/current root与新root及完整资源差异，并确认同一完整intent，原 OS Owner/session/强 action/drain为真实能力来源。新增root选择仅该动作有限材料，不能开放任意报告/职责/生产权限；同T issuer/anchor不能换key。原120秒确认窗、强drain及真实后代终态、断连/epoch/floor/current保护不减。

所有root正文在该action已持有的原 QualificationMaterialsIndex内按原publisher_provenance/verifier_code_index目的明确存在。五字段material index不加字段；仍保T全部原材料/旧I1及需要的历史档案，不覆盖旧文件。root与准入/proof complete DAG、当前有效期/撤销、全原报告/独立关系、same record/Binding完整覆盖在SQL外严格验证。选择I2不由其签名自授权。

### 5.3 原wire版本与唯一消费者

首次 purpose/六键locator、真实同peer/实例/host源不变，新 wire=`held-installation-record-v2`。沿原4byte LE framing/FRAME_LIMIT/10秒：request exact `wire,session,seq,method=admit_record,instance_id`；reply exact `wire,session,seq,status,code,instance_id,record_admission`；成功200/code=record_source_admitted且payload是完整admission-v2，错误原403/409/422/503且payload=null。caller从真正initialization source选择明确version，不能失败后换版本盲重试。旧v1-candidate原分派/字节保持。

replacement purpose/locator/peer保持0066，新wire=`held-installation-record-replacement-v2`，四方法、公用头、seq/deadline/错误与exactpayload key保持；prepare/recover的replacement为v2，assert/confirm/recover的request SHA都必须同一v2原请求，其原强action/drain对象对应该全字段。无public root mint或新channel。Backend `NativeInstallationRecordConsumer.admit_record` 显式v1/v2分支；原 `replace_record`/`resume_existing_replace` 消费对应v1/v2，不将kind字符串当来源。

### 5.4 同writer接受、归档与提交恢复

原source在SQL外实际选择/读取候选root并建 registered Prepared root selection，冻结同T/issuer/anchor/host/instance/action/request SHA/new record/material index/expected current及root。成员eq=False/不可反序列化，原强installer/Owner action、peer/holds/drain生命周期负责 current；仅签名/body不能构造它。

首次writer核原empty record/Owner状态、真实T与expected registry/floor；replace writer核0066全部expected captures再核expected旧root。依原顺序 `control.reserve`→短writer先/后真正同source local检查与完整CAS→原record/event/commands/current、完整newroot/producers/proofs/报告和接受关联同事务archive。`receipt_json`保存上述完整新action，event/request SHA包括selector；不另给metadata里的root pointer优先权，不先切root再commitrecord。rollback则全不提交；费用/Operation保持原账本。

原 committed export新增 `installation-committed-evidence-v3` exact外层仍 format、instance_id、registry_revision、trust_commit、record_commit。trust_commit是原真实TrustCommit，不改T；record_commit exact仍 record_ref、action_ref、request、request_sha256、registry_revision、source_receipt。request/source_receipt通过strict格式判别原v1/0066v2/本节v2动作；新v2的完整request只从实际event原receipt重建，不使用原 `_request` 的五键lossy重算。action_ref仍 `{document_id=action_id,revision=实际event.registry_revision,sha256=完整receiptSHA}`；requestSHA、event、command、同record/current所有字段一一对应，版本对应错误拒绝。旧v1/v2 export读者保留，不能热改旧export或将新动作塞进旧五键request。

当前source的root selector从该真实完整RecordCommit.source_receipt/request唯一投影，并核same action/current/event/command/ref/material index/root archive；trust-only bootstrap才取T唯一root。Native `Registry.install_committed`/完成reader独立消费同v3与同grammar并重核真实Owner/action/target/map/报告，backend reply或sidecar不证明完成。原 protected snapshot字段/qualification binding不额外复制root；它们的实际record/revision指向已原子提交的action，必须经该受控reader取root。

原 `open_native_qualification_trust`/assert_current/_assert_snapshot_rows/read_committed_evidence/export_committed_evidence 增量 pin实际action/root和完整source成员。所有活动origin依赖当前C的相同accepted selector，root选择变化使旧活动origin失效；H仍借C受认证历史reader读H真实接受的root/报告，H事实不复活H grant。不能仅把root在材料list里找到就注册。writer只重核已固定原source/local/SQL，不做文件/RPC/签名。

ACK丢失/冷恢复只按原 same owner/scope/action/key/request SHA 查询原commands/event/fullreceipt/archive和protectedfloor：同body重用同提交和选择；不同body409；SQL未commit且原source真实有效才继续同writer；已commit仅原可信导出/control/native收尾；未知不重建action/换key/清pointer。新进程丢真实Owner/action/drain来源沿0066真实仅该原请求的恢复确认，不从原receipt造能力或回填接受时间。原root/proof缺同字节可受控补回，不重新分析扣费；真正缺失/无法判定保持精确missing/unknown，不能宣完成。

## 6. 实施归属、错误和独立保护矩阵

Backend：唯一v2 proof/index/动作及v3提交grammar、签名投影/strict dispatcher；原pre-work强工厂和capture header/writer；checkreport/observation两caller的exact父投影；真实installer/replace/resume/committed export/current/H reader完整接线。新增持久内容走原event receipt/archive/current CAS；如原archive字段不能保完整action/来源，由Backend提交明确最小迁移方案，不用旁路可写文件代可信提交。

Integration：同一精确Native grammar/角色 source/key基础设施/producer-root bootstrap与真实安装、Owner/drain、peer/原成员保持、v2 wire/v3 committed reader/Registry；搬运完整原材料与真实签名，不持独立工作签发权。Test真正suite/check两个单职责入口及实际有限工作/逐refproof；Review/Acceptance按原职责实际独立工作。Media无需新DTO/根管理scope，消费原registered输入/Operation，不自行生成proof。

错误区分：缺实际source/报告/资格/父关联未实现为原精确503/NOT_READY；实际伪源或跨能力403；未知格式/非法投影422；同key/body冲突、竞争父、current/epoch/root/CAS变化409；unknown Operation/签发/commit保核实状态，不能吞EngineError成null。真实失败报告可形成真实工作证明，完整资源validator仍拒绝pass资格。未实测时不得声称两个source、Owner替换、平台、媒体或生产阳性已通过。

独立后继至少验证：S/C同Test但两资格可合法先开始，未有报告不需未来proof；错S/假attempt/过期或撤销C不能capture；真实失败/unknown不签pass、不换key费用。多Binding/多case分片投影、observation唯一父、错case/sectionSHA/竞争父/遗漏伴件拒绝；七伴件不独立冒role报告。真实T/I1/A→Owner接受I2/B→H仍I1、C只I2；未被action接受的同锚I2拒绝；root/current在writer前改变整事务rollback；合法ACK丢失/恢复无第二接受事件，unknown不当absence。旧action/原字节V1兼容、不丢红结果、不降低独立角色/完整验证。

这些是待Test/Review定义并独立执行的需求，不改oracle、不授运行。本阶段InputPins/普通件/ActualInterfaces/Delta/Impact/Handoff记录实际停止来源及read范围；完成自然工具终态后只交独Review，后续实施与完整R1→R2验收保持OPEN。
