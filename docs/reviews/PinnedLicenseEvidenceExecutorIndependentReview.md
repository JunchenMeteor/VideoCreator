# PinnedLicenseEvidenceExecutorIndependentReview

结论：SOURCE_STATIC_REVIEW_COMPLETE_WITH_TWO_OPEN_P2。候选尚不具备执行准入；PLEE-P01 和 PLEE-P02 均为 Integration 归属、OPEN_SOURCE_STATIC。没有执行候选、故障注入、parser、归档解释、下载、产品或安装。本报告不把静态读取、作者 source assembly 退出 0 或声明的工具闭包当实际进程、原始双流 EOF、许可证分发、包安装或 R1/R2 验收。

## 固定范围与输入

任务卡为 G:/开发测试/Projects/VideoCreator/docs/task-board/PinnedLicenseEvidenceExecutorIndependentReview.md，5132B，SHA256 5521f6326cb057ef3a0336487f9fab2e44d432bf4511a7b64d7ec42211a58933。只读已停止 SourceStageRevisionTwo 的 ordinary 副本及正式材料；未读取其 source_path 指向的生产实现，也未读取其他角色热源。工作区和仓库 AGENTS 的 SHA256 分别为 af69f90a45d8b3ed80bc9b5e2cc4243ac8e2cc6f53785aa28ae2d423f93a17ec、6de878f514b02788f8af5ba512f71c56bb053f6800d76cf19f3cdd955b7f6a0d。

正式根：G:/开发测试/Codex/VideoCreatorImplementation/Integration/PinnedLicenseEvidenceExecutorPreparation/SourceStageRevisionTwo/。主要身份如下，完整 53 路径和大小、SHA 见本评审 InputBefore.json 与 InputAfter.json：

| 文件 | 字节 | SHA256 |
|---|---:|---|
| Handoff.md | 2412 | ce55b2373fae96f0342a93fa4f731946d64cc521b9b40d6ebf11976da76d5892 |
| Handoff.json | 5768 | 9c7fc277c1136d392f34293b9be80b875b5814a204f45222f38be219d417550a |
| SourceIndex.json | 9678 | bc8c7c4a5edaf4005f96fc97a0a5f0a7cf29a20076c6150501120ea010bab000 |
| Full.diff | 127915 | 2aae350a1c422d9ab791f16ccd5899f8b4e2bca4ef7247ef40f4f350a9458789 |
| Impact.json | 27656 | d1fb171b6658cede9b196142d344a90bde5bb961b64738aa18386a83d2cc7176 |
| Interfaces.md | 3666 | cad9fc3616fead6705d4cd7f5b40e209590cd0c800bd469e23c11aedcacdfbcb |
| InputIndex.json | 15008 | d1a18315b06d79e7f963ae1cb487c5f0384e27e52aeee4516738aeece6e37a3e |
| OrdinaryIndex.json | 14040 | 845f7a2c8524df6e3ddf67ff4bc37ed8aeea2cadd30bb27e538dc8bb98221715 |
| ErrorMatrix.json | 3126 | 5807cdd20b6eb77d93ee974ecdd87d40911185b4b38d6b7cb2a1df5ee47ce1fb |
| FreezeReceipt.json | 1669 | e710f956f366370fe080dea2e44cd72190805471411ad12b1ed4b1735451a861 |

自身过程根：G:/开发测试/Codex/VideoCreatorImplementation/Review/PinnedLicenseEvidenceExecutorIndependentReview/。 corrected InputBefore 的 53 个固定路径末核全部大小、SHA 相同，changes=[]。此为有限输入核验，不是运行环境或实体工具闭包重扫。作者 InputIndex 有 23 声明项，其中 22 有 ordinary 输入，系统 pwsh 项为声明；ordinary 索引列 47 件。上述口径不互换。

## 完整差异与源码消费

已按全部 2057 行重建 127915B Full.diff 的四个差异段；前三个旧版本与停止的 Input-014、Input-013、Input-012 普通副本字节、SHA 一致，三个新版本与实际 ordinary 副本一致。第四段 CandidateRevisionOne 的旧 owner 由差异重建、与 DiffPairs 声明的 10355B / 6c385611735aee23466e99cd71187a1b841a7f32b1dcfc484b8530c16fdf93e4 一致；没有另读该旧 candidate 的物理文件，故不把这个声明匹配称独立物理副本核验。DiffReconstruction.json 保留每段完整结果。

完整阅读 13 个 stopped source/plan/receipt：Acquire、Run owner、692 行 Inspector、174 行 tail、148 行 Assemble、RunSourceAssembly、165 行 Finalizer、6B pth、Loader、两个完整 Plan、PreparationDelta、SourceAssemblyReceipt。三主源码 SHA 为：

- SourceCopies/AcquirePinnedEvidence.ps1：8865B / 845456f377161503e9a97ac2293ddbf48b8036ade235f51d9d8ef16932a25b1a。
- SourceCopies/RunPinnedLicenseEvidence.ps1：10452B / 833c5ca6f2a1ebc224a2f172c7784556b73fe0f7358cef59066e40907cf65ff7。
- SourceCopies/InspectPinnedLicenseEvidence.py：34692B / 7b048415f60dd47e7d77f8b8afa9f5da46d144a94dd491251898686f317bf6e6。

WheelExecutionPlan.json 为 44360B / e9b3a6b1b7c71ee8a62612310952771de449225d1bdd04c9d173c71ce2199f14；CommitExecutionPlan.json 为 39442B / d5fd56301e78acadf872a4d609e3fb2d6546bb2130b7fb69d534c86a03805a42。两个 Plan 非 phase 字段、完整 input 向量、三个 Loader 投影及原请求向量逐值比较；实际 argv 的 exact Plan SHA 和 cwd 同正式交接一致，不靠作者 bool 代读。

## PLEE-P01 — 观察异常发生在 drain 建立前，原始双流证据丢失

P2 / Integration / OPEN_SOURCE_STATIC。精确停止源为 G:/开发测试/Codex/VideoCreatorImplementation/Integration/PinnedLicenseEvidenceExecutorPreparation/SourceStageRevisionTwo/SourceCopies/RunPinnedLicenseEvidence.ps1，SHA256 833c5ca6f2a1ebc224a2f172c7784556b73fe0f7358cef59066e40907cf65ff7。

82–84 行先 Start 原 Process 并置 started=true，再读 PID/StartTime，最后才建立 stdout/stderr CopyToAsync。最小条件是 Start 成功后 StartTime 观察抛异常；此时两 task 均为 null。103–108 行 catch 等待该原 child，却跳过 null task；112–113 行释放原流/Process 并保存。原输出字节因此未被复制。第二条 pump 建立抛异常时，对缺失的那条流也成立。若 child 因未 drain 的流填满而阻塞，还可能阻止自然退出；这是条件性控制流后果，没有声称固定 child 正常必然填满缓冲或已发生 OS 故障。

保持红且不启第二个 Process 是正确的，但不能同时证明 ErrorMatrix 要求的原 Process 双 byte EOF。该 metadata-before-pumps 次序继承旧 owner；新 recovery catch 未补齐它。修复须由原 Integration 在新 immutable 阶段保存同一 original Process，对两条原 pipe 的 drain 独立建立或恢复，首错误保持 sticky red；明确真实 terminal/stream completion 或无法观察时的保留条件。不得把 null 当 EOF、伪造 creation、启动替代 child 或吞错误。

后继独立 Test 最小条件为 post-start creation getter 异常及第二条 pump 建立异常，核同一原 child、两原 byte 输出、无第二 Process、真实自然终态。本报告没有授予这些执行。

## PLEE-P02 — 自然零退出及已完成双流路径漏期限检查

P2 / Integration / OPEN_SOURCE_STATIC。同一停止源和 SHA。86–89 行仅 WaitForExit(1000) 返回 false 时检查 elapsed；91–96 行仅 pump 尚未完成时检查。静态反例：上次失败 poll 仍在 sticky_seconds 内，原 child 在下一次一秒 wait 内、但刚过期限自然 exit 0，两 pump 已完成；两个 loop body 均不再执行，98–99 行接受 actual_exit=0 且 timeout_sticky=false，外层可继续 Inspection 或封存成功。

原 Plan 的 acquisition 22000 秒、inspection 900 秒未变，本发现不建议改阈值。Stopwatch 还在 post-start metadata、pump attachment 和 85 行 receipt Save 后才启动，故可能漏掉阻塞 setup 的时间；上述 terminal-gap 反例独立成立，不依赖这项附加时间条件。

原 Integration 应在原 terminal/双流完成之后、任何成功或续 child 之前检查同一 monotonic deadline，超期状态永久 sticky，保原 Process/EOF，不 kill/retry/restart；明确授权 command 的起算瞬间，不能围绕阻塞 Save 后移。后继 Test 应区分合法期限内成功与刚过期限的自然 0 且双流已完成。本报告无实际计时测试或运行授权。

## 已核安全门与保留保护

Acquire 的 before-pin/regular path、phase exact SHA、闭集 HTTPS host、精确 fresh 文件名和 CreateNew partial、禁止覆盖旧 batch 均为真实源码门。六 wheel 请求与四 Git commit 请求的完整 URL/spec 向量保持原 Plan；一次尝试、3600 秒、第一红停止、不自动 retry。HTTP 禁 redirect/proxy/cookies/default credentials/decompression，限制 header 并验证 status 200、final URL、编码、Content-Range、body cap；wheel 要求精确长度。remaining+1 探针超过 cap 即拒绝并在写入前挡住，多取的一个失败探针不成为 accepted body。只有原 byte EOF、flush、完整 size/SHA 后 Move；异常及 dispose/save 错误不洗成 0。

六 wheel 获取上限合计 5990743B；旧 FlatBuffers 26661B 仅 exact read，合计所选 wheel 6017404B，无重复 GET。四 Git body 各 1MiB、合计 4194304B；未知历史 size/SHA 保留 null。Tokenizers 此 Windows 选择为 0.23.2，不能继承旧 0.23.3 归档红或其他平台向量为已执行。六与四 phase 独立，不形成自动十请求授权。

owner 实际 RealChain 使用一个反斜杠字符 Replace('\','/')，未读错成双字符。真实全路径 no-reparse、23 input pin、29 工具全成员/大小/SHA 在 batch 和 HTTP 前检查；缺工具 fail closed。原 Process 正常分支采同一 PID/creation、两原流 CopyToAsync、自然 exit；没有 kill/restart。新增 post-finally cleanup-error 门可阻止 cleanup 错误后继续下一 child；这一修订有源码支持，但不能补 P01、P02 的缺口。outer 错误、输入漂移、row error、sticky、exit、EOF 均保留失败，末 Save 异常传播，不虚构成功终态。

Inspector 只以 19 个 exact source 模块的固定 byte/hash 编译装载，sys.path=[]、不写 pyc、自有 finder/Builtin/Frozen 闭集；不导入 archive vendor、site 或任意 ZIP fallback。这里只审源码，未触发 compile 或实际 import。12 个保护 helper 比较保留原校验；read_json 的文本差异仅额外空行，其 1MiB、duplicate-key 拒绝条件未变。文件数/expanded byte caps 收紧，不放松旧 RECORD/native 门。

ZIP 路径、Windows reserved components、casefold alias、symlink/special、central/local membership、single disk、EOCD/no tail、deflate EOF/CRC/unused bytes 和 expanded caps 真实保留。仅允许有界冗余 local ZIP64 size pair，真正 ZIP64 仍显式 grammar 拒绝；不能据此断言上游归档坏或已经兼容。RECORD 全成员、三列/唯一/self-empty/精确 size+SHA；METADATA Name/Version、WHEEL 1.0、ASCII 大小写 true/false、完整 tags 均严格。支持 METADATA 1.0/1.1/1.2/2.1–2.4，其他版本保持拒绝。

License-File 按 2.4 的 exact dist-info/licenses 路径或 legacy 两个候选中唯一真实路径处理，缺失/歧义拒绝；不凭 suffix 猜正文。license/notice 名称 heuristic 仅用于候选证据，原 archive 和所选原始 METADATA/WHEEL/RECORD/license .bin 保留。PE 仅数据解析，不 load。Git body 限 1MiB、duplicate-key 拒绝、精确 commit/repo/tree URL 和 SHA 形状；不把 API JSON、tree SHA 形状或声明签名当实际 Git 对象密码学/源码等价/许可证正文证明。

## Loader 与许可范围

LoaderProposal.json 为 22115B / 9f33711ff6ea5590b6415193df6c1ee3b175d3366400c271d9c89f0f995810ff。完整 29 target 声明为 5 binary、19 source、3 startup encoding、1 linecache 和本 candidate 的 6B pth，合计 6899063B，target 唯一；28 个历史成员声明与旧 Plan 停止 ordinary input 中的 path/size/SHA 对应，未重新读取历史 runtime 实体或复制工具。

6B PythonPathProposal.txt 的 byte 为 2E0A4C69620A，仅 '.\nLib\n'，SHA256 82cfe92f04fbacfdcb908eccc04c6c9bfb662bd6e554615a67e53d573d544387；不含 import site，未使用旧 153B pth。源装配仅生成文本/JSON 和 regex module-map，未运行 Python。作者 PSParseReceipt 错误数组为空及 source assembly 自然 0，仅是其静态/材料生产范围，不是 candidate 启动或 Inspector 兼容性证明。

声明的 5 binaries、Builtin/Frozen 实际 origins、CPython ABI、动态 DLL/.NET/TLS 来源、原历史 source 和许可证完整 body、真实未来 materialization 均无本轮执行证据。缺工具前置拒绝是源码支持，不是 physical tool 已 ready。不能从 metadata、数量、名字或 LicenseFile 候选推合法分发、生产安装/模型/ASR/TTS/六归档/目标业务资格。

## 原错误、工具终态与后继责任

自身 62da0c 因 PowerShell 数组拼接误把多路径组合为一项，出现非终止读取错误但 outer exit 0；原 InputBefore-OriginalProjectionError.json 保留，6d8fa8 才生成正确 53 输入。没有把该 outer 0 称首次末核成功。大输出 f5eada、75419e、8ccffd 的截断保留，只由后续定向读取/完整向量和字节重建补齐，未声称截断输出全文。原作者 formal/静态准备失败与 SourceStage 修订身份不改历史，不把其修订 outer 0 洗掉旧 stderr。

末核阶段 eb52f4 在 shell 前因 MXC 枚举 F 盘 BitLocker 锁定失败，exit 1；没有目标 IO 或产品运行。受审查通道 73699e、e2228c 自然 exit 0 后完成自身材料读取。完整自然工具记录与本次封存实际 return 分开：ToolHistory.json 不预言当前 writer 自身 exit，FinalizerTerminal/最终消息记录已观察结果。没有 live target session，没有重启旧工具，没有遗留原 Process/Browser/网络句柄；全部阅读为同步有限文件 IO。

原 19 exhausted 三失败、31 NOT_READY、绑定原两失败及第三数据限制、原 regex/voice/Tokenizers 红、历史 198/18 类材料缺件和未知历史次数/20 元/已付三次等既有约束保留，未重置额度或给新运行。本轮输出仅交原 Integration 做 P01/P02 新 immutable 窄修；真实正常运行与故障注入另由独立 Test 在明确后继准入下验证。此报告不授下载、归档解释、应用候选、安装、费用或 R1/R2 通过。
