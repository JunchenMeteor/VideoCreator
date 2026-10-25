# Qualification coverage 与 Owner replace 独立设计评审

结论：ADR0066 的四报告/无环覆盖、H/C 分离与历史归档、独立 Owner replace/强 drain/全 expected-current CAS 和受控恢复方向得到 **LIMITED_DESIGN_SUPPORT**。存在 **QCOR-P01（P2，Architecture，OPEN_DESIGN）**：实际执行伴件的唯一冻结 grammar 尚未绑定，本精确版本 **NOT_READY_FOR_COMPLETE_IMPLEMENTATION**。本轮未确认第二个 P1/P2。不授源码实施、候选应用、实际报告通过、资格准入或运行；设计支持不关闭原 SOURCE/运行问题或完整 R1→连续 R2。

## 固定版本与独立输入

当前任务卡：`G:/开发测试/Projects/VideoCreator/docs/task-board/QualificationCoverageAndOwnerReplaceIndependentReview.md`，2698B，SHA-256 `a98000af3f6f6e851ef68f6e95b94b68db4066ace7963abafa05bf963980acf2`。当前 ACTIVE_DESIGN_REVIEW_ONLY 优先；下方 QUEUED 是历史，不合并 31 准备/0066 实现或已完成 P01/P02 源码复审。

主合同：`G:/开发测试/Projects/VideoCreator/docs/decisions/0066-qualification-coverage-and-owner-replacement.md`，29703B，151 行，SHA-256 **`593569baf7070820e28e4087d962589054ad949ebe3e6edc5bf21603afeb1f12`**。全文已读取：首个组合输出截断，后用 af2fe4 完整补齐 1–66；原输出保留，未以截断代全文。

停止架构根：`G:/开发测试/Codex/VideoCreatorImplementation/Architecture/QualificationCoverageAndOwnerReplaceContract/`。

| 正式件 | SHA-256 |
| --- | --- |
| Handoff.md | `bea15ebd5d4bb9b3a27144e03020d04d7a8f573b89dee916f2f6edc6071a7dcb` |
| Handoff.json | `132b86717699014122cb337671d4f2b4d58f43977b057e146becb0a5c450d94d` |
| Snapshot.json | `701f25f1c5ff867df3d46b1bd1702daa5a3ff33b8fddd1bd75d2f11bf396b6f3` |
| InputPins.json | `e18380f2731696d272f86547928991faee55b9cbbcee8d62d3bea5bb9b399e80` |
| OrdinaryIndex.json | `d7db8c6517aae1876d1f6a53faa16aef3ac7ae27a0de2cac8ddd3f5aae1f1417` |
| SourceAfter.json | `596d14d1961c09e29b4b559800e36d4aa3c5798a32cc1a00197c88030cc1c257` |

自身过程：`G:/开发测试/Codex/VideoCreatorImplementation/Review/QualificationCoverageAndOwnerReplaceIndependentReview/`。InputBefore 自己逐项核 36 个普通副本的实际大小/SHA，与成员索引无 mismatch；加规则、卡、主 ADR 与六正式件共 46 有限路径，InputAfter 同一组末核。只读 ordinary_copy；没有读取 original_path/source_path 的生产实现，也未复制/扫描整个 runtime。

语义读取与身份核查分开。全文读取当前 ADR、卡、Handoff 两件、原 14-installation_qualification.py、02-native_installation_record.py、04-installation_record_consumer.py、33-35-native-qualification_registry.rs.rs、34-49-native_commit.rs、25-QualificationCoverageGap.md 与 28-PartialInterfaces.md。相关 trust source 读取原 31–74/181–237，committed exporter 30–119；原 0063/64 及两既有独评只核必要覆盖/H-C/归档/原期限和未实施边界，不声称所有 36 源码全文独审。其余索引/普通件只固定元数据与字节身份。

## 四报告与实际 observation

0066:17–32 保留 strict canonical UTF-8、原字段类型和既有材料/帧/2MiB 上限；完整 binding 包含 registration/resource/runtime、catalog、完整 method/route/model/source/rule/check_kinds、target/fullmap/partition。一个聚合报告 1..16 section，按完整 binding 的 canonical SHA 唯一排序，reader 找唯一完整相等 section，不从包级 passed 推方法通过。suite→criterion/source、check→suite/实际执行、review→suite/check、acceptance→suite/check/review，禁止回指 future record/action/completion 和反向循环。

36–58 的 suite/case/check/observation/review/acceptance 外层语法明确：全部 check_kinds 与五个 observation 维度覆盖；每项原 case 对应唯一 real/pass result/完整 observation；synthetic/not_run/skipped/error 不算通过，不从多份冲突结果挑有利子集。独立 Review 必须实际审 case/criterion/source 和真实执行，source-static 只能 incomplete/rejected，OPEN P0/P1/P2 不可 supported；独立 Acceptance 要同 binding、完整集合和独立 review。producer_ref 不是新 issuer，body 的 role 字符串不证明独立性。后继必须实际核 producer/角色来源，不能作者自报签名或数组代验收。

60–62 的共享 `verify_resource_coverage` 方向适当：SQL 外依原 held protected reader 读 exact bytes、限额、canonical/SHA/purpose/全 closure 与独立实际来源，前后 assert_current；生成 eq=False 的真实源/epoch/thread 成员，短 writer 只核本地真实成员/captures，不作 RPC、文件/模型/测试 I/O。Native 必须按同一冻结 grammar 对称解析；Python 的 true 或 DTO 不是 Native 权力。

**尚未闭合的 P2**：45–50 的 `request_ref/result_ref/operation_ref`、`consumption_ref` 和 before/after-source/attempt 收据仍只用“实际原固定导出 grammar/收据”引用。没有给唯一 body format/version、exact keys/types/status、原定义/导出 SHA、protected reader 和跨 ref 关系。现普通 `14-installation_qualification.py:48–52` 的 QualificationRef 只标 document_id/revision/SHA；189–224 的 record/profile/report refs 不定义执行 body。原 `ComponentDiagnosticObservationV1` 的输出/检查 refs 也不单独证明 Step/Operation settled、deadline、消费入口和真实失效后的无副作用。

同 binding、suite 和签名都合法时，Backend 与 Native 仍可能选不同原日志/DTO，或只有 expected 字段而无 actual 成功/拒绝的唯一判断。安全实现只能保持 missing/unrecognized/not_ready；不能为闭合这一缺件接任意 dict/callback。详见本过程 `Finding-QCOR-P01.md`，3498B，SHA **`996b5b403ac1d82ef5028682a118dfea319ef536fc59c0e5674a86bb38204ee4`**。原 Architecture 需冻结必要执行伴件注册表，原 Backend/Integration 提供真实原类型/导出和 protected reader，Test 只负责实际执行/原始收据；不改业务 Operation/费用/unknown 或测试 oracle。本评审没有要求执行新目标。

原停止 `01-native_qualification_trust.py:181–236` 的 require_material/verify_record 仍主要核 purpose、签名、wholemap/profile/target/时间；它不是已经实现四报告覆盖 parser。现合同和原 Gap 不能作为实际 producer/report 已存在的证据。

## H、C 与同事务历史闭包

64 明确 H 按原 action accepted_at_us 复核原真实提交闭包，C 按现在 current/revoke/floor/许可及完整覆盖；replacement 后 C 的新 bytes 不得补造 H。必要 suite/check/observation/review/acceptance/criterion/provenance closure 的原 exact bytes/ref/purpose 与原提交关联，必须和 completion 同一 writer 归档，历史缺件仍 historical_evidence_unavailable。归档不授当前权力，也不收全 runtime 树或秘密。

与停止 0064 及其独评一致：历史 a1/body/key 原件保留，当前 a2 只认证 captures，新的 B 完成一次追加；完整 method/target/fullmap/route 真变化仍 changed409，不以名字关联。自然到期和显式撤销分别处理，不以新 ref 洗真实撤销。旧外部预读→writer 的原 30 秒机制、claim 新成员、未知账本/reconcile 和不重费规则仍保留。当前合同不改原 0063/64/65。

## Owner replace：权限、四 method 与强成员

70–78 将首次 InstallationRecordAdmission 十键/kind/empty-Owner 门留在原分支；新 replace request 独立闭合，携完整 expected old record/ref/revision/floor/Owner binding/material index 与新 record/材料/build/intent。intent 去自身 hash，request canonical SHA 是原幂等请求身份，避免 future event/ref 自哈希循环。同 action 不同 bytes409。真实 OS Owner/session/image/build/instance 管理来源及用户明确点击/TTY 才产强成员；Production/renderer/agent/普通 MCP 或描述 DTO 不可升级安装管理权。

82–101 的新 purpose/role、六字段 locator、真实 pid/creation/SID/image/hash/build/instance 核验，排除 setup-only 来源；四 method (`prepare_replace`、`assert_replacement_current`、`confirm_committed_replace`、`recover_existing_replace`) 的 request/payload exact 字段、strict seq/canonical/frame、原每次 10 秒期限和成功/错误码封闭。200/null 不能表示不确定。prepared/backend_committed/native_committed/unavailable recovery 的非空关系明确。confirmation reply 是事实描述，真实 action/drain/Registry 仍是权力来源；断连或旧描述不复活成员。

原普通 `02-native_installation_record.py:13–97` 只有 installation-record-admission 和 seq1/admit_record，确认实际缺更换 purpose/caller；`04-installation_record_consumer.py:101–104/119–122` 明确拒已有 Owner/record 的首次准入。0066 不应靠放宽这些旧门实现 replace；119/125 要求专用管理 caller、精确 format dispatch 与封闭 Original variant，这是必要新实现，不是现有源码已通。

## 强 drain、锁序与短 writer

107–115 要新增不可序列化 RetiredQualificationDrain，绑定同 Registry/installation/action/原 expected source/epoch 以及实际旧 consumer Process/Job 终态集合。ClosePipe、gate=false、()、drained JSON 或自报 PID 数组不够；不能等待 management child 自己。真实无法观察/超时/旧 held mutable 文件未释放，不返强成员、不提交新资格，不擅强杀。

原普通 `33-35-native-qualification_registry.rs.rs:58–64` 的 retire_current 只关新 lease、try_write/retire/epoch，返回 ()。122–130 的 Lease Drop 持原 RW guard 等真实 parent wait_exit 和 Job 后代为空；0066 要保该保护，新增消费者集合/drain 也必须覆盖显式 lease end 后仍活跃的实际 child，不能只检查“没有读锁”。这是 107–109 对全部真实旧 qualified consumer 的要求，尚未有对应新实现。

111–113 禁止拿 SQL writer、control.lock、安装文件锁或待退休 mutable holds 等 Registry/Process/Job；真实 Run/Operation/unknown 不取消、不清 pending、不换 key。先准备新 immutable 版本材料，真正 drain 后释放需更换的原 Control/index current holds，管理来源继续持有原 Owner/image/session/build 和新 immutable 材料，独立于旧 Production guard。原 `34-49-native_commit.rs:33–54/87–118` 当前 holds Control/snapshot/evidence 且限定 RecordAdmissionOriginal；原 `04-installation_record_consumer.py:70` 持安装/control 锁再做首次材料验证，不可把新 drain 搬进这个持锁段。新路径必须实际按 121 的先 drain 再 reserve/短 writer 顺序实施。

Prepared replacement 只能由本目的真实 connection factory 及同 Native 原 action/drain member 构造，不能 reply JSON 包装后自资格。SQL 外 current RPC/peer/member 真实核查；writer 内只 registered Python member/thread/本地连接生命与真实 SQL captures，不 RPC。管理 session 生命周期必须保留 Native action/drain member，外部失效不回 success。writer 后真实外部 current/committed 重建失败不得称 Native qualified。这些是可支持的设计义务；目前没有真实 OS/lifetime/锁竞争证据。

## current CAS、unknown 与冷恢复

121–135 的 replace 仍复用原 records/events/current/commands writer，追加 event.kind=replace、同事务 completion/set/archive，保旧不可变行。expected-current 不止 revision：实例、trust admission、旧 record/ref/revision/floor、Owner binding revision、material index 都须真实 captures/full CAS；writer 前后分别核旧 expected/正常新状态，冲突整事务 rollback。SQL 外已验 record/signature/fullmaps/权限/有效期，writer 不现做加密/管道/文件。

原 `05-committed_installation_evidence.py:37–89` 实际 exporter 比对 event/command/request/snapshot；目前 61/70 仍是 PersistedRecordReceipt/installation-committed-evidence-v1 的首次记录，0066 的新 variant/v2 closure 必须在 Backend exporter 与 Native reader 同源增量，不从 sidecar 回 success。原 Control.pending/floor 及更高/冲突 evidence/.pending拒绝保持。

恢复只同 action/request：未提交且真实 source/drain 有效才继续同 reservation；已提交但 export/floor 未完仅收尾；floor 已完/ACK 丢失仅原 Registry 重建确认；是否提交未知保持 unknown，不能新 key/revision、清 pending 或异常当 absent。冷新进程不从历史 receipt 造旧 Arc/Owner 点击；真实 Owner recovery 对完全相同原 request 建新受限当前来源。旧 SQL 未提交先核旧 current/floor 再真实 drain；已提交只准完成当前恰为该新 record 的收尾，不能第二次 replace。原 accepted/event bytes 保留，不复活旧 grant或改历史时间。

这支持 recovery 方向；实际双 caller、source/member 闭集、native recovery/TTY/UI/平台通道、强 drain 与正常同 action SQL/导出/断连仍 **NOT_IMPLEMENTED/NOT_RUN**，不能永久503占位称需求完成。

## 下游与终态

原 Architecture 先修 QCOR-P01 的停止后继合同并交独评；原 Backend/Integration 需依修后唯一 grammar 落真实 parser/export/对称 reader/Owner 管理 source/drain/CAS/closure/恢复；原 Test 生成真实 suite/check/observation/raw材料，Review/Acceptance 各自独立给完整实际来源结论。Owner replace 设计方向不授产品 plan、发布或任意费用。当前 SOURCE 两项修复、旧 failure、unknown/两authority/200000us、预算、19目标累计次数和完整 R1后连续R2 全部保留；没有安装整包或制作流程已通过的证据。

本轮所有工具是有限文件/元数据读取或自身过程写入，没有第三方/产品/Pydantic/SQL/native/网络/模型/费用/密钥/安装/测试执行。原 51c8eb 合并渲染截断，ADR首段另补；10ea3d 自然1为末次 rg 无匹配并有合并输出截断，消费源154–166/必要trust/transport/exporter由8e0b4d定向补齐；939eb1/71a556输出截断只按实际已读范围记录，Native commit首24行另补，不宣旧合同/普通源全审。末输入核对、报告身份与原工具自然终态见自身 FinalHandoff/FinalizerTerminal；Agent FINAL 仅在本人最后工具实际返回后确认，全 reader 释放，不以文件存在推完成。
