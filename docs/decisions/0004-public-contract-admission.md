# ADR 0004：公开契约与媒体接缝准入

状态：批准接口方向、实现待交；2026-10-08。不写Python/SDK/测试，不认定候选Schema0.1.0已冻结。

## B3→集成→前端

1. B3将ErrorEnvelope从后端唯一Pydantic源明确关联OpenAPI错误响应：code/message/retryability/request_id；实际领域错误及请求校验错误使用同一结构，状态码/幂等冲突/重试或核实语义可追踪。当前runtime handler有该类型，生成OpenAPI components实际缺它；不能让前端手写第二份接口模型。
2. B3稳定顶层video_creator/__init__.py及实际启动/CLI入口，给源hash、运行入口和checkpoint完整清单；文件仅在working tree存在不能算可重建包。集成从该固定源重新生成Schema/SDK与manifest，消费者类型及错误处理同步，T角色核验源→生成→运行一致性。
3. API的accepted/queued是命令受理，不是已生成；worker_connected=false必须如实显示。F1开发代理的同origin/会话边界只代表开发连接，不代表生产桌面IPC或后台Worker通过。

## B3→Agent/媒体→I3

staging ready/201只表示受控暂存，未经过AssetService的真实媒体decoder不能登记成功。F1当前import503 media_validator_missing是能力缺口，不得改成成功、伪decoded或前端隐藏错误。

B3定义/注入MediaValidator受控端口，输入限实例暂存引用/固定MIME，输出后端MediaProbe中的真实规格、解码证据和工具版本；校验hash/size/MIME/范围后才提交Asset。Agent/媒体提供实际解码实现，I3提供固定可验证FFmpeg/ffprobe/字体或已有真实合法解码工具的资源与入口，CLI/host在能力就绪时接入；没有资源则维持明确503和可继续暂存。不得接受用户/模型任意shell、外部绝对路径或以文件扩展名视为已解码。

## I3可并行准备

原工具来源三轮失败和MSVC两次安装失败保留。可做失败日志/签名/官方来源调查、不同且可验证分发来源的hash/许可验证、RuntimeContract/IPC生命周期设计、0001+0002随包完整性与内部候选构建清单。不能重复同失败安装/下载而称新任务，也不能以SDK26100/Rust1.99导入替代cl/link/MSBuild或exe成功。

MSVC未装成，最终用户路径保持Microsoft/VsBuildTools；mac/Linux实机、签名/公证、专用生成API与商业资质缺口继续保留。桌面IPC实现/编译与真实进程生命周期归集成，独立测试和验收另交，代理HTTP200不算三OS安装。
