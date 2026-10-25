# RV53：F6 未知受理意图修正独立源码评审

结论：RV52-P01、RV52-P02 均可在 **CLOSED_SOURCE_STATIC** 范围关闭。关闭的是固定 F6 中的原两条不安全分支；不是完整制作恢复、行为实测、安装或 R1/R2 验收。本轮未发现新的阻断源码问题。单窗口、同 origin 的本机记录语义是本次判断边界；跨窗口原子协调、真实浏览器/host 持久化与后端对账事实仍待验证。

## 输入身份

F6 正式 MD SHA 1d8fb8a12f50e4cf0aa7d383845cd39c5add94f9f3640e03ed2f641dda85548d；JSON a9217c047221b4e891d9268fce364e10b69a9ea14e7742f4c1da9355adfdeb73。
F6SourceSnapshot SHA 854d92ef672a68ffedf6b8c63c31b19d57158a9f51a7df31e4e7174df2b3964a；F6SourceDelta 51de37843b2b5548d9b53a1696bacf8741c7face51ac45fb8b3f255a06eee465。

实际核对十一份 F6 普通源、十份 F5 原普通源、I33 固定 client/routes/schema/OpenAPI 四份普通源及必要正式件，共35固定输入无 mismatch。实际 Delta 为3修改、1新增、7不变，逐字差异已保存到过程目录；没有读或回填当前生产源。39路由字面量、37唯一键仍属于生成43键，没有新增非契约 route。没有执行 SDK 或任何 route。

| 本轮改动源 | 固定 SHA |
| --- | --- |
| engine.ts | 50f682ef00c8ce258029206b1818d6879225eb45446641a3286c49d7e9d7dbfd |
| Workbench.tsx | af1f408ffd050f4c669fae93e38985e90e1afc6506669fc6fa94fbddd00fb61f |
| BundleImportView.tsx | b9bb81333746d3b34c1f5a7d582931d77b312fcdf3ed1ca8d23dfd1c96a0023a |
| submissionIntents.ts | 2c8edd2f805cdcc041e19ee79168f7365bf4926d1651c8b0cfab7bc4f3dc1953 |

原 RV52 报告 ccc679fb83c57b0f927f11b3ed0a1dab22c1156c0e88375e4acb4f7a657d6373 与交接82fdaa3c5800e67402bde8c3cf8922f7e76ae52170a0f93f630df3fdf8468c79 保持；原编译红/绿、旧测试不改，不借它们证明 F6。全部精确输入路径/SHA 与结束核对见 RV53Snapshot.json、RV53SourceAfter.json。

## RV52-P01：有限源码关闭

[engine.ts](G:/开发测试/Codex/VideoCreatorImplementation/Frontend/WorkbenchIntentRecovery-F6/OrdinarySources/engine.ts:30)，30–49、69–84行：默认 submissionDisposition=unknown，不改原 retryability。not_sent 只在 configuredClient 尚不存在、调用 client 前产生。rejected 同时要求完整 ErrorEnvelope、never、明确 code/status 配对，不能由所有4xx或“undefined retryability”推导。409、408、5xx、safe/reconcile、未知 code、非 Envelope 都留 unknown；原生错误原样传出，不完整 data 默认 unknown。

[Workbench.tsx](G:/开发测试/Codex/VideoCreatorImplementation/Frontend/WorkbenchIntentRecovery-F6/OrdinarySources/Workbench.tsx:129)，97–104、129–184行：
- 每次新提交及重新打开都先读原意图，未解决或本机记录不可读时不发新制作 POST。
- 同组件提交 ref 先锁住；原生成 body 克隆并固定 hash/key，成功存储后才到159行POST。实例变化、保存失败、已有未知身份均停止。
- ACK 检查实例、发起项目、production/run/request_revision 编号、支持的 schema/status 与非空定位路径。将有效 production_id 保存到原意图后，submitted 才变 false。
- 非标准502/503、原生网络错、不完整 ACK 进入 unknown 并保留原记录，修正了 RV52 的错误类型漏锁。后续列表刷新失败不会把已保存的有效 ACK 当成未知或丢掉。
- 仅 first-submit 的可信未发送/明确拒绝可清原键，清除失败继续停提交。没有实现未知制作重放，所以不存在用“第二次拒绝”洗掉原未知的制作恢复分支。

这一关闭依赖可信实例/SDK的既有错误及回执契约；代码并没有凭 HTTP状态造一个上游未受理证明。实际传输、错误分类和存储时序仍需 Test 验证。

## RV52-P02：有限源码关闭

[submissionIntents.ts](G:/开发测试/Codex/VideoCreatorImplementation/Frontend/WorkbenchIntentRecovery-F6/OrdinarySources/submissionIntents.ts:20)，20–71行：本实例分键；读取检查基本形状、实例、项目、固定键格式和回执定位；保存拒绝覆盖另一未知键并回读检查。仅生成JSON输入/非秘密定位进入记录，无ZIP、File、媒体字节或连接/模型凭证。JSON克隆隔离后续编辑；重放前检查当前实例及完整 body 的 hash/key。记录丢失、损坏或不可读时停提交，不被解释成已拒绝。

[BundleImportView.tsx](G:/开发测试/Codex/VideoCreatorImplementation/Frontend/WorkbenchIntentRecovery-F6/OrdinarySources/BundleImportView.tsx:74)，36–55、74–128、132–137行：
- 卸载前记录存入 localStorage，重开按实例恢复；导航本身可以继续，但原未知意图不再仅放在已卸载组件 ref 中。
- 新导入保存 staging_id、archive_sha256、原项目、完整 origin/body/key 后才POST。暂存阶段或 makeIntent 等待中卸载会停止后续新导入POST；实例变化同样拒发。
- wasUnknown=true 的恢复只验证并重发原 body/key，不再暂存ZIP，不按当前项目改写。未知状态下按钮和事件处理都拒绝重新选择。
- 若首次明确未受理，可清除；若原来已 unknown，即使重放收到 not_sent/rejected，也不清第一次未知。这是122–124行的真实分支，不只是提示词。
- 只有当前POST的完整匹配ACK（本地实例、原项目、import_id、ready、全部 origin 字段、定位和index_state）保存定位后才解除。手动读取相似导入记录不清原意图。

原“导航卸载/网络失败重选会丢完整 body”的条件在本候选源码已修正。原预报告撤回的“普通项目切换保留旧 ref”不重新作为缺陷。原 F5 导入键算法不被冒称 F6 的兼容恢复：旧版并未保存该本地记录，本轮也没有迁移原未知请求的实施证据。

## 未完成条件与独立后继

1. **制作完整恢复尚未完成。** F6 只持久保锁，没有精确重放/查询操作。固定 I33 的创建POST声明 Idempotency-Key 和 ProductionAccepted/202，但未表达未知时同键同body的完整副作用/原回执保证，也没有按键查询 route。Backend/架构应冻结该语义，Frontend再接恢复；不能用任务列表相似目标解锁。未读 B28活源码，不认为未来实现已存在。
2. Test 应真实触达 F6 调用链：not_sent；明确 never/code/status；409/408/5xx/safe/reconcile/未知Envelope与非Envelope；原生错误、不完整/错实例/错项目ACK；ACK后刷新失败；保存失败/损坏/hash-key不符；unknown 导航卸载、重开、重选；旧未知重放再拒绝；同body实际回执；暂存阶段卸载与实例变化。合成故障只能证明机制；真实HTTP/UI、Backend账本与产物需另验。
3. localStorage不是OS权限或跨窗口原子锁。没有 storage事件/原子互斥的资格证据，不将单窗口 ref/check/set 说成多窗口协调；跨origin或真实安装宿主也未测。不同实例分键仍保留旧实例未解决意图，不能据新实例页面状态说旧实例已对账。
4. F6新类型/build/UI/API均未跑。原F4 noEmit0、F5 build0、T37旧版本的计划/执行以及mock数量都不验证本批；没有读取 T37 活输出。真实Owner/native/host流式保存、策略与资格注册、素材绑定、八件作品、实际ASR与三OS继续未完成，不借本关闭完成R1。

未发现需要另开阻断 source Finding；这些后继限制是原已确认未完成范围。完整R1独立验收后连续R2保留。评审不代Frontend修复、不改测试/标准、不授RuntimeBinding/生产收费/发布。费用、密钥读取、网络、产品/SDK/测试执行均0。

过程只使用 stdlib 对已保存artifact作字节、JSON和差异解析，053e64自然exit0；本轮分析器无失败，不虚构一次红→绿。7e6444和08eec8的长显示局部截断由固定JSON完整解析与具体变更diff正文补足。原RV52路径/审批/自有解析错误证据仍在旧过程目录，未改写或称产品红。
