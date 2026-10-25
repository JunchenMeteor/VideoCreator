# RV70 — B31 Windows私有客户端与安装工厂有限源码评审

结论：**SOURCE_REVIEW_FINAL；两项P2/OPEN，归Backend**。B31这份固定候选存在路径表示误拒与异步提交异常所有权窗口，不能仅据Ruff0进入已通过实际通道/资源资格判断。本轮只读固定普通字节和历史静态证据；没有运行产品、Test、Win32、NamedPipe、SQL、native EXE、ASR、模型、网络、凭证或收费，不批准RuntimeBinding。

## 固定范围与身份

正式根：`G:/开发测试/Codex/VideoCreatorImplementation/Backend/HeldResourceConsumer-B31/`；完整61普通源位于其`FinalStatic/SourceCopies/`，全部与索引逐字节hash/size匹配。五文件改变，其余56与索引所列before SHA相同；对原两既有文件额外读取固定B32正文并生成实际diff，改变仅optional session guard协议/参数/属性和_guard两行调用，没有改原权限、floor、预算、Operation未知、lease/fence、policy、rights、请求hash或SQL/DTO。源码保护不代运行行为验证。

|输入|完整SHA256|
|---|---|
|B31Handoff.md|ee5e6e1b57eac92e1adfbcf658f680d702f37e4ce0bafd4d48039f466ee20dda|
|B31Interfaces.md|ead01aebca0096148a3705f56b1daa6afa300da33f02a766e8922d8e5a4910f0|
|FinalStatic/SourceSnapshot.json|2989e27e87df66ba3e2d1fcece8bbf9c6361957ff5e605cd32547509907965eb|
|application/native_installation.py|1458d3bb1781fa53df598e69dff3ec0b54273c38fff6aad9c5c0bdb64cf95509|
|application/owner_services.py|26b2bb6c49570c9643fd57c01ef3109da6107240d9c6c59d67e9f31f48d9c9ee|
|application/production_admissions.py|806cea608ed50560c5be1553cf897121ce741155375e69995d72ef34a90da79d|
|infrastructure/held_authority.py|7cd4f20812b2a6e4bba6207cb119bd16712aa8a44bbbb8be52e7e4c01781d410|
|infrastructure/windows_authority_pipe.py|21c202319fd5c6c8ed3306356259b2dfac016aba1c548c812a8e073216f7b355|
|InputCopies/BackendChannelContract.md|1862fda36061d411de3d5e115e851b1149aeb208a6e4ed7fb4c03d5678e0a7cc|
|InputCopies/0032-held-resource-authority-channel.md|71f51cce4ea63dd34380486ded9ec684eb5b7931e598ba66ca109390f0800126|
|InputCopies/src-resource_authority.rs|6602f597bf8b196e822af1289a824689201f329d4a66c400d1a69605643953f0|

过程：`G:/开发测试/Codex/VideoCreatorImplementation/Review/NativeClient-RV70/`。Snapshot/InputAfter共80个必要路径、mismatches=[]，没有复制runtime或扫描环境。曾有bd3669/93524c/4642b7显示截断，结论只依据完整定向源码片及本地stdlib实际解析保存的有限证据，不声称截断显示已全文消费。5106bf外层exit0中自身PowerShell数组拼接产生一次Get-Content路径错误；122dcd仅stdlib纠正两条原固定文件读取，原错误作为评审过程事实保留，不是产品失败或产品重跑。

## 独立发现

状态：SOURCE_STATIC / OPEN。只读固定B31和其I49普通源；未运行Win32/pipe/产品/Test。两个发现均归Backend，原源停留在本次固定身份。

## RV70-P01 / P2：同一宿主的普通与extended-length路径被字符串比较拒绝

固定源：`G:/开发测试/Codex/VideoCreatorImplementation/Backend/HeldResourceConsumer-B31/FinalStatic/SourceCopies/services/engine/src/video_creator/infrastructure/windows_authority_pipe.py`，SHA256 `21c202319fd5c6c8ed3306356259b2dfac016aba1c548c812a8e073216f7b355`。

调用链：`_Win32.process_identity` 93–97直接返回`QueryFullProcessImageNameW(...,0,...)`的路径；`WindowsAuthorityPipe.assert_peer` 220–226只用`os.path.normcase`比较这个字符串与locator.image及独立build.path。固定I49普通`InputCopies/src-resource_authority.rs` SHA256 `6602f597bf8b196e822af1289a824689201f329d4a66c400d1a69605643953f0`，52–56先Query再`PathBuf.canonicalize()`，将canonical image写入server身份。

最小静态条件：实际Query返回`G:\Native\host.exe`，同文件的locator.image为`\\?\G:\Native\host.exe`。`normcase`只处理大小写/分隔符，保留`\\?\`，224比较不相等，即使PID/creation/SID、原独立protected build、SHA全正确也抛installation_peer_denied403。这不是实际Python通道已运行失败，也没有读取I50改动来倒填旧源。

修复条件：双方约定可验证的同文件路径表示/对象身份，以真实原process HANDLE和独立原held build为根，不仅去前缀就接受任意别名。保完整PID/creation/SID/parent/build SHA及Owner保护条件。后继Test需真实普通drive与extended同文件正向、不同文件/别名或junction负向、中文空格与长路径边界。

## RV70-P02 / P2：accepted但尚未记录的异步I/O可能在异常路径提前释放buffer/event

同固定源230–281。242初始`pending=False`，245调用ReadFile/WriteFile，249才记录`pending=True`，263只有pending才进入取消并等真实完成；281随后CloseHandle(event)。

最小静态条件：原ReadFile/WriteFile已向OS提交异步操作，但call返回观察前或245–249间发生KeyboardInterrupt/SystemExit/异常。259捕获并标invalid，finally仍pending=False，跳过取消完成循环，关闭event并让overlap/buffer离开作用域。连接无效并不证明OS已不再引用该内存。正常已观察ERROR_IO_PENDING后取消分支保原对象，不能覆盖这个尚未记录的提交窗口。

修复条件：在可能接触OS前建立保守的提交所有权/未知状态；仅有同调用明确未受理事实才释放，accepted或受理未知均保留原pipe/overlap/buffer/event，核真实完成，不重交或换对象。后继Test最小覆盖提交前失败、明确未受理、已受理但返回观察抛异常、正常pending、取消竞态/真实完成后原异常重抛。未证明实际OS可达次数/内存损坏。


P01补充：若为了匹配Rust而直接把installed_native_image改为extended路径，固定`owner_identity.py`100–103原本拒绝`str(path).startswith('\\\\')`，会在build检查阶段先得到owner_directory_denied403。因此归属修复应协调真实local文件身份和Owner保护，而不能用取消UNC/link/Owner检查或任意前缀裁剪放宽权限。这里只是原源码条件推导，未实际运行此输入。

P02补充：原pending正常路径会先置invalid，保原pipe/overlap/buffer/event，在CancelIoEx后继续Wait/GetOverlappedResult；这部分源码意图得到支持，但不能覆盖调用返回观察前的受理UNKNOWN。后继需按原对象和实际完成事实验证，不能用call返回Bool、CancelIoEx成功、事件关闭或不存在PID冒真实I/O终态。GetOverlappedResult/Wait/Cancel错误分类与再次中断仍属于实际Win32异常矩阵待验证，不据本轮语法判已安全运行。

## 已支持的有限源链

1. Win32声明使用HANDLE/指针宽度、DWORD/BBOOL及显式restype/argtypes；OVERLAPPED含pointer-sized Internal/InternalHigh、DWORDoffset、HANDLEevent；FILETIME拼接原64位creation。静态没有据这些声明发现独立ABI类型误配，兼容性仍未运行。CreateFileW开放child自己连接，retained OpenProcess，GetNamedPipeServerProcessId+os.getppid严格原父，actualcreation/SID/当前childSID/image与独立build三重约束，失败不fallback ancestor或JSON PID。
2. 独立build入口要求外部可信installed记录提供path/SHA，不从locator回填；Owner/DACL/link及实际file/dir identity，CreateFileW只share read，原heldHANDLE分段wholehash/size前后核。它不建立installed记录来源/签名或资源资格；记录的真正独立受保护provenance仍需Integration准入，不能一个Python参数就自授安装。
3. held_authority.py54–77严格UTF8/duplicate/nonfinite及exponent overflow；22–25 exactfields，35–37拒bool伪int；93–125完整非空固定map、重复path拒、engine和indexed两个非空分区、oversize启动前拒不截断。188–227逐reply/session/seq/contextSHA/status/code/资格/fullmap比对。当前I49只not_ready；未知或外国409经过_exchange异常清全强身份，不自动reconnect/复活ID。
4. 原对象语义：254–269强引用HeldFactsObservation、epoch和`is`；同值拷贝/别session不发RPC即409；271–274用原ID远端assert；_native adapter78–94 Evidence→原facts强引用，同original对象/本地epoch及远端current复核。不会把序列化事实或等值dataclass当guard。
5. deadline：startup传原20秒deadline，初次bind取min(startup, now+10)；每_exchange共用10秒deadline覆盖全部read/write并在peer复核后244–245再次检查。与原RV68 Rust不同，B31不会从成功_exchange返回超期结果。本轮不关闭RV68-P01、不宣同步OS/hash工作可被硬限时，且P02异常清理窗口仍阻断安全资格。
6. 短writer：ProductionAdmissions.current_guard150–196在writer前实际authority.observe/assert；_guard198–208加入optional guard，先原object/thread/issuer再local check后原revision/floor。NativeInstallationAuthority96–103及OwnedAuthorityConnection173–186/276–282用nonblocking RLock，busy503；WindowsAuthorityPipe203–210仅原process零等待/pipe本地poll/build closed，没有RPC、hash、token检查。current外部关闭/异常被观察后连接不可逆invalid；不承诺故障观察前已commit可以回撤。
7. 实际工厂151–181校同instance/role、Worker拒management=True、execution_registration三SHA，调用同Engine/Bundle/Owner的assemble_owner_services。原owner_services61–85保bundle.engine is engine、Owner bootstrap/current、仅management构造registry并resolve认证secret、执行注册完整exactdict/owner/principal一致。Worker仍构造OwnerSecretStore服务对象，但不调用resolve/create或加载管理secret；不能把import/构造对象说成vault读取。默认guard=None保持原行为。
8. native_installation50–61在facts.not_ready时抛production_installation_not_ready503，**零InstalledProductionEvidence**，即使提供Protocol issuer也不能越过当前wire199–202的not_ready-only资格边界。futureissuer issue/assert仅声明，真实资格store/report/reference/role/完整ABI/license/workflow/driver/revocation和来源尚未建立。CLI serve/mcp-stdio/Worker没有自动装配此factory；来源、装配在ready前、Worker独立存活会话、清理先authority后build均仍需实际接线验证。不能以永久503作为完成。

## 原静态证据与后继独立测试

原StaticReceipt.json SHA8ef24b05588f8968763a992759de662a17ae73345a816f7c9cfd01075fd24426：owner29508/Ruff41672，原80b822自然1，I001/SIM102/BLE001三项原lint和Ruff.stdout2580B保留；无product import。FinalStatic/StaticReceipt.json SHA3596a7b75e346e390757e710a328175c06a3ff919f100e45ff5d71b01156cfe4：owner8560/Ruff35120，b97dfe自然0/publicwait0，communicate EOF/streamsclosed，61copies/54AST、drift[]/stickyfalse/exception[]，physical child/Job未证明。原intermediate1d53c5为不同输入，仅其局部静态结果，不重写原红。原最终raw stdout19B“All checks passed!”/stderr0按receipt核相同hash；这是lint，不是产品、pipe或Owner运行。

必要后继：Backend固定P01/P02新source/diff后另源码复审；Test独立在真实registered native→Python child/原process handle/Job/Build/file原件链验证正向、wrongPID/creation/SID/image/parent/instance/role、EOF/半帧/重复/超大/seq/fullmap、复制对象/foreignID、超时sticky、accepted-unobserved异常及Cancel竞态的真实completion、writer忙/连接失效。不要硬call、换假HANDLE、偷parentproxy、重start或close-event洗终态。true installed record和保护链、厂商资源许可/ABI/完整资格、真实API/MCP/Worker ready/cleanup以及Linux/macOS等价guardian仍另门槛。本轮不消费I50/B31未来fix或实际双端结果，不继承Rust own probe0、Ruff0为Python事实运行。完整R1三OS独验→连续R2目标、原失败、RES13拒绝与生产收费/发布授权边界保持。

状态：RV70-P01/P02 SOURCE_STATIC/P2/OPEN；没有OS复现结论、RuntimeBinding、Owner真人认证、实际资格/ASR精度/完整生产/R1/R2通过结论。全部必要读者终态并释放，产品/Test/SQL/native/网络/模型/secret/费用/安装0。
