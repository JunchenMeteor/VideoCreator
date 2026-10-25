# RV63：B29 真实 Owner bootstrap 源码有限独立评审

**RV63-P01 / P2 / Backend / OPEN_SOURCE_STATIC**：管理 registry 后续使用捕获的 OS/目录身份，不能保证当前实际目录仍与绑定相同。其余已读入口/固定旧 writer 支持设计的有限接线；三份真实 help 与两轮静态检查只证明该声明范围。**未运行真实 Owner、OS 权限、秘密库、数据库或恢复，不批准 RuntimeBinding/完整运行/Gate/R1。**

## 固定输入与评审方法

正式来源 `G:/开发测试/Codex/VideoCreatorImplementation/Backend/OwnerBootstrap-B29/`。最终源码只从 `FinalSourceStage/SourceCopies/` 读取：58 件普通源全部 bytes/SHA 匹配，六变化源完整相关正文与必要原 registry/Control/policy/admissions/reauthorization/SQLite 接缝已读。前 B28 53 件中只有 CLI main 修改，另增五 Owner 模块，52 件旧支撑 SHA 保持。`main` 独立 diff 只新增 owner parser 与惰性分派；未改旧公开 DTO/default/SQL、预算/unknown、API、Worker或媒体代码。哈希保护不等于新 caller 的全部行为已测。

正式/治理、58 源、原两阶段输出/收据、必要 runner 与旧 main 共 **84 路径**，末次输入无变化。Review 未 import 产品、执行 help/Ruff/Test、读数据库/OS 账户/凭证、发网络、安装或收费；未读取 I48/T45 活产物或当前生产源。Handoff 大 JSON 以完整解析后逐必要字段/实际路径读取，未用截断输出冒全文。

| 正式件 | SHA-256 |
|---|---|
| B29Handoff.md | bac9c6e06c612f9733fa8a9227f15441097c14ce9df6745f12b38155ce29c3c1 |
| B29Handoff.json | 371ee841d3ac1d6b85040c814fcd31440adc036cc78cdaf7ba5f6235ce25d3ed |
| B29Interfaces.md | 83085d8284f2fa8ed31368f894f386335a572982036dfbff7d19a40e9627ea46 |
| FinalSourceStage/SourceSnapshot.json | a948f5e1b42c5760f53e9734ef871661e975b616dfd88350a76e35b928f97f15 |
| StaticAndHelpReceipt.json | a1efc03c60e76017f671cdea8a968da7e3cd027d761d1942151a148b559cfc43 |
| FinalSourceStage/StaticReceipt.json | 4e356de4ded38b04f52199dcd75e2f440e99e05398d595eb4d03d2462815d130 |
| RevocationTargetChanges.diff | ad454473fc3669af2711cf83d3518c09a3a1efa12ddc22ae11a2968d6689d822 |

六最终源 SHA：

- `cli/main.py`：cb2802590cfddc6175e185e55522af309377baf77968c8f6b77b3bac0d4defed
- `infrastructure/owner_identity.py`：58eea3fe521060d215e6f3d7fc494b6998330c6a093c5a47d80c8583b8d2db79
- `infrastructure/owner_secret.py`：c5c3e7ad8f357be8a448065a98f7fccaebf97a029cf06a24be047a8c624c1fba
- `application/owner_bootstrap.py`：37b9d13a214d03283a32effd4a0dd0c3dcab7e140e65f19891855cc7abd2f694
- `application/owner_services.py`：0e6504ec13a59162eb298a5843ce193cf883a88cdf1ec5644b256a929e5dc046
- `cli/owner.py`：0a1b29a75692575a29bf611fad3c8a34f43a982546cc50008428803796c7215b

## RV63-P01：当前权限检查沿用捕获的物理目录身份

**严重度/归属**：P2，Backend。SOURCE_STATIC 已定位；没有真实 OS 目录替换、授权成功或权限绕过复现。

**精确固定源**：`G:/开发测试/Codex/VideoCreatorImplementation/Backend/OwnerBootstrap-B29/FinalSourceStage/SourceCopies/services/engine/src/video_creator/application/owner_bootstrap.py`，17444 bytes，SHA `37b9d13a214d03283a32effd4a0dd0c3dcab7e140e65f19891855cc7abd2f694`。

53–58 行仅构造时调用 `inspect_owner_directory` 并保存 `self.os_identity`。`_decode:68–74` 将原记录的 SID/UID/device/inode 与该**捕获值**比较；`current:104–112` 读取路径上的 DB/Control/generation/expiry，却没有重新核实际目录。`PersistentOwnerManagementRegistry._current_record:244–251` 与 `action_guard:265–274` 沿这个 current，held record 分支也不读取当前物理身份。

**最小条件**：合法 D0 已构造 live store/registry，随后同一绝对 data 路径换为实际 inode/device 不同的 D1，同时保留同原 instance、绑定、项目、policy 与 Control 字节；继续使用该对象/已签发 capability，不新建 Store。无需 symlink 或自报管理员字段。长寿命装配可触发；当前 CLI 也有源码窗口：`cli/owner.py:78–90` 先装配/认证，104 行之后才作策略 TTY 确认，期间发生替换则同回调继续使用捕获值。

**调用链**：CLI callback → `OwnerAuthorizationService._action:24–29` → registry `action_guard:266` → `store.current` → `_decode` 比旧 D0 值 → 原 `ProductionAuthorizationService._action:165–170` 短 writer。该 writer 的 `_principal` 使用 held record；`Database.connect:151–152` 按固定绝对 filename 新开 SQLite，没有原目录对象身份句柄。因此旧 D0 记录与旧 D0 快照可相互一致，但路径操作已经面对 D1，源码检查仍可能进入新策略 writer。

**要求/影响**：ADR0031 要求实际 OS Owner、本实例数据目录身份和 current 管理事实；B29 自述 device/inode 改变拒绝。这条缓存检查不足以保证上述不变量。它不是证明普通 token 可升权、不是 Windows 实测攻击，也不是所有 CLI 失败：替换后再运行新的 CLI 构造，会重新获得 D1 并拒绝 D0 记录；`owner-init/change:144` 有刷新，问题是 policy current/action guard 无对应刷新。

**最小关闭条件**：在可变路径锁/任何管理写入前、认证/使用 capability 时重新核实际 OS 主体和 data/Control 目录身份，并确保随后 writer 使用同一被验证身份；变化须拒绝，不能重写原绑定为新 inode、重置 floor 或靠同字节恢复洗绿。保原 receipt/current generation/expiry/revocation 与 worker 不读管理秘密边界。独立 Test 至少覆盖确认期间替换、已持 cap 后替换、实际 owner/链接/inode/ACL 改变，以及未变目录正常流程；拒绝时无 policy/Owner writer 变化。路径检查本身不自动宣称解决全部 OS TOCTOU，真实平台边界仍需实证。

## 其余可支持的源码机制

`owner_identity.py:100–122` 初始检查绝对本地已有目录、父链 symlink/junction、Windows 当前 process SID/目录 owner/DACL 或 POSIX uid/euid/目录 mode，并比较前后 dev/inode。这是实际 OS API 代码，未据此授三 OS/ACL 实机资格；P01 涉及后续 current 生命周期。

`owner_secret.py:29–71` 自生成管理秘密；Windows/macOS 通过允许的 OS keyring backend，Linux 使用 OwnerSecrets0700、文件0600、O_NOFOLLOW、有界实际 fstat/read、文件/父目录 fsync。canonical record/Control/commands 保存非秘密 binding id 和事实，未输出或 hash 秘密。Review 只读代码，没有读取真实 secret、.ssh、OS vault 或环境 credential。

`change:128–232` 用实际自有有限 project、明确 expiry、TTY 完整 `AUTHORIZE <instance> <action>` 与 OS 身份形成安装动作。稳定 action-key/proposal hash 绑定原 commands；独立 OwnerControl reserve→DB 短事务重核→complete 保高水位；缺 floor/落后/pending 拒绝。没有 `--yes`、caller bool 或普通 bearer bootstrap 入口。revocation/renew 的 generation、旧 cap/expiry 与 policy 实际 revoke 分开，不能把管理撤销称旧 policy 已撤销。上述事务/重启正确性仍未实跑。

**pending revoke 增量**：`revocation_target:114–126` 只读 retained Control/原 OS-bound binding，不发 cap、不写 DB、不清 pending。CLI revoke:66–74 用原 scope 后继续 TTY/change。原 commit 后 floor pending 可静态到 existing commands:155–169、同完整 request hash/generation completion；原 `current` 未放宽。错误 key/scope/floor仍进入原拒绝分支。第一次 help 对应旧实现，最终两源改变此读取路径，没有实际 crash/DB 恢复证据，不据 source 修正关闭真实恢复缺口。

`owner_services.py:42–73` 限同 Engine/Bundle/域 Owner 的装配；for_management=False 不解析管理秘密、不造管理 registry。直接私有 service 缺管理配置时 `_principal:36–38` 实际为503；普通 API 外层403是另一层，旧 API 源未改，不能混用层级。False 可继续独立 worker execution policy/floor，不自授管理能力。

新增 policy CLI 只分派既有 DTO 与 `ProductionAuthorizationService`/`ProductionReauthorization`；原 `_action` 进行当前 principal/项目、原 receipt、同 key 改 body409、原 Control 与短 writer。reauthorize 保原 Production/Run/request/unknown账本，不重置花费或盲重提交。注册只单 Owner 精确范围，安装 authority 与 factory 是私有可信端口；factory 非空或资源 SHA 不是实际资格。默认 serve/MCP/registered worker 未接新装配，I48 实现仍缺；本片不能据类型对象/源码端口授安装或自动成片。

## 原命令与未测边界

保原 942fc9 Ruff exit=1（formal history 记五格式/UTC问题，FirstRuffCopies 保当时源）；Review 未重跑或拼造首次工具输出。7a766d 原四 Popen（Ruff+三 help）自然 wait/communicate EOF/close，收据与原 stdout/stderr hash 对应，源 58/51AST、drift=[]。072d6a 最后两源 Ruff 自然0/EOF/close、无 drift；没有重跑三 help。原三 help stdout 为根、owner-init、owner-policy 的 argparse 声明，没有运行 selected Owner 代码。help 未另保存模块 origin inventory；其输出不外推实际 OS/凭证/Owner/DB行为。venv launch PID 不冒 physical child PID 或 Job 身份。

没有真实 Owner bootstrap/renew/revoke/policy、OS ACL/UID、OS vault/Linux secret、DB/floor/crash/跨进程/重启、安装 authority、同 API/Worker 装配、模型/ASR/许可/完整作品。既有普通管理403、预算20元及RES13原拒绝不放宽；配置503不当最终产品可用结果。完整 R1 三 OS独立验收后连续R2 目标不缩。

本 Review 37a2c0 的 PowerShell数组拼接误把目录/后缀分开，记录为自身路径读错，非 ACL/产品红；按固定 JSON identity 修正。85bdce 中一处旧 reauthorize 输出截断，115f69 已读完整该方法和相关 precheck；不将截断当全文。全部原读取工具终态，最后自身事实核 session55041→19e025 actual0，无重复执行原产品。

## 自有正式证据

Snapshot：`G:/开发测试/Codex/VideoCreatorImplementation/Review/OwnerBootstrap-RV63/RV63Snapshot.json`，SHA `c2d154b4066865b64ad60fc1efaf9874e50524e7f01844cbf6f7caea17629cae`。

FactsCheck：`G:/开发测试/Codex/VideoCreatorImplementation/Review/OwnerBootstrap-RV63/RV63FactsCheck.json`，SHA `5f3880dd6bf96d8d899776353fc4cce234a9d0fd925b2556dcf9ff01627ee5ba`。

InputAfter：`G:/开发测试/Codex/VideoCreatorImplementation/Review/OwnerBootstrap-RV63/RV63InputAfter.json`，84/84 无变化，SHA `7c73577653cdf14eddd9c93ca3edac49289c9b7739ad917843ad54c484595d50`。

全部源码 reader 已释放，无 current 实现 freeze/live 原句柄；P01 交 Backend 原 writer，独立 Test 后继反例另批，本 Review 不代实现/验收。
