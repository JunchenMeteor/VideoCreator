# F11 恢复拒绝窄修独立源码复审

**F11-P01：CLOSED_SOURCE_STATIC_ONLY。** 原错误链在固定增量中得到源码修复；没有运行React/UI/API/native/Test，不能据此称实际回放、安装或R1通过。F11-I04与原生lost-prepare关联保持OPEN。Backend阶段的DG-P01不由本结论关闭。

## 固定版本与范围

唯一新源根 `G:/开发测试/Codex/VideoCreatorImplementation/Frontend/NativeGoalWorkbench-F11/RecoveryRejectionFixStage/SourceCopies/`，14完整普通源码逐路径/大小/SHA核对，13份与原CurrentGoalSourceStage相同。8份SDK只读固定SdkEarlyOrdinary/Generated副本，未读当前SDK；编译器/依赖/环境不扫描或执行。

Handoff MD `fcf284a70ac8832a7eadac0437bebf0d8e4e7ac214a01ae3a8527c26fd9a3058`；JSON `8bd5ff8e30db5f90175b81573e5872bc1a1c7178c62d6edca47b0326cc077cd6`；SourceSnapshot `3d848b29a55230b57033f549061e8d2ed54547db8521ed521535324cb4b9029e`。原Finding `291ed71763f0a25045d1c09c4fb3f87385856efa38133b1970709b86d449bf97` 不改。

唯一NativeSetupView.tsx原SHA `53b72b66a01a3e3a59fc2de212387214846003f52f51de92d9344c91e7daa20a`→新SHA `a3cfb57656df6454b2fa3a2338753cf85d848ff14814aab33dbefe35d2db198c`。独立重构完整diff只有catch的!recover和两行解释。原14全文上下文的独立报告保留，本轮核13同字节，再完整读修改组件/存储/native上下文和相干旧错误/恢复路径，不重复宽审。

## 原错误链与源修复

NativeSetupView:71–74的submit(true)只读取原pending API intent；sendApi:55–63仍核原context/bodyHash，POST唯一project-goals并使用原完整body和Idempotency-Key。goalIntents:31–44保原slot/完整body/key/context，pending不同key不能覆盖。

旧catch把后续401/403/not_sent也用于原未知请求rejected；新:98明确仅!recover进入这条写分支。恢复的此类失败只显示本次错误，不改原pending、body/key/context/attempt/receipt，:76仍挡新key创建，:115按钮也仍禁新Goal。本次拒绝没有被解释为首次未受理。实际原匹配回执仍由sendApi:60–62保存accepted；首次fresh明确拒绝在!recover为真时仍保旧语义，allowlist、SDK、body/selector无变化。

因此仅原F11-P01源码逻辑闭合，没有将Test未运行变成runtime关闭。最小独立Test仍需accepted+lostACK→401/403/not_sent恢复→重连保原body/key/身份与pending、无第二Goal→同key原回执；首次fresh明确拒绝可显式新动作；坏回执、storage失败、实例/principal切换仍不改绑。

## 原生等价路径与仍缺部分

未改nativeSetup.ts。:53状态读取异常只failed；:75/95 prepare/present/abort异常置uncertain、保original，不重发prepare/newkey；:72异attempt/generation不接受。NativeSetupView:40–46仅同原attempt的实际completed typed receipt或实际aborted状态结算；异常/当前拒绝不是aborted。此处是原固定source协议消费，未签原生确认或授权。

普通新OwnerSetupPort SHA `df713a887e9da3388a886d2264be9e9cec1466d5e6aa36c05371d83ff4231d28`增加request_identity/current_document声明，固定接口说明须对比原完整Goal/key才关联lost prepare。但nativeSetup/组件没有消费这两个新增字段；仍不能自动关联丢失的prepare ACK。缺件诚实保留，不猜attempt/重prepare。真实configureNativeSetup、同已安装Bundle私有ready instance/principal descriptor、Backend真实qualified producer与原Daily路径也不由catch修复证明。

F11-I04/P3仍OPEN：Workbench:370称浏览器仅存偏好与定位编号，但goalIntents:35/40保存完整Goal/body/source_text。只需准确披露本地缓存，不清未知意图、不推中心上传。

owner报唯一 changed-source TS工具1d7666/0，两个固定raw均0B；本轮没有重跑TS或核完整编译器闭包，也不以作者typecheck替代UI/API验证。五步、权限/预算/发布和多模态交付原范围不变。

## 读取错误、证据等级与交接

1f26b8遍历snapshot.fixed_interface_and_finding_inputs时误读其中production `G:/开发测试/Projects/VideoCreator/apps/desktop/OwnerSetupPort.ts`，实际SHA与该批普通port同df713…，属于Review可避免的范围读取错误；已立即报告统筹、停止，**不作为closure证据且未再次after读取**。没有产品执行或秘密读取。报告不声称只读ordinary；有效结论来自固定普通port/14源/8ordinarySDK。合并输出只截NativeSetupView头段，bbba2e定向补完，原输出保留。

本Frontend有限37个有效输入after无变化，误读生产path另列excluded_after；Backend原任务卡变更只作为独立治理历史，不回填原107。过程 `G:/开发测试/Codex/VideoCreatorImplementation/Review/GoalSourceFixIndependentRecheck/` 保存FrontendIndependentDiff、FrontendSourceFacts、FrontendInputAfter及原误读记录。固定源读者已释放，费用/秘密0。无RuntimeBinding/Owner/OS/安装/Gate/R1签字，完整独立R1后连续R2保持。
