# ADR 0005：批准最小私有API停止接缝

状态：接口方向批准，生产实现和独立生命周期验收待B4及下游；2026-10-08。永久架构角色，不写实现/测试/标准/评审验收。费用0、key读取0，无发布或安装授权扩大。

## 依据与未通过事实

I4正式I4LifecycleInterfaceRequest.md/json要求的参数是`--control-stdin`；早期`--shutdown-stdin`仅历史建议，不成为另一兼容入口。源为cli/main.py SHA`0b0a6eaa8e3965d231ce88ac61a8532e5f20c57bf430395f570d6936a186bdcc`，API SHA`90ca70480c8b245ba08717d1d89092e626a62cf703a38a9805509c18276228b1`：CLI86参数、147 serve、164内联Server.run；API62只有recover/ready/yield。

I4仅修过程脚本过度声明并AST退出0，生产正常停止尚未修。AV0固定引擎候选68c1f0699086382856f61c703f88c8b03b5d2547两次CTRL_BREAK实际exit3；端口关闭/句柄回收/重启持久不替代正常退出和清理证明。原失败、68c1f069包与前端cea36dd分离保留。本ADR不是Gate0通过或框架冻结。

## 批准的私有控制v1

| 项 | 准入语义 |
| --- | --- |
| 启用 | 仅可信CLI的serve显式`--control-stdin`，默认关闭；不读取HTTP/UI/模型数据作控制，无公网关闭端点，不扩公开Pydantic/SDK |
| 通道 | 启动器创建并持有该子进程stdin PIPE；固定ASCII完整帧`shutdown\n`，最大64字节含LF；主窗口或外部模型不能提交自由命令 |
| 接收 | 仅完整精确帧请求此API正常停止；不trim/大小写转换，不接受CRLF、JSON、额外空格、路径/URL/模块/shell；重复请求不扩大范围 |
| 拒绝 | 未知/非ASCII/超长/未完成帧只固定诊断，不回显内容，不停API或改账本；超长帧丢弃到其换行，不把后缀拆成合法shutdown |
| EOF | 只表明控制通道失联，结束reader，不推断停止/暂停/取消Production或API；未完成帧不算命令。API仍按独立服务语义运行 |
| stdout | ready只保留event/base_url/instance_id三字段；不放token、任意输入、媒体路径或生命周期成功声明 |
| stderr | 成功marker固定JSON事件`{"event":"api_stopped","scope":"api"}`加LF；允许固定错误码诊断，不反射输入/异常原文。marker含义仅API资源清理完成 |

这是一条由本机可信启动器持有的控制通道，不宣称隔离拥有同一OS用户权限的恶意程序。无标志时不读stdin、不启控制reader，保留原独立serve/supervisor行为；原CTRL_BREAK非零不能被新协议抹掉。

## 真实完成与失败

B4持有明确Uvicorn Server及listener所有权；收到明确帧后通过后端确认的线程安全接缝请求该Server停止，在reader线程不直接运行异步清理。正常停止拒绝新连接、按明确有界策略处理当前HTTP/SSE，实际server loop/lifespan完成，listener和本API辅助资源关闭后才可发marker。当前EngineService/Database是每事务短连接，不要求虚构一个全局close/WAL动作；实际新增资源由owner明确登记和清理。

marker必须同时有：该Server确已ready并进入服务、实际正常停止完成、lifespan收尾成功、listener已关闭、私有reader已结束或由可证明不会阻塞进程退出的策略回收，以及没有异常/超时/强制终止被冒充。不能在finally无条件发，不能以should_exit=True、wait返回或stderr空白当清理完成。若后台reader仍阻塞，不能因为daemon模式就声称线程已清理；独立检查需记录真实存活范围。

后端和启动器明确有限正常等待窗口；超时标shutdown_timeout或forced_cleanup而非graceful。启动失败、清理异常、原信号非零及强制终止保留真实失败/非零退出，不强改exit0；没有完成证据就不发成功marker。正常路径让CLI自然返回；独立成功判定同时需要marker、实际exit0、端口关闭和所有该启动器持有的API辅助后代已结束，marker不能替代退出状态。

此API范围不承诺全部Run/Worker/媒体生成或供应商费用结束。停止请求不调用cancel/pause/reconcile、不释放未知预留、不重试供应商；已落盘事实保留，下次启动按既有recover与Step/Operation事实恢复。当前serve未启Worker，该范围不得外推未来收费制作已完成。

## UI关闭、后台继续与父进程异常

“关闭窗口”“停止本API”“取消制作”是不同操作。选择后台继续时，启动器须确认实际托盘/独立监督服务仍持有API/Worker；当前不能用窗口已关或EOF声称任务继续。选择退出前由host明确等待/后台/退出策略，只有需要停止API时才发送固定帧；私有停止本身不取消Run。

父进程崩溃的EOF不是用户指令。当前最小后端接口保留API独立运行；未来前台host若用Windows JobObject/macOS或Linux监督机制回收自身API，必须明确归属并记forced/parent_loss，不能发成功marker或批量杀其他实例/独立后台Worker。后台继续须先建立真实独立监督所有权或保留托盘host，再移出前台清理范围；未完成移交不展示继续承诺。后台服务和前台子树的所有权不得混合。

## 媒体接缝限定

现公开MediaProbe.duration_us允许None，AssetService只对video/audio要求正时长；静态PNG/JPEG已真实解码且MIME/尺寸正确时，duration=None符合现接口。无需新增公开Schema或由W4复制类型。视频/音频仍须真实流和正时长，静态图片的时间线展示时长来自Clip，不伪造源文件时长。

W4当前有限格式及协议/嵌套引用政策→T5独立复验，QuickTime/MP3不支持要明确拒绝，不外推永远不支持或用类型猜测放行。若确需跨AssetService/公开Schema改变，先由后端owner提出精确接缝；媒体角色不跨界。生命周期裁决不等待或代签这批媒体验证。

## 唯一owner与独立交接

1. B4后端：CLI flag/有界parser/Server所有权、API lifespan实际收尾状态和必要内部回调、listener/reader清理、自然退出/固定marker；不得修改media/workflows/桌面或上游库。公开Schema不因私有控制改变。可立即阅读本批准和准备实现；T5本轮冻结复验默认包含CLI/API，收到T5冻结批完成交接前不得写这些生产源，避免污染独立证据；之后固定B4新源再做下游验证。
2. 集成：可信host以字节管道发送固定LF帧、正常等待/超时/owned-tree策略、消费marker和真实exit、固定B4源后新精确提交重建候选；原包/原失败不覆盖。不得跨界改后端。
3. 测试：无flag默认、正常帧、EOF、未知/非ASCII/超长及后缀、部分帧/重复帧、早于ready/启动失败、清理异常/超时、SSE/实际请求排空、父子异常、端口/线程/后代、重启同实例版本/未知预留分别取免费证据。
4. 评审独立看固定源/原反例与新的失败分类；验收独立运行新候选及真实正常停止，架构批准不替代两者。

原三轮编排限制与ADR0003保持：此生命周期免费批准不重开收费Crew实验、不因余额重置验证、不决定唯一生产框架。MSVC/UAC、桌面IPC、干净Windows/macOS/Linux、模型/商业资源继续按实际缺口推进；本任务不部署、安装或读取密钥。
