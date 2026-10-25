# I61 后继 — 生产依赖真实产物闭包

状态：ACTIVE。Acceptance genuine FINAL 后已恢复原 Integration，执行本卡有限准备。完整 R1、随后的完整 R2 保持。

固定输入：Integration/KimiOfflineWheelsAndGraph-I61/ProductionGraphRevisionExecutionHandoff.md SHA 9f0017ede4544baaceabd817f164532d217677e6878159451511c11d6170fc3d；JSON 1a5533887577b383cc1023eb01518fad95c0faa453a1d0fde4d69369f2ca32c4；NextProductionArtifactClosurePlan.md 4e343ec1f658603323b2293f08583b595e829e37475f90a9633508c98576541b；JSON f38bf355017505eabc780d1470949fd63ac8d5260550001998b50ee7a89226e6。Root 已读正式交接，40df49再次完整读后继MD。八投影只是候选，299唯一artifact尚未获取，不算锁定安装依赖。

责任与白名单：原集成角色，只写仓库既定 Integration 白名单及自身 Codex/VideoCreatorImplementation/Integration 过程目录。不能写 Backend、Media、Test、Review、Acceptance 源或借其私有运行环境；不接触.ssh、密钥、Owner、模型、付费、产品启动、线上发布。

先完成可执行的有限准备：

1. 根据实际四个自建 wheel Requires-Dist 与目标 marker/extras，明确生产目标选择，保留 Windows、Linux、macOS 两架构四目标；两个参考锁有冲突/歧义必须报告，不能用当前宿主默认条件或删除依赖来通过。
2. 将确实需要的官方 artifacts 精确 URL/size/SHA、允许的重定向源、下载超时/最大字节、独占新输出、完整输入索引及原句柄终态机制写成有限获取计划。禁止在线resolver、安装、vendor import或SDK执行。无认证/消费的官方公开包读取可作为后继计划范围，不假定此卡已准入整个未知命令。
3. 检查计划必须读取实际完整 wheel ZIP/CRC/RECORD、METADATA/Requires-Python/Requires-Dist、资源与完整 LICENSE/NOTICE，与图中边逐项核对；native wheel ABI/平台最低版本仍分开记录，不能靠文件名证明OS运行。四自建wheel零内嵌license的源许可与A32修改告知附件继续保留。
4. ripgrepy2.2.0 没有目标wheel：独立准备固定31740B/SHA4c43c61384f257660007acd271a5d8e4abe9be0b069c418d091f7299e080ca9d原sdist的数据检查和离线构建工具闭包。不得顺手build/install，不依赖ambient ripgrep或把缺口从图中移除。
5. keyring现存六分发126普通仅可供应独立已准入数据；Scripts/keyring.exe以及Linux SecretStorage/jeepney缺口如实保留。数据闭包不能代目标OS vault、安装、运行资格。

交付：完整停止写入的计划/实现助手/实际输入索引/输出不存在检查/原始metadata准备命令收据/风险与未执行项，供统筹固定一次执行范围。准备后所有工具与读者终态，有限 Handoff/FINAL。不得自称完整安装包、Kimi生图生视频API或商业权利通过。

## 有限公开产物取证准入更新

统筹明确允许原Integration直接取证已固定官方Windows CLI参考134候选+原ripgrepy31740B sdist，总上限57428480B。执行前记录确切选择/原官方URL、size/SHA、允许host/redirect、原runtime/tool/argv/输出独占目录；不超名单、不浮动resolve、不用凭证、不收费。自身既有系统工具或纯stdlib数据工具可以实际下载与只读ZIP/CRC/RECORD/METADATA/完整许可；未知native组件先报告。失败保留原红、不改SHA/检查器、不盲重试。禁止install、vendor/SDK import、sdistbuild、服务/Owner/model调用，其他目标/两锁差异/安装运行缺口保持。有限实际结果或明确失败后FINAL，优先I62独立源码。此限定公开读取不再以全helper/后继299资料准备作为前置。

## 实际首批结果

原29d298/session87392由本人9365c0等待terminal1。Acquisition21296自然0/双EOF，135 HTTP200/一次各项/57428480B原收据身份全一致（Root042ce1/e3e26e核记录，不声称当前文件独立再hash）；Inspection5512自然1/双EOF，5结果后Unsupported WHEEL version/purity grammar。原批永久失败不覆写、不重复GET。限定只读第6包原WHEEL/metadata与规范诊断后正式交接FINAL，优先I62；后续仅已下载bytes的检查修订另新namespace，不改原结果/不降CRC/RECORD规则。
