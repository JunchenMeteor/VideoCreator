# RV68 — I49 持有资源通道有限独立评审

结论为 **SOURCE_AND_OWNER_EVIDENCE_REVIEW_FINAL**。固定源码包含真实 Windows NamedPipe / 原 process HANDLE / Job / ResourcePins 接缝，原两会话 probe 的有限结果有源码和原收据支持。新发现 **RV68-P01 / P2 / Integration / OPEN**：同步 I/O 与晚观察完成路径未一致执行已声明的绝对截止时间。该问题是静态源码结论，未进行 OS 复现。**不批准 RuntimeBinding、Python 接通、InstalledProductionEvidence、资源安装资格或完整 Gate/R1/R2。**

## 固定身份和职责

只读 I49 正式交接/索引、38 份索引普通副本及规则/任务卡，共 46 个必要路径；前后 hash/size 无差异。没有读取 B31 当前源、重新编译、运行 probe/产品/测试、扫描 runtime、安装、读取秘密或产生费用。准确输入及前后身份见自身 `RV68InputBefore.json` / `RV68InputAfter.json` / `RV68Snapshot.json`。本报告只写评审白名单。

五项本轮生产改动的普通副本位于 `G:/开发测试/Codex/VideoCreatorImplementation/Integration/HeldResourceChannel-I49/Ordinary/SourceAfter/`：

| 文件 | SHA-256 |
| --- | --- |
| Cargo.toml | 2a8c97e26a54f8b2ecee2be78462d69abf177842823f8bb354abb5b8de1ab30c |
| src-lib.rs | fcc04761bffc3b340b47d5f9bfd3b484ab14686d0c55687d192abb1f68b9cd80 |
| src-platform.rs | 05dffb23306fc998d21bfdc1d1cb22429bd7f385e4e8818d64daaffacbd63513 |
| src-resource_pins.rs | 1a49a4901e34c1c62ae1c2d48d4f014c7f34cceff3a9819bae49466f90cf78cc |
| src-resource_authority.rs | 6602f597bf8b196e822af1289a824689201f329d4a66c400d1a69605643953f0 |

必要支持源码 load_policy/supervisor/native carrier 和锁文件均来自同一普通索引，未以当前工作树补历史身份。Freeze 对没有 before 样本的支持源码使用了 `changed=true` 并明确有“new or unchanged”注释；本报告不据此声称额外生产改动数量。

## RV68-P01 — 同步与晚完成路径漏绝对 deadline（P2，Integration，OPEN）

固定源码：`G:/开发测试/Codex/VideoCreatorImplementation/Integration/HeldResourceChannel-I49/Ordinary/SourceAfter/src-resource_authority.rs`（上表完整 SHA）。契约普通副本 `G:/开发测试/Codex/VideoCreatorImplementation/Integration/HeldResourceChannel-I49/Ordinary/BackendChannelContract.md`，SHA `1862fda36061d411de3d5e115e851b1149aeb208a6e4ed7fb4c03d5678e0a7cc`，第 9 行声明启动 20 秒、逐帧 I/O 10 秒，超时使会话失效但保留原 operation/child/Job/guard。

调用链：`calls:168` → `receive:109` → `bytes:102–107`。只有 ReadFile/WriteFile 返回 `ERROR_IO_PENDING` 才进入 `complete:86–95`；同步成功直接推进 offset，没有检查该绝对 deadline。`connect:99–100` 同样直接接受同步成功或已连接。`complete:90` 先返回已完成结果，第 92 行才把已过 deadline 锁存为失败。

最小触发条件：同一帧绝对 deadline 已过（例如分块间发生调度延迟），随后已缓冲字节使 read/write 同步完成；剩余前缀/正文仍可完成并被处理，未形成 `authority_deadline`。另一分支是首次观察某 pending completion 时 deadline 已过，但第 90 行先返回成功。原运行没有这些延迟样本；不能把这个静态反例写成实际 Windows 故障、远程权限绕过或观测 hash 绕过。

修复条件：统一检查同步、pending、connect、前缀/正文和连续分块路径的同一绝对期限；已观察过期不得被晚完成洗成成功。取消 pending I/O 后仍须保留原 OVERLAPPED/event/buffer 至真实终态，不能因此提前释放 child/Job/ResourcePins。独立 Test 需覆盖已过期但立即完成、分块延迟、pending/取消完成和 UNKNOWN 保留；不要修改原 I49 证据或只验证 pending happy path。早报告 `RV68EarlyDeadlineFinding.md` 已交统筹路由，评审未修源码。

## 相干源码支持的机制及边界

- 创建和登记：resource_authority:131–135 通过同一 guard 观察/解析 held child image，然后创建 per-child FIRST_INSTANCE/拒远程/owner+SYSTEM DACL pipe（77–82）；随机 session 和固定上下文不是凭证。143–162 从实际 pipe 查询 client PID，以登记的同一 Arc<Mutex<OwnedProcess>> 检查；platform:167–176 对原 HANDLE 的 PID、creation、原 Job membership 和仍存活逐项拒绝不一致。随后实际 SID/image/hash 必须匹配，calls:167/182 在处理前后重复检查。不是从 JSON PID 重新 OpenProcess 来取得 child 所有权。
- 客户端 resource_authority:217–233 查询实际 server pipe PID、当前 child 的 parent PID，并保留 server process HANDLE；校验 creation/SID/image/hash、每次调用前后复核。**它仍依赖可信 bootstrap 传入 expected locator**，当前没有独立 owner-protected native build trust anchor。环境 JSON/PID/SHA、同 SID、父子关系或这些事实不能自行授予 authority。B31 需实现真正薄客户端/factory 和安装资格来源，不能把 `not_ready` 改成 True 或永远不可用当完工。
- 观察：resource_pins:24–75 持有文件和祖先目录；90–116 从原 Mutex<File> 复核实际 size/hash 并恢复 file position；118–146 使用 private issuer 指针和原借用对象。resource_authority:165–179 保留原 HeldFileObservation 的 session 表，observe 选原 full map，assert 用原对象；foreign/unknown ID 返回 409。序号严格递增，typed serde 请求没有 path/argv/env/subset/generic method；恶意重复字段/超大/残帧等 **实际矩阵未运行**，本轮不把源码声明升级为其运行通过。
- 生命周期：serve:154–158 在断开/错误后销毁该 session 观察 ID，但保留原 guard、process HANDLE 和 Job，直到真实 exit 且原 Job 无后代；UNKNOWN 留在持有循环。AuthorityOwnedChild:190–211 继续持有 guard，PreparedLaunch 接缝还持有同一原 prepared/source_carrier；Drop 请求终止后同样等真实 terminal/空 Job 才结束。注册失败及 post-Create 错误依赖 load_policy:44–53 → platform:37–46 的原 guard 所有权。完整 PreparedLaunch 路径 **只编译、未执行**。
- qualification：resource_authority:124/182 的所有服务端回复固定 `not_ready`，当前源码不构造 InstalledProductionEvidence。reply hashes 只是原 native launch context 引用；probe 的 context 使用试验标签 digest，**不是实际注册/安装 manifest 的资格正证据**。

## 原运行究竟覆盖了什么

覆盖编译原 Plan argv 为 `cargo build --lib --bin channel-probe --offline --locked --target x86_64-pc-windows-msvc --manifest-path .../CompileWorkspace/Library/Cargo.toml`。库入口是真实 copied `src/lib.rs`，non-test source 覆盖 platform/ResourcePins/resource_authority/PreparedLaunch/carrier；依赖 23 包，build scripts/proc macros 可执行。本报告只核归档来源，不运行 Cargo。

原 session88608 → terminal2dea97 / Cargo41112 / creation `2026-10-09T14:34:03.7160403Z`，自然 0、两流 EOF、timeout=false、errors=[]、inputs_after=[]；编译 input Plan 174 项由原 runner 记录，本评审不重新扫描 174 项环境。8 个原 dead-code/unused warnings 保留（含 PreparedLaunch、carrier、launch_prepared_facts_only 未用）。probe EXE 1,404,416 B，SHA `22971a0fbe307881dcd00c0b0e87cd05d7966c274152530824796e7c9ec7298b`；只被动核普通 EXE bytes/hash，没有执行。

实际 owner probe 原 session94976 → terminal104203：root29480 / creation `2026-10-09T14:39:27.1623681Z`，自然 0、两流 EOF、timeout=false、errors=[]、inputs_after=[]；原 actual Plan 31 项，源/工具历史 before/after 由原 runner 保存，本评审未扫描整 runtime。receipt started/ended 分别 `14:39:26.7794758Z` / `14:39:38.7190009Z`。原 UTF-8 ReadToEndAsync 完成后将文本规范化 LF 保存，**没有逐字节 stdout/stderr 原镜像**；Rust ASCII JSON 语义仍可从原归档核对。

| 原会话 | child / creation_filetime | 原结果与界限 |
| --- | --- | --- |
| 1 | 25700 / 134360303676386320 | 自然 0、两 reader 完成、Job 空、拒 1 个实际同 SID 未登记 peer；unknown ID 409；跨会话检查 null/NOT_EXECUTED |
| 2 | 22888 / 134360303753997363 | 自然 0、两 reader 完成、Job 空、拒 1 个实际同 SID 未登记 peer；真正将会话1的 ID 发到会话2并获 409 |

原 stdout 与正式 Handoff.actual_parent_child 完全逐值一致。Probe:34–74 使用真正 OwnedProcess/原 Job、真实 pipe 开启（spoof_open:26–32），正常 child:11–17 调用真实 AuthorityClient；不含 Python 工厂。Probe:19 的 `full_fact_map` 只断言 files.len()==2，并未独立保存/逐项对照 wire 中每个 path/size/hash；身份查询细分原始读数及拒绝具体 code 也没有单独保存，不能扩成完整资源 manifest 的独立逐项验收。

Probe:18 `invalidate()` 实际关闭本地 pipe 后，后续 assert 被本地 `valid=false` 拒绝；**不是远程重连/replay 的证明**。两服务端原 `authority_io_failed` 都保留；这是 EOF 失效路径，未改成 normal RPC success。Probe:39 在持有 guard 时写 payload 被拒；75–76 先复核原 guard、等两 child exit 与 Job 空、释放原 guard 后实际 append 成功。73 的 wrapper Drop 仍调用原 empty Job 的 force，但原 child 的自然 exit/空 Job 在该调用前已核；不能据此说 child 被强制退出，也不声称所有异常 Drop 场景通过。原证据没有独立保存文件写拒的 Win32 错误码。

## 尚未完成及下一独立测试

B31 需可信启动消费 locator、实际 Python↔Rust wire、OS server identity/build anchor、强对象 identity map（is）、qualification 和 Backend-owned error 映射；这不是本轮已接通。Independent Test 还需异常 seq/context/重复字段/残帧/上限/晚完成、未登记 peer/实际远程 ACL、disconnect/重连/不同 session、原 child exit/活 descendants/UNKNOWN/取消后持有，以及真正 PreparedLaunch + bootstrap/carrier + API/worker/MCP/ASR 串联。原两 Rust 会话不替代这些。

qualified issuer/native protected installation、权利/许可/native ABI/minOS/8 VC floors、全147/24资源、POSIX guardians、真人 Owner、三 OS/R1/R2 仍未验收。不扩大模型/网络/发布/费用授权；完整目标仍为三平台 R1 独立验收后连续 R2。

## 终态交接

本轮所有输入只读且无变化，源读者已释放；自身纯 artifact/std-lib 解析，不运行产品或测试。原 preparation c8e2e4 exit1（PowerShell bare false，无 Cargo）、e93dfa metadata 完成 0 和 matcher-only rg exit1 保留，未回填原红或重跑。正式自身工具终态以 `RV68FinalizerTerminal.json` 与本轮最后工具返回为准；正式身份在 `RV68Handoff.json`。
