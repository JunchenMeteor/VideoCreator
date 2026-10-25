# RV1 修复与接缝独立复审（已分派）

task_id RV1；Gate0；永久评审角色integration_review。实现、测试、规格只读，只写docs/reviews及Review过程材料，不代修、不修改标准、不代验收。完整范围Gate0→R1独立验收→连续R2。

输入RV0原问题/撤回记录、A1Handoff与0002/0003/0004 ADR、F1Handoff及8源hash/截图、T2原红、W3/B3/I3稳定源与T3独立回归。只对已交且实际可读证据作结论；未到交接标未测，不据owner自查宣布通过。

1. 复核T2原四失败是否在新稳定源和原期望下解决，合法数据控制标签与真实混合协议保护同时保持；委派completed须绑定实际模型成功产物，不能只靠执行前计数、非空hash或模拟成功。Crew原三轮委派0和LG交互成功/无人模式失败均保留，免费具体修复不能重置盲试。
2. B3唯一公开ErrorEnvelope→OpenAPI→集成SDK→前端消费的源/hash与失败状态一致，顶层入口/迁移资源进入完整checkpoint；契约方向批准不等于运行已证实。
3. staging201与真实Asset分开。CLI validator必须实解码，不以扩展名/假metadata或客户端Blob回退绕过；坏媒体、越权和工具失败保持失败语义。F1真实文字资产、项目/冲突/queued/SSE自查仅作局部证据，音视频与审核待实测。
4. I3已验证媒体工具hash/许可、真实引擎包/IPC生命周期。MSVC1602原因与旧工具下载失败保留；Windows候选不能外推DMG/Linux/签名公证。
5. 官方Provider准入必须证明产品内部正式厂商接口、商业权限、费用/额度、异步任务与结果回存、临时数据TTL/删除；Kimi网页会员内部插件不得作为商业后台已接通。BYOK免注册与账号失效不锁本地仍保持。

保存source/test/evidence hash、实际命令与发现归属角色/严重度、未测条件、复审结论。公开材料优先ReviewHandoff，权限不足报具体路径，不改ACL、不读.ssh或运行收费。交RV1Handoff给统筹和独立AV0；标准新版本按独立评审流程，不倒填历史或消除失败。评审不签Gate0/R1/R2独立验收。
