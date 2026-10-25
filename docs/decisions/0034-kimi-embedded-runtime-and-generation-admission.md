# ADR0034：Kimi内嵌运行时、本人WebView与官方生成接入

2026-10-10，A31。**准入无收费SDK技术spike及独立WebView验证设计，不批准实际生成/账号操作/服务商业资格。** W19正式Findings/Snapshot/ToolReceipts及原W2摘要已核；13项预期SHA匹配，完整来源见Architecture/KimiEmbedding-A31/InputPins.json。无新公开研究、模型/账号调用；不读生产热源。五步主工作台、实例持有工程/作品、免本产品注册BYOK、三OS/API/MCP及R1独验后连续R2保持。

## 三条路线分别成立

| 路线 | 本次明确决定与仍缺证据 |
| --- | --- |
| 本人Kimi Code或自有API：嵌入Agent SDK | [官方SDK](https://github.com/MoonshotAI/kimi-agent-sdk)可编程使用Code CLI并扩展工具，允许技术spike；**不等于官网会员创意插件在SDK内可用**。精确发布/CLI依赖/SDK及CLI分发许可、该账号服务scope、生成tool和真实费用尚未准入 |
| 本人官网账号：独立顶层WebView | 保留App内部登录/展示/取原产物的候选，登录与必要用户动作显式。匿名HEAD200/未见CSP-XFO不代嵌入许可/实际兼容；不是iframe，也不是无人值守/服务器生成承诺 |
| 本产品official订阅：合作API/MCP/SDK | 最符合授权后只看结果、后台自动生产；商业Gateway持正式服务凭证和权益，实例持作品。需外部生成能力/持久task/下载/费用/临时数据TTL及允许商用服务的具体协议；私人会员账号不能共享给订阅用户 |

W19已读[官网条款](https://www.kimi.com/user/agreement/modelUse?version=v2)§2.2、4.6(e/g/h)、5.2及specific优先规则：一般条款限制模拟人工的自动使用/未授权转授，不能一刀说所有SDK/WebView禁止，也不能隐藏自动点击冒已许可。SDK README的Apache声明不代完整LICENSE/NOTICE及CLI/transitive许可，更不代在线插件服务权。 [API产品说明](https://www.kimi.com/help/kimi-api/api-overview)区分会员、Code、开放平台：不能由同品牌/key推套餐覆盖； [官网生成能力](https://www.kimi.com/help/others/capability)和接外部MCP不证明原内置插件有外部endpoint。当前Kimi生成Provider仍not_ready，但不能用长期not_ready代完整产品交付。

## 首个可实施spike：Python SDK，单步受控执行

优先[Python SDK的Session](https://github.com/MoonshotAI/kimi-agent-sdk/blob/main/guides/python/quickstart.md)路线，复用项目Python方向；先隔离为**可选provider运行时**，不往主Engine/Crew依赖环境强装、不新增生产Node服务。SDK+匹配Code CLI/依赖在同版本包纳管，原native guardian按私有PreparedLaunch固定exe/cwd/资源启动。Integration先核SDK/CLI精确tag/commit、Python3.13兼容/三个目标架构、完整许可与可打包方式；当前main文档没有数字版本冻结依据，失败不默换主Python/框架。

SDK只是本系统最终单Crew或LangGraph编排中的**有界制作步骤执行器**，无另建全局导演/无限多agent。外层先锁Run/Step/Operation身份，固定输入、工具集合、最大turn/tool次数、token/耗时/输出大小与现预算；不可凭SDK sessionId代供应商job或本机fence。禁止直接照搬quickstart `yolo=True`，禁止`approve_for_session`泛授权；不继承用户全局默认agent、skills/MCP、任意PATH/env或配置发现。自定义agent采用明确白名单；不extend默认Shell/Task/FileWrite/任意HTTP/Search工具。若精确SDK不能关闭/截断这些能力，就不能挂生产Provider。

可信工具只接本系统已准入的生成、原task查询及结果暂存端口，固定Schema/厂商路由，无任意shell/URL/文件路径；MCP仅可作为已准厂商或本机受控工具transport。**SDK ApprovalRequest不是完整安全边界**：无审批事件的工具/网络同样须受OS隔离、白名单与本系统guard。ApprovalRequest/完整ToolCall参数由Backend原Owner政策/权限/外发范围/当前fence检查；已可信预授权可自动批准单次精确动作，interactive才呈指导/审核，不伪造真人ReviewDecision。模型字符串、工具自报approved不能授信。拒绝/过期/撤销和缺资源照原语义；SDK等待须有限取消/阻塞状态，不能在writer内等人或RPC。

**每次付费prompt受理前也预留预算**，不是只在生成tool时计费。工具副作用继续由Backend写原Operation+allocation再提交；一次SDK/tool ID对应已有Operation，同ID参数变化拒绝，stream片段/重放不重复执行。usage缺失为unknown；CLI退出/SDK close不等厂商取消或退款。真实生成之前必须另满足适用服务权、已准工具、真实安装/current检查及剩余额度；本ADR不授新CNY或重开Crew实验。

私有adapter仅需四种操作语义：启动/恢复同bounded会话、解析完整审批/工具事件、由原guard执行指定typed动作、停止本地会话并保留未核实副作用；Backend唯一签精确字段/端口，Media实现供应商消费，Integration只封装runtime。原engine公开DTO不为probe另写一套。恢复用原session日志+本机Operation和厂商task核实： [Node SDK](https://github.com/MoonshotAI/kimi-agent-sdk/blob/main/node/agent_sdk/README.md)可读取会话事件，Python可resume，不等远端exactly-once；需要SDK写入/恢复格式由固定源验证。断线先查原task，不能因resume再prompt或工具日志出现就重交。

## 产物、WebView与headless边界

生成tool成功不等作品交付。Media须拿真实task/result引用→受保护下载暂存→bytes/SHA/MIME/完整decode→Backend本机Asset/来源/许可登记→按现多模态Bundle原子成包（视频、旁白/混音、源码、ASR/字幕/语义关联），缺项不成功。SDK文本/URL/工具“文件已生成”及网页服务端ffprobe只作观察；缓存工具trace/思考不直接进RAG，真实文本/媒体坐标按原规范。秘密/原cookie/token不入session导出或Bundle，投放另授权。

WebView只能本人账号独立远端origin，独立OS保护的站点存储；无本机Engine/admin Bearer、Tauri命令/文件/任意导航能力。对OAuth/外链/下载所需新窗口逐域许可；无法支持时返回明确兼容缺口，不偷换UA/注cookie/私有网关。用户登录不会自动授权后台点击。下载在可信native transport里绑定当前账号/原task/允许origin与实际用户或专用授权事件，重定向/大小/类型/过期/重复及本机路径均受guard；renderer不能给任意URL/SHA作真实ticket。一次配置/登录可放在设置连接页；工作台仍五步。不把必须每次手动点生成/下载的WebView称“只看最终结果”的自动成品。

原W2图片chat `1a11736a-8b82-8f30-8000-09b7dbe33199`、视频chat `1a117446-e692-8628-8000-09b7dbd00f21`网页报告完成，但各一次下载未拿到文件；**文件交接未验证，不改写生成失败/成功成包**。后续只读原chat/卡片/下载记录的方案独立分派，原chat/tool身份保持；无重新提交、搜索内部agent-gw或盲再点击。若文件已在授权目的地，先实际校验；否则根据当前原卡片及适用许可/用户动作再定取回步骤，本卡不执行。

Linux headless走同可选SDK/CLI固定运行时及可信配置/授权来源，生产期间无浏览器依赖；首次身份建立如需厂商交互采用厂商允许的一次授权流程并安全保管，具体方式未证不猜device/OAuth scope。WebView是桌面候选，不能作为headless方案。official订阅最终必须合作生成接口由Gateway直调用、原task查询/下载/对账，前台/API/MCP沿同身份预算；不要求用户安装/打开Kimi App或搬结果。Kimi缺件期间其他**真实已准入**Provider和完整本地制作可并行推进；占位片/理解模型/模拟不替图像、视频、声音生成要求。

## 下一分派与验证

**Integration第一卡：无收费源码兼容spike。** 自身过程目录固定SDK/CLI源、元数据与完整license闭包，确定Python隔离runtime/跨OS包清单，验证白名单能移除默认危险工具、有限事件/审批/退出/日志恢复的实际签名；不得登录、送prompt或运行有收费能力。若用自有stub/本地wire fixture，只证明协议/隔离，不算Kimi运行或真实生成。先交精确稳定合同给Backend/Media；打包与真实OS启动另获实施卡后分开取证。

**Media下一卡：生成能力消费合同/原W2取回计划。** 列具体生成tool/许可与账号scope来源，submit/query/download/usage/cancel/TTL每项可证与缺件；未有官方插件外部合同就不猜工具名或endpoint。Backend接Approval/Operation/费用与unknown核实，Media只写provider驱动；Frontend按生成/待授权/能力未配/结果状态呈现。本人WebView实际兼容/原task只读取回与官方合作条件是独立任务，不混成SDK绿。

Test随后独立验证自有危险工具拒绝、预授权撤销/超限/同ID重放、流中断/未知受理、会话恢复无重复副作用、真实原文件下载解码与成包；Windows/macOS桌面和Linux无头逐项真实跑，不skip冒三OS通过。Review检查具体服务准入与SDK隔离；验收另实看实听，SDK compile/页面按钮均不算作品。源码spike可立即推进，缺厂商商业端口/许可记准确外部资源，不占槽无限检索或降低总目标。
