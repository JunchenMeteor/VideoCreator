# ADR0017：0.3 单作品独立参考材料准入

2026-10-08。批准以下唯一增量作为 B11 实施输入，不批准真实参考、authority、方法资格或产品通过。不读活跃生产源码、不运行产品/测试、不联网/安装/读凭证/收费；A14 native 另卡处理。完整 R1 自动路径、R1 后连续 R2 保持。

来源为 A15 卡 SHA24dc104f4ab7f46ab3ae7146b9bb2b444cfcb423bf7234613cef9bc831819ec7、完整 B11/ReferenceAdmissionRequest.md SHAa0510dec60d193f13a22bb8d9be10fb270b5ddb4fbdaed8cd69b83ea09a54d62，以及 ADR0015 SHA869d8943f092c2f169353b2550264d416a61506b58ef02083c3f2b417d6b28ff、ADR0016 SHAa517af8c75e3b58381c895d2069de96216b3b5985b727d840ee9e330ca109a26。

## 1 唯一类型和严格分派

新增独立 schema_kind=`precision_reference_v03`；唯一文档类型 `PerWorkReferenceDocument`，Manifest artifact role=`precision_reference`。0.3 的 `(manifest_version, role, schema_kind)` 精确组合分派到此类型；`precision_report_v03` 仍仅解析真正 `PrecisionEvaluationReportV03`，不增加 reference/report union，不凭字段存在或 scope 猜测类型。

scope 相同不代表材料相同：参考、测量报告均使用 Literal `per_work_reference_measurement`，但一个是独立边界依据，一个是复算结果；`method_benchmark` 只能是 `capability_benchmark`，不能替参考。旧 0.2 precision_reference 的 audit_summary grammar、默认、hash 与原字节不变；不把旧文件自动转成新可信参考。未知版本、错 kind/role、混合 grammar、缺字段/多余字段按原公开错误契约严格拒绝。

批准 B11 文档的字段集合，并固定歧义：

| 字段 | 必须语义 |
| --- | --- |
| schema_version / evaluation_scope | 分别为 `0.3.0-candidate`、`per_work_reference_measurement` 的 Literal |
| report_id | 保留既有 EvidenceReportRef 的标识名称，语义为参考文档 ID，不赋测量报告身份；scope、版本、实际 hash 与索引 kind 同时核对 |
| input_audio_sha256 | 实际受评原输入音轨的字节 SHA；在本 run/request 的准备记录解析唯一音轨身份/版本、完整解码/时基与范围，不能仅接受调用方一个 hash 或拿 mix/源稿代替 |
| units | 非空、完整、有序的 transcript_unit_id 声明列表，不另存一套预测边界；逐项严格 ID、唯一性核查后再建 map |
| boundaries | 非空 PrecisionReferenceUnit 列表：transcript_unit_id + reference_range。与 units 及实际固定 Transcript 全单位集合一一对应；原列表重复/缺损/多出/坏范围先拒绝，不靠去重修好 |
| authority_ref / issuer | 固定可信 authority revision/hash 与公开 issuer ID；由本地 registry 核其当前状态、适用范围及签发能力，不能从正文 approved 字段得信任 |
| independent_listener_refs | 非空、可解析的不可变监听/标注材料引用，含真实文档身份、版本及 SHA；仅一串 SHA 无法定位正文，不满足完整核验 |
| arbitration_ref | 实际裁决记录的不可变引用。无争议也须有明确无争议及最终完整单位集的审核事实，不能填一个不存在的占位文件 |
| signature | `{algorithm: HMAC-SHA256, key_id, digest}`；key_id/issuer 为公开定位，秘密不在材料中 |
| content_sha256 | 下述内部签名记录 hash；不是文件 MaterialReceipt 的 hash |

reference_range 延用原音轨本征坐标：整数微秒、半开区间；与真实时基、非零原 PTS 及已有坐标映射核对，不以视频/字幕毫秒坐标直接替代。完整人口与原 max 起终误差、N 单位 nearest-rank、200000us 判据保持；本卡不批准缩集合、词级准入或 MM05 变动。

## 2 签名只能认证声明，不能制造独立性

批准 HMAC-SHA256 为本机受控 issuer 的认证形式，不是公开可验证签名或 OS 权限隔离证明。使用后端既定 canonical JSON 和严格重复键/非有限数规则：签名输入为移除 signature/content_sha256 后的完整 canonical 正文；content_sha256 为移除自身字段、保留 signature 的完整 canonical 记录 SHA。实际完整 JSON 文件另由 ready Receipt 计算 SHA，并用于 EvidenceReportRef/Manifest；三者不可混用。不排除 units、音轨、监听/裁决引用、issuer/authority 等真实字段来规避 hash。

签名/核验能力只由可信安装配置及后端构造注入：issuer 必须明确获准签发该 scope 的独立参考声明，覆盖对应 criterion、音轨/作品及监听来源范围，状态/有效期/撤销均核对。普通 launcher、Production/API/MCP、模型或通用签任何 JSON 的 callback 不获此能力。参考 issuer 不因此获得安装 policy、批准 benchmark/method qualification 或注册 authority 的权限。

HMAC 只证明“持有受信 key 的 issuer 声明了这些字节”。真正参考准入还须核实际音轨、全 units、可得监听材料/人员身份/标注工具及独立性、争议裁决和独立批准事实；不能从被评 ASR/Alignment 复制边界后由同一流程自签。缺真实资源或可信根保持 pending/拒绝，不能制造 positive。发布前在 ADR0016 的受控 registry/fence 次序中再核撤销；签名从未替代实际证据或测量复算。

## 3 完整引用与无环组装

参考制作先绑定实际输入音轨、固定 Transcript 单位身份及已完成监听/裁决证据 → 固定参考正文/签名/ready Receipt → 取得带实际完整文件 SHA 的 reference_ref → 按 ADR0016 预分配无未来 SHA 的测量 report locator → 固定 Alignment → 实际复算测量报告 → WorkValidation/Quality → Manifest 索引及发布。

参考不得依赖未来 Alignment、其 precision、测量报告或 Quality 的 SHA；监听/裁决文件不得反引尚未生成参考的 SHA。先分配公开 reference ID 可在来源记录中标示关联，但不是 future hash 或授权票据。来源身份/坐标的引用与边界独立性分别核验：使用实际 Transcript 的 ID 绑定不会授权复制其预测时间。Allocation 仍无未来 SHA/size，不当作 ready Receipt；材料只落一次不可变字节。

reference_ref 指向 `precision_reference` role + `precision_reference_v03` kind 的实际材料；measurement_report_locator 最终只能绑定 `precision_report_v03` 的真实测量报告。报告绑定音轨、Alignment 和参考的实际身份/hash，核验完整集后复算 N/max-boundary；不能只验证签名便接收媒体传来的 passed/P95。

已有 qualified-method runtime 的无本片参考路径完全保持：assessment=not_measured，reference_ref/sample_count/p95/measurement_report_locator 全 null，不创建 reference/report placeholder、不要求每片人工标注。真正 strict/per-work 测量缺参考仍 alignment_required/waiting_user，不用 benchmark 代替或偷偷换策略。

## 4 导出、导入和信任

完整测量证据的 artifact 索引必须包含参考正文、实际测量报告及必要监听/裁决证据的真实引用闭包，含许可/来源身份。音轨/Transcript/Alignment 按原包索引身份关联；包内引用可解析、hash 一致且无环。监听或参考含私人信息时按真实披露/再分发许可决定，hash 和签名不自动授导出权。

需要完整 per-work 证明的默认交付/投影，缺必要正文或许可就拒该完整证明导出/等待权限；不能删掉证据却称闭包齐全。原作品另作已获准的媒体/文本投影仍按 ADR0016 保留父包身份与证据取得限制，显式不是完整测量证明，不改原包字节、不新造已核验参考。benchmark 的 provenance_reference 模式不自动扩展为本片独立 reference 的可替代物。

导入严格按版本/kind/role、内容/文件 hash、全单位/时基、引用闭包分派并保留 origin 字节；HMAC 无本地同一可信 issuer/key 时只能留作来源认证声明，不可公开验证或自动 recognized。默认 `origin_snapshot_only`，即使签名可核也仍须本地 registry 核相同授权范围、实际证据可得性及当前撤销状态；外来 issuer/key/authority 不能从导入包自行安装。导出不得携 HMAC secret，监听/裁决引用不能携本机绝对路径或秘密。

合法既有作品读取与新的生产资格分开：缺信任/证据可得性时保留 origin 和准确限制，不把 origin 已发布改成“本地已独立测量”，也不授新任务参考/算法能力。

## 5 唯一后续负责者

- 后端：在自身 B11 实施独立类型/kind、精确 role dispatch、受控 `PersistentEvidenceRegistry.verify_work_reference(reference)`、两种 hash 与签名验证及完整证据闭包；检查真实准备音轨/Transcript、发布权限和 revocation。先固定消费签名，再交媒体/集成；只继续自身被分派路径，本文不持其生产读锁。
- Test：准备实际标准/用例增量，区分 reference/report/benchmark、错误 grammar、伪监听/越权 issuer、重复/缺损/坏 range、签名及两种 hash 混用、来源循环/缺许可、origin 不授本地资格、自动 null 路径。真实资源未配不能只用 synthetic authority 冒正向。Review 独立批准实际 criteria 后才能据此运行，本 ADR 不代标准审批。
- 媒体：消费后端固定类型与 Allocation/Receipt；可产真实音轨/ASR/Alignment及测量输入，不自行制造独立听审/authority；不改 registry/DTO/账本/测试。
- 集成：仅从后端实际源重生 contracts/SDK；新 kind 在解析/导出索引生成中显式存在，不修改旧默认或封装 synthetic 资格。无需本卡联网、安装或改 native 方案。

当前真实参考、监听/裁决、authority、方法基准与产品 Gate0 仍未批准。全读取终态后固定交接并释放，不等待其他实现批，不扩 A14。
