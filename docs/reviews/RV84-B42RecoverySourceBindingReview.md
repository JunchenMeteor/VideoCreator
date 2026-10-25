# RV84 — B42 历史收口修订与启动来源候选独立评审

结论为 **SOURCE_STATIC**。CommittedReceiptRevision85 的 RV82-P01、RV82-P03 原源码缺口可有限关闭；独立运行要求仍未关闭。HistoricalStartupCandidate86 对原 RV82-P02 提供部分源码修复，但新增 **RV84-P01 / P2 / Backend / OPEN**，当前来源回退仍有真实性接缝。未应用候选，未授产品运行、安装资格、Owner 管理或验收许可。

## 固定输入及证据层级

本轮完整核对 committed85/75 AST 与 candidate86/76 AST。171 份普通源 SHA 全匹配；完整两个差异分别能从原普通件逐字重建。Committed 仅改 accepted_goal_facts.py、owner_setup_history.py；candidate 仅改 accepted_goal_facts.py、cli/native_startup.py 并新增 native_goal_facts_startup.py。owner_services.py、owner_setup_service.py、production_admissions.py、cli/main.py 的共享入口均未改。末核初始204条加6条补充去重为207个有限输入，mismatches/conflicts均空；不含运行环境盘点。

| 固定版本 | SHA-256 |
| --- | --- |
| Committed SourceIndex | 9397ecf0bc313fdce9a274a59e619766f629c005bec20ea2cf244a8cd60fb4d5 |
| Committed accepted_goal_facts.py | 432ac8b5bed854698b06c977311e859cd90ede54a4212eb3ee1916dfbf1ec319 |
| Committed owner_setup_history.py | 66a40a44ad9fc14ad67468b0300e6f8583fd021da81f462f83e181218394759c |
| Committed 完整差异 | a0a3558453094b262c8936ba7762252710d23ea1a82eb375b53b3e8fd0d39709 |
| Candidate SourceIndex | d333ac70b20065c00a5c2f338ea13216c80ea67f316baa4b6a48df9516bef9ee |
| Candidate accepted_goal_facts.py | 96b60983ccd7013ce29d6fd078255c78a657e5c4f1dd5f6b0b3381d89685b3f2 |
| Candidate native_goal_facts_startup.py | cf0e7fd871b106ce025e80722a8a491f5b80c3a0a75cf7219a387fc4ca784855 |
| Candidate cli/native_startup.py | 296fe9aa8578047fc0a62b336390be6996e7285b42b3aec659a0f9c19503796c |
| Candidate 完整20439字节差异 | a9d3b6ec64d60af74b5e4ab377349f900f0dde827bb9eb1b77542f9f6a518e15 |

完整普通路径、元数据、前后核与差异结论在本轮 [Snapshot](G:/开发测试/Codex/VideoCreatorImplementation/Review/RecoverySourceBinding-RV84/RV84Snapshot.json)、[SourceFacts](G:/开发测试/Codex/VideoCreatorImplementation/Review/RecoverySourceBinding-RV84/RV84SourceFacts.json)、[InputAfter](G:/开发测试/Codex/VideoCreatorImplementation/Review/RecoverySourceBinding-RV84/RV84InputAfter.json)，未拿热源码补固定身份。ADR0040/0041 的角色、真实历史来源和当前执行权限分离要求保持。

## 原 RV82-P01：CLOSED_SOURCE_STATIC，运行未测

[accepted_goal_facts.py:235](G:/开发测试/Codex/VideoCreatorImplementation/Backend/OwnerSetupRecovery-B42/CommittedReceiptRevision/StaticFirst/SourceCopies/services/engine/src/video_creator/application/accepted_goal_facts.py:235) 的 _committed_acceptance_facts 从原 protected intent 校验五个 planned IDs，包含 receipt_id；重读原 parent、child、Production、原 acceptance Run/Event、immutable Request 与 creation receipt。235–277 同时绑定 owner/instance、key、request revision/canonical/hash、原授权及创建引用、时间/registry revision、原完整安装和三个角色 refs、原 child policy。不是只核被修改叶子的自洽 hash。

调用在 finish_committed 前的319行；原事实查询加入 _FactReader 缓存，初始/final 同 writer 或 finish reader 重核。原 _acceptance_run 使用 production.accepted 原事件与原 Run，未取最新 Run；没有重新 create/accept、预算、计数或 lease 行为。candidate 保留这个修订。实际合法 replay 与逐层叶节点篡改仍须独立运行验证，不能据此关闭 RV80 的恢复交付要求。

## 原 RV82-P03：CLOSED_SOURCE_STATIC，运行未测

[owner_setup_history.py:165](G:/开发测试/Codex/VideoCreatorImplementation/Backend/OwnerSetupRecovery-B42/CommittedReceiptRevision/StaticFirst/SourceCopies/services/engine/src/video_creator/application/owner_setup_history.py:165) 的165–177形成三分支矩阵：成功必须 phase=completed、原成功 canonical/SHA 一致且无 denial；拒绝必须 phase=blocked、成功两字段 NULL、独立 denial 与本次真实 committed denial 相等；未 commit 仅 accepted/running/blocked、无成功或独立 denial。completed+NULL 与混合进度在 yield facts/writer 前拒绝。

188–210 的独立 denial 核原 GOAL_DENIED 命令、request SHA、metadata、setup journal/接受字节及原 intent，不能用 blocked 标签替原拒绝事实。合法 committed 路径只核真实 Project Owner，不强迫后来草稿仍为旧 revision；未 commit 仍核原草稿完整来源。accepted_goal_facts:338–345 在 purpose=None 前也调用矩阵，不能绕过损坏检查。真实 blocked 重启、later draft edits、相互矛盾行的回归尚未执行。

## 原 RV82-P02：部分源码支持，仍 OPEN

[native_goal_facts_startup.py:135](G:/开发测试/Codex/VideoCreatorImplementation/Backend/OwnerSetupRecovery-B42/HistoricalStartupCandidate/StaticRevision/SourceCopies/services/engine/src/video_creator/application/native_goal_facts_startup.py:135) 在读取原 facts context 后、任何 denial writer/complete 前绑定精确 Store/context/epoch/thread/原 Bundle、真实 domain Owner/OS root、原 Authority/OwnedConnection 与实际持久来源。_record 核原安装/登记/actions/commands；_startup 比较完整 map、engine partition、image path/SHA、role/instance 及三身份；_source_owner 重建历史 Owner 命令和实际目录/有限 scope。不用 SHA 或 carrier 声明代来源。

new member 仅是当前 context 的私有 frozen eq=False 对象，不能序列化为执行票据。167–187 的短 writer guard 不做新 OS/hash/RPC；初始/final 查询与 native pre-complete reader 检查真实缓存。事实 root 期限与执行 grant 期限分开；不调用 _active 为旧来源授执行，facts 完成后仍先 full Store.current 再正常服务。不同 Owner/map/role 没有进入已核 writer 的正常分支。

但以下新 P2 阻止当前候选的来源真实性闭合。

### RV84-P01 / P2 / Backend / OPEN：当前 tuple 不匹配时漏核其原 Owner 证明

精确源及完整反例见 [正式早交](G:/开发测试/Codex/VideoCreatorImplementation/Review/RecoverySourceBinding-RV84/RV84P01EarlyFinding.md)（SHA 41166c399af39d2e4f4087742b1aeeaf790055c6ac3263c492bfb04c3ffcf6d6）。

[native_goal_facts_startup.py:112](G:/开发测试/Codex/VideoCreatorImplementation/Backend/OwnerSetupRecovery-B42/HistoricalStartupCandidate/StaticRevision/SourceCopies/services/engine/src/video_creator/application/native_goal_facts_startup.py:112) 的112–119先 _record、再 _startup；409 execution_registration_startup_conflict 进入 fallback。当前来源的 _source_owner 仅在匹配的120–122执行，129–131只认证旧 pending 来源。固定 execution_registration.py:369–442 证明 _record 核的是 owner.execution.*，不补其历史 owner.bootstrap.* 命令。accepted_goal_facts:152–153仅核原 pending Owner 与实际 root；208–218也只核 successor 登记/动作。

最小静态触发：pending为generation1、current来源为generation2、实际root为generation3；原1和实际3的证明完整；current2的 canonical 安装/角色/执行动作完整，但其 bootstrap 原命令缺失，或合法 canonical result 的 request_sha256 损坏；较旧 carrier 只匹配pending1。fallback可绕过中间current2的原 Owner 命令认证。旧 _source_owner 虽解析所有 bootstrap result，仅对目标generation核其 request/action，所以有效canonical的中间损坏或缺行未因此被补核。

与 FailureMatrix 的“损坏 current proof 不回退掩盖”及 _select_source:101–102 相悖；可以继续到事实 denial/finish 接缝。不是已证任意权限、实际 OS/SQL 复现。需在允许 current tuple 冲突回退前认证它的完整历史 Owner 命令/目录/scope，并缓存对应查询；损坏应422 daily_project_fact_invalid 或相应原403，writer/floor不变。合法已认证 current 确有 tuple 不同仍可使用原 pending 事实来源；不能强迫新 current 等于旧 Goal，不扩执行权限。

后继 Test 由原归属者独立固定三代记录与坏中间命令反例，核 commands/journal/registry/floor/预算/unknown不变，并保合法完整中间来源＋旧carrier的收口对照。Review 未构造或执行 fixture。

## 作用域、异常、原失败与来源历史

候选 native_startup:22–30 保 instance/role/原 RegisteredRuntime 与 Worker非管理边界；32–46只持有一个原 Authority/build，经 gated facts→current→原正常装配。47–60 尝试两个原 close，cleanup异常仅加 note，并重新抛首异常；已取得 current 时再 release。connect_native_installation 和正常 NativeOwnerServices.close 是未改原路径，不能从新 except 的源码或静态0推所有 Win32 cleanup/unknown 已实测。原 holder/受理未知的独立 OS 安全验证仍待，未替换对象或将unknown标为成功。

Committed 原2d6106自然0：85/75AST、owner28448/Ruff4104、原 errors/drift/sticky空、wait+communicate EOF/两流关闭，仅源/语法/Ruff。Candidate原 eb9b17自然1，保3项Ruff原红（I001及两处BLE001）；修订21f060自然0，86/76AST、格式整理及明确 cleanup noqa、双流EOF/drift空。均非产品/Owner/native测试。原 process patch hunk错误和 guessed ReviewCandidateScope 文件缺失保留；没有静态0替代运行红。

原全局 startup hook 被拒且未应用；本候选仅上述三文件，Review未换 writer 执行任何被拒动作。方案是否窄化与工具/人类应用权限分列，本报告不代后者授权。SourceHistoryAddendum 与 Accepted.patch 仍仅回溯会话转录/文件：缺同期 raw 收据与真实callID，不能提升为当时原始审批证据；RV82-I01 原 raw 历史缺口保持 OPEN。

本角色的 e6adfb 读错复数文件名保留；该 shell虽0但读异常及其后残留变量输出排除，改按 Snapshot 精确 singular 路径8422b1/dc7c92。d5c4df猜 docs/architecture 路径退出1保留，31581d按rg定位正式 docs/decisions；输出截断以定向补读弥补，均不记产品失败。

## 剩余与终态

源码级 P01/P03 关闭不关闭运行要求；原 RV80-P01/P02、真实 headless/native重启及内存失效转交、合法 setup-aware成功、真人Owner child再授权、实际qualified producer/媒体多模态作品、三OS安装与完整R1独验后连续R2仍未验收。两种数据本地持有和五步前台保持。

所有固定源码读取已终态；最后输入末核 ebba56自然0，207项无漂移。产品import/Test/DB/OS/candidate执行、密钥读取、安装、模型、网络、费用均0。正式保存与最后工具终态由本轮 Handoff/Terminal单独记录；停止读取固定普通源，不等后继修复或外部平台。
