# ADR0019：令牌仅宿主持有的完整原生传输

2026-10-08。批准此增量设计作为后续各 owner 实施输入，不批准真实 API/Worker/原生完整交付或三 OS 通过。ADR0018 原字节保留；其中 renderer sessionToken/direct-fetch 方案及对应 native CORS 接入要求由本文替代。自动审批已拒该令牌返回补丁，I20 确认整批未落；不通过改名、编码、另一编辑工具或媒体通道返回同一秘密。

A16卡 SHA5d46d3d3e08db8f40f8cd9229dc8c20e0192a562a0ea65aa1254367627194f4f；I20正式MD c841cd38de851503433b90240b86e3947faf5fd1c5e7c510aa1b7471e511c76d、JSON a7a5493687a256787577270ca77cacd9ae5d5fd8cbfa7e5710ff98ef7836eff5、Freeze fe901b7d485e3fe8c3f10fea08b12cbfd133f397b696955346c4ef35b0ac53b2、ApprovalRejection cf685f6b15c81d38a05914c42617a04491029c78ee303f93a0630166c88b02fb。原 NativeProbe081b3f59a12378d7ee827864d85852e2bcf463d135c32eccfb230c68ba064608 的 duplicate panic101及WM_CLOSE引号失败/force1保留；新close4a94a411acf210e5144f5e8e3e8dc18626bbc491afd1773a6b2c56cdab5e1988仅证明空引擎主窗自然0/captured8无残树，未开CDP的端口字段缺/null不计端口绿。已有Job源码编译不是实际API归属/父死回收证明。

## 1 固定实例 broker，唯一 SDK

沿 ADR0018 的固定 child/安装manifest/实例锁、受控 ready 三字段、实际端口和受保护 health instance核验。安全随机 Bearer 每次实际 API 启动轮换，只在 Rust 内存与可信 child 环境持有；任何 renderer DTO/header/body/URL/日志/构建常量均不含该 Bearer。只有这些验证完成且实际 child仍活着，broker才ready；当前I20未ready是真实阻断，不填假Bearer或预设地址。

Rust broker仅请求这一已确认本地实例；固定loopback base、禁HTTP环境proxy、禁redirect和任意目标URL/DNS/端口/模块/文件路径，身份异常立即失效。原Backend必须确认正式非浏览器service-client鉴权语义（固定Host、有效Bearer、Origin缺省的处理）；Rust不转发renderer的Origin/Cookie/Authorization，不为了broker放宽已有CORS/允许null或*。若正式接口还不接受此受控宿主请求，交Backend补明确接口，未补前保持unavailable。浏览器不再直接连接API，CSP也不为native页面开放任意loopback fetch；开发managed proxy沿I21独立契约。

公开Python/OpenAPI仍为唯一领域源。Backend正式导出须声明 operation_id、method、path模板/参数、query/header语法、request content-type/body种类、response及鉴权作用域；Integration由同一精确OpenAPI生成不可变 `NativeRouteManifest`，含format/schema/OpenAPI SHA、全部受支持operation及transport约束，与TS SDK/Rust include资源同锁同hash。它是传输映射，不另写领域DTO或手造第二份路由。Rust按operation解析固定路由并编码参数，调用方不能传URL/method/path、覆写Host/auth/origin或额外未声明header；未知operation/旧manifest/版本漂移在HTTP提交前拒绝。raw staging或事件/Range语法若源缺声明，Backend补后重生，不用临时手写放行。

SDK增加 `mode:'native'` 与 `NativeTransportV1` adapter，复用原生成operation、参数/body序列化和 `request`/`requestRaw`。不调用getToken、不在前端构造Authorization；native与I21 managed/direct来源同时出现则诚实unavailable。HTTP/MCP服务调用者仍走原实例协议，长任务不依赖IPC/HTTP连接；此broker不启动另一调度器、不直接调用供应商或代替原预算/权限。

传输format、公开API/请求版本和DB schema彼此独立。新增native adapter不升级已存ProductionRequestRevision、不改旧0.2默认strict/幂等hash/报告字节；0.3自动策略仍须显式版本及可信预授权，按ADR0015—0017与实际Backend模型消费。旧生成SDK在新route manifest不匹配时拒接，不借私有wire v1暗改领域对象。

## 2 私有 wire v1 和有界 request/response

私有format=`native-ipc-v1-candidate`。所有命令经AppManifest/精确main capability，再核真实调用Webview label、完整native URL与预绑定值；session generation及所有handle绑定该实际renderer文档、实例和连接代次。导航/reload、child异常、停止、manifest变化会废弃旧handles；renderer传的generation只防漂移，不是授权票据。无全局事件广播、自由shell/fs/http plugin。既有 `get_engine_session()` 名称可保留，只返回以下非秘密描述；不得恢复旧token DTO。

| 私有命令/字段 | 明确行为 |
| --- | --- |
| get_engine_session() | 未ready固定拒绝；ready返回 `{mode:'native',instance_id,generation,contract_version,route_manifest_sha256,transport_format,limits}`。无token/baseURL/OS路径 |
| engine_request_open({generation,client_request_id,operation_id,path_params,query,headers,body:{kind,length?}}) | 验正式route/body/header与权限，绑定本次request；kind为none/bytes，JSON由唯一SDK先按原序列化生成bytes。返回非秘密request_handle及上传约束，不返回认证信息 |
| engine_upload_chunk(raw frame;私有IPC header仅handle/generation/seq) | Tauri Raw Request承载二进制，不在JSON/base64中装整文件；单handle按seq/offset顺序接收、有界ack后才发下一块 |
| engine_upload_finish(handle,generation,seq,total_bytes) | 严格核长度/连续EOF；只结束HTTP body，不生成或批准Bundle。早响应/拒绝立即停止继续上传，保实际HTTP响应 |
| engine_response_head(handle,generation) | 实际响应headers到达才返回 `{status,headers,body_kind,content_length?}`；上传时SDK并行监听此口，避免服务器早拒绝后仍无限发送/互等 |
| engine_response_read(handle,generation,seq,offset,max_bytes) | 按需读取下一原始body块，返回下面raw binary frame；并发同handle读拒绝，实际EOF才返回EOFframe |
| engine_request_abort(handle,generation,reason) / engine_request_release(handle,generation) | 幂等关闭本HTTP请求/流/队列及handle；不调用production_cancel、pause或供应商cancel；记录可能已受理，不自动重交 |
| engine_response_save(handle,generation,delivery_ref,suggested_name?) | SDK专属native保存扩展；只消费尚未读的原响应，原生OS文件对话框取得目标，renderer无绝对路径参数；从原实例实际固定ref核SHA/size后有限流式落盘 |
| engine_media_open(generation,delivery_ref,purpose) / engine_media_close(handle,generation) | 只绑定经原实例授权的固定视频/音轨/字幕资产；返回本进程私有媒体URI与非秘密逻辑handle，绝无Bearer或下载票据秘密 |

非秘密HTTP业务header仅取生成语法：Accept/Content-Type、Range/条件请求、SSE恢复游标及原真实幂等header等，不能凭本表猜最终header名称。非法覆盖auth/host/cookie/origin/fetch-site、CRLF、双重转义路径或未声明key在Rust拒绝。body受operation真实上限控制，不能以通用32MB/128MiB上限把完整导入/成片能力砍掉；大body走流式，用户数据原本的业务限制另由Backend处理。

raw frame使用24字节小端头：version:u8=1、kind:u8(0=data/1=eof)、flags:u16=0、offset:u64、payload_length:u32、next_offset:u64，后接原payload。offset/next_offset的JSON参数为规范无符号十进制字符串，TS按BigInt/DataView解析，不损失大文件整数精度。data payload<=65536且next=offset+length；EOF payload=0且next=offset。IPC错误走固定typed错误，不伪装EOF。24字节frame头不算HTTP内容/完整文件SHA；禁止重编码原JSON/text/binary。

每个handle每方向最多一项inflight，保留最后一项未确认frame/ack；重发相同seq/offset及相同bytes只返回原frame/ack，不重复写上游；不同正文同seq冲突。读下一seq/offset即确认前一块，结束明确release。不能靠响应丢失就重发HTTP mutating operation。每主Webview最多8个普通HTTP handles，应用层每handle最多2个64KiB缓冲frame；超过限制固定busy而非无界排队。库/内核缓冲另记录真实峰值，不能把应用限额说成整进程RSS上界。

SDK把head和pull reader组装为原生 `Response`/`ReadableStream<Uint8Array>`，highWaterMark=0，不在requestRaw返回时预取整body；AbortSignal与reader.cancel调用transport abort。status/可披露原headers及原bytes保持，非2xx/206/304不重写成200；Response规则要求HEAD/204/304无body。上游JSON ErrorEnvelope原body保留，便利request按原安全错误解析；IPC/网络故障是独立TransportError(code,phase,may_have_been_accepted)，不制造API ErrorEnvelope/HTTP状态或reflect异常原文。

响应headers仅去hop-by-hop及credential/cookie秘密，其余由正式route声明的content-type/length/disposition、range、ETag/条件缓存、retry-after/关联ID等保留；鉴权header不出renderer。Rust设Accept-Encoding:identity并禁透明解压/压缩/转码；意外Content-Encoding在完整artifact校验处明确处理/拒绝，不能把编码后的body当原文件SHA。200完整+真实size/SHA才完成完整性验证；206/304绝不证明全文件。SDK本身的Response合成不声明媒体/Bundle成功。

## 3 上传、导出、事件与失败恢复

导入/素材上传通过File.stream/原生文件来源逐块发送；Rust只接原始bytes并受控转给正式staging operation，不读renderer指定本机路径。明确body length/hash与实际服务端staging receipt再finish/import，网络失联可重查原staging/import key；不保一份秘密/整媒体到日志或JSON。上传成功的HTTP body不等BundleImport完成。

完整导出仍先请求原bundle_export journal、取实际ready ZIP/完整ref，再原字节下载。大文件由engine_response_save受信对话框+同目录私有partial文件+有限chunk流写，真实结束/长度/SHA/父Bundle版本核全后原子提交；缺证据或取消保固定失败，清理只限本次拥有partial，不能覆盖不相关用户文件。另取原服务器受保护delivery metadata验证ref，不信renderer自报SHA。SDK以WeakMap绑定native Response/handle，save与ReadableStream只有一个消费者，已消费的handle拒save；不为保存拼完整ArrayBuffer。普通网页传输继续原方式，不获得native任意fs权限。

Range/If-Range/ETag与206/304沿唯一源语义，取完整文件不得把分段结果/未消费原Response标完整；zip/html/json/音视频均按实际MIME及字节。选择投影、引用、撤销/过期、跨实例ID权限仍在Backend，broker没有本地绕过路径。

SSE走原认证HTTP bytes的pull stream，SDK fetch式解析保留event_id/sequence和原顺序；切断/慢reader保有界背压，按最后已消费游标重新订阅/补读，由Backend持久事件决定gap。缺sequence/过期游标按正式契约报告，不自造事件或丢掉重复边界。连接取消/窗口隐藏/timeout不是制作取消；production_cancel只由用户明确业务动作提交同生成operation并落原账本。单次production_create受理后浏览器/IPC断开仍由真实Worker继续，恢复查原ID/key，不盲试收费。

连接deadline、head等待、上传/下载idle有界；上传head deadline从body结束或实际早响应阶段区分，不因大body花时误判为未提交。SSE使用正式心跳/恢复策略，不给几分钟制作套一个短全程HTTP timeout。实际401使宿主session进入失效并中止handles，重建仅走受控真实child；403/409等业务拒绝不改Run为已完成。HTTP已提交但无响应返回may_have_been_accepted，幂等重查原服务事实，原unknown/预算/租约规则保持；broker不清预留、不重渲染。保留部分bytes和实际网络错误的证据，但不把断流转换成正常EOF或partial成功。

## 4 视频/音轨真实播放与 seek

大媒体播放采用Tauri私有 `native-media` protocol；它是固定已授权artifact的资源通道，不是自由文件URL、任意远程HTTP或Bearer别名。官方 [Tauri2.12.1 UriSchemeContext](https://docs.rs/tauri/2.12.1/tauri/struct.UriSchemeContext.html)公开webview_label/app_handle。每次GET/HEAD实际context需为main且当前完整URL/文档generation仍匹配；handle只是逻辑定位，猜中/复制URI到其他窗口、外部页或新代次不授权。注册协议自身没有capability自动保护，必须复用同一Rust source/状态守卫。

URI仅指向Rust已绑定的固定delivery_ref；每次range经原Backend重新核项目/票据有效/撤销/内容版本，Rust注入内部Bearer，renderer或URI没有auth/本机路径。API返回的外部下载URL不用于native协议跳转。原生协议响应CORS如需要只给已绑定main origin，无*或null；不改变Engine原CORS。CSP仅给此实际协议表示所需media-src/字幕资源，主导航/new-window仍拒它作为新页面。

Tauri异步responder返回整段Cow/Vec bytes，并非无限流；不照抄官方示例无Range时read_to_end整个视频。协议每range响应最多1MiB、最多4个inflight媒体片段，验证实际Content-Range/长度/总size/ETag后才响应；较大/开放range拆为连续有限206片段，拒无界multipart及错误范围。单次206仍不宣全SHA通过。无Range的大响应不全读：保明确range_required/不可播放，并由Test实核各WebView是否按此有限range连续读取和seek；若某支持平台不兼容，必须完成该平台的受控播放适配再过R1，不能放宽到全文件常驻内存或删三OS目标。小文件的完整有界响应仍核200完整字节。

关闭播放器仅释放该media handle/请求；关闭主窗或generation失效释放流资源但不取消制作。独立实测MP4/旁白/混音、暂停/seek/字幕、长媒体慢reader/撤销/断流及实际内存峰值，不能以URI生成/JSON health代真实可播放。所有scheme路径/Windows转换形式从实际Tauri helper/锁版构建核定，不给renderer自填origin或任意asset scope。

## 5 重复实例与生命周期切片

OS锁真实拒第二实例是正确事实，但setup panic101不是正常用户错误。Integration在setup内捕获typed `InstanceInUse`，设置startup_rejected、显示固定用户提示“该实例已在运行”，不启动API/Job/Worker/返回ready；安排本次app.exit(2)，setup返回Ok而不是Err/expect/panic。其他可预期权限/数据初始化错误同样受控提示+非零退出；系统构建/run本身的失败保真实1，不洗成0。首实例/锁/窗口不改、不杀；没有证实已有本机受信激活通道时不伪focus或无条件删除锁。Rejected进程的退出分支不得被“后台继续”prevent_exit钩子阻住。

四个阶段分别验收：①pre-ready/重复实例：无API、未ready源守卫，受控exit2；②空引擎窗口关闭：只核native/Webview自然0与自有树，无API marker/无worker，也不捏造未启CDP端口绿；③实际API关闭：先禁新broker请求，按ADR0005固定shutdown LF、真实scope=api marker/exit0/端口及owned树核，不拿①②替；④真实制作/后台：只有实际托盘和独立Worker owner可确认才隐藏/继续，不以API已停说仍制作。

关闭窗口、连接abort、用户production_cancel分开。完全退出与异常父停保原持久Run/Step/Operation、unknown核实及租约fence；不以断开broker擅自取消或重交。ADR0018 Windows suspended→owned Job→resume/父失forced、POSIX固定guardian及前后台所有权界限保留，但当前Job/guardian/Worker/托盘实际仍未测。原force1/panic101红、新window-only0和后续API/后台结果分别保存。

## 6 实施顺序与完整目标

Integration只写自身desktop Rust broker/平台/manifest/锁、SDK native adapter及生成NativeRouteManifest；新增src/transport.rs/src/media_protocol.rs在原desktop白名单。不写Backend/Frontend/测试。Rust固定loopback HTTP client候选reqwest0.13.5（官方metadata/MSRV1.85实得，未安装），default proxy/redirect/压缩关闭、stream能力同当前Tauri/tokio实际锁编译核；缺feature/依赖由集成记录并有限裁定，不借SDK改框架。

Backend正式全源先交CLI/鉴权/health、原始staging、event cursor、Range/条件请求、完整headers/body/幂等契约；Integration再按实际源生成SDK/route映射并封装匹配完整引擎。未交前可实现source/frames/duplicate守卫和诚实unready负向，不能用mockBearer/native健康假响应签联调。Frontend只消费真正 `mode:native` adapter、原Response/流/保存/媒体handles，界面保五步；不兼写Rust/SDK或让用户填写Bearer。

W11工厂正式f46176340b97d11c45c35be79d0dba8d89e936861e28c4b9b08d60a4c5ad6189仅固定入口/参数，当前只provenance_reference、新资源与旧I16 stage不匹配。其新provider/worker/loader需Integration独立新封装；embedded_full_report的可信完整报告/可披露许可读取端口由Backend另交后Media实现，保持此完整需求pending，不以已有分支缩目标。现authority/benchmark/独立参考、MM03/MM05及自主模型创作仍缺独立准入/实际产品证据。

Test写真实新增标准：无秘密DTO/错误源/handle跨代及横向访问；实际API/SDK合同匹配；chunk重复/乱序/背压/EOF/早拒绝/取消；>128MiB实际上传/导出、原bytes/SHA、Range206/304/错误JSON、SSE恢复与慢reader；视频/音频/字幕真实播放seek；duplicate自然2不panic/首实例不变；各生命周期切片/实际Worker持续及未知恢复；跨OS安装/资源/许可/原自动成片门。Review独立批实际标准与实现，Acceptance实看实听；本ADR不是标准批准或产品pass。

原全目标Gate0→独立R1本地自主视频/API/MCP完整多模态/三OS→连续R2保持。真实缺机器/完整发行sidecar/CRT及媒体库分发/方法资格/官方资源照实pending，官方订阅仍须产品内部允许API/MCP直接生成/查询/下载/对账；官方登录失效不锁本地。本轮仅架构/文档研究，无产品/测试/安装/凭证/模型调用/费用。研究资源credits单列，终态及正式hash见NativeTransport-A16交接。
