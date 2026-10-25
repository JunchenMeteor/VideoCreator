# RV56：F9 恢复定位修正独立源码评审

结论：**RV55-P01 可限于原列表改写恢复定位的源码链关闭（CLOSED_SOURCE_STATIC）；新增 RV56-P01、RV56-P02 均 P2 / Frontend / OPEN_SOURCE_STATIC。** F9尚无UI/API/typecheck/build实证，不能授完整恢复、跨实例行为、RuntimeBinding或Gate/R1/R2。原F7问题和T38/F6结果各自保留，不回填动态通过。

## 固定身份与范围

F9 MD 644076f74cddb933ca422b3549b9d169513acf61c60003699ee72c2a6dc08ecb；JSON 706324ceda60b79296f0d9a2a94c914cead48bb3fddd49654384fe2834329cd8；Snapshot d4d42a25bf377f7f2b62b83328a7ed8803406e16ee0adb73f2a75d310253fb1a；Delta ea736903327a87a80cbed84cdc38205bc627a06d02d3edb5d81f6cc0f8a7f4a6；InterfaceConsumption 893006e1fa1ad57a93bc3712df121c5483f2454f83c147ad3eb4771c847c29ab。

十一固定普通源只Workbench修改，56494B / SHA 6a2abf795ce6a92e708b4dac7c9234633c86d56254a1871670b63d0d04678980；其余十份不变。本次26固定路径全部hash/大小匹配且after无漂移，完整绝对路径见自身RV56Snapshot/SourceAfter。只F9普通源、原RV55报告/交接、F7固定Workbench及索引、既有I33普通SDK；未读当前production SDK、Test/I44活源或环境。

## 原 RV55-P01 窄源码关闭依据

[Workbench.tsx](G:/开发测试/Codex/VideoCreatorImplementation/Frontend/RecoveryLocator-F9/OrdinarySources/Workbench.tsx:132) 17、55–58、132–144、153–156：三身份locator由唯一生成ProductionAccepted的Pick派生，不再裸productionId跟随editor。已有同实例locator时effect早return；补空的functional updater也保留同实例已有选择。因此同实例恢复A后，B后台列表新增/变更或B草稿null不会按旧122–127链覆盖为B/null。失败/消失不猜换另一任务。

89–99详情回包及selectedProduction消费核instance/project/production；Run订阅取已核最新run_id，事件再按run/production过滤。361错误刷新、368状态/操作、369交付都取选中任务链。372任务行不再load/flush/save A，dirty B也可只读打开A；356、363区分所看A任务与保留B表单/保存状态。158–166和357提供明确回到当前创作/项目成功载入/新草稿语义。只支持上述静态修正，不证明React调度或跨实例完整闭环；下面新问题限制该更广资格。

对原F7三段独立提取字节对比：retainProductionReceipt SHA d73cd616f6975db8e7702e120260c464d5a5165a27e695aa666991de1c6af496；createProduction cc3978cdf929933225a09070f9b5cf904dbb049cfb13d728f3b57d072f8fd3a4；recoverProduction 15641e702efef038ad4a836960660dfcd6c59b15b16fa86b17e031dcc51316a5；全部与F7相同。原body/key/instance/project校验、匹配ACK保存定位先于解除unknown、已知receipt仅GET、后来拒绝/存储失败不clear旧unknown、首Run和latest GET分开保持。但字节相同不代表调用的新定位链完整通过。

## RV56-P01 — 实例守卫晚于编辑器回包写入（P2，Frontend）

主位置 [Workbench.tsx](G:/开发测试/Codex/VideoCreatorImplementation/Frontend/RecoveryLocator-F9/OrdinarySources/Workbench.tsx:159) 159–163，SHA 6a2abf795ce6a92e708b4dac7c9234633c86d56254a1871670b63d0d04678980；关联 [useProjectEditor.ts](G:/开发测试/Codex/VideoCreatorImplementation/Frontend/RecoveryLocator-F9/OrdinarySources/useProjectEditor.ts:33) 33–45、47–53，SHA 6ef1cf47a7bb881795aed17621e47896096bd2a5be120b41eb994e2aca0d9ad8。

最小条件：实例A启动project GET并挂起；同一Workbench/hook切到实例B，B项目/表单已载入或修改；A回包后来完成。F9新selectProject先await editor.load，再检查currentInstance。固定旧helper 37–42在返回前已经写projectRef/formRef、setProject/setForm、setEdited(false)、phase及旧实例locator；44旧请求失败也写phase/error，没有实时实例或请求世代检查。因此新guard只能阻止returnToEditor，不能撤销旧A对B表单的覆盖/dirty清除。旧helper本来存在，此处指出新包装guard并未补足它，不能称这些旧行是F9新增代码。

影响已限定为静态可到达的本地编辑状态错写/输入丢失风险；没有运行UI，未观察或声称autosave/PUT已经派发，更未声称后端存储被实际覆盖。正常新请求是否存在同ID及后端如何拒绝不是关闭本地错误的依据。

修改条件：实时instance与request/navigation世代必须在helper内部、每个异步回包修改ref/state/phase/locator之前检查；旧错误和收尾也不得清新请求状态。可取消旧读，但取消本身不替代身份/世代守卫。保留当前脏输入，不能为了绿把它载入覆盖或绑定到其它实例。独立Test应延迟A GET，切B完成载入并修改B，再放行A成功/失败；逐项核B project/form/dirty/phase/locator和原请求观察，不允许把未运行的autosave推成真实证据。同实例先load后新草稿/后导航的世代逆序也应核。

## RV56-P02 — 取消确认没有绑定打开时任务（P2，Frontend）

主位置 [Workbench.tsx](G:/开发测试/Codex/VideoCreatorImplementation/Frontend/RecoveryLocator-F9/OrdinarySources/Workbench.tsx:301) 301–312；相关55–57、65、132–144、368、380；同一完整SHA如上。

最小条件：A任务上368点击取消，只setCancelOpen(true)；尚未确认时health/受控连接切到B，同一组件仍挂载；B项目/列表/详情加载完成，自动补出B任务，loading结束且connected=true。cancelOpen 65只是boolean，111/132等实例/定位effects没有清它，380通用确认框仍开；确认时301–307才捕获**当前selectedProduction B**并向B的production_id POST cancel。308核回包对的是此时捕获B，309核的operationInstance也是B，不是用户打开A确认时的身份，故这些回包守卫不能阻止错目标提交。

这个反例需要B已具备有效已选详情，B未连接/尚无任务时302会拒。无需假设能穿透modal点击底层导航，实例后台变化和项目列表自动载入链足够；仍仅SOURCE_STATIC，不是实际UI/HTTP取消复现。原F7也有确认时读取当前任务的模式，本轮不是把继承行为伪报成新增行，而是F9跨实例定位准入仍缺这一关联。

修改条件：打开确认时保存并显示原instance/project/production目标；目标或实例变化即失效/关闭，确认只向该原目标且当前授权连接一致时派发。保留回包身份守卫，不以放宽权限、换key或自动改为当前B修正。独立Test应A打开dialog→切B加载新任务→确认，断言B cancel POST为0；正常A确认只对打开的A发一次，并核迟到回包不改新实例状态。

## 其它有限支持与未测

pause/resume/feedback 272–299读取selectedProduction最新Run和由该Run事件绑定的reviewRevision，body只有指导决定，不带编辑B的goal/source/project。操作回包/提示增加currentInstance检查；取消回包增加三身份检查，原始源码方向正确，但不能替代打开确认时绑定及helper内部守卫。后台列表保护、主动导航busy按钮与原GET/刷新失败定位仍需独立当前版本行为验证。

本轮无产品/SDK/Node/UI/API/DB/test执行、费用、密钥、网络、部署；仅自有stdlib解析/hash/字节diff。T38固定F6十九绿不授F9。完整Backend受理/并发、native宿主持久性/跨窗口、媒体/ASR/权利来源/三OS与R1独验后连续R2未缩。

工具记录：首6ada45实际exit0，但误探F9Interfaces.md不存在产生非终止只读错误；真实Handoff明确的是F9InterfaceConsumption.md，6aba7e已全文读核，原误探保且不当产品红。f4fc53自有artifact分析自然0，26pins及保护区完整保存；大diff显示截断不影响固定完整diff，相关调用链另588f7a正文已完整读。全部源读者已结束，无live handle；正式终态交接记录最后真实metadata工具完成。
