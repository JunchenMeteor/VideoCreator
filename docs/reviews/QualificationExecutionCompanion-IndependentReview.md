# ADR0067 资格执行伴件合同独立评审

结论：`DESIGN_REVIEW_SUPPORTED_ONLY`。QCOR-P01 所指的执行伴件格式、原来源和唯一解析职责缺口，在本固定 0067 合同范围可标为 `CLOSED_DESIGN_ONLY`。没有确认新增 P1/P2。该结论没有关闭实际采集、导出、消费收据、计时控制、对称 reader 或真实资格的实现及运行缺口。

本轮只读停止材料，不执行候选、产品、Test、第三方/Pydantic、SQL、Native、模型或网络，不读取 Integration 正在执行的 BindingPreparationRoundOne。原 19 耗尽、31 未准入、两个原 RECORD 纯数据失败及完整 R1 后连续 R2 要求保持。

## 固定输入与读取范围

唯一正文为 [ADR0067 普通副本](G:/开发测试/Codex/VideoCreatorImplementation/Architecture/QualificationExecutionCompanionContract/Ordinary/ADR0067.md)，24793B，SHA-256 `1138133993eaa2d55573bd4cb7f1af1996324220c146495a46ba35e2b5249b17`，117 行全文已读。正式 Handoff MD/JSON/Snapshot 分别为 `768bc34a2ebcce3cd6fd29b26c368f0c0791cc01c2d71de2386aab5a4b3fbf3e`、`d5e7b945a00411cef0d8c195ba2f7870db34e37eeeea8dbbb2a8287ece24798a`、`512784692f8aabf8343c6b026a29d95eb1a5184503eb550771c0fdbf93d0e9c7`。

[OrdinaryIndex.json](G:/开发测试/Codex/VideoCreatorImplementation/Architecture/QualificationExecutionCompanionContract/OrdinaryIndex.json) 的 23 个普通副本均实际核 byte/SHA。自有 InputBefore/After 固定 34 个有限路径，包含这些副本、正式材料和治理输入；身份末核见自身交接。索引中的生产 `source_path` 没有作为读取路径。没有全 131 源逐行重审或运行环境资格扫描。

已对照原 QCOR-P01 完整 finding `996b5b403ac1d82ef5028682a118dfea319ef536fc59c0e5674a86bb38204ee4`，原 0066 `593569baf7070820e28e4087d962589054ad949ebe3e6edc5bf21603afeb1f12` 及其独评 `c928783ed9c6d4a806a3b2f4dc8d4ad40df02fedfe6e1ce3aed992046556ee78`。必要源码为本阶段普通副本的 Engine、Executor、组件诊断服务及类型、原资格 trust source、qualifiedAuthority 和 Native Registry；全文读取与有界函数读取分开记录于 ReviewFacts，不把身份核对当全文代码评审。

## QCOR-P01 的设计关闭依据

0067 第 25–41 行将七种 format/version 与 exact 公共字段固定，沿用原 QualificationRef、Identifier、RecipeSourceRef、完整 method/binding/target，没有新增 issuer 或业务授权。第 47–95 行分别定义字段、状态/null、真实 bytes/SHA、费用和失效证据；第 99–109 行明确唯一捕获、导出、受保护读入及 Native 对称职责。原 finding 第 11 行允许必要唯一私有导出尚未实现，但必须明确 NOT_IMPLEMENTED；当前正文第 21、63、101、113 行保留了该事实，没有用任意 dict、callback、signature 或 outcome 代替真实导出。

| 伴件 | 原合同行 | 独立核到的实质约束 |
| --- | --- | --- |
| request | 47–49 | 原 OperationIntent 五键、实际 CapabilityRoute、注册 input bytes/ref 和 payload；method/route/input SHA 对齐，不能换 key 或创建新权限。 |
| result | 51–53 | 原 observation 的七字段和原 cost/null 关系；外部字符串保存实际 UTF-8 raw bytes，result JSON token 与原值对应，不能用浮点重编码求同 SHA。正向需 succeeded、真实成本和实际消费结果。 |
| operation | 57–65 | 原 prepared/submitting/pending/succeeded/failed/unknown、settled、claimed fence 和账本单位；旧 unknown 不清、历史 fence 不替换。真实 dispatch window、同 clock 原 bound 和实际退出必须存在，created_at/heartbeat 不代替。 |
| consumption | 69–73 | 真实诊断 Fact/Ref、原 AnalysisOperation/OutputRef、同原 writer 消费和首次 committed receipt；不能事后读回时间冒提交时间或重复消费旧 fact。 |
| before/after source | 77–83 | 原 v2 wire、原 session/seq、完整 14-key reply、same original observed member；真实 peer/current 仍需原强源。NULL/timeout 不算失效，200 binding 改变必须由原 Python current 门实际拒绝。 |
| invalidation attempt | 87–95 | 仅四个原入口，actual accepted/rejected/unavailable 分开；原 EngineError、真实 driver 进入次数、完整有限一致性 snapshots。必须实际拒绝且无新增账本/成本/完成事实；共享账本并发变化为 inconclusive。 |

第 105–107 行的 cross-ref DAG 从 request 指原 input、result 指 request、operation 指 request/result、consumption 指前三者/fact、attempt 指 before/after/request，不回指上层报告/未来 record，避免自 SHA 环。原 held materials 的 purpose、大小、总量与 path/current 门保留；2 MiB 超限或缺完整闭包仍 not_ready，不能截断集合当 absence。

## 与真实停止源码的对应

[11-executor.py](G:/开发测试/Codex/VideoCreatorImplementation/Architecture/QualificationExecutionCompanionContract/Ordinary/11-executor.py) 全文 SHA `b4b9c89f10520dfa7715c38834c0da4206d0ff95db93594377a0a27db02f804e`：prepare 先于原 route/credential/claim/driver，已 settled 返回原 observation，非 prepared 要 reconciliation；driver 异常与未知实际成本保留 unknown。该原 body 没有新的资格计时、捕获或 exporter。0067 将这些列为新增而非假称现有实现。

[10-engine.py](G:/开发测试/Codex/VideoCreatorImplementation/Architecture/QualificationExecutionCompanionContract/Ordinary/10-engine.py:640)，SHA `e6d0d39730907b4ac9ccb93072aa4412bb918c49f3a50bfacdef66f6b07600b6`：640–663 的同 dedupe immutable replay 在原 input/step/route/cost 完全相同时返回原 row；它不需要重新取得执行许可。700–730 的 claim 才绑定实际新提交 fence/current，并在原同 writer 末核。732–788 的原观察和结算保留实际成本、unknown、预留及共享预算，793–818 的 Step 完成另需全部成功结算。合同没有把旧 fence 换成新 fence、将费用 unknown 填成零或以诊断 fact 伪造 Step completed。

该 replay 是后继 negative case 的必要边界：一次失效后 `prepare_original_operation` 若合法返回旧 immutable row，必须记录 accepted，不能把它改名为 rejected 或放宽原 current 去造通过。0067 第 89、95 行已将 accepted 与 qualified negative 分开；只实际被拒、完整 effects 不变和 driver0 的窗口可通过。合同没有证明四个入口在所有既有状态都会拒绝。新 operation、claim、consume 和 source assert 的触发条件应由原 Test 分别按真实原入口验证。

[12-component_diagnosis_service.py](G:/开发测试/Codex/VideoCreatorImplementation/Architecture/QualificationExecutionCompanionContract/Ordinary/12-component_diagnosis_service.py:393)，SHA `b73938149e2ba87daf9c4c88ef6b996dfa7b025db3acc922c248d363f0cf965b`：393–416 读取真实成功/settled Op、原 payload/route/input、actual observation raw SHA 和 output SHA；419–440 验实际输出 Ref。541–615 的原 record 调用实际 factory verifier，再以原 issuer guard、来源 captures、同 writer 的 fact/result/selected 索引和后门提交。原代码没有资格 consumption receipt/首次 committed_at，因此 0067 第 69–73、101、113 行是待实施的同 writer 合同，不是已观察提交。

普通类型 `15-component_diagnosis.py` 59–62、68–94、139–204 保持原 MetadataRef、method、Observation、Fact 和 AnalysisOperationRef；`14-contracts.py` 293–345 保持真实 route、Intent、Observation 的费用和结果关系。新 companion 是旁证协议，不替换这些业务类型或提高精度阈值。

[21-03-qualified_authority.py](G:/开发测试/Codex/VideoCreatorImplementation/Architecture/QualificationExecutionCompanionContract/Ordinary/21-03-qualified_authority.py:65)，SHA `f67431c13c0260948e40099735a5197ab61424d308ea9706980588aee69614a8`：65–138 的严格 reply、session/seq、实际 maps、peer 前后门和期限；144–171 的原 observation member/epoch 和 record/revision/floor；173–217 的强 lease/unknown 保留。assert_current 成功 reply 不返回 observe 的 files/id/time，失败帧按原闭集为空资格载荷；任何原 exchange 异常会使本地 epoch 失效。0067 没有用新 observe 冒旧 member 拒绝，也不把普通 reply JSON 变成原 member。

[22-33-35-native-qualification_registry.rs.rs](G:/开发测试/Codex/VideoCreatorImplementation/Architecture/QualificationExecutionCompanionContract/Ordinary/22-33-35-native-qualification_registry.rs.rs:65)，SHA `ec436f54ceec091ad649ecf8f887009c1cfc52938bf485e2c6731e7194fc5eee`：真实 current/gate、record 时效、Registry pointer/epoch/ref、Process 强成员与 read guard 在 observe/assert/begin/end/Drop 中核；未确认退出时原 guard 保持至 Process/Job 真终态。合同没有将 source-frame 截图、EOF 或签名当已释放生命周期或当前权力。

protected companion reader 的 trust source 与被检验失效的旧 resource observation 是不同职责。`20-native_qualification_trust.py` 76–116 的真实原连接/held materials/current 门和 130–179 的本地成员/同 connection SQL captures 仍须存在；0066 第 64 行的历史 H archive 与当前 C 分开。后继 reader 应用当前合法 held 来源读原捕获 bytes，不能复活已经失效的旧 observation，也不能让新 C bytes 补造旧 H。未获得合法材料来源或旧确切 bytes 时，保持 not_ready/historical_evidence_unavailable。

## 未实现与后继职责

Backend 尚须实现严格七 companion 类型/serializer、真实 service 注册 capture、原 dispatch/exit 计时持久事实、原消费同 writer receipt、完整效果采样、只读 immutable export 和共享 protected reader。恢复只允许从原授权 durable facts 重建；未记录的 timing/receipt/effect 仍缺失，不能补猜。原 Op 去重和跨 fence 只读复用不授第二次 driver、收费或新 key。

Integration 尚须实现同源 Native 七 grammar/cross-ref reader 和原 authenticated frame 捕获。Media 的真实 typed deadline/退出控制源及其冻结定义/身份未在本输入中提供，合同第 63、113 行明确须后继固定；一般 Callable、日志时间或普通 DTO 不足。Test 后继实际原始证据与独立 criterion/source 仍须评审；Review/Acceptance 不由 producer 自授。

当前没有任何产品/SQL/pipe/模型实际执行证据证明本新 capture/receipt/export/reader 已运行；没有实际新的 Owner replacement 或安装资格证据。本设计结论不能把 31 NOT_READY、真实 bounded call/result consumption/invalidation、媒体/Owner/native/API/MCP、完整安装或三 OS R1→R2改成通过。

## 工具历史与末态

ea7612 合并正文输出截断，已用 aac4a8 的 ADR 1–80 和后段完整输出、438f33 的 85–117 及 Native 67–100 补齐必要正文，不把截断称全文。d297a1 在完成有效正文输出后，末尾误指不存在的 `Architecture/.../Ordinary/InspectInputs.ps1`，自然 exit 1；该自有定位错误保持，不算产品失败。后续 feb32a 正确读取自身脚本，5aa972 自然 exit 0，未重跑目标。所有读取均为有限文件/元数据读取，不持生产冻结或资源句柄。

末核、实际自然终态与全部读者释放以本轮 FinalHandoff 和 Agent TRUE FINAL 确认为准。身份核对与本设计判断均不构成运行授权。
