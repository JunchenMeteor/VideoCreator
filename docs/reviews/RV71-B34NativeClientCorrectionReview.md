# RV71 — B34客户端修复有限独立源码复审

结论：**SOURCE_REVIEW_FINAL**。RV70-P01在本固定版本**CLOSED_SOURCE_STATIC**，实际Windows同文件/别名/权限验证未测；RV70-P02的首次受理未记录窗口获得修复支持，但整体所有权安全仅**PARTIAL_SOURCE_STATIC**，新增**RV71-P01/P2/Backend/OPEN**：清理循环边界再次中断可丢失仍未完成I/O的Python局部内存。本轮未运行产品、模块/函数、Win32、pipe、DB、Owner、Test、ASR、模型、native、网络、秘密、安装或收费，没有RuntimeBinding或产品/Gate授权。

## 固定身份

准确根：`G:/开发测试/Codex/VideoCreatorImplementation/Backend/NativeClientCorrection-B34/`。StaticRevision/SourceSnapshot.json列61ordinary逐个真实hash/size核相同；与B31索引完整相同名单，只有windows_authority_pipe.py变化，其余60 SHA一致。B31原单源实际正文固定21c202…与B34新正文作独立实际diff，保存于自身过程RV71ActualDelta.diff。没有读取B35/I50/T49当前源/活证据，原RV70报告由B34InputCopies固定字节消费；没有宽扫描环境。

|固定件|完整SHA256|
|---|---|
|B34Handoff.md|d50178856a75f041ce7f0be7dde7bbf60f13c70d54e8ecc1e0cd160211f68bc2|
|B34Handoff.json|919838fcc6951740b7ba18924f4a3517ac2efd88fee62d047f1898fe0695af3b|
|B34Interfaces.md|aecffd8d8cc0245e59cc9bafa1392339f21256f1edffa987f9ba322908a7729e|
|StaticRevision/SourceSnapshot.json|f5112c722ba367917cd8c683667758e3b615fa63e70557c614edcb25941451a4|
|唯一新windows_authority_pipe.py，21730B|bebb6a0ef7e3763436380489e845cd53215ebe4d4fb839bdbe6cc63d41d6cc13|
|B31原windows_authority_pipe.py，16619B|21c202319fd5c6c8ed3306356259b2dfac016aba1c548c812a8e073216f7b355|
|InputCopies/RV70-B31NativeClientReview.md|d032b1e110590f4ceae40d01bb978a59ffb5b0a36c92af3a5b57d079fd282750|
|原StaticReceipt.json|665b5407976e782e92060372861261de41e38a79da7b8c0c17558d54a649a0d1|
|StaticRevision/StaticReceipt.json|cd4d7f75f081c35e7c055275633b7490f29d83e0357f0e34f3d44302d25b0b09|

过程准确根：`G:/开发测试/Codex/VideoCreatorImplementation/Review/NativeClientCorrection-RV71/`。Snapshot/InputAfter共77必要输入，hash/size前后mismatches=[]；61完整普通源只核固定件，不复制runtime。原只读及pin/dis工具均自然0；自有报告finalizer4a9cf6/1因Windows路径分隔符匹配漏归一化而StopIteration，原脚本/终态保留，修正仅自身artifact检索、没有产品重跑。所有工具终态、无live句柄。静态dis只生成**未执行code object**，不exec/eval/import/call产品；不是控制异常实验或OS复现。

## RV70-P01：限定SOURCE_STATIC关闭

固定新源22–41 `_local_image_path`先将斜线转为Win32分隔符，只去掉精确extended-drive前缀，随后必须字母drive+冒号+根分隔符；拒绝额外冒号/ADS、空分段、dot/dotdot、尾空格/尾点及控制字符，leaf symlink/junction拒绝。UNC、device、extended UNC不会在去前缀后满足drive语法。正常drive与相同extended-drive转为同普通Path，供原Owner规则调用，避免原extended父路径被UNC规则误拒。

文本不是权限：123–135新GetFileInformationByHandle取得原HANDLE的volume serial、64位file index及size，目录/reparse拒绝；203–227由独立trusted installed输入打开只share-read的extended Win32路径并保存_native_file_identity。155–180继续原Path.stat dev/inode/size、parent Owner/link保护、file Owner、**原handle native fileID**和whole实际字节/SHA/size前后检查。182–195必须 normalized **exact独立build路径**，再真正打开该同路径、核actualfileID/size相同；别名即使同hardlink也因路径不同拒绝，不能靠文本裁剪授任意路径。

267–283对原process HANDLE Query实际image与locator.image均走assert_image_path，仍核真实GetNamedPipeServerProcessId、os.getppid、creation、SID、child当前SID和独立installed SHA，不把locator自报SHA回填。原RV70最小`G:\Native\host.exe` vs同原件extended表示的字符串误拒路径已消除，具有实际原件检查边界，故独立关闭这个**源码**finding。

未测：真实ordinary/extended正向与长路径/中文空格、UNC/device/ADS/dot/junction/短名别名或另一文件/同hash不同fileID负向、actualParent/Owner/DACL、filesystem namespace race。源码闭合不等OS正向或TOCTOU原子安全；独立installed build的真实provenance、publisher/resource资格与三OS仍未建立，不能以Python参数自授安装。

## RV70-P02：首次窗口修复支持与新增阻断分开

285–310保持_transfer签名。291在event前分配overlap/buffer；298记录original_pipe；301–302准备原function/arguments；305 **OS contact前**may_reference=True。306–307从同原调用观察result及last-error。308–310只有实际false/non997才能按明确原调用拒绝释放；328–329在首次观察已记录后被打断时复用这两个**实际已记录**事实，不凭异常/无返回认未受理。未知/accepted路径330–342先invalid，保同局部原pipe/event/overlap/buffer、CancelIoEx同原request、原event+GetOverlappedResult完成检查，不重交ReadFile/WriteFile。

364–373不把invalid-handle6/invalid-argument87/incomplete996或Internal STATUS_PENDING认完成。成功结果或其它已完原kernel状态/原event组合才允许退出局部等待；取消返回、timeout、EOF、PID消失都未直接替代终态。343–351对inner body再次观察异常延后，352–362正常完成清理后保原异常优先/附后续清理note。未知甚至未确认曾提交且无event终态时可能保持等待，这是安全保留意图，不宣liveness或自然退出。

这些改动支持原RV70首次提交受理但pending尚未记录的精确窗口已修；但引用仍全部局部，inner try之外仍可再次抛异常。因此整体P02不能据该静态修订判安全关闭，新的精确条件如下。

# RV71-P01：清理循环的再次中断仍可逃逸原I/O所有权

P2 / Backend / SOURCE_STATIC / OPEN。不是Win32运行复现。固定普通源：G:/开发测试/Codex/VideoCreatorImplementation/Backend/NativeClientCorrection-B34/StaticRevision/SourceCopies/services/engine/src/video_creator/infrastructure/windows_authority_pipe.py，21730B，SHA256 bebb6a0ef7e3763436380489e845cd53215ebe4d4fb839bdbe6cc63d41d6cc13。

B34的305前置may_reference确实修复RV70的首次调用受理未记录窗口；但原I/O强引用仍仅保存在_transfer局部变量291/296/298/302。330–351的while只有336–351内try/except捕获再次异常，335的循环条件及回跳不在这个保护体内。

最小静态触发：真实原I/O已受理或受理未知；首次deadline/异常进入finally，completed仍False；再次KeyboardInterrupt/SystemExit在335循环回跳等内层try外位置被交付。新异常可直接离开finally、覆盖原异常，函数栈的overlap/buffer/arguments等引用随解栈释放。即使event未被CloseHandle也只留下一个OS handle，并不保存这块Python内存；尚无同原调用真实完成证明，因此不能认为保留了原缓冲区。

独立纯静态核：对固定文本只ast.parse/compile生成未执行code object并用dis读取异常表，没有exec/eval/import/call产品。RV71StaticFacts.json记录CPython3.13的335回跳offset1872和2856为JUMP_BACKWARD、protected_by=[]；后者处于异常路径展开的finally拷贝。外围清理异常表仅做栈清理/传播，不重进此等待循环。没有真实信号/线程/OS失败观察。

关闭条件：原I/O所有权需在可能接触OS前由不随该函数异常解栈失去的保守持有者固定；异常/再次中断/观察失败不能丢原pipe/event/overlap/buffer及同调用未受理/完成事实，未证明完成就保UNKNOWN，不重发ReadFile/WriteFile、不替HANDLE、不用event/PID消失推终态。可以由原owner选择具体最小结构，但不能仅增加另一个局部try循环就声称任意再次中断安全。原异常须在真实终态后按契约作为主异常交付。

后继Test在固定新源上验证：已受理未观察异常→进入取消等待→在循环边界/异常handler边界再次中断，原对象外部持有且未完成前未释放；同操作实际完成后再清理/重抛；提交前/明确未受理及正常pending分开。机制注入不代真实Win32完成。当前不据B34静态0批准危险真实Python故障注入或完整运行资格。


## 原证据与权限边界

原B34首67bd0a自然1：owner45520/Ruff40576，原唯一FURB188 removeprefix样式提示；原receipt、stdout963B/原hash b4578345a914851ab28ad1d64d96033101457adc2f1e403a227f41f970e364f8、stderr0和原候选保持。StaticRevision8a2e3a自然0：owner37884/Ruff27604，同一单源ruff check，actual/publicwait0、communicate EOF/streamsclosed、61copies/54AST、beforeafterdrift[]/stickyfalse/exception[]；physicalchild/Jobproven=false。最终stdout19B的SHA82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18、stderr0按各receipt独立核相同字节。它们只证明静态lint，不是OS/runtime。

其余60源没改变，原wholeframe期限/强fullmap/原对象is/sessionepoch/不可逆invalid/独立build与parent条件/Worker无management/sessionguard仅localwriter/原policy、rights、floor、lease/fence、budgetunknown、请求hash/默认factory继续保留。当前wire not_ready依旧零InstalledProductionEvidence；未来qualified issuer只有Protocol声明、当前grammar不能越过资格阻断。实际CLI serve/MCP/Worker trusted全启动/ready和清理、资格store/ABI/license/rights/真实Owner/vault、POSIX等价guardian尚待另门槛。不把永久503、Rust/native另批六期限case或I50正常interop冒本B34重复中断验证。

后继具体顺序：Backend修RV71-P01并固定新的单源/diff/具体所有权存储与释放条件；Review再有限静态复审；Test于固定新源验证真实original operation的首次accepted-unobserved、循环/handler边界再次中断、同原buffer外部强持有直到真实completion、原异常优先和原HANDLE/无重复提交；正常/明确拒绝/取消竞态/结果API错误分列。机制注入不替实际Win32 completion，不能复用本版本普通局部引用作无限安全资格。未关闭运行finding或RuntimeBinding；完整R1三OS独验后连续R2、原失败、RES13拒绝及发布/收费授权边界保持。

最终状态：RV70-P01 CLOSED_SOURCE_STATIC；RV70-P02 PARTIAL_SOURCE_STATIC，新增RV71-P01 P2/OPEN/Backend。全部本轮工具实际终态、必要读者释放；无产品/Test/OS/DB/native/秘密/网络/费用/安装。
