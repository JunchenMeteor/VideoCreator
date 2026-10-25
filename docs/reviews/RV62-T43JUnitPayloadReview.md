# RV62：T43 共用 JUnit writer 有限独立评审

**RV60-I01 在新共用 writer 的 XML1.0 编码与本次纯格式样本范围内有限关闭。** 固定源码与原运行证据支持八份新 XML 严格解析/正文/计数正确，原两个非法 XML expected-red 保持；旧冻结 T40/T42 runner 没有接入此库。另有 **RV62-I01 / P3 / Test：稀疏数组导致声明数与节点数不一致**，属 SOURCE_STATIC，未执行反例，不改本批八正常样本通过结果。

## 固定身份与实际范围

正式根：`G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/JUnitPayload-T43/`；ordinary 根：`G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T43JUnitPayload/`。Manifest 的 31 个普通副本均与其原身份 bytes/SHA 匹配；六历史件、正式治理/原工具终态、必要库源码等共 **45 路径**，末次输入核无变化。Review 只读固定实现/测试/已存在 XML 与 raw，使用自身 stdlib 解析已有 artifact，未执行 writer、Test、UI、产品、数据库、网络或模型，未读 B29/current SDK 或扫描整个环境。

| 固定件 | SHA-256 |
|---|---|
| T43Handoff.md | 8c3259daba9f5e98b45ce2c2ecb54a8b3204d262ec2f9168a85c11a63f788203 |
| T43Handoff.json | 2b7cb048c77f3006de8e24391a5047e713c75bae7767c06a24edb65d2fbab2fe |
| T43OrdinaryManifest.json | 8d72e7e2008860709ad2ad19d187294891f8e64c8bb961f8bb441ede21a44fc4 |
| 共用 junitXml.mjs（1952 bytes） | c513fc129dc9685dc65dd44fe29adf40ce2b9b617f3ac9900c1060fd619c165c |
| WriterProbeT43.mjs | c82d8a9ab674cf427014db3cc5257c66fc85f0a821005aff45ee61da036d9055 |
| ParseProbeT43.py | 65421aace637746e80be37a2fcc9cc7cef6838621d0d0186578489e253c68db6 |
| RunT43.ps1 | 2157264186c3a2a3343cde1b894e247d555f1455600f60eca73885876116db30 |
| 原 CommandReceipt | 74e6cc4c86bf756ebe5642d596b81b9d730865ee60f110ad9cce29e3c1bcac56 |
| 原 ParserReceipt | d5fcc4faa5d6cb1b098d357016543f2ae5882f540b60fcb8e6b4031cfef555d7 |
| 原 T43MainToolTerminal | f0af21283636bc0c213bc0d03c384bc432ecc66d42fadbdf4e7daeeab0a4cbd7 |

## 编码修正与独立 oracle

`tools/testing/junitXml.mjs:2–14` 按 JavaScript Unicode 码点遍历，XML1.0 禁用码点输出可读的字面 `\uXXXX`，不静默删除。TAB/LF/CR 输出字符引用，避免 attribute 正规化损失；合法 BMP/补充字符、C1、中文保留，XML 元字符作实体。孤立 surrogate、FFFE/FFFF 转义，合法 surrogate pair 保留。原 raw/OriginalPayloads JSON 另外保存，因此可读 XML 不冒充原字符字节。

原 WriterProbe 真 import 共用库；七个单 failure 样本加六节点 mixed 构成八份报告、共 13 个 testcase 节点。字面 expected 是手写内容/计数，并未调用 escapeXml10 再制造期望。原 CPython ElementTree 逐 suite/name、节点/tag/text/count 检查。本 Review 从独立字面期望再次解析**已有**八 XML，核全部正文、节点计数及 duration：单项 0.125，mixed 1–6。

八样本覆盖 ANSI ESC、NUL/禁用控制字符、合法 TAB/LF/CR text/attribute、中文/emoji/C1、XML 元字符、surrogate pair/noncharacters、孤立 surrogate、mixed 状态计数。mixed 精确为 tests=6/failures=2/errors=2/skipped=1；没有删除失败/error/skip 节点来求绿。现有代码对显式未知 outcome、非有限/负 duration 抛 TypeError；原 InvalidShape 检查实际覆盖 unknown outcome 和 NaN，不扩称所有非法形状均已实测。

原标准 parser 的 10 检查为八新报告通过与两 expected-red。合成旧编码 ANSI XML 的 ParseError 为 line1/column65；原 T40 XML 仍 line3/column0，原件 SHA `9d8e994cd6b84f700299b46bc4fe35a64f7628ec770c7cf9d1a604d52402a3dd`、9485 bytes、两个原 ESC 均保持。OriginalANSI.raw 25 bytes、SHA `ca4f620f9faea36fbaea9a01ca04516644f81dac9db040f19232d293d2f93d93`，与保存原 payload UTF-8 bytes 一致。旧失败没有重写为合法 XML 或绿结果。

## RV62-I01：稀疏数组可绕过逐项检查（P3，Test）

**固定源**：`G:/开发测试/Projects/VideoCreator/tools/testing/junitXml.mjs`，SHA `c513fc129dc9685dc65dd44fe29adf40ce2b9b617f3ac9900c1060fd619c165c`；同字节 ordinary 为 `G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T43JUnitPayload/SourceBodies/junitXml.mjs`。

**触发/调用链**：`renderJUnit({name:'s', cases:new Array(1)})` 是合法 Array，19 行仅 Array.isArray 可通过；20 行把 `cases.length` 记 tests=1；21 行 Array.map 跳过缺失索引，22–23 行 outcome/duration 验证不被执行；30 行 nodes.join 输出零 testcase，failures/errors/skipped 仍 0。这会生成声明已包含一项却没有该项节点的报告。

**边界/影响**：静态 JavaScript 语义推演，未运行 Node 反例，没有实际旧 runner 或本批数据触发证据。八个现有密集数组样本保持通过。共用库将用于后续报告入口，因此在采用 renderJUnit 前应补形状检查，不能凭当前 InvalidShape 名称宣称稀疏情况已经拒绝。

**最小整改与独立验证**：Test 唯一 writer 应在输出前逐索引确认密集数组/完整 item，或者按索引遍历并拒绝不存在的 item；不能只把 tests 改成已输出数而静默丢 missing 项。后续新批保固定旧 T43，真实验证单 hole/混合 hole 拒绝、显式 unknown outcome/坏 duration 仍拒绝、密集 mixed 的独立节点/计数与正文均保持。Review 不代改实现或期望。

## 原真实终态及范围限制

原唯一工具 `185aa6` actual exit=0，无 yield/session/replay。Writer PID48512，creation `2026-10-09T12:44:02.0898154Z`；Parser PID2308，creation `2026-10-09T12:44:02.4105064Z`。原 launch、terminal、CommandReceipt 和原 stdout 相干：两原 Process 自然 exit=0、stdout/stderr 双 byte EOF、forced=false、errors=[]；原 stderr 各为空。Node 原 stdout 声明八文档/九本地检查；Parser 原 stdout 为十检查/八新文档/两 expected-red。27 原输入 before/after 向量逐值保持，本 Review 仅有限核六历史件及必要源码，不另盘点这些运行时 DLL/解释器的完整发行资格。

runner 从原 Process.Start 起保同对象、原 BaseStream 到独立 raw 文件，并在 finally 等实际 terminal/两个泵 EOF；30 秒持柄强制分支未触发，本批不授 timeout/OS/Job 保证。未运行 UI、46 React 重跑、SDK、API、媒体或 ASR。T40 NOTPASS 与 T42 原 46 绿及其 raw/source/结果保持六件 hash；旧入口既未 import escapeXml10 也未替换原 escape。**RV60-I01 有限关闭只适用于新库编码和本批纯格式验证，旧入口现状与原红照实保留。**

自身首次显示 OriginalPayloads 时 ensure_ascii=False 遇孤立 surrogate，7bd9df exit=1；仅改自身控制台 JSON 转义并保记录，6a07dc 和已有 artifact 解析 1c08ea 实际 exit=0。不是产品/Test 红或原证据修改。

全 R1 三 OS 独立验收→连续 R2 目标、原所有失败及授权边界不变；本报告不是业务/OS/native/RuntimeBinding/Gate 资格。

## 自有正式证据

Snapshot：`G:/开发测试/Codex/VideoCreatorImplementation/Review/JUnitPayload-RV62/RV62Snapshot.json`，SHA `a8d750823eac89969ac336a8290ed0485b40deaa48029e1e9b81701981f51989`。

FactsCheck：`G:/开发测试/Codex/VideoCreatorImplementation/Review/JUnitPayload-RV62/RV62FactsCheck.json`，SHA `edfbfeebe4c43fe5afea5052e986d7944ef8281894ccdbefb6c0a5e8c12c0fa6`。

InputAfter：`G:/开发测试/Codex/VideoCreatorImplementation/Review/JUnitPayload-RV62/RV62InputAfter.json`，45/45 无变化，SHA `929152f20b93ecfa037c3df7a2dff4a4bc129bda7661d81ecec6c9bac246183f`。

全部 source reader 释放、live=[]，最后固定证据解析 1c08ea actual exit=0；最终写入只本有限报告/交接。
