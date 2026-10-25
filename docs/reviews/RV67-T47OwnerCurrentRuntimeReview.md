# RV67 — T47 Owner 组件原运行证据独立复核

2026-10-09，EVIDENCE_REVIEW_FINAL。**原 T47 整批仍 NOTPASS：19=12PASS/7ERROR/0FAIL/0SKIP，整体自然 exit1。** 有依据将 RV65-P01 的 TEXT 解码缺陷限定为 **CLOSED_COMPONENT_RUNTIME（固定 B32，显式 TestOS/确认/内存秘密适配）**；不能扩大为实际 Owner 安装或 OS/vault 授权。RV63-P01 的实际替换后 long-lived/held/writer 路径仍 **OPEN_RUNTIME**，原源层限定支持不变。原 T44/T46/T47 红及未达到记录保持。

原测试运行与本轮只读评审分开：本轮未启动测试/产品/DB/OS检查/模型/ASR/API/native/provider/network/install，不读 B31/I49 当前源；实际秘密内容/秘密 hash 读取0，费用0。完整三 OS R1 独立验收后连续 R2、实例持有数据与五步前台均保持。

## 固定输入及实际命令/终态

正式根 `G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/OwnerCurrentValidation-T47/`：

| 文件 | SHA-256 |
| --- | --- |
| T47Handoff.md | `41522edb5015317165bba1892c112e336968663575cc4f691c4537891f4b2c51` |
| T47Handoff.json | `2fbd9e3f2ef4e5a0627c6089667901f1fef655fd48818d6822923a822a1162cd` |
| T47HandoffSnapshot.json | `51bb7a5fb4d688e6f5ec680f244e57cca5b601be28942136f68969b3a3be55f8` |
| T47OrdinaryManifest.json | `b13743171644eb15606c90fb4f6366baa2c8591c9538c9047b70d639fd23e3e2` |

普通精确根 `G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T47OwnerCurrentValidation/`。实际核79副本大小/SHA与其 original SHA，mismatch[]；包括原 XML/raw/Rows/事件/方法/原调用源码与5个 B32 正文，不复制 runtime。原代码被消费身份：bootstrap `d53044244c7206420e7961f97dd09a75d9bd3d8a4fcf452ad7e2ceea3797dec7`，owner_services `57ea29425bb0e71b7d920ff292c21a3630421fdfb975d29cc23fddc3d57e5968`，production_authorization `dbec8e2002a00c39c7c908e8636f0db66d73a908c38bdf99ca88dcd0539bf6ff`，engine `3cfb8351560e53b97cded1fcc26748479da70694ca69d2e45c7506d86c59b823`，database `96f1971b1b1980d39cb0575d6acce0325de657c24fa5d78e313aa2dcc8c6bef7`。

原命令（只读复核，未再执行）：system pwsh `-NoProfile -NonInteractive -File G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/OwnerCurrentValidation-T47/RunT47.ps1 -ExpectedInputIndex fbfdf3fd38d1076e5aad4916acd3a3e6f8838b656053907f759663a1ce69282f`；cwd该正式根。两个 Python原child均 `-I -S -B -X utf8` 调各 ProbeT47.py/ActualMainT47.py并带同索引hash，使用固定T26解释器，不据此授正式安装包资格。

原 session45631→cb62d8整体1；Probe PID23408，creation `2026-10-09T14:34:22.0684379Z`，自然1；ActualMain driver PID29548，creation `2026-10-09T14:34:43.6424196Z`，自然0。原 Process/双 byte stdout/stderr EOF、no force/无 lifecycle error，启动/终态/CommandReceipt对应。**内部真实 cli.main exit1**、owner_directory_denied403；driver0仅匹配预期负向拒绝。C00实际WindowsIdentity/GetAcl+inspector/selected CLI和fullmain的unsafe目录拒绝支持；两CLI的TTY都未达、Owner action/vault0。不能用wrapper0洗原main1或授真人Owner正向。

实际原19-node JUnit、Summary与19个case_result名字/结果逐项一致；事件共139（19 starts、19 results、39 rejection、9 decoder samples、3 metadata samples等）。原方法聚合 `_decode=109,_pending=3,current=140,change=36,assert_current_directory=369` 支持实际入口调用，计数只作旁证，关闭依据还包括真实case正文/通过断言/Rows。begin_step0/prepare_operation5/claim0/observe0，与五个Setup ERROR一致；不能拿非空JSON代成功。Test原 InputAfter记录1687和changes[]；本Review仅末核 **87 必要固定路径**无变化，不声称重核1687实体环境。

## 已到达的十二项与限定关闭

| 原case | 实际有限支持 |
| --- | --- |
| C00 | unsafe目录真实Windows/CLI负向403；TTY未到，不是Owner安装 |
| C01 | 真stdin/stdout非TTY，真实confirm_local_action精确403；修复原测试接线 |
| C02 | actual initialize/current/registry与同原key TEXT replay，changed body/空重复foreign项目/过去与bool期限拒绝；前后Rows完全相同 |
| C03 | renew generation2，新registry可认证，原cap/不同registry/到期cap拒绝；实际同进程重建registry，不冒OS进程重启 |
| C06 | actual DB已commit的revoke/floor pending窗口、错key/错body拒绝不清原floor；直接修改cached baseline的精确409。不是实际OS身份变化 |
| C07/C08 | 原floor丢失或高于DB503且不补0/重置；原Rows保持 |
| C09 | nonmanagement assembly不resolve TestSecretStore、registry=None、private get_policy未配置503；不是公开HTTP403实测 |
| C12 | 唯一TEXT `_decode` 正常canonical及9个严格坏样本精确422，前后Rows保持 |
| C13 | 真实本测试SQLite metadata行BLOB/非canonical/重复键损坏，current和旧cap均精确拒；只恢复原fixture字节、前后Rows保持 |
| C14 | 真实本测试原command行非canonical，原key replay422且current/floor保持；恢复原fixture后同key成功，Rows相同 |
| C15 | actual generated pending renewal的TEXT recovery与damage rejection，原same key/generation/floor闭环 |

ProbeT47.py:116–140 对 OS检查、确认和秘密实现分别用显式 TestOS（实际目录stat）、TestConfirmation、memory TestSecretStore；Engine/SQLite/Store/Registry/Control/事务是真实原方法。不能把这些适配变成真实 OS Owner映射/secret vault/安装authority/执行Permit。

RV65-P01：C02/C03与真实current/registry消除了原正常canonical TEXT的str.decode错误；commands同原key replay在C02/C14实际到达，pending record在C15实际到达。C12:433–441 九样本为bytes、None、int、坏Unicode、noncanonical、重复键、NaN、正/负指数溢出，均在444精确code/status422；事件逐样本九个，Rows前后相同。C13真实row的3类损坏及C14真实command损坏拒绝/原fixture恢复，保持严格JSON/canonical，不SQL制造新授权。

C15:493–495透明注入 reserve 前异常，**原change已实际生成Pending文件**，不是手写正常Owner记录；pending['record']为str。原Rows与after-pending-window完全相同（generation1/commands1）；仅原测试pending副本加非canonical前缀，samekey重试422/floor不变，再恢复原pending字节后重试成功：generation2、expires200000000、commands2、pending文件删、floor2无pending、旧cap403。原Rows-after-pending-recovery独立对应这些值。此关闭是该具体TEXT/恢复组件窗口，不能叫真实kill/全部崩溃恢复、unknown账本或policy守卫通过；这些通过case的 budget/Production/Run/Op为空。

**RV65-I01限定关闭**：RunT47.ps1:47实际redirect stdin，53 Close；C01:232–235真isatty均False并进入真实非TTY403。**RV65-I02限定关闭**：SecretBoundaryT47:27–29精确module类型guard，ActualMainT47:47恢复profile，原main stderr只保403、无ignored teardown异常；没有吞业务异常、改原main退出码，SecretBoundary全部行为未外推。

## 原七 ERROR 的独立归属与修复条件

**RV67-I01 P2 / Test / OPEN：五个ledger helper未开始实际Step。** C04/C05/C10/C11/C18原栈→Probe151–164 acquire_run160后直接prepare161→actual Engine._prepare_operation_writer586–588缺running Step，正确step_not_running。原方法计数begin_step0/prepare5/claim0/observe0；unknown观察和政策操作都未达到，不是Backend拒绝错误。

Test新命名最小先调用真实 `begin_step(lease,'t47-step','a'*64)`，再原prepare/claim/observe unknown；保存同run/fence/Stepinput/status/Op/reserved即时行，保持dedupe/route/amount/期待及原5目标，不SQL插Step、伪ready、关闭守卫、重置预算或降unknown要求。仅补入正确协议顺序，不保证后续所有代码能过；新出现错误按真实结果保。

**RV67-I02 P2 / Test / OPEN：C16 emit的kind冲突。** Probe405–426的实际target.rename413/copy414、newinode416和完整原文件bytes421断言先完成；422 `emit('actual_directory_replacement',...,kind=kind)`与emit:25的位置参数冲突。原trace保TypeError，确认回调527还没返回给Backend.change161，确认后的fresh目录检查/no-commit/floor/旧cap断言均未达。即时Replacement-DataDir.json424没写，post-run旧/新inode观察明标POST_RUN_ONLY，不能回填即时收据或生产检查；terminal Rows相同只证明测试失败窗口未改这些业务行。

Test仅改诊断字段directory_kind等不冲突名，保物理rename、新inode/原bytes、精确409与no-commit/floor/旧cap及即时身份收据，不捕获诊断错误后假称sourcecheck已达。

**RV67-I03 P3 / 平台约束：C17真实held时Windows拒Control rename。** 原C17:541–544已进真实action_guard并assert held record，然后replace413触WinError5；没有替换inode、held-path拒绝或oldcap断言。原Rows-before-held与terminal相同；不把此实际OS拒绝叫源码漏洞，也不能把它偷换成原“替换后当前性拒绝”目标PASS。证据显示真实Control锁持有期间rename被拒，不证明唯一具体HANDLE因果或所有Windows攻击路径。

Windows后继可另命名检验原held锁期间rename拒绝、原inode/文件/Rows保持及自然退出后的held清理；但必须仍列旧held换inode目标未达，不能关lock、mock stat/OS身份或改期待制造绿。旧目标需允许真实rename的平台/批准场景另验证，POSIX未测。C11修helper后才实际测long-lived DataDir/current/旧cap；C18修helper后先保真实OS是否允许Control替换的结果，原same writer rollback/floor目标不能提前绿。如果平台阻止替换，也不能释放真实Control锁再称原writer语义已测。

早交片 `RV67EarlySeamFindings.md` SHA `fb8931c0a16475281b7f340ff36ba92a1cc428e9c7fb4911855e258f08b6b017` 与本正式报告一致。两个C06/C09精确新码纠正有原RV66源码裁定和固定T47OracleCorrections；原12目标其余保持，新命名不能宽匹配403/409/503、删除预算/floor/真实current拒绝或改公开普通鉴权。

## 剩余范围及终态

RV65-P01关闭限固定B32的TEXT严格解析/三consumer真实组件窗口；RV65-I01/I02限本次stdin和profile问题。RV63-P01实际long-lived/held/同writer替换未关；unknown成本/lease/fence/policy回归、真实OwnerTTY/vault、API/MCP Owner、三OS实际安装、媒体/ASR、完整Bundle、Gate和完整R1→R2未授资格。原T47总批1/七ERROR不覆盖、不重跑；Review不实现/修测试/自兼验收。

所有固定源/原证据读取关闭并释放，无当前生产reader冻结。原所有child自然终态与byteEOF已核；自有最后finalizer真实自然返回由原工具回包确认。有限阶段结束，不等待T48或新资源。
