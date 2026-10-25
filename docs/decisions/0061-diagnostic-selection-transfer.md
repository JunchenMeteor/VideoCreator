# 0061 — 诊断事实追加与当前选择的原子转移

状态：ARCHITECTURE_CONTRACT_CORRECTION_READY_FOR_INDEPENDENT_REVIEW。本轮架构合同修正，未经后继独立复审/实现/运行/验收；不关闭CFDJ-P01或BDE-P01/P02。旧0060 SHA8fc928e2ea0ff418a0ee1cfe998baf5d86873d542989bf2f22f100df114d184f完整原字节保留。本文有限替代0060§5–7中“record后即成为当前选择”的不完整接缝，并补其§3 source伴件的选择证据；其它失败join、一次wholeverify、两authority、200000us、rights/整份plan/费用/unknown及R1后连续R2目标保持。后端唯一维护私有types/实现，媒体只消费。

## 1. 实际缺口与设计边界

固定127普通源 component_diagnosis_service.py:477–540 的 record同时追加Fact和写component-diagnostic-selected.<preparation_id>。518–525先拒绝任何不同selected ref；同一prepared确有新completion/input-v2时也无法追加。31–55原发布门读取此SELECT_PREFIX，而596–619 reader读取当前journal ref；仅改变journal会造成发布门继续消费旧inconclusive来源。bundles.py:1418在原publication_guard和可见性事务内调用该门，不能绕开。

保三个不同概念：不可变已记录Fact；尚未选定的候选；已由真实writer提交的当前选择。新增Fact不推翻旧选择或失败，不授制作/发布。仅下述两种writer可以提交选择：原Runtime.park_current_final_evidence的等待转移；首次无等待账本的原BundleService.publish可见性事务。prepare/append/read/join不改变选择。其它角色/模型/renderer不能调用底层writer。

## 2. 唯一input结果与append-only端口

Backend在原CurrentFinalEvidencePorts添加两个私有方法，原四诊断口及旧public DTO不删除：

- append_component_diagnosis(inputs, observation) -> RegisteredComponentDiagnosisV1：只追加真实已succeeded/settled分析的Fact及唯一input结果索引，不写SELECT_PREFIX/journal/companion。输入必须是本服务登记的V1/V2 held inputs；原factory纯verifier、真实Operation/route/cost/source投影、绑定/全文大小及current守卫全部复用。新路径由原注册Media producer在真实analysis-only续步调用，不能是用户接口。
- read_recorded_component_diagnosis(inputs) -> RegisteredComponentDiagnosisV1 | None：准确held registered input/key的纯读取，不接受任意ref、SQL、prefix或“最近记录”；None仅该准确input从未记录。已记录但损坏、跨binding、源失效分别拒绝，不能把异常变None重新分析。

为脱离selected仍保持same-input唯一性，增加私有metadata key component-diagnostic-result.<full_input_sha256>，值为原ComponentDiagnosisRefV1的准确canonical正文。索引不是权限，Fact仍原component-diagnosis.<input>.<factSHA>及原FactV1 bytes。原短事务同时INSERT Fact和这个唯一索引；index存在时必须核原record/size/SHA、完整input/Operation/source再纯复用。同input不同Fact不论当前有没有selected均409；同record_id不同真实正文也409。不能仅扫描selected判断唯一性。

正确调用序为read_recorded→确无记录且原账本允许时分析→append。恢复先read原record，不以新fence重新生成包含authored_fence的Fact；实际原author fence保历史字节，新held读取使用当前lease/fence。两个并发候选只能同input同record幂等，不能靠新fence/content SHA建立第二Fact。unknown/submitting/unsettled先原reconcile，未核实不新key/route/额度。

旧record_component_diagnosis默认语义保留：旧v1调用仍真实first-select/同ref复用；不同selected仍409，不能偷偷改成覆盖。其内部可共享同一个fact/index校验，但要保原失败事务效果：旧默认调用若selected冲突，不能先commit新Fact再抛旧拒绝。新增恢复路径必须显式调用append，不靠Bool参数把旧record改宽。新旧方法共用唯一input索引；旧有效record没有索引时，只能从已验证的旧selected/准确registered input定位其原record、核全文和实际Operation后建立同ref索引；多个同input不同事实409，损坏422，不选latest/修原字节。

## 3. 当前选择的真实held准备

BundleService新增私有 prepare_current_diagnostic_selection(lease, preparation_id, recorded, *, continuation=None) -> PreparedDiagnosticSelection。recorded只接受本服务登记的真实RegisteredComponentDiagnosisV1对象，不接受外部Ref；返回Backend唯一定义的eq=False、短期held对象。它只是待提交选择，不是committed状态或执行权。原join/current analysis-assessment builder关联该对象，供原writer读取；不能由Media传expected_old_body决定授权。

held内容来自真实读取：完整binding、当前lease/fence/thread/prepared+intent；new record/ref与registered input全文/格式/Operation；原old selected整行/准确原body（或经实际读取证明absence）；old exact journal body及准确source companion body（均可真实absence）；current parent/assembly/READY/route/creative revisions和实际资源/current guard捕获；真实continuation/resume_context/完成源；目标转移first_select/retain/successor。所有准备/大文件/纯verifier在SQL外，关键metadata行再由短writer重核。

old selected若存在，先严格parse原ComponentDiagnosisRefV1、核原Fact全文/size/SHA及binding/parent，原body也须保存；既不能只比ref equality/hash，也不能把损坏当absence。old journal存在时，其snapshot或0060伴件中的有效diagnostic_ref必须和old selected一致；解析或来源关联冲突409/422，不清pointer。probe→queue→claim期间也捕获并重核该old selected body，避免另一分析在新fence之前偷偷换当前来源。

允许选择：

1. retain：当前old selected==new ref，真实source/readset仍当前，准确原输入记录复用。
2. first_select：目标prepared的SELECT_PREFIX真实不存在。若也无journal，只能原初始流程在实际验证结束后park，或实际Verified publication事务提交；若已有journal，则须原真实continuation/合法selected-child来源指明该prepared，不能借未选定资产改父准备。
3. successor：old ref!=new ref必须不同input key。原0060已登记resume_context.previous_diagnostic_ref、previous waiting/source及actualcompletion证明链，须准确等于捕获old ref/body；newinput真正消费该completion且原分析已settled。同input不同ref始终409。不同prepared/Run/registration不属于此转移，仍原祖先/child选择门。

任一新record没有上述实际来源，最多是未选定历史Fact，不可进入失败join、修复proposal或发布。准备时不写SELECT_PREFIX，不覆盖Fact；旧选择继续拒绝组件错误。

## 4. 同短connection提交selected、journal及source

原Runtime.park_current_final_evidence(lease, assessment)签名不扩成用户选ref：assessment只能本服务真实原whole结果join或0060已准真实analysis continuation builder形成，服务内部登记关联PreparedDiagnosticSelection。Runtime原current_guard/lease/thread/TTL/settled/pause/cancel/human wait与selected-child门不改。新增BundleService.commit_current_diagnostic_selection_writer(connection, lease, selection, *, transition)为原writer内部方法；不得自开事务或向Media/公共API暴露。

顺序必须在同一个原短事务：

1. 重核held identity、current Owner/request/action scope、actuallease/fence、所有old captured rows，包括old selected完整body、old journal和source伴件；核原new Fact/唯一input索引/实际Operation和completion源。new Fact必须已经commit，不在此调用provider或重分析。
2. 构造准确new journal/source正文。选定指针仍存原ComponentDiagnosisRefV1 bytes，不换成新包装。first_select用absence条件INSERT；retain核原body不变不重复更新；successor以key+准确old body执行UPDATE，必须rowcount=1。失去absence/old body任何CAS都409。
3. 原journal也以准确old body/absence CAS；写new exact journal SHA伴件。双方更改及事件/Run waiting状态都处于本connection，任一失败整体rollback。不存在selected已变而journal/source未commit的可见中间态。
4. writer再次读取并核selected==准确new ref/body、journal==准确newbody、source==准确newsource；原诊断writer/生产issuer及全部未改变源final assert。自己的SELECT_PREFIX与journal变更只能在先核old且CAS成功后用准确new整行替代那两项captured rows做最终检查；不是直接过滤、True guard或忽略全metadata。其它源、Operation、route、READY、许可/current拒绝都保留。

0060私有source companion新增严格后继 current-final-diagnostic-source-v2，旧v1 parser/bytes仍接受但不新增解释。v2保v1所有origin/failure/context字段，另必填selection_evidence：selection_kind（first_select/retain/successor）、old_selected_body|null、old_selected_ref|null、new_selected_body、new_selected_ref、new_registered_input_ref、old_journal_sha256|null、previous_committed_source_ref|null。old body/ref同时为null或同时准确；newref和input对应，且和newjournal snapshot.diagnostic_ref或source.diagnostic_ref一致；original_snapshot可切回普通v1精度等待时，准确新诊断ref仍存source，不清失败。newjournalSHA只向source单向定位，无自SHA环。

旧0060source-v1若没有selection证据，仅当真实当前SELECT_PREFIX和其显式ref/正文/source完全一致时可纯retain；不能从v1猜successor。新选择转移写v2，旧record及oldsource不改。queue/claim只复制已committed选择到new journal SHA的v2伴件并重核selected，不能选尚未完成的新candidate。真正successor只在analysis完成后的park事务提交。旧v1 ordinary无diagnostic仍原路。

## 5. 首次无wait的实际publication writer

初次append后可能诊断为no_component_failure/timing_only，原once wholeverify返回真实VerifiedMaterial而没有waiting journal；该路径不能永远因SELECT_PREFIX不存在拒绝，也不能在append时先洗成通过。

在原join成功分支将prepared selection关联到本服务当前verification_id/真实VerifiedMaterial，仍原30秒/lease/thread/actualfiles/current绑定。BundleService.publish在已进入原publication_guard的同可见性connection、已核原preparation之后，且在1418的assert_diagnostic_publish_writer之前，仅允许以下首次动作：准确old selected absence、准确old journal absence、真实newrecord supported且result不是component_repair/information_required、selection.first_select、当前VerifiedMaterial及完整原guard。调用同commit writer的transition=first_publish；不能通过该路径迁移已有不同选择或存在等待journal的选择。

first_publish在同事务写原SELECT_PREFIX及一个私有不可变 publication selection source，key component-diagnostic-publication-source.<preparation_id>.<actual_manifest_file_sha256>，format=current-component-diagnostic-publication-source-v1。字段限binding/preparation/intent、actual manifest SHA、authored fence、selected_ref/body、registered_input_ref和准确old absence/source evidence；不存可复活的VerifiedToken。该记录是选择历史，不能凭hash代原当前verification/rights。已有同key/body只作准确幂等；differentbody409。

随后原assert_diagnostic_publish_writer必须运行并消费刚提交于本事务中的同一选择/真实held reader，原correction/CTC/all Operations/creative approvals/final rights/current/source/文件签名/_finalize_bundle_current/交付账本都保持；任一失败连首次选择/来源一起rollback，Fact/index已保存但仍未选定。成功则选择和实际published状态/交付Step同事务可见。指针不存在而没有该真实first selection仍原409，不放宽required gate。legacy旧record先selected及无新路径时仍原guard，不新造absence事实。

存在journal/old selected不同的新no_component_failure先完成第4节park→真实resume/new fence→原最终验证；不借publish执行successor或直接把旧inconclusive删除。selected已准确new ref的正常publish只retain，新的guard重核current journal/source/selected，不再选另一Fact。

## 6. 三消费者一致与恢复ABI

Backend须接真实调用者而非只有声明：

| 端口/方法 | 调用者/结果 | 选择权限 |
| --- | --- | --- |
| Ports.append_component_diagnosis(inputs, observation) | 原Media新恢复branch→真实RegisteredDiagnosisV1 | Fact/index追加，零selected变更 |
| Ports.read_recorded_component_diagnosis(inputs) | 原Media先纯读/崩溃恢复→记录或None | 精确input；未选定也可读但无执行权 |
| Bundle.prepare_current_diagnostic_selection(...) | 原join/analysis assessment builder→eq=False held | 不写选择；实际old body/readset由Backend读取 |
| Runtime.park_current_final_evidence(lease, assessment) | 原worker等待出口 | 关联held选择，同事务selected+journal+source |
| Bundle.commit_current_diagnostic_selection_writer(...) | 仅原Runtime park或原Bundle publication内部 | 不开放独立提交/rendererref/任意key |
| 原read_component_diagnosis、join、assert_diagnostic_publish_writer | 原真实continuation/已关联held/newpublication事务 | 只消费同一committed选择，或明确待提交候选限定读 |

原read_component_diagnosis增加严格一致性门：current journal/source显式ref、SELECT_PREFIX整body、唯一input结果索引/实际Fact必须同一选择；actualexecuting continuation和fence仍必须真实。普通v1精度等待的诊断ref从其真实v2伴件取，不凭类名猜空。新内部join可以消费已由当前registered input明确读取的pending record，但必须关联合法held selection，其输出只供上述commit writer；未commit的pending result不能用于publication或authorize_affected_execution。

独立candidate read和committed read不能混为一口的“任选ref”。同parent多未选定Fact不拒绝合法准确registered input，而按该input结果索引唯一读取；但没有受控input时禁止从held集合挑“新est/任一”。原success-only helper的多held冲突不能靠删字典/任意选择绕过，Backend改为当前准确selection/candidate关联，其他未选择事实只是历史。

resume无lease probe把准确old selected body加进readset；queue/claim同CAS仅建立诊断续步，selected保持old。analysis→append后、park前崩溃：new Fact/index保留；current selected/journal/source全部仍old。新actualfence恢复按准确resume registered input纯read，原analysis Operation succeeded/settled则零重dispatch/扣费；unknown先原核实。重建held selection再次核old selected/body和current source，park原子切new。不能把旧thread对象/serializedselection跨进程当授权。

park已成功但响应丢失：读实际current source-v2/selected/newjournal完全一致，仅观察已commit并按原Runtime后续，不再用已失效lease重复park/重收费。若其中任一不一致则409/422真实拒绝，不能自动补一半或把mismatch视“已完成”。first_publish响应丢失亦按原实际published/manifest/Step观察，不能重建发布许可。

child/祖先仍按0057真实selected-child/command/lineage。新的current selection一致门作用于该当前准备/显式已commit来源；原合法历史lineage对其immutable旧Fact的纯读取仍合法，不用后来父selected指针覆盖历史command。历史读不复活旧执行权；当前修复/发布仍核实际selected child及原完整guard。不扩大祖先授权/许可用途。

## 7. 错误、验证和后继

403：假的held选择/跨服务或thread/expired原current、Owner/action/rights撤销；409：sameinput不同Fact、old selected/journal/source任一CAS变化、未选定pending用于修复或发布、missing actualinput/fence、sourcechain/多记录冲突；422：严格正文/原immutablebody/unknownformat损坏；503：确未装driver/resource verifier，不能将冲突或撤销变not_ready。未知收费/Operation保持原unknown及核实，不取0/重置限次或新key。

Test独立后继须真实验证：旧inconclusive→真实completion/input-v2→new settled Fact追加而旧SELECT/journal仍原样→原park同事务选择转移→原最终验证及原publication selected门；append后park前kill/新fence纯复用0新调用/收费；指针/journal/source分别CAS竞争及原许可current撤销全部rollback；同input新author fence不重构Fact、不同Fact409；first nojournal publication真实成功及rights/CTC/第二authority/文件变更拒绝连first-select回滚；pending no_component_failure不能绕old选择；已commit响应丢失只观察；legacyv1 bytes/同ref默认record/timing/edit合法路径、原精度闭包/200000us/wholeplan及unknown均不变。本轮不编写标准/测试或运行。

原Review独审本后继，CFDJ-P01的关闭由其独立判断，原实现findings仍OPEN。Backend唯一新增私有类型/index/source-v2、两个ports、held选择、实际park/publication与读取一致门；先交实际source/type/caller固定ABI。Media改新branch调用append/read，不造选择或DTO；Integration对实际新增源和私有grammar按原安装source coverage打包，未涉及公共SDK不得手造新版publicDTO。原Test/Review/Acceptance另授权独立行为验证；环境/三OS/真实模型资格不由本设计授予。

固定输入身份与必要正文：任务7342d26e全文、正式Report a22dfe71全文、唯一Finding b28e7c00全文、FinalHandoff71776ca7全文、旧ADR0060 8fc928e2全文字节；component servicefa2d8f89:1–80/477–541/596–620、runtime4609dcea:93–140/209–258/288–318、bundles589a0d4f:1413–1450，均来自上一架构停止ordinary，127 SourceIndex2647be66不变。不是127全部源码正文评审。过程保存完整SHA/原输入后核/有限ordinary/Handoff。工具只文本读取与自有元数据核对，产品/SQL/Pydantic/native/网络/模型/测试/费用/密钥/安装/第四历史目标均0；完整R1后R2均未验收。
