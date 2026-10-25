# ADR0018：最小 Tauri2 原生宿主与真实会话

2026-10-08。批准 I20 按下述唯一宿主方案实施；当前 native/主入口 API 连接仍 not_run，不冻结原生兼容或签名发行。只读 I19/I21 正式资料、F3 交接和已停写的 DevRuntime/Vite 两源，未读/import B11 活跃生产、未启动产品。R1 三平台及 R1 后 R2 保持；原生壳不另造引擎、领域模型或创作账本。

## 1 事实与官方依据

I19NativeHostPlan SHAffe29c2480d6dab4e47c58b837ea8db6929da6a1c0470df3cf66a4116e320fb4；I21Handoff MDd1e4b6e746f4e43bb380c34f0d5cdf59ebfbc7bca5f599a3e4e3d023860d2262、BootstrapContract ee19a99d0cd105bf352e637f230ae26e0011c075965dea9ce6f17b2c00c5f981。实际 DevRuntime d2dfc873d38051014284521a258ff73276b71eb749d8050042ef2acada7f3adc、Vite3d28355a199e96a30d01608cc7d881fd4b6528b5b0c6613ec4fe35dd5c76733b 已核；I21 只 source/config 观察，不能外推真实 main/API-ready。desktop 现只有 package 清单/CLI2.12.1，没有 Rust/session。

官方 [capabilities](https://v2.tauri.app/security/capabilities/) 明确：自定义 invoke_handler commands 默认向应用全部窗口开放，需 AppManifest::commands 纳入 capability 控制；窗口标签本身也不等安全 URL。官方 [calling Rust](https://v2.tauri.app/develop/calling-rust/)支持从调用上下文取得 WebviewWindow。官方 [configuration](https://v2.tauri.app/reference/config/#usehttpsscheme)说明 Windows 默认本地协议为 http://<scheme>.localhost、useHttpsScheme 默认 false，不能把 Context7 中旧 2.0/平台概括当本次三 OS 实测。官方 [sidecar](https://v2.tauri.app/develop/sidecar/)规定 externalBin 构建输入带目标 triple 后缀；它支持封装 Python 引擎，但不自动证明我们已有完整引擎产物。

Firecrawl 4 次新官方 scrape 均 exit0，额度735→731；Context7 官方 /tauri-apps/tauri-docs v2 library+3次docs 均0，没有版本化 ID。crates.io/npm 只读元数据实得：tauri2.12.1、tauri-build2.7.1（均 MSRV1.90），serde1.0.229、serde_json1.0.151、getrandom0.4.3、windows-sys0.61.2、JS @tauri-apps/api2.12.1。这是清单候选和源溯证据，不是已安装、已解析锁或已编译。

## 2 唯一原生启动与会话

采用 Tauri2 Rust 宿主持有真实固定 Engine API child；Rust 负责进程/session/实例路径，Python 仍负责 API/账本/创作。固定 argv、shell=false；不从 Webview/模型收程序、模块、路径或任意参数，不开放 shell/fs/http 插件给页面。OS 安全随机生成32字节以上会话 Bearer，每次实际 API 启动轮换，只放 Rust 内存及受控 child 环境；禁止 VITE、URL、日志、导出、localStorage 或持久 session 文件。

启动前校验固定解释器或完整 sidecar/资源 manifest 身份，登记 child 的真实 OS handle/PID/创建身份、实例目录和受控管道。API 启动入口须来自后端正式交接的 CLI 契约；沿用 serve/private --control-stdin/loopback 动态端口与固定 allowed-origin 接缝，不通过阅读 WIP 猜 flag。若原 CLI origin grammar 仅支持 HTTP，后端须提供下面的受控 native origin 增量后才能启动对应平台。

解析 ready 仅接受原 event/base_url/instance_id 三字段、严格限长 JSON，不拿预设地址或 stdout 文字当 ready。base_url 必须是此次 child 绑定的 http://127.0.0.1:<实际端口>、无 userinfo/query/fragment/额外路径；确认 child 未退出、实际端口归属及受保护 health 的 instance_id 与 ready/本地持久实例一致。Bearer 由宿主生成而非 ready 供应。校验失败/超时清理本次 owned 资源，无 session 或 fake success；不接已有陌生监听器。

唯一初版 IPC 为无参数 `get_engine_session()`，返回 `{mode:'direct', baseUrl, instanceId, sessionToken}`。这是私有宿主 DTO，非第二公开领域模型。只在上述真实校验全部成功且此 child/session 仍有效时返回；Rust 会话状态至少区分 starting/ready/stopping/failed/closed，停止或异常立即禁止新取会话。对日志/前端错误只给固定安全 code，不含 token/本机资源路径。前端只在内存 getToken 闭包持有 descriptor，用唯一生成 SDK direct 传输；401、child 退出或身份不符清空连接，不退回 proxy/旧 token 或自制 origin。重连只能经新的受控宿主启动，不重新提交原未知 Operation。

## 3 主 Webview、IPC 与 HTTP 是两层

仅宿主创建的主 Webview label=`main` 获准。用固定 `WebviewUrl::App("index.html")`/已锁配置初始化，宿主依据 Tauri resolver 算定并记录唯一 expected_main_url；在页面可导航前核其完整 scheme/host/port/path，无 userinfo/query/fragment。Windows 固定 useHttpsScheme=false，预期本地 http://tauri.localhost；macOS/Linux 预期 Tauri 本地 app 协议，确切 resolved URL 与实际 Origin 由 I20 对各 OS 记录，未测不凭片段冻结。初始化仅接受固定 bundle entry 的解析结果，不从页面 location 或任意导航后的 url 生成 allowlist。

native dev 单独使用固定 loopback devUrl/端口与同一 `main` label，启动器确认其本项目 Vite 实例；其 exact URL 从可信开发配置给出。native dev 不启动第二套 DevRuntime API/proxy。release 不加载 devUrl、远程站点或磁盘任意 HTML。

build.rs 的 AppManifest::commands 明确列 get_engine_session；独立 allow-get-engine-session permission，capability 仅 main 的本地内容，明确列入 app.security.capabilities，remote 不开放、无通配 window/全插件权限。每次 IPC 再核 native 调用上下文的真实 label+当前完整 URL 与预先绑定值一致；renderer 参数或 window.origin 不参与授信。导航守卫在初次加载前安装，拒外部/其他路径/query/fragment；新窗口/window.open 一律 Deny，未知窗口无 capability。使用官方导航/new-window hook，集成按已锁 tauri2.12.1 编译签名核对，不把 Context7 旧“仅 plugin hook”描述当编译事实。

Rust IPC 授权不替代 API Bearer/CORS。Backend 唯一 CLI owner 提供受信启动 origin 的精确解析/校验：仅宿主固定本地 app origin 或已配置 native-dev loopback origin，无 *、null、任意路径/用户名或用户 payload 注册；HTTP Origin 与完整 Webview URL 分别核。API 在实际 session 下校验 Bearer、Host 和精确 Origin/预检；CORS 不因某个 tauri label、客户端 marker 或 allow-origin 字符串自动授 Owner。必须实测 Authorization/Content-Type/原生成请求所需 headers/methods、必要响应 header 暴露、SSE/二进制原字节；浏览器 fetch 不用任意 http 插件绕 CORS。如果平台实际发送 opaque/null Origin，保持 unavailable 并交 Backend/Architect 明确接缝，不加入 null 通配求绿。

生产 CSP 保留 Tauri 自身 IPC sources、限定本地资源及此次 loopback API 必要连接，禁止任意远程脚本/对象/frame、unsafe-eval 或关闭 CSP。动态端口的有限 connect-src 由宿主已知配置处理，CSP 本身不是授权凭证；native dev 的 HMR 只进开发策略。媒体仍经已授权接口读取，不给 app-data 整目录 asset 协议；现 F3 的128MiB预览/raw-upload缺口不是原生完整媒体交付已支持的证明。

## 4 实例数据与资源

安装目录只放可更新、已核身份的代码/资源。实例根由 Tauri app_data_dir 加稳定实例目录推导，首次创建持久实例标识；原项目/素材/账本/Operation/审计本地持有，普通 renderer/model 不选根路径。同实例取真实 OS 独占锁，锁身份与实际 process handle 关联，不靠 PID 文本或随意删 stale 文件。第二宿主不得另开同目录 API/Worker。开发使用明确隔离测试目录，不能默认借旧 Codex 私有实例。

本地/BYOK免产品注册，账号失效不关闭本地数据/本地能力；官方 Gateway 凭证/订阅属于后续独立控制面，不进 native bootstrap。升级/回退按当前 DB schema 与可信撤销/完整材料备份处理，不在窗口退出时迁移/删除用户数据。

开发模式由集成可信启动配置固定本项目独立 Python3.13 环境/源码入口/锁身份，界面明确开发。不得从页面或任意 PATH 搜 python。release 则 externalBin 指完整 Engine sidecar 的目标 triple 构建输入；resources manifest 列实际 installed_relative_path/大小/SHA、Python与全部引擎依赖、模型/FFmpeg资源和许可。用 Tauri 资源/安装根 resolver 解析并检查 realpath 边界，安装后文件名由真实打包结果核定，不猜 triple 是否保留。I16仅 ASR runtime、I3旧候选或缺件目录不能冒完整0.3引擎。缺完整合法 sidecar 时允许明确开发验证，release 构建/发行保持 blocked。

## 5 正常关闭、后台继续与异常父退出

CloseRequested 先 prevent_close；API停机、取消制作、关闭窗口三者分开。无制作或选择完全退出：使 session 不可再取，向该 API 私有 stdin 写固定 shutdown LF，有限等待真实 api_stopped(scope=api)+exit0+端口关闭+owned辅助后代退出；完整证据才 normal，timeout/信号/forced 独立记，不伪0。启动期间关闭不得发 fake ready；父硬停的 EOF 不作为 API/Run cancel。

存在制作时提供已实现的受控选择。后台继续采用同一宿主仍存活的托盘模式：只有托盘可恢复窗口、API/实际独立 Worker 与监督所有权均已确认才隐藏主窗并 prevent_exit；不能仅 hide 后丢入口。当前 worker=false/托盘未实测时不得展示“仍在制作”的成功承诺，可保留主窗并提示等待能力。完全退出先协调停止该 owned Worker 接新步骤、留原持久事实/未知受理，再停 API；该动作不调用 cancel/pause 或重交费用，下一启动按原 recover/reconcile。Worker 停止/租约接口不足交 Backend/Media owner，不用 kill 成功冒持续可靠执行。

Windows 前台 owned API/辅助后代用独立 JobObject、KILL_ON_JOB_CLOSE、非继承 owner handle；创建 child 时先受控 suspended、加入 Job 后再运行，避免先 spawn 后 attach 竞态。不得将其他实例/已独立后台监督 Worker 加入前台 Job，不允许模型/process随意 breakaway。正常退出先上述私有协议，最后关闭已空 Job；崩溃/hard kill 由 OS Job 回收，分类 parent_loss/forced，不冒正常清理。真实句柄、退出与端口必须实证，禁止仅 taskkill /T 或 PID marker 证明归属。

POSIX 不以 Windows Job 或 process group 独存假装有父崩溃回收。采用同一 native 可执行文件的固定私有 owned-supervisor 模式：受控父生命管道、拥有独立 process group 的 guardian、固定 API/Worker入口；父异常时 guardian 对自己持有且仍可证身份的组作有界 TERM/KILL并记录 parent_loss，正常退出优先私有 API/Worker协议。该 guardian 管道 EOF 是宿主生命信号，不能混同 API --control-stdin 的 EOF 语义；不建通用调度服务/任意命令入口。其 bootstrap/child归属证据在私有管道传回 Rust，不改公开 ready 三字段。跨平台实现/真实 kill 尚未做，缺对应机器明确 pending；Windows I20 不需等 POSIX 实测才能做本平台有限实现。

独立后台服务移交不是初版默认；未来要移交，必须先确认新监督 owner/Worker及持久状态，再从前台清理范围移出。不以 GUI关闭、API scope marker、worker PID 或文件存在证明后台制作可靠，账本/租约/危险副作用守卫沿原 Gate0。

## 6 I20 清单、接缝与验证范围

集成唯一可写 native生产 `apps/desktop/src-tauri/{Cargo.toml,Cargo.lock,build.rs,tauri.conf.json,permissions/,capabilities/,src/main.rs,src/session.rs,src/platform.rs,src/supervisor.rs}`、desktop package及相关根依赖/锁/构建配置、packaging/tools/build 自己的明确清单。不写 Frontend/B11/测试/标准；新增所需图标/资源在desktop归属路径，不能把下载包/日志混入仓库。所有依赖/锁由集成统一。

清单候选固定本次官方稳定 tauri2.12.1/tauri-build2.7.1、serde/json/getrandom及目标 Windows-only windows-sys0.61.2；POSIX OS binding 仅在对应实现确有需要时核其官方维护线/锁。@tauri-apps/api2.12.1 若需新增用于官方 invoke，由集成仅配置依赖，前端才消费。不是按 JS CLI 版本机械填 Rust crate；禁止自动 latest/floating major、无关 shell/fs/http 插件。核现有 Rust/MSVC/Windows SDK/WebView2实际版本与官方 MSRV/peer/features，真实同锁解析构建后才固化兼容；若冲突留实际 error并裁定小范围，不先大升级或换框架。macOS signing/notarization和 Linux WebKit/runtime 需各平台实际核，无机器不报通过。

Backend在正式源释放后交唯一 CLI argv/受信 native Origin/health身份/Worker停止契约；当前 B11 WIP不读取/不启动，不默改跨owner源。I20可先编译壳/能力守卫和缺会话负向，真实 API-ready/health要等正式匹配后端与SDK。Frontend另接真实无参 invoke/direct descriptor，bootstrapManagedWorkbench仍只用于I21开发managed proxy，不凭 __TAURI__ 标志或任意 origin制造会话；双来源冲突直接 unavailable。Integration不跨界改 main。

Test另备实际标准与正负向：真 Webview invoke+session+health；未ready/旧token/错误URL或窗口/外部导航/popup/CORS拒绝；重启新session且旧实例数据恢复；正常私有停止/启动中关闭/父hardkill归属；实际后台 Worker继续与显式退出后的账本恢复；full8原字节/音视频/字幕/RAG及引用导入仍独立门。owner自查不代 Test/Review/Acceptance。安装、安装依赖、真实发布、收费与模型实验不由本ADR扩大授权；原DeepSeek/Kimi共享20元及Crew限次保持。

正式文本/来源hash与全部研究命令终态见 NativeHost-A14/A14Handoff.json。无产品/测试运行、凭证或付费模型调用；本轮的4 research credits与CNY实验账本分列。
