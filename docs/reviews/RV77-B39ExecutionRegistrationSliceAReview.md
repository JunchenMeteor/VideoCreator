# RV77 — B39 Slice A 持久执行登记独立源码评审

结论：**LIMITED_SOURCE_STATIC_SUPPORTED**。在已实现的私有模型、schema8候选、Store读取/current/强对象guard范围内，未发现新的生产P1/P2。此结论不批准 RuntimeBinding、Owner动作、数据库迁移或正常启动通过；完整 B39 仍未实现，R1三OS真实作品/多模态独立验收后连续R2目标保持。

## 固定身份与定位修正

过程：`G:/开发测试/Codex/VideoCreatorImplementation/Review/ExecutionRegistrationPersistence-RV77`。实际最终索引是 `G:/开发测试/Codex/VideoCreatorImplementation/Backend/ExecutionRegistrationPersistence-B39/SliceA/StaticRevision/SourceSnapshot.json`，SHA **34506cbd465678a72555faeb8bf2ab492bc145132ac97a459ef248970c361ae3**。其67普通源码逐文件字节数/SHA匹配；59 Python文件仅作标准库AST解析，无产品import。88条有限输入的完整路径及SHA见 RV77Snapshot.json，前后检查见 RV77InputAfter.json；不读Backend热application、后继SliceB或当前运行环境。

原卡把该最终SHA写在首层SourceSnapshot路径旁，存在定位歧义。实际首层 `SliceA/SourceSnapshot.json` SHA **ddf487b802842b04819abbcd0d0d8372f686a51953267d24dccda211b082680c** 属首批，application为fba9bc7f…21826B；正式Handoff明确指向StaticRevision，application为103c7fb4…21810B。统筹消息确认此定位，本轮没有改卡或覆盖原批。前者、原lint红和错误工具记录均保留；这不是产品源码漂移或运行缺陷。

| 最终生产路径（均在上述StaticRevision/SourceCopies） | SHA-256 |
| --- | --- |
| services/engine/src/video_creator/domain/native_execution_registration.py | 6983fa964d4fcbc0ff3f30d30f4b5c5bb9e943177caa35c3d60e033d1be0ccca |
| services/engine/src/video_creator/application/execution_registration.py | 103c7fb412076db2fdf029cc87646a87f2b0ccd067da63bbe81181f4df0b6123 |
| services/engine/migrations/0008_installed_execution_registrations.sql | 4872324c662fadced1376c9ad7abd26ba18620cac99dc2c64a0d3b5b601ad0b6 |
| services/engine/src/video_creator/infrastructure/database.py | 6285de3a81581c2c71046744a16006a41631ec4b470e81cb12b1c937ee3be7c0 |

接口 Interfaces.md SHA **2b171c35637853fb783cda6264e13c4c7b06f7e59aac9e636fece8d2b077d489**；ADR0036正式原件/普通副本 SHA **fd69319e24390a16463654792133ebc04ae388cb406112adb512ea30084c5a03**。Handoff/原新收据与原源也已pin；没有拿未来实现修正本次固定身份。

## 实际源码支持

- **私有记录和canonical闭合**：model21–24采用UTF8、sorted keys、compact JSON及完整SHA；Contract原extra=forbid/frozen，模型未接公开API/MCP/SDK。NativeBuildReceipt53–73要求独立四类实际来源ref与不同(kind,id)，仅描述构建；NativeInstallationInputs76–124核host大小/SHA、payload/registration/resource/runtime、外部receipt完整canonicalSHA、完整图/排序/分区。原HeldFileFact与NativeLaunchContext验证整数/路径/唯一成员及16KiB framing margin；路径文本约束不是实际打开、物理身份或资格证明。InstalledBody、ExecutionBody、独立ActionReceipt分别139–213，不造PolicyRef或携带ticket；执行主体限定真实domain Owner，有限项目/namespace、角色及有效期。安装提案/receipt类型不等于已执行Owner安装或合法许可。
- **原body/action/command关联**：Store76–168要求原canonical有限TEXT；原JSON边界严格解析，不接受BLOB/非canonical/坏模型。逐installed/execution body和ref/fullSHA、row中的实例/Owner/role/安装ref与original action匹配。_action95–110要求同原commands(owner,scope,key)的request_sha256和result_json，scope为owner.execution.<action>；不是凭三个SHA挑授权。read代码不写当前记录、不初始化floor、不改预算或Operation。
- **当前主体/范围与carrier**：_active170–185核installed和registration的current/revoked、当前Owner及登记有效期、generation/action/authentication binding、真实OS目录身份、administrator/source、项目范围和实际项目所有权。_startup188–198核原NativeLaunchContext的实例/角色/三个SHA/完整map/engine分区，以及独立host绝对路径/SHA；没有将载体当安装事实来源。这仍不执行host/payload打开或资源观察。
- **原锁/floor**：current212–240为Store RLock→bootstrap.current的原OwnerControl→同authorization.control的ProductionControl→DB read。bootstrap.current实际定义在本固定owner_bootstrap118–128；ProductionControl实际定义在production_management106–221，pending或DB低于外部floor继续拒503。get200–210经原管理_principal/action_guard再ProductionControl并重核目标项目，不将历史读取激活为执行授权。
- **强对象/短writer**：CurrentExecutionRegistration和Guard38–55为eq=False原对象，包含原Store backreference；_currents/_guards持有原对象。current_guard247–265保Owner/Production锁与Owner canonical正文；assert_writer_current267–293限定原Store/thread/未release current，逐原Owner metadata、installed/registration整行、current/revoked/到期、DB revision、项目及原commands原文检查。其实际调用链只有DB读取、原_revision/_project_scope、clock和对象/线程比较；没有资源hash、OS身份检查、RPC或网络。资源epoch/实际observer/current authority必须由后继在writer外完成，不能用这里的原对象替代资源资格。original_projection295–303只是未来同issuer投影原八字段，单独字典不是身份票据；尚未绑定issuer。

## schema8与静态检查边界

0008增加installed_native_records和execution_registrations两表、immutable body/action/ref字段、FK及有限current/revoked检查；execution的唯一current为(instance,Owner,role)，安装current为(instance,Owner,composition_root)。没有插入Owner/floor/current默认记录。database34–55把7纳入升级前备份、逐迁移在原单writer中递增至8、拒>8；snapshot_backup保原SQLite/文件/未知成本知识与外部Control依赖，禁止原地降版。静态上不重置spent/reserved/unknown或原floor。**实际7→8迁移、备份/恢复兼容和真实损坏/并发仍NOT_RUN**。

原ee9082退出1是I001/SIM117。已保存的首批fba9bc7f源与最终103c7fb4全文差异仅import分组和get()组合with，资源进入/退出顺序保持；原差异存 NarrowLintCorrection.diff。修订278f41/原Ruff收据实际0、communicate EOF/streams_closed、无sticky/exception/drift；它们仅支持源/AST/Ruff。收据明确physical_child_pid_or_job_proven=false，不能升级为真实Job、Windows原生资源或产品入口证据。Review未运行Ruff、模型构造、SQL或Store方法。

## 下游与未达范围

本片没有新增生产整改finding。Backend继续原真实Owner install/replace/select/revoke/get及幂等/crash恢复、原reserve→DB原子提交→complete、mutators/current lookup正常记录入口；Integration实现真实安装观察/双retained guard；随后Backend接同Engine/Bundle/原issuer强对象绑定与writer外资源current。这些是明确未实现的后继范围，不能由私有协议类型、read代码或静态67/59宣为通过，也不能在最终产品留下所有合法记录永久503。

仍须独立实际验证合法Owner写入→重启→正常current/ready，以及坏body/action/map/command、pending/restore、revoke/expiry/generation、前后并发撤销、跨Store/issuer旧强对象、外部host/实际全图/许可/资格及资源变动。真实Owner/Native认证、安装、Windows危险故障、媒体/ASR精度、三OS和完整R1/R2均未授资格。

Review工具范围只读固定源码/资料和标准库有限解析，费用/真实key/产品/Test/DB/native/模型运行0。初次大索引输出截断已用有限源码补读；fef643中PowerShell数组拼接错误、ccdcd1的猜Control文件名rg1均是Review工具错误，原结果保留，之后按正式JSON/import定位补读，不冒称生产红。末次输入前后核验与实际工具终态记录在自有Handoff/FinalizerTerminal；所有固定源reader释放后交FINAL。
