# RV84 后继 — HistoricalStartupOwnerProofRevision 独立复审

**RV84-P01 可关闭为 CLOSED_SOURCE_STATIC；原 RV82-P02 的候选来源认证缺口可有限关闭为 CLOSED_SOURCE_STATIC_UNAPPLIED_CANDIDATE。** 本轮未发现新的 P1/P2 源码阻断。候选尚未应用，未运行产品/DB/native/Test；该结论不批准应用或启动，不关闭真实恢复、资格及完整交付要求。原 RV84 报告和全部失败原件不变。

## 精确版本

| 件 | SHA-256 |
| --- | --- |
| Handoff.md | b54d0c043c0ba9dc73f4eb286b7e154e5f86a444df8c4004d1c3014305a158e1 |
| Handoff.json | 112d4685fb029952cc325b189516397c52009f8eab6ee6169168e65c785dbd99 |
| Interfaces.md | f99a9cab0b7127968e0f0993275b2ba34224ee166c8f70c1a6ee838c9b09c693 |
| SourceIndex.json | e2114b558ebfdf3129bf4241c840adf317cc20938534e6bac6213be74763a538 |
| 新 native_goal_facts_startup.py | 8e51611cecc732ed280bcb05f96bd71b75c666d163338f1bbcb7c03bfbdee9be |
| 对旧86窄差异，961字节 | a9b467820b98cfbea6d627e4fbf182c856ebc77e4248f4ca8584dc9520aa8fc8 |
| 对 committed85 完整补丁，20435字节 | 2e0e1c55c64bf8fd41bb355f4b20506752091e1f027a8686f3da30ab3d8f159e |

独立核新86、旧86、committed85共257份固定普通源全部 SHA；只对新86进行76个 Python AST 解析。新旧候选唯一字节变化为 native_goal_facts_startup.py，唯一 AST 变化为 _select_source；accepted_goal_facts.py 和 cli/native_startup.py 与旧86逐字相等。新候选对85仍仅三个原 prospective targets，没有共享 OwnerServices/issuer/setup/main/public hook。两份完整差异均由独立普通原件重建，逐字相等，未应用补丁。

## 为什么原反例被阻断

[新来源选择:112](G:/开发测试/Codex/VideoCreatorImplementation/Backend/OwnerSetupRecovery-B42/HistoricalStartupOwnerProofRevision/Static/SourceCopies/services/engine/src/video_creator/application/native_goal_facts_startup.py:112) 112–115先读取 actual current 的真实 _record，然后立即 _source_owner；116行才进入 _startup 的 try。仅118–120接收确切 execution_registration_startup_conflict/409。旧匹配分支中重复的 Owner 检查移除，原源认证没有位于该捕获范围中。

原三代反例中，generation1 pending及generation3 root证明完整不能替generation2 current的原命令。54–77从该持久安装正文取真实 generation/action/authentication IDs：中间命令缺失使 owners数量不为1；canonical result仍有效而 request_sha256损坏时，调用 accepted_goal_facts._owner_command:86–106重建实际原请求/动作并422 daily_project_fact_invalid。两种失败均发生于115行、tuple try和fallback之前，也早于 context native member、denial writer与floor complete，不会被409吞掉。

80–92继续核真实 Owner/OS subject/目录device+inode、instance/domain/executing principal、原 installation action/authentication/project scope/期限边界。未以只读 carrier/hash、声明或现有 generation1/3事实代真实中间命令。

## 合法回退与查询缓存仍成立

中间 current证明完整、较旧 carrier tuple确有差异时，精确409仍可以进入125–131；引用仅取 original protected pending parent 的对应role，旧 _record、完整 _startup 与 _source_owner均执行。匹配的新合法 current直接在122返回，未强迫它与旧 Goal refs 相等；没有任意历史扫描或 caller-selected ref。

当前和旧回退证明共用 _FactReader；它只允许 SELECT，50–68记录完整实际结果，重复查询漂移即拒。_bind_startup:150–162仅在完整检查后合并到原 context查询缓存，并核两个读取阶段的同键值一致。新 current bootstrap命令也在该缓存中；不是只记录 old tuple或预期 Bool。

原 native member仍核同Store/context/root/Bundle/Authority/connection/thread/epoch，assert_native_startup_fact_writer:167–187核原成员和完整 startup。accepted_goal_facts:367–404核原context/revision及每一缓存查询；denial transaction:418/428为初始/final门，finish:431和native pre-complete:441再核。源漂移在commit前拒并rollback；已commit后失败保持实际结果及原pending，以后只能真实finish。修订未在短writer增加OS/hash/RPC。

用途仍由原 protected事实确定，匹配source不授grant/Current/management/qualified。真实历史期限可过期；原 _active/current执行门没有放宽。native_pending_goal_store:221先绑定，再222 resolve；原私有CLI完成facts后仍 Store.current→原正常装配。headless分支和全部facts/CLI字节不变；原 reader-only native context缺member仍拒writer。预算、unknown、计数、lease/fence、Owner/policy/hash/source正文没有此修订变化。

## 证据层级、待测与审批

原候选lint三红/路径读错误保留；本后继原 c9508c自然0仅copy/hash/AST/三目标Ruff：owner18028、Ruff31000、86/76、0.572681秒、原两流EOF/关闭、sticky/drift空。真实 stdout19字节“checks passed”及空stderr的SHA独立匹配。它不是上述三代反例的DB/OS测试，也不是实际服务、Job或资格证明。

归Test的后继最小集合：坏中间命令缺失和坏requestSHA均writer前拒且原commands/journal/revision/floor/预算/unknown不变；完整三代＋合法旧carrier回退、匹配新current而原Goal仍旧refs、读间/初final/precomplete查询漂移、wrongdomain/map/image/role、closed/cloned/thread变化；真实过期grant能facts收口但正常执行拒。Review没有构造或运行这些测试，不借现有fixture/typed对象自授OS真实性。

原全局hook拒绝未重放。此不同候选的窄源码结论不替代原工具审批或人类允许；生产仍是committed85。RV82-P01/P03保持此前仅源码关闭、运行OPEN；RV82-I01仍缺同期审批raw/callID，回溯文档不能补该等级。RV80恢复/新Owner-child、实际 headless/native/live失效转交、setup-aware正常成功/重启、真实qualified producer、多模态作品及R1三OS独验后连续完整R2均未关闭。

## 终态

本后继 Snapshot初始281条加2个原raw，去重279个有限输入；末核03a3f1自然0，变化/冲突空。来源读取结束，无live工具/产品句柄，不读热源码或排队T56材料，不扫描环境。过程固定于 [OwnerProofRevision](G:/开发测试/Codex/VideoCreatorImplementation/Review/RecoverySourceBinding-RV84/OwnerProofRevision/RV84OwnerProofSnapshot.json)，完整diff/成员事实和末核另存；正式Handoff/Terminal记录最后保存工具自然终态。网络/密钥/费用/安装/产品import/测试执行为0。
