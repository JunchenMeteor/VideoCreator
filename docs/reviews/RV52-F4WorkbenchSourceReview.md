# RV52：F4 工作台固定源码独立评审

结论：SOURCE_REVIEW_FINAL。有限源码身份与新 noEmit 证据可支持；两项 Frontend P2 保持 OPEN。本轮没有运行产品、UI、SDK、测试、HTTP 或媒体，不授 RuntimeBinding、完整作品、三 OS、Gate0、R1 或 R2 资格。完整 R1 独立验收后连续 R2 的目标不变。

## 固定身份与实际范围

固定 F5 SourceSnapshot：80d575a39dc9ed0a494446ef8112937cb92a9a21ec151f2bae33d1f4198d6b82。十份 OrdinarySources 的大小、SHA 与 F4 正式 Handoff 和 CandidateThree 十份选定源码元数据一致。I33 OrdinarySourceIndex：4e947aef58f4d1256f2e66764c03b7ca409fff6eae0ad09d806046c95d912184；16 普通副本一致。共 46 个本轮固定输入全部匹配，完整路径与 SHA 见 RV52Snapshot.json；结束核对见 RV52SourceAfter.json。

F4 正式 MD：123a36806ae3d1ad90c64d9f32d0954b5c1945451dc8c4a3ecefccb16163a8e8；JSON：c5b251e777e1bb3b93b92e30c8b457e7c0d922f6f488e8e73ae69b03e6f962c8。十份正文上下文均只读；39 路由字面量含类型声明中的引用，对应 37 个唯一路由，全属于固定生成 SDK 的 43 个 route key。它们不是 39 次真实请求。

CandidateTwo 原 stdout 的 TS2741、native exit 1、原 Workbench e1f47900aec111c9d7a4609b31e4e7064138fde502d5ac7b27d81d9bb72bfc1f 保留。CandidateThree SourceDelta 的两处新增均为 waiting_authorization 状态显示；新 Workbench 1aaa788a151d23f59a868bb8de9013951a254bf5bbd22b2ecd2f793f8938c3b7。新 Started 原 argv 是 --project 加 --noEmit；Terminal ded625aa4eabded48b0028f14e26465f91e566e9540fa98e99b171f09549ce32 记录 PID 46296、同持有进程自然终态、native 0、原 stdout/stderr 空、有限输入无漂移。运行器正文 55–118 行保留两条 BaseStream 消耗、finally 等待、异常记录与退出码；它不是产品启动器或 Job/sandbox 证明。未重新执行编译器，也未复核 1362 项环境；仅解析该清单并对十份批准前端身份作匹配。其它四个修改文件缺本轮批准的旧正文，不虚构逐字前后差异。

## RV52-P01 / P2 / Frontend / OPEN

**提交后的非标准错误被当成可再次创作的失败。**

固定文件：
- [Workbench.tsx](G:/开发测试/Codex/VideoCreatorImplementation/Frontend/WorkbenchBuild-F5/OrdinarySources/Workbench.tsx:135)，SHA 1aaa788a151d23f59a868bb8de9013951a254bf5bbd22b2ecd2f793f8938c3b7，118–146、221、224 行。
- [engine.ts](G:/开发测试/Codex/VideoCreatorImplementation/Frontend/WorkbenchBuild-F5/OrdinarySources/engine.ts:30)，SHA 58f74397446b63c3ec82c9bd949b5f7bf2ce617a55c011131b7ba88efbae8811，30–42、61–75 行。
- [client.ts](G:/开发测试/Codex/VideoCreatorImplementation/Integration/LocalCopyContracts-I33/OrdinarySources/packages/api-client/src/client.ts:158)，SHA 218cd01f6c5aa191d1802e98728ad2ea82b85e3f9c5d9b5c99775841e174f8a4，158–167 行。

最小静态触发：制作 POST 发出后，第一请求已经可能受理，但页面得到非 ErrorEnvelope 的 HTTP 502/503（例如中间层 text/html），或没有 data 的不完整受理响应。SDK 将非 2xx 包成 ApiError；transportFailure 把它包成 retryability=undefined 的 RequestFailure；engineData 的 response_unavailable 也没有 retryability。Workbench submitted=true 的 catch 只对非 RequestFailure 或 reconcile 锁存 creationUncertain，所以该分支不锁存。用户修改目标后，inputHash 与 Idempotency-Key 都变了，原键的幂等不能保护新键。

影响：在未证明原请求未受理时允许新身份继续创作，可能重复模型执行与费用。这里没有实际 HTTP 或费用复现；502/503 也不能反过来证明第一请求已受理。

最小修复条件：按可信的“尚未发送/明确未受理”事实与“可能已经提交、结果不完整”分开分类，不能用 Error 类型或 undefined retryability 判断安全。后者保留原请求身份和输入并走对账；只在明确拒绝或可信未接触证明下释放。不得给未知错误伪造 safe。独立 Test 至少覆盖原生 transport 错误、非 Envelope 502/503、不完整 ACK、真实 reconcile、明确拒绝以及本地连接缺失的区别；改输入前不得发第二制作 POST。

## RV52-P02 / P2 / Frontend / OPEN

**未知导入可丢失原意图，无法继续重试原 body。**

固定 [BundleImportView.tsx](G:/开发测试/Codex/VideoCreatorImplementation/Frontend/WorkbenchBuild-F5/OrdinarySources/BundleImportView.tsx:44)，SHA 5592cb1bb03382a88778ed55ffcc19929a6e0fc4f29dd19bf8f399262048de3f，18–28、44–58、62–67 行；与 Workbench 214、230 行挂载链相连。

最小触发 A：staging 完成、pending 固定到原 project/origin/archive/staging，导入 POST 可能已受理后出现原生网络异常。66 行允许重新选择文件，立即清空 pending/stage，没有明确未受理或对账事实。非 Envelope 的 RequestFailure 也走该分支。
最小触发 B：尚在提交或未知失败时点击其它导航页。Workbench 214 行导航不受导入意图约束；230 行仅在素材页挂载此组件，因此卸载后 useRef 状态丢失。重新打开只有新的暂存路径，没有保存原完整 body 或返回的 import_id。

影响：失去“重试同一导入”的原身份与回执定位；再次导入只能新暂存。该键未包含 staging_id，而请求 body 包含它，因此新暂存下的幂等冲突/重复行为需由 Backend 的真实策略判定，本轮不宣称成功重复导入。正文中的“重试同一导入”不能代替原意图保全。

最小修复条件：在提交前保全并绑定本实例、发起项目、origin、完整 body 与固定幂等键；未知后只对账或重发同一 body。重选、导航卸载与重开页面不得默默丢失未知意图；明确未受理后才可新建身份。只保存非秘密定位与意图，不持久化凭证或媒体内容。Test 应分开覆盖 staging 前失败、POST 后丢响应、重选按钮、导航卸载/重开、原项目绑定和同键同 body。

早期预报告怀疑“普通项目切换保留旧 project_id pending”。完整挂载链表明正常切到项目页会先卸载；本报告不将该未证路径列为另一个缺陷或实际复现。

## 可支持的静态机制与未完成项

- 前台五步和 Agent 产物页已组织；审核绑定真实 revision/run，pause/resume/取消走生成 route，状态来自实例记录。V03 新请求明确 0.3.0-candidate、delivery_requirements=null，由实例解析；等待授权没有被抬成可执行。旧 Bundle 0.2/0.3 descriptor 都可解析。这些是源码机制，不是实际制作或向后兼容实跑。
- Raw Blob 暂存/登记有独立步骤；浏览器 128MiB 预览、64MiB 导出缓存只作当前 UI 内存界限，不是安装实例全产品上限。Delivery/asset 先取 metadata，再核 original body 的状态、完整性、大小、SHA、MIME、locator/version、本实例与权限 TTL；206/304 拒作完整对象。失败、断连、到期会清预览并撤 Object URL；没有把本机路径或引用 JSON 当访问凭证。本轮没有播放或听审。
- 旁白、混音、审核稿、实际转写等角色分开；RevisionView 区分三个 evaluation_scope，null 测量显示未测，没有硬填合格值。产物存在清单不能授 ASR 精度或八件交付资格。
- main 只接受 Integration 注入的可信 origin 常量；engine/SDK 不从 window.location 授信。六项管理操作未调用，未发 InstallationBearer 冒充 Owner，renderer 不接模型密钥。

仍 OPEN：真实 Owner/native 会话与六管理接线、可信 host handshake 的实际启动、策略/资格注册、未知制作的可操作对账恢复、大包 host 流式落盘、素材选择与 inputs.asset_ids/source_bindings 绑定（新任务当前仍为空）、完整八件作品及真实 ASR/三 OS/发布商业链。blocked/未接通标签诚实，但不算实现这些需求。主要归 Frontend 与 Integration；策略/Owner 授权事实归 Backend；真实制作与 ASR 归 Media；独立行为验收归 Test/Acceptance。本评审未替代任何角色。

过程曾发生误猜索引路径、审批超时和应用权限撤销，均未运行产品；自有分析器首轮因 I33 索引字段名误读 KeyError，自然 1，保留原脚本后只修自己解析，7e23ac 自然 0。错误不是产品运行红。固定 Snapshot/FactsCheck/SourceAfter 与 ToolHistory 保留，不修改原 F4 红或编译证据。
