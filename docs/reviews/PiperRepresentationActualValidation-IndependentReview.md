# Piper 首次实际 87 项表示比较 — 独立限定结果评审

结论：LIMITED_COMPONENT_PASS。本固定版本完整比较器的 87 个 outer case、每项实际 Result、Summary、PartialResults、JUnit，以及 93 份实际 Python JSON 输出互相对应。未确认新的 P1/P2 阻断。此结论只支持限定表示语法、比较和本批 JSON 写入，不批准下一次运行，不代表六归档、PDM 收据故障、TTS、安装、Owner、native、真实作品或三 OS 通过；完整 R1 后连续 R2 未验收。

评审只用停止普通副本和原执行资料，自身 PowerShell/.NET 读取 JSON/XML/字节，没有执行候选、parser、87、fixture、vendor 或产品，没有重新扫描或复制 runtime。

固定任务卡为 G:/开发测试/Projects/VideoCreator/docs/task-board/PiperRepresentationActualValidationIndependentReview.md，SHA256 c81730b92030584ff354107b1ef2874ee3ac2e479cd847ab8af2bf91d53ed6d1。工作区和仓库 AGENTS 已全文读取。正式根为 G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/PiperDependencyRepresentationActualValidation/；正式 ExecutionHandoff.md 的 SHA 为 3540e9b127a73e062e89d7527fb16c9c2deb2aa365c81b09c800c693642e2fbc，JSON 为 b640a191a513951080d0995603f38ba8794d9c4a8e57fd970c138d9ff09213e0。SourceStage/OrdinaryIndex.json 为 846ac142a13384d94b11c55412c672b211214bd89c0f497a5fcfce4736fd5800。125 份普通副本各自实际大小、SHA 与索引及原件声明一致。原 134 个有限输入前后无漂移；另行保存 1 份原投影历史补充，不回填原 Before。没有将 999 runtime 声明变为本次独立全环境读取。

以下源码和结果路径均在上述 SourceStage/Ordinary/ 下；完整映射在本评审 InputBefore.json，逐项检查在 ActualArtifactFacts.json：

| 固定入口或标准 | SHA256 | 实际读审范围 |
| --- | --- | --- |
| Input100-RunRepresentation.ps1 | cf9b189554c51b697ac9a07d51f21732f67830217b2010acf6cb82589537abfa | 全文 1–176 |
| Input101-ProbeRepresentation.py | d065f669787e2f8b10b8cec0f66a68b97507acc5a4b3a0a3f356a24a41356af2 | 全文 1–353 |
| Input122-RequirementRepresentation.py | 9eae0ad968c464189810a62e0ecf2579a2dc5ef11de1fc6dd3b523e3018ac382 | 全文 1–335 |
| Input102-RepresentationCases.json | 8dd5dc91509f19ef92cf5628bf2a1072291068ecd2f827d9e83b70b6b42014e0 | 全文手写 54+20+11+2 |
| Input103-IndependentOracle.md | c19887589b67231c080aba0496a684bbfdfd1602dd822b4b2ffd096a4fd9f82b | 全文；未从被测 parser 反填期望 |
| Input104-RepresentationInputIndex.json | eebc3fde031942f040df11628c43c358e6c40a3b8b20b2e49f2579f3d5c62d3d | 原 607402 字节；解析 1041/364 声明和工具绑定，不逐个重读 runtime |
| Input077-Summary.json | 2393343d677ca5e6379466048bb8ef20dfa165f4eff6b9537142779011f1d507 | 全部 87 ID、状态、duration 和 input-after |
| Input020-JUnit.xml | 6b00141be19f80ff7f1c71fda509074a15c0ec5c5befcf6a8b501855b9283f24 | 全部 87 node，XML 与 JSON 范围分开 |

原 Run 的 -ExpectedInputIndex 值与实际 index SHA 相同。Input003-LaunchReceipt.json 给出真实 argv：原固定 Python，-I -S -B -X utf8、原 Probe 完整路径、原 index 完整路径及上述 SHA；cwd 为原 PiperRepresentationFutureJsonLfCorrection。没有暗中换解释器、工作目录或候选。原 request/runtime_approved=false 字节保持，实际执行依据是 Input125 中 Root 独立一次激活，不把历史 request 改为授权。

原进程与输入终态核对

Input001-CommandReceipt.json，SHA 060968191ec7bb2d4eb19ad1fc9398890f874a7f44b5c7fc6ba4fc512a5c191c，记录同 child PID 2900、creation UTC ticks 639272836379344527、actual_exit=0、natural_terminal=true、forced=false、双 byte EOF、errors=[]。Input004/005 原 stderr/stdout 副本各为 0 字节，SHA 为标准空文件 e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855。其身份与 LaunchReceipt 相同。Run 89–124 从一次成功 Process.Start 后持原 Process/creation/handle，双 raw CopyToAsync；126–175 持原对象等待、双 pump 完成、独立 actual index 与全部 members 末核、错误 sticky exit 1。本次没有强制停止或错误，不能据正常批推未知结束及 save 故障已实测。

原 MainToolTerminal.json 的 SHA f15775285229cacd0cf29031787e3e82125b23d1048f1a0562659c0e71e1680f，保留原 7480cf/session20578→d3d095 actual 0、无重启。其 VoidTaskResult 文本属于工具输出，不是 child raw 或通过依据。外层 OS PID/creation 没有独立捕获，限度保留。

InputBefore 记录 1041；Input019 及 Summary 内 input-after 均有 index-after 和 records-after true、errors=[]，原完整 index 路径/607402B/SHA 前后相同。源码 Probe 44–58、318–333 与 Run 48–59、155–171 分别从实际 index 路径重读，与外部固定期望比较，另核原 records；不是缓存旧 bool 后直接宣末核。本评审独立重核的是 125 普通副本和有限控制输入，不复扫原 999 runtime。

实际模块与覆盖核对

Input006 记录 CPython 3.13.16、cpython-313、原 T26 InterpreterBodies executable/prefix/base_prefix、isolated=1、no_site=1、optimization=0、dont_write_bytecode=true，与冻结 index binding 一致。Probe 61–75 核真实启动属性，270–277 用 spec_from_file_location/module_from_spec/exec_module 加载原完整模块并保存 origin/SHA；Input021 实际源 SHA 为 9eae0ad9…，whole_module=true、extracted_functions=false。全文 source 及真实结果支持这个完整模块调用链，没有 AST 抽函数或 shadow parser；它不等于安装资格或完整 DLL 来源证明。

逐项 ID 顺序为 R01–R54、V01–V20、B01–B11、T01-12、T_CHANGED，共 87 唯一项。冻结 Cases、实际 Summary、PartialResults、JUnit 及 87 单项 Result 均同序且完整，无残差；JUnit 87 tests / 0 failure / 0 error / 0 skip，Summary 87 pass / 0 failure / 0 error / 0 NOT_EXECUTED。87 个 case duration 与各 XML time 数值一致。Summary suite duration 为 2.4660431999946013 秒，各 case duration 合计 1.7791788998874836 秒，两者不同计时范围，不把前者称独立 wall-clock 或强行相等。

各模式不只计数：compare 的 literal/representation、无 marker truth、无 extras activation、无 version range resolution、duplicates、具体 parse-error 个数和逐 side 全 raw/index/order 均与手写数据相符。R31 完整 typed marker 树、R52 原顺序三约束及重复次数、V01–20 各原变量 spelling 与 literal 类型树均逐值相符。reject_parse/reject_compare 要求实际受控 RepresentationSyntaxError message prefix，由 Probe 156–162 的确切类型捕获；没有 any-exception 绿。R34 2 个逐行 parse_errors、literal=true 但 representation=false 保留。边界 16384/16385 UTF8 bytes、4096/4097 rows、63/64 组、341/342 comparisons、完整报告 >8MiB 的实际结果和受控信息逐项吻合。正常成功不证明 cap 故障以外的所有 parser 输入、未来生产或全 PEP508/PEP440 等价。

Input111 的原 tokenizers saved/actual 12 行与 Cases 逐值相同：T01-12 literal=false、representation=true；它只支持原相同约束的 conjunction 顺序、外部空白和 quote delimiter 差异。T_CHANGED 实际首行改为 <=3.0，literal=false、representation=false。旧 literal-failed 归档并未改绿，typer/safetensors 未执行仍未执行，six-archive 与 CRC/ZIP64/RECORD/native gate 不在本次 87 中。

93 份实际 JSON 字节范围

JSONLFObservation.json 原 SHA 5e252d19ef18a28108ccdb2b4bce5a394316ee9b2d4b31b012f7086365c31fd1 的 93 项声明逐项映射到本批普通字节。本评审独立严格 UTF8 decode、JSON parse、大小/SHA、BOM、物理 CR 字节与最后 LF，全部一致；文件集合恰为 MethodRoundOne 的 87 Results 加 ActualStartupBinding、LoadedModule、CacheReadEvents、InputAfter、PartialResults、Summary 6 件。没有只看作者 UTF8_LF_noBOM bool。

合法 JSON 转义的数据与物理结构换行分开；没有重写结果、消除字符串数据或把解码后的数据 LF 当结构 CRLF。JUnit.xml 为另一路二进制 XML 文件，已核 hash/全部 node，不纳入 93 JSON，也不宣所有 launcher/formal JSON 属本 LF 集合。Probe 263 的共同 save 实際使用 encoding=utf-8、newline=LF；本批 93 文件的真实字节支持此正常路径，其他未来故障路径未实测。

证据限度与原错误

CacheReadEvents 仅一条原 FileLoader.get_data code identity、cache absent-at-event/source binding 的许可前观测。Probe 116–130 明确该记录发生在实际读取返回之前，不能当 OS FileNotFoundError/return trace，更不能当完整 cache/DLL 加载证据。没有独立方法 call-count 文件；87 是 outer case，不是 87 独立进程或某方法调用 87 次。具体调用来自 Probe 165–237、278–293 源码与实际完整结果，不补造 profiler 次数。

原 ReadProjectionCorrection.json（3bfc72c0f895cc11a1e7485f10f190ad8478021301a6ae6f379ca077c1bfd0d3）明确原3ee5ef输出截断、298ca4误用不存在 results key 产生 all_result_count=0，713fad 按真实 cases key纠正；这是 observer 错误，不是原87失败。本评审 6723b4 聚合索引输出截断，90bc60/并行聚合可见源码尾和 runner 开头被截断，799808 定向补读真正遗漏段，不能将截断当全文；未重跑目标或改原证据。一次自身封存 functions 脚本因 JavaScript 模板内 PowerShell 换行转义发生 SyntaxError: Unexpected identifier r，未进入 shell、未写目标；原错误保留，后续仅修正自身封存字符串。

后继角色只能使用 LIMITED_COMPONENT_PASS 的上述准确范围。PDM 真实收据故障/漂移和六归档需要原独立 Test 的另批，后续 Integration 实際 semantic 入口也须单独准入；原19三次失败及第四等价目标禁止、媒体/Owner/native/安装/full R1→R2 门均不改变。未发现本批新的阻断，不等于授予这些运行或验收。
