# RV5：I5静态修复、T7原反例与T8窄补评审

2026-10-08；永久独立评审；静态阶段FINAL。只读固定实现及普通可读证据，未测试、修源码/标准、收费、读取真实key/ValidationInstance/.ssh、操作进程/ACL、安装或部署。静态阶段先释放槽，T9正式证据另批，不等待未确认进程。

## 结论

I5三新源与正式交接JSON、九份owner证据hash全部匹配。RV4-P01/P02的修复方向在新代码中覆盖，但**独立新源复验尚待T9，两个P2不据owner63自查关闭**。T7原源15绿及两条红均保留：P01已由真实Node→Python受控查询失败验证；P02只由固定stop源切片/模拟Vite计数验证，不能据它声称实际Vite残留。

T8正式交接、13普通副本与275依赖逐hash匹配；只改一条startup否定断言，实际2pass/0skip/exit0，**RV3-P01在该窄范围关闭**。旧T6源及112项结果不倒填新身份。新增RV5-P01（P3）仅运行契约的逗号串格式问题，不涉及实现失败；不为此改T9当前冻结源。

## 固定身份

| 对象 | SHA256 |
| --- | --- |
| EngineProcess.mjs（I5） | 874d0adc2205cc55dca0138963aa349c0389cab42bf6073d401ba6082ad95a28 |
| DevRuntime.mjs（I5） | c0683c9a523398c0c866d5b711b605ea87f1e8864946e53fd0056d8acf820af8 |
| RuntimeContract.md（I5） | 0434a26717fc8cc6a82794e3908b9322202e7c713d9ee34b75679e2824d584b4 |
| I5Handoff.json | e869558dc501b62d7f2dadc4ca176867a4e7229d2d0afa79792431c43a641021 |
| T7Handoff.json | 182facf925c32eaae50cc50b283f7bc36ed7f2efc718582733f1718cacb31890 |
| T7普通38副本manifest | a6b25b3066e7cc7f1f879cb9387431abb375e8c1c8d32c9808697254cdb1034d |
| T8Handoff.json | f314604df2670043d96924285a99a4a2c2b0d8a5414c6109a9dde580a08cae14 |
| T8普通13副本manifest | 045fea80dddc55401b51c99343ebef91b9976ca4ca4a4670e89ee0bd84245114 |
| test_t6_cli_lifecycle.py（T8新） | f76b493e38efa00a44cc9b66ecd3d8112012b44ed6aa4e5b8286ecb14fc03504 |

I5Original的三份原源副本实际匹配I4旧7e94/d900/0081完整hash。T7三批before/after及旧host身份、38普通副本声明hash全部匹配；本评审只读副本，不再读取私有case原件。T8 13副本逐项匹配copy和声明original hash，275范围当前字节及当次before/after全部一致。精确清单见 [RV5Snapshot.json](G:/开发测试/Codex/VideoCreatorImplementation/Review/RV5Snapshot.json)。AGENTS仍6de878f5…；本次任务卡99c8712c…，接口批准与技术Gate分开。

## I5静态分支复审

**RV4-P01：修复方向覆盖，独立关闭待T9。** EngineProcess:70—79不再因empty/ended或实际close0自动verified；曾spawn正PID但root未捕获返回root_identity_missing/false，非空集合要求rootIdentity且无inspectionError；capture、inspect和target即时复核的查询失败均为粘性错误。只有无PID、actual close且无检查错可证明没有创建子进程。:90—94复核失败记录固定identity_unverified/skip，不对未知目标taskkill。ready:164明确只表示API可用，清理仍需完整身份条件。因此原查询失效反例不应被原normal条件放行；新支路尚未独立实跑，尤其target复核失效不能借owner其他场景算通过。

**RV4-P02：修复方向覆盖，独立关闭待T9。** EngineProcess:199—204的cleanupRuntimeChildren分别通过Promise.resolve().then安排API/Vite，并使用allSettled；同步throw和异步reject均不能阻止另一条调用被安排。DevRuntime:47—54读取两路结果，失败输出固定错误码、实际exit/signal或null、完整清理false和host非零，不转发异常原文。该静态改变解决旧的顺序await漏调用；不等于任意callback不合作/永不resolve、完整Vite/UI信号、父崩溃及native资源已测。新P02测试因helper抽出须纳入EngineProcess身份，并保留旧“API失败仍尝试Vite”和实际非零的语义，不为适配结构降低期望。

marker、actual close0/no signal、port明确关闭、root/捕获后代与未确认后代组合未降低；EOF不取消、制作/费用不由host收尾。有限CIM快照、创建时间复核到taskkill的TOCTOU仍保留，不能称JobObject/无竞态保证。owner新五场景32checks、四边界31checks及整源语法0有固定收据；target复核故障、完整DevRuntime/UI不在owner实测范围。

## T7原证据：不倒填I5

| 原批（旧I4源） | 实际终态 | 范围 |
| --- | --- | --- |
| T7HostRoundOne | Node15pass/0fail/0skip/97.428798s、子exit0；外层打印GBK错误exit1 | 283项、内外变化0 |
| T7CimBoundaryRoundOne | 1红、Node及UTF8 wrapper exit1、2.1954416s | 284项、内外变化0 |
| T7DevStopBoundaryRoundOne | 1隔离分支红、Node及UTF8 wrapper exit1、0.09954s | 4项、内外变化0；原结构不依赖EngineProcess |

三批实际argv/CommandReceipt/JUnit hash与交接一致；Node JUnit实际15/1/1 testcase，失败0/1/1。首批run_recorded保存真实子stdout/receipt后打印✔发生GBK UnicodeEncodeError，外层1仍保留，不能把“子测试绿”改写为“整体命令0”。后两批只加-Xutf8调用，不改wrapper源。

P01普通CimLookupUnavailable收据实际health200、Python close0、marker1、portclosed，同时inspection_error=owned_inspection_failed/captured=[]/verified=true/classification=normal，独立root前live后absent；原期待error断言红。它证实旧误报分支，不证明恶意PID接管或真实残留。P02RejectedEngineBranch收据绑定旧DevRuntime源与切片SHA，engine失败后模拟Vite清理计数0、原期望1、隔离exit1；actual_vite_started=false，明确无OS残留结论。正常/负向样本真实Node→Python与受控marker扰动分列；split不保证两次OS data事件。T7未捕获系统PowerShell/taskkill当时hash，完整工具链冻结不由这些样本外推。

I5九份owner证据hash已核：四边界里lookup/fast真实进程验证，sync/async是实际stop切片+受控API失败+真实自有Vite，子脚本actual1/expected1和汇总工具0分开保留；五正常回归32checks另列。它们是开发者自查，不能替代T9独立新源复验，更不能直接称完整DevRuntime/UI或候选App验收。

## T8：RV3-P01窄范围关闭

实际对比原普通源副本SHA5fd785f5…与当前SHAf76b493e…，仅 [test_t6_cli_lifecycle.py:88](G:/开发测试/Projects/VideoCreator/tests/gate0/test_t6_cli_lifecycle.py:88) 从b"api_ready"否定改为stdout必须为空，同时仍无成功marker。真实ready或任意stdout都将失败，原helper不变。实际命令为Python -Xutf8 -m pytest同文件的缺token用例及plain正常私有LF停止用例；JUnit2pass/0failure/error/skip/3.459s，pytest/UTF8 wrapper exit0。CommandReceipt SHAfb89e60b6dba66879852f19e3f15b5fa56cc58fb2cca8885093e993fc0c97477，JUnit SHAc91e0401b4e1bcd548f32ad74fbf75dee2a7a716b87673ff459c741ae3f32885。

正例实际ready、exit0/marker1/portclosed/已观察后代结束/采集线程join；缺token实际exit1、ready=null、marker0且stdout空。13副本和275依赖hash全部匹配，内外变化0。此证据关闭旧标签覆盖缺口，不关闭历史unknown首raw缺失，不替整个112/83回归重跑，不把新test身份倒填旧结果；不读取或判定Node host本身。

## RV5-P01：新增I5契约段被写成逗号串（P3，文档格式）

归属Integration。固定 [RuntimeContract.md:54](G:/开发测试/Projects/VideoCreator/packaging/RuntimeContract.md:54) 以“,## I5…”开头，并以双逗号串联整段；Markdown不能将其呈现为预期标题和分段，读者易漏掉检查失败及分路清理条款。语义内容可读且不改变实际代码，不升级为生产失败。后续owner按新hash改为真实LF标题/段落，保留当前0434源/结果；**不能为此修改T9仍在冻结的三源**。

本阶段正式FINAL；T9正式收据未交、没有读取其WIP当通过，不预借绿。后续独立批决定RV4-P01/P02关闭，继续新精确包/AV验收。旧68包及AV0两次exit3、自主协作成片、真实视听Bundle/RAG、Worker/官方商用资源和额度TTL、三OS及商业发布缺口保留。完整目标 **Gate0→R1独立验收→连续R2** 不变，本局部评审不自签Gate或验收、不扩大收费/发布/部署授权。
