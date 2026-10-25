# F11 当前 Goal 工作台独立源码评审

**SOURCE_STATIC：F11-P01（P2 / Frontend）OPEN。** 新 Goal 恢复分支会将后续核实请求的拒绝误作首次请求未受理。本片没有运行 UI、API、SDK、Test、DB、native、安装、模型或网络，不给运行/Owner/资源资格、Gate0、R1/R2 签字。后继修订另批复审，不能倒填当前版本。

## 固定身份与读取范围

正式根：`G:/开发测试/Codex/VideoCreatorImplementation/Frontend/NativeGoalWorkbench-F11/CurrentGoalSourceStage/`。以正式 JSON documents 的准确名称为准：`CurrentGoalHandoff.md` / `.json`、`CurrentGoalSourceSnapshot.json`、`CurrentGoalSourceDelta.json`、`CurrentGoalAfterCheck.json`。不是旧四文件 early slice。

- Handoff MD：`98ad4cd52b9e37d18bec321a8d3d3c61c97d71e8fd2d20e7eb20f63ce9a68aca`。
- Handoff JSON：`522d0cc4326f00e0d2244a88af03bc54ff7059b933a55a47a0688518709e308f`。
- Snapshot：`66e35d6b36da53a36552fae89a32fd79fe1d5a1c87d2d08964def3a4e40d53b3`。
- Delta：`680a1750465f9d104349bb4572eb312b3d31f3890dacb00505690d8b2d9f53ec`。
- AfterCheck：`3581c637fb0759d817e0a98335216716bfbe32d29fe8ec872a8377ba17ed8de9`。

独立读取十四份完整普通源码字节、八份生成 SDK 普通文件、十一份必要固定 F10 before 源及有限治理/交接/原生 port，合计 46 pins，输入前后无变化。Delta 实际为三新增、四修改、七未变，独立从固定新旧正文生成 patch。当前 TS/TSX 完整行为上下文已读取；CSS 只审新增四行及字节身份，不做布局/浏览器判断。八份 SDK 只读固定 ordinary：验证各自与 Snapshot 声明的 original/copy SHA 相同，不热读当前 original SDK 或 compiler，不声称独立核到活原件或所有传递依赖。

原四命令 port 的补充固定普通路径：`G:/开发测试/Codex/VideoCreatorImplementation/Integration/NativeOwnerSetupCarrier-I62/EarlyUiOrdinary/apps/desktop/OwnerSetupPort.ts`，SHA `8d0752412dfac1312c27361b0f4d382b70675cb8ade6e13e2328109cb912c9b8`。其泛型返回 SetupView，发送 generation/key/Goal 或 generation/attempt；不是 runtime schema validator，且尚无原 key/Goal 到 lost-attempt 的查询关联字段。只用该历史闭集，不读取后继 request_identity 热 ABI。完整身份和来源见本轮 InputSnapshot.json。

原 owner typecheck `e6ad78` noEmit 自然 0、有限 `23b7e2` fourteen/eight/config 后核 0、最终 `56bcce` 释放，均按正式 Handoff/AfterCheck 记录；这不是本轮重跑或 UI/API 通过。首 0e9a2c 缺完整 before pins、后续 bookkeeping/猜路径错误、duplicate target patch 拒绝及旧 early Git 事件照原交接保留，不称产品运行红或全部依赖闭包已合格。此前 T38/T42 等机制证据也不继承为这十四份新源已通过动态回归。

## F11-P01 — 核实请求拒绝不能清掉原首次未知受理

**P2 / Frontend / OPEN / SOURCE_STATIC，未实跑。**

精确普通路径：`G:/开发测试/Codex/VideoCreatorImplementation/Frontend/NativeGoalWorkbench-F11/CurrentGoalSourceStage/SourceCopies/NativeSetupView.tsx:95–99`，SHA `53b72b66a01a3e3a59fc2de212387214846003f52f51de92d9344c91e7daa20a`。

`submit(true):71–74` 从本地取原 pending API Goal，`sendApi:57–59` 核原 context/hash，再用原 body 与 key 核实。共享 catch 却只判断 `submissionDisposition !== unknown`，把这一次恢复中的 rejected/not_sent 保存为原 intent 的 rejected。固定 `engine.ts:41–47` 会将合法 `401 unauthorized / retryability=never` 信封分类 rejected。

最小条件：首次 POST 已受理但 ACK 丢失，记录 pending；之后会话过期，用户核实原任务，鉴权先拒这次回放、尚未读取原幂等回执。当前源码将旧记录改为 rejected，连接恢复后 `submit(false):75–84` 允许用新 key 创建另一 Goal。于是未知但可能已经创建的原任务可被重复。这是源码反例，没有声称实际 HTTP 故障。后续请求的拒绝、未发送或权限错误只能说明本次操作，不能证明第一次没有受理。当前 `Workbench.tsx:252–254` 的历史 production 恢复及 `BundleImportView.tsx:122–124` 已正确保留这个区分。

修复归 Frontend：新提交与恢复失败分开；恢复继续保原 pending/body/key/身份，不用后续 rejected/not_sent 释放它。只有原完整回执或针对原 attempt 的可信未受理证明才能解决旧 unknown。不要改 reject allowlist、换 key、取当前表单重建 body、猜 authorization_ref、重开 native attempt 或清缓存。

后继独立 Test：首次已受理+丢 ACK → 核实时 401/403/not_sent → 重新连接仍保相同 pending/key/body、新 Goal 被阻止 → 原同 key 回放得到原回执；并保留首次 fresh 请求被准确拒绝后可以由独立用户动作发新 key 的阳性。当前原冻结片问题不因作者后继源码/类型成功而关闭。

## 有限源码支持

**新 Goal 一次创建与编辑分离。** `Workbench:51` 明确 `allowLegacyCreate=false`；`useProjectEditor:120–125/:149–154` 禁止新 draft 的旧项目 POST/自动保存；既有项目仍原 PUT/revision 编辑。唯一新 Goal API 调用为 `NativeSetupView:59` 的 `/api/v1/project-goals`；`Workbench:223` 的旧 productions POST 是原历史请求恢复，保旧 body/key，没有替新 Goal 做两段创建。公开固定 SDK 对该接口声明一个实际 Project/child scope/Production/Run 原子受理及同 principal/key/canonical Goal 原回执；本片只核声明与调用，没有核真实事务。

**意图与恢复。** `goalIntents:39–44` 脱离表单保存 exact JSON body、body hash、随机独立 key、context；API slot 包含 instance/principal。发送前保存并回读；pending 拦另一 key。恢复先核相同 context/hash，原 authorization_ref 为 null 时也原样保留，未自动选新 ref。已受理或确切首次拒绝后的另一次明确用户动作可以使用新 key，两个相同 Goal 不因 body 相同而合并。本地损坏/不可持久化会阻发送，不以 storage 异常推原请求没创建。F11-P01 是这一链的具体例外。

**typed 回执与当前状态。** `goalIntents:46–55` 核 format、四 ID 与嵌套 ProductionAccepted ID、derivation/hash 形状；API要求原 instance。`Workbench:195–203` 选择原 project/production，仅目标受理后进方向；实际详情 GET 再比三身份并读取真实最新 Run，旧原回执不是最新执行进度。这里没有声称 shallow shape checker等于完整生成模型 runtime validation、goal_sha256 等于本地 JSON hash，或业务 ID 是权限。完整运行合法性仍靠真实 Backend/客户端与独立 Test。

**导航与异步。** 新 Goal handler的 detached body、锁、captured scope 和 trusted submission identity 限定 callback；Workbench 的 user project/draft/production navigation 递增 selection generation；离开首次创作页会卸载组件，迟到结果仍可保原记录但不改当前选择。已有 Editor 的 context object/generation 检查保护 load/save/flush 的回包和保存中草稿；cancel 仍用原三身份与 context 世代、变更则不提交当前新目标。真实 React/跨窗口/连接重装测试仍待，不以静态 ref 或之前 F10 绿作当前 UI 行为完成。

**五步与权限。** 前台仍建项目→定方向→看方案→制作→成片，最小输入目标/文字资料，不要求人写剧本或分镜。preferences仅进入唯一 CreativeBriefInput 的语言/时长/画幅/guidance；unattended 文本注明已有本机授权范围，未生成发布许可、预算、Owner 或来源凭证。方向/剧本/分镜/质检来自实际 revisions，人审/feedback 绑定原 revision；没有计时器伪造生成。交付页只有真实 BundleRef 才读固定 manifest/独立旁白/混音/批准稿/实际转写/RAG文本及语义时码，export 与 reference 同版本校验、普通 source path 不冒访问权。它们的真实作品与许可链本片未验收。新 Goal 当前 `asset_ids=[]/source_bindings=[]`，只传本页文字资料；素材库导入尚不等于该素材已选入新 Goal。

## 接线与剩余运行边界

- **F11-I01 / OPEN：可信 native bootstrap。** 固定 `main.tsx` 没有实际 `configureNativeSetup(invoke)`；`nativeSetup:15–21` 仅消费可信原 native invoke。完成初次流程后转到后续 API Goal 还依赖正确连接撤销/lifecycle，不能把 native completed 当媒体完成或普通 globals 当来源。真实 Owner 对话框/原 child/Job/双 EOF 未在本片运行。
- **F11-I02 / OPEN：可信 API identity。** `bootstrapManagedWorkbench:32–34` 没有 genuine instance/principal descriptor；Goal 页缺 descriptor 会保持不可提交。`configureEngineConnection` 的冻结 identity 只是 request binding，不是授权票据。原健康成功不能猜 local principal。真实 Desktop/Portal 接线及连接变更/重开待验证。
- **F11-I03 / OPEN：Daily 服务与 lost-native association。** 正式交接声明原 DailyProjectService 装配未接、null ref 对实际当前 Owner 单一 grant 才可能选择；未配置/零或多条/无权限应准确拒绝。不能把 503 视永久产品功能或填假 ref。原 native prepare 回复若丢且 attempt 未保留，固定 port 未给原 key/Goal 关联查询；前端保 pending 并不猜另一个 attempt，这个恢复缺口仍需 Integration 的真实同来源关联及后继独测。本片不读取其热后继 source，也不读取新 Backend 的装配来倒填当前状态。
- **F11-I04 / P3 / Frontend / OPEN：继承缓存文案不准确。** `Workbench:370` 声称浏览器只保偏好/定位编号；`goalIntents:31–41` 实际保存完整 Goal JSON（含 source_text），原 `submissionIntents` 也存生成 input body。这是本地缓存披露不一致，不能据此推中心上传或泄露。应准确说明当前本地 intent/cache，与安装实例的数据分别解释；不得为文案修正清掉未知原请求。

还需真实第一 native Goal、两个后续 Goal、失回执/重开/身份变化/取消/导航、实际系统审核、当前 proposal 与多模态交付。没有 build/browser/Owner/API/native/媒体/安装/三 OS 或商业通过；完整 R1 独验后连续 R2 保持不变。

## 评审过程与交接

过程根 `G:/开发测试/Codex/VideoCreatorImplementation/Review/CurrentGoalSource-F11/`：InputSnapshot、InputAfter、IndependentSourceDiff、SourceScopeFacts、GoalContractExtract、EarlyFinding-F11-P01 保完整有限来源。原简称三路径 ABSENT（ebd6c6）按正式 JSON 更正；c8703c 单行 PowerShell scalar 索引显示 App 首字符，5a64fd raw 已核真实 export；622085 展示超出实际380行的空行只是阅读输出格式，没有改源、没有产品失败或缺失正文。所有原记录保留，不把定位/解析错误洗成产品红。

所有源码/SDK读者已释放、无 live handle；实际最后报告 writer 终态由工具返回后另归档 FinalizerTerminal，再发 Agent FINAL。仅本片 SOURCE_STATIC 结论，不接下一热修或自授运行。
