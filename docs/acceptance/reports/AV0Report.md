# AV0 Gate0 独立验收阶段报告

日期：2026-10-08。永久独立角色 acceptance。结论：**Gate0 未通过，技术栈不能整体冻结；R1、R2 均未验收完成。** 本报告只签实际核验范围，不替代评审或统筹决定。完整目标仍为 Gate0 → R1 完整独立验收 → 连续 R2。

## 输入、版本与边界

独立读取工作区和仓库规则、任务卡、状态、原始 01—11 规格、GATE0/BASELINE/COMMANDS、A1 ADR0002、T3Handoff、RV0 和固定 I3/F2 交接。11 规格及四份范围标准 SHA256 与批准记录一致；`STANDARDS-FREEZE.json`只批准范围和证据规则，技术未批准。历史 BASELINE 中 pending 状态保留，不静默改标准。

实际引擎构建提交 `68c1f0699086382856f61c703f88c8b03b5d2547`；I3 上游稳定源码 `bb597bf36054cc49aff3efa276399493fbd94622`。F2 前端另为 `cea36dd71a1293b197264950b993e2f291eb5e7d`，不宣称 API 包包含前端或桌面壳。BuildReceipt SHA `c1f4867cb5eac58c09e67f0e5e4f3eda02842cad12e7972f2bdd1119e9519b65`，EXE SHA `afa520ada8efdd4c3b30d0d21900f57c0f03f8fd0906591dc343a981467a4f60`。

独立复制全部 3432 文件、823233680 字节至 Acceptance/IndependentWindows/中文 空格/VideoCreatorEngine，每项字节及 SHA 与 BuildReceipt 相符，无额外文件。复制前目标不存在。包内媒体资源 manifest 身份匹配。应用子进程清 PYTHONPATH/PYTHONHOME/VIRTUAL_ENV，PATH 仅 System32，cwd 在验收目录；应用运行自带 Python/媒体/迁移资源。标准库采证脚本由项目解释器运行，**因此这是当前 Windows 机器的隔离目录运行，不能称干净无运行时 Windows 安装实测。** 无密钥读取、供应商请求、预算授权或费用；随机会话只存私有子进程环境，不进入报告。

## 实际命令和结果

```powershell
& 'G:/开发测试/Projects/VideoCreator/.venv/Scripts/python.exe' -X utf8 'G:/开发测试/Codex/VideoCreatorImplementation/Acceptance/ProbeAV0.py'
& 'G:/开发测试/Projects/VideoCreator/.venv/Scripts/python.exe' -X utf8 'G:/开发测试/Codex/VideoCreatorImplementation/Acceptance/MediaAV0.py'
```

第一条实际退出 **1**，53 断言中 51 通过、2 失败；包含规格/标准/产物身份检查，不能把 51 都计成业务或真实模型测试。退出码未吞。独立实例 `instance-662b2351e753496c94c2a6f40b314184`：真实 ready、401、foreign Origin403、health200/worker=false、中文项目201、相同幂等键同项目、不同输入409、schema v2、两 MP4 与 WAV 实际 bundled 解码导入、鉴权 content/Range、坏媒体422、不同进程重启的同实例/项目/三资产 hash 完整通过。

两次向自己的 CREATE_NEW_PROCESS_GROUP 子进程发送 CTRL_BREAK_EVENT，wait 实际返回 **3、3**，端口关闭、进程 handle 已回收；未使用强制终止兜底。`FirstStop_clean_exit_zero`、`SecondStop_clean_exit_zero`失败。当前无应用 teardown 完成标记；stderr 为空也不能证明优雅清理完成。不把“端口已关/可重启”替代零退出及完整生命周期。独立 probe 完成后 CIM 未见候选 EXE 进程。

第二条首次采证脚本退出1：FFmpeg drawtext 绝对字体路径解析失败，后续 decode/frame 因无有效产物失败。原 `AV0MediaReceipt.json`、RenderedSignals 全部日志保留。只修自身采证方法，采用 verified 本地 Font.otf/Title.txt 和 explicit cwd，新目录 RenderedSignalsCorrected，不改生产/依赖/标准。修正后实际退出 **0**，六个 render/decode/frame 进程均退出0；两画幅各真实10秒 H264/AAC 测试信号。直接使用复制候选的媒体二进制和字体，没有借源工作区工具 PATH。

实际看过四张抽帧：I3 原信号竖屏2秒/横屏6秒，以及本角色新信号两画幅5秒。彩条、运动图案和中文字“视频创作系统 · 中文字体验证”“独立验收 中文测试”清晰无缺字。此为抽帧视觉核验，**没有连续观看完整片段，更不是三 AI 生成镜头或创作质量通过**。WAV 解码时长17773379us，保留与原 W1 17773378us 差1us，不倒改历史时码。

真实 UI 只读浏览器启动尝试失败：cua_repl 内核在初始化时返回 `windows sandbox failed: helper_unknown_error: apply deny-read ACLs`。没有可用页面状态，不宣称本角色完成 UI/播放复测。F2 浏览器播放证据属于开发自查，本报告只审阅其边界，不代签。音频输入明确当前工具不支持，未听过；解码、ASR、波形和播放器 readyState 不替实际听审。

## 逐 Gate 判定

| Gate | 等级与状态 | 已有证据及未达到门槛 |
| --- | --- | --- |
| G0-ENV | real/inspection，部分验证，整体 not_run | 固定候选3432文件/资源、冻结 schema export 实跑；全依赖与最低OS/三平台锁一致未独立安装验证，不包含ASR独立环境 |
| G0-ORCH | inspection/simulated，failed/未证 | T3 35机制绿是受控假transport；历史 Crew三轮真实委派0，修后模型自主仍未证；LG交互真实但无公平完整成功对照，最终唯一生产框架未冻结 |
| G0-REVIEW | inspection，部分证据，not_run | LG 同Production第三镜头指导/跨进程恢复交接存在；本角色未新增收费复跑，无人真实流程仍失败，三审核点完整制作未证 |
| G0-LEDGER | real/inspection/simulated，部分验证 | 独立重复项目/输入冲突和不同进程实例/三资产持久通过；T2真实kill与T3机制记录只审阅，不冒充本角色完成全收费断线/副作用窗口验收 |
| G0-BOUNDARY | real/inspection/simulated，部分验证 | 独立401/Origin403/content保护/坏媒体422与无收费实例；完整路由/外发/预算/成员权限守卫未本轮全复跑，供应商商业准入无证 |
| G0-MEDIA | real，部分验证，blocked | 候选资源两画幅10秒实际编码/完整解码/中文抽帧，三媒体hash读取及重启保存通过；听审能力缺、旁白/混音/MP4关系完整验收缺，信号不计真实作品 |
| G0-ALIGN | inspection，blocked/not_run | 源稿/实际ASR分离和整数时码交接可检查；无人工边界标注、forced alignment/非零偏移成片与P95≤200ms实证，包未含ASR |
| G0-DESKTOP | real局部/failed/not_run | API EXE独立路径运行及资源可用；两次CTRL_BREAK exit3；Tauri、IPC、JobObject、对话框、干净Windows/macOS安装与签名/公证未验 |
| G0-LINUX | blocked | 缺原生Linux机器，没有最低glibc/发行版/安装/同10秒任务实测 |
| G0-CONTRACT | real/inspection，部分验证 | frozen export退出0，ErrorEnvelope公开，OpenAPI与生成文件结构相等；八组完整契约、MCP/Bundle/非法计划与版本校验未全验 |
| G0-UI | blocked/not_run | 实际浏览器启动工具失败，F2八源/播放仅开发交接；独立五步1440/1024/720、键盘、50镜头、恢复和已有素材合成体验未验 |

Gate0 全部11项均未整体达到门槛；没有必需项跳过后算通过，没有为了全绿降低标准。RV0批准范围与证据规则；截至本报告采证时 RV1 正在进行、固定最终报告尚未交，本报告不预判评审关闭。

## 归属和后续

AV0-LIFECYCLE-01：集成/发布归属，独立复现候选停止 exit3；明确生产退出协议与清理证据，必要时向后端接口 owner 交接。不能只在探针中把任意返回码改成成功。

声音独立听审、mac/Linux实机、专用合法生成接口/预算、商户与支付沙箱、发布授权、签名及分发许可仍缺。Kimi网页任务“完成”无可核验文件、私人会员接口/商用未证，不计官方模型服务。官方订阅必须产品内部合法API/MCP生产/查询/下载/成本对账；本地免注册独立继续可用。

R1 至少真实口播和≥3生成镜头短动画、横竖屏、HTTP/MCP一次触发到完整多模态/RAG包、导出与引用、三平台安装均未通过。R2 CM01—08、FR05/10增强、FR17、真实支付/权益/发布回执全部仍须后续独立验收；FR18排除。不能用本报告局部CLI/API通过替代这些完成条件。

机器可读报告 `AV0Report.json` 绑定实际 receipts/样本/命令/产物 SHA；过程保存在 Acceptance 下。只写验收白名单，没有修改实现、测试、标准、依赖或其他角色实例。
