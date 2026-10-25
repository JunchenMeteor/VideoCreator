# RV15 — T14 真实单输出中断恢复证据评审

状态：FINAL。永久独立评审；只读固定历史证据，无产品、测试、解码、收费或密钥操作。不读 B9/W9 当前生产源码。

## 结论

RV11-P01（P2）可在精确已测窗口局部关闭：固定 B7/W7 的免费本地三镜头 profile，shot1 原 renderer 与 finish_output 已真正返回、Operation 尚 submitting/settled=0/observation=null 时，对自有 Windows 进程树按 PID/Creation 核实后实际强制终止；等真实墙钟租约过期；新 nononce Worker 核实原完整单输出，结束核实阶段，再取得新普通 fence，继续同 Run/Binding/Flow 到真实 quality 等待。状态为 **CLOSED_FOR_SAMPLED_SINGLE_OUTPUT_FINISH_BEFORE_OBSERVATION_WINDOW**。

这不是全部恢复窗口关闭，也不是 Gate0、AV、R1 或 R2 通过。原 T13 字面失败、旧 03966 测试和 candidate1 拒绝不改写；T14 使用 RV14 精确批准 revision2 的分阶段判据，不能称旧全 Run 总数 1/1 字面断言原样变绿。没有发现阻断此窄结论的新产品缺陷。

37 份生产源码正文未在 T14 运行前保存是实质证据限制。本评审仅恢复已有同 hash 历史正文；缺失的 B7 application/CLI 正文没有用 B9 当前源倒补。因此结论依赖独立实际运行、精确输入身份及即时父/子事实，不扩大成后端完整静态事务或负向权限审计。

## 固定输入与完整性

| 输入 | SHA-256 |
| --- | --- |
| RV15 卡 | c0805044e2d1666f2ca7ecb1fcc21b3d64714b5b9b5d2100afd61815418a9a43 |
| T14RealHandoff.json | 89518be831a78d161d32301c1c9e1baa9efc21ec39f8a87c5e2432743eeb2c55 |
| T14RealHandoff.md | ac17566be20c7427f54b99adf894e0d9cfc682c6306876843c015d4b98dc6130 |
| T14RealResultSummaryRoundOne.json | 99dfe6ace3ea68913e2af00bf5fdf031f7dfb151febdb9aea3752530d079e02b |
| T14RealCopiesManifestRoundOne.json | ea1575a201c758038599d4cf56e36077b78fe300317b3596f2b4a3b7e0da8078 |
| T14RealEvidenceManifestRoundOne.json | 4c555e2de75941b0ed3187d521beddfd0e564b1c98d49e39bad1f0a7a2625175 |
| 原 CommandReceipt | 420aab7f9afe1e1ddf29db4b84d697a0ef61cf7312cf32f33b7f1f927f3e7549 |
| 原 JUnit | ba48c0b9ef0440b53901f659798bf07ceeb1aa4606bdc93139d26a48399baab2 |

普通副本目录为 G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T14RealRoundOne/。121 份副本逐字节实算 SHA/size，全部匹配 manifest 中原/副本声明；未直接读取原私有 Case。20 个即时父事件、K 6 个及 RN 58 个子调用事件的 sequence/previous_event_sha256 全匹配，保留原时序，不把收尾副本生成时间当原观察时间。

RV14 criterion JSON 87e1e9d1f9d495ad97985df644591545ad1d93a7a935a1ddbd10cd79dd8bf927、MD 03d00c495ba732184cafebf745ba80c6530f5bada2ca925ab17a685813e1ef75；fixture manifest a7382bc0590b28d0ad40b0c376e34f1b66074aacee9d69689c4283e702ba0cc1。启动批准输入 09af0491ff38256ab11bbabd2462c4aee18d0b2902b07980cfbc7feb0b118007 引用 RV14 report bebf63a90ac7dd4c737ad93727e15586814b4352667071dbc10b01f90b043db1 与 Handoff 6c75aced55c0c0574d755f112d430879e08769f2b8df3a364a11817a6864e8af，revision=2、root_launch_authorized/independent_criteria_approved 明确。10 份批准 fixture 与运行 receipt before/after 全同 hash，不继承被拒绝 candidate1。

原实际命令在 G:/开发测试/Projects/VideoCreator：
`.venv/Scripts/python.exe -X utf8 -m pytest tests/gate0/test_t14_recovery_phased.py -q --junitxml=G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/T14RealRoundOne.xml`。
原 session 53757 / launch 1d2fb1 / terminal ca7c1a，receipt exit0；stdout 1 passed in115.92s，JUnit suite115.925s/case115.844s，0failure/error/skip。wrapper 墙钟124.239751s（04:03:36.054398Z—04:05:40.294149Z），不是把不同计时层强行写成一致。

12325 个 declared source/library/fixture 输入 before/after map 无变化；范围外68个 map 条目无变化；37个生产 hash 与批准输入及 receipt before/after 一致；20个外部资源/工具/审批身份在原即时观察前后相同。范围包括声明的 site-packages 文件类型，不能称穷尽 OS/stdlib/任意文件保护。

## K：原完成文件、真实 kill 与真实租约过期

Run 为 run-23490da28c6b48c79a47af2ab2bfb3db，Production production-5befcabb9d714348b6555222ebfee1d0。原 Operation operation-bc51e66334aa44bb8866d1cad97078d3，allocation attempt-608017be5fb04736b68fb6ab9a61aa27，Staging staging-feeb8b89561047b682f38838dc33abf8。

Evidence036/037 子事件记录实际 render_shot begin/returned，step local-shot-1、PID41484；Evidence029 LatchReady 在原 finish_output 成功返回后阻塞，未伪造媒体、SQL、租约或账本。父 Event0005/0006 显示 running/fence1、2Step/1Operation/1allocation/1inputAsset，Op submitting/settled0/observation=null；原 ready 文件91883 bytes，SHA341e80fd13c29157bf8f33392351127c350c0ea4f91d4d32e0d23db7803e2776，mtime1791432232483184300ns，无输出 Asset。

原 root52900，实际 Worker41484/Creation2026-10-08T04:03:45.1802200Z；captured tree 52900/45568/41484。父 Event0007 保留 creation_verified_test_teardown_force、taskkill tool0、实际被杀 root exit1及 captured tree_after=[]。这是合法故障注入，不是产品优雅停止0。

lease_until1791432261846042us；墙钟 before1791432235692976、after1791432261997328us；实际等待26.304357s。没有 clock injection 或直接改业务租约。

## R：仅核实原副作用后释放核实租约

新 root51108，实际 Worker45628/Creation2026-10-08T04:04:22.0754400Z；保持同 Run/Binding，核实 fence2。Evidence042—045 两次原 probe begin/returned 绑定唯一 call_id、此 PID/Run、原受控 Staging 路径，before/after SHA/size/mtime 相同且 changed_during_call=false；decoded=true、video/mp4、4000000us、720×1280、有音频和视频。实际两次 decoder 是 consumer 与后端复核，不是两次生成。

Evidence046/047 与039记录原 finish_reconciliation 成功返回；父 Event0012 在返回之后读取 queued、worker=NULL、lease0、presence idle。仍2Step/1Operation/1allocation/1inputAsset，原 Flow 仅 prepare；原 Op succeeded/settled1、零元 confirmed_no_charge，完整 generated_files 对应原 attempt/staging/SHA/size/MIME/source/rights。原文件 SHA/size/mtime保持。R 无 render、allocate、Asset或Step提交增量；不是只在尚未 finish 前取暂态计数。

## N：新普通 fence 合法续作，有序音画关联

父 Event0013 释放 R 闩锁，Event0014 观察 normal fence3>2。该 Worker nononce 模式经正常入口继续；Event0015 显示同 Run waiting_user、waiting_revision=local-quality.Run、lease0/workerNULL、5Step/4Operation/5allocation/6Assets（1输入+5输出），四个 render Operation 均 succeeded/settled1、Production零元。

原 shot1 Operation ID/input/claimed_fence1/observation_json 在 R与N字节相同；原 allocation及文件保持。N 仍有 shot1 的幂等 allocate_output 调用和 commit_generated_step，用原 allocation合法导入 Asset/补 Step；**不能写成 N shot1 完全没有方法调用**。其 renderer增量0；shot2、shot3、compose 原 renderer各实际调用一次。

五个有序生成输出逐项对应 Operation.generated_files→allocation(input/fence/output_key/staging)→imported staging.asset_id→Asset(hash/size/MIME/owner/source/rights)→Step有序asset_ids。五ID独立，compose顺序为video/mixed，不靠数量冒称映射正确：

| 步骤/输出 | Asset ID | 字节数 |
| --- | --- | ---: |
| shot1/video | asset-324cac58e69d488884b21b97578aac09 | 91883 |
| shot2/video | asset-f489f38b3103469b99fb62fa63fd1c03 | 62616 |
| shot3/video | asset-7d498fb5b37c463f9e7999c5e5c9c45d | 62820 |
| compose/video | asset-ebd72e6e107f4fa49f3480a75b2c24a6 | 205896 |
| compose/mixed | asset-1a0871720deb40b39fddb64802e4379e | 1920078 |

原 Binding SHA5e7cf158a31724524208dfdf8beb29da8b16067bdb58ce842a528225099c2295 和 Flow UUID f58dff1e-d989-527c-bd1c-e25f73ff85c0 不变；checkpoint依序累积原shot1/2/3 Asset前缀，再compose video/mixed，再review_pending。Plan/quality revision及最终等待关联经批准断言核，checkpoint本身不是成片验收。

Event0016 是独立测试角色读取自有 Objects 的精确字节副本到受控 Staging 后真正完整 decode；批准 case lines195—221验证复制前后hash/size及流/时长。6 Assets（含旧17.773379s输入WAV）实际decoded；三镜头4/3/3s、video/mixed各10s，四个视频720×1280且有音频，mixed只有音频。RV15只读此收据，没有自行解码、看/听作品，也不能称人工视听质量通过。

## 自然停止、保护及历史正文限制

RN wrapper实测nononce70秒自然exit0；父 Event0018捕获树空、presence stopped/expiry0/active=NULL。健康非空兄弟 root26252、children45564/29248 的 PID/Creation 前后保持且HTTP200；Sibling自然0、captured tree空、自有65045端口关闭由原final_cleanup记录。此范围不能继承到 API/Node监督、JobObject或所有父进程硬杀。

历史正文只读核对并保存至 RV15Snapshot：
- W7SourceFinal/workflows local_reconciliation SHA6a699c63e43b715bcf4fb05730628d3fb3dbb03adf2a58a843dc0cbb6b87a725；W7 ffmpeg SHA74854f37be5af6893952fbf35263db0f9d7aa0d0d7a1a5406c6fa62325660c0f。
- W6 normal workflow SHA173c9a474821e87cb1ac19d8717b48a9b71a0417e3fa1e24983b37940be25581；W6 local media SHA8fa206e0940b2be35efaf0d1d900d4b0563ccbaf4078bcda85446a84e5987285。
- RV13Snapshot既有domain/worker正文重编码SHA7aa24bd8f0e8555d408f59b7b42ff97f8d60841f7fff09910867fc6db43a10cc匹配T14。
consumer历史正文lines236—386显示独立核实入口、原文件有序集合、实际完整probe/二次hash、受限observe接口；不启动normalFlow/render/allocate/新AssetStep，typed queued仅建议，由runner最终处理。已测事件为此窗口的直接运行事实。

**RV15-I01，证据限制，归属Test/Backend（不作为本窄结论阻断）**：37生产正文运行前无归档；已有 B7Handoff与B8SourceSnapshot只是hash。未找到 B7 application/worker c61cfe0cd6ed866aab44dba2c08e75dc3e95b14ce41a642ec4aff36a8d5a34be、application/engine6dcd7c9b588f41cd25f9ac39b911837ad5fce9a3e4f5d977848168ded00d0a8e、cli/main7553fa5731f45d0448f382923344d4008525cc73a3eb416999c2b77cd7ad1b2b正文。缺口限制静态证明及未来重现，不否定已保存真实即时事件，但禁止补新源伪称历史。后续固定批在launch前归档声明生产正文；若需补此历史静态审查，提供已存在同hash普通副本，不要求B9停写或重新收费。

未覆盖：partial/缺失/损坏/篡改、多输出中断（本次compose正常两输出不等于多输出恢复）、stale fence/cancel/pause、重复核实、槽公平/热循环、其他kill窗、success Op未Step/Step未Flow、新后端/桌面整入口、Mac/Linux安装、AI主动创作、完整Bundle/RAG/Portal/MCP及商业R2。原本地模板与复用自造SAPI语音保持实验标识；费用0/keys0声明限原免费路线和角色动作，不冒称穷尽全进程网络审计。独立AV仍另行。

Review事实文件：RV15CopyChecks.json SHA286dd4f3785cc44db84ffeece00daedca3229d1927890d98ed79173c940c3d18；RV15FactsCheck.json SHA05839af612eca7627a808167ef0c6ba3dd7aea90708a5b517163dabffcf7b06a；RV15Snapshot.json SHAd38458494288e117613767f8d05a9a726971b7595e101fde05259fbd550b9046。自有汇总命令曾发生重复字段parse error及PowerShell false漏sigil，均未运行产品/测试；无效null Snapshot已在固定普通证据上修正为完整有效Snapshot，未修改原证据。所有工具终态、无live，结束本批。
