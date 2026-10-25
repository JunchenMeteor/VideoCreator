# ADR0030：原生产物与可追溯构建来源的受控重建准入

2026-10-09。状态：**有限工程方案批准，源码/工具/产物/许可闭包及八项 numeric VC floor 尚未合格**。接续 ADR0027；不改现有资源、锁、私有合同或最低 OS，不授权本轮下载、编译、安装、系统读取或产品运行。完整 147 生产依赖、24 ASR 依赖、四 profile、MFC、CPU ASR 和三 OS 保持；R1 完整闭环后连续 R2。

## 1. 现有证据能证明什么

I34 正式 `NextEngineeringPlan.md` SHA `961556e853af66c8ba2a6e9879e18ee317e666010e5004c0a400c75c484f93c5` 是准确计划来源；任务摘要中的 NextRebuildPlan 不是另一个待寻找文件。I34 Handoff MD `fd4d1000…`、JSON `b1e0ee71…` 和 Snapshot `c1075c51…` 已核。四个 release 给出 source commit refs，但没有现有 wheel/standalone 完整 SHA 到实际 builder/compiler/linker/CRT 的绑定；pywin32 精确 wheel provenance 请求 HTTP404。HTTP200、source ref、RECORD、PE 线索和 release 日期分别不能补工具链证明。八项 numeric floor 继续 unknown，不填 0 或当前 host 版本。

I36 正式 Handoff MD `2e4c30eb…`/JSON `336f237a…`：其 own `--lib` 编译自然 0，固定 7 source、23 archive/index 和 5573 tool/SDK metadata pins。它证明本项目这个库的有限编译，不证明第三方 wheel 的 producer，不证明原 Engine/default wiring、Windows native collector 或 OS/ABI 已运行合格。本轮只读取该正式说明与元数据，不执行或读取工具/产物二进制。

沿用 ADR0027 固定的 Microsoft 一手规则：[binary compatibility](https://learn.microsoft.com/en-us/cpp/porting/binary-compat-2015-2017?view=msvc-170)、[supported redist](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170)、[redistribution](https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files?view=msvc-170)。本轮没有新联网或另耗官方调查 scope；I34 原六个 scrape、Context7 及其错误/费用观察按原记录保留，不重命名重试。

## 2. 唯一工程方向与第一批

对没有精确原 producer attestation 的必要 owner，走**同版本、已固定 source、目标 ABI/能力保持的受控新产物**路线。若后来取得确切旧 artifact 的可信完整构建证明，可以单独准入该证明；不得把新编译日志贴给旧 wheel。没有原 patch/config 时，新产物是可追溯的新发行件，不能称 bit-for-bit 复现原 wheel。

第一批限定 **pywin32 312 / b312 / `2a277cb5552756c2b4d42b524dc36d25e0bb6354` 的完整 wheel 输入准备**。完整 Pythonwin、COM/MAPI/native 模块保持；A24 已固定的四个 MFC Pythonwin importer 与 I34 的六个 focused pywin32 importer 是检查入口，不是允许只重建这些文件的白名单。禁止关闭 MFC、删除 mfc140u 或仅替一个 pyd。

Integration 下一卡分为两个明确切片：

1. **准备切片**：先消费 I34 的普通固定库存，列现有准确 source/build materials、目标 Python artifact/ABI、licensed MSVC/MFC/ATL/SDK 与 build dependencies 的身份和缺件。需要获取源码时，先提交 b312 精确 commit、官方 origin、完整 source/archive 与递归 submodule/外部依赖的有限获取清单、大小预算/上界和输出目录；只有统筹对该具体清单准入后才能获取。未知大小记未测，不用本 ADR 授任意下载或在线 resolver。完成同 revision 的真实 build entry/全部 flags/环境/依赖/NOTICE 后，交可执行 `argv/cwd/env` 与下载/编译 scope，不把 I34 候选命令直接执行。
2. **单独 build-only 切片**：完整输入清单及 builder 条件满足、有限执行 scope 经统筹批准后才运行。新任务目录中的 Source/Build/Cache/Target/Artifacts/Logs 独立，保留原 stage、锁与历史红；不得在共享环境安装或升级、不写当前 resource stage、不偷偷运行产品或 ASR。deadline、后代进程/EOF 和失败保留按准确 Process plan；Cargo/编译器执行是实际代码执行，不宣它是沙箱或零 native 执行。

若 source、必要工具/许可组件、依赖或机器缺失，准备切片交 **局部 blocked_source / blocked_builder / blocked_rights**、准确缺件与下一有限 scope，并结束交接；不等全平台资源、不把这些未知清成成功，也不永久停留在口头 pending。缺可复原原配置仍可提出明确新构建配置，但任何能力差异需架构独立裁定后验证，不能为完成编译删功能。

## 3. 每个新产物必须绑定的最小事实

Integration 维护唯一 private provenance manifest；不新增公开 API/DTO/SQL，不由 Backend 或 Media 补 Bool。每一个确认结论必须指向固定材料及实际 receipt：

| 部分 | 最小可核事实 |
| --- | --- |
| Source | owner/version、canonical origin、完整 source revision/tag 解析、归档/树 SHA、递归 submodule revisions、每个 patch 的字节/顺序和理由、license/NOTICE；CPython 上游 tag 与 standalone producer revision 分开 |
| Build inputs | Python target 的实际 artifact/headers/libs/ABI/架构身份；build backend、Python build requirements、CMake/Ninja/Rust/Cargo 等实际需要工具及锁；每个 wheel/crate/source/prebuilt lib 的 origin/version/full SHA/许可，禁止未锁浮动获取 |
| Builder | 实际 compiler/linker/MSBuild/toolset/SDK、CRT headers/libs、MFC/ATL 组件与可执行文件/完整输入身份；选择的 exact toolchain、目标架构、环境、flags、CPU/provider/OpenMP/链接配置。目录名、I36 库成功和 PATH 查到工具不代此构建观察 |
| Execution | exact argv/cwd/闭集非秘密环境、原 stdout/stderr、全部自然退出/超时/强制终止与 child/EOF receipt；实际选择工具的记录。受控已有 cache 只能按输入 SHA 使用，不让 cache/下载隐藏另一 producer |
| Artifact | 输出 wheel/archive SHA、size、真实 WHEEL tag、METADATA/version、全部 native/data/RECORD identity、静态/延迟/动态依赖与 owner 关系；生成它的 source/build/receipt manifest SHA；各副本独立核身份 |
| Rights | 本次实际发行者对 source、第三方编译输入及 Microsoft redistributables 的准入事实和对应原文/版本；MIT/PSF 或源码可读不能替 Microsoft 分发权，private provenance 不接秘密或假法律批准 |

编入结果的 prebuilt `.lib`、opaque object、随包 DLL/OpenMP/provider 等也有自己的 producer/兼容与许可闭包；仅重编最终 pyd、忽略未知预编译输入，不足以确认完整 floor。全部由本次受控 source 构建产生的对象可共享本次确切 builder 记录，仍需逐件输出绑定；保留旧 third-party binary 的件不能借它继承证明。

“可重复执行同一构建规程”“实际生成产物已绑定”和“重复构建字节相等”分开记录。首轮可确认 observed build→artifact 绑定；没有第二次实际构建与全件比较，不宣 bitwise reproducible。时间戳/debug/path 差异必须有准确解释及保留原字节，不把不同 SHA 写成相同；本卡不强行加一次未授权重建来求重复性标签。

## 4. 其余 owner 与完整资源闭包

| owner | 固定来源起点 / 必保约束 |
| --- | --- |
| CTranslate2 4.8.2 | `d44d2d069eb88c7b7804da864c10c201501cb4a9`；同 revision CMake/python wheel 的完整 CPU/shared binding 和随包 OpenMP/第三方闭包，原 CPU ASR 能力不改为禁用选项 |
| onnxruntime 1.30.0 | `f2c39fe2f838cf35ce7da92824f5a5e3ee6e88a7`；完整 Windows CPU wheel/providers/data；api/asr 两份实际 binary SHA 分别绑定，不因版本同名授互换 |
| chromadb 1.1.1 | `34dc0eb9b5b9943ca554aae2b3ecef6c1350f5f9`；同 revision Rust/Cargo.lock/maturin/Python 与真实 native 闭包；原 ABI 若为 abi3 保真实 tag/支持关系，不强写 cp313 掩盖 ABI 差异 |
| CPython 3.13.16 standalone | 原 archive SHA、实际 standalone producer/source revision/patch/config、完整上游 tag 根提交仍需补；`571c51f…` 仅 python.props file-last-change，不能充当根提交/producer。保 standard GIL、cp313、x64 与完整 stdlib/DLLs/CRT/Tcl/SQLite/OpenSSL，不只重建 python.exe 留混版资源，也不默换 PSF installer |

第一批 target Python 可以先被准确列为已有、provenance 未合格的 build target 候选；这不授它运行或发行。其执行/构建用途需具体 scope，最终资源资格仍依完整 standalone producer 闭包。后续构建次序由实际依赖决定，不把五 owner 全部同时重建当第一批。

I34 focused 13 importer/42 relation 与 A24 445 static relation 是定位材料，**不是完整 147/24 native producer 清单**。Integration 必须从固定资源索引列全部受 VC 影响的 native owner 与静态/延迟/实际动态关系，包括上述表以外的包；允许有已证 provenance 的件保留，不要求无依据重编纯 Python 包。必要来源缺一件，整体 floor 不合格。FFmpeg9、CPU ASR86、Agent/动态依赖、四 profile 与原有限 alias/actual-origin/held-guard 规则保持，不能以一包或五包 max 覆盖全局。

## 5. VC floor、发行前置和 OS 分开准入

八组件仍完整：mfc140u、msvcp140、msvcp140_1、msvcp140_2、msvcp140_atomic_wait、msvcp140_codecvt_ids、vcruntime140、vcruntime140_1。零 seed 静态边不让后三个 MSVCP 组件变 optional。vcruntime 329/99 当前 payload 解析关系不改称 System32 边。

每条新 artifact 的实际 compiler19.xx、VS17/18.xx、toolset/CRT14.xx 和 redist package14.xx 必须保各自版本域。只有真实 CRT/toolset 对应包及准确官方兼容映射能提供该 artifact 的 **redist14 requirement**；不能从版本号拼接转换、PE 或当前 host DLL 反推。必要 importer 全已绑定后，按组件/架构取已核 requirement 的 max。unknown 不参与 null/0 max；任何必要未核项保持整体 unknown，collector 原拒绝不放宽。

这里的 bound 是**发行采用的有依据下限**，不声称数学最小或全部旧 OS 最小。central x64 redist 仍默认工程前置：后续单准 exact Microsoft package/version/arch/full SHA/publisher/component closure/许可与实际发行者权利；变动 latest URL 不是固定产物。app-local 只在完整、获准分发的闭包与维护/来源验证下另准，不从 System32 复制八件。为用户运行不用安装完整 VS。

新完整 resources/index/private source contracts/manifest 原子产生新版本，由 Integration 独立实现与冻结；旧 stage/合同/error/history 不回填，锁与版本切换需其独立准入。先实际 loaded-origin/全部能力，再干净目标 Windows/完整作品与更新验证；一个当前 host 构建或 redist OS 官方清单不冻结产品 MinOS。macOS/Linux 不继承 Windows 或 VC 证明。

## 6. 下游分工与验证边界

Integration 先交第一批准备 Plan、确切缺件和工具/版权闭包，经统筹准具体 scope 后 build-only；随后 provenance/floor/redist 及新资源 consumer。Backend/Media 只消费合格的固定资源与身份，不写 compiler/licence Bool、猜 shell 或换 runtime。Test 独立制定并运行：误绑旧 wheel、同 version 不同 artifact、未锁输入/依赖遗漏、compiler/CRT 域混比、unknown 被取 max、缺 MFC/组件、错架构/来源/alias、真实构建产物与初始/最终 guard、完整四 profile/CPU ASR/三 OS 和真实作品。Review/Acceptance 各自审验；架构文档不关闭原红或代运行。

A27 所有读取仅固定普通文档/元数据；无 network/download/build/install/System32/EXE/native/product/DB/model/key/费用。原读取命令尾部索引等待已以原 session 77651 自然 exit0 收束。全部工具/reader 终态、固定 Handoff 后释放；外部 license/机器/源码缺件不占槽等待。完整 R1→R2 目标保持。
