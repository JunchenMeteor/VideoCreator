# ADR0026：历史策略来源与当前复制许可

2026-10-09。状态：**窄语义补充准入；Backend 两端消费及真实许可/复制闭环待验**。只 Architecture；完整 R1 后连续 R2、实例持有数据、五步 UI、原质量/精度门不变。无生产/import/DB/测试/模型/native/网络/凭证/费用操作。

## 依据与唯一裁定

完整读 ADR0024 §2/4/5/6 和 ADR0020 §1/3/4/5，核正式 RV34 §4 的未接消费及 B22/B23固定接口。B23当前只是默认None的SourcePolicyAuthorization容器；_correction_source_artifact初始门和_origin_bindings_current最终门仍human-only，不宣称已接通。B23的47 ordinary身份固定，未读活动生产或Test/Integration WIP。

既有规则足以区分三件事：ADR0024 §5便携材料是原授权来源审计、不是外国ticket或复活策略；§6当前执行/最终writer必须核current/revoke/expiry/fence。ADR0020 §3已published历史字节不覆写、当前使用/导出另判；§5源条件与当前新声明分开。因此裁定：**真实历史Owner声明不会仅因原制作策略后来replace/revoke/expire而变成“从未发生”；当前复制也不因此取得许可。**不用一套新授权/法律机制替代现ledger、current admission和PreparedRightsAuthority。

| 来源情况 | 原声明证明 | 新复制的独立条件 |
| --- | --- | --- |
| 本机human源 | 原不可变版本及真实approve仍按原human门核 | 当前新作品真实human或当前policy声明、source/current全部rights/用途/许可闭包有效 |
| 本机policy源，原策略仍active | 实际local policy正文/原Owner动作/原plan admission/Ready doc与plan证明过去声明 | 不能把source当前active当新Run许可；另核当前新声明及ordinary fence |
| 本机policy源，原策略后来被替换、撤销或到期 | 原不可变事实真实、当时有效且完整绑定时，仍可作为历史声明来源；不要求旧source creator lease现在活动 | 仅在source RightsSnapshot及每项真正许可当前仍有效、未被实质撤销且允许实际copy用途，并且新作品另有真实当前许可时可继续 |
| source RightsSnapshot/许可已过期、尚未生效、实质撤销或用途缺失 | 历史发生记录可保留，不成为当前有效permission | 当前copy拒绝；新policy不能给旧许可续期或清撤销，需真实新来源许可/受控证据再走既有完整绑定 |
| foreign origin_snapshot_only或无实际local action/admission/journal | 严格portable关系可作历史审计 | 本路径不得发本机source/copy/制作票据；可读/导入/同Owner不等redistribution |
| owned/licensed外部权源 | 按真实已准入authority来源核 | 未准adapter/许可继续not_measured/not_ready，不转user_asserted、不用policy覆盖 |

“策略撤销”在既有协议中是撤销未来自动执行权限。它**不隐含**撤销全部版权/许可或抹除既有声明；实际rights/许可证撤销必须来自真实具该范围权力的主体/已准入权源及明确对象/生效事实。反过来，一份旧RightsSnapshot没有实时撤销信息，不能凭自报字节宣称外部许可当前有效。架构不决定某具体许可法律结论，也不新增用户商业政策。

## Backend 两端的最小接口条件

保留 `correction_origin_evidence(ordinary_lease, reference, *, purpose)` 与既有typed容器。唯一Backend私有历史read/assert helper可以放现bundle_authorization；名字由Backend定义，不注册API/MCP、不另造public DTO、管理策略或新SQL表。不能直接把当前执行专用assert_local_current套在旧source Run上，也不能删除当前新作品的这个守卫。

1. **真实source读/准备（writer外文件部分）**：从same owner/project、本机真实Ready BundleRef/Manifest/index/journal取得source授权doc及其真正plan。核每件原file SHA/size/MIME/kind/role/receipt、strict grammar及完整portable关系；计划的CreativeRevision/原canonical SHA、SourceManifest/原Production/Run/request身份逐项匹配。Bundle imports/foreign locator、caller传doc、filename/hash/None容器都不能代本机事实。SourcePolicyAuthorization仅承载实际这些对象。
2. **历史ledger断言（初始短读与最终writer均做）**：与真实local production_admissions原execute_plan行/body/SHA、原PolicyRef/不可变policy正文、真实installation create/replace action及原commands幂等请求/receipt、原主体/完整项目scope和实际plan/right声明相等。原fact的checked_at/有效范围是**当时**签发事实；其原fence/valid_until/resource绑定不能作现在许可，但不是仅因后来fence或期限结束就删历史证据。使用现管理记录的不可变identity核，不借issuer `_record/_bound` 的当前active执行分支给source换新lease或重签admission。保存并区分记录当前已replace/revoke/expire的状态与历史identity；已有明确说明原事实无效/被伪造等完整性证据必须拒，不能用“历史”逃过它。
3. **当前新作品断言**：当前Production/Run/request/preparation/ordinary fence和当前声明完全匹配。human路径保真实approve/target；policy路径保现assert_local_current及实际current Owner action/policy/route/input/resource/预算/期限/撤销/floor，不得写假ApprovalRef或用source旧admission代current fact。其输入source范围必须真实覆盖该源；不能只核新作品general policy存在。_origin_bindings_current分别核source历史与current执行，不把二者合成一个current Bool。
4. **真正权利断言**：初始事实和final writer都核source/current RightsSnapshot、每source grant及许可/依赖的当前用途/期限/撤销/authority revision与narrowing。初始成功只产生本次服务事实；final仍按ADR0020 §3当前同connection短核。文件/全文SHA/外部权源观察在writer外，writer只读本地受控ledger/journal/current撤销及期限，禁止联网/文件hash/供应商调用。过期cache、wrong fence、source身份变化、撤销revision/floor失效均拒并重新受控核实。

历史helper不要求原创作策略**现在**current；但必须核真实原事实在当时由受控服务合法签发，不从纯portable字段重建“当时True”。不额外引入尚未批准的Owner时钟容差/registry因果标准；RV34相关inspection不由本ADR冒充独立测试通过。现管理/来源更新不能给历史原件回写当前policy或未来hash。

## 声明与许可的有效性、撤销和恢复

user_asserted仍只是实际Owner的完整声明来源，不是独立所有权认证。source policy中那一份精确rights正文/声明ID必须对应实际source right；当前copy声明另需实际新human/policy来源。按ADR0020 §5保basis/holder/license/署名、用途/平台/地域/limitations交集及期限narrowing，不能把source licensed改成user_asserted或以一份当前较宽声明覆盖原限制。旧字段None沿既有明确语义，不拿它填“未知当前撤销状态/无限有效”；外部权源current可核性缺失继续未配。

执行policy替换/撤销/到期，不是rights撤销渠道。实际外部grant/许可状态由原已准入PreparedRightsAuthority的真实来源、更新/撤销渠道和有限本地观察核；Owner user_asserted仍按其明确有效声明与现实际权限边界核，不能凭一次source策略revoke推断其所有rights也撤销。若Owner明确撤回某source权利声明，必须是真实授权动作且绑定实际source/right identity并经受控来源服务纳入current检查；现policy管理revoke receipt没有这个rights动作含义，不虚构本轮已经安装了该来源。缺此事实接口时准确交Backend/权源owner按ADR0020现source当前检查实现，不能创建一个模型Bool或假rights revocation。**本ADR不新增权利撤回政策、表或管理API，也不授予原制作policy更大的权利处置能力**；所规定的是实际权源提供撤销事实时的既有current守卫效果，缺资源/来源如实pending。

真正source权利已失效时，停止该依赖的新copy/publish；恢复须实际获范围许可的Owner或已准入issuer提供新的明确来源许可/声明与有效证据，按既有新不可变source revision或独立新权源绑定路径处理，保旧原件审计。不能修改旧RightsSnapshot/报告bytes、清撤销、把当前一般plan approve当源再许可，或自动扩大原合法copy分支。当前制作policy缺失则按ADR0024 waiting_authorization→真实重新授权→queued新fence恢复，保同Run既有资产/Operation/预算；source真正许可缺失单列具体rights blocker，不盲重render/重新收费。

已合法published/export的历史字节不覆写或假装召回；今后的read/playback/export/redistribution根据真实请求目的分别判。保存历史可审计不等重新公开披露，content可读不等whole Manifest或proof/许可全文可导出；原leaf-only grant、purpose和projection闭包不扩。

## 完整证明集合与祖先闭包

SourcePolicyAuthorization进入source_set/context/cache时，绑定实际source BundleRef/Manifest、doc Artifact/Receipt/完整file和内部record身份、plan Artifact/Receipt/实际revision、原policy/action/admission identity及对应source right声明SHA；不能只hash policy ID或拼四字段就标ready。服务签发事实绑当前请求/lease与完整已核source集合，None旧human路径继续原校验/旧hash语义；新增policy分支的canonical及私有事实格式由Backend唯一固定后给Media消费，不getattr猜兼容。

doc和plan是本次必需**核实来源**，参与32祖先报告/256 source artifacts/实际max_bytes集合与完整性/访问检查，按真实identity去重；它们的验证引用不能伪造artifact dependency自环或豁免真实graph环。它们不因私有核实便自动成为当前交付附件；若被Manifest索引/声明交付dependency或通过投影导出，就按自身真实rights/许可和原role/path/kind规则取得实际复制/披露/redistribution权限并完整stage，不能仅因为“是证明”默认可复制全文。后端不得用同source授权doc自我声明为独立legal authority。

每个祖先report、原父index内child、许可文本及其自身right/必要依赖逐来源走同一human/policy/authority分支。C→B→A、0.2/0.3严格dispatch、file SHA与record SHA分离、source许可→新许可ID映射、原byte/new allocation、完整边及narrowing、环/冲突/资源上界保持ADR0020 §4/5。相同bytes不同权源不能去重成较宽范围。新current授权doc仅授权当前作品，不能取代A/B的来源证明或许可。源许可撤销在final再次被发现时不得以preflight/原cache绿继续提交。

## owner、拒绝与独立验证输入

- Backend接通 `_correction_source_artifact` 初始门、服务签发完整source/context/cache、`_origin_bindings_current` final source/current两端；真实source history helper和current execution helper分开，完整许可与实际revocation来源仍受控，不实施fake授权。
- Media只消费后端正式typed facts、source_set/context版本和许可完整集合；新allocation/stage/immutable byte不变，不能私有SQL/签policy/构ticket/反射None放行。Integration如实际public schema未变无需手改SDK；发生实际契约变化仍由Backend唯一导出、集成再生。
- Test/Review独立固定验证：合法human与current policy source；source policy后来replace/revoke/expire但rights合法且当前新copy授权的阳性；同源仅声明来源而缺当前许可的阴性；source真实rights/任一祖先或license过期/实质撤销/用途与redistribution缺失；foreign/无localledger/错误scope或right/doc/plan/receipt；proof可读但不可披露；初始到final source journal或当前policy/权源撤销竞争；完整多层许可与typed/hash/None回归、guard/source floor、资源和环。此为验证输入，不新增/改已冻criteria或声称产品运行通过。

错误沿既有语义：坏原件/ledger/grammar422、不可用或变动source409、实际缺当前用途/有效权利403、未安装真实owned/licensed authority503并not_measured；当前unattended制作授权缺失走原waiting_authorization可恢复链。Backend固定准确ErrorEnvelope/code，不吞失败为origin_only许可、不永久human-only/503代R1。B23静态0只证容器/文本，本ADR不授法律许可、真实Owner/action、权源adapter、复制/作品、三OS或Gate验收。正式来源/交接及all reader terminal后立即释放。
