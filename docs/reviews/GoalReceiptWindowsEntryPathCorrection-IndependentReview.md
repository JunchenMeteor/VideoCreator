# GoalReceipt Windows入口修正独立评审

结论：**GRRP-P01在本次固定版本关闭为CLOSED_SOURCE_STATIC**。本修订消除了三份入口及物理Python的斜线表示不一致，未发现新增P1/P2阻断。解码后的LaunchRequest完整argv、cwd、索引、计划和输出路径与冻结对象一致，没有解码后重复分隔符。本结论只评源码/准备材料，不授入口、19项测试、Owner、native、HTTP/MCP或产品验收运行。

## 固定版本与只读范围

任务卡SHA为`68c422df3ee611ece9a758337f688750c8380fd44155ff718bfc4ee0fb8781a6`。规则和10/11规格已读取；角色仍仅写本报告与自己的Review过程。固定准备根为`G:\开发测试\Codex\VideoCreatorImplementation\TestDevelopment\GoalReceiptWindowsEntryPathCorrection`，普通副本为其正式OrdinaryManifest列出的`TestDevelopment/ReviewHandoff/GoalReceiptWindowsEntryPathCorrection`。

| 文件 | 完整SHA-256 |
| --- | --- |
| PreparationHandoff.md | f1241c82ad9042a0fbb141f141a38a4d62a931d3686f548cfbfe2d837fdc153b |
| PreparationHandoff.json | ccf4e9c3d7ca376c845ddb16e91b4c3b22f71080fb268afe11bf995200da5c1e |
| FinalizerToolTerminal.json | 0b24ee51cb8bdfa8d12573bcdb90af5920966df697a52ab09b2677dd31180417 |
| RunGoalReceipt.ps1（7140字节） | 13c269f6e11f3b5d9a1eb82260d43b74ee4f05ea7817e7191d131270392815f4 |
| FullSourceDiff.md | 00e19bef60659015bdc902242112cfaafafc77ff3db062bc5132a1ee8fd4591e |
| GoalReceiptLaunchRequest.json（2446字节） | ef211f538825ca4c53d5221a6c7c4eb509c6a0ce564b72d950491ae615dd3beb |
| GoalReceiptInputIndex.json（2737143字节） | 2e8b1cb38069cca35429f04a1651122d5bf667ad2aaba11a1ac62ead3c74cd2a |
| OrdinaryManifest.json | 7e6a81c07a80dcb975d18a5c2f1fb6a8631d39df49ce1320d3cce21cf2be022a |

26份ordinary逐件大小/SHA与正式manifest匹配，原件与副本声明的身份一致。独立有限输入前后共51条/51唯一完整路径，changes为空。没有重扫3635环境对象或复制runtime；前后身份明细位于本过程InputBefore.json/InputAfter.json。

## GRRP-P01关闭依据

原普通RunGoalReceipt.ps1 SHA`35bfe687c159312a0de015e57ebe9ac10a7860ab3389c6a042827e279f6f8f59`的44–45行只把入口侧转为正斜线，另一侧完整index记录仍为反斜线，导致合法同一对象被拒。原Python literal和index executable也有同类表示差异。原独立finding与失败材料保留，不将其改写成运行通过。

新普通RunGoalReceipt.ps1第32–36行对两个index Python字段先Assert-Physical，再将双方完整绝对路径GetFullPath后用`-cne`比较。47–54行先拒非fully-qualified记录，将完整pins和完整入口同样GetFullPath后`-cnotin`比较。没有basename/suffix匹配、大小写折叠、通配或alias准入。4–17行的祖先ReparsePoint拒绝、37–43行的每文件完整size/SHA、44–46行的999 required runtime membership保持，全部在61–62行创建输出和89行spawn之前；18–25行原Root/tool/index身份门保持。

独立计算的完整old→new源码diff仅上述两段，与FullSourceDiff正文的两个hunk一致。GetFullPath是这里明确规定的词法表示处理；它不是原子OS对象绑定、TOCTOU豁免或执行授权。关闭仅针对原确定表示错误。

## 精确LaunchRequest

JSON解码后原字符串逐字比较，不替换分隔符或隐式修正请求。`/argv/4`、`/cwd`、`/index/path`、`/plan/path`、`/original_plan/path`、`/outputs/0`、`/outputs/1`均等于本次冻结对象的完整绝对路径literal；每个反斜线连续run长度均为1。JSON正文的`\\`是转义表示，并非解码后两个反斜线。`/argv/0`保持已固定`C:/Program Files/PowerShell/7/pwsh.exe`。

完整未来argv（JSON表示，尚未执行）为：

```json
[
  "C:/Program Files/PowerShell/7/pwsh.exe",
  "-NoProfile",
  "-NonInteractive",
  "-File",
  "G:\\开发测试\\Codex\\VideoCreatorImplementation\\TestDevelopment\\GoalReceiptWindowsEntryPathCorrection\\RunGoalReceipt.ps1",
  "-ExpectedInputIndex",
  "2e8b1cb38069cca35429f04a1651122d5bf667ad2aaba11a1ac62ead3c74cd2a"
]
```

cwd为`G:\开发测试\Codex\VideoCreatorImplementation\TestDevelopment\GoalReceiptWindowsEntryPathCorrection`。两个独占输出分别为`G:\开发测试\Codex\VideoCreatorImplementation\TestDevelopment\GoalReceiptWindowsEntryPathCorrection\LauncherRoundOne`、`G:\开发测试\Codex\VideoCreatorImplementation\TestDevelopment\GoalReceiptWindowsEntryPathCorrection\MethodRoundOne`，本次只读exists观察均absent。`-File`指向本候选7140字节PS；`-ExpectedInputIndex`与实际index SHA相等。index/plan/original_plan的完整path、bytes和SHA声明与固定实际文件匹配。下层PS65–66行构造原完整Python argv与本root cwd，并非用外部cwd猜入口。相同路径表述没有被评审替换成新alias。

详细八pointer原值、期待literal、分隔符run及逐项比较保存在Facts.json；原请求bytes不变。此静态支持并不表示CreateProcess已经使用这些参数或原19项已经到达。

## 闭包、原断言和生命周期保护

旧3619完整record逐值全部保留，重复路径0；新3635 record重复0，新增16条都是精确候选/审查依据身份。原index SHA`fee3d145d575a02a7193bdddb2e9de629dc5bffe400f264113a0a17d2d04627b`保持。whole102完整映射与旧版逐值一致；999 required runtime路径保持且全部在记录中，prefix/base_prefix/executable完整原物理解释器字段不变。没有将当前Backend或Media热源补入旧冻结身份。

原1257 missing cache关联无改，新增5个候选自身源码关联后为1262，各source完整path/size/SHA均匹配index记录；原116 optional metadata及其reader、91 product profile paths和依赖provenance无变。这里只核记录关系，不声称Windows实际cache/metadata访问结果或全闭包实际import资格。

ProbeGoalReceipt.py、GoalReceiptCases.py、RunGoalReceipt.py、PositivePrerequisiteMatrix.md、GoalReceiptPlan.md新旧完整bytes一致；前三完整AST也独立相同。故原19 ordered cases、所有断言、90秒child bound、5秒观察窗、持有原Process及creation、双原始字节流EOF、错误传播未被本次修正改变。PS完整124行已审，93–95行原PID/creation收据、96–118行持有原对象等待和字节泵、123–124行异常与原exit传播保持，不以新路径匹配替代终态。

## 已存在静态证据与实际限制

固定CheckEntryPaths.ps1仅提取并调用原prelaunch guard，执行范围止于输出/Process分支之前。原StaticRoundOne/PathGuardReceipt的9项确分别为：旧Python拒、旧entry拒、新native三入口通过、新双方斜线形式通过、同名异目录拒、大小写差异拒、相对路径拒、foreign Python拒、同长度坏fixture SHA拒。parse三对象error_count=0。完整提取源与receipt对应，ChangedEntryFixture 21字节前后SHA不同；该人为坏文件仅属于本任务的独立fixture。

原MetadataToolTerminal记录自然0，stdlib-only；StaticToolTerminal记录自然0，guard-only；对应原stdout和stderr（后者空）与记录一致。原formal最后工具661213自然0及reader release另有FinalizerToolTerminal。它们证明有限原准备/guard机制，不是本评审执行9项，更不是启动器或19业务case运行。19全部NOT_EXECUTED，runtime_grant=null，lawful accepted/pending/denied/history均NOT_READY。

GRRP-I01继续SOURCE_INSPECTION_ONLY_NOT_REPRODUCED：并行原export reader/background对metadata替换的归因界限未复现，没有关闭原export生命周期或削掉no-replacement断言。本次无新P1/P2 finding。

## 评审自身错误和交接

第一次合并输出7d1319以及245e41/并行正文的总输出被截断，只对遗漏有限段补读，未把截断文本冒充全部显示。曾猜StaticRoundOne/CommandReceipt.json得到ABSENT，随后按正式26条manifest改读准确Metadata/StaticToolTerminal；该locator错误不属产品失败。自己的933ae6解析工具自然1，因为用含Receipt的宽子串误把GoalReceipt源码选为JSON，触JSONDecodeError；准确命名读取57fde8自然0。原错误按ToolHistory记录保留，不洗成产品或Test失败。

无产品/候选/Test执行，无vendor import、SQL/DB、HTTP/MCP、Win32/native、ASR、模型、联网、钥匙读取、安装或费用动作。真实入口/19 fault行为仍需统筹单独按完整固定request准入，合法阳性依然缺真实Owner/资格事实；本评审不授该运行。Material第四次、媒体精度与安装验收也不在范围内。完整三OS真实R1独立验收后连续R2的总目标没有缩减。

过程根为`G:\开发测试\Codex\VideoCreatorImplementation\Review\GoalReceiptWindowsEntryPathCorrection`。本报告只标SOURCE_REVIEW_FINAL；最后工具实际返回与读者释放由后续正式Handoff/terminal及实际工具输出分别封存，不能用文件存在或自声明替代返回。
