# ADR0068：覆盖资料的实际独立生产者与原成员交接

状态：DESIGN_ONLY_READY_FOR_INDEPENDENT_REVIEW。仅补 CoverageProducerAdmissionContract 的停止缺口。未授候选应用、签发资格、业务运行或费用；不改0063—0067、测试 oracle 或公开业务 DTO。完整 R1 独验后连续 R2。原137候选仍 NOT_FOR_APPLICATION，本文不能关闭功能 finding。

## 1. 固定事实与唯一增量

ProducerAdmissionGap 三完整普通源已全文读：native_qualification_trust.py=3f849a3b952d523cf8e6fa23162425902f375029ee7b65b3dd040bba342d12ec；qualification_coverage.py=febc1e82ce88e807449cc88e70c06414b8a9a4f6fa0d3eebaa699ce0f8e5ea30；diagnostic_resource_coverage.py=84f9042301940f234e37164570eb5cb08c6d874377c8b7a6c69e8427ce03bf99。Gap MD=a49d3a2657293e7a04e4416d358f611e62a8a46627566e2bbe5b53b790f7a215，JSON=b91192d7dc103e194598b51be09c57be9ea17d242fd19b066d120518af04c526。

最新停止137源索引 d9caae274bb9c6a26fc23de77e3ce2a7125939b78e9d259c9b88ae0e2ee2457d。ActualInterfaces=5c1d6bc9fd0d0506912649c55a912c045aacae64efdf6b72454f591716e75608，Impact=b2826cf46d57443105bc06e6fc266e6121357f51e248abf8eb98b1520f023164。必要最新成员方法读自其完整普通副本：NativeTrust=a0d54a13fc3b114a191295dab554ed3d4032056842e24727aa616c047a878175、CoverageReader=309701109142b8d3e1bb8c8099197da4b616b4c90f3e37310e58a32cf9b172e6。原 TrustAdmission/消费者分别 c317c9b0fb8122a74149bdb6dab594b480a3f5e4688c63f3e70837d7c21c3996 / 40317c88df1b01290c04c594d213340e6421118f538f60069ebd7be223f2dbba，均完整读。并非全文审查137源或106790B产品 diff。

追加停止Native接口全文输入仅四件：Interfaces.md=0053be86ccb66a66a7404468ffbe9f618193d9fcd436ed8f47e7b5b6c67fa70f；MissingProductionSeams.md=087da413ef64edd089f256863f01aaad3cc4ac828b8963bef39b6e49d0a102fa；Impact.json=4f5f4b094fe6aa3ba168a248471dad76cb263937c78fde32782e0c37cb5bf953；FormalStageRevisionTwo/Handoff.md=b501e555cd2cb93480416fcea1ce307d05a210ea7b8ee37bf16ba3e78159ebfc。它们定位原45源未应用接口，不替代其source全文/编译/运行，不读取另一个热修正窗口。

原 TrustAdmission 是真正 Owner/安装 action 接受的锚；QualificationMaterialsIndex 五字段仅绑定原 held ref/path/bytes/purpose。原 _TOKEN 工厂及 OS peer、安装图、protected floor/current、epoch/thread 真实存在。最新候选已有 read_required_ref、prepared coverage 注册/local检查及执行捕获接点，尚没有四职责实际 producer admission/proof 工厂。角色名字、不同 SHA、签名、source 字段、回调返回 True 或空 registry 都不能补这个缺项。

增量只为原 publisher_provenance / verifier_code_index 加三种封闭文档及原工厂私有成员方法，使用同一原 Ed25519 锚、材料 holds、Owner 接受 action 和 current/local 链；不另建登录、资格服务器、公共角色 mint API 或第二授权系统。角色签发端和安装验证端分开。既有 suite/check/observation/review/acceptance/七伴件原字节和 grammar 不变。

## 2. 实际职责、合法阳性与信任边界

| 职责 | 唯一实际生产者 | 必须完成的实际工作 | 可签发内容 |
| --- | --- | --- | --- |
| suite | 测试开发的已准入 suite 生产入口 | 固定原 criteria 和实际 case source；完整 Binding、check kinds、五观察维度闭包；冻结后不能按结果改期望 | suite 原 body + suite work proof |
| check | 测试开发的已准入执行入口 | 使用真实原登记资源、原许可/租约/Operation/有限费用，实际执行每 case；真实 target/load、request/result/settled/消费及失效反例；保所有红/unknown | check report、实际 observation/七伴件引用 + check work proof |
| review | 原独立评审入口 | 只读冻结标准、case/source、所有结果和完整伴件/许可；逐项来源判断、finding 与结论；不能改执行结果或标准 | review 原 body + review work proof |
| acceptance | 原独立验收入口 | 按冻结标准独立观察/运行原准入入口，读同一完整 check/review；真实 target、影音与职责范围内观察；未观察不通过 | acceptance 原 body + acceptance work proof |

suite/check 可由同一 Test 主体、同一受保护 Test key 持有者完成，但是两个明确入口和两份职责资格。Review 必须独立于 suite/check 的执行与标准修改主体；Acceptance 必须独立于 suite/check 与 Review 的签发主体。独立性是原可信发行/本地验证 source 实际登记的不同责任主体、不同 role signer key、不同只读/执行能力边界及各自实际工作，不以不同进程、文件名、任务名、哈希或一句 independent=true 替代。共享机器或 OS 用户不自动否定独立角色，也不证明独立；同一通用任意签名器给四种字符串换名不合格。

Integration 实现受保护 key/held source 基础设施和角色入口的原连接；Backend 实现唯一私有类型、封闭解析、验证和 archive。二者只能验证/归档真实角色产物，不可持 Test/Review/Acceptance 的工作签发能力，不可代其生成 pass、findings 或实际执行证据。发行锚可授权一个真实职责 source，不能用锚签名代替该 source 已完成工作。

合法阳性有两条同 grammar 路线，不强加产品注册或逐作品确认：

1. 正常发行：真实独立 Test→Review→Acceptance 在已授权的发行验证实例完成工作，各自产出原正文和角色 work proof；发行锚只签职责资格和完整 producer index。Integration 原成包入口携带这些完整 bytes/refs；安装实例真正 Owner 接受原 TrustAdmission 锚和完整安装 action，原工厂验证后进入原 record_admit/当前资格/资源准备。用户不需要装开发工具或执行四组命令。
2. 原 local_verifier：一次真实 Owner 接受原 verifier_code_index/anchor_generation 和其中已审受限入口。使用安装实例内预配置的独立 Test/Review/Acceptance source；新增资源按原资源 action 执行其有限实测/审验，再由原 Owner/current writer 提交。入口及 signer 必须实际实现并具备原许可/安装/source资格；不能让模型提交 role/proof JSON，也不要求用户填写内部 proof。没有本地独立 source 时该具体资源 not_ready，下一任务必须实现 source，不把此状态宣成产品完成。

两路都不能免费凭空生成付费验证；原 CNY/限次/unknown账本持续共享，unknown 只能 reconcile，已有不可变结果不重做/重扣。报告 pipeline 的权限不授普通生产、新模型、发布或账户管理权。当前独立 source、key custody 与完整 publisher/local生产接线均 NOT_IMPLEMENTED/NOT_VERIFIED，不声称有真实阳性。

## 3. 三种唯一文档、primitive 与签名

只注册以下 format，全部使用原 canonical_bytes / parse_exact：UTF-8，递归排序 key、compact、完整显式字段/null、无重复 key/NaN/Infinity、无额外字段。整数均 strict，bool 不作整数。Identifier、Sha256、PositiveI64、QualificationRef、RecipeSourceRef、ResourceCoverageBindingV1、QualificationTarget 均复用原定义。Ed25519 public key 64位小写hex，signature 128位小写hex。单件 ≤2MiB，原完整 closure ≤4096refs /128MiB，不扩大原材料 bounds。

### 3.1 diagnostic-coverage-producer-admission-v1

exact 字段：format、producer_id、revision、issuer_id、trust_mode、anchor_key_sha256、host_build_receipt_sha256、bindings、role、principal_subject、role_source_id、role_public_key_hex、producer_build_ref、source_definitions、entry_module、entry_callable、allowed_formats、valid_from_us、expires_at_us、possession_signature、anchor_signature。

role 仅 suite/check/review/acceptance。bindings 是完整原 Binding tuple（1..16，按原binding canonical SHA排序唯一），明确有限范围，保原AggregateV1一个producer_ref可覆盖多个section；不强迫把原多方法报告拆成单方法或授wildcard。请求binding须在其完整集合内，3.2仍逐binding证明实际工作。principal_subject/role_source_id 是实际可信 source 登记的 Identifier，不由报告作者选名获得身份。producer_build_ref 为原实际受保护 build_provenance QualificationRef，完整读取/验证其原发行 build receipt 和生产 source 图；不接受只填 hash、未知 body 或任意文件。source_definitions 为实际生产/解析/签发入口的完整已保护 RecipeSourceRef 集合，按 resource_name 唯一排序，须与 producer build/index 中的真实 source 图一致。不得用工作台/模型/后端通用签名入口冒独立 source。entry_module/callable 是该图中的实际固定入口，source 能力由原登记对象限制，不由两个字符串建立权限。

allowed_formats exact：suite 只有 diagnostic-resource-qualification-suite-v1；check 为 diagnostic-resource-check-report-v1、diagnostic-resource-check-observation-v1，及0067七个 exact companion format（按字典序唯一排序）；review 只有 diagnostic-resource-independent-review-v1；acceptance 只有 diagnostic-resource-independent-acceptance-v1。role work proof 是私有签发器的固定伴件，不是允许任意额外业务 body。

valid_from_us < expires_at_us，资格有限。host_build_receipt_sha256/issuer/trust_mode/anchor_key_sha256 来自真正被 Owner 接受的原锚/安装 source，不从新 body 自证。publisher source 的 producer build 与客户 host build 可不同，但两者完整 refs、原发行 provenance、目标 Binding 必须严格匹配，不能拿自编译工具证明未知 vendor binary。

签名投影：possession_signature 的消息为 canonical(all fields 去掉 possession_signature 与 anchor_signature)，由真实角色受保护 key 签；anchor_signature 的消息为 canonical(all fields 仅去掉 anchor_signature)，由原被接受锚签。资格 ref 的 SHA 是包含两签名的完整 canonical body。验证 possession 仅证明真实 key 持有关系，不证明独立工作已经完成；必须继续核3.2及实际 factory来源。

资格 source 建立顺序：原锚可信管理入口先实核实际角色主体、其受限 source/build/能力与受保护 key possession，再接受资格；不能提供接受 arbitrary subject/role/source dict 的 mint 方法。Publisher由实际受保护发行角色账户/任务source建立；local_verifier由已真实接受的 verifier source 对其固定独立角色入口建立。source私有注册表绑定实际 role source/key/entry对象，而非从 body 标签生成角色。Backend/Integration仅消费这一资格关系。

### 3.2 diagnostic-coverage-role-work-proof-v1

exact 字段：format、proof_id、revision、producer_ref、role、binding、report_ref、suite_ref、check_report_refs、independent_review_ref、source_definitions、work、started_at_us、finished_at_us、valid_from_us、expires_at_us、signature。

producer_ref 必须是3.1完整 ref，report_ref 是实际完整原报告的 ref；role相同、binding在资格完整bindings内。source_definitions精确投影该次实际source，须在资格已保护完整source图内，并完整覆盖原实际 capture/exporter/case/role消费者代码；不能凭源码SHA不同扩大资格范围。署名入口不能给任意 request caller 签其 JSON。原时序 started≤finished，valid_from≤started≤finished<expires；proof区间落在该资格有效区间内。signature 为实际角色 key 对 canonical(all fields 去掉 signature) 的签名。签名只能由下述实际已登记角色工作对象提交入口完成。

suite_ref/check_report_refs/independent_review_ref exact关系：suite 为 null/()/null；check 为原 suite_ref/()/null；review 为原 suite_ref/完整原 check_report_refs/null；acceptance 为原 suite_ref/完整原 check_report_refs/原 independent_review_ref。null 显式，不用无字段或空字符串。排序/唯一性沿原 ref口径。report_ref 指向对应 role 唯一原 format，整个 scope 一份报告的一次真实工作只配一份 work proof；冲突不能挑有利版本。

work 是 role discriminator 的封闭 union，exact如下；没有任意 evidence dict、passed bool 或 outcome callback：

- suite：kind=suite；criterion_refs（完整原 criteria refs）、case_source_refs（完整实际 case源）、check_ids（冻结全部ID）、case_closure_sha256（该 Binding 原 cases 完整 canonical SHA）。均与原 suite Section 全量计算一致。入口实际读取冻结标准/source、确认完整维度覆盖后产生，不能从用户给的四列表直接签。
- check：kind=check；execution_ids（该 Binding 全部实际 observation 的原 execution_id）、observation_refs（全部原观察 ref）、companion_refs（该范围实际引用的七伴件完整唯一闭包）、case_closure_sha256（原 suite cases）、result_section_sha256（实际原 CheckSection完整canonical SHA）。不把所需五维度写成已执行；每 case 的真实/红/unknown、时序、原 Operation/settled/费用/消费和失效副作用必须可由原报告及0067 set verifier逐项重算。制作失败保留真实 fail/error报告，不能签成 pass。
- review：kind=review；read_report_refs（实际完整读取的 suite/check/observation/companions/finding证据闭包）、criterion_refs、case_source_refs、reviewed_check_ids、finding_body_sha256（原 findings完整canonical SHA）、review_section_sha256。读集合由原只读 Review source 实际完整读取 receipt 产生并与本片闭包 exact匹配，不能仅 echo 一个 ref 列表；真实发现/关闭来源保留。不能改 Test标准、结果或为漏测签supported。
- acceptance：kind=acceptance；read_report_refs（实际完整读取的同 suite/check/observation/companions/review闭包）、accepted_check_ids、executed_check_report_refs、acceptance_section_sha256、observation_refs（验收职责内实际原观察refs）。原 accepted IDs、报告refs、未观察与结论全量匹配；本职责必须实际观察/执行的部分由原标准确定，不把读取 Test报告冒实际验收，也不为本文新增门或降原影音/精度/平台要求。

所有列表 bounded≤4096、按原refs/ID排序且唯一；source_refs按原resource_name。每条 observation/companion/check/read refs必须完整 protected读取，真实 case/读/消费来源不是一句 work已完成。Review/Acceptance的读 receipt与实际完成对象是下节生产 source 内部真实记录；如果不存在，NOT_IMPLEMENTED，不能靠给模型一个签名工具或用户填 proof解决。proof是这些真实工作和原报告的受认证投影；签名无法证明人工判断正确，独立 Review/Acceptance必须继续真实职责验收。

### 3.3 diagnostic-coverage-producer-index-v1

exact 字段：format、index_id、revision、issuer_id、trust_mode、anchor_key_sha256、host_build_receipt_sha256、bindings、producers、revocations、valid_from_us、expires_at_us、signature。

bindings 为本 index实际涵盖的完整 Binding tuple（1..16，按原 binding canonical SHA排序唯一）。producers 为1..4096 exact条目 {producer_ref, work_proof_refs}；资格ref唯一排序，proof refs完整唯一排序且非空。每proof属于该资格、同binding/role/report；同一 scope/report不得两个不同 proof或资格争抢出处。revocations 为 exact条目 {producer_ref,revoked_at_us,reason_code}，按资格ref排序唯一，reason_code 原 Identifier；撤销只能由原可信 source提交，不从文件消失或签名错误推断。正常首index可空撤销；非空不能被省略。index的完整有限有效期与真正受保护 current source一致；签名消息为 canonical(all fields仅去掉signature)，由原发行/本地锚签。

publisher材料 purpose=publisher_provenance；local_verifier purpose=verifier_code_index。3.1/3.2/3.3都按原模式存该purpose；既有报告/criterion/七伴件purpose仍原qualification_suite/qualification_report/independent_review/independent_acceptance。QualificationMaterialsIndex不加第六字段，不添加随意用途。由真正 TrustAdmission.material_refs 明确绑定一个该format的完整 index根；由此解析所需证书/proof，不扫任意同名文件猜根。原Admission同时仍完整包含原锚及其它已需材料；index不是新TrustAdmission。原材料source不含根/只含旧未知provenance时not_ready，不把旧签名材料洗成新职责资格。

本格式仅对本资源覆盖职责新增可识别 grammar，不改旧其它publisher provenance的语义。未知/其它format不得新producer positive，也不丢掉其原合法其它用途。

## 4. 无环完整闭包与独立性检查

构建DAG固定顺序：真实 source/build/原criteria→3.1资格→suite正文→suite proof→真实check/observation/七伴件→check proof→独立review正文/proof→独立acceptance正文/proof→3.3 index→原material index/完整qualification record→实际Trust/record/资源action。3.1不引用未来报告/index/TrustAdmission ref；suite只引用其资格，proof引用已存在正文；index最后引用所有资格/proof。报告不引用自己proof/index。TrustAdmission接受index原ref，而3.1/3.3只绑定原issuer/锚keySHA/host build receipt，不引用含自身index的TrustAdmission SHA，因此无自哈希环。

source build图、原target/report refs、report scope、全部case/results/观察和七伴件若存在back edge/cycle、重复ref不同用途/bytes或same report多proof冲突，拒绝422/immutable409，不只检顶层SHA。全集的计数/bytes按实际唯一原ref计入原4096/128MiB上限；不得新增隐藏不计数列表。

ReportOwner关系由本次精确 report_ref 判定，不能仅 producer_ref+role+binding。每原完整报告先由protectedreader读取并精确parse；其 producer_ref只定位真实资格。工厂查3.3内一份属于该 report_ref 的完整3.2，验证实际3.1身份/source与签名，role work及完整report DAG匹配后才注册成员。role declaration只在已接受锚和真实受限source中有效，拒绝外部自签新锚或自行塞入index。

独立性由工厂基于真实职责 source登记和签名完成proof做全闭包检查：Review source不能是实际suite/check source/受控同 signer，Acceptance不能是suite/check/Review；不同principal_subject必须同时对应不同受保护role key、真实不同source成员/实际职责能力。若多个check source参与，逐一比较全部实际source，不能只比较第一份。不能允许外部body自己声明一份排除名单。suite/check同一Test主体是允许的原职责组合，其基数不强迫四个不同人。

3.3的签名、Test key/Review key/Acceptance key不同是必要认证检查，仍不足以证明工作。实际生成时只有相应职责的已登记工作对象可提交proof，source保存其原工作/完整读取/执行/输出receipt；消费时核完整受保护证据与签发端source/build能力来源，独评再检真实执行而非相信标签。与普通App创作/模型无关，Agent不得获得这个签发工具。

## 5. 原强工厂、签发入口与两个 caller

以下是待实现私有合同，不伪称baseline已有type/方法。所有held类型 frozen、eq=False、禁止repr秘密，注册表按真正对象identity/原generation/epoch/thread。JSON可以是持久事实，不能反序列化成能力对象。

职责生产source：Integration提供原受保护role signer/构建source持有基础设施；真正Test/Review/Acceptance各自入口在自身职责范围内生成已登记工作对象。它绑定真实被准入3.1、当前受保护key/producer build、原有限role任务及完整实际工作/读/执行receipt，失效/关闭后不能签。原签发器只接受这个同一对象并自己投影3.2，不提供 sign(arbitrary_json)、role=用户字符串或 passed参数。发行锚只签3.1及3.3，安装器只收取完整原 bytes。角色私钥不得被Backend/Integration持有或转存日志；Infrastructure管理密钥句柄不等获得角色完成签发能力。具体受保护key部署由原source实现按现权限执行，不由本文读取/生成秘密。

唯一producer侧入口：

- Test produce_coverage_suite(role_source, frozen_criteria, binding) → 原suite正文/ref +实际suite work成员；produce_coverage_check(role_source, original_suite, actual_case_runs) → 原check/observations/companions refs +实际check work成员。actual_case_runs只能来自真实原准入执行/capture，不能从ExpectedResult tuple mint。
- Review produce_coverage_review(role_source, frozen_complete_test_closure, actual_review_completion) → 原review正文/ref +实际review work成员。completion只能是原Review该次真实工作来源，其原readonly receipt是同source成员，不是installer给的结论dict。
- Acceptance produce_coverage_acceptance(role_source, same_frozen_closure, actual_acceptance_completion) → 原acceptance正文/ref +实际acceptance work成员；需要的观察/运行沿既有标准，未观察保incomplete。
- 同一role_source.finalize_coverage_work(work_member) →3.2完整bytes/ref；真实限定入口自己检原数据与签名，role_source只能给自己的成员签。已有同ID同body immutable返回原bytes；不同body409；unknown已提交只查询原签发结果，不重执行/重收费。
- 原发行/local锚finalize_coverage_producer_index(actual_admitted_sources, actual_work_refs) →3.3 bytes/ref；它完整校验签名和闭包，只签aggregate资格/来源索引，不产角色正文、不替角色签3.2。

这些入口由各原角色实现其生产逻辑，Integration只实现source/key/held部件、成包与搬运；不能由Backend把一份genericDTO送任意签名器满足全部职责。实际阳性须原独Review批准合同及后续实现、真实执行和验收。

消费者复用原 open_native_qualification_trust 的_TOKEN、holds、实际connection与build；仅在该真正同Engine/Bundle/Owner/action/安装source工厂建立职责读取成员，外部调用不能构造source。真实方法精确为：

read_admitted_coverage_producer(self, ref:QualificationRef, *, role, binding:ResourceCoverageBindingV1, report_ref:QualificationRef, at_us:PositiveI64, usage:historical_acceptance|current) →原 HeldCoverageProducerOrigin。

report_ref 是已实际完整读取并解析的同reportref；at_us/usage来自原 verify_resource_coverage 入参，不能用默认now检查历史H或凭模型选择。方法读取完整3.1/3.2/3.3/原role build及实际report闭包、核独立关系、签名/source/proof所有crossrefs、原usage时点并真实assert_current；成功只构造该source私有注册成员。原 dataclass增量私有binding：_report_ref、_proof_ref、_index_ref、_at_us、_usage、_native_origin、_source、_producer_source、_epoch、_thread，另保原ref/role/binding；不是第二公开DTO。

assert_admitted_coverage_producer_current(self, origin) →None：必须exact注册对象、同source/Engine/Bundle、同scope/report/proof/index、epoch/thread；原真正connection member与holds/current/floor/row一致；原有限validation deadline内。外SQLite执行真实peer/RPC/held完整源检查。失败保存原specific错误，不把所有EngineError吃成not_ready。

assert_admitted_coverage_producer_local(self, origin) →None：同对象注册/current epoch/thread/报告与proof注册scope，原current行/floor/strong local快照与hold有效；仅本地/已持有的原guard，不在短writer内读文件/RPC/签名。被撤销、thread不同、source关闭、foreign连接/Engine/Bundle或json重建对象均拒绝。原 register_prepared_resource_coverage 注册全部origin；assert_prepared_resource_coverage_local遍历其全部真实origin，不只检查第一份或通过bool。

Closure.producer 改为producer(ref,role,binding,*,report_ref,at_us,usage)并转上述参数。caller精确：suite用原 record.qualification_suite_ref；每 check report用loop当前完整report_ref；每 observation用该result.observation_ref；review用原 independent_review_ref；acceptance用原 independent_acceptance_ref。它们的producer_ref各自来自已读取原body。各自3.2只覆盖对应ref，不能靠一份check proof覆盖所有文件名。共享验证器核每真实companion引用与该check工作闭包/实际原source，不将capture接受report bool当证据。

完整caller序：原protectedTrust/source完整current→读取exact材料/root/报告→真实职责成员+完整闭包外SQLite验证→注册PreparedResourceCoverage→原source当前检查→原短writer同row/current/local检查→archive完整原bytes/ref/event/command→writer后原当前检查→原完成/安装floor。原已有installer尚没接完整prepare caller的事实保持；下游必须实际接它，不能只有helper定义。

## 6. 原observe成员和assert_current的闭合转交

send_exact只捕获原请求/回复bytes，不构造真正观察成员。须在原 OwnedQualifiedAuthorityConnection.observe_facts 收到/验证original reply并在原connection登记真实observation之后，从该同一真正callsite保留该original object；before capture绑定同connection/session/seq/peer/instance和actual observation_id，不接受body里填的ID获得成员。

Integration在原真实source构建/连接接点提供闭合私有handoff；Backend在原Source读/注册边界消费，形状为 retain_original_coverage_observation(source, actual_connection, original_observation, actual_frame_capture) →私有held桥接成员。这不是可由API/MCP/renderer调用的注册端口。构造只由原 observe登记成功callsite内部触发；需原connection注册identity完整核验，不能只instance或同observation_id。桥接成员保强original object引用和原source/connection/generation/epoch/thread、report/qualification/context绑定；actual frame是该callsite实际capture对象。候选未实现该transfer。

后续source/current捕获调用 same actual_connection.assert_current_facts(same original_observation)，保原before observation对象，不能fresh observe或只持一个capture/ref。local writer只读取该原成员已建立的local guard，不跨thread借ID。source/connection/parent/lease生命周期终结或epoch变化即注销桥接成员，旧capture仍可原字节归档但不再assert成功。

停止Native接口的实际caller必须同时接通：原 QualifiedRegistration.register_with_capture 在单一原channel登记后由 OwnedSetupRun 持有 RegisteredHandlerCapture；原安装qualification消费者从它调用 read_original(original_observation_id, actual_seq, observe/assert_current)，分别得到真正 HeldHandlerExchange，而不是传 transcript bytes。消费者把这两个同process/session/source的真实成员及原七个索引refs交 CoverageProducerSource.read_execution，保留 PreparedNativeExecution、Arc<TrustAdmissionOriginal>、实际资源holds和original process/Job直至其真实终态。原CoverageProducerSource.read_admitted_coverage_producer也增加同Python的report_ref/at_us/usage完整参数并按三文档注册实际 OriginAdmission；不能把现空map当工厂。

Backend自己的原受认证connection/source构建器只在同一原peer/current/action对应关系验证后建立Python注册成员：其original_observation还是该Python connection原实际observe登记对象，Native实际exchange/protected reader结果是同source验证证据，不序列化Rust opaque origin作权限。安装器负责将两边实际原source/request/reply/context对应到同材料ref/报告scope，并由各自original factory登记；异instance/process/session/record/action/floor拒绝。没有完成这个source-owned caller和桥接就明确NOT_IMPLEMENTED，不能仅调用ParsedExecutionSet、把data predicate或一份capture包装能力当接通。未知close期间仍保原Arc/资源/Job持有，不以EOF缩短原寿命。

原首次record_admit准备路径尚未qualified时，唯一可用是原 OwnedInstallationRecordConnection 内已实际接受并登记的same installer action；只验证该action所需的有限材料/完整closure，不把not_ready observation当qualified，不给生产Run发permit。此source工厂保原_installer_action与actual action身份、ExpectedCurrent/floor和原scope。提交后必须原record/committed-evidence路径转换，不自动把该action转成普通运行观察成员。正常qualified路径使用原observe/member对象，两种来源精确分派，不以同字段JSON相互替代。

原Native/Backend独立验证相同grammar：Native真 registry/source保护完整材料和独立性，并在真正action/current切换重验；Backend从原受认证强连接持有上述实际member，完整读取和local同源检查。无需新公共wire或第二身份channel；若现send_exact hook只能传bytes，必须完成此原constructor/caller接线，不能把bytes包装新dataclass冒成员。原0066 Ownerreplace/drain wire规则继续，不因本合同另加更宽scope。

## 7. H历史、C当前、有效期、撤销与恢复

所有活动origin依赖当前C真正source/action/原guard。current用C实际时刻验证角色资格/proof/index有效、没有适用撤销、current root/报告绑定完整；必须真实被current锚接受。旧证书、过期证明、body变化、根更新或anchor/Owner replace使活动origin失效，不复活旧grant。

historical_acceptance用于读取真实原H接受时点/不可变archive的事实：完整H资料及当时实际被接受的锚/职责来源必须由原可信H archive reader取到，3.1/3.2当时有效、未在H之前撤销、原报告/command/commit身份不变；仍由C原Owner/current source及已经批准的H/C受控读取路线认证。不能因H资格已过期删除历史事实，也不能将H proof升为C执行/新producer签发权。只有H字节没有原可信接受关系，保持missing/unknown；不能用当前锚给它补签以洗白。原H与C两个实际资格来源/许可关系另行完整消费，本合同不换成history-only或current-only。

source退役/撤销按原Owner替换、drain、强载体及ExpectedCurrent CAS路径更新真实root/current；不另发文件撤销权限。新3.3 index必须经过原真实安装/replace source接受，不能文件热改就认可更高revision。未完成替换/暂时离线保持原原子状态/unknown，不推断false或null。旧refs和archive immutable；同source/action/key/body合法replay读原结果不重签、重分析、扣预算；同key不同body409，unknown原Operation reconciliation-only。

首次合法资料完整且原锚已接受时，允许原installer准备→外writer全验证→local CAS提交→原committed/current恢复成功，不因缺一个尚未实现的role字符串callback永久503。资源/资料缺失要明确missing来源及对应角色生产任务；恶意自签/不同binding/未授权role拒403或422；当前撤销/过期/替换/foreign member409；真实未知/缺实现503。费用unknown不因为不同role task名重置或重发。

## 8. 实施切片与可直接交接ABI

1. Backend：唯一domain新增三exactmodel/签名投影/parse注册；完善原NativeQualificationTrustSource三方法及新report_ref/at_us/usage参数，保真正注册/current/local；Closure实际五处reportcaller；完整archive原bytes和immutable refs；H/C读语义。不能签独立role proof或应用未经批准候选。
2. Integration：真实发行/local producer source/build/key custody与同一观察成员handoff；Native同grammar/独立性/index/proof校验和原installer prepare/commit caller；成包保全部新角色code/完整材料图与原依赖/147+24/三OS资源，不把证书文档当真实资格。签发行锚的工作与独立角色签工作分权。
3. Test：在自身允许路径实现suite/check真实资料producer与实际capture/finite原case运行；冻结criteria后保持红/unknown，记录完整实际报告闭包；只持Test source的工作签发能力。
4. Review：在自身报告/过程范围完成实际独立review正文及受认证work export；先独审本合同再独审实现与结果。不代修源、签Test或Acceptance。
5. Acceptance：在自身范围实现实际验收正文/work export与观测闭包；只持Acceptance source。影音/精度/运行/平台未验保持未验，不由原source签名自动通过。

source/capacity/key的具体bootstrap、读receipt、签发器与handoff现缺，必须真实实现并取得原独评；不是部署到某台机器就自动独立。没有publisher真实key/合法报告时可先实现受保护结构/负向、免费真实local资料链，不能捏阳性或向外联系厂商/管理员。本卡不产生/读取key，不启动role pipeline。

## 9. 独立验证与保护矩阵

必须独立核以下真实源码/运行反例；本文不改oracle或将它们宣通过：

| 情形 | 必须行为 |
| --- | --- |
| 原Owner接受锚、真实suite/check→独立review→独立acceptance→完整index/materials→same installer action | 全部实际work和完整原refs匹配后原prepare/commit阳性；不是只parse/health |
| suite/check同Test key，Review/Acceptance各实际独立source | 合法；不误强迫四个不同账户 |
| Role标签/不同SHA/自签key/一通用signer四次换名 | 不得positive或mint角色 |
| 同producer+binding但report_ref不同，或只换报告bytes | 无匹配原work proof/immutable conflict；不能沿用来源 |
| Proof引用未完整读报告、漏case/七伴件、修改criteria、丢红/unknown | 全闭包拒绝；不选有利执行重收费 |
| Report→proof→index自hash/cycle或不同purpose复用ref | 拒绝，source/member不注册 |
| Review/Acceptance实际source或key与Test相同/跨能力写标准 | 独立关系拒绝，不因不同ID接受 |
| genuine observe +send_exact→同原member assert_current | 真实handoff成功，before/after同对象；fresh observe/foreign/json对象不通过 |
| installer首not_ready阶段 | 仅same实际record action验证资料；不能生产permit或伪qualified |
| source变更发生在外验证与writer之间、epoch/thread/floor不符 | local同源检查拒绝/回滚，无部分archive/新授权 |
| H真实原接受、C新source current，或过期H资料查询 | 保真实H immutable历史；不复活H grant，C副作用仍当前独立授权 |
| 同action同bytes replay、unknown签发/Operation、source替换恢复 | 读同原事实/核实原状态；不创建第二收费执行/新body或清旧pointer |

保护层始终为原OS/Owner接受锚→完整held材料/资格→实际独立work→原registered member→外writer全验证→writer内local/CAS→原完整archive/committed当前。任何一层的hash/signature/body只是该层事实，不能替代其它层。原两authority、预算未知不重放、lease/thread/fence/epoch、不可变replay、200ms及原角色独立保持。

## 10. 阶段交接与未处理项

本阶段只固定合同和普通来源；下游原独立Review必须先审，随后原Backend/Integration/Test/Review/Acceptance分别接线。当前137 partial及本设计不等许可、实现、原schema应用、影音/平台通过或R1完成。原0065 MRPL-I01关于角色集合基数是独立非阻断后续澄清，不在本卡热改0065或吞并MDG能力。完整输入身份、实际读取范围、差异、Impact和interfaces位于 Architecture/CoverageProducerAdmissionContract/，最终自然工具回执和全部reader释放由正式交接报告，不从文件存在推断。
