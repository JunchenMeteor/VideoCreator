# SourceScopeAndLocatorCorrection 独立复审

状态：SOURCE_REVIEW_FINAL。本次分别将 RMCP-P01、RMCP-P02、QECP-P01 限定为 CLOSED_SOURCE_STATIC_ONLY；未确认新增 P1/P2。结论针对以下两个停止候选集及原具体反例，不授应用、候选执行、安装、资源资格或完整 R1/R2 验收。

## 固定范围与独立方法

活动任务卡为 G:/开发测试/Projects/VideoCreator/docs/task-board/SourceScopeAndLocatorCorrectionIndependentRecheck.md，3662 bytes，SHA-256 fc7bb7f3d3d3bf852579260b4369384e3d69a315965751b5948b8fa751435330。本次规则全文身份：工作区 AGENTS 8738 bytes / af69f90a45d8b3ed80bc9b5e2cc4243ac8e2cc6f53785aa28ae2d423f93a17ec；仓库 AGENTS 6658 bytes / 6de878f514b02788f8af5ba512f71c56bb053f6800d76cf19f3cdd955b7f6a0d。

独立固定 349 个唯一实际路径，包含 Integration 三对完整源码、56 个原索引声明材料及正式交接、Backend 137 修前与 137 候选普通源码、原 finding 和必要规则。Backend 两集合的 repo key 完全一致，只有 qualification_coverage.py 改动，136 件相同。没有据 source_path 读取生产热源，也没有重新扫描完整运行环境。InputBefore.json SHA-256 50b84c026330340da214891f1978d0a605602a65035da90b1276882773397f85；InputAfter.json SHA-256 463bc97466f979b59b43e3607d8b0d82032317a284382ceb4a190449dee5ed90，349 路径 differences=[]。

逐个原 hunk 用 ordinal 文本上下文匹配，在内存重建完整候选 UTF-8/LF 字节并比较大小及完整 SHA。四项结果均 byte_exact=true：Inventory 4 hunks / +57 -7；Stage 4 hunks / +71 -12；Collector 0 hunk / +0 -0；Backend coverage 1 hunk / +9 -0。保存 DiffReconstruction.json，4052 bytes，SHA-256 b75cbe0ecdb47b12b92a28fbbe94a2762ae6752af927a4da81d2e6c9b1fd8465。此为源码字节重建，没有执行候选、抽取函数、parser、测试或目标 import。

## Integration：RMCP-P01

唯一停止源根 G:/开发测试/Codex/VideoCreatorImplementation/Integration/RuntimeMetadataAndStageLocatorCorrection/SourcePreparationRevisionTwo/；before 在 OriginalSources，候选在 CandidateSources。EngineResourceInventory.py before 20413 bytes / 3090f70a5530e07f21bb18b6f6facdc34f0a8c4b391065d141da3e765dcc746f；候选 24092 bytes / 8c7b5680546668252c4681f035bea1257a5912661046bf06319fd65fdb38ecf3。完整原 256 行和新 306 行已读；合并输出遗漏的 235–255 行另行定向补齐。

原问题是 payload walk 跳过 __pycache__、.pyc、.pyo，同一过滤结果又作 grammar 成员集合：未知缓存可以逃过成员比较。新 walk 第 9–21 行仍服务原 payload 语义；完整 grammar 检查另用 whole_grammar_members 第 43–65 行，没有依赖过滤后集合。

新检查先在第 46–49 行逐个核根及所有父目录的 lstat，拒绝 link/reparse 和非目录；第 50–64 行完整枚举所有目录与文件，包含隐藏成员和空目录，拒绝重复物理目录、特殊对象及不安全原始 locator。遇到任意 __pycache__ 路径段或 .pyc/.pyo 是拒绝而非跳过。第 143–155 行核声明 file 的原字符串、缓存声明、大小写重复及完整父目录集合，再将完整实际 file+directory 集合逐值比较，并核每件大小和 SHA。第 156–166 行 packaging 路径和 import 位于这些门之后。

因此原额外缓存/未知目录反例在源码控制流中不能继续到原 packaging import，合法声明的普通成员保留原大小/SHA与加载顺序。RMCP-P01 在此完整新候选上 CLOSED_SOURCE_STATIC_ONLY。没有实际候选导入、Windows loader、缓存文件拒绝运行或原子无 TOCTOU 证明。

## Integration：RMCP-P02

BuildPortableEngineStage.py before 8666 bytes / 115b2ce363c6663565a6549986d48b0bb27224a542f2baaf2222fd17c2f4299e；候选 13039 bytes / 37a7227c9cb8baac81089dd109ddcec26de96d1baf7eb4f1a4b84824d5592fc1。完整原 78 行及新 137 行已读。

原 locator 先经 PurePosixPath 归一后遗漏 Windows drive absolute 语义，C:/Outside 等字符串可进入 inventory；stage root / relative 在 Windows 上可被右侧绝对路径替代，原第一写入前没有完整包含关系门。

新 Inventory 第 23–34 行、Stage 第 9–27 行对原始字符串先作闭集检查：拒绝空值、反斜杠、冒号/drive/UNC/absolute/root、空/点/父目录段、重复分隔、尾点空格、控制/代理字符、特殊字符及设备别名，拒绝归一后变化。Inventory add 第 118–130 行在第 119 行先核 locator，再收集 source/hash/output。允许 payload 根保持 Code、Migrations、Fonts、Runtime/Python 与 LocalAsr 指定子目录；内部 generated=True 的四个 manifest 例外没有开放给普通输入计划。

Stage 第 29–50 行检查完整根链、root 的物理身份以及 lexical/resolved containment，并对已存在目的文件和父目录拒绝 link/reparse/非正常类型。第 52–55 行每次 mkdir 前后重新检查。第 64–68 行将新的 staging 根限定为原 owner 的直接子目录，核完整 owner 链与原始根名，拒绝 lexists 包括 dangling 对象。第 70–75 行所有 inventory locator、大小写重复、file-parent 冲突均先于第 81 行首个创建/保存动作；空间预算第 76–77 行保留。

实际 copy 第 87–92 行在 source 和 destination 检查后进行，保存原 source SHA/大小、目标 SHA/大小和 source-after 核。原 _pth/METADATA/WHEEL、ASR 索引、Engine 和 Installation manifests 在第 96–123 行均走有界 prepare_destination；LocalAsr 两个索引名纳入完整闭集。原 installation not_admitted、qualification=false、mode、Code 根、空间上限、异常 exit1 和最终保存门保持。

因此原 C:/Outside、路径归一别名和链接父目录反例在新的源链中有明确先写门。RMCP-P02 CLOSED_SOURCE_STATIC_ONLY；没有执行实际 copy/mkdir、Windows reparse 替换、故障注入或真实安装。多次路径观察仍不等于持有原对象的原子 OS 安全证明。

## Collector 与 Integration 保护范围

BindQualifiedCompletionDependencies.py 两侧完整 29007 bytes / 507 行，SHA-256 均 e7c600a4c3ec4e2a03011c9fca9e702bd6b7088a54c6e9bb7713beb09964b5ba；全文分两批读取，重建确认零改动。

原 stdlib 闭包、whole-file 成员和停止 source SHA、count/size/deadline、源前后检查保留。第 70–82 行 RECORD 相对路径严格原值处理仍在；第 85–100 行 Requires-Dist 仅名字级 join 并保留 markers/version NOT_EVALUATED，不冒充目标环境选择。第 349–373 行有 License-File 时要求 Metadata-Version 2.4，且完整声明文件必须来自唯一 RECORD/SHA 与实际材料关系；legal_admission=false 没有放宽。第 390–410 行全 raw 条件枝并不表示当前 Windows 必需依赖已经满足。静态 PE/DLL 和数量不代表 runtime ABI；47 缺材料与 Scripts/.pth 实际加载、许可证及分发权仍待原 owner。

正式 Integration 身份：FormalStage/Handoff.md 3017 bytes / fcca58288eab029378e987a97b744d3ca294c91ac628eb5d93a47f2e9274497d；Handoff.json 7131 bytes / 12520cff0354b56dd2119072d07678a52396662960a9aaaa83c447863fee46d6；SourcePreparationRevisionTwo/SourceIndex.json 2876 bytes / 6e633ddda339dffd82d18da7db5eb239d63684eb086fd3fbf4f752fa2054c464；Full.diff 19077 bytes / d12cc969fe708f697626b3156ede1b5bb215620bfe5467c00b96a589f2fec8e5。Interfaces.md 5561 bytes / 653711a3353585a44dfd94ac1080bf60e4a1a745233e13458aa5131b26e7f5fe；BoundaryRequirements.md 2651 bytes / bf17ab86de11766cec4ad848d48b9e8a0eec58599c357ecd6a50977a6e4a3215，后者是建议，不是已执行测试标准。

原 MetadataPreparationRoundOne 收据 878 bytes / 167061d29b52d9366574e27e1ed562533cd9a123304c34faca609aaa03527bc0：child 3380，creation 2026-10-11T10:01:54.0564465Z，自然 0、双 EOF、19 inputs 无变化。RevisionTwo 890 bytes / e0b0d950788d6c223b9b2ea51c003c58af2813d8505b2d5f4ee31aea7e47c403：child 10508，creation 2026-10-11T10:03:50.7313923Z，自然 0、双 EOF、19 无变化。二者仅作者自身文本组装/两项 stdlib AST，未执行上述候选。首稿两处 LocalAsr generated 闭集遗漏经源读发现，原稿与 dd39b1 记录保留，不改称已运行候选绿。

## Backend：QECP-P01

唯一根 G:/开发测试/Codex/VideoCreatorImplementation/Backend/QualificationNegativeEffectsScopeCorrection/；原 SourceBefore 与 CandidateSources 各 137 件。qualification_coverage.py before 22594 bytes / 309701109142b8d3e1bb8c8099197da4b616b4c90f3e37310e58a32cf9b172e6；候选 23343 bytes / d5611b66e91d7fb6dc66206820176f413b39ef152ed1a19ac272225eb8e72ec6。

完整新 363 行和 9 行插入 patch 已独立核。_negative 第 221–266 行保留原三 header/request、签名、实际 observed/assert_current 原 session/seq/correlation、变更/撤销/过期拒绝、完整 effects 前后相等、非空错误以及 driver_entries=0。新增第 237–245 行把 typed request.body.identity 作为实际作用域：old/new/tried 三个实例均须等于 request 的 instance；两个 effects 的 production_id、run_id 须分别等于 request P/R；每个 before/after Step.run_id 也须相同。失败走原第 21–22 行 EngineError 422 / resource_evidence_invalid。

真实共同消费者不是作者列举：verify_qualification_execution_set 第 269–273 行在第 271 行用此 _negative；verify_resource_coverage 第 283–363 行在第 344 行同样用它。完整类型 qualification_execution.py（094c2ac8ba6729d9c9d180b82a77958b6780a09c9474d6e8903ccae054837acc）保留 Identity、Step、Effects 原闭字段/排序唯一、group 成组空值与 raw frame/session/current 联结。故合法结构但异 instance、P/R 或 Step Run 的原静态反例现在经过两个实际消费者都会拒绝，未改费用、预算、current 或响应 body。QECP-P01 CLOSED_SOURCE_STATIC_ONLY。

必要原 capture/export 来源 application/qualification_execution_capture.py 21541 bytes / 20d4bb03bb2edb70c3fba2437d6347a73c329fce342c99c1fd27c8b6a25f8df3 未改。第 240–256 行从真实 lease Run/原 canonical key/body 取 Step/document；persist writer 第 259–318 行保持同 service/input/lease/member 和前后 writer guard，第 267–268 行合法 immutable replay 保存原回执，Operation 查询同 Run，identity 来源实际 instance/P/R/Op。export 第 321–340 行核 member/kind/ref/body SHA，不存在时原 503 保留。没有用新九行生成阳性或 fake exporter，也未执行 SQLite。

空数组、签名、typed body 和这些额外等式不能单独证明完整负面 effects 捕获；原 actual 同范围 exporter、完整 native frame、费用 unknown、actual issuer/installer/Owner/H+C 和 producer 源门仍保持未实现/未验证边界。

Backend 正式身份：Handoff.md 1204 bytes / f3fbb54482f60a48d79bc294400a4bd834b99a6c0effd6fa50e9cf5574d581d6；JSON 2435 bytes / b3d42d5a13646e9f3ad7d7ed24149bf617ccff276720327e667ccbd8a5a7b875；SourceIndex.json 85467 bytes / 387d1ca695e8a76b449dfc539455e17676501ffcde1b9d4fbda42b4af4281c84；BeforeSourceIndex.json 84083 bytes / 3980a6a694e78ff77950007e09f5f44a6c213f32d4e1350caa7c4798f1739462；FullProposal.patch 1547 bytes / 31e72ac0ca105b883ffbba48acb6f17d757611ff85373bf9ca048907d6f07ade；ActualInterfaces.md 1745 bytes / aa6e17ef447739ea82daa53835811a1ae63d8111556e19d5b0911323d89c2577。作者 AST/metadata 自然 0 只是准备证据，没有实际 Pydantic、SQL 或负面运行。

## 应用与后继责任

Integration 原 owner 须先确认真实当前基线与完整候选一致，再按独立任务提交对应两个脚本；Review 不应用。后续独立 Test 应核 extra cache、隐藏/空目录、原 drive/UNC/dot/alias/reparse/special、正确合法路径和写入前拒绝，保原 SHA/source-after/资源上限，不用过滤集合求绿。

Backend 137 是未应用的完整候选基线。本阶段九行只供后继完整候选保留，不能直接套到不同仓库基线；应随真实 producer/exporter、installer/H+C 和完整报告合同闭合后另行评审及授权。负面 Test 必须覆盖两个消费者、三实例、双 effects P/R、每个 Step Run、完整原 frame 与 unknown/费用保护。合法 immutable replay及实际拒绝不能为求绿削掉。

原 RMCP 两 finding、QECP-P01 和全部首稿/旧失败字节未覆写。old19 已耗尽，31 NOT_READY、无实际第三方/候选运行、完整安装/媒体/真实 Owner/API/native/三 OS 及完整 R1 后 R2 均未由此关闭。

## 自有读取错误与终态

3b61d6 的父级 InputIndex 简称定位失败保留，PowerShell 继续读其他已固定件，不能说此调用无 error；后据 FormalStage 精确位置补读。a4c309 合并输出截断保留，235–255 行已用 17a706 定向补齐。5978c6 自然 1 为旧 rg 可执行入口不存在，正文已经读取；ccf0fd 据当前 Get-Command 入口定向补类型缺段和停止 source 搜索，未安装工具或改变目标环境。661c4f 将 OrderedDictionary 用 Select-Object 显示四个 null 行，仅投影错误，实际保存重建 JSON 完整；b01625 全文补读，未重跑目标。

末输入核 94271d 自然 0 / no live，349 differences=[]；封存前自身材料核 3f78d7、9630b9 均自然 0 / no live。全部 source reader 已停止；正式写入实际自然返回与最终读写释放见独立 FinalizerTerminal.json 和最终交接消息，不从文件存在预言当前工具终态。本任务没有产品执行、候选函数执行、SQL/OS/native故障、安装、网络、模型、费用或秘密操作。
