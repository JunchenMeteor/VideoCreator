# T56 CLI grammar 源码早期独立评审

结论：**SOURCE_ONLY_FINAL；T56-CLI-P01 / P2 / OPEN，归 Test**。固定 Probe 的 Windows 路径比较会跳过 product profile 分支，不能把空 Methods 或 ForbiddenCalls 当作产品行为未执行或提前拒绝有效的证据。metadata 透明观察链在本片有静态支持。执行 formal 仍未消费，本报告不作十二项实际通过、进程终态或原两个失败 raw 的独立运行判断，不等待这些后继材料占槽。

## 固定输入

准确过程根：[CliGrammarIndependentReview-T56](G:/开发测试/Codex/VideoCreatorImplementation/Review/CliGrammarIndependentReview-T56/CliSourceReviewSnapshot.json)。普通根 `G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T56CliMetadataReaderPreparation/`；17项普通材料与对应原件均 size/SHA 匹配。独立补读旧 CliCacheReaderRevision Probe、固定原 CLI 6128B 与三规则/卡，共40路径；末核无漂移。未读取活 execution formal、当前 B42、系统 DLL、整环境或后继实现。

| 固定输入 | SHA-256 |
| --- | --- |
| PreparationHandoff.md | 7bda57a8b10c756be47ab5e4118757fad86b7aa995baaae68b41b9432b4896a7 |
| PreparationHandoff.json | bf9596ce7b7e5e0851059b55a1c6a788297c2d1985d21066336f10bcec3e63f9 |
| ProbeCliFramesT56.py | ebdb19bcf346cf0c59ba814f7dd3715a9679f3dd074db3d1080347caa0726112 |
| T56CliInputIndex.json | 0e6d6be457c62eb53469865c4289109d2ebfc8ac84e1cfac40a856ba02f1d7e3 |
| 完整原 native_owner_setup.py | 28694e66c32ff7cfc77aadeddcb32f470c220c3c7ca4ade312fac2fd86c86c2a |

## T56-CLI-P01：Windows 路径格式使 product profile 与提前拒绝门失效 / P2

固定源码：[ProbeCliFramesT56.py:322](G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T56CliMetadataReaderPreparation/ProbeCliFramesT56.py:322)。索引49条 `profile_module_paths` 保留正斜线 `G:/...`；322行把调用方 `co_filename` 经 Windows `str(Path(...))` 转成反斜线字符串，再对原字符串列表作成员比较。以标准库 PureWindowsPath 做表示分析，49条全部不匹配；此是静态字符串语义分析，未运行 Probe、产品、测试或构造真实 frame。

**触发条件：**Windows 主机，真实 product frame 在这些固定源内；其文件名进入322的 Path 字符串转换。路径即使是同一文件也不命中索引，323–324的 METHODS计数以及325–333的 declared-function whitelist/拒绝逻辑同时被跳过。该分支要求的不只是统计：原固定 CLI 的 `_response` 和 `main` 也在 product_function_names名单；正确匹配时它们应被 before-body 规则拒绝，而当前路径层无法到达该规则。

**影响与边界：**这是 Test 观察器/限制器缺陷，不能归为产品 _request 逻辑故障；不能从 METHODS{}、ForbiddenCalls[] 推出业务服务未构造、无 Owner/native 调用，或者有效拒绝已经覆盖。334–340的 keyring指定名称拒绝在独立分支，278–312的 audit资源限制也仍存在；不能把此 P2 夸大为所有限制全部失效，更不能据此虚构实际危险调用已经发生。

**最小修正条件：**仅由 Test 在新冻结版本统一索引和 frame路径表示，启动时构建一次明确的 Path/规范表示集合；不要对所有身份/hash/来源比较泛化放宽，不改十二 grammar断言或产品函数，也不通过硬写 METHODS/ForbiddenCalls 造记录。保持完整原模块 file/hash门及真实 frame/module/co_name来源。后继独立小批应证明允许的原 `_request` 会真实计数，受控禁止调用在 body前拒绝，陌生路径/函数不能伪装；故障注入必须采用安全观察器机制，不以关闭审计或运行危险原生服务换绿。语法阳性和限制器机制要分别报告，已有十二绿不因补统计自动授予完整产品资格。本评审不实现、不重跑原批。

## 真实原 `_request` 的源码消费支持

已完整读取冻结原 [native_owner_setup.py](G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/OwnerSetupValidation-T56/CliFramePreparation/SourceBodies/video_creator/cli/native_owner_setup.py:31)。31–50行读取4字节小端长度、有限正文，调用原 `_json` 与原 SetupPreparationRequest 校验，再检查完整 canonical正文；只是返回 proposal。64–120的真实 main服务/Owner/native/DB路径另存在，测试声明不调用它。

Probe whole_module343–348核真实模块文件/hash；Cases.bind359取得该完整原模块，365–373逐名查所有已载 product module来源/hash。Cases.parse388和reject396直接调用 `self.cli._request(stream)`，不存在摘出或重写该函数。F01–F12覆盖字段保留、截断长度、32MiB减16KiB边界、UTF8/BOM、重复JSON/nonfinite、canonical、旧格式/unknown、小端及单帧消费；F05只有最大长度到达正文读的有限空流，不证明最大大小的合法 Goal。F12明确单帧边界，不证明 main EOF 生命周期。

独立对旧/新完整 Probe 的十二方法及完整 Cases类 AST 比较均相同，并与 AssertionPreservation保存的两侧AST逐值一致；没有删断言、缩输入或将模型/原方法换成 mock。这是源码支持，实际 Summary/JUnit/Events/已载模块/原流收据将在 Test正式终态后另片复核。

## metadata 观察链的静态边界

原标准库四完整正文副本分别与索引原来源 SHA对应。原 Pydantic get_plugins22–58枚举 distribution.entry_points；原 Distribution.entry_points489–496调用 read_text；原 PathDistribution.read_text907–917自行 `suppress` FileNotFoundError等并返回None；原 pathlib._local539–546 →_abc628–633 →_local.open529–537进行真实只读文件读取。

新 Probe check85–95绑定十个确切缺失 entry_points路径、原分发目录与 METADATA身份；已存在文件仍走完整原 pin。original_missing_distribution_read212–247限定原六层调用栈、函数/来源路径、原 PathDistribution对象及_filename、physical祖先、真实absence和原 METADATA hash/size。这里只有 read-only/open审计分支309–311才调用，没有默认所有optional metadata均允许的规则，也没有创建缺失文件。

metadata_frame_path198–209和栈226使用两侧 Path比较，和322的字符串列表问题不同。metadata_trace250–275只记录原read_text frame的真实 FileNotFoundError属性及随后原return；不赋值 exception/return，不替换原函数或插件状态。main543–547只在 Cases.bind期间启用 trace，finally撤回。原库负责 suppress→None，观察器记录这条结果，而不是注入假OS错误。

本片没有消费实际 MissingMetadataOSOutcomes：不能把candidate.exists()==false、output cache映射或计划文本当作真实 OS错误；仅returnNone没有同frame此前匹配异常仍应记不完整。Python-level exception观察也不能变成独立 Win32 HANDLE/绝对系统 DLL加载或安装资格。标准 ctypes once/finally撤回、platform一次hostname读取与audit门仅按固定源码保留，本片未实测它们。

## 阶段交接

Preparation声称的原两批NOTPASS/十二NOT_STARTED和原 runner等待/EOF规则保持，实际原raw/两个进程及新十二运行结果均留待正式固定execution片；没有根据统筹预报倒填本评审通过。5235df合并输出因误展开保存的AST文本而截断，原输出保留，不声称该输出完整展示；7ffea0标准库完整AST/字段分析只输出有限统计，errors[]/自然0，构成本报告保护结论。

所有固定source reader已释放，live[]、无生产冻结；未执行 product/Test/安装/凭证/费用/网络，也未改实现或期望。Owner正常main、native通道、DB、安装、B42运行、完整三OS/R1独立验收及后续全R2均未获资格。后续 execution片或 source修正应另固定/另评审，不覆盖此原source finding。
