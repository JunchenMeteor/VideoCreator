# ADR 0010：unknown原本地Operation的受控核实阶段

2026-10-08；批准最小接口方向，B7/W7及独立新源验证待交。永久架构只读设计，不实施/测试/产品进程/key/收费，不改生产冻结源或旧标准。补充0009，现有workflow与schema3优先保持，不扩成通用供应商/调度框架。

依据：RV11正式报告SHA `377e022be960e61ba4c963e3a6e758737a1a7c170d1082505690f6e926a13ba5`；B6 worker SHA `7c53bfd06bd4cf1a388a958783acda911b943e4fe9a2782012860bafaf7ace9f`、engine SHA `b7177032a8429b90dac457dc8b8adf465134d2e4deeeb34c8af4d4fdbcb6d233`、W6 Flow SHA `173c9a474821e87cb1ac19d8717b48a9b71a0417e3fa1e24983b37940be25581`实读匹配。恢复把submitting置unknown/Run置needs_reconciliation正确，但当前Worker仅领queued；正常bind/begin/prepare/finish_output也不能在核实状态执行。W6已有核实分支不等入口可达。

统筹交T13真实kill反例终态1/1failed：原完整ready文件保留，真实墙钟越过租约，新nononce Worker自然0后原Operation仍unknown/unsettled、Run仍needs_reconciliation，未重写或重render。这是独立测试向统筹交接的事实，本架构未代跑/读取其原始私有Cases；T13原三批夹具/观察红、后独立观察补绿均保留，不混为产品全通过。

## 限权模型与领取

后端在唯一内部domain/worker.py定义候选 `ReconciliationInvocation`（reconciliation_version=`gate0-local-reconciliation-v1`）及只读原目标视图；独立于正常WorkerInvocation，既有ExecutionBinding/workflow_version不改，避免改变Flow身份。视图固定当前核实lease/fence、原run/production/request/binding、operation_id/step/input/dedupe/route/既有external_id与精确allocation/output_key集合；绝对文件句柄仅可信进程内，不进公开API/导出。

B7为同一可信固定CLI Worker增加核实领取/分派，不靠外部任意模块或用户授权字符串。可复用acquire_run(reconciliation=True)，但私有guard须限原needs_reconciliation及本workflow既存binding、当前presence/资源hash、原本人Run、credential-free owned_local固定render路线/0成本/原政策；不能新建binding/route/预算或将waiting_provider任意当本地文件任务。每次领取仍增加fence/attempt，保持单槽/心跳与有界窗口。内部阶段类型由固定调度器构造，不是HTTP/model能自行获得的权限。

**不放宽正常_lease/bind/begin_step/prepare/claim/allocate/commit/创意或审核写权限。** 仅新私有核实guard可用现allow_cancel=True并加上述精确范围；核实阶段不kickoff正常Flow、不render、不分配新文件、不提交新Step/Asset、不接受人造成功/免费清unknown。

## 最小端口与B7/W7分工

1. B7：领取核实、读取既存binding/request/原Operation/精确allocations及必要已持久计划/Step事实、原文件受控句柄、核实心跳、观察原Operation、结束核实并释放/转换。每次读取/最终事务重核worker/fence/lease与归属，不把新fence写成“新生成”；原allocation_fence/attempt/id保留。绑定缺失、输入/资源/路线不一致403/409，保持待核实，不重新bind。
2. W7：固定 `run_reconciliation(invocation, services)` 只做本地证据核查，按原profile/计划重建纯输出规格，不调用正常Flow或begin/prepare。输出全集由后端原operation与同run/step/input精确allocation确定，按W6固定profile核对应完整集合，不仅成员包含；歧义/缺项不猜。媒体核每份completed字节/size/hash、真实decoder/MIME/流/时长/尺寸及原manifest；禁止目录扫描/任意路径、借Objects越validator范围或将.partial认领成功。
3. B7：接收唯一内部完整文件证据，事务内再次核原operation/输入/route/全集、lease、既有external_id及所有权后更新必要staging证据并观察**原operation_id**。已ready/imported的size/hash不可变；allocated空hash只能在精确归属及实际完整解码证据后首次固定，不虚称已有原hash证明。临时文件/字节校验在短事务外，最终按固定hash重核；文件变化不能提交成功。

观察保持W6既有 `OperationObservation.result_json.generated_files` 形状及稳定顺序、原external_id约束；仅已证本地无凭证0成本路线可记confirmed_no_charge/actual0，不给任何付费Operation推断免费。没有登记Asset就不填result_asset_ids。重复相同证据幂等、不同证据409；旧fence/并发失lease拒绝，Operation既有成功观察不覆盖。取消可核实既已发生的本地事实，但不新执行、不重新queued或生成审核成果。

## 完整、部分与回正常阶段

完整精确全输出有真实证据才可成功settle原Operation；partial、少任一输出、文件缺失/损坏/解码不符、输入资源漂移均保持unknown/needs_reconciliation，不删除文件、释放未知预留或重claim/render。程序异常/失lease不伪观察成功；明确的证据冲突记录固定错误，原事实保留。核实不成功也必须释放自己的执行槽/lease，不阻塞人工或其他任务。

后端最终检查原Run所有unknown、未结清/进行中Operation及cancel/pause，不能因一项成功就提前回正常。每项观察与派生状态须按原核实守卫一致；有剩余未知仍needs_reconciliation。需继续的原Operation全部succeeded+settled且无其他失败/不确定阻断后，通过专用结束端口撤销核实lease/清执行槽，未取消才回queued（保留paused标志）；**正常阶段重新acquire_run得到新fence**，才允许原W6正常Flow继续。已知failed不当恢复完成，取消保留原cancel_requested/cancelled派生状态，不复活失败/取消任务；不得将同一核实grant直接转普通执行权或手改running绕守卫。仅为结束持有而处理已cancelled状态的私有校验，不扩大任何正常_lease权限。

非once Worker按有界轮次处理核实与普通queued任务；本次已尝试但未解决的Run不能每250ms热循环续占槽。至少每Worker进程对相同原证据只核一次，后续显式重启/新证据才重试；其他queued任务仍可执行。不搭通用重试系统。CLI退出0仅自然收尾，不证明目标已恢复，输出须明确仍needs_reconciliation或已转换范围。

**另一个窗口：Operation已succeeded+settled，仅Asset/Step或Flow未提交。** 仍走正常queued恢复，复用原manifest/字节；新正常lease仅更新Step执行fence，原Operation不再提交、不重render，Asset+Step沿原原子守卫，之后补Flow checkpoint。这与unknown核实分开，不能把二者样本互相当通过，也不直接新增Production/Bundle succeeded。

## 冻结、兼容与独立验证

B7只后端domain/application/cli及必要内部端口；W7只workflows/media。优先使用schema3原runs/operations/bindings/allocations/staging，不新增公开HTTP模型、正常审核状态或数据库列；如确需迁移/公开shape改变先提交精确理由，依原架构/SDK/备份规则。旧binding/Flow UUID保持，原源与红、hash留存，不覆盖T13。

T13相关源已交释放事实，但I13当前完整入口另有读取依赖；**B7/W7只读准备，待统筹明确全部相关批解除冻结再实施**。新固定源→测试真实kill：完整单/多输出、部分/缺失/篡改、原成功但Step/Flow未存、旧fence/取消/重复核实/并发、新Worker与normal新fence；记录原operation数、render调用及文件hash、实decode、墙钟到期和实际进程终态。不得弱化旧断言、以直接接口模拟替所有OS窗口。RV独立关闭P01，完整Gate/R1/R2及商用产品内API/MCP能力另交；费用key0、ADR0003限制不变。架构正式交接即FINAL，不等待新测试。
