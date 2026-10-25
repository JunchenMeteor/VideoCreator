# ADR0050 — 真实制作阻塞日志与有限同 Run 恢复

状态：APPROVED_DESIGN_ONLY；2026-10-10。仅补 ADR0049 的 blocker/resume/denied 生命周期，不修改 ADR0049 或原标准。完整 R1 独立验收后连续 R2；一次真实预授权自动制作、本地免产品注册/BYOK、五步 UI、安装实例持有数据和三 OS 保持。本决策不证明实现、运行、资源资格或作品质量通过。

## 固定来源与结论

任务 SHA `6d3989c559b63b90c90c0f08257eb31f7c0c88869810f32426cfa61df7d1a1f6`；ADR0049 `59743e9ae79c6998c1540b3fdb4e5cb68788926e95720a2da28cd1ab3ca27e68` 保持。Backend/CurrentProductionImplementation 的 Gap.md `22fc9f148e6f53cd166f5158ae6951a5a3fc586cdea25abe98a098efe86622e2`、Gap.json `c11d1a52d974b60b5532fa34e661d498a4c6c078ae461e1f075789e951313c08`、EarlyInterfaces `2c0bde98989a7aa4bbc74d80cfb4676d5c12bcd56395e882320bbe3ca59e72ea`、EarlyTypedSourceIndex `2def6fdfad1326bd63053ba0d7214562485181ffe406dc2f93cd75d4e3f92b76` 已全文核实。原119 InputSnapshot `e11d4c9dfe1a7a2abf52e14a15f0766a48573d722d43761053088fdae2cac8c3`、停写 SourceStageOne/SourceIndex `bf9e8e89ab32ae16b3edcfbaf584d7cd95377adce788fa00d7f0e3bf427ed37e` 仅精选普通副本消费，不读热源。

现 park 伪造 quality（原 media_registration:201–211；新停写副本:364–374）。AuthorizationWait 是显式 Owner 重授权日志，不能拿来记录资源可用性。原 metadata 表已存在，无需新表/迁移。

关键实证：early production_admissions:205–286 的 current_guard(registered)/_guard 不需要 ordinary lease；它们实际检查同 issuer identity、原 native store/current、qualification/session、control floor。:332–399、545–602 的 _request/_bound/current binding/record 检查真实请求、原 immutable bind_request 或真正 Owner 重授权来源、当前/derived policy 范围。这可作为有限排队资格来源，不能用旧 lease、序列化哈希或 True callback 替代。ordinary _lease（原 engine:184–194）确实拒绝等待后/过期租约。

## 1. 唯一日志 grammar 与 producer

Backend 唯一维护私有 `CurrentProductionBlockerJournal`，strict/frozen/extra-forbid；沿原 canonical JSON，metadata key 精确为 `current_production_blocker:<实际 run_id>`，且仅四个 required 字段：

| 字段 | 准确合同 |
| --- | --- |
| format | literal current-production-blocker-v1 |
| binding | 原完整 ProductionBinding；instance/Production/Run/request revision+SHA/registration/input assets 全量保留，来自真实 execution_binding |
| result | 原唯一 CurrentProductionUpstreamResult；只允许 waiting_authorization 或 resource_not_ready；media_roles 为空、实际非空 blocker_code；同 Run/原 lease fencing_token |
| blocked_at_us | engine.clock() 的 strict 正整数；拒 bool/浮点/不合原服务时序 |

此日志是实际进度记录，不是 policy、授权票或法律证明。不能接受模型/HTTP/native JSON 直接写入。唯一 producer 为实际 v2 RegisteredMediaRuntime 的已受信工厂结果处理；Backend 私有入口精确：

`park_current_upstream(ordinary_lease, result:CurrentProductionUpstreamResult) -> None`。

在同一短 writer 中核当前真实 _lease/fence/cancel、原 Production/request canonical 字节+SHA、同一完整 execution_binding/registration、该 Run 为当前 Production 的实际最新 Run。仅接受原 running/waiting_provider 活租约状态；已过期 lease 不得用于写日志。此为停止/挂起事务：即使执行政策已失效，也可凭真实当前租约和不可变原请求/binding停下；不调用会要求重新获得执行许可的 normal _evidence_execution_guard 来“批准”阻塞，也不放宽那个正常执行 guard。这里不创建 admission、ReviewDecision、Owner action、quality、Asset 或权限。

若有实际 unsettled Operation（settled=0）或 submitting/pending/unknown，拒绝普通等待/终态路径，沿既有实际 reconciliation 处理；保原 Operation/费用/allocations。prepared 等未结算状态不能被改名为 unknown，也不能强行当零费用清空；若需原 Operation 完结，交原账本恢复，不在此合同造结果。

正常挂起原子写日志、同 Run waiting_user/waiting_revision_id=NULL、worker_id=NULL/lease_until_us=0；Production 仅在仍为其最新 Run 时同步 waiting_user。fence/attempt/counters/budget/floor/request/assets 不变。事件 `production.capability_blocked`，沿原 _event 第四参数记录该 canonical 日志 SHA，非伪 revision。事务失败全部回滚；既有同 key 非相同记录是 409，不覆盖。重复已经成功释放的结果只能观察完整原记录/同状态，无第二写入/事件，不以旧 lease 再 park。原人工待审已有实际 waiting_revision_id/释放 lease，仍由 ADR0049 的纯观察路径处理，不转此日志。

## 2. 明确可用的恢复入口与可信排队来源

唯一入口为 Backend 固定 `RegisteredMediaRuntime.resume_current_blocker(run_id)`，内部返回 `(state, reason_code)`；state 仅 queued/still_blocked/not_blocked/needs_reconciliation，reason_code 为原安全 Identifier 或 None。它不是许可 bool、公有路由或 Owner 管理接口。唯一生产调用方为原 `run_registered_worker` 的正常 v2 循环：在原队列 acquire 之前，有限检查本 Runtime 注册下的日志候选；有显式 run_id 时只检查该 Run，无参数时每个 poll 最多一个候选，采用内部有限退避（同 Run 不快于 5 秒），不做全局 startup/history 恢复。停止/control 已到时不再探测；once 模式至多一次正常探测/处理，不假装长期守护完成。资源后来真实可用时，原非 once worker 自动排回同 Run，无新 Owner 确认或逐项目 CLI。未启 worker 时，仍通过原可信安装 worker 启动入口接续，不增加绕审批后台 hook。

具体来源沿新停写 Runtime:234–242 的实际 `engine._authorization_identity(真实 Production owner)` 获取原服务持有的身份，而非调用方填 owner/principal。policy 分支沿原精确 PolicyExecutionPorts.issuer/registered（early:853–871）；进入实际 issuer.current_guard(registered)，整个短 writer 保留原 object/thread-scoped _AdmissionGuard、native/qualification 保护作用域。不能调用依赖 lease 的 _current_services/get_request(lease) 来获得恢复服务。

Backend 在原 ProductionAdmissions 增有限私有检查：

`assert_blocker_resume_current(connection, guard, *, run_id, binding:ProductionBinding, blocker_sha256:c.Sha256) -> None`。

该方法必须识别原 issuer._guards 中同线程活 guard，并调用原 _guard；不发新 guard、身份、admission 或 Owner action。SHA 只作日志 compare-and-swap 身份，不作授权源。

- unattended：用原 _request/_bound(action=begin_execution)/当前或真实 derived record 证明原 request、原真实 policy_ref/Owner action/声明 SHA、注册三 SHA、当前范围及有效期。存在真实重授权指针时沿原 current binding 的完整 command/receipt 校验；不猜来源、不选新默认 policy。已有 plan/quality 时按实际下一阶段读其真实字节/rights 与原 current policy 的 action 范围。历史 bind_request/旧 fence facts 只用于原来源关联，不能当当前执行许可；此处不要求已释放的旧 begin_execution/plan fact 仍是当前许可。
- interactive 的 resource_not_ready：原 _guard/_request 和可信当前配置的原 Owner 有限声明/真实 request scope 校验；不需要也不造 unattended policy。已真实提交的审批按原 immutable decision/hash/target 只读核关联，不发人审 fact；新 lease 后仍按原 _admit/current human checks 执行。interactive waiting_authorization 不可借此替代真人审核。带真实 waiting_revision_id 的人审等待从来不自动恢复。
- 显式 AuthorizationWait 日志存在、源政策已撤销/替换/过期、原权限需真正重授权时，保留等待并交原 Owner 路径；不借资源探测清掉旧授权日志、造 derived 项目成员或自动 Owner receipt。

安装/resource/config/source 检查、实际原安装资格/原 source current、固定 route/driver/许可与本地 credential-handle 可用性预检都在 SQL writer 外，沿原受信 Runtime/真实安装 authority；保持完整 v2 闭包，不能以 ASR-only、config SHA 或客户端路径冒资格。此预检不运行 provider/network/model/ASR/FFmpeg、不下载/收费、不输出或复制凭证；不注入任意可调用 validator。凭证可用性不是许可，缺许可不能 queue。真实 held/current observation 与同 scope 的 original native/qualification session 在 writer 中由 _guard 原机制作本地重核，无 RPC/hash/file I/O。资源变化后新执行仍要重新检查；缺真实 authority/dependency 保具体 still_blocked，不将空/True guard 算通过。

## 3. writer 原子恢复与权限边界

outside-writer 读候选 raw journal、完整 binding/request/config 注册，完成上述资源预检与真实 current_guard。打开原短 writer 后重新读并严格验证：

- 完整原 journal canonical 字节/SHA 未变，format/绑定/结果时序正确；实际 instance/Production/Run/request/body/registration/input assets 与原 execution_binding 一致。run.fencing_token 仍是日志旧 fence。当前 Runtime 注册与日志相同；v1 immutable binding 不能清记录后被升级。
- 最新同 Run 仍 waiting_user、waiting_revision_id=NULL、worker_id=NULL、lease_until_us=0、无 pause/cancellation/terminal；不是其他 run/人审等待，也无 unsettled/unknown Operation。原 source/current guard/控制 floor/Owner真实政策/资格和 scope 经上节 helper 当前再核。
- 日志缺失且原状态正常：not_blocked，无写入。竞争期间已 queue/owned/终态、journal改变：409，不抢 lease或覆盖新状态。损坏 grammar/binding/hash：422；不当成“无日志”。外部源或实际资格拒绝：保 journal/等待并给具体 403/503 reason；不是数据损坏。
- 实际未结算/unknown：仅沿现有真实 reconciliation 转入/保 needs_reconciliation，保日志与原费用/Operation；不删除日志，不提交新生成。没有实际 Operation 证据不能靠 result 标签宣 reconciliation。

全部检查通过才删除精确 key+原 value 的日志、原 Run/仍最新 Production 改 queued、waiting_revision_id 保 NULL，发 `production.capability_resumed`（实体关联旧日志 SHA）。同一事务只排队，无 Operation/provider/admission/费用/预算/Owner写入；旧 fence/attempt 暂时不改。原 scheduler acquire 正常增加 fence/attempt 后，必须重新 begin_execution、真实 plan/quality facts/current-operation guard。queued 不是执行许可，不能复用日志或旧事实绕 guard。

若 writer 竞争或撤销，事务不得部分清日志/排队。事务成功后进程崩溃：同一 Run 已 queued 且日志不存在，原队列可正常接续；不重写预算/再发 resume 事件。若尚缺真正 installer 原 identity/current/完整许可或可用资源，Backend/Integration 补原 assembly/producer 后才能恢复；接口设计本身不准资格，也不把永久等待算完整产品。

## 4. denied 的当前同 Run 终态

Backend 固定私有 `finish_current_upstream_denied(ordinary_lease, result:CurrentProductionUpstreamResult) -> None`，只接受受信原 factory 的 denied、empty media_roles、真实 blocker_code、同 Run/fence。短 writer 对实际活 _lease、完整原 request/binding/registration、最新 Run、cancel/状态竞争作与挂起同样的检查；这是 denial-only 停止，不要求给过期/已拒政策补执行许可。不能拿模型/provider JSON、过期 lease、无关 Run、或“拒绝”字符串自行终结。

仍有 unsettled/unknown 时不标完成/failed，不清费用/输出；走原 reconciliation，终态以后由原结算恢复核实。无悬而未决副作用时，仅同 Run 和仍最新 Production→failed，worker/lease/waiting_revision 释放，原预算/计数/Operation/Asset/binding/floor不变，事件 `production.capability_denied` 关联安全真实 blocker_code；不创建 quality/review/Owner action。cancel 优先按原取消/核实路径；其他已终态不可复活或覆盖。重复真实终态只观察，无新事件/生成。

## Inspector、责任与有限验证

保持原公开状态枚举，不新 public state model/route。资源/授权日志等待是 waiting_user 且 NULL waiting_revision；人工待审有真实 revision，UI 不把前者呈现成必须“审批质量”。原有经认证 inspector 在原同 Owner/项目读权限下可解析上述私有日志/事件、安全 reason；读取不授 resume 权限。若现 inspector 尚无该具体只读接线，Backend 在原接口固定增量、由原唯一 Schema/SDK生成流程交接，不能借默认本机授权或 renderer hash 添加宽读取权。

Backend 实施唯一定义/日志 writer/resumer/denied/helper/原 worker-loop接线；Media 只返回原 typed result，不写 metadata/SQL/权限/新 result schema；Integration 补完整实际资格/source/resource/原 installer身份，不能假 authorizer；Test 独立制定并实际验证，Review/Acceptance独立。必测：一次 park 无 fake quality/人审；released/stale fence 拒二次写；资源后来可用同 Run queue→新 fence→新 begin/plan；原3真实权限来源；不存在/损坏/foreign/cancel/pause/真实审核/active owner/old v1 拒或区分；policy撤销/过期、资格/文件在两阶段改变、writer CAS竞态、SQL回滚与 queue 后 kill 恢复；真实 unknown/unsettled 不重交不清账；denied活租约准确终态与 cancel/unknown优先；counter/budget/旧资产不重置。既有质量/200ms/MM/许可/三 OS 阈值不动，设计/模拟不冒真实成功。

本轮只读上述固定普通源，未执行产品/SQL/Owner/native/网络/模型/收费/ASR/安装/部署；不重试被拒 supervisor/global-startup hook。先以本固定 ADR 交后端实施，详细 InputPins/SourceAfter/Handoff随后仅架构自身目录冻结。ADR0049停写原字节保留。
