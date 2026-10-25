# RV81：T55 八个 RetainedHandleClose 边界独立评审

结论：**LIMITED_RUNTIME_CLOSE_BOUNDARIES_SUPPORTED**。固定 B37 原实现的 C02–C05 × pipe/process 八个真实边界获得本批证据支持；未发现新增生产 P1/P2。该结论不关闭全部句柄故障、不授 RuntimeBinding、Owner、安装或产品 Gate。RV74 的源级修复获得这八个具体窗口的运行支持，不能外推未执行窗口。

## 固定身份与独立操作

只读 T55 正式普通副本及七份必要固定源。183 份执行普通副本与声明的原字节 size/SHA 均匹配；初始195个路径加七源，共202个唯一输入，末核全部不变。完整列表见 [RV81Snapshot.json](G:/开发测试/Codex/VideoCreatorImplementation/Review/RetainedCloseBoundaries-RV81/RV81Snapshot.json) 与 [RV81InputAfter.json](G:/开发测试/Codex/VideoCreatorImplementation/Review/RetainedCloseBoundaries-RV81/RV81InputAfter.json)。未重新散列1333个物理运行环境文件、未复制环境；没有产品/Test/native/DB/模型/网络执行，没有密钥读取、费用或实现/标准修改。

正式 T55 Handoff MD SHA `047e0df0ff2e01f8719398ba11ee25f2c840211da7377952ad675bbbaab2c8ce`，JSON SHA `b55c2cf355002e7a549b89c18b2b212a0a283bfcc1000a87910964bb646012ed`。普通 Manifest SHA `963297b2db0104626697e475be7bbcea230ae4737a78e36b2c6cee224ab2728c`；完整原路径→普通路径映射已保存在自身过程目录。

真正被调用的 Windows 源是 B37 `windows_authority_pipe.py`，SHA `491c1e0d3d8472b7dc87ab06740f5f3ec28e3f78509e97882cbe84c75946aecd`。Peer 固定 SHA `c045b82387100a1fb98ed17a7af2f5fbde9cc3bc0243bc37e2108b6e0aedb036`；Runner SHA `2e0a0074501fe08eaae6b07df2cc2849e3f0448d171699f42dced908bf584af4`；guardian Rust SHA `825a7dee7b55a878fe2968a578e2544fab7fb61f3a74d3ec4d5d167c263ab0fc`，原编译 EXE SHA `f3ea52b9190e94b87daf0807d5106fc3a27bfa347f42f2ec2f7bf5267478b21c`。原报告的 B31 scope 文本是历史标签，不改变实际 B37 源身份；development/not_ready/qualification=false 保留。

## 真实运行证据

原执行 session3410 / terminal `4bf44b` 自然0，无重启/重放/强制结束。原八个 case 收据均自然0；聚合标准 XML 恰好8个命名 testcase、0fail/error/skip。64个 peer 检查及24个 outer 检查不是88个测试。批收据24个引用逐个与普通字节 size/SHA 一致。

每项 guardian 与 Python 的原 PID/creation FILETIME、Original Process 保持、Job active0、实际退出0均跨原收据核对；四流原始字节完整，parent/Python stdout 的完整 JSON 与原 NativeReport/CaseReceipt 及嵌套 python_report 逐类型逐值相同，两 stderr 为原空字节。outer PowerShell 只有原工具 chunks，没有独立 outer 字节文件，不补造其 EOF。原 byteEOF 与 natural terminal 来自 guardian/Python 原观察，不由 written-started 或 pytest 汇总代替。

| 实际 case | Guardian PID / creation FILETIME | Python PID / creation FILETIME | 目标 / 另一运输句柄 OS close数 | 收尾事实 | 原 server_session_end |
|---|---|---|---|---|---|
| C02.pipe | 12120 / 134360552605765771 | 34280 / 134360552654456660 | 0 / 1 | 保留未知 | authority_io_failed |
| C02.process | 35752 / 134360552832040941 | 33420 / 134360552880244998 | 0 / 1 | 保留未知 | authority_peer_terminal |
| C03.pipe | 29624 / 134360553063626512 | 11104 / 134360553111485641 | 1 / 1 | 保留未知 | authority_io_failed |
| C03.process | 32904 / 134360553298592465 | 20100 / 134360553346409005 | 1 / 1 | 保留未知 | authority_io_failed |
| C04.pipe | 28296 / 134360553547331485 | 17612 / 134360553595261483 | 1 / 1 | 确认后元数据完成 | authority_peer_terminal |
| C04.process | 36740 / 134360553774954369 | 36748 / 134360553822782933 | 1 / 1 | 确认后元数据完成 | authority_peer_terminal |
| C05.pipe | 11316 / 134360554006036217 | 23416 / 134360554053833760 | 1 / 1 | 确认后元数据完成 | authority_io_failed |
| C05.process | 37468 / 134360554243538180 | 36024 / 134360554291694836 | 1 / 1 | 确认后元数据完成 | authority_io_failed |

计数只覆盖实际 pipe/process 运输句柄 CloseHandle recorder，不能声称整进程全部 OS 调用为0或1。C02 的 outer 检查仍有旧“两次 real close”显示名，但实际原 journal 为目标0、另一句柄1，评审以该事实为准。五个 `authority_io_failed`、三个 `authority_peer_terminal` 均原样保留，natural0 不把它们改称正常协议关闭。

## 原方法与异常边界

[B37 原方法](G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T55CloseBoundarySourceStage/Source03-windows_authority_pipe.py:450) 以 global 强 holder、原 owner/role/HANDLE/function 保持联系；463写 contacted，465调用真正原 API，466才写 confirmed，478赋None，479删除原 holder。原 `close` 的 pipe 主异常与 process finally 保持首异常，重复进入未知路径仍抛同一原异常。Peer 在原 compiled frame/原 RLock/原线程上注入，不创建影子 close；实际 wrapper 将真正 CloseHandle BOOL 和随后 GetHandleInformation/error6 记录进 journal。

- **C02（465原调用前）**：contacted=true/confirmed=false，目标未调用 OS；原句柄实际仍有效，原 holder/owner/error 在异常解栈、两次原 resume 与最后 authority.close 后均保留，重入 OS delta0。
- **C03（原 CloseHandle 成功返回后、466确认前）**：目标实际BOOL1，紧接 GetHandleInformation BOOL0/error6；随后异常保留原 holder 与未确认状态、同一错误。两次原 resume 和最终收尾不再次数值 close。`C03_old_numeric_HANDLE_requery_or_reclose=false` 字段本身是固定写入值；支持来自实际 journal、完整 Peer 分支和原方法调用链，不能把该字段冒充全局 OS 查询监视器。
- **C04（478确认后赋None前）**：目标实际 close一次、confirmed=true、字段仍非空；原 resume 完成赋None/删holder，最终元数据已释放，OS无新增。
- **C05（479赋None后删holder前）**：目标实际 close一次、confirmed=true且字段已None；原 resume 只删除原 holder，重复调用不再次close。

[Peer](G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T55CloseBoundarySourceStage/Source21-PeerCloseBoundariesT55.py:179) 保留原 raised/caught exception identity、真实 RLock/thread、原 owner/function 身份，并在第二次危险数字 close 前拒绝；[Runner](G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T55CloseBoundarySourceStage/Source25-RunCloseBoundariesT55.ps1:53) 持原 Process/creation、读取真实字节流、自然等候并保留超时粘性；[guardian](G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T55CloseBoundarySourceStage/Source13-python_channel_host.rs:1) 的实际 child/Job/reader路径保存原 raw 后再解析，允许有限事实观察自然0同时保留 server error。C02/C03 的 unknown custody 到自然解释器 teardown 仍存在；这不是产品已确认释放。最终 build/进程自然结束不清洗未知 close 状态，也不证明 actual Owner shutdown。

## 完整存储映射

八份 ActualFullMap 与八份 ExpectedFullMap 各1333行，逐项比较 relative_path、整数bytes、SHA字符串及类型；再与 T55InputIndex 的完整 expected_files 和 source_records→relative 映射比较，零差异、无重复路径。16份原 map 字节均 SHA `a90d2047b0e54930ad038f9b4cf3b9e5a2df33d07322f2cdc38ad3251437e070`；原 canonical expected-map SHA `0eee2dc7b411819a571dbadbfa86bd0137719d1abdb17b49254d2e0253c82e74`。这证明保存的完整数组一致，不只 len 或布尔一致；安装、许可、真实发行 authority 仍不由保存映射自动成立。八份原 sourceafter 为1333行且变化[]，自身末核只核202个固定输入。

## 未测与原失败保留

本批只新增上述8窗口。目录17项中历史N01/C01.pipe/C01.process加本批共11项；I01、I02、R01、R02.pipe、R02.process、E01六项仍NOTRUN。未验证 pending I/O 在异常下的所有生命周期、Owner真人操作、完整产品/媒体/ASR、全部资格、三OS、R1或R2。真实完整R1验收后连续R2目标不变。

评审自己的首纯解析 `61c634/1` 误强制八项都为 authority_io_failed，原三不同会话导致解析检查红；不是产品/Test红。原脚本和事实保存为 CheckRuntimeFactsOriginal.py/RV81RuntimeFactsOriginal.json，纠正后的纯解析 `0892a2/0` 只读取原字节；原Test、原失败、原server end均未改。[OriginalParserFailure.json](G:/开发测试/Codex/VideoCreatorImplementation/Review/RetainedCloseBoundaries-RV81/OriginalParserFailure.json) 记录完整缘由。

末有限解析 `efa588/0` 核24引用/聚合8/XML/202输入，全部自然终态。全部输入 reader 已释放，不持生产冻结、不等待后继资格。结论仅上述有限运行支持，独立Acceptance及未执行边界继续开放。
