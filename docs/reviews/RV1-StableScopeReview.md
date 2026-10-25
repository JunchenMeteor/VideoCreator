# RV1 稳定范围独立评审

2026-10-08。永久评审角色；只读源码、规格、测试及过程证据，只写本报告和 Review 过程材料。未修改实现、测试、标准、锁文件或权限；未执行供应商、付费、支付、发布或部署操作，未读取真实密钥、.ssh 或 ValidationInstance。使用 senior-engineering-guardrails 作范围与证据约束；已授权的完整 RV1 审阅继续完成。

**结论：本批稳定身份与局部机制证据可进入下游；不能冻结整个技术 Gate、框架选择或产品完成。** T3 的 13/3/35 绿对应明确范围；W3 解决了原四反例；新增完整解析接缝已被 T4 免费实跑反证为 P1，媒体嵌套引用另保留 inspection。I3 是 Windows CLI/API 内部候选，F2 是浏览器开发接缝；均不等于完整桌面 App。最终验收由 AV 角色独立执行，本报告不代签。

## 1. 精确审阅范围

| 范围 | 身份 | 本评审核对 |
| --- | --- | --- |
| A1/B3/W3/F1 与 SDK 开发运行时 | bb597bf36054cc49aff3efa276399493fbd94622 | B3 18 源、W3 3 改源同时匹配提交 blob、handoff 与当前字节；其余依赖逐项对 T3 before/after |
| 内部 PyInstaller 引擎包 | 68c1f0699086382856f61c703f88c8b03b5d2547 | 从该提交提取的 35 文件、13 资源、全部 3432 产物独立逐项 hash 无差异，共 823233680 bytes |
| F2 唯一新前端源 | cea36dd71a1293b197264950b993e2f291eb5e7d | 8 前端源匹配交接与提交；只 engine.ts 较 F1 改变，其余 7 源保持 |
| 测试、标准、评审与任务材料 | commit 外各自 SHA | 不倒填为上述提交已包含；原测试与标准证据保持原范围 |

T3 当前依赖再次只读核 hash：23/23/33 项均匹配，各批运行时源变化与范围外变化均为 0。Generated SDK 的 4 个源及 3 个输出逐项匹配 generation.manifest。工作树中的 untracked tests/criteria/task-board/PROGRESS/BLOCKED 不是“产品源码与测试全已提交”的证据。完整身份见 RV1Snapshot.json，不能把当前 HEAD 或并发工作树视为全部已测冻结。

## 2. 标准范围批准与技术冻结

原 01—11 文档全部重读并核 SHA；21 FR、24 AC、11 MM、8 CM 与原批准范围保持。FR18 排除；FR05/FR10 与 FR17 的 R2 范围、CM 项及 R2 保留 R1 回归均不因机制测试通过而消失。标准四文件/BASELINE 原 SHA 保持，A1 ADR0002 的 SHA 为 96890611c77d8017b9f9d90d38a9bfa50cda0b6d4339789c97b36921c7b5d854。

ADR0002 只批准 scope/evidence；ADR0003 明确相同用例和账本比较，最终生产只留一个编排框架，未选定赢家；ADR0004 明确 staging 不等于可用 Asset、公开 Schema 唯一与实际资源纳管。该状态可独立冻结标准范围和证据规则，不得据此冻结尚未完成的 provider、作品、框架性能、多 OS 或商业测试结果。

官方 Provider 准入文档已把私人官网会员/Code API/开放平台 API/BYOK/本产品 official 分开；需允许的正式内嵌生成、查询、下载、成本/额度、商业使用权、TTL/删除与实例落盘证据。CapabilityRoute.verified 或官网插件页面不能替代该准入；Kimi 一次 401 不证明视觉/生成能力不支持。新的商业治理须显式定版，不能静默改写旧规格 SHA 或以后台未实现为完成。

## 3. 问题与归属

### RV1-P01：裸 JSON 与锁版 Crew 解析接缝（P1，T4 原源实际反证）

**触发：** response_model=None 下供应商返回完整裸 JSON；内容无控制标记，或合法脚本字面含 Action: 与 Action Input: / Final Answer:。react_protocol.py:14—18 将其完整识别为数据；85—98 只转义 JSON 字面 Final Answer:，start=0 时仍返回裸 JSON。controlled_llm.py:169—180 将其交 Crew；锁版 parser.py:92—103 在全字符串扫描 Final/Action，而非只解析数据外的控制。

**实际反证：** T4ParserOriginal 实际 exit1，6项中3红/3绿，37.035s；36源及范围外变化均0。普通裸 JSON 与含 Final 数据的裸 JSON 得到 OutputParserError；含合法 Action/Input 课程字面量的 JSON 得到 AgentAction，tool=demo 和，而不是 AgentFinish。这里确认错误分类，不声称错误工具已执行或真实多收费。原 plain-json 正例只断 validate_react_turn（test_w1_protocol_gate0.py:59—69）；新增测试真正执行 ControlledTextLLM→锁 parse，并核成功 final 的公开 CreativeProposal 解码值应保持。真 Action 参数的字面量保留、真实混合/伪 Observation 拒绝三项仍绿。

**归属/最小改法：** Agent媒体确认适配边界并保留真实原响应/usage；测试 T4 已保留原源实跑裸 JSON 三正例、真 Action 正例及混合反例；后续由归属角色最小修复，并用原红断言和35原回归验证。合法数据应保留解码值且不会作为控制；真 Action 应仍被执行，真实混合/自造 Observation 仍拒绝。不以硬调用 delegate 或新付费盲试伪通过。

**源身份：** react_protocol.py 48df4fcda9039b390448b4edb3bffda5511e256db223b86249b16a3b9d292865；controlled_llm.py 33ce7667ed2ddc6d301b2d54ebf5f3676e74022686f6bf347a943723f077b835。已交统筹、Agent媒体归属与 T4。原红 XML SHA 4dace629f81cc7ea5eff15f1b85c662a869b8d5fb567e9fdc5a05ede734927c1；CommandReceipt SHA 4c8afdbde6530b9cedc8fc5123665003cbf4571a2857f051cb620379e6f7911a；新增测试 SHA 0f959a440784abde83b06029eb9b150ddfcdca7a61fd51781cf55d5a62ee6ac5。未改原T3断言、未付费。

### RV1-I02：解码器嵌套引用范围（外部读取仍为 inspection；调用前拒绝反例已实跑）

**触发：** 上传本地 Staging 中的播放列表/带外部引用媒体。FFmpegRuntime._path 只保证入口路径在 staging；ffmpeg.py:96—99 ffprobe 与 124—142 decode 无输入协议/网络/嵌套引用范围约束。

**实际边界：** T4MediaOriginal 实跑4项3红1绿、exit1、5.652s，24源与范围外变化0；三个HLS/concat引用样本均进入 ffprobe，未在解码进程前拒绝。loopback GET=0，三个样本均 media_process_failed、无 Asset，staging 保持 ready；自产自包含 WAV 真实导入绿。该证据仅反证调用前拒绝机制，没有证明 SSRF 成功或目录外文件被读取，不作更强安全结论。XML SHA 344fb10a51e1e212c50112b1c8673dbbaf831b4f3abcbf999590b78aa72c19d0，CommandReceipt SHA 1b3000bf124a781883644cd40ed6c513ebbda4aa3f52efb26293b163645e78f8。固定 video/mp4/audio/wav MIME 推断属于已知 W4 待修范围，不以 T3 两格式绿外推图片或其他容器。

**归属/最小改法：** Agent媒体 W4 提供明确允许容器/输入协议或受控工具沙箱；T4 已在自建无秘密实例用自产沙箱标记素材与 loopback 免费取证；归属角色须明确并验证允许容器/协议及嵌套引用限制。尚未观测的外部读取仍保留 inspection；修后原政策反例及原真实 WAV/MP4 正例回归，不能只靠某个 malformed 样本失败证明完整沙箱。

### RV1-P02：候选过程脚本过度标记优雅停止（P2，源码已确认，生产生命周期仍未测）

ProbeEngineCandidate.py:120—123 发送 CTRL_BREAK_EVENT、wait 后直接置 graceful_shutdown=True，无应用 teardown 完成 marker。I3 本次两次实际 child exit3；终态 EngineCandidateProbe.json 已纠正为 null，明确端口关闭、句柄回收与实例重启持久，原 Raw/Attempt1 保留，未吞 exit3。这一纠正符合证据边界。

**归属/改法：** 集成只修自己的过程脚本，不改引擎也不重复探针；保存原脚本身份及本次原记录，使后续脚本默认 null/unknown，仅在真正停止完成证据成立时标 true。当前脚本 SHA c2ee13ef02d84ffd5fa507166a0041fb9bad037a3cd6c85df1c2bcb94a3ccd6e。不能把脚本状态 integration_probe_success、端口关闭或 Uvicorn SIGBREAK 源码推断等同桌面优雅退出。

## 4. 原问题的局部闭环

- **RV0 混合 Action/伪 Observation：** W3 ControlledTextLLM 实际发送并 hash 绑定 stop，非法回复原文及费用已落 Operation 后拒绝，相同输入不会再次网络提交；原七混合/inline 反例保留。原付费 Crew 三轮 delegation=0 仍失败，工具注册名误报正式撤回，不再沿错误展示名结论。
- **RV0 attempt/Ask/error 冒充真实委派：** AuditedDelegateTool 真实执行子任务，成功 call 须当前角色/已知成本；actual recorded model final 经公开 Schema 解析后与 Task 结果 canonical 精确相等（delegation_audit.py:139—167）；manager 最终 insight/candidates 必须精确复用专业产物（50—79）。T3 真实锁版工具调度的预设五响应正例为两个 completed，model-output-drift 原红变 failed；计数不再是完成依据。此处是机制闭环，不是模型自主质量通过。
- **RV0 首次迁移竞态：** Database 在 BEGIN IMMEDIATE writer transaction 内首次读 version、应用两个迁移并核版本，无 executescript 隐式提交；B2/T2 原源双进程红→当前 57 绿及 kill 恢复保留。当前 database.py SHA e0cdcd2ff82d882a4f1b04b18cc41d963cbe38b41bc4ffa51efff382897c11b4 与 B3/T3 保持。
- **B3 错误与媒体：** ErrorEnvelope→OpenAPI→生成 SDK 唯一来源；400 Host/Range 与416 text/plain、框架404/405 detail是明确边界。F2 只识别合法 JSON envelope 的 code/retryability/request_id，message/原 body 不反射，不自行重试。可信成对绝对本地工具、缺资源503保持同 ready staging；真实 probe/decode201才登记 Asset，坏媒体与同长度篡改仍拒绝。CLI 源码入口和迁移已纳入精确提交/包范围，旧 I1 缺源码问题不再套用到新候选。

## 5. 实际证据和命令范围

T3 CommandReceipt、JUnit 原文件 hash 与六普通可读副本均独立核对一致；副本 source/copy 的声明 hash 相同，不改 ACL，也不读取私有 pytest 路径。原断言两个测试文件 SHA 保持，四失败 testcase 名映射逐项保留；原红未覆盖。T4 后续六 parser 加四 media 共10份普通可读收据逐项匹配 original/copy声明哈希；副本 manifest SHA dfc8ee6c43914abeab601d5ab750e6977d1c968eecc50fd4240428346a7d0e6e，原响应及账本原文一致。

| 执行方与命令 | 实际结果 | 可证明范围 |
| --- | --- | --- |
| T3：pytest tests/gate0/test_b3_public_media_gate0.py -q | exit0，13/0/0/0，9.811s，23 依赖 | 公开错误、真实资源配置/CLI、自产1s WAV/MP4实际解码、鉴权Range/ETag、坏媒体/篡改 |
| T3：test_backend_gate0 三个 API/Asset/同长篡改节点 | exit0，3/0/0/0，14.365s，23 依赖 | 原 API/素材回归 |
| T3：test_w1_protocol_gate0.py + test_controlled_llm_gate0.py | exit0，35/0/0/0，78.013s，33 依赖 | 免费 MockTransport、锁版真实工具调度、故障接缝；非自主模型作品 |
| I3：python -X utf8 -m PyInstaller … Engine.spec | BuildReceipt 实际exit0，3432 文件/823233680 bytes | Windows onedir 内部 CLI/framework/media 候选；不含隔离ASR解释器/模型、Tauri shell或安装器 |
| I3：固定 exe serve --data-dir 中文空格实例 --port0 | 13 检查；ready1.548s/restart1.176s，child两次exit3 | 鉴权/UTF8持久/实际视频 decode201/Range206恰64bytes/v2迁移；无 worker/provider；未证明优雅退出 |
| F2：pnpm typecheck + build:workbench | owner实跑exit0，Vite1.31s | 8 前端源构建、自查保护预览和错误 UI；非独立性能/生命周期/作品验收 |

完整参数、UTC、退出码、before/after、范围外监控见 COMMANDS 与 T3Handoff.json；本评审没有重跑或自编验收测试。T3 保留 111 Crew 与 1 Starlette 弃用 warning；13 工具历史自测不重跑、不累计作业务项。I3 3432 产物全 hash 核对仅证明包身份；GPL-3.0 二进制及 OFL 字体许可证实际随包，manifest 明确内部候选，正式源码/notice/发行义务未完成，不批准发行。

## 6. 仍须下游完成

完整自主洞察→方案→模型协作→视听制作→Bundle/export/reference、API/MCP持续链、interactive指导修订与 unattended、同输入 Crew/LG公平对照、未知收费跨重启恢复与作品消费仍须独立实测。当前 worker_connected=false 的开发UI应继续显示队列/真实空结果。

F2 的原 WAV 同 staging import201、哈希与实际播放时钟可读；音频工具明确不支持输入，未听过中文语音，听懂度/音色/混音/音画同步仍 pending。测试信号和彩条不是 AC03 三个真实生成动画镜头；ASR不替代 forced alignment。F2 React卸载、键盘/性能、完整独立前端测试仍待 T/AV。

Windows MSVC/UAC、桌面IPC/退出/干净机器安装；macOS/Linux 实机安装；official生成准入、商户/订阅权益/计费幂等、额度、两平台授权发布回执与商业条款仍缺实际资源或授权。缺凭证/支付沙箱/OS机不能计成功，不把技术或预算不足包装为已通过。后续新源码必须另固定 hash 与原反例回归，不能自动继承本批绿。

交 RV1Handoff.json 给统筹、架构、集成、测试和 AV。范围评审完成，新增 P1 解析反证待修复及原断言回归，媒体调用前政策反例已实跑，外部读取与隔离充分性仍无证明；Gate0/R1/R2 均未签署通过。
