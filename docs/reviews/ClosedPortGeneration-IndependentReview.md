# ClosedPortGeneration 独立源码复审

本轮以停止版本 `e38057e30a5576180d39950667318356354a800bf3ad3cd5434038dc45fd26b7` 对照原 `ebb818fa78044533eb8ca924a445f732e02c8f8feed5eae48d2291140d06e9f1`，支持 DALI-P01 在 **CLOSED_SOURCE_STATIC_ONLY** 范围关闭。原已撤销 A 再次 `close()` 的入口现在先核同一原注册表中的对象身份；若不再是实际成员，在同一 RLock 内返回，未进入删除 factory 或诊断 held 条目的原清理循环。合法后来 B 仍是注册对象时继续原首次清理。未确认新的 P1/P2。

这是原源码缺陷的限定修复结论。未运行产品、数据库、Worker、Owner、native 或 A→B→A 测试；没有安装、真实资源资格、三 OS、完整制作流程、R1 或 R2 通过结论。原失败与历史 finding 保留，未改成运行通过。

## 固定来源与身份

任务卡 `G:/开发测试/Projects/VideoCreator/docs/task-board/ClosedPortGenerationIndependentReview.md`：2568B，SHA256 `b41abd26ea1b89c651462cc58c98889256b4010849ca37277d53ba7951808b48`。工作区和仓库 AGENTS 已全文读取，分别为 `af69f90a45d8b3ed80bc9b5e2cc4243ac8e2cc6f53785aa28ae2d423f93a17ec` 与 `6de878f514b02788f8af5ba512f71c56bb053f6800d76cf19f3cdd955b7f6a0d`。

新固定根：`G:/开发测试/Codex/VideoCreatorImplementation/Backend/ClosedPortGenerationCorrection/`。全文读取 Handoff.md、Handoff.json、Interfaces.md、729B FullDiff.patch，按 SourceIndex 中每项 `ordinary_copy` 读取停止普通源；未用其 `source_path` 读取当前实现。

| 文件 | SHA256 |
| --- | --- |
| Handoff.md | 71c3dbf43e8dcedaae8ded99f29abdc82da488f6da8c5a191959159764d7d651 |
| Handoff.json | 18095cf0dbbd19d73bf783ac30dd31a3ec651ccf07e35e50565e631592987982 |
| Interfaces.md | 53bc482ee47d7e00afe85ea1467ca5f1c020b9f718f924bff063a3aab805409b |
| SourceStage/SourceIndex.json | e38057e30a5576180d39950667318356354a800bf3ad3cd5434038dc45fd26b7 |
| SourceStage/FullDiff.patch | bd438241b63dac083eb2ec0c73f2007e763974f4be162759937a70889ef00c58 |

原固定根为 `G:/开发测试/Codex/VideoCreatorImplementation/Backend/DiagnosticActiveInputsLifecycleCorrection/SourceStage/`，SourceIndex 为 `ebb818fa78044533eb8ca924a445f732e02c8f8feed5eae48d2291140d06e9f1`。原 finding 全文读取：`G:/开发测试/Codex/VideoCreatorImplementation/Review/DiagnosticActiveInputsLifecycleIndependentReview/Finding-DALI-P01.md`，SHA256 `52ada4a069c164a4dff72f4d9391acce633eda60e87539917fb679e70ed1493c`；原正式报告与交接只作历史身份，未重审其全片。

独立核 130 旧、130 新普通源的 bytes/SHA，以及每项新 `before_sha256` 对原版本的关系；仅下列一源变更，其余 129 个相同。包括规则、任务卡、有限正式及历史件共 272 条输入；纠正后的 InputBefore 无残差，InputAfter 实际 272 条、差异 0。此为完整来源身份核验，不是全文审查 130 个模块或运行全库。

唯一变更普通源：`G:/开发测试/Codex/VideoCreatorImplementation/Backend/ClosedPortGenerationCorrection/SourceStage/SourceCopies/services/engine/src/video_creator/application/current_final_evidence.py`，11623B，SHA256 `95877d4872273f795ef0e64880382f8c339eca3426638577fe5db2fc7fc7240d`；旧 11600B，SHA256 `96c99854db5e08853266a1bdddc743c5f1ac8ddbbb41042f4c685ce49c6f020b`。

## 原触发和修正机制

原 DALI-P01 的条件是：A 首次关闭并撤销原成员身份，合法同 lease/thread 的实际 factory 与 B 后来建立，再对仍持引用但已撤销的 A 调用 `close()`。旧方法只在仍注册时 pop A，却无条件继续 lease/thread 清理；因此能够删除 B 后来的实际 factory source 和部分 held 状态，导致原实际来源校验拒绝 B。active inputs 的 owner 条件局部保护不足以保护后续 factory 清理。

新 `current_final_evidence.py:160–164` 在 `self._service._lock` 内把 registry 对象身份当作整个关闭操作的前置条件：`get(id(self)) is not self` 时立即返回，否则 pop 原成员再执行原后续循环。没有新增 caller 可赋值的 `_closed` 布尔量，也没有捕获或吞掉 403。注册表强持对象，核的是同一 service 中的实际对象身份，不是 tuple 标签或作者断言。

独立在内存将旧源码的唯一两行条件块替换为新三行块，UTF-8 编码后完整 11623B 与停止新源逐字节相同；替换命中数为 1，条件块之前前缀、从 `_diagnostic_inputs_active` 开始至文件结尾的原首次清理 suffix 全部相同。未 import 或调用源码。完整 729B diff 已读，结果封存在 DiffProtection.json。

因此上述 A 再关闭时在第一次 registry 判断返回，不再读取并删除后来 B 的 factory、held 或 active 状态。仍实际注册的 B 首次关闭会通过判断，撤销 B 后继续原清理；再次关闭 B 则同样返回。本结论不把同时多 port、跨线程清理或全部生命周期 redesign 当作新增批准：原 unique/current 门仍负责合法使用范围，原首次清理范围仍按旧合同保留。

## 相干真实调用链与原门

以下路径均指新固定根的 `SourceStage/SourceCopies/services/engine/src/video_creator/application/` 普通件；源身份也在 InputBefore / InputAfter 中逐项登记。

1. `bundles.py:249–271` 的真实 `BundleService(CurrentFinalEvidenceService)` 建立 `_final_evidence_ports`，使用 `threading.RLock()`。`current_final_evidence_service.py:30–53` 先读取原 lease/bound context 后登记 `registry[id(port)] = port`；`_final_binding` 对同 lease/thread 实际成员要求唯一，继续核 current binding。新 close 使用同一原锁和同一注册表，未用旁路或影子 guard。
2. `current_final_evidence.py:35–44` 的 `_current` 继续要求 registry 的原对象、原 thread、原 lease，再调用原 Engine lease 检查；`prepare_component_diagnosis:130–132` 仍将原 `owner_port=self` 传入 service。close 的后续原循环仍保留 active tuple owner、factory lease/thread、diagnostic held owner 的原关系。
3. `media_registration.py:317–350` 的实际 factory source 建立路径先获得原 current services，再验证原 engine/worker/bundle/executor、registration、execution port、bound context/current policy 来源，最后在 BundleService 原锁下持有来源。`affected_repair_service.py:65–72` 仍要求实际同 lease/thread factory source 唯一，否则原 `production_services_source_invalid` 403；未降门或制造资格。
4. `component_diagnosis_service.py:104–110,311–389` 的真实 prepare 继续先核原 port 成员身份、实际 factory/methods、parent/read input；原事务 guard/current/immutable 冲突保持。退出后在同锁再次核 owner port 再持有 input，active key 含 run/preparation/thread/fence，held tuple 含原 owner。`_current_diagnostic_inputs` 继续检查 owner、thread、lease、fence 及实际来源。`diagnostic_selection.py:221–246` 对 active 重用继续核原成员、held tuple 和 fence；失效后不伪造缓存，仍走原 selected reader。
5. `current_final_evidence_runtime.py:72–92` 的真实 `_final_producer` 使用原 factory 与 binding，取得注册 port 后调用实际 Media factory；若抛 BaseException，原 `ports.close(); raise` 保留。`media_registration.py:384–407` 将 port 记入真实 `_active_final_ports`，原恢复消费者签名门保留。
6. `media_registration.py:645–849` 的真实 `run_registered_worker` 获得原 presence/lease，运行 heartbeat，`bind→invoke`（743–744）仍使用原 cancellation/deadline/current fence 检查。结果与 journal/状态处理未改；attempt finally 先结束并 join heartbeat，再取 `_active_final_ports` 调用其 close（825–830），清理本 lease 的 factory 并写 presence idle（831–837）；外 finally 继续清理原 held 并关闭 presence（845–849）。这是真实 Worker 的调用链源码核对，不是 fixture 或方法计数的运行证明。

相关停止源 SHA256：

| 模块 | SHA256 |
| --- | --- |
| current_final_evidence_service.py | cc3956af0ae7fc346622a61a4ed7f975c877bc790c12500dae2770c240a954b1 |
| current_final_evidence_runtime.py | 604327bb8e6ee51d1a30926bef58031a01e88c0f0927f5f0f36b0c079ff3783c |
| media_registration.py | 72ce559d18adb2bef283e3cb7fe9de4453f9c1ee3a173386601459286e483681 |
| worker.py | 219d91ecdfb25dbc3e3a167869da418c5ed330bc4896323dd28b8cf8304dd248 |
| affected_repair_service.py | 344c9ef354dbcd0563aed45c0990ecbbacdcbb5c9df8d0c7a199d825d5a4749a |
| component_diagnosis_service.py | 5e3efc3a0eb54d0c43d32a2737683032199e52c414035527b1f9891c8d997271 |
| diagnostic_selection.py | 2b05e9f36a92e85ed2a4826a51afcb14b384198d0f1dead1367e3def18ff1e0b |

未重新签署这些未变模块的全部业务语义；这里只核与本 finding 直接相关的原调用链。

## 尚未运行与下游检验

实际合法 A 首次 close→原同 lease/current factory 建立 B→B prepare/read/record/select→A 再 close 的 SQL/Worker 状态未测，B 首次和再次关闭的实际生命周期也未测。后续由原 Test 在明确准入后核真实原成员、原 factory 与 held 对象、原 key/fence/thread、拒绝后无错误删除；同时保原跨 Run/fence/thread/current 拒绝，不能为了制造阳性容许多个同时有效 port、移除 owner 门或吞 403。

本轮未提供实际 Owner、human confirmation、强 held resource、安装 qualification、Media 完整 factory/validator、模型/ASR/CTC 精度、两 authority、实际业务作品、三 OS 或 R1/R2 资格。0063 设计 DRC-P01、其他业务恢复与耗尽窗口另任务仍按原状态；没有用本单行修复关闭它们。

## 自有错误、工具和交接

原自有工具 179187 自然 exit 0，但有四个 formal 路径拼接的非终止读取错误，产生 null SHA/0bytes 和错误 matches；source_map Count 显示向量也不是 130。该原 InputBefore 已原样保存为 InputBefore-179187-Original.json，不能称该次 272 全绿。a78afc 保存错误后，f8674c 只纠正四个正式路径与计数，保留之前成功核出的 260 ordinary 身份及其余有效记录；修正后 272 有效，source 原件未变。这是本角色元数据错误，非产品失败，未美化工具输出。

本轮 source 读取、内存差异和有限身份工具均已真实返回；最后事实核对 f701b2 自然 exit 0，无 live handle。4813f2 完成唯一块重建，dfa936 完成 Worker/原 RLock 必要源码读取，f701b2 完成缺失 invoke 段与 272 条末核。之后仅保存自身评审文档及交接，不新读源码或执行目标。正式最终工具返回与读者释放由 FinalizerTerminal/FinalHandoff 另记，文件存在不代替工具终态。
