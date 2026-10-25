# ADR 0066：真实资源覆盖报告与 Owner 安装替换

状态：DESIGN_ONLY_READY_FOR_INDEPENDENT_REVIEW。本合同未经独立评审，不授予应用候选补丁、安装资格、模型调用、SQL 或生产运行。旧 ADR0063/0064/0065、首次安装十字段、质量门槛和历史失败原字节保留。R1 完整闭环独验后连续 R2；本合同不是产品完成声明。

## 1. 固定事实与唯一增量

主要输入为 Backend/DiagnosticResourceCompletionImplementation 的 QualificationCoverageGap.md（76c53e2a）、InputPins.json（b5abe04d）及其 23 个停止普通输入。原 trust.verify_record 读取材料用途、签名、完整文件映射和当前有效期，却没有 suite/check/review/acceptance 的实际 body 覆盖解析。原 InstallationRecordAdmissionSource 仅支持 installation-record-admission / admit_record；原 consumer 明确拒绝已有 Owner/record 的首次安装。原 Registry.retire_current 返回 ()，不能被序列化成“已 drain”证明。其真实 Lease Drop 会等待原 OwnedProcess 退出和 Job 后代为空，这一保证必须保留。

唯一增量是两套私有协议：在原 QualificationRef 和用途 map 内解析真实覆盖闭包；在原安装发行者/Registry 内建立独立 Owner replacement 来源和 drain 成员。两个 Partial candidate 只做准备，未被当成生产实现。所有公开 DTO、持久 schema、SQL 和唯一 parser 由 Backend 实现；Integration 实现原生来源和对称消费者，不能各自发明同名不同语义。

## 2. 四类报告的严格原始 body

### 2.1 共同语法与无环绑定

新增解析仅用于 ADR0063 资源完成资格分支；不要求重构与该资源无关的所有 runtime/license 报告。旧安装报告仍可供既有安装逻辑读取，但未知资源格式不能产生 completion，也不能作为可信 absence。

以下 body 均使用原 strict canonical JSON：UTF-8、递归对象键排序、紧凑分隔符、禁止 NaN/Infinity、重复键、未知字段、宽松数字/布尔转换；字段类型沿用原 Identifier、Sha256、QualificationRef、PositiveI64。解析后重新编码必须与真实 held 原始 bytes 完全一致。单文档、材料数量和合计 bytes 继续受原材料及帧上限限制；不得为了新增报告提高上限。资源报告本身仍为 ADR0063 的 2 MiB 上限，材料合计保留原限额。

共同 ResourceCoverageBindingV1 的 exact 字段为：registration_sha256、resource_manifest_sha256、runtime_manifest_sha256、diagnostic_catalog_sha256、method_ref、target、full_file_map_sha256、engine_partition_sha256。method_ref 必须完整复用 ComponentDiagnosticMethodRefV1，包含 implementation_source_refs、rule_template_sha256、完整 route、model_binding、check_kinds 及资源/runtime SHA；不只比较 method_id。target 完整复用 QualificationTarget。binding 不含未来 report/ref、record/ref、action 或 completion，避免自哈希循环。

每个聚合 body 的 coverage 为 1..16 个 section，按完整 binding 的 canonical SHA 排序且唯一；不同目标/方法不能共享一个 section。一个签名安装 record 的同一 suite/review/acceptance ref 可以覆盖多个真实方法，reader 必须定位恰好一个完整 binding 相等的 section。没有该 section 即未覆盖；不接受“整个包已 passed”推导。所有 refs 都必须是原 held 材料索引中对应 purpose 的 exact ref，并通过 size/SHA/path/current 两侧检查。

四类 exact 顶层字段如下。producer_ref 指向原已准入 publisher_provenance 或 local_verifier 的 verifier_code_index 材料，类型和用途由原 trust_mode 决定；不是新 issuer。producer 的真实职责/代码/执行来源由原准入 provenance 和其实际固定证据绑定，不能靠 body 内一个 role 字符串证明独立性。

| 原 purpose | format | 其余 exact 顶层字段 |
| --- | --- | --- |
| qualification_suite | diagnostic-resource-qualification-suite-v1 | producer_ref, coverage |
| qualification_report | diagnostic-resource-check-report-v1 | producer_ref, suite_ref, coverage |
| independent_review | diagnostic-resource-independent-review-v1 | producer_ref, suite_ref, check_report_refs, coverage |
| independent_acceptance | diagnostic-resource-independent-acceptance-v1 | producer_ref, suite_ref, check_report_refs, independent_review_ref, coverage |

有向闭包为 suite → 已固定 criterion/source；check → suite/真实执行材料；review → suite/check；acceptance → suite/check/review；ReadinessReport → 上述四类。后三者不得引用 ReadinessReport、未来 installation record/action/completion，也不得互相反向引用。各 body 必须独立有真实 bytes；一个字段不能同时充当 review、acceptance 或 check。所有闭包 refs 在同一受保护材料集合中可解析；缺 ref、循环、重复 ref、用途错配、合计超限均拒绝。

### 2.2 Suite section 与真实 check section

Suite section exact 字段为 binding、cases。cases 按 check_id 排序、唯一、非空。CaseV1 exact 字段为 check_id、check_kind、criterion_ref、case_source_ref、required_observations。check_kind 只取原 method_ref.check_kinds；precision_boundary/cover_frame/narration_source/mix_source/visual_source/ambient_source 的既有语义不变。criterion_ref 是已独立批准的固定 criterion 材料 QualificationRef；case_source_ref 复用原 RecipeSourceRef，绑定真实执行脚本的资源名和 source SHA。不得把模板说明或文档中的预期结果当成执行证据。

required_observations 是下列固定枚举的有序非空集合：resource_load、bounded_call、result_consumption、route_source_binding、current_invalidation。一个 section 的 cases 合集必须覆盖全部五项，并覆盖该方法全部 check_kinds；一项 case 可以覆盖多项，但每项都须有实际记录。该集合是资格证据维度，不改生产质量阈值或用例 oracle；Test 仍是 criterion 和实际测试代码唯一 owner，Review 必须独评 criterion/source 是否真的实现所声明的维度。

Check section exact 字段为 binding、results。ResultV1 exact 字段为 check_id、case_source_ref、started_at_us、finished_at_us、execution、outcome、observation_ref、failure_code。execution 仅 real/synthetic/not_run；outcome 仅 pass/fail/error/skipped/not_run；failure_code 对 pass 为 null，其他为非空原错误码。observation_ref 对 real 非空，其他可为 null。real 要求 finish ≥ start，case_source_ref 与 suite 完全相等，实际 observation 文档真实存在。synthetic、skipped、not_run、error 不可算通过，即使字段 outcome 被写成 pass 也拒绝。

observation_ref 仍用原 QualificationRef/purpose=qualification_report，指向 strict diagnostic-resource-check-observation-v1。其 exact 字段：producer_ref、binding、check_id、case_source_ref、execution_id、started_at_us、finished_at_us、observations。observations 的 key 集合必须与该 case.required_observations 完全相等；以下 value 使用 exact grammar，不容任意 dict 或 callback 返回 bool：

- resource_load：loaded_source_refs（原 RecipeSourceRef 有序唯一集合）、loaded_file_map_sha256、actual_target（原 QualificationTarget）。必须与原方法/source/完整文件映射/目标相等，不能只有预期 import 名。
- bounded_call：request_ref、result_ref、operation_ref、deadline_us、finished_at_us。request/result/operation_ref 均为真实 qualification_report 材料 ref；operation body 复用实际原 Operation/Step/Observation 的固定导出 grammar，必须为 succeeded/settled、有真实结果和该 method/route/input/output SHA，且完成不超过实际 deadline。text 方法仍需真实授权的模型执行；本合同不授予费用。owned_local 方法原零成本/无 credential/model 约束保持。
- result_consumption：result_ref、consumption_ref。必须同 bounded_call 的实际 result；consumption_ref 指向真实原生产消费入口的固定执行收据，绑定该 result SHA、消费者实际 source ref、当前 method/route/input，实际解析/消费成功。仅能 import 或有文件不能代消费。
- route_source_binding：actual_method_ref（完整原类型）、loaded_source_refs、actual_route（原 CapabilityRoute）。逐项等于 binding/已 held 方法源码；仅参数宣称 expected 不能代真实观察。
- current_invalidation：before_source_ref、after_source_ref、attempt_ref。三者指向真实源观察/变更后受控尝试收据，必须同实例/方法/完整资源关系，记录真实失效后拒绝且没有新增提交/收费/完成事实。不能用伪布尔 guard 或没执行的“应当拒绝”。

原导出 grammar 是当前真实执行源的原 strict 类型/固定版本，不在这里另造 Operation DTO；Backend 必须将其确切版本及 protected reader 暴露给 qualification parser，Integration 必须同源消费。原观测材料尚未有可解析导出或 raw receipt 实际无法绑定时为 missing/unrecognized，不能给正向资格。Test 负责实际执行及原始收据；负责该源的 Backend/Integration 只负责真实导出，不自写测试通过结论。

Suite 每个 required case 必须且只能匹配一个 real/pass Result 和完整 observation；不允许从几个报告挑有利子集。check_report_refs 可以含不同 case 的报告，但同 case 冲突、重复执行结果或遗漏必须拒绝并返回精确缺口。ADR0063 passed_check_ids 必须等于该 section 的完整通过 case 集合；数组只能作为索引，不能代 body 检查。

### 2.3 Review / acceptance section 与共享 validator

Review section exact 字段：binding、reviewed_check_ids、criterion_refs、case_source_refs、findings、conclusion。findings 的 item exact 字段为 finding_id、priority（0..3 strict int）、state（open/closed）、evidence_refs（非空 QualificationRef 集合）。conclusion 仅 supported/rejected/incomplete；supported 要求覆盖该 suite 全部 cases/criteria/source/真实 check 收据，无 OPEN P0/P1/P2，且原实际 Review 来源确为独立角色。未审、仅 source-static、未知执行材料或范围不全只能 incomplete/rejected，不能宣资源资格通过。

Acceptance section exact 字段：binding、accepted_check_ids、executed_check_report_refs、conclusion、unobserved_check_ids。conclusion 仅 pass/fail/incomplete。pass 要求恰好覆盖全部 suite cases，unobserved 空、真实已独审 supported、实际 executed reports 与本 ReadinessReport/check/review 的全闭包一致。真实 Acceptance 角色独立读取并确认同一平台/资源/方法/报告；没有真实验收源时不构造 pass。一般“产品验收通过”或其它平台报告不能代本资源绑定。

Backend 唯一新增共享函数语义：verify_resource_coverage(*, trust_source, readiness_report, qualification_record, at_us, usage) → PreparedResourceCoverage（eq=False、不可由 DTO 构造）；usage 仅 historical_acceptance/current。函数在 SQL 外通过原 held materials 的 read_required_ref(ref,purpose,limit) 逐件读 raw bytes，验证所有 SHA、canonical、grammar、无环全闭包、完整 binding、cases/实际结果和独立来源，然后 before/after assert_current。不得注册任意 bool validator。Native 用同一冻结 grammar 的对称验证，不能只接受 Python 回一个 true。

PreparedResourceCoverage 只携带原 source/epoch/线程真实成员、实际解析对象/refs、checked_at_us、usage 和该 source.assert_current；短 writer 只消费这一个真实成员并重核原 captured SQL/source 事实，不做管道、文件 I/O、模型或测试。缺 body/未知格式/缺真实 producer 资格明确 not_ready；已观察失败、错用途/签名、伪结果/冲突为 rejected；不能将其转换成 zero-report absence。报告仅表示该安装资源资格，不替生产作品独立精度报告/版权授权或 Owner 计划批准。

H 使用原 action 的真实 accepted_at_us 验证该时刻有效性和实际提交闭包；C 使用现在真实 current record/revoke/floor/许可和完整覆盖。H 依赖的原报告不能在 replacement 后靠 C 的新 bytes 补成历史。Backend 在原 completion 同一 SQL writer 内扩充原 metadata archive：只存本 completion 实际使用的 suite/check/observation/review/acceptance/criterion/provenance 必要报告 closure 的 exact bytes/ref/purpose 和原提交关联；不存全 runtime 树、密钥或任意用户文件。仍受原材料数/bytes 限制。归档是历史事实，不是当前权力。旧 H 无这些真实 bytes 时仍 historical_evidence_unavailable；不猜通过。自然到期按 H 原时刻与 C 现在分别核，真实资格/权利撤销不能被新 C 洗掉。

## 3. 独立 Owner replacement 来源与 closed wire

### 3.1 保留首次安装，单独声明更换动作

InstallationRecordAdmission 原十键/kind=record_admit、原 purpose/locator、admit_record request/reply 和首次无 Owner 检查完整不变。更换不能从 ProductionInstallationAuthority、ordinary worker/agent/MCP、renderer bool、NativeOwnerServices 的 DTO 类型或已有管理绑定自动提权。

新增 sole Backend 私有 InstallationRecordReplaceRequestV1 exact 字段：format=installation-record-replace-request-v1、action_id、kind=replace、trust_admission_ref、expected_registry_revision、expected_record_ref、expected_revocation_floor、expected_owner_binding_revision、expected_material_index_sha256、record_ref、record_sha256、material_index_sha256、host_build_receipt_sha256、intent_sha256。record_ref 是完整新 record 的真实 QualificationRef。expected_record_ref 非空且必须为当前真实旧 record；同 issuer/trust admission、不跨实例，旧→新 revision 单调。三个完整资源 SHA/fullmap 等从真实新 record 消费，不从 renderer 推导。

intent_sha256 是本 request 去掉 intent_sha256 后的原 strict canonical SHA；不含接受时间、OS 临时会话或未来 request/event/completion SHA，避免回填循环。整个 request 的 canonical SHA 用作原 control.reserve/commands 的幂等 request SHA。action_id 仍原真实 Owner 动作幂等键，同 key 不同 bytes 为 409。

新增 InstallationRecordReplacementV1 exact 字段：format=installation-record-replacement-v1、accepted_at_us、request、record、owner_confirmation_ref。request 为上述完整类型；record 为原 InstallationQualificationRecord、canonical SHA/ref 完全匹配 request。owner_confirmation_ref 采用原 metadata 三字段 record_id/content_sha256/size，精确指向真实原生 Owner 确认收据 bytes，只标识实际确认材料，不是可从 JSON 获权的 carrier。真实 Native source 保存该收据 bytes、实际 OS Owner/session/action/member/同实例/可信 image/current 关系；没有这一成员不得实例化 Prepared replacement。

Owner 确认沿原已准入宿主的真实 OS SID/session、OwnerDirectory、可信 image/build receipt/同 instance/原 Owner 管理绑定来源。Integration 在原 native Owner 确认 UI 内显示真实旧 record/ref/revision/floor、新 record/full资源覆盖差异和本 intent，真实点击才创建 RecordReplacementOriginal 强成员；Linux headless 保留原真实 TTY/OS Owner 确认路径，不能伪造 isatty。首次配置不能重复提示日常每 Project；仅用户实际请求替换安装资源时确认该管理动作。source 的权限只有该 request，不增生产 plan/费用/发布/任意管理 scope。

### 3.2 连接身份与闭合消息

新 purpose/role 固定 installation-record-replacement；Windows locator 保留 original exact 六字段 pipe/session/role/server/purpose/instance_id，pipe 前缀 VideoCreator-InstallationReplace-，server 保留 pid/creation_filetime/sid/image/image_sha256。factory 必须沿原受保护启动实例来源核对真实 peer、creation、SID、image/hash/build、同 instance 和 Owner 管理来源；排除初次 setup-only source 和非本目的连接。JSON 仅载荷，不是身份。非 Windows 按已批准 POSIX 等价强来源实现，缺实现/实机保持未资格，不放宽成 socket 路径身份。

wire 固定 held-installation-record-replacement-v1；4-byte little-endian 长度 framing、原帧/字节上限、strict canonical、连续正 seq、单 request 同原一次 reply、拒绝多余字段/版本/方法/重放。每次 exchange 的原 10 秒 deadline 保留；Owner UI/任务等待不得借长帧或在 SQL 内等待。

request exact 公共头：wire,session,seq,method,instance_id。仅四种 method，额外字段封闭：

| method | 额外 request 字段 | success payload |
| --- | --- | --- |
| prepare_replace | request_sha256 | replacement（完整 InstallationRecordReplacementV1） |
| assert_replacement_current | action_id, request_sha256 | assertion（下述 ReplacementAssertionV1） |
| confirm_committed_replace | action_id, request_sha256, committed_evidence_ref | confirmed（下述 ConfirmedReplacementV1） |
| recover_existing_replace | action_id, request_sha256 | recovery（下述 ReplacementRecoveryV1） |

reply exact 公共字段 wire,session,seq,status,code,instance_id，另恰好该方法 payload key。错误 status 仅 403/409/422/503，payload=null；不得用 200/null 表示“也许已完成”。成功 code 分别 replacement_prepared、replacement_current、replacement_committed、replacement_recovery_observed。外部可见 binding 描述是 identity 数据，Native 的 Arc/drain/Owner/action 注册表才是权力成员。

ReplacementAssertionV1 exact 字段为 action_id、request_sha256、instance_id、from_epoch、to_epoch、stage；stage 仅 prepared/backend_committed/native_committed，epoch 为原严格非负 I64 且 to_epoch > from_epoch。实际 Native handler 只从该受认证 session 注册的同一个 Owner/action/drain 成员取值并检查原 accepted UI action deadline、OS/session/Owner/source 当前性；不能接受 caller 回传 assertion 或只对照 descriptor。断连/失效/重放即不可借用成员，未进入 writer 的 action 原生确认有效窗沿用原 120 秒。

ConfirmedReplacementV1 exact 字段为 action_id、request_sha256、record_ref、registry_revision、revocation_floor、committed_evidence_ref。只有 Native 真正读受保护 committed evidence/control/snapshot、重建全部报告与 action、完成 Registry.install_committed 后才可产生。它是完成事实，不单凭 reply 授资格。

ReplacementRecoveryV1 exact 字段为 action_id、request_sha256、state、replacement、committed_evidence_ref、confirmed。state 仅 prepared/backend_committed/native_committed/unavailable；相应非空关系为 prepared 仅 replacement 非空，backend_committed 为 replacement 和 committed ref 非空，native_committed 三者非空，unavailable 三者全 null。不能把 RPC 失联推成 not_committed，也不能靠这个 descriptor 在新进程造原 Owner/action/drain 成员。

## 4. 真正 drain → 同原 writer → 恢复

### 4.1 Registry 强 drain 成员与锁序

Integration 在原 Registry 新增 retire_for_replacement(*, action: Arc<RecordReplacementOriginal>, deadline) → RetiredQualificationDrain。这是私有不可序列化成员；保留 retire_current 的旧 () API 兼容。RetiredQualificationDrain 绑定同 Registry/installation Arc/instance、action 的完整 request SHA、旧 record/revision/floor/material index/source、from_epoch/to_epoch，以及实际所有旧 qualified consumer session 的 OwnedProcess/Job 终态观察。返回前必须关闭新 lease、拿到原 try_write、实际退掉 current source/其 mutable Control/material holds，epoch 单调且旧观察/会话 ID 失效。仅 ClosePipe、gate=false、()、空自报 PID 数组、线程退出或 JSON drained=true 均不满足。

原生产 writer lease 的 readguard/OwnedProcess/Job Drop 保持：实际 parent wait_exit 且真实 Job 后代为空才释放。所有原 qualified session 在原绑定处加入 Registry 已有实例内消费者集合，drain 核该集合的实际 terminal 而不是猜全机进程。新 replacement 管理 child 独立于旧生产 lease/Job，不能等待自己；其权限只该管理 action，不能执行生产。真实无法观察某旧 child/Job、超时或未释放 held mutable 文件时不返回强成员、不提交新资格，不强杀未获授权的工作。

不得在持有 Backend SQL writer、control.lock、安装文件锁/待被 retire 的旧 mutable holds 时等待 Registry/Process/Job。实际已生产的 Run/Operation/unknown 不取消、不清除、不换 key；worker 先按原 heartbeat/checkpoint 停止领取新尝试并保留真实结果，尚有活尝试就等待真实结束/既有受控关闭。payload 不同的新安装不是活动 Run 的无缝重绑，本合同不授改其 inputs。

新报告和材料可先在原 Owner 受保护、按真实 ref 命名的不可变版本目录准备；旧已签资源文件不原地覆盖，全部 pins/许可检查保持。即使仅补报告而完整 map 相同，仍必须真实 release 会被更换的 Control/index current holds。drain 后 action source 继续持有原真实 OS/session/image/build/Owner 来源和新候选 immutable materials，不依赖已退休 Production current guard。

Backend 的新 eq=False InstallationRecordReplacementSource 只能由该目的真实连接 factory 创建；其 consume_replace 返回 PreparedInstallationReplacement，包含原 Native Owner/action/drain 强成员的受认证连接关联、完整 replacement/实际报告覆盖、原 SQL/控制观察 captures。它不是将 reply JSON 包装成合法强成员：SQL 外 assert_current 必须经 assert_replacement_current 和原真实 peer/member/epoch/Owner 校验，Native 同步核其原 action+RetiredQualificationDrain 注册成员仍有效；只接受准确 request/source。该 source 的 writer 内 assert_writer_current 仅核原已注册 Python 成员/线程/连接本地生命周期和原 Owner/current SQL captures，不进行 RPC；原生借用 action/drain 成员在管理 session 生命周期内保留，不能释放成员而继续回 success。writer 后再做真实外部 current 校验和完成重建；失败不能宣 Native qualified。原 trusted issuer 不变。

### 4.2 原 consumer 增量与两个实际 callers

Backend 唯一 consumer 新方法 replace_record(*,engine,bundle,bound_replacement_connection)；原 admit_record 原样。真正 caller 是用户实际发起的 Native 安装资源更新管理动作，经原 native owner session 启动/绑定专用 Python 管理入口，然后调用 replace_record；普通生产服务、agent 和启动全局扫描不得自动调用它。

实际顺序：原生真实 Owner 确认及新材料 held prepare → 原 Registry retire_for_replacement/强 drain → 受认证 prepare_replace → Backend SQL 外完整报告 validator/current/许可/target/map 检查 → 原 control.reserve(expected revision,request SHA) → 原短 writer 重核 expected_current 和 source captures → 原 record/event(kind=replace)/commands/current/资源报告闭包 archive/completion set 原子提交 → 原 v2 committed export/snapshot/control.complete → confirm_committed_replace → Native 独立读/验证相同 set/body/全报告并 install_committed。

writer 精确 expected_current 为原实例、当前 trust admission、旧 record/ref/revision/floor、Owner binding revision、旧 material index 的真实 SQL/control captures，全字段 CAS；不是只 revision。new record/signature/fullmaps/用途及 coverage 在外面已验证，writer 只校验真实成员/current、准确重核本地 captures 和有效期，失败整事务 rollback。实际更换事件不能沿 record_admit 分支伪装首次准入。completion 与报告 archive 同事务，committed export 后重建仍须真实当前 Owner/source/target/map/报告，不凭 sidecar 完成。

InstallationActionRequest 的旧 grammar 不改；replace 的原 command/event 读者新增明确 request format dispatch，只接受本 strict 新类型。CommittedQualificationSource 的 action 字段新增封闭原始成员 variant（RecordAdmissionOriginal 或 RecordReplacementOriginal），分别检查 kind/expected captures，不能任意 kind 字符串。NativeQualificationTrustSource、original consumer、v2 exporter、native completion reader/Registry 只在这个真实新目的 branch 增量，旧入场 caller 全保持。

第二 caller 为用户真实发起或原同存活 management source 的 resume_existing_replace；只恢复原 action/request，不新建 action/record/revision 或收费。Backend 先受控读取原 commands/event/current/已归档 record/replacement，和原 reserve/snapshot/export floor 比较：

- 同 key 不同 request SHA 或原 immutable bytes 冲突：409；不得覆盖旧 command。
- SQL 未提交且原 source/drain 真实有效：按同 reservation/同 request 继续原 writer，不重复准备测试/模型；drain 不可复用失效成员。
- SQL 已提交但 export/snapshot/floor 未完成：原实际 event/record/request/报告 bytes 证明提交后，原受认证 management source 只完成原可信导出/control 收尾，不重做 SQL replace。若原能力 source 丢失，必须通过原 Native 真实 Owner recovery 确认建立仅该已存在动作的新 recovery 成员，历史 receipt 只用于核事实，不当当前确认。
- floor 完成、Native install 未确认或 ACK 丢失：recover_existing_replace + protected body reader 精确查原提交；同 current 只原 Registry 重建/确认，无第二事件。成功需实际当前 qualified source 而非 reply 状态单独推导。
- SQL 是否提交或原源事实未知：unknown 原状态保留，禁止新 key、下一 revision、清 pending、或把异常吞成 absent/not_committed。原 immutable source/材料缺失时返回准确 missing；允许实际补回相同 bytes 后恢复，不猜历史。

新进程不能从序列化 receipt/文件制造原 Arc、Owner 点击或 drain；可由真实 Owner recovery 动作确认完全相同原 canonical request，建立新的受限当前来源。若原 writer 未提交，先实核旧 record 仍 current 和旧 revision/floor，再重新真实 drain；若原 writer 已提交，核当前恰好为该已提交新 record，只准收尾，不再 grant replace。新确认是恢复权限来源，原 accepted_at/event bytes 保留；不得改历史时间或复活旧 grant。需要原 pending request 完整 bytes 却找不到时维持 unknown，不能只由 request SHA 反推。正常已有记录的 replace 与已提交恢复要真实实现，不能永久返回 503 代需求。

## 5. 实施接线与独立证据

| 角色 | 最小实际实现 |
| --- | --- |
| Backend | 原 domain 唯一 four-body/observation/replace grammar；原 trust held body reader +共享 coverage validator；原 installation consumer 独立 replace/resume；commands/event dispatch/current CAS；原同 metadata archive closure；original qualified issuer/member/source captures及 v2 export。不扩大旧 admit 或让生产 guard 管安装。 |
| Integration | 原 provenance/materials exact body 同源 reader；真实 Owner UI/TTY replace/recovery carrier及新 purpose pipe；Registry 强 drain 与真实 consumer Process/Job 集合；原 committed action 封闭 variant；Native 独立 coverage/完成重建。保三 OS 原强身份、许可和完整能力。 |
| Test | 原 criterion/source oracle；实际 suite/check/observation 及 raw receipt 固定材料；执行真实正反后输出原独立测试事实，不能提前生成通过报告。 |
| Review / Acceptance | 各自产真实固定 body/来源与实际独立结论，评审该合同后再评审实现/执行；不能以此文档替它们的实际报告。 |
| Media | 只继续原 completion/current 消费 ABI，不生成 suite/Owner source/drain 或重复资格 DTO。本卡不重做0065角色/lineage。 |

最小独立正向证据：真实同 binding 多方法聚合报告可准确选中；原 source load→bounded call→实际 result consumer→route/source→失效拒绝全部 real；原初次十键仍工作；真实已有 Owner/record 的新替换使用专用管理 source，旧 Process/Job drain、新 record+set+archive 同一提交；H 留原 A 后 C 真实 replace 补 B 可同 Run 继续，原 Operation/费用不重复；SQL 已提交/ACK 丢失和冷重启仅受控收尾。

必须的负向：purpose-only/签名-only/数组 passed；unknown format、缺 section/body/receipt、synthetic/skipped/failed；错 check/source/route/model/target/fullmap/criterion、反向 ref/cycle、冲突结果、source-only review/无真实 acceptance；H 缺原 bytes/C 真实撤销；Production/agent/renderer 假 Owner、初次 source 用 replace、错 OS peer/session/image/SID/instance/purpose；JSON drained、活 parent 或 Job 后代、超时/断连/drain 成员失效；同 key 不同 bytes/expectedcurrent CAS 冲突；SQL rollback/部分 export/pending floor/未知提交；文件 sidecar 或新 manifest 冒资格；新进程仅凭历史 receipt 复活旧权限。所有原 unknown/reconcile、两 authority、精度200ms、原预算和角色审批保持。

本阶段只形成可审合同。四种原始 report、实际 admission/replace provenance、所有 OS 通道和独立测试尚未据此运行或资格通过；具体缺件须作为 not_ready 原因交下一 owner，不能由宽松 parser、bool 或永久不可用占位替代完整实现。
