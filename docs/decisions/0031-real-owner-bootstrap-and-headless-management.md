# ADR0031：真实本机 Owner 与无头管理入口

2026-10-09。状态：**最小入口设计批准，当前没有安装后可用的 Owner 正向入口**。接续 ADR0024/0028；本轮只读设计，不运行服务/凭证/安装。完整 R1 独立验收后连续 R2；本地/BYOK 无需云注册或供应商 App。

## 当前结论（代码依据）

| 状态 | 准确接缝 |
| --- | --- |
| 已实现；本轮未运行 Owner 正向 | `application/production_management.py:23–96` 有 distinct ManagementPrincipal、registry.authenticate/assert_current/revoke_binding；`production_authorization.py:116–175,177–250` 已有 install/select/revoke/get 与真实动作回执、幂等和外置 floor；`production_reauthorization.py:131` 有同原请求重新授权 |
| 已实测普通身份拒绝 | I45 SDK18检查通过，其中普通安装 bearer 管理403；原总运行 exit1/端口观察缺口保留。`api/app.py:135–142` 明确拒普通 token。这是正确权限边界，不能改为通过 |
| 缺正常启动接通 | `cli/main.py:98–140,267–295` 无 Owner 命令，serve 未装 management/copy 服务。API仅 `app.py:415–443` 六个 local-copy 管理口，无 production policy 管理口。代码没有名为 AdministrationPort 的实际类，沿现有服务补 adapter，不假称已有入口 |
| 缺桌面/无头产品入口 | native `route_contract.rs:65` 只接受两种执行模式；`transport.rs:21,112` 仅一个普通 bearer。工作台无 policy 管理界面；DevRuntime仅普通 session。`RegisteredMediaRuntime:87–136` 未装管理/ProductionAdmissions；`production_admissions.py:52–55` 的实际安装 authority 仍仅协议，配置 SHA 不能代资源观察或 Owner 动作 |

## 最先实现并真实验证的一条路径

**本机 OS Owner 控制的终端 → 显式初始化管理身份 → 用原 DTO 安装/选择策略 → 普通凭证受理 → 当前 policy/fence 自动执行。** 当前前两步缺 CLI adapter，不能给一条现有命令冒充可运行。Backend 新增 `owner-init` 和 `owner-policy` 命令族（拟名，正式 help/代码由 Backend 唯一定义），第一批先验证真实管理，不依赖收费模型或 ASR。

`owner-init` 必须由已认证 OS 交互会话在自己拥有的安装数据目录运行，可信 OS API取得 SID/UID、目录实际所有者及本实例 identity，不用命令 JSON 自报 administrator。已有项目先由正常创建入口建立；显式显示并确认实例、实际 domain owner、有限真实自有 project_ids、管理期限及 scope。OS主体与 domain owner 的映射是这次明确安装动作，不是字符串相等或持普通 token 就成立。确认后持久记录本机 bootstrap/管理绑定事实及撤销代次；秘密在本机凭证库或 Linux仅真实 Owner 可读的专用文件，日志/argv/作品/导出不出现内容或秘密 hash。拒普通 bearer、模型、远程网页及仅环境 Bool/config SHA 初始化；不能默认为所有项目或无限期限授管理权。

`owner-policy` 在同一真实 OS Owner 上下文认证该绑定，签发现 registry 的短期独立 capability；只分派现 `InstallProductionPolicy/SelectProductionPolicy/RevokeProductionPolicy/ProductionPolicyRef/ReauthorizeOriginalProduction` 至上述服务，真实 idempotency key和原 receipt 保留。首次/改变范围/续期/恢复须明确 Owner 动作；重放同命令返回原回执，不重置预算。纯 proposal 文件不能自我授权，`--yes`/自报 subject不成为首次 bootstrap 的替代。撤销/到期及时使 registry capability失效，管理身份失效与 policy撤销分开；旧 policy需其真实 revoke/到期/current检查，恢复保留 Control高水位，缺/落后不得重置0或重造审批。

Linux 无头安装同样先由真实管理员在本机或其已授权安全远程终端完成上述动作，再让普通 API/MCP调用；不能要求桌面/产品云注册。第一批只 loopback，不为了接 Portal 新开公网管理端口或放宽 CORS；远程调用另由部署入口保护。当前无 Linux 实机资格，设计不宣已测。

## 唯一装配与角色顺序

1. **Backend**先补上述 CLI/持久 bootstrap adapter 和唯一装配函数：同 engine/owner/DB，真实 registry + `Control/ProductionAuthorizationControl.json` → ProductionAuthorizationService → ProductionAdmissions；同 BundleService → LocalCopyInputService。真实管理命令不绕 service writer，原权限/预算/质量/request hash不变。受理、Worker、MCP均消费同安装绑定/Control与实际注册身份；Worker不持管理credential。`register_execution_identity` 仍必须由可信 adapter绑定真正认证 principal/project/registration，普通调用不能自报。现 Engine按 owner_subject 单映射的限制必须保留：第一批明确单本机Owner；若给不同 Portal principal委派执行，必须接现 InstancePrincipalRegistry真实 registration及其 exact scope，不能把多人折成local-user或静默扩大 map。
2. **Integration**提供可信 OS身份/本机secret句柄与启动封装；把实际 `ProductionInstallationAuthority.observe/assert_current` 接既有固定资源及 held guard，不用安装配置 SHA直接造 InstalledProductionEvidence。API/Worker同原数据、Control及资源版本分别装配，ready不冒worker。没有合格资源时，Owner管理可准确完成，但制作仍具体 resource-not-ready，不能称自动链成功。桌面随后新增**独立管理通道**：Rust内部持管理credential，真实主Webview/来源/capability和明确Owner确认绑定具体命令；执行broker继续普通credential。仅 Backend实际声明 `actual_owner_management` 的固定操作可走该通道，不能全路由通用升权、让 renderer交 bearer或自动选择管理员。保原raw/幂等/来源/关闭语义，失败不用开发proxy顶替native。
3. **Backend→Integration→Frontend**：桌面需要HTTP时，Backend复用上列既有 DTO加 policy install/select/revoke/get/reauthorize 薄路由，复用独立管理依赖并与local-copy共享同registry，不新增泛授权模型；Integration由唯一OpenAPI生成SDK/manifest并修独立认证 dispatch。Frontend在设置/原项目中做“一次授权、续期/撤销、缺授权恢复”，制作仍五步；模型只给proposal，实际Owner确认安装，之后 scope内任务不逐片点击或伪ReviewDecision。

## 下一个独立验证与仍缺条件

先由后端/集成固定真实 CLI入口和 scope，执行角色在专属零费用实例通过真实 OS Owner初始化→install/select/get→ordinary管理403→revoke/expiry/重启后的真实 current/floor检查，再交 Test/Review；无外部账户阻碍这条本机管理验证。随后才接桌面/无头当前资源及普通 API/MCP无人制作，独立验证全部音视频/text/RAG交付。错误沿原 ErrorEnvelope：普通/过期/撤销/错project403，冲突409，坏事实422，缺真实配置/恢复floor503；这些准确拒绝不代最终正向实现。RES13已拒 ASR监督改动仍待用户答复，不代写或绕审；预算、许可、精度门、三 OS及官方订阅内部API/MCP生成要求保持。全部源码读取终态后固定交接，架构批准不等产品或验收通过。
