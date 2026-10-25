# RV41 — T30 两轮原失败与下一验证准入评审

结论：固定历史证据复核完成，T30 两轮保持 **NOTPASS**。首轮实际 trace 支持 Test 夹具重复配置被既有后端守卫拒绝。第二轮实际支持 8 条 ok、1 条无保存 traceback 的 ERROR、最后一组未完成，以及强制结束后实际退出码 1；不支持整套通过、死锁定位或完整历史 Bundle 资格。四项 P2 均归 TestDevelopment，静态候选与原运行事实分列。

## 范围、身份及数量

仅固定 T30 ordinary、两轮原 raw/receipt、固定 Backend 副本和有限消费者。没有读取 B24 当前源或 A26/T31 WIP，没有重跑、延时、产品 import/启动、DB 查询、native/ASR、网络、key 或费用。完整目标仍为 R1 三 OS 独立验收后连续 R2；本报告不授 RuntimeBinding、发布/许可、ASR 精度、完整 Bundle 或 Gate 资格。

唯一普通副本根均为 G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff 下 T30HistoricalCopyAuthorization 与 T30HistoricalCopyAuthorizationRoundOne。主清单 256 条、首轮 107 条、正式入口 7 条去重后，366 独立路径全部匹配，结束复核 0 变化；绝对路径/字节/hash 见本角色 RV41InputPins.json。

每批保存的记录 1290 个、记录路径 3579 个；实际 before/after 地图首轮分别 3590/3590、第二轮 3598/3598，地图相同且包含全部记录路径。该结论不是重新哈希当前整个运行环境。原 10 case 方法体 AST 一致不等于运行通过。

| 正式输入 | SHA-256 |
|---|---|
| T30Handoff.md | ded76cc0a5a0bf7903b4843898ed571bcd96aa6339062a8aeb15ba56f298e42b |
| T30Handoff.json | f57c485c5f4f50e2fc10e8bf8bc38a1de814aaef31549947db39150ed3e9dab7 |
| T30HandoffSnapshot.json | 0dce131dac7f654b432e4b10142e1d2eb0908976a0b5f6c652e63af332615618 |
| T30OrdinaryManifest.json | 27b04fb9dd30b10eed752949f946f50ce50050b54972bf3196e5b4ad40aa7e59 |
| T30RoundOneOrdinaryManifest.json | a9dbb6257c55959655efe8241e84164bb296c6c70ff22e38f01236461c917ed0 |
| T30TerminalReceipt.json | e473fa60c3d8721f554b2596be446d510c327561da3b0a79d2096449dfd441c2 |
| T30RoundTwoFailureAnalysis.json | 36717d8d5e4e4b0701cac79c12532b3b529a78ffd56b73612743eecf0fddd76c |

任务卡 SHA b4c288b712f1b657b2e01dc0db1da3e07b40c284881e521a74293329a526f546；仓库 AGENTS SHA 6de878f514b02788f8af5ba512f71c56bb053f6800d76cf19f3cdd955b7f6a0d。

## 首轮实际失败

原工具 0fd494 / session35336 → 2efb27 实际退出 1；JUnit 为 10 tests / 10 errors / 0 failures / 0 skip。十条真实 trace 同为 ProbeT30.py:34 第二次 configure → 固定 engine.py:89 → production_authorization_configuration_conflict。child44636 / creation134359811869367378 / actual exit1 / forced false；wrapper39968 / creation134359811855560203 / exit1，lifecycle_errors 空。

ProbeT30.py:26–34 先 super.setUp；MechanismBaseT30.py:128–132 已 register/configure。夹具随后 unregister/register 新 namespace，再 configure。固定 engine.py:86–89 允许精确同绑定重复配置，拒绝 live issuer/registration 被静默替换。实际 MethodCounts register20 / configure20 / unregister10 相符；没有十个 case body/tearDown snapshot。这是 Test setup 失败，不是十个产品缺陷。

修订二基类首次 register 就带 portal-test / owned-test，Probe 修订二 setUp:26–30 去掉重复配置；原十方法体/断言保留。第二轮观察到的 case 进展支持该 setup 问题在观察范围修正，不使原首轮或整套变绿。

原 JUnit SHA e1c92085a0dedfe66f316d2f3a0485287244dadcf8da655991257860ec8270c7；stderr22c3f262036ce498585ac06c315a2342d45f67a32b704ceab1dda63738f716fa；CommandReceipt e9d89e78475a64e33b34df4d41b8d1583deaf76bcb2b56f393f5f6892b7355ee；MethodCounts886c3fa9514b8212e8845014003dc355ab59e7ec87c40a5d449c5e4da9767145；原 before/after 各 a53e27973f6d93889f24d148785928e77b3b877bfc9a3e3ef11b811bb2b2a1a5。

## 第二轮实际终态与缺口

原工具 af906f / session94063 → f8aa38 实际退出1。child48080 / creation134359818057492894 / actual exit1 / forced true；wrapper51908 / creation134359818043634752 / exit1、EOF，保存的 lifecycle_errors 空。launch 到 CommandReceipt ended 为 **90.7019917 秒**，不是自然完成耗时。

1647 字节原 stderr 只有 8 条 ok、human ERROR、末尾 source-revoked case 的未完成省略号；没有该 ERROR traceback、整套 JUnit、Events、ActualMethodCounts 或 case Receipt，summary null。原 10/0/0/0 标准未满足。实际 argv 是固定便携 Python3.13.16，以 -I -S -B -X utf8 启动 ProbeT30RevisionTwo.py，输出到原 MethodRoundTwo/Cases；本轮未运行此命令。

17 份已保存即时 snapshot 的 hash、字节、JSON 行值及相对 launch 的时钟均核。第一 source-ready10.8203057s，current-ready16.0321119s；后续 expired/replaced 双实例准备持续到约84s。末组 source-ready 为 **87.5052656s**，当时 run running / fence1 / Operation0 / spent0 / reserved0。这些证明进展和最后保存状态，不定位下一方法的阻塞或死锁。

事后 ProductionAuthorizationControl.json 的 minimum_revision7 / pending_request_sha256 null 不是即时 SQLite 或真实方法 trace；不能证明已完整撤销或归因死锁。execution policy replace/revoke 与法律素材权利撤回分别处理。

原 stderr SHA a241d9c49f24c76146ea07a5f42b88f0e9ad2e626189a7217571ebc661547b68；CommandReceipt7e8e41a66ab3ae2fe36e0737ca625aa8d518f672ad99752645061458c771aee6；RetainedChildWaitReceipt3d281cba72d4a2e5f51ffcbae9ef6eadcf7dd872ff157c359b1c6ec28c793d7b；LaunchReceipt66f363a308b3ff73a6d163dc0c06d62c0c7d3768ee791028bd9f4f841ba507c7；ActualCommand beda27d5220b2a17ef1da52a8d94a9b5e083ea15e05f7c5632bbae798b955319；原 before/after 各 b255ba0c71554ce7fffd2dfd6ce8795324ec7f8c1d85e47a40996a080d8982b1。
末即时 snapshot9950fa0c92e8ac8be94b2f60b950b8ff84395bc0372b016af2f487166b9b3258；事后控制4f3b08dbb020c463be4471001b032d3442757f2c960c77c0be5551abb1ebc624。

## Findings：四项均归原 Test owner

### RV41-P01 / P2 / OPEN：整套返回才保存真实错误栈和进展

固定 [ProbeT30RevisionTwo.py](G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T30HistoricalCopyAuthorization/PreparationRevisionTwo/SourceBodies/ProbeT30RevisionTwo.py:273)，SHA8a118d60b62fde030c203488f209f1ab703d80ebc40481461adf53d9cd5fe9ff。273–276 的 Recorded 仅 startTest；290 等整套 TextTestRunner.run 返回，292–310 才写 trace/events/counts/JUnit/summary。human ERROR 后继续未完成末组再 forced，实际原输出未到最终 printErrors/落盘。真实缺栈与静态迟写链互证，但不推测缺失的原栈。

修复条件：在实际 addError/addFailure/stopTest 等时点持久保存有界 case/phase/真实栈、clock、PID/source；逐方法计数/关键进展在下一可能阻塞前保存。partial 明确为 partial，不合成整套通过。若需运行中只读捕获阻塞栈，先固定方法、权限和新计划；不能源码回填旧缺栈。

### RV41-P02 / P2 / OPEN：finally 覆盖终止尝试收据

固定 [RunT30RevisionTwo.py](G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T30HistoricalCopyAuthorization/PreparationRevisionTwo/SourceBodies/RunT30RevisionTwo.py:104)，SHAd13682f845dbd9193c3312b5d03be061b889b788e0ce6873ff1f4bf35af596a8。54–55 write_bytes 覆盖，89–91 retain_wait_receipt 写同一文件；104–119 timeout 分支 110–111 查 creation、113 记 attempt、114 调 terminate、119 写收据；128–136 finally 又写 wait/terminal，未携带 attempts/creation_matches_before_terminate。实际最终 RetainedChildWaitReceipt 仅 retained handle/terminal/actual exit1/forced/空 lifecycle_errors，没有真实 pre-terminate 比对或 attempt/result。

修复条件：不可覆盖地保存每次实际身份检查、termination 请求与结果/异常，同一 retained handle 的 wait/EOF/actual exit。forced 永久 red，未知保持未知。源码有 terminate 不证明实际调用成功；当前也没有杀错进程或 Job 资格证据。不得盲重跑、以 PID 消失洗未知或改绿原 forced 结果。

### RV41-P03 / P2 / OPEN_STATIC：human 夹具缺必填 method_ref

固定 [ProbeT30RevisionTwo.py](G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T30HistoricalCopyAuthorization/PreparationRevisionTwo/SourceBodies/ProbeT30RevisionTwo.py:209) 的 human190–226 链，209–211 BundleArtifact 构造缺 method_ref；固定 [contracts.py](G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T30HistoricalCopyAuthorization/FixedInputs/Backend/services/engine/src/video_creator/domain/contracts.py:740)，SHA175d105c6c80415b14d0f4a5b69f841548b7fbc968d3058f55d13e1cba5284ec，730–742 中 method_ref:Identifier 无默认。到该构造时现契约无法满足。

原 stderr 只证 human ERROR，缺 stack，故这不是已复现的实际根因。Test 应按有限方法身份显式填 method_ref，并保存下一实际前后 trace；不把 Backend 字段改可选、伪造 staging/发布资产或 precision。原 canonical-only human 夹具不是完整已发布历史阳性。

### RV41-P04 / P2 / OPEN_STATIC_DEFERRED：H01 bytes → str/dict parser 不相容

固定 [HistoricalConsumersT30.py](G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T30HistoricalCopyAuthorization/HistoricalConsumersT30.py:24)，SHAc40ca09084a5c617e18d2817e4b6816b67f35b35238b700356eedaea7b074eb7，actual_index14–31 要求真实 Bundle.verify index；24 read_bytes，25 与 row canonical UTF-8/hash 比对，28 把 raw bytes 传 parse_bundle_manifest。固定 [contracts.py](G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T30HistoricalCopyAuthorization/FixedInputs/Backend/services/engine/src/video_creator/domain/contracts.py:1704) 的1704–1708仅 str 分支 json.loads，否则直接 value.get；bytes 没有 get。

H01–07 未执行，这不是已有两轮失败的原因。Test 应保留同一 canonical 字节/hash 检查，传 ABI 接受的已验证 UTF-8 str 或严格 JSON dict；不改旧 parser ABI、跳过 Bundle.verify 或 SQL 伪造 ready index。

首轮固定 Probe SHA16f6a501b8169875be4537fce1b99af1cbc86eac0ec495a6ed4d7b276b35ae45；基类103532946225f9e3de97667c10fc3df8e9e81c95635b8a8c53c4dce593e358b1；修订二基类494734cd86983a321b28fd5ca0d2c04ed1349e4dab449726bd5fc4e4b3064c5f；固定 engine24aad20ab71ace1c1e03110f448b973c620007de79a17ea9656440d90c92c351。全部精确路径见 Findings/InputPins。

## 下一验证准入

1. 原 Test owner 修复四项，固定新源码、输入/解释器闭包与一次有界新计划。保存机制应先有可审批的故障验证条件，不能靠整套成功才留下诊断；原两轮 raw/断言/deadline/NOTPASS 保留。本轮不批准第三次启动。
2. 新预算按上述真实实例准备和 I/O 分层进度论证；不以死锁猜测解释旧超时、直接延长原批或无界重试。先确保实际 phase/逐方法进展、retained process 身份/请求/exit/EOF 可保存。新 deadline 不改原90秒 forced red。
3. 原10断言与 H01–07 完整前提保持。actual_index 必须来自真实 Bundle.verify；correction_origin_evidence 全祖先/sourceSet、copied-rights 真 verify_rights_evidence、final源文件 fresh 检查与 writer 内 current scope、真 publish、私有证明不泄漏均需实际接线。有限 prepare 驱动代码不代表 H01–07 执行。
4. 尚缺真完整 outputs/masters/文本/QC、settled Operations、ASR journal/时码和独立 MM05/精度 authority、current Owner/resource/runtime、版权许可、foreign/local/human 来源及新 fence 联合闭合。不能以结构夹具、ordinary hook、True 或 SQL ready 填补。真实法律权利撤销和 execution policy 撤销分别验证。

## 终态与交接

固定 reader 全部结束释放，无生产 freeze/live handle；本角色只保存字节身份与既有 JSON/XML/AST 标准库分析及报告。没有运行产品/Test/DB/native/ASR/网络，fee/key0。SOURCE_EVIDENCE_REVIEW_FINAL 不等于 Acceptance，也不等待 A26/T31 或未来资源。

RV41FactsCheck SHA7d1cefd5078c9b455719ee2ddbf8abdc71dc55202c384906efb61e101c025699；SourceAfter SHAb98f048e3753ca4f2be37666c49a071f4308b6571f9abdf1aac2511fee9e5d6b。正式 Snapshot/Handoff 给出报告/Findings/InputPins 完整身份；原失败和缺失完整保留。
