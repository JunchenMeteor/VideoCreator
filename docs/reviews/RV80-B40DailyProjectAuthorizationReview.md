# RV80 — B40 有界日常项目创建与授权源码评审

结论：SOURCE_STATIC / CHANGES_REQUIRED。两项 P2 恢复接缝保持 OPEN：已知 Goal pending 在原 execution 到期后不能完成自动拒绝；派生作品失效后缺少可接到真实新政策的有限 reauthorize 路径。其余已读链具有同连接提交、有限精确派生和明确来源的源码支持。本轮不执行产品、DB、Owner、native、API、MCP、Worker、媒体、模型、测试；费用、钥、安装、网络均 0。不是完整运行验收。

## 固定输入与实际范围

唯一源根为 `G:/开发测试/Codex/VideoCreatorImplementation/Backend/DailyProjectAndNativeConsumer-B40/DailyProject/StaticFinal/SourceCopies`。依据最终 B40SourceIndex/StaticFinal Snapshot；早期 Native71 和当前 B41 不冒作本批身份。74 份普通源 SHA/大小匹配，65 Python 仅 AST 解析；9 份正式/支持件及 5 份治理件，共 88 个不同路径独立固定。前后字节结果见自身 RV80Snapshot.json/RV80InputsAfter.json，源漂移不以当前生产文件替代核对。

关键正式 SHA：

| 文件 | SHA-256 |
|---|---|
| B40Handoff.md | 0b14d68aabe631cceca75522457c4d4d4d8bc9b0f93afb93dacf56c20c1e2c0c |
| Interfaces.md | 3d6a3b1d16e132d895b52b43aa623e2ffecf067498b573f4a0cc9e85f2d0fca1 |
| B40SourceIndex.json | 3ee491074e59319a59ae1caf4e14aa589107a2a4705766c639914529637d0743 |
| StaticFinal/SourceSnapshot.json | ef2f0ce9043af8371ec62f19d2888a98c2e8aabf98a4007a3eb79f35cb4b9d1d |
| StaticFinal/StaticReceipt.json | 031671f252deed2ee66dbb4fd9ddfe682af41cc8243a4d3597c2019fb7b465ce |
| StaticFinal/AcceptedSourceChanges.diff | 6f7bc6a7706c69da1c7fadeb8b8ba703d327b8e327afb3ef6944bf474e0a9248 |
| ADR0037 | 48431e2e77ef1fb4841668e25acefe7158a9b0f6abec1607400a117401818d9c |

读取相干正文而非仅信摘要：完整 DailyProjectService、完整新域模型、OwnerServices、数据库/0009；issuer request/binding/current/rights/document/finalize、原 Store current/recovery/writer guard；API/MCP/CLI 有关入口；Bundle 0.1/0.2 解析、portable/current/history 校验；原生观察器及其 retained one-shot/真实 peer/full map/not_ready 接缝。未声称 74 份所有方法均逐字人工审核，未扫描运行时或全部环境。完整来源 pins 在 RV80Snapshot.json。

## RV80-P01：过期 execution 抢先拒绝已知 pending Goal 的无副作用收口

P2 / OPEN / SOURCE_STATIC；Backend 归属，恢复权限范围需要 Architecture 明确。最小条件：完整真实 accepted intent 与受保护副本已保存，floor reserve 已发生，Goal 接受事务未 commit；原 execution 在 reserve→writer 检查窗口或重启前到期，父有效期可以恰等于原 execution 有效期。

[daily_projects.py:811](G:/开发测试/Codex/VideoCreatorImplementation/Backend/DailyProjectAndNativeConsumer-B40/DailyProject/StaticFinal/SourceCopies/services/engine/src/video_creator/application/daily_projects.py:811) reserve 后 :816 调 issuer._guard；[execution_registration.py:599](G:/开发测试/Codex/VideoCreatorImplementation/Backend/DailyProjectAndNativeConsumer-B40/DailyProject/StaticFinal/SourceCopies/services/engine/src/video_creator/application/execution_registration.py:599)–605 在原登记到期时抛 execution_registration_changed/409，事务回滚但 reservation 保留。重启 current :488 已读 Goal proof，却 :507 _active 先抛 execution_registration_inactive/403。原在内存对象的 current_guard 也先经过 [production_admissions.py:211](G:/开发测试/Codex/VideoCreatorImplementation/Backend/DailyProjectAndNativeConsumer-B40/DailyProject/StaticFinal/SourceCopies/services/engine/src/video_creator/application/production_admissions.py:211)→_identity:173–176 的 execution expiry 403；Goal 私有 guard :560 还在 yield proof 前要求 active。

明确 denied classifier 位于 daily:768–782，只捕获内部 Goal scope/quota/normalization 的 403，前置错误不在其范围；_deny_intent:790/:797 本身仍依赖活跃 issuer guard。普通 Store.current_guard:573–574→ProductionControl.assert_revision:217–220 拒任意 pending floor。此已知 expiry 不能靠现有自动拒绝路径 complete，也不能改绑原 parent 精确 role refs。

ADR0037 §5 要求已知真实 intent 在父权限失效时只写原 denied/cancelled，以同预留 revision complete；不创建子 scope、不收费、不长期阻无关健康 Run。当前实现保持 fail-closed，但这段恢复闭环没有接通。未证实际停摆、并发或所有撤销窗口。

整改应把真实性恢复证明和可执行 current 分开：仅在完整原 protected intent、原 Owner/DB/floor/action 仍可核且无未知损坏时，可信服务允许仅提交原 intent 的无副作用拒绝，并保持原 ID/hash/revision/计数/预算/unknown；成功执行仍须当前完整 guard。不能授权过期 execution、接受客户端恢复票据、降 floor 或洗未知损坏。独立测试至少覆盖 reserve 后到期、重启及原在内存对象两入口、精确旧回执、healthy sibling 和无新增副作用。

固定源码 SHA：daily=250a24770e76edace6d375793deb35e462ab0604cf0ab5d7065055fb44cede4e；Store=97358f57ff5b029a9518dd915d79f4cddbc7a0e309efddab81e352bf7c587549；issuer=cd944dd801f92572bf79814cf02975d7f26cdcf627206c3103fea80d17b98d5d。早正式 finding SHA f46da2f51246b7d13b9a2f3db0d65e97430fabe943c45251150d2a84305caf34 保留。

## RV80-P02：原子作品无法按现有可信 reauthorize 进入真实新政策

P2 / OPEN / SOURCE_STATIC；Backend 归属，有限子项目管理权限交 Architecture 决定。实际派生子项目原 unattended Run 因原父到期/替换/撤销而待恢复时，旧 ManagementPrincipal 仍保持旧有限项目列表。原 reauthorize:139–141→ProductionAuthorizationService._principal:37–41→ManagementRegistry.assert_current:78–88 对新子项目明确 403；这是安全拒绝，不能改旧 tuple 取得权限。

真实取得新管理 capability 的现有路径存在：实际 Owner initialize/renew→OwnerBootstrap.change:227–235 接受新的精确项目列表，生成新的 binding/generation/action；它不是有限子项目恢复端口，会变更完整 Owner 来源。DailyProjectService._current:264–270 要求原父的旧 generation/action/authentication binding，因此这个真实换代也不会自动接通旧作品。不得把缺少有限端口写成永远不能获得实际 Owner 授权。

即使实际 Owner 已合法得到含该子项目的新 capability，[production_reauthorization.py:160](G:/开发测试/Codex/VideoCreatorImplementation/Backend/DailyProjectAndNativeConsumer-B40/DailyProject/StaticFinal/SourceCopies/services/engine/src/video_creator/application/production_reauthorization.py:160)–168 仍先 issuer._request:291–294→daily.derived_record:447–456，原失效 parent current 检查发生在验证新 policy_ref 之前。原父仍活跃时，issuer._record:301–307 也总先选择该项目原 derived policy；新 policy_ref 与原 child policy 不同仍 production_policy_scope_denied/403，无法进入真实独立新 policy 分支。

ADR0037 §4 的失效阻止副作用、保持历史/资产/unknown 有源码支持；“需要恢复走原可信 reauthorize”的实际派生作品新授权接线缺失。父/子的 get/revoke 不能替代该功能，历史来源可读不代表当前许可。

最小整改需真正 Owner 确认、有限该真实 child/project/production/run/request/hash 的新管理动作和真实 receipt/current source，历史 creation provenance 保留；request/current binding 应识别新的真实来源，不无条件先要求旧 parent 当前或始终选旧 child policy。不能扩旧 finite scope、绕 current、伪人审、清 unknown/预算/Operations、换请求或造替身 Run。权限范围未批准不得由 Review/Test 自动扩大；实际授权与恢复验证留独立 Test。

固定 SHA：reauthorize=9e8b48decec2bc506e7018c06b66b7aa5a7ffa3c7da45aefcb1337add6960a4f；management=f7ed157cbbe78e2055a25d6b40c83c520cfe20526feec08e8195788d338e372f；OwnerBootstrap=d53044244c7206420e7961f97dd09a75d9bd3d8a4fcf452ad7e2ceea3797dec7；daily/issuer 同 P01。早正式 finding SHA 2e6311a5e797208c44f1301ca3ff150753dfee46c901eeece65e50e264dcfbb8 保留。

## 其余有限源码支持

- Daily.accept 保存原 canonical Goal/Owner/ref/key/entry/计划实际 ID/request SHA 和受保护 intent，已 committed 返回原 immutable acceptance；异正文冲突。_commit_intent:800–883 与 Engine._accept_production_connection:358–432 同原连接写实际 Project/child/receipt/Production/Run/journal/count，私有 context 为同 service/thread 原对象并在 finally 释放；没有 public nested transaction。
- 父模板完整保 routes/源版本/语言画幅/时长/素材 SHA/交付/rights assertion/质量/修订/预算；child 实际唯一 project_id；同原预算组和 Operation 路径，没有新组/清 unknown/重置计数。lifetime quota 原记录 carry，active quota 查实际 Production 终态；新 B 创建增加高水位，Store/issuer 使用下限，scope 不含 usage counter，没有直接重写 A 的旧 Owner/role/ref/lease/asset/费用字节。真实 A/B 并发和中断仍未运行。
- API:218–226 与 MCP:46/:98–99 经同 Bundle:1479–1486→Engine:78–81→Daily.accept；入口授权使用实际 actor/同实例/原 Owner，locator/body/token 不安装委托。旧 draft create_project 和 production 接收入口保留。
- CurrentAdmission/rights 明确 delegated_project；v0.2 complete parent+child+trusted derivation 与真实 creation action 分离，不伪造人工 Approval。Bundle 0.1/0.2 按版本解析，portable 只来源审计，历史从原本机 admission/Goal/原 parent/plan/ready row 核；current 另核原 guard/lease/fence/parent/child。导入为 origin，不安装本机执行资格。Media/Integration/SDK/UI 后继消费不得把新枚举的 else 当真人审核，现运行未证。
- 0009 新父/子记录及唯一 project/production/run 外键、current/revoked 字段；Database 支持 7/8 backup→9，同 writer 应用迁移并拒 >9，保 WAL backup/file/unknown/cost 说明。迁移/恢复/回滚相容实际未运行。
- 原生安装观察器 one-shot，实际原 held build/receipt、OS peer、完整 map/epoch 对象成员，原 local writer hook 不哈希/RPC；严格仅接受 qualification=not_ready，保 contacted-but-unconfirmed close 和未知原句柄。仅编写/阅读此适配器不证明安装 qualified、Win32 故障安全或 Python/native 正常实跑。

## 原结果、展示限制和终态

B40 CommandReceipt 记录 final e3c438/0、wrapper PID25016/natural return0/communicate EOF/streams closed/source_drift[]，physical child/Job 未证明，scope 仅 AST/copies/diff/Ruff；本评审不继承为运行 PASS。原 bf88e4/d0fe27/0e3497、原13 Ruff及 C408保留；未重跑或回填旧失败。本批读自身方法索引及并行 source 输出曾展示截断，已只补遗漏 domain 116–235、issuer 605–717、portable 1–95；索引定位不是产品失败，不把截断显示当全文读。

未覆盖：真实 Owner/Vault/安装授权、完整 setup 空实例、两 Goal 并发及所有 floor 窗口、API/MCP/Worker 完整作品、同项目修订/再授权实际行为、Bundle/RAG/媒体/ASR/精度/权利、17 fault 全目录、App UI/发行/三 OS、R1 验收或 R2。完整 R1 独验后连续 R2 的目标不缩。

输入均普通固定副本，未读 B41 热 source、T55 运行证据或其它 WIP。读工具全部自然终态；readers 已释放，无产品进程或异步 reader。末核结果与报告/Handoff 实际哈希见自身交接，本轮正式 SOURCE_REVIEW_FINAL 后释放角色。
