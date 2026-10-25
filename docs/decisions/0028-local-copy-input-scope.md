# ADR0028：跨Production本地复制输入范围

2026-10-09。状态：**最小契约设计准入，真实管理/持久实现/复制验证待验**。只Architecture；完整R1后连续R2保持。固定B23 Implementation Gap `c56f097a…`、Snapshot `966aa275…`、正式Interfaces/交接已读。B23静态0不是运行通过。未读I32、未运行/收费/读取秘密。

## 唯一选择和兼容

当前PolicyInputAsset只含真实asset_id/SHA，PolicySourceScope要求system/namespace，确实不能表达历史本地Bundle中的受控Material。补充**独立受管理的LocalCopyInputScope**及本机当前请求绑定，保旧ProductionAuthorizationPolicy/Request/AuthorizationActionReceipt/AdmissionFact/portable doc的kind、字段、canonical SHA和原bytes；不往旧0.1策略默认加字段，不伪SourceBinding/namespace，不把material装成Asset，不以caller_supplied_text_allowed或general Bool放行。

本轮解决同实例/同Owner/同project的**跨Production**来源，source_project_id仍显式记录且须等于destination_project_id；ADR0020/26现same-project守卫不因任务标题扩大。跨project/跨实例授权需另有两侧真实权限/来源映射，未由此补丁准入。真正本地indexed material可以由新scope覆盖，原合法sameProduction/namespace分支保持；不能把新scope缺失的403当完整产品最终完成。

## Backend唯一公开管理合同

新增独立kind `local_copy_input_scope`、version `0.1.0-candidate`，由Backend定义Pydantic/OpenAPI/错误及严格grammar。最少正文：

| 字段组 | 明确内容 |
| --- | --- |
| 身份 | scope_id/revision，instance_id、owner_subject、destination_project_id、有限executing_principal_ids与实际registration SHA、精确现ProductionPolicyRef（id/revision/bodySHA） |
| 有效期 | valid_from_us/expires_at_us整数微秒且有限；不晚于绑定执行policy范围；current/revoked状态由真实服务记录，不由proposal给Bool |
| 来源集合 | 非空有限items，每项kind=`local_bundle_artifact`，source_instance/project/production、完整BundleRef（revision/schema/manifestSHA）、artifact_id、严格discriminated locator=`material`+真实material_id 或 `asset`+真实asset_id、fullfile SHA/size/MIME/role/kind、实际source RightsSnapshot SHA |
| 操作范围 | 每项明确handling=`verify_only`或`copy_into_delivery`，适用的原UsePurpose有限集合；proof核实不默认可披露，复制需要实际derivative/export/redistribution及输出用途 |
| 版本与约束 | 从真实来源服务解析的完整source集合/边canonical SHA与各成员身份；不含自己的bodySHA/绝对路径/secret，不含任意目录、future版本、通配artifact或未知namespace |

items必须来自实际本机Ready Bundle索引/MaterialReceipt或Asset，不仅查询到materialID或文件存在。既有gap就是这种indexed历史material；未索引的孤立Material不凭此产生Bundle身份/权利，需先真实完成其受控来源记录。BundleRef跨revision/file/role变化拒，不按同bytes或同artifactID替换。重复/冲突先拒再去重，来源不超过既有256artifact/32report/实际max_bytes闭包限制；读用途不能加成whole Manifest披露。

可信服务在安装预览中从选定历史源解析全部实际祖先/许可/proof集合供Owner确认；复制成员和仅核实成员分别显式列出。不能给一个root加`include_all_dependencies=true`便默认授未来/未知附件；后续选中root的真实闭包每个成员和必要边都须落在已确认集合且身份/范围相符，少任一成员明确拒。任务可以使用获准集合的合法子集，binding记录本次实际使用子集SHA，不强制未用成员成为输入或交付；子集不得截断该选中root的必要依赖。新材料需要真实replace动作/新revision，不自动扩大旧scope。Owner可以一次安装这个有限范围供符合条件的多次API/MCP任务使用，不要求每个作品人工填内部proof。

管理proposal只是建议；唯一实际管理服务经已有受限 `production.authorization.manage` 及Owner/项目/注册权限核后install/replace/select/revoke。普通Portal执行credential/MCP/model工具不能管理或自行安装。独立 `LocalCopyInputActionReceipt`记录actual instance/actor/project、动作、scopeRef/bodySHA、原管理command idempotency/requestSHA、时间、registry revision和真实认证来源；与旧AuthorizationActionReceipt不同kind/命令scope，不扩旧action enum或伪旧create结果。非Owner授权、foreign导入或模型JSON/hash不成为安装事实。

## 持久性与原请求绑定

Backend新迁移增加两张最小表：`local_copy_input_scopes`保存不可变revision/body/action与当前/撤销状态；`local_copy_input_bindings`保存Production/Run/request_revision_id/requestSHA、认证principal/registration、精确scopeRef/action、执行policyRef与本次实际source-set binding。管理floor/default选择使用现受控metadata的独立键，不能覆盖production/alignment floor。迁移编号由Backend根据实际最新schema顺序选定，不回填任何允许行、不重写旧记录/hash。

accept事务可选择Owner已选定的、与当前policy/principal/project匹配的scope并将其精确ref绑定原request；相同create幂等返回原绑定，不因默认scope更新静默升级旧Production。无scope时旧行为保持，稍后真实Owner管理动作可对这个原Production/request补绑定/重新授权，不要求重建request或新Production。binding只是原选择，**不是执行许可**；正常ordinary lease取得后，从实际scope/action/current/floor与精确source集合派生私有CopyInputAdmission，绑当前Run/request/fence/checked/有限valid_until。旧fence只作历史，重启重核同选择，不清Operation/费用/限次、不新增budget group。

管理撤销/replace/expiry与prepare/final writer用同本机事务次序；scope替换或执行policy替换使旧current binding不能继续执行，需真实重新绑定，不选择“最新相似scope”。失效停止受影响复制/提交，但不抹历史字节、不召回已发送内容、不清unknown预留。当前执行policy的预算/route/resource/external-transfer/普通fence与来源法律权利都照原独立守卫核。

## 唯一消费与实际许可

Backend在现assert_current_copy_scope新增准确分支，以**实际requested source artifact及完整source集合**为参数，而不是只凭original Manifest任一条source_ref即认为全Bundle可复制。新服务返回typed本机事实，至少含scopeRef/actionRef/绑定行ID、当前Production/Run/request/fence、source-set SHA、实际逐项identity/required uses、checked/valid_until与registry revision。Media只能消费服务签发结果和新私有事实格式，不能提交该DTO/Bool换权限；Backend固定canonical/context/cache版本后正式交接。

初始correction_origin_evidence/_copied_rights_bindings与final _origin_bindings_current均重核此范围。文件/完整SHA/源祖先解析在writer外；短writer同connection核真实scope/action/binding/current floor/期限、原immutable Ready身份、当前ordinary lease/policy和完整许可/撤销。不得writer内网络/hash/模型；preflight/cache绿不能替final。最终提交同原原子Bundle/Step/admission顺序，无future Manifest hash循环。

scope只授权**这些内容可作当前制作输入**，不授所有权、source重新许可、输出rights/QC或平台发布。ADR0026的source历史证明与新current许可分开，ADR0020每层license/自身right/dependency/用途期限撤销与narrowing不减；source策略后来inactive仍可历史核，但source真正许可失效不能由本scope复活。owned/licensed真实authority缺件仍not_measured/not_ready。foreign origin-only、导入receipt、可读、同Owner或allitems SHA自洽都不本机ticket；新scope及binding也不从Bundle import安装。

当前portable ProductionAuthorizationDocument旧字节/关系不新增此scope字段。新本机input事实由独立表/私有cache/final writer保存，不用旧doc伪声明新增授权。若将scope管理证据对外披露，需独立严格kind/role/许可及生成契约准入，不能塞audit_summary或反写旧doc；它也只能审计，不跨实例授权。本轮不要求普通用户增加作品步骤，可信Owner设置/Portal管理员可一次预配置，执行API/MCP自动绑定并完成完整制作。

## 失败与下游

422坏grammar/矛盾identity或管理原件；403 scope不覆盖当前source/principal/用途或未经授权管理；409绑定/版本/currentfloor/immutable source漂移；当前scope缺失仍具体`production_copy_source_scope_missing`，需Owner安装/原请求真实绑定恢复，可按原waiting_authorization释放lease→queued新fence，不写ReviewDecision/伪人审。真实rights到期/撤销或未配authority沿原rights错误，资源超限413，不将它们合成泛not_ready。Backend唯一定义公开ErrorEnvelope和可恢复状态，不降低旧阈值。

Backend负责独立管理模型/两表迁移/actual Owner动作/accept及原任务补绑定/typed source守卫/最终writer、完整唯一export；Integration同Backend正式OpenAPI/Pydantic生成契约/SDK、封装可信管理入口；Frontend保五步和一次Owner范围配置；Media消费正式source集合、binding和私有版本，不伪Asset/namespace。架构不代写实现/SQL/SDK/标准。

Test独立固定真实正反：真实管理安装一次→两次新Production原请求绑定→跨Production无namespace Material完整复制/publish阳性；旧sameProduction/namespace/human/hash回归；普通执行者管理拒；wrong instance/project/owner/principal/registration/policy/request/fence；sameID异SHA/receipt、Material假Asset、foreign导入不ticket、scope漏任一祖先/许可/proof、verify-only不可交付、source真rights失效；撤销/replace/expiry发生于initial与final之间、默认变化不替旧幂等绑定、恢复不重预算/unknown；所有license及三OS/真实作品另验。Review批准实际标准及独立实现，源AST0不等这些运行通过。

固定source pins/正式Handoff后本轮释放，无产品/DB/import/测试/native/model/network/key/安装/收费。A24八VC下限仍unknown，本契约不授native运行或发行资格，也不因缺外部资源缩完整R1→连续R2。
