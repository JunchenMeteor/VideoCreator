# RV34：B20 Bundle 制作授权有限独立源码评审

结论：**SOURCE_REVIEW_FINAL；RV34-P01 / P2 / OPEN，归 Backend。** 新的本机 publication scope/current writer 与便携 origin 原件已分开；本轮发现便携授权材料漏核 Owner 动作项目范围。其余下述链路只有静态支持，未授运行、RuntimeBinding、真实安装/Owner/权利或 Gate/R1/R2。Review 不修改生产、标准或测试。

## 1 固定输入与变更面

过程输入唯一根：`G:/开发测试/Codex/VideoCreatorImplementation/Backend/ProductionBundleAuthorization-B20/`；源码从其 `SourceCopies/services/engine/` 读取。未读 B21/current production、I30 或 T27 WIP。

正式 B20Handoff MD `c0631872387ce62bd75dab01dc7dcf13b8ab7dfb418c6b9f65b8e0b2acd96f98`、JSON `3979438c3e9d96497e0fcf002a2b960aa7838c89412f045fe2a2f30e67a7ab19`、Interfaces `4d68fc09672fe38ce28654ac25f55018bc9ee46bcfbd98682d6880f4a7c23a54`、SourceSnapshot `7f02ed2991b5d8467ee3790c06e49ffc8932f4cbf6262428a0fee7161e467056` 均实核。47 个 source_map 的 ordinary SHA/size 全匹配；加正式输入及四份必要 B19 固定正文基线，共67 pins/0 mismatch。末次固定输入66 pins/0变化，统筹可更新的任务卡单列，不持当前生产 freeze。

五个变更源：

| 固定源（相对于上述 SourceCopies/services/engine/src/video_creator/） | SHA256 |
| --- | --- |
| application/bundle_authorization.py | ed2bd6753a0d577dddbf5182f3a11de8568b0bb2e2813293dbe8236461bbbb06 |
| application/bundle_facts.py | a5adc5415116c33b875c6cfaec06e634fd2d40c78150ebbfcff049d0dfdf289b |
| application/bundles.py | 8d7b8f73ffd5ed260a8e263d9a58ddfa3690f5d33c69cda713f21544d2628df5 |
| application/production_admissions.py | 7f1d044c17a6e14e94e2d3f3ec4b98b4f5dabe45d3dce18899460864b1daf060 |
| domain/bundle.py | 504649b976d62abf0fb0875e5659a528d348414489d2640daefda06775754083 |

AcceptedSourceChanges.diff SHA `f7971760d21f4e46caa3a26e6e3b61e6004f2fd25100b8a5aaf9a55fbb163a7c`。独立以冻结 B19 ordinary 为基线，在内存逐 hunk 核文本，五份结果与固定候选逐行相同：bundle_authorization 1hunk/207行；bundle_facts 3/166；bundles 20/2525；production_admissions 1/701；domain.bundle 3/155。旧上下文核对0/18/159/6/19处，错误0；这是文本身份验证，**没有执行或应用 diff、import/AST抽取测试**。

原 Engine、公共 contracts、授权 domain、SQL/schema6、Operation/预算及旧 Request0.2/0.3默认/canonical身份未在这五源 diff 中变化。B20 固定 Engine 仍为 `ace4a97c…`；本轮不借 B21未来修复关闭 RV33-P01。

## 2 静态链路支持与实际限制

**strict材料及不可变原件。** domain.bundle31–55把production_authorization列为独立MaterialSlot kind，Receipt仍受控。bundles71–92/151–189将它 dispatch 到完整ProductionAuthorizationDocument，严格UTF8/LF/JSON、重复key/非有限数、Pydantic额外字段等规则保持；prepare682–719核唯一kind/path、精确Checks/production-authorization.json和application/json，slot/路径不可混用。stage721–751只从已配置issuer和实际registered identity读取同Run execute_plan admission，规范正文加LF后走原stage journal；generic stage也只能保存满足strict类型的bytes，不成为本机许可。已有ready正文异SHA/size拒409。

bundle_authorization27–66绑定唯一role/path/MIME、material_id、原instance/Production/Run/Request、真实production-plan CreativeRevision的canonical SHA、plan dependency与完全相等policy.rights；文件SHA/size与canonical document SHA分别保存在artifact/receipt与private refs。原prepare可以尚无授权slot；**本机unattended rights/verify必须收到恰好一项真实source**，缺件不会通过最终发布。不是“prepare成功就完整成片”。

**本机current事实。** bundle_authorization143–171对本机原immutable admission row/body/SHA、当前_binding policy与原installation action、当前ordinary fence的同plan execute_plan fact及当前ready receipt逐项核；foreign/不同Run/不同request不能借portable doc执行。旧doc允许作为原fence历史审计，执行仍需当前fence的实际fact。policy/action变更使旧doc拒绝，原bytes不能改写，需要同Run新actual plan admission/new preparation；Media实际接通此流程未测。

production_admissions142–198由已登记ProductionInstallationAuthority取得typed完整source/resource观察，issuer/control/thread对象作用域guard在writer外建立；166–198的真实锁/floor检查不等于一种JSON ticket。_request/_record220–282核原canonical Request、actual commands/Owner动作、revoked/current/期限/主体项目、route/input/source/transfer/cap/限次；production_authorization90–114再核真实route配置/cost-rule、Asset、既有budget group身份，official未实现不因policy被放行。真实安装/认证adapter未接，不能把typed测试观察或wellformed SHA称生产资格。

**最终可见writer。** bundles1060–1119要求同preparation、真实文件/媒体probe、8输出/17固定附件、关系验证、all operations succeeded+settled、历史无unknown，形成同lease/30秒验证cache。publish1143–1213在writer外重hash文件/Manifest和legacy final authority，在writer内核同ordinary lease、actual revisions/真实human approvals、final private context、权源/复制闭包、0.3 current registry、Manifest字节及文件identity；同一事务调用唯一_finalize再提交Step/published/Run。

bundle_authorization174–207的scope来自实际cache token、同Manifest/final context，受实际set membership及线程限制，并在进入scope时重核Manifest全SHA。production_admissions619–670只消费这个scope，核最新原Run/request/current policy/action/fence、真实begin/plan/continue-validation事实及quality/plan SHA、8输出/画幅/时长/原alignment mode，final_manifest fact与Bundle visible同writer提交且不回写Manifest形成hash环。普通production_admission516–543只准execute_plan/continue_bundle_validation；555–581不接受finalize_bundle。tuple/dataclass/AST数量不能代这些对象guard的实际运行证据。

**human与独立权源。** interactive仍用bundles267–301的真实immutable创作版本和真实approve decision，_check_revisions1043–1051要求script/quality审核。policy分支user_asserted只核当前Owner声明完全相等，不造ApprovalRef。owned/licensed在preflight398–424继续not_measured；legacy final callback只能在实际最终Manifest分支使用，不能冒已准preflight authority或安装资格。QC需要7项verified；continue-validation不是QC通过。未知Operation与预算不清零。

**foreign与projection。** _material_kind1706–1711和_import_documents1760–1779在导入严格核role/path/MIME（混用415），_parse_import1804–1842核完整archive/index/每文件SHA/size；_validate_import_relations1844–1898调用纯portable关系，不读取/安装本地策略、admission或qualification。import_bundle1953–2050只提交bundle_imports/本机内容映射/commands；foreign原许可/grant不继承到本机执行。

_selection1381–1403把授权doc加入projection，再扩plan/artifact/license全依赖；request_export1405–1410重新核扩展后完整集合的同purpose、单grant及semantic文本权限，不自动追加grant。foreign import export1700–1703仍需本机owner/operation/purpose和所选全部rights。此链只有源码支持，没有foreign完整阳性、撤销竞态或真实projection实测。

## 3 RV34-P01：portable原件漏核实际Owner动作项目范围

**P2 / OPEN / Backend；静态反例，未产品运行、未实测import，非本机执行越权。**

精确固定路径：
- `G:/开发测试/Codex/VideoCreatorImplementation/Backend/ProductionBundleAuthorization-B20/SourceCopies/services/engine/src/video_creator/domain/production_authorization.py` SHA `114aec63c3f7abdcfab68dd5eda2fc38b2497ae1fde89d61ccac847f05801489`，ProductionPolicyRecord190–198、ProductionAuthorizationDocument338–365。
- 同ordinary根 `application/bundle_authorization.py` SHA `ed2bd6753a0d577dddbf5182f3a11de8568b0bb2e2813293dbe8236461bbbb06`，validate_portable_authorization27–66，尤其55–61。
- 同ordinary根 `application/bundles.py` SHA `8d7b8f73ffd5ed260a8e263d9a58ddfa3690f5d33c69cda713f21544d2628df5`，validate_text151–189、_parse_import1838–1839、_validate_import_relations1844–1847。

真实本机ProductionPolicyRecord.original_action明确要求：
`(action.instance_id, action.owner_subject, action.project_ids) == (policy.instance_id, policy.owner_subject, policy.project_ids)`。
新增ProductionAuthorizationDocument.no_future_target核instance/owner/action kind、policyRef完整SHA、Owner-action SHA、resource身份，却没有project_ids关系。新的pure portable validator只核manifest.project_id属于policy.project_ids，未核Owner receipt覆盖同一policy项目范围。导入dispatch直接构造Document，不经过PolicyRecord。

最小静态负候选：其余原件和完整包关系合法的前提下，policy.project_ids=(project-A,)，Manifest在project-A；Owner create/replace receipt.project_ids=(project-B,)；保持同instance/owner/policyRef，并将修改后的完整Owner receipt SHA更新到plan_admission.owner_action_ref，更新doc原bytes/file SHA/size和相应Manifest artifact信息。类型现有validator与新增pure关系没有检查A/B差异；原件会通过这些**新增检查**。Reviewer未构造/运行这个候选，不能声称完整foreign import已经成功或实际资格存在。

影响：portable材料声称原策略由完整实际Owner动作endorse，但scope与其声称不符；hash一致仅证明自洽字节，不能代实际scope关系。依赖此原件做审计/RAG的调用方会收到相互矛盾的授权来源。**本机路径不会因此获权**：management._record构造ProductionPolicyRecord并核真实ledger；assert_local_current还要求实际local admission及current policy/action，外国doc不能绕过它。

最小关闭条件：Backend让strict Document/pure origin关系复用或等价实现现PolicyRecord的原动作项目范围一致性；不能为了import造current=True/假安装记录、读取当前本机policy给外国源续权或扩大公开model字段。保历史有效的origin_only、现本机current guard及独立权源门。独立Test另固定完整源，以合法原typed材料为基准，只修改Owner动作项目范围并重算相关原件SHA，实际经validate_text与portable/import消费方法验证拒绝；保持合法origin正向、badkind/path/MIME及foreign不能取得local admission负向。没有本轮运行批准。

相关inspection（**不另造已冻结标准或产品红**）：Document/pure关系未核Owner action authorized_at相对plan.checked_at的因果时间，或Owner action registry_revision不高于plan fact.registry_revision。现本机真实writer会在已存在Owner动作后签fact；pure字段可能声明相反顺序。建议Backend/架构明确历史原件的这些因果约束，再由Test固定负例；不将未经明确的新时钟规则塞入本P01关闭门。

## 4 已知未闭合消费及所需独立验证

复制/更正原件的policy-only闭环没有因此完成：bundles480–500的_origin_bindings_current仍对source和current user_asserted调用_assert_owner_right，要求真实human ApprovalRef；policy-only合法作品没有这些假human决定。新普通Owner-policy作品的本机检查已单独适配，但这个历史复制分支未适配typed policy来源。B20已明确Media/B15未完成，故列**未接消费**，不冒新实测失败、不允许通过补造ApprovalRef解决。后续Backend/Media/B15必须提供真实source/current许可与redistribution全祖先闭包，policy不能把licensed/owned变user_asserted或让unknown权利通过。

独立Test后续应分别冻结：实际配置的完整admission/plan/doc/preparation→rights/QC→cache/scope→同writer final fact+publish阳性；错误/伪造/退出scope/跨thread/token/context/fence；撤销、expires、route/input/group/plan/quality/Manifest漂移与事务回滚；unknown/未settled拒绝；policy改变后旧doc拒绝及新prepare不改旧bytes；human审核回归；foreign坏scope原件与合法origin_only；projection只grant视频但缺doc/plan/license依赖时拒绝、完整授权集合正向；policy-only复制原件的许可闭合。只纯double/AST不能替实际服务/完整Bundle、竞态或三OS。Test准备/实际launch仍需后续独立准入，不由本评审批准。

实际安装/管理员认证/bootstrap、Media新增stage和policy分支、B15 licensed素材复制、完整成片音视频听看、真实ASR精度/恢复、最终权源authority、foreign/projection阳性、撤销竞争、public schema/export与SDK接通尚未完成或未测。原ASR/_admit/sharedWorker自动审查拒绝不绕过。本轮SourceStage不是永久503或缩R1设计；完整R1三OS独立验收后连续R2、安装处持有数据、五步前台不变。

## 5 原静态证据与终态

B20原2536c3 Ruff exit1三处I001和e95954相对cwd读取错误保留；7a9fe2是中间Ruff0，后还有Protocol/projection源码变动，**以最终17d643固定片为准**。StaticReceipt SHA `1d8a51decdf605be57182689114c5b25f12bc6d23e2c96b9edc6a11e826c2159`、CommandReceipt `4fc63987c3c7b4df2a20db80c9fc159179beeac4d10e0ba5a1679d5462691b13`：owner48172/ruff49780已wait exit0，41 AST/5目标Ruff0/47copies/原46before副本无漂移。它们只支持静态检查终态，不继承T26实际隔离机制为B20 Bundle运行通过。

RV34InputPins/FactsCheck/SourceAfter保存精确输入、五源diff关联与源后66pins无变化。所有源码/evidence读者终态释放、live=[]、current freeze=false。只写本报告与 `G:/开发测试/Codex/VideoCreatorImplementation/Review/BundleAuthorization-RV34/`；产品/import/DB/测试/ASR/native/模型/provider/keys/fee/network/install/apply=0。工具输出少量截断不计已全文审计；必要相干方法已分别有界补读，未进行全历史重复审计。

