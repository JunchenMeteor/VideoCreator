# T15 完整Bundle与ASR候选验收标准

版本gate0-bundle-asr-evidence-v1，candidate revision2。状态：待独立批准，尚未执行产品。本文件和同名JSON为测试标准，公开对象只使用后端唯一Pydantic源，不另造接口。依据01—11、ADR0012/0013及B9已固定两模型/消费端口。保留T14原结果和历史正文缺口，本轮不重跑。

## 交付及真实证据

默认video、narration_audio、mixed_audio、approved_script、actual_transcript、subtitles、semantic_manifest、rag_chunks八项齐全。SRT/VTT、封面、洞察/Brief/计划、来源/镜头表、作品摘要、质量报告及所需权利许可是固定附件。实际文件hash与规范记录hash分别复算；每个引用对应精确有序文件/资产/文本材料。文本走受控Material，媒体经真实Asset及解码。旁白/编码前PCM混音用途和真实生产链分别证明，相同声音不能靠复制文件凑用途。

主转写只来自最终mixed或已登记MP4解码音轨。参考稿不进入ASR输入；完整迭代输出、原始raw、模型commit/所有资源hash、真正compute/runtime/解码samples/PTS分别保存。中文漏词/多词、不可辨、静音/音乐及非零偏移是实际样本。空segments不是静音证据，词概率不是时间精度。

缺可信标注听审和authority时，默认utterance_verified与空降级要求保持alignment_required/waiting_user，不发布完整包或success。精度positive需要独立人工标注文件与裁决收据在测试基准中固定hash、服务端可信authority注册和真实音频/alignment/report逐项绑定；payload的true、模型自报measured或返回true的测试callback只算机制，不能计真实精度通过。全标注unit不可挑选；候选计算每语句起止绝对误差最大值，再按nearest-rank ceil(.95N)取P95<=200000us。算法数学定义由RV16单独批准；整套fixture、语料与authority入口仍待独立审批；没有另行批准词标准不宣词精度。标注人员/方法/音频坐标/样本hash/听审工具/争议裁决及逐unit误差必须可核。

当前独立时间标注/听审基准、authority注册、MM05人工标注30选题/60作品均未就绪，真实精度与MM05 positive状态为not_run。原W8单素材跨容器时间差和59字比较不是ground truth精度。RAG文件存在不代表检索合格：至少30选题60作品、同题异事实/过期/受众/画面不符负例，precision>=90%且报告recall/refusal；全拒答不能过。精确文章版本关系须100%保留并支持失效停止推荐。

## 时间、权限和成包

所有range为非负整数微秒半开区间且不越实际解码。源sample/PTS和目标时间线分别持有；真实crop/place/stretch/encoding关系按有理数及各边界half_up_us独立核，不能双改sample/duration或offset使metadata自洽。字幕使用ADR0013 contain-capped-v1，同SRT/VTT误差绝对值<1000us，末尾/相邻/声明重叠/坍缩均核，量化误差不是ASR精度。

完整可见必须在精确不可变文件持久化后，同事务写Bundle/交付Step/Run/Production/outbox。unknown/failed/未结清Operation、过期fence/取消/缺项/漂移不得publish；清理未知不能当确定失败或settled/refund。真实kill两窗口、原journal/ID/hash/fence、重新核实不再生成及outbox去重分别测试。SQL仅只读观察，禁止补业务求通过。schema4迁移/旧版本拒绝/一致备份恢复另测，不降user_version伪回滚。

主体从认证登记构造，payload/recipient不能扩大权限；owner与Portal独立凭证映射。每次Range、304、分页、语义及导出读前校验项目/用途/grant/到期撤销，范围外不返回字节或计数。严格包路径、ZIP全集/大小/重名/CRC、完整与projection、第二实例原origin字节与本地locator/主体独立分别核。没有embedding/厂商账号仍能重建文本索引及精确定位；索引失败与importready分别记录。已有合法离线副本不冒称可远程撤回。

## 分批执行与边界

下表是拟执行场景。real要求真正入口及实际字节，injection仅说明故障机制；每条还需被测源与真实接口稳定后绑定，不是已运行。未来先阻断/前提负例，再有独立基准的真实完整包，再崩溃/权限/跨实例分批。每批只有统筹准入和标准独立批准后可运行。

| 编号 | 需求 | 分类 | 判据及证据 |
| --- | --- | --- | --- |
| T15-01 | MM01,MM02,G0-CONTRACT | real | 默认新请求固定8输出、附件齐备；不自动扩大显式子集；新最小请求→固定request/hash/policy；合法subset副作用前output_profile_unavailable/waiting_user且0生成 |
| T15-02 | AC17,MM02 | real | video/旁白/mix_master可独立完整decode与视听；用途/真实生产链各自证明；不能复制文件充mix；无其他声源导致bytes相同需独立chain；抽样播放和独立AV另有真实收据 |
| T15-03 | G0-CONTRACT,MM04 | real | Manifest实际UTF8/LF字节hash，全部精确文件/hash/size及material/asset互斥；文本严格类型验证不走media fakeprobe；缺项/双locator/错hash/未知角色/依赖环拒；不扫描私有文件 |
| T15-04 | G0-CONTRACT,MM04 | real | JSON/JSONL嵌套重复键及非有限数拒绝；规范记录hash独立复算；数组/原文/Unicode不偷偷修补；Manifest不含递归自身hash；rawhash与recordhash分开 |
| T15-05 | MM02,G0-ALIGN | real | 实际主转写只由最终mixed PCM/已登记MP4解码音轨输入；参考原稿不送ASR；原稿含漏/多句反例；保完整输出及不同revision，不复制脚本 |
| T15-06 | MM02,G0-ALIGN | real | 中文、非语音音乐、静音及不可辨语音保持实际结果/真实gap；ASR empty不是silence证明；无词时据实际信号/审核记录gap；不能造台词满足非空 |
| T15-07 | G0-MEDIA,MM02 | real | ASR decoded identity绑定真实音频path/hash/size/sample/PTS；模型/库/compute真实固定；self-consistent输出不等于可信；取输入实际probe、资源model每文件hash/commit和真实worker元数据对照 |
| T15-08 | G0-CONTRACT,MM07 | injection | 实际driver接收坏输出拒：bool PTS/双sample-duration改/双offset改/language类型/compute虚构；使用自己可控raw child输出，原命令/异常保留；不称模型攻击/真实ASR正向 |
| T15-09 | MM03,G0-ALIGN | real | 默认utterance_verified/allowed_degradations空；无独立精度基准alignment_required/waiting_user；no BundleRef/success/outbox；词估计/复制对比时码/伪measured/人工未听不能凑默认正向 |
| T15-10 | MM03 | real | 可信authority来自固定测试基准+实例配置；实际report对所有标注unit精确绑定与复算；未知authority/客户端bool/篡改report/audio/alignment/reference/挑好样本拒；评价输入不可用candidate自身定义 |
| T15-11 | MM03 | real | 语句P95<=200000us；每unit最大起止绝对误差nearest-rank候选算法；完整标注集合、误差列表、样本数、ceil(.95N)位、听审版本保存；算法须本候选独立审批；词级不冒用语句指标 |
| T15-12 | MM03,MM07 | real | word_verified仅按固定显式降级+服务政策+批准事实允许词估计，语句仍核实；旧请求无字段不是许可；伪ApprovalRef/越policy/未测词精度不标verified；校正另版本不覆盖ASR |
| T15-13 | MM03,AC17 | real | 旁白/mixed/MP4编码轨真实逐片段映射，非零正负PTS offset、裁切/拼接/变速；实际sample/PTS有理数和真实transform先比，独立half_up_us边界误差再比；不靠元数据自洽或任意容差 |
| T15-14 | MM03,AC17 | real | 所有微秒半开range非负不越真实decode，音轨固有与作品原点分明；同持续时长不同audio_id/stream/mapping片段不可互换；有符号encoding offset不冒负MediaRange |
| T15-15 | MM03,G0-CONTRACT | real | SRT/VTT同策略contain-capped-v1与原cue逐一对应，误差<1000us；floor start/min(ceil end,floor timeline)/非重叠相邻前end截后start；重叠声明保持；坍缩422不改原cue |
| T15-16 | MM06,AC18 | real | 精准来源查回namespace/system/article/topic/fact准确版本全部保持；同ID不同namespace/新版本/同题不同事实不串；local confirmed_facts不伪称Portalfact审批 |
| T15-17 | MM04,MM06 | real | segments→视频Range/audio_spans/mapping/shot/transcript/rights→RAG逐项一致；同规格shot2/3交换、共用segment/assets、错误origin/文字与实际speech不符均拒；仅prompt/色板不是实际画面 |
| T15-18 | MM02,MM04,AC18 | real | 画面语义有最终帧实际hash/PTS/decode证据；标明observed/inference/user/derived；provider自报frame-verified/计划描述不能替代可信framevalidator；speech与真实transcript关系不靠同文本hash |
| T15-19 | MM05,AC19 | real | 固定>=30选题>=60候选人工标注，精确率>=.90并报告召回/拒答率；包含同题异事实/过期/异受众/画面不符负例；全部拒答不达标；纯引用与Portal索引分别检验 |
| T15-20 | MM06,AC18 | real | source/Bundle旧revision不可变；expiry/revoke让索引停止推荐旧结果；旧导出合法副本不会远程撤回；新内容不回填旧request/ref/manifest |
| T15-21 | AC08,MM04 | real | 可信认证层principal/project/purpose形成AccessContext，不接受payload主体；owner/Portal不同登记credential；recipient伪造、跨主体相同IDs、foreignorigin不是本地权限 |
| T15-22 | AC08,MM04 | real | 未授权检查先于Range/If-None-Match304/分页计数/语义读取；无字节/记录/资源存在泄漏；跨主体404/已知scope403/auth401；既有Host/Range框架边界不伪称全JSON |
| T15-23 | AC08,MM06 | real | grant仅缩小原scope用途许可有效期，expiry/revoke真实墙钟后每次读失效；不凭固定ID访问；撤销后再次Range/304/page不能泄露；长连接即时撤销未测单列 |
| T15-24 | G0-CONTRACT,MM04 | real | 权利/方法/附件白名单完整，缺license/用途/到期权限不能默删后整包成功；SAPI试验商用权不自动授予；秘密不进export/log/Flow/manifest；用自己marker而非真实key |
| T15-25 | MM07,G0-CONTRACT | real | unknown/failed/unsettled Operation禁止publish；旧fence/取消/漂移重核拒；B7核实grant没有正常publish权限；不清unknown、不重render/收费、不SQL补业务 |
| T15-26 | MM07 | injection | cancel/deadline输入真实执行回收子树；清理无法确定必须unknown且不确定settle/refund；leader0不等全子树净；PID+Creation+退出/句柄/port核，自己的nativechild；模拟lookup失效仅机制 |
| T15-27 | MM01,MM04 | injection | 精确文件落盘→DB commit前真实kill不得半包；原revision文件只核实不再生成；原hash/ID/journal/fence保留，墙钟lease，新进程读取/只核实；不扫目录或覆盖manifest |
| T15-28 | MM01,MM04 | injection | DB commit→Flow前真实kill靠已提交Bundle/Step恢复，不再成包；原manifest/items/Step/Run/Production/outbox一事务可见，success仅其后；raw事件不模拟Flow事实 |
| T15-29 | MM01,MM07 | injection | 同input/key并发只一BundleRevision/成功event；异input409，旧请求hash不回填；固定成本/Operation/版本保持，事件unique；freezip不用新的模型Operation |
| T15-30 | MM04,AC13 | real | 完整ZIP保原Manifest和文件全集精确hash，真实export job持久化202后才返回；独立export lease/fence、API断开任务不取消；重启原journal核实，不借成功Runlease；CLI0不是jobready |
| T15-31 | MM04,AC13 | real | projection独立delivery.manifest闭包/parent origin/用途hash，真实文件可读；不带缺项却自称完整Manifest；projection导入完整Bundle必须415 |
| T15-32 | MM04,AC13 | real | ZIP traversal/绝对/反斜线/盘符/链接/重名大小写/重复/缺项/额外项拒；自己Marker在包外前后字节不变，无外网/private路径；小有界fixture，不造巨zipbomb |
| T15-33 | MM04,AC13 | real | 归档实际compressed/uncompressed/membercount/单entry限额在写前核；具体产品limit待固定handoff记录原值，测试不提高限制；构造实际limit邻界和中央目录错误/CRC |
| T15-34 | MM04,AC13 | real | 第二独立实例import保持origin Ref/Manifest/semantic原字节和ID，另建local locator；同名origin revision不同instance/hash不碰撞；foreignRun不是localProduction；local mapping不串权 |
| T15-35 | MM04,AC18 | real | 无embedding/厂商账号可导入、重建文本索引、精确媒体定位并重导出；实际本地保护读/API+MCP同入口；index失败保importready且indexfailed，不冒匹配90% |
| T15-36 | G0-CONTRACT,MM04 | real | 固定版本/OpenAPI/SDK/API/MCP同一公开源及唯一ErrorEnvelope真实正反；409/401/403/404/413/415/422/503声明及真实status；frameworkdetail/Host/Range例外保存 |
| T15-37 | MM01 | real | 完整最小目标资料到作品一次HTTP/MCP触发，断开继续，在授权审核点等待；人不补脚本/分镜；本阶段真实template物理包不算自主LLM或unattended质量；未授权付费保持未测 |
| T15-38 | AC01,AC07,AC13 | real | 三OS安装离线资源/许可、横竖媒体、干净系统及跨实例备份另验；本机Python/WAV/模型存在不代表exe/dmg/Linux发行；缺机/听审/许可列not_run，不skip算绿 |

## 拟夹具、输入和命令

tests/bundle/t15_evidence.py只做自己包内精确字节、strict JSON及即时fsync日志；t15_oracles.py是独立证据断言，不是生产模型；t15_adversarial.py生成有界坏raw/ZIP；t15_fixture_sanity.py仅测试这些纯夹具。tools/testing/t15_prepare.py只AST和纯sanity，不import产品/启动ASR/操作DB。其真实命令与结果在本角色收据另存，不能作为上表产品pass。实际服务/HTTP/MCP适配及可信资源入口待最终handoff，未提供的入口不虚构已实现，不以skip/fakepass代缺项。

未来launch前保存完整生产正文和测试正文普通副本，声明所有实际消费源/库/工具/资源before-after及hash，不能拿后来B9正文补T14。自己隔离DataDir、真实PID/Creation/heartbeat/lease墙钟和非空健康兄弟保护即时落盘；原handle/raw/真实exit/JUnit/失败/子树端口清理保存。工具/资源未固定即不launch，不盲重跑。固定候选后停止修改交独立评审；修订保存原候选/红/审批hash，按新版本复验，不降低原MM03/04/05或回填旧请求。

费用/key/vault读取均0，不用ValidationInstance或他人私有Case；攻击仅自己有界marker/loopback，无外网DNS、私密文件或真实账号。Windows Job有限证据不冒完整App、TTY或三OS；真实AV、API/MCP断开持续、自主Agent、Portal检索、安装及商业R2仍需独立验证。Rollback仅移除未执行Test候选/拟夹具；产品DB与请求完全未改，旧标准/历史保持。Gate0→R1独立验收→连续R2范围不缩减。


## 修订2：仅RV16两个Test P2

原revision1 JSON/MD、17普通副本和9项纯sanity收据完全保留，另有17原字节归档。RV16批准P95数学定义，不批准整套criterion/fixture或运行。修订2仍not_ready_for_execution，38项为拟case，实际服务/API/MCP/ASR业务适配及人体基准未就绪。

P01：strict JSON入口parse_float在合法数值token转换后检查finite，拒正负及嵌套1e999/-1e999；parse_constant和重复键原守卫保留，有限float/原数组/Unicode语义不改，不采用Decimal改变公开hash语义。

P02：任何ID→range映射前，核原alignment列表完整长度、每条range、unit_id与transcript_unit_id的严格非空字符串及唯一性、独立基准/report完整一一对应。坏先好后、反向、同值重复、遗漏/额外/替换ID、非法ID类型/坏隐藏range均不能通过；报告自己原条目也按完整集合核。不去重、不改原数组，正常200000us门槛与完整20unit nearest-rank不降。

Before在旧helpers真实执行新增断言：21 unittest tests、17失败subtests/1错误、exit1，原nine正常检查仍在；仅测试oracle/strict JSON自身红，不是B9产品红。After同断言仅修两个helper：21tests/0fail/error/skip、exit0；包括正常200000us接受、200001us拒绝、20units P95=190000us。合成reference/authority字典只测试数学/完整性，不是可用真实基准。未执行ASR/decoder/DB/产品入口。

当前准备入口tools/testing/t15_revision_two.py，实际Before/After目录、源码正文/原身份、stderr/stdout和收据见TestDevelopment/T15RevisionTwo*。旧t15_prepare.py只属revision1原九项历史入口，不作为新版完整sanity入口。当前候选与全部新拟夹具固定后交RV17，不根据本轮绿提前产品运行。
