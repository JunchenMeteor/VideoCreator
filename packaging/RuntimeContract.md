# F2 本机运行时交接（候选接口，2026-10-08）

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

生命周期：固定CLI随机loopback端口，30秒ready超时；仅接收`event/base_url/instance_id`且校验URL。引擎退出会终止本host的Vite，Vite退出会停止本host引擎；SIGINT/SIGTERM清理两个子进程；Windows使用本host持有的ChildProcess PID及taskkill /T关闭venv redirector/Vite的自身子树。Windows强制结束父进程树仍需按本host身份清理，开发host不是Windows生产JobObject替代。杀API后账本恢复由后端CLI下一次启动执行。stderr不转发任意引擎数据；错误只输出固定code。尚未做独立生命周期测试，不以代码审阅算通过。

## 桌面IPC目标：尚未实现/编译验证

`engine_connection`仅供Tauri主窗口，参数为空，返回`{base_url,session_token,instance_id}`。token是当前本地API会话令牌，允许工作台内存持有，不是模型key。`engine_status`参数为空，返回`starting|ready|failed|stopped`及固定错误code，不返回任意stderr。目标shell启动固定签名/哈希纳管的sidecar、应用数据目录和随机端口；仅允许主窗口本地origin，退出关闭自身sidecar，崩溃恢复不能重发未知收费Operation。

IPC不接受URL/绝对路径/shell，模型凭证留后端OSvault。桌面媒体仍需受保护fetch/Blob；发布与生产收费另授权。此IPC目前只是待实现的私有host接口，F1可留adapter边界，不能展示“桌面已连接”或写死token假跑。Windows Rust/MSVC构建和真实生命周期未完成；HTTP200不等于exe通过。

## I3可信媒体资源与精确提交成包

开发host可接收非VITE_环境变量`VIDEO_CREATOR_RESOURCE_MANIFEST=<绝对可信manifest路径>`。启动前核资源根真实路径、十个bin/DLL大小及SHA-256、ffmpeg/ffprobe固定条目，再向CLI传成对参数。未配置资源维持媒体import503；前端不能选择二进制、manifest或实例根。I3实例和原Staging保留，启动器仍无worker/route/预算。

`node tools/build/BuildEngine.mjs --commit <40位提交> --output-dir <绝对构建目录> --resource-manifest <绝对可信manifest>`从Git提交逐文件提取固定源码/迁移/清单/uv锁/入口与spec，核资源hash后打包。BuildReceipt保存源码、资源、精确命令、实际退出、每个产物hash与体积；包含当前CrewAI框架代码/数据/递归metadata、两迁移和媒体资源。Entry在冻结包中固定迁移位置、关闭匿名遥测，serve前验证资源。当前仅Windows内部onedir API/框架候选；隔离ASR解释器和模型、Tauri UI及多OS安装包尚未成包，不能称完整创作App或发行包。
