# Media 0057 选中 CTC 恢复消费者独立评审

结论：本次停止版本未发现新增 P1/P2。M44-I01 的 retry 消费者接线可在 **CLOSED_SOURCE_STATIC_ONLY** 范围内关闭：仅指已经保留合法原 assembly、五份 speech READY 资料和与本版本完全相符的实际 CTC MethodEvidence 的来源，不是实际恢复、质量、资格或完整制作流程通过。旧历史方法描述不一致的资料仍明确拒绝，不能据此关闭全部历史恢复。Backend **BSC-P01/P2/OPEN** 的最终 writer 父 intent 来源快照缺口不由本消费者修复或关闭。

## 固定输入及独立检查

任务卡 `G:/开发测试/Projects/VideoCreator/docs/task-board/MediaSelectedChildCtcReadIndependentReview.md`：`81856257c1529b1600f96b17c5be20a85531614c01b07facf18f845b3bbc9509`。

Media 根为 `G:/开发测试/Codex/VideoCreatorImplementation/AgentMedia/SelectedChildCtcReadConsumption/`；只读 SourceCopies/BeforeCopies，不读取 source_path 指向的生产源码。

| 固定件 | SHA-256 |
| --- | --- |
| Handoff.md | 256c6334e9ed24e6ec5147c60b33a49c28ac0280ed6cb34dd7eb6bd9ce492682 |
| Handoff.json | 04da08a64b683a5084d3e4022976495401b34feb8cb5f595ac800911973b32ea |
| SourceSnapshot.json | 5f61cba8b75a0f39a1f25d9cb029edaf66ac078df3e4f74954a714286cb6abf2 |
| Complete.diff | c19a95d162f5fa9432466e465c826c1a0684c706f25a6c09da692a7a33e6dce0 |
| FactoryConsumption.md | 1971ec61f2d2293f16e8ec9f72638e9f1c97dc6809cd940f6abe57c8e395f8c9 |
| FailuresAndLimits.md | 32d73124cb589e38052f03cdd23da97d3dbf9579d1d93bcdf10264411641c489 |
| 新 workflows/alignment_recovery.py（17832B） | afd7a3568addf5d41bb89a2567bd1c9ec840c797d7f4ea66d226646625329a80 |
| 新 workflows/bundle_recovery.py（45857B） | a85b15810c09a6efa4d26d4a9b5c114de972d8280a61ed2e8a31b4e788bcbd49 |
| 旧 alignment_recovery.py | db6df61634ddab7e8f6a5c52665589467ff24884710f7d644681a86efb7d20db |
| 旧 bundle_recovery.py | c8ea3d9add3c348bfd8c7a8fbefee3f9c7ec9c1c14a886a6e6737a251eeb5d13 |

独立标准库解析核对完整 44 新源与 44 旧源：88 个源码 AST 均可解析；只有上述两源字节变化，其余 42 源不变。9767B 全 diff 由原完整字节独立重建，与作者 diff 逐字一致。完整两个变化模块及相干调用链定向阅读；并非以作者 Ruff/AST 数字替代语义审查。

必要 Backend121 仅用 `Backend/SelectedChildCtcReadComposition/SourceStage/SourceIndex.json`（`c0ab833f165fb5cde13f23f54e6c7041107f115e3868b92f0b29f2f3a8d2acdf`）所列七份普通副本；ADR0057 固定为 `19472f7635a40be25630d0a84e0426bbd06283522f513128caa437e2499c1b57`。此前 Media44 报告 `bd13e857e941144272ed8ea71b623d73635d67fcae3a0c060ded2842847fa8be` 和 Backend121 报告 `85e3a0544caa39a9fbdd0659b78b93f8cfe9552fec557fe9667bb881290bfc46` 保持原件。

自有 InputBefore/InputAfter 共 112 个有限唯一文件；末核 differences=[]。没有扫描、复制或重新核查整套运行环境。

## 消费者实际调用链

### 原 held 来源与五事实

新 `SourceCopies/workflows/alignment_recovery.py:105–171` 在 117 行只调用一次 `require_final_port(port).read_selected_alignment_result(lease, continuation)`。原 `workflows/current_final_evidence.py:18–27` 要求唯一真实类型，随后 Backend `application/current_final_evidence.py:119–123` 经 `_current` 委托原服务；类型本身不授信。本次消费者不提供新的 preparation/command/Operation ID 查找参数，也不把返回值转换成执行 permit。

118–126 行仅消费 held 服务明确返回的 None，并核原 transcript/alignment 同一 ASR method、唯一原 MethodEvidence 和原 ASR Operation。没有捕获错误转为 None。Backend 原 `committed_alignment_read.py:241–272` 对这一 legacy 分支保原实际 ASR、当前允许策略和 READY method 事实；缺失/未知/错误 CTC 来源仍拒绝。

127–161 行核返回五元组、原 bytes、既有唯一类型、succeeded Observation、一个 CTC Operation、原 generated manifest/canonical request SHA、binding、ASR Operation/context/input/route/staging/context bytes SHA。没有发明不存在的 `CurrentFinalAsrRead.result_file_sha256`。读取结果的完整 staging SHA、文件稳定性及 Operation/Step 来源校验仍归实际 Backend held 服务，消费者没有拿自己算出的 DTO 字段冒充它。

146–150 行精确关联原 transcript 与 immutable alignment，只排除已由独立测量覆盖的 precision/content_sha256；不是把全对象不等改成任意通过。locator 为原 initial preparation 或 affected command SHA；实际执行身份来自原 Observation，MethodEvidence 的 model revision 来自同一个 registered request。Backend 原事实的合法性与 BSC-P01 的读后 writer 问题仍独立保留。

### 两个 Operation、方法顺序及后续报告

`alignment_recovery.py:162–171` 保 assembly.methods 原顺序：已有该 method 必须全对象相同且唯一；affected 方法缺失即拒绝；只在真实 initial 方法尚未写入时追加这一实际方法。不能以集合包含覆盖旧 Operation/config 或重排全部序列。

`bundle_recovery.py:376–378,517–520` 在 retry 传原 continuation 并消费五事实。`344–411` 分别保 `_actual(readset)` 原 ASR 验证、CTC `runtime_actual` 投影和实际 CTC Operation ID；`finish_v03_evidence` 明确带原 ASR ID。原 `workflows/registered_alignment.py:122–128` 只更换已成功 Observation 的 execution_identity，ASR text/language/segments/context 不被 CTC 或资格对象替换。原 `bundle_v03.py:272–313` 在 WorkReport 中保两份 Operation ID，实际身份仍须与当前资格相符；getter 成功本身不能使 report verified。

`bundle_recovery.py:445–455` Manifest 使用消费者返回的完整 methods。同步 `_repair` 完整 AST 不变，`551–561,603–605` 仍传本次受权执行所得 Observation/Operation；新增 retry getter 不派发它、不复活旧执行对象。新函数没有 run_alignment/register/Worker.begin/创建 child/分配资源或预算调用。这个判断是静态调用链判断，不是零 SQL/零预算的运行测量。

### READY 复用和独立精度

`_validate_readset:100–130` 保原 preparation/intent/fence、完整有序 allocations、Ready receipt 与原 bytes/hash、严格材料和原 candidate SHA。`_documents:206–234` 使用原 document-artifact IDs；不从当前请求重建地址。

已有完整 candidate 走 `_candidate` 后直接验证；未有 candidate 时，`_generate_candidate:406–411` 从已有 WorkReport/quality 或原 allocation 取 report ID。`430–439` 对已有 Ready 原 bytes 逐项比较，冲突拒绝；不存在的材料才使用原 allocation staging。`423` 保已有 audit 原字节。这不是一个全材料原子 staging 事务的证明：原逐项 staging 可能在后续冲突前留下新的部分 READY，本次未改变该既有行为；没有代码覆盖既有 READY 或以新 ID 隐藏冲突。

initial 五份 speech 未完整时原 `restore_initial` 分支及其原调用不变；本片解决的是 ADR0057 明确的 child speech/assembly 已提交、首 report/candidate 尚未 READY 的 retry 来源缺口。不能将此结论扩为任何未提交 child assembly 的恢复保证。

原 `bundle_v03.py` 全字节不变：55–68 的 source gaps、71–108 的当前资格关联、255–269 的每 utterance max(start,end)/nearest-rank P95、272–344 的 report/measurement/quality 分离均保留。独立 reference 只在 CTC 后用于测量；两 authority/200000us/current/rights 的实际门未被新消费者替代。not_measured/P95 null 不能凭新 getter 升为精度通过。

## 关闭范围与仍开放事项

- **M44-I01：CLOSED_SOURCE_STATIC_ONLY（限定本固定消费者）**。合法已提交 CTC 来源现在有独立 held 五事实消费路径，不再在 retry 首报告处误用 child initial-only getter。实际 initial/affected/partial-report/candidate/unknown/revocation/fence/source-change 等运行反验证仍 NOT_RUN。
- **历史 MethodEvidence 兼容限制保持 OPEN**：`produce_realignment_child:243–250` 将未来 actual method 的 limitations 对齐唯一 Backend 生成文本。旧已持久方法的 limitations 若不同，162–168 的全对象门及 Backend `committed_alignment_read:297–304` 会拒绝；本次不规范化/迁移/重写旧 bytes，不称全部历史 child 已可恢复。
- **BSC-P01/P2/OPEN** 保留为 Backend 归属。此消费者不补最终 writer 的父 intent 快照，不用 getter 的源级成功关闭该窗口。
- 新消费者未确认额外 P1/P2；RRD/ADR0058 角色依赖另一链不在本次范围。Media/Backend 原模型、weights、许可、运行时资格/资源、真实安装、SQL/API/MCP 自动视频+旁白+字幕+RAG 整流程、三 OS 与完整 R1/R2 均无本片独立通过证据。

后继 Test 必须另按真实准入验证：合法初始及新 canonical affected 方法；首 report 缺失/部分 READY/完整 candidate 复用；旧方法差异和重复/缺失方法拒绝；双 Operation；任一五事实/原 context/locator/current/fence 改动拒绝且不重派发；未知来源不退回 ASR。测试不能用资格对象伪造实际 CTC Observation，也不能减小原预算/未知成本/次数边界或给第四个等价原目标授权。

## 原错误、工具和停止状态

作者原猜路径读错、未执行 DTO 草稿错误及旧 Ruff BLE001 两项均保留；本片不以两个目标 Ruff 0 冒全目录或产品通过。自有 e8989f 读了不存在的 `Failures.json`，后改读正式 `FailuresAndLimits.md`，只是定位错误，工具仍自然0；ebaf01/9c21be 合并输出截断，已只定向补读实际缺失相干段，不声称截断输出全文可见。

本片工具只使用只读 PowerShell和 `C:/Python314/python.exe -I -S -B -X utf8` 标准库字节/hash/AST/diff分析，未 import/call 产品/测试/vendor。固定末核工具 `0a50aa` 自然 exit0、112 输入无漂移；所有源 reader 已停止。报告写入和最终封存工具的实际返回由独立 FinalHandoff/FinalizerTerminal 记录，不从文件存在推测终态。完整 R1 独立验收后连续 R2 的总目标未降低。
