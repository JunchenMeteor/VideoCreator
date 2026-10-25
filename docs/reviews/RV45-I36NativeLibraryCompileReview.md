# RV45 I36离线库编译证据有限独立评审

结论：LIMITED_COMPILE_EVIDENCE_SUPPORTED。本轮未发现本编译证据切片的新增阻断；只支持固定 library 的一次 Windows MSVC 目标构建自然成功，不授予测试、功能、RuntimeBinding、安装、发行或 Gate/R1 资格。完整目标仍为 R1 三 OS 独立验收后连续 R2。

## 固定身份与读取范围

输入仅来自 G:/开发测试/Codex/VideoCreatorImplementation/Integration/NativeConsumerLibrary-I36/ 及当前仓库规则/任务卡。正式 Handoff MD 2e4c30ebeecf57ae059df8b09b8ea00c196a4820769de1b478a5464660d899a9、JSON 336f237acef3f9362f3f0ab4022732ed5350ff3fd336a993a59eae2a23644fce；CompiledFreeze 1ffd61c84f7c5d9941349cd9b2223237ecc921dbe54c639f6871852908904892。

独立 byte/hash 核对 Freeze 明列 24 个文件记录（14 个实际编译源/普通源副本、原/普通 rlib、命令/准备/raw 等）及 13 个补充固定文件，前后检查无漂移。完整路径、bytes、预期/实核 hash 见 RV45InputPins.json；未扫描整个 Integration、重核工具环境或读取 B27/T33 活源。

## 原真实命令与终态

CompileRoundOne/CommandReceipt.json SHA 933a371b02de478e74c9571d31b90112ce3f7e735c4bf38d899b3851363c0cd5：只含一条 Cargo 命令，原 PID27372 / creation 2026-10-09T04:09:23.5440342Z，actual_exit=0、natural_terminal=true、stdout_eof/stderr_eof=true，force/timeout_sticky=false、owner_error=null。Handoff 保存原 exec82e4bc/session70412→owner poll0c8cbe/0；本评审未重跑。

argv 为 build --lib --offline --locked --target x86_64-pc-windows-msvc --manifest-path 指向本任务 Workspace/tools/build/native-lifetime-library/Cargo.toml，cwd 为本任务 Workspace。OfflineCompilePlan SHA 9b935b243592bd0d6a1a079496a6f1179175e9e16d94c894b49a5154ea9d0cbe 与原收据一致。

固定 RunOfflineCompileRoundOne.ps1 SHA 451c2bf5df79db720f3e373b47bc112c0dad6ed7d285900e0dbb872839d7eb31：
- 8–13 行核计划/输入/lock及输出边界；24–25 行 UseShellExecute=false，并 Clear 环境后只复制固定计划的19项环境与字面 argv。
- 30–55 行保留原 Process/两路 streams，读取 creation、原 ExitCode 和 EOF；57 行将退出/timeout/stream/owner错误保持失败。
- 58–59 行核 immutable lock 并记录真实 rlib；64–66 行复核同一计划的全部输入，任何 drift 使结果失败。

CargoHome/config.toml SHA fba20fb779d21fea83d88522e748745edc96f42c197540daec91c118eba3569f，指定 offline 和本任务固定 local-registry。上述是固定 runner/计划与原收据相干证据，不是网络监控、环境沙箱或所有后代终态证明。

原 stdout 0 bytes / e3b0c442…；原 stderr 8127 bytes / ae151d6e964d832e1b8db1ee7b9df4b7c2b0a7649f47f12128865c2a474a52b2 完整保留 7 条警告及 Finished dev profile in 12.66s。7 条分别涉及 Profile 未读字段、Document 未读字段、source_carrier 未读、StartedPreparedLaunch 未构造、launch_owned/launch_using 未用、context/bound 未读、bind_before_resume 未用。没有 suppress/fix/rebuild。12.66s 是 Cargo 报告时间；原 Cargo creation→记录 terminal 12.7415605s；收据 started→ended 25.8031987s，不能互换为完整工具墙钟。

## 输入、依赖与产物

七个 Workspace 源/配置逐一匹配普通副本，且每个在该 CompilePlan 有同 bytes/hash 的输入项，含四个实际 Rust 模块、Cargo.toml、Cargo.lock、lib.rs。lock SHA 4bb0070c55d57ffaaedb41eaa5442138d51aec8d6e75e8dc44d9013ad9616334；没有借 I32 原 EXE/旧消费者前缀当新 library。

原 PreparationReceipt SHA 0686dbc5a7e96d8ab4ec29bbbdbee9155a1c28756f95621e92c327b14d7270e8 保存5638输入、5573 current tool pins、7源/46 archive-index copies、errors/input_changes=[]；metadata 原 Python PID31448自然0/两路EOF。CompileReceipt 同样 input_changes=[]，独立复核的是保存证据及本轮37固定文件，不重 hash 那5573工具。

Plan 的11266项规范化 Windows 路径字符串去重为5693项，包含历史/当前路径拼写；该计数不是 OS file-ID、硬链接/TOCTOU 或运行依赖闭包证明。metadata proposal 的未执行状态、旧 inverse helper 非真实 before 快照继续按原限定保留。

原及普通 rlib 均为19956948 bytes，SHA 0ed9e4ef53f92830301a19cfa6309159917db25a055f24e28335013f4bae6ba7。
原编译输出包含22个依赖及本 crate；Inventory保存23个locked registry package，包括本目标未编译的libc。selected依赖包含generic-array/proc-macro2/quote/serde/serde_core/serde_json/zmij构建脚本和serde_derive proc-macro，不能称零 native 执行。此材料不是每个buildscript/linker syscall的独立执行轨迹。

## 未覆盖与下游条件

Cargo.toml 的build=false/autobins/autotests/autoexamples/autobenches=false与lib.rs四模块入口限定该构建。cfg(test)私有fixture/消费者、本 Test模块、engine.rs真实默认接线、main/Tauri/build.rs/facts EXE 均不在本次编译/运行范围。Win32/File定义可获得本目标类型编译依据；真实collector、WinTrust/catalog、原P01/P02消费者故障、birth/Job/cleanup、CT2/auth/ABI/VC floor/许可、资源闭包与三OS仍未测。8项数值VC floor仍unknown。

下游Test需绑定本新源/lock/library及其独立模块/夹具/runner，再独立批准和执行实际消费者证据；不得继承旧I32/T31绿色或本库编译授权。没有 product/API/Worker/MCP/ASR/模型/收费/密钥/安装操作。本评审不是验收代签，源读者在正式交接终态后释放。
