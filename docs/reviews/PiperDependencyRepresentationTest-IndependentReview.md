# Piper 独立依赖表示测试准备评审

结论：87项候选的手写标准和完整模块调用边界在下面限定范围获得SOURCE_STATIC支持；本版本存在PDRT-P01（P2）和PDRT-I01（P3），不能作为无问题执行准备包。**87项全部NOT_EXECUTED，本评审不授权运行。** 原Integration PDM-P01仍独立OPEN；原19目标三次失败及累计限次不重置。完整R1三OS真实作品独立验收后连续R2仍未完成。

评审角色只读停止源码/JSON/已有准备证据；仅使用自身stdlib身份、JSON、AST和文本差异分析，未执行Test候选、parser、regex、cases、vendor、archive、Pydantic、Backend、SQL、HTTP/MCP、native、模型或安装。未读取Backend/Integration热修源，未修实现或测试。

## 固定输入与实际读取

任务卡 `G:/开发测试/Projects/VideoCreator/docs/task-board/PiperDependencyRepresentationTestIndependentReview.md`，SHA256 `624127d0af9df6098b6f91021ffb5296e4a31c273047ea025229140b82e176c1`。工作区及仓库AGENTS已全文读取。

停止输入根 `G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/PiperDependencyRepresentationIndependentTestPreparation/`；正式Handoff MD `28f4d6aad227a8f3e0548472c9a9dcc286832f4178dd97198f206b29849e3b3d`、JSON `64f6e6bce8a2d8f702b1616245e14bb4fa4fbb27d65b46bc8b7ca9034d68aed0`。SourceSnapshot `cc1cc7279c507071a11452cb191a98da5034100377d0f8cbbe53026625cccb55`；SourceStage/OrdinaryIndex `4396ea5acb882dd50225465b74f1c24f3232c7da8e0e052c8cae3a91db12e85f`，32普通副本均实际size/SHA核对一致。独立Before为68唯一有限路径：32原源+32普通副本、索引和3治理文件；不是68测试，不重新扫描或复制999环境实体。

全文读取固定335行RequirementRepresentation.py、310行ProbeRepresentation.py、149行RunRepresentation.ps1、147行PrepareSourceStage.ps1、完整54 fixed case/20变量/11 boundaries/两组合JSON、oracle/计划、原grammar Parser/Tokenizer、历史12行raw及准备终态。specifier文件只做完整源码AST与静态常量文本比对，无vendor执行。完整58450B新文件diff已依据六份完整停止源独立重建，SHA `4f12c7c4cd33e4da2bf62beb10e4881c4c35b6faf1d173fcc36c8be311dfa749`，逐字节一致。全文/核对结果不采用作者布尔值替代。

主输入版本：

| 普通副本（SourceStage/Ordinary下） | bytes | SHA256 |
| --- | ---: | --- |
| FixedInputs/RequirementRepresentation.py | 14205 | 9eae0ad968c464189810a62e0ecf2579a2dc5ef11de1fc6dd3b523e3018ac382 |
| ProbeRepresentation.py | 15545 | 10119c7f4e293a7ce9c655b681c3fc44ca122dfc396c034eed99e02c7b5fbc21 |
| RunRepresentation.ps1 | 7644 | e1a02388e72525a81bc5a83a6e18b343a0d076f601ea24c2c9d1a1d6fcb746a2 |
| RepresentationCases.json | 13696 | 8dd5dc91509f19ef92cf5628bf2a1072291068ecd2f827d9e83b70b6b42014e0 |
| RepresentationInputIndex.json | 618135 | 97bdacd950b14fcc4938c731dbc33f8b9ce12243aeb0e2a33d85f1b5d032a633 |
| FutureLaunchRequest.json | 1721 | c08b60f1463cdf852ab8e96e279301a91301b7d303f40ad48df4274cd6de0bca |

## PDRT-P01：末核遗漏固定启动索引

**P2 / OPEN_SOURCE_STATIC / 原Test。** 精确Finding：`G:/开发测试/Codex/VideoCreatorImplementation/Review/PiperDependencyRepresentationTestIndependentReview/Finding-PDRT-P01.md`，SHA `f5c811ba19a7aef1f6ca73aa0a10eac262f889a03a6fc31d7c45e13df3962a39`。

launcher51和Probe224各在首次读取前核index SHA。launcher137末核只 `Assert-Pins $index.records`，Probe290末核只 `verify(index)`；完整1041行并不包含index自身，其在PrepareSourceStage119形成records之后才在122–123落盘。只改变运行中实际index、保持其余1041文件不变，两个末核都可能通过旧内存records，launcher138–142仍可能记input_after_verified=true及旧index SHA。没有实跑该故障，不称真实exit0或OS复现；已缓存调用未必改变，确定缺口是前后固定索引的完整性证据。

后继新不可变版本必须用外部预期SHA独立核actual index-after并分列结果，读取失败/漂移进入sticky error使整体非零。不得递归selfhash或宽放任意audit路径；可验证并解析同一首读字节缓冲。保留1041范围、87原期望、首红/90s/双byte EOF；具体反例另由Test申请独立执行，Review不运行。

## PDRT-I01：新JSON实际为CRLF

**P3 / OPEN_ARTIFACT_FORMAT / 原Test。** 工作区规则明确新文本UTF8/LF。实际Before发现9份新原件含CRLF：SourceProvenance.json 251处、RepresentationInputIndex.json 10286处、FutureLaunchRequest.json 38处、PreparationReceipt.json 21处、StaticRuntimeGraph.json 332处、PreparationToolTerminal.json 37处、SourceSnapshot.json 84处、PreparationHandoff.json 73处、SourceStage/OrdinaryIndex.json 391处；前8份对应普通副本也相同。因此68检查中17条路径不满足LF，全部无BOM，无lone CR。六份手写源码/标准和完整diff实际LF通过，不把整个包一概说成CRLF。

源头PrepareSourceStage.ps1:9在Windows使用ConvertTo-Json内部换行，仅末尾追加LF；RunRepresentation.ps1:17–19也使用同种写法，未来JSON仍有同类来源风险，未来输出未实际生成。原版本/收据字节必须保留，后继修正仅新作者生成物与生成函数并重新固定关联SHA/index/request/copies。不得改第三方参考或把旧byte身份回填为LF；这不是parser语义/测试运行红。

## 可支持的独立标准范围

完整cases数量54+20+11+2=87，54 ID均唯一。手写期望只允许外部空白、引号定界、约束conjunction顺序、row multiset顺序及version parentheses格式差异；名字/extra/URL/version值、duplicate rows/constraints/extras、extras顺序、literal内部空白、variable类型与marker顺序/显式group保持。未执行被测parser来反填oracle，也未采用Integration26提议作为批准标准。

R01/R02明确 `<3.0` 与 `<=3.0` 区别；R03–R07/R52–54保留版本值、任意===大小写值、重复约束、原约束顺序及wildcard/local/compatible规则。R08–R18覆盖row duplicate/multiset、name/extra严格性与URL分号分隔；R19–R31覆盖quote/literal内部字节、typed variable、别名不等、boolean流和group；R31完整typed树独立字面保存。R32–R51只接受特定RepresentationSyntaxError及前缀，不把任意异常当通过；R34明确两边同unknown语法也不能equate，parse_errors保留侧/行/index/raw。compare断言145–160核两种独立equal字段、四个非激活标志、完整raw/index和行数，不遗漏拒绝行。

V01–V20覆盖停止合同全部20个变量spelling。B01–04按UTF8 bytes核16384/16385而非字符；B05–06按4096/4097 rows；组深度63组加comparison=64、64组=65；341 comparisons×3+根sequence=1024 nodes，342=1027。B11两侧4096×1000 literal原raw约8192000字节，另保完整解析及multisets使总report超8388608；期望显式完整report拒绝，不截断去重。此为静态schema/fixture数学，不是实际parser运行结果。

T01-12完整saved/actual数组逐值等于固定HistoricalTokenizersLiteralComparison.json；原raw_multiset_match=false未改变，T_CHANGED只把实际首行<3.0改<=3.0并期待representation false。原literal FAILED及typer/safetensors NOT_EXECUTED保留。原Specifier静态regex常量实比只少末尾空白行8字符，非语义token改变；精确原bytes不相等的事实保于GrammarConstantTextComparison.json，不能声称逐字节相同。未调用regex或vendor。87并非穷尽所有PEP508/PEP440表达式，本标准明确更窄表示合同，不证明完整语义等价。

## 启动、真实调用与收尾边界

解码后的FutureLaunchRequest完整Windows argv/cwd/indexSHA/writes与实际固定目标一致，无路径分隔字符串误读。Index1041行唯一，无duplicate路径：999既有解释器实体+16参考来源及16副本+6自身源+diff/provenance/旧工具索引/pwsh。不是1041个实际loaded模块。364 cache map逐项由对应pinned .py、cpython-313/optimization0产生，source size/SHA关联和Windows完整native字符串符合，无映射差异；没有重新hash999环境或证明其actual load。

launcher49–67启动前核物理祖先、全records、三mandatory sources、两个独占output不存在和absent cache；74–90用同fixed Python、闭集env、shell=false、redirect stdio及-I -S -B -X utf8。Probe224–235核index、全records、实际executable/prefix/base_prefix/version/cachetag/flags，再240之前建立输出。startup imports在reader guard安装之前已发生，StaticRuntimeGraph明确NOT_OBSERVED，不把999文件或native pins当实际System DLL闭包/安装资格。

Probe248–255真正spec_from_file_location/exec_module完整停止模块，再256–267形成计划并268–282调用真实Parser.requirement/compare_rows；无AST抽取实现、monkeypatch、Mock或shadow算法。lambda只是冻结case/输入构造。87不同于旧Pydantic/Backend19入口，不重置其三次失败。audit61–128限制pinned读和自有output写，foreign vendor/产品import及socket/subprocess/ctypes/SQLite等拒绝；缺cache只允许原FileLoader.get_data代码身份、精确derived key、源size/SHA及仍不存在，不宽放任何missing路径。cache events只是许可前置，未观测真实OS FileNotFoundError/return，不能升级该来源资格。

首个unexpected failure/error停止后续；完整结果每项落盘、Summary将剩余NOT_EXECUTED，JUnit skipped明确未执行而不算pass。setup failure可能无Summary/JUnit，原raw/SetupError/missing输出需如实保存；无actual receipt不能声称整批通过。

launcher93之后保同Process及真实StartTime/HANDLE，stdio各原byte stream CopyToAsync，finally等待同child真实exit与两泵完成，分别记录EOF后才Dispose。正常等待路径90s设置forced/error且只用原held Process Kill一次，不重新找PID/tree或重跑。启动后取creation、泵/receipt异常进入finally时可继续等待同对象；不能把90s当所有异常路径的硬墙钟上限，更不能无terminal就释放或自动重试。这里SOURCE机制支持，实际PID/creation/kill/双EOF均NOT_EXECUTED。

final CommandReceipt138–142写入没有catch吞失败，144维持forced/errors/EOF/input-after失败为整体1；最后Write-Json异常会终止而非继续149 exit0。与原Integration SaveOwner吞最终保存异常的PDM-P01不同，不能用本source分支关闭后者。没有注入save故障/运行PowerShell来证明实际行为。新增index末核缺口仍按PDRT-P01阻断当前包。

## 证据等级、历史和交接

准备原metadata session92681→937656自然0只通过固定PreparationToolTerminal声明及原工具文本保存；stdout明确tool chunk string，不当双raw byte EOF。原18c1a2/1是F盘launcher未启动PowerShell的定位/环境红，11bf44等只读后继成功；最后准备9ff8b4/0由统筹分派提供，不从文件出现推终态。新parser、87case、syntax/runtime、六archive、TTS、Owner/业务阳性、安装/三OS、R1/R2均未执行。原Integration lifecycle热修未读。

本Review阶段合并输出截断时只补Probe61–144，原截断保留，不假定全文已返回；未重跑candidate。自身grammar文本比对保留原exact-string=false与仅末尾空白差异的澄清，不改原facts。独立Before、SourceAndOracleFacts、GrammarConstantTextComparison、Finding及After均在 `G:/开发测试/Codex/VideoCreatorImplementation/Review/PiperDependencyRepresentationTestIndependentReview/`。末核只复核已固定68路径，不全环境扫描。自然工具终态与全部读者释放由后继FinalHandoff/FinalizerTerminal及评审本人实际工具返回分列；报告生成本身不预言工具exit。

下一原Test须新immutable版本修PDRT-P01及新生成LF问题，保原87和旧失败，再独立源评与Root单次实际卡；Review不授runtime。原Integration继续独立修PDM-P01；两任务不能互借绿色或用纸面标准代替真实parser/归档与产品验收。
