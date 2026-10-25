# RV74 — B37 原 pipe/process 关闭事实有限独立复审

状态：**FINAL / SOURCE_STATIC**。**RV73-P01 CLOSED_SOURCE_STATIC**，仅绑定 B37 固定 Windows 源与同 owner 串行私有清理语义。没有新增本片阻断 finding。原 RV71 buffer/OVERLAPPED 跨解栈 holder 的源级结论保持；这些都不等于真实 Win32 中断/复用、安全自然退出、RuntimeBinding 或产品 R1 通过。

本角色只读固定源、接口、旧报告与 owner 原静态收据，进行了标准库 hash/AST/diff 文本分析。没有产品 import/exec/eval/call、产品 code object、Win32/native/EXE/pipe/Test/OS signal/DB/模型/ASR/网络/秘密/费用/安装执行，没有读取 B38 或其它活源。

## 固定身份及变化范围

B37准确根 `G:/开发测试/Codex/VideoCreatorImplementation/Backend/RetainedHandleClose-B37/`；普通源在 `SourceCopies/`，索引在根下 `SourceSnapshot.json`。B36基线准确根 `G:/开发测试/Codex/VideoCreatorImplementation/Backend/RetainedIoOwner-B36/`，只读 `StaticRevision/SourceSnapshot.json` 与对应 `SourceCopies/`。RV73原正式报告/交接保持原字节。

| 固定件 | SHA-256 |
| --- | --- |
| B37Handoff.md | `afe6f15ba89d2ee1af72aceb9b356e64fae84c2bb8de113bcbbe3be1b9cb34cc` |
| B37Handoff.json | `e34905265f7f24715170ee39b65714ec614366df4fd1e5edfd627eb02e75d8f1` |
| Interfaces.md | `e803305f1e0b5e51e9259416c11d46d3da50acde0a862ccd1d5adc2acee76367` |
| SourceSnapshot.json | `0e58fcd24620e39f6f5d8f80f6868f0ecf65560a5e4954843a8ed72e4789a494` |
| B37 Windows 源，26966B | `491c1e0d3d8472b7dc87ab06740f5f3ec28e3f78509e97882cbe84c75946aecd` |
| B36同源，24596B | `c4bb35a79d96691a47bba4de3a098414a46987fa16a443f41ca1624c25f50309` |
| B36 StaticRevision/SourceSnapshot.json | `85c5a9ad54c15d2b5b40e4a8330f771a61bb953baf1bd32e3f834ab85bbf266b` |

双方各62个完整普通源实际 path/bytes/SHA 核相同；名单完全一致，唯一变化为 Windows 私有源，B37每个 before SHA 均匹配 B36。其它61源及 B35 cli/main.py、cli/startup_services.py 的原字节保持，没有把 source copies 混成当前运行环境。142项必要输入末核 changes=[]。自身 `RV74Snapshot.json` 保存所有精确绝对身份；`RV74ActualDelta.diff` 记录实际前后变化。

独立 AST/diff 核明仅新增 `_RetainedHandleClose` class、全局强字典、private `_close_retained_handle` 与 `WindowsAuthorityPipe.close` 修订；其它顶层语句相同。原 `_Win32`、OwnerProtectedNativeBuild、`_RetainedIo` 三整类及 Pipe九个原方法等同（含 _transfer、_finish_retained_io、observe_retained_io、terminal判定、read_exact/write_all）。这些比较保护源码范围，不替实际安全验证。

## RV73-P01：精确源级关闭依据

固定源码完整路径：`G:/开发测试/Codex/VideoCreatorImplementation/Backend/RetainedHandleClose-B37/SourceCopies/services/engine/src/video_creator/infrastructure/windows_authority_pipe.py`。

249–260 `_RetainedHandleClose`保存原 owner、固定 attribute name、原 numeric HANDLE、原 API-bound callable、contacted/confirmed/error，257入模块级强字典。它与调用局部栈分离，不是只保布尔值或 weakref。450–459只接受内部 pipe/process 名称，并优先找同 owner is self/name 的旧 holder；没有公开数字句柄输入、重连或另一个进程/HANDLE。

原 RV73触发为 CloseHandle 已执行而后续 None 未赋，第二次 close 再提交该可能复用数字。新463先锁存 contacted，再465进行唯一原 wrapper 调用；466仅在实际 wrapper 返回后确认。此处即使在第一次 OS 调用后、确认记录前再次解栈，已登记 holder与 contacted仍存；下次同 owner 到470–473只能重抛原 error/close_unknown，不能再走465。若 marker已设但实际 contact未发生，也按 unknown保守保留，不以无响应或异常证明未接受。

466已确认但478赋None前被打断：后续走同旧 holder，只允许字段保持原数值或None（474–475），再做确定字段清理与移除，绝不再调用原 wrapper。478已None但479字典删除前被打断同理。新过程没有提前将 owner字段置None授关闭完成，也没有把旧holder当可新用的访问票据。正常确认清理顺序为 **原 wrapper return → confirmed →字段None →移除strong record**。

只在没有旧 holder且真实字段None时457–458无动作。已登记 precontact holder的contacted false可进行第一次原close；wrapper抛异常保error于468而保持contacted/unconfirmed，不能凭错误文本、6、PID消失、取消返回或任意bool当拒绝/关闭事实。既有 `_Win32.close`不能提供持久的同调用False/error原记录，因此此候选不冒称所有wrapper错误明确未受理；它采取unknown不再重试。这与实际已证明precontact区分，属于安全保守，而非“异常算关闭”。已知0/无效non-handle的原wrapper no-op语义保持，不因此授实际有效HANDLE关闭证据。

以上覆盖 RV73原 **pipe/process accepted-unobserved →再次close可能重复提交** 的具体源码条件，故限定关闭其 SOURCE_STATIC finding。没有运行中断、原 OS BOOL返回、受控句柄复用或false-refusal实验；真实运行finding未由本报告关闭。

## 原 I/O前置、错误优先与finally

481–485仍先invalid并调用原 observe_retained_io。B36持有原 pipe/event/OVERLAPPED/buffer/参数的强字典与具体完成/unknown规则完全保持；accepted/unknown I/O、未确认event关闭或观察再次解栈均不能越过observer进入两个handle的close。没有新ReadFile/WriteFile、buffer、event、locator、原数据I/O重交或自动RPC。

488先pipe，494位于finally中尝试process，保原清理顺序；490锁存已捕获pipe error，若process也失败，496–497重抛前者并以process error为cause，而不是吞错误返回成功。两个原 unknown holder各保自身error与owner。没有要求调用者恢复原交换：connection仍invalid，后续仅同 owner的私有观察/清理使用既有事实。

支持范围是已保存contact/confirmation/error且同owner串行调用的机制；既有 connection lock语义没有新线程/自动supervisor。本次不宣并发直接调用private methods、任意再次异常在error记录前或记录后瞬间、解释器关停/内存耗尽、长久unknown清理liveness都安全。Interfaces对即时传播可能被再次异常改变作了明确限制，不把此瞬间当已终态或丢失已记录原contact。其它原native build/临时token等关闭路径不是本RV73精确pipe/process finding的运行关闭范围。

## 原 owner 静态收据与未执行范围

B37 preparation87d1cd/0、changed-source static23edeb/0被正式交接记录；本角色原收据只读，owner7180/Ruff372 actual/publicwait0、communicate EOF/streams_closed、62copies/55AST、无sticky/exception/drift。physical child PID/Job没有被该lint收据证明；不能将它当本次真实OS受理/完成，也不能用同数PID替creation/HANDLE。B37无新failed patch/static批；B36/B35原失败及misleading旧diffheader继续保留，不回填/擦除。本角色没有重跑Ruff/AST owner命令或任何之前通过批。

其它61源字节不变，源码层保留 B35同Engine/Bundle/registeredRuntime的startup接口、Owner/fileID/drive/peer/fullmap/is/sessionepoch、not_ready零Evidence、预算/unknown/rights/floor/lease/fence/RES拒绝等；这些实际业务及caller供给尚待各自独立运行证据。原不具备qualified/native全启动/真实Owner权限仍未具备，不能将关闭flags当安装或许可资格，也不以永久503替未来正式准入。

## 后继Test具体条件与安全准入

由独立Test在另固定源码、计划、资源及guardian身份的批次验证，而非Review执行或本报告直接允许任意危险注入：

1. pipe/process各自正常与字段None再close；保原wrapper/HANDLE/owner，对应全记录正常移除，实际close一次，无新的data读写提交。
2. holder已登记但marker前；marker后而OS未接触；实际CloseHandle执行但确认未记录；确认后但None前；None后但registry删除前。各状态分列，unknown绝不为了收尾重复调用；确认后的metadata补清只操作记录。
3. 循环/handler/caller边界再次中断，原holder/API callable/handle/error在外部强字典保持；两handle同时失败的pipe主异常、process cause及仍可检查原事实。需实际原操作收据，不把普通field bool/Mock call count当OS完成。
4. 原I/O accepted-unobserved、未完成buffer及event-closeunknown须继续阻止进入pipe/process关闭；原event/OVERLAPPED/buffer保到同原GetOverlappedResult真实终态，没有重提交或新句柄/PID替证。
5. 受控句柄复用负例只能使用本任务自产无秘密对象，原native guardian持有实际CPython进程/HANDLE/Job到真实terminal，实际original resource identity、close完成与byteEOF分别观测。不得对其它进程、用户资源或现不受保护版盲注入。先核具体计划与执行授权，静态flags、合成机制或RV72正常13绿不自授该运行资格。

真实OS all-case关闭、guardian terminal、Owner/资格/native/三OS完整启动、媒体/ASR/作品以及完整三OS R1独验后连续R2仍须完成。本片不等待这些缺项占读者；所有必要源码读者已释放，所有读工具终态，无live产品/Test进程。过程准确根 `G:/开发测试/Codex/VideoCreatorImplementation/Review/RetainedHandleClose-RV74/`。正式metadata finalizer实际返回由调用者观察后另记。
