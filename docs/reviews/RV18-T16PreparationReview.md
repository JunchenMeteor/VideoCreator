# RV18 — T16 0.3 标准与准备材料独立评审

结论：**批准本轮固定 0.3 标准及纯断言准备范围；不批准运行 adapter 准入，不授予真实产品/测试启动许可。** `not_ready_for_execution` 保留。RV18-P01 为静态 P2，归 Test 原 owner；未运行反例，不将它称作真实产品失败。完整目标仍为 Gate0 → R1 独立验收 → 连续 R2，本轮不签 Gate、R1、MM05 或基准 authority。

## 1. 固定身份与审批边界

| 固定对象 | SHA-256 | 本轮判断 |
| --- | --- | --- |
| 新 criterion JSON | b3944783e8420ac742bfd55ea875d1f52109163efeef5c22fdb2f2ce72de2d20 | APPROVED_CRITERION_REVISION1_ONLY |
| 新 criterion Markdown | 340514bfd9fb8b5bb126056f3143fd16d1bf725cc516a5465e005a50e9f55048 | APPROVED_CRITERION_REVISION1_ONLY |
| T16CasePlanRevisionOne | a6376d4bb782fc927c7303febae4ac9551677de91164bd23cf1a94a69f9306d6 | APPROVED_PLANNED_COVERAGE_ONLY，58 项均未执行 |
| t16_assertions.py | 5abfc8ebad117c9df64831c082dac27d3a3683d4b5d3d252c51dbcf0aa2d66d4 | APPROVED_PLAIN_ASSERTION_PREPARATION_ONLY |
| t16_preparation_sanity.py | 323e9947b866242c8e8e8eb7a5e8b9456e8ee2c8e499ad94367c37b2c3e9201d | 六项纯 sanity 源与历史收据可支持准备机制 |
| T16FixtureManifestRevisionOne | 6e7629974ccbec03b6db4618449a1ee2b6340d753c939388c34cbb56c3625586 | 身份库存已核，不整体批准其 runtime adapter |
| t16_guard.py | 11f7e2b1958662e9bfeeeb019dfa9918c5278f8da2a2febf240ee627b5d10657 | NOT_APPROVED_RUNTIME_GUARD |
| t16_business_adapter.py | 6cf1bc25eb67e335770cffd9833e0be0e71c77116ac73ca1b48880a73cc4b543 | NOT_APPROVED_RUNTIME_ADAPTER |

正式 T16 Handoff：JSON a5e7c282a3c962cd8e4d30c9af209f3286a2a75bf82b710e59a5912e1925d2e2 / Markdown 3e83e7f264d8ff2c8e9eec4efa9efa72e383493f2f561c64f096ccfdf5beb991。27 普通副本均与声明身份匹配，CopiesManifest 4e9c06f8e230b36320edf0d8f66a72ebdcd7c02420cd396453691e5bd2f67d29。六份消费 Test 正文、副本及 before/after 身份全部匹配。正文归档明确是本轮纯 Test 运行后保存的同 hash 正文，不能充作未来产品 import 前完整源码归档，也不回填 T14 历史缺口。

ADR0015 869d8943f092c2f169353b2550264d416a61506b58ef02083c3f2b417d6b28ff 与 ADR0016 a517af8c75e3b58381c895d2069de96216b3b5985b727d840ee9e330ca109a26 已按冻结正文阅读。未读取 B11/F3 当前业务实现，未要求其停止写入。

## 2. 标准可批准的理由

旧 criterion JSON 40afb746a669df341adc815491bc9e8d5962038591241081149931ddb6d43ecb、Markdown 6546e6ad8383f9e2c01bb48fb3ef9a23b1ac629b3de6ce665cfef22296ab23a0 与旧 fixture manifest 8365c21f4af6e1ea5a6d367f66d778ee53c83ebd4416f96b0f9e4767fb470c30 的当前固定字节保持原 SHA。新 criterion.inherited38、计划.inherited38_unchanged 与 RV17 固定旧 cases 的 38 项全部字段值及顺序相等；新 20 项 criterion 与计划亦逐值相等。原红、绿和旧错误报告保留；未运行新的 58 个业务场景。

0.3 显式版本及可信实例/项目预授权允许只有目标和资料的自动制作；不要求每片人工标注参考。旧请求默认/旧 body/hash/幂等比较不隐式改版。三种 scope 正确区分：独立 capability benchmark、本片 runtime validation、本片有独立参考时的 measurement。无本片参考时 status=not_measured，N/P95/reference/measurement locator 全 null，实际 measurement 附件为空；不能借基准分数、confidence 或两个模型的一致性冒本片测量。

有独立参考的评估保留每单元 max(start,end) 误差、全部 N 个唯一单元、nearest-rank ceil(95*N/100)、200000μs 门槛；先核所有单元合法性/重复/完整覆盖，再建映射。候选明确区分 10 单元一次 300ms 错误的正确 P95=300000 与错误 2N 算法的 0；旧报告不能用于新版本发布。词级门与独立标注听审仍未获准。

新增 20 场景覆盖可信资格与实际模型/资源/计算/OS 匹配、issuer/expiry/revoke、执行与发布同 writer 撤销顺序、旧 registry 重放/备份、持久 Allocation 与普通 lease/fence、无未来 SHA/size 和无环组装、基准许可与实际引用闭包、origin 原字节/本地信任分离、schema4→5 同事务迁移与完整备份/旧程序拒5、真实 API/MCP及整包运行核验。批准的是判据及计划；registry 竞争、迁移、真实文件闭包、跨 OS 等还没有本轮实际观察或合格正向资料。

## 3. RV18-P01 — 导入前依赖身份守卫在导入后才拒绝（P2，OPEN）

归属：Test 原 owner。固定源码：t16_business_adapter.py 6cf1…，第21–28行；t16_guard.py 11f7…，第40–56行。仅静态源码链，未构造、import 或执行产品反例。

触发推演：授权 admission 的 source map 未列目标 bundles 模块或缺必要依赖，但其所声明的 source/body 项均匹配（两项批准 flag 与 archive-completed 声明已设置）。admit_runtime 只遍历所声明的 map，未先验证该 adapter 所需闭包非空且包含目标。ServiceAdapter 在第23行执行 import_module("video_creator.application.bundles")，第26–28行才按 module.__file__ 检查目标是否已归档，因此实际顺序是产品 import → 身份缺项拒绝。普通路径范围/hash 校验与最后的 boolean 声明不能把拒绝移到 import 前。传入 service 本身也已由外部构造，不能据此证明首次产品 import 之前完成了正文归档。

影响：不能批准这版“缺身份时在 import 前拒绝”的 runtime 准入守卫。不是已证实的公开攻击、真实未授权服务启动或生产漏洞；本轮完全没有调用它。当前无 runtime 授权，所以不存在因本轮审批而执行该分支。

修复建议：由 Test 在无产品 import 的阶段，先基于冻结 adapter/宿主绑定验证必需非空 source/resource 闭包、目标模块规范路径、实际文件及对应 prelaunch 正文；再由已准入的 bootstrap 构造服务。拒绝缺目标/缺正文/缺资源/空闭包应发生在任何生产 import 或构造前；不得以补 flags、事后 module.__file__ 或假 service 替代。原候选保留，新版本由原 owner 固定后独立复审。修复不要求现在读取 B11 或运行真实服务。

## 4. RV18-I01 — 完整消费签名与 0.3 bootstrap 未发布（准备阻断，非调用失败）

实际 ServiceAdapter 共13 wrappers。固定 B9ServiceConsumption d0cc81974125f4e239725ff500943540dc74f3c93dfb198e6d2c3813e712f6a2 与 B9Interfaces 0d2c15920b2738506ad410a7e4986c097c664c05a52b113d5de7b7767b35c30b，可核 context 和六 producer 的文档参数次序：prepare/stage_material/read_material/verify/publish/recover_preparation。其调用直接传原参数/返回原结果，不造第二 DTO 或私有 SQL。

其余六方法 request_export/export_status/import_bundle/import_status/content/semantic_page 在固定 B9 文档仅有名字或首参 AccessContext，没有完整签名。尤其 adapter 将 content 的 purpose、semantic_page 的 cursor/limit 按位置参数传递；不能根据文档推断它们是否为 keyword-only。本轮未证调用失败，也不能批准全部13精确兼容。后续唯一正式冻结接口和 fixture bootstrap 交给 Test 绑定新版本，不能以 B11 未来签名倒证旧 B9 身份。

HTTP adapter 只针对自己隔离实例的 loopback/凭证、无代理/跳转、有界原响应读；本轮 HTTP 请求0，工厂不算宿主。MCP 使用安装 SDK 的真实 stdio 接缝，但 final host binding 未发布就 NotReady；本轮宿主调用0，不将注册 handler 冒充 IPC。0.3 唯一 DTO/registry/producer/bootstrap、真实完整资源和独立资格/语料均未 ready，planned commands 不构成启动许可。

## 5. 六项 sanity 与未测边界

只读历史 Receipt ab26996617b64b0ec6370c8452183f78804e8391b95e219ef0c7ea8e480b3116、stdout 和源码：6 passed /0 failure/error/skip，exit0，0.000614699994912371s；原 stdout 为 Ran6tests in0.001s。七项运行 scope 的 before/after map 完全相等，六份 Test 正文与两个时点匹配。它验证纯断言的数学/非法单元/null/Allocation/无环等准备逻辑，没有实例化 ServiceAdapter，无真实业务、API、MCP、ASR、解码或DB调用。

Reviewer 本轮产品/测试运行、网络、安装、费用、key 读取均0；所有工具终态，无 live handle。没有生产 freeze。独立标注听审 authority、30×60 基准、MM05、真实全包、registry 并发/故障、schema5迁移/回退、跨OS/计算资源资格仍未测/未就绪。既有产品恢复问题及所有 Gate 完成条件不因这轮标准批准而关闭。

有限事实与冻结正文见自身 Review/RV18FactsCheck.json、RV18Snapshot.json。原 owner 按最多三轮修订具体准备缺口，本轮结束，不等待活跃生产，也不扩大旧历史审计。
