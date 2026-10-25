# WorkbenchPreviewBrowserSmoke

ACTIVE，唯一原 `test_local_resource` 续作独立测试开发；仅写测试源码/入口与自身 `Test/WorkbenchPreviewBrowserSmoke/` 过程，不改Frontend/Backend/Media/Integration生产源码、预览服务进程、其他测试任务或评审/验收报告。目标是回答用户当前 `http://127.0.0.1:18471/` “无法加载”是否为页面实际渲染错误，而不把静态预览当成完整产品。

输入：当前预览仅运行在本机 18471，Root之前验证端口 PID11500、`/`/`/workbench.html`/JS/CSS HTTP200，Codex浏览器控制工具报 Transport closed，因此需独立真实浏览器渲染。先复核当前唯一监听进程创建身份与HTTP，不擅自重启/替换；若监听已消失，记录而不将旧PID或超时当活。使用工作区共享 `G:/开发测试/.sharedDependencies/playwright-browsers`，先检查仓库已有Playwright入口/版本；仅实际可用时从当前浏览器跑根页和 `/workbench.html`，记录DOM可见文本、控制台/pageerror、失败请求、截图与原命令/exit，必要时短等待首屏。勿将HTTP200当渲染通过。

有真实错误时给路径/复现/最小修复归属Frontend或Integration；无错误时给可点击的直达链接与截图/当前页面版本，说明Codex内置标签页Transport closed尚未独立消除。当前构建无后端/模型/生成，不测试收费、凭证、部署或R1。所有日志/截图/可清理脚本置本任务目录，实际工具自然终态与读写释放交Root。
