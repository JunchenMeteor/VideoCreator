# RV40：B24 Slice A 本地复制契约与迁移有限独立评审

结论：**SOURCE_REVIEW_FINAL；RV40-P01 / P2 / Backend / OPEN_STATIC_CONTRACT_DEVIATION。** 首片独立类型及存储结构具有下述源码支持，但全依赖深度额外限制与ADR0028的artifact/report数量边界不同，需要归属者纠正或架构明确裁定。Review没有运行Pydantic、SQL、schema、产品或Test；不能称实际复制失败。Slice A不是完整B24、真实管理或成片通过。

## 1 固定输入

唯一首片根：`G:/开发测试/Codex/VideoCreatorImplementation/Backend/LocalCopyInputScope-B24/SliceA/`，源码仅从其 `SourceCopies/services/engine/`读取；旧47份来源：`Backend/PolicyOriginCopy-B23/Implementation/SourceCopies/services/engine/`。没有读取正在修改的B24 B/C、I34或T30，不混另一失败评审。

| 正式对象 | SHA256 |
| --- | --- |
| ADR0028 | 252f67acb04c2ccef3cd1601cea1ec3d92793868a1fbcebb903b13904807d5fa |
| B24Handoff.md | 71d2d167d5499f38ad83019bb3f0d4c61f14c356fb8af9553830d07a5d87a914 |
| B24Handoff.json | 774faaacf0a54f72997244f618c40ec5793a348338a09a5e323fbe7381529fbe |
| B24Interfaces.md | a9f19bfaeb981daca44800712cba85a82a7a2ed8a0a1d95b4901732b5aa6fac9 |
| Slice A SourceSnapshot.json | fe414b10feda7be6bfef31a2ea525343bce8e46edd5397b2fd12600e160b1118 |
| 旧B23 Implementation/SourceSnapshot.json | 966aa2755a82516a63f45c28e3cfb434951f348bc6adb86a9d015295c3636103 |
| AcceptedSourceChanges.diff | 2b72e22cf8ddc734633c85a2dfa82d7e0a0f512ce04f1132d98fdb1e228cf592 |
| StaticReceipt.json | 64d4d17b90a380ff4850370d037506226a3644187e0abc7f95a053f10918e9b1 |
| CommandReceipt.json | 73a1d55d2918182d54dcc326155adb9316426567ef76fb8edfbf5e46ba1335a5 |

50新普通源、47旧普通源及9正式输入，共106路径记录SHA/size全部匹配，末核无变化。四份diff只用标准库在内存核文本，其结果与固定普通源逐行相同；原47中仅database.py变化、46源完全同SHA；新增三文件。未apply diff、运行产品AST/Pydantic或重跑Ruff。

| 首片相对于SourceCopies/services/engine/ | SHA256 |
| --- | --- |
| src/video_creator/domain/local_copy_input_scope.py | eab4044a5c6031008d240ae4db1398a85095766bb00aaf8fdb81b69b44338764 |
| src/video_creator/application/local_copy_input_ports.py | dfaf9147249519181790ea79675c93bcb9c3dceffca3066624651c05489bd3c5 |
| src/video_creator/infrastructure/database.py | 96f1971b1b1980d39cb0575d6acce0325de657c24fa5d78e313aa2dcc8c6bef7 |
| migrations/0007_local_copy_input_scopes.sql | 430d8b46da57cc1a699ad09e6b2e939dc823a4f964c2e89384c822ebedf9a1f3 |

## 2 RV40-P01：report数量被用作全部DAG深度限制

**P2 / OPEN_STATIC；实现归Backend，新增通用深度标准的裁定归Architecture。** 精确固定源：`G:/开发测试/Codex/VideoCreatorImplementation/Backend/LocalCopyInputScope-B24/SliceA/SourceCopies/services/engine/src/video_creator/domain/local_copy_input_scope.py`，完整SHA见上表。

ADR0028第23行的原文边界是“来源不超过既有256artifact/32report/实际max_bytes闭包限制”。新源14行定义MAX_SOURCE_REPORTS=32，complete_graph162行对**所有成员**计算 `depth = 1 + max(walk(child))`，164–165用该report常量拒绝所有depth>32。没有判断节点是否report。正式Interfaces也将它描述为最多32依赖深度，同时声明真实report数量32由后续resolver核，故这不是摘要笔误，而是实际grammar新增的另一种限制。

最小静态反例：同实例、同项目的33个已索引普通文本artifact，完整不同member identity，handling=verify_only且required uses明确；一root、32个artifact_dependency边组成完整可达无环线性链，report数量0、artifact数量33，实际字节总量在安装实例max_bytes内，余下身份/权利均满足条件。按获准计数仍在256/32范围内；新walk在root处得到33并抛ValueError。这个反例只说明**类型层会额外拒这种有限形状**，没有构造模型、安装scope、创建数据库或实际复制，不能声称真实现存作品已失败。

影响是契约提前排除批准范围内的非report闭包；其DFS已经memo且最多256节点，不能把报告数量自动当全部图深度的既有标准。没有发现通过此问题获得授权或跨项目复制的路径。

最小关闭条件：Backend分开实际report数量限制与通用DAG结构校验，保256artifact/32report/实际max_bytes、cycle/重复/完整可达边界；真实report识别与数量仍由可信resolver核实际材料，不能靠caller角色字符串装已核。如果确需通用depth32，Architecture应独立明确准入这个新增边界，再冻结对应grammar/Interfaces/标准并由Review复审；Review不自行放宽或修改ADR。

独立Test后续固定语法版本核32/33普通非report链、真实32/33report、缺祖先/重复冲突/cycle/超过256、ordered canonical SHA与合法子集；只是测试建议，不授本轮构造或产品运行。不得以当前B/C未来实现、Mock或改期望回填这个首片。

## 3 其它唯一契约的源码支持

domain17–20 canonical以model_dump(mode=json)、sort_keys、UTF8、无NaN完整SHA，保items/roots/edges元组顺序；source_set_sha不自包含。Member key23–26使用完整BundleRef与artifact，重复完整键/重复root/重复edge先拒，150–153核成员与边存在且非自环，156–173核cycle及从root全可达。不能从这些形状检查推断真实文件/全部source图已核。

Material/Asset locator51–66采用明确discriminator；SourceItem76–88与原BundleArtifact的既有MIME分类规则一致，text Material不装成Asset，instance必须匹配完整BundleRef，roles/required uses非空且不同，copy_into_delivery必有derivative/export/redistribution。verify_only明确单列，尚未接真实消费者，不能据此称不会披露的实际行为已验。

Scope177–204独立kind/version、instance/Owner/project/principal/registration及原ProductionPolicyRef；仅同实例同项目成员、有限微秒有效期、精确完整source_set SHA，没有current/revoked/bodySHA或目录通配输入。policy实际有效期、真实principal/registration及Bundle Ready、fullSHA/MIME/roles/rights等需后续服务核动态事实，类型本身不授权。

Install207–219只允许revision1或精确previous+1；Select/Revoke/Bind命令独立。Action243–269不扩旧AuthorizationActionReceipt enum，明确actual actor/authentication binding/source、独立scopeRef/idempotency/requestSHA/time/registry；revoke才有reason、bind_request才有同scope精确target。ScopeRecord272–296核完整scope bodySHA与实际installation action身份，以及真实撤销receipt关系；current/revoked只服务读结果，不是安装proposal。

Binding299–316保原Production/Run/request、principal/registration/policy/scope/action及source-set SHA，无allowed Bool或执行fence。旧Policy/Request/action/doc/domain合同、B23三消费源及human None分支字节未改，旧canonical/default不被新模块导入扩字段。公开Schema/OpenAPI/SDK尚未生成或接通，不能把Python模块存在当公开接口可用。

## 4 私有端口及两表迁移

ports28–67明确resolver-owned实际BundleContentHandle/MaterialReceipt或Asset、完整ResolvedLocalCopySources和私有CopyInputAdmission（当前fence/checked/valid_until等）。Protocol70–105只固定受限AdministrationCapability管理和同connection当前requested fullclosure签名，未安装具体实现。dataclass可构造、Protocol可实现都不是发行/权限；后续实现必须独立核真实resolver/cache发行、逐项观察与source-set精确一致，不能caller/model提交DTO或None返回换授权。

ADR的合法选中root子集仍须完整闭包且记录实际使用子集身份；后续B/C应核binding与admission的SHA语义，不把未使用成员强制变输入，也不截断所用root的祖先/许可/proof。本首片只端口，不据未实现动态检查造新运行缺陷。

SQL7全文只有两表及索引，scope/policy exactrevision FK、project/production/run FK、current条件唯一、不可变正文/动作/selection及完整SHA列；独立local_copy_input_registry_revision初始0，没有允许scope、grant、Operation或预算行。它不覆盖production/alignment registry键；真实外部floor/default/idempotence/Owner管理仍未接通。表与FK存在不证明跨列主体/请求一致、current许可或事务回滚已经验证。

新Database34–54对旧schema3—6先snapshot_backup，短BEGIN IMMEDIATE writer内再次读version并按序执行migration7，拒>7；不用隐式提交executescript。backup95接受已知7、115记录独立copy registry identity，记录unknown/费用知识和外部可信floor依赖，rollback_compatibility_verified=False。旧固定database42仍拒>6；只源码推导旧码遇7会拒，不称真实启动通过。新旧迁移1—6字节相同，原存量/hash不回写。

实际schema7迁移、WAL备份、恢复/重启/并发、受信control文件与registry、原请求幂等/补绑定、普通lease/newfence及initial→final revoke/replace/expiry、当前writer许可和完整复制尚未执行。不能将七号迁移塞入旧I32候选就宣布新engine完整兼容，也不能把缺scope403/503当整个B24已完成。

## 5 原证据与终态

原732dbd实际tool0：50普通copy/43AST/三Python目标Ruff0/no drift，owner50992/ruff27996已wait，CommandReceipt自然0；adf21a原只读身份0。它们支持source/static终态，不支持Pydantic构造、SQL、管理或copy/publish。原两误猜文件名85ce7d/5c0478及宽读84c5ee仍为工具过程错误，旧red与拒绝不覆盖。

本轮标准库d24e24自然0只核固定文本身份与diff；不是产品/测试执行。SourceAfter73f751自然0，106输入无变化，固定source/evidence读者全部终态已释放，live=[]，不持B/C活源freeze。写入仅此报告及 `G:/开发测试/Codex/VideoCreatorImplementation/Review/LocalCopyContract-RV40/`，保存InputPins/FactsCheck/Finding/Snapshot/SourceAfter/Handoff。

真实管理与rights authority、source preview、原请求绑定、全requestedclosure、initial/final短writer、HTTP/唯一export/SDK、完整作品及三OS资格仍归后续完整切片与独立Test/Acceptance。Review不改实现、标准或测试，不运行产品/DB/schema/native/ASR/provider/network/key/fee/install。原sharedWorker/ASR/_admit拒绝不绕。完整R1三OS独立验收后连续R2、实例自持数据、前台五步不缩。
