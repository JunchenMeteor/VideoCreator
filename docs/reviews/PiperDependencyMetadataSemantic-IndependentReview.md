# Piper 六归档依赖元数据表示比较：独立源码评审

结论：比较器的限定表示边界有源码支持，原归档安全门未降；存在一项 P2 收尾错误传播问题 PDM-P01，OPEN_SOURCE_STATIC，归 Integration。当前候选没有运行、案例没有执行；本报告不给后继执行或安装资格。

## 固定版本与完整输入

- 任务卡 `PiperDependencyMetadataSemanticIndependentReview.md`：39e44e73abbb9e6a63832a7cb282a0a340c8e06c45cd0e53813b7fd46d75d7c1。卡正文的 QUEUED 是原治理状态，实际激活来自本轮原角色分派，不修改已 pin 卡。
- 正式源根：`G:/开发测试/Codex/VideoCreatorImplementation/Integration/PiperDependencyMetadataSemanticPreparation/SourcePreparationStage`。Handoff.md 24d02497196bfb2d4a8fc36bf1806c1f00661533f36266707359b5e87ad08ed7；Handoff.json f229ab326ce65988b687240e7111f59660813d7cb7e80bf2f31a7598e5ebf344；OrdinaryIndex.json af948c8695a1301c01ef7c0b40eb36d920658d1c82edea29eb02ba6fe574d14e。
- 四停止源：Plan 55240B／292edfd85fd5fe08c5a4cfed501f2b1dfdf92ac8db26584c81eaf07e75a10327；helper 37505B／85446bdb3783653d1b5fa997848d59c778ba6f95ea4eda6515092d0f90146143；parser 14205B／9eae0ad968c464189810a62e0ecf2579a2dc5ef11de1fc6dd3b523e3018ac382；runner 8896B／9fd3b5af423e2f3505c843bd5acb7a60763ca95c85a54812f388649884bdb24d。实际审读普通副本 Input071、Input099、Input100 及停止 Plan。
- 105 索引条目是 99 普通副本与 6 保留原工具二进制；独立核每份声明 source/copy 的完整 bytes/SHA 与 102 Plan 输入，differences=[]。工具二进制仅哈希，没有运行。末核 312 次记录／209 个精确不同路径无漂移；不宣称全环境盘点。
- 108619B SemanticSourceRevisionTwo.diff，954d15491d26d4de00c2dace93e42018134f9a78d4e96d6d9ab6000ab069263e，完整三段逐 hunk 在内存复原，对旧 helper／旧 runner／新 parser 的上下文、删除行和新完整文件均 exact。没有 apply diff。Plan 是独立完整冻结 JSON，不伪称其内容在上述三段 source diff 内。

本轮全文读 335 行 parser、725 行 helper、89 行 runner 与完整 Plan JSON；完整包装参考 `_parser.py`／`_tokenizer.py` 语法链及 specifiers 的语法常量和构造验证已核。三个参考文件完整原 bytes/SHA 固定，未导入包装器或范围求解器；specifiers 其余版本范围计算不作为本比较器资格。完整 diff 复原另见 StaticFacts.json。

## 独立语义判断

保存的 PyPI 完整 JSON 原件由实际字段重新核数：tqdm 8、huggingfacehub 109、pyyaml 0、tokenizers 12、typer 4、safetensors 36，总计 169 条 Requires-Dist。每份 saved raw 顺序与 Plan.expected_raw_requires_dist 相同。此核查没有打开/解压归档；不据此声称实际 wheel 新比较已成功。

Parser 241–304 保存 name、ordered extras、direct URL、每个 operator 与精确版本 operand；只把逗号版本 conjunction 排序，重复约束不删除，版本外括号记录为原格式。307–335 按每条 index/raw/representation 完整保存并进行多重集比较，重复行不删除。原 raw_multiset 与表示比较分别报告。name/extras/operand 值和大小写保持精确，不借规范化扩大允许等价范围；这比一般包语义等价更窄。

177–239 的 marker 是 typed literal/variable 比较节点与顺序 sequence，显式括号 group 保留；and/or、变量、operator、左右 operand、字符串内空格均不丢失。不交换 operand、不重排布尔式、不折叠 grouping、不求 marker 真值、不激活 extras、不解版本范围。syntax error/unknown variable/缺括号/缺 operand/不支持的 escape 不能落入 equality；4096 行、16384 UTF8 bytes/row、64 depth、1024 nodes 与 8MiB 完整输出边界均在源码中。

SPECIFIER_PATTERN 来自固定 specifiers.py 247–337；AST 常量初次逐字不相等，进一步独立确认差异仅字符串外沿缩进，`.strip()` 后原字符串 exact。没有编译或运行该模式。这一来源核对不是 26 个提议案例通过的结果。现语法明确拒绝未支持形式，不宣称普遍 PEP508/PEP440 语义兼容。

Helper 555–594 核完整同 release JSON 的 bytes/SHA、唯一 artifact URL/size/SHA/yanked=false，保 original/saved/actual/Plan raw 与 parse errors，保存新比较记录后拒绝错误/表示不等/Plan 原行变化。583–586 要求原 tokenizers 旧字面失败证据仍 false，且两份原 raw 列表分别与当前来源完全相同，不能用表示结果覆盖旧红。

## 原安全门与生命周期

独立 AST 对照旧 helper：20 个原顶层定义完整 AST 相同，仅 compare_saved_release 改动。parse_zip／zip_extra／verify_record／headers／native_pe／inspect_one／main 等原 bytes、CRC、EOCD/EOF、成员名单和大小/SHA、RECORD 完整覆盖、WHEEL tag/purity/name/version、原 source/NOTICE/native-static 门保持；六项计划仍逐份执行，first error 停止后续，非通过占位。

单归档 compressed 36700160B、entries 20000、单成员 134217728B、expanded 536870912B、ratio 2000、RECORD 16777216B、METADATA/WHEEL 2097152B、完整 original text views 16777216B 保持。保存的 release JSON 用 exact size+SHA 专门读取，tokenizers 2457274B 与 safetensors 2021773B 没有误套 1MiB 通用 JSON 读取上限。ZIP64 支持仅原明确冗余 local 布局，未靠跳 CRC/RECORD 放宽归档。

独立入口的 argv/cwd/exclusive namespace、固定 Plan SHA、102 前后 hash、startup absent 状态、清环境、原单 Process/PID/creation、两条原始 byte stream、900s sticky 超时/不 kill/不重放保持。迟于 deadline 的自然结束仍失败。不可把 runtime module metadata/frozen __file__ 或已缓存 pyc 字段当 loaded-source/OS/ABI 证明。

PDM-P01 是本次已确认例外：新 runner 78→83→85→86→88–89 允许最后 SaveOwner 首次失败后保持 actual_exit=0；11 catch 只 ErrorRecord。终态保存失败发生在最后 errors 检查之后。条件是其余执行/保存/输入检查均成功、只有最后保存异常；没有故障注入或 OS 复现。旧 Input005 同分支，属于继承缺口，不能改原失败批消除它。固定完整 Finding 见自有过程 Finding-PDM-P01.md；只修新入口，使最后收据保存失败保持首异常且不能成功退出，不以旧收据/重跑/清 errors 消除。后继故障 oracle 需由 Test 单独固定，这里不授执行。

## 原失败、许可及未运行界限

原 DataInspectionRoundOne CommandReceipt 1f2442a687ab39751599ae7ec102db520130275a073a33e5afb2a16f6d36ff41 与 InspectionReceipt 314d24f91df77b45c83473510a3d4d73cf804d24001837033689d6ac7bd07b19 独立读原字段：owner 1；PID41752/creation 2026-10-10T19:25:39.9776401Z，child natural1、双 byteEOF、timeout=false。tqdm/huggingfacehub/pyyaml 原 PASS_DATA_ONLY；tokenizers 原 FAILED_FIRST_ERROR_PRESERVED，typer/safetensors 原 NOT_EXECUTED。历史 12 原行写法差异/原 actual124c3e/1 不重分类，不说新 parser 已证它们等价。

原 c6271d/1 是 PinFile 对整个对象而非 input.path 的准备错误，separate child NOT_STARTED、archive/parser/case NOT_EXECUTED；旧 partial Plan 保留。RevisionTwo 自己的路径/名字修订不能回填原结果。

固定原 LICENSE／LICENSE.BSD／LICENSE.APACHE 原正文和语法来源 SHA 已核，parser 顶部有修改声明与来源。仅证明来源材料保存；不授各依赖 native 对应源码、整包再分发或模型资源许可。26 条 PlannedRepresentationCases 全文仅是建议，Integration 入口不读或执行它们；Test 还需独立案例源码/期望/冻结/后续批准。

候选 parser、26 cases、归档检查/安装、vendor/product/SQL/native/HTTP、模型、ASR、费用、密钥读取均为 0。归档数据检查、ABI、TTS/模型/资源权利、真实安装与完整 R1→连续 R2 仍未验收。原旧 19 目标第三次限制不因本任务重置。

## 评审过程与交接

自己的初次脚本 60007b/1 因六条 retained tool 的 ordinary=null 读取错误终止，纠正只评审脚本后 9b8c68/0；不是产品/候选失败。7cca0b 与 7e481b 输出有截断，未当完整阅读；实际所缺 source/案例/许可段按固定路径补读。259822 常量逐字不等记录保留，后续仅 outer-whitespace 的来源事实另写，不擦原结果。未以这些 own 解析差异修实现、执行候选或批准运行。

有限证据在 `G:/开发测试/Codex/VideoCreatorImplementation/Review/PiperDependencyMetadataSemanticIndependentReview`：InputBefore/After、StaticFacts、SourceASTComparison、FinalFacts、Finding-PDM-P01 和正式 Handoff。所有源码/普通副本读者在有限末核后释放；artifact writer 自然返回情况由最终实际工具结果交接，不凭文件存在宣告完成。本报告是 SOURCE_STATIC_ONLY，有一项 P2 OPEN，不签 Gate/安装/作品/R1/R2。
