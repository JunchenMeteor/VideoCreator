# MaterialConnection 修订准备条件独立评审

结论：**ORACLE_SOURCE_STATIC_APPROVED**。批准下表精确版本的准备条件与 oracle 修订；原 MCR-P01 的前置谓词缺陷仅在此版本 **CLOSED_ORACLE_SOURCE_STATIC**。没有发现阻断本份准备方案的新问题。Review 不授予运行许可；新 14 项仍为 NOT_RUN，须由统筹在实际运行准入后另行分派。原 Old/Fixed 两次 NOTPASS 与 raw 不变，不继承为新批通过。

## 固定范围与身份

任务卡 SHA d4ae7282c5985c0e41e7111c7305a4cb3caa390cdc1cca69af98f2d81c2bf609。普通根 `G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/MaterialConnectionPreparationCorrection/`；过程根 `G:/开发测试/Codex/VideoCreatorImplementation/Review/MaterialConnectionCorrectedOracle/`。

35 个 manifest 普通副本实际大小/SHA匹配；原 MaterialConnectionFixed 的 Fixed14 产品与 SDK8 普通副本共22项匹配候选 index 的来源身份。正式 MD/JSON/Boundary/Snapshot/Terminal/Manifest、卡和规则另存有限 InputSnapshot；末次 InputAfter 无漂移。没有重新盘点8824环境文件或访问528个真实链接；这些数字属于候选声明和原准备收据，本轮有限实际路径另列 InputSnapshot。

| 固定件 | SHA-256 |
| --- | --- |
| MaterialCorrectionInputIndex.json | b87f1612fde27758b0e91554ead523031660ed87c99de776deb0ee05d8f9f982 |
| CorrectionLaunchRequest.json | bf988bef8943c3271cb642f8b65f00eeb1dc3a4d5f78a3ea5a0e862e8d92bff5 |
| ConnectionCasesCorrected.mjs | a849ada622f96d56c95ef389790e917811efacf850a624cee633eb335cc0b1c6 |
| PreparationObservation.mjs | 127a2bafdbebd201f4461a884c821e54b702f1bc4cf9c3ac9d28e11c466506e1 |
| Harness/Entry.tsx | e3b63ff891897f215a198b7c4c4e8312c8d8b58ee820dfe0eed27ddcf29b834b |
| RunConnectionCorrected.mjs | e4e3eef3967d43b31ee6c04c3ef850e8778cf0b14ae70ee3e0be638b8562bef4 |
| RunConnectionCorrected.ps1 | 744b38f53cd8477a63e89ac9a0408811e86dd8c58c9f21324853016041e886c9 |
| PreparationHandoff.md | 5979ca25c2acae2e52f06cf5a9569a43d504e84880abe425b42ac143bac3a074 |
| PreparationHandoff.json | 4e07a77d93f1a7a8992693b4c9a837d5b4abbc65d0409741ece7d2faf7e7cea1 |
| PreparationOrdinaryManifest.json | e3b0edaec1be4017dbf17e20dfd5f97a5072b4510ef34a271763cd0cb57533df |

独立读完整新 Cases、Observation、Entry、Node/PS runner、JUnit 与四完整 diff，核原实现对应事件链，未以作者摘要/数量代语义。四个 unified diff 独立重算逐字一致。纯文本平衡括号并处理引号的检查证明14名称/顺序及34个完整原assert调用逐字同序，保存于 IndependentAssertionAndDiffChecks.json；其中包含作者证明数组在字符串内分号截短的那条完整调用，不据其截短数组冒称完整调用已核。

原index8773条对应path/size/SHA全保留。四条原case/entry/runner仅kind→role元数据改变，不是字节变化；528链接记录同序一致。新index8824条是实际运行前后核验的计划，本轮未遍历其全环境求绿。

## MCR-P01 关闭依据与实际前置语义

旧 ConnectionCases:182 将“开始创作”enabled当作B health ready，但只在A填初始Goal，B目标到后续goal helper才填。固定 useProjectEditor:6,15,46–64允许新B空草稿；NativeSetupView:128同时依赖非空goal、pending、busy及native状态。原运行未单独保存B Goal值，不能回溯声称当时必定为空，也不能从旧准备失败推出Frontend产品错误。

新 PreparationObservation:29–49要求原getter当前connection、期望instance/principal、同epoch Query成功记录、该实例health数据、实际HTTP200到达与真实file input可用。Entry:31–39仅原getter/QueryCache读取，没有setQueryData、伪identity/asset或替换产品回调。固定 engine:31–49每次安装新冻结context与epoch；Workbench:48–58以epoch为Query key，发起和回包核同一原connection，成功值携带该对象，外层遮蔽不当前数据。因此旧缓存A或同client旧安装Query不能独自满足新条件。HTTP到达label/200是诊断，不声称其自身与epoch一对一；代际筛选依赖原Query的connection关联。

新 Observation:52–67通过实际DOM fill/read建立合法B Goal后再等待原按钮，不强行enable、不改React/Query状态。Workbench:418仍走原editor.update，NativeSetup的完整guard保留。M13只导入，采用材料条件避免无关Goal按钮。file input不是权限凭据，原Workbench:376–400仍核原source/rights、捕获connection、两次mutation及回包/current、错误/finally；实例权限由原实现负责。

## 全14目标、顺序与未测窗口

- M01保原A导入与Goal asset-A/client/key；仅初始A增加真实准备观察。
- M02/M05/M06切B、另一principal或同client新安装后仍故意held health；不等待或解除该health。缓存A、原文件不得发新client、退役按钮disabled的原目标全保。
- M03/M04保A staging held、B或A→B→A切换、主动释放A、零import/不显示旧成功。新增观察不释放held请求。
- M07/M08/M09 Cases:185–204保原A staging/import held和各成功/失败类型。关闭原对话框后先真实B材料就绪/DOM Goal，再必须真正到达B staging held；197主动放行A，199–201仍检查B busy、旧source不采纳、旧error不显示，之后放行B、等待真实成功并提交asset-B-only Goal。finally release只是清理，不能代目标到达。新前置与错误快照保存到结果和Events。
- M10导入A后切B，真实DOM建立B Goal；原B提交asset_ids=[]/clientB不变。
- M11保同connection重试两个相同import body、一次staging以及原字节/source/rights关联。
- M12保丢ACK的pending原body/key/hash/asset-A/context；切B不改绑意图、不把unknown清成拒绝、不新建第二请求。
- M13新同client安装后调用旧disposer，依据新epoch成功Query及真实材料输入走原一次import断言。
- M14保旧A preview metadata held、换连接、释放A、零后续content dispatch。

这些为拟执行源码路径，不是新运行到达证据。原各谓词5000ms、Playwright default5000ms、Node240000ms、outer300s未改变；新增条件也5000ms，不将各条件之和冒称所有case总墙钟上限。

## 运行器、原失败与权限界限

Node:12–28固定Fixed/index与记录/链接核验；67仅换新case文件。原实际SDK/React/Query/Workbench、listen(0)、BrowserServer原ChildProcess、cleanup、输入after、首红停止、NOT_EXECUTED与runner-boundary独立JUnit节点保持。CLOSE LF的forced/error粘性保留。PS完整diff仅新根/index/runner/Fixed集合与准确argv；原.NET Process/handle/creation、两byte泵、300s后原stdin CLOSE、EOF/退出码不吞。新输出namespace仍须实际准入时确认空置。

准备只记录metadata714c69 exit0、四MJS --check27fab9 exit0和PS parse99add4 exit0；没有执行模块body/浏览器/产品。原两次定位错误、metadata未分别捕获byte-pump raw保留。Review几次大输出截断不当产品红、不称完整输出；必要遗漏PS/Workbench链定向补读，diff独立精确对照。自身finalizer29e0f4自然1因Initial/Metadata字段叫bytes而合并器期待size，未写报告/after；c1392b纯读取确认后修自身合并，不改测试或原证据，不据此声称源漂移。

Old原M01 pass/M02 A bytes实际发B staging断言红/M03–14未执行/自然1；Fixed原M01–06 pass/M07准备interaction红/M08–14未执行/自然1保持。旧B Goal值未捕获限制保留。新14仍NOT_RUN。实际installedAPI、Owner/人审/native/Win32/Backend canonical Goal算法、许可/模型/真媒体/三OS均不能由此透明HTTP/SDK准备取得资格。完整R1独立验收后连续R2不缩，其他原finding与费用/数据/权限边界不变。

后继只可由统筹消费该固定准备批准，另行决定单独一轮精确namespace实际准入。若真实准备、目标或清理红，保raw及未执行分类，不自动重跑、增时或削断言。Review未代授该运行。
