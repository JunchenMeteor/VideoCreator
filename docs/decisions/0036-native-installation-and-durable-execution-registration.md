# ADR0036 — 独立宿主安装记录与持久执行登记

- 状态：A33 架构准入；尚未实现、运行、独立验证或取得资源资格。
- 日期：2026-10-10。唯一路线：真实 Owner 管理动作写持久登记，启动可信 current lookup，经同 Engine 原 issuer 新发原对象；不采用可携带完整授权的启动 JSON。
- 依据：B38 固定普通源/Interfaces/SourceGap；I53 止写 SourceGap 与 NextProducerPlan；ADR0032。精确身份见 A33InputPins.json。保留 Gate0→完整 R1 三 OS/本地免产品注册/BYOK/API/MCP 自动制作→连续 R2。

## 1. 已有事实与准入边界

B38 的 native-startup-binding-v1 十字段只描述实例、角色、独立宿主镜像及三 SHA、完整文件图/分区。ProductionAdmissions.register_execution_identity 当前只将原对象放入 issuer 内存集合；新 Engine 没有持久登记查询。OwnerBindingRecord 及 production.authorization.manage 是独立管理授权，不能自动授执行权限。原 Owner CLI 有明确 TTY 确认、实际 OS/目录身份、管理 registry；原 ProductionAuthorizationControl 有 reserve→DB commit→complete、高水位与原命令幂等恢复，均保留。

I53 的 pins.root 是 Engine 清单父目录，宿主 EXE 通常位于其外；将 EXE SHA 写入又嵌入该 EXE 的清单产生自哈希循环。两次 Cargo check0 只证明源码可编译，不证明此 prototype 可成包。当前 qualification issuer 仍未准入；持久登记可实现，不能把登记、文件 hash 或本 ADR 当 InstalledProductionEvidence。

## 2. 无环宿主构建与独立安装记录

构建顺序固定：完整 Engine/资源 payload 与其清单→宿主编译（可嵌该 payload 清单 SHA）→取得最终 EXE bytes/完整 SHA→外部 native-build-receipt-v1。收据含实际产物大小/SHA、target、宿主源/锁/工具/producer input ref、对应 payload/registration/resource/runtime 身份和版权/资格证据 ref；其最终 SHA 或含最终 EXE SHA 的记录不得再嵌回同一个 EXE/payload。收据描述构建事实，签名须有已独立安装的可信发布者锚才能授相应发布者信任；自带 signer/hash 不是锚。本人本地构建可由真实 Owner 明确接纳镜像身份，不冒充厂商签名、许可证或 ABI/ASR 资格。

实际 Owner 安装动作将该收据及完整 payload 关系写为私有 installed-native-record-v1：record id/revision、instance/domain Owner、真实 OS/存储目录身份、安装 composition root、独立 host-image 绝对本地路径/大小/SHA、payload root/清单/完整 expected_files 与 engine_file_names、构建收据 ref/full SHA、原安装动作/当前与撤销状态。上述实际路径/身份由安装端实际打开核对，不由任务、locator.server、Webview 或配置 hash 提供资格。收据及记录的原始规范字节须保留且可重核；完整图与分区必须唯一相符。大小/路径/字节限制沿现有 grammar，禁止 ..、别名截断、链接/UNC/ADS 绕行。

记录由实际 Owner 同一受保护实例存储及原 action/floor 管理；后台读取不需管理 secret。OS保护保障其他 OS principal 不改写，并不声称抵御任意同 Owner 原生代码或系统管理员；产品的模型/插件工具无 Control/安装记录写入能力。默认普通用户安装/便携路径仍可由实际 Owner 保护并接纳，不新增一律 root/admin 前置。系统级签名安装和 POSIX 实际保护/加载能力仍按原准入另验。

宿主镜像保持原独立 OwnerProtectedNativeBuild/image guard；Engine 保持原 ResourcePins/PreparedLaunch guard。composition root 来自真实安装记录，host 可在 payload root 外，不将它伪装为 Engine 相对成员。宿主、安装记录和 payload 都须受真实原对象/句柄及 current 状态约束。新的启动载体由这些已核输入在启动时生成；含 host SHA 的 NativeStartup.json 改作独立控制材料，不能继续成为嵌入清单的递归成员。这是新 artifact 版本的明确分层，不移除147生产/24 ASR包或其它能力资源，也不篡改旧 artifact 的图/资格。

## 3. 原 Owner 动作与持久登记

Backend 增加私有 ExecutionRegistrationStore，使用实例原 SQLite/commands 与同一 ProductionAuthorizationControl/registry revision；不用第二授权库、模型布尔或新 bearer。持久事实分为 installed_native_records 和 execution_registrations，current 指针可由唯一约束/metadata 实现；Backend 唯一定义 schema 与新迁移，旧事实不重写。安装记录与执行登记有各自独立 action receipt/ref，不伪造原必含 policy_ref 的 AuthorizationActionReceipt。

执行登记规范体至少含：format=installed-execution-registration-v1；id/revision；instance_id、owner_subject、executing_principal_id；role（api/mcp/worker，仅执行）；有限 project_ids；registration/resource/runtime 三 SHA；有限 allowed_source_namespaces；installed_record_ref（id/revision/content_sha256）；完整 payload 图/分区身份绑定；expires_at_us；原 Owner binding generation/action/authentication_binding_id；安装/替换/revoke 原动作及当前状态。第一版本 executing_principal_id 必须等于真实 domain Owner，与 B38/原 assemble_owner_services 一致；其它主体不能在该版本伪装。role 不携管理、发布平台或预算权限。每 instance+Owner+role 只有一个 current 登记；三个角色可在一次明确确认的有限事务中分别登记，不按 hash 碰运气挑历史记录。

新 owner-execution install/replace/revoke/get 由原真实 Owner TTY/受控 Native UI 或已认证 headless 管理会话进入，同原 registry.authenticate→action_guard 与 capability；管理登录本身不创建登记。install/replace 展示完整范围/镜像/资源身份及有限有效期，由 Owner 明确确认；replace 指向确切 previous ref，不能覆盖不同请求的同 key。范围不得超出实际 Owner 所有项目和当前 management binding 范围；有效期不得超过其本次明确 binding 有效期。Owner generation 改变、撤销/过期或存储 OS 身份改变使原登记不再可用于新执行；续期/迁移可在一次真实 Owner 动作中显式重新认可原范围，不能静默续授。日常启动/每条作品无需重复确认、不能自动重新 owner-init。

动作复用原锁序与保留 floor：OwnerControl→ProductionControl→短 DB writer；管理 capability/项目所有权在准备与 commit 均重核。外部 floor 先 reserve，DB 同事务提交 immutable body/action/commands/current/revision，再 complete；安装记录与关联登记原子绑定。崩溃保留 pending，只有原同 key/同 canonical request 的真实授权重试能 complete。DB 落后 floor、损坏或未知状态拒绝，不能自动回退/造当前记录。首次空库的初始化只随真实 Owner 动作；已有库缺 Control 不重建为零。

这只登记实际执行环境/主体。原 ProductionPolicy install/select/revoke/reauthorize、实际 request/admission/action、lease/fence、rights/许可、预算组/cap 与 paid operation 仍各自逐次校验；不存在“已登记即准制作/发布”的总开关。

## 4. 可信 current lookup 与原 issuer 对象

保持 B38 十字段 v1、原固定 module/callable/canonical bytes/大小限制不变。_current_execution_registration 的正式后继接入同 Engine 的 ExecutionRegistrationStore.current(owner_subject, role, startup_record)，按实例/真实 Bundle Owner/role 找唯一 current，核原完整体/action/ref/Owner generation/floor/project/expiry/独立安装记录以及载体全部身份（不只三 SHA）。不存在当前记录404；主体/角色/范围/撤销/过期403；冲突/换代409；损坏422；缺原 floor/资源资格或未实现端口503。Backend 沿唯一 ErrorEnvelope 定义具体 code，不能把 unknown 变 null，或所有合法当前记录永久503。

返回私有 CurrentExecutionRegistration 原事实及原强对象 current-check 绑定，非 public DTO/可移植 ticket。由同一次 assemble 原 issuer.register_execution_identity 投影原八字段，再 engine.configure_production_authorization；原 RegisteredExecutionIdentity 仍 issuer 集合的 eq=False 强对象。附加私有原对象→registration ref/current authority 绑定，不能仅投影字典后丢失持久来源。复制 JSON、跨 Engine/issuer、旧对象、关连 session/角色不产生同等身份。

启动顺序：读受保护安装/登记事实→实际打开独立 host-image 与原 payload guard→原 pipe peer/child PID+creation/SID/source/角色/instance/fullmap 核验→绑定同 Engine/Bundle/registered runtime 与 issuer→原 ready。载体不能覆盖已核安装记录。失败关闭部分连接并保留原资源到实际子进程/Job后代及原 byte EOF 终态；关窗口/API cleanup、Worker继续/取消仍按原切片，不由登记回收假终态。

每次原 current_guard：资源/EXE/安装记录重核及 authority RPC/hash 在 writer 外；再持 OwnerControl→ProductionControl 原锁并核已读取 floor/无 pending、Owner和登记 current。短 writer 用原 connection 再核 immutable ref/当前指针/revision/项目/过期/Owner generation及原本地 installation epoch/object，禁止 writer 内 hash/RPC/网络。与 Owner revoke/replace 串行，不能只在启动核一次后缓存 True。外部 current check 失效须使本地强对象 guard 不再可用；资源资格 issuer 的 current 仍独立。不得在管理动作回调倒序取锁；Backend/Integration 在接口交接中列出实际锁序。未知收费 Operation 保留原 reconciliation 守卫，撤销阻止新派发，不把旧 unknown 自动删除、重放或伪成功。

## 5. 兼容、实现顺序与独立验证

1. Backend：先唯一私有模型/store/迁移与原 Owner 实际 action 入口/receipt；再 current lookup/强对象绑定/current_guard 接入原同 Engine 工厂。管理 API如需新声明仅 Backend 定义、Integration生成；普通制作 API/MCP 不暴露登记写工具。原旧 OwnerBinding/政策/预算/作品保原字节，内存测试注册语义不冒充可持久记录；旧安装升级须真实 Owner 承认新 artifact 身份，不暗增范围。后继迁移数量以最终唯一源为准，不把旧5迁移 artifact 当新7迁移或再新增迁移成品。
2. Integration：先独立 build receipt/Owner 安装记录实际生成读取与双 guard；修 root 外 host 与载体无环 producer；消费 Backend 正式新合同/完整源快照（含 B38 fixed entry和最终全部迁移）及固定 Media，唯一 builder 新版本成包。保147+24/四profiles/CPU-ASR/FFmpeg及完整 namespace、data/native/许可闭包；不得 plain cli.main 回退。随后实测真实安装/Owner动作/current登记→API/MCP/Worker原入口，不从测试 ID 创建资格。
3. Frontend：一次明确安装/执行范围确认、当前/过期/撤销显示与正常创作五步；后续日常自动流程不要求逐作品安装批准。Media继续原 typed admission/操作链，不改授权或预算账本。
4. Test：原真实 Owner 动作写记录后，关闭/重启新 Engine，合法 current 经独立 host/payload→同 issuer/same Bundle→正常 ready及自动作品；分别 API/MCP/Worker。负例覆盖缺/多 current、tampered body/action/map/receipt、另一 Owner/角色/instance、管理 token 冒执行、三SHA伪登记、原 ref换代/撤销/expiry、floor pending/DB restore、前后 concurrent revoke、跨issuer旧强对象、payload root外合法host/路径绕行、构建自哈希回边、真实子进程/后代未终态不释放。正常记录不得只检查 expected拒绝；缺真实资格的 facts-only正负检查明确不能算作品成功。
5. Review独立查 store/锁序/权利不扩/新 producer 无环；Acceptance验实际本地安装与完整Bundle。Windows当前 protected-image实现不等于Linux/macOS通过；POSIX等价任务按ADR0033继续，不能以此留永久unsupported。官方生成/Kimi SDK其它准入、许可证、CRT floor、ASR监督/精度与三OS实测保持未完成，不由此准入或回避。

本 ADR 仅批准上述有限实现路线。A33 未执行产品、Owner动作、DB、SDK、native、模型或安装；费用/凭证/联网为0。来源静态事实与方案分开，独立测试/Review/验收尚未运行。
