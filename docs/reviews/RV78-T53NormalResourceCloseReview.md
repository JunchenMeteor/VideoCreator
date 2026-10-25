# RV78 — T53 N01 实际正常关闭有限评审

结论：**SUPPORTED_LIMITED_RUNTIME_NORMAL_CLOSE**。固定 N01 的真实消费者、两个原 HANDLE 的正常关闭、同一原连接再次关闭以及原主子进程终态获得有限支持；本片没有新 P1/P2。其它 16 个 T52 单元及受理未知、重复中断、句柄复用故障均未执行。此结论不关闭这些故障边界，不授安装、Owner、产品、三 OS、R1 或 R2 资格。

## 固定输入与身份

只读普通根 `G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T53NormalResourceCloseExecution` 的 24 件源码/原收据/字节日志，以及索引明确引用的三个 B37 历史普通源码和原快照。加治理入口共 35 条路径记录、33 个唯一路径，实际 SHA/大小均匹配，末核 `changes=[]`；未重新扫描或散列全部 1,333 个运行时/资源输入。完整 pins 见同任务过程的 `RV78InputPinsFinal.json`。

正式身份：

| 固定文件 | SHA-256 |
| --- | --- |
| T53ExecutionHandoff.md | bfa982ef429a1142115ec9501278d1df85bc651d1843ded17422a22e13820054 |
| T53ExecutionHandoff.json | c3ac8174cad4857b52a0c8306f337c03628f4c2843667416904de0d7979b820b |
| T53ExecutionOrdinaryManifest.json | 0ed4a4c03412559807fd177fc632d4198dd3d997f86818e07b97fc6426325170 |
| T53ExecutionFinalToolTerminal.json | 2d1c78cf1d78d43dac039e9ceca5d8cbb61950c96d371fc3c485e9d6b4a9368c |
| PeerNormalCloseT53.py | 336811c4035a1daeeb998007e17c0d7c7e7d0ab32ddaf8b80d2c5b96620dac55 |
| RunNormalT53.ps1 | e038769cefc69852383b353624420992eaaa8f7259c4eb80e41c14e5c8ccf85d |
| B37 SourceSnapshot.json | 0e58fcd24620e39f6f5d8f80f6868f0ecf65560a5e4954843a8ed72e4789a494 |
| B37 windows_authority_pipe.py | 491c1e0d3d8472b7dc87ab06740f5f3ec28e3f78509e97882cbe84c75946aecd |

`T53InputIndex.json` 的 source_root 指向 B37/SourceCopies，三个实际消费源码与 B37 snapshot 声明一致。NativeReport.scope 中旧“B31 factory”文字是继承标签，不能替代本片实际 B37 身份。

## 原真实证据与调用链

- JUnit 原字节仅 **1 testcase、0 failure/error/skip**。Peer 的 4 项断言及 runner 的 3 项外层检查是同一 N01 内检查，不是 7 个测试。ParentStdout 原 JSON 等于 NativeReport，PythonStdout 原 JSON 等于 CaseReceipt；native 内嵌 python_report 也相等。OsCalls.jsonl 等于原 CaseReceipt 两调用，独立解析核对 20 项均成立。
- PeerNormalCloseT53.py:114–157 锁定原 connection/transport 和两个 HANDLE，记录器保存并调用原 kernel.CloseHandle，再立即真实 GetHandleInformation，返回原 BOOL；没有合成返回值或另造清理对象。原 pipe **736** 与 process **752** 关闭前 BOOL=1；各仅一次实际 CloseHandle，BOOL=1、last_error=0；关闭后原 HANDLE 查询均 BOOL=0/error=6。
- Peer:160–183 在原连接锁内调用 `connection.close()`，首次后的两个 owner 字段均 None，原 owner 的 I/O 与 close 强持有记录均为空；同一原连接第二次 close 后仍仅 2 次 OS 接触。B37 held_authority.py:284–288 的第二次 close 仍会进入同一 transport.close；B37 windows_authority_pipe.py:450–498 在原字段 None 且无 retained close 时返回，不再次接触 OS。这里支持实际第二次连接关闭及其真实底层路径，不代表故障未知、同时并发或复用已测。
- Peer:187–200 finally 中先关闭 authority，再恢复原 CloseHandle，再关闭 build。CaseReceipt.method_calls 包含该真实 finally 路径，最终两调用数仍为 2、cleanup_errors=[]。build 的原资源关闭不属于这两个 pipe/process HANDLE 的计数。
- 原 guardian PID **31772**、creation FILETIME **134360493983819203** 与连接内 server PID/parent/creation 相同；Python PID **36212**、creation **134360494036130106**。CommandReceipt 实际 entry/native exit=0，NativeReport Python actual exit=0、natural terminal=true、Job active zero=true，主子 stdout/stderr 各实际字节 EOF；forced=false、deadline_sticky=false、errors=[]。外层原 Process 持有到终态并完成原字节泵，不靠后来 PID 消失替换退出证据。exec 未提供外层 pwsh wrapper creation，报告不补造该身份。

## 资源表与资格边界

Peer:104–113 实际 `dataclasses.asdict(facts.files)` 与完整 expected_files 按 relative_path 排序后逐值比较；随后写入完整表的 canonical SHA。独立复算固定预期表的 1,333 个唯一路径及摘要 `c5054a55f87d680ffc1fc7cafc9d1aa797f14684f7a304e47a8497967bbe56e6`，与原 FullMapReceipt 两摘要相同。

普通件没有单独保存实际 facts.files 完整正文，本评审不能重新逐行比对该实际表或声称已重新核了实体资源；支持来自固定消费者的完整比较源码、原断言到达、收据摘要和原字节输出的一致性。配置表/透明开发 fixture 不是正式安装或许可资格。

原 **server_session_end=authority_io_failed** 完整保留。主子自然 0、OS 资源关闭成功不把这项变成 graceful protocol 完成。qualification=not_ready、qualification_issuer=None、evidence_constructors=[]，未执行真实 Owner/凭证/发布/Worker/媒体/ASR/模型/费用；不能凭本 N01 授 RuntimeBinding 或全产品 Gate。

## 保留失败与后续

原执行 `232535/session56139 → 827eda` 自然 0，原 finalizer `940dbe` 和 final hash `523b49` 自然 0；没有重放。评审自有解析 `3d01e6` 自然 1 是误用 EOF 字段大小写的 KeyError，原脚本和错误记录保留；按原 `parent_*_byte_EOF`/`outcome` 字段定向修订后 `37efb8` 自然 0。这不改变产品或 T53 原运行结果。

本片剩余真实 fault 条件交独立 Test 后续批：pre-contact/accepted unknown、解栈强持有、重复中断、原对象与数值 HANDLE 复用、独立取消完成/未完成。先保原协议与拒绝规则；不借 N01 正向关闭这些安全条件。安装与三 OS、真实作品多模态、完整 R1 后连续 R2 的总目标保持。

评审仅读取固定证据和源、做标准库解析/散列，产品/Test/native/OS/DB/网络/费用/凭证调用为 0；输入读者已释放，正式交接后结束本轮。
