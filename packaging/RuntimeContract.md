# F2 本机运行时交接（候选接口，2026-10-08）

此文件保留分阶段历史记录。当前 portable 启动候选接口见 [IndexedRuntimeContract.md](IndexedRuntimeContract.md)，依据 ADR0023；尚未运行准入。下文早期 `engine_connection` token DTO 是已废弃提案，不是现 native 接口：Bearer 仅可信宿主和 child 持有，renderer 不接收 token/base URL。各历史 probe/版本不得外推当前 artifact。

## 已实现并实跑：开发工作台

源码入口：`G:/开发测试/Projects/VideoCreator/tools/build/DevRuntime.mjs`；构建代理：`apps/workbench/vite.config.ts`。

从项目根启动（DataDir必须绝对路径，选择无模型route的独立实例）：

```powershell
& 'C:/Program Files/nodejs/node.exe' 'G:/开发测试/Projects/VideoCreator/tools/build/DevRuntime.mjs' --data-dir 'G:/开发测试/Codex/VideoCreatorImplementation/Integration/DevInstance'
```

也可`pnpm dev:runtime --data-dir <绝对实例目录>`。I3真实后台host PID22508，日志`Integration/Logs/DevRuntimeMedia.*`；应先核PID命令身份再停止/重启。访问`http://127.0.0.1:1420/`。已有SDK`@video-creator/api-client`通过workspace导入，业务类型唯一来自43个Pydantic模型/OpenAPI，Schema版本`0.1.0-candidate`。

F1开发请求使用相对路径`/api/v1/...`；每次fetch带`X-Video-Creator-Client: workbench`。无需获取token。代理只允许Origin1420，或Origin省略但Sec-Fetch-Site为same-origin；不接受外站/跨站/缺标记/未配置引擎。启动器持有随机32bytes会话token，仅传入引擎和Vite子进程非VITE_环境变量；由代理附加Authorization，HTML/URL/构建产物/localStorage均没有token。所有API响应no-store。该防护针对跨站网页，不把同一OS用户可控制的恶意本机程序当作隔离边界。

实际正反探针：HTML200、带正确Origin/标记的health200，foreignOrigin/missingMarker/missingOrigin均403。`DevRuntimeProbe.json`保存结果，不含token。health真实`worker_connected=false`，不假装自动制作已连接。本启动器不导入密钥、不注册route、不授权预算、不启worker；F1保存/事件/预览可使用此独立实例，但禁止借此重新授权另一个20元账本。

HTTP错误按公开ErrorEnvelope显示。PUT带If-Match，创建/制作/决定带稳定Idempotency-Key。SSE要用fetch流（可传标记；桌面时还需Bearer），不要使用无法带认证头的原生EventSource。媒体内容走受保护API，fetch为Blob/ObjectURL预览并在退出/更换时revoke；直接`<video src=受保护API>`不能添加上述标记/桌面Bearer。Range按公开端点调用，不将原始绝对路径交给页面。浏览器刷新没有secret存储；稳定同origin代理会话仍可请求health恢复。

生命周期（I4源码候选）：开发启动器消费 `tools/build/EngineProcess.mjs`，固定CLI/random loopback端口、stdin字节PIPE及30秒ready上限；私有 `--control-stdin` 默认仅此可信host显式启用。停止策略和实际探针范围见下文。I3已运行host22508仍持其旧源码/旧API，未因本次文件修改自动升级或重启；原强停退出3和AV0失败保留。

## 桌面IPC目标：尚未实现/编译验证

`engine_connection`仅供Tauri主窗口，参数为空，返回`{base_url,session_token,instance_id}`。token是当前本地API会话令牌，允许工作台内存持有，不是模型key。`engine_status`参数为空，返回`starting|ready|failed|stopped`及固定错误code，不返回任意stderr。目标shell启动固定签名/哈希纳管的sidecar、应用数据目录和随机端口；仅允许主窗口本地origin，退出关闭自身sidecar，崩溃恢复不能重发未知收费Operation。

IPC不接受URL/绝对路径/shell，模型凭证留后端OSvault。桌面媒体仍需受保护fetch/Blob；发布与生产收费另授权。此IPC目前只是待实现的私有host接口，F1可留adapter边界，不能展示“桌面已连接”或写死token假跑。Windows Rust/MSVC构建和真实生命周期未完成；HTTP200不等于exe通过。

## I3可信媒体资源与精确提交成包

开发host可接收非VITE_环境变量`VIDEO_CREATOR_RESOURCE_MANIFEST=<绝对可信manifest路径>`。启动前核资源根真实路径、十个bin/DLL大小及SHA-256、ffmpeg/ffprobe固定条目，再向CLI传成对参数。未配置资源维持媒体import503；前端不能选择二进制、manifest或实例根。I3实例和原Staging保留，启动器仍无worker/route/预算。

`node tools/build/BuildEngine.mjs --commit <40位提交> --output-dir <绝对构建目录> --resource-manifest <绝对可信manifest>`从Git提交逐文件提取固定源码/迁移/清单/uv锁/入口与spec，核资源hash后打包。BuildReceipt保存源码、资源、精确命令、实际退出、每个产物hash与体积；包含当前CrewAI框架代码/数据/递归metadata、两迁移和媒体资源。Entry在冻结包中固定迁移位置、关闭匿名遥测，serve前验证资源。当前仅Windows内部onedir API/框架候选；隔离ASR解释器和模型、Tauri UI及多OS安装包尚未成包，不能称完整创作App或发行包。

## I4 私有 API 生命周期候选（源进程实测；非桌面验收）

可信host只发送ASCII字节 `shutdown\n`（9bytes），不使用平台WriteLine、不接受页面/模型自由命令。标记必须是stderr整行固定 `{"event":"api_stopped","scope":"api"}` 加LF；helper按字节精确匹配唯一固定常量，并丢弃其他诊断，不将原文转发页面。stdout ready仍只接受event/base_url/instance_id三个字段。令牌仅在可信host内存和子进程环境中，探针日志不保存令牌。

后端正常收尾上限10秒，host等待15秒。normal须同时满足固定marker恰好一次、ChildProcess实际close code0且signal=null、原listener端口明确ECONNREFUSED、所有捕获的root/后代PID+creation-time身份消失且没有查询发现的未确认后代。只看到marker、退出事件或端口关闭均不足。Windows CIM读取字段仅PID/parent PID/creation time；每次taskkill前复核捕获身份，保护其他实例与已复用PID。

EOF仅结束私有reader，API保持运行，不自动cancel/pause/reconcile制作、释放预留或重发未知Operation。若host随后明确选择退出而管道已失联，则记录forced/error并只清理其已捕获API自有子树；保留实际child exit/signal及taskkill工具退出。无flag的API忽略该帧，等待超时后也只能记录forced，不能冒充normal。正常退出异常、startup失败或marker缺失保留error/nonzero；CIM查询失败或身份不明则不宣称清理完成。

DevRuntime SIGINT/SIGTERM或自有Vite退出会异步请求API正常停止，然后核身份清理自有Vite；引擎异常退出触发error。host没有强制调用process.exit掩盖子进程结果。异步过程不能在process exit事件或硬杀父进程后保证运行，父进程崩溃/未捕获后代竞态仍需要实际Windows JobObject或平台监督器验证。当前helper仅Windows开发过程，不能替代生产native隔离，也不保证后台Worker或费用清理。

本轮免费独立源探针入口：

```powershell
& 'C:/Program Files/nodejs/node.exe' 'G:/开发测试/Codex/VideoCreatorImplementation/Integration/Scripts/ProbeOwnedEngineNode.mjs'
```

探针在Integration/I4NodeProbe/中文 空格下使用独立API实例、随机端口及已验证FFmpeg资源，不启动Vite、不访问原DevInstance，不注册route/预算、不读key。覆盖正常关闭+真实MP4解码、同实例UTF8数据恢复、EOF继续服务、默认无control忽略帧、真实缺会话启动失败。结果和各实际进程退出见Evidence/I4NodeHostProbe.json；开发者自测不代替T/RV/AV独立报告。DevRuntime本轮未重新启动，UI联动与信号接缝尚待独立验证。

packaging入口/spec目前会原样传可信serve参数并递归采集已纳管Python模块；新增cli/lifecycle.py必须进入未来稳定提交及采集清单。旧68c1f069 API候选不包含此修复，不能用本轮源码结果回填旧包。新精确提交构建、冻结exe实跑、Tauri JobObject、完整App和macOS/Linux实机验证均待后续。
## I5检查失败与分路清理（候选修复）

所有权检查失败为粘性错误：曾spawn正PID但未捕获root身份，或CIM查询/target即时复核失败，即使实际close0、marker1、端口关闭，也不能verified/normal/cleanup_complete。只有没有创建PID的真实spawn失败且已收到close、无检查错误，才可证明未创建子进程。ready仅表示API可用，不签owned身份；host仍可发送私有帧让API正常收尾，结果保留error及真实exit/marker。身份复核失败只记固定identity_unverified/skip，不对未知目标执行taskkill。

DevRuntime经私有cleanupRuntimeChildren分别安排API与Vite清理，每次调用独立捕获同步throw/异步reject，两路都尝试并收集结果。API失败不跳过自有Vite；输出仅固定错误码与已知实际exit/signal或null，任一失败/清理未确认保持host非零。不以exitCode赋值证明资源已退出；管道、端口和owned身份仍由各自实际结果核验，未知仍需监督。未改变Worker/后台移交、EOF或收费语义，父崩溃/查询到taskkill非原子竞态及三OS缺口保留。

## I7完整开发host控制（ADR0007；Windows源候选）

开发入口默认workbench端口1420；可信CLI可指定--workbench-port canonical十进制整数1024—65535，固定127.0.0.1，API origin和Vite private非VITE_端口一致。前导零/小数/末尾LF/URL/缺失/重复拒绝；strictPort冲突失败，不能静默换端口、终止其他持有者或放宽同源/marker/token guard。

host --control-stdin默认off，重复flag拒绝。开启只接受可读node:net Socket、非TTY且fd0元数据非regular file/character device；检查失败拒绝，合法Windows匿名PIPE的isFIFO/isSocket可全false，不要求POSIX特征。可信父持stdin是前提，这不是同OS用户身份隔离。

固定9bytes ASCII shutdown LF；最多64bytes含LF，非法/CRLF/非ASCII/空格/JSON/部分不请求停止，超长丢至LF而不接收后缀。诊断只固定code。EOF只结束reader，不取消/暂停/对账API或制作、不声称后台移交。完整合法帧在API await-ready之前被锁存；早停不启动Vite、不发host ready并保非零。重复/并发调用复用stop Promise；startup/child异常为粘性失败。

host真正Vite local-listen提示后才发dev_runtime_ready；启动冲突/超时不能发伪ready。明确停止回收host stdin reader/句柄，并分别等待API及自有Vite结果。dev_runtime_stopped scope=host、api_scope=api；controlled仅表示API normal并且Vite既有owned_force真实清理完成（或明确未启动）且没有启动/child/early错误，host自然close0。API仍须其exact marker1/close0/port/owned身份；Vite实际force动作/exit1独立列明，不称Vite graceful或Worker/费用已正常结束。未确认/失败非零，不能用打印日志代真实host退出。

本轮owner完整入口已实跑独立端口真实HTML/同源代理health及拒绝、固定FFmpeg真实MP4入库、API normal与Vite owned_force和自然hostclose。正向旧5个配置PID在当次查询均无匹配，空集相等不能证明旧host身份保持；后续有限反向使用真实活跃B5兄弟API的health/creation保护。原反向probe曾因自身TCP占位fixture收尾挂住而被限定自树forced结束，原exit1/未终态receipt保留；仅修fixture后新名补未完成2例，不将整个原6批算通过。

末尾LF严格检查后新源合法最小完整入口另记hash/出口，不重复媒体。正式I7Handoff保存所有原/新来源、scope与未测项；owner探针不是T10/RV/AV独立验收。TTY和未知stdin类型尚待独立验证；Windows SIGTERM/hard parent termination保持forced，native JobObject/后台Worker/三OS/完整安装包仍未验证。旧68包与AV0exit3不覆盖。

## I9停止来源与预缓冲（ADR0008）

controlled且host自然0仅可来自已准可信stdin完整host_control帧，并满足完整ready/API normal/Vite实际owned清理与无粘性异常。SIGINT/SIGTERM在本有限开发host都为中断来源，先锁存异常再复用已有stop Promise；即使API/Vite清理完整，也保持host error/非零。cause仅起因，不能覆盖后来异常或作为可信来源证明，资源清理事实与host分类分开。

纯同步参数/PIPE准入后先建立pending状态与reader，再作异步资源准备和launchEngine。未有engine的完整帧只锁存，不能引用空资源；prepare前让预缓冲字节消费，准备中锁存则停止后续创建。未创建API/Vite的早停自然非零，标not_started及stopped_before_ready，不发API成功marker或hostready，也不称已启动资源清理完成。API已存在时的早停清理实际资源且跳Vite；EOF/非法仍不停止或取消制作。

该来源/reader顺序是新源，原I7/T10十八项结果不倒填。Windows真实OS signal handler可达性仍待证；emit/回调注入只证明分支，父硬kill不能冒充handler被执行。byte9/64、canonical origin/strictPort、token/manifest、两路隔离及有限PID归属/TOCTOU边界保持。

## I10 已完成清理后的异常退出码

异常停止请求在复用同一个 stop Promise 前同步锁存非零退出码，包含 cleanup 已 settled、host 尚未实际退出时到达的 SIGINT/SIGTERM 或其他异常回调。不得重发控制帧或重跑两路清理。此前已发 dev_runtime_stopped 是发送当时的清理与分类事实；更晚异常不能改写旧日志，最终 host 实际 close/exit/signal 另核，不能以旧 controlled 日志代替实际出口。

原 T11 settled 反例来自源码绑定 VM 与 synthetic 清理资源，Windows OS 信号可达性仍未测。本阶段窄修不改变 reader 前序、pending、9/64/EOF、同源/token/资源或自有 PID 清理边界，不继承旧样本通过。
