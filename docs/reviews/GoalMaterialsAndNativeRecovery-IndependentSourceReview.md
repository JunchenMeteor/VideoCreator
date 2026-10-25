# Goal 素材与 native 恢复独立源码评审

结论：**PARTIAL_SOURCE_STATIC，GMNR-P01/P2 OPEN**。当前素材 ID 接入、原 unknown Goal 固定与 native lost-prepare 语义关联有源码支持；素材请求尚未绑定真实连接换代，不能签异实例隔离闭合。没有运行 DOM/API/native/媒体或重跑绿色，亦不授安装、Owner、权限、三 OS、R1/R2 验收。

## 固定输入

唯一实现输入根：`G:/开发测试/Codex/VideoCreatorImplementation/Frontend/GoalMaterialsAndNativeRecovery/`。Handoff MD `e12350165a737263c3f79af001e8bb48b5d0de33afb2461454f26058d16a95c4`；JSON `9ae19c396eb58c942f0ccba55780cf5e2c8bc941a125e694d1607af2433a40bc`；FinalSourceIndex `4c7be51c308571f1a427a864affa5bb6d6b189c8e8abb1edb3a957e74129be00`；完整 diff `7bf1d4b33ec9d91b252c6e30542f135353a8ecd6dd44ca0c4fad4405e27cc75a`；ContractGap `f0ec3212c689f218374c32fcf45bfe1844c8790e75f2b8ae24da52b22eb6d821`。

FinalSourceIndex 列 19 个类型检查输入；本评审依据它映射 `SourceCopies` 的 18 个精确文本副本：14 工作台源、2 SDK、1 desktop port、1 tsconfig，逐 size/SHA 均匹配。第 19 个为 24MB tsc.exe，未随普通源复制，本轮未读热 binary、未重跑编译；它是原声明支持，不是源码丢失或产品失败。首次映射保存的 missing-compiler 项保持在 FixedSourceInputs.json，TextSourceVerification.json 单独澄清，不擦原件。

完整读 Workbench、NativeSetupView、nativeSetup、goalIntents、engine 相干逻辑、CSS 增量与全部六目标 diff；必要旧副本和公开类型核版本。独立 stdlib 在内存解析所有 unified hunks，以固定 Before 重建六份完整 After，与冻结副本逐件相同；这不是 apply，也不是执行测试。末核 41 个有限输入 changes=[]，不读热 A45/Backend/native/其他实现。

## 有源码依据的部分

- Workbench 74–78、316–358、378：从真实 import 回应或 GET/受保护内容校验后的 AssetRecord 维护有限本次素材，显示 source/media_type/size/rights，checkbox 只选择这些实际 asset_id。导入成功回建项目阶段，不把导入片段宣称新成片。没有伪全列表、路径授票或 fabricated Portal source ID。
- NativeSetupView 86–93/goalIntents 50–55：把 `[...assetIds]` 与其他 Goal 一起脱离当前表单复制并 hash/key 固定。recover 80–83 取原 intent，sendApi 64–72 发原 body/key，后续选择变化不会重建原 asset set。原 recovery catch/finally 与 Before **字节相同**，块 SHA `b7322e362a3048806b84ba07e4aad1031264cf109364297a3b240ad5709c8ee6`；107 行仍只允许 fresh 已证拒绝转 rejected，恢复时 401/403/not_sent 不清原 pending。
- Specification09 固定 section2 65 行允许个人材料没有外部 source_bindings，167 行限定受控上传或实际资产 ID。本个人表面保持 source_bindings=[] 与 AssetRecord 中来源/rights，不从文件名或 hash 造文章版本。import/readable 不等于制作许可：Backend 仍需实际范围、rights/许可、有效期、预算及外发核验。用户填写的 rights 字符串不是已验证权利或 authority，本轮没把它升成 Boolean 资格。
- goalIntents 15–23 的递归 JSON 语义比较忽略对象键序、保数组序及值；nativeSetup 53–63 比同原 owner/generation/key/full proposal，失配保 failed/uncertain；没有再 prepare、新 key、猜 attempt 或自动审批。NativeSetupView 40–57 将实际 status attempt 仅关联到持久原 generation/key/full Goal，completed/aborted 的状态也在同原关联内处理。
- NativeSetupView 118–132 仅原 nativeAssociated、review/can_present/current_document 时展示确认；nativeSetup 75–84 在命令执行处再次要求 current_document。已有回执可在导航后显式查看；关联/可读不等于 native 人审或授权。原 port SHA `df713a887e9da3388a886d2264be9e9cec1466d5e6aa36c05371d83ff4231d28` 13–22 明确该含义。真实 status producer/通道/本人确认未在本轮执行。

## GMNR-P01：health 缓存不能绑定实际素材连接

**P2，OPEN_SOURCE_STATIC。归 Frontend；若真实私有 bootstrap 换代合同缺件，交 Integration 提供精确接缝。**

精确固定文件：`SourceCopies/Workbench.tsx` SHA `7097923c6fe16e1834cbbc7623068fd20a0ef4d968c29b0b5a8e118b80a98dfd`；`SourceCopies/engine.ts` SHA `9f33197721062eb529c5a976ab42120fe687c275462d4e993bca598368340c79`。完整 Finding-GMNR-P01.json 保路径/触发/源链和下一 Test 条件。

调用链：Workbench 48–50 的实例来自每 5000ms 刷新的 Query health；88 行 currentInstance 也只是该值。importAsset 344–350 用此缓存判断 connected、捕获 operationInstance，然后 `engineData` 首次 staging；351–356 写 pendingStage、随后 import，再把回应加入 knownAssets 并自动勾选。两个 guard（350/354）都仅比较缓存实例字符串；addKnownAsset 316–318 用闭包的同一实例标记素材。engine 25–28 的 configureEngineConnection 却即时替换 configuredClient/submissionIdentity；49–56 每次请求使用当前 client，不等 health 刷新。

最小静态触发一：同一 Workbench 仍挂载，实际 bootstrap 将 client A 换成 B，health 尚缓存 A；用户在此窗口导入。operationInstance/currentInstance 均为 A，首个 staging POST 实际发 B，后续 guard 没识别实际连接不同。触发二：先对 A staging，换 B 而 health 尚 A，再到达原 A staging 回应；350 行仍放行，下一 import 用 B client，携带 A staging。若 B 回应返回，354 行仍放行，316–318/355–356 可将 B 素材标为 A 并勾选。实际 Backend 是否拒绝/接受及真实 host 是否允许这种窗口未测；本报告不称已泄露或 OS/HTTP 复现。基本 A→B 且 health 已同步的 success guard 有作用，不能将它泛成所有换代安全。

engine 的当前-client查找与 health 缓存为继承行为；新增材料流水线的 health-only guards/自动选择没有弥补该实际连接关联。359 行旧 catch/finally 还会无原连接检查写当前素材 error/busy。不能靠最终丢弃 UI 回包追回已经向不同 client 发出的首个/续步请求。

最小修复条件：捕获实际私有连接 lifetime/identity，首 mutation、每 await 后续请求、成功/error/finally 写入皆核同原 context；A→B→A 不复活旧操作。staging/file/known assets 留在原连接，不能转移或通过新 scope/credential 假授权。health 标识只作展示和一致性检查，不能当该绑定。若缺 epoch/identity，只交真实 bootstrap/Frontend 内部接缝，不发明公开 DTO 或从 ID 推 authority。保持原 unknown Goal body/key/assetset、native full proposal/current_document 及 rights 门。

独立 Test 最小范围：受控实际 client A→B 而真实 Query health 保 A，确保 A 所选 file 不出现 B staging；迟到 A staging 不续发 B import、不挂 foreign material/自动勾选、不写过期 UI；A→B→A/同实例换 principal 也丢过期操作，稳定连接的真实 import/select/Goal IDs 正向保持。这些下一批测试本轮没有运行或代写。

## 类型检查与未测界限

原 8357b3 natural0/noEmit 覆盖其固定 19 输入；CheckAfter differences=[]，没有事前独占读窗证明。之后 Workbench/engine 两处字符串文案变更，FinalSourceIndex 与 CheckInputs 明确两 hash 不同；不把此前 TS0 冒 final-version 类型/DOM 绿。diff --no-index 的六次 exit1 是正常有差异；原定位错误及原历史红保持。自身 c72e89 源展示超额截断，后定向 0fa172 补全其余 diff/6c2da3 完整内存重建；不声称截断 console 全读。

本轮只源级：素材完整实际上传/rights、真实受控 content、unknown 持久恢复、native lost-prepare/window 切换、current_document status 来源、Provider/视频/音频/RAG/时码、安装及三 OS 均待独立实际验证。此前同实例 wrong-Goal 回执关联/唯一 canonical hash 合同仍独立 OPEN；本次 sameGoalProposal 不充当服务端哈希或关闭该问题。没有拒绝更宽权限、伪 approval、模型费、密钥读取、热源或安装；完整 R1 独立验收后连续 R2 不缩。

过程：`G:/开发测试/Codex/VideoCreatorImplementation/Review/GoalMaterialsAndNativeRecovery/`。固定输入读者已释放；实际每个工具终态和末次写工具返回另给，不预填未来 exit。
