# RV4：固定I4 Node host静态评审

2026-10-08；永久独立评审；阶段FINAL。只读固定实现和普通可读证据，只写docs/reviews及自身Review。本批没有运行测试、查询/停止进程、收费、读取真实key/ValidationInstance/.ssh、安装、构建或部署；不修实现、测试、标准或ACL。T7尚无正式通过证据，本报告不等待其运行、不借owner自查签独立验收。

## 结论与固定身份

固定三源和正式交接七份子证据逐字节hash全部匹配。私有字节控制/marker解析、失败出口和有限PID身份核验有明确代码；发现两项P2静态分支问题，交永久Integration owner修复。它们尚未实跑，不称T7已失败或已有真实残留/错误normal收据。当前host完整清理结论不能冻结。

| 固定源 | SHA256 |
| --- | --- |
| tools/build/EngineProcess.mjs | 7e94a02e9cdc12254d0cb4af4a9954eae353f724dffc69be23974853d455ceca |
| tools/build/DevRuntime.mjs | d900d689d960ade8f3c13bc9f495922f3890436bd58a03752f8a5dd44a4898c5 |
| packaging/RuntimeContract.md | 00814447e397c868235acf66d5bd07f982df53067611d62b9248765761f0fa7f |
| I4HostPhaseHandoff.json | fc24ee61697c85e45bae033e743ee43a52152cb1a2cc2cdf615338dcce161a02 |
| I4HostPhaseHandoff.md | a30d412af63fa33afd045125e4bd50130508b9d73174d96f4b9b648e47740061 |
| owner最终I4NodeHostProbe.json | 1e7d32decf78fd47cc42a898e3312aad64adf45b1b7997f38cd4e62183186056 |

AGENTS SHA6de878f5…、RV4任务卡SHAd21e9d85…；B4/B5和ADR0005语义沿用RV3固定源。本报告不改变RV3的公开415局部关闭、原W5/媒体机制范围或旧68包/AV0 exit3事实。

## RV4-P01：缺失进程身份时可能误判已验证清理（P2）

归属：Integration；证据类别：**静态源码分支已定位，未实跑反例**。

源码 [EngineProcess.mjs:70](G:/开发测试/Projects/VideoCreator/tools/build/EngineProcess.mjs:70) 在captured为空时返回verified=!!ended，未检查inspectionError，也不要求曾捕获rootIdentity。capture:46—65把CIM/JSON/查询失败仅记录owned_inspection_failed后返回；ready:156随后仍可能resolve，因为capture吞错而不是reject。正常停止:175—177只以verified、空alive、空unproven_children作为ownership成功条件。

具体触发链：API真实输出合法ready→初始/后续停止前metadata查询失败，或root在取得创建身份前退出，使captured为空→固定shutdown被API接受且实际close0/marker1/端口关闭→inspect:70因ended存在将verified置true→normal或cleanup_complete可被判成功，尽管未证明root/后代身份。此时返回对象甚至可同时带inspection_error=owned_inspection_failed和verified=true，违反RuntimeContract:41“CIM查询失败或身份不明则不宣称清理完成”。已正常capture的owner样本不能覆盖这条分支。

改法边界：Integration明确区分从未成功spawn/无pid与已启动但root身份缺失；metadata失败、root未知或后代未确认不能转成verified成功，保留错误分类及原exit/marker。ready能否继续诊断需明确，但不能把capture无抛错当所有权验证通过。不能用盲taskkill、取消创建身份核验或把所有空集合当成功修复。测试owner在原固定源做免费受控metadata失败/快速退出原例，保存原源与结果；修复后新冻结批按同一断言复验，不改旧证据。

## RV4-P02：API清理抛错会跳过Vite独立清理（P2）

归属：Integration；证据类别：**静态源码分支已定位，未实跑残留**。

源码 [DevRuntime.mjs:47](G:/开发测试/Projects/VideoCreator/tools/build/DevRuntime.mjs:47) 先await engine.shutdown，:48才执行viteOwned.force；:52外层catch仅输出固定failed并设置process.exitCode=1。EngineProcess.force:87的逐target metadata复核位于try:89之外，会在CIM超时/解析失败等条件下reject，shutdown:180未吸收为结构化失败。

具体触发链：自有Vite已启动→host收到SIGINT/SIGTERM、Vite/API异常或其他停止原因→API不能正常确认，走force→某次已捕获目标的即时metadata复核失败抛错→DevRuntime直接进入:52→Vite清理:48未执行。设置exitCode不会结束仍存活的Vite及其管道，host可继续被这些资源保持；没有独立T7运行证明本触发已经发生，故不写实际残留PID。

改法边界：API和Vite的cleanup分别尝试并收集独立结果，即使API清理抛错仍进入自有Vite清理；失败保持非零和清理未完成，不能吞成normal。每条清理自身有有限策略且保持PID创建身份边界，不以杀全部Node/Python进程替代。测试owner补API清理reject且自有Vite存在的受控故障，确认Vite尝试、实际退出/owned终态、固定错误记录和兄弟进程保护；不以console/exitCode字段替代真实资源终态。

## 可支持的代码机制

EngineProcess固定spawn参数，shell=false，绝对本地repo/executable/dataDir校验、限定origin和成对mediaArgs；开发host显式启control，后端CLI默认仍关闭。只发送9bytes ASCII shutdown LF，不暴露自由shell/页面命令；EOF由disconnectControl结束stdin，不主动取消制作/对账。stderr按有界512bytes整行精确匹配唯一LF marker，超长行丢弃到LF，其他诊断不转发；ready只接受三个字段、127.0.0.1随机HTTP端口和有界16KiB/30秒等待。

normal要求sent、close code0/no signal、marker1、原端口明确ECONNREFUSED和ownership集合终态共同成立；正常等待15秒与后端10秒区分，失败回退保留actual exit/signal/taskkill出口。CIM只查数字PID/parent PID/创建时间，最多128捕获身份、16层快照；target再次核创建身份后才调用固定taskkill /PID /T /F。保护兄弟及PID复用是尽力身份策略，查询到taskkill之间仍非原子，有限快照不能保证发现所有瞬时后代或父崩溃清理。P01/P02修复前不能把这些正向代码条件称完整清理已通过。

DevRuntime重新使用同一DataDir并把会话token留内存/子环境，可信manifest校验资源真实路径、大小/hash和固定ffmpeg/ffprobe。未启动Worker或新增预算/route。SIGINT/SIGTERM监听、不调用process.exit掩盖结果；硬杀父进程不能运行异步清理，尚无生产JobObject或独立后台移交。资源和数据持久化机制来自源码及owner样本，不等于新Vite/UI联动实测。

## owner证据及范围

七份普通证据hash全部匹配，详见 [RV4Snapshot.json](G:/开发测试/Codex/VideoCreatorImplementation/Review/RV4Snapshot.json)。owner第一轮5场景/29checks实际exit0、原JSON保留，未捕获当轮host源身份，不补作最终三源冻结；第二轮实际2026-10-07T19:45:14.400Z—19:45:51.116Z，5场景/32checks/0fail、reported exit0，host三源匹配，source_changes0；11冻结输入before/after一致。旧22508/27872/36296与原MSVC38488/51712前后创建身份相同，只是owner当时metadata记录，本评审未查询或重启这些进程。

owner五场景为：中文空格独立实例真实MP4解码正常关闭、同实例重启持久、EOF保持health200后明确forced、default无control等待后forced、真实缺session启动error。前两个marker1/close0；forced为exit1/marker0；startup为exit1/marker0无force动作。进程捕获数量分别4/3/3/3/3，无剩余捕获身份。probe不启动Vite，因此不覆盖DevRuntime完整启动、Vite失败、host信号联动或P02；正常CIM样本也未覆盖P01。DevRuntime --check actual0只证明语法。owner命令均由Integration执行，本评审未复跑。

T7本批终态及冻结范围尚未正式交付；没有读取其WIP测试并当已测结论。本次先完成静态FINAL释放槽，后续独立测试结果另批复审。**T7旧固定批终态/解除冻结前，Integration不能修改这三个host源；修复须新hash/新批，原结果继续绑定旧源。**

完整桌面/新精确包/原生父崩溃监督、后台Worker/费用收尾、干净Windows/macOS/Linux、自主作品及视听Bundle/RAG、官方资源商业权益、计费与授权发布均未因此通过。旧68c1f069及AV0退出3不继承源码绿。完整目标保持 **Gate0→R1独立验收→连续R2**，R2保留R1回归；本评审不代验收、不扩大收费/发布/部署权限。
