# RV73 — B36 原 I/O 跨解栈持有有限独立源码评审

状态：**FINAL / SOURCE_STATIC**。本角色读取固定源、接口及 owner 原静态收据，只作标准库 hash/AST/diff 分析；没有 import/exec/eval/call 产品或生成/执行产品 code object，没有运行 Win32、Test、native/pipe、OS signal、DB、模型、ASR、Owner、网络、安装、密钥或费用。

结论：原 **RV71-P01 的局部 buffer/OVERLAPPED 在再次解栈时丢失问题 CLOSED_SOURCE_STATIC**，仅绑定固定 B36 holder 源。所有实际运行关闭仍待独立故障证据。新增 **RV73-P01 / P2 / Backend / OPEN / SOURCE_STATIC**：继承的 pipe/process CloseHandle 未确认窗口可能重复关闭已回收句柄。因此整体原 transport teardown 安全仍未通过，危险真实异常注入继续暂停；RV72 正常 batch 不关闭这个问题。

## 固定输入与基线关系

准确 B36 根：`G:/开发测试/Codex/VideoCreatorImplementation/Backend/RetainedIoOwner-B36/`。只读其正式 ordinary；B35 基线根为 `G:/开发测试/Codex/VideoCreatorImplementation/Backend/StartupAssembly-B35/`。

| 固定件 | SHA-256 |
| --- | --- |
| B36Handoff.md | `280228a7a93e45ac794c1f7a43f641701a1f94f28201ac5b6de369caa33e9e8f` |
| Interfaces.md | `a0af1357042220026578463cf206b3c589cf130c26f8fbf5e98e4e0800f5d8fd` |
| B36 StaticRevision/SourceSnapshot.json | `85c5a9ad54c15d2b5b40e4a8330f771a61bb953baf1bd32e3f834ab85bbf266b` |
| B35 StaticRevision/SourceSnapshot.json | `3b5c85109fa5817ce39d233f4e49f2292703b7a660099f6723f0dd9a878ef1dc` |
| B36 windows_authority_pipe.py，24596B | `c4bb35a79d96691a47bba4de3a098414a46987fa16a443f41ca1624c25f50309` |
| B35 原同源，21730B | `bebb6a0ef7e3763436380489e845cd53215ebe4d4fb839bdbe6cc63d41d6cc13` |

双方固定 62 普通源全部按 path/bytes/SHA 实核，名单相同，唯一变化是该 Win32 文件；所有 B36 before SHA 均与 B35 相应正文一致，其余 61 字节/SHA 保持，包括 B35 cli/main.py 与 cli/startup_services.py。没有读取当前默认入口、B37、T50 或活源，没有核整个环境。139 项必要输入末核 changes=[]。完整身份见自身 `RV73Snapshot.json`，实际 diff 见 `RV73ActualDelta.diff`。14 个未改原方法 AST 等同只是文本保护证据，不是运行安全通过。

## 原 holder 问题：限定源级关闭

固定源230–246新增 `_RetainedIo` 和模块级强字典：owner、原 pipe/event、OVERLAPPED、buffer、DWORD count、原 function/argument tuple，以及提交/完成/异常/关闭状态均被同一对象引用。241实际入强字典，321构造在325可能接触 OS 的保守 marker 前；普通局部返回失败、`_transfer`/`_finish_retained_io` 循环条件或 handler 边界再次解栈，已登记操作仍由字典持有，owner 又保持原 API 与 handles。不是 weakref，也不是只记录整数或布尔值。

304–345维持每次一次原 ReadFile/WriteFile：309既 invalid 或同 owner 有 retained entry 就拒绝新提交；325先设 may_reference，326–327保存同一次调用已观测 result/error。352–354只有确切 precontact 或实际 false/non997 才当未受理，不凭异常、None/无返回或新 event/PID 证明未创建。accepted/unknown 走355–375，用同 original pipe/OVERLAPPED 取消并观测同原 event；只在 event signalled 后调用原 GetOverlappedResult 与414–422原 terminal 判定。6/87/996/STATUS_PENDING 不能 discharge。取消布尔返回、deadline、EOF、PID 消失均不直接释放内存，也不重新 Read/Write。

377–397为 event CloseHandle 建立 precontact 状态：event_close_contacted 在调用 wrapper 前设置；未确认 event_closed 时保留强 entry，不重试这个可能复用的 event 数值。只有原 I/O 已 terminal 且 event close 已确认，398才能删除 entry。已保存的 original_error 在373–374/386–394/399–402优先于 cleanup_error；unknown entry 的原异常可由同 owner 私有 observer 后续取回。401附 cleanup note 不是把 cleanup exception 改为业务主异常。

406–411 observer 只取该强字典且 owner is self 的原操作，347–349再核对象 is registry entry；不新建句柄、buffer、OVERLAPPED、locator 或 reconnect。436–440 close 在 pipe/process 清理前观察，观察中断、event close unknown 或未证明原 completion 都不能越过这个前置步骤。若原 completion 后重抛 primary，首次 close 是 error，后一次原 owner close 才能尝试后面的原 handles。这些源链消除了 RV71 的“已接受/unknown + 再次跳出局部循环导致 buffer 失去强引用”精确条件，故只关闭其 **SOURCE_STATIC** finding。

限制：本轮不证明真实 Win32 completion、任意 async/thread/解释器关停下整个所有权生命周期、所有 first-exception 的交付窗口、内存耗尽、正常关闭 liveness 或全异常退出。优先级支持针对已经保存到 holder 的原异常，实际第二异常在异常记录前/后、handler/loop边界的行为需独立核验。registry 数量/AST 不能代替这些测试。

## RV73-P01 — 原 pipe/process 关闭未确认时可重复关闭复用句柄

**P2 / Backend / OPEN / SOURCE_STATIC / inherited-tail**。

固定完整普通源：`G:/开发测试/Codex/VideoCreatorImplementation/Backend/RetainedIoOwner-B36/StaticRevision/SourceCopies/services/engine/src/video_creator/infrastructure/windows_authority_pipe.py`，SHA `c4bb35a79d96691a47bba4de3a098414a46987fa16a443f41ca1624c25f50309`。

调用链为 `WindowsAuthorityPipe.close` 436–446 → `_Win32.close` 87–89 →实际 kernel.CloseHandle。event 用377–397的 contacted/confirmed 状态，但 pipe/process 442–446仍是：调用 close；随后才赋 None。B35 原387–396已有此 try/finally 尾部；独立 AST 对照确认新旧尾部完全相同。新观察前置阻止 pending I/O 的过早释放，但没有消除此继承的关闭受理窗口。

最小静态触发：

1. 原 registry 已无未完成 I/O，或 observation 已合法完成；同 owner 的 close 进入441后的原 handle 清理。
2. 442或445的 wrapper 实际 CloseHandle 已被 OS 执行，但函数返回/443或446的 `STORE None` 前发生 KeyboardInterrupt/SystemExit/其它异常；此前不存在跨解栈的该 handle 的 close_contacted/confirmed 状态。
3. `self.pipe` 或 `self.process` 仍保存该原数字。pipe 路径的 finally 还会关闭 process，不会修复 pipe 的未知受理状态。持有该 owner 的可信上层以后再调用同一个 close，会把残留数字再传给 CloseHandle；若系统期间已将数字分配给另一原生对象，可能误关另一对象。

这里第二次 CloseHandle 的条件性可达性由源码证明；**没有实际 OS 中断、句柄复用或误关复现**。它与原 buffer/OVERLAPPED 跨栈释放问题不同，不是声称当前 pending buffers 已被释放，也不是声称 event unknown 保护失效。数字未复用的实际后果也未实测。普通值未置 None、取消成功或事后 PID 消失不能变成 close 是否执行的独立证明。

最小修复归属 Backend：对原 pipe/process 分别建立跨异常解栈保留的 immutable original handle 与 close 受理/完成事实。可能接触 CloseHandle 前先保守锁存 contacted；unknown 不重新关闭该 numeric HANDLE，不能仅把字段提前置 None 丢弃原事实或凭 invalid-handle/PID/event 消失授成功。确认关闭后才解除持有；真实未受理/实际进程 terminal 的恢复策略需与原 guardian 一致。同 owner observer/close 不重交数据 I/O，也不换 process/HANDLE、自动 reconnect 或改预算/权限。不要由 Review 修源。

需要原 Backend 新固定 source/diff/接口，再独立复审；Test 于获准的固定版本检查 pipe 与 process 两处：提交 close 前、实际 close 执行但返回未记录、返回已记录但字段未清、再次中断、后续观察/close无重复，以及真实 OS 同一资源身份/受控复用负例。不得在当前不安全版先做真实重复-interrupt 故障，不能用 synthetic pointer/布尔 marker 或正常 native session 替 OS 收据。

## 原静态失败与运行门槛

B36 原 initial apply_patch context verification 失败在编辑前，`InitialPatchVerificationFailure.md`原证据保；不当审批拒绝或产品运行红。原静态7df44a/1（owner11036/Ruff6448）两 BLE001、后 narrow revision3c9f54/0（owner25332/Ruff6448）记录 natural return、communicate EOF/closed、62copies/55AST、drift=[]；两记录逐 launch 区分，同数字 PID 不构成物理进程身份。原 StaticReceipt 与修订 StaticRevision/StaticReceipt 均保持原字节，仅 owner lint/AST，physical child/Job未证明。没有用新0覆盖旧1；旧 diff 的 misleading FixedB36 header 标签保留，实际 before/new hash为准。本角色没有重跑这些命令。

B35两启动源和其它61源未变，支持源码不退化；其实际 trusted callback、同 Engine/Bundle/API/MCP/registeredWorker、原进程/Job清理与 qualified bootstrap 尚未在本批执行。保持 original fullmap/is/epoch、protected build/fileID/Owner/drive、peer parent/creation/SID、不可逆 invalid、not_ready/零 Evidence、原许可/权限/预算/unknown账本/lease/fence/floor 与 RES 拒绝动作；字节保持不授全实际产品资格。

后继有限测试必须同时保正常/refusal/precontact、accepted-unobserved、loop/handler边界再次异常时全部原引用、同 owner恢复、真实同操作completion后主异常、event未知 close不重复、pipe/process未知关闭保护和无新的Read/Write提交。先原owner修 P01 并静态复审，再另按实际计划决定危险故障准入；本报告不自授 RuntimeBinding。完整三OS R1独验、真实媒体/ASR/安装与连续R2不缩。

本轮 Review工具全部已返回终态，无live来源进程/reader；过程准确根 `G:/开发测试/Codex/VideoCreatorImplementation/Review/RetainedIoOwner-RV73/`。必要139输入末核无变，正式metadata写入真实工具退出由调用者观察后提供。
