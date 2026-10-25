# I61 首个 wheel 检查失败独立评审

结论：**首失败的直接归属为 Integration 自有检查器的大小写兼容策略；I61-AR-P01 / P2 / OPEN**。原代码明确拒绝原包的 `Root-Is-Purelib: True`，不能仅凭这一大小写差异诊断上游包损坏。缓存官方规范支持布尔语义；对大小写兼容的建议属于明确标注的实现推断，不能扩展成整个 jsonref wheel 合规、安装可用或其余产物通过。本评审未运行检查器、产品、安装或获取请求，不阻塞 I62。

## 固定来源与身份

过程根：[ArtifactInspectionReview-I61](G:/开发测试/Codex/VideoCreatorImplementation/Review/ArtifactInspectionReview-I61/ArtifactInspectionSnapshot.json)。先全文读取 Diagnostic、ClosureExecutionHandoff MD/JSON；从正式 ordinary index 的 entries 取得原检查器、首失败收据及五完成结果。定向检查10份 ordinary 及对应原件，全数 size/SHA 一致；合计31项有限输入，末核无变更。

| 输入 | SHA-256 |
| --- | --- |
| 原 Diagnostic | c2d324abf3d7936a289655417294fc6b95c1cc047a7f946b308f0cd90a86160c |
| ClosureExecutionHandoff.md | 3b3a317c820f8fa6ae038d85a6b794c57ab6bd5b47c5639d7cbccb13956c3817 |
| ClosureExecutionHandoff.json | 9c6db055e73e943d22133388968aba83d7e73ac3ee05b0971907bcd5529d7f1e |
| ordinary index | c238a234164eb5ebc1111a617821a39746883a0f058e8e5fcf28644ea1dfb5d7 |
| 原 InspectProductionArtifacts.py | 48e6c6e8dc4691086ca895be0e80f62ca14e6dcaf4eacd5aaa594550c904738c |
| 原 CommandReceipt | 7b3320ee3cef9f0dc010d41eef8359b073633116052f72499da63004a7b04c28 |
| 原 ArtifactInspectionReceipt | e9f683bc8951b80046441bb7683ba85ed425474f3f99a35eaa23bf984c42b95e |
| jsonref-1.1.0-py3-none-any.whl / 9425B | 590dc7773df6c21cbf948b5dac07a72a251db28b0238ceecce0a2abfa8ec30a9 |
| 原官方规范缓存 JSON | 3ab3d9a9098c070f17828c25e0a4ac5b036a08cc79f65af04e8397b17184d975 |

检查器固定普通路径：[InspectProductionArtifacts.py](G:/开发测试/Codex/VideoCreatorImplementation/Integration/KimiOfflineWheelsAndGraph-I61/ProductionArtifactClosureExecutionOrdinary/InspectProductionArtifacts.py:910)。本评审将完整源码作为数据解析 AST，并完整读取相干 headers、one_header、inspect_wheel、main 调用链，未 import/call 它。

## 原字节与真实失败链

从原 Diagnostic 唯一指定 wheel 只读两个成员，未提取、重写包或导入 vendor。原 WHEEL 四行是版本1.0、pdm-pep517生成信息、纯库值 True、py3-none-any tag。87B 的 WHEEL SHA为 `fcb0c1aa980854534766fbc53866e0da9bc938436ae911c0c93e69c7e1de5f45`；2722B METADATA SHA为 `f98db3890394fba23912faab86ad8f70ed564fc8c885298b636b270f28453e43`；两者与原 Diagnostic 完整匹配。这只是两成员数据/身份核对，不是重跑原整个 ZIP/RECORD/许可证检查。

headers（681–697）只把字段名转为小写，保留字段值；one_header（848–854）要求唯一字段。inspect_wheel 在文件名/METADATA身份判断之后，于910检查版本是否等于1.0以及纯库值是否属于小写 true/false。原 Version1.0 通过该比较，而唯一原值 True 不属于该集合，911抛出原 ValueError。没有字符串缺失、重复字段、下载身份失败的证据支持改变该直接归属。

main（1095–1107）逐包调用 inspect_wheel；第六件抛出后1104–1107不会保存该件结果，1110–1111保存错误，1129–1132保留退出1。原 receipt 确有同名错误与五件 Inspection000–004，并与这五份原普通结果逐 SHA/size 对齐。第六件没有完成结果；后续 tag（912–916）、Requires-Python/依赖（917–924）、RECORD（925）、native与license（926–936）不能借本评审宣布完成。

## 缓存规范的真实来源与边界

真正缓存为 [RecordSpecification.json](G:/开发测试/Codex/VideoCreatorImplementation/Integration/KimiOfflineWheelsAndGraph-I61/BuilderRecordResearchRoundThree/.firecrawl/RecordSpecification.json)，26872B；来源 [PyPA Binary distribution format](https://packaging.python.org/en/latest/specifications/binary-distribution-format/)。metadata含来源 URL、status200、scrapeID `01a122c8-b153-706a-8fc8-4c51f51cdc27`，与原 research CommandReceipt 的同一 URL、`-o` 路径及 stderr scrapeID 对齐。

原同轮 stdout 实际0B，是保存选项的输出形态；不能拿空 stdout 声称规范获取失败，也不能把它当正文。原缓存 markdown21399字符已作为数据读取；其213–250行包含 WHEEL key:value格式、小写示例和该字段决定 purelib/platlib 安装路由的说明，32–43行也给出安装步骤。这些段落**没有明确排他大小写词法，也没有直接声明值大小写不敏感**。

因此本评审区分事实和推断：原失败确定来自自有小写集合；以布尔语义、非排他示例和原观察值推断，首个后继修正应兼容明确的布尔大小写，而不是重写上游包。缓存规范没有单独替全部包提供有效性证明；本报告不声称它明文保证任意大小写或所有其他字段。

## I61-AR-P01：纯库布尔字段过窄拦截 / P2

**归属：Integration。触发：**有效下载身份、唯一 Root-Is-Purelib 字段且原值 True、版本1.0、身份前置检查已到达；固定910拒绝并终止整个逐包数据检查。**影响：**当前自有检查策略将可表达纯库布尔含义的实际产物挡在后续数据核验之前；现有证据不能把责任转给上游，也不能通过忽略错误使剩余检查变绿。优先级是候选数据闭包流程的 P2，不是已运行产品/安装漏洞。

**最小后继建议：**只修改唯一 purity 字段的比较，显式映射布尔文本的大小写到 true/false，再限制为这两种语义。保留 raw wheel_headers，不使用一般字符串 truthiness、不设缺失默认false、不接受 yes/no/1/0/空值，不顺手宽放 Wheel-Version、字段唯一性、身份、tags、RECORD、native、许可、输入及原生命周期门。建议采用仅对该字段的 ASCII布尔规范化；case兼容策略和预期需写入新版本，不改原 wheel/旧结果或原检查器冻结身份。

**应由归属者另批验证：**小写 true/false及原大写 True/False得到相同明确布尔语义；原 jsonref固定包应到达后续检查，是否整包通过由实际新批决定；重复/缺失字段、空/未知文本、坏 Wheel-Version、tag不一致、坏 RECORD、坏许可引用仍按各原门拒绝。至少一个合法大小写但故意坏后续字段的反例证明新策略没有提前宣布成功。仅做数据夹具/原缓存，不新增 GET、安装、vendor执行或费用。本评审不实现这些修正，也没有执行上述预期验证。

## 原批终态与未测保持

原整体工具29d298/session87392 →9365c0自然1。原 Acquisition21296 / creation2026-10-10T00:31:12.8100557Z自然0，Inspection5512 / creation00:32:02.9149014Z自然1；各原进程双 byte EOF、无timeout/force/观察错误，与正式交接和原 CommandReceipt逐值一致。下载0不能洗成检查0。

134wheel加1sdist的候选清单只有前五件保存了完整检查结果；剩余129件wheel包含失败的第六件和128件尚未进入检查，另1件sdist未检查。五个完成结果也不授 ABI/MinOS/发行权或安装资格。原获取的135 exactGET、剩余元数据闭包、全部RECORD/许可/标签/安装、三OS、SDK/Owner/媒体、Gate0/R1/R2都不能从本片获通过。125条原 after记录只按已保存收据保留，本评审未对所有环境/包重新扫描。

自身评审最初8cc06d把索引按 records/members寻找，打印0项；后9b3d15按真实 entries56纠正，仅定位材料，不是原产品/检查器失败。本片证据与源均未修改。正式事实详见 [ArtifactInspectionFacts.json](G:/开发测试/Codex/VideoCreatorImplementation/Review/ArtifactInspectionReview-I61/ArtifactInspectionFacts.json)。末输入无漂移、原读者已释放、live[]，无需等待I62或后继修复。完整R1独立验收后连续完整R2的目标保持。
