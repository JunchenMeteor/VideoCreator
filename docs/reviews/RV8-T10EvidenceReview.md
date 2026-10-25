# RV8 — T10 正式独立证据有限复审

阶段 FINAL。永久独立评审只读 T10 正式交接、100份普通副本和历史 I7 四源；没有执行或重跑测试、导入产品、操作进程、读取密钥、修改实现或标准。本轮不重复全历史审计，不关闭 RV7-P01 / RV7-I01；两项另待 I9 及其独立证据。

## 身份与结论

T10Handoff.json SHA `ff395377d257e1d00cae3939fec5b4ce97b7004797d3d5726c91ba2f46f364f9`；MD SHA `258b2f6dde76b6ee5082e8267351da0e58b03ad3feca62849bef1d88043982ca`；普通副本manifest SHA `19fc54c9a4cb97cea243f5889e0b001d550db838dc3a7a11c39fedd891e3fae9`。三者实读hash与统筹正式身份一致。

100个普通副本逐份实读hash，全部与copy_sha256及清单声明的original_sha256一致；没有读取私有案例原目录或改变ACL。历史源码使用 T10Evidence089—092 的普通副本，全部匹配：

| 历史 I7 源 | SHA256 |
| --- | --- |
| tools/build/DevRuntime.mjs | eaf146f36afc674770efa4d4c65e75ae232e8a96d5b96206d8a5cd4f466265da |
| tools/build/EngineProcess.mjs | 3b6716f93e05122a718e41d4bfbbcf330d706be3b4412f271816729c08eed076 |
| apps/workbench/vite.config.ts | c5cf940ca7aba73896e70ae37a4fd0177fd1d1d0e16370e972c35047d8ff6932 |
| packaging/RuntimeContract.md | 5b3200f5dd5c96aa44abd26045a38a553c29a34a0633d2838d152883f23bce4b |

T10SourceCopyStatus 的 copied_tested_bytes=true，与实际副本hash一致。后续 I9 当前工作树没有被读来代替这些源，不倒填任何新源通过。

**本批有限证据一致，可支持历史 I7 在所测18项 Windows 开发入口机制上的独立结果；没有新增阻断性证据问题。** 仍不是完整信号/通道/并发准入、整体技术冻结或 Gate0/R1/R2 验收。

## 三批原子结果

| 实际批 | 实际句柄 | JUnit case / fail / error / skip | Node / UTF8包装记录 | 总耗时 | 原子源范围 |
| --- | --- | --- | --- | --- | --- |
| T10PositiveRoundOne | 34816 | 1 / 0 / 0 / 0 | 0 / 0 | 11.5345142s | 296，范围内外变化0 |
| T10ProtocolRoundOne | 38774 | 4 / 0 / 0 / 0 | 0 / 0 | 39.3418374s | 298，范围内外变化0 |
| T10StartupRoundOne | 85707 | 13 / 0 / 0 / 0 | 0 / 0 | 22.0770507s | 298，范围内外变化0 |

共18项，不叠加旧19/83或owner自查。三份CommandReceipt的实际argv与正式交接一致；stdout/stderr SHA、JUnit SHA均与已核普通副本一致；各source before/after、all_source before/after、交接完整map及变化列表一致。CommandReceipt的exit为实际Node子命令；UTF8外包装exit依据正式T10终态记录，来源分别保存。

| 批 | CommandReceipt SHA | JUnit SHA |
| --- | --- | --- |
| Positive | d37349b042581934b0731f63fc2b46a485765087c5ab76a43a965a004c4458bc | 27cb302aff3ab2d01a9aafa748907f64ea35332d8c139478a2197de852197aaf |
| Protocol | e93677e04a3d7c22cc463afe2e6d8ea9ffefadf43df669cfa37c378013770ff2 | e051cbeb64347ec3d35f0970d39777969b5baf2f3ad2dfe4ed2a81e2569ebed2 |
| Startup | c9fc812712220d07e9be12316ba01cc190270d94f53805b78e49c0364e78c5f9 | a12f6e2c9f04a039bfb438e0b5a7a58c9ee6509ab896f3ecc1e9e8f493fe541a |

真实命令均为Node `--test --test-concurrency=1` 加spec/JUnit两个reporter，分别执行 `t10_full_runtime_positive.test.mjs`、`t10_full_runtime_protocol.test.mjs`、`t10_full_runtime_startup.test.mjs`。完整argv、cwd/开始结束和XML标题见 RV8Handoff.json 的 verified_batches，未在本轮重跑。

T10RuntimeInputs 普通副本记录282个路径、16个包。Positive、ByteProtocol、DefaultOff、EarlyBuffered、Eof、OccupiedDefaultPort、OccupiedExplicitPort 七份收据均有282个运行文件before/after且逐路径hash无差异。本评审核对的是已核收据的原子map及路径清单，没有重哈希当前运行资源并宣称全机或新工作树冻结。

## 可支持的具体机制

正向是未切片的真实 DevRuntime → Python API → Vite，经 actual spawn PIPE 输入9bytes。测试读取真正工作台HTML200（含src/main.tsx）和同源health200、worker=false、media manifest verified，并对外来源、缺marker、错误marker、缺来源标记四种实际请求得到403。自然host close0/signalnull、host scope controlled、API normal0/marker1与Vite owned_force实际exit1/动作均分别保存，captured PID/创建身份无剩余；这不是Vite graceful或Worker正常停止。

首正向 T10Evidence016（SHA `79c00b85eacb244c8bccffc263364124943e0a34f9063726b7488502d3c9efda`）的workbench端口有独立TCP检查；API端口字段来自产品stop观察并有独立PID消失。**它没有独立发现API监听端口后逐端口TCP观察的首批证明。** 不用后续证据回填该首批。

另Protocol ByteProtocol的 T10Evidence019（SHA `a50dd44a226426a8f171106ba2071ee950fda309983724fb7d789effc16d71da`）由captured自有PID独立发现实际API63504和Vite52852监听端口，终态逐一观察closed=true；helper只把明确ECONNREFUSED判true，timeout为null，不把端口未知当关闭。九种非法字节输入（CRLF、前后空格、JSON、大小写、空帧、非ASCII、超长内合法后缀、64bytes未知）均真实保持health200/live，再经分两次写入的精确完整帧受控关闭。该协议批独立补充TCP证据，只属于自己的新实例/新时点。

正向的自有holder保护是非空创建身份（PID54032）前后相同、HTTP200，最后自身IPC自然exit0。Protocol兄弟同样非空；默认1420及显式端口冲突用真占位holder保持HTTP200、原PID/创建时间不变，实际host error/非零、无伪ready，最后holder自然退出。原22508在正向before/after为空，记录为absent_not_claimed，不称当时保护了运行中的旧实例。

DefaultOff（T10Evidence022）和partial EOF（T10Evidence028）输入后真实health200/live，没有产品stop事件；之后测试按自有捕获创建身份执行force teardown，实际host exit1、独立端口关闭和剩余为空。这是测试为了清理实例而强制结束，**不属于产品normal/controlled完成、自动取消制作或后台移交**。对应测试pass验证“不应自动停”的预期，不将实际子进程exit1洗为产品exit0。

EarlyBuffered实际提前写完整帧，host exit1、stopped_before_ready/error、API真实normal、Vite not_started、无dev_runtime_ready；owned_cleanup_complete=true只描述其已有资源收尾，不表示host成功。早帧行为样本不裁决reader在创建engine之前建立的源码顺序，也不关闭RV7-I01。

启动13项包括8个实际参数/重复flag拒绝、真regular-fd0观察与显式控制拒绝、显式及实际默认1420的strictPort冲突、缺媒体资源文件、同write重复完整帧。regular-file配对观察的fd0.regular_file=true，真实产品host_control_pipe_required/exit1/无ready；并非模拟TTY。重复完整帧实际只一个controlled停止事件/marker1/host0，不等于已覆盖并发异常child或真实Windows信号时序。

## 未测与保留

- RV7-P01信号分类与RV7-I01创建顺序继续开放，另由I9/Architecture及新独立批处理；本旧源18绿不能关闭源码问题或提前借给新源。
- 真TTY/character device、任意Readable/未知stream、真实Windows SIGINT/SIGTERM handler可达性及部分并发异常、defaultoff+regularfile组合未测。合法真实PIPE已被产品接受，但本批没有单独发出合法PIPE的Socket/fstat观察记录。
- 282文件闭包与296/298原子scope不代表全部OS/编译器/依赖或生产环境冻结。观察HTML/输出无凭证字段仅是有限匹配检查，不声称穷尽任意秘密泄露；未继承/读取供应商key。
- 原I7 owner70558夹具挂起/forced1、51858缺立即after，以及已知历史失败/原始缺失保持；未补写缺失历史或重跑旧19/83。
- native父硬崩溃/JobObject/Worker/费用、精确候选包/干净三OS安装、完整UI听看、自主模型作品/公平编排/Bundle-RAG、官方商业资源/支付/发布及完整Gate0→R1独立验收→连续R2均不由本有限阶段签通过。

## 交接

统筹可登记历史I7所测机制的18项独立证据已核一致，继续I9及后续独立测试/评审/验收，不为相同结果重跑全历史。报告为 `docs/reviews/RV8-T10EvidenceReview.md`，过程与完整copy/source/原子核对为 `G:/开发测试/Codex/VideoCreatorImplementation/Review/RV8Handoff.json`。

仅写上述两文件；评审测试运行0、费用0、真实key读取0、产品进程操作0、实现/测试/标准修改0、构建/部署0。安全PowerShell require_escalated绕过已知F盘启动器问题，未解锁卷或改ACL。阶段FINAL后释放槽。
