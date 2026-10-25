# RV65 — B30 当前目录与同一 writer 源码复审、T46 到达边界

2026-10-09。永久独立 Review；SOURCE_REVIEW_FINAL。只读取固定普通副本并解析原有证据，未导入/运行产品、测试、DB、真实 OS 检查、Owner 动作、凭证、安装、网络、ASR 或模型；费用 0。完整三 OS R1 独立验收后连续 R2、实例持有数据与五步前台均保持。

RV63-P01 的原缓存身份授权路径可 **CLOSED_SOURCE_STATIC（限定三源版本）**；实际确认窗口、旧 cap、writer 内替换、Control 替换及 OS TOCTOU 运行层仍未验证。新 **RV65-P01 P2 / Backend / OPEN**：合法 SQLite TEXT Owner 记录被送入 bytes 解析器；B29 有真实组件失败证据，B30 继承同一缺陷尚未运行。不能以源码修正或 Ruff 通过签 Owner、Bundle、Binding、Gate、R1/R2。

## 固定输入与核验范围

B30 的 58 普通源全部核 SHA，三处变化、55 处保持 B29 旧 SHA。旧 B29 的三个变化前正文、原 RV63 报告/交接、ADR0031、B30 固定 diff/Interfaces/静态收据及 T46 正式交接/38 普通副本均绑定过程 Snapshot。T46 38 副本大小及原/副本 SHA 全匹配。末次本次固定输入核验 118 个独立路径无漂移；未重新盘点原运行的 1683 环境路径，也不读取 B32/current 或未来测试。

| 固定三源 | SHA-256 |
| --- | --- |
| B30 SourceCopies/services/engine/src/video_creator/application/owner_bootstrap.py | `35200d06bd2a54926a5914c0cb06c92e4f55d36c6e307219fc87a8f0315da996` |
| B30 SourceCopies/services/engine/src/video_creator/application/owner_services.py | `57ea29425bb0e71b7d920ff292c21a3630421fdfb975d29cc23fddc3d57e5968` |
| B30 SourceCopies/services/engine/src/video_creator/application/production_authorization.py | `dbec8e2002a00c39c7c908e8636f0db66d73a908c38bdf99ca88dcd0539bf6ff` |

固定根：`G:/开发测试/Codex/VideoCreatorImplementation/Backend/OwnerDirectoryCurrent-B30/`。完整 58 源和所有正式路径身份见 `G:/开发测试/Codex/VideoCreatorImplementation/Review/OwnerDirectoryCurrent-RV65/RV65Snapshot.json`；本表不替代完整索引。

## RV63-P01 有限源码关闭依据

1. `owner_bootstrap.py:53–70` 锁存实际 DataDir/已有 Control 的原 LocalOwnerIdentity，`assert_current_directory` 新取原 OS inspector 事实并与原基线比较；无 caller identity、重新绑定 DataDir、copy inode 或 floor reset。构造时缺 Control 仅首次 initialize 经原确认、原锁及 metadata 空检查后建立初次 Control identity（143–176），renew/revoke 与已有 Owner 记录不能借此恢复丢失基线。
2. `current:116–126` 在锁/路径 DB 连接前、decode 时及正常 context 返回检查；`revocation_target:128–141` 保原只读 scope 和 pending 限制。`change:159–176` 在原真实 TTY 确认后检查；244–256 在实际 bootstrap writer 进入和全部写入后、commit 前检查。`OwnerBindingRecord` 与 `confirm_local_action` 正文 hash 与 B29 相同；CLI/assembly/公开 DTO/schema 及其余 55 源未改变。
3. `PersistentOwnerManagementRegistry._current_record:271–279` 的 held 分支也读当前目录，不能只返 cached record；`authenticate:281–290` 在颁 cap 前后检查，后检查失败丢弃未交付 cap 并重抛；`action_guard:300–310` 保原 RLock、OwnerControl 锁与 held record，正常返回再检查、finally 清 held。原 cap issued/issuer/expiry/binding/project 校验沿原 registry，未改成 True。
4. `owner_services.py:26–32` 的覆写包住 `super()._management_transaction` yield 的**同一个 connection**：进入后校验，原 mutation/metadata/commands 写完再校验。`production_authorization.py:44–47,172–181` 基类仍包装原 DB transaction，无新 writer；异常到 `database.py:159–169` 的 rollback/rethrow/close，正常才 commit。原 reserve 在 writer 前、complete 在 commit 后；失败保 floor reservation。原 action exact replay、pending/lagging floor 与无 floor 禁止重置逻辑未被删去。

这些静态控制点能拒持续存在的身份替换，并补上原 long-lived/held/policy writer 路径。它们是路径 stat/SID/UID/ACL 检查，未新增目录句柄固定或 VFS；瞬时换入又恢复、检查与系统调用之间的所有 TOCTOU、线程/跨进程原子性均不能据此关闭。继承 decoder 错误当前使正常读取提前失败，运行层尚不能证明上述分支实际到达。

## RV65-P01：合法 SQLite TEXT 的类型接缝（P2，Backend，OPEN）

最小条件：原 Store.initialize 已保存正常 canonical OwnerBindingRecord；同 Store/current、Registry 构造或同 key exact replay 读取该记录。无需数据损坏、伪造授权或目录替换。

实际源链：`engine.py:47–48` canonical 返回 str → B30 `owner_bootstrap.py:254–255` 写 metadata/commands → `0001_ledger.sql:2` 与 `0002_cancellation_and_commands.sql:4` 为 TEXT → `database.py:151–156` 默认文本读取，无 text_factory 转换 → `_read:89–91` 原样传 row[0] → `_decode:74` → `bundles.py:96–116` 的 strict_json 在 112 执行 data.decode。正常 str 没有 decode，AttributeError 不在两层捕获范围；B30 `_decode:80` 的新目录比对尚未到达。旧 B29 `_decode:62`/`_read:77–79` 是同一缺陷，B30 没有引入它。

T46 原 JUnit 的 C02–C11 十个 error 节点均保留该 AttributeError；代表 C02 Rows-terminal 记录真实生产初始化写入的 metadata.value / commands.result_json 为 JSON 字符串，Probe 的 116–137 执行真实 Engine/Store initialize 后在 registry 构造失败。OS身份/确认/秘密分别是显式 TestOS、TestConfirmation、内存 TestSecretStore：这是 **B29 真实 Engine/SQLite/Store 组件反例，不是实际 Owner 授权或 vault 运行**。B30 的同型失败仅 SOURCE_STATIC，不能倒填为它的真实测试。

归属 Backend：在 Owner 专用 decoder 明确持久化 TEXT 边界，保留/检验 canonical 原文并显式严格 UTF-8 编码后送 bytes parser，或采用明确支持该文本的专用严格解析器；不要盲改通用 bytes strict_json。三个入口——metadata current、commands replay、pending['record']——都应一致覆盖；保持畸形/重复键/nonfinite/noncanonical 拒绝、原权限和 ErrorEnvelope。独立后继实际 initialize→current/registry→原 key replay，再到 floor/revoke/expiry/目录 writer 分支；原红与断言保留。详细七源完整 hash 早交片见过程 `RV65-P01-SqliteTextFinding.md/json`，其早交时只记录静态结论，新增实际证明仅在本正式报告。

## T46 原 NOTPASS 与 Test 自身边界

`T46Handoff.md` SHA `a93ef8517fce1c02eedee34c8d74c239cc7f9a950a9089b3edb0565ad08d4266`；JSON SHA `7eecbdda35f4ee657a4bd30f9fbf9af213a87e5c75ececaf307e35d02e94fa76`；manifest SHA `ffa883a6c3d1d41ff327e0f4c639aa909da55fae531d079e460a566b65ecffb0`。

- 原 session 52522→ff4750 自然 exit 1；JUnit `tests=12, failures=1, errors=10, skipped=0`，只有 C00 PASS。Probe PID 53972 exit 1；ActualMain driver PID 24568 exit 0；两子进程原 byte stdout/stderr EOF、no force。**内部真实 cli.main exit 1**、owner_directory_denied；driver 0 仅确认预期拒绝匹配，不把 CLI 原失败洗绿。CommandReceipt/T46MainToolTerminal 均保 input_changes=[]，原 1683 路径是 Test 原记录口径，不是本 Review 重新全树实测。
- C00 真 WindowsIdentity/GetAcl 及实际 inspector/selected CLI 观察到目录可被其他主体写入，原 403 拒绝正确；TTY 未到、Owner action/vault 未执行。真实 main 的错误也保同 403。只支持该负向权限门，不能借此判首次授权正向完成。
- **RV65-I01：P2 / Test / OPEN（真实 C01 setup 失败）**。固定普通 `RunT46.ps1:46–47` 仅 redirect stdout/stderr；Probe:231–235 原 `assertFalse(sys.stdin.isatty())` 实际 True，在 confirm_local_action 前失败。Test 后继须真实 redirect stdin 管道并关闭自己 EOF，保原非 TTY 断言；不能 mock isatty、删除断言或归 Backend。
- **RV65-I02：P3 / Test / OPEN（已观察 instrumentation teardown）**。ActualMainStderr.raw 保 logging `_removeHandlerRef` teardown 时 `SecretBoundaryT46.py:27,33` 的 module=None 导致 `.startswith` AttributeError ignored。该 profile 在 ActualMainT46:29 安装；Test 应仅为 module 类型做严格 guard（或正常恢复自己的 profiler 生命周期），不吞/降真实 secret/产品错误。它不改变 main exit 1 或 driver 0，也不能叫新的 Backend main 错误。
- C02–C11 在 `mechanism` 的 registry 构造处终止；C11:365 的 mechanism 先于 374 的目录 rename，后者及 DirectorySwapResults 根本未到。replay/expiry/revoke/floor/policy/unknown budget/不同目录 writer 等目标未执行。原 T44 import 拒绝、T46 首 metadata 准备错误与原红都保持；未运行第三批。

## 下游与终态

仅 RV63-P01 原缓存目录路径得到有限源码修正；其运行验证未关闭，新 RV65-P01 保 OPEN。交 Backend 修 Owner 文本 decoder；Test 在新命名空间修真实 stdin/profile，然后独立消费新冻结源复验原 12 项及目录/held/same-writer 边界。不能给 B30/未来 B32 静态支持继承旧测试绿或安装资格。

所有本次源/原证据读取均关闭并释放，无产品 reader freeze；自有末次 InputAfter 无变化。SOURCE_STATIC 与有限原 B29 组件结果分别裁定，不代 Test、Acceptance 或人类授权；真实 Owner、实际 OS vault、API/MCP Owner 正向、Bundle、媒体/ASR、三 OS、R1/R2 仍待。
