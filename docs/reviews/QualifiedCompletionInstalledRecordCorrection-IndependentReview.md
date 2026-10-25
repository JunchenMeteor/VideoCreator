# 已安装 RECORD 路径候选独立源码评审

结论：**LIMITED_SOURCE_STATIC_SUPPORT / NO_NEW_CONFIRMED_P1_P2 / RUNTIME_NOT_ADMITTED**。固定 RevisionThree 的窄修正支持识别原已安装 RECORD 中的 Windows 分隔符，同时保留原冻结 Python 根、manifest、文件身份及重复路径门。本结论不等于第三次纯数据绑定通过，不授候选函数、依赖批或 31 项回归运行。

任务卡完整身份为 `b854c9b280d1987ac577fa5e1ae303ecc0af2de3db936e811a73a1c9825c5472`，范围为 ACTIVE_SOURCE_REVIEW_ONLY。原两批纯数据失败、原 19 三次耗尽、31 NOT_EXECUTED / authenticated flow NOT_READY 均保持。没有读取活动 0067 或其他热生产源。

## 固定输入与独立核查

正式根：`G:/开发测试/Codex/VideoCreatorImplementation/Integration/QualifiedCompletionDependencyBindingPreparation/RevisionThree/FormalStage/`。普通副本位于该根 `SourceCopies/`，来源按 SourceIndex 中的 source / ordinary 成对记录核对。评审过程根：`G:/开发测试/Codex/VideoCreatorImplementation/Review/QualifiedCompletionInstalledRecordCorrectionIndependentReview/`。

| 输入 | 字节 | SHA-256 |
| --- | ---: | --- |
| Handoff.md | 1245 | 24b8cb3d881a8752d6f7919e08e82300bbc207a3882154e7c170e2d5dd474764 |
| Handoff.json | 3632 | d81315a30b8e3dfc903c2b26e015056c3292da1130d12b95b51feb453602fec0 |
| Full.diff | 8899 | 912a16165bf4209a051bd7426d9273c11a010f00156ce14cd1e1928b48d17e6e |
| ImpactAndBoundaryRequirements.json | 9107 | 9e2839f28d441b261d53e1e4193d2bee1c0ab936c26d77b090b31fbc67336d0c |
| SourceIndex.json | 8887 | c880facb6a10096aadb3580679daf101b7df0006fe5129c35822a8b2adfd12ad |
| Candidate-BindQualifiedCompletionDependencies.py | 27130 | 3c8b8ba70795bdd0c65985291ae6d5ace8e225585ae50ea71967e8d182458f55 |
| Original-BindQualifiedCompletionDependencies.py | 26404 | 999df7ee87e72e47efd8108a788933a8f0eb23148c2b3f8c63092a195507424a |
| Candidate-RunBindingPreparation.ps1 | 5239 | 13e04410df75d3bd4c2d47087db8cfbba03e23f7d8e3cda87401203e22a75485 |
| Candidate-PrepareBindingPlan.ps1 | 8189 | def96ece3900ffcd50e60e0e89aa8e985ccc85744769a27788b0457385cd6bf0 |
| Candidate-BindingPreparationPlan.json | 1251908 | 3e7a38dafcd48f52cad9234fa0051af09e72a3ec50821d98294dd667c22b778b |
| Original-BindingPreparationPlan.json | 1251888 | 24ea1240db841c121187d13193a0edb48baaf9107628ab72b18f58dffa5f845d |
| 两份 ToolRuntimeInputIndex.json | 各 597978 | 549ca603bbbb87c460d8a6cdef330d5afe78dd3ea9d714f48b926f4145239f3d |

`InputBefore.json` 和 `InputAfter.json` 独立核查 61 个有限 source / ordinary / formal / 治理 / 已声明非 runtime 数据路径：预期 mismatch 0，前后 differences 0。补充原 pendulum METADATA / RECORD / WHEEL 和第二批 Stderr.bin 共 4 个路径，单独保存 InputSupplement / InputSupplementAfter，不回填初始 61 项；补充前后差异 0。完整路径、字节、SHA 以这些过程原件为准。

全文读取候选 482 行 helper、完整 runner、PrepareBindingPlan、冻结工具及正式接口材料；原 helper 通过完整补丁重建对照。评审自有 ReconstructDiff.ps1 只处理文本，在逐 hunk 验证所有删除行 / 上下文 / 新旧行数后重建四文件：helper 2 hunks、runner 1、PrepareBindingPlan 1、Plan 3，均与完整候选文本逐字相等。它没有执行补丁或候选函数，也没有用作者 AST bool 代替这一核查。

完整 Plan 逐值比较确认只改变 `task_root / batch / argv / environment / inputs`；2284 输入中三个自有工具路径替换，2281 共同记录的 path / bytes / SHA 全相同。全部 2264 工具 runtime 声明成员逐值相同。另将保存的 InputsObservedAfter 的 2284 唯一路径与候选 Plan 对照，记录残差 0；这是原作者观察记录的完整数据对应，**不是本评审重扫 2264 runtime 文件**。本评审没有扩成全环境身份检查。

## 原失败与本次修正的关系

首批 CommandReceipt.json：SHA `c3ef22d14bb3b286f71551b92713f41c283240496efd2b6873ec7d26e88f1bc9`，原 child PID 37624，creation `2026-10-11T07:33:16.3167730Z`，natural exit 1，stdout / stderr EOF true。首批失败原因本轮没有另行重分析。

第二批 CommandReceipt.json：SHA `aab65dc737e562592573d765a84f24491aae97dfde6237da2f0d95d4e6a5f831`，原 child PID 26060，creation `2026-10-11T07:48:10.1812960Z`，natural exit 1，双 EOF true。原 1104 字节 Stderr.bin SHA `75145127238e248804798ee72a5637318da0d71b44e88609041fb95f55b7e389` 完整保存并读取，真实栈为原 helper main → run301 → record_relative74，因 `pendulum-3.2.0.dist-info\METADATA` 抛 Unsafe RECORD member。两原 receipt 的 timeout_sticky 为 false、errors 为空，不能用这些字段把 child_exit 1 改称通过。

独立读取同冻结 StageMoved 的原 RECORD 文本，共 128 行、126 行含反斜杠；零基 ordinal 2 的原行是 `pendulum-3.2.0.dist-info\METADATA,sha256=2qa3M6SkLsOLh7by3HTb2tYOTmAWJuVWXrj71esaIKA,6954`。RECORD 为 10787B / `eb31205b1ed54be508fa58763456eb399b239a9b1e78d97974c3e389f6c65348`；METADATA 为 6954B / `daa6b733a4a42ec38b87b6f2dc74dbdad60e4e601626e5565eb8fbd5eb1a20a0`；WHEEL 为 97B / `9ff06617af48c86b62a15584f5cdccff3b047deebec4c672d6fe4708bffaa84d`。三份实际文本与原 manifest 行身份均相同。这是原字面及来源事实，未执行 candidate record_relative 或模拟其路径返回值。

本次未改这三份包文本、原 RECORD 或原两个失败批次。source 修正可以消除原 blanket-backslash 拒绝的条件，但第三批整体能否完成仍未观察。正式状态不得写作实际绑定成功。

## 真实路径与消费链

以下行号均对应正式普通副本 `SourceCopies/Candidate-BindQualifiedCompletionDependencies.py`，全 SHA 如上。

1. 70–82 的 record_relative 在任何 join 前拒绝空串、初始 slash / backslash、任意 colon 和 NUL。因此绝对 drive、drive-relative、UNC、device 等字面不能借转换通过。78 只把原安装分隔符表示转为 slash；79 仍在同一个 `Runtime/Python/Lib/site-packages/` 基准做 posix normpath；80–81 要求最终保留精确 `Runtime/Python/` 前缀，逃出该根拒绝。合法 `../../Scripts` 的语义保持：它没有被改成只能留在 site-packages 的门，也没有引入任意外部基准。
2. run300–308 继续用 csv.reader 读取原 UTF-8 RECORD，每行必须恰有三个字段，零基 ordinal 不改；raw_path / encoded_hash / byte_string 原值不被转换覆盖。规范化结果在读取 entry 前进入同一 RECORD 的 casefold seen 集合，separator、dot、parent 别名或大小写映射到同一最终路径的第二项立即拒绝。这里拒绝的是**规范化后的重复目标**，不是把所有含 dot 或合法 parent 的单项一概拒绝。
3. 309–328 通过 exact `actual.get(relative)` 查询由原 manifest 建立的成员，必须已有 IDENTITY_MATCH 才能得 RECORD_HASH_SIZE_MATCH；保留 sha256 算法、URL-safe 无 padding 哈希和十进制原 size 的核对。未知 / changed / unsupported / mismatched 目标进入 record_problems，不能伪造身份匹配。它们是问题记录而非任意路径读权限；helper 的整体状态仍为 data observed / runtime not admitted，exit 0 本身不能代表问题集合为空。
4. 329–334 另存 raw_row / ordinal / 原 literal / separator 表示 / 固定基准 / normalized_manifest_relative，并明确 normalization_grants_authority=false。没有写回 RECORD，也没有将转换后的路径当包签名或运行授权。
5. 196–220 的原 manifest 全成员 expected / casefold 门、safe_member56–67 的段约束与逐层 symlink / junction 检查、root168–170 检查、regular stat213、实际 bytes / SHA216 保持。物理 walk225–240 对 linked member、成员上限、missing / unexpected 集合继续报告；LICENSE 等原文本只在已匹配 entry341 后才读取，不使用 raw_path 直接访问文件。

这套链的静态支持不等于 Windows 实际文件句柄、系统路径别名或跨读取 TOCTOU 的原子证明。原 stat / exists / 字节读取和前后 hash 是多个观察点；本任务未运行物理故障、reparse 替换或 OS 测试，不能将源门概括为“所有路径竞态已安全”。

## 未降低的原数据与生命周期保护

冻结 inventory 实际声明 147 distributions / 147 METADATA；原 manifest 中有 148 个 METADATA，唯一差集恰为 `video_creator_engine-0.1.0.dist-info/METADATA`，122B / `1e57f23491fe5097bb8b4d0faf6f3d4dd77c0d7d5c40ca6eba87045618518d22` / generated=true。helper243–270 的 name 唯一、cardinality、additional 集合精确相等、generated 双检查、实际身份核对均未改，不将内部候选 metadata 当第三方合法资格。

原 license 字段和 body 门未降低：helper343–348 对已匹配实际原文件按原 cap 保存原 bytes 和 ordinary_body 身份，legal_admission=false；356–364 保留原 License / License-Expression / License-File、raw Requires-Dist、Provides-Extra、原 selected extras、历史 wheel 行。85–100 / 365–385 只做 name-index / declared union，不评估版本或 marker，也不把其他 OS / 未选 extras 的 absence 强说成 Windows 缺依赖。实际许可证履行、分发许可及 marker / extras 激活本轮未验证，不从 METADATA 的 MIT 字段给整个 147 包法律准入。

PE103–163 / 386–412 的 bounded 静态解析、原 delay-import 引用、候选 DLL 名表保留；实际 native load 为零，ABI / search order admitted=false。仍不能用 cp313 / AMD64 文件名或旧表 SHA 代真实 DLL 来源和 ABI 兼容。

Plan caps 全字段逐值相同：JSON16MiB、METADATA1MiB、RECORD8MiB、license4MiB、native单文件256MiB、material30000文件 / 1GiB、deadline1800s。runner 的 lifetime sticky1860s / no_kill / no_restart / no_replay / original byte EOF 不变。helper221 的期限检查仍在原 material 循环，不能将未增加的检查点说成所有后续阶段的硬中断保证。

完整 runner 普通副本的 7 / 12–18 行保 Plan SHA 和全部输入门；50 创建同一 child，56–57 对原 stdout / stderr byte stream 建 CopyToAsync；59–63 sticky 超时不会重开进程；74–94 finally 使用同 process 等自然终态并收两 stream、核 after inputs、保存原 receipt；97 将 child_exit / sticky / errors / 缺任一 EOF 判为失败。此次 runner 全差异只 taskRoot 一个值；本轮未注入 save / observation / lifecycle 故障，也未证明最外层 tool 观察链。原异常仍可能中断 finally 后续动作的 inherited 边界不能由路径修复宣称已消除。

main469–478 仍核传入 Plan SHA 后进入原 run。Plan / Handoff 的 decoded 路径对应同 RevisionThree 文件和 cwd；-I / -S / -B / utf8 与受限环境不改。它是未授权的 future command 描述，不是实际 admission。当前候选 BindingPreparationRoundOne 输出目录未存在。

## 下游应保持的边界

Integration 持有候选 helper / runner / Plan，不需要本轮确认的新源码 P1/P2 修复。Test 的正反路径案例和期望仍由 Test 独立持有；BoundaryRequirements 只是需求提议。必要后继应区分原真实 Windows 安装字面及合法 Scripts、绝对 / colon / NUL / 根外路径、规范化与 casefold 重复、unknown / changed manifest、链接及 size / SHA 不匹配；不能通过改包原件或放宽 frozen root 获绿。本报告不授权这一批运行，也不把上述条件列成已执行案例。

第三纯数据依赖批、全部147绑定完成、版本及 extras/markers、真实 DLL/namespace/source-map、完整 licenses、154目标模块和31回归均未通过本轮运行验证。正常 authenticated flow / qualified observer 的真实来源缺件保持 NOT_READY；原 Engine/Pydantic 失败导入段及三次 exhausted 限制不因本次路径 namespace 更新而重置。完整制作流程 / 安装包、真实媒体 / ASR / 人审、三 OS R1及连续R2均无本轮独立通过证据。

## 收口与工具证据

读取工具 48dfda / 3c11f2 / 3959bd / 88acd6 / f72dc8 / 366c54 / 5bebc2 / f900a1 / 8a18fc / fd093d 均自然 exit 0，无 live。88acd6 的合并输出被截断，原截断保留；未声称其整段输出全文可见，主函数469–482及 SourceIndex 投影已通过 f72dc8 定向补齐。其余完整 helper 段与完整 diff 原件独立核对，不拿截断替全文。

自有 InspectInputs / ReconstructDiff / InspectMetadata 只运行 PowerShell 字节身份、固定 JSON、原文本与补丁算法；候选 / parser / third-party / target / cases / SQL / native / network / installation / models / fees 均为零。不存在候选调用、新增环境或 runtime 树扫描。InputAfter61差异0，InputSupplementAfter4差异0。报告和 FinalHandoff 冻结后，末 finalizer 的返回由 Agent 实际工具结果另确认，文件不能提前自证自身返回。所有读取句柄均随已自然终态工具关闭；本轮不持生产 freeze。
