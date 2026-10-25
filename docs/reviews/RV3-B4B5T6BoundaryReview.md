# RV3：B4/B5、T5/T6与生成契约范围评审

2026-10-08；永久独立评审；阶段FINAL。本报告只支持下列固定源与证据范围，不是独立验收签字。没有运行测试、模型、收费、安装或部署；没有读取真实凭证、ValidationInstance、.ssh或私有pytest case，没有修改ACL、实现、测试、标准。只读273份普通证据副本及明确的源码/标准/命令记录，写入评审白名单。

## 结论

- **RV2-P01（P2：公开415声明/SDK缺口）在本固定范围关闭。** B5唯一API源声明、实际TCP的四类415、唯一ErrorEnvelope、原422及生成SDK类型一致；不是仅凭AssetService或OpenAPI断言关闭。
- **RV1-I02的局部关闭扩展到本次三个真实MP4外部dref样本。** 网络URL、目录外URL、URN在媒体decoder启动前拒绝；原HLS/concat拒绝继续回归。结论限定这些输入和固定入口，不外推所有容器、协议或OS文件读取隔离。
- **B4私有停止机制在Windows源码API范围有独立正反证据。** 正常路径实际exit0、固定marker、端口关闭/采集线程EOF/观察到的API后代终态；失败和forced负例没有冒充正常退出。新host、新打包及全部Worker不属于这个结论。
- 六份原测试源SHA保持；T6新29+原83真实通过。此前T5新25已包含在原83中，不能重复加算为新增产品覆盖。W5协议机制局部关闭保持，实际自主Crew委派/作品/唯一生产框架仍未通过，未重新收费试跑。
- 未发现本范围新增已证实P1/P2生产缺陷。新增P3测试覆盖问题RV3-P01；历史双轮raw缺失和工具链完整身份限制如实保留。完整Gate0、R1及R2均未因此通过。

## 固定身份与核验

| 对象 | SHA256 |
| --- | --- |
| api/app.py（B5最终） | e559055241046cc97450df5d6f181fa54d8430f472949671431bff775857284e |
| cli/main.py（B4） | 791d282639e082a1e481ca3c653f81862d923f110909ae56281d7c5690442c75 |
| cli/lifecycle.py（B4新增） | 3c339920297ebd0518df0faa4ea57217c9f82e54bd9e11cb066d622668ca053e |
| media/ffmpeg.py（W4） | 36a13bb084228e1e1b1021da8812688720192c71560340a4951ad6595a201a5d |
| workflows/react_protocol.py（W5） | 84a39f18b6ceacdaa783c3e2b7266bc526a2b0e99f6496ef610dc704e2b238a2 |
| packages/contracts/generation.manifest.json | 1f2ca47d58c3b5676813f98b750b242c71f5939bdd412906f556cec861713fd4 |
| tools/build/GenerateContracts.mjs | 1e2cf026e042d20b2f5101711cbdbdd8f51e040c63e00a8522850d746bbe99f4 |
| packages/contracts/openapi.json | 4020c28cc1779e37359c7d0bcdfe19ed2444eb3246f8ce4fc4fd7e8777fa05ba |
| packages/contracts/schemas.json | b86f90149c3695c07e18b4f7ede6e704b114fdf123e1ad52836212be97ff0697 |
| packages/api-client/src/schema.d.ts | c59a37fffd6b008aaa4ef617b5b052fe463407d4d2da267a16ebf45dfff448be |

实际读字节计算：T6列出的31生产源、286依赖范围及SDK10项均全部匹配；T6 manifest的237副本与T5 manifest的36副本均匹配各自copy_sha256及声明original_sha256，合计273/273。没有越权读取原私有case，因此副本核验表示与已提供的原hash声明一致，不把它称为本评审再次读取原文件。

T5历史40项范围现38项仍匹配；API由90ca7048…到e5590552…、CLI由0b0a6eaa…到791d2826…是T5结束后B4/B5的新身份，保留历史差异。T6以新身份实际重复原83，不倒填T5旧批。完整路径/逐项hash、来源/副本/范围记录见 [RV3Snapshot.json](G:/开发测试/Codex/VideoCreatorImplementation/Review/RV3Snapshot.json)。ADR0005 SHA528329d3…、ADR0006 SHA86a01264…为接口方向批准，不是技术Gate批准。

## 实际批次与原失败

下列命令已经由永久测试角色执行；本评审只核其收据/JUnit/源码，未重跑。

| 批次 | 真实终态 | 固定范围 |
| --- | --- | --- |
| T5Original58Regression | 58pass/0error/0skip/exit0，JUnit94.268s | 39项；内外变化0 |
| T5RealFormatsRoundOne | 25pass/0error/0skip/exit0，18.528s | 40项；内外变化0 |
| T6LifecycleRoundOne | 18fail/exit1，JUnit176.911s | 285项；原脚手架失败保留，交接摘要176.99s与JUnit字段不同，两值保留 |
| T6LifecycleHttpRoundTwo | 29pass/0error/0skip/exit0，65.835s | 286项；内外变化0 |
| T6Original83Regression | 0tests/exit4 | 错历史文件名，不能计通过 |
| T6Original83RegressionCorrected | 83pass/0error/0skip/exit0，69.157s | 286项；内外变化0，原六测试SHA不变 |
| T6 SDK类型检查 | 实际exit0，stdout/stderr空 | 10项源码/生成产物身份；不等同HTTP行为 |

新29实际命令入口为 .venv/Scripts/python.exe -m pytest tests/gate0/test_t6_cli_lifecycle.py tests/gate0/test_t6_http_media.py -q；原83为parser6、protocol/controlled35、reference4、B3public13、realformats25六个原文件。完整argv含基目录/JUnit路径及开始结束UTC见各CommandReceipt和 [T6Handoff.json](G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/T6Handoff.json)，正式wrapper命令见 [COMMANDS.md](G:/开发测试/Projects/VideoCreator/docs/acceptance/criteria/COMMANDS.md)。

首轮真实错误分别对应ready标签、cli.main签名、缺token错误码、cancellation_requested所属表。两轮范围差异只在三个新增T6脚手架源及新HTTP测试；生产/原六断言/阈值保持。源读证实当前真实ready为ready、main无传参、错误码session_token_missing、取消字段属于runs；这些更正没有把生产失败写成成功。原18失败及错误命令exit4的文件/hash仍存在。新批1条Starlette警告和原83的112条警告（Crew111+Starlette1）保留，未据此断言兼容性全部消除。

## 公开媒体与SDK

B5唯一增量为app.py:50的ERROR_RESPONSES 415，handler:91—100继续使用唯一Pydantic ErrorEnvelope四字段及原status_code。实际解析新OpenAPI为43个公开schema、18个操作引用同一ErrorEnvelope；content416继续text/plain string，没有第二份媒体/前端Schema。非业务路由404/405仍framework detail，Host400仍纯文本，不能按全部错误都是Envelope解析。

T6 TCP普通副本Evidence094/099/104/109分别覆盖APNG、网络URL、目录外URL、URN。每例两次实际import均415、正确code/retryability=never、request_id不同；两次均无decoder进程、0loopbackGET、无Asset、暂存ready/asset_id=null且输入保持。实际进程观察透传真实Popen，并过滤启动版本检测，不是空mock固定值。目录外文件内容不变本身不是“未读”审计；此处还依赖前置拒绝的固定源码及0decoder，结论不是全OS文件访问审计。

T5新25普通收据已全部实读：真实自产PNG/JPEG/PCM WAV/H264+AAC MP4/纯AAC MP4probe+完整decode+import+content字节相等；四错MIME、两个真实未支持QuickTime/MP3、七畸形/缺流、超限尺寸/像素、实际268435457字节文件、9音轨MP4拒绝。T5是AssetService入口，无HTTP415；T6另以TCP给五格式201、真实两次probe/decode进程、保护content/Range206和416，原垃圾422及401/403/404/409/422、redaction回归。

永久GenerateContracts已包含新增lifecycle.py，并从唯一CLI导出后调用openapi-typescript；owner的I4PermanentSdkReceipt实际exit0、五源前后不变、四产物与窄生成一致。T6独立核产物hash和实际类型检查exit0：415/422类型等于ErrorEnvelope、416等于string。当前只读TypeScript package.json为7.0.2，但T6的10项未冻结Node二进制、TypeScript实现、锁文件/类型检查fixture运行前后身份，286范围亦不含这些；这仍是有限类型检查证据，不能称完整构建工具链冻结。后续正式构建证据补工具链身份即可，不需无因重跑本批。

## 私有生命周期：可支持的范围

lifecycle.py:28—59按字节解析、最多64bytes含LF；超长丢弃到LF，固定精确shutdown LF，CRLF/非ASCII/未知/部分帧不转成停止。ControlPipe自己dup fd、Windows二进制模式及PeekNamedPipe；EOF只结束reader，主API仍运行。flag默认关，main.py:174仅opt-in加入is_stopping/on_shutdown；没有公开HTTP停止端点，也未调用cancel/pause/reconcile或释放未知预留。

controlled_serve:123—178在同loop置Server.should_exit，有界正常等待；timeout发失败，不在finally写成功。confirm_stopped:181—201在loop/listener返回后同时要求实际ready/lifespan/server/reader完成、没有连接/活动task/新增活线程、listener关闭，然后才发固定marker。host还须实际exit0和owned子树终态；marker不是费用/Worker完成证明。

T6独立普通收据证实：完整/部分/重复/早ready帧实际自然exit0；非法帧后health200；默认/EOF三例最后测试owner明确force清理exit1且无marker，不混作正常停止。缺token实际exit1/空stdout无成功marker。观察模式的实际dup fd检查为EBADF，真实状态reader/serve/lifespan completed，listener=-1、新增活线程为空；pending_loop=False来自t6_fault_host.py:85常量，**完全排除其观察价值**。SSE实际先收production.accepted，再自然EOF且queued未取消；0.8s实际在途HTTP正常排空200，0.35s受控窗口实际exit1/无成功marker（客户端500），清理异常实际exit1/无marker。

unknown免费合成实验：before与两次stop/restart的after逐JSON相等，same instance、operation=unknown、reserved=0.2、spent=0、cancellation=0，driver调用仅1次。它证明该合成事实没有被停止/恢复擅改；不是供应商查询、实收费用、活Worker恢复或支付对账验证。

## 问题、证据缺口与待测

### RV3-P01：缺token测试仍用过时ready标签（P3，已证实测试覆盖缺口）

归属：永久测试开发。源码 [test_t6_cli_lifecycle.py:88](G:/开发测试/Projects/VideoCreator/tests/gate0/test_t6_cli_lifecycle.py:88) SHA5fd785f5…断言b"api_ready"不在stdout；真实main.py:165和helper:117使用event=ready。触发：未来错误实现若先输出真实ready后以session_token_missing退出1，该否定断言不会捕获。当前实际普通stdout副本Evidence060为空、固定源create_app在ready前拒绝，故不推翻本批启动失败事实，也不改生产归属。改法：后续T owner新批按实际三字段ready拒绝或断言stdout为空，保留旧结果，不修原收据、不降低期望。

### RV3-E01：unknown首轮进程raw被覆盖（P2范围证据缺口，非已证实生产缺陷）

归属：测试证据；后续新host测试/验收。test_t6_cli_lifecycle.py:135—148两轮复用Child目录，close覆盖ChildReceipt/Stdout/Stderr；普通Evidence110只保留第二轮，Evidence113有两轮结构化facts与exit0。可以支持两轮事实相等和本测试断言执行，不能独立逐轮核完整marker/port/后代/原始输出。改法：后续新批每cycle独立目录保存raw及前后事实；历史首raw继续写missing，不重建。此缺口不阻断本415或其他正常API样本的局部关闭，但不能用它签完整双轮候选生命周期。

### Inspection与范围限制

后端10s正常窗口不能被本样本外推成任意不合作callback/线程/任务都能10s终止；finally gather和asyncio.run收尾仍要等待实际资源，复杂同步阻塞、拒绝取消及新增后台资源未实测。可信host需要独立有限forced owned-tree策略和明确失败分类；这是待测风险，不是本评审已运行出的缺陷。

本报告未审后续I4 host三源的新候选；其owner5场景/32检查不是独立T7或安装验收。新精确包尚需纳管lifecycle及新W4/W5/B4/B5、生成契约、host源、资源与许可后再构建/验收。原68c1f069包及AV0两次CTRL_BREAK exit3保留，不继承本源码API绿，也不借新协议倒改旧失败。

全部codec/其他PCM/两小时时长极值、OS总内存隔离、macOS/Linux、有效Worker/后台移交/父异常、签名/干净机安装、视听品质、真实自主协作成片、语义Bundle/RAG、官方资源商业权限/额度TTL、订阅计费与两平台授权发布尚不在本批通过范围。官方资源应由产品内部允许商用的API/MCP真实生成/查询/取回，不以个人Kimi网页会员替代；未授权收费/发布/部署不能当成功。

标准范围可保持其既有独立冻结，技术Gate和唯一生产框架不能随本局部机制绿冻结。完整目标继续 **Gate0→R1独立验收→连续R2**；FR05/FR10/FR17及CM保留，FR18排除，R2必须保留R1回归。后续实现归owner、补证据归测试、验收归AV，root或本评审均不代签。
